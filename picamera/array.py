# vim: set et sw=4 sts=4 fileencoding=utf-8:
#
# Python camera library for the Rasperry-Pi camera module
# Copyright (c) 2013-2015 Dave Jones <dave@waveform.org.uk>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the copyright holder nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from __future__ import (
    unicode_literals,
    print_function,
    division,
    absolute_import,
    )

# Make Py2's str and range equivalent to Py3's
native_str = str
str = type('')
try:
    range = xrange
except NameError:
    pass

import io
import ctypes as ct
import warnings

import numpy as np
from numpy.lib.stride_tricks import as_strided

from . import mmalobj as mo, mmal
from .exc import (
    mmal_check,
    PiCameraValueError,
    PiCameraDeprecated,
    PiCameraPortDisabled,
    )


motion_dtype = np.dtype([
    (native_str('x'),   np.int8),
    (native_str('y'),   np.int8),
    (native_str('sad'), np.uint16),
    ])


def raw_resolution(resolution, splitter=False):
    """
    Round a (width, height) tuple up to the nearest multiple of 32 horizontally
    and 16 vertically (as this is what the Pi's camera module does for
    unencoded output).
    """
    width, height = resolution
    if splitter:
        fwidth = (width + 15) & ~15
    else:
        fwidth = (width + 31) & ~31
    fheight = (height + 15) & ~15
    return fwidth, fheight


def bytes_to_yuv(data, resolution):
    """
    Converts a bytes object containing YUV data to a `numpy`_ array.
    """
    width, height = resolution
    fwidth, fheight = raw_resolution(resolution)
    y_len = fwidth * fheight
    uv_len = (fwidth // 2) * (fheight // 2)
    if len(data) != (y_len + 2 * uv_len):
        raise PiCameraValueError(
            'Incorrect buffer length for resolution %dx%d' % (width, height))
    # Separate out the Y, U, and V values from the array
    a = np.frombuffer(data, dtype=np.uint8)
    Y = a[:y_len].reshape((fheight, fwidth))
    Uq = a[y_len:-uv_len].reshape((fheight // 2, fwidth // 2))
    Vq = a[-uv_len:].reshape((fheight // 2, fwidth // 2))
    # Reshape the values into two dimensions, and double the size of the
    # U and V values (which only have quarter resolution in YUV4:2:0)
    U = np.empty_like(Y)
    V = np.empty_like(Y)
    U[0::2, 0::2] = Uq
    U[0::2, 1::2] = Uq
    U[1::2, 0::2] = Uq
    U[1::2, 1::2] = Uq
    V[0::2, 0::2] = Vq
    V[0::2, 1::2] = Vq
    V[1::2, 0::2] = Vq
    V[1::2, 1::2] = Vq
    # Stack the channels together and crop to the actual resolution
    return np.dstack((Y, U, V))[:height, :width]


def bytes_to_rgb(data, resolution):
    """
    Converts a bytes objects containing RGB/BGR data to a `numpy`_ array.
    """
    width, height = resolution
    fwidth, fheight = raw_resolution(resolution)
    # Workaround: output from the video splitter is rounded to 16x16 instead
    # of 32x16 (but only for RGB, and only when a resizer is not used)
    if len(data) != (fwidth * fheight * 3):
        fwidth, fheight = raw_resolution(resolution, splitter=True)
        if len(data) != (fwidth * fheight * 3):
            raise PiCameraValueError(
                'Incorrect buffer length for resolution %dx%d' % (width, height))
    # Crop to the actual resolution
    return np.frombuffer(data, dtype=np.uint8).\
            reshape((fheight, fwidth, 3))[:height, :width, :]


class PiArrayOutput(io.BytesIO):
    """
    Base class for capture arrays.

    This class extends :class:`io.BytesIO` with a `numpy`_ array which is
    intended to be filled when :meth:`~io.IOBase.flush` is called (i.e. at the
    end of capture).

    .. attribute:: array

        After :meth:`~io.IOBase.flush` is called, this attribute contains the
        frame's data as a multi-dimensional `numpy`_ array. This is typically
        organized with the dimensions ``(rows, columns, plane)``. Hence, an
        RGB image with dimensions *x* and *y* would produce an array with shape
        ``(y, x, 3)``.
    """

    def __init__(self, camera, size=None):
        super(PiArrayOutput, self).__init__()
        self.camera = camera
        self.size = size
        self.array = None

    def close(self):
        super(PiArrayOutput, self).close()
        self.array = None

    def truncate(self, size=None):
        """
        Resize the stream to the given size in bytes (or the current position
        if size is not specified). This resizing can extend or reduce the
        current file size.  The new file size is returned.

        In prior versions of picamera, truncation also changed the position of
        the stream (because prior versions of these stream classes were
        non-seekable). This functionality is now deprecated; scripts should
        use :meth:`~io.IOBase.seek` and :meth:`truncate` as one would with
        regular :class:`~io.BytesIO` instances.
        """
        if size is not None:
            warnings.warn(
                PiCameraDeprecated(
                    'This method changes the position of the stream to the '
                    'truncated length; this is deprecated functionality and '
                    'you should not rely on it (seek before or after truncate '
                    'to ensure position is consistent)'))
        super(PiArrayOutput, self).truncate(size)
        if size is not None:
            self.seek(size)


class PiRGBArray(PiArrayOutput):
    """
    Produces a 3-dimensional RGB array from an RGB capture.

    This custom output class can be used to easily obtain a 3-dimensional numpy
    array, organized (rows, columns, colors), from an unencoded RGB capture.
    The array is accessed via the :attr:`~PiArrayOutput.array` attribute. For
    example::

        import picamera
        import picamera.array

        with picamera.PiCamera() as camera:
            with picamera.array.PiRGBArray(camera) as output:
                camera.capture(output, 'rgb')
                print('Captured %dx%d image' % (
                        output.array.shape[1], output.array.shape[0]))

    You can re-use the output to produce multiple arrays by emptying it with
    ``truncate(0)`` between captures::

        import picamera
        import picamera.array

        with picamera.PiCamera() as camera:
            with picamera.array.PiRGBArray(camera) as output:
                camera.resolution = (1280, 720)
                camera.capture(output, 'rgb')
                print('Captured %dx%d image' % (
                        output.array.shape[1], output.array.shape[0]))
                output.truncate(0)
                camera.resolution = (640, 480)
                camera.capture(output, 'rgb')
                print('Captured %dx%d image' % (
                        output.array.shape[1], output.array.shape[0]))

    If you are using the GPU resizer when capturing (with the *resize*
    parameter of the various :meth:`~PiCamera.capture` methods), specify the
    resized resolution as the optional *size* parameter when constructing the
    array output::

        import picamera
        import picamera.array

        with picamera.PiCamera() as camera:
            camera.resolution = (1280, 720)
            with picamera.array.PiRGBArray(camera, size=(640, 360)) as output:
                camera.capture(output, 'rgb', resize=(640, 360))
                print('Captured %dx%d image' % (
                        output.array.shape[1], output.array.shape[0]))
    """

    def flush(self):
        super(PiRGBArray, self).flush()
        self.array = bytes_to_rgb(self.getvalue(), self.size or self.camera.resolution)


class PiYUVArray(PiArrayOutput):
    """
    Produces 3-dimensional YUV & RGB arrays from a YUV capture.

    This custom output class can be used to easily obtain a 3-dimensional numpy
    array, organized (rows, columns, channel), from an unencoded YUV capture.
    The array is accessed via the :attr:`~PiArrayOutput.array` attribute. For
    example::

        import picamera
        import picamera.array

        with picamera.PiCamera() as camera:
            with picamera.array.PiYUVArray(camera) as output:
                camera.capture(output, 'yuv')
                print('Captured %dx%d image' % (
                        output.array.shape[1], output.array.shape[0]))

    The :attr:`rgb_array` attribute can be queried for the equivalent RGB
    array (conversion is performed using the `ITU-R BT.601`_ matrix)::

        import picamera
        import picamera.array

        with picamera.PiCamera() as camera:
            with picamera.array.PiYUVArray(camera) as output:
                camera.resolution = (1280, 720)
                camera.capture(output, 'yuv')
                print(output.array.shape)
                print(output.rgb_array.shape)

    If you are using the GPU resizer when capturing (with the *resize*
    parameter of the various :meth:`~picamera.PiCamera.capture` methods),
    specify the resized resolution as the optional *size* parameter when
    constructing the array output::

        import picamera
        import picamera.array

        with picamera.PiCamera() as camera:
            camera.resolution = (1280, 720)
            with picamera.array.PiYUVArray(camera, size=(640, 360)) as output:
                camera.capture(output, 'yuv', resize=(640, 360))
                print('Captured %dx%d image' % (
                        output.array.shape[1], output.array.shape[0]))

    .. _ITU-R BT.601: https://en.wikipedia.org/wiki/YCbCr#ITU-R_BT.601_conversion
    """

    def __init__(self, camera, size=None):
        super(PiYUVArray, self).__init__(camera, size)
        self._rgb = None

    def flush(self):
        super(PiYUVArray, self).flush()
        self.array = bytes_to_yuv(self.getvalue(), self.size or self.camera.resolution)
        self._rgb = None

    @property
    def rgb_array(self):
        if self._rgb is None:
            # Apply the standard biases
            YUV = self.array.astype(float)
            YUV[:, :, 0]  = YUV[:, :, 0]  - 16  # Offset Y by 16
            YUV[:, :, 1:] = YUV[:, :, 1:] - 128 # Offset UV by 128
            # YUV conversion matrix from ITU-R BT.601 version (SDTV)
            #              Y       U       V
            M = np.array([[1.164,  0.000,  1.596],    # R
                          [1.164, -0.392, -0.813],    # G
                          [1.164,  2.017,  0.000]])   # B
            # Calculate the dot product with the matrix to produce RGB output,
            # clamp the results to byte range and convert to bytes
            self._rgb = YUV.dot(M.T).clip(0, 255).astype(np.uint8)
        return self._rgb


class BroadcomRawHeader(ct.Structure):
    _fields_ = [
        ('name',          ct.c_char * 32),
        ('width',         ct.c_uint16),
        ('height',        ct.c_uint16),
        ('padding_right', ct.c_uint16),
        ('padding_down',  ct.c_uint16),
        ('dummy',         ct.c_uint32 * 6),
        ('transform',     ct.c_uint16),
        ('format',        ct.c_uint16),
        ('bayer_order',   ct.c_uint8),
        ('bayer_format',  ct.c_uint8),
        ]


class PiBayerArray(PiArrayOutput):
    """
    Produces a 3-dimensional RGB array from raw Bayer data.

    This custom output class is intended to be used with the
    :meth:`~picamera.PiCamera.capture` method, with the *bayer* parameter set
    to ``True``, to include raw Bayer data in the JPEG output.  The class
    strips out the raw data, and constructs a numpy array from it.  The
    resulting data is accessed via the :attr:`~PiArrayOutput.array` attribute::

        import picamera
        import picamera.array

        with picamera.PiCamera() as camera:
            with picamera.array.PiBayerArray(camera) as output:
                camera.capture(output, 'jpeg', bayer=True)
                print(output.array.shape)

    The *output_dims* parameter specifies whether the resulting array is
    three-dimensional (the default, or when *output_dims* is 3), or
    two-dimensional (when *output_dims* is 2). The three-dimensional data is
    already separated into the three color planes, whilst the two-dimensional
    variant is not (in which case you need to know the Bayer ordering to
    accurately deal with the results).

    .. note::

        Bayer data is *usually* full resolution, so the resulting array usually
        has the shape (1944, 2592, 3) with the V1 module, or (2464, 3280, 3)
        with the V2 module (if two-dimensional output is requested the
        3-layered color dimension is omitted). If the camera's
        :attr:`~picamera.PiCamera.sensor_mode` has been forced to something
        other than 0, then the output will be the native size for the requested
        sensor mode.

        This also implies that the optional *size* parameter (for specifying a
        resizer resolution) is not available with this array class.

    As the sensor records 10-bit values, the array uses the unsigned 16-bit
    integer data type.

    By default, `de-mosaicing`_ is **not** performed; if the resulting array is
    viewed it will therefore appear dark and too green (due to the green bias
    in the `Bayer pattern`_). A trivial weighted-average demosaicing algorithm
    is provided in the :meth:`demosaic` method::

        import picamera
        import picamera.array

        with picamera.PiCamera() as camera:
            with picamera.array.PiBayerArray(camera) as output:
                camera.capture(output, 'jpeg', bayer=True)
                print(output.demosaic().shape)

    Viewing the result of the de-mosaiced data will look more normal but still
    considerably worse quality than the regular camera output (as none of the
    other usual post-processing steps like auto-exposure, white-balance,
    vignette compensation, and smoothing have been performed).

    .. versionchanged:: 1.13
        This class now supports the V2 module properly, and handles flipped
        images, and forced sensor modes correctly.

    .. _de-mosaicing: https://en.wikipedia.org/wiki/Demosaicing
    .. _Bayer pattern: https://en.wikipedia.org/wiki/Bayer_filter
    """
    BAYER_OFFSETS = {
        0: ((0, 0), (1, 0), (0, 1), (1, 1)),
        1: ((1, 0), (0, 0), (1, 1), (0, 1)),
        2: ((1, 1), (0, 1), (1, 0), (0, 0)),
        3: ((0, 1), (1, 1), (0, 0), (1, 0)),
        }

    def __init__(self, camera, output_dims=3):
        super(PiBayerArray, self).__init__(camera, size=None)
        if not (2 <= output_dims <= 3):
            raise PiCameraValueError('output_dims must be 2 or 3')
        self._demo = None
        self._header = None
        self._output_dims = output_dims

    @property
    def output_dims(self):
        return self._output_dims

    def _to_3d(self, array):
        array_3d = np.zeros(array.shape + (3,), dtype=array.dtype)
        (
            (ry, rx), (gy, gx), (Gy, Gx), (by, bx)
            ) = PiBayerArray.BAYER_OFFSETS[self._header.bayer_order]
        array_3d[ry::2, rx::2, 0] = array[ry::2, rx::2] # Red
        array_3d[gy::2, gx::2, 1] = array[gy::2, gx::2] # Green
        array_3d[Gy::2, Gx::2, 1] = array[Gy::2, Gx::2] # Green
        array_3d[by::2, bx::2, 2] = array[by::2, bx::2] # Blue
        return array_3d

    def flush(self):
        super(PiBayerArray, self).flush()
        self._demo = None
        offset = {
            'OV5647': {
                0: 6404096,
                1: 2717696,
                2: 6404096,
                3: 6404096,
                4: 1625600,
                5: 1233920,
                6: 445440,
                7: 445440,
                },
            'IMX219': {
                0: 10270208,
                1: 2678784,
                2: 10270208,
                3: 10270208,
                4: 2628608,
                5: 1963008,
                6: 1233920,
                7: 445440,
                },
            }[self.camera.revision.upper()][self.camera.sensor_mode]
        data = self.getvalue()[-offset:]
        if data[:4] != b'BRCM':
            raise PiCameraValueError('Unable to locate Bayer data at end of buffer')
        # Extract header (with bayer order and other interesting bits), which
        # is 176 bytes from start of bayer data, and pixel data which 32768
        # bytes from start of bayer data
        self._header = BroadcomRawHeader.from_buffer_copy(
            data[176:176 + ct.sizeof(BroadcomRawHeader)])
        data = np.frombuffer(data, dtype=np.uint8, offset=32768)
        # Reshape and crop the data. The crop's width is multiplied by 5/4 to
        # deal with the packed 10-bit format; the shape's width is calculated
        # in a similar fashion but with padding included (which involves
        # several additional padding steps)
        crop = mo.PiResolution(
            self._header.width * 5 // 4,
            self._header.height)
        shape = mo.PiResolution(
            (((self._header.width + self._header.padding_right) * 5) + 3) // 4,
            (self._header.height + self._header.padding_down)
            ).pad()
        data = data.reshape((shape.height, shape.width))[:crop.height, :crop.width]
        # Unpack 10-bit values; every 5 bytes contains the high 8-bits of 4
        # values followed by the low 2-bits of 4 values packed into the fifth
        # byte
        data = data.astype(np.uint16) << 2
        for byte in range(4):
            data[:, byte::5] |= ((data[:, 4::5] >> ((4 - byte) * 2)) & 3)
        self.array = np.zeros(
            (data.shape[0], data.shape[1] * 4 // 5), dtype=np.uint16)
        for i in range(4):
            self.array[:, i::4] = data[:, i::5]
        if self.output_dims == 3:
            self.array = self._to_3d(self.array)

    def demosaic(self):
        """
        Perform a rudimentary `de-mosaic`_ of ``self.array``, returning the
        result as a new array. The result of the demosaic is *always* three
        dimensional, with the last dimension being the color planes (see
        *output_dims* parameter on the constructor).

        .. _de-mosaic: https://en.wikipedia.org/wiki/Demosaicing
        """
        if self._demo is None:
            # Construct 3D representation of Bayer data (if necessary)
            if self.output_dims == 2:
                array_3d = self._to_3d(self.array)
            else:
                array_3d = self.array
            # Construct representation of the bayer pattern
            bayer = np.zeros(array_3d.shape, dtype=np.uint8)
            (
                (ry, rx), (gy, gx), (Gy, Gx), (by, bx)
                ) = PiBayerArray.BAYER_OFFSETS[self._header.bayer_order]
            bayer[ry::2, rx::2, 0] = 1 # Red
            bayer[gy::2, gx::2, 1] = 1 # Green
            bayer[Gy::2, Gx::2, 1] = 1 # Green
            bayer[by::2, bx::2, 2] = 1 # Blue
            # Allocate output array with same shape as data and set up some
            # constants to represent the weighted average window
            window = (3, 3)
            borders = (window[0] - 1, window[1] - 1)
            border = (borders[0] // 2, borders[1] // 2)
            # Pad out the data and the bayer pattern (np.pad is faster but
            # unavailable on the version of numpy shipped with Raspbian at the
            # time of writing)
            rgb = np.zeros((
                array_3d.shape[0] + borders[0],
                array_3d.shape[1] + borders[1],
                array_3d.shape[2]), dtype=array_3d.dtype)
            rgb[
                border[0]:rgb.shape[0] - border[0],
                border[1]:rgb.shape[1] - border[1],
                :] = array_3d
            bayer_pad = np.zeros((
                array_3d.shape[0] + borders[0],
                array_3d.shape[1] + borders[1],
                array_3d.shape[2]), dtype=bayer.dtype)
            bayer_pad[
                border[0]:bayer_pad.shape[0] - border[0],
                border[1]:bayer_pad.shape[1] - border[1],
                :] = bayer
            bayer = bayer_pad
            # For each plane in the RGB data, construct a view over the plane
            # of 3x3 matrices. Then do the same for the bayer array and use
            # Einstein summation to get the weighted average
            self._demo = np.empty(array_3d.shape, dtype=array_3d.dtype)
            for plane in range(3):
                p = rgb[..., plane]
                b = bayer[..., plane]
                pview = as_strided(p, shape=(
                    p.shape[0] - borders[0],
                    p.shape[1] - borders[1]) + window, strides=p.strides * 2)
                bview = as_strided(b, shape=(
                    b.shape[0] - borders[0],
                    b.shape[1] - borders[1]) + window, strides=b.strides * 2)
                psum = np.einsum('ijkl->ij', pview)
                bsum = np.einsum('ijkl->ij', bview)
                self._demo[..., plane] = psum // bsum
        return self._demo


class PiMotionArray(PiArrayOutput):
    """
    Produces a 3-dimensional array of motion vectors from the H.264 encoder.

    This custom output class is intended to be used with the *motion_output*
    parameter of the :meth:`~picamera.PiCamera.start_recording` method.  Once
    recording has finished, the class generates a 3-dimensional numpy array
    organized as (frames, rows, columns) where ``rows`` and ``columns`` are the
    number of rows and columns of `macro-blocks`_ (16x16 pixel blocks) in the
    original frames. There is always one extra column of macro-blocks present
    in motion vector data.

    The data-type of the :attr:`~PiArrayOutput.array` is an (x, y, sad)
    structure where ``x`` and ``y`` are signed 1-byte values, and ``sad`` is an
    unsigned 2-byte value representing the `sum of absolute differences`_ of
    the block. For example::

        import picamera
        import picamera.array

        with picamera.PiCamera() as camera:
            with picamera.array.PiMotionArray(camera) as output:
                camera.resolution = (640, 480)
                camera.start_recording(
                      '/dev/null', format='h264', motion_output=output)
                camera.wait_recording(30)
                camera.stop_recording()
                print('Captured %d frames' % output.array.shape[0])
                print('Frames are %dx%d blocks big' % (
                    output.array.shape[2], output.array.shape[1]))

    If you are using the GPU resizer with your recording, use the optional
    *size* parameter to specify the resizer's output resolution when
    constructing the array::

        import picamera
        import picamera.array

        with picamera.PiCamera() as camera:
            camera.resolution = (640, 480)
            with picamera.array.PiMotionArray(camera, size=(320, 240)) as output:
                camera.start_recording(
                    '/dev/null', format='h264', motion_output=output,
                    resize=(320, 240))
                camera.wait_recording(30)
                camera.stop_recording()
                print('Captured %d frames' % output.array.shape[0])
                print('Frames are %dx%d blocks big' % (
                    output.array.shape[2], output.array.shape[1]))

    .. note::

        This class is not suitable for real-time analysis of motion vector
        data. See the :class:`PiMotionAnalysis` class instead.

    .. _macro-blocks: https://en.wikipedia.org/wiki/Macroblock
    .. _sum of absolute differences: https://en.wikipedia.org/wiki/Sum_of_absolute_differences
    """

    def flush(self):
        super(PiMotionArray, self).flush()
        width, height = self.size or self.camera.resolution
        cols = ((width + 15) // 16) + 1
        rows = (height + 15) // 16
        b = self.getvalue()
        frames = len(b) // (cols * rows * motion_dtype.itemsize)
        self.array = np.frombuffer(b, dtype=motion_dtype).reshape((frames, rows, cols))


class PiAnalysisOutput(io.IOBase):
    """
    Base class for analysis outputs.

    This class extends :class:`io.IOBase` with a stub :meth:`analyze` method
    which will be called for each frame output. In this base implementation the
    method simply raises :exc:`NotImplementedError`.
    """

    def __init__(self, camera, size=None):
        super(PiAnalysisOutput, self).__init__()
        self.camera = camera
        self.size = size

    def writable(self):
        return True

    def write(self, b):
        return len(b)

    def analyze(self, array):
        """
        Stub method for users to override.
        """
        try:
            self.analyse(array)
            warnings.warn(
                PiCameraDeprecated(
                    'The analyse method is deprecated; use analyze (US '
                    'English spelling) instead'))
        except NotImplementedError:
            raise

    def analyse(self, array):
        """
        Deprecated alias of :meth:`analyze`.
        """
        raise NotImplementedError


class PiRGBAnalysis(PiAnalysisOutput):
    """
    Provides a basis for per-frame RGB analysis classes.

    This custom output class is intended to be used with the
    :meth:`~picamera.PiCamera.start_recording` method when it is called with
    *format* set to ``'rgb'`` or ``'bgr'``. While recording is in progress, the
    :meth:`~PiAnalysisOutput.write` method converts incoming frame data into a
    numpy array and calls the stub :meth:`~PiAnalysisOutput.analyze` method
    with the resulting array (this deliberately raises
    :exc:`NotImplementedError` in this class; you must override it in your
    descendent class).

    .. note::

        If your overridden :meth:`~PiAnalysisOutput.analyze` method runs slower
        than the required framerate (e.g. 33.333ms when framerate is 30fps)
        then the camera's effective framerate will be reduced. Furthermore,
        this doesn't take into account the overhead of picamera itself so in
        practice your method needs to be a bit faster still.

    The array passed to :meth:`~PiAnalysisOutput.analyze` is organized as
    (rows, columns, channel) where the channels 0, 1, and 2 are R, G, and B
    respectively (or B, G, R if *format* is ``'bgr'``).
    """

    def write(self, b):
        result = super(PiRGBAnalysis, self).write(b)
        self.analyze(bytes_to_rgb(b, self.size or self.camera.resolution))
        return result


class PiYUVAnalysis(PiAnalysisOutput):
    """
    Provides a basis for per-frame YUV analysis classes.

    This custom output class is intended to be used with the
    :meth:`~picamera.PiCamera.start_recording` method when it is called with
    *format* set to ``'yuv'``. While recording is in progress, the
    :meth:`~PiAnalysisOutput.write` method converts incoming frame data into a
    numpy array and calls the stub :meth:`~PiAnalysisOutput.analyze` method
    with the resulting array (this deliberately raises
    :exc:`NotImplementedError` in this class; you must override it in your
    descendent class).

    .. note::

        If your overridden :meth:`~PiAnalysisOutput.analyze` method runs slower
        than the required framerate (e.g. 33.333ms when framerate is 30fps)
        then the camera's effective framerate will be reduced. Furthermore,
        this doesn't take into account the overhead of picamera itself so in
        practice your method needs to be a bit faster still.

    The array passed to :meth:`~PiAnalysisOutput.analyze` is organized as
    (rows, columns, channel) where the channel 0 is Y (luminance), while 1 and
    2 are U and V (chrominance) respectively. The chrominance values normally
    have quarter resolution of the luminance values but this class makes all
    channels equal resolution for ease of use.
    """

    def write(self, b):
        result = super(PiYUVAnalysis, self).write(b)
        self.analyze(bytes_to_yuv(b, self.size or self.camera.resolution))
        return result


class PiMotionAnalysis(PiAnalysisOutput):
    """
    Provides a basis for real-time motion analysis classes.

    This custom output class is intended to be used with the *motion_output*
    parameter of the :meth:`~picamera.PiCamera.start_recording` method.  While
    recording is in progress, the write method converts incoming motion data
    into numpy arrays and calls the stub :meth:`~PiAnalysisOutput.analyze`
    method with the resulting array (which deliberately raises
    :exc:`NotImplementedError` in this class).

    .. note::

        If your overridden :meth:`~PiAnalysisOutput.analyze` method runs slower
        than the required framerate (e.g. 33.333ms when framerate is 30fps)
        then the camera's effective framerate will be reduced. Furthermore,
        this doesn't take into account the overhead of picamera itself so in
        practice your method needs to be a bit faster still.

    The array passed to :meth:`~PiAnalysisOutput.analyze` is organized as
    (rows, columns) where ``rows`` and ``columns`` are the number of rows and
    columns of `macro-blocks`_ (16x16 pixel blocks) in the original frames.
    There is always one extra column of macro-blocks present in motion vector
    data.

    The data-type of the array is an (x, y, sad) structure where ``x`` and
    ``y`` are signed 1-byte values, and ``sad`` is an unsigned 2-byte value
    representing the `sum of absolute differences`_ of the block.

    An example of a crude motion detector is given below::

        import numpy as np
        import picamera
        import picamera.array

        class DetectMotion(picamera.array.PiMotionAnalysis):
            def analyze(self, a):
                a = np.sqrt(
                    np.square(a['x'].astype(np.float)) +
                    np.square(a['y'].astype(np.float))
                    ).clip(0, 255).astype(np.uint8)
                # If there're more than 10 vectors with a magnitude greater
                # than 60, then say we've detected motion
                if (a > 60).sum() > 10:
                    print('Motion detected!')

        with picamera.PiCamera() as camera:
            with DetectMotion(camera) as output:
                camera.resolution = (640, 480)
                camera.start_recording(
                      '/dev/null', format='h264', motion_output=output)
                camera.wait_recording(30)
                camera.stop_recording()

    You can use the optional *size* parameter to specify the output resolution
    of the GPU resizer, if you are using the *resize* parameter of
    :meth:`~picamera.PiCamera.start_recording`.
    """

    def __init__(self, camera, size=None):
        super(PiMotionAnalysis, self).__init__(camera, size)
        self.cols = None
        self.rows = None

    def write(self, b):
        result = super(PiMotionAnalysis, self).write(b)
        if self.cols is None:
            width, height = self.size or self.camera.resolution
            self.cols = ((width + 15) // 16) + 1
            self.rows = (height + 15) // 16
        self.analyze(
                np.frombuffer(b, dtype=motion_dtype).\
                reshape((self.rows, self.cols)))
        return result


class MMALArrayBuffer(mo.MMALBuffer):
    __slots__ = ('_shape',)

    def __init__(self, port, buf):
        super(MMALArrayBuffer, self).__init__(buf)
        width = port._format[0].es[0].video.width
        height = port._format[0].es[0].video.height
        bpp = self.size // (width * height)
        self.offset = 0
        self.length = width * height * bpp
        self._shape = (height, width, bpp)

    def __enter__(self):
        mmal_check(
            mmal.mmal_buffer_header_mem_lock(self._buf),
            prefix='unable to lock buffer header memory')
        assert self.offset == 0
        return np.frombuffer(
            ct.cast(
                self._buf[0].data,
                ct.POINTER(ct.c_uint8 * self._buf[0].alloc_size)).contents,
            dtype=np.uint8, count=self.length).reshape(self._shape)

    def __exit__(self, *exc):
        mmal.mmal_buffer_header_mem_unlock(self._buf)
        return False


class PiArrayTransform(mo.MMALPythonComponent):
    """
    A derivative of :class:`~picamera.mmalobj.MMALPythonComponent` which eases
    the construction of custom MMAL transforms by representing buffer data as
    numpy arrays. The *formats* parameter specifies the accepted input
    formats as a sequence of strings (default: 'rgb', 'bgr', 'rgba', 'bgra').

    Override the :meth:`transform` method to modify buffers sent to the
    component, then place it in your MMAL pipeline as you would a normal
    encoder.
    """
    __slots__ = ()

    def __init__(self, formats=('rgb', 'bgr', 'rgba', 'bgra')):
        super(PiArrayTransform, self).__init__()
        if isinstance(formats, bytes):
            formats = formats.decode('ascii')
        if isinstance(formats, str):
            formats = (formats,)
        try:
            formats = {
                {
                    'rgb': mmal.MMAL_ENCODING_RGB24,
                    'bgr': mmal.MMAL_ENCODING_BGR24,
                    'rgba': mmal.MMAL_ENCODING_RGBA,
                    'bgra': mmal.MMAL_ENCODING_BGRA,
                    }[fmt]
                for fmt in formats
                }
        except KeyError as e:
            raise PiCameraValueError(
                'PiArrayTransform cannot handle format %s' % str(e))
        self.inputs[0].supported_formats = formats
        self.outputs[0].supported_formats = formats

    def _callback(self, port, source_buf):
        try:
            target_buf = self.outputs[0].get_buffer(False)
        except PiCameraPortDisabled:
            return False
        if target_buf:
            target_buf.copy_meta(source_buf)
            result = self.transform(
                MMALArrayBuffer(port, source_buf._buf),
                MMALArrayBuffer(self.outputs[0], target_buf._buf))
            try:
                self.outputs[0].send_buffer(target_buf)
            except PiCameraPortDisabled:
                return False
        return False

    def transform(self, source, target):
        """
        This method will be called for every frame passing through the
        transform.  The *source* and *target* parameters represent buffers from
        the input and output ports of the transform respectively. They will be
        derivatives of :class:`~picamera.mmalobj.MMALBuffer` which return a
        3-dimensional numpy array when used as context managers. For example::

            def transform(self, source, target):
                with source as source_array, target as target_array:
                    # Copy the source array data to the target
                    target_array[...] = source_array
                    # Draw a box around the edges
                    target_array[0, :, :] = 0xff
                    target_array[-1, :, :] = 0xff
                    target_array[:, 0, :] = 0xff
                    target_array[:, -1, :] = 0xff
                    return False

        The target buffer's meta-data starts out as a copy of the source
        buffer's meta-data, but the target buffer's data starts out
        uninitialized.
        """
        return False

