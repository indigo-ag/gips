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

import os, sys
import pprint
import traceback


import gips
from gips import __version__ as version
from gips.parsers import GIPSParser
from gips.utils import (VerboseOut, create_environment_settings,
    create_user_settings, create_repos, get_data_variables)
from gips.inventory import orm


def migrate_database():
    """
    TODO: move this into orm
    Migrate the database if the ORM is turned on.
    """
    if not orm.use_orm():
        return
    from django.core.management import call_command
    print 'Migrating database'
    orm.setup()
    call_command('migrate', interactive=False)


def create_data_variables():
    """ Create the DataVariable catalog if ORM is turned on."""
    if not orm.use_orm():
        return
    print 'Creating DataVariable catalog'
    orm.setup()
    # This import must be run after orm.setup()
    from gips.inventory.dbinv.models import DataVariable
    data_variables = get_data_variables()

    for dv in data_variables:
        name = dv.pop('name')
        dv_model, created = DataVariable.objects.update_or_create(
            name=name, defaults=dv
        )
        dv_model.save()


def configure_environment(repos_path, email, drivers, earthdata_user,
                          earthdata_password, update, **kwargs):
    try:
        cfgfile = create_environment_settings(
            repos_path, email, drivers,
            earthdata_user, earthdata_password,
            update_config=update
        )
        print 'Environment settings file: %s' % cfgfile
        print 'Creating repository directories'
        create_repos()
        migrate_database()
        create_data_variables()
    except Exception, e:
        # TODO error-handling-fix: standard script-level handler
        print traceback.format_exc()
        print 'Could not create environment settings: %s' % e
        sys.exit(1)



def main():
    import gips
    title = 'GIPS Configuration Utility (v%s)' % (version)

    parser = GIPSParser(description=title, datasources=False)
    subparser = parser.add_subparsers(dest='command')
    subparser.add_parser('print', help='Print current settings')
    p = subparser.add_parser(
        'env',
        help='Configure GIPS repositories in this environment'
    )
    p.add_argument(
        '-r', '--repos', help='Top level directory for repositories',
        default='/data/repos'
    )
    p.add_argument(
        '-e', '--email',
        help='Set email address (used for anonymous FTP sources)', default=''
    )
    p.add_argument(
        '-d', '--drivers', nargs='*',
        default=('modis', 'merra', 'landsat', 'aod'),
        help='List of drivers to enable for this installation',
    )
    p.add_argument(
        '-U', '--user',
        help='Set username for EARTHDATA login', default=''
    )
    p.add_argument(
        '-P', '--password',
        help='Set password for EARTHDATA login', default=''
    )
    p.add_argument(
        '-u', '--update',
        help='Overwrite any existing settings file with these options',
        default=False, action='store_true',
    )
    p = subparser.add_parser('user', help='Configure GIPS repositories for this user (for per user customizations)')
    #p.add_argument('-e', '--email', help='Set email address (used for anonymous FTP sources)')
    #h = 'Install full configuration file without inheriting from environment settings'
    #p.add_argument('-f', '--full', help=h, default=False, action='store_true')
    args = parser.parse_args()
    print title

    if args.command == 'print':
        try:
            from gips.utils import settings
            s = settings()
            for v in dir(s):
                if not v.startswith('__') and v != 'gips':
                    print
                    print v
                    exec('pprint.pprint(s.%s)' % v)
        except Exception as e:
            # TODO error-handling-fix: standard script-level handler
            # print traceback.format_exc()
            print 'Unable to access settings: {}'.format(e)
            sys.exit(1)

    elif args.command == 'env':
        configure_environment(**args)
    elif args.command == 'user':
        try:
            # first try importing environment settings
            import gips.settings
            cfgfile = create_user_settings()
        except ImportError:
            # TODO error-handling-fix: standard script-level handler
            print 'Could not create user settings: %s' % e

        try:
            print 'User settings file: %s' % cfgfile
            print 'Creating repository directories'
            create_repos()
            migrate_database()
            create_data_variables()
        except Exception as e:
            # TODO error-handling-fix: standard script-level handler
            print traceback.format_exc()
            print 'Could not create repository directories'
            sys.exit(1)


if __name__ == "__main__":
    main()
