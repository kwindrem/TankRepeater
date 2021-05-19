import QtQuick 1.1
import com.victron.velib 1.0
import "utils.js" as Utils
import "tanksensor.js" as TankSensor

MbPage {
	id: root
	property string bindPrefix

	model: VisualItemModel {

		MbSpinBox {
			id: capacityItem
			description: qsTr("Capacity")
			unit: TankSensor.getVolumeFormat(volumeUnit.value).unit
			stepSize: TankSensor.getVolumeFormat(volumeUnit.value).stepSize
			numOfDecimals: TankSensor.getVolumeFormat(volumeUnit.value).precision
			min: TankSensor.volumeConvertFromSI(volumeUnit.value, capacity.min)
			max: TankSensor.volumeConvertFromSI(volumeUnit.value, capacity.max)
			valid: true
			onExitEditMode: {
				/* Convert to SI value and update bus item */
				if (changed) {
					capacity.setValue(TankSensor.volumeConvertToSI(volumeUnit.value, localValue))
				}

				/* Restore local value to cached bus item value.
				 * When the bus item has changed, the onValueChanged is called
				 * and will update the local value to the new value. */
				update()
			}

			VBusItem {
				id: capacity
				bind: Utils.path(bindPrefix, "/Capacity")
				onValueChanged: capacityItem.update()
			}

			/* Convert from SI and update the local value to the bus value.
			 * Set local value to 0.0 when undefined/invalid, otherwise we cannot edit it */
			function update() {
				capacityItem.localValue = capacity.value !== undefined ?
					TankSensor.volumeConvertFromSI(volumeUnit.value, capacity.value) : 0.0
			}
		}

		MbItemOptions {
			id: standard
			description: qsTr("Standard")
			bind: Utils.path(bindPrefix, "/Standard")
			show: item.valid
			possibleValues: [
				MbOption { description: qsTr("European (0 to 180 Ohm)"); value: 0 },
				MbOption { description: qsTr("US (240 to 30 Ohm)"); value: 1 },
				MbOption { description: qsTr("Custom"); value: 2 }
			]
		}

		MbSpinBox {
			description: qsTr("Resistance when empty")
			bind: Utils.path(bindPrefix, "/ResistanceWhenEmpty")
			show: standard.item.value === 2
			unit: "Ω"
		}

		MbSpinBox {
			description: qsTr("Resistance when full")
			bind: Utils.path(bindPrefix, "/ResistanceWhenFull")
			show: standard.item.value === 2
			unit: "Ω"
		}

		MbItemOptions {
			description: qsTr("Fluid type")
			bind: Utils.path(bindPrefix, "/FluidType")
			possibleValues: [
				MbOption { description: qsTr("Fuel"); value: 0 },
				MbOption { description: qsTr("Fresh water"); value: 1 },
				MbOption { description: qsTr("Waste water"); value: 2 },
				MbOption { description: qsTr("Live well"); value: 3 },
				MbOption { description: qsTr("Oil"); value: 4 },
				MbOption { description: qsTr("Black water (sewage)"); value: 5 }
			]
		}

		MbItemOptions {
			id: volumeUnit
			description: qsTr("Volume unit")
			bind: "com.victronenergy.settings/Settings/System/VolumeUnit"
			possibleValues:[
				MbOption { description: qsTr("Cubic metre"); value: 0 },
				MbOption { description: qsTr("Litre"); value: 1 },
				MbOption { description: qsTr("Imperial gallon"); value: 2 },
				MbOption { description: qsTr("U.S. gallon"); value: 3 }
			]
			onValueChanged: capacityItem.update()
		}

		MbSubMenu {
			property VBusItem shape: VBusItem { bind: Utils.path(root.bindPrefix, "/Shape") }

			show: shape.seen
			description: qsTr("Custom shape")
			subpage: Component {
				PageTankShape {
					bindPrefix: root.bindPrefix
				}
			}
		}

		MbItemValue {
			description: qsTr("Sensor resistance")
			item.bind: Utils.path(bindPrefix, "/Resistance")
			item.unit: "Ω"
			show: item.valid
		}
	}
}
