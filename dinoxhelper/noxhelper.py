from .envutils import source_bash_file
import inspect
import nox
import os

try:
    import __builtin__ as builtins
except ImportError:
    import builtins


def get_session():
    stack = inspect.stack()
    try:
        locals_ = stack[2][0].f_locals
    finally:
        del stack
    if 'session' not in locals_:
        raise RuntimeError('This method should be called from the nox session handler')

    return locals_.get('session')


def is_main_nox_module():
    if os.environ.get('NOT_MAIN_NOX_MODULE') == 1:
        return False
    curframe = inspect.currentframe()
    calframe = inspect.getouterframes(curframe, 2)
    caller_folder = os.path.dirname(calframe[1][1])
    return nox_work_folder == caller_folder


def search_nox_sub_projects(work_folder, folders=None):
    if folders is None:
        folders = []
    if os.environ.get('NOT_MAIN_NOX_MODULE') == 1:
        return folders
    work_folder = os.path.join(work_folder, 'projects')
    if os.path.isdir(work_folder):
        for folder in os.listdir(work_folder):
            folder = os.path.join(work_folder, folder)
            if os.path.isdir(folder):
                if os.path.exists(os.path.join(work_folder, folder, 'noxfile.py')):
                    search_nox_sub_projects(folder, folders)
                    folders.append(folder)
    return folders


def call_from_nox_subprojects():
    session = get_session()
    method_name = session._runner.name
    nox_helper_path = os.path.dirname(os.path.dirname(__file__))
    for module in nox_modules:
        if hasattr(module, method_name) and callable(getattr(module, method_name)):
            if (module.__file__, method_name) in called_nox_sessions:
                continue
            called_nox_sessions.append((module.__file__, method_name))
            if os.environ.get('PIP_EXTRA_INDEX_URL'):
                session.env['PIP_EXTRA_INDEX_URL'] = os.environ.get('PIP_EXTRA_INDEX_URL')
            session.install('nox')
            try:
                session.log('Try to install dinoxhelper with pip')
                session.install('dinoxhelper')
            except nox.command.CommandFailed:
                session.log('Try to install dinoxhelper from the current dinoxhelper installation path')
                session.install(nox_helper_path)
            session.chdir(os.path.dirname(module.__file__))
            env = {'NOT_MAIN_NOX_MODULE': '1'}
            if os.environ.get('PIP_EXTRA_INDEX_URL'):
                env['PIP_EXTRA_INDEX_URL'] = os.environ.get('PIP_EXTRA_INDEX_URL')
            session.run('python', '-m', 'nox', '-s', method_name, env = env)


def load_env_vars(path):
    import json
    session = get_session()

    if os.path.isabs(path):
        abs_path = path
    else:
        abs_path = os.path.join(os.path.abspath(os.getcwd()), path)
    if os.path.exists(abs_path):
        session.log(f'Source {path}')
        with open(abs_path, 'rt', encoding='utf8') as f:
            session.env.update(json.load(f))
    else:
        session.log(f'Not found {path}')


def install_di_library(library, extras=None, base_path=None):
    from os.path import join

    session = get_session()

    try:
        session.log(f'Try to install {library} with pip')
        if extras:
            session.install('-U', f'{library}[{extras}]')
        else:
            session.install('-U', f'{library}')
    except nox.command.CommandFailed:
        session.log(f'Try to install {library} from the local development installation path')
        if library == 'dilibraries':
            repository = 'runtime-common-library-di_libraries'
        else:
            repository = f'runtime-common-library-{library}'
        if base_path is None:
            repository = join(nox_work_folder, 'projects', repository)
        else:
            repository = join(base_path, repository)
        session.install('-U', '-r', join(repository, join('requirements', 'default.txt')))
        if extras:
            extras = extras.split(',')
            for item in extras:
                item = item.strip()
                session.install('-U',  '-r', join(repository, 'requirements', 'extras', f'{item}.txt'))
        session.install(repository)


def setup_pip(no_extra_index=False):

    session = get_session()

    if not no_extra_index:
        if os.environ.get('PIP_EXTRA_INDEX_URL'):
            session.env['PIP_EXTRA_INDEX_URL'] = os.environ.get('PIP_EXTRA_INDEX_URL')

    session.install('-U', 'pip')
    session.install('-U', 'wheel', 'setuptools', 'certifi')


work_folder = os.path.abspath(os.getcwd())
trim_length = len(work_folder) + 1
folders = search_nox_sub_projects(work_folder)
folders = [folder[trim_length:].replace('/', '.') + '.noxfile' for folder in folders]
builtins.nox = nox
builtins.source_bash_file = source_bash_file
builtins.load_env_vars = load_env_vars
builtins.install_di_library = install_di_library
builtins.setup_pip = setup_pip
builtins.is_main_nox_module = is_main_nox_module
if not (os.environ.get('NOT_MAIN_NOX_MODULE') == 1):
  builtins.nox_work_folder = work_folder
builtins.nox_paths = folders
# print(folders)
builtins.nox_modules = [__import__(folder, fromlist=[None]) for folder in folders]
builtins.call_from_nox_subprojects = call_from_nox_subprojects
builtins.called_nox_sessions = []
