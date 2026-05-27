#!/usr/bin/env python3
"""Pytest assertions for the ARIS end-to-end drill.

Verifies that the hardened audit + claim gate correctly catches
two deliberately injected failures:
  1. Wrong split (train instead of test)
  2. Dead code path (attention module bypassed, no delta)

Run:
    cd tests/e2e_drill
    python -m pytest test_e2e_drill.py -v
"""

import json
import os
import sys
import unittest
from pathlib import Path

# Ensure run_drill is importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_drill


class TestE2EDrill(unittest.TestCase):
    """Run the full drill once, then assert on the produced artifacts."""

    @classmethod
    def setUpClass(cls):
        """Execute the drill and cache results for all tests."""
        cls.audit, cls.verdict = run_drill.run_drill()
        cls.checks = cls.audit["checks"]

    # ------------------------------------------------------------------
    # Audit checks
    # ------------------------------------------------------------------

    def test_audit_catches_wrong_split(self):
        """Check G (Split Correctness) should FAIL when eval uses train
        split instead of the planned test split."""
        split_check = self.checks["split_correctness"]
        self.assertEqual(split_check["status"], "fail",
                         f"Expected split_correctness=fail, got {split_check['status']}")
        self.assertIn("train", split_check["details"].lower(),
                      "Audit should mention that 'train' split was used")
        self.assertIn("test", split_check["details"].lower(),
                      "Audit should mention that 'test' split was planned")

    def test_audit_catches_no_delta(self):
        """Check I (Delta Assertion) should FAIL when experiment vs control
        produces identical results (delta=0, same predictions_hash)."""
        delta_check = self.checks["delta_assertion"]
        self.assertEqual(delta_check["status"], "fail",
                         f"Expected delta_assertion=fail, got {delta_check['status']}")
        self.assertIn("no observable effect",
                      delta_check["details"].lower().replace("no\nobservable", "no observable"),
                      "Audit should state the core modification has no observable effect")

    def test_audit_catches_dead_code(self):
        """Check D (Dead Code Detection) should WARN when ChannelAttention
        is defined but never called in forward()."""
        dead_check = self.checks["dead_code"]
        self.assertEqual(dead_check["status"], "warn",
                         f"Expected dead_code=warn, got {dead_check['status']}")
        self.assertIn("attention", dead_check["details"].lower(),
                      "Audit should mention the attention module as dead code")

    def test_audit_catches_unresolved_deviation(self):
        """Check H (Implementation Conformance) should FAIL when
        IMPLEMENTATION_DEVIATIONS.json has unresolved items with
        claim_impact=breaks_claim_test."""
        conf_check = self.checks["implementation_conformance"]
        self.assertEqual(conf_check["status"], "fail",
                         f"Expected implementation_conformance=fail, got {conf_check['status']}")
        self.assertIn("breaks_claim_test", conf_check["details"],
                      "Audit should cite breaks_claim_test impact")
        self.assertIn("unresolved", conf_check["details"].lower(),
                      "Audit should cite unresolved status")

    def test_audit_overall_verdict_is_fail(self):
        """Overall audit verdict must be FAIL given checks G, H, I all fail."""
        self.assertEqual(self.audit["overall_verdict"], "fail",
                         f"Expected overall_verdict=fail, got {self.audit['overall_verdict']}")
        self.assertEqual(self.audit["integrity_status"], "fail",
                         f"Expected integrity_status=fail, got {self.audit['integrity_status']}")

    # ------------------------------------------------------------------
    # Claim gate checks
    # ------------------------------------------------------------------

    def test_claim_gate_blocks_claim(self):
        """claim_supported must be 'no' given audit failures and
        unresolved deviations with breaks_claim_test."""
        self.assertEqual(self.verdict["claim_supported"], "no",
                         f"Expected claim_supported=no, got {self.verdict['claim_supported']}")

    def test_claim_confidence_is_low(self):
        """confidence must be downgraded to 'low' given
        integrity_status == fail."""
        self.assertEqual(self.verdict["confidence"], "low",
                         f"Expected confidence=low, got {self.verdict['confidence']}")

    def test_claim_has_plan_drift_tag(self):
        """Verdict must carry [PLAN DRIFT] tag for unresolved deviation."""
        tags = self.verdict.get("plan_drift_tags", [])
        has_drift_tag = any("[PLAN DRIFT]" in t for t in tags)
        self.assertTrue(has_drift_tag,
                        f"Expected [PLAN DRIFT] tag in verdict, got: {tags}")

    def test_claim_delta_assertion_failed(self):
        """delta_assertion_status must be 'failed' in the verdict."""
        self.assertEqual(self.verdict["delta_assertion_status"], "failed",
                         f"Expected delta_assertion_status=failed, "
                         f"got {self.verdict['delta_assertion_status']}")

    def test_claim_evidence_mapping_broken(self):
        """evidence_mapping_status must be 'broken' given upstream failures."""
        self.assertEqual(self.verdict["evidence_mapping_status"], "broken",
                         f"Expected evidence_mapping_status=broken, "
                         f"got {self.verdict['evidence_mapping_status']}")

    def test_claim_deviation_impact_is_breaks(self):
        """implementation_deviation_impact must be 'breaks_claim_test'."""
        self.assertEqual(
            self.verdict["implementation_deviation_impact"],
            "breaks_claim_test",
            f"Expected breaks_claim_test, "
            f"got {self.verdict['implementation_deviation_impact']}")

    def test_claim_has_integrity_concern_tag(self):
        """Verdict must carry [INTEGRITY CONCERN] tag when audit fails."""
        tags = self.verdict.get("plan_drift_tags", [])
        has_integrity_tag = any("[INTEGRITY CONCERN]" in t for t in tags)
        self.assertTrue(has_integrity_tag,
                        f"Expected [INTEGRITY CONCERN] tag, got: {tags}")

    # ------------------------------------------------------------------
    # Artifact existence
    # ------------------------------------------------------------------

    def test_audit_json_written(self):
        """EXPERIMENT_AUDIT.json should be written to audit/ directory."""
        path = run_drill.AUDIT_DIR / "EXPERIMENT_AUDIT.json"
        self.assertTrue(path.exists(), f"Missing: {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertIn("overall_verdict", data)
        self.assertIn("checks", data)

    def test_claim_verdict_json_written(self):
        """CLAIM_VERDICT.json should be written to claim/ directory."""
        path = run_drill.CLAIM_DIR / "CLAIM_VERDICT.json"
        self.assertTrue(path.exists(), f"Missing: {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertIn("claim_supported", data)
        self.assertIn("confidence", data)


if __name__ == "__main__":
    unittest.main()
