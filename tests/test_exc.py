from __future__ import (
    unicode_literals,
    print_function,
    division,
    absolute_import,
    )

# Make Py2's str equivalent to Py3's
str = type('')

from picamera import mmal
from picamera.exc import mmal_check, PiCameraError
import pytest

def test_mmal_check():
    mmal_check(mmal.MMAL_SUCCESS)
    with pytest.raises(PiCameraError):
        mmal_check(mmal.MMAL_ENOSYS)
    with pytest.raises(PiCameraError):
        mmal_check(mmal.MMAL_ENOMEM)
    with pytest.raises(PiCameraError):
        mmal_check(mmal.MMAL_ENOSPC)
    with pytest.raises(PiCameraError):
        mmal_check(mmal.MMAL_EINVAL)
