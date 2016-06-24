#!/usr/bin/env python
# -*- coding: utf-8 -*-

import csv

import math
import numpy as np
from scipy.ndimage import gaussian_filter1d
import matplotlib.pyplot as plot

import getopt, os, sys
import time

time_factor = 1000.0 # Data in input format is epoch in milliseconds (so * 1000 compored to standard unix epoch)

# Input format of csv file from Flight Recorder 24
fields_srcs = ['timedate', 'time', 'lat', 'lon', 'h msl', 'speed', 'bearing', 'accuracy', 'nx', 'ny', 'nz', 'pitch', 'roll', 'yaw', 'original pitch', 'original roll', 'original yaw', 'pressure', 'baro', 'phase', 'event']

fields_dest = ['time', 'lon', 'lat', 'h msl', 'roll', 'pitch', 'yaw']

# Default format of a complete FDR file
#fields_dest = ['time', 'temp', 'lon', 'lat', 'h msl', 'h rad', 'ailn', 'elev', 'rudd', 'pitch', 'roll', 'heading', 'speed', 'VVI', 'slip', 'turn', 'mach', 'AOA', 'stall', 'flap request', 'flap actual', 'slat', 'sbrk', 'gear', 'Ngear', 'Lgear', 'Rgear', 'elev trim', 'NAV–1 frq', 'NAV–2 frq', 'NAV–1 type', 'NAV–2 type', 'OBS–1', 'OBS–2', 'DME–1', 'DME–2', 'NAV–1 h-def', 'NAV–2 h-def', 'NAV–1 n/t/f', 'NAV–2 n/t/f', 'NAV–1 v-def', 'NAV–2 v-def', 'OM', 'MM', 'IM', 'f-dir 0/1', 'f-dir pitch', 'f-dir roll', 'ktmac 0/1', 'throt mode', 'hdg mode', 'alt mode', 'hnav mode', 'glslp mode', 'speed selec', 'hdg selec', 'vvi selec', 'alt selec', 'baro', 'DH', 'Mcaut 0/1', 'Mwarn 0/1', 'GPWS 0/1', 'Mmode 0–4', 'Mrang 0–6', 'throt ratio', 'prop cntrl', 'prop rpm', 'prop deg', 'N1 %', 'N2 %', 'MPR', 'EPR', 'torq', 'FF', 'ITT', 'EGT', 'CHT']

class FlightFeature:
	date = ''
	time = ''
	location = ''
	pilot = ''
	aircrat = ''
	registration = ''
	
	def __str__(self):
		return "Aircraft: %s (%s)\nPilot: %s\nLocation: %s\nDate: %s Time: UTC %s" % (self.aircraft, self.registration, self.pilot, self.location, self.date, self.time)

#####
# Clean and Filter input data
def zero_listmaker(n):
	return [0] * n

def is_number(s):
	try:
		float(s)
		return True
	except ValueError:
		return False

_start_time = float('NaN')
def convert_time(value):
	global _start_time
	global time_factor
	if math.isnan(_start_time):
		_start_time = float(value)
		return 0.0
	else:
		return (float(value) - _start_time) / time_factor

def date_time_parse(value):
	# Value format: UTC 24-Apr-2016 08:50:08.295
	date_time = value.split('.')[0] # Split to avoid milli-seconds
	conv = time.strptime(date_time, "%Z %d-%b-%Y %H:%M:%S")
	return time.strftime("%d/%m/%Y", conv), time.strftime("%H:%M:%S", conv)
		
def format_and_filter_csv(input_file, start_time, stop_time, output_file):
	output = []
	first_valid_row = True
	ff = FlightFeature()
	with open(input_file, 'rb') as ifile:
		reader = csv.reader(ifile, delimiter=';', quotechar='|')
		for index, row in enumerate(reader):
			if (index < 3):
				# Do not care of line 0 and 2 which contain text headers
				if (index == 1):
					if (row[0] == "1.2.1") or (row[0] == "1.2.4"): # Check the Flight24 version
						# Don't get date from that field beacause it's not Zulu time
						ff.location = row[3]
						ff.pilot = row[5]
						ff.aircraft = row[6]
						ff.registration = row[7]
					else:
						print "Warning: you are using a Flight24 release different from the one tested."
			else: # Index line >= 3 contains relevant data
				# If row correspond to data that we want to convert
				if (len(row) == len(fields_srcs)) and (is_number(row[2])):
					if (int(row[1]) < int(start_time)): # Don't care about epoch time < start_time
						continue
					if (int(row[1]) > int(stop_time)): # Stop parsing after epoch time > stop_time
						break
					if (first_valid_row): # Store the date and time of the first valid row (beginning of flight)
						ff.date, ff.time = date_time_parse(row[0])
						first_valid_row = False
					nan_val = False
					output_row = zero_listmaker(len(fields_dest))
					for column in range(len(fields_srcs)):
						# Try to find src field in dest
						try:
							ind = fields_dest.index(fields_srcs[column])
						except ValueError:
							ind = -1
						# if field is present, then add value to the right place
						if (ind != -1):
							# if (fields_srcs[column] == 'time'):
								# value = convert_time(row[column])
							# else:
							value = float(row[column])
							if (not is_number(value)) or (math.isnan(value)):
								nan_val = True
								break
							output_row[ind] = value
					#output_row = ['DATA'] + output_row + ['']
					if not(nan_val):
						output.append(output_row)

	# with open(output_file, 'wb') as ofile:
		# writer = csv.writer(ofile, delimiter=';')
		# writer.writerows(output)
	return output, ff

#####
# Utilities to make some computations
def great_circle(pointA, pointB):
	lon1 = math.radians(pointA[1])
	lat1 = math.radians(pointA[2])
	lon2 = math.radians(pointB[1])
	lat2 = math.radians(pointB[2])
	R = 6371000
	x2 = (lon2 - lon1) * math.cos(0.5 * (lat2 + lat1))
	y2 = lat2 - lat1
	d = R * math.sqrt(x2 * x2 + y2 * y2)
	return d

def get_path_length(data):
	total_length = 0.0
	segment_list = []
	segment_list.append(0.0)

	for index in range(len(data)-1):
		pointA = data[index]
		pointB = data[index + 1]
		segment_length = great_circle(pointA, pointB)
		total_length += segment_length
		segment_list.append(segment_length)
	return total_length, segment_list

#####
# Clean and smooth data
def clean_raw_data(data):
	cleaned_data = []
	for index, row in enumerate(data):
		# try:
			# pointA = data[index]
			# pointB = data[index + 1]
			# if great_circle(pointA, pointB) == 0:
				# continue
		# except:
			# break
		cleaned_row = row
		# Correction of altitude: substract 121 feet
		altitude = row[3] - 137
		if altitude < 13: # TODO: depend on the aiport altitude
			altitude = 13
		cleaned_row[3] = altitude
		# Correction of roll (+160°)
		roll = row[4]
		if (roll > 0):
			roll -= 180
		else:
			roll += 180
		cleaned_row[4] = roll
		# Correction of pitch (+25°)
		pitch = row[5]
		cleaned_row[5] = pitch + 23

		cleaned_data.append(cleaned_row)
	return cleaned_data

def smooth_data(data, sigma):
	mat = list(zip(*data))

	t = np.linspace(0, 1, len(mat[0]))
	t2 = np.linspace(0, 1, len(mat[0]))

	ret_data = []
	for col in mat:
		values_interp = np.interp(t2, t, col)
		values_filtered = gaussian_filter1d(values_interp, sigma)
		ret_data.append(values_filtered)

	return list(zip(*ret_data))

#####
# Manage FDR format
def to_fdr(data):
	global time_factor

	pos_lst = []
	timelst = []
	fdr_data=[]

	cumT = 0.0

	for index, row in enumerate(data):
		if index == 0:
			Tdif = 0.0
		else:
			Tdif = row[0] - data[index - 1][0]
		cumT += Tdif
		timelst.append(cumT)
		
		time_chng = (timelst[len(timelst) - 1] - timelst[len(timelst) - 2]) / time_factor
		if time_chng == 0.0:
			time_chng = 0.0000000001
			if index != 0:
				print 'Warning: suspect time at index ' + str(index) + ' !'
		
		# Get bearing
		roll = row[4]
		pitch = row[5]
		bearing = row[6] # bearing = yaw

		t_st = timelst[len(timelst) - 1]
		pos_lst.append([row[0], row[1], row[2], row[3]]) # Done: added row[0] to be able to use great_circle
		pointA = (pos_lst[len(pos_lst) - 2])
		pointB = (pos_lst[len(pos_lst) - 1])
		d = great_circle(pointA, pointB)
		v_st = (d / abs(time_chng)) / 0.51444444

		fdr_data.append([t_st, row[1], row[2], row[3], v_st, bearing, pitch, roll])

	return fdr_data

def print_flight_info(fdr_data, flight_feature):
	global time_factor
	print str(flight_feature) + '\n'

	path_length, segment_list = get_path_length(fdr_data)
	print 'Flight path distance: ' + '{0:.3f}'.format(path_length / 1000.0) + ' km'

	m, s = divmod(fdr_data[len(fdr_data) - 1][0] / time_factor, 60)
	h, m = divmod(m, 60)
	print "Flight time: %d:%02d:%02d" % (h, m, s)

#####
# Export function to different formats
def write_french_csv(data, header, file):
	csvfile = open(file, 'wb')
	csvfile.write(header + '\n')
	for row in data:
		for num in row:
			csvfile.write(str(num).replace('.', ',') + ';')
		csvfile.write('\n')
	csvfile.close()

def write_kml(data, kml_file):
	global time_factor

	(mdir, mfilename) = os.path.split(kml_file)
	(mnam, mext) = os.path.splitext(mfilename)

	coord_str = ''
	tag_str = ''
	_time = 0.0
	for index, row in enumerate(data):
		lonlatalt_str = str(row[1]) + ',' + str(row[2]) + ',' + str(int((float(row[3])) / 3.28084)) # Converted to meters instead of feet
		lnstr = lonlatalt_str + '\n'
		coord_str +=  lnstr
		if (row[0] >= _time):
			converted_time1 = time.strftime('%H:%M', time.localtime(row[0] / time_factor))
			converted_time2 = time.strftime('%H:%M:%S %d/%m/%Y', time.localtime(row[0] / time_factor))
			tagstr = '<Placemark>\n<name>' + converted_time1 + '</name>\n<description>' + converted_time2 + '</description>\n'
			tagstr += '<Point><coordinates>' + lonlatalt_str + '</coordinates></Point>\n</Placemark>\n'
			tag_str += tagstr
			if _time == 0.0:
				_time = row[0] + 60000.0
			else:
				_time += 60000.0

	f = open(kml_file, 'wb')
	f.write("<?xml version='1.0' encoding='UTF-8'?>\n")
	f.write("<kml xmlns='http://earth.google.com/kml/2.1'>\n")
	f.write("<Document>\n")
	f.write("	<name>" + mnam + '.kml' +"</name>\n")
	f.write("	<Placemark>\n")
	f.write("		<name>" + mnam + "</name>\n")
	f.write("		<description>spline path</description>\n")
	f.write("		<LineString>\n")
	f.write("			<tessellate>1</tessellate>\n")
	f.write("			<altitudeMode>absolute</altitudeMode>\n")
	f.write("			<coordinates>" + coord_str + "</coordinates>\n")
	f.write("		</LineString>\n")
	f.write("	</Placemark>\n")

	f.write("   <Folder>\n")
	f.write("      <name>Tags</name>\n")
	f.write("      <description>Tags added during the flight.</description>\n")
	f.write(tag_str)
	f.write("   </Folder>\n")

	f.write("</Document>\n")
	f.write("</kml>\n")
	f.close()

def write_fdr(data, flight_feature, fdr_file):
	(mdir, mfilename) = os.path.split(fdr_file)
	(mnam, mext) = os.path.splitext(mfilename)

	output = []
	f = open(fdr_file, 'wb')
	f.write('A' + '\n')
	f.write('2' + '\n')
	f.write('\n')
	f.write('COMM,Pilot=' +  flight_feature.pilot + ',\n')
	f.write('COMM,Location=' +  flight_feature.location + ',\n')
	f.write('TAIL,' + flight_feature.registration + ',\n')
	f.write('DATE,' + flight_feature.date + ',\n')
	f.write('PRES,29.83,\n')
	f.write('TEMP,65,\n')
	f.write('WIND,230,16,\n')
	f.write('TIME,' + flight_feature.time + '\n')
	f.write('\n')

	# Roll factor, set to 10 or so for small UAVs or RC models
	rf = 1.0
	
	for index, row in enumerate(data):
		t_str = '{0:.3f}'.format(convert_time(row[0]))
		lonstr = '{0:.6f}'.format(row[1])
		latstr = '{0:.6f}'.format(row[2])
		elevstr = str(int(row[3])) # * 3.28084
		pitchstr = '{0:.2f}'.format(row[6])
		rollstr = '{0:.2f}'.format(row[7] * rf)
		hdgstr = '{0:.2f}'.format(row[5])
		kias_str = '{0:.2f}'.format(row[4]) # * 1.94384449
		ailDefl = '{0:.2f}'.format((row[7] / 90.0) * 0.3)
		elevDefl = '{0:.2f}'.format((row[6] / 90.0) * 0.3)

		if index == 0:
			pitchstr = '{0:.2f}'.format(data[2][6])
			rollstr = '{0:.2f}'.format(data[3][7] * rf)
			hdgstr = '{0:.2f}'.format(data[2][5])
			ailDefl = '{0:.2f}'.format((data[3][7] / 90.0) * 0.3) 
			elevDefl = '{0:.2f}'.format((data[2][6] / 90.0) * 0.3)

		if index == 1:
			rollstr = '{0:.2f}'.format(data[3][7] * rf)
			ailDefl = '{0:.2f}'.format((data[3][7] / 90.0) * 0.3) 

		f.write('DATA,' + t_str + ',25,' + lonstr + ',' + latstr + ',' + elevstr + ', 0,' + ailDefl + ',' + elevDefl + ',0,' + pitchstr + ',' + rollstr + ',' + hdgstr + ',' + kias_str + ',0,0,0,0.5,20,0, 0,0,0,0,0,0,0,0,0, 11010,10930,4,4,90, 270,0,0,10,10,1,1,10,10,0,0,0,0,10,10, 0,0,0,0,0,0,0,0,0,0,500, 29.92,0,0,0,0,0,0, 1,1,0,0, 2000,2000,0,0, 2000,2000,0,0, 30,30,0,0, 100,100,0,0, 100,100,0,0, 0,0,0,0, 0,0,0,0, 1500,1500,0,0, 400,400,0,0, 1000,1000,0,0, 1000,1000,0,0, 0,0,0,0,' + '\n')
		output.append([t_str, lonstr, latstr, elevstr, ailDefl, elevDefl, pitchstr, rollstr, hdgstr, kias_str])

	f.close()
	return output

#####
# Plot functions

def find_label_index(format, label):
	for index, value in enumerate(format.split(';')):
		if (value == label):
			return index
	return -1

def plot_2Dfigure(data, format, color, output, output_prefix, x_axis, y_axis):
	mat = list(zip(*data))

	x_index = find_label_index(format, x_axis)
	y_index = find_label_index(format, y_axis)
	if (x_index == -1) or (y_index == -1): # if one of the parameter if not found, exit function
		print 'Warning: one of the parameter (' + x_axis + ', ' + y_axis + ') not found'
		return
	x_values = mat[x_index]
	y_values = mat[y_index]

	output_file = output_filename(output, 'plot' + output_prefix + '_', '_' + str(x_axis) + '_' + str(y_axis) + '.png')
	plot.xlabel(x_axis)
	plot.ylabel(y_axis)
	plot.title(str(x_axis) + '_' + str(y_axis))
	plot.plot(x_values, y_values, color)
	plot.axis( [ min(x_values), max(x_values), min(y_values), max(y_values) ] )
	#plot.show()
	plot.savefig(output_file)
	plot.clf()

def plot_figures(data, format, color, output, output_prefix):
	plot_2Dfigure(data, format, color, output, output_prefix, 'Lon', 'Lat')
	plot_2Dfigure(data, format, color, output, output_prefix, 'Time', 'Alt')
	plot_2Dfigure(data, format, color, output, output_prefix, 'Time', 'Speed')
	plot_2Dfigure(data, format, color, output, output_prefix, 'Time', 'Pitch')
	plot_2Dfigure(data, format, color, output, output_prefix, 'Time', 'Roll')
	plot_2Dfigure(data, format, color, output, output_prefix, 'Time', 'Bearing')

#####
# Main Program
def output_filename(output_dir, filename_prefix, filename_suffix):
	(dir, filename) = os.path.split(output_dir)
	return output_dir + '/' + filename_prefix + filename + filename_suffix

def usage():
	print "Usage: " + sys.argv[0] + " -i FILE -o DIR [option]"
	print
	print "flightrecorder24tofdr.py generates files in DIR from a flightrecorder24 log file"
	print
	print "Arguments:"
	print "    -i, --input=FILE"
	print "        Specify the input filename in csv format"
	print "    -o, --output=DIR"
	print "        Specify a directory name to generate kml, fdr files in"
	print "Options:"
	print "    -d, --debug"
	print "        Activate debug flag to create more data files for debugging"
	print "    -h, --help"
	print "        Print this message"
	print "    --info"
	print "        Print information about flight collected from input file"
	print "    -p, --plot"
	print "        Generate different figures representing principal parameters"
	print "    -s, --smooth=VAL"
	print "        Specify the sigma value used for the gaussian filter to smooth"
	print "    --start-time=TIME"
	print "        Specify the start time of the flight (truncated data before this time)."
	print "         Time is specified as day/month/year_hour:minute:second"
	print "    --stop-time=TIME"
	print "        Specify the stop time of the flight (truncated data after this time)."
	print "	       Time is specified as day/month/year_hour:minute:second"
	print "    --window=SIZE"
	print "        Specify the window size to determine the mobile average applied to data."

def main(argv):
	global time_factor

	# Initialize parameters values
	debug = False
	info = False
	input_file = ""
	output = ""
	plotting = False
	sigma = 0
	window = 0
	start_time = 0
	stop_time = time.mktime(time.localtime()) * time_factor
	try:
		opts, args = getopt.getopt(argv, "hdi:o:ps:w:", ["help", "debug", "input=", "output=", "plot", "smooth=", "window=", "info", "start-time=", "stop-time="])
	except getopt.GetoptError:
		print sys.argv[0] + ": invalid option"
		usage()
		sys.exit(2)
	for opt, arg in opts:
		if opt in ("-h", "--help"):
			usage()
			sys.exit()
		elif opt in ("-d", "--debug"):
			debug = True
		elif opt in ("-i", "--input"):
			input_file = arg
		elif opt in ("-o", "--output"):
			output = arg
		elif opt in ("-p", "--plot"):
			plotting = True
		elif opt in ("-s", "--smooth"):
			sigma = arg
		elif opt in ("-w", "--window"):
			window = arg
		elif opt in ("--info"):
			info = True
		elif opt in ("--start-time"):
			start_time = time.mktime(time.strptime(arg, "%d/%m/%Y_%H:%M:%S")) * time_factor
		elif opt in ("--stop-time"):
			stop_time = time.mktime(time.strptime(arg, "%d/%m/%Y_%H:%M:%S")) * time_factor

	if (input_file == "") or (output == ""):
		print sys.argv[0] + ": must specify arguments"
		usage()
		sys.exit(1)
	else:
		if not os.path.isdir(output):
			os.makedirs(output)

	default_format = 'Time;Lon;Lat;Alt;Roll;Pitch;Yaw'
	# Raw data
	raw_data, flight_feature = format_and_filter_csv(input_file, start_time, stop_time, output_filename(output, '', '.csv'))
	if debug:
		write_french_csv(raw_data, default_format, output_filename(output, '', '_raw.csv'))

	# Clean data
	cleaned_data = clean_raw_data(raw_data)
	if debug:
		write_french_csv(cleaned_data, default_format, output_filename(output, '', '_cleaned.csv'))

	# Smooth data
	smoothed_data = smooth_data(cleaned_data, sigma)
	if debug:
		write_french_csv(smoothed_data, default_format, output_filename(output, '', '_smooth.csv'))
	if plotting:
		plot_figures(smoothed_data, default_format, 'r', output, '_smooth')

	# Export data to KML format
	write_kml(smoothed_data, output_filename(output, '', '.kml'))

	# Transform to FDR format
	fdr_data = to_fdr(smoothed_data)
	if debug:
		write_french_csv(fdr_data, 'Time;Lon;Lat;Alt;Speed;Bearing;Pitch;Roll', output_filename(output, '', '_fdr.csv'))
	if plotting:
		plot_figures(fdr_data, 'Time;Lon;Lat;Alt;Speed;Bearing;Pitch;Roll', 'royalblue', output, '_fdr')

	# Write FDR data to file an export it to csv to verify what as been really written
	written_data = write_fdr(fdr_data, flight_feature, output_filename(output, '', '.fdr'))
	if debug:
		write_french_csv(written_data, 'TIME;LONG;LAT;ALT;AILDEFL;ELEVDEFL;PITCH;ROLL;HEADING;SPEED', output_filename(output, '', '_written.csv'))

	# Print information about flight
	if info:
		print_flight_info(fdr_data, flight_feature)

if __name__ == "__main__":
	main(sys.argv[1:])