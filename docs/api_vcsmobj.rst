.. _api_mmalobj:

=============
API - vcsmobj
=============

.. module:: picamera.vcsmobj

.. currentmodule:: picamera.vcsmobj

This module provides an object-oriented interface to the VideoCore shared
memory API, to make it simpler to use from Python.

.. warning::

    This part of the API is still experimental and subject to change in future
    versions. Backwards compatibility is not (yet) guaranteed.


The Shared Memory Interface
===========================
Some MMAL functions (see :mod:`~picamera.mmalobj`) need to pass larger amounts
of information to the GPU, which we can achieve using shared memory.  The API
doesn't provide a persistent way to "hold on" to a block of shared memory, which
means this transfer is effectively one way, i.e. it allows us to transfer data
onto the GPU, but not back off again.

The process of getting some data onto the GPU usually consists of:

#. Allocate a block of shared memory on the GPU.
#. Get a "handle" that identifies the block of memory.
#. "Lock" the block of memory - stop the GPU from accessing it, and make it 
   available to the CPU.
#. Copy the data into the block of memory.
#. Unlock the memory.
#. Unallocate the block of memory so it can be re-used later.

It's important that all of these steps are done in sequence; interrupting the 
process can leave blocks of memory allocated (or worse, locked) when they are 
no longer needed, which eventually causes crashes.  That's the purpose of this
module; it wraps up the above process in higher-level functions, making it much
harder to accidentally crash the GPU.  This module also makes sure the VCSM 
interface is initialised and shut down cleanly.

A Simple Example
----------------
The :class:`VideoCoreSharedMemory` class represents a block of memory.  This
block is initialised when the object is created, and freed when the object
is destroyed.  It also provides functions that will copy data in from either a
`ctypes` buffer object or a `numpy` array.  Our example starts by importing
the shared memory class (usually the only part of the module that is required)
and creating an array to send to the GPU.  This uses ``numpy`` to create a 
10x10 array of bytes:

.. code-block:: pycon

    >>> from picamera.vcsmobj import VideoCoreSharedMemory
    >>> import numpy as np
    >>> w = 10
    >>> h = 10
    >>> data_to_send = np.ones((w, h), dtype=np.uint8)

Next, we allocate some shared memory and copy our ``numpy`` array into it:
    
.. code-block:: pycon

    >>> shared_mem = VideoCoreSharedMemory(w*h, "test_data")
    >>> shared_mem.copy_from_array(data_to_send)
    
You can then use this block of shared memory in a function (usually in the
MMAL library) by referring to ``shared_mem.videocore_handle`` which returns
a handle that identifies the block of memory to functions that run on the
GPU.  The block of memory is freed when the object is garbage-collected by
Python, so there is no need to explicitly free it again.  The first time 
you allocate shared memory, the interface is initialised, and the module 
will take care of closing down the shared memory interface when Python exits.


Classes
=======

The VCSM wrapper can be used through one class, :class:`VideoCoreSharedMemory`.
This handles allocating and freeing the memory, as well as locking it and 
copying in the data.  There is a further class defined, used only to manage
initialising and closing the low-level VCSM interface 
(:class:`VideoCoreSharedMemoryServiceManager`).

.. autoclass:: VideoCoreSharedMemory

.. autoclass:: VideoCoreSharedMemoryServiceManager


Functions
=========

It is possible and recommended to use this module only through 
:class:`VideoCoreSharedMemory`.  However, there are a couple of functions 
defined to explicitly initialise and shut down the shared memory interface.
These don't need to be called unless you are worried about the (very small)
overhead of starting the interface the first time you allocate memory.

.. autofunction:: ensure_vcsm_init

.. autofunction:: vcsm_exit

