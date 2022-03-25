# JS8MAP - Automatic mapping of the JS8CALL network

JS8MAP is an adjunct tool to run alongside the JS8CALL program.
It listens to UDP messages from JS8CALL and updates a map of station locations and behavior.

## Setup

### Prerequisites

JS8MAP is written in python version 3.  It calls on the following libraries that you may need to install:

* __tkinter__, the python GUI library
* __pillow__, the python image library, usually called 'pil'.

It also calls on the following libraries that are usually part of a standard python installation:

* __configparser__ for reading and writing INI files
* __re__ for analyzing *regular expressions*
* __argparse__ for parsing the command line
* __json__ for parsing messages from JS8CALL.

### JS8CALL settings

Before running JS8MAP, you need to enable UDP reporting in the JS8CALL configuration pages, using port 2242 (the default) or some other port of your choosing.

If you want, you can create a `js8map.ini` file to specify all the options you want, following the template in sample.ini, or you can let `JS8MAP` do it for you as described below.

### Command options

Run the program from the command line using a __python3__ environment. Note that python3 is not just the latest version of python, it is a slightly different language from python2.  Depending how your system is set up you may need to type `python3` as the command line instead of just `python`.

There are several options you can specify but it will be easier in the long run if you set up the `js8map.ini` file as described below. Here is an example:
```
   python js8map.py --call=AA2XYZ --grid=EM99 --lock="CL75,FN68"
```

* **`--call=AA2XYZ`**  
Callsign of the local station.

* **`--grid=XY99`**  
Maidenhead Grid of the local station.

* **`--width=n`**  
Initial width of the display window in pixels.  Default 500.  You can resize it later.

* **`--port=n`** The UDP port number on which JS8CALL has been configured
to send reports.  The defalt is 2242.

* **`--corners="DC,FN"`**  
Maidenhead Grids of the lower-left and upper-right map coordinates at startup.
If omitted, the map will start out centered on the location indicated by `--grid`.  Two or four letters can be used.  For example, `--corners="CL75,FN68"` sets the
map to cover the Continental United States.  

* **`--lock`** Prevent the map from automatically adjusting to include
off-screen stations when they appear.  This can result
in unusual behavior if you happen to pick up a station on another continent.
This can be changed later by the `View/Lock` menu item.

* **`--icon`** Initializes display mode to showing a small icon for each
station instead of the full callsign.  Default is the callsign.

* **`--map=n`** Choose the number of the initial background map.
Default is zero.  This can be changed later with the window menu.
The available maps are listed in the `maps/index.dat` file.

* **`--data=filename`**  
The full path to the file where station information is remembered between
sessions.  The default is `callbook.dat` in the same directory as the
`js8map.py` file.  A prepopulated file is supplied to get you going.

* **`--debug=n`**  Debug message level.  Higher values report lower
level details.  Default is zero, no messages.

* **`--config=filename`** Name of a file in INI format from which all settings
can be taken.  Other commnad line options will override what the file supplies.
If not specified, the file `js8map.ini` is read.  A sample file is supplied.

Once it is running to your satisfaction, you can use the `File/Save config` menu operation to save all the settings to the `js8map.ini` file.  From then on, all you need to do is this:
```
    python js8map.py
```

## Operation

A station will be drawn on the map as soon as all of these conditions
are satisfied:

1. The station's location is known, either from the `callbook.dat` file
or by hearing a `HEARTBEAT` or `GRID` message from the station
2. The station is the source or destination of a transmission
3. The station's location falls within the `lock`ed map area, if any.

Any newly discovered station locations are saved in the file `callbook.dat`
so that the program will have a head start the next time it is run.

Some stations do not enable the automatic sending of
HEARTBEATs.  These stations could be considered not to be "participating"
in "the network". They will not automatically appear on the map
because JS8MAP will not know their location.

But JS8MAP learns along with JS8CALL.  If you see a station on JS8CALL
where its GRID value it not showing, just send them a `GRID?` message.
If the station replies, JS8MAP will see that reply as well and add it
to its own database and start drawing it on the map.

If all else fails, if you learn a station's grid by other means you
can manually edit the `callbook.dat` file and add the callsign and grid.
Then restart JS8MAP.   When JS8MAP exits, it will always print a list
of the callsigns it heard but never learned the location.

### Interpreting the map

Stations are represented either by their callsign or by a small icon.  Which one is used can be switched by toggling the `Show icons` item on the `View` menu.  The `--icon` command line option sets the initial value.  The color of the representation indicates how recently the station has been heard from:

* PINK - the local station
* WHITE - A station heard from in the last 30 minutes
* BLUE - A station heard from this session, but not within the last `station_timeout` minutes.
* RED - A station that was heard from in some previous session, but not this session.  It has been mentioned by some other station.

Stations that have been heard directly at the local station will have their
callsigns underlined.  Stations that are *not* underlined have been heard
*about* in this session and have probably been heard on some previous session,
which his how JS8MAP knows their location

When two stations are observed to exchange messages, a yellow line is
drawn between them.  The line will be removed in 14 seconds.

A station sending a CQ will have a brief green circle drawn around it.
A station sending a HEARTBEAT will have a brief pink circle drawn around it.

At the upper left is a "congestion" value.  This is the average number
of transmissions picked up over an hour in the entire receiver passband.
The number is recomputed every 10 minutes.

Just to the right of the congestion value is the duration of the current
session in hours and minutes.  The timer is reset at any band change.
The current band is displayed in the title bar.  You do not need
to tell JS8MAP which band you are on - it will find out from JS8CALL.

If you click on a station with the mouse a popup will appear giving
the station grid location, station 'info' if known, other stations it
has heard, and minutes since last heard from.  To remove the text box,
click anywhere else.

### Menu commands

A menu at the top of the window provides functions to exit, modify the map
display, and change the background map.

* **File**

    * **`Save config`** Saves the current configuration in `js8map.ini`.  This is useful after you have adjusted the map panning to be just how you like it.  The next time you run `JS8MAP` it will start up with the same map appearance.

    * **`Quit`**

* **View**

    * **`Show icons`** will display a colored dot instead of a callsign at each station location.  This can be helpful if the map is crowded.

    * **`Show history`** will display every pair of stations that has communicated during the session, in faint grey lines.

    * **`Lock zoom`** Prevents the map from automatically zooming out when a new station appears that would otherwise be off-screen.  Using the `--lock` command line option sets this by default.

* **Map**
    Contains a list of the available background maps.

### Keyboard commands

Certain single keystrokes on the map window will have effects:

* **Arrow keys** pan the map up, down, left, right
* **Plus sign** zooms in
* **Minus sign** zooms out
* **Control 'q'** exits the program

## Tips

* If a station has been heard but is not on the map, it is probably because JS8MAP does not know it's grid location.  Using JS8CALL, send it a `GRID?` query and when it responds JS8MAP will learn the location and the station will appear on the map.  Or you can just wait for the station to send a `HEARTBEAT` and it will happen automatically.

* If you leave JS8MAP and JS8CALL running for several hours in the evening on 40m, with `Show history` enabled, you will be able to see how extensive the JS8CALL network actually is.  All of those stations may not be on the air *at the same time*, but JS8MAP remembers them as long as it does not exit.  Their locations, however *are* remembered, in the `callbook.dat` file.

* As yet there is no internal way to save the map image, but you can use your computer's Snapshot feature to take a copy.
This information can be useful in planning use of the store-and-forward mailbox feature of JS8CALL.

* You can add your own background maps to the `maps` directory. They need to be in "EquiRectangular Projection" and an entry needs to be placed in the `maps/index.dat` file describing them.  Both dark and light maps can be used and there are instructions in `index.dat` about how JS8MAP can accomodate that.

# Future ideas

1. JS8MAP only knows about things that happen within hearing of the local radio.  Although callsigns of remote stations can be gathered from messages addressed to them, unless we receive a `HEARTBEAT` or `GRID` message, we do not know their location and so can not map them.  Doing this automatcially would involve sending relayed `GRID?` and `HEARING?` commands.  Gathering remote information has to wait until JS8CALL implements relaying of query responses.  As a workaround, manually adding remote stations to the `callbook.dat` file will have to do.  

2. Another way to collect information on remote stations is for instances of JS8MAP to share their local data with each other through exchange of `MSG` commands.  This could get too voluminous.

2. Both of the above ideas require some form of automatic transmissions controlled by JS8MAP.  There are two aspects to doing this:

    * Care must be taken not to hog the channel, or to overload other stations with too many relay requests.  An exponential backoff algorithm is under development.

    * JS8MAP has no way of knowing what frequency offset will result in the least QRM to other stations.  For this reason, JS8MAP should not be left unattended with automatic trasmissions enabled.  Perhaps it can take note of the offset of *other* station's transmissions and somehow pick a good place to go.
