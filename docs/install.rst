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

For development purposes it is easiest to obtain the source by cloning the
GitHub repository and then use the "develop" target of the Makefile which will
install the package as a link to the cloned repository allowing in-place
development (it also builds a tags file for use with vim/emacs with exuberant's
ctags utility).  The following example demonstrates this method within a
virtual Python environment::

    $ sudo apt-get install build-essential git git-core exuberant-ctags \
        python-virtualenv
    $ virtualenv sandbox
    $ source sandbox/bin/activate
    (sandbox) $ git clone https://github.com/waveform80/picamera.git
    (sandbox) $ cd picamera
    (sandbox) $ make develop


.. _PyPI: https://pypi.python.org/pypi/picamera/

