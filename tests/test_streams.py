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
import mock
try:
    from itertools import accumulate
except ImportError:
    def accumulate(iterable):
        it = iter(iterable)
        total = next(it)
        yield total
        for element in it:
            total += element
            yield total

import pytest
from picamera.encoders import PiVideoFrame, PiVideoFrameType
from picamera.streams import CircularIO, PiCameraCircularIO


def test_init():
    stream = CircularIO(10)
    assert stream.readable()
    assert stream.writable()
    assert stream.seekable()
    assert stream.size == 10
    assert stream.tell() == 0
    with pytest.raises(ValueError):
        CircularIO(-1)

def test_seek_tell():
    stream = CircularIO(10)
    assert stream.tell() == 0
    stream.write(b'defghijklm')
    assert stream.tell() == 10
    stream.seek(0)
    assert stream.tell() == 0
    stream.seek(4, io.SEEK_CUR)
    assert stream.tell() == 4
    stream.seek(0, io.SEEK_END)
    assert stream.tell() == 10
    with pytest.raises(ValueError):
        stream.seek(-20, io.SEEK_END)

def test_read():
    stream = CircularIO(10)
    stream.write(b'abcdef')
    stream.write(b'ghijklm')
    stream.seek(0)
    assert stream.read(1) == b'd'
    assert stream.read(4) == b'efgh'
    assert stream.read() == b'ijklm'
    assert stream.tell() == 10
    assert stream.read() == b''
    stream.seek(0)
    assert stream.read() == b'defghijklm'

def test_read1():
    stream = CircularIO(10)
    stream.write(b'abcdef')
    stream.write(b'ghijklm')
    stream.seek(0)
    assert stream.read1() == b'def'
    stream.seek(0)
    assert stream.read1(5) == b'def'
    assert stream.read1(3) == b'ghi'
    assert stream.read1() == b'jklm'
    assert stream.read1() == b''

def test_write():
    stream = CircularIO(10)
    stream.write(b'')
    assert stream.tell() == 0
    assert stream.getvalue() == b''
    stream.seek(2)
    stream.write(b'abc')
    assert stream.getvalue() == b'\x00\x00abc'
    assert stream.tell() == 5
    stream.write(b'def')
    assert stream.getvalue() == b'\x00\x00abcdef'
    assert stream.tell() == 8
    stream.write(b'ghijklm')
    assert stream.getvalue() == b'defghijklm'
    assert stream.tell() == 10
    stream.seek(1)
    stream.write(b'aaa')
    assert stream.getvalue() == b'daaahijklm'
    assert stream.tell() == 4
    stream.seek(-2, io.SEEK_END)
    stream.write(b'bbb')
    assert stream.tell() == 10
    assert stream.getvalue() == b'aaahijkbbb'

def test_truncate():
    stream = CircularIO(10)
    stream.write(b'abcdef')
    stream.write(b'ghijklm')
    stream.seek(8)
    stream.truncate()
    stream.seek(0, io.SEEK_END)
    assert stream.tell() == 8
    stream.seek(10)
    stream.truncate()
    stream.seek(8)
    assert stream.read() == b'\x00\x00'
    stream.truncate(4)
    stream.seek(0)
    assert stream.read() == b'defg'
    with pytest.raises(ValueError):
        stream.truncate(-1)

def generate_frames(s, index=0):
    # Generates a sequence of mock frame data and their corresponding
    # PiVideoFrame meta-data objects.
    pos = 0
    timestamp = 0
    for data in s:
        if data == 'k':
            pos += 1
            yield data.encode('ascii'), PiVideoFrame(
                index=index,
                frame_type=PiVideoFrameType.key_frame,
                frame_size=1,
                video_size=pos,
                split_size=pos,
                timestamp=timestamp,
                complete=False)
        pos += 1
        yield data.encode('ascii'), PiVideoFrame(
            index=index,
            frame_type={
                'f': PiVideoFrameType.frame,
                'k': PiVideoFrameType.key_frame,
                'h': PiVideoFrameType.sps_header,
                'm': PiVideoFrameType.motion_data,
                }[data],
            frame_size={
                'f': 1,
                'k': 2,
                'h': 1,
                'm': 1,
                }[data],
            video_size=pos,
            split_size=pos,
            timestamp=timestamp,
            complete=True)
        index += 1
        timestamp += 1000000

def test_camera_stream_init():
    camera = mock.Mock()
    encoder = mock.Mock()
    camera._encoders = {1: encoder}
    with pytest.raises(ValueError):
        PiCameraCircularIO(None, size=1)
    with pytest.raises(ValueError):
        PiCameraCircularIO(camera)
    with pytest.raises(ValueError):
        PiCameraCircularIO(camera, size=1, seconds=1)
    assert PiCameraCircularIO(camera, seconds=1, bitrate=1024).size == 1024 // 8

def test_camera_stream_frames():
    camera = mock.Mock()
    encoder = mock.Mock()
    camera._encoders = {1: encoder}
    stream = PiCameraCircularIO(camera, size=10)
    frames = []
    for data, frame in generate_frames('hkffkff'):
        encoder.frame = frame
        if frame.complete:
            frames.append(frame)
        stream.write(data)
    assert stream.getvalue() == b'hkkffkkff'
    assert list(stream.frames) == frames
    assert list(reversed(stream.frames)) == frames[::-1]

def test_camera_stream_frames_trunc_right():
    # We don't officially support this but the code should work if entire
    # frames are truncated (without leaving partial frame data) which is what
    # we're testing for here (of course, the resulting H.264 stream won't be
    # valid, but we're not testing that...)
    camera = mock.Mock()
    encoder = mock.Mock()
    camera._encoders = {1: encoder}
    stream = PiCameraCircularIO(camera, size=10)
    frames = []
    for data, frame in generate_frames('hkffkff'):
        encoder.frame = frame
        if frame.complete:
            frames.append(frame)
        stream.write(data)
    stream.seek(7)
    stream.truncate()
    del frames[-2:]
    assert stream.getvalue() == b'hkkffkk'
    assert list(stream.frames) == frames
    assert list(reversed(stream.frames)) == frames[::-1]

def test_camera_stream_frames_trunc_left():
    camera = mock.Mock()
    encoder = mock.Mock()
    camera._encoders = {1: encoder}
    stream = PiCameraCircularIO(camera, size=10)
    frames = []
    for data, frame in generate_frames('hkffkffhkff'):
        encoder.frame = frame
        if frame.complete:
            frames.append(frame)
        stream.write(data)
    del frames[:3]
    # As we've gotten rid of the start of the stream we need to re-calc the
    # video and split sizes in the comparison meta-data
    sizes = accumulate(f.frame_size for f in frames)
    frames = [
        PiVideoFrame(
            f.index,
            f.frame_type,
            f.frame_size,
            size,
            size,
            f.timestamp,
            f.complete
            )
        for f, size in zip(frames, sizes)
        ]
    assert stream.getvalue() == b'fkkffhkkff'
    assert list(stream.frames) == frames
    assert list(reversed(stream.frames)) == frames[::-1]

def test_camera_stream_clear():
    camera = mock.Mock()
    encoder = mock.Mock()
    camera._encoders = {1: encoder}
    stream = PiCameraCircularIO(camera, size=10)
    for data, frame in generate_frames('hkffkff'):
        encoder.frame = frame
        stream.write(data)
    stream.clear()
    assert stream.getvalue() == b''
    assert list(stream.frames) == []
    assert list(reversed(stream.frames)) == []

def test_camera_stream_copy_bad():
    camera = mock.Mock()
    encoder = mock.Mock()
    camera._encoders = {1: encoder}
    with pytest.raises(ValueError):
        PiCameraCircularIO(camera, size=10).copy_to('foo', size=1000, seconds=10)

def test_camera_stream_copy_all():
    camera = mock.Mock()
    encoder = mock.Mock()
    camera._encoders = {1: encoder}
    stream = PiCameraCircularIO(camera, size=10)
    for data, frame in generate_frames('hkffkff'):
        encoder.frame = frame
        stream.write(data)
    output = io.BytesIO()
    stream.copy_to(output)
    assert output.getvalue() == b'hkkffkkff'
    for data, frame in generate_frames('hkffkff'):
        encoder.frame = frame
        stream.write(data)
    assert stream.getvalue() == b'fhkkffkkff'
    output = io.BytesIO()
    stream.copy_to(output)
    assert output.getvalue() == b'hkkffkkff'

def test_camera_stream_copy_size():
    camera = mock.Mock()
    encoder = mock.Mock()
    camera._encoders = {1: encoder}
    stream = PiCameraCircularIO(camera, size=10)
    for data, frame in generate_frames('hkffkff'):
        encoder.frame = frame
        stream.write(data)
    output = io.BytesIO()
    stream.copy_to(output, size=5)
    assert output.getvalue() == b''
    stream.copy_to(output, size=10)
    assert output.getvalue() == b'hkkffkkff'

def test_camera_stream_copy_seconds():
    camera = mock.Mock()
    encoder = mock.Mock()
    camera._encoders = {1: encoder}
    stream = PiCameraCircularIO(camera, size=10)
    for data, frame in generate_frames('hkffkff'):
        encoder.frame = frame
        stream.write(data)
    output = io.BytesIO()
    stream.copy_to(output, seconds=1)
    assert output.getvalue() == b''
    stream.copy_to(output, seconds=10)
    assert output.getvalue() == b'hkkffkkff'

