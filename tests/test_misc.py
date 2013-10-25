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

def test_dual_camera(camera):
    with pytest.raises(picamera.PiCameraError):
        another_camera = picamera.PiCamera()

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
        mmal.mmal_component_enable.return_value = 1
        with pytest.raises(picamera.PiCameraError) as e:
            picamera.PiCamera()
        assert e.value.args[0].startswith("Camera component couldn't be enabled")
        ct.POINTER.return_value.return_value[0].input_num = 0
        with pytest.raises(picamera.PiCameraError) as e:
            picamera.PiCamera()
        assert e.value.args[0] == "No input ports on preview component"
        mmal.mmal_port_parameter_set = mock.MagicMock(side_effect=[0, 1])
        with pytest.raises(picamera.PiCameraError) as e:
            picamera.PiCamera()
        assert e.value.args[0].startswith("Unable to set preview port parameters")

