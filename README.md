offstrategy
===========

Part of the offscale fabric, handles: creation of nodes across multiple providers.

Key differential to alternatives is support for more providers, and a JSON configuration to optimise on various variables.

NOTE: This is alpha software, recommend waiting for v1 ^_^

## Requirements

Tested on 64-bit Windows and Linux with Python 2.7 and etcd 2.

### etcd
[etcd](https://github.com/coreos/etcd) is a CP distributed key/value store which we use to store information about provisioned nodes.

Other projects then retrieve these nodes and do useful things with them, e.g.: joining to clusters.

## Strategy

A JSON file consisting of: provider, hardware, OS and pick strategy.

This flexibility allows it to scale elastically across multiple cloud providers, optimising on:

  - Price [coming soon]
  - Aggregate price [coming soon]
  - Hardware specifications
  - Software specifications
  - Geolocation
  - Redundancy ratio [coming soon]

See `config` directory for example configs.

### Pick strategy

Depends on what you put in the `"pick"` field. Examples:

  - `first` [default], takes first non-error

#### Coming soon

  - `random`
  - `cheapest`
  - `priciest`

### Redundancy [coming soon]

Global field `redundancy`. Here are examples of possible values:

  - `1:1` [default]
  - `2:1`
  - `+5`

TODO: Workout exactly what this will look like, especially taking georedundancy into consideration.

## Requirements

    pip install -r requirements.txt

## Install

    pip install https://github.com/offscale/offstrategy/archive/master.zip#egg=offstrategy

## Usage

### Compute

    $ python -m offstrategy -h
    usage: __main__.py [-h] [-s STRATEGY] [-n NUMBER_OF_NODES]
                       [--provider PROVIDER] [--image IMAGE]
    
    Create compute nodes
    
    optional arguments:
      -h, --help            show this help message and exit
      -s STRATEGY, --strategy STRATEGY
                            strategy file [strategy.sample.json]
      -n NUMBER_OF_NODES, --number_of_nodes NUMBER_OF_NODES
                            number of nodes to create [1]
      --provider PROVIDER   Try this provider first
      --image IMAGE         Try this image first

Default strategy in `strategy.sample.json`.

## Roadmap

### Version 1

  - Build in logic around different strategies (e.g.: redundancy ratio, cheapest provider)
  - Define + validate against JSON-schema
  - Add DNS support (maybe an `offregister` job?)
