.. _install3:

========================
Python 3.2+ Installation
========================

There are several ways to install picamera under Python 3.2 (or above), each
with their own advantages and disadvantages. Have a read of the sections below
and select an installation method which conforms to your needs.


.. _firmware3:

Firmware upgrades
=================

The behaviour of the Pi's camera module is dictated by the Pi's firmware. Over
time, considerable work has gone into fixing bugs and extending the
functionality of the Pi's camera module through new firmware releases. Whilst
the picamera library attempts to maintain backward compatibility with older Pi
firmwares, it is only tested against the latest firmware at the time of
release, and not all functionality may be available if you are running an older
firmware. As an example, the :attr:`~picamera.PiCamera.annotate_text` attribute
relies on a recent firmware; older firmwares lacked the functionality.

You can determine the revision of your current firmware with the following
command::

    $ uname -a

The firmware revision is the number after the ``#``::

    Linux kermit 3.12.26+ #707 PREEMPT Sat Aug 30 17:39:19 BST 2014 armv6l GNU/Linux
                            /
                           /
      firmware revision --+

On Raspbian, the standard upgrade procedure should keep your firmware
up to date::

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

.. _PiTFT: http://www.adafruit.com/product/1601


.. _raspbian_install3:

Raspbian installation
=====================

If you are using the `Raspbian`_ distro, it is best to install picamera using
the system's package manager: apt. This will ensure that picamera is easy to
keep up to date, and easy to remove should you wish to do so. It will also make
picamera available for all users on the system. To install picamera using apt
simply::

    $ sudo apt-get update
    $ sudo apt-get install python3-picamera

To upgrade your installation when new releases are made you can simply use
apt's normal upgrade procedure::

    $ sudo apt-get update
    $ sudo apt-get upgrade

If you ever need to remove your installation::

    $ sudo apt-get remove python3-picamera

.. note::

    If you are using a recent installation of Raspbian, you may find that the
    python3-picamera package is already installed (it is included by default
    in recent versions of `NOOBS`_).

.. note::

    The release of the picamera package on Raspbian lags behind the release of
    picamera packages on PyPI (see :ref:`system_install2` below) by a few days.
    If you find yourself unable to upgrade immediately following a release
    announcement, you can either switch to a PyPI installation or wait a few
    days for the Raspbian packages to arrive in the repository.

.. _Raspbian: http://www.raspbian.org/
.. _NOOBS: http://www.raspberrypi.org/downloads/


.. _user_install3:

User installation
=================

This is the simplest (non-apt) form of installation (though it's also complex
to uninstall should you wish to do so later), but bear in mind that it will
only work for the user you install under. For example, if you install as the
``pi`` user, you will only be able to use picamera as the ``pi`` user. If you
run python as root (e.g. with ``sudo python3``) it will not find the module.
See :ref:`system_install3` below if you require a root installation.

To install as your current user::

    $ sudo apt-get install python3-pip
    $ pip-3.2 install --user picamera

If you wish to use the classes in the :mod:`picamera.array` module then specify
the "array" option which will pull in numpy as a dependency (be warned that
building numpy takes a *long* time on a Pi)::

    $ pip-3.2 install --user "picamera[array]"

Note that ``pip-3.2`` is **not** run with ``sudo``; this is deliberate. To
upgrade your installation when new releases are made::

    $ pip-3.2 install --user -U picamera

If you ever need to remove your installation::

    $ pip-3.2 uninstall picamera


.. _system_install3:

System installation
===================

A system installation will make picamera accessible to all users (in contrast
to the user installation). It is as simple to perform as the user installation
and equally easy to keep updated. To perform the installation::

    $ sudo apt-get install python3-pip
    $ sudo pip-3.2 install picamera

If you wish to use the classes in the :mod:`picamera.array` module then specify
the "array" option which will pull in numpy as a dependency (be warned that
building numpy takes a *long* time on a Pi)::

    $ sudo pip-3.2 install "picamera[array]"

To upgrade your installation when new releases are made::

    $ sudo pip-3.2 install -U picamera

If you ever need to remove your installation::

    $ sudo pip-3.2 uninstall picamera


.. _virtualenv_install3:

Virtualenv installation
=======================

If you wish to install picamera within a virtualenv (useful if you're working
on several Python projects with potentially conflicting dependencies, or you
just like keeping things separate and easily removable)::

    $ sudo apt-get install python3-pip python-virtualenv
    $ virtualenv -p python3 sandbox
    $ source sandbox/bin/activate
    (sandbox) $ pip-3.2 install picamera

If you wish to use the classes in the :mod:`picamera.array` module then specify
the "array" option which will pull in numpy as a dependency (be warned that
building numpy takes a *long* time on a Pi)::

    (sandbox) $ pip-3.2 install "picamera[array]"

Bear in mind that each time you want to use picamera you will need to activate
the virtualenv before running Python::

    $ source sandbox/bin/activate
    (sandbox) $ python
    >>> import picamera

To upgrade your installation, make sure the virtualenv is activated and just
use easy_install::

    $ source sandbox/bin/activate
    (sandbox) $ pip-3.2 install -U picamera

To remove your installation simply blow away the virtualenv::

    $ rm -fr ~/sandbox/


.. _dev_install3:

Development installation
========================

If you wish to develop picamera itself, it is easiest to obtain the source by
cloning the GitHub repository and then use the "develop" target of the Makefile
which will install the package as a link to the cloned repository allowing
in-place development (it also builds a tags file for use with vim/emacs with
exuberant's ctags utility).  The following example demonstrates this method
within a virtual Python environment::

    $ sudo apt-get install build-essential git git-core exuberant-ctags \
        python-virtualenv
    $ virtualenv -p python3 sandbox
    $ source sandbox/bin/activate
    (sandbox) $ git clone https://github.com/waveform80/picamera.git
    (sandbox) $ cd picamera
    (sandbox) $ make develop

To pull the latest changes from git into your clone and update your
installation::

    $ source sandbox/bin/activate
    (sandbox) $ cd picamera
    (sandbox) $ git pull
    (sandbox) $ make develop

To remove your installation blow away the sandbox and the clone::

    $ rm -fr ~/sandbox/ ~/picamera/

For anybody wishing to hack on the project please understand that although it
is technically written in pure Python, heavy use of :mod:`ctypes` is involved
so the code really doesn't look much like Python - more a sort of horrid
mish-mash of C and Python.

The project consists primarily of a class (:class:`~picamera.camera.PiCamera`)
which is a re-implementation of high-level bits of the ``raspistill`` and
``raspivid`` commands using the :mod:`ctypes` based ``libmmal`` header
conversion, plus a set of :ref:`encoder classes <custom_encoders>` which
re-implement the encoder callback configuration in the aforementioned binaries.
Various classes for specialized applications also exist
(:class:`~picamera.streams.PiCameraCircularIO`,
:class:`~picamera.array.PiBayerArray`, etc.)

Even if you don't feel up to hacking on the code, I'd love to hear suggestions
from people of what you'd like the API to look like (even if the code itself
isn't particularly pythonic, the interface should be)!


.. _test_suite3:

Test suite
==========

If you wish to run the picamera test suite, follow the instructions in
:ref:`dev_install2` above and then install the following additional
dependencies (note: avconv is installed system-wide)::

    (sandbox) $ sudo apt-get install libav-tools
    (sandbox) $ pip install Pillow pytest mock numpy

Finally, to run the test suite, execute the following command::

    (sandbox) $ make test

.. warning::

    The test suite takes a *very* long time to execute (at least 4 hours on an
    overclocked Pi). Depending on configuration, it can also lockup the camera
    requiring a reboot to reset, so ensure you are familiar with SSH or using
    alternate TTYs to access a command line in the event you need to reboot.
