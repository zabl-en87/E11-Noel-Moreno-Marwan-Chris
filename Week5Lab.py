import adafruit_bme680
import datetime
import board
import time
import numpy as np
import sys
import csv
import busio
from digitalio import DigitalInOut, Direction, Pull

from adafruit_pm25.i2c import PM25_I2C



arguments = sys.argv

print(arguments)

data_path = 'data/' + arguments[1]
runtime = int(arguments[2])

file = open(data_path, 'w' , newline = None)
csvwriter = csv.writer(file, delimiter = ',')

# Create sensor object, communicating over the board's default I2C bus
i2c = board.I2C()   # uses board.SCL and board.SDA
bme680 = adafruit_bme680.Adafruit_BME680_I2C(i2c)

# change this to match the location's pressure (hPa) at sea level
bme680.sea_level_pressure = 1013.25

reset_pin = None

import serial
uart = serial.Serial("/dev/ttyS0", baudrate=9600, timeout=0.25)

from adafruit_pm25.uart import PM25_UART
pm25 = PM25_UART(uart, reset_pin)


i = 0
localTime = ["Time"]
localTemp = ["Temperature"]
localGas = ["Gas"]
localRelHum = ["Relative Humidity"]
localPressure = ["Pressure"]
localAltitude = ["Altitude"]


meta = ['time', 'concentration', 'particles03', 'particles05', 'particles10', 'particles25', 'particles50', 'particles100',localTime, localTemp, localGas, localRelHum, localPressure, localAltitude]
csvwriter.writerow(meta)




masList = [localTime, localTemp, localGas, localRelHum, localPressure, localAltitude,]

while i < runtime:
    time.sleep(1)

    try:
        aqdata = pm25.read()
        # print(aqdata)
    except RuntimeError:
        print("Unable to read from sensor, retrying...")
        continue

    current_time = datetime.datetime.now()
    #print(current_time.strftime("%H:%M:%S"))
    a = current_time.strftime("%H:%M:%S")
    b = bme680.temperature
    c = bme680.gas
    d = bme680.relative_humidity
    e = bme680.pressure
    f = bme680.altitude
    Info1 = [a,b,c,d,e,f]
    print(Info1)
    localTime.append(a)
    localTemp.append(b)
    localGas.append(c)
    localRelHum.append(d)
    localPressure.append(e)
    localAltitude.append(f)

    csvwriter.writerow([i, aqdata["pm25 standard"], aqdata["particles 03um"], aqdata["particles 05um"], aqdata["particles 10um"], aqdata["particles 25um"], aqdata["particles 50um"], aqdata["particles 100um"],a,b,c,d,e,f])


    
    i = i + 1
  
file.close()
