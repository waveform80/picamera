# vim: set et sw=4 sts=4 fileencoding=utf-8:
#
# Python header conversion
# Copyright (c) 2013-2017 Dave Jones <dave@waveform.org.uk>
# Please blame this particular file on
# Richard Bowman <richard.bowman@cantab.net>
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

"""
Wraps the VideoCore Shared Memory library in Python.

This Python module wraps the necessary functions from the Raspberry Pi 
``userland`` module to allow shared memory use in ``picamera``.  Currently
this is only used to load a custom lens shading table.  Please see the
comments in [user_vcsm.h](https://github.com/raspberrypi/userland/
blob/master/host_applications/linux/libs/sm/user-vcsm.h).
"""

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

_lib = ct.CDLL('libvcsm.so')

VCSM_STATUS_T = ct.c_uint32 # enum
(
    VCSM_STATUS_VC_WALK_ALLOC,
    VCSM_STATUS_HOST_WALK_MAP,
    VCSM_STATUS_HOST_WALK_PID_MAP,
    VCSM_STATUS_HOST_WALK_PID_ALLOC,
    VCSM_STATUS_VC_MAP_ALL,
    VCSM_STATUS_NONE,
) = range(6)

VCSM_CACHE_TYPE_T = ct.c_uint32 # enum
(
    VCSM_CACHE_TYPE_NONE,
    VCSM_CACHE_TYPE_HOST,
    VCSM_CACHE_TYPE_VC,
    VCSM_CACHE_TYPE_HOST_AND_VC,
) = range(4)

vcsm_init = _lib.vcsm_init
vcsm_init.argtypes = []
vcsm_init.restype = ct.c_int

vcsm_exit = _lib.vcsm_exit
vcsm_exit.argtypes = []
vcsm_exit.restype = None

vcsm_status = _lib.vcsm_status
vcsm_status.argtypes = [VCSM_STATUS_T, ct.c_int]
vcsm_status.restype = None

vcsm_malloc = _lib.vcsm_malloc
vcsm_malloc.argtypes = [ct.c_uint, ct.c_char_p]
vcsm_malloc.restype = ct.c_uint

vcsm_malloc_share = _lib.vcsm_malloc_share
vcsm_malloc_share.argtypes = [ct.c_uint]
vcsm_malloc_share.restype = ct.c_uint

vcsm_free = _lib.vcsm_free
vcsm_free.argtypes = [ct.c_uint]
vcsm_free.restype = None

vcsm_vc_hdl_from_ptr = _lib.vcsm_vc_hdl_from_ptr
vcsm_vc_hdl_from_ptr.argtypes = [ct.c_void_p]
vcsm_vc_hdl_from_ptr.restype = ct.c_uint

vcsm_vc_hdl_from_hdl = _lib.vcsm_vc_hdl_from_hdl
vcsm_vc_hdl_from_hdl.argtypes = [ct.c_uint]
vcsm_vc_hdl_from_hdl.restype = ct.c_uint

vcsm_lock = _lib.vcsm_lock
vcsm_lock.argtypes = [ct.c_uint]
vcsm_lock.restype = ct.c_void_p

vcsm_unlock_ptr = _lib.vcsm_unlock_ptr
vcsm_unlock_ptr.argtypes = [ct.c_void_p]
vcsm_unlock_ptr.restype = ct.c_int

vcsm_unlock_hdl = _lib.vcsm_unlock_hdl
vcsm_unlock_hdl.argtypes = [ct.c_uint]
vcsm_unlock_hdl.restype = ct.c_int
