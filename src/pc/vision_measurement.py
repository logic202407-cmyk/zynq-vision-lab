"""M2 measurement codec. Neither packets nor ingestion grant motion authority."""
from dataclasses import dataclass
import binascii
import struct

BODY = struct.Struct('>2s6BQIIHHIII6H')
PACKET_BYTES = BODY.size + 2


@dataclass(frozen=True)
class Measurement:
    camera: int
    flags: int
    origin: int
    mask: int
    session: int
    sequence: int
    tick: int
    width: int
    height: int
    count: int
    sum_x: int
    sum_y: int
    xmin: int
    ymin: int
    xmax: int
    ymax: int
    cx: int
    cy: int

    @property
    def centroid(self):
        return (self.cx, self.cy) if self.flags & 2 else None

    def validate(self):
        if self.camera not in range(4) or self.origin not in (1, 2) or self.mask not in (1, 2):
            raise ValueError('unsupported identity/operator')
        if not self.session or self.flags & ~7 or not 0 < self.width <= 640 or not 0 < self.height <= 480:
            raise ValueError('invalid session/flags/size')
        if not self.flags & 4 and self.tick:
            raise ValueError('unavailable capture tick must be zero')
        data = (self.count, self.sum_x, self.sum_y, self.xmin, self.ymin, self.xmax, self.ymax, self.cx, self.cy)
        if not self.flags & 2:
            if any(data):
                raise ValueError('invalid observation must clear geometry')
        elif not self.flags & 1 or not 0 < self.count <= self.width * self.height:
            raise ValueError('invalid count/completeness')
        elif not (0 <= self.xmin <= self.cx <= self.xmax < self.width and
                  0 <= self.ymin <= self.cy <= self.ymax < self.height and
                  self.sum_x <= self.count * (self.width - 1) and
                  self.sum_y <= self.count * (self.height - 1) and
                  self.cx == self.sum_x // self.count and self.cy == self.sum_y // self.count):
            raise ValueError('inconsistent geometry')
        return self

    def encode(self):
        self.validate()
        body = BODY.pack(b'\xa5\x5a', 2, 1, self.camera, self.flags, self.origin, self.mask,
                         self.session, self.sequence, self.tick, self.width, self.height,
                         self.count, self.sum_x, self.sum_y, self.xmin, self.ymin,
                         self.xmax, self.ymax, self.cx, self.cy)
        return body + struct.pack('>H', binascii.crc_hqx(body, 0xffff))

    def line(self):
        return b'v2 ' + self.encode().hex().encode('ascii') + b'\n'


def decode(packet):
    if len(packet) != PACKET_BYTES or binascii.crc_hqx(packet[:-2], 0xffff) != int.from_bytes(packet[-2:], 'big'):
        raise ValueError('packet length/CRC')
    values = BODY.unpack(packet[:-2])
    if values[:3] != (b'\xa5\x5a', 2, 1):
        raise ValueError('version/type')
    return Measurement(*values[3:]).validate()


def from_pl(value, session, width=640, height=480):
    """Existing PLMeasurement, not a PC-computed detector result."""
    valid = value.frame_complete and value.target_valid and value.count > 0
    geometry = (value.count, value.sum_x, value.sum_y, *value.bbox, *value.centroid) if valid else (0,) * 9
    return Measurement(0, int(value.frame_complete) | (2 if valid else 0), 1, value.mask_version,
                       session, value.frame_seq, 0, width, height, *geometry).validate()
