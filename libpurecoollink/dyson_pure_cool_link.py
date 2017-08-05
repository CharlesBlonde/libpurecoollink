"""Dyson pure cool link device."""

# pylint: disable=too-many-locals

import json
import logging
import time
import socket
from threading import Thread
from queue import Queue, Empty


import paho.mqtt.client as mqtt

from .dyson_device import DysonDevice, NetworkDevice, DEFAULT_PORT
from .utils import printable_fields, support_heating
from .dyson_pure_state import DysonPureHotCoolState, DysonPureCoolState, \
    DysonEnvironmentalSensorState
from .zeroconf import ServiceBrowser, Zeroconf

_LOGGER = logging.getLogger(__name__)


class DysonPureCoolLink(DysonDevice):
    """Dyson device (fan)."""

    class DysonDeviceListener(object):
        """Message listener."""

        def __init__(self, serial, add_device_function):
            """Create a new message listener.

            :param serial: Device serial
            :param add_device_function: Callback function
            """
            self._serial = serial
            self.add_device_function = add_device_function

        def remove_service(self, zeroconf, device_type, name):
            # pylint: disable=unused-argument,no-self-use
            """Remove listener."""
            _LOGGER.info("Service %s removed", name)

        def add_service(self, zeroconf, device_type, name):
            """Add device.

            :param zeroconf: MSDNS object
            :param device_type: Service type
            :param name: Device name
            """
            device_serial = (name.split(".")[0]).split("_")[1]
            if device_serial == self._serial:
                # Find searched device
                info = zeroconf.get_service_info(device_type, name)
                address = socket.inet_ntoa(info.address)
                network_device = NetworkDevice(device_serial, address,
                                               info.port)
                self.add_device_function(network_device)
                zeroconf.close()

    def __init__(self, json_body):
        """Create a new Pure Cool Link device.

        :param json_body: JSON message returned by the HTTPS API
        """
        super().__init__(json_body)

        self._sensor_data_available = Queue()
        self._environmental_state = None
        self._request_thread = None

    @property
    def status_topic(self):
        """MQTT status topic."""
        return "{0}/{1}/status/current".format(self.product_type,
                                               self.serial)

    @staticmethod
    def on_message(client, userdata, msg):
        # pylint: disable=unused-argument
        """Set function Callback when message received."""
        payload = msg.payload.decode("utf-8")
        if DysonPureCoolState.is_state_message(payload):
            if support_heating(userdata.product_type):
                device_msg = DysonPureHotCoolState(payload)
            else:
                device_msg = DysonPureCoolState(payload)
            if not userdata.device_available:
                userdata.state_data_available()
            userdata.state = device_msg
            for function in userdata.callback_message:
                function(device_msg)
        elif DysonEnvironmentalSensorState.is_environmental_state_message(
                payload):
            device_msg = DysonEnvironmentalSensorState(payload)
            if not userdata.device_available:
                userdata.sensor_data_available()
            userdata.environmental_state = device_msg
            for function in userdata.callback_message:
                function(device_msg)
        else:
            _LOGGER.warning("Unknown message: %s", payload)

    def auto_connect(self, timeout=5, retry=15):
        """Try to connect to device using mDNS.

        :param timeout: Timeout
        :param retry: Max retry
        :return: True if connected, else False
        """
        for i in range(retry):
            zeroconf = Zeroconf()
            listener = self.DysonDeviceListener(self._serial,
                                                self._add_network_device)
            ServiceBrowser(zeroconf, "_dyson_mqtt._tcp.local.", listener)
            try:
                self._network_device = self._search_device_queue.get(
                    timeout=timeout)
            except Empty:
                # Unable to find device
                _LOGGER.warning("Unable to find device %s, try %s",
                                self._serial, i)
                zeroconf.close()
            else:
                break
        if self._network_device is None:
            _LOGGER.error("Unable to connect to device %s", self._serial)
            return False
        return self._mqtt_connect()

    def connect(self, device_ip, device_port=DEFAULT_PORT):
        """Connect to the device using ip address.

        :param device_ip: Device IP address
        :param device_port: Device Port (default: 1883)
        :return: True if connected, else False
        """
        self._network_device = NetworkDevice(self._name, device_ip,
                                             device_port)

        return self._mqtt_connect()

    def _mqtt_connect(self):
        """Connect to the MQTT broker."""
        self._mqtt = mqtt.Client(userdata=self)
        self._mqtt.on_message = self.on_message
        self._mqtt.on_connect = self.on_connect
        self._mqtt.username_pw_set(self._serial, self._credentials)
        self._mqtt.connect(self._network_device.address,
                           self._network_device.port)
        self._mqtt.loop_start()
        self._connected = self._connection_queue.get(timeout=10)
        if self._connected:
            self.request_current_state()
            # Start Environmental thread
            self._request_thread = EnvironmentalSensorThread(
                self.request_environmental_state)
            self._request_thread.start()

            # Wait for first data
            self._state_data_available.get()
            self._sensor_data_available.get()
            self._device_available = True
        else:
            self._mqtt.loop_stop()
        return self._connected

    def sensor_data_available(self):
        """Call when first sensor data are available. Internal method."""
        _LOGGER.debug("Sensor data available for device %s", self._serial)
        self._sensor_data_available.put_nowait(True)

    def disconnect(self):
        """Disconnect from the device."""
        self._request_thread.stop()
        self._connected = False

    def request_environmental_state(self):
        """Request new state message."""
        if self._connected:
            payload = {
                "msg": "REQUEST-PRODUCT-ENVIRONMENT-CURRENT-SENSOR-DATA",
                "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }
            self._mqtt.publish(
                self._product_type + "/" + self._serial + "/command",
                json.dumps(payload))
        else:
            _LOGGER.warning(
                "Unable to send commands because device %s is not connected",
                self.serial)

    def set_fan_configuration(self, data):
        # pylint: disable=too-many-arguments,too-many-locals
        """Configure Fan.

        :param data: Data to send
        """
        if self._connected:
            payload = {
                "msg": "STATE-SET",
                "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "mode-reason": "LAPP",
                "data": data
            }
            self._mqtt.publish(self.command_topic, json.dumps(payload), 1)
        else:
            _LOGGER.warning("Not connected, can not set configuration: %s",
                            self.serial)

    def _parse_command_args(self, **kwargs):
        """Parse command arguments.

        :param kwargs Arguments
        :return payload dictionary
        """
        fan_mode = kwargs.get('fan_mode')
        oscillation = kwargs.get('oscillation')
        fan_speed = kwargs.get('fan_speed')
        night_mode = kwargs.get('night_mode')
        quality_target = kwargs.get('quality_target')
        standby_monitoring = kwargs.get('standby_monitoring')
        sleep_timer = kwargs.get('sleep_timer')
        reset_filter = kwargs.get('reset_filter')

        f_mode = fan_mode.value if fan_mode \
            else self._current_state.fan_mode
        f_speed = fan_speed.value if fan_speed \
            else self._current_state.speed
        f_oscillation = oscillation.value if oscillation \
            else self._current_state.oscillation
        f_night_mode = night_mode.value if night_mode \
            else self._current_state.night_mode
        f_quality_target = quality_target.value if quality_target \
            else self._current_state.quality_target
        f_standby_monitoring = standby_monitoring.value if \
            standby_monitoring else self._current_state.standby_monitoring
        f_sleep_timer = sleep_timer if sleep_timer or isinstance(
            sleep_timer, int) else "STET"
        f_reset_filter = reset_filter.value if reset_filter \
            else "STET"

        return {
            "fmod": f_mode,
            "fnsp": f_speed,
            "oson": f_oscillation,
            "sltm": f_sleep_timer,  # sleep timer
            "rhtm": f_standby_monitoring,  # monitor air quality
            # when inactive
            "rstf": f_reset_filter,  # reset filter lifecycle
            "qtar": f_quality_target,
            "nmod": f_night_mode
        }

    def set_configuration(self, **kwargs):
        """Configure fan.

        :param kwargs: Parameters
        """
        data = self._parse_command_args(**kwargs)
        self.set_fan_configuration(data)

    @property
    def environmental_state(self):
        """Environmental Device state."""
        return self._environmental_state

    @environmental_state.setter
    def environmental_state(self, value):
        """Set Environmental Device state."""
        self._environmental_state = value

    @property
    def connected(self):
        """Device connected."""
        return self._connected

    @connected.setter
    def connected(self, value):
        """Set device connected."""
        self._connected = value

    def __repr__(self):
        """Return a String representation."""
        fields = self._fields()
        return 'DysonPureCoolLink(' + ",".join(printable_fields(fields)) + ')'


class EnvironmentalSensorThread(Thread):
    """Environmental Sensor thread.

    The device don't send environmental data if not asked.
    """

    def __init__(self, request_data_method, interval=30):
        """Create new Environmental Sensor thread."""
        Thread.__init__(self)
        self._interval = interval
        self._request_data_method = request_data_method
        self._stop_queue = Queue()

    def stop(self):
        """Stop the thread."""
        self._stop_queue.put_nowait(True)

    def run(self):
        """Start Refresh sensor state thread."""
        stopped = False
        while not stopped:
            self._request_data_method()
            try:
                stopped = self._stop_queue.get(timeout=self._interval)
            except Empty:
                # Thread has not been stopped
                pass
