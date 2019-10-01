#!/usr/bin/env python
################################################################################
#    GIPS: Geospatial Image Processing System
#
#    AUTHOR: Matthew Hanson
#    EMAIL:  matt.a.hanson@gmail.com
#
#    Copyright (C) 2014-2018 Applied Geosolutions
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 3 of the License, or
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
import os
import datetime
import glob
import traceback
import re

from backports.functools_lru_cache import lru_cache
import gdal
import numpy
import requests

import gippy
from gips.data.core import Repository, Asset, Data
from gips.utils import File2List, List2File
from gips import utils


class aodRepository(Repository):
    name = 'AOD'
    description = 'Aerosol Optical Depth from MODIS (MOD08)'
    _datedir = '%Y%j'
    _subdirs = [
        'tiles', 'stage', 'quarantine', 'composites',
        'composites/ltad'
    ]
    _the_tile = 'h01v01'

    @classmethod
    def data_path(cls, tile='', date=''):
        path = cls.path('tiles')
        if date != '':
            path = os.path.join(path, str(date.strftime('%Y')), str(date.strftime('%j')))
        return path

    @classmethod
    def find_tiles(cls):
        return [cls._the_tile]

    @classmethod
    def find_dates(cls, tile=''):
        """ Get list of dates available in repository for a tile """
        tdir = cls.path('tiles')
        #if os.path.exists(tdir):
        dates = []
        for year in os.listdir(tdir):
            days = os.listdir(os.path.join(tdir, year))
            for day in days:
                dates.append(datetime.datetime.strptime(year + day, '%Y%j').date())
        return dates

    @classmethod
    def vector2tiles(cls, *args, **kwargs):
        """ There are no tiles -- so use the "one tile" style """
        return {cls._the_tile: (1, 1)}


class aodAsset(Asset):
    Repository = aodRepository

    _sensors = {
        'MOD': {'description': 'MODIS Terra'},
        #'MYD': {'description': 'MODIS Aqua'},
    }
    _host = 'ladsweb.nascom.nasa.gov'
    _assets = {
        'MOD08': {
            'pattern': r'^MOD08_D3.+?hdf$',
            'startdate': datetime.date(2000, 2, 18),
            'path': '/allData/6/MOD08_D3',
            'latency': 7,
            'url': 'https://ladsweb.modaps.eosdis.nasa.gov/'
                   'archive/allData/61/MOD08_D3/',
        },
        #'MYD08': {
        #    'pattern': 'MYD08_D3*hdf',
        #    'url': 'ladsweb.nascom.nasa.gov/allData/51/MYD08_D3'
        #}
    }

    def __init__(self, filename):
        """ Inspect a single file and get some metadata """
        super(aodAsset, self).__init__(filename)

        bname = os.path.basename(filename)
        self.asset = bname[0:5]
        self.tile = self.Repository._the_tile
        year = bname[10:14]
        doy = bname[14:17]
        self.date = datetime.datetime.strptime(year + doy, "%Y%j").date()
        self.sensor = bname[:3]
        collection_number = float(bname[18:21])
        # collection number is encoded in the filename as 005, 006, 051, or
        # 055.  So, we take it as a float, and then divide by the order of
        # magnitude to get the modis_collection number
        self._version = collection_number / (
                10**numpy.floor(numpy.log10(collection_number)))
        prefix = 'HDF4_EOS:EOS_GRID:"'
        sds = {
            5: 'Optical_Depth_Land_And_Ocean_Mean',
            6: 'Aerosol_Optical_Depth_Land_Ocean_Mean',
        }
        self.products['aod'] = (prefix + filename + '":mod08:{}'.format(
            sds[int(self._version)]))

    def datafiles(self):
        indexfile = self.filename + '.index'

        if os.path.exists(indexfile):
            datafiles = File2List(indexfile)
        else:
            gdalfile = gdal.Open(self.filename)
            subdatasets = gdalfile.GetSubDatasets()
            datafiles = [s[0] for s in subdatasets]
            List2File(datafiles, indexfile)
        return datafiles

    @classmethod
    def query_provider(cls, asset, tile, date):
        """Find out from the NASA servers what AOD assets are available."""
        if asset not in cls._assets:
            raise ValueError('{} has no defined asset for {}'.format(cls.Repository.name, asset))
        with utils.error_handler("Error querying " + cls._host, continuable=True):
            # example full json query URL:
            # https://ladsweb.modaps.eosdis.nasa.gov/archive/allData/6/MOD08_D3/2017/145.json
            url_head = cls._assets[asset]['url'] + date.strftime('%Y/%j')
            query_url = url_head + '.json'
            utils.verbose_out('Downloading ' + query_url, 5)
            resp = requests.get(query_url)
            resp.raise_for_status() # some errors don't raise otherwise
            found_assets = resp.json()
            if len(found_assets) != 1:
                raise ValueError('Expected one {} asset, found {}'.format(
                    asset, len(resp)))
            filename = str(found_assets[0]['name']) # str() to prevent unicode
            return filename, url_head + '/' + filename
        return None, None


    @classmethod
    def fetch(cls, asset, tile, date):
        """Fetch the AOD asset matching the ATD."""
        query_rv = cls.query_service(asset, tile, date)
        if query_rv is None:
            return []
        bn, url = query_rv['basename'], query_rv['url']
        stage_dn = cls.Repository.path('stage')
        stage_fp = os.path.join(stage_dn, bn)
        with utils.make_temp_dir(prefix='fetch', dir=stage_dn) as tmp_dn:
            tmp_fp = os.path.join(tmp_dn, bn)
            utils.verbose_out('Fetching from {}, saving in {}'.format(
                url, tmp_fp), 5)
            resp = requests.get(url, stream=True)
            resp.raise_for_status()
            with open(tmp_fp, 'wb') as tmp_fo:
                for chunk in resp.iter_content(chunk_size=(1024**2)):
                    tmp_fo.write(chunk)
            os.rename(tmp_fp, stage_fp)
        return [stage_fp]


class aodData(Data):
    name = 'AOD'
    version = '0.9.1'
    Asset = aodAsset

    _products = {
        'aod': {
            'description': 'Aerosol Optical Depth',
            # the list of asset types associated with this product
            'assets': ['MOD08'],  # , 'MYD08'],
        },
        'ltad': {
            'description': 'Average daily AOD',
            # the list of asset types associated with this product
            'assets': ['MOD08'],  # , 'MYD08'],
            'composite': True,
        },
        'lta': {
            'description': 'Average AOD',
            'assets': ['MOD08'],
            'composite': True
        }
    }


    #def process(self, products):
    #    start = datetime.datetime.now()
        #bname = os.path.basename(self.assets[''].filename)
    #    for product in products:
            #if product == 'aerolta':
            #    self.process_aerolta()
    #        utils.verbose_out(' -> %s: processed %s in %s' % (fout, product, datetime.datetime.now()-start))

    @classmethod
    def initialize_composites(cls):
        '''
        This method is incomplete, but will ensure that the composites
        directory is boostrapped for running process composites.

        INCOMPLETE at this time.
        '''
        lta_tif = os.path.join(cls.Asset.Repository.path('composites'), 'lta.tif')
        ltadpat = os.path.join(
            cls.Asset.Repository.path('composites'),
            'ltad',
            'ltad???.tif'
        )
        ltad_tifs = glob.glob(ltadpat)
        if os.path.exists(lta_tif) and len(ltad_tifs) == 366:
            utils.verbose_out('lta composites already initialized', 2)
            return
        a = inv[inv.dates[0]].tiles[cls.Asset.Repository._the_tile].open('aod')
        a[0] = a[0] * 0 + a[0].nodata()
        a.save(ltatif)


    @classmethod
    def process_composites(cls, inventory, products, **kwargs):
        '''
        Currently inoperative do to absence of 'start_day' and 'end_day' from
        DataInventory class.
        '''
        # since it is broken
        raise NotImplementedError('Composite processing is currently broken')
        cls.initialize_composites()
        for product in products:
            cpath = os.path.join(cls.Asset.Repository.path('composites'), 'ltad')
            path = os.path.join(cpath, 'ltad')
            # Calculate AOT long-term multi-year averages (lta) for given day
            if product == 'ltad':
                # tried this as a replacement for the 'for' below, but this
                # doesn't make it work either.
                # for day in range(
                #         inventory.temporal.daybounds[0],
                #         inventory.temporal.daybounds[1] + 1
                # ):
                for day in range(inventory.start_day, inventory.end_day + 1):
                    dates = [d for d in inventory.dates if int(d.strftime('%j')) == day]
                    filenames = [inventory[d].tiles[cls.Asset.Repository._the_tile].filenames['MOD', 'aod'] for d in dates]
                    fout = path + '%s.tif' % str(day).zfill(3)
                    cls.process_mean(filenames, fout)
            # Calculate single average per pixel (all days and years)
            if product == 'lta':
                filenames = glob.glob(path + '*.tif')
                if len(filenames) > 0:
                    fout = os.path.join(cls.Asset.Repository.path('composites'), 'lta.tif')
                    cls.process_mean(filenames, fout)
                else:
                    raise Exception('No daily LTA files exist!')

    @classmethod
    def process_mean(cls, filenames, fout):
        """ Calculates mean of all filenames, and per pixel variances """
        start = datetime.datetime.now()
        if len(filenames) > 0:
            img = gippy.GeoImage(filenames)
            imgout = gippy.GeoImage.create_from(img, fout, 2, 'float32')
            imgout.set_nodata(-32768)
            img.mean(imgout[0])
            meanimg = imgout[0].read()
            for band in range(0, len(img)):
                data = img[band].read()
                mask = img[band].DataMask()
                var = numpy.multiply(numpy.power(data - meanimg, 2), mask)
                if band == 0:
                    totalvar = var
                    counts = mask
                else:
                    totalvar = totalvar + var
                    counts = counts + mask
            inds = numpy.where(counts == 0)
            totalvar[inds] = -32768
            inds = numpy.where(counts != 0)
            totalvar[inds] = numpy.divide(totalvar[inds], counts[inds])
            imgout[1].write(totalvar)
            t = datetime.datetime.now() - start
            utils.verbose_out(
                '%s: mean/var for %s files processed in %s' %
                (os.path.basename(fout), len(filenames), t)
            )
        else:
            raise Exception('No filenames provided')
        return imgout

    @classmethod
    def _read_point(cls, filename, roi, nodata):
        """ Read single point from mean/var file and return if valid, or mean/var of 3x3 neighborhood """
        # hacky unpack the region of interest
        x0, y0, x1, y1 = roi

        if not os.path.exists(filename):
            return (numpy.nan, numpy.nan)
        with utils.error_handler('Unable to read point from {}'.format(filename), continuable=True):
            img = gippy.GeoImage(filename)
            vals = img[0].read()[x0:x1,y0:y1].squeeze()
            variances = img[1].read()[x0:x1,y0:y1]
            vals[numpy.where(vals == nodata)] = numpy.nan
            variances[numpy.where(variances == nodata)] = numpy.nan
            val = numpy.nan
            var = numpy.nan
            if ~numpy.isnan(vals[1, 1]):
                val = vals[1, 1]
            elif numpy.any(~numpy.isnan(vals)):
                val = numpy.mean(vals[~numpy.isnan(vals)])
            if ~numpy.isnan(variances[1,1]):
                var = variances[1, 1]
            elif numpy.any(~numpy.isnan(variances)):
                var = numpy.mean(variances[~numpy.isnan(variances)])
            img = None
            return (val, var)
        return (numpy.nan, numpy.nan)

    @classmethod
    def get_aod(cls, lat, lon, date, fetch=True):
        """Returns an aod value for the given lat/lon.

        If the pixel has a no-data value, nearby values are averaged.  If
        no nearby values are available, it makes an estimate using
        long-term averages.
        """
        pixx = int(numpy.round(float(lon) + 179.5))
        pixy = int(numpy.round(89.5 - float(lat)))

        # hacky create region of interest
        x0, y0, x1, y1 = pixx - 1, pixy - 1, pixx + 2, pixy + 2
        roi = (x0, y0, x1, y1)

        # try reading actual data file first
        aod = numpy.nan

        with utils.error_handler('Unable to load aod values', continuable=True):

            # this is just for fetching the data
            inv = cls.inventory(dates=date.strftime('%Y-%j'), fetch=fetch, products=['aod'])
            img = inv[date].tiles[cls.Asset.Repository._the_tile].open('aod')
            vals = img[0].read()[x0:x1,y0:y1]
            # TODO - do this automagically in swig wrapper
            vals[numpy.where(vals == img[0].nodata())] = numpy.nan
            aod = vals[1, 1]
            img = None
            source = 'MODIS (MOD08_D3)'
             # if invalid center but valid vals exist in 3x3
            if numpy.isnan(aod) and numpy.any(~numpy.isnan(vals)):
                aod = numpy.mean(vals[~numpy.isnan(vals)])
                source = 'MODIS (MOD08_D3) spatial average'

        # Calculate best estimate from multiple sources
        if numpy.isnan(aod):
            day = date.strftime('%j')
            repo = cls.Asset.Repository
            cpath = repo.path('composites')
            nodata = -32768

            source = 'Weighted estimate using MODIS LTA values'

            def _calculate_estimate(filename):
                val, var = cls._read_point(filename, roi, nodata)
                aod = numpy.nan
                norm = numpy.nan

                # Negative values don't make sense
                if val < 0:
                    val = 0
                if var == 0:
                    # There is only one observation, so make up
                    # the variance.
                    if val == 0:
                        var = 0.15
                    else:
                        var = val / 2
                if not numpy.isnan(val) and not numpy.isnan(var):
                    aod = val / var
                    norm = 1.0 / var
                    utils.verbose_out('AOD: LTA-Daily = %s, %s' % (val, var), 3)
                return aod, norm

            # LTA-Daily
            utils.verbose_out('Using long term average AOD')
            filename = os.path.join(cpath, 'ltad', 'ltad%s.tif' % str(day).zfill(4))
            daily_aod, daily_norm = _calculate_estimate(filename)

            # LTA
            lta_aod, lta_norm = _calculate_estimate(os.path.join(cpath, 'lta.tif'))

            if numpy.isnan(lta_aod):
                raise Exception("Could not retrieve AOD")

            aod = lta_aod
            norm = lta_norm
            if not numpy.isnan(daily_aod):
                aod = aod + daily_aod
                norm = norm + daily_norm

            # TODO - adjacent days

            # Final AOD estimate
            aod = aod / norm

        utils.verbose_out('AOD: Source = %s Value = %s' % (source, aod), 2)
        return (source, aod)
