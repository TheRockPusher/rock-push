#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
Usage: scripts/link.sh [--target DIR]... [--unlink] [--prune] [--dry-run] [skill...]

Link all skills, or only the named skills, into each target directory.
Targets come from repeated --target options, then colon-separated SKILL_TARGETS,
then $HOME/.agents/skills (used by omp and Codex). To also support Claude Code:

  scripts/link.sh --target "$HOME/.agents/skills" --target "$HOME/.claude/skills"

  --target DIR  Choose a target directory; may be repeated.
  --unlink      Remove only symlinks resolving into this checkout's skills/.
  --prune       Remove dangling symlinks resolving into this checkout's skills/.
                Pruning covers all names in each target, even deleted skills.
  --dry-run     Print actions without changing anything.
  --help        Show this help.

Existing files, directories, and links to other locations are never replaced.
Exit status: 0 = success, 1 = conflict or filesystem error, 2 = invalid arguments.
EOF
}

fail_usage() {
    printf 'error: %s\n' "$1" >&2
    exit 2
}

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repo_root=$(realpath -- "$script_dir/..")
skills_root=$(realpath -m -- "$repo_root/skills")
targets=()
requested=()
unlink=false
prune=false
dry_run=false

while (($#)); do
    case "$1" in
        --help|-h) usage; exit 0 ;;
        --target)
            (($# >= 2)) || fail_usage '--target requires a directory'
            [[ -n $2 ]] || fail_usage '--target requires a non-empty directory'
            targets+=("$2")
            shift 2
            ;;
        --unlink) unlink=true; shift ;;
        --prune) prune=true; shift ;;
        --dry-run) dry_run=true; shift ;;
        --) shift; requested+=("$@"); break ;;
        -*) fail_usage "unknown option: $1" ;;
        *) requested+=("$1"); shift ;;
    esac
done

if ((${#targets[@]} == 0)); then
    if [[ -n ${SKILL_TARGETS:-} ]]; then
        [[ $SKILL_TARGETS != :* && $SKILL_TARGETS != *: && $SKILL_TARGETS != *::* ]] ||
            fail_usage 'SKILL_TARGETS contains an empty directory'
        IFS=: read -r -a targets <<< "$SKILL_TARGETS"
    else
        [[ -n ${HOME:-} ]] || fail_usage 'HOME is unset; use --target'
        targets=("$HOME/.agents/skills")
    fi
fi

shopt -s nullglob dotglob
available=()
for skill_dir in "$skills_root"/*; do
    [[ -d $skill_dir && -f $skill_dir/SKILL.md ]] || continue
    available+=("${skill_dir##*/}")
done

selected=("${available[@]}")
if ((${#requested[@]})); then
    selected=()
    for name in "${requested[@]}"; do
        found=false
        for known in "${available[@]}"; do
            if [[ $name == "$known" ]]; then
                found=true
                break
            fi
        done
        $found || fail_usage "unknown skill: $name"
        # Repeated names should not produce duplicate actions (including dry runs).
        duplicate=false
        for known in "${selected[@]}"; do
            [[ $name != "$known" ]] || duplicate=true
        done
        $duplicate || selected+=("$name")
    done
fi

status=0
# realpath -m resolves existing symlinks and also canonicalizes dangling targets.
# The trailing slash boundary excludes similarly named sibling directories.
is_owned_link() {
    [[ -L $1 ]] || return 1
    local resolved
    resolved=$(realpath -m -- "$1") || return 1
    [[ $resolved == "$skills_root/"* ]]
}
if ((${#available[@]} == 0)) && ! $unlink && ! $prune; then
    printf 'no skills to link\n'
    exit 0
fi


remove_link() {
    local path=$1 action=$2
    if $dry_run; then
        printf 'would %s %s\n' "$action" "$path"
    elif rm -- "$path"; then
        printf '%s %s\n' "$action" "$path"
    else
        status=1
    fi
}

processed_targets=()
for target in "${targets[@]}"; do
    target=$(realpath -m -- "$target")
    duplicate=false
    for known in "${processed_targets[@]}"; do
        [[ $target != "$known" ]] || duplicate=true
    done
    $duplicate && continue
    processed_targets+=("$target")

    if [[ ! -d $target ]]; then
        if $dry_run; then
            printf 'would mkdir %s\n' "$target"
        elif ! mkdir -p -- "$target"; then
            status=1
            continue
        fi
    fi

    if $unlink; then
        if ((${#requested[@]})); then
            candidates=()
            for name in "${selected[@]}"; do
                candidates+=("$target/$name")
            done
        else
            candidates=("$target"/*)
        fi
        for path in "${candidates[@]}"; do
            if is_owned_link "$path"; then
                remove_link "$path" unlinked
            fi
        done
    fi

    if $prune; then
        for path in "$target"/*; do
            if [[ ! -e $path ]] && is_owned_link "$path"; then
                # In a dry run --unlink has already described this same removal.
                if $dry_run && $unlink; then
                    if ((${#requested[@]} == 0)); then
                        continue
                    fi
                    already_selected=false
                    for name in "${selected[@]}"; do
                        [[ $path != "$target/$name" ]] || already_selected=true
                    done
                    $already_selected && continue
                fi
                remove_link "$path" pruned
            fi
        done
    fi

    $unlink && continue
    for name in "${selected[@]}"; do
        source=$(realpath -- "$skills_root/$name")
        path=$target/$name
        if [[ -L $path ]] && [[ $(realpath -m -- "$path") == "$source" ]]; then
            printf 'ok %s\n' "$path"
        elif [[ -e $path || -L $path ]]; then
            printf 'SKIP %s (exists, not ours)\n' "$path"
            status=1
        elif $dry_run; then
            printf 'would link %s -> %s\n' "$path" "$source"
        elif ln -s -- "$source" "$path"; then
            printf 'linked %s -> %s\n' "$path" "$source"
        else
            status=1
        fi
    done
done

if ((${#available[@]} == 0)); then
    printf 'no skills to link\n'
fi
exit "$status"
