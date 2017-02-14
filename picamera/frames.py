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

# Make Py2's str and range equivalent to Py3's
str = type('')

import warnings
from collections import namedtuple

from picamera.exc import (
    mmal_check,
    PiCameraError,
    PiCameraMMALError,
    PiCameraValueError,
    PiCameraRuntimeError,
    PiCameraDeprecated,
    )


class PiVideoFrameType(object):
    """
    This class simply defines constants used to represent the type of a frame
    in :attr:`PiVideoFrame.frame_type`. Effectively it is a namespace for an
    enum.

    .. attribute:: frame

        Indicates a predicted frame (P-frame). This is the most common frame
        type.

    .. attribute:: key_frame

        Indicates an intra-frame (I-frame) also known as a key frame.

    .. attribute:: sps_header

        Indicates an inline SPS/PPS header (rather than picture data) which is
        typically used as a split point.

    .. attribute:: motion_data

        Indicates the frame is inline motion vector data, rather than picture
        data.

    .. versionadded:: 1.5
    """
    frame = 0
    key_frame = 1
    sps_header = 2
    motion_data = 3


class PiVideoFrame(namedtuple('PiVideoFrame', (
    'index',         # the frame number, where the first frame is 0
    'frame_type',    # a constant indicating the frame type (see PiVideoFrameType)
    'frame_size',    # the size (in bytes) of the frame's data
    'video_size',    # the size (in bytes) of the video so far
    'split_size',    # the size (in bytes) of the video since the last split
    'timestamp',     # the presentation timestamp (PTS) of the frame
    'complete',      # whether the frame is complete or not
    ))):
    """
    This class is a :func:`~collections.namedtuple` derivative used to store
    information about a video frame. It is recommended that you access the
    information stored by this class by attribute name rather than position
    (for example: ``frame.index`` rather than ``frame[0]``).

    .. attribute:: index

        Returns the zero-based number of the frame. This is a monotonic counter
        that is simply incremented every time the camera starts outputting a
        new frame. As a consequence, this attribute cannot be used to detect
        dropped frames. Nor does it necessarily represent actual frames; it
        will be incremented for SPS headers and motion data buffers too.

    .. attribute:: frame_type

        Returns a constant indicating the kind of data that the frame contains
        (see :class:`PiVideoFrameType`). Please note that certain frame types
        contain no image data at all.

    .. attribute:: frame_size

        Returns the size in bytes of the current frame. If a frame is written
        in multiple chunks, this value will increment while :attr:`index`
        remains static. Query :attr:`complete` to determine whether the frame
        has been completely output yet.

    .. attribute:: video_size

        Returns the size in bytes of the entire video up to this frame.  Note
        that this is unlikely to match the size of the actual file/stream
        written so far. This is because a stream may utilize buffering which
        will cause the actual amount written (e.g. to disk) to lag behind the
        value reported by this attribute.

    .. attribute:: split_size

        Returns the size in bytes of the video recorded since the last call to
        either :meth:`~PiCamera.start_recording` or
        :meth:`~PiCamera.split_recording`. For the reasons explained above,
        this may differ from the size of the actual file/stream written so far.

    .. attribute:: timestamp

        Returns the presentation timestamp (PTS) of the frame. This represents
        the point in time that the Pi received the first line of the frame from
        the camera.

        The timestamp is measured in microseconds (millionths of a second).
        When the camera's clock mode is ``'reset'`` (the default), the
        timestamp is relative to the start of the video recording.  When the
        camera's :attr:`~PiCamera.clock_mode` is ``'raw'``, it is relative to
        the last system reboot. See :attr:`~PiCamera.timestamp` for more
        information.

        .. warning::

            Currently, the camera occasionally returns "time unknown" values in
            this field which picamera represents as ``None``. If you are
            querying this property you will need to check the value is not
            ``None`` before using it. This happens for SPS header "frames",
            for example.

    .. attribute:: complete

        Returns a bool indicating whether the current frame is complete or not.
        If the frame is complete then :attr:`frame_size` will not increment
        any further, and will reset for the next frame.

    .. versionchanged:: 1.5
        Deprecated :attr:`header` and :attr:`keyframe` attributes and added the
        new :attr:`frame_type` attribute instead.

    .. versionchanged:: 1.9
        Added the :attr:`complete` attribute.
    """

    __slots__ = () # workaround python issue #24931

    @property
    def position(self):
        """
        Returns the zero-based position of the frame in the stream containing
        it.
        """
        return self.split_size - self.frame_size

    @property
    def keyframe(self):
        """
        Returns a bool indicating whether the current frame is a keyframe (an
        intra-frame, or I-frame in MPEG parlance).

        .. deprecated:: 1.5
            Please compare :attr:`frame_type` to
            :attr:`PiVideoFrameType.key_frame` instead.
        """
        warnings.warn(
            PiCameraDeprecated(
                'PiVideoFrame.keyframe is deprecated; please check '
                'PiVideoFrame.frame_type for equality with '
                'PiVideoFrameType.key_frame instead'))
        return self.frame_type == PiVideoFrameType.key_frame

    @property
    def header(self):
        """
        Contains a bool indicating whether the current frame is actually an
        SPS/PPS header. Typically it is best to split an H.264 stream so that
        it starts with an SPS/PPS header.

        .. deprecated:: 1.5
            Please compare :attr:`frame_type` to
            :attr:`PiVideoFrameType.sps_header` instead.
        """
        warnings.warn(
            PiCameraDeprecated(
                'PiVideoFrame.header is deprecated; please check '
                'PiVideoFrame.frame_type for equality with '
                'PiVideoFrameType.sps_header instead'))
        return self.frame_type == PiVideoFrameType.sps_header

