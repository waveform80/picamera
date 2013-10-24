import picamera
import pytest

def test_dual_camera(camera):
    with pytest.raises(picamera.PiCameraError):
        another_camera = picamera.PiCamera()

