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

import io
import os
import time
import tempfile
import picamera
import pytest
from PIL import Image
from collections import namedtuple
from verify import verify_image, verify_raw


CaptureCase = namedtuple('CaptureCase', ('format', 'ext', 'options'))

CAPTURE_CASES = (
    CaptureCase('jpeg', '.jpg', {'quality': 95}),
    CaptureCase('jpeg', '.jpg', {}),
    CaptureCase('jpeg', '.jpg', {'resize': (640, 480)}),
    CaptureCase('jpeg', '.jpg', {'quality': 50}),
    CaptureCase('gif',  '.gif', {}),
    CaptureCase('png',  '.png', {}),
    CaptureCase('bmp',  '.bmp', {}),
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
@pytest.fixture(params=CAPTURE_CASES)
def format_options(request):
    return request.param.format, request.param.options

# Run tests with one of the two supported raw formats
@pytest.fixture(params=('yuv', 'rgb', 'rgba', 'bgr', 'bgra'))
def raw_format(request):
    return request.param

@pytest.fixture(params=(False, True))
def use_video_port(request):
    return request.param


def test_capture_to_file(
        camera, previewing, mode, filename_format_options, use_video_port):
    filename, format, options = filename_format_options
    resolution, framerate = mode
    #if resolution == (2592, 1944) and format == 'gif' and not use_video_port:
    #    pytest.xfail('Camera runs out of memory with this combination')
    #if resolution == (2592, 1944) and 'resize' in options:
    #    pytest.xfail('Camera runs out of memory with this combination')
    camera.capture(filename, use_video_port=use_video_port, **options)
    if 'resize' in options:
        resolution = options['resize']
    verify_image(filename, format, resolution)

def test_capture_to_stream(
        camera, previewing, mode, format_options, use_video_port):
    stream = io.BytesIO()
    format, options = format_options
    resolution, framerate = mode
    #if resolution == (2592, 1944) and format == 'gif' and not use_video_port:
    #    pytest.xfail('Camera runs out of memory with this combination')
    #if resolution == (2592, 1944) and 'resize' in options:
    #    pytest.xfail('Camera runs out of memory with this combination')
    if 'resize' in options:
        resolution = options['resize']
    camera.capture(stream, format, use_video_port=use_video_port, **options)
    stream.seek(0)
    verify_image(stream, format, resolution)

def test_capture_continuous_to_file(
        camera, previewing, mode, tmpdir, use_video_port):
    resolution, framerate = mode
    for i, filename in enumerate(
            camera.capture_continuous(os.path.join(
                str(tmpdir), 'image{counter:02d}.jpg'),
                use_video_port=use_video_port)):
        verify_image(filename, 'jpeg', resolution)
        if i == 3:
            break

def test_capture_continuous_to_stream(
        camera, previewing, mode, use_video_port):
    resolution, framerate = mode
    stream = io.BytesIO()
    for i, foo in enumerate(
            camera.capture_continuous(stream, format='jpeg',
                use_video_port=use_video_port)):
        stream.truncate()
        stream.seek(0)
        verify_image(stream, 'jpeg', resolution)
        stream.seek(0)
        if i == 3:
            break

def test_capture_sequence_to_file(
        camera, previewing, mode, tmpdir, use_video_port):
    resolution, framerate = mode
    filenames = [os.path.join(str(tmpdir), 'image%d.jpg' % i) for i in range(3)]
    camera.capture_sequence(filenames, use_video_port=use_video_port)
    for filename in filenames:
        verify_image(filename, 'jpeg', resolution)

def test_capture_sequence_to_stream(
        camera, previewing, mode, use_video_port):
    resolution, framerate = mode
    streams = [io.BytesIO() for i in range(3)]
    camera.capture_sequence(streams, use_video_port=use_video_port)
    for stream in streams:
        stream.seek(0)
        verify_image(stream, 'jpeg', resolution)

def test_capture_raw(camera, mode, raw_format, use_video_port):
    resolution, framerate = mode
    if resolution == (2592, 1944) and raw_format in ('rgba', 'bgra') and not use_video_port:
        pytest.xfail('Camera runs out of memory with this combination')
    if resolution == (2592, 1944) and raw_format in ('rgb', 'bgr'):
        pytest.xfail('Camera times out with this combination')
    stream = io.BytesIO()
    camera.capture(stream, format=raw_format, use_video_port=use_video_port)
    verify_raw(stream, raw_format, resolution)

def test_capture_continuous_raw(camera, mode, raw_format, use_video_port):
    resolution, framerate = mode
    if resolution == (2592, 1944) and raw_format in ('rgba', 'bgra') and not use_video_port:
        pytest.xfail('Camera runs out of memory with this combination')
    if resolution == (2592, 1944) and raw_format in ('rgb', 'bgr'):
        pytest.xfail('Camera times out with this combination')
    for i, stream in enumerate(camera.capture_continuous(
            io.BytesIO(), format=raw_format, use_video_port=use_video_port)):
        if i == 3:
            break
        verify_raw(stream, raw_format, resolution)
        stream.seek(0)
        stream.truncate()

def test_capture_sequence_raw(camera, mode, raw_format, use_video_port):
    resolution, framerate = mode
    if resolution == (2592, 1944) and raw_format in ('rgba', 'bgra') and not use_video_port:
        pytest.xfail('Camera runs out of memory with this combination')
    if resolution == (2592, 1944) and raw_format in ('rgb', 'bgr'):
        pytest.xfail('Camera times out with this combination')
    streams = [io.BytesIO() for i in range(3)]
    camera.capture_sequence(streams, format=raw_format, use_video_port=use_video_port)
    for stream in streams:
        verify_raw(stream, raw_format, resolution)

def test_capture_bayer(camera, mode):
    stream = io.BytesIO()
    camera.capture(stream, format='jpeg', bayer=True)
    # Bayer data is always the last 6404096 bytes of the stream, and starts
    # with 'BRCM'
    stream.seek(-6404096, io.SEEK_END)
    assert stream.read(4) == 'BRCM'

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

