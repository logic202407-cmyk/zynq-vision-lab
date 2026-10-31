"""Optional wire-edge recording around the existing acceptance runner (no force)."""
import json,sys
from pathlib import Path
import check_motion_cosim as test
Base=test.Coupled
class Recorded(Base):
    def __init__(self,stage):
        super().__init__(stage)
        self.edges=[];self.last_tx=1;self.last_rx=1
        step=self.sim.step;drive=self.sim.drive
        def observed_step():
            value=step();tx=value&1
            if tx!=self.last_tx:self.edges.append([self.us,'FPGA_TX',tx]);self.last_tx=tx
            return value
        def observed_drive(value):
            if value!=self.last_rx:self.edges.append([self.us,'MCU_TX',value]);self.last_rx=value
            drive(value)
        self.sim.step=observed_step;self.sim.drive=observed_drive
    def close(self):
        (self.stage/'wire-edges.json').write_text(json.dumps({'resolution_us':1,'edges':self.edges},separators=(',',':')))
        super().close()
test.Coupled=Recorded
if __name__=='__main__':test.main()
