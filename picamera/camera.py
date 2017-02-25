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

# Make Py2's str equivalent to Py3's
str = type('')

import warnings
import datetime
import mimetypes
import ctypes as ct
import threading
from fractions import Fraction
from operator import itemgetter
from collections import namedtuple

from . import bcm_host, mmal, mmalobj as mo
from .exc import (
    PiCameraError,
    PiCameraValueError,
    PiCameraRuntimeError,
    PiCameraClosed,
    PiCameraNotRecording,
    PiCameraAlreadyRecording,
    PiCameraMMALError,
    PiCameraDeprecated,
    PiCameraFallback,
    )
from .encoders import (
    PiVideoFrame,
    PiVideoEncoder,
    PiRawVideoEncoder,
    PiCookedVideoEncoder,
    PiRawOneImageEncoder,
    PiRawMultiImageEncoder,
    PiCookedOneImageEncoder,
    PiCookedMultiImageEncoder,
    )
from .renderers import (
    PiPreviewRenderer,
    PiOverlayRenderer,
    PiNullSink,
    )
from .color import Color

try:
    from RPi import GPIO
except ImportError:
    # Can't find RPi.GPIO so just null-out the reference
    GPIO = None


def docstring_values(values, indent=8):
    """
    Formats a dictionary of values for inclusion in a docstring.
    """
    return ('\n' + ' ' * indent).join(
        "* ``'%s'``" % k
        for (k, v) in
        sorted(values.items(), key=itemgetter(1)))


class PiCameraMaxResolution(object):
    """
    Singleton representing the maximum resolution of the camera module.
    """
PiCameraMaxResolution = PiCameraMaxResolution()


class PiCameraMaxFramerate(object):
    """
    Singleton representing the maximum framerate of the camera module.
    """
PiCameraMaxFramerate = PiCameraMaxFramerate()


class PiCamera(object):
    """
    Provides a pure Python interface to the Raspberry Pi's camera module.

    Upon construction, this class initializes the camera. The *camera_num*
    parameter (which defaults to 0) selects the camera module that the instance
    will represent. Only the Raspberry Pi compute module currently supports
    more than one camera.

    The *sensor_mode*, *resolution*, *framerate*, *framerate_range*, and
    *clock_mode* parameters provide initial values for the :attr:`sensor_mode`,
    :attr:`resolution`, :attr:`framerate`, :attr:`framerate_range`, and
    :attr:`clock_mode` attributes of the class (these attributes are all
    relatively expensive to set individually, hence setting them all upon
    construction is a speed optimization). Please refer to the attribute
    documentation for more information and default values.

    The *stereo_mode* and *stereo_decimate* parameters configure dual cameras
    on a compute module for sterescopic mode. These parameters can only be set
    at construction time; they cannot be altered later without closing the
    :class:`PiCamera` instance and recreating it. The *stereo_mode* parameter
    defaults to ``'none'`` (no stereoscopic mode) but can be set to
    ``'side-by-side'`` or ``'top-bottom'`` to activate a stereoscopic mode. If
    the *stereo_decimate* parameter is ``True``, the resolution of the two
    cameras will be halved so that the resulting image has the same dimensions
    as if stereoscopic mode were not being used.

    The *led_pin* parameter can be used to specify the GPIO pin which should be
    used to control the camera's LED via the :attr:`led` attribute. If this is
    not specified, it should default to the correct value for your Pi platform.
    You should only need to specify this parameter if you are using a custom
    DeviceTree blob (this is only typical on the `Compute Module`_ platform).

    No preview or recording is started automatically upon construction.  Use
    the :meth:`capture` method to capture images, the :meth:`start_recording`
    method to begin recording video, or the :meth:`start_preview` method to
    start live display of the camera's input.

    Several attributes are provided to adjust the camera's configuration. Some
    of these can be adjusted while a recording is running, like
    :attr:`brightness`. Others, like :attr:`resolution`, can only be adjusted
    when the camera is idle.

    When you are finished with the camera, you should ensure you call the
    :meth:`close` method to release the camera resources::

        camera = PiCamera()
        try:
            # do something with the camera
            pass
        finally:
            camera.close()

    The class supports the context manager protocol to make this particularly
    easy (upon exiting the :keyword:`with` statement, the :meth:`close` method
    is automatically called)::

        with PiCamera() as camera:
            # do something with the camera
            pass

    .. versionchanged:: 1.8
        Added *stereo_mode* and *stereo_decimate* parameters.

    .. versionchanged:: 1.9
        Added *resolution*, *framerate*, and *sensor_mode* parameters.

    .. versionchanged:: 1.10
        Added *led_pin* parameter.

    .. versionchanged:: 1.11
        Added *clock_mode* parameter, and permitted setting of resolution as
        appropriately formatted string.

    .. versionchanged:: 1.13
        Added *framerate_range* parameter.

    .. _Compute Module: https://www.raspberrypi.org/documentation/hardware/computemodule/cmio-camera.md
    """

    CAMERA_PREVIEW_PORT = 0
    CAMERA_VIDEO_PORT = 1
    CAMERA_CAPTURE_PORT = 2
    MAX_RESOLUTION = PiCameraMaxResolution # modified by PiCamera.__init__
    MAX_FRAMERATE = PiCameraMaxFramerate # modified by PiCamera.__init__
    DEFAULT_ANNOTATE_SIZE = 32
    CAPTURE_TIMEOUT = 60

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

    FLASH_MODES = {
        'off':           mmal.MMAL_PARAM_FLASH_OFF,
        'auto':          mmal.MMAL_PARAM_FLASH_AUTO,
        'on':            mmal.MMAL_PARAM_FLASH_ON,
        'redeye':        mmal.MMAL_PARAM_FLASH_REDEYE,
        'fillin':        mmal.MMAL_PARAM_FLASH_FILLIN,
        'torch':         mmal.MMAL_PARAM_FLASH_TORCH,
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
        # The following don't work
        #'posterize':     mmal.MMAL_PARAM_IMAGEFX_POSTERIZE,
        #'whiteboard':    mmal.MMAL_PARAM_IMAGEFX_WHITEBOARD,
        #'blackboard':    mmal.MMAL_PARAM_IMAGEFX_BLACKBOARD,
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
        'deinterlace1':  mmal.MMAL_PARAM_IMAGEFX_DEINTERLACE_DOUBLE,
        'deinterlace2':  mmal.MMAL_PARAM_IMAGEFX_DEINTERLACE_ADV,
        }

    DRC_STRENGTHS = {
        'off':    mmal.MMAL_PARAMETER_DRC_STRENGTH_OFF,
        'low':    mmal.MMAL_PARAMETER_DRC_STRENGTH_LOW,
        'medium': mmal.MMAL_PARAMETER_DRC_STRENGTH_MEDIUM,
        'high':   mmal.MMAL_PARAMETER_DRC_STRENGTH_HIGH,
        }

    RAW_FORMATS = {
        'yuv',
        'rgb',
        'rgba',
        'bgr',
        'bgra',
        }

    STEREO_MODES = {
        'none':         mmal.MMAL_STEREOSCOPIC_MODE_NONE,
        'side-by-side': mmal.MMAL_STEREOSCOPIC_MODE_SIDE_BY_SIDE,
        'top-bottom':   mmal.MMAL_STEREOSCOPIC_MODE_BOTTOM,
        }

    CLOCK_MODES = {
        'reset':        mmal.MMAL_PARAM_TIMESTAMP_MODE_RESET_STC,
        'raw':          mmal.MMAL_PARAM_TIMESTAMP_MODE_RAW_STC,
        }

    _METER_MODES_R    = {v: k for (k, v) in METER_MODES.items()}
    _EXPOSURE_MODES_R = {v: k for (k, v) in EXPOSURE_MODES.items()}
    _FLASH_MODES_R    = {v: k for (k, v) in FLASH_MODES.items()}
    _AWB_MODES_R      = {v: k for (k, v) in AWB_MODES.items()}
    _IMAGE_EFFECTS_R  = {v: k for (k, v) in IMAGE_EFFECTS.items()}
    _DRC_STRENGTHS_R  = {v: k for (k, v) in DRC_STRENGTHS.items()}
    _STEREO_MODES_R   = {v: k for (k, v) in STEREO_MODES.items()}
    _CLOCK_MODES_R    = {v: k for (k, v) in CLOCK_MODES.items()}

    __slots__ = (
        '_used_led',
        '_led_pin',
        '_camera',
        '_camera_config',
        '_camera_exception',
        '_revision',
        '_preview',
        '_preview_alpha',
        '_preview_layer',
        '_preview_fullscreen',
        '_preview_window',
        '_splitter',
        '_splitter_connection',
        '_encoders_lock',
        '_encoders',
        '_overlays',
        '_raw_format',
        '_image_effect_params',
        '_exif_tags',
        )

    def __init__(
            self, camera_num=0, stereo_mode='none', stereo_decimate=False,
            resolution=None, framerate=None, sensor_mode=0, led_pin=None,
            clock_mode='reset', framerate_range=None):
        bcm_host.bcm_host_init()
        mimetypes.add_type('application/h264',  '.h264',  False)
        mimetypes.add_type('application/mjpeg', '.mjpg',  False)
        mimetypes.add_type('application/mjpeg', '.mjpeg', False)
        self._used_led = False
        if GPIO and led_pin is None:
            try:
                led_pin = {
                    (0, 0): 2,  # compute module (default for cam 0)
                    (0, 1): 30, # compute module (default for cam 1)
                    (1, 0): 5,  # Pi 1 model B rev 1
                    (2, 0): 5,  # Pi 1 model B rev 2 or model A
                    (3, 0): 32, # Pi 1 model B+ or Pi 2 model B
                    }[(GPIO.RPI_REVISION, camera_num)]
            except KeyError:
                raise PiCameraError(
                        'Unable to determine default GPIO LED pin for RPi '
                        'revision %d and camera num %d' % (
                            GPIO.RPI_REVISION, camera_num))
        self._led_pin = led_pin
        self._camera = None
        self._camera_config = None
        self._camera_exception = None
        self._preview = None
        self._preview_alpha = 255
        self._preview_layer = 2
        self._preview_fullscreen = True
        self._preview_window = None
        self._splitter = None
        self._splitter_connection = None
        self._encoders_lock = threading.Lock()
        self._encoders = {}
        self._overlays = []
        self._raw_format = 'yuv'
        self._image_effect_params = None
        with mo.MMALCameraInfo() as camera_info:
            info = camera_info.control.params[mmal.MMAL_PARAMETER_CAMERA_INFO]
            self._revision = 'ov5647'
            if camera_info.info_rev > 1:
                self._revision = info.cameras[camera_num].camera_name.decode('ascii')
            self._exif_tags = {
                'IFD0.Model': 'RP_%s' % self._revision,
                'IFD0.Make': 'RaspberryPi',
                }
            if PiCamera.MAX_RESOLUTION is PiCameraMaxResolution:
                PiCamera.MAX_RESOLUTION = mo.PiResolution(
                        info.cameras[camera_num].max_width,
                        info.cameras[camera_num].max_height,
                        )
        if PiCamera.MAX_FRAMERATE is PiCameraMaxFramerate:
            if self._revision.upper() == 'OV5647':
                PiCamera.MAX_FRAMERATE = 90
            else:
                PiCamera.MAX_FRAMERATE = 120
        if resolution is None:
            # Get screen resolution
            w = ct.c_uint32()
            h = ct.c_uint32()
            if bcm_host.graphics_get_display_size(0, w, h) == -1:
                w = 1280
                h = 720
            else:
                w = int(w.value)
                h = int(h.value)
            resolution = mo.PiResolution(w, h)
        elif resolution is PiCameraMaxResolution:
            resolution = PiCamera.MAX_RESOLUTION
        else:
            resolution = mo.to_resolution(resolution)
        if framerate_range is None:
            if framerate is None:
                framerate = 30
            elif framerate is PiCameraMaxFramerate:
                framerate = PiCamera.MAX_FRAMERATE
            else:
                framerate = mo.to_fraction(framerate)
        elif framerate is not None:
            raise PiCameraValueError(
                "Can't specify framerate and framerate_range")
        else:
            try:
                low, high = framerate_range
            except TypeError:
                raise PiCameraValueError(
                    "framerate_range must have (low, high) values")
            if low is PiCameraMaxFramerate:
                low = PiCamera.MAX_FRAMERATE
            if high is PiCameraMaxFramerate:
                high = PiCamera.MAX_FRAMERATE
            framerate = (mo.to_fraction(low), mo.to_fraction(high))
        try:
            stereo_mode = self.STEREO_MODES[stereo_mode]
        except KeyError:
            raise PiCameraValueError('Invalid stereo mode: %s' % stereo_mode)
        try:
            clock_mode = self.CLOCK_MODES[clock_mode]
        except KeyError:
            raise PiCameraValueError('Invalid clock mode: %s' % clock_mode)
        try:
            self._init_camera(camera_num, stereo_mode, stereo_decimate)
            self._configure_camera(sensor_mode, framerate, resolution, clock_mode)
            self._init_preview()
            self._init_splitter()
            self._camera.enable()
            self._init_defaults()
        except:
            self.close()
            raise

    def _init_led(self):
        global GPIO
        if GPIO:
            try:
                GPIO.setmode(GPIO.BCM)
                GPIO.setwarnings(False)
                GPIO.setup(self._led_pin, GPIO.OUT, initial=GPIO.LOW)
                self._used_led = True
            except RuntimeError:
                # We're probably not running as root. In this case, forget the
                # GPIO reference so we don't try anything further
                GPIO = None

    def _init_camera(self, num, stereo_mode, stereo_decimate):
        try:
            self._camera = mo.MMALCamera()
        except PiCameraMMALError as e:
            if e.status == mmal.MMAL_ENOMEM:
                raise PiCameraError(
                    "Camera is not enabled. Try running 'sudo raspi-config' "
                    "and ensure that the camera has been enabled.")
            else:
                raise
        self._camera_config = self._camera.control.params[mmal.MMAL_PARAMETER_CAMERA_CONFIG]
        # Don't attempt to set this if stereo mode isn't requested as it'll
        # break compatibility on older firmwares
        if stereo_mode != mmal.MMAL_STEREOSCOPIC_MODE_NONE:
            for p in self._camera.outputs:
                mp = mmal.MMAL_PARAMETER_STEREOSCOPIC_MODE_T(
                    mmal.MMAL_PARAMETER_HEADER_T(
                        mmal.MMAL_PARAMETER_STEREOSCOPIC_MODE,
                        ct.sizeof(mmal.MMAL_PARAMETER_STEREOSCOPIC_MODE_T),
                    ),
                    mode=stereo_mode,
                    decimate=stereo_decimate,
                    swap_eyes=False,
                    )
                p.params[mmal.MMAL_PARAMETER_STEREOSCOPIC_MODE] = mp
        # Must be done *after* stereo-scopic setting
        self._camera.control.params[mmal.MMAL_PARAMETER_CAMERA_NUM] = num

    def _init_defaults(self):
        self.sharpness = 0
        self.contrast = 0
        self.brightness = 50
        self.saturation = 0
        self.iso = 0 # auto
        self.video_stabilization = False
        self.exposure_compensation = 0
        self.exposure_mode = 'auto'
        self.meter_mode = 'average'
        self.awb_mode = 'auto'
        self.image_effect = 'none'
        self.color_effects = None
        self.rotation = 0
        self.hflip = self.vflip = False
        self.zoom = (0.0, 0.0, 1.0, 1.0)

    def _init_splitter(self):
        # Create a splitter component for the video port. This is to permit
        # video recordings and captures where use_video_port=True to occur
        # simultaneously (#26)
        self._splitter = mo.MMALSplitter()
        self._splitter.inputs[0].connect(
                self._camera.outputs[self.CAMERA_VIDEO_PORT]).enable()

    def _init_preview(self):
        # Create a null-sink component, enable it and connect it to the
        # camera's preview port. If nothing is connected to the preview port,
        # the camera doesn't measure exposure and captured images gradually
        # fade to black (issue #22)
        self._preview = PiNullSink(
            self, self._camera.outputs[self.CAMERA_PREVIEW_PORT])

    def _start_capture(self, port):
        # Only enable capture if the port is the camera's still port, or if
        # there's a single active encoder on the video splitter
        if (
                port == self._camera.outputs[self.CAMERA_CAPTURE_PORT] or
                len([e for e in self._encoders.values() if e.active]) == 1):
            port.params[mmal.MMAL_PARAMETER_CAPTURE] = True

    def _stop_capture(self, port):
        # Only disable capture if the port is the camera's still port, or if
        # there's a single active encoder on the video splitter
        if (
                port == self._camera.outputs[self.CAMERA_CAPTURE_PORT] or
                len([e for e in self._encoders.values() if e.active]) == 1):
            port.params[mmal.MMAL_PARAMETER_CAPTURE] = False

    def _check_camera_open(self):
        """
        Raise an exception if the camera is already closed, or if the camera
        has encountered a fatal error.
        """
        exc, self._camera_exception = self._camera_exception, None
        if exc:
            raise exc
        if self.closed:
            raise PiCameraClosed("Camera is closed")

    def _check_recording_stopped(self):
        """
        Raise an exception if the camera is currently recording.
        """
        if self.recording:
            raise PiCameraRuntimeError("Recording is currently running")

    def _get_ports(self, from_video_port, splitter_port):
        """
        Determine the camera and output ports for given capture options.

        See :ref:`camera_hardware` for more information on picamera's usage of
        camera, splitter, and encoder ports. The general idea here is that the
        capture (still) port operates on its own, while the video port is
        always connected to a splitter component, so requests for a video port
        also have to specify which splitter port they want to use.
        """
        self._check_camera_open()
        if from_video_port and (splitter_port in self._encoders):
            raise PiCameraAlreadyRecording(
                    'The camera is already using port %d ' % splitter_port)
        camera_port = (
            self._camera.outputs[self.CAMERA_VIDEO_PORT]
            if from_video_port else
            self._camera.outputs[self.CAMERA_CAPTURE_PORT]
            )
        output_port = (
            self._splitter.outputs[splitter_port]
            if from_video_port else
            camera_port
            )
        return (camera_port, output_port)

    def _get_output_format(self, output):
        """
        Given an output object, attempt to determine the requested format.

        We attempt to determine the filename of the *output* object and derive
        a MIME type from the extension. If *output* has no filename, an error
        is raised.
        """
        if isinstance(output, bytes):
            filename = output.decode('utf-8')
        elif isinstance(output, str):
            filename = output
        else:
            try:
                filename = output.name
            except AttributeError:
                raise PiCameraValueError(
                    'Format must be specified when output has no filename')
        (type, encoding) = mimetypes.guess_type(filename, strict=False)
        if not type:
            raise PiCameraValueError(
                'Unable to determine type from filename %s' % filename)
        return type

    def _get_image_format(self, output, format=None):
        """
        Given an output object and an optional format, attempt to determine the
        requested image format.

        This method is used by all capture methods to determine the requested
        output format. If *format* is specified as a MIME-type the "image/"
        prefix is stripped. If *format* is not specified, then
        :meth:`_get_output_format` will be called to attempt to determine
        format from the *output* object.
        """
        if isinstance(format, bytes):
            format = format.decode('utf-8')
        format = format or self._get_output_format(output)
        format = (
            format[6:] if format.startswith('image/') else
            format)
        if format == 'x-ms-bmp':
            format = 'bmp'
        if format == 'raw':
            format = self.raw_format
        return format

    def _get_video_format(self, output, format=None):
        """
        Given an output object and an optional format, attempt to determine the
        requested video format.

        This method is used by all recording methods to determine the requested
        output format. If *format* is specified as a MIME-type the "video/" or
        "application/" prefix will be stripped. If *format* is not specified,
        then :meth:`_get_output_format` will be called to attempt to determine
        format from the *output* object.
        """
        if isinstance(format, bytes):
            format = format.decode('utf-8')
        format = format or self._get_output_format(output)
        format = (
            format[6:]  if format.startswith('video/') else
            format[12:] if format.startswith('application/') else
            format)
        return format

    def _get_image_encoder(
            self, camera_port, output_port, format, resize, **options):
        """
        Construct an image encoder for the requested parameters.

        This method is called by :meth:`capture` and :meth:`capture_continuous`
        to construct an image encoder. The *camera_port* parameter gives the
        MMAL camera port that should be enabled for capture by the encoder. The
        *output_port* parameter gives the MMAL port that the encoder should
        read output from (this may be the same as the camera port, but may be
        different if other component(s) like a splitter have been placed in the
        pipeline). The *format* parameter indicates the image format and will
        be one of:

        * ``'jpeg'``
        * ``'png'``
        * ``'gif'``
        * ``'bmp'``
        * ``'yuv'``
        * ``'rgb'``
        * ``'rgba'``
        * ``'bgr'``
        * ``'bgra'``

        The *resize* parameter indicates the size that the encoder should
        resize the output to (presumably by including a resizer in the
        pipeline). Finally, *options* includes extra keyword arguments that
        should be passed verbatim to the encoder.
        """
        encoder_class = (
                PiRawOneImageEncoder if format in self.RAW_FORMATS else
                PiCookedOneImageEncoder)
        return encoder_class(
                self, camera_port, output_port, format, resize, **options)

    def _get_images_encoder(
            self, camera_port, output_port, format, resize, **options):
        """
        Construct a multi-image encoder for the requested parameters.

        This method is largely equivalent to :meth:`_get_image_encoder` with
        the exception that the encoder returned should expect to be passed an
        iterable of outputs to its :meth:`~PiEncoder.start` method, rather than
        a single output object. This method is called by the
        :meth:`capture_sequence` method.

        All parameters are the same as in :meth:`_get_image_encoder`. Please
        refer to the documentation for that method for further information.
        """
        encoder_class = (
                PiRawMultiImageEncoder if format in self.RAW_FORMATS else
                PiCookedMultiImageEncoder)
        return encoder_class(
                self, camera_port, output_port, format, resize, **options)

    def _get_video_encoder(
            self, camera_port, output_port, format, resize, **options):
        """
        Construct a video encoder for the requested parameters.

        This method is called by :meth:`start_recording` and
        :meth:`record_sequence` to construct a video encoder.  The
        *camera_port* parameter gives the MMAL camera port that should be
        enabled for capture by the encoder. The *output_port* parameter gives
        the MMAL port that the encoder should read output from (this may be the
        same as the camera port, but may be different if other component(s)
        like a splitter have been placed in the pipeline). The *format*
        parameter indicates the video format and will be one of:

        * ``'h264'``
        * ``'mjpeg'``

        The *resize* parameter indicates the size that the encoder should
        resize the output to (presumably by including a resizer in the
        pipeline). Finally, *options* includes extra keyword arguments that
        should be passed verbatim to the encoder.
        """
        encoder_class = (
                PiRawVideoEncoder if format in self.RAW_FORMATS else
                PiCookedVideoEncoder)
        return encoder_class(
                self, camera_port, output_port, format, resize, **options)

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
        for port in list(self._encoders):
            self.stop_recording(splitter_port=port)
        assert not self.recording
        for overlay in list(self._overlays):
            self.remove_overlay(overlay)
        if self._preview:
            self._preview.close()
            self._preview = None
        if self._splitter:
            self._splitter.close()
            self._splitter = None
        if self._camera:
            self._camera.close()
            self._camera = None
        exc, self._camera_exception = self._camera_exception, None
        if exc:
            raise exc

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.close()

    def start_preview(self, **options):
        """
        Displays the preview overlay.

        This method starts a camera preview as an overlay on the Pi's primary
        display (HDMI or composite). A :class:`PiRenderer` instance (more
        specifically, a :class:`PiPreviewRenderer`) is constructed with the
        keyword arguments captured in *options*, and is returned from the
        method (this instance is also accessible from the :attr:`preview`
        attribute for as long as the renderer remains active).  By default, the
        renderer will be opaque and fullscreen.

        This means the default preview overrides whatever is currently visible
        on the display. More specifically, the preview does not rely on a
        graphical environment like X-Windows (it can run quite happily from a
        TTY console); it is simply an overlay on the Pi's video output. To stop
        the preview and reveal the display again, call :meth:`stop_preview`.
        The preview can be started and stopped multiple times during the
        lifetime of the :class:`PiCamera` object.

        All other camera properties can be modified "live" while the preview is
        running (e.g. :attr:`brightness`).

        .. note::

            Because the default preview typically obscures the screen, ensure
            you have a means of stopping a preview before starting one. If the
            preview obscures your interactive console you won't be able to
            Alt+Tab back to it as the preview isn't in a window. If you are in
            an interactive Python session, simply pressing Ctrl+D usually
            suffices to terminate the environment, including the camera and its
            associated preview.
        """
        self._check_camera_open()
        self._preview.close()
        options.setdefault('layer', self._preview_layer)
        options.setdefault('alpha', self._preview_alpha)
        options.setdefault('fullscreen', self._preview_fullscreen)
        options.setdefault('window', self._preview_window)
        renderer = PiPreviewRenderer(
            self, self._camera.outputs[self.CAMERA_PREVIEW_PORT], **options)
        self._preview = renderer
        return renderer

    def stop_preview(self):
        """
        Hides the preview overlay.

        If :meth:`start_preview` has previously been called, this method shuts
        down the preview display which generally results in the underlying
        display becoming visible again. If a preview is not currently running,
        no exception is raised - the method will simply do nothing.
        """
        self._check_camera_open()
        self._preview.close()
        self._preview = PiNullSink(
            self, self._camera.outputs[self.CAMERA_PREVIEW_PORT])

    def add_overlay(self, source, size=None, format=None, **options):
        """
        Adds a static overlay to the preview output.

        This method creates a new static overlay using the same rendering
        mechanism as the preview. Overlays will appear on the Pi's video
        output, but will not appear in captures or video recordings. Multiple
        overlays can exist; each call to :meth:`add_overlay` returns a new
        :class:`PiOverlayRenderer` instance representing the overlay.

        The *source* must be an object that supports the :ref:`buffer protocol
        <bufferobjects>` in one of the supported unencoded formats: ``'yuv'``,
        ``'rgb'``, ``'rgba'``, ``'bgr'``, or ``'bgra'``. The format can
        specified explicitly with the optional *format* parameter. If not
        specified, the method will attempt to guess the format based on the
        length of *source* and the *size* (assuming 3 bytes per pixel for RGB,
        and 4 bytes for RGBA).

        The optional *size* parameter specifies the size of the source image as
        a ``(width, height)`` tuple. If this is omitted or ``None`` then the
        size is assumed to be the same as the camera's current
        :attr:`resolution`.

        The length of *source* must take into account that widths are rounded
        up to the nearest multiple of 32, and heights to the nearest multiple
        of 16.  For example, if *size* is ``(1280, 720)``, and *format* is
        ``'rgb'``, then *source* must be a buffer with length 1280 × 720 × 3
        bytes, or 2,764,800 bytes (because 1280 is a multiple of 32, and 720 is
        a multiple of 16 no extra rounding is required).  However, if *size* is
        ``(97, 57)``, and *format* is ``'rgb'`` then *source* must be a buffer
        with length 128 × 64 × 3 bytes, or 24,576 bytes (pixels beyond column
        97 and row 57 in the source will be ignored).

        New overlays default to *layer* 0, whilst the preview defaults to layer
        2. Higher numbered layers obscure lower numbered layers, hence new
        overlays will be invisible (if the preview is running) by default. You
        can make the new overlay visible either by making any existing preview
        transparent (with the :attr:`~PiRenderer.alpha` property) or by moving
        the overlay into a layer higher than the preview (with the
        :attr:`~PiRenderer.layer` property).

        All keyword arguments captured in *options* are passed onto the
        :class:`PiRenderer` constructor. All camera properties except
        :attr:`resolution` and :attr:`framerate` can be modified while overlays
        exist. The reason for these exceptions is that the overlay has a static
        resolution and changing the camera's mode would require resizing of the
        source.

        .. warning::

            If too many overlays are added, the display output will be disabled
            and a reboot will generally be required to restore the display.
            Overlays are composited "on the fly". Hence, a real-time constraint
            exists wherein for each horizontal line of HDMI output, the content
            of all source layers must be fetched, resized, converted, and
            blended to produce the output pixels.

            If enough overlays exist (where "enough" is a number dependent on
            overlay size, display resolution, bus frequency, and several other
            factors making it unrealistic to calculate in advance), this
            process breaks down and video output fails. One solution is to add
            ``dispmanx_offline=1`` to ``/boot/config.txt`` to force the use of
            an off-screen buffer. Be aware that this requires more GPU memory
            and may reduce the update rate.

        .. _RGB: https://en.wikipedia.org/wiki/RGB
        .. _RGBA: https://en.wikipedia.org/wiki/RGBA_color_space

        .. versionadded:: 1.8

        .. versionchanged:: 1.13
            Added *format* parameter
        """
        self._check_camera_open()
        renderer = PiOverlayRenderer(self, source, size, format, **options)
        self._overlays.append(renderer)
        return renderer

    def remove_overlay(self, overlay):
        """
        Removes a static overlay from the preview output.

        This method removes an overlay which was previously created by
        :meth:`add_overlay`. The *overlay* parameter specifies the
        :class:`PiRenderer` instance that was returned by :meth:`add_overlay`.

        .. versionadded:: 1.8
        """
        if not overlay in self._overlays:
            raise PiCameraValueError(
                "The specified overlay is not owned by this instance of "
                "PiCamera")
        overlay.close()
        self._overlays.remove(overlay)

    def start_recording(
            self, output, format=None, resize=None, splitter_port=1, **options):
        """
        Start recording video from the camera, storing it in *output*.

        If *output* is a string, it will be treated as a filename for a new
        file which the video will be written to. If *output* is not a string,
        but is an object with a ``write`` method, it is assumed to be a
        file-like object and the video data is appended to it (the
        implementation only assumes the object has a ``write()`` method - no
        other methods are required but ``flush`` will be called at the end of
        recording if it is present). If *output* is not a string, and has no
        ``write`` method it is assumed to be a writeable object implementing
        the buffer protocol. In this case, the video frames will be written
        sequentially to the underlying buffer (which must be large enough to
        accept all frame data).

        If *format* is ``None`` (the default), the method will attempt to guess
        the required video format from the extension of *output* (if it's a
        string), or from the *name* attribute of *output* (if it has one). In
        the case that the format cannot be determined, a
        :exc:`PiCameraValueError` will be raised.

        If *format* is not ``None``, it must be a string specifying the format
        that you want the video output in. The format can be a MIME-type or
        one of the following strings:

        * ``'h264'`` - Write an H.264 video stream
        * ``'mjpeg'`` - Write an M-JPEG video stream
        * ``'yuv'`` - Write the raw video data to a file in YUV420 format
        * ``'rgb'`` - Write the raw video data to a file in 24-bit RGB format
        * ``'rgba'`` - Write the raw video data to a file in 32-bit RGBA format
        * ``'bgr'`` - Write the raw video data to a file in 24-bit BGR format
        * ``'bgra'`` - Write the raw video data to a file in 32-bit BGRA format

        If *resize* is not ``None`` (the default), it must be a two-element
        tuple specifying the width and height that the video recording should
        be resized to. This is particularly useful for recording video using
        the full resolution of the camera sensor (which is not possible in
        H.264 without down-sizing the output).

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
          'high', but can be one of 'baseline', 'main', 'extended', 'high', or
          'constrained'.

        * *level* - The `H.264 level`_ to use for encoding. Defaults to '4',
          but can be any H.264 level up to '4.2'.

        * *intra_period* - The key frame rate (the rate at which I-frames are
          inserted in the output). Defaults to ``None``, but can be any 32-bit
          integer value representing the number of frames between successive
          I-frames. The special value 0 causes the encoder to produce a single
          initial I-frame, and then only P-frames subsequently. Note that
          :meth:`split_recording` will fail in this mode.

        * *intra_refresh* - The key frame format (the way in which I-frames
          will be inserted into the output stream). Defaults to ``None``, but
          can be one of 'cyclic', 'adaptive', 'both', or 'cyclicrows'.

        * *inline_headers* - When ``True``, specifies that the encoder should
          output SPS/PPS headers within the stream to ensure GOPs (groups of
          pictures) are self describing. This is important for streaming
          applications where the client may wish to seek within the stream, and
          enables the use of :meth:`split_recording`. Defaults to ``True`` if
          not specified.

        * *sei* - When ``True``, specifies the encoder should include
          "Supplemental Enhancement Information" within the output stream.
          Defaults to ``False`` if not specified.

        * *sps_timing* - When ``True`` the encoder includes the camera's
          framerate in the SPS header. Defaults to ``False`` if not specified.

        * *motion_output* - Indicates the output destination for motion vector
          estimation data. When ``None`` (the default), motion data is not
          output. Otherwise, this can be a filename string, a file-like object,
          or a writeable buffer object (as with the *output* parameter).

        All encoded formats accept the following additional options:

        * *bitrate* - The bitrate at which video will be encoded. Defaults to
          17000000 (17Mbps) if not specified. The maximum value depends on the
          selected `H.264 level`_ and profile. Bitrate 0 indicates the encoder
          should not use bitrate control (the encoder is limited by the quality
          only).

        * *quality* - Specifies the quality that the encoder should attempt
          to maintain. For the ``'h264'`` format, use values between 10 and 40
          where 10 is extremely high quality, and 40 is extremely low (20-25 is
          usually a reasonable range for H.264 encoding). For the ``mjpeg``
          format, use JPEG quality values between 1 and 100 (where higher
          values are higher quality). Quality 0 is special and seems to be
          a "reasonable quality" default.

        * *quantization* - Deprecated alias for *quality*.

        .. versionchanged:: 1.0
            The *resize* parameter was added, and ``'mjpeg'`` was added as a
            recording format

        .. versionchanged:: 1.3
            The *splitter_port* parameter was added

        .. versionchanged:: 1.5
            The *quantization* parameter was deprecated in favor of *quality*,
            and the *motion_output* parameter was added.

        .. versionchanged:: 1.11
            Support for buffer outputs was added.

        .. _H.264 level: https://en.wikipedia.org/wiki/H.264/MPEG-4_AVC#Levels
        """
        if 'quantization' in options:
            warnings.warn(
                PiCameraDeprecated(
                    'The quantization option is deprecated; please use '
                    'quality instead (same value)'))
        with self._encoders_lock:
            camera_port, output_port = self._get_ports(True, splitter_port)
            format = self._get_video_format(output, format)
            encoder = self._get_video_encoder(
                    camera_port, output_port, format, resize, **options)
            self._encoders[splitter_port] = encoder
        try:
            encoder.start(output, options.get('motion_output'))
        except Exception as e:
            encoder.close()
            with self._encoders_lock:
                del self._encoders[splitter_port]
            raise

    def split_recording(self, output, splitter_port=1, **options):
        """
        Continue the recording in the specified output; close existing output.

        When called, the video encoder will wait for the next appropriate
        split point (an inline SPS header), then will cease writing to the
        current output (and close it, if it was specified as a filename), and
        continue writing to the newly specified *output*.

        The *output* parameter is treated as in the :meth:`start_recording`
        method (it can be a string, a file-like object, or a writeable
        buffer object).

        The *motion_output* parameter can be used to redirect the output of the
        motion vector data in the same fashion as *output*. If *motion_output*
        is ``None`` (the default) then motion vector data will not be
        redirected and will continue being written to the output specified by
        the *motion_output* parameter given to :meth:`start_recording`.
        Alternatively, if you only wish to redirect motion vector data, you can
        set *output* to ``None`` and given a new value for *motion_output*.

        The *splitter_port* parameter specifies which port of the video
        splitter the encoder you wish to change outputs is attached to. This
        defaults to ``1`` and most users will have no need to specify anything
        different. Valid values are between ``0`` and ``3`` inclusive.

        Note that unlike :meth:`start_recording`, you cannot specify format or
        other options as these cannot be changed in the middle of recording.
        Only the new *output* (and *motion_output*) can be specified.
        Furthermore, the format of the recording is currently limited to H264,
        and *inline_headers* must be ``True`` when :meth:`start_recording` is
        called (this is the default).

        .. versionchanged:: 1.3
            The *splitter_port* parameter was added

        .. versionchanged:: 1.5
            The *motion_output* parameter was added

        .. versionchanged:: 1.11
            Support for buffer outputs was added.
        """
        try:
            with self._encoders_lock:
                encoder = self._encoders[splitter_port]
        except KeyError:
            raise PiCameraNotRecording(
                    'There is no recording in progress on '
                    'port %d' % splitter_port)
        else:
            encoder.split(output, options.get('motion_output'))

    def request_key_frame(self, splitter_port=1):
        """
        Request the encoder generate a key-frame as soon as possible.

        When called, the video encoder running on the specified *splitter_port*
        will attempt to produce a key-frame (full-image frame) as soon as
        possible. The *splitter_port* defaults to ``1``. Valid values are
        between ``0`` and ``3`` inclusive.

        .. note::

            This method is only meaningful for recordings encoded in the H264
            format as MJPEG produces full frames for every frame recorded.
            Furthermore, there's no guarantee that the *next* frame will be
            a key-frame; this is simply a request to produce one as soon as
            possible after the call.

        .. versionadded:: 1.11
        """
        try:
            with self._encoders_lock:
                encoder = self._encoders[splitter_port]
        except KeyError:
            raise PiCameraNotRecording(
                    'There is no recording in progress on '
                    'port %d' % splitter_port)
        else:
            encoder.request_key_frame()

    def wait_recording(self, timeout=0, splitter_port=1):
        """
        Wait on the video encoder for timeout seconds.

        It is recommended that this method is called while recording to check
        for exceptions. If an error occurs during recording (for example out of
        disk space) the recording will stop, but an exception will only be
        raised when the :meth:`wait_recording` or :meth:`stop_recording`
        methods are called.

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
            with self._encoders_lock:
                encoder = self._encoders[splitter_port]
        except KeyError:
            raise PiCameraNotRecording(
                    'There is no recording in progress on '
                    'port %d' % splitter_port)
        else:
            encoder.wait(timeout)

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
            with self._encoders_lock:
                encoder = self._encoders[splitter_port]
        except KeyError:
            raise PiCameraNotRecording(
                    'There is no recording in progress on '
                    'port %d' % splitter_port)
        else:
            try:
                self.wait_recording(0, splitter_port)
            finally:
                encoder.close()
                with self._encoders_lock:
                    del self._encoders[splitter_port]

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
        with self._encoders_lock:
            camera_port, output_port = self._get_ports(True, splitter_port)
            format = self._get_video_format('', format)
            encoder = self._get_video_encoder(
                    camera_port, output_port, format, resize, **options)
            self._encoders[splitter_port] = encoder
        try:
            start = True
            for output in outputs:
                if start:
                    start = False
                    encoder.start(output, options.get('motion_output'))
                else:
                    encoder.split(output)
                yield output
        finally:
            try:
                encoder.wait(0)
            finally:
                encoder.close()
                with self._encoders_lock:
                    del self._encoders[splitter_port]

    def capture(
            self, output, format=None, use_video_port=False, resize=None,
            splitter_port=0, bayer=False, **options):
        """
        Capture an image from the camera, storing it in *output*.

        If *output* is a string, it will be treated as a filename for a new
        file which the image will be written to. If *output* is not a string,
        but is an object with a ``write`` method, it is assumed to be a
        file-like object and the image data is appended to it (the
        implementation only assumes the object has a ``write`` method - no
        other methods are required but ``flush`` will be called at the end of
        capture if it is present). If *output* is not a string, and has no
        ``write`` method it is assumed to be a writeable object implementing
        the buffer protocol. In this case, the image data will be written
        directly to the underlying buffer (which must be large enough to accept
        the image data).

        If *format* is ``None`` (the default), the method will attempt to guess
        the required image format from the extension of *output* (if it's a
        string), or from the *name* attribute of *output* (if it has one). In
        the case that the format cannot be determined, a
        :exc:`PiCameraValueError` will be raised.

        If *format* is not ``None``, it must be a string specifying the format
        that you want the image output in. The format can be a MIME-type or
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
        *use_video_port* is ``False``. See :ref:`mmal` for more information
        about the video splitter.

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
          ranging from 1 to 100. Defaults to 85. Please note that JPEG quality
          is not a percentage and `definitions of quality`_ vary widely.

        * *restart* - Defines the restart interval for the JPEG encoder as a
          number of JPEG MCUs. The actual restart interval used will be a
          multiple of the number of MCUs per row in the resulting image.

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

        .. versionchanged:: 1.11
            Support for buffer outputs was added.

        .. _definitions of quality: http://photo.net/learn/jpeg/#qual
        """
        if format == 'raw':
            warnings.warn(
                PiCameraDeprecated(
                    'The "raw" format option is deprecated; specify the '
                    'required format directly instead ("yuv", "rgb", etc.)'))
        if use_video_port and bayer:
            raise PiCameraValueError(
                'bayer is only valid with still port captures')
        if 'burst' in options:
            raise PiCameraValueError(
                'burst is only valid with capture_sequence or capture_continuous')
        with self._encoders_lock:
            camera_port, output_port = self._get_ports(use_video_port, splitter_port)
            format = self._get_image_format(output, format)
            encoder = self._get_image_encoder(
                    camera_port, output_port, format, resize, **options)
            if use_video_port:
                self._encoders[splitter_port] = encoder
        try:
            if bayer:
                camera_port.params[mmal.MMAL_PARAMETER_ENABLE_RAW_CAPTURE] = True
            encoder.start(output)
            # Wait for the callback to set the event indicating the end of
            # image capture
            if not encoder.wait(self.CAPTURE_TIMEOUT):
                raise PiCameraRuntimeError(
                    'Timed out waiting for capture to end')
        finally:
            encoder.close()
            with self._encoders_lock:
                if use_video_port:
                    del self._encoders[splitter_port]

    def capture_sequence(
            self, outputs, format='jpeg', use_video_port=False, resize=None,
            splitter_port=0, burst=False, bayer=False, **options):
        """
        Capture a sequence of consecutive images from the camera.

        This method accepts a sequence or iterator of *outputs* each of which
        must either be a string specifying a filename for output, or a
        file-like object with a ``write`` method, or a writeable buffer object.
        For each item in the sequence or iterator of outputs, the camera
        captures a single image as fast as it can.

        The *format*, *use_video_port*, *splitter_port*, *resize*, and
        *options* parameters are the same as in :meth:`capture`, but *format*
        defaults to ``'jpeg'``.  The format is **not** derived from the
        filenames in *outputs* by this method.

        If *use_video_port* is ``False`` (the default), the *burst* parameter
        can be used to make still port captures faster.  Specifically, this
        prevents the preview from switching resolutions between captures which
        significantly speeds up consecutive captures from the still port. The
        downside is that this mode is currently has several bugs; the major
        issue is that if captures are performed too quickly some frames will
        come back severely underexposed. It is recommended that users avoid the
        *burst* parameter unless they absolutely require it and are prepared to
        work around such issues.

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

        .. versionchanged:: 1.11
            Support for buffer outputs was added.
        """
        if use_video_port:
            if burst:
                raise PiCameraValueError(
                    'burst is only valid with still port captures')
            if bayer:
                raise PiCameraValueError(
                    'bayer is only valid with still port captures')
        with self._encoders_lock:
            camera_port, output_port = self._get_ports(use_video_port, splitter_port)
            format = self._get_image_format('', format)
            if use_video_port:
                encoder = self._get_images_encoder(
                        camera_port, output_port, format, resize, **options)
                self._encoders[splitter_port] = encoder
            else:
                encoder = self._get_image_encoder(
                        camera_port, output_port, format, resize, **options)
        try:
            if use_video_port:
                encoder.start(outputs)
                encoder.wait()
            else:
                if burst:
                    camera_port.params[mmal.MMAL_PARAMETER_CAMERA_BURST_CAPTURE] = True
                try:
                    for output in outputs:
                        if bayer:
                            camera_port.params[mmal.MMAL_PARAMETER_ENABLE_RAW_CAPTURE] = True
                        encoder.start(output)
                        if not encoder.wait(self.CAPTURE_TIMEOUT):
                            raise PiCameraRuntimeError(
                                'Timed out waiting for capture to end')
                finally:
                    if burst:
                        camera_port.params[mmal.MMAL_PARAMETER_CAMERA_BURST_CAPTURE] = False
        finally:
            encoder.close()
            with self._encoders_lock:
                if use_video_port:
                    del self._encoders[splitter_port]

    def capture_continuous(
            self, output, format=None, use_video_port=False, resize=None,
            splitter_port=0, burst=False, bayer=False, **options):
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

        .. tabularcolumns:: |p{80mm}|p{40mm}|p{10mm}|

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

        If *output* is not a string, but has a ``write`` method, it is assumed
        to be a file-like object and each image is simply written to this
        object sequentially. In this case you will likely either want to write
        something to the object between the images to distinguish them, or
        clear the object between iterations. If *output* is not a string, and
        has no ``write`` method, it is assumed to be a writeable object
        supporting the buffer protocol; each image is simply written to the
        buffer sequentially.

        The *format*, *use_video_port*, *splitter_port*, *resize*, and
        *options* parameters are the same as in :meth:`capture`.

        If *use_video_port* is ``False`` (the default), the *burst* parameter
        can be used to make still port captures faster.  Specifically, this
        prevents the preview from switching resolutions between captures which
        significantly speeds up consecutive captures from the still port. The
        downside is that this mode is currently has several bugs; the major
        issue is that if captures are performed too quickly some frames will
        come back severely underexposed. It is recommended that users avoid the
        *burst* parameter unless they absolutely require it and are prepared to
        work around such issues.

        For example, to capture 60 images with a one second delay between them,
        writing the output to a series of JPEG files named image01.jpg,
        image02.jpg, etc. one could do the following::

            import time
            import picamera
            with picamera.PiCamera() as camera:
                camera.start_preview()
                try:
                    for i, filename in enumerate(
                            camera.capture_continuous('image{counter:02d}.jpg')):
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

        .. versionchanged:: 1.11
            Support for buffer outputs was added.
        """
        if use_video_port:
            if burst:
                raise PiCameraValueError(
                    'burst is only valid with still port captures')
            if bayer:
                raise PiCameraValueError(
                    'bayer is only valid with still port captures')
        with self._encoders_lock:
            camera_port, output_port = self._get_ports(use_video_port, splitter_port)
            format = self._get_image_format(output, format)
            encoder = self._get_image_encoder(
                    camera_port, output_port, format, resize, **options)
            if use_video_port:
                self._encoders[splitter_port] = encoder
        try:
            if burst:
                camera_port.params[mmal.MMAL_PARAMETER_CAMERA_BURST_CAPTURE] = True
            try:
                if isinstance(output, bytes):
                    # If we're fed a bytes string, assume it's UTF-8 encoded
                    # and convert it to Unicode. Technically this is wrong
                    # (file-systems use all sorts of encodings), but UTF-8 is a
                    # reasonable default and this keeps compatibility with
                    # Python 2 simple although it breaks the edge cases of
                    # non-UTF-8 encoded bytes strings with non-UTF-8 encoded
                    # file-systems
                    output = output.decode('utf-8')
                if isinstance(output, str):
                    counter = 1
                    while True:
                        filename = output.format(
                            counter=counter,
                            timestamp=datetime.datetime.now(),
                            )
                        if bayer:
                            camera_port.params[mmal.MMAL_PARAMETER_ENABLE_RAW_CAPTURE] = True
                        encoder.start(filename)
                        if not encoder.wait(self.CAPTURE_TIMEOUT):
                            raise PiCameraRuntimeError(
                                'Timed out waiting for capture to end')
                        yield filename
                        counter += 1
                else:
                    while True:
                        if bayer:
                            camera_port.params[mmal.MMAL_PARAMETER_ENABLE_RAW_CAPTURE] = True
                        encoder.start(output)
                        if not encoder.wait(self.CAPTURE_TIMEOUT):
                            raise PiCameraRuntimeError(
                                'Timed out waiting for capture to end')
                        yield output
            finally:
                if burst:
                    camera_port.params[mmal.MMAL_PARAMETER_CAMERA_BURST_CAPTURE] = False
        finally:
            encoder.close()
            with self._encoders_lock:
                if use_video_port:
                    del self._encoders[splitter_port]

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
        return any(
                isinstance(e, PiVideoEncoder) and e.active
                for e in self._encoders.values()
                )

    @property
    def previewing(self):
        """
        Returns ``True`` if the :meth:`start_preview` method has been called,
        and no :meth:`stop_preview` call has been made yet.

        .. deprecated:: 1.8
            Test whether :attr:`preview` is ``None`` instead.
        """
        warnings.warn(
            PiCameraDeprecated(
                'PiCamera.previewing is deprecated; test PiCamera.preview '
                'is not None instead'))
        return isinstance(self._preview, PiPreviewRenderer)

    @property
    def revision(self):
        """
        Returns a string representing the revision of the Pi's camera module.
        At the time of writing, the string returned is 'ov5647' for the V1
        module, and 'imx219' for the V2 module.
        """
        return self._revision

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
        GPIO.output(self._led_pin, bool(value))
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

        .. note::

            At present, the camera's LED cannot be controlled on the Pi 3
            (the GPIOs used to control the camera LED were re-routed to GPIO
            expander on the Pi 3).

        .. warning::

            There are circumstances in which the camera firmware may override
            an existing LED setting. For example, in the case that the firmware
            resets the camera (as can happen with a CSI-2 timeout), the LED may
            also be reset. If you wish to guarantee that the LED remain off at
            all times, you may prefer to use the ``disable_camera_led`` option
            in `config.txt`_ (this has the added advantage that sudo privileges
            and GPIO access are not required, at least for LED control).

        .. _config.txt: https://www.raspberrypi.org/documentation/configuration/config-txt.md
        """)

    def _get_raw_format(self):
        warnings.warn(
            PiCameraDeprecated(
                'PiCamera.raw_format is deprecated; use required format '
                'directly with capture methods instead'))
        return self._raw_format
    def _set_raw_format(self, value):
        warnings.warn(
            PiCameraDeprecated(
                'PiCamera.raw_format is deprecated; use required format '
                'directly with capture methods instead'))
        if value not in self.RAW_FORMATS:
            raise PiCameraValueError("Invalid raw format: %s" % value)
        self._raw_format = value
    raw_format = property(_get_raw_format, _set_raw_format, doc="""
        Retrieves or sets the raw format of the camera's ports.

        .. deprecated:: 1.0
            Please use ``'yuv'`` or ``'rgb'`` directly as a format in the
            various capture methods instead.
        """)

    def _get_timestamp(self):
        self._check_camera_open()
        return self._camera.control.params[mmal.MMAL_PARAMETER_SYSTEM_TIME]
    timestamp = property(_get_timestamp, doc="""
        Retrieves the system time according to the camera firmware.

        The camera's timestamp is a 64-bit integer representing the number of
        microseconds since the last system boot. When the camera's
        :attr:`clock_mode` is ``'raw'`` the values returned by this attribute
        are comparable to those from the :attr:`frame`
        :attr:`~PiVideoFrame.timestamp` attribute.
        """)

    def _get_frame(self):
        self._check_camera_open()
        for e in self._encoders.values():
            try:
                return e.frame
            except AttributeError:
                pass
        raise PiCameraRuntimeError(
            "Cannot query frame information when camera is not recording")
    frame = property(_get_frame, doc="""
        Retrieves information about the current frame recorded from the camera.

        When video recording is active (after a call to
        :meth:`start_recording`), this attribute will return a
        :class:`PiVideoFrame` tuple containing information about the current
        frame that the camera is recording.

        If multiple video recordings are currently in progress (after multiple
        calls to :meth:`start_recording` with different values for the
        ``splitter_port`` parameter), which encoder's frame information is
        returned is arbitrary. If you require information from a specific
        encoder, you will need to extract it from :attr:`_encoders` explicitly.

        Querying this property when the camera is not recording will result in
        an exception.

        .. note::

            There is a small window of time when querying this attribute will
            return ``None`` after calling :meth:`start_recording`. If this
            attribute returns ``None``, this means that the video encoder has
            been initialized, but the camera has not yet returned any frames.
        """)

    def _disable_camera(self):
        """
        An internal method for disabling the camera, e.g. for re-configuration.
        This disables the splitter and preview connections (if they exist).
        """
        self._splitter.connection.disable()
        self._preview.renderer.connection.disable()
        self._camera.disable()

    def _enable_camera(self):
        """
        An internal method for enabling the camera after re-configuration.
        This ensures the splitter configuration is consistent, then re-enables
        the camera along with the splitter and preview connections.
        """
        self._camera.enable()
        self._preview.renderer.connection.enable()
        self._splitter.connection.enable()

    def _configure_splitter(self):
        """
        Ensures all splitter output ports have a sensible format (I420) and
        buffer sizes.

        This method is used to ensure the splitter configuration is sane,
        typically after :meth:`_configure_camera` is called.
        """
        self._splitter.inputs[0].copy_from(self._camera.outputs[self.CAMERA_VIDEO_PORT])
        self._splitter.inputs[0].commit()

    def _control_callback(self, port, buf):
        try:
            if buf.command == mmal.MMAL_EVENT_ERROR:
                raise PiCameraRuntimeError(
                    "No data recevied from sensor. Check all connections, "
                    "including the SUNNY chip on the camera board")
            elif buf.command != mmal.MMAL_EVENT_PARAMETER_CHANGED:
                raise PiCameraRuntimeError(
                    "Received unexpected camera control callback event, 0x%08x" % buf[0].cmd)
        except Exception as exc:
            # Pass the exception to the main thread; next time
            # check_camera_open() is called this will get raised
            self._camera_exception = exc

    def _configure_camera(
            self, sensor_mode, framerate, resolution, clock_mode,
            old_sensor_mode=0):
        """
        An internal method for setting a new camera mode, framerate,
        resolution, and/or clock_mode.

        This method is used by the setters of the :attr:`resolution`,
        :attr:`framerate`, and :attr:`sensor_mode` properties. It assumes the
        camera is currently disabled. The *old_mode* and *new_mode* arguments
        are required to ensure correct operation on older firmwares
        (specifically that we don't try to set the sensor mode when both old
        and new modes are 0 or automatic).
        """
        old_cc = mmal.MMAL_PARAMETER_CAMERA_CONFIG_T.from_buffer_copy(self._camera_config)
        old_ports = [
            (port.framesize, port.framerate, port.params[mmal.MMAL_PARAMETER_FPS_RANGE])
            for port in self._camera.outputs
            ]
        if old_sensor_mode != 0 or sensor_mode != 0:
            self._camera.control.params[mmal.MMAL_PARAMETER_CAMERA_CUSTOM_SENSOR_CONFIG] = sensor_mode
        if not self._camera.control.enabled:
            # Initial setup
            self._camera.control.enable(self._control_callback)
            preview_resolution = resolution
        elif (
                self._camera.outputs[self.CAMERA_PREVIEW_PORT].framesize ==
                self._camera.outputs[self.CAMERA_VIDEO_PORT].framesize
                ):
            preview_resolution = resolution
        else:
            preview_resolution = self._camera.outputs[self.CAMERA_PREVIEW_PORT].framesize
        try:
            try:
                fps_low, fps_high = framerate
            except TypeError:
                fps_low = fps_high = framerate
            else:
                framerate = 0
            fps_range = mmal.MMAL_PARAMETER_FPS_RANGE_T(
                mmal.MMAL_PARAMETER_HEADER_T(
                    mmal.MMAL_PARAMETER_FPS_RANGE,
                    ct.sizeof(mmal.MMAL_PARAMETER_FPS_RANGE_T)
                ),
                fps_low=mo.to_rational(fps_low),
                fps_high=mo.to_rational(fps_high),
                )

            cc = self._camera_config
            cc.max_stills_w = resolution.width
            cc.max_stills_h = resolution.height
            cc.stills_yuv422 = 0
            cc.one_shot_stills = 1
            cc.max_preview_video_w = resolution.width
            cc.max_preview_video_h = resolution.height
            cc.num_preview_video_frames = max(3, fps_high // 10)
            cc.stills_capture_circular_buffer_height = 0
            cc.fast_preview_resume = 0
            cc.use_stc_timestamp = clock_mode
            self._camera.control.params[mmal.MMAL_PARAMETER_CAMERA_CONFIG] = cc

            # Clamp preview resolution to camera's resolution
            if (
                    preview_resolution.width > resolution.width or
                    preview_resolution.height > resolution.height
                    ):
                preview_resolution = resolution
            for port in self._camera.outputs:
                port.params[mmal.MMAL_PARAMETER_FPS_RANGE] = fps_range
                if port.index == self.CAMERA_PREVIEW_PORT:
                    port.framesize = preview_resolution
                else:
                    port.framesize = resolution
                port.framerate = framerate
                port.commit()
        except:
            # If anything goes wrong, restore original resolution and
            # framerate otherwise the camera can be left in unusual states
            # (camera config not matching ports, etc).
            self._camera.control.params[mmal.MMAL_PARAMETER_CAMERA_CONFIG] = old_cc
            self._camera_config = old_cc
            for port, (res, fps, fps_range) in zip(self._camera.outputs, old_ports):
                port.framesize = res
                port.framerate = fps
                port.params[mmal.MMAL_PARAMETER_FPS_RANGE] = fps_range
                port.commit()
            raise

    def _get_framerate(self):
        self._check_camera_open()
        port_num = (
            self.CAMERA_VIDEO_PORT
            if self._encoders else
            self.CAMERA_PREVIEW_PORT
            )
        return mo.PiCameraFraction(self._camera.outputs[port_num].framerate)
    def _set_framerate(self, value):
        self._check_camera_open()
        self._check_recording_stopped()
        value = mo.to_fraction(value, den_limit=256)
        if not (0 < value <= self.MAX_FRAMERATE):
            raise PiCameraValueError("Invalid framerate: %.2ffps" % value)
        sensor_mode = self.sensor_mode
        clock_mode = self.CLOCK_MODES[self.clock_mode]
        resolution = self.resolution
        self._disable_camera()
        self._configure_camera(
            sensor_mode=sensor_mode, framerate=value, resolution=resolution,
            clock_mode=clock_mode)
        self._configure_splitter()
        self._enable_camera()
    framerate = property(_get_framerate, _set_framerate, doc="""\
        Retrieves or sets the framerate at which video-port based image
        captures, video recordings, and previews will run.

        When queried, the :attr:`framerate` property returns the rate at which
        the camera's video and preview ports will operate as a
        :class:`~fractions.Fraction` instance (which can be easily converted to
        an :class:`int` or :class:`float`). If :attr:`framerate_range` has been
        set, then :attr:`framerate` will be 0 which indicates that a dynamic
        range of framerates is being used.

        .. note::

            For backwards compatibility, a derivative of the
            :class:`~fractions.Fraction` class is actually used which permits
            the value to be treated as a tuple of ``(numerator, denominator)``.

            Setting and retrieving framerate as a ``(numerator, denominator)``
            tuple is deprecated and will be removed in 2.0. Please use a
            :class:`~fractions.Fraction` instance instead (which is just as
            accurate and also permits direct use with math operators).

        When set, the property configures the camera so that the next call to
        recording and previewing methods will use the new framerate. Setting
        this property implicitly sets :attr:`framerate_range` so that the low
        and high values are equal to the new framerate. The framerate can be
        specified as an :ref:`int <typesnumeric>`, :ref:`float <typesnumeric>`,
        :class:`~fractions.Fraction`, or a ``(numerator, denominator)`` tuple.
        For example, the following definitions are all equivalent::

            from fractions import Fraction

            camera.framerate = 30
            camera.framerate = 30 / 1
            camera.framerate = Fraction(30, 1)
            camera.framerate = (30, 1) # deprecated

        The camera must not be closed, and no recording must be active when the
        property is set.

        .. note::

            This attribute, in combination with :attr:`resolution`, determines
            the mode that the camera operates in. The actual sensor framerate
            and resolution used by the camera is influenced, but not directly
            set, by this property. See :attr:`sensor_mode` for more
            information.

        The initial value of this property can be specified with the
        *framerate* parameter in the :class:`PiCamera` constructor, and will
        default to 30 if not specified.
        """)

    def _get_sensor_mode(self):
        self._check_camera_open()
        return self._camera.control.params[mmal.MMAL_PARAMETER_CAMERA_CUSTOM_SENSOR_CONFIG]
    def _set_sensor_mode(self, value):
        self._check_camera_open()
        self._check_recording_stopped()
        try:
            if not (0 <= value <= 7):
                raise PiCameraValueError(
                    "Invalid sensor mode: %d (valid range 0..7)" % value)
        except TypeError:
            raise PiCameraValueError("Invalid sensor mode: %s" % value)
        sensor_mode = self.sensor_mode
        clock_mode = self.CLOCK_MODES[self.clock_mode]
        resolution = self.resolution
        framerate = Fraction(self.framerate)
        if framerate == 0:
            framerate = self.framerate_range
        self._disable_camera()
        self._configure_camera(
            old_sensor_mode=sensor_mode, sensor_mode=value,
            framerate=framerate, resolution=resolution,
            clock_mode=clock_mode)
        self._configure_splitter()
        self._enable_camera()
    sensor_mode = property(_get_sensor_mode, _set_sensor_mode, doc="""\
        Retrieves or sets the input mode of the camera's sensor.

        This is an advanced property which can be used to control the camera's
        sensor mode. By default, mode 0 is used which allows the camera to
        automatically select an input mode based on the requested
        :attr:`resolution` and :attr:`framerate`. Valid values are currently
        between 0 and 7. The set of valid sensor modes (along with the
        heuristic used to select one automatically) are detailed in the
        :ref:`camera_modes` section of the documentation.

        .. note::

            At the time of writing, setting this property does nothing unless
            the camera has been initialized with a sensor mode other than 0.
            Furthermore, some mode transitions appear to require setting the
            property twice (in a row). This appears to be a firmware
            limitation.

        The initial value of this property can be specified with the
        *sensor_mode* parameter in the :class:`PiCamera` constructor, and will
        default to 0 if not specified.

        .. versionadded:: 1.9
        """)

    def _get_clock_mode(self):
        self._check_camera_open()
        return self._CLOCK_MODES_R[self._camera_config.use_stc_timestamp]
    def _set_clock_mode(self, value):
        self._check_camera_open()
        self._check_recording_stopped()
        try:
            clock_mode = self.CLOCK_MODES[value]
        except KeyError:
            raise PiCameraValueError("Invalid clock mode %s" % value)
        sensor_mode = self.sensor_mode
        framerate = Fraction(self.framerate)
        if framerate == 0:
            framerate = self.framerate_range
        resolution = self.resolution
        self._disable_camera()
        self._configure_camera(
            sensor_mode=sensor_mode, framerate=framerate,
            resolution=resolution, clock_mode=clock_mode)
        self._configure_splitter()
        self._enable_camera()
    clock_mode = property(_get_clock_mode, _set_clock_mode, doc="""\
        Retrieves or sets the mode of the camera's clock.

        This is an advanced property which can be used to control the nature of
        the frame timestamps available from the :attr:`frame` property. When
        this is "reset" (the default) each frame's timestamp will be relative
        to the start of the recording. When this is "raw", each frame's
        timestamp will be relative to the last initialization of the camera.

        The initial value of this property can be specified with the
        *clock_mode* parameter in the :class:`PiCamera` constructor, and will
        default to "reset" if not specified.

        .. versionadded:: 1.11
        """)

    def _get_resolution(self):
        self._check_camera_open()
        return mo.PiResolution(
            int(self._camera_config.max_stills_w),
            int(self._camera_config.max_stills_h)
            )
    def _set_resolution(self, value):
        self._check_camera_open()
        self._check_recording_stopped()
        value = mo.to_resolution(value)
        if not (
                (0 < value.width <= self.MAX_RESOLUTION.width) and
                (0 < value.height <= self.MAX_RESOLUTION.height)):
            raise PiCameraValueError(
                    "Invalid resolution requested: %r" % (value,))
        sensor_mode = self.sensor_mode
        clock_mode = self.CLOCK_MODES[self.clock_mode]
        framerate = Fraction(self.framerate)
        if framerate == 0:
            framerate = self.framerate_range
        self._disable_camera()
        self._configure_camera(
            sensor_mode=sensor_mode, framerate=framerate,
            resolution=value, clock_mode=clock_mode)
        self._configure_splitter()
        self._enable_camera()
    resolution = property(_get_resolution, _set_resolution, doc="""
        Retrieves or sets the resolution at which image captures, video
        recordings, and previews will be captured.

        When queried, the :attr:`resolution` property returns the resolution at
        which the camera will operate as a tuple of ``(width, height)``
        measured in pixels. This is the resolution that the :meth:`capture`
        method will produce images at, and the resolution that
        :meth:`start_recording` will produce videos at.

        When set, the property configures the camera so that the next call to
        these methods will use the new resolution.  The resolution can be
        specified as a ``(width, height)`` tuple, as a string formatted
        ``'WIDTHxHEIGHT'``, or as a string containing a commonly recognized
        `display resolution`_ name (e.g. "VGA", "HD", "1080p", etc). For
        example, the following definitions are all equivalent::

            camera.resolution = (1280, 720)
            camera.resolution = '1280x720'
            camera.resolution = '1280 x 720'
            camera.resolution = 'HD'
            camera.resolution = '720p'

        The camera must not be closed, and no recording must be active when the
        property is set.

        .. note::

            This attribute, in combination with :attr:`framerate`, determines
            the mode that the camera operates in. The actual sensor framerate
            and resolution used by the camera is influenced, but not directly
            set, by this property. See :attr:`sensor_mode` for more
            information.

        The initial value of this property can be specified with the
        *resolution* parameter in the :class:`PiCamera` constructor, and will
        default to the display's resolution or 1280x720 if the display has
        been disabled (with ``tvservice -o``).

        .. versionchanged:: 1.11
            Resolution permitted to be set as a string. Preview resolution
            added as separate property.

        .. _display resolution: https://en.wikipedia.org/wiki/Graphics_display_resolution
        """)

    def _get_framerate_range(self):
        self._check_camera_open()
        port_num = (
            self.CAMERA_VIDEO_PORT
            if self._encoders else
            self.CAMERA_PREVIEW_PORT
            )
        mp = self._camera.outputs[port_num].params[mmal.MMAL_PARAMETER_FPS_RANGE]
        return mo.PiFramerateRange(
            mo.to_fraction(mp.fps_low), mo.to_fraction(mp.fps_high))
    def _set_framerate_range(self, value):
        self._check_camera_open()
        self._check_recording_stopped()
        low, high = value
        low = mo.to_fraction(low, den_limit=256)
        high = mo.to_fraction(high, den_limit=256)
        if not (0 < low <= self.MAX_FRAMERATE):
            raise PiCameraValueError("Invalid low framerate: %.2ffps" % low)
        if not (0 < high <= self.MAX_FRAMERATE):
            raise PiCameraValueError("Invalid high framerate: %.2ffps" % high)
        if high < low:
            raise PiCameraValueError("framerate_range is backwards")
        sensor_mode = self.sensor_mode
        clock_mode = self.CLOCK_MODES[self.clock_mode]
        resolution = self.resolution
        self._disable_camera()
        self._configure_camera(
            sensor_mode=sensor_mode, framerate=(low, high),
            resolution=resolution, clock_mode=clock_mode)
        self._configure_splitter()
        self._enable_camera()
    framerate_range = property(_get_framerate_range, _set_framerate_range, doc="""\
        Retrieves or sets a range between which the camera's framerate is
        allowed to float.

        When queried, the :attr:`framerate_range` property returns a
        :func:`~collections.namedtuple` derivative with ``low`` and ``high``
        components (index 0 and 1 respectively) which specify the limits of the
        permitted framerate range.

        When set, the property configures the camera so that the next call to
        recording and previewing methods will use the new framerate range.
        Setting this property will implicitly set the :attr:`framerate`
        property to 0 (indicating that a dynamic range of framerates is in use
        by the camera).

        .. note::

            Use of this property prevents use of :attr:`framerate_delta` (there
            would be little point in making fractional adjustments to the
            framerate when the framerate itself is variable).

        The low and high framerates can be specified as :ref:`int
        <typesnumeric>`, :ref:`float <typesnumeric>`, or
        :class:`~fractions.Fraction` values. For example, the following
        definitions are all equivalent::

            from fractions import Fraction

            camera.framerate_range = (0.16666, 30)
            camera.framerate_range = (Fraction(1, 6), 30 / 1)
            camera.framerate_range = (Fraction(1, 6), Fraction(30, 1))

        The camera must not be closed, and no recording must be active when the
        property is set.

        .. note::

            This attribute, like :attr:`framerate`, determines the mode that
            the camera operates in. The actual sensor framerate and resolution
            used by the camera is influenced, but not directly set, by this
            property. See :attr:`sensor_mode` for more information.

        .. versionadded:: 1.13
        """)

    def _get_framerate_delta(self):
        self._check_camera_open()
        if self.framerate == 0:
            raise PiCameraValueError(
                'framerate_delta cannot be used with framerate_range')
        port_num = (
            self.CAMERA_VIDEO_PORT
            if self._encoders else
            self.CAMERA_PREVIEW_PORT
            )
        return self._camera.outputs[port_num].params[mmal.MMAL_PARAMETER_FRAME_RATE] - self.framerate
    def _set_framerate_delta(self, value):
        self._check_camera_open()
        if self.framerate == 0:
            raise PiCameraValueError(
                'framerate_delta cannot be used with framerate_range')
        value = mo.to_fraction(self.framerate + value, den_limit=256)
        self._camera.outputs[self.CAMERA_PREVIEW_PORT].params[mmal.MMAL_PARAMETER_FRAME_RATE] = value
        self._camera.outputs[self.CAMERA_VIDEO_PORT].params[mmal.MMAL_PARAMETER_FRAME_RATE] = value
    framerate_delta = property(_get_framerate_delta, _set_framerate_delta, doc="""\
        Retrieves or sets a fractional amount that is added to the camera's
        framerate for the purpose of minor framerate adjustments.

        When queried, the :attr:`framerate_delta` property returns the amount
        that the camera's :attr:`framerate` has been adjusted. This defaults
        to 0 (so the camera's framerate is the actual framerate used).

        When set, the property adjusts the camera's framerate on the fly. The
        property can be set while recordings or previews are in progress. Thus
        the framerate used by the camera is actually :attr:`framerate` +
        :attr:`framerate_delta`.

        .. note::

            Framerates deltas can be fractional with adjustments as small as
            1/256th of an fps possible (finer adjustments will be rounded).
            With an appropriately tuned PID controller, this can be used to
            achieve synchronization between the camera framerate and other
            devices.

        If the new framerate demands a mode switch (such as moving between a
        low framerate and a high framerate mode), currently active recordings
        may drop a frame. This should only happen when specifying quite large
        deltas, or when framerate is at the boundary of a sensor mode (e.g.
        49fps).

        The framerate delta can be specified as an :ref:`int <typesnumeric>`,
        :ref:`float <typesnumeric>`, :class:`~fractions.Fraction` or a
        ``(numerator, denominator)`` tuple. For example, the following
        definitions are all equivalent::

            from fractions import Fraction

            camera.framerate_delta = 0.5
            camera.framerate_delta = 1 / 2 # in python 3
            camera.framerate_delta = Fraction(1, 2)
            camera.framerate_delta = (1, 2) # deprecated

        .. note::

            This property is implicitly reset to 0 when :attr:`framerate` or
            :attr:`framerate_range` is set. When :attr:`framerate` is 0
            (indicating that :attr:`framerate_range` is set), this property
            cannot be used.  (there would be little point in making fractional
            adjustments to the framerate when the framerate itself is
            variable).

        .. versionadded:: 1.11
        """)

    def _get_still_stats(self):
        self._check_camera_open()
        return self._camera.control.params[mmal.MMAL_PARAMETER_CAPTURE_STATS_PASS]
    def _set_still_stats(self, value):
        self._check_camera_open()
        self._camera.control.params[mmal.MMAL_PARAMETER_CAPTURE_STATS_PASS] = value
    still_stats = property(_get_still_stats, _set_still_stats, doc="""\
        Retrieves or sets whether statistics will be calculated from still
        frames or the prior preview frame.

        When queried, the :attr:`still_stats` property returns a boolean value
        indicating when scene statistics will be calculated for still captures
        (that is, captures where the *use_video_port* parameter of
        :meth:`capture` is ``False``).  When this property is ``False`` (the
        default), statistics will be calculated from the preceding preview
        frame (this also applies when the preview is not visible). When `True`,
        statistics will be calculated from the captured image itself.

        When set, the propetry controls when scene statistics will be
        calculated for still captures. The property can be set while recordings
        or previews are in progress. The default value is ``False``.

        The advantages to calculating scene statistics from the captured image
        are that time between startup and capture is reduced as only the AGC
        (automatic gain control) has to converge. The downside is that
        processing time for captures increases and that white balance and gain
        won't necessarily match the preview.

        .. warning::

            Enabling the still statistics pass will `override fixed white
            balance`_ gains (set via :attr:`awb_gains` and :attr:`awb_mode`).

        .. _override fixed white balance: https://www.raspberrypi.org/forums/viewtopic.php?p=875772&sid=92fa4ea70d1fe24590a4cdfb4a10c489#p875772

        .. versionadded:: 1.9
        """)

    def _get_saturation(self):
        self._check_camera_open()
        return int(self._camera.control.params[mmal.MMAL_PARAMETER_SATURATION] * 100)
    def _set_saturation(self, value):
        self._check_camera_open()
        if not (-100 <= value <= 100):
            raise PiCameraValueError(
                "Invalid saturation value: %d (valid range -100..100)" % value)
        self._camera.control.params[mmal.MMAL_PARAMETER_SATURATION] = Fraction(value, 100)
    saturation = property(_get_saturation, _set_saturation, doc="""\
        Retrieves or sets the saturation setting of the camera.

        When queried, the :attr:`saturation` property returns the color
        saturation of the camera as an integer between -100 and 100. When set,
        the property adjusts the saturation of the camera. Saturation can be
        adjusted while previews or recordings are in progress. The default
        value is 0.
        """)

    def _get_sharpness(self):
        self._check_camera_open()
        return int(self._camera.control.params[mmal.MMAL_PARAMETER_SHARPNESS] * 100)
    def _set_sharpness(self, value):
        self._check_camera_open()
        if not (-100 <= value <= 100):
            raise PiCameraValueError(
                "Invalid sharpness value: %d (valid range -100..100)" % value)
        self._camera.control.params[mmal.MMAL_PARAMETER_SHARPNESS] = Fraction(value, 100)
    sharpness = property(_get_sharpness, _set_sharpness, doc="""\
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
        return int(self._camera.control.params[mmal.MMAL_PARAMETER_CONTRAST] * 100)
    def _set_contrast(self, value):
        self._check_camera_open()
        if not (-100 <= value <= 100):
            raise PiCameraValueError(
                "Invalid contrast value: %d (valid range -100..100)" % value)
        self._camera.control.params[mmal.MMAL_PARAMETER_CONTRAST] = Fraction(value, 100)
    contrast = property(_get_contrast, _set_contrast, doc="""\
        Retrieves or sets the contrast setting of the camera.

        When queried, the :attr:`contrast` property returns the contrast level
        of the camera as an integer between -100 and 100.  When set, the
        property adjusts the contrast of the camera. Contrast can be adjusted
        while previews or recordings are in progress. The default value is 0.
        """)

    def _get_brightness(self):
        self._check_camera_open()
        return int(self._camera.control.params[mmal.MMAL_PARAMETER_BRIGHTNESS] * 100)
    def _set_brightness(self, value):
        self._check_camera_open()
        if not (0 <= value <= 100):
            raise PiCameraValueError(
                "Invalid brightness value: %d (valid range 0..100)" % value)
        self._camera.control.params[mmal.MMAL_PARAMETER_BRIGHTNESS] = Fraction(value, 100)
    brightness = property(_get_brightness, _set_brightness, doc="""\
        Retrieves or sets the brightness setting of the camera.

        When queried, the :attr:`brightness` property returns the brightness
        level of the camera as an integer between 0 and 100.  When set, the
        property adjusts the brightness of the camera. Brightness can be
        adjusted while previews or recordings are in progress. The default
        value is 50.
        """)

    def _get_shutter_speed(self):
        self._check_camera_open()
        return int(self._camera.control.params[mmal.MMAL_PARAMETER_SHUTTER_SPEED])
    def _set_shutter_speed(self, value):
        self._check_camera_open()
        self._camera.control.params[mmal.MMAL_PARAMETER_SHUTTER_SPEED] = value
    shutter_speed = property(_get_shutter_speed, _set_shutter_speed, doc="""\
        Retrieves or sets the shutter speed of the camera in microseconds.

        When queried, the :attr:`shutter_speed` property returns the shutter
        speed of the camera in microseconds, or 0 which indicates that the
        speed will be automatically determined by the auto-exposure algorithm.
        Faster shutter times naturally require greater amounts of illumination
        and vice versa.

        When set, the property adjusts the shutter speed of the camera, which
        most obviously affects the illumination of subsequently captured
        images. Shutter speed can be adjusted while previews or recordings are
        running. The default value is 0 (auto).

        .. note::

            You can query the :attr:`exposure_speed` attribute to determine the
            actual shutter speed being used when this attribute is set to 0.
            Please note that this capability requires an up to date firmware
            (#692 or later).

        .. note::

            In later firmwares, this attribute is limited by the value of the
            :attr:`framerate` attribute. For example, if framerate is set to
            30fps, the shutter speed cannot be slower than 33,333µs (1/fps).
        """)

    def _get_exposure_speed(self):
        self._check_camera_open()
        return self._camera.control.params[mmal.MMAL_PARAMETER_CAMERA_SETTINGS].exposure
    exposure_speed = property(_get_exposure_speed, doc="""\
        Retrieves the current shutter speed of the camera.

        When queried, this property returns the shutter speed currently being
        used by the camera. If you have set :attr:`shutter_speed` to a non-zero
        value, then :attr:`exposure_speed` and :attr:`shutter_speed` should be
        equal. However, if :attr:`shutter_speed` is set to 0 (auto), then you
        can read the actual shutter speed being used from this attribute.  The
        value is returned as an integer representing a number of microseconds.
        This is a read-only property.

        .. versionadded:: 1.6
        """)

    def _get_analog_gain(self):
        self._check_camera_open()
        return mo.to_fraction(
            self._camera.control.params[mmal.MMAL_PARAMETER_CAMERA_SETTINGS].analog_gain)
    analog_gain = property(_get_analog_gain, doc="""\
        Retrieves the current analog gain of the camera.

        When queried, this property returns the analog gain currently being
        used by the camera. The value represents the analog gain of the sensor
        prior to digital conversion. The value is returned as a
        :class:`~fractions.Fraction` instance.

        .. versionadded:: 1.6
        """)

    def _get_digital_gain(self):
        self._check_camera_open()
        return mo.to_fraction(
            self._camera.control.params[mmal.MMAL_PARAMETER_CAMERA_SETTINGS].digital_gain)
    digital_gain = property(_get_digital_gain, doc="""\
        Retrieves the current digital gain of the camera.

        When queried, this property returns the digital gain currently being
        used by the camera. The value represents the digital gain the camera
        applies after conversion of the sensor's analog output. The value is
        returned as a :class:`~fractions.Fraction` instance.

        .. versionadded:: 1.6
        """)

    def _get_video_denoise(self):
        self._check_camera_open()
        return self._camera.control.params[mmal.MMAL_PARAMETER_VIDEO_DENOISE]
    def _set_video_denoise(self, value):
        self._check_camera_open()
        self._camera.control.params[mmal.MMAL_PARAMETER_VIDEO_DENOISE] = value
    video_denoise = property(_get_video_denoise, _set_video_denoise, doc="""\
        Retrieves or sets whether denoise will be applied to video recordings.

        When queried, the :attr:`video_denoise` property returns a boolean
        value indicating whether or not the camera software will apply a
        denoise algorithm to video recordings.

        When set, the property activates or deactivates the denoise algorithm
        for video recordings. The property can be set while recordings or
        previews are in progress. The default value is ``True``.

        .. versionadded:: 1.7
        """)

    def _get_image_denoise(self):
        self._check_camera_open()
        return self._camera.control.params[mmal.MMAL_PARAMETER_STILLS_DENOISE]
    def _set_image_denoise(self, value):
        self._check_camera_open()
        self._camera.control.params[mmal.MMAL_PARAMETER_STILLS_DENOISE] = value
    image_denoise = property(_get_image_denoise, _set_image_denoise, doc="""\
        Retrieves or sets whether denoise will be applied to image captures.

        When queried, the :attr:`image_denoise` property returns a boolean
        value indicating whether or not the camera software will apply a
        denoise algorithm to image captures.

        When set, the property activates or deactivates the denoise algorithm
        for image captures. The property can be set while recordings or
        previews are in progress. The default value is ``True``.

        .. versionadded:: 1.7
        """)

    def _get_drc_strength(self):
        self._check_camera_open()
        return self._DRC_STRENGTHS_R[
            self._camera.control.params[mmal.MMAL_PARAMETER_DYNAMIC_RANGE_COMPRESSION].strength
            ]
    def _set_drc_strength(self, value):
        self._check_camera_open()
        try:
            mp = self._camera.control.params[mmal.MMAL_PARAMETER_DYNAMIC_RANGE_COMPRESSION]
            mp.strength = self.DRC_STRENGTHS[value]
        except KeyError:
            raise PiCameraValueError(
                "Invalid dynamic range compression strength: %s" % value)
        self._camera.control.params[mmal.MMAL_PARAMETER_DYNAMIC_RANGE_COMPRESSION] = mp
    drc_strength = property(_get_drc_strength, _set_drc_strength, doc="""\
        Retrieves or sets the dynamic range compression strength of the camera.

        When queried, the :attr:`drc_strength` property returns a string
        indicating the amount of `dynamic range compression`_ the camera
        applies to images.

        When set, the attributes adjusts the strength of the dynamic range
        compression applied to the camera's output. Valid values are given
        in the list below:

        {values}

        The default value is ``'off'``. All possible values for the attribute
        can be obtained from the ``PiCamera.DRC_STRENGTHS`` attribute.

        .. warning::

            Enabling DRC will `override fixed white balance`_ gains (set via
            :attr:`awb_gains` and :attr:`awb_mode`).

        .. _dynamic range compression: https://en.wikipedia.org/wiki/Gain_compression
        .. _override fixed white balance: https://www.raspberrypi.org/forums/viewtopic.php?p=875772&sid=92fa4ea70d1fe24590a4cdfb4a10c489#p875772

        .. versionadded:: 1.6
        """.format(values=docstring_values(DRC_STRENGTHS)))

    def _get_ISO(self):
        warnings.warn(
            PiCameraDeprecated(
                'PiCamera.ISO is deprecated; use PiCamera.iso instead'))
        return self.iso
    def _set_ISO(self, value):
        warnings.warn(
            PiCameraDeprecated(
                'PiCamera.ISO is deprecated; use PiCamera.iso instead'))
        self.iso = value
    ISO = property(_get_ISO, _set_ISO, doc="""
        Retrieves or sets the apparent ISO setting of the camera.

        .. deprecated:: 1.8
            Please use the :attr:`iso` attribute instead.
        """)

    def _get_iso(self):
        self._check_camera_open()
        return self._camera.control.params[mmal.MMAL_PARAMETER_ISO]
    def _set_iso(self, value):
        self._check_camera_open()
        try:
            if not (0 <= value <= 1600):
                raise PiCameraValueError(
                    "Invalid iso value: %d (valid range 0..800)" % value)
        except TypeError:
            raise PiCameraValueError("Invalid iso value: %s" % value)
        self._camera.control.params[mmal.MMAL_PARAMETER_ISO] = value
    iso = property(_get_iso, _set_iso, doc="""\
        Retrieves or sets the apparent ISO setting of the camera.

        When queried, the :attr:`iso` property returns the ISO setting of the
        camera, a value which represents the `sensitivity of the camera to
        light`_. Lower values (e.g. 100) imply less sensitivity than higher
        values (e.g. 400 or 800). Lower sensitivities tend to produce less
        "noisy" (smoother) images, but operate poorly in low light conditions.

        When set, the property adjusts the sensitivity of the camera (by
        adjusting the :attr:`analog_gain` and :attr:`digital_gain`). Valid
        values are between 0 (auto) and 1600. The actual value used when iso is
        explicitly set will be one of the following values (whichever is
        closest): 100, 200, 320, 400, 500, 640, 800.

        On the V1 camera module, non-zero ISO values attempt to fix overall
        gain at various levels. For example, ISO 100 attempts to provide an
        overall gain of 1.0, ISO 200 attempts to provide overall gain of 2.0,
        etc. The algorithm prefers analog gain over digital gain to reduce
        noise.

        On the V2 camera module, ISO 100 attempts to produce overall gain of
        ~1.84, and ISO 800 attempts to produce overall gain of ~14.72 (the V2
        camera module was calibrated against the `ISO film speed`_ standard).

        The attribute can be adjusted while previews or recordings are in
        progress. The default value is 0 which means automatically determine a
        value according to image-taking conditions.

        .. note::

            Some users on the Pi camera forum have noted that higher ISO values
            than 800 (specifically up to 1600) can be achieved in certain
            conditions with :attr:`exposure_mode` set to ``'sports'`` and
            :attr:`iso` set to 0.  It doesn't appear to be possible to manually
            request an ISO setting higher than 800, but the picamera library
            will permit settings up to 1600 in case the underlying firmware
            permits such settings in particular circumstances.

        .. note::

            Certain :attr:`exposure_mode` values override the ISO setting. For
            example, ``'off'`` fixes :attr:`analog_gain` and
            :attr:`digital_gain` entirely, preventing this property from
            adjusting them when set.

        .. _sensitivity of the camera to light: https://en.wikipedia.org/wiki/Film_speed#Digital
        .. _ISO film speed: https://en.wikipedia.org/wiki/Film_speed#Current_system:_ISO
        """)

    def _get_meter_mode(self):
        self._check_camera_open()
        return self._METER_MODES_R[
            self._camera.control.params[mmal.MMAL_PARAMETER_EXP_METERING_MODE].value
            ]
    def _set_meter_mode(self, value):
        self._check_camera_open()
        try:
            mp = self._camera.control.params[mmal.MMAL_PARAMETER_EXP_METERING_MODE]
            mp.value = self.METER_MODES[value]
        except KeyError:
            raise PiCameraValueError("Invalid metering mode: %s" % value)
        self._camera.control.params[mmal.MMAL_PARAMETER_EXP_METERING_MODE] = mp
    meter_mode = property(_get_meter_mode, _set_meter_mode, doc="""\
        Retrieves or sets the metering mode of the camera.

        When queried, the :attr:`meter_mode` property returns the method by
        which the camera `determines the exposure`_ as one of the following
        strings:

        {values}

        When set, the property adjusts the camera's metering mode. All modes
        set up two regions: a center region, and an outer region. The major
        `difference between each mode`_ is the size of the center region. The
        ``'backlit'`` mode has the largest central region (30% of the width),
        while ``'spot'`` has the smallest (10% of the width).

        The property can be set while recordings or previews are in progress.
        The default value is ``'average'``. All possible values for the
        attribute can be obtained from the ``PiCamera.METER_MODES`` attribute.

        .. _determines the exposure: https://en.wikipedia.org/wiki/Metering_mode
        .. _difference between each mode: https://www.raspberrypi.org/forums/viewtopic.php?p=565644#p565644
        """.format(values=docstring_values(METER_MODES)))

    def _get_video_stabilization(self):
        self._check_camera_open()
        return self._camera.control.params[mmal.MMAL_PARAMETER_VIDEO_STABILISATION]
    def _set_video_stabilization(self, value):
        self._check_camera_open()
        self._camera.control.params[mmal.MMAL_PARAMETER_VIDEO_STABILISATION] = value
    video_stabilization = property(
        _get_video_stabilization, _set_video_stabilization, doc="""\
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

        .. _vertical and horizontal motion: https://www.raspberrypi.org/forums/viewtopic.php?p=342667&sid=ec7d95e887ab74a90ffaab87888c48cd#p342667
        """)

    def _get_exposure_compensation(self):
        self._check_camera_open()
        return self._camera.control.params[mmal.MMAL_PARAMETER_EXPOSURE_COMP]
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
        self._camera.control.params[mmal.MMAL_PARAMETER_EXPOSURE_COMP] = value
    exposure_compensation = property(
        _get_exposure_compensation, _set_exposure_compensation, doc="""\
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
        return self._EXPOSURE_MODES_R[
            self._camera.control.params[mmal.MMAL_PARAMETER_EXPOSURE_MODE].value
            ]
    def _set_exposure_mode(self, value):
        self._check_camera_open()
        try:
            mp = self._camera.control.params[mmal.MMAL_PARAMETER_EXPOSURE_MODE]
            mp.value = self.EXPOSURE_MODES[value]
        except KeyError:
            raise PiCameraValueError("Invalid exposure mode: %s" % value)
        self._camera.control.params[mmal.MMAL_PARAMETER_EXPOSURE_MODE] = mp
    exposure_mode = property(_get_exposure_mode, _set_exposure_mode, doc="""\
        Retrieves or sets the exposure mode of the camera.

        When queried, the :attr:`exposure_mode` property returns a string
        representing the exposure setting of the camera. The possible values
        can be obtained from the ``PiCamera.EXPOSURE_MODES`` attribute, and
        are as follows:

        {values}

        When set, the property adjusts the camera's exposure mode.  The
        property can be set while recordings or previews are in progress. The
        default value is ``'auto'``.

        .. note::

            Exposure mode ``'off'`` is special: this disables the camera's
            automatic gain control, fixing the values of :attr:`digital_gain`
            and :attr:`analog_gain`.

            Please note that these properties are not directly settable
            (although they can be influenced by setting :attr:`iso` *prior* to
            fixing the gains), and default to low values when the camera is
            first initialized. Therefore it is important to let them settle on
            higher values before disabling automatic gain control otherwise all
            frames captured will appear black.
        """.format(values=docstring_values(EXPOSURE_MODES)))

    def _get_flash_mode(self):
        self._check_camera_open()
        return self._FLASH_MODES_R[
            self._camera.control.params[mmal.MMAL_PARAMETER_FLASH].value
            ]
    def _set_flash_mode(self, value):
        self._check_camera_open()
        try:
            mp = self._camera.control.params[mmal.MMAL_PARAMETER_FLASH]
            mp.value = self.FLASH_MODES[value]
        except KeyError:
            raise PiCameraValueError("Invalid flash mode: %s" % value)
        self._camera.control.params[mmal.MMAL_PARAMETER_FLASH] = mp
    flash_mode = property(_get_flash_mode, _set_flash_mode, doc="""\
        Retrieves or sets the flash mode of the camera.

        When queried, the :attr:`flash_mode` property returns a string
        representing the flash setting of the camera. The possible values can
        be obtained from the ``PiCamera.FLASH_MODES`` attribute, and are as
        follows:

        {values}

        When set, the property adjusts the camera's flash mode.  The property
        can be set while recordings or previews are in progress.  The default
        value is ``'off'``.

        .. note::

            You must define which GPIO pins the camera is to use for flash and
            privacy indicators. This is done within the `Device Tree
            configuration`_ which is considered an advanced topic.
            Specifically, you need to define pins ``FLASH_0_ENABLE`` and
            optionally ``FLASH_0_INDICATOR`` (for the privacy indicator). More
            information can be found in this :ref:`recipe
            <flash_configuration>`.

        .. _Device Tree configuration: https://www.raspberrypi.org/documentation/configuration/pin-configuration.md

        .. versionadded:: 1.10
        """.format(values=docstring_values(FLASH_MODES)))

    def _get_awb_mode(self):
        self._check_camera_open()
        return self._AWB_MODES_R[
            self._camera.control.params[mmal.MMAL_PARAMETER_AWB_MODE].value
            ]
    def _set_awb_mode(self, value):
        self._check_camera_open()
        try:
            mp = self._camera.control.params[mmal.MMAL_PARAMETER_AWB_MODE]
            mp.value = self.AWB_MODES[value]
        except KeyError:
            raise PiCameraValueError("Invalid auto-white-balance mode: %s" % value)
        self._camera.control.params[mmal.MMAL_PARAMETER_AWB_MODE] = mp
    awb_mode = property(_get_awb_mode, _set_awb_mode, doc="""\
        Retrieves or sets the auto-white-balance mode of the camera.

        When queried, the :attr:`awb_mode` property returns a string
        representing the auto white balance setting of the camera. The possible
        values can be obtained from the ``PiCamera.AWB_MODES`` attribute, and
        are as follows:

        {values}

        When set, the property adjusts the camera's auto-white-balance mode.
        The property can be set while recordings or previews are in progress.
        The default value is ``'auto'``.

        .. note::

            AWB mode ``'off'`` is special: this disables the camera's automatic
            white balance permitting manual control of the white balance via
            the :attr:`awb_gains` property. However, even with AWB disabled,
            some attributes (specifically :attr:`still_stats` and
            :attr:`drc_strength`) can cause AWB re-calculations.
        """.format(values=docstring_values(AWB_MODES)))

    def _get_awb_gains(self):
        self._check_camera_open()
        mp = self._camera.control.params[mmal.MMAL_PARAMETER_CAMERA_SETTINGS]
        return (
            mo.to_fraction(mp.awb_red_gain),
            mo.to_fraction(mp.awb_blue_gain),
            )
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
            mo.to_rational(red_gain),
            mo.to_rational(blue_gain),
            )
        self._camera.control.params[mmal.MMAL_PARAMETER_CUSTOM_AWB_GAINS] = mp
    awb_gains = property(_get_awb_gains, _set_awb_gains, doc="""\
        Gets or sets the auto-white-balance gains of the camera.

        When queried, this attribute returns a tuple of values representing
        the `(red, blue)` balance of the camera. The `red` and `blue` values
        are returned :class:`~fractions.Fraction` instances. The values will
        be between 0.0 and 8.0.

        When set, this attribute adjusts the camera's auto-white-balance gains.
        The property can be specified as a single value in which case both red
        and blue gains will be adjusted equally, or as a `(red, blue)` tuple.
        Values can be specified as an :ref:`int <typesnumeric>`, :ref:`float
        <typesnumeric>` or :class:`~fractions.Fraction` and each gain must be
        between 0.0 and 8.0.  Typical values for the gains are between 0.9 and
        1.9.  The property can be set while recordings or previews are in
        progress.

        .. note::

            This attribute only has an effect when :attr:`awb_mode` is set to
            ``'off'``. Also note that even with AWB disabled, some attributes
            (specifically :attr:`still_stats` and :attr:`drc_strength`) can
            cause AWB re-calculations.

        .. versionchanged:: 1.6
            Prior to version 1.6, this attribute was write-only.
        """)

    def _get_image_effect(self):
        self._check_camera_open()
        return self._IMAGE_EFFECTS_R[
            self._camera.control.params[mmal.MMAL_PARAMETER_IMAGE_EFFECT].value
            ]
    def _set_image_effect(self, value):
        self._check_camera_open()
        try:
            mp = self._camera.control.params[mmal.MMAL_PARAMETER_IMAGE_EFFECT]
            mp.value = self.IMAGE_EFFECTS[value]
            self._image_effect_params = None
        except KeyError:
            raise PiCameraValueError("Invalid image effect: %s" % value)
        self._camera.control.params[mmal.MMAL_PARAMETER_IMAGE_EFFECT] = mp
    image_effect = property(_get_image_effect, _set_image_effect, doc="""\
        Retrieves or sets the current image effect applied by the camera.

        When queried, the :attr:`image_effect` property returns a string
        representing the effect the camera will apply to captured video. The
        possible values can be obtained from the ``PiCamera.IMAGE_EFFECTS``
        attribute, and are as follows:

        {values}

        When set, the property changes the effect applied by the camera.  The
        property can be set while recordings or previews are in progress, but
        only certain effects work while recording video (notably ``'negative'``
        and ``'solarize'``). The default value is ``'none'``.
        """.format(values=docstring_values(IMAGE_EFFECTS)))

    def _get_image_effect_params(self):
        self._check_camera_open()
        return self._image_effect_params
    def _set_image_effect_params(self, value):
        self._check_camera_open()
        to_int = lambda x: int(x)
        to_byte = lambda x: max(0, min(255, int(x)))
        to_bool = lambda x: (0, 1)[bool(x)]
        to_8dot8 = lambda x: int(x * 256)
        valid_transforms = {
            'solarize': [
                (to_bool, to_byte, to_byte, to_byte, to_byte),
                (to_byte, to_byte, to_byte, to_byte),
                (to_bool,),
                ],
            'colorpoint': [
                (lambda x: max(0, min(3, int(x))),),
                ],
            'colorbalance': [
                (to_8dot8, to_8dot8, to_8dot8, to_8dot8, to_int, to_int),
                (to_8dot8, to_8dot8, to_8dot8, to_8dot8),
                (to_8dot8, to_8dot8, to_8dot8),
                ],
            'colorswap': [
                (to_bool,),
                ],
            'posterise': [
                (lambda x: max(2, min(31, int(x))),),
                ],
            'blur': [
                (lambda x: max(1, min(2, int(x))),),
                ],
            'film': [
                (to_byte, to_byte, to_byte),
                ],
            'watercolor': [
                (),
                (to_byte, to_byte),
                ]
            }
        # Ensure params is a tuple
        try:
            params = tuple(i for i in value)
        except TypeError:
            params = (value,)
        # Find the parameter combination for the current effect
        effect = self.image_effect
        param_transforms = [
            transforms for transforms in valid_transforms.get(effect, [])
            if len(transforms) == len(params)
            ]
        if not param_transforms:
            raise PiCameraValueError(
                'invalid set of parameters for effect "%s"' % effect)
        param_transforms = param_transforms[0]
        params = tuple(
            transform(p)
            for (transform, p) in zip(param_transforms, params)
            )
        mp = mmal.MMAL_PARAMETER_IMAGEFX_PARAMETERS_T(
            mmal.MMAL_PARAMETER_HEADER_T(
                mmal.MMAL_PARAMETER_IMAGE_EFFECT_PARAMETERS,
                ct.sizeof(mmal.MMAL_PARAMETER_IMAGEFX_PARAMETERS_T)
                ),
            effect=self.IMAGE_EFFECTS[effect],
            num_effect_params=len(params),
            effect_parameter=params,
            )
        self._camera.control.params[mmal.MMAL_PARAMETER_IMAGE_EFFECT_PARAMETERS] = mp
        self._image_effect_params = value
    image_effect_params = property(
            _get_image_effect_params, _set_image_effect_params, doc="""\
        Retrieves or sets the parameters for the current :attr:`effect
        <image_effect>`.

        When queried, the :attr:`image_effect_params` property either returns
        ``None`` (for effects which have no configurable parameters, or if no
        parameters have been configured), or a tuple of numeric values up to
        six elements long.

        When set, the property changes the parameters of the current
        :attr:`effect <image_effect>` as a sequence of numbers, or a single
        number. Attempting to set parameters on an effect which does not
        support parameters, or providing an incompatible set of parameters for
        an effect will raise a :exc:`PiCameraValueError` exception.

        The effects which have parameters, and what combinations those
        parameters can take is as follows:

        .. tabularcolumns:: |p{30mm}|p{25mm}|p{75mm}|

        +--------------------+----------------+-----------------------------------------+
        | Effect             | Parameters     | Description                             |
        +====================+================+=========================================+
        | ``'solarize'``     | *yuv*,         | *yuv* controls whether data is          |
        |                    | *x0*, *y1*,    | processed as RGB (0) or YUV(1). Input   |
        |                    | *y2*, *y3*     | values from 0 to *x0* - 1 are remapped  |
        |                    |                | linearly onto the range 0 to *y0*.      |
        |                    |                | Values from *x0* to 255 are remapped    |
        |                    |                | linearly onto the range *y1* to *y2*.   |
        |                    +----------------+-----------------------------------------+
        |                    | *x0*, *y0*,    | Same as above, but *yuv* defaults to    |
        |                    | *y1*, *y2*     | 0 (process as RGB).                     |
        |                    +----------------+-----------------------------------------+
        |                    | *yuv*          | Same as above, but *x0*, *y0*, *y1*,    |
        |                    |                | *y2* default to 128, 128, 128, 0        |
        |                    |                | respectively.                           |
        +--------------------+----------------+-----------------------------------------+
        | ``'colorpoint'``   | *quadrant*     | *quadrant* specifies which quadrant     |
        |                    |                | of the U/V space to retain chroma       |
        |                    |                | from: 0=green, 1=red/yellow, 2=blue,    |
        |                    |                | 3=purple. There is no default; this     |
        |                    |                | effect does nothing until parameters    |
        |                    |                | are set.                                |
        +--------------------+----------------+-----------------------------------------+
        | ``'colorbalance'`` | *lens*,        | *lens* specifies the lens shading       |
        |                    | *r*, *g*, *b*, | strength (0.0 to 256.0, where 0.0       |
        |                    | *u*, *v*       | indicates lens shading has no effect).  |
        |                    |                | *r*, *g*, *b* are multipliers for their |
        |                    |                | respective color channels (0.0 to       |
        |                    |                | 256.0). *u* and *v* are offsets added   |
        |                    |                | to the U/V plane (0 to 255).            |
        |                    +----------------+-----------------------------------------+
        |                    | *lens*,        | Same as above but *u* are defaulted     |
        |                    | *r*, *g*, *b*  | to 0.                                   |
        |                    +----------------+-----------------------------------------+
        |                    | *lens*,        | Same as above but *g* also defaults to  |
        |                    | *r*, *b*       | to 1.0.                                 |
        +--------------------+----------------+-----------------------------------------+
        | ``'colorswap'``    | *dir*          | If *dir* is 0, swap RGB to BGR. If      |
        |                    |                | *dir* is 1, swap RGB to BRG.            |
        +--------------------+----------------+-----------------------------------------+
        | ``'posterise'``    | *steps*        | Control the quantization steps for the  |
        |                    |                | image. Valid values are 2 to 32, and    |
        |                    |                | the default is 4.                       |
        +--------------------+----------------+-----------------------------------------+
        | ``'blur'``         | *size*         | Specifies the size of the kernel. Valid |
        |                    |                | values are 1 or 2.                      |
        +--------------------+----------------+-----------------------------------------+
        | ``'film'``         | *strength*,    | *strength* specifies the strength of    |
        |                    | *u*, *v*       | effect. *u* and *v* are offsets added   |
        |                    |                | to the U/V plane (0 to 255).            |
        +--------------------+----------------+-----------------------------------------+
        | ``'watercolor'``   | *u*, *v*       | *u* and *v* specify offsets to add to   |
        |                    |                | the U/V plane (0 to 255).               |
        |                    +----------------+-----------------------------------------+
        |                    |                | No parameters indicates no U/V effect.  |
        +--------------------+----------------+-----------------------------------------+

        .. versionadded:: 1.8
        """)

    def _get_color_effects(self):
        self._check_camera_open()
        mp = self._camera.control.params[mmal.MMAL_PARAMETER_COLOUR_EFFECT]
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
        self._camera.control.params[mmal.MMAL_PARAMETER_COLOUR_EFFECT] = mp
    color_effects = property(_get_color_effects, _set_color_effects, doc="""\
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
        return self._camera.outputs[0].params[mmal.MMAL_PARAMETER_ROTATION]
    def _set_rotation(self, value):
        self._check_camera_open()
        try:
            value = ((int(value) % 360) // 90) * 90
        except ValueError:
            raise PiCameraValueError("Invalid rotation angle: %s" % value)
        for port in self._camera.outputs:
            port.params[mmal.MMAL_PARAMETER_ROTATION] = value
    rotation = property(_get_rotation, _set_rotation, doc="""\
        Retrieves or sets the current rotation of the camera's image.

        When queried, the :attr:`rotation` property returns the rotation
        applied to the image. Valid values are 0, 90, 180, and 270.

        When set, the property changes the rotation applied to the camera's
        input. The property can be set while recordings or previews are in
        progress. The default value is ``0``.
        """)

    def _get_vflip(self):
        self._check_camera_open()
        return self._camera.outputs[0].params[mmal.MMAL_PARAMETER_MIRROR] in (
            mmal.MMAL_PARAM_MIRROR_VERTICAL, mmal.MMAL_PARAM_MIRROR_BOTH)
    def _set_vflip(self, value):
        self._check_camera_open()
        value = {
            (False, False): mmal.MMAL_PARAM_MIRROR_NONE,
            (True,  False): mmal.MMAL_PARAM_MIRROR_VERTICAL,
            (False, True):  mmal.MMAL_PARAM_MIRROR_HORIZONTAL,
            (True,  True):  mmal.MMAL_PARAM_MIRROR_BOTH,
            }[(bool(value), self.hflip)]
        for port in self._camera.outputs:
            port.params[mmal.MMAL_PARAMETER_MIRROR] = value
    vflip = property(_get_vflip, _set_vflip, doc="""\
        Retrieves or sets whether the camera's output is vertically flipped.

        When queried, the :attr:`vflip` property returns a boolean indicating
        whether or not the camera's output is vertically flipped. The property
        can be set while recordings or previews are in progress. The default
        value is ``False``.
        """)

    def _get_hflip(self):
        self._check_camera_open()
        return self._camera.outputs[0].params[mmal.MMAL_PARAMETER_MIRROR] in (
            mmal.MMAL_PARAM_MIRROR_HORIZONTAL, mmal.MMAL_PARAM_MIRROR_BOTH)
    def _set_hflip(self, value):
        self._check_camera_open()
        value = {
            (False, False): mmal.MMAL_PARAM_MIRROR_NONE,
            (True,  False): mmal.MMAL_PARAM_MIRROR_VERTICAL,
            (False, True):  mmal.MMAL_PARAM_MIRROR_HORIZONTAL,
            (True,  True):  mmal.MMAL_PARAM_MIRROR_BOTH,
            }[(self.vflip, bool(value))]
        for port in self._camera.outputs:
            port.params[mmal.MMAL_PARAMETER_MIRROR] = value
    hflip = property(_get_hflip, _set_hflip, doc="""\
        Retrieves or sets whether the camera's output is horizontally flipped.

        When queried, the :attr:`hflip` property returns a boolean indicating
        whether or not the camera's output is horizontally flipped. The
        property can be set while recordings or previews are in progress. The
        default value is ``False``.
        """)

    def _get_zoom(self):
        self._check_camera_open()
        mp = self._camera.control.params[mmal.MMAL_PARAMETER_INPUT_CROP]
        return (
            mp.rect.x / 65535.0,
            mp.rect.y / 65535.0,
            mp.rect.width / 65535.0,
            mp.rect.height / 65535.0,
            )
    def _set_zoom(self, value):
        self._check_camera_open()
        try:
            x, y, w, h = value
        except (TypeError, ValueError) as e:
            raise PiCameraValueError(
                "Invalid zoom rectangle (x, y, w, h) tuple: %s" % value)
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
        self._camera.control.params[mmal.MMAL_PARAMETER_INPUT_CROP] = mp
    zoom = property(_get_zoom, _set_zoom, doc="""\
        Retrieves or sets the zoom applied to the camera's input.

        When queried, the :attr:`zoom` property returns a ``(x, y, w, h)``
        tuple of floating point values ranging from 0.0 to 1.0, indicating the
        proportion of the image to include in the output (this is also known as
        the "Region of Interest" or ROI). The default value is ``(0.0, 0.0,
        1.0, 1.0)`` which indicates that everything should be included. The
        property can be set while recordings or previews are in progress.
        """)

    def _get_crop(self):
        warnings.warn(
            PiCameraDeprecated(
                'PiCamera.crop is deprecated; use PiCamera.zoom instead'))
        return self.zoom
    def _set_crop(self, value):
        warnings.warn(
            PiCameraDeprecated(
                'PiCamera.crop is deprecated; use PiCamera.zoom instead'))
        self.zoom = value
    crop = property(_get_crop, _set_crop, doc="""
        Retrieves or sets the zoom applied to the camera's input.

        .. deprecated:: 1.8
            Please use the :attr:`zoom` attribute instead.
        """)

    def _get_overlays(self):
        self._check_camera_open()
        return self._overlays
    overlays = property(_get_overlays, doc="""\
        Retrieves all active :class:`PiRenderer` overlays.

        If no overlays are current active, :attr:`overlays` will return an
        empty iterable. Otherwise, it will return an iterable of
        :class:`PiRenderer` instances which are currently acting as overlays.
        Note that the preview renderer is an exception to this: it is *not*
        included as an overlay despite being derived from :class:`PiRenderer`.

        .. versionadded:: 1.8
        """)

    def _get_preview(self):
        self._check_camera_open()
        if isinstance(self._preview, PiPreviewRenderer):
            return self._preview
    preview = property(_get_preview, doc="""\
        Retrieves the :class:`PiRenderer` displaying the camera preview.

        If no preview is currently active, :attr:`preview` will return
        ``None``.  Otherwise, it will return the instance of
        :class:`PiRenderer` which is currently connected to the camera's
        preview port for rendering what the camera sees. You can use the
        attributes of the :class:`PiRenderer` class to configure the appearance
        of the preview. For example, to make the preview semi-transparent::

            import picamera

            with picamera.PiCamera() as camera:
                camera.start_preview()
                camera.preview.alpha = 128

        .. versionadded:: 1.8
        """)

    def _get_preview_alpha(self):
        self._check_camera_open()
        warnings.warn(
            PiCameraDeprecated(
                'PiCamera.preview_alpha is deprecated; use '
                'PiCamera.preview.alpha instead'))
        if self.preview:
            return self.preview.alpha
        else:
            return self._preview_alpha
    def _set_preview_alpha(self, value):
        self._check_camera_open()
        warnings.warn(
            PiCameraDeprecated(
                'PiCamera.preview_alpha is deprecated; use '
                'PiCamera.preview.alpha instead'))
        if self.preview:
            self.preview.alpha = value
        else:
            self._preview_alpha = value
    preview_alpha = property(_get_preview_alpha, _set_preview_alpha, doc="""\
        Retrieves or sets the opacity of the preview window.

        .. deprecated:: 1.8
            Please use the :attr:`~PiRenderer.alpha` attribute of the
            :attr:`preview` object instead.
        """)

    def _get_preview_layer(self):
        self._check_camera_open()
        warnings.warn(
            PiCameraDeprecated(
                'PiCamera.preview_layer is deprecated; '
                'use PiCamera.preview.layer instead'))
        if self.preview:
            return self.preview.layer
        else:
            return self._preview_layer
    def _set_preview_layer(self, value):
        self._check_camera_open()
        warnings.warn(
            PiCameraDeprecated(
                'PiCamera.preview_layer is deprecated; '
                'use PiCamera.preview.layer instead'))
        if self.preview:
            self.preview.layer = value
        else:
            self._preview_layer = value
    preview_layer = property(_get_preview_layer, _set_preview_layer, doc="""\
        Retrieves or sets the layer of the preview window.

        .. deprecated:: 1.8
            Please use the :attr:`~PiRenderer.layer` attribute of the
            :attr:`preview` object instead.
        """)

    def _get_preview_fullscreen(self):
        self._check_camera_open()
        warnings.warn(
            PiCameraDeprecated(
                'PiCamera.preview_fullscreen is deprecated; '
                'use PiCamera.preview.fullscreen instead'))
        if self.preview:
            return self.preview.fullscreen
        else:
            return self._preview_fullscreen
    def _set_preview_fullscreen(self, value):
        self._check_camera_open()
        warnings.warn(
            PiCameraDeprecated(
                'PiCamera.preview_fullscreen is deprecated; '
                'use PiCamera.preview.fullscreen instead'))
        if self.preview:
            self.preview.fullscreen = value
        else:
            self._preview_fullscreen = value
    preview_fullscreen = property(
            _get_preview_fullscreen, _set_preview_fullscreen, doc="""\
        Retrieves or sets full-screen for the preview window.

        .. deprecated:: 1.8
            Please use the :attr:`~PiRenderer.fullscreen` attribute of the
            :attr:`preview` object instead.
        """)

    def _get_preview_window(self):
        self._check_camera_open()
        warnings.warn(
            PiCameraDeprecated(
                'PiCamera.preview_window is deprecated; '
                'use PiCamera.preview.window instead'))
        if self.preview:
            return self.preview.window
        else:
            return self._preview_window
    def _set_preview_window(self, value):
        self._check_camera_open()
        warnings.warn(
            PiCameraDeprecated(
                'PiCamera.preview_window is deprecated; '
                'use PiCamera.preview.window instead'))
        if self.preview:
            self.preview.window = value
        else:
            self._preview_window = value
    preview_window = property(
        _get_preview_window, _set_preview_window, doc="""\
        Retrieves or sets the size of the preview window.

        .. deprecated:: 1.8
            Please use the :attr:`~PiRenderer.window` attribute of the
            :attr:`preview` object instead.
        """)

    def _get_annotate_text(self):
        self._check_camera_open()
        mp = self._camera.control.params[mmal.MMAL_PARAMETER_ANNOTATE]
        if mp.enable:
            return mp.text.decode('ascii')
        else:
            return ''
    def _set_annotate_text(self, value):
        self._check_camera_open()
        mp = self._camera.control.params[mmal.MMAL_PARAMETER_ANNOTATE]
        mp.enable = bool(value or mp.show_frame_num)
        if mp.enable:
            try:
                mp.text = value.encode('ascii')
            except ValueError as e:
                raise PiCameraValueError(str(e))
        self._camera.control.params[mmal.MMAL_PARAMETER_ANNOTATE] = mp
    annotate_text = property(_get_annotate_text, _set_annotate_text, doc="""\
        Retrieves or sets a text annotation for all output.

        When queried, the :attr:`annotate_text` property returns the current
        annotation (if no annotation has been set, this is simply a blank
        string).

        When set, the property immediately applies the annotation to the
        preview (if it is running) and to any future captures or video
        recording. Strings longer than 255 characters, or strings containing
        non-ASCII characters will raise a :exc:`PiCameraValueError`. The
        default value is ``''``.

        .. versionchanged:: 1.8
            Text annotations can now be 255 characters long. The prior limit
            was 32 characters.
        """)

    def _get_annotate_frame_num(self):
        self._check_camera_open()
        mp = self._camera.control.params[mmal.MMAL_PARAMETER_ANNOTATE]
        return mp.show_frame_num.value != mmal.MMAL_FALSE
    def _set_annotate_frame_num(self, value):
        self._check_camera_open()
        mp = self._camera.control.params[mmal.MMAL_PARAMETER_ANNOTATE]
        mp.enable = bool(value or mp.text)
        mp.show_frame_num = bool(value)
        self._camera.control.params[mmal.MMAL_PARAMETER_ANNOTATE] = mp
    annotate_frame_num = property(
        _get_annotate_frame_num, _set_annotate_frame_num, doc="""\
        Controls whether the current frame number is drawn as an annotation.

        The :attr:`annotate_frame_num` attribute is a bool indicating whether
        or not the current frame number is rendered as an annotation, similar
        to :attr:`annotate_text`. The default is ``False``.

        .. versionadded:: 1.8
        """)

    def _get_annotate_text_size(self):
        self._check_camera_open()
        if self._camera.annotate_rev == 3:
            mp = self._camera.control.params[mmal.MMAL_PARAMETER_ANNOTATE]
            return mp.text_size or self.DEFAULT_ANNOTATE_SIZE
        else:
            return self.DEFAULT_ANNOTATE_SIZE
    def _set_annotate_text_size(self, value):
        self._check_camera_open()
        if not (6 <= value <= 160):
            raise PiCameraValueError(
                "Invalid annotation text size: %d (valid range 6-160)" % value)
        if self._camera.annotate_rev == 3:
            mp = self._camera.control.params[mmal.MMAL_PARAMETER_ANNOTATE]
            mp.text_size = value
            self._camera.control.params[mmal.MMAL_PARAMETER_ANNOTATE] = mp
        elif value != self.DEFAULT_ANNOTATE_SIZE:
            warnings.warn(
                PiCameraFallback(
                    "Firmware does not support setting annotation text "
                    "size; using default (%d) instead" % self.DEFAULT_ANNOTATE_SIZE))
    annotate_text_size = property(
        _get_annotate_text_size, _set_annotate_text_size, doc="""\
        Controls the size of the annotation text.

        The :attr:`annotate_text_size` attribute is an int which determines how
        large the annotation text will appear on the display. Valid values are
        in the range 6 to 160, inclusive. The default is {size}.

        .. versionadded:: 1.10
        """.format(size=DEFAULT_ANNOTATE_SIZE))

    def _get_annotate_foreground(self):
        self._check_camera_open()
        mp = self._camera.control.params[mmal.MMAL_PARAMETER_ANNOTATE]
        if self._camera.annotate_rev == 3 and mp.custom_text_color:
            return Color.from_yuv_bytes(
                    mp.custom_text_Y,
                    mp.custom_text_U,
                    mp.custom_text_V)
        else:
            return Color('white')
    def _set_annotate_foreground(self, value):
        self._check_camera_open()
        if not isinstance(value, Color):
            raise PiCameraValueError(
                'annotate_foreground must be a Color')
        elif self._camera.annotate_rev < 3:
            if value.rgb_bytes != (255, 255, 255):
                warnings.warn(
                    PiCameraFallback(
                        "Firmware does not support setting a custom foreground "
                        "annotation color; using white instead"))
            return
        mp = self._camera.control.params[mmal.MMAL_PARAMETER_ANNOTATE]
        mp.custom_text_color = True
        (
            mp.custom_text_Y,
            mp.custom_text_U,
            mp.custom_text_V,
            ) = value.yuv_bytes
        self._camera.control.params[mmal.MMAL_PARAMETER_ANNOTATE] = mp
    annotate_foreground = property(
        _get_annotate_foreground, _set_annotate_foreground, doc="""\
        Controls the color of the annotation text.

        The :attr:`annotate_foreground` attribute specifies, partially, the
        color of the annotation text. The value is specified as a
        :class:`Color`. The default is white.

        .. note::

            The underlying firmware does not directly support setting all
            components of the text color, only the Y' component of a `Y'UV`_
            tuple. This is roughly (but not precisely) analogous to the
            "brightness" of a color, so you may choose to think of this as
            setting how bright the annotation text will be relative to its
            background. In order to specify just the Y' component when setting
            this attribute, you may choose to construct the
            :class:`Color` instance as follows::

                camera.annotate_foreground = picamera.Color(y=0.2, u=0, v=0)

        .. _Y'UV: https://en.wikipedia.org/wiki/YUV

        .. versionadded:: 1.10
        """)

    def _get_annotate_background(self):
        self._check_camera_open()
        mp = self._camera.control.params[mmal.MMAL_PARAMETER_ANNOTATE]
        if self._camera.annotate_rev == 3:
            if mp.enable_text_background:
                if mp.custom_background_color:
                    return Color.from_yuv_bytes(
                        mp.custom_background_Y,
                        mp.custom_background_U,
                        mp.custom_background_V)
                else:
                    return Color('black')
            else:
                return None
        else:
            if mp.black_text_background:
                return Color('black')
            else:
                return None
    def _set_annotate_background(self, value):
        self._check_camera_open()
        if value is True:
            warnings.warn(
                PiCameraDeprecated(
                    'Setting PiCamera.annotate_background to True is '
                    'deprecated; use PiCamera.color.Color("black") instead'))
            value = Color('black')
        elif value is False:
            warnings.warn(
                PiCameraDeprecated(
                    'Setting PiCamera.annotate_background to False is '
                    'deprecated; use None instead'))
            value = None
        elif value is None:
            pass
        elif not isinstance(value, Color):
            raise PiCameraValueError(
                'annotate_background must be a Color or None')
        elif self._camera.annotate_rev < 3 and value.rgb_bytes != (0, 0, 0):
            warnings.warn(
                PiCameraFallback(
                    "Firmware does not support setting a custom background "
                    "annotation color; using black instead"))
        mp = self._camera.control.params[mmal.MMAL_PARAMETER_ANNOTATE]
        if self._camera.annotate_rev == 3:
            if value is None:
                mp.enable_text_background = False
            else:
                mp.enable_text_background = True
                mp.custom_background_color = True
                (
                    mp.custom_background_Y,
                    mp.custom_background_U,
                    mp.custom_background_V,
                    ) = value.yuv_bytes
        else:
            if value is None:
                mp.black_text_background = False
            else:
                mp.black_text_background = True
        self._camera.control.params[mmal.MMAL_PARAMETER_ANNOTATE] = mp
    annotate_background = property(
        _get_annotate_background, _set_annotate_background, doc="""\
        Controls what background is drawn behind the annotation.

        The :attr:`annotate_background` attribute specifies if a background
        will be drawn behind the :attr:`annotation text <annotate_text>` and,
        if so, what color it will be. The value is specified as a
        :class:`Color` or ``None`` if no background should be drawn. The
        default is ``None``.

        .. note::

            For backward compatibility purposes, the value ``False`` will be
            treated as ``None``, and the value ``True`` will be treated as the
            color black. The "truthiness" of the values returned by the
            attribute are backward compatible although the values themselves
            are not.

        .. versionadded:: 1.8

        .. versionchanged:: 1.10
            In prior versions this was a bool value with ``True`` representing
            a black background.
        """)

