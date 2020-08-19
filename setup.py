# flake8: noqa

from pathlib import Path

from dinoxhelper import metadata
from setuptools import find_packages, setup

BUNDLES = {}


def strip_comments(l):
    return l.split('#', 1)[0].strip()


def _pip_requirement(req, *root):
    if req.startswith('-r ') or req.startswith('-c '):
        _, path = req.split()
        return reqs(*root, *path.split('/'))
    return [req]


def _reqs(*f):
    path = (Path.cwd() / 'requirements').joinpath(*f)
    if not path.is_file():
        return []
    with path.open() as fh:
        reqs = [strip_comments(l) for l in fh.readlines()]
        return [_pip_requirement(r, *f[:-1]) for r in reqs if r]


def reqs(*f):
    return [req for subreq in _reqs(*f) for req in subreq]


def extras(*p):
    return reqs('extras', *p)


def extras_require():
    deps = {x: extras(f'{x}.txt') for x in BUNDLES}
    pre_deps = {x: extras(f'pre-{x}.txt') for x in BUNDLES}
    keys = set(deps.keys()).union(set(pre_deps.keys()))
    result = {}
    for key in keys:
        result[key] = list(set(deps.get(key, [])).union(set(pre_deps.get(key, []))))
    return result


if __name__ == '__main__':
    setup(
        name=metadata.name,
        version=metadata.version,
        url=metadata.url,
        license=metadata.license,
        author=metadata.author,
        author_email=metadata.author_email,
        description=metadata.description,
        packages=find_packages(exclude=['tests', 'examples', 'docs']),
        python_requires='>=3.6.0',
        install_requires=reqs('default.txt') + reqs('pre-default.txt'),
        extras_require=extras_require(),
        long_description=open('README.rst').read(),
        zip_safe=False,
    )
