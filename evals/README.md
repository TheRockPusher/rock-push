# Skill evaluations

Keep evaluations outside the distributed `skills/` directory. Each skill can have
an `evals/<name>/evals.json` file with trigger prompts, outcome cases, or both.
The matching `skills/<name>/` directory must exist.

## Skills roots

A skills root contains `skills/<name>/SKILL.md` and
`evals/<name>/{evals.json,fixtures/,checks/}`. The central root is this repository;
an incubating skill's root is `<project git toplevel>/.agents`, committed in the
project. A skill must live in only one root; promote it with `scripts/promote.sh`
or give a differing project variant another name.

`scripts/validate.py --root DIR [skill...]` validates any skills root, showing
paths relative to that root; without `--root`, it validates the central root.

## Spec format

This example is valid JSON; its referenced fixture and checker must also exist:

```json
{
  "skill_name": "example-skill",
  "trigger": {
    "positive": ["A request that should load example-skill"],
    "negative": ["A near-miss request that should not load example-skill"]
  },
  "evals": [
    {
      "id": "basic-case",
      "prompt": "Perform the task in this project",
      "expected_output": "A human-readable description of the intended result",
      "files": ["fixtures/basic-case"],
      "expectations": ["The response explains the result accurately"],
      "check": "checks/basic-case.sh"
    }
  ]
}
```

| Field | Requirement and meaning |
| --- | --- |
| `skill_name` | Required; equals this eval directory's name and an existing skill directory's name. |
| `trigger` | Optional object with `positive` and/or `negative` arrays of prompts. Positive prompts should load the skill; negative prompts should not. |
| `evals` | Optional array of outcome cases. At least one of `trigger` or `evals` must be present. |
| `evals[].id` | Required, unique case identifier matching `^[a-z0-9]+(-[a-z0-9]+)*$`. |
| `evals[].prompt` | Required, nonempty task prompt. |
| `evals[].expected_output` | Optional description for humans; not itself a pass/fail assertion. |
| `evals[].files` | Optional list of existing paths relative to `evals/<name>/`; each entry's contents are copied into the fresh run project's root. |
| `evals[].expectations` | Optional array of strings, graded by an LLM only with `--judge`. |
| `evals[].check` | Optional existing checker path relative to `evals/<name>/`, usually `checks/<id>.sh`. |

Every outcome case needs at least one of `check` or `expectations`. Use nonempty
expectations when relying on the judge alone. The core outcome fields are
compatible with Anthropic's skill-creator eval format; `trigger` is an extension.

## Fixtures and checks

Put fixture projects in `fixtures/<case-id>/` and deterministic checkers in
`checks/<case-id>.sh`. Each run gets a fresh temporary directory, the fixture
contents, a Git repository, and the selected skill version. Fixture paths are
relative, not absolute or parent-directory traversals. Reserve `.omp/skills/`
and the runner's artifact filenames for the runner.

Checkers run as `bash <absolute-check-path>` with the run project as their working
directory. They receive `OMP_OUTPUT`, the absolute path to `output.txt`, and
should inspect the produced project and/or assistant text. Exit zero means pass;
any other exit means fail. Checker output is saved separately. For example:

```bash
#!/usr/bin/env bash
set -euo pipefail
[[ -s result.txt ]]
grep -q 'expected explanation' "$OMP_OUTPUT"
```

A model error always fails the run. With `--judge`, all expectations must pass in
addition to the checker, when present. The judge sees the case prompt,
expectations, and final assistant text—not the complete modified filesystem.
Malformed judge replies fail closed. Expectations-only cases are marked
`skipped` without `--judge`, and are excluded from the run count.

## Arms and invocation

The runner requires Bash, `python3`, `git`, and `omp` on `PATH` (plus standard Unix
utilities). `--root DIR` explicitly selects a skills root. Otherwise, when run
inside another Git repository containing `.agents/skills/<skill>/SKILL.md`, it
uses that project's `.agents` root; otherwise it uses the central root. For a
project root, head comes from the project's `HEAD` and work from its working
tree. If the skill also exists centrally, the runner exits **2** with
`<skill> exists in both <project root> and <central>: promote or rename one`.
Arms run sequentially:

- **none**: no skills, using `--no-skills`; the outcome baseline.
- **head**: the skill directory from `HEAD`, including its auxiliary files. If
  that skill has never been committed, this arm is skipped with a notice.
- **work**: the skill directory from the current working tree.

For outcomes, head/work install their skill under the temporary project's
`.omp/skills/<name>/` and use `--skills <name>`. For triggers, only head/work run,
without a skill filter. A trigger is observed when `skill://<name>` appears in
the event stream; positive prompts must trigger it, and negative prompts must
not. Runs disable the `agents` discovery provider via a per-run
`.omp/config.yml` (`disabledProviders: [agents]`) so live-linked global skills
in `~/.agents/skills` can neither shadow nor compete with the arm under test.
Trigger runs therefore measure the skill's own description against prompts,
not competition with other global skills.

```bash
# All arms, three repeats per prompt, model smol (or EVAL_MODEL).
scripts/eval.sh example-skill

# Include semantic grading; choose the agent and judge models separately.
scripts/eval.sh example-skill --judge --model smol --judge-model smol

# Check description/trigger changes against HEAD.
scripts/eval.sh example-skill --only trigger --arms head,work --repeat 5

# Preserve full projects for outcome debugging.
scripts/eval.sh example-skill --only outcome --arms none,work --repeat 1 --keep

# From an incubating project; use none/work before its first skill commit.
~/src/rock-push/scripts/eval.sh example-skill --arms none,work

# Select a skills root explicitly.
scripts/eval.sh example-skill --root /path/to/project/.agents

scripts/eval.sh --help
```

Defaults are arms `none,head,work`, three repeats, and `--max-time 5m` per model
call. `EVAL_MODEL` overrides the default agent model; `EVAL_JUDGE_MODEL` overrides
the default judge model. Both otherwise default to `smol`.

## Results and decisions

Each invocation writes to `<root>/evals/.results/<UTC timestamp>-<skill>/`.
The results directory is self-gitignored, including in project roots:

- `meta.txt`: model names, runner options, `omp --version`, and the HEAD commit
  when that arm is available.
- `summary.tsv`: `kind`, `case`, `arm`, `passes`, `runs`, `rate`. Rates are pass
  fractions from 0 to 1; `n/a` means there were no graded runs.
- `verdicts.tsv`: one status per planned run, including skipped cases.
- `<arm>/<kind>-<case>-r<i>/`: `events.ndjson`, `output.txt`, `stderr.txt`, and
  `verdict.json`, plus checker/judge logs when used. Trigger case names are
  `positive-1`, `negative-1`, and so on. `--keep` also preserves the complete run
  project, including fixtures, changes, and `.git`/`.omp` directories.

Without `--keep`, temporary projects are deleted after saving their artifacts.
The runner prints a summary table and compares aggregate work/head pass rates
for each kind. It exits **1** if work has strictly fewer passes than head for any
evaluated kind; otherwise it exits **0**. A missing head arm is not a regression.
Invalid inputs or missing prerequisites exit **2**. Failing individual cases can
still exit zero when they do not regress—read the results, not just the exit
status.

**Commit only when work is at least as good as head and strictly better than
none on outcomes.** A new, uncommitted skill has no head baseline yet; establish
that baseline before claiming a work-versus-head comparison. Change a skill's
description only with trigger evidence, including near-miss negative prompts.
The automatic exit rule checks only regressions, not improvement over none.
Use equal prompts and repeat counts when comparing rates.

Every executed run is a model call: **runs = prompts × applicable arms ×
repeat**. Trigger prompts have no none arm. Skipped cases make no model call;
`--judge` adds another call for each outcome run with expectations. Keep results
private if prompts, fixtures, or model outputs contain sensitive information.
