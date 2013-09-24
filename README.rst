.. -*- rst -*-

========
picamera
========

This package provides a pure Python interface to the `Raspberry Pi`_ `camera`_
module.

.. warning::
    This package is still in heavy development and many things do not yet work.
    `Pull requests`_ gratefully received!

The project is written to be compatible with `Python`_ 2.7 from the 2.x series
(it will not work with 2.6 or below), and Python 3.2 or above from the 3.x
series. The same codebase supports both Python 2 and 3 with no conversions
(e.g. ``2to3``) required.

The code is licensed under the `BSD license`_ as much of the code is a
translation of the libmmal headers which Broadcom have licensed under this same
license. I'm unsure of the legal obligations surrounding such header
conversions so for the sake of simplicity I've kept the license the same.

Packages can be downloaded from the project `homepage`_. The `source code`_
can be obtained from GitHub. The `documentation`_ can be read on ReadTheDocs.

Quick start
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

Development
===========

For anybody wishing to hack on the project please understand that although it
is technically written in pure Python, heavy use of ``ctypes`` is involved so
the code really doesn't look much like Python - more a sort of horrid mish-mash
of C and Python. The project currently consists of a class (PiCamera) which is
a crude re-implementation of useful bits of the ``raspistill`` and ``raspivid``
commands using the ``ctypes`` based ``libmmal`` header conversion.

Even if you don't feel up to hacking on the code, I'd love to hear suggestions
from people of what you'd like the API to look like (even if the code itself
isn't particularly pythonic, the interface should be)!

To do
=====

Major things that still need work:

* Video recording

* Image encoding selection (PNG, BMP, GIF, etc.)

* Image thumbnail settings

* JPEG quality configuration

* EXIF tags

* Preview alpha configuration

* Preview display-rect configuration

* Documentation, examples, tests, etc. etc.

.. _Raspberry Pi: http://www.raspberrypi.org/
.. _camera: http://www.raspberrypi.org/camera
.. _homepage: https://pypi.python.org/pypi/picamera/
.. _documentation: http://picamera.readthedocs.org/
.. _source code: https://github.com/waveform80/picamera.git
.. _Python: http://python.org/
.. _BSD license: http://opensource.org/licenses/BSD-3-Clause
.. _Pull requests: https://github.com/waveform80/picamera.git
