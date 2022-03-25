'''
    This module is part of JS8MAP.  It manages the display of a map
    of the world.

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

import os
from tkinter import *
from PIL import Image, ImageFont, ImageDraw
from PIL import ImageTk
import tkinter as tk
from tkinter import font
import js8draw as draw

canvas = None
FLAGS = None

# This class represents all the available underlay map files
# and holds the propererties that allow for zooming and scaling.
class MapSpec:

  mapfiles = []
  selected = None
  mapdir = None

  @classmethod
  def load( self ):
    srcpath = os.path.abspath(__file__)
    MapSpec.mapdir = os.path.dirname(srcpath) + "/maps/"
    ifname = MapSpec.mapdir + 'index.dat'
    if not os.path.isfile(ifname):
      print("No map index file {}".format(ifname))
      return
    
    with open(ifname, "r") as f:
      d = f.readline()
      while d:
        d = d.strip()
        # Ignore empty and comment lines.
        if d != '' and d[0] != '#':
          fname, llng, rlng, blat, tlat, \
            lmar, rmar, bmar, tmar, gamut = d.split(',')
          MapSpec.mapfiles.append( MapSpec( \
            fname, \
            llng, rlng, blat, tlat, \
            lmar, rmar, bmar, tmar, gamut))
        d = f.readline()
    f.close

  @classmethod
  def list(self):
    names = []
    for m in MapSpec.mapfiles:
      names.append( m.filename )
    return names

  @classmethod
  def select(self, n):
    MapSpec.selected = MapSpec.mapfiles[n]
    draw.gamut = MapSpec.selected.color_gamut
    return MapSpec.selected

  def __init__(self, fname, llng, rlng, blat, tlat, \
               lmar, rmar, bmar, tmar, gamut):
    self.filename = fname
    self.left_longitude = int(llng)
    self.right_longitude = int(rlng)
    self.bottom_latitude = int(blat)
    self.top_latitude = int(tlat)
    self.left_margin = int(lmar)
    self.right_margin = int(rmar)
    self.bottom_margin = int(bmar)
    self.top_margin = int(tmar)
    self.color_gamut = int(gamut)

  def __str__(self):
    return "File '{}' Long=[{:.1f} {:.1f}] Lat=[{:.1f} {:.1f}]".format( \
      self.filename, self.left_longitude, self.right_longitude, \
      self.bottom_latitude, self.top_latitude)

def mstretch( lat ):
  return math.secant( math.radians(lat) )

# Convert a Latitude and Longitude to a grid coordinate.
def ll2grid(lng, lat):
  # Correct origins
  lat1=lat+90
  lng1=lng+180
  # Scale to A-R in 18 steps.  360/18 = 20 and 180/18 = 10.
  lnga = lng1/20
  latb = lat1/10
  # Split high and low order
  lnga1 = int(lnga)
  lngc1 = int((lnga - lnga1)*10)
  latb1 = int(latb)
  latd1 = int((latb - latb1)*10)
  # High order becomes letters, lo order becomes digits
  a = chr(65+lnga1)
  b = chr(65+latb1)
  c = chr(48+lngc1)
  d = chr(48+latd1)
  return a + b + c + d

# This class represents the world map background.  Which map is
# actually used is specified by the user.
class World:

  # Initialize
  def __init__(self, cnv, flg):
    global canvas, FLAGS

    canvas = cnv
    FLAGS = flg
    self.map_ll = self.map_ur = None
    self.setmap( FLAGS.map )

  # Select a new background map.  We have loaded its specifics
  # from the index.dat file and set up the scaling based on its
  # actual image size.
  @classmethod
  def setmap( self, mnum ):
    self.m = MapSpec.select( mnum )

    fullname = MapSpec.mapdir + self.m.filename
    if not os.path.isfile( fullname ):
      print("World map file '{}' not found".format( fullname ))
      return None

    # Read the file, and we learn how big it is.
    self.raw = Image.open( fullname )
    self.rawx = self.raw.width
    self.rawy = self.raw.height

    # We would like the useful width of the map to be 360 degrees
    # and the useful height to be 90 degrees, but sometimes they
    # are not so we compute pixes-per-degree.
    self.pixlng = (self.rawx - \
      (self.m.right_margin + self.m.left_margin)) / \
      (self.m.right_longitude - self.m.left_longitude)
    self.pixlat = \
      (self.rawy - self.m.top_margin - self.m.bottom_margin) / \
      (self.m.top_latitude - self.m.bottom_latitude)

    self.cropped = None
    self.fitted = None
    self.image = None

    if FLAGS.debug > 3:
      print("New raw map image {} by {}".format( \
           self.rawx, self.rawy ))

    draw.needupdate()

  # Select the part of the map to be displayed.  The world
  # coordinates bounding box is converted to pixels within
  # the image.  This can change if the user types +->< or
  # if the auto-zooming is active.  This must be called before
  # fit().
  def zoom( self, lngmin, lngmax, latmin, latmax ):
    global canvas, FLAGS

    # Convert coordinates back to grid names.
    ll = ll2grid( lngmin, latmin )
    ur = ll2grid( lngmax, latmax )

    # If nothing has changed, no need to do anything.
    if ll == self.map_ll and ur == self.map_ur:
      return

    if FLAGS.debug > 0:
      print("Map corners {},{}".format(ll, ur))

    FLAGS.corners = ll + ',' + ur

    # Remember the new corners for next time.
    self.map_ll = ll
    self.map_ur = ur

    if self.cropped:
        del self.cropped

    # Convert longitude degrees to pixels in the image.
    Lx = int((lngmin - self.m.left_longitude) * \
             self.pixlng) + self.m.left_margin
    Rx = int((lngmax - self.m.left_longitude) * \
             self.pixlng) + self.m.left_margin

    By = self.rawy - int((latmin - self.m.bottom_latitude) * \
             self.pixlat) + self.m.top_margin
    Ty = self.rawy - int((latmax - self.m.bottom_latitude) * \
             self.pixlat) + self.m.top_margin

    # Make a cropped verion
    # Give coordinates of NW and SE corners.
    self.cropped = self.raw.crop( (Lx, Ty, Rx, By) )

  # Fit the zoomed image to the current canvas size.  This
  # can change if the user resizes the main window.
  def fit( self):
    global canvas
    if self.image:
        canvas.delete(self.bg)
        del self.bg
        del self.fitted
        del self.image

    self.fitted = self.cropped.resize(
      (canvas.winfo_width(), canvas.winfo_height()),
      Image.ANTIALIAS)

    self.image = ImageTk.PhotoImage(self.fitted)
    self.bg = canvas.create_image( 0, 0, image=self.image, anchor=tk.NW )

    # Make sure the world map stays behind everything else.
    canvas.lower( self.bg )
