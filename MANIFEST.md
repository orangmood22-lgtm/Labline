# Research Output Manifest

> Auto-maintained by ARIS skills. Tracks all generated artifacts across the research lifecycle.
> See [shared-references/output-manifest.md](skills/shared-references/output-manifest.md) for the protocol.

| Timestamp | Skill | File | Stage | Description |
|-----------|-------|------|-------|-------------|
| 2026-05-12 00:00 | /manual | MANIFEST.md | implementation | Initialized manifest for night implementation tracking |
| 2026-05-12 00:00 | /manual | discussions/NIGHT_PROGRESS_20260512.md | implementation | Night progress log for implementation + exploration |
| 2026-05-13 00:00 | /manual | skills/shared-references/integration-contract.md | implementation | Added shared experiment-chain vocabulary covering expectation, execution spec, data flow, delta assertion, and evidence mapping |
| 2026-05-13 00:00 | /manual | skills/shared-references/output-versioning.md | implementation | Added plan/run/audit/claim versioning guidance and timestamping expectations for load-bearing experiment-chain sidecars |
| 2026-05-13 00:00 | /manual | skills/shared-references/output-manifest.md | implementation | Added manifest traceability guidance so plan → run → audit → claim artifacts can be reconstructed from MANIFEST.md |
| 2026-05-13 00:00 | /manual | templates/EXPERIMENT_PLAN_TEMPLATE.md | implementation | Expanded experiment plan template with expectation declaration, execution spec, data flow, delta assertion, evidence mapping, and audit-ready checklist |
| 2026-05-13 00:00 | /manual | skills/experiment-plan/SKILL.md | implementation | Updated experiment-plan to require the shared experiment-chain contract sections and audit/claim traceability |
| 2026-05-13 00:00 | /manual | skills/experiment-bridge/SKILL.md | implementation | Updated experiment-bridge to parse the new contract, verify implementation conformance, enforce sanity delta checks, and record deviations |
| 2026-05-13 00:00 | /manual | skills/experiment-audit/SKILL.md | implementation | Expanded experiment-audit with split correctness, implementation conformance, delta assertion, and evidence-mapping traceability checks |
| 2026-05-13 00:00 | /manual | skills/result-to-claim/SKILL.md | implementation | Updated result-to-claim to consume plan contract sections, audit verdicts, and delta/evidence alignment before judging claims |
| 2026-05-13 00:00 | /manual | tools/semantic_scholar_fetch.py | implementation | Hardened transient API recovery with exponential backoff and retry-on-empty/invalid JSON for retryable responses |
| 2026-05-13 00:00 | /manual | tools/watchdog.py | implementation | Hardened watchdog persistence with atomic writes for tasks, per-task status, and summary artifacts |
| 2026-05-13 00:00 | /manual | tests/test_recovery_hardening.py | implementation | Added targeted regression tests for retry recovery on malformed API responses and watchdog atomic state writes |
| 2026-05-13 00:00 | /manual | tools/experiment_queue/queue_manager.py | implementation | Hardened queue manager state persistence with atomic writes for restart-safe scheduler state |
| 2026-05-13 00:00 | /manual | tests/test_queue_manager_state.py | implementation | Added targeted regression tests for queue manager atomic state writes and state initialization/load behavior |
| 2026-05-13 00:00 | /manual | tools/experiment_queue/build_manifest.py | implementation | Hardened queue manifest persistence with atomic writes for restart-safe manifest generation |
| 2026-05-13 00:00 | /manual | tests/test_build_manifest_state.py | implementation | Added targeted regression tests for manifest atomic writes and grid expansion persistence behavior |
| 2026-05-13 00:00 | /manual | skills/experiment-bridge/SKILL.md | implementation | Tightened experiment-bridge contract consumption to explicitly require Execution Spec conformance before implementation and deployment |
| 2026-05-13 00:00 | /manual | skills/shared-references/integration-contract.md | implementation | Extended shared experiment-chain vocabulary with implementation deviation receipts for plan-drift traceability |
| 2026-05-13 00:00 | /manual | skills/shared-references/output-versioning.md | implementation | Clarified versioning expectations for implementation deviation sidecars as load-bearing run artifacts |
| 2026-05-13 00:00 | /manual | skills/experiment-bridge/SKILL.md | implementation | Standardized IMPLEMENTATION_DEVIATIONS.json as the machine-readable plan-drift sidecar with claim and artifact impact fields |
| 2026-05-13 00:00 | /manual | skills/experiment-audit/SKILL.md | implementation | Tightened implementation conformance audit to validate IMPLEMENTATION_DEVIATIONS.json completeness and no-drift receipts |
| 2026-05-13 00:00 | /manual | tools/experiment_queue/queue_manager.py | implementation | Documented queue manager against the shared recovery state contract for resumability and backoff traceability |
| 2026-05-13 00:00 | /manual | tools/watchdog.py | implementation | Documented watchdog persistence artifacts as recovery receipts under the shared recovery state contract |
| 2026-05-13 00:00 | /manual | tests/test_queue_manager_state.py | implementation | Expanded queue manager regression coverage to assert resumability metadata initialization |
| 2026-05-13 00:00 | /manual | skills/shared-references/experiment-integrity.md | implementation | Clarified that declared evaluation types must stay aligned with plan expectations and implementation deviation receipts before audit/claim gating |
| 2026-05-13 00:00 | /manual | discussions/ARIS_NON_PROGRAMMER_READING_GUIDE_20260513.md | implementation | Wrote a non-programmer navigation guide explaining reading order, file roles, skip-first-pass areas, and key questions for understanding the experiment chain |
