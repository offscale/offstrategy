from unittest import TestCase, main as unittest_main

from libcloud.compute.drivers.dummy import DummyNodeDriver

from etcd import EtcdKeyNotFound, EtcdResult
from etcd.tests.unit.test_request import TestClientApiBase
from http.client import HTTPException

from offutils_strategy_register import save_node_info, get_node_info  # , del_node_info
from offutils import obj_to_d, pp, ping_port, raise_f


class TestEtcdNodeRavel(TestClientApiBase):
    node = DummyNodeDriver("").create_node()

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

    def test_0_put(self):
        self.assertIsNotNone(save_node_info(self.node.name, self.node))

    def test_newkey(self):
        """ Can set a new value """
        d = {
            "action": "set",
            "node": {
                "expiration": "2013-09-14T00:56:59.316195568+02:00",
                "modifiedIndex": 183,
                "key": "/testkey",
                "ttl": 19,
                "value": "test",
            },
        }

        self._mock_api(201, d)
        res = self.client.write(d["node"]["key"], d["node"]["value"])
        d["node"]["newKey"] = True
        self.assertEqual(res, EtcdResult(**d))

    def test_1_get(self):
        result = get_node_info(self.node.name)
        # self.assertEqual checks memory location, like `('foo',) is ('foo',)`
        # and `self.assertTrue(self.node == result)` also fails.
        for attr in dir(self.node):
            if attr.startswith("_") or attr in (
                "destroy",
                "driver",
                "get_uuid",
                "image",
                "reboot",
                "size",
            ):
                continue
            self.assertEqual(getattr(self.node, attr), getattr(result, attr))

    def _test_2_del(self):
        print((del_node_info(self.node.name)._prev_node))

        self.assertEqual(
            del_node_info(self.node.name).key,
            "/{key}".format(key="/".join(("unclustered", self.node.name))),
        )

    @classmethod
    def tearDownClass(cls):
        error = False
        try:
            # del_node_info(cls.node.name)
            ""
        except EtcdKeyNotFound:
            error = True
        if not error:
            pass  # raise AssertionError('test_2_del failed to remove key')


if __name__ == "__main__":
    unittest_main()
