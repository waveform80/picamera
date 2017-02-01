.. _api_exc:

================
API - Exceptions
================

.. currentmodule:: picamera

All exceptions defined by picamera are listed in this section. All exception
classes utilize multiple inheritance in order to make testing for exception
types more intuitive. For example, :exc:`PiCameraValueError` derives from both
:exc:`PiCameraError` and :exc:`ValueError`. Hence it will be caught by blocks
intended to catch any error specific to the picamera library::

    try:
        camera.brightness = int(some_user_value)
    except PiCameraError:
        print('Something went wrong with the camera')

Or by blocks intended to catch value errors::

    try:
        camera.contrast = int(some_user_value)
    except ValueError:
        print('Invalid value')


Warnings
========

.. autoexception:: PiCameraWarning
    :show-inheritance:

.. autoexception:: PiCameraDeprecated
    :show-inheritance:

.. autoexception:: PiCameraFallback
    :show-inheritance:

.. autoexception:: PiCameraResizerEncoding
    :show-inheritance:

.. autoexception:: PiCameraAlphaStripping
    :show-inheritance:


Exceptions
==========

.. autoexception:: PiCameraError
    :show-inheritance:

.. autoexception:: PiCameraValueError
    :show-inheritance:

.. autoexception:: PiCameraRuntimeError
    :show-inheritance:

.. autoexception:: PiCameraClosed
    :show-inheritance:

.. autoexception:: PiCameraNotRecording
    :show-inheritance:

.. autoexception:: PiCameraAlreadyRecording
    :show-inheritance:

.. autoexception:: PiCameraMMALError
    :show-inheritance:

.. autoexception:: PiCameraPortDisabled
    :show-inheritance:


Functions
=========

.. autofunction:: mmal_check

