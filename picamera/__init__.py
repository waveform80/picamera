# vim: set et sw=4 sts=4 fileencoding=utf-8:
#
# Python camera library for the Rasperry-Pi camera module
# Copyright (c) 2013,2014 Dave Hughes <dave@waveform.org.uk>
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
This package primarily provides the :class:`PiCamera` class which is a pure
Python interface to the Raspberry Pi's camera module. Various ancillary classes
are provided for usage with :class:`PiCamera` including :class:`PiVideoFrame`
(for holding video frame meta-data), :class:`PiCameraCircularIO` (for recording
video to a ring-buffer), :class:`PiEncoder` (an abstract base class for
camera encoders), and the concrete encoder classes: :class:`PiVideoEncoder`,
:class:`PiCookedOneImageEncoder`, :class:`PiCookedMultiImageEncoder`,
:class:`PiRawOneImageEncoder`, and :class:`PiRawMultiImageEncoder`.

.. note::

    In the documentation below several apparently "private" methods are
    documented (i.e. methods which have names beginning with an underscore).
    Most users can ignore these methods; they are intended for those developers
    that wish to override or extend the encoder implementations used by
    picamera.

    Some may question, given that these methods are intended to be overridden,
    why they are declared with a leading underscore (which in the Python idiom
    suggests that these methods are "private" to the class). In the cases where
    such methods are documented, the author intends these methods to have
    "protected" status (in the idiom of C++ and Object Pascal). That is to say,
    they are not intended to be used outside of the declaring class, but are
    intended to be accessible to, and overridden by, descendent classes.


PiCamera
========

.. autoclass:: PiCamera()
    :members:
    :private-members:


PiCameraCircularIO
==================

.. autoclass:: PiCameraCircularIO
    :members:


CircularIO
==========

.. autoclass:: CircularIO
    :members:


PiVideoFrameType
================

.. autoclass:: PiVideoFrameType
    :members:


PiVideoFrame
============

.. autoclass:: PiVideoFrame(index, frame_type, frame_size, video_size, split_size, timestamp)
    :members:


PiEncoder
=========

.. autoclass:: PiEncoder
    :members:
    :private-members:


PiVideoEncoder
==============

.. autoclass:: PiVideoEncoder
    :members:
    :private-members:


PiImageEncoder
==============

.. autoclass:: PiImageEncoder
    :members:
    :private-members:


PiOneImageEncoder
=================

.. autoclass:: PiOneImageEncoder
    :members:
    :private-members:


PiMultiImageEncoder
===================

.. autoclass:: PiMultiImageEncoder
    :members:
    :private-members:


PiRawEncoderMixin
=================

.. autoclass:: PiRawEncoderMixin
    :members:
    :private-members:


PiCookedOneImageEncoder
=======================

.. autoclass:: PiCookedOneImageEncoder
    :members:
    :private-members:


PiRawOneImageEncoder
====================

.. autoclass:: PiRawOneImageEncoder
    :members:
    :private-members:


PiCookedMultiImageEncoder
=========================

.. autoclass:: PiCookedMultiImageEncoder
    :members:
    :private-members:


PiRawMultiImageEncoder
======================

.. autoclass:: PiRawMultiImageEncoder
    :members:
    :private-members:


Exceptions
==========

.. autoexception:: PiCameraWarning

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

from picamera.exc import (
    PiCameraWarning,
    PiCameraError,
    PiCameraRuntimeError,
    PiCameraClosed,
    PiCameraNotRecording,
    PiCameraAlreadyRecording,
    PiCameraValueError,
    PiCameraMMALError,
    mmal_check,
    )
from picamera.camera import PiCamera
from picamera.encoders import (
    PiVideoFrame,
    PiVideoFrameType,
    PiEncoder,
    PiVideoEncoder,
    PiImageEncoder,
    PiOneImageEncoder,
    PiMultiImageEncoder,
    PiRawEncoderMixin,
    PiCookedOneImageEncoder,
    PiRawOneImageEncoder,
    PiCookedMultiImageEncoder,
    PiRawMultiImageEncoder,
    )
from picamera.streams import PiCameraCircularIO, CircularIO


