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

.. autoexception:: PiCameraDeprecated

.. autoexception:: PiCameraFallback

.. autoexception:: PiCameraResizerEncoding

.. autoexception:: PiCameraAlphaStripping


Exceptions
==========

.. autoexception:: PiCameraError

.. autoexception:: PiCameraValueError

.. autoexception:: PiCameraRuntimeError

.. autoexception:: PiCameraClosed

.. autoexception:: PiCameraNotRecording

.. autoexception:: PiCameraAlreadyRecording

.. autoexception:: PiCameraMMALError


Functions
=========

.. autofunction:: mmal_check

