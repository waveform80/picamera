.. _development:

===========
Development
===========

.. currentmodule:: picamera

The main GitHub repository for the project can be found at:

    https://github.com/waveform80/picamera

Anyone is more than welcome to open tickets to discuss bugs, new features, or
just to ask usage questions (I find this useful for gauging what questions
ought to feature in the FAQ, for example).

For anybody wishing to hack on the project, I would strongly recommend reading
through the :class:`PiCamera` class' source, to get a handle on using the
:mod:`~picamera.mmalobj` layer. This is a layer introduced in picamera 1.11 to
ease the usage of ``libmmal`` (the underlying library that picamera,
``raspistill``, and ``raspivid`` all rely upon).

Beneath :mod:`~picamera.mmalobj` is a :mod:`ctypes` translation of the
``libmmal`` headers but my hope is that most developers will never need to deal
with this directly (thus, a working knowledge of C is hopefully no longer
necessary to hack on picamera).

Various classes for specialized applications also exist
(:class:`PiCameraCircularIO`, :class:`~array.PiBayerArray`, etc.)

Even if you don’t feel up to hacking on the code, I’d love to hear suggestions
from people of what you’d like the API to look like (even if the code itself
isn’t particularly pythonic, the interface should be)!


.. _dev_install:

Development installation
========================

If you wish to develop picamera itself, it is easiest to obtain the source by
cloning the GitHub repository and then use the "develop" target of the Makefile
which will install the package as a link to the cloned repository allowing
in-place development (it also builds a tags file for use with vim/emacs with
Exuberant’s ctags utility). The following example demonstrates this method
within a virtual Python environment:

.. code-block:: console

    $ sudo apt-get install lsb-release build-essential git git-core \
    >   exuberant-ctags virtualenvwrapper python-virtualenv python3-virtualenv \
    >   python-dev python3-dev libjpeg8-dev zlib1g-dev libav-tools
    $ cd
    $ mkvirtualenv -p /usr/bin/python3 picamera
    $ workon picamera
    (picamera) $ git clone https://github.com/waveform80/picamera.git
    (picamera) $ cd picamera
    (picamera) $ make develop

To pull the latest changes from git into your clone and update your
installation:

.. code-block:: console

    $ workon picamera
    (picamera) $ cd ~/picamera
    (picamera) $ git pull
    (picamera) $ make develop

To remove your installation, destroy the sandbox and the clone:

.. code-block:: console

    (picamera) $ deactivate
    $ rmvirtualenv picamera
    $ rm -fr ~/picamera


Building the docs
=================

If you wish to build the docs, you'll need a few more dependencies. Inkscape
is used for conversion of SVGs to other formats, Graphviz is used for rendering
certain charts, and TeX Live is required for building PDF output. The following
command should install all required dependencies:

.. code-block:: console

    $ sudo apt-get install texlive-latex-recommended texlive-latex-extra \
        texlive-fonts-recommended graphviz inkscape python-sphinx

Once these are installed, you can use the "doc" target to build the
documentation:

.. code-block:: console

    $ workon picamera
    (picamera) $ cd ~/picamera
    (picamera) $ make doc

The HTML output is written to :file:`docs/_build/html` while the PDF output
goes to :file:`docs/_build/latex`.


.. _test_suite:

Test suite
==========

If you wish to run the picamera test suite, follow the instructions in
:ref:`dev_install` above and then make the "test" target within the sandbox:

.. code-block:: console

    $ workon picamera
    (picamera) $ cd ~/picamera
    (picamera) $ make test

.. warning::

    The test suite takes a *very* long time to execute (at least 1 hour on an
    overclocked Pi 3). Depending on configuration, it can also lockup the
    camera requiring a reboot to reset, so ensure you are familiar with SSH or
    using alternate TTYs to access a command line in the event you need to
    reboot.


