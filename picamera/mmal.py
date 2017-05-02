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

from .bcm_host import VCOS_UNSIGNED

_lib = ct.CDLL('libmmal.so')

# mmal.h #####################################################################

MMAL_VERSION_MAJOR = 0
MMAL_VERSION_MINOR = 1
MMAL_VERSION = (MMAL_VERSION_MAJOR << 16 | MMAL_VERSION_MINOR)

def MMAL_VERSION_TO_MAJOR(a):
    return a >> 16

def MMAL_VERSION_TO_MINOR(a):
    return a & 0xFFFF

# mmal_common.h ##############################################################

def MMAL_FOURCC(s):
    return sum(ord(c) << (i * 8) for (i, c) in enumerate(s))

def FOURCC_str(n):
    return ''.join(chr(n >> i & 0xFF) for i in range(0, 32, 8))

MMAL_MAGIC = MMAL_FOURCC('mmal')

MMAL_FALSE = 0
MMAL_TRUE = 1

class MMAL_BOOL_T(ct.c_int32):
    # This only exists to ensure we've got a distinct type to ct.c_int32
    # for mmalobj to perform dict-lookups against
    def __str__(self):
        return ['MMAL_FALSE', 'MMAL_TRUE'][bool(self.value)]

    def __repr__(self):
        return str(self)


class MMAL_CORE_STATISTICS_T(ct.Structure):
    _fields_ = [
        ('buffer_count',      ct.c_uint32),
        ('first_buffer_time', ct.c_uint32),
        ('last_buffer_time',  ct.c_uint32),
        ('max_delay',         ct.c_uint32),
        ]

class MMAL_CORE_PORT_STATISTICS_T(ct.Structure):
    _fields_ = [
        ('rx', MMAL_CORE_STATISTICS_T),
        ('tx', MMAL_CORE_STATISTICS_T),
        ]

MMAL_FIXED_16_16_T = ct.c_uint32

# mmal_types.h ###############################################################

MMAL_STATUS_T = ct.c_uint32 # enum
(
    MMAL_SUCCESS,
    MMAL_ENOMEM,
    MMAL_ENOSPC,
    MMAL_EINVAL,
    MMAL_ENOSYS,
    MMAL_ENOENT,
    MMAL_ENXIO,
    MMAL_EIO,
    MMAL_ESPIPE,
    MMAL_ECORRUPT,
    MMAL_ENOTREADY,
    MMAL_ECONFIG,
    MMAL_EISCONN,
    MMAL_ENOTCONN,
    MMAL_EAGAIN,
    MMAL_EFAULT,
) = range(16)
MMAL_STATUS_MAX = 0x7FFFFFFF

class MMAL_RECT_T(ct.Structure):
    _fields_ = [
        ('x',      ct.c_int32),
        ('y',      ct.c_int32),
        ('width',  ct.c_int32),
        ('height', ct.c_int32),
        ]

    def __repr__(self):
        return '(%d, %d)->(%d, %d)' % (
                self.x, self.y, self.x + self.width, self.y + self.height)

class MMAL_RATIONAL_T(ct.Structure):
    _fields_ = [
        ('num',  ct.c_int32),
        ('den',  ct.c_int32),
        ]

    def __repr__(self):
        return '%d/%d' % (self.num, self.den)

MMAL_TIME_UNKNOWN = ct.c_int64(1<<63).value

MMAL_FOURCC_T = ct.c_uint32

# mmal_format.h ##############################################################

MMAL_ES_TYPE_T = ct.c_uint32 # enum
(
   MMAL_ES_TYPE_UNKNOWN,
   MMAL_ES_TYPE_CONTROL,
   MMAL_ES_TYPE_AUDIO,
   MMAL_ES_TYPE_VIDEO,
   MMAL_ES_TYPE_SUBPICTURE,
) = range(5)

class MMAL_VIDEO_FORMAT_T(ct.Structure):
    _fields_ = [
        ('width',       ct.c_uint32),
        ('height',      ct.c_uint32),
        ('crop',        MMAL_RECT_T),
        ('frame_rate',  MMAL_RATIONAL_T),
        ('par',         MMAL_RATIONAL_T),
        ('color_space', MMAL_FOURCC_T),
        ]

    def __repr__(self):
        return '<MMAL_VIDEO_FORMAT_T width=%d, height=%d, crop=%r, frame_rate=%r, par=%r, color_space=%r>' % (
                self.width, self.height, self.crop, self.frame_rate, self.par, self.color_space)

class MMAL_AUDIO_FORMAT_T(ct.Structure):
    _fields_ = [
        ('channels',        ct.c_uint32),
        ('sample_rate',     ct.c_uint32),
        ('bits_per_sample', ct.c_uint32),
        ('block_align',     ct.c_uint32),
        ]

    def __repr__(self):
        return '<MMAL_AUDIO_FORMAT_T channels=%d, sample_rate=%d, bits_per_sample=%d, block_align=%d>' % (
                self.channels, self.sample_rate, self.bits_per_sample, self.block_align)

class MMAL_SUBPICTURE_FORMAT_T(ct.Structure):
    _fields_ = [
        ('x_offset', ct.c_uint32),
        ('y_offset', ct.c_uint32),
        ]

    def __repr__(self):
        return '<MMAL_SUBPICTURE_FORMAT_T x_offset=%d, y_offset=%d>' % (
                self.x_offset, self.y_offset)

class MMAL_ES_SPECIFIC_FORMAT_T(ct.Union):
    _fields_ = [
        ('audio',      MMAL_AUDIO_FORMAT_T),
        ('video',      MMAL_VIDEO_FORMAT_T),
        ('subpicture', MMAL_SUBPICTURE_FORMAT_T),
        ]

MMAL_ES_FORMAT_FLAG_FRAMED = 0x01
MMAL_ENCODING_UNKNOWN = 0
MMAL_ENCODING_VARIANT_DEFAULT = 0

class MMAL_ES_FORMAT_T(ct.Structure):
    _fields_ = [
        ('type',             MMAL_ES_TYPE_T),
        ('encoding',         MMAL_FOURCC_T),
        ('encoding_variant', MMAL_FOURCC_T),
        ('es',               ct.POINTER(MMAL_ES_SPECIFIC_FORMAT_T)),
        ('bitrate',          ct.c_uint32),
        ('flags',            ct.c_uint32),
        ('extradata_size',   ct.c_uint32),
        ('extradata',        ct.POINTER(ct.c_uint8)),
        ]

    def __repr__(self):
        return '<MMAL_ES_FORMAT_T type=%r, encoding=%r, ...>' % (self.type, self.encoding)

mmal_format_alloc = _lib.mmal_format_alloc
mmal_format_alloc.argtypes = []
mmal_format_alloc.restype = ct.POINTER(MMAL_ES_FORMAT_T)

mmal_format_free = _lib.mmal_format_free
mmal_format_free.argtypes = [ct.POINTER(MMAL_ES_FORMAT_T)]
mmal_format_free.restype = None

mmal_format_extradata_alloc = _lib.mmal_format_extradata_alloc
mmal_format_extradata_alloc.argtypes = [ct.POINTER(MMAL_ES_FORMAT_T), ct.c_uint]
mmal_format_extradata_alloc.restype = MMAL_STATUS_T

mmal_format_copy = _lib.mmal_format_copy
mmal_format_copy.argtypes = [ct.POINTER(MMAL_ES_FORMAT_T), ct.POINTER(MMAL_ES_FORMAT_T)]
mmal_format_copy.restype = None

mmal_format_full_copy = _lib.mmal_format_full_copy
mmal_format_full_copy.argtypes = [ct.POINTER(MMAL_ES_FORMAT_T), ct.POINTER(MMAL_ES_FORMAT_T)]
mmal_format_full_copy.restype = MMAL_STATUS_T

MMAL_ES_FORMAT_COMPARE_FLAG_TYPE             = 0x01
MMAL_ES_FORMAT_COMPARE_FLAG_ENCODING         = 0x02
MMAL_ES_FORMAT_COMPARE_FLAG_BITRATE          = 0x04
MMAL_ES_FORMAT_COMPARE_FLAG_FLAGS            = 0x08
MMAL_ES_FORMAT_COMPARE_FLAG_EXTRADATA        = 0x10

MMAL_ES_FORMAT_COMPARE_FLAG_VIDEO_RESOLUTION   = 0x0100
MMAL_ES_FORMAT_COMPARE_FLAG_VIDEO_CROPPING     = 0x0200
MMAL_ES_FORMAT_COMPARE_FLAG_VIDEO_FRAME_RATE   = 0x0400
MMAL_ES_FORMAT_COMPARE_FLAG_VIDEO_ASPECT_RATIO = 0x0800
MMAL_ES_FORMAT_COMPARE_FLAG_VIDEO_COLOR_SPACE  = 0x1000

MMAL_ES_FORMAT_COMPARE_FLAG_ES_OTHER = 0x10000000

mmal_format_compare = _lib.mmal_format_compare
mmal_format_compare.argtypes = [ct.POINTER(MMAL_ES_FORMAT_T), ct.POINTER(MMAL_ES_FORMAT_T)]
mmal_format_compare.restype = ct.c_uint32

# mmal_buffer.h ##############################################################

class MMAL_BUFFER_HEADER_VIDEO_SPECIFIC_T(ct.Structure):
    _fields_ = [
        ('planes', ct.c_uint32),
        ('offset', ct.c_uint32 * 4),
        ('pitch',  ct.c_uint32 * 4),
        ('flags',  ct.c_uint32),
        ]

class MMAL_BUFFER_HEADER_TYPE_SPECIFIC_T(ct.Union):
    _fields_ = [
        ('video', MMAL_BUFFER_HEADER_VIDEO_SPECIFIC_T),
        ]

class MMAL_BUFFER_HEADER_PRIVATE_T(ct.Structure):
    _fields_ = []

class MMAL_BUFFER_HEADER_T(ct.Structure):
    pass

MMAL_BUFFER_HEADER_T._fields_ = [
        ('next',       ct.POINTER(MMAL_BUFFER_HEADER_T)), # self-reference
        ('priv',       ct.POINTER(MMAL_BUFFER_HEADER_PRIVATE_T)),
        ('cmd',        ct.c_uint32),
        ('data',       ct.POINTER(ct.c_uint8)),
        ('alloc_size', ct.c_uint32),
        ('length',     ct.c_uint32),
        ('offset',     ct.c_uint32),
        ('flags',      ct.c_uint32),
        ('pts',        ct.c_int64),
        ('dts',        ct.c_int64),
        ('type',       ct.POINTER(MMAL_BUFFER_HEADER_TYPE_SPECIFIC_T)),
        ('user_data',  ct.c_void_p),
        ]

MMAL_BUFFER_HEADER_FLAG_EOS                    = (1<<0)
MMAL_BUFFER_HEADER_FLAG_FRAME_START            = (1<<1)
MMAL_BUFFER_HEADER_FLAG_FRAME_END              = (1<<2)
MMAL_BUFFER_HEADER_FLAG_FRAME                  = (MMAL_BUFFER_HEADER_FLAG_FRAME_START|MMAL_BUFFER_HEADER_FLAG_FRAME_END)
MMAL_BUFFER_HEADER_FLAG_KEYFRAME               = (1<<3)
MMAL_BUFFER_HEADER_FLAG_DISCONTINUITY          = (1<<4)
MMAL_BUFFER_HEADER_FLAG_CONFIG                 = (1<<5)
MMAL_BUFFER_HEADER_FLAG_ENCRYPTED              = (1<<6)
MMAL_BUFFER_HEADER_FLAG_CODECSIDEINFO          = (1<<7)
MMAL_BUFFER_HEADER_FLAGS_SNAPSHOT              = (1<<8)
MMAL_BUFFER_HEADER_FLAG_CORRUPTED              = (1<<9)
MMAL_BUFFER_HEADER_FLAG_TRANSMISSION_FAILED    = (1<<10)
MMAL_BUFFER_HEADER_FLAG_DECODEONLY             = (1<<11)

MMAL_BUFFER_HEADER_FLAG_FORMAT_SPECIFIC_START  = (1<<16)
MMAL_BUFFER_HEADER_VIDEO_FLAG_INTERLACED       = (MMAL_BUFFER_HEADER_FLAG_FORMAT_SPECIFIC_START<<0)
MMAL_BUFFER_HEADER_VIDEO_FLAG_TOP_FIELD_FIRST  = (MMAL_BUFFER_HEADER_FLAG_FORMAT_SPECIFIC_START<<1)
MMAL_BUFFER_HEADER_VIDEO_FLAG_DISPLAY_EXTERNAL = (MMAL_BUFFER_HEADER_FLAG_FORMAT_SPECIFIC_START<<3)
MMAL_BUFFER_HEADER_VIDEO_FLAG_PROTECTED        = (MMAL_BUFFER_HEADER_FLAG_FORMAT_SPECIFIC_START<<4)

mmal_buffer_header_acquire = _lib.mmal_buffer_header_acquire
mmal_buffer_header_acquire.argtypes = [ct.POINTER(MMAL_BUFFER_HEADER_T)]
mmal_buffer_header_acquire.restype = None

mmal_buffer_header_reset = _lib.mmal_buffer_header_reset
mmal_buffer_header_reset.argtypes = [ct.POINTER(MMAL_BUFFER_HEADER_T)]
mmal_buffer_header_reset.restype = None

mmal_buffer_header_release = _lib.mmal_buffer_header_release
mmal_buffer_header_release.argtypes = [ct.POINTER(MMAL_BUFFER_HEADER_T)]
mmal_buffer_header_release.restype = None

mmal_buffer_header_release_continue = _lib.mmal_buffer_header_release_continue
mmal_buffer_header_release_continue.argtypes = [ct.POINTER(MMAL_BUFFER_HEADER_T)]
mmal_buffer_header_release_continue.restype = None

MMAL_BH_PRE_RELEASE_CB_T = ct.CFUNCTYPE(
    MMAL_BOOL_T,
    ct.POINTER(MMAL_BUFFER_HEADER_T), ct.c_void_p)

mmal_buffer_header_pre_release_cb_set = _lib.mmal_buffer_header_pre_release_cb_set
mmal_buffer_header_pre_release_cb_set.argtypes = [ct.POINTER(MMAL_BUFFER_HEADER_T), MMAL_BH_PRE_RELEASE_CB_T, ct.c_void_p]
mmal_buffer_header_pre_release_cb_set.restype = None

mmal_buffer_header_replicate = _lib.mmal_buffer_header_replicate
mmal_buffer_header_replicate.argtypes = [ct.POINTER(MMAL_BUFFER_HEADER_T), ct.POINTER(MMAL_BUFFER_HEADER_T)]
mmal_buffer_header_replicate.restype = MMAL_STATUS_T

mmal_buffer_header_mem_lock = _lib.mmal_buffer_header_mem_lock
mmal_buffer_header_mem_lock.argtypes = [ct.POINTER(MMAL_BUFFER_HEADER_T)]
mmal_buffer_header_mem_lock.restype = MMAL_STATUS_T

mmal_buffer_header_mem_unlock = _lib.mmal_buffer_header_mem_unlock
mmal_buffer_header_mem_unlock.argtypes = [ct.POINTER(MMAL_BUFFER_HEADER_T)]
mmal_buffer_header_mem_unlock.restype = None

# mmal_clock.h ###############################################################

MMAL_CLOCK_EVENT_MAGIC              = MMAL_FOURCC('CKLM')
MMAL_CLOCK_EVENT_REFERENCE          = MMAL_FOURCC('CREF')
MMAL_CLOCK_EVENT_ACTIVE             = MMAL_FOURCC('CACT')
MMAL_CLOCK_EVENT_SCALE              = MMAL_FOURCC('CSCA')
MMAL_CLOCK_EVENT_TIME               = MMAL_FOURCC('CTIM')
MMAL_CLOCK_EVENT_UPDATE_THRESHOLD   = MMAL_FOURCC('CUTH')
MMAL_CLOCK_EVENT_DISCONT_THRESHOLD  = MMAL_FOURCC('CDTH')
MMAL_CLOCK_EVENT_REQUEST_THRESHOLD  = MMAL_FOURCC('CRTH')
MMAL_CLOCK_EVENT_INPUT_BUFFER_INFO  = MMAL_FOURCC('CIBI')
MMAL_CLOCK_EVENT_OUTPUT_BUFFER_INFO = MMAL_FOURCC('COBI')
MMAL_CLOCK_EVENT_LATENCY            = MMAL_FOURCC('CLAT')
MMAL_CLOCK_EVENT_INVALID            = 0

class MMAL_CLOCK_UPDATE_THRESHOLD_T(ct.Structure):
    _fields_ = [
        ('threshold_lower', ct.c_int64),
        ('threshold_upper', ct.c_int64),
        ]

class MMAL_CLOCK_DISCONT_THRESHOLD_T(ct.Structure):
    _fields_ = [
        ('threshold', ct.c_int64),
        ('duration',  ct.c_int64),
        ]

class MMAL_CLOCK_REQUEST_THRESHOLD_T(ct.Structure):
    _fields_ = [
        ('threshold',        ct.c_int64),
        ('threshold_enable', MMAL_BOOL_T),
        ]

class MMAL_CLOCK_BUFFER_INFO_T(ct.Structure):
    _fields_ = [
        ('time_stamp',   ct.c_int64),
        ('arrival_time', ct.c_uint32),
        ]

class MMAL_CLOCK_LATENCY_T(ct.Structure):
    _fields_ = [
        ('target',        ct.c_int64),
        ('attack_period', ct.c_int64),
        ('attack_rate',   ct.c_int64),
        ]

class _MMAL_CLOCK_EVENT_DATA(ct.Union):
    _fields_ = [
        ('enable',            MMAL_BOOL_T),
        ('scale',             MMAL_RATIONAL_T),
        ('media_time',        ct.c_int64),
        ('update_threshold',  MMAL_CLOCK_UPDATE_THRESHOLD_T),
        ('discont_threshold', MMAL_CLOCK_DISCONT_THRESHOLD_T),
        ('request_threshold', MMAL_CLOCK_REQUEST_THRESHOLD_T),
        ('buffer',            MMAL_CLOCK_BUFFER_INFO_T),
        ('latency',           MMAL_CLOCK_LATENCY_T),
        ]

class MMAL_CLOCK_EVENT_T(ct.Structure):
    _fields_ = [
        ('id',        ct.c_uint32),
        ('magic',     ct.c_uint32),
        ('buffer',    ct.POINTER(MMAL_BUFFER_HEADER_T)),
        ('padding0',  ct.c_uint32),
        ('data',      _MMAL_CLOCK_EVENT_DATA),
        ('padding1',  ct.c_uint64),
        ]

# Ensure MMAL_CLOCK_EVENT_T preserves 64-bit alignment
assert not ct.sizeof(MMAL_CLOCK_EVENT_T) & 0x07

def MMAL_CLOCK_EVENT_INIT(i):
    return MMAL_CLOCK_EVENT_T(
        id=i,
        magic=MMAL_CLOCK_EVENT_MAGIC,
        buffer=None,
        padding0=0,
        data=_MMAL_CLOCK_EVENT_DATA(enable=MMAL_FALSE),
        padding1=0,
        )

# mmal_parameters_common.h ###################################################

MMAL_PARAMETER_GROUP_COMMON   = (0<<16)
MMAL_PARAMETER_GROUP_CAMERA   = (1<<16)
MMAL_PARAMETER_GROUP_VIDEO    = (2<<16)
MMAL_PARAMETER_GROUP_AUDIO    = (3<<16)
MMAL_PARAMETER_GROUP_CLOCK    = (4<<16)
MMAL_PARAMETER_GROUP_MIRACAST = (5<<16)

(
    MMAL_PARAMETER_UNUSED,
    MMAL_PARAMETER_SUPPORTED_ENCODINGS,
    MMAL_PARAMETER_URI,
    MMAL_PARAMETER_CHANGE_EVENT_REQUEST,
    MMAL_PARAMETER_ZERO_COPY,
    MMAL_PARAMETER_BUFFER_REQUIREMENTS,
    MMAL_PARAMETER_STATISTICS,
    MMAL_PARAMETER_CORE_STATISTICS,
    MMAL_PARAMETER_MEM_USAGE,
    MMAL_PARAMETER_BUFFER_FLAG_FILTER,
    MMAL_PARAMETER_SEEK,
    MMAL_PARAMETER_POWERMON_ENABLE,
    MMAL_PARAMETER_LOGGING,
    MMAL_PARAMETER_SYSTEM_TIME,
    MMAL_PARAMETER_NO_IMAGE_PADDING,
    MMAL_PARAMETER_LOCKSTEP_ENABLE,
) = range(MMAL_PARAMETER_GROUP_COMMON, MMAL_PARAMETER_GROUP_COMMON + 16)

class MMAL_PARAMETER_HEADER_T(ct.Structure):
    _fields_ = [
        ('id',   ct.c_uint32),
        ('size', ct.c_uint32),
        ]

class MMAL_PARAMETER_CHANGE_EVENT_REQUEST_T(ct.Structure):
    _fields_ = [
        ('hdr',       MMAL_PARAMETER_HEADER_T),
        ('change_id', ct.c_uint32),
        ('enable',    MMAL_BOOL_T),
        ]

class MMAL_PARAMETER_BUFFER_REQUIREMENTS_T(ct.Structure):
    _fields_ = [
        ('hdr',                     MMAL_PARAMETER_HEADER_T),
        ('buffer_num_min',          ct.c_uint32),
        ('buffer_size_min',         ct.c_uint32),
        ('buffer_alignment_min',    ct.c_uint32),
        ('buffer_num_recommended',  ct.c_uint32),
        ('buffer_size_recommended', ct.c_uint32),
        ]

class MMAL_PARAMETER_SEEK_T(ct.Structure):
    _fields_ = [
        ('hdr',    MMAL_PARAMETER_HEADER_T),
        ('offset', ct.c_int64),
        ('flags',  ct.c_uint32),
        ]

MMAL_PARAM_SEEK_FLAG_PRECISE = 0x01
MMAL_PARAM_SEEK_FLAG_FORWARD = 0x02

class MMAL_PARAMETER_STATISTICS_T(ct.Structure):
    _fields_ = [
        ('hdr',                 MMAL_PARAMETER_HEADER_T),
        ('buffer_count',        ct.c_uint32),
        ('frame_count',         ct.c_uint32),
        ('frames_skipped',      ct.c_uint32),
        ('frames_discarded',    ct.c_uint32),
        ('eos_seen',            ct.c_uint32),
        ('maximum_frame_bytes', ct.c_uint32),
        ('total_bytes',         ct.c_int64),
        ('corrupt_macroblocks', ct.c_uint32),
        ]

MMAL_CORE_STATS_DIR = ct.c_uint32 # enum
(
    MMAL_CORE_STATS_RX,
    MMAL_CORE_STATS_TX,
) = range(2)
MMAL_CORE_STATS_MAX = 0x7fffffff

class MMAL_PARAMETER_CORE_STATISTICS_T(ct.Structure):
    _fields_ = [
        ('hdr',   MMAL_PARAMETER_HEADER_T),
        ('dir',   MMAL_CORE_STATS_DIR),
        ('reset', MMAL_BOOL_T),
        ('stats', MMAL_CORE_STATISTICS_T),
        ]

class MMAL_PARAMETER_MEM_USAGE_T(ct.Structure):
    _fields_ = [
        ('hdr',                 MMAL_PARAMETER_HEADER_T),
        ('pool_mem_alloc_size', ct.c_uint32),
        ]

class MMAL_PARAMETER_LOGGING_T(ct.Structure):
    _fields_ = [
        ('hdr',   MMAL_PARAMETER_HEADER_T),
        ('set',   ct.c_uint32),
        ('clear', ct.c_uint32),
        ]

# mmal_parameters_camera.h ###################################################

(
    MMAL_PARAMETER_THUMBNAIL_CONFIGURATION,
    MMAL_PARAMETER_CAPTURE_QUALITY,
    MMAL_PARAMETER_ROTATION,
    MMAL_PARAMETER_EXIF_DISABLE,
    MMAL_PARAMETER_EXIF,
    MMAL_PARAMETER_AWB_MODE,
    MMAL_PARAMETER_IMAGE_EFFECT,
    MMAL_PARAMETER_COLOUR_EFFECT,
    MMAL_PARAMETER_FLICKER_AVOID,
    MMAL_PARAMETER_FLASH,
    MMAL_PARAMETER_REDEYE,
    MMAL_PARAMETER_FOCUS,
    MMAL_PARAMETER_FOCAL_LENGTHS,
    MMAL_PARAMETER_EXPOSURE_COMP,
    MMAL_PARAMETER_ZOOM,
    MMAL_PARAMETER_MIRROR,
    MMAL_PARAMETER_CAMERA_NUM,
    MMAL_PARAMETER_CAPTURE,
    MMAL_PARAMETER_EXPOSURE_MODE,
    MMAL_PARAMETER_EXP_METERING_MODE,
    MMAL_PARAMETER_FOCUS_STATUS,
    MMAL_PARAMETER_CAMERA_CONFIG,
    MMAL_PARAMETER_CAPTURE_STATUS,
    MMAL_PARAMETER_FACE_TRACK,
    MMAL_PARAMETER_DRAW_BOX_FACES_AND_FOCUS,
    MMAL_PARAMETER_JPEG_Q_FACTOR,
    MMAL_PARAMETER_FRAME_RATE,
    MMAL_PARAMETER_USE_STC,
    MMAL_PARAMETER_CAMERA_INFO,
    MMAL_PARAMETER_VIDEO_STABILISATION,
    MMAL_PARAMETER_FACE_TRACK_RESULTS,
    MMAL_PARAMETER_ENABLE_RAW_CAPTURE,
    MMAL_PARAMETER_DPF_FILE,
    MMAL_PARAMETER_ENABLE_DPF_FILE,
    MMAL_PARAMETER_DPF_FAIL_IS_FATAL,
    MMAL_PARAMETER_CAPTURE_MODE,
    MMAL_PARAMETER_FOCUS_REGIONS,
    MMAL_PARAMETER_INPUT_CROP,
    MMAL_PARAMETER_SENSOR_INFORMATION,
    MMAL_PARAMETER_FLASH_SELECT,
    MMAL_PARAMETER_FIELD_OF_VIEW,
    MMAL_PARAMETER_HIGH_DYNAMIC_RANGE,
    MMAL_PARAMETER_DYNAMIC_RANGE_COMPRESSION,
    MMAL_PARAMETER_ALGORITHM_CONTROL,
    MMAL_PARAMETER_SHARPNESS,
    MMAL_PARAMETER_CONTRAST,
    MMAL_PARAMETER_BRIGHTNESS,
    MMAL_PARAMETER_SATURATION,
    MMAL_PARAMETER_ISO,
    MMAL_PARAMETER_ANTISHAKE,
    MMAL_PARAMETER_IMAGE_EFFECT_PARAMETERS,
    MMAL_PARAMETER_CAMERA_BURST_CAPTURE,
    MMAL_PARAMETER_CAMERA_MIN_ISO,
    MMAL_PARAMETER_CAMERA_USE_CASE,
    MMAL_PARAMETER_CAPTURE_STATS_PASS,
    MMAL_PARAMETER_CAMERA_CUSTOM_SENSOR_CONFIG,
    MMAL_PARAMETER_ENABLE_REGISTER_FILE,
    MMAL_PARAMETER_REGISTER_FAIL_IS_FATAL,
    MMAL_PARAMETER_CONFIGFILE_REGISTERS,
    MMAL_PARAMETER_CONFIGFILE_CHUNK_REGISTERS,
    MMAL_PARAMETER_JPEG_ATTACH_LOG,
    MMAL_PARAMETER_ZERO_SHUTTER_LAG,
    MMAL_PARAMETER_FPS_RANGE,
    MMAL_PARAMETER_CAPTURE_EXPOSURE_COMP,
    MMAL_PARAMETER_SW_SHARPEN_DISABLE,
    MMAL_PARAMETER_FLASH_REQUIRED,
    MMAL_PARAMETER_SW_SATURATION_DISABLE,
    MMAL_PARAMETER_SHUTTER_SPEED,
    MMAL_PARAMETER_CUSTOM_AWB_GAINS,
    MMAL_PARAMETER_CAMERA_SETTINGS,
    MMAL_PARAMETER_PRIVACY_INDICATOR,
    MMAL_PARAMETER_VIDEO_DENOISE,
    MMAL_PARAMETER_STILLS_DENOISE,
    MMAL_PARAMETER_ANNOTATE,
    MMAL_PARAMETER_STEREOSCOPIC_MODE,
    MMAL_PARAMETER_CAMERA_INTERFACE,
    MMAL_PARAMETER_CAMERA_CLOCKING_MODE,
    MMAL_PARAMETER_CAMERA_RX_CONFIG,
    MMAL_PARAMETER_CAMERA_RX_TIMING,
    MMAL_PARAMETER_DPF_CONFIG,
    MMAL_PARAMETER_JPEG_RESTART_INTERVAL,
) = range(MMAL_PARAMETER_GROUP_CAMERA, MMAL_PARAMETER_GROUP_CAMERA + 81)

class MMAL_PARAMETER_THUMBNAIL_CONFIG_T(ct.Structure):
    _fields_ = [
        ('hdr',     MMAL_PARAMETER_HEADER_T),
        ('enable',  ct.c_uint32),
        ('width',   ct.c_uint32),
        ('height',  ct.c_uint32),
        ('quality', ct.c_uint32),
        ]

class MMAL_PARAMETER_EXIF_T(ct.Structure):
    _fields_ = [
        ('hdr',          MMAL_PARAMETER_HEADER_T),
        ('keylen',       ct.c_uint32),
        ('value_offset', ct.c_uint32),
        ('valuelen',     ct.c_uint32),
        ('data',         ct.c_uint8 * 1),
        ]

MMAL_PARAM_EXPOSUREMODE_T = ct.c_uint32 # enum
(
    MMAL_PARAM_EXPOSUREMODE_OFF,
    MMAL_PARAM_EXPOSUREMODE_AUTO,
    MMAL_PARAM_EXPOSUREMODE_NIGHT,
    MMAL_PARAM_EXPOSUREMODE_NIGHTPREVIEW,
    MMAL_PARAM_EXPOSUREMODE_BACKLIGHT,
    MMAL_PARAM_EXPOSUREMODE_SPOTLIGHT,
    MMAL_PARAM_EXPOSUREMODE_SPORTS,
    MMAL_PARAM_EXPOSUREMODE_SNOW,
    MMAL_PARAM_EXPOSUREMODE_BEACH,
    MMAL_PARAM_EXPOSUREMODE_VERYLONG,
    MMAL_PARAM_EXPOSUREMODE_FIXEDFPS,
    MMAL_PARAM_EXPOSUREMODE_ANTISHAKE,
    MMAL_PARAM_EXPOSUREMODE_FIREWORKS,
) = range(13)
MMAL_PARAM_EXPOSUREMODE_MAX = 0x7fffffff

class MMAL_PARAMETER_EXPOSUREMODE_T(ct.Structure):
    _fields_ = [
        ('hdr',   MMAL_PARAMETER_HEADER_T),
        ('value', MMAL_PARAM_EXPOSUREMODE_T),
        ]

MMAL_PARAM_EXPOSUREMETERINGMODE_T = ct.c_uint32 # enum
(
    MMAL_PARAM_EXPOSUREMETERINGMODE_AVERAGE,
    MMAL_PARAM_EXPOSUREMETERINGMODE_SPOT,
    MMAL_PARAM_EXPOSUREMETERINGMODE_BACKLIT,
    MMAL_PARAM_EXPOSUREMETERINGMODE_MATRIX,
) = range(4)
MMAL_PARAM_EXPOSUREMETERINGMODE_MAX = 0x7fffffff

class MMAL_PARAMETER_EXPOSUREMETERINGMODE_T(ct.Structure):
    _fields_ = [
        ('hdr',   MMAL_PARAMETER_HEADER_T),
        ('value', MMAL_PARAM_EXPOSUREMETERINGMODE_T),
        ]

MMAL_PARAM_AWBMODE_T = ct.c_uint32 # enum
(
    MMAL_PARAM_AWBMODE_OFF,
    MMAL_PARAM_AWBMODE_AUTO,
    MMAL_PARAM_AWBMODE_SUNLIGHT,
    MMAL_PARAM_AWBMODE_CLOUDY,
    MMAL_PARAM_AWBMODE_SHADE,
    MMAL_PARAM_AWBMODE_TUNGSTEN,
    MMAL_PARAM_AWBMODE_FLUORESCENT,
    MMAL_PARAM_AWBMODE_INCANDESCENT,
    MMAL_PARAM_AWBMODE_FLASH,
    MMAL_PARAM_AWBMODE_HORIZON,
) = range(10)
MMAL_PARAM_AWBMODE_MAX = 0x7fffffff

class MMAL_PARAMETER_AWBMODE_T(ct.Structure):
    _fields_ = [
        ('hdr',   MMAL_PARAMETER_HEADER_T),
        ('value', MMAL_PARAM_AWBMODE_T),
        ]

MMAL_PARAM_IMAGEFX_T = ct.c_uint32 # enum
(
    MMAL_PARAM_IMAGEFX_NONE,
    MMAL_PARAM_IMAGEFX_NEGATIVE,
    MMAL_PARAM_IMAGEFX_SOLARIZE,
    MMAL_PARAM_IMAGEFX_POSTERIZE,
    MMAL_PARAM_IMAGEFX_WHITEBOARD,
    MMAL_PARAM_IMAGEFX_BLACKBOARD,
    MMAL_PARAM_IMAGEFX_SKETCH,
    MMAL_PARAM_IMAGEFX_DENOISE,
    MMAL_PARAM_IMAGEFX_EMBOSS,
    MMAL_PARAM_IMAGEFX_OILPAINT,
    MMAL_PARAM_IMAGEFX_HATCH,
    MMAL_PARAM_IMAGEFX_GPEN,
    MMAL_PARAM_IMAGEFX_PASTEL,
    MMAL_PARAM_IMAGEFX_WATERCOLOUR,
    MMAL_PARAM_IMAGEFX_FILM,
    MMAL_PARAM_IMAGEFX_BLUR,
    MMAL_PARAM_IMAGEFX_SATURATION,
    MMAL_PARAM_IMAGEFX_COLOURSWAP,
    MMAL_PARAM_IMAGEFX_WASHEDOUT,
    MMAL_PARAM_IMAGEFX_POSTERISE,
    MMAL_PARAM_IMAGEFX_COLOURPOINT,
    MMAL_PARAM_IMAGEFX_COLOURBALANCE,
    MMAL_PARAM_IMAGEFX_CARTOON,
    MMAL_PARAM_IMAGEFX_DEINTERLACE_DOUBLE,
    MMAL_PARAM_IMAGEFX_DEINTERLACE_ADV,
    MMAL_PARAM_IMAGEFX_DEINTERLACE_FAST,
) = range(26)
MMAL_PARAM_IMAGEFX_MAX = 0x7fffffff

class MMAL_PARAMETER_IMAGEFX_T(ct.Structure):
    _fields_ = [
        ('hdr',   MMAL_PARAMETER_HEADER_T),
        ('value', MMAL_PARAM_IMAGEFX_T),
        ]

MMAL_MAX_IMAGEFX_PARAMETERS = 6

class MMAL_PARAMETER_IMAGEFX_PARAMETERS_T(ct.Structure):
    _fields_ = [
        ('hdr',               MMAL_PARAMETER_HEADER_T),
        ('effect',            MMAL_PARAM_IMAGEFX_T),
        ('num_effect_params', ct.c_uint32),
        ('effect_parameter',  ct.c_uint32 * MMAL_MAX_IMAGEFX_PARAMETERS),
        ]

class MMAL_PARAMETER_COLOURFX_T(ct.Structure):
    _fields_ = [
        ('hdr',    MMAL_PARAMETER_HEADER_T),
        ('enable', ct.c_int32),
        ('u',      ct.c_uint32),
        ('v',      ct.c_uint32),
        ]

MMAL_CAMERA_STC_MODE_T = ct.c_uint32 # enum
(
    MMAL_PARAM_STC_MODE_OFF,
    MMAL_PARAM_STC_MODE_RAW,
    MMAL_PARAM_STC_MODE_COOKED,
) = range(3)
MMAL_PARAM_STC_MODE_MAX = 0x7fffffff

class MMAL_PARAMETER_CAMERA_STC_MODE_T(ct.Structure):
    _fields_ = [
        ('hdr',   MMAL_PARAMETER_HEADER_T),
        ('value', MMAL_CAMERA_STC_MODE_T),
        ]

MMAL_PARAM_FLICKERAVOID_T = ct.c_uint32 # enum
(
    MMAL_PARAM_FLICKERAVOID_OFF,
    MMAL_PARAM_FLICKERAVOID_AUTO,
    MMAL_PARAM_FLICKERAVOID_50HZ,
    MMAL_PARAM_FLICKERAVOID_60HZ,
) = range(4)
MMAL_PARAM_FLICKERAVOID_MAX = 0x7FFFFFFF

class MMAL_PARAMETER_FLICKERAVOID_T(ct.Structure):
    _fields_ = [
        ('hdr',   MMAL_PARAMETER_HEADER_T),
        ('value', MMAL_PARAM_FLICKERAVOID_T),
        ]

MMAL_PARAM_FLASH_T = ct.c_uint32 # enum
(
    MMAL_PARAM_FLASH_OFF,
    MMAL_PARAM_FLASH_AUTO,
    MMAL_PARAM_FLASH_ON,
    MMAL_PARAM_FLASH_REDEYE,
    MMAL_PARAM_FLASH_FILLIN,
    MMAL_PARAM_FLASH_TORCH,
) = range(6)
MMAL_PARAM_FLASH_MAX = 0x7FFFFFFF

class MMAL_PARAMETER_FLASH_T(ct.Structure):
    _fields_ = [
        ('hdr',   MMAL_PARAMETER_HEADER_T),
        ('value', MMAL_PARAM_FLASH_T),
        ]

MMAL_PARAM_REDEYE_T = ct.c_uint32 # enum
(
    MMAL_PARAM_REDEYE_OFF,
    MMAL_PARAM_REDEYE_ON,
    MMAL_PARAM_REDEYE_SIMPLE,
) = range(3)
MMAL_PARAM_REDEYE_MAX = 0x7FFFFFFF

class MMAL_PARAMETER_REDEYE_T(ct.Structure):
    _fields_ = [
        ('hdr', MMAL_PARAMETER_HEADER_T),
        ('value', MMAL_PARAM_REDEYE_T),
        ]

MMAL_PARAM_FOCUS_T = ct.c_uint32 # enum
(
    MMAL_PARAM_FOCUS_AUTO,
    MMAL_PARAM_FOCUS_AUTO_NEAR,
    MMAL_PARAM_FOCUS_AUTO_MACRO,
    MMAL_PARAM_FOCUS_CAF,
    MMAL_PARAM_FOCUS_CAF_NEAR,
    MMAL_PARAM_FOCUS_FIXED_INFINITY,
    MMAL_PARAM_FOCUS_FIXED_HYPERFOCAL,
    MMAL_PARAM_FOCUS_FIXED_NEAR,
    MMAL_PARAM_FOCUS_FIXED_MACRO,
    MMAL_PARAM_FOCUS_EDOF,
    MMAL_PARAM_FOCUS_CAF_MACRO,
    MMAL_PARAM_FOCUS_CAF_FAST,
    MMAL_PARAM_FOCUS_CAF_NEAR_FAST,
    MMAL_PARAM_FOCUS_CAF_MACRO_FAST,
    MMAL_PARAM_FOCUS_FIXED_CURRENT,
) = range(15)
MMAL_PARAM_FOCUS_MAX = 0x7FFFFFFF

class MMAL_PARAMETER_FOCUS_T(ct.Structure):
    _fields_ = [
        ('hdr',   MMAL_PARAMETER_HEADER_T),
        ('value', MMAL_PARAM_FOCUS_T),
        ]

MMAL_PARAM_CAPTURE_STATUS_T = ct.c_uint32 # enum
(
    MMAL_PARAM_CAPTURE_STATUS_NOT_CAPTURING,
    MMAL_PARAM_CAPTURE_STATUS_CAPTURE_STARTED,
    MMAL_PARAM_CAPTURE_STATUS_CAPTURE_ENDED,
) = range(3)
MMAL_PARAM_CAPTURE_STATUS_MAX = 0x7FFFFFFF

class MMAL_PARAMETER_CAPTURE_STATUS_T(ct.Structure):
    _fields_ = [
        ('hdr',    MMAL_PARAMETER_HEADER_T),
        ('status', MMAL_PARAM_CAPTURE_STATUS_T),
        ]

MMAL_PARAM_FOCUS_STATUS_T = ct.c_uint32 # enum
(
    MMAL_PARAM_FOCUS_STATUS_OFF,
    MMAL_PARAM_FOCUS_STATUS_REQUEST,
    MMAL_PARAM_FOCUS_STATUS_REACHED,
    MMAL_PARAM_FOCUS_STATUS_UNABLE_TO_REACH,
    MMAL_PARAM_FOCUS_STATUS_LOST,
    MMAL_PARAM_FOCUS_STATUS_CAF_MOVING,
    MMAL_PARAM_FOCUS_STATUS_CAF_SUCCESS,
    MMAL_PARAM_FOCUS_STATUS_CAF_FAILED,
    MMAL_PARAM_FOCUS_STATUS_MANUAL_MOVING,
    MMAL_PARAM_FOCUS_STATUS_MANUAL_REACHED,
    MMAL_PARAM_FOCUS_STATUS_CAF_WATCHING,
    MMAL_PARAM_FOCUS_STATUS_CAF_SCENE_CHANGED,
) = range(12)
MMAL_PARAM_FOCUS_STATUS_MAX = 0x7FFFFFFF

class MMAL_PARAMETER_FOCUS_STATUS_T(ct.Structure):
    _fields_ = [
        ('hdr',    MMAL_PARAMETER_HEADER_T),
        ('status', MMAL_PARAM_FOCUS_STATUS_T),
        ]

MMAL_PARAM_FACE_TRACK_MODE_T = ct.c_uint32 # enum
(
    MMAL_PARAM_FACE_DETECT_NONE,
    MMAL_PARAM_FACE_DETECT_ON,
) = range(2)
MMAL_PARAM_FACE_DETECT_MAX = 0x7FFFFFFF

class MMAL_PARAMETER_FACE_TRACK_T(ct.Structure):
    _fields_ = [
        ('hdr',        MMAL_PARAMETER_HEADER_T),
        ('mode',       MMAL_PARAM_FACE_TRACK_MODE_T),
        ('maxRegions', ct.c_uint32),
        ('frames',     ct.c_uint32),
        ('quality',    ct.c_uint32),
        ]

class MMAL_PARAMETER_FACE_TRACK_FACE_T(ct.Structure):
    _fields_ = [
        ('face_id',    ct.c_int32),
        ('score',      ct.c_int32),
        ('face_rect',  MMAL_RECT_T),
        ('eye_rect',   MMAL_RECT_T * 2),
        ('mouth_rect', MMAL_RECT_T),
        ]

class MMAL_PARAMETER_FACE_TRACK_RESULTS_T(ct.Structure):
    _fields_ = [
        ('hdr',          MMAL_PARAMETER_HEADER_T),
        ('num_faces',    ct.c_uint32),
        ('frame_width',  ct.c_uint32),
        ('frame_height', ct.c_uint32),
        ('faces',        MMAL_PARAMETER_FACE_TRACK_FACE_T * 1),
        ]

MMAL_PARAMETER_CAMERA_CONFIG_TIMESTAMP_MODE_T = ct.c_uint32 # enum
(
    MMAL_PARAM_TIMESTAMP_MODE_ZERO,
    MMAL_PARAM_TIMESTAMP_MODE_RAW_STC,
    MMAL_PARAM_TIMESTAMP_MODE_RESET_STC,
) = range(3)
MMAL_PARAM_TIMESTAMP_MODE_MAX = 0x7FFFFFFF

class MMAL_PARAMETER_CAMERA_CONFIG_T(ct.Structure):
    _fields_ = [
        ('hdr',                                   MMAL_PARAMETER_HEADER_T),
        ('max_stills_w',                          ct.c_uint32),
        ('max_stills_h',                          ct.c_uint32),
        ('stills_yuv422',                         ct.c_uint32),
        ('one_shot_stills',                       ct.c_uint32),
        ('max_preview_video_w',                   ct.c_uint32),
        ('max_preview_video_h',                   ct.c_uint32),
        ('num_preview_video_frames',              ct.c_uint32),
        ('stills_capture_circular_buffer_height', ct.c_uint32),
        ('fast_preview_resume',                   ct.c_uint32),
        ('use_stc_timestamp',                     MMAL_PARAMETER_CAMERA_CONFIG_TIMESTAMP_MODE_T),
        ]

MMAL_PARAMETER_CAMERA_INFO_MAX_CAMERAS = 4
MMAL_PARAMETER_CAMERA_INFO_MAX_FLASHES = 2
MMAL_PARAMETER_CAMERA_INFO_MAX_STR_LEN = 16

class MMAL_PARAMETER_CAMERA_INFO_CAMERA_T(ct.Structure):
    _fields_ = [
        ('port_id',      ct.c_uint32),
        ('max_width',    ct.c_uint32),
        ('max_height',   ct.c_uint32),
        ('lens_present', MMAL_BOOL_T),
        ]

class MMAL_PARAMETER_CAMERA_INFO_CAMERA_V2_T(ct.Structure):
    _fields_ = [
        ('port_id',      ct.c_uint32),
        ('max_width',    ct.c_uint32),
        ('max_height',   ct.c_uint32),
        ('lens_present', MMAL_BOOL_T),
        ('camera_name',  ct.c_char * MMAL_PARAMETER_CAMERA_INFO_MAX_STR_LEN),
        ]

MMAL_PARAMETER_CAMERA_INFO_FLASH_TYPE_T = ct.c_uint32 # enum
MMAL_PARAMETER_CAMERA_INFO_FLASH_TYPE_XENON = 0
MMAL_PARAMETER_CAMERA_INFO_FLASH_TYPE_LED   = 1
MMAL_PARAMETER_CAMERA_INFO_FLASH_TYPE_OTHER = 2
MMAL_PARAMETER_CAMERA_INFO_FLASH_TYPE_MAX = 0x7FFFFFFF

class MMAL_PARAMETER_CAMERA_INFO_FLASH_T(ct.Structure):
    _fields_ = [
        ('flash_type', MMAL_PARAMETER_CAMERA_INFO_FLASH_TYPE_T),
        ]

class MMAL_PARAMETER_CAMERA_INFO_T(ct.Structure):
    _fields_ = [
        ('hdr',         MMAL_PARAMETER_HEADER_T),
        ('num_cameras', ct.c_uint32),
        ('num_flashes', ct.c_uint32),
        ('cameras',     MMAL_PARAMETER_CAMERA_INFO_CAMERA_T * MMAL_PARAMETER_CAMERA_INFO_MAX_CAMERAS),
        ('flashes',     MMAL_PARAMETER_CAMERA_INFO_FLASH_T * MMAL_PARAMETER_CAMERA_INFO_MAX_FLASHES),
        ]

class MMAL_PARAMETER_CAMERA_INFO_V2_T(ct.Structure):
    _fields_ = [
        ('hdr',         MMAL_PARAMETER_HEADER_T),
        ('num_cameras', ct.c_uint32),
        ('num_flashes', ct.c_uint32),
        ('cameras',     MMAL_PARAMETER_CAMERA_INFO_CAMERA_V2_T * MMAL_PARAMETER_CAMERA_INFO_MAX_CAMERAS),
        ('flashes',     MMAL_PARAMETER_CAMERA_INFO_FLASH_T * MMAL_PARAMETER_CAMERA_INFO_MAX_FLASHES),
        ]

MMAL_PARAMETER_CAPTUREMODE_MODE_T = ct.c_uint32 # enum
(
    MMAL_PARAM_CAPTUREMODE_WAIT_FOR_END,
    MMAL_PARAM_CAPTUREMODE_WAIT_FOR_END_AND_HOLD,
    MMAL_PARAM_CAPTUREMODE_RESUME_VF_IMMEDIATELY,
) = range(3)

class MMAL_PARAMETER_CAPTUREMODE_T(ct.Structure):
    _fields_ = [
        ('hdr',  MMAL_PARAMETER_HEADER_T),
        ('mode', MMAL_PARAMETER_CAPTUREMODE_MODE_T),
        ]

MMAL_PARAMETER_FOCUS_REGION_TYPE_T = ct.c_uint32 # enum
(
    MMAL_PARAMETER_FOCUS_REGION_TYPE_NORMAL,
    MMAL_PARAMETER_FOCUS_REGION_TYPE_FACE,
    MMAL_PARAMETER_FOCUS_REGION_TYPE_MAX,
) = range(3)

class MMAL_PARAMETER_FOCUS_REGION_T(ct.Structure):
    _fields_ = [
        ('rect',   MMAL_RECT_T),
        ('weight', ct.c_uint32),
        ('mask',   ct.c_uint32),
        ('type',   MMAL_PARAMETER_FOCUS_REGION_TYPE_T),
        ]

class MMAL_PARAMETER_FOCUS_REGIONS_T(ct.Structure):
    _fields_ = [
        ('hdr',           MMAL_PARAMETER_HEADER_T),
        ('num_regions',   ct.c_uint32),
        ('lock_to_faces', MMAL_BOOL_T),
        ('regions',       MMAL_PARAMETER_FOCUS_REGION_T * 1),
        ]

class MMAL_PARAMETER_INPUT_CROP_T(ct.Structure):
    _fields_ = [
        ('hdr',  MMAL_PARAMETER_HEADER_T),
        ('rect', MMAL_RECT_T),
        ]

class MMAL_PARAMETER_SENSOR_INFORMATION_T(ct.Structure):
    _fields_ = [
        ('hdr',             MMAL_PARAMETER_HEADER_T),
        ('f_number',        MMAL_RATIONAL_T),
        ('focal_length',    MMAL_RATIONAL_T),
        ('model_id',        ct.c_uint32),
        ('manufacturer_id', ct.c_uint32),
        ('revision',        ct.c_uint32),
        ]

class MMAL_PARAMETER_FLASH_SELECT_T(ct.Structure):
    _fields_ = [
        ('hdr',        MMAL_PARAMETER_HEADER_T),
        ('flash_type', MMAL_PARAMETER_CAMERA_INFO_FLASH_TYPE_T),
        ]

class MMAL_PARAMETER_FIELD_OF_VIEW_T(ct.Structure):
    _fields_ = [
        ('hdr',   MMAL_PARAMETER_HEADER_T),
        ('fov_h', MMAL_RATIONAL_T),
        ('fov_v', MMAL_RATIONAL_T),
        ]

MMAL_PARAMETER_DRC_STRENGTH_T = ct.c_uint32 # enum
(
    MMAL_PARAMETER_DRC_STRENGTH_OFF,
    MMAL_PARAMETER_DRC_STRENGTH_LOW,
    MMAL_PARAMETER_DRC_STRENGTH_MEDIUM,
    MMAL_PARAMETER_DRC_STRENGTH_HIGH,
) = range(4)
MMAL_PARAMETER_DRC_STRENGTH_MAX = 0x7fffffff

class MMAL_PARAMETER_DRC_T(ct.Structure):
    _fields_ = [
        ('hdr',      MMAL_PARAMETER_HEADER_T),
        ('strength', MMAL_PARAMETER_DRC_STRENGTH_T),
        ]

MMAL_PARAMETER_ALGORITHM_CONTROL_ALGORITHMS_T = ct.c_uint32 # enum
(
    MMAL_PARAMETER_ALGORITHM_CONTROL_ALGORITHMS_FACETRACKING,
    MMAL_PARAMETER_ALGORITHM_CONTROL_ALGORITHMS_REDEYE_REDUCTION,
    MMAL_PARAMETER_ALGORITHM_CONTROL_ALGORITHMS_VIDEO_STABILISATION,
    MMAL_PARAMETER_ALGORITHM_CONTROL_ALGORITHMS_WRITE_RAW,
    MMAL_PARAMETER_ALGORITHM_CONTROL_ALGORITHMS_VIDEO_DENOISE,
    MMAL_PARAMETER_ALGORITHM_CONTROL_ALGORITHMS_STILLS_DENOISE,
    MMAL_PARAMETER_ALGORITHM_CONTROL_ALGORITHMS_TEMPORAL_DENOISE,
    MMAL_PARAMETER_ALGORITHM_CONTROL_ALGORITHMS_ANTISHAKE,
    MMAL_PARAMETER_ALGORITHM_CONTROL_ALGORITHMS_IMAGE_EFFECTS,
    MMAL_PARAMETER_ALGORITHM_CONTROL_ALGORITHMS_DYNAMIC_RANGE_COMPRESSION,
    MMAL_PARAMETER_ALGORITHM_CONTROL_ALGORITHMS_FACE_RECOGNITION,
    MMAL_PARAMETER_ALGORITHM_CONTROL_ALGORITHMS_FACE_BEAUTIFICATION,
    MMAL_PARAMETER_ALGORITHM_CONTROL_ALGORITHMS_SCENE_DETECTION,
    MMAL_PARAMETER_ALGORITHM_CONTROL_ALGORITHMS_HIGH_DYNAMIC_RANGE,
) = range(14)
MMAL_PARAMETER_ALGORITHM_CONTROL_ALGORITHMS_MAX = 0x7fffffff

class MMAL_PARAMETER_ALGORITHM_CONTROL_T(ct.Structure):
    _fields_ = [
        ('hdr',       MMAL_PARAMETER_HEADER_T),
        ('algorithm', MMAL_PARAMETER_ALGORITHM_CONTROL_ALGORITHMS_T),
        ('enabled',   MMAL_BOOL_T),
        ]

MMAL_PARAM_CAMERA_USE_CASE_T = ct.c_uint32 # enum
(
   MMAL_PARAM_CAMERA_USE_CASE_UNKNOWN,
   MMAL_PARAM_CAMERA_USE_CASE_STILLS_CAPTURE,
   MMAL_PARAM_CAMERA_USE_CASE_VIDEO_CAPTURE,
) = range(3)
MMAL_PARAM_CAMERA_USE_CASE_MAX = 0x7fffffff

class MMAL_PARAMETER_CAMERA_USE_CASE_T(ct.Structure):
    _fields_ = [
        ('hdr',      MMAL_PARAMETER_HEADER_T),
        ('use_case', MMAL_PARAM_CAMERA_USE_CASE_T),
        ]

class MMAL_PARAMETER_FPS_RANGE_T(ct.Structure):
    _fields_ = [
        ('hdr',      MMAL_PARAMETER_HEADER_T),
        ('fps_low',  MMAL_RATIONAL_T),
        ('fps_high', MMAL_RATIONAL_T),
        ]

class MMAL_PARAMETER_ZEROSHUTTERLAG_T(ct.Structure):
    _fields_ = [
        ('hdr',                   MMAL_PARAMETER_HEADER_T),
        ('zero_shutter_lag_mode', MMAL_BOOL_T),
        ('concurrent_capture',    MMAL_BOOL_T),
        ]

class MMAL_PARAMETER_AWB_GAINS_T(ct.Structure):
    _fields_ = [
        ('hdr',    MMAL_PARAMETER_HEADER_T),
        ('r_gain', MMAL_RATIONAL_T),
        ('b_gain', MMAL_RATIONAL_T),
        ]

class MMAL_PARAMETER_CAMERA_SETTINGS_T(ct.Structure):
    _fields_ = [
        ('hdr',            MMAL_PARAMETER_HEADER_T),
        ('exposure',       ct.c_uint32),
        ('analog_gain',    MMAL_RATIONAL_T),
        ('digital_gain',   MMAL_RATIONAL_T),
        ('awb_red_gain',   MMAL_RATIONAL_T),
        ('awb_blue_gain',  MMAL_RATIONAL_T),
        ('focus_position', ct.c_uint32),
        ]

MMAL_PARAM_PRIVACY_INDICATOR_T = ct.c_uint32 # enum
(
    MMAL_PARAMETER_PRIVACY_INDICATOR_OFF,
    MMAL_PARAMETER_PRIVACY_INDICATOR_ON,
    MMAL_PARAMETER_PRIVACY_INDICATOR_FORCE_ON,
) = range(3)
MMAL_PARAMETER_PRIVACY_INDICATOR_MAX = 0x7fffffff

class MMAL_PARAMETER_PRIVACY_INDICATOR_T(ct.Structure):
    _fields_ = [
        ('hdr',           MMAL_PARAMETER_HEADER_T),
        ('mode',          MMAL_PARAM_PRIVACY_INDICATOR_T),
        ]

MMAL_CAMERA_ANNOTATE_MAX_TEXT_LEN = 32

class MMAL_PARAMETER_CAMERA_ANNOTATE_T(ct.Structure):
    _fields_ = [
        ('hdr',              MMAL_PARAMETER_HEADER_T),
        ('enable',           MMAL_BOOL_T),
        ('text',             ct.c_char * MMAL_CAMERA_ANNOTATE_MAX_TEXT_LEN),
        ('show_shutter',     MMAL_BOOL_T),
        ('show_analog_gain', MMAL_BOOL_T),
        ('show_lens',        MMAL_BOOL_T),
        ('show_caf',         MMAL_BOOL_T),
        ('show_motion',      MMAL_BOOL_T),
        ]

MMAL_CAMERA_ANNOTATE_MAX_TEXT_LEN_V2 = 256

class MMAL_PARAMETER_CAMERA_ANNOTATE_V2_T(ct.Structure):
    _fields_ = [
        ('hdr',                   MMAL_PARAMETER_HEADER_T),
        ('enable',                MMAL_BOOL_T),
        ('show_shutter',          MMAL_BOOL_T),
        ('show_analog_gain',      MMAL_BOOL_T),
        ('show_lens',             MMAL_BOOL_T),
        ('show_caf',              MMAL_BOOL_T),
        ('show_motion',           MMAL_BOOL_T),
        ('show_frame_num',        MMAL_BOOL_T),
        ('black_text_background', MMAL_BOOL_T),
        ('text',                  ct.c_char * MMAL_CAMERA_ANNOTATE_MAX_TEXT_LEN_V2),
        ]

MMAL_CAMERA_ANNOTATE_MAX_TEXT_LEN_V3 = 256

class MMAL_PARAMETER_CAMERA_ANNOTATE_V3_T(ct.Structure):
    _fields_ = [
        ('hdr',                     MMAL_PARAMETER_HEADER_T),
        ('enable',                  MMAL_BOOL_T),
        ('show_shutter',            MMAL_BOOL_T),
        ('show_analog_gain',        MMAL_BOOL_T),
        ('show_lens',               MMAL_BOOL_T),
        ('show_caf',                MMAL_BOOL_T),
        ('show_motion',             MMAL_BOOL_T),
        ('show_frame_num',          MMAL_BOOL_T),
        ('enable_text_background',  MMAL_BOOL_T),
        ('custom_background_color', MMAL_BOOL_T),
        ('custom_background_Y',     ct.c_uint8),
        ('custom_background_U',     ct.c_uint8),
        ('custom_background_V',     ct.c_uint8),
        ('dummy1',                  ct.c_uint8),
        ('custom_text_color',       MMAL_BOOL_T),
        ('custom_text_Y',           ct.c_uint8),
        ('custom_text_U',           ct.c_uint8),
        ('custom_text_V',           ct.c_uint8),
        ('text_size',               ct.c_uint8),
        ('text',                    ct.c_char * MMAL_CAMERA_ANNOTATE_MAX_TEXT_LEN_V3),
        ]

MMAL_STEREOSCOPIC_MODE_T = ct.c_uint32 # enum
(
    MMAL_STEREOSCOPIC_MODE_NONE,
    MMAL_STEREOSCOPIC_MODE_SIDE_BY_SIDE,
    MMAL_STEREOSCOPIC_MODE_BOTTOM,
) = range(3)
MMAL_STEREOSCOPIC_MODE_MAX = 0x7fffffff

class MMAL_PARAMETER_STEREOSCOPIC_MODE_T(ct.Structure):
    _fields_ = [
        ('hdr',        MMAL_PARAMETER_HEADER_T),
        ('mode',       MMAL_STEREOSCOPIC_MODE_T),
        ('decimate',   MMAL_BOOL_T),
        ('swap_eyes',  MMAL_BOOL_T),
        ]

MMAL_CAMERA_INTERFACE_T = ct.c_uint32 # enum
(
    MMAL_CAMERA_INTERFACE_CSI2,
    MMAL_CAMERA_INTERFACE_CCP2,
    MMAL_CAMERA_INTERFACE_CPI,
) = range(3)
MMAL_CAMERA_INTERFACE_MAX = 0x7fffffff

class MMAL_PARAMETER_CAMERA_INTERFACE_T(ct.Structure):
    _fields_ = [
        ('hdr',       MMAL_PARAMETER_HEADER_T),
        ('mode',      MMAL_CAMERA_INTERFACE_T),
        ]

MMAL_CAMERA_CLOCKING_MODE_T = ct.c_uint32 # enum
(
    MMAL_CAMERA_CLOCKING_MODE_STROBE,
    MMAL_CAMERA_CLOCKING_MODE_CLOCK,
) = range(2)
MMAL_CAMERA_CLOCKING_MODE_MAX = 0x7fffffff

class MMAL_PARAMETER_CAMERA_CLOCKING_MODE_T(ct.Structure):
    _fields_ = [
        ('hdr',       MMAL_PARAMETER_HEADER_T),
        ('mode',      MMAL_CAMERA_CLOCKING_MODE_T),
        ]

MMAL_CAMERA_RX_CONFIG_DECODE = ct.c_uint32 # enum
(
   MMAL_CAMERA_RX_CONFIG_DECODE_NONE,
   MMAL_CAMERA_RX_CONFIG_DECODE_DPCM8TO10,
   MMAL_CAMERA_RX_CONFIG_DECODE_DPCM7TO10,
   MMAL_CAMERA_RX_CONFIG_DECODE_DPCM6TO10,
   MMAL_CAMERA_RX_CONFIG_DECODE_DPCM8TO12,
   MMAL_CAMERA_RX_CONFIG_DECODE_DPCM7TO12,
   MMAL_CAMERA_RX_CONFIG_DECODE_DPCM6TO12,
   MMAL_CAMERA_RX_CONFIG_DECODE_DPCM10TO14,
   MMAL_CAMERA_RX_CONFIG_DECODE_DPCM8TO14,
   MMAL_CAMERA_RX_CONFIG_DECODE_DPCM12TO16,
   MMAL_CAMERA_RX_CONFIG_DECODE_DPCM10TO16,
   MMAL_CAMERA_RX_CONFIG_DECODE_DPCM8TO16,
) = range(12)
MMAL_CAMERA_RX_CONFIG_DECODE_MAX = 0x7fffffff

MMAL_CAMERA_RX_CONFIG_ENCODE = ct.c_uint32 # enum
(
   MMAL_CAMERA_RX_CONFIG_ENCODE_NONE,
   MMAL_CAMERA_RX_CONFIG_ENCODE_DPCM10TO8,
   MMAL_CAMERA_RX_CONFIG_ENCODE_DPCM12TO8,
   MMAL_CAMERA_RX_CONFIG_ENCODE_DPCM14TO8,
) = range(4)
MMAL_CAMERA_RX_CONFIG_ENCODE_MAX = 0x7fffffff

MMAL_CAMERA_RX_CONFIG_UNPACK = ct.c_uint32 # enum
(
   MMAL_CAMERA_RX_CONFIG_UNPACK_NONE,
   MMAL_CAMERA_RX_CONFIG_UNPACK_6,
   MMAL_CAMERA_RX_CONFIG_UNPACK_7,
   MMAL_CAMERA_RX_CONFIG_UNPACK_8,
   MMAL_CAMERA_RX_CONFIG_UNPACK_10,
   MMAL_CAMERA_RX_CONFIG_UNPACK_12,
   MMAL_CAMERA_RX_CONFIG_UNPACK_14,
   MMAL_CAMERA_RX_CONFIG_UNPACK_16,
) = range(8)
MMAL_CAMERA_RX_CONFIG_UNPACK_MAX = 0x7fffffff

MMAL_CAMERA_RX_CONFIG_PACK = ct.c_uint32 # enum
(
   MMAL_CAMERA_RX_CONFIG_PACK_NONE,
   MMAL_CAMERA_RX_CONFIG_PACK_8,
   MMAL_CAMERA_RX_CONFIG_PACK_10,
   MMAL_CAMERA_RX_CONFIG_PACK_12,
   MMAL_CAMERA_RX_CONFIG_PACK_14,
   MMAL_CAMERA_RX_CONFIG_PACK_16,
   MMAL_CAMERA_RX_CONFIG_PACK_RAW10,
   MMAL_CAMERA_RX_CONFIG_PACK_RAW12,
) = range(8)
MMAL_CAMERA_RX_CONFIG_PACK_MAX = 0x7fffffff

class MMAL_PARAMETER_CAMERA_RX_CONFIG_T(ct.Structure):
    _fields_ = [
        ('hdr',                 MMAL_PARAMETER_HEADER_T),
        ('decode',              MMAL_CAMERA_RX_CONFIG_DECODE),
        ('encode',              MMAL_CAMERA_RX_CONFIG_ENCODE),
        ('unpack',              MMAL_CAMERA_RX_CONFIG_UNPACK),
        ('pack',                MMAL_CAMERA_RX_CONFIG_PACK),
        ('data_lanes',          ct.c_uint32),
        ('encode_block_length', ct.c_uint32),
        ('embedded_data_lines', ct.c_uint32),
        ('image_id',            ct.c_uint32),
        ]

class MMAL_PARAMETER_CAMERA_RX_TIMING_T(ct.Structure):
    _fields_ = [
        ('hdr',                 MMAL_PARAMETER_HEADER_T),
        ('timing1',             ct.c_uint32),
        ('timing2',             ct.c_uint32),
        ('timing3',             ct.c_uint32),
        ('timing4',             ct.c_uint32),
        ('timing5',             ct.c_uint32),
        ('term1',               ct.c_uint32),
        ('term2',               ct.c_uint32),
        ('cpi_timing1',         ct.c_uint32),
        ('cpi_timing2',         ct.c_uint32),
        ]

# mmal_parameters_video.h ####################################################

(
   MMAL_PARAMETER_DISPLAYREGION,
   MMAL_PARAMETER_SUPPORTED_PROFILES,
   MMAL_PARAMETER_PROFILE,
   MMAL_PARAMETER_INTRAPERIOD,
   MMAL_PARAMETER_RATECONTROL,
   MMAL_PARAMETER_NALUNITFORMAT,
   MMAL_PARAMETER_MINIMISE_FRAGMENTATION,
   MMAL_PARAMETER_MB_ROWS_PER_SLICE,
   MMAL_PARAMETER_VIDEO_LEVEL_EXTENSION,
   MMAL_PARAMETER_VIDEO_EEDE_ENABLE,
   MMAL_PARAMETER_VIDEO_EEDE_LOSSRATE,
   MMAL_PARAMETER_VIDEO_REQUEST_I_FRAME,
   MMAL_PARAMETER_VIDEO_INTRA_REFRESH,
   MMAL_PARAMETER_VIDEO_IMMUTABLE_INPUT,
   MMAL_PARAMETER_VIDEO_BIT_RATE,
   MMAL_PARAMETER_VIDEO_FRAME_RATE,
   MMAL_PARAMETER_VIDEO_ENCODE_MIN_QUANT,
   MMAL_PARAMETER_VIDEO_ENCODE_MAX_QUANT,
   MMAL_PARAMETER_VIDEO_ENCODE_RC_MODEL,
   MMAL_PARAMETER_EXTRA_BUFFERS,
   MMAL_PARAMETER_VIDEO_ALIGN_HORIZ,
   MMAL_PARAMETER_VIDEO_ALIGN_VERT,
   MMAL_PARAMETER_VIDEO_DROPPABLE_PFRAMES,
   MMAL_PARAMETER_VIDEO_ENCODE_INITIAL_QUANT,
   MMAL_PARAMETER_VIDEO_ENCODE_QP_P,
   MMAL_PARAMETER_VIDEO_ENCODE_RC_SLICE_DQUANT,
   MMAL_PARAMETER_VIDEO_ENCODE_FRAME_LIMIT_BITS,
   MMAL_PARAMETER_VIDEO_ENCODE_PEAK_RATE,
   MMAL_PARAMETER_VIDEO_ENCODE_H264_DISABLE_CABAC,
   MMAL_PARAMETER_VIDEO_ENCODE_H264_LOW_LATENCY,
   MMAL_PARAMETER_VIDEO_ENCODE_H264_AU_DELIMITERS,
   MMAL_PARAMETER_VIDEO_ENCODE_H264_DEBLOCK_IDC,
   MMAL_PARAMETER_VIDEO_ENCODE_H264_MB_INTRA_MODE,
   MMAL_PARAMETER_VIDEO_ENCODE_HEADER_ON_OPEN,
   MMAL_PARAMETER_VIDEO_ENCODE_PRECODE_FOR_QP,
   MMAL_PARAMETER_VIDEO_DRM_INIT_INFO,
   MMAL_PARAMETER_VIDEO_TIMESTAMP_FIFO,
   MMAL_PARAMETER_VIDEO_DECODE_ERROR_CONCEALMENT,
   MMAL_PARAMETER_VIDEO_DRM_PROTECT_BUFFER,
   MMAL_PARAMETER_VIDEO_DECODE_CONFIG_VD3,
   MMAL_PARAMETER_VIDEO_ENCODE_H264_VCL_HRD_PARAMETERS,
   MMAL_PARAMETER_VIDEO_ENCODE_H264_LOW_DELAY_HRD_FLAG,
   MMAL_PARAMETER_VIDEO_ENCODE_INLINE_HEADER,
   MMAL_PARAMETER_VIDEO_ENCODE_SEI_ENABLE,
   MMAL_PARAMETER_VIDEO_ENCODE_INLINE_VECTORS,
   MMAL_PARAMETER_VIDEO_RENDER_STATS,
   MMAL_PARAMETER_VIDEO_INTERLACE_TYPE,
   MMAL_PARAMETER_VIDEO_INTERPOLATE_TIMESTAMPS,
   MMAL_PARAMETER_VIDEO_ENCODE_SPS_TIMING,
   MMAL_PARAMETER_VIDEO_MAX_NUM_CALLBACKS,
) = range(MMAL_PARAMETER_GROUP_VIDEO, MMAL_PARAMETER_GROUP_VIDEO + 50)

MMAL_DISPLAYTRANSFORM_T  = ct.c_uint32 # enum
MMAL_DISPLAY_ROT0 = 0
MMAL_DISPLAY_MIRROR_ROT0 = 1
MMAL_DISPLAY_MIRROR_ROT180 = 2
MMAL_DISPLAY_ROT180 = 3
MMAL_DISPLAY_MIRROR_ROT90 = 4
MMAL_DISPLAY_ROT270 = 5
MMAL_DISPLAY_ROT90 = 6
MMAL_DISPLAY_MIRROR_ROT270 = 7
MMAL_DISPLAY_DUMMY = 0x7FFFFFFF

MMAL_DISPLAYMODE_T = ct.c_uint32 # enum
MMAL_DISPLAY_MODE_FILL = 0
MMAL_DISPLAY_MODE_LETTERBOX = 1
MMAL_DISPLAY_MODE_DUMMY = 0x7FFFFFFF

MMAL_DISPLAYSET_T = ct.c_uint32 # enum
MMAL_DISPLAY_SET_NONE = 0
MMAL_DISPLAY_SET_NUM = 1
MMAL_DISPLAY_SET_FULLSCREEN = 2
MMAL_DISPLAY_SET_TRANSFORM = 4
MMAL_DISPLAY_SET_DEST_RECT = 8
MMAL_DISPLAY_SET_SRC_RECT = 0x10
MMAL_DISPLAY_SET_MODE = 0x20
MMAL_DISPLAY_SET_PIXEL = 0x40
MMAL_DISPLAY_SET_NOASPECT = 0x80
MMAL_DISPLAY_SET_LAYER = 0x100
MMAL_DISPLAY_SET_COPYPROTECT = 0x200
MMAL_DISPLAY_SET_ALPHA = 0x400
MMAL_DISPLAY_SET_DUMMY = 0x7FFFFFFF

class MMAL_DISPLAYREGION_T(ct.Structure):
    _fields_ = [
        ('hdr',                  MMAL_PARAMETER_HEADER_T),
        ('set',                  ct.c_uint32),
        ('display_num',          ct.c_uint32),
        ('fullscreen',           MMAL_BOOL_T),
        ('transform',            MMAL_DISPLAYTRANSFORM_T),
        ('dest_rect',            MMAL_RECT_T),
        ('src_rect',             MMAL_RECT_T),
        ('noaspect',             MMAL_BOOL_T),
        ('mode',                 MMAL_DISPLAYMODE_T),
        ('pixel_x',              ct.c_uint32),
        ('pixel_y',              ct.c_uint32),
        ('layer',                ct.c_int32),
        ('copyprotect_required', MMAL_BOOL_T),
        ('alpha',                ct.c_uint32),
        ]

MMAL_VIDEO_PROFILE_T = ct.c_uint32 # enum
(
    MMAL_VIDEO_PROFILE_H263_BASELINE,
    MMAL_VIDEO_PROFILE_H263_H320CODING,
    MMAL_VIDEO_PROFILE_H263_BACKWARDCOMPATIBLE,
    MMAL_VIDEO_PROFILE_H263_ISWV2,
    MMAL_VIDEO_PROFILE_H263_ISWV3,
    MMAL_VIDEO_PROFILE_H263_HIGHCOMPRESSION,
    MMAL_VIDEO_PROFILE_H263_INTERNET,
    MMAL_VIDEO_PROFILE_H263_INTERLACE,
    MMAL_VIDEO_PROFILE_H263_HIGHLATENCY,
    MMAL_VIDEO_PROFILE_MP4V_SIMPLE,
    MMAL_VIDEO_PROFILE_MP4V_SIMPLESCALABLE,
    MMAL_VIDEO_PROFILE_MP4V_CORE,
    MMAL_VIDEO_PROFILE_MP4V_MAIN,
    MMAL_VIDEO_PROFILE_MP4V_NBIT,
    MMAL_VIDEO_PROFILE_MP4V_SCALABLETEXTURE,
    MMAL_VIDEO_PROFILE_MP4V_SIMPLEFACE,
    MMAL_VIDEO_PROFILE_MP4V_SIMPLEFBA,
    MMAL_VIDEO_PROFILE_MP4V_BASICANIMATED,
    MMAL_VIDEO_PROFILE_MP4V_HYBRID,
    MMAL_VIDEO_PROFILE_MP4V_ADVANCEDREALTIME,
    MMAL_VIDEO_PROFILE_MP4V_CORESCALABLE,
    MMAL_VIDEO_PROFILE_MP4V_ADVANCEDCODING,
    MMAL_VIDEO_PROFILE_MP4V_ADVANCEDCORE,
    MMAL_VIDEO_PROFILE_MP4V_ADVANCEDSCALABLE,
    MMAL_VIDEO_PROFILE_MP4V_ADVANCEDSIMPLE,
    MMAL_VIDEO_PROFILE_H264_BASELINE,
    MMAL_VIDEO_PROFILE_H264_MAIN,
    MMAL_VIDEO_PROFILE_H264_EXTENDED,
    MMAL_VIDEO_PROFILE_H264_HIGH,
    MMAL_VIDEO_PROFILE_H264_HIGH10,
    MMAL_VIDEO_PROFILE_H264_HIGH422,
    MMAL_VIDEO_PROFILE_H264_HIGH444,
    MMAL_VIDEO_PROFILE_H264_CONSTRAINED_BASELINE,
) = range(33)
MMAL_VIDEO_PROFILE_DUMMY = 0x7FFFFFFF

MMAL_VIDEO_LEVEL_T = ct.c_uint32 # enum
(
    MMAL_VIDEO_LEVEL_H263_10,
    MMAL_VIDEO_LEVEL_H263_20,
    MMAL_VIDEO_LEVEL_H263_30,
    MMAL_VIDEO_LEVEL_H263_40,
    MMAL_VIDEO_LEVEL_H263_45,
    MMAL_VIDEO_LEVEL_H263_50,
    MMAL_VIDEO_LEVEL_H263_60,
    MMAL_VIDEO_LEVEL_H263_70,
    MMAL_VIDEO_LEVEL_MP4V_0,
    MMAL_VIDEO_LEVEL_MP4V_0b,
    MMAL_VIDEO_LEVEL_MP4V_1,
    MMAL_VIDEO_LEVEL_MP4V_2,
    MMAL_VIDEO_LEVEL_MP4V_3,
    MMAL_VIDEO_LEVEL_MP4V_4,
    MMAL_VIDEO_LEVEL_MP4V_4a,
    MMAL_VIDEO_LEVEL_MP4V_5,
    MMAL_VIDEO_LEVEL_MP4V_6,
    MMAL_VIDEO_LEVEL_H264_1,
    MMAL_VIDEO_LEVEL_H264_1b,
    MMAL_VIDEO_LEVEL_H264_11,
    MMAL_VIDEO_LEVEL_H264_12,
    MMAL_VIDEO_LEVEL_H264_13,
    MMAL_VIDEO_LEVEL_H264_2,
    MMAL_VIDEO_LEVEL_H264_21,
    MMAL_VIDEO_LEVEL_H264_22,
    MMAL_VIDEO_LEVEL_H264_3,
    MMAL_VIDEO_LEVEL_H264_31,
    MMAL_VIDEO_LEVEL_H264_32,
    MMAL_VIDEO_LEVEL_H264_4,
    MMAL_VIDEO_LEVEL_H264_41,
    MMAL_VIDEO_LEVEL_H264_42,
    MMAL_VIDEO_LEVEL_H264_5,
    MMAL_VIDEO_LEVEL_H264_51,
) = range(33)
MMAL_VIDEO_LEVEL_DUMMY = 0x7FFFFFFF

class MMAL_PARAMETER_VIDEO_PROFILE_S(ct.Structure):
    _fields_ = [
        ('profile', MMAL_VIDEO_PROFILE_T),
        ('level',   MMAL_VIDEO_LEVEL_T),
        ]

class MMAL_PARAMETER_VIDEO_PROFILE_T(ct.Structure):
    _fields_ = [
        ('hdr', MMAL_PARAMETER_HEADER_T),
        ('profile', MMAL_PARAMETER_VIDEO_PROFILE_S * 1),
        ]

MMAL_VIDEO_RATECONTROL_T = ct.c_uint32 # enum
(
    MMAL_VIDEO_RATECONTROL_DEFAULT,
    MMAL_VIDEO_RATECONTROL_VARIABLE,
    MMAL_VIDEO_RATECONTROL_CONSTANT,
    MMAL_VIDEO_RATECONTROL_VARIABLE_SKIP_FRAMES,
    MMAL_VIDEO_RATECONTROL_CONSTANT_SKIP_FRAMES,
) = range(5)
MMAL_VIDEO_RATECONTROL_DUMMY = 0x7fffffff

MMAL_VIDEO_INTRA_REFRESH_T = ct.c_uint32
(
    MMAL_VIDEO_INTRA_REFRESH_CYCLIC,
    MMAL_VIDEO_INTRA_REFRESH_ADAPTIVE,
    MMAL_VIDEO_INTRA_REFRESH_BOTH,
) = range(3)
MMAL_VIDEO_INTRA_REFRESH_KHRONOSEXTENSIONS = 0x6F000000
MMAL_VIDEO_INTRA_REFRESH_VENDORSTARTUNUSED = 0x7F000000
(
    MMAL_VIDEO_INTRA_REFRESH_CYCLIC_MROWS,
    MMAL_VIDEO_INTRA_REFRESH_PSEUDO_RAND,
    MMAL_VIDEO_INTRA_REFRESH_MAX,
) = range(MMAL_VIDEO_INTRA_REFRESH_VENDORSTARTUNUSED, MMAL_VIDEO_INTRA_REFRESH_VENDORSTARTUNUSED + 3)
MMAL_VIDEO_INTRA_REFRESH_DUMMY         = 0x7FFFFFFF

MMAL_VIDEO_ENCODE_RC_MODEL_T = ct.c_uint32
MMAL_VIDEO_ENCODER_RC_MODEL_DEFAULT = 0
(
    MMAL_VIDEO_ENCODER_RC_MODEL_JVT,
    MMAL_VIDEO_ENCODER_RC_MODEL_VOWIFI,
    MMAL_VIDEO_ENCODER_RC_MODEL_CBR,
    MMAL_VIDEO_ENCODER_RC_MODEL_LAST,
) = range(MMAL_VIDEO_ENCODER_RC_MODEL_DEFAULT, MMAL_VIDEO_ENCODER_RC_MODEL_DEFAULT + 4)
MMAL_VIDEO_ENCODER_RC_MODEL_DUMMY      = 0x7FFFFFFF

class MMAL_PARAMETER_VIDEO_ENCODE_RC_MODEL_T(ct.Structure):
    _fields_ = [
        ('hdr',      MMAL_PARAMETER_HEADER_T),
        ('rc_model', MMAL_VIDEO_ENCODE_RC_MODEL_T),
        ]

class MMAL_PARAMETER_VIDEO_RATECONTROL_T(ct.Structure):
    _fields_ = [
        ('hdr',     MMAL_PARAMETER_HEADER_T),
        ('control', MMAL_VIDEO_RATECONTROL_T),
        ]

MMAL_VIDEO_ENCODE_H264_MB_INTRA_MODES_T = ct.c_uint32 # enum
MMAL_VIDEO_ENCODER_H264_MB_4x4_INTRA = 1
MMAL_VIDEO_ENCODER_H264_MB_8x8_INTRA = 2
MMAL_VIDEO_ENCODER_H264_MB_16x16_INTRA = 4
MMAL_VIDEO_ENCODER_H264_MB_INTRA_DUMMY = 0x7fffffff

class MMAL_PARAMETER_VIDEO_ENCODER_H264_MB_INTRA_MODES_T(ct.Structure):
    _fields_ = [
        ('hdr',     MMAL_PARAMETER_HEADER_T),
        ('mb_mode', MMAL_VIDEO_ENCODE_H264_MB_INTRA_MODES_T),
        ]

MMAL_VIDEO_NALUNITFORMAT_T = ct.c_uint32
MMAL_VIDEO_NALUNITFORMAT_STARTCODES = 1
MMAL_VIDEO_NALUNITFORMAT_NALUNITPERBUFFER = 2
MMAL_VIDEO_NALUNITFORMAT_ONEBYTEINTERLEAVELENGTH = 4
MMAL_VIDEO_NALUNITFORMAT_TWOBYTEINTERLEAVELENGTH = 8
MMAL_VIDEO_NALUNITFORMAT_FOURBYTEINTERLEAVELENGTH = 16
MMAL_VIDEO_NALUNITFORMAT_DUMMY = 0x7fffffff

class MMAL_PARAMETER_VIDEO_NALUNITFORMAT_T(ct.Structure):
    _fields_ = [
        ('hdr',    MMAL_PARAMETER_HEADER_T),
        ('format', MMAL_VIDEO_NALUNITFORMAT_T),
        ]

class MMAL_PARAMETER_VIDEO_LEVEL_EXTENSION_T(ct.Structure):
    _fields_ = [
        ('hdr',                   MMAL_PARAMETER_HEADER_T),
        ('custom_max_mbps',       ct.c_uint32),
        ('custom_max_fs',         ct.c_uint32),
        ('custom_max_br_and_cpb', ct.c_uint32),
        ]

class MMAL_PARAMETER_VIDEO_INTRA_REFRESH_T(ct.Structure):
    _fields_ = [
        ('hdr',          MMAL_PARAMETER_HEADER_T),
        ('refresh_mode', MMAL_VIDEO_INTRA_REFRESH_T),
        ('air_mbs',      ct.c_uint32),
        ('air_ref',      ct.c_uint32),
        ('cir_mbs',      ct.c_uint32),
        ('pir_mbs',      ct.c_uint32),
        ]

class MMAL_PARAMETER_VIDEO_EEDE_ENABLE_T(ct.Structure):
    _fields_ = [
        ('hdr',    MMAL_PARAMETER_HEADER_T),
        ('enable', ct.c_uint32),
        ]

class MMAL_PARAMETER_VIDEO_EEDE_LOSSRATE_T(ct.Structure):
    _fields_ = [
        ('hdr',       MMAL_PARAMETER_HEADER_T),
        ('loss_rate', ct.c_uint32),
        ]

class MMAL_PARAMETER_VIDEO_DRM_INIT_INFO_T(ct.Structure):
    _fields_ = [
        ('hdr',           MMAL_PARAMETER_HEADER_T),
        ('current_time',  ct.c_uint32),
        ('ticks_per_sec', ct.c_uint32),
        ('lhs',           ct.c_uint8 * 32),
        ]

class MMAL_PARAMETER_VIDEO_DRM_PROTECT_BUFFER_T(ct.Structure):
    _fields_ = [
        ('hdr',         MMAL_PARAMETER_HEADER_T),
        ('size_wanted', ct.c_uint32),
        ('protect',     ct.c_uint32),
        ('mem_handle',  ct.c_uint32),
        ('phys_addr',   ct.c_void_p),
        ]

class MMAL_PARAMETER_VIDEO_RENDER_STATS_T(ct.Structure):
    _fields_ = [
        ('hdr',                 MMAL_PARAMETER_HEADER_T),
        ('valid',               MMAL_BOOL_T),
        ('match',               ct.c_uint32),
        ('period',              ct.c_uint32),
        ('phase',               ct.c_uint32),
        ('pixel_clock_nominal', ct.c_uint32),
        ('pixel_clock',         ct.c_uint32),
        ('hvs_status',          ct.c_uint32),
        ('dummy',               ct.c_uint32 * 2),
        ]

MMAL_INTERLACE_TYPE_T = ct.c_uint32 # enum
(
    MMAL_InterlaceProgressive,
    MMAL_InterlaceFieldSingleUpperFirst,
    MMAL_InterlaceFieldSingleLowerFirst,
    MMAL_InterlaceFieldsInterleavedUpperFirst,
    MMAL_InterlaceFieldsInterleavedLowerFirst,
    MMAL_InterlaceMixed,
) = range(6)
MMAL_InterlaceKhronosExtensions = 0x6F000000
MMAL_InterlaceVendorStartUnused = 0x7F000000
MMAL_InterlaceMax = 0x7FFFFFFF

class MMAL_PARAMETER_VIDEO_INTERLACE_TYPE_T(ct.Structure):
    _fields_ = [
        ('hdr',               MMAL_PARAMETER_HEADER_T),
        ('eMode',             MMAL_INTERLACE_TYPE_T),
        ('bRepeatFirstField', MMAL_BOOL_T),
        ]

# mmal_parameters_audio.h ####################################################

(
   MMAL_PARAMETER_AUDIO_DESTINATION,
   MMAL_PARAMETER_AUDIO_LATENCY_TARGET,
   MMAL_PARAMETER_AUDIO_SOURCE,
   MMAL_PARAMETER_AUDIO_PASSTHROUGH,
) = range(MMAL_PARAMETER_GROUP_AUDIO, MMAL_PARAMETER_GROUP_AUDIO + 4)

class MMAL_PARAMETER_AUDIO_LATENCY_TARGET_T(ct.Structure):
    _fields_ = [
        ('hdr',          MMAL_PARAMETER_HEADER_T),
        ('enable',       MMAL_BOOL_T),
        ('filter',       ct.c_uint32),
        ('target',       ct.c_uint32),
        ('shift',        ct.c_uint32),
        ('speed_factor', ct.c_int32),
        ('inter_factor', ct.c_int32),
        ('adj_cap',      ct.c_int32),
        ]

# mmal_parameters_clock.h ####################################################

(
   MMAL_PARAMETER_CLOCK_REFERENCE,
   MMAL_PARAMETER_CLOCK_ACTIVE,
   MMAL_PARAMETER_CLOCK_SCALE,
   MMAL_PARAMETER_CLOCK_TIME,
   MMAL_PARAMETER_CLOCK_UPDATE_THRESHOLD,
   MMAL_PARAMETER_CLOCK_DISCONT_THRESHOLD,
   MMAL_PARAMETER_CLOCK_REQUEST_THRESHOLD,
   MMAL_PARAMETER_CLOCK_ENABLE_BUFFER_INFO,
   MMAL_PARAMETER_CLOCK_FRAME_RATE,
   MMAL_PARAMETER_CLOCK_LATENCY,
) = range(MMAL_PARAMETER_GROUP_CLOCK, MMAL_PARAMETER_GROUP_CLOCK + 10)

class MMAL_PARAMETER_CLOCK_UPDATE_THRESHOLD_T(ct.Structure):
    _fields_ = [
        ('hdr',    MMAL_PARAMETER_HEADER_T),
        ('value',  MMAL_CLOCK_UPDATE_THRESHOLD_T),
        ]

class MMAL_PARAMETER_CLOCK_DISCONT_THRESHOLD_T(ct.Structure):
    _fields_ = [
        ('hdr',    MMAL_PARAMETER_HEADER_T),
        ('value',  MMAL_CLOCK_DISCONT_THRESHOLD_T),
        ]

class MMAL_PARAMETER_CLOCK_REQUEST_THRESHOLD_T(ct.Structure):
    _fields_ = [
        ('hdr',    MMAL_PARAMETER_HEADER_T),
        ('value',  MMAL_CLOCK_REQUEST_THRESHOLD_T),
        ]

class MMAL_PARAMETER_CLOCK_LATENCY_T(ct.Structure):
    _fields_ = [
        ('hdr',    MMAL_PARAMETER_HEADER_T),
        ('value',  MMAL_CLOCK_LATENCY_T),
        ]

# mmal_parameters.h ##########################################################

class MMAL_PARAMETER_UINT64_T(ct.Structure):
    _fields_ = [
        ('hdr',   MMAL_PARAMETER_HEADER_T),
        ('value', ct.c_uint64),
        ]

class MMAL_PARAMETER_INT64_T(ct.Structure):
    _fields_ = [
        ('hdr',   MMAL_PARAMETER_HEADER_T),
        ('value', ct.c_int64),
        ]

class MMAL_PARAMETER_UINT32_T(ct.Structure):
    _fields_ = [
        ('hdr',   MMAL_PARAMETER_HEADER_T),
        ('value', ct.c_uint32),
        ]

class MMAL_PARAMETER_INT32_T(ct.Structure):
    _fields_ = [
        ('hdr',   MMAL_PARAMETER_HEADER_T),
        ('value', ct.c_int32),
        ]

class MMAL_PARAMETER_RATIONAL_T(ct.Structure):
    _fields_ = [
        ('hdr',   MMAL_PARAMETER_HEADER_T),
        ('value', MMAL_RATIONAL_T),
        ]

class MMAL_PARAMETER_BOOLEAN_T(ct.Structure):
    _fields_ = [
        ('hdr',    MMAL_PARAMETER_HEADER_T),
        ('enable', MMAL_BOOL_T),
        ]

class MMAL_PARAMETER_STRING_T(ct.Structure):
    _fields_ = [
        ('hdr', MMAL_PARAMETER_HEADER_T),
        ('str', ct.c_char_p),
        ]

class MMAL_PARAMETER_BYTES_T(ct.Structure):
    _fields_ = [
        ('hdr',  MMAL_PARAMETER_HEADER_T),
        ('data', ct.POINTER(ct.c_uint8)),
        ]

class MMAL_PARAMETER_SCALEFACTOR_T(ct.Structure):
    _fields_ = [
        ('hdr',     MMAL_PARAMETER_HEADER_T),
        ('scale_x', MMAL_FIXED_16_16_T),
        ('scale_y', MMAL_FIXED_16_16_T),
        ]

MMAL_PARAM_MIRROR_T = ct.c_uint32 # enum
(
   MMAL_PARAM_MIRROR_NONE,
   MMAL_PARAM_MIRROR_VERTICAL,
   MMAL_PARAM_MIRROR_HORIZONTAL,
   MMAL_PARAM_MIRROR_BOTH,
) = range(4)

class MMAL_PARAMETER_MIRROR_T(ct.Structure):
    _fields_ = [
        ('hdr',   MMAL_PARAMETER_HEADER_T),
        ('value', MMAL_PARAM_MIRROR_T),
        ]

class MMAL_PARAMETER_URI_T(ct.Structure):
    _fields_ = [
        ('hdr', MMAL_PARAMETER_HEADER_T),
        ('uri', ct.c_char * 200),
        ]

class MMAL_PARAMETER_ENCODING_T(ct.Structure):
    _fields_ = [
        ('hdr',      MMAL_PARAMETER_HEADER_T),
        ('encoding', ct.c_uint32 * 30),
        ]

class MMAL_PARAMETER_FRAME_RATE_T(ct.Structure):
    _fields_ = [
        ('hdr',        MMAL_PARAMETER_HEADER_T),
        ('frame_rate', MMAL_RATIONAL_T),
        ]

class MMAL_PARAMETER_CONFIGFILE_T(ct.Structure):
    _fields_ = [
        ('hdr',       MMAL_PARAMETER_HEADER_T),
        ('file_size', ct.c_uint32),
        ]

class MMAL_PARAMETER_CONFIGFILE_CHUNK_T(ct.Structure):
    _fields_ = [
        ('hdr',    MMAL_PARAMETER_HEADER_T),
        ('size',   ct.c_uint32),
        ('offset', ct.c_uint32),
        ('data',   ct.c_char_p),
        ]

# mmal_port.h ################################################################

MMAL_PORT_TYPE_T = ct.c_uint32 # enum
(
    MMAL_PORT_TYPE_UNKNOWN,
    MMAL_PORT_TYPE_CONTROL,
    MMAL_PORT_TYPE_INPUT,
    MMAL_PORT_TYPE_OUTPUT,
    MMAL_PORT_TYPE_CLOCK,
) = range(5)
MMAL_PORT_TYPE_INVALID = 0xffffffff

MMAL_PORT_CAPABILITY_PASSTHROUGH = 0x01
MMAL_PORT_CAPABILITY_ALLOCATION = 0x02
MMAL_PORT_CAPABILITY_SUPPORTS_EVENT_FORMAT_CHANGE = 0x04

class MMAL_PORT_PRIVATE_T(ct.Structure):
    _fields_ = []

class MMAL_PORT_T(ct.Structure):
    # NOTE Defined in mmal_component.h below after definition of MMAL_COMPONENT_T
    pass

mmal_port_format_commit = _lib.mmal_port_format_commit
mmal_port_format_commit.argtypes = [ct.POINTER(MMAL_PORT_T)]
mmal_port_format_commit.restype = MMAL_STATUS_T

MMAL_PORT_BH_CB_T = ct.CFUNCTYPE(
    None,
    ct.POINTER(MMAL_PORT_T), ct.POINTER(MMAL_BUFFER_HEADER_T))

mmal_port_enable = _lib.mmal_port_enable
mmal_port_enable.argtypes = [ct.POINTER(MMAL_PORT_T), MMAL_PORT_BH_CB_T]
mmal_port_enable.restype = MMAL_STATUS_T

mmal_port_disable = _lib.mmal_port_disable
mmal_port_disable.argtypes = [ct.POINTER(MMAL_PORT_T)]
mmal_port_disable.restype = MMAL_STATUS_T

mmal_port_flush = _lib.mmal_port_flush
mmal_port_flush.argtypes = [ct.POINTER(MMAL_PORT_T)]
mmal_port_flush.restype = MMAL_STATUS_T

mmal_port_parameter_set = _lib.mmal_port_parameter_set
mmal_port_parameter_set.argtypes = [ct.POINTER(MMAL_PORT_T), ct.POINTER(MMAL_PARAMETER_HEADER_T)]
mmal_port_parameter_set.restype = MMAL_STATUS_T

mmal_port_parameter_get = _lib.mmal_port_parameter_get
mmal_port_parameter_get.argtypes = [ct.POINTER(MMAL_PORT_T), ct.POINTER(MMAL_PARAMETER_HEADER_T)]
mmal_port_parameter_get.restype = MMAL_STATUS_T

mmal_port_send_buffer = _lib.mmal_port_send_buffer
mmal_port_send_buffer.argtypes = [ct.POINTER(MMAL_PORT_T), ct.POINTER(MMAL_BUFFER_HEADER_T)]
mmal_port_send_buffer.restype = MMAL_STATUS_T

mmal_port_connect = _lib.mmal_port_connect
mmal_port_connect.argtypes = [ct.POINTER(MMAL_PORT_T), ct.POINTER(MMAL_PORT_T)]
mmal_port_connect.restype = MMAL_STATUS_T

mmal_port_disconnect = _lib.mmal_port_disconnect
mmal_port_disconnect.argtypes = [ct.POINTER(MMAL_PORT_T)]
mmal_port_disconnect.restype = MMAL_STATUS_T

mmal_port_payload_alloc = _lib.mmal_port_payload_alloc
mmal_port_payload_alloc.argtypes = [ct.POINTER(MMAL_PORT_T), ct.c_uint32]
mmal_port_payload_alloc.restype = ct.POINTER(ct.c_uint8)

mmal_port_payload_free = _lib.mmal_port_payload_free
mmal_port_payload_free.argtypes = [ct.POINTER(MMAL_PORT_T), ct.POINTER(ct.c_uint8)]
mmal_port_payload_free.restype = None

mmal_port_event_get = _lib.mmal_port_event_get
mmal_port_event_get.argtypes = [ct.POINTER(MMAL_PORT_T), ct.POINTER(ct.POINTER(MMAL_BUFFER_HEADER_T)), ct.c_uint32]
mmal_port_event_get.restype = MMAL_STATUS_T

# mmal_component.h ###########################################################

class MMAL_COMPONENT_PRIVATE_T(ct.Structure):
    _fields_ = []

class MMAL_COMPONENT_T(ct.Structure):
    _fields_ = [
        ('priv',       ct.POINTER(MMAL_COMPONENT_PRIVATE_T)),
        ('userdata',   ct.c_void_p),
        ('name',       ct.c_char_p),
        ('is_enabled', ct.c_uint32),
        ('control',    ct.POINTER(MMAL_PORT_T)),
        ('input_num',  ct.c_uint32),
        ('input',      ct.POINTER(ct.POINTER(MMAL_PORT_T))),
        ('output_num', ct.c_uint32),
        ('output',     ct.POINTER(ct.POINTER(MMAL_PORT_T))),
        ('clock_num',  ct.c_uint32),
        ('clock',      ct.POINTER(ct.POINTER(MMAL_PORT_T))),
        ('port_num',   ct.c_uint32),
        ('port',       ct.POINTER(ct.POINTER(MMAL_PORT_T))),
        ('id',         ct.c_uint32),
        ]

# NOTE MMAL_PORT_T's fields are declared here as they reference
# MMAL_COMPONENT_T which in turn references MMAL_PORT_T, hence the empty
# forward decl in mmal_port.h above

MMAL_PORT_T._fields_ = [
        ('priv',                    ct.POINTER(MMAL_PORT_PRIVATE_T)),
        ('name',                    ct.c_char_p),
        ('type',                    MMAL_PORT_TYPE_T),
        ('index',                   ct.c_uint16),
        ('index_all',               ct.c_uint16),
        ('is_enabled',              ct.c_uint32),
        ('format',                  ct.POINTER(MMAL_ES_FORMAT_T)),
        ('buffer_num_min',          ct.c_uint32),
        ('buffer_size_min',         ct.c_uint32),
        ('buffer_alignment_min',    ct.c_uint32),
        ('buffer_num_recommended',  ct.c_uint32),
        ('buffer_size_recommended', ct.c_uint32),
        ('buffer_num',              ct.c_uint32),
        ('buffer_size',             ct.c_uint32),
        ('component',               ct.POINTER(MMAL_COMPONENT_T)),
        ('userdata',                ct.c_void_p),
        ('capabilities',            ct.c_uint32),
        ]

mmal_component_create = _lib.mmal_component_create
mmal_component_create.argtypes = [ct.c_char_p, ct.POINTER(ct.POINTER(MMAL_COMPONENT_T))]
mmal_component_create.restype = MMAL_STATUS_T

mmal_component_acquire = _lib.mmal_component_acquire
mmal_component_acquire.argtypes = [ct.POINTER(MMAL_COMPONENT_T)]
mmal_component_acquire.restype = None

mmal_component_release = _lib.mmal_component_release
mmal_component_release.argtypes = [ct.POINTER(MMAL_COMPONENT_T)]
mmal_component_release.restype = MMAL_STATUS_T

mmal_component_destroy = _lib.mmal_component_destroy
mmal_component_destroy.argtypes = [ct.POINTER(MMAL_COMPONENT_T)]
mmal_component_destroy.restype = MMAL_STATUS_T

mmal_component_enable = _lib.mmal_component_enable
mmal_component_enable.argtypes = [ct.POINTER(MMAL_COMPONENT_T)]
mmal_component_enable.restype = MMAL_STATUS_T

mmal_component_disable = _lib.mmal_component_disable
mmal_component_disable.argtypes = [ct.POINTER(MMAL_COMPONENT_T)]
mmal_component_disable.restype = MMAL_STATUS_T

# mmal_metadata.h ############################################################

# XXX This does not appear to be in libmmal.so...

#MMAL_METADATA_HELLO_WORLD = MMAL_FOURCC('HELO')
#
#class MMAL_METADATA_T(ct.Structure):
#    _fields_ = [
#        ('id',   ct.c_uint32),
#        ('size', ct.c_uint32),
#        ]
#
#class MMAL_METADATA_HELLO_WORLD_T(ct.Structure):
#    _fields_ = [
#        ('id',      ct.c_uint32),
#        ('size',    ct.c_uint32),
#        ('myvalue', ct.c_uint32),
#        ]
#
#mmal_metadata_get = _lib.mmal_metadata_get
#mmal_metadata_get.argtypes = [ct.POINTER(MMAL_BUFFER_HEADER_T), ct.c_uint32]
#mmal_metadata_get.restype = ct.POINTER(MMAL_METADATA_T)
#
#mmal_metadata_set = _lib.mmal_metadata_set
#mmal_metadata_set.argtypes = [ct.POINTER(MMAL_BUFFER_HEADER_T), ct.POINTER(MMAL_METADATA_T)]
#mmal_metadata_set.restype = MMAL_STATUS_T

# mmal_queue.h ###############################################################

class MMAL_QUEUE_T(ct.Structure):
    _fields_ = []

mmal_queue_create = _lib.mmal_queue_create
mmal_queue_create.argtypes = []
mmal_queue_create.restype = ct.POINTER(MMAL_QUEUE_T)

mmal_queue_put = _lib.mmal_queue_put
mmal_queue_put.argtypes = [ct.POINTER(MMAL_QUEUE_T), ct.POINTER(MMAL_BUFFER_HEADER_T)]
mmal_queue_put.restype = None

mmal_queue_put_back = _lib.mmal_queue_put_back
mmal_queue_put_back.argtypes = [ct.POINTER(MMAL_QUEUE_T), ct.POINTER(MMAL_BUFFER_HEADER_T)]
mmal_queue_put_back.restype = None

mmal_queue_get = _lib.mmal_queue_get
mmal_queue_get.argtypes = [ct.POINTER(MMAL_QUEUE_T)]
mmal_queue_get.restype = ct.POINTER(MMAL_BUFFER_HEADER_T)

mmal_queue_wait = _lib.mmal_queue_wait
mmal_queue_wait.argtypes = [ct.POINTER(MMAL_QUEUE_T)]
mmal_queue_wait.restype = ct.POINTER(MMAL_BUFFER_HEADER_T)

try:
    mmal_queue_timedwait = _lib.mmal_queue_timedwait
except AttributeError:
    # mmal_queue_timedwait doesn't exist in older firmwares. We don't use it
    # anyway, so ignore it if we don't find it
    pass
else:
    mmal_queue_timedwait.argtypes = [ct.POINTER(MMAL_QUEUE_T), VCOS_UNSIGNED]
    mmal_queue_timedwait.restype = ct.POINTER(MMAL_BUFFER_HEADER_T)

mmal_queue_length = _lib.mmal_queue_length
mmal_queue_length.argtypes = [ct.POINTER(MMAL_QUEUE_T)]
mmal_queue_length.restype = ct.c_uint

mmal_queue_destroy = _lib.mmal_queue_destroy
mmal_queue_destroy.argtypes = [ct.POINTER(MMAL_QUEUE_T)]
mmal_queue_destroy.restype = None

# mmal_pool.h ################################################################

class MMAL_POOL_T(ct.Structure):
    _fields_ = [
        ('queue',       ct.POINTER(MMAL_QUEUE_T)),
        ('headers_num', ct.c_uint32),
        ('header',      ct.POINTER(ct.POINTER(MMAL_BUFFER_HEADER_T))),
        ]

mmal_pool_allocator_alloc_t = ct.CFUNCTYPE(
    None,
    ct.c_void_p, ct.c_uint32)
mmal_pool_allocator_free_t = ct.CFUNCTYPE(
    None,
    ct.c_void_p, ct.c_void_p)

mmal_pool_create = _lib.mmal_pool_create
mmal_pool_create.argtypes = [ct.c_uint, ct.c_uint32]
mmal_pool_create.restype = ct.POINTER(MMAL_POOL_T)

mmal_pool_create_with_allocator = _lib.mmal_pool_create_with_allocator
mmal_pool_create_with_allocator.argtypes = [
        ct.c_uint,
        ct.c_uint32,
        ct.c_void_p,
        mmal_pool_allocator_alloc_t,
        mmal_pool_allocator_free_t,
        ]
mmal_pool_create_with_allocator.restype = ct.POINTER(MMAL_POOL_T)

mmal_pool_destroy = _lib.mmal_pool_destroy
mmal_pool_destroy.argtypes = [ct.POINTER(MMAL_POOL_T)]
mmal_pool_destroy.restype = None

mmal_pool_resize = _lib.mmal_pool_resize
mmal_pool_resize.argtypes = [ct.POINTER(MMAL_POOL_T), ct.c_uint, ct.c_uint32]
mmal_pool_resize.restype = MMAL_STATUS_T

MMAL_POOL_BH_CB_T = ct.CFUNCTYPE(
    MMAL_BOOL_T,
    ct.POINTER(MMAL_POOL_T), ct.POINTER(MMAL_BUFFER_HEADER_T), ct.c_void_p)

mmal_pool_callback_set = _lib.mmal_pool_callback_set
mmal_pool_callback_set.argtypes = [ct.POINTER(MMAL_POOL_T), MMAL_POOL_BH_CB_T]
mmal_pool_callback_set.restype = None

mmal_pool_pre_release_callback_set = _lib.mmal_pool_pre_release_callback_set
mmal_pool_pre_release_callback_set.argtypes = [ct.POINTER(MMAL_POOL_T), MMAL_BH_PRE_RELEASE_CB_T, ct.c_void_p]
mmal_pool_pre_release_callback_set.restype = None

# mmal_events.h ##############################################################

MMAL_EVENT_ERROR              = MMAL_FOURCC('ERRO')
MMAL_EVENT_EOS                = MMAL_FOURCC('EEOS')
MMAL_EVENT_FORMAT_CHANGED     = MMAL_FOURCC('EFCH')
MMAL_EVENT_PARAMETER_CHANGED  = MMAL_FOURCC('EPCH')

class MMAL_EVENT_END_OF_STREAM_T(ct.Structure):
    _fields_ = [
        ('port_type',  MMAL_PORT_TYPE_T),
        ('port_index', ct.c_uint32),
        ]

class MMAL_EVENT_FORMAT_CHANGED_T(ct.Structure):
    _fields_ = [
        ('buffer_size_min',         ct.c_uint32),
        ('buffer_num_min',          ct.c_uint32),
        ('buffer_size_recommended', ct.c_uint32),
        ('buffer_num_recommended',  ct.c_uint32),
        ('format',                  ct.POINTER(MMAL_ES_FORMAT_T)),
        ]

class MMAL_EVENT_PARAMETER_CHANGED_T(ct.Structure):
    _fields_ = [
        ('hdr', MMAL_PARAMETER_HEADER_T),
        ]

mmal_event_format_changed_get = _lib.mmal_event_format_changed_get
mmal_event_format_changed_get.argtypes = [ct.POINTER(MMAL_BUFFER_HEADER_T)]
mmal_event_format_changed_get.restype = ct.POINTER(MMAL_EVENT_FORMAT_CHANGED_T)

# mmal_encodings.h ###########################################################

MMAL_ENCODING_H264            = MMAL_FOURCC('H264')
MMAL_ENCODING_MVC             = MMAL_FOURCC('MVC ')
MMAL_ENCODING_H263            = MMAL_FOURCC('H263')
MMAL_ENCODING_MP4V            = MMAL_FOURCC('MP4V')
MMAL_ENCODING_MP2V            = MMAL_FOURCC('MP2V')
MMAL_ENCODING_MP1V            = MMAL_FOURCC('MP1V')
MMAL_ENCODING_WMV3            = MMAL_FOURCC('WMV3')
MMAL_ENCODING_WMV2            = MMAL_FOURCC('WMV2')
MMAL_ENCODING_WMV1            = MMAL_FOURCC('WMV1')
MMAL_ENCODING_WVC1            = MMAL_FOURCC('WVC1')
MMAL_ENCODING_VP8             = MMAL_FOURCC('VP8 ')
MMAL_ENCODING_VP7             = MMAL_FOURCC('VP7 ')
MMAL_ENCODING_VP6             = MMAL_FOURCC('VP6 ')
MMAL_ENCODING_THEORA          = MMAL_FOURCC('THEO')
MMAL_ENCODING_SPARK           = MMAL_FOURCC('SPRK')
MMAL_ENCODING_MJPEG           = MMAL_FOURCC('MJPG')

MMAL_ENCODING_JPEG            = MMAL_FOURCC('JPEG')
MMAL_ENCODING_GIF             = MMAL_FOURCC('GIF ')
MMAL_ENCODING_PNG             = MMAL_FOURCC('PNG ')
MMAL_ENCODING_PPM             = MMAL_FOURCC('PPM ')
MMAL_ENCODING_TGA             = MMAL_FOURCC('TGA ')
MMAL_ENCODING_BMP             = MMAL_FOURCC('BMP ')

MMAL_ENCODING_I420            = MMAL_FOURCC('I420')
MMAL_ENCODING_I420_SLICE      = MMAL_FOURCC('S420')
MMAL_ENCODING_YV12            = MMAL_FOURCC('YV12')
MMAL_ENCODING_I422            = MMAL_FOURCC('I422')
MMAL_ENCODING_I422_SLICE      = MMAL_FOURCC('S422')
MMAL_ENCODING_YUYV            = MMAL_FOURCC('YUYV')
MMAL_ENCODING_YVYU            = MMAL_FOURCC('YVYU')
MMAL_ENCODING_UYVY            = MMAL_FOURCC('UYVY')
MMAL_ENCODING_VYUY            = MMAL_FOURCC('VYUY')
MMAL_ENCODING_NV12            = MMAL_FOURCC('NV12')
MMAL_ENCODING_NV21            = MMAL_FOURCC('NV21')
MMAL_ENCODING_ARGB            = MMAL_FOURCC('ARGB')
MMAL_ENCODING_ARGB_SLICE      = MMAL_FOURCC('argb')
MMAL_ENCODING_RGBA            = MMAL_FOURCC('RGBA')
MMAL_ENCODING_RGBA_SLICE      = MMAL_FOURCC('rgba')
MMAL_ENCODING_ABGR            = MMAL_FOURCC('ABGR')
MMAL_ENCODING_ABGR_SLICE      = MMAL_FOURCC('abgr')
MMAL_ENCODING_BGRA            = MMAL_FOURCC('BGRA')
MMAL_ENCODING_BGRA_SLICE      = MMAL_FOURCC('bgra')
MMAL_ENCODING_RGB16           = MMAL_FOURCC('RGB2')
MMAL_ENCODING_RGB16_SLICE     = MMAL_FOURCC('rgb2')
MMAL_ENCODING_RGB24           = MMAL_FOURCC('RGB3')
MMAL_ENCODING_RGB24_SLICE     = MMAL_FOURCC('rgb3')
MMAL_ENCODING_RGB32           = MMAL_FOURCC('RGB4')
MMAL_ENCODING_RGB32_SLICE     = MMAL_FOURCC('rgb4')
MMAL_ENCODING_BGR16           = MMAL_FOURCC('BGR2')
MMAL_ENCODING_BGR16_SLICE     = MMAL_FOURCC('bgr2')
MMAL_ENCODING_BGR24           = MMAL_FOURCC('BGR3')
MMAL_ENCODING_BGR24_SLICE     = MMAL_FOURCC('bgr3')
MMAL_ENCODING_BGR32           = MMAL_FOURCC('BGR4')
MMAL_ENCODING_BGR32_SLICE     = MMAL_FOURCC('bgr4')

MMAL_ENCODING_BAYER_SBGGR10P  = MMAL_FOURCC('pBAA')
MMAL_ENCODING_BAYER_SGRBG10P  = MMAL_FOURCC('pgAA')
MMAL_ENCODING_BAYER_SGBRG10P  = MMAL_FOURCC('pGAA')
MMAL_ENCODING_BAYER_SRGGB10P  = MMAL_FOURCC('PRAA')
MMAL_ENCODING_BAYER_SBGGR8    = MMAL_FOURCC('BA81')
MMAL_ENCODING_BAYER_SGBRG8    = MMAL_FOURCC('GBRG')
MMAL_ENCODING_BAYER_SGRBG8    = MMAL_FOURCC('GRBG')
MMAL_ENCODING_BAYER_SRGGB8    = MMAL_FOURCC('RGGB')
MMAL_ENCODING_BAYER_SBGGR12P  = MMAL_FOURCC('BY12')
MMAL_ENCODING_BAYER_SBGGR16   = MMAL_FOURCC('BYR2')
MMAL_ENCODING_BAYER_SBGGR10DPCM8 = MMAL_FOURCC('bBA8')

MMAL_ENCODING_YUVUV128        = MMAL_FOURCC('SAND')
MMAL_ENCODING_OPAQUE          = MMAL_FOURCC('OPQV')

MMAL_ENCODING_EGL_IMAGE       = MMAL_FOURCC('EGLI')
MMAL_ENCODING_PCM_UNSIGNED_BE = MMAL_FOURCC('PCMU')
MMAL_ENCODING_PCM_UNSIGNED_LE = MMAL_FOURCC('pcmu')
MMAL_ENCODING_PCM_SIGNED_BE   = MMAL_FOURCC('PCMS')
MMAL_ENCODING_PCM_SIGNED_LE   = MMAL_FOURCC('pcms')
MMAL_ENCODING_PCM_FLOAT_BE    = MMAL_FOURCC('PCMF')
MMAL_ENCODING_PCM_FLOAT_LE    = MMAL_FOURCC('pcmf')
MMAL_ENCODING_PCM_UNSIGNED    = MMAL_ENCODING_PCM_UNSIGNED_LE
MMAL_ENCODING_PCM_SIGNED      = MMAL_ENCODING_PCM_SIGNED_LE
MMAL_ENCODING_PCM_FLOAT       = MMAL_ENCODING_PCM_FLOAT_LE

MMAL_ENCODING_MP4A            = MMAL_FOURCC('MP4A')
MMAL_ENCODING_MPGA            = MMAL_FOURCC('MPGA')
MMAL_ENCODING_ALAW            = MMAL_FOURCC('ALAW')
MMAL_ENCODING_MULAW           = MMAL_FOURCC('ULAW')
MMAL_ENCODING_ADPCM_MS        = MMAL_FOURCC('MS\x00\x02')
MMAL_ENCODING_ADPCM_IMA_MS    = MMAL_FOURCC('MS\x00\x01')
MMAL_ENCODING_ADPCM_SWF       = MMAL_FOURCC('ASWF')
MMAL_ENCODING_WMA1            = MMAL_FOURCC('WMA1')
MMAL_ENCODING_WMA2            = MMAL_FOURCC('WMA2')
MMAL_ENCODING_WMAP            = MMAL_FOURCC('WMAP')
MMAL_ENCODING_WMAL            = MMAL_FOURCC('WMAL')
MMAL_ENCODING_WMAV            = MMAL_FOURCC('WMAV')
MMAL_ENCODING_AMRNB           = MMAL_FOURCC('AMRN')
MMAL_ENCODING_AMRWB           = MMAL_FOURCC('AMRW')
MMAL_ENCODING_AMRWBP          = MMAL_FOURCC('AMRP')
MMAL_ENCODING_AC3             = MMAL_FOURCC('AC3 ')
MMAL_ENCODING_EAC3            = MMAL_FOURCC('EAC3')
MMAL_ENCODING_DTS             = MMAL_FOURCC('DTS ')
MMAL_ENCODING_MLP             = MMAL_FOURCC('MLP ')
MMAL_ENCODING_FLAC            = MMAL_FOURCC('FLAC')
MMAL_ENCODING_VORBIS          = MMAL_FOURCC('VORB')
MMAL_ENCODING_SPEEX           = MMAL_FOURCC('SPX ')
MMAL_ENCODING_ATRAC3          = MMAL_FOURCC('ATR3')
MMAL_ENCODING_ATRACX          = MMAL_FOURCC('ATRX')
MMAL_ENCODING_ATRACL          = MMAL_FOURCC('ATRL')
MMAL_ENCODING_MIDI            = MMAL_FOURCC('MIDI')
MMAL_ENCODING_EVRC            = MMAL_FOURCC('EVRC')
MMAL_ENCODING_NELLYMOSER      = MMAL_FOURCC('NELY')
MMAL_ENCODING_QCELP           = MMAL_FOURCC('QCEL')
MMAL_ENCODING_MP4V_DIVX_DRM   = MMAL_FOURCC('M4VD')

MMAL_ENCODING_VARIANT_H264_DEFAULT = 0
MMAL_ENCODING_VARIANT_H264_AVC1    = MMAL_FOURCC('AVC1')
MMAL_ENCODING_VARIANT_H264_RAW     = MMAL_FOURCC('RAW ')
MMAL_ENCODING_VARIANT_MP4A_DEFAULT = 0
MMAL_ENCODING_VARIANT_MP4A_ADTS    = MMAL_FOURCC('ADTS')

MMAL_COLOR_SPACE_UNKNOWN      = 0
MMAL_COLOR_SPACE_ITUR_BT601   = MMAL_FOURCC('Y601')
MMAL_COLOR_SPACE_ITUR_BT709   = MMAL_FOURCC('Y709')
MMAL_COLOR_SPACE_JPEG_JFIF    = MMAL_FOURCC('YJFI')
MMAL_COLOR_SPACE_FCC          = MMAL_FOURCC('YFCC')
MMAL_COLOR_SPACE_SMPTE240M    = MMAL_FOURCC('Y240')
MMAL_COLOR_SPACE_BT470_2_M    = MMAL_FOURCC('Y__M')
MMAL_COLOR_SPACE_BT470_2_BG   = MMAL_FOURCC('Y_BG')
MMAL_COLOR_SPACE_JFIF_Y16_255 = MMAL_FOURCC('YY16')

# util/mmal_default_components.h #############################################

MMAL_COMPONENT_DEFAULT_VIDEO_DECODER   = b"vc.ril.video_decode"
MMAL_COMPONENT_DEFAULT_VIDEO_ENCODER   = b"vc.ril.video_encode"
MMAL_COMPONENT_DEFAULT_VIDEO_RENDERER  = b"vc.ril.video_render"
MMAL_COMPONENT_DEFAULT_IMAGE_DECODER   = b"vc.ril.image_decode"
MMAL_COMPONENT_DEFAULT_IMAGE_ENCODER   = b"vc.ril.image_encode"
MMAL_COMPONENT_DEFAULT_CAMERA          = b"vc.ril.camera"
MMAL_COMPONENT_DEFAULT_VIDEO_CONVERTER = b"vc.video_convert"
MMAL_COMPONENT_DEFAULT_SPLITTER        = b"vc.splitter"
MMAL_COMPONENT_DEFAULT_SCHEDULER       = b"vc.scheduler"
MMAL_COMPONENT_DEFAULT_VIDEO_INJECTER  = b"vc.video_inject"
MMAL_COMPONENT_DEFAULT_VIDEO_SPLITTER  = b"vc.ril.video_splitter"
MMAL_COMPONENT_DEFAULT_AUDIO_DECODER   = b"none"
MMAL_COMPONENT_DEFAULT_AUDIO_RENDERER  = b"vc.ril.audio_render"
MMAL_COMPONENT_DEFAULT_MIRACAST        = b"vc.miracast"
MMAL_COMPONENT_DEFAULT_CLOCK           = b"vc.clock"
MMAL_COMPONENT_DEFAULT_CAMERA_INFO     = b"vc.camera_info"
# The following two components aren't in the MMAL headers, but do exist
MMAL_COMPONENT_DEFAULT_NULL_SINK       = b"vc.null_sink"
MMAL_COMPONENT_DEFAULT_RESIZER         = b"vc.ril.resize"
MMAL_COMPONENT_DEFAULT_ISP             = b"vc.ril.isp"
MMAL_COMPONENT_RAW_CAMERA              = b"vc.ril.rawcam"

# util/mmal_util_params.h ####################################################

mmal_port_parameter_set_boolean = _lib.mmal_port_parameter_set_boolean
mmal_port_parameter_set_boolean.argtypes = [ct.POINTER(MMAL_PORT_T), ct.c_uint32, MMAL_BOOL_T]
mmal_port_parameter_set_boolean.restype = MMAL_STATUS_T

mmal_port_parameter_get_boolean = _lib.mmal_port_parameter_get_boolean
mmal_port_parameter_get_boolean.argtypes = [ct.POINTER(MMAL_PORT_T), ct.c_uint32, ct.POINTER(MMAL_BOOL_T)]
mmal_port_parameter_get_boolean.restype = MMAL_STATUS_T

mmal_port_parameter_set_uint64 = _lib.mmal_port_parameter_set_uint64
mmal_port_parameter_set_uint64.argtypes = [ct.POINTER(MMAL_PORT_T), ct.c_uint32, ct.c_uint64]
mmal_port_parameter_set_uint64.restype = MMAL_STATUS_T

mmal_port_parameter_get_uint64 = _lib.mmal_port_parameter_get_uint64
mmal_port_parameter_get_uint64.argtypes = [ct.POINTER(MMAL_PORT_T), ct.c_uint32, ct.POINTER(ct.c_uint64)]
mmal_port_parameter_get_uint64.restype = MMAL_STATUS_T

mmal_port_parameter_set_int64 = _lib.mmal_port_parameter_set_int64
mmal_port_parameter_set_int64.argtypes = [ct.POINTER(MMAL_PORT_T), ct.c_uint32, ct.c_int64]
mmal_port_parameter_set_int64.restype = MMAL_STATUS_T

mmal_port_parameter_get_int64 = _lib.mmal_port_parameter_get_int64
mmal_port_parameter_get_int64.argtypes = [ct.POINTER(MMAL_PORT_T), ct.c_uint32, ct.POINTER(ct.c_int64)]
mmal_port_parameter_get_int64.restype = MMAL_STATUS_T

mmal_port_parameter_set_uint32 = _lib.mmal_port_parameter_set_uint32
mmal_port_parameter_set_uint32.argtypes = [ct.POINTER(MMAL_PORT_T), ct.c_uint32, ct.c_uint32]
mmal_port_parameter_set_uint32.restype = MMAL_STATUS_T

mmal_port_parameter_get_uint32 = _lib.mmal_port_parameter_get_uint32
mmal_port_parameter_get_uint32.argtypes = [ct.POINTER(MMAL_PORT_T), ct.c_uint32, ct.POINTER(ct.c_uint32)]
mmal_port_parameter_get_uint32.restype = MMAL_STATUS_T

mmal_port_parameter_set_int32 = _lib.mmal_port_parameter_set_int32
mmal_port_parameter_set_int32.argtypes = [ct.POINTER(MMAL_PORT_T), ct.c_uint32, ct.c_int32]
mmal_port_parameter_set_int32.restype = MMAL_STATUS_T

mmal_port_parameter_get_int32 = _lib.mmal_port_parameter_get_int32
mmal_port_parameter_get_int32.argtypes = [ct.POINTER(MMAL_PORT_T), ct.c_uint32, ct.POINTER(ct.c_int32)]
mmal_port_parameter_get_int32.restype = MMAL_STATUS_T

mmal_port_parameter_set_rational = _lib.mmal_port_parameter_set_rational
mmal_port_parameter_set_rational.argtypes = [ct.POINTER(MMAL_PORT_T), ct.c_uint32, MMAL_RATIONAL_T]
mmal_port_parameter_set_rational.restype = MMAL_STATUS_T

mmal_port_parameter_get_rational = _lib.mmal_port_parameter_get_rational
mmal_port_parameter_get_rational.argtypes = [ct.POINTER(MMAL_PORT_T), ct.c_uint32, ct.POINTER(MMAL_RATIONAL_T)]
mmal_port_parameter_get_rational.restype = MMAL_STATUS_T

mmal_port_parameter_set_string = _lib.mmal_port_parameter_set_string
mmal_port_parameter_set_string.argtypes = [ct.POINTER(MMAL_PORT_T), ct.c_uint32, ct.c_char_p]
mmal_port_parameter_set_string.restype = MMAL_STATUS_T

mmal_port_parameter_set_bytes = _lib.mmal_port_parameter_set_bytes
mmal_port_parameter_set_bytes.argtypes = [ct.POINTER(MMAL_PORT_T), ct.c_uint32, ct.POINTER(ct.c_uint8), ct.c_uint]
mmal_port_parameter_set_bytes.restype = MMAL_STATUS_T

mmal_util_port_set_uri = _lib.mmal_util_port_set_uri
mmal_util_port_set_uri.argtypes = [ct.POINTER(MMAL_PORT_T), ct.c_char_p]
mmal_util_port_set_uri.restype = MMAL_STATUS_T

mmal_util_set_display_region = _lib.mmal_util_set_display_region
mmal_util_set_display_region.argtypes = [ct.POINTER(MMAL_PORT_T), ct.POINTER(MMAL_DISPLAYREGION_T)]
mmal_util_set_display_region.restype = MMAL_STATUS_T

mmal_util_camera_use_stc_timestamp = _lib.mmal_util_camera_use_stc_timestamp
mmal_util_camera_use_stc_timestamp.argtypes = [ct.POINTER(MMAL_PORT_T), MMAL_CAMERA_STC_MODE_T]
mmal_util_camera_use_stc_timestamp.restype = MMAL_STATUS_T

mmal_util_get_core_port_stats = _lib.mmal_util_get_core_port_stats
mmal_util_get_core_port_stats.argtypes = [ct.POINTER(MMAL_PORT_T), MMAL_CORE_STATS_DIR, MMAL_BOOL_T, ct.POINTER(MMAL_CORE_STATISTICS_T)]
mmal_util_get_core_port_stats.restype = MMAL_STATUS_T

# util/mmal_connection.h #####################################################

MMAL_CONNECTION_FLAG_TUNNELLING = 0x1
MMAL_CONNECTION_FLAG_ALLOCATION_ON_INPUT = 0x2
MMAL_CONNECTION_FLAG_ALLOCATION_ON_OUTPUT = 0x4
MMAL_CONNECTION_FLAG_KEEP_BUFFER_REQUIREMENTS = 0x8
MMAL_CONNECTION_FLAG_DIRECT = 0x10

class MMAL_CONNECTION_T(ct.Structure):
    # Forward type declaration
    pass

MMAL_CONNECTION_CALLBACK_T = ct.CFUNCTYPE(
    None,
    ct.POINTER(MMAL_CONNECTION_T))

MMAL_CONNECTION_T._fields_ = [
    ('user_data',    ct.c_void_p),
    ('callback',     MMAL_CONNECTION_CALLBACK_T),
    ('is_enabled',   ct.c_uint32),
    ('flags',        ct.c_uint32),
    # Originally "in", but this is a Python keyword
    ('in_',          ct.POINTER(MMAL_PORT_T)),
    ('out',          ct.POINTER(MMAL_PORT_T)),
    ('pool',         ct.POINTER(MMAL_POOL_T)),
    ('queue',        ct.POINTER(MMAL_QUEUE_T)),
    ('name',         ct.c_char_p),
    ('time_setup',   ct.c_int64),
    ('time_enable',  ct.c_int64),
    ('time_disable', ct.c_int64),
    ]

mmal_connection_create = _lib.mmal_connection_create
mmal_connection_create.argtypes = [ct.POINTER(ct.POINTER(MMAL_CONNECTION_T)), ct.POINTER(MMAL_PORT_T), ct.POINTER(MMAL_PORT_T), ct.c_uint32]
mmal_connection_create.restype = MMAL_STATUS_T

mmal_connection_acquire = _lib.mmal_connection_acquire
mmal_connection_acquire.argtypes = [ct.POINTER(MMAL_CONNECTION_T)]
mmal_connection_acquire.restype = None

mmal_connection_release = _lib.mmal_connection_release
mmal_connection_release.argtypes = [ct.POINTER(MMAL_CONNECTION_T)]
mmal_connection_release.restype = MMAL_STATUS_T

mmal_connection_destroy = _lib.mmal_connection_destroy
mmal_connection_destroy.argtypes = [ct.POINTER(MMAL_CONNECTION_T)]
mmal_connection_destroy.restype = MMAL_STATUS_T

mmal_connection_enable = _lib.mmal_connection_enable
mmal_connection_enable.argtypes = [ct.POINTER(MMAL_CONNECTION_T)]
mmal_connection_enable.restype = MMAL_STATUS_T

mmal_connection_disable = _lib.mmal_connection_disable
mmal_connection_disable.argtypes = [ct.POINTER(MMAL_CONNECTION_T)]
mmal_connection_disable.restype = MMAL_STATUS_T

mmal_connection_event_format_changed = _lib.mmal_connection_event_format_changed
mmal_connection_event_format_changed.argtypes = [ct.POINTER(MMAL_CONNECTION_T), ct.POINTER(MMAL_BUFFER_HEADER_T)]
mmal_connection_event_format_changed.restype = MMAL_STATUS_T

# util/mmal_util.h ###########################################################

mmal_status_to_string = _lib.mmal_status_to_string
mmal_status_to_string.argtypes = [MMAL_STATUS_T]
mmal_status_to_string.restype = ct.c_char_p

mmal_encoding_stride_to_width = _lib.mmal_encoding_stride_to_width
mmal_encoding_stride_to_width.argtypes = [ct.c_uint32, ct.c_uint32]
mmal_encoding_stride_to_width.restype = ct.c_uint32

mmal_encoding_width_to_stride = _lib.mmal_encoding_width_to_stride
mmal_encoding_width_to_stride.argtypes = [ct.c_uint32, ct.c_uint32]
mmal_encoding_width_to_stride.restype = ct.c_uint32

mmal_port_type_to_string = _lib.mmal_port_type_to_string
mmal_port_type_to_string.argtypes = [MMAL_PORT_TYPE_T]
mmal_port_type_to_string.restype = ct.c_char_p

mmal_port_parameter_alloc_get = _lib.mmal_port_parameter_alloc_get
mmal_port_parameter_alloc_get.argtypes = [ct.POINTER(MMAL_PORT_T), ct.c_uint32, ct.c_uint32, ct.POINTER(MMAL_STATUS_T)]
mmal_port_parameter_alloc_get.restype = ct.POINTER(MMAL_PARAMETER_HEADER_T)

mmal_port_parameter_free = _lib.mmal_port_parameter_free
mmal_port_parameter_free.argtypes = [ct.POINTER(MMAL_PARAMETER_HEADER_T)]
mmal_port_parameter_free.restype = None

mmal_buffer_header_copy_header = _lib.mmal_buffer_header_copy_header
mmal_buffer_header_copy_header.argtypes = [ct.POINTER(MMAL_BUFFER_HEADER_T), ct.POINTER(MMAL_BUFFER_HEADER_T)]
mmal_buffer_header_copy_header.restype = None

mmal_port_pool_create = _lib.mmal_port_pool_create
mmal_port_pool_create.argtypes = [ct.POINTER(MMAL_PORT_T), ct.c_uint, ct.c_uint32]
mmal_port_pool_create.restype = ct.POINTER(MMAL_POOL_T)

mmal_port_pool_destroy = _lib.mmal_port_pool_destroy
mmal_port_pool_destroy.argtypes = [ct.POINTER(MMAL_PORT_T), ct.POINTER(MMAL_POOL_T)]
mmal_port_pool_destroy.restype = None

mmal_log_dump_port = _lib.mmal_log_dump_port
mmal_log_dump_port.argtypes = [ct.POINTER(MMAL_PORT_T)]
mmal_log_dump_port.restype = None

mmal_log_dump_format = _lib.mmal_log_dump_format
mmal_log_dump_format.argtypes = [ct.POINTER(MMAL_ES_FORMAT_T)]
mmal_log_dump_format.restype = None

mmal_util_get_port = _lib.mmal_util_get_port
mmal_util_get_port.argtypes = [ct.POINTER(MMAL_COMPONENT_T), MMAL_PORT_TYPE_T, ct.c_uint]
mmal_util_get_port.restype = ct.POINTER(MMAL_PORT_T)

mmal_4cc_to_string = _lib.mmal_4cc_to_string
mmal_4cc_to_string.argtypes = [ct.c_char_p, ct.c_size_t, ct.c_uint32]
mmal_4cc_to_string.restype = ct.c_char_p

