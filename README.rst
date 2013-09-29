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

Packages can be downloaded from the project `homepage`_. The `source code`_ can
be obtained from GitHub. The `documentation`_ (including installation
instructions and a quick start tutorial) can be read on ReadTheDocs.

To do
=====

Major things that still need work:

* Image encoding selection (PNG, BMP, GIF, etc.)

* Image thumbnail settings

* JPEG quality configuration

* EXIF tags

* Preview alpha configuration

* Preview display-rect configuration

* Tests

* Future work - text overlay on preview (GLES?)

.. _Raspberry Pi: http://www.raspberrypi.org/
.. _camera: http://www.raspberrypi.org/camera
.. _homepage: https://pypi.python.org/pypi/picamera/
.. _documentation: http://picamera.readthedocs.org/
.. _source code: https://github.com/waveform80/picamera.git
.. _Python: http://python.org/
.. _BSD license: http://opensource.org/licenses/BSD-3-Clause
.. _Pull requests: https://github.com/waveform80/picamera.git
