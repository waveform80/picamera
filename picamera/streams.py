# vim: set et sw=4 sts=4 fileencoding=utf-8:
#
# Python camera library for the Rasperry-Pi camera module
# Copyright (c) 2013-2017 Dave Jones <dave@waveform.org.uk>
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


import io
from threading import RLock
from collections import deque
from operator import attrgetter
from weakref import ref

from picamera.exc import PiCameraValueError
from picamera.frames import PiVideoFrame, PiVideoFrameType


class BufferIO(io.IOBase):
    """
    A stream which uses a :class:`memoryview` for storage.

    This is used internally by picamera for capturing directly to an existing
    object which supports the buffer protocol (like a numpy array). Because the
    underlying storage is fixed in size, the stream also has a fixed size and
    will raise an :exc:`IOError` exception if an attempt is made to write
    beyond the end of the buffer (though seek beyond the end is supported).

    Users should never need this class directly.
    """
    __slots__ = ('_buf', '_pos', '_size')

    def __init__(self, obj):
        self._buf = memoryview(obj)
        if self._buf.ndim > 1 or self._buf.format != 'B':
            try:
                # Py2.7 doesn't have memoryview.cast
                self._buf = self._buf.cast('B')
            except AttributeError:
                raise ValueError(
                    'buffer object must be one-dimensional and have unsigned '
                    'byte format ("B")')
        self._pos = 0
        self._size = self._buf.shape[0]

    def close(self):
        super(BufferIO, self).close()
        try:
            self._buf.release()
        except AttributeError:
            # Py2.7 doesn't have memoryview.release
            pass

    def _check_open(self):
        if self.closed:
            raise ValueError('I/O operation on a closed stream')

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
        self._check_open()
        return True

    def writable(self):
        """
        Returns ``True``, indicating that the stream supports :meth:`write`.
        """
        self._check_open()
        return not self._buf.readonly

    def seekable(self):
        """
        Returns ``True``, indicating the stream supports :meth:`seek` and
        :meth:`tell`.
        """
        self._check_open()
        return True

    def getvalue(self):
        """
        Return ``bytes`` containing the entire contents of the buffer.
        """
        with self.lock:
            return self._buf.tobytes()

    def tell(self):
        """
        Return the current buffer position.
        """
        self._check_open()
        return self._pos

    def seek(self, offset, whence=io.SEEK_SET):
        """
        Change the buffer position to the given byte *offset*. *offset* is
        interpreted relative to the position indicated by *whence*. Values for
        *whence* are:

        * ``SEEK_SET`` or ``0`` – start of the buffer (the default); *offset*
          should be zero or positive

        * ``SEEK_CUR`` or ``1`` – current buffer position; *offset* may be
          negative

        * ``SEEK_END`` or ``2`` – end of the buffer; *offset* is usually
          negative

        Return the new absolute position.
        """
        self._check_open()
        if whence == io.SEEK_CUR:
            offset = self._pos + offset
        elif whence == io.SEEK_END:
            offset = self.size + offset
        if offset < 0:
            raise ValueError(
                'New position is before the start of the stream')
        self._pos = offset
        return self._pos

    def read(self, n=-1):
        """
        Read up to *n* bytes from the buffer and return them. As a convenience,
        if *n* is unspecified or -1, :meth:`readall` is called. Fewer than *n*
        bytes may be returned if there are fewer than *n* bytes from the
        current buffer position to the end of the buffer.

        If 0 bytes are returned, and *n* was not 0, this indicates end of the
        buffer.
        """
        self._check_open()
        if n < 0:
            return self.readall()
        elif n == 0:
            return b''
        else:
            result = self._buf[self._pos:self._pos + n].tobytes()
            self._pos += len(result)
            return result

    def readinto(self, b):
        """
        Read bytes into a pre-allocated, writable bytes-like object b, and
        return the number of bytes read.
        """
        self._check_open()
        result = max(0, min(len(b), self._size - self._pos))
        if result == 0:
            return 0
        else:
            b[:result] = self._buf[self._pos:self._pos + result]
            return result

    def readall(self):
        """
        Read and return all bytes from the buffer until EOF.
        """
        return self.read(max(0, self.size - self._pos))

    def truncate(self, size=None):
        """
        Raises :exc:`NotImplementedError` as the underlying buffer cannot be
        resized.
        """
        raise NotImplementedError('cannot resize a BufferIO stream')

    def write(self, b):
        """
        Write the given bytes or bytearray object, *b*, to the underlying
        buffer and return the number of bytes written. If the underlying
        buffer isn't large enough to contain all the bytes of *b*, as many
        bytes as possible will be written before raising :exc:`IOError`.
        """
        self._check_open()
        if self._buf.readonly:
            raise IOError('buffer object is not writeable')
        excess = max(0, len(b) - (self.size - self._pos))
        result = len(b) - excess
        if excess:
            self._buf[self._pos:self._pos + result] = b[:-excess]
        else:
            self._buf[self._pos:self._pos + result] = b
        self._pos += result
        return result


class CircularIO(io.IOBase):
    """
    A thread-safe stream which uses a ring buffer for storage.

    CircularIO provides an in-memory stream similar to the :class:`io.BytesIO`
    class. However, unlike :class:`io.BytesIO` its underlying storage is a
    `ring buffer`_ with a fixed maximum size. Once the maximum size is reached,
    writing effectively loops round to the beginning to the ring and starts
    overwriting the oldest content.

    Actually, this ring buffer is slightly different to "traditional" ring
    buffers. This ring buffer is optimized for camera usage which is expected
    to be read-light, write-heavy, and with writes *mostly* aligned to frame
    boundaries. Internally, the stream simply references each chunk written and
    drops references each time the overall size of the stream would exceed the
    specified limit.

    As a result the ring buffer doesn't stay strictly at its allocated limit as
    traditional ring buffers do. It also drops entire writes when the limit is
    reached (this is a desirable behaviour because it means that often whole
    frames are dropped from the start of the stream, rather than leaving
    partial frames at the start as in a traditional ring buffer). For example:

    .. code-block:: pycon

        >>> stream = CircularIO(size=10)
        >>> stream.write(b'abc')
        >>> stream.write(b'def')
        >>> stream.getvalue()
        b'abcdef'
        >>> stream.write(b'ghijk')
        >>> stream.getvalue()
        b'defghijk'

    In a traditional ring buffer, one would expect the last ``getvalue()`` call
    to return ``'bcdefghijk'`` as only the first character would be lost at the
    limit of 10 bytes. However, this ring buffer has dropped the entire write
    of ``'abc'``.

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

    .. _ring buffer: https://en.wikipedia.org/wiki/Circular_buffer
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

    def _check_open(self):
        if self.closed:
            raise ValueError('I/O operation on a closed stream')

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
        self._check_open()
        return True

    def writable(self):
        """
        Returns ``True``, indicating that the stream supports :meth:`write`.
        """
        self._check_open()
        return True

    def seekable(self):
        """
        Returns ``True``, indicating the stream supports :meth:`seek` and
        :meth:`tell`.
        """
        self._check_open()
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
        self._check_open()
        with self.lock:
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
        self._check_open()
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
        self._check_open()
        if n < 0:
            return self.readall()
        elif n == 0:
            return b''
        else:
            with self.lock:
                if self._pos >= self._length:
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
        return self.read(max(0, self._length - self._pos))

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
        self._check_open()
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
        self._check_open()
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
                if self._pos_offset > 0:
                    self._data[self._pos_index] = self._data[self._pos_index][:self._pos_offset]
                    self._pos_index += 1
                    self._pos_offset = 0
                else:
                    self._data.pop()
                self._length = size
                if self._pos != save_pos:
                    self._set_pos(save_pos)

    def write(self, b):
        """
        Write the given bytes or bytearray object, *b*, to the underlying
        stream and return the number of bytes written.
        """
        self._check_open()
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
            # whole chunks until the size is within the limit again
            while self._length > self._size:
                chunk = self._data.popleft()
                self._length -= len(chunk)
                self._pos -= len(chunk)
                self._pos_index -= 1
                # no need to adjust self._pos_offset
            return result


class PiCameraDequeHack(deque):
    def __init__(self, stream):
        super(PiCameraDequeHack, self).__init__()
        self.stream = ref(stream)  # avoid a circular ref

    def append(self, item):
        # Include the frame's metadata.
        frame = self.stream()._get_frame()
        return super(PiCameraDequeHack, self).append((item, frame))

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
        for item, frame in self.iter_both(False):
            yield item

    def __reversed__(self):
        for item, frame in self.iter_both(True):
            yield item

    def iter_both(self, reverse):
        if reverse:
            return super(PiCameraDequeHack, self).__reversed__()
        else:
            return super(PiCameraDequeHack, self).__iter__()


class PiCameraDequeFrames(object):
    def __init__(self, stream):
        super(PiCameraDequeFrames, self).__init__()
        self.stream = ref(stream)  # avoid a circular ref

    def __iter__(self):
        with self.stream().lock:
            pos = 0
            for item, frame in self.stream()._data.iter_both(False):
                pos += len(item)
                if frame:
                    # Rewrite the video_size and split_size attributes
                    # according to the current position of the chunk
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
        with self.stream().lock:
            pos = self.stream()._length
            for item, frame in self.stream()._data.iter_both(True):
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
          based, left truncation will occur automatically); the exception
          to this is the :meth:`clear` method.

    The *camera* parameter specifies the :class:`PiCamera` instance that will
    be recording video to the stream. If specified, the *size* parameter
    determines the maximum size of the stream in bytes. If *size* is not
    specified (or ``None``), then *seconds* must be specified instead. This
    provides the maximum length of the stream in seconds, assuming a data rate
    in bits-per-second given by the *bitrate* parameter (which defaults to
    ``17000000``, or 17Mbps, which is also the default bitrate used for video
    recording by :class:`PiCamera`).  You cannot specify both *size* and
    *seconds*.

    The *splitter_port* parameter specifies the port of the built-in splitter
    that the video encoder will be attached to. This defaults to ``1`` and most
    users will have no need to specify anything different. If you do specify
    something else, ensure it is equal to the *splitter_port* parameter of the
    corresponding call to :meth:`~PiCamera.start_recording`.  For example::

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
        :class:`PiVideoFrame` tuple), discarding meta-data for frames which are
        no longer fully stored within the underlying ring buffer.  You can use
        the frame meta-data to locate, for example, the first keyframe present
        in the stream in order to determine an appropriate range to extract.
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
        try:
            camera._encoders
        except AttributeError:
            raise PiCameraValueError('camera must be a valid PiCamera object')
        self.camera = camera
        self.splitter_port = splitter_port
        self._data = PiCameraDequeHack(self)
        self._frames = PiCameraDequeFrames(self)

    def _get_frame(self):
        """
        Return frame metadata from latest frame, when it is complete.
        """
        encoder = self.camera._encoders[self.splitter_port]
        return encoder.frame if encoder.frame.complete else None

    @property
    def frames(self):
        """
        An iterable which contains the meta-data (:class:`PiVideoFrame`
        objects) for all complete frames currently stored in the circular
        buffer.
        """
        return self._frames

    def clear(self):
        """
        Resets the stream to empty safely.

        This method truncates the stream to empty, and clears the associated
        frame meta-data too, ensuring that subsequent writes operate correctly
        (see the warning in the :class:`PiCameraCircularIO` class
        documentation).
        """
        with self.lock:
            self.seek(0)
            self.truncate()

    def _find(self, field, criteria, first_frame):
        first = last = None
        attr = attrgetter(field)
        for frame in reversed(self._frames):
            if last is None:
                last = frame
            if first_frame in (None, frame.frame_type):
                first = frame
            if last is not None and attr(last) - attr(frame) >= criteria:
                break
                if last is not None and attr(last) - attr(frame) >= criteria:
                    break
        return first, last

    def _find_all(self, first_frame):
        chunks = []
        first = last = None
        for frame in reversed(self._frames):
            last = frame
            break
        for frame in self._frames:
            if first_frame in (None, frame.frame_type):
                first = frame
                break
        return first, last

    def copy_to(
            self, output, size=None, seconds=None, frames=None,
            first_frame=PiVideoFrameType.sps_header):
        """
        copy_to(output, size=None, seconds=None, frames=None, first_frame=PiVideoFrameType.sps_header)

        Copies content from the stream to *output*.

        By default, this method copies all complete frames from the circular
        stream to the filename or file-like object given by *output*.

        If *size* is specified then the copy will be limited to the whole
        number of frames that fit within the specified number of bytes. If
        *seconds* if specified, then the copy will be limited to that number of
        seconds worth of frames. If *frames* is specified then the copy will
        be limited to that number of frames. Only one of *size*, *seconds*, or
        *frames* can be specified. If none is specified, all frames are copied.

        If *first_frame* is specified, it defines the frame type of the first
        frame to be copied. By default this is
        :attr:`~PiVideoFrameType.sps_header` as this must usually be the first
        frame in an H264 stream. If *first_frame* is ``None``, not such limit
        will be applied.

        .. warning::

            Note that if a frame of the specified type (e.g. SPS header) cannot
            be found within the specified number of seconds, bytes, or frames,
            then this method will simply copy nothing (but no error will be
            raised).

        The stream's position is not affected by this method.
        """
        if (size, seconds, frames).count(None) < 2:
            raise PiCameraValueError(
                'You can only specify one of size, seconds, or frames')
        if isinstance(output, bytes):
            output = output.decode('utf-8')
        opened = isinstance(output, str)
        if opened:
            output = io.open(output, 'wb')
        try:
            with self.lock:
                if size is not None:
                    first, last = self._find('video_size', size, first_frame)
                elif seconds is not None:
                    seconds = int(seconds * 1000000)
                    first, last = self._find('timestamp', seconds, first_frame)
                elif frames is not None:
                    first, last = self._find('index', frames, first_frame)
                else:
                    first, last = self._find_all(first_frame)
                # Copy chunk references into a holding buffer; this allows us
                # to release the lock on the stream quickly (in case recording
                # is on-going)
                chunks = []
                if first is not None and last is not None:
                    pos = 0
                    for buf, frame in self._data.iter_both(False):
                        if pos > last.position + last.frame_size:
                            break
                        elif pos >= first.position:
                            chunks.append(buf)
                        pos += len(buf)
            # Perform the actual I/O, copying chunks to the output
            for buf in chunks:
                output.write(buf)
            return first, last
        finally:
            if opened:
                output.close()
