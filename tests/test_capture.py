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

import io
import os
import time
import tempfile
import picamera
import pytest
from PIL import Image
from collections import namedtuple
from verify import verify_image, RAW_FORMATS


CaptureCase = namedtuple('CaptureCase', ('format', 'ext', 'options'))

CAPTURE_CASES = (
    CaptureCase('jpeg', '.jpg',  {'quality': 95}),
    CaptureCase('jpeg', '.jpg',  {}),
    CaptureCase('jpeg', '.jpg',  {'resize': (640, 480)}),
    CaptureCase('jpeg', '.jpg',  {'quality': 50}),
    CaptureCase('gif',  '.gif',  {}),
    #CaptureCase('png',  '.png',  {}),
    CaptureCase('bmp',  '.bmp',  {}),
    ) + tuple(
    CaptureCase(fmt,    '.data', {})
    for fmt in RAW_FORMATS
    )


# Run tests with a variety of file suffixes and expected formats
@pytest.fixture(scope='module', params=CAPTURE_CASES)
def filename_format_options(request):
    filename = tempfile.mkstemp(suffix=request.param.ext)[1]
    def fin():
        os.unlink(filename)
    request.addfinalizer(fin)
    return filename, request.param.format, request.param.options

# Run tests with a variety of file suffixes and expected formats
@pytest.fixture(params=CAPTURE_CASES)
def ext_format_options(request):
    return request.param.ext, request.param.format, request.param.options

# Run tests with a variety of format specs
@pytest.fixture(params=CAPTURE_CASES)
def format_options(request):
    return request.param.format, request.param.options

@pytest.fixture(params=(False, True))
def use_video_port(request):
    return request.param

@pytest.fixture(params=(False, True))
def burst(request):
    return request.param

def expected_failures(resolution, format, use_video_port, burst=False):
    if resolution == (2592, 1944) and format in ('gif', 'bmp'):
        pytest.xfail('Camera fails to produce output with max. res BMPs or GIFs')
    if resolution == (2592, 1944) and format in ('rgba', 'bgra') and not use_video_port:
        pytest.xfail('Camera runs out of memory with this combination')
    if use_video_port and burst:
        pytest.xfail('Burst captures not supported with use_video_port')


def test_capture_to_file(
        camera, previewing, mode, filename_format_options, use_video_port):
    filename, format, options = filename_format_options
    resolution, framerate = mode
    expected_failures(resolution, format, use_video_port)
    camera.capture(
            filename,
            # Check that in the case of cooked formats, capture correctly
            # derives the format from the extension
            format=format if format in RAW_FORMATS else None,
            use_video_port=use_video_port, **options)
    if 'resize' in options:
        resolution = options['resize']
    verify_image(filename, format, resolution)

def test_capture_to_stream(
        camera, previewing, mode, format_options, use_video_port):
    stream = io.BytesIO()
    format, options = format_options
    resolution, framerate = mode
    expected_failures(resolution, format, use_video_port)
    if 'resize' in options:
        resolution = options['resize']
    camera.capture(stream, format, use_video_port=use_video_port, **options)
    stream.seek(0)
    verify_image(stream, format, resolution)

def test_capture_continuous_to_file(
        camera, mode, ext_format_options, tempdir, use_video_port, burst):
    ext, format, options = ext_format_options
    resolution, framerate = mode
    expected_failures(resolution, format, use_video_port, burst)
    for i, filename in enumerate(
            camera.capture_continuous(os.path.join(
                tempdir, 'image{counter:02d}%s' % ext),
                format=format if format in RAW_FORMATS else None,
                use_video_port=use_video_port, burst=burst)):
        verify_image(filename, format, resolution)
        if i == 3:
            break

def test_capture_continuous_to_stream(
        camera, mode, format_options, use_video_port, burst):
    format, options = format_options
    resolution, framerate = mode
    expected_failures(resolution, format, use_video_port, burst)
    stream = io.BytesIO()
    for i, foo in enumerate(
            camera.capture_continuous(stream, format=format,
                use_video_port=use_video_port, burst=burst)):
        stream.truncate()
        stream.seek(0)
        verify_image(stream, format, resolution)
        stream.seek(0)
        if i == 3:
            break

def test_capture_sequence_to_file(
        camera, mode, ext_format_options, tempdir, use_video_port, burst):
    ext, format, options = ext_format_options
    resolution, framerate = mode
    expected_failures(resolution, format, use_video_port, burst)
    filenames = [
        os.path.join(tempdir, 'image%d%s' % (i, ext))
        for i in range(3)
        ]
    camera.capture_sequence(
            filenames, format=format,
            use_video_port=use_video_port, burst=burst)
    for filename in filenames:
        verify_image(filename, format, resolution)

def test_capture_sequence_to_stream(
        camera, mode, format_options, use_video_port, burst):
    format, options = format_options
    resolution, framerate = mode
    expected_failures(resolution, format, use_video_port, burst)
    streams = [io.BytesIO() for i in range(3)]
    camera.capture_sequence(
            streams, format=format,
            use_video_port=use_video_port, burst=burst)
    for stream in streams:
        stream.seek(0)
        verify_image(stream, format, resolution)

def test_capture_bayer(camera, mode):
    stream = io.BytesIO()
    camera.capture(stream, format='jpeg', bayer=True)
    # Bayer data is always the last 6404096 bytes of the stream, and starts
    # with 'BRCM'
    if camera.exif_tags['IFD0.Model'].upper() == 'RP_OV5647':
        stream.seek(-6404096, io.SEEK_END)
    else:
        stream.seek(-10270208, io.SEEK_END)
    assert stream.read(4) == b'BRCM'

def test_capture_sequence_bayer(camera, mode):
    streams = [io.BytesIO() for i in range(3)]
    camera.capture_sequence(streams, format='jpeg', bayer=True)
    for stream in streams:
        if camera.exif_tags['IFD0.Model'].upper() == 'RP_OV5647':
            stream.seek(-6404096, io.SEEK_END)
        else:
            stream.seek(-10270208, io.SEEK_END)
        assert stream.read(4) == b'BRCM'

def test_exif_ascii(camera, mode):
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
def test_exif_binary(camera, mode):
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

def test_capture_bad_format(camera):
    with pytest.raises(picamera.PiCameraValueError):
        camera.capture('test.foo')
    with pytest.raises(picamera.PiCameraValueError):
        camera.capture('test.jpg', format='foo')
    with pytest.raises(picamera.PiCameraValueError):
        camera.capture('test.tiff')
    with pytest.raises(picamera.PiCameraValueError):
        camera.capture('test.jpg', format='tiff')

def test_capture_bad_burst(camera):
    with pytest.raises(picamera.PiCameraValueError):
        camera.capture_sequence(['test.jpg'], use_video_port=True, burst=True)
    with pytest.raises(picamera.PiCameraValueError):
        camera.capture('test.jpg', use_video_port=True, burst=True)

def test_capture_bytes_filename(camera, tmpdir):
    camera.capture(str(tmpdir.join('test.jpg')).encode('utf-8'))

def test_capture_bytes_format(camera, tmpdir):
    camera.capture(str(tmpdir.join('test.jpg')), b'jpeg')

