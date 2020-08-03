import dinoxhelper

lib_name = 'dinoxhelper'

dilibraries = tuple()


@nox.session(python=test_pythons)
@nox.parametrize('extras', [None])
def test(session, extras, dilibraries=dilibraries):
    """Run the test suite."""
    session.log(f'Run test in {lib_name}')
    standard_di_test(session, extras=extras, dilibraries=dilibraries)


@nox.session(python=main_python)
def docs(session, dilibraries=dilibraries):
    """Generate documentation."""
    session.log(f'Run docs in {lib_name}')
    standard_di_docs(session, dilibraries=dilibraries)


@nox.session(python=main_python)
def install_dev(session):
    """Create development virtual environment."""
    session.log(f'Run install_dev in {lib_name}')
    common_setup(session, dilibraries=dilibraries)


@nox.session(python=main_python)
def build_library(session):
    """Build library package. (Add version file manually.)"""
    session.log(f'Run build_library in {lib_name}')
    standard_build_di_library(session, dilibraries=dilibraries)
