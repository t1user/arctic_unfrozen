# Repository Guidelines

## Purpose & Procedure

Project's purpose is to revive this long unmaintained repo. The target is to make it use latest version of dependencies including current version of python, mongo, pymongo, pandas and numpy. Supported Python versions are currently 3.10 through 3.13. It's paramount not to break any functionality and keep existing interface. Subsequently new functionality and additional interface points may be added but it should be done while keeping full backwards compatibility. Don't make sweeping changes all at once, focus on the requested change. If warranted you may suggest next steps to achieve the overall purpose.

Use `PLAN.md` as the durable roadmap for sequencing modernization work. Keep it updated when priorities, supported versions, or CI strategy change.

## Target Structure

All config in pyproject.toml, remove other config files to the extend possible
Checkers and linters: mypy, black, flake8
Testing: pytest

## Project Structure & Module Organization

This repository contains the legacy `arctic` Python package, now in maintenance mode. Core library code lives under `arctic/`, with major areas split into `chunkstore/`, `tickstore/`, `store/`, `serialization/`, `date/`, `asynchronous/`, and command-line entry points in `arctic/scripts/`. Tests are under `tests/`, separated into `tests/unit/` and `tests/integration/`. Documentation is in `docs/`, examples are in `howtos/`, performance work is in `benchmarks/`, and logo assets are in `logo/`.

## Build, Test, and Development Commands

- `python -m pip install -e .[test,dev]`: install Arctic plus test and development tooling into the active virtualenv.
- `python -m pytest tests/unit`: run the unit-test baseline used by GitHub Actions on Python 3.10 through 3.13.
- `python -m nox -s unit`: run the unit-test CI session on the active Python.
- `python -m nox -s integration`: run the MongoDB-backed integration-test CI session on the active Python. Without `ARCTIC_TEST_MONGO_HOST`, this starts a local `mongod` if available.
- `python -m nox -s unit_matrix integration_matrix`: run the full local Python matrix only before high-risk pushes or when explicitly requested. It is too slow for routine edit cycles.
- `python -m pytest tests/unit/test_auth.py`: run a focused test file or directory.
- `git diff --check`: catch whitespace and conflict-marker issues before committing.
- `pycodestyle arctic tests`: check style using the ignore rules in `setup.cfg` when style-sensitive files are changed. Prefer focused checks during compatibility work.
- `mkdocs build`: build documentation locally when docs are changed.

Use a virtualenv for local work, for example `virtualenv .venv -p python3` and `source .venv/bin/activate`.

## Verification Policy

Use the narrowest useful verification first, then escalate based on risk and failures. Do not run full integration or full Python matrices after every small edit.

- For documentation-only changes: run `git diff --check`; no tests are required unless commands or examples changed.
- For small code edits: run `git diff --check`, compile touched modules if useful, and run the focused unit or integration test covering the changed path.
- For shared behavior changes in storage, dates, serialization, MongoDB, or pandas/numpy compatibility: run the focused tests first, then `python -m nox -s unit`; add targeted integration tests for the affected subsystem.
- Before pushing for CI validation: rely on GitHub Actions for the full supported Python matrix unless the change is high risk or CI failures need local reproduction.
- Run `python -m nox -s integration` or matrix sessions only when the change is cross-cutting, when preparing a release, or when explicitly requested.

## Coding Style & Naming Conventions

Prefer minimal, targeted changes that preserve the existing architecture. Follow the surrounding Python style: four-space indentation, explicit imports, readable functions, and descriptive snake_case names for modules, functions, and variables. Classes use `CamelCase`; constants use `UPPER_SNAKE_CASE`. Keep public APIs stable unless the change explicitly requires an API break. Run `pycodestyle` before submitting; avoid broad formatting-only diffs in legacy files.

## Testing Guidelines

Use `pytest`. Put fast isolated tests in `tests/unit/` and MongoDB-backed or end-to-end coverage in `tests/integration/`. Name test files `test_*.py` and test functions `test_*`. Add focused regression tests near the affected module, for example `tests/unit/chunkstore/` for `arctic/chunkstore/` changes. If an integration test needs external services, state that clearly in the PR.

GitHub Actions currently runs `nox` unit and integration-smoke sessions on Python 3.10 through 3.13. It also runs the full MongoDB-backed integration suite as a non-blocking diagnostic matrix because the legacy integration suite is not yet green on modern dependencies. MongoDB jobs use MongoDB 4.4.18 through a GitHub Actions service container.

Benchmarking is deferred to a later stage. The existing ASV and manual benchmark scripts in `benchmarks/` are stale, partly MongoDB-backed, and not suitable for required CI until they are modernized for the supported Python versions and isolated test data.

## Commit & Pull Request Guidelines

Recent history uses short imperative summaries and merge commits such as `pandas 2: is_monotonic was removed, replaced by is_monotonic_increasing`. Keep commit messages concise and specific; when committing from Codex, append `[codex]` to the commit message. Push only when explicitly prompted. Pull requests should describe the behavior changed, list tests run, link related issues when available, and call out compatibility risks for pandas, numpy, or pymongo.

## Security & Configuration Tips

Do not commit secrets, local connection strings, virtualenvs, generated coverage output, or `.env` files. Treat MongoDB credentials and test database names as local configuration. Before adding new tooling or dependencies, justify the maintenance cost and keep changes compatible with this legacy package.
