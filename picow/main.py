"""Read temp and humidity and send to MQTT server

Adapted from: http://www.steves-internet-guide.com/into-mqtt-python-client/
"""

import os
import sys

import time
import utime

# Imports for picow
import machine
from machine import Pin

# Imports for MQTT
import rp2
import network
import ubinascii
import socket
from umqtt.simple import MQTTClient

# Imports for DHT11
from DHT22 import DHT22
from secrets import secrets


last_message = 0
message_interval = 5
counter = 0

#
# Set country to avoid possible errors / https://randomnerdtutorials.com/micropython-mqtt-esp32-esp8266/
rp2.country('EN')

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
# If you need to disable powersaving mode

# See the MAC address in the wireless chip OTP
mac = ubinascii.hexlify(network.WLAN().config('mac'),':').decode()
print('mac = ' + mac)

# Other things to query
# print(wlan.config('channel'))
# print(wlan.config('essid'))
# print(wlan.config('txpower'))

# Load login data from different file for safety reasons
ssid = secrets['ssid']
pw = secrets['pw']
broker = secrets['broker']
sub_topic = secrets['subtopic']
pub_topic = secrets['pubtopic']
#client_id = ubinascii.hexlify(machine.unique_id())
#client_id = mac
client_id = secrets['client_id']
picow_id = secrets['picow_id']

wlan.connect(ssid, pw)

# Wait for connection with 10 second timeout
timeout = 10
while timeout > 0:
    if wlan.status() < 0 or wlan.status() >= 3:
        break
    timeout -= 1
    print('Waiting for connection...')
    time.sleep(1)
    
# Handle connection error
# Error meanings
# 0  Link Down
# 1  Link Join
# 2  Link NoIp
# 3  Link Up
# -1 Link Fail
# -2 Link NoNet
# -3 Link BadAuth
if wlan.status() != 3:
    raise RuntimeError('Wi-Fi connection failed')
else:
    led = machine.Pin('LED', machine.Pin.OUT)
    for i in range(wlan.status()):
        led.on()
        time.sleep(.1)
        led.off()
    print('Connected')
    status = wlan.ifconfig()
    print('ip = ' + status[0])
    
### Topic Setup ###

def sub_cb(topic, msg):
  print((topic, msg))
  if msg == b'LEDon':
    print('Device received LEDon message on subscribed topic')
    led.value(1)
  if msg == b'LEDoff':
    print('Device received LEDoff message on subscribed topic')
    led.value(0)


def connect_and_subscribe():
  global client_id, mqtt_server, topic_sub
  client = MQTTClient(client_id, broker)
  client.set_callback(sub_cb)
  client.connect()
  client.subscribe(sub_topic)
  print('Connected to %s MQTT broker as client ID: %s, subscribed to %s topic' % (broker, client_id, sub_topic))
  return client

def restart_and_reconnect():
  print('Failed to connect to MQTT broker. Reconnecting...')
  time.sleep(10)
  machine.reset()
  
try:
  client = connect_and_subscribe()
except OSError as e:
  restart_and_reconnect()

# Get the sensor
dht_sensor=DHT22(Pin(15,Pin.IN,Pin.PULL_UP),dht11=True)

while True:
  try:
    client.check_msg()
    print(f"Counter = {counter}")
    if (time.time() - last_message) >= message_interval:
      temp, humidity = dht_sensor.read()
      y, m, d, H, M, S = utime.localtime()[:6]
      timestamp = f"{y}-{m:02d}-{d:02d}T{H:02d}:{M:02d}:{S:02d}"
      if temp is None:
        print(" sensor error")
      #else:
      pub_msg = f'{{"picowId": {picow_id}, "temperature": {temp}, "humidity": {humidity}, "timestamp": {timestamp}}}'
      print(pub_msg)
      #DHT22 not responsive if delay to short
      #utime.sleep_ms(5000)
      
      #pub_msg = b'Hello #%d' % counter
      client.publish(pub_topic, pub_msg)
      last_message = time.time()
      time.sleep(message_interval)
      counter += 1
  except OSError as e:
    restart_and_reconnect()