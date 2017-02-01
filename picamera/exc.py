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


class PiCameraResizerEncoding(PiCameraWarning, RuntimeWarning):
    """
    Raised when picamera uses a resizer purely for encoding purposes.
    """


class PiCameraAlphaStripping(PiCameraWarning, RuntimeWarning):
    """
    Raised when picamera does alpha-byte stripping.
    """


class PiCameraResolutionRounded(PiCameraWarning, RuntimeWarning):
    """
    Raised when picamera has to round a requested frame size upward.
    """


class PiCameraError(Exception):
    """
    Base class for PiCamera errors.
    """


class PiCameraRuntimeError(PiCameraError, RuntimeError):
    """
    Raised when an invalid sequence of operations is attempted with a
    :class:`PiCamera` object.
    """


class PiCameraClosed(PiCameraRuntimeError):
    """
    Raised when a method is called on a camera which has already been closed.
    """


class PiCameraNotRecording(PiCameraRuntimeError):
    """
    Raised when :meth:`~PiCamera.stop_recording` or
    :meth:`~PiCamera.split_recording` are called against a port which has no
    recording active.
    """


class PiCameraAlreadyRecording(PiCameraRuntimeError):
    """
    Raised when :meth:`~PiCamera.start_recording` or
    :meth:`~PiCamera.record_sequence` are called against a port which already
    has an active recording.
    """


class PiCameraValueError(PiCameraError, ValueError):
    """
    Raised when an invalid value is fed to a :class:`~PiCamera` object.
    """


class PiCameraIOError(PiCameraError, IOError):
    """
    Raised when a :class:`~PiCamera` object is unable to perform an IO
    operation.
    """


class PiCameraMMALError(PiCameraError):
    """
    Raised when an MMAL operation fails for whatever reason.
    """
    def __init__(self, status, prefix=""):
        self.status = status
        PiCameraError.__init__(self, "%s%s%s" % (prefix, ": " if prefix else "", {
            mmal.MMAL_ENOMEM:    "Out of memory",
            mmal.MMAL_ENOSPC:    "Out of resources",
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


class PiCameraPortDisabled(PiCameraMMALError):
    """
    Raised when attempting a buffer operation on a disabled port.

    This exception is intended for the common use-case of attempting to get
    or send a buffer just when a component is shutting down (e.g. at script
    teardown) and simplifies the trivial response (ignore the error and shut
    down quietly). For example::

        def _callback(self, port, buf):
            try:
                buf = self.outputs[0].get_buffer(False)
            except PiCameraPortDisabled:
                return True # shutting down
            # ...
    """
    def __init__(self, msg):
        super(PiCameraPortDisabled, self).__init__(mmal.MMAL_EINVAL, msg)


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

