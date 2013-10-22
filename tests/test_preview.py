import picamera
import pytest

def numeric_attr(camera, attr, value_min, value_max, step=1):
    save_value = getattr(camera, attr)
    try:
        for value in range(value_min, value_max + 1, step):
            setattr(camera, attr, value)
            assert value == getattr(camera, attr)
        with pytest.raises(picamera.PiCameraError):
            setattr(camera, attr, value_min - 1)
        with pytest.raises(picamera.PiCameraError):
            setattr(camera, attr, value_max + 1)
    finally:
        setattr(camera, attr, save_value)

def keyword_attr(camera, attr, values):
    save_value = getattr(camera, attr)
    try:
        for value in values:
            setattr(camera, attr, value)
            assert value == getattr(camera, attr)
        with pytest.raises(picamera.PiCameraError):
            setattr(camera, attr, 'foobar')
    finally:
        setattr(camera, attr, save_value)

def boolean_attr(camera, attr):
    save_value = getattr(camera, attr)
    try:
        setattr(camera, attr, False)
        assert not getattr(camera, attr)
        setattr(camera, attr, True)
        assert getattr(camera, attr)
    finally:
        setattr(camera, attr, save_value)

def test_awb(camera):
    keyword_attr(camera, 'awb_mode', camera.AWB_MODES)

def test_brightness(camera):
    numeric_attr(camera, 'brightness', 0, 100)

def test_color_effects(camera):
    save_value = camera.color_effects
    try:
        camera.color_effects = None
        assert camera.color_effects is None
        camera.color_effects = (128, 128)
        assert camera.color_effects == (128, 128)
        camera.color_effects = (0, 255)
        assert camera.color_effects == (0, 255)
        camera.color_effects = (255, 0)
        assert camera.color_effects == (255, 0)
        with pytest.raises(picamera.PiCameraError):
            camera.color_effects = (-1, -1)
        with pytest.raises(picamera.PiCameraError):
            camera.color_effects = (0, 300)
    finally:
        camera.color_effects = save_value

def test_contrast(camera):
    numeric_attr(camera, 'contrast', -100, 100)

def test_exposure_compensation(camera):
    # XXX Workaround: for some weird reason the camera won't precisely accept
    # positive exposure compensations. Sometimes the value winds up what we
    # set it, sometimes it's one less ... ?
    save_value = camera.exposure_compensation
    try:
        for value in range(-25, 26):
            camera.exposure_compensation = value
            if value < 0:
                assert camera.exposure_compensation == value
            else:
                assert camera.exposure_compensation in (value, value - 1)
        with pytest.raises(picamera.PiCameraError):
            camera.exposure_compensation = -26
        with pytest.raises(picamera.PiCameraError):
            camera.exposure_compensation = 26
    finally:
        camera.exposure_compensation = save_value

def test_exposure_mode(camera):
    # XXX Workaround: setting mode verylong can cause locks so exclude it from
    # tests for now
    keyword_attr(camera, 'exposure_mode', (
        e for e in camera.EXPOSURE_MODES if e != 'verylong'))

def test_image_effect(camera):
    # XXX Workaround: setting posterize, whiteboard and blackboard doesn't
    # currently work
    keyword_attr(camera, 'image_effect', (
        e for e in camera.IMAGE_EFFECTS
        if e not in ('blackboard', 'whiteboard', 'posterize')))

def test_meter_mode(camera):
    keyword_attr(camera, 'meter_mode', camera.METER_MODES)

def test_rotation(camera):
    save_value = camera.rotation
    try:
        for value in range(0, 360):
            camera.rotation = value
            assert camera.rotation == [0, 90, 180, 270][value // 90]
        camera.rotation = 360
        assert camera.rotation == 0
    finally:
        camera.rotation = save_value

def test_saturation(camera):
    numeric_attr(camera, 'saturation', -100, 100)

def test_sharpness(camera):
    numeric_attr(camera, 'sharpness', -100, 100)

def test_video_stabilization(camera):
    boolean_attr(camera, 'video_stabilization')

def test_hflip(camera):
    boolean_attr(camera, 'hflip')

def test_vflip(camera):
    boolean_attr(camera, 'vflip')

def test_shutter_speed(camera):
    # When setting shutter speed manually, ensure the actual shutter speed is
    # within 50usec of the specified amount
    for value in range(0, 500000, 50):
        camera.shutter_speed = value
        assert (value - 50) <= camera.shutter_speed <= value

# XXX The preview properties work, but don't return correct values unless the
# preview is actually running; if this isn't expected behaviour then we should
# xfail these tests instead of simply testing for previewing...

def test_preview_alpha(camera):
    if camera.previewing:
        numeric_attr(camera, 'preview_alpha', 0, 255)

def test_preview_fullscreen(camera):
    if camera.previewing:
        boolean_attr(camera, 'preview_fullscreen')

def test_preview_window(camera):
    if camera.previewing:
        camera.preview_window = (0, 0, 320, 240)
        assert camera.preview_window == (0, 0, 320, 240)
        camera.preview_window = (1280-320, 720-240, 320, 240)
        assert camera.preview_window == (1280-320, 720-240, 320, 240)
        camera.preview_window = (0, 0, 640, 360)
        assert camera.preview_window == (0, 0, 640, 360)
        camera.preview_window = (0, 720-360, 640, 360)
        assert camera.preview_window == (0, 720-360, 640, 360)
        camera.preview_window = (1280-640, 0, 640, 360)
        assert camera.preview_window == (1280-640, 0, 640, 360)
        camera.preview_window = (1280-640, 720-360, 640, 360)
        assert camera.preview_window == (1280-640, 720-360, 640, 360)
        camera.preview_window = (0, 0, 1920, 1080)
        assert camera.preview_window == (0, 0, 1920, 1080)

def test_framerate(camera):
    # Framerate can only be changed when the camera is idle
    if camera.previewing:
        with pytest.raises(picamera.PiCameraError):
            camera.framerate = 30
    else:
        save_framerate = camera.framerate
        try:
            assert len(camera.framerate) == 2
            camera.framerate = (30, 1)
            n, d = camera.framerate
            assert n/d == 30
            camera.framerate = (15, 1)
            n, d = camera.framerate
            assert n/d == 15
            camera.framerate = 30
            n, d = camera.framerate
            assert n/d == 30
            camera.framerate = 15
            n, d = camera.framerate
            assert n/d == 15
            camera.framerate = (30, 2)
            n, d = camera.framerate
            assert n/d == 15
            camera.framerate = 5
            n, d = camera.framerate
            assert n/d == 5
            camera.framerate = 10
            n, d = camera.framerate
            assert n/d == 10
            with pytest.raises(picamera.PiCameraError):
                camera.framerate = -1
            with pytest.raises(picamera.PiCameraError):
                camera.framerate = 60
        finally:
            camera.framerate = save_framerate

def test_resolution(camera):
    # Resolution can only be changed when the camera is idle
    if camera.previewing:
        with pytest.raises(picamera.PiCameraError):
            camera.resolution = (320, 240)
    else:
        save_resolution = camera.resolution
        try:
            # Test setting some regular resolutions
            camera.resolution = (320, 240)
            assert camera.resolution == (320, 240)
            assert camera._camera[0].port[2][0].format[0].es[0].video.width == 320
            assert camera._camera[0].port[2][0].format[0].es[0].video.height == 240
            camera.resolution = (640, 480)
            assert camera.resolution == (640, 480)
            assert camera._camera[0].port[2][0].format[0].es[0].video.width == 640
            assert camera._camera[0].port[2][0].format[0].es[0].video.height == 480
            camera.resolution = (1280, 720)
            assert camera.resolution == (1280, 720)
            assert camera._camera[0].port[2][0].format[0].es[0].video.width == 1280
            assert camera._camera[0].port[2][0].format[0].es[0].video.height == 720
            camera.resolution = (1920, 1080)
            assert camera.resolution == (1920, 1080)
            # Camera's vertical resolution is always a multiple of 16, hence the
            # difference in the video format height here and below
            assert camera._camera[0].port[2][0].format[0].es[0].video.width == 1920
            assert camera._camera[0].port[2][0].format[0].es[0].video.height == 1088
            camera.resolution = (2592, 1944)
            assert camera.resolution == (2592, 1944)
            assert camera._camera[0].port[2][0].format[0].es[0].video.width == 2592
            assert camera._camera[0].port[2][0].format[0].es[0].video.height == 1952
            # Test some irregular resolutions
            camera.resolution = (100, 100)
            assert camera.resolution == (100, 100)
            assert camera._camera[0].port[2][0].format[0].es[0].video.width == 128
            assert camera._camera[0].port[2][0].format[0].es[0].video.height == 112
            # Anything below 16,16 will fail (because the camera's vertical resolution
            # works in increments of 16)
            with pytest.raises(picamera.PiCameraError):
                camera.resolution = (0, 0)
            with pytest.raises(picamera.PiCameraError):
                camera.resolution = (15, 15)
        finally:
            camera.resolution = save_resolution

