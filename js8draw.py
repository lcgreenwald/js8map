# JS8DRAW: Manage the visual map
'''
    This module is part of JS8MAP.

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
from tkinter import *
from PIL import Image, ImageFont, ImageDraw
from PIL import ImageTk
import tkinter as tk
from tkinter import font
import js8station as sta
import js8explore as explore
import js8world as world
import datetime

update_needed = False
canvas = None
menuLockFlag = None
congestion = 0
worldmap = None
cropneeded = True
fitneeded = True
doingcrop = False
gamut = 0
resetTime = None
showHistory = False
infoBox = None

# We want the map to resize when the user stretches the main window.
class ResizingCanvas(Canvas):

  lastResize = None

  def __init__(self,parent,**kwargs):
    Canvas.__init__(self,parent,**kwargs)
    self.bind("<Configure>", self.on_resize)
    self.bind("<Button-1>", self.on_click)
    self.height = self.winfo_reqheight()
    self.width = self.winfo_reqwidth()

  def on_resize(self,event):
    # User has resized the window.  Scale the map to match.
    global cropneeded, update_needed, swid, shgt, FLAGS
    swid = self.width = FLAGS.width = event.width
    shgt = self.height = event.height
    self.config(width=self.width, height=self.height)
    cropneeded = True
    needupdate('resize')
    repaint()

  # Respond to mouse clicks on the map.  If the click is close
  # enough to a station, we show what we know about it.
  def on_click(self, event):
    global infoBox, canvas
    # Remove any existing info first.
    canvas.delete( 'info' )

    # Find the station we clicked on.
    for s in sta.Station.book.values():
      if abs( event.x - s.x ) < 20 and \
         abs( event.y - s.y ) < 10:
        drawStationInfo(s)
        return

    # Nothing clicked on.  Remove any existing text.

# Intialize the drawing context within the provided application window.
def start( w, f, lockFlag ):
  global window, canvas, callfont, logofont, logo, shgt, swid, FLAGS
  global worldmap, resetTime, callfont2, menuLockFlag
  window = w
  menuLockFlag = lockFlag
  FLAGS = f
  resetTime = datetime.datetime.now()

  # Create font definitions.
  callfont = font.Font(family="Arial", size=12, weight="bold")
  callfont2 = ('Arial 12 bold underline')
  logofont = font.Font(family="mincho", size=30)

  # Create the canvas, filling the window.  It is an automatically
  # reszing canvas.
  canvas = ResizingCanvas(window,
    width=window.winfo_width(), height=window.winfo_height(),
    background='black')
  canvas.pack()
  canvas.update()

  swid = canvas.winfo_width()
  shgt = canvas.winfo_height()

  # Load map descriptors and choose one.
  world.MapSpec.load()
  
  worldmap = world.World( canvas, FLAGS )

  # We flash a temporary logo and version for 3 seconds.
  flash_message( "JS8MAP\nVersion 0.7" )

  # Update clock once per minute
  window.after( 60000, clock_tick )

def flash_message( msg ):
  global logo, logofont, canvas
  logo = canvas.create_text(int(swid/2), int(shgt/2), \
      text=msg, \
    fill='cyan1', font=logofont, justify=tk.CENTER )
  window.after( 3000, remove_logo )
  
def setmap( self, mnum ):
  worldmap.setmap( mnum )

def clock_tick():
  needupdate()
  window.after( 60000, clock_tick )

########## Convert Grid coordinates ############
minx = 200
miny = 100
maxx = -200
maxy = -100
xscale = 1
yscale = 1
oldcrop = (minx, maxx, miny, maxy)

# Dump out known stations, for debugging.
def dump(x):
  global xscale, yscale, minx, miny, maxx, maxy  
  global shgt, swid
  for s in sta.Station.book.values():
    print("  {} at {} detected {} state {} with {} links".format(
      s.call,s.grid,s.reported,s.state, len(s.links)))

# Fit a bounding box around all observed stations.  This has
# the effect of zooming the map to enclose those stations.
def setbound(x,y, observeLock=True):
  global minx, miny, maxx, maxy, oldcrop
  global cropneeded, fitneeded, FLAGS

  if FLAGS.debug > 4:
    print('setbound to {},{} locked {}'.format(x,y,menuLockFlag.get()))

  # Do not move the map automatically if lock is set.
  if observeLock and menuLockFlag.get():
    if FLAGS.debug > 4:
      print('Limits stay at [{} {}], [{} {}]'.format( \
          minx, maxx, miny, maxy))
    return

  minx = min(x-6,minx)
  miny = min(y-3,miny)
  maxx = max(x+6,maxx)
  maxy = max(y+3,maxy)
  newcrop = (minx, maxx, miny, maxy)
  if newcrop != oldcrop:
    cropneeded = True
    oldcrop = newcrop

# Convert grid name to longitude and latitude degrees.
# Cells go A-R for 360 degrees or 20 deg per major cell in
# longitude, and A-R for 180 degrees in latitude.
# So cells are twice as wide as they are tall.
def grid2coord(g):
  if len(g) < 4:
    print("Bad grid '{}'".format(g))
    return (-90,40)

  lng = ((ord(g[0]) - ord('A')) * 10 + (ord(g[2]) - ord('0'))) * 2 - 180+1
  lat = ((ord(g[1]) - ord('A')) * 10 + (ord(g[3]) - ord('0'))) - 90
  
  return (lng, lat)

########## Drawing the map ############

# Get screen coordinates for a station.  tkinter puts origin
# at upper left corner so we also invert the Y axis.
# Values of minx/y and xscale/yscale must reflect the
# current map zoom.
def screen_coordinates(s):
  global xscale, yscale, minx, miny, shgt
  if not s.longitude:
    return None, None

  sx = int(xscale*(s.longitude - minx))
  sy = shgt - int(yscale*(s.latitude - miny))
  return sx, sy

def clearHistory( s=None ):
  global canvas
  if s:
    for line in s.hearshown.values():
      canvas.delete( line )
    s.hearshown = {}
  else:
    for s2 in sta.Station.book.values():
      clearHistory(s2)

# Draw links to all heard by this station at any time during
# this session.
def drawhears( sfr ):
  global gamut
  if not sfr:
    return
  if len(sfr.hears) == 0:
    return

  linecolor = ['grey64', 'grey48'][gamut]

  # Get where this station is on the screen.
  x1, y1 = screen_coordinates(sfr)

  # Draw a faint line each other station.
  for other in sfr.hears.values():
    # Get location for each heard station.
    x2, y2 = screen_coordinates(other)
    if x1 and x2:
      # We know its location.  If we already drew a line,
      # delete it in case it moved.
      if other.call in sfr.hearshown:
        gfx = sfr.hearshown[ other.call ]
        canvas.delete(gfx)
      # Draw the line from 'sfr' to 'other'
      gfx = canvas.create_line( x1, y1, x2, y2, fill=linecolor )
      sfr.hearshown[ other.call ] = gfx

# Draw the line between two communicating stations.  This line is
# temporary and represent something happening right now.
def drawlink( sfr, sto ):
  global canvas
  if not sfr:
    return
  if not sto:
    return

  # Request grid if not yet available
  if not sfr.grid:
    explore.getGrid(sfr)
    return

  if not sto.grid:
    explore.getGrid(sto)
    return

  x1, y1 = screen_coordinates(sfr)
  x2, y2 = screen_coordinates(sto)
  if x1 and x2:
    setAction( sfr, canvas.create_line( x1, y1, x2, y2, fill='wheat1' ))

# Add an action indication to a station that will be removed in
# one JS8 cycle.
def setAction( s, a ):
  global window
  removeAction( s )
  s.action = a
  window.after( 14000, removeAction, s )
  needupdate()

# Remove the notation of a station action.
def removeAction( s ):
  global canvas
  if s.action:
    canvas.delete( s.action )
    s.action = None
    needupdate('action')

def removeStation( s ):
  global canvas
  if s.icon:
    canvas.delete( s.icon )
    s.icon = None
    needupdate('action')

def actCQ( s ):
  global canvas
  x, y = screen_coordinates( s )
  if x:
    setAction( s, canvas.create_oval( x-20, y-20, x+20, y+20,
            width=3, outline='green'))

def actHB( s ):
  global canvas
  x, y = screen_coordinates( s )
  if x:
    setAction( s, canvas.create_oval( x-20, y-20, x+20, y+20,
            width=3, outline='pink'))

# Draw a JS8 station on the map.  It can be shown as the callsign
# or as a colored dot.
def drawstation( s, doingcrop=False ):
  global FLAGS, gamut, callfont, callfont2, showHistory

  # Select color by station state.
  color = [['red', 'white', 'cyan2', 'orchid1'], \
           ['red', 'blue2', 'turquoise3', 'green4']][gamut][s.state]

  s.x, s.y = screen_coordinates( s )
  if FLAGS.debug > 4:
    print("Plot {} at {}, {}".format( s.call, s.x, s.y ))

  # If style of icon changes, we may need to recreate it.
  if s.icon:
    oldShape = canvas.type( s.icon )
    if (FLAGS.icon and oldShape != 'oval') or \
       (not FLAGS.icon and oldShape != 'text'):
      canvas.delete( s.icon )
      del s.icon
      s.icon = None

  if s.heardme:
    sfont = callfont2
  else:
    sfont = callfont

  # Existing station icons just get tweaked.  New ones get
  # created.
  if s.icon:
    # Hint we might be moving.
    if doingcrop:
      oldCoords = canvas.coords(s.icon)
      dX = s.x - oldCoords[0]
      dY = s.y - oldCoords[1]
      if dX != 0 or dY != 0:
        canvas.move( s.icon, dX, dY )
    # Update color
    canvas.itemconfigure( s.icon, fill=color )
    # Update if they heard us
    if not FLAGS.icon:
      canvas.itemconfigure( s.icon, font=sfont )
  else:
    # Choose the appropriate visual representation.
    if FLAGS.icon:
      s.icon = canvas.create_oval( s.x-6, s.y-6, s.x+6, s.y+6, \
        fill=color, outline=['white', 'black'][gamut] )
    else:
      s.icon = canvas.create_text( s.x, s.y, \
        text=s.call, fill=color, font=sfont)

  # This has to come after updating position
  if showHistory:
    drawhears( s )

    s.changed = False

# Draw a text box with various information about one station.
def drawStationInfo(s):
  global canvas, callfont, FLAGS

  # Build a report about this station.
  rpt = "{} grid {}".format( s.call, s.grid )
  if s.heard:
    age = int((datetime.datetime.now() - s.heard).seconds/60)
    rpt += '\nLast heard {} min ago'.format(age)
  names = []
  for ocall in s.hears:
    names.append( ocall )
  if len(names) > 0:
    rpt += "\nHears {}".format(' '.join(names))
  if s.info:
    rpt += "\nInfo: {}".format( s.info )

  # Put all that in a text item.
  infoBox = canvas.create_text( s.x, s.y, width=300, \
     text=rpt, fill='black', font=callfont, tags='info' )
  # Draw a box around it.
  bounds = canvas.bbox(infoBox)
  canvas.create_rectangle( \
    bounds[0]-4, bounds[1]-4, bounds[2]+4, bounds[3]+4, \
    fill='yellow', outline='blue', tags='info', width=3 )
  # Then move the text in front of the box.
  canvas.tag_raise( infoBox )

# Remove the logo that appears at startup.
def remove_logo():
  global canvas, logo
  canvas.delete(logo)
  logo = None

def needupdate( why=None ):
  global update_needed, FLAGS
  if FLAGS.debug > 3:
    if why:
      print("Refresh because {}".format(why))
  update_needed = True

# Recompute the zoom factors to preserve aspect ratio.
def rezoom():
  global minx, miny, maxx, maxy, xscale, yscale, swid, shgt
  global worldmap, cropneeded, fitneeded, doingcrop
  # width = 1 + maxx - minx
  # height = 1 + maxy - miny
  # XR = width / height   # Radio of x/y ranges
  # SR = swid / shgt      # Ratio of window dimensions
  # RR = XR / SR

  # if RR > 1.0:
  #   # x/y too wide, so stretch vertically
  #   ydiff = height * RR / 2
  #   maxy += ydiff
  #   miny -= ydiff
  # else:
  #   # xy/y too short, so stretch horizontally
  #   xdiff = width / RR / 2
  #   maxx += xdiff
  #   minx -= xdiff

  if minx > 199.0:
    return

  if cropneeded:
    cropneeded = False
    doingcrop = True
    fitneeded = True
    if FLAGS.debug > 2:
      print("Map zoom to [{:.1f} {:.1f}] to [{:.1f} {:.1f}]".format( \
        minx, maxx, miny, maxy))

  if worldmap:
    worldmap.zoom( minx, maxx, miny, maxy )

    if fitneeded:
      fitneeded = False
      worldmap.fit()

# Update the entire map.
def repaint():
  global canvas, callfont, swid, shgt, minx, miny, maxx, maxy
  global congestion, xscale, yscale, update_needed, doingcrop, gamut
  global FLAGS, menuLockFLag

  if not update_needed:
    return
  update_needed = False

  # Remove all 'temporary' objects.
  canvas.delete("temp")

  rezoom()

  # Compute final scale factors
  xspan = max(1, maxx - minx)
  yspan = max(1, maxy - miny)
  xscale = swid / xspan
  yscale = shgt / yspan

  if FLAGS.debug > 4:
    print(" Xspan {:.1f} scale {:.1f} Yspan {:.1f} scale {:.1f}".format( \
      xspan, xscale, yspan, yscale))

  sta.Station.drawall(doingcrop)

  # Report observed activity level.
  duration = (datetime.datetime.now() - resetTime).seconds
  hours = int(duration / 3600)
  minutes = int((duration/60) % 60)

  canvas.create_text( 10, 10, tags='temp', \
      fill=['yellow','black'][gamut], \
                      state=tk.DISABLED, anchor=tk.NW, \
      text="Congestion {} duration {}:{:02d}".format( \
      congestion, hours, minutes), font=callfont)

  doingcrop = False

def setCongestion( c ):
  global congestion
  congestion = c

# Set the map to enclose a pair of grid cooridnates.
def setzoom( spec ):
  global menuLockFlag, FLAGS
#  if not re.match('^[A-Z0-9,]$', spec):
#    print("Bad --lock syntax")
#    return

  if FLAGS.debug > 1:
    print("Setting zoom to {} lock is {}".format(spec,menuLockFlag.get()))

  if spec:
    ll, ur = spec.split(",")
  else:
    ll = 'AA00'
    ur = 'RR99'

  # Supply low-order digits if missing.
  if len(ll) < 4:
    ll += '00'
  if len(ur) < 4:
    ur += '99'

  x, y = grid2coord(ll)
  # A little bigger if just using station location.
  if ll == ur:
    x -= 6
    y -= 3
  setbound(x,y,False)

  x, y = grid2coord(ur)
  if ll == ur:
    x += 6
    y += 3
  setbound(x,y,False)

  rezoom()

# Slide the map by percentages
def pan( xoffset, yoffset, zoffset ):
  global minx, maxx, miny, maxy, cropneeded
  xspan = maxx - minx
  tweak = xoffset / 200 * xspan
  if -180 <= (minx + tweak) <= +180 and \
     -180 <= (maxx + tweak) <= +180:
    minx += tweak
    maxx += tweak

  yspan = maxy - miny
  tweak = yoffset / 200 * yspan
  if -90 <= (miny + tweak) <= +90 and \
     -90 <= (maxy + tweak) <= +90:
    miny += tweak
    maxy += tweak

  tweak = zoffset / 200 * xspan
  if -180 <= (minx + tweak) <= +180 and \
     -180 <= (maxx + tweak) <= +180:
    minx += tweak
    maxx -= tweak

  tweak = zoffset / 200 * yspan
  if -90 <= (miny + tweak) <= +90 and \
     -90 <= (maxy + tweak) <= +90:
    miny += tweak
    maxy -= tweak

  cropneeded = True
