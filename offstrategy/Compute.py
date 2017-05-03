#!/usr/bin/env python

import json
import cPickle as pickle
from collections import namedtuple

from os import environ, path
from functools import partial
from itertools import imap, ifilter

from libcloud.compute.base import NodeAuthPassword, NodeSize
from libcloud.compute.types import Provider, LibcloudError
from libcloud.compute.providers import get_driver
from libcloud import security
from libcloud.compute.deployment import SSHKeyDeployment

from offutils_strategy_register import save_node_info, node_to_dict, obj_to_d, normal_types
from offutils import pp, ping_port

from __init__ import logger
from Strategy import Strategy

if environ.get('disable_ssl'):
    security.VERIFY_SSL_CERT = False

NodeImage__proxy = namedtuple('NodeImage__proxy', ('id',))

obj_to_san_d = lambda obj: {attr: getattr(obj, attr) for attr in dir(obj)
                            if not attr.startswith('__') and type(getattr(obj, attr)) in normal_types
                            and getattr(obj, attr)}


class Compute(object):
    """ Light wrapper around libcloud to facilitate integration with strategy_dict files,
        and simplification of commands """

    offset = 0
    node = None
    node_specs = None
    node_name = None
    provider_name = None
    provider_dict = None
    provider_cls = None
    key_pair = None

    def __init__(self, strategy_file):
        self.strategy = Strategy(strategy_file)
        self.set_node()

    def __getattr__(self, attr):
        return getattr(self.provider_cls, attr)

    def set_node(self):
        self.provider_dict = self.strategy.get_provider(self.offset)

        # region=self.provider_dict['provider']['region'],
        # pp(self.provider_dict['auth'])
        self.provider_cls = (lambda driver: driver(
            **self.provider_dict['auth']
        ))(get_driver(getattr(Provider, self.provider_dict['provider']['name'])))

        '''pp(map(node_to_dict, self.provider_cls.list_nodes()))
        print '-' * 10
        print next(node_to_dict(obj) for obj in self.provider_cls.list_nodes()
                   if obj.extra['ex_vagrantfile'] == '/mnt/large_linux/vagrant/ficus/Vagrantfile')
        exit(1)
        '''

        if 'http_proxy' in environ:
            self.provider_cls.connection.set_http_proxy(proxy_url=environ['http_proxy'])

        # pp(map(obj_to_d, self.list_sizes()))
        get_option = partial(self.strategy.get_option,
                             provider_name=self.provider_dict['provider']['name'])

        # pp(map(node_to_dict, ifilter(lambda n: '12.04.5 x64' in n.id + n.name, self.list_images())))
        # pp(map(lambda n: (n.id, n.name), self.list_images()))
        # pp(map(obj_to_d, self.list_sizes()))
        # exit(1)

        if self.provider_cls.type.startswith('azure'):
            node_img = NodeImage__proxy(self.provider_dict['auth']['region'])

            '''images = self.list_images(node_img)
            with open('images.json', 'wt') as f:
                print 'images =', map(obj_to_san_d, images)
                json.dump({'images': map(obj_to_san_d, images)}, f, indent=4)'''

            if path.isfile('images.pkl'):
                with open('images.pkl', 'rt') as f:
                    images = pickle.load(f)
            else:
                images = self.list_images(node_img)
                with open('images.pkl', 'wt') as f:
                    pickle.dump(images, f)

            self.node_specs = {
                'size': get_option('hardware', self.list_sizes(node_img)),
                'image': get_option('image', images),
                'location': get_option('location', self.list_locations())
            }
        elif self.provider_cls.type == 'Vagrant':
            logger.warn('size/image/location not validated for Vagrant')

            if 'extras' not in self.strategy.strategy_dict['node']:
                self.strategy.strategy_dict['node']['extras'] = dict(options=(self.provider_dict,))

            hardware, image, extras = imap(
                (lambda typ: next(dict(key=self.provider_dict['provider']['key'], **spec)
                                  for spec in self.strategy.strategy_dict['node'][typ]['options']
                                  for key in ('region', 'name')
                                  if spec['provider'][key] == self.provider_dict['provider'][key])
                 ), ('hardware', 'image', 'extras'))

            nodesize_kwargs = {'driver': self.provider_cls}
            nodesize_kwargs.update(**{k: v for k, v in hardware.iteritems()
                                      if k not in frozenset(('provider', 'key', 'name'))})

            if 'extra' not in nodesize_kwargs:
                nodesize_kwargs['extra'] = {'provider': hardware['provider']['visor']}
            else:
                nodesize_kwargs.update(**{'extra': {'provider': hardware['provider']['visor']}})

            if 'id' not in nodesize_kwargs:
                nodesize_kwargs['id'] = hardware['key']
            if 'name' not in nodesize_kwargs:
                nodesize_kwargs['name'] = self.node_name
            if nodesize_kwargs['extra'].get('memory'):
                nodesize_kwargs['ram'] = nodesize_kwargs['extra']['memory']
            for k in ('ram', 'disk', 'bandwidth', 'price'):
                if k not in nodesize_kwargs:
                    nodesize_kwargs[k] = None

            nodesize_kwargs = {k: '"{}"'.format(v) if isinstance(v, basestring) and not v.isdigit() else v
                               for k, v in nodesize_kwargs.iteritems()}
            nodesize_kwargs['extra'] = {k: '"{}"'.format(v) if isinstance(v, basestring) and not v.isdigit() else v
                                        for k, v in nodesize_kwargs['extra'].iteritems()}

            self.node_specs = {
                'size': NodeSize(**nodesize_kwargs),
                'key': hardware['key'],
                'ex_vagrantfile': hardware['key'],
                'image': NodeImage__proxy(image['id']),
                'location': hardware['provider']['region'],
                'extras': extras
            }
            del nodesize_kwargs
            self.strategy.image_name = self.node_specs['image']
        else:
            self.node_specs = {
                'size': get_option('hardware', self.list_sizes()),
                'image': get_option('image', self.list_images()),
                'location': get_option('location', self.list_locations())
            }

        if 'create_with' in self.provider_dict:
            self.node_specs.update(self.provider_dict['create_with'])

        if 'ssh' in self.provider_dict and 'node_password' in self.provider_dict['ssh']:
            self.node_specs.update({
                'auth': NodeAuthPassword(self.provider_dict['ssh']['node_password'])
            })

        pp({self.provider_dict['provider']['name']: self.node_specs})

        if 'security_group' in self.provider_dict:
            self.node_specs.update({'ex_securitygroup': self.provider_dict['security_group']})
        if 'key_name' in self.provider_dict:
            self.node_specs.update({'ex_keyname': self.provider_dict['key_name']})

        self.node_specs.update(dict((ex, val) for ex, val in self.provider_dict.iteritems() if ex.startswith('ex')))

    def restrategise(self):
        self.offset += 1
        self.set_node()

    def setup_keypair(self):
        try:
            self.import_key_pair_from_file(
                name=self.provider_dict['ssh']['key_name'],
                key_file_path=self.provider_dict['ssh']['public_key_path']
            )
        except NotImplementedError:
            logger.warn(
                '`import_key_pair_from_file` not implemented for {}'.format(self.provider_dict['provider']['name']))
            pass  # DW about it
        except Exception as e:
            if not e.message.startswith('InvalidKeyPair.Duplicate'):
                raise e

    def attempt_provision(self, create_or_deploy='create', prefer_provider=None, prefer_image=None):
        if ping_port() is not True:
            raise EnvironmentError('etcd server not up')

        if prefer_provider:
            self.strategy.strategy_dict['provider']['options'] = next(
                ifilter(
                    lambda obj: obj.keys()[0] == prefer_provider,
                    self.strategy.strategy_dict['provider']['options']
                )
            ),
            '''
            # Prefer syntax
            self.strategy_dict.strategy_dict['provider']['options'].insert(
                0, self.strategy_dict.strategy_dict['provider']['options'].pop(
                    next(
                        ifilter(
                            lambda (idx, obj): obj.keys()[0] == prefer_provider,
                            enumerate(self.strategy_dict.strategy_dict['provider']['options'])
                        )
                    )[0]
                )
            )
            '''
        for i in xrange(len(self.strategy.strategy_dict['provider']['options'])):  # Threshold
            logger.info('Attempting to create node {node_name!r} on: {provider!r}'.format(
                node_name=self.node_name, provider=self.provider_dict['provider']['name']
            ))
            self.provision(create_or_deploy)

            if self.node:
                save_node_info(self.node.name.partition('.')[0], node_to_dict(self.node), marshall=json)
                return self.node
            self.restrategise()

        raise LibcloudError('Failed to provision node')

    def provision(self, create_or_deploy):
        try:
            self.setup_keypair()
        except LibcloudError as e:
            logger.warn('{cls}: {msg}'.format(cls=e.__class__.__name__, msg=e.message))
        except KeyError as e:
            if e.message != 'ssh':
                raise e
            logger.warn('SSH not setup [by us] for: {!r}'.format(self.node_name))

        if 'ex_securitygroup' in self.node_specs and self.provider_dict['provider']['name'].startswith('EC2'):
            print 'ex_securitygroup =', self.node_specs['ex_securitygroup']

        if create_or_deploy == 'deploy':
            with open(self.provider_dict['ssh']['public_key_path'], mode='rt') as f:
                public_ssh_key = f.read()
            self.node_specs.update({'deploy': SSHKeyDeployment(public_ssh_key)})

        assert self.node_name

        try:
            self.node = getattr(
                self, '{0}_node'.format(create_or_deploy)
            )(name=self.node_name, **self.node_specs)
        except NotImplementedError as e:
            if create_or_deploy != 'deploy':
                raise e
            error_message = 'deploy_node not implemented for this driver'
            if e.message != error_message:
                raise
            logger.info('{error_message}, so running `create_node` instead.'.format(
                error_message=error_message.replace('deploy_node', '`deploy_node`')
            ))
            self.node = self.create_node(name=self.node_name, **self.node_specs)
            # logger.info('SoftLayer billing is giving error, will remove condition once resolved.')
        except LibcloudError as e:
            logger.warn('{cls}: {msg}'.format(cls=e.__class__.__name__, msg=e.message))
            raise e
