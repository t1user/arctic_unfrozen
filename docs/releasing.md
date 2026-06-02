# Releasing Arctic Unfrozen

Release automation for the maintained `arctic_unfrozen` distribution is not
yet established. Do not upload artifacts until the publishing destination,
credentials, and release approval process are documented.

## Pre-release Checklist

1. Update the version in `pyproject.toml`.
1. Move the relevant notes from `Unreleased` into a versioned section in
   `CHANGES.md`.
1. Run the unit, mypy, and MongoDB-backed integration sessions described in
   `AGENTS.md`.
1. Build the documentation with `python -m mkdocs build --strict`.
1. Build a wheel and source distribution with `python -m build`.
1. Install the wheel into a clean virtualenv and verify imports and CLI entry
   points.
1. Tag the approved release and push the tag.

## Publishing

Add the final artifact-signing and upload commands here before the first Arctic
Unfrozen release. The legacy `setup.py upload` workflow is obsolete.
