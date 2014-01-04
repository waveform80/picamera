# vim: set et sw=4 sts=4 fileencoding=utf-8:
#
# Python camera library for the Rasperry-Pi camera module
# Copyright (c) 2013, Dave Hughes <dave@waveform.org.uk>
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

import io
import os
import time
import math
import tempfile
import picamera
import pytest
from PIL import Image
from collections import namedtuple


CaptureCase = namedtuple('TestCase', ('format', 'ext', 'options'))

CAPTURE_CASES = (
    CaptureCase('jpeg', '.jpg', {'quality': 95}),
    CaptureCase('jpeg', '.jpg', {}),
    CaptureCase('jpeg', '.jpg', {'quality': 50}),
    #CaptureCase('gif',  '.gif', {}),
    CaptureCase('png',  '.png', {}),
    #CaptureCase('bmp',  '.bmp', {}),
    )


# Run tests with a variety of file suffixes and expected formats
@pytest.fixture(scope='module', params=CAPTURE_CASES)
def filename_format_options(request):
    filename = tempfile.mkstemp(suffix=request.param.ext)[1]
    def fin():
        os.unlink(filename)
    request.addfinalizer(fin)
    return filename, request.param.format, request.param.options

# Run tests with a variety of format specs
@pytest.fixture(scope='module', params=CAPTURE_CASES)
def format_options(request):
    return request.param.format, request.param.options

# Run tests with one of the two supported raw formats
@pytest.fixture(scope='module', params=('yuv', 'rgb'))
def raw_format(request, camera):
    save_format = camera.raw_format
    camera.raw_format = request.param
    def fin():
        camera.raw_format = save_format
    request.addfinalizer(fin)
    return request.param

@pytest.fixture(scope='module', params=(False, True))
def use_video_port(request):
    return request.param


def test_capture_to_file(
        camera, previewing, resolution, filename_format_options, use_video_port):
    filename, format, options = filename_format_options
    camera.capture(filename, use_video_port=use_video_port, **options)
    img = Image.open(filename)
    assert img.size == resolution
    assert img.format.lower() == format
    img.verify()

def test_capture_to_stream(
        camera, previewing, resolution, format_options, use_video_port):
    stream = io.BytesIO()
    format, options = format_options
    camera.capture(stream, format, use_video_port=use_video_port, **options)
    stream.seek(0)
    img = Image.open(stream)
    assert img.size == resolution
    assert img.format.lower() == format
    img.verify()

def test_capture_continuous_to_file(
        camera, previewing, resolution, tmpdir, use_video_port):
    for i, filename in enumerate(
            camera.capture_continuous(os.path.join(
                str(tmpdir), 'image{counter:02d}.jpg'),
                use_video_port=use_video_port)):
        img = Image.open(filename)
        assert img.size == resolution
        assert img.format == 'JPEG'
        img.verify()
        if not previewing:
            time.sleep(0.5)
        if i == 3:
            break

def test_capture_continuous_to_stream(
        camera, previewing, resolution, use_video_port):
    stream = io.BytesIO()
    for i, foo in enumerate(
            camera.capture_continuous(stream, format='jpeg',
                use_video_port=use_video_port)):
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

def test_capture_sequence_to_file(
        camera, previewing, resolution, tmpdir, use_video_port):
    filenames = [os.path.join(str(tmpdir), 'image%d.jpg' % i) for i in range(3)]
    camera.capture_sequence(filenames, use_video_port=use_video_port)
    for filename in filenames:
        img = Image.open(filename)
        assert img.size == resolution
        assert img.format == 'JPEG'
        img.verify()

def test_capture_sequence_to_stream(
        camera, previewing, resolution, use_video_port):
    streams = [io.BytesIO() for i in range(3)]
    camera.capture_sequence(streams, use_video_port=use_video_port)
    for stream in streams:
        stream.seek(0)
        img = Image.open(stream)
        assert img.size == resolution
        assert img.format == 'JPEG'
        img.verify()

def test_capture_raw(camera, resolution, raw_format, use_video_port):
    # Calculate the expected size of the streams for the current
    # resolution; horizontal resolution is rounded up to the nearest
    # multiple of 32, and vertical to the nearest multiple of 16 by the
    # camera for raw data. RGB format holds 3 bytes per pixel, YUV format
    # holds 1.5 bytes per pixel (1 byte of Y per pixel, and 2 bytes of Cb
    # and Cr per 4 pixels)
    if raw_format == 'rgb' and use_video_port:
        pytest.xfail('Cannot capture raw-RGB from video port')
    size = (
            math.ceil(resolution[0] / 32) * 32
            * math.ceil(resolution[1] / 16) * 16
            * {'yuv': 1.5, 'rgb': 3}[raw_format])
    stream = io.BytesIO()
    camera.capture(stream, format='raw', use_video_port=use_video_port)
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

