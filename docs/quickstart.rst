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
        for i in range(100):
            camera.brightness = i
            time.sleep(0.2)
        camera.stop_preview()

