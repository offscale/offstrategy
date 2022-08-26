from __future__ import print_function

import json
from sys import version
from unittest import TestCase
from unittest import main as unittest_main

from etcd3 import client
from six import b, u

if version[0] == "2":
    from httplib import HTTPException
else:
    from http.client import HTTPException

from libcloud.compute.base import NodeDriver, NodeImage, NodeSize
from libcloud.compute.drivers.dummy import DummyNodeDriver
from offutils import ping_port, raise_f
from offutils_strategy_register import (
    del_node_info,
    dict_to_node,
    get_node_info,
    node_to_dict,
    save_node_info,
)


class TestEtcdNodeRavel(TestCase):
    node = DummyNodeDriver("").create_node(
        image=NodeImage(driver=NodeDriver(key=""), id="", name=""),
        name="",
        size=NodeSize(
            bandwidth=None,
            disk=0,
            driver=NodeDriver(key=""),
            id="",
            name="",
            price=0.0,
            ram=0,
        ),
    )

    @classmethod
    def setUpClass(cls):
        # TODO: Mock all tests so etcd doesn't need to be running
        (
            lambda res: res
            if res is True
            else raise_f(
                HTTPException, "Failed to connect to etcd, errno: {}".format(res)
            )
        )(ping_port(port=2379))
        cls.client = client(port=2379)

    def test_0_put(self):
        """Can set an initial value"""
        self.assertIsNotNone(save_node_info(self.node.name, self.node))

    def test_newkey(self):
        """Can set a new value. Sanity check of the internal client library."""
        d = {
            "action": "set",
            "node": {
                "expiration": "2013-09-14T00:56:59.316195568+02:00",
                "modifiedIndex": 183,
                "key": u("/testkey"),
                "ttl": 19,
                "value": "test0",
            },
        }

        res = self.client.put(d["node"]["key"], d["node"]["value"])
        zeroth = res.header.revision
        d["node"]["value"] = "test1"
        res = self.client.put(d["node"]["key"], d["node"]["value"])
        self.assertEqual(zeroth + 1, res.header.revision)
        self.assertEqual(self.client.get(d["node"]["key"])[0], b(d["node"]["value"]))

    def test_1_get(self):
        save_node_info(self.node.name, node_to_dict(self.node), marshall=json)
        res_node_d = get_node_info(self.node.name, marshall=json)
        res_node_d.update(
            {
                "driver_cls": DummyNodeDriver,
                "_class": "DummyNodeDriver",
                "extra": {"provider": "DummyNodeDriver"},
            }
        )
        s = {
            "driver": "DummyNodeDriver",
            "extra": {},
            "id": "3",
            "name": "dummy-3",
            "private_ips": [],
            "public_ips": ["127.0.0.3"],
            "state": "running",
        }
        result = dict_to_node(res_node_d)
        self.assertDictEqual(
            node_to_dict(result),
            {
                "driver": "DummyNodeDriver",
                "extra": {},
                "id": "3",
                "name": "dummy-3",
                "private_ips": [],
                "public_ips": ["127.0.0.3"],
                "state": "running",
            },
        )

    def _test_2_del(self):
        self.assertEqual(
            del_node_info(self.node.name).key,
            "/{key}".format(key="/".join(("unclustered", self.node.name))),
        )

    @classmethod
    def tearDownClass(cls):
        assert del_node_info(cls.node.name) is True


if __name__ == "__main__":
    unittest_main()
