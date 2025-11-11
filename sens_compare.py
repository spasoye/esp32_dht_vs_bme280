import machine
import BME280.bme280_int as bme280
import dht
import utime
import ntptime
import json
import time
from machine import Timer
from machine import Pin
import sys
import config
from umqtt.simple import MQTTClient

bme_sensor = None
dht_sensor = None
mqtt_client = None

#def mqtt_init():
#    global mqtt_client
#    print("Initializing MQTT client.")
#    mqtt_client = MQTTClient(config.name, config.broker)
    
#    mqtt_client.connect()
 
def mqtt_discover_sensors():
    sensors = [
        {
            "name": "BME280 Temperature",
            "unit": "°C",
            "device_class": "temperature",
            "state_topic": f"{config.mqtt_base_topic}/sensor/bme280_temperature/state",
            "unique_id": "bme280_temperature",
        },
        {
            "name": "BME280 Humidity",
            "unit": "%",
            "device_class": "humidity",
            "state_topic": f"{config.mqtt_base_topic}/sensor/bme280_humidity/state",
            "unique_id": "bme280_humidity",
        },
        {
            "name": "BME280 Pressure",
            "unit": "hPa",
            "device_class": "pressure",
            "state_topic": f"{config.mqtt_base_topic}/sensor/bme280_pressure/state",
            "unique_id": "bme280_pressure",
        },
        {
            "name": "DHT22 Temperature",
            "unit": "°C",
            "device_class": "temperature",
            "state_topic": f"{config.mqtt_base_topic}/sensor/dht22_temperature/state",
            "unique_id": "dht22_temperature",
        },
        {
            "name": "DHT22 Humidity",
            "unit": "%",
            "device_class": "humidity",
            "state_topic": f"{config.mqtt_base_topic}/sensor/dht22_humidity/state",
            "unique_id": "dht22_humidity",
        },
    ]

    for s in sensors:
        topic = f"{config.mqtt_base_topic}/sensor/{s['unique_id']}/config"
        payload = {
            "name": s["name"],
            "unique_id": s["unique_id"],
            "state_topic": s["state_topic"],
            "unit_of_measurement": s["unit"],
            "device_class": s["device_class"],
            "device": {
                "identifiers": [config.client_id],
                "name": config.client_id,
                "model": "ESP32 MicroPython",
                "manufacturer": "DIY"
            }
        }
        mqtt_client.publish(topic, bytes(json.dumps(payload)), retain=True)
        print(f"Published discovery for {s['name']}")
    
#     discovery_payload = {
#         "device": {
#             "identifiers": f'{DEVICE_ID}',  # Unique device identifier
#             "name": "doorbell",          # Device name
#             "manufacturer": "ESP32",   # Optional
#             "model": f'{DEVICE_ID}',    # Optional
#             "configuration_url": f'http://{DEVICE_IP}'
#         },
#         "o": {  # Device metadata (optional)
#             "name": "doorbell"
#         },
#         "cmps": {  # Components of the device
#             "button": {  # Button trigger
#                 "p": "device_automation",
#                 "automation_type": "trigger",
#                 "payload": "short_press",
#                 "topic": "doorbell/triggers/button1",
#                 "type": "button_short_press",
#                 "subtype": "button_1"
#             },
#             "temp": {  # Environment sensor
#                 "p": "sensor",
#                 "state_topic": "doorbell/env_sens/temp",
#                 "unique_id": "doorbell_temp",
#                 "name": "Doorbell temperature",
#                 "unit_of_measurement": "°C",
#                 "value_template": '{{ value }}'
#             },
#             "humd": {  # Environment sensor
#                 "p": "sensor",
#                 "state_topic": "doorbell/env_sens/humd",
#                 "unique_id": "doorbell_hum",
#                 "name": "Doorbell humidity",
#                 "unit_of_measurement": "%",
#                 "value_template": '{{ value }}'
#             },
#             "press": {  # Environment sensor
#                 "p": "sensor",
#                 "state_topic": "doorbell/env_sens/press",
#                 "unique_id": "doorbell_press",
#                 "name": "Doorbell pressure",
#                 "unit_of_measurement": "hPa",
#                 "value_template": '{{ value }}'
#             }
#         }
#     }
# 
#     # Publish the combined discovery payload
#     print("Payload size: ", len(json.dumps(discovery_payload)))
#     print("Sending combined discovery payload:\n", bytes(json.dumps(discovery_payload),'utf-8'))
#     
#     mqtt_client.publish(MQTT_DISCOVERY_TOPIC, bytes(json.dumps(discovery_payload),'utf-8'))



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