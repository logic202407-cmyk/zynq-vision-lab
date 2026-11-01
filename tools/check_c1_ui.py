"""Exercise actual Tk widgets with labelled synthetic data; no hardware I/O."""
import json
from pathlib import Path
import struct
import sys
import tkinter as tk
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.pc.experiment_dashboard import Dashboard
from src.pc.vendor_udp import Frame,PLMeasurement

root=tk.Tk();root.withdraw()
ui=Dashboard(root,1,'SYNTHETIC OFFLINE TEST')
ui.ingest_frame(Frame(b'\x00\x00'*640*480,640,480,1,
    pl_measurement=PLMeasurement(1,True,True,2,60,80,(10,20,50,60))),10)
ui.model.openmv(1,struct.pack('<BBhhBB',0xaa,0xff,20,-20,1,0xee),20)
ui.refresh(20);root.update_idletasks()
assert len(ui.devices.get_children())==3
assert len(ui.vision.get_children())==4
assert ui.photo.width()==640 and ui.photo.height()==480
s=ui.model.snapshot(20)
assert s['cameras'][0]['centroid']==(30,40) and s['cameras'][1]['centroid']==(100,80)
assert [g['communication'] for g in s['gimbals']]==['OFFLINE','NOT CONNECTED','NOT CONNECTED']
root.destroy()
print(json.dumps(dict(verdict='PASS',exit_code=0,cases=3,
    checks=['actual_Tk_video_overlay','two_independent_sources','three_device_rows_six_unknown_targets'],
    scope='synthetic display only; no hardware communication')))
