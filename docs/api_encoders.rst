.. _api_encoders:

==============
API - Encoders
==============

.. currentmodule:: picamera

Encoders are typically used by the camera to compress captured images or video
frames for output to disk. However, picamera also has classes representing
"unencoded" output (raw RGB, etc). Most users will have no direct need to use
these classes directly, but advanced users may find them useful as base classes
for :ref:`custom_encoders`.

PiEncoder
=========

.. autoclass:: PiEncoder
    :members:
    :private-members:


PiVideoEncoder
==============

.. autoclass:: PiVideoEncoder
    :members:
    :private-members:


PiImageEncoder
==============

.. autoclass:: PiImageEncoder
    :members:
    :private-members:


PiRawMixin
==========

.. autoclass:: PiRawMixin
    :members:
    :private-members:


PiCookedVideoEncoder
====================

.. autoclass:: PiCookedVideoEncoder
    :members:
    :private-members:


PiRawVideoEncoder
=================

.. autoclass:: PiRawVideoEncoder
    :members:
    :private-members:


PiOneImageEncoder
=================

.. autoclass:: PiOneImageEncoder
    :members:
    :private-members:


PiMultiImageEncoder
===================

.. autoclass:: PiMultiImageEncoder
    :members:
    :private-members:


PiRawImageMixin
===============

.. autoclass:: PiRawImageMixin
    :members:
    :private-members:


PiCookedOneImageEncoder
=======================

.. autoclass:: PiCookedOneImageEncoder
    :members:
    :private-members:


PiRawOneImageEncoder
====================

.. autoclass:: PiRawOneImageEncoder
    :members:
    :private-members:


PiCookedMultiImageEncoder
=========================

.. autoclass:: PiCookedMultiImageEncoder
    :members:
    :private-members:


PiRawMultiImageEncoder
======================

.. autoclass:: PiRawMultiImageEncoder
    :members:
    :private-members:

