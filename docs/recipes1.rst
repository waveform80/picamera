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
the output of whatever capture() method you require::

    import time
    import picamera

    with picamera.PiCamera() as camera:
        camera.resolution = (1024, 768)
        camera.start_preview()
        # Camera warm-up time
        time.sleep(2)
        camera.capture('foo.jpg')

Note that files opened by picamera (as in the case above) will be flushed and
closed so that when the capture() method returns, the data should be accessible
to other processes.


.. _stream_capture:

Capturing to a stream
=====================

Capturing an image to a file-like object (a :func:`~socket.socket`, a
:class:`io.BytesIO` stream, an existing open file object, etc.) is as simple as
specifying that object as the output of whatever capture() method you're
using::

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
open the stream it can't presume to close it either. In the case of file
objects this can mean that the data doesn't actually get written to the disk
until the object is explicitly closed::

    import time
    import picamera

    # Explicitly open a new file called my_image.jpg
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


.. _streaming_capture:

Capturing to a network stream
=============================

This is a variation of :ref:`timelapse_capture`. Here we have two scripts: a
server (presumably on a fast machine) which listens for a connection from the
Raspberry Pi, and a client which runs on the Raspberry Pi and sends a continual
stream of images to the server. Firstly the server script (which relies on PIL
for reading JPEGs, but you could replace this with any other suitable graphics
library, e.g. OpenCV or GraphicsMagick)::

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
            image_len = struct.unpack('<L', connection.read(4))[0]
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
:attr:`~picamera.PiCamera.resolution` to 2592x1944::

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


.. _file_record:

Recording video to a file
=========================

Recording a video to a file is simple, provided you remember that the only
format (currently) supported is a raw H264 stream::

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
        camera.start_recording(stream, quantization=23)
        camera.wait_recording(15)
        camera.stop_recording()

Here, we've set the *quantization* parameter which will cause the video encoder
to use VBR (variable bit-rate) encoding. This can be considerably more
efficient especially in mostly static scenes (which can be important when
recording to memory, as in the example above). Quantization values can be
between 0 and 40, where 0 represents the highest possible quality, and 40 the
lowest.  Typically, a value in the range of 20-25 provides reasonable quality
for reasonable bandwidth.


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
keyframe).

.. versionadded:: 0.8


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
pipe it to VLC for display::

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
        # Run VLC with the appropriately selected demuxer (as we're not giving
        # it a filename which would allow it to guess correctly)
        vlc = subprocess.Popen(
            ['vlc', '--demux', 'h264', '-'],
            stdin=subprocess.PIPE)
        while True:
            # Repeatedly read 1k of data from the connection and write it to
            # VLC's stdin
            data = connection.read(1024)
            if not data:
                break
            vlc.stdin.write(data)
    finally:
        connection.close()
        server_socket.close()
        vlc.terminate()

.. note::
    If you run this script on Windows you will probably need to provide a
    complete path to the VLC executable.

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

You will probably notice several seconds of latency with this setup. This is
normal and is because VLC buffers several seconds to guard against unreliable
network streams. Low latency video streaming requires rather more effort (the
`x264dev blog`_ provides some insight into the complexity involved)!

It should also be noted that the effect of the above is much more easily
achived (at least on Linux) with a combination of ``netcat`` and the
``raspivid`` executable. For example::

    server-side: nc -l 8000 | vlc --demux h264 -
    client-side: raspivid -w 640 -h 480 -t 60000 -o - | nc my_server 8000

However, this recipe does serve as a starting point for video streaming
applications. For example, it shouldn't be terribly difficult to extend the
recipe above to permit the server to control some aspects of the client's video
stream.


.. _PIL: http://effbot.org/imagingbook/pil-index.htm
.. _OpenCV: http://opencv.org/
.. _x264dev blog: http://x264dev.multimedia.cx/archives/249
