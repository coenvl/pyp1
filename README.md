# PyP1

This program takes a P1 frame from the P1 serial bus, converts it to an InfluxDb data point, and posts it to a database of your desire.

## Requirements
- python3
- pip (to get python packages)

## Installation

Using pip:

```
pip install -r requirements.txt
```

## Running
```
python pyp1.py
```

Or automate running by adding such a line to your crontab:
```
*/5 * * * * /usr/bin/python /folder/to/this/repo/pyp1.py
```
