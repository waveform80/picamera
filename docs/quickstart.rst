.. _quickstart:

===========
Quick Start
===========

Start a preview for 10 seconds with the default settings::

    import time
    import picamera

    camera = picamera.PiCamera()
    try:
        camera.start_preview()
        time.sleep(10)
        camera.stop_preview()
    finally:
        camera.close()

Note that you should always ensure you call ``close()`` on the PiCamera object
to clean up resources. The following example demonstrates that the context
manager protocol can be used to achieve this::

    import time
    import picamera

    with picamera.PiCamera() as camera:
        camera.start_preview()
        time.sleep(10)
        camera.stop_preview()

The following example shows that certain properties can be adjusted "live"
while a preview is running. In this case, the brightness is increased steadily
during display::

    import time
    import picamera

    with picamera.PiCamera() as camera:
        camera.start_preview()
        try:
            for i in range(100):
                camera.brightness = i
                time.sleep(0.2)
        finally:
            camera.stop_preview()

The next example demonstrates setting the camera resolution (this can only be
done when the camera is not recording or previewing) to 640x480, then starting
a preview and a recording to a disk file::

    import picamera

    with picamera.PiCamera() as camera:
        camera.resolution = (640, 480)
        camera.start_preview()
        camera.start_recording('foo.h264')
        camera.wait_recording(60)
        camera.stop_recording()
        camera.stop_preview()

Note that :meth:`PiCamera.wait_recording` is used above instead of
``time.sleep``. This method checks for errors (e.g. out of disk space) while
the recording is running and raises an exception if one occurs. If
``time.sleep`` was used instead the exception would be raised by
:meth:`PiCamera.stop_recording` but only after the full waiting time had run.

This example demonstrates starting a preview, setting some parameters
and then capturing an image while the preview is running::

    import time
    import picamera

    with picamera.PiCamera() as camera:
        camera.resolution = (1280, 720)
        camera.start_preview()
        camera.exposure_compensation = 2
        camera.exposure_mode = 'spotlight'
        camera.meter_mode = 'matrix'
        camera.image_effect = 'gpen'
        time.sleep(2)
        camera.capture('foo.jpg')
        camera.stop_preview()

