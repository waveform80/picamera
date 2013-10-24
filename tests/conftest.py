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

# Run all tests while the camera is idle and while it's previewing
@pytest.fixture(scope='module', params=(False, True))
def camera(request):
    camera = picamera.PiCamera()
    if request.param:
        camera.start_preview()
    def fin():
        if camera.previewing:
            camera.stop_preview()
        camera.close()
    request.addfinalizer(fin)
    return camera

# Run tests at a variety of resolutions (and aspect ratios, 1:1, 4:3, 16:9)
@pytest.fixture(scope='module', params=(
    (100, 100),
    (320, 240),
    (1920, 1080),
    (2592, 1944),
    ))
def resolution(request, camera):
    was_previewing = camera.previewing
    if camera.previewing:
        camera.stop_preview()
    camera.resolution = request.param
    if was_previewing:
        camera.start_preview()
    return request.param

