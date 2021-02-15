#!/usr/bin/env python

# This creates a dummy dBus tank service that simulates a SeeLevel the NMEA2000 tank sensor system
# for testing SeeLevelRepeater

# Values input to this service should propagate through the repeaters to the GUI.

# The repeater searchs for a tank service with a specified product ID.
# In order to connect to the simulator, you must change com.victronenergy.settings /Settings/Devices/TankRepeater/SeeLevelProductId 
# to the following value using dbus-spy:

SimulatedSeeLevelProductId = 999999

# If "simulate" is specified on the command line, this code sets values for each tank, then move on to the next tank. 
# The level sent to the service is obtained from Levels [ ] for the values it sends to the service.
# Specifying a level of -99 in Levels [ ] tells this program to skip that tank.

# If "auto" is specified on the command line, this code updates the level for each tank for each cycle, creating a changing value
# in the repeater services and on the GUI if everything is working properly.
#
# When the full or empty limit is reached, the increment is inverted (an empty tank starts filling and visa-versa)

# If neither of these options is specified, the SeeLevel service sits idle allowing value changes to be input via dbus-spy

# SeeLevel reports one tank every ~1.5 seconds with all enabled tanks reporting in ~3-4 seconds
# The cycle repeats indefinitely and tanks are reported whether or not any values change
# Tanks may be disabled in which case they are not included in the cycle
# The cycle for the simulator is slower: a complete pass through 6 tanks in 6 seconds

SeeLevelUpdatePeriodInSeconds = 1.0
SeeLevelUpdatePeriod = int (SeeLevelUpdatePeriodInSeconds * 1000)		# in timer ticks

# SeeLevel reports fluid type, level and tank capacity
# /Level is in percent (100 = full)
# /Capacity is in liters * 10
# but it is converted to cubic meters for the dBus service

import gobject
import platform
import argparse
import logging
import sys
import os
import dbus

# add our own packages
sys.path.insert(1, os.path.join(os.path.dirname(__file__), './ext/velib_python'))
from vedbus import VeDbusService

# SeeLevelServiceName is the name of the SeeLevel dBus service
# this service name must NOT match that of the actual SeeLevel sensor system so that
# the repeater services can identify it for processing
# is determined by examining the system once the SeeLevel N2K sensor system is attached

SeeLevelServiceName = 'com.victronenergy.tank.SimulatedSeeLevel'

class DbusTankService:

    Auto = False

# other parameters are unaffected by these simulations.
# -99 in Level indicates to skip that tank

    Tank = 0

# tanks            0    1     2    3   4    5  
#                fuel fresh gray live oil black
    Levels =    [ -99,  70,  30,  -99,  -99,  60 ]
    Increment = [  0,   -3,   2,    0,    0,   1 ]

# /Capacity is in cubic meters so gallons must be converted
# /Capacity is preset to 30 gallons
# here we initialize capacity to 30 gallons
# no updates to /Capacity occur in this simulator so it can be changed from dbus-spy

    Capacity = 30 * 0.0037854118


    def __init__(self, dBusInstance, simulate, auto):

        self.SeeLevelService = VeDbusService(SeeLevelServiceName)

        # Create the management objects, as specified in the ccgx dbus-api document
        self.SeeLevelService.add_path('/Mgmt/ProcessName', __file__)
        self.SeeLevelService.add_path('/Mgmt/ProcessVersion', '2.0')
        self.SeeLevelService.add_path('/Mgmt/Connection', '')

        # Create the mandatory objects
        self.SeeLevelService.add_path ('/DeviceInstance', dBusInstance)
        self.SeeLevelService.add_path ('/ProductName', 'Simulated SeeLevel N2K')
        self.SeeLevelService.add_path ('/ProductId', SimulatedSeeLevelProductId)
        self.SeeLevelService.add_path ('/FirmwareVersion', 0)
        self.SeeLevelService.add_path ('/HardwareVersion', 0)
        self.SeeLevelService.add_path ('/Serial', 'no hardware')
# make /Connected writable
	self.SeeLevelService.add_path ('/Connected', True, writeable = True)

	self.SeeLevelService.add_path ('/Level', self.Levels[0], writeable = True)
	self.SeeLevelService.add_path ('/FluidType', 0, writeable = True)
	self.SeeLevelService.add_path ('/Capacity', self.Capacity, writeable = True)
	self.SeeLevelService.add_path ('/CustomName', '', writeable = True)

# switch tanks and update level every 0.5 second

	global SeeLevelUpdatePeriod
	if simulate == True:
		gobject.timeout_add(SeeLevelUpdatePeriod, self._update)
		self.Auto = auto

# simulate SeeLevel activity: switching to a new tank and other values
# the repeater must capture these changing values and forward stable data for each tank to their respective repeater services

    def _update (self):

	level = self.Levels [self.Tank]

# a level of -99 means, to skip this tank
	if level != -99:

# change values automatically 
		if self.Auto:
			level += self.Increment [self.Tank]
			if level > 100:
				self.Increment [self.Tank] = -self.Increment [self.Tank]
				level = level + self.Increment [self.Tank]
			if level < 0:
				self.Increment [self.Tank] = -self.Increment [self.Tank]
				level = level + self.Increment [self.Tank]

			self.Levels [self.Tank] = level

		self.SeeLevelService ['/FluidType'] = self.Tank
		self.SeeLevelService ['/Level'] = level

# switch to next tank for the next pass through _update
	while True:
		self.Tank += 1
		if self.Tank >= len(self.Levels):
			self.Tank = 0
		if self.Levels [self.Tank] != -99:
			break;

	return True


def main():

    from dbus.mainloop.glib import DBusGMainLoop

    # Have a mainloop, so we can send/receive asynchronous calls to and from dbus
    DBusGMainLoop(set_as_default=True)

    auto = False
    simulate = False

    if len (sys.argv) > 1:
	if sys.argv[1] == "auto":
		auto = True
		simulate = True

	if sys.argv[1] == "simulate":
		simulate = True
 
    DbusTankService ( 1, simulate, auto)

    mainloop = gobject.MainLoop()
    mainloop.run()

# Always run our main loop so we can process updates
main()
