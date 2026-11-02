"""Original synthetic top fixtures; no vendor source is embedded."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('sccb_contract', Path(__file__).resolve().parents[1] / 'tools/c1_sccb_contract.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
TOP = """parameter CLK_FREQ=27'd50_000_000;
parameter I2C_FREQ=20'd250_000;
i2c_dri #(.CLK_FREQ(CLK_FREQ),.I2C_FREQ(I2C_FREQ))
u_i2c_dri(.clk(clk_50m),.dri_clk(i2c_dri_clk));"""


class SCCBContractTests(unittest.TestCase):
    def test_reviewed_binding(self):
        result = module.review_binding(TOP)
        self.assertEqual((result['divider'], result['half_parent_cycles'], result['period_ns']), (50, 25, 1000))
        self.assertFalse(result['measured'])

    def test_reject_clock_rate_change(self):
        with self.assertRaises(ValueError): module.review_binding(TOP.replace('50_000_000', '100_000_000'))

    def test_reject_bus_rate_change(self):
        with self.assertRaises(ValueError): module.review_binding(TOP.replace('250_000', '400_000'))

    def test_reject_clock_rewire(self):
        with self.assertRaises(ValueError): module.review_binding(TOP.replace('.clk(clk_50m)', '.clk(clk_200m)'))

    def test_reject_literal_instance_override(self):
        with self.assertRaises(ValueError): module.review_binding(TOP.replace('.I2C_FREQ(I2C_FREQ)', ".I2C_FREQ(20'd400000)"))

    def test_reject_duplicate_instance(self):
        with self.assertRaises(ValueError): module.review_binding(TOP + TOP)

    def test_reject_alternate_override(self):
        with self.assertRaises(ValueError): module.review_binding(TOP + '\ndefparam u_i2c_dri.I2C_FREQ=400000;')

    def test_comments_do_not_supply_binding(self):
        with self.assertRaises(ValueError): module.review_binding('/*' + TOP + '*/')
