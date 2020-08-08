from configparser import ConfigParser
import inspect
import nox
import os
import platform
import shutil

from .envutils import source_bash_file

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
                session.log(
                    'Try to install dinoxhelper from the current dinoxhelper installation path')
                session.install(nox_helper_path)
            session.chdir(os.path.dirname(module.__file__))
            env = {'NOT_MAIN_NOX_MODULE': '1'}
            if os.environ.get('PIP_EXTRA_INDEX_URL'):
                env['PIP_EXTRA_INDEX_URL'] = os.environ.get('PIP_EXTRA_INDEX_URL')
            session.run('python', '-m', 'nox', '-s', method_name, env=env)


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
        session.log(
            f'Try to install {library} from the local development installation path')
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
                session.install('-U', '-r',
                                join(repository, 'requirements', 'extras', f'{item}.txt'))
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
                session.install('-U', '-r', join('deploy', 'requirements', f'{item}.txt'))
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
    print(base_path)

    setup_pip()

    for entry in dilibraries:
        lib_name, lib_extras = entry
        install_di_library(lib_name, extras=lib_extras)

    install_own_dependencies(extras)

    if no_extra_index and 'PIP_EXTRA_INDEX_URL' in session.env:
        del session.env['PIP_EXTRA_INDEX_URL']


def run_di_app(session, main_env, local_env, kafka, extras=None,
               dilibraries=None):
    from distutils.dir_util import copy_tree
    common_setup(session, extras=extras, dilibraries=dilibraries)
    basepath = os.path.join(nox_work_folder, 'projects',
                            'runtime-common-library-disecrets', 'disecrets')
    if not os.path.isdir(basepath):
        basepath = os.path.join(nox_work_folder, '..',
                                'runtime-common-library-disecrets', 'disecrets')
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
    session.install('-U', 'pytest-cov')
    session.install('-U', 'pytest')
    session.run('python', '-m', 'pytest')


def standard_di_docs(session, extras=None, dilibraries=None):
    common_setup(session, extras=extras, dilibraries=dilibraries)
    session.install('-U', 'Sphinx')
    session.install('-U', 'rinohtype')
    session.install('-U', 'commonmark', 'recommonmark')
    session.install('-U', 'sphinx-autodoc-typehints')
    session.install('-U', 'sphinx-markdown-tables')
    session.install('-U', 'sphinx_rtd_theme')
    session.chdir('docs')
    session.run('make', 'html', external=True)
    shutil.rmtree('build/text', ignore_errors=True)
    session.run('make', 'text', external=True)
    session.run('sphinx-build', '-b', 'rinoh', 'source',
                os.path.join('build', 'rinoh'), external=True)


def standard_build_di_library(session, extras=None, dilibraries=None):
    common_setup(session, extras=extras, dilibraries=dilibraries)
    # session.install('--no-cache-dir', '-U', 'setuptools', 'wheel')
    session.run('python', 'setup.py', 'sdist', 'bdist_wheel')


def standard_di_flake8(session, extras=None, dilibraries=None):
    common_setup(session, extras=extras, dilibraries=dilibraries)
    session.install('-U', 'flake8',
                    'flake8-docstrings',
                    'mccabe',
                    'pep8-naming',
                    'radon',
                    'flake8-bugbear')
    session.run('python', '-m', 'flake8', '--version')
    session.run('python', '-m', 'flake8')


def standard_di_pylint(session, extras=None, dilibraries=None):
    common_setup(session, extras=extras, dilibraries=dilibraries)
    session.install('-U', 'pylint')
    config = ConfigParser()
    config.read('setup.cfg')
    paths = config['pylint']['paths']
    session.run('python', '-m', 'pylint', '--rcfile=setup.cfg', *paths.split(','))


def standard_di_bandit(session, extras=None, dilibraries=None):
    common_setup(session, extras=extras, dilibraries=dilibraries)
    session.install('-U', 'bandit')
    session.run('python', '-m', 'bandit', '-r', '-c', './.bandit.cfg', '--ini', 'setup.cfg')
    # session.run('bandit-config-generator', '-o', './.bandit.cfg')


def standard_di_isort_check(session):
    common_setup(session)
    session.install('-U', 'isort')
    session.run('python', '-m', 'isort', '.', '--diff')
    session.run('python', '-m', 'isort', '.', '--check-only')


def standard_di_isort(session):
    common_setup(session)
    session.install('-U', 'isort')
    session.run('python', '-m', 'isort', '.')


def standard_di_mypy(session, extras=None, dilibraries=None):
    common_setup(session, extras=extras, dilibraries=dilibraries)
    session.install('-U', 'mypy')
    session.install('-U', 'lxml')
    session.run('python', '-m', 'mypy')


def standard_di_black_check(session):
    common_setup(session)
    session.install('-U', 'brunette')
    session.run('python', '-m', 'brunette', '.', '--config=setup.cfg', '--diff')
    session.run('python', '-m', 'brunette', '.', '--config=setup.cfg', '--check')


def standard_di_black(session):
    common_setup(session)
    session.install('-U', 'brunette')
    session.run('python', '-m', 'brunette', '.', '--config=setup.cfg')


def standard_di_check_outdated(session, extras=None, dilibraries=None):
    common_setup(session, extras=extras, dilibraries=dilibraries)
    session.run('python', '-m', 'pip', 'list', '--outdated')


def standard_di_proselint(session):
    common_setup(session)
    session.install('-U', 'proselint')
    config = ConfigParser()
    config.read('setup.cfg')
    paths = config['proselint']['paths']
    session.run('python', '-m', 'proselint', *paths.split(','))


def standard_di_vale(session):
    """Check code with vale."""

    def install_vale():
        files = {
            'Linux': 'vale',
            'Darwin': 'vale',
            'Windows': 'vale.exe',
        }
        markers = {
            'Linux': 'Linux',
            'Darwin': 'macOS',
            'Windows': 'Windows',
        }
        system = platform.system()
        file = files[system]
        if not os.path.isfile(f'vale/{file}'):
            marker = markers[system]
            path = 'https://github.com/errata-ai/vale/releases/download/' \
                   'v2.3.0/vale_2.3.0_{marker}_64-bit.tar.gz'
            session.run('sh', '-c',
                        f'curl -L {path.format(marker=marker)} | '
                        f'tar -C "vale/" -xvf - '
                        f'"vale"',
                        external=True)

    def prepare_dir():
        if not os.path.isdir('vale'):
            os.mkdir('vale')
        if not os.path.isdir('vale/styles'):
            os.mkdir('vale/styles')

    def install_style(name):
        if not os.path.isdir(f'vale/styles/{name}'):
            session.run('sh', '-c',
                        f'curl "https://codeload.github.com/errata-ai/{name}/tar.gz/master" | '
                        f'tar -C "vale/styles/" --strip-components=1 -xvf - '
                        f'"{name}-master/{name}/*" ',
                        external=True)

    install_vale()
    session.install('-U', 'Sphinx')  # To install rst2html for the Joblint
    prepare_dir()
    config = ConfigParser()
    config.read('setup.cfg')
    style_list = config['vale']['styles'].split(',')
    for style in style_list:
        install_style(style)
    paths = config['vale']['paths'].split(',')
    vale_path = os.path.abspath(os.path.join('vale', 'vale'))
    session.run(vale_path, *paths, external=True)


work_folder = os.path.abspath(os.getcwd())
trim_length = len(work_folder) + 1
folders = search_nox_sub_projects(work_folder)
folders = [folder[trim_length:].replace('/', '.') + '.noxfile' for folder in
           folders]
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
builtins.standard_di_flake8 = standard_di_flake8
builtins.standard_di_pylint = standard_di_pylint
builtins.standard_di_bandit = standard_di_bandit
builtins.standard_di_isort_check = standard_di_isort_check
builtins.standard_di_isort = standard_di_isort
builtins.standard_di_mypy = standard_di_mypy
builtins.standard_di_check_outdated = standard_di_check_outdated
builtins.standard_di_black_check = standard_di_black_check
builtins.standard_di_black = standard_di_black
builtins.standard_di_proselint = standard_di_proselint
builtins.standard_di_vale = standard_di_vale
builtins.main_python = main_python
builtins.test_pythons = test_pythons
builtins.kafka_presets = kafka_presets
builtins.main_env_presets = main_env_presets
builtins.local_env_presets = local_env_presets
if not (os.environ.get('NOT_MAIN_NOX_MODULE') == 1):
    builtins.nox_work_folder = work_folder
builtins.nox_paths = folders
# print(folders)
builtins.nox_modules = [__import__(folder, fromlist=[None]) for folder in
                        folders]
builtins.call_from_nox_subprojects = call_from_nox_subprojects
builtins.called_nox_sessions = []
