## Goal

Create a personal skill repository/plugin

## Rules

Always read  omp://skills.md 

## Inspiration

[pstack](https://github.com/cursor/plugins/tree/main/pstack)

[matt skills](https://github.com/mattpocock/skills)

## Best  practices

[claude](https://claude.com/docs/skills/how-to)

## Repo conventions

- Skills are flat: `skills/<name>/SKILL.md`, with optional `references/`, `scripts/`, and `assets/` inside. Only the skill directory is distributed.
- Keep evals outside skills: `evals/<name>/evals.json`, fixtures in `evals/<name>/fixtures/<case>/`, optional checkers in `evals/<name>/checks/<case>.sh`; run output belongs in gitignored `evals/.results/`.
- Incubate skills in `<project>/.agents/skills/<name>/` and their evals in `<project>/.agents/evals/<name>/`; commit both in the project.
- Promote reusable skills with `scripts/promote.sh <name>` from the project, then commit the removal in the project and the addition in the central checkout.
- One skill, one place: project incubation or central promotion, never both. Differing project variants need different names; project-only skills are never promoted.
- `scripts/validate.py --root DIR` validates a skills root; `scripts/eval.sh <skill>` auto-detects a project's `.agents` root when its skill exists, or accepts `--root DIR`.
- Tooling lives in `scripts/validate.py`, `scripts/link.sh`, `scripts/eval.sh`, and `scripts/promote.sh`; `.github/workflows/validate.yml` runs static validation only.
- Begin `SKILL.md` with YAML frontmatter between `---` lines. Only `name`, `description`, `license`, `compatibility`, `metadata`, and `allowed-tools` are allowed.
- Required `name` equals the directory name, is 1–64 characters, and matches `^[a-z0-9]+(-[a-z0-9]+)*$`. Required `description` is a non-empty string of at most 1024 characters, in third person, explaining what and when.
- Optional `compatibility` is a 1–500-character string; `metadata` maps strings to strings; `license` and `allowed-tools` are strings. Keep the body at most 500 lines; move detail, code, and templates to their respective subdirectories.
- Validate every skill change with `python scripts/validate.py` and evaluate it with `scripts/eval.sh <skill>` before committing. Compare `none`/`head`/`work`; require `work` ≥ `head` with no regression.
- With every new skill, add or extend `evals/<name>/evals.json` with positive and negative trigger prompts and at least one outcome case. Each case must have a deterministic `check` or judge-only `expectations`; use `--judge` to grade expectations.
- Update the README catalog and CHANGELOG when adding or changing skills. Releases use whole-repo semver tags.
- Never put harness-specific frontmatter such as `hide`, `enabled`, or `disable-model-invocation` in skills.


## Extra

Use UV and not pip. 
