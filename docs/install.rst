.. _install:

============
Installation
============

.. currentmodule:: picamera


.. _raspbian_install:

Raspbian installation
=====================

If you are using the `Raspbian`_ distro, you probably have picamera installed
by default. You can find out simply by starting Python and trying to import
picamera:

.. code-block:: console

    $ python -c "import picamera"
    $ python3 -c "import picamera"

If you get no error, you've already got picamera installed! Just continue to
:ref:`quickstart`. If you don't have picamera installed you'll see something
like the following:

.. code-block:: console

    $ python -c "import picamera"
    Traceback (most recent call last):
      File "<string>", line 1, in <module>
    ImportError: No module named picamera
    $ python3 -c "import picamera"
    Traceback (most recent call last):
      File "<string>", line 1, in <module>
    ImportError: No module named 'picamera'

To install picamera on Raspbian, it is best to use the system's package
manager: apt. This will ensure that picamera is easy to keep up to date, and
easy to remove should you wish to do so. It will also make picamera available
for all users on the system. To install picamera using apt simply run:

.. code-block:: console

    $ sudo apt-get update
    $ sudo apt-get install python-picamera python3-picamera

To upgrade your installation when new releases are made you can simply use
apt's normal upgrade procedure:

.. code-block:: console

    $ sudo apt-get update
    $ sudo apt-get upgrade

If you ever need to remove your installation:

.. code-block:: console

    $ sudo apt-get remove python-picamera python3-picamera



.. _non_raspbian_install:

Alternate distro installation
=============================

On distributions other than Raspbian, it is probably simplest to install system
wide using Python's ``pip`` tool:

.. code-block:: console

    $ sudo pip install picamera

If you wish to use the classes in the :mod:`picamera.array` module then specify
the "array" option which will pull in numpy as a dependency:

.. code-block:: console

    $ sudo pip install "picamera[array]"

.. warning::

    Be warned that older versions of pip will attempt to build numpy from
    source. This will take a *very* long time on a Pi (several hours on slower
    models). Modern versions of pip will download and install a pre-built
    numpy "wheel" instead which is much faster.

To upgrade your installation when new releases are made:

.. code-block:: console

    $ sudo pip install -U picamera

If you ever need to remove your installation:

.. code-block:: console

    $ sudo pip uninstall picamera


.. _firmware:

Firmware upgrades
=================

The behaviour of the Pi's camera module is dictated by the Pi's firmware. Over
time, considerable work has gone into fixing bugs and extending the
functionality of the Pi's camera module through new firmware releases. Whilst
the picamera library attempts to maintain backward compatibility with older Pi
firmwares, it is only tested against the latest firmware at the time of
release, and not all functionality may be available if you are running an older
firmware. As an example, the :attr:`~PiCamera.annotate_text` attribute relies
on a recent firmware; older firmwares lacked the functionality.

You can determine the revision of your current firmware with the following
command:

.. code-block:: console

    $ uname -a

The firmware revision is the number after the ``#``:

.. code-block:: text

    Linux kermit 3.12.26+ #707 PREEMPT Sat Aug 30 17:39:19 BST 2014 armv6l GNU/Linux
                            /
                           /
      firmware revision --+

On Raspbian, the standard upgrade procedure should keep your firmware
up to date:

.. code-block:: console

    $ sudo apt-get update
    $ sudo apt-get upgrade

.. warning::

    Previously, these documents have suggested using the ``rpi-update`` utility
    to update the Pi's firmware; this is now discouraged. If you have
    previously used the ``rpi-update`` utility to update your firmware, you can
    switch back to using ``apt`` to manage it with the following commands::

        $ sudo apt-get update
        $ sudo apt-get install --reinstall libraspberrypi0 libraspberrypi-{bin,dev,doc} raspberrypi-bootloader
        $ sudo rm /boot/.firmware_revision

    You will need to reboot after doing so.

.. note::

    Please note that the `PiTFT`_ screen (and similar GPIO-driven screens)
    requires a custom firmware for operation. This firmware lags behind the
    official firmware and at the time of writing lacks several features
    including long exposures and text overlays.


.. _Raspbian: http://www.raspberrypi.org/downloads/raspbian/
.. _PiTFT: http://www.adafruit.com/product/1601
