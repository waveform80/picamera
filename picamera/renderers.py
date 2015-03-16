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
The renderers module defines the renderer classes used by the camera to provide
preview and overlay output on the Pi's display. Users will rarely need to
construct instances of these classes directly
(:meth:`~picamera.camera.PiCamera.start_preview` and
:meth:`~picamera.camera.PiCamera.add_overlay` are generally used instead) but
may find the attribute references for them useful.

.. note::

    All classes in this module are available from the :mod:`picamera` namespace
    without having to import :mod:`picamera.renderers` directly.

The following classes are defined in the module:


PiRenderer
==========

.. autoclass:: PiRenderer
    :members:


PiOverlayRenderer
=================

.. autoclass:: PiOverlayRenderer
    :members:


PiPreviewRenderer
=================

.. autoclass:: PiPreviewRenderer
    :members:


PiNullSink
==========

.. autoclass:: PiNullSink
    :members:

"""

from __future__ import (
    unicode_literals,
    print_function,
    division,
    absolute_import,
    )

# Make Py2's str and range equivalent to Py3's
str = type('')

import ctypes as ct

import picamera.mmal as mmal
from picamera.exc import (
    PiCameraRuntimeError,
    PiCameraValueError,
    mmal_check,
    )


def _overlay_callback(port, buf):
    mmal.mmal_buffer_header_release(buf)
_overlay_callback = mmal.MMAL_PORT_BH_CB_T(_overlay_callback)


class PiRenderer(object):
    """
    Base implementation of an MMAL video renderer for use by PiCamera.

    The *parent* parameter specifies the :class:`~picamera.camera.PiCamera`
    instance that has constructed this renderer. The *layer* parameter
    specifies the layer that the renderer will inhabit. Higher numbered layers
    obscure lower numbered layers (unless they are partially transparent). The
    initial opacity of the renderer is specified by the *alpha* parameter
    (which defaults to 255, meaning completely opaque). The *fullscreen*
    parameter which defaults to ``True`` indicates whether the renderer should
    occupy the entire display.  Finally, the *window* parameter (which only has
    meaning when *fullscreen* is ``False``) is a four-tuple of ``(x, y, width,
    height)`` which gives the screen coordinates that the renderer should
    occupy when it isn't full-screen.

    This base class isn't directly used by :class:`~picamera.camera.PiCamera`,
    but the two derivatives defined below, :class:`PiOverlayRenderer` and
    :class:`PiPreviewRenderer`, are used to produce overlays and the camera
    preview respectively.
    """

    def __init__(
            self, parent, layer=0, alpha=255, fullscreen=True, window=None,
            crop=None, rotation=0, vflip=False, hflip=False):
        # Create and enable the renderer component
        self._rotation = 0
        self._vflip = False
        self._hflip = False
        self.parent = parent
        self.renderer = ct.POINTER(mmal.MMAL_COMPONENT_T)()
        mmal_check(
            mmal.mmal_component_create(
                mmal.MMAL_COMPONENT_DEFAULT_VIDEO_RENDERER, self.renderer),
            prefix="Failed to create renderer component")
        try:
            if not self.renderer[0].input_num:
                raise PiCameraError("No input ports on renderer component")

            self.layer = layer
            self.alpha = alpha
            self.fullscreen = fullscreen
            if window is not None:
                self.window = window
            if crop is not None:
                self.crop = crop
            self.rotation = rotation
            self.vflip = vflip
            self.hflip = hflip

            mmal_check(
                mmal.mmal_component_enable(self.renderer),
                prefix="Renderer component couldn't be enabled")
        except:
            mmal.mmal_component_destroy(self.renderer)
            raise

    def close(self):
        """
        Finalizes the renderer and deallocates all structures.

        This method is called by the camera prior to destroying the renderer
        (or more precisely, letting it go out of scope to permit the garbage
        collector to destroy it at some future time).
        """
        if self.renderer:
            mmal.mmal_component_destroy(self.renderer)
            self.renderer = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.close()

    def _get_alpha(self):
        mp = mmal.MMAL_DISPLAYREGION_T(
            mmal.MMAL_PARAMETER_HEADER_T(
                mmal.MMAL_PARAMETER_DISPLAYREGION,
                ct.sizeof(mmal.MMAL_DISPLAYREGION_T)
            ))
        mmal_check(
            mmal.mmal_port_parameter_get(self.renderer[0].input[0], mp.hdr),
            prefix="Failed to get alpha")
        return mp.alpha
    def _set_alpha(self, value):
        try:
            if not (0 <= value <= 255):
                raise PiCameraValueError(
                    "Invalid alpha value: %d (valid range 0..255)" % value)
        except TypeError:
            raise PiCameraValueError("Invalid alpha value: %s" % value)
        mp = mmal.MMAL_DISPLAYREGION_T(
            mmal.MMAL_PARAMETER_HEADER_T(
                mmal.MMAL_PARAMETER_DISPLAYREGION,
                ct.sizeof(mmal.MMAL_DISPLAYREGION_T)
                ),
            set=mmal.MMAL_DISPLAY_SET_ALPHA,
            alpha=value
            )
        mmal_check(
            mmal.mmal_port_parameter_set(self.renderer[0].input[0], mp.hdr),
            prefix="Failed to set alpha")
    alpha = property(_get_alpha, _set_alpha, doc="""
        Retrieves or sets the opacity of the renderer.

        When queried, the :attr:`alpha` property returns a value between 0 and
        255 indicating the opacity of the renderer, where 0 is completely
        transparent and 255 is completely opaque. The default value is 255. The
        property can be set while recordings or previews are in progress.
        """)

    def _get_layer(self):
        mp = mmal.MMAL_DISPLAYREGION_T(
            mmal.MMAL_PARAMETER_HEADER_T(
                mmal.MMAL_PARAMETER_DISPLAYREGION,
                ct.sizeof(mmal.MMAL_DISPLAYREGION_T)
            ))
        mmal_check(
            mmal.mmal_port_parameter_get(self.renderer[0].input[0], mp.hdr),
            prefix="Failed to get layer")
        return mp.layer
    def _set_layer(self, value):
        try:
            if not (0 <= value <= 255):
                raise PiCameraValueError(
                    "Invalid layer value: %d (valid range 0..255)" % value)
        except TypeError:
            raise PiCameraValueError("Invalid layer value: %s" % value)
        mp = mmal.MMAL_DISPLAYREGION_T(
            mmal.MMAL_PARAMETER_HEADER_T(
                mmal.MMAL_PARAMETER_DISPLAYREGION,
                ct.sizeof(mmal.MMAL_DISPLAYREGION_T)
                ),
            set=mmal.MMAL_DISPLAY_SET_LAYER,
            layer=value
            )
        mmal_check(
            mmal.mmal_port_parameter_set(self.renderer[0].input[0], mp.hdr),
            prefix="Failed to set layer")
    layer = property(
            _get_layer, _set_layer, doc="""
        Retrieves of sets the layer of the renderer.

        The :attr:`layer` property is an integer which controls the layer that
        the renderer occupies. Higher valued layers obscure lower valued layers
        (with 0 being the "bottom" layer). The default value is 2. The property
        can be set while recordings or previews are in progress.
        """)

    def _get_fullscreen(self):
        mp = mmal.MMAL_DISPLAYREGION_T(
            mmal.MMAL_PARAMETER_HEADER_T(
                mmal.MMAL_PARAMETER_DISPLAYREGION,
                ct.sizeof(mmal.MMAL_DISPLAYREGION_T)
            ))
        mmal_check(
            mmal.mmal_port_parameter_get(self.renderer[0].input[0], mp.hdr),
            prefix="Failed to get fullscreen")
        return mp.fullscreen != mmal.MMAL_FALSE
    def _set_fullscreen(self, value):
        mp = mmal.MMAL_DISPLAYREGION_T(
            mmal.MMAL_PARAMETER_HEADER_T(
                mmal.MMAL_PARAMETER_DISPLAYREGION,
                ct.sizeof(mmal.MMAL_DISPLAYREGION_T)
                ),
            set=mmal.MMAL_DISPLAY_SET_FULLSCREEN,
            fullscreen=bool(value)
            )
        mmal_check(
            mmal.mmal_port_parameter_set(self.renderer[0].input[0], mp.hdr),
            prefix="Failed to set fullscreen")
    fullscreen = property(
            _get_fullscreen, _set_fullscreen, doc="""
        Retrieves or sets whether the renderer appears full-screen.

        The :attr:`fullscreen` property is a bool which controls whether the
        renderer takes up the entire display or not. When set to ``False``, the
        :attr:`window` property can be used to control the precise size of the
        renderer display. The property can be set while recordings or previews
        are active.
        """)

    def _get_window(self):
        mp = mmal.MMAL_DISPLAYREGION_T(
            mmal.MMAL_PARAMETER_HEADER_T(
                mmal.MMAL_PARAMETER_DISPLAYREGION,
                ct.sizeof(mmal.MMAL_DISPLAYREGION_T)
            ))
        mmal_check(
            mmal.mmal_port_parameter_get(self.renderer[0].input[0], mp.hdr),
            prefix="Failed to get window")
        return (
            mp.dest_rect.x,
            mp.dest_rect.y,
            mp.dest_rect.width,
            mp.dest_rect.height,
            )
    def _set_window(self, value):
        try:
            x, y, w, h = value
        except (TypeError, ValueError) as e:
            raise PiCameraValueError(
                "Invalid window rectangle (x, y, w, h) tuple: %s" % value)
        mp = mmal.MMAL_DISPLAYREGION_T(
            mmal.MMAL_PARAMETER_HEADER_T(
                mmal.MMAL_PARAMETER_DISPLAYREGION,
                ct.sizeof(mmal.MMAL_DISPLAYREGION_T)
                ),
            set=mmal.MMAL_DISPLAY_SET_DEST_RECT,
            dest_rect=mmal.MMAL_RECT_T(x, y, w, h),
            )
        mmal_check(
            mmal.mmal_port_parameter_set(self.renderer[0].input[0], mp.hdr),
            prefix="Failed to set window")
    window = property(_get_window, _set_window, doc="""
        Retrieves or sets the size of the renderer.

        When the :attr:`fullscreen` property is set to ``False``, the
        :attr:`window` property specifies the size and position of the renderer
        on the display. The property is a 4-tuple consisting of ``(x, y, width,
        height)``. The property can be set while recordings or previews are
        active.
        """)

    def _get_crop(self):
        mp = mmal.MMAL_DISPLAYREGION_T(
            mmal.MMAL_PARAMETER_HEADER_T(
                mmal.MMAL_PARAMETER_DISPLAYREGION,
                ct.sizeof(mmal.MMAL_DISPLAYREGION_T)
            ))
        mmal_check(
            mmal.mmal_port_parameter_get(self.renderer[0].input[0], mp.hdr),
            prefix="Failed to get crop")
        return (
            mp.src_rect.x,
            mp.src_rect.y,
            mp.src_rect.width,
            mp.src_rect.height,
            )
    def _set_crop(self, value):
        try:
            x, y, w, h = value
        except (TypeError, ValueError) as e:
            raise PiCameraValueError(
                "Invalid crop rectangle (x, y, w, h) tuple: %s" % value)
        mp = mmal.MMAL_DISPLAYREGION_T(
            mmal.MMAL_PARAMETER_HEADER_T(
                mmal.MMAL_PARAMETER_DISPLAYREGION,
                ct.sizeof(mmal.MMAL_DISPLAYREGION_T)
                ),
            set=mmal.MMAL_DISPLAY_SET_SRC_RECT,
            src_rect=mmal.MMAL_RECT_T(x, y, w, h),
            )
        mmal_check(
            mmal.mmal_port_parameter_set(self.renderer[0].input[0], mp.hdr),
            prefix="Failed to set crop")
    crop = property(_get_crop, _set_crop, doc="""
        Retrieves or sets the area to read from the source.

        The :attr:`crop` property specifies the rectangular area that the
        renderer will read from the source as a 4-tuple of ``(x, y, width,
        height)``. The special value ``(0, 0, 0, 0)`` (which is also the
        default) means to read entire area of the source. The property can be
        set while recordings or previews are active.

        For example, if the camera's resolution is currently configured as
        1280x720, setting this attribute to ``(160, 160, 640, 400)`` will
        crop the preview to the center 640x400 pixels of the input. Note that
        this property does not affect the size of the output rectangle,
        which is controlled with :attr:`fullscreen` and :attr:`window`.

        .. note::

            This property only affects the renderer; it has no bearing on image
            captures or recordings (unlike the
            :attr:`~picamera.camera.PiCamera.zoom` property of the
            :class:`~picamera.camera.PiCamera` class).
        """)

    def _get_rotation(self):
        return self._rotation
    def _set_rotation(self, value):
        try:
            value = ((int(value) % 360) // 90) * 90
        except ValueError:
            raise PiCameraValueError("Invalid rotation angle: %s" % value)
        self._set_transform(
                self._get_transform(value, self._vflip, self._hflip))
        self._rotation = value
    rotation = property(_get_rotation, _set_rotation, doc="""
        Retrieves of sets the current rotation of the renderer.

        When queried, the :attr:`rotation` property returns the rotation
        applied to the renderer. Valid values are 0, 90, 180, and 270.

        When set, the property changes the rotation applied to the renderer's
        output. The property can be set while recordings or previews are
        active. The default is 0.

        .. note::

            This property only affects the renderer; it has no bearing on image
            captures or recordings (unlike the
            :attr:`~picamera.camera.PiCamera.rotation` property of the
            :class:`~picamera.camera.PiCamera` class).
        """)

    def _get_vflip(self):
        return self._vflip
    def _set_vflip(self, value):
        value = bool(value)
        self._set_transform(
                self._get_transform(self._rotation, value, self._hflip))
        self._vflip = value
    vflip = property(_get_vflip, _set_vflip, doc="""
        Retrieves of sets whether the renderer's output is vertically flipped.

        When queried, the :attr:`vflip` property returns a boolean indicating
        whether or not the renderer's output is vertically flipped. The
        property can be set while recordings or previews are in progress. The
        default is ``False``.

        .. note::

            This property only affects the renderer; it has no bearing on image
            captures or recordings (unlike the
            :attr:`~picamera.camera.PiCamera.vflip` property of the
            :class:`~picamera.camera.PiCamera` class).
        """)

    def _get_hflip(self):
        return self._hflip
    def _set_hflip(self, value):
        value = bool(value)
        self._set_transform(
                self._get_transform(self._rotation, self._vflip, value))
        self._hflip = value
    hflip = property(_get_hflip, _set_hflip, doc="""
        Retrieves of sets whether the renderer's output is horizontally
        flipped.

        When queried, the :attr:`vflip` property returns a boolean indicating
        whether or not the renderer's output is horizontally flipped. The
        property can be set while recordings or previews are in progress. The
        default is ``False``.

        .. note::

            This property only affects the renderer; it has no bearing on image
            captures or recordings (unlike the
            :attr:`~picamera.camera.PiCamera.hflip` property of the
            :class:`~picamera.camera.PiCamera` class).
        """)

    def _get_transform(self, rotate, vflip, hflip):
        # Use a (horizontally) mirrored transform if one of vflip or hflip is
        # set. If vflip is set, rotate by an extra 180 degrees to make up for
        # the lack of a "true" vertical flip
        mirror = vflip ^ hflip
        if vflip:
            rotate = (rotate + 180) % 360
        return {
            (0,   False): mmal.MMAL_DISPLAY_ROT0,
            (90,  False): mmal.MMAL_DISPLAY_ROT90,
            (180, False): mmal.MMAL_DISPLAY_ROT180,
            (270, False): mmal.MMAL_DISPLAY_ROT270,
            (0,   True):  mmal.MMAL_DISPLAY_MIRROR_ROT0,
            (90,  True):  mmal.MMAL_DISPLAY_MIRROR_ROT90,
            (180, True):  mmal.MMAL_DISPLAY_MIRROR_ROT180,
            (270, True):  mmal.MMAL_DISPLAY_MIRROR_ROT270,
            }[(rotate, mirror)]

    def _set_transform(self, value):
        mp = mmal.MMAL_DISPLAYREGION_T(
            mmal.MMAL_PARAMETER_HEADER_T(
                mmal.MMAL_PARAMETER_DISPLAYREGION,
                ct.sizeof(mmal.MMAL_DISPLAYREGION_T)
                ),
            set=mmal.MMAL_DISPLAY_SET_TRANSFORM,
            transform=value,
            )
        mmal_check(
            mmal.mmal_port_parameter_set(self.renderer[0].input[0], mp.hdr),
            prefix="Failed to set transform")


class PiOverlayRenderer(PiRenderer):
    """
    Represents an MMAL renderer with a static source for overlays.

    This class descends from :class:`PiRenderer` and adds a static source for
    the MMAL renderer. The optional *size* parameter specifies the size of the
    source image as a ``(width, height)`` tuple. If this is omitted or ``None``
    then the size is assumed to be the same as the parent camera's current
    :attr:`~picamera.camera.PiCamera.resolution`.

    The *source* must be an object that supports the :ref:`buffer protocol
    <bufferobjects>` which has the same length as an image in `RGB`_ format
    (colors represented as interleaved unsigned bytes) with the specified
    *size* after the width has been rounded up to the nearest multiple of 32,
    and the height has been rounded up to the nearest multiple of 16.

    For example, if *size* is ``(1280, 720)``, then *source* must be a buffer
    with length 1280 x 720 x 3 bytes, or 2,764,800 bytes (because 1280 is a
    multiple of 32, and 720 is a multiple of 16 no extra rounding is required).
    However, if *size* is ``(97, 57)``, then *source* must be a buffer with
    length 128 x 64 x 3 bytes, or 24,576 bytes (pixels beyond column 97 and row
    57 in the source will be ignored).

    The *layer*, *alpha*, *fullscreen*, and *window* parameters are the same
    as in :class:`PiRenderer`.

    .. _RGB: http://en.wikipedia.org/wiki/RGB
    """

    def __init__(
            self, parent, source, size=None, layer=0, alpha=255,
            fullscreen=True, window=None, crop=None, rotation=0, vflip=False,
            hflip=False):
        super(PiOverlayRenderer, self).__init__(
            parent, layer, alpha, fullscreen, window, crop,
            rotation, vflip, hflip)

        # Copy format from camera's preview port, then adjust the encoding to
        # RGB888 and optionally adjust the resolution and size
        port = self.renderer[0].input[0]
        fmt = port[0].format
        mmal.mmal_format_copy(
            fmt, parent._camera[0].output[parent.CAMERA_PREVIEW_PORT][0].format)
        fmt[0].encoding = mmal.MMAL_ENCODING_RGB24
        fmt[0].encoding_variant = mmal.MMAL_ENCODING_RGB24
        if size is not None:
            w, h = size
            fmt[0].es[0].video.width = mmal.VCOS_ALIGN_UP(w, 32)
            fmt[0].es[0].video.height = mmal.VCOS_ALIGN_UP(h, 16)
            fmt[0].es[0].video.crop.width = w
            fmt[0].es[0].video.crop.height = h
        mmal_check(
            mmal.mmal_port_format_commit(port),
            prefix="Overlay format couldn't be set")
        port[0].buffer_num = port[0].buffer_num_min
        port[0].buffer_size = port[0].buffer_size_recommended

        mmal_check(
            mmal.mmal_component_enable(self.renderer),
            prefix="Overlay couldn't be enabled")

        mmal_check(
            mmal.mmal_port_enable(port, _overlay_callback),
            prefix="Overlay input port couldn't be enabled")

        self.pool = mmal.mmal_port_pool_create(
            port, port[0].buffer_num, port[0].buffer_size)
        if not self.pool:
            raise PiCameraRuntimeError("Couldn't create pool for overlay")

        self.update(source)

    def close(self):
        super(PiOverlayRenderer, self).close()
        if self.pool:
            mmal.mmal_pool_destroy(self.pool)
            self.pool = None

    def update(self, source):
        """
        Update the overlay with a new source of data.

        The new *source* buffer must have the same size as the original buffer
        used to create the overlay. There is currently no method for changing
        the size of an existing overlay (remove and recreate the overlay if you
        require this).
        """
        port = self.renderer[0].input[0]
        fmt = port[0].format
        bp = ct.c_uint8 * (fmt[0].es[0].video.width * fmt[0].es[0].video.height * 3)
        try:
            sp = bp.from_buffer(source)
        except TypeError:
            sp = bp.from_buffer_copy(source)
        buf = mmal.mmal_queue_get(self.pool[0].queue)
        if not buf:
            raise PiCameraRuntimeError(
                "Couldn't get a buffer from the overlay's pool")
        ct.memmove(buf[0].data, sp, buf[0].alloc_size)
        buf[0].length = buf[0].alloc_size
        mmal_check(
            mmal.mmal_port_send_buffer(port, buf),
            prefix="Unable to send a buffer to the overlay's port")


class PiPreviewRenderer(PiRenderer):
    """
    Represents an MMAL renderer which uses the camera's preview as a source.

    This class descends from :class:`PiRenderer` and adds an MMAL connection to
    connect the renderer to an MMAL port. The *source* parameter specifies the
    MMAL port to connect to the renderer.

    The *layer*, *alpha*, *fullscreen*, and *window* parameters are the same
    as in :class:`PiRenderer`.
    """

    def __init__(
            self, parent, source, layer=2, alpha=255, fullscreen=True,
            window=None, crop=None, rotation=0, vflip=False, hflip=False):
        super(PiPreviewRenderer, self).__init__(
            parent, layer, alpha, fullscreen, window, crop,
            rotation, vflip, hflip)
        self.connection = self.parent._connect_ports(
            source, self.renderer[0].input[0])

    def close(self):
        if self.connection:
            mmal.mmal_connection_destroy(self.connection)
            self.connection = None
        super(PiPreviewRenderer, self).close()


class PiNullSink(object):
    """
    Implements an MMAL null-sink which can be used in place of a renderer.

    The *parent* parameter specifies the :class:`~picamera.camera.PiCamera`
    instance which constructed this null-sink. The *source* parameter specifies
    the MMAL port which the null-sink should connect to its input.

    The null-sink can act as a drop-in replacement for :class:`PiRenderer` in
    most cases, but obviously doesn't implement attributes like ``alpha``,
    ``layer``, etc. as it simply dumps any incoming frames. This is also the
    reason that this class doesn't derive from :class:`PiRenderer` like all
    other classes in this module.
    """

    def __init__(self, parent, source):
        self.parent = parent
        self.renderer = ct.POINTER(mmal.MMAL_COMPONENT_T)()
        mmal_check(
            mmal.mmal_component_create(
                mmal.MMAL_COMPONENT_DEFAULT_NULL_SINK, self.renderer),
            prefix="Failed to create null sink component")
        try:
            if not self.renderer[0].input_num:
                raise PiCameraError("No input ports on null sink component")
            mmal_check(
                mmal.mmal_component_enable(self.renderer),
                prefix="Null sink component couldn't be enabled")
        except:
            mmal.mmal_component_destroy(self.renderer)
            raise
        self.connection = self.parent._connect_ports(
            source, self.renderer[0].input[0])

    def close(self):
        """
        Finalizes the null-sink and deallocates all structures.

        This method is called by the camera prior to destroying the null-sink
        (or more precisely, letting it go out of scope to permit the garbage
        collector to destroy it at some future time).
        """
        if self.connection:
            mmal.mmal_connection_destroy(self.connection)
            self.connection = None
        if self.renderer:
            mmal.mmal_component_destroy(self.renderer)
            self.renderer = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.close()


