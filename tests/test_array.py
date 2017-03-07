# vim: set et sw=4 sts=4 fileencoding=utf-8:
#
# Python camera library for the Rasperry-Pi camera module
# Copyright (c) 2013-2017 Dave Jones <dave@waveform.org.uk>
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

import numpy as np
import picamera
import picamera.array
import picamera.bcm_host as bcm_host
import picamera.mmal as mmal
import pytest
import mock


@pytest.fixture()
def fake_cam(request):
    cam = mock.Mock()
    cam.resolution = (10, 10)
    return cam


def test_rgb_array1(camera, mode):
    resolution, framerate = mode
    with picamera.array.PiRGBArray(camera) as stream:
        camera.capture(stream, 'rgb')
        assert stream.array.dtype == np.uint8
        assert stream.array.shape == (resolution[1], resolution[0], 3)

def test_rgb_array2(fake_cam):
    with picamera.array.PiRGBArray(fake_cam) as stream:
        stream.write(b'\x01\x02\x03' * 256)
        stream.write(b'\x01\x02\x03' * 256)
        stream.flush()
        assert (stream.array[:, :, 0] == 1).all()
        assert (stream.array[:, :, 1] == 2).all()
        assert (stream.array[:, :, 2] == 3).all()
        stream.truncate(0)
        with pytest.raises(picamera.PiCameraValueError):
            stream.write(b'\x00' * 10)
            stream.flush()

def test_rgb_array3(camera, mode):
    resolution, framerate = mode
    resize = (resolution[0] // 2, resolution[1] // 2)
    with picamera.array.PiRGBArray(camera, size=resize) as stream:
        camera.capture(stream, 'rgb', resize=resize)
        assert stream.array.dtype == np.uint8
        assert stream.array.shape == (resize[1], resize[0], 3)

def test_yuv_array1(camera, mode):
    resolution, framerate = mode
    if resolution == (2592, 1944):
        pytest.xfail('Pi runs out of memory during RGB conversion at this resolution')
    with picamera.array.PiYUVArray(camera) as stream:
        camera.capture(stream, 'yuv')
        assert stream.array.dtype == np.uint8
        assert stream.array.shape == (resolution[1], resolution[0], 3)
        assert stream.rgb_array.dtype == np.uint8
        assert stream.rgb_array.shape == (resolution[1], resolution[0], 3)

def test_yuv_array2(fake_cam):
    with picamera.array.PiYUVArray(fake_cam) as stream:
        stream.write(b'\x01' * 32 * 16)
        stream.write(b'\x02' * 16 * 8)
        stream.write(b'\x03' * 16 * 8)
        stream.flush()
        assert (stream.array[:, :, 0] == 1).all()
        assert (stream.array[:, :, 1] == 2).all()
        assert (stream.array[:, :, 2] == 3).all()
        # XXX What about rgb_array?
        stream.truncate(0)
        with pytest.raises(picamera.PiCameraValueError):
            stream.write(b'\x00' * 10)
            stream.flush()

def test_yuv_array3(camera, mode):
    resolution, framerate = mode
    resize = (resolution[0] // 2, resolution[1] // 2)
    with picamera.array.PiYUVArray(camera, size=resize) as stream:
        camera.capture(stream, 'yuv', resize=resize)
        assert stream.array.dtype == np.uint8
        assert stream.array.shape == (resize[1], resize[0], 3)
        assert stream.rgb_array.dtype == np.uint8
        assert stream.rgb_array.shape == (resize[1], resize[0], 3)

def test_yuv_buffer(camera, mode):
    resolution, framerate = mode
    width, height = resolution
    fwidth = (width + 31) // 32 * 32 # big enough even if 16x16 rounding
    fheight = (height + 15) // 16 * 16
    buf = np.empty((int(fwidth * fheight * 1.5),), dtype=np.uint8)
    camera.capture(buf, 'yuv')

def test_rgb_buffer(camera, mode):
    resolution, framerate = mode
    width, height = resolution
    fwidth = (width + 31) // 32 * 32 # big enough even if 16x16 rounding
    fheight = (height + 15) // 16 * 16
    buf = np.empty((fwidth * fheight * 3,), dtype=np.uint8)
    camera.capture(buf, 'rgb')

def test_bayer_array(camera, mode):
    with picamera.array.PiBayerArray(camera) as stream:
        camera.capture(stream, 'jpeg', bayer=True)
        # Bayer data is always full res
        if camera.exif_tags['IFD0.Model'].upper() == 'RP_OV5647':
            assert stream.array.shape == (1944, 2592, 3)
            assert stream.demosaic().shape == (1944, 2592, 3)
        else:
            assert stream.array.shape == (2464, 3280, 3)
            assert stream.demosaic().shape == (2464, 3280, 3)

def test_motion_array1(camera, mode):
    resolution, framerate = mode
    if resolution == (2592, 1944):
        pytest.xfail('Cannot encode video at max resolution')
    elif framerate == 5 and camera.exif_tags['IFD0.Model'].upper() == 'RP_IMX219':
        pytest.xfail('Motion vectors fail at low framerate on V2 camera module')
    with picamera.array.PiMotionArray(camera) as stream:
        camera.start_recording('/dev/null', 'h264', motion_output=stream)
        camera.wait_recording(1)
        camera.stop_recording()
        width = ((resolution[0] + 15) // 16) + 1
        height = (resolution[1] + 15) // 16
        assert stream.array.shape[1:] == (height, width)
        # Number of frames isn't going to be exact and due to start-up costs
        # in recent firmwares a lower bound seems difficult to calculate. Make
        # sure we get at least 1 frame and no more than we expect
        assert 1 < stream.array.shape[0] <= framerate

def test_motion_array2(camera, mode):
    resolution, framerate = mode
    if framerate == 5 and camera.exif_tags['IFD0.Model'].upper() == 'RP_IMX219':
        pytest.xfail('Motion vectors fail at low framerate on V2 camera module')
    if resolution == (2592, 1944):
        resize = (640, 480)
    else:
        resize = (resolution[0] // 2, resolution[1] // 2)
    with picamera.array.PiMotionArray(camera, size=resize) as stream:
        camera.start_recording(
            '/dev/null', 'h264', motion_output=stream, resize=resize)
        camera.wait_recording(1)
        camera.stop_recording()
        width = ((resize[0] + 15) // 16) + 1
        height = (resize[1] + 15) // 16
        assert stream.array.shape[1:] == (height, width)
        # Number of frames isn't going to be exact and due to start-up costs
        # in recent firmwares a lower bound seems difficult to calculate. Make
        # sure we get at least 1 frame and no more than we expect
        assert 1 < stream.array.shape[0] <= framerate

def test_yuv_analysis1(camera, mode):
    resolution, framerate = mode
    if resolution == (2592, 1944):
        pytest.xfail('Cannot encode video at max resolution')
    class YUVTest(picamera.array.PiYUVAnalysis):
        def __init__(self, camera):
            super(YUVTest, self).__init__(camera)
            self.write_called = False
        def analyze(self, a):
            self.write_called = True
            assert a.shape == (resolution[1], resolution[0], 3)
    with YUVTest(camera) as stream:
        camera.start_recording(stream, 'yuv')
        camera.wait_recording(1)
        camera.stop_recording()
        assert stream.write_called

def test_yuv_analysis2(fake_cam):
    class YUVTest(picamera.array.PiYUVAnalysis):
        def analyze(self, a):
            assert (a[..., 0] == 1).all()
            assert (a[..., 1] == 2).all()
            assert (a[..., 2] == 3).all()
    with YUVTest(fake_cam) as stream:
        stream.write((b'\x01' * 32 * 16) + (b'\x02' * 16 * 8) + (b'\x03' * 16 * 8))
        with pytest.raises(picamera.PiCameraValueError):
            stream.write(b'\x00' * 10)

def test_rgb_analysis1(camera, mode):
    resolution, framerate = mode
    if resolution == (2592, 1944):
        pytest.xfail('Cannot encode video at max resolution')
    class RGBTest(picamera.array.PiRGBAnalysis):
        def __init__(self, camera):
            super(RGBTest, self).__init__(camera)
            self.write_called = False
        def analyze(self, a):
            self.write_called = True
            assert a.shape == (resolution[1], resolution[0], 3)
    with RGBTest(camera) as stream:
        camera.start_recording(stream, 'rgb')
        camera.wait_recording(1)
        camera.stop_recording()
        assert stream.write_called

def test_rgb_analysis2(fake_cam):
    class RGBTest(picamera.array.PiRGBAnalysis):
        def analyze(self, a):
            assert (a[..., 0] == 1).all()
            assert (a[..., 1] == 2).all()
            assert (a[..., 2] == 3).all()
    with RGBTest(fake_cam) as stream:
        stream.write(b'\x01\x02\x03' * 512)
        with pytest.raises(picamera.PiCameraValueError):
            stream.write(b'\x00' * 10)

def test_motion_analysis1(camera, mode):
    resolution, framerate = mode
    if resolution == (2592, 1944):
        pytest.xfail('Cannot encode video at max resolution')
    width = ((resolution[0] + 15) // 16) + 1
    height = (resolution[1] + 15) // 16
    class MATest(picamera.array.PiMotionAnalysis):
        def __init__(self, camera):
            super(MATest, self).__init__(camera)
            self.write_called = False
        def analyze(self, a):
            self.write_called = True
            assert a.shape == (height, width)
    with MATest(camera) as stream:
        camera.start_recording('/dev/null', 'h264', motion_output=stream)
        camera.wait_recording(1)
        camera.stop_recording()
        assert stream.write_called

def test_motion_analysis2(camera, mode):
    resolution, framerate = mode
    if resolution == (2592, 1944):
        resize = (640, 480)
    else:
        resize = (resolution[0] // 2, resolution[1] // 2)
    width = ((resize[0] + 15) // 16) + 1
    height = (resize[1] + 15) // 16
    class MATest(picamera.array.PiMotionAnalysis):
        def __init__(self, camera, size):
            super(MATest, self).__init__(camera, size)
            self.write_called = False
        def analyze(self, a):
            self.write_called = True
            assert a.shape == (height, width)
    with MATest(camera, size=resize) as stream:
        camera.start_recording(
            '/dev/null', 'h264', motion_output=stream, resize=resize)
        camera.wait_recording(1)
        camera.stop_recording()
        assert stream.write_called

def test_overlay_array1(camera, mode):
    resolution, framerate = mode
    # Draw a cross overlay
    w, h = resolution
    w = bcm_host.VCOS_ALIGN_UP(w, 32)
    h = bcm_host.VCOS_ALIGN_UP(h, 16)
    a = np.zeros((h, w, 3), dtype=np.uint8)
    a[resolution[1] // 2, :, :] = 0xff
    a[:, resolution[0] // 2, :] = 0xff
    overlay = camera.add_overlay(a, resolution, alpha=128)
    assert len(camera.overlays) == 1
    assert camera.overlays[0].alpha == 128
    camera.remove_overlay(overlay)
    assert not camera.overlays

def test_overlay_array2(camera, mode):
    resolution, framerate = mode
    # Construct an array 25x25 big and display it at 10x10 on the screen
    a = np.zeros((32, 32, 3), dtype=np.uint8)
    a[:25, :25, :] = 0xff
    overlay = camera.add_overlay(
        a, (25, 25), layer=3, fullscreen=False, window=(10, 10, 25, 25))
    assert len(camera.overlays) == 1
    assert not camera.overlays[0].fullscreen
    assert camera.overlays[0].window == (10, 10, 25, 25)
    assert camera.overlays[0].layer == 3
    camera.remove_overlay(overlay)
    assert not camera.overlays

def test_overlay_array3(camera, mode):
    resolution, framerate = mode
    # Construct an array 32x32x3 array, make sure it's auto-detected as RGB
    a = np.zeros((32, 32, 3), dtype=np.uint8)
    overlay = camera.add_overlay(a, (32, 32))
    try:
        assert overlay.renderer.inputs[0].format == mmal.MMAL_ENCODING_RGB24
    finally:
        camera.remove_overlay(overlay)
    # Make sure it works with an explicit specification of RGB or BGR
    overlay = camera.add_overlay(a, (32, 32), 'rgb')
    try:
        assert overlay.renderer.inputs[0].format == mmal.MMAL_ENCODING_RGB24
    finally:
        camera.remove_overlay(overlay)
    overlay = camera.add_overlay(a, (32, 32), 'bgr')
    try:
        assert overlay.renderer.inputs[0].format == mmal.MMAL_ENCODING_BGR24
    finally:
        camera.remove_overlay(overlay)
    # Construct an array 32x32x4 array, make sure it's auto-detected as RGBA
    a = np.zeros((32, 32, 4), dtype=np.uint8)
    overlay = camera.add_overlay(a, (32, 32))
    try:
        assert overlay.renderer.inputs[0].format == mmal.MMAL_ENCODING_RGBA
    finally:
        camera.remove_overlay(overlay)
    # Make sure it works with an explicit specification of RGBA (we don't
    # test BGRA as old firmwares don't supported it on renderers)
    overlay = camera.add_overlay(a, (32, 32), 'rgba')
    try:
        assert overlay.renderer.inputs[0].format == mmal.MMAL_ENCODING_RGBA
    finally:
        camera.remove_overlay(overlay)
    # Make sure it fails with RGB or BGR
    with pytest.raises(picamera.PiCameraError):
        overlay = camera.add_overlay(a, (32, 32), 'rgb')
    with pytest.raises(picamera.PiCameraError):
        overlay = camera.add_overlay(a, (32, 32), 'bgr')

def test_bayer_bad(camera):
    stream = picamera.array.PiBayerArray(camera)
    stream.write(b'\x00' * 12000000)
    with pytest.raises(picamera.PiCameraValueError):
        stream.flush()

def test_array_writable(camera):
    stream = picamera.array.PiRGBArray(camera)
    assert stream.writable()

def test_array_no_analyze(camera):
    stream = picamera.array.PiRGBAnalysis(camera)
    res = camera.resolution.pad()
    with pytest.raises(NotImplementedError):
        stream.write(b'\x00' * (res.width * res.height * 3))

def test_analysis_writable(camera):
    stream = picamera.array.PiRGBAnalysis(camera)
    assert stream.writable()
