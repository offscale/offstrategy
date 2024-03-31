# -*- coding: utf-8 -*-
from argparse import ArgumentParser
from multiprocessing import Pool
from os import path

from .__init__ import __version__, logger
from .Compute import Compute


def _build_parser():
    """
    CLI parser builder using builtin `argparse` module

    :return: instanceof ArgumentParser
    :rtype: ```ArgumentParser```
    """
    parser = ArgumentParser(description="Create compute nodes")
    parser.add_argument(
        "-s",
        "--strategy",
        help="strategy file [strategy.sample.json]",
        default=path.join(path.dirname(__file__), "config", "strategy.sample.json"),
    )
    parser.add_argument(
        "-n",
        "--number_of_nodes",
        help="number of nodes to create [1]",
        default=1,
        type=int,
    )
    parser.add_argument("--provider", help="Try this provider first")
    parser.add_argument("--image", help="Try this image first")
    parser.add_argument(
        "--version", action="version", version="%(prog)s {}".format(__version__)
    )
    return parser


if __name__ == "__main__":
    args = _build_parser().parse_args()

    def one(*ignore):
        compute = Compute(args.strategy)
        compute.node_name = compute.strategy.get_node_name()
        logger.info(
            compute.attempt_provision(
                "create", prefer_provider=args.provider, prefer_image=args.image
            )
        )

    logger.info(
        "Provisioning {} node{}".format(
            args.number_of_nodes, "s" if args.number_of_nodes > 1 else ""
        )
    )
    if args.number_of_nodes == 1:
        one()
    else:
        p = Pool(args.number_of_nodes)
        p.map(one, list(range(args.number_of_nodes)))
