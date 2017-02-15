# vim: set et sw=4 sts=4 fileencoding=utf-8:
#
# Python camera library for the Rasperry-Pi camera module
# Copyright (c) 2013-2015 Dave Jones <dave@waveform.org.uk>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the copyright holder nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

"""
The picamera package consists of several modules which provide a pure Python
interface to the Raspberry Pi's camera module. The package is only intended to
run on a Raspberry Pi, and expects to be able to load the MMAL library
(libmmal.so) upon import.

The classes defined by most modules in this package are available directly from
the :mod:`picamera` namespace. In other words, the following code is typically
all that is required to access classes in the package::

    import picamera

The :mod:`picamera.array` module is an exception to this as it depends on the
third-party `numpy`_ package (this avoids making numpy a mandatory dependency
for picamera).

.. _numpy: http://www.numpy.org/


The following sections document the various modules available within the
package:

* :mod:`picamera.camera`
* :mod:`picamera.encoders`
* :mod:`picamera.frames`
* :mod:`picamera.streams`
* :mod:`picamera.renderers`
* :mod:`picamera.color`
* :mod:`picamera.exc`
* :mod:`picamera.array`
"""

from __future__ import (
    unicode_literals,
    print_function,
    division,
    absolute_import,
    )

# Make Py2's str equivalent to Py3's
str = type('')

from picamera.exc import (
    PiCameraWarning,
    PiCameraDeprecated,
    PiCameraFallback,
    PiCameraAlphaStripping,
    PiCameraResizerEncoding,
    PiCameraError,
    PiCameraRuntimeError,
    PiCameraClosed,
    PiCameraNotRecording,
    PiCameraAlreadyRecording,
    PiCameraValueError,
    PiCameraMMALError,
    PiCameraPortDisabled,
    mmal_check,
    )
from picamera.mmalobj import PiResolution, PiFramerateRange
from picamera.camera import PiCamera
from picamera.display import PiDisplay
from picamera.frames import PiVideoFrame, PiVideoFrameType
from picamera.encoders import (
    PiEncoder,
    PiVideoEncoder,
    PiImageEncoder,
    PiRawMixin,
    PiCookedVideoEncoder,
    PiRawVideoEncoder,
    PiOneImageEncoder,
    PiMultiImageEncoder,
    PiRawImageMixin,
    PiCookedOneImageEncoder,
    PiRawOneImageEncoder,
    PiCookedMultiImageEncoder,
    PiRawMultiImageEncoder,
    )
from picamera.renderers import (
    PiRenderer,
    PiOverlayRenderer,
    PiPreviewRenderer,
    PiNullSink,
    )
from picamera.streams import PiCameraCircularIO, CircularIO, BufferIO
from picamera.color import Color, Red, Green, Blue, Hue, Lightness, Saturation

