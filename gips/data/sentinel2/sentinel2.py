#!/usr/bin/env python
################################################################################
#    GIPS: Geospatial Image Processing System
#
#    Copyright (C) 2017 Applied Geosolutions
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

from __future__ import print_function

import math
import os
import shutil
import sys
import datetime
import shlex
import re
import subprocess
import json
import tempfile
import zipfile
import copy
import glob
from itertools import izip_longest
from xml.etree import ElementTree, cElementTree

import numpy
import pyproj
import requests
from requests.auth import HTTPBasicAuth
from shapely.wkt import loads as wkt_loads

import gippy
import gippy.algorithms

from gips.data.core import Repository, Asset, Data
from gips import utils
from gips import atmosphere


"""Steps for adding a product to this driver:

* add the product to the _products dict
* make a $prod_geoimage() method to generate the GeoImage; follow pattern of others.
* add a stanza to the conditional below where $prod_geoimage is called.
* add the product to the dependency dict above.
* if atmo correction is in use:
    * save its metadata (see 'ref' for a pattern)
    * add the product to the conditional for metadata in the file-saving block
* update system tests
"""

_asset_type = 'L1C' # only one for the whole driver for now


class sentinel2Repository(Repository):
    name = 'Sentinel2'
    description = 'Data from the Sentinel 2 satellite(s) from the ESA'
    # when looking at the tiles shapefile, what's the key to fetch a feature's tile ID?
    _tile_attribute = 'Name'

    @classmethod
    def tile_lat_lon(cls, tileid):
        """Returns the coordinates of the given tile ID.

        Uses the reference tile vectors provided with the driver.
        Returns (x0, x1, y0, y1), which is
        (west lon, east lon, south lat, north lat) in degrees.
        """
        e = utils.open_vector(cls.get_setting('tiles'), cls._tile_attribute)[tileid].Extent()
        return e.x0(), e.x1(), e.y0(), e.y1()


class sentinel2Asset(Asset):
    Repository = sentinel2Repository

    _sensors = {
        'S2A': {
            'description': 'Sentinel-2, Satellite A',
            # Note all these lists are aligned with eachother, so that GREEN is band 3, and has
            # bandwidth 0.035.
            # found in the granule filenames
            'band-strings':
                ['01', '02', '03', '04', '05', '06',
                 '07', '08', '8A', '09', '10', '11', '12'],
            # for GIPS' & gippy's use, not inherent to driver
            'colors':
                ["COASTAL",  "BLUE", "GREEN",    "RED", "REDEDGE1", "REDEDGE2",
                 "REDEDGE3", "NIR",  "REDEDGE4", "WV",  "CIRRUS",   "SWIR1",    "SWIR2"],
            # center wavelength of band in micrometers, CF:
            # https://earth.esa.int/web/sentinel/user-guides/sentinel-2-msi/resolutions/radiometric
            'bandlocs':
                [0.443, 0.490, 0.560, 0.665, 0.705, 0.740,
                 0.783, 0.842, 0.865, 0.945, 1.375, 1.610, 2.190],
            # width of band, evenly split in the center by bandloc:
            # https://earth.esa.int/web/sentinel/user-guides/sentinel-2-msi/resolutions/radiometric
            'bandwidths':
                [0.020, 0.065, 0.035, 0.030, 0.015, 0.015,
                 0.020, 0.115, 0.020, 0.020, 0.030, 0.090, 0.180],
            'bandbounds':
                # low and high boundaries of each band; formatted this way to match other lists
                [(0.433, 0.453), (0.4575, 0.5225), (0.5425, 0.5775), (0.65, 0.68),
                    (0.6975, 0.7125), (0.7325, 0.7475),
                 (0.773, 0.793), (0.7845, 0.8995), (0.855, 0.875), (0.935, 0.955), (1.36, 1.39),
                    (1.565, 1.655), (2.1, 2.28)],
            # in meters per https://sentinel.esa.int/web/sentinel/user-guides/sentinel-2-msi/resolutions/spatial
            'spatial-resolutions':
                [60, 10, 10, 10, 20, 20,
                 20, 10, 20, 60, 60, 20, 20],
            # 'E': None  # S.B. Pulled from asset metadata file
            # 'tcap': _tcapcoef,

            # colors needed for computing indices products such as NDVI
            # color names are ['BLUE', 'GREEN', 'RED', 'NIR', 'SWIR1', 'SWIR2']
            'indices-bands': ['02', '03', '04', '05', '06',
                              '07', '08', '8A', '11', '12'],
            # similar to landsat's "visbands"
            'indices-colors': ['BLUE', 'GREEN', 'RED',
                               'REDEDGE1', 'REDEDGE2', 'REDEDGE3',
                               'NIR', 'REDEDGE4', 'SWIR1', 'SWIR2'],
        },
    }
    _sensors['S2B'] = copy.deepcopy(_sensors['S2A'])
    _sensors['S2B']['description'] = 'Sentinel-2, Satellite B'

    _assets = {
        'L1C': {
            # 'pattern' is used for searching the repository of locally-managed assets; this pattern
            # is used for both original and shortened post-2016-12-07 assets.
            'pattern': '^.*S2._.*MSIL1C_.*.{8}T.{6}_.*R..._.*\.zip$',
            # TODO find real start date for S2 data:
            # https://scihub.copernicus.eu/dhus/search?q=filename:S2?*&orderby=ingestiondate%20asc
            # (change to orderby=ingestiondate%20desc if needed)
            'startdate': datetime.date(2015, 1, 1), # used to prevent
            # impossible searches
            # TODO: (may need to change -- nigeria work shows no
            # imagery before August 2015)
            'latency': 3, # actually seems to be 3,7,3,7..., but this value seems to be unused;
                          # only needed by Asset.end_date and Asset.available, but those are never called?
        },

    }

    _2016_12_07 = datetime.datetime(2016, 12, 7, 0, 0) # first day of new-style assets, UTC

    # regexes for verifying filename correctness & extracting metadata; convention:
    # https://sentinels.copernicus.eu/web/sentinel/user-guides/sentinel-2-msi/naming-convention
    _tile_re = '(?P<tile>\d\d[A-Z]{3})'
    # example, note that leading tile code is spliced in by Asset.fetch:
    # 19TCH_S2A_OPER_PRD_MSIL1C_PDMC_20170221T213809_R050_V20151123T091302_20151123T091302.zip
    _orig_name_re = (
        '(?P<sensor>S2[AB])_OPER_PRD_MSIL1C_....' # sensor
        '_(?P<pyear>\d{4})(?P<pmon>\d\d)(?P<pday>\d\d)' # processing date
        'T(?P<phour>\d\d)(?P<pmin>\d\d)(?P<psec>\d\d)' # processing time
        '_R(?P<rel_orbit>\d\d\d)' # relative orbit, not sure if want
        # observation datetime:
        '_V(?P<year>\d{4})(?P<mon>\d\d)(?P<day>\d\d)' # year, month, day
        'T(?P<hour>\d\d)(?P<min>\d\d)(?P<sec>\d\d)' # hour, minute, second
        '_\d{8}T\d{6}.zip') # repeated observation datetime for no known reason

    _2016_12_07_name_re = (
        '^(?P<sensor>S2[AB])_MSIL1C_' # sensor
        '(?P<year>\d{4})(?P<mon>\d\d)(?P<day>\d\d)' # year, month, day
        'T(?P<hour>\d\d)(?P<min>\d\d)(?P<sec>\d\d)' # hour, minute, second
        '_N\d{4}_R\d\d\d_T' + _tile_re +  # tile
        '_(?P<pyear>\d{4})(?P<pmon>\d\d)(?P<pday>\d\d)' # processing date
        'T(?P<phour>\d\d)(?P<pmin>\d\d)(?P<psec>\d\d)' # processing time
        '.zip$'
    )

    _asset_styles = {
        'original': {
            # original-style assets can't use the same name for downloading and archiving, because
            # each downloaded file contains multiple tiles of data
            'downloaded-name-re': _orig_name_re,
            'archived-name-re': '^' + _tile_re + '_' + _orig_name_re,
            # raster file pattern
            # TODO '/.*/' can be misleading due to '/' satisfying '.', so rework into '/[^/]*/'
            'raster-re': r'^.*/GRANULE/.*/IMG_DATA/.*_T{tileid}_B(?P<band>\d[\dA]).jp2$',
            ## internal metadata file patterns
            # updated assumption: only XML file in DATASTRIP/ (not including subdirs)
            'datastrip-md-re': '^.*/DATASTRIP/[^/]+/[^/]*.xml$',
            'tile-md-re': '^.*/GRANULE/.*_T{tileid}_.*/.*_T{tileid}.xml$',
            'asset-md-re': '^.*/S2.*\.xml$',
        },
        _2016_12_07: {
            # post-2016 assets use their downloaded FN as their archived FN
            'downloaded-name-re': _2016_12_07_name_re,
            'archived-name-re': _2016_12_07_name_re,
            # raster file pattern
            'raster-re': '^.*/GRANULE/.*/IMG_DATA/.*_B(?P<band>\d[\dA]).jp2$',
            # internal metadata file patterns
            'datastrip-md-re': '^.*/DATASTRIP/.*/MTD_DS.xml$',
            'tile-md-re': '^.*/GRANULE/.*/MTD_TL.xml$',
            # Two files with asset-global metadata, this is one of them:
            # for INSPIRE.xml see http://inspire.ec.europa.eu/XML-Schemas/Data-Specifications/2892
            'inspire-md-re': '^.*/INSPIRE.xml$',
            'asset-md-re': '^.*/MTD_MSIL1C.xml$',
        },
    }

    # default resultant resolution for resampling during to Data().copy()
    _defaultresolution = (10, 10)

    def __init__(self, filename):
        """Inspect a single file and set some metadata.

        Both shortened and original longer file name & content structure are supported:
        https://sentinels.copernicus.eu/web/sentinel/user-guides/sentinel-2-msi/naming-convention
        """
        super(sentinel2Asset, self).__init__(filename)
        with utils.error_handler("Error opening asset '({})'".format(filename)):
            if os.path.exists(filename):  # __init__ should work even if file doesn't exist
                zipfile.ZipFile(filename)  # exception if file isn't a valid zip
        base_filename = os.path.basename(filename)

        for style, style_dict in self._asset_styles.items():
            match = re.match(style_dict['archived-name-re'], base_filename)
            if match is not None:
                break
        if match is None:
            raise IOError("Asset file name is incorrect for Sentinel-2: '{}'".format(base_filename))
        self.style = style
        self.asset = 'L1C' # only supported asset type
        self.sensor = match.group('sensor')
        self.tile = match.group('tile')
        self.date = datetime.date(*[int(i) for i in match.group('year', 'mon', 'day')])
        self.time = datetime.time(*[int(i) for i in match.group('hour', 'min', 'sec')])
        self.set_style_regular_expressions()
        self._version = int(''.join(
            match.group('pyear', 'pmon', 'pday', 'phour', 'pmin', 'psec')
        ))
        self.meta = {} # for caching asset metadata values


    def set_style_regular_expressions(self):
        """Sets self.style_res dict.

        This lets the asset object locate internal metadata by setting
        patterns appropriate for the asset's style.
        """
        sr = self.style_res = copy.deepcopy(self._asset_styles[self.style])
        if self.style == 'original':
            self.style_res['tile-md-re'] = sr['tile-md-re'].format(tileid=self.tile)
            self.style_res['datastrip-md-re'] = sr['datastrip-md-re'].format(tileid=self.tile)

    @classmethod
    def query_scihub(cls, style, tile, date):
        username = cls.Repository.get_setting('username')
        password = cls.Repository.get_setting('password')

        year, month, day = date.timetuple()[:3]
        # search step:  locate the asset corresponding to (asset, tile, date)
        url_head = 'https://scihub.copernicus.eu/dhus/search?q='
        #                vvvvvvvv--- sort by processing date so always get the newest one
        url_tail = '&orderby=ingestiondate desc&format=json'
        if style == 'original':
            # compute the center coordinate of the tile
            x0, x1, y0, y1 = cls.Repository.tile_lat_lon(tile)
            lat, lon = (y0 + y1)/2, (x0 + x1)/2
            #                                                  year mon  day
            url_search_string = ('filename:S2?_OPER_PRD_MSIL1C_*_{}{:02}{:02}T??????.SAFE'
                                 '%20AND%20footprint:%22Intersects({},%20{})%22') # <-- lat/lon
            search_url = url_head + url_search_string.format(year, month, day, lat, lon) + url_tail
        else:
            #                                      year mon  day                    tile
            url_search_string = 'filename:S2?_MSIL1C_{}{:02}{:02}T??????_N????_R???_T{}_*.SAFE'
            search_url = url_head + url_search_string.format(year, month, day, tile) + url_tail

        auth = HTTPBasicAuth(username, password)
        r = requests.get(search_url, auth=auth, verify=False)
        r.raise_for_status()
        return r.json()

    @classmethod
    def query_provider(cls, asset, tile, date, pclouds=100, **fetch_kwargs):
        """Search for a matching asset in the Sentinel-2 servers.

        Uses the given (asset, tile, date) tuple as a search key, and
        returns a tuple (base-filename-of-asset, url-for-fetching).  If
        no assets were found, returns (None, None).
        """
        # set up fetch params
        style = 'original' if date < cls._2016_12_07 else cls._2016_12_07

        # search for the asset's URL with wget call (using a suprocess call to wget instead of a
        # more conventional call to a lib because available libs are perceived to be inferior).
        with utils.error_handler("Error performing asset search '({} {} {})'".format(asset, tile, date.strftime("%Y%j"))):
            results = cls.query_scihub(style, tile, date)['feed'] # always top-level key

            result_count = int(results['opensearch:totalResults'])
            if result_count == 0:
                return None, None # nothing found, a normal occurence for eg date range queries
            # unfortunately the data's structure varies with the result count
            if result_count == 1:
                entry = results['entry']
            else: # result_count > 1
                utils.verbose_out(
                        "Query returned {} results; choosing the newest.".format(result_count))
                entry = results['entry'][0]

            if 'rel' in entry['link'][0]: # sanity check - the right one doesn't have a 'rel' attrib
                raise IOError("Unexpected 'rel' attribute in search link")
            asset_url = entry['link'][0]['href']
            output_file_name = entry['title'] + '.zip'

        if pclouds < 100:
            asset = cls(output_file_name)
            if not asset.filter(pclouds):
                return None, None

        return output_file_name, asset_url


    @classmethod
    def fetch(cls, asset, tile, date, pclouds=100, **fetch_kwargs):
        """Fetch the asset corresponding to the given asset type, tile, and date."""
        qs_rv = cls.query_service(asset, tile, date)
        if qs_rv is None:
            return []
        output_file_name, asset_url = (qs_rv['basename'], qs_rv['url'])

        # old-style assets cover many tiles, so there may be duplication of
        # effort; avoid that by aborting if the stage already contains the
        # desired asset
        full_staged_path = os.path.join(cls.Repository.path('stage'),
                                        output_file_name)
        if os.path.exists(full_staged_path):
            utils.verbose_out('Asset `{}` needed but already in stage/,'
                              ' skipping.'.format(output_file_name))
            return []

        username = cls.Repository.get_setting('username')
        password = cls.Repository.get_setting('password')
        # download the asset via the asset URL, putting it in a temp folder, then move to the stage
        # if the download is successful (this is necessary to avoid a race condition between
        # archive actions and fetch actions by concurrent processes)
        fetch_cmd_template = ('wget --no-check-certificate --user="{}" --password="{}" --timeout=30'
                              ' --no-verbose --output-document="{}" "{}"')
        if gippy.Options.Verbose() != 0:
            fetch_cmd_template += ' --show-progress --progress=dot:giga'
        utils.verbose_out("Fetching " + output_file_name)
        with utils.error_handler("Error performing asset download '({})'".format(asset_url)):
            tmp_dir_full_path = tempfile.mkdtemp(dir=cls.Repository.path('stage'))
            try:
                output_full_path = os.path.join(tmp_dir_full_path, output_file_name)
                fetch_cmd = fetch_cmd_template.format(
                        username, password, output_full_path, asset_url)
                args = shlex.split(fetch_cmd)
                p = subprocess.Popen(args)
                p.communicate()
                if p.returncode != 0:
                    raise IOError("Expected wget exit status 0, got {}".format(p.returncode))
                cls.stage_asset(output_full_path, output_file_name)
            finally:
                shutil.rmtree(tmp_dir_full_path) # always remove the dir even if things break
        return [output_full_path]


    @classmethod
    def archive(cls, path, recursive=False, keep=False, update=False):
        """Archive original and new-style Sentinel-2 assets.

        Original-style Sentinel-2 assets have special archiving needs
        due to their multi-tile nature, so this method archives them
        specially using hard links.
        """
        if recursive:
            raise ValueError('Recursive asset search not supported by Sentinel-2 driver.')

        found_files = {
            'original': [],
            cls._2016_12_07: [],
        }

        for fn in utils.find_files(cls._assets['L1C']['pattern'], path):
            with utils.error_handler('Error archiving asset', continuable=True):
                bn = os.path.basename(fn)
                for style, style_dict in cls._asset_styles.items():
                    match = re.match(style_dict['downloaded-name-re'], bn)
                    if match is not None:
                        found_files[style].append(fn) # save the found path, not the basename
                        break
                if match is None:
                    raise IOError("Asset file name is incorrect for Sentinel-2: '{}'".format(bn))

        assets = []
        overwritten_assets = []
        for fn in found_files[cls._2016_12_07]:
            new_aol, new_overwritten_aol = super(sentinel2Asset, cls).archive(
                    fn, False, keep, update)
            assets += new_aol
            overwritten_assets += new_overwritten_aol

        for fn in found_files['original']:
            tile_list = cls.tile_list(fn)
            # use the stage dir since it's likely not to break anything (ie on same filesystem)
            with utils.make_temp_dir(dir=cls.Repository.path('stage')) as tdname:
                for tile in tile_list:
                    tiled_fp = os.path.join(tdname, tile + '_' + os.path.basename(fn))
                    os.link(fn, tiled_fp)
                orig_aol, orig_overwritten_aol = (
                        super(sentinel2Asset, cls).archive(
                                tdname, False, False, update))
                assets += orig_aol
                overwritten_assets += orig_overwritten_aol
            if not keep:
                utils.RemoveFiles([fn], ['.index', '.aux.xml'])

        return assets, overwritten_assets


    @classmethod
    def stage_asset(cls, asset_full_path, asset_base_name):
        """Copy the given asset to the stage."""
        stage_path = cls.Repository.path('stage')
        stage_full_path = os.path.join(stage_path, asset_base_name)
        os.rename(asset_full_path, stage_full_path) # on POSIX, if it works, it's atomic


    @classmethod
    def tile_list(cls, file_name):
        """Extract a list of tiles from the given old-style asset."""
        # find an xml file with a very long name in the top-level .SAFE/ directory
        # eg
        # S2A_OPER_MTD_SAFL1C_PDMC_20161030T191653_R079_V20161030T095132_20161030T095132.xml
        tiles = set()
        file_pattern = cls._asset_styles['original']['raster-re'].format(tileid=cls._tile_re)
        p = re.compile(file_pattern)
        with zipfile.ZipFile(file_name) as asset_zf:
            for f in asset_zf.namelist():
                m = p.match(f)
                if m:
                    tiles.add(m.group('tile'))
        if not tiles:
            raise Exception(
                'Datastrip asset contains no tiles???? ({})'
                .format(file_name)
            )
        return list(tiles)


    def cloud_cover(self):
        """Returns cloud cover for the current asset.

        Caches and returns the value found in self.meta['cloud-cover']."""
        if 'cloud-cover' in self.meta:
            return self.meta['cloud-cover']
        if os.path.exists(self.filename):
            with utils.make_temp_dir() as tmpdir:
                metadata_file = [
                    f for f in self.datafiles()
                    if re.match(self.style_res['tile-md-re'], f)
                ][0]
                self.extract([metadata_file], path=tmpdir)
                tree = ElementTree.parse(tmpdir + '/' + metadata_file)
            root = tree.getroot()
            nsre = r'^({.+})Level-1C_Tile_ID$'
            cloud_cover_xpath = "./{}Quality_Indicators_Info/Image_Content_QI/CLOUDY_PIXEL_PERCENTAGE"

            for el in root.iter():
                match = re.match(nsre, el.tag)
                ns = False
                if match:
                    ns = match.group(1)
                    break
                if not ns:
                    raise Exception("Tile metadata xml namespace could not be found")
            cloud_coverage_el = root.findall(cloud_cover_xpath.format(ns))[0]
            self.meta['cloud-cover'] = float(cloud_coverage_el.text)

            return self.meta['cloud-cover']
        else:
            results = self.query_scihub(self.style, self.tile, self.date)

            if 'entry' in results['feed']:
                # TODO: This assertion is occasionally false.  'entry'
                #       sometimes points at a list, instead of a dict.
                #       Make this jive with the API better.
                if type(results['feed']['entry']) is list:
                    entry = results['feed']['entry'][0]
                else:
                    entry = results['feed']['entry']
                assert entry['double']['name'] == 'cloudcoverpercentage'
                return float(entry['double']['content'])
            raise ValueError("%s doesn't exist locally or remotely" % self.filename)

    def filter(self, pclouds=100, **kwargs):
        if pclouds >= 100:
            return True
        cc = self.cloud_cover()
        asset_passes_filter = cc <= pclouds
        if asset_passes_filter:
            msg = 'Asset cloud cover is {} %, meets pclouds threshold of {} %'
        else:
            msg = ('Asset cloud cover is {} %,'
                   ' fails to meet pclouds threshold of {} %')
        utils.verbose_out(msg.format(cc, pclouds), 3)
        return asset_passes_filter

    def xml_subtree(self, md_file_type, subtree_tag):
        """Loads XML, then returns the given Element from it.

        File to read is specified by type eg 'tile' or 'datastrip'.  The first
        matching tag in the XML tree is returned.  The metadata file is located
        in self.style_res eg 'tile' results in 'tile-md-re' being used.
        """
        file_pattern = self.style_res[md_file_type + '-md-re']
        # python idiom for "first item in list that satisfies a condition"
        metadata_fn = next(fn for fn in self.datafiles() if re.match(file_pattern, fn))
        with zipfile.ZipFile(self.filename) as asset_zf:
            with asset_zf.open(metadata_fn) as metadata_zf:
                tree = ElementTree.parse(metadata_zf)
                return next(tree.iter(subtree_tag))


    def solar_irradiances(self):
        """Loads solar irradiances from asset metadata and returns them.

        The order of the list matches the band list above.  Irradiance
        values are in watts/(m^2 * micrometers).  Wikipedia claims it is
        really "spectral flux density" and measures the power flowing onto
        a surface per unit wavelength:
        https://en.wikipedia.org/wiki/Spectral_flux_density
        """
        sil_elem = self.xml_subtree('datastrip', 'Solar_Irradiance_List')
        values_tags = sil_elem.findall('SOLAR_IRRADIANCE')
        # sanity check that the bands are in the right order
        assert range(13) == [int(vt.attrib['bandId']) for vt in values_tags]
        return [float(vt.text) for vt in values_tags]


    def mean_viewing_angle(self, angle='both'):
        """Loads & returns mean viewing angle:  (zenith, azimuth).

        Queries and returns asset metadata for these values.  Return
        value is in degrees.
        """
        if angle != 'both':
            raise NotImplementedError('getting zenith or azimuth separately is not supported')
        mvial_elem = self.xml_subtree('tile', 'Mean_Viewing_Incidence_Angle_List')
        # should only be one list, with 13 elems, each with 2 angles, a zen and an az
        angles = mvial_elem.findall('Mean_Viewing_Incidence_Angle')
        mean_zen = numpy.mean([float(e.find('ZENITH_ANGLE' ).text) for e in angles])
        mean_az  = numpy.mean([float(e.find('AZIMUTH_ANGLE').text) for e in angles])
        return (mean_zen, mean_az)


    def mean_solar_angle(self, angle='both'):
        """Loads & returns solar zenith and/or azimuth angle.

        Queries and returns asset metadata for these values.  Set angle
        to 'zenith' or 'azimuth' to get single values, or 'both' to get
        (zenith, azimuth).  Return value is in degrees.
        """
        assert angle in ('both', 'zenith', 'azimuth') # sanity check
        msa_elem = self.xml_subtree('tile', 'Mean_Sun_Angle')
        get_angle = lambda tag: float(msa_elem.find(tag).text)
        if angle == 'both':
            return (get_angle('ZENITH_ANGLE'), get_angle('AZIMUTH_ANGLE'))
        if angle == 'zenith':
            return get_angle('ZENITH_ANGLE')
        if angle == 'azimuth':
            return get_angle('AZIMUTH_ANGLE')


    def tile_lat_lon(self):
        """Loads & returns boundaries for this asset's tile.

        If the asset is old-style, it's taken from the tiles shapefile.
        Otherwise, taken from asset metadata; tuple is (w-lon, e-lon,
        s-lat, n-lat), in degrees.  Structure for the lat/lons in
        INSPIRE.xml is, deep in the file:
            <gmd:EX_GeographicBoundingBox>
                <gmd:westBoundLongitude>
                    <gco:Decimal>-71.46678204877877</gco:Decimal>
                </gmd:westBoundLongitude>
                . . . and so on for 3 more values . . .
            </gmd:EX_GeographicBoundingBox>
        """
        if self.style == 'original':
            return self.Repository.tile_lat_lon(self.tile)
        gmd = '{http://www.isotc211.org/2005/gmd}' # xml namespace foolishness
        gco = '{http://www.isotc211.org/2005/gco}'
        gbb_elem = self.xml_subtree('inspire', gmd + 'EX_GeographicBoundingBox')
        return tuple(float(gbb_elem.find(gmd + s).find(gco + 'Decimal').text) for s in (
                'westBoundLongitude', 'eastBoundLongitude',
                'southBoundLatitude', 'northBoundLatitude',
        ))


    #def gridded_zenith_angle(self):
    #    """Loads and returns zenith angle from the asset metadata.
    #
    #    These are stored in MTD_TL.xml, in degrees, at 5km x 5km resolution.
    #    """
    #    asset_contents = self.datafiles()
    #    # python idiom for "first item in list that satisfies a condition"; should only be one
    #    metadata_fn = next(n for n in asset_contents if re.match('^.*/GRANULE/.*/MTD_TL.xml$', n))
    #    with zipfile.ZipFile(self.filename) as asset_zf:
    #        with asset_zf.open(metadata_fn) as metadata_zf:
    #            tree = ElementTree.parse(metadata_zf)
    #            sag_elem = next(tree.iter('Sun_Angles_Grid')) # should only be one
    #            values_tags = sag_elem.find('Zenith').find('Values_List').findall('VALUES')
    #            text_rows = [vt.text for vt in values_tags]
    #            zenith_grid = []
    #            for tr in text_rows:
    #                numerical_row = [float(t) for t in tr.split()]
    #                zenith_grid.append(numerical_row)
    #    return zenith_grid


    def radiance_factors(self):
        """Computes values needed for converting L1C to TOA radiance.

        Sentinel-2's L1C is a TOA reflectance product.  That can be
        reverted to a TOA radiance product by multiplying each data
        point by a constant factor.  The factor is constant for each
        band of a given asset; the ordering in the returned list is the
        same as the order of the bands in _sensors given above.  See:
        https://sentinel.esa.int/web/sentinel/technical-guides/sentinel-2-msi/level-1c/algorithm
        """
        mza = math.radians(self.mean_solar_angle('zenith'))
        solar_irrads = self.solar_irradiances()
        julian_date = utils.julian_date(datetime.datetime.combine(self.date, self.time), 'cnes')
        return [(1 - 0.01673 * math.cos(0.0172 * (julian_date - 2)))**-2 # solar distance term
                * math.cos(mza) / math.pi # solar angle term
                * si # "equivalent extra-terrestrial solar spectrum" term; aka solar irradiance
                / 1000.0 # revert scaling factor so 16-bit ints aren't overflowed
                for si in solar_irrads]


    def generate_atmo_corrector(self):
        """Generate & return a SIXS object appropriate for this asset.

        Re-usees a previously created object if possible.
        """
        if hasattr(self, '_atmo_corrector'):
            utils.verbose_out('Found existing atmospheric correction object, reusing it.', 4)
            return self._atmo_corrector
        utils.verbose_out('Generating atmospheric correction object.', 4)
        sensor_md = self._sensors[self.sensor]
        visbands = sensor_md['indices-colors'] # TODO visbands isn't really the right name
        vb_indices = [sensor_md['colors'].index(vb) for vb in visbands]
        # assemble list of relevant band boundaries
        wvlens = [sensor_md['bandbounds'][i] for i in vb_indices]
        # assemble geometries
        (viewing_zn, viewing_az) = self.mean_viewing_angle()
        (solar_zn, solar_az) = self.mean_solar_angle()
        (w_lon, e_lon, s_lat, n_lat) = self.tile_lat_lon()
        geo = {
            'zenith': viewing_zn,
            'azimuth': viewing_az,
            'solarzenith': solar_zn,
            'solarazimuth': solar_az,
            'lon': (w_lon + e_lon) / 2.0, # copy landsat - use center of tile
            'lat': (s_lat + n_lat) / 2.0, # copy landsat - use center of tile
        }
        dt = datetime.datetime.combine(self.date, self.time)
        self._atmo_corrector = atmosphere.SIXS(visbands, wvlens, geo, dt, sensor=self.sensor)
        return self._atmo_corrector

    def footprint(self):
        asset_contents = self.datafiles()

        mtd_file_pattern = self._asset_styles[self.style]['asset-md-re']
        metadata_fn = next(n for n in asset_contents if re.match(mtd_file_pattern, n))

        metadata_zf = next(iter(self.extract([metadata_fn])))
        tree = ElementTree.parse(metadata_zf)
        sag_elem = next(tree.iter('Global_Footprint')) #      should only be one
        values_tags = sag_elem.find('EXT_POS_LIST')

        # format as valid WKT
        points = values_tags.text.strip().split(" ")
        zipped_points = izip_longest(*[iter(points)]*2)  # fancy way to group list into pairs
        wkt_points = ", ".join([y + " " + x for x, y in list(zipped_points)])
        footprint_wkt = "POLYGON (({}))".format(wkt_points)

        # For old style assets, `Global_Footprint` is the entire swath,
        # so intersect it with tile boundary to get actual footprint.
        tile_polygon = wkt_loads(self.get_geometry())
        return tile_polygon.intersection(wkt_loads(footprint_wkt)).wkt


class sentinel2Data(Data):
    name = 'Sentinel2'
    version = '0.1.1'
    Asset = sentinel2Asset

    _productgroups = {
        'Index': [
            'ndvi', 'evi', 'lswi', 'ndsi', 'bi', 'satvi', 'msavi2', 'vari',
            'brgt', 'ndti', 'crc', 'crcm', 'isti', 'sti',
        ],
        'ACOLITE': ['rhow', 'oc2chl', 'oc3chl', 'fai',
                    'spm655', 'turbidity', 'acoflags'],
    }

    _products = {
        # standard products
        'rad': {
            'description': 'Surface-leaving radiance',
            'assets': [_asset_type],
            'bands': [{'name': band_name, 'units': 'W/m^2/um'} # aka watts/(m^2 * micrometers)
                      for band_name in Asset._sensors['S2A']['indices-colors']],
            # 'startdate' and 'latency' are optional for DH
        },
        'ref': {
            'description': 'Surface reflectance',
            'assets': [_asset_type],
            'bands': [{'name': band_name, 'units': Data._unitless}
                      for band_name in Asset._sensors['S2A']['indices-colors']],
        },
        'cfmask': {
            'description': 'Cloud, cloud shadow, and water classification',
            'assets': [_asset_type],
            'bands': {'name': 'cfmask', 'units': Data._unitless},
            'toa': True,
        },
        'cloudmask': {
            'description': 'Cloud mask',
            'assets': [_asset_type],
            'bands': {'name': 'cloudmask', 'units': Data._unitless},
        },
    }

    # add index products to _products
    _products.update(
        (p, {'description': d,
             'assets': [_asset_type],
             'bands': [{'name': p, 'units': Data._unitless}]}
        ) for p, d in [
            # duplicated in modis and landsat; may be worth it to DRY out
            ('ndvi',   'Normalized Difference Vegetation Index'),
            ('evi',    'Enhanced Vegetation Index'),
            ('lswi',   'Land Surface Water Index'),
            ('ndsi',   'Normalized Difference Snow Index'),
            ('bi',     'Brightness Index'),
            ('satvi',  'Soil-Adjusted Total Vegetation Index'),
            ('msavi2', 'Modified Soil-adjusted Vegetation Index'),
            ('vari',   'Visible Atmospherically Resistant Index'),
            ('brgt',   'VIS and NIR reflectance, weighted by solar energy distribution.'),
            # index products related to tillage
            ('ndti',   'Normalized Difference Tillage Index'),
            ('crc',    'Crop Residue Cover (uses BLUE)'),
            ('crcm',   'Crop Residue Cover, Modified (uses GREEN)'),
            ('isti',   'Inverse Standard Tillage Index'),
            ('sti',    'Standard Tillage Index'),
            # not processed by gippy.Indices() but still indices products:
            ('mtci',    'MERIS Terrestrial Chlorophyll Index'),
            ('s2rep',   'Sentinel-2 Red Edge Position'),
        ]
    )

    atmosphere.add_acolite_product_dicts(_products, _asset_type)

    _product_dependencies = {
        'indices':      'ref',
        'indices-toa':  'ref-toa',
        'ref':          'rad-toa',
        'rad':          'rad-toa',
        'rad-toa':      'ref-toa',
        'ref-toa':      None, # has no deps but the asset
        'cfmask':       None,
        'mtci-toa':     'ref-toa',
        's2rep-toa':    'ref-toa',
        'mtci':         'ref',
        's2rep':        'ref',
	'cloudmask':	'cfmask',
    }

    need_fetch_kwargs = True

    @classmethod
    def need_to_fetch(cls, a_type, tile, date, update, **fetch_kwargs):
        if date < sentinel2Asset._2016_12_07:
            # must be an original-style asset, which has many tiles at
            # query time, so there's no easy way to tell if we can skip the
            # download or not.  So, just assume the worst and fetch it.
            return True
        return super(sentinel2Data, cls).need_to_fetch(
                a_type, tile, date, update, **fetch_kwargs)

    def plan_work(self, requested_products, overwrite):
        """Plan processing run using requested products & their dependencies.

        Returns a set of processing steps needed to generate
        requested_products.  For instance, 'rad-toa' depends on
        'ref-toa', so if the user requests 'rad-toa', set(['rad-toa',
        'ref-toa']) is returned.  But if 'ref-toa' is already in the
        inventory, it is omitted, unless overwrite is True.
        requested_products should contain strings matching
        _product_dependencies above.
        """
        surf_indices = self._productgroups['Index']
        toa_indices  = [i + '-toa' for i in self._productgroups['Index']]
        acolite_products = self._productgroups['ACOLITE']
        _pd = self._product_dependencies
        work = set()
        for rp in requested_products:
            # handle indices specially
            if rp in surf_indices:
                prereq = 'indices'
            elif rp in toa_indices:
                prereq = 'indices-toa'
            elif rp in acolite_products:
                prereq = None
            else:
                if rp not in _pd:
                    raise ValueError(
                            'Could not find dependency listing for ' + rp)
                prereq = rp
            # go thru each prereq and add it in if it's not already present, respecting overwrite.
            while prereq in _pd and (overwrite or prereq not in self.products):
                work.add(prereq)
                prereq = _pd[prereq]
        return work

    def current_asset(self):
        return self.assets[_asset_type]

    def current_sensor(self):
        return self.sensors[_asset_type]


    def load_image(self, product):
        """Load a product file into a GeoImage and return it

        The GeoImage is instead fetched from a cache if possible.
        (sensor, product) should match an entry from self.filenames.
        """
        if product in self._product_images:
            return self._product_images[product]
        image = gippy.GeoImage(self.filenames[(self.current_sensor(), product)])
        self._product_images[product] = image
        return image


    @classmethod
    def normalize_tile_string(cls, tile_string):
        """Sentinel-2 customized tile-string normalizer.

        Raises an exception if the tile string doesn't match MGRS
        format, and converts the tile string to uppercase.
        """
        if not re.match(r'^\d\d[a-zA-Z]{3}$', tile_string):
            err_msg = "Tile string '{}' doesn't match MGRS format (eg '04QFJ')".format(tile_string)
            raise IOError(err_msg)
        return tile_string.upper()

    @classmethod
    def add_filter_args(cls, parser):
        """Add custom filtering options for sentinel2."""
        help_str = ('cloud percentage threshold; assets with cloud cover'
                    ' percentages higher than this value will be filtered out')
        parser.add_argument('--pclouds', help=help_str,
                            type=cls.natural_percentage, default=100)

    def filter(self, pclouds=100, **kwargs):
        return all([asset.filter(pclouds, **kwargs) for asset in self.assets.values()])

    def prep_meta(self, additional=None):
        meta = super(sentinel2Data, self).prep_meta(
            self.current_asset().filename, additional)
        return meta

    def prep_meta(self, additional=None):
        meta = super(sentinel2Data, self).prep_meta(
            self.current_asset().filename, additional)
        return meta

    def load_metadata(self):
        """Ingest metadata from asset files; just raster filenames presently."""
        if hasattr(self, 'metadata'):
            return # nothing to do if metadata is already loaded

        # only one asset type supported for this driver so for now hardcoding is ok
        asset_type = 'L1C'
        datafiles = self.assets[asset_type].datafiles()

        # restrict filenames known to just the raster layers
        asset = self.current_asset()
        raster_fn_pat = asset.style_res['raster-re'].format(tileid=asset.tile)
        fnl = [df for df in datafiles if re.match(raster_fn_pat, df)]
        # have to sort the list or else gippy will get confused about which band is which
        band_strings = sentinel2Asset._sensors[self.sensors[asset_type]]['band-strings']
        # sorting is weird because the bands aren't named consistently
        fnl.sort(key=lambda f: band_strings.index(f[-6:-4]))
        self.metadata = {'filenames': fnl}


    def read_raw(self):
        """Read in bands using original SAFE asset file (a .zip)."""
        self.load_metadata()

        if utils.settings().REPOS[self.Repository.name.lower()].get('extract', False):
            # Extract files to disk
            datafiles = self.assets['L1C'].extract(self.metadata['filenames'])
        else:
            # Use zipfile directly using GDAL's virtual filesystem
            datafiles = [os.path.join('/vsizip/' + self.assets['L1C'].filename, f)
                    for f in self.metadata['filenames']]
        self.metadata['abs-filenames'] = datafiles

    def ref_toa_geoimage(self, sensor, data_spec):
        """Make a proto-product which acts as a basis for several products.

        It is equivalent to ref-toa; it's needed because the asset's
        spatial resolution must be resampled to be equal for all bands
        of interest.
        """
        # TODO data_spec can be refactored out of argslist;
        #      only depends on self & asset_type ('L1C')
        self._time_report('Start VRT for ref-toa image')
        src_filenames = [f for f in self.metadata['abs-filenames']
                         if f[-6:-4] in data_spec['indices-bands']]

        with utils.make_temp_dir() as tmpdir:
            # TODO document why VRT is superior to prior method (faster?)
            vrt_filename = os.path.join(tmpdir, self.basename + '_ref-toa.vrt')
            cmd_str = (
                'gdalbuildvrt -tr 20 20 -separate '
                '-srcnodata 0 -vrtnodata 0 {} {}'
            ).format(vrt_filename, ' '.join(src_filenames))
            cmd_args = shlex.split(cmd_str)
            p = subprocess.Popen(cmd_args)
            p.communicate()
            if p.returncode != 0:
                raise IOError("Expected gdalbuildvrt exit status 0, got {}"
                              .format(p.returncode))
            vrt_img = gippy.GeoImage(vrt_filename)
            vrt_img.SetNoData(0)
            vrt_img.SetGain(0.0001) # 16-bit storage values / 10^4 = refl values
            # eg:   3        '08'
            for band_num, band_string in enumerate(data_spec['indices-bands'], 1):
                # starts at 0
                band_index = data_spec['band-strings'].index(band_string)
                color_name = data_spec['colors'][band_index]
                vrt_img.SetBandName(color_name, band_num)
        self._product_images['ref-toa'] = vrt_img
        self._time_report('Finished VRT for ref-toa image')

    def rad_toa_geoimage(self, asset_type, sensor):
        """Reverse-engineer TOA ref data back into a TOA radiance product.

        This is used as intermediary data but is congruent to the rad-toa
        product.
        """
        self._time_report('Starting reversion to TOA radiance.')
        reftoa_img = self.load_image('ref-toa')
        asset_instance = self.assets[asset_type] # sentinel2Asset
        colors = asset_instance._sensors[sensor]['colors']

        radiance_factors = asset_instance.radiance_factors()

        rad_image = gippy.GeoImage(reftoa_img)

        for i in range(len(rad_image)):
            color = rad_image[i].Description()
            rf = radiance_factors[colors.index(color)]
            self._time_report(
                'TOA radiance reversion factor for {} (band {}): {}'.format(color, i + 1, rf))
            rad_image[i] = rad_image[i] * rf
        rad_image.SetNoData(0)
        self._product_images['rad-toa'] = rad_image


    def rad_geoimage(self):
        """Transmute TOA radiance product into a surface radiance product."""
        self._time_report('Setting up for converting radiance from TOA to surface')
        rad_toa_img = self.load_image('rad-toa')
        ca = self.current_asset()
        atm6s = ca.generate_atmo_corrector()

        rad_image = gippy.GeoImage(rad_toa_img)
        # to check the gain & other values set on the object:
        # print('rad_image info:', rad_image.Info()

        # set meta to pass along to indices
        rad_image._aod_source = str(atm6s.aod[0])
        rad_image._aod_value  = str(atm6s.aod[1])

        for c in ca._sensors[self.current_sensor()]['indices-colors']:
            (T, Lu, Ld) = atm6s.results[c] # Ld is unused for this product
            # 6SV1/Py6S/SIXS produces atmo correction values suitable
            # for raw values ("digital numbers") from landsat, but
            # rad_toa_img isn't a raw value; it has a gain.  So, apply
            # that same gain to Lu, apparently the atmosphere's
            # inherent radiance, to get a reasonable difference.
            lu = 0.0001 * Lu
            rad_image[c] = (rad_toa_img[c] - lu) / T
        self._product_images['rad'] = rad_image


    def process_indices(self, mode, sensor, indices):
        """Generate the given indices.

        gippy.algorithms.Indices is called for the given indices, using
        an image appropriate for the given mode ('toa' or not).
        """
        if len(indices) == 0:
            return

        self._time_report('Starting indices processing for: {}'.format(indices.keys()))

        metadata = self.prep_meta()
        if mode != 'toa':
            image = self.load_image('ref')
            # this faff is needed because gippy shares metadata across images behind your back
            metadata['AOD Source'] = getattr(image, '_aod_source', image.Meta('AOD Source'))
            metadata['AOD Value']  = getattr(image, '_aod_value',  image.Meta('AOD Value'))
        else:
            image = self.load_image('ref-toa')

        # reminder - indices' values are the keys, split by hyphen, eg {ndvi-toa': ['ndvi', 'toa']}
        gippy_input = {} # map prod types to temp output filenames for feeding to gippy
        tempfps_to_ptypes = {} # map temp output filenames to prod types, needed for AddFile
        for prod_type, pt_split in indices.items():
            temp_fp = self.temp_product_filename(sensor, prod_type)
            gippy_input[pt_split[0]] = temp_fp
            tempfps_to_ptypes[temp_fp] = prod_type

        prodout = gippy.algorithms.Indices(image, gippy_input, metadata)

        for temp_fp in prodout.values():
            archived_fp = self.archive_temp_path(temp_fp)
            self.AddFile(sensor, tempfps_to_ptypes[temp_fp], archived_fp)

        self._time_report(' -> %s: processed %s' % (self.basename, indices))

    # this function creates a geolocation error
    #def shrunk_bbox(self, tile):
        #w_lon, e_lon, s_lat, n_lat = self.Repository.tile_lat_lon(tile)
        #latlon = pyproj.Proj(init='epsg:4326')
        #utm = pyproj.Proj(init='epsg:326{}'.format(tile[0:2]))

        #w_lon_utm, s_lat_utm = pyproj.transform(latlon, utm, w_lon, s_lat)
        #e_lon_utm, n_lat_utm = pyproj.transform(latlon, utm, e_lon, n_lat)

        #lon_diff = (e_lon_utm - w_lon_utm) / 16
        #lat_diff = (n_lat_utm - s_lat_utm) / 16

        #w_lon_shrunk, s_lat_shrunk = pyproj.transform(utm, latlon, w_lon_utm + lon_diff, s_lat_utm + lat_diff)
        #e_lon_shrunk, n_lat_shrunk = pyproj.transform(utm, latlon, e_lon_utm - lon_diff, n_lat_utm - lat_diff)

        #return w_lon_shrunk, e_lon_shrunk, s_lat_shrunk, n_lat_shrunk


    def process_acolite(self, aco_prods):
        a_obj, sensor = self.current_asset(), self.current_sensor()
        self._time_report("Starting acolite processing") # for {}".format(x.keys()))
        # let acolite use a subdirectory in this run's tempdir:
        aco_tmp_dir = self.generate_temp_path('acolite')
        os.mkdir(aco_tmp_dir)
        acolite_product_spec = {'meta': self.prep_meta()}
        for p in aco_prods:
            # TODO use tempdirs to match current gips practices
            fn = os.path.join(self.path, self.product_filename(sensor, p))
            aps_p = acolite_product_spec[p] = {'fname': fn}
            aps_p.update(self._products[p])
            aps_p.pop('assets')

        w_lon, e_lon, s_lat, n_lat = self.Repository.tile_lat_lon(a_obj.tile)
        roi = None
        if a_obj.style == 'original':
            roi = (s_lat, w_lon, n_lat, e_lon)

        prodout = atmosphere.process_acolite(
                a_obj, aco_tmp_dir, acolite_product_spec,
                a_obj.style_res['raster-re'].format(tileid=self.id),
                extracted_asset_glob='*.SAFE',
                roi=roi,
                band='02')

        [self.AddFile(sensor, pt, fn) for pt, fn in prodout.items()]
        self._time_report(' -> {}: processed {}'.format(
                self.basename + '_' + sensor, prodout.keys()))

    def ref_geoimage(self, asset_type, sensor):
        """Generate a surface reflectance image.

        Made from a rad-toa image (the reverted ref-toa data sentinel-2 L1C
        provides), put through an atmospheric correction process.  CF landsat.
        """
        self._time_report('Computing atmospheric corrections for surface reflectance')
        atm6s = self.assets[asset_type].generate_atmo_corrector()
        scaling_factor = 0.001 # to prevent chunky small ints
        rad_toa_image = self.load_image('rad-toa')
        sr_image = gippy.GeoImage(rad_toa_image)
        # set meta to pass along to indices
        sr_image._aod_source = str(atm6s.aod[0])
        sr_image._aod_value  = str(atm6s.aod[1])
        for c in self.assets[asset_type]._sensors[sensor]['indices-colors']:
            (T, Lu, Ld) = atm6s.results[c]
            lu = 0.0001 * Lu # see rad_geoimage for reason for this
            TLdS = T * Ld * scaling_factor
            sr_image[c] = (rad_toa_image[c] - lu) / TLdS
        self._product_images['ref'] = sr_image


    def fmask_geoimage(self, asset_type):
        """Generate cloud mask.

        Uses python implementation of cfmask. Builds a VRT of all the necessary
        bands in the proper order, an angles image is created using the supplied
        metadata, and then the two are put through the fmask algorithm.
        """
        self._time_report('Generating cloud mask')

        asset_style = self.assets[asset_type].style

        DEVNULL = open(os.devnull, 'w')

        gdalbuildvrt_args = [
            "gdalbuildvrt",
            "-resolution", "user",
            "-tr", "20", "20",
            "-separate",
            "%s/allbands.vrt" % self._temp_proc_dir,
        ] + self.metadata['abs-filenames']
        subprocess.check_call(gdalbuildvrt_args, stderr=DEVNULL)

        safe_zip = zipfile.ZipFile(self.assets[asset_type].filename, 'r')
        metadata_xml = None
        for name in safe_zip.namelist():
            if re.match(self.Asset._asset_styles[asset_style]['tile-md-re'].format(tileid=self.assets[asset_type].tile), name):
                safe_zip.extract(name, self._temp_proc_dir)
                metadata_xml = "{}/{}".format(self._temp_proc_dir, name)
        if not metadata_xml:
            raise IOError("{} does not contain expected metadatafile.".format(safe_zip.filename))
        safe_zip.close()

        angles_cmd_list = [
            "fmask_sentinel2makeAnglesImage.py",
            "-i", metadata_xml,
            "-o", "%s/angles.img" % self._temp_proc_dir,
        ]
        fmask_cmd_list = [
            "fmask_sentinel2Stacked.py",
            "-a", "%s/allbands.vrt" % self._temp_proc_dir,
            "-z", "%s/angles.img" % self._temp_proc_dir,
            "-o", "%s/cloudmask.tif" % self._temp_proc_dir,
            "--cloudprobthreshold", "5",
            "-v",
        ]
        # Temp dir for intermediaries that pyfmask generates in the current
        # working directory.  N.B.: the mask is output to self._temp_proc_dir.
        with utils.make_temp_dir(prefix='gips-py-fmask', dir='/tmp') as tdir:
            prev_wd = os.getcwd()
            os.chdir(tdir)
            try:
                utils.verbose_out('running: ' + ' '.join(angles_cmd_list), 3)
                subprocess.check_call(
                    angles_cmd_list,
                    #stderr=DEVNULL
                )
                utils.verbose_out('running: ' + ' '.join(fmask_cmd_list), 3)
                subprocess.check_call(
                    fmask_cmd_list,
                    stderr=DEVNULL
                )
            except:
                raise
            finally:
                os.chdir(prev_wd)

        DEVNULL.close()
        fmask_image = gippy.GeoImage("%s/cloudmask.tif" % self._temp_proc_dir)
        self._product_images['cfmask'] = fmask_image


    def cloudmask_geoimage(self):
        fmask_image = self.load_image('cfmask')
        npfm = fmask_image.Read()
        # cfmask values:
        # 0 = NoData
        # 1 = Land
        # 2 = Cloud
        # 3 = Cloud Shadow
        # 4 = Snow
        # 5 = Water

        # Set cfmask 2 and 3 to 1's, everything else to 0's
        np_cloudmask = numpy.logical_or( npfm == 2, npfm == 3).astype('uint8')

        # cloudmask.tif is taken by cfmask
        cloudmask_filename = "%s/cloudmask2.tif" % self._temp_proc_dir
        cloudmask_img = gippy.GeoImage(
            cloudmask_filename,
            fmask_image,
            gippy.GDT_Byte,
            1
        )
        cloudmask_img[0].Write(np_cloudmask)
        self._product_images['cloudmask'] = cloudmask_img


    def mtci_geoimage(self, mode):
        """Generate Python implementation of MTCI."""
        # test this with eg:
        # gips_process sentinel2 -t 16TDP -d 2017-10-01 -v5 -p mtci --overwrite
        self._time_report('Generating MTCI')
        asset_style = self.assets[_asset_type].style

        # change this to 'ref'
        ref_img = self.load_image('ref-toa' if mode == 'toa' else 'ref')

        b4 = ref_img['RED'].Read()
        b5 = ref_img['REDEDGE1'].Read()
        b6 = ref_img['REDEDGE2'].Read()

        gain = 0.0002
        missing = -32768

        mtci = missing + 0. * b4.copy()
        wg = (b4 > 0.)&(b4 <= 1.)&(b5 > 0.)&(b5 <= 1.)&(b6 > 0.)&(b6 <= 1.)&(b5 - b4 != 0.)
        mtci[wg] = ((b6[wg] - b5[wg]) / (b5[wg] - b4[wg]))
        mtci[(mtci < -6.)|(mtci >= 6.)] = missing
        mtci[mtci != missing] = mtci[mtci != missing]/gain
        mtci = mtci.astype('int16')

        mtci_filename = "%s/mtci.tif" % self._temp_proc_dir
        mtci_img = gippy.GeoImage(mtci_filename, ref_img, gippy.GDT_Int16, 1)

        mtci_img[0].Write(mtci)
        mtci_img[0].SetGain(gain)
        mtci_img[0].SetNoData(missing)

        self._product_images[
                'mtci-toa' if mode == 'toa' else 'mtci'] = mtci_img

    def s2rep_geoimage(self, mode):
        """Generate Python implementation of S2REP."""
        self._time_report('Generating S2REP')
        asset_style = self.assets[_asset_type].style

        # change this to 'ref'
        ref_img = self.load_image('ref-toa' if mode == 'toa' else 'ref')

        b4 = ref_img['RED'].Read()
        b5 = ref_img['REDEDGE1'].Read()
        b6 = ref_img['REDEDGE2'].Read()
        b7 = ref_img['REDEDGE3'].Read()

        gain = 0.04
        offset = 400.
        missing = -32768

        s2rep = missing + 0. * b4.copy()
        wg = (b4 > 0.)&(b4 <= 1.)&(b5 > 0.)&(b5 <= 1.)&(b6 > 0.)&(b6 <= 1.)&(b7 > 0.)&(b7 <= 1.)&(b6 - b5 != 0.)
        s2rep[wg] = 705. + 35. * ((((b7[wg] + b4[wg])/2.) - b5[wg])/(b6[wg] - b5[wg]))

        s2rep[(s2rep < 400.)|(s2rep >= 1100.)] = missing
        s2rep[s2rep != missing] = (s2rep[s2rep != missing] - offset)/gain
        s2rep = s2rep.astype('int16')

        s2rep_filename = "%s/s2rep.tif" % self._temp_proc_dir
        s2rep_img = gippy.GeoImage(s2rep_filename, ref_img, gippy.GDT_Int16, 1)

        s2rep_img[0].Write(s2rep)
        s2rep_img[0].SetGain(gain)
        s2rep_img[0].SetOffset(offset)
        s2rep_img[0].SetNoData(missing)

        self._product_images[
                's2rep-toa' if mode == 'toa' else 's2rep'] = s2rep_img

    @Data.proc_temp_dir_manager
    def process(self, products=None, overwrite=False, **kwargs):
        """Produce data products and save them to files.

        If `products` is None, it processes all products.  If
        `overwrite` is True, it will overwrite existing products if they
        are found.  Products are saved to a well-known or else specified
        directory.  kwargs is unused, and is present for compatibility.
        """
        asset_type = 'L1C' # only one in the driver for now, conveniently
        self._time_report('Starting processing for this temporal-spatial unit')
        products = self.needed_products(products, overwrite)
        if len(products) == 0:
            utils.verbose_out('No new processing required.')
            return
        self._product_images = {}

        # Read the assets
        with utils.error_handler('Error reading '
                                 + utils.basename(self.assets[asset_type].filename)):
            self.read_raw() # returns a GeoImage, presently unused

        sensor = self.sensors[asset_type]
        # dict describing specification for all the bands in the asset
        data_spec = self.assets[asset_type]._sensors[sensor]

        work = self.plan_work(products.requested.keys(), overwrite) # see if we can save any work

        # only do the bits that need doing
        if 'ref-toa' in work:
            self.ref_toa_geoimage(sensor, data_spec)
        if 'rad-toa' in work:
            self.rad_toa_geoimage(asset_type, sensor)
        if 'rad' in work:
            self.rad_geoimage()
        if 'ref' in work:
            self.ref_geoimage(asset_type, sensor)
        if 'cfmask' in work:
            self.fmask_geoimage(asset_type)
        if 'cloudmask' in work:
            self.cloudmask_geoimage()
        if 'mtci-toa' in work:
            self.mtci_geoimage('toa')
        if 's2rep-toa' in work:
            self.s2rep_geoimage('toa')
        if 'mtci' in work:
            self.mtci_geoimage('surf')
        if 's2rep' in work:
            self.s2rep_geoimage('surf')

        self._time_report('Starting on standard product processing')

        # Process standard products
        for prod_type in products.groups()['Standard']:
            err_msg = 'Error creating product {} for {}'.format(
                    prod_type, os.path.basename(self.assets[asset_type].filename))
            with utils.error_handler(err_msg, continuable=True):
                self._time_report('Starting {} processing'.format(prod_type))
                temp_fp = self.temp_product_filename(sensor, prod_type)
                # have to reproduce the whole object because gippy refuses to write metadata when
                # you do image.Process(filename).
                source_image = self._product_images[prod_type]
                output_image = gippy.GeoImage(temp_fp, source_image)
                output_image.SetNoData(0)
                output_image.SetMeta(self.prep_meta())
                if prod_type in ('ref', 'rad'): # atmo-correction metadata
                    output_image.SetMeta('AOD Source', source_image._aod_source)
                    output_image.SetMeta('AOD Value',  source_image._aod_value)
                if prod_type in ('ref-toa', 'rad-toa', 'rad', 'ref'):
                    output_image.SetGain(0.0001)
                if prod_type == 'cfmask':
                    output_image.SetMeta('FMASK_0', 'nodata')
                    output_image.SetMeta('FMASK_1', 'valid')
                    output_image.SetMeta('FMASK_2', 'cloud')
                    output_image.SetMeta('FMASK_3', 'cloud shadow')
                    output_image.SetMeta('FMASK_4', 'snow')
                    output_image.SetMeta('FMASK_5', 'water')
                if prod_type == 'mtci':
                    output_image.SetGain(0.0002)
                    output_image.SetNoData(-32768)
                if prod_type == 's2rep':
                    output_image.SetGain(0.04)
                    output_image.SetOffset(400.0)
                    output_image.SetNoData(-32768)
                for b_num, b_name in enumerate(source_image.BandNames(), 1):
                    output_image.SetBandName(b_name, b_num)
                # process bandwise because gippy had an error doing it all at once
                for i in range(len(source_image)):
                    source_image[i].Process(output_image[i])
                archive_fp = self.archive_temp_path(temp_fp)
                self.AddFile(sensor, prod_type, archive_fp)

            self._time_report('Finished {} processing'.format(prod_type))
            (source_image, output_image) = (None, None) # gc hint due to C++/swig weirdness
        self._time_report('Completed standard product processing')

        # process indices in two groups:  toa and surf
        indices = products.groups()['Index']
        toa_indices  = {k: v for (k, v) in indices.items() if 'toa' in v}
        self.process_indices('toa', sensor, toa_indices)

        surf_indices  = {k: v for (k, v) in indices.items() if 'toa' not in v}
        self.process_indices('surf', sensor, surf_indices)

        if len(products.groups()['ACOLITE']) > 0:
            self.process_acolite(products.groups()['ACOLITE'])

        self._product_images = {} # hint for gc; may be needed due to C++/swig weirdness
        self._time_report('Processing complete for this spatial-temporal unit')
