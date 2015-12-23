#!/usr/bin/env python

import json

from os import name as os_name, environ
from functools import partial
from itertools import imap, ifilter

from libcloud.compute.types import Provider, LibcloudError
from libcloud.compute.providers import get_driver
from libcloud import security
from libcloud.compute.deployment import SSHKeyDeployment

from offutils_strategy_register import save_node_info, node_to_dict
from offutils import obj_to_d, pp, ping_port

from __init__ import logger
from Strategy import Strategy


# AWS Certificates are acting up (on Windows), remove this in production:
if os_name == 'nt' or environ.get('disable_ssl'):
    security.VERIFY_SSL_CERT = False


class Compute(object):
    """ Light wrapper around libcloud to facilitate integration with strategy files,
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
        self.provider_name, self.provider_dict = (
            lambda _provider_obj: (lambda name: (name, _provider_obj[name]))(_provider_obj.keys()[0])
        )(self.strategy.get_provider(self.offset))

        self.provider_cls = get_driver(
            getattr(Provider, self.provider_name)
        )(self.provider_dict['auth']['username'], self.provider_dict['auth']['key'])

        if 'http_proxy' in environ:
            self.provider_cls.connection.set_http_proxy(proxy_url=environ['http_proxy'])

        # pp(map(obj_to_d, self.list_sizes()))
        get_option = partial(self.strategy.get_option, provider_name=self.provider_name)

        '''
        pp(map(node_to_dict,
               ifilter(lambda image: image and image.id in ('ami-90bfe4f3', 'ami-ffaef69c'), self.list_images())))
        '''

        self.node_specs = {
            'size': get_option('hardware', self.list_sizes()),
            'image': get_option('image', self.list_images()),
            'location': get_option('location', self.list_locations())
        }

        pp({self.provider_name: self.node_specs})
        if 'security_group' in self.provider_dict:
            self.node_specs.update({'ex_securitygroup': self.provider_dict['security_group']})
        if 'key_name' in self.provider_dict:
            self.node_specs.update({'ex_keyname': self.provider_dict['key_name']})

    def restrategise(self):
        self.offset += 1
        self.set_node()

    def setup_keypair(self):
        try:
            self.import_key_pair_from_file(
                name=self.provider_dict['ssh']['key_name'],
                key_file_path=self.provider_dict['ssh']['public_key_path']
            )
        except Exception as e:
            if not e.message.startswith('InvalidKeyPair.Duplicate'):
                raise e

    def attempt_provision(self, create_or_deploy='create', prefer_provider=None, prefer_image=None):
        if ping_port() is not True:
            raise EnvironmentError('etcd server not up')

        if prefer_provider:
            self.strategy.strategy['provider']['options'] = (next(
                ifilter(
                    lambda obj: obj.keys()[0] == prefer_provider,
                    self.strategy.strategy['provider']['options']
                )
            ),)
            '''
            # Prefer syntax
            self.strategy.strategy['provider']['options'].insert(
                0, self.strategy.strategy['provider']['options'].pop(
                    next(
                        ifilter(
                            lambda (idx, obj): obj.keys()[0] == prefer_provider,
                            enumerate(self.strategy.strategy['provider']['options'])
                        )
                    )[0]
                )
            )
            '''
        for i in xrange(len(self.strategy.strategy['provider']['options'])):  # Threshold
            logger.info('Attempting to create node "{node_name}" on: {provider}'.format(
                node_name=self.strategy.get_node_name(), provider=self.provider_name
            ))
            self.provision(create_or_deploy)

            if self.node:
                save_node_info(self.node_name, node_to_dict(self.node), marshall=json)
                return self.node
            self.restrategise()

        raise LibcloudError('Failed to provision node')

    def provision(self, create_or_deploy):
        try:
            self.setup_keypair()
        except LibcloudError as e:
            logger.warn('{cls}: {msg}'.format(cls=e.__class__.__name__, msg=e.message))

        if 'ex_securitygroup' in self.node_specs and self.provider_name.startswith('EC2'):
            print self.node_specs['ex_securitygroup']

        if create_or_deploy == 'deploy':
            with open(self.provider_dict['ssh']['public_key_path'], mode='rt') as f:
                ssh_key = f.read()
            self.node_specs.update({'deploy': SSHKeyDeployment(ssh_key)})

        self.node_name = self.strategy.get_node_name()
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
        except Exception as e:
            if e.message.startswith('InvalidGroup.NotFound'):
                print 'InvalidGroup.NotFound'
                exit(1)
            else:
                raise e
