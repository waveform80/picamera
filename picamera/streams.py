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
The streams module defines stream classes suited to generating certain types of
camera output (beyond those provided by Python by default). Currently, this
consists primarily of :class:`~PiCameraCircularIO`.

.. note::

    All classes in this module are available from the :mod:`picamera` namespace
    without having to import :mod:`picamera.streams` directly.

The following classes are defined in the module:


PiCameraCircularIO
==================

.. autoclass:: PiCameraCircularIO
    :members:


CircularIO
==========

.. autoclass:: CircularIO
    :members:

"""

from __future__ import (
    unicode_literals,
    print_function,
    division,
    absolute_import,
    )

# Make Py2's str equivalent to Py3's
str = type('')


import io
from threading import RLock
from collections import deque

from picamera.exc import PiCameraValueError
from picamera.encoders import PiVideoFrame


__all__ = [
    'CircularIO',
    'PiCameraCircularIO',
    ]


class CircularIO(io.IOBase):
    """
    A thread-safe stream which uses a ring buffer for storage.

    CircularIO provides an in-memory stream similar to the :class:`io.BytesIO`
    class. However, unlike BytesIO its underlying storage is a `ring buffer`_
    with a fixed maximum size. Once the maximum size is reached, writing
    effectively loops round to the beginning to the ring and starts overwriting
    the oldest content.

    The *size* parameter specifies the maximum size of the stream in bytes. The
    :meth:`read`, :meth:`tell`, and :meth:`seek` methods all operate
    equivalently to those in :class:`io.BytesIO` whilst :meth:`write` only
    differs in the wrapping behaviour described above. A :meth:`read1` method
    is also provided for efficient reading of the underlying ring buffer in
    write-sized chunks (or less).

    A re-entrant threading lock guards all operations, and is accessible for
    external use via the :attr:`lock` attribute.

    The performance of the class is geared toward faster writing than reading
    on the assumption that writing will be the common operation and reading the
    rare operation (a reasonable assumption for the camera use-case, but not
    necessarily for more general usage).

    .. _ring buffer: http://en.wikipedia.org/wiki/Circular_buffer
    """
    def __init__(self, size):
        if size < 1:
            raise ValueError('size must be a positive integer')
        self._lock = RLock()
        self._data = deque()
        self._size = size
        self._length = 0
        self._pos = 0
        self._pos_index = 0
        self._pos_offset = 0

    @property
    def lock(self):
        """
        A re-entrant threading lock which is used to guard all operations.
        """
        return self._lock

    @property
    def size(self):
        """
        Return the maximum size of the buffer in bytes.
        """
        return self._size

    def readable(self):
        """
        Returns ``True``, indicating that the stream supports :meth:`read`.
        """
        return True

    def writable(self):
        """
        Returns ``True``, indicating that the stream supports :meth:`write`.
        """
        return True

    def seekable(self):
        """
        Returns ``True``, indicating the stream supports :meth:`seek` and
        :meth:`tell`.
        """
        return True

    def getvalue(self):
        """
        Return ``bytes`` containing the entire contents of the buffer.
        """
        with self.lock:
            return b''.join(self._data)

    def _set_pos(self, value):
        self._pos = value
        self._pos_index = -1
        self._pos_offset = chunk_pos = 0
        for self._pos_index, chunk in enumerate(self._data):
            if chunk_pos + len(chunk) > value:
                self._pos_offset = value - chunk_pos
                return
            else:
                chunk_pos += len(chunk)
        self._pos_index += 1
        self._pos_offset = value - chunk_pos

    def tell(self):
        """
        Return the current stream position.
        """
        return self._pos

    def seek(self, offset, whence=io.SEEK_SET):
        """
        Change the stream position to the given byte *offset*. *offset* is
        interpreted relative to the position indicated by *whence*. Values for
        *whence* are:

        * ``SEEK_SET`` or ``0`` – start of the stream (the default); *offset*
          should be zero or positive

        * ``SEEK_CUR`` or ``1`` – current stream position; *offset* may be
          negative

        * ``SEEK_END`` or ``2`` – end of the stream; *offset* is usually
          negative

        Return the new absolute position.
        """
        with self.lock:
            if whence == io.SEEK_CUR:
                offset = self._pos + offset
            elif whence == io.SEEK_END:
                offset = self._length + offset
            if offset < 0:
                raise ValueError(
                    'New position is before the start of the stream')
            self._set_pos(offset)
            return self._pos

    def read(self, n=-1):
        """
        Read up to *n* bytes from the stream and return them. As a convenience,
        if *n* is unspecified or -1, :meth:`readall` is called. Fewer than *n*
        bytes may be returned if there are fewer than *n* bytes from the
        current stream position to the end of the stream.

        If 0 bytes are returned, and *n* was not 0, this indicates end of the
        stream.
        """
        if n == -1:
            return self.readall()
        else:
            with self.lock:
                if self._pos == self._length:
                    return b''
                from_index, from_offset = self._pos_index, self._pos_offset
                self._set_pos(self._pos + n)
                result = self._data[from_index][from_offset:from_offset + n]
                # Bah ... can't slice a deque
                for i in range(from_index + 1, self._pos_index):
                    result += self._data[i]
                if from_index < self._pos_index < len(self._data):
                    result += self._data[self._pos_index][:self._pos_offset]
                return result

    def readall(self):
        """
        Read and return all bytes from the stream until EOF, using multiple
        calls to the stream if necessary.
        """
        return self.read(self._length - self._pos)

    def read1(self, n=-1):
        """
        Read up to *n* bytes from the stream using only a single call to the
        underlying object.

        In the case of :class:`CircularIO` this roughly corresponds to
        returning the content from the current position up to the end of the
        write that added that content to the stream (assuming no subsequent
        writes overwrote the content). :meth:`read1` is particularly useful
        for efficient copying of the stream's content.
        """
        with self.lock:
            if self._pos == self._length:
                return b''
            chunk = self._data[self._pos_index]
            if n == -1:
                n = len(chunk) - self._pos_offset
            result = chunk[self._pos_offset:self._pos_offset + n]
            self._pos += len(result)
            self._pos_offset += n
            if self._pos_offset >= len(chunk):
                self._pos_index += 1
                self._pos_offset = 0
            return result

    def truncate(self, size=None):
        """
        Resize the stream to the given *size* in bytes (or the current position
        if *size* is not specified). This resizing can extend or reduce the
        current stream size. In case of extension, the contents of the new file
        area will be NUL (``\\x00``) bytes. The new stream size is returned.

        The current stream position isn’t changed unless the resizing is
        expanding the stream, in which case it may be set to the maximum stream
        size if the expansion causes the ring buffer to loop around.
        """
        with self.lock:
            if size is None:
                size = self._pos
            if size < 0:
                raise ValueError('size must be zero, or a positive integer')
            if size > self._length:
                # Backfill the space between stream end and current position
                # with NUL bytes
                fill = b'\x00' * (size - self._length)
                self._set_pos(self._length)
                self.write(fill)
            elif size < self._length:
                # Lop off chunks until we get to the last one at the truncation
                # point, and slice that one
                save_pos = self._pos
                self._set_pos(size)
                while self._pos_index < len(self._data) - 1:
                    self._data.pop()
                self._data[self._pos_index] = self._data[self._pos_index][:self._pos_offset]
                self._length = size
                self._pos_index += 1
                self._pos_offset = 0
                if self._pos != save_pos:
                    self._set_pos(save_pos)

    def write(self, b):
        """
        Write the given bytes or bytearray object, *b*, to the underlying
        stream and return the number of bytes written.
        """
        b = bytes(b)
        with self.lock:
            # Special case: stream position is beyond the end of the stream.
            # Call truncate to backfill space first
            if self._pos > self._length:
                self.truncate()
            result = len(b)
            if self._pos == self._length:
                # Fast path: stream position is at the end of the stream so
                # just append a new chunk
                self._data.append(b)
                self._length += len(b)
                self._pos = self._length
                self._pos_index = len(self._data)
                self._pos_offset = 0
            else:
                # Slow path: stream position is somewhere in the middle;
                # overwrite bytes in the current (and if necessary, subsequent)
                # chunk(s), without extending them. If we reach the end of the
                # stream, call ourselves recursively to continue down the fast
                # path
                while b and (self._pos < self._length):
                    chunk = self._data[self._pos_index]
                    head = b[:len(chunk) - self._pos_offset]
                    assert head
                    b = b[len(head):]
                    self._data[self._pos_index] = b''.join((
                            chunk[:self._pos_offset],
                            head,
                            chunk[self._pos_offset + len(head):]
                            ))
                    self._pos += len(head)
                    if self._pos_offset + len(head) >= len(chunk):
                        self._pos_index += 1
                        self._pos_offset = 0
                    else:
                        self._pos_offset += len(head)
                if b:
                    self.write(b)
            # If the stream is now beyond the specified size limit, remove
            # chunks (or part of a chunk) until the size is within the limit
            # again
            while self._length > self._size:
                chunk = self._data[0]
                if self._length - len(chunk) >= self._size:
                    # Need to remove the entire chunk
                    self._data.popleft()
                    self._length -= len(chunk)
                    self._pos -= len(chunk)
                    self._pos_index -= 1
                    # no need to adjust self._pos_offset
                else:
                    # need to remove the head of the chunk
                    self._data[0] = chunk[self._length - self._size:]
                    self._pos -= self._length - self._size
                    self._length = self._size
            return result


class PiCameraDequeHack(deque):
    def __init__(self, camera, splitter_port=1):
        super(PiCameraDequeHack, self).__init__()
        self.camera = camera
        self.splitter_port = splitter_port

    def append(self, item):
        encoder = self.camera._encoders[self.splitter_port]
        if encoder.frame.complete:
            # If the chunk being appended is the end of a new frame, include
            # the frame's metadata from the camera
            return super(PiCameraDequeHack, self).append((item, encoder.frame))
        else:
            return super(PiCameraDequeHack, self).append((item, None))

    def pop(self):
        return super(PiCameraDequeHack, self).pop()[0]

    def popleft(self):
        return super(PiCameraDequeHack, self).popleft()[0]

    def __getitem__(self, index):
        return super(PiCameraDequeHack, self).__getitem__(index)[0]

    def __setitem__(self, index, value):
        frame = super(PiCameraDequeHack, self).__getitem__(index)[1]
        return super(PiCameraDequeHack, self).__setitem__(index, (value, frame))

    def __iter__(self):
        for item, frame in super(PiCameraDequeHack, self).__iter__():
            yield item


class PiCameraDequeFrames(object):
    def __init__(self, stream):
        super(PiCameraDequeFrames, self).__init__()
        self.stream = stream

    def __iter__(self):
        with self.stream.lock:
            pos = 0
            for item, frame in super(PiCameraDequeHack, self.stream._data).__iter__():
                pos += len(item)
                if frame:
                    # Rewrite the video_size and split_size attributes according
                    # to the current position of the chunk
                    frame = PiVideoFrame(
                        index=frame.index,
                        frame_type=frame.frame_type,
                        frame_size=frame.frame_size,
                        video_size=pos,
                        split_size=pos,
                        timestamp=frame.timestamp,
                        complete=frame.complete,
                        )
                    # Only yield the frame meta-data if the start of the frame
                    # still exists in the stream
                    if pos - frame.frame_size >= 0:
                        yield frame

    def __reversed__(self):
        with self.stream.lock:
            pos = self.stream._length
            for item, frame in super(PiCameraDequeHack, self.stream._data).__reversed__():
                if frame:
                    frame = PiVideoFrame(
                        index=frame.index,
                        frame_type=frame.frame_type,
                        frame_size=frame.frame_size,
                        video_size=pos,
                        split_size=pos,
                        timestamp=frame.timestamp,
                        complete=frame.complete,
                        )
                    if pos - frame.frame_size >= 0:
                        yield frame
                pos -= len(item)


class PiCameraCircularIO(CircularIO):
    """
    A derivative of :class:`CircularIO` which tracks camera frames.

    PiCameraCircularIO provides an in-memory stream based on a ring buffer. It
    is a specialization of :class:`CircularIO` which associates video frame
    meta-data with the recorded stream, accessible from the :attr:`frames`
    property.

    .. warning::

        The class makes a couple of assumptions which will cause the frame
        meta-data tracking to break if they are not adhered to:

        * the stream is only ever appended to - no writes ever start from
          the middle of the stream

        * the stream is never truncated (from the right; being ring buffer
          based, left truncation will occur automatically)

    The *camera* parameter specifies the :class:`~picamera.camera.PiCamera`
    instance that will be recording video to the stream. If specified, the
    *size* parameter determines the maximum size of the stream in bytes. If
    *size* is not specified (or ``None``), then *seconds* must be specified
    instead. This provides the maximum length of the stream in seconds,
    assuming a data rate in bits-per-second given by the *bitrate* parameter
    (which defaults to ``17000000``, or 17Mbps, which is also the default
    bitrate used for video recording by :class:`~picamera.camera.PiCamera`).
    You cannot specify both *size* and *seconds*.

    The *splitter_port* parameter specifies the port of the built-in splitter
    that the video encoder will be attached to. This defaults to ``1`` and most
    users will have no need to specify anything different. If you do specify
    something else, ensure it is equal to the *splitter_port* parameter of the
    corresponding call to :meth:`~picamera.camera.PiCamera.start_recording`.
    For example::

        import picamera

        with picamera.PiCamera() as camera:
            with picamera.PiCameraCircularIO(camera, splitter_port=2) as stream:
                camera.start_recording(stream, format='h264', splitter_port=2)
                camera.wait_recording(10, splitter_port=2)
                camera.stop_recording(splitter_port=2)

    .. attribute:: frames

        Returns an iterator over the frame meta-data.

        As the camera records video to the stream, the class captures the
        meta-data associated with each frame (in the form of a
        :class:`~picamera.encoders.PiVideoFrame` tuple), discarding meta-data
        for frames which are no longer fully stored within the underlying ring
        buffer.  You can use the frame meta-data to locate, for example, the
        first keyframe present in the stream in order to determine an
        appropriate range to extract.
    """
    def __init__(
            self, camera, size=None, seconds=None, bitrate=17000000,
            splitter_port=1):
        if size is None and seconds is None:
            raise PiCameraValueError('You must specify either size, or seconds')
        if size is not None and seconds is not None:
            raise PiCameraValueError('You cannot specify both size and seconds')
        if seconds is not None:
            size = bitrate * seconds // 8
        super(PiCameraCircularIO, self).__init__(size)
        self._data = PiCameraDequeHack(camera, splitter_port)
        self.frames = PiCameraDequeFrames(self)

