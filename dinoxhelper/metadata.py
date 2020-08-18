"""Package metadata aggregation."""

import os

# pylint: disable=invalid-name
# pylint: disable=redefined-builtin

version_file = os.path.join(os.path.dirname(__file__), 'version.py')
if os.path.isfile(version_file):
    from .version import __version__ as version  # pylint: disable=import-error # type: ignore
else:
    version = 'dev'

name = 'dinoxhelper'
copyright = '2020, SoftwareONE'
author = 'Koptev, Roman'
description = 'Helper library to manage hierarchical nox-based projects'
license = 'SWO'
url = 'https://swodataintelligence@dev.azure.com/swodataintelligence/Data%20Intelligence%20Scrum/_git/runtime-common-library-dinoxhelper'  # pylint: disable=line-too-long # noqa E501
author_email = 'roman.koptev@softwareone.com'
