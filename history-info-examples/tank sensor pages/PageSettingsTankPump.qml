import QtQuick 1.1
import "utils.js" as Utils

MbPage {
	id: root

	property string settingsBindPreffix: "com.victronenergy.settings"
	property string pumpBindPreffix: "com.victronenergy.pump.startstop0"
	property variant availableBatteryMonitors: availableBatteryServices.valid ? availableBatteryServices.value : ""
	property VBusItem availableBatteryServices: VBusItem { bind: Utils.path("com.victronenergy.pump.startstop0", "/AvailableTankServices") }
	property VBusItem generatorState: VBusItem { bind: Utils.path("com.victronenergy.pump.startstop0", "/State") }
	property VBusItem relayFunction: VBusItem { bind: Utils.path(settingsBindPreffix, "/Settings/Relay/Function") }

	title: qsTr("Tank pump")

	onAvailableBatteryMonitorsChanged: {
		if (availableBatteryMonitors !== "")
			monitorService.possibleValues = getMonitorList(availableBatteryMonitors)
	}

	function getMonitorList(list)
	{
		var fullList = []
		var component = Qt.createComponent("MbOption.qml");
		for (var i in list) {
			var params = {
				"description": list[i],
				"value": i
			}
				var option = component.createObject(root, params)
				fullList.push(option)
		}
		return fullList
	}

	model: relayFunction.value == undefined ? startStopModel : relayFunction.value  === 3 ? startStopModel : disabledModel

	VisualItemModel {
		id: disabledModel

		MbItemText {
			wrapMode: Text.WordWrap
			text: qsTr("Tank pump start/stop function is not enabled, go to relay settings and set " +
					   "function to \"Tank pump\"" )
		}
	}

	VisualItemModel {
		id: startStopModel

		MbItemValue {
			description: qsTr("Pump state")

			item.text: state.value === 1 ? qsTr("On") : qsTr("Off")
			VBusItem{ id: state; bind: Utils.path(pumpBindPreffix, "/State")}
		}

		MbItemOptions {
			description: qsTr("Mode")
			bind: Utils.path(settingsBindPreffix, "/Settings/Pump0/Mode")
			possibleValues: [
				MbOption { description: qsTr("Auto"); value: 0 },
				MbOption { description: qsTr("On"); value: 1 },
				MbOption { description: qsTr("Off"); value: 2}
			]
		}

		MbItemOptions {
			id: monitorService
			description: qsTr("Tank sensor")
			bind: Utils.path(settingsBindPreffix, "/Settings/Pump0/TankService")
			unknownOptionText: qsTr("Unavailable monitor, set another")
		}

		MbSpinBox {
			id: startValue
			description: qsTr("Start level")
			bind: Utils.path(settingsBindPreffix,"/Settings/Pump0/StartValue")
			unit: "%"
			numOfDecimals: 0
			stepSize: 1
			min: 0
			max: 100
		}

		MbSpinBox {
			id: stopValue
			description: qsTr("Stop level")
			bind: Utils.path(settingsBindPreffix,"/Settings/Pump0/StopValue")
			unit: "%"
			numOfDecimals: 0
			stepSize: 1
			min: 0
			max: 100
		}
	}
}
