from unittest import TestCase, main as unittest_main
from json import dumps
from os import path

from offstrategy.Strategy import Strategy


class TestStrategy(TestCase):
    strategy = Strategy(path.join(path.dirname(__file__), '..', 'config', 'strategy.sample.json'))
    multi_options_mock = {'options': ['foo', 'bar'], 'pick': 'first'}

    def test_get_next_option0(self):
        self.assertRaises(ValueError, lambda: self.strategy._get_next_option(
            {'options': [], 'pick': 'first'}
        ))

    def test_get_next_option_offset_0(self):
        self.assertEqual(self.strategy._get_next_option(self.multi_options_mock, offset=0), 'foo')

    def test_get_next_option_offset_1(self):
        self.assertEqual(self.strategy._get_next_option(self.multi_options_mock, offset=1), 'bar')

    def test_get_next_option_offset_2(self):
        self.assertRaises(ValueError,
                          lambda: self.strategy._get_next_option(self.multi_options_mock, offset=2))


if __name__ == '__main__':
    unittest_main()
