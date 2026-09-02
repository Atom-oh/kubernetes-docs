"""Export aggregate MLflow run metadata from the in-cluster server."""

import json
from pathlib import Path

from mlflow import MlflowClient


def main() -> None:
    client = MlflowClient(tracking_uri="http://127.0.0.1:5000")
    export = {"experiments": []}
    for experiment in client.search_experiments():
        experiment_data = {
            "experiment_id": experiment.experiment_id,
            "name": experiment.name,
            "runs": [],
        }
        for run in client.search_runs([experiment.experiment_id]):
            experiment_data["runs"].append(
                {
                    "run_id": run.info.run_id,
                    "run_name": run.info.run_name,
                    "status": run.info.status,
                    "start_time": run.info.start_time,
                    "end_time": run.info.end_time,
                    "metrics": dict(sorted(run.data.metrics.items())),
                    "params": dict(sorted(run.data.params.items())),
                }
            )
        export["experiments"].append(experiment_data)
    Path("/tmp/mlflow-export.json").write_text(
        json.dumps(export, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
