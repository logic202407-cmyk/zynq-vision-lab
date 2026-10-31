"""Offline XSim diagnostic test; optional RTL synthesis only, no hardware API."""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage',type=Path,required=True,help='ASCII alias path outside Git')
    parser.add_argument('--vivado-bin',type=Path,default=Path('D:/Vivado/Vivado/2024.2/bin'))
    args=parser.parse_args()
    stage=args.stage
    if not str(stage).isascii():
        raise ValueError('Use an ASCII drive alias for simulator working directory')
    stage.mkdir(parents=True,exist_ok=True)
    output=ROOT/'report/evidence/checkpoint_d'
    output.mkdir(parents=True,exist_ok=True)
    files=['src/rtl/uart_tx_8n1.v','src/rtl/zynq_uart_diagnostic.v','sim/uart_diagnostic_tb.v']
    for name in files:
        shutil.copyfile(ROOT/name,stage/Path(name).name)
    steps=[]

    def run(name,tool,arguments):
        result=subprocess.run([str(args.vivado_bin/(tool+'.bat'))]+arguments,
                              cwd=stage,capture_output=True,env=dict(os.environ,PYTHONUTF8='1'))
        raw=result.stdout+result.stderr
        (stage/(name+'.raw')).write_bytes(raw)
        text=raw.decode('utf-8','replace').replace('\r','')
        text='\n'.join(line.rstrip() for line in text.splitlines()).rstrip()+'\n'
        with (output/(name+'.txt')).open('w',encoding='utf-8',newline='\n') as f:
            f.write(text+f'\nEXIT_CODE={result.returncode}\n')
        steps.append({'tool':tool,'arguments':arguments,'exit_code':result.returncode})
        if result.returncode or re.search(r'\b(ERROR:|Fatal:)',text):
            raise RuntimeError(name+' failed; see '+str(output/(name+'.txt')))
        return text

    run('compile','xvlog',[Path(f).name for f in files])
    run('elaborate','xelab',['uart_diagnostic_tb','-s','diagnostic_check'])
    text=run('simulate','xsim',['diagnostic_check','-runall'])
    if 'UART_DIAGNOSTIC_TB_PASS' not in text:
        raise RuntimeError('No pass marker')
    # out-of-context synthesis verifies synthesizable candidate RTL, no pins/hw.
    tcl='''set_param general.maxThreads 2
create_project -in_memory -part xc7z100ffg900-2
read_verilog {uart_tx_8n1.v zynq_uart_diagnostic.v}
synth_design -top zynq_uart_diagnostic -part xc7z100ffg900-2 -mode out_of_context
report_utilization -file diagnostic_utilization.rpt
puts "DIAGNOSTIC_SYNTH_PASS"
close_project
exit 0
'''
    (stage/'synth.tcl').write_text(tcl,encoding='ascii')
    synthesis=run('synthesis','vivado',['-mode','batch','-nojournal','-log','synth.log','-source','synth.tcl'])
    if 'DIAGNOSTIC_SYNTH_PASS' not in synthesis:
        raise RuntimeError('No synthesis pass marker')
    utilization=(stage/'diagnostic_utilization.rpt').read_text('utf-8')
    with (output/'utilization.rpt').open('w',encoding='utf-8',newline='\n') as f:
        f.write('\n'.join(line.rstrip() for line in utilization.splitlines()).rstrip()+'\n')
    result={'scope':'XSim and out-of-context synthesis only; no pins, implementation or hardware',
        'parent_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'version':re.findall(r'Vivado[^\r\n]*2024\.2[^\r\n]*',synthesis)[:1],
        'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in files},
        'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'pass_marker':re.findall(r'UART_DIAGNOSTIC_TB_PASS[^\r\n]*',text)[-1],
        'steps':steps,'hardware_actions':[],'exit_code':0}
    (output/'manifest.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(result['pass_marker']);print('PASS diagnostic RTL synthesis; no hardware action')


if __name__=='__main__':
    main()
