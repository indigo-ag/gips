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
import sys
import re
import datetime
import urllib

import numpy as np
import requests

import gippy
# TODO: Use this:
# from gippy.algorithms import indices
from gips.data.core import Repository, Asset, Data
from gips import utils
from gips.utils import vprint


PROJ = (
    'PROJCS["WELD_CONUS",GEOGCS["GCS_WGS_1984",DATUM["WGS_1984",'
    'SPHEROID["WGS_84",6378137.0,298.257223563]],PRIMEM["Greenwich",0.0],'
    'UNIT["Degree",0.0174532925199433]],PROJECTION["Albers_Conic_Equal_Area"],'
    'PARAMETER["False_Easting",0.0],PARAMETER["False_Northing",0.0],'
    'PARAMETER["longitude_of_center",-96.0],PARAMETER["Standard_Parallel_1",'
    '29.5],PARAMETER["Standard_Parallel_2",45.5],PARAMETER["latitude_of_center",'
    '23.0],UNIT["Meter",1.0]]')


def binmask(arr, bit):
    """ Return boolean array indicating which elements as binary have a 1 in
        a specified bit position. Input is Numpy array.
    """
    return arr & (1 << (bit - 1)) == (1 << (bit - 1))


class weldRepository(Repository):
    name = 'WELD'
    description = 'WELD Landsat'

    _manager_url = "https://urs.earthdata.nasa.gov"

    @classmethod
    def feature2tile(cls, feature):
        """ convert tile field attributes to tile identifier """
        fldindex_h = feature.GetFieldIndex("h")
        fldindex_v = feature.GetFieldIndex("v")
        h = str(int(feature.GetField(fldindex_h))).zfill(2)
        v = str(int(feature.GetField(fldindex_v))).zfill(2)
        return "h%sv%s" % (h, v)


class weldAsset(Asset):
    Repository = weldRepository

    _sensors = {
        'WELD': {'description': 'WELD Landsat'},
    }

    _assets = {
        'CONUS': {
            'pattern': r'^CONUS\.week\d{2}\..{4}\.h.{2}v.{2}\.doy\d{3}to\d{3}\.v1\.5\.hdf$',
            'url': 'http://e4ftl01.cr.usgs.gov/WELD/WELDUSWK.001',
            'startdate': datetime.date(2003, 1, 1),
            'latency': 0,
        },
    }

    _defaultresolution = [30.0, 30.0]

    def __init__(self, filename):
        """ Inspect a single file and get some metadata """
        super(weldAsset, self).__init__(filename)
        bname = os.path.basename(filename)
        parts = bname.split('.')
        self.asset = parts[0]
        self.tile = parts[3]
        year = parts[2]
        doy1 = parts[4][3:6]
        doy2 = parts[4][8:11]
        week = parts[1][4:6]
        self.sensor = "WELD"
        doy = str(datetime.timedelta(7*(int(week) - 1) + 1).days).zfill(3)
        self.date = datetime.datetime.strptime(year + doy, "%Y%j").date()

    @classmethod
    def fetch(cls, asset, tile, date):
        raise NotImplementedError("http://e4ftl01.cr.usgs.gov/WELD/ no longer exists")
        year, month, day = date.timetuple()[:3]
        mainurl = '%s/%s.%02d.%02d' % (cls._assets[asset]['url'], str(year), month, day)
        utils.verbose_out("searching at " + mainurl, 4)
        with utils.error_handler('Unable to access {}'.format(mainurl)):
            response = cls.Repository.managed_request(mainurl)
            if response is None:
                return []
        pattern = r'(%s.week\d{2}.%s.%s.doy\d{3}to\d{3}.v1.5.hdf)' % (asset, str(year), tile)
        cpattern = re.compile(pattern)
        fetched = []
        http_kw = {'timeout': 10,
                   'auth': (cls.Repository.get_setting('username'),
                            cls.Repository.get_setting('password'))}
        for item in response.readlines():
            item = item.decode('utf-8')
            if cpattern.search(item):
                if 'xml' in item:
                    continue
                name = cpattern.findall(item)[0]
                url = ''.join([mainurl, '/', name])
                utils.verbose_out("found " + url)
                outpath = os.path.join(cls.Repository.path('stage'), name)
                if os.path.exists(outpath):
                    continue
                # match found, perform the download
                err_msg = 'Unable to retrieve {} from {}'.format(name, url)
                with utils.error_handler(err_msg, continuable=True):
                    response = cls.Repository.managed_request(url)
                    if response is None:
                        return fetched # might as well give up now since the rest probably fail too
                    with open(outpath, 'wb') as fd:
                        fd.write(response.read())
                    utils.verbose_out('Retrieved {}'.format(name), 2)
                    fetched.append(outpath)
        if not fetched:
            utils.verbose_out('Unable to find remote match for {} at {}'.format(pattern, mainurl),
                              4, sys.stderr)
        return fetched


class weldData(Data):
    """ A tile of data (all assets and products) """
    name = 'WELD'
    version = '0.1.0'
    Asset = weldAsset
    _productgroups = {
        "indices": ['ndsi', 'ndvi', 'brgt'],
    }
    _products = {
        'ndsi': {
            'description': 'Snow index',
            'assets': ['CONUS'],
        },
        'ndvi': {
            'description': 'Vegetation index',
            'assets': ['CONUS'],
        },
        'brgt': {
            'description': 'Brightness index',
            'assets': ['CONUS'],
        },
        'snow': {
            'description': 'Snow cover',
            'assets': ['CONUS'],
        },
    }

    @classmethod
    def need_to_fetch(cls, *args, **kwargs):
        return True

    @Data.proc_temp_dir_manager
    def process(self, *args, **kwargs):
        """Process requested products."""
        products = super(weldData, self).process(*args, **kwargs)
        if len(products) == 0:
            return
        sensor = 'WELD'
        for key, val in products.requested.items():
            start = datetime.datetime.now()
            prod_type = val[0]
            fname = self.temp_product_filename(sensor, prod_type) # moved to archive at end of loop

            meta = self.meta_dict()
            meta['AVAILABLE_ASSETS'] = ''

            # Check for asset availability
            needed_assets = self._products[val[0]]['assets']
            allsds = []
            for a in needed_assets:
                if a in self.assets:
                    with utils.error_handler('Error reading datafiles for ' + a, continuable=True):
                        allsds.extend(self.assets[a].datafiles())
                        meta['AVAILABLE_ASSETS'] += ' ' + a
            if meta['AVAILABLE_ASSETS'] == '':
                utils.verbose_out('There are no available assets (%s) on %s for tile %s'
                           % (str(needed_assets), str(self.date), str(self.id), ), 5)
                continue

            # SNOW ICE INDEX PRODUCT
            if val[0] == "ndsi":
                VERSION = "1.0"
                meta['VERSION'] = VERSION
                refl = gippy.GeoImage(allsds)
                # band 2
                grnimg = refl[1].read()
                missing = refl[1].nodata()
                # band 4
                nirimg = refl[3].read()
                assert refl[3].nodata() == missing
                # band 5
                swrimg = refl[4].read()
                assert refl[4].nodata() == missing
                cldimg = refl[11].read()
                ndsi = missing + np.zeros_like(grnimg)
                wg = np.where((grnimg != missing) & (swrimg != missing) & (grnimg + swrimg != 0.0) & (cldimg == 0))
                ng = len(wg[0])
                vprint("ng", ng)
                if ng == 0:
                    continue
                ndsi[wg] = (grnimg[wg] - swrimg[wg]) / (grnimg[wg] + swrimg[wg])
                vprint(ndsi.min(), ndsi.max())
                vprint(ndsi[wg].min(), ndsi[wg].max())
                vprint("writing", fname)
                imgout = gippy.GeoImage.create_from(refl, fname, 1, 'float32')
                imgout.set_nodata(float(missing))
                imgout.set_offset(0.0)
                imgout.set_gain(1.0)
                imgout.set_srs(PROJ)
                imgout[0].write(ndsi)
                imgout.set_bandname('NDSI', 1)

            # SNOW ICE COVER PRODUCT
            if val[0] == "snow":
                VERSION = "1.0"
                meta['VERSION'] = VERSION
                refl = gippy.GeoImage(allsds)
                # band 2
                grnimg = refl[1].read()
                missing = refl[1].nodata()
                # band 4
                nirimg = refl[3].read()
                assert refl[3].nodata() == missing
                # band 5
                swrimg = refl[4].read()
                assert refl[4].nodata() == missing
                cldimg = refl[11].read()
                accaimg = refl[13].read()
                snow = 127 + np.zeros_like(grnimg)
                ndsi = missing + np.zeros_like(grnimg)
                wg = np.where((grnimg != missing) & (swrimg != missing) & (grnimg + swrimg != 0.0) & (cldimg == 0))
                ng = len(wg[0])
                vprint("ng", ng)
                if ng == 0:
                    continue
                ndsi[wg] = (grnimg[wg] - swrimg[wg]) / (grnimg[wg] + swrimg[wg])
                ws = np.where((ndsi != missing) & (ndsi > 0.4) & (nirimg > 0.11) & (swrimg > 0.1))
                wc = np.where((ndsi != missing) & (ndsi > 0.4) & (nirimg <= 0.11) & (swrimg <= 0.1))
                ns = len(ws[0])
                nc = len(wc[0])
                vprint(ng, ns, nc)
                if (ns > 0):
                    snow[ws] = 1
                if (nc > 0):
                    snow[wc] = 0
                vprint("writing", fname)
                imgout = gippy.GeoImage.create_from(refl, fname, 1, 'uint8')
                imgout.set_nodata(127)
                imgout.set_offset(0.)
                imgout.set_gain(1.)
                imgout.set_srs(PROJ)
                imgout[0].write(snow)
                imgout.set_bandname('SNOW', 1)

            # VEGETATION INDEX PRODUCT
            if val[0] == "ndvi":
                VERSION = "1.0"
                meta['VERSION'] = VERSION
                refl = gippy.GeoImage(allsds)
                # band 3
                redimg = refl[2].read()
                missing = refl[2].nodata()
                # band 4
                nirimg = refl[3].read()
                assert refl[3].nodata() == missing
                cldimg = refl[11].read()
                accaimg = refl[13].read()
                ndvi = missing + np.zeros_like(redimg)
                wg = np.where((redimg != missing) & (nirimg != missing) & (redimg + nirimg != 0.0) & (cldimg == 0))
                ng = len(wg[0])
                vprint("ng", ng)
                if ng == 0:
                    continue
                ndvi[wg] = (nirimg[wg] - redimg[wg]) / (nirimg[wg] + redimg[wg])
                vprint(ndvi.min(), ndvi.max())
                vprint(ndvi[wg].min(), ndvi[wg].max())
                vprint("writing", fname)
                imgout = gippy.GeoImage.create_from(refl, fname, 1, 'float32')
                imgout.set_nodata(float(missing))
                imgout.set_offset(0.0)
                imgout.set_gain(1.0)
                imgout.set_srs(PROJ)
                imgout[0].write(ndvi)
                imgout.set_bandname('NDVI', 1)

            # BRIGHTNESS PRODUCT
            if val[0] == "brgt":
                VERSION = "1.0"
                meta['VERSION'] = VERSION
                refl = gippy.GeoImage(allsds)
                # band 2
                grnimg = refl[1].read()
                missing = refl[1].nodata()
                # band 3
                redimg = refl[2].read()
                assert refl[2].nodata() == missing
                # band 4
                nirimg = refl[3].read()
                assert refl[3].nodata() == missing
                cldimg = refl[11].read()
                brgt = missing + np.zeros_like(redimg)
                wg = np.where((grnimg != missing) & (redimg != missing) & (nirimg != missing) & (cldimg == 0))
                ng = len(wg[0])
                vprint("ng", ng)
                if ng == 0:
                    continue
                brgt[wg] = (grnimg[wg] + redimg[wg] + nirimg[wg])/3.
                vprint(brgt.min(), brgt.max())
                vprint(brgt[wg].min(), brgt[wg].max())
                vprint("writing", fname)
                imgout = gippy.GeoImage.create_from(refl, fname, 1, 'float32')
                imgout.set_nodata(float(missing))
                imgout.set_offset(0.0)
                imgout.set_gain(1.0)
                imgout.set_srs(PROJ)
                imgout[0].write(brgt)
                imgout.set_bandname('BRGT', 1)

            # set metadata
            meta = {k: str(v) for k, v in meta.iteritems()}
            imgout.add_meta(meta)

            # add product to inventory
            archive_fp = self.archive_temp_path(fname)
            self.AddFile(sensor, key, archive_fp)
            vprint(' -> {}: processed in {}'.format(os.path.basename(fname),
                                                    datetime.datetime.now() - start))
