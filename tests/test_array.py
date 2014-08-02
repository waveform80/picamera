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

import numpy as np
import picamera
import picamera.array
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

def test_bayer_array(camera, mode):
    with picamera.array.PiBayerArray(camera) as stream:
        camera.capture(stream, 'jpeg', bayer=True)
        # Bayer data is always full res
        assert stream.array.shape == (1944, 2592, 3)
        assert stream.demosaic().shape == (1944, 2592, 3)

def test_motion_array1(camera, mode):
    resolution, framerate = mode
    if resolution == (2592, 1944):
        pytest.xfail('Cannot encode video at max resolution')
    with picamera.array.PiMotionArray(camera) as stream:
        camera.start_recording('/dev/null', 'h264', motion_output=stream)
        camera.wait_recording(1)
        camera.stop_recording()
        width = ((resolution[0] + 15) // 16) + 1
        height = (resolution[1] + 15) // 16
        assert stream.array.shape[1:] == (height, width)
        # Number of frames isn't going to be exact - make sure we're within 10
        # of the expected number
        assert framerate  - 5 <= stream.array.shape[0] <= framerate + 5

def test_motion_array2(camera, mode):
    resolution, framerate = mode
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
        # Number of frames isn't going to be exact - make sure we're within 10
        # of the expected number
        assert framerate  - 5 <= stream.array.shape[0] <= framerate + 5

def test_motion_analysis1(camera, mode):
    resolution, framerate = mode
    if resolution == (2592, 1944):
        pytest.xfail('Cannot encode video at max resolution')
    width = ((resolution[0] + 15) // 16) + 1
    height = (resolution[1] + 15) // 16
    class MATest(picamera.array.PiMotionAnalysis):
        def analyse(self, a):
            assert a.shape == (height, width)
    with MATest(camera) as stream:
        camera.start_recording('/dev/null', 'h264', motion_output=stream)
        camera.wait_recording(1)
        camera.stop_recording()

def test_motion_analysis1(camera, mode):
    resolution, framerate = mode
    resize = (resolution[0] // 2, resolution[1] // 2)
    width = ((resize[0] + 15) // 16) + 1
    height = (resize[1] + 15) // 16
    class MATest(picamera.array.PiMotionAnalysis):
        def analyse(self, a):
            assert a.shape == (height, width)
    with MATest(camera, size=resize) as stream:
        camera.start_recording(
            '/dev/null', 'h264', motion_output=stream, resize=resize)
        camera.wait_recording(1)
        camera.stop_recording()

