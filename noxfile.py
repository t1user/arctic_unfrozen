import nox


PYTHON_VERSIONS = ["3.10", "3.11", "3.12", "3.13"]

nox.options.default_venv_backend = "venv"
nox.options.sessions = ["unit"]


def _pytest_args(default_path, posargs):
    return posargs or [default_path]


def _run_pytest(session, default_path):
    session.install("setuptools>=68", "wheel")
    session.install("-e", ".[test]", "--no-build-isolation")
    session.run("python", "-m", "pytest", *_pytest_args(default_path, session.posargs))


@nox.session
def unit(session):
    _run_pytest(session, "tests/unit")


@nox.session
def integration(session):
    _run_pytest(session, "tests/integration")


@nox.session(python=PYTHON_VERSIONS)
def unit_matrix(session):
    _run_pytest(session, "tests/unit")


@nox.session(python=PYTHON_VERSIONS)
def integration_matrix(session):
    _run_pytest(session, "tests/integration")
