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

import mimetypes
import ctypes as ct
from functools import reduce
from operator import or_

from . import bcm_host, mmalobj as mo, mmal
from .encoders import PiCookedOneImageEncoder, PiRawOneImageEncoder
from .exc import PiCameraRuntimeError, PiCameraValueError


class PiDisplay(object):
    __slots__ = (
        '_display',
        '_info',
        '_transform',
        '_exif_tags',
        )

    _ROTATIONS = {
        bcm_host.DISPMANX_NO_ROTATE:  0,
        bcm_host.DISPMANX_ROTATE_90:  90,
        bcm_host.DISPMANX_ROTATE_180: 180,
        bcm_host.DISPMANX_ROTATE_270: 270,
        }
    _ROTATIONS_R = {v: k for k, v in _ROTATIONS.items()}
    _ROTATIONS_MASK = reduce(or_, _ROTATIONS.keys(), 0)

    RAW_FORMATS = {
        'yuv',
        'rgb',
        'rgba',
        'bgr',
        'bgra',
        }

    def __init__(self, display_num=0):
        bcm_host.bcm_host_init()
        self._exif_tags = {}
        self._display = bcm_host.vc_dispmanx_display_open(display_num)
        self._transform = bcm_host.DISPMANX_NO_ROTATE
        if not self._display:
            raise PiCameraRuntimeError('unable to open display %d' % display_num)
        self._info = bcm_host.DISPMANX_MODEINFO_T()
        if bcm_host.vc_dispmanx_display_get_info(self._display, self._info):
            raise PiCameraRuntimeError('unable to get display info')

    def close(self):
        bcm_host.vc_dispmanx_display_close(self._display)
        self._display = None

    @property
    def closed(self):
        return self._display is None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.close()

    def _get_output_format(self, output):
        """
        Given an output object, attempt to determine the requested format.

        We attempt to determine the filename of the *output* object and derive
        a MIME type from the extension. If *output* has no filename, an error
        is raised.
        """
        if isinstance(output, bytes):
            filename = output.decode('utf-8')
        elif isinstance(output, str):
            filename = output
        else:
            try:
                filename = output.name
            except AttributeError:
                raise PiCameraValueError(
                    'Format must be specified when output has no filename')
        (type, encoding) = mimetypes.guess_type(filename, strict=False)
        if not type:
            raise PiCameraValueError(
                'Unable to determine type from filename %s' % filename)
        return type

    def _get_image_format(self, output, format=None):
        """
        Given an output object and an optional format, attempt to determine the
        requested image format.

        This method is used by all capture methods to determine the requested
        output format. If *format* is specified as a MIME-type the "image/"
        prefix is stripped. If *format* is not specified, then
        :meth:`_get_output_format` will be called to attempt to determine
        format from the *output* object.
        """
        if isinstance(format, bytes):
            format = format.decode('utf-8')
        format = format or self._get_output_format(output)
        format = (
            format[6:] if format.startswith('image/') else
            format)
        if format == 'x-ms-bmp':
            format = 'bmp'
        return format

    def _get_image_encoder(self, output_port, format, resize, **options):
        """
        Construct an image encoder for the requested parameters.

        This method is called by :meth:`capture`. The *output_port* parameter
        gives the MMAL port that the encoder should read output from. The
        *format* parameter indicates the image format and will be one of:

        * ``'jpeg'``
        * ``'png'``
        * ``'gif'``
        * ``'bmp'``
        * ``'yuv'``
        * ``'rgb'``
        * ``'rgba'``
        * ``'bgr'``
        * ``'bgra'``

        The *resize* parameter indicates the size that the encoder should
        resize the output to (presumably by including a resizer in the
        pipeline). Finally, *options* includes extra keyword arguments that
        should be passed verbatim to the encoder.
        """
        encoder_class = (
                PiRawOneImageEncoder if format in self.RAW_FORMATS else
                PiCookedOneImageEncoder)
        return encoder_class(
                self, None, output_port, format, resize, **options)

    def capture(self, output, format=None, resize=None, **options):
        format = self._get_image_format(output, format)
        if format == 'yuv':
            raise PiCameraValueError('YUV format is unsupported at this time')
        res = self.resolution
        if (self._info.transform & bcm_host.DISPMANX_ROTATE_90) or (
                self._info.transform & bcm_host.DISPMANX_ROTATE_270):
            res = res.transpose()
        transform = self._transform
        if (transform & bcm_host.DISPMANX_ROTATE_90) or (
                transform & bcm_host.DISPMANX_ROTATE_270):
            res = res.transpose()
        source = mo.MMALPythonSource()
        source.outputs[0].format = mmal.MMAL_ENCODING_RGB24
        if format == 'bgr':
            source.outputs[0].format = mmal.MMAL_ENCODING_BGR24
            transform |= bcm_host.DISPMANX_SNAPSHOT_SWAP_RED_BLUE
        source.outputs[0].framesize = res
        source.outputs[0].commit()
        encoder = self._get_image_encoder(
            source.outputs[0], format, resize, **options)
        try:
            encoder.start(output)
            try:
                pitch = res.pad(width=16).width * 3
                image_ptr = ct.c_uint32()
                resource = bcm_host.vc_dispmanx_resource_create(
                    bcm_host.VC_IMAGE_RGB888, res.width, res.height, image_ptr)
                if not resource:
                    raise PiCameraRuntimeError(
                        'unable to allocate resource for capture')
                try:
                    buf = source.outputs[0].get_buffer()
                    if bcm_host.vc_dispmanx_snapshot(self._display, resource, transform):
                        raise PiCameraRuntimeError('failed to capture snapshot')
                    rect = bcm_host.VC_RECT_T(0, 0, res.width, res.height)
                    if bcm_host.vc_dispmanx_resource_read_data(resource, rect, buf._buf[0].data, pitch):
                        raise PiCameraRuntimeError('failed to read snapshot')
                    buf._buf[0].length = pitch * res.height
                    buf._buf[0].flags = (
                        mmal.MMAL_BUFFER_HEADER_FLAG_EOS |
                        mmal.MMAL_BUFFER_HEADER_FLAG_FRAME_END
                        )
                finally:
                    bcm_host.vc_dispmanx_resource_delete(resource)
                source.outputs[0].send_buffer(buf)
                # XXX Anything more intelligent than a 10 second default?
                encoder.wait(10)
            finally:
                encoder.stop()
        finally:
            encoder.close()

    def _calculate_transform(self):
        """
        Calculates a reverse transform to undo any that the boot configuration
        applies (presumably the user has altered the boot configuration to
        match their screen orientation so they want any capture to appear
        correctly oriented by default). This is then modified by the transforms
        specified in the :attr:`rotation`, :attr:`hflip` and :attr:`vflip`
        attributes.
        """
        r = PiDisplay._ROTATIONS[self._info.transform & PiDisplay._ROTATIONS_MASK]
        r = (360 - r) % 360 # undo the native rotation
        r = (r + self.rotation) % 360 # add selected rotation
        result = PiDisplay._ROTATIONS_R[r]
        result |= self._info.transform & ( # undo flips by re-doing them
            bcm_host.DISPMANX_FLIP_HRIZ | bcm_host.DISPMANX_FLIP_VERT
            )
        return result

    @property
    def resolution(self):
        """
        Retrieves the resolution of the display device.
        """
        return mo.PiResolution(width=self._info.width, height=self._info.height)

    def _get_hflip(self):
        return bool(self._info.transform & bcm_host.DISPMANX_FLIP_HRIZ)
    def _set_hflip(self, value):
        if value:
            self._info.transform |= bcm_host.DISPMANX_FLIP_HRIZ
        else:
            self._info.transform &= ~bcm_host.DISPMANX_FLIP_HRIZ
    hflip = property(_get_hflip, _set_hflip, doc="""\
        Retrieves or sets whether snapshots are horizontally flipped.

        When queried, the :attr:`vflip` property returns a boolean indicating
        whether or not the output of :meth:`capture` is horizontally flipped.
        The default is ``False``.

        .. note::

            This property only affects snapshots; it does not affect the
            display output itself.
        """)

    def _get_vflip(self):
        return bool(self._info.transform & bcm_host.DISPMANX_FLIP_VERT)
    def _set_vflip(self, value):
        if value:
            self._info.transform |= bcm_host.DISPMANX_FLIP_VERT
        else:
            self._info.transform &= ~bcm_host.DISPMANX_FLIP_VERT
    vflip = property(_get_vflip, _set_vflip, doc="""\
        Retrieves or sets whether snapshots are vertically flipped.

        When queried, the :attr:`vflip` property returns a boolean indicating
        whether or not the output of :meth:`capture` is vertically flipped. The
        default is ``False``.

        .. note::

            This property only affects snapshots; it does not affect the
            display output itself.
        """)

    def _get_rotation(self):
        return PiDisplay._ROTATIONS[self._transform & PiDisplay._ROTATIONS_MASK]
    def _set_rotation(self, value):
        try:
            self._transform = (
                self._transform & ~PiDisplay._ROTATIONS_MASK) | PiDisplay._ROTATIONS_R[value]
        except KeyError:
            raise PiCameraValueError('invalid rotation %d' % value)
    rotation = property(_get_rotation, _set_rotation, doc="""\
        Retrieves or sets the rotation of snapshots.

        When queried, the :attr:`rotation` property returns the rotation
        applied to the result of :meth:`capture`. Valid values are 0, 90, 180,
        and 270. When set, the property changes the rotation applied to the
        result of :meth:`capture`. The default is 0.

        .. note::

            This property only affects snapshots; it does not affect the
            display itself. To rotate the display itself, modify the
            ``display_rotate`` value in :file:`/boot/config.txt`.
        """)

    def _get_exif_tags(self):
        return self._exif_tags
    def _set_exif_tags(self, value):
        self._exif_tags = {k: v for k, v in value.items()}
    exif_tags = property(_get_exif_tags, _set_exif_tags)

