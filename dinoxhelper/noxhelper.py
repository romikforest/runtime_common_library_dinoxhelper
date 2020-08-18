import importlib
import inspect
import os
import platform
import shutil
from configparser import ConfigParser
from os.path import dirname
from os.path import exists as path_exists
from os.path import isdir, isfile, join

import nox
from dinoxhelper.envutils import source_bash_file

main_python = 'python3.7.7'
test_pythons = ['python3.7.3', 'python3.7.7']
kafka_presets = [
    'HDInsights_prod',
    'HDInsights_test',
    'k8s_prod',
    'k8s_test',
    'linux_local',
    'mac_local',
    'win_local',
]

main_env_presets = [
    'test',
    'prod',
]

local_env_presets = [
    'mac_local',
    'linux_local',
    'win_local',
]

SHELL = 'sh'
SHELL_EXEC = '-c'
CP = 'cp'

try:
    import __builtin__ as builtins
except ImportError:
    import builtins

nox.options.error_on_missing_interpreters = True


def load_metadata():
    if isdir('src'):
        spec = importlib.util.spec_from_file_location('metadata', join('src', 'metadata.py'))
        metadata = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(metadata)
        return metadata
    spec = importlib.util.spec_from_file_location('setup', './setup.py')
    setup_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(setup_module)
    return setup_module.metadata


def load_config_section(path, section):
    config = ConfigParser()
    config.read(path)
    if section in config:
        config = config[section]
    else:
        config = {}
    return config


def load_list_config(config, name, default=None):
    result = config.get(name)
    if result:
        if isinstance(result, list):
            result = set(result)
        else:
            result = set(result.split(','))
    else:
        if default:
            if isinstance(default, str):
                result = set(default.split(','))
            else:
                result = set(default)
        else:
            result = set()
    return result


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
    caller_folder = dirname(calframe[1][1])
    return nox_work_folder == caller_folder


def search_nox_sub_projects(work_folder, folders=None):
    if folders is None:
        folders = []
    if os.environ.get('NOT_MAIN_NOX_MODULE') == 1:
        return folders
    work_folder = join(work_folder, 'projects')
    if isdir(work_folder):
        for folder in os.listdir(work_folder):
            folder = join(work_folder, folder)
            if isdir(folder):
                if path_exists(join(work_folder, folder, 'noxfile.py')):
                    search_nox_sub_projects(folder, folders)
                    folders.append(folder)
    return folders


def call_from_nox_subprojects():
    session = get_session()
    method_name = session._runner.name
    nox_helper_path = dirname(dirname(__file__))
    for module in nox_modules:
        if hasattr(module, method_name) and callable(getattr(module, method_name)):
            if (module.__file__, method_name) in called_nox_sessions:
                continue
            called_nox_sessions.append((module.__file__, method_name))
            if os.environ.get('PIP_EXTRA_INDEX_URL'):
                session.env['PIP_EXTRA_INDEX_URL'] = os.environ.get('PIP_EXTRA_INDEX_URL')
            session.install('-U', 'pip')
            session.install('nox')
            try:
                session.log('Try to install dinoxhelper with pip')
                session.install('dinoxhelper>=0.0.0dev0')
            except nox.command.CommandFailed:
                session.log(
                    'Try to install dinoxhelper from the current dinoxhelper installation path'
                )
                session.install(nox_helper_path)
            session.chdir(dirname(module.__file__))
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
        abs_path = join(os.path.abspath(os.getcwd()), path)
    if path_exists(abs_path):
        session.log(f'Source {path}')
        with open(abs_path, 'rt', encoding='utf8') as f:
            session.env.update(json.load(f))
    else:
        session.log(f'Not found {path}')


def install_di_library(library, extras=None, base_path=None):
    session = get_session()

    try:
        session.log(f'Try to install {library} with pip')
        if extras:
            session.install('-U', f'{library}[{extras}]>=0.0.0dev0')
        else:
            session.install('-U', f'{library}>=0.0.0dev0')
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
            if not isdir(new_repository):
                new_repository = join('..', repository)
            repository = new_repository
        else:
            repository = join(base_path, repository)
        session.install('-U', '-r', join(repository, 'requirements', 'default.txt'))
        if extras:
            extras = extras.split(',')
            for item in extras:
                item = item.strip()
                session.install(
                    '-U', '-r', join(repository, 'requirements', 'extras', f'{item}.txt')
                )
        session.install(repository)


def install_own_dependencies(extras=None):
    session = get_session()

    if isdir('src'):
        main_file = join('src', 'requirements.txt')
        if isfile(main_file):
            session.install('-U', '-r', main_file)
        pre_file = join('src', 'pre-requirements.txt')
        if isfile(pre_file):
            session.install('-U', '--pre', '-r', pre_file)
        if extras:
            extras = extras.split(',')
            for item in extras:
                item = item.strip()
                main_file = join('src', join('deploy', 'requirements', f'{item}.txt'))
                if isfile(main_file):
                    session.install('-U', '-r', main_file)
                pre_file = join('deploy', 'requirements', f'pre-{item}.txt')
                if isfile(pre_file):
                    session.install('-U', '--pre', '-r', pre_file)
    else:
        main_file = join('requirements', 'default.txt')
        if isfile(main_file):
            session.install('-U', '-r', main_file)
        pre_file = join('requirements', 'pre-default.txt')
        if isfile(pre_file):
            session.install('-U', '--pre', '-r', pre_file)
        if extras:
            extras = extras.split(',')
            for item in extras:
                item = item.strip()
                main_file = join('requirements', 'extras', f'{item}.txt')
                if isfile(main_file):
                    session.install(
                        '-U', '-r',
                    )
                pre_file = join('requirements', 'extras', f'pre-{item}.txt')
                if isfile(pre_file):
                    session.install('-U', '--pre', '-r', pre_file)


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
    if 'COMMON_SETUP_COMPLETED' in session.env:
        return
    else:
        session.env['COMMON_SETUP_COMPLETED'] = ''

    dilibraries = dilibraries or {}

    session.run('python', '--version')

    # base_path = dirname(__file__)
    nested_level = 0
    base_path = dirname((inspect.stack()[nested_level])[1])
    while base_path == dirname(__file__):
        nested_level += 1
        base_path = dirname((inspect.stack()[nested_level])[1])
    session.chdir(base_path)

    setup_pip()

    for entry in dilibraries:
        lib_name, lib_extras = entry
        install_di_library(lib_name, extras=lib_extras)

    install_own_dependencies(extras)

    if no_extra_index and 'PIP_EXTRA_INDEX_URL' in session.env:
        del session.env['PIP_EXTRA_INDEX_URL']


def run_di_app(session, main_env, local_env, kafka, extras=None, dilibraries=None, profiler=None):
    from distutils.dir_util import copy_tree

    common_setup(session, extras=extras, dilibraries=dilibraries)
    basepath = join(nox_work_folder, 'projects', 'runtime-common-library-disecrets', 'disecrets')
    if not isdir(basepath):
        basepath = join(nox_work_folder, '..', 'runtime-common-library-disecrets', 'disecrets')
    session.run(
        'python',
        join(basepath, 'one_config.py'),
        join('src', 'di_description.json'),
        f'azure/k8s/{main_env}',
        local_env,
        join('env', f'{main_env}-{local_env}.json'),
        join(basepath, 'in'),
    )
    copy_tree(join(basepath, 'in', 'data', 'kafka_settings'), join('env', 'kafka'))

    load_env_vars(join('env', f'{main_env}-{local_env}.json'))
    load_env_vars(join('env', 'kafka', f'{kafka}.json'))

    session.chdir(join('src', 'app'))

    if profiler is None:
        profiler = os.environ.get('DI_PROFILER')

    if profiler is None:
        session.run('python', 'app.py')
    else:
        session.error(f'Unsupported profiler ({profiler})')


def standard_di_test(session, extras=None, dilibraries=None):
    """Run the test suite."""
    config = load_config_section('setup.cfg', 'test')
    if config and config.getboolean('skip', fallback=False):
        session.log('Skip session as requiered by setup.cfg')
        return
    common_setup(session, extras=extras, dilibraries=dilibraries)
    session.install('-U', 'pytest-cov')
    session.install('-U', 'pytest')
    # shutil.rmtree('code_coverage', ignore_errors=True)
    session.run('python', '-m', 'pytest')


def standard_di_docs(session, extras=None, dilibraries=None):
    """Generate documentation."""

    session.log('Graphviz should be installed if you want to generate diagrams')
    config = load_config_section('setup.cfg', 'docs')
    if config and config.getboolean('skip', fallback=False):
        session.log('Skip session as requiered by setup.cfg')
        return
    extra_modules = load_list_config(config, 'extra_modules')
    langs = load_list_config(config, 'langs', 'en')
    engines = load_list_config(config, 'engines', 'html,linkcheck,doc_coverage,text')
    make_targets = load_list_config(config, 'make_targets')
    tlmgr_extra = load_list_config(config, 'tlmgr_extra')
    dipdf_base = config.get('dipdf_base', 'latex')
    if dipdf_base not in ['latex', 'rinoh', 'rst2pdf']:
        session.error(f'Unsupported base for dipdf ({dipdf_base})')

    common_setup(session, extras=extras, dilibraries=dilibraries)

    metadata = load_metadata()

    session.install('-U', 'sphinx')
    session.install('-U', 'pygments')
    session.install('-U', 'commonmark', 'recommonmark')
    session.install('-U', 'sphinx-autodoc-typehints')
    session.install('-U', 'sphinx-markdown-tables')
    session.install('-U', 'sphinx_rtd_theme')

    if 'dipdf' in engines:
        if dipdf_base == 'rinoh':  # rinohtype is AGPL licensed !
            session.install('-U', 'rinohtype', 'pillow')
        elif dipdf_base == 'rst2pdf':
            session.install('-U', 'rst2pdf')

    # # You can install any pypi package, e.g. sphinx-autoapi
    # # Use extra_modules config variable
    # session.install('-U', 'sphinx-autoapi')
    # session.install('-U', 'pylatex')
    for module in extra_modules:
        session.install('-U', module)

    session.chdir('docs')

    shutil.rmtree('build', ignore_errors=True)
    # shutil.rmtree(join('build', 'text'), ignore_errors=True)
    shutil.rmtree(join('source', '_api_reference'), ignore_errors=True)
    shutil.rmtree(join('source', '_autosummary'), ignore_errors=True)

    if 'html' in engines:
        engines.remove('html')
        for lang in langs:
            session.run(
                'sphinx-build',
                '-b',
                'html',
                'source',
                join('build', lang, metadata.version, 'html'),
                '-D',
                f'language={lang}',
                external=True,
            )

    if 'dipdf' in engines:
        engines.remove('dipdf')

        # install latex tools (not finished):
        #####################################
        # if shutil.which('wget'):
        #     LOADER = 'wget -qO-'
        # elif shutil.which('curl'):
        #     LOADER = 'curl -L'
        # else:
        #     session.error('Neither wget nor curl have been found.')
        # if shutil.which('latexmk') is None:
        #     system = platform.system()
        #     if system == 'Windows':
        #         # need to be adapted for win. The url is correct
        #         session.run(SHELL, SHELL_EXEC,
        #                     f'{LOADER} "https://yihui.org/gh/tinytex/tools/install-windows.bat" | sh')
        #     else:
        #         session.run(SHELL, SHELL_EXEC,
        #                     f'{LOADER} "https://yihui.org/gh/tinytex/tools/install-unx.sh" | {SHELL}')
        #
        # # Some packages need to be instaled with tlmgr:
        #
        # #    latex-recommended collection-latexrecommended
        # #    latex-extra collection-latexextra
        # #    fonts-recommended collection-fontsrecommended
        #
        # # Required for my first project (possible they are included in the above packages):
        # # tlmgr install cmap
        # # polyglossia
        # # FreeSerif gnu-freefont
        # # fncychap fancyhdr titlesec tabulary varwidth wrapfig parskip upquote capt-of needspace
        # # oberdiek (hypcap) xindy (!) makeindex, pdftex
        #

        for lang in langs:
            out_dir = join('build', lang, metadata.version, 'dipdf')

            if dipdf_base == 'rinoh':  # rinohtype is AGPL licensed !
                session.run(
                    'sphinx-build',
                    '-b',
                    'rinoh',
                    'source',
                    out_dir,
                    '-D',
                    f'language={lang}',
                    external=True,
                )
            elif dipdf_base == 'rst2pdf':
                session.run(
                    'sphinx-build',
                    '-M',
                    'pdf',
                    'source',
                    out_dir,
                    '-D',
                    f'language={lang}',
                    external=True,
                )
                pdf_src = join(out_dir, 'pdf', '*')
                session.run(
                    SHELL, SHELL_EXEC, f'{CP} {pdf_src} {out_dir}', external=True,
                )
            elif dipdf_base == 'latex':
                for extra in tlmgr_extra:
                    session.run('tmlgr', 'install', extra)
                session.run(
                    'sphinx-build',
                    '-b',
                    'latex',
                    'source',
                    out_dir,
                    '-D',
                    f'language={lang}',
                    external=True,
                )
                session.run('make', '-C', out_dir, 'all-pdf', external=True)

    if 'linkcheck' in engines:
        engines.remove('linkcheck')
        for lang in langs:
            out_dir = join('build', lang, metadata.version, 'linkcheck')
            session.run(
                'sphinx-build',
                '-b',
                'linkcheck',
                'source',
                out_dir,
                '-D',
                f'language={lang}',
                external=True,
            )
    if 'doc_coverage' in engines or 'coverage' in engines:
        if 'doc_coverage' in engines:
            engines.remove('doc_coverage')
        if 'coverage' in engines:
            engines.remove('coverage')
        for lang in langs:
            out_dir = join('build', lang, metadata.version, 'doc_coverage')
            session.run(
                'sphinx-build',
                '-b',
                'coverage',
                'source',
                out_dir,
                '-D',
                f'language={lang}',
                external=True,
            )

    for target in engines:
        for lang in langs:
            out_dir = os.path.join('build', lang, metadata.version, target)
            session.run(
                'sphinx-build',
                '-b',
                target,
                'source',
                out_dir,
                '-D',
                f'language={lang}',
                external=True,
            )

    for target in make_targets:
        for lang in langs:
            out_dir = join('build', lang, metadata.version, target)
            session.run(
                'sphinx-build',
                '-M',
                target,
                'source',
                out_dir,
                '-D',
                f'language={lang}',
                external=True,
            )


def standard_build_di_library(session, extras=None, dilibraries=None):
    """Build library package (Add version file manually)."""
    common_setup(session, extras=extras, dilibraries=dilibraries)
    # session.install('--no-cache-dir', '-U', 'setuptools', 'wheel')
    session.run('python', 'setup.py', 'sdist', 'bdist_wheel')


def standard_di_flake8(session, extras=None, dilibraries=None):
    """Check code with flake8."""
    common_setup(session, extras=extras, dilibraries=dilibraries)
    session.install(
        '-U', 'flake8', 'flake8-docstrings', 'mccabe', 'pep8-naming', 'radon', 'flake8-bugbear'
    )
    session.run('python', '-m', 'flake8', '--version')
    session.run('python', '-m', 'flake8')


def standard_di_pylint(session, extras=None, dilibraries=None):
    """Check code with pylint."""
    config = load_config_section('setup.cfg', 'pylint')
    paths = load_list_config(config, 'paths')
    if not paths:
        session.error('There are no paths to check with pylint in setup.cfg. Exiting...')
        return

    common_setup(session, extras=extras, dilibraries=dilibraries)
    session.install('-U', 'pylint')

    session.run('python', '-m', 'pylint', '--rcfile=setup.cfg', *paths)


def standard_di_pytype(session, extras=None, dilibraries=None):
    """Check code with pytype."""
    config = load_config_section('setup.cfg', 'pytype')
    inputs = load_list_config(config, 'inputs')
    if not inputs:
        session.error('There are no inputs to check with pytype in setup.cfg. Exiting...')
        return

    common_setup(session, extras=extras, dilibraries=dilibraries)
    session.install('-U', 'pytype')
    session.run('python', '-m', 'pytype')


def standard_di_bandit(session, extras=None, dilibraries=None):
    """Check code with bandit."""
    common_setup(session, extras=extras, dilibraries=dilibraries)
    session.install('-U', 'bandit')
    session.run('python', '-m', 'bandit', '-r', '-c', './.bandit.cfg', '--ini', 'setup.cfg')
    # session.run('bandit-config-generator', '-o', './.bandit.cfg')


def standard_di_isort_check(session, dilibraries=None):
    """Check code with isort."""
    common_setup(session, dilibraries=dilibraries)
    session.install('-U', 'isort')
    session.run('python', '-m', 'isort', '.', '--diff')
    session.run('python', '-m', 'isort', '.', '--check-only')


def standard_di_isort(session, dilibraries=None):
    """Sort imports with isort."""
    common_setup(session, dilibraries=dilibraries)
    session.install('-U', 'isort')
    session.run('python', '-m', 'isort', '.')


def standard_di_mypy(session, extras=None, dilibraries=None):
    """Check code with mypy."""
    common_setup(session, extras=extras, dilibraries=dilibraries)
    session.install('-U', 'mypy')
    session.install('-U', 'lxml')
    session.run('python', '-m', 'mypy')


def standard_di_black_check(session, dilibraries=None):
    """Print code diffs for black (brunette) formatting."""
    common_setup(session, dilibraries=dilibraries)
    session.install('-U', 'brunette')
    session.run('python', '-m', 'brunette', '.', '--config=setup.cfg', '--diff')
    session.run('python', '-m', 'brunette', '.', '--config=setup.cfg', '--check')


def standard_di_black(session, dilibraries=None):
    """Format code with black (brunette)."""
    common_setup(session, dilibraries=dilibraries)
    session.install('-U', 'brunette')
    session.run('python', '-m', 'brunette', '.', '--config=setup.cfg')


def standard_di_check_outdated(session, extras=None, dilibraries=None):
    """Check for outdated packages."""
    common_setup(session, extras=extras, dilibraries=dilibraries)
    session.run('python', '-m', 'pip', 'list', '--outdated')


def standard_di_proselint(session, dilibraries=None):
    """Check code with proselint."""
    config = load_config_section('setup.cfg', 'proselint')
    paths = load_list_config(config, 'paths')
    if not paths:
        session.error('There are no paths to check with proselint in setup.cfg. Exiting...')
        return

    common_setup(session, dilibraries=dilibraries)
    session.install('-U', 'proselint')
    session.run('python', '-m', 'proselint', *paths)


def standard_di_vale(session, dilibraries=None):
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
        if not isfile(f'vale/{file}'):
            marker = markers[system]
            path = (
                'https://github.com/errata-ai/vale/releases/download/'
                'v2.3.0/vale_2.3.0_{marker}_64-bit.tar.gz'
            )
            session.run(
                SHELL,
                SHELL_EXEC,
                f'{LOADER} {path.format(marker=marker)} | ' f'tar -C "vale/" -xvf - ' f'"vale"',
                external=True,
            )

    def prepare_dir():
        if not isdir('vale'):
            os.mkdir('vale')
        if not isdir('vale/styles'):
            os.mkdir('vale/styles')

    def install_style(name):
        if not isdir(f'vale/styles/{name}'):
            session.run(
                SHELL,
                SHELL_EXEC,
                f'{LOADER} '
                f'"https://codeload.github.com/errata-ai/{name}/tar.gz/master" | '
                f'tar -C "vale/styles/" --strip-components=1 -xvf - '
                f'"{name}-master/{name}/*" ',
                external=True,
            )

    if shutil.which('wget'):
        LOADER = 'wget -qO-'
    elif shutil.which('curl'):
        LOADER = 'curl -L'
    else:
        session.error('Neither wget nor curl have been found.')

    prepare_dir()
    install_vale()
    session.install('-U', 'Sphinx')  # To install rst2html for the Joblint

    config = load_config_section('setup.cfg', 'vale')
    paths = load_list_config(config, 'paths')
    styles = load_list_config(config, 'styles')
    globs = load_list_config(config, 'globs')
    if not paths:
        session.error('There is no paths to check for vale in setup.cfg. Exiting...')
        return
    if not styles:
        session.error('There is no styles for vale in setup.cfg. Exiting...')
        return
    for style in styles:
        install_style(style)
    globs = {f"--glob='!{x}'" for x in globs}
    vale_path = os.path.abspath(join('vale', 'vale'))
    session.run(vale_path, *paths, *globs, external=True)


def standard_di_quality_task(session, extras=None, dilibraries=None):
    """Format and check code."""
    common_setup(session, extras=extras, dilibraries=dilibraries)
    standard_di_isort(session)
    standard_di_black(session)
    standard_di_pylint(session, extras, dilibraries)
    standard_di_flake8(session, extras, dilibraries)
    standard_di_mypy(session, extras, dilibraries)
    standard_di_pytype(session, extras, dilibraries)
    standard_di_black(session)
    standard_di_check_outdated(session, extras, dilibraries)
    session.log('You may run tasks like `vale` and `proselint` manually if you wish.')


def standard_di_quality_check(session, extras=None, dilibraries=None):
    """Check code for quality."""
    config = load_config_section('setup.cfg', 'qa_check')
    if config and config.getboolean('skip', fallback=False):
        session.log('Skip session as requiered by setup.cfg')
        return
    common_setup(session, extras=extras, dilibraries=dilibraries)
    standard_di_black_check(session)
    standard_di_pylint(session, extras, dilibraries)
    standard_di_flake8(session, extras, dilibraries)
    standard_di_mypy(session, extras, dilibraries)
    standard_di_pytype(session, extras, dilibraries)
    standard_di_black(session)
    standard_di_check_outdated(session, extras, dilibraries)
    session.log("This task doesn't check with isort due the conflict with the black check")
    session.log('You may run tasks like `vale` and `proselint` manually if you wish.')


_work_folder = os.path.abspath(os.getcwd())
_trim_length = len(_work_folder) + 1
_folders = search_nox_sub_projects(_work_folder)
_folders = [folder[_trim_length:].replace('/', '.') + '.noxfile' for folder in _folders]

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
builtins.standard_di_quality_task = standard_di_quality_task
builtins.standard_di_quality_check = standard_di_quality_check
builtins.main_python = main_python
builtins.test_pythons = test_pythons
builtins.kafka_presets = kafka_presets
builtins.main_env_presets = main_env_presets
builtins.local_env_presets = local_env_presets
builtins.standard_di_pytype = standard_di_pytype
if not (os.environ.get('NOT_MAIN_NOX_MODULE') == 1):
    builtins.nox_work_folder = _work_folder
builtins.nox_paths = _folders
# print(_folders)
builtins.nox_modules = [__import__(folder, fromlist=[None]) for folder in _folders]
builtins.call_from_nox_subprojects = call_from_nox_subprojects
builtins.called_nox_sessions = []
