
#
# Copyright (C) 2022 The University of Sydney, Australia
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License, version 2, as published by
# the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#

# If 'importlib_resources' installed then use that, otherwise use standard library 'importlib.resources'.
#
# Support for accessing *namespace* packages only added in Python 3.10 (to 'importlib.resources').
# For Python <3.10 must instead use (and install) backport PyPI package 'importlib_resources'.
try:
    import importlib_resources as resources
except:
    from importlib import resources
from pathlib import Path
import shutil


def install(
        dest_path="./pybacktrack_supplementary"):
    """Install supplementary scripts in the given location.

    Supplementary scripts are pre/post processing, conversion and test scripts that are not necessary for running the pyBacktrack module.

    WARNING: If the path exists, the example data files will be written into the path
    and will overwrite any existing files with which they collide. The default path
    is chosen to make collision less likely / problematic.
    """

    # Copy the supplementary.
    with resources.path('pybacktrack', 'supplementary') as src_path:
        # Copy source to destination.
        #
        # Note: Python 3.8 added the 'dirs_exist_ok' argument to 'shutil.copytree()' which, when True,
        #       will just overwrite a directory that exists instead of raising an exception.
        #       This makes 'shutil.copytree()' equivalent to 'distutils.dir_util.copy_tree'
        #       (where 'distutils' was in the Python standard library but was removed in Python 3.12).
        shutil.copytree(src_path, dest_path, dirs_exist_ok=True)
