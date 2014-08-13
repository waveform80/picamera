.. _recipes1:

=============
Basic Recipes
=============

The following recipes should be reasonably accessible to Python programmers of
all skill levels. Please feel free to suggest enhancements or additional
recipes.


.. _file_capture:

Capturing to a file
===================

Capturing an image to a file is as simple as specifying the name of the file as
the output of whatever :meth:`~picamera.PiCamera.capture` method you require::

    import time
    import picamera

    with picamera.PiCamera() as camera:
        camera.resolution = (1024, 768)
        camera.start_preview()
        # Camera warm-up time
        time.sleep(2)
        camera.capture('foo.jpg')

Note that files opened by picamera (as in the case above) will be flushed and
closed so that when the capture method returns, the data should be accessible
to other processes.


.. _stream_capture:

Capturing to a stream
=====================

Capturing an image to a file-like object (a :func:`~socket.socket`, a
:class:`io.BytesIO` stream, an existing open file object, etc.) is as simple as
specifying that object as the output of whatever
:meth:`~picamera.PiCamera.capture` method you're using::

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

Note that the format is explicitly specified in the case above. The
:class:`~io.BytesIO` object has no filename, so the camera can't automatically
figure out what format to use.

One thing to bear in mind is that (unlike specifying a filename), the stream is
*not* automatically closed after capture; picamera assumes that since it didn't
open the stream it can't presume to close it either. However, if the object has
a ``flush`` method, this will be called prior to capture returning. This should
ensure that once capture returns the data is accessible to other processes
although the object still needs to be closed::

    import time
    import picamera

    # Explicitly open a new file called my_image.jpg
    my_file = open('my_image.jpg', 'wb')
    with picamera.PiCamera() as camera:
        camera.start_preview()
        time.sleep(2)
        camera.capture(my_file)
    # At this point my_file.flush() has been called, but the file has
    # not yet been closed
    my_file.close()

Note that in the case above, we didn't have to specify the format as the camera
interrogated the ``my_file`` object for its filename (specifically, it looks
for a ``name`` attribute on the provided object). As well as using stream
classes built into Python (like :class:`~io.BytesIO`) you can also construct
your own :ref:`custom outputs <custom_outputs>`.


.. _pil_capture:

Capturing to a PIL Image
========================

This is a variation on :ref:`stream_capture`. First we'll capture an image to a
:class:`~io.BytesIO` stream (Python's in-memory stream class), then we'll
rewind the position of the stream to the start, and read the stream into a
`PIL`_ Image object::

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
image to a :class:`~io.BytesIO` stream (Python's in-memory stream class), then
convert the stream to a numpy array and read the array with `OpenCV`_::

    import io
    import time
    import picamera
    import cv2
    import numpy as np

    # Create the in-memory stream
    stream = io.BytesIO()
    with picamera.PiCamera() as camera:
        camera.start_preview()
        time.sleep(2)
        camera.capture(stream, format='jpeg')
    # Construct a numpy array from the stream
    data = np.fromstring(stream.getvalue(), dtype=np.uint8)
    # "Decode" the image from the array, preserving colour
    image = cv2.imdecode(data, 1)
    # OpenCV returns an array with data in BGR order. If you want RGB instead
    # use the following...
    image = image[:, :, ::-1]

If you want to avoid the JPEG encoding and decoding (which is lossy) and
potentially speed up the process, you can now use the classes in the
:mod:`picamera.array` module. As OpenCV images are simply numpy arrays arranged
in BGR order, one can use the :class:`~picamera.array.PiRGBArray` class and
simply capture with the ``'bgr'`` format (given that RGB and BGR data is the
same size and configuration, just with reversed color planes)::

    import time
    import picamera
    import picamera.array
    import cv2

    with picamera.PiCamera() as camera:
        camera.start_preview()
        time.sleep(2)
        with picamera.array.PiRGBArray(camera) as stream:
            camera.capture(stream, format='bgr')
            # At this point the image is available as stream.array
            image = stream.array


.. _resize_capture:

Capturing resized images
========================

Sometimes, particularly in scripts which will perform some sort of analysis or
processing on images, you may wish to capture smaller images than the current
resolution of the camera. Although such resizing can be performed using
libraries like PIL or OpenCV, it is considerably more efficient to have the
Pi's GPU perform the resizing when capturing the image. This can be done with
the *resize* parameter of the :meth:`~picamera.PiCamera.capture` methods::

    import time
    import picamera

    with picamera.PiCamera() as camera:
        camera.resolution = (1024, 768)
        camera.start_preview()
        # Camera warm-up time
        time.sleep(2)
        camera.capture('foo.jpg', resize=(320, 240))

The *resize* parameter can also be specified when recording video with the
:meth:`~picamera.PiCamera.start_recording` method.


.. _consistent_capture:

Capturing consistent images
===========================

You may wish to capture a sequence of images all of which look the same in
terms of brightness, color, and contrast (this can be useful in timelapse
photography, for example). Various attributes need to be used in order to
ensure consistency across multiple shots. Specifically, you need to ensure that
the camera's exposure time, white balance, and gains are all fixed:

* To fix exposure time, set the :attr:`~picamera.PiCamera.shutter_speed`
  attribute to a reasonable value, then set
  :attr:`~picamera.PiCamera.exposure_mode` to ``'off'``.
* To fix gains, set the :attr:`~picamera.PiCamera.ISO` attribute to an
  appropriate value (higher values imply higher gains).
* To fix white balance, set the :attr:`~picamera.PiCamera.awb_mode` to
  ``'off'``, then set :attr:`~picamera.PiCamera.awb_gains` to a (red, blue)
  tuple of gains.

It can be difficult to know what appropriate values might be for these
attributes.  For :attr:`~picamera.PiCamera.ISO`, a simple rule of thumb is that
100 and 200 are reasonable values for daytime, while 400 and 800 are better for
low light. To determine a reasonable value for
:attr:`~picamera.PiCamera.shutter_speed` you can query the
:attr:`~picamera.PiCamera.exposure_speed` attribute when
:attr:`~picamera.PiCamera.exposure_mode` is set to something other than
``'off'``. This will tell you the camera's exposure speed as determined by the
auto-exposure algorithm. FInally, to determine reasonable values for
:attr:`~picamera.PiCamera.awb_gains` simply query the property while
:attr:`~picamera.PiCamera.awb_mode` is set to something other than ``'off'``.
Again, this will tell you the camera's white balance gains as determined by the
auto-white-balance algorithm.

The following script provides a brief example of configuring these settings::

    import time
    import picamera

    with picamera.PiCamera() as camera:
        camera.resolution = (1280, 720)
        camera.framerate = 30
        # Give the camera's auto-exposure and auto-white-balance algorithms
        # some time to measure the scene and determine appropriate values
        camera.ISO = 200
        time.sleep(2)
        # Now fix the values
        camera.shutter_speed = camera.exposure_speed
        camera.exposure_mode = 'off'
        g = camera.awb_gains
        camera.awb_mode = 'off'
        camera.awb_gains = g
        # Finally, take several photos with the fixed settings
        camera.capture_sequence(['image%02d.jpg' % i for i in range(10)])


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
        delay = (next_hour - datetime.now()).seconds
        time.sleep(delay)

    with picamera.PiCamera() as camera:
        camera.start_preview()
        wait()
        for filename in camera.capture_continuous('img{timestamp:%Y-%m-%d-%H-%M}.jpg'):
            print('Captured %s' % filename)
            wait()


.. _dark_capture:

Capturing in low light
======================

Using similar tricks to those in :ref:`consistent_capture`, the Pi's camera can
capture images in low light conditions. The primary objective is to set a high
gain, and a long exposure time to allow the camera to gather as much light as
possible However, the :attr:`~picamera.PiCamera.shutter_speed` attribute is
constrained by the camera's :attr:`~picamera.PiCamera.framerate` so the first
thing we need to do is set a very slow framerate. The following script captures
an image with a 6 second exposure time (the maximum the Pi's camera module is
currently capable of)::

    import picamera
    from time import sleep
    from fractions import Fraction

    with picamera.PiCamera() as camera:
        camera.resolution = (1280, 720)
        # Set a framerate of 1/6fps, then set shutter
        # speed to 6s and ISO to 800
        camera.framerate = Fraction(1, 6)
        camera.shutter_speed = 6000000
        camera.exposure_mode = 'off'
        camera.ISO = 800
        # Give the camera a good long time to measure AWB
        # (you may wish to use fixed AWB instead)
        sleep(10)
        # Finally, capture an image with a 6s exposure. Due
        # to mode switching on the still port, this will take
        # longer than 6 seconds
        camera.capture('dark.jpg')

In anything other than dark conditions, the image produced by this script will
most likely be completely white or at least heavily over-exposed.

.. note::

    The Pi's camera module uses a `rolling shutter`_. This means that moving
    subjects may appear distorted if they move relative to the camera. This
    effect will be exaggerated by using longer exposure times.


.. _streaming_capture:

Capturing to a network stream
=============================

This is a variation of :ref:`timelapse_capture`. Here we have two scripts: a
server (presumably on a fast machine) which listens for a connection from the
Raspberry Pi, and a client which runs on the Raspberry Pi and sends a continual
stream of images to the server. We'll use a very simple protocol for
communication: first the length of the image will be sent as a 32-bit integer
(in `Little Endian`_ format), then this will be followed by the bytes of image
data. If the length is 0, this indicates that the connection should be closed
as no more images will be forthcoming. This protocol is illustrated below:

.. image:: image_protocol.*
    :align: center

Firstly the server script (which relies on PIL for reading JPEGs, but you could
replace this with any other suitable graphics library, e.g. OpenCV or
GraphicsMagick)::

    import io
    import socket
    import struct
    from PIL import Image

    # Start a socket listening for connections on 0.0.0.0:8000 (0.0.0.0 means
    # all interfaces)
    server_socket = socket.socket()
    server_socket.bind(('0.0.0.0', 8000))
    server_socket.listen(0)

    # Accept a single connection and make a file-like object out of it
    connection = server_socket.accept()[0].makefile('rb')
    try:
        while True:
            # Read the length of the image as a 32-bit unsigned int. If the
            # length is zero, quit the loop
            image_len = struct.unpack('<L', connection.read(struct.calcsize('<L')))[0]
            if not image_len:
                break
            # Construct a stream to hold the image data and read the image
            # data from the connection
            image_stream = io.BytesIO()
            image_stream.write(connection.read(image_len))
            # Rewind the stream, open it as an image with PIL and do some
            # processing on it
            image_stream.seek(0)
            image = Image.open(image_stream)
            print('Image is %dx%d' % image.size)
            image.verify()
            print('Image is verified')
    finally:
        connection.close()
        server_socket.close()

Now for the client side of things, on the Raspberry Pi::

    import io
    import socket
    import struct
    import time
    import picamera

    # Connect a client socket to my_server:8000 (change my_server to the
    # hostname of your server)
    client_socket = socket.socket()
    client_socket.connect(('my_server', 8000))

    # Make a file-like object out of the connection
    connection = client_socket.makefile('wb')
    try:
        with picamera.PiCamera() as camera:
            camera.resolution = (640, 480)
            # Start a preview and let the camera warm up for 2 seconds
            camera.start_preview()
            time.sleep(2)

            # Note the start time and construct a stream to hold image data
            # temporarily (we could write it directly to connection but in this
            # case we want to find out the size of each capture first to keep
            # our protocol simple)
            start = time.time()
            stream = io.BytesIO()
            for foo in camera.capture_continuous(stream, 'jpeg'):
                # Write the length of the capture to the stream and flush to
                # ensure it actually gets sent
                connection.write(struct.pack('<L', stream.tell()))
                connection.flush()
                # Rewind the stream and send the image data over the wire
                stream.seek(0)
                connection.write(stream.read())
                # If we've been capturing for more than 30 seconds, quit
                if time.time() - start > 30:
                    break
                # Reset the stream for the next capture
                stream.seek(0)
                stream.truncate()
        # Write a length of zero to the stream to signal we're done
        connection.write(struct.pack('<L', 0))
    finally:
        connection.close()
        client_socket.close()

The server script should be run first to ensure there's a listening socket
ready to accept a connection from the client script.


.. _file_record:

Recording video to a file
=========================

Recording a video to a file is simple::

    import picamera

    with picamera.PiCamera() as camera:
        camera.resolution = (640, 480)
        camera.start_recording('my_video.h264')
        camera.wait_recording(60)
        camera.stop_recording()

Note that we use :meth:`~picamera.PiCamera.wait_recording` in the example above
instead of :func:`time.sleep` which we've been using in the image capture
recipes above. The :meth:`~picamera.PiCamera.wait_recording` method is similar
in that it will pause for the number of seconds specified, but unlike
:func:`time.sleep` it will continually check for recording errors (e.g. an out
of disk space condition) while it is waiting. If we had used :func:`time.sleep`
instead, such errors would only be raised by the
:meth:`~picamera.PiCamera.stop_recording` call (which could be long after the
error actually occurred).


.. _stream_record:

Recording video to a stream
===========================

This is very similar to :ref:`file_record`::

    import io
    import picamera

    stream = io.BytesIO()
    with picamera.PiCamera() as camera:
        camera.resolution = (640, 480)
        camera.start_recording(stream, format='h264', quality=23)
        camera.wait_recording(15)
        camera.stop_recording()

Here, we've set the *quality* parameter to indicate to the encoder the level
of image quality that we'd like it to try and maintain. The camera's H.264
encoder is primarily constrained by two parameters:

* *bitrate* limits the encoder's output to a certain number of bits per second.
  The default is 17000000 (17Mbps), and the maximum value is 25000000 (25Mbps).
  Higher values give the encoder more "freedom" to encode at higher qualities.
  You will likely find that the default doesn't constrain the encoder at all
  except at higher recording resolutions.

* *quality* tells the encoder what level of image quality to maintain. Values
  can be between 1 (highest quality) and 40 (lowest quality), with typical
  values providing a reasonable trade-off between bandwidth and quality being
  between 20 and 25.

As well as using stream classes built into Python (like :class:`~io.BytesIO`)
you can also construct your own :ref:`custom outputs <custom_outputs>`. This is
particularly useful for video recording, as discussed in the linked recipe.


.. _split_record:

Recording over multiple files
=============================

If you wish split your recording over multiple files, you can use the
:meth:`~picamera.PiCamera.split_recording` method to accomplish this::

    import picamera

    with picamera.PiCamera() as camera:
        camera.resolution = (640, 480)
        camera.start_recording('1.h264')
        camera.wait_recording(5)
        for i in range(2, 11):
            camera.split_recording('%d.h264' % i)
            camera.wait_recording(5)
        camera.stop_recording()

This should produce 10 video files named ``1.h264``, ``2.h264``, etc. each of
which is approximately 5 seconds long (approximately because the
:meth:`~picamera.PiCamera.split_recording` method will only split files at a
key-frame).

The :meth:`~picamera.PiCamera.record_sequence` method can also be used to
achieve this with slightly cleaner code::

    import picamera

    with picamera.PiCamera() as camera:
        camera.resolution = (640, 480)
        for filename in camera.record_sequence(
                '%d.h264' % i for i in range(1, 11)):
            camera.wait_recording(5)

.. versionchanged:: 1.3
    The :meth:`~picamera.PiCamera.record_sequence` method was introduced in
    version 1.3


.. _circular_record1:

Recording to a circular stream
==============================

This is similar to :ref:`stream_record` but uses a special kind of in-memory
stream provided by the picamera library. The
:class:`~picamera.PiCameraCircularIO` class implements a `ring buffer`_ based
stream, specifically for video recording.  This enables you to keep an
in-memory stream containing the last *n* seconds of video recorded (where *n*
is determined by the bitrate of the video recording and the size of the ring
buffer underlying the stream).

A typical use-case for this sort of storage is security applications where one
wishes to detect motion and only record to disk the video where motion was
detected. This example keeps 20 seconds of video in memory until the
``write_now`` function returns ``True`` (in this implementation, this is random
but one could, for example, replace this with some sort of motion detection
algorithm). Once ``write_now`` returns ``True``, the script waits 10 more
seconds (so that the buffer contains 10 seconds of video from before the event,
and 10 seconds after) and writes the resulting video to disk before going back
to waiting::

    import io
    import random
    import picamera

    def write_now():
        # Randomly return True (like a fake motion detection routine)
        return random.randint(0, 10) == 0

    def write_video(stream):
        print('Writing video!')
        with stream.lock:
            # Find the first header frame in the video
            for frame in stream.frames:
                if frame.header:
                    stream.seek(frame.position)
                    break
            # Write the rest of the stream to disk
            with io.open('motion.h264', 'wb') as output:
                output.write(stream.read())

    with picamera.PiCamera() as camera:
        stream = picamera.PiCameraCircularIO(camera, seconds=20)
        camera.start_recording(stream, format='h264')
        try:
            while True:
                camera.wait_recording(1)
                if write_now():
                    # Keep recording for 10 seconds and only then write the
                    # stream to disk
                    camera.wait_recording(10)
                    write_video(stream)
        finally:
            camera.stop_recording()

In the above script we use the threading lock in the
:attr:`~picamera.CircularIO.lock` attribute to prevent the camera's background
writing thread from changing the stream while our own thread reads from it (as
the stream is a circular buffer, a write can remove information that is about
to be read). If we had stopped recording to the stream while writing we could
eliminate the ``with stream.lock`` line in the ``write_video`` function.

.. note::

    Note that *at least* 20 seconds of video are in the stream. This is an
    estimate only; if the H.264 encoder requires less than the specified
    bitrate (17Mbps by default) for recording the video, then more than 20
    seconds of video will be available in the stream.

.. versionadded:: 1.0


.. _streaming_record:

Recording to a network stream
=============================

This is similar to :ref:`stream_record` but instead of an in-memory stream like
:class:`~io.BytesIO`, we will use a file-like object created from a
:func:`~socket.socket`. Unlike the example in :ref:`streaming_capture` we don't
need to complicate our network protocol by writing things like the length of
images. This time we're sending a continual stream of video frames (which
necessarily incorporates such information, albeit in a much more efficient
form), so we can simply dump the recording straight to the network socket.

Firstly, the server side script which will simply read the video stream and
pipe it to a media player for display::

    import socket
    import subprocess

    # Start a socket listening for connections on 0.0.0.0:8000 (0.0.0.0 means
    # all interfaces)
    server_socket = socket.socket()
    server_socket.bind(('0.0.0.0', 8000))
    server_socket.listen(0)

    # Accept a single connection and make a file-like object out of it
    connection = server_socket.accept()[0].makefile('rb')
    try:
        # Run a viewer with an appropriate command line. Uncomment the mplayer
        # version if you would prefer to use mplayer instead of VLC
        cmdline = ['vlc', '--demux', 'h264', '-']
        #cmdline = ['mplayer', '-fps', '25', '-cache', '1024', '-']
        player = subprocess.Popen(cmdline, stdin=subprocess.PIPE)
        while True:
            # Repeatedly read 1k of data from the connection and write it to
            # the media player's stdin
            data = connection.read(1024)
            if not data:
                break
            player.stdin.write(data)
    finally:
        connection.close()
        server_socket.close()
        player.terminate()

.. note::

    If you run this script on Windows you will probably need to provide a
    complete path to the VLC or mplayer executable. If you run this script
    on Mac OS X, and are using Python installed from MacPorts, please ensure
    you have also installed VLC or mplayer from MacPorts.

You will probably notice several seconds of latency with this setup. This is
normal and is because media players buffer several seconds to guard against
unreliable network streams. Some media players (notably mplayer in this case)
permit the user to skip to the end of the buffer (press the right cursor key in
mplayer), reducing the latency by increasing the risk that delayed / dropped
network packets will interrupt the playback.

Now for the client side script which simply starts a recording over a file-like
object created from the network socket::

    import socket
    import time
    import picamera

    # Connect a client socket to my_server:8000 (change my_server to the
    # hostname of your server)
    client_socket = socket.socket()
    client_socket.connect(('my_server', 8000))

    # Make a file-like object out of the connection
    connection = client_socket.makefile('wb')
    try:
        with picamera.PiCamera() as camera:
            camera.resolution = (640, 480)
            camera.framerate = 24
            # Start a preview and let the camera warm up for 2 seconds
            camera.start_preview()
            time.sleep(2)
            # Start recording, sending the output to the connection for 60
            # seconds, then stop
            camera.start_recording(connection, format='h264')
            camera.wait_recording(60)
            camera.stop_recording()
    finally:
        connection.close()
        client_socket.close()

It should also be noted that the effect of the above is much more easily
achieved (at least on Linux) with a combination of ``netcat`` and the
``raspivid`` executable. For example::

    server-side: nc -l 8000 | vlc --demux h264 -
    client-side: raspivid -w 640 -h 480 -t 60000 -o - | nc my_server 8000

However, this recipe does serve as a starting point for video streaming
applications. It's also possible to reverse the direction of this recipe
relatively easily. In this scenario, the Pi acts as the server, waiting for a
connection from the client. When it accepts a connection, it starts streaming
video over it for 60 seconds. Another variation (just for the purposes of
demonstration) is that we initialize the camera straight away instead of
waiting for a connection to allow the streaming to start faster on connection::

    import socket
    import time
    import picamera

    with picamera.PiCamera() as camera:
        camera.resolution = (640, 480)
        camera.framerate = 24

        server_socket = socket.socket()
        server_socket.bind(('0.0.0.0', 8000))
        server_socket.listen(0)

        # Accept a single connection and make a file-like object out of it
        connection = server_socket.accept()[0].makefile('wb')
        try:
            camera.start_recording(connection, format='h264')
            camera.wait_recording(60)
            camera.stop_recording()
        finally:
            connection.close()
            server_socket.close()

One advantage of this setup is that no script is needed on the client side - we
can simply use VLC with a network URL::

    vlc tcp/h264://my_pi_address:8000/

.. note::

    VLC (or mplayer) will *not* work for playback on a Pi. Neither is
    (currently) capable of using the GPU for decoding, and thus they attempt to
    perform video decoding on the Pi's CPU (which is not powerful enough for
    the task). You will need to run these applications on a faster machine
    (though "faster" is a relative term here: even an Atom powered netbook
    should be quick enough for the task at non-HD resolutions).


.. _text_overlay:

Overlaying text on the output
=============================

The camera includes a rudimentary annotation facility which permits up to 31
characters of ASCII text to be overlayed on all output (including the preview,
image captures and video recordings). To achieve this, simply assign a string
to the :attr:`~picamera.PiCamera.annotate_text` attribute::

    import picamera
    import time

    with picamera.PiCamera() as camera:
        camera.resolution = (640, 480)
        camera.framerate = 24
        camera.start_preview()
        camera.annotate_text = 'Hello world!'
        time.sleep(2)
        # Take a picture including the annotation
        camera.capture('foo.jpg')

With a little ingenuity, it's possible to display longer strings::

    import picamera
    import time
    import itertools

    s = "This message would be far too long to display normally..."

    with picamera.PiCamera() as camera:
        camera.resolution = (640, 480)
        camera.framerate = 24
        camera.start_preview()
        camera.annotate_text = ' ' * 31
        for c in itertools.cycle(s):
            camera.annotate_text = camera.annotate_text[1:31] + c
            time.sleep(0.1)

And of course, it can be used to display (and embed) a timestamp in
recordings::

    import picamera
    import datetime as dt

    with picamera.PiCamera() as camera:
        camera.resolution = (1280, 720)
        camera.framerate = 24
        camera.start_preview()
        camera.annotate_text = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        camera.start_recording('timestamped.h264')
        start = dt.datetime.now()
        while (dt.datetime.now() - start).seconds < 30:
            camera.annotate_text = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            camera.wait_recording(0.2)
        camera.stop_recording()


.. _led_control:

Controlling the LED
===================

In certain circumstances, you may find the camera module's red LED a hindrance.
For example, in the case of automated close-up wild-life photography, the LED
may scare off animals. It can also cause unwanted reflected red glare with
close-up subjects.

One trivial way to deal with this is simply to place some opaque covering on
the LED (e.g. blue-tack or electricians tape). Another method is to use the
``disable_camera_led`` option in the `boot configuration`_.

However, provided you have the `RPi.GPIO`_ package installed, and provided your
Python process is running with sufficient privileges (typically this means
running as root with ``sudo python``), you can also control the LED via the
:attr:`~picamera.PiCamera.led` attribute::

    import picamera

    with picamera.PiCamera() as camera:
        # Turn the camera's LED off
        camera.led = False
        # Take a picture while the LED remains off
        camera.capture('foo.jpg')

.. warning::

    Be aware when you first use the LED property it will set the GPIO library
    to Broadcom (BCM) mode with ``GPIO.setmode(GPIO.BCM)`` and disable warnings
    with ``GPIO.setwarnings(False)``. The LED cannot be controlled when the
    library is in BOARD mode.


.. _PIL: http://effbot.org/imagingbook/pil-index.htm
.. _OpenCV: http://opencv.org/
.. _RPi.GPIO: https://pypi.python.org/pypi/RPi.GPIO
.. _ring buffer: http://en.wikipedia.org/wiki/Circular_buffer
.. _boot configuration: http://www.raspberrypi.org/documentation/configuration/config-txt.md
.. _Little Endian: http://en.wikipedia.org/wiki/Endianness
.. _rolling shutter: http://en.wikipedia.org/wiki/Rolling_shutter

