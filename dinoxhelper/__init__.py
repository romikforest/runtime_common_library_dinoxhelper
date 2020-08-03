from .metadata import version as __version__


def _need_import():
    import __main__
    return __main__.__file__ != 'setup.py'


if _need_import():
    from .noxhelper import *
