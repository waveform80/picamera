# vim: set noet sw=4 ts=4 fileencoding=utf-8:

# External utilities
PYTHON=python
PYFLAGS=
DEST_DIR=/

# Horrid hack to ensure setuptools is installed in our python environment. This
# is necessary with Python 3.3's venvs which don't install it by default.
ifeq ($(shell python -c "import setuptools" 2>&1),)
SETUPTOOLS:=
else
SETUPTOOLS:=$(shell wget https://bitbucket.org/pypa/setuptools/raw/bootstrap/ez_setup.py -O - | $(PYTHON))
endif

# Calculate the base names of the distribution, the location of all source,
# documentation, packaging, icon, and executable script files
NAME:=$(shell $(PYTHON) $(PYFLAGS) setup.py --name)
VER:=$(shell $(PYTHON) $(PYFLAGS) setup.py --version)
PYVER:=$(shell $(PYTHON) $(PYFLAGS) -c "import sys; print('py%d.%d' % sys.version_info[:2])")
PY_SOURCES:=$(shell \
	$(PYTHON) $(PYFLAGS) setup.py egg_info >/dev/null 2>&1 && \
	cat $(NAME).egg-info/SOURCES.txt)
DEB_SOURCES:=debian/changelog \
	debian/control \
	debian/copyright \
	debian/rules
DOC_SOURCES:=$(wildcard docs/*.rst)

# Calculate the name of all outputs
DIST_EGG=dist/$(NAME)-$(VER)-$(PYVER).egg
DIST_TAR=dist/$(NAME)-$(VER).tar.gz
DIST_ZIP=dist/$(NAME)-$(VER).zip
DIST_DEB=dist/python-$(NAME)_$(VER)-1_armhf.deb dist/python3-$(NAME)_$(VER)-1_armhf.deb dist/python-$(NAME)-docs_$(VER)-1_all.deb
DIST_DSC=dist/$(NAME)_$(VER).orig.tar.gz dist/$(NAME)_$(VER)-1.dsc dist/$(NAME)_$(VER)-1_source.changes


# Default target
all:
	@echo "make install - Install on local system"
	@echo "make develop - Install symlinks for development"
	@echo "make test - Run tests"
	@echo "make doc - Generate HTML and PDF documentation"
	@echo "make source - Create source package"
	@echo "make egg - Generate a PyPI egg package"
	@echo "make zip - Generate a source zip package"
	@echo "make tar - Generate a source tar package"
	@echo "make deb - Generate Debian packages"
	@echo "make dist - Generate all packages"
	@echo "make clean - Get rid of all generated files"
	@echo "make release - Create and tag a new release"
	@echo "make upload - Upload the new release to repositories"

install:
	$(PYTHON) $(PYFLAGS) setup.py install --root $(DEST_DIR)

doc: $(DOC_SOURCES)
	$(PYTHON) $(PYFLAGS) setup.py build_sphinx -b html

source: $(DIST_TAR) $(DIST_ZIP)

egg: $(DIST_EGG)

zip: $(DIST_ZIP)

tar: $(DIST_TAR)

deb: $(DIST_DEB) $(DIST_DSC)

dist: $(DIST_EGG) $(DIST_DEB) $(DIST_DSC) $(DIST_TAR) $(DIST_ZIP)

develop: tags
	$(PYTHON) $(PYFLAGS) setup.py develop

test:
	$(PYTHON) $(PYFLAGS) setup.py test

clean:
	$(PYTHON) $(PYFLAGS) setup.py clean
	$(MAKE) -f $(CURDIR)/debian/rules clean
	rm -fr build/ dist/ $(NAME).egg-info/ tags
	find $(CURDIR) -name "*.pyc" -delete

tags: $(PY_SOURCES)
	ctags -R --exclude="build/*" --exclude="debian/*" --exclude="docs/*" --languages="Python"

$(DIST_TAR): $(PY_SOURCES)
	$(PYTHON) $(PYFLAGS) setup.py sdist --formats gztar

$(DIST_ZIP): $(PY_SOURCES)
	$(PYTHON) $(PYFLAGS) setup.py sdist --formats zip

$(DIST_EGG): $(PY_SOURCES)
	$(PYTHON) $(PYFLAGS) setup.py bdist_egg

$(DIST_DEB): $(PY_SOURCES) $(DEB_SOURCES)
	# build the source package in the parent directory then rename it to
	# project_version.orig.tar.gz
	$(PYTHON) $(PYFLAGS) setup.py sdist --dist-dir=../
	rename -f 's/$(NAME)-(.*)\.tar\.gz/$(NAME)_$$1\.orig\.tar\.gz/' ../*
	debuild -b -i -I -Idist -Ibuild -Ihtmlcov -I__pycache__ -I.coverage -Itags -I*.pyc -I.*xcf -rfakeroot
	mkdir -p dist/
	cp ../python-$(NAME)_$(VER)-1_armhf.deb dist/
	cp ../python3-$(NAME)_$(VER)-1_armhf.deb dist/
	cp ../python-$(NAME)-docs_$(VER)-1_all.deb dist/

$(DIST_DSC): $(PY_SOURCES) $(DEB_SOURCES)
	# build the source package in the parent directory then rename it to
	# project_version.orig.tar.gz
	$(PYTHON) $(PYFLAGS) setup.py sdist --dist-dir=../
	rename -f 's/$(NAME)-(.*)\.tar\.gz/$(NAME)_$$1\.orig\.tar\.gz/' ../*
	debuild -S -i -I -Idist -Ibuild -Ihtmlcov -I__pycache__ -I.coverage -Itags -I*.pyc -I.*xcf -rfakeroot
	mkdir -p dist/
	cp ../$(NAME)_$(VER)-1_source.changes dist/
	cp ../$(NAME)_$(VER)-1.dsc dist/
	cp ../$(NAME)_$(VER)-1.tar.gz dist/

release: $(PY_SOURCES) $(DOC_SOURCES)
	$(MAKE) clean
	# ensure there are no current uncommitted changes
	test -z "$(shell git status --porcelain)"
	# commit the changes and add a new tag
	git tag -s release-$(VER) -m "Release $(VER)"
	# update the package's registration on PyPI (in case any metadata's changed)
	$(PYTHON) $(PYFLAGS) setup.py register

upload: $(PY_SOURCES) $(DOC_SOURCES) $(DIST_DEB) $(DIST_DSC)
	# build a source archive and upload to PyPI
	$(PYTHON) $(PYFLAGS) setup.py sdist upload
	./maildebs.py $(DIST_DEB) $(DIST_DSC)

.PHONY: all install develop test doc source egg zip tar dist clean tags release upload

