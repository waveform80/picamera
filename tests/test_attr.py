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

import picamera
from picamera.color import Color
import pytest
import time
from fractions import Fraction
from decimal import Decimal


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


def test_analog_gain(camera, previewing):
    # Just test the read-only property returns something sensible
    assert 0.0 <= camera.analog_gain <= 8.0

def test_annotate_text(camera, previewing):
    save_value = camera.annotate_text
    try:
        camera.annotate_text = ''
        assert camera.annotate_text == ''
        camera.annotate_text = 'foo'
        assert camera.annotate_text == u'foo'
        camera.annotate_text = 'foo bar baz quux xyzzy'
        assert camera.annotate_text == u'foo bar baz quux xyzzy'
        with pytest.raises(picamera.PiCameraValueError):
            camera.annotate_text = ('abcd' * 64) + 'a'
        with pytest.raises(picamera.PiCameraValueError):
            camera.annotate_text = 'Oh lá lá'
    finally:
        camera.annotate_text = save_value

def test_annotate_text_size(camera, previewing):
    numeric_attr(camera, 'annotate_text_size', 6, 160)

def test_annotate_foreground(camera, previewing):
    save_value = camera.annotate_foreground
    try:
        camera.annotate_foreground = Color('black')
        camera.annotate_foreground = Color('white')
        camera.annotate_foreground = Color.from_yuv(0.5, 0, 0)
        with pytest.raises(picamera.PiCameraValueError):
            camera.annotate_foreground = 'white'
        with pytest.raises(picamera.PiCameraValueError):
            camera.annotate_foreground = 0
        with pytest.raises(picamera.PiCameraValueError):
            camera.annotate_foreground = None
    finally:
        camera.annotate_foreground = save_value

def test_annotate_background(camera, previewing):
    save_value = camera.annotate_background
    try:
        camera.annotate_background = Color('black')
        camera.annotate_background = Color('white')
        camera.annotate_background = Color(128, 128, 0)
        with pytest.raises(picamera.PiCameraValueError):
            camera.annotate_background = 'black'
        with pytest.raises(picamera.PiCameraValueError):
            camera.annotate_background = 0
        camera.annotate_background = None
    finally:
        camera.annotate_background = save_value

def test_annotate_frame_num(camera, previewing):
    boolean_attr(camera, 'annotate_frame_num')

def test_awb_mode(camera, previewing):
    keyword_attr(camera, 'awb_mode', camera.AWB_MODES)

def test_awb_gains(camera, previewing):

    def check_gains(red, blue):
        # The camera needs some time to let the AWB gains adjust
        time.sleep(0.4)
        # The gains we get back aren't absolutely precise, but they're
        # close (+/- 0.05)
        r, b = camera.awb_gains
        assert red - 0.05 <= r <= red + 0.05
        assert blue - 0.05 <= b <= blue + 0.05

    save_mode = camera.awb_mode
    try:
        # Can't use numeric_attr here as awb_mode is a (red, blue) tuple
        camera.awb_mode = 'off'
        for i in range (1, 9):
            camera.awb_gains = i
            check_gains(i, i)
        camera.awb_gains = 1.5
        check_gains(1.5, 1.5)
        camera.awb_gains = (0.5, 0.5)
        check_gains(0.5, 0.5)
        camera.awb_gains = (Fraction(16, 10), 1.9)
        check_gains(1.6, 1.9)
        with pytest.raises(picamera.PiCameraError):
            camera.awb_gains = Fraction(20, 1)
    finally:
        camera.awb_mode = save_mode

def test_brightness(camera, previewing):
    numeric_attr(camera, 'brightness', 0, 100)

def test_color_effects(camera, previewing):
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

def test_contrast(camera, previewing):
    numeric_attr(camera, 'contrast', -100, 100)

def test_digital_gain(camera, previewing):
    # Just test the read-only property returns something sensible
    assert 0.0 <= camera.digital_gain <= 8.0

def test_exposure_compensation(camera, previewing):
    numeric_attr(camera, 'exposure_compensation', -25, 25)

def test_exposure_mode(camera, previewing):
    keyword_attr(camera, 'exposure_mode', camera.EXPOSURE_MODES)

def test_flash_mode(camera, previewing):
    keyword_attr(camera, 'flash_mode', camera.FLASH_MODES)

def test_image_effects1(camera, previewing):
    valid_combinations = {
        'solarize': [
            (False, 128, 128, 128, 0),
            (True, 128, 128, 128, 0),
            (False, 16, 192, 0, 0),
            (128, 128, 128, 0),
            0,
            ],
        'colorbalance': [
            (0, 1, 1, 1, 0, 0),
            (0, 0.5, 0.5, 0.5),
            (0.451, 1, 1),
            (0, 1.0, 0.5, 0.75, -64, 64),
            ],
        'colorpoint': [0, (1,), (2,), 3],
        'colorswap':  [0, (1,)],
        'posterise':  [2, (30,), 16],
        'blur':       [1, (2,)],
        'film':       [(0, 0, 0), (50, 128, 128)],
        'watercolor': [(), (128, 128)],
        }
    try:
        for effect in camera.IMAGE_EFFECTS:
            camera.image_effect = effect
            assert camera.image_effect_params is None
            if effect in valid_combinations:
                for params in valid_combinations[effect]:
                    camera.image_effect_params = params
                    assert camera.image_effect_params == params
    finally:
        camera.image_effect = 'none'

def test_image_effects2(camera, previewing):
    invalid_combinations = {
        'solarize':     [(3, 3, 3), ()],
        'colorpoint':   [(1, 1), ()],
        'colorbalance': [(1,), False, ()],
        'colorswap':    [(1, 1), ()],
        'posterise':    [(1, 1), ()],
        'blur':         [(1, 1), ()],
        'film':         [(1, 1), (), (12, 2, 3, 4)],
        'watercolor':   [1, (1, 2, 3)],
        }
    try:
        for effect, params_sets in invalid_combinations.items():
            camera.image_effect = effect
            for params in params_sets:
                with pytest.raises(picamera.PiCameraValueError):
                    camera.image_effect_params = params
    finally:
        camera.image_effect = 'none'

def test_drc_strength(camera, previewing):
    keyword_attr(camera, 'drc_strength', camera.DRC_STRENGTHS)

def test_meter_mode(camera, previewing):
    keyword_attr(camera, 'meter_mode', camera.METER_MODES)

def test_rotation(camera, previewing):
    save_value = camera.rotation
    try:
        for value in range(0, 360):
            camera.rotation = value
            assert camera.rotation == [0, 90, 180, 270][value // 90]
        camera.rotation = 360
        assert camera.rotation == 0
    finally:
        camera.rotation = save_value

def test_saturation(camera, previewing):
    numeric_attr(camera, 'saturation', -100, 100)

def test_sharpness(camera, previewing):
    numeric_attr(camera, 'sharpness', -100, 100)

def test_iso(camera, previewing):
    numeric_attr(camera, 'iso', 0, 1600)

def test_video_stabilization(camera, previewing):
    boolean_attr(camera, 'video_stabilization')

def test_video_denoise(camera, previewing):
    boolean_attr(camera, 'video_denoise')

def test_image_denoise(camera, previewing):
    boolean_attr(camera, 'image_denoise')

def test_still_stats(camera, previewing):
    boolean_attr(camera, 'still_stats')

def test_hflip(camera, previewing):
    boolean_attr(camera, 'hflip')

def test_vflip(camera, previewing):
    boolean_attr(camera, 'vflip')

def test_shutter_speed(camera, previewing):
    # Shutter speed is now clamped by frame-rate; set frame-rate to something
    # nice and low to enable the test to run correctly
    save_framerate = camera.framerate
    camera.framerate = 1
    try:
        # When setting shutter speed manually, ensure the actual shutter speed
        # is within 50usec of the specified amount (the value+1 accounts for
        # a rounding error)
        for value in range(0, 700000, 50):
            camera.shutter_speed = value
            assert (value - 50) <= camera.shutter_speed <= (value + 1)
        # Test the shutter speed clamping by framerate
        camera.framerate = 30
        assert 33000 <= camera.shutter_speed <= 33333
    finally:
        camera.framerate = save_framerate
        camera.shutter_speed = 0

def test_zoom(camera, previewing):
    save_zoom = camera.zoom
    try:
        camera.zoom = (0.0, 0.0, 1.0, 1.0)
        assert camera.zoom == (0.0, 0.0, 1.0, 1.0)
        camera.zoom = (0.2, 0.2, 0.6, 0.6)
        assert camera.zoom == (0.2, 0.2, 0.6, 0.6)
        camera.zoom = (0.1, 0.1, 0.8, 0.8)
        # 0.1 doesn't quite make the round trip...
        assert camera.zoom == (int(0.1*65535.0)/65535.0, int(0.1*65535.0)/65535.0, 0.8, 0.8)
    finally:
        camera.zoom = save_zoom

# XXX The preview properties work, but don't return correct values unless the
# preview is actually running; if this isn't expected behaviour then we should
# xfail these tests instead of simply testing for previewing...

def test_preview_alpha(camera, previewing):
    if previewing:
        numeric_attr(camera.preview, 'alpha', 0, 255)

def test_preview_layer(camera, previewing):
    if previewing:
        numeric_attr(camera.preview, 'layer', 0, 255)

def test_preview_fullscreen(camera, previewing):
    if previewing:
        boolean_attr(camera.preview, 'fullscreen')

def test_preview_window(camera, previewing):
    if previewing:
        camera.preview.window = (0, 0, 320, 240)
        assert camera.preview.window == (0, 0, 320, 240)
        camera.preview.window = (1280-320, 720-240, 320, 240)
        assert camera.preview.window == (1280-320, 720-240, 320, 240)
        camera.preview.window = (0, 0, 640, 360)
        assert camera.preview.window == (0, 0, 640, 360)
        camera.preview.window = (0, 720-360, 640, 360)
        assert camera.preview.window == (0, 720-360, 640, 360)
        camera.preview.window = (1280-640, 0, 640, 360)
        assert camera.preview.window == (1280-640, 0, 640, 360)
        camera.preview.window = (1280-640, 720-360, 640, 360)
        assert camera.preview.window == (1280-640, 720-360, 640, 360)
        camera.preview.window = (0, 0, 1920, 1080)
        assert camera.preview.window == (0, 0, 1920, 1080)

def test_preview_resolution(camera, previewing):
    if previewing:
        save_resolution = camera.resolution
        try:
            camera.resolution = (640, 480)
            assert camera.preview.resolution is None
            camera.preview.resolution = (320, 240)
            assert camera.preview.resolution == (320, 240)
            assert camera._camera.outputs[0].framesize == (320, 240)
            assert camera._camera.outputs[2].framesize == (640, 480)
            camera.resolution = (320, 240)
            assert camera.preview.resolution is None
            assert camera._camera.outputs[0].framesize == (320, 240)
            assert camera._camera.outputs[2].framesize == (320, 240)
            camera.resolution = (1280, 720)
            assert camera.resolution == (1280, 720)
            assert camera.preview.resolution is None
            assert camera._camera.outputs[0].framesize == (1280, 720)
            assert camera._camera.outputs[2].framesize == (1280, 720)
            with pytest.raises(picamera.PiCameraValueError):
                camera.preview.resolution = (1281, 720)
            with pytest.raises(picamera.PiCameraValueError):
                camera.preview.resolution = (1280, 721)
        finally:
            camera.resolution = save_resolution

def test_preview_rotation(camera, previewing):
    if previewing:
        save_value = camera.preview.rotation
        try:
            for value in range(0, 360):
                camera.preview.rotation = value
                assert camera.preview.rotation == [0, 90, 180, 270][value // 90]
            camera.preview.rotation = 360
            assert camera.preview.rotation == 0
        finally:
            camera.preview.rotation = save_value

def test_preview_vflip(camera, previewing):
    if previewing:
        boolean_attr(camera.preview, 'vflip')

def test_preview_hflip(camera, previewing):
    if previewing:
        boolean_attr(camera.preview, 'hflip')

def test_sensor_mode(camera, previewing):
    save_mode = camera.sensor_mode
    try:
        for mode in range(8):
            camera.sensor_mode = mode
            assert camera.sensor_mode == mode
        with pytest.raises(picamera.PiCameraError):
            camera.sensor_mode = 10
    finally:
        camera.sensor_mode = save_mode

def test_framerate_delta(camera, previewing):
    for num in range(-10, 11):
        camera.framerate_delta = num / 10
        assert Fraction(num, 10) - Fraction(1, 256) <= camera.framerate_delta <= Fraction(num, 10) + Fraction(1, 256)

def test_framerate(camera, previewing):
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
        camera.framerate = 15.0
        n, d = camera.framerate
        assert n/d == 15
        camera.framerate = Fraction(30, 2)
        n, d = camera.framerate
        assert n/d == 15
        camera.framerate = Decimal(30)
        n, d = camera.framerate
        assert n/d == 30
        camera.framerate = 60
        n, d = camera.framerate
        assert n/d == 60
        camera.framerate = 90
        n, d = camera.framerate
        assert n/d == 90
        with pytest.raises(picamera.PiCameraError):
            camera.framerate = (30, 0)
        with pytest.raises(picamera.PiCameraError):
            camera.framerate = -1
        with pytest.raises(picamera.PiCameraError):
            camera.framerate = 200
    finally:
        camera.framerate = save_framerate

def test_resolution(camera, previewing):
    save_resolution = camera.resolution
    try:
        # Test setting some regular resolutions
        camera.resolution = (320, 240)
        assert camera.resolution == (320, 240)
        assert camera._camera.outputs[2].framesize == (320, 240)
        camera.resolution = (640, 480)
        assert camera.resolution == (640, 480)
        assert camera._camera.outputs[2].framesize == (640, 480)
        camera.resolution = (1280, 720)
        assert camera.resolution == (1280, 720)
        assert camera._camera.outputs[2].framesize == (1280, 720)
        camera.resolution = (1920, 1080)
        assert camera.resolution == (1920, 1080)
        # Camera's vertical resolution is always a multiple of 16, and
        # horizontal is a multiple of 32, hence the difference in the video
        # formats here and below
        assert camera._camera.outputs[2]._port[0].format[0].es[0].video.width == 1920
        assert camera._camera.outputs[2]._port[0].format[0].es[0].video.height == 1088
        camera.resolution = (2592, 1944)
        assert camera.resolution == (2592, 1944)
        assert camera._camera.outputs[2]._port[0].format[0].es[0].video.width == 2592
        assert camera._camera.outputs[2]._port[0].format[0].es[0].video.height == 1952
        # Test some irregular resolutions
        camera.resolution = (100, 100)
        assert camera.resolution == (100, 100)
        assert camera._camera.outputs[2]._port[0].format[0].es[0].video.width == 128
        assert camera._camera.outputs[2]._port[0].format[0].es[0].video.height == 112
        # Anything below 16,16 will fail (because the camera's vertical
        # resolution works in increments of 16)
        with pytest.raises(picamera.PiCameraError):
            camera.resolution = (0, 0)
        with pytest.raises(picamera.PiCameraError):
            camera.resolution = (15, 15)
    finally:
        camera.resolution = save_resolution

