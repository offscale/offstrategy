# -*- coding: utf-8 -*-
from collections import deque
from os import environ
from sys import version
from unittest import TestCase
from unittest import main as unittest_main

if version[0] == "2":
    from itertools import imap as map

from offstrategy.parser.env import parse_out_env


class TestParseEnv(TestCase):
    def test_env(self):
        environ["bar"] = "foo"
        input_strings = (
            'foo bar "env.bar" can haz',
            "env.bar",
            '"env.bar"',
            "'env.bar'",
            "'env.bar'}",
            '"env.bar"}',
            "",
            "env.",
        )
        deque(
            map(
                lambda input_s: self.assertEqual(
                    parse_out_env(input_s), input_s.replace("env.bar", environ["bar"])
                ),
                input_strings,
            ),
            maxlen=0,
        )

    def test_env_edge_case(self):
        environ["bar"] = "foo"
        self.assertEqual(
            *(lambda s: (parse_out_env(s), s.replace("env.bar", environ["bar"])))(
                "'env.bar'}"
            )
        )


if __name__ == "__main__":
    unittest_main()
