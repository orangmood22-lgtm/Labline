#!/usr/bin/env bash
# Health check for ARIS GPU container deployments.

set -euo pipefail

FRAMEWORK="/aris/framework"
PROJECTS_ROOT="/aris/projects"
DATASETS="/aris/shared/datasets"
PROJECTS=()

usage() {
    cat <<'EOF'
Usage: deploy/aris_gpu_doctor.sh [options]

Options:
  --framework PATH       Framework path inside the checked environment
  --projects-root PATH   Projects root inside the checked environment
  --datasets PATH        Shared datasets path inside the checked environment
  --project NAME         Project to check; repeatable
  -h, --help             Show this help
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --framework) FRAMEWORK="${2:?--framework requires PATH}"; shift 2 ;;
        --projects-root) PROJECTS_ROOT="${2:?--projects-root requires PATH}"; shift 2 ;;
        --datasets) DATASETS="${2:?--datasets requires PATH}"; shift 2 ;;
        --project) PROJECTS+=("${2:?--project requires NAME}"); shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "unknown option: $1" >&2; exit 2 ;;
    esac
done

failures=0

fail() {
    echo "FAIL $*"
    failures=$((failures + 1))
}

repair_install_cmd() {
    local project_name="$1"
    echo "  repair: bash $FRAMEWORK/tools/install_aris.sh $PROJECTS_ROOT/$project_name --aris-repo $FRAMEWORK --quiet --no-doc"
}

check_project_skills() {
    local project_name="$1"
    local project_path="$PROJECTS_ROOT/$project_name"
    local skills_dir=""
    local link target
    local candidates=("$project_path/.agents/skills" "$project_path/.claude/skills")

    if [[ ! -d "$project_path" ]]; then
        fail "$project_name project: missing at $project_path"
        return
    fi

    for candidate in "${candidates[@]}"; do
        if [[ -d "$candidate" ]]; then
            skills_dir="$candidate"
            break
        fi
    done

    if [[ -z "$skills_dir" ]]; then
        fail "$project_name skills: missing .agents/skills or .claude/skills"
        repair_install_cmd "$project_name"
        return
    fi

    while IFS= read -r -d '' link; do
        target="$(readlink "$link")"
        if [[ "$target" != "$FRAMEWORK"/skills/* && "$target" != /aris/framework/skills/* ]]; then
            fail "$project_name skills: stale target outside framework"
            echo "  link: $link -> $target"
            repair_install_cmd "$project_name"
            return
        fi
    done < <(find "$skills_dir" -mindepth 1 -maxdepth 1 -type l -print0)

    echo "OK $project_name skills"
}

check_project_dataset() {
    local project_name="$1"
    local project_path="$PROJECTS_ROOT/$project_name"
    local dataset_path="$project_path/data/VOCdevkit"
    local shared_dataset="$DATASETS/VOCdevkit"

    if [[ ! -d "$project_path" ]]; then
        return
    fi
    if [[ ! -e "$shared_dataset" ]]; then
        fail "$project_name dataset: shared VOCdevkit missing at $shared_dataset"
        return
    fi
    if [[ -L "$dataset_path" ]]; then
        if [[ "$(readlink "$dataset_path")" != "$DATASETS/VOCdevkit" && "$(readlink "$dataset_path")" != "/aris/shared/datasets/VOCdevkit" ]]; then
            fail "$project_name dataset: symlink target is not container shared dataset"
            echo "  link: $dataset_path -> $(readlink "$dataset_path")"
            echo "  repair: rm $project_path/data/VOCdevkit && ln -s $DATASETS/VOCdevkit $project_path/data/VOCdevkit"
            return
        fi
        echo "OK $project_name dataset"
        return
    fi
    if [[ ! -e "$dataset_path" ]]; then
        fail "$project_name dataset: missing data/VOCdevkit"
        echo "  repair: mkdir -p $project_path/data && ln -s $DATASETS/VOCdevkit $project_path/data/VOCdevkit"
        return
    fi
    echo "OK $project_name dataset"
}

if [[ ${#PROJECTS[@]} -eq 0 ]]; then
    PROJECTS=(exp0516 exp0603)
fi

for project in "${PROJECTS[@]}"; do
    check_project_skills "$project"
    check_project_dataset "$project"
done

if [[ $failures -gt 0 ]]; then
    exit 1
fi

exit 0
