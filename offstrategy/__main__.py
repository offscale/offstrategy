from os import path
from functools import partial
from argparse import ArgumentParser
from multiprocessing import Pool

from offutils import ping_port

from __init__ import logger
from Compute import Compute

config_join = partial(path.join, path.dirname(__file__), 'config')


def _build_parser():
    parser = ArgumentParser(description='Create compute nodes')
    parser.add_argument('-s', '--strategy', help='strategy file [strategy.sample.json]',
                        default=config_join('strategy.sample.json'))
    parser.add_argument('-n', '--number_of_nodes', help='number of nodes to create [1]',
                        default=1, type=int)
    parser.add_argument('--provider', help='Try this provider first')
    parser.add_argument('--image', help='Try this image first')
    return parser


if __name__ == '__main__':
    args = _build_parser().parse_args()

    def one(*ignore):
        compute = Compute(args.strategy)
        logger.info(compute.attempt_provision('create', prefer_provider=args.provider, prefer_image=args.image))

    print 'args.number_of_nodes =', args.number_of_nodes
    if args.number_of_nodes == 1:
        one()
    else:
        p = Pool(args.number_of_nodes)
        p.map(one, xrange(args.number_of_nodes))
