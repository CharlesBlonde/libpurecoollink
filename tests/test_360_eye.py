import unittest

from unittest import mock
from unittest.mock import Mock
import json

from libpurecoollink.dyson_360_eye import Dyson360Eye, NetworkDevice, \
    Dyson360EyeState, Dyson360EyeMapGlobal, Dyson360EyeMapData, \
    Dyson360EyeMapGrid, Dyson360EyeTelemetryData, Dyson360Goodbye
from libpurecoollink.const import PowerMode, Dyson360EyeMode


def _mocked_request_state(*args, **kwargs):
    assert args[0] == 'N223/device-id-1/command'
    msg = json.loads(args[1])
    assert msg['msg'] in ['REQUEST-CURRENT-STATE']
    assert msg['time']


def _mocked_send_start_command(*args, **kwargs):
    assert args[0] == 'N223/device-id-1/command'
    msg = json.loads(args[1])
    assert msg['msg'] in ['START']
    assert msg['time']


class TestDysonEye360Device(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    @staticmethod
    def _device_sample():
        return Dyson360Eye({
            "Active": True,
            "Serial": "device-id-1",
            "Name": "device-1",
            "ScaleUnit": "SU01",
            "Version": "11.3.5.10",
            "LocalCredentials": "1/aJ5t52WvAfn+z+fjDuef86kQDQPefbQ6/70ZGysII1K"
                                "e1i0ZHakFH84DZuxsSQ4KTT2vbCm7uYeTORULKLKQ==",
            "AutoUpdate": True,
            "NewVersionAvailable": False,
            "ProductType": "N223"
        })

    def test_status_topic(self):
        device = self._device_sample()
        self.assertEqual(device.status_topic, "N223/device-id-1/status")

    @mock.patch('paho.mqtt.client.Client.publish',
                side_effect=_mocked_request_state)
    @mock.patch('paho.mqtt.client.Client.connect')
    def test_request_state(self, mocked_connect, mocked_publish):
        device = self._device_sample()
        network_device = NetworkDevice('device-1', 'host', 1883)
        device.connection_callback(True)
        device._add_network_device(network_device)
        device.state_data_available()
        connected = device.connect('192.168.1.1')
        self.assertTrue(connected)
        self.assertEqual(mocked_connect.call_count, 1)
        mocked_connect.assert_called_with('192.168.1.1', 1883)
        self.assertEqual(mocked_publish.call_count, 1)
        device.request_current_state()
        self.assertEqual(mocked_publish.call_count, 2)
        self.assertEqual(device.__repr__(), "Dyson360Eye(serial=device-id-1,"
                                            "active=True,name=device-1,"
                                            "version=11.3.5.10,"
                                            "auto_update=True,"
                                            "new_version_available=False,"
                                            "product_type=N223,"
                                            "network_device=NetworkDevice("
                                            "name=device-1,"
                                            "address=192.168.1.1,port=1883))")

    def test_start_not_connected(self):
        self._called = False

        def publish(topic, data, qos):
            self._called = True

        device = self._device_sample()
        device._connected = False
        device._mqtt = Mock()
        device._mqtt.publish = publish
        device.start()
        self.assertFalse(self._called)

    def test_start(self):
        self._parameters = None

        def publish(topic, data, qos):
            self._parameters = (topic, data, qos)

        device = self._device_sample()
        device._connected = True
        device._mqtt = Mock()
        device._mqtt.publish = publish
        device.start()
        self.assertEqual(self._parameters[0], "N223/device-id-1/command")
        self.assertEqual(json.loads(self._parameters[1])["msg"], "START")
        self.assertEqual(json.loads(self._parameters[1])["fullCleanType"],
                         "immediate")
        self.assertEqual(self._parameters[2], 1)

    def test_pause(self):
        self._parameters = None

        def publish(topic, data, qos):
            self._parameters = (topic, data, qos)

        device = self._device_sample()
        device._connected = True
        device._mqtt = Mock()
        device._mqtt.publish = publish
        device.pause()
        self.assertEqual(self._parameters[0], "N223/device-id-1/command")
        self.assertEqual(json.loads(self._parameters[1])["msg"], "PAUSE")
        self.assertTrue("fullCleanType" not in json.loads(self._parameters[1]))
        self.assertEqual(self._parameters[2], 1)

    def test_resume(self):
        self._parameters = None

        def publish(topic, data, qos):
            self._parameters = (topic, data, qos)

        device = self._device_sample()
        device._connected = True
        device._mqtt = Mock()
        device._mqtt.publish = publish
        device.resume()
        self.assertEqual(self._parameters[0], "N223/device-id-1/command")
        self.assertEqual(json.loads(self._parameters[1])["msg"], "RESUME")
        self.assertTrue("fullCleanType" not in json.loads(self._parameters[1]))
        self.assertEqual(self._parameters[2], 1)

    def test_abort(self):
        self._parameters = None

        def publish(topic, data, qos):
            self._parameters = (topic, data, qos)

        device = self._device_sample()
        device._connected = True
        device._mqtt = Mock()
        device._mqtt.publish = publish
        device.abort()
        self.assertEqual(self._parameters[0], "N223/device-id-1/command")
        self.assertEqual(json.loads(self._parameters[1])["msg"], "ABORT")
        self.assertTrue("fullCleanType" not in json.loads(self._parameters[1]))
        self.assertEqual(self._parameters[2], 1)

    def test_set_power_mode(self):
        self._parameters = None

        def publish(topic, data, qos):
            self._parameters = (topic, data, qos)

        device = self._device_sample()
        device._connected = True
        device._mqtt = Mock()
        device._mqtt.publish = publish
        device.set_power_mode(PowerMode.MAX)
        self.assertEqual(self._parameters[0], "N223/device-id-1/command")
        self.assertEqual(json.loads(self._parameters[1])["msg"], "STATE-SET")
        self.assertEqual(
            json.loads(self._parameters[1])["data"]["defaultVacuumPowerMode"],
            "fullPower")
        self.assertTrue("fullCleanType" not in json.loads(self._parameters[1]))
        self.assertEqual(self._parameters[2], 1)

        device.set_power_mode(PowerMode.QUIET)
        self.assertEqual(self._parameters[0], "N223/device-id-1/command")
        self.assertEqual(json.loads(self._parameters[1])["msg"], "STATE-SET")
        self.assertEqual(
            json.loads(self._parameters[1])["data"]["defaultVacuumPowerMode"],
            "halfPower")
        self.assertTrue("fullCleanType" not in json.loads(self._parameters[1]))
        self.assertEqual(self._parameters[2], 1)

    def test_on_unknown_message(self):
        def callback_function(msg):
            assert False

        device = self._device_sample()
        device._connected = True
        message = Mock()
        message.payload = Mock()
        message.payload.decode.return_value = '{"msg":"nothing"}'
        device.add_message_listener(callback_function)
        Dyson360Eye.on_message(None, device, message)

    def test_on_state_message(self):
        self.message = None

        def callback_function(msg):
            self.message = msg

        state_message = open("tests/data/vacuum/state.json", "r").read()
        device = self._device_sample()
        device._connected = True
        message = Mock()
        message.payload = Mock()
        message.payload.decode.return_value = state_message
        device.add_message_listener(callback_function)
        Dyson360Eye.on_message(None, device, message)
        self.assertTrue(isinstance(self.message, Dyson360EyeState))
        self.assertEqual(self.message.clean_id,
                         "0d000000-4a47-3845-5548-454131323334")
        self.assertEqual(self.message.state, Dyson360EyeMode.INACTIVE_CHARGED)
        self.assertEqual(self.message.full_clean_type, "")
        self.assertEqual(self.message.position, (6, 37))
        self.assertEqual(self.message.power_mode, PowerMode.QUIET)
        self.assertEqual(self.message.battery_level, 100)
        self.assertEqual(self.message.__repr__(),
                         "Dyson360EyeState("
                         "state=Dyson360EyeMode.INACTIVE_CHARGED,"
                         "clean_id=0d000000-4a47-3845-5548-454131323334,"
                         "full_clean_type=,power_mode=PowerMode.QUIET,"
                         "battery_level=100,position=(6, 37))")

    def test_on_state_unknown_values_message(self):
        self.message = None

        def callback_function(msg):
            self.message = msg

        state_message = open("tests/data/vacuum/state-unknown-values.json",
                             "r").read()
        device = self._device_sample()
        device._connected = True
        message = Mock()
        message.payload = Mock()
        message.payload.decode.return_value = state_message
        device.add_message_listener(callback_function)
        Dyson360Eye.on_message(None, device, message)
        self.assertTrue(isinstance(self.message, Dyson360EyeState))
        self.assertEqual(self.message.clean_id,
                         "0d000000-4a47-3845-5548-454131323334")
        self.assertEqual(self.message.state, "UNKNOWN")
        self.assertEqual(self.message.full_clean_type, "")
        self.assertEqual(self.message.position, (6, 37))
        self.assertEqual(self.message.power_mode, "unknown")
        self.assertEqual(self.message.battery_level, 100)
        self.assertEqual(self.message.__repr__(),
                         "Dyson360EyeState(state=UNKNOWN,"
                         "clean_id=0d000000-4a47-3845-5548-454131323334,"
                         "full_clean_type=,power_mode=unknown,"
                         "battery_level=100,position=(6, 37))")

    def test_on_state_change_message(self):
        self.message = None

        def callback_function(msg):
            self.message = msg

        state_message = open("tests/data/vacuum/state-change.json", "r").read()
        device = self._device_sample()
        device._connected = True
        message = Mock()
        message.payload = Mock()
        message.payload.decode.return_value = state_message
        device.add_message_listener(callback_function)
        Dyson360Eye.on_message(None, device, message)
        self.assertTrue(isinstance(self.message, Dyson360EyeState))
        self.assertEqual(self.message.clean_id,
                         "0e000000-4a47-3845-5548-454131323334")
        self.assertEqual(self.message.state,
                         Dyson360EyeMode.FULL_CLEAN_INITIATED)
        self.assertEqual(self.message.full_clean_type, "immediate")
        self.assertEqual(self.message.position, (6, 37))
        self.assertEqual(self.message.power_mode, PowerMode.QUIET)
        self.assertEqual(self.message.battery_level, 95)
        self.assertEqual(self.message.__repr__(),
                         "Dyson360EyeState("
                         "state=Dyson360EyeMode.FULL_CLEAN_INITIATED,"
                         "clean_id=0e000000-4a47-3845-5548-454131323334,"
                         "full_clean_type=immediate,"
                         "power_mode=PowerMode.QUIET,"
                         "battery_level=95,position=(6, 37))")

    def test_on_map_global_message(self):
        self.message = None

        def callback_function(msg):
            self.message = msg

        state_message = open("tests/data/vacuum/map-global.json", "r").read()
        device = self._device_sample()
        device._connected = True
        message = Mock()
        message.payload = Mock()
        message.payload.decode.return_value = state_message
        device.add_message_listener(callback_function)
        Dyson360Eye.on_message(None, device, message)
        self.assertTrue(isinstance(self.message, Dyson360EyeMapGlobal))
        self.assertEqual(self.message.clean_id,
                         "0e000000-4a47-3845-5548-454131323334")
        self.assertEqual(self.message.grid_id, "1")
        self.assertEqual(self.message.position_x, 0)
        self.assertEqual(self.message.position_y, 0)
        self.assertEqual(self.message.angle, -180)
        self.assertEqual(self.message.time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                         "2017-07-16T07:31:35Z")
        self.assertEqual(self.message.__repr__(),
                         "Dyson360EyeMapGlobal(grid_id=1,"
                         "clean_id=0e000000-4a47-3845-5548-454131323334,"
                         "x=0,y=0,angle=-180,time=2017-07-16 07:31:35)")

    def test_on_map_grid_message(self):
        self.message = None

        def callback_function(msg):
            self.message = msg

        state_message = open("tests/data/vacuum/map-grid.json", "r").read()
        device = self._device_sample()
        device._connected = True
        message = Mock()
        message.payload = Mock()
        message.payload.decode.return_value = state_message
        device.add_message_listener(callback_function)
        Dyson360Eye.on_message(None, device, message)
        self.assertTrue(isinstance(self.message, Dyson360EyeMapGrid))
        self.assertEqual(self.message.clean_id,
                         "0e000000-4a47-3845-5548-454131323334")
        self.assertEqual(self.message.grid_id, "1")
        self.assertEqual(self.message.resolution, 43)
        self.assertEqual(self.message.width, 144)
        self.assertEqual(self.message.height, 144)
        self.assertEqual(self.message.anchor, (16, 72))
        self.assertEqual(self.message.time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                         "2017-07-16T07:34:31Z")
        self.assertEqual(self.message.__repr__(),
                         "Dyson360EyeMapGrid(grid_id=1,"
                         "clean_id=0e000000-4a47-3845-5548-454131323334,"
                         "resolution=43,width=144,height=144,"
                         "anchor=(16, 72),time=2017-07-16 07:34:31)")

    def test_on_map_data_message(self):
        self.message = None

        def callback_function(msg):
            self.message = msg

        state_message = open("tests/data/vacuum/map-data.json", "r").read()
        device = self._device_sample()
        device._connected = True
        message = Mock()
        message.payload = Mock()
        message.payload.decode.return_value = state_message
        device.add_message_listener(callback_function)
        Dyson360Eye.on_message(None, device, message)
        self.assertTrue(isinstance(self.message, Dyson360EyeMapData))
        self.assertEqual(self.message.clean_id,
                         "0e000000-4a47-3845-5548-454131323334")
        self.assertEqual(self.message.grid_id, "1")
        self.assertEqual(self.message.content_type, "application/json")
        self.assertEqual(self.message.content_encoding, "gzip")
        self.assertEqual(self.message.content, "xxx")
        self.assertEqual(self.message.time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                         "2017-07-16T07:34:00Z")
        self.assertEqual(self.message.__repr__(),
                         "Dyson360EyeMapData(grid_id=1,"
                         "clean_id=0e000000-4a47-3845-5548-454131323334,"
                         "content_type=application/json,content_encoding=gzip,"
                         "content=xxx,time=2017-07-16 07:34:00)")

    def test_on_telemetry_data_message(self):
        self.message = None

        def callback_function(msg):
            self.message = msg

        state_message = open("tests/data/vacuum/telemetry-data.json",
                             "r").read()
        device = self._device_sample()
        device._connected = True
        message = Mock()
        message.payload = Mock()
        message.payload.decode.return_value = state_message
        device.add_message_listener(callback_function)
        Dyson360Eye.on_message(None, device, message)
        self.assertTrue(isinstance(self.message, Dyson360EyeTelemetryData))
        self.assertEqual(self.message.field1, "1.0.0")
        self.assertEqual(self.message.field2, "2.000000")
        self.assertEqual(self.message.field3, "")
        self.assertEqual(self.message.field4,
                         "0e000000-4a47-3845-5548-454131323334")
        self.assertEqual(self.message.telemetry_data_id, "40010000")
        self.assertEqual(self.message.time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                         "2017-07-16T07:34:34Z")
        self.assertEqual(self.message.__repr__(),
                         "Dyson360EyeTelemetryData("
                         "telemetry_data_id=40010000,field1=1.0.0,"
                         "field2=2.000000,field3=,"
                         "field4=0e000000-4a47-3845-5548-454131323334,"
                         "time=2017-07-16 07:34:34)")

    def test_on_goodbye_message(self):
        self.message = None

        def callback_function(msg):
            self.message = msg

        state_message = open("tests/data/vacuum/goodbye.json", "r").read()
        device = self._device_sample()
        device._connected = True
        message = Mock()
        message.payload = Mock()
        message.payload.decode.return_value = state_message
        device.add_message_listener(callback_function)
        Dyson360Eye.on_message(None, device, message)
        self.assertTrue(isinstance(self.message, Dyson360Goodbye))
        self.assertEqual(self.message.reason, "UNKNOWN")
        self.assertEqual(self.message.time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                         "2017-07-30T16:00:13Z")
        self.assertEqual(self.message.__repr__(),
                         "Dyson360EyeGoodbye(reason=UNKNOWN,"
                         "time=2017-07-30 16:00:13)")
