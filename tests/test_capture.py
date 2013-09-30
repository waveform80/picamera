import io
import os
import time
import tempfile
import picamera
import pytest
from PIL import Image

# Run tests while the camera is idle and after a 2 second preview warm-up
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

# Run tests at a variety of resolutions (and aspect ratios, 1:1, 4:3, 16:9)
@pytest.fixture(scope='module', params=(
    (100, 100),
    (320, 240),
    (1920, 1080),
    (2592, 1944),
    ))
def resolution(request, camera):
    was_previewing = camera.previewing
    if camera.previewing:
        camera.stop_preview()
    camera.resolution = request.param
    if was_previewing:
        camera.start_preview()
    return request.param

# Run tests with a variety of file suffixes and expected formats
@pytest.fixture(scope='module', params=(
    ('.jpg', 'JPEG'),
    ('.gif', 'GIF'),
    ('.png', 'PNG'),
    ('.bmp', 'BMP'),
    ))
def filename_format(request):
    suffix, fmt = request.param
    fn = tempfile.mkstemp(suffix=suffix)[1]
    def fin():
        os.unlink(fn)
    request.addfinalizer(fin)
    return fn, fmt

# Run tests with a variety of format specs
@pytest.fixture(scope='module', params=('jpeg', 'gif', 'png', 'bmp'))
def format(request):
    return request.param


def test_capture_to_file(camera, resolution, filename_format):
    filename, format = filename_format
    camera.capture(filename)
    img = Image.open(filename)
    assert img.size == resolution
    assert img.format == format
    img.verify()

def test_capture_to_stream(camera, resolution, format):
    stream = io.BytesIO()
    camera.capture(stream, format)
    stream.seek(0)
    img = Image.open(stream)
    assert img.size == resolution
    assert img.format == format.upper()
    img.verify()

def test_exif_ascii(camera):
    camera.exif_tags['IFD0.Artist'] = 'Me!'
    camera.exif_tags['IFD0.Copyright'] = 'Copyright (c) 2000 Foo'
    # Exif is only supported with JPEGs...
    stream = io.BytesIO()
    camera.capture(stream, 'jpeg')
    stream.seek(0)
    img = Image.open(stream)
    exif = img._getexif()
    # IFD0.Artist = 315
    # IFD0.Copyright = 33432
    assert exif[315] == 'Me!'
    assert exif[33432] == 'Copyright (c) 2000 Foo'

@pytest.mark.xfail(reason="Exif binary values don't work")
def test_exif_binary(camera):
    camera.exif_tags['IFD0.Copyright'] = b'Photographer copyright (c) 2000 Foo\x00Editor copyright (c) 2002 Bar\x00'
    camera.exif_tags['IFD0.UserComment'] = b'UNICODE\x00\xff\xfeF\x00o\x00o\x00'
    # Exif is only supported with JPEGs...
    stream = io.BytesIO()
    camera.capture(stream, 'jpeg')
    stream.seek(0)
    img = Image.open(stream)
    exif = img._getexif()
    # IFD0.Copyright = 33432
    # IFD0.UserComment = 37510
    assert exif[33432] == b'Photographer copyright (c) 2000 Foo\x00Editor copyright (c) 2002 Bar\x00'
    assert exif[37510] == b'UNICODE\x00\xff\xfeF\x00o\x00o\x00'

