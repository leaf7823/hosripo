#!/usr/bin/env python3

import json
import re

# commons-lang3-3.4.jar -> /usr/lib/jvm/java-8-openjdk-amd64/jre/lib/rt.jar
JAR_TO_JAR_RE = re.compile(r'^(.+?\.jar)\s+->\s+(.+?\.jar)\s*$')

#    org.apache.commons.lang3 (commons-lang3-3.4.jar)
PACKAGE_SOURCE_RE = re.compile(r'^\s+(\S+)\s+\(.+?\.jar\)\s*$')

#       -> java.io
#       -> org.apache.commons.lang3.builder commons-lang3-3.4.jar
#       -> com.sun.tools.javadoc.Main       JDK internal API (tools.jar)
PACKAGE_DESTINATION_RE = re.compile(r'^\s+->\s+(\S+)\s*.*$')

#    org.apache.commons.lang3.AnnotationUtils -> java.lang.Boolean
#    org.apache.commons.lang3.AnnotationUtils -> org.apache.commons.lang3.AnnotationUtils$1 commons-lang3-3.4.jar
CLASS_TO_CLASS_RE = re.compile(r'^\s+(\S+)\s+->\s+(\S+)\s*.*$')


def _register_dep_to_dict(src, dest, dep_dict):
    dests = dep_dict.get(src)
    if dests is None:
        dests = set()
        dep_dict[src] = dests
    dests.add(dest)


def _load_deps_of_packages(dep_dict, file):
    src = None
    for i, line in enumerate(file, 1):
        src_match = PACKAGE_SOURCE_RE.match(line)
        if src_match is not None:
            src = src_match.group(1)
            continue
        dest_match = PACKAGE_DESTINATION_RE.match(line)
        if dest_match is not None:
            dest = dest_match.group(1)
            if src is None:
                raise ValueError('line {}: src must not be None'.format(i))
            _register_dep_to_dict(src, dest, dep_dict)
        else:
            src = None


def _load_deps_with_re(dep_dict, file, jdeps_re):
    for line in file:
        match = jdeps_re.match(line)
        if match is None:
            continue
        src, dest = match.groups()
        _register_dep_to_dict(src, dest, dep_dict)


def load(file, *, dep_type='package', dep_dict=None):
    if dep_dict is None:
        dep_dict = {}
    if dep_type == 'package':
        _load_deps_of_packages(dep_dict, file)
    elif dep_type == 'class':
        _load_deps_with_re(dep_dict, file, CLASS_TO_CLASS_RE)
    elif dep_type == 'jar':
        _load_deps_with_re(dep_dict, file, JAR_TO_JAR_RE)
    else:
        raise ValueError('invalid dep_type: {}'.format(dep_type))
    return dep_dict


def _dump_as_txt(dep_dict, file):
    for src, dests in dep_dict.items():
        for dest in sorted(dests):
            print("{} {}".format(src, dest))


def _dump_as_json(dep_dict, file):
    json.dump({k: sorted(list(v)) for k, v in dep_dict.items()}, file)


def dump(dep_dict, file, *, format='json'):
    if format == 'json':
        _dump_as_json(dep_dict, file)
    elif format == 'txt':
        _dump_as_txt(dep_dict, file)
    else:
        raise ValueError('invalid format: {}'.format(format))


def main():
    import argparse
    import sys

    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--deptype', default='package')
    parser.add_argument('-f', '--format', default='json')
    parser.add_argument('file', nargs='*')
    args = parser.parse_args()
    if args.file:
        dep_dict = {}
        for fpath in args.file:
            with open(fpath) as f:
                load(f, dep_type=args.deptype, dep_dict=dep_dict)
    else:
        dep_dict = load(sys.stdin, dep_type=args.deptype)
    dump(dep_dict, sys.stdout, format=args.format)


if __name__ == '__main__':
    main()
