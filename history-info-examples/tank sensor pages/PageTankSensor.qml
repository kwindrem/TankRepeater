import QtQuick 1.1
import com.victron.velib 1.0
import "utils.js" as Utils
import "tanksensor.js" as TankSensor

MbPage {
	id: root

	property variant service
	property string bindPrefix

	property list<MbOption> fluidTypes: [
		MbOption { description: qsTr("Fuel"); value: 0 },
		MbOption { description: qsTr("Fresh water"); value: 1 },
		MbOption { description: qsTr("Waste water"); value: 2 },
		MbOption { description: qsTr("Live well"); value: 3 },
		MbOption { description: qsTr("Oil"); value: 4 },
		MbOption { description: qsTr("Black water (sewage)"); value: 5 }
	]

	property VBusItem connection: VBusItem { bind: Utils.path(bindPrefix, "/Mgmt/Connection") }
	property VBusItem customName: VBusItem { bind: Utils.path(bindPrefix, "/CustomName") }
	property VBusItem fluidType: VBusItem {	bind: Utils.path(bindPrefix, "/FluidType") }
	property VBusItem volumeUnit: VBusItem { bind: "com.victronenergy.settings/Settings/System/VolumeUnit" }

	title: getTitle()
	summary: level.item.valid ? level.item.text : status.valid ? status.text : "--"

	function getTitle() {
		if (customName.valid && customName.value !== "")
			return customName.value

		var inputNumber = connection.valid ? connection.value.replace(/\D/g,'') : ""
		var inputNumberStr = ""

		if (inputNumber !== "")
			inputNumberStr = " (" + inputNumber + ")"

		if (fluidType.valid)
			return fluidTypeText(fluidType.value) + qsTr(" tank") + inputNumberStr
		return service.description + inputNumberStr
	}

	function fluidTypeText(value) {
		for (var i = 0; i < fluidTypes.length; i++) {
			var option = fluidTypes[i];
			if (option.value === value)
				return option.description;
		}
		return qsTr("Unknown")
	}

	model: VisualItemModel {
		MbItemOptions {
			id: status
			description: qsTr("Status")
			bind: service.path("/Status")
			readonly: true
			show: item.valid
			possibleValues: [
				MbOption { description: qsTr("Ok"); value: 0 },
				MbOption { description: qsTr("Disconnected"); value: 1 },
				MbOption { description: qsTr("Short circuited"); value: 2 },
				MbOption { description: qsTr("Reverse polarity"); value: 3 },
				MbOption { description: qsTr("Unknown"); value: 4 },
				MbOption { description: qsTr("Error"); value: 5 }
			]
		}

		MbItemValue {
			id: level
			description: qsTr("Level")
			item.bind: service.path("/Level")
			item.unit: "%"
		}

		MbItemValue {
			id: remaining
			description: qsTr("Remaining")
			item {
				bind: service.path("/Remaining")
				text: TankSensor.formatVolume(volumeUnit.value, item.value)
			}
		}

		MbSubMenu {
			id: setupMenu
			description: qsTr("Setup")
			subpage: Component {
				PageTankSetup {
					title: setupMenu.description
					bindPrefix: root.bindPrefix
				}
			}
		}

		MbSubMenu {
			id: deviceMenu
			description: qsTr("Device")
			subpage: Component {
				PageDeviceInfo {
					title: deviceMenu.description
					bindPrefix: root.bindPrefix
				}
			}
		}
	}
}
