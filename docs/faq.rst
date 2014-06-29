.. _faq:

================================
Frequently Asked Questions (FAQ)
================================

Can I put the preview in a window?
==================================

No. The camera module's preview system is quite crude: it simply tells the GPU
to overlay the preview on the Pi's video output. The preview has no knowledge
(or interaction with) the X-Windows environment (incidentally, this is why the
preview works quite happily from the command line, even without anyone logged
in).

That said, the preview area can be resized and repositioned via the
:attr:`~picamera.PiCamera.preview_window` attribute. If your program can
respond to window repositioning and sizing events you can "cheat" and position
the preview within the borders of the target window. However, there's currently
no way to allow anything to appear on top of the preview so this is an
imperfect solution at best.

Help! I started a preview and can't see my console!
===================================================

As mentioned above, the preview is simply an overlay over the Pi's video
output.  If you start a preview you may therefore discover you can't see your
console anymore and there's no obvious way of getting it back. If you're
confident in your typing skills you can try calling
:meth:`~picamera.PiCamera.stop_preview` by typing "blindly" into your hidden
console. However, the simplest way of getting your display back is usually
to hit ``Ctrl+D`` to terminate the Python process (which should also shut down
the camera).

Before starting a preview, you may want to set
:attr:`~picamera.PiCamera.preview_alpha` to something like 128. This should
ensure that when the preview is display it is partially transparent so you can
still see your console.

How much power does the camera require?
=======================================

The camera `requires 250mA`_ when running. Note that simply creating a
:class:`~picamera.PiCamera` object means the camera is running (due to the
hidden preview that is started to allow the auto-exposure algorithm to run). If
you are running your Pi from batteries, you should
:meth:`~picamera.PiCamera.close` (or destroy) the instance when the camera is
not required in order to conserve power. For example, the following code
captures 60 images over an hour, but leaves the camera running all the time::

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
convenient :meth:`~picamera.PiCamera.capture_continuous` method as a result)::

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

"Out of memory" when initializing the camera
============================================

If you see something like this when trying to create an instance of
:class:`~picamera.PiCamera`::

    >>> import picamera
    >>> camera = picamera.PiCamera()
    mmal: mmal_vc_component_create: failed to create component 'vc.ril.camera' (1:ENOMEM)
    mmal: mmal_component_create_core: could not create component 'vc.ril.camera' (1)
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
      File "/usr/lib/python2.7/dist-packages/picamera/camera.py", line 257, in __init__
        self._init_camera()
      File "/usr/lib/python2.7/dist-packages/picamera/camera.py", line 288, in _init_camera
        prefix="Failed to create camera component")
      File "/usr/lib/python2.7/dist-packages/picamera/exc.py", line 112, in mmal_check
        raise PiCameraMMALError(status, prefix)
    picamera.exc.PiCameraMMALError: Failed to create camera component: Out of memory

This usually means that you haven't enabled the Pi's camera module. Run ``sudo
raspi-config``, select the "Enable Camera" option, select "Enable", and then
"Finish". You will need to reboot to complete the process.

.. note::

    Enabling the camera doesn't affect the camera itself. Rather, it tells the
    operating system to load the firmware for the camera on the next boot.  If
    you re-install your operating system for whatever reason (or switch SD
    cards for another operating system) you will need to re-enable the camera
    in this way.

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

