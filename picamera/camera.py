from __future__ import (
    unicode_literals,
    print_function,
    division,
    absolute_import,
    )

# Make Py2's str equivalent to Py3's
str = type('')

import datetime
import mimetypes
import ctypes as ct

import picamera.mmal as mmal
import picamera.bcm_host as bcm_host
from picamera.exc import (
    PiCameraError,
    PiCameraValueError,
    PiCameraRuntimeError,
    mmal_check,
    )
from picamera.encoders import (
    PiVideoEncoder,
    PiImageEncoder,
    PiRawImageEncoder,
    PiCookedImageEncoder,
    PiMultiImageEncoder,
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
    CAMERA_VIDEO_PORT = PiVideoEncoder.port
    CAMERA_CAPTURE_PORT = PiImageEncoder.port
    CAMERA_PORTS = (
        CAMERA_PREVIEW_PORT,
        CAMERA_VIDEO_PORT,
        CAMERA_CAPTURE_PORT,
        )
    MAX_IMAGE_RESOLUTION = (2592, 1944)
    MAX_VIDEO_RESOLUTION = (1920, 1080)
    DEFAULT_FRAME_RATE_NUM = 30
    DEFAULT_FRAME_RATE_DEN = 1
    FULL_FRAME_RATE_NUM = 15
    FULL_FRAME_RATE_DEN = 1
    VIDEO_OUTPUT_BUFFERS_NUM = 3

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

    RAW_FORMATS = {
        'yuv': mmal.MMAL_ENCODING_I420,
        'rgb': mmal.MMAL_ENCODING_BGR24,
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
        self._camera = None
        self._camera_config = None
        self._preview = None
        self._preview_connection = None
        self._null_sink = None
        self._video_encoder = None
        self._still_encoder = None
        self._exif_tags = {
            'IFD0.Model': 'RP_OV5647',
            'IFD0.Make': 'RaspberryPi',
            }
        self._init_led()
        try:
            self._init_camera()
            self._init_defaults()
            self._init_preview()
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
            except RuntimeError:
                # We're probably not running as root. In this case, cleanup and
                # forget the GPIO reference so we don't try anything further
                GPIO.cleanup()
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

        screen_width = ct.c_uint32()
        screen_height = ct.c_uint32()
        bcm_host.graphics_get_display_size(0, screen_width, screen_height)
        cc = self._camera_config
        cc.max_stills_w=screen_width.value
        cc.max_stills_h=screen_height.value
        cc.stills_yuv422=0
        cc.one_shot_stills=1
        cc.max_preview_video_w=screen_width.value
        cc.max_preview_video_h=screen_height.value
        cc.num_preview_video_frames=3
        cc.stills_capture_circular_buffer_height=0
        cc.fast_preview_resume=0
        cc.use_stc_timestamp=mmal.MMAL_PARAM_TIMESTAMP_MODE_RESET_STC
        mmal_check(
            mmal.mmal_port_parameter_set(self._camera[0].control, cc.hdr),
            prefix="Camera control port couldn't be configured")

        for p in self.CAMERA_PORTS:
            port = self._camera[0].output[p]
            fmt = port[0].format
            fmt[0].encoding = mmal.MMAL_ENCODING_I420 if p != self.CAMERA_PREVIEW_PORT else mmal.MMAL_ENCODING_OPAQUE
            fmt[0].encoding_variant = mmal.MMAL_ENCODING_I420
            fmt[0].es[0].video.width = cc.max_preview_video_w
            fmt[0].es[0].video.height = cc.max_preview_video_h
            fmt[0].es[0].video.crop.x = 0
            fmt[0].es[0].video.crop.y = 0
            fmt[0].es[0].video.crop.width = cc.max_preview_video_w
            fmt[0].es[0].video.crop.height = cc.max_preview_video_h
            fmt[0].es[0].video.frame_rate.num = 3 if p == self.CAMERA_CAPTURE_PORT else self.DEFAULT_FRAME_RATE_NUM
            fmt[0].es[0].video.frame_rate.den = 1 if p == self.CAMERA_CAPTURE_PORT else self.DEFAULT_FRAME_RATE_DEN
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
        if not self._preview[0].input_num:
            raise PiCameraError("No input ports on null sink component")

        mmal_check(
            mmal.mmal_component_enable(self._null_sink),
            prefix="Null sink component couldn't be enabled")

        self._preview_connection = ct.POINTER(mmal.MMAL_CONNECTION_T)()
        mmal_check(
            mmal.mmal_connection_create(
                self._preview_connection,
                self._camera[0].output[self.CAMERA_PREVIEW_PORT],
                self._null_sink[0].input[0],
                mmal.MMAL_CONNECTION_FLAG_TUNNELLING |
                mmal.MMAL_CONNECTION_FLAG_ALLOCATION_ON_INPUT),
            prefix="Failed to connect camera to null sink")
        mmal_check(
            mmal.mmal_connection_enable(self._preview_connection),
            prefix="Failed to enable preview connection")

    def _check_camera_open(self):
        if self.closed:
            raise PiCameraRuntimeError("Camera is closed")

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
        if self.recording:
            self.stop_recording()
        if self._preview_connection:
            mmal.mmal_connection_destroy(self._preview_connection)
            self._preview_connection = None
        if self._null_sink:
            mmal.mmal_component_destroy(self._null_sink)
            self._null_sink = None
        if self._preview:
            mmal.mmal_component_destroy(self._preview)
            self._preview = None
        if self._camera:
            mmal.mmal_component_destroy(self._camera)
            self._camera = None
        if GPIO:
            GPIO.cleanup()
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
        while the preview is running (e.g. :attr:`brightness`).  The preview
        typically overrides whatever is currently visible on the display. To
        stop the preview and reveal the display again, call
        :meth:`stop_preview`. The preview can be started and stopped multiple
        times during the lifetime of the :class:`PiCamera` object.
        """
        self._check_camera_open()
        # Switch the camera's preview port from the null sink to the
        # preview component
        if self._preview_connection:
            mmal.mmal_connection_destroy(self._preview_connection)
            self._null_connection = None
        self._preview_connection = ct.POINTER(mmal.MMAL_CONNECTION_T)()
        mmal_check(
            mmal.mmal_connection_create(
                self._preview_connection,
                self._camera[0].output[self.CAMERA_PREVIEW_PORT],
                self._preview[0].input[0],
                mmal.MMAL_CONNECTION_FLAG_TUNNELLING |
                mmal.MMAL_CONNECTION_FLAG_ALLOCATION_ON_INPUT),
            prefix="Failed to connect camera to preview")
        mmal_check(
            mmal.mmal_connection_enable(self._preview_connection),
            prefix="Failed to enable preview connection")

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
        self._preview_connection = ct.POINTER(mmal.MMAL_CONNECTION_T)()
        mmal_check(
            mmal.mmal_connection_create(
                self._preview_connection,
                self._camera[0].output[self.CAMERA_PREVIEW_PORT],
                self._null_sink[0].input[0],
                mmal.MMAL_CONNECTION_FLAG_TUNNELLING |
                mmal.MMAL_CONNECTION_FLAG_ALLOCATION_ON_INPUT),
            prefix="Failed to connect camera to null sink")
        mmal_check(
            mmal.mmal_connection_enable(self._preview_connection),
            prefix="Failed to enable preview connection")

    def start_recording(self, output, format=None, **options):
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

        Certain formats accept additional options which can be specified
        as keyword arguments. The ``'h264'`` format accepts the following
        additional options:

        * *profile* - The H.264 profile to use for encoding. Defaults to 'high',
          but can be one of 'baseline', 'main', 'high', or 'constrained'.

        * *intraperiod* - The key frame rate (the rate at which I-frames are
          inserted in the output). Defaults to 0, but can be any positive
          32-bit integer value.

        * *bitrate* - The bitrate at which video will be encoded. Defaults to
          17000000 (17Mbps) if not specified.
        """
        format = self._get_video_format(output, format)
        encoder = PiVideoEncoder(self, format, **options)
        try:
            encoder.start(output)
        except Exception as e:
            encoder.close()
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
        if not self._video_encoder:
            raise PiCameraRuntimeError('There is no recording in progress')
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
            if self._video_encoder:
                self._video_encoder.close()

    def capture(self, output, format=None, **options):
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

        * ``'bmp'`` - Write a bitmap file

        * ``'raw'`` - Write the raw sensor data to a file (set
          :attr:`raw_format` to determine the raw format)

        Certain file formats accept additional options which can be specified
        as keyword arguments. Currently, only the ``'jpeg'`` encoder accepts
        additional options, which are:

        * *quality* - Defines the quality of the JPEG encoder as an integer
          ranging from 1 to 100. Defaults to 85.

        * *thumbnail* - Defines the size and quality of the thumbnail to embed
          in the Exif data. Specifying ``None`` disables thumbnail generation.
          Otherwise, specify a tuple of ``(width, height, quality)``. Defaults
          to ``(64, 48, 35)``.
        """
        format = self._get_image_format(output, format)
        if format == 'raw':
            encoder = PiRawImageEncoder(self, format, **options)
        else:
            encoder = PiCookedImageEncoder(self, format, **options)
        try:
            encoder.start(output)
            # Wait for the callback to set the event indicating the end of
            # image capture
            encoder.wait()
        finally:
            encoder.close()
            encoder = None

    def capture_sequence(
            self, outputs, format='jpeg', use_video_port=False, **options):
        """
        Capture a sequence of consecutive images from the camera.

        This method accepts a sequence or iterator of *outputs* each of which
        must either be a string specifying a filename for output, or a
        file-like object with a ``write`` method. For each item in the sequence
        or iterator of outputs, the camera captures a single image as fast as
        it can.

        The *format* and *options* parameters are the same as in
        :meth:`capture`, but *format* defaults to ``'jpeg'``. The format is
        _not_ derived from the filenames in *outputs* by this method.

        The *use_video_port* parameter controls whether the camera's image or
        video port is used to capture images. It defaults to False which means
        that the camera's image port is used. This port is slow but produces
        better quality pictures. If you need rapid capture up to the rate of
        video frames, set this to True.

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
        """
        format = self._get_image_format('', format)
        if use_video_port:
            encoder = PiMultiImageEncoder(self, format, **options)
            try:
                encoder.start(outputs)
                encoder.wait()
            finally:
                encoder.close()
        else:
            if format == 'raw':
                encoder = PiRawImageEncoder(self, format, **options)
            else:
                encoder = PiCookedImageEncoder(self, format, **options)
            try:
                for output in outputs:
                    encoder.start(output)
                    encoder.wait()
            finally:
                encoder.close()

    def capture_continuous(
            self, output, format=None, use_video_port=False, **options):
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

        The *format* and *options* parameters are the same as in
        :meth:`capture`.

        The *use_video_port* parameter controls whether the camera's image or
        video port is used to capture images. It defaults to False which means
        that the camera's image port is used. This port is slow but produces
        better quality pictures. If you need rapid capture up to the rate of
        video frames, set this to True.

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
                    time.sleep(0.5)
        """
        format = self._get_image_format(output, format)
        if format == 'raw':
            encoder = PiRawImageEncoder(
                self, format, use_video_port=use_video_port, **options)
        else:
            encoder = PiCookedImageEncoder(
                self, format, use_video_port=use_video_port, **options)
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
                    encoder.wait()
                    yield filename
                    counter += 1
            else:
                while True:
                    encoder.start(output)
                    encoder.wait()
                    yield output
        finally:
            encoder.close()

    def continuous(self, output, format, **options):
        """
        .. deprecated:: 0.5

            Please use :meth:`capture_continuous` instead. This method will be
            removed in 1.0.

        """
        for result in self.capture_continuous(output, format, **options):
            yield result

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
        state of the camera's LED as a boolean value (True is on, False is
        off).

        .. note::
            This is a write-only property. While it can be used to control the
            camera's LED, you cannot query the state of the camera's LED using
            this property.
        """)

    def _get_raw_format(self):
        self._check_camera_open()
        return self._RAW_FORMATS_R[
            self._camera[0].output[1][0].format[0].encoding]
    def _set_raw_format(self, value):
        self._check_camera_open()
        self._check_recording_stopped()
        try:
            value = self.RAW_FORMATS[value]
        except KeyError:
            raise PiCameraValueError("Invalid raw format: %s" % value)
        mmal_check(
            mmal.mmal_connection_disable(self._preview_connection),
            prefix="Failed to disable preview connection")
        mmal_check(
            mmal.mmal_component_disable(self._camera),
            prefix="Failed to disable camera")
        for port in (self.CAMERA_VIDEO_PORT, self.CAMERA_CAPTURE_PORT):
            fmt = self._camera[0].output[port][0].format[0]
            fmt.encoding = value
            fmt.encoding_variant = value
            mmal_check(
                mmal.mmal_port_format_commit(self._camera[0].output[port]),
                prefix="Camera port format couldn't be set")
        mmal_check(
            mmal.mmal_component_enable(self._camera),
            prefix="Failed to enable camera")
        mmal_check(
            mmal.mmal_connection_enable(self._preview_connection),
            prefix="Failed to enable preview connection")
    raw_format = property(_get_raw_format, _set_raw_format, doc="""
        Retrieves or sets the raw format of the camera's ports.

        This property is only of interest to those wishing to :meth:`capture`
        images with `format='raw'`. It configures the raw output format of the
        image and video capture ports of the camera. By default, these are set
        to ``'yuv'``, and this is the only format which is compatible with the
        encoders for JPEG, PNG, etc. (attempting to use :meth:`capture` while
        :attr:`raw_format` is set to something other than ``'yuv'`` will result
        in an exception). Currently the only settings supported by this
        attribute are:

        * ``'yuv'`` - Capture data in planar YUV 4:2:0 format (FOURCC=I420).

        * ``'rgb'`` - Capture data in 24-bit RGB format (8 bits per color).

        .. note::
            The camera is capable of other raw formats (e.g. NV12); if anyone
            is interested in the library providing access to these formats,
            please contact the author or file an enhancement ticket in the bug
            tracker.

        For example, if you wish to capture raw images in RGB format (8 bits
        of red, 8 bits of green, 8 bits of blue) you would do the following::

            import time
            import picamera
            with picamera.PiCamera() as camera:
                camera.raw_format = 'rgb'
                camera.start_preview()
                time.sleep(1)
                camera.capture('foo.raw', format='raw')

        All available raw formats can be queried from the
        ``PiCamera.RAW_FORMATS`` attribute. The camera must not be closed, and
        no recording must be active when the property is set.
        """)

    def _get_framerate(self):
        self._check_camera_open()
        return (
            self._camera[0].output[1][0].format[0].es[0].video.frame_rate.num,
            self._camera[0].output[1][0].format[0].es[0].video.frame_rate.den)
    def _set_framerate(self, value):
        self._check_camera_open()
        self._check_recording_stopped()
        w, h = self.resolution
        try:
            n, d = value
        except (TypeError, ValueError) as e:
            n = int(value)
            d = 1
        # At resolutions higher than 1080p, drop the frame rate (GPU can only
        # manage 15fps at full frame)
        if ((w > self.MAX_VIDEO_RESOLUTION[0])
                or (h > self.MAX_VIDEO_RESOLUTION[1])):
            max_rate = 15
        else:
            max_rate = 30
        if not (0 < n / d <= max_rate):
            raise PiCameraValueError(
                "Maximum framerate at the current resolution is %dfps" % max_rate)
        mmal_check(
            mmal.mmal_connection_disable(self._preview_connection),
            prefix="Failed to disable preview connection")
        mmal_check(
            mmal.mmal_component_disable(self._camera),
            prefix="Failed to disable camera")
        for port in (self.CAMERA_VIDEO_PORT, self.CAMERA_PREVIEW_PORT):
            fmt = self._camera[0].output[port][0].format[0].es[0]
            fmt.video.frame_rate.num = n
            fmt.video.frame_rate.den = d
            mmal_check(
                mmal.mmal_port_format_commit(self._camera[0].output[port]),
                prefix="Camera video format couldn't be set")
        mmal_check(
            mmal.mmal_component_enable(self._camera),
            prefix="Failed to enable camera")
        mmal_check(
            mmal.mmal_connection_enable(self._preview_connection),
            prefix="Failed to enable preview connection")
    framerate = property(_get_framerate, _set_framerate, doc="""
        Retrieves or sets the framerate at which video-port based image
        captures, video recordings, and previews will run.

        When queried, the :attr:`framerate` property returns the rate at
        which the camera's video and preview ports will operate as a tuple of
        ``(numerator, denominator)``. The true framerate can be calculated as
        ``numerator / denominator``.

        When set, the property reconfigures the camera so that the next call to
        recording and previewing methods will use the new framerate.  The
        framerate can be specified as a ``(numerator, denominator)`` tuple, or
        as a simple integer.  The camera must not be closed, and no recording
        must be active when the property is set.

        The property defaults to 30fps at resolutions of 1080p (1920x1080) or
        below. Above this resolution, the property defaults to 15fps. These
        are the maximum framerates of the camera and attempting to set higher
        rates will result in a PiCameraValueError.
        """)

    def _get_resolution(self):
        self._check_camera_open()
        return (
            self._camera_config.max_stills_w,
            self._camera_config.max_stills_h
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
        # At resolutions higher than 1080p, drop the frame rate (GPU can only
        # manage 15fps at full frame)
        if ((w > self.MAX_VIDEO_RESOLUTION[0])
                or (h > self.MAX_VIDEO_RESOLUTION[1])) and (n / d > 15):
            n = 15
            d = 1
        mmal_check(
            mmal.mmal_connection_disable(self._preview_connection),
            prefix="Failed to disable preview connection")
        mmal_check(
            mmal.mmal_component_disable(self._camera),
            prefix="Failed to disable camera")
        self._camera_config.max_stills_w = w
        self._camera_config.max_stills_h = h
        self._camera_config.max_preview_video_w = w
        self._camera_config.max_preview_video_h = h
        mmal_check(
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
            if port != self.CAMERA_CAPTURE_PORT:
                fmt.video.frame_rate.num = n
                fmt.video.frame_rate.den = d
            mmal_check(
                mmal.mmal_port_format_commit(self._camera[0].output[port]),
                prefix="Camera video format couldn't be set")
        mmal_check(
            mmal.mmal_component_enable(self._camera),
            prefix="Failed to enable camera")
        mmal_check(
            mmal.mmal_connection_enable(self._preview_connection),
            prefix="Failed to enable preview connection")
    resolution = property(_get_resolution, _set_resolution, doc="""
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
        closed, and no recording must be active when the property is set.

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

        .. warning::
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

        .. warning::
            Currently, the "verylong" exposure mode can `lock up the camera`_
            under certain conditions.

        .. _lock up the camera: http://www.raspberrypi.org/phpBB3/viewtopic.php?p=429945#p429945
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
                int(65535 * x),
                int(65535 * y),
                int(65535 * w),
                int(65535 * h)
                ),
            )
        mmal_check(
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
        set to False, the :attr:`preview_window` property can be used to
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

        When the :attr:`preview_fullscreen` property is set to False, the
        :attr:`preview_window` property specifies the size and position of the
        preview window on the display. The property is a 4-tuple consisting of
        ``(x, y, width, height)``. The property can be set while recordings or
        previews are active.

        .. note::
            The :attr:`preview_window` attribute is afflicted by the same issue
            as :attr:`preview_alpha` with regards to changes while the preview
            is not running.
        """)

bcm_host.bcm_host_init()
mimetypes.add_type('application/h264', '.h264', False)

