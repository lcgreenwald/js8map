# JS8CONFIG: Save and load settings for JS8MAP
'''
    JS8CONFIG is part of the JS8MAP package.  It deals with configuration
    options on the commnad line and INI file.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
'''
    
import os, sys
import datetime
import re
import configparser
import argparse

FLAGS = None

# Initialize all options, first from the configuration file, if any,
# and then from the commnad line.
def start():
    global FLAGS, inifile
    
    # First see if command line specifies a config file.  The
    # default is js8map.ini in the same directory as the source files.
    srcpath = os.path.abspath(__file__)
    cfpath = os.path.dirname(srcpath) + "/js8map.ini"

    p = argparse.ArgumentParser()
    p.add_argument( '--config', default=cfpath, \
                    help='Configuration file name' )
    p.add_argument( '--debug', type=int, default=0,
      help='Level of tracing output')
    FLAGS, unparsed = p.parse_known_args()

    # Load from the config file, if any.
    load( FLAGS.config )

    # Now the command line can override what the config file said.
    p.add_argument( '--call', default=FLAGS.call,
      help='Local station callsign')
    p.add_argument( '--grid', default=FLAGS.grid,
      help='Local station grid location')
    p.add_argument( '--width', type=int, default=FLAGS.width,
      help='Width of window in pixels')
    p.add_argument( '--lock', action='store_true', \
                     default=FLAGS.lock)
    p.add_argument( '--data', default=FLAGS.data,
                    help='File to save information')
    p.add_argument( '--corners', default=FLAGS.corners )
    p.add_argument( '--link_timeout', type=int, default=15,
      help="Minutes until links fade")
    p.add_argument( '--station_timeout', type=int, default=30,
      help="Minutes until stations turn blue")
    p.add_argument( '--map', type=int, default=FLAGS.map,
      help='Map file selector')
    p.add_argument( '--port', type=int, default=FLAGS.port,
      help='UDP port from JS8CALL')
    p.add_argument( '--tx', action='store_true', default=FLAGS.tx,
      help='Enable exploratory transmission')
    p.add_argument( '--icon', action='store_true', \
                    default=FLAGS.icon, \
                    help='Display stations as icons')

    FLAGS, unparsed = p.parse_known_args()
    return FLAGS

# Load options from an INI-formated file.
def load( fname ):
    global FLAGS

    if FLAGS.debug > 0:
        print("Reading configuration from {}".format(fname))

    c = configparser.ConfigParser()
    if not c.read( fname ):
        print('Unable to read configuration file "{}"'.format(fname))
        # Fake an empty configuration so that all the defaults
        # will be taken below
        c = {}

    srcpath = os.path.abspath(__file__)
    cbpath = os.path.dirname(srcpath) + "/callbook.dat"

    # If a section exists we can read it.  Otherwise we just
    # set the defaults.
    if 'STATION' in c:
        s = c['STATION']
        FLAGS.call = s.get('call', None)
        FLAGS.grid = s.get('grid', None)
        FLAGS.data = s.get('data', cbpath)
    else:
        FLAGS.call = None
        FLAGS.grid = None
        FLAGS.data = cbpath
        
    if 'JS8CALL' in c:
        j = c['JS8CALL']
        FLAGS.port = j.get('port', 2242 )
        FLAGS.tx = s.getboolean('transmit', False)
    else:
        FLAGS.port = 2242
        FLAGS.tx = False

    if 'MAPS' in c:
        m = c['MAPS']
        FLAGS.lock = m.getboolean('lock', True)
        FLAGS.icon = m.getboolean('icon', False)
        FLAGS.corners = m.get('corners', None)
        FLAGS.map = m.getint('map', 0)
        FLAGS.width = m.getint('width', 600)
    else:
        FLAGS.lock = False
        FLAGS.width = 800
        FLAGS.map = 0
        FLAGS.corners = None
        FLAGS.icon = False

# Write a new INI file from the current settings.
def save( fname=None ):
    global FLAGS

    # Build a new configuration object with all the current
    # FLAGS values.
    c = configparser.ConfigParser()
    c['STATION'] = {'call': FLAGS.call, \
                    'grid': FLAGS.grid }
    c['JS8CALL'] = {'port': str(FLAGS.port) }
# NYI                    'transmit': str(FLAGS.tx) }
    c['MAPS'] = {'width': str(FLAGS.width), \
                 'corners': FLAGS.corners, \
                 'lock': str(FLAGS.lock), \
                 'map': str(FLAGS.map) }
    
    # Where the file is written can be specified various ways.
    if fname:
        cfgfile = fname
    elif 'config' in FLAGS:
        cfgfile = FLAGS.config
    else:
        srcpath = os.path.abspath(__file__)
        cfgfile = os.path.dirname(srcpath) + "/js8map.ini"

    with open( cfgfile, "w") as f:
        c.write(f)

