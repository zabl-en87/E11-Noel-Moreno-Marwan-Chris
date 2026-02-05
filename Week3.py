import adafruit_bme680
import datetime
import board
import time
import numpy as np


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




while x<4:
    
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
    np.savetxt('score.csv', [p for p in zip(localTime, localTemp, localGas, localRelHum, localPressure, localAltitude)], delimiter = ',', fmt = '%s')
    x = int(x+1)

    time.sleep(2)
    
