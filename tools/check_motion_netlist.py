"""Compile/simulate an exported functional netlist; never access hardware."""
import argparse,subprocess,shutil,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);p.add_argument('--netlist',type=Path,required=True);a=p.parse_args();stage=a.stage.absolute();stage.mkdir(parents=True,exist_ok=False)
 shutil.copyfile(a.netlist,stage/'motion_func.v');shutil.copyfile(ROOT/'sim/motion_netlist_tb.v',stage/'tb.v')
 shutil.copyfile('D:/Vivado/Vivado/2024.2/data/verilog/src/glbl.v',stage/'glbl.v')
 (stage/'run.tcl').write_text('run all\nquit\n');vb=Path('D:/Vivado/Vivado/2024.2/bin');results=[]
 for name,cmd in [('xvlog',[str(vb/'xvlog.bat'),'motion_func.v','tb.v','glbl.v']),('xelab',[str(vb/'xelab.bat'),'motion_netlist_tb','glbl','-L','unisims_ver','-s','gate']),('xsim',[str(vb/'xsim.bat'),'gate','-tclbatch','run.tcl'])]:
  r=subprocess.run(cmd,cwd=stage,capture_output=True,timeout=600);(stage/(name+'.log')).write_bytes(r.stdout+r.stderr);results.append({'name':name,'exit_code':r.returncode})
  assert r.returncode==0,(name,r.stdout,r.stderr)
  if name=='xsim':assert b'MOTION_NETLIST_PASS' in r.stdout and b'Fatal' not in r.stdout,(r.stdout,r.stderr)
 (stage/'result.json').write_text(json.dumps({'pass':'MOTION_NETLIST_PASS','bytes':45,'scope':'exported functional-netlist smoke, no SDF or hardware timing','steps':results,'exit_code':0},indent=2));print('MOTION_NETLIST_PASS 45 bytes; all tool exit codes 0')
if __name__=='__main__':main()
