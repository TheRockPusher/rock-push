# Changelog

All notable changes are documented here, following [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Releases use whole-repository [Semantic Versioning](https://semver.org/) tags (`vMAJOR.MINOR.PATCH`), not per-skill versions.

## [Unreleased]

### Added

- Portable skill repository structure, separate eval specs and fixtures, and authoring documentation.
- `scripts/validate.py` for static skill and eval validation.
- `scripts/link.sh` for live global skill symlinks.
- `scripts/eval.sh` for headless omp comparisons of no-skill, committed, and working-tree versions.
- CI workflow for static validation.
