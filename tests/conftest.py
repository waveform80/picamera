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
    was_previewing = camera.previewing
    if was_previewing:
        camera.stop_preview()
    camera.resolution = request.param
    if was_previewing:
        camera.start_preview()
    def fin():
        was_previewing = camera.previewing
        if was_previewing:
            camera.stop_preview()
        camera.resolution = save_resolution
        if was_previewing:
            camera.start_preview()
    return request.param

# Run tests with one of the two supported raw formats
@pytest.fixture(scope='module', params=('yuv', 'rgb'))
def raw_format(request, camera):
    save_format = camera.raw_format
    was_previewing = camera.previewing
    if was_previewing:
        camera.stop_preview()
    camera.raw_format = request.param
    if was_previewing:
        camera.start_preview()
    def fin():
        was_previewing = camera.previewing
        if was_previewing:
            camera.stop_preview()
        camera.raw_format = save_format
        if was_previewing:
            camera.start_preview()
    request.addfinalizer(fin)
    return request.param

