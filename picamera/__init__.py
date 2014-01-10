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
Python interface to the Raspberry Pi's camera module.


PiCamera
========

.. autoclass:: PiCamera()
    :members:


PiCameraCircularIO
==================

.. autoclass:: PiCameraCircularIO
    :members:


CircularIO
==========

.. autoclass:: CircularIO
    :members:


PiVideoFrame
============

.. class:: PiVideoFrame(index, key, frame_size, video_size, split_size, timestamp)

    .. attribute:: index

        Returns the zero-based number of the frame. This is a monotonic counter
        that is simply incremented every time the camera returns a frame-end
        buffer. As a consequence, this attribute cannot be used to detect
        dropped frames.

    .. attribute:: position

        Returns the zero-based position of the frame in the stream containing
        it.

    .. attribute:: keyframe

        Returns a bool indicating whether the current frame is a keyframe (an
        intra-frame, or I-frame in MPEG parlance).

    .. attribute:: frame_size

        Returns the size in bytes of the current frame.

    .. attribute:: video_size

        Returns the size in bytes of the entire video up to the current frame.
        Note that this is unlikely to match the size of the actual file/stream
        written so far. Firstly this is because the frame attribute is only
        updated when the encoder outputs the *end* of a frame, which will cause
        the reported size to be smaller than the actual amount written.
        Secondly this is because a stream may utilize buffering which will
        cause the actual amount written (e.g. to disk) to lag behind the value
        reported by this attribute.

    .. attribute:: split_size

        Returns the size in bytes of the video recorded since the last call to
        either :meth:`~PiCamera.start_recording` or
        :meth:`~PiCamera.split_recording`. For the reasons explained above,
        this may differ from the size of the actual file/stream written so far.

    .. attribute:: timestamp

        Returns the presentation timestamp (PTS) of the current frame as
        reported by the encoder. This is represented by the number of
        microseconds (millionths of a second) since video recording started. As
        the frame attribute is only updated when the encoder outputs the end of
        a frame, this value may lag behind the actual time since
        :meth:`~PiCamera.start_recording` was called.

        .. warning::

            Currently, the video encoder occasionally returns "time unknown"
            values in this field which picamera represents as ``None``. If you
            are querying this property you will need to check the value is not
            ``None`` before using it.

    .. attribute:: header

        Contains a bool indicating whether the current frame is actually an
        SPS/PPS header. Typically it is best to split an H.264 stream so that
        it starts with an SPS/PPS header.


Exceptions
==========

.. autoexception:: PiCameraError

.. autoexception:: PiCameraValueError

.. autoexception:: PiCameraRuntimeError

"""

from __future__ import (
    unicode_literals,
    print_function,
    division,
    absolute_import,
    )

# Make Py2's str equivalent to Py3's
str = type('')

from picamera.exc import PiCameraError, PiCameraRuntimeError, PiCameraValueError
from picamera.camera import PiCamera, PiVideoFrame
from picamera.streams import PiCameraCircularIO, CircularIO


__all__ = [
    'PiCamera',
    'PiVideoFrame',
    'PiCameraError',
    'PiCameraRuntimeError',
    'PiCameraValueError',
    'PiCameraCircularIO',
    'CircularIO',
    ]

