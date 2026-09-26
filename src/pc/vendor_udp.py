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


class FrameAssembler:
    """Assemble one fixed-size frame from row-sized UDP datagrams.

    The vendor format has no frame number or row index. A lost or reordered
    row cannot be identified exactly. On an early next-frame header, the
    incomplete frame is discarded. With only full-size rows, undetectable
    reorder/duplicate packets remain a protocol limitation.
    """

    def __init__(self) -> None:
        self._buffer = bytearray(FRAME_BYTES)
        self._received = 0
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

    def feed(self, packet: bytes) -> Frame | None:
        self.datagrams += 1
        if len(packet) == ROW_BYTES + 8:
            self.reset_partial()
            if packet[:8] != FRAME_HEADER:
                self.malformed += 1
                return None
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
            return Frame(bytes(self._buffer))
        return None
