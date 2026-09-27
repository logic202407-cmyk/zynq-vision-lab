import unittest

from src.pc.vendor_udp import (
    FRAME_BYTES,
    FRAME_HEADER,
    HEIGHT,
    ROW_BYTES,
    FrameAssembler,
)


class FrameAssemblerTests(unittest.TestCase):
    def setUp(self):
        self.assembler = FrameAssembler()
        self.row = bytes.fromhex("f800") * (ROW_BYTES // 2)

    def test_complete_frame(self):
        self.assertIsNone(self.assembler.feed(FRAME_HEADER + self.row))
        frame = None
        for _ in range(HEIGHT - 1):
            frame = self.assembler.feed(self.row)
        self.assertIsNotNone(frame)
        self.assertEqual(len(frame.rgb565_be), FRAME_BYTES)
        self.assertEqual(frame.rgb565_be[:ROW_BYTES], self.row)
        self.assertEqual(self.assembler.completed, 1)

    def test_incomplete_frame_dropped_at_next_header(self):
        self.assembler.feed(FRAME_HEADER + self.row)
        self.assembler.feed(self.row)
        self.assembler.feed(FRAME_HEADER + self.row)
        self.assertEqual(self.assembler.incomplete, 1)
        self.assertEqual(self.assembler.rows_received, 1)

    def test_bad_header_and_orphan(self):
        self.assembler.feed(FRAME_HEADER[:4] + b"\x00\x01\x00\x01" + self.row)
        self.assembler.feed(self.row)
        self.assertEqual(self.assembler.malformed, 1)
        self.assertEqual(self.assembler.orphan_rows, 1)

    def test_bad_row_invalidates_partial(self):
        self.assembler.feed(FRAME_HEADER + self.row)
        self.assembler.feed(b"short")
        self.assertEqual(self.assembler.malformed, 1)
        self.assertEqual(self.assembler.incomplete, 1)
        self.assertEqual(self.assembler.rows_received, 0)

    def test_pixel_row_can_begin_with_magic_bytes(self):
        self.assembler.feed(FRAME_HEADER + self.row)
        pixel_row = bytes.fromhex("f05aa50f") + self.row[4:]
        self.assembler.feed(pixel_row)
        self.assertEqual(self.assembler.rows_received, 2)
        self.assertEqual(self.assembler.malformed, 0)

    def test_pl_extension_attaches_previous_frame_measurement(self):
        extension = (2).to_bytes(4, "big") + (1).to_bytes(4, "big")
        extension += bytes((3, 1, 0, 0))
        extension += (2).to_bytes(4, "big")
        extension += (9).to_bytes(4, "big") + (7).to_bytes(4, "big")
        extension += b"".join(n.to_bytes(2, "big") for n in (3, 2, 6, 5))
        self.assertEqual(len(extension), 32)
        self.assembler.feed(FRAME_HEADER + extension + self.row)
        frame = None
        for _ in range(HEIGHT - 1):
            frame = self.assembler.feed(self.row)
        self.assertEqual(frame.frame_seq, 2)
        self.assertEqual(frame.previous_measurement.frame_seq, 1)
        self.assertEqual(frame.previous_measurement.count, 2)
        self.assertEqual(frame.previous_measurement.bbox, (3, 2, 6, 5))
        self.assertEqual(frame.previous_measurement.centroid, (4, 3))

    def test_bad_pl_extension_is_rejected(self):
        self.assertIsNone(self.assembler.feed(FRAME_HEADER + bytes(32) + self.row))
        self.assertEqual(self.assembler.malformed, 1)


if __name__ == "__main__":
    unittest.main()
