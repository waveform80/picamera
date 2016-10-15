# vim: set et sw=4 sts=4 fileencoding=utf-8:
#
# Python header conversion
# Copyright (c) 2013-2015 Dave Jones <dave@waveform.org.uk>
#
# Original headers
# Copyright (c) 2012, Broadcom Europe Ltd
# All rights reserved.
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
import warnings

_lib = ct.CDLL('libbcm_host.so')

# bcm_host.h #################################################################

bcm_host_init = _lib.bcm_host_init
bcm_host_init.argtypes = []
bcm_host_init.restype = None

bcm_host_deinit = _lib.bcm_host_deinit
bcm_host_deinit.argtypes = []
bcm_host_deinit.restype = None

graphics_get_display_size = _lib.graphics_get_display_size
graphics_get_display_size.argtypes = [ct.c_uint16, ct.POINTER(ct.c_uint32), ct.POINTER(ct.c_uint32)]
graphics_get_display_size.restype = ct.c_int32

# vcos_platform.h ############################################################

VCOS_UNSIGNED = ct.c_uint32

# vcos_types.h ###############################################################

VCOS_STATUS_T = ct.c_uint32 # enum
(
    VCOS_SUCCESS,
    VCOS_EAGAIN,
    VCOS_ENOENT,
    VCOS_ENOSPC,
    VCOS_EINVAL,
    VCOS_EACCESS,
    VCOS_ENOMEM,
    VCOS_ENOSYS,
    VCOS_EEXIST,
    VCOS_ENXIO,
    VCOS_EINTR,
) = range(11)

def VCOS_ALIGN_UP(value, round_to):
    # Note: this function assumes round_to is some power of 2.
    return (value + (round_to - 1)) & ~(round_to - 1)

def VCOS_ALIGN_DOWN(value, round_to):
    # Note: this function assumes round_to is some power of 2.
    return value & ~(round_to - 1)

# vc_image_types.h ###########################################################

class VC_RECT_T(ct.Structure):
    _fields_ = [
        ('x', ct.c_int32),
        ('y', ct.c_int32),
        ('width', ct.c_int32),
        ('height', ct.c_int32),
        ]

VC_IMAGE_TYPE_T = ct.c_uint32 # enum
(
   VC_IMAGE_MIN,
   VC_IMAGE_RGB565,
   VC_IMAGE_1BPP,
   VC_IMAGE_YUV420,
   VC_IMAGE_48BPP,
   VC_IMAGE_RGB888,
   VC_IMAGE_8BPP,
   VC_IMAGE_4BPP,
   VC_IMAGE_3D32,
   VC_IMAGE_3D32B,
   VC_IMAGE_3D32MAT,
   VC_IMAGE_RGB2X9,
   VC_IMAGE_RGB666,
   VC_IMAGE_PAL4_OBSOLETE,
   VC_IMAGE_PAL8_OBSOLETE,
   VC_IMAGE_RGBA32,
   VC_IMAGE_YUV422,
   VC_IMAGE_RGBA565,
   VC_IMAGE_RGBA16,
   VC_IMAGE_YUV_UV,
   VC_IMAGE_TF_RGBA32,
   VC_IMAGE_TF_RGBX32,
   VC_IMAGE_TF_FLOAT,
   VC_IMAGE_TF_RGBA16,
   VC_IMAGE_TF_RGBA5551,
   VC_IMAGE_TF_RGB565,
   VC_IMAGE_TF_YA88,
   VC_IMAGE_TF_BYTE,
   VC_IMAGE_TF_PAL8,
   VC_IMAGE_TF_PAL4,
   VC_IMAGE_TF_ETC1,
   VC_IMAGE_BGR888,
   VC_IMAGE_BGR888_NP,
   VC_IMAGE_BAYER,
   VC_IMAGE_CODEC,
   VC_IMAGE_YUV_UV32,
   VC_IMAGE_TF_Y8,
   VC_IMAGE_TF_A8,
   VC_IMAGE_TF_SHORT,
   VC_IMAGE_TF_1BPP,
   VC_IMAGE_OPENGL,
   VC_IMAGE_YUV444I,
   VC_IMAGE_YUV422PLANAR,
   VC_IMAGE_ARGB8888,
   VC_IMAGE_XRGB8888,
   VC_IMAGE_YUV422YUYV,
   VC_IMAGE_YUV422YVYU,
   VC_IMAGE_YUV422UYVY,
   VC_IMAGE_YUV422VYUY,
   VC_IMAGE_RGBX32,
   VC_IMAGE_RGBX8888,
   VC_IMAGE_BGRX8888,
   VC_IMAGE_YUV420SP,
   VC_IMAGE_YUV444PLANAR,
   VC_IMAGE_TF_U8,
   VC_IMAGE_TF_V8,
   VC_IMAGE_MAX,
) = range(57)

TRANSFORM_HFLIP = 1 << 0
TRANSFORM_VFLIP = 1 << 1
TRANSFORM_TRANSPOSE = 1 << 2

VC_IMAGE_TRANSFORM_T = ct.c_uint32 # enum
VC_IMAGE_ROT0          = 0
VC_IMAGE_MIRROR_ROT0   = TRANSFORM_HFLIP
VC_IMAGE_MIRROR_ROT180 = TRANSFORM_VFLIP
VC_IMAGE_ROT180        = TRANSFORM_HFLIP | TRANSFORM_VFLIP
VC_IMAGE_MIRROR_ROT90  = TRANSFORM_TRANSPOSE
VC_IMAGE_ROT270        = TRANSFORM_TRANSPOSE | TRANSFORM_HFLIP
VC_IMAGE_ROT90         = TRANSFORM_TRANSPOSE | TRANSFORM_VFLIP
VC_IMAGE_MIRROR_ROT270 = TRANSFORM_TRANSPOSE | TRANSFORM_HFLIP | TRANSFORM_VFLIP

VC_IMAGE_BAYER_ORDER_T = ct.c_uint32 # enum
(
   VC_IMAGE_BAYER_RGGB,
   VC_IMAGE_BAYER_GBRG,
   VC_IMAGE_BAYER_BGGR,
   VC_IMAGE_BAYER_GRBG,
) = range(4)

VC_IMAGE_BAYER_FORMAT_T = ct.c_uint32 # enum
(
   VC_IMAGE_BAYER_RAW6,
   VC_IMAGE_BAYER_RAW7,
   VC_IMAGE_BAYER_RAW8,
   VC_IMAGE_BAYER_RAW10,
   VC_IMAGE_BAYER_RAW12,
   VC_IMAGE_BAYER_RAW14,
   VC_IMAGE_BAYER_RAW16,
   VC_IMAGE_BAYER_RAW10_8,
   VC_IMAGE_BAYER_RAW12_8,
   VC_IMAGE_BAYER_RAW14_8,
   VC_IMAGE_BAYER_RAW10L,
   VC_IMAGE_BAYER_RAW12L,
   VC_IMAGE_BAYER_RAW14L,
   VC_IMAGE_BAYER_RAW16_BIG_ENDIAN,
   VC_IMAGE_BAYER_RAW4,
) = range(16)

# vc_display_types.h #########################################################

VCOS_DISPLAY_INPUT_FORMAT_T = ct.c_uint32 # enum
(
   VCOS_DISPLAY_INPUT_FORMAT_INVALID,
   VCOS_DISPLAY_INPUT_FORMAT_RGB888,
   VCOS_DISPLAY_INPUT_FORMAT_RGB565
) = range(3)

DISPLAY_INPUT_FORMAT_INVALID = VCOS_DISPLAY_INPUT_FORMAT_INVALID
DISPLAY_INPUT_FORMAT_RGB888  = VCOS_DISPLAY_INPUT_FORMAT_RGB888
DISPLAY_INPUT_FORMAT_RGB565  = VCOS_DISPLAY_INPUT_FORMAT_RGB565
DISPLAY_INPUT_FORMAT_T = VCOS_DISPLAY_INPUT_FORMAT_T

DISPLAY_3D_FORMAT_T = ct.c_uint32 # enum
(
   DISPLAY_3D_UNSUPPORTED,
   DISPLAY_3D_INTERLEAVED,
   DISPLAY_3D_SBS_FULL_AUTO,
   DISPLAY_3D_SBS_HALF_HORIZ,
   DISPLAY_3D_TB_HALF,
   DISPLAY_3D_FRAME_PACKING,
   DISPLAY_3D_FRAME_SEQUENTIAL,
   DISPLAY_3D_FORMAT_MAX,
) = range(8)

DISPLAY_INTERFACE_T = ct.c_uint32 # enum
(
   DISPLAY_INTERFACE_MIN,
   DISPLAY_INTERFACE_SMI,
   DISPLAY_INTERFACE_DPI,
   DISPLAY_INTERFACE_DSI,
   DISPLAY_INTERFACE_LVDS,
   DISPLAY_INTERFACE_MAX,
) = range(6)

DISPLAY_DITHER_T = ct.c_uint32 # enum
(
   DISPLAY_DITHER_NONE,
   DISPLAY_DITHER_RGB666,
   DISPLAY_DITHER_RGB565,
   DISPLAY_DITHER_RGB555,
   DISPLAY_DITHER_MAX,
) = range(5)

class DISPLAY_INFO_T(ct.Structure):
    _fields_ = [
        ('type',             DISPLAY_INTERFACE_T),
        ('width',            ct.c_uint32),
        ('height',           ct.c_uint32),
        ('input_format',     DISPLAY_INPUT_FORMAT_T),
        ('interlaced',       ct.c_uint32),
        ('output_dither',    DISPLAY_DITHER_T),
        ('pixel_freq',       ct.c_uint32),
        ('line_rate',        ct.c_uint32),
        ('format_3d',        DISPLAY_3D_FORMAT_T),
        ('use_pixelvalve_1', ct.c_uint32),
        ('dsi_video_mode',   ct.c_uint32),
        ('hvs_channel',      ct.c_uint32),
        ]

# vc_dispmanx_types.h ########################################################

DISPMANX_DISPLAY_HANDLE_T = ct.c_uint32
DISPMANX_UPDATE_HANDLE_T = ct.c_uint32
DISPMANX_ELEMENT_HANDLE_T = ct.c_uint32
DISPMANX_RESOURCE_HANDLE_T = ct.c_uint32
DISPMANX_PROTECTION_T = ct.c_uint32

DISPMANX_TRANSFORM_T = ct.c_uint32 # enum
DISPMANX_NO_ROTATE              = 0
DISPMANX_ROTATE_90              = 1
DISPMANX_ROTATE_180             = 2
DISPMANX_ROTATE_270             = 3
DISPMANX_FLIP_HRIZ              = 1 << 16
DISPMANX_FLIP_VERT              = 1 << 17
DISPMANX_STEREOSCOPIC_INVERT    = 1 << 19
DISPMANX_STEREOSCOPIC_NONE      = 0 << 20
DISPMANX_STEREOSCOPIC_MONO      = 1 << 20
DISPMANX_STEREOSCOPIC_SBS       = 2 << 20
DISPMANX_STEREOSCOPIC_TB        = 3 << 20
DISPMANX_STEREOSCOPIC_MASK      = 15 << 20
DISPMANX_SNAPSHOT_NO_YUV        = 1 << 24
DISPMANX_SNAPSHOT_NO_RGB        = 1 << 25
DISPMANX_SNAPSHOT_FILL          = 1 << 26
DISPMANX_SNAPSHOT_SWAP_RED_BLUE = 1 << 27
DISPMANX_SNAPSHOT_PACK          = 1 << 28

DISPMANX_FLAGS_ALPHA_T = ct.c_uint32 # enum
DISPMANX_FLAGS_ALPHA_FROM_SOURCE       = 0
DISPMANX_FLAGS_ALPHA_FIXED_ALL_PIXELS  = 1
DISPMANX_FLAGS_ALPHA_FIXED_NON_ZERO    = 2
DISPMANX_FLAGS_ALPHA_FIXED_EXCEED_0X07 = 3
DISPMANX_FLAGS_ALPHA_PREMULT           = 1 << 16
DISPMANX_FLAGS_ALPHA_MIX               = 1 << 17

class DISPMANX_ALPHA_T(ct.Structure):
    _fields_ = [
        ('flags',   DISPMANX_FLAGS_ALPHA_T),
        ('opacity', ct.c_uint32),
        ('mask',    ct.c_void_p),
        ]

class VC_DISPMANX_ALPHA_T(ct.Structure):
    _fields_ = [
        ('flags',   DISPMANX_FLAGS_ALPHA_T),
        ('opacity', ct.c_uint32),
        ('mask',    DISPMANX_RESOURCE_HANDLE_T),
        ]

DISPMANX_FLAGS_CLAMP_T = ct.c_uint32 # enum
(
  DISPMANX_FLAGS_CLAMP_NONE,
  DISPMANX_FLAGS_CLAMP_LUMA_TRANSPARENT,
  DISPMANX_FLAGS_CLAMP_TRANSPARENT,
  DISPMANX_FLAGS_CLAMP_REPLACE,
) = range(4)

DISPMANX_FLAGS_KEYMASK_T = ct.c_uint32 # enum
DISPMANX_FLAGS_KEYMASK_OVERRIDE = 1
DISPMANX_FLAGS_KEYMASK_SMOOTH   = 1 << 1
DISPMANX_FLAGS_KEYMASK_CR_INV   = 1 << 2
DISPMANX_FLAGS_KEYMASK_CB_INV   = 1 << 3
DISPMANX_FLAGS_KEYMASK_YY_INV   = 1 << 4

class _YUV(ct.Structure):
    _fields_ = [
        ('yy_upper', ct.c_uint8),
        ('yy_lower', ct.c_uint8),
        ('cr_upper', ct.c_uint8),
        ('cr_lower', ct.c_uint8),
        ('cb_upper', ct.c_uint8),
        ('cb_lower', ct.c_uint8),
        ]

class _RGB(ct.Structure):
    _fields_ = [
        ('red_upper',   ct.c_uint8),
        ('red_lower',   ct.c_uint8),
        ('green_upper', ct.c_uint8),
        ('green_lower', ct.c_uint8),
        ('blue_upper',  ct.c_uint8),
        ('blue_lower',  ct.c_uint8),
        ]

class DISPMANX_CLAMP_KEYS_T(ct.Union):
    _fields_ = [
        ('yuv', _YUV),
        ('rgb', _RGB),
        ]

class DISPMANX_CLAMP_T(ct.Structure):
    _fields_ = [
        ('mode',          DISPMANX_FLAGS_CLAMP_T),
        ('key_mask',      DISPMANX_FLAGS_KEYMASK_T),
        ('key_value',     DISPMANX_CLAMP_KEYS_T),
        ('replace_value', ct.c_uint32),
        ]

class DISPMANX_MODEINFO_T(ct.Structure):
    _fields_ = [
        ('width',        ct.c_int32),
        ('height',       ct.c_int32),
        ('transform',    DISPMANX_TRANSFORM_T),
        ('input_format', DISPAY_INPUT_FORMAT_T),
        ('display_num',  ct.c_uint32),
        ]

DISPMANX_CALLBACK_FUNC_T = ct.FUNCTYPE(
    None,
    DISPMANX_UPDATE_HANDLE_T, ct.c_void_p)

DISPMANX_PROGRESS_CALLBACK_FUNC_T = ct.FUNCTYPE(
    None,
    DISPMANX_UPDATE_HANDLE_T, ct.c_uint32, ct.c_void_p)

# vc_dispmanx.h ##############################################################

vc_dispmanx_stop = _lib.vc_dispmanx_stop
vc_dispmanx_stop.argtypes = []
vc_dispmanx_stop.restype = None

vc_dispmanx_rect_set = _lib.vc_dispmanx_rect_set
vc_dispmanx_rect_set.argtypes = [ct.POINTER(VC_RECT_T), ct.c_uint32, ct.c_uint32, ct.c_uint32, ct.c_uint32]
vc_dispmanx_rect_set.restype = ct.c_int

vc_dispmanx_resource_create = _lib.vc_dispmanx_resource_create
vc_dispmanx_resource_create.argtypes = [VC_IMAGE_TYPE_T, ct.c_uint32, ct.c_uint32, ct.POINTER(ct.c_uint32)]
vc_dispmanx_resource_create.restype = DISPMANX_RESOURCE_HANDLE_T

vc_dispmanx_resource_write_data = _lib.vc_dispmanx_resource_write_data
vc_dispmanx_resource_write_data.argtypes = [DISPMANX_RESOURCE_HANDLE_T, VC_IMAGE_TYPE_T, ct.c_int, ct.c_void_p, ct.POINTER(VC_RECT_T)]
vc_dispmanx_resource_write_data.restype = ct.c_int

vc_dispmanx_resource_read_data = _lib.vc_dispmanx_resource_read_data
vc_dispmanx_resource_read_data.argtypes = [DISPMANX_RESOURCE_HANDLE_T, ct.POINTER(VC_RECT_T), ct.c_void_p, ct.c_uint32]
vc_dispmanx_resource_read_data.restype = ct.c_int

vc_dispmanx_resource_delete = _lib.vc_dispmanx_resource_delete
vc_dispmanx_resource_delete.argtypes = [DISPMANX_RESOURCE_HANDLE_T]
vc_dispmanx_resource_delete.restype = ct.c_int

vc_dispmanx_display_open = _lib.vc_dispmanx_display_open
vc_dispmanx_display_open.argtypes = [ct.c_uint32]
vc_dispmanx_display_open.restype = DISPMANX_DISPLAY_HANDLE_T

vc_dispmanx_display_open_mode = _lib.vc_dispmanx_display_open_mode
vc_dispmanx_display_open_mode.argtypes = [ct.c_uint32, ct.c_uint32]
vc_dispmanx_display_open_mode.restype = DISPMANX_DISPLAY_HANDLE_T

vc_dispmanx_display_open_offscreen = _lib.vc_dispmanx_display_open_offscreen
vc_dispmanx_display_open_offscreen.argtypes = [DISPMANX_RESOURCE_HANDLE_T, DISPMANX_TRANSFORM_T]
vc_dispmanx_display_open_offscreen.restype = DISPMANX_DISPLAY_HANDLE_T

vc_dispmanx_display_reconfigure = _lib.vc_dispmanx_display_reconfigure
vc_dispmanx_display_reconfigure.argtypes = [DISPMANX_DISPLAY_HANDLE_T, ct.c_uint32]
vc_dispmanx_display_reconfigure.restype = ct.c_int

vc_dispmanx_display_set_destination = _lib.vc_dispmanx_display_set_destination
vc_dispmanx_display_set_destination.argtypes = [DISPMANX_DISPLAY_HANDLE_T, DISPMANX_RESOURCE_HANDLE_T]
vc_dispmanx_display_set_destination.restype = ct.c_int

vc_dispmanx_display_set_background = _lib.vc_dispmanx_display_set_background
vc_dispmanx_display_set_background.argtypes = [DISPMANX_UPDATE_HANDLE_T, DISPMANX_DISPLAY_HANDLE_T, ct.c_uint8, ct.c_uint8, ct.c_uint8]
vc_dispmanx_display_set_background.restype = ct.c_int

vc_dispmanx_display_get_info = _lib.vc_dispmanx_display_get_info
vc_dispmanx_display_get_info.argtypes = [DISPMANX_DISPLAY_HANDLE_T, ct.POINTER(DISPMANX_MODEINFO_T)]
vc_dispmanx_display_get_info.restype = ct.c_int

vc_dispmanx_display_close = _lib.vc_dispmanx_display_close
vc_dispmanx_display_close.argtypes = [DISPMANX_DISPLAY_HANDLE_T]
vc_dispmanx_display_close.restype = ct.c_int

vc_dispmanx_update_start = _lib.vc_dispmanx_update_start
vc_dispmanx_update_start.argtypes = [ct.c_int32]
vc_dispmanx_update_start.restype = DISPMANX_UPDATE_HANDLE_T

vc_dispmanx_element_add = _lib.vc_dispmanx_element_add
vc_dispmanx_element_add.argtypes = [DISPMANX_UPDATE_HANDLE_T, DISPMANX_DISPLAY_HANDLE_T, ct.c_int32, ct.POINTER(VC_RECT_T), DISPMANX_RESOURCE_HANDLE_T, ct.POINTER(VC_RECT_T), DISPMANX_PROTECTION_T, VC_DISPMANX_ALPHA_T, DISPMANX_CLAMP_T, DISPMANX_TRANSFORM_T]
vc_dispmanx_element_add.restype = DISPMANX_ELEMENT_HANDLE_T

vc_dispmanx_element_change_source = _lib.vc_dispmanx_element_change_source
vc_dispmanx_element_change_source.argtypes = [DISPMANX_UPDATE_HANDLE_T, DISPMANX_ELEMENT_HANDLE_T, DISPMANX_RESOURCE_HANDLE_T]
vc_dispmanx_element_change_source.restype = ct.c_int

vc_dispmanx_element_change_layer = _lib.vc_dispmanx_element_change_layer
vc_dispmanx_element_change_layer.argtypes = [DISPMANX_UPDATE_HANDLE_T, DISPMANX_ELEMENT_HANDLE_T, ct.c_int32]
vc_dispmanx_element_change_layer.restype = ct.c_int

vc_dispmanx_element_modified = _lib.vc_dispmanx_element_modified
vc_dispmanx_element_modified.argtypes = [DISPMANX_UPDATE_HANDLE_T, DISPMANX_ELEMENT_HANDLE_T, ct.POINTER(VC_RECT_T)]
vc_dispmanx_element_modified.restype = ct.c_int

vc_dispmanx_element_remove = _lib.vc_dispmanx_element_remove
vc_dispmanx_element_remove.argtypes = [DISPMANX_UPDATE_HANDLE_T, DISPMANX_ELEMENT_HANDLE_T]
vc_dispmanx_element_remove.restype = ct.c_int

vc_dispmanx_update_submit = _lib.vc_dispmanx_update_submit
vc_dispmanx_update_submit.argtypes = [DISPMANX_UPDATE_HANDLE_T, DISPMANX_CALLBACK_FUNC_T, ct.c_void_p]
vc_dispmanx_update_submit.restype = ct.c_int

vc_dispmanx_update_submit_sync = _lib.vc_dispmanx_update_submit_sync
vc_dispmanx_update_submit_sync.argtypes = [DISPMANX_UPDATE_HANDLE_T]
vc_dispmanx_update_submit_sync.restype = ct.c_int

vc_dispmanx_query_image_formats = _lib.vc_dispmanx_query_image_formats
vc_dispmanx_query_image_formats.argtypes = [ct.POINTER(ct.c_uint32)]
vc_dispmanx_query_image_formats.restype = ct.c_int

vc_dispmanx_element_change_attributes = _lib.vc_dispmanx_element_change_attributes
vc_dispmanx_element_change_attributes.argtypes = [DISPMANX_UPDATE_HANDLE_T, DISPMANX_ELEMENT_HANDLE_T, ct.c_uint32, ct.c_int32, ct.c_uint8, ct.POINTER(VC_RECT_T), ct.POINTER(VC_RECT_T), DISPMANX_RESOURCE_HANDLE_T, DISPMANX_TRANSFORM_T]
vc_dispmanx_element_change_attributes.restype = ct.c_int

vc_dispmanx_resource_get_image_handle = _lib.vc_dispmanx_resource_get_image_handle
vc_dispmanx_resource_get_image_handle.argtypes = [DISPMANX_RESOURCE_HANDLE_T]
vc_dispmanx_resource_get_image_handle.restype = ct.c_uint32

vc_vchi_dispmanx_init = _lib.vc_vchi_dispmanx_init
vc_vchi_dispmanx_init.argtypes = [VCHI_INSTANCE_T, ct.POINTER(ct.POINTER(VCHI_CONNECTION_T)), ct.c_uint32]
vc_vchi_dispmanx_init.restype = None

vc_dispmanx_snapshot = _lib.vc_dispmanx_snapshot
vc_dispmanx_snapshot.argtypes = [DISPMANX_DISPLAY_HANDLE_T, DISPMANX_RESOURCE_HANDLE_T, DISPMANX_TRANSFORM_T]
vc_dispmanx_snapshot.restype = ct.c_int

vc_dispmanx_resource_set_palette = _lib.vc_dispmanx_resource_set_palette
vc_dispmanx_resource_set_palette.argtypes = [DISPMANX_RESOURCE_HANDLE_T, ct.c_void_p, ct.c_int, ct.c_int]
vc_dispmanx_resource_set_palette.restype = ct.c_int

vc_dispmanx_vsync_callback = _lib.vc_dispmanx_vsync_callback
vc_dispmanx_vsync_callback.argtypes = [DISPMANX_DISPLAY_HANDLE_T, DISPMANX_CALLBACK_FUNC_T, ct.c_void_p]
vc_dispmanx_vsync_callback.restype = ct.c_int

