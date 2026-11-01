"""Offline observations only; no sockets, serial devices or PWM drivers."""
import binascii
from dataclasses import replace
import struct
import unittest
from src.pc.vision_measurement import Measurement, decode
from src.pc.experiment_dashboard import ExperimentState


def sample():
    return Measurement(0,3,1,1,1,1,0,640,480,2,60,80,10,20,50,60,30,40)


class C1Integration(unittest.TestCase):
    def test_wire_crc_and_bandwidth(self):
        m=sample();self.assertEqual(decode(m.encode()),m)
        self.assertEqual(len(m.encode()),54);self.assertEqual(len(m.line()),112)
        damaged=bytearray(m.encode());damaged[28]^=1
        with self.assertRaises(ValueError):decode(damaged)

    def test_zero_coordinate_is_not_no_target(self):
        m=replace(sample(),count=1,sum_x=0,sum_y=0,xmin=0,ymin=0,xmax=0,ymax=0,cx=0,cy=0)
        self.assertEqual(decode(m.encode()).centroid,(0,0))
        self.assertIsNone(decode(replace(m,flags=1,count=0).encode()).centroid)

    def test_sources_gaps_and_age(self):
        s=ExperimentState(1);s.measurement(sample().encode(),10)
        s.measurement(replace(sample(),sequence=4).encode(),20)
        s.openmv(1,struct.pack('<BBhhBB',0xaa,0xff,20,-20,1,0xee),30)
        v=s.snapshot(220)
        self.assertEqual(v['cameras'][0]['gaps'],2)
        self.assertFalse(v['cameras'][0]['fresh']);self.assertTrue(v['cameras'][1]['fresh'])
        self.assertEqual(v['cameras'][0]['centroid'],(30,40))
        self.assertEqual(v['cameras'][1]['centroid'],(100,80))
        self.assertIsNone(v['cameras'][1]['gaps'])
        for m in (sample(),replace(sample(),session=2),replace(sample(),origin=2,sequence=5)):
            with self.assertRaises(ValueError):s.measurement(m.encode(),30)

    def test_openmv_quadrants_loss_and_identity(self):
        s=ExperimentState(1)
        for dx,dy in ((20,20),(-20,20),(-20,-20),(20,-20)):
            s.openmv(1,struct.pack('<BBhhBB',0xaa,0xff,dx,dy,1,0xee),0)
            self.assertEqual(s.cameras[1]['centroid'],(80+dx,60-dy))
        s.openmv(1,struct.pack('<BBhhBB',0xaa,0xff,0,0,0,0xee),0)
        self.assertIsNone(s.cameras[1]['centroid'])
        for camera,dx in ((2,0),(1,80)):
            with self.assertRaises(ValueError):s.openmv(camera,struct.pack('<BBhhBB',0xaa,0xff,dx,0,1,0xee),0)

    def test_three_devices_unknown_not_fabricated(self):
        s=ExperimentState(1)
        self.assertEqual(len(s.gimbals),3)
        self.assertEqual([x['communication'] for x in s.gimbals],['OFFLINE','NOT CONNECTED','NOT CONNECTED'])
        for g in s.gimbals:self.assertIsNone(g['pan']);self.assertIsNone(g['enabled'])
        s.gimbals[0]['pan']=1550
        self.assertIsNone(s.gimbals[1]['pan']);self.assertIsNone(s.gimbals[2]['pan'])

    def test_invalid_geometry_and_version(self):
        for m in (replace(sample(),flags=2),replace(sample(),cx=31),replace(sample(),width=0)):
            with self.assertRaises(ValueError):m.encode()
        packet=bytearray(sample().encode());packet[2]=99
        packet[-2:]=binascii.crc_hqx(packet[:-2],0xffff).to_bytes(2,'big')
        with self.assertRaises(ValueError):decode(packet)


if __name__=='__main__':unittest.main()
