# vim: set et sw=4 sts=4 fileencoding=utf-8:
#
# Python camera library for the Rasperry-Pi camera module
# Copyright (c) 2013,2014 Dave Hughes <dave@waveform.org.uk>
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

"""
The :mod:`picamera.array` module provides a set of classes which aid in
constructing n-dimensional `numpy`_ arrays from the camera output. In order to
avoid adding a hard dependency on numpy to picamera, the module is not
automatically imported by the main picamera package and must be explicitly
imported.

.. _numpy: http://www.numpy.org/

The following classes are defined in the module:

PiBaseOutput
============

.. autoclass:: PiBaseOutput
    :members:


PiRGBArray
==========

.. autoclass:: PiRGBArray


PiYUVArray
==========

.. autoclass:: PiYUVArray


PiBayerArray
============

.. autoclass:: PiBayerArray


PiMotionArray
=============

.. autoclass:: PiMotionArray


PiMotionAnalysis
================

.. autoclass:: PiMotionAnalysis
"""

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

import numpy as np
from numpy.lib.stride_tricks import as_strided

from .exc import PiCameraValueError


motion_dtype = np.dtype([
    (native_str('x'),   np.int8),
    (native_str('y'),   np.int8),
    (native_str('sad'), np.uint16),
    ])


class PiBaseOutput(object):
    """
    Base class for all custom output classes defined in this module.

    This class is not intended for direct use, but is a useful base-class for
    constructing :ref:`custom outputs <custom_outputs>`. The :meth:`write`
    method simply appends data to the :attr:`buffer` attribute until the
    :meth:`flush` method is called which in descendent classes is expected to
    construct a `numpy`_ array from the buffered data.
    """
    def __init__(self, camera, size=None):
        super(PiBaseOutput, self).__init__()
        self.closed = False
        self.camera = camera
        self.size = size
        self.buffer = b''
        self.array = None

    def readable(self):
        """
        Returns ``False``, indicating that the stream doesn't support :meth:`read`.
        """
        return False

    def writable(self):
        """
        Returns ``True``, indicating that the stream supports :meth:`write`.
        """
        return True

    def seekable(self):
        """
        Returns ``False``, indicating that the stream doesn't support :meth:`seek`.
        """
        return False

    def read(self, n=-1):
        """
        Raises :exc:`NotImplementedError` as this is a write-only stream.
        """
        raise NotImplementedError

    def write(self, b):
        """
        Write the given bytes or bytearray object, *b*, to the internal
        buffer and return the number of bytes written.
        """
        self._check_closed()
        self.buffer += b
        return len(b)

    def seek(self, offset, whence=0):
        """
        Raises :exc:`NotImplementedError` as this is a non-seekable stream.
        """
        raise NotImplementedError

    def tell(self):
        """
        Returns the current stream position (always equal to the length of
        the internal buffer in this implementation).
        """
        self._check_closed()
        return len(self.buffer)

    def truncate(self, size=None):
        """
        Resize the stream to the given *size* in bytes (or the current position
        if *size* is not specified). This resizing can only reduce the
        current stream size in this implementation.

        As this stream is non-seekable and the position is dictated by the
        internal buffer size, shrinking the stream changes the position.
        """
        self._check_closed()
        if size is not None:
            self.buffer = self.buffer[:size]

    def flush(self):
        """
        Override this method in descendent classes to construct the array from
        the buffered data available in :attr:`buffer`.
        """
        self.array = None

    def _check_closed(self):
        if self.closed:
            raise PiCameraValueError('I/O operation on closed file')

    def close(self):
        """
        Closes the stream and frees all resources associated with it.
        """
        self.closed = True
        self.buffer = b''
        self.array = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.close()


class PiRGBArray(PiBaseOutput):
    """
    Produces a 3-dimensional RGB array from an RGB capture.

    This custom output class can be used to easily obtain a 3-dimensional numpy
    array, organized (rows, columns, colors), from an unencoded RGB capture.
    The array is accessed via the :attr:`array` attribute. For example::

        import picamera
        import picamera.array

        with picamera.PiCamera() as camera:
            with picamera.array.PiRGBArray(camera) as output:
                camera.capture(output, 'rgb')
                print('Captured %dx%d image' % (
                        output.array.shape[1], output.array.shape[0]))

    You can re-use the output to produce multiple arrays by emptying it with
    truncate(0) between captures::

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
    parameter of the various :meth:`~picamera.PiCamera.capture` methods),
    specify the resized resolution as the optional *size* parameter when
    constructing the array output::

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
        width, height = self.size or self.camera.resolution
        fwidth = (width + 31) // 32 * 32
        fheight = (height + 15) // 16 * 16
        if len(self.buffer) != (fwidth * fheight * 3):
            raise PiCameraValueError(
                'Incorrect buffer length for resolution %dx%d' % (width, height))
        # Crop to the actual resolution
        self.array = np.frombuffer(self.buffer, dtype=np.uint8).\
                reshape((fheight, fwidth, 3))[:height, :width, :]


class PiYUVArray(PiBaseOutput):
    """
    Produces 3-dimensional YUV & RGB arrays from a YUV capture.

    This custom output class can be used to easily obtain a 3-dimensional numpy
    array, organized (rows, columns, channel), from an unencoded YUV capture.
    The array is accessed via the :attr:`array` attribute. For example::

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

    .. _ITU-R BT.601: http://en.wikipedia.org/wiki/YCbCr#ITU-R_BT.601_conversion
    """

    def __init__(self, camera, size=None):
        super(PiYUVArray, self).__init__(camera, size)
        self._rgb = None

    def flush(self):
        super(PiYUVArray, self).flush()
        self._rgb = None
        width, height = self.size or self.camera.resolution
        fwidth = (width + 31) // 32 * 32
        fheight = (height + 15) // 16 * 16
        y_len = fwidth * fheight
        uv_len = (fwidth // 2) * (fheight // 2)
        if len(self.buffer) != (y_len + 2 * uv_len):
            raise PiCameraValueError(
                'Incorrect buffer length for resolution %dx%d' % (width, height))
        # Separate out the Y, U, and V values from the array
        a = np.frombuffer(self.buffer, dtype=np.uint8)
        Y = a[:y_len]
        U = a[y_len:-uv_len]
        V = a[-uv_len:]
        # Reshape the values into two dimensions, and double the size of the
        # U and V values (which only have quarter resolution in YUV4:2:0)
        Y = Y.reshape((fheight, fwidth))
        U = U.reshape((fheight // 2, fwidth // 2)).repeat(2, axis=0).repeat(2, axis=1)
        V = V.reshape((fheight // 2, fwidth // 2)).repeat(2, axis=0).repeat(2, axis=1)
        # Stack the channels together and crop to the actual resolution
        YUV = np.dstack((Y, U, V))[:height, :width]
        self.array = YUV

    @property
    def rgb_array(self):
        if self._rgb is None:
            # Apply the standard biases
            YUV = self.array.copy()
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


class PiBayerArray(PiBaseOutput):
    """
    Produces a 3-dimensional RGB array from raw Bayer data.

    This custom output class is intended to be used with the
    :meth:`~picamera.PiCamera.capture` method, with the *bayer* parameter set
    to ``True``, to include raw Bayer data in the JPEG output. The class strips
    out the raw data, constructing a 3-dimensional numpy array organized as
    (rows, columns, colors). The resulting data is accessed via the
    :attr:`array` attribute::

        import picamera
        import picamera.array

        with picamera.PiCamera() as camera:
            with picamera.array.PiBayerArray(camera) as output:
                camera.capture(output, 'jpeg', bayer=True)
                print(output.array.shape)

    Note that Bayer data is *always* full resolution, so the resulting array
    always has the shape (1944, 2592, 3); this also implies that the optional
    *size* parameter (for specifying a resizer resolution) is not available
    with this array class. As the sensor records 10-bit values, the array uses
    the unsigned 16-bit integer data type.

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

    .. _de-mosaicing: http://en.wikipedia.org/wiki/Demosaicing
    .. _Bayer pattern: http://en.wikipedia.org/wiki/Bayer_filter
    """

    def __init__(self, camera):
        super(PiBayerArray, self).__init__(camera, size=None)
        self._demo = None

    def flush(self):
        super(PiBayerArray, self).flush()
        self._demo = None
        data = self.buffer[-6404096:]
        if data[:4] != 'BRCM':
            raise PiCameraValueError('Unable to locate Bayer data at end of buffer')
        # Strip header
        data = data[32768:]
        # Reshape into 2D pixel values
        data = np.frombuffer(data, dtype=np.uint8).\
                reshape((1952, 3264))[:1944, :3240]
        # Unpack 10-bit values; every 5 bytes contains the high 8-bits of 4
        # values followed by the low 2-bits of 4 values packed into the fifth
        # byte
        data = data.astype(np.uint16) << 2
        for byte in range(4):
            data[:, byte::5] |= ((data[:, 4::5] >> ((4 - byte) * 2)) & 3)
        data = np.delete(data, np.s_[4::5], 1)
        # XXX Should test camera's vflip and hflip settings here and adjust
        self.array = np.zeros(data.shape + (3,), dtype=data.dtype)
        self.array[1::2, 0::2, 0] = data[1::2, 0::2] # Red
        self.array[0::2, 0::2, 1] = data[0::2, 0::2] # Green
        self.array[1::2, 1::2, 1] = data[1::2, 1::2] # Green
        self.array[0::2, 1::2, 2] = data[0::2, 1::2] # Blue

    def demosaic(self):
        if self._demo is None:
            # XXX Again, should take into account camera's vflip and hflip here
            # Construct representation of the bayer pattern
            bayer = np.zeros(self.array.shape, dtype=np.uint8)
            bayer[1::2, 0::2, 0] = 1 # Red
            bayer[0::2, 0::2, 1] = 1 # Green
            bayer[1::2, 1::2, 1] = 1 # Green
            bayer[0::2, 1::2, 2] = 1 # Blue
            # Allocate output array with same shape as data and set up some
            # constants to represent the weighted average window
            window = (3, 3)
            borders = (window[0] - 1, window[1] - 1)
            border = (borders[0] // 2, borders[1] // 2)
            # Pad out the data and the bayer pattern (np.pad is faster but
            # unavailable on the version of numpy shipped with Raspbian at the
            # time of writing)
            rgb = np.zeros((
                self.array.shape[0] + borders[0],
                self.array.shape[1] + borders[1],
                self.array.shape[2]), dtype=self.array.dtype)
            rgb[
                border[0]:self.array.shape[0] - border[0],
                border[1]:self.array.shape[1] - border[1],
                :] = self.array
            bayer_pad = np.zeros((
                bayer.shape[0] + borders[0],
                bayer.shape[1] + borders[1],
                bayer.shape[2]), dtype=bayer.dtype)
            bayer_pad[
                border[0]:bayer_pad.shape[0] - border[0],
                border[1]:bayer_pad.shape[1] - border[1],
                :] = bayer
            bayer = bayer_pad
            # For each plane in the RGB data, construct a view over the plane
            # of 3x3 matrices. Then do the same for the bayer array and use
            # Einstein summation to get the weighted average
            self._demo = np.empty(self.array.shape, dtype=self.array.dtype)
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


class PiMotionArray(PiBaseOutput):
    """
    Produces a 3-dimensional array of motion vectors from the H.264 encoder.

    This custom output class is intended to be used with the *motion_output*
    parameter of the :meth:`~picamera.PiCamera.start_recording` method. Once
    recording has finished, the class generates a 3-dimensional numpy array
    organized as (frames, rows, columns) where ``rows`` and ``columns`` are the
    number of rows and columns of `macro-blocks`_ (16x16 pixel blocks) in the
    original frames. There is always one extra column of macro-blocks present
    in motion vector data.

    The data-type of the :attr:`array` is an (x, y, sad) structure where ``x``
    and ``y`` are signed 1-byte values, and ``sad`` is an unsigned 2-byte value
    representing the `sum of absolute differences`_ of the block. For example::

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

    .. _macro-blocks: http://en.wikipedia.org/wiki/Macroblock
    .. _sum of absolute differences: http://en.wikipedia.org/wiki/Sum_of_absolute_differences
    """

    def flush(self):
        super(PiMotionArray, self).flush()
        width, height = self.size or self.camera.resolution
        cols = ((width + 15) // 16) + 1
        rows = (height + 15) // 16
        frames = len(self.buffer) // (cols * rows * motion_dtype.itemsize)
        self.array = np.frombuffer(self.buffer, dtype=motion_dtype).\
                reshape((frames, rows, cols))


class PiMotionAnalysis(PiBaseOutput):
    """
    Provides a basis for real-time motion analysis classes.

    This custom output class is intended to be used with the *motion_output*
    parameter of the :meth:`~picamera.PiCamera.start_recording` method. While
    recording is in progress, the write method converts incoming motion data
    into numpy arrays and calls the stub :meth:`analyse` method with the
    resulting array (which deliberately raises :exc:`NotImplementedError`
    in this class).

    .. warning::

        Because the :meth:`analyse` method will be running within the encoder's
        callback, it must be **fast**. Specifically, it needs to return before
        the next frame is produced. Therefore, if the camera is running at
        30fps, analyse cannot take more than 1/30s or 33ms to execute (and
        should take considerably less given that this doesn't take into account
        encoding overhead). You may wish to adjust the framerate of the camera
        accordingly.

    The array passed to :meth:`analyse` is organized as (rows, columns) where
    ``rows`` and ``columns`` are the number of rows and columns of
    `macro-blocks`_ (16x16 pixel blocks) in the original frames. There is
    always one extra column of macro-blocks present in motion vector data.

    The data-type of the array is an (x, y, sad) structure where ``x`` and
    ``y`` are signed 1-byte values, and ``sad`` is an unsigned 2-byte value
    representing the `sum of absolute differences`_ of the block.

    An example of a crude motion detector is given below::

        import numpy as np
        import picamera
        import picamera.array

        class DetectMotion(picamera.array.PiMotionAnalysis):
            def analyse(self, a):
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
        if self.cols is None:
            width, height = self.size or self.camera.resolution
            self.cols = ((width + 15) // 16) + 1
            self.rows = (height + 15) // 16
        self.analyse(
                np.frombuffer(b, dtype=motion_dtype).\
                reshape((self.rows, self.cols)))
        return len(b)

    def analyse(self, array):
        """
        Stub method for users to override.
        """
        raise NotImplementedError

    def tell(self):
        raise NotImplementedError

    def truncate(self, size=None):
        raise NotImplementedError
