from random import randint
from uuid import uuid4
from json import loads
from types import DictType

from libcloud.compute.base import NodeImage

from offutils_strategy_register import dict_to_node, node_to_dict
from offconf import replace_variables
from offutils import raise_f, find_by_key, obj_to_d, pp, lists_of_dicts_intersection_on, l_of_d_intersection


class Strategy(object):
    image = None

    def __init__(self, strategy_filename):
        with open(strategy_filename) as f:
            strategy = replace_variables(f.read())
        self.strategy = loads(strategy)
        self.default_pick = self.strategy['default_pick']

    def get_node_name(self, image_name=None):
        if type(self.image) is DictType:
            image_name = image_name or self.image['name']
        elif isinstance(self.image, NodeImage):
            image_name = image_name or self.image.name
        return '{purpose}-{image}-{uuid}'.format(
            purpose='-'.join(self.strategy['purpose']),
            image=image_name.encode('string-escape'),
            uuid=uuid4().get_hex()
        ).replace('/', '.').replace(' ', '')

    def get_provider(self, offset=0):
        return self._get_next_option(self.strategy['provider'], offset)

    @staticmethod
    def get_location(enumerable, options):
        return next(lists_of_dicts_intersection_on(('driver', 'id'), enumerable, options), None)

    @staticmethod
    def get_hardware(enumerable, options):
        return next(lists_of_dicts_intersection_on(('driver', 'name'), enumerable, options), None)

    def get_image(self, enumerable, options):
        for option in options:
            self.image = next((image for image in enumerable
                               if 'name' not in option and 'image' in option and image.id == option['image']),
                              None)
            if self.image:
                return self.image
        self.image = next(lists_of_dicts_intersection_on(('driver', 'name'), enumerable, options), None)
        return self.image

    def get_option(self, name, enumerable, provider_name):
        result = getattr(self, 'get_{name}'.format(name=name))(
            enumerable,
            filter(lambda opt: opt['provider'] == provider_name,
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


if __name__ == '__main__':
    pass
