# Changelog

All notable changes are documented here, following [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Releases use whole-repository [Semantic Versioning](https://semver.org/) tags (`vMAJOR.MINOR.PATCH`), not per-skill versions.

## [Unreleased]

### Added

- Portable skill repository structure, separate eval specs and fixtures, and authoring documentation.
- `scripts/validate.py` for static skill and eval validation.
- `scripts/link.sh` for live global skill symlinks.
- `scripts/eval.sh` for headless omp comparisons of no-skill, committed, and working-tree versions.
- CI workflow for static validation.
- `scripts/promote.sh` to move incubating skills and evals into the central checkout and link them globally.
- Project incubation in `<project>/.agents`, with skills and evals committed in the project.
- `scripts/eval.sh --root` and automatic project-root detection for evaluating skills in place.
- `scripts/validate.py --root` for static validation of any skills root.

### Changed

- Eval runs isolate the arm under test from live-linked global skills in `~/.agents/skills`.
- README now documents incubation, evaluation, promotion, and live-linked improvement as the skill lifecycle.
