#!/usr/bin/env python3
# vim: set et sw=4 sts=4 fileencoding=utf-8:
#
# Python camera library for the Rasperry-Pi camera module
# Copyright (c) 2013-2018 Dave Jones <dave@waveform.org.uk>
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

import sys
import os
from datetime import datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
on_rtd = os.environ.get('READTHEDOCS', None) == 'True'
import setup as _setup

# Mock out certain modules while building documentation
class Mock(object):
    __all__ = []

    def __init__(self, *args, **kw):
        pass

    def __call__(self, *args, **kw):
        return Mock()

    def __mul__(self, other):
        return Mock()

    def __and__(self, other):
        return Mock()

    def __bool__(self):
        return False

    def __nonzero__(self):
        return False

    @classmethod
    def __getattr__(cls, name):
        if name in ('__file__', '__path__'):
            return '/dev/null'
        else:
            return Mock()

sys.modules['ctypes'] = Mock()
sys.modules['numpy'] = Mock()
sys.modules['numpy.lib'] = sys.modules['numpy'].lib
sys.modules['numpy.lib.stride_tricks'] = sys.modules['numpy'].lib.stride_tricks

# -- General configuration ------------------------------------------------

extensions = ['sphinx.ext.autodoc', 'sphinx.ext.viewcode', 'sphinx.ext.intersphinx']
if on_rtd:
    needs_sphinx = '1.4.0'
    extensions.append('sphinx.ext.imgmath')
    imgmath_image_format = 'svg'
    tags.add('rtd')
else:
    extensions.append('sphinx.ext.mathjax')
    mathjax_path = '/usr/share/javascript/mathjax/MathJax.js?config=TeX-AMS_HTML'

templates_path = ['_templates']
source_suffix = '.rst'
#source_encoding = 'utf-8-sig'
master_doc = 'index'
project = _setup.__project__.title()
copyright = '2013-%s %s' % (datetime.now().year, _setup.__author__)
version = _setup.__version__
release = _setup.__version__
#language = None
#today_fmt = '%B %d, %Y'
exclude_patterns = ['_build']
highlight_language = 'python3'
#default_role = None
#add_function_parentheses = True
#add_module_names = True
#show_authors = False
pygments_style = 'sphinx'
#modindex_common_prefix = []
#keep_warnings = False

# -- Autodoc configuration ------------------------------------------------

autodoc_member_order = 'groupwise'
autodoc_default_flags = ['members']

# -- Intersphinx configuration --------------------------------------------

intersphinx_mapping = {
    'python': ('https://docs.python.org/3.5', None),
    'numpy':  ('https://docs.scipy.org/doc/numpy/', None),
    'colorzero': ('https://colorzero.readthedocs.io/en/latest/', None),
}

# -- Options for HTML output ----------------------------------------------

if on_rtd:
    html_theme = 'sphinx_rtd_theme'
    pygments_style = 'default'
    #html_theme_options = {}
    #html_sidebars = {}
else:
    html_theme = 'default'
    #html_theme_options = {}
    #html_sidebars = {}
html_title = '%s %s Documentation' % (project, version)
#html_theme_path = []
#html_short_title = None
#html_logo = None
#html_favicon = None
html_static_path = ['_static']
#html_extra_path = []
#html_last_updated_fmt = '%b %d, %Y'
#html_use_smartypants = True
#html_additional_pages = {}
#html_domain_indices = True
#html_use_index = True
#html_split_index = False
#html_show_sourcelink = True
#html_show_sphinx = True
#html_show_copyright = True
#html_use_opensearch = ''
#html_file_suffix = None
htmlhelp_basename = '%sdoc' % _setup.__project__

# Hack to make wide tables work properly in RTD
# See https://github.com/snide/sphinx_rtd_theme/issues/117 for details
def setup(app):
    app.add_stylesheet('style_override.css')

# -- Options for LaTeX output ---------------------------------------------

#latex_engine = 'pdflatex'

latex_elements = {
    'papersize': 'a4paper',
    'pointsize': '10pt',
    'preamble': r'\def\thempfootnote{\arabic{mpfootnote}}', # workaround sphinx issue #2530
}

latex_documents = [
    (
        'index',                       # source start file
        '%s.tex' % _setup.__project__, # target filename
        '%s %s Documentation' % (project, version), # title
        _setup.__author__,             # author
        'manual',                      # documentclass
        True,                          # documents ref'd from toctree only
    ),
]

#latex_logo = None
#latex_use_parts = False
latex_show_pagerefs = True
latex_show_urls = 'footnote'
#latex_appendices = []
#latex_domain_indices = True

# -- Options for epub output ----------------------------------------------

epub_basename = _setup.__project__
#epub_theme = 'epub'
#epub_title = html_title
epub_author = _setup.__author__
epub_identifier = 'https://picamera.readthedocs.io/'
#epub_tocdepth = 3
epub_show_urls = 'no'
#epub_use_index = True

# -- Options for manual page output ---------------------------------------

man_pages = []

man_show_urls = True

# -- Options for Texinfo output -------------------------------------------

texinfo_documents = []

#texinfo_appendices = []
#texinfo_domain_indices = True
#texinfo_show_urls = 'footnote'
#texinfo_no_detailmenu = False

# -- Options for linkcheck builder ----------------------------------------

linkcheck_retries = 3
linkcheck_workers = 20
linkcheck_anchors = True
