"""Dyson 360 eye device."""

import logging
import json
import time
import datetime

import paho.mqtt.client as mqtt

from .dyson_device import DysonDevice, NetworkDevice, DEFAULT_PORT
from .utils import printable_fields
from .const import PowerMode, Dyson360EyeMode, Dyson360EyeCommand

_LOGGER = logging.getLogger(__name__)


class Dyson360Eye(DysonDevice):
    """Dyson 360 Eye device."""

    def connect(self, device_ip, device_port=DEFAULT_PORT):
        """Try to connect to device.

        :param device_ip: Device IP address
        :param device_port: Device Port (default: 1883)
        :return: True if connected, else False
        """
        self._network_device = NetworkDevice(self._name, device_ip,
                                             device_port)

        self._mqtt = mqtt.Client(userdata=self, protocol=3)
        self._mqtt.username_pw_set(self._serial, self._credentials)
        self._mqtt.on_message = self.on_message
        self._mqtt.on_connect = self.on_connect
        self._mqtt.connect(self._network_device.address,
                           self._network_device.port)
        self._mqtt.loop_start()
        if self._connection_queue.get(timeout=10):
            self._connected = True
            _LOGGER.info("Connected to device %s", self.serial)
            self.request_current_state()

            # Wait for first data
            self._state_data_available.get()
            self._device_available = True
        else:
            self._mqtt.loop_stop()

        return self._device_available

    @property
    def status_topic(self):
        """MQTT status topic."""
        return "{0}/{1}/status".format(self.product_type, self.serial)

    def _send_command(self, command, data=None):
        """Send command to the device.

        :param command Command to send (const.Dyson360EyeCommand)
        :param data Data dictionary to send. Can be empty
        """
        if data is None:
            data = {}
        if self._connected:
            payload = {
                "msg": "{0}".format(command),
                "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            payload.update(data)
            _LOGGER.debug("Sending command to the device: %s",
                          json.dumps(payload))
            self._mqtt.publish(self.command_topic, json.dumps(payload), 1)
        else:
            _LOGGER.warning(
                "Not connected, can not send commands: %s",
                self.serial)

    def set_power_mode(self, power_mode):
        """Set power mode.

        :param power_mode Power mode (const.PowerMode)
        """
        self._send_command(Dyson360EyeCommand.STATE_SET.value, {
            "data": {"defaultVacuumPowerMode": power_mode.value}})

    def start(self):
        """Start cleaning."""
        self._send_command(Dyson360EyeCommand.START.value,
                           {"fullCleanType": "immediate"})

    def pause(self):
        """Pause cleaning."""
        self._send_command(Dyson360EyeCommand.PAUSE.value)

    def resume(self):
        """Resume cleaning."""
        self._send_command(Dyson360EyeCommand.RESUME.value)

    def abort(self):
        """Abort cleaning."""
        self._send_command(Dyson360EyeCommand.ABORT.value)

    @staticmethod
    def call_callback_functions(functions, message):
        """Call callback functions."""
        for func in functions:
            func(message)

    @staticmethod
    def on_message(client, userdata, msg):
        # pylint: disable=unused-argument
        """Set function Callback when message received."""
        payload = msg.payload.decode("utf-8")
        device_msg = None
        if Dyson360EyeState.is_state_message(payload):
            device_msg = Dyson360EyeState(payload)
            if not userdata.device_available:
                userdata.state_data_available()
            userdata.state = device_msg
        elif Dyson360EyeMapGlobal.is_map_global(payload):
            device_msg = Dyson360EyeMapGlobal(payload)
        elif Dyson360EyeTelemetryData.is_telemetry_data(payload):
            device_msg = Dyson360EyeTelemetryData(payload)
        elif Dyson360EyeMapGrid.is_map_grid(payload):
            device_msg = Dyson360EyeMapGrid(payload)
        elif Dyson360EyeMapData.is_map_data(payload):
            device_msg = Dyson360EyeMapData(payload)
        elif Dyson360Goodbye.is_goodbye_message(payload):
            device_msg = Dyson360Goodbye(payload)
        else:
            _LOGGER.warning(payload)

        if device_msg:
            Dyson360Eye.call_callback_functions(userdata.callback_message,
                                                device_msg)

    def __repr__(self):
        """Return a String representation."""
        fields = self._fields()
        return 'Dyson360Eye(' + ",".join(printable_fields(fields)) + ')'


class Dyson360EyeState:
    """Dyson 360 Eye state."""

    @staticmethod
    def is_state_message(payload):
        """Return true if this message is a Dyson 360 Eye state message."""
        return json.loads(payload)['msg'] in ["CURRENT-STATE", "STATE-CHANGE"]

    def __init__(self, json_body):
        """Create a new Dyson 360 Eye state."""
        data = json.loads(json_body)
        try:
            self._state = Dyson360EyeMode(
                data["state"] if "state" in data else data["newstate"])
        except ValueError:
            _LOGGER.error("Unknown state value %s",
                          data["state"] if "state" in data else data[
                              "newstate"])
            self._state = data["state"] if "state" in data else data[
                "newstate"]

        self._full_clean_type = data["fullCleanType"]
        if "globalPosition" in data and len(data["globalPosition"]) == 2:
            self._position = (int(data["globalPosition"][0]),
                              int(data["globalPosition"][1]))
        try:
            self._power_mode = PowerMode(data["currentVacuumPowerMode"])
        except ValueError:
            _LOGGER.error("Unknown power mode value %s",
                          data["currentVacuumPowerMode"])
            self._power_mode = data["currentVacuumPowerMode"]
        self._clean_id = data["cleanId"]
        self._battery_level = int(data["batteryChargeLevel"])

    @property
    def state(self):
        """Return state status."""
        return self._state

    @property
    def full_clean_type(self):
        """Return full clean type."""
        return self._full_clean_type

    @property
    def position(self):
        """Return position."""
        return self._position

    @property
    def power_mode(self):
        """Return power mode."""
        return self._power_mode

    @property
    def battery_level(self):
        """Return battery level."""
        return self._battery_level

    @property
    def clean_id(self):
        """Return clean id."""
        return self._clean_id

    def __repr__(self):
        """Return a String representation."""
        fields = [("state", str(self.state)),
                  ("clean_id", str(self.clean_id)),
                  ("full_clean_type", str(self.full_clean_type)),
                  ("power_mode", str(self.power_mode)),
                  ("battery_level", str(self.battery_level)),
                  ("position", str(self.position))]
        return 'Dyson360EyeState(' + ",".join(printable_fields(fields)) + ')'


class Dyson360EyeTelemetryData:
    """Dyson 360 Eye Telemetry Data."""

    @staticmethod
    def is_telemetry_data(payload):
        """Return true if this message is a telemetry data message."""
        json_message = json.loads(payload)
        return json_message['msg'] in ["TELEMETRY-DATA"]

    def __init__(self, json_body):
        """Create a new Telemetry Data."""
        data = json.loads(json_body)
        self._telemetry_data_id = data["id"]
        self._field1 = data["field1"]
        self._field2 = data["field2"]
        self._field3 = data["field3"]
        self._field4 = data["field4"]
        self._time = datetime.datetime.strptime(data["time"],
                                                "%Y-%m-%dT%H:%M:%SZ")

    @property
    def telemetry_data_id(self):
        """Return Telemetry data id."""
        return self._telemetry_data_id

    @property
    def field1(self):
        """Return field 1."""
        return self._field1

    @property
    def field2(self):
        """Return field 2."""
        return self._field2

    @property
    def field3(self):
        """Return field 3."""
        return self._field3

    @property
    def field4(self):
        """Return field 4."""
        return self._field4

    @property
    def time(self):
        """Return time."""
        return self._time

    def __repr__(self):
        """Return a String representation."""
        fields = [("telemetry_data_id", str(self.telemetry_data_id)),
                  ("field1", str(self.field1)),
                  ("field2", str(self.field2)),
                  ("field3", str(self.field3)),
                  ("field4", str(self.field4)),
                  ("time", str(self.time))]
        return 'Dyson360EyeTelemetryData(' + ",".join(
            printable_fields(fields)) + ')'


class Dyson360EyeMapData:
    """Dyson 360 Eye map data."""

    @staticmethod
    def is_map_data(payload):
        """Return true if this message is a map data message."""
        json_message = json.loads(payload)
        return json_message['msg'] in ["MAP-DATA"]

    def __init__(self, json_body):
        """Create a new Map Data."""
        data = json.loads(json_body)
        self._grid_id = data["gridID"]
        self._clean_id = data["cleanId"]
        self._content_type = data["data"]["content-type"]
        self._content_encoding = data["data"]["content-encoding"]
        self._content = data["data"]["content"]
        self._time = datetime.datetime.strptime(data["time"],
                                                "%Y-%m-%dT%H:%M:%SZ")

    @property
    def grid_id(self):
        """Return Grid id."""
        return self._grid_id

    @property
    def clean_id(self):
        """Return Clean Id."""
        return self._clean_id

    @property
    def content_type(self):
        """Return content type."""
        return self._content_type

    @property
    def content_encoding(self):
        """Return content encoding."""
        return self._content_encoding

    @property
    def content(self):
        """Return content."""
        return self._content

    @property
    def time(self):
        """Return time."""
        return self._time

    def __repr__(self):
        """Return a String representation."""
        fields = [("grid_id", str(self.grid_id)),
                  ("clean_id", str(self.clean_id)),
                  ("content_type", str(self.content_type)),
                  ("content_encoding", str(self.content_encoding)),
                  ("content", str(self.content)),
                  ("time", str(self.time))]
        return 'Dyson360EyeMapData(' + ",".join(printable_fields(fields)) + ')'


class Dyson360EyeMapGrid:
    """Dyson 360 Eye map grid."""

    @staticmethod
    def is_map_grid(payload):
        """Return true if this message is a map grid message."""
        json_message = json.loads(payload)
        return json_message['msg'] in ["MAP-GRID"]

    def __init__(self, json_body):
        """Create a new Map Grid."""
        data = json.loads(json_body)
        self._grid_id = data["gridID"]
        self._resolution = data["resolution"]
        self._width = data["width"]
        self._height = data["height"]
        self._clean_id = data["cleanId"]
        if "anchor" in data and len(data["anchor"]) == 2:
            self._anchor = (int(data["anchor"][0]), int(data["anchor"][1]))
        self._time = datetime.datetime.strptime(data["time"],
                                                "%Y-%m-%dT%H:%M:%SZ")

    @property
    def grid_id(self):
        """Return grid id."""
        return self._grid_id

    @property
    def clean_id(self):
        """Return clean id."""
        return self._clean_id

    @property
    def resolution(self):
        """Return resolution."""
        return self._resolution

    @property
    def width(self):
        """Return width."""
        return self._width

    @property
    def height(self):
        """Return height."""
        return self._height

    @property
    def anchor(self):
        """Return Anchor."""
        return self._anchor

    @property
    def time(self):
        """Return time."""
        return self._time

    def __repr__(self):
        """Return a String representation."""
        fields = [("grid_id", str(self.grid_id)),
                  ("clean_id", str(self.clean_id)),
                  ("resolution", str(self.resolution)),
                  ("width", str(self.width)),
                  ("height", str(self.height)),
                  ("anchor", str(self.anchor)),
                  ("time", str(self.time))]
        return 'Dyson360EyeMapGrid(' + ",".join(printable_fields(fields)) + ')'


class Dyson360EyeMapGlobal:
    """Dyson 360Eye map global."""

    @staticmethod
    def is_map_global(payload):
        """Return true if this message is a map global message."""
        json_message = json.loads(payload)
        return json_message['msg'] in ["MAP-GLOBAL"]

    def __init__(self, json_body):
        """Create a new Map Global."""
        data = json.loads(json_body)
        self._grid_id = data["gridID"]
        self._x = data["x"]
        self._y = data["y"]
        self._angle = data["angle"]
        self._clean_id = data["cleanId"]
        self._time = datetime.datetime.strptime(data["time"],
                                                "%Y-%m-%dT%H:%M:%SZ")

    @property
    def grid_id(self):
        """Return grid id."""
        return self._grid_id

    @property
    def clean_id(self):
        """Return clean id."""
        return self._clean_id

    @property
    def position_x(self):
        """Return x."""
        return self._x

    @property
    def position_y(self):
        """Return y."""
        return self._y

    @property
    def angle(self):
        """Return angle."""
        return self._angle

    @property
    def time(self):
        """Return time."""
        return self._time

    def __repr__(self):
        """Return a String representation."""
        fields = [("grid_id", str(self.grid_id)),
                  ("clean_id", str(self.clean_id)),
                  ("x", str(self.position_x)),
                  ("y", str(self.position_y)),
                  ("angle", str(self.angle)),
                  ("time", str(self.time))]
        return 'Dyson360EyeMapGlobal(' + ",".join(
            printable_fields(fields)) + ')'


class Dyson360Goodbye:
    """Dyson 360 Eye goodbye message."""

    @staticmethod
    def is_goodbye_message(payload):
        """Return true if this message is a goodbye message."""
        json_message = json.loads(payload)
        return json_message['msg'] in ["GOODBYE"]

    def __init__(self, json_body):
        """Create a new Map Global."""
        data = json.loads(json_body)
        self._reason = data["reason"]
        self._time = datetime.datetime.strptime(data["time"],
                                                "%Y-%m-%dT%H:%M:%SZ")

    @property
    def reason(self):
        """Return reason."""
        return self._reason

    @property
    def time(self):
        """Return time."""
        return self._time

    def __repr__(self):
        """Return a String representation."""
        fields = [("reason", str(self.reason)),
                  ("time", str(self.time))]
        return 'Dyson360EyeGoodbye(' + ",".join(printable_fields(fields)) + ')'
