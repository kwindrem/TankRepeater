import QtQuick 1.1
import com.victron.velib 1.0
import "utils.js" as Utils
import "tanksensor.js" as TankSensor

MbPage {
	id: root

	property string bindPrefix
	property bool isMouse: false
	property VBusItem shapeItem: VBusItem { bind: Utils.path(bindPrefix, "/Shape") }

	title: qsTr("Add point")
	pageToolbarHandler: toolbarHandler
	onActiveChanged: if (active) level.edit(isMouse); else reset()

	ToolbarHandler {
		id: toolbarHandler

		leftText: qsTr("Cancel")
		rightText: qsTr("Add")

		function leftAction()
		{
			cancel();
		}

		function rightAction()
		{
			addPoint();
		}
	}

	function reset()
	{
		level.item.setValue("")
		volume.item.setValue("")
		listview.currentIndex = 0
	}

	function cancel()
	{
		pageStack.pop();
	}

	function addPoint()
	{
		var lvl = +level.item.value;
		var vol = +volume.item.value;

		if (lvl < 1 || lvl > 99) {
			toast.createToast("Invalid sensor level");
			return;
		}

		if (vol < 1 || vol > 99) {
			toast.createToast("Invalid volume");
			return;
		}

		var p = TankSensor.stringToPointArray(shapeItem.value);
		p.push([lvl, vol]);
		p.sort(function(a, b) { return a[0] - b[0] });

		for (var i = 1; i < p.length; i++) {
			if (p[i][0] <= p[i - 1][0]) {
				toast.createToast(qsTr("Duplicate sensor level values not allowed"));
				return;
			}

			if (p[i][1] <= p[i - 1][1]) {
				toast.createToast(qsTr("Volume values must be increasing"));
				return;
			}
		}

		shapeItem.setValue(TankSensor.pointArrayToString(p));
		pageStack.pop();
	}

	model: VisualItemModel {
		MbEditBox {
			id: level
			description: qsTr("Sensor Level")
			matchString: "0123456789"
			maximumLength: 2
			numericOnlyLayout: true
			item.value: ""
			onClicked: item.value = ""
			unit: "%"

			onEditDone: { listview.currentIndex = 1; volume.edit(root.isMouse) }
		}

		MbEditBox {
			id: volume
			description: qsTr("Volume")
			matchString: "0123456789"
			maximumLength: 2
			numericOnlyLayout: true
			item.value: ""
			onClicked: item.value = ""
			unit: "%"

			onEditDone: root.addPoint()
		}
	}
}
