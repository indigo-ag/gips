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

"""Daymet driver module; see https://daymet.ornl.gov/

Daymet is an unusual GIPS driver in that its assets are also its
products. During fetch, files are constructed out of data downloaded in
non-file format (via opendap). These files are then available as both
assets and products simultaneously.
"""

import os
import datetime
import time
import numpy as np
import re

from pydap.client import open_url

import gippy
from gips.data.core import Repository, Asset, Data
from gips.utils import VerboseOut, basename
from gips import utils

requirements =['pydap']

PROJ = """PROJCS["unnamed",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433],AUTHORITY["EPSG","4326"]],PROJECTION["Lambert_Conformal_Conic_2SP"],PARAMETER["standard_parallel_1",25],PARAMETER["standard_parallel_2",60],PARAMETER["latitude_of_origin",42.5],PARAMETER["central_meridian",-100],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]]]"""

# Cyanomap: tmax, tmin, tmean, ppt, solar rad, and vapor pressure

# maximum temperature (C) - tmax.nc *
# minimum temperature (C) - tmin.nc  *
# precipitation (mm day-1) - prcp.nc *
# shortwave radiation (W m-2) - srad.nc *
# vapor pressure (Pa) - vp.nc *
# snow-water equivalent (kg m-2) - swe.nc
# daylength (sec day-1) - dayl.nc


def create_datatype(np_dtype):
    """ provide translation between data type codes """
    gippy.GDT_UInt8 = gippy.GDT_Byte
    np_dtype = str(np_dtype)
    typestr = 'gippy.GDT_' + np_dtype.title().replace('Ui', 'UI')
    g_dtype = eval(typestr)
    return g_dtype

class daymetRepository(Repository):
    name = 'Daymet'
    description = 'Daymet weather data'


class daymetAsset(Asset):
    Repository = daymetRepository

    _sensors = {
        'daymet': {
            'description': 'Daily surface weather and climatological summaries',
        }
    }

    _sensor = 'daymet' # only one in the driver

    _latency = 0
    _startdate = datetime.date(1980, 1, 1)
    _url = "https://thredds.daac.ornl.gov/thredds/dodsC/ornldaac/1328/tiles/%d/%s_%d"

    # daymet assets are named just like products: tile_date_sensor_asset/product.tif
    _asset_template = '{}_{}_{}_{}.tif' # for generating filenames
    # for validating and parsing filenames - doubling of {} is due to format() -----vv
    _asset_re = r'^(?P<tile>\d{{5}})_(?P<date>\d{{7}})_' + _sensor + r'_(?P<ap_type>{})\.tif$'

    _assets = {
        'tmin': {
            'description': 'Daily minimum air temperature (C)',
            'pattern': _asset_re.format('tmin'),
            'source': 'tmin.nc',
            'url': _url,
            'startdate': _startdate,
            'latency': _latency,
        },
        'tmax': {
            'description': 'Daily maximum air temperature (C)',
            'pattern': _asset_re.format('tmax'),
            'source': 'tmax.nc',
            'url': _url,
            'startdate': _startdate,
            'latency': _latency,
        },
        'prcp': {
            'description': 'Daily precipitation (mm)',
            'pattern': _asset_re.format('prcp'),
            'source': 'prcp.nc',
            'url': _url,
            'startdate': _startdate,
            'latency': _latency,
        },
        'srad': {
            'description': 'Daily solar radiation (W m-2)',
            'pattern': _asset_re.format('srad'),
            'source': 'srad.nc',
            'url': _url,
            'startdate': _startdate,
            'latency': _latency,
        },
        'vp': {
            'description': 'Daily vapor pressure (Pa)',
            'pattern': _asset_re.format('vp'),
            'source': 'vp.nc',
            'url': _url,
            'startdate': _startdate,
            'latency': _latency,
        },
    }

    _defaultresolution = (1000., 1000.,)

    def parse_asset_fp(self):
        """Parse self.filename using the class's asset patterns.

        On the first successful match, the re lib match object is
        returned. Raises ValueError on failure to parse.
        """
        # this method may be useful in core.Asset
        asset_bn = os.path.basename(self.filename)
        for av in self._assets.values():
            match = re.match(av['pattern'], asset_bn)
            if match is not None:
                return match
        raise ValueError("Unparseable asset file name:  " + self.filename)

    def __init__(self, filename):
        """Uses regexes above to parse filename & save metadata."""
        super(daymetAsset, self).__init__(filename)
        self.tile, date_str, self.asset = (
            self.parse_asset_fp().group('tile', 'date', 'ap_type'))
        self.date = datetime.datetime.strptime(date_str, '%Y%j').date()
        self.sensor = self._sensor
        # how daymet products load magically
        self.products[self.asset] = filename


    @classmethod
    def fetch(cls, asset, tile, date):
        """ Get this asset for this tile and date (using OpenDap service) """
        url = cls._assets[asset].get('url', '') % (date.year, tile, date.year)
        source = cls._assets[asset]['source'] 
        loc = "%s/%s" % (url, source)
        utils.verbose_out(loc)
        dataset = open_url(loc)
        x0 = dataset['x'].data[0] - 500.0
        y0 = dataset['y'].data[0] + 500.0
        day = date.timetuple().tm_yday
        iday = day - 1
        var = dataset[asset]
        data = np.array(var.array[iday, :, :]).squeeze().astype('float32')
        ysz, xsz = data.shape
        description = cls._assets[asset]['description']
        meta = {'ASSET': asset, 'TILE': tile, 'DATE': str(date.date()), 'DESCRIPTION': description}
        sday = str(day).zfill(3)
        geo = [float(x0), cls._defaultresolution[0], 0.0,
               float(y0), 0.0, -cls._defaultresolution[1]]
        geo = np.array(geo).astype('double')
        dtype = create_datatype(data.dtype)
        date_str = date.strftime(cls.Repository._datedir)
        filename = cls._asset_template.format(tile, date_str, cls._sensor, asset)
        stage_dir = cls.Repository.path('stage')
        with utils.make_temp_dir(prefix='fetch', dir=stage_dir) as temp_dir:
            temp_fp = os.path.join(temp_dir, filename)
            stage_fp = os.path.join(stage_dir, filename)
            imgout = gippy.GeoImage(temp_fp, xsz, ysz, 1, dtype)
            imgout.SetBandName(asset, 1)
            imgout.SetNoData(-9999.)
            imgout.SetProjection(PROJ)
            imgout.SetAffine(geo)
            imgout[0].Write(data)
            os.rename(temp_fp, stage_fp)
            return [stage_fp]


class daymetData(Data):
    """ A tile of data (all assets and products) """
    name = 'Daymet'
    version = '0.1'
    Asset = daymetAsset

    _products = {
        'tmin': {
            'description': 'Daily minimum air temperature (C)',
            'assets': ['tmin']
        },
        'tmax': {
            'description': 'Daily maximum air temperature (C)',
            'assets': ['tmax']
        },
        'prcp': {
            'description': 'Daily precipitation (mm)',
            'assets': ['prcp']
        },
        'srad': {
            'description': 'Daily solar radiation (W m-2)',
            'assets': ['srad']
        },
        'vp': {
            'description': 'Daily vapor pressure (Pa)',
            'assets': ['vp']
        },
    }
