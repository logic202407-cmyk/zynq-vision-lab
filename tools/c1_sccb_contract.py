"""Bind the SCCB constraint to reviewed private source, never guessed frequency."""
import argparse
import hashlib
import json
import re
from pathlib import Path

DRIVER_SHA256 = '3e5ceea17dd403f69f3245272a147227f9bb55ae8868d9dee95f20e1ec1e62ad'


def review_binding(text):
    text = re.sub(r'/\*.*?\*/|//[^\n]*', '', text, flags=re.S)
    values = {}
    for name, expected in [('CLK_FREQ', 50000000), ('I2C_FREQ', 250000)]:
        found = re.findall(r'\bparameter\s+' + name + r"\s*=\s*\d+'d([\d_]+)\s*;", text)
        if len(found) != 1 or int(found[0].replace('_', '')) != expected:
            raise ValueError('Unreviewed top parameter: ' + name)
        values[name] = expected
    instance = re.findall(r'\bi2c_dri\s*#\s*\((.*?)\)\s*u_i2c_dri\s*\((.*?)\)\s*;', text, re.S)
    if len(instance) != 1:
        raise ValueError('Expected exactly one reviewed SCCB instance')
    params, ports = instance[0]
    for name in values:
        if len(re.findall(r'\.' + name + r'\s*\(\s*' + name + r'\s*\)', params)) != 1:
            raise ValueError('Unreviewed instance parameter: ' + name)
    for name, net in [('clk', 'clk_50m'), ('dri_clk', 'i2c_dri_clk')]:
        if len(re.findall(r'\.' + name + r'\s*\(\s*' + net + r'\s*\)', ports)) != 1:
            raise ValueError('Unreviewed instance connection: ' + name)
    # Alternate elaboration overrides must not silently invalidate the derivation.
    if re.search(r'\bdefparam\b', text):
        raise ValueError('Defparam overrides require a new source review')
    return dict(parent_hz=values['CLK_FREQ'], sccb_bit_hz=values['I2C_FREQ'],
                divider=50, half_parent_cycles=25, period_ns=1000,
                source_pin='u_i2c_dri/dri_clk_reg/C',
                target_pin='u_i2c_dri/dri_clk_reg/Q', measured=False)


def inspect(vendor):
    driver = (vendor / 'rtl/ov5640/i2c_dri.v').read_bytes()
    top = (vendor / 'rtl/ov5640_udp_pc.v').read_bytes()
    if hashlib.sha256(driver).hexdigest() != DRIVER_SHA256:
        raise ValueError('Private SCCB driver differs from the reviewed fingerprint')
    result = review_binding(top.decode('latin1'))
    result['source_sha256'] = {'rtl/ov5640/i2c_dri.v': hashlib.sha256(driver).hexdigest(),
                               'rtl/ov5640_udp_pc.v': hashlib.sha256(top).hexdigest()}
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--vendor', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = inspect(args.vendor)
    except (ValueError, OSError) as error:
        parser.exit(2, str(error) + '\n')
    if args.output.exists():
        parser.exit(2, 'Fresh contract output required\n')
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print('SCCB_SOURCE_CONTRACT_PASS divide_by=50 parent_period=20ns')


if __name__ == '__main__':
    main()
