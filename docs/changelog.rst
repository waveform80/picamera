.. _changelog:

==========
Change log
==========


Release 0.7
===========

0.7 is mostly a bug fix release, with a few new video recording features:

* Added ``quantisation`` and ``inline_headers`` options to
  :meth:`~picamera.PiCamera.start_recording` method
* Fixed bugs in the :attr:`~picamera.PiCamera.crop` property
* The issue of captures fading to black over time when the preview is not
  running has been resolved. This solution was to permanently activate the
  preview, but pipe it to a null-sink when not required. Note that this means
  rapid capture gets even slower when not using the video port
* LED support is via RPi.GPIO only; the RPIO library simply doesn't support it
  at this time
* Numerous documentation fixes

Release 0.6
===========

In 0.6, the major features added were:

* New ``'raw'`` format added to all capture methods
  (:meth:`~picamera.PiCamera.capture`,
  :meth:`~picamera.PiCamera.capture_continuous`, and
  :meth:`~picamera.PiCamera.capture_sequence`) to permit capturing of raw
  sensor data
* New :attr:`~picamera.PiCamera.raw_format` attribute to permit control of
  raw format (defaults to ``'yuv'``, only other setting currently is ``'rgb'``)
* New :attr:`~picamera.PiCamera.shutter_speed` attribute to permit manual
  control of shutter speed (defaults to 0 for automatic shutter speed, and
  requires latest firmware to operate - use ``sudo rpi-update`` to upgrade)
* New "Recipes" chapter in the documentation which demonstrates a wide variety
  of capture techniques ranging from trivial to complex


Release 0.5
===========

In 0.5, the major features added were:

* New :meth:`~picamera.PiCamera.capture_sequence` method
* :meth:`~picamera.PiCamera.continuous` method renamed to
  :meth:`~picamera.PiCamera.capture_continuous`. Old method name retained for
  compatiblity until 1.0.
* *use_video_port* option for :meth:`~picamera.PiCamera.capture_sequence` and
  :meth:`~picamera.PiCamera.capture_continuous` to allow rapid capture of
  JPEGs via video port
* New :attr:`~picamera.PiCamera.framerate` attribute to control video and
  rapid-image capture frame rates
* Default value for :attr:`~picamera.PiCamera.ISO` changed from 400 to 0 (auto)
  which fixes :attr:`~picamera.PiCamera.exposure_mode` not working by default
* *intraperiod* and *profile* options for
  :meth:`~picamera.PiCamera.start_recording`

In addition a few bugs were fixed:

* Byte strings not being accepted by :meth:`~picamera.PiCamera.continuous`
* Erroneous docs for :attr:`~picamera.PiCamera.ISO`

Many thanks to the community for the bug reports!

Release 0.4
===========

In 0.4, several new attributes were introduced for configuration of the preview
window:

* :attr:`~picamera.PiCamera.preview_alpha`
* :attr:`~picamera.PiCamera.preview_fullscreen`
* :attr:`~picamera.PiCamera.preview_window`

Also, a new method for rapid continual capture of still images was introduced:
:meth:`~picamera.PiCamera.continuous`.

Release 0.3
===========

The major change in 0.3 was the introduction of custom Exif tagging for
captured images, and fixing a silly bug which prevented more than one image
being captured during the lifetime of a PiCamera instance.

Release 0.2
===========

The major change in 0.2 was support for video recording, along with the new
:attr:`~picamera.PiCamera.resolution` property which replaced the separate
``preview_resolution`` and ``stills_resolution`` properties.

