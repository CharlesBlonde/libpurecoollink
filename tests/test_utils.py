import unittest

from libpurecoollink.utils import support_heating, is_heating_device, \
    is_360_eye_device, printable_fields, decrypt_password


class TestUtils(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_support_heating(self):
        self.assertTrue(support_heating("455"))
        self.assertFalse(support_heating("469"))

    def test_is_heating_device(self):
        self.assertTrue(is_heating_device({"ProductType": "455"}))
        self.assertFalse(is_heating_device({"ProductType": "469"}))

    def test_is_360_eye_device(self):
        self.assertTrue(is_360_eye_device({"ProductType": "N223"}))
        self.assertFalse(is_360_eye_device({"ProductType": "455"}))

    def test_printable_fields(self):
        idx = 0
        fields = ["field1=value1", "field2=value2"]
        for field in printable_fields(
                [("field1", "value1"), ("field2", "value2")]):
            self.assertEqual(field, fields[idx])
            idx += 1

    def test_decrypt_password(self):
        password = decrypt_password("1/aJ5t52WvAfn+z+fjDuef86kQDQPefbQ6/70"
                                    "ZGysII1Ke1i0ZHakFH84DZuxsSQ4KTT2vbCm7"
                                    "uYeTORULKLKQ==")
        self.assertEqual(password, "password1")
