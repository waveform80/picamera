#!/usr/bin/env python3
# vim: set et sw=4 sts=4 fileencoding=utf-8:
#
# Python camera library for the Rasperry-Pi camera module
# Copyright (c) 2013-2016 Dave Jones <dave@waveform.org.uk>
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

needs_sphinx = '1.4.0'
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.viewcode', 'sphinx.ext.intersphinx', 'sphinx.ext.imgmath']
templates_path = ['_templates']
source_suffix = '.rst'
#source_encoding = 'utf-8-sig'
master_doc = 'index'
project = _setup.__project__.title()
copyright = '2013-2016 %s' % _setup.__author__
version = _setup.__version__
release = _setup.__version__
#language = None
#today_fmt = '%B %d, %Y'
exclude_patterns = ['_build']
#default_role = None
#add_function_parentheses = True
#add_module_names = True
#show_authors = False
pygments_style = 'sphinx'
#modindex_common_prefix = []
#keep_warnings = False
imgmath_image_format = 'svg'

# -- Autodoc configuration ------------------------------------------------

autodoc_member_order = 'groupwise'
autodoc_default_flags = ['members']

# -- Intersphinx configuration --------------------------------------------

intersphinx_mapping = {
    'python': ('https://docs.python.org/3.4', None),
    'numpy':  ('https://docs.scipy.org/doc/numpy/', None),
    }

# -- Options for HTML output ----------------------------------------------

if on_rtd:
    html_theme = 'sphinx_rtd_theme'
    #html_theme_options = {}
    #html_theme_path = []
    #html_sidebars = {}
else:
    html_theme = 'default'
    #html_theme_options = {}
    #html_theme_path = []
    #html_sidebars = {}
#html_title = None
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

latex_elements = {
    'papersize': 'a4paper',
    'pointsize': '10pt',
    #'preamble': '',
}

latex_documents = [
    (
        'index',                       # source start file
        '%s.tex' % _setup.__project__, # target filename
        '%s Documentation' % project,  # title
        _setup.__author__,             # author
        'manual',                      # documentclass
        ),
]

#latex_logo = None
#latex_use_parts = False
#latex_show_pagerefs = False
#latex_show_urls = False
#latex_appendices = []
#latex_domain_indices = True

# -- Options for manual page output ---------------------------------------

man_pages = []

#man_show_urls = False

# -- Options for Texinfo output -------------------------------------------

texinfo_documents = []

#texinfo_appendices = []
#texinfo_domain_indices = True
#texinfo_show_urls = 'footnote'
#texinfo_no_detailmenu = False
