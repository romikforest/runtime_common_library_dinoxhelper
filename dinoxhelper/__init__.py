"""DINOXHELPER."""

from dinoxhelper.metadata import version as __version__

# flake8: noqa: F401, F403


def _need_import():
    import inspect  # pylint: disable=import-outside-toplevel

    import __main__  # pylint: disable=import-outside-toplevel

    stack = inspect.stack(0)
    try:
        for entry in stack:
            if hasattr(entry, 'function') and entry.function == 'load_metadata':
                return False
    finally:
        del stack
    return __main__.__file__ != 'setup.py'


if _need_import():
    from dinoxhelper.noxhelper import *
