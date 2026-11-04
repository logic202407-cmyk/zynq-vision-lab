"""Validate the selected F407 wiring metadata. No device access or enable code."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'src/prototype/skystar_openmv/stm32_skystar_tracking/user/gimbal_wiring.def'
# DS8626 Tables 7/9: limited to pins reviewed for this standalone board.
PWM_CAPABILITIES = {
    'PD12': ('TIM4', 1, 2), 'PD13': ('TIM4', 2, 2),
    'PD14': ('TIM4', 3, 2), 'PD15': ('TIM4', 4, 2),
    'PE9': ('TIM1', 1, 1), 'PE11': ('TIM1', 2, 1),
}
RX_CAPABILITIES = {
    'PA3': ('USART2', 7), 'PD6': ('USART2', 7),
    'PC7': ('USART6', 8), 'PD2': ('UART5', 8),
    'PC11': ('USART3', 7), 'PB11': ('USART3', 7),
}
RESERVED_PINS = {'PC10', 'PC11', 'PA0', 'PA9', 'PA10', 'PA13', 'PA14', 'PE2'}


def parse(text: str) -> tuple[list[tuple], list[tuple]]:
    pwm, rx = [], []
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
    for number, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        match = re.fullmatch(r'GIMBAL_PWM\((\d+),\s*(\d+),\s*(P[A-E]\d+),\s*(TIM\d+),\s*(\d+),\s*(\d+)\)', line)
        if match:
            g, axis, pin, timer, channel, af = match.groups()
            pwm.append((int(g), int(axis), pin, timer, int(channel), int(af)))
            continue
        match = re.fullmatch(r'GIMBAL_RX\((\d+),\s*(P[A-E]\d+),\s*(U(?:SART|ART)\d+),\s*(\d+)\)', line)
        if match:
            g, pin, uart, af = match.groups()
            rx.append((int(g), pin, uart, int(af)))
            continue
        raise ValueError(f'Unrecognized wiring row at stripped line {number}: {line}')
    return pwm, rx


def validate(pwm: list[tuple], rx: list[tuple], *, sdio_enabled: bool = False) -> list[str]:
    errors = []
    if [(p[0], p[1]) for p in pwm] != [(g, a) for g in range(3) for a in range(2)]:
        errors.append('PWM rows must contain ordered IDs 0..2, PAN=0 then TILT=1')
    if [r[0] for r in rx] != [0, 1, 2]:
        errors.append('RX rows must contain ordered IDs 0..2 exactly once')
    pins = [p[2] for p in pwm] + [r[1] for r in rx]
    if len(pins) != len(set(pins)):
        errors.append('Duplicate physical pin allocation')
    if set(pins) & RESERVED_PINS:
        errors.append('Pin conflicts with FPGA console, debug, KEY or existing output')
    channels = [(p[3], p[4]) for p in pwm]
    if len(channels) != len(set(channels)):
        errors.append('Duplicate timer channel allocation')
    uarts = [r[2] for r in rx]
    if len(uarts) != len(set(uarts)) or 'USART3' in uarts:
        errors.append('UART peripheral reused or conflicts with FPGA USART3')
    for _, _, pin, timer, channel, af in pwm:
        if PWM_CAPABILITIES.get(pin) != (timer, channel, af):
            errors.append(f'Unsupported PWM pin/channel/AF: {pin}')
    for _, pin, uart, af in rx:
        if RX_CAPABILITIES.get(pin) != (uart, af):
            errors.append(f'Unsupported RX pin/peripheral/AF: {pin}')
    if sdio_enabled:
        errors.append('TF/SDIO prohibited: PD2 and existing PC10/PC11 are allocated')
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=CONFIG)
    parser.add_argument('--sdio-enabled', action='store_true', help='Reject incompatible SDIO configuration')
    args = parser.parse_args()
    try:
        pwm, rx = parse(args.config.read_text(encoding='utf-8'))
        errors = validate(pwm, rx, sdio_enabled=args.sdio_enabled)
    except (OSError, ValueError) as exc:
        errors = [str(exc)]
    print(json.dumps({'scope': 'offline wiring metadata only', 'passed': not errors,
                      'errors': errors, 'hardware_tested': False}, indent=2))
    return int(bool(errors))


if __name__ == '__main__':
    raise SystemExit(main())
