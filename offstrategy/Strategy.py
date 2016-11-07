from random import randint
from uuid import uuid4
from json import loads
from types import DictType
from string import ascii_letters

from libcloud.compute.base import NodeImage

from offutils_strategy_register import dict_to_node, node_to_dict
from offconf import replace_variables
from offutils import (
    raise_f, find_by_key, pp, lists_of_dicts_intersection_on,
    lists_of_dicts_intersection_on_any, find_replace_many
)


class Strategy(object):
    image = None

    # TODO: Write some regular-expressions to generate a big list of these:
    image_name_short_map = ('Ubuntu Linux 14.04 LTS Trusty Tahr - Minimal Install (64 bit)', 'Ubuntu 14.04 x64'),

    def __init__(self, strategy_filename):
        with open(strategy_filename) as f:
            strategy = replace_variables(f.read())
        self.strategy = loads(strategy)
        self.default_pick = self.strategy['default_pick']

    def get_node_name(self, image_name=None):
        """ Returns the node_name, a combination of cluster-purpose, image-name and uuid,
            sanitised for cloud compliance """
        if type(self.image) is DictType:
            image_name = (
                lambda n: ''.join(ch for ch in n if ch in ascii_letters)
                if self.image['driver'].__name__.startswith('Azure') else n
            )(image_name or self.image['name'])
        elif isinstance(self.image, NodeImage):
            image_name = image_name or self.image.name

        return find_replace_many('{purpose}-{image}-{uuid}'.format(
            purpose='-'.join(self.strategy['purpose']),
            image=find_replace_many(image_name, self.image_name_short_map
                                    ).encode('string-escape' if isinstance(image_name, str) else 'unicode-escape'),
            uuid=uuid4().get_hex()
        ), (('/', '-'), (' ', ''), ('.', '')))

    def get_provider(self, offset=0):
        return self._get_next_option(self.strategy['provider'], offset)

    @staticmethod
    def get_location(enumerable, options):
        options1 = filter(None, map(
            lambda provider_dict: {'name': provider_dict['provider']['region'],
                                   'region_name': provider_dict['provider']['region'],
                                   'availability_zone': provider_dict['provider'].get('availability_zone')
                                   } if 'region' in provider_dict.get('provider', frozenset()) else None,
            options))

        for options in (options, options1):
            r = next(lists_of_dicts_intersection_on_any((('driver', 'id'), ('name',), ('availability_zone',)),
                                                        enumerable, options),
                     next(lists_of_dicts_intersection_on(
                         ('name',), enumerable,
                         [next(lists_of_dicts_intersection_on(('availability_zone',),
                                                              map(node_to_dict, enumerable), options1),
                               None)
                          ]), None)
                     )
            if r:
                return r

    @staticmethod
    def get_hardware(enumerable, options):
        return next(lists_of_dicts_intersection_on_any(
            (('id',), ('driver', 'name'), ('ram', 'name', 'disk'), ('name',)),
            enumerable, options), None
        )

    def get_image(self, enumerable, options):
        self.image = next(lists_of_dicts_intersection_on_any((('id',), ('name',)), enumerable, options), None)
        return self.image

    def get_option(self, name, enumerable, provider_name):
        result = getattr(self, 'get_{name}'.format(name=name))(
            enumerable,
            filter(lambda opt: opt['provider']['name'] == provider_name,
                   find_by_key(self.strategy, name)['options'])
        )
        if result:
            return dict_to_node(result) if type(result) is DictType else result

        raise ValueError('Failed to set "{name}"'.format(name=name))

    def get_key_pair(self, name, offset=0):
        print 'get_key_pair::offset =', offset
        return self._get_next_option(self.strategy['provider'], offset)

    _get_next_option = lambda self, obj, offset=0: (
        lambda idx: obj['options'][offset:][idx] if (idx + offset) < len(obj['options'])
        else raise_f(ValueError, '`_pick` performed on empty list')
    )(idx=self._pick(obj.get('pick', self.default_pick), len(obj['options'])))

    _pick = lambda self, algorithm, length: {
        'first': 0,
        'random': randint(0, length)
    }[algorithm] if length else raise_f(ValueError, '`_pick` performed on empty list')
