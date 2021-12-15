import re
import serial

from typing import List, Dict
from influxdb import InfluxDBClient
from datetime import datetime

device = '/dev/ttyUSB0'
bitrate = 115200
parity = 'none'

dbhost = '192.168.178.200'
dbport = 8086

def getP1frame() -> List[str]:
	linecounter = 0
	frame = []
	inblock = False
	ser = serial.Serial(
		port=device,
		baudrate=bitrate,
		bytesize=serial.EIGHTBITS,
		parity=serial.PARITY_NONE,
		stopbits=serial.STOPBITS_ONE,
	)

	try:
		while linecounter < 75: # max number of lines; if this is reached, something is wrong
			line = ser.readline().decode(encoding="UTF-8", errors="strict").strip()
			linecounter += 1

			if len(line) == 0:
				continue
			if line[0] == '/':
				# This marks the start of a new frame
				inblock = True
			elif inblock and line[0] == '!':
				# This marks the end of a frame
				break

			if inblock:
				frame.append(line)
	finally:
		ser.close()
	return frame

def parse_value(line: str) -> float:
	m = re.search("\((\d+\.\d+)\*", line)
	return float(m.group(1))

def get_measurement(frame: List[str]) -> Dict:
	fields = {}
	for line in frame:
		if line.startswith('1-0:1.8.1'):
			fields['consumption_tariff1_kWh'] = parse_value(line)
		elif line.startswith('1-0:1.8.2'):
			fields['consumption_tariff2_kWh'] = parse_value(line)
		elif line.startswith('1-0:2.8.1'):
			fields['production_tariff1_kWh'] = parse_value(line)
		elif line.startswith('1-0:2.8.2'):
			fields['production_tariff2_kWh'] = parse_value(line)
		elif line.startswith('1-0:1.7.0'):
			fields['consumption_W'] = 1000 * parse_value(line)
		elif line.startswith('1-0:2.7.0'):
			fields['production_W'] = 1000 * parse_value(line)
		elif line.startswith('0-1:24.2.1'):
			fields['gas_consumption_m3'] = parse_value(line)
	
	return {
		"measurement": "p1data",
		"time": str(datetime.now()),
		"fields": fields
	}

def post_measurement(measurement: Dict) -> None:
	client = InfluxDBClient(host=dbhost, port=dbport, database='p1')
	if not client.write_points([measurement]):
		print("Unable to upload to InfluxDB")

if __name__ == "__main__":
	frame = getP1frame()
	measurement = get_measurement(frame)
	post_measurement(measurement)