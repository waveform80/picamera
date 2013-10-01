import io
import os
import time
import tempfile
import picamera
import pytest
from PIL import Image

# Run tests with a variety of file suffixes and expected formats
@pytest.fixture(scope='module', params=(
    ('.jpg', 'JPEG', (('quality', 95),)),
    ('.jpg', 'JPEG', ()),
    ('.jpg', 'JPEG', (('quality', 50),)),
    ('.gif', 'GIF',  ()),
    ('.png', 'PNG',  ()),
    ('.bmp', 'BMP',  ()),
    ))
def filename_format_options(request):
    suffix, format, options = request.param
    filename = tempfile.mkstemp(suffix=suffix)[1]
    def fin():
        os.unlink(filename)
    request.addfinalizer(fin)
    return filename, format, dict(options)

# Run tests with a variety of format specs
@pytest.fixture(scope='module', params=(
    ('jpeg', (('quality', 95),)),
    ('jpeg', ()),
    ('jpeg', (('quality', 50),)),
    ('gif',  ()),
    ('png',  ()),
    ('bmp',  ()),
    ))
def format_options(request):
    format, options = request.param
    return format, dict(options)


def test_capture_to_file(camera, resolution, filename_format_options):
    filename, format, options = filename_format_options
    camera.capture(filename, **options)
    img = Image.open(filename)
    assert img.size == resolution
    assert img.format == format
    img.verify()

def test_capture_to_stream(camera, resolution, format_options):
    stream = io.BytesIO()
    format, options = format_options
    camera.capture(stream, format, **options)
    stream.seek(0)
    img = Image.open(stream)
    assert img.size == resolution
    assert img.format == format.upper()
    img.verify()

def test_continuous_to_file(camera, resolution, tmpdir):
    for i, filename in enumerate(camera.continuous(os.path.join(str(tmpdir), 'image{counter:02d}.jpg'))):
        img = Image.open(filename)
        assert img.size == resolution
        assert img.format == 'JPEG'
        img.verify()
        if not camera.previewing:
            time.sleep(0.1)
        if i == 3:
            break

def test_continuous_to_stream(camera, resolution):
    stream = io.BytesIO()
    for i, foo in enumerate(camera.continuous(stream, format='jpeg')):
        stream.truncate()
        stream.seek(0)
        img = Image.open(stream)
        assert img.size == resolution
        assert img.format == 'JPEG'
        img.verify()
        stream.seek(0)
        if not camera.previewing:
            time.sleep(0.1)
        if i == 3:
            break

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

