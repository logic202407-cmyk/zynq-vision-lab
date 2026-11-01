"""Run existing frozen mailbox scenarios at full 219-bit width and clock ratios."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from check_motion_cosim import ROOT, VB

def main():
    p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True)
    stage=p.parse_args().stage.absolute();stage.mkdir(parents=True,exist_ok=False)
    original=(ROOT/'sim/c1/vision_cdc_tb.v').read_text()
    rtl=ROOT/'src/rtl/vision_snapshot_cdc.v'
    results=[]
    # Half-periods in ns: source slower, faster, near-equal, equal/phase shifted.
    for index,(sh,dh,phase) in enumerate([(7,5,0),(3,11,2),(11,3,1),(5,5,3),(5,6,2)]):
        work=stage/str(index);work.mkdir()
        tb=original.replace('always #7 sclk=~sclk;always #5 dclk=~dclk;',
            f'always #{sh} sclk=~sclk;initial begin #{phase};forever #{dh} dclk=~dclk;end')
        tb=tb.replace('[63:0]','[218:0]').replace('.WIDTH(64)', '.WIDTH(219)')
        # Preserve the original >=40-deliveries assertion even for a fast source
        # and slow destination: increase traffic, never relax the pass threshold.
        tb=tb.replace('i<600', 'i<2400')
        tb=tb.replace("{32'hfedcba98^i,i[31:0]}", "{7{i[31:0]^32'hfedcba98}}")
        tb=tb.replace("64'h12345678abcdef01", "{219{1'b1}}")
        tb=tb.replace("64'hffff00000000ffff", "{109{2'b10}}")
        # Track data stability in addition to the unchanged receive scoreboard.
        tb=tb.replace(' initial begin\n #31;', ''' reg[218:0] last_hold; reg was_busy=0;
 always @(negedge sclk) begin
  if(!srst||!drst) was_busy=0;
  else begin
   if(was_busy && dut.holding!==last_hold)$fatal(1,"payload changed while outstanding");
   last_hold=dut.holding;was_busy=!ready;
  end
 end
 initial begin
 #31;''')
        (work/'vision_cdc_tb.v').write_text(tb)
        (work/rtl.name).write_bytes(rtl.read_bytes())
        (work/'run.tcl').write_text('run all\nquit\n')
        row=dict(source_half_ns=sh,destination_half_ns=dh,phase_ns=phase,commands=[])
        for tool,args in [('xvlog',['vision_snapshot_cdc.v','vision_cdc_tb.v']),
                          ('xelab',['vision_cdc_tb','-s','cdc']),
                          ('xsim',['cdc','-tclbatch','run.tcl'])]:
            cmd=[str(VB/(tool+'.bat'))]+args
            run=subprocess.run(cmd,cwd=work,capture_output=True,timeout=120)
            output=run.stdout+run.stderr;(work/(tool+'.txt')).write_bytes(output)
            row['commands'].append(dict(command=cmd,exit_code=run.returncode))
            if run.returncode or b'Fatal' in output or (tool=='xsim' and b'C1_CDC_PASS' not in output):
                row['verdict']='FAIL';results.append(row)
                (stage/'result.json').write_text(json.dumps(results,indent=2));raise RuntimeError((index,tool))
        row['verdict']='PASS';results.append(row)
    (stage/'result.json').write_text(json.dumps(dict(cases=results,passed=len(results),failed=0,
        source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                       for p in [rtl,ROOT/'sim/c1/vision_cdc_tb.v',Path(__file__).resolve()]},
        limitation='Digital simulation does not model metastability or establish MTBF',hardware_actions=[]),indent=2))
    print('C1_CDC_SWEEP_PASS 5 full-width clock/phase cases')

if __name__=='__main__':main()
