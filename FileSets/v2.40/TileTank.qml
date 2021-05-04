// This file replaces the original TileTank.qml file
// The changes here are optional and can be used with or without the SeeLevel repeater

// Changes:
// Bar text turns red and indicates "NO RESPONSE" for sensor connection errors
// if tank had already been responding at some time in the past
// This indication is triggered by the dBus services's /Connected flag being 0
// Color of bar turns red on limits instead of blinking
// Color of bar text turns red below lower limit so there is some indication of empty when the bar is too small to be seen
// If space is limited, bar graph height and associated text are reduced so up to 6 tanks will fit in the available space
// Beyond 6 tanks, the display gets bunched up and may not be readable
// Added custom tank name

// The default Tile is not used. It is replicated here so that we can squeeze things to save vertical space
// Squeezing is triggered by a height of less than 50 (more than 4 tanks)
// Squeeze affects title font size, underline, bar graph height and bar graph font size

import QtQuick 1.1
import "utils.js" as Utils
// add import for display of remaining volume
import "tanksensor.js" as TankSensor



Rectangle
{
	id: root

	property string bindPrefix: serviceName
    property string pumpBindPrefix

// add thse two properties to allow displaying remaining volume
    property VBusItem remainingItem: VBusItem { id: remainingItem; bind: Utils.path(bindPrefix, "/Remaining"); decimals: 0 }
    property VBusItem volumeUnit: VBusItem { bind: "com.victronenergy.settings/Settings/System/VolumeUnit" }

    property VBusItem levelItem: VBusItem { id: levelItem; bind: Utils.path(bindPrefix, "/Level"); decimals: 0; unit: "%" }
	property VBusItem fluidTypeItem: VBusItem { id: fluidTypeItem; bind: Utils.path(bindPrefix, "/FluidType") }
    property VBusItem connectedItem: VBusItem { id: connectedItem; bind: Utils.path(bindPrefix, "/Connected") }
    property VBusItem nameItem: VBusItem { id: nameItem; bind: Utils.path(bindPrefix, "/CustomName") }
	property alias valueBarColor: valueBar.color
	property alias level: levelItem.value
	property alias tank: fluidTypeItem.value

// full warning for waste water and black water tanks
	property int fullWarningLevel: ([2, 5].indexOf(tank) > -1) ? 80 : 101
// empty warning for other tank types
	property int emptyWarningLevel: !([2, 5].indexOf(tank) > -1) ? 20 : -1
	property variant fluidTypes: [qsTr("FUEL"), qsTr("FRESH WATER"), qsTr("WASTE WATER"), qsTr("LIVE WELL"), qsTr("OIL"), qsTr("BLACK WATER")]
	property variant fluidColor: ["#1abc9c", "#4aa3df", "#95a5a6", "#dcc6e0", "#f1a9a0", "#7f8c8d"]

	// small tile height threshold
	property bool squeeze: height < 50

	border.width: 2
	border.color: "#fff"
	clip: true
	color: fluidTypeItem.valid ? fluidColor[tank] : "#4aa3df"

// title font
// reduce size and top margin for smaller tiles
	Text
	{
		id: titleField
		font.pixelSize: squeeze ? 12 : 13
		text: nameItem.valid && nameItem.value != '' ? nameItem.value : (fluidTypeItem.valid ? fluidTypes[tank] : "TANK ?")
		color: "white"
		anchors
		{
			top: parent.top; topMargin: squeeze ? 1 : 5
			left: parent.left; leftMargin: 5
		}
	}

// hide underline for smaller tiles
	Rectangle
	{
		id: titleLine
		width: parent.width - 10
		height: 1
		visible: squeeze ? false : true
		color: "white"
		anchors
		{
			top: titleField.bottom
			left: titleField.left
		}
	}

// tank level bar outline
// when squeezing, move bar under title and reduce margin
	Rectangle
	{
		color: "#c0c0bd"
		border { width:1; color: "white" }
		width: root.width - 10
		height: Math.min(21, ((root.height / 6) * 2) + 1) // insure height is an odd number
		anchors
		{
			horizontalCenter: parent.horizontalCenter
			topMargin: squeeze ? 0 : 5
			top: squeeze ? titleField.bottom : titleLine.bottom
		}

// tank level bar
		Rectangle
		{
			id: valueBar
			width: root.level >= 0 ? root.level / 100 * parent.width - 2 : 0
			height: parent.height - 2
			color: level >= fullWarningLevel || level <= emptyWarningLevel ? "#e74c3c" : "#34495e"
			opacity: connectedItem.value ? 1 : 0.2
			anchors
			{
				verticalCenter: parent.verticalCenter
				left: parent.left; leftMargin: 1
			}
		}

// tank fullness / error
		Text
		{
			font.pixelSize: squeeze ? 10 : 12
			font.bold: true
// handle level value that indicates a no sensor response, sensor error #### TBD not sure what those are
// include remaint level in display
			text: !connectedItem.value ? "NO RESPONSE" : level >= 0 ? root.levelItem.text + " " + TankSensor.formatVolume(volumeUnit.value, root.remainingItem.value) : "ERROR"
			color: !connectedItem.value ? "red" : level <= emptyWarningLevel ? "red" : "white"
			anchors.centerIn: parent
		}
	}
}
