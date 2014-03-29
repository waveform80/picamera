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

# Make Py2's str equivalent to Py3's
str = type('')

import picamera
import pytest
from fractions import Fraction


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


def test_awb_mode(camera, previewing):
    keyword_attr(camera, 'awb_mode', camera.AWB_MODES)

def test_awb_gains(camera, previewing):
    save_mode = camera.awb_mode
    try:
        # XXX Workaround: can't use numeric_attr here as awb_mode is write-only
        camera.awb_mode = 'off'
        for i in range (9):
            camera.awb_gains = i
        camera.awb_gains = 1.5
        camera.awb_gains = (1.5, 1.5)
        camera.awb_gains = (Fraction(16, 10), 1.9)
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

def test_exposure_compensation(camera, previewing):
    numeric_attr(camera, 'exposure_compensation', -25, 25)

def test_exposure_mode(camera, previewing):
    # XXX Workaround: setting mode verylong can cause locks so exclude it from
    # tests for now
    keyword_attr(camera, 'exposure_mode', (
        e for e in camera.EXPOSURE_MODES if e != 'verylong'))

def test_image_effect(camera, previewing):
    # XXX Workaround: setting posterize, whiteboard and blackboard doesn't
    # currently work
    keyword_attr(camera, 'image_effect', (
        e for e in camera.IMAGE_EFFECTS
        if e not in ('blackboard', 'whiteboard', 'posterize')))

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

def test_video_stabilization(camera, previewing):
    boolean_attr(camera, 'video_stabilization')

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
        # is within 50usec of the specified amount
        for value in range(0, 200000, 50):
            camera.shutter_speed = value
            assert (value - 50) <= camera.shutter_speed <= value
        # Test the shutter speed clamping by framerate
        camera.framerate = 30
        assert 33000 <= camera.shutter_speed <= 33333
    finally:
        camera.framerate = save_framerate
        camera.shutter_speed = 0

def test_crop(camera, previewing):
    save_crop = camera.crop
    try:
        camera.crop = (0.0, 0.0, 1.0, 1.0)
        assert camera.crop == (0.0, 0.0, 1.0, 1.0)
        camera.crop = (0.2, 0.2, 0.6, 0.6)
        assert camera.crop == (0.2, 0.2, 0.6, 0.6)
        camera.crop = (0.1, 0.1, 0.8, 0.8)
        # 0.1 doesn't quite make the round trip...
        assert camera.crop == (int(0.1*65535.0)/65535.0, int(0.1*65535.0)/65535.0, 0.8, 0.8)
    finally:
        camera.crop = save_crop

# XXX The preview properties work, but don't return correct values unless the
# preview is actually running; if this isn't expected behaviour then we should
# xfail these tests instead of simply testing for previewing...

def test_preview_alpha(camera, previewing):
    if previewing:
        numeric_attr(camera, 'preview_alpha', 0, 255)

def test_preview_layer(camera, previewing):
    if previewing:
        numeric_attr(camera, 'preview_layer', 0, 10)

def test_preview_fullscreen(camera, previewing):
    if previewing:
        boolean_attr(camera, 'preview_fullscreen')

def test_preview_window(camera, previewing):
    if previewing:
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
            camera.framerate = 100
    finally:
        camera.framerate = save_framerate

def test_resolution(camera, previewing):
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

