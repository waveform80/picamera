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

import os
import time
import tempfile
import picamera
import pytest
from collections import namedtuple
from verify import verify_video, verify_image, RAW_FORMATS


RecordingCase = namedtuple('RecordingCase', ('format', 'ext', 'options'))

RECORDING_CASES = (
    RecordingCase('h264',  '.h264', {'profile': 'baseline'}),
    RecordingCase('h264',  '.h264', {'profile': 'high'}),
    RecordingCase('h264',  '.h264', {'resize': (640, 480)}),
    RecordingCase('h264',  '.h264', {'bitrate': 0, 'quality': 20}),
    RecordingCase('h264',  '.h264', {'bitrate': 1000000, 'quality': 40}),
    RecordingCase('h264',  '.h264', {'bitrate': 10000000, 'intra_period': 0}),
    RecordingCase('h264',  '.h264', {'bitrate': 10000000, 'intra_period': 15}),
    RecordingCase('h264',  '.h264', {'bitrate': 10000000, 'inline_headers': False}),
    RecordingCase('h264',  '.h264', {'bitrate': 10000000, 'sei': True}),
    RecordingCase('h264',  '.h264', {'bitrate': 15000000}),
    RecordingCase('h264',  '.h264', {'bitrate': 20000000, 'profile': 'main'}),
    RecordingCase('mjpeg', '.mjpg', {}),
    RecordingCase('mjpeg', '.mjpg', {'bitrate': 10000000}),
    RecordingCase('mjpeg', '.mjpg', {'bitrate': 1000000}),
    ) + tuple(
    RecordingCase(fmt,     '.data', {})
    for fmt in RAW_FORMATS
    if not fmt.startswith('bgr')
    )


@pytest.fixture(params=RECORDING_CASES)
def filenames_format_options(request):
    filename1 = tempfile.mkstemp(suffix=request.param.ext)[1]
    filename2 = tempfile.mkstemp(suffix=request.param.ext)[1]
    def fin():
        os.unlink(filename1)
        os.unlink(filename2)
    request.addfinalizer(fin)
    return filename1, filename2, request.param.format, request.param.options


# Run tests with a variety of format specs
@pytest.fixture(params=RECORDING_CASES)
def format_options(request):
    return request.param.format, request.param.options


def expected_failures(resolution, format, options):
    if resolution == (2592, 1944) and 'resize' not in options:
        pytest.xfail('Cannot encode video at max resolution')
    if resolution.height > 1080 and format == 'mjpeg':
        pytest.xfail('Locks up camera')
    if resolution.height >= 1080 and format.startswith('rgb'):
        pytest.xfail('Split point often times out due to excessive IO delays')


def test_record_to_file(camera, previewing, mode, filenames_format_options):
    filename1, filename2, format, options = filenames_format_options
    resolution, framerate = mode
    expected_failures(resolution, format, options)
    camera.start_recording(
            filename1,
            # Check that in the case of cooked formats, capture correctly
            # derives the format from the extension
            format=format if format in RAW_FORMATS else None,
            **options)
    try:
        camera.wait_recording(1)
        verify2 = (
                format != 'h264' or (
                    options.get('inline_headers', True) and
                    options.get('intra_period', 1)
                    )
                )
        if verify2:
            camera.split_recording(filename2)
            camera.wait_recording(1)
        else:
            with pytest.raises(picamera.PiCameraRuntimeError):
                camera.split_recording(filename2)
    finally:
        camera.stop_recording()
    if 'resize' in options:
        resolution = options['resize']
    verify_video(filename1, format, resolution)
    if verify2:
        verify_video(filename2, format, resolution)


def test_record_to_stream(camera, previewing, mode, format_options):
    format, options = format_options
    resolution, framerate = mode
    expected_failures(resolution, format, options)
    stream1 = tempfile.SpooledTemporaryFile()
    stream2 = tempfile.SpooledTemporaryFile()
    camera.start_recording(stream1, format, **options)
    try:
        camera.wait_recording(1)
        verify2 = (
                format != 'h264' or (
                    options.get('inline_headers', True) and
                    options.get('intra_period', 1)
                    )
                )
        if verify2:
            camera.split_recording(stream2)
            camera.wait_recording(1)
        else:
            with pytest.raises(picamera.PiCameraRuntimeError):
                camera.split_recording(stream2)
    finally:
        camera.stop_recording()
    stream1.seek(0)
    if 'resize' in options:
        resolution = options['resize']
    verify_video(stream1, format, resolution)
    if verify2:
        stream2.seek(0)
        verify_video(stream2, format, resolution)


def test_record_sequence_to_file(camera, mode, tempdir):
    resolution, framerate = mode
    expected_failures(resolution, 'h264', {})
    filenames = [os.path.join(tempdir, 'clip%d.h264' % i) for i in range(3)]
    for filename in camera.record_sequence(filenames):
        camera.wait_recording(1)
    for filename in filenames:
        verify_video(filename, 'h264', resolution)


def test_record_sequence_to_stream(camera, mode):
    resolution, framerate = mode
    expected_failures(resolution, 'h264', {})
    streams = [tempfile.SpooledTemporaryFile() for i in range(3)]
    for stream in camera.record_sequence(streams):
        camera.wait_recording(1)
    for stream in streams:
        stream.seek(0)
        verify_video(stream, 'h264', resolution)


def test_circular_record(camera, mode):
    resolution, framerate = mode
    expected_failures(resolution, 'h264', {})
    stream = picamera.PiCameraCircularIO(camera, seconds=4)
    camera.start_recording(stream, format='h264')
    try:
        # Keep recording until the stream is definitely full and starts
        # removing earlier bits, or until 20 seconds
        start = time.time()
        while stream._length < stream._size and time.time() - start < 20:
            camera.wait_recording(1)
        # Record one more second, then test the result
        camera.wait_recording(1)
    finally:
        camera.stop_recording()
    temp = tempfile.SpooledTemporaryFile()
    for frame in stream.frames:
        if frame.header:
            stream.seek(frame.position)
            break
    while True:
        buf = stream.read1()
        if not buf:
            break
        temp.write(buf)
    temp.seek(0)
    verify_video(temp, 'h264', resolution)


def test_split_and_capture(camera, mode):
    resolution, framerate = mode
    expected_failures(resolution, 'h264', {})
    v_stream1 = tempfile.SpooledTemporaryFile()
    v_stream2 = tempfile.SpooledTemporaryFile()
    c_stream1 = tempfile.SpooledTemporaryFile()
    camera.start_recording(v_stream1, format='h264')
    try:
        camera.wait_recording(1)
        camera.capture(c_stream1, format='jpeg', use_video_port=True)
        camera.split_recording(v_stream2)
        camera.wait_recording(1)
    finally:
        camera.stop_recording()
    v_stream1.seek(0)
    v_stream2.seek(0)
    c_stream1.seek(0)
    verify_image(c_stream1, 'jpeg', resolution)
    verify_video(v_stream1, 'h264', resolution)
    verify_video(v_stream2, 'h264', resolution)


def test_multi_res_record(camera, mode):
    resolution, framerate = mode
    expected_failures(resolution, 'h264', {})
    v_stream1 = tempfile.SpooledTemporaryFile()
    v_stream2 = tempfile.SpooledTemporaryFile()
    new_res = (resolution[0] // 2, resolution[1] // 2)
    camera.start_recording(v_stream1, format='h264')
    try:
        camera.start_recording(v_stream2, format='h264', resize=new_res, splitter_port=2)
        try:
            camera.wait_recording(1)
            camera.wait_recording(1, splitter_port=2)
        finally:
            camera.stop_recording()
    finally:
        # Deliberately stop out of order to test #105
        camera.stop_recording(splitter_port=2)
    v_stream1.seek(0)
    v_stream2.seek(0)
    verify_video(v_stream1, 'h264', resolution)
    verify_video(v_stream2, 'h264', new_res)


def test_macroblock_limit(camera):
    res, fps = camera.resolution, camera.framerate
    try:
        camera.resolution = '1080p'
        camera.framerate = 31
        with pytest.raises(picamera.PiCameraValueError):
            camera.start_recording(os.devnull, 'h264')
        camera.framerate_range = (15, 31)
        with pytest.raises(picamera.PiCameraValueError):
            camera.start_recording(os.devnull, 'h264')
    finally:
        camera.resolution = res
        camera.framerate = fps


def test_multi_res_record_len(camera, mode):

    class SizeTest(object):
        def __init__(self):
            self.size = 0
        def write(self, s):
            self.size += len(s)

    resolution, framerate = mode
    expected_failures(resolution, 'h264', {})
    output1 = SizeTest()
    output2 = SizeTest()
    camera.start_recording(output1, 'h264')
    try:
        camera.start_recording(output2, 'h264', splitter_port=2)
        try:
            camera.wait_recording(1)
        finally:
            camera.stop_recording(splitter_port=2)
        camera.wait_recording(1)
    finally:
        camera.stop_recording()
    # output1's size should be larger than output2's although given H.264 is
    # impressively efficient we really can't say by how much!
    assert output2.size > 0
    assert output1.size > output2.size


def test_motion_record(camera, mode):

    class MotionTest(object):
        def __init__(self, camera):
            width, height = camera.resolution
            self.rows = (height + 15) // 16
            self.cols = (width + 15) // 16
            self.cols += 1
        def write(self, s):
            assert len(s) == self.cols * self.rows * 4
            return len(s)

    resolution, framerate = mode
    expected_failures(resolution, 'h264', {})
    camera.start_recording(
            '/dev/null', format='h264',
            motion_output=MotionTest(camera))
    try:
        camera.wait_recording(1)
    finally:
        camera.stop_recording()


def test_record_bad_format(camera):
    with pytest.raises(picamera.PiCameraValueError):
        camera.start_recording('test.foo')
    with pytest.raises(picamera.PiCameraValueError):
        camera.start_recording('test.h264', format='foo')
    with pytest.raises(picamera.PiCameraValueError):
        camera.start_recording('test.mp4')
    with pytest.raises(picamera.PiCameraValueError):
        camera.start_recording('test.h264', format='mp4')


def test_record_bad_timestamp(camera):
    # Frame timestamps should be positive integers in all cases. Prior to #357
    # getting fixed a None timestamp (from a 0 PTS) would be followed by a
    # large negative timestamp (from an unrecognized TIME_UNKNOWN timestamp)

    class Timestamps(object):
        def __init__(self, camera):
            self.camera = camera
            self.timestamps = []
        def write(self, buf):
            self.timestamps.append(self.camera.frame.timestamp)

    output = Timestamps(camera)
    camera.start_recording(output, 'h264')
    camera.wait_recording(1)
    camera.stop_recording()
    for timestamp in output.timestamps:
        assert timestamp >= 0
