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

import warnings
import datetime
import mimetypes
import ctypes as ct
import fractions

import picamera.mmal as mmal
import picamera.bcm_host as bcm_host
from picamera.exc import (
    PiCameraError,
    PiCameraValueError,
    PiCameraRuntimeError,
    mmal_check,
    )
from picamera.encoders import (
    PiVideoFrame,
    PiVideoEncoder,
    PiImageEncoder,
    PiRawOneImageEncoder,
    PiRawMultiImageEncoder,
    PiCookedOneImageEncoder,
    PiCookedMultiImageEncoder,
    )

try:
    import RPi.GPIO as GPIO
except ImportError:
    # Can't find RPi.GPIO so just null-out the reference
    GPIO = None


__all__ = ['PiCamera']


def _control_callback(port, buf):
    if buf[0].cmd != mmal.MMAL_EVENT_PARAMETER_CHANGED:
        raise PiCameraRuntimeError(
            "Received unexpected camera control callback event, 0x%08x" % buf[0].cmd)
    mmal.mmal_buffer_header_release(buf)
_control_callback = mmal.MMAL_PORT_BH_CB_T(_control_callback)


# Guardian variable set upon initialization of PiCamera and used to ensure that
# no more than one PiCamera is instantiated at a given time
_CAMERA = None


class PiCameraFraction(fractions.Fraction):
    """
    Extends :class:`~fractions.Fraction` to act as a (numerator, denominator)
    tuple when required.
    """
    def __len__(self):
        return 2

    def __getitem__(self, index):
        if index == 0:
            return self.numerator
        elif index == 1:
            return self.denominator
        else:
            raise IndexError('invalid index %d' % index)

    def __contains__(self, value):
        return value in (self.numerator, self.denominator)


def to_rational(value):
    """
    Converts a value to a numerator, denominator tuple.

    Given a :class:`int`, :class:`float`, or :class:`~fractions.Fraction`
    instance, returns the value as a `(numerator, denominator)` tuple where the
    numerator and denominator are integer values.
    """
    try:
        # int, long, or fraction
        n, d = value.numerator, value.denominator
    except AttributeError:
        try:
            # float
            n, d = value.as_integer_ratio()
        except AttributeError:
            try:
                # tuple
                n, d = value
            except (TypeError, ValueError):
                # anything else...
                n = int(value)
                d = 1
    # Ensure denominator is reasonable
    if d == 0:
        raise PiCameraValueError("Denominator cannot be 0")
    elif d > 65536:
        f = fractions.Fraction(n, d).limit_denominator(65536)
        n, d = f.numerator, f.denominator
    return n, d


class PiCamera(object):
    """
    Provides a pure Python interface to the Raspberry Pi's camera module.

    Upon construction, this class initializes the camera. As there is only a
    single camera supported by the Raspberry Pi, this means that only a single
    instance of this class can exist at any given time (it is effectively a
    singleton class although it is not implemented as such).

    No preview or recording is started automatically upon construction.  Use
    the :meth:`capture` method to capture images, the :meth:`start_recording`
    method to begin recording video, or the :meth:`start_preview` method to
    start live display of the camera's input.

    Several attributes are provided to adjust the camera's configuration. Some
    of these can be adjusted while a recording is running, like
    :attr:`brightness`. Others, like :attr:`resolution`, can only be adjusted
    when the camera is idle.

    When you are finished with the camera, you should ensure you call the
    :meth:`close` method to release the camera resources (failure to do this
    leads to GPU memory leaks)::

        camera = PiCamera()
        try:
            # do something with the camera
            pass
        finally:
            camera.close()

    The class supports the context manager protocol to make this particularly
    easy (upon exiting the ``with`` statement, the :meth:`close` method is
    automatically called)::

        with PiCamera() as camera:
            # do something with the camera
            pass
    """

    CAMERA_PREVIEW_PORT = 0
    CAMERA_VIDEO_PORT = 1
    CAMERA_CAPTURE_PORT = 2
    CAMERA_PORTS = (
        CAMERA_PREVIEW_PORT,
        CAMERA_VIDEO_PORT,
        CAMERA_CAPTURE_PORT,
        )
    MAX_RESOLUTION = (2592, 1944)
    MAX_IMAGE_RESOLUTION = (2592, 1944) # Deprecated - use MAX_RESOLUTION instead
    MAX_VIDEO_RESOLUTION = (1920, 1080) # Deprecated - use MAX_RESOLUTION instead
    DEFAULT_FRAME_RATE_NUM = 30
    DEFAULT_FRAME_RATE_DEN = 1
    VIDEO_OUTPUT_BUFFERS_NUM = 3

    METER_MODES = {
        'average': mmal.MMAL_PARAM_EXPOSUREMETERINGMODE_AVERAGE,
        'spot':    mmal.MMAL_PARAM_EXPOSUREMETERINGMODE_SPOT,
        'backlit': mmal.MMAL_PARAM_EXPOSUREMETERINGMODE_BACKLIT,
        'matrix':  mmal.MMAL_PARAM_EXPOSUREMETERINGMODE_MATRIX,
        }

    EXPOSURE_MODES = {
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

    RAW_FORMATS = {
        # For some bizarre reason, the non-alpha formats are backwards...
        'yuv':  mmal.MMAL_ENCODING_I420,
        'rgb':  mmal.MMAL_ENCODING_BGR24,
        'rgba': mmal.MMAL_ENCODING_RGBA,
        'bgr':  mmal.MMAL_ENCODING_RGB24,
        'bgra': mmal.MMAL_ENCODING_BGRA,
        }

    _METER_MODES_R    = {v: k for (k, v) in METER_MODES.items()}
    _EXPOSURE_MODES_R = {v: k for (k, v) in EXPOSURE_MODES.items()}
    _AWB_MODES_R      = {v: k for (k, v) in AWB_MODES.items()}
    _IMAGE_EFFECTS_R  = {v: k for (k, v) in IMAGE_EFFECTS.items()}
    _RAW_FORMATS_R    = {v: k for (k, v) in RAW_FORMATS.items()}

    def __init__(self):
        global _CAMERA
        if _CAMERA:
            raise PiCameraRuntimeError(
                "Only one PiCamera object can be in existence at a time")
        _CAMERA = self
        bcm_host.bcm_host_init()
        mimetypes.add_type('application/h264',  '.h264',  False)
        mimetypes.add_type('application/mjpeg', '.mjpg',  False)
        mimetypes.add_type('application/mjpeg', '.mjpeg', False)
        self._used_led = False
        self._camera = None
        self._camera_config = None
        self._preview = None
        self._preview_connection = None
        self._null_sink = None
        self._splitter = None
        self._splitter_connection = None
        self._encoders = {}
        self._raw_format = 'yuv'
        self._exif_tags = {
            'IFD0.Model': 'RP_OV5647',
            'IFD0.Make': 'RaspberryPi',
            }
        try:
            self._init_camera()
            self._init_defaults()
            self._init_preview()
            self._init_splitter()
        except:
            self.close()
            raise

    def _init_led(self):
        global GPIO
        if GPIO:
            try:
                GPIO.setmode(GPIO.BCM)
                GPIO.setwarnings(False)
                GPIO.setup(5, GPIO.OUT, initial=GPIO.LOW)
                self._used_led = True
            except RuntimeError:
                # We're probably not running as root. In this case, forget the
                # GPIO reference so we don't try anything further
                GPIO = None

    def _init_camera(self):
        self._camera = ct.POINTER(mmal.MMAL_COMPONENT_T)()
        self._camera_config = mmal.MMAL_PARAMETER_CAMERA_CONFIG_T(
            mmal.MMAL_PARAMETER_HEADER_T(
                mmal.MMAL_PARAMETER_CAMERA_CONFIG,
                ct.sizeof(mmal.MMAL_PARAMETER_CAMERA_CONFIG_T)
                ))
        mmal_check(
            mmal.mmal_component_create(
                mmal.MMAL_COMPONENT_DEFAULT_CAMERA, self._camera),
            prefix="Failed to create camera component")
        if not self._camera[0].output_num:
            raise PiCameraError("Camera doesn't have output ports")

        mmal_check(
            mmal.mmal_port_enable(
                self._camera[0].control,
                _control_callback),
            prefix="Unable to enable control port")

        # Get screen resolution
        w = ct.c_uint32()
        h = ct.c_uint32()
        bcm_host.graphics_get_display_size(0, w, h)
        w = int(w.value)
        h = int(h.value)
        cc = self._camera_config
        cc.max_stills_w = w
        cc.max_stills_h = h
        cc.stills_yuv422 = 0
        cc.one_shot_stills = 1
        cc.max_preview_video_w = w
        cc.max_preview_video_h = h
        cc.num_preview_video_frames = 3
        cc.stills_capture_circular_buffer_height = 0
        cc.fast_preview_resume = 0
        cc.use_stc_timestamp = mmal.MMAL_PARAM_TIMESTAMP_MODE_RESET_STC
        mmal_check(
            mmal.mmal_port_parameter_set(self._camera[0].control, cc.hdr),
            prefix="Camera control port couldn't be configured")

        for p in self.CAMERA_PORTS:
            port = self._camera[0].output[p]
            fmt = port[0].format
            fmt[0].encoding = mmal.MMAL_ENCODING_I420 if p != self.CAMERA_PREVIEW_PORT else mmal.MMAL_ENCODING_OPAQUE
            fmt[0].encoding_variant = mmal.MMAL_ENCODING_I420
            fmt[0].es[0].video.width = mmal.VCOS_ALIGN_UP(w, 32)
            fmt[0].es[0].video.height = mmal.VCOS_ALIGN_UP(h, 16)
            fmt[0].es[0].video.crop.x = 0
            fmt[0].es[0].video.crop.y = 0
            fmt[0].es[0].video.crop.width = w
            fmt[0].es[0].video.crop.height = h
            # 0 implies variable frame-rate
            fmt[0].es[0].video.frame_rate.num = self.DEFAULT_FRAME_RATE_NUM if p != self.CAMERA_CAPTURE_PORT else 0
            fmt[0].es[0].video.frame_rate.den = self.DEFAULT_FRAME_RATE_DEN
            mmal_check(
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

        mmal_check(
            mmal.mmal_component_enable(self._camera),
            prefix="Camera component couldn't be enabled")

    def _init_defaults(self):
        self.sharpness = 0
        self.contrast = 0
        self.brightness = 50
        self.saturation = 0
        self.ISO = 0 # auto
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

    def _init_splitter(self):
        # Create a splitter component for the video port. This is to permit
        # video recordings and captures where use_video_port=True to occur
        # simultaneously (#26)
        self._splitter = ct.POINTER(mmal.MMAL_COMPONENT_T)()
        mmal_check(
            mmal.mmal_component_create(
                mmal.MMAL_COMPONENT_DEFAULT_VIDEO_SPLITTER, self._splitter),
            prefix="Failed to create video splitter")
        if not self._splitter[0].input_num:
            raise PiCameraError("No input ports on splitter component")
        if self._splitter[0].output_num != 4:
            raise PiCameraError(
                "Expected 4 output ports on splitter "
                "(found %d)" % self._splitter[0].output_num)
        self._reconfigure_splitter()
        self._splitter_connection = self._connect_ports(
            self._camera[0].output[self.CAMERA_VIDEO_PORT],
            self._splitter[0].input[0])

    def _init_preview(self):
        # Create and enable the preview component, but don't actually connect
        # it to the camera at this time
        self._preview = ct.POINTER(mmal.MMAL_COMPONENT_T)()
        mmal_check(
            mmal.mmal_component_create(
                mmal.MMAL_COMPONENT_DEFAULT_VIDEO_RENDERER, self._preview),
            prefix="Failed to create preview component")
        if not self._preview[0].input_num:
            raise PiCameraError("No input ports on preview component")

        mp = mmal.MMAL_DISPLAYREGION_T(
            mmal.MMAL_PARAMETER_HEADER_T(
                mmal.MMAL_PARAMETER_DISPLAYREGION,
                ct.sizeof(mmal.MMAL_DISPLAYREGION_T)
            ))
        mp.set = (
            mmal.MMAL_DISPLAY_SET_LAYER |
            mmal.MMAL_DISPLAY_SET_ALPHA |
            mmal.MMAL_DISPLAY_SET_FULLSCREEN)
        mp.layer = 2
        mp.alpha = 255
        mp.fullscreen = 1
        mmal_check(
            mmal.mmal_port_parameter_set(self._preview[0].input[0], mp.hdr),
            prefix="Unable to set preview port parameters")

        mmal_check(
            mmal.mmal_component_enable(self._preview),
            prefix="Preview component couldn't be enabled")

        # Create a null-sink component, enable it and connect it to the
        # camera's preview port. If nothing is connected to the preview port,
        # the camera doesn't measure exposure and captured images gradually
        # fade to black (issue #22)
        self._null_sink = ct.POINTER(mmal.MMAL_COMPONENT_T)()
        mmal_check(
            mmal.mmal_component_create(
                mmal.MMAL_COMPONENT_DEFAULT_NULL_SINK, self._null_sink),
            prefix="Failed to create null sink component")
        if not self._null_sink[0].input_num:
            raise PiCameraError("No input ports on null sink component")
        mmal_check(
            mmal.mmal_component_enable(self._null_sink),
            prefix="Null sink component couldn't be enabled")

        self._preview_connection = self._connect_ports(
            self._camera[0].output[self.CAMERA_PREVIEW_PORT],
            self._null_sink[0].input[0])

    def _connect_ports(self, output_port, input_port):
        """
        Connect the specified output and input ports
        """
        result = ct.POINTER(mmal.MMAL_CONNECTION_T)()
        mmal_check(
            mmal.mmal_connection_create(
                result, output_port, input_port,
                mmal.MMAL_CONNECTION_FLAG_TUNNELLING |
                mmal.MMAL_CONNECTION_FLAG_ALLOCATION_ON_INPUT),
            prefix="Failed to create connection")
        mmal_check(
            mmal.mmal_connection_enable(result),
            prefix="Failed to enable connection")
        return result

    def _get_ports(self, from_video_port, splitter_port):
        """
        Determine the camera and output ports for given capture options
        """
        camera_port = (
            self._camera[0].output[self.CAMERA_VIDEO_PORT]
            if from_video_port else
            self._camera[0].output[self.CAMERA_CAPTURE_PORT]
            )
        output_port = (
            self._splitter[0].output[splitter_port]
            if from_video_port else
            camera_port
            )
        return (camera_port, output_port)

    def _reconfigure_splitter(self):
        """
        Copy the camera's video port config to the video splitter
        """
        mmal.mmal_format_copy(
            self._splitter[0].input[0][0].format,
            self._camera[0].output[self.CAMERA_VIDEO_PORT][0].format)
        self._splitter[0].input[0][0].buffer_num = max(
            self._splitter[0].input[0][0].buffer_num,
            self.VIDEO_OUTPUT_BUFFERS_NUM)
        mmal_check(
            mmal.mmal_port_format_commit(self._splitter[0].input[0]),
            prefix="Couldn't set splitter input port format")
        for p in range(4):
            mmal.mmal_format_copy(
                self._splitter[0].output[p][0].format,
                self._splitter[0].input[0][0].format)
            mmal_check(
                mmal.mmal_port_format_commit(self._splitter[0].output[p]),
                prefix="Couldn't set splitter output port %d format" % p)

    def _disable_camera(self):
        """
        Temporarily disable the camera and all permanently attached components
        """
        mmal_check(
            mmal.mmal_connection_disable(self._splitter_connection),
            prefix="Failed to disable splitter connection")
        mmal_check(
            mmal.mmal_connection_disable(self._preview_connection),
            prefix="Failed to disable preview connection")
        mmal_check(
            mmal.mmal_component_disable(self._camera),
            prefix="Failed to disable camera")

    def _enable_camera(self):
        """
        Re-enable the camera and all permanently attached components
        """
        self._reconfigure_splitter()
        mmal_check(
            mmal.mmal_component_enable(self._camera),
            prefix="Failed to enable camera")
        mmal_check(
            mmal.mmal_connection_enable(self._preview_connection),
            prefix="Failed to enable preview connection")
        mmal_check(
            mmal.mmal_connection_enable(self._splitter_connection),
            prefix="Failed to enable splitter connection")

    def _check_camera_open(self):
        """
        Raise an exception if the camera is already closed
        """
        if self.closed:
            raise PiCameraRuntimeError("Camera is closed")

    def _check_recording_stopped(self):
        """
        Raise an exception if the camera is currently recording
        """
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
        (type, encoding) = mimetypes.guess_type(filename, strict=False)
        if type:
            return type
        raise PiCameraValueError(
            'Unable to determine type from filename %s' % filename)

    def _get_image_format(self, output, format):
        format = self._get_format(output, format)
        format = (
            format[6:] if format.startswith('image/') else
            format)
        if format == 'x-ms-bmp':
            format = 'bmp'
        if format == 'raw':
            format = self.raw_format
        return format

    def _get_video_format(self, output, format):
        format = self._get_format(output, format)
        format = (
            format[6:]  if format.startswith('video/') else
            format[12:] if format.startswith('application/') else
            format)
        return format

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
        global _CAMERA
        for port in self._encoders:
            self.stop_recording(splitter_port=port)
        assert not self.recording
        if self._splitter_connection:
            mmal.mmal_connection_destroy(self._splitter_connection)
            self._splitter_connection = None
        if self._preview_connection:
            mmal.mmal_connection_destroy(self._preview_connection)
            self._preview_connection = None
        if self._null_sink:
            mmal.mmal_component_destroy(self._null_sink)
            self._null_sink = None
        if self._splitter:
            mmal.mmal_component_destroy(self._splitter)
            self._splitter = None
        if self._preview:
            mmal.mmal_component_destroy(self._preview)
            self._preview = None
        if self._camera:
            mmal.mmal_component_destroy(self._camera)
            self._camera = None
        _CAMERA = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.close()

    def start_preview(self):
        """
        Displays the preview window.

        This method starts a new preview running at the configured resolution
        (see :attr:`resolution`). Most camera properties can be modified "live"
        while the preview is running (e.g. :attr:`brightness`). The preview
        overrides whatever is currently visible on the display. More
        specifically, the preview does not rely on a graphical environment like
        X-Windows (it can run quite happily from a TTY console); it is simply
        an overlay on the Pi's video output.

        To stop the preview and reveal the display again, call
        :meth:`stop_preview`. The preview can be started and stopped multiple
        times during the lifetime of the :class:`PiCamera` object.

        .. note::
            Because the preview typically obscures the screen, ensure you have
            a means of stopping a preview before starting one. If the preview
            obscures your interactive console you won't be able to Alt+Tab back
            to it as the preview isn't in a window. If you are in an
            interactive Python session, simply pressing Ctrl+D usually suffices
            to terminate the environment, including the camera and its
            associated preview.
        """
        self._check_camera_open()
        # Switch the camera's preview port from the null sink to the
        # preview component
        if self._preview_connection:
            mmal.mmal_connection_destroy(self._preview_connection)
            self._null_connection = None
        self._preview_connection = self._connect_ports(
            self._camera[0].output[self.CAMERA_PREVIEW_PORT],
            self._preview[0].input[0])

    def stop_preview(self):
        """
        Closes the preview window display.

        If :meth:`start_preview` has previously been called, this method shuts
        down the preview display which generally results in the underlying TTY
        becoming visible again. If a preview is not currently running, no
        exception is raised - the method will simply do nothing.
        """
        self._check_camera_open()
        # This is the reverse of start_preview; disconnect the camera from the
        # preview component (if it's connected) and connect it to the null sink
        if self._preview_connection:
            mmal.mmal_connection_destroy(self._preview_connection)
            self._preview_connection = None
        self._preview_connection = self._connect_ports(
            self._camera[0].output[self.CAMERA_PREVIEW_PORT],
            self._null_sink[0].input[0])

    def start_recording(
            self, output, format=None, resize=None, splitter_port=1, **options):
        """
        Start recording video from the camera, storing it in *output*.

        If *output* is a string, it will be treated as a filename for a new
        file which the video will be written to. Otherwise, *output* is assumed
        to be a file-like object and the video data is appended to it (the
        implementation only assumes the object has a ``write()`` method - no
        other methods will be called).

        If *format* is ``None`` (the default), the method will attempt to guess
        the required video format from the extension of *output* (if it's a
        string), or from the *name* attribute of *output* (if it has one). In
        the case that the format cannot be determined, a
        :exc:`PiCameraValueError` will be raised.

        If *format* is not ``None``, it must be a string specifying the format
        that you want the image written to. The format can be a MIME-type or
        one of the following strings:

        * ``'h264'`` - Write an H.264 video stream
        * ``'mjpeg'`` - Write an M-JPEG video stream

        If *resize* is not ``None`` (the default), it must be a two-element
        tuple specifying the width and height that the video recording should
        be resized to. This is particularly useful for recording video using
        the full area of the camera sensor (which is not possible without
        down-sizing the output).

        The *splitter_port* parameter specifies the port of the built-in
        splitter that the video encoder will be attached to. This defaults to
        ``1`` and most users will have no need to specify anything different.
        If you wish to record multiple (presumably resized) streams
        simultaneously, specify a value between ``0`` and ``3`` inclusive for
        this parameter, ensuring that you do not specify a port that is
        currently in use.

        Certain formats accept additional options which can be specified
        as keyword arguments. The ``'h264'`` format accepts the following
        additional options:

        * *profile* - The H.264 profile to use for encoding. Defaults to
          'high', but can be one of 'baseline', 'main', 'high', or
          'constrained'.

        * *intra_period* - The key frame rate (the rate at which I-frames are
          inserted in the output). Defaults to 0, but can be any positive
          32-bit integer value representing the number of frames between
          successive I-frames.

        * *inline_headers* - When ``True``, specifies that the encoder should
          output SPS/PPS headers within the stream to ensure GOPs (groups of
          pictures) are self describing. This is important for streaming
          applications where the client may wish to seek within the stream, and
          enables the use of :meth:`split_recording`. Defaults to ``True`` if
          not specified.

        * *sei* - When ``True``, specifies the encoder should include
          "Supplemental Enhancement Information" within the output stream.
          Defaults to ``False`` if not specified.

        All formats accept the following additional options:

        * *bitrate* - The bitrate at which video will be encoded. Defaults to
          17000000 (17Mbps) if not specified. A value of 0 implies VBR
          (variable bitrate) encoding. The maximum value is 25000000 (25Mbps).

        * *quantization* - When *bitrate* is zero (for variable bitrate
          encodings), this parameter specifies the quality that the encoder
          should attempt to maintain.

          For the ``'h264'`` format, use values between 10 and 40 where 10 is
          extremely high quality, and 40 is extremely low (20-25 is usually a
          reasonable range for H.264 encoding). Note that
          :meth:`split_recording` cannot be used in VBR mode.

        .. versionchanged:: 1.0
            The *resize* parameter was added, and ``'mjpeg'`` was added as a
            recording format

        .. versionchanged:: 1.3
            The *splitter_port* parameter was added
        """
        if splitter_port in self._encoders:
            raise PiCameraRuntimeError(
                    'The camera is already recording on '
                    'port %d' % splitter_port)
        camera_port, output_port = self._get_ports(True, splitter_port)
        format = self._get_video_format(output, format)
        self._still_encoding = mmal.MMAL_ENCODING_I420
        encoder = PiVideoEncoder(
                self, camera_port, output_port, format, resize, **options)
        self._encoders[splitter_port] = encoder
        try:
            encoder.start(output)
        except Exception as e:
            encoder.close()
            del self._encoders[splitter_port]
            raise

    def split_recording(self, output, splitter_port=1):
        """
        Continue the recording in the specified output; close existing output.

        When called, the video encoder will wait for the next appropriate
        split point (an inline SPS header), then will cease writing to the
        current output (and close it, if it was specified as a filename), and
        continue writing to the newly specified *output*.

        If *output* is a string, it will be treated as a filename for a new
        file which the video will be written to. Otherwise, *output* is assumed
        to be a file-like object and the video data is appended to it (the
        implementation only assumes the object has a ``write()`` method - no
        other methods will be called).

        The *splitter_port* parameter specifies which port of the video
        splitter the encoder you wish to change outputs is attached to. This
        defaults to ``1`` and most users will have no need to specify anything
        different. Valid values are between ``0`` and ``3`` inclusive.

        Note that unlike :meth:`start_recording`, you cannot specify format or
        options as these cannot be changed in the middle of recording. Only the
        new *output* can be specified. Furthermore, the format of the recording
        is currently limited to H264, *inline_headers* must be ``True``, and
        *bitrate* must be non-zero (CBR mode) when :meth:`start_recording` is
        called (this is the default).

        .. versionchanged:: 1.3
            The *splitter_port* parameter was added
        """
        try:
            self._encoders[splitter_port].split(output)
        except KeyError:
            raise PiCameraRuntimeError(
                    'There is no recording in progress on '
                    'port %d' % splitter_port)

    def wait_recording(self, timeout=0, splitter_port=1):
        """
        Wait on the video encoder for timeout seconds.

        It is recommended that this method is called while recording to check
        for exceptions. If an error occurs during recording (for example out of
        disk space), an exception will only be raised when the
        :meth:`wait_recording` or :meth:`stop_recording` methods are called.

        If ``timeout`` is 0 (the default) the function will immediately return
        (or raise an exception if an error has occurred).

        The *splitter_port* parameter specifies which port of the video
        splitter the encoder you wish to wait on is attached to. This
        defaults to ``1`` and most users will have no need to specify anything
        different. Valid values are between ``0`` and ``3`` inclusive.

        .. versionchanged:: 1.3
            The *splitter_port* parameter was added
        """
        assert timeout is not None
        try:
            self._encoders[splitter_port].wait(timeout)
        except KeyError:
            raise PiCameraRuntimeError(
                    'There is no recording in progress on '
                    'port %d' % splitter_port)

    def stop_recording(self, splitter_port=1):
        """
        Stop recording video from the camera.

        After calling this method the video encoder will be shut down and
        output will stop being written to the file-like object specified with
        :meth:`start_recording`. If an error occurred during recording and
        :meth:`wait_recording` has not been called since the error then this
        method will raise the exception.

        The *splitter_port* parameter specifies which port of the video
        splitter the encoder you wish to stop is attached to. This defaults to
        ``1`` and most users will have no need to specify anything different.
        Valid values are between ``0`` and ``3`` inclusive.

        .. versionchanged:: 1.3
            The *splitter_port* parameter was added
        """
        try:
            self.wait_recording(0, splitter_port)
        finally:
            encoder = self._encoders[splitter_port]
            del self._encoders[splitter_port]
            encoder.close()

    def record_sequence(
            self, outputs, format='h264', resize=None, splitter_port=1, **options):
        """
        Record a sequence of video clips from the camera.

        This method accepts a sequence or iterator of *outputs* each of which
        must either be a string specifying a filename for output, or a
        file-like object with a ``write`` method.

        The method acts as an iterator itself, yielding each item of the
        sequence in turn. In this way, the caller can control how long to
        record to each item by only permitting the loop to continue when ready
        to switch to the next output.

        The *format*, *splitter_port*, *resize*, and *options* parameters are
        the same as in :meth:`start_recording`, but *format* defaults to
        ``'h264'``.  The format is **not** derived from the filenames in
        *outputs* by this method.

        For example, to record 3 consecutive 10-second video clips, writing the
        output to a series of H.264 files named clip01.h264, clip02.h264, and
        clip03.h264 one could use the following::

            import picamera
            with picamera.PiCamera() as camera:
                for filename in camera.record_sequence([
                        'clip01.h264',
                        'clip02.h264',
                        'clip03.h264']):
                    print('Recording to %s' % filename)
                    camera.wait_recording(10)

        Alternatively, a more flexible method of writing the previous example
        (which is easier to expand to a large number of output files) is by
        using a generator expression as the input sequence::

            import picamera
            with picamera.PiCamera() as camera:
                for filename in camera.record_sequence(
                        'clip%02d.h264' % i for i in range(3)):
                    print('Recording to %s' % filename)
                    camera.wait_recording(10)

        More advanced techniques are also possible by utilising infinite
        sequences, such as those generated by :func:`itertools.cycle`. In the
        following example, recording is switched between two in-memory streams.
        Whilst one stream is recording, the other is being analysed. The script
        only stops recording when a video recording meets some criteria defined
        by the ``process`` function::

            import io
            import itertools
            import picamera
            with picamera.PiCamera() as camera:
                analyse = None
                for stream in camera.record_sequence(
                        itertools.cycle((io.BytesIO(), io.BytesIO()))):
                    if analyse is not None:
                        if process(analyse):
                            break
                        analyse.seek(0)
                        analyse.truncate()
                    camera.wait_recording(5)
                    analyse = stream

        .. versionadded:: 1.3
        """
        if splitter_port in self._encoders:
            raise PiCameraRuntimeError(
                    'The camera is already recording on '
                    'port %d' % splitter_port)
        camera_port, output_port = self._get_ports(True, splitter_port)
        format = self._get_video_format('', format)
        self._still_encoding = mmal.MMAL_ENCODING_I420
        encoder = PiVideoEncoder(
                self, camera_port, output_port, format, resize, **options)
        self._encoders[splitter_port] = encoder
        try:
            start = True
            for output in outputs:
                if start:
                    start = False
                    encoder.start(output)
                else:
                    encoder.split(output)
                yield output
        finally:
            try:
                encoder.wait(0)
            finally:
                del self._encoders[splitter_port]
                encoder.close()

    def capture(
            self, output, format=None, use_video_port=False, resize=None,
            splitter_port=0, **options):
        """
        Capture an image from the camera, storing it in *output*.

        If *output* is a string, it will be treated as a filename for a new
        file which the image will be written to. Otherwise, *output* is assumed
        to a be a file-like object and the image data is appended to it (the
        implementation only assumes the object has a ``write()`` method - no
        other methods will be called).

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

        * ``'bmp'`` - Write a Windows bitmap file

        * ``'yuv'`` - Write the raw image data to a file in YUV420 format

        * ``'rgb'`` - Write the raw image data to a file in 24-bit RGB format

        * ``'rgba'`` - Write the raw image data to a file in 32-bit RGBA format

        * ``'bgr'`` - Write the raw image data to a file in 24-bit BGR format

        * ``'bgra'`` - Write the raw image data to a file in 32-bit BGRA format

        * ``'raw'`` - Deprecated option for raw captures; the format is taken
          from the deprecated :attr:`raw_format` attribute

        The *use_video_port* parameter controls whether the camera's image or
        video port is used to capture images. It defaults to ``False`` which
        means that the camera's image port is used. This port is slow but
        produces better quality pictures. If you need rapid capture up to the
        rate of video frames, set this to ``True``.

        When *use_video_port* is ``True``, the *splitter_port* parameter
        specifies the port of the video splitter that the image encoder will be
        attached to. This defaults to ``0`` and most users will have no need to
        specify anything different. This parameter is ignored when
        *use_video_port* is ``False``. See :ref:`under_the_hood` for more
        information about the video splitter.

        If *resize* is not ``None`` (the default), it must be a two-element
        tuple specifying the width and height that the image should be resized
        to.

        .. warning::

            If *resize* is specified, or *use_video_port* is ``True``, Exif
            metadata will **not** be included in JPEG output. This is due to an
            underlying firmware limitation.

        Certain file formats accept additional options which can be specified
        as keyword arguments. Currently, only the ``'jpeg'`` encoder accepts
        additional options, which are:

        * *quality* - Defines the quality of the JPEG encoder as an integer
          ranging from 1 to 100. Defaults to 85.

        * *thumbnail* - Defines the size and quality of the thumbnail to embed
          in the Exif metadata. Specifying ``None`` disables thumbnail
          generation.  Otherwise, specify a tuple of ``(width, height,
          quality)``. Defaults to ``(64, 48, 35)``.

        * *bayer* - If ``True``, the raw bayer data from the camera's sensor
          is included in the Exif metadata.

        .. note::

            The so-called "raw" formats listed above (``'yuv'``, ``'rgb'``,
            etc.) do not represent the raw bayer data from the camera's sensor.
            Rather they provide access to the image data after GPU processing,
            but before format encoding (JPEG, PNG, etc). Currently, the only
            method of accessing the raw bayer data is via the *bayer* parameter
            described above.

        .. versionchanged:: 1.0
            The *resize* parameter was added, and raw capture formats can now
            be specified directly

        .. versionchanged:: 1.3
            The *splitter_port* parameter was added, and *bayer* was added as
            an option for the ``'jpeg'`` format

        """
        if use_video_port and (splitter_port in self._encoders):
            raise PiCameraRuntimeError(
                    'The camera is already recording on '
                    'port %d' % splitter_port)
        camera_port, output_port = self._get_ports(use_video_port, splitter_port)
        format = self._get_image_format(output, format)
        if not use_video_port:
            if resize:
                self._still_encoding = mmal.MMAL_ENCODING_I420
            else:
                self._still_encoding = self.RAW_FORMATS.get(
                    format, mmal.MMAL_ENCODING_OPAQUE)
        encoder_class = (
                PiRawOneImageEncoder if format in self.RAW_FORMATS else
                PiCookedOneImageEncoder)
        encoder = encoder_class(
                self, camera_port, output_port, format, resize, **options)
        try:
            encoder.start(output)
            # Wait for the callback to set the event indicating the end of
            # image capture
            if not encoder.wait(30):
                raise PiCameraRuntimeError(
                    'Timed out waiting for capture to end')
        finally:
            encoder.close()
            encoder = None

    def capture_sequence(
            self, outputs, format='jpeg', use_video_port=False, resize=None,
            splitter_port=0, **options):
        """
        Capture a sequence of consecutive images from the camera.

        This method accepts a sequence or iterator of *outputs* each of which
        must either be a string specifying a filename for output, or a
        file-like object with a ``write`` method. For each item in the sequence
        or iterator of outputs, the camera captures a single image as fast as
        it can.

        The *format*, *use_video_port*, *splitter_port*, *resize*, and
        *options* parameters are the same as in :meth:`capture`, but *format*
        defaults to ``'jpeg'``.  The format is **not** derived from the
        filenames in *outputs* by this method.

        For example, to capture 3 consecutive images::

            import time
            import picamera
            with picamera.PiCamera() as camera:
                camera.start_preview()
                time.sleep(2)
                camera.capture_sequence([
                    'image1.jpg',
                    'image2.jpg',
                    'image3.jpg',
                    ])
                camera.stop_preview()

        If you wish to capture a large number of images, a list comprehension
        or generator expression can be used to construct the list of filenames
        to use::

            import time
            import picamera
            with picamera.PiCamera() as camera:
                camera.start_preview()
                time.sleep(2)
                camera.capture_sequence([
                    'image%02d.jpg' % i
                    for i in range(100)
                    ])
                camera.stop_preview()

        More complex effects can be obtained by using a generator function to
        provide the filenames or output objects.

        .. versionchanged:: 1.0
            The *resize* parameter was added, and raw capture formats can now
            be specified directly

        .. versionchanged:: 1.3
            The *splitter_port* parameter was added
        """
        if use_video_port and (splitter_port in self._encoders):
            raise PiCameraRuntimeError(
                    'The camera is already recording on '
                    'port %d' % splitter_port)
        camera_port, output_port = self._get_ports(use_video_port, splitter_port)
        format = self._get_image_format('', format)
        if format == 'jpeg' and not use_video_port and not resize:
            self._still_encoding = mmal.MMAL_ENCODING_OPAQUE
        else:
            self._still_encoding = mmal.MMAL_ENCODING_I420
        if use_video_port:
            encoder_class = (
                    PiRawMultiImageEncoder if format in self.RAW_FORMATS else
                    PiCookedMultiImageEncoder)
            encoder = encoder_class(
                    self, camera_port, output_port, format, resize, **options)
            try:
                encoder.start(outputs)
                encoder.wait()
            finally:
                encoder.close()
        else:
            encoder_class = (
                    PiRawOneImageEncoder if format in self.RAW_FORMATS else
                    PiCookedOneImageEncoder)
            encoder = encoder_class(
                    self, camera_port, output_port, format, resize, **options)
            try:
                for output in outputs:
                    encoder.start(output)
                    if not encoder.wait(30):
                        raise PiCameraRuntimeError(
                            'Timed out waiting for capture to end')
            finally:
                encoder.close()

    def capture_continuous(
            self, output, format=None, use_video_port=False, resize=None,
            splitter_port=0, **options):
        """
        Capture images continuously from the camera as an infinite iterator.

        This method returns an infinite iterator of images captured
        continuously from the camera. If *output* is a string, each captured
        image is stored in a file named after *output* after substitution of
        two values with the :meth:`~str.format` method. Those two values are:

        * ``{counter}`` - a simple incrementor that starts at 1 and increases
          by 1 for each image taken

        * ``{timestamp}`` - a :class:`~datetime.datetime` instance

        The table below contains several example values of *output* and the
        sequence of filenames those values could produce:

        +--------------------------------------------+--------------------------------------------+-------+
        | *output* Value                             | Filenames                                  | Notes |
        +============================================+============================================+=======+
        | ``'image{counter}.jpg'``                   | image1.jpg, image2.jpg, image3.jpg, ...    |       |
        +--------------------------------------------+--------------------------------------------+-------+
        | ``'image{counter:02d}.jpg'``               | image01.jpg, image02.jpg, image03.jpg, ... |       |
        +--------------------------------------------+--------------------------------------------+-------+
        | ``'image{timestamp}.jpg'``                 | image2013-10-05 12:07:12.346743.jpg,       | (1)   |
        |                                            | image2013-10-05 12:07:32.498539, ...       |       |
        +--------------------------------------------+--------------------------------------------+-------+
        | ``'image{timestamp:%H-%M-%S-%f}.jpg'``     | image12-10-02-561527.jpg,                  |       |
        |                                            | image12-10-14-905398.jpg                   |       |
        +--------------------------------------------+--------------------------------------------+-------+
        | ``'{timestamp:%H%M%S}-{counter:03d}.jpg'`` | 121002-001.jpg, 121013-002.jpg,            | (2)   |
        |                                            | 121014-003.jpg, ...                        |       |
        +--------------------------------------------+--------------------------------------------+-------+

        1. Note that because timestamp's default output includes colons (:),
           the resulting filenames are not suitable for use on Windows. For
           this reason (and the fact the default contains spaces) it is
           strongly recommended you always specify a format when using
           ``{timestamp}``.

        2. You can use both ``{timestamp}`` and ``{counter}`` in a single
           format string (multiple times too!) although this tends to be
           redundant.

        If *output* is not a string, it is assumed to be a file-like object
        and each image is simply written to this object sequentially. In this
        case you will likely either want to write something to the object
        between the images to distinguish them, or clear the object between
        iterations.

        The *format*, *use_video_port*, *splitter_port*, *resize*, and
        *options* parameters are the same as in :meth:`capture`.

        For example, to capture 60 images with a one second delay between them,
        writing the output to a series of JPEG files named image01.jpg,
        image02.jpg, etc. one could do the following::

            import time
            import picamera
            with picamera.PiCamera() as camera:
                camera.start_preview()
                try:
                    for i, filename in enumerate(camera.capture_continuous('image{counter:02d}.jpg')):
                        print(filename)
                        time.sleep(1)
                        if i == 59:
                            break
                finally:
                    camera.stop_preview()

        Alternatively, to capture JPEG frames as fast as possible into an
        in-memory stream, performing some processing on each stream until
        some condition is satisfied::

            import io
            import time
            import picamera
            with picamera.PiCamera() as camera:
                stream = io.BytesIO()
                for foo in camera.capture_continuous(stream, format='jpeg'):
                    # Truncate the stream to the current position (in case
                    # prior iterations output a longer image)
                    stream.truncate()
                    stream.seek(0)
                    if process(stream):
                        break

        .. versionchanged:: 1.0
            The *resize* parameter was added, and raw capture formats can now
            be specified directly

        .. versionchanged:: 1.3
            The *splitter_port* parameter was added
        """
        if use_video_port and (splitter_port in self._encoders):
            raise PiCameraRuntimeError(
                    'The camera is already recording on '
                    'port %d' % splitter_port)
        camera_port, output_port = self._get_ports(use_video_port, splitter_port)
        format = self._get_image_format(output, format)
        if format == 'jpeg' and not use_video_port and not resize:
            self._still_encoding = mmal.MMAL_ENCODING_OPAQUE
        else:
            self._still_encoding = mmal.MMAL_ENCODING_I420
        encoder_class = (
                PiRawOneImageEncoder if format in self.RAW_FORMATS else
                PiCookedOneImageEncoder)
        encoder = encoder_class(
                self, camera_port, output_port, format, resize, **options)
        try:
            if isinstance(output, bytes):
                # If we're fed a bytes string, assume it's UTF-8 encoded and
                # convert it to Unicode. Technically this is wrong
                # (file-systems use all sorts of encodings), but UTF-8 is a
                # reasonable default and this keeps compatibility with Python 2
                # simple although it breaks the edge cases of non-UTF-8 encoded
                # bytes strings with non-UTF-8 encoded file-systems
                output = output.decode('utf-8')
            if isinstance(output, str):
                counter = 1
                while True:
                    filename = output.format(
                        counter=counter,
                        timestamp=datetime.datetime.now(),
                        )
                    encoder.start(filename)
                    if not encoder.wait(30):
                        raise PiCameraRuntimeError(
                            'Timed out waiting for capture to end')
                    yield filename
                    counter += 1
            else:
                while True:
                    encoder.start(output)
                    if not encoder.wait(30):
                        raise PiCameraRuntimeError(
                            'Timed out waiting for capture to end')
                    yield output
        finally:
            encoder.close()

    @property
    def closed(self):
        """
        Returns ``True`` if the :meth:`close` method has been called.
        """
        return not self._camera

    @property
    def recording(self):
        """
        Returns ``True`` if the :meth:`start_recording` method has been called,
        and no :meth:`stop_recording` call has been made yet.
        """
        # XXX Should probably check this is actually enabled...
        return bool(self._encoders)

    @property
    def previewing(self):
        """
        Returns ``True`` if the :meth:`start_preview` method has been called,
        and no :meth:`stop_preview` call has been made yet.
        """
        return (
                bool(self._preview_connection)
                and self._preview_connection[0].is_enabled
                and self._preview_connection[0].in_[0].name.startswith(
                    mmal.MMAL_COMPONENT_DEFAULT_VIDEO_RENDERER)
                )

    @property
    def exif_tags(self):
        """
        Holds a mapping of the Exif tags to apply to captured images.

        .. note::

            Please note that Exif tagging is only supported with the ``jpeg``
            format.

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

        You may also specify datetime values, integer, or float values, all of
        which will be converted to appropriate ASCII strings (datetime values
        are formatted as ``YYYY:MM:DD HH:MM:SS`` in accordance with the Exif
        standard).

        The currently supported Exif tags are:

        +-------+-------------------------------------------------------------+
        | Group | Tags                                                        |
        +=======+=============================================================+
        | IFD0, | ImageWidth, ImageLength, BitsPerSample, Compression,        |
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
        |       | RelatedImageLength                                          |
        +-------+-------------------------------------------------------------+
        """
        return self._exif_tags

    def _set_led(self, value):
        if not self._used_led:
            self._init_led()
        if not GPIO:
            raise PiCameraRuntimeError(
                "GPIO library not found, or not accessible; please install "
                "RPi.GPIO and run the script as root")
        GPIO.output(5, bool(value))
    led = property(None, _set_led, doc="""
        Sets the state of the camera's LED via GPIO.

        If a GPIO library is available (only RPi.GPIO is currently supported),
        and if the python process has the necessary privileges (typically this
        means running as root via sudo), this property can be used to set the
        state of the camera's LED as a boolean value (``True`` is on, ``False``
        is off).

        .. note::

            This is a write-only property. While it can be used to control the
            camera's LED, you cannot query the state of the camera's LED using
            this property.
        """)

    def _get_raw_format(self):
        return self._raw_format
    def _set_raw_format(self, value):
        warnings.warn(
            'PiCamera.raw_format is deprecated; use required format directly '
            'with capture methods instead', DeprecationWarning)
        try:
            self.RAW_FORMATS[value]
        except KeyError:
            raise PiCameraValueError("Invalid raw format: %s" % value)
        self._raw_format = value
    raw_format = property(_get_raw_format, _set_raw_format, doc="""
        Retrieves or sets the raw format of the camera's ports.

        .. deprecated:: 1.0
            Please use ``'yuv'`` or ``'rgb'`` directly as a format in the
            various capture methods instead.
        """)

    def _get_frame(self):
        # XXX This is rather messy; see if we can't come up with a better
        # design in 2.0
        if not self._encoders:
            raise PiCameraRuntimeError(
                "Cannot query frame information when camera is not recording")
        elif len(self._encoders) == 1:
            return next(iter(self._encoders.values())).frame
        else:
            return {
                    port: encoder.frame
                    for (port, encoder) in self._encoders.items()
                    }
    frame = property(_get_frame, doc="""
        Retrieves information about the current frame recorded from the camera.

        When video recording is active (after a call to
        :meth:`start_recording`), this attribute will return a
        :class:`PiVideoFrame` tuple containing information about the current
        frame that the camera is recording.

        If multiple video recordings are currently in progress (after multiple
        calls to :meth:`start_recording` with different values for the
        ``splitter_port`` parameter), this attribute will return a
        :class:`dict` mapping active port numbers to a :class:`PiVideoFrame`
        tuples.

        Querying this property when the camera is not recording will result in
        an exception.

        .. note::

            There is a small window of time when querying this attribute will
            return ``None`` after calling :meth:`start_recording`. If this
            attribute returns ``None``, this means that the video encoder has
            been initialized, but the camera has not yet returned any frames.
        """)

    def _get_framerate(self):
        self._check_camera_open()
        fmt = self._camera[0].output[self.CAMERA_VIDEO_PORT][0].format[0].es[0]
        return PiCameraFraction(fmt.video.frame_rate.num, fmt.video.frame_rate.den)
    def _set_framerate(self, value):
        self._check_camera_open()
        self._check_recording_stopped()
        n, d = to_rational(value)
        if not (0 <= n / d <= 90):
            raise PiCameraValueError("Invalid framerate: %.2ffps" % (n / d))
        self._disable_camera()
        for port in (self.CAMERA_VIDEO_PORT, self.CAMERA_PREVIEW_PORT):
            fmt = self._camera[0].output[port][0].format[0].es[0]
            fmt.video.frame_rate.num = n
            fmt.video.frame_rate.den = d
            mmal_check(
                mmal.mmal_port_format_commit(self._camera[0].output[port]),
                prefix="Camera video format couldn't be set")
        self._enable_camera()
    framerate = property(_get_framerate, _set_framerate, doc="""
        Retrieves or sets the framerate at which video-port based image
        captures, video recordings, and previews will run.

        When queried, the :attr:`framerate` property returns the rate at which
        the camera's video and preview ports will operate as a
        :class:`~fractions.Fraction` instance which can be easily converted to
        an :class:`int` or :class:`float`.

        .. note::

            For backwards compatibility, a derivative of the
            :class:`~fractions.Fraction` class is actually used which permits
            the value to be treated as a tuple of ``(numerator, denominator)``.

        When set, the property reconfigures the camera so that the next call to
        recording and previewing methods will use the new framerate.  The
        framerate can be specified as an :class:`int`, :class:`float`,
        :class:`~fractions.Fraction`, or a ``(numerator, denominator)`` tuple.
        The camera must not be closed, and no recording must be active when the
        property is set.

        .. note::

            This attribute, in combination with :attr:`resolution`, determines
            the mode that the camera operates in. The actual sensor framerate
            and resolution used by the camera is influenced, but not directly
            set, by this property. See :ref:`camera_modes` for more
            information.
        """)

    def _get_resolution(self):
        self._check_camera_open()
        return (
            int(self._camera_config.max_stills_w),
            int(self._camera_config.max_stills_h)
            )
    def _set_resolution(self, value):
        self._check_camera_open()
        self._check_recording_stopped()
        n, d = self.framerate
        try:
            w, h = value
        except (TypeError, ValueError) as e:
            raise PiCameraValueError(
                "Invalid resolution (width, height) tuple: %s" % value)
        self._disable_camera()
        self._camera_config.max_stills_w = w
        self._camera_config.max_stills_h = h
        self._camera_config.max_preview_video_w = w
        self._camera_config.max_preview_video_h = h
        mmal_check(
            mmal.mmal_port_parameter_set(self._camera[0].control, self._camera_config.hdr),
            prefix="Failed to set preview resolution")
        for port in (self.CAMERA_CAPTURE_PORT, self.CAMERA_VIDEO_PORT, self.CAMERA_PREVIEW_PORT):
            fmt = self._camera[0].output[port][0].format[0].es[0]
            fmt.video.width = mmal.VCOS_ALIGN_UP(w, 32)
            fmt.video.height = mmal.VCOS_ALIGN_UP(h, 16)
            fmt.video.crop.x = 0
            fmt.video.crop.y = 0
            fmt.video.crop.width = w
            fmt.video.crop.height = h
            if port != self.CAMERA_CAPTURE_PORT:
                fmt.video.frame_rate.num = n
                fmt.video.frame_rate.den = d
            mmal_check(
                mmal.mmal_port_format_commit(self._camera[0].output[port]),
                prefix="Camera video format couldn't be set")
        self._enable_camera()
    resolution = property(_get_resolution, _set_resolution, doc="""
        Retrieves or sets the resolution at which image captures, video
        recordings, and previews will be captured.

        When queried, the :attr:`resolution` property returns the resolution at
        which the camera will operate as a tuple of ``(width, height)``
        measured in pixels. This is the resolution that the :meth:`capture`
        method will produce images at, and the resolution that
        :meth:`start_recording` will produce videos at.

        When set, the property reconfigures the camera so that the next call to
        these methods will use the new resolution.  The resolution must be
        specified as a ``(width, height)`` tuple, the camera must not be
        closed, and no recording must be active when the property is set.

        The property defaults to the Pi's currently configured display
        resolution.

        .. note::

            This attribute, in combination with :attr:`framerate`, determines
            the mode that the camera operates in. The actual sensor framerate
            and resolution used by the camera is influenced, but not directly
            set, by this property. See :ref:`camera_modes` for more
            information.
        """)

    def _get_still_encoding(self):
        self._check_camera_open()
        port = self._camera[0].output[self.CAMERA_CAPTURE_PORT]
        return port[0].format[0].encoding
    def _set_still_encoding(self, value):
        self._check_camera_open()
        if value == self._still_encoding.value:
            return
        self._check_recording_stopped()
        self._disable_camera()
        port = self._camera[0].output[self.CAMERA_CAPTURE_PORT]
        port[0].format[0].encoding = value
        if value == mmal.MMAL_ENCODING_OPAQUE:
            port[0].format[0].encoding_variant = mmal.MMAL_ENCODING_I420
        else:
            port[0].format[0].encoding_variant = value
        mmal_check(
            mmal.mmal_port_format_commit(port),
            prefix="Couldn't set capture port encoding")
        self._enable_camera()
    _still_encoding = property(_get_still_encoding, _set_still_encoding, doc="""
        Configures the encoding of the camera's still port.

        This attribute is intended for internal use only.
        """)

    def _get_saturation(self):
        self._check_camera_open()
        mp = mmal.MMAL_RATIONAL_T()
        mmal_check(
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
                raise PiCameraValueError(
                    "Invalid saturation value: %d (valid range -100..100)" % value)
        except TypeError:
            raise PiCameraValueError("Invalid saturation value: %s" % value)
        mmal_check(
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
        mmal_check(
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
                raise PiCameraValueError(
                    "Invalid sharpness value: %d (valid range -100..100)" % value)
        except TypeError:
            raise PiCameraValueError("Invalid sharpness value: %s" % value)
        mmal_check(
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
        mmal_check(
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
                raise PiCameraValueError(
                    "Invalid contrast value: %d (valid range -100..100)" % value)
        except TypeError:
            raise PiCameraValueError("Invalid contrast value: %s" % value)
        mmal_check(
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
        mmal_check(
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
                raise PiCameraValueError(
                    "Invalid brightness value: %d (valid range 0..100)" % value)
        except TypeError:
            raise PiCameraValueError("Invalid brightness value: %s" % value)
        mmal_check(
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

    def _get_shutter_speed(self):
        self._check_camera_open()
        mp = ct.c_uint32()
        mmal_check(
            mmal.mmal_port_parameter_get_uint32(
                self._camera[0].control,
                mmal.MMAL_PARAMETER_SHUTTER_SPEED,
                mp
                ),
            prefix="Failed to get shutter speed")
        return mp.value
    def _set_shutter_speed(self, value):
        self._check_camera_open()
        # XXX Valid values?
        mmal_check(
            mmal.mmal_port_parameter_set_uint32(
                self._camera[0].control,
                mmal.MMAL_PARAMETER_SHUTTER_SPEED,
                value
                ),
            prefix="Failed to set shutter speed")
    shutter_speed = property(_get_shutter_speed, _set_shutter_speed, doc="""
        Retrieves or sets the shutter speed of the camera in microseconds.

        When queried, the :attr:`shutter_speed` property returns the shutter
        speed of the camera in microseconds, or 0 which indicates that the
        speed will be automatically determined according to lighting
        conditions. Faster shutter times naturally require greater amounts of
        illumination and vice versa.

        When set, the property adjusts the shutter speed of the camera, which
        most obviously affects the illumination of subsequently captured
        images. Shutter speed can be adjusted while previews or recordings are
        running. The default value is 0 (auto).
        """)

    def _get_ISO(self):
        self._check_camera_open()
        mp = ct.c_uint32()
        mmal_check(
            mmal.mmal_port_parameter_get_uint32(
                self._camera[0].control,
                mmal.MMAL_PARAMETER_ISO,
                mp
                ),
            prefix="Failed to get ISO")
        return mp.value
    def _set_ISO(self, value):
        self._check_camera_open()
        try:
            if not (0 <= value <= 800):
                raise PiCameraValueError(
                    "Invalid ISO value: %d (valid range 0..800)" % value)
        except TypeError:
            raise PiCameraValueError("Invalid ISO value: %s" % value)
        mmal_check(
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

        When set, the property adjusts the sensitivity of the camera. Valid
        values are between 0 (auto) and 800. The actual value used when ISO is
        explicitly set will be one of the following values (whichever is
        closest): 100, 200, 320, 400, 500, 640, 800.

        ISO can be adjusted while previews or recordings are in progress. The
        default value is 0 which means the ISO is automatically set according
        to image-taking conditions.

        .. note::

            With ISO settings other than 0 (auto), the :attr:`exposure_mode`
            property becomes non-functional.

        .. _sensitivity of the camera to light: http://en.wikipedia.org/wiki/Film_speed#Digital
        """)

    def _get_meter_mode(self):
        self._check_camera_open()
        mp = mmal.MMAL_PARAMETER_EXPOSUREMETERINGMODE_T(
            mmal.MMAL_PARAMETER_HEADER_T(
                mmal.MMAL_PARAMETER_EXP_METERING_MODE,
                ct.sizeof(mmal.MMAL_PARAMETER_EXPOSUREMETERINGMODE_T)
                ))
        mmal_check(
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
            mmal_check(
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
        | Value         | Description                                       |
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
        mmal_check(
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
            mmal_check(
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
            raise PiCameraValueError(
                "Invalid video stabilization boolean value: %s" % value)
    video_stabilization = property(
        _get_video_stabilization, _set_video_stabilization, doc="""
        Retrieves or sets the video stabilization mode of the camera.

        When queried, the :attr:`video_stabilization` property returns a
        boolean value indicating whether or not the camera attempts to
        compensate for motion.

        When set, the property activates or deactivates video stabilization.
        The property can be set while recordings or previews are in progress.
        The default value is ``False``.

        .. note::

            The built-in video stabilization only accounts for `vertical and
            horizontal motion`_, not rotation.

        .. _vertical and horizontal motion: http://www.raspberrypi.org/phpBB3/viewtopic.php?p=342667&sid=ec7d95e887ab74a90ffaab87888c48cd#p342667
        """)

    def _get_exposure_compensation(self):
        self._check_camera_open()
        mp = ct.c_int32()
        mmal_check(
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
                raise PiCameraValueError(
                    "Invalid exposure compensation value: "
                    "%d (valid range -25..25)" % value)
        except TypeError:
            raise PiCameraValueError(
                "Invalid exposure compensation value: %s" % value)
        mmal_check(
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
        level. Each increment represents 1/6th of a stop. Hence setting the
        attribute to 6 increases exposure by 1 stop. The property can be set
        while recordings or previews are in progress. The default value is 0.
        """)

    def _get_exposure_mode(self):
        self._check_camera_open()
        mp = mmal.MMAL_PARAMETER_EXPOSUREMODE_T(
            mmal.MMAL_PARAMETER_HEADER_T(
                mmal.MMAL_PARAMETER_EXPOSURE_MODE,
                ct.sizeof(mmal.MMAL_PARAMETER_EXPOSUREMODE_T)
                ))
        mmal_check(
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
            mmal_check(
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
        mmal_check(
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
            mmal_check(
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

    def _get_awb_gains(self):
        raise NotImplementedError
        #self._check_camera_open()
        #mp = mmal.MMAL_PARAMETER_AWB_GAINS_T(
        #    mmal.MMAL_PARAMETER_HEADER_T(
        #        mmal.MMAL_PARAMETER_CUSTOM_AWB_GAINS,
        #        ct.sizeof(mmal.MMAL_PARAMETER_AWB_GAINS_T)
        #        ))
        #mmal_check(
        #    mmal.mmal_port_parameter_get(self._camera[0].control, mp.hdr),
        #    prefix="Failed to get auto-white-balance gains")
        #return mp.r_gain, mp.b_gain
    def _set_awb_gains(self, value):
        self._check_camera_open()
        try:
            red_gain, blue_gain = value
        except (ValueError, TypeError):
            red_gain = blue_gain = value
        if not (0.0 <= red_gain <= 8.0 and 0.0 <= blue_gain <= 8.0):
            raise PiCameraValueError(
                "Invalid gain(s) in (%f, %f) (valid range: 0.0-8.0)" % (
                    red_gain, blue_gain))
        mp = mmal.MMAL_PARAMETER_AWB_GAINS_T(
            mmal.MMAL_PARAMETER_HEADER_T(
                mmal.MMAL_PARAMETER_CUSTOM_AWB_GAINS,
                ct.sizeof(mmal.MMAL_PARAMETER_AWB_GAINS_T)
                ),
            mmal.MMAL_RATIONAL_T(*to_rational(red_gain)),
            mmal.MMAL_RATIONAL_T(*to_rational(blue_gain)),
            )
        mmal_check(
            mmal.mmal_port_parameter_set(self._camera[0].control, mp.hdr),
            prefix="Failed to set auto-white-balance gains")
    awb_gains = property(_get_awb_gains, _set_awb_gains, doc="""
        Sets the auto-white-balance gains of the camera.

        When set, this attribute adjusts the camera's auto-white-balance gains.
        The property can be specified as a single value in which case both red
        and blue gains will be adjusted equally, or as a `(red, blue)` tuple.
        Values can be specified as an :class:`int`, :class:`float` or
        :class:`~fractions.Fraction` and each gain must be between 0.0 and 8.0.
        Typical values for the gains are between 0.9 and 1.9.  The property can
        be set while recordings or previews are in progress.

        .. note::

            This attribute only has an effect when :attr:`awb_mode` is set to
            ``'off'``. The write-only nature of this attribute is a firmware
            limitation.
        """)

    def _get_image_effect(self):
        self._check_camera_open()
        mp = mmal.MMAL_PARAMETER_IMAGEFX_T(
            mmal.MMAL_PARAMETER_HEADER_T(
                mmal.MMAL_PARAMETER_IMAGE_EFFECT,
                ct.sizeof(mmal.MMAL_PARAMETER_IMAGEFX_T)
                ))
        mmal_check(
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
            mmal_check(
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
        mmal_check(
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
        mmal_check(
            mmal.mmal_port_parameter_set(self._camera[0].control, mp.hdr),
            prefix="Failed to set color effects")
    color_effects = property(_get_color_effects, _set_color_effects, doc="""
        Retrieves or sets the current color effect applied by the camera.

        When queried, the :attr:`color_effects` property either returns
        ``None`` which indicates that the camera is using normal color
        settings, or a ``(u, v)`` tuple where ``u`` and ``v`` are integer
        values between 0 and 255.

        When set, the property changes the color effect applied by the camera.
        The property can be set while recordings or previews are in progress.
        For example, to make the image black and white set the value to ``(128,
        128)``. The default value is ``None``.
        """)

    def _get_rotation(self):
        self._check_camera_open()
        mp = ct.c_int32()
        mmal_check(
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
            mmal_check(
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
        mmal_check(
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
            mmal_check(
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
        mmal_check(
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
            mmal_check(
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
        mmal_check(
            mmal.mmal_port_parameter_get(self._camera[0].control, mp.hdr),
            prefix="Failed to get crop")
        return (
            mp.rect.x / 65535.0,
            mp.rect.y / 65535.0,
            mp.rect.width / 65535.0,
            mp.rect.height / 65535.0,
            )
    def _set_crop(self, value):
        self._check_camera_open()
        try:
            x, y, w, h = value
        except (TypeError, ValueError) as e:
            raise PiCameraValueError(
                "Invalid crop rectangle (x, y, w, h) tuple: %s" % value)
        mp = mmal.MMAL_PARAMETER_INPUT_CROP_T(
            mmal.MMAL_PARAMETER_HEADER_T(
                mmal.MMAL_PARAMETER_INPUT_CROP,
                ct.sizeof(mmal.MMAL_PARAMETER_INPUT_CROP_T)
                ),
            mmal.MMAL_RECT_T(
                max(0, min(65535, int(65535 * x))),
                max(0, min(65535, int(65535 * y))),
                max(0, min(65535, int(65535 * w))),
                max(0, min(65535, int(65535 * h))),
                ),
            )
        mmal_check(
            mmal.mmal_port_parameter_set(self._camera[0].control, mp.hdr),
            prefix="Failed to set crop")
    crop = property(_get_crop, _set_crop, doc="""
        Retrieves or sets the crop applied to the camera's input.

        When queried, the :attr:`crop` property returns a ``(x, y, w, h)``
        tuple of floating point values ranging from 0.0 to 1.0, indicating the
        proportion of the image to include in the output (the "Region of
        Interest" or ROI). The default value is ``(0.0, 0.0, 1.0, 1.0)`` which
        indicates that everything should be included. The property can be set
        while recordings or previews are in progress.
        """)

    def _get_preview_alpha(self):
        mp = mmal.MMAL_DISPLAYREGION_T(
            mmal.MMAL_PARAMETER_HEADER_T(
                mmal.MMAL_PARAMETER_DISPLAYREGION,
                ct.sizeof(mmal.MMAL_DISPLAYREGION_T)
            ))
        mmal_check(
            mmal.mmal_port_parameter_get(self._preview[0].input[0], mp.hdr),
            prefix="Failed to get preview alpha")
        return mp.alpha
    def _set_preview_alpha(self, value):
        self._check_camera_open()
        try:
            if not (0 <= value <= 255):
                raise PiCameraValueError(
                    "Invalid alpha value: %d (valid range 0..255)" % value)
        except TypeError:
            raise PiCameraValueError("Invalid alpha value: %s" % value)
        mp = mmal.MMAL_DISPLAYREGION_T(
            mmal.MMAL_PARAMETER_HEADER_T(
                mmal.MMAL_PARAMETER_DISPLAYREGION,
                ct.sizeof(mmal.MMAL_DISPLAYREGION_T)
                ),
            set=mmal.MMAL_DISPLAY_SET_ALPHA,
            alpha=value
            )
        mmal_check(
            mmal.mmal_port_parameter_set(self._preview[0].input[0], mp.hdr),
            prefix="Failed to set preview alpha")
    preview_alpha = property(_get_preview_alpha, _set_preview_alpha, doc="""
        Retrieves or sets the opacity of the preview window.

        When queried, the :attr:`preview_alpha` property returns a value
        between 0 and 255 indicating the opacity of the preview window, where 0
        is completely transparent and 255 is completely opaque. The default
        value is 255. The property can be set while recordings or previews are
        in progress.

        .. note::

            If the preview is not running, the property will not reflect
            changes to it, but they will be in effect next time the preview is
            started. In other words, you can set preview_alpha to 128, but
            querying it will still return 255 (the default) until you call
            :meth:`start_preview` at which point the preview will appear
            semi-transparent and :attr:`preview_alpha` will suddenly return
            128. This appears to be a firmware issue.
        """)

    def _get_preview_layer(self):
        mp = mmal.MMAL_DISPLAYREGION_T(
            mmal.MMAL_PARAMETER_HEADER_T(
                mmal.MMAL_PARAMETER_DISPLAYREGION,
                ct.sizeof(mmal.MMAL_DISPLAYREGION_T)
            ))
        mmal_check(
            mmal.mmal_port_parameter_get(self._preview[0].input[0], mp.hdr),
            prefix="Failed to get preview alpha")
        return mp.layer
    def _set_preview_layer(self, value):
        self._check_camera_open()
        mp = mmal.MMAL_DISPLAYREGION_T(
            mmal.MMAL_PARAMETER_HEADER_T(
                mmal.MMAL_PARAMETER_DISPLAYREGION,
                ct.sizeof(mmal.MMAL_DISPLAYREGION_T)
                ),
            set=mmal.MMAL_DISPLAY_SET_LAYER,
            layer=value
            )
        mmal_check(
            mmal.mmal_port_parameter_set(self._preview[0].input[0], mp.hdr),
            prefix="Failed to set preview layer")
    preview_layer = property(
            _get_preview_layer, _set_preview_layer, doc="""
        Retrieves of sets the layer of the preview window.

        The :attr:`preview_layer` property is an integer which controls the
        layer that the preview window occupies. It defaults to 2 which results
        in the preview appearing above all other output.

        .. warning::

            Operation of this attribute is not yet fully understood. The
            documentation above is incomplete and may be incorrect!
        """)

    def _get_preview_fullscreen(self):
        mp = mmal.MMAL_DISPLAYREGION_T(
            mmal.MMAL_PARAMETER_HEADER_T(
                mmal.MMAL_PARAMETER_DISPLAYREGION,
                ct.sizeof(mmal.MMAL_DISPLAYREGION_T)
            ))
        mmal_check(
            mmal.mmal_port_parameter_get(self._preview[0].input[0], mp.hdr),
            prefix="Failed to get preview fullscreen")
        return mp.fullscreen != mmal.MMAL_FALSE
    def _set_preview_fullscreen(self, value):
        self._check_camera_open()
        value = bool(value)
        mp = mmal.MMAL_DISPLAYREGION_T(
            mmal.MMAL_PARAMETER_HEADER_T(
                mmal.MMAL_PARAMETER_DISPLAYREGION,
                ct.sizeof(mmal.MMAL_DISPLAYREGION_T)
                ),
            set=mmal.MMAL_DISPLAY_SET_FULLSCREEN,
            fullscreen={
                False: mmal.MMAL_FALSE,
                True:  mmal.MMAL_TRUE,
                }[value]
            )
        mmal_check(
            mmal.mmal_port_parameter_set(self._preview[0].input[0], mp.hdr),
            prefix="Failed to set preview fullscreen")
    preview_fullscreen = property(
            _get_preview_fullscreen, _set_preview_fullscreen, doc="""
        Retrieves or sets full-screen for the preview window.

        The :attr:`preview_fullscreen` property is a bool which controls
        whether the preview window takes up the entire display or not. When
        set to ``False``, the :attr:`preview_window` property can be used to
        control the precise size of the preview display. The property can be
        set while recordings or previews are active.

        .. note::

            The :attr:`preview_fullscreen` attribute is afflicted by the same
            issue as :attr:`preview_alpha` with regards to changes while the
            preview is not running.
        """)

    def _get_preview_window(self):
        mp = mmal.MMAL_DISPLAYREGION_T(
            mmal.MMAL_PARAMETER_HEADER_T(
                mmal.MMAL_PARAMETER_DISPLAYREGION,
                ct.sizeof(mmal.MMAL_DISPLAYREGION_T)
            ))
        mmal_check(
            mmal.mmal_port_parameter_get(self._preview[0].input[0], mp.hdr),
            prefix="Failed to get preview window")
        return (
            mp.dest_rect.x,
            mp.dest_rect.y,
            mp.dest_rect.width,
            mp.dest_rect.height,
            )
    def _set_preview_window(self, value):
        self._check_camera_open()
        try:
            x, y, w, h = value
        except (TypeError, ValueError) as e:
            raise PiCameraValueError(
                "Invalid window rectangle (x, y, w, h) tuple: %s" % value)
        mp = mmal.MMAL_DISPLAYREGION_T(
            mmal.MMAL_PARAMETER_HEADER_T(
                mmal.MMAL_PARAMETER_DISPLAYREGION,
                ct.sizeof(mmal.MMAL_DISPLAYREGION_T)
                ),
            set=mmal.MMAL_DISPLAY_SET_DEST_RECT,
            dest_rect=mmal.MMAL_RECT_T(x, y, w, h),
            )
        mmal_check(
            mmal.mmal_port_parameter_set(self._preview[0].input[0], mp.hdr),
            prefix="Failed to set preview window")
    preview_window = property(_get_preview_window, _set_preview_window, doc="""
        Retrieves or sets the size of the preview window.

        When the :attr:`preview_fullscreen` property is set to ``False``, the
        :attr:`preview_window` property specifies the size and position of the
        preview window on the display. The property is a 4-tuple consisting of
        ``(x, y, width, height)``. The property can be set while recordings or
        previews are active.

        .. note::

            The :attr:`preview_window` attribute is afflicted by the same issue
            as :attr:`preview_alpha` with regards to changes while the preview
            is not running.
        """)

