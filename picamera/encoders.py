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
The encoders module defines encoder classes for use by the camera. Most users
will have no direct need to use these classes directly, but advanced users may
find them useful as base classes for :ref:`custom_encoders`.

.. note::

    All classes in this module are available from the :mod:`picamera` namespace
    without having to import :mod:`picamera.encoders` directly.

The following classes are defined in the module:


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


PiRawMixin
==========

.. autoclass:: PiRawMixin
    :members:
    :private-members:


PiCookedVideoEncoder
====================

.. autoclass:: PiCookedVideoEncoder
    :members:
    :private-members:


PiRawVideoEncoder
=================

.. autoclass:: PiRawVideoEncoder
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


PiRawImageMixin
===============

.. autoclass:: PiRawImageMixin
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

"""

from __future__ import (
    unicode_literals,
    print_function,
    division,
    absolute_import,
    )

# Make Py2's str and range equivalent to Py3's
str = type('')
try:
    range = xrange
except NameError:
    pass

import io
import datetime
import threading
import warnings
import ctypes as ct
from collections import namedtuple

import picamera.mmal as mmal
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
    This class is a namedtuple derivative used to store information about a
    video frame. It is recommended that you access the information stored by
    this class by attribute name rather than position (for example:
    ``frame.index`` rather than ``frame[0]``).

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

        Returns the size in bytes of the entire video up to the current frame.
        Note that this is unlikely to match the size of the actual file/stream
        written so far. This is because a stream may utilize buffering which
        will cause the actual amount written (e.g. to disk) to lag behind the
        value reported by this attribute.

    .. attribute:: split_size

        Returns the size in bytes of the video recorded since the last call to
        either :meth:`~picamera.camera.PiCamera.start_recording` or
        :meth:`~picamera.camera.PiCamera.split_recording`. For the reasons
        explained above, this may differ from the size of the actual
        file/stream written so far.

    .. attribute:: timestamp

        Returns the presentation timestamp (PTS) of the current frame as
        reported by the encoder. This is represented by the number of
        microseconds (millionths of a second) since video recording started. As
        the frame attribute is only updated when the encoder outputs the end of
        a frame, this value may lag behind the actual time since
        :meth:`~picamera.camera.PiCamera.start_recording` was called.

        .. warning::

            Currently, the video encoder occasionally returns "time unknown"
            values in this field which picamera represents as ``None``. If you
            are querying this property you will need to check the value is not
            ``None`` before using it.

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


def _debug_buffer(buf):
    f = buf[0].flags
    print(''.join((
        'flags=',
        'E' if f & mmal.MMAL_BUFFER_HEADER_FLAG_FRAME_END     else '_',
        'K' if f & mmal.MMAL_BUFFER_HEADER_FLAG_KEYFRAME      else '_',
        'C' if f & mmal.MMAL_BUFFER_HEADER_FLAG_CONFIG        else '_',
        'M' if f & mmal.MMAL_BUFFER_HEADER_FLAG_CODECSIDEINFO else '_',
        'X' if f & mmal.MMAL_BUFFER_HEADER_FLAG_EOS           else '_',
        ' ',
        'len=%d' % buf[0].length,
        )))


def _encoder_callback(port, buf):
    #_debug_buffer(buf)
    encoder = ct.cast(port[0].userdata, ct.POINTER(ct.py_object))[0]
    encoder._callback(port, buf)
_encoder_callback = mmal.MMAL_PORT_BH_CB_T(_encoder_callback)


class PiEncoder(object):
    """
    Base implementation of an MMAL encoder for use by PiCamera.

    The *parent* parameter specifies the :class:`~picamera.camera.PiCamera`
    instance that has constructed the encoder. The *camera_port* parameter
    provides the MMAL camera port that the encoder should enable for capture
    (this will be the still or video port of the camera component). The
    *input_port* parameter specifies the MMAL port that the encoder should
    connect to its input.  Sometimes this will be the same as the camera port,
    but if other components are present in the pipeline (e.g. a splitter), it
    may be different.

    The *format* parameter specifies the format that the encoder should
    produce in its output. This is specified as a string and will be one of
    the following for image encoders:

    * ``'jpeg'``
    * ``'png'``
    * ``'gif'``
    * ``'bmp'``
    * ``'yuv'``
    * ``'rgb'``
    * ``'rgba'``
    * ``'bgr'``
    * ``'bgra'``

    And one of the following for video encoders:

    * ``'h264'``
    * ``'mjpeg'``

    The *resize* parameter is either ``None`` (indicating no resizing
    should take place), or a ``(width, height)`` tuple specifying the
    resolution that the output of the encoder should be resized to.

    Finally, the *options* parameter specifies additional keyword arguments
    that can be used to configure the encoder (e.g. bitrate for videos, or
    quality for images).

    The class has a number of attributes:

    .. attribute:: camera_port

        A pointer to the camera output port that needs to be activated and
        deactivated in order to start/stop capture. This is not necessarily the
        port that the encoder component's input port is connected to (for
        example, in the case of video-port based captures, this will be the
        camera video port behind the splitter).

    .. attribute:: encoder

        A pointer to the MMAL encoder component, or None if no encoder
        component has been created (some encoder classes don't use an actual
        encoder component, for example :class:`PiRawImageMixin`).

    .. attribute:: encoder_connection

        A pointer to the MMAL connection linking the encoder's input port to
        the camera, splitter, or resizer output port (depending on
        configuration), if any.

    .. attribute:: event

        A :class:`threading.Event` instance used to synchronize operations
        (like start, stop, and split) between the control thread and the
        callback thread.

    .. attribute:: exception

        If an exception occurs during the encoder callback, this attribute is
        used to store the exception until it can be re-raised in the control
        thread.

    .. attribute:: format

        The image or video format that the encoder is expected to produce. This
        is equal to the value of the *format* parameter.

    .. attribute:: input_port

        A pointer to the MMAL port that the encoder component's input port
        should be connected to.

    .. attribute:: output_port

        A pointer to the MMAL port of the encoder's output. In the case no
        encoder component is created, this should be the camera/component
        output port responsible for producing data. In other words, this
        attribute **must** be set on initialization.

    .. attribute:: outputs

        A mapping of ``key`` to ``(output, opened)`` tuples where ``output``
        is a file-like object, and ``opened`` is a bool indicating whether or
        not we opened the output object (and thus whether we are responsible
        for eventually closing it).

    .. attribute:: outputs_lock

        A :func:`threading.Lock` instance used to protect access to
        :attr:`outputs`.

    .. attribute:: parent

        The :class:`~picamera.camera.PiCamera` instance that created this
        PiEncoder instance.

    .. attribute:: pool

        A pointer to a pool of MMAL buffers.

    .. attribute:: resizer

        A pointer to the MMAL resizer component, or None if no resizer
        component has been created.

    .. attribute:: resizer_connection

        A pointer to the MMAL connection linking the resizer's input port to
        the camera or splitter's output port, if any.
    """

    encoder_type = None

    def __init__(
            self, parent, camera_port, input_port, format, resize, **options):
        self.parent = parent
        self.format = format
        self.encoder = None
        self.resizer = None
        self.encoder_connection = None
        self.resizer_connection = None
        self.camera_port = camera_port
        self.input_port = input_port
        self.output_port = None
        self.pool = None
        self.started_capture = False
        self.outputs_lock = threading.Lock() # protects access to self.outputs
        self.outputs = {}
        self.exception = None
        self.event = threading.Event()
        self.stopped = True
        try:
            if parent.closed:
                raise PiCameraRuntimeError("Camera is closed")
            if resize:
                self._create_resizer(*resize)
            self._create_encoder(**options)
            self._create_pool()
            self._create_connections()
        except:
            self.close()
            raise

    def _create_resizer(self, width, height):
        """
        Creates and configures an MMAL resizer component.

        This is called when the initializer's *resize* parameter is something
        other than ``None``. The *width* and *height* parameters are passed to
        the constructed resizer. Note that this method only constructs the
        resizer - it does not connect it to the encoder. The method sets the
        :attr:`resizer` attribute to the constructed resizer component.
        """
        self.resizer = ct.POINTER(mmal.MMAL_COMPONENT_T)()
        mmal_check(
            mmal.mmal_component_create(
                mmal.MMAL_COMPONENT_DEFAULT_RESIZER, self.resizer),
            prefix="Failed to create resizer component")
        if not self.resizer[0].input_num:
            raise PiCameraError("No input ports on resizer component")
        if not self.resizer[0].output_num:
            raise PiCameraError("No output ports on resizer component")
        # Copy the original input port's format to the resizer's input,
        # then the resizer's input format to the output, and configure it
        mmal.mmal_format_copy(
            self.resizer[0].input[0][0].format, self.input_port[0].format)
        mmal_check(
            mmal.mmal_port_format_commit(self.resizer[0].input[0]),
            prefix="Failed to set resizer input port format")
        mmal.mmal_format_copy(
            self.resizer[0].output[0][0].format, self.resizer[0].input[0][0].format)
        fmt = self.resizer[0].output[0][0].format
        fmt[0].es[0].video.width = mmal.VCOS_ALIGN_UP(width, 32)
        fmt[0].es[0].video.height = mmal.VCOS_ALIGN_UP(height, 16)
        fmt[0].es[0].video.crop.x = 0
        fmt[0].es[0].video.crop.y = 0
        fmt[0].es[0].video.crop.width = width
        fmt[0].es[0].video.crop.height = height
        mmal_check(
            mmal.mmal_port_format_commit(self.resizer[0].output[0]),
            prefix="Failed to set resizer output port format")

    def _create_encoder(self):
        """
        Creates and configures the MMAL encoder component.

        This method only constructs the encoder; it does not connect it to the
        input port. The method sets the :attr:`encoder` attribute to the
        constructed encoder component, and the :attr:`output_port` attribute to
        the encoder's output port (or the previously constructed resizer's
        output port if one has been requested). Descendent classes extend this
        method to finalize encoder configuration. 

        .. note::

            It should be noted that this method is called with the
            initializer's ``option`` keyword arguments. This base
            implementation expects no additional arguments, but descendent
            classes extend the parameter list to include options relevant to
            them.
        """
        assert not self.encoder
        self.encoder = ct.POINTER(mmal.MMAL_COMPONENT_T)()
        mmal_check(
            mmal.mmal_component_create(self.encoder_type, self.encoder),
            prefix="Failed to create encoder component")
        if not self.encoder[0].input_num:
            raise PiCameraError("No input ports on encoder component")
        if not self.encoder[0].output_num:
            raise PiCameraError("No output ports on encoder component")
        # Ensure output format is the same as the input
        self.output_port = self.encoder[0].output[0]
        if self.resizer:
            mmal.mmal_format_copy(
                self.encoder[0].input[0][0].format, self.resizer[0].output[0][0].format)
        else:
            mmal.mmal_format_copy(
                self.encoder[0].input[0][0].format, self.input_port[0].format)
        mmal_check(
            mmal.mmal_port_format_commit(self.encoder[0].input[0]),
            prefix="Failed to set encoder input port format")
        mmal.mmal_format_copy(
            self.output_port[0].format, self.encoder[0].input[0][0].format)
        # Set buffer size and number to appropriate values
        if self.format == 'mjpeg':
            # There is a bug in the MJPEG encoder that causes a deadlock if the
            # FIFO is full on shutdown. Increasing the encoder buffer size
            # makes this less likely to happen. See
            # https://github.com/raspberrypi/userland/issues/208
            self.output_port[0].buffer_size = max(512 * 1024, self.output_port[0].buffer_size_recommended)
        else:
            self.output_port[0].buffer_size = self.output_port[0].buffer_size_recommended
        self.output_port[0].buffer_num = self.output_port[0].buffer_num_recommended
        # NOTE: We deliberately don't commit the output port format here as
        # this is a base class and the output configuration is incomplete at
        # this point. Descendents are expected to finish configuring the
        # encoder and then commit the port format themselves

    def _create_pool(self):
        """
        Allocates a pool of MMAL buffers for the encoder.

        This method is expected to construct an MMAL pool of buffers for the
        :attr:`output_port`, and store the result in the :attr:`pool`
        attribute.
        """
        assert not self.pool
        self.pool = mmal.mmal_port_pool_create(
            self.output_port,
            self.output_port[0].buffer_num,
            self.output_port[0].buffer_size)
        if not self.pool:
            raise PiCameraError(
                "Failed to create buffer header pool for encoder component")

    def _create_connections(self):
        """
        Creates all connections between MMAL components.

        This method is called to connect the encoder and the optional resizer
        to the input port provided by the camera. It sets the
        :attr:`encoder_connection` and :attr:`resizer_connection` attributes as
        required.
        """
        assert not self.encoder_connection
        if self.resizer:
            self.resizer_connection = self.parent._connect_ports(
                self.input_port, self.resizer[0].input[0])
            self.encoder_connection = self.parent._connect_ports(
                self.resizer[0].output[0], self.encoder[0].input[0])
        else:
            self.encoder_connection = self.parent._connect_ports(
                self.input_port, self.encoder[0].input[0])

    def _callback(self, port, buf):
        """
        The encoder's main callback function.

        When the encoder is active, this method is periodically called in a
        background thread. The *port* parameter specifies the MMAL port
        providing the output (typically this is the encoder's output port, but
        in the case of unencoded captures may simply be a camera port), while
        the *buf* parameter is an MMAL buffer header pointer which can be used
        to obtain the data to write, along with meta-data about the current
        frame.

        This method *must* release the MMAL buffer header before returning
        (failure to do so will cause a lockup), and should recycle buffers if
        expecting further data (the :meth:`_callback_recycle` method can be
        called to perform the latter duty). Finally, this method must set
        :attr:`event` when the encoder has finished (and should set
        :attr:`exception` if an exception occurred during encoding).

        Developers wishing to write a custom encoder class may find it simpler
        to override the :meth:`_callback_write` method, rather than deal with
        these complexities.
        """
        if self.stopped:
            mmal.mmal_buffer_header_release(buf)
        else:
            stop = False
            try:
                try:
                    mmal_check(
                        mmal.mmal_buffer_header_mem_lock(buf),
                        prefix="Unable to lock buffer header memory")
                    try:
                        stop = self._callback_write(buf)
                    finally:
                        mmal.mmal_buffer_header_mem_unlock(buf)
                finally:
                    mmal.mmal_buffer_header_release(buf)
                    self._callback_recycle(port, buf)
            except Exception as e:
                stop = True
                self.exception = e
            if stop:
                self.stopped = True
                self.event.set()

    def _callback_write(self, buf, key=PiVideoFrameType.frame):
        """
        Writes output on behalf of the encoder callback function.

        This method is called by :meth:`_callback` to handle writing to an
        object in :attr:`outputs` identified by *key*. The *buf* parameter is
        an MMAL buffer header pointer which can be used to obtain the length of
        data available (``buf[0].length``), a pointer to the data
        (``buf[0].data``) which should typically be used with
        :func:`ctypes.string_at`, and meta-data about the contents of the
        buffer (``buf[0].flags``). The method is expected to return a boolean
        to indicate whether output is complete (``True``) or whether more data
        is expected (``False``).

        The default implementation simply writes the contents of the buffer to
        the output identified by *key*, and returns ``True`` if the buffer
        flags indicate end of stream. Image encoders will typically override
        the return value to indicate ``True`` on end of frame (as they only
        wish to output a single image). Video encoders will typically override
        this method to determine where key-frames and SPS headers occur.
        """
        if buf[0].length:
            with self.outputs_lock:
                try:
                    written = self.outputs[key][0].write(
                       ct.string_at(buf[0].data, buf[0].length))
                except KeyError:
                    pass
                else:
                    # Ignore None return value; most Python 2 streams have
                    # no return value for write()
                    if (written is not None) and (written != buf[0].length):
                        raise PiCameraError(
                            "Unable to write buffer to output %s" % key)
        return bool(buf[0].flags & mmal.MMAL_BUFFER_HEADER_FLAG_EOS)

    def _callback_recycle(self, port, buf):
        """
        Recycles the buffer on behalf of the encoder callback function.

        This method is called by :meth:`_callback` when there is a buffer to
        recycle (because further output is expected). It is unlikely descendent
        classes will have a need to override this method, but if they override
        the :meth:`_callback` method they may wish to call it.
        """
        new_buf = mmal.mmal_queue_get(self.pool[0].queue)
        if not new_buf:
            raise PiCameraError(
                "Unable to get a buffer to return to the encoder port")
        mmal_check(
            mmal.mmal_port_send_buffer(port, new_buf),
            prefix="Unable to return a buffer to the encoder port")

    def _open_output(self, output, key=PiVideoFrameType.frame):
        """
        Opens *output* and associates it with *key* in :attr:`outputs`.

        If *output* is a string, this method opens it as a filename and keeps
        track of the fact that the encoder was the one to open it (which
        implies that :meth:`_close_output` should eventually close it).
        Otherwise, *output* is assumed to be a file-like object and is used
        verbatim. The opened output is added to the :attr:`outputs` dictionary
        with the specified *key*.
        """
        with self.outputs_lock:
            opened = isinstance(output, (bytes, str))
            if opened:
                # Open files in binary mode with a decent buffer size
                output = io.open(output, 'wb', buffering=65536)
            self.outputs[key] = (output, opened)

    def _close_output(self, key=PiVideoFrameType.frame):
        """
        Closes the output associated with *key* in :attr:`outputs`.

        Closes the output object associated with the specified *key*, and
        removes it from the :attr:`outputs` dictionary (if we didn't open the
        object then we attempt to flush it instead).
        """
        with self.outputs_lock:
            try:
                (output, opened) = self.outputs.pop(key)
            except KeyError:
                pass
            else:
                if opened:
                    output.close()
                else:
                    try:
                        output.flush()
                    except AttributeError:
                        pass

    @property
    def active(self):
        """
        Returns ``True`` if the MMAL encoder exists and is enabled.
        """
        return bool(self.encoder and self.output_port[0].is_enabled)

    def start(self, output):
        """
        Starts the encoder object writing to the specified output.

        This method is called by the camera to start the encoder capturing
        data from the camera to the specified output. The *output* parameter
        is either a filename, or a file-like object (for image and video
        encoders), or an iterable of filenames or file-like objects (for
        multi-image encoders).
        """
        self.event.clear()
        self.stopped = False
        self.exception = None
        self._open_output(output)
        self.output_port[0].userdata = ct.cast(
            ct.pointer(ct.py_object(self)),
            ct.c_void_p)
        with self.parent._encoders_lock:
            mmal_check(
                mmal.mmal_port_enable(self.output_port, _encoder_callback),
                prefix="Failed to enable encoder output port")
            for q in range(mmal.mmal_queue_length(self.pool[0].queue)):
                buf = mmal.mmal_queue_get(self.pool[0].queue)
                if not buf:
                    raise PiCameraRuntimeError(
                        "Unable to get a required buffer from pool queue")
                mmal_check(
                    mmal.mmal_port_send_buffer(self.output_port, buf),
                    prefix="Unable to send a buffer to encoder output port")
            self.parent._start_capture(self.camera_port)

    def wait(self, timeout=None):
        """
        Waits for the encoder to finish (successfully or otherwise).

        This method is called by the owning camera object to block execution
        until the encoder has completed its task. If the *timeout* parameter
        is None, the method will block indefinitely. Otherwise, the *timeout*
        parameter specifies the (potentially fractional) number of seconds
        to block for. If the encoder finishes successfully within the timeout,
        the method returns ``True``. Otherwise, it returns ``False``.
        """
        result = self.event.wait(timeout)
        if result:
            self.stop()
            # Check whether the callback set an exception
            if self.exception:
                raise self.exception
        return result

    def stop(self):
        """
        Stops the encoder, regardless of whether it's finished.

        This method is called by the camera to terminate the execution of the
        encoder. Typically, this is used with video to stop the recording, but
        can potentially be called in the middle of image capture to terminate
        the capture.
        """
        # The check below is not a race condition; we ignore the EINVAL error
        # in the case the port turns out to be disabled when we disable below.
        # The check exists purely to prevent stderr getting spammed by our
        # continued attempts to disable an already disabled port
        with self.parent._encoders_lock:
            if self.active:
                self.parent._stop_capture(self.camera_port)
                try:
                    mmal_check(
                        mmal.mmal_port_disable(self.output_port),
                        prefix="Failed to disable encoder output port")
                except PiCameraMMALError as e:
                    if e.status != mmal.MMAL_EINVAL:
                        raise
        self.stopped = True
        self.event.set()
        self._close_output()

    def close(self):
        """
        Finalizes the encoder and deallocates all structures.

        This method is called by the camera prior to destroying the encoder (or
        more precisely, letting it go out of scope to permit the garbage
        collector to destroy it at some future time). The method destroys all
        components that the various create methods constructed and resets their
        attributes.
        """
        self.stop()
        if self.encoder_connection:
            mmal.mmal_connection_destroy(self.encoder_connection)
            self.encoder_connection = None
        if self.pool:
            mmal.mmal_port_pool_destroy(self.output_port, self.pool)
            self.pool = None
        if self.resizer_connection:
            mmal.mmal_connection_destroy(self.resizer_connection)
        if self.encoder:
            mmal.mmal_component_destroy(self.encoder)
            self.encoder = None
        if self.resizer:
            mmal.mmal_component_destroy(self.resizer)
            self.resizer = None
        self.output_port = None


class PiRawMixin(PiEncoder):
    """
    Mixin class for "raw" (unencoded) output.

    This mixin class overrides the initializer of :class:`PiEncoder`, along
    with :meth:`_create_resizer` and :meth:`_create_encoder` to configure the
    pipeline for unencoded output. Specifically, it disables the construction
    of an encoder, and sets the output port to the input port passed to the
    initializer, unless resizing is required (either for actual resizing, or
    for format conversion) in which case the resizer's output is used.
    """

    RAW_ENCODINGS = {
        # name   mmal-encoding            bytes-per-pixel
        'yuv':  (mmal.MMAL_ENCODING_I420, 1.5),
        'rgb':  (mmal.MMAL_ENCODING_RGBA, 3),
        'rgba': (mmal.MMAL_ENCODING_RGBA, 4),
        'bgr':  (mmal.MMAL_ENCODING_BGRA, 3),
        'bgra': (mmal.MMAL_ENCODING_BGRA, 4),
        }

    def __init__(
            self, parent, camera_port, input_port, format, resize, **options):
        # If a resize hasn't been requested, check the input_port format. If
        # it requires conversion, force the use of a resizer to perform the
        # conversion
        if not resize:
            if parent.RAW_FORMATS[format] != input_port[0].format[0].encoding.value:
                resize = parent.resolution
        # Workaround: If a non-alpha format is requested when a resizer is
        # required, we use the alpha-inclusive format and set a flag to get the
        # callback to strip the alpha bytes (for some reason the resizer won't
        # work with non-alpha output formats - firmware bug?)
        if resize:
            width, height = resize
            self._strip_alpha = format in ('rgb', 'bgr')
        else:
            width, height = parent.resolution
            self._strip_alpha = False
        width = mmal.VCOS_ALIGN_UP(width, 32)
        height = mmal.VCOS_ALIGN_UP(height, 16)
        # Workaround (#83): when the resizer is used the width and height must
        # be aligned (both the actual and crop values) to avoid an error when
        # the output port format is set
        if resize:
            resize = (width, height)
        # Workaround: Calculate the expected image size, to be used by the
        # callback to decide when a frame ends. This is to work around a
        # firmware bug that causes the raw image to be returned twice when the
        # maximum camera resolution is requested
        self._frame_size = int(width * height * self.RAW_ENCODINGS[format][1])
        super(PiRawMixin, self).__init__(
                parent, camera_port, input_port, format, resize, **options)

    def _create_resizer(self, width, height):
        """
        Overridden to configure the resizer's output with the required
        encoding.
        """
        super(PiRawMixin, self)._create_resizer(width, height)
        encoding = self.RAW_ENCODINGS[self.format][0]
        port = self.resizer[0].output[0]
        port[0].format[0].encoding = encoding
        port[0].format[0].encoding_variant = encoding
        mmal_check(
            mmal.mmal_port_format_commit(port),
            prefix="Failed to set resizer output port format")

    def _create_encoder(self):
        """
        Overridden to skip creating an encoder. Instead, this class simply uses
        the resizer's port as the output port (if a resizer has been
        configured) or the specified input port otherwise.
        """
        if self.resizer:
            self.output_port = self.resizer[0].output[0]
        else:
            self.output_port = self.input_port

    def _create_connections(self):
        """
        Overridden to skip creating an encoder connection; only a resizer
        connection is required (if one has been configured).
        """
        if self.resizer:
            self.resizer_connection = self.parent._connect_ports(
                self.input_port, self.resizer[0].input[0])

    @property
    def active(self):
        return bool(self.output_port[0].is_enabled)

    def _callback_write(self, buf, key=PiVideoFrameType.frame):
        """
        Overridden to strip alpha bytes when required.
        """
        if self._strip_alpha:
            s = ct.string_at(buf[0].data, buf[0].length)
            s = bytearray(s)
            del s[3::4]
            # All this messing around with buffers is to work around some issue
            # with MMAL or ctypes (I'm not sure which is at fault). Anyway, the
            # upshot is that if you fiddle with buf[0].data in any way
            # whatsoever (even if you make every attempt to restore its value
            # afterward), mmal_port_disable locks up when we call it in stop()
            new_buf = mmal.MMAL_BUFFER_HEADER_T.from_buffer_copy(buf[0])
            new_buf.length = len(s)
            new_buf.data = ct.pointer(ct.c_uint8.from_buffer(s))
            return super(PiRawMixin, self)._callback_write(ct.pointer(new_buf), key)
        else:
            return super(PiRawMixin, self)._callback_write(buf, key)


class PiVideoEncoder(PiEncoder):
    """
    Encoder for video recording.

    This derivative of :class:`PiEncoder` configures itself for H.264 or MJPEG
    encoding.  It also introduces a :meth:`split` method which is used by
    :meth:`~picamera.camera.PiCamera.split_recording` and
    :meth:`~picamera.camera.PiCamera.record_sequence` to redirect future output
    to a new filename or object. Finally, it also extends
    :meth:`PiEncoder.start` and :meth:`PiEncoder._callback_write` to track
    video frame meta-data, and to permit recording motion data to a separate
    output object.
    """

    encoder_type = mmal.MMAL_COMPONENT_DEFAULT_VIDEO_ENCODER

    def __init__(
            self, parent, camera_port, input_port, format, resize, **options):
        super(PiVideoEncoder, self).__init__(
                parent, camera_port, input_port, format, resize, **options)
        self._next_output = []
        self.frame = None

    def _create_encoder(
            self, bitrate=17000000, intra_period=None, profile='high',
            quantization=0, quality=0, inline_headers=True, sei=False,
            motion_output=None, intra_refresh=None):
        """
        Extends the base :meth:`~PiEncoder._create_encoder` implementation to
        configure the video encoder for H.264 or MJPEG output.
        """
        super(PiVideoEncoder, self)._create_encoder()

        # XXX Remove quantization in 2.0
        quality = quality or quantization

        try:
            self.output_port[0].format[0].encoding = {
                'h264':  mmal.MMAL_ENCODING_H264,
                'mjpeg': mmal.MMAL_ENCODING_MJPEG,
                }[self.format]
        except KeyError:
            raise PiCameraValueError('Unrecognized format %s' % self.format)

        if not (0 <= bitrate <= 25000000):
            raise PiCameraValueError('bitrate must be between 0 and 25Mbps')
        self.output_port[0].format[0].bitrate = bitrate
        self.output_port[0].format[0].es[0].video.frame_rate.num = 0
        self.output_port[0].format[0].es[0].video.frame_rate.den = 1
        mmal_check(
            mmal.mmal_port_format_commit(self.output_port),
            prefix="Unable to set format on encoder output port")

        if self.format == 'h264':
            mp = mmal.MMAL_PARAMETER_VIDEO_PROFILE_T(
                    mmal.MMAL_PARAMETER_HEADER_T(
                        mmal.MMAL_PARAMETER_PROFILE,
                        ct.sizeof(mmal.MMAL_PARAMETER_VIDEO_PROFILE_T),
                        ),
                    )
            try:
                mp.profile[0].profile = {
                    'baseline':    mmal.MMAL_VIDEO_PROFILE_H264_BASELINE,
                    'main':        mmal.MMAL_VIDEO_PROFILE_H264_MAIN,
                    'high':        mmal.MMAL_VIDEO_PROFILE_H264_HIGH,
                    'constrained': mmal.MMAL_VIDEO_PROFILE_H264_CONSTRAINED_BASELINE,
                }[profile]
            except KeyError:
                raise PiCameraValueError("Invalid H.264 profile %s" % profile)
            mp.profile[0].level = mmal.MMAL_VIDEO_LEVEL_H264_4
            mmal_check(
                mmal.mmal_port_parameter_set(self.output_port, mp.hdr),
                prefix="Unable to set encoder H.264 profile")

            if inline_headers:
                mmal_check(
                    mmal.mmal_port_parameter_set_boolean(
                        self.output_port,
                        mmal.MMAL_PARAMETER_VIDEO_ENCODE_INLINE_HEADER,
                        mmal.MMAL_TRUE),
                    prefix="Unable to set inline_headers")

            if sei:
                mmal_check(
                    mmal.mmal_port_parameter_set_boolean(
                        self.output_port,
                        mmal.MMAL_PARAMETER_VIDEO_ENCODE_SEI_ENABLE,
                        mmal.MMAL_TRUE),
                    prefix="Unable to set SEI")

            if motion_output:
                mmal_check(
                    mmal.mmal_port_parameter_set_boolean(
                        self.output_port,
                        mmal.MMAL_PARAMETER_VIDEO_ENCODE_INLINE_VECTORS,
                        mmal.MMAL_TRUE),
                    prefix="Unable to set inline motion vectors")

            # We need the intra-period to calculate the SPS header timeout in
            # the split method below. If one is not set explicitly, query the
            # encoder's default
            if intra_period is not None:
                mp = mmal.MMAL_PARAMETER_UINT32_T(
                        mmal.MMAL_PARAMETER_HEADER_T(
                            mmal.MMAL_PARAMETER_INTRAPERIOD,
                            ct.sizeof(mmal.MMAL_PARAMETER_UINT32_T),
                            ),
                        intra_period
                        )
                mmal_check(
                    mmal.mmal_port_parameter_set(self.output_port, mp.hdr),
                    prefix="Unable to set encoder intra_period")
                self._intra_period = intra_period
            else:
                mp = mmal.MMAL_PARAMETER_UINT32_T(
                    mmal.MMAL_PARAMETER_HEADER_T(
                        mmal.MMAL_PARAMETER_INTRAPERIOD,
                        ct.sizeof(mmal.MMAL_PARAMETER_UINT32_T),
                        ))
                mmal_check(
                    mmal.mmal_port_parameter_get(self.output_port, mp.hdr),
                    prefix="Unable to get encoder intra_period")
                self._intra_period = mp.value

            if intra_refresh is not None:
                # Get the intra-refresh structure first as there are several
                # other fields in it which we don't wish to overwrite
                mp = mmal.MMAL_PARAMETER_VIDEO_INTRA_REFRESH_T(
                        mmal.MMAL_PARAMETER_HEADER_T(
                            mmal.MMAL_PARAMETER_VIDEO_INTRA_REFRESH,
                            ct.sizeof(mmal.MMAL_PARAMETER_VIDEO_INTRA_REFRESH_T),
                            ))
                # Deliberately avoid checking whether this call succeeds
                mmal.mmal_port_parameter_get(self.output_port, mp.hdr)
                try:
                    mp.refresh_mode = {
                        'cyclic':     mmal.MMAL_VIDEO_INTRA_REFRESH_CYCLIC,
                        'adaptive':   mmal.MMAL_VIDEO_INTRA_REFRESH_ADAPTIVE,
                        'both':       mmal.MMAL_VIDEO_INTRA_REFRESH_BOTH,
                        'cyclicrows': mmal.MMAL_VIDEO_INTRA_REFRESH_CYCLIC_MROWS,
                        }[intra_refresh]
                except KeyError:
                    raise PiCameraValueError(
                        "Invalid intra_refresh %s" % intra_refresh)
                mmal_check(
                    mmal.mmal_port_parameter_set(self.output_port, mp.hdr),
                    prefix="Unable to set encoder intra_refresh")

        elif self.format == 'mjpeg':
            # MJPEG doesn't have an intra_period setting as such, but as every
            # frame is a full-frame, the intra_period is effectively 1
            self._intra_period = 1

        if quality:
            mp = mmal.MMAL_PARAMETER_UINT32_T(
                    mmal.MMAL_PARAMETER_HEADER_T(
                        mmal.MMAL_PARAMETER_VIDEO_ENCODE_INITIAL_QUANT,
                        ct.sizeof(mmal.MMAL_PARAMETER_UINT32_T),
                        ),
                    quality
                    )
            mmal_check(
                mmal.mmal_port_parameter_set(self.output_port, mp.hdr),
                prefix="Unable to set initial quality")
            mp = mmal.MMAL_PARAMETER_UINT32_T(
                    mmal.MMAL_PARAMETER_HEADER_T(
                        mmal.MMAL_PARAMETER_VIDEO_ENCODE_MIN_QUANT,
                        ct.sizeof(mmal.MMAL_PARAMETER_UINT32_T),
                        ),
                    quality,
                    )
            mmal_check(
                mmal.mmal_port_parameter_set(self.output_port, mp.hdr),
                prefix="Unable to set minimum quality")
            mp = mmal.MMAL_PARAMETER_UINT32_T(
                    mmal.MMAL_PARAMETER_HEADER_T(
                        mmal.MMAL_PARAMETER_VIDEO_ENCODE_MAX_QUANT,
                        ct.sizeof(mmal.MMAL_PARAMETER_UINT32_T),
                        ),
                    quality,
                    )
            mmal_check(
                mmal.mmal_port_parameter_set(self.output_port, mp.hdr),
                prefix="Unable to set maximum quality")

        mmal_check(
            mmal.mmal_port_parameter_set_boolean(
                self.encoder[0].input[0],
                mmal.MMAL_PARAMETER_VIDEO_IMMUTABLE_INPUT,
                1),
            prefix="Unable to set immutable flag on encoder input port")

        mmal_check(
            mmal.mmal_component_enable(self.encoder),
            prefix="Unable to enable video encoder component")

    def start(self, output, motion_output=None):
        """
        Extended to initialize video frame meta-data tracking.
        """
        self.frame = PiVideoFrame(
                index=0,
                frame_type=None,
                frame_size=0,
                video_size=0,
                split_size=0,
                timestamp=0,
                complete=False,
                )
        if motion_output is not None:
            self._open_output(motion_output, PiVideoFrameType.motion_data)
        super(PiVideoEncoder, self).start(output)

    def stop(self):
        super(PiVideoEncoder, self).stop()
        self._close_output(PiVideoFrameType.motion_data)

    def split(self, output, motion_output=None):
        """
        Called to switch the encoder's output.

        This method is called by
        :meth:`~picamera.camera.PiCamera.split_recording` and
        :meth:`~picamera.camera.PiCamera.record_sequence` to switch the
        encoder's :attr:`output` object to the *output* parameter (which can be
        a filename or a file-like object, as with :meth:`start`).
        """
        with self.outputs_lock:
            outputs = {}
            if output is not None:
                outputs[PiVideoFrameType.frame] = output
            if motion_output is not None:
                outputs[PiVideoFrameType.motion_data] = motion_output
            self._next_output.append(outputs)
        # intra_period / framerate gives the time between I-frames (which
        # should also coincide with SPS headers). We multiply by three to
        # ensure the timeout is deliberately excessive, and clamp the minimum
        # timeout to 1 second (otherwise unencoded formats tend to fail
        # presumably due to I/O capacity)
        timeout = max(1.0, float(self._intra_period / self.parent.framerate) * 3.0)
        if not self.event.wait(timeout):
            raise PiCameraRuntimeError(
                'Timed out waiting for a split point')
        self.event.clear()

    def _callback_write(self, buf, key=PiVideoFrameType.frame):
        """
        Extended to implement video frame meta-data tracking, and to handle
        splitting video recording to the next output when :meth:`split` is
        called.
        """
        self.frame = PiVideoFrame(
            index=
                self.frame.index + 1
                if self.frame.complete else
                self.frame.index,
            frame_type=
                PiVideoFrameType.key_frame
                if buf[0].flags & mmal.MMAL_BUFFER_HEADER_FLAG_KEYFRAME else
                PiVideoFrameType.sps_header
                if buf[0].flags & mmal.MMAL_BUFFER_HEADER_FLAG_CONFIG else
                PiVideoFrameType.motion_data
                if buf[0].flags & mmal.MMAL_BUFFER_HEADER_FLAG_CODECSIDEINFO else
                PiVideoFrameType.frame,
            frame_size=
                buf[0].length
                if self.frame.complete else
                self.frame.frame_size + buf[0].length,
            video_size=
                self.frame.video_size
                if buf[0].flags & mmal.MMAL_BUFFER_HEADER_FLAG_CODECSIDEINFO else
                self.frame.video_size + buf[0].length,
            split_size=
                self.frame.split_size
                if buf[0].flags & mmal.MMAL_BUFFER_HEADER_FLAG_CODECSIDEINFO else
                self.frame.split_size + buf[0].length,
            timestamp=
                None
                if buf[0].pts in (0, mmal.MMAL_TIME_UNKNOWN) else
                buf[0].pts,
            complete=
                bool(buf[0].flags & mmal.MMAL_BUFFER_HEADER_FLAG_FRAME_END),
            )
        if self.format != 'h264' or (buf[0].flags & mmal.MMAL_BUFFER_HEADER_FLAG_CONFIG):
            with self.outputs_lock:
                try:
                    new_outputs = self._next_output.pop(0)
                except IndexError:
                    new_outputs = None
            if new_outputs:
                for new_key, new_output in new_outputs.items():
                    self._close_output(new_key)
                    self._open_output(new_output, new_key)
                    if new_key == PiVideoFrameType.frame:
                        self.frame = PiVideoFrame(
                                index=self.frame.index,
                                frame_type=self.frame.frame_type,
                                frame_size=self.frame.frame_size,
                                video_size=self.frame.video_size,
                                split_size=0,
                                timestamp=self.frame.timestamp,
                                complete=self.frame.complete,
                                )
                self.event.set()
        if buf[0].flags & mmal.MMAL_BUFFER_HEADER_FLAG_CODECSIDEINFO:
            key = PiVideoFrameType.motion_data
        return super(PiVideoEncoder, self)._callback_write(buf, key)


class PiCookedVideoEncoder(PiVideoEncoder):
    """
    Video encoder for encoded recordings.

    This class is a derivative of :class:`PiVideoEncoder` and only exists to
    provide naming symmetry with the image encoder classes.
    """


class PiRawVideoEncoder(PiRawMixin, PiVideoEncoder):
    """
    Video encoder for unencoded recordings.

    This class is a derivative of :class:`PiVideoEncoder` and the
    :class:`PiRawMixin` class intended for use with
    :meth:`~picamera.camera.PiCamera.start_recording` when it is called with an
    unencoded format.

    .. warning::

        This class creates an inheritance diamond. Take care to determine the
        MRO of super-class calls.
    """

    def _create_encoder(self):
        super(PiRawVideoEncoder, self)._create_encoder()
        # Raw formats don't have an intra_period setting as such, but as every
        # frame is a full-frame, the intra_period is effectively 1
        self._intra_period = 1


class PiImageEncoder(PiEncoder):
    """
    Encoder for image capture.

    This derivative of :class:`PiEncoder` extends the :meth:`_create_encoder`
    method to configure the encoder for a variety of encoded image outputs
    (JPEG, PNG, etc.).
    """

    encoder_type = mmal.MMAL_COMPONENT_DEFAULT_IMAGE_ENCODER

    def _create_encoder(self, quality=85, thumbnail=(64, 48, 35), bayer=False):
        """
        Extends the base :meth:`~PiEncoder._create_encoder` implementation to
        configure the image encoder for JPEG, PNG, etc.
        """
        super(PiImageEncoder, self)._create_encoder()

        try:
            self.output_port[0].format[0].encoding = {
                'jpeg': mmal.MMAL_ENCODING_JPEG,
                'png':  mmal.MMAL_ENCODING_PNG,
                'gif':  mmal.MMAL_ENCODING_GIF,
                'bmp':  mmal.MMAL_ENCODING_BMP,
                }[self.format]
        except KeyError:
            raise PiCameraValueError("Unrecognized format %s" % self.format)
        mmal_check(
            mmal.mmal_port_format_commit(self.output_port),
            prefix="Unable to set format on encoder output port")

        if self.format == 'jpeg':
            mmal_check(
                mmal.mmal_port_parameter_set_uint32(
                    self.output_port,
                    mmal.MMAL_PARAMETER_JPEG_Q_FACTOR,
                    quality),
                prefix="Failed to set JPEG quality")

            mmal_check(
                mmal.mmal_port_parameter_set_boolean(
                    self.camera_port,
                    mmal.MMAL_PARAMETER_ENABLE_RAW_CAPTURE,
                    int(bool(bayer))),
                prefix="Failed to set raw capture")

            if thumbnail is None:
                mp = mmal.MMAL_PARAMETER_THUMBNAIL_CONFIG_T(
                    mmal.MMAL_PARAMETER_HEADER_T(
                        mmal.MMAL_PARAMETER_THUMBNAIL_CONFIGURATION,
                        ct.sizeof(mmal.MMAL_PARAMETER_THUMBNAIL_CONFIG_T)
                        ),
                    0, 0, 0, 0)
            else:
                mp = mmal.MMAL_PARAMETER_THUMBNAIL_CONFIG_T(
                    mmal.MMAL_PARAMETER_HEADER_T(
                        mmal.MMAL_PARAMETER_THUMBNAIL_CONFIGURATION,
                        ct.sizeof(mmal.MMAL_PARAMETER_THUMBNAIL_CONFIG_T)
                        ),
                    1, *thumbnail)
            mmal_check(
                mmal.mmal_port_parameter_set(self.encoder[0].control, mp.hdr),
                prefix="Failed to set thumbnail configuration")

        mmal_check(
            mmal.mmal_component_enable(self.encoder),
            prefix="Unable to enable encoder component")


class PiOneImageEncoder(PiImageEncoder):
    """
    Encoder for single image capture.

    This class simply extends :meth:`~PiEncoder._callback_write` to terminate
    capture at frame end (i.e. after a single frame has been received).
    """

    def _callback_write(self, buf, key=PiVideoFrameType.frame):
        return (
            super(PiOneImageEncoder, self)._callback_write(buf, key)
            ) or bool(
            buf[0].flags & (
                mmal.MMAL_BUFFER_HEADER_FLAG_FRAME_END |
                mmal.MMAL_BUFFER_HEADER_FLAG_TRANSMISSION_FAILED)
            )


class PiMultiImageEncoder(PiImageEncoder):
    """
    Encoder for multiple image capture.

    This class extends :class:`PiImageEncoder` to handle an iterable of outputs
    instead of a single output. The :meth:`~PiEncoder._callback_write` method
    is extended to terminate capture when the iterable is exhausted, while
    :meth:`PiEncoder._open_output` is overridden to begin iteration and rely
    on the new :meth:`_next_output` method to advance output to the next item
    in the iterable.
    """

    def _open_output(self, outputs, key=PiVideoFrameType.frame):
        self._output_iter = iter(outputs)
        self._next_output(key)

    def _next_output(self, key=PiVideoFrameType.frame):
        """
        This method moves output to the next item from the iterable passed to
        :meth:`~PiEncoder.start`.
        """
        self._close_output(key)
        super(PiMultiImageEncoder, self)._open_output(next(self._output_iter), key)

    def _callback_write(self, buf, key=PiVideoFrameType.frame):
        try:
            if (
                super(PiMultiImageEncoder, self)._callback_write(buf, key)
                ) or bool(
                buf[0].flags & (
                    mmal.MMAL_BUFFER_HEADER_FLAG_FRAME_END |
                    mmal.MMAL_BUFFER_HEADER_FLAG_TRANSMISSION_FAILED)
                ):
                self._next_output(key)
            return False
        except StopIteration:
            return True


class PiCookedOneImageEncoder(PiOneImageEncoder):
    """
    Encoder for "cooked" (encoded) single image output.

    This encoder extends :class:`PiOneImageEncoder` to include Exif tags in the
    output.
    """

    exif_encoding = 'ascii'

    def _add_exif_tag(self, tag, value):
        # Format the tag and value into an appropriate bytes string, encoded
        # with the Exif encoding (ASCII)
        if isinstance(tag, str):
            tag = tag.encode(self.exif_encoding)
        if isinstance(value, str):
            value = value.encode(self.exif_encoding)
        elif isinstance(value, datetime.datetime):
            value = value.strftime('%Y:%m:%d %H:%M:%S').encode(self.exif_encoding)
        # MMAL_PARAMETER_EXIF_T is a variable sized structure, hence all the
        # mucking about with string buffers here...
        buf = ct.create_string_buffer(
            ct.sizeof(mmal.MMAL_PARAMETER_EXIF_T) + len(tag) + len(value) + 1)
        mp = ct.cast(buf, ct.POINTER(mmal.MMAL_PARAMETER_EXIF_T))
        mp[0].hdr.id = mmal.MMAL_PARAMETER_EXIF
        mp[0].hdr.size = len(buf)
        if (b'=' in tag or b'\x00' in value):
            data = tag + value
            mp[0].keylen = len(tag)
            mp[0].value_offset = len(tag)
            mp[0].valuelen = len(value)
        else:
            data = tag + b'=' + value
        ct.memmove(mp[0].data, data, len(data))
        mmal_check(
            mmal.mmal_port_parameter_set(self.output_port, mp[0].hdr),
            prefix="Failed to set Exif tag %s" % tag)

    def start(self, output):
        timestamp = datetime.datetime.now()
        timestamp_tags = (
            'EXIF.DateTimeDigitized',
            'EXIF.DateTimeOriginal',
            'IFD0.DateTime')
        # Timestamp tags are always included with the value calculated
        # above, but the user may choose to override the value in the
        # exif_tags mapping
        for tag in timestamp_tags:
            self._add_exif_tag(tag, self.parent.exif_tags.get(tag, timestamp))
        # All other tags are just copied in verbatim
        for tag, value in self.parent.exif_tags.items():
            if not tag in timestamp_tags:
                self._add_exif_tag(tag, value)
        super(PiCookedOneImageEncoder, self).start(output)


class PiCookedMultiImageEncoder(PiMultiImageEncoder):
    """
    Encoder for "cooked" (encoded) multiple image output.

    This encoder descends from :class:`PiMultiImageEncoder` but includes no
    new functionality as video-port based encodes (which is all this class
    is used for) don't support Exif tag output.
    """
    pass


class PiRawImageMixin(PiRawMixin, PiImageEncoder):
    """
    Mixin class for "raw" (unencoded) image capture.

    The :meth:`_callback_write` method is overridden to manually calculate when
    to terminate output.
    """

    def __init__(
            self, parent, camera_port, input_port, format, resize, **options):
        super(PiRawImageMixin, self).__init__(
                parent, camera_port, input_port, format, resize, **options)
        self._image_size = 0

    def _callback_write(self, buf, key=PiVideoFrameType.frame):
        """
        Overridden to manually calculate when to terminate capture (see
        comments in :meth:`__init__`).
        """
        if self._image_size > 0:
            super(PiRawImageMixin, self)._callback_write(buf, key)
            self._image_size -= buf[0].length
        return self._image_size <= 0

    def start(self, output):
        self._image_size = self._frame_size
        super(PiRawImageMixin, self).start(output)


class PiRawOneImageEncoder(PiOneImageEncoder, PiRawImageMixin):
    """
    Single image encoder for unencoded capture.

    This class is a derivative of :class:`PiOneImageEncoder` and the
    :class:`PiRawImageMixin` class intended for use with
    :meth:`~picamera.camera.PiCamera.capture` (et al) when it is called with an
    unencoded image format.

    .. warning::

        This class creates an inheritance diamond. Take care to determine the
        MRO of super-class calls.
    """
    pass


class PiRawMultiImageEncoder(PiMultiImageEncoder, PiRawImageMixin):
    """
    Multiple image encoder for unencoded capture.

    This class is a derivative of :class:`PiMultiImageEncoder` and the
    :class:`PiRawImageMixin` class intended for use with
    :meth:`~picamera.camera.PiCamera.capture_sequence` when it is called with
    an unencoded image format.

    .. warning::

        This class creates an inheritance diamond. Take care to determine the
        MRO of super-class calls.
    """
    def _next_output(self, key=PiVideoFrameType.frame):
        super(PiRawMultiImageEncoder, self)._next_output(key)
        self._image_size = self._frame_size

