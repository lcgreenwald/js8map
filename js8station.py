# JS8MAP.explore: Query remote JS8CALL stations
'''
    Ths module is part of the JS8MAP package.

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
import time
import re
import random
import js8draw as draw

FLAGS = None
canvas = None
link_timeout = 600000
station_timeout = 60*30*1000

# This hash table contains ALL known stations and their grid locations,
# from all past sessions.  It is not the same as Station.book, which
# is a hash of all the Station objects for *this* session only.
callbook = {}
localStation = None

# Station status
sUNHEARD = 0
sRECENT = 1
sFADING = 2
sLOCAL = 3

def start( fl ):
  global FLAGS, link_timeout, station_timeout, callpat, gridpat
  FLAGS = fl
  link_timeout = 60 * FLAGS.link_timeout
  station_timeout = 60 * FLAGS.station_timeout
#  callpat = re.compile('^\\d?[A-Z]+\\d[A-Z]+$')
  callpat = re.compile('^[0-9A-Z/]+$')
  gridpat = re.compile('^[A-Z]{2}[0-9]{2}$')

# Clean up messy callsigns.  These can result from incorrect
# decoding of weak signals.
def clean(c):
  global callpat
  if re.match( callpat, c ):
    return c
  return None

# Look up a known station given its call, or create a new one.
# Group names are ignored because they have no geographic location.
def gotStation(c):
  global callbook

  if not c:
    return None

  # Ignore group names
  if c[0] == '@':
    return None

  # Check active stations this session.  'Station.book' is
  # just active stations.  'callbook' is all stations ever heard.
  if c in Station.book:
    # Already know this one.
    return Station.book[c]

  # Create a new Station object.
  s = Station(c)

  # Have we seen it before?  Can fill in grid if so.
  if c in callbook:
    s.setgrid( callbook[c] )

  return s

# Load the callbook of previously discovered station
# locations.  Each line of the file contains a callsign
# and grid locator.
def load():
  global FLAGS, callbook, sLOCAL
  if os.path.isfile(FLAGS.data):
    with open(FLAGS.data, "r") as f:
      d = f.readline()
      while d:
        d = d.strip()
        # Ignore empty and comment lines.
        if d != '' and d[0] != '#':
          (c,g) = d.split(',')
          callbook[c] = g
        d = f.readline()
    f.close
  else:
    print("No callbook file {}".format(FLAGS.data))

  # Create a Station instance for the local station.
  if FLAGS.call:
    s = Station(FLAGS.call)
    localStation = s
    s.reported = 1
    s.state = sLOCAL
    if FLAGS.grid:
      s.setgrid( FLAGS.grid, saveit=0 )
    else:
      if FLAGS.call in callbook:
        s.setgrid( callbook[FLAGS.call] )

  if FLAGS.debug > 0:
    print("Callbook has {} stations".format(
      len(callbook)))

#### This class represents one station in the network.
class Station:

  book = {}    # A dictionary of all known stations, indexed by call.

  @classmethod
  def drawall(self, forcecrop=False):
    # Draw 'hearing' links underneath.
    for s1 in Station.book.values():
      for s2 in s1.links:
        draw.drawlink( s1, s2 )

    # Now draw the station names on top.  Only the ones
    # we know the positions of.
    for s1 in Station.book.values():
      s1.draw(forcecrop)

  # Mark all stations as unheard so they disappear from the map.
  # All links as well.  Only the local station remais.
  @classmethod
  def reset(self):
    global sLOCAL
    us = None
    self.hears = {}
    self.hearshown = {}

    for c,s in Station.book.items():
      s.links = []
      s.hears = {}
      draw.removeAction( s )
      if s.state != sLOCAL:
        draw.removeStation(s)
      else:
        us = s

    del Station.book
    Station.book = {}
    if us:
      Station.book[us.call] = us

    draw.needupdate('reset')

  def __init__(self, callsign):
    self.call = callsign   # Simple callsign
    self.heard = None      # Time it was last heard from
    self.links = []        # Other stations is communicating with
    self.grid = None       # Maidenhead coordinates
    self.x = 0             # Screen coorinates
    self.y = 0
    self.reported = None   # Has the station been seen in this session?
    self.latitude = None   # Geographic location
    self.longitude = None
    self.action = None     # tkinter annotation handle
    self.state = sUNHEARD  # Display state
    self.icon = None       # tkinter callsign handle
    self.heardme = False   # Has this station heard us?
    self.info = None
    self.hasmsg = False
    self.hears = {}
    self.hearshown = {}
    self.changed = True

    # Register any new instance in the dictionary of all such.
    Station.book[callsign] = self

  def addhears( self, c2 ):
    if c2.call not in self.hears:
      self.hears[ c2.call ] = c2

  # A station has announced its location.  This is important but
  # rare information so we remember it.
  def setgrid( self, loc, saveit=1 ):
    global FLAGS, gridpat, callbook
    if loc == '':
      return

    # In case somebody sent an extended grid, use just the first
    # four characters.
    loc = loc[0:4]

    # Then we check whether this is a valid grid.  A bad value
    # could turn up if somebody sent a message like:
    #    'CALL1: CALL2 GRID IS DOWN'
    if not re.match( gridpat, loc ):
      return

    # It has the proper form, so we process it.
    self.changed = True

    # Has he moved?
    if self.call in callbook:
      oldloc = callbook[self.call]
      if oldloc != loc:
        # Announce the move.  We need a better way to remember this.
        print("{} has moved from {} to {}".format( \
          self.call, oldloc, loc ))
        # We delete the old entry so the code below will treat it
        # like new information.
        del callbook[self.call]
    else:
      # Not in callbook so this is new information.
      if FLAGS.debug > 1:
        print('{} reports being at "{}"'.format(cfr,loc))

    # Remember the grid as well as map coorindates
    self.longitude, self.latitude = draw.grid2coord(loc)
    self.grid = loc

    # Give the map a chance to rezoom.
    draw.setbound(self.longitude, self.latitude)
    draw.needupdate('set grid')

    # Remember this for the future.
    if saveit and self.call not in callbook:
      callbook[self.call] = loc
      self.save()

  # Reveal everything we know about a station.
  def dump(self):
    # Various simple flags.
    flags = ''
    if self.heardme:
      flags += 'H'
    if self.hasmsg:
      flags += 'M'
    sname = ['Old','Active','Fading','Me'][self.state]
    print(' {} at {} |{}| {}'.format( \
      self.call, self.grid, flags, sname ))

    # The list of other stations heard by this one.
    names = []
    for ocall in self.hears:
      names.append( ocall )
    if len(names) > 0:
      print("   Hears {}".format(' '.join(names)))

  def CQ( self ):
    draw.actCQ(self)

  def HB( self ):
    draw.actHB(self)

  def addHeard( self, other ):
    if other:
      if other.call not in self.hears:
        if FLAGS.debug > 2:
          print("  {} heard {}".format( self.call, other.call ))
        self.hears[ other.call ] = other
        if other.state == sLOCAL:
          self.heardme = True
          self.changed = True
    
  # A station has reported all it can hear with a HEARING message.
  # We can discover new stations that we can not hear ourselves.
  # 'others' is a list of callsigns.
  def sethears(self, others):
    for c in others:
      nice = clean(c)
      if nice:
        s2 = gotStation(nice)
        self.addHeard( s2 )
    draw.needupdate('set links for {}'.format(self.call))

  def save(self):
    global FLAGS
    if FLAGS.debug > 1:
      print("Saving {} at {}".format(self.call, self.grid))
    with open(FLAGS.data, "a+") as f:
      f.write("{},{}\n".format(self.call, self.grid))

  def link(self, other):
    self.addHeard( other )
    draw.drawlink( self, other )

  def purgelinks( self ):
    global link_timeout, FLAGS
    since = self.age()
    if not since or since < link_timeout:
      return
    if FLAGS.debug > 3:
      print("Checking links from {}".format(self.call))
    for other in self.links:
      since = other.age()
      if not since or since > link_timeout:
        self.links.remove( other )
        if FLAGS.debug > 2:
          print("  Removed link from {} to {}".format(
            self.call, other.call))
        draw.needupdate('purge links for {}'.format(self.call))

  def age(self):
    if self.heard:
      now = datetime.datetime.now()
      return (now - self.heard).seconds
    else:
      return None

  # Put a represenation of the station onto the map.
  def draw(self, forcecrop=False):
    global local, station_timeout, FLAGS, callfont
    global sLOCAL, sRECENT, sUNHEARD, sFADING

    # We can't draw it if we do not know where it is.
    if not self.grid:
      return

    # Display color depends on how recently we heard from it.
    if self.state != sLOCAL:     # We never change
      if self.reported:
        recent = self.age()
        if recent < station_timeout:  # It is recent
          self.state = sRECENT
        else:
          self.state = sFADING
      else:
        self.state = sUNHEARD

    draw.drawstation( self, forcecrop )
