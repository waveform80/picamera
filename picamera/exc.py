# vim: set et sw=4 sts=4 fileencoding=utf-8:
#
# Python camera library for the Rasperry-Pi camera module
# Copyright (c) 2013-2015 Dave Jones <dave@waveform.org.uk>
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

"""
This module defines the exceptions used by picamera. All exception classes
utilize multiple inheritance in order to make testing for exception types more
intuitive. For example, :exc:`PiCameraValueError` derives from both
:exc:`PiCameraError` and :exc:`ValueError`. Hence it will be caught by blocks
intended to catch any error specific to the picamera library::

    try:
        camera.brightness = int(some_user_value)
    except PiCameraError:
        print('Something went wrong with the camera')

Or by blocks intended to catch value errors::

    try:
        camera.contrast = int(some_user_value)
    except ValueError:
        print('Invalid value')

.. note::

    All classes in this module are available from the :mod:`picamera` namespace
    without having to import :mod:`picamera.streams` directly.

The following classes are defined in the module:


.. autoexception:: PiCameraWarning

.. autoexception:: PiCameraDeprecated

.. autoexception:: PiCameraFallback

.. autoexception:: PiCameraError

.. autoexception:: PiCameraValueError

.. autoexception:: PiCameraRuntimeError

.. autoexception:: PiCameraClosed

.. autoexception:: PiCameraNotRecording

.. autoexception:: PiCameraAlreadyRecording

.. autoexception:: PiCameraMMALError

.. autofunction:: mmal_check

"""

from __future__ import (
    unicode_literals,
    print_function,
    division,
    absolute_import,
    )

# Make Py2's str equivalent to Py3's
str = type('')


import picamera.mmal as mmal


class PiCameraWarning(Warning):
    """
    Base class for PiCamera warnings.
    """


class PiCameraDeprecated(PiCameraWarning, DeprecationWarning):
    """
    Raised when deprecated functionality in picamera is used.
    """


class PiCameraFallback(PiCameraWarning, RuntimeWarning):
    """
    Raised when picamera has to fallback on old functionality.
    """


class PiCameraError(Exception):
    """
    Base class for PiCamera errors.
    """


class PiCameraRuntimeError(PiCameraError, RuntimeError):
    """
    Raised when an invalid sequence of operations is attempted with a
    :class:`~picamera.camera.PiCamera` object.
    """


class PiCameraClosed(PiCameraRuntimeError):
    """
    Raised when a method is called on a camera which has already been closed.
    """


class PiCameraNotRecording(PiCameraRuntimeError):
    """
    Raised when :meth:`~picamera.camera.PiCamera.stop_recording` or
    :meth:`~picamera.camera.PiCamera.split_recording` are called against a port
    which has no recording active.
    """


class PiCameraAlreadyRecording(PiCameraRuntimeError):
    """
    Raised when :meth:`~picamera.camera.PiCamera.start_recording` or
    :meth:`~picamera.camera.PiCamera.record_sequence` are called against a port
    which already has an active recording.
    """


class PiCameraValueError(PiCameraError, ValueError):
    """
    Raised when an invalid value is fed to a :class:`~picamera.camera.PiCamera`
    object.
    """


class PiCameraMMALError(PiCameraError):
    """
    Raised when an MMAL operation fails for whatever reason.
    """
    def __init__(self, status, prefix=""):
        self.status = status
        PiCameraError.__init__(self, "%s%s%s" % (prefix, ": " if prefix else "", {
            mmal.MMAL_ENOMEM:    "Out of memory",
            mmal.MMAL_ENOSPC:    "Out of resources (other than memory)",
            mmal.MMAL_EINVAL:    "Argument is invalid",
            mmal.MMAL_ENOSYS:    "Function not implemented",
            mmal.MMAL_ENOENT:    "No such file or directory",
            mmal.MMAL_ENXIO:     "No such device or address",
            mmal.MMAL_EIO:       "I/O error",
            mmal.MMAL_ESPIPE:    "Illegal seek",
            mmal.MMAL_ECORRUPT:  "Data is corrupt #FIXME not POSIX",
            mmal.MMAL_ENOTREADY: "Component is not ready #FIXME not POSIX",
            mmal.MMAL_ECONFIG:   "Component is not configured #FIXME not POSIX",
            mmal.MMAL_EISCONN:   "Port is already connected",
            mmal.MMAL_ENOTCONN:  "Port is disconnected",
            mmal.MMAL_EAGAIN:    "Resource temporarily unavailable; try again later",
            mmal.MMAL_EFAULT:    "Bad address",
            }.get(status, "Unknown status error")))


def mmal_check(status, prefix=""):
    """
    Checks the return status of an mmal call and raises an exception on
    failure.

    The *status* parameter is the result of an MMAL call. If *status* is
    anything other than MMAL_SUCCESS, a :exc:`PiCameraMMALError` exception is
    raised. The optional *prefix* parameter specifies a prefix message to place
    at the start of the exception's message to provide some context.
    """
    if status != mmal.MMAL_SUCCESS:
        raise PiCameraMMALError(status, prefix)

