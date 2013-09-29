import os
import time
import tempfile
import picamera
import pytest
from PIL import Image

# Run all tests while the camera is idle and after a 2 second preview warm-up
@pytest.fixture(scope='module', params=(False, True))
def camera(request):
    camera = picamera.PiCamera()
    if request.param:
        camera.start_preview()
    def fin():
        if camera.previewing:
            camera.stop_preview()
        camera.close()
    request.addfinalizer(fin)
    return camera

# Run all tests at a variety of resolutions (and aspect ratios, 1:1, 4:3, 16:9)
@pytest.fixture(scope='module', params=((100, 100), (320, 240), (1920, 1080), (2592, 1944)))
def resolution(request, camera):
    was_previewing = camera.previewing
    if camera.previewing:
        camera.stop_preview()
    camera.resolution = request.param
    if was_previewing:
        camera.start_preview()
    return request.param

# Fixtures for producing temporary files with a variety of suffixes
@pytest.fixture
def tmpfile(request, suffix=''):
    result = tempfile.mkstemp(suffix=suffix)[1]
    def fin():
        os.unlink(result)
    request.addfinalizer(fin)
    return result

@pytest.fixture
def jpegfile(request):
    return tmpfile(request, suffix='.jpg')

@pytest.fixture
def pngfile(request):
    return tmpfile(request, suffix='.png')

@pytest.fixture
def giffile(request):
    return tmpfile(request, suffix='.gif')

@pytest.fixture
def bmpfile(request):
    return tmpfile(request, suffix='.bmp')

def test_jpeg(camera, resolution, jpegfile):
    camera.capture(jpegfile)
    img = Image.open(jpegfile)
    assert img.size == resolution
    assert img.format == 'JPEG'
    img.verify()

def test_png(camera, resolution, pngfile):
    camera.capture(pngfile)
    img = Image.open(pngfile)
    assert img.size == resolution
    assert img.format == 'PNG'
    img.verify()

def test_gif(camera, resolution, giffile):
    camera.capture(giffile)
    img = Image.open(giffile)
    assert img.size == resolution
    assert img.format == 'GIF'
    img.verify()

def test_bmp(camera, resolution, bmpfile):
    camera.capture(bmpfile)
    img = Image.open(bmpfile)
    assert img.size == resolution
    assert img.format == 'BMP'
    img.verify()

