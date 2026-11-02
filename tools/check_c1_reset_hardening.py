"""Offline reset boundaries and QID exhaustion, using real XSim/STM32 C."""
import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from check_motion_cosim import ROOT, VB, build, Coupled


def run(cmd, work, name, marker=None):
    result = subprocess.run(cmd, cwd=work, capture_output=True, timeout=180)
    output = result.stdout + result.stderr
    (work / (name + '.log')).write_bytes(output)
    passed = result.returncode == 0 and b'Fatal' not in output
    if marker:
        passed = passed and marker.encode() in output
    row = dict(command=cmd, exit_code=result.returncode, passed=passed)
    if not passed:
        raise AssertionError(row)
    return row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', type=Path, required=True)
    args = parser.parse_args()
    stage = args.stage.absolute()
    stage.mkdir(parents=True, exist_ok=False)
    results = []
    work = stage / 'reset'
    work.mkdir()
    for rel in ['src/rtl/vision_snapshot_cdc.v', 'sim/c1/vision_cdc_reset_tb.v']:
        shutil.copyfile(ROOT / rel, work / Path(rel).name)
    (work / 'run.tcl').write_text('run all\nquit\n')
    for tool, params, marker in [
        ('xvlog', ['vision_snapshot_cdc.v', 'vision_cdc_reset_tb.v'], None),
        ('xelab', ['vision_cdc_reset_tb', '-s', 'reset_boundaries'], None),
        ('xsim', ['reset_boundaries', '-tclbatch', 'run.tcl'], 'CDC_RESET_BOUNDARY_PASS 26')]:
        results.append(run([str(VB / (tool + '.bat'))] + params, work, tool, marker))
    work = stage / 'qid'
    build(work)
    maximum = (1 << 128) - 1
    cases = []
    for case, epoch in [('stop_at_max', maximum), ('last_stop_id', maximum - 1),
                        ('arm_at_max', maximum), ('arm_reserves_stop', maximum - 1),
                        ('active_last_stop', maximum - 2)]:
        c = Coupled(work)
        try:
            c.controls = (c.controls & ~(maximum << 23)) | (epoch << 23)
            c.drive()
            c.sync()
            if case == 'active_last_stop':
                c.arm()
                c.move(0, 1550)
            if case in ('last_stop_id', 'active_last_stop'):
                c.stop()
                assert c.lines[-1].startswith('s1q ' + 'f' * 32 + ' stop*')
                assert c.lib.model_reg(0x40000820) == 0
            before = list(c.lines)
            arming = case in ('arm_at_max', 'arm_reserves_stop')
            c.pulse(2 if arming else 4)
            c.advance(270000)
            assert c.state == 6 and c.status & 32
            assert c.lines == before, 'exhausted ID emitted a new UART command'
            assert c.lib.model_reg(0x40000820) == 0
            if not arming:
                assert not c.status & 64, 'unconfirmed STOP reported confirmed'
            # Ordinary incoming data cannot clear the latched fault or authorize.
            c.advance(120000)
            assert c.state == 6 and c.lib.model_reg(0x40000820) == 0
            cases.append(dict(case=case, epoch=f'{epoch:032x}', passed=True,
                              lines=c.lines, status=c.status, pwm_ccer=0))
            (stage / (case + '.json')).write_text(json.dumps(dict(
                case=case, to_mcu=c.to_mcu, from_mcu=c.from_mcu,
                trace=c.trace, lines=c.lines), indent=2))
        finally:
            c.close()
    sources = ['src/rtl/vision_snapshot_cdc.v', 'src/rtl/zynq_vision_link.v',
               'src/rtl/zynq_motion_s1.v', 'sim/c1/vision_cdc_reset_tb.v',
               'tools/check_c1_reset_hardening.py']
    report = dict(verdict='PASS', reset_scenarios=26, qid_cases=cases,
                  commands=results, exit_code=0,
                  source_sha256={s: hashlib.sha256((ROOT / s).read_bytes()).hexdigest()
                                 for s in sources}, hardware_actions=[],
                  limitation='Digital reset tests do not model metastability; '
                             'QID exhaustion does not provide persistent epoch allocation')
    (stage / 'result.json').write_text(json.dumps(report, indent=2))
    print('RESET_HARDENING_PASS 26 reset scenarios + 5 QID exhaustion cases')


if __name__ == '__main__':
    main()
