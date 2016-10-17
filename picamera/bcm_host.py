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

# vchi.h #####################################################################

VCHI_INSTANCE_T = ct.c_void_p
VCHI_CONNECTION_T = ct.c_void_p

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

vcos_bool_t = ct.c_int32
vcos_fourcc_t = ct.c_int32

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
) = range(15)

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
        ('input_format', DISPLAY_INPUT_FORMAT_T),
        ('display_num',  ct.c_uint32),
        ]

DISPMANX_CALLBACK_FUNC_T = ct.CFUNCTYPE(
    None,
    DISPMANX_UPDATE_HANDLE_T, ct.c_void_p)

DISPMANX_PROGRESS_CALLBACK_FUNC_T = ct.CFUNCTYPE(
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

vc_vchi_dispmanx_init = _lib.vc_vchi_dispmanx_init
vc_vchi_dispmanx_init.argtypes = [VCHI_INSTANCE_T, ct.POINTER(VCHI_CONNECTION_T), ct.c_uint32]
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

# vc_cec.h ###################################################################

CEC_BROADCAST_ADDR  = 0xF
CEC_TV_ADDRESS      = 0
CEC_MAX_XMIT_LENGTH = 15
CEC_CLEAR_ADDR      = 0xFFFF

CEC_VERSION                    = 0x4
CEC_VENDOR_ID_BROADCOM         = 0x18C086
CEC_VENDOR_ID_ONKYO            = 0x0009B0
CEC_VENDOR_ID_PANASONIC_EUROPE = 0x000F12
CEC_VENDOR_ID                  = 0

CEC_BLOCKING = 1
CEC_NONBLOCKING = 0

CEC_AllDevices_T = ct.c_uint32 # enum
(
   CEC_AllDevices_eTV,
   CEC_AllDevices_eRec1,
   CEC_AllDevices_eRec2,
   CEC_AllDevices_eSTB1,
   CEC_AllDevices_eDVD1,
   CEC_AllDevices_eAudioSystem,
   CEC_AllDevices_eSTB2,
   CEC_AllDevices_eSTB3,
   CEC_AllDevices_eDVD2,
   CEC_AllDevices_eRec3,
   CEC_AllDevices_eSTB4,
   CEC_AllDevices_eDVD3,
   CEC_AllDevices_eRsvd3,
   CEC_AllDevices_eRsvd4,
   CEC_AllDevices_eFreeUse,
   CEC_AllDevices_eUnRegistered,
) = range(16)

CEC_DEVICE_TYPE_T = ct.c_uint32 # enum
(
   CEC_DeviceType_TV,
   CEC_DeviceType_Rec,
   CEC_DeviceType_Reserved,
   CEC_DeviceType_Tuner,
   CEC_DeviceType_Playback,
   CEC_DeviceType_Audio,
   CEC_DeviceType_Switch,
   CEC_DeviceType_VidProc,
) = range(8)
CEC_DeviceType_Invalid = 0xF

CEC_OPCODE_T = ct.c_uint32 # enum
CEC_Opcode_FeatureAbort                = 0x00
CEC_Opcode_ImageViewOn                 = 0x04
CEC_Opcode_TunerStepIncrement          = 0x05
CEC_Opcode_TunerStepDecrement          = 0x06
CEC_Opcode_TunerDeviceStatus           = 0x07
CEC_Opcode_GiveTunerDeviceStatus       = 0x08
CEC_Opcode_RecordOn                    = 0x09
CEC_Opcode_RecordStatus                = 0x0A
CEC_Opcode_RecordOff                   = 0x0B
CEC_Opcode_TextViewOn                  = 0x0D
CEC_Opcode_RecordTVScreen              = 0x0F
CEC_Opcode_GiveDeckStatus              = 0x1A
CEC_Opcode_DeckStatus                  = 0x1B
CEC_Opcode_SetMenuLanguage             = 0x32
CEC_Opcode_ClearAnalogTimer            = 0x33
CEC_Opcode_SetAnalogTimer              = 0x34
CEC_Opcode_TimerStatus                 = 0x35
CEC_Opcode_Standby                     = 0x36
CEC_Opcode_Play                        = 0x41
CEC_Opcode_DeckControl                 = 0x42
CEC_Opcode_TimerClearedStatus          = 0x43
CEC_Opcode_UserControlPressed          = 0x44
CEC_Opcode_UserControlReleased         = 0x45
CEC_Opcode_GiveOSDName                 = 0x46
CEC_Opcode_SetOSDName                  = 0x47
CEC_Opcode_SetOSDString                = 0x64
CEC_Opcode_SetTimerProgramTitle        = 0x67
CEC_Opcode_SystemAudioModeRequest      = 0x70
CEC_Opcode_GiveAudioStatus             = 0x71
CEC_Opcode_SetSystemAudioMode          = 0x72
CEC_Opcode_ReportAudioStatus           = 0x7A
CEC_Opcode_GiveSystemAudioModeStatus   = 0x7D
CEC_Opcode_SystemAudioModeStatus       = 0x7E
CEC_Opcode_RoutingChange               = 0x80
CEC_Opcode_RoutingInformation          = 0x81
CEC_Opcode_ActiveSource                = 0x82
CEC_Opcode_GivePhysicalAddress         = 0x83
CEC_Opcode_ReportPhysicalAddress       = 0x84
CEC_Opcode_RequestActiveSource         = 0x85
CEC_Opcode_SetStreamPath               = 0x86
CEC_Opcode_DeviceVendorID              = 0x87
CEC_Opcode_VendorCommand               = 0x89
CEC_Opcode_VendorRemoteButtonDown      = 0x8A
CEC_Opcode_VendorRemoteButtonUp        = 0x8B
CEC_Opcode_GiveDeviceVendorID          = 0x8C
CEC_Opcode_MenuRequest                 = 0x8D
CEC_Opcode_MenuStatus                  = 0x8E
CEC_Opcode_GiveDevicePowerStatus       = 0x8F
CEC_Opcode_ReportPowerStatus           = 0x90
CEC_Opcode_GetMenuLanguage             = 0x91
CEC_Opcode_SelectAnalogService         = 0x92
CEC_Opcode_SelectDigitalService        = 0x93
CEC_Opcode_SetDigitalTimer             = 0x97
CEC_Opcode_ClearDigitalTimer           = 0x99
CEC_Opcode_SetAudioRate                = 0x9A
CEC_Opcode_InactiveSource              = 0x9D
CEC_Opcode_CECVersion                  = 0x9E
CEC_Opcode_GetCECVersion               = 0x9F
CEC_Opcode_VendorCommandWithID         = 0xA0
CEC_Opcode_ClearExternalTimer          = 0xA1
CEC_Opcode_SetExternalTimer            = 0xA2
CEC_Opcode_ReportShortAudioDescriptor  = 0xA3
CEC_Opcode_RequestShortAudioDescriptor = 0xA4
CEC_Opcode_InitARC                     = 0xC0
CEC_Opcode_ReportARCInited             = 0xC1
CEC_Opcode_ReportARCTerminated         = 0xC2
CEC_Opcode_RequestARCInit              = 0xC3
CEC_Opcode_RequestARCTermination       = 0xC4
CEC_Opcode_TerminateARC                = 0xC5
CEC_Opcode_CDC                         = 0xF8
CEC_Opcode_Abort                       = 0xFF

CEC_ABORT_REASON_T = ct.c_uint32 # enum
(
   CEC_Abort_Reason_Unrecognised_Opcode,
   CEC_Abort_Reason_Wrong_Mode,
   CEC_Abort_Reason_Cannot_Provide_Source,
   CEC_Abort_Reason_Invalid_Operand,
   CEC_Abort_Reason_Refused,
   CEC_Abort_Reason_Undetermined,
) = range(6)

CEC_DISPLAY_CONTROL_T = ct.c_uint32 # enum
CEC_DISPLAY_CONTROL_DEFAULT_TIME       = 0
CEC_DISPLAY_CONTROL_UNTIL_CLEARED      = 1 << 6
CEC_DISPLAY_CONTROL_CLEAR_PREV_MSG     = 1 << 7

CEC_POWER_STATUS_T = ct.c_uint32 # enum
(
   CEC_POWER_STATUS_ON,
   CEC_POWER_STATUS_STANDBY,
   CEC_POWER_STATUS_ON_PENDING,
   CEC_POWER_STATUS_STANDBY_PENDING,
) = range(4)

CEC_MENU_STATE_T = ct.c_uint32 # enum
(
   CEC_MENU_STATE_ACTIVATED,
   CEC_MENU_STATE_DEACTIVATED,
   CEC_MENU_STATE_QUERY,
) = range(3)

CEC_DECK_INFO_T = ct.c_uint32 # enum
(
   CEC_DECK_INFO_PLAY,
   CEC_DECK_INFO_RECORD,
   CEC_DECK_INFO_PLAY_REVERSE,
   CEC_DECK_INFO_STILL,
   CEC_DECK_INFO_SLOW,
   CEC_DECK_INFO_SLOW_REVERSE,
   CEC_DECK_INFO_SEARCH_FORWARD,
   CEC_DECK_INFO_SEARCH_REVERSE,
   CEC_DECK_INFO_NO_MEDIA,
   CEC_DECK_INFO_STOP,
   CEC_DECK_INFO_WIND,
   CEC_DECK_INFO_REWIND,
   CEC_DECK_IDX_SEARCH_FORWARD,
   CEC_DECK_IDX_SEARCH_REVERSE,
   CEC_DECK_OTHER_STATUS,
) = range(0x11, 0x20)

CEC_DECK_CTRL_MODE_T = ct.c_uint32 # enum
(
   CEC_DECK_CTRL_FORWARD,
   CEC_DECK_CTRL_BACKWARD,
   CEC_DECK_CTRL_STOP,
   CEC_DECK_CTRL_EJECT,
) = range(1, 5)

CEC_PLAY_MODE_T = ct.c_uint32 # enum
CEC_PLAY_FORWARD                       = 0x24
CEC_PLAY_REVERSE                       = 0x20
CEC_PLAY_STILL                         = 0x25
CEC_PLAY_SCAN_FORWARD_MIN_SPEED        = 0x05
CEC_PLAY_SCAN_FORWARD_MED_SPEED        = 0x06
CEC_PLAY_SCAN_FORWARD_MAX_SPEED        = 0x07
CEC_PLAY_SCAN_REVERSE_MIN_SPEED        = 0x09
CEC_PLAY_SCAN_REVERSE_MED_SPEED        = 0x0A
CEC_PLAY_SCAN_REVERSE_MAX_SPEED        = 0x0B
CEC_PLAY_SLOW_FORWARD_MIN_SPEED        = 0x15
CEC_PLAY_SLOW_FORWARD_MED_SPEED        = 0x16
CEC_PLAY_SLOW_FORWARD_MAX_SPEED        = 0x17
CEC_PLAY_SLOW_REVERSE_MIN_SPEED        = 0x19
CEC_PLAY_SLOW_REVERSE_MED_SPEED        = 0x1A
CEC_PLAY_SLOW_REVERSE_MAX_SPEED        = 0x1B

CEC_DECK_STATUS_REQUEST_T = ct.c_uint32 # enum
(
   CEC_DECK_STATUS_ON,
   CEC_DECK_STATUS_OFF,
   CEC_DECK_STATUS_ONCE,
) = range(1, 4)

CEC_USER_CONTROL_T = ct.c_uint32 # enum
CEC_User_Control_Select                      = 0x00
CEC_User_Control_Up                          = 0x01
CEC_User_Control_Down                        = 0x02
CEC_User_Control_Left                        = 0x03
CEC_User_Control_Right                       = 0x04
CEC_User_Control_RightUp                     = 0x05
CEC_User_Control_RightDown                   = 0x06
CEC_User_Control_LeftUp                      = 0x07
CEC_User_Control_LeftDown                    = 0x08
CEC_User_Control_RootMenu                    = 0x09
CEC_User_Control_SetupMenu                   = 0x0A
CEC_User_Control_ContentsMenu                = 0x0B
CEC_User_Control_FavoriteMenu                = 0x0C
CEC_User_Control_Exit                        = 0x0D
CEC_User_Control_Number0                     = 0x20
CEC_User_Control_Number1                     = 0x21
CEC_User_Control_Number2                     = 0x22
CEC_User_Control_Number3                     = 0x23
CEC_User_Control_Number4                     = 0x24
CEC_User_Control_Number5                     = 0x25
CEC_User_Control_Number6                     = 0x26
CEC_User_Control_Number7                     = 0x27
CEC_User_Control_Number8                     = 0x28
CEC_User_Control_Number9                     = 0x29
CEC_User_Control_Dot                         = 0x2A
CEC_User_Control_Enter                       = 0x2B
CEC_User_Control_Clear                       = 0x2C
CEC_User_Control_ChannelUp                   = 0x30
CEC_User_Control_ChannelDown                 = 0x31
CEC_User_Control_PreviousChannel             = 0x32
CEC_User_Control_SoundSelect                 = 0x33
CEC_User_Control_InputSelect                 = 0x34
CEC_User_Control_DisplayInformation          = 0x35
CEC_User_Control_Help                        = 0x36
CEC_User_Control_PageUp                      = 0x37
CEC_User_Control_PageDown                    = 0x38
CEC_User_Control_Power                       = 0x40
CEC_User_Control_VolumeUp                    = 0x41
CEC_User_Control_VolumeDown                  = 0x42
CEC_User_Control_Mute                        = 0x43
CEC_User_Control_Play                        = 0x44
CEC_User_Control_Stop                        = 0x45
CEC_User_Control_Pause                       = 0x46
CEC_User_Control_Record                      = 0x47
CEC_User_Control_Rewind                      = 0x48
CEC_User_Control_FastForward                 = 0x49
CEC_User_Control_Eject                       = 0x4A
CEC_User_Control_Forward                     = 0x4B
CEC_User_Control_Backward                    = 0x4C
CEC_User_Control_Angle                       = 0x50
CEC_User_Control_Subpicture                  = 0x51
CEC_User_Control_VideoOnDemand               = 0x52
CEC_User_Control_EPG                         = 0x53
CEC_User_Control_TimerProgramming            = 0x54
CEC_User_Control_InitialConfig               = 0x55
CEC_User_Control_PlayFunction                = 0x60
CEC_User_Control_PausePlayFunction           = 0x61
CEC_User_Control_RecordFunction              = 0x62
CEC_User_Control_PauseRecordFunction         = 0x63
CEC_User_Control_StopFunction                = 0x64
CEC_User_Control_MuteFunction                = 0x65
CEC_User_Control_RestoreVolumeFunction       = 0x66
CEC_User_Control_TuneFunction                = 0x67
CEC_User_Control_SelectDiskFunction          = 0x68
CEC_User_Control_SelectAVInputFunction       = 0x69
CEC_User_Control_SelectAudioInputFunction    = 0x6A
CEC_User_Control_F1Blue                      = 0x71
CEC_User_Control_F2Red                       = 0x72
CEC_User_Control_F3Green                     = 0x73
CEC_User_Control_F4Yellow                    = 0x74
CEC_User_Control_F5                          = 0x75

class VC_CEC_TOPOLOGY_T(ct.Structure):
    _fields_ = [
        ('active_mask', ct.c_uint16),
        ('num_devices', ct.c_uint16),
        ('device_attr', ct.c_uint32 * 16),
        ]

class VC_CEC_MESSAGE_T(ct.Structure):
    _fields_ = [
        ('length', ct.c_uint32),
        ('initiator', CEC_AllDevices_T),
        ('follower',  CEC_AllDevices_T),
        ('payload',   ct.c_uint8 * (CEC_MAX_XMIT_LENGTH + 1)),
        ]

VC_CEC_NOTIFY_T = ct.c_uint32 # enum
VC_CEC_NOTIFY_NONE       = 0
VC_CEC_TX                = 1 << 0
VC_CEC_RX                = 1 << 1
VC_CEC_BUTTON_PRESSED    = 1 << 2
VC_CEC_BUTTON_RELEASE    = 1 << 3
VC_CEC_REMOTE_PRESSED    = 1 << 4
VC_CEC_REMOTE_RELEASE    = 1 << 5
VC_CEC_LOGICAL_ADDR      = 1 << 6
VC_CEC_TOPOLOGY          = 1 << 7
VC_CEC_LOGICAL_ADDR_LOST = 1 << 15

CEC_CALLBACK_T = ct.CFUNCTYPE(
    None,
    ct.c_void_p, ct.c_uint32, ct.c_uint32, ct.c_uint32, ct.c_uint32)

CEC_CB_REASON     = lambda x: x & 0xFFFF
CEC_CB_MSG_LENGTH = lambda x: (x >> 16) & 0xFF
CEC_CB_RC         = lambda x: (x >> 24) & 0xFF

CEC_CB_INITIATOR  = lambda x: (x >> 4) & 0xF
CEC_CB_FOLLOWER   = lambda x: x & 0xF
CEC_CB_OPCODE     = lambda x: (x >> 8) & 0xFF
CEC_CB_OPERAND1   = lambda x: (x >> 16) & 0xFF
CEC_CB_OPERAND2   = lambda x: (x >> 24) & 0xFF

VC_CEC_ERROR_T = ct.c_uint32 # enum
(
   VC_CEC_SUCCESS,
   VC_CEC_ERROR_NO_ACK,
   VC_CEC_ERROR_SHUTDOWN,
   VC_CEC_ERROR_BUSY,
   VC_CEC_ERROR_NO_LA,
   VC_CEC_ERROR_NO_PA,
   VC_CEC_ERROR_NO_TOPO,
   VC_CEC_ERROR_INVALID_FOLLOWER,
   VC_CEC_ERROR_INVALID_ARGUMENT,
) = range(9)

# vc_cecservice.h ############################################################

CECSERVICE_CALLBACK_T = ct.CFUNCTYPE(
    None,
    ct.c_void_p, ct.c_uint32, ct.c_uint32, ct.c_uint32, ct.c_uint32, ct.c_uint32)

vc_vchi_cec_init = _lib.vc_vchi_cec_init
vc_vchi_cec_init.argtypes = [VCHI_INSTANCE_T, ct.POINTER(ct.POINTER(VCHI_CONNECTION_T)), ct.c_uint32]
vc_vchi_cec_init.restype = None

vc_vchi_cec_stop = _lib.vc_vchi_cec_stop
vc_vchi_cec_stop.argtypes = []
vc_vchi_cec_stop.restype = None

vc_cec_register_callback = _lib.vc_cec_register_callback
vc_cec_register_callback.argtypes = [CECSERVICE_CALLBACK_T, ct.c_void_p]
vc_cec_register_callback.restype = None

vc_cec_register_command = _lib.vc_cec_register_command
vc_cec_register_command.argtypes = [CEC_OPCODE_T]
vc_cec_register_command.restype = ct.c_int

vc_cec_register_all = _lib.vc_cec_register_all
vc_cec_register_all.argtypes = []
vc_cec_register_all.restype = ct.c_int

vc_cec_deregister_command = _lib.vc_cec_deregister_command
vc_cec_deregister_command.argtypes = [CEC_OPCODE_T]
vc_cec_deregister_command.restype = ct.c_int

vc_cec_deregister_all = _lib.vc_cec_deregister_all
vc_cec_deregister_all.argtypes = []
vc_cec_deregister_all.restype = ct.c_int

vc_cec_send_message = _lib.vc_cec_send_message
vc_cec_send_message.argtypes = [ct.c_uint32, ct.POINTER(ct.c_uint8), ct.c_uint32, vcos_bool_t]
vc_cec_send_message.restype = ct.c_int

vc_cec_get_logical_address = _lib.vc_cec_get_logical_address
vc_cec_get_logical_address.argtypes = [ct.POINTER(CEC_AllDevices_T)]
vc_cec_get_logical_address.restype = ct.c_int

vc_cec_alloc_logical_address = _lib.vc_cec_alloc_logical_address
vc_cec_alloc_logical_address.argtypes = []
vc_cec_alloc_logical_address.restype = ct.c_int

vc_cec_release_logical_address = _lib.vc_cec_release_logical_address
vc_cec_release_logical_address.argtypes = []
vc_cec_release_logical_address.restype = ct.c_int

vc_cec_get_topology = _lib.vc_cec_get_topology
vc_cec_get_topology.argtypes = [ct.POINTER(VC_CEC_TOPOLOGY_T)]
vc_cec_get_topology.restype = ct.c_int

vc_cec_set_vendor_id = _lib.vc_cec_set_vendor_id
vc_cec_set_vendor_id.argtypes = [ct.c_uint32]
vc_cec_set_vendor_id.restype = ct.c_int

vc_cec_set_osd_name = _lib.vc_cec_set_osd_name
vc_cec_set_osd_name.argtypes = [ct.c_char_p]
vc_cec_set_osd_name.restype = ct.c_int

vc_cec_get_physical_address = _lib.vc_cec_get_physical_address
vc_cec_get_physical_address.argtypes = [ct.POINTER(ct.c_uint16)]
vc_cec_get_physical_address.restype = ct.c_int

vc_cec_get_vendor_id = _lib.vc_cec_get_vendor_id
vc_cec_get_vendor_id.argtypes = [CEC_AllDevices_T, ct.POINTER(ct.c_uint32)]
vc_cec_get_vendor_id.restype = ct.c_int

vc_cec_device_type = _lib.vc_cec_device_type
vc_cec_device_type.argtypes = [CEC_AllDevices_T]
vc_cec_device_type.restype = CEC_DEVICE_TYPE_T

vc_cec_send_message2 = _lib.vc_cec_send_message2
vc_cec_send_message2.argtypes = [ct.POINTER(VC_CEC_MESSAGE_T)]
vc_cec_send_message2.restype = ct.c_int

vc_cec_param2message = _lib.vc_cec_param2message
vc_cec_param2message.argtypes = [ct.c_uint32, ct.c_uint32, ct.c_uint32, ct.c_uint32, ct.c_uint32, ct.POINTER(VC_CEC_MESSAGE_T)]
vc_cec_param2message.restype = ct.c_int

vc_cec_poll_address = _lib.vc_cec_poll_address
vc_cec_poll_address.argtypes = [CEC_AllDevices_T]
vc_cec_poll_address.restype = ct.c_int

vc_cec_set_logical_address = _lib.vc_cec_set_logical_address
vc_cec_set_logical_address.argtypes = [CEC_AllDevices_T, CEC_DEVICE_TYPE_T, ct.c_uint32]
vc_cec_set_logical_address.restype = ct.c_int

vc_cec_add_device = _lib.vc_cec_add_device
vc_cec_add_device.argtypes = [CEC_AllDevices_T, ct.c_uint16, CEC_DEVICE_TYPE_T, vcos_bool_t]
vc_cec_add_device.restype = ct.c_int

vc_cec_set_passive = _lib.vc_cec_set_passive
vc_cec_set_passive.argtypes = [vcos_bool_t]
vc_cec_set_passive.restype = ct.c_int

vc_cec_send_FeatureAbort = _lib.vc_cec_send_FeatureAbort
vc_cec_send_FeatureAbort.argtypes = [ct.c_uint32, CEC_OPCODE_T, CEC_ABORT_REASON_T]
vc_cec_send_FeatureAbort.restype = ct.c_int

vc_cec_send_ActiveSource = _lib.vc_cec_send_ActiveSource
vc_cec_send_ActiveSource.argtypes = [ct.c_uint16, vcos_bool_t]
vc_cec_send_ActiveSource.restype = ct.c_int

vc_cec_send_ImageViewOn = _lib.vc_cec_send_ImageViewOn
vc_cec_send_ImageViewOn.argtypes = [ct.c_uint32, vcos_bool_t]
vc_cec_send_ImageViewOn.restype = ct.c_int

vc_cec_send_SetOSDString = _lib.vc_cec_send_SetOSDString
vc_cec_send_SetOSDString.argtypes = [ct.c_uint32, CEC_DISPLAY_CONTROL_T, ct.c_char_p, vcos_bool_t]
vc_cec_send_SetOSDString.restype = ct.c_int

vc_cec_send_Standby = _lib.vc_cec_send_Standby
vc_cec_send_Standby.argtypes = [ct.c_uint32, vcos_bool_t]
vc_cec_send_Standby.restype = ct.c_int

vc_cec_send_MenuStatus = _lib.vc_cec_send_MenuStatus
vc_cec_send_MenuStatus.argtypes = [ct.c_uint32, CEC_MENU_STATE_T, vcos_bool_t]
vc_cec_send_MenuStatus.restype = ct.c_int

vc_cec_send_ReportPhysicalAddress = _lib.vc_cec_send_ReportPhysicalAddress
vc_cec_send_ReportPhysicalAddress.argtypes = [ct.c_uint16, CEC_DEVICE_TYPE_T, vcos_bool_t]
vc_cec_send_ReportPhysicalAddress.restype = ct.c_int

# vc_gencmd.h ################################################################

vc_gencmd_init = _lib.vc_gencmd_init
vc_gencmd_init.argtypes = []
vc_gencmd_init.restype = ct.c_int

vc_gencmd_stop = _lib.vc_gencmd_stop
vc_gencmd_stop.argtypes = []
vc_gencmd_stop.restype = None

vc_gencmd_send = _lib.vc_gencmd_send
vc_gencmd_send.argtypes = [ct.c_char_p]
vc_gencmd_send.restype = ct.c_int

vc_gencmd_read_response = _lib.vc_gencmd_read_response
vc_gencmd_read_response.argtypes = [ct.c_char_p, ct.c_int]
vc_gencmd_read_response.restype = ct.c_int

vc_gencmd = _lib.vc_gencmd
vc_gencmd.argtypes = [ct.c_char_p, ct.c_int, ct.c_char_p]
vc_gencmd.restype = ct.c_int

vc_gencmd_string_property = _lib.vc_gencmd_string_property
vc_gencmd_string_property.argtypes = [ct.c_char_p, ct.c_char_p, ct.POINTER(ct.c_char_p), ct.POINTER(ct.c_int)]
vc_gencmd_string_property.restype = ct.c_int

vc_gencmd_number_property = _lib.vc_gencmd_number_property
vc_gencmd_number_property.argtypes = [ct.c_char_p, ct.c_char_p, ct.POINTER(ct.c_int)]
vc_gencmd_number_property.restype = ct.c_int

vc_gencmd_until = _lib.vc_gencmd_until
vc_gencmd_until.argtypes = [ct.c_char_p, ct.c_char_p, ct.c_char_p, ct.c_char_p, ct.c_int]
vc_gencmd_until.restype = ct.c_int

