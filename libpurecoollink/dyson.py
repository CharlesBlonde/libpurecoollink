"""Dyson Pure Cool Link library."""

# pylint: disable=too-many-public-methods,too-many-instance-attributes
# pylint: disable=useless-super-delegation

import base64
import json
import logging
import socket
import time
from queue import Queue, Empty

from threading import Thread
import paho.mqtt.client as mqtt
import requests
from requests.auth import HTTPBasicAuth
from Crypto.Cipher import AES

from .zeroconf import ServiceBrowser, Zeroconf

DEFAULT_PORT = 1883

_LOGGER = logging.getLogger(__name__)

DYSON_API_URL = "api.cp.dyson.com"

DYSON_PURE_COOL_LINK_TOUR = "475"
DYSON_PURE_COOL_LINK_DESK = "469"

MQTT_RETURN_CODES = {
    0: "Connection successful",
    1: "Connection refused - incorrect protocol version",
    2: "Connection refused - invalid client identifier",
    3: "Connection refused - server unavailable",
    4: "Connection refused - bad username or password",
    5: "Connection refused - not authorised"
}


def unpad(string):
    """Un pad string."""
    return string[:-ord(string[len(string) - 1:])]


class DysonAccount:
    """Dyson account."""

    def __init__(self, email, password, country):
        """Create a new Dyson account.

        :param email: User email
        :param password: User password
        :param country: 2 characters language code
        """
        self._email = email
        self._password = password
        self._country = country
        self._logged = False
        self._auth = None

    def login(self):
        """Login to dyson web services."""
        request_body = {
            "Email": self._email,
            "Password": self._password
        }
        login = requests.post(
            "https://{0}/v1/userregistration/authenticate?country={1}".format(
                DYSON_API_URL, self._country), request_body, verify=False)
        # pylint: disable=no-member
        if login.status_code == requests.codes.ok:
            json_response = login.json()
            self._auth = HTTPBasicAuth(json_response["Account"],
                                       json_response["Password"])
            self._logged = True
        else:
            self._logged = False
        return self._logged

    def devices(self):
        """Return all devices linked to the account."""
        if self._logged:
            device_response = requests.get(
                "https://{0}/v1/provisioningservice/manifest".format(
                    DYSON_API_URL), verify=False, auth=self._auth)
            devices = []
            for device in device_response.json():
                dyson_device = DysonPureCoolLink(device)
                devices.append(dyson_device)

            return devices
        else:
            _LOGGER.warning("Not logged to Dyson Web Services.")
            raise DysonNotLoggedException()

    @property
    def logged(self):
        """Return True if user is logged, else False."""
        return self._logged


class NetworkDevice:
    """Network device."""

    def __init__(self, name, address, port):
        """Create a new network device.

        :param name: Device name
        :param address: Device address
        :param port: Device port
        """
        self._name = name
        self._address = address
        self._port = port

    @property
    def name(self):
        """Device name."""
        return self._name

    @property
    def address(self):
        """Device address."""
        return self._address

    @property
    def port(self):
        """Device port."""
        return self._port

    def __repr__(self):
        """Return a String representation."""
        fields = [self.name, self.address, str(self.port)]
        return 'NetworkDevice(' + ",".join(fields) + ')'


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


class DysonPureCoolLink:
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
        self._active = json_body['Active']
        self._serial = json_body['Serial']
        self._name = json_body['Name']
        self._version = json_body['Version']
        self._credentials = self._decrypt_password(
            json_body['LocalCredentials'])
        self._auto_update = json_body['AutoUpdate']
        self._new_version_available = json_body['NewVersionAvailable']
        self._product_type = json_body['ProductType']
        self._network_device = None
        self._search_device_queue = Queue()
        self._connection_queue = Queue()
        self._state_data_available = Queue()
        self._sensor_data_available = Queue()
        self._device_available = False
        self._mqtt = None
        self._callback_message = []
        self._connected = False
        self._current_state = None
        self._environmental_state = None
        self._request_thread = None

    def _add_network_device(self, network_device):
        """Add network device.

        :param network_device: Network device
        """
        self._search_device_queue.put_nowait(network_device)

    @staticmethod
    def on_connect(client, userdata, flags, return_code):
        # pylint: disable=unused-argument
        """Set function callback when connected."""
        if return_code == 0:
            _LOGGER.debug("Connected with result code: %s", return_code)
            client.subscribe(
                "{0}/{1}/status/current".format(userdata.product_type,
                                                userdata.serial))

            userdata.connection_callback(True)
        else:
            _LOGGER.error("Connection error: %s",
                          MQTT_RETURN_CODES[return_code])
            userdata.connection_callback(False)

    @staticmethod
    def on_message(client, userdata, msg):
        # pylint: disable=unused-argument
        """Set function Callback when message received."""
        payload = msg.payload.decode("utf-8")
        if DysonState.is_state_message(payload):
            device_msg = DysonState(payload)
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

    @staticmethod
    def _decrypt_password(encrypted_password):
        """Decrypt password.

        :param encrypted_password: Encrypted password
        """
        key = b'\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\x0c\r\x0e\x0f\x10' \
              b'\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f '
        init_vector = b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' \
                      b'\x00\x00\x00\x00'
        cipher = AES.new(key, AES.MODE_CBC, init_vector)
        json_password = json.loads(unpad(
            cipher.decrypt(base64.b64decode(encrypted_password)).decode(
                'utf-8')))
        return json_password["apPasswordHash"]

    def connect(self, on_message=None, device_ip=None, timeout=5, retry=15):
        """Try to connect to device.

        If device_ip is provided, mDNS discovery step will be skipped.

        :param on_message: On Message callback function
        :param device_ip: Device IP address
        :param timeout: Timeout
        :param retry: Max retry
        """
        if device_ip is None:
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
        else:
            self._network_device = NetworkDevice(self._name, device_ip,
                                                 DEFAULT_PORT)

        if on_message:
            self._callback_message.append(on_message)
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

    def state_data_available(self):
        """Call when first state data are available. Internal method."""
        _LOGGER.debug("State data available for device %s", self._serial)
        self._state_data_available.put_nowait(True)

    def sensor_data_available(self):
        """Call when first sensor data are available. Internal method."""
        _LOGGER.debug("Sensor data available for device %s", self._serial)
        self._sensor_data_available.put_nowait(True)

    @property
    def device_available(self):
        """Return True if device is fully available, else false."""
        return self._device_available

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

    def request_current_state(self):
        """Request new state message."""
        if self._connected:
            payload = {
                "msg": "REQUEST-CURRENT-STATE",
                "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }
            self._mqtt.publish(
                self._product_type + "/" + self._serial + "/command",
                json.dumps(payload))
        else:
            _LOGGER.warning(
                "Unable to send commands because device %s is not connected",
                self.serial)

    def set_fan_configuration(self, fan_mode, oscillation, fan_speed,
                              night_mode, quality_target, standby_monitoring,
                              sleep_timer):
        # pylint: disable=too-many-arguments,too-many-locals
        """Configure Fan.

        :param fan_mode: Fan mode (const.FanMode)
        :param oscillation: Oscillation mode (const.Oscillation)
        :param fan_speed: Fan Speed (const.FanSpeed)
        :param night_mode: Night Mode (const.NightMode)
        :param quality_target: Air Quality target (const.QualityTarget)
        :param standby_monitoring: Monitor when on standby
                                   (const.StandbyMonitoring)
        :param sleep_timer: Sleep timer in minutes, 0 to cancel (Integer)
        """
        if self._connected:
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

            payload = {
                "msg": "STATE-SET",
                "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "mode-reason": "LAPP",
                "data": {
                    "fmod": f_mode,
                    "fnsp": f_speed,
                    "oson": f_oscillation,
                    "sltm": f_sleep_timer,  # sleep timer
                    "rhtm": f_standby_monitoring,  # monitor air quality
                                                   # when inactive
                    "rstf": "STET",  # ??,
                    "qtar": f_quality_target,
                    "nmod": f_night_mode
                }
            }
            self._mqtt.publish(
                self._product_type + "/" + self._serial + "/command",
                json.dumps(payload), 1)
        else:
            _LOGGER.warning(
                "Unable to send commands because device %s is not connected",
                self.serial)

    def set_configuration(self, **kwargs):
        """Configure fan.

        :param kwargs: Parameters
        """
        fan_mode = kwargs.get('fan_mode')
        oscillation = kwargs.get('oscillation')
        fan_speed = kwargs.get('fan_speed')
        night_mode = kwargs.get('night_mode')
        quality_target = kwargs.get('quality_target')
        standby_monitoring = kwargs.get('standby_monitoring')
        sleep_timer = kwargs.get('sleep_timer')

        self.set_fan_configuration(fan_mode, oscillation, fan_speed,
                                   night_mode, quality_target,
                                   standby_monitoring, sleep_timer)

    @property
    def active(self):
        """Active status."""
        return self._active

    @property
    def serial(self):
        """Device serial."""
        return self._serial

    @property
    def name(self):
        """Device name."""
        return self._name

    @property
    def version(self):
        """Device version."""
        return self._version

    @property
    def credentials(self):
        """Device encrypted credentials."""
        return self._credentials

    @property
    def auto_update(self):
        """Auto update configuration."""
        return self._auto_update

    @property
    def new_version_available(self):
        """Return if new version available."""
        return self._new_version_available

    @property
    def product_type(self):
        """Product type."""
        return self._product_type

    @property
    def network_device(self):
        """Network device."""
        return self._network_device

    @property
    def state(self):
        """Device state."""
        return self._current_state

    @state.setter
    def state(self, value):
        """Set current state."""
        self._current_state = value

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

    @property
    def callback_message(self):
        """Return callback functions when message are received."""
        return self._callback_message

    def add_message_listener(self, callback_message):
        """Add message listener."""
        self._callback_message.append(callback_message)

    def remove_message_listener(self, callback_message):
        """Remove a message listener."""
        if callback_message in self._callback_message:
            self.callback_message.remove(callback_message)

    def clear_message_listener(self):
        """Clear all message listener."""
        self.callback_message.clear()

    def connection_callback(self, connected):
        """Set function called when device is connected."""
        self._connection_queue.put_nowait(connected)

    def __repr__(self):
        """Return a String representation."""
        fields = [self.serial, str(self.active), self.name, self.version,
                  str(self.auto_update), str(self.new_version_available),
                  self.product_type, str(self.network_device)]
        return 'DysonDevice(' + ",".join(fields) + ')'


class DysonState:
    """Dyson device state."""

    @staticmethod
    def is_state_message(payload):
        """Return true if this message is a state message."""
        json_message = json.loads(payload)
        return json_message['msg'] in ["CURRENT-STATE", "STATE-CHANGE"]

    @staticmethod
    def __get_field_value(state, field):
        """Get field value."""
        return state[field][1] if isinstance(state[field], list) else state[
            field]

    def __init__(self, payload):
        """Create a new state.

        :param payload: Message payload
        """
        json_message = json.loads(payload)
        state = json_message['product-state']
        self._fan_mode = self.__get_field_value(state, 'fmod')
        self._fan_state = self.__get_field_value(state, 'fnst')
        self._night_mode = self.__get_field_value(state, 'nmod')
        self._speed = self.__get_field_value(state, 'fnsp')
        self._oscilation = self.__get_field_value(state, 'oson')
        self._filter_life = self.__get_field_value(state, 'filf')
        self._quality_target = self.__get_field_value(state, 'qtar')
        self._standby_monitoring = self.__get_field_value(state, 'rhtm')

    @property
    def fan_mode(self):
        """Fan mode."""
        return self._fan_mode

    @property
    def fan_state(self):
        """Fan state."""
        return self._fan_state

    @property
    def night_mode(self):
        """Night mode."""
        return self._night_mode

    @property
    def speed(self):
        """Fan speed."""
        return self._speed

    @property
    def oscillation(self):
        """Oscillation mode."""
        return self._oscilation

    @property
    def filter_life(self):
        """Filter life."""
        return self._filter_life

    @property
    def quality_target(self):
        """Air quality target."""
        return self._quality_target

    @property
    def standby_monitoring(self):
        """Monitor when inactive (standby)."""
        return self._standby_monitoring

    def __repr__(self):
        """Return a String representation."""
        fields = [self.fan_mode, self.fan_state, self.night_mode, self.speed,
                  self.oscillation, self.filter_life, self.quality_target,
                  self.standby_monitoring]
        return 'DysonState(' + ",".join(fields) + ')'


class DysonEnvironmentalSensorState:
    """Environmental sensor state."""

    @staticmethod
    def is_environmental_state_message(payload):
        """Return true if this message is a state message."""
        json_message = json.loads(payload)
        return json_message['msg'] in ["ENVIRONMENTAL-CURRENT-SENSOR-DATA"]

    @staticmethod
    def __get_field_value(state, field):
        """Get field value."""
        return state[field][1] if isinstance(state[field], list) else state[
            field]

    def __init__(self, payload):
        """Create a new Environmental sensor state.

        :param payload: Message payload
        """
        json_message = json.loads(payload)
        data = json_message['data']
        self._humidity = int(self.__get_field_value(data, 'hact'))
        volatil_copounds = self.__get_field_value(data, 'vact')
        self._volatil_compounds = 0 if volatil_copounds == 'INIT' else int(
            volatil_copounds)
        self._temperature = float(self.__get_field_value(data, 'tact'))/10
        self._dust = int(self.__get_field_value(data, 'pact'))
        sltm = self.__get_field_value(data, 'sltm')
        self._sleep_timer = 0 if sltm == 'OFF' else int(sltm)

    @property
    def humidity(self):
        """Humidity in percent."""
        return self._humidity

    @property
    def volatil_organic_compounds(self):
        """Volatil organic compounds level."""
        return self._volatil_compounds

    @property
    def temperature(self):
        """Temperature in Kelvin."""
        return self._temperature

    @property
    def dust(self):
        """Dust level."""
        return self._dust

    @property
    def sleep_timer(self):
        """Sleep timer."""
        return self._sleep_timer

    def __repr__(self):
        """Return a String representation."""
        fields = [str(self.humidity), str(self.volatil_organic_compounds),
                  str(self.temperature), str(self.dust),
                  str(self._sleep_timer)]
        return 'DysonEnvironmentalSensorState(' + ",".join(fields) + ')'


class DysonNotLoggedException(Exception):
    """Not logged to Dyson Web Services Exception."""

    def __init__(self):
        """Dyson Not Logged Exception."""
        super(DysonNotLoggedException, self).__init__()
