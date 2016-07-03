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
import weakref
from collections import namedtuple
from fractions import Fraction
from itertools import cycle

from . import mmal
from .exc import (
    mmal_check,
    PiCameraValueError,
    PiCameraRuntimeError,
    PiCameraMMALError,
    PiCameraDeprecated,
    )


# Old firmwares confuse the RGB24 and BGR24 encodings. This flag tracks whether
# the order needs fixing (it is set during MMALCamera.__init__).
FIX_RGB_BGR_ORDER = None

# Mapping of parameters to the C-structure they expect / return. If a parameter
# does not appear in this mapping, it cannot be queried / set with the
# MMALControlPort.params attribute.
PARAM_TYPES = {
    mmal.MMAL_PARAMETER_ALGORITHM_CONTROL:              mmal.MMAL_PARAMETER_ALGORITHM_CONTROL_T,
    mmal.MMAL_PARAMETER_ANNOTATE:                       None, # adjusted by MMALCamera.annotate_rev
    mmal.MMAL_PARAMETER_ANTISHAKE:                      mmal.MMAL_PARAMETER_BOOLEAN_T,
    mmal.MMAL_PARAMETER_AUDIO_LATENCY_TARGET:           mmal.MMAL_PARAMETER_AUDIO_LATENCY_TARGET_T,
    mmal.MMAL_PARAMETER_AWB_MODE:                       mmal.MMAL_PARAMETER_AWBMODE_T,
    mmal.MMAL_PARAMETER_BRIGHTNESS:                     mmal.MMAL_PARAMETER_RATIONAL_T,
    mmal.MMAL_PARAMETER_BUFFER_FLAG_FILTER:             mmal.MMAL_PARAMETER_UINT32_T,
    mmal.MMAL_PARAMETER_BUFFER_REQUIREMENTS:            mmal.MMAL_PARAMETER_BUFFER_REQUIREMENTS_T,
    mmal.MMAL_PARAMETER_CAMERA_BURST_CAPTURE:           mmal.MMAL_PARAMETER_BOOLEAN_T,
    mmal.MMAL_PARAMETER_CAMERA_CLOCKING_MODE:           mmal.MMAL_PARAMETER_CAMERA_CLOCKING_MODE_T,
    mmal.MMAL_PARAMETER_CAMERA_CONFIG:                  mmal.MMAL_PARAMETER_CAMERA_CONFIG_T,
    mmal.MMAL_PARAMETER_CAMERA_CUSTOM_SENSOR_CONFIG:    mmal.MMAL_PARAMETER_UINT32_T,
    mmal.MMAL_PARAMETER_CAMERA_INFO:                    None, # adjusted by MMALCameraInfo.info_rev
    mmal.MMAL_PARAMETER_CAMERA_INTERFACE:               mmal.MMAL_PARAMETER_CAMERA_INTERFACE_T,
    mmal.MMAL_PARAMETER_CAMERA_MIN_ISO:                 mmal.MMAL_PARAMETER_UINT32_T,
    mmal.MMAL_PARAMETER_CAMERA_NUM:                     mmal.MMAL_PARAMETER_INT32_T,
    mmal.MMAL_PARAMETER_CAMERA_RX_CONFIG:               mmal.MMAL_PARAMETER_CAMERA_RX_CONFIG_T,
    mmal.MMAL_PARAMETER_CAMERA_RX_TIMING:               mmal.MMAL_PARAMETER_CAMERA_RX_TIMING_T,
    mmal.MMAL_PARAMETER_CAMERA_SETTINGS:                mmal.MMAL_PARAMETER_CAMERA_SETTINGS_T,
    mmal.MMAL_PARAMETER_CAMERA_USE_CASE:                mmal.MMAL_PARAMETER_CAMERA_USE_CASE_T,
    mmal.MMAL_PARAMETER_CAPTURE_EXPOSURE_COMP:          mmal.MMAL_PARAMETER_INT32_T,
    mmal.MMAL_PARAMETER_CAPTURE:                        mmal.MMAL_PARAMETER_BOOLEAN_T,
    mmal.MMAL_PARAMETER_CAPTURE_MODE:                   mmal.MMAL_PARAMETER_CAPTUREMODE_T,
    mmal.MMAL_PARAMETER_CAPTURE_STATS_PASS:             mmal.MMAL_PARAMETER_BOOLEAN_T,
    mmal.MMAL_PARAMETER_CAPTURE_STATUS:                 mmal.MMAL_PARAMETER_CAPTURE_STATUS_T,
    mmal.MMAL_PARAMETER_CHANGE_EVENT_REQUEST:           mmal.MMAL_PARAMETER_CHANGE_EVENT_REQUEST_T,
    mmal.MMAL_PARAMETER_CLOCK_ACTIVE:                   mmal.MMAL_PARAMETER_BOOLEAN_T,
    mmal.MMAL_PARAMETER_CLOCK_DISCONT_THRESHOLD:        mmal.MMAL_PARAMETER_CLOCK_DISCONT_THRESHOLD_T,
    mmal.MMAL_PARAMETER_CLOCK_ENABLE_BUFFER_INFO:       mmal.MMAL_PARAMETER_BOOLEAN_T,
    mmal.MMAL_PARAMETER_CLOCK_FRAME_RATE:               mmal.MMAL_PARAMETER_RATIONAL_T,
    mmal.MMAL_PARAMETER_CLOCK_LATENCY:                  mmal.MMAL_PARAMETER_CLOCK_LATENCY_T,
    mmal.MMAL_PARAMETER_CLOCK_REQUEST_THRESHOLD:        mmal.MMAL_PARAMETER_CLOCK_REQUEST_THRESHOLD_T,
    mmal.MMAL_PARAMETER_CLOCK_SCALE:                    mmal.MMAL_PARAMETER_RATIONAL_T,
    mmal.MMAL_PARAMETER_CLOCK_TIME:                     mmal.MMAL_PARAMETER_INT64_T,
    mmal.MMAL_PARAMETER_CLOCK_UPDATE_THRESHOLD:         mmal.MMAL_PARAMETER_CLOCK_UPDATE_THRESHOLD_T,
    mmal.MMAL_PARAMETER_COLOUR_EFFECT:                  mmal.MMAL_PARAMETER_COLOURFX_T,
    mmal.MMAL_PARAMETER_CONTRAST:                       mmal.MMAL_PARAMETER_RATIONAL_T,
    mmal.MMAL_PARAMETER_CORE_STATISTICS:                mmal.MMAL_PARAMETER_CORE_STATISTICS_T,
    mmal.MMAL_PARAMETER_CUSTOM_AWB_GAINS:               mmal.MMAL_PARAMETER_AWB_GAINS_T,
    mmal.MMAL_PARAMETER_DISPLAYREGION:                  mmal.MMAL_DISPLAYREGION_T,
    mmal.MMAL_PARAMETER_DPF_CONFIG:                     mmal.MMAL_PARAMETER_UINT32_T,
    mmal.MMAL_PARAMETER_DYNAMIC_RANGE_COMPRESSION:      mmal.MMAL_PARAMETER_DRC_T,
    mmal.MMAL_PARAMETER_ENABLE_RAW_CAPTURE:             mmal.MMAL_PARAMETER_BOOLEAN_T,
    mmal.MMAL_PARAMETER_EXIF_DISABLE:                   mmal.MMAL_PARAMETER_BOOLEAN_T,
    mmal.MMAL_PARAMETER_EXIF:                           mmal.MMAL_PARAMETER_EXIF_T,
    mmal.MMAL_PARAMETER_EXP_METERING_MODE:              mmal.MMAL_PARAMETER_EXPOSUREMETERINGMODE_T,
    mmal.MMAL_PARAMETER_EXPOSURE_COMP:                  mmal.MMAL_PARAMETER_INT32_T,
    mmal.MMAL_PARAMETER_EXPOSURE_MODE:                  mmal.MMAL_PARAMETER_EXPOSUREMODE_T,
    mmal.MMAL_PARAMETER_EXTRA_BUFFERS:                  mmal.MMAL_PARAMETER_UINT32_T,
    mmal.MMAL_PARAMETER_FIELD_OF_VIEW:                  mmal.MMAL_PARAMETER_FIELD_OF_VIEW_T,
    mmal.MMAL_PARAMETER_FLASH:                          mmal.MMAL_PARAMETER_FLASH_T,
    mmal.MMAL_PARAMETER_FLASH_REQUIRED:                 mmal.MMAL_PARAMETER_BOOLEAN_T,
    mmal.MMAL_PARAMETER_FLASH_SELECT:                   mmal.MMAL_PARAMETER_FLASH_SELECT_T,
    mmal.MMAL_PARAMETER_FLICKER_AVOID:                  mmal.MMAL_PARAMETER_FLICKERAVOID_T,
    mmal.MMAL_PARAMETER_FOCUS:                          mmal.MMAL_PARAMETER_FOCUS_T,
    mmal.MMAL_PARAMETER_FOCUS_REGIONS:                  mmal.MMAL_PARAMETER_FOCUS_REGIONS_T,
    mmal.MMAL_PARAMETER_FOCUS_STATUS:                   mmal.MMAL_PARAMETER_FOCUS_STATUS_T,
    mmal.MMAL_PARAMETER_FPS_RANGE:                      mmal.MMAL_PARAMETER_FPS_RANGE_T,
    mmal.MMAL_PARAMETER_FRAME_RATE:                     mmal.MMAL_PARAMETER_RATIONAL_T, # actually mmal.MMAL_PARAMETER_FRAME_RATE_T but this only contains a rational anyway...
    mmal.MMAL_PARAMETER_IMAGE_EFFECT:                   mmal.MMAL_PARAMETER_IMAGEFX_T,
    mmal.MMAL_PARAMETER_IMAGE_EFFECT_PARAMETERS:        mmal.MMAL_PARAMETER_IMAGEFX_PARAMETERS_T,
    mmal.MMAL_PARAMETER_INPUT_CROP:                     mmal.MMAL_PARAMETER_INPUT_CROP_T,
    mmal.MMAL_PARAMETER_INTRAPERIOD:                    mmal.MMAL_PARAMETER_UINT32_T,
    mmal.MMAL_PARAMETER_ISO:                            mmal.MMAL_PARAMETER_UINT32_T,
    mmal.MMAL_PARAMETER_JPEG_ATTACH_LOG:                mmal.MMAL_PARAMETER_BOOLEAN_T,
    mmal.MMAL_PARAMETER_JPEG_Q_FACTOR:                  mmal.MMAL_PARAMETER_UINT32_T,
    mmal.MMAL_PARAMETER_LOCKSTEP_ENABLE:                mmal.MMAL_PARAMETER_BOOLEAN_T,
    mmal.MMAL_PARAMETER_LOGGING:                        mmal.MMAL_PARAMETER_LOGGING_T,
    mmal.MMAL_PARAMETER_MB_ROWS_PER_SLICE:              mmal.MMAL_PARAMETER_UINT32_T,
    mmal.MMAL_PARAMETER_MEM_USAGE:                      mmal.MMAL_PARAMETER_MEM_USAGE_T,
    mmal.MMAL_PARAMETER_MINIMISE_FRAGMENTATION:         mmal.MMAL_PARAMETER_BOOLEAN_T,
    mmal.MMAL_PARAMETER_MIRROR:                         mmal.MMAL_PARAMETER_MIRROR_T,
    mmal.MMAL_PARAMETER_NALUNITFORMAT:                  mmal.MMAL_PARAMETER_VIDEO_NALUNITFORMAT_T,
    mmal.MMAL_PARAMETER_NO_IMAGE_PADDING:               mmal.MMAL_PARAMETER_BOOLEAN_T,
    mmal.MMAL_PARAMETER_POWERMON_ENABLE:                mmal.MMAL_PARAMETER_BOOLEAN_T,
    mmal.MMAL_PARAMETER_PRIVACY_INDICATOR:              mmal.MMAL_PARAMETER_PRIVACY_INDICATOR_T,
    mmal.MMAL_PARAMETER_PROFILE:                        mmal.MMAL_PARAMETER_VIDEO_PROFILE_T,
    mmal.MMAL_PARAMETER_RATECONTROL:                    mmal.MMAL_PARAMETER_VIDEO_RATECONTROL_T,
    mmal.MMAL_PARAMETER_REDEYE:                         mmal.MMAL_PARAMETER_REDEYE_T,
    mmal.MMAL_PARAMETER_ROTATION:                       mmal.MMAL_PARAMETER_INT32_T,
    mmal.MMAL_PARAMETER_SATURATION:                     mmal.MMAL_PARAMETER_RATIONAL_T,
    mmal.MMAL_PARAMETER_SEEK:                           mmal.MMAL_PARAMETER_SEEK_T,
    mmal.MMAL_PARAMETER_SENSOR_INFORMATION:             mmal.MMAL_PARAMETER_SENSOR_INFORMATION_T,
    mmal.MMAL_PARAMETER_SHARPNESS:                      mmal.MMAL_PARAMETER_RATIONAL_T,
    mmal.MMAL_PARAMETER_SHUTTER_SPEED:                  mmal.MMAL_PARAMETER_UINT32_T,
    mmal.MMAL_PARAMETER_STATISTICS:                     mmal.MMAL_PARAMETER_STATISTICS_T,
    mmal.MMAL_PARAMETER_STEREOSCOPIC_MODE:              mmal.MMAL_PARAMETER_STEREOSCOPIC_MODE_T,
    mmal.MMAL_PARAMETER_STILLS_DENOISE:                 mmal.MMAL_PARAMETER_BOOLEAN_T,
    mmal.MMAL_PARAMETER_SUPPORTED_ENCODINGS:            mmal.MMAL_PARAMETER_ENCODING_T,
    mmal.MMAL_PARAMETER_SUPPORTED_PROFILES:             mmal.MMAL_PARAMETER_VIDEO_PROFILE_T,
    mmal.MMAL_PARAMETER_SW_SATURATION_DISABLE:          mmal.MMAL_PARAMETER_BOOLEAN_T,
    mmal.MMAL_PARAMETER_SW_SHARPEN_DISABLE:             mmal.MMAL_PARAMETER_BOOLEAN_T,
    mmal.MMAL_PARAMETER_SYSTEM_TIME:                    mmal.MMAL_PARAMETER_UINT64_T,
    mmal.MMAL_PARAMETER_THUMBNAIL_CONFIGURATION:        mmal.MMAL_PARAMETER_THUMBNAIL_CONFIG_T,
    mmal.MMAL_PARAMETER_URI:                            mmal.MMAL_PARAMETER_URI_T,
    mmal.MMAL_PARAMETER_USE_STC:                        mmal.MMAL_PARAMETER_CAMERA_STC_MODE_T,
    mmal.MMAL_PARAMETER_VIDEO_ALIGN_HORIZ:              mmal.MMAL_PARAMETER_UINT32_T,
    mmal.MMAL_PARAMETER_VIDEO_ALIGN_VERT:               mmal.MMAL_PARAMETER_UINT32_T,
    mmal.MMAL_PARAMETER_VIDEO_BIT_RATE:                 mmal.MMAL_PARAMETER_UINT32_T,
    mmal.MMAL_PARAMETER_VIDEO_DENOISE:                  mmal.MMAL_PARAMETER_BOOLEAN_T,
    mmal.MMAL_PARAMETER_VIDEO_DROPPABLE_PFRAMES:        mmal.MMAL_PARAMETER_BOOLEAN_T,
    mmal.MMAL_PARAMETER_VIDEO_EEDE_ENABLE:              mmal.MMAL_PARAMETER_VIDEO_EEDE_ENABLE_T,
    mmal.MMAL_PARAMETER_VIDEO_EEDE_LOSSRATE:            mmal.MMAL_PARAMETER_VIDEO_EEDE_LOSSRATE_T,
    mmal.MMAL_PARAMETER_VIDEO_ENCODE_FRAME_LIMIT_BITS:  mmal.MMAL_PARAMETER_UINT32_T,
    mmal.MMAL_PARAMETER_VIDEO_ENCODE_INITIAL_QUANT:     mmal.MMAL_PARAMETER_UINT32_T,
    mmal.MMAL_PARAMETER_VIDEO_ENCODE_INLINE_HEADER:     mmal.MMAL_PARAMETER_BOOLEAN_T,
    mmal.MMAL_PARAMETER_VIDEO_ENCODE_INLINE_VECTORS:    mmal.MMAL_PARAMETER_BOOLEAN_T,
    mmal.MMAL_PARAMETER_VIDEO_ENCODE_MAX_QUANT:         mmal.MMAL_PARAMETER_UINT32_T,
    mmal.MMAL_PARAMETER_VIDEO_ENCODE_MIN_QUANT:         mmal.MMAL_PARAMETER_UINT32_T,
    mmal.MMAL_PARAMETER_VIDEO_ENCODE_PEAK_RATE:         mmal.MMAL_PARAMETER_UINT32_T,
    mmal.MMAL_PARAMETER_VIDEO_ENCODE_QP_P:              mmal.MMAL_PARAMETER_UINT32_T,
    mmal.MMAL_PARAMETER_VIDEO_ENCODE_RC_MODEL:          mmal.MMAL_PARAMETER_VIDEO_ENCODE_RC_MODEL_T,
    mmal.MMAL_PARAMETER_VIDEO_ENCODE_RC_SLICE_DQUANT:   mmal.MMAL_PARAMETER_UINT32_T,
    mmal.MMAL_PARAMETER_VIDEO_ENCODE_SEI_ENABLE:        mmal.MMAL_PARAMETER_BOOLEAN_T,
    mmal.MMAL_PARAMETER_VIDEO_ENCODE_SPS_TIMINGS:       mmal.MMAL_PARAMETER_BOOLEAN_T,
    mmal.MMAL_PARAMETER_VIDEO_FRAME_RATE:               mmal.MMAL_PARAMETER_RATIONAL_T, # actually mmal.MMAL_PARAMETER_FRAME_RATE_T but this only contains a rational anyway...
    mmal.MMAL_PARAMETER_VIDEO_IMMUTABLE_INPUT:          mmal.MMAL_PARAMETER_BOOLEAN_T,
    mmal.MMAL_PARAMETER_VIDEO_INTERLACE_TYPE:           mmal.MMAL_PARAMETER_VIDEO_INTERLACE_TYPE_T,
    mmal.MMAL_PARAMETER_VIDEO_INTERPOLATE_TIMESTAMPS:   mmal.MMAL_PARAMETER_BOOLEAN_T,
    mmal.MMAL_PARAMETER_VIDEO_INTRA_REFRESH:            mmal.MMAL_PARAMETER_VIDEO_INTRA_REFRESH_T,
    mmal.MMAL_PARAMETER_VIDEO_LEVEL_EXTENSION:          mmal.MMAL_PARAMETER_VIDEO_LEVEL_EXTENSION_T,
    mmal.MMAL_PARAMETER_VIDEO_MAX_NUM_CALLBACKS:        mmal.MMAL_PARAMETER_UINT32_T,
    mmal.MMAL_PARAMETER_VIDEO_RENDER_STATS:             mmal.MMAL_PARAMETER_VIDEO_RENDER_STATS_T,
    mmal.MMAL_PARAMETER_VIDEO_REQUEST_I_FRAME:          mmal.MMAL_PARAMETER_BOOLEAN_T,
    mmal.MMAL_PARAMETER_VIDEO_STABILISATION:            mmal.MMAL_PARAMETER_BOOLEAN_T,
    mmal.MMAL_PARAMETER_ZERO_COPY:                      mmal.MMAL_PARAMETER_BOOLEAN_T,
    mmal.MMAL_PARAMETER_ZERO_SHUTTER_LAG:               mmal.MMAL_PARAMETER_ZEROSHUTTERLAG_T,
    mmal.MMAL_PARAMETER_ZOOM:                           mmal.MMAL_PARAMETER_SCALEFACTOR_T,
    }


class PiCameraFraction(Fraction):
    """
    Extends :class:`~fractions.Fraction` to act as a (numerator, denominator)
    tuple when required.
    """
    def __len__(self):
        warnings.warn(
            PiCameraDeprecated(
                'Accessing framerate as a tuple is deprecated; this value is '
                'now a Fraction, so you can query the numerator and '
                'denominator properties directly, convert to an int or float, '
                'or perform arithmetic operations and comparisons directly'))
        return 2

    def __getitem__(self, index):
        warnings.warn(
            PiCameraDeprecated(
                'Accessing framerate as a tuple is deprecated; this value is '
                'now a Fraction, so you can query the numerator and '
                'denominator properties directly, convert to an int or float, '
                'or perform arithmetic operations and comparisons directly'))
        if index == 0:
            return self.numerator
        elif index == 1:
            return self.denominator
        else:
            raise IndexError('invalid index %d' % index)

    def __contains__(self, value):
        return value in (self.numerator, self.denominator)


class PiCameraResolution(namedtuple('PiCameraResolution', ('width', 'height'))):
    """
    A :func:`~collections.namedtuple` derivative which represents a resolution
    with a :attr:`width` and :attr:`height`.
    """
    def __str__(self):
        return '%dx%d' % (self.width, self.height)


def to_resolution(value):
    """
    Converts *value* which may be a (width, height) tuple or a string
    containing a representation of a resolution (e.g. "1024x768" or "1080p") to
    a (width, height) tuple.
    """
    if isinstance(value, bytes):
        value = value.decode('utf-8')
    if isinstance(value, str):
        try:
            # A selection from https://en.wikipedia.org/wiki/Graphics_display_resolution
            # Feel free to suggest additions
            w, h = {
                'VGA':   (640, 480),
                'SVGA':  (800, 600),
                'XGA':   (1024, 768),
                'SXGA':  (1280, 1024),
                'UXGA':  (1600, 1200),
                'HD':    (1280, 720),
                'FHD':   (1920, 1080),
                '1080P': (1920, 1080),
                '720P':  (1280, 720),
                }[value.strip().upper()]
        except KeyError:
            w, h = (int(i.strip()) for i in value.upper().split('X', 1))
    else:
        try:
            w, h = value
        except (TypeError, ValueError):
            raise PiCameraValueError("Invalid resolution tuple: %r" % value)
    return PiCameraResolution(w, h)


def to_fraction(value, den_limit=65536):
    """
    Converts *value*, which can be any numeric type, an MMAL_RATIONAL_T, or a
    (numerator, denominator) tuple to a :class:`~fractions.Fraction` limiting
    the denominator to the range 0 < n <= *den_limit* (which defaults to
    65536).
    """
    try:
        # int, long, or fraction
        n, d = value.numerator, value.denominator
    except AttributeError:
        try:
            # float
            n, d = value.as_integer_ratio()
        except AttributeError:
            try:
                n, d = value.num, value.den
            except AttributeError:
                try:
                    # tuple
                    n, d = value
                    warnings.warn(
                        PiCameraDeprecated(
                            "Setting framerate or gains as a tuple is "
                            "deprecated; please use one of Python's many "
                            "numeric classes like int, float, Decimal, or "
                            "Fraction instead"))
                except (TypeError, ValueError):
                    # try and convert anything else to a Fraction directly
                    value = Fraction(value)
                    n, d = value.numerator, value.denominator
    # Ensure denominator is reasonable
    if d == 0:
        raise PiCameraValueError("Denominator cannot be 0")
    elif d > den_limit:
        return Fraction(n, d).limit_denominator(den_limit)
    else:
        return Fraction(n, d)


def to_rational(value):
    """
    Converts *value* to an MMAL_RATIONAL_T.
    """
    value = to_fraction(value)
    return mmal.MMAL_RATIONAL_T(value.numerator, value.denominator)


def debug_pipeline(port):
    """
    Given an :class:`MMALVideoPort` *port*, this traces all objects in the
    pipeline feeding it (including components and connections) and yields each
    object in turn. Hence the generator typically yields something like:

    * :class:`MMALVideoPort` (the specified output port)
    * :class:`MMALEncoder` (the encoder which owns the output port)
    * :class:`MMALVideoPort` (the encoder's input port)
    * :class:`MMALConnection` (the connection between the splitter and encoder)
    * :class:`MMALVideoPort` (the splitter's output port)
    * :class:`MMALSplitter` (the splitter on the camera's video port)
    * :class:`MMALVideoPort` (the splitter's input port)
    * :class:`MMALConnection` (the connection between the splitter and camera)
    * :class:`MMALVideoPort` (the camera's video port)
    * :class:`MMALCamera` (the camera component)
    """

    def find_port(addr):
        for obj in MMALObject.REGISTRY:
            if isinstance(obj, MMALControlPort):
                if ct.addressof(obj._port[0]) == addr:
                    return obj
        raise IndexError('unable to locate port with address %x' % addr)

    def find_component(addr):
        for obj in MMALObject.REGISTRY:
            if isinstance(obj, MMALComponent):
                if ct.addressof(obj._component[0]) == addr:
                    return obj
        raise IndexError('unable to locate component with address %x' % addr)

    assert isinstance(port, MMALControlPort)
    while True:
        yield port
        comp = find_component(ct.addressof(port._port[0].component[0]))
        yield comp
        if not isinstance(comp, MMALDownstreamComponent):
            break
        port = find_port(ct.addressof(comp.connection._connection[0].in_[0]))
        yield port
        yield comp.connection
        port = find_port(ct.addressof(comp.connection._connection[0].out[0]))


def print_pipeline(port):
    """
    Prints a human readable representation of the pipeline feeding the
    specified :class:`MMALVideoPort` *port*.
    """
    rows = [[], [], [], []]
    under_comp = False
    for obj in reversed(list(debug_pipeline(port))):
        if isinstance(obj, MMALComponent):
            rows[0].append(obj.name)
            under_comp = True
        elif isinstance(obj, MMALVideoPort):
            rows[0].append('[%d]' % obj._port[0].index)
            if under_comp:
                rows[1].append('encoding')
            if obj.format == mmal.MMAL_ENCODING_OPAQUE:
                rows[1].append(obj.opaque_subformat)
            else:
                rows[1].append(str(obj._port[0].format[0].encoding))
            if under_comp:
                rows[2].append('buf')
            rows[2].append('%dx%d' % (obj._port[0].buffer_num, obj._port[0].buffer_size))
            if under_comp:
                rows[3].append('frame')
                under_comp = False
            rows[3].append('%dx%d@%sfps' % (
                obj._port[0].format[0].es[0].video.width,
                obj._port[0].format[0].es[0].video.height,
                obj.framerate))
        elif isinstance(obj, MMALConnection):
            rows[0].append('')
            rows[1].append('-->')
            rows[2].append('')
            rows[3].append('')
    if under_comp:
        rows[1].append('encoding')
        rows[2].append('buf')
        rows[3].append('frame')
    cols = list(zip(*rows))
    max_lens = [max(len(s) for s in col) + 2 for col in cols]
    rows = [
        ''.join('{0:{align}{width}s}'.format(s, align=align, width=max_len)
            for s, max_len, align in zip(row, max_lens, cycle('^<^>')))
        for row in rows
        ]
    for row in rows:
        print(row)


class MMALObject(object):
    """
    Represents an object wrapper around an MMAL object (component, port,
    connection, etc). This base class maintains a registry of all MMAL objects
    currently alive (via weakrefs) which permits object lookup by name and
    listing all used MMAL objects.
    """

    REGISTRY = weakref.WeakSet()

    def __init__(self):
        super(MMALObject, self).__init__()
        self.REGISTRY.add(self)


class MMALComponent(MMALObject):
    """
    Represents a generic MMAL component. Class attributes are read to determine
    the component type, and the OPAQUE sub-formats of each connectable port.
    """

    component_type = 'none'
    opaque_input_subformats = ()
    opaque_output_subformats = ()

    def __init__(self):
        super(MMALComponent, self).__init__()
        self._component = ct.POINTER(mmal.MMAL_COMPONENT_T)()
        mmal_check(
            mmal.mmal_component_create(self.component_type, self._component),
            prefix="Failed to create MMAL component %s" % self.component_type)
        if self._component[0].input_num != len(self.opaque_input_subformats):
            raise PiCameraRuntimeError(
                'Expected %d inputs but found %d on component %s' % (
                    input_count,
                    self._components[0].input_num,
                    self.component_type))
        if self._component[0].output_num != len(self.opaque_output_subformats):
            raise PiCameraRuntimeError(
                'Expected %d inputs but found %d on component %s' % (
                    output_count,
                    self._components[0].input_num,
                    self.component_type))
        self._control = MMALControlPort(self._component[0].control)
        port_class = {
            mmal.MMAL_ES_TYPE_UNKNOWN:    MMALPort,
            mmal.MMAL_ES_TYPE_CONTROL:    MMALControlPort,
            mmal.MMAL_ES_TYPE_VIDEO:      MMALVideoPort,
            mmal.MMAL_ES_TYPE_AUDIO:      MMALAudioPort,
            mmal.MMAL_ES_TYPE_SUBPICTURE: MMALSubPicturePort,
            }
        self._inputs = tuple(
            port_class[self._component[0].input[n][0].format[0].type](
                self._component[0].input[n], opaque_subformat)
            for n, opaque_subformat in enumerate(self.opaque_input_subformats))
        self._outputs = tuple(
            port_class[self._component[0].output[n][0].format[0].type](
                self._component[0].output[n], opaque_subformat)
            for n, opaque_subformat in enumerate(self.opaque_output_subformats))

    def close(self):
        """
        Close the component and release all its resources. After this is
        called, most methods will raise exceptions if called.
        """
        if self._component:
            # ensure we free any pools associated with input/output ports
            for output in self.outputs:
                output.disable()
            for input in self.inputs:
                input.disable()
            mmal.mmal_component_destroy(self._component)
            self._component = None
            self._inputs = ()
            self._outputs = ()
            self._control = None

    @property
    def name(self):
        return self._component[0].name

    @property
    def control(self):
        """
        The :class:`MMALControlPort` control port of the component which can be
        used to configure most aspects of the component's behaviour.
        """
        return self._control

    @property
    def inputs(self):
        """
        A sequence of :class:`MMALPort` objects representing the inputs
        of the component.
        """
        return self._inputs

    @property
    def outputs(self):
        """
        A sequence of :class:`MMALPort` objects representing the outputs
        of the component.
        """
        return self._outputs

    def _get_enabled(self):
        return bool(self._component[0].is_enabled)
    def _set_enabled(self, value):
        if value:
            mmal_check(
                mmal.mmal_component_enable(self._component),
                prefix="Failed to enable component")
        else:
            mmal_check(
                mmal.mmal_component_disable(self._component),
                prefix="Failed to disable component")
    enabled = property(
        # use lambda trick to enable overriding _get_enabled, _set_enabled
        lambda self: self._get_enabled(),
        lambda self, value: self._set_enabled(value),
        doc="""\
        Retrieves or sets whether the component is currently enabled. When a
        component is disabled it does not produce or consume data. Components
        may be implicitly enabled by downstream components.
        """)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.close()

    def __repr__(self):
        if self._component:
            return '<MMALComponent "%s": %d inputs %d outputs>' % (
                self.name, len(self.inputs), len(self.outputs))
        else:
            return '<MMALComponent closed>'


class MMALControlPort(MMALObject):
    """
    Represents an MMAL port with properties to configure the port's parameters.
    """
    def __init__(self, port):
        super(MMALControlPort, self).__init__()
        self._port = port
        self._params = MMALPortParams(port)
        self._wrapper = None

    @property
    def index(self):
        """
        Returns an integer indicating the port's position within its owning
        list (inputs, outputs, etc.)
        """
        return self._port[0].index

    @property
    def enabled(self):
        """
        Returns a :class:`bool` indicating whether the port is currently
        enabled. Unlike other classes, this is a read-only property. Use
        :meth:`enable` and :meth:`disable` to modify the value.
        """
        return bool(self._port[0].is_enabled)

    def enable(self, callback=None):
        """
        Enable the port with the specified callback function (this must be
        ``None`` for connected ports, and a callable for disconnected ports).

        The callback function must accept two parameters which will be this
        :class:`MMALControlPort` (or descendent) and an :class:`MMALBuffer`
        instance. Any return value will be ignored.
        """
        def wrapper(port, buf):
            buf = MMALBuffer(buf)
            try:
                callback(self, buf)
            finally:
                buf.release()

        if not self.enabled:
            if callback:
                self._wrapper = mmal.MMAL_PORT_BH_CB_T(wrapper)
            else:
                self._wrapper = None
            mmal_check(
                mmal.mmal_port_enable(self._port, self._wrapper),
                prefix="Unable to enable port %s" % self.name)

    def disable(self):
        """
        Disable the port.
        """
        if self.enabled:
            mmal_check(
                mmal.mmal_port_disable(self._port),
                prefix="Unable to disable port %s" % self.name)
            self._wrapper = None

    def send_buffer(self, buf):
        """
        Send :class:`MMALBuffer` *buf* to the port.
        """
        mmal_check(
            mmal.mmal_port_send_buffer(self._port, buf._buf),
            prefix="unable to send the buffer to port %s" % self.name)

    def flush(self):
        """
        Flush the port.
        """
        mmal_check(
            mmal.mmal_port_flush(self._port),
            prefix="Unable to flush port %s" % self.name)

    @property
    def name(self):
        return self._port[0].name

    @property
    def params(self):
        """
        The configurable parameters for the port. This is presented as a
        mutable mapping of parameter numbers to values, implemented by the
        :class:`MMALPortParams` class.
        """
        return self._params

    def __repr__(self):
        if self._port:
            return '<MMALControlPort "%s">' % self.name
        else:
            return '<MMALControlPort closed>'


class MMALPort(MMALControlPort):
    """
    Represents an MMAL port with properties to configure and update the port's
    format. This is the base class of :class:`MMALVideoPort`,
    :class:`MMALAudioPort`, and :class:`MMALSubPicturePort`.
    """
    def __init__(self, port, opaque_subformat='OPQV'):
        super(MMALPort, self).__init__(port)
        self.opaque_subformat = opaque_subformat
        self._pool = None
        self._stopped = True

    def _get_opaque_subformat(self):
        return self._opaque_subformat
    def _set_opaque_subformat(self, value):
        self._opaque_subformat = value
    opaque_subformat = property(
        _get_opaque_subformat, _set_opaque_subformat, doc="""\
        Retrieves or sets the opaque sub-format that the port speaks. While
        most formats (I420, RGBA, etc.) mean one thing, the opaque format is
        special; different ports produce different sorts of data when
        configured for OPQV format. This property stores a string which
        uniquely identifies what the associated port means for OPQV format.

        If the port does not support opaque format at all, set this property to
        ``None``.

        :class:`MMALConnection` uses this information when negotiating formats
        for a connection between two ports.
        """)

    def _get_format(self):
        result = self._port[0].format[0].encoding
        if FIX_RGB_BGR_ORDER:
            return {
                mmal.MMAL_ENCODING_RGB24: mmal.MMAL_ENCODING_BGR24,
                mmal.MMAL_ENCODING_BGR24: mmal.MMAL_ENCODING_RGB24,
                }.get(result.value, result)
        else:
            return result
    def _set_format(self, value):
        if FIX_RGB_BGR_ORDER:
            value = {
                mmal.MMAL_ENCODING_RGB24: mmal.MMAL_ENCODING_BGR24,
                mmal.MMAL_ENCODING_BGR24: mmal.MMAL_ENCODING_RGB24,
                }.get(value, value)
        self._port[0].format[0].encoding = value
        if value == mmal.MMAL_ENCODING_OPAQUE:
            self._port[0].format[0].encoding_variant = mmal.MMAL_ENCODING_I420
    format = property(_get_format, _set_format, doc="""\
        Retrieves or sets the encoding format of the port. Setting this
        attribute implicitly sets the encoding variant to a sensible value
        (I420 in the case of OPAQUE).

        After setting this attribute, call :meth:`commit` to make the changes
        effective.
        """)

    @property
    def supported_formats(self):
        """
        Retrieves a sequence of supported encodings on this port.

        .. warning::

            This property does not work on the camera's still port
            (``MMALCamera.outputs[2]``) due to an underlying firmware bug.
        """
        mp = self.params[mmal.MMAL_PARAMETER_SUPPORTED_ENCODINGS]
        return [
            mmal.MMAL_FOURCC_T(v)
            for v in mp.encoding
            if v != 0
            ][:mp.hdr.size // ct.sizeof(ct.c_uint32)]

    def _get_bitrate(self):
        return self._port[0].format[0].bitrate
    def _set_bitrate(self, value):
        self._port[0].format[0].bitrate = value
    bitrate = property(_get_bitrate, _set_bitrate, doc="""\
        Retrieves or sets the bitrate limit for the port's format.
        """)

    def copy_from(self, source):
        """
        Copies the port's :attr:`format` from the *source*
        :class:`MMALControlPort`.
        """
        mmal.mmal_format_copy(self._port[0].format, source._port[0].format)

    def commit(self):
        """
        Commits the port's configuration and automatically updates the number
        and size of associated buffers. This is typically called after
        adjusting the port's format and/or associated settings (like width and
        height for video ports).
        """
        mmal_check(
            mmal.mmal_port_format_commit(self._port),
            prefix="Format couldn't be set on port %s" % self.name)
        # Workaround: Unfortunately, there is an upstream issue with the
        # buffer_num_recommended which means it can't currently be used (see
        # discussion in raspberrypi/userland#167). There's another upstream
        # issue with buffer_num_min which means we need to guard against 0
        # values...
        self._port[0].buffer_num = max(1, self._port[0].buffer_num_min)
        self._port[0].buffer_size = self._port[0].buffer_size_recommended

    @property
    def pool(self):
        """
        Returns the :class:`MMALPool` associated with the buffer, if any.
        """
        return self._pool

    @property
    def buffer_count(self):
        return self._port[0].buffer_num

    @property
    def buffer_size(self):
        return self._port[0].buffer_size

    def enable(self, callback=None):
        """
        Enable the port with the specified callback function (this must be
        ``None`` for connected ports, and a callable for disconnected ports).

        The callback function must accept two parameters which will be this
        :class:`MMALControlPort` (or descendent) and an :class:`MMALBuffer`
        instance. The callback should return ``True`` when processing is
        complete and no further calls are expected (e.g. at frame-end for an
        image encoder), and ``False`` otherwise.
        """
        def wrapper(port, buf):
            buf = MMALBuffer(buf)
            try:
                if not self._stopped and callback(self, buf):
                    self._stopped = True
            finally:
                buf.release()
                if not self._stopped:
                    self._pool.send_buffer()

        if not self.enabled:
            # Workaround: There is a bug in the MJPEG encoder that causes a
            # deadlock if the FIFO is full on shutdown. Increasing the encoder
            # buffer size makes this less likely to happen. See
            # raspberrypi/userland#208. Connecting the encoder component resets
            # the output port's buffer size, hence why we correct this here,
            # just before enabling the port.
            if self._port[0].format[0].encoding == mmal.MMAL_ENCODING_MJPEG:
                self._port[0].buffer_size = max(512 * 1024, self._port[0].buffer_size_recommended)
            if callback:
                assert self._stopped
                self._stopped = False
                self._wrapper = mmal.MMAL_PORT_BH_CB_T(wrapper)
                mmal_check(
                    mmal.mmal_port_enable(self._port, self._wrapper),
                    prefix="Unable to enable port %s" % self.name)
                assert self._pool is None
                self._pool = MMALPortPool(self)
                # If this port is an output port, send it all the buffers
                # in the pool. If it's an input port, don't bother: the user
                # will presumably want to feed buffers to it manually
                if self._port[0].type == mmal.MMAL_PORT_TYPE_OUTPUT:
                    try:
                        self._pool.send_all_buffers(self)
                    except:
                        self._pool.close()
                        self._pool = None
                        raise
            else:
                super(MMALPort, self).enable()

    def disable(self):
        """
        Disable the port.
        """
        self._stopped = True
        super(MMALPort, self).disable()
        if self._pool:
            self._pool.close()
            self._pool = None

    def __repr__(self):
        if self._port:
            return '<MMALPort "%s": format=%r buffers=%dx%d>' % (
                self.name, self.format, self.buffer_count, self.buffer_size)
        else:
            return '<MMALPort closed>'


class MMALVideoPort(MMALPort):
    """
    Represents an MMAL port used to pass video data.
    """

    def _get_framesize(self):
        return PiCameraResolution(
            self._port[0].format[0].es[0].video.crop.width,
            self._port[0].format[0].es[0].video.crop.height,
            )
    def _set_framesize(self, value):
        value = to_resolution(value)
        video = self._port[0].format[0].es[0].video
        video.width = mmal.VCOS_ALIGN_UP(value.width, 32)
        video.height = mmal.VCOS_ALIGN_UP(value.height, 16)
        video.crop.width = value.width
        video.crop.height = value.height
    framesize = property(_get_framesize, _set_framesize, doc="""\
        Retrieves or sets the size of the port's video frames as a (width,
        height) tuple. This attribute implicitly handles scaling the given
        size up to the block size of the camera (32x16).

        After setting this attribute, call :meth:`~MMALPort.commit` to make the
        changes effective.
        """)

    def _get_framerate(self):
        video = self._port[0].format[0].es[0].video
        try:
            return Fraction(
                video.frame_rate.num,
                video.frame_rate.den)
        except ZeroDivisionError:
            return Fraction(0, 1)
    def _set_framerate(self, value):
        value = to_fraction(value)
        video = self._port[0].format[0].es[0].video
        video.frame_rate.num = value.numerator
        video.frame_rate.den = value.denominator
    framerate = property(_get_framerate, _set_framerate, doc="""\
        Retrieves or sets the framerate of the port's video frames in fps.

        After setting this attribute, call :meth:`~MMALPort.commit` to make the
        changes effective.
        """)

    def __repr__(self):
        if self._port:
            return '<MMALVideoPort "%s": format=%r buffers=%dx%d frames=%s@%sfps>' % (
                self.name, self.format, self._port[0].buffer_num,
                self._port[0].buffer_size, self.framesize, self.framerate)
        else:
            return '<MMALVideoPort closed>'


class MMALAudioPort(MMALPort):
    """
    Represents an MMAL port used to pass audio data.
    """

    def __repr__(self):
        if self._port:
            return '<MMALAudioPort "%s": format=%r buffers=%dx%d>' % (
                self.name, self.format, self._port[0].buffer_num,
                self._port[0].buffer_size)
        else:
            return '<MMALAudioPort closed>'


class MMALSubPicturePort(MMALPort):
    """
    Represents an MMAL port used to pass sub-picture (caption) data.
    """

    def __repr__(self):
        if self._port:
            return '<MMALSubPicturePort "%s": format=%r buffers=%dx%d>' % (
                self.name, self.format, self._port[0].buffer_num,
                self._port[0].buffer_size)
        else:
            return '<MMALSubPicturePort closed>'


class MMALPortParams(object):
    """
    Represents the parameters of an MMAL port. This class implements the
    :attr:`MMALControlPort.params` attribute.

    Internally, the class understands how to convert certain structures to more
    common Python data-types. For example, parameters that expect an
    MMAL_RATIONAL_T type will return and accept Python's
    :class:`~fractions.Fraction` class (or any other numeric types), while
    parameters that expect an MMAL_BOOL_T type will treat anything as a truthy
    value. Parameters that expect the MMAL_PARAMETER_STRING_T structure will be
    treated as plain strings, and likewise MMAL_PARAMETER_INT32_T and similar
    structures will be treated as plain ints.

    Parameters that expect more complex structures will return and expect
    those structures verbatim.
    """
    def __init__(self, port):
        super(MMALPortParams, self).__init__()
        self._port = port

    def __getitem__(self, key):
        dtype = PARAM_TYPES[key]
        # Use the short-cut functions where possible (teeny bit faster if we
        # get some C to do the structure wrapping for us)
        func = {
            mmal.MMAL_PARAMETER_RATIONAL_T: mmal.mmal_port_parameter_get_rational,
            mmal.MMAL_PARAMETER_BOOLEAN_T:  mmal.mmal_port_parameter_get_boolean,
            mmal.MMAL_PARAMETER_INT32_T:    mmal.mmal_port_parameter_get_int32,
            mmal.MMAL_PARAMETER_INT64_T:    mmal.mmal_port_parameter_get_int64,
            mmal.MMAL_PARAMETER_UINT32_T:   mmal.mmal_port_parameter_get_uint32,
            mmal.MMAL_PARAMETER_UINT64_T:   mmal.mmal_port_parameter_get_uint64,
            }.get(dtype, mmal.mmal_port_parameter_get)
        conv = {
            mmal.MMAL_PARAMETER_RATIONAL_T: lambda v: Fraction(v.num, v.den),
            mmal.MMAL_PARAMETER_BOOLEAN_T:  lambda v: v.value != mmal.MMAL_FALSE,
            mmal.MMAL_PARAMETER_INT32_T:    lambda v: v.value,
            mmal.MMAL_PARAMETER_INT64_T:    lambda v: v.value,
            mmal.MMAL_PARAMETER_UINT32_T:   lambda v: v.value,
            mmal.MMAL_PARAMETER_UINT64_T:   lambda v: v.value,
            mmal.MMAL_PARAMETER_STRING_T:   lambda v: v.str.decode('ascii'),
            }.get(dtype, lambda v: v)
        if func == mmal.mmal_port_parameter_get:
            result = dtype(
                mmal.MMAL_PARAMETER_HEADER_T(key, ct.sizeof(dtype))
                )
            mmal_check(
                func(self._port, result.hdr),
                prefix="Failed to get parameter %d" % key)
        else:
            dtype = {
                mmal.MMAL_PARAMETER_RATIONAL_T: mmal.MMAL_RATIONAL_T,
                mmal.MMAL_PARAMETER_BOOLEAN_T:  mmal.MMAL_BOOL_T,
                mmal.MMAL_PARAMETER_INT32_T:    ct.c_int32,
                mmal.MMAL_PARAMETER_INT64_T:    ct.c_int64,
                mmal.MMAL_PARAMETER_UINT32_T:   ct.c_uint32,
                mmal.MMAL_PARAMETER_UINT64_T:   ct.c_uint64,
                }[dtype]
            result = dtype()
            mmal_check(
                func(self._port, key, result),
                prefix="Failed to get parameter %d" % key)
        return conv(result)

    def __setitem__(self, key, value):
        dtype = PARAM_TYPES[key]
        func = {
            mmal.MMAL_PARAMETER_RATIONAL_T: mmal.mmal_port_parameter_set_rational,
            mmal.MMAL_PARAMETER_BOOLEAN_T:  mmal.mmal_port_parameter_set_boolean,
            mmal.MMAL_PARAMETER_INT32_T:    mmal.mmal_port_parameter_set_int32,
            mmal.MMAL_PARAMETER_INT64_T:    mmal.mmal_port_parameter_set_int64,
            mmal.MMAL_PARAMETER_UINT32_T:   mmal.mmal_port_parameter_set_uint32,
            mmal.MMAL_PARAMETER_UINT64_T:   mmal.mmal_port_parameter_set_uint64,
            mmal.MMAL_PARAMETER_STRING_T:   mmal.mmal_port_parameter_set_string,
            }.get(dtype, mmal.mmal_port_parameter_set)
        conv = {
            mmal.MMAL_PARAMETER_RATIONAL_T: lambda v: to_rational(v),
            mmal.MMAL_PARAMETER_BOOLEAN_T:  lambda v: mmal.MMAL_TRUE if v else mmal.MMAL_FALSE,
            mmal.MMAL_PARAMETER_STRING_T:   lambda v: v.encode('ascii'),
            }.get(dtype, lambda v: v)
        if func == mmal.mmal_port_parameter_set:
            mp = conv(value)
            assert mp.hdr.id == key
            assert mp.hdr.size >= ct.sizeof(dtype)
            mmal_check(
                func(self._port, mp.hdr),
                prefix="Failed to set parameter %d to %r" % (key, value))
        else:
            mmal_check(
                func(self._port, key, conv(value)),
                prefix="Failed to set parameter %d to %r" % (key, value))


class MMALBuffer(object):
    """
    Represents an MMAL buffer header. This is usually constructed from the
    buffer header pointer and is largely supplied simply to make working with
    the buffer's data a bit simpler; accessing the :attr:`data` attribute
    implicitly locks the buffer's memory and returns the data as a bytes
    string.
    """
    def __init__(self, buf):
        super(MMALBuffer, self).__init__()
        self._buf = buf

    @property
    def command(self):
        """
        Returns the command set in the buffer's meta-data. This is usually 0
        for buffers returned by an encoder; typically this is only used by
        buffers sent to the callback of a control port.
        """
        return self._buf[0].cmd

    @property
    def flags(self):
        """
        Returns the flags set in the buffer's meta-data.
        """
        return self._buf[0].flags

    @property
    def pts(self):
        """
        Returns the presentation timestamp (PTS) of the buffer.
        """
        return self._buf[0].pts

    @property
    def dts(self):
        """
        Returns the decoding timestamp (DTS) of the buffer.
        """
        return self._buf[0].dts

    @property
    def size(self):
        """
        Returns the length of the buffer's data area in bytes. This will be
        greater than or equal to :attr:`length` and is fixed in value.
        """
        return self._buf[0].alloc_size

    @property
    def length(self):
        """
        Returns the length of data held in the buffer. This is equal to calling
        :func:`len` on :attr:`data` but faster (as retrieving the buffer's data
        requires memory locks in certain cases).
        """
        return self._buf[0].length

    @property
    def data(self):
        """
        Returns the data held in the buffer as a :class:`bytes` string.
        """
        # dirty hack; we could do pointer arithmetic with offset but it's
        # rather long-winded in Python and this method needs to be *fast*
        assert self._buf[0].offset == 0
        mmal_check(
            mmal.mmal_buffer_header_mem_lock(self._buf),
            prefix='unable to lock buffer header memory')
        try:
            return ct.string_at(self._buf[0].data, self._buf[0].length)
        finally:
            mmal.mmal_buffer_header_mem_unlock(self._buf)

    def update(self, data):
        """
        Overwrites the :attr:`data` in the buffer. The *data* parameter is an
        object supporting the buffer protocol which contains up to
        :attr:`size` bytes.

        .. warning::

            Some buffer objects *cannot* be modified without consequence (for
            example, buffers returned by an encoder's output port).
        """
        if isinstance(data, memoryview) and (data.ndim > 1 or data.itemsize > 1):
            data = data.cast('B')
        bp = ct.c_uint8 * len(data)
        try:
            sp = bp.from_buffer(data)
        except TypeError:
            sp = bp.from_buffer_copy(data)
        ct.memmove(self._buf[0].data, sp, len(data))
        self._buf[0].length = len(data)

    def copy(self, data=None):
        """
        Return a copy of this buffer header, optionally replacing the
        :attr:`data` attribute with *data* which must be an object supporting
        the buffer protocol.
        """
        result = MMALBuffer(ct.pointer(mmal.MMAL_BUFFER_HEADER_T.from_buffer_copy(self._buf[0])))
        if data is not None:
            bp = ct.c_uint8 * len(data)
            try:
                sp = bp.from_buffer(data)
            except TypeError:
                sp = bp.from_buffer_copy(data)
            result._buf[0].length = len(data)
            result._buf[0].data = ct.cast(ct.pointer(sp), ct.POINTER(ct.c_uint8))
        return result

    def acquire(self):
        mmal.mmal_buffer_header_acquire(self._buf)

    def release(self):
        mmal.mmal_buffer_header_release(self._buf)

    def reset(self):
        mmal.mmal_buffer_header_reset(self._buf)

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.release()

    def __repr__(self):
        if self._buf:
            return '<MMALBuffer object: flags=%s length=%d>' % (
                ''.join((
                'E' if self.flags & mmal.MMAL_BUFFER_HEADER_FLAG_FRAME_END     else '_',
                'K' if self.flags & mmal.MMAL_BUFFER_HEADER_FLAG_KEYFRAME      else '_',
                'C' if self.flags & mmal.MMAL_BUFFER_HEADER_FLAG_CONFIG        else '_',
                'M' if self.flags & mmal.MMAL_BUFFER_HEADER_FLAG_CODECSIDEINFO else '_',
                'X' if self.flags & mmal.MMAL_BUFFER_HEADER_FLAG_EOS           else '_',
                )), self.length)
        else:
            return '<MMALBuffer object: ???>'


class MMALPool(object):
    """
    Construct an MMAL pool containing *num* buffer headers of *size* bytes.
    """
    def __init__(self, pool):
        super(MMALPool, self).__init__()
        self._pool = pool

    def close(self):
        if self._pool is not None:
            mmal.mmal_pool_destroy(self._pool)
            self._pool = None

    def get_buffer(self):
        """
        Get the next buffer from the pool.
        """
        buf = mmal.mmal_queue_get(self._pool[0].queue)
        if not buf:
            raise PiCameraRuntimeError('failed to get a buffer from the pool')
        return MMALBuffer(buf)

    def send_buffer(self, port):
        """
        Get a buffer from the pool and send it to *port*.
        """
        port.send_buffer(self.get_buffer())

    def send_all_buffers(self, port):
        """
        Send all buffers from the pool to *port*.
        """
        for i in range(mmal.mmal_queue_length(self._pool[0].queue)):
            port.send_buffer(self.get_buffer())


class MMALPortPool(MMALPool):
    """
    Construct an MMAL pool for the number and size of buffers required by
    the :class:`MMALPort` *port*.
    """

    def __init__(self, port):
        pool = mmal.mmal_port_pool_create(
            port._port, port._port[0].buffer_num, port._port[0].buffer_size)
        if not pool:
            raise PiCameraRuntimeError(
                'failed to create buffer header pool for port %s' % port.name)
        super(MMALPortPool, self).__init__(pool)
        self._port = port

    def close(self):
        if self._pool:
            mmal.mmal_port_pool_destroy(self._port._port, self._pool)
            self._port = None
            self._pool = None

    @property
    def port(self):
        return self._port

    def send_buffer(self):
        """
        Get a buffer from the pool and send it to the port the pool is
        associated with.
        """
        self._port.send_buffer(self.get_buffer())

    def send_all_buffers(self, port):
        """
        Send all buffers from the pool to the port the pool is associated
        with.
        """
        for i in range(mmal.mmal_queue_length(self._pool[0].queue)):
            self._port.send_buffer(self.get_buffer())


class MMALConnection(MMALObject):
    """
    Represents an MMAL internal connection between two components. The
    constructor accepts arguments providing the *source* :class:`MMALPort` and
    *target* :class:`MMALPort`.

    The connection will automatically negotiate the most efficient format
    supported by both ports (implicitly handling the incompatibility of some
    OPAQUE sub-formats). See :ref:`under_the_hood` for more information.
    """
    compatible_formats = {
        (f, f) for f in (
            'OPQV-single',
            'OPQV-dual',
            'OPQV-strips',
            'I420')
        } | {
        ('OPQV-dual', 'OPQV-single'),
        ('OPQV-single', 'OPQV-dual'), # recent firmwares permit this
        }

    def __init__(self, source, target):
        super(MMALConnection, self).__init__()
        self._connection = ct.POINTER(mmal.MMAL_CONNECTION_T)()
        if (source.opaque_subformat, target.opaque_subformat) in self.compatible_formats:
            source.format = mmal.MMAL_ENCODING_OPAQUE
        else:
            source.format = mmal.MMAL_ENCODING_I420
        source.commit()
        mmal_check(
            mmal.mmal_connection_create(
                self._connection, source._port, target._port,
                mmal.MMAL_CONNECTION_FLAG_TUNNELLING |
                mmal.MMAL_CONNECTION_FLAG_ALLOCATION_ON_INPUT),
            prefix="Failed to create connection")
        mmal_check(
            mmal.mmal_connection_enable(self._connection),
            prefix="Failed to enable connection")

    def close(self):
        if self._connection is not None:
            mmal.mmal_connection_destroy(self._connection)
            self._connection = None

    def _get_enabled(self):
        return bool(self._connection[0].is_enabled)
    def _set_enabled(self, value):
        if value:
            mmal_check(
                mmal.mmal_connection_enable(self._connection),
                prefix="Failed to enable connection")
        else:
            mmal_check(
                mmal.mmal_connection_disable(self._connection),
                prefix="Failed to disable connection")
    enabled = property(_get_enabled, _set_enabled)

    @property
    def name(self):
        return self._connection[0].name

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.close()

    def __repr__(self):
        if self._connection:
            return '<MMALConnection "%s">' % self._connection[0].name
        else:
            return '<MMALConnection closed>'


class MMALCamera(MMALComponent):
    """
    Represents the MMAL camera component.

    The intended use of the output ports (which in turn determines the
    behaviour of those ports) is as follows:

    * Port 0 is intended for preview renderers

    * Port 1 is intended for video recording

    * Port 2 is intended for still image capture
    """

    component_type = mmal.MMAL_COMPONENT_DEFAULT_CAMERA
    opaque_output_subformats = ('OPQV-single', 'OPQV-dual', 'OPQV-strips')

    annotate_structs = (
        mmal.MMAL_PARAMETER_CAMERA_ANNOTATE_T,
        mmal.MMAL_PARAMETER_CAMERA_ANNOTATE_V2_T,
        mmal.MMAL_PARAMETER_CAMERA_ANNOTATE_V3_T,
        )

    def __init__(self):
        global FIX_RGB_BGR_ORDER
        super(MMALCamera, self).__init__()
        if PARAM_TYPES[mmal.MMAL_PARAMETER_ANNOTATE] is None:
            found = False
            # try largest struct to smallest as later firmwares still happily
            # accept earlier revision structures
            # XXX do old firmwares reject too-large structs?
            for struct in reversed(MMALCamera.annotate_structs):
                try:
                    PARAM_TYPES[mmal.MMAL_PARAMETER_ANNOTATE] = struct
                    self.control.params[mmal.MMAL_PARAMETER_ANNOTATE]
                except PiCameraMMALError:
                    pass
                else:
                    found = True
                    break
            if not found:
                PARAM_TYPES[mmal.MMAL_PARAMETER_ANNOTATE] = None
                raise PiCameraMMALError(
                        mmal.MMAL_EINVAL, "unknown camera annotation structure revision")
        if FIX_RGB_BGR_ORDER is None:
            try:
                self.outputs[2].supported_formats
            except PiCameraMMALError:
                # old firmware lists BGR24 before RGB24 in supported_formats
                for f in self.outputs[1].supported_formats:
                    if f == mmal.MMAL_ENCODING_BGR24:
                        FIX_RGB_BGR_ORDER = True
                        break
                    elif f == mmal.MMAL_ENCODING_RGB24:
                        FIX_RGB_BGR_ORDER = False
                        break
            else:
                # old firmware has a bug which prevents supported_formats
                # working on the still port
                FIX_RGB_BGR_ORDER = False

    def _get_annotate_rev(self):
        try:
            return MMALCamera.annotate_structs.index(PARAM_TYPES[mmal.MMAL_PARAMETER_ANNOTATE]) + 1
        except IndexError:
            raise PiCameraMMALError(
                    mmal.MMAL_EINVAL, "unknown camera annotation structure revision")
    def _set_annotate_rev(self, value):
        try:
            PARAM_TYPES[mmal.MMAL_PARAMETER_ANNOTATE] = MMALCamera.annotate_structs[value - 1]
        except IndexError:
            raise PiCameraMMALError(
                mmal.MMAL_EINVAL, "invalid camera annotation structure revision")
    annotate_rev = property(_get_annotate_rev, _set_annotate_rev, doc="""\
        The annotation capabilities of the firmware have evolved over time and
        several structures are available for querying and setting video
        annotations. By default the :class:`MMALCamera` class will pick the
        latest annotation structure supported by the current firmware but you
        can select older revisions with :attr:`annotate_rev` for other purposes
        (e.g. testing).
        """)


class MMALCameraInfo(MMALComponent):
    """
    Represents the MMAL camera-info component.
    """
    component_type = mmal.MMAL_COMPONENT_DEFAULT_CAMERA_INFO

    info_structs = (
        mmal.MMAL_PARAMETER_CAMERA_INFO_T,
        mmal.MMAL_PARAMETER_CAMERA_INFO_V2_T,
        )

    def __init__(self):
        super(MMALCameraInfo, self).__init__()
        if PARAM_TYPES[mmal.MMAL_PARAMETER_CAMERA_INFO] is None:
            found = False
            # try smallest structure to largest as later firmwares reject
            # older structures
            for struct in MMALCameraInfo.info_structs:
                try:
                    PARAM_TYPES[mmal.MMAL_PARAMETER_CAMERA_INFO] = struct
                    self.control.params[mmal.MMAL_PARAMETER_CAMERA_INFO]
                except PiCameraMMALError:
                    pass
                else:
                    found = True
                    break
            if not found:
                PARAM_TYPES[mmal.MMAL_PARAMETER_CAMERA_INFO] = None
                raise PiCameraMMALError(
                        mmal.MMAL_EINVAL, "unknown camera info structure revision")

    def _get_info_rev(self):
        try:
            return MMALCameraInfo.info_structs.index(PARAM_TYPES[mmal.MMAL_PARAMETER_CAMERA_INFO]) + 1
        except IndexError:
            raise PiCameraMMALError(
                    mmal.MMAL_EINVAL, "unknown camera info structure revision")
    def _set_info_rev(self, value):
        try:
            PARAM_TYPES[mmal.MMAL_PARAMETER_CAMERA_INFO] = MMALCameraInfo.info_structs[value - 1]
        except IndexError:
            raise PiCameraMMALError(
                mmal.MMAL_EINVAL, "invalid camera info structure revision")
    info_rev = property(_get_info_rev, _set_info_rev, doc="""\
        The camera information capabilities of the firmware have evolved over
        time and several structures are available for querying camera
        information. When initialized, :class:`MMALCameraInfo` will attempt
        to discover which structure is in use by the extant firmware. This
        property can be used to discover the structure version and to modify
        the version in use for other purposes (e.g. testing).
        """)


class MMALDownstreamComponent(MMALComponent):
    """
    Represents an MMAL component that acts as a filter of some sort, with a
    single input that connects to an upstream source port. This is an asbtract
    base class.
    """
    def __init__(self):
        super(MMALDownstreamComponent, self).__init__()
        assert len(self.opaque_input_subformats) == 1
        self._connection = None

    def connect(self, source):
        if self.connection:
            self.disconnect()
        self._connection = MMALConnection(source, self.inputs[0])

    def disconnect(self):
        if self.connection:
            self.connection.close()
            self._connection = None

    def close(self):
        self.disconnect()
        super(MMALDownstreamComponent, self).close()

    def _set_enabled(self, value):
        if value:
            super(MMALDownstreamComponent, self)._set_enabled(True)
            if self.connection:
                self.connection.enabled = True
        else:
            if self.connection:
                self.connection.enabled = False
            super(MMALDownstreamComponent, self)._set_enabled(False)

    @property
    def connection(self):
        return self._connection


class MMALSplitter(MMALDownstreamComponent):
    """
    Represents the MMAL splitter component.
    """
    component_type = mmal.MMAL_COMPONENT_DEFAULT_VIDEO_SPLITTER
    opaque_input_subformats = ('OPQV-single',)
    opaque_output_subformats = ('OPQV-single',) * 4


class MMALResizer(MMALDownstreamComponent):
    """
    Represents the MMAL resizer component.
    """
    component_type = mmal.MMAL_COMPONENT_DEFAULT_RESIZER
    opaque_input_subformats = (None,)
    opaque_output_subformats = (None,)


class MMALEncoder(MMALDownstreamComponent):
    """
    Represents a generic MMAL encoder. This is an abstract base class.
    """


class MMALVideoEncoder(MMALEncoder):
    """
    Represents the MMAL video encoder component.
    """
    component_type = mmal.MMAL_COMPONENT_DEFAULT_VIDEO_ENCODER
    opaque_input_subformats = ('OPQV-dual',)
    opaque_output_subformats = (None,)


class MMALImageEncoder(MMALEncoder):
    """
    Represents the MMAL image encoder component.
    """
    component_type = mmal.MMAL_COMPONENT_DEFAULT_IMAGE_ENCODER
    opaque_input_subformats = ('OPQV-strips',)
    opaque_output_subformats = (None,)


class MMALRenderer(MMALDownstreamComponent):
    """
    Represents the MMAL preview renderer component.
    """
    component_type = mmal.MMAL_COMPONENT_DEFAULT_VIDEO_RENDERER
    opaque_input_subformats = ('OPQV-single',)


class MMALNullSink(MMALDownstreamComponent):
    """
    Represents the MMAL null-sink component.
    """
    component_type = mmal.MMAL_COMPONENT_DEFAULT_NULL_SINK
    opaque_input_subformats = ('OPQV-single',)

