"""Feed independently decoded XSim TX bytes into actual USART3 ISR/queue."""
import csv,json,ctypes as C,subprocess,argparse,hashlib
from pathlib import Path
from check_motion_cosim import ROOT,FW
p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);a=p.parse_args();s=a.stage.absolute()
(s/'uart_queue.c').write_text('#include "'+(ROOT/'sim/cosim/stm32_adapter.c').as_posix()+'"\nAPI int b3_pop(void){uint8_t b;uint32_t t;return board_pc_timed_byte(&b,&t)?b:-1;}\n')
cmd=['D:/Dev-Cpp/MinGW64/bin/gcc.exe','-shared','-std=c99','-Wall','-Wextra','-Werror','-O2','-DBOARD_HOST_TEST','-DS1ACK1','-DCONSOLE_USART=3','-I'+str(FW/'User'),'-I'+str(FW.parent/'stm32_project/User'),str(s/'uart_queue.c'),str(FW/'User/safety.c'),str(FW/'User/tracking.c'),str(FW.parent/'stm32_project/User/pid.c'),'-o',str(s/'uart_queue.dll')]
r=subprocess.run(cmd,capture_output=True);(s/'c-build.log').write_bytes(r.stdout+r.stderr);assert r.returncode==0
lib=C.CDLL(str(s/'uart_queue.dll'));rows=list(csv.DictReader((s/'matrix.csv').open()));groups={int(x['case']):x for x in rows}
for x in rows:x['c_queue_errors']=0;x['c_bytes']=0
old=None
for line in (s/'mcu_bytes.csv').read_text().splitlines():
 case,idx,expected,value,bad=map(int,line.split(','));g=groups[case]
 if case!=old:lib.model_init();old=case
 lib.model_receive(value,bad);actual=lib.b3_pop();g['c_bytes']+=1
 if actual!=(-1 if bad else value):g['c_queue_errors']+=1
required=[x for x in rows if abs(float(x['relative_percent']))<=2.001]
failed=[x for x in required if any(int(x[k]) for k in ['tx_errors','rx_errors','frame_errors','c_queue_errors']) or int(x['tx_count'])!=int(x['rx_count'])]
passing=[float(x['relative_percent']) for x in rows if all(int(x[k])==0 for k in ['tx_errors','rx_errors','frame_errors']) and int(x['tx_count'])==int(x['rx_count'])]
failpos=sorted(float(x['relative_percent']) for x in rows if float(x['relative_percent'])>0 and (int(x['tx_errors']) or int(x['rx_errors']) or int(x['frame_errors'])))
failneg=sorted((float(x['relative_percent']) for x in rows if float(x['relative_percent'])<0 and (int(x['tx_errors']) or int(x['rx_errors']) or int(x['frame_errors']))),reverse=True)
source_sha256={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in list((FW/'User').glob('*.[ch]'))+[ROOT/'sim/cosim/stm32_adapter.c',Path(__file__).resolve()]}
result={'source_sha256':source_sha256,'tool':'XSim2024.2 + GCC actual USART3 ISR/queue','scope':'behavioral 3-sample timing surrogate, not ST silicon receiver equivalence','command':cmd,'compile_exit':r.returncode,'matrix_count':len(rows),'required_relative_2percent_count':len(required),'required_failed':len(failed),'passing_observed_range_percent':[min(passing),max(passing)],'first_observed_failure_percent':[failneg[0],failpos[0]],'boundary_resolution':'sampled grid only, not exact maximum tolerance','rows':rows,'exit_code':int(bool(failed))}
(s/'uart-result.json').write_text(json.dumps(result,indent=2));print({k:v for k,v in result.items() if k not in ['rows','command']});raise SystemExit(result['exit_code'])
