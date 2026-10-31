"""B2 coupled real XSim / C acceptance; simulation ports only."""
import argparse,ctypes as C,hashlib,json,os,shutil,subprocess,time,binascii
from collections import deque
from pathlib import Path
from xsim_c_bridge import XSim,Logic
ROOT=Path(__file__).resolve().parents[1]
FW=ROOT/'src/prototype/skystar_openmv/stm32_skystar_tracking'
VB=Path('D:/Vivado/Vivado/2024.2/bin')

def build(stage,auth_ms=30000,legacy=False):
    stage.mkdir(parents=True,exist_ok=False)
    sources=['uart_tx_8n1.v','uart_rx.v','zynq_motion_s1.v']
    for f in sources: shutil.copyfile(ROOT/'src/rtl'/f,stage/f)
    (stage/'motion_c_bridge_tb.v').write_text((ROOT/'sim/cosim/motion_c_bridge_tb.v').read_text().replace('AUTH_TEST_MS=30000','AUTH_TEST_MS='+str(auth_ms)))
    inputs=list((FW/'User').glob('*.[ch]'))+list((FW.parent/'stm32_project/User').glob('pid.[ch]'))
    inputs += [ROOT/'src/rtl'/f for f in sources]+[ROOT/'sim/cosim/stm32_adapter.c',ROOT/'sim/cosim/motion_c_bridge_tb.v',Path(__file__).resolve(),ROOT/'tools/xsim_c_bridge.py']
    (stage/'build-inputs.json').write_text(json.dumps({'auth_ms':auth_ms,'legacy':legacy,'sha256':{f.relative_to(ROOT).as_posix():hashlib.sha256(f.read_bytes()).hexdigest() for f in inputs}},indent=2))
    commands={
    'c-build':[r'D:\Dev-Cpp\MinGW64\bin\gcc.exe','-shared','-std=c99','-Wall','-Wextra','-Werror','-O2',
        '-DBOARD_HOST_TEST','-DS1ACK1','-DCONSOLE_USART=3','-I'+str(FW/'User'),
        '-I'+str(FW.parent/'stm32_project/User'),str(ROOT/'sim/cosim/stm32_adapter.c'),
        str(FW/'User/tracking.c'),str(FW/'User/safety.c'),str(FW.parent/'stm32_project/User/pid.c'),'-o',str(stage/'stm32.dll')],
    'xvlog':[str(VB/'xvlog.bat')]+sources+['motion_c_bridge_tb.v'],
    'xelab':[str(VB/'xelab.bat'),'motion_c_bridge_tb','-debug','all','-dll','-s','coupled']}
    if legacy:commands['c-build'].remove('-DS1ACK1')
    for name,cmd in commands.items():
        p=subprocess.run(cmd,cwd=stage,capture_output=True,timeout=120)
        (stage/(name+'.log')).write_bytes(p.stdout+p.stderr)
        if p.returncode: raise RuntimeError((name,p.returncode,p.stdout.decode(errors='replace'),p.stderr.decode(errors='replace')))

class Coupled:
    def __init__(self,stage):
        self.stage=stage;self.lib=C.CDLL(str(stage/'stm32.dll'))
        self.lib.model_reg.argtypes=[C.c_uint];self.lib.model_reg.restype=C.c_uint
        self.lib.model_init();self.sim=XSim(stage)
        self.port=self.sim.kernel.xsi_get_port_number(self.sim.handle,b'controls');assert self.port>=0
        self.controls=(1<<151)|(1<<152)|(1<<153)|(0x12345678<<23)
        self.us=0;self.status=0;self.rx_start=None;self.sample=0;self.index=0;self.value=0
        self.frame=None;self.frame_at=0;self.prev=0;self.to_mcu=[];self.from_mcu=[];self.rx=[];self.lines=[];self.line=bytearray()
        self.drop=False;self.disconnect=False;self.corrupt=False;self.trace=[]
        self.hold=False;self.held=[];self.replay=deque();self.mutate=None;self.in_line=bytearray();self.frame_hidden=False
        self.drive();self.advance(2);self.setbit(0,1)
    def drive(self):
        words=(Logic*5)(*[Logic((self.controls>>(32*i))&0xffffffff,0) for i in range(5)])
        self.sim.kernel.xsi_put_value(self.sim.handle,self.port,words)
    def setbit(self,n,v):
        self.controls=(self.controls&~(1<<n))|(v<<n);self.drive()
    def pulse(self,n):
        self.setbit(n,1);self.advance(2);self.setbit(n,0)
    def command(self,axis,value):
        self.controls=(self.controls&~(((1<<18)-1)<<5))|(axis<<5)|(value<<7);self.drive();self.pulse(3)
    def advance(self,n):
        for _ in range(n):
            self.us+=1;now=self.us*1000;p=self.sim.step();tx=p&1;self.status=(p>>1)&0xffffffff
            count=p>>73;data=(p>>65)&255
            if count!=self.prev: assert count==self.prev+1;self.rx.append(data);self.prev=count
            if self.us%1000==0:self.lib.model_tick()
            if self.rx_start is None and tx==0:
                self.rx_start=now;self.index=-1;self.value=0;self.sample=now+4340
            if self.rx_start is not None and now>=self.sample:
                if self.index==-1:
                    if tx:self.rx_start=None
                elif self.index<8:self.value|=tx<<self.index
                else:
                    self.to_mcu.append(self.value);self.line.append(self.value)
                    if self.value==10:self.lines.append(self.line.decode());self.line.clear()
                    if not self.disconnect:self.lib.model_receive(self.value,not tx)
                    self.rx_start=None
                self.index+=1;self.sample+=8680
            self.lib.model_foreground()
            if self.frame is not None and now>=self.frame_at+86800:self.frame=None
            if self.frame is None:
                if self.replay:
                    b=self.replay.popleft();self.frame_hidden=False
                else:
                    b=self.lib.model_transmit();self.frame_hidden=False
                    if b>=0:
                        self.from_mcu.append(b)
                        if self.hold:
                            self.held.append(b);self.frame_hidden=True
                        elif self.mutate:
                            self.in_line.append(b);self.frame_hidden=True
                            if b==10:
                                data=bytes(self.in_line);self.in_line.clear()
                                if data.startswith(b'S1ACK S '):
                                    body=data.split(b'*')[0].split()
                                    if self.mutate=='sequence':body[3]=b'99'
                                    elif self.mutate=='nonce':body[2]=b'ffffffffffffffff'
                                    elif self.mutate=='target':body[12]=b'1600'
                                    elif self.mutate=='opcode':body[5]=b'pan'
                                    elif self.mutate=='request_crc':body[4]=b'0000'
                                    text=b' '.join(body);data=text+b'*%04x\n'%binascii.crc_hqx(text,0xffff)
                                elif data.startswith(b'S1SYNC ') and self.mutate=='query_id':
                                    body=data.split(b'*')[0].split();body[1]=b'0'*32
                                    text=b' '.join(body);data=text+b'*%04x\n'%binascii.crc_hqx(text,0xffff)
                                self.replay.extend(data)
                        if self.corrupt and b==42:b=43
                if b>=0:self.frame=(1<<9)|(b<<1);self.frame_at=now
            level=1 if self.frame is None or self.drop or self.frame_hidden else (self.frame>>int((now-self.frame_at)//8680))&1
            self.sim.drive(level)
            if self.us%1000==0:self.trace.append([self.us,self.status,self.lib.model_state(),self.lib.model_reg(0x40000820),self.lib.model_pan(),self.lib.model_tilt()])
    @property
    def state(self):return self.status&15
    @property
    def accepts(self):return self.status>>16
    def until(self,test,budget=150000):
        start=self.us
        while not test():
            if self.us-start>=budget:raise AssertionError(('deadline',self.us,self.status,self.lines,bytes(self.from_mcu).decode(errors='replace')))
            self.advance(100)
    def sync(self):
        self.advance(10000);assert not self.to_mcu
        self.pulse(1);self.until(lambda:self.state==3);assert self.lib.model_state()==0
    def arm(self):
        self.pulse(2);self.until(lambda:self.state==4);assert self.lib.model_state()==1
        assert self.lib.model_reg(0x40000820)==0
    def move(self,axis,value):
        old=self.accepts;self.command(axis,value);self.until(lambda:self.accepts>old)
        assert self.state==4 and self.lib.model_reg(0x40000820)==17
    def stop(self):
        self.pulse(4);self.until(lambda:bool(self.status&64));assert self.lib.model_reg(0x40000820)==0
    def close(self):self.sim.close()

def main():
    a=argparse.ArgumentParser();a.add_argument('--stage',type=Path,required=True);a.add_argument('--built',action='store_true');a.add_argument('--case',default='normal');a.add_argument('--auth-ms',type=int,default=30000);a.add_argument('--legacy',action='store_true');args=a.parse_args();stage=args.stage.absolute()
    assert str(stage).isascii() and ROOT not in stage.resolve().parents
    if not args.built:build(stage,args.auth_ms,args.legacy)
    def frame(body):return body+'*%04x\n'%binascii.crc_hqx(body.encode(),0xffff)
    assert binascii.crc_hqx(b'123456789',0xffff)==0x29b1
    assert frame('s1 1234567887654321 0 arm')=='s1 1234567887654321 0 arm*be15\n'
    initial=[frame('s1q 00000000000000000000000012345678 st'),frame('s1q 00000000000000000000000012345679 st'),frame('s1 1234000112340002 0 arm'),frame('s1 1234000112340002 1 pan 1550')]
    normal=initial+[frame('s1 1234000112340002 %d %s'%(n,p)) for n,p in enumerate(['tlt 1550','pan 1500','tlt 1500','pan 1540','tlt 1530','home','hb'],2)]+[frame('s1q 0000000000000000000000001234567a stop')]
    (stage/('expected-'+args.case+'.json')).write_text(json.dumps({'case':args.case,'initial':initial,'normal':normal if args.case=='normal' else None},indent=2))
    started=time.monotonic();c=Coupled(stage)
    try:
        if args.case=='normal':
            c.sync();c.arm();c.move(0,1550);assert c.lib.model_pan()==1550 and c.lib.model_tilt()==1500
            c.move(1,1550);assert c.lib.model_pan()==1550 and c.lib.model_tilt()==1550
            c.move(0,1500);c.move(1,1500);c.move(0,1540);c.move(1,1530);c.move(2,1500)
            before=c.accepts;c.advance(140000);assert c.accepts>before
            c.stop();c.advance(30000);assert c.rx==c.from_mcu
        elif args.case in ('legacy','stale_sync','sync_crc'):
            c.advance(10000)
            if args.case=='stale_sync':c.mutate='query_id'
            if args.case=='sync_crc':c.corrupt=True
            c.pulse(1);c.advance(270000)
            assert c.state==6 and c.lib.model_reg(0x40000820)==0
            assert all(x.startswith('s1q ') for x in c.lines)
        else:
            c.sync();c.arm();c.move(0,1550)
            before=c.accepts
            if args.case=='ack_loss':
                c.drop=True;c.command(1,1540);c.advance(270000)
                assert c.state==6 and c.accepts==before and not(c.status&64)
                assert c.lib.model_reg(0x40000820)==0
                assert sum(' tlt ' in x for x in c.lines)==1
                c.drop=False;c.advance(150000);assert c.state==6
            elif args.case=='late_ack':
                c.hold=True;c.command(1,1540);c.advance(270000)
                assert c.state==6 and c.accepts==before
                c.hold=False;c.replay.extend(c.held);c.held.clear();c.advance(100000)
                assert c.state==6 and c.accepts==before and c.lib.model_reg(0x40000820)==0
            elif args.case.startswith('mismatch_'):
                c.mutate=args.case[9:];c.command(1,1540);c.advance(270000)
                assert c.state==6 and c.lib.model_reg(0x40000820)==0
                assert c.accepts<=before+1 # only correlated stop may succeed
                assert sum(' tlt ' in x for x in c.lines)==1
            elif args.case=='recovery':
                c.command(0,1701);c.until(lambda:c.state==6)
                c.advance(20000);assert c.lib.model_reg(0x40000820)==0
                c.controls=(c.controls&~(((1<<128)-1)<<23))|(0xabcdef1234<<23);c.drive();c.pulse(1)
                c.until(lambda:c.state==3);c.advance(120000)
                assert c.lib.model_reg(0x40000820)==0
                c.arm();c.move(1,1530);c.stop()
            elif args.case=='link_loss':
                c.drop=True;c.disconnect=True;c.command(1,1540);c.advance(520000)
                assert c.state==6 and c.lib.model_state()==4 and c.lib.model_reg(0x40000820)==0
                c.drop=False;c.disconnect=False;c.advance(150000)
                assert c.state==6 and c.lib.model_reg(0x40000820)==0
            elif args.case=='bad_ack_crc':
                c.corrupt=True;c.command(1,1540);c.advance(270000)
                assert c.state==6 and c.accepts==before and c.lib.model_reg(0x40000820)==0
            elif args.case=='fpga_reset':
                count=len(c.lines);c.setbit(0,0);c.advance(20);c.setbit(0,1);c.advance(520000)
                assert len(c.lines)==count and c.lib.model_state()==4 and c.lib.model_reg(0x40000820)==0
            elif args.case=='mcu_reset':
                c.lib.model_reboot();c.advance(270000)
                assert c.status&32 and c.lib.model_reg(0x40000820)==0
                assert sum(' arm*' in x for x in c.lines)==1
            elif args.case=='busy_repeat':
                old=len(c.lines);c.command(1,1540);c.advance(500)
                for _ in range(5):c.command(0,1600);c.pulse(2)
                c.until(lambda:c.accepts>before);assert c.lib.model_pan()==1550 and c.lib.model_tilt()==1540
                assert len(c.lines)==old+1;c.stop()
            elif args.case=='pc_handoff':
                c.setbit(151,0);c.until(lambda:bool(c.status&64));c.until(lambda:not(c.status&16))
                assert c.lib.model_reg(0x40000820)==0
            elif args.case=='auth_expiry':
                assert args.auth_ms==300
                c.advance(350000);assert c.status&64 and c.lib.model_reg(0x40000820)==0
                old=len(c.lines);c.advance(150000);assert len(c.lines)==old
            elif args.case=='handoff_unconfirmed':
                c.drop=True;c.setbit(151,0);c.advance(270000)
                assert c.state==6 and c.status&16 and not(c.status&64)
            elif args.case=='boundaries':
                for axis in (0,1):
                    for value in (1300,1700):
                        c.move(axis,value)
                        assert (c.lib.model_pan() if axis==0 else c.lib.model_tilt())==value
                c.stop()
            elif args.case=='range':
                c.command(0,1701);c.until(lambda:c.state==6);assert c.lib.model_reg(0x40000820)==0
                assert not any('1701' in x for x in c.lines)
            else:raise ValueError(args.case)
        if args.case not in ('legacy','stale_sync','sync_crc'):assert c.lines[:4]==initial
        if args.case=='normal':assert c.lines==normal
        for line in c.lines:
            body,crc=line.rstrip().split('*');assert int(crc,16)==binascii.crc_hqx(body.encode(),0xffff)
        result={'pass' :'B2_COUPLED_PASS','case':args.case,'simulated_us':c.us,'wall_seconds':time.monotonic()-started,
                'requests':c.lines,'response':bytes(c.from_mcu).decode(),'accepts':c.accepts,'exit_code':0,'hardware_actions':[]}
        (stage/('result-'+args.case+'.json')).write_text(json.dumps(result,indent=2));(stage/('trace-'+args.case+'.json')).write_text(json.dumps(c.trace))
        print(json.dumps(result,indent=2))
    finally:
        (stage/('observed-'+args.case+'.json')).write_text(json.dumps({'us':c.us,'status':c.status,'requests':c.lines,'response':bytes(c.from_mcu).decode(errors='replace'),'trace':c.trace},indent=2))
        c.close()
if __name__=='__main__':main()
