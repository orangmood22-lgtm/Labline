"""Evaluation script for CIFAR-10 classification.

DELIBERATE BUG: The split is hardcoded to "train" instead of "test".
The experiment plan requires evaluation on the TEST split, but this
script evaluates on the TRAIN split — a classic data leakage bug
that the audit system should catch.
"""

import json
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))


def evaluate_model(model_name: str, split: str = "train") -> dict:
    """Evaluate a model on CIFAR-10.

    BUG (intentional): split defaults to "train" and is hardcoded below,
    ignoring the plan's requirement to use "test".

    In a real implementation this would load the model and dataset.
    For this drill we return mock results.
    """
    # === BUG: hardcoded to train split regardless of argument ===
    actual_split = "train"  # Should be: actual_split = split

    # Mock results — both models get identical accuracy because
    # ToyClassifier's attention module is bypassed (dead path)
    mock_results = {
        "ToyClassifier": {
            "accuracy": 0.782,
            "predictions_hash": "abc123def456",
            "num_samples": 50000 if actual_split == "train" else 10000,
        },
        "BaselineMLP": {
            "accuracy": 0.782,
            "predictions_hash": "abc123def456",  # Same hash = identical predictions
            "num_samples": 50000 if actual_split == "train" else 10000,
        },
    }

    if model_name not in mock_results:
        raise ValueError(f"Unknown model: {model_name}")

    result = mock_results[model_name]
    result["model"] = model_name
    result["split"] = actual_split
    result["dataset"] = "CIFAR-10"

    return result


def run_block1():
    """Run Block 1: Main Result — ToyClassifier vs BaselineMLP."""
    toy_result = evaluate_model("ToyClassifier", split="test")  # BUG: ignored
    baseline_result = evaluate_model("BaselineMLP", split="test")  # BUG: ignored

    output = {
        "block": "B1_main_result",
        "claim_tested": "C1",
        "dataset": "CIFAR-10",
        "split_used": toy_result["split"],  # Will say "train" — the bug
        "planned_split": "test",
        "results": {
            "ToyClassifier": {
                "accuracy": toy_result["accuracy"],
                "predictions_hash": toy_result["predictions_hash"],
                "num_samples": toy_result["num_samples"],
            },
            "BaselineMLP": {
                "accuracy": baseline_result["accuracy"],
                "predictions_hash": baseline_result["predictions_hash"],
                "num_samples": baseline_result["num_samples"],
            },
        },
        "delta": toy_result["accuracy"] - baseline_result["accuracy"],
        "success_criterion": "delta >= 0.05",
        "criterion_met": (toy_result["accuracy"] - baseline_result["accuracy"]) >= 0.05,
    }

    return output


def run_block2():
    """Run Block 2: Ablation — Full ToyClassifier vs NoAttention variant."""
    # Since attention is bypassed, ablation also shows no difference
    full_result = evaluate_model("ToyClassifier", split="test")

    output = {
        "block": "B2_ablation",
        "claim_tested": "C1 (novelty isolation)",
        "dataset": "CIFAR-10",
        "split_used": full_result["split"],  # Will say "train"
        "planned_split": "test",
        "results": {
            "ToyClassifier_full": {
                "accuracy": 0.782,
            },
            "ToyClassifier_no_attention": {
                "accuracy": 0.780,  # Tiny difference (noise, not real)
            },
        },
        "delta": 0.782 - 0.780,
        "success_criterion": "delta >= 0.02",
        "criterion_met": (0.782 - 0.780) >= 0.02,
    }

    return output


if __name__ == "__main__":
    results_dir = os.path.join(os.path.dirname(__file__), "..", "results")
    os.makedirs(results_dir, exist_ok=True)

    # Block 1
    b1 = run_block1()
    with open(os.path.join(results_dir, "main_result.json"), "w") as f:
        json.dump(b1, f, indent=2)
    print(f"Block 1: delta={b1['delta']:.4f}, criterion_met={b1['criterion_met']}")

    # Block 2
    b2 = run_block2()
    with open(os.path.join(results_dir, "ablation_result.json"), "w") as f:
        json.dump(b2, f, indent=2)
    print(f"Block 2: delta={b2['delta']:.4f}, criterion_met={b2['criterion_met']}")
