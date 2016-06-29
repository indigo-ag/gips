import logging, os
from pprint import pformat

import pytest
import envoy
from scripttest import TestFileEnvironment, ProcResult

logger = logging.getLogger(__name__)

# set constants, mostly places to find various needed files
TEST_DATA_DIR  = str(pytest.config.rootdir.join('gips/test'))
DATA_REPO_ROOT = pytest.config.getini('data-repo')
OUTPUT_DIR     = pytest.config.getini('output-dir')
NH_SHP_PATH    = os.path.join(TEST_DATA_DIR, 'NHseacoast.shp')
# changing this will require changes in expected_*_files below:
STD_ARGS       = ('modis', '-s', NH_SHP_PATH,
                  '-d', '2012-12-01,2012-12-03', '-v', '4')

@pytest.fixture
def setup_modis_data(pytestconfig):
    """Use gips_inventory to ensure presence of MODIS data in the data repo."""
    if not pytestconfig.getoption('setup_repo'):
        logger.debug("Skipping repo setup per lack of option.")
        return
    logger.info("Downloading MODIS data . . .")
    cmd_str = 'gips_inventory ' + ' '.join(STD_ARGS) + ' --fetch'
    outcome = envoy.run(cmd_str)
    logger.info("MODIS data download complete.")
    if outcome.status_code != 0:
        raise RuntimeError("MODIS data setup via `gips_inventory` failed",
                           outcome.std_out, outcome.std_err, outcome)


class GipsTestFileEnv(TestFileEnvironment):
    """As superclass but customized for GIPS use case.

    Saves ProcResult objects in self.proc_result."""
    proc_result = None

    @staticmethod
    def log_findings(description, files):
        """If user asks for debug output, log post-run file findings.

        Logs in a format suitable for updating known good values when tests
        need to be updated to match code changes."""
        files_and_hashes = extract_hashes(files)
        logger.debug("{}: {}".format(description, pformat(files_and_hashes)))

    def run(self, *args, **kwargs):
        """As super().run but store result & prevent premature exits."""
        pr = super(GipsTestFileEnv, self).run(
                *args, expect_error=True, expect_stderr=True, **kwargs)
        self.proc_result = pr
        logging.debug("standard output: {}".format(pr.stdout))
        logging.debug("standard error: {}".format(pr.stderr))
        self.log_findings("Created files", pr.files_created)
        self.log_findings("Updated files", pr.files_updated)
        self.log_findings("Deleted files", pr.files_deleted)
        return pr

    def remove_created(self):
        """Remove files created by test run."""
        if self.proc_result is None:
            raise RuntimeError("No previous run to clean up from.")
        for fname in self.proc_result.files_created.keys():
            os.remove(os.path.join(DATA_REPO_ROOT, fname))


def extract_hashes(files):
    """Return a dict of file names and unique hashes of their content.

    `files` should be a dict in a result object from TestFileEnvironment.run().
    Directories' don't have hashes so use None instead."""
    return {k: getattr(v, 'hash', None) for k, v in files.items()}


@pytest.yield_fixture
def test_file_environment():
    """Provide means to test files created by run & clean them up after."""
    gtfe = GipsTestFileEnv(DATA_REPO_ROOT, start_clear=False)
    yield gtfe
    # This step isn't effective if DATA_REPO_ROOT isn't right; in that case it
    # ruins further test runs because files already exist when the test starts.
    # Maybe add self-healing by having setup_modis_data run in a TFE and
    # detecting which files are present when it starts.
    gtfe.remove_created()


@pytest.yield_fixture
def keep_data_repo_clean(test_file_environment):
    """Keep data repo clean without having to run anything in it.

    This emulates tfe.run()'s checking the directory before and after a run,
    then working out how the directory has changed.  Unfortunately half the
    work is done in tfe, the other half in ProcResult."""
    tfe = test_file_environment
    before = tfe._find_files()
    yield # directory mutation happens here
    after = tfe._find_files()
    tfe.proc_result = ProcResult(tfe, ['N/A'], '', '', '', 0, before, after)


@pytest.fixture
def output_tfe():
    """Provide means to test files created by run & clean them up after."""
    gtfe = GipsTestFileEnv(OUTPUT_DIR)
    return gtfe


expected_inventory_fetch_created_files = {
    'modis/tiles/h12v04/2012336/MOD10A1.A2012336.h12v04.005.2012339213007.hdf': 1588268768,
    'modis/tiles/h12v04/2012336/MOD11A1.A2012336.h12v04.005.2012339180517.hdf': -868909291,
    'modis/tiles/h12v04/2012336/MYD10A1.A2012336.h12v04.005.2012340031954.hdf': 1810195064,
    'modis/tiles/h12v04/2012336/MYD11A1.A2012336.h12v04.005.2012341040543.hdf': 1579682812,
    'modis/tiles/h12v04/2012337/MCD43A2.A2012337.h12v04.005.2012356160504.hdf': 1983871800,
    'modis/tiles/h12v04/2012337/MCD43A4.A2012337.h12v04.005.2012356160504.hdf': -1050109825,
    'modis/tiles/h12v04/2012337/MOD09Q1.A2012337.h12v04.005.2012346141041.hdf': 1786923716,
    'modis/tiles/h12v04/2012337/MOD10A1.A2012337.h12v04.005.2012340033542.hdf': -1365792644,
    'modis/tiles/h12v04/2012337/MOD11A1.A2012337.h12v04.005.2012339204007.hdf': 1707500981,
    'modis/tiles/h12v04/2012337/MOD11A2.A2012337.h12v04.005.2012346152330.hdf': -168268015,
    'modis/tiles/h12v04/2012337/MYD10A1.A2012337.h12v04.005.2012340112013.hdf': -577720815,
    'modis/tiles/h12v04/2012337/MYD11A1.A2012337.h12v04.005.2012341072847.hdf': 1606986907,
    'modis/tiles/h12v04/2012338/MOD10A1.A2012338.h12v04.005.2012341091201.hdf': 1691161136,
    'modis/tiles/h12v04/2012338/MOD11A1.A2012338.h12v04.005.2012341041222.hdf': 1621811920,
    'modis/tiles/h12v04/2012338/MYD10A1.A2012338.h12v04.005.2012340142152.hdf': 1292876648,
    'modis/tiles/h12v04/2012338/MYD11A1.A2012338.h12v04.005.2012341075802.hdf': 1495599893,
}


# TODO label so it's usually skipped
def test_inventory_fetch(test_file_environment):
    """Test gips_inventory --fetch; actually contacts data provider."""
    args = STD_ARGS + ('--fetch',)

    # check repo before run to see if it's cleaned out
    before = set(test_file_environment._find_files().keys())
    expected = set(expected_inventory_fetch_created_files.keys())
    if before & expected:
        raise RuntimeError('Output files found before test; repo '
                           'may not be clean.')

    logger.info('starting run')
    outcome = test_file_environment.run('gips_inventory', *args)
    logger.info('run complete')

    # repo should now have specific new files with the right content
    detected_files = extract_hashes(outcome.files_created)

    assert (outcome.returncode == 0
            and not outcome.stderr
            and not outcome.files_deleted
            and expected_inventory_fetch_created_files == detected_files)


expected_inventory_stdout = """\x1b[1mGIPS Data Inventory (v0.8.2)\x1b[0m
Retrieving inventory for site NHseacoast-0

\x1b[1mAsset Coverage for site NHseacoast-0\x1b[0m
\x1b[1m
Tile Coverage
\x1b[4m  Tile      % Coverage   % Tile Used\x1b[0m
  h12v04      100.0%        0.2%

\x1b[1m\x1b[4m    DATE     MCD12Q1   MCD43A2   MCD43A4   MOD09Q1   MOD10A1   MOD10A2   MOD11A1   MOD11A2   MYD10A1   MYD10A2   MYD11A1   MYD11A2   Product  \x1b[0m
\x1b[1m2012        
\x1b[0m    336                                               100.0%               100.0%               100.0%               100.0%             \n    337                 100.0%     100.0%     100.0%     100.0%               100.0%     100.0%     100.0%               100.0%             \n    338                                               100.0%               100.0%               100.0%               100.0%             \n\n\n3 files on 3 dates\n\x1b[1m\nSENSORS\x1b[0m\n\x1b[35mMCD: Aqua/Terra Combined\x1b[0m\n\x1b[31mMOD: Terra\x1b[0m\n\x1b[32mMOD-MYD: Aqua/Terra together\x1b[0m\n\x1b[34mMYD: Aqua\x1b[0m
"""


def test_inventory(setup_modis_data, test_file_environment):
    """Test `gips_inventory modis` and confirm recorded output is given."""
    outcome = test_file_environment.run('gips_inventory', *STD_ARGS)
    assert (outcome.returncode == 0
            and not outcome.stderr
            and not outcome.files_created
            and not outcome.files_updated
            and not outcome.files_deleted
            and outcome.stdout == expected_inventory_stdout)


# list of recorded output file names and their checksums; each should be
# created by the test
expected_process_created_files = {
    # TODO Are these broken or what?  Each None is a broken symlink:
    'modis/tiles/h12v04/2012337/h12v04_2012337_MCD_quality.tif': None,
    'modis/tiles/h12v04/2012337/h12v04_2012337_MOD_temp8td.tif': None,
    'modis/tiles/h12v04/2012337/h12v04_2012337_MOD_temp8tn.tif': None,
    'modis/tiles/h12v04/2012336/MOD10A1.A2012336.h12v04.005.2012339213007.hdf.index': -1075525670,
    'modis/tiles/h12v04/2012336/MOD11A1.A2012336.h12v04.005.2012339180517.hdf.index': -1602319177,
    'modis/tiles/h12v04/2012336/MYD10A1.A2012336.h12v04.005.2012340031954.hdf.index': 1623945316,
    'modis/tiles/h12v04/2012336/MYD11A1.A2012336.h12v04.005.2012341040543.hdf.index': -1720582124,
    'modis/tiles/h12v04/2012336/h12v04_2012336_MCD_fsnow.tif': -843500181,
    'modis/tiles/h12v04/2012336/h12v04_2012336_MCD_snow.tif': 388495321,
    'modis/tiles/h12v04/2012336/h12v04_2012336_MOD-MYD_obstime.tif': 1994827924,
    'modis/tiles/h12v04/2012336/h12v04_2012336_MOD-MYD_temp.tif': 2094570047,
    'modis/tiles/h12v04/2012336/h12v04_2012336_MOD_clouds.tif': 161070470,
    'modis/tiles/h12v04/2012337/MCD43A2.A2012337.h12v04.005.2012356160504.hdf.index': 1869798455,
    'modis/tiles/h12v04/2012337/MCD43A4.A2012337.h12v04.005.2012356160504.hdf.index': 1702701995,
    'modis/tiles/h12v04/2012337/MOD09Q1.A2012337.h12v04.005.2012346141041.hdf.index': 1528708875,
    'modis/tiles/h12v04/2012337/MOD10A1.A2012337.h12v04.005.2012340033542.hdf.index': 1739917027,
    'modis/tiles/h12v04/2012337/MOD11A1.A2012337.h12v04.005.2012339204007.hdf.index': 640817914,
    'modis/tiles/h12v04/2012337/MOD11A2.A2012337.h12v04.005.2012346152330.hdf.index': 53371709,
    'modis/tiles/h12v04/2012337/MYD10A1.A2012337.h12v04.005.2012340112013.hdf.index': 531935583,
    'modis/tiles/h12v04/2012337/MYD11A1.A2012337.h12v04.005.2012341072847.hdf.index': 1676310978,
    'modis/tiles/h12v04/2012337/h12v04_2012337_MCD_fsnow.tif': 297883486,
    'modis/tiles/h12v04/2012337/h12v04_2012337_MCD_indices.tif': -2140726827,
    'modis/tiles/h12v04/2012337/h12v04_2012337_MCD_snow.tif': -748640537,
    'modis/tiles/h12v04/2012337/h12v04_2012337_MOD-MYD_obstime.tif': -1729084231,
    'modis/tiles/h12v04/2012337/h12v04_2012337_MOD-MYD_temp.tif': -1718009535,
    'modis/tiles/h12v04/2012337/h12v04_2012337_MOD_clouds.tif': -832284681,
    'modis/tiles/h12v04/2012337/h12v04_2012337_MOD_ndvi8.tif': -593200294,
    'modis/tiles/h12v04/2012338/MOD10A1.A2012338.h12v04.005.2012341091201.hdf.index': 1725484908,
    'modis/tiles/h12v04/2012338/MOD11A1.A2012338.h12v04.005.2012341041222.hdf.index': 838676814,
    'modis/tiles/h12v04/2012338/MYD10A1.A2012338.h12v04.005.2012340142152.hdf.index': -130649785,
    'modis/tiles/h12v04/2012338/MYD11A1.A2012338.h12v04.005.2012341075802.hdf.index': -642783734,
    'modis/tiles/h12v04/2012338/h12v04_2012338_MCD_fsnow.tif': -1930181337,
    'modis/tiles/h12v04/2012338/h12v04_2012338_MCD_snow.tif': 387672365,
    'modis/tiles/h12v04/2012338/h12v04_2012338_MOD-MYD_obstime.tif': -1693632983,
    'modis/tiles/h12v04/2012338/h12v04_2012338_MOD-MYD_temp.tif': 1712906003,
    'modis/tiles/h12v04/2012338/h12v04_2012338_MOD_clouds.tif': 296967275,
}

def test_e2e_process(setup_modis_data, test_file_environment):
    """Test gips_process on modis data."""
    logger.info('starting run')
    outcome = test_file_environment.run('gips_process', *STD_ARGS)
    logger.info('run complete')

    # extract the checksum from each found file
    detected_files = extract_hashes(outcome.files_created)
    # repo should now have specific new files with the right content
    # TODO refactor this into four separate tests that DO NOT repeat the
    # gips_process command; need this because 'and' is lazy so not all branches
    # are being evaluated (and thus reported-on).
    assert (outcome.returncode == 0
            and not outcome.stderr
            and not outcome.files_deleted
            and expected_process_created_files == detected_files)


# trailing whitespace and other junk characters are in current output
expected_info_stdout = """\x1b[1mGIPS Data Repositories (v0.8.2)\x1b[0m
\x1b[1m
Modis Products v1.0.0\x1b[0m
\x1b[1m
Terra 8-day Products
\x1b[0m   ndvi8       Normalized Difference Vegetation Index: 250m
   temp8td     Surface temperature: 1km                
   temp8tn     Surface temperature: 1km                
\x1b[1m
Nadir BRDF-Adjusted 16-day Products
\x1b[0m   indices     Land indices                            
   quality     MCD Product Quality                     
\x1b[1m
Terra/Aqua Daily Products
\x1b[0m   fsnow       Fractional snow cover data              
   obstime     MODIS Terra/Aqua overpass time          
   snow        Snow and ice cover data                 
   temp        Surface temperature data                
\x1b[1m
Standard Products
\x1b[0m   clouds      Cloud Mask                              
   landcover   MCD Annual Land Cover                   
"""

def test_e2e_info(test_file_environment):
    """Test `gips_info modis` and confirm recorded output is given."""
    outcome = test_file_environment.run('gips_info', 'modis')
    assert (outcome.returncode == 0
            and not outcome.stderr
            and not outcome.files_created
            and not outcome.files_updated
            and not outcome.files_deleted
            and outcome.stdout == expected_info_stdout)


expected_project_created_files = {
    '0': None, # directory
    '0/2012336_MCD_fsnow.tif': -1883071404,
    '0/2012336_MCD_obstime.tif': 1180170371,
    '0/2012336_MCD_snow.tif': -1824464052,
    '0/2012336_MOD-MYD_temp.tif': 2024858861,
    '0/2012336_MOD_clouds.tif': -1957614367,
    '0/2012337_MCD_fsnow.tif': -856980949,
    '0/2012337_MCD_indices.tif': -2065700846,
    '0/2012337_MCD_obstime.tif': 1283853420,
    '0/2012337_MCD_quality.tif': 1722910771,
    '0/2012337_MCD_snow.tif': -1690607189,
    '0/2012337_MOD-MYD_temp.tif': 407802214,
    '0/2012337_MOD_clouds.tif': -415873821,
    '0/2012337_MOD_ndvi8.tif': -1739368216,
    '0/2012337_MOD_temp8td.tif': 900823219,
    '0/2012337_MOD_temp8tn.tif': -727707878,
    '0/2012338_MCD_fsnow.tif': -1017381876,
    '0/2012338_MCD_obstime.tif': -922366135,
    '0/2012338_MCD_snow.tif': -319441628,
    '0/2012338_MOD-MYD_temp.tif': -869467051,
    '0/2012338_MOD_clouds.tif': 1789735888,
}


def test_e2e_project(setup_modis_data, keep_data_repo_clean, output_tfe):
    """Test gips_project modis with warping."""
    args = STD_ARGS + ('--res', '100', '100',
                       '--outdir', OUTPUT_DIR, '--notld')
    logger.info('starting run')
    outcome = output_tfe.run('gips_project', *args)
    logger.info('run complete')

    # confirm generated files match expected fingerprints
    detected_files = extract_hashes(outcome.files_created)
    assert (outcome.returncode == 0
            and not outcome.stderr
            and not outcome.files_deleted
            and expected_project_created_files == detected_files)


expected_project_no_warp_created_files = {
    '0': None, # directory
    '0/2012336_MCD_fsnow.tif': -232655043,
    '0/2012336_MCD_obstime.tif': -508398437,
    '0/2012336_MCD_snow.tif': 1704870455,
    '0/2012336_MOD-MYD_temp.tif': -1437591930,
    '0/2012336_MOD_clouds.tif': 792250507,
    '0/2012337_MCD_fsnow.tif': -118176399,
    '0/2012337_MCD_indices.tif': -517980660,
    '0/2012337_MCD_obstime.tif': -266130329,
    '0/2012337_MCD_quality.tif': -148594234,
    '0/2012337_MCD_snow.tif': -1562861219,
    '0/2012337_MOD-MYD_temp.tif': 125915217,
    '0/2012337_MOD_clouds.tif': 1172608606,
    '0/2012337_MOD_ndvi8.tif': 1952565287,
    '0/2012337_MOD_temp8td.tif': 2072205290,
    '0/2012337_MOD_temp8tn.tif': -937913415,
    '0/2012338_MCD_fsnow.tif': -50404254,
    '0/2012338_MCD_obstime.tif': -1256437319,
    '0/2012338_MCD_snow.tif': 415741551,
    '0/2012338_MOD-MYD_temp.tif': -566077737,
    '0/2012338_MOD_clouds.tif': -1110899594,
}


def test_e2e_project_no_warp(setup_modis_data, keep_data_repo_clean, output_tfe):
    """Test gips_project modis without warping."""
    args = STD_ARGS + ('--outdir', OUTPUT_DIR, '--notld')
    logger.info('starting run')
    outcome = output_tfe.run('gips_project', *args)
    logger.info('run complete')

    # confirm generated files match expected fingerprints
    detected_files = extract_hashes(outcome.files_created)
    assert (outcome.returncode == 0
            and not outcome.stderr
            and not outcome.files_deleted
            and expected_project_no_warp_created_files == detected_files)


expected_tiles_created_files = {
    'h12v04': None, # directory
    # TODO there should be something here but nothing is saved here during
    # manual runs.
}


def test_e2e_tiles(setup_modis_data, keep_data_repo_clean, output_tfe):
    """Test gips_tiles modis with warping."""
    # gips_tiles modis $ARGS --outdir modis_warped_tiles --notld
    args = STD_ARGS + ('--outdir', OUTPUT_DIR, '--notld')
    logger.info('starting run')
    outcome = output_tfe.run('gips_tiles', *args)
    logger.info('run complete')

    # confirm generated files match expected fingerprints
    detected_files = extract_hashes(outcome.files_created)
    assert (outcome.returncode == 0
            and not outcome.stderr
            and not outcome.files_deleted
            and expected_tiles_created_files == detected_files)


expected_tiles_copy_created_files = {
    'h12v04': None, # directory
    'h12v04/h12v04_2012336_MCD_fsnow.tif': 1284302156,
    'h12v04/h12v04_2012336_MCD_obstime.tif': -1094139895,
    'h12v04/h12v04_2012336_MCD_snow.tif': -2069225181,
    'h12v04/h12v04_2012336_MOD-MYD_temp.tif': -1168080196,
    'h12v04/h12v04_2012336_MOD_clouds.tif': -221229092,
    'h12v04/h12v04_2012337_MCD_fsnow.tif': 1361214837,
    'h12v04/h12v04_2012337_MCD_indices.tif': 1837681424,
    'h12v04/h12v04_2012337_MCD_obstime.tif': -1655167224,
    'h12v04/h12v04_2012337_MCD_quality.tif': 1493878267,
    'h12v04/h12v04_2012337_MCD_snow.tif': 1201721272,
    'h12v04/h12v04_2012337_MOD-MYD_temp.tif': -746264257,
    'h12v04/h12v04_2012337_MOD_clouds.tif': 1101505794,
    'h12v04/h12v04_2012337_MOD_ndvi8.tif': 99716648,
    'h12v04/h12v04_2012337_MOD_temp8td.tif': -508252777,
    'h12v04/h12v04_2012337_MOD_temp8tn.tif': 866606587,
    'h12v04/h12v04_2012338_MCD_fsnow.tif': -647359984,
    'h12v04/h12v04_2012338_MCD_obstime.tif': -1721291893,
    'h12v04/h12v04_2012338_MCD_snow.tif': -1222056036,
    'h12v04/h12v04_2012338_MOD-MYD_temp.tif': 1547257469,
    'h12v04/h12v04_2012338_MOD_clouds.tif': -2052728372,
}


def test_e2e_tiles_copy(setup_modis_data, keep_data_repo_clean, output_tfe):
    """Test gips_tiles modis with copying."""
    # doesn't quite use STD_ARGS this time
    COPY_STD_ARGS = ('modis', '-t', 'h12v04',
                     '-d', '2012-12-01,2012-12-03', '-v', '4')
    args = COPY_STD_ARGS + ('--outdir', OUTPUT_DIR, '--notld')
    logger.info('starting run')
    outcome = output_tfe.run('gips_tiles', *args)
    logger.info('run complete')

    # confirm generated files match expected fingerprints
    detected_files = extract_hashes(outcome.files_created)
    assert (outcome.returncode == 0
            and not outcome.stderr
            and not outcome.files_deleted
            and expected_tiles_copy_created_files == detected_files)


expected_stats_created_files = {
    'clouds_stats.txt': -142855826,
    'fsnow_stats.txt': 1649245444,
    'indices_stats.txt': 551916811,
    'ndvi8_stats.txt': -1389553863,
    'obstime_stats.txt': -1289336000,
    'quality_stats.txt': 41881649,
    'snow_stats.txt': 239300424,
    'temp8td_stats.txt': 2023193464,
    'temp8tn_stats.txt': -1364990917,
    'temp_stats.txt': -1532103523
}


def test_e2e_stats(setup_modis_data, keep_data_repo_clean, output_tfe):
    """Test gips_stats on projected files."""
    # generate data needed for stats computation
    args = STD_ARGS + ('--res', '100', '100',
                       '--outdir', OUTPUT_DIR, '--notld')
    outcome = output_tfe.run('gips_project', *args)
    assert outcome.returncode == 0 # confirm it worked; not really in the test

    # compute stats
    gtfe = GipsTestFileEnv(OUTPUT_DIR, start_clear=False)
    outcome = gtfe.run('gips_stats', OUTPUT_DIR)

    # check for correct stats content
    detected_files = extract_hashes(outcome.files_created)
    assert (outcome.returncode == 0
            and not outcome.stderr
            and not outcome.files_deleted
            and expected_stats_created_files == detected_files)
