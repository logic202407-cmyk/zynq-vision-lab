"""Offline-only self-checking XSim runner; writes commands/exits/hashes."""
import argparse,subprocess,shutil,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];VB=Path('D:/Vivado/Vivado/2024.2/bin')
def run(top,files,stage,limit=1800):
 stage.mkdir(parents=True,exist_ok=False);record={'tool':'Vivado XSim2024.2','sources':{},'steps':[]}
 for f in files:
  p=ROOT/f;shutil.copyfile(p,stage/p.name);record['sources'][f]=hashlib.sha256(p.read_bytes()).hexdigest()
 (stage/'run.tcl').write_text('run all\nquit\n')
 for name,cmd in [('xvlog',[str(VB/'xvlog.bat')]+[Path(f).name for f in files]),('xelab',[str(VB/'xelab.bat'),top,'-s','test']),('xsim',[str(VB/'xsim.bat'),'test','-tclbatch','run.tcl'])]:
  p=subprocess.run(cmd,cwd=stage,capture_output=True,timeout=limit);(stage/(name+'.log')).write_bytes(p.stdout+p.stderr)
  record['steps'].append({'command':cmd,'exit_code':p.returncode});(stage/'run.json').write_text(json.dumps(record,indent=2))
  if p.returncode or b'Fatal' in p.stdout:raise RuntimeError(name+' failed')
  if name=='xsim' and not (b'B3_' in p.stdout and b'_PASS' in p.stdout):raise RuntimeError('Missing explicit test PASS')
 print(top+' finished; inspect explicit PASS and matrix')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--top',required=True);p.add_argument('--stage',type=Path,required=True);p.add_argument('files',nargs='+');a=p.parse_args();run(a.top,a.files,a.stage)
