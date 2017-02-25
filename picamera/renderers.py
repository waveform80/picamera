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

import ctypes as ct

from . import mmal, mmalobj as mo
from .exc import (
    PiCameraRuntimeError,
    PiCameraValueError,
    mmal_check,
    )


class PiRenderer(object):
    """
    Wraps :class:`~mmalobj.MMALRenderer` for use by PiCamera.

    The *parent* parameter specifies the :class:`PiCamera` instance that has
    constructed this renderer. The *layer* parameter specifies the layer that
    the renderer will inhabit. Higher numbered layers obscure lower numbered
    layers (unless they are partially transparent). The initial opacity of the
    renderer is specified by the *alpha* parameter (which defaults to 255,
    meaning completely opaque). The *fullscreen* parameter which defaults to
    ``True`` indicates whether the renderer should occupy the entire display.
    Finally, the *window* parameter (which only has meaning when *fullscreen*
    is ``False``) is a four-tuple of ``(x, y, width, height)`` which gives the
    screen coordinates that the renderer should occupy when it isn't
    full-screen.

    This base class isn't directly used by :class:`PiCamera`, but the two
    derivatives defined below, :class:`PiOverlayRenderer` and
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
        self.renderer = mo.MMALRenderer()
        try:
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
            self.renderer.enable()
        except:
            self.renderer.close()
            raise

    def close(self):
        """
        Finalizes the renderer and deallocates all structures.

        This method is called by the camera prior to destroying the renderer
        (or more precisely, letting it go out of scope to permit the garbage
        collector to destroy it at some future time).
        """
        if self.renderer:
            self.renderer.close()
            self.renderer = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.close()

    def _get_alpha(self):
        return self.renderer.inputs[0].params[mmal.MMAL_PARAMETER_DISPLAYREGION].alpha
    def _set_alpha(self, value):
        try:
            if not (0 <= value <= 255):
                raise PiCameraValueError(
                    "Invalid alpha value: %d (valid range 0..255)" % value)
        except TypeError:
            raise PiCameraValueError("Invalid alpha value: %s" % value)
        mp = self.renderer.inputs[0].params[mmal.MMAL_PARAMETER_DISPLAYREGION]
        mp.set = mmal.MMAL_DISPLAY_SET_ALPHA
        mp.alpha = value
        self.renderer.inputs[0].params[mmal.MMAL_PARAMETER_DISPLAYREGION] = mp
    alpha = property(_get_alpha, _set_alpha, doc="""\
        Retrieves or sets the opacity of the renderer.

        When queried, the :attr:`alpha` property returns a value between 0 and
        255 indicating the opacity of the renderer, where 0 is completely
        transparent and 255 is completely opaque. The default value is 255. The
        property can be set while recordings or previews are in progress.

        .. note::

            If the renderer is being fed RGBA data (as in partially transparent
            overlays), the alpha property will be ignored.
        """)

    def _get_layer(self):
        return self.renderer.inputs[0].params[mmal.MMAL_PARAMETER_DISPLAYREGION].layer
    def _set_layer(self, value):
        try:
            if not (0 <= value <= 255):
                raise PiCameraValueError(
                    "Invalid layer value: %d (valid range 0..255)" % value)
        except TypeError:
            raise PiCameraValueError("Invalid layer value: %s" % value)
        mp = self.renderer.inputs[0].params[mmal.MMAL_PARAMETER_DISPLAYREGION]
        mp.set = mmal.MMAL_DISPLAY_SET_LAYER
        mp.layer = value
        self.renderer.inputs[0].params[mmal.MMAL_PARAMETER_DISPLAYREGION] = mp
    layer = property(_get_layer, _set_layer, doc="""\
        Retrieves or sets the layer of the renderer.

        The :attr:`layer` property is an integer which controls the layer that
        the renderer occupies. Higher valued layers obscure lower valued layers
        (with 0 being the "bottom" layer). The default value is 2. The property
        can be set while recordings or previews are in progress.
        """)

    def _get_fullscreen(self):
        return self.renderer.inputs[0].params[mmal.MMAL_PARAMETER_DISPLAYREGION].fullscreen.value != mmal.MMAL_FALSE
    def _set_fullscreen(self, value):
        mp = self.renderer.inputs[0].params[mmal.MMAL_PARAMETER_DISPLAYREGION]
        mp.set = mmal.MMAL_DISPLAY_SET_FULLSCREEN
        mp.fullscreen = bool(value)
        self.renderer.inputs[0].params[mmal.MMAL_PARAMETER_DISPLAYREGION] = mp
    fullscreen = property(_get_fullscreen, _set_fullscreen, doc="""\
        Retrieves or sets whether the renderer appears full-screen.

        The :attr:`fullscreen` property is a bool which controls whether the
        renderer takes up the entire display or not. When set to ``False``, the
        :attr:`window` property can be used to control the precise size of the
        renderer display. The property can be set while recordings or previews
        are active.
        """)

    def _get_window(self):
        mp = self.renderer.inputs[0].params[mmal.MMAL_PARAMETER_DISPLAYREGION]
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
        mp = self.renderer.inputs[0].params[mmal.MMAL_PARAMETER_DISPLAYREGION]
        mp.set = mmal.MMAL_DISPLAY_SET_DEST_RECT
        mp.dest_rect = mmal.MMAL_RECT_T(x, y, w, h)
        self.renderer.inputs[0].params[mmal.MMAL_PARAMETER_DISPLAYREGION] = mp
    window = property(_get_window, _set_window, doc="""\
        Retrieves or sets the size of the renderer.

        When the :attr:`fullscreen` property is set to ``False``, the
        :attr:`window` property specifies the size and position of the renderer
        on the display. The property is a 4-tuple consisting of ``(x, y, width,
        height)``. The property can be set while recordings or previews are
        active.
        """)

    def _get_crop(self):
        mp = self.renderer.inputs[0].params[mmal.MMAL_PARAMETER_DISPLAYREGION]
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
        mp = self.renderer.inputs[0].params[mmal.MMAL_PARAMETER_DISPLAYREGION]
        mp.set = mmal.MMAL_DISPLAY_SET_SRC_RECT
        mp.src_rect = mmal.MMAL_RECT_T(x, y, w, h)
        self.renderer.inputs[0].params[mmal.MMAL_PARAMETER_DISPLAYREGION] = mp
    crop = property(_get_crop, _set_crop, doc="""\
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
            captures or recordings (unlike the :attr:`~PiCamera.zoom` property
            of the :class:`PiCamera` class).
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
    rotation = property(_get_rotation, _set_rotation, doc="""\
        Retrieves or sets the current rotation of the renderer.

        When queried, the :attr:`rotation` property returns the rotation
        applied to the renderer. Valid values are 0, 90, 180, and 270.

        When set, the property changes the rotation applied to the renderer's
        output. The property can be set while recordings or previews are
        active. The default is 0.

        .. note::

            This property only affects the renderer; it has no bearing on image
            captures or recordings (unlike the :attr:`~PiCamera.rotation`
            property of the :class:`PiCamera` class).
        """)

    def _get_vflip(self):
        return self._vflip
    def _set_vflip(self, value):
        value = bool(value)
        self._set_transform(
                self._get_transform(self._rotation, value, self._hflip))
        self._vflip = value
    vflip = property(_get_vflip, _set_vflip, doc="""\
        Retrieves or sets whether the renderer's output is vertically flipped.

        When queried, the :attr:`vflip` property returns a boolean indicating
        whether or not the renderer's output is vertically flipped. The
        property can be set while recordings or previews are in progress. The
        default is ``False``.

        .. note::

            This property only affects the renderer; it has no bearing on image
            captures or recordings (unlike the :attr:`~PiCamera.vflip` property
            of the :class:`PiCamera` class).
        """)

    def _get_hflip(self):
        return self._hflip
    def _set_hflip(self, value):
        value = bool(value)
        self._set_transform(
                self._get_transform(self._rotation, self._vflip, value))
        self._hflip = value
    hflip = property(_get_hflip, _set_hflip, doc="""\
        Retrieves or sets whether the renderer's output is horizontally
        flipped.

        When queried, the :attr:`vflip` property returns a boolean indicating
        whether or not the renderer's output is horizontally flipped. The
        property can be set while recordings or previews are in progress. The
        default is ``False``.

        .. note::

            This property only affects the renderer; it has no bearing on image
            captures or recordings (unlike the :attr:`~PiCamera.hflip` property
            of the :class:`PiCamera` class).
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
        mp = self.renderer.inputs[0].params[mmal.MMAL_PARAMETER_DISPLAYREGION]
        mp.set = mmal.MMAL_DISPLAY_SET_TRANSFORM
        mp.transform = value
        self.renderer.inputs[0].params[mmal.MMAL_PARAMETER_DISPLAYREGION] = mp


class PiOverlayRenderer(PiRenderer):
    """
    Represents an :class:`~mmalobj.MMALRenderer` with a static source for
    overlays.

    This class descends from :class:`PiRenderer` and adds a static *source* for
    the :class:`~mmalobj.MMALRenderer`. The *source* must be an object that
    supports the :ref:`buffer protocol <bufferobjects>` in one of the supported
    formats.

    The optional *resolution* parameter specifies the size of the *source* as a
    ``(width, height)`` tuple. If this is omitted or ``None`` then the
    resolution is assumed to be the same as the parent camera's current
    :attr:`~PiCamera.resolution`. The optional *format* parameter specifies the
    encoding of the *source*. This can be one of the unencoded formats:
    ``'yuv'``, ``'rgb'``, ``'rgba'``, ``'bgr'``, or ``'bgra'``. If omitted or
    ``None``, *format* will be guessed based on the size of *source* (assuming
    3 bytes for `RGB`_, and 4 bytes for `RGBA`_).

    The length of *source* must take into account that widths are rounded up to
    the nearest multiple of 32, and heights to the nearest multiple of 16.  For
    example, if *resolution* is ``(1280, 720)``, and *format* is ``'rgb'`` then
    *source* must be a buffer with length 1280 x 720 x 3 bytes, or 2,764,800
    bytes (because 1280 is a multiple of 32, and 720 is a multiple of 16 no
    extra rounding is required).  However, if *resolution* is ``(97, 57)``, and
    *format* is ``'rgb'`` then *source* must be a buffer with length 128 x 64 x
    3 bytes, or 24,576 bytes (pixels beyond column 97 and row 57 in the source
    will be ignored).

    The *layer*, *alpha*, *fullscreen*, and *window* parameters are the same
    as in :class:`PiRenderer`.

    .. _RGB: https://en.wikipedia.org/wiki/RGB
    .. _RGBA: https://en.wikipedia.org/wiki/RGBA_color_space

    .. versionchanged:: 1.13
        Added *format* parameter
    """

    SOURCE_BPP = {
        3: 'rgb',
        4: 'rgba',
        }

    SOURCE_ENCODINGS = {
        'yuv':  mmal.MMAL_ENCODING_I420,
        'rgb':  mmal.MMAL_ENCODING_RGB24,
        'rgba': mmal.MMAL_ENCODING_RGBA,
        'bgr':  mmal.MMAL_ENCODING_BGR24,
        'bgra': mmal.MMAL_ENCODING_BGRA,
        }

    def __init__(
            self, parent, source, resolution=None, format=None, layer=0,
            alpha=255, fullscreen=True, window=None, crop=None, rotation=0,
            vflip=False, hflip=False):
        super(PiOverlayRenderer, self).__init__(
            parent, layer, alpha, fullscreen, window, crop,
            rotation, vflip, hflip)

        # Copy format from camera's preview port, then adjust the encoding to
        # RGB888 or RGBA and optionally adjust the resolution and size
        if resolution is not None:
            self.renderer.inputs[0].framesize = resolution
        else:
            self.renderer.inputs[0].framesize = parent.resolution
        self.renderer.inputs[0].framerate = 0
        if format is None:
            source_len = mo.buffer_bytes(source)
            plane_size = self.renderer.inputs[0].framesize.pad()
            plane_len = plane_size.width * plane_size.height
            try:
                format = self.SOURCE_BPP[source_len // plane_len]
            except KeyError:
                raise PiCameraValueError(
                    'unable to determine format from source size')
        try:
            self.renderer.inputs[0].format = self.SOURCE_ENCODINGS[format]
        except KeyError:
            raise PiCameraValueError('unknown format %s' % format)
        self.renderer.inputs[0].commit()
        # The following callback is required to prevent the mmalobj layer
        # automatically passing buffers back to the port
        self.renderer.inputs[0].enable(callback=lambda port, buf: True)
        self.update(source)

    def update(self, source):
        """
        Update the overlay with a new source of data.

        The new *source* buffer must have the same size as the original buffer
        used to create the overlay. There is currently no method for changing
        the size of an existing overlay (remove and recreate the overlay if you
        require this).

        .. note::

            If you repeatedly update an overlay renderer, you must make sure
            that you do so at a rate equal to, or slower than, the camera's
            framerate. Going faster will rapidly starve the renderer's pool of
            buffers leading to a runtime error.
        """
        buf = self.renderer.inputs[0].get_buffer()
        buf.data = source
        self.renderer.inputs[0].send_buffer(buf)


class PiPreviewRenderer(PiRenderer):
    """
    Represents an :class:`~mmalobj.MMALRenderer` which uses the camera's
    preview as a source.

    This class descends from :class:`PiRenderer` and adds an
    :class:`~mmalobj.MMALConnection` to connect the renderer to an MMAL port.
    The *source* parameter specifies the :class:`~mmalobj.MMALPort` to connect
    to the renderer.

    The *layer*, *alpha*, *fullscreen*, and *window* parameters are the same
    as in :class:`PiRenderer`.
    """

    def __init__(
            self, parent, source, resolution=None, layer=2, alpha=255,
            fullscreen=True, window=None, crop=None, rotation=0, vflip=False,
            hflip=False):
        super(PiPreviewRenderer, self).__init__(
            parent, layer, alpha, fullscreen, window, crop,
            rotation, vflip, hflip)
        self._parent = parent
        if resolution is not None:
            resolution = mo.to_resolution(resolution)
            source.framesize = resolution
        self.renderer.inputs[0].connect(source).enable()

    def _get_resolution(self):
        result = self._parent._camera.outputs[self._parent.CAMERA_PREVIEW_PORT].framesize
        if result != self._parent.resolution:
            return result
        else:
            return None
    def _set_resolution(self, value):
        if value is not None:
            value = mo.to_resolution(value)
        if (
                value.width > self._parent.resolution.width or
                value.height > self._parent.resolution.height
                ):
            raise PiCameraValueError(
                'preview resolution cannot exceed camera resolution')
        self.renderer.connection.disable()
        if value is None:
            value = self._parent.resolution
        self._parent._camera.outputs[self._parent.CAMERA_PREVIEW_PORT].framesize = value
        self._parent._camera.outputs[self._parent.CAMERA_PREVIEW_PORT].commit()
        self.renderer.connection.enable()
    resolution = property(_get_resolution, _set_resolution, doc="""\
        Retrieves or sets the resolution of the preview renderer.

        By default, the preview's resolution matches the camera's resolution.
        However, particularly high resolutions (such as the maximum resolution
        of the V2 camera module) can cause issues. In this case, you may wish
        to set a lower resolution for the preview that the camera's resolution.

        When queried, the :attr:`resolution` property returns ``None`` if the
        preview's resolution is derived from the camera's. In this case, changing
        the camera's resolution will also cause the preview's resolution to
        change. Otherwise, it returns the current preview resolution as a
        tuple.

        .. note::

            The preview resolution cannot be greater than the camera's
            resolution (in either access). If you set a preview resolution,
            then change the camera's resolution below the preview's resolution,
            this property will silently revert to ``None``, meaning the
            preview's resolution will follow the camera's resolution.

        When set, the property reconfigures the preview renderer with the new
        resolution.  As a special case, setting the property to ``None`` will
        cause the preview to follow the camera's resolution once more. The
        property can be set while recordings are in progress. The default is
        ``None``.

        .. note::

            This property only affects the renderer; it has no bearing on image
            captures or recordings (unlike the :attr:`~PiCamera.resolution`
            property of the :class:`PiCamera` class).

        .. versionadded:: 1.11
        """)


class PiNullSink(object):
    """
    Implements an :class:`~mmalobj.MMALNullSink` which can be used in place of
    a renderer.

    The *parent* parameter specifies the :class:`PiCamera` instance which
    constructed this :class:`~mmalobj.MMALNullSink`. The *source* parameter
    specifies the :class:`~mmalobj.MMALPort` which the null-sink should connect
    to its input.

    The null-sink can act as a drop-in replacement for :class:`PiRenderer` in
    most cases, but obviously doesn't implement attributes like ``alpha``,
    ``layer``, etc. as it simply dumps any incoming frames. This is also the
    reason that this class doesn't derive from :class:`PiRenderer` like all
    other classes in this module.
    """

    def __init__(self, parent, source):
        self.renderer = mo.MMALNullSink()
        self.renderer.enable()
        self.renderer.inputs[0].connect(source).enable()

    def close(self):
        """
        Finalizes the null-sink and deallocates all structures.

        This method is called by the camera prior to destroying the null-sink
        (or more precisely, letting it go out of scope to permit the garbage
        collector to destroy it at some future time).
        """
        if self.renderer:
            self.renderer.close()
            self.renderer = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.close()


