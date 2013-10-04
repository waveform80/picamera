.. _install:

============
Installation
============

User installation
=================

This is by far the simplest form of installation (though it's also the most
complex to uninstall should you wish to do so later)::

    $ sudo apt-get install python-setuptools
    $ easy_install --user picamera

To upgrade your installation when new releases are made::

    $ easy_install --user -U picamera

If you ever need to remove your installation::

    $ rm -fr ~/.local/lib/python*/site-packages/picamera-*
    $ sed -i -e '/^\.\/picamera-/d' ~/.local/lib/python*/site-packages/easy-install.pth

.. note::
    If the removal looks horribly complex, that's because it is! This is the
    reason Python devs tend to prefer virtualenvs. However, I suspect it's
    unlikely that most users will actually care about removing picamera - it's
    a tiny package and has no dependencies so leaving it lying around shouldn't
    cause any issues even if you don't use it anymore.


Virtualenv installation
=======================

If you wish to install picamera within a virtualenv (useful if you're working
on several Python projects with potentially conflicting dependencies, or you
just like keeping things separate and easily removable)::

    $ sudo apt-get install python-setuptools python-virtualenv
    $ virtualenv sandbox
    $ source sandbox/bin/activate
    (sandbox) $ easy_install picamera

Bear in mind that each time you want to use picamera you will need to activate
the virtualenv before running Python::

    $ source sandbox/bin/activate
    (sandbox) $ python
    >>> import picamera

To upgrade your installation, make sure the virtualenv is activated and just
use easy_install::

    $ source sandbox/bin/activate
    (sandbox) $ easy_install -U picamera

To remove your installation simply blow away the virtualenv::

    $ rm -fr ~/sandbox/


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
    $ virtualenv sandbox
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

To remove your installation blow away the sandbox and the checkout::

    $ rm -fr ~/sandbox/ ~/picamera/

For anybody wishing to hack on the project please understand that although it
is technically written in pure Python, heavy use of :mod:`ctypes` is involved
so the code really doesn't look much like Python - more a sort of horrid
mish-mash of C and Python. The project currently consists of a class
(:class:`PiCamera`) which is a crude re-implementation of useful bits of the
``raspistill`` and ``raspivid`` commands using the :mod:`ctypes` based
``libmmal`` header conversion.

Even if you don't feel up to hacking on the code, I'd love to hear suggestions
from people of what you'd like the API to look like (even if the code itself
isn't particularly pythonic, the interface should be)!

