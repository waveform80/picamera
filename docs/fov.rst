.. _camera_hardware:

===============
Camera Hardware
===============

.. currentmodule:: picamera

This chapter attempts to provide an overview of the operation of the camera
under various conditions, as well as to provide an introduction to the low
level software interface that picamera utilizes.


.. _operations:

Theory of Operation
===================

The Pi's camera module is, essentially, a mobile phone camera module. Mobile
phone digital cameras differ from their larger, more expensive, brethren
(DSLRs) in several respects. The most important of these, for understanding the
camera's operation, is that many mobile cameras (including the Pi's camera
module) use a `rolling shutter`_. When the camera needs to capture a frame, it
reads out values from the sensor a line at a time rather than gathering all
values in one consistent read.

What do we mean by "values"? Quite simply sensor counts; the more photons pass
through the `bayer filter`_ and hit the sensor elements, the more those
elements increment their counters. When a line of elements is read back, the
counters are reset. The longer the line read-out time, the more photons can
fall on the sensor elements, and the higher the counter's values.

Reading out a line of elements takes a certain minimum time. This minimum time
influences the maximum framerate that the camera can achieve in various modes.
Conversely, this implies that if the camera's :attr:`~PiCamera.framerate` is
set to a certain value, it necessarily limits the amount of time available for
reading sensor lines, and indeed this is so: the
:attr:`~PiCamera.exposure_speed` attribute is limited by the framerate.
Framerate adjustments, as done with :attr:`~PiCamera.framerate_delta` are
achieved by manipulating the number of "padding" lines added to the end of a
frame.

At this point, a reader familiar with operating system theory may be
questioning how a non-real-time operating system like Linux could possibly be
reading lines from the sensor? After all, to ensure each line is read in
exactly the same amount of time (to ensure a constant exposure over the whole
image) would require precision timing, which cannot be guaranteed in a
non-real-time OS. The answer is quite simply that Linux *doesn't* control the
sensor.

In fact, none of the camera processing occurs on the CPU at all.  Instead, it
is done on the Pi's GPU (VideoCore IV) which is running its own real-time OS
(VCOS). From the Linux side we merely send "messages" to VCOS requesting that
it do certain things (initialize the camera, set an exposure time, configure a
JPEG encoder, begin streaming data), and from time to time VCOS sends messages
back (e.g. here's a frame of JPEG encoded data).

The diagram below roughly illustrates the architecture of the system:

.. image:: images/camera_architecture.*
    :align: center

The other important factor influencing sensor counts, aside from line read-out
time, is the sensor's gain. Specifically, the gain given by the
:attr:`~PiCamera.analog_gain` attribute. The corresponding
:attr:`~PiCamera.digital_gain` attribute refers to a manipulation of the sensor
counts done in the GPU after frame read-out has completed (i.e.
post-processing). In fact *all* controls other than analog gain and line
read-out time ("shutter speed") are GPU post-processing in some form or
another.

The analog gain cannot be *directly* controlled in picamera, but various
attributes can be used to "influence" it.

* Setting :attr:`~PiCamera.exposure_mode` to ``'off'`` locks the analog (and
  digital) gains at their current values and doesn't allow them to adjust at
  all, no matter what happens to the scene, and no matter what other camera
  attributes may be adjusted.

* Setting :attr:`~PiCamera.exposure_mode` to values other than ``'off'``
  permits the gains to "float" according to the auto-exposure mode selected.
  The camera firmware always prefers to adjust the analog gain when possible,
  as digital gain produces more noise. Some examples of the factors that the
  auto-exposure modes target:

  - ``'sports'`` prefers higher gain to increasing exposure time (i.e. line
    read-out time) to reduce motion blur.

  - ``'night'`` is intended as a stills mode so it permits very long exposure
    times while attempting to keep gains low.

* The :attr:`~PiCamera.iso` attribute effectively represents another set of
  auto-exposure modes with specific gains:

  - With the V1 camera module, ISO 100 attempts to use an overall gain of 1.0.
    ISO 200 attempts to use an overall gain of 2.0, and so on.

  - With the V2 camera module, calibration was performed against the relevant
    standard. Hence ISO 100 produces an overall gain of ~1.84. ISO 60 produces
    overall gain of 1.0, and ISO 800 of 14.72.

You can observe the effect of the auto-exposure algorithm quite easily during
daylight. Ensure the camera module is pointed at something bright like the sky
or the view through a window, and query the camera's analog gain and exposure
time:

.. code-block:: pycon

    >>> camera = PiCamera()
    >>> camera.start_preview(alpha=192)
    >>> float(camera.analog_gain)
    1.0
    >>> camera.exposure_speed
    3318

Now, force the camera to use a higher gain by setting ISO to 800. If you have
the preview running, you'll see very little difference in the scene. However,
if you subsequently query the exposure time you'll find the firmware has
drastically reduced it to compensate for the higher sensor gain:

.. code-block:: pycon

    >>> camera.iso = 800
    >>> camera.exposure_speed
    198

You can force a longer exposure time with the :attr:`~PiCamera.shutter_speed`
attribute at which point the scene will become quite washed out (because both
the gain and exposure time are now fixed). If you let the gain float again by
setting ISO back to automatic (0) you should find the gain reduces accordingly
and the scene returns more or less to normal:

.. code-block:: pycon

    >>> camera.shutter_speed = 4000
    >>> camera.exposure_speed
    3998
    >>> camera.iso = 0
    >>> float(camera.analog_gain)
    1.0

The camera's auto-exposure algorithm attempts to produce a scene with a target
Y (`luminance`_) value (or values) within the constraints set by things like
ISO, shutter speed, and so forth. The target Y value can be adjusted with the
:attr:`~PiCamera.exposure_compensation` attribute which is measured in
increments of 1/6th of an `f-stop`_. So if, whilst the exposure time is fixed,
you increase the luminance that the camera is aiming for by a couple of stops,
then wait a few seconds you should find that the gain has increased
accordingly:

.. code-block:: pycon

    >>> camera.exposure_compensation = 12
    >>> float(camera.analog_gain)
    1.48046875

If you allow the exposure time to float once more (by setting
:attr:`~PiCamera.shutter_speed` back to 0), then wait a few seconds, you should
find the analog gain decreases back to 1.0, but the exposure time increases to
maintain the deliberately over-exposed appearance of the scene:

.. code-block:: pycon

    >>> camera.shutter_speed = 0
    >>> float(camera.analog_gain)
    1.0
    >>> camera.exposure_speed
    4244

.. _camera_modes:

Sensor Modes
============

The Pi's camera has a discrete set of input modes. On the V1 module these are
as follows:

+---+------------+--------------+-------------+-------+-------+---------+---------+
| # | Resolution | Aspect Ratio | Framerates  | Video | Image | FoV     | Binning |
+===+============+==============+=============+=======+=======+=========+=========+
| 1 | 1920x1080  | 16:9         | 1-30fps     | x     |       | Partial | None    |
+---+------------+--------------+-------------+-------+-------+---------+---------+
| 2 | 2592x1944  | 4:3          | 1-15fps     | x     | x     | Full    | None    |
+---+------------+--------------+-------------+-------+-------+---------+---------+
| 3 | 2592x1944  | 4:3          | 0.1666-1fps | x     | x     | Full    | None    |
+---+------------+--------------+-------------+-------+-------+---------+---------+
| 4 | 1296x972   | 4:3          | 1-42fps     | x     |       | Full    | 2x2     |
+---+------------+--------------+-------------+-------+-------+---------+---------+
| 5 | 1296x730   | 16:9         | 1-49fps     | x     |       | Full    | 2x2     |
+---+------------+--------------+-------------+-------+-------+---------+---------+
| 6 | 640x480    | 4:3          | 42.1-60fps  | x     |       | Full    | 4x4     |
+---+------------+--------------+-------------+-------+-------+---------+---------+
| 7 | 640x480    | 4:3          | 60.1-90fps  | x     |       | Full    | 4x4     |
+---+------------+--------------+-------------+-------+-------+---------+---------+

.. note::

    This table is accurate as of firmware revision #656. Firmwares prior to
    this had a more restricted set of modes, and all video modes had partial
    FoV. Please use ``sudo apt-get dist-upgrade`` to upgrade to the latest
    firmware.

On the V2 module, these are:

+---+------------+--------------+------------+-------+-------+---------+---------+
| # | Resolution | Aspect Ratio | Framerates | Video | Image | FoV     | Binning |
+===+============+==============+============+=======+=======+=========+=========+
| 1 | 1920x1080  | 16:9         | 0.1-30fps  | x     |       | Partial | None    |
+---+------------+--------------+------------+-------+-------+---------+---------+
| 2 | 3280x2464  | 4:3          | 0.1-15fps  | x     | x     | Full    | None    |
+---+------------+--------------+------------+-------+-------+---------+---------+
| 3 | 3280x2464  | 4:3          | 0.1-15fps  | x     | x     | Full    | None    |
+---+------------+--------------+------------+-------+-------+---------+---------+
| 4 | 1640x1232  | 4:3          | 0.1-40fps  | x     |       | Full    | 2x2     |
+---+------------+--------------+------------+-------+-------+---------+---------+
| 5 | 1640x922   | 16:9         | 0.1-40fps  | x     |       | Full    | 2x2     |
+---+------------+--------------+------------+-------+-------+---------+---------+
| 6 | 1280x720   | 16:9         | 40-90fps   | x     |       | Partial | 2x2     |
+---+------------+--------------+------------+-------+-------+---------+---------+
| 7 | 640x480    | 4:3          | 40-90fps   | x     |       | Partial | 2x2     |
+---+------------+--------------+------------+-------+-------+---------+---------+

Modes with full field of view (FoV) capture from the whole area of the camera's
sensor (2592x1944 pixels for the V1 camera, 3280x2464 for the V2 camera).
Modes with partial FoV capture from the center of the sensor. The combination
of FoV limiting, and `binning`_ is used to achieve the requested resolution.

The image below illustrates the difference between full and partial field of
view for the V1 camera:

.. image:: images/sensor_area_1.png
    :width: 640px
    :align: center

While the various fields of view for the V2 camera are illustrated in the
following image:

.. image:: images/sensor_area_2.png
    :width: 640px
    :align: center

The input mode can be manually specified with the *sensor_mode* parameter in
the :class:`PiCamera` constructor (using one of the values from the # column in
the tables above). This defaults to 0 indicating that the mode should be
selected automatically based on the requested :attr:`~PiCamera.resolution` and
:attr:`~PiCamera.framerate`. The rules governing which input mode is selected
are as follows:

* The mode must be acceptable. Video modes can be used for video recording, or
  for image captures from the video port (i.e. when *use_video_port* is
  ``True`` in calls to the various capture methods). Image captures when
  *use_video_port* is ``False`` must use an image mode (of which only two
  exist, both with the maximum resolution).

* The closer the requested :attr:`~PiCamera.resolution` is to the mode's
  resolution the better, but downscaling from a higher input resolution is
  preferable to upscaling from a lower input resolution.

* The requested :attr:`~PiCamera.framerate` should be within the range of the
  input mode.

* The closer the aspect ratio of the requested :attr:`~PiCamera.resolution` to
  the mode's resolution, the better. Attempts to set resolutions with aspect
  ratios other than 4:3 or 16:9 (which are the only ratios directly supported
  by the modes in the table above) will choose the mode which maximizes the
  resulting FoV.

A few examples are given below to clarify the operation of this heuristic (note
these examples assume the V1 camera module):

* If you set the :attr:`~PiCamera.resolution` to 1024x768 (a 4:3 aspect ratio),
  and :attr:`~PiCamera.framerate` to anything less than 42fps, the 1296x972
  mode will be selected, and the camera will downscale the result to 1024x768.

* If you set the :attr:`~PiCamera.resolution` to 1280x720 (a 16:9 wide-screen
  aspect ratio), and :attr:`~PiCamera.framerate` to anything less than 49fps,
  the 1296x730 mode will be selected and downscaled appropriately.

* Setting :attr:`~PiCamera.resolution` to 1920x1080 and
  :attr:`~PiCamera.framerate` to 30fps exceeds the resolution of both the
  1296x730 and 1296x972 modes (i.e. they would require upscaling), so the
  1920x1080 mode is selected instead, although it has a reduced FoV.

* A :attr:`~PiCamera.resolution` of 800x600 and a :attr:`~PiCamera.framerate`
  of 60fps will select the 640x480 60fps mode, even though it requires
  upscaling because the algorithm considers the framerate to take precedence in
  this case.

* Any attempt to capture an image without using the video port will
  (temporarily) select the 2592x1944 mode while the capture is performed (this
  is what causes the flicker you sometimes see when a preview is running while
  a still image is captured).


.. _hardware_limits:

Hardware Limits
===============

The are additional limits imposed by the GPU hardware that performs all
image and video processing:

* The maximum resolution for MJPEG recording depends partially on GPU
  memory. If you get "Out of resource" errors with MJPEG recording at high
  resolutions, try increasing ``gpu_mem`` in ``/boot/config.txt``.

* The maximum horizontal resolution for default H264 recording is 1920.
  Any attempt to recording H264 video at higher horizontal resolutions
  will fail.

* However, H264 high profile level 4.2 has slightly higher limits and may
  succeed with higher resolutions.

* The maximum resolution of the V2 camera may require additional GPU memory
  when operating at low framerates (<1fps). Increase ``gpu_mem`` in
  ``/boot/config.txt`` if you encounter "out of resources" errors when
  attempting long-exposure captures with a V2 module.

* The maximum resolution of the V2 camera can also cause issues with previews.
  Currently, picamera runs previews at the same resolution as captures
  (equivalent to ``-fp`` in ``raspistill``).  You may need to increase
  ``gpu_mem`` in ``/boot/config.txt`` to achieve full resolution operation with
  the V2 camera module, or configure the preview to use a lower
  :attr:`~PiPreviewRenderer.resolution` than the camera itself.

* The maximum framerate of the camera depends on several factors. With
  overclocking, 120fps has been achieved on a V2 module but 90fps is the
  maximum supported framerate.

* The maximum exposure time is currently 6 seconds on the V1 camera
  module, and 10 seconds on the V2 camera module. Remember that exposure
  time is limited by framerate, so you need to set an extremely slow
  :attr:`~picamera.PiCamera.framerate` before setting
  :attr:`~picamera.PiCamera.shutter_speed`.


.. _under_the_hood:

MMAL
====

The MMAL layer below picamera presents the camera with three ports: the
still port, the video port, and the preview port. The following sections
describe how these ports are used by picamera and how they influence the
camera's resolutions.

The Still Port
--------------

Firstly, the still port. Whenever this is used to capture images, it (briefly)
forces the camera's mode to one of the two supported still modes (see
:ref:`camera_modes`) so that images are captured using the full area of the
sensor. It also uses a strong de-noise algorithm on captured images so that
they appear higher quality.

The still port is used by the various :meth:`~PiCamera.capture` methods when
their *use_video_port* parameter is ``False`` (which it is by default).

The Video Port
--------------

The video port is somewhat simpler in that it never changes the camera's mode.
The video port is used by the :meth:`~PiCamera.start_recording` method (for
recording video), and is also used by the various :meth:`~PiCamera.capture`
methods when their *use_video_port* parameter is ``True``. Images captured from
the video port tend to have a "grainy" appearance, much more akin to a video
frame than the images captured by the still port (this is due to the still port
using a slower, more aggressive denoise algorithm).

The Preview Port
----------------

The preview port operates more or less identically to the video port. The
preview port is always connected to some form of output to ensure that the
auto-gain algorithm can run. When an instance of :class:`PiCamera` is
constructed, the preview port is initially connected to an instance of
:class:`PiNullSink`.  When :meth:`~PiCamera.start_preview` is called, this null
sink is destroyed and the preview port is connected to an instance of
:class:`~PiPreviewRenderer`. The reverse occurs when
:meth:`~PiCamera.stop_preview` is called.

Pipelines
---------

This section attempts to provide detail of what MMAL pipelines picamera
constructs in response to various method calls.

The firmware provides various encoders which can be attached to the still and
video ports for the purpose of producing output (e.g. JPEG images or H.264
encoded video). A port can have a single encoder attached to it at any given
time (or nothing if the port is not in use).

Encoders are connected directly to the still port. For example, when capturing
a picture using the still port, the camera's state conceptually moves through
these states:

.. image:: images/still_port_capture.*
    :align: center

As you have probably noticed in the diagram above, the video port is a little
more complex. In order to permit simultaneous video recording and image capture
via the video port, a "splitter" component is permanently connected to the
video port by picamera, and encoders are in turn attached to one of its four
output ports (numbered 0, 1, 2, and 3). Hence, when recording video the
camera's setup looks like this:

.. image:: images/video_port_record.*
    :align: center

And when simultaneously capturing images via the video port whilst recording,
the camera's configuration moves through the following states:

.. image:: images/video_port_capture.*
    :align: center

When the ``resize`` parameter is passed to one of the aforementioned methods, a
resizer component is placed between the camera's ports and the encoder, causing
the output to be resized before it reaches the encoder. This is particularly
useful for video recording, as the H.264 encoder cannot cope with full
resolution input (the GPU hardware can only handle frame widths up to 1920
pixels). Hence, when performing full frame video recording, the camera's setup
looks like this:

.. image:: images/video_fullfov_record.*
    :align: center

Finally, when performing unencoded captures an encoder is (naturally) not
required.  Instead data is taken directly from the camera's ports. However,
various firmware limitations require acrobatics in the pipeline to achieve
requested encodings.

For example, in older firmwares the camera's still port cannot be configured
for RGB output (due to a faulty buffer size check). However, they can be
configured for YUV output so in this case picamera configures the still port
for YUV output, attaches as resizer (configured with the same input and output
resolution), then configures the resizer's output for RGBA (the resizer doesn't
support RGB for some reason). It then runs the capture and strips the redundant
alpha bytes off the data.

Recent firmwares fix the buffer size check, so with these picamera will
simply configure the still port for RGB output (since 1.11):

.. image:: images/still_raw_capture.*
    :align: center

Encodings
---------

The ports used to connect MMAL components together pass image data around in
particular encodings. Often, this is the `YUV420`_ encoding. On rare occasions
it is `RGB`_ (RGB is a large and rather inefficient format). However, another
format sometimes used is the "OPAQUE" encoding.

"OPAQUE" is the most efficient encoding to use when connecting MMAL components
as it simply passes pointers around under the hood rather than full frame data
(as such it's not really an encoding at all, but it's treated as such by the
MMAL framework). However, not all OPAQUE encodings are equivalent:

* The preview port's OPAQUE encoding contains a single image.

* The video port's OPAQUE encoding contains two images (used for motion
  estimation by various encoders).

* The still port's OPAQUE encoding contains strips of a single image.

* The JPEG image encoder accepts the still port's OPAQUE strips format.

* The MJPEG video encoder does *not* accept the OPAQUE strips format, only
  the single and dual image variants provided by the preview or video ports.

* The H264 video encoder in older firmwares only accepts the dual image
  OPAQUE format (it will accept full-frame YUV input instead though). In newer
  firmwares it now accepts the single image OPAQUE format too (presumably
  constructing the second image itself for motion estimation).

* The splitter accepts single or dual image OPAQUE input, but only outputs
  single image OPAQUE input (or YUV; in later firmwares it also
  supports RGB or BGR output).

* The resizer theoretically accepts OPAQUE input (though the author hasn't
  managed to get this working at the time of writing) but will only produce
  YUV/RGBA/BGRA output.

The new :mod:`~picamera.mmalobj` layer introduced in picamera 1.11 is aware of
these OPAQUE encoding differences and attempts to configure connections between
components with the most efficient formats possible. However, it is not aware
of firmware revisions so if you're playing with MMAL components via this layer
be prepared to do some tinkering to get your pipeline working.

Please note that even the description above is almost certainly far removed
from what actually happens at the camera's ISP level. Rather, what has been
described in this section is how the MMAL library exposes the camera to
applications which utilize it (these include the picamera library, along with
the official ``raspistill`` and ``raspivid`` applications).

In other words, by using picamera you are passing through (at least) two
abstraction layers which necessarily obscure (but hopefully simplify) the
"true" operation of the camera.


.. _binning: http://www.andor.com/learning-academy/ccd-binning-what-does-binning-mean
.. _rolling shutter: http://en.wikipedia.org/wiki/Rolling_shutter
.. _bayer filter: http://en.wikipedia.org/wiki/Bayer_filter
.. _f-stop: https://en.wikipedia.org/wiki/F-number
.. _luminance: https://en.wikipedia.org/wiki/Relative_luminance
.. _YUV420: http://en.wikipedia.org/wiki/YUV#Y.27UV420p_.28and_Y.27V12_or_YV12.29_to_RGB888_conversion
.. _RGB: http://en.wikipedia.org/wiki/RGB
