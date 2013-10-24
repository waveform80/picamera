from __future__ import (
    unicode_literals,
    print_function,
    division,
    absolute_import,
    )

# Make Py2's str equivalent to Py3's
str = type('')

import io
import os
import time
import math
import picamera
import pytest
from PIL import Image


def test_capture_to_file(camera, previewing, resolution, filename_format_options):
    filename, format, options = filename_format_options
    camera.capture(filename, **options)
    img = Image.open(filename)
    assert img.size == resolution
    assert img.format == format
    img.verify()

def test_capture_to_stream(camera, previewing, resolution, format_options):
    stream = io.BytesIO()
    format, options = format_options
    camera.capture(stream, format, **options)
    stream.seek(0)
    img = Image.open(stream)
    assert img.size == resolution
    assert img.format == format.upper()
    img.verify()

def test_capture_continuous_to_file(camera, previewing, resolution, tmpdir):
    for i, filename in enumerate(camera.capture_continuous(os.path.join(str(tmpdir), 'image{counter:02d}.jpg'))):
        img = Image.open(filename)
        assert img.size == resolution
        assert img.format == 'JPEG'
        img.verify()
        if not previewing:
            time.sleep(0.5)
        if i == 3:
            break

def test_capture_continuous_to_stream(camera, previewing, resolution):
    stream = io.BytesIO()
    for i, foo in enumerate(camera.capture_continuous(stream, format='jpeg')):
        stream.truncate()
        stream.seek(0)
        img = Image.open(stream)
        assert img.size == resolution
        assert img.format == 'JPEG'
        img.verify()
        stream.seek(0)
        if not previewing:
            time.sleep(0.1)
        if i == 3:
            break

def test_capture_sequence_to_file(camera, previewing, resolution, tmpdir):
    filenames = [os.path.join(str(tmpdir), 'image%d.jpg' % i) for i in range(3)]
    camera.capture_sequence(filenames)
    for filename in filenames:
        img = Image.open(filename)
        assert img.size == resolution
        assert img.format == 'JPEG'
        img.verify()

def test_capture_sequence_to_stream(camera, previewing, resolution):
    streams = [io.BytesIO() for i in range(3)]
    camera.capture_sequence(streams)
    for stream in streams:
        stream.seek(0)
        img = Image.open(stream)
        assert img.size == resolution
        assert img.format == 'JPEG'
        img.verify()

def test_capture_raw_rgb(camera, resolution, raw_format):
    # Calculate the expected size of the streams for the current
    # resolution; horizontal resolution is rounded up to the nearest
    # multiple of 32, and vertical to the nearest multiple of 16 by the
    # camera for raw data. RGB format holds 3 bytes per pixel, YUV format
    # holds 1.5 bytes per pixel (1 byte of Y per pixel, and 2 bytes of Cb
    # and Cr per 4 pixels)
    size = (
            math.ceil(resolution[0] / 32) * 32
            * math.ceil(resolution[1] / 16) * 16
            * {'yuv': 1.5, 'rgb': 3}[raw_format])
    stream = io.BytesIO()
    camera.capture(stream, format='raw')
    # Check the output stream has 3-bytes (24-bits) per pixel
    assert stream.tell() == size

def test_exif_ascii(camera, previewing, resolution):
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
def test_exif_binary(camera, previewing, resolution):
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

