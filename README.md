# tofdr
Script to provide data transformation to the XPlane FDR format

This script is inspired by fdr_tools https://opengeoxplane.net/fdr_tools/

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
This python script generates several files from a flightrecorder24 log file exported in csv format. It can create the following type of files to analyse or view your flight information . The generated files depend on the command line activated parameters. You can find below the command's help.

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
```