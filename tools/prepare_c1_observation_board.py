"""Private vendor integration. Does not access hardware; no motion authorization exists."""
import argparse,hashlib,json,shutil,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--vendor',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
r=Path(__file__).resolve().parents[1];v=a.vendor.resolve();o=a.output.absolute()
if o.exists() or not o.as_posix().isascii() or o.resolve()==r or r in o.resolve().parents:raise SystemExit('Fresh ASCII private output outside repository required')
seed=o.parent/(o.name+'-seed');seed.mkdir(exist_ok=False)
shutil.copytree(v/'rtl',seed/'rtl');shutil.copytree(v/'prj/ov5640_udp_pc.srcs/sources_1/ip',seed/'ip')
shutil.copyfile(v/'prj/ov5640_udp_pc.srcs/constrs_1/new/ov5640_udp_pc.xdc',seed/'ov5640_udp_pc.xdc')
for n in ('preflight.tcl','build_horizontal.tcl'):(seed/n).write_text('# Not used; custom C1 build script owns the flow.\n')
subprocess.run([sys.executable,str(r/'tools/prepare_vendor_red_camera.py'),'--source',str(seed),'--output',str(o),'--spatial-filter'],check=True)
top=o/'rtl/ov5640_udp_pc.v';s=top.read_text(encoding='latin1')
old='    inout              cam_sda';assert old in s;s=s.replace(old,'    output wire        c1_mcu_tx, c1_pc_tx,\n    input wire         c1_mcu_rx,\n'+old,1)
# Keep archive camera timing; no silent reuse of an unrecorded 30-FPS patch.
anchor='wire pl_pixel_valid, pl_frame_start, pl_frame_end;';assert s.count(anchor)==1
block=(r/'board/skystar_f407/c1_observation_insert.vh').read_text()
s=s.replace(anchor,block+'\n'+anchor,1)
# New PL-only reset trees use local synchronous release; original vendor logic retained.
s=s.replace('.cam_pclk(cam_pclk), .rst_n(rst_n), .cam_vsync', '.cam_pclk(cam_pclk), .rst_n(c1_cam_reset_n), .cam_vsync')
s=s.replace('.clk(cam_pclk), .rst_n(rst_n), .pixel_valid', '.clk(cam_pclk), .rst_n(c1_cam_reset_n), .pixel_valid')
s=s.replace('.clk(cam_pclk), .rst_n(rst_n), .result_strobe', '.clk(cam_pclk), .rst_n(c1_cam_reset_n), .result_strobe')
top.write_text(s,encoding='latin1')
files=['uart_tx_8n1','uart_rx','zynq_motion_s1','vision_measurement_tx','vision_snapshot_cdc','uart_line_queue','uart_line_scheduler','measurement_nonce_observer','measurement_session','zynq_vision_link','c1_observation_link','camera_measurement_snapshot']
for n in files:shutil.copyfile(r/'src/rtl'/ (n+'.v'),o/'rtl'/ (n+'.v'))
x=o/'ov5640_udp_pc.xdc';s=x.read_text(encoding='latin1');s+='\nset_property -dict {PACKAGE_PIN AB25 IOSTANDARD LVCMOS33} [get_ports c1_mcu_tx]\nset_property -dict {PACKAGE_PIN AB26 IOSTANDARD LVCMOS33} [get_ports c1_mcu_rx]\nset_property -dict {PACKAGE_PIN AA28 IOSTANDARD LVCMOS33} [get_ports c1_pc_tx]\n';x.write_text(s,encoding='latin1')
manifest={str(f.relative_to(o)):hashlib.sha256(f.read_bytes()).hexdigest() for f in o.rglob('*') if f.is_file() and f.suffix in ('.v','.xdc','.xci')}
(o/'source-sha256.json').write_text(json.dumps(manifest,indent=2));print('PRIVATE_BOARD_PREPARED',o)
