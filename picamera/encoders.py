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
from collections import namedtuple

import picamera.mmal as mmal
from picamera.exc import (
    mmal_check,
    PiCameraWarning,
    PiCameraError,
    PiCameraMMALError,
    PiCameraValueError,
    PiCameraRuntimeError,
    )


__all__ = [
    'PiEncoder',
    'PiVideoEncoder',
    'PiImageEncoder',
    'PiRawImageEncoder',
    'PiOneImageEncoder',
    'PiMultiImageEncoder',
    ]


class PiVideoFrame(namedtuple('PiVideoFrame', (
    'index',         # the frame number, where the first frame is 0
    'keyframe',      # True when the frame is a keyframe
    'frame_size',    # the size (in bytes) of the frame's data
    'video_size',    # the size (in bytes) of the video so far
    'split_size',    # the size (in bytes) of the video since the last split
    'timestamp',     # the presentation timestamp (PTS) of the frame
    'header',        # the frame is an SPS/PPS header
    ))):

    @property
    def position(self):
        return self.split_size - self.frame_size


def _encoder_callback(port, buf):
    encoder = ct.cast(port[0].userdata, ct.POINTER(ct.py_object))[0]
    encoder._callback(port, buf)
_encoder_callback = mmal.MMAL_PORT_BH_CB_T(_encoder_callback)


class PiEncoder(object):
    """
    Abstract base implemetation of an MMAL encoder for use by PiCamera
    """

    encoder_type = None

    def __init__(
            self, parent, camera_port, input_port, format, resize, **options):
        self.parent = parent
        self.format = format
        self.encoder = None
        self.resizer = None
        self.encoder_connection = None
        self.resizer_connection = None
        self.camera_port = camera_port
        self.input_port = input_port
        self.output_port = None
        self.pool = None
        self.started_capture = False
        self.opened_output = False
        self.output = None
        self.lock = threading.Lock() # protects access to self.output
        self.exception = None
        self.event = threading.Event()
        self.stopped = True
        try:
            if parent.closed:
                raise PiCameraRuntimeError("Camera is closed")
            if resize:
                self._create_resizer(*resize)
            self._create_encoder(**options)
            self._create_pool()
            self._create_connection()
        except:
            self.close()
            raise

    def _create_encoder(self):
        """
        Creates and configures the encoder itself
        """
        assert not self.encoder
        self.encoder = ct.POINTER(mmal.MMAL_COMPONENT_T)()
        mmal_check(
            mmal.mmal_component_create(self.encoder_type, self.encoder),
            prefix="Failed to create encoder component")
        if not self.encoder[0].input_num:
            raise PiCameraError("No input ports on encoder component")
        if not self.encoder[0].output_num:
            raise PiCameraError("No output ports on encoder component")
        # Ensure output format is the same as the input
        self.output_port = self.encoder[0].output[0]
        if self.resizer:
            mmal.mmal_format_copy(
                self.encoder[0].input[0][0].format, self.resizer[0].output[0][0].format)
        else:
            mmal.mmal_format_copy(
                self.encoder[0].input[0][0].format, self.input_port[0].format)
        mmal_check(
            mmal.mmal_port_format_commit(self.encoder[0].input[0]),
            prefix="Failed to set encoder input port format")
        mmal.mmal_format_copy(
            self.output_port[0].format, self.encoder[0].input[0][0].format)
        # Set buffer size and number to appropriate values
        self.output_port[0].buffer_size = max(
            self.output_port[0].buffer_size_recommended,
            self.output_port[0].buffer_size_min)
        self.output_port[0].buffer_num = max(
            self.output_port[0].buffer_num_recommended,
            self.output_port[0].buffer_num_min)
        # NOTE: We deliberately don't commit the output port format here as
        # this is a base class and the output configuration is incomplete at
        # this point. Descendents are expected to finish configuring the
        # encoder and then commit the port format themselves

    def _create_resizer(self, width, height):
        self.resizer = ct.POINTER(mmal.MMAL_COMPONENT_T)()
        mmal_check(
            mmal.mmal_component_create(
                mmal.MMAL_COMPONENT_DEFAULT_RESIZER, self.resizer),
            prefix="Failed to create resizer component")
        if not self.resizer[0].input_num:
            raise PiCameraError("No input ports on resizer component")
        if not self.resizer[0].output_num:
            raise PiCameraError("No output ports on resizer component")
        # Copy the original input port's format to the resizer's input,
        # then the resizer's input format to the output, and configure it
        mmal.mmal_format_copy(
            self.resizer[0].input[0][0].format, self.input_port[0].format)
        mmal_check(
            mmal.mmal_port_format_commit(self.resizer[0].input[0]),
            prefix="Failed to set resizer input port format")
        mmal.mmal_format_copy(
            self.resizer[0].output[0][0].format, self.resizer[0].input[0][0].format)
        fmt = self.resizer[0].output[0][0].format
        fmt[0].es[0].video.width = mmal.VCOS_ALIGN_UP(width, 32)
        fmt[0].es[0].video.height = mmal.VCOS_ALIGN_UP(height, 16)
        fmt[0].es[0].video.crop.x = 0
        fmt[0].es[0].video.crop.y = 0
        fmt[0].es[0].video.crop.width = width
        fmt[0].es[0].video.crop.height = height
        mmal_check(
            mmal.mmal_port_format_commit(self.resizer[0].output[0]),
            prefix="Failed to set resizer output port format")

    def _create_pool(self):
        """
        Allocates a pool of buffers for the encoder
        """
        assert not self.pool
        self.pool = mmal.mmal_port_pool_create(
            self.output_port,
            self.output_port[0].buffer_num,
            self.output_port[0].buffer_size)
        if not self.pool:
            raise PiCameraError(
                "Failed to create buffer header pool for encoder component")

    def _create_connection(self):
        """
        Connects the camera to the encoder object
        """
        assert not self.encoder_connection
        if self.resizer:
            self.resizer_connection = self.parent._connect_ports(
                self.input_port, self.resizer[0].input[0])
            self.encoder_connection = self.parent._connect_ports(
                self.resizer[0].output[0], self.encoder[0].input[0])
        else:
            self.encoder_connection = self.parent._connect_ports(
                self.input_port, self.encoder[0].input[0])

    def _callback(self, port, buf):
        """
        The encoder's main callback function
        """
        if self.stopped:
            mmal.mmal_buffer_header_release(buf)
        else:
            stop = False
            try:
                try:
                    stop = self._callback_write(buf)
                finally:
                    mmal.mmal_buffer_header_release(buf)
                    self._callback_recycle(port, buf)
            except Exception as e:
                stop = True
                self.exception = e
            if stop:
                self.stopped = True
                self.event.set()

    def _callback_write(self, buf):
        """
        Performs output writing on behalf of the encoder callback function;
        return value determines whether writing has completed.
        """
        if buf[0].length:
            mmal_check(
                mmal.mmal_buffer_header_mem_lock(buf),
                prefix="Unable to lock buffer header memory")
            try:
                with self.lock:
                    if self.output:
                        written = self.output.write(
                           ct.string_at(buf[0].data, buf[0].length))
                        # Ignore None return value; most Python 2 streams have
                        # no return value for write()
                        if (written is not None) and (written != buf[0].length):
                            raise PiCameraError(
                                "Unable to write buffer to file - aborting")
            finally:
                mmal.mmal_buffer_header_mem_unlock(buf)
        return bool(buf[0].flags & mmal.MMAL_BUFFER_HEADER_FLAG_EOS)

    def _callback_recycle(self, port, buf):
        """
        Recycles the buffer on behalf of the encoder callback function
        """
        new_buf = mmal.mmal_queue_get(self.pool[0].queue)
        if not new_buf:
            raise PiCameraError(
                "Unable to get a buffer to return to the encoder port")
        mmal_check(
            mmal.mmal_port_send_buffer(port, new_buf),
            prefix="Unable to return a buffer to the encoder port")

    def _open_output(self, output):
        """
        Opens the specified output object, if necessary and tracks whether
        we were the one to open it.
        """
        with self.lock:
            self.opened_output = isinstance(output, (bytes, str))
            if self.opened_output:
                # Open files in binary mode with a decent buffer size
                self.output = io.open(output, 'wb', buffering=65536)
            else:
                self.output = output

    def _close_output(self):
        """
        Closes the output object, if necessary or simply flushes it if we
        didn't open it and it has a flush method.
        """
        with self.lock:
            if self.output:
                if self.opened_output:
                    self.output.close()
                elif hasattr(self.output, 'flush'):
                    self.output.flush()
                self.output = None
                self.opened_output = False

    def start(self, output):
        """
        Starts the encoder object writing to the specified output
        """
        self.event.clear()
        self.stopped = False
        self.exception = None
        self._open_output(output)
        self.output_port[0].userdata = ct.cast(
            ct.pointer(ct.py_object(self)),
            ct.c_void_p)
        mmal_check(
            mmal.mmal_port_enable(self.output_port, _encoder_callback),
            prefix="Failed to enable encoder output port")

        for q in range(mmal.mmal_queue_length(self.pool[0].queue)):
            buf = mmal.mmal_queue_get(self.pool[0].queue)
            if not buf:
                raise PiCameraRuntimeError(
                    "Unable to get a required buffer from pool queue")
            mmal_check(
                mmal.mmal_port_send_buffer(self.output_port, buf),
                prefix="Unable to send a buffer to encoder output port")
        b = mmal.MMAL_BOOL_T()
        mmal_check(
            mmal.mmal_port_parameter_get_boolean(
                self.camera_port,
                mmal.MMAL_PARAMETER_CAPTURE,
                b),
            prefix="Failed to query capture status")
        self.started_capture = not bool(b)
        if self.started_capture:
            mmal_check(
                mmal.mmal_port_parameter_set_boolean(
                    self.camera_port,
                    mmal.MMAL_PARAMETER_CAPTURE,
                    mmal.MMAL_TRUE),
                prefix="Failed to start capture")

    def wait(self, timeout=None):
        """
        Waits for the encoder to finish (successfully or otherwise)
        """
        result = self.event.wait(timeout)
        if result:
            if self.started_capture:
                self.started_capture = False
                mmal_check(
                    mmal.mmal_port_parameter_set_boolean(
                        self.camera_port,
                        mmal.MMAL_PARAMETER_CAPTURE,
                        mmal.MMAL_FALSE),
                    prefix="Failed to stop capture")
            try:
                mmal_check(
                    mmal.mmal_port_disable(self.output_port),
                    prefix="Failed to disable encoder output port")
            except PiCameraMMALError as e:
                if e.status != mmal.MMAL_EINVAL:
                    raise
            self._close_output()
            # Check whether the callback set an exception
            if self.exception:
                raise self.exception
        return result

    def stop(self):
        """
        Stops the encoder, regardless of whether it's finished
        """
        # The check on is_enabled below is not a race condition; we ignore the
        # EINVAL error in the case the port turns out to be disabled when we
        # disable below. The check exists purely to prevent stderr getting
        # spammed by our continued attempts to disable an already disabled port
        if self.encoder and self.output_port[0].is_enabled:
            if self.started_capture:
                self.started_capture = False
                mmal_check(
                    mmal.mmal_port_parameter_set_boolean(
                        self.camera_port,
                        mmal.MMAL_PARAMETER_CAPTURE,
                        mmal.MMAL_FALSE),
                    prefix="Failed to stop capture")
            try:
                mmal_check(
                    mmal.mmal_port_disable(self.output_port),
                    prefix="Failed to disable encoder output port")
            except PiCameraMMALError as e:
                if e.status != mmal.MMAL_EINVAL:
                    raise
        self.stopped = True
        self.event.set()
        self._close_output()

    def close(self):
        """
        Finalizes the encoder and deallocates all structures
        """
        self.stop()
        if self.encoder_connection:
            mmal.mmal_connection_destroy(self.encoder_connection)
            self.encoder_connection = None
        if self.pool:
            mmal.mmal_port_pool_destroy(self.output_port, self.pool)
            self.pool = None
        if self.resizer_connection:
            mmal.mmal_connection_destroy(self.resizer_connection)
        if self.encoder:
            mmal.mmal_component_destroy(self.encoder)
            self.encoder = None
        if self.resizer:
            mmal.mmal_component_destroy(self.resizer)
            self.resizer = None
        self.output_port = None


class PiVideoEncoder(PiEncoder):
    encoder_type = mmal.MMAL_COMPONENT_DEFAULT_VIDEO_ENCODER

    def __init__(
            self, parent, camera_port, input_port, format, resize, **options):
        super(PiVideoEncoder, self).__init__(
                parent, camera_port, input_port, format, resize, **options)
        self._next_output = []
        self.frame = None

    def _create_encoder(
            self, bitrate=17000000, intra_period=0, profile='high',
            quantization=0, inline_headers=True, sei=False):
        super(PiVideoEncoder, self)._create_encoder()

        try:
            self.output_port[0].format[0].encoding = {
                'h264':  mmal.MMAL_ENCODING_H264,
                'mjpeg': mmal.MMAL_ENCODING_MJPEG,
                }[self.format]
        except KeyError:
            raise PiCameraValueError('Unrecognized format %s' % self.format)

        if not (0 <= bitrate <= 25000000):
            raise PiCameraValueError('bitrate must be between 0 (VBR) and 25Mbps')
        if quantization and bitrate:
            warnings.warn('Setting bitrate to 0 as quantization is non-zero', PiCameraWarning)
            bitrate = 0
        self.output_port[0].format[0].bitrate = bitrate
        mmal_check(
            mmal.mmal_port_format_commit(self.output_port),
            prefix="Unable to set format on encoder output port")

        if self.format == 'h264':
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
            mp.profile[0].level = mmal.MMAL_VIDEO_LEVEL_H264_4
            mmal_check(
                mmal.mmal_port_parameter_set(self.output_port, mp.hdr),
                prefix="Unable to set encoder H.264 profile")

            mmal_check(
                mmal.mmal_port_parameter_set_boolean(
                    self.output_port,
                    mmal.MMAL_PARAMETER_VIDEO_ENCODE_INLINE_HEADER,
                    int(inline_headers)),
                prefix="Unable to set inline_headers")

            mmal_check(
                mmal.mmal_port_parameter_set_boolean(
                    self.output_port,
                    mmal.MMAL_PARAMETER_VIDEO_ENCODE_SEI_ENABLE,
                    int(sei)),
                prefix="Enable to set SEI")

            if not (bitrate and inline_headers):
                # If inline_headers is disabled, or VBR encoding is configured,
                # disable the split function
                self._next_output = None

            # We need the intra-period to calculate the SPS header timeout in
            # the split method below. If one is not set explicitly, query the
            # encoder's default
            if intra_period:
                mp = mmal.MMAL_PARAMETER_UINT32_T(
                        mmal.MMAL_PARAMETER_HEADER_T(
                            mmal.MMAL_PARAMETER_INTRAPERIOD,
                            ct.sizeof(mmal.MMAL_PARAMETER_UINT32_T),
                            ),
                        intra_period
                        )
                mmal_check(
                    mmal.mmal_port_parameter_set(self.output_port, mp.hdr),
                    prefix="Unable to set encoder intra_period")
                self._intra_period = intra_period
            else:
                mp = mmal.MMAL_PARAMETER_UINT32_T(
                    mmal.MMAL_PARAMETER_HEADER_T(
                        mmal.MMAL_PARAMETER_INTRAPERIOD,
                        ct.sizeof(mmal.MMAL_PARAMETER_UINT32_T),
                        ))
                mmal_check(
                    mmal.mmal_port_parameter_get(self.output_port, mp.hdr),
                    prefix="Unable to get encoder intra_period")
                self._intra_period = mp.value

        elif self.format == 'mjpeg':
            # MJPEG doesn't have an intra_period setting as such, but as every
            # frame is a full-frame, the intra_period is effectively 1
            self._intra_period = 1

        if quantization:
            mp = mmal.MMAL_PARAMETER_UINT32_T(
                    mmal.MMAL_PARAMETER_HEADER_T(
                        mmal.MMAL_PARAMETER_VIDEO_ENCODE_INITIAL_QUANT,
                        ct.sizeof(mmal.MMAL_PARAMETER_UINT32_T),
                        ),
                    quantization
                    )
            mmal_check(
                mmal.mmal_port_parameter_set(self.output_port, mp.hdr),
                prefix="Unable to set initial quantization")
            mp = mmal.MMAL_PARAMETER_UINT32_T(
                    mmal.MMAL_PARAMETER_HEADER_T(
                        mmal.MMAL_PARAMETER_VIDEO_ENCODE_MIN_QUANT,
                        ct.sizeof(mmal.MMAL_PARAMETER_UINT32_T),
                        ),
                    quantization,
                    )
            mmal_check(
                mmal.mmal_port_parameter_set(self.output_port, mp.hdr),
                prefix="Unable to set minimum quantization")
            mp = mmal.MMAL_PARAMETER_UINT32_T(
                    mmal.MMAL_PARAMETER_HEADER_T(
                        mmal.MMAL_PARAMETER_VIDEO_ENCODE_MAX_QUANT,
                        ct.sizeof(mmal.MMAL_PARAMETER_UINT32_T),
                        ),
                    quantization,
                    )
            mmal_check(
                mmal.mmal_port_parameter_set(self.output_port, mp.hdr),
                prefix="Unable to set maximum quantization")

        mmal_check(
            mmal.mmal_port_parameter_set_boolean(
                self.encoder[0].input[0],
                mmal.MMAL_PARAMETER_VIDEO_IMMUTABLE_INPUT,
                1),
            prefix="Unable to set immutable flag on encoder input port")

        mmal_check(
            mmal.mmal_component_enable(self.encoder),
            prefix="Unable to enable video encoder component")

    def start(self, output):
        self._size = 0 # internal counter for frame size
        self.frame = PiVideoFrame(
                index=-1,
                keyframe=False,
                frame_size=0,
                video_size=0,
                split_size=0,
                timestamp=0,
                header=False,
                )
        super(PiVideoEncoder, self).start(output)

    def split(self, output):
        with self.lock:
            if self._next_output is None:
                raise PiCameraRuntimeError(
                    'Cannot use split_recording without inline_headers and CBR')
            self._next_output.append(output)
        # intra_period / framerate gives the time between I-frames (which
        # should also coincide with SPS headers). We multiply by two to ensure
        # the timeout is deliberately excessive
        timeout = float(self._intra_period / self.parent.framerate) * 2.0
        if not self.event.wait(timeout):
            raise PiCameraRuntimeError('Timed out waiting for an SPS header')
        self.event.clear()

    def _callback_write(self, buf):
        self._size += buf[0].length
        if buf[0].flags & mmal.MMAL_BUFFER_HEADER_FLAG_FRAME_END:
            self.frame = PiVideoFrame(
                    index=self.frame.index + 1,
                    keyframe=bool(buf[0].flags & mmal.MMAL_BUFFER_HEADER_FLAG_KEYFRAME),
                    frame_size=self._size,
                    video_size=self.frame.video_size + self._size,
                    split_size=self.frame.split_size + self._size,
                    timestamp=None if buf[0].pts in (0, mmal.MMAL_TIME_UNKNOWN) else buf[0].pts,
                    header=bool(buf[0].flags & mmal.MMAL_BUFFER_HEADER_FLAG_CONFIG),
                    )
            self._size = 0
        if self.format != 'h264' or (buf[0].flags & mmal.MMAL_BUFFER_HEADER_FLAG_CONFIG):
            new_output = None
            with self.lock:
                if self._next_output:
                    new_output = self._next_output.pop(0)
            if new_output:
                self._close_output()
                self.frame = PiVideoFrame(
                        index=self.frame.index,
                        keyframe=self.frame.keyframe,
                        frame_size=self.frame.frame_size,
                        video_size=self.frame.video_size,
                        split_size=0,
                        timestamp=self.frame.timestamp,
                        header=self.frame.header,
                        )
                self._open_output(new_output)
                self.event.set()
        super(PiVideoEncoder, self)._callback_write(buf)


class PiImageEncoder(PiEncoder):
    encoder_type = mmal.MMAL_COMPONENT_DEFAULT_IMAGE_ENCODER

    def _create_encoder(self, quality=85, thumbnail=(64, 48, 35), bayer=False):
        super(PiImageEncoder, self)._create_encoder()

        try:
            self.output_port[0].format[0].encoding = {
                'jpeg': mmal.MMAL_ENCODING_JPEG,
                'png':  mmal.MMAL_ENCODING_PNG,
                'gif':  mmal.MMAL_ENCODING_GIF,
                'bmp':  mmal.MMAL_ENCODING_BMP,
                }[self.format]
        except KeyError:
            raise PiCameraValueError("Unrecognized format %s" % self.format)
        mmal_check(
            mmal.mmal_port_format_commit(self.output_port),
            prefix="Unable to set format on encoder output port")

        if self.format == 'jpeg':
            mmal_check(
                mmal.mmal_port_parameter_set_uint32(
                    self.output_port,
                    mmal.MMAL_PARAMETER_JPEG_Q_FACTOR,
                    quality),
                prefix="Failed to set JPEG quality")

            mmal_check(
                mmal.mmal_port_parameter_set_boolean(
                    self.camera_port,
                    mmal.MMAL_PARAMETER_ENABLE_RAW_CAPTURE,
                    int(bool(bayer))),
                prefix="Failed to set raw capture")

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
            mmal_check(
                mmal.mmal_port_parameter_set(self.encoder[0].control, mp.hdr),
                prefix="Failed to set thumbnail configuration")

        mmal_check(
            mmal.mmal_component_enable(self.encoder),
            prefix="Unable to enable encoder component")


class PiOneImageEncoder(PiImageEncoder):
    def _callback_write(self, buf):
        return (
            super(PiOneImageEncoder, self)._callback_write(buf)
            ) or bool(
            buf[0].flags & (
                mmal.MMAL_BUFFER_HEADER_FLAG_FRAME_END |
                mmal.MMAL_BUFFER_HEADER_FLAG_TRANSMISSION_FAILED)
            )


class PiMultiImageEncoder(PiImageEncoder):
    def _open_output(self, outputs):
        self._output_iter = iter(outputs)
        self._next_output()

    def _next_output(self):
        if self.output:
            self._close_output()
        super(PiMultiImageEncoder, self)._open_output(next(self._output_iter))

    def _callback_write(self, buf):
        try:
            if (
                super(PiMultiImageEncoder, self)._callback_write(buf)
                ) or bool(
                buf[0].flags & (
                    mmal.MMAL_BUFFER_HEADER_FLAG_FRAME_END |
                    mmal.MMAL_BUFFER_HEADER_FLAG_TRANSMISSION_FAILED)
                ):
                self._next_output()
            return False
        except StopIteration:
            return True


class PiCookedOneImageEncoder(PiOneImageEncoder):
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
        mmal_check(
            mmal.mmal_port_parameter_set(self.output_port, mp[0].hdr),
            prefix="Failed to set Exif tag %s" % tag)

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
    # No Exif stuff here as video-port encodes (which is all
    # PiCookedMultiImageEncoder gets called for) don't support Exif output
    pass


class PiRawEncoderMixin(PiImageEncoder):

    RAW_ENCODINGS = {
        # name   mmal-encoding            bytes-per-pixel
        'yuv':  (mmal.MMAL_ENCODING_I420, 1.5),
        'rgb':  (mmal.MMAL_ENCODING_RGBA, 3),
        'rgba': (mmal.MMAL_ENCODING_RGBA, 4),
        'bgr':  (mmal.MMAL_ENCODING_BGRA, 3),
        'bgra': (mmal.MMAL_ENCODING_BGRA, 4),
        }

    def __init__(
            self, parent, camera_port, input_port, format, resize, **options):
        # If a resize hasn't been requested, check the input_port format. If
        # it requires conversion, force the use of a resizer to perform the
        # conversion
        if not resize:
            if parent.RAW_FORMATS[format] != input_port[0].format[0].encoding.value:
                resize = parent.resolution
        # Workaround: If a non-alpha format is requested when a resizer is
        # required, we use the alpha-inclusive format and set a flag to get the
        # callback to strip the alpha bytes (for some reason the resizer won't
        # work with non-alpha output formats - firmware bug?)
        if resize:
            width, height = resize
            self._strip_alpha = format in ('rgb', 'bgr')
        else:
            width, height = parent.resolution
            self._strip_alpha = False
        width = mmal.VCOS_ALIGN_UP(width, 32)
        height = mmal.VCOS_ALIGN_UP(height, 16)
        # Workaround (#83): when the resizer is used the width and height must
        # be aligned (both the actual and crop values) to avoid an error when
        # the output port format is set
        if resize:
            resize = (width, height)
        # Workaround: Calculate the expected image size, to be used by the
        # callback to decide when a frame ends. This is to work around a
        # firmware bug that causes the raw image to be returned twice when the
        # maximum camera resolution is requested
        self._expected_size = int(width * height * self.RAW_ENCODINGS[format][1])
        self._image_size = 0
        super(PiRawEncoderMixin, self).__init__(
                parent, camera_port, input_port, format, resize, **options)

    def _create_resizer(self, width, height):
        super(PiRawEncoderMixin, self)._create_resizer(width, height)
        encoding = self.RAW_ENCODINGS[self.format][0]
        port = self.resizer[0].output[0]
        port[0].format[0].encoding = encoding
        port[0].format[0].encoding_variant = encoding
        mmal_check(
            mmal.mmal_port_format_commit(port),
            prefix="Failed to set resizer output port format")

    def _create_encoder(self):
        # Overridden to skip creating an encoder. Instead we simply use the
        # resizer's port as the output port (if we have a resizer) or the
        # input port otherwise
        if self.resizer:
            self.output_port = self.resizer[0].output[0]
        else:
            self.output_port = self.input_port

    def _create_connection(self):
        # Overridden to skip creating an encoder connection; we only need the
        # resizer connection (if we have a resizer)
        if self.resizer:
            self.resizer_connection = self.parent._connect_ports(
                self.input_port, self.resizer[0].input[0])

    def _callback_write(self, buf):
        # Overridden to strip alpha bytes when necessary (see _create_resizer),
        # and manually calculate the frame end
        if buf[0].length and self._image_size:
            mmal_check(
                mmal.mmal_buffer_header_mem_lock(buf),
                prefix="Unable to lock buffer header memory")
            try:
                s = ct.string_at(buf[0].data, buf[0].length)
                if self._strip_alpha:
                    s = b''.join(s[i:i+3] for i in range(0, len(s), 4))
                with self.lock:
                    if self.output:
                        written = self.output.write(s)
                        # Ignore None return value; most Python 2 streams have
                        # no return value for write()
                        if (written is not None) and (written != len(s)):
                            raise PiCameraError(
                                "Unable to write buffer to file - aborting")
                        self._image_size -= len(s)
                        assert self._image_size >= 0
            finally:
                mmal.mmal_buffer_header_mem_unlock(buf)
        return self._image_size <= 0

    def start(self, output):
        self._image_size = self._expected_size
        super(PiRawEncoderMixin, self).start(output)


class PiRawOneImageEncoder(PiOneImageEncoder, PiRawEncoderMixin):
    pass


class PiRawMultiImageEncoder(PiMultiImageEncoder, PiRawEncoderMixin):
    def _next_output(self):
        super(PiRawMultiImageEncoder, self)._next_output()
        self._image_size = self._expected_size

