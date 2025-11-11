import machine
import BME280.bme280_int as bme280
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

    bme_sensor = bme280.BME280(i2c=i2c)

def bme280_read():
    global bme_sensor
    global client
    
    #sensor.measure()
    temp,press,hum = bme_sensor.read_compensated_data()

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
    
    dht_sensor = dht.DHT22(config.dht_out)
    
def dht_read():
    global dht_sensor
    global client
    
    dht_sensor.measure()
    temp = dht_sensor.temperature()
    hum = dht_sensor.humidity()
    
    time = utime.localtime()
    return temp, hum
def mqtt_init():
    global mqtt_client
    
    print("Initializing MQTT client.")
    
    # Assume config.py has: mqtt_broker, mqtt_port (optional, default 1883), mqtt_user (optional), mqtt_pass (optional), client_id, device_id, device_name
    mqtt_client = MQTTClient(config.client_id, config.mqtt_broker, port=getattr(config, 'mqtt_port', 1883))
    
    if hasattr(config, 'mqtt_user') and hasattr(config, 'mqtt_pass'):
        mqtt_client.set_credentials(config.mqtt_user, config.mqtt_pass)
    mqtt_client.connect()
    
    print("Connected to MQTT broker.")
        
bme280_init()
dht_init()

mqtt_init()

while True:
    bme_tem, bme_press, bme_hum = bme280_read()
    dht_temp, dht_hum = dht_read()
    print("BME280 values: ", bme_tem, bme_press, bme_hum )
    print("DHT values: ", dht_temp, dht_hum)
    utime.sleep(5)