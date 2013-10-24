from __future__ import (
    unicode_literals,
    print_function,
    division,
    absolute_import,
    )

# Make Py2's str equivalent to Py3's
str = type('')

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


def test_awb(camera_b):
    keyword_attr(camera_b, 'awb_mode', camera_b.AWB_MODES)

def test_brightness(camera_b):
    numeric_attr(camera_b, 'brightness', 0, 100)

def test_color_effects(camera_b):
    save_value = camera_b.color_effects
    try:
        camera_b.color_effects = None
        assert camera_b.color_effects is None
        camera_b.color_effects = (128, 128)
        assert camera_b.color_effects == (128, 128)
        camera_b.color_effects = (0, 255)
        assert camera_b.color_effects == (0, 255)
        camera_b.color_effects = (255, 0)
        assert camera_b.color_effects == (255, 0)
        with pytest.raises(picamera.PiCameraError):
            camera_b.color_effects = (-1, -1)
        with pytest.raises(picamera.PiCameraError):
            camera_b.color_effects = (0, 300)
    finally:
        camera_b.color_effects = save_value

def test_contrast(camera_b):
    numeric_attr(camera_b, 'contrast', -100, 100)

def test_exposure_compensation(camera_b):
    # XXX Workaround: for some weird reason the camera won't precisely accept
    # positive exposure compensations. Sometimes the value winds up what we
    # set it, sometimes it's one less ... ?
    save_value = camera_b.exposure_compensation
    try:
        for value in range(-25, 26):
            camera_b.exposure_compensation = value
            if value < 0:
                assert camera_b.exposure_compensation == value
            else:
                assert camera_b.exposure_compensation in (value, value - 1)
        with pytest.raises(picamera.PiCameraError):
            camera_b.exposure_compensation = -26
        with pytest.raises(picamera.PiCameraError):
            camera_b.exposure_compensation = 26
    finally:
        camera_b.exposure_compensation = save_value

def test_exposure_mode(camera_b):
    # XXX Workaround: setting mode verylong can cause locks so exclude it from
    # tests for now
    keyword_attr(camera_b, 'exposure_mode', (
        e for e in camera_b.EXPOSURE_MODES if e != 'verylong'))

def test_image_effect(camera_b):
    # XXX Workaround: setting posterize, whiteboard and blackboard doesn't
    # currently work
    keyword_attr(camera_b, 'image_effect', (
        e for e in camera_b.IMAGE_EFFECTS
        if e not in ('blackboard', 'whiteboard', 'posterize')))

def test_meter_mode(camera_b):
    keyword_attr(camera_b, 'meter_mode', camera_b.METER_MODES)

def test_rotation(camera_b):
    save_value = camera_b.rotation
    try:
        for value in range(0, 360):
            camera_b.rotation = value
            assert camera_b.rotation == [0, 90, 180, 270][value // 90]
        camera_b.rotation = 360
        assert camera_b.rotation == 0
    finally:
        camera_b.rotation = save_value

def test_saturation(camera_b):
    numeric_attr(camera_b, 'saturation', -100, 100)

def test_sharpness(camera_b):
    numeric_attr(camera_b, 'sharpness', -100, 100)

def test_video_stabilization(camera_b):
    boolean_attr(camera_b, 'video_stabilization')

def test_hflip(camera_b):
    boolean_attr(camera_b, 'hflip')

def test_vflip(camera_b):
    boolean_attr(camera_b, 'vflip')

def test_shutter_speed(camera_b):
    # When setting shutter speed manually, ensure the actual shutter speed is
    # within 50usec of the specified amount
    for value in range(0, 200000, 50):
        camera_b.shutter_speed = value
        assert (value - 50) <= camera_b.shutter_speed <= value

# XXX The preview properties work, but don't return correct values unless the
# preview is actually running; if this isn't expected behaviour then we should
# xfail these tests instead of simply testing for previewing...

def test_preview_alpha(camera_p):
    numeric_attr(camera_p, 'preview_alpha', 0, 255)

def test_preview_fullscreen(camera_p):
    boolean_attr(camera_p, 'preview_fullscreen')

def test_preview_window(camera_p):
    camera_p.preview_window = (0, 0, 320, 240)
    assert camera_p.preview_window == (0, 0, 320, 240)
    camera_p.preview_window = (1280-320, 720-240, 320, 240)
    assert camera_p.preview_window == (1280-320, 720-240, 320, 240)
    camera_p.preview_window = (0, 0, 640, 360)
    assert camera_p.preview_window == (0, 0, 640, 360)
    camera_p.preview_window = (0, 720-360, 640, 360)
    assert camera_p.preview_window == (0, 720-360, 640, 360)
    camera_p.preview_window = (1280-640, 0, 640, 360)
    assert camera_p.preview_window == (1280-640, 0, 640, 360)
    camera_p.preview_window = (1280-640, 720-360, 640, 360)
    assert camera_p.preview_window == (1280-640, 720-360, 640, 360)
    camera_p.preview_window = (0, 0, 1920, 1080)
    assert camera_p.preview_window == (0, 0, 1920, 1080)

def test_framerate_preview(camera_p):
    # Framerate can only be changed when the camera is idle
    with pytest.raises(picamera.PiCameraError):
        camera_p.framerate = 30

def test_framerate(camera):
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

def test_resolution_preview(camera_p):
    # Resolution can only be changed when the camera is idle
    with pytest.raises(picamera.PiCameraError):
        camera.resolution = (320, 240)

def test_resolution(camera):
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
        # Camera's vertical resolution is always a multiple of 16, and
        # horizontal is a multiple of 32, hence the difference in the video
        # formats here and below
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
        # Anything below 16,16 will fail (because the camera's vertical
        # resolution works in increments of 16)
        with pytest.raises(picamera.PiCameraError):
            camera.resolution = (0, 0)
        with pytest.raises(picamera.PiCameraError):
            camera.resolution = (15, 15)
    finally:
        camera.resolution = save_resolution

