DINOXHELPER
===========

About DINOXHELPER
-----------------

DINOXHELPER (DI Nox Helper) is a python package that provides program API
to work with hierarchical projects under the [nox](https://github.com/theacodes/nox) control.

This package was developed by Koptev, Roman (<koptev.roman@softwareone.com>)
to be used by SoftwareONE DataIntelligence Team and initially was placed
in Azure DevOps repository
https://dev.azure.com/swodataintelligence/Data%20Intelligence%20Scrum/_git/runtime-common-library-dinoxhelper 

**Nox** is a tool similar to [tox](https://github.com/tox-dev/tox), but it's pure python.
It's simple, cross platform and highly customizable because it's entirely written using
the python program language.

With combination with [pyenv](https://github.com/pyenv/pyenv) and [pyenv-win](https://github.com/pyenv-win/pyenv-win)
nox can be used to install multiple python versions and create virtual environments for different automated tasks.

It's supposed that all stages of your python application life cycle are managed by nox sessions.
E.g. using nox sessions you can:

- create and setup the development virtual environment
- run the application in development mode with different options
- run tests for different platforms/python versions/settings
- create python packages
- create production installation builds
- execute any custom commands

This package especially helps create a top level `noxfile` that automatically search projects with
noxfiles in projects subfolders, so that the tasks defined from those noxfiles can be called from the main
noxfile. You can also increase the number of project levels creating nested structure of any complexity.

I also have here some helper code for some typical tasks I often use in nox files in multiple my projects.

Installation
____________

*Comming soon...*

Docummentation
______________

*Comming soon...*
