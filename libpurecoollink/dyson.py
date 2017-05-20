"""Dyson Pure Cool Link library."""

# pylint: disable=too-many-public-methods,too-many-instance-attributes

import base64
import json
import logging
import socket
import time
from queue import Queue, Empty

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
        request_body = {
            "Email": email,
            "Password": password
        }
        login = requests.post(
            "https://{0}/v1/userregistration/authenticate?country={1}".format(
                DYSON_API_URL, country), request_body, verify=False)
        # pylint: disable=no-member
        if login.status_code == requests.codes.ok:
            json_response = login.json()
            self._auth = HTTPBasicAuth(json_response["Account"],
                                       json_response["Password"])
            self._logged = True
        else:
            self._logged = False

    def devices(self):
        """Return all devices linked to the account."""
        device_response = requests.get(
            "https://{0}/v1/provisioningservice/manifest".format(
                DYSON_API_URL), verify=False, auth=self._auth)
        devices = []
        for device in device_response.json():
            dyson_device = DysonPureCoolLink(device)
            devices.append(dyson_device)

        return devices

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
        self._mqtt = None
        self._callback_message = []
        self._connected = False
        self._current_state = None

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
            userdata.state = device_msg
            for function in userdata.callback_message:
                function(device_msg)

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
        else:
            self._mqtt.loop_stop()

        return self._connected

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
                              night_mode):
        """Configure Fan.

        :param fan_mode: Fan mode (const.FanMode)
        :param oscillation: Oscillation mode (const.Oscillation)
        :param fan_speed: Fan Speed (const.FanSpeed)
        :param night_mode: Night Mode (const.NightMode)
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
            payload = {
                "msg": "STATE-SET",
                "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "mode-reason": "LAPP",
                "data": {
                    "fmod": f_mode,
                    "fnsp": f_speed,
                    "oson": f_oscillation,
                    "sltm": "STET",  # ??
                    "rhtm": self._current_state.rhtm,  # ??
                    "rstf": "STET",  # ??,
                    "qtar": self._current_state.qtar,  # ??
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

        self.set_fan_configuration(fan_mode, oscillation, fan_speed,
                                   night_mode)

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
        """Return treu if this message is a state message."""
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
        self._qtar = self.__get_field_value(state, 'qtar')
        self._rhtm = self.__get_field_value(state, 'rhtm')

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
    def qtar(self):
        """Unknown property."""
        return self._qtar

    @property
    def rhtm(self):
        """Unknown property."""
        return self._rhtm

    def __repr__(self):
        """Return a String representation."""
        fields = [self.fan_mode, self.fan_state, self.night_mode, self.speed,
                  self.oscillation, self.filter_life, self.qtar, self.rhtm]
        return 'DysonState(' + ",".join(fields) + ')'
