#!/usr/bin/env python3
"""End-to-end drill: simulate the full ARIS experiment chain.

Walks through plan → bridge → audit → result-to-claim using the toy
CIFAR-10 scenario with two deliberately injected failures:

  1. Wrong split (train instead of test)  → audit check G, H fail
  2. Dead code path (attention bypassed)  → audit check D warn, I fail

No real GPU, no Codex MCP — pure local simulation.

Usage:
    python run_drill.py            # prints summary + writes audit & claim artifacts
    python -m pytest test_e2e_drill.py -v   # runs assertions
"""

import json
import os
import re
import sys
from pathlib import Path

DRILL_DIR = Path(__file__).resolve().parent
REFINE_LOGS = DRILL_DIR / "refine-logs"
RESULTS_DIR = DRILL_DIR / "results"
SRC_DIR = DRILL_DIR / "src"
AUDIT_DIR = DRILL_DIR / "audit"
CLAIM_DIR = DRILL_DIR / "claim"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_json(path: Path):
    # type: (...) -> Union[dict, list]
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


def read_text(path: Path) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------------------
# Phase 1: Parse Plan (extract key contract values)
# ---------------------------------------------------------------------------

def parse_plan(plan_path: Path) -> dict:
    """Extract structured contract info from EXPERIMENT_PLAN.md."""
    text = read_text(plan_path)

    plan = {}

    # Planned split — look in Expectation Declaration
    if "**test**" in text.lower() or "test split" in text.lower():
        plan["planned_split"] = "test"
    else:
        plan["planned_split"] = "unknown"

    # GT source
    if "dataset-provided" in text.lower() or "torchvision" in text.lower():
        plan["gt_source"] = "dataset"
    else:
        plan["gt_source"] = "unknown"

    # Delta assertion threshold
    plan["delta_threshold"] = 0.001  # "difference < 0.1%" per plan

    # Claims
    plan["claims"] = ["C1"]

    # Expected result files
    plan["expected_result_files"] = [
        "results/main_result.json",
        "results/ablation_result.json",
    ]

    # Evidence mapping: C1 → B1, B2
    plan["evidence_mapping"] = {
        "C1": {
            "blocks": ["B1", "B2"],
            "result_files": [
                "results/main_result.json",
                "results/ablation_result.json",
            ],
        }
    }

    return plan


# ---------------------------------------------------------------------------
# Phase 2: Simulate Bridge (artifacts already created; just load & verify)
# ---------------------------------------------------------------------------

def load_bridge_artifacts(drill_dir: Path) -> dict:
    """Load the bridge outputs: source code, results, deviations."""
    artifacts = {}

    # Source code text (for dead-code analysis)
    toy_src = read_text(drill_dir / "src" / "toy_classifier.py")
    eval_src = read_text(drill_dir / "src" / "eval_cifar10.py")
    artifacts["toy_classifier_src"] = toy_src
    artifacts["eval_src"] = eval_src

    # Result files
    artifacts["main_result"] = load_json(drill_dir / "results" / "main_result.json")
    artifacts["ablation_result"] = load_json(drill_dir / "results" / "ablation_result.json")

    # Deviations
    dev_path = drill_dir / "refine-logs" / "IMPLEMENTATION_DEVIATIONS.json"
    if dev_path.exists():
        artifacts["deviations"] = load_json(dev_path)
    else:
        artifacts["deviations"] = None

    return artifacts


# ---------------------------------------------------------------------------
# Phase 3: Audit Simulation (checks A–J)
# ---------------------------------------------------------------------------

def run_audit(plan: dict, artifacts: dict) -> dict:
    """Simulate experiment-audit checks A–J and produce audit report."""

    checks = {}

    # --- A. Ground Truth Provenance ---
    # Plan says GT from dataset; eval script uses mock but not model-derived GT
    checks["gt_provenance"] = {
        "status": "pass",
        "details": "Ground truth source is CIFAR-10 dataset labels (plan declares "
                   "dataset-provided labels, eval uses torchvision).",
    }

    # --- B. Score Normalization ---
    # No self-normalization in eval script
    checks["score_normalization"] = {
        "status": "pass",
        "details": "No self-referencing normalization detected. Raw accuracy reported.",
    }

    # --- C. Result File Existence ---
    result_files_exist = all(
        (DRILL_DIR / f).exists() for f in plan["expected_result_files"]
    )
    if result_files_exist:
        checks["result_existence"] = {
            "status": "pass",
            "details": "All expected result files exist: "
                       + ", ".join(plan["expected_result_files"]),
        }
    else:
        missing = [f for f in plan["expected_result_files"]
                   if not (DRILL_DIR / f).exists()]
        checks["result_existence"] = {
            "status": "fail",
            "details": f"Missing result files: {missing}",
        }

    # --- D. Dead Code Detection ---
    # Check if ChannelAttention.forward() is ever called in ToyClassifier.forward()
    toy_src = artifacts["toy_classifier_src"]
    attention_defined = "class ChannelAttention" in toy_src
    attention_called = "self.attention(" in toy_src and \
                       not re.search(r"#.*self\.attention\(", toy_src)

    # More precise: look for self.attention( NOT preceded by # on same line
    lines = toy_src.split("\n")
    attention_call_live = False
    for line in lines:
        stripped = line.strip()
        if "self.attention(" in stripped and not stripped.startswith("#"):
            attention_call_live = True
            break

    if attention_defined and not attention_call_live:
        checks["dead_code"] = {
            "status": "warn",
            "details": "ChannelAttention module is defined (class ChannelAttention) "
                       "but never called in ToyClassifier.forward(). "
                       "The attention module is a dead code path.",
        }
    else:
        checks["dead_code"] = {
            "status": "pass",
            "details": "All defined modules appear to be called.",
        }

    # --- E. Scope Assessment ---
    main_result = artifacts["main_result"]
    num_samples = main_result["results"]["ToyClassifier"].get("num_samples", 0)
    checks["scope"] = {
        "status": "pass",
        "details": f"Evaluated on {num_samples} samples. "
                   "Scope is adequate for a single-dataset claim.",
    }

    # --- F. Evaluation Type Classification ---
    checks["eval_type"] = "real_gt"

    # --- G. Split Correctness ---
    planned_split = plan["planned_split"]
    actual_split = main_result.get("split_used", "unknown")

    if actual_split != planned_split:
        checks["split_correctness"] = {
            "status": "fail",
            "details": f"SPLIT MISMATCH: Plan requires '{planned_split}' split, "
                       f"but evaluation ran on '{actual_split}' split. "
                       f"Result file shows split_used='{actual_split}', "
                       f"num_samples={num_samples} (train has 50000, test has 10000). "
                       "This is a data leakage risk — evaluation on training data "
                       "does not validate generalization.",
            "planned": planned_split,
            "actual": actual_split,
        }
    else:
        checks["split_correctness"] = {
            "status": "pass",
            "details": f"Evaluation correctly uses '{planned_split}' split.",
        }

    # --- H. Implementation Conformance ---
    deviations = artifacts.get("deviations")

    if deviations is None:
        checks["implementation_conformance"] = {
            "status": "warn",
            "details": "No IMPLEMENTATION_DEVIATIONS.json found. "
                       "Cannot verify implementation conformance.",
        }
    else:
        unresolved = [d for d in deviations if d.get("status") == "unresolved"]
        breaks_claim = [d for d in deviations
                        if d.get("claim_impact") == "breaks_claim_test"]

        if unresolved and breaks_claim:
            checks["implementation_conformance"] = {
                "status": "fail",
                "details": f"IMPLEMENTATION CONFORMANCE FAILURE: "
                           f"{len(unresolved)} unresolved deviation(s), "
                           f"{len(breaks_claim)} with claim_impact='breaks_claim_test'. "
                           "Deviations: " +
                           "; ".join(
                               f"[{d['deviation_type']}] planned='{d['planned_value']}' "
                               f"actual='{d['actual_value']}' "
                               f"impact={d['claim_impact']} status={d['status']}"
                               for d in unresolved
                           ),
                "unresolved_count": len(unresolved),
                "breaks_claim_count": len(breaks_claim),
            }
        elif unresolved:
            checks["implementation_conformance"] = {
                "status": "warn",
                "details": f"{len(unresolved)} unresolved deviation(s) "
                           "but none break the claim test.",
            }
        else:
            checks["implementation_conformance"] = {
                "status": "pass",
                "details": "All deviations are resolved/accepted. "
                           "Implementation conforms to plan.",
            }

    # --- I. Delta Assertion / Core Modification Effect ---
    delta = abs(main_result.get("delta", 0))
    threshold = plan["delta_threshold"]
    predictions_match = (
        main_result["results"]["ToyClassifier"].get("predictions_hash")
        == main_result["results"]["BaselineMLP"].get("predictions_hash")
    )

    if delta < threshold and predictions_match:
        checks["delta_assertion"] = {
            "status": "fail",
            "details": f"DELTA ASSERTION FAILED: ToyClassifier vs BaselineMLP "
                       f"delta={delta:.6f} (threshold={threshold}), "
                       f"predictions_hash identical "
                       f"('{main_result['results']['ToyClassifier'].get('predictions_hash')}'). "
                       "The claimed core modification (channel attention) shows NO "
                       "observable effect. Combined with dead-code detection (check D), "
                       "the attention module is likely bypassed.",
            "delta": delta,
            "threshold": threshold,
            "predictions_identical": predictions_match,
        }
    elif delta < threshold:
        checks["delta_assertion"] = {
            "status": "fail",
            "details": f"DELTA ASSERTION FAILED: delta={delta:.6f} below "
                       f"threshold={threshold}. Core modification shows no "
                       "meaningful effect.",
            "delta": delta,
            "threshold": threshold,
        }
    else:
        checks["delta_assertion"] = {
            "status": "pass",
            "details": f"Delta={delta:.4f} exceeds threshold={threshold}. "
                       "Core modification has observable effect.",
        }

    # --- J. Evidence Mapping Traceability ---
    evidence_ok = True
    evidence_details = []

    for claim_id, mapping in plan["evidence_mapping"].items():
        for rf in mapping["result_files"]:
            rf_path = DRILL_DIR / rf
            if not rf_path.exists():
                evidence_ok = False
                evidence_details.append(
                    f"{claim_id}: expected file '{rf}' missing"
                )
            else:
                # Check if result supports the claim
                result_data = load_json(rf_path)
                if not result_data.get("criterion_met", False):
                    evidence_details.append(
                        f"{claim_id}: file '{rf}' exists but criterion NOT met "
                        f"(delta={result_data.get('delta', 'N/A')})"
                    )

    # Check if delta/split failures break traceability
    if checks["split_correctness"]["status"] == "fail" or \
       checks["delta_assertion"]["status"] == "fail":
        checks["evidence_mapping"] = {
            "status": "fail",
            "details": "EVIDENCE MAPPING BROKEN: Result files exist but cannot "
                       "support claims due to split mismatch and/or zero delta. " +
                       " | ".join(evidence_details) if evidence_details else
                       "Upstream check failures invalidate evidence chain.",
        }
    elif evidence_details:
        checks["evidence_mapping"] = {
            "status": "warn",
            "details": " | ".join(evidence_details),
        }
    else:
        checks["evidence_mapping"] = {
            "status": "pass",
            "details": "All claims traceable to existing result files "
                       "that meet success criteria.",
        }

    # --- Overall Verdict ---
    statuses = []
    for k, v in checks.items():
        if isinstance(v, dict) and "status" in v:
            statuses.append(v["status"])

    if "fail" in statuses:
        overall = "fail"
    elif "warn" in statuses:
        overall = "warn"
    else:
        overall = "pass"

    # --- Deviations status summary ---
    if deviations is None:
        dev_status = "missing"
    elif not deviations:
        dev_status = "no_deviation_receipt"
    elif any(d.get("status") == "unresolved" for d in deviations):
        dev_status = "present_with_unresolved_drift"
    else:
        dev_status = "present_with_accepted_drift"

    # --- Claim impact ---
    claims_impact = []
    for claim_id in plan["claims"]:
        if overall == "fail":
            claims_impact.append({"id": claim_id, "impact": "unsupported"})
        elif overall == "warn":
            claims_impact.append({"id": claim_id, "impact": "needs_qualifier"})
        else:
            claims_impact.append({"id": claim_id, "impact": "supported"})

    audit = {
        "date": "2026-05-14",
        "auditor": "e2e-drill-simulator (local, no Codex MCP)",
        "overall_verdict": overall,
        "integrity_status": overall,
        "checks": checks,
        "implementation_deviations_status": dev_status,
        "recovery_context_status": "none",
        "claims": claims_impact,
    }

    return audit


# ---------------------------------------------------------------------------
# Phase 4: Claim Gate Simulation (result-to-claim Step 3.5 logic)
# ---------------------------------------------------------------------------

def run_claim_gate(plan: dict, audit: dict, artifacts: dict) -> dict:
    """Simulate result-to-claim verdict logic per SKILL.md Step 3.5."""

    main_result = artifacts["main_result"]
    deviations = artifacts.get("deviations", []) or []
    checks = audit["checks"]

    # Start with base assessment from results
    delta = abs(main_result.get("delta", 0))
    criterion_met = main_result.get("criterion_met", False)

    verdict = {
        "claim_supported": "yes" if criterion_met else "no",
        "confidence": "high",
        "what_results_support": "",
        "what_results_dont_support": "",
        "missing_evidence": "",
        "suggested_claim_revision": "",
        "evidence_mapping_status": "aligned",
        "delta_assertion_status": "satisfied",
        "implementation_deviation_impact": "none",
        "recovery_context_status": "none",
        "integrity_status": audit.get("integrity_status", "unavailable"),
        "plan_drift_tags": [],
    }

    # --- Step 3.5: Check audit results ---

    # Implementation conformance
    impl_check = checks.get("implementation_conformance", {})
    if impl_check.get("status") == "fail":
        verdict["claim_supported"] = "no"
        verdict["what_results_dont_support"] += (
            "Implementation conformance failed — planned claim coverage is broken. "
        )

    # Unresolved deviations with breaks_claim_test
    unresolved_breaking = [
        d for d in deviations
        if d.get("status") == "unresolved"
        and d.get("claim_impact") == "breaks_claim_test"
    ]

    if unresolved_breaking:
        verdict["claim_supported"] = "no"
        verdict["implementation_deviation_impact"] = "breaks_claim_test"
        verdict["plan_drift_tags"].append(
            "[PLAN DRIFT] — unresolved implementation deviation affects claim coverage"
        )
        # Downgrade confidence by one level
        confidence_levels = ["high", "medium", "low"]
        current_idx = confidence_levels.index(verdict["confidence"])
        verdict["confidence"] = confidence_levels[
            min(current_idx + 1, len(confidence_levels) - 1)
        ]

    # Narrow scope / weakens evidence deviations
    narrowing = [
        d for d in deviations
        if d.get("claim_impact") in ("narrow_scope", "weakens_evidence")
    ]
    if narrowing and verdict["implementation_deviation_impact"] == "none":
        verdict["implementation_deviation_impact"] = narrowing[0]["claim_impact"]

    # Delta assertion
    delta_check = checks.get("delta_assertion", {})
    if delta_check.get("status") == "fail":
        verdict["claim_supported"] = "no"
        verdict["delta_assertion_status"] = "failed"
        verdict["what_results_dont_support"] += (
            "Core modification shows no observable effect (delta assertion failed). "
        )

    # Evidence mapping
    evidence_check = checks.get("evidence_mapping", {})
    if evidence_check.get("status") == "fail":
        verdict["evidence_mapping_status"] = "broken"
        verdict["what_results_dont_support"] += (
            "Claim-traceability-broken: evidence chain invalidated by upstream failures. "
        )
    elif evidence_check.get("status") == "warn":
        verdict["evidence_mapping_status"] = "partial"

    # Split correctness
    split_check = checks.get("split_correctness", {})
    if split_check.get("status") == "fail":
        verdict["missing_evidence"] += (
            f"Correct split evaluation required: plan says "
            f"'{split_check.get('planned', 'test')}' but actual is "
            f"'{split_check.get('actual', 'unknown')}'. "
        )

    # Integrity status gating
    if audit.get("integrity_status") == "fail":
        verdict["confidence"] = "low"
        if "[INTEGRITY CONCERN]" not in str(verdict.get("plan_drift_tags", [])):
            verdict["plan_drift_tags"].append(
                "[INTEGRITY CONCERN] — audit found issues, see EXPERIMENT_AUDIT"
            )

    # --- Fill in human-readable fields ---
    if verdict["claim_supported"] == "no":
        verdict["what_results_support"] = (
            "Pipeline runs without crash. Result files are generated."
        )
        if not verdict["what_results_dont_support"]:
            verdict["what_results_dont_support"] = (
                "No evidence that ToyClassifier outperforms BaselineMLP."
            )
        if not verdict["missing_evidence"]:
            verdict["missing_evidence"] = (
                "Correct split evaluation; observable delta between systems."
            )
        verdict["suggested_claim_revision"] = (
            "Cannot make any performance claim until split and delta issues are "
            "resolved. Re-run with correct test split and functioning attention module."
        )
    elif verdict["claim_supported"] == "partial":
        verdict["suggested_claim_revision"] = (
            "Narrow the claim to match the actually tested scope."
        )

    return verdict


# ---------------------------------------------------------------------------
# Main — run the full drill
# ---------------------------------------------------------------------------

def run_drill():
    """Execute the full e2e drill and return (audit, claim_verdict)."""

    print("=" * 70)
    print("  ARIS End-to-End Drill: ToyClassifier on CIFAR-10")
    print("  Injected failures: wrong split + dead code path")
    print("=" * 70)

    # Phase 1: Parse plan
    print("\n[Phase 1] Parsing experiment plan...")
    plan = parse_plan(REFINE_LOGS / "EXPERIMENT_PLAN.md")
    print(f"  Planned split: {plan['planned_split']}")
    print(f"  GT source: {plan['gt_source']}")
    print(f"  Claims: {plan['claims']}")
    print(f"  Expected result files: {plan['expected_result_files']}")

    # Phase 2: Load bridge artifacts
    print("\n[Phase 2] Loading bridge artifacts...")
    artifacts = load_bridge_artifacts(DRILL_DIR)
    deviations = artifacts.get("deviations", [])
    print(f"  Deviations found: {len(deviations) if deviations else 0}")
    if deviations:
        for i, d in enumerate(deviations):
            print(f"    [{i+1}] {d['deviation_type']}: "
                  f"{d['planned_value'][:50]}... → {d['actual_value'][:50]}... "
                  f"[{d['claim_impact']}, {d['status']}]")

    # Phase 3: Run audit
    print("\n[Phase 3] Running audit simulation (checks A–J)...")
    audit = run_audit(plan, artifacts)

    for key, val in audit["checks"].items():
        if isinstance(val, dict):
            status = val["status"].upper()
            symbol = {"PASS": "✅", "WARN": "⚠️", "FAIL": "🔴"}[status]
            print(f"  {symbol} Check {key}: {status}")
        else:
            print(f"  ℹ️  Check {key}: {val}")

    print(f"\n  Overall verdict: {audit['overall_verdict'].upper()}")
    print(f"  Integrity status: {audit['integrity_status']}")
    print(f"  Deviations status: {audit['implementation_deviations_status']}")

    # Write audit artifacts
    write_json(AUDIT_DIR / "EXPERIMENT_AUDIT.json", audit)
    print(f"\n  Written: audit/EXPERIMENT_AUDIT.json")

    # Phase 4: Run claim gate
    print("\n[Phase 4] Running claim gate simulation...")
    verdict = run_claim_gate(plan, audit, artifacts)

    print(f"  claim_supported: {verdict['claim_supported']}")
    print(f"  confidence: {verdict['confidence']}")
    print(f"  delta_assertion_status: {verdict['delta_assertion_status']}")
    print(f"  implementation_deviation_impact: {verdict['implementation_deviation_impact']}")
    print(f"  evidence_mapping_status: {verdict['evidence_mapping_status']}")
    if verdict.get("plan_drift_tags"):
        for tag in verdict["plan_drift_tags"]:
            print(f"  🏷️  {tag}")

    # Write claim verdict
    write_json(CLAIM_DIR / "CLAIM_VERDICT.json", verdict)
    print(f"\n  Written: claim/CLAIM_VERDICT.json")

    # Summary
    print("\n" + "=" * 70)
    if verdict["claim_supported"] == "no":
        print("  ❌ DRILL RESULT: Claim correctly BLOCKED")
        print("     The audit + claim gate caught the injected failures.")
        print("     This confirms the hardened pipeline works as designed.")
    elif verdict["claim_supported"] == "partial":
        print("  ⚠️  DRILL RESULT: Claim correctly NARROWED")
    else:
        print("  ⚠️  UNEXPECTED: Claim was supported despite injected failures!")
        print("     This would indicate a gap in the audit/claim logic.")
    print("=" * 70)

    return audit, verdict


if __name__ == "__main__":
    run_drill()
