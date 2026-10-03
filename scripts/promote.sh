#!/usr/bin/env bash
set -euo pipefail

usage() {
    printf 'Usage: %s <skill> [--root DIR]\nMove a project skill and its evals to rock-push and link it globally.\n' "${0##*/}"
}
fail() { printf 'error: %s\n' "$2" >&2; exit "$1"; }
central=$(realpath -- "$(dirname -- "${BASH_SOURCE[0]}")/..")
skill= root=
while (($#)); do
    case "$1" in
        --help|-h) usage; exit 0 ;;
        --root) (($# >= 2)) || fail 2 '--root requires DIR'; root=$2; shift 2 ;;
        -*) fail 2 "unknown option: $1" ;;
        *) [[ -z "$skill" ]] || fail 2 'expected one skill name'; skill=$1; shift ;;
    esac
done
[[ "$skill" =~ ^[a-z0-9]+(-[a-z0-9]+)*$ ]] || fail 2 'invalid or missing skill name'
if [[ -z "$root" ]]; then
    project=$(git rev-parse --show-toplevel 2>/dev/null) || fail 2 'run from a project Git repository or use --root'
    root=$project/.agents
fi
root=$(realpath -e -- "$root") || fail 2 'project skills root does not exist'
[[ -d "$root" && "$root" != "$central" ]] || fail 2 'root must be a project skills root, not rock-push'
[[ -f "$root/skills/$skill/SKILL.md" ]] || fail 2 "missing $root/skills/$skill/SKILL.md"
project=$(git -C "$root" rev-parse --show-toplevel 2>/dev/null) || fail 2 'project root must belong to a Git repository'
project=$(realpath -- "$project")
for path in "$central/skills/$skill" "$central/evals/$skill"; do
    [[ ! -e "$path" && ! -L "$path" ]] || fail 1 "central destination already exists: $path"
done
python3 "$central/scripts/validate.py" --root "$root" "$skill" || fail 1 'project skill validation failed'
[[ -f "$root/evals/$skill/evals.json" ]] || fail 1 'project skill requires evals/<skill>/evals.json'
rollback() { rm -rf -- "$central/skills/$skill" "$central/evals/$skill"; }
trap 'rollback; printf "error: promotion copy failed; project copies retained\n" >&2' ERR
mkdir -p -- "$central/skills" "$central/evals"
cp -a -- "$root/skills/$skill" "$central/skills/$skill"
cp -a -- "$root/evals/$skill" "$central/evals/$skill"
rm -rf -- "$central/evals/$skill/.results"
if ! python3 "$central/scripts/validate.py" "$skill"; then
    rollback; fail 1 'central validation failed; project copies retained'
fi
if ! "$central/scripts/link.sh" "$skill"; then
    "$central/scripts/link.sh" --unlink "$skill" || true
    rollback; fail 1 'global linking failed (a foreign entry may occupy the name); project copies retained'
fi
trap 'printf "error: project cleanup failed; central copies and global links retained\n" >&2' ERR
paths=("$root/skills/$skill" "$root/evals/$skill")
claude=$project/.claude/skills/$skill
if [[ -L "$claude" && "$(readlink -f -- "$claude")" == "$(realpath -- "$root/skills/$skill")" ]]; then
    paths+=("$claude")
fi
for path in "${paths[@]}"; do
    relative=${path#"$project"/}
    if [[ -n "$(git -C "$project" ls-files -- "$relative")" ]]; then
        git -C "$project" rm -r -q -- "$relative"
    fi
    rm -rf -- "$path"
done
trap - ERR
printf 'Promoted %s. Next steps:\n' "$skill"
printf '  git -C %q commit -m %q\n' "$project" "Promote $skill to rock-push"
printf '  cd %q\n  Update README catalog + CHANGELOG.\n' "$central"
printf '  scripts/eval.sh %s --arms none,work  # no central HEAD yet\n' "$skill"
printf '  git add skills/%s evals/%s README.md CHANGELOG.md && git commit && git push\n' "$skill" "$skill"
