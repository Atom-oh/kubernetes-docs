"""Execution gate for the historical, pinned PyTorch DLC baseline.

Source: aws/deep-learning-containers,
docs/src/data/pytorch-training/2.8-gpu-sagemaker.yml (reviewed 2026-09-12).
The published catalog reports eop: 2026-08-06.
"""

import argparse
from datetime import date, datetime, timezone


DLC_PATCH_END = date(2026, 8, 6)


def require_supported_baseline(today: date | None = None) -> None:
    today = today or datetime.now(timezone.utc).date()
    if today > DLC_PATCH_END:
        raise RuntimeError(
            "Execution blocked: the pinned PyTorch 2.8 DLC reached end of patch "
            "on 2026-08-06. Update and validate the DLC, torch/dependency pins, "
            "and GPU smoke run together before enabling this example. "
            "Local tests/request previews and owned-resource cleanup remain available."
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-execution", action="store_true", required=True)
    parser.parse_args()
    try:
        require_supported_baseline()
    except RuntimeError as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
