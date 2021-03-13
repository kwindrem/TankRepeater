import QtQuick 1.1
import com.victron.velib 1.0
import "utils.js" as Utils
import "tanksensor.js" as TankSensor

MbPage {
	id: root

	property string bindPrefix
	property VBusItem shapeItem: VBusItem { bind: Utils.path(bindPrefix, "/Shape") }
	property variant subpage: PageTankShapeAddPoint { bindPrefix: root.bindPrefix }

	title: qsTr("Custom shape")
	model: TankSensor.stringToPointArray(shapeItem.value)
	pageToolbarHandler: user.accessLevel >= User.AccessInstaller ? addPointToolbarHandler : undefined

	ToolbarHandler {
		id: addPointToolbarHandler

		leftText: qsTr("Add")
		rightText: listview.count === 0 ? "" : qsTr("Remove")

		function leftAction(isMouse)
		{
			addPoint(isMouse);
		}

		function rightAction()
		{
			removePoint();
		}
	}

	function addPoint(isMouse)
	{
		if (model.length > 9) {
			toast.createToast("Max 10 points allowed");
			return;
		}

		subpage.isMouse = isMouse === true
		pageStack.push(subpage);
	}

	function removePoint()
	{
		var p = model;
		p.splice(currentIndex, 1);
		shapeItem.setValue(TankSensor.pointArrayToString(p));
	}

	MbItemText {
		wrapMode: Text.WordWrap
		show: listview.count === 0
		text: qsTr("No custom shape defined. Use 'Add' to define one with up to ten points. Note that 0% and 100% are implied.")
	}

	delegate: Component {
		MbItemRow {
			description: qsTr("Point") + " " + (index + 1)
			values: [
				MbTextBlock { item.value: modelData[0] + '%'; width: 60 },
				MbTextBlock { item.value: modelData[1] + '%'; width: 60 }
			]
		}
	}
}
