"""Receiver-side framing for the ATK OV5640 UDP reference design.

This is an original implementation of the wire format observed in the local
XC7Z100/50_ov5640_udp_pc reference. No vendor HDL is redistributed here.
"""

from dataclasses import dataclass


BOARD_IP = "192.168.1.10"
PC_IP = "192.168.1.102"
UDP_PORT = 1234
WIDTH = 640
HEIGHT = 480
ROW_BYTES = WIDTH * 2
FRAME_BYTES = ROW_BYTES * HEIGHT
FRAME_HEAD = bytes.fromhex("f05aa50f")
FRAME_HEADER = FRAME_HEAD + WIDTH.to_bytes(2, "big") + HEIGHT.to_bytes(2, "big")
START_COMMAND = b"1"
STOP_COMMAND = b"0"


@dataclass(frozen=True)
class Frame:
    rgb565_be: bytes
    width: int = WIDTH
    height: int = HEIGHT
    frame_seq: int | None = None
    previous_measurement: "PLMeasurement | None" = None
    pl_measurement: "PLMeasurement | None" = None


@dataclass(frozen=True)
class PLMeasurement:
    frame_seq: int
    frame_complete: bool
    target_valid: bool
    count: int
    sum_x: int
    sum_y: int
    bbox: tuple[int, int, int, int] | None

    @property
    def centroid(self) -> tuple[int, int] | None:
        if not self.target_valid or self.count == 0:
            return None
        return self.sum_x // self.count, self.sum_y // self.count


def parse_pl_extension(extension: bytes) -> tuple[int, PLMeasurement | None]:
    """Decode the 32-byte camera-clock-domain measurement header extension."""
    if len(extension) != 32 or extension[9] != 1 or extension[10:12] != b"\0\0":
        raise ValueError("invalid PL extension")
    current_seq = int.from_bytes(extension[0:4], "big")
    result_seq = int.from_bytes(extension[4:8], "big")
    flags = extension[8]
    if current_seq == 0 or flags & ~3 or result_seq != ((current_seq - 1) & 0xFFFFFFFF):
        raise ValueError("invalid PL sequence or flags")
    if result_seq == 0:
        return current_seq, None
    count = int.from_bytes(extension[12:16], "big")
    sum_x = int.from_bytes(extension[16:20], "big")
    sum_y = int.from_bytes(extension[20:24], "big")
    bbox_values = tuple(int.from_bytes(extension[offset:offset + 2], "big")
                        for offset in (24, 26, 28, 30))
    complete = bool(flags & 1)
    valid = bool(flags & 2)
    if (not complete or not valid) and (count or sum_x or sum_y or any(bbox_values)):
        raise ValueError("invalid empty PL measurement")
    if valid and (not complete or count == 0):
        raise ValueError("invalid target flags")
    return current_seq, PLMeasurement(result_seq, complete, valid, count,
                                      sum_x, sum_y, bbox_values if valid else None)


class FrameAssembler:
    """Assemble one fixed-size frame from row-sized UDP datagrams.

    The original vendor format has no frame number or row index. The optional
    32-byte PL extension adds a frame sequence and previous-frame result, but
    still no row index or checksum. A lost or reordered row cannot always be
    identified exactly. On an early next-frame header, the
    incomplete frame is discarded. With only full-size rows, undetectable
    reorder/duplicate packets remain a protocol limitation.
    """

    def __init__(self) -> None:
        self._buffer = bytearray(FRAME_BYTES)
        self._received = 0
        self._frame_seq: int | None = None
        self._previous_measurement: PLMeasurement | None = None
        self.datagrams = 0
        self.completed = 0
        self.incomplete = 0
        self.malformed = 0
        self.orphan_rows = 0

    @property
    def rows_received(self) -> int:
        return self._received // ROW_BYTES

    def reset_partial(self) -> None:
        if self._received:
            self.incomplete += 1
        self._received = 0
        self._frame_seq = None
        self._previous_measurement = None

    def feed(self, packet: bytes) -> Frame | None:
        self.datagrams += 1
        if len(packet) in (ROW_BYTES + 8, ROW_BYTES + 40):
            self.reset_partial()
            if packet[:8] != FRAME_HEADER:
                self.malformed += 1
                return None
            if len(packet) == ROW_BYTES + 40:
                try:
                    self._frame_seq, self._previous_measurement = parse_pl_extension(packet[8:40])
                except ValueError:
                    self.malformed += 1
                    return None
                row = packet[40:]
            else:
                row = packet[8:]
        else:
            if len(packet) != ROW_BYTES:
                self.malformed += 1
                self.reset_partial()
                return None
            if self._received == 0:
                self.orphan_rows += 1
                return None
            row = packet

        end = self._received + ROW_BYTES
        if end > FRAME_BYTES:
            self.malformed += 1
            self.reset_partial()
            return None
        self._buffer[self._received:end] = row
        self._received = end
        if end == FRAME_BYTES:
            self.completed += 1
            self._received = 0
            return Frame(bytes(self._buffer), frame_seq=self._frame_seq,
                         previous_measurement=self._previous_measurement)
        return None
