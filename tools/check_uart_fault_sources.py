"""Host-only fault-source regression; never opens a physical device."""
import argparse
import ctypes as c
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / 'src/prototype/skystar_openmv/stm32_skystar_tracking'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', required=True, type=Path)
    args = parser.parse_args()
    args.stage.mkdir(parents=True, exist_ok=False)
    pid = FW.parent / 'stm32_project/user'
    dll = args.stage / 'uart_probe.dll'
    cmd = [os.environ.get('CC', 'C:/msys64/ucrt64/bin/gcc.exe'), '-shared', '-std=c99',
           '-Wall', '-Wextra', '-Werror', '-O2', '-DBOARD_HOST_TEST', '-DS1ACK1',
           '-DC1_OBSERVATIONS', '-DC1_CLOSED_LOOP', '-DSKYSTAR_TEAM_PROFILE',
           '-DCONSOLE_USART=3', '-I' + str(FW / 'user'), '-I' + str(pid),
           str(ROOT / 'sim/c1/uart_fault_probe.c'),
           *[str(FW / 'user' / n) for n in ('tracking.c', 'safety.c', 'gimbal_registry.c',
                                            'vision_measurement.c', 'laser_lock.c')],
           str(pid / 'pid.c'), '-o', str(dll)]
    p = subprocess.run(cmd, capture_output=True)
    (args.stage / 'compile.log').write_bytes(p.stdout + p.stderr)
    if p.returncode:
        raise RuntimeError('compiler exit %d' % p.returncode)
    lib = c.CDLL(str(dll)); lib.model_reg.argtypes = [c.c_uint]; lib.model_reg.restype = c.c_uint
    lib.inject_uart.argtypes = [c.c_uint, c.c_uint, c.c_uint]
    lib.uart_fault_field.argtypes = [c.c_uint]; lib.uart_fault_field.restype = c.c_uint
    cases = []
    for port in (2, 3):
        for name, flags in (('parity', 1), ('framing', 2), ('noise', 4), ('overrun', 8)):
            lib.model_init(); assert lib.uart_fault_field(0) == 0xffffffff
            lib.model_tick(); lib.inject_uart(port, flags | 32, 0x55)
            assert lib.model_reg(0x40000820) == 0
            assert [lib.uart_fault_field(i) for i in range(4)] == [port, flags, 0, 1]
            lib.model_foreground()
            assert lib.model_state() == 4 and lib.model_reason() == 6
            lib.inject_uart(3 if port == 2 else 2, 40, 0x55); lib.model_foreground()
            assert lib.model_state() == 4 and lib.model_reg(0x40000820) == 0
            assert [lib.uart_fault_field(i) for i in range(4)] == [port, flags, 0, 1]
            cases.append('usart%d_%s_latched' % (port, name))
        lib.model_init()
        for _ in range(256):
            lib.inject_uart(port, 32, 0x55)
        assert [lib.uart_fault_field(i) for i in range(3)] == [port, 0, 1]
        lib.model_foreground()
        assert lib.model_state() == 4 and lib.model_reason() == 6
        lib.inject_uart(port, 32, 0x55); lib.model_foreground()
        assert lib.model_state() == 4
        assert lib.model_reg(0x40000820) == 0
        cases.append('usart%d_queue_overflow_latched' % port)
    result = {'verdict': 'PASS', 'cases': cases, 'count': len(cases),
              'scope': 'actual C with host register model; no hardware or concurrency timing proof',
              'compile_exit': p.returncode}
    (args.stage / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
