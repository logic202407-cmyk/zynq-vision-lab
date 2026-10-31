"""Run the B2 candidate offline suite; never opens a physical device."""
import argparse,concurrent.futures,json,shutil,subprocess,sys
from pathlib import Path
from check_motion_cosim import build,ROOT
GROUPS=[['normal','ack_loss','link_loss','fpga_reset','mcu_reset','busy_repeat','pc_handoff','handoff_unconfirmed','range','stale_sync'],
        ['bad_ack_crc','late_ack','mismatch_sequence','mismatch_nonce','mismatch_opcode','mismatch_request_crc','mismatch_target','recovery','boundaries','sync_crc']]
def main():
    if not __debug__:raise RuntimeError('Assertions must be enabled')
    p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);a=p.parse_args();root=a.stage.absolute()
    assert str(root).isascii() and ROOT not in root.resolve().parents
    root.mkdir(parents=True,exist_ok=False)
    build(root/'a');shutil.copytree(root/'a',root/'b')
    build(root/'auth',300);build(root/'legacy',30000,True)
    def group(name,cases,extra=()):
        stage=root/name;results=[]
        for case in cases:
            print('RUN '+name+'/'+case,flush=True)
            cmd=[sys.executable,'-B',str(ROOT/'tools/check_motion_cosim.py'),'--stage',str(stage),'--built','--case',case]+list(extra)
            p=subprocess.run(cmd,cwd=ROOT,capture_output=True,timeout=300)
            (stage/(case+'.log')).write_bytes(p.stdout+p.stderr)
            results.append({'case':case,'exit_code':p.returncode})
            (stage/'suite-exits.json').write_text(json.dumps(results,indent=2))
            print('EXIT '+name+'/'+case+' '+str(p.returncode),flush=True)
            if p.returncode:raise RuntimeError(str(stage/(case+'.log')))
        return results
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        jobs=[pool.submit(group,'a',GROUPS[0]),pool.submit(group,'b',GROUPS[1]),
              pool.submit(group,'auth',['auth_expiry'],['--auth-ms','300']),
              pool.submit(group,'legacy',['legacy'],['--legacy'])]
        results=[j.result() for j in jobs]
    p=subprocess.run([sys.executable,'-B',str(ROOT/'tools/check_s1ack_c.py'),'--stage',str(root/'a')],capture_output=True,cwd=ROOT)
    (root/'c-tests.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0
    c=json.loads((root/'a/c-tests.json').read_text())
    out={'pass':'B2_OFFLINE_SUITE_PASS','coupled_scenarios':sum(map(len,results)),
         'c_cases':c['count'],'cases':results,'exit_code':0,'hardware_actions':[]}
    (root/'suite.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
if __name__=='__main__':main()
