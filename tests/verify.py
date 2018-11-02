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
import io
import re
import math
import struct
import subprocess
from PIL import Image


FFMPEG = os.environ.get('PICAMERA_FFMPEG', 'ffmpeg')

RAW_FORMATS = {
    # name   bytes-per-pixel
    'yuv':  1.5,
    'rgb':  3,
    'rgba': 4,
    'bgr':  3,
    'bgra': 4,
    }

# From http://www.w3.org/Graphics/JPEG/itu-t81.pdf
JPEG_MARKERS = {
    b'\x00': (0,  'PAD'),   # byte stuffing in entropy coded data
    b'\xff': (0,  'PAD'),   # padding
    b'\xc0': (-1, 'SOF0'),  # start of frame (baseline)
    b'\xc1': (-1, 'SOF1'),  # start of frame (extended sequential)
    b'\xc2': (-1, 'SOF2'),  # start of frame (progressive)
    b'\xc3': (-1, 'SOF3'),  # start of frame (spatial lossless)
    b'\xc4': (-1, 'DHT'),   # define huffman tables
    b'\xc5': (-1, 'SOF5'),  # start of frame (differential sequential)
    b'\xc6': (-1, 'SOF6'),  # start of frame (differential progressive)
    b'\xc7': (-1, 'SOF7'),  # start of frame (differential spatial)
    b'\xc8': (-1, 'JPG'),   # extension
    b'\xc9': (-1, 'SOF9'),  # start of frame (extended sequential, arithmetic coding)
    b'\xca': (-1, 'SOF10'), # start of frame (progressive, arithmetic coding)
    b'\xcb': (-1, 'SOF11'), # start of frame (spatial lossless, arithmetic coding)
    b'\xcc': (4,  'DAC'),   # define arithmetic coding conditioning
    b'\xcd': (-1, 'SOF13'), # start of frame (differential sequential, arithmetic coding)
    b'\xce': (-1, 'SOF14'), # start of frame (differential progressive, arithmetic coding)
    b'\xcf': (-1, 'SOF15'), # start of frame (differential spatial, arithmetic coding)
    b'\xd0': (0,  'RST0'),  # restart index 0
    b'\xd1': (0,  'RST1'),  # restart index 1
    b'\xd2': (0,  'RST2'),  # restart index 2
    b'\xd3': (0,  'RST3'),  # restart index 3
    b'\xd4': (0,  'RST4'),  # restart index 4
    b'\xd5': (0,  'RST5'),  # restart index 5
    b'\xd6': (0,  'RST6'),  # restart index 6
    b'\xd7': (0,  'RST7'),  # restart index 7
    b'\xd8': (0,  'SOI'),   # start of image
    b'\xd9': (0,  'EOI'),   # end of image
    b'\xda': (-1, 'SOS'),   # start of scan (followed by entropy-coded data)
    b'\xdb': (-1, 'DQT'),   # define quantization tables
    b'\xdc': (4,  'DNL'),   # define number of lines
    b'\xdd': (4,  'DRI'),   # define restart interval
    b'\xde': (-1, 'DHP'),   # define hierarchical progression
    b'\xdf': (4,  'EXP'),   # expand reference component
    b'\xe0': (-1, 'APP0'),  # app marker 0
    b'\xe1': (-1, 'APP1'),  # app marker 1
    b'\xe2': (-1, 'APP2'),  # app marker 2
    b'\xe3': (-1, 'APP3'),  # app marker 3
    b'\xe4': (-1, 'APP4'),  # app marker 4
    b'\xe5': (-1, 'APP5'),  # app marker 5
    b'\xe6': (-1, 'APP6'),  # app marker 6
    b'\xe7': (-1, 'APP7'),  # app marker 7
    b'\xe8': (-1, 'APP8'),  # app marker 8
    b'\xe9': (-1, 'APP9'),  # app marker 9
    b'\xea': (-1, 'APP10'), # app marker 10
    b'\xeb': (-1, 'APP11'), # app marker 11
    b'\xec': (-1, 'APP12'), # app marker 12
    b'\xed': (-1, 'APP13'), # app marker 13
    b'\xee': (-1, 'APP14'), # app marker 14
    b'\xef': (-1, 'APP15'), # app marker 15
    b'\xfe': (-1, 'COM'),   # comment
    }

def parse_jpeg(stream):
    # digraph G {
    #   start->markers
    #   markers->entropy
    #   markers->markers
    #   entropy->markers
    #   entropy->entropy
    #   markers->finish
    #   entropy->finish
    # }
    state = 'start'
    mark = stream.read(1)
    while True:
        if state == 'entropy':
            if mark != b'\xff':
                mark = stream.read(1)
                continue
        else:
            assert mark == b'\xff', 'marker byte is not FF'
        try:
            mark_len, mark_type = JPEG_MARKERS[stream.read(1)]
        except KeyError:
            assert False, 'invalid JPEG marker'
        if mark_len == -1:
            mark_len, = struct.unpack('>H', stream.read(2))
        elif mark_len > 0:
            check_len, = struct.unpack('>H', stream.read(2))
            assert mark_len == check_len, 'incorrect marker length'
        else:
            assert mark_len == 0, 'invalid marker length'
        if mark_len:
            mark_data = stream.read(mark_len - 2)
        else:
            mark_data = b''
        if state == 'start':
            assert mark_type == 'SOI'
            state = 'markers'
        elif state == 'markers':
            if mark_type == 'SOS':
                state = 'entropy'
            elif mark_type == 'EOI':
                break
            else:
                pass
        elif state == 'entropy':
            if mark_type == 'PAD':
                pass
            elif mark_type == 'EOI':
                break
            else:
                state = 'markers'
        else:
            assert False, 'invalid state'
        mark = stream.read(1)


def verify_jpeg(stream, resolution):
    pos = stream.tell()
    image = Image.open(stream)
    # check PIL can read the JPEG and that the resolution is as expected
    assert image.size == resolution
    stream.seek(pos)
    # parse the JPEG manually, which also has the effect of seeking just past
    # the end of the JPEG (so if this is an MJPEG our next call will deal with
    # the next frame)
    parse_jpeg(stream)


def verify_video(filename_or_obj, format, resolution):
    """
    Verify that the video in filename_or_obj has the specified format and
    resolution.
    """
    width, height = resolution
    if format in RAW_FORMATS:
        size1 = (
                math.ceil(width / 16) * 16
                * math.ceil(height / 16) * 16
                * RAW_FORMATS[format]
                )
        size2 = (
                math.ceil(width / 32) * 32
                * math.ceil(height / 16) * 16
                * RAW_FORMATS[format]
                )
        if isinstance(filename_or_obj, str):
            stream = io.open(filename_or_obj, 'rb')
        else:
            stream = filename_or_obj
        stream.seek(0, os.SEEK_END)
        assert stream.tell() > 0
        # Check the stream size is an exact multiple of the one of the possible
        # frame sizes
        assert (stream.tell() % size1 == 0) or (stream.tell() % size2 == 0)
    elif format == 'mjpeg':
        if isinstance(filename_or_obj, str):
            f = io.open(filename_or_obj, 'rb')
        else:
            f = filename_or_obj
        pos = f.tell()
        f.seek(0, io.SEEK_END)
        f_end = f.tell()
        f.seek(pos)
        while f.tell() < f_end:
            verify_jpeg(f, resolution)
    elif format == 'h264':
        if isinstance(filename_or_obj, str):
            p = subprocess.Popen([
                FFMPEG,
                '-f', format,
                '-i', filename_or_obj,
                ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        else:
            p = subprocess.Popen([
                FFMPEG,
                '-f', format,
                '-i', '-',
                ], stdin=filename_or_obj, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        out = p.communicate()[0]
        assert p.returncode == 1, 'ffmpeg returned unexpected code %d' % p.returncode
        state = 'start'
        for line in out.splitlines():
            line = line.decode('utf-8').strip()
            if state == 'start' and re.match(r'^Input #0', line):
                state = 'input'
            elif state == 'input' and re.match(r'^Duration', line):
                state = 'dur'
            elif state == 'dur' and re.match(r'^Stream #0[.:]0', line):
                assert re.match(
                    r'^Stream #0[.:]0: '
                    r'Video: %s( \(.*\))?, '
                    r'yuvj?420p(\(progressive\))?, '
                    r'%dx%d( \[PAR \d+:\d+ DAR \d+:\d+\])?, '
                    r'\d+ fps(, \d+ tbr)?, \d+k? tbn(, \d+k? tbc)?$' % (
                        format, width, height),
                    line
                    ), 'Unexpected ffmpeg output: %s' % line
                return
            else:
                state = 'start'
        assert False, 'Failed to locate stream analysis in ffmpeg output'
    else:
        assert False, 'Unable to verify format %s' % format


def verify_image(filename_or_obj, format, resolution):
    """
    Verify that the image in filename_or_obj has the specified format and
    resolution.
    """
    width, height = resolution
    if format in RAW_FORMATS:
        size1 = (
                math.ceil(width / 16) * 16
                * math.ceil(height / 16) * 16
                * RAW_FORMATS[format]
                )
        size2 = (
                math.ceil(width / 32) * 32
                * math.ceil(height / 16) * 16
                * RAW_FORMATS[format]
                )
        if isinstance(filename_or_obj, str):
            stream = io.open(filename_or_obj, 'rb')
        else:
            stream = filename_or_obj
        stream.seek(0, os.SEEK_END)
        assert stream.tell() in (size1, size2)
    else:
        img = Image.open(filename_or_obj)
        assert img.size == resolution
        assert img.format.lower() == format.lower()
        img.verify()


# For comparison of floating point values. See PEP485 for more information.
try:
    from math import isclose
except ImportError:
    # Backported from https://github.com/PythonCHB/close_pep
    from math import isinf
    def isclose(a, b, rel_tol=1e-9, abs_tol=0.0):
        if rel_tol < 0.0 or abs_tol < 0.0:
            raise ValueError('error tolerances must be non-negative')
        if a == b:
            return True
        if isinf(a) or isinf(b):
            return False
        diff = abs(b - a)
        return (((diff <= abs(rel_tol * b)) or
                 (diff <= abs(rel_tol * a))) or
                 (diff <= abs_tol))

