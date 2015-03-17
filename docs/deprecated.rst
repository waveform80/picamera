.. _deprecated:

========================
Deprecated Functionality
========================

The picamera library is (at the time of writing) nearly a year old and has
grown quite rapidly in this time. Occasionally, when adding new functionality
to the library, the API is obvious and natural (e.g.
:meth:`~picamera.camera.PiCamera.start_recording` and
:meth:`~picamera.camera.PiCamera.stop_recording`). At other times, it's been
less obvious (e.g. unencoded captures) and my initial attempts have proven to
be less than ideal. In such situations I've endeavoured to improve the API
without breaking backward compatibility by introducing new methods or
attributes and deprecating the old ones.

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
to the intended replacement functionality (see
:attr:`~picamera.camera.PiCamera.raw_format` for example). However, Python also
provides excellent methods for determining automatically whether any deprecated
functionality is being used via the :mod:`warnings` module.


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

And produces the following output on the console when run::

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

Now when we run the script it produces the following::

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
tuple for the framerate. Now we run again, and this time get the following::

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
specifying the ``'raw'`` format with the
:meth:`~picamera.camera.PiCamera.capture` method, with the
:attr:`~picamera.camera.PiCamera.raw_format` attribute providing the actual
encoding. The attribute is deprecated, as is usage of the value ``'raw'`` with
the *format* parameter of all the capture methods. Hence, code like this::

    camera.raw_format = 'rgb'
    camera.capture('output.data', format='raw')

Should be replaced with the following::

    camera.capture('output.data', format='rgb')


.. _deprecated_quantization:

Recording quality
-----------------

The *quantization* parameter for
:meth:`~picamera.camera.PiCamera.start_recording` and
:meth:`~picamera.camera.PiCamera.record_sequence` is deprecated in favor of the
*quality* parameter; this change was made to keep the recording methods
consistent with the capture methods, and to make the meaning of the parameter
more obvious to newcomers. The values of the parameter remain the same (i.e.
1-100 for MJPEG recordings with higher values indicating higher quality, and
1-40 for H.264 recordings with lower values indicating higher quality). Hence,
the following code::

    camera.start_recording('foo.h264', quantization=25)

should be replaced with::

    camera.start_recording('foo.h264', quality=25)


.. _deprecated_fractions:

Fractions as tuples
-------------------

Several attributes in picamera expect rational (fractional) values. In early
versions of picamera, these values could only be specified as a tuple expressed
as ``(numerator, denominator)``. In later versions, support was expanded to
accept any of Python's numeric types including :ref:`int <typesnumeric>`,
:ref:`float <typesnumeric>`, :class:`~decimal.Decimal`, and
:class:`~fractions.Fraction`. Hence, the following code::

    camera.framerate = (24, 1)

can be replaced with any of the following variations::

    from decimal import Decimal
    from fractions import Fraction

    camera.framerate = 24
    camera.framerate = 24.0
    camera.framerate = Fraction(72, 3)
    camera.framerate = Decimal('24')
    camera.framerate = Fraction('48/2')

These attributes return a :class:`~fractions.Fraction` instance as well, but
one modified to permit access as a tuple in order to maintain backward
compatibility. This is also deprecated, hence code like this::

    n, d = camera.framerate
    print('The framerate is %d/%d fps' % (n, d))

should be updated to this::

    f = camera.framerate
    print('The framerate is %d/%d fps' % (f.numerator, f.denominator))

Although you may wish to simply convert the :class:`~fractions.Fraction`
instance to a :ref:`float <typesnumeric>` for greater convenience::

    f = float(camera.framerate)
    print('The framerate is %0.2f fps' % f)


.. _deprecated_preview:

Preview functions
-----------------

Release 1.8 introduced rather sweeping changes to the preview system to
incorporate the ability to create multiple static overlays on top of the
preview. As a result, the preview system is no longer "part of" the
:class:`~picamera.camera.PiCamera` class. Instead, it is represented by the
:attr:`~picamera.camera.PiCamera.preview` attribute which is a separate
:class:`~picamera.renderers.PiPreviewRenderer` instance when the preview is
active. In turn this meant that :attr:`~picamera.camera.PiCamera.preview_alpha`
was deprecated in favor of the :attr:`~picamera.renderers.PiRenderer.alpha`
property of the new :attr:`~picamera.camera.PiCamera.preview` attribute.
Similar changes were made to :attr:`~picamera.camera.PiCamera.preview_layer`,
:attr:`~picamera.camera.PiCamera.preview_fullscreen`, and
:attr:`~picamera.camera.PiCamera.preview_window`. Hence, the following code::

    camera.start_preview()
    camera.preview_alpha = 128
    camera.preview_fullscreen = False
    camera.preview_window = (0, 0, 640, 480)

should be replaced with::

    camera.start_preview()
    camera.preview.alpha = 128
    camera.preview.fullscreen = False
    camera.preview.window = (0, 0, 640, 480)

Not an enormous change, but the eagle-eyed will have noticed that the
:attr:`~picamera.camera.PiCamera.preview` attribute is set to ``None`` when the
preview is not active. This means that setting the
:attr:`~picamera.renderers.PiRenderer.alpha` property *before* the preview is
active is no longer possible. To accomodate this use-case, optional parameters
were added to :meth:`~picamera.camera.PiCamera.start_preview` to provide
initial settings for the preview renderer. Therefore, the following code::

    camera.preview_alpha = 128
    camera.preview_fullscreen = False
    camera.preview_window = (0, 0, 640, 480)
    camera.start_preview()

should be replaced with::

    camera.start_preview(
        alpha=128, fullscreen=False, window=(0, 0, 640, 480))

Finally, the :attr:`~picamera.camera.PiCamera.previewing` attribute is now
obsolete (and thus deprecated) as its functionality can be trivially obtained
by checking the :attr:`~picamera.camera.PiCamera.preview` attribute. Hence, the
following code::

    if camera.previewing:
        print('The camera preview is running')
    else:
        print('The camera preview is not running')

can be replaced with::

    if camera.preview:
        print('The camera preview is running')
    else:
        print('The camera preview is not running')


.. _deprecated_truncate:

Array stream truncation
-----------------------

In release 1.8, the base :class:`~picamera.array.PiArrayOutput` class was
changed to derive from :class:`io.BytesIO` in order to add support for seeking,
and to improve performance. The prior implementation had been non-seekable, and
therefore to accommodate re-use of the stream between captures the
:meth:`~picamera.array.PiArrayOutput.truncate` method had an unusual
side-effect not seen with regular Python streams: after truncation, the
position of the stream was set to the new length of the stream. In all other
Python streams, the ``truncate`` method doesn't affect the stream position. The
method is overridden in 1.8 to maintain its unusual behaviour, but this
behaviour is nonetheless deprecated.

If you only need your code to work with the latest version of picamera you
can replace calls like the following::

    with picamera.array.PiYUVArray(camera) as stream:
        for i in range(3):
            camera.capture(stream, 'yuv')
            print(stream.array.shape)
            stream.truncate(0)

with this::

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

In release 1.8, the :attr:`~picamera.camera.PiCamera.crop` attribute was
renamed to :attr:`~picamera.camera.PiCamera.zoom`; the old name was retained as
a deprecated alias for backward compatibility. This change was made as ``crop``
was a thoroughly misleading name for the attribute (which actually sets the
"region of interest" for the sensor), leading to numerous support questions.
Hence, the following code::

    camera.crop = (0.25, 0.25, 0.5, 0.5)

should be changed to::

    camera.zoom = (0.25, 0.25, 0.5, 0.5)


.. _deprecated_iso:

Incorrect ISO capitalisation
----------------------------

In release 1.8, the :attr:`~picamera.camera.PiCamera.ISO` attribute was renamed
to :attr:`~picamera.camera.PiCamera.iso` for compliance with `PEP-8`_ (even
though it's an acronym this is still more consistent with the existing API;
consider :attr:`~picamera.camera.PiCamera.led`,
:attr:`~picamera.camera.PiCamera.awb_mode`, and so on). This means the
following code::

    camera.ISO = 100

should simply be replaced with::

    camera.iso = 100


.. _deprecated_frame_type:

Frame types
-----------

Over time, several capabilities were added to the H.264 encoder in the GPU
firmware. This expanded the number of possible frame types from a simple
key-frame / non-key-frame affair, to a multitude of possibilities (P-frame,
I-frame, SPS/PPS header, motion vector data, and who knows in future). Rather
than keep adding more and more boolean fields to the
:class:`~picamera.encoders.PiVideoFrame` named tuple, release 1.5 introduced
the :class:`~picamera.encoders.PiVideoFrameType` enumeration used by the
:attr:`~picamera.encoders.PiVideoFrame.frame_type` attribute and deprecated the
:attr:`~picamera.encoders.PiVideoFrame.keyframe` and
:attr:`~picamera.encoders.PiVideoFrame.header` attributes. Hence, the following
code::

    if camera.frame.keyframe:
        handle_keyframe()
    elif camera.frame.header:
        handle_header()
    else:
        handle_frame()

should be replaced with::

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

In release 1.10, the :attr:`~picamera.camera.PiCamera.annotate_background`
attribute was enhanced to support setting the background color of annotation
text. Older versions of picamera treated this attribute as a bool (``False``
for no background, ``True`` to draw a black background).

In order to provide the new functionality while maintaining a certain amount of
backward compatibility the new attribute accepts ``None`` for no background
(note that the "truthiness" of ``None`` is the same as ``False`` so existing
tests should continue to work), and a :class:`~picamera.color.Color` instance
for a custom background color (:class:`~picamera.color.Color` instances are
"truthy" so again, existing tests against the attribute continue to work).

Setting the attribute as a bool is now deprecated. Hence, the following code::

    camera.annotate_background = False
    camera.annotate_background = True

should be replaced with::

    camera.annotate_background = None
    camera.annotate_background = picamera.Color('black')

Naive tests against the attribute should work as normal, but specific tests
(which are considered bad practice anyway), should be re-written. For example::

    if camera.annotate_background == False:
        pass
    if camera.annotate_background is True:
        pass

should become::

    if not camera.annotate_background:
        pass
    if camera.annotate_background:
        pass


.. _semantic versioning: http://semver.org/
.. _PEP-8: http://legacy.python.org/dev/peps/pep-0008/

