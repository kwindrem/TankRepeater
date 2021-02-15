#!/usr/bin/env python

# This module creates a dBus tank 'repeater' for handling NMEA2000 tank sensor systems that report more than one tank
# While written for the SeeLevel system, it may work for other CanBus sensors that report multiple tanks.
# The Venus NMEA2000 dBus services assume only one tank (aka sensor aka fluid type) per external device
# so all tanks end up in the same dBus service resulting in each tank overwriting the others
# To avoid this, individual dBus "repeater' services for each tank are created
# data for each tank is extracted from the NEMA2000 tank dBus service and published to a separate repeater service
# 
# This module handles all 6 defined tanks. 
# The SeeLevel N2K sensor system supports at most 3 tanks (1 = fresh, 2 = gray, 5 = black)
# Other N2K systems may report more and this repeater should be able to handle them as long as
# the tank number is unique

# The dBus tank service processed by TankRepeater is identified by its product ID stored in non-volatile settings at
# dbus com.victron.settings /Settings/Devices/TankRepeater/IncomingProdId
# When this process first starts, it creates the setting with a default value of 41312
# If the ProcessId for the service of interest is different dbus-spy can be used to change it
# Use dbus-spy to inspect the SeeLevel tank service for the proper value to enter
# Setting ProcessId to -1 disables the repeater. Venus may need to be restarted to purge any repeaters
# that have already been created

# dbus com.victron.settings /Settings/Devices/TankRepeater/TankRepeaterService is set by the repeater program
# so that the GUI can hide the appropirate service

# Limitation: Only one repeater program is permitted since a second one would attempt to create duplicate dBus services

# Modifications to OverviewMobile.qml in the GUI arr needed to hide the incoming Tank's dBus object that rotates between tank data
# Modificaitons to TileTank.qml have also been made to:
#  alert the operatortor of loss of communciaitons with tank system
#  display custom tank names
#  remove flashing and add error messages, replacing the tank fullness percentage
#  squeeze the tile height when necessary to fit more tanks into the available space

# The service daemon insures this repeater module runs at startup and restarts it should it crash 
# To run this module, a link to the TankRepeater directory is created in the /service directory

# The Repeater dBus services are created only after data is received from sender for the related tank
# to avoid GUI clutter

# A timeout mechanism control's the repeater's /Connected flag to indicate if the Repeater service is active or not
# when the sender stops reporting data for a specific tank, The repeater's /Connected flag will eventually be cleared by this timeout mechanism
# The GUI (TileTank) then tests /Connected to hide report "No Response" in the Tanks column

# SeeLevel sends /FluidType, /Level and /Capacity
# /FluidType is enumerated consistently with other Victron tanks
# /Level is in percentage (100 = full)
# /Level is used to report a sensor error, however the Venus NMEA2000 tank driver limits these values to 0-100%
# so there is no way to display a sensor error (such as an open in the wiring)
# SeeLevel reports capacity in liters * 10 and the tank driver converts this to cubic meters used elsewhere in the Venus code
# /Remaining is calculated in the Repeater

# SeeLevel reports information for all tanks about every 3-4 seconds
# However, it can get into a mode where info for all tanks is sent very quickly, then no activity for ~ 3 seconds
# Polling for changes can miss data for a specific tank which makes it appear that the tank is not being reported (timeout)
# For this reason, PropertiesChanged signal handlers for /FluidType, /Level and /Capacity are used to collect tank info
# But this also is tricky since a signal for a level or capacity change may not be issued for every tank.
# For example, if all tanks are empty, the level signal handler is never called! 
# The same would be true for /FluidLevel if there was only one tank.
# The signal handlers for /FluidType, /Level and /Capacity store the values received.
# On the next /FluidType signal, the combination of /FluidType, /Level and /Capacity previuosly stored are consistent.
# Those values are sent to the appropriate repeater which stores the values for later.
# The repeater's background task validates values, creates the dBus service if necessary then updates the dBus service witb new values.
# The background task also polls for the incoming tank dBus information to be used in the absence of signals.
# The signal handlers are called from another thread/process so the amount of time spent in these routines is kept to a minimum.

import gobject
import platform
import argparse
import logging
import sys
import os
import dbus
import time

# add the path to our own packages for import
sys.path.insert(1, os.path.join(os.path.dirname(__file__), './ext/velib_python'))
from vedbus import VeDbusService
from settingsdevice import SettingsDevice

# RepeaterServiceName is the name of the dBus service where data is sent
# tank number is appended when the service is created

RepeaterServiceName = 'com.victronenergy.tank.repeater'
ProductName = 'NMES2000 Multiple Tank %d Repeater'

# timer periods and watchdog timeout are defined here for convenience

# If a repater service is not updated at least every 8 seconds
# (approximately twice the SeeLevel reporting period)
# it is marked as disconnected so the GUI can alert the user that
# the level should not be trusted

RepeaterTimeoutInSeconds = 6.0

# the update loop in the Repeater only manages timeouts so runs infrequently
RepeaterTimerPeriodInSeconds = 1.0

# This period defines how often the incoming tank dBus object is checked
# for existence and to pull /Capacity values for each tank
# 1 second is frequent enough for these tasks 

IncomingTankScanPeriodInSeconds = 1.0

IncomingTankScanPeriod = int (IncomingTankScanPeriodInSeconds * 1000)		# in timer ticks
RepeaterTimerPeriod = int (RepeaterTimerPeriodInSeconds * 1000)		# in timer ticks
RepeaterTimeout = int (RepeaterTimeoutInSeconds / RepeaterTimerPeriodInSeconds)	# in passes through update loop


# These methods permit creation of a separate connection for each Repeater
# overcoming the one service per process limitation
# requires updated vedbus, originally obtained from https://github.com/victronenergy/dbus-digitalinputs
# updates are incorporated in the ext directory of this package

class SystemBus(dbus.bus.BusConnection):
	def __new__(cls):
		return dbus.bus.BusConnection.__new__(cls, dbus.bus.BusConnection.TYPE_SYSTEM)

class SessionBus(dbus.bus.BusConnection):
	def __new__(cls):
		return dbus.bus.BusConnection.__new__(cls, dbus.bus.BusConnection.TYPE_SESSION)

def dbusconnection():
    return SessionBus() if 'DBUS_SESSION_BUS_ADDRESS' in os.environ else SystemBus()


# repeater bus services are created from this class
# one Repeater instance is created for each tank (aka fluid type)
# a corresponding dBus service is created when the Repeater is instantiated.

class Repeater:

    global RepeaterServiceName
    global ProductName
    global RepeaterTimeout
    global RepeaterTimerPeriod

    DbusService = None
    StartupDelay = True

    DbusBus = None
    ServiceName = ""

# local tank values
# the dBus service is not created until messages are received
# so the incoming tank signal handler and background loop set these,
# triggering service cration in the repeater's background loop
# repeater background loop then updates the dBus values

    Tank = 0
    Level = 0
    Capacity = 0
    UpdateReceived = False

    TimeoutCount = 0


    def __init__(self, tank):

	self.Tank = tank
	self.RepeaterTimeout = RepeaterTimeout
	self.TimeoutCount = 0

# set up unique dBus connection
# The Repeater dBus service is not created until incoming tank messages for that tank are received
	self.DbusBus = dbusconnection()

# gobject.timeout_add uses a 1 mS timer (1000 ticks per second)
# _update is called periodically with the following call

	gobject.timeout_add(RepeaterTimerPeriod, self._update)


# flag value change from external source

    def _handlechangedvalue (self, path, value):

	self.UpdateReceived = True
        return True 


# create tank Repeater service

    def _createDbusService (self):

# create a unique service name that puts tanks in the desired order (see note at top of this module)
	self.ServiceName = RepeaterServiceName + "_%d" % self.Tank

# updated version of VeDbusService (in ext directory) -- see https://github.com/victronenergy/dbus-digitalinputs for new imports
	self.DbusService = VeDbusService (self.ServiceName, bus = self.DbusBus)

# make custom name non-volatile
        settingsPath = '/Settings/Devices/TankRepeater/Tank%d' % self.Tank

        SETTINGS = { 'customname': [settingsPath + '/CustomName', '', 0, 0] }

        self.settings = SettingsDevice(self.DbusBus, SETTINGS, self.setting_changed)

# Create the objects

	self.DbusService.add_path ('/Mgmt/ProcessName', __file__)
	self.DbusService.add_path ('/Mgmt/ProcessVersion', '1.0')
        self.DbusService.add_path ('/Mgmt/Connection', 'dBus')

        self.DbusService.add_path ('/DeviceInstance', self.Tank)
        self.DbusService.add_path ('/ProductName', ProductName % self.Tank)
        self.DbusService.add_path ('/ProductId', 0)
        self.DbusService.add_path ('/FirmwareVersion', 0)
        self.DbusService.add_path ('/HardwareVersion', 0)
        self.DbusService.add_path ('/Serial', '')
# use numeric values (1/0) not True/False for /Connected to make GUI display correct state
	self.DbusService.add_path ('/Connected', 0)
 
	self.DbusService.add_path ('/Level', 0, writeable = True, onchangecallback = self._handlechangedvalue)
	self.DbusService.add_path ('/FluidType', self.Tank, writeable = True, onchangecallback = self._handlechangedvalue)
	self.DbusService.add_path ('/Capacity', 0, writeable = True, onchangecallback = self._handlechangedvalue)
	self.DbusService.add_path ('/Remaining', 0, writeable = True, onchangecallback = self._handlechangedvalue)

	self.DbusService.add_path ('/CustomName', self.get_customname(), writeable = True, onchangecallback = self.customname_changed)

	self.TimeoutCount = 0;
	self.StartupDelay = True

	return


    def get_customname(self):
        return self.settings['customname']
            
    def set_customname (self, val):
	self.settings['customname'] = val

    def setting_changed (self, name, old, new):
        if name == 'customname':
	    self.DbusService['/CustomName'] = new
	return

    def customname_changed (self, path, val):
        self.set_customname (val)
        return True


# do background processing for this repeater
# CheckIncomingTank updates Repeater local variables
# those values are passed to the dBus service as a background operation here
# the dBus service is created here when the first update for this tank is received
# the /Connected flag is managed here: True if updates are being received,
# False if no updates have been received in the timeout period

    def _update(self):

# update has been received - create dBus service if not done previously
# then update dBus values from local storage
	if self.UpdateReceived:
		if self.DbusService == None:
			self._createDbusService ()
# do nothing this pass if just created dBus service
# update flag isn't cleared so the update is processed next pass
			return True

# update servcie values from local storage
		self.DbusService['/Level'] = self.Level
		self.DbusService['/Capacity'] = self.Capacity
		self.DbusService['/Remaining'] = self.Capacity * self.Level / 100
		self.UpdateReceived = False
		self.TimeoutCount = 0

# skip timeout processing if dBus service does not exist
	if self.DbusService == None:
		return True

# update connected flag
	if self.TimeoutCount == 0:
		if self.DbusService['/Connected'] == 0:
			self.DbusService['/Connected'] = 1
			logging.info ("Tank %d is responding", self.Tank)

	if self.TimeoutCount > self.RepeaterTimeout:
		if self.DbusService['/Connected'] == 1:
			self.DbusService['/Connected'] = 0
			logging.warning ("Tank %d is NOT responding", self.Tank)
	else:
		self.TimeoutCount += 1

	return True


# method called from the CheckIncomingTank processing to update repeater values

    def UpdateRepeater (self, level, capacity):

	if level != -99:
		self.Level = level
	if capacity != -99:
		self.Capacity = capacity
	self.UpdateReceived = True
	return True
 

# CheckIncomingTank is the polling loop to extract incoming tank information
# it collects and validates information from the incoming tank dBus service and forwards it to the tank repeater objects if for whatever reason
# the signal handlers are not called. This would be the case if there is only one tank, or level doesn't change between messages.
# Data from the tank dBus service is read as quickly as possible followed by a second read of the first parameter (tank number)
# if that second read matches the first, we assume the intermediate reads are valid
#
# this method runs even if a tank sensor system isn't attached to Venus. In this case, the incoming tank dBus service won't exist
# Read attempts to that service will generate an exception which is trapped here to skip processing.
# note also that if the GUI isn't running or crashes, the incoming tank dBus object goes away
#
# This method runs once per second to manage incoming tank service object pointers and to read /Capacity
# The incoming tank service can switch to a different tank quickly and this polling loop will miss some tanks
# /FluidType  and /Level signal handlers (below) are used for updates to minimize the chance of a missed tank
# Only /Level is processed in the signal handler for speed.
# FluidTLevelHandler will not be called when tank system switches to a new tank if it has the same level as the previous tank
# Values from the two handlers (tank and level) are saved in persistent storage so they can be processed together at the next /FluidType change
#
# persistent storage for incoming tank data are created
# so objects don't have to be fetched each time this process runs
# GetValue() calls using these pointers fails if the incoming messages aren't being received or processed
# The CanBus processing is tied to the GUI process so if the GUI process dies, incoming messages will not be received.
# When the incoming tank dBus service is again present, the connection to it is reset and tank info forwarding continues
# During this time, a no response error will be displayed.

IncomingTankTankObject = None
IncomingTankFluidLevelObject = None
IncomingTankCapacityObject = None
IncomingTankUniqueName = ""
LastTank = -99
LastLevel = -99
LastCapacity = -99
IncomingTankDbusOK = False
NoLevelCount = 0
NoCapacityCount = 0
AlreadyLogged = False
NewIncomingTankProdId = True	# force immediate service reference updates
IncomingTankSearchDelay = 0

# this is the dBus bus (system in this case)
TheBus = None

# RepeaterList provides persistent storage for a repeater instance so that it may be called from CheckIncomingTank 
# This list is indexed by fluid type and needs to be expanded if additional fluid types are added in the future

RepeaterList =  [None,  None, None, None, None, None ]


# check to see if the incoming tank dBus object exists
# innitialize object pointers if so
# invalidate object pointers if not

# signal handlers are the primary update for level and capacity unless there is only one tank
# or values don't change between tanks, so we still need to poll for values here

# dbus exceptions will occur if incoming tank dBus object doesn't exist (normal)
# or if the GUI isn't running (CanBus runs from GUI thread) (also expected)


def CheckIncomingTank():

	global IncomingTankUniqueName
	global IncomingTankDbusOK
	global NvSettings

	global IncomingTankTankObject
	global IncomingTankFluidLevelObject
	global IncomingTankCapacityObject

	global NewIncomingTankProdId

	global RepeaterList
	global LastTank
	global LastLevel
	global LastCapacity
	global TheBus
	global NoLevelCount
	global NoCapacityCount
	global AlreadyLogged
	global IncomingTankSearchDelay

	IncomingTankSearchDelay += 1
	if IncomingTankSearchDelay > 10:
		IncomingTankSearchDelay = 0
	
	try:

# check for incoming tank dBus service present
# done every 10 passes (seconds) if a service hasn't already been found
# or immediately if a new product ID from non-volatile setting is pending
# productId == -1 disables search for service - SeeLevel service name is cleared so GUI will not hide it in the tanks list
		if (IncomingTankDbusOK == False and IncomingTankSearchDelay == 0) or NewIncomingTankProdId == True:
			nvProductId = NvSettings['incomingTankProdIdNv']
			if nvProductId == -1 and NewIncomingTankProdId == True:
				logging.warning ("Incoming Tank Repeater disabled")
				NvSettings['incomingTankNameNv'] = ""

			NewIncomingTankProdId = False
			IncomingTankDbusOK = False
			IncomingTankSearchDelay = 0

			for service in TheBus.list_names():
# ignore repeater services
				if service.startswith(RepeaterServiceName):
					continue
# found a match - stop looking
				if service.startswith("com.victronenergy.tank") \
						and TheBus.get_object(service, '/ProductId').GetValue() == nvProductId:
					IncomingTankDbusOK = True
					break

# found a matching service - now set up incoming tank dBus references
# including Nv copy of service name which is used by the GUI to hide the incoming tank
			if IncomingTankDbusOK:
				IncomingTankTankObject = TheBus.get_object(service, '/FluidType')
				IncomingTankFluidLevelObject = TheBus.get_object(service, '/Level')
				IncomingTankCapacityObject = TheBus.get_object (service, '/Capacity')
				IncomingTankUniqueName = TheBus.get_name_owner(service)
				LastTank = -99
				LastLevel = -99
				LastCapacity = -99
				NoLevelCount = 0
				NoCapacityCount = 0
				AlreadyLogged = False
				logging.info ("Incoming tank dBus connection established at:%s:" % service) 
				NvSettings['incomingTankNameNv'] = service

# skip processing if no incoming tank dBus service
		if IncomingTankDbusOK == False:
			return True

# do a background update to the associated repeater
		tank = IncomingTankTankObject.GetValue()
		level = IncomingTankFluidLevelObject.GetValue()
		capacity = IncomingTankCapacityObject.GetValue ()
		tank2 = IncomingTankTankObject.GetValue()

	except dbus.DBusException:
		IncomingTankDbusOK = False
		if AlreadyLogged == False:
			logging.warning ("No response from incoming tank at:%s:", NvSettings['incomingTankNameNv'])
			AlreadyLogged = True
		return True


# update the repeater's level and capacity values from the poll
# range check tank before using it as an array index
	if tank >= 0 and tank < len(RepeaterList) and tank == tank2:
		RepeaterList [tank].UpdateRepeater (level, capacity)

# wait 10 passes before doing anything to give signals a chance to be received
# if level signals are not being received but tank number signals ARE being received
# the level of all tanks is probalby the same, so set LastLevel from the polled value
	if (LastLevel == -99 and LastTank != -99 and level != -99):
		NoLevelCount += 1					
		if NoLevelCount > 10:
			LastLevel = level
			logging.info ("No /Level signals have been received - using polled data") 
	else:
		NoLevelCount = 0

# ditto for capacity
	if (LastCapacity == -99 and LastTank != -99 and capacity != -99):
		NoCapacityCount += 1					
		if NoCapacityCount > 10:
			LastCapacity = capacity
			logging.info ("No /Capacity signals have been received - using polled data") 
	else:
		NoCapacityCount = 0

	return True


# signal handlers

def FluidTypeHandler (changes, sender):

	global IncomingTankUniqueName
	global IncomingTankDbusOK
	global LastTank
	global LastLevel
	global LastCapacity

# ignore signal if it's not from the incoming tank dBus service
	if IncomingTankDbusOK == False or sender != IncomingTankUniqueName:
		return

# test value as text to identify an invaild value before extracting the actual value
# (getting value fails with a dBus exception if incoming tank service isn't responding)
# ignore if text is null

	if changes.get ("Text") == "":
		return

	tank = int (changes.get ("Value"))

# Update the repeater based on PREVIOUS tank, level and capacity before saving the current tank for next call
# range check tank and level before processing
	if LastTank >= 0 and LastTank < len(RepeaterList):
		RepeaterList [LastTank].UpdateRepeater (LastLevel, LastCapacity)

# save new fluid type for processing on next call to this handler
	LastTank = tank

	return


def FluidLevelHandler (changes, sender):

	global IncomingTankUniqueName
	global IncomingTankDbusOK
	global LastLevel

# ignore signal if it's not from the incoming tank service
	if IncomingTankDbusOK == False or sender != IncomingTankUniqueName:
		return

# save level for processing during next call of FluidTypeHandler
# test value as text to identify an invaild value before extracting the actual value
	if changes.get ("Text") != "":
		LastLevel = float (changes.get ("Value"))

	return


def FluidCapacityHandler (changes, sender):

	global IncomingTankUniqueName
	global IncomingTankDbusOK
	global LastCapacity

# ignore signal if it's not from the incoming tank service
	if IncomingTankDbusOK == False or sender != IncomingTankUniqueName:
		return

# save capacity for processing during next call of FluidTypeHandler
# test value as text to identify an invaild value before extracting the actual value
	if changes.get ("Text") != "":
		LastCapacity = float (changes.get ("Value"))

	return

#declare a global for non-volatile settings
NvSettings = ''


# NV copy of incoming tank dBus service Product Id changed
# set the flag - value change handled elsewnere
# incoming tank service name comes in here also
# (This code only sets productId so ignore changes for service name)

def IncomingTankSettingChanged (name, old, new):
	global NewIncomingTankProdId

	if name == 'incomingTankProdIdNv':
		NewIncomingTankProdId = True

#	elif name == 'incomingTankNameNv':
		# do nothing
	return


def main():

	from dbus.mainloop.glib import DBusGMainLoop

	global TheBus
	global IncomingTankServiceChanged
	global NvSettings

# set logging level to include info level entries
	logging.basicConfig(level=logging.INFO)

# Have a mainloop, so we can send/receive asynchronous calls to and from dbus
	DBusGMainLoop(set_as_default=True)

        logging.info (">>>>>>>>>>>>>>>> TankRepeater Starting <<<<<<<<<<<<<<<<")

# create repeaters for all tanks
# dBus services are NOT created at this time to save GUI clutter
	for tank in range (len(RepeaterList)):
		RepeaterList [tank] = Repeater (tank)


# install a signal handler for /FluidType and /Level
	TheBus = dbus.SystemBus()
	TheBus.add_signal_receiver (FluidTypeHandler, path = "/FluidType",
                dbus_interface='com.victronenergy.BusItem', signal_name='PropertiesChanged',
		sender_keyword="sender")
	TheBus.add_signal_receiver (FluidLevelHandler, path = "/Level",
                dbus_interface='com.victronenergy.BusItem', signal_name='PropertiesChanged',
		sender_keyword="sender")
	TheBus.add_signal_receiver (FluidCapacityHandler, path = "/Capacity",
                dbus_interface='com.victronenergy.BusItem', signal_name='PropertiesChanged',
		sender_keyword="sender")

# create non-volatile setting for incoming tank dBus service name and productId
# installer will modify in productId via dbus-spy if necessary when setting things up - default is 41312
# service name is set up by CheckIncomingTank above if service is found matching the productId
# the GUI uses the service name to hide the incoming tank dBus service
# SettingsDevice could be called early in system boot so wait up to 10 seconds before giving up

	SETTINGS = {	'incomingTankNameNv': ['/Settings/Devices/TankRepeater/IncomingTankService', '', 0, 0],
			'incomingTankProdIdNv': ['/Settings/Devices/TankRepeater/IncomingTankProductId', 41312, -1, 999999] }

	NvSettings = SettingsDevice(TheBus, SETTINGS, IncomingTankSettingChanged, timeout = 10)

# periodically look for incoming tnak service
	gobject.timeout_add(IncomingTankScanPeriod, CheckIncomingTank)

	mainloop = gobject.MainLoop()
	mainloop.run()

# Always run our main loop so we can process updates
main()
