"""Reproduce stopped-session monotonicity in the existing host C model."""
import argparse
import binascii
import ctypes
import json
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--model-stage', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    lib = ctypes.CDLL(str((a.model_stage/'stm32.dll').absolute()))

    def drain():
        data = bytearray()
        while True:
            value = lib.model_transmit()
            if value < 0:
                return bytes(data)
            data.append(value)

    def wire(body):
        return (body+'*%04x\n' % binascii.crc_hqx(body.encode('ascii'),0xffff)).encode('ascii')

    def send(body):
        for byte in wire(body):
            lib.model_receive(byte,0)
            lib.model_foreground()
        return drain()

    def nonce():
        return '%08x%08x' % (lib.model_nonce_hi() & 0xffffffff,lib.model_nonce_lo() & 0xffffffff)

    lib.model_init(); drain(); initial = nonce()
    first = send('v2b '+initial+' 8000000000000000')
    assert b'V2A ' in first
    stop = send('s1q 00000000000000000000000000000001 stop')
    assert b'S1ACK Q ' in stop and b' stop ACCEPT REG ' in stop
    assert nonce()==initial and lib.model_state()==0
    older = send('v2b '+initial+' 5000000000000000')
    assert b'V2A ' not in older
    newer = send('v2b '+initial+' f000000000000000')
    assert b'V2A ' in newer
    result = {'verdict':'PASS', 'checks':['stopped_stop_keeps_nonce',
              'same_nonce_lower_session_no_ack', 'same_nonce_higher_session_ack'],
              'scope':'host C model; possible explanation, not proof of physical TX bytes',
              'hardware_actions':[]}
    a.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('OBSERVATION_REBIND_PASS checks=3')


if __name__=='__main__':
    main()
