.. _api_mmalobj:

=============
API - mmalobj
=============

.. module:: picamera.mmalobj

.. currentmodule:: picamera.mmalobj

This module provides an object-oriented interface to ``libmmal`` which is the
library underlying picamera, ``raspistill``, and ``raspivid``.  It is provided
to ease the usage of ``libmmal`` to Python coders unfamiliar with C and also
works around some of the idiosyncracies in ``libmmal``.


Components
==========

.. autoclass:: MMALComponent

.. autoclass:: MMALCamera
    :show-inheritance:

.. autoclass:: MMALCameraInfo
    :show-inheritance:

.. autoclass:: MMALDownstreamComponent
    :show-inheritance:

.. autoclass:: MMALSplitter
    :show-inheritance:

.. autoclass:: MMALResizer
    :show-inheritance:

.. autoclass:: MMALEncoder
    :show-inheritance:

.. autoclass:: MMALVideoEncoder
    :show-inheritance:

.. autoclass:: MMALImageEncoder
    :show-inheritance:

.. autoclass:: MMALRenderer
    :show-inheritance:

.. autoclass:: MMALNullSink
    :show-inheritance:


Ports
=====

.. autoclass:: MMALControlPort

.. autoclass:: MMALPort
    :show-inheritance:

.. autoclass:: MMALVideoPort
    :show-inheritance:

.. autoclass:: MMALSubPicturePort
    :show-inheritance:

.. autoclass:: MMALAudioPort
    :show-inheritance:

.. autoclass:: MMALPortParams


Connections
===========

.. autoclass:: MMALConnection

.. autoclass:: MMALPool

.. autoclass:: MMALPortPool
    :show-inheritance:


Buffers
=======

.. autoclass:: MMALBuffer


Debugging
=========

The following functions are useful for quickly dumping the state of a given
MMAL pipeline:

.. autofunction:: debug_pipeline

.. autofunction:: print_pipeline

.. note::

    It is also worth noting that most classes, in particular
    :class:`MMALVideoPort` and :class:`MMALBuffer` have useful :func:`repr`
    outputs which can be extremely useful with simple :func:`print` calls for
    debugging.

