.. _install:

============
Installation
============

The picamera package can be obtained from `PyPI`_ but probably the simplest
method is to use the setuptools easy_install command (preferably from within a
virtual Python environment to avoid affecting the system Python installation)::

    $ sudo apt-get install python-virtualenv
    $ virtualenv sandbox
    $ source sandbox/bin/activate
    (sandbox) $ easy_install picamera


Development
===========

If you wish to development picamera itself, it is easiest to obtain the source
by cloning the GitHub repository and then use the "develop" target of the
Makefile which will install the package as a link to the cloned repository
allowing in-place development (it also builds a tags file for use with
vim/emacs with exuberant's ctags utility).  The following example demonstrates
this method within a virtual Python environment::

    $ sudo apt-get install build-essential git git-core exuberant-ctags \
        python-virtualenv
    $ virtualenv sandbox
    $ source sandbox/bin/activate
    (sandbox) $ git clone https://github.com/waveform80/picamera.git
    (sandbox) $ cd picamera
    (sandbox) $ make develop

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


.. _PyPI: https://pypi.python.org/pypi/picamera/

