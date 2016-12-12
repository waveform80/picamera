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

import picamera
import pytest
import tempfile
import shutil


# The basic camera fixture returns a camera which is not running a preview.
# This should be used for tests which cannot be run when a preview is active
@pytest.fixture(scope='function')
def camera(request):
    camera = picamera.PiCamera()
    def fin():
        camera.close()
    request.addfinalizer(fin)
    return camera

# Activates and deactivates preview mode to test things in both states
@pytest.fixture(params=(False, True))
def previewing(request, camera):
    if request.param and not camera.previewing:
        camera.start_preview()
    if not request.param and camera.previewing:
        camera.stop_preview()
    return request.param

# Run tests at a variety of resolutions (and aspect ratios, 1:1, 4:3, 16:9) and
# framerates (which dictate the input mode of the camera)
@pytest.fixture(params=(
    ((100, 100), 60),
    ((320, 240), 5),
    ((1280, 720), 30),
    ((1920, 1080), 24),
    ((2592, 1944), 15),
    ))
def mode(request, camera):
    save_resolution = camera.resolution
    save_framerate = camera.framerate
    new_resolution, new_framerate = request.param
    camera.resolution = new_resolution
    camera.framerate = new_framerate
    def fin():
        try:
            for port in camera._encoders:
                camera.stop_recording(splitter_port=port)
        finally:
            camera.resolution = save_resolution
            camera.framerate = save_framerate
    request.addfinalizer(fin)
    return (picamera.PiResolution(*new_resolution), new_framerate)

# A fixture for temporary directories which cleans them up immediately after
# usage (the built-in tmpdir fixture only cleans up after several test runs
# and with the number of picamera tests that now exist, that can easily fill
# the 16Gb SD card in the dev rig)
@pytest.fixture()
def tempdir(request):
    dirname = tempfile.mkdtemp()
    def fin():
        shutil.rmtree(dirname)
    request.addfinalizer(fin)
    return dirname

