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
import tempfile
import picamera
import pytest
from collections import namedtuple


TestCase = namedtuple('TestCase', ('format', 'ext', 'options'))

TEST_CASES = (
    TestCase('h264',  '.h264', {'profile': 'baseline'}),
    TestCase('h264',  '.h264', {'profile': 'main'}),
    TestCase('h264',  '.h264', {'profile': 'high'}),
    TestCase('h264',  '.h264', {'profile': 'constrained'}),
    TestCase('h264',  '.h264', {'bitrate': 0, 'quantization': 10}),
    TestCase('h264',  '.h264', {'bitrate': 0, 'quantization': 20}),
    TestCase('h264',  '.h264', {'bitrate': 0, 'quantization': 30}),
    TestCase('h264',  '.h264', {'bitrate': 0, 'quantization': 40}),
    TestCase('h264',  '.h264', {'bitrate': 10000000, 'intra_period': 15}),
    TestCase('h264',  '.h264', {'bitrate': 10000000, 'inline_headers': False}),
    TestCase('h264',  '.h264', {'bitrate': 15000000}),
    TestCase('h264',  '.h264', {'bitrate': 20000000, 'profile': 'main'}),
    TestCase('mjpeg', '.mjpg', {}),
    TestCase('mjpeg', '.mjpg', {'bitrate': 10000000}),
    TestCase('mjpeg', '.mjpg', {'bitrate': 0, 'quantization': 20}),
    )


@pytest.fixture(scope='module', params=TEST_CASES)
def filenames_format_options(request):
    filename1 = tempfile.mkstemp(suffix=request.param.ext)[1]
    filename2 = tempfile.mkstemp(suffix=request.param.ext)[1]
    def fin():
        os.unlink(filename1)
        os.unlink(filename2)
    request.addfinalizer(fin)
    return filename1, filename2, request.param.format, request.param.options

# Run tests with a variety of format specs
@pytest.fixture(scope='module', params=TEST_CASES)
def format_options(request):
    return request.param.format, request.param.options


# TODO We don't yet test that the recordings are actually valid in any way, so
# at the moment this is little more than making sure exceptions don't occur

def test_record_to_file(camera, previewing, resolution, filenames_format_options):
    if resolution == (2592, 1944):
        pytest.xfail('Cannot encode video at max resolution')
    filename1, filename2, format, options = filenames_format_options
    camera.start_recording(filename1, **options)
    try:
        camera.wait_recording(1)
        if format == 'h264' and not (options.get('inline_headers', True) and options.get('bitrate', 1)):
            with pytest.raises(picamera.PiCameraRuntimeError):
                camera.split_recording(filename2)
        else:
            camera.split_recording(filename2)
            camera.wait_recording(1)
    finally:
        camera.stop_recording()
    # TODO verify the files

def test_record_to_stream(camera, previewing, resolution, format_options):
    if resolution == (2592, 1944):
        pytest.xfail('Cannot encode video at max resolution')
    format, options = format_options
    stream1 = io.BytesIO()
    stream2 = io.BytesIO()
    camera.start_recording(stream1, format, **options)
    try:
        camera.wait_recording(1)
        if format == 'h264' and not (options.get('inline_headers', True) and options.get('bitrate', 1)):
            with pytest.raises(picamera.PiCameraRuntimeError):
                camera.split_recording(stream2)
        else:
            camera.split_recording(stream2)
            camera.wait_recording(1)
    finally:
        camera.stop_recording()
    stream1.seek(0)
    stream2.seek(0)
    # TODO verify the stream

