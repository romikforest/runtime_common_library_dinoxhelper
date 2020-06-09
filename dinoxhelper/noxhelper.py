import inspect
import nox
import os

try:
    import __builtin__ as builtins
except ImportError:
    import builtins


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
    stack = inspect.stack()
    try:
        locals_ = stack[1][0].f_locals
    finally:
        del stack
    if 'session' not in locals_:
        return
    session = locals_.get('session')
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


work_folder = os.path.abspath(os.getcwd())
trim_length = len(work_folder) + 1
folders = search_nox_sub_projects(work_folder)
folders = [folder[trim_length:].replace('/', '.') + '.noxfile' for folder in folders]
builtins.nox = nox
builtins.is_main_nox_module = is_main_nox_module
if not (os.environ.get('NOT_MAIN_NOX_MODULE') == 1):
  builtins.nox_work_folder = work_folder
builtins.nox_paths = folders
builtins.nox_modules = [__import__(folder, fromlist=[None]) for folder in folders]
builtins.call_from_nox_subprojects = call_from_nox_subprojects
builtins.called_nox_sessions = []
