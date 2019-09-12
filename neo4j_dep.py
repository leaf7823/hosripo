#!/usr/bin/env python3

import re
import sys
from collections import namedtuple

from neo4j.v1 import GraphDatabase

Config = namedtuple('Config', ['url', 'username', 'password',
                               'node_label', 'rel_type', 'batch_size'])

VALID_NAME_RE = re.compile(r'^[A-Za-z][A-Za-z0-9_]*$')


def create_records(dep_dict, config):
    db = GraphDatabase.driver(config.url, auth=(config.username, config.password))
    with db.session() as session:
        create_records_with_session(session, dep_dict, config)


def create_records_with_session(session, dep_dict, config):
    if VALID_NAME_RE.match(config.node_label) is None:
        raise ValueError('invalid Node label: ' + config.node_label)
    if VALID_NAME_RE.match(config.rel_type) is None:
        raise ValueError('invalid Relationship type: ' + config.rel_type)
    session.run('CREATE INDEX ON :{node_label}({rel_type})'
                .format(node_label=config.node_label, rel_type=config.rel_type))
    tx = session.begin_transaction()
    index = 0
    mutation = '''
    MERGE (src:{node_label} {{name: $src}})
    MERGE (dest:{node_label} {{name: $dest}})
    MERGE (src)-[dep:{rel_type}]->(dest)
    '''.format(node_label=config.node_label, rel_type=config.rel_type)
    for src, dests in dep_dict.items():
        for dest in dests:
            tx.run(mutation, src=src, dest=dest)
            if index % config.batch_size == config.batch_size - 1:
                print('{}: Committing...'.format(index + 1), file=sys.stderr)
                tx.commit()
                tx = session.begin_transaction()
            index += 1
    tx.commit()


def main():
    import argparse
    import json
    import os

    parser = argparse.ArgumentParser()
    parser.add_argument('-U', '--url', default='bolt://localhost:7687')
    parser.add_argument('-u', '--username')
    parser.add_argument('-p', '--password')
    parser.add_argument('-b', '--batchsize', type=int, default=10000)
    parser.add_argument('-n', '--nodelabel', default='Package')
    parser.add_argument('-r', '--reltype', default='PDEPENDS')
    parser.add_argument('file', nargs='*')
    args = parser.parse_args()
    if args.username:
        username = args.username
    else:
        username = os.getenv('NEO4J_USERNAME', 'neo4j')
    if args.password:
        password = args.password
    else:
        password = os.getenv('NEO4J_PASSWORD', 'neo4j')

    config = Config(url=args.url, username=username, password=password,
                    node_label=args.nodelabel, rel_type=args.reltype,
                    batch_size=args.batchsize)
    db = GraphDatabase.driver(config.url, auth=(config.username, config.password))
    with db.session() as session:
        if args.file:
            for fpath in args.file:
                with open(fpath) as f:
                    dep_dict = json.load(f)
                    create_records_with_session(session, dep_dict, config)
        else:
            dep_dict = json.load(sys.stdin)
            create_records_with_session(session, dep_dict, config)


if __name__ == '__main__':
    main()
