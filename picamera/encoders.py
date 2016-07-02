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
str = type('')
try:
    range = xrange
except NameError:
    pass

import io
import datetime
import threading
import warnings
import ctypes as ct

from . import mmal, mmalobj as mo
from .frames import PiVideoFrame, PiVideoFrameType
from .streams import BufferIO
from .exc import (
    mmal_check,
    PiCameraError,
    PiCameraMMALError,
    PiCameraValueError,
    PiCameraRuntimeError,
    PiCameraResizerEncoding,
    PiCameraAlphaStripping,
    PiCameraResolutionRounded,
    )


class PiEncoder(object):
    """
    Base implementation of an MMAL encoder for use by PiCamera.

    The *parent* parameter specifies the :class:`PiCamera` instance that has
    constructed the encoder. The *camera_port* parameter provides the MMAL
    camera port that the encoder should enable for capture (this will be the
    still or video port of the camera component). The *input_port* parameter
    specifies the MMAL port that the encoder should connect to its input.
    Sometimes this will be the same as the camera port, but if other components
    are present in the pipeline (e.g. a splitter), it may be different.

    The *format* parameter specifies the format that the encoder should
    produce in its output. This is specified as a string and will be one of
    the following for image encoders:

    * ``'jpeg'``
    * ``'png'``
    * ``'gif'``
    * ``'bmp'``
    * ``'yuv'``
    * ``'rgb'``
    * ``'rgba'``
    * ``'bgr'``
    * ``'bgra'``

    And one of the following for video encoders:

    * ``'h264'``
    * ``'mjpeg'``

    The *resize* parameter is either ``None`` (indicating no resizing
    should take place), or a ``(width, height)`` tuple specifying the
    resolution that the output of the encoder should be resized to.

    Finally, the *options* parameter specifies additional keyword arguments
    that can be used to configure the encoder (e.g. bitrate for videos, or
    quality for images).

    .. attribute:: camera_port

        The :class:`~mmalobj.MMALVideoPort` that needs to be activated and
        deactivated in order to start/stop capture. This is not necessarily the
        port that the encoder component's input port is connected to (for
        example, in the case of video-port based captures, this will be the
        camera video port behind the splitter).

    .. attribute:: encoder

        The :class:`~mmalobj.MMALComponent` representing the encoder, or
        ``None`` if no encoder component has been created (some encoder classes
        don't use an actual encoder component, for example
        :class:`PiRawImageMixin`).

    .. attribute:: event

        A :class:`threading.Event` instance used to synchronize operations
        (like start, stop, and split) between the control thread and the
        callback thread.

    .. attribute:: exception

        If an exception occurs during the encoder callback, this attribute is
        used to store the exception until it can be re-raised in the control
        thread.

    .. attribute:: format

        The image or video format that the encoder is expected to produce. This
        is equal to the value of the *format* parameter.

    .. attribute:: input_port

        The :class:`~mmalobj.MMALVideoPort` that the encoder should be
        connected to.

    .. attribute:: output_port

        The :class:`~mmalobj.MMALVideoPort` that produces the encoder's output.
        In the case no encoder component is created, this should be the
        camera/component output port responsible for producing data. In other
        words, this attribute **must** be set on initialization.

    .. attribute:: outputs

        A mapping of ``key`` to ``(output, opened)`` tuples where ``output``
        is a file-like object, and ``opened`` is a bool indicating whether or
        not we opened the output object (and thus whether we are responsible
        for eventually closing it).

    .. attribute:: outputs_lock

        A :func:`threading.Lock` instance used to protect access to
        :attr:`outputs`.

    .. attribute:: parent

        The :class:`PiCamera` instance that created this PiEncoder instance.

    .. attribute:: pool

        A pointer to a pool of MMAL buffers.

    .. attribute:: resizer

        The :class:`~mmalobj.MMALResizer` component, or ``None`` if no resizer
        component has been created.
    """

    DEBUG = 0
    encoder_type = None

    def __init__(
            self, parent, camera_port, input_port, format, resize, **options):
        self.parent = parent
        self.encoder = None
        self.resizer = None
        self.camera_port = camera_port
        self.input_port = input_port
        self.output_port = None
        self.outputs_lock = threading.Lock() # protects access to self.outputs
        self.outputs = {}
        self.exception = None
        self.event = threading.Event()
        try:
            if parent.closed:
                raise PiCameraRuntimeError("Camera is closed")
            if resize:
                self._create_resizer(*resize)
            self._create_encoder(format, **options)
            if self.encoder:
                if self.resizer:
                    self.encoder.connect(self.resizer.outputs[0])
                else:
                    self.encoder.connect(self.input_port)
        except:
            self.close()
            raise

    def _create_resizer(self, width, height):
        """
        Creates and configures an :class:`~mmalobj.MMALResizer` component.

        This is called when the initializer's *resize* parameter is something
        other than ``None``. The *width* and *height* parameters are passed to
        the constructed resizer. Note that this method only constructs the
        resizer - it does not connect it to the encoder. The method sets the
        :attr:`resizer` attribute to the constructed resizer component.
        """
        self.resizer = mo.MMALResizer()
        self.resizer.connect(self.input_port)
        self.resizer.outputs[0].copy_from(self.resizer.inputs[0])
        self.resizer.outputs[0].format = mmal.MMAL_ENCODING_I420
        self.resizer.outputs[0].framesize = (width, height)
        self.resizer.outputs[0].commit()

    def _create_encoder(self, format):
        """
        Creates and configures the :class:`~mmalobj.MMALEncoder` component.

        This method only constructs the encoder; it does not connect it to the
        input port. The method sets the :attr:`encoder` attribute to the
        constructed encoder component, and the :attr:`output_port` attribute to
        the encoder's output port (or the previously constructed resizer's
        output port if one has been requested). Descendent classes extend this
        method to finalize encoder configuration.

        .. note::

            It should be noted that this method is called with the
            initializer's ``option`` keyword arguments. This base
            implementation expects no additional arguments, but descendent
            classes extend the parameter list to include options relevant to
            them.
        """
        assert not self.encoder
        self.encoder = self.encoder_type()
        self.output_port = self.encoder.outputs[0]
        if self.resizer:
            self.encoder.inputs[0].copy_from(self.resizer.outputs[0])
        else:
            self.encoder.inputs[0].copy_from(self.input_port)
        self.encoder.outputs[0].copy_from(self.encoder.inputs[0])
        # NOTE: We deliberately don't commit the output port format here as
        # this is a base class and the output configuration is incomplete at
        # this point. Descendents are expected to finish configuring the
        # encoder and then commit the port format themselves

    def _callback(self, port, buf):
        """
        The encoder's main callback function.

        When the encoder is active, this method is periodically called in a
        background thread. The *port* parameter specifies the :class:`MMALPort`
        providing the output (typically this is the encoder's output port, but
        in the case of unencoded captures may simply be a camera port), while
        the *buf* parameter is an :class:`~mmalobj.MMALBuffer` which can be
        used to obtain the data to write, along with meta-data about the
        current frame.

        This method must set :attr:`event` when the encoder has finished (and
        should set :attr:`exception` if an exception occurred during encoding).

        Developers wishing to write a custom encoder class may find it simpler
        to override the :meth:`_callback_write` method, rather than deal with
        these complexities.
        """
        if self.DEBUG > 1:
            print(repr(buf))
        try:
            stop = self._callback_write(buf)
        except Exception as e:
            stop = True
            self.exception = e
        if stop:
            self.event.set()
        return stop

    def _callback_write(self, buf, key=PiVideoFrameType.frame):
        """
        Writes output on behalf of the encoder callback function.

        This method is called by :meth:`_callback` to handle writing to an
        object in :attr:`outputs` identified by *key*. The *buf* parameter is
        an :class:`~mmalobj.MMALBuffer` which can be used to obtain the data.
        The method is expected to return a boolean to indicate whether output
        is complete (``True``) or whether more data is expected (``False``).

        The default implementation simply writes the contents of the buffer to
        the output identified by *key*, and returns ``True`` if the buffer
        flags indicate end of stream. Image encoders will typically override
        the return value to indicate ``True`` on end of frame (as they only
        wish to output a single image). Video encoders will typically override
        this method to determine where key-frames and SPS headers occur.
        """
        if buf.length:
            with self.outputs_lock:
                try:
                    output = self.outputs[key][0]
                    written = output.write(buf.data)
                except KeyError:
                    # No output associated with the key type; discard the
                    # data
                    pass
                else:
                    # Ignore None return value; most Python 2 streams have
                    # no return value for write()
                    if (written is not None) and (written != buf.length):
                        raise PiCameraError(
                            "Failed to write %d bytes from buffer to "
                            "output %r" % (buf.length, output))
        return bool(buf.flags & mmal.MMAL_BUFFER_HEADER_FLAG_EOS)

    def _open_output(self, output, key=PiVideoFrameType.frame):
        """
        Opens *output* and associates it with *key* in :attr:`outputs`.

        If *output* is a string, this method opens it as a filename and keeps
        track of the fact that the encoder was the one to open it (which
        implies that :meth:`_close_output` should eventually close it).
        Otherwise, if *output* has a ``write`` method it is assumed to be a
        file-like object and it is used verbatim. If *output* is neither a
        string, nor an object with a ``write`` method it is assumed to be a
        writeable object supporting the buffer protocol (this is wrapped in
        a :class:`BufferIO` stream to simplify writing).

        The opened output is added to the :attr:`outputs` dictionary with the
        specified *key*.
        """
        with self.outputs_lock:
            opened = isinstance(output, (bytes, str))
            if opened:
                # Open files in binary mode with a decent buffer size
                output = io.open(output, 'wb', buffering=65536)
            else:
                try:
                    output.write
                except AttributeError:
                    # If there's no write method, try and treat the output as
                    # a writeable buffer
                    opened = True
                    output = BufferIO(output)
            self.outputs[key] = (output, opened)

    def _close_output(self, key=PiVideoFrameType.frame):
        """
        Closes the output associated with *key* in :attr:`outputs`.

        Closes the output object associated with the specified *key*, and
        removes it from the :attr:`outputs` dictionary (if we didn't open the
        object then we attempt to flush it instead).
        """
        with self.outputs_lock:
            try:
                (output, opened) = self.outputs.pop(key)
            except KeyError:
                pass
            else:
                if opened:
                    output.close()
                else:
                    try:
                        output.flush()
                    except AttributeError:
                        pass

    @property
    def active(self):
        """
        Returns ``True`` if the MMAL encoder exists and is enabled.
        """
        return bool(self.output_port and self.output_port.enabled)

    def start(self, output):
        """
        Starts the encoder object writing to the specified output.

        This method is called by the camera to start the encoder capturing
        data from the camera to the specified output. The *output* parameter
        is either a filename, or a file-like object (for image and video
        encoders), or an iterable of filenames or file-like objects (for
        multi-image encoders).
        """
        if self.DEBUG > 0:
            mo.print_pipeline(self.output_port)
        self.event.clear()
        self.exception = None
        self._open_output(output)
        with self.parent._encoders_lock:
            self.output_port.enable(self._callback)
            self.parent._start_capture(self.camera_port)

    def wait(self, timeout=None):
        """
        Waits for the encoder to finish (successfully or otherwise).

        This method is called by the owning camera object to block execution
        until the encoder has completed its task. If the *timeout* parameter
        is None, the method will block indefinitely. Otherwise, the *timeout*
        parameter specifies the (potentially fractional) number of seconds
        to block for. If the encoder finishes successfully within the timeout,
        the method returns ``True``. Otherwise, it returns ``False``.
        """
        result = self.event.wait(timeout)
        if result:
            self.stop()
            # Check whether the callback set an exception
            if self.exception:
                raise self.exception
        return result

    def stop(self):
        """
        Stops the encoder, regardless of whether it's finished.

        This method is called by the camera to terminate the execution of the
        encoder. Typically, this is used with video to stop the recording, but
        can potentially be called in the middle of image capture to terminate
        the capture.
        """
        # The check below is not a race condition; we ignore the EINVAL error
        # in the case the port turns out to be disabled when we disable below.
        # The check exists purely to prevent stderr getting spammed by our
        # continued attempts to disable an already disabled port. Lock
        # acquisition must occur after the check to avoid re-acquiring a
        # non-re-entrant lock in certain conditions (e.g. encoder destruction
        # from __init__, when the lock is held by the same thread)
        if self.active:
            with self.parent._encoders_lock:
                self.parent._stop_capture(self.camera_port)
                try:
                    self.output_port.disable()
                except PiCameraMMALError as e:
                    if e.status != mmal.MMAL_EINVAL:
                        raise
        self.event.set()
        self._close_output()

    def close(self):
        """
        Finalizes the encoder and deallocates all structures.

        This method is called by the camera prior to destroying the encoder (or
        more precisely, letting it go out of scope to permit the garbage
        collector to destroy it at some future time). The method destroys all
        components that the various create methods constructed and resets their
        attributes.
        """
        self.stop()
        if self.encoder:
            self.encoder.disconnect()
        if self.resizer:
            self.resizer.disconnect()
        if self.encoder:
            self.encoder.close()
            self.encoder = None
        if self.resizer:
            self.resizer.close()
            self.resizer = None
        self.output_port = None


class PiRawMixin(PiEncoder):
    """
    Mixin class for "raw" (unencoded) output.

    This mixin class overrides the initializer of :class:`PiEncoder`, along
    with :meth:`_create_resizer` and :meth:`_create_encoder` to configure the
    pipeline for unencoded output. Specifically, it disables the construction
    of an encoder, and sets the output port to the input port passed to the
    initializer, unless resizing is required (either for actual resizing, or
    for format conversion) in which case the resizer's output is used.
    """

    RAW_ENCODINGS = {
        # name   mmal-encoding             bytes-per-pixel
        'yuv':  (mmal.MMAL_ENCODING_I420,  1.5),
        'rgb':  (mmal.MMAL_ENCODING_RGB24, 3),
        'rgba': (mmal.MMAL_ENCODING_RGBA,  4),
        'bgr':  (mmal.MMAL_ENCODING_BGR24, 3),
        'bgra': (mmal.MMAL_ENCODING_BGRA,  4),
        }

    def __init__(
            self, parent, camera_port, input_port, format, resize, **options):
        encoding, bpp = self.RAW_ENCODINGS[format]
        # Workaround: on older firmwares, non-YUV encodings aren't supported on
        # the still port. If a non-YUV format is requested without resizing,
        # test whether we can commit the requested format on the input port and
        # if this fails, set resize to force resizer usage
        if resize is None and encoding != mmal.MMAL_ENCODING_I420:
            input_port.format = encoding
            try:
                input_port.commit()
            except PiCameraMMALError as e:
                if e.status != mmal.MMAL_EINVAL:
                    raise
                resize = parent.resolution
                warnings.warn(
                    PiCameraResizerEncoding(
                        "using a resizer to perform non-YUV encoding; "
                        "upgrading your firmware with sudo rpi-update "
                        "may improve performance"))
        # Workaround: If a non-alpha format is requested with the resizer, use
        # the alpha-inclusive format and set a flag to get the callback to
        # strip the alpha bytes
        self._strip_alpha = False
        if resize:
            width, height = resize
            try:
                format = {
                    'rgb': 'rgba',
                    'bgr': 'bgra',
                    }[format]
                self._strip_alpha = True
                warnings.warn(
                    PiCameraAlphaStripping(
                        "using alpha-stripping to convert to non-alpha "
                        "format; you may find the equivalent alpha format "
                        "faster"))
            except KeyError:
                pass
        else:
            width, height = parent.resolution
        # Workaround (#83): when the resizer is used the width must be aligned
        # (both the frame and crop values) to avoid an error when the output
        # port format is set (height is aligned too, simply for consistency
        # with old picamera versions). Warn the user as they're not going to
        # get the resolution they expect
        if not resize and format != 'yuv' and input_port.name.startswith(b'vc.ril.video_splitter'):
            # Workaround: Expected frame size is rounded to 16x16 when splitter
            # port with no resizer is used and format is not YUV
            fwidth = mmal.VCOS_ALIGN_UP(width, 16)
        else:
            fwidth = mmal.VCOS_ALIGN_UP(width, 32)
        fheight = mmal.VCOS_ALIGN_UP(height, 16)
        if fwidth != width or fheight != height:
            warnings.warn(
                PiCameraResolutionRounded(
                    "frame size rounded up from %dx%d to %dx%d" % (
                        width, height, fwidth, fheight)))
        if resize:
            resize = (fwidth, fheight)
        # Workaround: Calculate the expected frame size, to be used by the
        # callback to decide when a frame ends. This is to work around a
        # firmware bug that causes the raw image to be returned twice when the
        # maximum camera resolution is requested
        self._frame_size = int(fwidth * fheight * bpp)
        super(PiRawMixin, self).__init__(
                parent, camera_port, input_port, format, resize, **options)

    def _create_encoder(self, format):
        """
        Overridden to skip creating an encoder. Instead, this class simply uses
        the resizer's port as the output port (if a resizer has been
        configured) or the specified input port otherwise.
        """
        if self.resizer:
            self.output_port = self.resizer.outputs[0]
        else:
            self.output_port = self.input_port
        self.output_port.format = self.RAW_ENCODINGS[format][0]
        self.output_port.commit()

    def _callback_write(self, buf, key=PiVideoFrameType.frame):
        """
        Overridden to strip alpha bytes when required.
        """
        if self._strip_alpha:
            s = bytearray(buf.data)
            del s[3::4]
            new_buf = buf.copy(s)
            return super(PiRawMixin, self)._callback_write(new_buf, key)
        else:
            return super(PiRawMixin, self)._callback_write(buf, key)


class PiVideoEncoder(PiEncoder):
    """
    Encoder for video recording.

    This derivative of :class:`PiEncoder` configures itself for H.264 or MJPEG
    encoding.  It also introduces a :meth:`split` method which is used by
    :meth:`~PiCamera.split_recording` and :meth:`~PiCamera.record_sequence` to
    redirect future output to a new filename or object. Finally, it also
    extends :meth:`PiEncoder.start` and :meth:`PiEncoder._callback_write` to
    track video frame meta-data, and to permit recording motion data to a
    separate output object.
    """

    encoder_type = mo.MMALVideoEncoder

    def __init__(
            self, parent, camera_port, input_port, format, resize, **options):
        super(PiVideoEncoder, self).__init__(
                parent, camera_port, input_port, format, resize, **options)
        self._next_output = []
        self.frame = None

    def _create_encoder(
            self, format, bitrate=17000000, intra_period=None, profile='high',
            quantization=0, quality=0, inline_headers=True, sei=False,
            motion_output=None, intra_refresh=None, level='4'):
        """
        Extends the base :meth:`~PiEncoder._create_encoder` implementation to
        configure the video encoder for H.264 or MJPEG output.
        """
        super(PiVideoEncoder, self)._create_encoder(format)

        # XXX Remove quantization in 2.0
        quality = quality or quantization

        try:
            self.output_port.format = {
                'h264':  mmal.MMAL_ENCODING_H264,
                'mjpeg': mmal.MMAL_ENCODING_MJPEG,
                }[format]
        except KeyError:
            raise PiCameraValueError('Unsupported format %s' % format)

        limit = 62500000 if format == 'h264' and level == '4.2' else 25000000
        if not (0 <= bitrate <= limit):
            raise PiCameraValueError(
                'bitrate must be between 0 and %.1fMbps' % (bitrate / 1000000))
        self.output_port.bitrate = bitrate
        self.output_port.framerate = 0
        self.output_port.commit()

        if format == 'h264':
            limit = 522240 if level == '4.2' else 245760
            w, h = self.output_port.framesize
            w = mmal.VCOS_ALIGN_UP(w, 16) >> 4
            h = mmal.VCOS_ALIGN_UP(h, 16) >> 4
            if w * h * (self.parent.framerate + self.parent.framerate_delta) > limit:
                raise PiCameraValueError(
                    'too many macroblocks/s requested; reduce resolution or '
                    'framerate')
            mp = mmal.MMAL_PARAMETER_VIDEO_PROFILE_T(
                    mmal.MMAL_PARAMETER_HEADER_T(
                        mmal.MMAL_PARAMETER_PROFILE,
                        ct.sizeof(mmal.MMAL_PARAMETER_VIDEO_PROFILE_T),
                        ),
                    )
            try:
                mp.profile[0].profile = {
                    'baseline':    mmal.MMAL_VIDEO_PROFILE_H264_BASELINE,
                    'main':        mmal.MMAL_VIDEO_PROFILE_H264_MAIN,
                    'high':        mmal.MMAL_VIDEO_PROFILE_H264_HIGH,
                    'constrained': mmal.MMAL_VIDEO_PROFILE_H264_CONSTRAINED_BASELINE,
                    }[profile]
            except KeyError:
                raise PiCameraValueError("Invalid H.264 profile %s" % profile)
            try:
                mp.profile[0].level = {
                    '4':   mmal.MMAL_VIDEO_LEVEL_H264_4,
                    '4.1': mmal.MMAL_VIDEO_LEVEL_H264_41,
                    '4.2': mmal.MMAL_VIDEO_LEVEL_H264_42,
                    }[level]
            except KeyError:
                raise PiCameraValueError("Invalid H.264 level %s" % level)
            self.output_port.params[mmal.MMAL_PARAMETER_PROFILE] = mp

            if inline_headers:
                self.output_port.params[mmal.MMAL_PARAMETER_VIDEO_ENCODE_INLINE_HEADER] = True
            if sei:
                self.output_port.params[mmal.MMAL_PARAMETER_VIDEO_ENCODE_SEI_ENABLE] = True
            if motion_output is not None:
                self.output_port.params[mmal.MMAL_PARAMETER_VIDEO_ENCODE_INLINE_VECTORS] = True

            # We need the intra-period to calculate the SPS header timeout in
            # the split method below. If one is not set explicitly, query the
            # encoder's default
            if intra_period is not None:
                self.output_port.params[mmal.MMAL_PARAMETER_INTRAPERIOD] = intra_period
                self._intra_period = intra_period
            else:
                self._intra_period = self.output_port.params[mmal.MMAL_PARAMETER_INTRAPERIOD]

            if intra_refresh is not None:
                # Get the intra-refresh structure first as there are several
                # other fields in it which we don't wish to overwrite
                mp = self.output_port.params[mmal.MMAL_PARAMETER_VIDEO_INTRA_REFRESH]
                try:
                    mp.refresh_mode = {
                        'cyclic':     mmal.MMAL_VIDEO_INTRA_REFRESH_CYCLIC,
                        'adaptive':   mmal.MMAL_VIDEO_INTRA_REFRESH_ADAPTIVE,
                        'both':       mmal.MMAL_VIDEO_INTRA_REFRESH_BOTH,
                        'cyclicrows': mmal.MMAL_VIDEO_INTRA_REFRESH_CYCLIC_MROWS,
                        }[intra_refresh]
                except KeyError:
                    raise PiCameraValueError(
                        "Invalid intra_refresh %s" % intra_refresh)
                self.output_port.params[mmal.MMAL_PARAMETER_VIDEO_INTRA_REFRESH] = mp

        elif format == 'mjpeg':
            # MJPEG doesn't have an intra_period setting as such, but as every
            # frame is a full-frame, the intra_period is effectively 1
            self._intra_period = 1

        if quality:
            self.output_port.params[mmal.MMAL_PARAMETER_VIDEO_ENCODE_INITIAL_QUANT] = quality
            self.output_port.params[mmal.MMAL_PARAMETER_VIDEO_ENCODE_MIN_QUANT] = quality
            self.output_port.params[mmal.MMAL_PARAMETER_VIDEO_ENCODE_MAX_QUANT] = quality

        self.encoder.inputs[0].params[mmal.MMAL_PARAMETER_VIDEO_IMMUTABLE_INPUT] = True
        self.encoder.enabled = True

    def start(self, output, motion_output=None):
        """
        Extended to initialize video frame meta-data tracking.
        """
        self.frame = PiVideoFrame(
                index=0,
                frame_type=None,
                frame_size=0,
                video_size=0,
                split_size=0,
                timestamp=0,
                complete=False,
                )
        if motion_output is not None:
            self._open_output(motion_output, PiVideoFrameType.motion_data)
        super(PiVideoEncoder, self).start(output)

    def stop(self):
        super(PiVideoEncoder, self).stop()
        self._close_output(PiVideoFrameType.motion_data)

    def request_key_frame(self):
        """
        Called to request an I-frame from the encoder.

        This method is called by :meth:`~PiCamera.request_key_frame` and
        :meth:`split` to force the encoder to output an I-frame as soon as
        possible.
        """
        self.encoder.control.params[mmal.MMAL_PARAMETER_VIDEO_REQUEST_I_FRAME] = True

    def split(self, output, motion_output=None):
        """
        Called to switch the encoder's output.

        This method is called by :meth:`~PiCamera.split_recording` and
        :meth:`~PiCamera.record_sequence` to switch the encoder's
        :attr:`output` object to the *output* parameter (which can be a
        filename or a file-like object, as with :meth:`start`).
        """
        with self.outputs_lock:
            outputs = {}
            if output is not None:
                outputs[PiVideoFrameType.frame] = output
            if motion_output is not None:
                outputs[PiVideoFrameType.motion_data] = motion_output
            self._next_output.append(outputs)
        # intra_period / framerate gives the time between I-frames (which
        # should also coincide with SPS headers). We multiply by three to
        # ensure the timeout is deliberately excessive, and clamp the minimum
        # timeout to 10 seconds (otherwise unencoded formats tend to fail
        # presumably due to I/O capacity)
        timeout = max(10.0, float(self._intra_period / self.parent.framerate) * 3.0)
        if self._intra_period > 1:
            self.request_key_frame()
        if not self.event.wait(timeout):
            raise PiCameraRuntimeError('Timed out waiting for a split point')
        self.event.clear()

    def _callback_write(self, buf, key=PiVideoFrameType.frame):
        """
        Extended to implement video frame meta-data tracking, and to handle
        splitting video recording to the next output when :meth:`split` is
        called.
        """
        self.frame = PiVideoFrame(
            index=
                self.frame.index + 1
                if self.frame.complete else
                self.frame.index,
            frame_type=
                PiVideoFrameType.key_frame
                if buf.flags & mmal.MMAL_BUFFER_HEADER_FLAG_KEYFRAME else
                PiVideoFrameType.sps_header
                if buf.flags & mmal.MMAL_BUFFER_HEADER_FLAG_CONFIG else
                PiVideoFrameType.motion_data
                if buf.flags & mmal.MMAL_BUFFER_HEADER_FLAG_CODECSIDEINFO else
                PiVideoFrameType.frame,
            frame_size=
                buf.length
                if self.frame.complete else
                self.frame.frame_size + buf.length,
            video_size=
                self.frame.video_size
                if buf.flags & mmal.MMAL_BUFFER_HEADER_FLAG_CODECSIDEINFO else
                self.frame.video_size + buf.length,
            split_size=
                self.frame.split_size
                if buf.flags & mmal.MMAL_BUFFER_HEADER_FLAG_CODECSIDEINFO else
                self.frame.split_size + buf.length,
            timestamp=
                None
                if buf.pts in (0, mmal.MMAL_TIME_UNKNOWN) else
                buf.pts,
            complete=
                bool(buf.flags & mmal.MMAL_BUFFER_HEADER_FLAG_FRAME_END),
            )
        if self._intra_period == 1 or (buf.flags & mmal.MMAL_BUFFER_HEADER_FLAG_CONFIG):
            with self.outputs_lock:
                try:
                    new_outputs = self._next_output.pop(0)
                except IndexError:
                    new_outputs = None
            if new_outputs:
                for new_key, new_output in new_outputs.items():
                    self._close_output(new_key)
                    self._open_output(new_output, new_key)
                    if new_key == PiVideoFrameType.frame:
                        self.frame = PiVideoFrame(
                                index=self.frame.index,
                                frame_type=self.frame.frame_type,
                                frame_size=self.frame.frame_size,
                                video_size=self.frame.video_size,
                                split_size=0,
                                timestamp=self.frame.timestamp,
                                complete=self.frame.complete,
                                )
                self.event.set()
        if buf.flags & mmal.MMAL_BUFFER_HEADER_FLAG_CODECSIDEINFO:
            key = PiVideoFrameType.motion_data
        return super(PiVideoEncoder, self)._callback_write(buf, key)


class PiCookedVideoEncoder(PiVideoEncoder):
    """
    Video encoder for encoded recordings.

    This class is a derivative of :class:`PiVideoEncoder` and only exists to
    provide naming symmetry with the image encoder classes.
    """


class PiRawVideoEncoder(PiRawMixin, PiVideoEncoder):
    """
    Video encoder for unencoded recordings.

    This class is a derivative of :class:`PiVideoEncoder` and the
    :class:`PiRawMixin` class intended for use with
    :meth:`~PiCamera.start_recording` when it is called with an unencoded
    format.

    .. warning::

        This class creates an inheritance diamond. Take care to determine the
        MRO of super-class calls.
    """

    def _create_encoder(self, format):
        super(PiRawVideoEncoder, self)._create_encoder(format)
        # Raw formats don't have an intra_period setting as such, but as every
        # frame is a full-frame, the intra_period is effectively 1
        self._intra_period = 1


class PiImageEncoder(PiEncoder):
    """
    Encoder for image capture.

    This derivative of :class:`PiEncoder` extends the :meth:`_create_encoder`
    method to configure the encoder for a variety of encoded image outputs
    (JPEG, PNG, etc.).
    """

    encoder_type = mo.MMALImageEncoder

    def _create_encoder(self, format, quality=85, thumbnail=(64, 48, 35)):
        """
        Extends the base :meth:`~PiEncoder._create_encoder` implementation to
        configure the image encoder for JPEG, PNG, etc.
        """
        super(PiImageEncoder, self)._create_encoder(format)

        try:
            self.output_port.format = {
                'jpeg': mmal.MMAL_ENCODING_JPEG,
                'png':  mmal.MMAL_ENCODING_PNG,
                'gif':  mmal.MMAL_ENCODING_GIF,
                'bmp':  mmal.MMAL_ENCODING_BMP,
                }[format]
        except KeyError:
            raise PiCameraValueError("Unsupported format %s" % format)
        self.output_port.commit()

        if format == 'jpeg':
            self.output_port.params[mmal.MMAL_PARAMETER_JPEG_Q_FACTOR] = quality
            if thumbnail is None:
                mp = mmal.MMAL_PARAMETER_THUMBNAIL_CONFIG_T(
                    mmal.MMAL_PARAMETER_HEADER_T(
                        mmal.MMAL_PARAMETER_THUMBNAIL_CONFIGURATION,
                        ct.sizeof(mmal.MMAL_PARAMETER_THUMBNAIL_CONFIG_T)
                        ),
                    0, 0, 0, 0)
            else:
                mp = mmal.MMAL_PARAMETER_THUMBNAIL_CONFIG_T(
                    mmal.MMAL_PARAMETER_HEADER_T(
                        mmal.MMAL_PARAMETER_THUMBNAIL_CONFIGURATION,
                        ct.sizeof(mmal.MMAL_PARAMETER_THUMBNAIL_CONFIG_T)
                        ),
                    1, *thumbnail)
            self.encoder.control.params[mmal.MMAL_PARAMETER_THUMBNAIL_CONFIGURATION] = mp

        self.encoder.enabled = True


class PiOneImageEncoder(PiImageEncoder):
    """
    Encoder for single image capture.

    This class simply extends :meth:`~PiEncoder._callback_write` to terminate
    capture at frame end (i.e. after a single frame has been received).
    """

    def _callback_write(self, buf, key=PiVideoFrameType.frame):
        return (
            super(PiOneImageEncoder, self)._callback_write(buf, key)
            ) or bool(
            buf.flags & (
                mmal.MMAL_BUFFER_HEADER_FLAG_FRAME_END |
                mmal.MMAL_BUFFER_HEADER_FLAG_TRANSMISSION_FAILED)
            )


class PiMultiImageEncoder(PiImageEncoder):
    """
    Encoder for multiple image capture.

    This class extends :class:`PiImageEncoder` to handle an iterable of outputs
    instead of a single output. The :meth:`~PiEncoder._callback_write` method
    is extended to terminate capture when the iterable is exhausted, while
    :meth:`PiEncoder._open_output` is overridden to begin iteration and rely
    on the new :meth:`_next_output` method to advance output to the next item
    in the iterable.
    """

    def _open_output(self, outputs, key=PiVideoFrameType.frame):
        self._output_iter = iter(outputs)
        self._next_output(key)

    def _next_output(self, key=PiVideoFrameType.frame):
        """
        This method moves output to the next item from the iterable passed to
        :meth:`~PiEncoder.start`.
        """
        self._close_output(key)
        super(PiMultiImageEncoder, self)._open_output(next(self._output_iter), key)

    def _callback_write(self, buf, key=PiVideoFrameType.frame):
        try:
            if (
                super(PiMultiImageEncoder, self)._callback_write(buf, key)
                ) or bool(
                buf.flags & (
                    mmal.MMAL_BUFFER_HEADER_FLAG_FRAME_END |
                    mmal.MMAL_BUFFER_HEADER_FLAG_TRANSMISSION_FAILED)
                ):
                self._next_output(key)
            return False
        except StopIteration:
            return True


class PiCookedOneImageEncoder(PiOneImageEncoder):
    """
    Encoder for "cooked" (encoded) single image output.

    This encoder extends :class:`PiOneImageEncoder` to include Exif tags in the
    output.
    """

    exif_encoding = 'ascii'

    def _add_exif_tag(self, tag, value):
        # Format the tag and value into an appropriate bytes string, encoded
        # with the Exif encoding (ASCII)
        if isinstance(tag, str):
            tag = tag.encode(self.exif_encoding)
        if isinstance(value, str):
            value = value.encode(self.exif_encoding)
        elif isinstance(value, datetime.datetime):
            value = value.strftime('%Y:%m:%d %H:%M:%S').encode(self.exif_encoding)
        # MMAL_PARAMETER_EXIF_T is a variable sized structure, hence all the
        # mucking about with string buffers here...
        buf = ct.create_string_buffer(
            ct.sizeof(mmal.MMAL_PARAMETER_EXIF_T) + len(tag) + len(value) + 1)
        mp = ct.cast(buf, ct.POINTER(mmal.MMAL_PARAMETER_EXIF_T))
        mp[0].hdr.id = mmal.MMAL_PARAMETER_EXIF
        mp[0].hdr.size = len(buf)
        if (b'=' in tag or b'\x00' in value):
            data = tag + value
            mp[0].keylen = len(tag)
            mp[0].value_offset = len(tag)
            mp[0].valuelen = len(value)
        else:
            data = tag + b'=' + value
        ct.memmove(mp[0].data, data, len(data))
        self.output_port.params[mmal.MMAL_PARAMETER_EXIF] = mp[0]

    def start(self, output):
        timestamp = datetime.datetime.now()
        timestamp_tags = (
            'EXIF.DateTimeDigitized',
            'EXIF.DateTimeOriginal',
            'IFD0.DateTime')
        # Timestamp tags are always included with the value calculated
        # above, but the user may choose to override the value in the
        # exif_tags mapping
        for tag in timestamp_tags:
            self._add_exif_tag(tag, self.parent.exif_tags.get(tag, timestamp))
        # All other tags are just copied in verbatim
        for tag, value in self.parent.exif_tags.items():
            if not tag in timestamp_tags:
                self._add_exif_tag(tag, value)
        super(PiCookedOneImageEncoder, self).start(output)


class PiCookedMultiImageEncoder(PiMultiImageEncoder):
    """
    Encoder for "cooked" (encoded) multiple image output.

    This encoder descends from :class:`PiMultiImageEncoder` but includes no
    new functionality as video-port based encodes (which is all this class
    is used for) don't support Exif tag output.
    """
    pass


class PiRawImageMixin(PiRawMixin, PiImageEncoder):
    """
    Mixin class for "raw" (unencoded) image capture.

    The :meth:`_callback_write` method is overridden to manually calculate when
    to terminate output.
    """

    def __init__(
            self, parent, camera_port, input_port, format, resize, **options):
        super(PiRawImageMixin, self).__init__(
                parent, camera_port, input_port, format, resize, **options)
        self._image_size = 0

    def _callback_write(self, buf, key=PiVideoFrameType.frame):
        """
        Overridden to manually calculate when to terminate capture (see
        comments in :meth:`__init__`).
        """
        if self._image_size > 0:
            super(PiRawImageMixin, self)._callback_write(buf, key)
            self._image_size -= buf.length
        return self._image_size <= 0

    def start(self, output):
        self._image_size = self._frame_size
        super(PiRawImageMixin, self).start(output)


class PiRawOneImageEncoder(PiOneImageEncoder, PiRawImageMixin):
    """
    Single image encoder for unencoded capture.

    This class is a derivative of :class:`PiOneImageEncoder` and the
    :class:`PiRawImageMixin` class intended for use with
    :meth:`~PiCamera.capture` (et al) when it is called with an unencoded image
    format.

    .. warning::

        This class creates an inheritance diamond. Take care to determine the
        MRO of super-class calls.
    """
    pass


class PiRawMultiImageEncoder(PiMultiImageEncoder, PiRawImageMixin):
    """
    Multiple image encoder for unencoded capture.

    This class is a derivative of :class:`PiMultiImageEncoder` and the
    :class:`PiRawImageMixin` class intended for use with
    :meth:`~PiCamera.capture_sequence` when it is called with an unencoded
    image format.

    .. warning::

        This class creates an inheritance diamond. Take care to determine the
        MRO of super-class calls.
    """
    def _next_output(self, key=PiVideoFrameType.frame):
        super(PiRawMultiImageEncoder, self)._next_output(key)
        self._image_size = self._frame_size

