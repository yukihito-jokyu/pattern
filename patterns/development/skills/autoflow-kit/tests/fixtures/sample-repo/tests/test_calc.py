import unittest

import calc


class CalcTest(unittest.TestCase):
    def test_add(self) -> None:
        self.assertEqual(calc.add(2, 3), 5)

    def test_clamp_low(self) -> None:
        self.assertEqual(calc.clamp(-1, 0, 10), 0)
