.. Libpurecoollink documentation master file, created by
   sphinx-quickstart on Sun Jun 18 08:28:58 2017.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Libpurecoollink's documentation
===============================

.. image:: https://api.travis-ci.org/CharlesBlonde/libpurecoollink.svg?branch=master
    :target: https://travis-ci.org/CharlesBlonde/libpurecoollink

.. image:: https://coveralls.io/repos/github/CharlesBlonde/libpurecoollink/badge.svg?branch=master
    :target: https://coveralls.io/github/CharlesBlonde/libpurecoollink?branch=master

.. image:: https://img.shields.io/pypi/v/libpurecoollink.svg
    :target: https://pypi.python.org/pypi/libpurecoollink

This Python 3.4+ library allow you to control `Dyson fan/purifier devices <http://www.dyson.com/air-treatment/purifiers/dyson-pure-hot-cool-link.aspx>`_ and `Dyson 360 Eye robot vacuum device <http://www.dyson.com/vacuum-cleaners/robot/dyson-360-eye.aspx>`_.

Status
------

Backward compatibility is a goal but breaking changes can still happen.

Discovery is not fully reliable yet. It's working most of the time but sometimes discovery will not work. Manual configuration is available to bypass this limitation.

Supported devices
~~~~~~~~~~~~~~~~~

-  Dyson pure cool link devices (Tower and Desk)
-  Dyson Cool+Hot devices
-  Dyson 360 Eye robot vacuum

Features
--------

Commands
~~~~~~~~

The following commands are supported:

- Purifier/fan devices

  -  Connect to the device using discovery or manually with IP Address
  -  Turn on/off
  -  Set speed
  -  Turn on/off oscillation
  -  Set Auto mode
  -  Set night mode
  -  Set sleep timer
  -  Set Air Quality target (Normal, High, Better)
  -  Enable/disable standby monitoring (the device continue to update sensors when in standby)
  -  Reset filter life

- Cool+Hot purifier/fan devices

  -  Set heat mode
  -  Set heat target
  -  Set fan focus mode

- 360 Eye device

  - Set power mode (Quiet/Max)
  - Start cleaning
  - Pause cleaning
  - Resume cleaning
  - Abort cleaning

Sensors
~~~~~~~

The following sensors are available for fan/purifier devices:

-  Humidity
-  Temperature in Kelvin
-  Dust (unknown metric)
-  Air Quality (unknown metric)

Usage
-----

Installation
~~~~~~~~~~~~

.. code:: shell

    pip install libpurecoollink


Dyson account
~~~~~~~~~~~~~

In order to access the devices, you need to have access to a valid Dyson account.

.. code:: python

    from libpurecoollink.dyson import DysonAccount

    # Log to Dyson account
    # Language is a two characters code (eg: FR)
    dyson_account = DysonAccount("<dyson_account_email>","<dyson_account_password>","<language>")
    logged = dyson_account.login()

Fan/Purifier devices
~~~~~~~~~~~~~~~~~~~~

Connect to devices
##################

After login to the Dyson account, known devices are available.

Connections to the devices can been done automatically using mDNS or manually with specifying IP address

Automatic connection (mDNS)
+++++++++++++++++++++++++++

.. code:: python

    from libpurecoollink.dyson import DysonAccount

    # Log to Dyson account
    # Language is a two characters code (eg: FR)
    dyson_account = DysonAccount("<dyson_account_email>","<dyson_account_password>","<language>")
    logged = dyson_account.login()

    if not logged:
        print('Unable to login to Dyson account')
        exit(1)

    # List devices available on the Dyson account
    devices = dyson_account.devices()

    # Connect using discovery to the first device
    connected = devices[0].auto_connect()

    # connected == device available, state values are available, sensor values are available

Manual connection
+++++++++++++++++

.. code:: python

    from libpurecoollink.dyson import DysonAccount

    # Log to Dyson account
    # Language is a two characters code (eg: FR)
    dyson_account = DysonAccount("<dyson_account_email>","<dyson_account_password>","<language>")
    logged = dyson_account.login()

    if not logged:
        print('Unable to login to Dyson account')
        exit(1)

    # List devices available on the Dyson account
    devices = dyson_account.devices()

    # Connect using discovery to the first device
    connected = devices[0].connect("192.168.1.2")

    # connected == device available, state values are available, sensor values are available

Disconnect from the device
##########################

Disconnection is required for fan/purifier devices in order to release resources (an internal thread is started to request update notifications)

.. code:: python

    from libpurecoollink.dyson import DysonAccount

    # ... connection do dyson account and to device ... #

    # Disconnect
    devices[0].disconnect()

Send commands
#############

After connected to the device, commands cand be send in order to update the device configuration

.. code:: python

    from libpurecoollink.dyson import DysonAccount
    from libpurecoollink.const import FanSpeed, FanMode, NightMode, Oscillation, \
        FanState, StandbyMonitoring, QualityTarget, ResetFilter, HeatMode, \
        FocusMode, HeatTarget

    # ... connection do dyson account and to device ... #

    # Turn on the fan to speed 2
    devices[0].set_configuration(fan_mode=FanMode.FAN, fan_speed=FanSpeed.FAN_SPEED_2)

    # Turn on oscillation
    devices[0].set_configuration(oscillation=Oscillation.OSCILLATION_ON)

    # Turn on night mode
    devices[0].set_configuration(night_mode=NightMode.NIGHT_MODE_ON)

    # Set 10 minutes sleep timer
    devices[0].set_configuration(sleep_timer=10)

    # Disable sleep timer
    devices[0].set_configuration(sleep_timer=0)

    # Set quality target (for auto mode)
    devices[0].set_configuration(quality_target=QualityTarget.QUALITY_NORMAL)

    # Disable standby monitoring
    devices[0].set_configuration(standby_monitoring=StandbyMonitoring.STANDBY_MONITORING_OFF)

    # Reset filter life
    devices[0].set_configuration(reset_filter=ResetFilter.RESET_FILTER)

    ## Cool+Hot devices only
    # Set Heat mode
    devices[0].set_configuration(heat_mode=HeatMode.HEAT_ON)
    # Set heat target
    devices[0].set_configuration(heat_target=HeatTarget.celsius(25))
    devices[0].set_configuration(heat_target=HeatTarget.fahrenheit(70))
    # Set fan focus mode
    devices[0].set_configuration(focus_mode=FocusMode.FOCUS_ON)

    # Everything can be mixed in one call
    devices[0].set_configuration(sleep_timer=10,
        fan_mode=FanMode.FAN,
        fan_speed=FanSpeed.FAN_SPEED_5,
        night_mode=NightMode.NIGHT_MODE_OFF,
        standby_monitoring=StandbyMonitoring.STANDBY_MONITORING_ON,
        quality_target=QualityTarget.QUALITY_HIGH)

States and sensors
##################

States and sensors values are available using *state* and *environment_state* properties

States values

.. code:: python

    # ... imports ... #

    # ... connection do dyson account and to device ... #

    print(devices[0].state.speed)
    print(devices[0].state.oscillation)
    # ... #

Environmental values

.. code:: python

    # ... imports ... #

    # ... connection do dyson account and to device ... #

    print(devices[0].environment_state.humidity)
    print(devices[0].environment_state.sleep_timer)
    # ... #

All properties are available in the sources.

Notifications
#############

You can register to any values changed by using a callback function

.. code:: python

    # ... imports ... #
    from libpurecoollink.dyson_pure_state import DysonPureHotCoolState, \
      DysonPureCoolState, DysonEnvironmentalSensorState

    # ... connection do dyson account and to device ... #
    def on_message(msg):
        # Message received
        if isinstance(msg, DysonPureCoolState):
            # Will be true for DysonPureHotCoolState too.
            print("DysonPureCoolState message received")
        if isinstance(msg, DysonPureHotCoolState):
            print("DysonPureHotCoolState message received")
        if isinstance(msg, DysonEnvironmentalSensorState)
            print("DysonEnvironmentalSensorState received")
        print(msg)

    devices[0].connect()
    devices[0].add_message_listener(on_message)

360 Eye robot vacuum
~~~~~~~~~~~~~~~~~~~~

Connect to devices
##################

After login to the Dyson account, known devices are available.

Auto discovery is not yet supported.

Manual connection
+++++++++++++++++

.. code:: python

    from libpurecoollink.dyson import DysonAccount

    # Log to Dyson account
    # Language is a two characters code (eg: FR)
    dyson_account = DysonAccount("<dyson_account_email>","<dyson_account_password>","<language>")
    logged = dyson_account.login()

    if not logged:
        print('Unable to login to Dyson account')
        exit(1)

    # List devices available on the Dyson account
    devices = dyson_account.devices()

    # Connect using discovery to the first device
    connected = devices[0].connect("192.168.1.2")

    # connected == device available, state values are available, sensor values are available

Send commands
#############

After connected to the device, commands cand be send in order to update the device configuration.

.. code:: python

    import time
    from libpurecoollink.dyson import DysonAccount
    from libpurecoollink.const import PowerMode

    # ... connection do dyson account and to device ... #

    # Set power mode
    devices[0].set_power_mode(PowerMode.QUIET)
    devices[0].set_power_mode(PowerMode.MAX)

    # Start cleaning
    devices[0].start

    time.sleep(30)

    # Pause cleaning
    devices[0].pause()

    time.sleep(30)

    # Resume cleaning
    devices[0].resume()

    time.sleep(30)

    # Abort cleaning (device return to the base)
    devices[0].abort()

States
######

State values are available using *state* property.

.. code:: python

    # ... imports ... #

    # ... connection do dyson account and to device ... #

    print(devices[0].state.state)
    print(devices[0].state.full_clean_type)
    print(devices[0].state.position)
    print(devices[0].state.power_mode)
    print(devices[0].state.battery_level)
    print(devices[0].state.clean_id)
    # ... #

All properties are available in the sources.

Notifications
#############

You can register to any values changed by using a callback function

.. code:: python

    # ... imports ... #
    from libpurecoollink.dyson_360_eye import Dyson360EyeState, \
      Dyson360EyeTelemetryData, Dyson360EyeMapData, Dyson360EyeMapGrid, \
      Dyson360EyeMapGlobal

    # ... connection do dyson account and to device ... #
    def on_message(msg):
        # Message received
        if isinstance(msg, Dyson360EyeState):
            print("Dyson360EyeState message received")
        if isinstance(msg, Dyson360EyeTelemetryData)
            print("Dyson360EyeTelemetryData received")
        if isinstance(msg, Dyson360EyeMapData)
            print("Dyson360EyeMapData received")
        if isinstance(msg, Dyson360EyeMapGrid)
            print("Dyson360EyeMapGrid received")
        if isinstance(msg, Dyson360EyeMapGlobal)
            print("Dyson360EyeMapGlobal received")
        print(msg)

    devices[0].connect()
    devices[0].add_message_listener(on_message)

API Documentation
-----------------

If you are looking for information on a specific function, class, or method,
this part of the documentation is for you.

.. toctree::
    api

How it's working
----------------
Dyson devices use many different protocols in order to work:

-  HTTPS to Dyson API in order to get devices informations (credentials, historical data, etc ...)
-  MDNS to discover devices on the local network
-  MQTT (with auth) to get device status and send commands

To my knowledge, no public technical information about API/MQTT are available so all the work is done by testing and a lot of properties are unknown to me at this time.

This library come with a modified version of `Zeroconf <https://github.com/jstasiak/python-zeroconf>`_ because Dyson MDNS implementation is not valid.

This `documentation <https://github.com/shadowwa/Dyson-MQTT2RRD>`_ help me to understand some of return values.

Work to do
----------

-  Better protocol understanding
-  Better technical documentation on how it is working
-  Get historical data from the API (air quality, etc ...)

Releases
--------

.. toctree::
    versions

Contributors
------------

.. include:: ../AUTHORS.rst
