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
