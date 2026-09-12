from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from launch.eks.export_mlflow import export_run


PROVENANCE = {
    "experiment_id": "qwen-pii-fixture",
    "cluster_name": "qwen-pii-fixture-smoke-eks",
    "execution_id": "1234567890abcdef1234567890abcdef",
}


class Page(list):
    token = None


def client_fixture():
    client = Mock()
    client.get_experiment_by_name.return_value = SimpleNamespace(experiment_id="1")
    run = SimpleNamespace(
        info=SimpleNamespace(
            run_id="a" * 32, run_name="eks-smoke", status="FINISHED",
            start_time=1, end_time=2,
        ),
        data=SimpleNamespace(
            metrics={"f1": 1.0},
            params={"run_environment": "eks", "model_id": "model", "private": "skip", **PROVENANCE},
        ),
    )
    client.search_runs.return_value = Page([run])

    def download(run_id, path, dst_path):
        output = Path(dst_path) / Path(path).name
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"artifact")
        return str(output)

    client.download_artifacts.side_effect = download
    return client


def test_export_preserves_allowlisted_files_and_ignores_raw_data(tmp_path):
    client = client_fixture()
    result = export_run(client, "smoke", tmp_path, expected_provenance=PROVENANCE)
    assert result["provenance"] == PROVENANCE
    paths = {item["path"] for item in result["artifacts"]}
    assert "adapter/adapter_model.safetensors" in paths
    assert "dataset-manifest.json" in paths
    assert "run-summary.json" in paths
    assert "raw-predictions.jsonl" not in paths
    assert "private" not in result["params"]
    assert all(len(item["sha256"]) == 64 for item in result["artifacts"])


def test_export_fails_when_a_required_artifact_is_missing(tmp_path):
    client = client_fixture()
    client.download_artifacts.side_effect = FileNotFoundError
    with pytest.raises(FileNotFoundError):
        export_run(client, "smoke", tmp_path, expected_provenance=PROVENANCE)
    assert not (tmp_path / "export.json").exists()


def test_export_refuses_missing_or_ambiguous_runs(tmp_path):
    client = client_fixture()
    client.search_runs.return_value = Page([])
    with pytest.raises(ValueError):
        export_run(client, "smoke", tmp_path, expected_provenance=PROVENANCE)
    run = client_fixture().search_runs.return_value[0]
    client.search_runs.return_value = Page([run, run])
    with pytest.raises(ValueError):
        export_run(client, "smoke", tmp_path, expected_provenance=PROVENANCE)


def test_export_checks_all_search_pages(tmp_path):
    client = client_fixture()
    second = client.search_runs.return_value
    first = Page([])
    first.token = "page2"
    client.search_runs.side_effect = [first, second]
    assert export_run(client, "smoke", tmp_path, expected_provenance=PROVENANCE)["run_id"] == "a" * 32
    assert client.search_runs.call_args.kwargs["page_token"] == "page2"


def test_same_mode_run_from_another_execution_is_rejected(tmp_path):
    client = client_fixture()
    client.search_runs.return_value[0].data.params["execution_id"] = "other-execution"
    with pytest.raises(ValueError, match="exactly one"):
        export_run(client, "smoke", tmp_path, expected_provenance=PROVENANCE)
    client.download_artifacts.assert_not_called()
