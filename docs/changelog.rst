.. _changelog:

==========
Change log
==========


Release 1.1 (2014-01-25)
========================

1.1 was mostly a bug fix release:

* A nasty race condition was discovered which led to crashes with long-running
  processes (`#40`_)
* An assertion error raised when performing raw captures with an active resize
  parameter was fixed (`#46`_)
* A couple of documentation enhancements made it in (`#41`_ and `#47`_)

.. _#40: https://github.com/waveform80/picamera/issues/40
.. _#41: https://github.com/waveform80/picamera/issues/41
.. _#46: https://github.com/waveform80/picamera/issues/46
.. _#47: https://github.com/waveform80/picamera/issues/47


Release 1.0 (2014-01-11)
========================

In 1.0 the major features added were:

* Debian packaging! (`#12`_)
* The new :attr:`~picamera.PiCamera.frame` attribute permits querying
  information about the frame last written to the output stream (number,
  timestamp, size, keyframe, etc.) (`#34`_, `#36`_)
* All capture methods (:meth:`~picamera.PiCamera.capture` et al), and the
  :meth:`~picamera.PiCamera.start_recording` method now accept a ``resize``
  parameter which invokes a resizer prior to the encoding step. This can be
  used to :ref:`record video with full field-of-view <full_res_record>`
  (`#21`_)
* A new :class:`~picamera.PiCameraCircularIO` stream class is provided to
  permit holding the last *n* seconds of video in memory, ready for writing out
  to disk (or whatever you like) (`#39`_)
* There's a new way to specify raw captures - simply use the format you require
  with the capture method of your choice. As a result of this, the
  :attr:`~picamera.PiCamera.raw_format` attribute is now deprecated (`#32`_)

Some bugs were also fixed:

* GPIO.cleanup is no longer called on :meth:`~picamera.PiCamera.close`
  (`#35`_), and GPIO set up is only done on first use of the
  :attr:`~picamera.PiCamera.led` attribute which should resolve issues that
  users have been having with using picamera in conjunction with GPIO
* Raw RGB video-port based image captures are now working again too (`#32`_)

As this is a new major-version, all deprecated elements were removed:

* The continuous method was removed; this was replaced by
  :meth:`~picamera.PiCamera.capture_continuous` in 0.5 (`#7`_)

.. _#7: https://github.com/waveform80/picamera/issues/7
.. _#12: https://github.com/waveform80/picamera/issues/12
.. _#21: https://github.com/waveform80/picamera/issues/21
.. _#32: https://github.com/waveform80/picamera/issues/32
.. _#34: https://github.com/waveform80/picamera/issues/34
.. _#35: https://github.com/waveform80/picamera/issues/35
.. _#36: https://github.com/waveform80/picamera/issues/36
.. _#39: https://github.com/waveform80/picamera/issues/39


Release 0.8 (2013-12-09)
========================

In 0.8 the major features added were:

* Capture of images whilst recording without frame-drop. Previously, images
  could be captured whilst recording but only from the still port which
  resulted in dropped frames in the recorded video due to the mode switch. In
  0.8, ``use_video_port=True`` can be specified on capture methods whilst
  recording video to avoid this.
* Splitting of video recordings into multiple files. This is done via the new
  :meth:`~picamera.PiCamera.split_recording` method, and requires that the
  :meth:`~picamera.PiCamera.start_recording` method was called with
  *inline_headers* set to True. The latter has now been made the default
  (technically this is a backwards incompatible change, but it's relatively
  trivial and I don't anticipate anyone's code breaking because of this
  change).

In addition a few bugs were fixed:

* Documentation updates that were missing from 0.7 (specifically the new
  video recording parameters)
* The ability to perform raw captures through the video port
* Missing exception imports in the encoders module (which caused very confusing
  errors in the case that an exception was raised within an encoder thread)


Release 0.7 (2013-11-14)
========================

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

Release 0.6 (2013-10-30)
========================

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


Release 0.5 (2013-10-21)
========================

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

Release 0.4 (2013-10-11)
========================

In 0.4, several new attributes were introduced for configuration of the preview
window:

* :attr:`~picamera.PiCamera.preview_alpha`
* :attr:`~picamera.PiCamera.preview_fullscreen`
* :attr:`~picamera.PiCamera.preview_window`

Also, a new method for rapid continual capture of still images was introduced:
:meth:`~picamera.PiCamera.continuous`.

Release 0.3 (2013-10-04)
========================

The major change in 0.3 was the introduction of custom Exif tagging for
captured images, and fixing a silly bug which prevented more than one image
being captured during the lifetime of a PiCamera instance.

Release 0.2
===========

The major change in 0.2 was support for video recording, along with the new
:attr:`~picamera.PiCamera.resolution` property which replaced the separate
``preview_resolution`` and ``stills_resolution`` properties.


