.. _root:

==========================
Documentation for picamera
==========================

This package provides a pure Python interface to the `Raspberry Pi`_ `camera`_
module.

The project is written to be compatible with `Python`_ 2.7 from the 2.x series
(it will not work with 2.6 or below), and Python 3.2 or above from the 3.x
series. The same codebase supports both Python 2 and 3 with no conversions
(e.g. ``2to3``) required.

The code is licensed under the `BSD license`_. Packages can be downloaded from
the project `homepage`_ on PyPI. The `source code`_ can be obtained from
GitHub, which also hosts the `bug tracker`_. The `documentation`_ (which
includes installation, quick-start examples, and the change-log) can be read on
ReadTheDocs.


To do
=====

Major things that still need work:

* Preview alpha configuration

* Preview display-rect configuration

* Tests

* Future work - text overlay on preview (GLES?)


Table of Contents
=================

.. toctree::
   :maxdepth: 1
   :numbered:

   install
   quickstart
   api
   changelog
   license


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


.. _Raspberry Pi: http://www.raspberrypi.org/
.. _camera: http://www.raspberrypi.org/camera
.. _homepage: http://pypi.python.org/pypi/picamera/
.. _documentation: http://picamera.readthedocs.org/
.. _source code: https://github.com/waveform80/picamera
.. _bug tracker: https://github.com/waveform80/picamera/issues
.. _Python: http://python.org/
.. _BSD license: http://opensource.org/licenses/BSD-3-Clause
.. _Pull requests: https://github.com/waveform80/picamera.git
