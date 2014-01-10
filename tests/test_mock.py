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

import ctypes as ct
import picamera.mmal as mmal
import picamera
import pytest
import mock

def test_camera_init():
    with \
            mock.patch('picamera.camera.bcm_host') as bcm_host, \
            mock.patch('picamera.camera.mmal') as mmal, \
            mock.patch('picamera.camera.ct') as ct:
        mmal.mmal_component_create.return_value = 1
        with pytest.raises(picamera.PiCameraError) as e:
            picamera.PiCamera()
        assert e.value.args[0].startswith("Failed to create camera component")
        mmal.mmal_component_create.return_value = 0
        ct.POINTER.return_value.return_value[0].output_num = 0
        ct.sizeof.return_value = 0
        with pytest.raises(picamera.PiCameraError) as e:
            picamera.PiCamera()
        assert e.value.args[0] == "Camera doesn't have output ports"
        ct.POINTER.return_value.return_value[0].output_num = 3
        mmal.mmal_port_enable.return_value = 1
        with pytest.raises(picamera.PiCameraError) as e:
            picamera.PiCamera()
        assert e.value.args[0].startswith("Unable to enable control port")
        mmal.mmal_port_enable.return_value = 0
        mmal.mmal_port_parameter_set.return_value = 1
        with pytest.raises(picamera.PiCameraError) as e:
            picamera.PiCamera()
        assert e.value.args[0].startswith("Camera control port couldn't be configured")
        mmal.mmal_port_parameter_set.return_value = 0
        mmal.mmal_port_format_commit.return_value = 0
        for p in picamera.PiCamera.CAMERA_PORTS:
            ct.POINTER.return_value.return_value[0].output[p][0].buffer_num = 1
        mmal.mmal_component_enable.return_value = 1
        with pytest.raises(picamera.PiCameraError) as e:
            picamera.PiCamera()
        assert e.value.args[0].startswith("Camera component couldn't be enabled")

def test_camera_led():
    with mock.patch('picamera.camera.GPIO') as GPIO:
        with picamera.PiCamera() as camera:
            camera.led = True
            GPIO.setmode.assert_called_once_with(GPIO.BCM)
            GPIO.setup.assert_called_once_with(5, GPIO.OUT, initial=GPIO.LOW)
            GPIO.output.assert_called_with(5, True)
            camera.led = False
            GPIO.output.assert_called_with(5, False)
            with pytest.raises(AttributeError):
                camera.led
