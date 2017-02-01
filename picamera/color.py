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

from __future__ import (
    unicode_literals,
    print_function,
    division,
    absolute_import,
    )
# Make Py2's zip equivalent to Py3's
try:
    from itertools import izip as zip
except ImportError:
    pass

# Make Py2's str and range equivalent to Py3's
str = type('')


import colorsys
from math import pi, sqrt, atan2, degrees, radians, sin, cos, exp
from fractions import Fraction
from collections import namedtuple


# From the CSS Color Module Level 3 specification, section 4.3
# <http://www.w3.org/TR/css3-color/#svg-color>
NAMED_COLORS = {
    'aliceblue':             '#f0f8ff',
    'antiquewhite':          '#faebd7',
    'aqua':                  '#00ffff',
    'aquamarine':            '#7fffd4',
    'azure':                 '#f0ffff',
    'beige':                 '#f5f5dc',
    'bisque':                '#ffe4c4',
    'black':                 '#000000',
    'blanchedalmond':        '#ffebcd',
    'blue':                  '#0000ff',
    'blueviolet':            '#8a2be2',
    'brown':                 '#a52a2a',
    'burlywood':             '#deb887',
    'cadetblue':             '#5f9ea0',
    'chartreuse':            '#7fff00',
    'chocolate':             '#d2691e',
    'coral':                 '#ff7f50',
    'cornflowerblue':        '#6495ed',
    'cornsilk':              '#fff8dc',
    'crimson':               '#dc143c',
    'cyan':                  '#00ffff',
    'darkblue':              '#00008b',
    'darkcyan':              '#008b8b',
    'darkgoldenrod':         '#b8860b',
    'darkgray':              '#a9a9a9',
    'darkgreen':             '#006400',
    'darkgrey':              '#a9a9a9',
    'darkkhaki':             '#bdb76b',
    'darkmagenta':           '#8b008b',
    'darkolivegreen':        '#556b2f',
    'darkorange':            '#ff8c00',
    'darkorchid':            '#9932cc',
    'darkred':               '#8b0000',
    'darksalmon':            '#e9967a',
    'darkseagreen':          '#8fbc8f',
    'darkslateblue':         '#483d8b',
    'darkslategray':         '#2f4f4f',
    'darkslategrey':         '#2f4f4f',
    'darkturquoise':         '#00ced1',
    'darkviolet':            '#9400d3',
    'deeppink':              '#ff1493',
    'deepskyblue':           '#00bfff',
    'dimgray':               '#696969',
    'dimgrey':               '#696969',
    'dodgerblue':            '#1e90ff',
    'firebrick':             '#b22222',
    'floralwhite':           '#fffaf0',
    'forestgreen':           '#228b22',
    'fuchsia':               '#ff00ff',
    'gainsboro':             '#dcdcdc',
    'ghostwhite':            '#f8f8ff',
    'gold':                  '#ffd700',
    'goldenrod':             '#daa520',
    'gray':                  '#808080',
    'green':                 '#008000',
    'greenyellow':           '#adff2f',
    'grey':                  '#808080',
    'honeydew':              '#f0fff0',
    'hotpink':               '#ff69b4',
    'indianred':             '#cd5c5c',
    'indigo':                '#4b0082',
    'ivory':                 '#fffff0',
    'khaki':                 '#f0e68c',
    'lavender':              '#e6e6fa',
    'lavenderblush':         '#fff0f5',
    'lawngreen':             '#7cfc00',
    'lemonchiffon':          '#fffacd',
    'lightblue':             '#add8e6',
    'lightcoral':            '#f08080',
    'lightcyan':             '#e0ffff',
    'lightgoldenrodyellow':  '#fafad2',
    'lightgray':             '#d3d3d3',
    'lightgreen':            '#90ee90',
    'lightgrey':             '#d3d3d3',
    'lightpink':             '#ffb6c1',
    'lightsalmon':           '#ffa07a',
    'lightseagreen':         '#20b2aa',
    'lightskyblue':          '#87cefa',
    'lightslategray':        '#778899',
    'lightslategrey':        '#778899',
    'lightsteelblue':        '#b0c4de',
    'lightyellow':           '#ffffe0',
    'lime':                  '#00ff00',
    'limegreen':             '#32cd32',
    'linen':                 '#faf0e6',
    'magenta':               '#ff00ff',
    'maroon':                '#800000',
    'mediumaquamarine':      '#66cdaa',
    'mediumblue':            '#0000cd',
    'mediumorchid':          '#ba55d3',
    'mediumpurple':          '#9370db',
    'mediumseagreen':        '#3cb371',
    'mediumslateblue':       '#7b68ee',
    'mediumspringgreen':     '#00fa9a',
    'mediumturquoise':       '#48d1cc',
    'mediumvioletred':       '#c71585',
    'midnightblue':          '#191970',
    'mintcream':             '#f5fffa',
    'mistyrose':             '#ffe4e1',
    'moccasin':              '#ffe4b5',
    'navajowhite':           '#ffdead',
    'navy':                  '#000080',
    'oldlace':               '#fdf5e6',
    'olive':                 '#808000',
    'olivedrab':             '#6b8e23',
    'orange':                '#ffa500',
    'orangered':             '#ff4500',
    'orchid':                '#da70d6',
    'palegoldenrod':         '#eee8aa',
    'palegreen':             '#98fb98',
    'paleturquoise':         '#afeeee',
    'palevioletred':         '#db7093',
    'papayawhip':            '#ffefd5',
    'peachpuff':             '#ffdab9',
    'peru':                  '#cd853f',
    'pink':                  '#ffc0cb',
    'plum':                  '#dda0dd',
    'powderblue':            '#b0e0e6',
    'purple':                '#800080',
    'red':                   '#ff0000',
    'rosybrown':             '#bc8f8f',
    'royalblue':             '#4169e1',
    'saddlebrown':           '#8b4513',
    'salmon':                '#fa8072',
    'sandybrown':            '#f4a460',
    'seagreen':              '#2e8b57',
    'seashell':              '#fff5ee',
    'sienna':                '#a0522d',
    'silver':                '#c0c0c0',
    'skyblue':               '#87ceeb',
    'slateblue':             '#6a5acd',
    'slategray':             '#708090',
    'slategrey':             '#708090',
    'snow':                  '#fffafa',
    'springgreen':           '#00ff7f',
    'steelblue':             '#4682b4',
    'tan':                   '#d2b48c',
    'teal':                  '#008080',
    'thistle':               '#d8bfd8',
    'tomato':                '#ff6347',
    'turquoise':             '#40e0d0',
    'violet':                '#ee82ee',
    'wheat':                 '#f5deb3',
    'white':                 '#ffffff',
    'whitesmoke':            '#f5f5f5',
    'yellow':                '#ffff00',
    'yellowgreen':           '#9acd32',
    }


class Red(float):
    """
    Represents the red component of a :class:`Color` for use in
    transformations. Instances of this class can be constructed directly with a
    float value, or by querying the :attr:`Color.red` attribute. Addition,
    subtraction, and multiplication are supported with :class:`Color`
    instances. For example::

        >>> Color.from_rgb(0, 0, 0) + Red(0.5)
        <Color "#7f0000">
        >>> Color('#f00') - Color('#900').red
        <Color "#660000">
        >>> (Red(0.1) * Color('red')).red
        Red(0.1)
    """

    def __repr__(self):
        return "Red(%s)" % self


class Green(float):
    """
    Represents the green component of a :class:`Color` for use in
    transformations.  Instances of this class can be constructed directly with
    a float value, or by querying the :attr:`Color.green` attribute. Addition,
    subtraction, and multiplication are supported with :class:`Color`
    instances. For example::

        >>> Color(0, 0, 0) + Green(0.1)
        <Color "#001900">
        >>> Color.from_yuv(1, -0.4, -0.6) - Green(1)
        <Color "#50002f">
        >>> (Green(0.5) * Color('white')).rgb
        (Red(1.0), Green(0.5), Blue(1.0))
    """

    def __repr__(self):
        return "Green(%s)" % self


class Blue(float):
    """
    Represents the blue component of a :class:`Color` for use in
    transformations.  Instances of this class can be constructed directly with
    a float value, or by querying the :attr:`Color.blue` attribute. Addition,
    subtraction, and multiplication are supported with :class:`Color`
    instances. For example::

        >>> Color(0, 0, 0) + Blue(0.2)
        <Color "#000033">
        >>> Color.from_hls(0.5, 0.5, 1.0) - Blue(1)
        <Color "#00fe00">
        >>> Blue(0.9) * Color('white')
        <Color "#ffffe5">
    """

    def __repr__(self):
        return "Blue(%s)" % self


class Hue(float):
    """
    Represents the hue of a :class:`Color` for use in transformations.
    Instances of this class can be constructed directly with a float value in
    the range [0.0, 1.0) representing an angle around the `HSL hue wheel`_. As
    this is a circular mapping, 0.0 and 1.0 effectively mean the same thing,
    i.e.  out of range values will be normalized into the range [0.0, 1.0).

    The class can also be constructed with the keyword arguments ``deg`` or
    ``rad`` if you wish to specify the hue value in degrees or radians instead,
    respectively. Instances can also be constructed by querying the
    :attr:`Color.hue` attribute.

    Addition, subtraction, and multiplication are supported with :class:`Color`
    instances. For example::

        >>> Color(1, 0, 0).hls
        (0.0, 0.5, 1.0)
        >>> (Color(1, 0, 0) + Hue(deg=180)).hls
        (0.5, 0.5, 1.0)

    Note that whilst multiplication by a :class:`Hue` doesn't make much sense,
    it is still supported. However, the circular nature of a hue value can lead
    to suprising effects. In particular, since 1.0 is equivalent to 0.0 the
    following may be observed::

        >>> (Hue(1.0) * Color.from_hls(0.5, 0.5, 1.0)).hls
        (0.0, 0.5, 1.0)

    .. _HSL hue wheel: https://en.wikipedia.org/wiki/Hue
    """

    def __new__(cls, n=None, deg=None, rad=None):
        if n is not None:
            return super(Hue, cls).__new__(cls, n % 1.0)
        elif deg is not None:
            return super(Hue, cls).__new__(cls, (deg / 360.0) % 1.0)
        elif rad is not None:
            return super(Hue, cls).__new__(cls, (rad / (2 * pi)) % 1.0)
        else:
            raise ValueError('You must specify a value, or deg or rad')

    def __repr__(self):
        return "Hue(deg=%s)" % self.deg

    @property
    def deg(self):
        return self * 360.0

    @property
    def rad(self):
        return self * 2 * pi


class Lightness(float):
    """
    Represents the lightness of a :class:`Color` for use in transformations.
    Instances of this class can be constructed directly with a float value, or
    by querying the :attr:`Color.lightness` attribute. Addition, subtraction,
    and multiplication are supported with :class:`Color` instances. For
    example::

        >>> Color(0, 0, 0) + Lightness(0.1)
        <Color "#191919">
        >>> Color.from_rgb_bytes(0x80, 0x80, 0) - Lightness(0.2)
        <Color "#191900">
        >>> Lightness(0.9) * Color('wheat')
        <Color "#f0cd8d">
    """

    def __repr__(self):
        return "Lightness(%s)" % self


class Saturation(float):
    """
    Represents the saturation of a :class:`Color` for use in transformations.
    Instances of this class can be constructed directly with a float value, or
    by querying the :attr:`Color.saturation` attribute. Addition, subtraction,
    and multiplication are supported with :class:`Color` instances. For
    example::

        >>> Color(0.9, 0.9, 0.6) + Saturation(0.1)
        <Color "#ebeb92">
        >>> Color('red') - Saturation(1)
        <Color "#7f7f7f">
        >>> Saturation(0.5) * Color('wheat')
        <Color "#e4d9c3">
    """

    def __repr__(self):
        return "Lightness(%s)" % self



clamp_float = lambda v: max(0.0, min(1.0, v))
clamp_bytes = lambda v: max(0, min(255, v))
to_srgb = lambda c: 12.92 * c if c <= 0.0031308 else (1.055 * c ** (1/2.4) - 0.055)
from_srgb = lambda c: c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
D65 = (0.95047, 1.0, 1.08883)
U = lambda x, y, z: 4 * x / (x + 15 * y + 3 * z)
V = lambda x, y, z: 9 * y / (x + 15 * y + 3 * z)
matrix_mult = lambda m, n: (
        sum(mval * nval for mval, nval in zip(mrow, n))
        for mrow in m
        )

class Color(namedtuple('Color', ('red', 'green', 'blue'))):
    """
    The Color class is a tuple which represents a color as red, green, and
    blue components.

    The class has a flexible constructor which allows you to create an instance
    from a variety of color systems including `RGB`_, `Y'UV`_, `Y'IQ`_, `HLS`_,
    and `HSV`_.  There are also explicit constructors for each of these systems
    to allow you to force the use of a system in your code. For example, an
    instance of :class:`Color` can be constructed in any of the following
    ways::

        >>> Color('#f00')
        <Color "#ff0000">
        >>> Color('green')
        <Color "#008000">
        >>> Color(0, 0, 1)
        <Color "#0000ff">
        >>> Color(hue=0, saturation=1, value=0.5)
        <Color "#7f0000">
        >>> Color(y=0.4, u=-0.05, v=0.615)
        <Color "#ff0f4c">

    The specific forms that the default constructor will accept are enumerated
    below:

    .. tabularcolumns:: |p{40mm}|p{100mm}|

    +------------------------------+------------------------------------------+
    | Style                        | Description                              |
    +==============================+==========================================+
    | Single positional parameter  | Equivalent to calling                    |
    |                              | :meth:`Color.from_string`.               |
    +------------------------------+------------------------------------------+
    | Three positional parameters  | Equivalent to calling                    |
    |                              | :meth:`Color.from_rgb` if all three      |
    |                              | parameters are between 0.0 and 1.0, or   |
    |                              | :meth:`Color.from_rgb_bytes` otherwise.  |
    +------------------------------+                                          |
    | Three named parameters:      |                                          |
    | *r*, *g*, *b*                |                                          |
    +------------------------------+                                          |
    | Three named parameters:      |                                          |
    | *red*, *green*, *blue*       |                                          |
    +------------------------------+------------------------------------------+
    | Three named parameters:      | Equivalent to calling                    |
    | *y*, *u*, *v*                | :meth:`Color.from_yuv` if *y* is between |
    |                              | 0.0 and 1.0, *u* is between -0.436 and   |
    |                              | 0.436, and *v* is between -0.615 and     |
    |                              | 0.615, or :meth:`Color.from_yuv_bytes`   |
    |                              | otherwise.                               |
    +------------------------------+------------------------------------------+
    | Three named parameters:      | Equivalent to calling                    |
    | *y*, *i*, *q*                | :meth:`Color.from_yiq`.                  |
    +------------------------------+------------------------------------------+
    | Three named parameters:      | Equivalent to calling                    |
    | *h*, *l*, *s*                | :meth:`Color.from_hls`.                  |
    +------------------------------+                                          |
    | Three named parameters:      |                                          |
    | *hue*, *lightness*,          |                                          |
    | *saturation*                 |                                          |
    +------------------------------+------------------------------------------+
    | Three named parameters:      | Equivalent to calling                    |
    | *h*, *s*, *v*                | :meth:`Color.from_hsv`                   |
    +------------------------------+                                          |
    | Three named parameters:      |                                          |
    | *hue*, *saturation*, *value* |                                          |
    +------------------------------+------------------------------------------+
    | Three named parameters:      | Equivalent to calling                    |
    | *x*, *y*, *z*                | :meth:`Color.from_cie_xyz`               |
    +------------------------------+------------------------------------------+
    | Three named parameters:      | Equivalent to calling                    |
    | *l*, *a*, *b*                | :meth:`Color.from_cie_lab`               |
    +------------------------------+------------------------------------------+
    | Three named parameters:      | Equivalent to calling                    |
    | *l*, *u*, *v*                | :meth:`Color.from_cie_luv`               |
    +------------------------------+------------------------------------------+

    If the constructor parameters do not conform to any of the variants in the
    table above, a :exc:`ValueError` will be thrown.

    Internally, the color is *always* represented as 3 float values
    corresponding to the red, green, and blue components of the color. These
    values take a value from 0.0 to 1.0 (least to full intensity). The class
    provides several attributes which can be used to convert one color system
    into another::

        >>> Color('#f00').hls
        (0.0, 0.5, 1.0)
        >>> Color.from_string('green').hue
        Hue(deg=120.0)
        >>> Color.from_rgb_bytes(0, 0, 255).yuv
        (0.114, 0.435912, -0.099978)

    As :class:`Color` derives from tuple, instances are immutable. While this
    provides the advantage that they can be used as keys in a dict, it does
    mean that colors themselves cannot be directly manipulated (e.g. by
    reducing the red component).

    However, several auxilliary classes in the module provide the ability to
    perform simple transformations of colors via operators which produce a new
    :class:`Color` instance. For example::

        >>> Color('red') - Red(0.5)
        <Color "#7f0000">
        >>> Color('green') + Red(0.5)
        <Color "#7f8000">
        >>> Color.from_hls(0.5, 0.5, 1.0)
        <Color "#00feff">
        >>> Color.from_hls(0.5, 0.5, 1.0) * Lightness(0.8)
        <Color "#00cbcc">
        >>> (Color.from_hls(0.5, 0.5, 1.0) * Lightness(0.8)).hls
        (0.5, 0.4, 1.0)

    From the last example above one can see that even attributes not directly
    stored by the color (such as lightness) can be manipulated in this fashion.
    In this case a :class:`Color` instance is constructed from HLS (hue,
    lightness, saturation) values with a lightness of 0.5. This is multiplied
    by a :class:`Lightness` instance with a value of 0.8 which constructs a new
    :class:`Color` with the same hue and saturation, but a lightness of 0.5 *
    0.8 = 0.4.

    If an instance is converted to a string (with :func:`str`) it will return a
    string containing the 7-character HTML code for the color (e.g. "#ff0000"
    for red). As can be seen in the examples above, a similar representation is
    returned for :func:`repr`.

    .. _RGB: https://en.wikipedia.org/wiki/RGB_color_space
    .. _Y'UV: https://en.wikipedia.org/wiki/YUV
    .. _Y'IQ: https://en.wikipedia.org/wiki/YIQ
    .. _HLS: https://en.wikipedia.org/wiki/HSL_and_HSV
    .. _HSV: https://en.wikipedia.org/wiki/HSL_and_HSV
    """

    def __new__(cls, *args, **kwargs):
        def from_rgb(r, g, b):
            if 0.0 <= r <= 1.0 and 0.0 <= g <= 1.0 and 0.0 <= b <= 1.0:
                return cls.from_rgb(r, g, b)
            else:
                return cls.from_rgb_bytes(r, g, b)

        def from_yuv(y, u, v):
            if 0.0 <= y <= 1.0 and -0.436 <= u <= 0.436 and -0.615 <= v <= 0.615:
                return cls.from_yuv(y, u, v)
            else:
                return cls.from_yuv_bytes(y, u, v)

        if kwargs:
            try:
                return {
                    frozenset('rgb'):   from_rgb,
                    frozenset('yuv'):   from_yuv,
                    frozenset('yiq'):   cls.from_yiq,
                    frozenset('hls'):   cls.from_hls,
                    frozenset('hsv'):   cls.from_hsv,
                    frozenset('xyz'):   cls.from_cie_xyz,
                    frozenset('lab'):   cls.from_cie_lab,
                    frozenset('luv'):   cls.from_cie_luv,
                    frozenset(('red', 'green', 'blue')):
                        lambda red, green, blue: from_rgb(red, green, blue),
                    frozenset(('hue', 'lightness', 'saturation')):
                        lambda hue, lightness, saturation: cls.from_hls(hue, lightness, saturation),
                    frozenset(('hue', 'saturation', 'value')):
                        lambda hue, saturation, value: cls.from_hsv(hue, saturation, value),
                    }[frozenset(kwargs.keys())](**kwargs)
            except KeyError:
                pass
        else:
            if len(args) == 1:
                return cls.from_string(args[0])
            elif len(args) == 3:
                return from_rgb(*args)
        raise ValueError('Unable to construct Color from provided arguments')

    @classmethod
    def from_string(cls, s):
        """
        Construct a :class:`Color` from a 4 or 7 character CSS-like
        representation (e.g. "#f00" or "#ff0000" for red), or from one of the
        named colors (e.g. "green" or "wheat") from the `CSS standard`_. Any
        other string format will result in a :exc:`ValueError`.

        .. _CSS standard: http://www.w3.org/TR/css3-color/#svg-color
        """
        if isinstance(s, bytes):
            s = s.decode('ascii')
        if s.startswith('#'):
            if len(s) == 7:
                return cls.from_rgb_bytes(
                    int(s[1:3], base=16),
                    int(s[3:5], base=16),
                    int(s[5:7], base=16)
                    )
            elif len(s) == 4:
                return cls.from_rgb_bytes(
                    int(s[1:2], base=16) * 0x11,
                    int(s[2:3], base=16) * 0x11,
                    int(s[3:4], base=16) * 0x11
                    )
            raise ValueError('Unrecognized color format "%s"' % s)
        try:
            return cls.from_string(NAMED_COLORS[s.lower()])
        except KeyError:
            raise ValueError('Unrecognized color name "%s"' % s)

    @classmethod
    def from_rgb(cls, r, g, b):
        """
        Construct a :class:`Color` from three `RGB`_ float values between 0.0
        and 1.0.
        """
        return super(Color, cls).__new__(cls, r, g, b)

    @classmethod
    def from_rgb_565(cls, n):
        """
        Construct a :class:`Color` from an unsigned 16-bit integer number
        in RGB565 format.
        """
        r = (n & 0xF800) / 0xF800
        g = (n & 0x07E0) / 0x07E0
        b = (n & 0x001F) / 0x001F
        return super(Color, cls).__new__(cls, r, g, b)

    @classmethod
    def from_rgb_bytes(cls, r, g, b):
        """
        Construct a :class:`Color` from three `RGB`_ byte values between 0 and
        255.
        """
        return super(Color, cls).__new__(cls, r / 255.0, g / 255.0, b / 255.0)

    @classmethod
    def from_yuv(cls, y, u, v):
        """
        Construct a :class:`Color` from three `Y'UV`_ float values. The Y value
        may be between 0.0 and 1.0. U may be between -0.436 and 0.436, while
        V may be between -0.615 and 0.615.
        """
        return super(Color, cls).__new__(
                cls,
                clamp_float(y + 1.14  * v),
                clamp_float(y - 0.395 * u - 0.581 * v),
                clamp_float(y + 2.033 * u),
                )

    @classmethod
    def from_yuv_bytes(cls, y, u, v):
        """
        Construct a :class:`Color` from three `Y'UV`_ byte values between 0 and
        255. The U and V values are biased by 128 to prevent negative values as
        is typical in video applications. The Y value is biased by 16 for the
        same purpose.
        """
        c = y - 16
        d = u - 128
        e = v - 128
        return cls.from_rgb_bytes(
                clamp_bytes((298 * c + 409 * e + 128) >> 8),
                clamp_bytes((298 * c - 100 * d - 208 * e + 128) >> 8),
                clamp_bytes((298 * c + 516 * d + 128) >> 8),
                )

    @classmethod
    def from_yiq(cls, y, i, q):
        """
        Construct a :class:`Color` from three `Y'IQ`_ float values. Y' can be
        between 0.0 and 1.0, while I and Q can be between -1.0 and 1.0.
        """
        return super(Color, cls).__new__(cls, *colorsys.yiq_to_rgb(y, i, q))

    @classmethod
    def from_hls(cls, h, l, s):
        """
        Construct a :class:`Color` from `HLS`_ (hue, lightness, saturation)
        floats between 0.0 and 1.0.
        """
        return super(Color, cls).__new__(cls, *colorsys.hls_to_rgb(h, l, s))

    @classmethod
    def from_hsv(cls, h, s, v):
        """
        Construct a :class:`Color` from `HSV`_ (hue, saturation, value) floats
        between 0.0 and 1.0.
        """
        return super(Color, cls).__new__(cls, *colorsys.hsv_to_rgb(h, s, v))

    @classmethod
    def from_cie_xyz(cls, x, y, z):
        """
        Construct a :class:`Color` from (X, Y, Z) float values representing
        a color in the `CIE 1931 color space`_. The conversion assumes the
        sRGB working space with reference white D65.

        .. _CIE 1931 color space: https://en.wikipedia.org/wiki/CIE_1931_color_space
        """
        m = matrix_mult(
            (( 3.2404542, -1.5371385, -0.4985314),
             (-0.9692660,  1.8760108,  0.0415560),
             ( 0.0556434, -0.2040259,  1.0572252),
             ),
            (x,
             y,
             z,
             ))
        return super(Color, cls).__new__(cls, *(to_srgb(c) for c in m))

    @classmethod
    def from_cie_lab(cls, l, a, b):
        """
        Construct a :class:`Color` from (L*, a*, b*) float values representing
        a color in the `CIE Lab color space`_. The conversion assumes the
        sRGB working space with reference white D65.

        .. _CIE Lab color space: https://en.wikipedia.org/wiki/Lab_color_space
        """
        theta = Fraction(6, 29)
        fy = (l + 16) / 116
        fx = fy + a / 500
        fz = fy - b / 200
        xyz = (
            n ** 3 if n > theta else 3 * theta ** 2 * (n - Fraction(4, 29))
            for n in (fx, fy, fz)
            )
        return cls.from_cie_xyz(*(n * m for n, m in zip(xyz, D65)))

    @classmethod
    def from_cie_luv(cls, l, u, v):
        """
        Construct a :class:`Color` from (L*, u*, v*) float values representing
        a color in the `CIE Luv color space`_. The conversion assumes the sRGB
        working space with reference white D65.

        .. _CIE Luv color space: https://en.wikipedia.org/wiki/CIELUV
        """
        uw = U(*D65)
        vw = V(*D65)
        u_p = u / (13 * l) + uw
        v_p = v / (13 * l) + vw
        y = D65[1] * (l * Fraction(3, 29) ** 3 if l <= 8 else ((l + 16) / 116) ** 3)
        x = y * (9 * u_p) / (4 * v_p)
        z = y * (12 - 3 * u_p - 20 * v_p) / (4 * v_p)
        return cls.from_cie_xyz(x, y, z)

    def __add__(self, other):
        if isinstance(other, Red):
            return Color(clamp_float(self.red + other), self.green, self.blue)
        elif isinstance(other, Green):
            return Color(self.red, clamp_float(self.green + other), self.blue)
        elif isinstance(other, Blue):
            return Color(self.red, self.green, clamp_float(self.blue + other))
        elif isinstance(other, Hue):
            h, l, s = self.hls
            return Color.from_hls((h + other) % 1.0, l, s)
        elif isinstance(other, Lightness):
            h, l, s = self.hls
            return Color.from_hls(h, clamp_float(l + other), s)
        elif isinstance(other, Saturation):
            h, l, s = self.hls
            return Color.from_hls(h, l, clamp_float(s + other))
        return NotImplemented

    def __radd__(self, other):
        # Addition is commutative
        if isinstance(other, (Red, Green, Blue, Hue, Lightness, Saturation)):
            return self.__add__(other)
        return NotImplemented

    def __sub__(self, other):
        if isinstance(other, Red):
            return Color(clamp_float(self.red - other), self.green, self.blue)
        elif isinstance(other, Green):
            return Color(self.red, clamp_float(self.green - other), self.blue)
        elif isinstance(other, Blue):
            return Color(self.red, self.green, clamp_float(self.blue - other))
        elif isinstance(other, Hue):
            h, l, s = self.hls
            return Color.from_hls((h - other) % 1.0, l, s)
        elif isinstance(other, Lightness):
            h, l, s = self.hls
            return Color.from_hls(h, clamp_float(l - other), s)
        elif isinstance(other, Saturation):
            h, l, s = self.hls
            return Color.from_hls(h, l, clamp_float(s - other))
        return NotImplemented

    def __rsub__(self, other):
        if isinstance(other, Red):
            return Color(clamp_float(other - self.red), self.green, self.blue)
        elif isinstance(other, Green):
            return Color(self.red, clamp_float(other - self.green), self.blue)
        elif isinstance(other, Blue):
            return Color(self.red, self.green, clamp_float(other - self.blue))
        elif isinstance(other, Hue):
            h, l, s = self.hls
            return Color.from_hls((other - h) % 1.0, l, s)
        elif isinstance(other, Lightness):
            h, l, s = self.hls
            return Color.from_hls(h, clamp_float(other - l), s)
        elif isinstance(other, Saturation):
            h, l, s = self.hls
            return Color.from_hls(h, l, clamp_float(other - s))
        return NotImplemented

    def __mul__(self, other):
        if isinstance(other, Red):
            return Color(clamp_float(self.red * other), self.green, self.blue)
        elif isinstance(other, Green):
            return Color(self.red, clamp_float(self.green * other), self.blue)
        elif isinstance(other, Blue):
            return Color(self.red, self.green, clamp_float(self.blue * other))
        elif isinstance(other, Hue):
            h, l, s = self.hls
            return Color.from_hls((h * other) % 1.0, l, s)
        elif isinstance(other, Lightness):
            h, l, s = self.hls
            return Color.from_hls(h, clamp_float(l * other), s)
        elif isinstance(other, Saturation):
            h, l, s = self.hls
            return Color.from_hls(h, l, clamp_float(s * other))
        return NotImplemented

    def __rmul__(self, other):
        # Multiplication is commutative
        if isinstance(other, (Red, Green, Blue, Hue, Lightness, Saturation)):
            return self.__mul__(other)

    def __str__(self):
        return '#%02x%02x%02x' % self.rgb_bytes

    def __repr__(self):
        return '<Color "%s">' % str(self)

    @property
    def rgb(self):
        """
        Returns a 3-tuple of (red, green, blue) float values (between 0.0 and
        1.0).
        """
        return (self.red, self.green, self.blue)

    @property
    def rgb_565(self):
        """
        Returns an unsigned 16-bit integer number representing the color in
        the RGB565 encoding.
        """
        return (
                (int(self.red   * 0xF800) & 0xF800) |
                (int(self.green * 0x07E0) & 0x07E0) |
                (int(self.blue  * 0x001F) & 0x001F))

    @property
    def rgb_bytes(self):
        """
        Returns a 3-tuple of (red, green, blue) byte values.
        """
        return (
                int(self.red * 255),
                int(self.green * 255),
                int(self.blue * 255),
                )

    @property
    def yuv(self):
        """
        Returns a 3-tuple of (y, u, v) float values; y values can be between
        0.0 and 1.0, u values are between -0.436 and 0.436, and v values are
        between -0.615 and 0.615.
        """
        r, g, b = self.rgb
        y = 0.299 * r + 0.587 * g + 0.114 * b
        return (
                y,
                0.492 * (b - y),
                0.877 * (r - y),
                )

    @property
    def yuv_bytes(self):
        """
        Returns a 3-tuple of (y, u, v) byte values. Y values are biased by 16
        in the result to prevent negatives. U and V values are biased by 128
        for the same purpose.
        """
        r, g, b = self.rgb_bytes
        return (
                (( 66 * r + 129 * g +  25 * b + 128) >> 8) + 16,
                ((-38 * r -  73 * g + 112 * b + 128) >> 8) + 128,
                ((112 * r -  94 * g -  18 * b + 128) >> 8) + 128,
                )

    @property
    def yiq(self):
        """
        Returns a 3-tuple of (y, i, q) float values; y values can be between
        0.0 and 1.0, whilst i and q values can be between -1.0 and 1.0.
        """
        return colorsys.rgb_to_yiq(self.red, self.green, self.blue)

    @property
    def cie_xyz(self):
        """
        Returns a 3-tuple of (X, Y, Z) float values representing the color in
        the `CIE 1931 color space`_. The conversion assumes the sRGB working
        space, with reference white D65.

        .. _CIE 1931 color space: https://en.wikipedia.org/wiki/CIE_1931_color_space
        """
        return tuple(matrix_mult(
            ((0.4124564, 0.3575761, 0.1804375),
             (0.2126729, 0.7151522, 0.0721750),
             (0.0193339, 0.1191920, 0.9503041),
             ),
            (from_srgb(self.red),
             from_srgb(self.green),
             from_srgb(self.blue)
             )
             ))

    @property
    def cie_lab(self):
        """
        Returns a 3-tuple of (L*, a*, b*) float values representing the color
        in the `CIE Lab color space`_ with the `D65 standard illuminant`_.

        .. _CIE Lab color space: https://en.wikipedia.org/wiki/Lab_color_space
        .. _D65 standard illuminant: https://en.wikipedia.org/wiki/Illuminant_D65
        """
        K = Fraction(1, 3) * Fraction(29, 6) ** 2
        e = Fraction(6, 29) ** 3
        x, y, z = (n / m for n, m in zip(self.cie_xyz, D65))
        fx, fy, fz = (
            n ** Fraction(1, 3) if n > e else K * n + Fraction(4, 29)
            for n in (x, y, z)
            )
        return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))

    @property
    def cie_luv(self):
        """
        Returns a 3-tuple of (L*, u*, v*) float values representing the color
        in the `CIE Luv color space`_ with the `D65 standard illuminant`_.

        .. _CIE Luv color space: https://en.wikipedia.org/wiki/CIELUV
        """
        K = Fraction(29, 3) ** 3
        e = Fraction(6, 29) ** 3
        XYZ = self.cie_xyz
        yr = XYZ[1] / D65[1]
        L = 116 * yr ** Fraction(1, 3) - 16 if yr > e else K * yr
        u = 13 * L * (U(*XYZ) - U(*D65))
        v = 13 * L * (V(*XYZ) - V(*D65))
        return (L, u, v)

    @property
    def hls(self):
        """
        Returns a 3-tuple of (hue, lightness, saturation) float values (between
        0.0 and 1.0).
        """
        return colorsys.rgb_to_hls(self.red, self.green, self.blue)

    @property
    def hsv(self):
        """
        Returns a 3-tuple of (hue, saturation, value) float values (between 0.0
        and 1.0).
        """
        return colorsys.rgb_to_hsv(self.red, self.green, self.blue)

    @property
    def red(self):
        """
        Returns the red component of the color as a :class:`Red` instance which
        can be used in operations with other :class:`Color` instances.
        """
        # super() calls needed here to avoid recursion
        return Red(super(Color, self).red)

    @property
    def green(self):
        """
        Returns the green component of the color as a :class:`Green` instance
        which can be used in operations with other :class:`Color` instances.
        """
        return Green(super(Color, self).green)

    @property
    def blue(self):
        """
        Returns the blue component of the color as a :class:`Blue` instance
        which can be used in operations with other :class:`Color` instances.
        """
        return Blue(super(Color, self).blue)

    @property
    def hue(self):
        """
        Returns the hue of the color as a :class:`Hue` instance which can be
        used in operations with other :class:`Color` instances.
        """
        return Hue(self.hls[0])

    @property
    def lightness(self):
        """
        Returns the lightness of the color as a :class:`Lightness` instance
        which can be used in operations with other :class:`Color` instances.
        """
        return Lightness(self.hls[1])

    @property
    def saturation(self):
        """
        Returns the saturation of the color as a :class:`Saturation` instance
        which can be used in operations with other :class:`Color` instances.
        """
        return Saturation(self.hls[2])

    def difference(self, other, method='euclid'):
        """
        Determines the difference between this color and *other* using the
        specified *method*. The *method* is specified as a string, and the
        following methods are valid:

        * 'euclid' - This is the default method. Calculate the `Euclidian
          distance`_. This is by far the fastest method, but also the least
          accurate in terms of human perception.
        * 'cie1976' - Use the `CIE 1976`_ formula for calculating the
          difference between two colors in CIE Lab space.
        * 'cie1994g' - Use the `CIE 1994`_ formula with the "graphic arts" bias
          for calculating the difference.
        * 'cie1994t' - Use the `CIE 1994`_ forumula with the "textiles" bias
          for calculating the difference.
        * 'cie2000' - Use the `CIEDE 2000`_ formula for calculating the
          difference.

        Note that the Euclidian distance will be significantly different to the
        other calculations; effectively this just measures the distance between
        the two colors by treating them as coordinates in a three dimensional
        Euclidian space. All other methods are means of calculating a `Delta
        E`_ value in which 2.3 is considered a `just-noticeable difference`_
        (JND).

        .. warning::

            This implementation has yet to receive any significant testing
            (constructor methods for CIELab need to be added before this can be
            done).

        .. _Delta E: https://en.wikipedia.org/wiki/Color_difference
        .. _just-noticeable difference: https://en.wikipedia.org/wiki/Just-noticeable_difference
        .. _Euclidian distance: https://en.wikipedia.org/wiki/Euclidean_distance
        .. _CIE 1976: https://en.wikipedia.org/wiki/Color_difference#CIE76
        .. _CIE 1994: https://en.wikipedia.org/wiki/Color_difference#CIE94
        .. _CIEDE 2000: https://en.wikipedia.org/wiki/Color_difference#CIEDE2000
        """
        if isinstance(method, bytes):
            method = method.decode('ascii')
        if method == 'euclid':
            return sqrt(sum((Cs - Co) ** 2 for Cs, Co in zip(self, other)))
        elif method == 'cie1976':
            return self._cie1976(other)
        elif method.startswith('cie1994'):
            return self._cie1994(other, method)
        elif method == 'ciede2000':
            return self._ciede2000(other)
        else:
            raise ValueError('invalid method: %s' % method)

    def _cie1976(self, other):
        return sqrt(sum((Cs - Co) ** 2 for Cs, Co in zip(self.cie_lab, other.cie_lab)))

    def _cie1994(self, other, method):
        L1, a1, b1 = self.cie_lab
        L2, a2, b2 = other.cie_lab
        dL = L1 - L2
        C1 = sqrt(a1 ** 2 + b1 ** 2)
        C2 = sqrt(a2 ** 2 + b2 ** 2)
        dC = C1 - C2
        # Don't bother with the sqrt here as due to limited float precision
        # we can wind up with a domain error (because the value is ever so
        # slightly negative - try it with black'n'white for an example)
        dH2 = (a1 - a2) ** 2 + (b1 - b2) ** 2 - dC ** 2
        kL, K1, K2 = {
            'cie1994g': (1, 0.045, 0.015),
            'cie1994t': (2, 0.048, 0.014),
            }[method]
        SC = 1 + K1 * C1
        SH = 1 + K2 * C1
        return sqrt((dL ** 2 / kL) + (dC ** 2 / SC) + (dH2 / SH))

    def _ciede2000(self, other):
        L1, a1, b1 = self.cie_lab
        L2, a2, b2 = other.cie_lab
        L_ = (L1 + L2) / 2
        dL = L2 - L1
        C1 = sqrt(a1 ** 2 + b1 ** 2)
        C2 = sqrt(a1 ** 2 + b1 ** 2)
        C_ = (C1 + C2) / 2
        dC = C2 - C1
        G = (1 - sqrt(C_ ** 7 / (C_ ** 7 + 25 ** 7))) / 2
        a1 = (1 + G) * a1
        a2 = (1 + G) * a2
        h1 = 0.0 if b1 == a1 == 0 else degrees(atan2(b1, a1)) % 360
        h2 = 0.0 if b2 == a2 == 0 else degrees(atan2(b2, a2)) % 360
        if C1 * C2 == 0.0:
            dh = 0.0
            h_ = h1 + h2
        elif abs(h1 - h2) <= 180:
            dh = h2 - h1
            h_ = (h1 + h2) / 2
        else:
            if h2 <= h1:
                dh = h2 - h1 + 360
            else:
                dh = h2 - h1 - 360
            if h1 + h2 >= 360:
                h_ = (h1 + h2 + 360) / 2
            else:
                h_ = (h1 + h2 - 360) / 2
        dH = 2 * sqrt(C1 * C2) * sin(radians(dh / 2))
        T = (
                1 -
                0.17 * cos(radians(h_ - 30)) +
                0.24 * cos(radians(2 * h_)) +
                0.32 * cos(radians(3 * h_ + 6)) -
                0.20 * cos(radians(4 * h_ - 63))
                )
        SL = 1 + (0.015 * (L_ - 50) ** 2) / sqrt(20 + (L_ - 50) ** 2)
        SC = 1 + 0.045 * C_
        SH = 1 + 0.015 * C_ * T
        RT = -2 * sqrt(C_ ** 7 / (C_ ** 7 + 25 ** 7)) * sin(radians(60 * exp(-(((h_ - 275) / 25) ** 2))))
        return sqrt((dL / SL) ** 2 + (dC / SC) ** 2 + (dH / SH) ** 2 + RT * (dC / SC) * (dH / SH))

