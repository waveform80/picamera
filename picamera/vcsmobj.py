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
An object-oriented wrapper for the VideoCore Shared Memory library.

This module is intended as a friendly Python wrapper for the VideoCore shared
memory API exposed by [user_vcsm.h](https://github.com/raspberrypi/userland/
blob/master/host_applications/linux/libs/sm/user-vcsm.h) in the Raspberry Pi
userland code.
"""


from __future__ import (
    unicode_literals,
    print_function,
    division,
    absolute_import,
    )

# Make Py2's str equivalent to Py3's
str = type('')

from . import user_vcsm as vcsm
import warnings
import contextlib
import ctypes

# All the next bit of code does is attempt to open/close the library.
# I am sure there ought to be a nice way to hook into the module unloading
# or the interpreter closing, but I have not yet found it.

class VideoCoreSharedMemoryServiceManager():
    """Class to manage initialising/closing the VCSM service.

    .. versionadded:: 1.14
    """
    def __init__(self):
        ret = vcsm.vcsm_init()
        if ret == 0:
            self._initialised = True
        else:
            raise Error("Error initialising VideoCore Shared Memory "
                        "interface.  Code {}".format(ret))

    def exit(self):
        """Shut down the VCSM service.  Should be called only once."""
        assert self._initialised, "The VCSM service is not running."
        vcsm.vcsm_exit()
        self._initialised = False

    def __del__(self):
        #TODO: find a reliable way to call this before Python shuts down!
        #print("Closing VideoCore Shared Memory service on garbage collection.")
        if self._initialised:
            self.exit()

_vcsm_manager = None
def ensure_vcsm_init():
    """Initialise the shared memory interface if required.

    The VideoCore shared memory service must be initialised in order to
    use any of the other functions.  When this module is unloaded or
    Python closes, it should release the library.

    .. versionadded:: 1.14
    """
    #TODO: find a better way to cleanly close the library.
    global _vcsm_manager
    if _vcsm_manager is None:
        _vcsm_manager = VideoCoreSharedMemoryServiceManager()

def vcsm_exit():
    """Close the VideoCore shared memory service down.

    It is not clear whether multiple init/close cycles are allowed in
    one run of Python.  This method should only be called once.  It is
    also probably not required - the library should be shut down cleanly
    when the garbage collector cleans up after the module.
    
    You probably do not want to call this function manually, but it is 
    here for completeness.

    .. versionadded:: 1.14
    """
    if _vcsm_manager is not None:
        _vcsm_manager.exit()
        _vcsm_manager = None
    else:
        warnings.warn("The VCSM service can't be closed - it's not open.")

class VideoCoreSharedMemory():
    """This class manages a chunk of VideoCore shared memory."""
    def __init__(self, size, name):
        """Create a chunk of shared memory.

        Arguments:
            size: unsigned integer
                The size of the block of memory, in bytes
            name: string
                A name for the block of shared memory.

        On creation, this object will create some VC shared memory by
        calling vcsm_malloc.  It will call vcsm_free to free the memory
        when the object is deleted.

        .. versionadded:: 1.14
        """
        ensure_vcsm_init()
        self._handle = vcsm.vcsm_malloc(size, name.encode())
        self._size = size
        if self._handle == 0:
            raise Error("Could not allocate VC shared memory block "
                        "'{}' with size {} bytes".format(name, size))

    def __del__(self):
        vcsm.vcsm_free(self._handle)

    def _get_handle(self):
        return self._handle
    handle = property(_get_handle, doc="""\
        The handle of the underlying VideoCore shared memory

        The handle identifies the block of shared memory, and is used by
        the various functions wrapped in ``user_vcsm.py``.

        .. versionadded:: 1.14
        """)

    def _get_videocore_handle(self):
        return vcsm.vcsm_vc_hdl_from_hdl(self._handle)

    videocore_handle = property(_get_videocore_handle, doc="""\
        A handle to access the shared memory from the GPU

        The handle identifies the block of shared memory to the GPU.  It
        cannot, for safety reasons, be used to read or write memory from
        the CPU, so it is only useful when passing data to the GPU.

        .. versionadded:: 1.14
        """)

    @contextlib.contextmanager
    def lock(self):
        """Lock the shared memory and return a pointer to it.

        Usage:
        ```
        sm = VideoCoreSharedMemory(128, "test")
        with sm.lock() as pointer:
            #copy stuff into the block
        ```

        .. versionadded:: 1.14
        """
        pointer = vcsm.vcsm_lock(self._handle)
        try:
            yield pointer
        finally:
            vcsm.vcsm_unlock_hdl(self._handle)

    def copy_from_buffer(self, source, size=None, warn_if_small=True):
        """Copy data from a buffer to shared memory.

        Arguments:
            buffer: ctypes.c_void_p
                A pointer to the location of the memory you want to copy in.
            size: integer (optional)
                If specified, copy this much memory.  It will not copy more
                than the size of the shared memory, and will raise an exception
                if you try to do so.
            warn_if_small: boolean (optional)
                By default, a warning will be raised if you copy in a buffer
                that is smaller than the allocated memory.  Set this to False
                to suppress the warning.

        .. versionadded:: 1.14
        """
        if size is None:
            size = self._size
        if size > self._size:
            raise ValueError("Attempted to copy in more bytes than the buffer holds.")
        if size < self._size:
            warnings.warn("The allocated memory won't be filled by the array passed in.")
        with self.lock() as destination:
            ctypes.memmove(destination, source, size)

    def copy_from_array(self, source):
        """Copy the contents of a numpy array into the buffer.

        Arguments:
            source: numpy.ndarray
                The data to copy into the buffer.  Must be np.uint8 datatype.

        NB the array must be contiguous.  This will be checked but, in order to avoid
        a hard dependency on numpy, it will not be made contiguous automatically.

        .. versionadded:: 1.14
        """
        if not source.flags['C_CONTIGUOUS']:
            raise ValueError("Only contiguous arrays can be copied to shared memory.")
        self.copy_from_buffer(source.ctypes.data_as(ctypes.c_void_p), source.size)
