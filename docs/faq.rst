.. _faq:

================================
Frequently Asked Questions (FAQ)
================================

.. currentmodule:: picamera


AttributeError: 'module' object has no attribute 'PiCamera'
===========================================================

You've named your script ``picamera.py`` (or you've named some other script
``picamera.py``. If you name a script after a system or third-party package you
will break imports for that system or third-party package. Delete or rename
that script (and any associated ``.pyc`` files), and try again.

Can I put the preview in a window?
==================================

No. The camera module's preview system is quite crude: it simply tells the GPU
to overlay the preview on the Pi's video output. The preview has no knowledge
(or interaction with) the X-Windows environment (incidentally, this is why the
preview works quite happily from the command line, even without anyone logged
in).

That said, the preview area can be resized and repositioned via the
:attr:`~PiRenderer.window` attribute of the :attr:`~PiCamera.preview` object.
If your program can respond to window repositioning and sizing events you can
"cheat" and position the preview within the borders of the target window.
However, there's currently no way to allow anything to appear on top of the
preview so this is an imperfect solution at best.

Help! I started a preview and can't see my console!
===================================================

As mentioned above, the preview is simply an overlay over the Pi's video
output.  If you start a preview you may therefore discover you can't see your
console anymore and there's no obvious way of getting it back. If you're
confident in your typing skills you can try calling
:meth:`~PiCamera.stop_preview` by typing "blindly" into your hidden console.
However, the simplest way of getting your display back is usually to hit
``Ctrl+D`` to terminate the Python process (which should also shut down the
camera).

When starting a preview, you may want to set the *alpha* parameter of the
:meth:`~PiCamera.start_preview` method to something like 128.  This should
ensure that when the preview is displayed, it is partially transparent so you
can still see your console.

The preview doesn't work on my PiTFT screen
===========================================

The camera's preview system directly overlays the Pi's output on the HDMI or
composite video ports. At this time, it will not operate with GPIO-driven
displays like the PiTFT. Some projects, like the `Adafruit Touchscreen Camera
project`_, have approximated a preview by rapidly capturing unencoded images
and displaying them on the PiTFT instead.

.. _Adafruit Touchscreen Camera project: https://learn.adafruit.com/diy-wifi-raspberry-pi-touch-cam/overview

How much power does the camera require?
=======================================

The camera `requires 250mA`_ when running. Note that simply creating a
:class:`PiCamera` object means the camera is running (due to the hidden preview
that is started to allow the auto-exposure algorithm to run). If you are
running your Pi from batteries, you should :meth:`~PiCamera.close` (or destroy)
the instance when the camera is not required in order to conserve power. For
example, the following code captures 60 images over an hour, but leaves the
camera running all the time::

    import picamera
    import time

    with picamera.PiCamera() as camera:
        camera.resolution = (1280, 720)
        time.sleep(1) # Camera warm-up time
        for i, filename in enumerate(camera.capture_continuous('image{counter:02d}.jpg')):
            print('Captured %s' % filename)
            # Capture one image a minute
            time.sleep(60)
            if i == 59:
                break

By contrast, this code closes the camera between shots (but can't use the
convenient :meth:`~PiCamera.capture_continuous` method as a result)::

    import picamera
    import time

    for i in range(60):
        with picamera.PiCamera() as camera:
            camera.resolution = (1280, 720)
            time.sleep(1) # Camera warm-up time
            filename = 'image%02d.jpg' % i
            camera.capture(filename)
            print('Captured %s' % filename)
        # Capture one image a minute
        time.sleep(59)

.. note::

    Please note the timings in the scripts above are approximate. A more
    precise example of timing is given in :ref:`timelapse_capture`.

If you are experiencing lockups or reboots when the camera is active, your
power supply may be insufficient. A practical minimum is 1A for running a Pi
with an active camera module; more may be required if additional peripherals
are attached.

.. _requires 250mA: http://www.raspberrypi.org/help/faqs/#cameraPower

How can I take two consecutive pictures with equivalent settings?
=================================================================

See the :ref:`consistent_capture` recipe.

Can I use picamera with a USB webcam?
=====================================

No. The picamera library relies on libmmal which is specific to the Pi's camera
module.

How can I tell what version of picamera I have installed?
=========================================================

The picamera library relies on the setuptools package for installation
services.  You can use the setuptools ``pkg_resources`` API to query which
version of picamera is available in your Python environment like so::

    >>> from pkg_resources import require
    >>> require('picamera')
    [picamera 1.2 (/usr/local/lib/python2.7/dist-packages)]
    >>> require('picamera')[0].version
    '1.2'

If you have multiple versions installed (e.g. from ``pip`` and ``apt-get``)
they will not show up in the list returned by the ``require`` method. However,
the first entry in the list will be the version that ``import picamera`` will
import.

If you receive the error "No module named pkg_resources", you need to install
the ``pip`` utility. This can be done with the following command in Raspbian::

    $ sudo apt-get install python-pip

How come I can't upgrade to the latest version?
===============================================

If you are using Raspbian, firstly check that you haven't got both a PyPI
(``pip``) and an apt (``apt-get``) installation of picamera installed
simultaneously. If you have, one will be taking precedence and it may not be
the most up to date version.

Secondly, please understand that while the PyPI release process is entirely
automated (so as soon as a new picamera release is announced, it will be
available on PyPI), the release process for Raspbian packages is semi-manual.
There is typically a delay of a few days after a release before updated
picamera packages become accessible in the Raspbian repository.

Users desperate to try the latest version may choose to uninstall their ``apt``
based copy (uninstall instructions are provided in the :ref:`installation
instructions <raspbian_install>`, and install using :ref:`pip instead
<non_raspbian_install>`. However, be aware that keeping a PyPI based
installation up to date is a more manual process (sticking with ``apt`` ensures
everything gets upgraded with a simple ``sudo apt-get upgrade`` command).

Why is there so much latency when streaming video?
==================================================

The first thing to understand is that streaming latency has little to do with
the encoding or sending end of things (i.e. the Pi), and much more to do with
the playing or receiving end. If the Pi weren't capable of encoding a frame
before the next frame arrived, it wouldn't be capable of recording video at all
(because its internal buffers would rapidly become filled with unencoded
frames).

So, why do players typically introduce several seconds worth of latency? The
primary reason is that most players (e.g. VLC) are optimized for playing
streams over a network. Such players allocate a large (multi-second) buffer and
only start playing once this is filled to guard against possible future packet
loss.

A secondary reason that all such players allocate at least a couple of frames
worth of buffering is that the MPEG standard includes certain frame types that
require it:

* I-frames (intra-frames, also known as "key frames"). These frames contain a
  complete picture and thus are the largest sort of frames. They occur at the
  start of playback and at periodic points during the stream.
* P-frames (predicted frames). These frames describe the changes from the prior
  frame to the current frame, therefore one must have successfully decoded the
  prior frame in order to decode a P-frame.
* B-frames (bi-directional predicted frames). These frames describe the changes
  from the next frame to the current frame, therefore one must have
  successfully decoded the *next* frame in order to decode the current B-frame.

B-frames aren't produced by the Pi's camera (or, as I understand it, by most
real-time recording cameras) as it would require buffering yet-to-be-recorded
frames before encoding the current one. However, most recorded media (DVDs,
Blu-rays, and hence network video streams) do use them, so players must support
them. It is simplest to write such a player by assuming that any source may
contain B-frames, and buffering at least 2 frames worth of data at all times to
make decoding them simpler.

As for the network in between, a slow wifi network may introduce a frame's
worth of latency, but not much more than that. Check the ping time across your
network; it's likely to be less than 30ms in which case your network cannot
account for more than a frame's worth of latency.

TL;DR: the reason you've got lots of latency when streaming video is nothing to
do with the Pi. You need to persuade your video player to reduce or forgo its
buffering.

Why are there more than 20 seconds of video in the circular buffer?
===================================================================

Read the note at the bottom of the :ref:`circular_record1` recipe. When you set
the number of seconds for the circular stream you are setting a *lower bound*
for a given bitrate (which defaults to 17Mbps - the same as the video recording
default). If the recorded scene has low motion or complexity the stream can
store considerably more than the number of seconds specified.

If you need to copy a specific number of seconds from the stream, see the
*seconds* parameter of the :meth:`~PiCameraCircularIO.copy_to` method (which
was introduced in release 1.11).

Finally, if you specify a different bitrate limit for the stream and the
recording, the seconds limit will be inaccurate.

Can I move the annotation text?
===============================

No: the firmware provides no means of moving the annotation text. The only
configurable attributes of the annotation are currently color and font size.

Why is playback too fast/too slow in VLC/omxplayer/etc.?
========================================================

The camera's H264 encoder doesn't output a full MP4 file (which would contain
frames-per-second meta-data). Instead it outputs an H264 NAL stream which just
has frame-size and a few other details (but not FPS).

Most players (like VLC) default to 24, 25, or 30 fps. Hence, recordings at
12fps will appear "fast", while recordings as 60fps will appear "slow". Your
playback client needs to be told what fps to use when playing back (assuming it
supports such an option).

For those wondering why the camera doesn't output a full MP4 file, consider
that the Pi camera's heritage is mobile phone cameras. In these devices you
only want the camera to output the H264 stream so you can mux it with, say, an
AAC stream recorded from the microphone input and wrap the result into a full
MP4 file.

To convert the H264 NAL stream to a full MP4 file, there are a couple of
options. The simplest is to use the ``MP4Box`` utility from the ``gpac``
package on Raspbian. Unfortunately this only works with files; it cannot accept
redirected streams:

.. code-block:: console

    $ sudo apt-get install gpac
    ...
    $ MP4Box -add input.h264 output.mp4

Alternatively you can use the console version of VLC to handle the conversion.
This is a more complex command line, but a lot more powerful (it'll handle
redirected streams and can be used with a vast array of outputs including
HTTP, RTP, etc.):

.. code-block:: console

    $ sudo apt-get install vlc
    ...
    $ cvlc input.h264 --play-and-exit --sout \
    > '#standard{access=file,mux=mp4,dst=output.mp4}' :demux=h264 \

Or to read from stdin:

.. code-block:: console

    $ raspivid -t 5000 -o - | cvlc stream:///dev/stdin \
    > --play-and-exit --sout \
    > '#standard{access=file,mux=mp4,dst=output.mp4}' :demux=h264 \

Out of resources at full resolution on a V2 module
==================================================

See :ref:`hardware_limits`.

Preview flickers at full resolution on a V2 module
==================================================

Use the new :attr:`~PiPreviewRenderer.resolution` property to select a lower
resolution for the preview, or specify one when starting the preview. For
example::

    from picamera import PiCamera

    camera = PiCamera()
    camera.resolution = camera.MAX_RESOLUTION
    camera.start_preview(resolution=(1024, 768))

Camera locks up with multiprocessing
====================================

The camera firmware is designed to be used by a *single* process at a time.
Attempting to use the camera from multiple processes simultaneously will fail
in a variety of ways (from simple errors to the process locking up).

Python's :mod:`multiprocessing` module creates multiple copies of a Python
process (usually via :func:`os.fork`) for the purpose of parallel processing.
Whilst you can use :mod:`multiprocessing` with picamera, you must ensure that
only a *single* process creates a :class:`PiCamera` instance at any given time.

The following script demonstrates an approach with one process that owns the
camera, which handles disseminating captured frames to other processes via a
:class:`~multiprocessing.Queue`:

.. literalinclude:: examples/multiproc_camera.py

