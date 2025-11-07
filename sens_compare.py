import machine
import BME280.bme280_float as bme280
import dht
import utime
import ntptime
import ujson
import time
from machine import Timer
from machine import Pin
import sys
import config

bme_sensor = None
dht_sensor = None

def bme280_init():
    global bme_sensor
    
    print("Initializing BME280 sensor.")

    pinSDA = machine.Pin(config.sda_pin)
    pinSCL = machine.Pin(config.scl_pin)

    i2c = machine.I2C(scl=pinSCL, sda=pinSDA)

    sensor = bme280.BME280(i2c=i2c)

def bme280_read(timer):
    global bme_sensor
    global client
    
    #sensor.measure()
    temp,press,hum = sensor.read_compensated_data()

    # C
    temp = temp / 100
    # hPa
    press = press / 256
    press = press / 100
    # %
    hum = hum / 1024
    
    return  temp,press,hum

def dht_init():
    global dht_sensor
    
    print("Initializing DHT22 sensor.")
    
    dht_sensor = dht.DHT22
    
def dht_read(timer):
    global dht_sensor
    global client
    
    dht_sensor.measure()
    temp = dht_sensor.temperature()
    hum = dht_sensor.humidity()
    
    time = utime.localtime()
    
    print("sensor read")
    
    try:
        client.publish(node_name + "/status", "online")
        client.publish(node_name + "/sens", "{ \"temp\": " + str(temp) +", \"hum\": " + str(hum) + "}")
    except Exception as e:
        print("fail while publishing:", e)