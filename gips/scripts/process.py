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

from gips import __version__
from gips.parsers import GIPSParser
from gips.core import SpatialExtent, TemporalExtent
from gips.utils import Colors, VerboseOut, open_vector, import_data_class
from gips import utils
from gips.inventory import DataInventory
from gips.inventory import orm
from functools import reduce


def main():
    title = Colors.BOLD + 'GIPS Data Processing (v%s)' % __version__ + Colors.OFF

    # argument parsing
    parser0 = GIPSParser(description=title)
    parser0.add_inventory_parser()
    parser0.add_process_parser()
    args = parser0.parse_args()

    cls = utils.gips_script_setup(args.command, args.stop_on_error)
    print(title)

    with utils.error_handler():
        extents = SpatialExtent.factory(
            cls, site=args.site, rastermask=args.rastermask,
            key=args.key, where=args.where, tiles=args.tiles,
            pcov=args.pcov, ptile=args.ptile
        )
        batchargs = None
        if args.batchout:
            tdl = []
            batchargs = '--chunksize ' + str(args.chunksize)
            batchargs += ' --format ' + str(args.format)
            batchargs += ' --numprocs ' + str(args.numprocs)
            batchargs += ' --verbose ' + str(args.verbose)
            if args.overwrite:
                batchargs += ' --overwrite '
            if args.products:
                batchargs += ' -p ' + ' '.join(args.products)

        for extent in extents:
            inv = DataInventory(
                cls, extent,
                TemporalExtent(args.dates, args.days), **vars(args)
            )
            if args.batchout:
                def get_commands(tiles_obj):
                    commands = []
                    for tile in tiles_obj.tiles.keys():
                        needed = any([p not in [k for sen, k in tiles_obj.tiles[tile].filenames.keys()]
                                      for p in args.products])
                        if not needed:
                            continue
                        commands.append(args.command + ' -t ' + str(tile) +
                                    ' -d ' + str(tiles_obj.date) + ' ' +
                                    batchargs + '\n')
                    return commands


                tdl = reduce(
                    list.__add__,
                    map(
                        get_commands,
                        inv.data.values()
                    ),
                    tdl
                )

            else:
                inv.process(overwrite=args.overwrite)
        if args.batchout:
            with open(args.batchout, 'w') as ofile:
                ofile.writelines(tdl)

    utils.gips_exit() # produce a summary error report then quit with a proper exit status


if __name__ == "__main__":
    main()
