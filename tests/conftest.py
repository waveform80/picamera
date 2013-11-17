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


# The basic camera fixture returns a camera which is not running a preview.
# This should be used for tests which cannot be run when a preview is active
@pytest.fixture(scope='module')
def camera(request):
    camera = picamera.PiCamera()
    def fin():
        camera.close()
    request.addfinalizer(fin)
    return camera

# Activates and deactivates preview mode to test things in both states
@pytest.fixture(scope='module', params=(False, True))
def previewing(request, camera):
    if request.param and not camera.previewing:
        camera.start_preview()
    if not request.param and camera.previewing:
        camera.stop_preview()
    def fin():
        if camera.previewing:
            camera.stop_preview()
    request.addfinalizer(fin)
    return request.param

# Run tests at a variety of resolutions (and aspect ratios, 1:1, 4:3, 16:9)
@pytest.fixture(scope='module', params=(
    (100, 100),
    (320, 240),
    (1920, 1080),
    (2592, 1944),
    ))
def resolution(request, camera):
    save_resolution = camera.resolution
    camera.resolution = request.param
    def fin():
        camera.resolution = save_resolution
    request.addfinalizer(fin)
    return request.param

