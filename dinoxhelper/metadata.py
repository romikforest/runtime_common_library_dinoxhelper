import os

version_file = os.path.join(os.path.dirname(__file__), 'version.py')
if os.path.isfile(version_file):
    from .version import __version__ as version
else:
    version = 'dev'

name = 'dinoxhelper'
lib_copyright = '2020, SoftwareONE'
author = 'Koptev, Roman'
description = 'Helper library to manage hierarchical nox-based projects'
lib_license = 'SWO'
url = 'https://swodataintelligence@dev.azure.com/swodataintelligence/Data%20Intelligence%20Scrum/_git/runtime-common-library-dinoxhelper'
author_email = 'roman.koptev@softwareone.com'
