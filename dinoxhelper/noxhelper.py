from .envutils import source_bash_file
import inspect
import nox
import os

main_python = 'python3.7.7'
test_pythons = ['python3.7.3', 'python3.7.7']
kafka_presets = [
    'HDInsights_prod',
    'HDInsights_test',
    'k8s_prod',
    'k8s_test',
    'linux_local',
    'mac_local',
]

main_env_presets = [
    'test',
    'prod',
]

local_env_presets = [
    'mac_local',
    'linux_local',
]

try:
    import __builtin__ as builtins
except ImportError:
    import builtins

nox.options.error_on_missing_interpreters = True


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
        elif library == 'disettings':
            repository = 'temporary-common-library-disettings'
        else:
            repository = f'runtime-common-library-{library}'
        if base_path is None:
            new_repository = join(nox_work_folder, 'projects', repository)
            if not os.path.isdir(new_repository):
                new_repository = join('..', repository)
            repository = new_repository
        else:
            repository = join(base_path, repository)
        session.install('-U', '-r', join(repository, 'requirements', 'default.txt'))
        if extras:
            extras = extras.split(',')
            for item in extras:
                item = item.strip()
                session.install('-U',  '-r', join(repository, 'requirements', 'extras', f'{item}.txt'))
        session.install(repository)

def install_own_dependencies(extras=None):
    from os.path import join

    session = get_session()

    if os.path.isdir('src'):
        session.install('-U', '-r', join('src', 'requirements.txt'))
        if extras:
            extras = extras.split(',')
            for item in extras:
                item = item.strip()
                session.install('-U',  '-r', join('deploy', 'requirements', f'{item}.txt'))
    else:
        session.install('-U', '-r', join('requirements', 'default.txt'))
        if extras:
            extras = extras.split(',')
            for item in extras:
                item = item.strip()
                session.install('-U', '-r', join('requirements', 'extras', f'{item}.txt'))


def setup_pip(no_extra_index=False):

    session = get_session()

    if not no_extra_index:
        if os.environ.get('PIP_EXTRA_INDEX_URL'):
            session.env['PIP_EXTRA_INDEX_URL'] = os.environ.get('PIP_EXTRA_INDEX_URL')
    elif 'PIP_EXTRA_INDEX_URL' in session.env:
        del session.env['PIP_EXTRA_INDEX_URL']

    session.install('-U', 'pip')
    session.install('-U', 'wheel', 'setuptools', 'certifi')


def common_setup(session, extras=None, dilibraries=None, no_extra_index=True):
    import inspect
    import os
    dilibraries = dilibraries or {}

    session.run('python', '--version')

    # base_path = os.path.dirname(__file__)
    nested_level = 0
    base_path = os.path.dirname((inspect.stack()[nested_level])[1])
    while base_path == os.path.dirname(__file__):
        nested_level += 1
        base_path = os.path.dirname((inspect.stack()[nested_level])[1])
    session.chdir(base_path)

    setup_pip()

    for entry in dilibraries:
        lib_name, lib_extras = entry
        install_di_library(lib_name, extras=lib_extras)

    install_own_dependencies(extras)

    if no_extra_index and 'PIP_EXTRA_INDEX_URL' in session.env:
      del session.env['PIP_EXTRA_INDEX_URL']


def run_di_app(session, main_env, local_env, kafka, extras=None, dilibraries=None):
    from distutils.dir_util import copy_tree
    common_setup(session, extras=extras, dilibraries=dilibraries)
    basepath = os.path.join(nox_work_folder, 'projects', 'runtime-common-library-disecrets', 'disecrets')
    if not os.path.isdir(basepath):
        basepath = os.path.join(nox_work_folder, '..', 'runtime-common-library-disecrets', 'disecrets')
    session.run(
        'python',
        os.path.join(basepath, 'one_config.py'),
        os.path.join('src', 'di_description.json'),
        f'azure/k8s/{main_env}',
        local_env,
        os.path.join('env', f'{main_env}-{local_env}.json'),
        os.path.join(basepath, 'in')
    )
    copy_tree(
        os.path.join(basepath, 'in', 'data', 'kafka_settings'),
        os.path.join('env', 'kafka')
    )

    load_env_vars(os.path.join('env', f'{main_env}-{local_env}.json'))
    load_env_vars(os.path.join('env', 'kafka', f'{kafka}.json'))

    session.chdir(os.path.join('src', 'app'))
    session.run('python', 'app.py')


def standard_di_test(session, extras=None, dilibraries=None):
    common_setup(session, extras=extras, dilibraries=dilibraries)
    session.install('pytest')
    session.run('python', '-m', 'pytest')


def standard_di_docs(session, extras=None, dilibraries=None):
    common_setup(session, extras=extras, dilibraries=dilibraries)
    session.install('Sphinx')
    session.install('rinohtype')
    session.chdir('docs')
    session.run('make', 'html', external=True)
    session.run('sphinx-build', '-b', 'rinoh', 'source', 'build/rinoh', external=True)


def standard_build_di_library(session, extras=None, dilibraries=None):
    common_setup(session, dilibraries=dilibraries)
    # session.install('--no-cache-dir', '-U', 'setuptools', 'wheel')
    session.run('python', 'setup.py', 'sdist', 'bdist_wheel')


work_folder = os.path.abspath(os.getcwd())
trim_length = len(work_folder) + 1
folders = search_nox_sub_projects(work_folder)
folders = [folder[trim_length:].replace('/', '.') + '.noxfile' for folder in folders]
builtins.nox = nox
builtins.source_bash_file = source_bash_file
builtins.load_env_vars = load_env_vars
builtins.install_di_library = install_di_library
builtins.install_own_dependencies = install_own_dependencies
builtins.setup_pip = setup_pip
builtins.is_main_nox_module = is_main_nox_module
builtins.run_di_app = run_di_app
builtins.common_setup = common_setup
builtins.standard_di_test = standard_di_test
builtins.standard_di_docs = standard_di_docs
builtins.standard_build_di_library = standard_build_di_library
builtins.main_python = main_python
builtins.test_pythons = test_pythons
builtins.kafka_presets = kafka_presets
builtins.main_env_presets = main_env_presets
builtins.local_env_presets = local_env_presets
if not (os.environ.get('NOT_MAIN_NOX_MODULE') == 1):
  builtins.nox_work_folder = work_folder
builtins.nox_paths = folders
# print(folders)
builtins.nox_modules = [__import__(folder, fromlist=[None]) for folder in folders]
builtins.call_from_nox_subprojects = call_from_nox_subprojects
builtins.called_nox_sessions = []
