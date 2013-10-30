.. _recipes:

=======
Recipes
=======


.. _stream_capture:

Capturing to a stream
=====================

Capturing to a file-like object (a socket, a :class:`io.BytesIO` stream, an
existing open file object, etc.) is as simple as specifying that object as the
output of whatever capture() method you're using::

    import io
    import time
    import picamera

    # Create an in-memory stream
    my_stream = io.BytesIO()
    with picamera.PiCamera() as camera:
        camera.start_preview()
        # Camera warm-up time
        time.sleep(2)
        camera.capture(my_stream, 'jpeg')

Note that the format is explicitly specified in the case above. The BytesIO
object has no filename, so the camera can't automatically figure out what
format to use.

One thing to bear in mind is that (unlike specifying a filename), the stream is
*not* automatically closed after capture; picamera assumes that since it didn't
open the stream it can't presume to close it either. In the case of file
objects this can mean that the data doesn't actually get written to the disk
until the object is explicitly closed::

    import time
    import picamera

    # Create a new file called my_image.jpg
    my_file = open('my_image.jpg', 'wb')
    with picamera.PiCamera() as camera:
        camera.start_preview()
        time.sleep(2)
        camera.capture(my_file)
    # Note that at this point the data is in the file cache, but may
    # not actually have been written to disk yet
    my_file.close()
    # Now the file has been closed, other processes should be able to
    # read the image successfully

Note that in the case above, we didn't have to specify the format as the camera
interrogated the ``my_file`` object for its filename (specifically, it looks
for a ``name`` attribute on the provided object).


.. _pil_capture:

Capturing to a PIL Image
========================

This is a variation on :ref:`stream_capture`. First we'll capture an image to
a BytesIO stream (Python's in-memory stream class), then we'll rewind the
position of the stream to the start, and read the stream into a `PIL`_ Image
object::

    import io
    import time
    import picamera
    from PIL import Image

    # Create the in-memory stream
    stream = io.BytesIO()
    with picamera.PiCamera() as camera:
        camera.start_preview()
        time.sleep(2)
        camera.capture(stream, format='jpeg')
    # "Rewind" the stream to the beginning so we can read its content
    stream.seek(0)
    image = Image.open(stream)


.. _opencv_capture:

Capturing to an OpenCV object
=============================

This is another variation on :ref:`stream_capture`. First we'll capture an
image to a BytesIO stream (Python's in-memory stream class), then rewind the
position of the stream to the start, and read the stream with `OpenCV`_::

    import io
    import time
    import picamera
    import cv2

    # Create the in-memory stream
    stream = io.BytesIO()
    with picamera.PiCamera() as camera:
        camera.start_preview()
        time.sleep(2)
        camera.capture(stream, format='jpeg')
    # "Rewind" the stream to the beginning so we can read its content
    stream.seek(0)
    image = cv2.imread(stream)


.. _timelapse_capture:

Capturing timelapse sequences
=============================

The simplest way to capture long time-lapse sequences is with the
:meth:`~picamera.PiCamera.capture_continuous` method. With this method, the
camera captures images continually until you tell it to stop. Images are
automatically given unique names and you can easily control the delay between
captures. The following example shows how to capture images with a 5 minute
delay between each shot::

    import time
    import picamera

    with picamera.PiCamera() as camera:
        camera.start_preview()
        time.sleep(2)
        for filename in camera.capture_continuous('img{counter:03d}.jpg'):
            print('Captured %s' % filename)
            time.sleep(300) # wait 5 minutes

However, you may wish to capture images at a particular time, say at the start
of every hour. This simply requires a refinement of the delay in the loop (the
:mod:`datetime` module is slightly easier to use for calculating dates and
times; this example also demonstrates the ``timestamp`` template in the
captured filenames)::

    import time
    import picamera
    from datetime import datetime, timedelta

    def wait():
        # Calculate the delay to the start of the next hour
        next_hour = (datetime.now() + timedelta(hour=1)).replace(
            minute=0, second=0, microsecond=0)
        delay = (datetime.now() - next_hour).seconds
        time.sleep(delay)

    with picamera.PiCamera() as camera:
        camera.start_preview()
        wait()
        for filename in camera.capture_continuous('img{timestamp:%Y-%m-%d-%H-%M}.jpg'):
            print('Captured %s' % filename)
            wait()


.. _preview_still_resolution:

Preview vs Still resolution
===========================

One thing you may have noted while experimenting with the camera's preview mode
is that captured images typically show more than the preview. The reason for
this is that the camera does not (usually) use the full sensor area for preview
or video captures, but does for image captures. Specifically, the camera's
sensor has a resolution of 2592x1944 pixels (approximately 5 mega-pixels in
area), but only the 1920x1080 pixels in the center of the sensor are used for
previews or video:

.. image:: sensor_area.png
    :width: 640px
    :align: center

When still images are captured, the full sensor area is used and the resulting
image is scaled to the requested resolution. This usually results in a
considerably larger field of view being observed in the final image than was
present in the preview shown before the capture. The following image shows the
preview area for the 1920x1080 resolution, and the resulting capture area
(which is scaled to 1920x1080 during capture):

.. image:: capture_area.png
    :width: 640px
    :align: center

The main method of mitigating this effect is to force the preview to use the
full sensor area. This can be done by setting
:attr:`~picamera.PiCamera.resolution` to 2592x1944 (this must be done before
starting the preview as resolution can only be set when the camera is idle)::

    import time
    import picamera

    with picamera.PiCamera() as camera:
        camera.resolution = (2592, 1944)
        # The following is equivalent
        #camera.resolution = camera.MAX_IMAGE_RESOLUTION
        camera.start_preview()
        time.sleep(2)
        camera.capture('foo.jpg')

When the preview runs at full resolution, you may notice that the framerate is
a little lower (specifically it is set to 15fps), however captures will show
the same content as the preview before hand. The main downside to this method
is that captured images are obviously full resolution. If you want something
smaller than full resolution, post scaling and/or cropping (e.g. in `PIL`_) is
required.


.. _video_port_capture:

.. _yuv_capture:

Raw image capture (YUV format)
==============================

If you want images captured without loss of detail (due to JPEG's lossy
compression), you are probably better off exploring PNG as an alternate image
format (PNG uses lossless compression). However, some applications
(particularly scientific ones) simply require the raw sensor data in numeric
form. For this, the ``raw`` format is provided::

    import time
    import picamera

    with picamera.PiCamera() as camera:
        camera.resolution = (100, 100)
        camera.start_preview()
        time.sleep(2)
        camera.capture('image.data', 'raw')

By default raw output is in `YUV`_ format, specifically YUV420 (planar). This
means that the Y (luminance) values occur first in the resulting data and have
full resolution (one 1-byte Y value for each pixel in the image). The Y values
are followed by the U (chrominance) values, and finally the V (chrominance)
values.  The UV values have one quarter the resolution of the Y components (4
1-byte Y values in a square for each 1-byte U and 1-byte V value).

It is also important to note that when outputting to raw format, the camera
rounds the requested resolution. The horizontal resolution is rounded up to the
nearest multiple of 32, while the vertical resolution is rounded up to the
nearest multiple of 16. For example, if the requested resolution is 100x100,
a raw capture will actually contain 128x112 pixels worth of data, but pixels
beyond 100x100 will be uninitialized.

Given that the YUV420 format contains 1.5 bytes worth of data for each pixel
(a 1-byte Y value for each pixel, and 1-byte U and V values for every 4 pixels),
and taking into account the resolution rounding, the size of a 100x100 raw
capture will be:

.. math::

           & 128   \quad \text{100 rounded up to nearest multiple of 32} \\
    \times & 112   \quad \text{100 rounded up to nearest multiple of 16} \\
    \times & 1.5   \quad \text{bytes of data per pixel in YUV420 format} \\
    =      & 21504 \quad \text{bytes}

The first 14336 bytes of the data (128*112) will be Y values, the next 3584
bytes (128*112/4) will be U values, and the final 3584 bytes will be the V
values.

The following code demonstrates capturing an image in raw YUV format, loading
the data into a set of `numpy`_ arrays, and converting the data to RGB format
in an efficient manner::

    from __future__ import division

    import io
    import time
    import picamera
    import numpy as np

    width = 100
    height = 100
    stream = io.BytesIO()
    # Capture the image in raw YUV format
    with picamera.PiCamera() as camera:
        camera.resolution = (width, height)
        camera.raw_format = 'yuv'
        camera.start_preview()
        time.sleep(2)
        camera.capture(stream, 'raw')
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

Alternatively, see :ref:`rgb_capture` for a method of having the camera output
RGB data directly.

.. _rgb_capture:

Raw image capture (RGB format)
==============================

The RGB format is rather larger than the `YUV`_ format discussed in the section
above, but is more useful for most analyses. To have the camera produce raw
output in `RGB`_ format, you simply need to adjust the
:attr:`~picamera.PiCamera.raw_format` attribute prior to capturing the image::

    import time
    import picamera

    with picamera.PiCamera() as camera:
        camera.resolution = (100, 100)
        camera.raw_format = 'rgb'
        camera.start_preview()
        time.sleep(2)
        camera.capture('image.data', 'raw')

Note that this attribute can only be adjusted while the camera is idle (hence
why the above code does so before starting the preview). Also note that
capturing to "ordinary" formats (JPEG, PNG, etc.) and video recording will
*not* work when :attr:`~picamera.PiCamera.raw_format` is set to ``rgb``. This
is because the encoders used for these formats all expect YUV input.

The size of raw RGB data can be calculated similarly to YUV captures. Firstly
round the resolution appropriately (see :ref:`yuv_capture` for the specifics),
then multiply the number of pixels by 3 (1 byte of red, 1 byte of green, and
1 byte of blue intensity). Hence, for a 100x100 capture, the amount of data
produced is:

.. math::

           & 128   \quad \text{100 rounded up to nearest multiple of 32} \\
    \times & 112   \quad \text{100 rounded up to nearest multiple of 16} \\
    \times & 3     \quad \text{bytes of data per pixel in RGB888 format} \\
    =      & 43008 \quad \text{bytes}

The resulting RGB data is interleaved. That is to say that the red, green and
blue values for a given pixel are grouped together, in that order. The first
byte of the data is the red value for the pixel at (0, 0), the second byte is
the green value for the same pixel, and the third byte is the blue value for
that pixel. The fourth byte is the red value for the pixel at (1, 0), and so
on.

Loading the resulting RGB data into a `numpy`_ array is simple::

    from __future__ import division

    width = 100
    height = 100
    stream = io.BytesIO()
    # Capture the image in raw YUV format
    with picamera.PiCamera() as camera:
        camera.resolution = (width, height)
        camera.raw_format = 'yuv'
        camera.start_preview()
        time.sleep(2)
        camera.capture(stream, 'raw')
    # Rewind the stream for reading
    stream.seek(0)
    # Calculate the actual image size in the stream (accounting for rounding
    # of the resolution)
    fwidth = (width + 31) // 32 * 32
    fheight = (height + 15) // 16 * 16
    # Load the data in a three-dimensional array and crop it to the requested
    # resolution
    image = np.fromfile(stream, dtype=uint8).\
            reshape((fheight, fwidth, 3))[:height, :width, :]
    # If you wish, the following code will convert the image's bytes into
    # floating point values in the range 0 to 1 (a typical format for some
    # sorts of analysis)
    image = image.astype(np.float, copy=False)
    image = image / 255.0


Rapid capture and processing
============================

The camera is capable of capturing a sequence of images extremely rapidly by
utilizing its video-capture capabilities with a JPEG encoder (via the
``use_video_port`` parameter). However, there are several things to note about
using this technique:

* When using video-port based capture only the preview area is captured; in
  some cases this may be desirable (see the discussion under
  :ref:`preview_still_resolution`).

* No Exif information is embedded in JPEG images captured through the
  video-port.

* Captures typically appear "granier" with this technique. The author is not
  aware of the exact technical reasons why this is so, but suspects that some
  part of the image processing pipeline that is present for still captures is
  not used when performing still captures through the video-port.

All capture methods support the ``use_video_port`` option, but the methods
differ in their ability to rapidly capture sequential frames. So, whilst
:meth:`~picamera.PiCamera.capture` and
:meth:`~picamera.PiCamera.capture_continuous` both support ``use_video_port``,
:meth:`~picamera.PiCamera.capture_sequence` is by far the fastest method. Using
this method, the author has managed 30fps JPEG captures at a resolution of
1024x768.

However, :meth:`~picamera.PiCamera.capture_sequence` is particular suited to
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
:meth:`~picamera.PiCamera.capture_sequence` method::

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

The major issue with capturing this rapidly is that the Raspberry Pi's IO
bandwidth is extremely limited. As a format, JPEG is considerably less
efficient than the H.264 video format (which is to say that, for the same
number of bytes, H.264 will provide considerably better quality over the same
number of frames).

At higher resolutions (beyond 800x600) you are likely to find you cannot
sustain 30fps captures to the Pi's SD card for very long (before exhausting the
disk cache).  In other words, if you are intending to perform processing on the
frames after capture, you may be better off just capturing video and decoding
frames from the resulting file rather than dealing with individual JPEG
captures.

However, if you can perform your processing fast enough, you may not need to
involve the disk at all.  Using a generator function, we can maintain a queue
of objects to store the captures, and have parallel threads accept and process
the streams as captures come in. Provided the processing runs at a faster frame
rate than the captures, the encoder won't stall and nothing ever need hit the
disk::

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
                processor = pool.pop()
            yield processor.stream
            processor.event.set()

    with picamera.PiCamera() as camera:
        pool = [ImageProcessor() for i in range (4)]
        camera.resolution = (640, 480)
        # Set the framerate appropriately; too fast and the image processors
        # will stall the image pipeline and crash the script
        camera.framerate = 10
        camera.start_preview()
        time.sleep(2)
        camera.capture_sequence(streams(), use_video_port=True)

    # Shut down the processors in an orderly fashion
    while pool:
        with lock:
            processor = pool.pop()
        processor.terminated = True
        processor.join()


.. _PIL: http://effbot.org/imagingbook/pil-index.htm
.. _OpenCV: http://opencv.org/
.. _YUV: http://en.wikipedia.org/wiki/YUV
.. _RGB: http://en.wikipedia.org/wiki/RGB
.. _numpy: http://www.numpy.org/
