"""Export one completed comparison run and its allowlisted artifacts."""

import argparse
import hashlib
import json
import re
import tarfile
from pathlib import Path


ARTIFACTS = (
    "dataset-manifest.json",
    "resolved-config.json",
    "dependency-versions.json",
    "baseline-metrics.json",
    "tuned-metrics.json",
    "run-summary.json",
    "adapter/adapter_config.json",
    "adapter/adapter_model.safetensors",
)
PARAMS = {
    "model_id", "seed", "run_environment", "execution_steps", "quantization",
    "lora_rank", "lora_alpha", "max_sequence_length", "learning_rate",
    "dataset_train_count", "dataset_validation_count", "dataset_test_count",
}


def export_run(client, mode: str, output: Path) -> dict:
    if mode not in {"smoke", "full"}:
        raise ValueError("Invalid mode")
    experiment = client.get_experiment_by_name("qwen-pii-finetuning")
    if experiment is None:
        raise ValueError("Comparison experiment was not found")
    candidates = []
    token = None
    while True:
        page = client.search_runs([experiment.experiment_id], page_token=token)
        candidates.extend(
            run for run in page
            if run.info.run_name == f"eks-{mode}"
            and run.info.status == "FINISHED"
            and run.data.params.get("run_environment") == "eks"
        )
        token = page.token
        if not token:
            break
    if len(candidates) != 1:
        raise ValueError("Expected exactly one completed comparison run")
    run = candidates[0]
    if not re.fullmatch(r"[a-fA-F0-9]{32}", run.info.run_id):
        raise ValueError("Unexpected run ID")
    output.mkdir(parents=True, exist_ok=True)
    artifacts = []
    for name in ARTIFACTS:
        destination = (output / name).parent
        destination.mkdir(parents=True, exist_ok=True)
        path = Path(client.download_artifacts(run.info.run_id, name, str(destination)))
        if path.resolve() != (output / name).resolve() or path.is_symlink():
            raise ValueError("Unexpected artifact destination")
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        artifacts.append(
            {"path": name, "bytes": path.stat().st_size, "sha256": digest.hexdigest()}
        )
    result = {
        "run_id": run.info.run_id,
        "run_name": run.info.run_name,
        "status": run.info.status,
        "start_time": run.info.start_time,
        "end_time": run.info.end_time,
        "metrics": dict(sorted(run.data.metrics.items())),
        "params": {
            key: value for key, value in sorted(run.data.params.items())
            if key in PARAMS or key.startswith("version_")
        },
        "artifacts": artifacts,
    }
    (output / "export.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def main() -> None:
    from mlflow import MlflowClient

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("smoke", "full"), required=True)
    args = parser.parse_args()
    output = Path(f"/tmp/mlflow-export-{args.mode}")
    if output.exists():
        raise FileExistsError("Export directory already exists; inspect it before retrying")
    export_run(MlflowClient(tracking_uri="http://127.0.0.1:5000"), args.mode, output)
    with tarfile.open(f"{output}.tar.gz", "w:gz") as archive:
        for name in (*ARTIFACTS, "export.json"):
            archive.add(output / name, arcname=name, recursive=False)


if __name__ == "__main__":
    main()
