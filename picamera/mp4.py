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

# Make Py2's str and range equivalent to Py3's
str = type('')

from pymp4.parser import Box, UNITY_MATRIX
from construct import Container
from collections import namedtuple
from io import BytesIO
import struct


NAL_TYPE_SPS = 7 # NAL type for a sequence parameter set
NAL_TYPE_PPS = 8 # NAL type for a picture parameter set


SPSIndications = namedtuple('SPSIndications', ('profile', 'compatibility', 'level'))
NALSizePatch = namedtuple('NALSizePatch', ('offset_in_mdat', 'size_to_write'))

DEFAULT_SPS_INDICATIONS = SPSIndications(profile=100, compatibility=0, level=40)

def nal_get_unit_type(nal_data):
    # The first NAL byte has this structure:
    #   1 forbidden bit (0)
    #   2 bits for nal ref idc
    #   5 bits for nal type
    return nal_data[0] & ((1 << 5) - 1)


def sps_get_indications(nal_data):
    assert(nal_get_unit_type(nal_data) == NAL_TYPE_SPS)
    # After the nal type, follows the profile_idc, the "constraint set", aka
    # the compatibility byte, followed by level_idc
    return SPSIndications(profile=nal_data[1], compatibility=nal_data[2], level=nal_data[3])


STATIC_FTYP = Box.build(
    Container(type=b'ftyp')(
        major_brand=b'isom')(
        minor_version=0x200)(
        compatible_brands=[b'isom', b'iso2', b'avc1', b'mp41']))


STATIC_EMPTY_MDAT = Box.build(Container(type=b'mdat')(data=b''))



class MP4Muxer(object):
    def __init__(self):
        super(MP4Muxer, self).__init__()
        self.indications = None
        self.pic_parm_sets = set()
        self.seq_parm_sets = set()
        self.current_mdat_size = 0

        self._sample_sizes = []
        self._nal_size_patches = []
        self._sps_header_buffer = BytesIO()
        self._last_frame_was_sps = False
        self.current_frame_size = 0

    def _write(self, data):
        pass

    def _seek(self, offset):
        pass


    def begin(self):
        self._output_mp4_header()


    def end(self, framerate, resolution):
        self._output_mp4_footer(framerate, resolution)
        self._patch_mdat_size()
        self._patch_nal_sizes()


    @property
    def mdat_offset(self):
        return len(STATIC_FTYP)


    @property
    def mdat_payload_offset(self):
        return self.mdat_offset + len(STATIC_EMPTY_MDAT)


    @property
    def nal_prefix(self):
        return b'\x00\x00\x00\x01'


    def _flush_sps_header_buffer(self, length):
        self._sps_header_buffer.seek(0)
        retval = self._sps_header_buffer.read(length)
        self._sps_header_buffer.seek(0)
        return retval


    def _record_frame_size(self, frame_size, frame_is_sps_header):
        # SPS headers gets a special treatment and they're considered part
        # of the next frame, as far as MP4 is concerned
        if self._last_frame_was_sps:
            self._sample_sizes[-1] += frame_size
        else:
            self._sample_sizes.append(frame_size)
        if not frame_is_sps_header:
            # SPS headers are already patched by process_sps_header. Normal
            # frames are not cached, so we can't patch their size in advance.
            # So we store the patch information and we fix up the stream
            # afterwards, to avoid seeking now.
            self._nal_size_patches.append(NALSizePatch(
                offset_in_mdat=self.current_mdat_size,
                size_to_write=frame_size - len(self.nal_prefix)))
            # We subtract the len of the NAL prefix because that is not part of the
            # length field in this case.
        # Finally, increment the total mdat size and update the internal flag
        self.current_mdat_size += frame_size
        self._last_frame_was_sps = frame_is_sps_header


    def _process_sps_header(self, sps_header_data):
        assert(sps_header_data.startswith(self.nal_prefix))
        # We remove the first element because it's going to be empty,
        # since the header starts with the NAL prefix
        nal_units = sps_header_data.split(self.nal_prefix)[1:]
        for nal_unit in nal_units:
            # Write to the stream the length of the nal unit. If in the native
            # architecture 'I' is more than a 32 bit integer, truncate
            self._write(struct.pack('>I', len(nal_unit))[-len(self.nal_prefix):])
            self._write(nal_unit)
            # Special treatment for SPS and PPS
            nal_type = nal_get_unit_type(nal_unit)
            if nal_type == NAL_TYPE_PPS:
                self.pic_parm_sets.add(nal_unit)
            elif nal_type == NAL_TYPE_SPS:
                self.seq_parm_sets.add(nal_unit)
                # For SPS, also extract the indications if needed
                if self.indications is None:
                    self.indications = sps_get_indications(nal_unit)


    def _output_mp4_header(self):
        self._write(STATIC_FTYP)
        self._write(STATIC_EMPTY_MDAT)


    def _patch_mdat_size(self):
        # Move to the position where the mdat size was
        self._seek(self.mdat_offset)
        # Write the actual mdat size as big endian 32 bit integer
        self._write(struct.pack('>I',
            self.current_mdat_size + len(STATIC_EMPTY_MDAT))[-4:]
        )


    def _patch_nal_sizes(self):
        for offset_in_mdat, size_to_write in self._nal_size_patches:
            self._seek(self.mdat_payload_offset + offset_in_mdat)
            # Write the actual mdat size as big endian 32 bit integer
            self._write(struct.pack('>I', size_to_write)[-len(self.nal_prefix):])


    def append(self, data, frame_is_sps_header, frame_is_complete):
        self.current_frame_size += len(data)

        # Sps gets special treatment because it goes first in a buffer
        if frame_is_sps_header:
            self._sps_header_buffer.write(data)
            if frame_is_complete:
                # Flush the SPS header and reset the buffer
                self._process_sps_header(self._flush_sps_header_buffer(self.current_frame_size))
        else:
            # Direct to output
            self._write(data)

        if frame_is_complete:
            # Store the size for this sample and reset the current one
            self._record_frame_size(self.current_frame_size, frame_is_sps_header)
            self.current_frame_size = 0

    def _output_mp4_footer(self, framerate, resolution):
        # Extact all the variables used after in the construction of the boxes
        sample_count = len(self._sample_sizes)
        timescale = framerate.numerator
        sample_delta = framerate.denominator
        duration = sample_count * sample_delta
        chunk_offset = self.mdat_payload_offset
        width = resolution[0]
        height = resolution[1]
        profile, compatibility, level = DEFAULT_SPS_INDICATIONS if self.indications is None else self.indications
        sample_sizes = self._sample_sizes
        sps = list(self.seq_parm_sets)
        pps = list(self.pic_parm_sets)

        # Build all the boxes we need
        HDLR = Container(type=b'hdlr')
        HDLR(version=0)
        HDLR(flags=0)
        HDLR(handler_type=b'vide')
        HDLR(name='VideoHandler')

        MDHD = Container(type=b'mdhd')
        MDHD(version=0)
        MDHD(flags=0)
        MDHD(creation_time=0)
        MDHD(modification_time=0)
        MDHD(timescale=timescale)
        MDHD(duration=duration)
        MDHD(language='und')

        URL_ = Container(type=b'url ')
        URL_(version=0)
        URL_(flags=Container(self_contained=True))
        URL_(location=None)

        DREF = Container(type=b'dref')
        DREF(version=0)
        DREF(flags=0)
        DREF(data_entries=[URL_])

        DINF = Container(type=b'dinf')
        DINF(children=[DREF])

        STTS = Container(type=b'stts')
        STTS(version=0)
        STTS(flags=0)
        STTS(entries=[Container(sample_count=sample_count)(sample_delta=sample_delta)])

        AVCC = Container(type=b'avcC')
        AVCC(version=1)
        AVCC(profile=profile)
        AVCC(compatibility=compatibility)
        AVCC(level=level)
        AVCC(nal_unit_length_field=3)
        AVCC(sps=sps)
        AVCC(pps=pps)

        AVC1 = Container(format=b'avc1')
        AVC1(data_reference_index=1)
        AVC1(version=0)
        AVC1(revision=0)
        AVC1(vendor=b'')
        AVC1(temporal_quality=0)
        AVC1(spatial_quality=0)
        AVC1(width=width)
        AVC1(height=height)
        AVC1(horizontal_resolution=72)
        AVC1(vertical_resolution=72)
        AVC1(data_size=0)
        AVC1(frame_count=1)
        AVC1(compressor_name=b'')
        AVC1(depth=24)
        AVC1(color_table_id=-1)
        AVC1(avc_data=AVCC)

        STSD = Container(type=b'stsd')
        STSD(version=0)
        STSD(flags=0)
        STSD(entries=[AVC1])

        STSC = Container(type=b'stsc')
        STSC(version=0)
        STSC(flags=0)
        STSC(entries=[Container(first_chunk=1)(samples_per_chunk=sample_count)(sample_description_index=1)])

        STCO = Container(type=b'stco')
        STCO(version=0)
        STCO(flags=0)
        STCO(entries=[Container(chunk_offset=chunk_offset)])

        STSZ = Container(type=b'stsz')
        STSZ(version=0)
        STSZ(flags=0)
        STSZ(sample_size=0)
        STSZ(sample_count=sample_count)
        STSZ(entry_sizes=sample_sizes)

        STBL = Container(type=b'stbl')
        STBL(children=[STSD, STTS, STSC, STSZ, STCO])

        VMHD = Container(type=b'vmhd')
        VMHD(version=0)
        VMHD(flags=1)
        VMHD(graphics_mode=0)
        VMHD(opcolor=Container(red=0)(green=0)(blue=0))

        MINF = Container(type=b'minf')
        MINF(children=[VMHD, DINF, STBL])

        MDIA = Container(type=b'mdia')
        MDIA(children=[MDHD, HDLR, MINF])

        # Width and height in TKHD are 16.16 integers
        TKHD = Container(type=b'tkhd')
        TKHD(version=0)
        TKHD(flags=3)
        TKHD(creation_time=0)
        TKHD(modification_time=0)
        TKHD(track_ID=1)
        TKHD(duration=duration)
        TKHD(layer=0)
        TKHD(alternate_group=0)
        TKHD(volume=0)
        TKHD(matrix=UNITY_MATRIX)
        TKHD(width=width << 16)
        TKHD(height=height << 16)

        TRAK = Container(type=b'trak')
        TRAK(children=[TKHD, MDIA])

        MVHD = Container(type=b'mvhd')
        MVHD(version=0)
        MVHD(flags=0)
        MVHD(creation_time=0)
        MVHD(modification_time=0)
        MVHD(timescale=timescale)
        MVHD(duration=duration)
        MVHD(rate=0x10000)
        MVHD(volume=0x100)
        MVHD(matrix=UNITY_MATRIX)
        MVHD(pre_defined=[0, 0, 0, 0, 0, 0])
        MVHD(next_track_ID=2)

        MOOV = Container(type=b'moov')
        MOOV(children=[MVHD, TRAK])

        # Finally write
        self._write(Box.build(MOOV))


