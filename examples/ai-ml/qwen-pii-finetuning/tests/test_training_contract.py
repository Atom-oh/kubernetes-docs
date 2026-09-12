from pathlib import Path

from src.train import (
    adapter_file_inventory,
    build_resolved_config,
    format_training_text,
    log_adapter_artifacts,
)


ROOT = Path(__file__).resolve().parents[1]


def test_resolved_config_changes_only_environment_fields():
    config_path = ROOT / "config" / "experiment.yaml"

    sagemaker = build_resolved_config(config_path, "sagemaker", 10)
    eks = build_resolved_config(config_path, "eks", 10)

    assert sagemaker["model_id"] == eks["model_id"]
    assert sagemaker["training"] == eks["training"]
    assert sagemaker["dataset"] == eks["dataset"]
    assert sagemaker["run_environment"] == "sagemaker"
    assert eks["run_environment"] == "eks"
    assert sagemaker["execution_steps"] == 10
    assert eks["execution_steps"] == 10


def test_sft_text_uses_instruction_source_and_tsv_target():
    record = {
        "source_text": "고객 김민수",
        "target_tsv": "PERSON\t김민수",
    }

    text = format_training_text(record)

    assert "TYPE<TAB>ORIGINAL" in text
    assert "고객 김민수" in text
    assert text.rstrip().endswith("PERSON\t김민수")


def test_training_module_imports_without_gpu_dependencies():
    import src.train

    assert callable(src.train.main)


def test_adapter_inventory_is_stable_and_excludes_other_artifacts(tmp_path):
    (tmp_path / "adapter_model.safetensors").write_bytes(b"adapter")
    (tmp_path / "adapter_config.json").write_text("{}")
    (tmp_path / "baseline-metrics.json").write_text("{}")

    assert adapter_file_inventory(tmp_path) == [
        {"name": "adapter_config.json", "bytes": 2},
        {"name": "adapter_model.safetensors", "bytes": 7},
    ]


def test_adapter_weights_are_logged_before_ephemeral_storage_is_deleted(tmp_path):
    from unittest.mock import Mock

    (tmp_path / "adapter_model.safetensors").write_bytes(b"adapter")
    (tmp_path / "adapter_config.json").write_text("{}")
    (tmp_path / "raw-predictions.jsonl").write_text("private")
    mlflow = Mock()
    log_adapter_artifacts(mlflow, tmp_path)
    assert [call.args[0] for call in mlflow.log_artifact.call_args_list] == [
        str(tmp_path / "adapter_config.json"),
        str(tmp_path / "adapter_model.safetensors"),
    ]
    assert all(
        call.kwargs == {"artifact_path": "adapter"}
        for call in mlflow.log_artifact.call_args_list
    )


def test_eks_run_logs_bound_execution_identifiers(monkeypatch):
    from unittest.mock import Mock
    from src.train import _safe_log_params

    monkeypatch.setenv("QWEN_EXPERIMENT_ID", "qwen-pii-fixture")
    monkeypatch.setenv("QWEN_CLUSTER_NAME", "qwen-pii-fixture-smoke-eks")
    monkeypatch.setenv("QWEN_EXECUTION_ID", "1234567890abcdef1234567890abcdef")
    resolved = build_resolved_config(ROOT / "config/experiment.yaml", "eks", 10)
    mlflow = Mock()
    _safe_log_params(mlflow, resolved, {})
    params = mlflow.log_params.call_args.args[0]
    assert params["experiment_id"] == "qwen-pii-fixture"
    assert params["cluster_name"] == "qwen-pii-fixture-smoke-eks"
    assert params["execution_id"] == "1234567890abcdef1234567890abcdef"
