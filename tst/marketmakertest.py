import unittest
import marketmaker


class MarketMakerTest(unittest.TestCase):
    def test_round_up_0_decimal(self):
        value = 4.13456
        self.assertEqual(5, marketmaker.round_up(value))

    def test_round_up_3_decimal(self):
        value = 4.45612389012
        self.assertEqual(4.457, marketmaker.round_up(value, 3))

    def test_round_up_5_decimal(self):
        value = 4.563
        self.assertEqual(4.563, marketmaker.round_up(value, 5))

    def test_round_up_6_decimal(self):
        value = 4.563000001
        self.assertEqual(4.563001, marketmaker.round_up(value, 6))

    def test_round_down_0_decimal(self):
        value = 4.63456
        self.assertEqual(4, marketmaker.round_down(value))

    def test_round_down_3_decimal(self):
        value = 4.45672389012
        self.assertEqual(4.456, marketmaker.round_down(value, 3))

    def test_round_down_5_decimal(self):
        value = 4.563
        self.assertEqual(4.563, marketmaker.round_down(value, 5))

    def test_round_down_6_decimal(self):
        value = 4.563000009
        self.assertEqual(4.563, marketmaker.round_down(value, 6))

unittest.main()
