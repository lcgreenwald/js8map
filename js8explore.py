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
import random
import json
from collections import deque
import js8station

bothered = {}
congestion = 0
queue = deque()

# Compute a delay time until the next transmission based on how
# busy the network seems to be.
def backoff():
  global congestion
  return 1000 * int((congestion+10) / 10)

# Process the next command waiting to be sent.
def send_next():
  global queue
  if not queue:
    return
  msg = queue.popleft()
  print("Sending {}".format(msg))
  window.after( backoff(), send_next )

# Add a message to the queue of waiting messages.
def enqueue( msg ):
  global queue, FLAGS, bothered
  if not FLAGS.tx:
    return
  if msg in queue:
    return

  # Do not bother the same station more than once every
  # twenty minutes.
  cto = msg.split(' ')[0]
  now = datetime.datetime.now()
  if cto in bothered:
    if (now - bothered[c]).seconds < 1200:
      return
    else:
      del bothered[cto]
  else:
    bothered[c] = now

  if FLAGS.debug > 1:
    print("Going to send {}".format(msg))
  if not queue:
    window.after( backoff(), send_next )
  queue.append( msg )

def start( w, f ):
  global window, FLAGS
  window = w
  FLAGS = f

def getGrid( s ):
  if s.heard:
    enqueue("{} GRID?".format( s.call ))

def getHeard( s ):
  if sheard:
    enqueue("{} HEARING?".format( s.call ))
