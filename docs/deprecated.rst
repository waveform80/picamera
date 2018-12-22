.. _deprecated:

========================
Deprecated Functionality
========================

.. currentmodule:: picamera

The picamera library is (at the time of writing) nearly a year old and has
grown quite rapidly in this time. Occasionally, when adding new functionality
to the library, the API is obvious and natural (e.g.
:meth:`~PiCamera.start_recording` and :meth:`~PiCamera.stop_recording`). At
other times, it's been less obvious (e.g. unencoded captures) and my initial
attempts have proven to be less than ideal. In such situations I've endeavoured
to improve the API without breaking backward compatibility by introducing new
methods or attributes and deprecating the old ones.

This means that, as of release 1.8, there's quite a lot of deprecated
functionality floating around the library which it would be nice to tidy up,
partly to simplify the library for debugging, and partly to simplify it for new
users. To assuage any fears that I'm imminently going to break backward
compatibility: I intend to leave a gap of at least a year between deprecating
functionality and removing it, hopefully providing ample time for people to
migrate their scripts.

Furthermore, to distinguish any release which is backwards incompatible, I
would increment the major version number in accordance with `semantic
versioning`_. In other words, the first release in which currently deprecated
functionality would be removed would be version 2.0, and as of the release of
1.8 it's at least a year away. Any future 1.x releases will include all
currently deprecated functions.

Of course, that still means people need a way of determining whether their
scripts use any deprecated functionality in the picamera library. All
deprecated functionality is documented, and the documentation includes pointers
to the intended replacement functionality (see :attr:`~PiCamera.raw_format` for
example). However, Python also provides excellent methods for determining
automatically whether any deprecated functionality is being used via the
:mod:`warnings` module.


.. _find_deprecated:

Finding and fixing deprecated usage
===================================

As of release 1.8, all deprecated functionality will raise
:exc:`DeprecationWarning` when used. By default, the Python interpreter
suppresses these warnings (as they're only of interest to developers, not
users) but you can easily configure different behaviour.

The following example script uses a number of deprecated functions::

    import io
    import time
    import picamera

    with picamera.PiCamera() as camera:
        camera.resolution = (1280, 720)
        camera.framerate = (24, 1)
        camera.start_preview()
        camera.preview_fullscreen = True
        camera.preview_alpha = 128
        time.sleep(2)
        camera.raw_format = 'yuv'
        stream = io.BytesIO()
        camera.capture(stream, 'raw', use_video_port=True)

Despite using deprecated functionality the script runs happily (and silently)
with picamera 1.8. To discover what deprecated functions are being used, we add
a couple of lines to tell the warnings module that we want "default" handling
of :exc:`DeprecationWarning`; "default" handling means that the first time an
attempt is made to raise this warning at a particular location, the warning's
details will be printed to the console. All future invocations from the same
location will be ignored. This saves flooding the console with warning details
from tight loops. With this change, the script looks like this::

    import io
    import time
    import picamera

    import warnings
    warnings.filterwarnings('default', category=DeprecationWarning)

    with picamera.PiCamera() as camera:
        camera.resolution = (1280, 720)
        camera.framerate = (24, 1)
        camera.start_preview()
        camera.preview_fullscreen = True
        camera.preview_alpha = 128
        time.sleep(2)
        camera.raw_format = 'yuv'
        stream = io.BytesIO()
        camera.capture(stream, 'raw', use_video_port=True)

And produces the following output on the console when run:

.. code-block:: text

    /usr/share/pyshared/picamera/camera.py:149: DeprecationWarning: Setting framerate or gains as a tuple is deprecated; please use one of Python's many numeric classes like int, float, Decimal, or Fraction instead
      "Setting framerate or gains as a tuple is deprecated; "
    /usr/share/pyshared/picamera/camera.py:3125: DeprecationWarning: PiCamera.preview_fullscreen is deprecated; use PiCamera.preview.fullscreen instead
      'PiCamera.preview_fullscreen is deprecated; '
    /usr/share/pyshared/picamera/camera.py:3068: DeprecationWarning: PiCamera.preview_alpha is deprecated; use PiCamera.preview.alpha instead
      'PiCamera.preview_alpha is deprecated; use '
    /usr/share/pyshared/picamera/camera.py:1833: DeprecationWarning: PiCamera.raw_format is deprecated; use required format directly with capture methods instead
      'PiCamera.raw_format is deprecated; use required format '
    /usr/share/pyshared/picamera/camera.py:1359: DeprecationWarning: The "raw" format option is deprecated; specify the required format directly instead ("yuv", "rgb", etc.)
      'The "raw" format option is deprecated; specify the '
    /usr/share/pyshared/picamera/camera.py:1827: DeprecationWarning: PiCamera.raw_format is deprecated; use required format directly with capture methods instead
      'PiCamera.raw_format is deprecated; use required format '

This tells us which pieces of deprecated functionality are being used in our
script, but it doesn't tell us where in the script they were used. For this,
it is more useful to have warnings converted into full blown exceptions. With
this change, each time a :exc:`DeprecationWarning` would have been printed, it
will instead cause the script to terminate with an unhandled exception and a
full stack trace::

    import io
    import time
    import picamera

    import warnings
    warnings.filterwarnings('error', category=DeprecationWarning)

    with picamera.PiCamera() as camera:
        camera.resolution = (1280, 720)
        camera.framerate = (24, 1)
        camera.start_preview()
        camera.preview_fullscreen = True
        camera.preview_alpha = 128
        time.sleep(2)
        camera.raw_format = 'yuv'
        stream = io.BytesIO()
        camera.capture(stream, 'raw', use_video_port=True)

Now when we run the script it produces the following:

.. code-block:: pycon

    Traceback (most recent call last):
      File "test_deprecated.py", line 10, in <module>
        camera.framerate = (24, 1)
      File "/usr/share/pyshared/picamera/camera.py", line 1888, in _set_framerate
        n, d = to_rational(value)
      File "/usr/share/pyshared/picamera/camera.py", line 149, in to_rational
        "Setting framerate or gains as a tuple is deprecated; "
    DeprecationWarning: Setting framerate or gains as a tuple is deprecated; please use one of Python's many numeric classes like int, float, Decimal, or Fraction instead

This tells us that line 10 of our script is using deprecated functionality, and
provides a hint of how to fix it. We change line 10 to use an int instead of a
tuple for the framerate. Now we run again, and this time get the following:

.. code-block:: pycon

    Traceback (most recent call last):
      File "test_deprecated.py", line 12, in <module>
        camera.preview_fullscreen = True
      File "/usr/share/pyshared/picamera/camera.py", line 3125, in _set_preview_fullscreen
        'PiCamera.preview_fullscreen is deprecated; '
    DeprecationWarning: PiCamera.preview_fullscreen is deprecated; use PiCamera.preview.fullscreen instead

Now we can tell line 12 has a problem, and once again the exception tells us
how to fix it. We continue in this fashion until the script looks like this::

    import io
    import time
    import picamera

    import warnings
    warnings.filterwarnings('error', category=DeprecationWarning)

    with picamera.PiCamera() as camera:
        camera.resolution = (1280, 720)
        camera.framerate = 24
        camera.start_preview()
        camera.preview.fullscreen = True
        camera.preview.alpha = 128
        time.sleep(2)
        stream = io.BytesIO()
        camera.capture(stream, 'yuv', use_video_port=True)

The script now runs to completion, so we can be confident it's no longer using
any deprecated functionality and will run happily even when this functionality
is removed in release 2.0. At this point, you may wish to remove the
``filterwarnings`` line as well (or at least comment it out).


.. _deprecated_list:

List of deprecated functionality
================================

For convenience, all currently deprecated functionality is detailed below. You
may wish to skim this list to check whether you're currently using deprecated
functions, but I would urge users to take advantage of the warnings system
documented in the prior section as well.


.. _deprecated_raw_capture:

Unencoded captures
------------------

In very early versions of picamera, unencoded captures were created by
specifying the ``'raw'`` format with the :meth:`~PiCamera.capture` method, with
the :attr:`~PiCamera.raw_format` attribute providing the actual encoding. The
attribute is deprecated, as is usage of the value ``'raw'`` with the *format*
parameter of all the capture methods.

The deprecated method of taking unencoded captures looks like this::

    camera.raw_format = 'rgb'
    camera.capture('output.data', format='raw')

In such cases, simply remove references to :attr:`~PiCamera.raw_format` and
place the required format directly within the :meth:`~PiCamera.capture` call::

    camera.capture('output.data', format='rgb')


.. _deprecated_quantization:

Recording quality
-----------------

The *quantization* parameter for :meth:`~PiCamera.start_recording` and
:meth:`~PiCamera.record_sequence` is deprecated in favor of the *quality*
parameter; this change was made to keep the recording methods consistent with
the capture methods, and to make the meaning of the parameter more obvious to
newcomers. The values of the parameter remain the same (i.e.  1-100 for MJPEG
recordings with higher values indicating higher quality, and 1-40 for H.264
recordings with lower values indicating higher quality).

The deprecated method of setting recording quality looks like this::

    camera.start_recording('foo.h264', quantization=25)

Simply replace the ``quantization`` parameter with the ``quality`` parameter
like so::

    camera.start_recording('foo.h264', quality=25)


.. _deprecated_fractions:

Fractions as tuples
-------------------

Several attributes in picamera expect rational (fractional) values. In early
versions of picamera, these values could only be specified as a tuple expressed
as ``(numerator, denominator)``. In later versions, support was expanded to
accept any of Python's numeric types.

The following code illustrates the deprecated usage of a tuple representing
a rational value::

    camera.framerate = (24, 1)

Such cases can be replaced with any of Python's numeric types, including
:ref:`int <typesnumeric>`, :ref:`float <typesnumeric>`,
:class:`~decimal.Decimal`, and :class:`~fractions.Fraction`. All the following
examples are functionally equivalent to the deprecated example above::

    from decimal import Decimal
    from fractions import Fraction

    camera.framerate = 24
    camera.framerate = 24.0
    camera.framerate = Fraction(72, 3)
    camera.framerate = Decimal('24')
    camera.framerate = Fraction('48/2')

These attributes return a :class:`~fractions.Fraction` instance as well, but
one modified to permit access as a tuple in order to maintain backward
compatibility. This is also deprecated behaviour. The following example
demonstrates accessing the :attr:`~PiCamera.framerate` attribute as a tuple::

    n, d = camera.framerate
    print('The framerate is %d/%d fps' % (n, d))

In such cases, use the standard :attr:`~fractions.Fraction.numerator` and
:attr:`~fractions.Fraction.denominator` attributes of the returned fraction
instead::

    f = camera.framerate
    print('The framerate is %d/%d fps' % (f.numerator, f.denominator))

Alternatively, you may wish to simply convert the :class:`~fractions.Fraction`
instance to a :ref:`float <typesnumeric>` for greater convenience::

    f = float(camera.framerate)
    print('The framerate is %0.2f fps' % f)


.. _deprecated_preview:

Preview functions
-----------------

Release 1.8 introduced rather sweeping changes to the preview system to
incorporate the ability to create multiple static overlays on top of the
preview. As a result, the preview system is no longer incorporated into the
:class:`PiCamera` class. Instead, it is represented by the
:attr:`~PiCamera.preview` attribute which is a separate
:class:`PiPreviewRenderer` instance when the preview is active.

This change meant that :attr:`~PiCamera.preview_alpha` was deprecated in favor
of the :attr:`~PiRenderer.alpha` property of the new :attr:`~PiCamera.preview`
attribute.  Similar changes were made to :attr:`~PiCamera.preview_layer`,
:attr:`~PiCamera.preview_fullscreen`, and :attr:`~PiCamera.preview_window`. The
following snippet illustrates the deprecated method of setting preview related
attributes::

    camera.start_preview()
    camera.preview_alpha = 128
    camera.preview_fullscreen = False
    camera.preview_window = (0, 0, 640, 480)

In this case, where preview attributes are altered *after* the preview has
been activated, simply modify the corresponding attributes on the preview
object::

    camera.start_preview()
    camera.preview.alpha = 128
    camera.preview.fullscreen = False
    camera.preview.window = (0, 0, 640, 480)

Unfortuantely, this simple change is not possible when preview attributes are
altered *before* the preview has been activated, as the
:attr:`~PiCamera.preview` attribute is ``None`` when the preview is not active.
To accomodate this use-case, optional parameters were added to
:meth:`~PiCamera.start_preview` to provide initial settings for the preview
renderer. The following example illustrates the deprecated method of setting
preview related attribtues prior to activating the preview::

    camera.preview_alpha = 128
    camera.preview_fullscreen = False
    camera.preview_window = (0, 0, 640, 480)
    camera.start_preview()

Remove the lines setting the attributes, and use the corresponding keyword
parameters of the :meth:`~PiCamera.start_preview` method instead::

    camera.start_preview(
        alpha=128, fullscreen=False, window=(0, 0, 640, 480))

Finally, the :attr:`~PiCamera.previewing` attribute is now obsolete (and thus
deprecated) as its functionality can be trivially obtained by checking the
:attr:`~PiCamera.preview` attribute. The following example illustrates the
deprecated method of checking whether the preview is activate::

    if camera.previewing:
        print('The camera preview is running')
    else:
        print('The camera preview is not running')

Simply replace :attr:`~PiCamera.previewing` with :attr:`~PiCamera.preview` to
bring this code up to date::

    if camera.preview:
        print('The camera preview is running')
    else:
        print('The camera preview is not running')


.. _deprecated_truncate:

Array stream truncation
-----------------------

In release 1.8, the base :class:`~array.PiArrayOutput` class was changed to
derive from :class:`io.BytesIO` in order to add support for seeking, and to
improve performance. The prior implementation had been non-seekable, and
therefore to accommodate re-use of the stream between captures the
:meth:`~array.PiArrayOutput.truncate` method had an unusual side-effect not
seen with regular Python streams: after truncation, the position of the stream
was set to the new length of the stream. In all other Python streams, the
``truncate`` method doesn't affect the stream position. The method is
overridden in 1.8 to maintain its unusual behaviour, but this behaviour is
nonetheless deprecated.

The following snippet illustrates the method of truncating an array stream
in picamera versions 1.7 and older::

    with picamera.array.PiYUVArray(camera) as stream:
        for i in range(3):
            camera.capture(stream, 'yuv')
            print(stream.array.shape)
            stream.truncate(0)

If you only need your script to work with picamera versions 1.8 and newer,
such code should be updated to use ``seek`` and ``truncate`` as you would
with any regular Python stream instance::

    with picamera.array.PiYUVArray(camera) as stream:
        for i in range(3):
            camera.capture(stream, 'yuv')
            print(stream.array.shape)
            stream.seek(0)
            stream.truncate()

Unfortunately, this will not work if your script needs to work with prior
versions of picamera as well (since such streams were non-seekable in prior
versions). In this case, call :meth:`~io.BytesIO.seekable` to determine the
correct course of action::

    with picamera.array.PiYUVArray(camera) as stream:
        for i in range(3):
            camera.capture(stream, 'yuv')
            print(stream.array.shape)
            if stream.seekable():
                stream.seek(0)
                stream.truncate()
            else:
                stream.truncate(0)


.. _deprecated_crop:

Confusing crop
--------------

In release 1.8, the :attr:`~PiCamera.crop` attribute was renamed to
:attr:`~PiCamera.zoom`; the old name was retained as a deprecated alias for
backward compatibility. This change was made as ``crop`` was a thoroughly
misleading name for the attribute (which actually sets the "region of interest"
for the sensor), leading to numerous support questions.

The following example illustrates the deprecated attribute name::

    camera.crop = (0.25, 0.25, 0.5, 0.5)

Simply replace :attr:`~PiCamera.crop` with :attr:`~PiCamera.zoom` in such
cases::

    camera.zoom = (0.25, 0.25, 0.5, 0.5)


.. _deprecated_iso:

Incorrect ISO capitalisation
----------------------------

In release 1.8, the :attr:`~PiCamera.ISO` attribute was renamed to
:attr:`~PiCamera.iso` for compliance with `PEP-8`_ (even though it's an acronym
this is still more consistent with the existing API; consider
:attr:`~PiCamera.led`, :attr:`~PiCamera.awb_mode`, and so on).

The following example illustrates the deprecated attribute case::

    camera.ISO = 100

Simply replace references to :attr:`~PiCamera.ISO` with :attr:`~PiCamera.iso`::

    camera.iso = 100


.. _deprecated_frame_type:

Frame types
-----------

Over time, several capabilities were added to the H.264 encoder in the GPU
firmware. This expanded the number of possible frame types from a simple
key-frame / non-key-frame affair, to a multitude of possibilities (P-frame,
I-frame, SPS/PPS header, motion vector data, and who knows in future). Rather
than keep adding more and more boolean fields to the :class:`PiVideoFrame`
named tuple, release 1.5 introduced the :class:`PiVideoFrameType` enumeration
used by the :attr:`~PiVideoFrame.frame_type` attribute and deprecated the
:attr:`~PiVideoFrame.keyframe` and :attr:`~PiVideoFrame.header` attributes.

The following code illustrates usage of the deprecated boolean fields::

    if camera.frame.keyframe:
        handle_keyframe()
    elif camera.frame.header:
        handle_header()
    else:
        handle_frame()

In such cases, test the :attr:`~PiVideoFrame.frame_type` attribute against the
corresponding value of the :class:`PiVideoFrameType` enumeration::

    if camera.frame.frame_type == picamera.PiVideoFrameType.key_frame:
        handle_keyframe()
    elif camera.frame.frame_type == picamera.PiVideoFrameType.sps_header:
        handle_header()
    else:
        handle_frame()

Alternatively, you may find something like this more elegant (and more future
proof as it'll throw a :exc:`KeyError` in the event of an unrecognized
frame type)::

    handler = {
        picamera.PiVideoFrameType.key_frame:  handle_keyframe,
        picamera.PiVideoFrameType.sps_header: handle_header,
        picamera.PiVideoFrameType.frame:      handle_frame,
        }[camera.frame.frame_type]
    handler()


.. _deprecated_annotate_background:

Annotation background color
---------------------------

In release 1.10, the :attr:`~PiCamera.annotate_background` attribute was
enhanced to support setting the background color of annotation text. Older
versions of picamera treated this attribute as a bool (``False`` for no
background, ``True`` to draw a black background).

In order to provide the new functionality while maintaining a certain amount of
backward compatibility, the new attribute accepts ``None`` for no background
and a :class:`Color` instance for a custom background color.  It is worth
noting that the truth values of ``None`` and ``False`` are equivalent, as are
the truth values of a :class:`Color` instance and ``True``. Hence, naive tests
against the attribute value will continue to work.

The following example illustrates the deprecated behaviour of setting the
attribute as a boolean::

    camera.annotate_background = False
    camera.annotate_background = True

In such cases, replace ``False`` with ``None``, and ``True`` with a
:class:`Color` instance of your choosing. Bear in mind that older Pi firmwares
can only produce a black background, so you may wish to stick with black to
ensure equivalent behaviour::

    camera.annotate_background = None
    camera.annotate_background = picamera.Color('black')

Naive tests against the attribute should work as normal, but specific tests
(which are considered bad practice anyway), should be re-written. The following
example illustrates specific boolean tests::

    if camera.annotate_background == False:
        pass
    if camera.annotate_background is True:
        pass

Such cases should be re-written to remove the specific boolean value mentioned
in the test (this is a general rule, not limited to this deprecation case)::

    if not camera.annotate_background:
        pass
    if camera.annotate_background:
        pass


Analysis classes use analyze
----------------------------

The various analysis classes in :mod:`picamera.array` were adjusted in 1.11 to
use :meth:`~array.PiAnalysisOutput.analyze` (US English spelling) instead of
``analyse`` (UK English spelling). The following example illustrates the old
usage::

    import picamera.array

    class MyAnalyzer(picamera.array.PiRGBAnalysis):
        def analyse(self, array):
            print('Array shape:', array.shape)

This should simply be re-written as::

    import picamera.array

    class MyAnalyzer(picamera.array.PiRGBAnalysis):
        def analyze(self, array):
            print('Array shape:', array.shape)


Positional args for PiCamera
----------------------------

The :class:`PiCamera` class was adjusted in 1.14 to expect keyword arguments on
construction. The following used to be accepted (although it was still rather
bad practice)::

    import picamera

    camera = picamera.PiCamera(0, 'none', False, '720p')

This should now be re-written as::

    import picamera

    camera = picamera.PiCamera(camera_num=0, stereo_mode='none',
                               stereo_decimate=False, resolution='720p')

Although if you only wanted to set ``resolution`` you could simply write this
as::

    import picamera

    camera = picamera.PiCamera(resolution='720p')


Color module
------------

The :mod:`picamera.color` module has now been split off into the `colorzero`_
library and as such is deprecated in its entirety. The `colorzero`_ library
contains everything that the color module used, along with a few enhancements
and several bug fixes and as such the transition is expected to be trivial.
Look for any imports of the :class:`~picamera.color.Color` class::

    from picamera import Color

    c = Color('green')

Replace these with references to :class:`colorzero.Color` instead::

    from colorzero import Color

    c = Color('green')

Alternatively, if the :class:`~picamera.color.Color` class is being used
directly from picamera itself::

    import picamera

    camera = picamera.PiCamera()
    c = picamera.Color('red')

In this case add an import for colorzero, and reference the class from there::

    import picamera
    import colorzero

    camera = picamera.PiCamera()
    c = colorzero.Color('red')


.. _semantic versioning: http://semver.org/
.. _PEP-8: http://legacy.python.org/dev/peps/pep-0008/
.. _colorzero: https://colorzero.readthedocs.io/
