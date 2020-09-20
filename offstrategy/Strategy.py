from importlib import import_module
from random import randint
from socket import getfqdn
from uuid import uuid4
from json import loads
from string import ascii_letters

from libcloud.compute.base import NodeImage
from libcloud.compute.providers import DRIVERS

from offutils_strategy_register import dict_to_node, node_to_dict
from offconf import replace_variables
from offutils import (
    raise_f,
    find_by_key,
    pp,
    lists_of_dicts_intersection_on,
    lists_of_dicts_intersection_on_any,
    find_replace_many,
)


class Strategy(object):
    image = None
    image_name = None

    # TODO: Write some regular-expressions to generate a big list of these:
    image_name_short_map = (
        (
            "Ubuntu Linux 14.04 LTS Trusty Tahr - Minimal Install (64 bit)",
            "Ubuntu 14.04 x64",
        ),
    )

    def __init__(self, strategy_filename):
        with open(strategy_filename) as f:
            strategy = replace_variables(f.read())
        self.strategy_dict = loads(strategy, strict=False)
        self.default_pick = self.strategy_dict["default_pick"]

    def get_node_name(self, image_name=None):
        """Returns the node_name, a combination of cluster-purpose, image-name and uuid,
        sanitised for cloud compliance"""

        def to_name(nom):
            if hasattr(nom, "id"):
                nom = nom.id
            nom = nom.encode(
                "string-escape"
                if isinstance(self.image_name, str)
                else "unicode-escape"
            )[:20]

            return getfqdn(
                "{prefix}-{uuid}".format(
                    prefix=find_replace_many(
                        "{purpose}-{image}".format(
                            purpose="-".join(self.strategy_dict["purpose"]),
                            image=nom,  # 20 chars
                        ),
                        ((" ", ""), (".", "-"), ("/", "-"), ("\\", "-")),
                    ).lower()[:32],
                    uuid=uuid4().get_hex(),  # 32 chars
                )
            )

        if isinstance(self.image, dict):
            if isinstance(self.image["driver"], str):
                drvs = tuple(
                    v[0]
                    for k, v in list(DRIVERS.items())
                    if v[1] == self.image["driver"]
                )
                self.image["driver"] = getattr(
                    import_module(drvs[0]), self.image["driver"]
                )
            name = (
                lambda n: "".join(ch for ch in n if ch in ascii_letters)
                if self.image["driver"].__name__.startswith("Azure")
                else n
            )(image_name or self.image["name"])
            self.image_name = self.image["name"] = to_name(name)
        elif isinstance(self.image, NodeImage):
            name = image_name or self.image.name
            self.image_name = self.image.name = to_name(name)
        elif self.image_name:
            self.image_name = to_name(self.image_name)
        else:
            raise TypeError(
                "Unexpected: "
                "`self.image = {self.image}; self.image_name = {self.image_name};`".format(
                    self=self
                )
            )

        return self.image_name

    def get_provider(self, offset=0):
        return self._get_next_option(self.strategy_dict["provider"], offset)

    @staticmethod
    def get_location(enumerable, options):
        options1 = [
            _f
            for _f in [
                {
                    "name": provider_dict["provider"]["region"],
                    "region_name": provider_dict["provider"]["region"],
                    "availability_zone": provider_dict["provider"].get(
                        "availability_zone"
                    ),
                }
                if "region" in provider_dict.get("provider", frozenset())
                else None
                for provider_dict in options
            ]
            if _f
        ]

        for options in (options, options1):
            r = next(
                lists_of_dicts_intersection_on_any(
                    (("driver", "id"), ("name",), ("availability_zone",)),
                    enumerable,
                    options,
                ),
                next(
                    lists_of_dicts_intersection_on(
                        ("name",),
                        enumerable,
                        [
                            next(
                                lists_of_dicts_intersection_on(
                                    ("availability_zone",),
                                    list(map(node_to_dict, enumerable)),
                                    options1,
                                ),
                                None,
                            )
                        ],
                    ),
                    None,
                ),
            )
            if r:
                return r

    @staticmethod
    def get_hardware(enumerable, options):
        return next(
            lists_of_dicts_intersection_on_any(
                (("id",), ("driver", "name"), ("ram", "name", "disk"), ("name",)),
                enumerable,
                options,
            ),
            None,
        )

    def get_image(self, enumerable, options):
        self.image = next(
            lists_of_dicts_intersection_on_any(
                (("id",), ("name",)), enumerable, options
            ),
            None,
        )
        return self.image

    def get_option(self, name, enumerable, provider_name):
        result = getattr(self, "get_{name}".format(name=name))(
            enumerable,
            [
                opt
                for opt in find_by_key(self.strategy_dict, name)["options"]
                if opt["provider"]["name"] == provider_name
            ],
        )
        if result:
            if result["driver"] == "AzureNodeDriver":
                # result.pop('name', None)
                if "get_uuid" in result and hasattr(result["get_uuid"], "__self__"):
                    return result["get_uuid"].__self__
            return dict_to_node(result) if isinstance(result, dict) else result

        raise ValueError('Failed to set "{name}"'.format(name=name))

    def get_key_pair(self, name, offset=0):
        print(("get_key_pair::offset =", offset))
        return self._get_next_option(self.strategy_dict["provider"], offset)

    _get_next_option = lambda self, obj, offset=0: (
        lambda idx: obj["options"][offset:][idx]
        if (idx + offset) < len(obj["options"])
        else raise_f(ValueError, "`_pick` performed on empty list")
    )(idx=self._pick(obj.get("pick", self.default_pick), len(obj["options"])))

    _pick = (
        lambda self, algorithm, length: {"first": 0, "random": randint(0, length)}[
            algorithm
        ]
        if length
        else raise_f(ValueError, "`_pick` performed on empty list")
    )
