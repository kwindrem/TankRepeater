/*
 * This file is to share unit conversion functions between PageTankSensor.qml and PageTankSetup.qml.
 * Otherwise both files would contain the same code.
 * This file can be removed as soon as unit conversion has been globally implemented.
 */
.pragma library

function getVolumeFormat(unit)
{
	var fmt = {}

	switch (unit) {
		case 1:
			fmt.precision = 0
			fmt.stepSize = 1
			fmt.unit = "L"
			fmt.factor = 1000.0
			break;
		case 2:
			fmt.precision = 0
			fmt.stepSize = 1
			fmt.unit = "gal"
			fmt.factor = 219.969157
			break;
		case 3:
			fmt.precision = 0
			fmt.stepSize = 1
			fmt.unit = "gal"
			fmt.factor = 264.172052
			break;
		default:
			fmt.precision = 3
			fmt.stepSize = 0.005
			fmt.unit = "m<sup>3</sup>"
			fmt.factor = 1.0
			break;
	}

	return fmt
}

function volumeConvertToSI(unit, volume)
{
	return volume /= getVolumeFormat(unit).factor
}

function volumeConvertFromSI(unit, volume)
{
	return volume *= getVolumeFormat(unit).factor
}

/* Convert bus format to display format */
function formatVolume(unit, volume)
{
	var fmt = getVolumeFormat(unit)

	if (volume === undefined)
		return "--"

	volume = volumeConvertFromSI(unit, volume);
	return volume.toFixed(fmt.precision) + fmt.unit
}

function stringToPointArray(str)
{
	if (str !== undefined && str.length)
		return str.split(",").map(function(s) { return s.split(":").map(function(x) { return +x } ) });

	return [];
}

function pointArrayToString(a)
{
	return a.map(function(x) { return x.join(":") }).join(",");
}
