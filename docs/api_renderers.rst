.. _api_renderers:

===============
API - Renderers
===============

.. currentmodule:: picamera

Renderers are used by the camera to provide preview and overlay functionality
on the Pi's display. Users will rarely need to construct instances of these
classes directly (:meth:`~PiCamera.start_preview` and
:meth:`~PiCamera.add_overlay` are generally used instead) but may find the
attribute references for them useful.


PiRenderer
==========

.. autoclass:: PiRenderer


PiOverlayRenderer
=================

.. autoclass:: PiOverlayRenderer


PiPreviewRenderer
=================

.. autoclass:: PiPreviewRenderer


PiNullSink
==========

.. autoclass:: PiNullSink

