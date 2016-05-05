.. _recipes2:

================
Advanced Recipes
================

.. currentmodule:: picamera

The following recipes involve advanced techniques and may not be "beginner
friendly". Please feel free to suggest enhancements or additional recipes.


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
:class:`~numpy.ndarray` (Python 3.x only)::

    import time
    import picamera
    import numpy as np

    with picamera.PiCamera() as camera:
        camera.resolution = (320, 240)
        camera.framerate = 24
        time.sleep(2)
        output = np.empty((240, 320, 3), dtype=np.uint8)
        camera.capture(output, 'rgb')

It is also important to note that when outputting to unencoded formats, the
camera rounds the requested resolution. The horizontal resolution is rounded up
to the nearest multiple of 32 pixels, while the vertical resolution is rounded
up to the nearest multiple of 16 pixels. For example, if the requested
resolution is 100x100, the capture will actually contain 128x112 pixels worth
of data, but pixels beyond 100x100 will be uninitialized.

So, to capture a 100x100 image we first need to provide a 128x112 array,
then strip off the uninitialized pixels afterward. The following example
demonstrates this along with the re-shaping necessary under Python 2.x::

    import time
    import picamera
    import numpy as np

    with picamera.PiCamera() as camera:
        camera.resolution = (100, 100)
        camera.framerate = 24
        time.sleep(2)
        output = np.empty((112 * 128 * 3,), dtype=np.uint8)
        camera.capture(output, 'rgb')
        output = output.reshape((112, 128, 3))
        output = output[:100, :100, :]

.. versionadded:: 1.11


.. _opencv_capture:

Capturing to an OpenCV object
=============================

This is a variation on :ref:`array_capture`. `OpenCV`_ uses numpy arrays as
images and defaults to colors in planar BGR. Hence, the following is all that's
required to capture an OpenCV compatible image (under Python 3.x)::

    import time
    import picamera
    import numpy as np
    import cv2

    with picamera.PiCamera() as camera:
        camera.resolution = (320, 240)
        camera.framerate = 24
        time.sleep(2)
        image = np.empty((240, 320, 3), dtype=np.uint8)
        camera.capture(image, 'bgr')

.. versionchanged:: 1.11
    Replaced recipe with direct array capture example.


.. _yuv_capture:

Unencoded image capture (YUV format)
====================================

If you want images captured without loss of detail (due to JPEG's lossy
compression), you are probably better off exploring PNG as an alternate image
format (PNG uses lossless compression). However, some applications
(particularly scientific ones) simply require the image data in numeric form.
For this, the ``'yuv'`` format is provided::

    import time
    import picamera

    with picamera.PiCamera() as camera:
        camera.resolution = (100, 100)
        camera.start_preview()
        time.sleep(2)
        camera.capture('image.data', 'yuv')

The specific `YUV`_ format used is `YUV420`_ (planar). This means that the Y
(luminance) values occur first in the resulting data and have full resolution
(one 1-byte Y value for each pixel in the image). The Y values are followed by
the U (chrominance) values, and finally the V (chrominance) values.  The UV
values have one quarter the resolution of the Y components (4 1-byte Y values
in a square for each 1-byte U and 1-byte V value). This is illustrated in the
diagram below:

.. image:: yuv420.*
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

.. image:: yuv_math.*
    :align: center

The first 14336 bytes of the data (128*112) will be Y values, the next 3584
bytes (128*112/4) will be U values, and the final 3584 bytes will be the V
values.

The following code demonstrates capturing YUV image data, loading the data into
a set of `numpy`_ arrays, and converting the data to RGB format in an efficient
manner::

    from __future__ import division

    import time
    import picamera
    import numpy as np

    width = 100
    height = 100
    stream = open('image.data', 'w+b')
    # Capture the image in YUV format
    with picamera.PiCamera() as camera:
        camera.resolution = (width, height)
        camera.start_preview()
        time.sleep(2)
        camera.capture(stream, 'yuv')
    # Rewind the stream for reading
    stream.seek(0)
    # Calculate the actual image size in the stream (accounting for rounding
    # of the resolution)
    fwidth = (width + 31) // 32 * 32
    fheight = (height + 15) // 16 * 16
    # Load the Y (luminance) data from the stream
    Y = np.fromfile(stream, dtype=np.uint8, count=fwidth*fheight).\
            reshape((fheight, fwidth))
    # Load the UV (chrominance) data from the stream, and double its size
    U = np.fromfile(stream, dtype=np.uint8, count=(fwidth//2)*(fheight//2)).\
            reshape((fheight//2, fwidth//2)).\
            repeat(2, axis=0).repeat(2, axis=1)
    V = np.fromfile(stream, dtype=np.uint8, count=(fwidth//2)*(fheight//2)).\
            reshape((fheight//2, fwidth//2)).\
            repeat(2, axis=0).repeat(2, axis=1)
    # Stack the YUV channels together, crop the actual resolution, convert to
    # floating point for later calculations, and apply the standard biases
    YUV = np.dstack((Y, U, V))[:height, :width, :].astype(np.float)
    YUV[:, :, 0]  = YUV[:, :, 0]  - 16   # Offset Y by 16
    YUV[:, :, 1:] = YUV[:, :, 1:] - 128  # Offset UV by 128
    # YUV conversion matrix from ITU-R BT.601 version (SDTV)
    #              Y       U       V
    M = np.array([[1.164,  0.000,  1.596],    # R
                  [1.164, -0.392, -0.813],    # G
                  [1.164,  2.017,  0.000]])   # B
    # Take the dot product with the matrix to produce RGB output, clamp the
    # results to byte range and convert to bytes
    RGB = YUV.dot(M.T).clip(0, 255).astype(np.uint8)

.. note::

    You may note that we are using :func:`open` in the code above instead of
    :func:`io.open` as in the other examples. This is because numpy's
    :func:`numpy.fromfile` method annoyingly only accepts "real" file objects.

This recipe is now encapsulated in the :class:`~array.PiYUVArray` class in the
:mod:`picamera.array` module, which means the same can be achieved as follows::

    import time
    import picamera
    import picamera.array

    with picamera.PiCamera() as camera:
        with picamera.array.PiYUVArray(camera) as stream:
            camera.resolution = (100, 100)
            camera.start_preview()
            time.sleep(2)
            camera.capture(stream, 'yuv')
            # Show size of YUV data
            print(stream.array.shape)
            # Show size of RGB converted data
            print(stream.rgb_array.shape)

As of 1.11 you can also capture directly to numpy arrays (see
:ref:`array_capture`). Due to the difference in resolution of the Y and UV
components, this isn't directly useful (if you need all three components,
you're better off using :class:`~array.PiYUVArray` as this rescales the UV
components for convenience). However, if you only require the Y plane you can
provide a buffer just large enough for this plane and ignore the error that
occurs when writing to the buffer (picamera will deliberately write as much as
it can to the buffer before raising an exception to support this use-case)::

    import time
    import picamera
    import picamera.array
    import numpy as np

    with picamera.PiCamera() as camera:
        camera.resolution = (100, 100)
        time.sleep(2)
        y_data = np.empty((112, 128), dtype=np.uint8)
        try:
            camera.capture(y_data, 'yuv')
        except IOError:
            pass
        y_data = y_data[:100, :100]
        # y_data now contains the Y-plane only

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
:meth:`~PiCamera.capture` method instead::

    import time
    import picamera

    with picamera.PiCamera() as camera:
        camera.resolution = (100, 100)
        camera.start_preview()
        time.sleep(2)
        camera.capture('image.data', 'rgb')

The size of `RGB`_ data can be calculated similarly to `YUV`_ captures.
Firstly round the resolution appropriately (see :ref:`yuv_capture` for the
specifics), then multiply the number of pixels by 3 (1 byte of red, 1 byte of
green, and 1 byte of blue intensity). Hence, for a 100x100 capture, the amount
of data produced is:

.. image:: rgb_math.*
    :align: center

The resulting `RGB`_ data is interleaved. That is to say that the red, green
and blue values for a given pixel are grouped together, in that order. The
first byte of the data is the red value for the pixel at (0, 0), the second
byte is the green value for the same pixel, and the third byte is the blue
value for that pixel. The fourth byte is the red value for the pixel at (1, 0),
and so on.

As the planes in `RGB`_ data are all equally sized (in contrast to `YUV420`_)
it is trivial to capture directly into a numpy array (Python 3.x only; see
:ref:`array_capture` for Python 2.x instructions)::

    import time
    import picamera
    import picamera.array
    import numpy as np

    with picamera.PiCamera() as camera:
        camera.resolution = (100, 100)
        time.sleep(2)
        image = np.empty((128, 112, 3), dtype=np.uint8)
        camera.capture(image, 'rgb')
        image = image[:100, :100]

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
captures a "burst" of 5 images::

    import time
    import picamera

    with picamera.PiCamera() as camera:
        camera.resolution = (1024, 768)
        camera.framerate = 30
        camera.start_preview()
        time.sleep(2)
        camera.capture_sequence([
            'image1.jpg',
            'image2.jpg',
            'image3.jpg',
            'image4.jpg',
            'image5.jpg',
            ])

We can refine this slightly by using a generator expression to provide the
filenames for processing instead of specifying every single filename manually::

    import time
    import picamera

    frames = 60

    with picamera.PiCamera() as camera:
        camera.resolution = (1024, 768)
        camera.framerate = 30
        camera.start_preview()
        # Give the camera some warm-up time
        time.sleep(2)
        start = time.time()
        camera.capture_sequence([
            'image%02d.jpg' % i
            for i in range(frames)
            ], use_video_port=True)
        finish = time.time()
    print('Captured %d frames at %.2ffps' % (
        frames,
        frames / (finish - start)))

However, this still doesn't let us capture an arbitrary number of frames until
some condition is satisfied. To do this we need to use a generator function to
provide the list of filenames (or more usefully, streams) to the
:meth:`~PiCamera.capture_sequence` method::

    import time
    import picamera

    frames = 60

    def filenames():
        frame = 0
        while frame < frames:
            yield 'image%02d.jpg' % frame
            frame += 1

    with picamera.PiCamera() as camera:
        camera.resolution = (1024, 768)
        camera.framerate = 30
        camera.start_preview()
        # Give the camera some warm-up time
        time.sleep(2)
        start = time.time()
        camera.capture_sequence(filenames(), use_video_port=True)
        finish = time.time()
    print('Captured %d frames at %.2ffps' % (
        frames,
        frames / (finish - start)))

The major issue with capturing this rapidly is firstly that the Raspberry Pi's
IO bandwidth is extremely limited and secondly that, as a format, JPEG is
considerably less efficient than the H.264 video format (which is to say that,
for the same number of bytes, H.264 will provide considerably better quality
over the same number of frames). At higher resolutions (beyond 800x600) you are
likely to find you cannot sustain 30fps captures to the Pi's SD card for very
long (before exhausting the disk cache).

If you are intending to perform processing on the frames after capture, you may
be better off just capturing video and decoding frames from the resulting file
rather than dealing with individual JPEG captures. Alternatively, you may wish
to investigate sending the data over the network (which typically has more
bandwidth available than the SD card interface) and having another machine
perform any required processing. However, if you can perform your processing
fast enough, you may not need to involve the disk or network at all. Using a
generator function, we can maintain a queue of objects to store the captures,
and have parallel threads accept and process the streams as captures come in.
Provided the processing runs at a faster frame rate than the captures, the
encoder won't stall::

    import io
    import time
    import threading
    import picamera

    # Create a pool of image processors
    done = False
    lock = threading.Lock()
    pool = []

    class ImageProcessor(threading.Thread):
        def __init__(self):
            super(ImageProcessor, self).__init__()
            self.stream = io.BytesIO()
            self.event = threading.Event()
            self.terminated = False
            self.start()

        def run(self):
            # This method runs in a separate thread
            global done
            while not self.terminated:
                # Wait for an image to be written to the stream
                if self.event.wait(1):
                    try:
                        self.stream.seek(0)
                        # Read the image and do some processing on it
                        #Image.open(self.stream)
                        #...
                        #...
                        # Set done to True if you want the script to terminate
                        # at some point
                        #done=True
                    finally:
                        # Reset the stream and event
                        self.stream.seek(0)
                        self.stream.truncate()
                        self.event.clear()
                        # Return ourselves to the pool
                        with lock:
                            pool.append(self)

    def streams():
        while not done:
            with lock:
                if pool:
                    processor = pool.pop()
                else:
                    processor = None
            if processor:
                yield processor.stream
                processor.event.set()
            else:
                # When the pool is starved, wait a while for it to refill
                time.sleep(0.1)

    with picamera.PiCamera() as camera:
        pool = [ImageProcessor() for i in range(4)]
        camera.resolution = (640, 480)
        camera.framerate = 30
        camera.start_preview()
        time.sleep(2)
        camera.capture_sequence(streams(), use_video_port=True)

    # Shut down the processors in an orderly fashion
    while pool:
        with lock:
            processor = pool.pop()
        processor.terminated = True
        processor.join()


.. _rapid_streaming:

Rapid capture and streaming
===========================

Following on from :ref:`rapid_capture`, we can combine the video-port capture
technique with :ref:`streaming_capture`. The server side script doesn't change
(it doesn't really care what capture technique is being used - it just reads
JPEGs off the wire). The changes to the client side script can be minimal at
first - just set *use_video_port* to ``True`` in the
:meth:`~PiCamera.capture_continuous` call::

    import io
    import socket
    import struct
    import time
    import picamera

    client_socket = socket.socket()
    client_socket.connect(('my_server', 8000))
    connection = client_socket.makefile('wb')
    try:
        with picamera.PiCamera() as camera:
            camera.resolution = (640, 480)
            camera.framerate = 30
            time.sleep(2)
            start = time.time()
            stream = io.BytesIO()
            # Use the video-port for captures...
            for foo in camera.capture_continuous(stream, 'jpeg',
                                                 use_video_port=True):
                connection.write(struct.pack('<L', stream.tell()))
                connection.flush()
                stream.seek(0)
                connection.write(stream.read())
                if time.time() - start > 30:
                    break
                stream.seek(0)
                stream.truncate()
        connection.write(struct.pack('<L', 0))
    finally:
        connection.close()
        client_socket.close()

Using this technique, the author can manage about 10fps of streaming at 640x480
on firmware #685. One deficiency of the script above is that it interleaves
capturing images with sending them over the wire (although we deliberately
don't flush on sending the image data). Potentially, it would be more efficient
to permit image capture to occur simultaneously with image transmission. We can
attempt to do this by utilizing the background threading techniques from the
final example in :ref:`rapid_capture`::

    import io
    import socket
    import struct
    import time
    import threading
    import picamera

    client_socket = socket.socket()
    client_socket.connect(('spider', 8000))
    connection = client_socket.makefile('wb')
    try:
        connection_lock = threading.Lock()
        pool_lock = threading.Lock()
        pool = []

        class ImageStreamer(threading.Thread):
            def __init__(self):
                super(ImageStreamer, self).__init__()
                self.stream = io.BytesIO()
                self.event = threading.Event()
                self.terminated = False
                self.start()

            def run(self):
                # This method runs in a background thread
                while not self.terminated:
                    # Wait for the image to be written to the stream
                    if self.event.wait(1):
                        try:
                            with connection_lock:
                                connection.write(struct.pack('<L', self.stream.tell()))
                                connection.flush()
                                self.stream.seek(0)
                                connection.write(self.stream.read())
                        finally:
                            self.stream.seek(0)
                            self.stream.truncate()
                            self.event.clear()
                            with pool_lock:
                                pool.append(self)

        count = 0
        start = time.time()
        finish = time.time()

        def streams():
            global count, finish
            while finish - start < 30:
                with pool_lock:
                    if pool:
                        streamer = pool.pop()
                    else:
                        streamer = None
                if streamer:
                    yield streamer.stream
                    streamer.event.set()
                    count += 1
                else:
                    # When the pool is starved, wait a while for it to refill
                    time.sleep(0.1)
                finish = time.time()

        with picamera.PiCamera() as camera:
            pool = [ImageStreamer() for i in range(4)]
            camera.resolution = (640, 480)
            camera.framerate = 30
            time.sleep(2)
            start = time.time()
            camera.capture_sequence(streams(), 'jpeg', use_video_port=True)

        # Shut down the streamers in an orderly fashion
        while pool:
            streamer = pool.pop()
            streamer.terminated = True
            streamer.join()

        # Write the terminating 0-length to the connection to let the server
        # know we're done
        with connection_lock:
            connection.write(struct.pack('<L', 0))

    finally:
        connection.close()
        client_socket.close()

    print('Sent %d images in %d seconds at %.2ffps' % (
        count, finish-start, count / (finish-start)))

On the same firmware, the above script achieves about 15fps. It is possible the
new high framerate modes may achieve more (the fact that 15fps is half of the
specified 30fps framerate suggests some stall on every other frame).


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
be produced before the next video frame is due::

    import picamera

    with picamera.PiCamera() as camera:
        camera.resolution = (800, 600)
        camera.start_preview()
        camera.start_recording('foo.h264')
        camera.wait_recording(10)
        camera.capture('foo.jpg', use_video_port=True)
        camera.wait_recording(10)
        camera.stop_recording()

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
recordings, each with a different resolution::

    import picamera

    with picamera.PiCamera() as camera:
        camera.resolution = (1024, 768)
        camera.framerate = 30
        camera.start_recording('highres.h264')
        camera.start_recording('lowres.h264', splitter_port=2, resize=(320, 240))
        camera.wait_recording(30)
        camera.stop_recording(splitter_port=2)
        camera.stop_recording()

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
a file-like object::

    import picamera

    with picamera.PiCamera() as camera:
        camera.resolution = (640, 480)
        camera.framerate = 30
        camera.start_recording('motion.h264', motion_output='motion.data')
        camera.wait_recording(10)
        camera.stop_recording()

Motion data is calculated at the `macro-block`_ level (an MPEG macro-block
represents a 16x16 pixel region of the frame), and includes one extra column of
data. Hence, if the camera's resolution is 640x480 (as in the example above)
there will be 41 columns of motion data ((640 / 16) + 1), in 30 rows (480 /
16).

Motion data values are 4-bytes long, consisting of a signed 1-byte x vector, a
signed 1-byte y vector, and an unsigned 2-byte SAD (`Sum of Absolute
Differences`_) value for each macro-block.  Hence in the example above, each
frame will generate 4920 bytes of motion data (41 * 30 * 4). Assuming the data
contains 300 frames (in practice it may contain a few more) the motion data
should be 1,476,000 bytes in total.

The following code demonstrates loading the motion data into a
three-dimensional numpy array. The first dimension represents the frame, with
the latter two representing rows and finally columns. A structured data-type
is used for the array permitting easy access to x, y, and SAD values::

    from __future__ import division

    import numpy as np

    width = 640
    height = 480
    cols = (width + 15) // 16
    cols += 1 # there's always an extra column
    rows = (height + 15) // 16

    motion_data = np.fromfile(
        'motion.data', dtype=[
            ('x', 'i1'),
            ('y', 'i1'),
            ('sad', 'u2'),
            ])
    frames = motion_data.shape[0] // (cols * rows)
    motion_data = motion_data.reshape((frames, rows, cols))

    # Access the data for the first frame
    motion_data[0]

    # Access just the x-vectors from the fifth frame
    motion_data[4]['x']

    # Access SAD values for the tenth frame
    motion_data[9]['sad']

You can calculate the amount of motion the vector represents simply by
calculating the `magnitude of the vector`_ with Pythagoras' theorem. The SAD
(`Sum of Absolute Differences`_) value can be used to determine how well the
encoder thinks the vector represents the original reference frame.

The following code extends the example above to use PIL to produce a PNG image
from the magnitude of each frame's motion vectors::

    from __future__ import division

    import numpy as np
    from PIL import Image

    width = 640
    height = 480
    cols = (width + 15) // 16
    cols += 1
    rows = (height + 15) // 16

    m = np.fromfile(
        'motion.data', dtype=[
            ('x', 'i1'),
            ('y', 'i1'),
            ('sad', 'u2'),
            ])
    frames = m.shape[0] // (cols * rows)
    m = m.reshape((frames, rows, cols))

    for frame in range(frames):
        data = np.sqrt(
            np.square(m[frame]['x'].astype(np.float)) +
            np.square(m[frame]['y'].astype(np.float))
            ).clip(0, 255).astype(np.uint8)
        img = Image.fromarray(data)
        filename = 'frame%03d.png' % frame
        print('Writing %s' % filename)
        img.save(filename)

You may wish to investigate the :class:`~array.PiMotionArray` class in the
:mod:`picamera.array` module which simplifies the above recipes to the
following::

    import numpy as np
    import picamera
    import picamera.array
    from PIL import Image

    with picamera.PiCamera() as camera:
        with picamera.array.PiMotionArray(camera) as stream:
            camera.resolution = (640, 480)
            camera.framerate = 30
            camera.start_recording('/dev/null', format='h264', motion_output=stream)
            camera.wait_recording(10)
            camera.stop_recording()
            for frame in range(stream.array.shape[0]):
                data = np.sqrt(
                    np.square(stream.array[frame]['x'].astype(np.float)) +
                    np.square(stream.array[frame]['y'].astype(np.float))
                    ).clip(0, 255).astype(np.uint8)
                img = Image.fromarray(data)
                filename = 'frame%03d.png' % frame
                print('Writing %s' % filename)
                img.save(filename)

Finally, the following command line can be used to generate an animation from
the generated PNGs with ffmpeg (this will take a *very* long time on the Pi so
you may wish to transfer the images to a faster machine for this step)::

    avconv -r 30 -i frame%03d.png -filter:v scale=640:480 -c:v libx264 motion.mp4

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
to the in-memory ring-buffer::

    import io
    import random
    import picamera
    from PIL import Image

    prior_image = None

    def detect_motion(camera):
        global prior_image
        stream = io.BytesIO()
        camera.capture(stream, format='jpeg', use_video_port=True)
        stream.seek(0)
        if prior_image is None:
            prior_image = Image.open(stream)
            return False
        else:
            current_image = Image.open(stream)
            # Compare current_image to prior_image to detect motion. This is
            # left as an exercise for the reader!
            result = random.randint(0, 10) == 0
            # Once motion detection is done, make the prior image the current
            prior_image = current_image
            return result

    with picamera.PiCamera() as camera:
        camera.resolution = (1280, 720)
        stream = picamera.PiCameraCircularIO(camera, seconds=10)
        camera.start_recording(stream, format='h264')
        try:
            while True:
                camera.wait_recording(1)
                if detect_motion(camera):
                    print('Motion detected!')
                    # As soon as we detect motion, split the recording to
                    # record the frames "after" motion
                    camera.split_recording('after.h264')
                    # Write the 10 seconds "before" motion to disk as well
                    stream.copy_to('before.h264', seconds=10)
                    stream.clear()
                    # Wait until motion is no longer detected, then split
                    # recording back to the in-memory circular buffer
                    while detect_motion(camera):
                        camera.wait_recording(1)
                    print('Motion stopped!')
                    camera.split_recording(stream)
        finally:
            camera.stop_recording()

This example also demonstrates using the *seconds* parameter of the
:meth:`~PiCameraCircularIO.copy_to` method to limit the before file to 10
seconds of data (given that the circular buffer may contain considerably more
than this).

.. versionadded:: 1.0

.. versionchanged:: 1.11
    Added use of :meth:`~PiCameraCircularIO.copy_to`


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
due to arrive).

The following trivial example demonstrates an incredibly simple custom output
which simply throws away the output while counting the number of bytes that
would have been written and prints this at the end of the output::

    from __future__ import print_function

    import picamera

    class MyOutput(object):
        def __init__(self):
            self.size = 0

        def write(self, s):
            self.size += len(s)

        def flush(self):
            print('%d bytes would have been written' % self.size)

    with picamera.PiCamera() as camera:
        camera.resolution = (640, 480)
        camera.framerate = 60
        camera.start_recording(MyOutput(), format='h264')
        camera.wait_recording(10)
        camera.stop_recording()

The following example shows how to use a custom output to construct a crude
motion detection system. We construct a custom output object which is used as
the destination for motion vector data (this is particularly simple as motion
vector data always arrives as single chunks; frame data by contrast sometimes
arrives in several separate chunks). The output object doesn't actually write
the motion data anywhere; instead it loads it into a numpy array and analyses
whether there are any significantly large vectors in the data, printing a
message to the console if there are. As we are not concerned with keeping the
actual video output in this example, we use ``/dev/null`` as the destination
for the video data::

    from __future__ import division

    import picamera
    import numpy as np

    motion_dtype = np.dtype([
        ('x', 'i1'),
        ('y', 'i1'),
        ('sad', 'u2'),
        ])

    class MyMotionDetector(object):
        def __init__(self, camera):
            width, height = camera.resolution
            self.cols = (width + 15) // 16
            self.cols += 1 # there's always an extra column
            self.rows = (height + 15) // 16

        def write(self, s):
            # Load the motion data from the string to a numpy array
            data = np.fromstring(s, dtype=motion_dtype)
            # Re-shape it and calculate the magnitude of each vector
            data = data.reshape((self.rows, self.cols))
            data = np.sqrt(
                np.square(data['x'].astype(np.float)) +
                np.square(data['y'].astype(np.float))
                ).clip(0, 255).astype(np.uint8)
            # If there're more than 10 vectors with a magnitude greater
            # than 60, then say we've detected motion
            if (data > 60).sum() > 10:
                print('Motion detected!')
            # Pretend we wrote all the bytes of s
            return len(s)

    with picamera.PiCamera() as camera:
        camera.resolution = (640, 480)
        camera.framerate = 30
        camera.start_recording(
            # Throw away the video data, but make sure we're using H.264
            '/dev/null', format='h264',
            # Record motion data to our custom output object
            motion_output=MyMotionDetector(camera)
            )
        camera.wait_recording(30)
        camera.stop_recording()

You may wish to investigate the classes in the :mod:`picamera.array` module
which implement several custom outputs for analysis of data with numpy. In
particular, the :class:`~array.PiMotionAnalysis` class can be used to remove
much of the boiler plate code from the recipe above::

    import picamera
    import picamera.array
    import numpy as np

    class MyMotionDetector(picamera.array.PiMotionAnalysis):
        def analyse(self, a):
            a = np.sqrt(
                np.square(a['x'].astype(np.float)) +
                np.square(a['y'].astype(np.float))
                ).clip(0, 255).astype(np.uint8)
            # If there're more than 10 vectors with a magnitude greater
            # than 60, then say we've detected motion
            if (a > 60).sum() > 10:
                print('Motion detected!')

    with picamera.PiCamera() as camera:
        camera.resolution = (640, 480)
        camera.framerate = 30
        camera.start_recording(
            '/dev/null', format='h264',
            motion_output=MyMotionDetector(camera)
            )
        camera.wait_recording(30)
        camera.stop_recording()


.. versionadded:: 1.5


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

The encoder classes defined by picamera form the following hierarchy (shaded
classes are actually instantiated by the implementation in picamera, white
classes implement base functionality but aren't technically "abstract"):

.. image:: encoder_classes.*
    :align: center

The following table details which :class:`PiCamera` methods use which encoder
classes, and which method they call to construct these encoders:

+--------------------------------------+---------------------------------------+------------------------------------+
| Method(s)                            | Call                                  | Returns                            |
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
captured (the camera's encoder doesn't use B-frames)::

    import picamera
    import picamera.mmal as mmal


    # Override PiVideoEncoder to keep track of the number of each type of frame
    class MyEncoder(picamera.PiCookedVideoEncoder):
        def start(self, output, motion_output=None):
            self.parent.i_frames = 0
            self.parent.p_frames = 0
            super(MyEncoder, self).start(output, motion_output)

        def _callback_write(self, buf):
            # Only count when buffer indicates it's the end of a frame, and
            # it's not an SPS/PPS header (..._CONFIG)
            if (
                    (buf[0].flags & mmal.MMAL_BUFFER_HEADER_FLAG_FRAME_END) and
                    not (buf[0].flags & mmal.MMAL_BUFFER_HEADER_FLAG_CONFIG)
                ):
                if buf[0].flags & mmal.MMAL_BUFFER_HEADER_FLAG_KEYFRAME:
                    self.parent.i_frames += 1
                else:
                    self.parent.p_frames += 1
            # Remember to return the result of the parent method!
            return super(MyEncoder, self)._callback_write(buf)


    # Override PiCamera to use our custom encoder for video recording
    class MyCamera(picamera.PiCamera):
        def __init__(self):
            super(MyCamera, self).__init__()
            self.i_frames = 0
            self.p_frames = 0

        def _get_video_encoder(
                self, camera_port, output_port, format, resize, **options):
            return MyEncoder(
                    self, camera_port, output_port, format, resize, **options)


    with MyCamera() as camera:
        camera.start_recording('foo.h264')
        camera.wait_recording(10)
        camera.stop_recording()
        print('Recording contains %d I-frames and %d P-frames' % (
                camera.i_frames, camera.p_frames))

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

* Bayer data occupies the last 6,404,096 bytes of the output file. The first
  32,768 bytes of this is header data which starts with the string ``'BRCM'``.

* Bayer data consists of 10-bit values, because this is the sensitivity of the
  `OV5647`_ sensor used by the Pi's camera. The 10-bit values are organized as
  4 8-bit values, followed by the low-order 2-bits of the 4 values packed into
  a fifth byte.

.. image:: bayer_bytes.*
    :align: center

* Bayer data is organized in a BGGR pattern (a minor variation of the common
  `Bayer CFA`_). The raw data therefore has twice as many green pixels as red
  or blue and if viewed "raw" will look distinctly strange (too dark, too
  green, and with zippering effects along any straight edges).

.. image:: bayer_pattern.*
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
captures::

    from __future__ import (
        unicode_literals,
        absolute_import,
        print_function,
        division,
        )


    import io
    import time
    import picamera
    import numpy as np
    from numpy.lib.stride_tricks import as_strided

    stream = io.BytesIO()
    with picamera.PiCamera() as camera:
        # Let the camera warm up for a couple of seconds
        time.sleep(2)
        # Capture the image, including the Bayer data
        camera.capture(stream, format='jpeg', bayer=True)

    # Extract the raw Bayer data from the end of the stream, check the
    # header and strip if off before converting the data into a numpy array

    data = stream.getvalue()[-6404096:]
    assert data[:4] == 'BRCM'
    data = data[32768:]
    data = np.fromstring(data, dtype=np.uint8)

    # The data consists of 1952 rows of 3264 bytes of data. The last 8 rows
    # of data are unused (they only exist because the actual resolution of
    # 1944 rows is rounded up to the nearest 16). Likewise, the last 24
    # bytes of each row are unused (why?). Here we reshape the data and
    # strip off the unused bytes

    data = data.reshape((1952, 3264))[:1944, :3240]

    # Horizontally, each row consists of 2592 10-bit values. Every four
    # bytes are the high 8-bits of four values, and the 5th byte contains
    # the packed low 2-bits of the preceding four values. In other words,
    # the bits of the values A, B, C, D and arranged like so:
    #
    #  byte 1   byte 2   byte 3   byte 4   byte 5
    # AAAAAAAA BBBBBBBB CCCCCCCC DDDDDDDD AABBCCDD
    #
    # Here, we convert our data into a 16-bit array, shift all values left
    # by 2-bits and unpack the low-order bits from every 5th byte in each
    # row, then remove the columns containing the packed bits

    data = data.astype(np.uint16) << 2
    for byte in range(4):
        data[:, byte::5] |= ((data[:, 4::5] >> ((4 - byte) * 2)) & 0b11)
    data = np.delete(data, np.s_[4::5], 1)

    # Now to split the data up into its red, green, and blue components. The
    # Bayer pattern of the OV5647 sensor is BGGR. In other words the first
    # row contains alternating green/blue elements, the second row contains
    # alternating red/green elements, and so on as illustrated below:
    #
    # GBGBGBGBGBGBGB
    # RGRGRGRGRGRGRG
    # GBGBGBGBGBGBGB
    # RGRGRGRGRGRGRG
    #
    # Please note that if you use vflip or hflip to change the orientation
    # of the capture, you must flip the Bayer pattern accordingly

    rgb = np.zeros(data.shape + (3,), dtype=data.dtype)
    rgb[1::2, 0::2, 0] = data[1::2, 0::2] # Red
    rgb[0::2, 0::2, 1] = data[0::2, 0::2] # Green
    rgb[1::2, 1::2, 1] = data[1::2, 1::2] # Green
    rgb[0::2, 1::2, 2] = data[0::2, 1::2] # Blue

    # At this point we now have the raw Bayer data with the correct values
    # and colors but the data still requires de-mosaicing and
    # post-processing. If you wish to do this yourself, end the script here!
    #
    # Below we present a fairly naive de-mosaic method that simply
    # calculates the weighted average of a pixel based on the pixels
    # surrounding it. The weighting is provided by a byte representation of
    # the Bayer filter which we construct first:

    bayer = np.zeros(rgb.shape, dtype=np.uint8)
    bayer[1::2, 0::2, 0] = 1 # Red
    bayer[0::2, 0::2, 1] = 1 # Green
    bayer[1::2, 1::2, 1] = 1 # Green
    bayer[0::2, 1::2, 2] = 1 # Blue

    # Allocate an array to hold our output with the same shape as the input
    # data. After this we define the size of window that will be used to
    # calculate each weighted average (3x3). Then we pad out the rgb and
    # bayer arrays, adding blank pixels at their edges to compensate for the
    # size of the window when calculating averages for edge pixels.

    output = np.empty(rgb.shape, dtype=rgb.dtype)
    window = (3, 3)
    borders = (window[0] - 1, window[1] - 1)
    border = (borders[0] // 2, borders[1] // 2)

    rgb_pad = np.zeros((
        rgb.shape[0] + borders[0],
        rgb.shape[1] + borders[1],
        rgb.shape[2]), dtype=rgb.dtype)
    rgb_pad[
        border[0]:rgb_pad.shape[0] - border[0],
        border[1]:rgb_pad.shape[1] - border[1],
        :] = rgb
    rgb = rgb_pad

    bayer_pad = np.zeros((
        bayer.shape[0] + borders[0],
        bayer.shape[1] + borders[1],
        bayer.shape[2]), dtype=bayer.dtype)
    bayer_pad[
        border[0]:bayer_pad.shape[0] - border[0],
        border[1]:bayer_pad.shape[1] - border[1],
        :] = bayer
    bayer = bayer_pad

    # In numpy >=1.7.0 just use np.pad (version in Raspbian is 1.6.2 at the
    # time of writing...)
    #
    #rgb = np.pad(rgb, [
    #    (border[0], border[0]),
    #    (border[1], border[1]),
    #    (0, 0),
    #    ], 'constant')
    #bayer = np.pad(bayer, [
    #    (border[0], border[0]),
    #    (border[1], border[1]),
    #    (0, 0),
    #    ], 'constant')

    # For each plane in the RGB data, we use a nifty numpy trick
    # (as_strided) to construct a view over the plane of 3x3 matrices. We do
    # the same for the bayer array, then use Einstein summation on each
    # (np.sum is simpler, but copies the data so it's slower), and divide
    # the results to get our weighted average:

    for plane in range(3):
        p = rgb[..., plane]
        b = bayer[..., plane]
        pview = as_strided(p, shape=(
            p.shape[0] - borders[0],
            p.shape[1] - borders[1]) + window, strides=p.strides * 2)
        bview = as_strided(b, shape=(
            b.shape[0] - borders[0],
            b.shape[1] - borders[1]) + window, strides=b.strides * 2)
        psum = np.einsum('ijkl->ij', pview)
        bsum = np.einsum('ijkl->ij', bview)
        output[..., plane] = psum // bsum

    # At this point output should contain a reasonably "normal" looking
    # image, although it still won't look as good as the camera's normal
    # output (as it lacks vignette compensation, AWB, etc).
    #
    # If you want to view this in most packages (like GIMP) you'll need to
    # convert it to 8-bit RGB data. The simplest way to do this is by
    # right-shifting everything by 2-bits (yes, this makes all that
    # unpacking work at the start rather redundant...)

    output = (output >> 2).astype(np.uint8)
    with open('image.data', 'wb') as f:
        output.tofile(f)

This recipe is also encapsulated in the :class:`~PiBayerArray` class in the
:mod:`picamera.array` module, which means the same can be achieved as follows::

    import time
    import picamera
    import picamera.array
    import numpy as np

    with picamera.PiCamera() as camera:
        with picamera.array.PiBayerArray(camera) as stream:
            camera.capture(stream, 'jpeg', bayer=True)
            # Demosaic data and write to output (just use stream.array if you
            # want to skip the demosaic step)
            output = (stream.demosaic() >> 2).astype(np.uint8)
            with open('image.data', 'wb') as f:
                output.tofile(f)

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
device tree source::

    $ sudo apt-get install device-tree-compiler
    $ wget http://www.raspberrypi.org/documentation/configuration/images/dt-blob.dts

The device tree source contains a number of sections enclosed in curly braces,
which form a hierarchy of definitions. The section to edit will depend on which
revision of Raspberry Pi you have:

+---------------------------------+---------------------------+
| Model                           | Section                   |
+=================================+===========================+
| Raspberry Pi Model B revision 1 | ``/videocore/pins_rev1``  |
+---------------------------------+---------------------------+
| Raspberry Pi Model A            | ``/videocore/pins_rev2``  |
|                                 |                           |
| Raspberry Pi Model B revision 2 |                           |
+---------------------------------+---------------------------+
| Raspberry Pi Model A+           | ``/videocore/pins_bplus`` |
|                                 |                           |
| Raspberry Pi Model B+           |                           |
|                                 |                           |
| Raspberry Pi 2 Model B          |                           |
+---------------------------------+---------------------------+

Under the section for your particular model of Pi you will find ``pin_config``
and ``pin_defines`` sections. Under the ``pin_config`` section you need to
configure the GPIO pins you want to use for the flash and privacy indicator as
using pull down termination. Then, under the ``pin_defines`` section you need
to associate those pins with the ``FLASH_0_ENABLE`` and ``FLASH_0_INDICATOR``
pins.

For example, to configure GPIO 17 as the flash pin, leaving the privacy
indicator pin absent, on a Raspberry Pi Model B revision 2 you would add the
following line under the ``/videocore/pins_rev2/pin_config`` section::

    pin@p17 { function = "output"; termination = "pull_down"; };

Please note that GPIO pins will be numbered according to the `Broadcom pin
numbers`_ (BCM mode in the RPi.GPIO library, *not* BOARD mode). Then change the
following section under ``/videocore/pins_rev2/pin_defines``. Specifically,
change the type from "absent" to "internal", and add a number property defining
the flash pin as GPIO 17::

    pin-define@FLASH_0_ENABLE {
        type = "internal";
        number = <17>;
    };

With the device tree source updated, you now need to compile it into a binary
blob for the firmware to read. This is done with the following command line::

    $ dtc -I dts -O dtb dt-blob.dts -o dt-blob.bin

Dissecting this command line, the following components are present:

* ``dtc`` - Execute the device tree compiler

* ``-I dts`` - The input file is in device tree source format

* ``-O dtb`` - The output file should be produced in device tree binary format

* ``dt-blob.dts`` - The first anonymous parameter is the input filename

* ``-o dt-blob.bin`` - The output filename

This should output the following::

    DTC: dts->dtb  on file "dt-blob.dts"

If anything else is output, it will most likely be an error message indicating
you have made a mistake in the device tree source. In this case, review your
edits carefully (note that sections and properties *must* be semi-colon
terminated for example), and try again.

Now the device tree binary blob has been produced, it needs to be placed on the
first partition of the SD card. In the case of non-NOOBS Raspbian installs,
this is generally the partition mounted as ``/boot``::

    $ sudo cp dt-blob.bin /boot/

However, in the case of NOOBS Raspbian installs, this is the recovery
partition, which is not mounted by default::

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
case of ``pins_bplus``). For example, change::

    pin_define@CAMERA_0_LED {
        type = "internal";
        number = <5>;
    };
    pin_define@FLASH_0_ENABLE {
        type = "absent";
    };

into this::

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

On the fly video frame rate adjustment
======================================

Frame synchronization, phase locking, gen locking... can only be
approximated with the raspberry pi camera module.  However, by making
small adjustments to the video frame rate, it is possible to phase
lock the presentation time of each video frame to some reference, such
as the system clock.  Raspberry pi system clocks can then be
synchronized with eachother through NTP or chrony.  This recipe shows
how to make the micro adjustments to the frame rate while the camera
is capturing, which is a precursor to being able to gen lock multiple
cameras.

.. literalinclude:: video_frame_rate.py
   :language: python

Some output::

   index: 587 current rate: 22.945 commanded rate: 22.9923569380.3f measured rate: 22.862
   index: 588 current rate: 22.992 commanded rate: 23.038248880.3f measured rate: 22.898
   index: 589 current rate: 23.035 commanded rate: 23.08433699560.3f measured rate: 22.948
   index: 590 current rate: 23.082 commanded rate: 23.13061667580.3f measured rate: 22.996
   index: 591 current rate: 23.129 commanded rate: 23.17708329290.3f measured rate: 23.046
   index: 592 current rate: 23.176 commanded rate: 23.22373220010.3f measured rate: 23.083
   index: 593 current rate: 23.223 commanded rate: 23.27055873250.3f measured rate: 23.133
   index: 594 current rate: 23.270 commanded rate: 23.31755820770.3f measured rate: 23.181

.. _YUV: http://en.wikipedia.org/wiki/YUV
.. _YUV420: http://en.wikipedia.org/wiki/YUV#Y.27UV420p_.28and_Y.27V12_or_YV12.29_to_RGB888_conversion
.. _RGB: http://en.wikipedia.org/wiki/RGB
.. _RGBA: http://en.wikipedia.org/wiki/RGBA_color_space
.. _numpy: http://www.numpy.org/
.. _ring buffer: http://en.wikipedia.org/wiki/Circular_buffer
.. _OV5647: http://www.ovt.com/products/sensor.php?id=66
.. _Bayer CFA: http://en.wikipedia.org/wiki/Bayer_filter
.. _de-mosaicing: http://en.wikipedia.org/wiki/Demosaicing
.. _color balance: http://en.wikipedia.org/wiki/Color_balance
.. _macro-block: http://en.wikipedia.org/wiki/Macroblock
.. _magnitude of the vector: http://en.wikipedia.org/wiki/Magnitude_%28mathematics%29#Euclidean_vectors
.. _Sum of Absolute Differences: http://en.wikipedia.org/wiki/Sum_of_absolute_differences
.. _rolling shutter: http://en.wikipedia.org/wiki/Rolling_shutter
.. _VideoCore device tree blob: http://www.raspberrypi.org/documentation/configuration/pin-configuration.md
.. _flash metering: http://en.wikipedia.org/wiki/Through-the-lens_metering#Through_the_lens_flash_metering
.. _Broadcom pin numbers: http://raspberrypi.stackexchange.com/questions/12966/what-is-the-difference-between-board-and-bcm-for-gpio-pin-numbering
.. _OpenCV: http://opencv.org/
