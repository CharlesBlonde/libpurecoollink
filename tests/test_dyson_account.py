import unittest

from unittest import mock

from libpurecoollink.dyson import DysonAccount, DysonPureCoolLink, \
    DysonPureHotCoolLink, Dyson360Eye, DysonNotLoggedException


class MockResponse:
    def __init__(self, json, status_code=200):
        self._json = json
        self.status_code = status_code

    def json(self, **kwargs):
        return self._json


def _mocked_login_post_failed(*args, **kwargs):
    url = 'https://{0}{1}?{2}={3}'.format('api.cp.dyson.com',
                                          '/v1/userregistration/authenticate',
                                          'country',
                                          'language')
    payload = {'Password': 'password', 'Email': 'email'}
    if args[0] == url and args[1] == payload:
        return MockResponse({
            'Account': 'account',
            'Password': 'password'
        }, 401)
    else:
        raise Exception("Unknown call")


def _mocked_login_post(*args, **kwargs):
    url = 'https://{0}{1}?{2}={3}'.format('api.cp.dyson.com',
                                          '/v1/userregistration/authenticate',
                                          'country',
                                          'language')
    payload = {'Password': 'password', 'Email': 'email'}
    if args[0] == url and args[1] == payload:
        return MockResponse({
            'Account': 'account',
            'Password': 'password'
        })
    else:
        raise Exception("Unknown call")


def _mocked_list_devices(*args, **kwargs):
    url = 'https://{0}{1}'.format('api.cp.dyson.com',
                                  '/v1/provisioningservice/manifest')
    if args[0] == url:
        return MockResponse(
            [
                {
                    "Active": True,
                    "Serial": "device-id-1",
                    "Name": "device-1",
                    "ScaleUnit": "SU01",
                    "Version": "21.03.08",
                    "LocalCredentials": "1/aJ5t52WvAfn+z+fjDuef86kQDQPefbQ6/"
                                        "70ZGysII1Ke1i0ZHakFH84DZuxsSQ4KTT2v"
                                        "bCm7uYeTORULKLKQ==",
                    "AutoUpdate": True,
                    "NewVersionAvailable": False,
                    "ProductType": "475"
                },
                {
                    "Active": False,
                    "Serial": "device-id-2",
                    "Name": "device-2",
                    "ScaleUnit": "SU02",
                    "Version": "21.02.04",
                    "LocalCredentials": "1/aJ5t52WvAfn+z+fjDuebkH6aWl2H5Q1vCq"
                                        "CQSjJfENzMefozxWaDoW1yDluPsi09SGT5nW"
                                        "MxqxtrfkxnUtRQ==",
                    "AutoUpdate": False,
                    "NewVersionAvailable": True,
                    "ProductType": "455"
                },
                {
                    "Active": True,
                    "Serial": "device-id-3",
                    "Name": "device-3",
                    "ScaleUnit": "SU01",
                    "Version": "21.03.08",
                    "LocalCredentials": "1/aJ5t52WvAfn+z+fjDuef86kQDQPefbQ6/"
                                        "70ZGysII1Ke1i0ZHakFH84DZuxsSQ4KTT2v"
                                        "bCm7uYeTORULKLKQ==",
                    "AutoUpdate": True,
                    "NewVersionAvailable": False,
                    "ProductType": "N223"
                }
            ]
        )


class TestDysonAccount(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    @mock.patch('requests.post', side_effect=_mocked_login_post)
    def test_connect_account(self, mocked_login):
        dyson_account = DysonAccount("email", "password", "language")
        logged = dyson_account.login()
        self.assertEqual(mocked_login.call_count, 1)
        self.assertTrue(logged)

    @mock.patch('requests.post', side_effect=_mocked_login_post_failed)
    def test_connect_account_failed(self, mocked_login):
        dyson_account = DysonAccount("email", "password", "language")
        logged = dyson_account.login()
        self.assertEqual(mocked_login.call_count, 1)
        self.assertFalse(logged)

    def test_not_logged(self):
        dyson_account = DysonAccount("email", "password", "language")
        self.assertRaises(DysonNotLoggedException, dyson_account.devices)

    @mock.patch('requests.get', side_effect=_mocked_list_devices)
    @mock.patch('requests.post', side_effect=_mocked_login_post)
    def test_list_devices(self, mocked_login, mocked_list_devices):
        dyson_account = DysonAccount("email", "password", "language")
        dyson_account.login()
        self.assertEqual(mocked_login.call_count, 1)
        self.assertTrue(dyson_account.logged)
        devices = dyson_account.devices()
        self.assertEqual(mocked_list_devices.call_count, 1)
        self.assertEqual(len(devices), 3)
        self.assertTrue(isinstance(devices[0], DysonPureCoolLink))
        self.assertTrue(isinstance(devices[1], DysonPureHotCoolLink))
        self.assertTrue(isinstance(devices[2], Dyson360Eye))
        self.assertTrue(devices[0].active)
        self.assertTrue(devices[0].auto_update)
        self.assertFalse(devices[0].new_version_available)
        self.assertEqual(devices[0].serial, 'device-id-1')
        self.assertEqual(devices[0].name, 'device-1')
        self.assertEqual(devices[0].version, '21.03.08')
        self.assertEqual(devices[0].product_type, '475')
        self.assertEqual(devices[0].credentials, 'password1')
