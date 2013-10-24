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

# A variant on the camera fixture which returns a camera with preview running
@pytest.fixture(scope='module')
def camera_p(request, camera):
    camera.start_preview()
    def fin():
        camera.stop_preview()
    request.addfinalizer(fin)
    return camera

# A variant on the camera fixture which returns the camera both in previewing
# and non-previewing states (for things which ought to be tested in both
# states)
@pytest.fixture(scope='module', params=(False, True))
def camera_b(request, camera):
    if request.param and not camera.previewing:
        camera.start_preview()
    if not request.param and camera.previewing:
        camera.stop_preview()
    def fin():
        if camera.previewing:
            camera.stop_preview()
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

# Run tests with one of the two supported raw formats
@pytest.fixture(scope='module', params=('yuv', 'rgb'))
def raw_format(request, camera):
    was_previewing = camera.previewing
    if camera.previewing:
        camera.stop_preview()
    camera.raw_format = request.param
    if was_previewing:
        camera.start_preview()
    return request.param

# Run tests with a variety of file suffixes and expected formats
@pytest.fixture(scope='module', params=(
    ('.jpg', 'JPEG', (('quality', 95),)),
    ('.jpg', 'JPEG', ()),
    ('.jpg', 'JPEG', (('quality', 50),)),
    ('.gif', 'GIF',  ()),
    ('.png', 'PNG',  ()),
    ('.bmp', 'BMP',  ()),
    ))
def filename_format_options(request):
    suffix, format, options = request.param
    filename = tempfile.mkstemp(suffix=suffix)[1]
    def fin():
        os.unlink(filename)
    request.addfinalizer(fin)
    return filename, format, dict(options)

# Run tests with a variety of format specs
@pytest.fixture(scope='module', params=(
    ('jpeg', (('quality', 95),)),
    ('jpeg', ()),
    ('jpeg', (('quality', 50),)),
    ('gif',  ()),
    ('png',  ()),
    ('bmp',  ()),
    ))
def format_options(request):
    format, options = request.param
    return format, dict(options)

