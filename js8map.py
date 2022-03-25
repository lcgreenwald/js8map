# JS8MAP: Collect station and network data from JS8CALL
'''
    This is the main module of JS8MAP.  It handles user interactions
    and analyzes information coming from the JS8CALL program.

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
    
import argparse
import os, sys
import socket
from PIL import Image, ImageFont, ImageDraw
from PIL import ImageTk
import tkinter as tk
from tkinter import font
import datetime
import time
import json
import re
import js8explore as explore
import js8station as sta
import js8draw as draw
import js8world as world
import js8config as cfg

# Load configuration from INI file and command line.
FLAGS = cfg.start()

if FLAGS.debug > 0:
  print("Settings: {}".format(FLAGS))

####### Initialize globals
band = 0
congestion = 0
cmdcount = 0
link_interval = FLAGS.link_timeout * 60 * 1000
measurement_interval = 10 * 60000   # Ten Minute measurement interval

########## Processing user inputs ###########
  
def toggleIcons(x=None):
  global FLAGS, showIconsFlag
  if x:
    showIconsFlag.set( 1 - showIconsFlag.get() )
  FLAGS.icon = showIconsFlag.get() > 0
  draw.needupdate('Icons')

def toggleHistory(x=None):
  global FLAGS, showHistoryFlag
  if x:
    showHistoryFlag.set( 1 - showHistoryFlag.get() )
  draw.showHistory = showHistoryFlag.get() > 0
  if showHistoryFlag.get() == 0:
    draw.clearHistory()
  draw.needupdate('History')

def setmap(mnum):
  world.World.setmap( mnum )
  draw.cropneeded = True
  draw.needupdate('Map')

def panright(ev):
  draw.pan( +10, 0, 0 )
  draw.needupdate('Manual')

def panleft(ev):
  draw.pan( -10, 0, 0 )
  draw.needupdate('Manual')

def panup(ev):
  draw.pan( 0, +10, 0 )
  draw.needupdate('Manual')

def pandown(ev):
  draw.pan( 0, -10, 0 )
  draw.needupdate('Manual')

def zoomin(ev=None):
  draw.pan(0, 0, +10 )
  draw.needupdate('Manual')

def zoomout(ev=None):
  draw.pan(0, 0, -10)
  draw.needupdate('Manual')

# Save the configuration for next startup.
def saveconfig(ev=None):
  global lockedFlag, FLAGS
  # Update FLAGS to match latest menu setting.
  FLAGS.lock = lockedFlag.get()
  cfg.save( )
  draw.flash_message("Configuratiuon saved")

def dump(x=None):
  print("Information about all stations")
  for s in sta.Station.book.values():
    s.dump()

######### Processing events from JS8CALL ##############
# Compute average messages per hour.  This is the 'congestion'
# level and is used to throttle automatic transmissions.
def measure():
  global cmdcount, measurement_interval, window
  global congestion
  congestion = int(cmdcount * 3.6E6 / measurement_interval)
  cmdcount = 0
  draw.needupdate( 'measure' )
  draw.setCongestion( congestion )
  window.after( measurement_interval, measure)

# Look for obsolete links from time to time.
def check_links():
  global window, link_interval
  for s in sta.Station.book.values():
    s.purgelinks()
  window.after( link_interval, check_links )

# Force quit.
def manual_quit(x):
  sys.exit()

# Watch frequency changes and update title bar.
def updatefreq( js8 ):
  global window, band
  mhz = int(js8['FREQ'] / 1000000)
  if mhz != band:
    band = mhz
    window.title("JS8 network on {} MHz".format(band))
    # Also clear out the map because we will find new stations
    # on this band.
    draw.resetTime = datetime.datetime.now()
    draw.clearHistory()
    sta.Station.reset()

def BHearsA( s, oth ):
  global FLAGS
  if not s or not oth:
    return
  if FLAGS.debug > 3:
    print("{} can hear {}".format( oth.call, s.call ))
  if s.state == sta.sLOCAL:
    oth.heardme = True
    oth.changed = True
  s.addHeard( oth )

# Process a CMD event from JS8CALL.  These represents all
# the substantive messages.
def do_cmd(js8):
  global window,band, cmdcount, FLAGS, msg

  c = js8['CMD'].strip()

  # Collect misc statistics
  tdrift = float(js8['TDRIFT'])
  offset = int(js8['OFFSET'])

  # Strip callsigns of extraneous modifiers
  cfr = sta.clean(js8['FROM'])
  cto = sta.clean(js8['TO'])
  lvl = int(js8['SNR'])

  sfr = sta.gotStation(cfr)
  sto = sta.gotStation(cto)

  # Several commands have useful information in the TEXT field.
  # We split it up for easy processing, and remove the
  # 'end-of-transmission' marker.
  txtlist = js8['TEXT'].strip().split(' ')[3:]
  if len(txtlist) > 0:
    txtlist.pop()
  txt = ' '.join(txtlist)

  if FLAGS.debug>2:
    print('{} to {} SNR={} TD={:.1f} OFF={} says "{}"'.format( \
        cfr, cto, lvl, tdrift, offset, txt))

  # Remember that we have heard these stations.  There might
  # be no destination station if it was a group.
  sfr.heard = datetime.datetime.now()
  sfr.level = lvl
  sfr.reported = 1
  if sto:
    sto.reported = 1
    sto.heard = sfr.heard
    # A message sent to me suggests the other station
    # has heard me.
    BHearsA( sfr, sto )

  if c == '':
    sfr.link( sto )
    if FLAGS.debug > 0:
      t = js8['TEXT'].strip()
      print("  {}".format(t))

  elif c == 'HEARTBEAT' or c == 'GRID':   
    # Somebody advertises their location.
    loc = js8['GRID'].strip()
    # Bug in JS8CALL - if station reports 6-character grid,
    # the GRID field will be empty so we have to look in the text.
    if len(loc) == 0:
      loc = txtlist.pop()
    if c == 'HEARTBEAT':
      sfr.HB()
    sfr.setgrid( loc )

  elif c == 'HEARING':
    # A good way to learn about stations we can not hear.
    # The text is CFR: CTO HEARING c1 c2 c3
    sfr.link(sto)
    if FLAGS.debug > 1:
      print('{} hears {}'.format(sfr.call, txtlist))
    sfr.sethears( txtlist )

  elif c == 'HEARTBEAT SNR' or c == 'SNR':
    # A station sending an SNR report has presumably heard the
    # station they are sending it to.
    if sto:
      BHearsA( sto, sfr )
      sfr.link( sto )
      sto.link( sfr )

  elif c == 'SNR?':
    sfr.link( sto )

  elif c == 'NO' or c == 'YES':
    # If somebody replies NO, then they must have
    # heard the query.
    sfr.link( sto )
    BHearsA( sto, sfr )

  elif c == 'INFO':
    sfr.info = txt
    if FLAGS.debug > 0:
      print('{} info {}'.format(sfr.call, txt))

  elif c == 'CQ':
    # It is common to send a message of "CQ CQ CQ grid"
    loc = txtlist.pop()
    if len(loc) == 4:
      sfr.setgrid( loc )
    sfr.CQ()

  elif c == 'INFO' or c == 'MSG':
    sfr.link( sto )
    BHearsA( sto, sfr )

  elif c == 'ACK':
    sto.addHeard(sfr)
    sfr.link( sto )

  elif c == 'HW CPY?':
    BHearsA( sto, sfr )
    sfr.link(sto)

  else:
    # Ignore anything else
    if FLAGS.debug > 4:
      print("Other CMD: {} {}".format( c, txt))

  # Collect data for congestion computation.
  cmdcount = cmdcount + 1

# Look for UDP messages from JS8CALL telling us things.
def check_messages():
  global cmdcount, msg

  # Look for an incoming UDP message
  try:
    msg, address = usock.recvfrom(2000)
  except socket.error:
    msg = None

  if msg:
    msg = msg.decode('utf-8')
    data = json.loads(msg)
    js8 = data['params']

    if 'CMD' in js8:
      do_cmd(js8)

    # Our own transmissions get counted
    elif 'TONES' in js8:
      cmdcount = cmdcount + 1
      n = 0

    # Watch for band changes
    elif 'DIAL' in js8:
      updatefreq( js8 )

  # If anything changed in what we know about the network,
  # redraw the map.
  draw.repaint()

  # Check for more UDP messages twice per second
  window.after( 550, check_messages )

####################
# Initialization starts here
####################

# Set up UDP port for listeming to JS8CALL.
try:
  usock = socket.socket( socket.AF_INET, socket.SOCK_DGRAM )
  usock.setblocking(False)
  usock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
  usock.bind( ('', FLAGS.port) )
except socket.error as msg:
  print("Socket error %s\n" % msg[1] )

# Set up a display window.  This has to be done before the
# font functions will work.
window = tk.Tk()
window.title( 'JS8 Network' )

# Window dimensions
swid = min( FLAGS.width, window.winfo_screenwidth())
shgt = min( int(FLAGS.width/2), window.winfo_screenheight())
window.geometry('%dx%d+%d+%d' % (swid, shgt, 8, 32))
window.configure(background='black')
window.update_idletasks()

# Initialize menu-controlled flags
showIconsFlag = tk.IntVar()
if FLAGS.icon:
  showIconsFlag.set(1)
else:
  showIconsFlag.set(0)  
showHistoryFlag = tk.IntVar()
showHistoryFlag.set(0)
lockedFlag = tk.BooleanVar()
lockedFlag.set(FLAGS.lock)

# Initialize subsystems
explore.start( window, FLAGS )
draw.start( window, FLAGS, lockedFlag )
sta.start( FLAGS )

# Bind user keystroke inputs to functions.
window.bind( '<Left>', panleft )
window.bind( '<Right>', panright )
window.bind( '<Up>', panup )
window.bind( '<Down>', pandown )
window.bind( '-', zoomout )
window.bind( '+', zoomin )
window.bind( 'd', dump )
window.bind( 'h', toggleHistory )
window.bind( 'i', toggleIcons )
window.bind( '<Control-q>', manual_quit )

# Create menus
menufont = ('Arial 14 bold')
menubar = tk.Menu( window, font=menufont )
filemenu = tk.Menu( menubar, tearoff=0 )
filemenu.add_command( label='Save config', command=saveconfig, \
                      font=menufont)
filemenu.add_command( label='Quit', command=window.quit, \
                      font=menufont, accelerator='CTRL-Q')
menubar.add_cascade( label="File", menu=filemenu, font=menufont )

viewmenu = tk.Menu( menubar )
viewmenu.add_command( label="Zoom in", font=menufont, \
                      command=zoomin, accelerator='+')
viewmenu.add_command( label="Zoom out", command=zoomout, \
                      accelerator='-', font=menufont)
viewmenu.add_checkbutton( label="Show icons", command=toggleIcons, \
                          font=menufont, accelerator='i', \
                          variable=showIconsFlag, \
                          offvalue=0, onvalue=1)
viewmenu.add_checkbutton( label="Show history", command=toggleHistory, \
                          font=menufont, accelerator='h', \
                          variable=showHistoryFlag, \
                          offvalue=0, onvalue=1)
viewmenu.add_checkbutton( label="Lock zoom", \
                          font=menufont, accelerator='z', \
                          variable=lockedFlag, \
                          offvalue=False, onvalue=True)
menubar.add_cascade( label='View', menu=viewmenu, font=menufont )

# A list of available background maps.
mapmenu = tk.Menu( menubar )
maps = world.MapSpec.list()
mapnum = 0
for mn in maps:
  mapmenu.add_command( label=mn, font=menufont, \
                       command=lambda n=mapnum: setmap(n) )
  mapnum += 1
menubar.add_cascade( label='Map', menu=mapmenu,  font=menufont )

window.config( menu=menubar )

# Set up initial scaling if a lock was specified.
if FLAGS.corners:
  draw.setzoom( FLAGS.corners )
else:
  if FLAGS.grid:
    FLAGS.corners = FLAGS.grid+','+FLAGS.grid
    draw.setzoom( FLAGS.corners )
  else:
    draw.setzoom( None )

# Schedule some events to happen later.  Some will reschedule
# themselves again.  Times are in milliseconds.
window.after( 200, check_messages )   # Check for UDP events
window.after( measurement_interval, measure)  # Compute statistics
window.after( link_interval, check_links )  # Detect dead links
window.after( 150, sta.load )         # Load historical data

# Everything else happens in the scheduled events.  'mainloop'
# will return when the user closes the window.
try:
  window.mainloop()
except KeyboardInterrupt:
  sys.exit()

# At exit, list those stations that were heard about
# during this session but for which we do not know
# the grid coordinates.
for s in sta.Station.book.values():
  if s.reported and not s.grid:
    print("  Missing grid for {}".format(s.call))
