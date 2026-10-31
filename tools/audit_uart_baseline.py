"""Audit archived artifacts only. Never opens a board, UART or programmer."""
import argparse
import hashlib
import json
import platform
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = '4a254d2bd5846efccadd6d812eb0980abd28d1f6'
BIT_SHA = 'af68cf8f6b14e36257e764874a5c60645030aeba3b8667c9d56a0d6b9339c46e'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifacts', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    directory = args.artifacts
    checks = []

    def check(name, condition):
        checks.append({'name': name, 'passed': bool(condition)})
        if not condition:
            raise RuntimeError(name)

    bit = directory / 'zynq_uart_bridge_verified.bit'
    digest = hashlib.sha256(bit.read_bytes()).hexdigest()
    check('archived bitstream SHA-256', digest == BIT_SHA)
    motion = json.loads((directory / 'motion-test.json').read_text('utf-8'))
    check('historical motion script exit/result', motion['result'] == 'pass')
    check('historical final PWM disabled', motion['final_status']['ENABLED'] == '0')
    tx = [row['tx'] for row in motion['records'] if 'tx' in row]
    check('historical step/return order', tx == [
        'stop', '__link_probe__', 'st', 'pan 1550', 'pan 1500',
        'tlt 1550', 'tlt 1500', 'stop'])
    check('historical reverse error response', any(
        row.get('line', '').startswith('ERROR command') for row in motion['records']))
    program = (directory / 'program-console.log').read_text('utf-8', errors='replace')
    check('historical startup HIGH', 'End of startup status: HIGH' in program)
    check('historical program completion', '\nTEMPORARY_BRIDGE_PROGRAM_COMPLETED' in program)
    xdc_path = 'board/skystar_f407/zynq_uart_bridge_v12.xdc'
    xdc = (ROOT / xdc_path).read_text('utf-8')
    mapping = dict((port, pin) for pin, port in re.findall(
        r'PACKAGE_PIN (\w+) IOSTANDARD LVCMOS33\} \[get_ports (\w+)\]', xdc))
    check('four-port pin mapping', mapping == {
        'pc_rx': 'AA27', 'pc_tx': 'AA28', 'skystar_rx': 'AB26', 'skystar_tx': 'AB25'})
    sources = {}
    for path in ['src/rtl/zynq_uart_bridge.v', 'sim/zynq_uart_bridge_tb.v', xdc_path]:
        archived = subprocess.check_output(['git', 'show', BASE + ':' + path], cwd=ROOT)
        # Working trees may use CRLF; compare canonical text and hash Git bytes.
        check('baseline source unchanged: ' + path,
              archived.replace(b'\r\n', b'\n') == (ROOT/path).read_bytes().replace(b'\r\n', b'\n'))
        sources[path] = hashlib.sha256(archived).hexdigest()
    result = {
        'scope': 'offline audit of historical artifacts; no new hardware action',
        'base_source_commit': BASE, 'python': platform.python_version(),
        'audit_tool_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'bitstream_sha256': digest, 'bitstream_bytes': bit.stat().st_size,
        'historical_stm32_flash_sha256_recorded_not_reread':
            'b94c9e0edc1cac282dcf0a39fd765bacb4aa3957f9d5dd751c46d962ac6dcae8',
        'stm32_v14_candidate_flashed': False,
        'actual_current_flash_identity': 'unconfirmed; no fresh read authorized/performed',
        'j23_electrical_measurement': 'pending; LVCMOS33 is a constraint, not a measured voltage',
        'physical_package_speed_grade': 'unconfirmed; vendor reference xc7z100ffg900-2',
        'pin_mapping': mapping, 'source_git_blob_sha256': sources,
        'checks': checks, 'exit_code': 0,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print('PASS', len(checks), 'archived baseline checks; electrical/Flash identity remain pending')


if __name__ == '__main__':
    main()
