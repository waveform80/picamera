.. _changelog:

==========
Change log
==========

.. currentmodule:: picamera


Release 1.12 (2016-07-03)
=========================

1.12 is almost entirely a bug fix release:

* Fixed issue with unencoded captures in Python 3 (`#297`_)
* Fixed several Python 3 bytes/unicode issues that were related to `#297`_ (I'd
  erroneously run the picamera test suite twice against Python 2 instead of 2
  and 3 when releasing 1.11, which is how these snuck in)
* Fixed multi-dimensional arrays for overlays under Python 3
* Finished alternate CIE constructors for the :class:`Color` class

.. _#297: https://github.com/waveform80/picamera/issues/297


Release 1.11 (2016-06-19)
=========================

1.11 on the surface consists mostly of enhancements, but underneath
includes a major re-write of picamera's core:

* Direct capture to buffer-protocol objects, such as numpy arrays
  (`#241`_)
* Add :meth:`~PiCamera.request_key_frame` method to permit manual request
  of an I-frame during H264 recording; this is now used implicitly by
  :meth:`~PiCamera.split_recording` (`#257`_)
* Added :attr:`~PiCamera.timestamp` attribute to query camera's clock
  (`#212`_)
* Added :attr:`~PiCamera.framerate_delta` to permit small adjustments to
  the camera's framerate to be performed "live" (`#279`_)
* Added :meth:`~PiCameraCircularIO.clear` and
  :meth:`~PiCameraCircularIO.copy_to` methods to
  :class:`PiCameraCircularIO` (`#216`_)
* Prevent setting attributes on the main :class:`PiCamera` class to ease
  debugging in educational settings (`#240`_)
* Due to the core re-writes in this version, you may require cutting edge
  firmware (``sudo rpi-update``) if you are performing unencoded captures,
  unencoded video recording, motion estimation vector sampling, or manual
  sensor mode setting.
* Added property to control preview's :attr:`~PiPreviewRenderer.resolution`
  separately from the camera's :attr:`~PiCamera.resolution` (required for
  maximum resolution previews on the V2 module - `#296`_).

There are also several bug fixes:

* Fixed basic stereoscopic operation on compute module (`#218`_)
* Fixed accessing framerate as a tuple (`#228`_)
* Fixed hang when invalid file format is specified (`#236`_)
* Fixed multiple bayer captures with :meth:`~PiCamera.capture_sequence`
  and :meth:`~PiCamera.capture_continuous` (`#264`_)
* Fixed usage of "falsy" custom outputs with ``motion_output`` (`#281`_)

Many thanks to the community, and especially thanks to 6by9 (one of the
firmware developers) who's fielded seemingly endless questions and
requests from me in the last couple of months!

.. _#241: https://github.com/waveform80/picamera/issues/241
.. _#257: https://github.com/waveform80/picamera/issues/257
.. _#212: https://github.com/waveform80/picamera/issues/212
.. _#279: https://github.com/waveform80/picamera/issues/279
.. _#216: https://github.com/waveform80/picamera/issues/216
.. _#240: https://github.com/waveform80/picamera/issues/240
.. _#218: https://github.com/waveform80/picamera/issues/218
.. _#228: https://github.com/waveform80/picamera/issues/228
.. _#236: https://github.com/waveform80/picamera/issues/236
.. _#264: https://github.com/waveform80/picamera/issues/264
.. _#281: https://github.com/waveform80/picamera/issues/281
.. _#296: https://github.com/waveform80/picamera/issues/296


Release 1.10 (2015-03-31)
=========================

1.10 consists mostly of minor enhancements:

* The major enhancement is the addition of support for the camera's flash
  driver. This is relatively complex to configure, but a full recipe has been
  included in the documentation (`#184`_)
* A new `intra_refresh` attribute is added to the
  :meth:`~PiCamera.start_recording` method permitting control of the
  intra-frame refresh method (`#193`_)
* The GPIO pins controlling the camera's LED are now configurable. This is
  mainly for any compute module users, but also for anyone who wishes to use
  the device tree blob to reconfigure the pins used (`#198`_)
* The new annotate V3 struct is now supported, providing custom background
  colors for annotations, and configurable text size. As part of this work a
  new :class:`Color` class was introduced for representation and manipulation
  of colors (`#203`_)
* Reverse enumeration of frames in :class:`PiCameraCircularIO` is now supported
  efficiently (without having to convert frames to a list first) (`#204`_)
* Finally, the API documentation has been re-worked as it was getting too
  large to comfortably load on all platforms (no ticket)

.. _#184: https://github.com/waveform80/picamera/issues/184
.. _#193: https://github.com/waveform80/picamera/issues/193
.. _#198: https://github.com/waveform80/picamera/issues/198
.. _#203: https://github.com/waveform80/picamera/issues/203
.. _#204: https://github.com/waveform80/picamera/issues/204


Release 1.9 (2015-01-01)
========================

1.9 consists mostly of bug fixes with a couple of minor new features:

* The camera's sensor mode can now be forced to a particular setting upon
  camera initialization with the new ``sensor_mode`` parameter to
  :class:`PiCamera` (`#165`_)
* The camera's initial framerate and resolution can also be specified as
  keyword arguments to the :class:`PiCamera` initializer. This is primarily
  intended to reduce initialization time (`#180`_)
* Added the :attr:`~PiCamera.still_stats` attribute which controls
  whether an extra statistics pass is made when capturing images from the still
  port (`#166`_)
* Fixed the :attr:`~PiCamera.led` attribute so it should now work on
  the Raspberry Pi model B+ (`#170`_)
* Fixed a nasty memory leak in overlay renderers which caused the camera to run
  out of memory when overlays were repeatedly created and destroyed (`#174`_) *
  Fixed a long standing issue with MJPEG recording which caused camera lockups
  when resolutions greater than VGA were used (`#47`_ and `#179`_)
* Fixed a bug with incorrect frame metadata in :class:`PiCameraCircularIO`.
  Unfortunately this required breaking backwards compatibility to some extent.
  If you use this class and rely on the frame metadata, please familiarize
  yourself with the new :attr:`~PiVideoFrame.complete` attribute (`#177`_)
* Fixed a bug which caused :class:`PiCameraCircularIO` to ignore the splitter
  port it was recording against (`#176`_)
* Several documentation issues got fixed too (`#167`_, `#168`_, `#171`_,
  `#172`_, `#182`_)

Many thanks to the community for providing several of these fixes as pull
requests, and thanks for all the great bug reports. Happy new year everyone!

.. _#47: https://github.com/waveform80/picamera/issues/47
.. _#165: https://github.com/waveform80/picamera/issues/165
.. _#166: https://github.com/waveform80/picamera/issues/166
.. _#167: https://github.com/waveform80/picamera/issues/167
.. _#168: https://github.com/waveform80/picamera/issues/168
.. _#170: https://github.com/waveform80/picamera/issues/170
.. _#171: https://github.com/waveform80/picamera/issues/171
.. _#172: https://github.com/waveform80/picamera/issues/172
.. _#174: https://github.com/waveform80/picamera/issues/174
.. _#176: https://github.com/waveform80/picamera/issues/176
.. _#177: https://github.com/waveform80/picamera/issues/177
.. _#179: https://github.com/waveform80/picamera/issues/179
.. _#180: https://github.com/waveform80/picamera/issues/180
.. _#182: https://github.com/waveform80/picamera/issues/182


Release 1.8 (2014-09-05)
========================

1.8 consists of several new features and the usual bug fixes:

* A new chapter on detecting and correcting deprecated functionality was added
  to the docs (`#149`_)
* Stereoscopic cameras are now tentatively supported on the Pi compute module.
  Please note I have no hardware for testing this, so the implementation is
  possibly (probably!) wrong; bug reports welcome! (`#153`_)
* Text annotation functionality has been extended; up to 255 characters are now
  possible, and the new :attr:`~PiCamera.annotate_frame_num` attribute adds
  rendering of the current frame number. In addition, the new
  :attr:`~PiCamera.annotate_background` flag permits a dark background to be
  rendered behind all annotations for contrast (`#160`_)
* Arbitrary image overlays can now be drawn on the preview using the new
  :meth:`~PiCamera.add_overlay` method. A new recipe has been included
  demonstrating overlays from PIL images and numpy arrays. As part of this work
  the preview system was substantially changed; all older scripts should
  continue to work but please be aware that most preview attributes are now
  deprecated; the new :attr:`~PiCamera.preview` attribute replaces them
  (`#144`_)
* Image effect parameters can now be controlled via the new
  :attr:`~PiCamera.image_effect_params` attribute (`#143`_)
* A bug in the handling of framerates meant that long exposures (>1s) weren't
  operating correctly. This *should* be fixed, but I'd be grateful if users
  could test this and let me know for certain (Exif metadata reports the
  configured exposure speed so it can't be used to determine if things are
  actually working) (`#135`_)
* A bug in 1.7 broke compatibility with older firmwares (resulting in an error
  message mentioning "mmal_queue_timedwait"). The library should now on older
  firmwares (`#154`_)
* Finally, the confusingly named :attr:`~PiCamera.crop` attribute was changed
  to a deprecated alias for the new :attr:`~PiCamera.zoom` attribute (`#146`_)

.. _#135: https://github.com/waveform80/picamera/issues/135
.. _#143: https://github.com/waveform80/picamera/issues/143
.. _#144: https://github.com/waveform80/picamera/issues/144
.. _#146: https://github.com/waveform80/picamera/issues/146
.. _#149: https://github.com/waveform80/picamera/issues/149
.. _#153: https://github.com/waveform80/picamera/issues/153
.. _#154: https://github.com/waveform80/picamera/issues/154
.. _#160: https://github.com/waveform80/picamera/issues/160


Release 1.7 (2014-08-08)
========================

1.7 consists once more of new features, and more bug fixes:

* Text overlay on preview, image, and video output is now possible (`#16`_)
* Support for more than one camera on the compute module has been added, but
  hasn't been tested yet (`#84`_)
* The :attr:`~PiCamera.exposure_mode` ``'off'`` has been added to allow locking
  down the exposure time, along with some new recipes demonstrating this
  capability (`#116`_)
* The valid values for various attributes including :attr:`~PiCamera.awb_mode`,
  :attr:`~PiCamera.meter_mode`, and :attr:`~PiCamera.exposure_mode` are now
  automatically included in the documentation (`#130`_)
* Support for unencoded formats (YUV, RGB, etc.) has been added to the
  :meth:`~PiCamera.start_recording` method (`#132`_)
* A couple of analysis classes have been added to :mod:`picamera.array` to
  support the new unencoded recording formats (`#139`_)
* Several issues in the :class:`~PiBayerArray` class were fixed; this should
  now work correctly with Python 3, and the :meth:`~PiBayerArray.demosaic`
  method should operate correctly (`#133`_, `#134`_)
* A major issue with multi-resolution recordings which caused all recordings
  to stop prematurely was fixed (`#136`_)
* Finally, an issue with the example in the documentation for custom encoders
  was fixed (`#128`_)

Once again, many thanks to the community for another round of excellent bug
reports - and many thanks to 6by9 and jamesh for their excellent work on the
firmware and official utilities!

.. _#16: https://github.com/waveform80/picamera/issues/16
.. _#84: https://github.com/waveform80/picamera/issues/84
.. _#116: https://github.com/waveform80/picamera/issues/116
.. _#128: https://github.com/waveform80/picamera/issues/128
.. _#130: https://github.com/waveform80/picamera/issues/130
.. _#132: https://github.com/waveform80/picamera/issues/132
.. _#133: https://github.com/waveform80/picamera/issues/133
.. _#134: https://github.com/waveform80/picamera/issues/134
.. _#136: https://github.com/waveform80/picamera/issues/136
.. _#139: https://github.com/waveform80/picamera/issues/139


Release 1.6 (2014-07-21)
========================

1.6 is half bug fixes, half new features:

* The :attr:`~PiCamera.awb_gains` attribute is no longer write-only; you can
  now read it to determine the red/blue balance that the camera is using
  (`#98`_)
* The new read-only :attr:`~PiCamera.exposure_speed` attribute will tell you
  the shutter speed the camera's auto-exposure has determined, or the shutter
  speed you've forced with a non-zero value of :attr:`~PiCamera.shutter_speed`
  (`#98`_)
* The new read-only :attr:`~PiCamera.analog_gain` and
  :attr:`~PiCamera.digital_gain` attributes can be used to determine the amount
  of gain the camera is applying at a couple of crucial points of the image
  processing pipeline (`#98`_)
* The new :attr:`~PiCamera.drc_strength` attribute can be used to query and set
  the amount of dynamic range compression the camera will apply to its output
  (`#110`_)
* The *intra_period* parameter for :meth:`~PiCamera.start_recording` can now be
  set to `0` (which means "produce one initial I-frame, then just P-frames")
  (`#117`_)
* The *burst* parameter was added to the various :meth:`~PiCamera.capture`
  methods; users are strongly advised to read the cautions in the docs before
  relying on this parameter (`#115`_)
* One of the advanced recipes in the manual ("splitting to/from a circular
  stream") failed under 1.5 due to a lack of splitter-port support in the
  circular I/O stream class. This has now been rectified by adding a
  *splitter_port* parameter to the constructor of :class:`~PiCameraCircularIO`
  (`#109`_)
* Similarly, the :mod:`array extensions <picamera.array>` introduced in 1.5
  failed to work when resizers were present in the pipeline. This has been
  fixed by adding a `size` parameter to the constructor of all the custom
  output classes defined in that module (`#121`_)
* A bug that caused picamera to fail when the display was disabled has been
  squashed (`#120`_)

As always, many thanks to the community for another great set of bug reports!

.. _#98: https://github.com/waveform80/picamera/issues/98
.. _#109: https://github.com/waveform80/picamera/issues/109
.. _#110: https://github.com/waveform80/picamera/issues/110
.. _#115: https://github.com/waveform80/picamera/issues/115
.. _#117: https://github.com/waveform80/picamera/issues/117
.. _#120: https://github.com/waveform80/picamera/issues/120
.. _#121: https://github.com/waveform80/picamera/issues/121


Release 1.5 (2014-06-11)
========================

1.5 fixed several bugs and introduced a couple of major new pieces of
functionality:

* The new :mod:`picamera.array` module provides a series of custom output
  classes which can be used to easily obtain numpy arrays from a variety of
  sources (`#107`_)
* The *motion_output* parameter was added to :meth:`~PiCamera.start_recording`
  to enable output of motion vector data generated by the H.264 encoder. A
  couple of new recipes were added to the documentation to demonstrate this
  (`#94`_)
* The ability to construct custom encoders was added, including some examples
  in the documentation. Many thanks to user Oleksandr Sviridenko (d2rk) for
  helping with the design of this feature! (`#97`_)
* An example recipe was added to the documentation covering loading and
  conversion of raw Bayer data (`#95`_)
* Speed of unencoded RGB and BGR captures was substantially improved in both
  Python 2 and 3 with a little optimization work. The warning about using
  alpha-inclusive modes like RGBA has been removed as a result (`#103`_)
* An issue with out-of-order calls to :meth:`~PiCamera.stop_recording` when
  multiple recordings were active was resolved (`#105`_)
* Finally, picamera caught up with raspistill and raspivid by offering a
  friendly error message when used with a disabled camera - thanks to Andrew
  Scheller (lurch) for the suggestion! (`#89`_)

.. _#89: https://github.com/waveform80/picamera/issues/89
.. _#94: https://github.com/waveform80/picamera/issues/94
.. _#95: https://github.com/waveform80/picamera/issues/95
.. _#97: https://github.com/waveform80/picamera/issues/97
.. _#103: https://github.com/waveform80/picamera/issues/103
.. _#105: https://github.com/waveform80/picamera/issues/105
.. _#107: https://github.com/waveform80/picamera/issues/107


Release 1.4 (2014-05-06)
========================

1.4 mostly involved bug fixes with a couple of new bits of functionality:

* The *sei* parameter was added to :meth:`~PiCamera.start_recording` to permit
  inclusion of "Supplemental Enhancement Information" in the output stream
  (`#77`_)
* The :attr:`~PiCamera.awb_gains` attribute was added to permit manual control
  of the auto-white-balance red/blue gains (`#74`_)
* A bug which cause :meth:`~PiCamera.split_recording` to fail when low
  framerates were configured was fixed (`#87`_)
* A bug which caused picamera to fail when used in UNIX-style daemons, unless
  the module was imported *after* the double-fork to background was fixed
  (`#85`_)
* A bug which caused the :attr:`~PiCamera.frame` attribute to fail when queried
  in Python 3 was fixed (`#80`_)
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
* The :meth:`~PiCamera.record_sequence` method was added to provide a cleaner
  interface for recording multiple consecutive video clips (`#53`_)
* The *splitter_port* parameter was added to all capture methods and
  :meth:`~PiCamera.start_recording` to permit recording multiple simultaneous
  video streams (presumably with different options, primarily *resize*)
  (`#56`_)
* The limits on the :attr:`~PiCamera.framerate` attribute were increased after
  firmware #656 introduced numerous new camera modes including 90fps recording
  (at lower resolutions) (`#65`_)

And partly bug fixes:

* It was reported that Exif metadata (including thumbnails) wasn't fully
  recorded in JPEG output (`#59`_)
* Raw captures with :meth:`~PiCamera.capture_continuous` and
  :meth:`~PiCamera.capture_sequence` were broken (`#55`_)

.. _#52: https://github.com/waveform80/picamera/issues/52
.. _#53: https://github.com/waveform80/picamera/issues/53
.. _#55: https://github.com/waveform80/picamera/issues/55
.. _#56: https://github.com/waveform80/picamera/issues/56
.. _#59: https://github.com/waveform80/picamera/issues/59
.. _#65: https://github.com/waveform80/picamera/issues/65


Release 1.2 (2014-02-02)
========================

1.2 was mostly a bug fix release:

* A bug introduced in 1.1 caused :meth:`~PiCamera.split_recording` to fail if
  it was preceded by a video-port-based image capture (`#49`_)
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
* The new :attr:`~PiCamera.frame` attribute permits querying information about
  the frame last written to the output stream (number, timestamp, size,
  keyframe, etc.) (`#34`_, `#36`_)
* All capture methods (:meth:`~PiCamera.capture` et al), and the
  :meth:`~PiCamera.start_recording` method now accept a ``resize`` parameter
  which invokes a resizer prior to the encoding step (`#21`_)
* A new :class:`~PiCameraCircularIO` stream class is provided to permit holding
  the last *n* seconds of video in memory, ready for writing out to disk (or
  whatever you like) (`#39`_)
* There's a new way to specify raw captures - simply use the format you require
  with the capture method of your choice. As a result of this, the
  :attr:`~PiCamera.raw_format` attribute is now deprecated (`#32`_)

Some bugs were also fixed:

* GPIO.cleanup is no longer called on :meth:`~PiCamera.close` (`#35`_), and
  GPIO set up is only done on first use of the :attr:`~PiCamera.led` attribute
  which should resolve issues that users have been having with using picamera
  in conjunction with GPIO
* Raw RGB video-port based image captures are now working again too (`#32`_)

As this is a new major-version, all deprecated elements were removed:

* The continuous method was removed; this was replaced by
  :meth:`~PiCamera.capture_continuous` in 0.5 (`#7`_)

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
  :meth:`~PiCamera.split_recording` method, and requires that the
  :meth:`~PiCamera.start_recording` method was called with *inline_headers* set
  to True. The latter has now been made the default (technically this is a
  backwards incompatible change, but it's relatively trivial and I don't
  anticipate anyone's code breaking because of this change).

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
  :meth:`~PiCamera.start_recording` method
* Fixed bugs in the :attr:`~PiCamera.crop` property
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

* New ``'raw'`` format added to all capture methods (:meth:`~PiCamera.capture`,
  :meth:`~PiCamera.capture_continuous`, and :meth:`~PiCamera.capture_sequence`)
  to permit capturing of raw sensor data
* New :attr:`~PiCamera.raw_format` attribute to permit control of raw format
  (defaults to ``'yuv'``, only other setting currently is ``'rgb'``)
* New :attr:`~PiCamera.shutter_speed` attribute to permit manual control of
  shutter speed (defaults to 0 for automatic shutter speed, and requires latest
  firmware to operate - use ``sudo rpi-update`` to upgrade)
* New "Recipes" chapter in the documentation which demonstrates a wide variety
  of capture techniques ranging from trivial to complex


Release 0.5 (2013-10-21)
========================

In 0.5, the major features added were:

* New :meth:`~PiCamera.capture_sequence` method
* :meth:`~PiCamera.continuous` method renamed to
  :meth:`~PiCamera.capture_continuous`. Old method name retained for
  compatiblity until 1.0.
* *use_video_port* option for :meth:`~PiCamera.capture_sequence` and
  :meth:`~PiCamera.capture_continuous` to allow rapid capture of JPEGs via
  video port
* New :attr:`~PiCamera.framerate` attribute to control video
  and rapid-image capture frame rates
* Default value for :attr:`~PiCamera.ISO` changed from 400 to 0 (auto) which
  fixes :attr:`~PiCamera.exposure_mode` not working by default
* *intraperiod* and *profile* options for :meth:`~PiCamera.start_recording`

In addition a few bugs were fixed:

* Byte strings not being accepted by :meth:`~PiCamera.continuous`
* Erroneous docs for :attr:`~PiCamera.ISO`

Many thanks to the community for the bug reports!

Release 0.4 (2013-10-11)
========================

In 0.4, several new attributes were introduced for configuration of the preview
window:

* :attr:`~PiCamera.preview_alpha`
* :attr:`~PiCamera.preview_fullscreen`
* :attr:`~PiCamera.preview_window`

Also, a new method for rapid continual capture of still images was introduced:
:meth:`~PiCamera.continuous`.

Release 0.3 (2013-10-04)
========================

The major change in 0.3 was the introduction of custom Exif tagging for
captured images, and fixing a silly bug which prevented more than one image
being captured during the lifetime of a PiCamera instance.

Release 0.2
===========

The major change in 0.2 was support for video recording, along with the new
:attr:`~PiCamera.resolution` property which replaced the separate
``preview_resolution`` and ``stills_resolution`` properties.


