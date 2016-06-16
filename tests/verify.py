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

import os
import io
import re
import math
import subprocess
from PIL import Image


RAW_FORMATS = {
    # name   bytes-per-pixel
    'yuv':  1.5,
    'rgb':  3,
    'rgba': 4,
    'bgr':  3,
    'bgra': 4,
    }


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
    else:
        if isinstance(filename_or_obj, str):
            p = subprocess.Popen([
                'avconv',
                '-f', format,
                '-i', filename_or_obj,
                ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        else:
            p = subprocess.Popen([
                'avconv',
                '-f', format,
                '-i', '-',
                ], stdin=filename_or_obj, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        out = p.communicate()[0]
        assert p.returncode == 1, 'avconv returned unexpected code %d' % p.returncode
        state = 'start'
        for line in out.splitlines():
            line = line.decode('utf-8').strip()
            if state == 'start' and re.match(r'^Input #0', line):
                state = 'input'
            elif state == 'input' and re.match(r'^Duration', line):
                state = 'dur'
            elif state == 'dur' and re.match(r'^Stream #0\.0', line):
                assert re.match(
                    r'^Stream #0\.0: '
                    r'Video: %s( \(.*\))?, '
                    r'yuvj?420p, '
                    r'%dx%d( \[PAR \d+:\d+ DAR \d+:\d+\])?, '
                    r'\d+ fps(, \d+ tbr)?, \d+k? tbn(, \d+k? tbc)?$' % (
                        format, width, height),
                    line
                    ), 'Unexpected avconv output: %s' % line
                return
        assert False, 'Failed to locate stream analysis in avconv output'


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

