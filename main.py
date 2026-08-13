import machine
import BME280.bme280_int as bme280
import dht
import ntptime
import time
import machine
import asyncio
import json

from umqtt.simple import MQTTClient

import config
from connect import connect_wifi

bme_sensor = None
dht_sensor = None
mqtt_client = None
mqtt_connected = False

MQTT_DISCOVERY_TOPIC = "homeassistant/device/{}/config".format(config.device_id)
STATE_TOPICS = {
    "bme280_temp": config.device_id + "/env/bme280_temp",
    "bme280_hum":  config.device_id + "/env/bme280_hum",
    "bme280_press":config.device_id + "/env/bme280_press",
    "dht22_temp":  config.device_id + "/env/dht22_temp",
    "dht22_hum":   config.device_id + "/env/dht22_hum"
}

def _mqtt_discover_sensors():
    """
    Publish discovery payloads for BME280 and DHT22 sensors to Home Assistant.
    """
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
            "name": "ESP32 EnvSens Compare",
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
    },
        "qos": 1
    }

    print("Payload size: ", len(json.dumps(discovery_payload)))
    print("Sending combined discovery payload:\n", bytes(json.dumps(discovery_payload),'utf-8'))

    mqtt_client.publish(MQTT_DISCOVERY_TOPIC, bytes(json.dumps(discovery_payload), 'utf-8'), retain=True)
    


def _bme280_init():
    global bme_sensor
    
    print("Initializing BME280 sensor.")

    pinSDA = machine.Pin(config.sda_pin)
    pinSCL = machine.Pin(config.scl_pin)

    i2c = machine.I2C(scl=pinSCL, sda=pinSDA)

    bme_sensor = bme280.BME280(i2c=i2c)

def _bme280_read():
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

def _dht_init():
    global dht_sensor
    
    print("Initializing DHT22 sensor.")
    
    dht_sensor = dht.DHT22(config.dht_out)
    
def _dht_read():
    global dht_sensor
    global client
    
    dht_sensor.measure()
    temp = dht_sensor.temperature()
    hum = dht_sensor.humidity()

    return temp, hum

def _mqtt_init():
    global mqtt_client
    
    print("Initializing MQTT client.")
    
    # Assume config.py has: mqtt_broker, mqtt_port (optional, default 1883), mqtt_user (optional), mqtt_pass (optional), client_id, device_id, device_name
    mqtt_client = MQTTClient(config.device_id, config.mqtt_broker, port=getattr(config, 'mqtt_port', 1883))
    
    if hasattr(config, 'mqtt_user') and hasattr(config, 'mqtt_pass'):
        mqtt_client.set_credentials(config.mqtt_user, config.mqtt_pass)
    try:
        mqtt_client.connect()
        mqtt_connected = True
        print("Connected to MQTT broker.")
    except Exception as e:
        print("Failed to connect to MQTT broker:", e)
        mqtt_connected = False

async def _mqtt_reconnect_task():
    global mqtt_client
    global mqtt_connected
    
    print("Attempting to reconnect to MQTT broker...")
    while True:
        if mqtt_connected == False:
            print("MQTT not connected. Attempting to reconnect...")
            try:
                mqtt_client.connect()
                mqtt_connected = True
                print("Reconnected to MQTT broker.")
            except Exception as e:
                print("Failed to reconnect to MQTT broker:", e)
                mqtt_connected = False

        await asyncio.sleep(5)  # Wait before retrying

def _mqtt_publish(topic, message):
    global mqtt_connected
    if not mqtt_connected:
        return
    
    try:
        mqtt_client.publish(topic, payload)
    except OSError as e:
        print("MQTT publish failed:", e)
        mqtt_connected = False

async def _sense_task():
    global mqtt_client

    try:
        _bme280_init()
        _dht_init()
    except Exception as e:
        print("Failed to initialize BME280 sensor:", e)
        return

    print("Sensors initialized.")

    while True:
        # Read BME280 sensor values
        try:
            bme_temp, bme_press, bme_hum = _bme280_read()
        except Exception as e:
            print("Failed to read BME280 sensor:", e)
            bme_temp, bme_press, bme_hum = None, None, None
        # Read DHT22 sensor values
        try:
            dht_temp, dht_hum = _dht_read()
        except Exception as e:
            print("Failed to read DHT22 sensor:", e)
            dht_temp, dht_hum = None, None
        
        try:
            print("Sending BME280 values: ", bme_temp, bme_press, bme_hum )
            mqtt_client.publish(STATE_TOPICS["bme280_temp"], str(bme_temp))
            mqtt_client.publish(STATE_TOPICS["bme280_hum"], str(bme_hum))
            mqtt_client.publish(STATE_TOPICS["bme280_press"], str(bme_press))

            print("Sending DHT values: ", dht_temp, dht_hum)
            mqtt_client.publish(STATE_TOPICS["dht22_temp"], str(dht_temp))
            mqtt_client.publish(STATE_TOPICS["dht22_hum"], str(dht_hum))

        except Exception as e:
            print("Error reading sensors or publishing data:", e)

        await asyncio.sleep(config.sleep_time)

async def _watchdog_task(wdt):
    while True:
        wdt.feed()
        await asyncio.sleep(config.wdt_feed_interval)

def main():
    wlan = connect_wifi()

    time.sleep(3)
    
    wdt = machine.WDT(timeout=config.wdt_timeout_ms)

    # Initialize NTP time synchronization
    try:
        print("Synchronizing time with NTP server...")
        ntptime.settime()
        print("Time synchronized.")
    except Exception as e:
        print("Failed to synchronize time:", e)

    # Initialize MQTT client and HA discover
    _mqtt_init()
    _mqtt_discover_sensors()

    loop = asyncio.get_event_loop()
    loop.create_task(_sense_task())
    loop.create_task(_mqtt_reconnect_task())
    loop.create_task(_watchdog_task(wdt))

    loop.run_forever()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Shuting down.")