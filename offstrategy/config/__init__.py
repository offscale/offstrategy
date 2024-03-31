# -*- coding: utf-8 -*-


# TODO: Generate JSON-schema to validate strategy files

"""
import json

import genson


def generate_schema(schema_filename, output_filename):
    s = genson.Schema()
    s.add_schema(json.load(open(schema_filename)))
    with open(output_filename, 'w') as f:
        json.dump(s.to_dict(), f, indent=4, sort_keys=True)


if __name__ == '__main__':
    generate_schema('strategy.sample.json', 'schema.json')
    # TODO: Get JSON-Schema to validate successfully
    # TODO: Generate schema in setup.py
"""
