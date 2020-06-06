from pathlib import Path
from setuptools import setup, find_packages

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
    with path.open() as fh:
        reqs = [strip_comments(l) for l in fh.readlines()]
        return [_pip_requirement(r, *f[:-1]) for r in reqs if r]


def reqs(*f):
    return [req for subreq in _reqs(*f) for req in subreq]


def extras(*p):
    return reqs('extras', *p)


def extras_require():
    return {x: extras(x + '.txt') for x in BUNDLES}

setup(name='di-nox-helper',
      version='0.0.1',
      url='https://swodataintelligence@dev.azure.com/swodataintelligence/Data%20Intelligence%20Scrum/_git/runtime-common-library-dinoxhelper',
      license='SWO',
      author='Koptev, Roman',
      author_email='roman.koptev@softwareone.com',
      description='DI Nox Helper functions to manage hierarchical nox projects',
      packages=find_packages(exclude=['tests', 'examples', 'docs']),
      python_requires='>=3.6.0',
      install_requires=reqs('default.txt'),
      extras_require=extras_require(),
      long_description=open('README.md').read(),
      zip_safe=False)
