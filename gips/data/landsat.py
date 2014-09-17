#!/usr/bin/env python
################################################################################
#    GIPS: Geospatial Image Processing System
#
#    Copyright (C) 2014 Matthew A Hanson
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

import os
import sys
import glob
import re
from datetime import datetime
import shutil
import numpy
import traceback

import gippy
from gips.core import Repository, Asset, Data
from gips.inventory import DataInventory
from gips.utils import VerboseOut, RemoveFiles
import gips.settings as settings

from gips.data.aod import AODData

__version__ = '0.7.0'


class LandsatRepository(Repository):
    """ Singleton (all class methods) to be overridden by child data classes """
    repo = settings.REPOS['landsat']
    _rootpath = repo.get('rootpath', Repository._rootpath)
    _tiles_vector = repo.get('tiles_vector', Repository._tiles_vector)
    _tile_attribute = repo.get('tile_attribute', Repository._tile_attribute)

    @classmethod
    def feature2tile(cls, feature):
        tile = super(LandsatRepository, cls).feature2tile(feature)
        return tile.zfill(6)


class LandsatAsset(Asset):
    """ Landsat asset (original raw tar file) """
    Repository = LandsatRepository

    # tassled cap coefficients for L5 and L7
    _tcapcoef = [
        [0.3561, 0.3972, 0.3904, 0.6966, 0.2286, 0.1596],
        [-0.3344, -0.3544, -0.4556, 0.6966, -0.0242, -0.2630],
        [0.2626, 0.2141, 0.0926, 0.0656, -0.7629, -0.5388],
        [0.0805, -0.0498, 0.1950, -0.1327, 0.5752, -0.7775],
        [-0.7252, -0.0202, 0.6683, 0.0631, -0.1494, -0.0274],
        [0.4000, -0.8172, 0.3832, 0.0602, -0.1095, 0.0985]
    ]

    # combine sensormeta with sensor
    _sensors = {
        #'LT4': {
        #    'description': 'Landsat 4',
        #},
        'LT5': {
            'description': 'Landsat 5',
            'bands': ['1', '2', '3', '4', '5', '6', '7'],
            'oldbands': ['1', '2', '3', '4', '5', '6', '7'],
            'colors': ["BLUE", "GREEN", "RED", "NIR", "SWIR1", "LWIR", "SWIR2"],
            # TODO - update bands with actual L5 values (these are L7)
            'bandlocs': [0.4825, 0.565, 0.66, 0.825, 1.65, 11.45, 2.22],
            'bandwidths': [0.065, 0.08, 0.06, 0.15, 0.2, 2.1, 0.26],
            'E': [1983, 1796, 1536, 1031, 220.0, 0, 83.44],
            'K1': [0, 0, 0, 0, 0, 607.76, 0],
            'K2': [0, 0, 0, 0, 0, 1260.56, 0],
            'tcap': _tcapcoef,
        },
        'LE7': {
            'description': 'Landsat 7',
            #bands = ['1','2','3','4','5','6_VCID_1','6_VCID_2','7','8']
            'bands': ['1', '2', '3', '4', '5', '6_VCID_1', '7'],
            'oldbands': ['1', '2', '3', '4', '5', '61', '7'],
            'colors': ["BLUE", "GREEN", "RED", "NIR", "SWIR1", "LWIR", "SWIR2"],
            'bandlocs': [0.4825, 0.565, 0.66, 0.825, 1.65, 11.45, 2.22],
            'bandwidths': [0.065, 0.08, 0.06, 0.15, 0.2, 2.1, 0.26],
            'E': [1997, 1812, 1533, 1039, 230.8, 0, 84.90],
            'K1': [0, 0, 0, 0, 0, 666.09, 0],
            'K2': [0, 0, 0, 0, 0, 1282.71, 0],
            'tcap': _tcapcoef,
        },
        'LC8': {
            'description': 'Landsat 8',
            'bands': ['1', '2', '3', '4', '5', '6', '7', '9', '10', '11'],
            'oldbands': ['1', '2', '3', '4', '5', '6', '7', '9', '10', '11'],
            'colors': ["COASTAL", "BLUE", "GREEN", "RED", "NIR", "SWIR1", "SWIR2", "CIRRUS", "LWIR", "LWIR2"],
            'bandlocs': [0.443, 0.4825, 0.5625, 0.655, 0.865, 1.610, 2.2, 1.375, 10.8, 12.0],
            'bandwidths': [0.01, 0.0325, 0.0375, 0.025, 0.02, 0.05, 0.1, 0.015, 0.5, 0.5],
            'E': [2638.35, 2031.08, 1821.09, 2075.48, 1272.96, 246.94, 90.61, 369.36, 0, 0],
            'K1': [0, 0, 0, 0, 0, 0, 0, 0, 774.89, 480.89],
            'K2': [0, 0, 0, 0, 0, 0, 0, 0, 1321.08, 1201.14],
            'tcap': [
                [0.3029, 0.2786, 0.4733, 0.5599, 0.508, 0.1872],
                [-0.2941, -0.243, -0.5424, 0.7276, 0.0713, -0.1608],
                [0.1511, 0.1973, 0.3283, 0.3407, -0.7117, -0.4559],
                [-0.8239, 0.0849, 0.4396, -0.058, 0.2013, -0.2773],
                [-0.3294, 0.0557, 0.1056, 0.1855, -0.4349, 0.8085],
                [0.1079, -0.9023, 0.4119, 0.0575, -0.0259, 0.0252],
            ]
        }
    }

    # TODO - consider assets and sensors relationship ?
    _assets = {
        '': {
            'pattern': 'L*.tar.gz'
            #_pattern = r'^L[TEC][4578].*\.tar\.gz$'
        }
    }

    _defaultresolution = [30.0, 30.0]

    def __init__(self, filename):
        """ Inspect a single file and get some metadata """
        super(LandsatAsset, self).__init__(filename)
        fname = os.path.basename(filename)
        self.sensor = fname[0:3]
        self.tile = fname[3:9]
        year = fname[9:13]
        doy = fname[13:16]
        self.date = datetime.strptime(year + doy, "%Y%j")
        if self.sensor not in self._sensors.keys():
            raise Exception("Sensor %s not supported" % self.sensor)
        # Landsat specific additions
        smeta = self._sensors[self.sensor]
        self.meta = {}
        for i, band in enumerate(smeta['colors']):
            wvlen = smeta['bandlocs'][i]
            self.meta[band] = {
                'bandnum': i + 1,
                'wvlen': wvlen,
                'wvlen1': wvlen - smeta['bandwidths'][i] / 2.0,
                'wvlen2': wvlen + smeta['bandwidths'][i] / 2.0,
                'E': smeta['E'][i],
                'K1': smeta['K1'][i],
                'K2': smeta['K2'][i],
            }
        self.visbands = [col for col in smeta['colors'] if col[0:4] != "LWIR"]
        self.lwbands = [col for col in smeta['colors'] if col[0:4] == "LWIR"]


class LandsatData(Data):
    name = 'Landsat'

    Asset = LandsatAsset

    _prodpattern = '*.tif'
    _products = {
        #'Standard': {
        # 'rgb': 'RGB image for viewing (quick processing)',
        'rad': {'description': 'Surface-leaving radiance', 'choices': ['toa']},
        'ref': {'description': 'Surface reflectance', 'choices': ['toa']},
        'temp': {'description': 'Brightness (apparent) temperature', 'toa': True},
        'acca': {'description':
                 ('Automated Cloud Cover Assesment -- 0 to 3 arguments. '
                  'First is erosion kernel diameter in pixels, '
                  'second is dilation kernel diameter in pixels, '
                  'and last is the cloud height in meters. '
                  'If not specified, the values are 5, 10 and 4000.'),
                 'args': '*', 'toa': True},
        'fmask': {'description': 'Fmask cloud cover', 'args': '*', 'toa': True},
        'tcap': {'description': 'Tassled cap transformation', 'toa': True},
        #'Indices': {
        'bi': {'description': 'Brightness Index', 'group': 'Index', 'choices': ['toa']},
        'evi': {'description': 'Enhanced Vegetation Index', 'group': 'Index', 'choices': ['toa']},
        'lswi': {'description': 'Land Surface Water Index', 'group': 'Index', 'choices': ['toa']},
        'msavi2': {'description':
                   'Modified Soil-Adjusted Vegetation Index (revised)',
                   'group': 'Index', 'choices': ['toa']},
        'ndsi': {'description': 'Normalized Difference Snow Index', 'group': 'Index', 'choices': ['toa']},
        'ndvi': {'description': 'Normalized Difference Vegetation Index', 'group': 'Index', 'choices': ['toa']},
        'ndwi': {'description': 'Normalized Difference Water Index', 'group': 'Index', 'choices': ['toa']},
        'satvi': {'description': 'Soil-Adjusted Total Vegetation Index', 'group': 'Index', 'choices': ['toa']},
        #'Tillage Indices': {
        'ndti': {'description': 'Normalized Difference Tillage Index', 'group': 'Tillage', 'choices': ['toa']},
        'crc': {'description': 'Crop Residue Cover', 'group': 'Tillage', 'choices': ['toa']},
        'sti': {'description': 'Standard Tillage Index', 'group': 'Tillage', 'choices': ['toa']},
        'isti': {'description': 'Inverse Standard Tillage Index', 'group': 'Tillage', 'choices': ['toa']},
    }
    _defaultproduct = 'ref'

    def SixS(self):
        from gips.utils import atmospheric_model
        from Py6S import SixS, Geometry, AeroProfile, Altitudes, Wavelength, GroundReflectance, AtmosCorr, SixSHelpers
        start = datetime.now()
        VerboseOut('Running atmospheric model (6S)', 2)

        dt = self.metadata['datetime']
        geo = self.metadata['geometry']

        s = SixS()
        # Geometry
        s.geometry = Geometry.User()
        s.geometry.from_time_and_location(geo['lat'], geo['lon'], str(dt), geo['zenith'], geo['azimuth'])
        s.altitudes = Altitudes()
        s.altitudes.set_target_sea_level()
        s.altitudes.set_sensor_satellite_level()

        # Atmospheric profile
        s.atmos_profile = atmospheric_model(self.metadata['JulianDay'], geo['lat'])

        # Aerosols
        # TODO - dynamically adjust AeroProfile?
        s.aero_profile = AeroProfile.PredefinedType(AeroProfile.Continental)

        self.aod = AODData.get_aod(geo['lat'], geo['lon'], self.date)
        s.aot550 = self.aod[1]

        # Other settings
        s.ground_reflectance = GroundReflectance.HomogeneousLambertian(GroundReflectance.GreenVegetation)
        s.atmos_corr = AtmosCorr.AtmosCorrLambertianFromRadiance(1.0)

        # Used for testing
        #filter_function = True
        if self.sensor != 'LC8':
            if self.sensor == 'LT5':
                func = SixSHelpers.Wavelengths.run_landsat_tm
            elif self.sensor == 'LE7':
                func = SixSHelpers.Wavelengths.run_landsat_etm
            elif self.sensor == 'LC8':
                func = SixSHelpers.Wavelengths.run_landsat_oli
            stdout = sys.stdout
            sys.stdout = open(os.devnull, 'w')
            wvlens, outputs = func(s)
            sys.stdout = stdout
        else:
            outputs = []
            for b in self.assets[''].visbands:
                wvlen1 = self.assets[''].meta[b]['wvlen1']
                wvlen2 = self.assets[''].meta[b]['wvlen2']
                s.wavelength = Wavelength(wvlen1, wvlen2)
                s.run()
                outputs.append(s.outputs)

        results = {}
        VerboseOut("{:>6} {:>8}{:>8}{:>8}".format('Band', 'T', 'Lu', 'Ld'), 2)
        for b, out in enumerate(outputs):
            t = out.trans['global_gas'].upward
            Lu = out.atmospheric_intrinsic_radiance
            Ld = (out.direct_solar_irradiance + out.diffuse_solar_irradiance + out.environmental_irradiance) / numpy.pi
            results[self.assets[''].visbands[b]] = [t, Lu, Ld]
            VerboseOut("{:>6}: {:>8.3f}{:>8.2f}{:>8.2f}".format(self.assets[''].visbands[b], t, Lu, Ld), 2)
        VerboseOut('Ran atmospheric model in %s' % str(datetime.now() - start), 2)

        return results

    def process(self, products, **kwargs):
        """ Make sure all products have been processed """
        start = datetime.now()
        bname = os.path.basename(self.assets[''].filename)
        try:
            img = self._readraw()
        except Exception, e:
            raise Exception('Error reading %s: %s' % (bname, e))

        # running atmosphere if any products require it
        toa = True
        for val in products.values():
            toa = toa and (self._products[val[0]].get('toa', False) or 'toa' in val)
        if not toa:
            start = datetime.now()
            try:
                atmos = self.SixS()
            except Exception, e:
                VerboseOut('Problem running atmospheric model', 2)
                VerboseOut(traceback.format_exc(), 3)

        # Break down by group
        groups = self.products2groups(products)

        meta = self.assets[''].meta
        visbands = self.assets[''].visbands
        lwbands = self.assets[''].lwbands

        md = self.meta_dict()
        if not toa:
            md["AOD Source"] = str(self.aod[0])
            md["AOD Value"] = str(self.aod[1])

        # create non-atmospherically corrected apparent reflectance and temperature image
        reflimg = gippy.GeoImage(img)
        theta = numpy.pi * self.metadata['geometry']['solarzenith'] / 180.0
        sundist = (1.0 - 0.016728 * numpy.cos(numpy.pi * 0.9856 * (self.metadata['JulianDay'] - 4.0) / 180.0))
        for col in self.assets[''].visbands:
            reflimg[col] = img[col] * (1.0 / ((meta[col]['E'] * numpy.cos(theta)) / (numpy.pi * sundist * sundist)))
        for col in self.assets[''].lwbands:
            reflimg[col] = (((img[col].pow(-1)) * meta[col]['K1'] + 1).log().pow(-1)) * meta[col]['K2'] - 273.15

        # Process standard products
        for key, val in groups['Standard'].items():
            start = datetime.now()
            # TODO - update if no atmos desired for others
            toa = self._products[val[0]].get('toa', False) or 'toa' in val
            # Create product
            try:
                fname = os.path.join(self.path, self.basename + '_' + key)
                if val[0] == 'acca':
                    s_azim = self.metadata['geometry']['solarazimuth']
                    s_elev = 90 - self.metadata['geometry']['solarzenith']
                    erosion = int(val[1]) if len(val) > 1 else 5
                    dilation = int(val[2]) if len(val) > 2 else 10
                    cloudheight = int(val[3]) if len(val) > 3 else 4000
                    imgout = gippy.ACCA(reflimg, fname, s_elev, s_azim, erosion, dilation, cloudheight)
                elif val[0] == 'fmask':
                    tolerance = int(val[1]) if len(val) > 1 else 3
                    dilation = int(val[2]) if len(val) > 2 else 5
                    imgout = gippy.Fmask(reflimg, fname, tolerance, dilation)
                elif val[0] == 'rad':
                    imgout = gippy.GeoImage(fname, img, gippy.GDT_Int16, len(visbands))
                    for i in range(0, imgout.NumBands()):
                        imgout.SetBandName(visbands[i], i + 1)
                    imgout.SetNoData(-32768)
                    imgout.SetGain(0.1)
                    if toa:
                        for col in visbands:
                            img[col].Process(imgout[col])
                    else:
                        for col in visbands:
                            ((img[col] - atmos[col][1]) / atmos[col][0]).Process(imgout[col])
                elif val[0] == 'ref':
                    imgout = gippy.GeoImage(fname, img, gippy.GDT_Int16, len(visbands))
                    for i in range(0, imgout.NumBands()):
                        imgout.SetBandName(visbands[i], i + 1)
                    imgout.SetNoData(-32768)
                    imgout.SetGain(0.0001)
                    if toa:
                        for c in visbands:
                            reflimg[c].Process(imgout[c])
                    else:
                        for c in visbands:
                            (((img[c] - atmos[c][1]) / atmos[c][0]) * (1.0 / atmos[c][2])).Process(imgout[c])
                elif val[0] == 'tcap':
                    tmpimg = gippy.GeoImage(reflimg)
                    tmpimg.PruneBands(['BLUE', 'GREEN', 'RED', 'NIR', 'SWIR1', 'SWIR2'])
                    tmpimg.SetBandName('SWIR2', 6)     # work-around
                    arr = numpy.array(self.Asset._sensors[self.sensor]['tcap']).astype('float32')
                    imgout = gippy.LinearTransform(tmpimg, fname, arr)
                    outbands = ['Brightness', 'Greenness', 'Wetness', 'TCT4', 'TCT5', 'TCT6']
                    for i in range(0, imgout.NumBands()):
                        imgout.SetBandName(outbands[i], i + 1)
                elif val[0] == 'temp':
                    imgout = gippy.GeoImage(fname, img, gippy.GDT_Int16, len(lwbands))
                    for i in range(0, imgout.NumBands()):
                        imgout.SetBandName(lwbands[i], i + 1)
                    imgout.SetNoData(-32768)
                    imgout.SetGain(0.1)
                    for col in lwbands:
                        band = img[col]
                        #if toa:
                        #    band = img[col]
                        #else:
                        #    lat = self.metadata['geometry']['lat']
                        #    lon = self.metadata['geometry']['lon']
                        #    atmos = MODTRAN(meta[col], self.metadata['datetime'], lat, lon)
                        #    e = 0.95
                        #    band = (img[col] - (atmos.output[1] + (1-e) * atmos.output[2])) / (atmos.output[0] * e)
                        band = (((band.pow(-1)) * meta[col]['K1'] + 1).log().pow(-1)) * meta[col]['K2'] - 273.15
                        band.Process(imgout[col])
                fname = imgout.Filename()
                imgout.SetMeta(md)
                imgout = None
                self.products[key] = fname
                VerboseOut(' -> %s: processed in %s' % (os.path.basename(fname), datetime.now() - start), 1)
            except Exception, e:
                VerboseOut('Error creating product %s for %s: %s' % (key, bname, e), 2)
                VerboseOut(traceback.format_exc(), 3)

        # Process Indices
        indices0 = dict(groups['Index'], **groups['Tillage'])
        if len(indices0) > 0:
            start = datetime.now()
            indices = {}
            indices_toa = {}
            for key, val in indices0.items():
                if 'toa' in val:
                    indices_toa[key] = val
                else:
                    indices[key] = val
            # Run TOA
            fnames = [os.path.join(self.path, self.basename + '_' + key) for key in indices_toa]
            prodarr = dict(zip([indices_toa[p][0] for p in indices_toa.keys()], fnames))
            if len(fnames) > 0:
                prodout = gippy.Indices(img, prodarr, md)
                self.products.update(prodout)
            # Run atmospherically corrected
            for col in visbands:
                img[col] = ((img[col] - atmos[col][1]) / atmos[col][0]) * (1.0 / atmos[col][2])
            fnames = [os.path.join(self.path, self.basename + '_' + key) for key in indices]
            if len(fnames) > 0:
                prodarr = dict(zip([indices[p][0] for p in indices.keys()], fnames))
                prodout = gippy.Indices(img, prodarr, md)
                self.products.update(prodout)
            VerboseOut(' -> %s: processed %s in %s' % (self.basename, indices0.keys(), datetime.now() - start), 1)

        img = None
        # cleanup directory
        try:
            for bname in self.assets[''].datafiles():
                if bname[-7:] != 'MTL.txt':
                    files = glob.glob(os.path.join(self.path, bname) + '*')
                    RemoveFiles(files)
            shutil.rmtree(os.path.join(self.path, 'modtran'))
        except:
            #VerboseOut(traceback.format_exc(), 4)
            pass

    def filter(self, pclouds=100, **kwargs):
        """ Check if tile passes filter """
        if pclouds < 100:
            self.meta()
            if self.metadata['clouds'] > pclouds:
                return False
        return True

    def meta(self):
        """ Read in Landsat MTL (metadata) file """

        # test if metadata already read in, if so, return

        datafiles = self.assets[''].datafiles()
        mtlfilename = [f for f in datafiles if 'MTL.txt' in f][0]
        if not os.path.exists(mtlfilename):
            mtlfilename = self.assets[''].extract([mtlfilename])[0]
        # Read MTL file
        try:
            text = open(mtlfilename, 'r').read()
        except IOError as e:
            raise Exception('({})'.format(e))

        smeta = self.assets['']._sensors[self.sensor]

        # Process MTL text - replace old metadata tags with new
        # NOTE This is not comprehensive, there may be others
        text = text.replace('ACQUISITION_DATE', 'DATE_ACQUIRED')
        text = text.replace('SCENE_CENTER_SCAN_TIME', 'SCENE_CENTER_TIME')
        for (ob, nb) in zip(smeta['oldbands'], smeta['bands']):
            text = re.sub(r'\WLMIN_BAND' + ob, 'RADIANCE_MINIMUM_BAND_' + nb, text)
            text = re.sub(r'\WLMAX_BAND' + ob, 'RADIANCE_MAXIMUM_BAND_' + nb, text)
            text = re.sub(r'\WQCALMIN_BAND' + ob, 'QUANTIZE_CAL_MIN_BAND_' + nb, text)
            text = re.sub(r'\WQCALMAX_BAND' + ob, 'QUANTIZE_CAL_MAX_BAND_' + nb, text)
            text = re.sub(r'\WBAND' + ob + '_FILE_NAME', 'FILE_NAME_BAND_' + nb, text)
        for l in ('LAT', 'LON', 'MAPX', 'MAPY'):
            for c in ('UL', 'UR', 'LL', 'LR'):
                text = text.replace('PRODUCT_' + c + '_CORNER_' + l, 'CORNER_' + c + '_' + l + '_PRODUCT')
        text = text.replace('\x00', '')
        # Remove junk
        lines = text.split('\n')
        mtl = dict()
        for l in lines:
            meta = l.replace('\"', "").strip().split('=')
            if len(meta) > 1:
                key = meta[0].strip()
                item = meta[1].strip()
                if key != "GROUP" and key != "END_GROUP":
                    mtl[key] = item

        # Extract useful metadata
        lats = (float(mtl['CORNER_UL_LAT_PRODUCT']), float(mtl['CORNER_UR_LAT_PRODUCT']),
                float(mtl['CORNER_LL_LAT_PRODUCT']), float(mtl['CORNER_LR_LAT_PRODUCT']))
        lons = (float(mtl['CORNER_UL_LON_PRODUCT']), float(mtl['CORNER_UR_LON_PRODUCT']),
                float(mtl['CORNER_LL_LON_PRODUCT']), float(mtl['CORNER_LR_LON_PRODUCT']))
        lat = (min(lats) + max(lats)) / 2.0
        lon = (min(lons) + max(lons)) / 2.0
        dt = datetime.strptime(mtl['DATE_ACQUIRED'] + ' ' + mtl['SCENE_CENTER_TIME'][:-2], '%Y-%m-%d %H:%M:%S.%f')
        try:
            clouds = float(mtl['CLOUD_COVER'])
        except:
            clouds = 0

        filenames = []
        gain = []
        offset = []
        dynrange = []
        for i, b in enumerate(smeta['bands']):
            minval = int(float(mtl['QUANTIZE_CAL_MIN_BAND_' + b]))
            maxval = int(float(mtl['QUANTIZE_CAL_MAX_BAND_' + b]))
            minrad = float(mtl['RADIANCE_MINIMUM_BAND_' + b])
            maxrad = float(mtl['RADIANCE_MAXIMUM_BAND_' + b])
            gain.append((maxrad - minrad) / (maxval - minval))
            offset.append(minrad)
            dynrange.append((minval, maxval))
            filenames.append(mtl['FILE_NAME_BAND_' + b].strip('\"'))

        _geometry = {
            'solarzenith': (90.0 - float(mtl['SUN_ELEVATION'])),
            'solarazimuth': float(mtl['SUN_AZIMUTH']),
            'zenith': 0.0,
            'azimuth': 180.0,
            'lat': lat,
            'lon': lon,
        }

        # TODO - now that metadata part of LandsatData object some of these keys not needed
        self.metadata = {
            'filenames': filenames,
            'gain': gain,
            'offset': offset,
            'dynrange': dynrange,
            'geometry': _geometry,
            'datetime': dt,
            'JulianDay': (dt - datetime(dt.year, 1, 1)).days + 1,
            'clouds': clouds
        }
        #self.metadata.update(smeta)

    @classmethod
    def meta_dict(cls):
        meta = super(LandsatData, cls).meta_dict()
        meta['GIPS-landsat Version'] = __version__
        return meta

    def _readraw(self):
        """ Read in Landsat bands using original tar.gz file """
        start = datetime.now()
        # make sure metadata is loaded
        self.meta()

        # Extract all files
        datafiles = self.assets[''].extract(self.metadata['filenames'])

        image = gippy.GeoImage(datafiles)
        image.SetNoData(0)

        # TODO - set appropriate metadata
        #for key,val in meta.iteritems():
        #    image.SetMeta(key,str(val))

        # Geometry used for calculating incident irradiance
        colors = self.assets['']._sensors[self.sensor]['colors']
        for bi in range(0, len(self.metadata['filenames'])):
            image.SetBandName(colors[bi], bi + 1)
            # need to do this or can we index correctly?
            band = image[bi]
            band.SetGain(self.metadata['gain'][bi])
            band.SetOffset(self.metadata['offset'][bi])
            dynrange = self.metadata['dynrange'][bi]
            band.SetDynamicRange(dynrange[0], dynrange[1])
            image[bi] = band

        VerboseOut('%s: read in %s' % (image.Basename(), datetime.now() - start), 2)
        return image

    @classmethod
    def extra_arguments(cls):
        return {
            '--%clouds': {
                'dest': 'pclouds',
                'help': 'Threshold of max %% cloud cover',
                'default': 100,
                'type': int
            },
        }


def main():
    DataInventory.main(LandsatData)
