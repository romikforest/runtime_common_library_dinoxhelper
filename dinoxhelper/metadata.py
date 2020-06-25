import os

version_file = os.path.join(os.path.dirname(__file__), 'version.py')
if os.path.isfile(version_file):
    from .version import __version__ as version
else:
    version = '0.0.1dev3'

name = 'dinoxhelper'
copyright = '2020, SoftwareONE'
author = 'Koptev, Roman'
description = 'Helper library to manage hierarchical nox-based projects'
license = 'SWO'
url = 'https://dev.azure.com/swodataintelligence/Data%20Intelligence%20Scrum/_git/runtime-common-library-dicountries'
author_email = 'roman.koptev@softwareone.com'
