#!/usr/bin/env python

import gobject
import platform
import argparse
import logging
import sys
import os
import dbus

# our own packages
sys.path.insert(1, os.path.join(os.path.dirname(__file__), '../ext/velib_python'))
from vedbus import VeDbusService

# 1 for fresh water, 5 for black water
desiredTankType = 1; 

# set this to 01 or 02 or some unique value compared to any sibling services
serviceNumber = 2;

class DbusTankService:
    
    def __init__(self, servicename, deviceinstance, paths, productname='Fresh tank sensor', connection='Fresh tank sensor dBus repeater'):
        self._dbusservice = VeDbusService(servicename)
        self._paths = paths

        logging.debug("%s /DeviceInstance = %d" % (servicename, deviceinstance))

        # Create the management objects, as specified in the ccgx dbus-api document
        self._dbusservice.add_path('/Mgmt/ProcessName', __file__)
        self._dbusservice.add_path('/Mgmt/ProcessVersion', '1.0')
        self._dbusservice.add_path('/Mgmt/Connection', connection)

        # Create the mandatory objects
        self._dbusservice.add_path('/DeviceInstance', deviceinstance)
        self._dbusservice.add_path('/ProductId', 41312)
        self._dbusservice.add_path('/ProductName', productname)
        self._dbusservice.add_path('/FirmwareVersion', 0)
        self._dbusservice.add_path('/HardwareVersion', 0)
        self._dbusservice.add_path('/Connected', 1)

        for path, settings in self._paths.iteritems():
            self._dbusservice.add_path(
                path, settings['initial'], writeable=True, onchangecallback=self._handlechangedvalue)

        gobject.timeout_add(100, self._update)

    def _update(self):
        bus = dbus.SystemBus()
        try:
            fluidType = bus.get_object('com.victronenergy.tank.socketcan_can1_di0_uc73', '/FluidType')
            fluidLevel = bus.get_object('com.victronenergy.tank.socketcan_can1_di0_uc73', '/Level')
        except dbus.DBusException:
            logging.info('couldn\'t resolve uc73 service ID')
        else:
            type1 = fluidType.GetValue()
            level1 = fluidLevel.GetValue()
            if type1 == desiredTankType:
                # pull another {type, level} tuple to see if we still have the same values
                type2 = fluidType.GetValue()
                level2 = fluidLevel.GetValue()
                if type2 == type1 and level2 == level1:
                    self._dbusservice['/Level'] = level1
                    logging.debug('updated level to %.2f' % level1)
                else:
                    logging.debug('rejected level because of race condition/mismatch')
        return True

    def _handlechangedvalue(self, path, value):
        logging.debug("someone else updated %s to %s" % (path, value))
        return True # accept the change


# === All code below is to simply run it from the commandline for debugging purposes ===

# It will created a dbus service called com.victronenergy.pvinverter.output.
# To try this on commandline, start this program in one terminal, and try these commands
# from another terminal:
# dbus com.victronenergy.pvinverter.output
# dbus com.victronenergy.pvinverter.output /Ac/Energy/Forward GetValue
# dbus com.victronenergy.pvinverter.output /Ac/Energy/Forward SetValue %20
#
# Above examples use this dbus client: http://code.google.com/p/dbus-tools/wiki/DBusCli
# See their manual to explain the % in %20

def main():
    logging.basicConfig(level=logging.DEBUG)

    from dbus.mainloop.glib import DBusGMainLoop
    # Have a mainloop, so we can send/receive asynchronous calls to and from dbus
    DBusGMainLoop(set_as_default=True)

    pvac_output = DbusTankService(
        servicename = 'com.victronenergy.tank.socketcan_can1_di0_uc%02d' % serviceNumber,
        deviceinstance = 2,
        paths={
            '/Level': {'initial': 0, },
            '/FluidType': {'initial': desiredTankType },
            '/Capacity': {'initial': 0.541 },
            '/N2kUniqueNumber': {'initial': 12345 },
            '/Remaining': {'initial': 0.281519 },
            '/Serial': {'initial': 213949 }
        })
    logging.info('Connected to dbus')

    logging.info('Switching to glib mainloop')
    mainloop = gobject.MainLoop()
    mainloop.run()

# Always run our main loop so we can process updates
main()


