# ARIS Framework Governance

Language for ARIS framework versioning, release, and branch governance.

## Language

**Version Management**:
The release governance for ARIS framework versions: release tags, changelog entries, and project-level framework pins. Branches support this process, but branch naming alone is not version management.
_Avoid_: using "version management" to mean only Git branch cleanup.

**Feature Branch**:
A short-lived branch for adding a new capability or changing behavior before it is ready for `dev` or `main`. A feature branch may include code, docs, tests, templates, or skill changes; it differs from a fix branch because the goal is new capability rather than restoring broken behavior.
_Avoid_: experiment branch, random dev branch

**Fix Branch**:
A short-lived branch for correcting an existing broken behavior, documentation error, deployment issue, or compatibility regression.
_Avoid_: hotfix unless the change must go directly to a released stable line.

**Stable Line**:
The `main` branch, containing released or release-ready ARIS framework state.
_Avoid_: orangmood edition branch, production branch

**Development Line**:
The `dev` branch, containing integrated but not-yet-released ARIS framework changes.
_Avoid_: scratch branch, personal branch

**Semantic Version**:
A framework release tag using `vMAJOR.MINOR.PATCH`. Before ARIS reaches `v1.0.0`, minor versions carry user-visible capability changes and patch versions carry fixes that do not change normal usage.
_Avoid_: date-only version, branch name as version

**Patch Release**:
A release that increments only `PATCH`, such as `v0.1.0` to `v0.1.1`, for bug fixes, documentation corrections, deployment fixes, or compatibility repairs.
_Avoid_: calling new features patch releases

**Minor Release**:
A release that increments `MINOR`, such as `v0.1.0` to `v0.2.0`, for new user-visible skills, tools, deployment support, client compatibility, or workflow capability.
_Avoid_: bundling breaking installation changes without calling them out

**Formal Release Tag**:
A stable release tag on `main`, such as `v0.1.0` or `v0.1.1`, intended for users and research projects to pin in `project.yaml`.
_Avoid_: tagging feature branches as releases

**Prerelease Tag**:
A temporary test tag, such as `v0.2.0-dev.1` or `v0.2.0-rc.1`, used only to pin a `dev` or release-candidate snapshot for server testing or multi-user validation.
_Avoid_: treating prerelease tags as stable project defaults

**Release Trigger**:
A reason to publish a new framework version from `main`. User-visible capability changes trigger a minor release; user-relevant fixes that preserve normal usage trigger a patch release; internal notes and `to-developer/` materials do not trigger releases.
_Avoid_: releasing every commit automatically

**User Changelog**:
The user-facing `CHANGELOG.md` release note. It records only changes users need to know when deciding whether to upgrade or pin a new framework version.
_Avoid_: commit-by-commit logs, internal implementation diary

**Development Log**:
The maintainer-facing module log in the dev checkout. It groups changes by framework module so maintainers do not need to reconstruct history from individual commits. It is not part of stable framework releases.
_Avoid_: putting maintainer-only module notes in `CHANGELOG.md`

**Developer Material**:
Maintainer-facing planning, discussion, handoff, validation, and ADR files kept in the dev checkout. They are not part of stable framework releases.
_Avoid_: committing credentials, host secrets, API keys, or private SSH notes

**Release Gate**:
The checklist that must pass before tagging a framework release. Patch releases use a lightweight gate focused on the changed area; minor releases use a stricter gate covering changelog, development log, generated catalogs/DAGs, installer behavior, Codex mirror compatibility, and at least one install or dev-to-stable validation.
_Avoid_: tagging first and checking later

**Release Tag Automation**:
The guarded scripts that check and create framework release tags. Tag automation defaults to dry-run, creates a local tag only with `--apply`, and pushes the tag only with the additional `--push-tag` flag.
_Avoid_: scripts that create or push tags by default

**Version Bump**:
An explicit request to compute the next semantic version from the latest formal release tag, such as `--bump patch` or `--bump minor`. Maintainers may also provide an explicit `vMAJOR.MINOR.PATCH` when needed, but the release script must validate that it is newer than the latest formal release.
_Avoid_: implicit version inference from arbitrary commit messages

**Initial Stable Release**:
The first formal ARIS framework release from the current `main` line, tagged `v0.1.0`. It establishes the baseline that research projects can pin before later patch and minor releases.
_Avoid_: treating pre-`v0.1.0` branch names as framework versions

**In-Place Project Initialization**:
Preparing the current directory as an ARIS research project by passing `.` as the project path to the project initialization command. This is the beginner-facing path when the user has already created an empty or existing project folder.
_Avoid_: assuming an empty folder already has ARIS commands installed

**New Project Creation**:
Creating or selecting an ARIS research project directory by passing a non-`.` path to the project initialization command, then preparing that directory as an ARIS research project.
_Avoid_: using "init project" ambiguously for both directory creation and current-directory setup

**ARIS CLI**:
The beginner-facing command entrypoint for installing, initializing, updating, and inspecting ARIS from a normal shell. It separates project-scoped commands under `aris project ...` from framework-scoped commands under `aris framework ...`.
_Avoid_: exposing script names as the primary beginner workflow

**Runnable Project Baseline**:
The minimum state in which a directory is recognizably an ARIS research project and can be opened by supported agent clients without additional manual scaffolding. It includes project metadata, agent instructions, standard project folders, local framework installation records, and an initial version-control baseline.
_Avoid_: treating skill symlink installation alone as a complete project initialization

**Experiment Transparency Ledger**:
A project-level evidence trail that records experiment blocks, runs, data splits, metric definitions, implementation deviations, result artifacts, and human checkpoint decisions as experiments progress. It is the canonical transparency surface for later audit and claim evaluation.
_Avoid_: treating post-hoc audit reports as the only transparency mechanism

**Fixed Checkpoint**:
A predefined human decision point in a workflow, such as before launching experiments, after an experiment block finishes, or when a deviation or anomaly is detected. Fixed checkpoints are the first-stage human-in-the-loop mechanism before introducing a general workflow runtime.
_Avoid_: arbitrary runtime interruption as a first implementation requirement

**Workflow Runtime**:
An optional execution backend for stateful, resumable, interruptible ARIS workflows. It may consume project artifacts and ledgers, but it must not replace the static skill protocol or make ordinary ARIS project initialization depend on a runtime engine.
_Avoid_: making LangGraph or another runtime a core project format requirement

**Project Detach**:
Removing ARIS integration from an existing project while leaving project-owned content intact. It removes framework-managed links, manifests, and managed metadata, but it does not delete the research project itself.
_Avoid_: uninstall, delete project, remove project directory

**Agent Status Stream**:
A shared local visibility channel that lets the Leader observe what delegated agents are doing while they run. It is for liveness, progress, blockers, and artifact pointers; it is not a task queue, planning surface, or peer-to-peer agent coordination mechanism.
_Avoid_: agent chat room, hidden scheduler, replacing Pipeline Status

**Agent Status Snapshot**:
The compact current-state view that the Leader reads from the Agent Status Stream during normal orchestration. It summarizes each active agent's role, task, liveness, current action, blockers, artifact pointers, and expected next update without exposing the full event history.
_Avoid_: full transcript, verbose scratch log, agent memory dump

**Agent Status File**:
A per-agent local file that contains exactly one agent's current Agent Status Snapshot. Each delegated agent owns its own status file, while the Leader reads those files to aggregate progress without requiring agents to write into a shared mutable snapshot.
_Avoid_: shared agent state file, central writable scratchpad

**Long-Running Job Handle**:
A durable pointer to a long-running task that can be checked independently of the agent that launched it, such as a tmux or screen session name, queue state file, watchdog task name, log path, or result directory. The Leader treats the job handle as the source of truth for task liveness when an agent status file stops updating.
_Avoid_: foreground SSH command, agent transcript as progress source

**Expected Update Time**:
The next time an agent or its associated long-running job is expected to provide a meaningful new signal. It is a pacing hint for Leader observation, not a deadline or failure condition by itself.
_Avoid_: timeout, SLA, polling loop

**Read-Only Status Check**:
A non-mutating check that the Leader may perform when an Expected Update Time arrives, such as reading status files, queue state, watchdog summaries, logs, or monitor outputs. It must not restart jobs, change configuration, deploy code, or mutate project artifacts.
_Avoid_: recovery action, automatic intervention

**Reviewer Role**:
The independent review role in ARIS that audits plans, code, results, claims, citations, or paper artifacts from original inputs. The role may be implemented through an MCP-backed model call, a spawned agent, or a separate CLI session depending on platform, but its independence contract is the same.
_Avoid_: equating Reviewer with Codex MCP only, executor self-review

**Project Runtime State**:
Local, non-versioned state written inside a research project while ARIS workflows run, such as agent status snapshots and transient coordination metadata. The ARIS framework repository provides tools and protocols for this state but must not contain real project runtime state.
_Avoid_: framework-owned runtime status, committed agent snapshots

**Project Registry**:
A non-versioned registry in a User Workspace that records ARIS project paths initialized for that user. Framework updates use it to keep registered projects in sync with the user's framework copy, and project detach removes projects from it.
_Avoid_: framework repo state, global project database, manually maintained project list

**Codex Session**:
A live local Codex CLI process that can read project files, request approvals, and update Project Runtime State. A previous closed thread is historical context; it can be recovered from artifacts or traces into a new Codex Session, but it is not itself a controllable live session.
_Avoid_: using thread to mean both a live process and past conversation history

**Remote Action Approval**:
A Feishu-mediated approval for one explicitly described action requested by a live Codex Session. It is not a session-wide permission grant; each approval is scoped to a single pending action and expires if unused.
_Avoid_: remote shell, global session authorization, approve-all mode

**Remote Session Inbox**:
A Feishu-mediated input channel that delivers user messages to a live Codex Session. The bridge records messages and returns session responses, but tool and skill execution still happens inside the Codex Session under the normal local permission model.
_Avoid_: bridge-executed tools, remote agent runner, Feishu shell

**Feishu-Controlled Session**:
An opt-in Codex Session that is registered for Remote Session Inbox messages, Remote Action Approval, status reporting, and response forwarding through Feishu. Sessions that never opt in are invisible to Feishu control.
_Avoid_: auto-attached session, hijacked terminal, uncontrolled thread takeover

**Active Remote Session**:
The Feishu-Controlled Session that receives unqualified Feishu messages by default. Users may list sessions, switch the active session, or address a specific session explicitly without implying that historical closed threads are still live.
_Avoid_: broadcast-to-all sessions, implicit old-thread control

**Control Lease**:
The temporary ownership marker for a Feishu-Controlled Session's user input stream. A lease may belong to local input or Feishu input; Feishu can take priority while the user is away, but the lease expires or can be released so local control can resume.
_Avoid_: simultaneous unsynchronised input, permanent remote lockout

**Phone Session Report**:
A mergeable record of work performed through a Feishu-Controlled Session while the user is away. It captures auditable facts such as messages, responses, commands, file changes, decisions, and open questions; it is not a dump of hidden model context.
_Avoid_: transcript merge, hidden context merge, memory graft

**User Workspace**:
The administrator-assigned research workspace for one ARIS user in a managed deployment. A User Workspace owns that user's framework copy and project area while sharing group-level research assets.
_Avoid_: shared project folder, everyone in one container, framework shared by all users

**User-Owned Framework Copy**:
The framework checkout inside one User Workspace whose version may be updated, pinned, or rolled back independently by that user. Administrators may provide a default baseline and inspect versions, but they do not silently overwrite a user's framework copy.
_Avoid_: globally shared framework, admin-only framework version, implicit forced upgrade

**Workspace Framework Rollback**:
Returning a User-Owned Framework Copy to the last known working framework commit after an update causes problems. It is a user-level recovery action, not a per-project version pin.
_Avoid_: project rollback, multi-project version matrix, forced admin downgrade

**Framework Update Check**:
A non-destructive check that tells a user whether their User-Owned Framework Copy is behind its configured upstream. It may inform the user that an update is available, but it does not change the working framework version or resync projects.
_Avoid_: automatic upgrade, silent pull, forced admin refresh

**Shared Research Assets**:
Group-level assets reused across User Workspaces, such as datasets, pretrained models, and download caches. They are not owned by a single project or user.
_Avoid_: per-user dataset copy, project-owned pretrained cache

## Example Dialogue

Developer: "This is a new skill workflow, so I will open a feature branch from `dev`."

Maintainer: "Good. When it is reviewed and tested, merge it back to `dev`. It becomes version-managed only when we include it in a release tag and changelog."

Developer: "This installer bug breaks existing projects."

Maintainer: "Use a fix branch. If it affects the current stable release, it may become a patch release."

Developer: "This release adds Codex/Claude dual-client skill governance."

Maintainer: "That is a minor release before v1.0.0. Tag it as something like `v0.1.0`, then use patch releases for follow-up fixes."

Developer: "Can I tag the current dev branch?"

Maintainer: "Only as a prerelease snapshot when you need reproducible testing, for example `v0.2.0-dev.1`. Formal release tags belong on `main`."

Developer: "I only updated internal planning notes."

Maintainer: "Do not release. Internal `to-developer/` changes are not framework version changes."

Developer: "This change touched skills, tools, and docs. Where do I record the developer detail?"

Maintainer: "Record it by module in the dev-only development log, then distill only user-visible entries into `CHANGELOG.md` at release time."

Developer: "Should developer notes be committed?"

Maintainer: "Keep structured developer material in the dev checkout, but never commit private settings, API keys, or SSH notes."

Developer: "This is only a patch release for a deployment doc fix."

Maintainer: "Use the patch release gate: clean worktree, changelog entry, development log entry, and the related test or manual check. Save the full minor gate for capability releases."

Developer: "Can the release script create the tag for me?"

Maintainer: "Yes, but it must be guarded. The default run is a dry-run; `--apply` creates the local tag; `--push-tag` is required to publish it."

Developer: "Should I type the exact version?"

Maintainer: "Either use `--bump patch` / `--bump minor` for normal releases, or provide an explicit `vX.Y.Z` for special cases. In both cases the script validates the result."

Developer: "What is the first stable version?"

Maintainer: "The current `main` line becomes `v0.1.0`; future fixes become `v0.1.1`, and future capability releases become `v0.2.0` or later."
