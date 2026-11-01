"""Three-gimbal observation dashboard. No serial, network or motion commands.

Existing UDP viewer can supply Frame objects to ingest_frame; JSONL replay is
the default standalone input. All fixture/replay data remains visibly labelled.
"""
import argparse
import binascii
from dataclasses import dataclass, field
import json
from pathlib import Path
import struct
import tkinter as tk
from tkinter import ttk
from PIL import ImageTk
from .camera_viewer import rgb565_be_to_image
from .vision_measurement import decode, from_pl


@dataclass
class ExperimentState:
    session: int
    cameras: dict = field(default_factory=dict)
    gimbals: list = field(default_factory=lambda: [
        dict(id=i, installed=i==0, pan=None, tilt=None, enabled=None,
             fault='UNKNOWN', owner='NONE', communication='OFFLINE' if i==0 else 'NOT CONNECTED')
        for i in range(3)])

    def measurement(self, packet, now):
        m=decode(packet)
        if m.origin!=1 or m.camera!=0:
            raise ValueError('PC reference cannot replace PL camera slot')
        if m.session!=self.session:
            raise ValueError('session must be explicitly rebound')
        old=self.cameras.get(m.camera)
        if old and m.sequence<=old['sequence']:
            raise ValueError('duplicate/reversed frame')
        self.cameras[m.camera]=dict(sequence=m.sequence, sequence_kind='source_frame',
            rx_ms=now, valid=bool(m.flags&2), centroid=m.centroid,
            bbox=(m.xmin,m.ymin,m.xmax,m.ymax) if m.flags&2 else None,
            width=m.width,height=m.height,origin='PL' if m.origin==1 else 'PC_REFERENCE',
            gaps=(old['gaps']+m.sequence-old['sequence']-1) if old else 0,
            calibration='UNKNOWN', count=m.count)

    def openmv(self, camera, packet, now):
        if camera!=1:
            raise ValueError('only OpenMV1 link is configured; other UART resources unknown')
        if len(packet)!=8:
            raise ValueError('OpenMV length')
        a,b,dx,dy,valid,end=struct.unpack('<BBhhBB',packet)
        if (a,b,end)!=(0xaa,0xff,0xee) or valid not in (0,1) or not -80<=dx<=79 or not -59<=dy<=60 or (not valid and (dx or dy)):
            raise ValueError('OpenMV framing/range')
        old=self.cameras.get(camera)
        self.cameras[camera]=dict(sequence=(old['sequence']+1) if old else 1,
            sequence_kind='local_receive_count',rx_ms=now,valid=bool(valid),
            centroid=(80+dx,60-dy) if valid else None,bbox=None,width=160,height=120,
            origin='OPENMV_MAX_BLOB',gaps=None,calibration='UNKNOWN',count=None)

    def snapshot(self,now):
        cameras={k:dict(v,fresh=0<=now-v['rx_ms']<200) for k,v in self.cameras.items()}
        return dict(gimbals=[dict(g) for g in self.gimbals],cameras=cameras)

    def ack_snapshot(self,line):
        """Display historical REG snapshot only; never authorizes or sends motion."""
        body,crc=line.strip().rsplit('*',1)
        if binascii.crc_hqx(body.encode('ascii'),0xffff)!=int(crc,16):
            raise ValueError('ACK CRC')
        f=body.split()
        if len(f)!=17 or f[0]!='S1ACK' or f[7]!='REG' or f[6]!='ACCEPT':
            raise ValueError('not a register ACK snapshot')
        pan,tilt,mask=int(f[12]),int(f[13]),int(f[14])
        if not 1300<=pan<=1700 or not 1300<=tilt<=1700 or mask not in (0,3):
            raise ValueError('invalid snapshot')
        self.gimbals[0].update(pan=pan,tilt=tilt,enabled=bool(mask),fault=f[10],
                              communication='ACK SNAPSHOT',owner='S1 historical')


class Dashboard(ttk.Frame):
    def __init__(self,master,session=1,label='OFFLINE / REPLAY'):
        super().__init__(master,padding=12);self.pack(fill='both',expand=True)
        self.model=ExperimentState(session);self.photo=None
        ttk.Label(self,text=label+' — 软件目标脉宽不是实测角度').pack(anchor='w')
        self.video=ttk.Label(self,text='OV5640: NO VIDEO');self.video.pack()
        self.vision=ttk.Treeview(self,columns=('source','seq','valid','xy','gap'),show='headings',height=4)
        for c,title in zip(self.vision['columns'],('来源/相机','序号及类型','有效/新鲜','像素坐标','丢帧')):
            self.vision.heading(c,text=title)
        self.vision.pack(fill='x')
        self.devices=ttk.Treeview(self,columns=('id','link','pan','tlt','enabled','fault'),show='headings',height=3)
        for c,title in zip(self.devices['columns'],('云台','通信','PAN目标 μs','TILT目标 μs','PWM使能','故障')):
            self.devices.heading(c,text=title)
        self.devices.pack(fill='x');self.refresh(0)

    def refresh(self,now):
        s=self.model.snapshot(now)
        self.vision.delete(*self.vision.get_children());self.devices.delete(*self.devices.get_children())
        for camera in range(4):
            c=s['cameras'].get(camera)
            values=(f'{camera}: '+c['origin'],f"{c['sequence']} ({c['sequence_kind']})",f"{c['valid']}/{c['fresh']}",str(c['centroid']),str(c['gaps'])) if c else (f'{camera}: NOT CONNECTED','—','False/False','—','UNKNOWN')
            self.vision.insert('','end',values=values)
        for g in s['gimbals']:
            self.devices.insert('','end',values=(g['id']+1,g['communication'],g['pan'] if g['pan'] is not None else 'UNKNOWN',g['tilt'] if g['tilt'] is not None else 'UNKNOWN',str(g['enabled']),g['fault']))

    def ingest_frame(self,frame,now):
        from PIL import ImageDraw
        image=rgb565_be_to_image(frame)
        m=frame.pl_measurement
        if m is not None and m.frame_seq==frame.frame_seq:
            self.model.measurement(from_pl(m,self.model.session,frame.width,frame.height).encode(),now)
            if m.target_valid and m.centroid is not None:
                draw=ImageDraw.Draw(image);draw.rectangle(m.bbox,outline='red',width=2)
                x,y=m.centroid;draw.line((x-4,y,x+4,y),fill='yellow');draw.line((x,y-4,x,y+4),fill='yellow')
        self.photo=ImageTk.PhotoImage(image);self.video.configure(image=self.photo,text='')
        self.refresh(now)


def main():
    p=argparse.ArgumentParser();p.add_argument('--replay',type=Path);p.add_argument('--session',type=int,required=True);a=p.parse_args()
    root=tk.Tk();root.title('三套云台视觉实验 — 仅观察');ui=Dashboard(root,a.session)
    if a.replay:
        records=[json.loads(x) for x in a.replay.read_text(encoding='utf-8').splitlines() if x.strip()]
        def step(i=0):
            if i>=len(records):return
            r=records[i]
            if r['type']=='pl':ui.model.measurement(bytes.fromhex(r['packet_hex']),r['rx_ms'])
            elif r['type']=='openmv':ui.model.openmv(r['camera'],bytes.fromhex(r['packet_hex']),r['rx_ms'])
            elif r['type']=='ack':ui.model.ack_snapshot(r['line'])
            elif r['type']=='video':
                from .vendor_udp import Frame,PLMeasurement
                m=PLMeasurement(**r['measurement']) if r.get('measurement') else None
                ui.ingest_frame(Frame(bytes.fromhex(r['rgb565_hex']),r['width'],r['height'],r['sequence'],pl_measurement=m),r['rx_ms'])
            else:raise ValueError('unknown record type')
            ui.refresh(r['rx_ms']);root.after(100,lambda:step(i+1))
        root.after(0,step)
    root.mainloop()


if __name__=='__main__':main()
