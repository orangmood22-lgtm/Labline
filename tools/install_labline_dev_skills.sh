#!/usr/bin/env bash
# install_labline_dev_skills.sh -- Dev-only skill installer for the LABLINE checkout.
#
# Scans to-developer/skills/dev-*/SKILL.md and links each dev skill directory
# into the current checkout's .agents/skills/dev-* surface. Managed entries are
# recorded in .labline/installed-dev-skills.txt. This script never touches .claude.

set -euo pipefail

MANIFEST_VERSION="1"
MANIFEST_NAME="installed-dev-skills.txt"
SOURCE_SKILLS_REL="to-developer/skills"
TARGET_SKILLS_REL=".agents/skills"
LABLINE_DIR_NAME=".labline"
SAFE_NAME_REGEX='^dev-[A-Za-z0-9][A-Za-z0-9._-]*$'

ACTION="auto" # auto | reconcile | detach | doctor
DRY_RUN=false
QUIET=false
MANIFEST_TMP=""
REPO_OVERRIDE=""

usage() {
    sed -n '2,40p' "$0" | sed 's/^# \?//'
}

log() {
    $QUIET && return 0
    echo "$*"
}

warn() {
    echo "warning: $*" >&2
}

die() {
    echo "error: $*" >&2
    exit 1
}

is_safe_name() {
    [[ "$1" =~ $SAFE_NAME_REGEX ]]
}

read_link_target() {
    readlink "$1"
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$script_dir/.." && pwd)"

resolve_repo_root() {
    if [[ -n "$REPO_OVERRIDE" ]]; then
        REPO_ROOT="$(cd "$REPO_OVERRIDE" && pwd)"
    fi
    SOURCE_SKILLS_DIR="$REPO_ROOT/$SOURCE_SKILLS_REL"
    TARGET_SKILLS_DIR="$REPO_ROOT/$TARGET_SKILLS_REL"
    LABLINE_DIR="$REPO_ROOT/$LABLINE_DIR_NAME"
    MANIFEST_PATH="$LABLINE_DIR/$MANIFEST_NAME"
}

SOURCE_SKILLS_DIR="$REPO_ROOT/$SOURCE_SKILLS_REL"
TARGET_SKILLS_DIR="$REPO_ROOT/$TARGET_SKILLS_REL"
LABLINE_DIR="$REPO_ROOT/$LABLINE_DIR_NAME"
MANIFEST_PATH="$LABLINE_DIR/$MANIFEST_NAME"

cleanup() {
    rm -f "$UPSTREAM_TMP" "$MANIFEST_DATA_TMP" "$MANIFEST_TMP"
}

check_parent_surface() {
    local p
    for p in "$LABLINE_DIR" "$REPO_ROOT/.agents" "$TARGET_SKILLS_DIR"; do
        if [[ -L "$p" ]]; then
            die "$p is a symlink; refusing to mutate symlinked parent directories"
        fi
    done
}

discover_upstream() {
    local d name
    shopt -s nullglob
    for d in "$SOURCE_SKILLS_DIR"/dev-*/; do
        [[ -d "$d" ]] || continue
        name="$(basename "$d")"
        [[ -f "$d/SKILL.md" ]] || continue
        is_safe_name "$name" || { warn "skipping unsafe dev skill name: $name"; continue; }
        printf "%s\t%s\n" "$name" "to-developer/skills/$name"
    done | sort -t$'\t' -k1,1
}

load_manifest_data() {
    local path="$1" out="$2"
    : > "$out"
    [[ -f "$path" ]] || return 0
    local ver
    ver="$(awk -F'\t' '$1=="version"{print $2; exit}' "$path")"
    [[ "$ver" == "$MANIFEST_VERSION" ]] || die "manifest version mismatch (got: ${ver:-none}, expected: $MANIFEST_VERSION)"
    awk -F'\t' '
        BEGIN { in_body=0 }
        /^kind\tname\tsource_rel\ttarget_rel\tmode$/ { in_body=1; next }
        in_body && NF==5 { print }
    ' "$path" > "$out"
}

write_manifest() {
    local upstream_data="$1" tmp="$2"
    {
        printf "version\t%s\n" "$MANIFEST_VERSION"
        printf "repo_root\t%s\n" "$REPO_ROOT"
        printf "source_root\t%s\n" "$SOURCE_SKILLS_REL"
        printf "target_root\t%s\n" "$TARGET_SKILLS_REL"
        printf "kind\tname\tsource_rel\ttarget_rel\tmode\n"
        awk -F'\t' -v target_root="$TARGET_SKILLS_REL" '{printf "skill\t%s\t%s\t%s/%s\tsymlink\n", $1, $2, target_root, $1}' "$upstream_data"
    } > "$tmp"
}

upstream_has_name() {
    local name="$1" data="$2"
    awk -F'\t' -v n="$name" '$1==n {found=1} END {exit found?0:1}' "$data"
}

install_or_reconcile() {
    local manifest_data="$1"
    local manifest_exists="$2"
    local allow_relink=false
    local allow_prune=false
    local name source_rel target_path expected_target current_target

    $manifest_exists && allow_relink=true && allow_prune=true
    [[ "$ACTION" == "reconcile" ]] && allow_relink=true && allow_prune=true

    if $DRY_RUN; then
        MANIFEST_TMP="$(mktemp)"
    else
        mkdir -p "$LABLINE_DIR" "$TARGET_SKILLS_DIR"
        MANIFEST_TMP="$(mktemp "$LABLINE_DIR/.installed-dev-skills.XXXXXX")"
    fi
    write_manifest "$UPSTREAM_TMP" "$MANIFEST_TMP"

    while IFS=$'\t' read -r name source_rel; do
        [[ -z "$name" ]] && continue
        target_path="$TARGET_SKILLS_DIR/$name"
        expected_target="$REPO_ROOT/$source_rel"

        if [[ -L "$target_path" ]]; then
            current_target="$(read_link_target "$target_path")"
            if [[ "$current_target" == "$expected_target" ]]; then
                log "reuse $name"
            elif $allow_relink; then
                if $DRY_RUN; then
                    log "(dry-run) relink $name -> $expected_target"
                else
                    rm -f "$target_path"
                    ln -s "$expected_target" "$target_path"
                    log "relink $name"
                fi
            else
                die "conflicting symlink at $target_path -> $current_target"
            fi
        elif [[ -e "$target_path" ]]; then
            die "refusing to overwrite real path: $target_path"
        else
            if $DRY_RUN; then
                log "(dry-run) ln -s $expected_target $target_path"
            else
                ln -s "$expected_target" "$target_path"
                log "link $name"
            fi
        fi
    done < "$UPSTREAM_TMP"

    if $allow_prune; then
        while IFS=$'\t' read -r kind name source_rel target_rel mode; do
            [[ -z "$name" ]] && continue
            upstream_has_name "$name" "$UPSTREAM_TMP" && continue
            target_path="$REPO_ROOT/$target_rel"
            if [[ -L "$target_path" ]]; then
                if $DRY_RUN; then
                    log "(dry-run) rm $target_path"
                else
                    rm -f "$target_path"
                    log "remove $name"
                fi
            elif [[ -e "$target_path" ]]; then
                die "refusing to remove non-symlink path: $target_path"
            fi
        done < "$manifest_data"
    fi

    if $DRY_RUN; then
        log "(dry-run) would write $MANIFEST_PATH"
    else
        mv -f "$MANIFEST_TMP" "$MANIFEST_PATH"
        MANIFEST_TMP=""
        log "wrote $MANIFEST_PATH"
    fi
}

detach() {
    local manifest_data="$1"
    local kind name source_rel target_rel mode target_path current_target expected_target
    if [[ -s "$manifest_data" ]]; then
        while IFS=$'\t' read -r kind name source_rel target_rel mode; do
            [[ -z "$name" ]] && continue
            target_path="$REPO_ROOT/$target_rel"
            if [[ -L "$target_path" ]]; then
                if $DRY_RUN; then
                    log "(dry-run) rm $target_path"
                else
                    rm -f "$target_path"
                    log "remove $name"
                fi
            elif [[ -e "$target_path" ]]; then
                die "refusing to remove non-symlink path: $target_path"
            fi
        done < "$manifest_data"
    else
        while IFS=$'\t' read -r name source_rel; do
            [[ -z "$name" ]] && continue
            target_path="$TARGET_SKILLS_DIR/$name"
            expected_target="$REPO_ROOT/$source_rel"
            if [[ -L "$target_path" ]]; then
                current_target="$(read_link_target "$target_path")"
                if [[ "$current_target" == "$expected_target" ]]; then
                    if $DRY_RUN; then
                        log "(dry-run) rm $target_path"
                    else
                        rm -f "$target_path"
                        log "remove $name"
                    fi
                fi
            fi
        done < "$UPSTREAM_TMP"
    fi

    if $DRY_RUN; then
        log "(dry-run) would remove $MANIFEST_PATH"
    else
        rm -f "$MANIFEST_PATH"
        log "removed manifest"
    fi
}

doctor() {
    local manifest_data="$1"
    local failures=0
    local name source_rel target_path expected_target current_target

    while IFS=$'\t' read -r name source_rel; do
        [[ -z "$name" ]] && continue
        target_path="$TARGET_SKILLS_DIR/$name"
        expected_target="$REPO_ROOT/$source_rel"
        if [[ ! -L "$target_path" ]]; then
            echo "missing: $name -> $target_path" >&2
            failures=1
            continue
        fi
        current_target="$(read_link_target "$target_path")"
        if [[ "$current_target" != "$expected_target" ]]; then
            echo "wrong target: $name -> $current_target (expected $expected_target)" >&2
            failures=1
        elif ! $QUIET; then
            echo "ok: $name"
        fi
    done < "$UPSTREAM_TMP"

    while IFS=$'\t' read -r kind name source_rel target_rel mode; do
        [[ -z "$name" ]] && continue
        upstream_has_name "$name" "$UPSTREAM_TMP" && continue
        target_path="$REPO_ROOT/$target_rel"
        if [[ -e "$target_path" || -L "$target_path" ]]; then
            echo "stale: $name -> $target_path" >&2
            failures=1
        fi
    done < "$manifest_data"

    return "$failures"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        install) ACTION="auto"; shift ;;
        update|--reconcile) ACTION="reconcile"; shift ;;
        detach|--detach) ACTION="detach"; shift ;;
        doctor|--doctor) ACTION="doctor"; shift ;;
        --labline-repo) REPO_OVERRIDE="${2:?missing value for --labline-repo}"; shift 2 ;;
        --dry-run) DRY_RUN=true; shift ;;
        --quiet) QUIET=true; shift ;;
        -h|--help) usage; exit 0 ;;
        --*) die "unknown option: $1" ;;
        *) die "unexpected positional argument: $1" ;;
    esac
done

resolve_repo_root
check_parent_surface

UPSTREAM_TMP="$(mktemp)"
MANIFEST_DATA_TMP="$(mktemp)"
trap cleanup EXIT

discover_upstream > "$UPSTREAM_TMP"
load_manifest_data "$MANIFEST_PATH" "$MANIFEST_DATA_TMP"
manifest_exists=false
[[ -f "$MANIFEST_PATH" ]] && manifest_exists=true

case "$ACTION" in
    doctor)
        $manifest_exists || die "manifest missing: $MANIFEST_PATH"
        doctor "$MANIFEST_DATA_TMP"
        ;;
    detach)
        detach "$MANIFEST_DATA_TMP"
        ;;
    auto|reconcile)
        install_or_reconcile "$MANIFEST_DATA_TMP" "$manifest_exists"
        ;;
    *)
        die "unknown action: $ACTION"
        ;;
esac
