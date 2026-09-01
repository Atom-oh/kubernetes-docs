"""Common QLoRA training entry point for SageMaker AI and Amazon EKS."""

import argparse
import copy
import importlib.metadata
import json
import os
import time
from pathlib import Path

import yaml

from src.dataset import (
    SYSTEM_INSTRUCTION,
    load_sft_dataset,
    prompt_messages,
    read_jsonl,
)
from src.metrics import evaluate_predictions
from src.pii_tokens import THINK_PATTERN, VALID_TYPES, parse_tsv


DEPENDENCIES = (
    "torch",
    "transformers",
    "peft",
    "trl",
    "accelerate",
    "bitsandbytes",
    "datasets",
    "mlflow",
    "sagemaker-mlflow",
)


def build_resolved_config(
    config_path: Path, environment: str, steps: int
) -> dict:
    config = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    resolved = copy.deepcopy(config)
    resolved["run_environment"] = environment
    resolved["execution_steps"] = int(steps)
    return resolved


def format_training_text(record: dict) -> str:
    return (
        f"### Instruction\n{SYSTEM_INSTRUCTION}\n\n"
        f"### Document\n{record['source_text']}\n\n"
        f"### Response\n{record['target_tsv']}"
    )


def dependency_versions() -> dict[str, str]:
    versions = {}
    for package in DEPENDENCIES:
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = "not-installed"
    return versions


def adapter_file_inventory(output_dir: Path) -> list[dict]:
    allowed = {"adapter_config.json", "adapter_model.safetensors"}
    return [
        {"name": path.name, "bytes": path.stat().st_size}
        for path in sorted(Path(output_dir).rglob("*"), key=lambda item: item.name)
        if path.is_file() and path.name in allowed
    ]


def _completion_is_parseable(content: str, source_text: str) -> bool:
    clean = THINK_PATTERN.sub("", content).strip()
    if not clean:
        return True
    return bool(parse_tsv(clean, source_text))


def _predict_records(
    model,
    tokenizer,
    records: list[dict],
    max_sequence_length: int,
    batch_size: int,
) -> list[dict]:
    import torch

    predictions = []
    previous_padding_side = tokenizer.padding_side
    tokenizer.padding_side = "left"
    model.eval()
    for offset in range(0, len(records), batch_size):
        batch = records[offset : offset + batch_size]
        prompts = [
            tokenizer.apply_chat_template(
                prompt_messages(record),
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=False,
            )
            for record in batch
        ]
        inputs = tokenizer(
            prompts,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=max_sequence_length,
        ).to(model.device)
        with torch.inference_mode():
            output_ids = model.generate(
                **inputs,
                do_sample=False,
                max_new_tokens=512,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id,
            )
        generated_ids = output_ids[:, inputs["input_ids"].shape[1] :]
        completions = tokenizer.batch_decode(
            generated_ids, skip_special_tokens=True
        )
        for record, content in zip(batch, completions):
            predictions.append(
                {
                    "id": record["id"],
                    "content": content,
                    "parse_success": _completion_is_parseable(
                        content, record["source_text"]
                    ),
                }
            )
    tokenizer.padding_side = previous_padding_side
    return predictions


def _flatten_numeric(prefix: str, value, output: dict[str, float]) -> None:
    if isinstance(value, bool):
        output[prefix] = float(value)
    elif isinstance(value, (int, float)):
        output[prefix] = float(value)
    elif isinstance(value, dict):
        for key, child in value.items():
            child_prefix = f"{prefix}.{key}" if prefix else key
            _flatten_numeric(child_prefix, child, output)


def _safe_log_params(mlflow, resolved: dict, versions: dict[str, str]) -> None:
    training = resolved["training"]
    params = {
        "model_id": resolved["model_id"],
        "seed": resolved["seed"],
        "run_environment": resolved["run_environment"],
        "execution_steps": resolved["execution_steps"],
        "quantization": training["quantization"],
        "lora_rank": training["lora_rank"],
        "lora_alpha": training["lora_alpha"],
        "max_sequence_length": training["max_sequence_length"],
        "learning_rate": training["learning_rate"],
        "dataset_train_count": resolved["dataset"]["train"],
        "dataset_validation_count": resolved["dataset"]["validation"],
        "dataset_test_count": resolved["dataset"]["test"],
    }
    params.update({f"version_{key}": value for key, value in versions.items()})
    mlflow.log_params(params)


def _write_json(path: Path, value: dict) -> None:
    path.write_text(
        f"{json.dumps(value, indent=2, sort_keys=True)}\n",
        encoding="utf-8",
    )


def run_training(args: argparse.Namespace) -> None:
    import mlflow
    import torch
    from peft import LoraConfig, prepare_model_for_kbit_training
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        BitsAndBytesConfig,
        set_seed,
    )
    from trl import SFTConfig, SFTTrainer

    resolved = build_resolved_config(args.config, args.environment, args.steps)
    training = resolved["training"]
    set_seed(int(resolved["seed"]))
    os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "1")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    resolved_path = output_dir / "resolved-config.json"
    versions_path = output_dir / "dependency-versions.json"
    baseline_path = output_dir / "baseline-metrics.json"
    tuned_path = output_dir / "tuned-metrics.json"
    summary_path = output_dir / "run-summary.json"
    _write_json(resolved_path, resolved)
    versions = dependency_versions()
    _write_json(versions_path, versions)

    tracking_uri = os.environ.get(
        "MLFLOW_TRACKING_URI", "file:/tmp/qwen-pii-mlruns"
    )
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(
        os.environ.get(
            "MLFLOW_EXPERIMENT_NAME", resolved["experiment_name"]
        )
    )

    train_records = read_jsonl(args.train_jsonl)
    validation_records = read_jsonl(args.validation_jsonl)
    test_records = read_jsonl(args.test_jsonl)
    dataset_manifest = json.loads(
        Path(args.dataset_manifest).read_text(encoding="utf-8")
    )

    run_name = f"{args.environment}-{args.mode}"
    with mlflow.start_run(run_name=run_name):
        _safe_log_params(mlflow, resolved, versions)
        mlflow.log_dict(dataset_manifest, "dataset-manifest.json")
        mlflow.log_artifact(str(resolved_path))
        mlflow.log_artifact(str(versions_path))

        load_started = time.monotonic()
        quantization = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
        )
        tokenizer = AutoTokenizer.from_pretrained(
            resolved["model_id"], use_fast=True
        )
        if tokenizer.pad_token_id is None:
            tokenizer.pad_token = tokenizer.eos_token
        tokenizer.padding_side = "right"
        model = AutoModelForCausalLM.from_pretrained(
            resolved["model_id"],
            quantization_config=quantization,
            device_map="auto",
            torch_dtype=torch.bfloat16,
            low_cpu_mem_usage=True,
        )
        model.config.use_cache = False
        model.config.output_router_logits = True
        model_load_seconds = time.monotonic() - load_started
        torch.cuda.reset_peak_memory_stats()

        baseline_started = time.monotonic()
        baseline_predictions = _predict_records(
            model,
            tokenizer,
            test_records,
            int(training["max_sequence_length"]),
            args.evaluation_batch_size,
        )
        baseline_metrics = evaluate_predictions(
            test_records, baseline_predictions
        )
        baseline_seconds = time.monotonic() - baseline_started
        _write_json(baseline_path, baseline_metrics)

        model = prepare_model_for_kbit_training(
            model, use_gradient_checkpointing=True
        )
        peft_config = LoraConfig(
            r=int(training["lora_rank"]),
            lora_alpha=int(training["lora_alpha"]),
            lora_dropout=float(training["lora_dropout"]),
            bias="none",
            task_type="CAUSAL_LM",
            target_modules=[
                "q_proj",
                "k_proj",
                "v_proj",
                "o_proj",
                "gate_proj",
                "up_proj",
                "down_proj",
            ],
        )
        train_dataset = load_sft_dataset(args.train_jsonl)
        validation_dataset = load_sft_dataset(args.validation_jsonl)
        eval_steps = min(
            int(training["evaluation_interval"]), int(args.steps)
        )
        sft_args = SFTConfig(
            output_dir=str(output_dir / "checkpoints"),
            max_steps=int(args.steps),
            per_device_train_batch_size=int(
                training["per_device_batch_size"]
            ),
            per_device_eval_batch_size=1,
            gradient_accumulation_steps=int(
                training["gradient_accumulation_steps"]
            ),
            learning_rate=float(training["learning_rate"]),
            lr_scheduler_type=training["scheduler"],
            warmup_ratio=float(training["warmup_ratio"]),
            logging_steps=1,
            eval_strategy="steps",
            eval_steps=eval_steps,
            save_strategy="steps",
            save_steps=int(args.steps),
            save_total_limit=1,
            bf16=True,
            gradient_checkpointing=True,
            gradient_checkpointing_kwargs={"use_reentrant": False},
            max_length=int(training["max_sequence_length"]),
            packing=False,
            completion_only_loss=True,
            report_to="none",
            seed=int(resolved["seed"]),
            data_seed=int(resolved["seed"]),
        )
        trainer = SFTTrainer(
            model=model,
            args=sft_args,
            train_dataset=train_dataset,
            eval_dataset=validation_dataset,
            processing_class=tokenizer,
            peft_config=peft_config,
        )
        train_started = time.monotonic()
        train_result = trainer.train()
        training_seconds = time.monotonic() - train_started
        trainer.save_model(str(output_dir))

        trainer.model.config.use_cache = True
        tuned_started = time.monotonic()
        tuned_predictions = _predict_records(
            trainer.model,
            tokenizer,
            test_records,
            int(training["max_sequence_length"]),
            args.evaluation_batch_size,
        )
        tuned_metrics = evaluate_predictions(test_records, tuned_predictions)
        tuned_seconds = time.monotonic() - tuned_started
        _write_json(tuned_path, tuned_metrics)

        peak_gpu_bytes = int(torch.cuda.max_memory_allocated())
        run_summary = {
            "environment": args.environment,
            "mode": args.mode,
            "model_id": resolved["model_id"],
            "dataset_sha256": dataset_manifest["sha256"],
            "model_load_seconds": model_load_seconds,
            "baseline_evaluation_seconds": baseline_seconds,
            "training_seconds": training_seconds,
            "tuned_evaluation_seconds": tuned_seconds,
            "peak_gpu_memory_bytes": peak_gpu_bytes,
            "train_metrics": {
                key: value
                for key, value in train_result.metrics.items()
                if isinstance(value, (int, float))
            },
            "baseline": baseline_metrics,
            "tuned": tuned_metrics,
            "adapter_files": adapter_file_inventory(output_dir),
        }
        _write_json(summary_path, run_summary)

        baseline_flat: dict[str, float] = {}
        tuned_flat: dict[str, float] = {}
        _flatten_numeric("baseline", baseline_metrics, baseline_flat)
        _flatten_numeric("tuned", tuned_metrics, tuned_flat)
        mlflow.log_metrics(baseline_flat)
        mlflow.log_metrics(tuned_flat)
        mlflow.log_metrics(
            {
                "model_load_seconds": model_load_seconds,
                "baseline_evaluation_seconds": baseline_seconds,
                "training_seconds": training_seconds,
                "tuned_evaluation_seconds": tuned_seconds,
                "peak_gpu_memory_bytes": float(peak_gpu_bytes),
            }
        )
        mlflow.log_artifact(str(baseline_path))
        mlflow.log_artifact(str(tuned_path))
        mlflow.log_artifact(str(summary_path))

    del train_records, validation_records, baseline_predictions, tuned_predictions


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--train-jsonl", type=Path, required=True)
    parser.add_argument("--validation-jsonl", type=Path, required=True)
    parser.add_argument("--test-jsonl", type=Path, required=True)
    parser.add_argument("--dataset-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--steps", type=int, required=True)
    parser.add_argument(
        "--environment", choices=("sagemaker", "eks"), required=True
    )
    parser.add_argument("--mode", choices=("smoke", "full"), required=True)
    parser.add_argument("--evaluation-batch-size", type=int, default=4)
    return parser.parse_args()


def main() -> None:
    run_training(parse_args())


if __name__ == "__main__":
    main()
