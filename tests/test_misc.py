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

def test_dual_camera(camera):
    with pytest.raises(picamera.PiCameraError):
        another_camera = picamera.PiCamera()

