import machine
import BME280.bme280_int as bme280
import dht
import utime
import ntptime
import ujson as json
import time
from machine import Timer
from machine import Pin
import sys
import config
from umqtt.simple import MQTTClient

bme_sensor = None
dht_sensor = None
mqtt_client = None

MQTT_DISCOVERY_TOPIC = "homeassistant/device/{}/config".format(config.device_id)
STATE_TOPICS = {
    "bme280_temp": config.device_id + "/env/bme280_temp",
    "bme280_hum":  config.device_id + "/env/bme280_hum",
    "bme280_press":config.device_id + "/env/bme280_press",
    "dht22_temp":  config.device_id + "/env/dht22_temp",
    "dht22_hum":   config.device_id + "/env/dht22_hum"
}

def mqtt_discover_sensors():
    discovery_payload = {
        "dev": {
            "ids": config.device_id,
            "name": config.device_id,
            "mf": "Spas Tech",
            "mdl": "ESP32",
            "sw": "1.0",
            "hw": "1.0",
            "sn": config.device_id
        },
        "o": {
            "name": "ESP32 Env Sensors",
            "sw": "1.0",
        },
        "cmps": {
        "bme280_temp": {
            "p": "sensor",
            "device_class": "temperature",
            "unit_of_measurement": "°C",
            "value_template": "{{ value }}",
            "unique_id": "bme280_temperature",   # renamed
            "name": "BME280 Temperature",        # friendly name
            "state_topic": STATE_TOPICS["bme280_temp"]
        },
        "bme280_hum": {
            "p": "sensor",
            "device_class": "humidity",
            "unit_of_measurement": "%",
            "value_template": "{{ value }}",
            "unique_id": "bme280_humidity",
            "name": "BME280 Humidity",
            "state_topic": STATE_TOPICS["bme280_hum"]
        },
        "bme280_press": {
            "p": "sensor",
            "device_class": "pressure",
            "unit_of_measurement": "hPa",
            "value_template": "{{ value }}",
            "unique_id": "bme280_pressure",
            "name": "BME280 Pressure",
            "state_topic": STATE_TOPICS["bme280_press"]
        },
        "dht22_temp": {
            "p": "sensor",
            "device_class": "temperature",
            "unit_of_measurement": "°C",
            "value_template": "{{ value }}",
            "unique_id": "dht22_temperature",   # renamed
            "name": "DHT22 Temperature",        # friendly name
            "state_topic": STATE_TOPICS["dht22_temp"]
        },
        "dht22_hum": {
            "p": "sensor",
            "device_class": "humidity",
            "unit_of_measurement": "%",
            "value_template": "{{ value }}",
            "unique_id": "dht22_humidity",
            "name": "DHT22 Humidity",
            "state_topic": STATE_TOPICS["dht22_hum"]
        }
    }
        "qos": 1
    }

    mqtt_client.publish(MQTT_DISCOVERY_TOPIC, bytes(json.dumps(discovery_payload), 'utf-8'), retain=True)


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
mqtt_discover_sensors()

while True:
    bme_tem, bme_press, bme_hum = bme280_read()
    dht_temp, dht_hum = dht_read()
    print("BME280 values: ", bme_tem, bme_press, bme_hum )
    print("DHT values: ", dht_temp, dht_hum)
    utime.sleep(5)