# Labline Framework Governance

Language for Labline framework versioning, release, and branch governance.

## Language

**Version Management**:
The release governance for Labline framework versions: release tags, changelog entries, and project-level framework pins. Branches support this process, but branch naming alone is not version management.
_Avoid_: using "version management" to mean only Git branch cleanup.

**Feature Branch**:
A short-lived branch for adding a new capability or changing behavior before it is ready for `dev` or `main`. A feature branch may include code, docs, tests, templates, or skill changes; it differs from a fix branch because the goal is new capability rather than restoring broken behavior.
_Avoid_: experiment branch, random dev branch

**Fix Branch**:
A short-lived branch for correcting an existing broken behavior, documentation error, deployment issue, or compatibility regression.
_Avoid_: hotfix unless the change must go directly to a released stable line.

**Stable Line**:
The `main` branch, containing released or release-ready Labline framework state.
_Avoid_: orangmood edition branch, production branch

**Development Line**:
The `dev` branch, containing integrated but not-yet-released Labline framework changes.
_Avoid_: scratch branch, personal branch

**Semantic Version**:
A framework release tag using `vMAJOR.MINOR.PATCH`. Before Labline reaches `v1.0.0`, minor versions carry user-visible capability changes and patch versions carry fixes that do not change normal usage.
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

**User Skill**:
A skill intended for research project users and project agents. User Skills may be installed into projects, included in the user-facing skill catalog, and promoted to the Stable Line when release gates pass.
_Avoid_: putting framework-maintenance helpers in the user skill graph

**Developer Skill**:
A maintainer-facing skill used to develop, review, test, generate, or release Labline itself. Developer Skills use a `dev-` name prefix, may live in the Development Line, are not installed into research projects, and are not promoted to the Stable Line as user capabilities.
_Avoid_: treating every dev checkout skill as a future stable skill; reusing a User Skill name for a Developer Skill

**Release Gate**:
The checklist that must pass before tagging a framework release. Patch releases use a lightweight gate focused on the changed area; minor releases use a stricter gate covering changelog, development log, generated catalogs/DAGs, installer behavior, Codex mirror compatibility, and at least one install or dev-to-stable validation.
_Avoid_: tagging first and checking later

**Promote Candidate Type**:
The classification that determines whether a dev checkout asset may move toward the Stable Line. Allowed candidate types are user-facing skills, tools, templates, docs, deploy assets, examples, compatibility assets, MCP servers, tests, and static assets; Developer Skills, Developer Material, dev runtime state, and private config are not promote candidates.
_Avoid_: promoting by path alone without checking user/developer scope

**Release Tag Automation**:
The guarded scripts that check and create framework release tags. Tag automation defaults to dry-run, creates a local tag only with `--apply`, and pushes the tag only with the additional `--push-tag` flag.
_Avoid_: scripts that create or push tags by default

**Version Bump**:
An explicit request to compute the next semantic version from the latest formal release tag, such as `--bump patch` or `--bump minor`. Maintainers may also provide an explicit `vMAJOR.MINOR.PATCH` when needed, but the release script must validate that it is newer than the latest formal release.
_Avoid_: implicit version inference from arbitrary commit messages

**Initial Stable Release**:
The first formal Labline framework release from the current `main` line, tagged `v0.1.0`. It establishes the baseline that research projects can pin before later patch and minor releases.
_Avoid_: treating pre-`v0.1.0` branch names as framework versions

**In-Place Project Initialization**:
Preparing the current directory as an Labline research project by passing `.` as the project path to the project initialization command. This is the beginner-facing path when the user has already created an empty or existing project folder.
_Avoid_: assuming an empty folder already has Labline commands installed

**New Project Creation**:
Creating or selecting an Labline research project directory by passing a non-`.` path to the project initialization command, then preparing that directory as an Labline research project.
_Avoid_: using "init project" ambiguously for both directory creation and current-directory setup

**Labline CLI**:
The beginner-facing command entrypoint for installing, initializing, updating, and inspecting Labline from a normal shell. It separates project-scoped commands under `lane project ...` from framework-scoped commands under `lane framework ...`.
_Avoid_: exposing script names as the primary beginner workflow

**Runnable Project Baseline**:
The minimum state in which a directory is recognizably an Labline research project and can be opened by supported agent clients without additional manual scaffolding. It includes project metadata, agent instructions, standard project folders, local framework installation records, and an initial version-control baseline.
_Avoid_: treating skill symlink installation alone as a complete project initialization

**Experiment Transparency Ledger**:
A project-level evidence trail that records experiment blocks, runs, data splits, metric definitions, implementation deviations, result artifacts, and human checkpoint decisions as experiments progress. It is the canonical transparency surface for later audit and claim evaluation.
_Avoid_: treating post-hoc audit reports as the only transparency mechanism

**Fixed Checkpoint**:
A predefined human decision point in a workflow, such as before launching experiments, after an experiment block finishes, or when a deviation or anomaly is detected. Fixed checkpoints are the first-stage human-in-the-loop mechanism before introducing a general workflow runtime.
_Avoid_: arbitrary runtime interruption as a first implementation requirement

**Workflow Runtime**:
An optional execution backend for stateful, resumable, interruptible Labline workflows. It may consume project artifacts and ledgers, but it must not replace the static skill protocol or make ordinary Labline project initialization depend on a runtime engine.
_Avoid_: making LangGraph or another runtime a core project format requirement

**Project Detach**:
Removing Labline integration from an existing project while leaving project-owned content intact. It removes framework-managed links, manifests, and managed metadata, but it does not delete the research project itself.
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

**Agent Status Contract**:
The minimum observability evidence that every Leader-dispatched child role must leave for runtime observation, including current status, expected update or durable handle where applicable, terminal verdict, and required artifact pointers. The base contract is role-agnostic; individual roles add role-specific artifact expectations without changing the shared observability rules. The runtime schema and validator are the source of truth for this contract; role prompts and skills are projections that help agents comply.
_Avoid_: skill text as final authority, transcript-only completion, role-specific status conventions without a shared base contract

**Mandatory Runtime Contract Injection**:
The dispatch rule that the Leader supplies the Agent Status Contract to every child-role task as part of the task context, instead of relying on the child role to discover or opt into a skill. Skill DAG entries may expose the contract, but dispatch-time injection and runtime validation preserve the contract.
_Avoid_: optional status skill, agent-selected observability protocol, relying on memory from a previous conversation

**Agent Observability Gate**:
The lifecycle gate that checks the Agent Status Contract before dispatch, after child-role boot, and before accepting a terminal outcome. It prevents an unobservable child role from being mistaken for a successful task, failed role verdict, or clean phase-boundary continuation.
_Avoid_: waiting indefinitely for missing status, accepting chat text as completion, converting unobservable child roles into phase readiness

**Leader-Gated Agent Retry**:
The recovery rule for a Delegated Agent Observability Failure: the runtime may wake or notify the Leader, but it must not silently retry the child role or overwrite the failed attempt. Any fresh retry is a new Leader decision and a new Runtime Task or event.
_Avoid_: automatic child-agent respawn, overwriting failed attempts, hidden duplicate reviewer or deployer runs

**Agent Retry Identity**:
The audit identity rule that a fresh retry of a child-role task receives a new Runtime Task identity while linking back to the failed or superseded attempt. The latest successful retry may satisfy downstream gates, but earlier failed or unobservable attempts remain part of the project runtime record.
_Avoid_: reusing failed task ids, erasing unobservable attempts, ambiguous reviewer report versions

**Delegated Agent Observability Failure Rate**:
The current runtime metric for how often Leader-dispatched child roles are unobservable: Delegated Agent Observability Failure count divided by the current delegated-agent task count in the runtime summary. It measures orchestration visibility health, not scientific failure, review quality, or experiment success.
_Avoid_: overall task failure rate, reviewer fail rate, experiment failure rate

**Long-Running Job Handle**:
A durable pointer to a long-running task that can be checked independently of the agent that launched it, such as a tmux or screen session name, queue state file, watchdog task name, log path, or result directory. The Leader treats the job handle as the source of truth for task liveness when an agent status file stops updating.
_Avoid_: foreground SSH command, agent transcript as progress source

**Runtime Task**:
The unified lifecycle object for Labline work that actually executes, whether it is short, interactive, delegated to an agent, or backed by a detached job. Runtime Tasks share events, status projection, observation, handoff, and terminal verdict semantics; pure status queries and read-only observations are not Runtime Tasks.
_Avoid_: separate ordinary-task and long-task lifecycles, treating `/status` as a task, hiding execution outside task events

**Runtime Task Capability Profile**:
The capability description attached to a Runtime Task that states how it runs and how much supervision it needs, such as inline execution, agent turn, detached job, resumability, supervisor ownership, observation, and heartbeat behavior. It replaces the ordinary-task versus long-task split as an implementation decision.
_Avoid_: task type explosion, forcing every short task through heavy supervision, implying every Runtime Task is resumable

**Supervised Runtime Task**:
A Runtime Task whose capability profile requires durable local supervision, usually because it is resumable, backed by a detached process or remote job, expected to outlive a single interactive turn, or needs escalation-gated heartbeat. It is the new canonical form of the older "long job" concept.
_Avoid_: separate long-task lifecycle, every Runtime Task as supervised, chat-owned background work

**Durable Task Supervisor**:
The local owner of a Runtime Task when its capability profile requires durable supervision: lifecycle authority, liveness, recovery metadata, and final artifact pointers. It remains authoritative even when the Remote Session Inbox, chat transport, or Remote Status Projection disconnects or fails to update.
_Avoid_: lark-channel-bridge as workflow runtime, chat card as process owner, treating all Runtime Tasks as heavy supervised jobs

**Local Job Service**:
A lightweight, local service that implements Durable Task Supervisor behavior for the current user and bridge profile. It manages supervised job queueing, child execution, lifecycle state, logs, verdicts, and handoff records without using a tmux session as the default execution container.
_Avoid_: daemon-lite, per-job tmux session as the normal backend, full multi-user scheduler

**Bridge-Managed Job Service**:
A Local Job Service whose availability is checked, started, and re-discovered by the Feishu bridge for the active bridge profile. Users should not need to start a separate service manually before launching remote Supervised Runtime Tasks.
_Avoid_: manual job-service prerequisite, hidden setup step for mobile entry, unmanaged background process with no bridge health check

**Detached Profile Job Service**:
A Bridge-Managed Job Service that is scoped to one bridge profile and continues running jobs independently of the bridge process that launched or discovered it. Bridge exit, restart, or session turnover must not by itself stop active supervised jobs.
_Avoid_: bridge child process lifecycle, killing jobs when the chat turn ends, one global job service shared across unrelated profiles

**Stale Supervised Runtime Task**:
A Supervised Runtime Task whose durable record remains available, but whose previous execution process can no longer be trusted after a host-level interruption such as reboot. It preserves handoff and logs for explicit continuation rather than automatically resuming execution. "Stale Long Job" is the legacy name.
_Avoid_: silent auto-resume after host reboot, losing job records on restart, treating stale as failed without inspection

**Expected Update Time**:
The next time an agent or its associated long-running job is expected to provide a meaningful new signal. It is a pacing hint for Leader observation, not a deadline or failure condition by itself.
_Avoid_: timeout, SLA, polling loop

**Read-Only Status Check**:
A non-mutating check that the Leader may perform when an Expected Update Time arrives, such as reading status files, queue state, watchdog summaries, logs, or monitor outputs. It must not restart jobs, change configuration, deploy code, or mutate project artifacts.
_Avoid_: recovery action, automatic intervention

**Phase-Boundary Continuation Wakeup**:
A Leader wakeup requested when a declared workflow stage has completed normally and the next useful action is Leader orchestration, not failure recovery or human approval. It carries completed-stage evidence and asks the Leader to choose the next role, gate, or checkpoint without assuming that the next task should run automatically.
_Avoid_: automatic continuation, treating every completed task as a continuation trigger, reusing blocked/stale/anomaly wakeups for clean stage completion

**Phase-Boundary Runtime Task**:
A Runtime Task that represents a declared workflow boundary rather than an executor-owned unit of work. It names the prerequisite tasks and required artifacts that must be terminal and present before a Phase-Boundary Continuation Wakeup is allowed.
_Avoid_: encoding phase boundaries only in pipeline-stage strings, making child agent status own whole-stage readiness, inferring phase completion from any completed task

**Ready-to-Continue Runtime Task**:
A Runtime Task state for a declared workflow boundary whose prerequisites and required artifacts are satisfied, so the Leader can be woken to orchestrate the next step. It is not a human approval request and must not imply that the next executor action should start without Leader judgment.
_Avoid_: overloading `need_decision`, treating readiness as approval, auto-starting the next experiment from readiness alone

**Phase-Boundary Readiness Authority**:
The ownership rule for phase-boundary readiness: the Leader declares the boundary and its prerequisites, the runtime observer verifies those prerequisites from task verdicts and artifacts, and child agents own only their own task verdicts. A child agent completion is evidence for a boundary, not authority over the boundary.
_Avoid_: child agent declares whole-stage readiness, transcript-only phase completion, shared mutable pipeline readiness

**Phase-Boundary Readiness Evidence**:
The explicit, machine-checkable evidence required before a Phase-Boundary Runtime Task may become ready to continue. It includes prerequisite task verdicts, required project artifacts, required gate or reviewer verdicts, and the next Leader question to answer after wakeup. Delegated Agent Observability Failure is not a gate verdict and cannot satisfy readiness evidence.
_Avoid_: inferring readiness from chat text, using recent activity as proof, hiding required artifacts in a prompt only

**Leader Orchestration Authority**:
The limited authority granted by a Ready-to-Continue Runtime Task wakeup. The Leader may inspect evidence, update its own orchestration state, choose the next role or gate, and decide whether a human decision is needed; it may not treat readiness as permission to launch high-cost, remote, deployment, or training work.
_Avoid_: readiness as executor authorization, automatic experiment launch, skipping policy checkpoints after a clean phase boundary

**One-Shot Phase-Boundary Wakeup**:
The lifecycle rule that a Ready-to-Continue Runtime Task is consumed when the Leader wakes and records the next orchestration outcome. The boundary task should then become terminal, while any resulting human decision or follow-up work is represented by a new Runtime Task.
_Avoid_: keeping consumed readiness active, repeated wakeups for the same boundary, mutating a phase-boundary trigger into the next executor task

**Phase-Boundary-Ready Wakeup**:
The auto-wakeup category for a Ready-to-Continue Runtime Task. It means a normal workflow boundary is ready for Leader orchestration and is distinct from stale recovery, blockers, anomalies, terminal-result notifications, and human-decision requests.
_Avoid_: presenting clean continuation as an alert, reusing `need_decision` for Leader-only orchestration, mixing phase continuation with failure recovery

**Reviewer Role**:
The independent review role in Labline that audits plans, code, results, claims, citations, or paper artifacts from original inputs. The role may be implemented through an MCP-backed model call, a spawned agent, or a separate CLI session depending on platform, but its independence contract is the same.
_Avoid_: equating Reviewer with Codex MCP only, executor self-review

**Delegated Agent Observability Failure**:
A failure mode where a Leader-dispatched Coder, Reviewer, Planner, or other child role does not leave enough Agent Status File, Long-Running Job Handle, expected-update, terminal verdict, or required artifact evidence for the Leader to observe the task outcome. It is classified from missing observability evidence before any role verdict is trusted; the Leader explains the failure and chooses recovery, but must not treat it as a substantive review, coding, or planning conclusion.
_Avoid_: Reviewer failed, Coder failed, treating missing status or missing verdict artifacts as a substantive task conclusion

**Project Runtime State**:
Local, non-versioned state written inside a research project while Labline workflows run, such as agent status snapshots and transient coordination metadata. The Labline framework repository provides tools and protocols for this state but must not contain real project runtime state.
_Avoid_: framework-owned runtime status, committed agent snapshots

**Project Runtime State Root**:
The project-local `.labline/runtime/` root for Labline-managed runtime control state, such as agents, jobs, queues, watchdog observations, pipeline state mirrors, tasks, events, leases, heartbeats, escalations, wakeups, foreground transports, and summaries. It is not a catch-all for project scaffolding, client entry files, install manifests, Git ignore rules, research artifacts, trace archives, or external bridge private state.
_Avoid_: moving Codex/Claude project entry files into runtime, treating installation metadata as runtime control state, sweeping all generated files into one directory

**Runtime Pipeline State**:
Machine-readable workflow phase state stored under `.labline/runtime/pipelines/`. It replaces the older root-level `PIPELINE_STATE.json` convention for new projects; human-readable stage status remains in shared project surfaces such as `CLAUDE.md` Pipeline Status, trackers, or summaries.
_Avoid_: root-level `PIPELINE_STATE.json` as a new-project protocol, hiding human stage status in machine JSON only

**Runtime Status Aggregator**:
A Labline runtime tool that reads component-owned state under `.labline/runtime/` and writes derived task and summary views such as `.labline/runtime/tasks/*.json` and `.labline/runtime/summaries/current.*`. It does not own the source state written by agents, queues, watchdogs, or pipeline controllers.
_Avoid_: letting multiple components overwrite a shared task file, treating summaries as source of truth

**Project Handoff Surface**:
The project-owned files and snapshots that let a fresh session or role understand current work, decisions, open questions, status, and artifact pointers without relying on hidden model context. Runtime Task records may reference or mirror this surface, but must not replace project-owned evidence.
_Avoid_: hidden conversation memory, duplicating full transcripts as handoff, treating chat cards as project evidence

**Human-Facing Project Surface**:
Project files intended primarily for human reading, review, teaching, or reporting. They should be concise, navigable, and stable enough for a person to inspect without learning runtime internals.
_Avoid_: making humans read raw status JSON, burying decisions only in hidden runtime state

**Human-Readable Project Structure**:
The stable, navigable layout of human-facing and shared project files that lets a person understand a Labline project without inspecting runtime internals. Runtime consolidation must preserve this structure and may add references or summaries, but it must not relocate established human-facing artifacts into maintenance directories.
_Avoid_: hiding plans, logs, reports, or configuration under `.labline/runtime`; optimizing machine state at the cost of human project readability

**Agent-Facing Project Surface**:
Project files intended primarily to restore or guide agent work, such as focused context, role instructions, recovery prompts, and machine-readable state summaries. They should be compact and structured for reliable loading by agents.
_Avoid_: forcing agents to infer state from long human narratives, treating every project artifact as default context

**Shared Project Surface**:
Project files that both humans and agents are expected to read or maintain directly, especially initialization/configuration files, plans, trackers, ledgers, and concise summaries that coordinate work across sessions.
_Avoid_: duplicating separate human and agent versions that can drift without a clear owner

**Maintenance Project Surface**:
Project-local files used by Labline tools, installers, runtimes, traces, caches, or compatibility adapters. They may be essential for operation, but they are not normal human or agent reading material unless diagnosing a problem.
_Avoid_: treating process receipts as research artifacts, loading maintenance logs as default agent context

**Project Registry**:
A non-versioned registry in a User Workspace that records Labline project paths initialized for that user. Framework updates use it to keep registered projects in sync with the user's framework copy, and project detach removes projects from it.
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

**Remote Status Projection**:
A derived, remote-visible view of a live Codex Session's liveness, progress, blockers, and final notifications. It is not the source of execution truth; local Project Runtime State, Agent Status Snapshots, and Long-Running Job Handles remain authoritative.
_Avoid_: authoritative chat card, execution state stored in Feishu, using remote display success as proof of run completion

**Conversation-Anchored Segmented Projection**:
A Remote Status Projection for observed Runtime Tasks that appears inside the initiating conversation as a small sequence of meaningful status segments. The current segment absorbs ordinary progress updates; new segments are reserved for important boundaries, blockers, input requests, anomalies, and terminal results.
_Avoid_: per-job dashboard card, one-card-per-heartbeat, status feed detached from the conversation

**Runtime Task Heartbeat**:
A liveness update emitted while an observed Runtime Task is still running, especially when a supervised task, active agent, or child process is waiting without producing user-visible output. It patches the active Conversation-Anchored Segmented Projection rather than creating a new status segment. "Long Job Heartbeat" is the legacy name for the supervised subset.
_Avoid_: requiring Leader output for liveness, new card per heartbeat, treating heartbeat as evidence of task progress

**Escalation-Gated Heartbeat**:
A periodic external status probe for Runtime Tasks whose capability profile enables heartbeat. It updates runtime state without involving the Leader by default, and wakes or resumes the Leader only when the probe produces an escalation, a blocker, a due decision, a terminal result, or an explicit user status request.
_Avoid_: scheduled Leader resume, LLM polling loop, treating every heartbeat as decision work

**Project Heartbeat Protocol**:
The framework-defined, project-executed file protocol for running Escalation-Gated Heartbeats inside a Labline project. It is independent of Feishu or any single chat transport; schedulers, bridges, shells, or future orchestrators may trigger it, but the protocol state belongs to the project runtime surface.
_Avoid_: Feishu-owned heartbeat, chat-transport lifecycle, scheduler-specific project format

**Runtime Interaction Entry**:
A user-facing way to inspect or request changes to Project Runtime State, such as Feishu/Lark ChatOps, local Codex CLI, a shell command, a dashboard, or a future IDE panel. Interaction entries translate user intent into runtime status reads, approvals, escalations, or lease-protected control actions; they do not own workflow state.
_Avoid_: Feishu as runtime owner, dashboard-owned tasks, treating a chat session as the project control plane

**Runtime Observation Entry**:
A read-only interaction path that lets a user follow progress from another endpoint without sending input to the active Leader session. It reads Project Runtime State, Remote Status Projection, events, summaries, and artifact pointers, but it does not create a Runtime Control Intent unless the user explicitly asks for a control action.
_Avoid_: treating `/status` as Leader input, injecting status questions into a busy TUI, acquiring control leases for read-only progress checks

**Remote Interaction Routing**:
The classification step that decides whether a remote message is read-only observation, a BTW Side Channel question, a Normal Project Interaction, or a Runtime Control Intent. It protects active tasks from accidental interruption while still allowing ordinary project work and explicit control actions. Ambiguous remote messages default to non-mutating observation or BTW until the user explicitly confirms a project-changing action.
_Avoid_: sending every remote message into the active Leader session, treating every question as project truth, hiding control actions inside side-channel answers

**Remote Observation Subscription**:
A bridge-owned mapping from a remote conversation to one project or task's read-only runtime projection. It is scoped by bridge profile or instance, workspace/project, conversation, and optional task id. It lets TUI-originated tasks push progress to Feishu/Lark by watching Project Runtime State and delivery state, without storing chat ownership in the project or sending input to the active Leader session.
_Avoid_: project-owned chat IDs, TUI transcript mirroring, global project-wide broadcast, requiring Leader to send progress messages

**Runtime Control Intent**:
A structured request from an interaction entry to change runtime state or control a live session, such as approve, reject, pause heartbeat, force check, stop task, resume task, or launch workflow. It must be recorded as a runtime event and must acquire the relevant lease before mutating state or resuming a session.
_Avoid_: free-form remote command execution, hidden direct TUI injection, unrecorded control action

**Multi-Endpoint Control**:
The rule that local CLI, Feishu/Lark, dashboard, scheduler, and future orchestrators may all observe the same project, but mutating operations converge through Runtime Control Intents and leases. Read-only status is concurrent; control is serialized by lease scope and event records.
_Avoid_: last-writer-wins chat control, parallel Leader resumes, endpoint-specific truth

**Heartbeat Monitor Worker**:
An optional short-lived worker used by an Escalation-Gated Heartbeat to summarize logs, queue state, metrics, or job handles before a Leader decision. It may prepare evidence and a recommended next action, but it does not own the decision or replace the original Leader session.
_Avoid_: autonomous monitor leader, hidden decision maker, replacing Leader context with a fresh worker context

**Runtime Task Surface Pointers**:
A short, high-signal set of project paths or artifact references shown in a Runtime Task's remote projection so the user can inspect the relevant Project Handoff Surface. These pointers identify handoff files, trackers, result directories, or logs without inlining their contents into the card. "Long Job Surface Pointers" is the legacy name for supervised tasks.
_Avoid_: full logs in chat cards, long path dumps, hiding project-owned evidence behind chat-only summaries

**Runtime Task Final Reply**:
A new user-visible message sent in the originating conversation when an observed Runtime Task reaches a terminal or attention-required state such as `blocked`, `need_decision`, or `anomaly`. It accompanies the status-card patch so completion, failure, stop results, or blockers are visible as a fresh chat notification rather than only as an edited card. "Long Job Final Reply" is the legacy name for supervised tasks.
_Avoid_: terminal or blocked state only as card patch, silent completion, requiring users to inspect old status cards for final results

**Projection Delivery State**:
The Remote Message Archive record of whether a Remote Status Projection update, terminal card patch, or Runtime Task Final Reply has been delivered, is pending, or failed and needs retry. It is keyed per remote observation subscription or projection target, and is separate from the Runtime Task lifecycle verdict.
_Avoid_: marking a completed job incomplete because Feishu send failed, losing retry intent, using delivery success as proof of task completion, deduplicating across unrelated bridge profiles

**Runtime Task Stop Request**:
An explicit stop intent interpreted by the Leader for a Runtime Task. `/stop` may pause the current Leader turn without directly killing background work; a user-facing request such as "stop the task" is handled by the Leader as the task stop decision.
_Avoid_: direct process kill from remote projection, card-only cancellation path, bypassing the Leader for job stop decisions

**Leader-Mediated Runtime Task Control**:
The rule that user queries, status checks, requirement changes, continuation requests, and stop intents enter through the Leader conversation or a lease-protected Runtime Control Intent. The Leader reads Runtime Task state and decides whether to update, continue, stop, or leave background work running; supervised tasks do not consume user messages directly.
_Avoid_: background job chat endpoint, user-to-job direct routing, bypassing Leader for ordinary control flow

**BTW Side Channel**:
A read-only remote side question that can be answered while the Leader conversation or a Runtime Task continues running. During an active task, ordinary remote questions default to this path unless they imply a control action. It may use recent transcript, Remote Message Archive facts, and Project Handoff Surface pointers as context, but it must not modify files, advance tasks, or inject text into the Leader conversation.
_Avoid_: side-channel task execution, hidden Leader interruption, merging BTW answers into job state as decisions

**BTW Thread**:
A short-lived, bridge-owned conversation thread for consecutive BTW Side Channel questions about the same project or active Runtime Task. It may carry recent read-only question context, task references, archive refs, and project pointers, but it is not a Runtime Task, Normal Project Interaction, Leader conversation, or control session.
_Avoid_: task execution thread, hidden project memory, using BTW continuity to change project state

**Normal Project Interaction**:
A remote message intended to become ordinary project work or Leader conversation input, such as starting a new task, changing requirements, making a decision, or asking the Leader to perform analysis that may update project artifacts. It is not a BTW Side Channel question and must respect leases and Runtime Control Intent rules when work is already active.
_Avoid_: treating project-changing instructions as read-only questions, bypassing control leases, implicit task creation from ambiguous chat

**Remote File Broker**:
A bridge-mediated file transfer surface that lets Feishu users request, receive, or upload files through controlled paths under the active workspace or approved roots. It does not provide direct remote filesystem editing; file modifications remain Leader-mediated project work.
_Avoid_: Feishu file manager, remote shell filesystem access, direct chat command for arbitrary file writes

**Bridge-Compatible Card Semantics**:
The constraint that Runtime Task status projections preserve the existing Feishu bridge card behavior, supported interactions, and fallback expectations rather than inventing a separate card surface for supervised jobs.
_Avoid_: special long-job card protocol, degraded card feature subset, divergent button semantics

**Remote Projection Boundary**:
The responsibility boundary where a Durable Task Supervisor owns Supervised Runtime Task lifecycle state, while the Feishu bridge owns remote rendering, card patching, callbacks, and user-visible fallback behavior.
_Avoid_: supervisor calling chat APIs directly, duplicating bridge card logic inside jobs, treating card delivery as task execution

**Remote Message Archive**:
The bridge-owned archive for Feishu/Lark conversation records, remote session traces, Runtime Task identity, projection metadata, and handoff state. It may reference many project workspaces; projects remain responsible for code, experiment outputs, and durable research artifacts.
_Avoid_: project-local chat archive as the authority, storing job identity only inside a workspace, treating Feishu cloud history as the local archive

**Project Runtime Task Mirror**:
A project-local, read-only discovery surface for a Supervised Runtime Task whose authoritative remote projection record lives in the Remote Message Archive. It helps a local session find the task, handoff snapshot, and artifact pointers without creating a second writable source of lifecycle truth. "Project Long Job Mirror" is the legacy name.
_Avoid_: project-owned remote job state, two-way status sync, editing mirrored job files to control the task

**Single-Workspace Runtime Task**:
A Runtime Task whose execution, recovery context, permissions, logs, and artifact pointers are anchored to one workspace or current working directory. Multi-workspace work is represented as orchestration across multiple tasks, not as one task with several mutable workspace roots. "Single-Workspace Long Job" is the legacy name for supervised tasks.
_Avoid_: cross-workspace job state, implicit cwd switching inside one job, one remote job owning multiple projects

**Explicit Runtime Task Entry**:
A deliberate user request, Leader dispatch, or workflow action that creates a Runtime Task. Ordinary status queries, follow-up questions, and read-only observations are not Runtime Task entries unless they explicitly start or change execution.
_Avoid_: treating every remote message as execution, implicit detached runs for status checks, accidental new tasks from progress questions

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

**Job Handoff Snapshot**:
A compact, agent-readable summary for resuming or inspecting a Durable Task Supervisor job from a new local or remote session. It includes the current objective, status, decisions, open questions, next action, artifact pointers, and log paths; it does not inline the full transcript or raw logs.
_Avoid_: full log replay, chat transcript as recovery context, attaching a new agent to a hidden live process

**Runtime Task Handoff Sync**:
The process of keeping a Runtime Task handoff record aligned with relevant Project Handoff Surface entries and Remote Message Archive facts. It links or mirrors auditable facts and artifact pointers without claiming that hidden model context moved between sessions. "Long Job Handoff Sync" is the legacy name for supervised tasks.
_Avoid_: two writable handoff authorities, copying entire logs into every job record, context transfer claims

**Structured Task Verdict**:
The machine-readable status a Runtime Task writes at the end of each agent turn, including whether the task is done, blocked, or ready to continue. Agent self-assessment may inform the verdict, but the Durable Task Supervisor compares supervised-task verdicts against explicit done criteria before ending the job.
_Avoid_: accepting free-text "done" as completion, ending a supervised task at every milestone, relying on chat wording as lifecycle state

**Compact Continuation Context**:
The bounded context packet supplied to each automatic continuation turn of a Supervised Runtime Task. It contains the original task goal and done criteria, the latest Job Handoff Snapshot, the previous Structured Task Verdict, and selected log excerpts or artifact pointers rather than full transcripts.
_Avoid_: replaying complete chat history, stuffing full logs into every continuation, relying on hidden model context for progress

**User Workspace**:
The administrator-assigned research workspace for one Labline user in a managed deployment. A User Workspace owns that user's framework copy and project area while sharing group-level research assets.
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
The top-level glossary and language reference for Labline framework governance. `CONTEXT.md` is the Semantic Root: it does not replace implementation docs, but it defines the shared meaning that lower-level plans, ADRs, skills, and archives should stay consistent with.
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

**Labline Role**:
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

**Developer Skill Install Surface**:
The development-only symlink and manifest surface that installs `dev-*` Developer Skills into an Labline dev checkout for framework maintenance. It is controlled by the `lane dev skills ...` namespace and must not install skills into research projects.
_Avoid_: reusing user project installers for developer-only skills; coupling developer skill updates to user-surface generation

**Developer User Surface**:
The development checkout surface that prepares user-facing assets for eventual stable release, such as User Skill mirrors, generated catalogs, DAGs, templates, and user docs. It is controlled by the `lane dev user-surface ...` namespace and must not include Developer Skills.
_Avoid_: mixing dev-only tools into generated user catalogs or project install manifests; mutating developer skill symlinks as a side effect of user-surface updates

**Developer Skill DAG**:
The development-only dependency graph for `dev-*` Developer Skills. It is separate from the user Skill DAG and must not make Developer Skills appear in user catalogs, project install manifests, or stable user role graphs.
_Avoid_: merging maintainer-only skill topology into the user Logical Skill Graph

**Developer Skill Fork**:
A Developer Skill derived from a User Skill so it can evolve for framework-maintenance work without changing the user-facing skill. Developer Skill Forks use `dev-` names and should preserve lineage to the source User Skill without sharing the same role in the user graph.
_Avoid_: editing User Skills for maintainer-only needs; silently duplicating skills without lineage

**Developer Runtime Surface**:
The development-only provider, model, role-binding, prompt, and run surface for maintainer helper agents. It is controlled by `lane dev runtime ...` with `lane dev rt ...` as the short alias; legacy `lane dev worker ...` is not part of the canonical CLI.
_Avoid_: creating one-off dev CLI namespaces for individual helper roles

**Dev Leader**:
The development-only orchestration role for maintaining Labline itself. Dev Leader decomposes framework work, delegates bounded tasks to development runtime roles such as Dev Real-Machine Tester and Cheap Worker, reads their evidence, and reports decisions back to the maintainer; it is not the user-facing project Leader.
_Avoid_: using the user Leader role for framework maintenance; letting Dev Leader replace independent review; treating delegated development evidence as automatic release approval

**Dev Workflow**:
A development-only, evidence-backed maintenance run coordinated by Dev Leader. It records framework-maintenance task files, delegated development role assignments, Expected Update Times, progress snapshots, question records, and evidence artifacts under Developer Material; it is not a user research workflow and not the general Workflow Runtime.
_Avoid_: mixing framework-maintenance workflow state into research projects; treating a Dev Workflow as release approval; allowing delegated roles to go silent past their Expected Update Time; losing ambiguities or maintainer questions in chat-only context

**Dev Real-Machine Tester**:
A development-only runtime role, normally delegated by Dev Leader, that validates Labline changes on an actual managed server or container by following the published deployment and operations docs, recording command evidence, logs, versions, and pass/fail results. It is not a User Skill, not a research project Deployer, and not part of the user Labline Role graph.
_Avoid_: treating real-machine validation as release approval; testing from undocumented private steps; mutating user projects or credentials during validation

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
A low-cost Developer Skill or development runtime helper used for bounded, reviewable framework-maintenance tasks such as batch documentation edits, reference sweeps, test drafts, and low-risk patch drafts. Cheap Worker is not a User Skill and is not part of the research project role graph.
_Avoid_: delegating ownership or final judgment to the cheapest model; exposing Cheap Worker as a project user role

**OpenAI-Compatible Provider**:
A worker provider configured with `base_url`, `model`, and `api_key_env` for chat-completions style APIs. Labline stores the environment variable name, not the API key value.
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

Developer: "The Docker docs changed; can I call the research Deployer to validate them on the 5090 server?"

Maintainer: "Use the Dev Real-Machine Tester. It follows the published docs on the real server, records evidence and logs, and reports findings; it does not approve the release or become a user project role."

Developer: "Who coordinates developer-side helpers as this process becomes more agentic?"

Maintainer: "The Dev Leader coordinates them. It can delegate to Dev Real-Machine Tester or Cheap Worker, but independent review and maintainer approval remain separate."

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
