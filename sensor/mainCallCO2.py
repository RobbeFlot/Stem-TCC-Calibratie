

from machine import UART, Pin,PWM

import machine
import time
from time import sleep

from scd4Pressure import SCD4X
from machine import Pin, I2C

import ssd1306

sensornummer=5
# Instantiate the micropyGPS object



i2c = I2C(scl=Pin(22), sda=Pin(21))

sensor = SCD4X(i2c)
sensor.start_periodic_measurement()
print("periodic meting wordt gestart")
time.sleep(5)
co2=0
tempSCD=0
humSCD=0


def readSCD():
    global co2
    global tempSCD
    global humSCD
    co2, tempSCD, humSCD = sensor.co2, sensor.temperature, sensor.relative_humidity
    print (co2, tempSCD, humSCD)
    
    
deadline = time.ticks_add(time.ticks_ms(), 300000)
readSCD()

print(deadline)
while  time.ticks_diff(deadline, time.ticks_ms()) > 0:
    print("Voer meting met SCD uit")
    readSCD()

    time.sleep(2)
    
sensor.stop_periodic_measurement()

print (" forced callibration wordt uitgevoerd")
sensor.FRC(410)