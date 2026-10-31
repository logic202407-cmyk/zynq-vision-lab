"""XSim 2024.2 XSI bindings based on installed xsi.h; simulation ports only."""
import ctypes as C
import os
from pathlib import Path


class Logic(C.Structure):
    _fields_=[('a',C.c_uint32),('b',C.c_uint32)]


class Setup(C.Structure):
    _fields_=[('log',C.c_char_p),('wdb',C.c_char_p),('directory',C.c_char_p)]


class XSim:
    def __init__(self, stage):
        self.cwd=Path.cwd()
        os.chdir(stage)
        base=Path('D:/Vivado/Vivado/2024.2')
        self.paths=[os.add_dll_directory(str(base/'lib/win64.o')),
                    os.add_dll_directory(str(base/'bin/unwrapped/win64.o'))]
        self.kernel=C.CDLL(str(base/'lib/win64.o/xv_simulator_kernel.dll'))
        self.design=C.CDLL(str(stage/'xsim.dir/coupled/xsimk.dll'))
        self.design.xsi_open.argtypes=[C.POINTER(Setup)];self.design.xsi_open.restype=C.c_void_p
        specs={'xsi_get_port_number':([C.c_void_p,C.c_char_p],C.c_int),
               'xsi_get_int':([C.c_void_p,C.c_int],C.c_int),
               'xsi_run':([C.c_void_p,C.c_int64],None),
               'xsi_get_value':([C.c_void_p,C.c_int,C.c_void_p],C.c_int),
               'xsi_put_value':([C.c_void_p,C.c_int,C.c_void_p],None),
               'xsi_get_status':([C.c_void_p],C.c_int),
               'xsi_close':([C.c_void_p],None)}
        for n,(a,r) in specs.items():
            f=getattr(self.kernel,n);f.argtypes=a;f.restype=r
        setup=Setup(b'xsi.log',None,None)
        self.handle=self.design.xsi_open(C.byref(setup))
        assert self.handle
        assert self.kernel.xsi_get_int(self.handle,2)==-12,'Expected picosecond precision'
        self.input=self.kernel.xsi_get_port_number(self.handle,b'mcu_rx')
        self.output=self.kernel.xsi_get_port_number(self.handle,b'bridge_sample')
        assert self.input>=0 and self.output>=0
        self.drive(1)

    def drive(self,value):
        v=Logic(value,0)
        self.kernel.xsi_put_value(self.handle,self.input,C.byref(v))

    def step(self):
        self.kernel.xsi_run(self.handle,1000000) # 1 us in 1 ps resolution
        assert self.kernel.xsi_get_status(self.handle)==1,'XSim abnormal status'
        values=(Logic*4)()
        self.kernel.xsi_get_value(self.handle,self.output,values)
        assert all(v.b==0 for v in values),'Unknown X/Z XSim port value'
        return sum(v.a<<(32*i) for i,v in enumerate(values))

    def close(self):
        self.kernel.xsi_close(self.handle)
        os.chdir(self.cwd)
