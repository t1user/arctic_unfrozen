# Repository Guidelines

## Purpose & Procedure

Project's purpose is to revive this long unmaintained repo. The target is to make it use latest version of dependencies including current version of python, mongo, pymongo, pandas and numpy. While being compatible with python 3.14, backward compatibility should be mainted with python 3.10. It's paramount not to break any functionality and keep existing interface. Subsequently new functionality and additional interface points may be added but it should be done while keeping full backwards compatibility. Don't make sweeping changes all at once, focus on the requested change. If warranted you may suggest next steps to achieve the overall purpose.

## Target Structure

All config in pyproject.toml, remove other config files to the extend possible
Checkers and linters: mypy, black, flake8
Testing: pytest

## Project Structure & Module Organization

This repository contains the legacy `arctic` Python package, now in maintenance mode. Core library code lives under `arctic/`, with major areas split into `chunkstore/`, `tickstore/`, `store/`, `serialization/`, `date/`, `asynchronous/`, and command-line entry points in `arctic/scripts/`. Tests are under `tests/`, separated into `tests/unit/` and `tests/integration/`. Documentation is in `docs/`, examples are in `howtos/`, performance work is in `benchmarks/`, and logo assets are in `logo/`.

## Build, Test, and Development Commands

- `python -m pip install -e .[test]`: install Arctic and test tooling into the active virtualenv.
- `python -m pytest tests/unit`: run the unit-test baseline used by GitHub Actions on Python 3.10 and 3.13.
- `python -m pytest tests/unit/test_auth.py`: run a focused test file or directory.
- `pycodestyle arctic tests`: check style using the ignore rules in `setup.cfg`.
- `mkdocs build`: build documentation locally when docs are changed.

Use a virtualenv for local work, for example `virtualenv .venv -p python3` and `source .venv/bin/activate`.

## Coding Style & Naming Conventions

Prefer minimal, targeted changes that preserve the existing architecture. Follow the surrounding Python style: four-space indentation, explicit imports, readable functions, and descriptive snake_case names for modules, functions, and variables. Classes use `CamelCase`; constants use `UPPER_SNAKE_CASE`. Keep public APIs stable unless the change explicitly requires an API break. Run `pycodestyle` before submitting; avoid broad formatting-only diffs in legacy files.

## Testing Guidelines

Use `pytest`. Put fast isolated tests in `tests/unit/` and MongoDB-backed or end-to-end coverage in `tests/integration/`. Name test files `test_*.py` and test functions `test_*`. Add focused regression tests near the affected module, for example `tests/unit/chunkstore/` for `arctic/chunkstore/` changes. If an integration test needs external services, state that clearly in the PR.

GitHub Actions currently runs `python -m pytest tests/unit` on Python 3.10 and 3.13. Keep this baseline green before expanding the matrix or adding integration-test jobs.

Benchmarking is deferred to a later stage. The existing ASV and manual benchmark scripts in `benchmarks/` are stale, partly MongoDB-backed, and not suitable for required CI until they are modernized for the supported Python versions and isolated test data.

## Commit & Pull Request Guidelines

Recent history uses short imperative summaries and merge commits such as `pandas 2: is_monotonic was removed, replaced by is_monotonic_increasing`. Keep commit messages concise and specific; when committing from Codex, append `[codex]` to the commit message. Push only when explicitly prompted. Pull requests should describe the behavior changed, list tests run, link related issues when available, and call out compatibility risks for pandas, numpy, or pymongo.

## Security & Configuration Tips

Do not commit secrets, local connection strings, virtualenvs, generated coverage output, or `.env` files. Treat MongoDB credentials and test database names as local configuration. Before adding new tooling or dependencies, justify the maintenance cost and keep changes compatible with this legacy package.
