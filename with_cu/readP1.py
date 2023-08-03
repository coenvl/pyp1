#!/usr/bin/python
# Python script to get Smartmeter P1 info based on a "cu -l /dev/ttyUSB0 -s 9600 --parity=none" call
# Based on user3210303's work on http://stackoverflow.com/questions/20596908/serial-communication-works-in-minicom-but-not-in-python
# Pure Python seems to drop content from P1
# Tested on a Kamstrup 162JxC smart meter connected to a Raspberry Pi with Raspbian

import time
import os
import signal
import subprocess
import re

from datetime import datetime
from influxdb import InfluxDBClient

device = '/dev/ttyUSB0'
bitrate = 115200
parity = 'none'

dbhost = '192.168.178.200'
dbport = 8086


def getP1stuff():
	linecounter = 0
	stack = []
	process = subprocess.Popen('cu -l {} -s {} --parity={} 2> /dev/null'.format(device, bitrate, parity), shell=True, stdout=subprocess.PIPE, bufsize=1, preexec_fn=os.setsid)

	inblock = False
	while linecounter < 75: 	# max number of lines; if this is reached, something is wrong
		line = process.stdout.readline().strip()
		linecounter = linecounter + 1
		if line.find('/')==0:
			inblock = True
		if inblock:
			stack.append(line)
		if line.find('!')==0:
			break

	os.killpg(process.pid, signal.SIGTERM) 
	return stack

def postInfluxDB(result, obis, key, unit = 'kWh', prod = 1):
	for line in result:
		if re.search(obis, line):
			m = re.search("\((\d+\.\d+)\*", line)
			value = float(m.group(1)) * prod
			#print '{}: {} {}'.format(key, value, unit).strip()
			return value

def postResults(result):
	consumption1 = postInfluxDB(result, '1-0:1.8.1', 'Consumption tariff 1')
	consumption2 = postInfluxDB(result, '1-0:1.8.2', 'Consumption tariff 2')
	production1 = postInfluxDB(result, '1-0:2.8.1', 'Production tariff 1')
	production2 = postInfluxDB(result, '1-0:2.8.2', 'Production tariff 2')
	consumption = postInfluxDB(result, '1-0:1.7.0', 'Consumption', 'W', 1000)
	production = postInfluxDB(result, '1-0:2.7.0', 'Production', 'W', 1000)
	gas = postInfluxDB(result, '0-1:24.2.1', 'Verbruik gas', 'm3')
	
	json = [
	{
		"measurement": "p1data",
		"time": str(datetime.now()),
		"fields": {
			"consumption_tariff1_kWh": consumption1,
			"consumption_tariff2_kWh": consumption2,
			"production_tariff1_kWh": production1,
			"production_tariff2_kWh": production2,
			"consumption_W": consumption,
			"production_W": production,
			"gas_consumption_m3": gas
		}
	}
	]

	#print(json)

	client = InfluxDBClient(host=dbhost, port=dbport)
	client.create_database('p1')
	client.switch_database('p1')
	success = client.write_points(json)
	if not success:
		print("Unable to uploade to InfluxDB")
	#else:
		#print("Successfully uploaded to InfluxDB")
	

trycounter = 100
while trycounter > 0:
	result = getP1stuff()
	trycounter -= 1 # count down
	if len(result) > 15:
		postResults(result)
		break

