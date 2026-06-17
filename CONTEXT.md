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

**Semantic Root**:
The top-level glossary and language reference for ARIS framework governance. `CONTEXT.md` is the Semantic Root: it does not replace implementation docs, but it defines the shared meaning that lower-level plans, ADRs, skills, and archives should stay consistent with.
_Avoid_: treating the glossary as a throwaway note, duplicating root semantics in every other document

**Feature Decision Lineage**:
The trace from a feature or workflow change back through the relevant context archive, ADR, plan, implementation change, and validation artifacts. It makes each upgrade or behavior change auditable without requiring every document to directly depend on `CONTEXT.md` in a literal DAG edge.
_Avoid_: relying on memory to reconstruct why a feature changed, forcing every document to point at the glossary directly

**Grilling Context Archive**:
A dated, topic-scoped archive of the context changes and decisions produced by a Design Grilling session. The active `CONTEXT.md` remains the current glossary, while archived copies preserve historical reasoning and topic evolution for later reference. Archive placement is context-specific and belongs to the documentation governance layer rather than the glossary.
_Avoid_: replacing the active glossary with scattered historical notes, losing the reasoning behind major context changes

**Global Context Sweep**:
The mandatory breadth check at the start of Design Grilling. It keeps the discussion connected to the project goal, active workflow, role boundaries, skill graph, experiment integrity, human checkpoints, and user-facing or developer-facing documentation impact before narrowing into a local decision. It is an internal grilling obligation by default, not a required standalone artifact, and it must not override the one-question-at-a-time interaction rule.
_Avoid_: resolving a local term while ignoring adjacent workflow, role, evidence, or documentation consequences; treating grilling as a whole-library skill-audit tool

**ARIS Role**:
A stable responsibility boundary such as Leader, Planner, Coder, Deployer, Writer, or Reviewer. A role describes what work is allowed and what independence or handoff contract applies; it does not imply a specific model, process, MCP server, or CLI session.
_Avoid_: defining responsibilities by whichever transport happens to run them today

**Role Transport**:
The implementation mechanism used to run a role, such as the current Codex session, a spawned local agent, a separate CLI session, an MCP-backed model, or an OpenAI-compatible API provider. Transport changes must not change the role's responsibility contract.
_Avoid_: treating a model/provider switch as a skill architecture change

**Logical Skill Graph**:
The transport-independent graph of roles, skills, workflow modules, and declared dependency edges. It describes allowed invocation and reference structure, not the current runtime binding to a model or API.
_Avoid_: mixing model/provider configuration into skill topology

**Runtime Binding View**:
The current mapping from roles to concrete transports, models, sessions, providers, and credentials. It can vary per deployment or project while the Logical Skill Graph stays stable.
_Avoid_: hard-coding cheap worker or reviewer topology into prose mentions

**Skill Invocation Edge**:
A machine-readable edge saying one skill or workflow step may call, delegate to, or require another skill. It must come from structured metadata or an explicit governance file, not from casual prose mention.
_Avoid_: inferring runtime dependencies from a skill name appearing in documentation

**Skill Reference Edge**:
A machine-readable edge saying one skill or document is human-facing context for another. A reference edge helps readers navigate but is not a runtime dependency.
_Avoid_: letting references trigger implicit calls

**Skill List Entry**:
A discovery edge that puts a skill into a catalog, menu, capability list, or queryable inventory. It affects discovery and selection, but it does not by itself authorize invocation.
_Avoid_: treating catalog membership as caller permission

**Unclassified Skill Mention**:
An occurrence of a skill, role, or workflow name in prose that has not been classified as invocation, reference, list entry, or another explicit semantic edge. Architecture-critical documents should not keep unclassified mentions.
_Avoid_: ambiguous dependency prose that tools cannot interpret

**Experiment Integrity Workflow**:
A persistent, project-local workflow/module that keeps experiment transparency visible throughout the research process. It is not a one-shot skill; it records checkpoints, ledger entries, evidence pointers, and audit-facing summaries that humans can inspect at any time.
_Avoid_: treating integrity verification as a final report after results are already selected

**Experiment Integrity Verification**:
A node or activity inside the Experiment Integrity Workflow that checks whether an experiment claim is backed by transparent data split, metric, code, config, run artifact, and deviation records. It is not the name of the whole workflow.
_Avoid_: using verification to mean the entire integrity system

**Experiment Integrity Entry Point**:
A single human-facing summary artifact for the current integrity state of a project. It is the first audit-facing place to look for status, evidence pointers, and unresolved checkpoints. The checkpoint queue is separate from this summary, and live status snapshots stay in Project Runtime State.
_Avoid_: scattering the integrity state across unrelated chat messages or making users hunt through the full ledger first

**Checkpoint Queue**:
The fixed list of pending human checkpoint decisions in an experiment workflow. It is the minimum first-stage human-in-the-loop mechanism and does not replace future general interruption support.
_Avoid_: arbitrary hidden pauses, unbounded free-form intervention state

**Cheap Worker**:
A low-cost development or execution worker used for bounded, reviewable tasks such as batch documentation edits, reference sweeps, test drafts, and low-risk patch drafts. Cheap workers do not make final architecture, release, promote, rollback, or secret-handling decisions.
_Avoid_: delegating ownership or final judgment to the cheapest model

**OpenAI-Compatible Provider**:
A worker provider configured with `base_url`, `model`, and `api_key_env` for chat-completions style APIs. ARIS stores the environment variable name, not the API key value.
_Avoid_: writing API keys into config, logs, task files, or recovered artifacts

**DeepSeek V4 Flash Worker**:
A named Cheap Worker provider using `transport=openai_compatible`, `model=deepseek-v4-flash`, `base_url=https://api.deepseek.com/v1`, and `api_key_env=DEEPSEEK_API_KEY`.
_Avoid_: making DeepSeek the role definition instead of one runtime provider

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
