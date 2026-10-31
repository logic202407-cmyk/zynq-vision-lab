"""Offline S1 encoder/status decoder. Does not import or open serial hardware."""
import argparse
import binascii
import re


def encode(nonce, sequence, payload):
    if not 0 < nonce < 2**64 or not 0 <= sequence < 2**32:
        raise ValueError('nonce/sequence out of range')
    if payload not in ('arm', 'hb', 'home', 'auto'):
        match = re.fullmatch(r'(pan|tlt) ([0-9]{4})', payload)
        if not match or not 1300 <= int(match[2]) <= 1700:
            raise ValueError('unsupported payload/pulse')
    if (payload == 'arm') != (sequence == 0):
        raise ValueError('arm requires sequence zero; other commands require positive sequence')
    body = f's1 {nonce:016x} {sequence} {payload}'.encode('ascii')
    return body + f'*{binascii.crc_hqx(body, 0xffff):04x}\n'.encode('ascii')


def status(line):
    parts = line.strip().split()
    names = ['SAFE', 'WHY', 'NONCE', 'SEQ', 'TX_DROP', 'FW']
    if len(parts) != 13 or parts[0] != 'S1STAT' or parts[1::2] != names:
        raise ValueError('not a complete S1STAT frame')
    values = dict(zip(names, parts[2::2]))
    if values['SAFE'] not in ('stopped', 'armed', 'manual', 'auto', 'fault'):
        raise ValueError('unknown safety state')
    if values['WHY'] not in ('boot', 'stop', 'ready', 'link_timeout', 'stale',
                             'parse', 'uart', 'key', 'vision', 'entropy'):
        raise ValueError('unknown safety reason')
    if not re.fullmatch('[0-9a-f]{16}', values['NONCE']) or values['FW'] != '15':
        raise ValueError('invalid nonce or firmware version')
    for key in ('SEQ', 'TX_DROP'):
        if not re.fullmatch('[0-9]+', values[key]) or not 0 <= int(values[key]) < 2**32:
            raise ValueError('invalid counter')
    return values


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--nonce', required=True, type=lambda s: int(s, 16))
    parser.add_argument('--sequence', required=True, type=int)
    parser.add_argument('payload')
    args = parser.parse_args()
    print(encode(args.nonce, args.sequence, args.payload).decode('ascii'), end='')
