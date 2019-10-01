import collections


expectations = collections.OrderedDict([
    # t_process[landsat-cloudmask-coreg] recording:
    ('cloudmask-coreg',
     [('landsat/tiles/012030/2017213/012030_2017213_coreg_args.txt',
       'text-full',
       ['x: -6.59999999999\n', 'y: -7.14'])]),

 # t_process[landsat-cloudmask] recording:
 ('cloudmask',
  [('landsat/tiles/012030/2017213/012030_2017213_LC8_cloudmask.tif',
    'raster',
    'gdalinfo-stats',
    ['Driver: GTiff/GeoTIFF',
     'Size is 7891, 8001',
     'Coordinate System is:',
     'PROJCS["WGS 84 / UTM zone 19N",',
     '    GEOGCS["WGS 84",',
     '        DATUM["WGS_1984",',
     '            SPHEROID["WGS 84",6378137,298.25722356,',
     '                AUTHORITY["EPSG","7030"]],',
     '            AUTHORITY["EPSG","6326"]],',
     '        PRIMEM["Greenwich",0,',
     '            AUTHORITY["EPSG","8901"]],',
     '        UNIT["degree",0.01745329,',
     '            AUTHORITY["EPSG","9122"]],',
     '        AUTHORITY["EPSG","4326"]],',
     '    PROJECTION["Transverse_Mercator"],',
     '    PARAMETER["latitude_of_origin",0],',
     '    PARAMETER["central_meridian",-69],',
     '    PARAMETER["scale_factor",0.9996],',
     '    PARAMETER["false_easting",500000],',
     '    PARAMETER["false_northing",0],',
     '    UNIT["metre",1,',
     '        AUTHORITY["EPSG","9001"]],',
     '    AXIS["Easting",EAST],',
     '    AXIS["Northing",NORTH],',
     '    AUTHORITY["EPSG","32619"]]',
     'Origin = (232485.00000000,4902615.00000000)',
     'Pixel Size = (30.00000000,-30.00000000)',
     'Metadata:',
     '  AREA_OR_POINT=Point',
     '  GIPS_C1_DILATED_PIXELS=20',
     '  GIPS_LANDSAT_CLOUDMASK_CLEAR_OR_NODATA_VALUE=0',
     '  GIPS_LANDSAT_CLOUDMASK_CLOUD_VALUE=1',
     '  GIPS_Landsat_Version=1.0.1',
     '  GIPS_Source_Assets=LC08_L1TP_012030_20170801_20170811_01_T1.tar.gz',
     '  GIPS_Version=0.0.0-dev',
     'Image Structure Metadata:',
     '  INTERLEAVE=BAND',
     'Corner Coordinates:',
     'Upper Left  (  232485.000, 4902615.000) ( 72d20\'58.04"W, 44d13\'39.53"N)',
     'Lower Left  (  232485.000, 4662585.000) ( 72d14\' 0.70"W, 42d 4\'11.22"N)',
     'Upper Right (  469215.000, 4902615.000) ( 69d23\' 8.77"W, 44d16\'34.07"N)',
     'Lower Right (  469215.000, 4662585.000) ( 69d22\'20.60"W, 42d 6\'53.13"N)',
     'Center      (  350850.000, 4782600.000) ( 70d50\' 6.95"W, 43d10\'53.23"N)',
     'Band 1 Block=7891x1 Type=Byte, ColorInterp=Gray',
     '  Description = cloudmask',
     '  Minimum=1.000, Maximum=1.000, Mean=1.000, StdDev=0.000',
     '  NoData Value=0',
     '  Metadata:',
     '    STATISTICS_MAXIMUM=1',
     '    STATISTICS_MEAN=1',
     '    STATISTICS_MINIMUM=1',
     '    STATISTICS_STDDEV=0',
     '    STATISTICS_VALID_PERCENT=12.7']),
   ]),

 # t_process[landsat-ndvi-toa] recording:
 ('ndvi-toa',
  [('landsat/tiles/012030/2017213/012030_2017213_LC8_ndvi-toa.tif',
    'raster',
    'gdalinfo-stats',
    ['Driver: GTiff/GeoTIFF',
     'Size is 7891, 8001',
     'Coordinate System is:',
     'PROJCS["WGS 84 / UTM zone 19N",',
     '    GEOGCS["WGS 84",',
     '        DATUM["WGS_1984",',
     '            SPHEROID["WGS 84",6378137,298.25722356,',
     '                AUTHORITY["EPSG","7030"]],',
     '            AUTHORITY["EPSG","6326"]],',
     '        PRIMEM["Greenwich",0,',
     '            AUTHORITY["EPSG","8901"]],',
     '        UNIT["degree",0.01745329,',
     '            AUTHORITY["EPSG","9122"]],',
     '        AUTHORITY["EPSG","4326"]],',
     '    PROJECTION["Transverse_Mercator"],',
     '    PARAMETER["latitude_of_origin",0],',
     '    PARAMETER["central_meridian",-69],',
     '    PARAMETER["scale_factor",0.9996],',
     '    PARAMETER["false_easting",500000],',
     '    PARAMETER["false_northing",0],',
     '    UNIT["metre",1,',
     '        AUTHORITY["EPSG","9001"]],',
     '    AXIS["Easting",EAST],',
     '    AXIS["Northing",NORTH],',
     '    AUTHORITY["EPSG","32619"]]',
     'Origin = (232485.00000000,4902615.00000000)',
     'Pixel Size = (30.00000000,-30.00000000)',
     'Metadata:',
     '  AREA_OR_POINT=Point',
     '  GIPS_Landsat_Version=1.0.1',
     '  GIPS_Source_Assets=LC08_L1TP_012030_20170801_20170811_01_T1.tar.gz',
     '  GIPS_Version=0.0.0-dev',
     'Image Structure Metadata:',
     '  INTERLEAVE=BAND',
     'Corner Coordinates:',
     'Upper Left  (  232485.000, 4902615.000) ( 72d20\'58.04"W, 44d13\'39.53"N)',
     'Lower Left  (  232485.000, 4662585.000) ( 72d14\' 0.70"W, 42d 4\'11.22"N)',
     'Upper Right (  469215.000, 4902615.000) ( 69d23\' 8.77"W, 44d16\'34.07"N)',
     'Lower Right (  469215.000, 4662585.000) ( 69d22\'20.60"W, 42d 6\'53.13"N)',
     'Center      (  350850.000, 4782600.000) ( 70d50\' 6.95"W, 43d10\'53.23"N)',
     'Band 1 Block=7891x1 Type=Int16, ColorInterp=Gray',
     '  Description = ndvi',
     '  Minimum=-11138.000, Maximum=9900.000, Mean=3186.320, StdDev=4836.391',
     '  NoData Value=-32768',
     '  Offset: 0,   Scale:0.0001',
     '  Metadata:',
     '    STATISTICS_MAXIMUM=9900',
     '    STATISTICS_MEAN=3186.32021753',
     '    STATISTICS_MINIMUM=-11138',
     '    STATISTICS_STDDEV=4836.39077010',
     '    STATISTICS_VALID_PERCENT=64.4'])]),

 # t_process[landsat-rad-toa] recording:
 ('rad-toa',
  [('landsat/tiles/012030/2017213/012030_2017213_LC8_rad-toa.tif',
    'raster',
    'gdalinfo-stats',
    ['Driver: GTiff/GeoTIFF',
     'Size is 7891, 8001',
     'Coordinate System is:',
     'PROJCS["WGS 84 / UTM zone 19N",',
     '    GEOGCS["WGS 84",',
     '        DATUM["WGS_1984",',
     '            SPHEROID["WGS 84",6378137,298.25722356,',
     '                AUTHORITY["EPSG","7030"]],',
     '            AUTHORITY["EPSG","6326"]],',
     '        PRIMEM["Greenwich",0,',
     '            AUTHORITY["EPSG","8901"]],',
     '        UNIT["degree",0.01745329,',
     '            AUTHORITY["EPSG","9122"]],',
     '        AUTHORITY["EPSG","4326"]],',
     '    PROJECTION["Transverse_Mercator"],',
     '    PARAMETER["latitude_of_origin",0],',
     '    PARAMETER["central_meridian",-69],',
     '    PARAMETER["scale_factor",0.9996],',
     '    PARAMETER["false_easting",500000],',
     '    PARAMETER["false_northing",0],',
     '    UNIT["metre",1,',
     '        AUTHORITY["EPSG","9001"]],',
     '    AXIS["Easting",EAST],',
     '    AXIS["Northing",NORTH],',
     '    AUTHORITY["EPSG","32619"]]',
     'Origin = (232485.00000000,4902615.00000000)',
     'Pixel Size = (30.00000000,-30.00000000)',
     'Metadata:',
     '  AREA_OR_POINT=Point',
     '  GIPS_Landsat_Version=1.0.1',
     '  GIPS_Source_Assets=LC08_L1TP_012030_20170801_20170811_01_T1.tar.gz',
     '  GIPS_Version=0.0.0-dev',
     'Image Structure Metadata:',
     '  INTERLEAVE=PIXEL',
     'Corner Coordinates:',
     'Upper Left  (  232485.000, 4902615.000) ( 72d20\'58.04"W, 44d13\'39.53"N)',
     'Lower Left  (  232485.000, 4662585.000) ( 72d14\' 0.70"W, 42d 4\'11.22"N)',
     'Upper Right (  469215.000, 4902615.000) ( 69d23\' 8.77"W, 44d16\'34.07"N)',
     'Lower Right (  469215.000, 4662585.000) ( 69d22\'20.60"W, 42d 6\'53.13"N)',
     'Center      (  350850.000, 4782600.000) ( 70d50\' 6.95"W, 43d10\'53.23"N)',
     'Band 1 Block=7891x1 Type=Int16, ColorInterp=Gray',
     '  Description = COASTAL',
     '  Minimum=459.000, Maximum=7379.000, Mean=691.671, StdDev=235.655',
     '  NoData Value=-32768',
     '  Offset: 0,   Scale:0.1',
     '  Metadata:',
     '    STATISTICS_MAXIMUM=7379',
     '    STATISTICS_MEAN=691.67124622',
     '    STATISTICS_MINIMUM=459',
     '    STATISTICS_STDDEV=235.65477269',
     '    STATISTICS_VALID_PERCENT=64.4',
     'Band 2 Block=7891x1 Type=Int16, ColorInterp=Blue',
     '  Description = BLUE',
     '  Minimum=255.000, Maximum=7246.000, Mean=577.542, StdDev=263.824',
     '  NoData Value=-32768',
     '  Offset: 0,   Scale:0.1',
     '  Metadata:',
     '    STATISTICS_MAXIMUM=7246',
     '    STATISTICS_MEAN=577.54176729',
     '    STATISTICS_MINIMUM=255',
     '    STATISTICS_STDDEV=263.82425330',
     '    STATISTICS_VALID_PERCENT=64.4',
     'Band 3 Block=7891x1 Type=Int16, ColorInterp=Green',
     '  Description = GREEN',
     '  Minimum=167.000, Maximum=6963.000, Mean=412.243, StdDev=262.031',
     '  NoData Value=-32768',
     '  Offset: 0,   Scale:0.1',
     '  Metadata:',
     '    STATISTICS_MAXIMUM=6963',
     '    STATISTICS_MEAN=412.24323431',
     '    STATISTICS_MINIMUM=167',
     '    STATISTICS_STDDEV=262.03142742',
     '    STATISTICS_VALID_PERCENT=64.4',
     'Band 4 Block=7891x1 Type=Int16, ColorInterp=Red',
     '  Description = RED',
     '  Minimum=6.000, Maximum=5872.000, Mean=246.700, StdDev=249.790',
     '  NoData Value=-32768',
     '  Offset: 0,   Scale:0.1',
     '  Metadata:',
     '    STATISTICS_MAXIMUM=5872',
     '    STATISTICS_MEAN=246.69981650',
     '    STATISTICS_MINIMUM=6',
     '    STATISTICS_STDDEV=249.79018895',
     '    STATISTICS_VALID_PERCENT=64.4',
     'Band 5 Block=7891x1 Type=Int16, ColorInterp=Gray',
     '  Description = NIR',
     '  Minimum=-5.000, Maximum=3593.000, Mean=594.428, StdDev=464.698',
     '  NoData Value=-32768',
     '  Offset: 0,   Scale:0.1',
     '  Metadata:',
     '    STATISTICS_MAXIMUM=3593',
     '    STATISTICS_MEAN=594.42774302',
     '    STATISTICS_MINIMUM=-5',
     '    STATISTICS_STDDEV=464.69770294',
     '    STATISTICS_VALID_PERCENT=64.4',
     'Band 6 Block=7891x1 Type=Int16, ColorInterp=Gray',
     '  Description = SWIR1',
     '  Minimum=-10.000, Maximum=894.000, Mean=69.101, StdDev=62.163',
     '  NoData Value=-32768',
     '  Offset: 0,   Scale:0.1',
     '  Metadata:',
     '    STATISTICS_MAXIMUM=894',
     '    STATISTICS_MEAN=69.10081469',
     '    STATISTICS_MINIMUM=-10',
     '    STATISTICS_STDDEV=62.16306790',
     '    STATISTICS_VALID_PERCENT=64.4',
     'Band 7 Block=7891x1 Type=Int16, ColorInterp=Gray',
     '  Description = SWIR2',
     '  Minimum=-4.000, Maximum=301.000, Mean=11.107, StdDev=13.463',
     '  NoData Value=-32768',
     '  Offset: 0,   Scale:0.1',
     '  Metadata:',
     '    STATISTICS_MAXIMUM=301',
     '    STATISTICS_MEAN=11.10686767',
     '    STATISTICS_MINIMUM=-4',
     '    STATISTICS_STDDEV=13.46300543',
     '    STATISTICS_VALID_PERCENT=64.4',
     'Band 8 Block=7891x1 Type=Int16, ColorInterp=Gray',
     '  Description = CIRRUS',
     '  Minimum=-6.000, Maximum=183.000, Mean=1.479, StdDev=0.710',
     '  NoData Value=-32768',
     '  Offset: 0,   Scale:0.1',
     '  Metadata:',
     '    STATISTICS_MAXIMUM=183',
     '    STATISTICS_MEAN=1.47879629',
     '    STATISTICS_MINIMUM=-6',
     '    STATISTICS_STDDEV=0.70958100',
     '    STATISTICS_VALID_PERCENT=64.4'])]),

 # t_process[landsat-ref-toa] recording:
 ('ref-toa',
  [('landsat/tiles/012030/2017213/012030_2017213_LC8_ref-toa.tif',
    'raster',
    'gdalinfo-stats',
    ['Driver: GTiff/GeoTIFF',
     'Size is 7891, 8001',
     'Coordinate System is:',
     'PROJCS["WGS 84 / UTM zone 19N",',
     '    GEOGCS["WGS 84",',
     '        DATUM["WGS_1984",',
     '            SPHEROID["WGS 84",6378137,298.25722356,',
     '                AUTHORITY["EPSG","7030"]],',
     '            AUTHORITY["EPSG","6326"]],',
     '        PRIMEM["Greenwich",0,',
     '            AUTHORITY["EPSG","8901"]],',
     '        UNIT["degree",0.01745329,',
     '            AUTHORITY["EPSG","9122"]],',
     '        AUTHORITY["EPSG","4326"]],',
     '    PROJECTION["Transverse_Mercator"],',
     '    PARAMETER["latitude_of_origin",0],',
     '    PARAMETER["central_meridian",-69],',
     '    PARAMETER["scale_factor",0.9996],',
     '    PARAMETER["false_easting",500000],',
     '    PARAMETER["false_northing",0],',
     '    UNIT["metre",1,',
     '        AUTHORITY["EPSG","9001"]],',
     '    AXIS["Easting",EAST],',
     '    AXIS["Northing",NORTH],',
     '    AUTHORITY["EPSG","32619"]]',
     'Origin = (232485.00000000,4902615.00000000)',
     'Pixel Size = (30.00000000,-30.00000000)',
     'Metadata:',
     '  AREA_OR_POINT=Point',
     '  GIPS_Landsat_Version=1.0.1',
     '  GIPS_Source_Assets=LC08_L1TP_012030_20170801_20170811_01_T1.tar.gz',
     '  GIPS_Version=0.0.0-dev',
     'Image Structure Metadata:',
     '  INTERLEAVE=PIXEL',
     'Corner Coordinates:',
     'Upper Left  (  232485.000, 4902615.000) ( 72d20\'58.04"W, 44d13\'39.53"N)',
     'Lower Left  (  232485.000, 4662585.000) ( 72d14\' 0.70"W, 42d 4\'11.22"N)',
     'Upper Right (  469215.000, 4902615.000) ( 69d23\' 8.77"W, 44d16\'34.07"N)',
     'Lower Right (  469215.000, 4662585.000) ( 69d22\'20.60"W, 42d 6\'53.13"N)',
     'Center      (  350850.000, 4782600.000) ( 70d50\' 6.95"W, 43d10\'53.23"N)',
     'Band 1 Block=7891x1 Type=Int16, ColorInterp=Gray',
     '  Description = COASTAL',
     '  Minimum=655.000, Maximum=10541.000, Mean=987.993, StdDev=336.613',
     '  NoData Value=-32768',
     '  Offset: 0,   Scale:0.0001',
     '  Metadata:',
     '    STATISTICS_MAXIMUM=10541',
     '    STATISTICS_MEAN=987.99329818',
     '    STATISTICS_MINIMUM=655',
     '    STATISTICS_STDDEV=336.61250899',
     '    STATISTICS_VALID_PERCENT=64.4',
     'Band 2 Block=7891x1 Type=Int16, ColorInterp=Blue',
     '  Description = BLUE',
     '  Minimum=474.000, Maximum=13445.000, Mean=1071.618, StdDev=489.525',
     '  NoData Value=-32768',
     '  Offset: 0,   Scale:0.0001',
     '  Metadata:',
     '    STATISTICS_MAXIMUM=13445',
     '    STATISTICS_MEAN=1071.61781489',
     '    STATISTICS_MINIMUM=474',
     '    STATISTICS_STDDEV=489.52486053',
     '    STATISTICS_VALID_PERCENT=64.4',
     'Band 3 Block=7891x1 Type=Int16, ColorInterp=Green',
     '  Description = GREEN',
     '  Minimum=346.000, Maximum=14410.000, Mean=853.116, StdDev=542.262',
     '  NoData Value=-32768',
     '  Offset: 0,   Scale:0.0001',
     '  Metadata:',
     '    STATISTICS_MAXIMUM=14410',
     '    STATISTICS_MEAN=853.11592069',
     '    STATISTICS_MINIMUM=346',
     '    STATISTICS_STDDEV=542.26162442',
     '    STATISTICS_VALID_PERCENT=64.4',
     'Band 4 Block=7891x1 Type=Int16, ColorInterp=Red',
     '  Description = RED',
     '  Minimum=10.000, Maximum=10662.000, Mean=447.959, StdDev=453.568',
     '  NoData Value=-32768',
     '  Offset: 0,   Scale:0.0001',
     '  Metadata:',
     '    STATISTICS_MAXIMUM=10662',
     '    STATISTICS_MEAN=447.95861284',
     '    STATISTICS_MINIMUM=10',
     '    STATISTICS_STDDEV=453.56837105',
     '    STATISTICS_VALID_PERCENT=64.4',
     'Band 5 Block=7891x1 Type=Int16, ColorInterp=Gray',
     '  Description = NIR',
     '  Minimum=-14.000, Maximum=10638.000, Mean=1759.828, StdDev=1375.761',
     '  NoData Value=-32768',
     '  Offset: 0,   Scale:0.0001',
     '  Metadata:',
     '    STATISTICS_MAXIMUM=10638',
     '    STATISTICS_MEAN=1759.82794331',
     '    STATISTICS_MINIMUM=-14',
     '    STATISTICS_STDDEV=1375.76090835',
     '    STATISTICS_VALID_PERCENT=64.4',
     'Band 6 Block=7891x1 Type=Int16, ColorInterp=Gray',
     '  Description = SWIR1',
     '  Minimum=-156.000, Maximum=13638.000, Mean=1054.858, StdDev=948.388',
     '  NoData Value=-32768',
     '  Offset: 0,   Scale:0.0001',
     '  Metadata:',
     '    STATISTICS_MAXIMUM=13638',
     '    STATISTICS_MEAN=1054.85812273',
     '    STATISTICS_MINIMUM=-156',
     '    STATISTICS_STDDEV=948.38825079',
     '    STATISTICS_VALID_PERCENT=64.4',
     'Band 7 Block=7891x1 Type=Int16, ColorInterp=Gray',
     '  Description = SWIR2',
     '  Minimum=-153.000, Maximum=12527.000, Mean=463.774, StdDev=558.375',
     '  NoData Value=-32768',
     '  Offset: 0,   Scale:0.0001',
     '  Metadata:',
     '    STATISTICS_MAXIMUM=12527',
     '    STATISTICS_MEAN=463.77383724',
     '    STATISTICS_MINIMUM=-153',
     '    STATISTICS_STDDEV=558.37499240',
     '    STATISTICS_VALID_PERCENT=64.4',
     'Band 8 Block=7891x1 Type=Int16, ColorInterp=Gray',
     '  Description = CIRRUS',
     '  Minimum=-62.000, Maximum=1864.000, Mean=15.054, StdDev=6.236',
     '  NoData Value=-32768',
     '  Offset: 0,   Scale:0.0001',
     '  Metadata:',
     '    STATISTICS_MAXIMUM=1864',
     '    STATISTICS_MEAN=15.05369893',
     '    STATISTICS_MINIMUM=-62',
     '    STATISTICS_STDDEV=6.23609811',
     '    STATISTICS_VALID_PERCENT=64.4'])]),

])
