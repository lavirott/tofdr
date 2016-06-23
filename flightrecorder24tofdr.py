#!/usr/bin/env python
# -*- coding: utf-8 -*-

import csv

import math
import numpy as np
from scipy.ndimage import gaussian_filter1d

import getopt, sys
import os
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
# Correct and smooth data
def fix_raw_data(data):
	fixed_data = []
	for index, row in enumerate(data):
		try:
			pointA = data[index]
			pointB = data[index + 1]
			if great_circle(pointA, pointB) == 0:
				continue
		except:
			break
		fixed_row = row
		# Correction of altitude: substract 121 feet
		altitude = row[3] - 137
		if altitude < 13: # TODO: depend on the aiport altitude
			altitude = 13
		fixed_row[3] = altitude
		# Correction of roll (+160°)
		roll = row[4]
		if (roll > 0):
			roll -= 180
		else:
			roll += 180
		fixed_row[4] = roll
		# Correction of pitch (+25°)
		pitch = row[5]
		fixed_row[5] = pitch + 23

		fixed_data.append(fixed_row)
	return fixed_data

#####
# Manage to FDR format

def to_fdr(data):
	global time_factor
	pos_lst = []
	timelst = []
	bear_lst = []
	pitch_lst = []
	vel_lst = []
	roll_lst = []
	degsec_lst = []

	cnt = 0
	cumT = 0.0

	fdr_data=[]

	# First select the right parameters for the moment (TODO: to be modified to be more suitable)
	smooth_raw = False
	rpy = True
	mov_avg = False
	
	for index, row in enumerate(data):
		#print str(index) + ': ' + str(row)
		pos_lst.append([row[0], row[1], row[2], row[3]]) # Done: added row[0] to be able to use great_circle
		pointA = (pos_lst[len(pos_lst) - 2])
		pointB = (pos_lst[len(pos_lst) - 1])
		#print str(pos_lst) + '\nPoint A: ' + str(pointA) + '\nPoint B: ' + str(pointB) + '\n'

		if smooth_raw:	
			timelst.append(row[4])
		else:		
			if index == 0:
				Tdif = 0.0
			else:
				Tdif = row[0] - data[index - 1][0]
			cumT += Tdif
			timelst.append(cumT)
		
		time_chng = (timelst[len(timelst) - 1] - timelst[len(timelst) - 2]) / time_factor
		if time_chng == 0.0:
			time_chng = 0.0000000001
			print 'Suspect time at index ' + str(index) + ' !'
		
		# Get bearing
		if rpy:
			bearing = row[6]
			bear_lst.append(bearing)
		else:
			if cnt == 0:
				bearing = 0
			else:	
				d = great_circle(pointA, pointB)
				if d > 0:
					bearing = BearingCalc(pointA, pointB)		
					bear_lst.append(bearing)
				else:
					bearing = bear_lst[len(bear_lst)-1]

		#Get roll
		if rpy:
			roll = row[4]
			roll_lst.append(roll)
		else:
			if len(pos_lst) < 3:
				roll = 0.0
				vel = 0.0		
			else:	
				p0 = (pos_lst[len(pos_lst)-3])
				p1 = (pos_lst[len(pos_lst)-2])
				p2 = (pos_lst[len(pos_lst)-1])

				b_last = bear_lst[len(bear_lst)-1]
				b_prev = bear_lst[len(bear_lst)-2]
			
				degchg = 180 - abs(180 - abs(b_last-b_prev))			
				degsec1 = degchg/abs(time_chng)		
				degsec_lst.append(degsec1)		
			
				if smooth_raw:
					vel1 = row[3]
				else:
					d = great_circle(pointA, pointB)							
					vel1 = d / abs(time_chng)

					vel_lst.append(vel1)
				dir = GetDir(p0,p1,p2)

				if mov_avg == True: 
					if len(vel_lst) > avg_win:	
						vel = sum(vel_lst[len(vel_lst)-avg_win:])/avg_win	
						degsec = sum(degsec_lst[len(degsec_lst)-avg_win:])/avg_win
					else:
						vel = vel1
						degsec = degsec1
				else:	
					vel = vel1
					degsec = degsec1
		
				roll = GetRoll(degsec, dir, vel)	
				roll_lst.append(roll)
		
		# Get pitch
		if rpy:
			pitch = row[5]
			pitch_lst.append(pitch)
		else:
			if cnt == 0:
				pitch = 0
			else:	
				pitch = DefPitch(pointA, pointB)	
				pitch_lst.append(pitch)

		if smooth_raw:
			t_st = row[4]
			v_st = row[3]
		else:
			t_st = timelst[len(timelst) - 1]
			# try:
				# v_st = vel
			# except:
			d = great_circle(pointA, pointB)
			v_st = (d / abs(time_chng)) / 0.51444444
			#print str(d) + ' ' + str(time_chng) + ' ' + str(v_st)
				
		if mov_avg == True: 
			if len(roll_lst) > avg_win: 
				roll = sum(roll_lst[len(roll_lst)-avg_win:])/avg_win
			if len(pitch_lst) > avg_win:	
				pitch = sum(pitch_lst[len(pitch_lst)-avg_win:])/avg_win
			if len(bear_lst) > avg_win:
				anglst = bear_lst[len(bear_lst)-avg_win:]
				bearing = AvAng(anglst)

		fdr_data.append([t_st, row[1], row[2], row[3], v_st, bearing, pitch, roll, d])
		cnt += 1
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

		f.write('DATA,' + t_str + ',25,' + lonstr + ',' + latstr + ',' + elevstr + ', 0,' + \
ailDefl + ',' + elevDefl + ',0,' + pitchstr + ',' + rollstr + ',' + hdgstr + ',' + kias_str + \
',0,0,0,0.5,20,0, 0,0,0,0,0,0,0,0,0, 11010,10930,4,4,90, 270,0,0,10,10,1,1,10,10,0,0,0,0,10,10, \
0,0,0,0,0,0,0,0,0,0,500, 29.92,0,0,0,0,0,0 , 1,1,0,0 , 2000,2000,0,0, 2000,2000,0,0 , 30,30,0,0 , \
100,100,0,0 , 100,100,0,0 , 0,0,0,0 , 0,0,0,0 , 1500,1500,0,0 , 400,400,0,0 , 1000,1000,0,0 , \
1000,1000,0,0 , 0,0,0,0,' + '\n')
		output.append([t_str, lonstr, latstr, elevstr, ailDefl, elevDefl, pitchstr, rollstr, hdgstr, kias_str])

	f.close()
	return output

#####
# Main Program

def usage():
	print "Usage: " + sys.argv[0] + " -i SOURCE -o DEST [option]"
	print "flightrecorder24tofdr.py generate kml, csv and fdr DEST files from a flightrecorder24 log"
	print "Options:"
	print "    -h, --help"
	print "        Print this message"
	print "    -i, --input=SOURCE"
	print "        Specify the input filename"
	print "    -o, --output=DEST"
	print "        Specify a generic filename as output (generate DEST.kml, DEST.fdr, ...)"
	print "    --start-time=TIME"
	print "        Specify the start time of the flight (truncated data before this time)."
	print "         Time is specified as day/month/year_hour:minute:second"
	print "    --stop-time=TIME"
	print "        Specify the stop time of the flight (truncated data after this time)."
	print "	       Time is specified as day/month/year_hour:minute:second"

def main(argv):
	global time_factor
	start_time = 0
	stop_time = time.mktime(time.localtime()) * time_factor
	try:
		opts, args = getopt.getopt(argv, "hi:o:", ["help", "input=", "output=", "start-time=", "stop-time="])
	except getopt.GetoptError:
		print sys.argv[0] + ": invalid option"
		usage()
		sys.exit(2)
	for opt, arg in opts:
		if opt in ("-h", "--help"):
			usage()
			sys.exit()
		elif opt in ("-i", "--input"):
			input_file = arg
		elif opt in ("-o", "--output"):
			output_file = arg
		elif opt in ("--start-time"):
			start_time = time.mktime(time.strptime(arg, "%d/%m/%Y_%H:%M:%S")) * time_factor
		elif opt in ("--stop-time"):
			stop_time = time.mktime(time.strptime(arg, "%d/%m/%Y_%H:%M:%S")) * time_factor


	raw_data, flight_feature = format_and_filter_csv(input_file, start_time, stop_time, output_file + '.csv')
	write_french_csv(raw_data, 'TIME;LONG;LAT;ALT;ROLL;PITCH;YAW', output_file + '_raw.csv')

	fixed_data = fix_raw_data(raw_data)
	write_french_csv(fixed_data, 'TIME;LONG;LAT;ALT;ROLL;PITCH;YAW', output_file + '_fixed.csv')
	write_kml(fixed_data, output_file + '.kml')

	fdr_data = to_fdr(fixed_data)
	write_french_csv(fdr_data, 'TIME;LONG;LAT;ALT;SPEED;BEARING;PITCH;ROLL; DISTANCE', output_file + '_fdr.csv')

	written_data = write_fdr(fdr_data, flight_feature, output_file + '.fdr')
	write_french_csv(written_data, 'TIME;LONG;LAT;ALT;AILDEFL;ELEVDEFL;PITCH;ROLL;HEADING;SPEED', output_file + '_written.csv')

	print_flight_info(fdr_data, flight_feature)

if __name__ == "__main__":
	main(sys.argv[1:])