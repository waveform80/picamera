.. _changelog:

==========
Change log
==========


Release 1.4 (2014-05-06)
========================

1.4 mostly involved bug fixes with a couple of new bits of functionality:

* The *sei* parameter was added to :meth:`~picamera.PiCamera.start_recording`
  to permit inclusion of "Supplemental Enhancement Information" in the output
  stream (`#77`_)
* The :attr:`~picamera.PiCamera.awb_gains` attribute was added to permit manual
  control of the auto-white-balance red/blue gains (`#74`_)
* A bug which cause :meth:`~picamera.PiCamera.split_recording` to fail when low
  framerates were configured was fixed (`#87`_)
* A bug which caused picamera to fail when used in UNIX-style daemons, unless
  the module was imported *after* the double-fork to background was fixed
  (`#85`_)
* A bug which caused the :attr:`~picamera.PiCamera.frame` attribute to fail
  when queried in Python 3 was fixed (`#80`_)
* A bug which caused raw captures with "odd" resolutions (like 100x100) to
  fail was fixed (`#83`_)

Known issues:

* Added a workaround for full-resolution YUV captures failing. This
  isn't a complete fix, and attempting to capture a JPEG before attempting to
  capture full-resolution YUV data will still fail, unless the GPU memory split
  is set to something huge like 256Mb (`#73`_)

Many thanks to the community for yet more excellent quality bug reports!

.. _#73: https://github.com/waveform80/picamera/issues/73
.. _#74: https://github.com/waveform80/picamera/issues/74
.. _#77: https://github.com/waveform80/picamera/issues/77
.. _#80: https://github.com/waveform80/picamera/issues/80
.. _#83: https://github.com/waveform80/picamera/issues/83
.. _#85: https://github.com/waveform80/picamera/issues/85
.. _#87: https://github.com/waveform80/picamera/issues/87


Release 1.3 (2014-03-22)
========================

1.3 was partly new functionality:

* The *bayer* parameter was added to the ``'jpeg'`` format in the capture
  methods to permit output of the camera's raw sensor data (`#52`_)
* The :meth:`~picamera.PiCamera.record_sequence` method was added to provide
  a cleaner interface for recording multiple consecutive video clips (`#53`_)
* The *splitter_port* parameter was added to all capture methods and
  :meth:`~picamera.PiCamera.start_recording` to permit recording multiple
  simultaneous video streams (presumably with different options, primarily
  *resize*) (`#56`_)
* The limits on the :attr:`~picamera.PiCamera.framerate` attribute were
  increased after firmware #656 introduced numerous new camera modes including
  90fps recording (at lower resolutions) (`#65`_)

And partly bug fixes:

* It was reported that Exif metadata (including thumbnails) wasn't fully
  recorded in JPEG output (`#59`_)
* Raw captures with :meth:`~picamera.PiCamera.capture_continuous` and
  :meth:`~picamera.PiCamera.capture_sequence` were broken (`#55`_)

.. _#52: https://github.com/waveform80/picamera/issues/52
.. _#53: https://github.com/waveform80/picamera/issues/53
.. _#55: https://github.com/waveform80/picamera/issues/55
.. _#56: https://github.com/waveform80/picamera/issues/56
.. _#59: https://github.com/waveform80/picamera/issues/59
.. _#65: https://github.com/waveform80/picamera/issues/65


Release 1.2 (2014-02-02)
========================

1.2 was mostly a bug fix release:

* A bug introduced in 1.1 caused :meth:`~picamera.PiCamera.split_recording`
  to fail if it was preceded by a video-port-based image capture (`#49`_)
* The documentation was enhanced to try and full explain the discrepancy
  between preview and capture resolution, and to provide some insight into
  the underlying workings of the camera (`#23`_)
* A new property was introduced for configuring the preview's layer at runtime
  although this probably won't find use until OpenGL overlays are explored
  (`#48`_)

.. _#23: https://github.com/waveform80/picamera/issues/23
.. _#48: https://github.com/waveform80/picamera/issues/48
.. _#49: https://github.com/waveform80/picamera/issues/49


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
  parameter which invokes a resizer prior to the encoding step (`#21`_)
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


