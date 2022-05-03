import unittest

from aiobafi6 import wireutils


class TestWireUtils(unittest.TestCase):
    def test_add_emulation_prevention(self):
        got = wireutils.add_emulation_prevention(b"\xc0")
        self.assertEqual(got, b"\xdb\xdc")
        got = wireutils.add_emulation_prevention(b"\xdb")
        self.assertEqual(got, b"\xdb\xdd")
        got = wireutils.add_emulation_prevention(
            b'\x12+")\x12\r\n\x0bLiving Room\x12\x04\x18\xc0\xbe\x01\x12\x03\xb0\x08\x00\x12\x03\xb8\x08\x00\x12\x03\xc0\x08\x01\x12\x03\xb0\t\x00'
        )
        self.assertEqual(
            got,
            b'\x12+")\x12\r\n\x0bLiving Room\x12\x04\x18\xdb\xdc\xbe\x01\x12\x03\xb0\x08\x00\x12\x03\xb8\x08\x00\x12\x03\xdb\xdc\x08\x01\x12\x03\xb0\t\x00',
        )

    def test_remove_emulation_prevention(self):
        got = wireutils.remove_emulation_prevention(b"\xdb\xdc")
        self.assertEqual(got, b"\xc0")
        got = wireutils.remove_emulation_prevention(b"\xdb\xdd")
        self.assertEqual(got, b"\xdb")
        got = wireutils.remove_emulation_prevention(
            b'\x12+")\x12\r\n\x0bLiving Room\x12\x04\x18\xdb\xdc\xbe\x01\x12\x03\xb0\x08\x00\x12\x03\xb8\x08\x00\x12\x03\xdb\xdc\x08\x01\x12\x03\xb0\t\x00'
        )
        self.assertEqual(
            got,
            b'\x12+")\x12\r\n\x0bLiving Room\x12\x04\x18\xc0\xbe\x01\x12\x03\xb0\x08\x00\x12\x03\xb8\x08\x00\x12\x03\xc0\x08\x01\x12\x03\xb0\t\x00',
        )


if __name__ == "__main__":
    unittest.main()
