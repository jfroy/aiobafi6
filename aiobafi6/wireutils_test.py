import unittest
from aiobafi6 import wireutils


class TestWireUtils(unittest.TestCase):
    def test_remove_emulation_prevention(self):
        buf = b"\xdb\xdc"
        got = wireutils.remove_emulation_prevention(buf)
        self.assertEqual(got, b"\xc0")
        buf = b"\xdb\xdd"
        got = wireutils.remove_emulation_prevention(buf)
        self.assertEqual(got, b"\xdb")
        buf = b'\x12+")\x12\r\n\x0bLiving Room\x12\x04\x18\xdb\xdc\xbe\x01\x12\x03\xb0\x08\x00\x12\x03\xb8\x08\x00\x12\x03\xdb\xdc\x08\x01\x12\x03\xb0\t\x00'
        got = wireutils.remove_emulation_prevention(buf)
        self.assertEqual(got, b'\x12+")\x12\r\n\x0bLiving Room\x12\x04\x18\xc0\xbe\x01\x12\x03\xb0\x08\x00\x12\x03\xb8\x08\x00\x12\x03\xc0\x08\x01\x12\x03\xb0\t\x00')


if __name__ == "__main__":
    unittest.main()
