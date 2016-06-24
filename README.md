# tofdr
This python script provides data transformation from raw sensors (GPS and IMU) to FDR formation used in X-Plane. During the transformation process, it can generate several files from log file exported in CSV format. It can create the following type of files to analyse or view your flight information: KML, FDR, CSV, PNG.

To record the raw data, I use a smartphone with the FlightRecorder24 application (but it can be recorded from any kind of device or application):
https://play.google.com/store/apps/details?id=com.tost.frederic.pro1flightrecorder&hl=fr

This script is inspired by fdr_tools https://opengeoxplane.net/fdr_tools/ and enable more features (like avoiding GUI to use command line parameters, generation of figures, more functions to clean source code).

## Install

```
https://github.com/lavirott/tofdr && cd tofdr
chmod a+x flightrecorder24tofdr.py
sudo apt-get install python-numpy python-scipy python-matplotlib
```
## Run

```
cd tofdr
./flightrecorder24tofdr.py --input flight_recorder.csv --output flight1
```

## Usage

The input file must at least contain the following information in the CSV format in the following order (input parameters can be definied in the script): Time, Longitude, Latitude, Altitude (from GPS sensor), Roll, Pitch and Yaw (from IMU sensor)

The generated files depend on the command line activated parameters. You can find below the command's help.

```
Arguments:
    -i, --input=FILE
        Specify the input filename in csv format
    -o, --output=DIR
        Specify a directory name to generate kml, fdr files in
Options:
    -d, --debug
        Activate debug flag to create more data files for debugging
    -h, --help
        Print this message
    --info
        Print information about flight collected from input file
    -p, --plot
        Generate different figures representing principal parameters
    -s, --smooth=VAL
        Specify the sigma value used for the gaussian filter to smooth
    --start-time=TIME
        Specify the start time of the flight (truncated data before this time).
         Time is specified as day/month/year_hour:minute:second
    --stop-time=TIME
        Specify the stop time of the flight (truncated data after this time).
	       Time is specified as day/month/year_hour:minute:second
    --window=SIZE
        Specify the window size to determine the mobile average applied to data.

Options for fixing incorrect values:

    All these options enable to apply a default correction on all values.
    This append when the collecting device was not in the right position
    when recording data. So translate logged data by specified value.

    --fix-airport-elevation=VAL
        Set the default elevation of the airport to be sure that no data are (feet)
        under this limit
    --fix-elevation=VAL
        Fix the elevation values adding VAL (feet)
    --fix-pitch=VAL
        Fix the pitch values adding VAL angle (degre)
    --fix-roll=VAL
        Fix the roll values adding VAL angle (degre)
    --fix-yaw=VAL
        Fix the yaw values adding VAL angle (degre)
```