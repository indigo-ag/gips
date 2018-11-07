#!/usr/bin/env python
################################################################################
#    GIPS: Geospatial Image Processing System
#
#    AUTHOR: Matthew Hanson
#    EMAIL:  matt.a.hanson@gmail.com
#
#    Copyright (C) 2014 Applied Geosolutions
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program. If not, see <http://www.gnu.org/licenses/>
################################################################################

"""
setup for GIPS
"""

import os
from setuptools import setup, find_packages
import shutil
import glob
import traceback
import imp

__version__ = imp.load_source('gips.version', 'gips/version.py').__version__

# collect console scripts to install
console_scripts = []
for f in glob.glob('gips/scripts/*.py'):
    try:
        name = os.path.splitext(os.path.basename(f))[0]
        if name not in ['__init__', 'core']:
            script = 'gips_%s = gips.scripts.%s:main' % (name, name.lower())
            console_scripts.append(script)
    except:
        print traceback.format_exc()


setup(
    name='gips',
    version=__version__,
    description='Geospatial Image Processing System',
    author='Matthew Hanson',
    author_email='matt.a.hanson@gmail.com',
    packages=find_packages(),
    package_data={
        '': ['*.shp', '*.prj', '*.shx', '*.dbf', '*.csv'],
        'gips': [
            'acolite.cfg',
            'data/landsat/input_file_tmp.inp',
            'data/landsat/lndortho.cps_par.ini',
        ],
    },
    install_requires=[
        'six>=1.9.0',
        'requests',
        'django==1.10',
        'netCDF4',
        'boto3<=1.5', # last tested on 1.4.x series; optional: only needed for S3 fetches
        'pyproj',
        'Py6S>=1.7.0',
        'shapely',
        'gippy>=0.3.11,<0.4',
        'homura==0.1.3',
        'python-dateutil',
        'pydap==3.2',
        'pysolar==0.6',
        'dbfread==2.0.7',
        'rios==1.4.3',
        'python-fmask==0.4.5',
        'usgs', # 0.2.1 known to work
        'backports.functools_lru_cache',
    ],
    dependency_links=[
        'https://bitbucket.org/chchrsc/rios/downloads/rios-1.4.3.zip#egg=rios-1.4.3',
        'https://bitbucket.org/chchrsc/python-fmask/downloads/python-fmask-0.4.5.zip#egg=python-fmask-0.4.5',
        'https://github.com/Applied-GeoSolutions/gippy/archive/v0.3.11.tar.gz#egg=gippy-0.3.11',
    ],
    entry_points={'console_scripts': console_scripts},
    zip_safe=False,
)
