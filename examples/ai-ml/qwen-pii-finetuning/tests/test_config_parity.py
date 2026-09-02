from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_experiment_config_contains_the_approved_constants():
    config = yaml.safe_load((ROOT / "config/experiment.yaml").read_text())

    assert config["model_id"] == "Qwen/Qwen3-30B-A3B-Instruct-2507"
    assert config["seed"] == 42
    assert config["dataset"] == {"train": 1600, "validation": 200, "test": 400}
    assert config["languages"] == {"ko": 0.8, "en": 0.2}
    assert config["training"]["max_steps"] == 80
    assert config["training"]["smoke_steps"] == 10
    assert config["training"]["max_runtime_seconds"] == 10800
    assert config["compute"]["sagemaker"] == "ml.g6e.4xlarge"
    assert config["compute"]["eks"] == "g6e.4xlarge"
