.. _recipes2:

================
Advanced Recipes
================

.. currentmodule:: picamera

The following recipes involve advanced techniques and may not be "beginner
friendly". Please feel free to suggest enhancements or additional recipes.

.. warning::

    When trying out these scripts do *not* name your file :file:`picamera.py`.
    Naming scripts after existing Python modules will cause errors when you
    try and import those modules (because Python checks the current directory
    before checking other paths).


.. _array_capture:

Capturing to a numpy array
==========================

Since 1.11, picamera can capture directly to any object which supports Python's
buffer protocol (including numpy's :class:`~numpy.ndarray`). Simply pass the
object as the destination of the capture and the image data will be written
directly to the object. The target object must fulfil various requirements
(some of which are dependent on the version of Python you are using):

1. The buffer object must be writeable (e.g. you cannot capture to a
   :class:`bytes` object as it is immutable).

2. The buffer object must be large enough to receive all the image data.

3. (Python 2.x only) The buffer object must be 1-dimensional.

4. (Python 2.x only) The buffer object must have byte-sized items.

For example, to capture directly to a three-dimensional numpy
:class:`~numpy.ndarray` (Python 3.x only):

.. literalinclude:: examples/array_capture_py3.py

It is also important to note that when outputting to unencoded formats, the
camera rounds the requested resolution. The horizontal resolution is rounded up
to the nearest multiple of 32 pixels, while the vertical resolution is rounded
up to the nearest multiple of 16 pixels. For example, if the requested
resolution is 100x100, the capture will actually contain 128x112 pixels worth
of data, but pixels beyond 100x100 will be uninitialized.

So, to capture a 100x100 image we first need to provide a 128x112 array,
then strip off the uninitialized pixels afterward. The following example
demonstrates this along with the re-shaping necessary under Python 2.x:

.. literalinclude:: examples/array_capture_py2.py


.. warning::

    Under certain circumstances (non-resized, non-YUV, video-port captures),
    the resolution is rounded to 16x16 blocks instead of 32x16. Adjust your
    resolution rounding accordingly.

.. versionadded:: 1.11


.. _opencv_capture:

Capturing to an OpenCV object
=============================

This is a variation on :ref:`array_capture`. `OpenCV`_ uses numpy arrays as
images and defaults to colors in planar BGR. Hence, the following is all that's
required to capture an OpenCV compatible image:

.. literalinclude:: examples/opencv_capture.py

.. versionchanged:: 1.11
    Replaced recipe with direct array capture example.


.. _yuv_capture:

Unencoded image capture (YUV format)
====================================

If you want images captured without loss of detail (due to JPEG's lossy
compression), you are probably better off exploring PNG as an alternate image
format (PNG uses lossless compression). However, some applications
(particularly scientific ones) simply require the image data in numeric form.
For this, the ``'yuv'`` format is provided:

.. literalinclude:: examples/yuv_capture1.py

The specific `YUV`_ format used is `YUV420`_ (planar). This means that the Y
(luminance) values occur first in the resulting data and have full resolution
(one 1-byte Y value for each pixel in the image). The Y values are followed by
the U (chrominance) values, and finally the V (chrominance) values.  The UV
values have one quarter the resolution of the Y components (4 1-byte Y values
in a square for each 1-byte U and 1-byte V value). This is illustrated in the
diagram below:

.. image:: images/yuv420.*
    :align: center

It is also important to note that when outputting to unencoded formats, the
camera rounds the requested resolution. The horizontal resolution is rounded up
to the nearest multiple of 32 pixels, while the vertical resolution is rounded
up to the nearest multiple of 16 pixels. For example, if the requested
resolution is 100x100, the capture will actually contain 128x112 pixels worth
of data, but pixels beyond 100x100 will be uninitialized.

Given that the `YUV420`_ format contains 1.5 bytes worth of data for each pixel
(a 1-byte Y value for each pixel, and 1-byte U and V values for every 4 pixels),
and taking into account the resolution rounding, the size of a 100x100 YUV
capture will be:

.. math::
    :nowrap:

    \begin{equation}
    \begin{array}[b]{rl}
        128.0 & \text{100 rounded up to nearest multiple of 32} \\
        \times \quad 112.0 & \text{100 rounded up to nearest multiple of 16} \\
        \times \qquad 1.5 & \text{bytes of data per pixel in YUV420 format} \\
        \hline
        21504.0 & \text{bytes total}
    \end{array}
    \end{equation}

The first 14336 bytes of the data (128*112) will be Y values, the next 3584
bytes (:math:`128 \times 112 \div 4`) will be U values, and the final 3584
bytes will be the V values.

The following code demonstrates capturing YUV image data, loading the data into
a set of `numpy`_ arrays, and converting the data to RGB format in an efficient
manner:

.. literalinclude:: examples/yuv_capture2.py

.. note::

    You may note that we are using :func:`open` in the code above instead of
    :func:`io.open` as in the other examples. This is because numpy's
    :func:`numpy.fromfile` method annoyingly only accepts "real" file objects.

This recipe is now encapsulated in the :class:`~array.PiYUVArray` class in the
:mod:`picamera.array` module, which means the same can be achieved as follows:

.. literalinclude:: examples/yuv_capture3.py

As of 1.11 you can also capture directly to numpy arrays (see
:ref:`array_capture`). Due to the difference in resolution of the Y and UV
components, this isn't directly useful (if you need all three components,
you're better off using :class:`~array.PiYUVArray` as this rescales the UV
components for convenience). However, if you only require the Y plane you can
provide a buffer just large enough for this plane and ignore the error that
occurs when writing to the buffer (picamera will deliberately write as much as
it can to the buffer before raising an exception to support this use-case):

.. literalinclude:: examples/yuv_capture4.py

Alternatively, see :ref:`rgb_capture` for a method of having the camera output
RGB data directly.

.. note::

    Capturing so-called "raw" formats (``'yuv'``, ``'rgb'``, etc.) does not
    provide the raw bayer data from the camera's sensor. Rather, it provides
    access to the image data after GPU processing, but before format encoding
    (JPEG, PNG, etc). Currently, the only method of accessing the raw bayer
    data is via the *bayer* parameter to the :meth:`~PiCamera.capture` method.
    See :ref:`bayer_data` for more information.

.. versionchanged:: 1.0
    The :attr:`~PiCamera.raw_format` attribute is now deprecated, as is the
    ``'raw'`` format specification for the :meth:`~PiCamera.capture` method.
    Simply use the ``'yuv'`` format instead, as shown in the code above.

.. versionchanged:: 1.5
    Added note about new :mod:`picamera.array` module.

.. versionchanged:: 1.11
    Added instructions for direct array capture.


.. _rgb_capture:

Unencoded image capture (RGB format)
====================================

The RGB format is rather larger than the `YUV`_ format discussed in the section
above, but is more useful for most analyses. To have the camera produce output
in `RGB`_ format, you simply need to specify ``'rgb'`` as the format for the
:meth:`~PiCamera.capture` method instead:

.. literalinclude:: examples/rgb_capture1.py

The size of `RGB`_ data can be calculated similarly to `YUV`_ captures.
Firstly round the resolution appropriately (see :ref:`yuv_capture` for the
specifics), then multiply the number of pixels by 3 (1 byte of red, 1 byte of
green, and 1 byte of blue intensity). Hence, for a 100x100 capture, the amount
of data produced is:

.. math::
    :nowrap:

    \begin{equation}
    \begin{array}[b]{rl}
        128.0 & \text{100 rounded up to nearest multiple of 32} \\
        \times \quad 112.0 & \text{100 rounded up to nearest multiple of 16} \\
        \times \qquad 3.0 & \text{bytes of data per pixel in RGB format} \\
        \hline
        43008.0 & \text{bytes total}
    \end{array}
    \end{equation}

.. warning::

    Under certain circumstances (non-resized, non-YUV, video-port captures),
    the resolution is rounded to 16x16 blocks instead of 32x16. Adjust your
    resolution rounding accordingly.

The resulting `RGB`_ data is interleaved. That is to say that the red, green
and blue values for a given pixel are grouped together, in that order. The
first byte of the data is the red value for the pixel at (0, 0), the second
byte is the green value for the same pixel, and the third byte is the blue
value for that pixel. The fourth byte is the red value for the pixel at (1, 0),
and so on.

As the planes in `RGB`_ data are all equally sized (in contrast to `YUV420`_)
it is trivial to capture directly into a numpy array (Python 3.x only; see
:ref:`array_capture` for Python 2.x instructions):

.. literalinclude:: examples/rgb_capture2.py

.. note::

    RGB captures from the still port do not work at the full resolution of the
    camera (they result in an out of memory error). Either use YUV captures, or
    capture from the video port if you require full resolution.

.. versionchanged:: 1.0
    The :attr:`~PiCamera.raw_format` attribute is now deprecated, as is the
    ``'raw'`` format specification for the :meth:`~PiCamera.capture` method.
    Simply use the ``'rgb'`` format instead, as shown in the code above.

.. versionchanged:: 1.5
    Added note about new :mod:`picamera.array` module.

.. versionchanged:: 1.11
    Added instructions for direct array capture.


.. _custom_outputs:

Custom outputs
==============

All methods in the picamera library which accept a filename also accept
file-like objects. Typically, this is only used with actual file objects, or
with memory streams (like :class:`io.BytesIO`). However, building a custom
output object is extremely easy and in certain cases very useful. A file-like
object (as far as picamera is concerned) is simply an object with a ``write``
method which must accept a single parameter consisting of a byte-string, and
which can optionally return the number of bytes written. The object can
optionally implement a ``flush`` method (which has no parameters), which will
be called at the end of output.

Custom outputs are particularly useful with video recording as the custom
output's ``write`` method will be called (at least) once for every frame that
is output, allowing you to implement code that reacts to each and every frame
without going to the bother of a full :ref:`custom encoder <custom_encoders>`.
However, one should bear in mind that because the ``write`` method is called so
frequently, its implementation must be sufficiently rapid that it doesn't stall
the encoder (it must perform its processing and return before the next write is
due to arrive if you wish to avoid dropping frames).

The following trivial example demonstrates an incredibly simple custom output
which simply throws away the output while counting the number of bytes that
would have been written and prints this at the end of the output:

.. literalinclude:: examples/custom_outputs_count.py

The following example shows how to use a custom output to construct a crude
motion detection system. We construct a custom output object which is used as
the destination for motion vector data (this is particularly simple as motion
vector data always arrives as single chunks; frame data by contrast sometimes
arrives in several separate chunks). The output object doesn't actually write
the motion data anywhere; instead it loads it into a numpy array and analyses
whether there are any significantly large vectors in the data, printing a
message to the console if there are. As we are not concerned with keeping the
actual video output in this example, we use :file:`/dev/null` as the
destination for the video data:

.. literalinclude:: examples/custom_outputs_motion_detector.py

You may wish to investigate the classes in the :mod:`picamera.array` module
which implement several custom outputs for analysis of data with numpy. In
particular, the :class:`~array.PiMotionAnalysis` class can be used to remove
much of the boiler plate code from the recipe above:

.. literalinclude:: examples/custom_outputs_motion_analysis.py

.. versionadded:: 1.5


.. _weird_outputs:

Unconventional file outputs
===========================

As noted in prior sections, picamera accepts a wide variety of things as an
output:

* A string, which will be treated as a filename.
* A file-like object, e.g. as returned by :func:`open`.
* A :ref:`custom output <custom_outputs>`.
* Any mutable object that implements the buffer interface.

The simplest of these, the filename, hides a certain amount of complexity. It
can be important to understand exactly how picamera treats files, especially
when dealing with "unconventional" files (e.g. pipes, FIFOs, etc.)

When given a filename, picamera does the following:

1. Opens the specified file with the ``'wb'`` mode, i.e. open for writing,
   truncating the file first, in binary mode.

2. The file is opened with a larger-than-normal buffer size, specifically 64Kb.
   A large buffer size is utilized because it improves performance and system
   load with the majority use-case, i.e. sequentially writing video to the
   disk.

3. The requested data (image captures, video recording, etc.) is written to the
   open file.

4. Finally, the file is flushed and closed. Note that this is the only
   circumstance in which picamera will presume to close the output for you,
   because picamera opened the output for you.

As noted above, this fits the majority use case (sequentially writing video to
a file) very well. However, if you are piping data to another process via a
FIFO (which picamera will simply treat as any other file), you may wish to
avoid all the buffering. In this case, you can simply open the output yourself
with no buffering. As noted above, you will then be responsible for closing the
output when you are finished with it (you opened it, so the responsibility for
closing it is yours as well).

For example:

.. literalinclude:: examples/weird_outputs.py


.. _rapid_capture:

Rapid capture and processing
============================

The camera is capable of capturing a sequence of images extremely rapidly by
utilizing its video-capture capabilities with a JPEG encoder (via the
*use_video_port* parameter). However, there are several things to note about
using this technique:

* When using video-port based capture only the video recording area is
  captured; in some cases this may be smaller than the normal image capture
  area (see discussion in :ref:`camera_modes`).

* No Exif information is embedded in JPEG images captured through the
  video-port.

* Captures typically appear "grainier" with this technique. Captures from the
  still port use a slower, more intensive denoise algorithm.

All capture methods support the *use_video_port* option, but the methods differ
in their ability to rapidly capture sequential frames. So, whilst
:meth:`~PiCamera.capture` and :meth:`~PiCamera.capture_continuous` both support
*use_video_port*, :meth:`~PiCamera.capture_sequence` is by far the fastest
method (because it does not re-initialize an encoder prior to each capture).
Using this method, the author has managed 30fps JPEG captures at a resolution
of 1024x768.

By default, :meth:`~PiCamera.capture_sequence` is particularly suited to
capturing a fixed number of frames rapidly, as in the following example which
captures a "burst" of 5 images:

.. literalinclude:: examples/rapid_capture_sequence.py

We can refine this slightly by using a generator expression to provide the
filenames for processing instead of specifying every single filename manually:

.. literalinclude:: examples/rapid_capture_generator.py

However, this still doesn't let us capture an arbitrary number of frames until
some condition is satisfied. To do this we need to use a generator function to
provide the list of filenames (or more usefully, streams) to the
:meth:`~PiCamera.capture_sequence` method:

.. literalinclude:: examples/rapid_capture_yield.py

The major issue with capturing this rapidly is firstly that the Raspberry Pi's
IO bandwidth is extremely limited and secondly that, as a format, JPEG is
considerably less efficient than the H.264 video format (which is to say that,
for the same number of bytes, H.264 will provide considerably better quality
over the same number of frames). At higher resolutions (beyond 800x600) you are
likely to find you cannot sustain 30fps captures to the Pi's SD card for very
long (before exhausting the disk cache).

If you are intending to perform processing on the frames after capture, you may
be better off just capturing video and decoding frames from the resulting file
rather than dealing with individual JPEG captures. Thankfully this is
relatively easy as the JPEG format has a simple `magic number`_ (``FF D8``).
This means we can use a :ref:`custom output <custom_outputs>` to separate the
frames out of an MJPEG video recording by inspecting the first two bytes of
each buffer:

.. literalinclude:: examples/rapid_capture_mjpeg.py

So far, we've just saved the captured frames to disk. This is fine if you're
intending to process later with another script, but what if we want to perform
all processing within the current script? In this case, we may not need to
involve the disk (or network) at all. We can set up a pool of parallel threads
to accept and process image streams as captures come in:

.. literalinclude:: examples/rapid_capture_threading.py


.. _rgb_recording:

Unencoded video capture
=======================

Just as unencoded RGB data can be captured as images, the Pi's camera module
can also capture an unencoded stream of RGB (or YUV) video data. Combining this with
the methods presented in :ref:`custom_outputs` (via the classes from
:mod:`picamera.array`), we can produce a fairly rapid color detection script:

.. literalinclude:: examples/color_detect.py


.. _rapid_streaming:

Rapid capture and streaming
===========================

Following on from :ref:`rapid_capture`, we can combine the video capture
technique with :ref:`streaming_capture`. The server side script doesn't change
(it doesn't really care what capture technique is being used - it just reads
JPEGs off the wire). The changes to the client side script can be minimal at
first - just set *use_video_port* to ``True`` in the
:meth:`~PiCamera.capture_continuous` call:

.. literalinclude:: examples/rapid_streaming.py

Using this technique, the author can manage about 19fps of streaming at
640x480. However, utilizing the MJPEG splitting demonstrated in
:ref:`rapid_capture` we can manage much faster:

.. literalinclude:: examples/rapid_streaming_mjpeg.py

The above script achieves 30fps with ease.


.. _web_streaming:

Web streaming
=============

Streaming video over the web is surprisingly complicated. At the time of
writing, there are still no video standards that are universally supported by
all web browsers on all platforms. Furthermore, HTTP was originally designed as
a one-shot protocol for serving web-pages. Since its invention, various
additions have been bolted on to cater for its ever increasing use cases (file
downloads, resumption, streaming, etc.) but the fact remains there's no
"simple" solution for video streaming at the moment.

If you want to have a play with streaming a "real" video format (specifically,
MPEG1) you may want to have a look at the `pistreaming`_ demo. However, for the
purposes of this recipe we'll be using a much simpler format: MJPEG. The
following script uses Python's built-in :mod:`http.server` module to make a
simple video streaming server:

.. literalinclude:: examples/web_streaming.py

Once the script is running, visit ``http://your-pi-address:8000/`` with your
web-browser to view the video stream.

.. note::

    This recipe assumes Python 3.x (the ``http.server`` module was named
    ``SimpleHTTPServer`` in Python 2.x)


.. _record_and_capture:

Capturing images whilst recording
=================================

The camera is capable of capturing still images while it is recording video.
However, if one attempts this using the stills capture mode, the resulting
video will have dropped frames during the still image capture. This is because
images captured via the still port require a mode change, causing the dropped
frames (this is the flicker to a higher resolution that one sees when capturing
while a preview is running).

However, if the *use_video_port* parameter is used to force a video-port based
image capture (see :ref:`rapid_capture`) then the mode change does not occur,
and the resulting video should not have dropped frames, assuming the image can
be produced before the next video frame is due:

.. literalinclude:: examples/record_and_capture.py

The above code should produce a 20 second video with no dropped frames, and a
still frame from 10 seconds into the video. Higher resolutions or non-JPEG
image formats may still cause dropped frames (only JPEG encoding is hardware
accelerated).


.. _multi_res_record:

Recording at multiple resolutions
=================================

The camera is capable of recording multiple streams at different resolutions
simultaneously by use of the video splitter. This is probably most useful for
performing analysis on a low-resolution stream, while simultaneously recording
a high resolution stream for storage or viewing.

The following simple recipe demonstrates using the *splitter_port* parameter of
the :meth:`~PiCamera.start_recording` method to begin two simultaneous
recordings, each with a different resolution:

.. literalinclude:: examples/multi_res_record.py

There are 4 splitter ports in total that can be used (numbered 0, 1, 2, and 3).
The video recording methods default to using splitter port 1, while the image
capture methods default to splitter port 0 (when the *use_video_port* parameter
is also True). A splitter port cannot be simultaneously used for video
recording and image capture so you are advised to avoid splitter port 0 for
video recordings unless you never intend to capture images whilst recording.

.. versionadded:: 1.3


.. _motion_data_output:

Recording motion vector data
============================

The Pi's camera is capable of outputting the motion vector estimates that the
camera's H.264 encoder calculates while generating compressed video. These can
be directed to a separate output file (or file-like object) with the
*motion_output* parameter of the :meth:`~PiCamera.start_recording` method. Like
the normal *output* parameter this accepts a string representing a filename, or
a file-like object:

.. literalinclude:: examples/motion_data1.py

Motion data is calculated at the `macro-block`_ level (an MPEG macro-block
represents a 16x16 pixel region of the frame), and includes one extra column of
data. Hence, if the camera's resolution is 640x480 (as in the example above)
there will be 41 columns of motion data (:math:`(640 \div 16) + 1`), in 30 rows
(:math:`480 \div 16`).

Motion data values are 4-bytes long, consisting of a signed 1-byte x vector, a
signed 1-byte y vector, and an unsigned 2-byte SAD (`Sum of Absolute
Differences`_) value for each macro-block.  Hence in the example above, each
frame will generate 4920 bytes of motion data (:math:`41 \times 30 \times 4`).
Assuming the data contains 300 frames (in practice it may contain a few more)
the motion data should be 1,476,000 bytes in total.

The following code demonstrates loading the motion data into a
three-dimensional numpy array. The first dimension represents the frame, with
the latter two representing rows and finally columns. A structured data-type
is used for the array permitting easy access to x, y, and SAD values:

.. literalinclude:: examples/motion_data2.py

You can calculate the amount of motion the vector represents simply by
calculating the `magnitude of the vector`_ with Pythagoras' theorem. The SAD
(`Sum of Absolute Differences`_) value can be used to determine how well the
encoder thinks the vector represents the original reference frame.

The following code extends the example above to use PIL to produce a PNG image
from the magnitude of each frame's motion vectors:

.. literalinclude:: examples/motion_data3.py

You may wish to investigate the :class:`~array.PiMotionArray` and
:class:`~array.PiMotionAnalysis` classes in the :mod:`picamera.array` module
which simplifies the above recipes to the following:

.. literalinclude:: examples/motion_data4.py

The following command line can be used to generate an animation from the
generated PNGs with ffmpeg (this will take a *very* long time on the Pi so you
may wish to transfer the images to a faster machine for this step):

.. code-block:: bash

    avconv -r 30 -i frame%03d.png -filter:v scale=640:480 -c:v libx264 motion.mp4

Finally, as a demonstration of what can be accomplished with motion vectors,
here's a gesture detection system:

.. literalinclude:: examples/gesture_detect.py

Within a few inches of the camera, move your hand up, down, left, and right,
parallel to the camera and you should see the direction displayed on the
console.

.. versionadded:: 1.5


.. _circular_record2:

Splitting to/from a circular stream
===================================

This example builds on the one in :ref:`circular_record1` and the one in
:ref:`record_and_capture` to demonstrate the beginnings of a security
application. As before, a :class:`PiCameraCircularIO` instance is used to keep
the last few seconds of video recorded in memory.  While the video is being
recorded, video-port-based still captures are taken to provide a motion
detection routine with some input (the actual motion detection algorithm is
left as an exercise for the reader).

Once motion is detected, the last 10 seconds of video are written to disk, and
video recording is split to another disk file to proceed until motion is no
longer detected. Once motion is no longer detected, we split the recording back
to the in-memory ring-buffer:

.. literalinclude:: examples/circular_record2.py

This example also demonstrates using the *seconds* parameter of the
:meth:`~PiCameraCircularIO.copy_to` method to limit the before file to 10
seconds of data (given that the circular buffer may contain considerably more
than this).

.. versionadded:: 1.0

.. versionchanged:: 1.11
    Added use of :meth:`~PiCameraCircularIO.copy_to`


.. _custom_encoders:

Custom encoders
===============

You can override and/or extend the encoder classes used during image or video
capture. This is particularly useful with video capture as it allows you to run
your own code in response to every frame, although naturally whatever code runs
within the encoder's callback has to be reasonably quick to avoid stalling the
encoder pipeline.

Writing a custom encoder is quite a bit harder than writing a :ref:`custom
output <custom_outputs>` and in most cases there's little benefit. The only
thing a custom encoder gives you that a custom output doesn't is access to the
buffer header flags. For many output formats (MJPEG and YUV for example), these
won't tell you anything interesting (i.e. they'll simply indicate that the
buffer contains a full frame and nothing else). Currently, the only format
where the buffer header flags contain useful information is H.264. Even then,
most of the information (I-frame, P-frame, motion information, etc.) would be
accessible from the :attr:`~PiCamera.frame` attribute which you could access
from your custom output's ``write`` method.

The encoder classes defined by picamera form the following hierarchy (dark
classes are actually instantiated by the implementation in picamera, light
classes implement base functionality but aren't technically "abstract"):

.. image:: images/encoder_classes.*
    :align: center

The following table details which :class:`PiCamera` methods use which encoder
classes, and which method they call to construct these encoders:

.. tabularcolumns:: |p{52mm}|p{42mm}|p{53mm}|

+--------------------------------------+---------------------------------------+------------------------------------+
| Method(s)                            | Calls                                 | Returns                            |
+======================================+=======================================+====================================+
| :meth:`~PiCamera.capture`            | :meth:`~PiCamera._get_image_encoder`  | :class:`PiCookedOneImageEncoder`   |
| :meth:`~PiCamera.capture_continuous` |                                       | :class:`PiRawOneImageEncoder`      |
| :meth:`~PiCamera.capture_sequence`   |                                       |                                    |
+--------------------------------------+---------------------------------------+------------------------------------+
| :meth:`~PiCamera.capture_sequence`   | :meth:`~PiCamera._get_images_encoder` | :class:`PiCookedMultiImageEncoder` |
|                                      |                                       | :class:`PiRawMultiImageEncoder`    |
+--------------------------------------+---------------------------------------+------------------------------------+
| :meth:`~PiCamera.start_recording`    | :meth:`~PiCamera._get_video_encoder`  | :class:`PiCookedVideoEncoder`      |
| :meth:`~PiCamera.record_sequence`    |                                       | :class:`PiRawVideoEncoder`         |
+--------------------------------------+---------------------------------------+------------------------------------+

It is recommended, particularly in the case of the image encoder classes, that
you familiarize yourself with the specific function of these classes so that
you can determine the best class to extend for your particular needs. You may
find that one of the intermediate classes is a better basis for your own
modifications.

In the following example recipe we will extend the
:class:`PiCookedVideoEncoder` class to store how many I-frames and P-frames are
captured (the camera's encoder doesn't use B-frames):

.. literalinclude:: examples/custom_encoders.py

Please note that the above recipe is flawed: PiCamera is capable of
initiating :ref:`multiple simultaneous recordings <multi_res_record>`. If this
were used with the above recipe, then each encoder would wind up incrementing
the ``i_frames`` and ``p_frames`` attributes on the ``MyCamera`` instance
leading to incorrect results.

.. versionadded:: 1.5


.. _bayer_data:

Raw Bayer data captures
=======================

The ``bayer`` parameter of the :meth:`~PiCamera.capture` method causes the raw
Bayer data recorded by the camera's sensor to be output as part of the image
meta-data.

.. note::

    The ``bayer`` parameter only operates with the JPEG format, and only
    for captures from the still port (i.e. when ``use_video_port`` is False,
    as it is by default).

Raw Bayer data differs considerably from simple unencoded captures; it is the
data recorded by the camera's sensor prior to *any* GPU processing including
auto white balance, vignette compensation, smoothing, down-scaling,
etc. This also means:

* Bayer data is *always* full resolution, regardless of the camera's output
  :attr:`~PiCamera.resolution` and any ``resize`` parameter.

* Bayer data occupies the last 6,404,096 bytes of the output file for the V1
  module, or the last 10,270,208 bytes for the V2 module. The first 32,768
  bytes of this is header data which starts with the string ``'BRCM'``.

* Bayer data consists of 10-bit values, because this is the sensitivity of the
  `OV5647`_ and `IMX219`_ sensors used in the Pi's camera modules. The 10-bit
  values are organized as 4 8-bit values, followed by the low-order 2-bits of
  the 4 values packed into a fifth byte.

.. image:: images/bayer_bytes.*
    :align: center

* Bayer data is organized in a BGGR pattern (a minor variation of the common
  `Bayer CFA`_). The raw data therefore has twice as many green pixels as red
  or blue and if viewed "raw" will look distinctly strange (too dark, too
  green, and with zippering effects along any straight edges).

.. image:: images/bayer_pattern.*
    :align: center

* To make a "normal" looking image from raw Bayer data you will need to
  perform `de-mosaicing`_ at the very least, and probably some form of
  `color balance`_.

This (heavily commented) example script causes the camera to capture an image
including the raw Bayer data. It then proceeds to unpack the Bayer data into a
3-dimensional `numpy`_ array representing the raw RGB data and finally performs
a rudimentary de-mosaic step with weighted averages. A couple of numpy tricks
are used to improve performance but bear in mind that all processing is
happening on the CPU and will be considerably slower than normal image
captures:

.. literalinclude:: examples/bayer_data.py

An enhanced version of this recipe (which also handles different bayer orders
caused by flips and rotations) is also encapsulated in the
:class:`~picamera.array.PiBayerArray` class in the :mod:`picamera.array`
module, which means the same can be achieved as follows:

.. literalinclude:: examples/bayer_array.py

.. versionadded:: 1.3

.. versionchanged:: 1.5
    Added note about new :mod:`picamera.array` module.


.. _flash_configuration:

Using a flash with the camera
=============================

The Pi's camera module includes an LED flash driver which can be used to
illuminate a scene upon capture. The flash driver has two configurable GPIO
pins:

* one for connection to an LED based flash (xenon flashes won't work with the
  camera module due to it having a `rolling shutter`_). This will fire before
  (`flash metering`_) and during capture
* one for an optional privacy indicator (a requirement for cameras in some
  jurisdictions). This will fire after taking a picture to indicate that the
  camera has been used

These pins are configured by updating the `VideoCore device tree blob`_.
Firstly, install the device tree compiler, then grab a copy of the default
device tree source:

.. code-block:: console

    $ sudo apt-get install device-tree-compiler
    $ wget https://github.com/raspberrypi/firmware/raw/master/extra/dt-blob.dts

The device tree source contains a number of sections enclosed in curly braces,
which form a hierarchy of definitions. The section to edit will depend on which
revision of Raspberry Pi you have (check the silk-screen writing on the board
for the revision number if you are unsure):

+--------------------------------+----------------------------+
| Model                          | Section                    |
+================================+============================+
| Raspberry Pi Model B rev 1     | ``/videocore/pins_rev1``   |
+--------------------------------+----------------------------+
| Raspberry Pi Model A and       | ``/videocore/pins_rev2``   |
| Model B rev 2                  |                            |
+--------------------------------+----------------------------+
| Raspberry Pi Model A+          | ``/videocore/pins_aplus``  |
+--------------------------------+----------------------------+
| Raspberry Pi Model B+ rev 1.1  | ``/videocore/pins_bplus1`` |
+--------------------------------+----------------------------+
| Raspberry Pi Model B+ rev 1.2  | ``/videocore/pins_bplus2`` |
+--------------------------------+----------------------------+
| Raspberry Pi 2 Model B rev 1.0 | ``/videocore/pins_2b1``    |
+--------------------------------+----------------------------+
| Raspberry Pi 2 Model B rev 1.1 | ``/videocore/pins_2b2``    |
| and rev 1.2                    |                            |
+--------------------------------+----------------------------+
| Raspberry Pi 3 Model B rev 1.0 | ``/videocore/pins_3b1``    |
+--------------------------------+----------------------------+
| Raspberry Pi 3 Model B rev 1.2 | ``/videocore/pins_3b2``    |
+--------------------------------+----------------------------+
| Raspberry Pi Zero rev 1.2 and  | ``/videocore/pins_pi0``    |
| rev 1.3                        |                            |
+--------------------------------+----------------------------+
| Raspberry Pi Zero Wireless     | ``/videocore/pins_pi0w``   |
| rev 1.1                        |                            |
+--------------------------------+----------------------------+

Under the section for your particular model of Pi you will find ``pin_config``
and ``pin_defines`` sections. Under the ``pin_config`` section you need to
configure the GPIO pins you want to use for the flash and privacy indicator as
using pull down termination. Then, under the ``pin_defines`` section you need
to associate those pins with the ``FLASH_0_ENABLE`` and ``FLASH_0_INDICATOR``
pins.

For example, to configure GPIO 17 as the flash pin, leaving the privacy
indicator pin absent, on a Raspberry Pi 2 Model B rev 1.1 you would add the
following line under the ``/videocore/pins_2b2/pin_config`` section:

.. code-block:: text

    pin@p17 { function = "output"; termination = "pull_down"; };

Please note that GPIO pins will be numbered according to the `Broadcom pin
numbers`_ (BCM mode in the RPi.GPIO library, *not* BOARD mode). Then change the
following section under ``/videocore/pins_2b2/pin_defines``. Specifically,
change the type from "absent" to "internal", and add a number property defining
the flash pin as GPIO 17:

.. code-block:: text

    pin_define@FLASH_0_ENABLE {
        type = "internal";
        number = <17>;
    };

With the device tree source updated, you now need to compile it into a binary
blob for the firmware to read. This is done with the following command line:

.. code-block:: console

    $ dtc -q -I dts -O dtb dt-blob.dts -o dt-blob.bin

Dissecting this command line, the following components are present:

* ``dtc`` - Execute the device tree compiler

* ``-I dts`` - The input file is in device tree source format

* ``-O dtb`` - The output file should be produced in device tree binary format

* ``dt-blob.dts`` - The first anonymous parameter is the input filename

* ``-o dt-blob.bin`` - The output filename

This should output nothing. If you get lots of warnings, you've forgotten the
``-q`` switch; you can ignore the warnings. If anything else is output, it will
most likely be an error message indicating you have made a mistake in the
device tree source. In this case, review your edits carefully (note that
sections and properties *must* be semi-colon terminated for example), and try
again.

Now the device tree binary blob has been produced, it needs to be placed on the
first partition of the SD card. In the case of non-NOOBS Raspbian installs,
this is generally the partition mounted as ``/boot``:

.. code-block:: console

    $ sudo cp dt-blob.bin /boot/

However, in the case of NOOBS Raspbian installs, this is the recovery
partition, which is not mounted by default:

.. code-block:: console

    $ sudo mkdir /mnt/recovery
    $ sudo mount /dev/mmcblk0p1 /mnt/recovery
    $ sudo cp dt-blob.bin /mnt/recovery
    $ sudo umount /mnt/recovery
    $ sudo rmdir /mnt/recovery

Please note that the filename and location are important. The binary blob must
be named ``dt-blob.bin`` (all lowercase), and it must be placed in the root
directory of the first partition on the SD card. Once you have rebooted the Pi
(to activate the new device tree configuration) you can test the flash with the
following simple script::

    import picamera

    with picamera.PiCamera() as camera:
        camera.flash_mode = 'on'
        camera.capture('foo.jpg')

You should see your flash LED blink twice during the execution of the script.

.. warning::

    The GPIOs only have a limited current drive which is insufficient for
    powering the sort of LEDs typically used as flashes in mobile phones. You
    will require a suitable drive circuit to power such devices, or risk
    damaging your Pi. One developer on the Pi forums notes:

        For reference, the flash driver chips we have used on mobile phones
        will often drive up to 500mA into the LED. If you're aiming for that,
        then please think about your power supply too.

If you wish to experiment with the flash driver without attaching anything to
the GPIO pins, you can also reconfigure the camera's own LED to act as the
flash LED. Obviously this is no good for actual flash photography but it can
demonstrate whether your configuration is good. In this case you need not add
anything to the ``pin_config`` section (the camera's LED pin is already defined
to use pull down termination), but you do need to set ``CAMERA_0_LED`` to
absent, and ``FLASH_0_ENABLE`` to the old ``CAMERA_0_LED`` definition (this
will be pin 5 in the case of ``pins_rev1`` and ``pins_rev2``, and pin 32 in the
case of everything else). For example, change:

.. code-block:: text

    pin_define@CAMERA_0_LED {
        type = "internal";
        number = <5>;
    };
    pin_define@FLASH_0_ENABLE {
        type = "absent";
    };

into this:

.. code-block:: text

    pin_define@CAMERA_0_LED {
        type = "absent";
    };
    pin_define@FLASH_0_ENABLE {
        type = "internal";
        number = <5>;
    };

After compiling and installing the device tree blob according to the
instructions above, and rebooting the Pi, you should find the camera LED now
acts as a flash LED with the Python script above.

.. versionadded:: 1.10


.. _YUV: https://en.wikipedia.org/wiki/YUV
.. _YUV420: https://en.wikipedia.org/wiki/YUV#Y.E2.80.B2UV420p_.28and_Y.E2.80.B2V12_or_YV12.29_to_RGB888_conversion
.. _RGB: https://en.wikipedia.org/wiki/RGB
.. _RGBA: https://en.wikipedia.org/wiki/RGBA_color_space
.. _numpy: http://www.numpy.org/
.. _ring buffer: https://en.wikipedia.org/wiki/Circular_buffer
.. _OV5647: http://www.ovt.com/products/sensor.php?id=66
.. _IMX219: http://www.sony.net/Products/SC-HP/new_pro/april_2014/imx219_e.html
.. _Bayer CFA: https://en.wikipedia.org/wiki/Bayer_filter
.. _de-mosaicing: https://en.wikipedia.org/wiki/Demosaicing
.. _color balance: https://en.wikipedia.org/wiki/Color_balance
.. _macro-block: https://en.wikipedia.org/wiki/Macroblock
.. _magnitude of the vector: https://en.wikipedia.org/wiki/Magnitude_%28mathematics%29#Euclidean_vector_space
.. _Sum of Absolute Differences: https://en.wikipedia.org/wiki/Sum_of_absolute_differences
.. _rolling shutter: https://en.wikipedia.org/wiki/Rolling_shutter
.. _VideoCore device tree blob: https://www.raspberrypi.org/documentation/configuration/pin-configuration.md
.. _flash metering: https://en.wikipedia.org/wiki/Through-the-lens_metering#Through_the_lens_flash_metering
.. _Broadcom pin numbers: https://raspberrypi.stackexchange.com/questions/12966/what-is-the-difference-between-board-and-bcm-for-gpio-pin-numbering
.. _OpenCV: http://opencv.org/
.. _magic number: https://en.wikipedia.org/wiki/Magic_number_(programming)#Magic_numbers_in_files
.. _pistreaming: https://github.com/waveform80/pistreaming/

