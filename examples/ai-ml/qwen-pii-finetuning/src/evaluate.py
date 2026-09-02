"""Aggregate model predictions without persisting raw PII in the output."""

import argparse
import hashlib
import json
from decimal import Decimal
from pathlib import Path

from src.metrics import compute_cost, evaluate_predictions


DEFAULT_MODEL_ID = "Qwen/Qwen3-30B-A3B-Instruct-2507"


def read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictions-jsonl", type=Path, required=True)
    parser.add_argument("--test-jsonl", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--phase", required=True)
    parser.add_argument("--duration-seconds", type=float, required=True)
    parser.add_argument("--hourly-usd", type=Decimal, required=True)
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    args = parser.parse_args()

    records = read_jsonl(args.test_jsonl)
    predictions = read_jsonl(args.predictions_jsonl)
    summary = evaluate_predictions(records, predictions)
    output = {
        "environment": args.environment,
        "phase": args.phase,
        "model_id": args.model_id,
        "dataset_sha256": hashlib.sha256(args.test_jsonl.read_bytes()).hexdigest(),
        "duration_seconds": args.duration_seconds,
        "hourly_usd": str(args.hourly_usd),
        "cost_usd": str(compute_cost(args.duration_seconds, args.hourly_usd)),
        "metrics": summary,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        f"{json.dumps(output, indent=2, sort_keys=True)}\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
