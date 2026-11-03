"""Exercise real C F1 feedback in STOPPED state, using synthetic UART/registers.

No Vivado, ARM compiler, physical serial port, SWD, or hardware access. A fresh
output directory is required; failure is recorded and returns a nonzero exit.
"""
import argparse
import binascii
import ctypes
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.pc.vision_measurement import Measurement

FW = ROOT / 'src/prototype/skystar_openmv/stm32_skystar_tracking'


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def run(stage, cc):
    stage.mkdir(parents=True, exist_ok=False)
    checks, wire = [], []
    result = {'verdict': 'FAIL', 'scope': 'real C with synthetic host registers only',
              'hardware_actions': [], 'checks': checks}
    try:
        sources = [ROOT / 'sim/c1/feedback_probe.c'] + [
            FW / 'User' / name for name in
            ('tracking.c', 'safety.c', 'gimbal_registry.c', 'vision_measurement.c')]
        sources.append(FW.parent / 'stm32_project/User/pid.c')
        library = stage / 'feedback.dll'
        command = [cc, '-shared', '-std=c99', '-Wall', '-Wextra', '-Werror', '-O2',
                   '-DBOARD_HOST_TEST', '-DS1ACK1', '-DC1_OBSERVATIONS',
                   '-DC1_CLOSED_LOOP', '-DCONSOLE_USART=3',
                   '-I' + str(FW / 'User'), '-I' + str(FW.parent / 'stm32_project/User'),
                   *map(str, sources), '-o', str(library)]
        compiled = subprocess.run(command, capture_output=True, timeout=120)
        (stage / 'compile.txt').write_bytes(compiled.stdout + compiled.stderr)
        require(compiled.returncode == 0, 'C compilation failed; see compile.txt')
        result['compiler'] = subprocess.check_output([cc, '--version'], text=True).splitlines()[0]
        inputs = set(sources + list((FW / 'User').glob('*.[ch]')) + [
            FW.parent / 'stm32_project/User/pid.h', Path(__file__).resolve(),
            ROOT / 'sim/c1/loop_adapter.c', ROOT / 'sim/c1/link_adapter.c',
            ROOT / 'sim/cosim/stm32_adapter.c', ROOT / 'src/pc/vision_measurement.py'])
        result['source_sha256'] = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                                   for p in sorted(inputs)}
        lib = ctypes.CDLL(str(library))
        for name in ('model_nonce_hi', 'model_nonce_lo'):
            getattr(lib, name).restype = ctypes.c_uint32

        def drain():
            data = bytearray()
            while True:
                value = lib.model_transmit()
                if value < 0:
                    break
                data.append(value)
            lines = data.decode('ascii').splitlines()
            wire.extend(lines)
            return lines

        def off():
            require(lib.model_reg(0x40000820) == 0, 'PWM register unexpectedly enabled')
            require(lib.model_state() in (0, 4), 'unexpected armed/manual/auto state')

        def feed(data, vision=False):
            receive = lib.model_vision_receive if vision else lib.model_receive
            for byte in data:
                receive(byte, 0)
                lib.model_foreground()
                off()

        def advance(ms):
            for _ in range(ms):
                lib.model_tick()
                lib.model_foreground()
                off()
            drain()

        def reset(bound=True):
            lib.feedback_probe_reset()
            drain()
            if bound:
                body = ('v2b %08x%08x %016x' %
                        (lib.model_nonce_hi(), lib.model_nonce_lo(), 1)).encode()
                feed(body + ('*%04x\n' % binascii.crc_hqx(body, 0xffff)).encode())
                ack = drain()
                require(any(s.startswith('V2A ') for s in ack) and lib.c1_bound(), 'binding failed')
            advance(60)

        def primary(count=64):
            feed(Measurement(0, 3, 1, 1, 1, 1, 0, 640, 480,
                             count, count * 100, count * 100, 96, 96, 103, 103, 100, 100).line())
            require(lib.c1_accepted() == 1, 'M2 rejected')
            drain()

        def frame(valid=1, expected=None):
            feed(struct.pack('<BBhhBB', 0xaa, 0xff, 20 if valid else 0,
                             -10 if valid else 0, valid, 0xee), vision=True)
            lines = [s for s in drain() if s.startswith('F1 ')]
            if expected is None:
                require(not lines, 'unexpected F1')
            else:
                require(len(lines) == 1, 'expected exactly one F1')
                body, crc = lines[0].split('*')
                require(len(body) == 49 and int(crc, 16) == binascii.crc_hqx(body.encode(), 0xffff), 'F1 CRC/length')
                fields = body.split()
                require(int(fields[1], 16) == 1 and int(fields[-1], 16) == expected, 'F1 session/validity')
                require(int(fields[2], 16) == lib.loop_vision_frames(), 'F1 OpenMV sequence')
                require(int(fields[3], 16) == lib.c1_sequence(), 'F1 primary sequence')
                require(fields[4:6] == (['0014', 'fff6'] if valid else ['0000', '0000']), 'F1 coordinates')
            off()

        reset(False); frame(); checks.append('unbound_session_suppresses_F1')
        reset(); primary(); frame(expected=1); checks.append('stopped_bound_valid_F1_without_ARM')
        frame(); checks.append('valid_F1_rate_limited_inside_50ms')
        frame(0, expected=0); checks.append('no_target_emits_invalid_F1_without_rate_limit')
        advance(50); frame(expected=1); checks.append('valid_F1_resumes_at_50ms')
        reset(); frame(expected=0); checks.append('missing_primary_emits_invalid_F1')
        reset(); primary(1); frame(expected=0); checks.append('sparse_primary_emits_invalid_F1')
        reset(); primary(); advance(200); frame(expected=0); checks.append('stale_primary_emits_invalid_F1')
        reset(); primary()
        feed(b'\xaa\xff\x14\x00', vision=True)
        require(not any(s.startswith('F1 ') for s in drain()), 'partial frame emitted F1')
        checks.append('partial_OpenMV_frame_silent')
        reset(); primary(); lib.model_tx_fill()
        require(lib.feedback_probe_tx_free() < 320, 'TX pressure not injected')
        frame(); checks.append('TX_reserve_suppresses_F1')
        frame(expected=1); checks.append('F1_recovers_after_TX_drain')
        reset(); primary(); old_nonce = lib.model_nonce_lo()
        lib.feedback_probe_key(1); lib.model_tick(); lib.model_foreground()
        lib.feedback_probe_key(0); drain()
        require(lib.model_state() == 4 and lib.model_reason() == 7, 'KEY fault not latched')
        require(lib.model_nonce_lo() != old_nonce and not lib.c1_bound(), 'KEY did not revoke session')
        frame(); checks.append('KEY_rotates_nonce_revokes_binding_and_suppresses_F1')
        feed(b'stop\n'); drain()
        require(lib.model_state() == 4 and not lib.c1_bound(), 'STOP cleared fault/session')
        frame(); checks.append('STOP_does_not_clear_KEY_or_restore_F1')
        result['verdict'] = 'PASS'
        result['checks_count'] = len(checks)
    except Exception:
        result['error'] = traceback.format_exc()
    (stage / 'wire.json').write_text(json.dumps(wire, indent=2) + '\n', encoding='utf-8')
    (stage / 'result.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(result['verdict'], len(checks), 'checks;', stage)
    if result['verdict'] != 'PASS':
        print(result['error'], file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', type=Path, required=True)
    parser.add_argument('--cc', default=os.environ.get('CC') or shutil.which('gcc') or 'gcc')
    args = parser.parse_args()
    sys.exit(run(args.stage.resolve(), args.cc))
