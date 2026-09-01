from pathlib import Path

from src.train import (
    adapter_file_inventory,
    build_resolved_config,
    format_training_text,
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
