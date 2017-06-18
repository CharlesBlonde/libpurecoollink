# Dyson Pure Cool Link Python library

[![Build Status](https://travis-ci.org/CharlesBlonde/libpurecoollink.svg?branch=master)](https://travis-ci.org/CharlesBlonde/libpurecoollink) [![Coverage Status](https://coveralls.io/repos/github/CharlesBlonde/libpurecoollink/badge.svg?branch=master)](https://coveralls.io/github/CharlesBlonde/libpurecoollink?branch=master)

This *work in progress* library is a tentative to be able to use [Dyson fan/purifier devices](http://www.dyson.com/air-treatment/purifiers/dyson-pure-hot-cool-link.aspx) from Python 3.4+.

## Status

This library is becoming quite stable and I'll do my best to keep backward compatibility.

### Devices supported

Dyson pure cool link devices (Tower and Desk)

### Devices not tested

Air Purifier Heater and fan

## Features

The following feature are supported:

* Connect to the device using discovery or manually with IP Address
* Turn on/off
* Set speed
* Turn on/off oscillation
* Set Auto mode
* Set night mode
* Set sleep timer
* Set Air Quality target (Normal, High, Better)
* Enable/disable standby monitoring (the device continue to update sensors when in standby)

The following sensors are available:

* Humidity
* Temperature in Kelvin
* Dust (unknown metric)
* Volatil organic compounds (unknown metric)

## Quick start

Install the library

```shell
pip install libpurecoollink
``` 

```python

from libpurecoollink.dyson import DysonAccount
from libpurecoollink.const import FanSpeed, FanMode, NightMode, Oscillation, FanState
from pprint import pprint
import time

# Callback function for each state/environment message
def on_message(message):
    # Print device state
    pprint(message)

# Log to Dyson account
dyson_account = DysonAccount("<dyson_account_email>","<dyson_account_password>","<language>")
connected = dyson_account.login()
# Language is a two characters code (eg: FR)

# List devices
devices = dyson_account.devices()

for device in devices:
  # Print device information
  pprint(device)
  
  # Connect to the device with discovery
  connected = device.connect(on_message)
  
  # Print network information
  pprint(device.network_device)
    
  time.sleep(2)
  
  # Set fan in auto mode, with night mode enable and oscillation disable
  device.set_configuration(fan_mode=FanMode.AUTO, 
    night_mode=NightMode.NIGHT_MODE_ON, 
    oscillation=Oscillation.OSCILLATION_OFF)
  
  # Set fan in fan mode, night mode off, speed 4 and oscillation enable
  device.set_configuration(fan_mode=FanMode.FAN, 
    night_mode=NightMode.NIGHT_MODE_OFF, 
    oscillation=Oscillation.OSCILLATION_ON,
    fan_speed=FanSpeed.FAN_SPEED_4)
    
  # Set sleep timer to 5 minutes
  device.set_configuration(sleep_timer=5)
   
  # Disable sleep timer
  device.set_configuration(sleep_timer=0)

# Wait to see status update
time.sleep(10000)
```

## How it's work

Dyson devices use many different protocols in order to work:

* HTTPS to Dyson API in order to get devices informations (credentials, historical data, etc ...)
* MDNS to discover devices on the local network
* MQTT (with auth) to get device status and send commands

To my knowledge, no public technical information about API/MQTT are available so all the work is done by testing and a lot of properties are unknown to me at this time.

This library come with a modified version of [Zeroconf](https://github.com/jstasiak/python-zeroconf) because Dyson MDNS implementation is not valid.

This [documentation](https://github.com/shadowwa/Dyson-MQTT2RRD) help me to understand some of return values.

## Work to do

* Better protocol understanding
* Better documentation on how it is working
* Get historical data from the API (air quality, etc ...)
* Air Purifier Heater and fan support
