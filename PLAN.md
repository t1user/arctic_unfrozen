# Project Plan

This repository is being restored as a maintained, backwards-compatible version of
the legacy `arctic` package. The priority is controlled modernization: keep
existing imports and behavior working while moving the project onto current
Python, pandas, numpy, pymongo, and MongoDB versions.

## 1. Keep the Unit Baseline Green

- Maintain GitHub Actions for Python 3.10 through 3.13.
- Keep `python -m pytest tests/unit` passing before broadening scope.
- Prefer small regression tests near the touched module.
- Use `nox` so contributors can run CI-equivalent checks before pushing.

## 2. Consolidate Tooling Configuration

- Move active project configuration into `pyproject.toml` where practical.
- Retire stale CI/config files once their behavior is replaced or confirmed
  obsolete. Legacy CircleCI has been replaced by GitHub Actions.
- Keep formatting changes narrow; avoid repository-wide reformatting until the
  compatibility work is stable.

## 3. Modernize Compatibility Hotspots

- Continue fixing breakages from modern pandas, numpy, pymongo, and Python.
- Preserve the public `arctic` package name and existing import paths.
- Prefer compatibility shims or focused rewrites over large architectural
  changes.
- Python 2 compatibility is no longer a target. Remove Python 2-only fixtures,
  skips, and compatibility branches when they are touched, while preserving
  Python 3 data compatibility.
- Document any intentional API break before making it.

## 4. Restore Integration Confidence

- Separate fast unit tests from MongoDB-backed integration tests.
- Define a repeatable local MongoDB setup for integration testing.
- Keep MongoDB-backed integration smoke tests blocking in CI across the
  supported Python matrix.
- Keep the full integration suite blocking in CI now that it is green across
  supported Python versions.
- Use plain `python -m pytest` as a full local confidence check, not a routine
  edit-cycle command; it runs unit plus integration tests and takes about 8
  minutes on the current Python 3.13 environment.

## 5. Improve Types Gradually

- Add type annotations opportunistically in touched files.
- Start with leaf modules and utility code before central storage APIs.
- Keep `python -m nox -s mypy` passing for the `arctic` package before broadening type strictness.
- Tighten typing by package slice rather than by adding broad `Any` annotations
  solely to satisfy `--disallow-untyped-defs`.
- Avoid type-only refactors that obscure behavior changes.

## 6. Revisit Benchmarks Later

- Treat the existing `benchmarks/` infrastructure as deferred work.
- Modernize benchmarks only after compatibility and integration tests are
  stable.
- Do not make benchmarks required in CI until they are deterministic, documented,
  and isolated from shared MongoDB state.

## 7. Release Readiness

- Update documentation once supported versions and setup commands settle.
- Verify packaging metadata and source distributions.
- Prepare a changelog section that separates compatibility fixes, tooling
  changes, and any user-visible behavior changes.
