import dinoxhelper

def common_setup(session, extras=None, no_extra_index=False, skip_library_installation=False):
    import os

    session.run('python', '--version')

    base_path = os.path.dirname(__file__)
    session.chdir(base_path)

    setup_pip()
    install_own_dependencies(extras)

    if no_extra_index and 'PIP_EXTRA_INDEX_URL' in session.env:
      del session.env['PIP_EXTRA_INDEX_URL']

    if not skip_library_installation:
        install_di_library('dinoxhelper', extras='fast')


@nox.session(python=['python3.7.3', 'python3.7.7'])
@nox.parametrize('extras', [None])
def test(session, extras):
    common_setup(session, extras=extras, no_extra_index=True, skip_library_installation=True)
    session.install('pytest')
    session.run('python', '-m', 'pytest')


@nox.session(python='python3.7.7', reuse_venv=True)
def docs(session):
    common_setup(session, no_extra_index=True, skip_library_installation=True)
    session.install('Sphinx')
    session.install('rinohtype')
    session.chdir('docs')
    session.run('make', 'html', external=True)
    session.run('sphinx-build', '-b', 'rinoh', 'source', 'build/rinoh')