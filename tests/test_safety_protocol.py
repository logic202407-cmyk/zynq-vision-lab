import binascii
import importlib.util
from pathlib import Path
import unittest

MODULE = Path(__file__).resolve().parents[1] / 'src/prototype/skystar_openmv/safety_protocol.py'
SPEC = importlib.util.spec_from_file_location('safety_protocol', MODULE)
codec = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(codec)


class SafetyProtocolTests(unittest.TestCase):
    def test_ccitt_reference_and_wire_body(self):
        self.assertEqual(binascii.crc_hqx(b'123456789', 0xffff), 0x29b1)
        frame = codec.encode(0x1234567887654321, 0, 'arm')
        body, crc = frame.rstrip(b'\n').split(b'*')
        self.assertEqual(body, b's1 1234567887654321 0 arm')
        self.assertEqual(int(crc, 16), binascii.crc_hqx(body, 0xffff))

    def test_only_explicit_supported_commands(self):
        for payload in ('hb', 'home', 'auto', 'pan 1500', 'tlt 1550'):
            self.assertTrue(codec.encode(1, 1, payload).endswith(b'\n'))
        for args in ((0, 0, 'arm'), (1, 1, 'arm'), (1, 0, 'hb'),
                     (1, 1, 'pan 1701'), (1, 1, 'tlt 1299'), (1, 1, 'stop\nhome'),
                     (1, 2**32, 'hb'), (2**64, 1, 'hb')):
            with self.subTest(args=args), self.assertRaises(ValueError):
                codec.encode(*args)

    def test_strict_safety_status(self):
        line = 'S1STAT SAFE fault WHY link_timeout NONCE 1234567887654321 SEQ 0 TX_DROP 1 FW 15'
        self.assertEqual(codec.status(line)['SAFE'], 'fault')
        for bad in ('P0V 1 STATE waiting', line + ' EXTRA 1',
                    line.replace('fault', 'ready'), line.replace('FW 15', 'FW 14'),
                    line.replace('SEQ 0', 'SEQ -1'), line.replace('1234567887654321', 'bad')):
            with self.subTest(line=bad), self.assertRaises(ValueError):
                codec.status(bad)
