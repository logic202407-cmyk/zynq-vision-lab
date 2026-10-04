"""Sixteen independent mathematical groups, adapted to the frozen reference."""
import unittest

from tools.check_pc_r0_cases import check_group, load_fixture


class IndependentR0Cases(unittest.TestCase):
    pass


def group_test(doc, case):
    def test(self):
        for result in check_group(doc, case):
            with self.subTest(check=result["id"]):
                self.assertTrue(result["passed"], result)
    return test


DOCUMENT = load_fixture()
for CASE in DOCUMENT["cases"]:
    setattr(IndependentR0Cases, f"test_{CASE['id']}", group_test(DOCUMENT, CASE))


if __name__ == "__main__":
    unittest.main()
