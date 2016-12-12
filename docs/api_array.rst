.. _api_array:

============
API - Arrays
============

.. module:: picamera.array

.. currentmodule:: picamera.array

The picamera library provides a set of classes designed to aid in construction
of n-dimensional `numpy`_ arrays from camera output. In order to avoid adding a
hard dependency on numpy to picamera, this module (:mod:`picamera.array`) is
not automatically imported by the main picamera package and must be explicitly
imported, e.g.::

    import picamera
    import picamera.array

.. _numpy: http://www.numpy.org/


PiArrayOutput
=============

.. autoclass:: PiArrayOutput


PiRGBArray
==========

.. autoclass:: PiRGBArray
    :no-members:


PiYUVArray
==========

.. autoclass:: PiYUVArray
    :no-members:


PiBayerArray
============

.. autoclass:: PiBayerArray
    :no-members:


PiMotionArray
=============

.. autoclass:: PiMotionArray
    :no-members:


PiAnalysisOutput
================

.. autoclass:: PiAnalysisOutput


PiRGBAnalysis
=============

.. autoclass:: PiRGBAnalysis
    :no-members:


PiYUVAnalysis
=============

.. autoclass:: PiYUVAnalysis
    :no-members:


PiMotionAnalysis
================

.. autoclass:: PiMotionAnalysis
    :no-members:


PiArrayTransform
================

.. autoclass:: PiArrayTransform

