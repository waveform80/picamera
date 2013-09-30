# vim: set et sw=4 sts=4 fileencoding=utf-8:
#
# Python header conversion
# Copyright (c) 2013, Dave Hughes <dave@waveform.org.uk>
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
This module primarily provides the :class:`PiCamera` class which is a pure
Python interface to the Raspberry Pi's camera module.


Classes
=======

.. autoclass:: PiCamera()
    :members:


Exceptions
==========

.. autoexception:: PiCameraError

.. autoexception:: PiCameraValueError

.. autoexception:: PiCameraRuntimeError

"""

from __future__ import (
    unicode_literals,
    print_function,
    division,
    absolute_import,
    )

import io
import datetime
import mimetypes
import threading
import ctypes as ct

import picamera.mmal as mmal
import picamera.bcm_host as bcm_host

__all__ = [
    'PiCamera',
    'PiCameraError',
    'PiCameraRuntimeError',
    'PiCameraValueError',
    ]


# Make Py2's str equivalent to Py3's
str = type('')


class PiCameraError(Exception):
    """
    Base class for PiCamera errors
    """

class PiCameraRuntimeError(PiCameraError, RuntimeError):
    """
    Raised when an invalid sequence of operations is attempted with a PiCamera object
    """

class PiCameraValueError(PiCameraError, ValueError):
    """
    Raised when an invalid value is fed to a PiCamera object
    """


def _check(status, prefix=""):
    """
    Checks the return status of an mmal call and raises an exception on
    failure.

    The optional prefix parameter specifies a prefix message to place at the
    start of the exception's message to provide some context.
    """
    if status != mmal.MMAL_SUCCESS:
        raise PiCameraError("%s%s%s" % (prefix, ": " if prefix else "", {
            mmal.MMAL_ENOMEM:    "Out of memory",
            mmal.MMAL_ENOSPC:    "Out of resources (other than memory)",
            mmal.MMAL_EINVAL:    "Argument is invalid",
            mmal.MMAL_ENOSYS:    "Function not implemented",
            mmal.MMAL_ENOENT:    "No such file or directory",
            mmal.MMAL_ENXIO:     "No such device or address",
            mmal.MMAL_EIO:       "I/O error",
            mmal.MMAL_ESPIPE:    "Illegal seek",
            mmal.MMAL_ECORRUPT:  "Data is corrupt #FIXME not POSIX",
            mmal.MMAL_ENOTREADY: "Component is not ready #FIXME not POSIX",
            mmal.MMAL_ECONFIG:   "Component is not configured #FIXME not POSIX",
            mmal.MMAL_EISCONN:   "Port is already connected",
            mmal.MMAL_ENOTCONN:  "Port is disconnected",
            mmal.MMAL_EAGAIN:    "Resource temporarily unavailable; try again later",
            mmal.MMAL_EFAULT:    "Bad address",
            }.get(status, "Unknown status error")))

def _control_callback(port, buf):
    if buf[0].cmd != mmal.MMAL_EVENT_PARAMETER_CHANGED:
        raise PiCameraRuntimeError(
            "Received unexpected camera control callback event, 0x%08x" % buf[0].cmd)
    mmal.mmal_buffer_header_release(buf)
_control_callback = mmal.MMAL_PORT_BH_CB_T(_control_callback)

def _encoder_callback(port, buf):
    encoder = ct.cast(port[0].userdata, ct.POINTER(ct.py_object))[0]
    encoder._callback(port, buf)
_encoder_callback = mmal.MMAL_PORT_BH_CB_T(_encoder_callback)


class _PiEncoder(object):
    """
    Abstract base implemetation of an MMAL encoder for use by PiCamera
    """

    encoder_type = None
    port = None

    def __init__(self, parent, format, **options):
        self.parent = parent
        self.camera = parent._camera
        self.encoder = None
        self.pool = None
        self.connection = None
        self.opened = False
        self.output = None
        self.exception = None
        self.event = threading.Event()
        self.stopped = True
        try:
            self._create_encoder(format, **options)
            self._create_pool()
            self._create_connection()
        except:
            self.close()
            raise

    def _create_encoder(self, format, **options):
        """
        Creates and configures the encoder itself
        """
        assert not self.encoder
        self.encoder = ct.POINTER(mmal.MMAL_COMPONENT_T)()
        _check(
            mmal.mmal_component_create(self.encoder_type, self.encoder),
            prefix="Failed to create encoder component")
        if not self.encoder[0].input_num:
            raise PiCameraError("No input ports on encoder component")
        if not self.encoder[0].output_num:
            raise PiCameraError("No output ports on encoder component")
        # Ensure output format is the same as the input
        enc_out = self.encoder[0].output[0]
        enc_in = self.encoder[0].input[0]
        mmal.mmal_format_copy(enc_out[0].format, enc_in[0].format)
        # Set buffer size and number to appropriate values
        enc_out[0].buffer_size = max(
            enc_out[0].buffer_size_recommended,
            enc_out[0].buffer_size_min)
        enc_out[0].buffer_num = max(
            enc_out[0].buffer_num_recommended,
            enc_out[0].buffer_num_min)

    def _create_pool(self):
        """
        Allocates a pool of buffers for the encoder
        """
        assert not self.pool
        enc_out = self.encoder[0].output[0]
        self.pool = mmal.mmal_port_pool_create(
            enc_out, enc_out[0].buffer_num, enc_out[0].buffer_size)
        if not self.pool:
            raise PiCameraError(
                "Failed to create buffer header pool for encoder component")

    def _create_connection(self):
        """
        Connects the camera to the encoder object
        """
        assert not self.connection
        self.connection = ct.POINTER(mmal.MMAL_CONNECTION_T)()
        _check(
            mmal.mmal_connection_create(
                self.connection,
                self.camera[0].output[self.port],
                self.encoder[0].input[0],
                mmal.MMAL_CONNECTION_FLAG_TUNNELLING |
                mmal.MMAL_CONNECTION_FLAG_ALLOCATION_ON_INPUT),
            prefix="Failed to connect camera to encoder")
        _check(
            mmal.mmal_connection_enable(self.connection),
            prefix="Failed to enable encoder connection")

    def _callback(self, port, buf):
        """
        The encoder's main callback function
        """
        stop = False
        try:
            try:
                stop = not self.stopped and self._callback_write(buf)
            finally:
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
            _check(
                mmal.mmal_buffer_header_mem_lock(buf),
                prefix="Unable to lock buffer header memory")
            try:
                if self.output.write(
                        ct.string_at(buf[0].data, buf[0].length)) != buf[0].length:
                    raise PiCameraError(
                        "Unable to write buffer to file - aborting")
            finally:
                mmal.mmal_buffer_header_mem_unlock(buf)
        return False

    def _callback_recycle(self, port, buf):
        """
        Recycles the buffer on behalf of the encoder callback function
        """
        mmal.mmal_buffer_header_release(buf)
        if port[0].is_enabled:
            new_buf = mmal.mmal_queue_get(self.pool[0].queue)
            if not new_buf:
                raise PiCameraError(
                    "Unable to get a buffer to return to the encoder port")
            _check(
                mmal.mmal_port_send_buffer(port, new_buf),
                prefix="Unable to return a buffer to the encoder port")

    def start(self, output):
        """
        Starts the encoder object writing to the specified output
        """
        self.event.clear()
        self.stopped = False
        self.opened = isinstance(output, (bytes, str))
        if self.opened:
            # Open files in binary mode with a *big* (1Mb) buffer
            self.output = io.open(output, 'wb', buffering=1048576)
        else:
            self.output = output
        self.encoder[0].output[0][0].userdata = ct.cast(
            ct.pointer(ct.py_object(self)),
            ct.c_void_p)
        _check(
            mmal.mmal_port_enable(self.encoder[0].output[0], _encoder_callback),
            prefix="Failed to enable encoder output port")

        for q in range(mmal.mmal_queue_length(self.pool[0].queue)):
            buf = mmal.mmal_queue_get(self.pool[0].queue)
            if not buf:
                raise PiCameraRuntimeError(
                    "Unable to get a required buffer from pool queue")
            _check(
                mmal.mmal_port_send_buffer(self.encoder[0].output[0], buf),
                prefix="Unable to send a buffer to encoder output port")

        _check(
            mmal.mmal_port_parameter_set_boolean(
                self.camera[0].output[self.port],
                mmal.MMAL_PARAMETER_CAPTURE, mmal.MMAL_TRUE),
            prefix="Failed to start capture")

    def wait(self, timeout=None):
        """
        Waits for the encoder to finish (successfully or otherwise)
        """
        result = self.event.wait(timeout)
        if result:
            _check(
                mmal.mmal_port_disable(self.encoder[0].output[0]),
                prefix="Failed to disable encoder output port")
            # Check whether the callback set an exception
            if self.exception:
                raise self.exception
        return result

    def stop(self):
        if self.encoder and self.encoder[0].output[0][0].is_enabled:
            _check(
                mmal.mmal_port_disable(self.encoder[0].output[0]),
                prefix="Failed to disable encoder output port")
        self.stopped = True
        self.event.set()
        # Closing connections may flush buffers hence file must be closed
        # *after* closing connections
        if self.output:
            if self.opened:
                self.output.close()
            self.output = None
            self.opened = False

    def close(self):
        """
        Finalizes the encoder and deallocates all structures
        """
        self.stop()
        if self.connection:
            mmal.mmal_connection_destroy(self.connection)
            self.connection = None
        if self.pool:
            mmal.mmal_port_pool_destroy(self.encoder[0].output[0], self.pool)
            self.pool = None
        if self.encoder:
            if self.encoder[0].is_enabled:
                mmal.mmal_component_disable(self.encoder)
            mmal.mmal_component_destroy(self.encoder)
            self.encoder = None


class _PiVideoEncoder(_PiEncoder):
    encoder_type = mmal.MMAL_COMPONENT_DEFAULT_VIDEO_ENCODER
    port = 1

    def _create_encoder(self, format, **options):
        super(_PiVideoEncoder, self)._create_encoder(format, **options)

        # TODO Allow configuration of bitrate/encoding?
        enc_out = self.encoder[0].output[0]
        enc_out[0].format[0].encoding = mmal.MMAL_ENCODING_H264
        enc_out[0].format[0].bitrate = 17000000
        _check(
            mmal.mmal_port_format_commit(enc_out),
            prefix="Unable to set format on encoder output port")

        # XXX Why does this fail? Is it even needed?
        #try:
        #    _check(
        #        mmal.mmal_port_parameter_set_boolean(
        #            enc_in,
        #            mmal.MMAL_PARAMETER_VIDEO_IMMUTABLE_INPUT,
        #            1),
        #        prefix="Unable to set immutable flag on encoder input port")
        #except PiCameraError as e:
        #    print(str(e))
        #    # Continue rather than abort...

        _check(
            mmal.mmal_component_enable(self.encoder),
            prefix="Unable to enable video encoder component")


class _PiStillEncoder(_PiEncoder):
    encoder_type = mmal.MMAL_COMPONENT_DEFAULT_IMAGE_ENCODER
    port = 2
    exif_encoding = 'ascii'

    def _create_encoder(self, format, **options):
        super(_PiStillEncoder, self)._create_encoder(format, **options)

        enc_out = self.encoder[0].output[0]
        try:
            enc_out[0].format[0].encoding = {
                'jpeg': mmal.MMAL_ENCODING_JPEG,
                'png':  mmal.MMAL_ENCODING_PNG,
                'gif':  mmal.MMAL_ENCODING_GIF,
                'bmp':  mmal.MMAL_ENCODING_BMP,
                }[format]
        except KeyError:
            raise PiCameraValueError('Unrecognized format %s' % format)
        _check(
            mmal.mmal_port_format_commit(enc_out),
            prefix="Unable to set format on encoder output port")

        if format == 'jpeg':
            _check(
                mmal.mmal_port_parameter_set_uint32(
                    enc_out,
                    mmal.MMAL_PARAMETER_JPEG_Q_FACTOR,
                    options.get('quality', 85)),
                prefix="Failed to set JPEG quality")

            thumbnail = options.get('thumbnail', (64, 48, 35))
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
            _check(
                mmal.mmal_port_parameter_set(self.encoder[0].control, mp.hdr),
                prefix="Failed to set thumbnail configuration")

        _check(
            mmal.mmal_component_enable(self.encoder),
            prefix="Unable to enable encoder component")

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
        _check(
            mmal.mmal_port_parameter_set(self.encoder[0].output[0], mp[0].hdr),
            prefix="Failed to set Exif tag %s" % tag)

    def start(self, output):
        timestamp = datetime.datetime.now()
        timestamp_tags = (
            'EXIF.DateTimeDigitized',
            'EXIF.DateTimeOriginal',
            'IFD0.DateTime')
        # Timestamp tags are always included with the value calculated above,
        # but the user may choose to override the value in the exif_tags
        # mapping
        for tag in timestamp_tags:
            self._add_exif_tag(tag, self.parent.exif_tags.get(tag, timestamp))
        # All other tags are just copied in verbatim
        for tag, value in self.parent.exif_tags.items():
            if not tag in timestamp_tags:
                self._add_exif_tag(tag, value)
        super(_PiStillEncoder, self).start(output)

    def _callback_write(self, buf):
        return (
            super(_PiStillEncoder, self)._callback_write(buf)
            ) or bool(
            buf[0].flags & (
                mmal.MMAL_BUFFER_HEADER_FLAG_FRAME_END |
                mmal.MMAL_BUFFER_HEADER_FLAG_TRANSMISSION_FAILED)
            )

class PiCamera(object):
    """
    Provides a pure Python interface to the Raspberry Pi's camera module.

    Upon construction, this class initializes the camera. As there is only a
    single camera supported by the Raspberry Pi, this means that only a single
    instance of this class can exist at any given time (it is effectively a
    singleton class although it is not implemented as such).

    No preview or recording is started automatically upon construction.  Use
    the :meth:`capture` method to capture image, the :meth:`start_recording`
    method to begin recording video, or the :meth:`start_preview` method to
    start live display of the camera's input.

    Several attributes are provided to adjust the camera's configuration. Some
    of these can be adjusted while a preview or recording is running, like
    :attr:`brightness`. Others, like :attr:`resolution` can only be adjusted
    when the camera is idle.

    When you are finished with the camera, you should ensure you call the
    :meth:`close` method to release the camera resources (failure to do this
    leads to GPU memory leaks)::

        camera = PiCamera()
        try:
            # do something with the camera
        finally:
            camera.close()

    The class supports the context manager protocol to make this particularly
    easy (upon exiting the ``with`` statement, the :meth:`close` method is
    automatically called)::

        with PiCamera() as camera:
            # do something with the camera

    """

    CAMERA_PREVIEW_PORT = 0
    CAMERA_VIDEO_PORT = _PiVideoEncoder.port
    CAMERA_CAPTURE_PORT = _PiStillEncoder.port
    CAMERA_PORTS = (
        CAMERA_PREVIEW_PORT,
        CAMERA_VIDEO_PORT,
        CAMERA_CAPTURE_PORT,
        )
    MAXIMUM_RESOLUTION = (2592, 1944)
    DEFAULT_RESOLUTION = (1920, 1080)
    DEFAULT_FRAME_RATE_NUM = 30
    DEFAULT_FRAME_RATE_DEN = 1
    FULL_FRAME_RATE_NUM = 15
    FULL_FRAME_RATE_DEN = 1
    VIDEO_OUTPUT_BUFFERS_NUM = 3
    PREVIEW_LAYER = 2
    PREVIEW_ALPHA = 255

    METER_MODES = {
        'average': mmal.MMAL_PARAM_EXPOSUREMETERINGMODE_AVERAGE,
        'spot':    mmal.MMAL_PARAM_EXPOSUREMETERINGMODE_SPOT,
        'backlit': mmal.MMAL_PARAM_EXPOSUREMETERINGMODE_BACKLIT,
        'matrix':  mmal.MMAL_PARAM_EXPOSUREMETERINGMODE_MATRIX,
        }

    EXPOSURE_MODES = {
        'off':           mmal.MMAL_PARAM_EXPOSUREMODE_OFF,
        'auto':          mmal.MMAL_PARAM_EXPOSUREMODE_AUTO,
        'night':         mmal.MMAL_PARAM_EXPOSUREMODE_NIGHT,
        'nightpreview':  mmal.MMAL_PARAM_EXPOSUREMODE_NIGHTPREVIEW,
        'backlight':     mmal.MMAL_PARAM_EXPOSUREMODE_BACKLIGHT,
        'spotlight':     mmal.MMAL_PARAM_EXPOSUREMODE_SPOTLIGHT,
        'sports':        mmal.MMAL_PARAM_EXPOSUREMODE_SPORTS,
        'snow':          mmal.MMAL_PARAM_EXPOSUREMODE_SNOW,
        'beach':         mmal.MMAL_PARAM_EXPOSUREMODE_BEACH,
        'verylong':      mmal.MMAL_PARAM_EXPOSUREMODE_VERYLONG,
        'fixedfps':      mmal.MMAL_PARAM_EXPOSUREMODE_FIXEDFPS,
        'antishake':     mmal.MMAL_PARAM_EXPOSUREMODE_ANTISHAKE,
        'fireworks':     mmal.MMAL_PARAM_EXPOSUREMODE_FIREWORKS,
        }

    AWB_MODES = {
        'off':           mmal.MMAL_PARAM_AWBMODE_OFF,
        'auto':          mmal.MMAL_PARAM_AWBMODE_AUTO,
        'sunlight':      mmal.MMAL_PARAM_AWBMODE_SUNLIGHT,
        'cloudy':        mmal.MMAL_PARAM_AWBMODE_CLOUDY,
        'shade':         mmal.MMAL_PARAM_AWBMODE_SHADE,
        'tungsten':      mmal.MMAL_PARAM_AWBMODE_TUNGSTEN,
        'fluorescent':   mmal.MMAL_PARAM_AWBMODE_FLUORESCENT,
        'incandescent':  mmal.MMAL_PARAM_AWBMODE_INCANDESCENT,
        'flash':         mmal.MMAL_PARAM_AWBMODE_FLASH,
        'horizon':       mmal.MMAL_PARAM_AWBMODE_HORIZON,
        }

    IMAGE_EFFECTS = {
        'none':          mmal.MMAL_PARAM_IMAGEFX_NONE,
        'negative':      mmal.MMAL_PARAM_IMAGEFX_NEGATIVE,
        'solarize':      mmal.MMAL_PARAM_IMAGEFX_SOLARIZE,
        'posterize':     mmal.MMAL_PARAM_IMAGEFX_POSTERIZE,
        'whiteboard':    mmal.MMAL_PARAM_IMAGEFX_WHITEBOARD,
        'blackboard':    mmal.MMAL_PARAM_IMAGEFX_BLACKBOARD,
        'sketch':        mmal.MMAL_PARAM_IMAGEFX_SKETCH,
        'denoise':       mmal.MMAL_PARAM_IMAGEFX_DENOISE,
        'emboss':        mmal.MMAL_PARAM_IMAGEFX_EMBOSS,
        'oilpaint':      mmal.MMAL_PARAM_IMAGEFX_OILPAINT,
        'hatch':         mmal.MMAL_PARAM_IMAGEFX_HATCH,
        'gpen':          mmal.MMAL_PARAM_IMAGEFX_GPEN,
        'pastel':        mmal.MMAL_PARAM_IMAGEFX_PASTEL,
        'watercolor':    mmal.MMAL_PARAM_IMAGEFX_WATERCOLOUR,
        'film':          mmal.MMAL_PARAM_IMAGEFX_FILM,
        'blur':          mmal.MMAL_PARAM_IMAGEFX_BLUR,
        'saturation':    mmal.MMAL_PARAM_IMAGEFX_SATURATION,
        'colorswap':     mmal.MMAL_PARAM_IMAGEFX_COLOURSWAP,
        'washedout':     mmal.MMAL_PARAM_IMAGEFX_WASHEDOUT,
        'posterise':     mmal.MMAL_PARAM_IMAGEFX_POSTERISE,
        'colorpoint':    mmal.MMAL_PARAM_IMAGEFX_COLOURPOINT,
        'colorbalance':  mmal.MMAL_PARAM_IMAGEFX_COLOURBALANCE,
        'cartoon':       mmal.MMAL_PARAM_IMAGEFX_CARTOON,
        }

    _METER_MODES_R    = {v: k for (k, v) in METER_MODES.items()}
    _EXPOSURE_MODES_R = {v: k for (k, v) in EXPOSURE_MODES.items()}
    _AWB_MODES_R      = {v: k for (k, v) in AWB_MODES.items()}
    _IMAGE_EFFECTS_R  = {v: k for (k, v) in IMAGE_EFFECTS.items()}

    def __init__(self):
        self._camera = None
        self._camera_config = None
        self._preview = None
        self._preview_connection = None
        self._video_encoder = None
        self._still_encoder = None
        self._exif_tags = {
            'IFD0.Model': 'RP_OV5647',
            'IFD0.Make': 'RaspberryPi',
            }
        self._camera = ct.POINTER(mmal.MMAL_COMPONENT_T)()
        self._camera_config = mmal.MMAL_PARAMETER_CAMERA_CONFIG_T(
            mmal.MMAL_PARAMETER_HEADER_T(
                mmal.MMAL_PARAMETER_CAMERA_CONFIG,
                ct.sizeof(mmal.MMAL_PARAMETER_CAMERA_CONFIG_T)
                ))
        _check(
            mmal.mmal_component_create(
                mmal.MMAL_COMPONENT_DEFAULT_CAMERA, self._camera),
            prefix="Failed to create camera component")
        try:
            if not self._camera[0].output_num:
                raise PiCameraError("Camera doesn't have output ports")

            _check(
                mmal.mmal_port_enable(
                    self._camera[0].control,
                    _control_callback),
                prefix="Unable to enable control port")

            cc = self._camera_config
            cc.max_stills_w=self.DEFAULT_RESOLUTION[0]
            cc.max_stills_h=self.DEFAULT_RESOLUTION[1]
            cc.stills_yuv422=0
            # XXX This is 1 in raspistill and 0 in raspivid ... doesn't seem to
            # make any difference though?
            cc.one_shot_stills=0
            cc.max_preview_video_w=self.DEFAULT_RESOLUTION[0]
            cc.max_preview_video_h=self.DEFAULT_RESOLUTION[1]
            cc.num_preview_video_frames=3
            cc.stills_capture_circular_buffer_height=0
            cc.fast_preview_resume=0
            cc.use_stc_timestamp=mmal.MMAL_PARAM_TIMESTAMP_MODE_RESET_STC
            _check(
                mmal.mmal_port_parameter_set(self._camera[0].control, cc.hdr),
                prefix="Camera control port couldn't be configured")

            for p in self.CAMERA_PORTS:
                port = self._camera[0].output[p]
                fmt = port[0].format
                fmt[0].encoding_variant = mmal.MMAL_ENCODING_I420
                fmt[0].encoding = mmal.MMAL_ENCODING_OPAQUE
                fmt[0].es[0].video.width = cc.max_preview_video_w
                fmt[0].es[0].video.height = cc.max_preview_video_h
                fmt[0].es[0].video.crop.x = 0
                fmt[0].es[0].video.crop.y = 0
                fmt[0].es[0].video.crop.width = cc.max_preview_video_w
                fmt[0].es[0].video.crop.height = cc.max_preview_video_h
                fmt[0].es[0].video.frame_rate.num = 1 if p == self.CAMERA_CAPTURE_PORT else self.DEFAULT_FRAME_RATE_NUM
                fmt[0].es[0].video.frame_rate.den = 1 if p == self.CAMERA_CAPTURE_PORT else self.DEFAULT_FRAME_RATE_DEN
                _check(
                    mmal.mmal_port_format_commit(self._camera[0].output[p]),
                    prefix="Camera %s format couldn't be set" % {
                        self.CAMERA_PREVIEW_PORT: "preview",
                        self.CAMERA_VIDEO_PORT:   "video",
                        self.CAMERA_CAPTURE_PORT: "still",
                        }[p])
                if p != self.CAMERA_PREVIEW_PORT:
                    port[0].buffer_num = max(
                        port[0].buffer_num,
                        self.VIDEO_OUTPUT_BUFFERS_NUM)

            _check(
                mmal.mmal_component_enable(self._camera),
                prefix="Camera component couldn't be enabled")

            self.sharpness = 0
            self.contrast = 0
            self.brightness = 50
            self.saturation = 0
            self.ISO = 400
            self.video_stabilization = False
            self.exposure_compensation = 0
            self.exposure_mode = 'auto'
            self.meter_mode = 'average'
            self.awb_mode = 'auto'
            self.image_effect = 'none'
            self.color_effects = None
            self.rotation = 0
            self.hflip = self.vflip = False
            self.crop = (0.0, 0.0, 1.0, 1.0)
        except:
            self.close()
            raise

    def _check_camera_open(self):
        if self.closed:
            raise PiCameraRuntimeError("Camera is closed")

    def _check_preview_stopped(self):
        if self.previewing:
            raise PiCameraRuntimeError("Preview is currently running")

    def _check_recording_stopped(self):
        if self.recording:
            raise PiCameraRuntimeError("Recording is currently running")

    def _get_format(self, output, format):
        if format:
            return format
        elif isinstance(output, (bytes, str)):
            filename = output
        elif hasattr(output, 'name'):
            filename = output.name
        else:
            raise PiCameraValueError(
                'Format must be specified when output has no filename')
        (type, encoding) = mimetypes.guess_type(filename)
        if type:
            return type
        raise PiCameraValueError(
            'Unable to determine type from filename %s' % filename)

    def close(self):
        """
        Finalizes the state of the camera.

        After successfully constructing a :class:`PiCamera` object, you should
        ensure you call the :meth:`close` method once you are finished with the
        camera (e.g. in the ``finally`` section of a ``try..finally`` block).
        This method stops all recording and preview activities and releases all
        resources associated with the camera; this is necessary to prevent GPU
        memory leaks.
        """
        if self.recording:
            self.stop_recording()
        if self.previewing:
            self.stop_preview()
        if self._camera:
            if self._camera[0].is_enabled:
                mmal.mmal_component_disable(self._camera)
            mmal.mmal_component_destroy(self._camera)
            self._camera = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.close()

    def start_preview(self):
        """
        Starts a preview session over the current display.

        This method starts a new preview running at the configured resolution
        (see :attr:`resolution`). Most camera properties can be modified "live"
        while the preview is running (e.g. :attr:`brightness`).  The preview
        typically overrides whatever is currently visible on the display. To
        stop the preview and reveal the display again, call
        :meth:`stop_preview`. The preview can be started and stopped multiple
        times during the lifetime of the :class:`PiCamera` object.
        """
        self._check_camera_open()
        self._check_preview_stopped()
        self._preview = ct.POINTER(mmal.MMAL_COMPONENT_T)()
        _check(
            mmal.mmal_component_create(
                mmal.MMAL_COMPONENT_DEFAULT_VIDEO_RENDERER, self._preview),
            prefix="Failed to create preview component")
        try:
            if not self._preview[0].input_num:
                raise PiCameraError("No input ports on preview component")

            mp = mmal.MMAL_DISPLAYREGION_T(
                mmal.MMAL_PARAMETER_HEADER_T(
                    mmal.MMAL_PARAMETER_DISPLAYREGION,
                    ct.sizeof(mmal.MMAL_DISPLAYREGION_T)
                    ),
                )
            mp.set = mmal.MMAL_DISPLAY_SET_LAYER
            mp.layer = self.PREVIEW_LAYER
            # TODO Allow configuration of alpha
            mp.set |= mmal.MMAL_DISPLAY_SET_ALPHA
            mp.alpha = self.PREVIEW_ALPHA
            # TODO Allow configuration of display rect
            mp.set |= mmal.MMAL_DISPLAY_SET_FULLSCREEN
            mp.fullscreen = 1
            _check(
                mmal.mmal_port_parameter_set(self._preview[0].input[0], mp.hdr),
                prefix="Unable to set preview port parameters")

            _check(
                mmal.mmal_component_enable(self._preview),
                prefix="Preview component couldn't be enabled")

            self._preview_connection = ct.POINTER(mmal.MMAL_CONNECTION_T)()
            _check(
                mmal.mmal_connection_create(
                    self._preview_connection,
                    self._camera[0].output[self.CAMERA_PREVIEW_PORT],
                    self._preview[0].input[0],
                    mmal.MMAL_CONNECTION_FLAG_TUNNELLING | mmal.MMAL_CONNECTION_FLAG_ALLOCATION_ON_INPUT),
                prefix="Failed to connect camera to preview")
            _check(
                mmal.mmal_connection_enable(self._preview_connection),
                prefix="Failed to enable preview connection")

        except:
            self.stop_preview()
            raise

    def stop_preview(self):
        """
        Stops the preview session and shuts down the preview window display.

        If :meth:`start_preview` has previously been called, this method shuts
        down the preview display which generally results in the underlying TTY
        becoming visible again. If a preview is not currently running, no
        exception is raised - the method will simply do nothing.
        """
        if self._preview_connection:
            mmal.mmal_connection_destroy(self._preview_connection)
            self._preview_connection = None
        if self._preview:
            if self._preview[0].is_enabled:
                mmal.mmal_component_disable(self._preview)
            mmal.mmal_component_destroy(self._preview)
            self._preview = None

    def start_recording(self, output, format=None, **options):
        """
        Start recording video from the camera, storing it as an H264 stream.

        If *output* is a string, it will be treated as a filename for a new
        file which the H264 stream will be written to. Otherwise, *output* is
        assumed to be a file-like object and the H264 data is appended to it
        (the implementation only assumes the object has a ``write()`` method -
        no other methods will be called).

        If *format* is ``None`` (the default), the method will attempt to guess
        the required video format from the extension of *output* (if it's a
        string), or from the *name* attribute of *output* (if it has one). In
        the case that the format cannot be determined, a
        :exc:`PiCameraValueError` will be raised.

        If *format* is not ``None``, it must be a string specifying the format
        that you want the image written to. The format can be a MIME-type or
        one of the following strings:

        * ``h264`` - Write an H.264 video stream
        """
        self._check_camera_open()
        self._check_recording_stopped()
        self._video_encoder = _PiVideoEncoder(self, format, **options)
        try:
            self._video_encoder.start(output)
        except Exception as e:
            self._video_encoder.close()
            raise

    def wait_recording(self, timeout=0):
        """
        Wait on the video encoder for timeout seconds.

        It is recommended that this method is called while recording to check
        for exceptions. If an error occurs during recording (for example out of
        disk space), an exception will only be raised when the
        :meth:`wait_recording` or :meth:`stop_recording` methods are called.

        If ``timeout`` is 0 (the default) the function will immediately return
        (or raise an exception if an error has occurred).
        """
        assert self._video_encoder
        assert timeout is not None
        self._video_encoder.wait(timeout)

    def stop_recording(self):
        """
        Stop recording video from the camera.

        After calling this method the video encoder will be shut down and
        output will stop being written to the file-like object specified with
        :meth:`start_recording`. If an error occurred during recording and
        :meth:`wait_recording` has not been called since the error then this
        method will raise the exception.
        """
        try:
            self.wait_recording(0)
        finally:
            self._video_encoder.close()
            self._video_encoder = None

    def capture(self, output, format=None, **options):
        """
        Capture an image from the camera, storing it in *output*.

        If *output* is a string, it will be treated as a filename for a new
        file which the JPEG data will be written to. Otherwise, *output* is
        assumed to a be a file-like object and the JPEG data is appended to it
        (the implementation only assumes the object has a ``write()`` method -
        no other methods will be called).

        If *format* is ``None`` (the default), the method will attempt to guess
        the required image format from the extension of *output* (if it's a
        string), or from the *name* attribute of *output* (if it has one). In
        the case that the format cannot be determined, a
        :exc:`PiCameraValueError` will be raised.

        If *format* is not ``None``, it must be a string specifying the format
        that you want the image written to. The format can be a MIME-type or
        one of the following strings:

        * ``'jpeg'`` - Write a JPEG file

        * ``'png'`` - Write a PNG file

        * ``'gif'`` - Write a GIF file

        * ``'bmp'`` - Write a bitmap file

        Certain file formats accept additional options which can be specified
        as keyword arguments. Currently, only the ``'jpeg'`` encoder accepts
        additional options, which are:

        * *quality* - Defines the quality of the JPEG encoder as an integer
            ranging from 1 to 100. Defaults to 85.

        * *thumbnail* - Defines the size and quality of the thumbnail to embed
            in the Exif data. Specifying ``None`` disables thumbnail
            generation.  Otherwise, specify a tuple of ``(width, height,
            quality)``. Defaults to ``(64, 48, 35)``.
        """
        self._check_camera_open()
        assert not self._still_encoder
        format = self._get_format(output, format)
        if format.startswith('image/'):
            format = format[6:]
        if format == 'x-ms-bmp':
            format = 'bmp'
        self._still_encoder = _PiStillEncoder(self, format)
        try:
            self._still_encoder.start(output)
            # Wait for the callback to set the event indicating the end of
            # image capture
            self._still_encoder.wait()
        finally:
            self._still_encoder.close()
            self._still_encoder = None

    @property
    def closed(self):
        """
        Returns True if the :meth:`close` method has been called.
        """
        return not self._camera

    @property
    def recording(self):
        """
        Returns True if the :meth:`start_recording` method has been called,
        and no :meth:`stop_recording` call has been made yet.
        """
        # XXX Should probably check this is actually enabled...
        return bool(self._video_encoder)

    @property
    def previewing(self):
        """
        Returns True if the :meth:`start_preview` method has been called,
        and no :meth:`stop_preview` call has been made yet.
        """
        # XXX Should probably check this is actually enabled...
        return bool(self._preview)

    @property
    def exif_tags(self):
        """
        Holds a mapping of the Exif tags to apply to captured images.

        By default several Exif tags are automatically applied to any images
        taken with the :meth:`capture` method: ``IFD0.Make`` (which is set to
        ``RaspberryPi``), ``IFD0.Model`` (which is set to ``RP_OV5647``), and
        three timestamp tags: ``IFD0.DateTime``, ``EXIF.DateTimeOriginal``, and
        ``EXIF.DateTimeDigitized`` which are all set to the current date and
        time just before the picture is taken.

        If you wish to set additional Exif tags, or override any of the
        aforementioned tags, simply add entries to the exif_tags map before
        calling :meth:`capture`. For example::

            camera.exif_tags['IFD0.Copyright'] = 'Copyright (c) 2013 Foo Industries'

        The Exif standard mandates ASCII encoding for all textual values, hence
        strings containing non-ASCII characters will cause an encoding error to
        be raised when :meth:`capture` is called.  If you wish to set binary
        values, use a :func:`bytes` value::

            camera.exif_tags['EXIF.UserComment'] = b'Something containing\\x00NULL characters'

        .. warning::
            Binary Exif values are currently ignored; this appears to be a
            libmmal or firmware bug.

        The currently supported Exif tags are:

        +-------+-------------------------------------------------------------+
        | Group | Tags                                                        |
        +=======+=============================================================+
        | IFD0/ | ImageWidth, ImageLength, BitsPerSample, Compression,        |
        | IFD1  | PhotometricInterpretation, ImageDescription, Make, Model,   |
        |       | StripOffsets, Orientation, SamplesPerPixel, RowsPerString,  |
        |       | StripByteCounts, Xresolution, Yresolution,                  |
        |       | PlanarConfiguration, ResolutionUnit, TransferFunction,      |
        |       | Software, DateTime, Artist, WhitePoint,                     |
        |       | PrimaryChromaticities, JPEGInterchangeFormat,               |
        |       | JPEGInterchangeFormatLength, YcbCrCoefficients,             |
        |       | YcbCrSubSampling, YcbCrPositioning, ReferenceBlackWhite,    |
        |       | Copyright                                                   |
        +-------+-------------------------------------------------------------+
        | EXIF  | ExposureTime, FNumber, ExposureProgram,                     |
        |       | SpectralSensitivity, ISOSpeedRatings, OECF, ExifVersion,    |
        |       | DateTimeOriginal, DateTimeDigitized,                        |
        |       | ComponentsConfiguration, CompressedBitsPerPixel,            |
        |       | ShutterSpeedValue, ApertureValue, BrightnessValue,          |
        |       | ExposureBiasValue, MaxApertureValue, SubjectDistance,       |
        |       | MeteringMode, LightSource, Flash, FocalLength, SubjectArea, |
        |       | MakerNote, UserComment, SubSecTime, SubSecTimeOriginal,     |
        |       | SubSecTimeDigitized, FlashpixVersion, ColorSpace,           |
        |       | PixelXDimension, PixelYDimension, RelatedSoundFile,         |
        |       | FlashEnergy, SpacialFrequencyResponse,                      |
        |       | FocalPlaneXResolution, FocalPlaneYResolution,               |
        |       | FocalPlaneResolutionUnit, SubjectLocation, ExposureIndex,   |
        |       | SensingMethod, FileSource, SceneType, CFAPattern,           |
        |       | CustomRendered, ExposureMode, WhiteBalance,                 |
        |       | DigitalZoomRatio, FocalLengthIn35mmFilm, SceneCaptureType,  |
        |       | GainControl, Contrast, Saturation, Sharpness,               |
        |       | DeviceSettingDescription, SubjectDistanceRange,             |
        |       | ImageUniqueID                                               |
        +-------+-------------------------------------------------------------+
        | GPS   | GPSVersionID, GPSLatitudeRef, GPSLatitude, GPSLongitudeRef, |
        |       | GPSLongitude, GPSAltitudeRef, GPSAltitude, GPSTimeStamp,    |
        |       | GPSSatellites, GPSStatus, GPSMeasureMode, GPSDOP,           |
        |       | GPSSpeedRef, GPSSpeed, GPSTrackRef, GPSTrack,               |
        |       | GPSImgDirectionRef, GPSImgDirection, GPSMapDatum,           |
        |       | GPSDestLatitudeRef, GPSDestLatitude, GPSDestLongitudeRef,   |
        |       | GPSDestLongitude, GPSDestBearingRef, GPSDestBearing,        |
        |       | GPSDestDistanceRef, GPSDestDistance, GPSProcessingMethod,   |
        |       | GPSAreaInformation, GPSDateStamp, GPSDifferential           |
        +-------+-------------------------------------------------------------+
        | EINT  | InteroperabilityIndex, InteroperabilityVersion,             |
        |       | RelatedImageFileFormat, RelatedImageWidth,                  |
        |       | RelatedImageLength>                                         |
        +-------+-------------------------------------------------------------+

        .. note::
            Please note that Exif tagging is only supported with the ``jpeg``
            format.
        """
        return self._exif_tags

    def _get_resolution(self):
        self._check_camera_open()
        return (
            self._camera_config.max_stills_w,
            self._camera_config.max_stills_h
            )
    def _set_resolution(self, value):
        self._check_camera_open()
        self._check_preview_stopped()
        self._check_recording_stopped()
        try:
            w, h = value
        except (TypeError, ValueError) as e:
            raise PiCameraValueError(
                "Invalid resolution (width, height) tuple: %s" % value)
        _check(
            mmal.mmal_component_disable(self._camera),
            prefix="Failed to disable camera")
        self._camera_config.max_stills_w = w
        self._camera_config.max_stills_h = h
        self._camera_config.max_preview_video_w = w
        self._camera_config.max_preview_video_h = h
        _check(
            mmal.mmal_port_parameter_set(self._camera[0].control, self._camera_config.hdr),
            prefix="Failed to set preview resolution")
        for port in (self.CAMERA_CAPTURE_PORT, self.CAMERA_VIDEO_PORT, self.CAMERA_PREVIEW_PORT):
            fmt = self._camera[0].output[port][0].format[0].es[0]
            fmt.video.width = w
            fmt.video.height = h
            fmt.video.crop.x = 0
            fmt.video.crop.y = 0
            fmt.video.crop.width = w
            fmt.video.crop.height = h
            # At resolutions higher than 1080p, drop the frame rate (GPU can
            # only manage 15fps at full frame)
            if port == self.CAMERA_CAPTURE_PORT:
                fmt.video.frame_rate.num = 1
                fmt.video.frame_rate.den = 1
            elif (w > self.DEFAULT_RESOLUTION[0]) or (h > self.DEFAULT_RESOLUTION[1]):
                fmt.video.frame_rate.num = self.FULL_FRAME_RATE_NUM
                fmt.video.frame_rate.den = self.FULL_FRAME_RATE_DEN
            else:
                fmt.video.frame_rate.num = self.DEFAULT_FRAME_RATE_NUM
                fmt.video.frame_rate.den = self.DEFAULT_FRAME_RATE_DEN
            _check(
                mmal.mmal_port_format_commit(self._camera[0].output[port]),
                prefix="Camera video format couldn't be set")
        _check(
            mmal.mmal_component_enable(self._camera),
            prefix="Failed to enable camera")
    resolution = property(
        _get_resolution, _set_resolution, doc="""
        Retrieves or sets the resolution at which image captures, video
        recordings, and previews will be captured.

        When queried, the :attr:`resolution` property returns the resolution at
        which the camera will operate as a tuple of ``(width, height)``
        measured in pixels. This is the resolution that the :meth:`capture`
        method will produce images at, the resolution that
        :meth:`start_recording` will produce videos at, and the resolution that
        :meth:`start_preview` will capture frames at.

        When set, the property reconfigures the camera so that the next call to
        these methods will use the new resolution.  The resolution must be
        specified as a ``(width, height)`` tuple, the camera must not be
        closed, and no preview or recording must be active when the property is
        set.

        The property defaults to the standard 1080p resolution of ``(1920,
        1080)``.

        .. note::
            Setting a resolution higher than 1080p will automatically cause
            previews to run at a reduced frame rate of 15fps (resolutions at or
            below 1080p use 30fps). This is due to GPU processing limits.
        """)

    def _get_saturation(self):
        self._check_camera_open()
        mp = mmal.MMAL_RATIONAL_T()
        _check(
            mmal.mmal_port_parameter_get_rational(
                self._camera[0].control,
                mmal.MMAL_PARAMETER_SATURATION,
                mp
                ),
            prefix="Failed to get saturation")
        return mp.num
    def _set_saturation(self, value):
        self._check_camera_open()
        try:
            if not (-100 <= value <= 100):
                raise PiCameraValueError("Invalid saturation value: %d (valid range -100..100)" % value)
        except TypeError:
            raise PiCameraValueError("Invalid saturation value: %s" % value)
        _check(
            mmal.mmal_port_parameter_set_rational(
                self._camera[0].control,
                mmal.MMAL_PARAMETER_SATURATION,
                mmal.MMAL_RATIONAL_T(value, 100)
                ),
            prefix="Failed to set saturation")
    saturation = property(_get_saturation, _set_saturation, doc="""
        Retrieves or sets the saturation setting of the camera.

        When queried, the :attr:`saturation` property returns the color
        saturation of the camera as an integer between -100 and 100. When set,
        the property adjusts the saturation of the camera. Saturation can be
        adjusted while previews or recordings are in progress. The default
        value is 0.
        """)

    def _get_sharpness(self):
        self._check_camera_open()
        mp = mmal.MMAL_RATIONAL_T()
        _check(
            mmal.mmal_port_parameter_get_rational(
                self._camera[0].control,
                mmal.MMAL_PARAMETER_SHARPNESS,
                mp
                ),
            prefix="Failed to get sharpness")
        return mp.num
    def _set_sharpness(self, value):
        self._check_camera_open()
        try:
            if not (-100 <= value <= 100):
                raise PiCameraValueError("Invalid sharpness value: %d (valid range -100..100)" % value)
        except TypeError:
            raise PiCameraValueError("Invalid sharpness value: %s" % value)
        _check(
            mmal.mmal_port_parameter_set_rational(
                self._camera[0].control,
                mmal.MMAL_PARAMETER_SHARPNESS,
                mmal.MMAL_RATIONAL_T(value, 100)
                ),
            prefix="Failed to set sharpness")
    sharpness = property(_get_sharpness, _set_sharpness, doc="""
        Retrieves or sets the sharpness setting of the camera.

        When queried, the :attr:`sharpness` property returns the sharpness
        level of the camera (a measure of the amount of post-processing to
        reduce or increase image sharpness) as an integer between -100 and 100.
        When set, the property adjusts the sharpness of the camera. Sharpness
        can be adjusted while previews or recordings are in progress. The
        default value is 0.
        """)

    def _get_contrast(self):
        self._check_camera_open()
        mp = mmal.MMAL_RATIONAL_T()
        _check(
            mmal.mmal_port_parameter_get_rational(
                self._camera[0].control,
                mmal.MMAL_PARAMETER_CONTRAST,
                mp
                ),
            prefix="Failed to get contrast")
        return mp.num
    def _set_contrast(self, value):
        self._check_camera_open()
        try:
            if not (-100 <= value <= 100):
                raise PiCameraValueError("Invalid contrast value: %d (valid range -100..100)" % value)
        except TypeError:
            raise PiCameraValueError("Invalid contrast value: %s" % value)
        _check(
            mmal.mmal_port_parameter_set_rational(
                self._camera[0].control,
                mmal.MMAL_PARAMETER_CONTRAST,
                mmal.MMAL_RATIONAL_T(value, 100)
                ),
            prefix="Failed to set contrast")
    contrast = property(_get_contrast, _set_contrast, doc="""
        Retrieves or sets the contrast setting of the camera.

        When queried, the :attr:`contrast` property returns the contrast level
        of the camera as an integer between -100 and 100.  When set, the
        property adjusts the contrast of the camera. Contrast can be adjusted
        while previews or recordings are in progress. The default value is 0.
        """)

    def _get_brightness(self):
        self._check_camera_open()
        mp = mmal.MMAL_RATIONAL_T()
        _check(
            mmal.mmal_port_parameter_get_rational(
                self._camera[0].control,
                mmal.MMAL_PARAMETER_BRIGHTNESS,
                mp
                ),
            prefix="Failed to get brightness")
        return mp.num
    def _set_brightness(self, value):
        self._check_camera_open()
        try:
            if not (0 <= value <= 100):
                raise PiCameraValueError("Invalid brightness value: %d (valid range 0..100)" % value)
        except TypeError:
            raise PiCameraValueError("Invalid brightness value: %s" % value)
        _check(
            mmal.mmal_port_parameter_set_rational(
                self._camera[0].control,
                mmal.MMAL_PARAMETER_BRIGHTNESS,
                mmal.MMAL_RATIONAL_T(value, 100)
                ),
            prefix="Failed to set brightness")
    brightness = property(_get_brightness, _set_brightness, doc="""
        Retrieves or sets the brightness setting of the camera.

        When queried, the :attr:`brightness` property returns the brightness
        level of the camera as an integer between 0 and 100.  When set, the
        property adjusts the brightness of the camera. Brightness can be
        adjusted while previews or recordings are in progress. The default
        value is 50.
        """)

    def _get_ISO(self):
        self._check_camera_open()
        mp = ct.c_uint32()
        _check(
            mmal.mmal_port_parameter_get_uint32(
                self._camera[0].control,
                mmal.MMAL_PARAMETER_ISO,
                mp
                ),
            prefix="Failed to get ISO")
        return mp.value
    def _set_ISO(self, value):
        self._check_camera_open()
        # XXX Valid values?
        _check(
            mmal.mmal_port_parameter_set_uint32(
                self._camera[0].control,
                mmal.MMAL_PARAMETER_ISO,
                value
                ),
            prefix="Failed to set ISO")
    ISO = property(_get_ISO, _set_ISO, doc="""
        Retrieves or sets the apparent ISO setting of the camera.

        When queried, the :attr:`ISO` property returns the ISO setting of the
        camera, a value which represents the `sensitivity of the camera to
        light`_. Lower ISO speeds (e.g. 100) imply less sensitivity than higher
        ISO speeds (e.g. 400 or 800). Lower sensitivities tend to produce less
        "noisy" (smoother) images, but operate poorly in low light conditions.

        When set, the property adjusts the sensitivity of the camera. The valid
        limits are currently undocumented, but a range of 100 to 1600 would
        seem reasonable. ISO can be adjusted while previews or recordings are
        in progress. The default value is 400.

        .. note::
            Currently, adjusting this value doesn't seem to do anything. The
            author has tried assigning values of 0 to 100,000 with no apparent
            effect (nor any error occurring).

        .. _sensitivity of the camera to light: http://en.wikipedia.org/wiki/Film_speed#Digital
        """)

    def _get_meter_mode(self):
        self._check_camera_open()
        mp = mmal.MMAL_PARAMETER_EXPOSUREMETERINGMODE_T(
            mmal.MMAL_PARAMETER_HEADER_T(
                mmal.MMAL_PARAMETER_EXP_METERING_MODE,
                ct.sizeof(mmal.MMAL_PARAMETER_EXPOSUREMETERINGMODE_T)
                ))
        _check(
            mmal.mmal_port_parameter_get(self._camera[0].control, mp.hdr),
            prefix="Failed to get meter mode")
        return self._METER_MODES_R[mp.value]
    def _set_meter_mode(self, value):
        self._check_camera_open()
        try:
            mp = mmal.MMAL_PARAMETER_EXPOSUREMETERINGMODE_T(
                mmal.MMAL_PARAMETER_HEADER_T(
                    mmal.MMAL_PARAMETER_EXP_METERING_MODE,
                    ct.sizeof(mmal.MMAL_PARAMETER_EXPOSUREMETERINGMODE_T)
                    ),
                self.METER_MODES[value]
                )
            _check(
                mmal.mmal_port_parameter_set(self._camera[0].control, mp.hdr),
                prefix="Failed to set meter mode")
        except KeyError:
            raise PiCameraValueError("Invalid metering mode: %s" % value)
    meter_mode = property(_get_meter_mode, _set_meter_mode, doc="""
        Retrieves or sets the metering mode of the camera.

        When queried, the :attr:`meter_mode` property returns the method by
        which the camera `determines the exposure`_ as one of the following
        strings:

        +---------------+---------------------------------------------------+
        | value         | description                                       |
        +===============+===================================================+
        | ``'average'`` | The camera measures the average of the entire     |
        |               | scene.                                            |
        +---------------+---------------------------------------------------+
        | ``'spot'``    | The camera measures the center of the scene.      |
        +---------------+---------------------------------------------------+
        | ``'backlit'`` | The camera measures a larger central area,        |
        |               | ignoring the edges of the scene.                  |
        +---------------+---------------------------------------------------+
        | ``'matrix'``  | The camera measures several points within the     |
        |               | scene.                                            |
        +---------------+---------------------------------------------------+

        When set, the property adjusts the camera's metering mode. The property
        can be set while recordings or previews are in progress. The default
        value is ``'average'``. All possible values for the attribute can be
        obtained from the ``PiCamera.METER_MODES`` attribute.

        .. _determines the exposure: http://en.wikipedia.org/wiki/Metering_mode
        """)

    def _get_video_stabilization(self):
        self._check_camera_open()
        mp = mmal.MMAL_BOOL_T()
        _check(
            mmal.mmal_port_parameter_get_boolean(
                self._camera[0].control,
                mmal.MMAL_PARAMETER_VIDEO_STABILISATION,
                mp
                ),
            prefix="Failed to get video stabilization")
        return mp.value != mmal.MMAL_FALSE
    def _set_video_stabilization(self, value):
        self._check_camera_open()
        try:
            _check(
                mmal.mmal_port_parameter_set_boolean(
                    self._camera[0].control,
                    mmal.MMAL_PARAMETER_VIDEO_STABILISATION,
                    {
                        False: mmal.MMAL_FALSE,
                        True:  mmal.MMAL_TRUE,
                        }[value]
                    ),
                prefix="Failed to set video stabilization")
        except KeyError:
            raise PiCameraValueError("Invalid video stabilization boolean value: %s" % value)
    video_stabilization = property(
        _get_video_stabilization, _set_video_stabilization, doc="""
        Retrieves or sets the video stabilization mode of the camera.

        When queried, the :attr:`video_stabilization` property returns a
        boolean value indicating whether or not the camera attempts to
        compensate for motion.

        When set, the property activates or deactivates video stabilization.
        The property can be set while recordings or previews are in progress.
        The default value is ``False``.

        .. warning::
            The built-in video stabilization only accounts for `vertical and
            horizontal motion`_, not rotation.

        .. _vertical and horizontal motion: http://www.raspberrypi.org/phpBB3/viewtopic.php?p=342667&sid=ec7d95e887ab74a90ffaab87888c48cd#p342667
        """)

    def _get_exposure_compensation(self):
        self._check_camera_open()
        mp = ct.c_int32()
        _check(
            mmal.mmal_port_parameter_get_int32(
                self._camera[0].control,
                mmal.MMAL_PARAMETER_EXPOSURE_COMP,
                mp
                ),
            prefix="Failed to get exposure compensation")
        return mp.value
    def _set_exposure_compensation(self, value):
        self._check_camera_open()
        try:
            if not (-25 <= value <= 25):
                raise PiCameraValueError("Invalid exposure compensation value: %d (valid range -25..25)" % value)
        except TypeError:
            raise PiCameraValueError("Invalid exposure compensation value: %s" % value)
        _check(
            mmal.mmal_port_parameter_set_int32(
                self._camera[0].control,
                mmal.MMAL_PARAMETER_EXPOSURE_COMP,
                value
                ),
            prefix="Failed to set exposure compensation")
    exposure_compensation = property(
        _get_exposure_compensation, _set_exposure_compensation, doc="""
        Retrieves or sets the exposure compensation level of the camera.

        When queried, the :attr:`exposure_compensation` property returns an
        integer value between -25 and 25 indicating the exposure level of the
        camera. Larger values result in brighter images.

        When set, the property adjusts the camera's exposure compensation
        level. The property can be set while recordings or previews are in
        progress. The default value is ``0``.
        """)

    def _get_exposure_mode(self):
        self._check_camera_open()
        mp = mmal.MMAL_PARAMETER_EXPOSUREMODE_T(
            mmal.MMAL_PARAMETER_HEADER_T(
                mmal.MMAL_PARAMETER_EXPOSURE_MODE,
                ct.sizeof(mmal.MMAL_PARAMETER_EXPOSUREMODE_T)
                ))
        _check(
            mmal.mmal_port_parameter_get(self._camera[0].control, mp.hdr),
            prefix="Failed to get exposure mode")
        return self._EXPOSURE_MODES_R[mp.value]
    def _set_exposure_mode(self, value):
        self._check_camera_open()
        try:
            mp = mmal.MMAL_PARAMETER_EXPOSUREMODE_T(
                mmal.MMAL_PARAMETER_HEADER_T(
                    mmal.MMAL_PARAMETER_EXPOSURE_MODE,
                    ct.sizeof(mmal.MMAL_PARAMETER_EXPOSUREMODE_T)
                    ),
                self.EXPOSURE_MODES[value]
                )
            _check(
                mmal.mmal_port_parameter_set(self._camera[0].control, mp.hdr),
                prefix="Failed to set exposure mode")
        except KeyError:
            raise PiCameraValueError("Invalid exposure mode: %s" % value)
    exposure_mode = property(_get_exposure_mode, _set_exposure_mode, doc="""
        Retrieves or sets the exposure mode of the camera.

        When queried, the :attr:`exposure_mode` property returns a string
        representing the exposure setting of the camera. The possible values
        can be obtained from the ``PiCamera.EXPOSURE_MODES`` attribute.

        When set, the property adjusts the camera's exposure mode.  The
        property can be set while recordings or previews are in progress. The
        default value is ``'auto'``.
        """)

    def _get_awb_mode(self):
        self._check_camera_open()
        mp = mmal.MMAL_PARAMETER_AWBMODE_T(
            mmal.MMAL_PARAMETER_HEADER_T(
                mmal.MMAL_PARAMETER_AWB_MODE,
                ct.sizeof(mmal.MMAL_PARAMETER_AWBMODE_T)
                ))
        _check(
            mmal.mmal_port_parameter_get(self._camera[0].control, mp.hdr),
            prefix="Failed to get auto-white-balance mode")
        return self._AWB_MODES_R[mp.value]
    def _set_awb_mode(self, value):
        self._check_camera_open()
        try:
            mp = mmal.MMAL_PARAMETER_AWBMODE_T(
                mmal.MMAL_PARAMETER_HEADER_T(
                    mmal.MMAL_PARAMETER_AWB_MODE,
                    ct.sizeof(mmal.MMAL_PARAMETER_AWBMODE_T)
                    ),
                self.AWB_MODES[value]
                )
            _check(
                mmal.mmal_port_parameter_set(self._camera[0].control, mp.hdr),
                prefix="Failed to set auto-white-balance mode")
        except KeyError:
            raise PiCameraValueError("Invalid auto-white-balance mode: %s" % value)
    awb_mode = property(_get_awb_mode, _set_awb_mode, doc="""
        Retrieves or sets the auto-white-balance mode of the camera.

        When queried, the :attr:`awb_mode` property returns a string
        representing the auto-white-balance setting of the camera. The possible
        values can be obtained from the ``PiCamera.AWB_MODES`` attribute.

        When set, the property adjusts the camera's auto-white-balance mode.
        The property can be set while recordings or previews are in progress.
        The default value is ``'auto'``.
        """)

    def _get_image_effect(self):
        self._check_camera_open()
        mp = mmal.MMAL_PARAMETER_IMAGEFX_T(
            mmal.MMAL_PARAMETER_HEADER_T(
                mmal.MMAL_PARAMETER_IMAGE_EFFECT,
                ct.sizeof(mmal.MMAL_PARAMETER_IMAGEFX_T)
                ))
        _check(
            mmal.mmal_port_parameter_get(self._camera[0].control, mp.hdr),
            prefix="Failed to get image effect")
        return self._IMAGE_EFFECTS_R[mp.value]
    def _set_image_effect(self, value):
        self._check_camera_open()
        try:
            mp = mmal.MMAL_PARAMETER_IMAGEFX_T(
                mmal.MMAL_PARAMETER_HEADER_T(
                    mmal.MMAL_PARAMETER_IMAGE_EFFECT,
                    ct.sizeof(mmal.MMAL_PARAMETER_IMAGEFX_T)
                    ),
                self.IMAGE_EFFECTS[value]
                )
            _check(
                mmal.mmal_port_parameter_set(self._camera[0].control, mp.hdr),
                prefix="Failed to set image effect")
        except KeyError:
            raise PiCameraValueError("Invalid image effect: %s" % value)
    image_effect = property(_get_image_effect, _set_image_effect, doc="""
        Retrieves or sets the current image effect applied by the camera.

        When queried, the :attr:`image_effect` property returns a string
        representing the effect the camera will apply to captured video. The
        possible values can be obtained from the ``PiCamera.IMAGE_EFFECTS``
        attribute.

        When set, the property changes the effect applied by the camera.  The
        property can be set while recordings or previews are in progress, but
        only certain effects work while recording video (notably ``'negative'``
        and ``'solarize'``). The default value is ``'none'``.
        """)

    def _get_color_effects(self):
        self._check_camera_open()
        mp = mmal.MMAL_PARAMETER_COLOURFX_T(
            mmal.MMAL_PARAMETER_HEADER_T(
                mmal.MMAL_PARAMETER_COLOUR_EFFECT,
                ct.sizeof(mmal.MMAL_PARAMETER_COLOURFX_T)
                ))
        _check(
            mmal.mmal_port_parameter_get(self._camera[0].control, mp.hdr),
            prefix="Failed to get color effects")
        if mp.enable != mmal.MMAL_FALSE:
            return (mp.u, mp.v)
        else:
            return None
    def _set_color_effects(self, value):
        self._check_camera_open()
        if value is None:
            enable = mmal.MMAL_FALSE
            u = v = 128
        else:
            enable = mmal.MMAL_TRUE
            try:
                u, v = value
            except (TypeError, ValueError) as e:
                raise PiCameraValueError(
                    "Invalid color effect (u, v) tuple: %s" % value)
            if not ((0 <= u <= 255) and (0 <= v <= 255)):
                raise PiCameraValueError(
                    "(u, v) values must be between 0 and 255")
        mp = mmal.MMAL_PARAMETER_COLOURFX_T(
            mmal.MMAL_PARAMETER_HEADER_T(
                mmal.MMAL_PARAMETER_COLOUR_EFFECT,
                ct.sizeof(mmal.MMAL_PARAMETER_COLOURFX_T)
                ),
            enable, u, v
            )
        _check(
            mmal.mmal_port_parameter_set(self._camera[0].control, mp.hdr),
            prefix="Failed to set color effects")
    color_effects = property(_get_color_effects, _set_color_effects, doc="""
        Retrieves or sets the current color effect applied by the camera.

        When queried, the :attr:`color_effect` property either returns ``None``
        which indicates that the camera is using normal color settings, or a
        ``(u, v)`` tuple where ``u`` and ``v`` are integer values between 0 and
        255.

        When set, the property changes the color effect applied by the camera.
        The property can be set while recordings or previews are in progress.
        For example, to make the image black and white set the value to ``(128,
        128)``. The default value is ``None``.
        """)

    def _get_rotation(self):
        self._check_camera_open()
        mp = ct.c_int32()
        _check(
            mmal.mmal_port_parameter_get_int32(
                self._camera[0].output[0],
                mmal.MMAL_PARAMETER_ROTATION,
                mp
                ),
            prefix="Failed to get rotation")
        return mp.value
    def _set_rotation(self, value):
        self._check_camera_open()
        try:
            value = ((int(value) % 360) // 90) * 90
        except ValueError:
            raise PiCameraValueError("Invalid rotation angle: %s" % value)
        for p in self.CAMERA_PORTS:
            _check(
                mmal.mmal_port_parameter_set_int32(
                    self._camera[0].output[p],
                    mmal.MMAL_PARAMETER_ROTATION,
                    value
                    ),
                prefix="Failed to set rotation")
    rotation = property(_get_rotation, _set_rotation, doc="""
        Retrieves or sets the current rotation of the camera's image.

        When queried, the :attr:`rotation` property returns the rotation
        applied to the image. Valid values are 0, 90, 180, and 270.

        When set, the property changes the color effect applied by the camera.
        The property can be set while recordings or previews are in progress.
        The default value is ``0``.
        """)

    def _get_vflip(self):
        self._check_camera_open()
        mp = mmal.MMAL_PARAMETER_MIRROR_T(
            mmal.MMAL_PARAMETER_HEADER_T(
                mmal.MMAL_PARAMETER_MIRROR,
                ct.sizeof(mmal.MMAL_PARAMETER_MIRROR_T)
                ))
        _check(
            mmal.mmal_port_parameter_get(self._camera[0].output[0], mp.hdr),
            prefix="Failed to get vertical flip")
        return mp.value in (mmal.MMAL_PARAM_MIRROR_VERTICAL, mmal.MMAL_PARAM_MIRROR_BOTH)
    def _set_vflip(self, value):
        self._check_camera_open()
        value = bool(value)
        for p in self.CAMERA_PORTS:
            mp = mmal.MMAL_PARAMETER_MIRROR_T(
                mmal.MMAL_PARAMETER_HEADER_T(
                    mmal.MMAL_PARAMETER_MIRROR,
                    ct.sizeof(mmal.MMAL_PARAMETER_MIRROR_T)
                    ),
                {
                    (False, False): mmal.MMAL_PARAM_MIRROR_NONE,
                    (True,  False): mmal.MMAL_PARAM_MIRROR_VERTICAL,
                    (False, True):  mmal.MMAL_PARAM_MIRROR_HORIZONTAL,
                    (True,  True):  mmal.MMAL_PARAM_MIRROR_BOTH,
                    }[(value, self.hflip)]
                )
            _check(
                mmal.mmal_port_parameter_set(self._camera[0].output[p], mp.hdr),
                prefix="Failed to set vertical flip")
    vflip = property(_get_vflip, _set_vflip, doc="""
        Retrieves or sets whether the camera's output is vertically flipped.

        When queried, the :attr:`vflip` property returns a boolean indicating
        whether or not the camera's output is vertically flipped. The property
        can be set while recordings or previews are in progress. The default
        value is ``False``.
        """)

    def _get_hflip(self):
        self._check_camera_open()
        mp = mmal.MMAL_PARAMETER_MIRROR_T(
            mmal.MMAL_PARAMETER_HEADER_T(
                mmal.MMAL_PARAMETER_MIRROR,
                ct.sizeof(mmal.MMAL_PARAMETER_MIRROR_T)
                ))
        _check(
            mmal.mmal_port_parameter_get(self._camera[0].output[0], mp.hdr),
            prefix="Failed to get horizontal flip")
        return mp.value in (mmal.MMAL_PARAM_MIRROR_HORIZONTAL, mmal.MMAL_PARAM_MIRROR_BOTH)
    def _set_hflip(self, value):
        self._check_camera_open()
        value = bool(value)
        for p in self.CAMERA_PORTS:
            mp = mmal.MMAL_PARAMETER_MIRROR_T(
                mmal.MMAL_PARAMETER_HEADER_T(
                    mmal.MMAL_PARAMETER_MIRROR,
                    ct.sizeof(mmal.MMAL_PARAMETER_MIRROR_T)
                    ),
                {
                    (False, False): mmal.MMAL_PARAM_MIRROR_NONE,
                    (True,  False): mmal.MMAL_PARAM_MIRROR_VERTICAL,
                    (False, True):  mmal.MMAL_PARAM_MIRROR_HORIZONTAL,
                    (True,  True):  mmal.MMAL_PARAM_MIRROR_BOTH,
                    }[(self.vflip, value)]
                )
            _check(
                mmal.mmal_port_parameter_set(self._camera[0].output[p], mp.hdr),
                prefix="Failed to set horizontal flip")
    hflip = property(_get_hflip, _set_hflip, doc="""
        Retrieves or sets whether the camera's output is horizontally flipped.

        When queried, the :attr:`hflip` property returns a boolean indicating
        whether or not the camera's output is horizontally flipped. The
        property can be set while recordings or previews are in progress. The
        default value is ``False``.
        """)

    def _get_crop(self):
        self._check_camera_open()
        mp = mmal.MMAL_PARAMETER_INPUT_CROP_T(
            mmal.MMAL_PARAMETER_HEADER_T(
                mmal.MMAL_PARAMETER_INPUT_CROP,
                ct.sizeof(mmal.MMAL_PARAMETER_INPUT_CROP_T)
                ))
        _check(
            mmal.mmal_port_parameter_get(self._camera[0].control, mp.hdr),
            prefix="Failed to get crop")
        return (
            mp[0].rect.x / 65535.0,
            mp[0].rect.y / 65535.0,
            mp[0].rect.width / 65535.0,
            mp[0].rect.height / 65535.0,
            )
    def _set_crop(self, value):
        self._check_camera_open()
        try:
            x, y, w, h = value
        except (TypeError, ValueError) as e:
            raise PiCameraValueError("Invalid crop rectangle (x, y, w, h) tuple: %s" % value)
        mp = mmal.MMAL_PARAMETER_INPUT_CROP_T(
            mmal.MMAL_PARAMETER_HEADER_T(
                mmal.MMAL_PARAMETER_INPUT_CROP,
                ct.sizeof(mmal.MMAL_PARAMETER_INPUT_CROP_T)
                ),
            mmal.MMAL_RECT_T(
                int(65535 * x),
                int(65535 * y),
                int(65535 * w),
                int(65535 * h)
                ),
            )
        _check(
            mmal.mmal_port_parameter_set(self._camera[0].control, mp.hdr),
            prefix="Failed to set crop")
    crop = property(_get_crop, _set_crop, doc="""
        Retrieves or sets the crop applied to the camera's input.

        When queried, the :attr:`crop` property returns a ``(x, y, w, h)``
        tuple of floating point values ranging from 0.0 to 1.0, indicating the
        proportion of the image to include in the output. The default value is
        ``(0.0, 0.0, 1.0, 1.0)`` which indicates that everything should be
        included. The property can be set while recordings or previews are in
        progress.
        """)


bcm_host.bcm_host_init()

