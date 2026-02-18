import adafruit_bme680
import datetime
import board
import time
import numpy as np
import sys
import csv

#Start of weather code

arguments = sys.argv

print(arguments)

data_path = 'data/' + arguments[1]
runtime = int(arguments[2])

# Create sensor object, communicating over the board's default I2C bus
i2c = board.I2C()   # uses board.SCL and board.SDA
bme680 = adafruit_bme680.Adafruit_BME680_I2C(i2c)

# change this to match the location's pressure (hPa) at sea level
bme680.sea_level_pressure = 1013.25
x = 0
localTime = ["Time"]
localTemp = ["Temperature"]
localGas = ["Gas"]
localRelHum = ["Relative Humidity"]
localPressure = ["Pressure"]
localAltitude = ["Altitude"]
masList = [localTime, localTemp, localGas, localRelHum, localPressure, localAltitude]




while x<runtime:
    
    #print("\nTemperature: %0.1f C" % bme680.temperature)
    #print("Gas: %d ohm" % bme680.gas)
    #print("Humidity: %0.1f %%" % bme680.relative_humidity)
    #print("Pressure: %0.3f hPa" % bme680.pressure)
    #print("Altitude = %0.2f meters" % bme680.altitude) 
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
    np.savetxt(data_path, [p for p in zip(localTime, localTemp, localGas, localRelHum, localPressure, localAltitude)], delimiter = ',', fmt = '%s')
    x = int(x+1)

    time.sleep(2)


#Start of air quality sensor code

#arguments = sys.argv
#print(arguments)

#data_path = 'data/' + arguments[1]
#runtime = int(arguments[2])


file = open(data_path, 'w' , newline = None)
csvwriter = csv.writer(file, delimiter = ',')

meta = ['time', 'concentration', 'particles03', 'particles05', 'particles10', 'particles25', 'particles50', 'particles100']
csvwriter.writerow(meta)

#for i in range(10):
 # now = time.time()
  #value = np.random.random()
  #csvwriter.writerow([now, value])


# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

"""
Example sketch to connect to PM2.5 sensor with either I2C or UART.
"""

import board
import busio
from digitalio import DigitalInOut, Direction, Pull

from adafruit_pm25.i2c import PM25_I2C

reset_pin = None
# If you have a GPIO, its not a bad idea to connect it to the RESET pin
# reset_pin = DigitalInOut(board.G0)
# reset_pin.direction = Direction.OUTPUT
# reset_pin.value = False


# For use with a computer running Windows:
# import serial
# uart = serial.Serial("COM30", baudrate=9600, timeout=1)

# For use with microcontroller board:
# (Connect the sensor TX pin to the board/computer RX pin)
# uart = busio.UART(board.TX, board.RX, baudrate=9600)

# For use with Raspberry Pi/Linux:
import serial
uart = serial.Serial("/dev/ttyS0", baudrate=9600, timeout=0.25)

# For use with USB-to-serial cable:
# import serial
# uart = serial.Serial("/dev/ttyUSB0", baudrate=9600, timeout=0.25)

# Connect to a PM2.5 sensor over UART
from adafruit_pm25.uart import PM25_UART
pm25 = PM25_UART(uart, reset_pin)

# Create library object, use 'slow' 100KHz frequency!
#i2c = busio.I2C(board.SCL, board.SDA, frequency=100000)
# Connect to a PM2.5 sensor over I2C
#pm25 = PM25_I2C(i2c, reset_pin)

print("Found PM2.5 sensor, reading data...")
i = 0
x = 5
while i < runtime:
    time.sleep(1)

    try:
        aqdata = pm25.read()
        # print(aqdata)
    except RuntimeError:
        print("Unable to read from sensor, retrying...")
        continue

    print()
    print("Concentration Units (standard)")
    print("---------------------------------------")
    print(
        "PM 1.0: %d\tPM2.5: %d\tPM10: %d"
        % (aqdata["pm10 standard"], aqdata["pm25 standard"], aqdata["pm100 standard"])
    )
    print("Concentration Units (environmental)")
    print("---------------------------------------")
    print(
        "PM 1.0: %d\tPM2.5: %d\tPM10: %d"
        % (aqdata["pm10 env"], aqdata["pm25 env"], aqdata["pm100 env"])
    )
    print("---------------------------------------")
    print("Particles > 0.3um / 0.1L air:", aqdata["particles 03um"])
    print("Particles > 0.5um / 0.1L air:", aqdata["particles 05um"])
    print("Particles > 1.0um / 0.1L air:", aqdata["particles 10um"])
    print("Particles > 2.5um / 0.1L air:", aqdata["particles 25um"])
    print("Particles > 5.0um / 0.1L air:", aqdata["particles 50um"])
    print("Particles > 10 um / 0.1L air:", aqdata["particles 100um"])
    print("---------------------------------------")

    csvwriter.writerow([i, aqdata["pm25 standard"], aqdata["particles 03um"], aqdata["particles 05um"], aqdata["particles 10um"], aqdata["particles 25um"], aqdata["particles 50um"], aqdata["particles 100um"]])


    
    i = i + 1
  
file.close()
