"""Cross-tool comparison must catch corruption without widening tolerance."""
import copy
import unittest
from tools.stm32_s04_crosscheck import compare


class CrosscheckTests(unittest.TestCase):
    def setUp(self):
        self.reference = [dict(id="sample", passed=True, actual=dict(value=1.0, valid=1))]
        self.actual = copy.deepcopy(self.reference)

    def test_small_float_difference_uses_original_tolerance(self):
        self.actual[0]["actual"]["value"] += 0.000009
        self.assertLess(compare(self.reference, self.actual)["max_abs_delta"], 0.00001)

    def test_large_float_difference_rejected(self):
        self.actual[0]["actual"]["value"] += 0.000011
        with self.assertRaisesRegex(ValueError, "tolerance exceeded"):
            compare(self.reference, self.actual)

    def test_integer_difference_rejected(self):
        self.actual[0]["actual"]["valid"] = 0
        with self.assertRaisesRegex(ValueError, "exact field differs"):
            compare(self.reference, self.actual)

    def test_nonfinite_not_accepted(self):
        self.actual[0]["actual"]["value"] = float("nan")
        with self.assertRaisesRegex(ValueError, "non-finite"):
            compare(self.reference, self.actual)

    def test_missing_case_rejected(self):
        with self.assertRaisesRegex(ValueError, "case identities"):
            compare(self.reference, [])

    def test_duplicate_case_rejected(self):
        with self.assertRaisesRegex(ValueError, "case identities"):
            compare(self.reference, self.actual * 2)

    def test_failed_case_rejected(self):
        self.actual[0]["passed"] = False
        with self.assertRaisesRegex(ValueError, "failed case"):
            compare(self.reference, self.actual)

    def test_missing_field_rejected(self):
        del self.actual[0]["actual"]["valid"]
        with self.assertRaisesRegex(ValueError, "snapshot fields"):
            compare(self.reference, self.actual)
