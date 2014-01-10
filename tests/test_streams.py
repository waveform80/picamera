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
import pytest
from picamera.streams import CircularIO


def test_circular_io():
    with pytest.raises(ValueError):
        CircularIO(-1)
    stream = CircularIO(10)
    assert stream.readable()
    assert stream.writable()
    assert stream.seekable()
    assert stream.size == 10
    assert stream.tell() == 0
    stream.write(b'')
    assert stream.tell() == 0
    assert stream.getvalue() == b''
    stream.write(b'abc')
    assert stream.getvalue() == b'abc'
    assert stream.tell() == 3
    stream.write(b'def')
    assert stream.getvalue() == b'abcdef'
    assert stream.tell() == 6
    stream.write(b'ghijklm')
    assert stream.getvalue() == b'defghijklm'
    stream.seek(0)
    assert stream.read(1) == b'd'
    assert stream.read(4) == b'efgh'
    assert stream.read() == b'ijklm'
    assert stream.tell() == 10
    stream.seek(0)
    assert stream.read() == stream.getvalue()
    stream.seek(0)
    assert stream.tell() == 0
    stream.write(b'')
    assert stream.getvalue() == b'defghijklm'
    assert stream.tell() == 0
    stream.write(b'a')
    assert stream.getvalue() == b'aefghijklm'
    assert stream.tell() == 1
    stream.write(b'bcd')
    assert stream.getvalue() == b'abcdhijklm'
    assert stream.tell() == 4
    stream.seek(0)
    assert stream.tell() == 0
    stream.write(b'efghijklmnop')
    assert stream.getvalue() == b'ghijklmnop'
    assert stream.tell() == 10
    assert stream.seek(-1, io.SEEK_CUR) == 9
    assert stream.seek(0, io.SEEK_END) == 10
    with pytest.raises(ValueError):
        stream.seek(-1)
    stream.seek(15)
    assert stream.tell() == 15
    stream.write(b'qrs')
    assert stream.getvalue() == b'op\x00\x00\x00\x00\x00qrs'
    assert stream.tell() == 10
    with pytest.raises(ValueError):
        stream.truncate(-1)
    stream.seek(4)
    stream.truncate()
    assert stream.getvalue() == b'op\x00\x00'
    assert stream.tell() == 4
    stream.write(b'tuv')
    stream.write(b'wxyz')
    assert stream.getvalue() == b'p\x00\x00tuvwxyz'
    assert stream.tell() == 10
    stream.truncate(5)
    assert stream.getvalue() == b'p\x00\x00tu'
    assert stream.tell() == 10
    stream.write(b'')
    assert stream.getvalue() == b'p\x00\x00tu\x00\x00\x00\x00\x00'
    assert stream.tell() == 10

