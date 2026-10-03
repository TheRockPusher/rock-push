# rock-push

A personal, portable [Agent Skills](https://agentskills.io/specification) collection, evaluated before changes are committed. Oh My Pi (`omp`) is the primary evaluation harness; skills also work with Claude Code, Codex, and `npx skills`.

## Layout

```text
skills/<name>/SKILL.md          # flat, one level; only skills/<name>/ is distributed
                               # optional references/, scripts/, assets/ inside
evals/<name>/evals.json         # trigger and outcome evaluation spec
evals/<name>/fixtures/<case>/   # fixture project copied to a temp dir per run
evals/<name>/checks/<case>.sh   # optional deterministic checker
evals/.results/                # gitignored run output
scripts/validate.py            # static checks
scripts/link.sh                # symlink skills into agent skill directories
scripts/eval.sh                # behavioral evals via headless omp
scripts/promote.sh             # move an incubating skill to the central checkout
.github/workflows/validate.yml # CI: validate only
README.md
CHANGELOG.md
AGENTS.md
```

## Install

There are no skills yet; installation becomes useful once the catalog has entries.

### Live global checkout

Clone to a stable path and link the skills:

```sh
git clone https://github.com/TheRockPusher/rock-push.git ~/src/rock-push
cd ~/src/rock-push
scripts/link.sh                            # ~/.agents/skills: omp / Codex
scripts/link.sh --target ~/.claude/skills   # Claude Code
```

These are symlinks: edits to installed skills from any project land in this checkout. On other machines, run `git pull` in the checkout and `scripts/link.sh` to receive updates.

No checkout? `npx skills add TheRockPusher/rock-push --skill <name>` gives a read-only copy with no flow-back.

## Lifecycle

**One skill, one place:** it lives in a project's `.agents` root while incubating or in this central checkout after promotion, never both. Project-only variants get a different name; skills that only make sense in one project are never promoted.

Requirements: Python 3 with PyYAML (`pip install pyyaml`) for validation; Python 3 and `omp` on `PATH` for behavioral evals.

1. **Incubate.** Create `<project>/.agents/skills/<name>/SKILL.md` and `<project>/.agents/evals/<name>/` with its spec, fixtures, and checks; commit both in the project's Git repository. Omp and Codex discover the project skill natively. For optional Claude Code exposure, run from the project root:
   ```sh
   mkdir -p .claude/skills
   ln -s ../../.agents/skills/<name> .claude/skills/<name>
   ```
2. **Evaluate in place.** From the project, run `~/src/rock-push/scripts/eval.sh <name>`; it automatically uses the project's `.agents` root, comparing the project's `HEAD` and working tree. Before the first project commit, use `--arms none,work`. Validate with `python ~/src/rock-push/scripts/validate.py --root <project>/.agents <name>`.
3. **Promote.** From the project, run `~/src/rock-push/scripts/promote.sh <name>`. It moves the skill and evals into the central checkout, removes the project copy, and links the skill globally. Commit the removal in the project and the addition in the central checkout, then push central.
4. **Improve.** From any project, edit through the global symlink into the central checkout. Evaluate there with `scripts/eval.sh <name>`, require no regression (`work` ≥ `head`), update the CHANGELOG, and commit/push there.

CI runs static validation only; behavioral evaluation is a local, model-backed check. See `scripts/eval.sh --help` for options, including `--root DIR` and optional LLM judging of expectations.

## Authoring rules

- Put each skill directly in `skills/<name>/SKILL.md`; no nested categories. Keep evals in `evals/<name>/`, never inside the distributed skill.
- Start `SKILL.md` with YAML frontmatter between `---` lines. Required `name` must match the directory, use lowercase letters/digits separated by single hyphens, and be 1–64 characters (`^[a-z0-9]+(-[a-z0-9]+)*$`).
- Required `description` is a non-empty string of at most 1024 characters, written in third person and stating what the skill does and when to use it.
- Allow only standard keys: `name`, `description`, `license`, `compatibility`, `metadata`, `allowed-tools`. `compatibility` is a 1–500-character string; `metadata` maps strings to strings; `license` and `allowed-tools` are strings.
- Keep the body at most 500 lines (validator warning above this). Move detail to `references/`, deterministic code to `scripts/`, and templates to `assets/` within the skill directory.
- Give every new skill an `evals/<name>/evals.json` with positive and negative trigger prompts and at least one outcome case. Each case needs a deterministic `check` or judge-only `expectations` (graded with `--judge`).

## Skills catalog

No skills yet.

| Skill | Purpose | Evals |
| --- | --- | --- |

## Inspiration

- [Cursor pstack](https://github.com/cursor/plugins/tree/main/pstack)
- [Matt Pocock's skills](https://github.com/mattpocock/skills)
- [Agent Skills specification](https://agentskills.io/specification)
- [Anthropic skills](https://github.com/anthropics/skills), particularly skill-creator's eval approach
