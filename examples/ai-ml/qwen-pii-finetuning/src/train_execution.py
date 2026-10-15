"""GPU QLoRA execution, separate from the preserved historical training entry.

Run from the example root with ``python -m src.train_execution``.
The host's execution JSON has model_id/model_revision/seed and nested runtime,
training, compute, budget objects. Compute and budget belong to the launcher.
Training accepts the host's historical keys plus optional weight_decay (0),
logging_steps (1), smoke_generation_examples (4 or 8), and checkpoints_dir
(/opt/ml/checkpoints). CLI --steps overrides smoke_steps/max_steps.

Only aggregate JSON, tokenizer files and final_adapter are exported. Trainer
checkpoints stay outside output-dir; no test records are read before training,
validation-based model selection and adapter reload verification finish.
"""

import argparse
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

from src.dataset import completion_messages, prompt_messages
from src.execution_metrics import aggregate_predictions, strict_parse_success


MODEL_ID = "Qwen/Qwen3-30B-A3B-Instruct-2507"
MODEL_REVISION = "0d7cf23991f47feeb3a57ecb4c9cee8ea4a17bfe"
PATCH_END = date(2027, 4, 30)
MAX_SEQUENCE_LENGTH = 1024
TARGET_MODULES = ("q_proj", "k_proj", "v_proj", "o_proj")
EXPECTED_VERSIONS = {
    "torch": "2.11.0", "transformers": "4.57.6", "peft": "0.17.1",
    "trl": "0.24.0", "accelerate": "1.10.1", "bitsandbytes": "0.50.2",
    "datasets": "3.6.0",
}
FIXED_TRAINING = {
    "quantization": "nf4", "double_quant": True, "compute_dtype": "bfloat16",
    "target_modules": list(TARGET_MODULES), "lora_rank": 16, "lora_alpha": 32,
    "max_sequence_length": MAX_SEQUENCE_LENGTH, "per_device_batch_size": 1,
    "gradient_accumulation_steps": 8,
}


@dataclass(frozen=True)
class ExecutionConfig:
    seed: int = 42
    max_steps: int = 600
    eval_steps: int = 100
    learning_rate: float = 0.0002
    warmup_ratio: float = 0.03
    weight_decay: float = 0.0
    lora_dropout: float = 0.05
    lr_scheduler_type: str = "cosine"
    logging_steps: int = 1
    max_new_tokens: int = 384
    smoke_generation_examples: int = 4
    checkpoints_dir: str = "/opt/ml/checkpoints"


def _integer(value, field, minimum=1):
    if type(value) is not int or value < minimum:
        raise ValueError(f"Invalid integer config field: {field}")
    return value


def _number(value, field, minimum=0.0, maximum=None):
    if type(value) not in (int, float) or not math.isfinite(value) or value < minimum:
        raise ValueError(f"Invalid numeric config field: {field}")
    if maximum is not None and value > maximum:
        raise ValueError(f"Numeric config field exceeds limit: {field}")
    return value


def load_config(args) -> ExecutionConfig:
    try:
        raw = json.loads(Path(args.config).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise ValueError("Cannot read execution JSON configuration") from None
    allowed = {"model_id", "model_revision", "seed", "runtime", "training", "compute", "budget"}
    if not isinstance(raw, dict) or raw.keys() - allowed:
        raise ValueError("Unknown execution configuration fields")
    if raw.get("model_id", MODEL_ID) != MODEL_ID or raw.get("model_revision", MODEL_REVISION) != MODEL_REVISION:
        raise ValueError("Execution requires the pinned model and revision")
    training = raw.get("training", {})
    adjustable = {
        "learning_rate", "scheduler", "warmup_ratio", "weight_decay", "lora_dropout",
        "smoke_steps", "max_steps", "evaluation_interval", "logging_steps",
        "max_new_tokens", "smoke_generation_examples", "checkpoints_dir",
    }
    if not isinstance(training, dict) or training.keys() - FIXED_TRAINING.keys() - adjustable:
        raise ValueError("Unknown training configuration fields")
    for key, value in FIXED_TRAINING.items():
        candidate = training.get(key, value)
        if type(candidate) is not type(value) or candidate != value:
            raise ValueError(f"Protected training configuration field: {key}")
    runtime = raw.get("runtime", {})
    if not isinstance(runtime, dict) or runtime.keys() - {
        "image_uri", "image_tag", "patch_end", "torch", "cuda", "python",
    }:
        raise ValueError("Unknown runtime configuration fields")
    for key, value in {"patch_end": "2027-04-30", "torch": "2.11.0", "cuda": "13.0", "python": "3.12"}.items():
        if runtime.get(key, value) != value:
            raise ValueError(f"Runtime contract mismatch: {key}")
    # Validate both step limits even when the CLI overrides the chosen one.
    full_steps = _integer(training.get("max_steps", 600), "max_steps")
    smoke_steps = _integer(training.get("smoke_steps", 4), "smoke_steps")
    steps = _integer(
        args.steps if args.steps is not None else smoke_steps if args.mode == "smoke" else full_steps,
        "steps",
    )
    eval_steps = min(steps, _integer(training.get("evaluation_interval", 100), "evaluation_interval"))
    scheduler = training.get("scheduler", "cosine")
    if scheduler not in ("cosine", "linear", "constant"):
        raise ValueError("Unsupported scheduler")
    generation_count = _integer(training.get("smoke_generation_examples", 4), "smoke_generation_examples")
    if generation_count not in (4, 8):
        raise ValueError("Smoke generation requires 4 or 8 examples")
    checkpoints_dir = training.get("checkpoints_dir", "/opt/ml/checkpoints")
    if not isinstance(checkpoints_dir, str) or not Path(checkpoints_dir).is_absolute():
        raise ValueError("checkpoints_dir must be an absolute local directory")
    return ExecutionConfig(
        seed=_integer(raw.get("seed", 42), "seed", 0), max_steps=steps, eval_steps=eval_steps,
        learning_rate=_number(training.get("learning_rate", 0.0002), "learning_rate", 1e-12),
        warmup_ratio=_number(training.get("warmup_ratio", 0.03), "warmup_ratio", 0, 1),
        weight_decay=_number(training.get("weight_decay", 0.0), "weight_decay"),
        lora_dropout=_number(training.get("lora_dropout", 0.05), "lora_dropout", 0, 0.5),
        lr_scheduler_type=scheduler,
        logging_steps=_integer(training.get("logging_steps", 1), "logging_steps"),
        max_new_tokens=_integer(training.get("max_new_tokens", 384), "max_new_tokens"),
        smoke_generation_examples=generation_count, checkpoints_dir=checkpoints_dir,
    )


def require_supported_execution(today=None):
    """Temporary UTC contract until the host supplies the shared runtime gate."""
    if (today or datetime.now(timezone.utc).date()) > PATCH_END:
        raise RuntimeError("Execution runtime support ended on 2027-04-30")


def validate_versions(versions):
    for name, expected in EXPECTED_VERSIONS.items():
        if versions.get(name, "").split("+", 1)[0] != expected:
            raise RuntimeError(f"Execution dependency version mismatch: {name}")


def numeric_metrics(values):
    result = {}
    for key, value in values.items():
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if not math.isfinite(value):
                raise RuntimeError("Non-finite numeric training/evaluation metric")
            result[key] = value
    return result


def emit_progress(values):
    print(json.dumps(numeric_metrics(values), sort_keys=True, allow_nan=False), flush=True)


def _write_json(path, value):
    payload = json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    temporary = Path(path).with_suffix(".json.tmp")
    temporary.write_text(payload, encoding="utf-8")
    temporary.replace(path)


def read_manifest(directory, seed):
    try:
        raw = json.loads((Path(directory) / "dataset-manifest.json").read_text(encoding="utf-8"))
        if raw["generator_version"] != "execution-1.0.0" or raw["seed"] != seed:
            raise ValueError
        counts, hashes = raw["counts"], raw["sha256"]
        for split in ("train", "validation", "test"):
            _integer(counts[split], "split count")
            digest = hashes[split]
            if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                raise ValueError
    except (OSError, ValueError, KeyError, TypeError):
        raise ValueError("Invalid execution dataset manifest") from None
    # Do not export arbitrary fields from the input manifest.
    return {
        "generator_version": raw["generator_version"], "seed": seed,
        "counts": {split: counts[split] for split in ("train", "validation", "test")},
        "sha256": {split: hashes[split] for split in ("train", "validation", "test")},
        "verified_splits": [],
    }


def read_records(path, *, expected_sha256=None, expected_count=None):
    """Read only the requested split and keep errors free of document contents."""
    try:
        payload = Path(path).read_bytes()
    except OSError:
        raise ValueError("Cannot read dataset split JSONL") from None
    if expected_sha256 and hashlib.sha256(payload).hexdigest() != expected_sha256:
        raise ValueError("Dataset split hash mismatch")
    try:
        rows = [json.loads(line) for line in payload.decode("utf-8").splitlines() if line.strip()]
    except ValueError:
        raise ValueError("Cannot read dataset split JSONL") from None
    if expected_count is not None and len(rows) != expected_count:
        raise ValueError("Dataset split count mismatch")
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or not all(
            isinstance(row.get(key), str) for key in ("id", "source_text", "target_tsv", "language")
        ):
            raise ValueError("Invalid dataset record structure")
        if row["id"] in seen or row["language"] not in ("ko", "en") or not isinstance(row.get("entities"), list):
            raise ValueError("Invalid dataset identity/language/entities")
        seen.add(row["id"])
        if not strict_parse_success(row["target_tsv"], row["source_text"], True):
            raise ValueError("Invalid dataset gold TSV")
        try:
            gold = "\n".join(f"{e['type']}\t{e['original']}" for e in row["entities"])
        except (KeyError, TypeError):
            raise ValueError("Invalid dataset entity structure") from None
        if gold != row["target_tsv"]:
            raise ValueError("Dataset gold entities disagree with completion")
    if not rows:
        raise ValueError("Dataset split must not be empty")
    return rows


def select_smoke_records(records, count):
    if len(records) < count:
        raise ValueError("Insufficient examples for smoke subset")
    # Deterministic coverage, not model-score-driven selection. No test access.
    first = {}
    for index, row in enumerate(records):
        first.setdefault((row["language"], bool(row["entities"])), index)
    selected = set(list(first.values())[:count])
    for index in range(len(records)):
        if len(selected) == count:
            break
        selected.add(index)
    return [records[index] for index in sorted(selected)]


def prompt_token_ids(tokenizer, record):
    text = tokenizer.apply_chat_template(
        prompt_messages(record), tokenize=False,
        add_generation_prompt=True, enable_thinking=False,
    )
    ids = tokenizer(text, add_special_tokens=False, truncation=False)["input_ids"]
    if not ids or len(ids) > MAX_SEQUENCE_LENGTH:
        raise ValueError("Source prompt exceeds sequence length; truncation prohibited")
    return text, ids


def tokenize_records(records, tokenizer):
    rows = []
    report = {
        "examples": len(records), "prompt_tokens": 0, "response_tokens": 0,
        "supervised_tokens": 0, "negative_examples": 0,
        "negative_supervised_tokens": 0, "eos_supervised_examples": 0,
        "max_sequence_length_observed": 0,
    }
    eos = tokenizer.eos_token_id
    if eos is None:
        raise ValueError("Tokenizer must define EOS")
    for record in records:
        prompt_text, prompt_ids = prompt_token_ids(tokenizer, record)
        full_text = tokenizer.apply_chat_template(
            prompt_messages(record) + completion_messages(record),
            tokenize=False, add_generation_prompt=False, enable_thinking=False,
        )
        ids = tokenizer(full_text, add_special_tokens=False, truncation=False)["input_ids"]
        if not full_text.startswith(prompt_text) or ids[:len(prompt_ids)] != prompt_ids:
            raise ValueError("Native chat template has an unstable prompt/completion boundary")
        suffix = ids[len(prompt_ids):]
        if eos not in suffix:
            raise ValueError("Completion has no supervised EOS")
        eos_index = len(prompt_ids) + suffix.index(eos)
        if tokenizer.decode(ids[eos_index + 1:], skip_special_tokens=False).strip():
            raise ValueError("Unexpected content after completion EOS")
        # Drop only the chat template's whitespace after EOS, never source tokens.
        ids = ids[:eos_index + 1]
        if len(ids) > MAX_SEQUENCE_LENGTH:
            raise ValueError("Training example exceeds sequence length; truncation prohibited")
        response_tokens = len(ids) - len(prompt_ids) - 1
        if record["target_tsv"] and response_tokens < 1:
            raise ValueError("Nonempty response has no supervised content tokens")
        mask = [0] * len(prompt_ids) + [1] * (response_tokens + 1)
        rows.append({"input_ids": ids, "completion_mask": mask})
        report["prompt_tokens"] += len(prompt_ids)
        report["response_tokens"] += response_tokens
        report["supervised_tokens"] += response_tokens + 1
        report["eos_supervised_examples"] += 1
        report["max_sequence_length_observed"] = max(report["max_sequence_length_observed"], len(ids))
        if not record["entities"]:
            report["negative_examples"] += 1
            report["negative_supervised_tokens"] += response_tokens + 1
    return rows, report


def inspect_collated_labels(rows, batch, eos):
    """Inspect actual TRL collator labels, including padding and negative EOS."""
    labels = batch["labels"].tolist() if hasattr(batch["labels"], "tolist") else batch["labels"]
    inputs = batch["input_ids"].tolist() if hasattr(batch["input_ids"], "tolist") else batch["input_ids"]
    if len(labels) != len(rows) or len(inputs) != len(rows):
        raise RuntimeError("Collator changed example count")
    for row, actual, tokens in zip(rows, labels, inputs):
        ids, mask = row["input_ids"], row["completion_mask"]
        expected = [token if included else -100 for token, included in zip(ids, mask)]
        if tokens[:len(ids)] != ids or actual[:len(ids)] != expected:
            raise RuntimeError("Completion/prompt mask mismatch in actual collator")
        if any(label != -100 for label in actual[len(ids):]):
            raise RuntimeError("Collator padding is supervised")
        if ids[-1] != eos or actual[len(ids) - 1] != eos or not any(m == 0 for m in mask):
            raise RuntimeError("Missing supervised EOS or prompt mask")


def sft_arguments(config, eval_batch_size):
    return {
        "output_dir": config.checkpoints_dir, "max_steps": config.max_steps,
        "per_device_train_batch_size": 1, "per_device_eval_batch_size": eval_batch_size,
        "gradient_accumulation_steps": 8, "learning_rate": config.learning_rate,
        "lr_scheduler_type": config.lr_scheduler_type, "warmup_ratio": config.warmup_ratio,
        "weight_decay": config.weight_decay, "optim": "paged_adamw_8bit",
        "logging_steps": min(config.logging_steps, config.max_steps), "logging_nan_inf_filter": False,
        "eval_strategy": "steps", "eval_steps": config.eval_steps,
        "save_strategy": "steps", "save_steps": config.eval_steps, "save_total_limit": 2,
        "load_best_model_at_end": True, "metric_for_best_model": "eval_loss",
        "greater_is_better": False, "prediction_loss_only": True,
        "bf16": True, "fp16": False, "tf32": True,
        "gradient_checkpointing": True, "gradient_checkpointing_kwargs": {"use_reentrant": False},
        "max_length": MAX_SEQUENCE_LENGTH, "packing": False, "padding_free": False,
        "completion_only_loss": True, "dataset_kwargs": {"skip_prepare_dataset": True},
        "save_safetensors": True, "save_only_model": True, "report_to": "none",
        "disable_tqdm": True, "seed": config.seed, "data_seed": config.seed,
        "dataloader_num_workers": 0,
    }


def _state_snapshot(model, adapter_name="default"):
    from peft import get_peft_model_state_dict

    return {
        key: value.detach().cpu().clone()
        for key, value in get_peft_model_state_dict(model, adapter_name=adapter_name).items()
    }


def _state_hash(state):
    import torch

    digest = hashlib.sha256()
    for key in sorted(state):
        value = state[key].contiguous()
        digest.update(key.encode())
        digest.update(str(tuple(value.shape)).encode())
        digest.update(str(value.dtype).encode())
        # LoRA is saved as floating point; uint8 also supports BF16 numpy bytes.
        digest.update(value.view(torch.uint8).numpy().tobytes())
    return digest.hexdigest()


def _compare_states(before, after):
    import torch

    if not before or before.keys() != after.keys():
        raise RuntimeError("Adapter state keys differ")
    changed, difference = 0, 0.0
    for key, value in before.items():
        other = after[key]
        if value.shape != other.shape or value.dtype != other.dtype:
            raise RuntimeError("Adapter tensor shape/dtype differs")
        if not torch.isfinite(value).all() or not torch.isfinite(other).all():
            raise RuntimeError("Non-finite adapter tensor")
        delta = float((value.float() - other.float()).abs().max().item())
        changed += int(delta != 0)
        difference = max(difference, delta)
    return {"changed_tensors": changed, "max_abs_difference": difference}


class GPUTrainingBackend:
    """All GPU imports and effects are behind the execution boundary."""

    def __init__(self, config, args):
        require_supported_execution()
        self.config, self.args = config, args
        self.versions = {name: importlib.metadata.version(name) for name in EXPECTED_VERSIONS}
        validate_versions(self.versions)
        import torch

        self.torch = torch
        if torch.__version__.split("+", 1)[0] != EXPECTED_VERSIONS["torch"]:
            raise RuntimeError("Imported torch does not match execution runtime")
        if sys.version_info[:2] != (3, 12) or torch.version.cuda != "13.0":
            raise RuntimeError("Execution requires Python 3.12 and CUDA 13.0")
        release = platform.freedesktop_os_release()
        if release.get("ID") != "amzn" or release.get("VERSION_ID") != "2023":
            raise RuntimeError("Execution requires Amazon Linux 2023")
        if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
            raise RuntimeError("Execution requires exactly one visible CUDA GPU")
        if int(os.environ.get("WORLD_SIZE", "1")) != 1:
            raise RuntimeError("Execution requires a single training process")
        torch.cuda.set_device(0)
        if not torch.cuda.is_bf16_supported(including_emulation=False):
            raise RuntimeError("Execution requires native GPU BF16 support")
        torch.cuda.reset_peak_memory_stats()
        self.versions.update({"python": platform.python_version(), "cuda": torch.version.cuda})
        self._history = []

    def prepare(self, train, validation):
        from datasets import Dataset
        from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, set_seed
        from transformers import TrainerCallback
        from trl import SFTConfig, SFTTrainer

        torch = self.torch
        set_seed(self.config.seed)
        self.tokenizer = AutoTokenizer.from_pretrained(
            MODEL_ID, revision=MODEL_REVISION, use_fast=True, trust_remote_code=False,
        )
        if self.tokenizer.pad_token_id is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        self.tokenizer.padding_side = "right"
        train_rows, train_masks = tokenize_records(train, self.tokenizer)
        validation_rows, validation_masks = tokenize_records(validation, self.tokenizer)
        if not train_masks["negative_examples"] or not train_masks["response_tokens"]:
            raise ValueError("Training must include a negative example and a nonempty response")
        self.model = AutoModelForCausalLM.from_pretrained(
            MODEL_ID, revision=MODEL_REVISION, trust_remote_code=False,
            quantization_config=BitsAndBytesConfig(
                load_in_4bit=True, bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=torch.bfloat16,
                llm_int8_enable_fp32_cpu_offload=False,
            ),
            device_map={"": 0}, torch_dtype=torch.bfloat16,
            attn_implementation="sdpa", low_cpu_mem_usage=True,
        )
        if not getattr(self.model, "is_loaded_in_4bit", False):
            raise RuntimeError("Model is not loaded in 4-bit mode")
        if any(p.device.type != "cuda" or p.device.index != 0 for p in self.model.parameters()):
            raise RuntimeError("Base model is offloaded or not entirely on CUDA device 0")
        self.model.config.use_cache = False
        self.model.config.output_router_logits = False
        self.model = prepare_model_for_kbit_training(
            self.model, use_gradient_checkpointing=True,
            gradient_checkpointing_kwargs={"use_reentrant": False},
        )
        self.model = get_peft_model(self.model, LoraConfig(
            r=16, lora_alpha=32, lora_dropout=self.config.lora_dropout,
            bias="none", task_type="CAUSAL_LM", target_modules=list(TARGET_MODULES),
            revision=MODEL_REVISION,
        ))
        trainable = [(name, value) for name, value in self.model.named_parameters() if value.requires_grad]
        if not trainable or any(
            not (".lora_A." in name or ".lora_B." in name)
            or not any(f".{target}." in name for target in TARGET_MODULES)
            for name, _ in trainable
        ):
            raise RuntimeError("Unexpected trainable base parameters")
        count = sum(value.numel() for _, value in trainable)
        if not 10_000_000 <= count <= 16_000_000:
            raise RuntimeError("Attention-only adapter parameter count is outside expected range")
        self.initial_state = _state_snapshot(self.model)
        history = self._history
        history_path = self.args.output_dir / "loss-history.json"

        class NumericProgress(TrainerCallback):
            def on_log(self, args, state, control, logs=None, **kwargs):
                safe = numeric_metrics(logs or {})
                safe["step"] = state.global_step
                history.append(safe)
                _write_json(history_path, history)
                emit_progress(safe)

        self.trainer = SFTTrainer(
            model=self.model, args=SFTConfig(**sft_arguments(self.config, self.args.eval_batch_size)),
            train_dataset=Dataset.from_list(train_rows), eval_dataset=Dataset.from_list(validation_rows),
            processing_class=self.tokenizer, callbacks=[NumericProgress()],
        )
        self.model = self.trainer.model
        # TRL 0.24.0's PEFT preparation re-enables checkpointing without kwargs.
        # Restore the non-reentrant mode before probing frozen-base gradients.
        self.model.gradient_checkpointing_enable(
            gradient_checkpointing_kwargs={"use_reentrant": False}
        )
        # Inspect the actual trainer datasets and its real collator, not a parallel
        # label implementation. Checking all rows costs only CPU token collation.
        for rows, dataset in ((train_rows, self.trainer.train_dataset), (validation_rows, self.trainer.eval_dataset)):
            if len(rows) != len(dataset):
                raise RuntimeError("Trainer changed dataset size")
            for start in range(0, len(rows), 8):
                examples = [dataset[index] for index in range(start, min(start + 8, len(rows)))]
                batch = self.trainer.data_collator(examples)
                inspect_collated_labels(rows[start:start + 8], batch, self.tokenizer.eos_token_id)
        # A real finite forward/backward on both positive and negative examples.
        probes = [next(i for i, r in enumerate(train) if r["entities"]),
                  next(i for i, r in enumerate(train) if not r["entities"])]
        losses, gradient_l1 = [], 0.0
        self.model.train()
        for index in probes:
            self.model.zero_grad(set_to_none=True)
            batch = {key: value.to("cuda:0") for key, value in
                     self.trainer.data_collator([train_rows[index]]).items()}
            with torch.autocast("cuda", dtype=torch.bfloat16):
                loss = self.model(**batch, use_cache=False).loss
            if not torch.isfinite(loss).item():
                raise RuntimeError("Non-finite forward loss")
            loss.backward()
            for name, value in self.model.named_parameters():
                if value.grad is not None:
                    if not value.requires_grad or not torch.isfinite(value.grad).all().item():
                        raise RuntimeError("Invalid/non-finite backward gradient")
                    gradient_l1 += float(value.grad.detach().float().abs().sum().item())
            losses.append(float(loss.detach().item()))
            del batch, loss
        self.model.zero_grad(set_to_none=True)
        if not math.isfinite(gradient_l1) or gradient_l1 <= 0:
            raise RuntimeError("Backward produced no finite nonzero adapter gradient")
        # Reset RNG so diagnostic dropout does not perturb the planned training.
        set_seed(self.config.seed)
        return {
            "runtime_verified": True, "mask_verified": True, "negative_supervision_verified": True,
            "forward_backward_verified": True, "forward_loss": losses[0],
            "negative_forward_loss": losses[1], "gradient_l1": gradient_l1,
            "trainable_parameters": count, "train_masks": train_masks,
            "validation_masks": validation_masks,
            "gpu_memory_bytes": torch.cuda.get_device_properties(0).total_memory,
        }

    def train(self):
        started = time.monotonic()
        result = self.trainer.train()
        state = self.trainer.state
        if state.global_step != self.config.max_steps:
            raise RuntimeError("Training ended before the requested optimizer steps")
        if not state.best_model_checkpoint or state.best_metric is None or not math.isfinite(state.best_metric):
            raise RuntimeError("No finite validation-selected checkpoint")
        if not any("loss" in row for row in self._history) or not any("eval_loss" in row for row in self._history):
            raise RuntimeError("Missing finite training or validation loss evidence")
        from safetensors.torch import load_file

        selected = _state_snapshot(self.model)
        best = load_file(str(Path(state.best_model_checkpoint) / "adapter_model.safetensors"), device="cpu")
        if _compare_states(best, selected)["changed_tensors"]:
            raise RuntimeError("Trainer did not restore the validation-selected adapter")
        del selected, best
        # Trainer has loaded best_model_checkpoint here; no test has been opened.
        return {
            "training_verified": True, "best_model_selected": True,
            "best_checkpoint_state_verified": True,
            "steps": state.global_step, "best_eval_loss": float(state.best_metric),
            "best_checkpoint": Path(state.best_model_checkpoint).name,
            "training_seconds": time.monotonic() - started,
            "train_metrics": numeric_metrics(result.metrics),
            "peak_gpu_memory_bytes": int(self.torch.cuda.max_memory_allocated()),
        }

    def save_and_verify(self, path):
        from safetensors.torch import load_file
        from transformers import AutoTokenizer

        selected = _state_snapshot(self.model)
        change = _compare_states(self.initial_state, selected)
        if change["changed_tensors"] == 0:
            raise RuntimeError("Selected adapter weights did not change during training")
        initial_hash, selected_hash = _state_hash(self.initial_state), _state_hash(selected)
        del self.initial_state
        path.mkdir(parents=True, exist_ok=False)
        self.model.save_pretrained(path, safe_serialization=True, save_embedding_layers=False)
        self.tokenizer.save_pretrained(path)
        disk = load_file(str(path / "adapter_model.safetensors"), device="cpu")
        if _compare_states(selected, disk)["changed_tensors"]:
            raise RuntimeError("Saved adapter state differs from selected model")
        # Reload a second adapter on the SAME quantized base to avoid a second
        # 30B model allocation. This tests PEFT's public saved-artifact load path.
        self.model.load_adapter(
            path, adapter_name="reload_verified", is_trainable=False,
            torch_device="cuda:0", ephemeral_gpu_offload=False, local_files_only=True,
        )
        reloaded = _state_snapshot(self.model, "reload_verified")
        reload_delta = _compare_states(selected, reloaded)
        if reload_delta["changed_tensors"] or _state_hash(reloaded) != selected_hash:
            raise RuntimeError("Reloaded adapter state differs from selected model")
        reloaded_tokenizer = AutoTokenizer.from_pretrained(path, local_files_only=True)
        if (reloaded_tokenizer.eos_token_id, reloaded_tokenizer.pad_token_id) != (
            self.tokenizer.eos_token_id, self.tokenizer.pad_token_id,
        ):
            raise RuntimeError("Reloaded tokenizer changed EOS/padding tokens")
        probe = {"source_text": "A public document.", "target_tsv": ""}
        if prompt_token_ids(reloaded_tokenizer, probe)[1] != prompt_token_ids(self.tokenizer, probe)[1]:
            raise RuntimeError("Reloaded tokenizer changed prompt tokenization")
        self.tokenizer = reloaded_tokenizer
        self.model.set_adapter("reload_verified")
        self.model.delete_adapter("default")
        self.model.requires_grad_(False)
        if any(p.device.type != "cuda" or p.device.index != 0 for p in self.model.parameters()):
            raise RuntimeError("Reloaded model/adapter is offloaded from CUDA device 0")
        self.model.gradient_checkpointing_disable()
        self.model.config.use_cache = True
        self.model.eval()
        files = []
        for name in ("adapter_config.json", "adapter_model.safetensors"):
            artifact = path / name
            if not artifact.is_file() or artifact.is_symlink():
                raise RuntimeError("Missing regular adapter artifact")
            files.append({
                "name": name, "bytes": artifact.stat().st_size,
                "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
            })
        del selected, disk, reloaded
        return {
            "adapter_weights_changed": True, "changed_tensors": change["changed_tensors"],
            "max_abs_training_difference": change["max_abs_difference"],
            "initial_state_sha256": initial_hash, "selected_state_sha256": selected_hash,
            "reloaded_state_sha256": selected_hash, "reload_verified": True, "state_equal": True,
            "max_abs_reload_difference": reload_delta["max_abs_difference"], "files": files,
        }

    def _predict(self, records):
        predictions = []
        tokenizer, torch = self.tokenizer, self.torch
        eos, pad = tokenizer.eos_token_id, tokenizer.pad_token_id
        # All prompts are validated before any inference, with no truncation.
        prompts = [prompt_token_ids(tokenizer, row)[1] for row in records]
        for start in range(0, len(records), self.args.eval_batch_size):
            group = prompts[start:start + self.args.eval_batch_size]
            width = max(map(len, group))
            ids = torch.tensor([[pad] * (width - len(p)) + p for p in group], device="cuda:0")
            attention = torch.tensor([[0] * (width - len(p)) + [1] * len(p) for p in group], device="cuda:0")
            with torch.inference_mode(), torch.autocast("cuda", dtype=torch.bfloat16):
                output = self.model.generate(
                    input_ids=ids, attention_mask=attention, do_sample=False,
                    max_new_tokens=self.config.max_new_tokens, pad_token_id=pad, eos_token_id=eos,
                    use_cache=True, return_dict_in_generate=False,
                )
            generated = output[:, width:].detach().cpu().tolist()
            if len(generated) != len(group):
                raise RuntimeError("Generation returned an unexpected example count")
            for row, tokens in zip(records[start:start + len(group)], generated):
                terminated = eos in tokens
                content_tokens = tokens[:tokens.index(eos)] if terminated else tokens
                # Keep unexpected special tokens visible to the strict parser.
                content = tokenizer.decode(content_tokens, skip_special_tokens=False)
                predictions.append({
                    "id": row["id"], "content": content, "terminated": terminated,
                    "parse_success": strict_parse_success(content, row["source_text"], terminated),
                })
            del output, ids, attention
            emit_progress({"generation_examples": len(predictions),
                           "generation_missing_eos": sum(not p["terminated"] for p in predictions)})
        return predictions

    def evaluate_pair(self, records):
        self.model.eval()
        with self.model.disable_adapter():
            predictions = self._predict(records)
            baseline = aggregate_predictions(records, predictions)
        del predictions
        # disable_adapter restores the active adapter on exit, even on exceptions.
        self.model.set_adapter("reload_verified")
        self.model.requires_grad_(False)
        predictions = self._predict(records)
        tuned = aggregate_predictions(records, predictions)
        del predictions
        return baseline, tuned

    def loss_history(self):
        return list(self._history)


def _prepare_output_paths(args, config):
    output, checkpoints, dataset = (
        args.output_dir.resolve(), Path(config.checkpoints_dir).resolve(), args.dataset_dir.resolve(),
    )
    for left, right in ((output, checkpoints), (output, dataset), (checkpoints, dataset)):
        if left == right or left in right.parents or right in left.parents:
            raise ValueError("Dataset, output and checkpoint directories must not overlap")
    for path in (args.output_dir, Path(config.checkpoints_dir)):
        if path.is_symlink() or (path.exists() and (not path.is_dir() or any(path.iterdir()))):
            raise ValueError("Execution output/checkpoint directory must be empty and not a symlink")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    Path(config.checkpoints_dir).mkdir(parents=True, exist_ok=True)


def run_training(args, *, backend_factory=GPUTrainingBackend):
    config = load_config(args)
    require_supported_execution()
    _prepare_output_paths(args, config)
    started = time.monotonic()
    manifest = read_manifest(args.dataset_dir, config.seed)

    def split_records(split):
        rows = read_records(
            args.dataset_dir / f"{split}.jsonl",
            expected_sha256=manifest["sha256"][split], expected_count=manifest["counts"][split],
        )
        manifest["verified_splits"].append(split)
        return rows

    train = split_records("train")
    validation = split_records("validation")
    if args.mode == "smoke":
        train = select_smoke_records(train, 32)
        validation = select_smoke_records(validation, 8)
    backend = backend_factory(config, args)
    _write_json(args.output_dir / "dependency-versions.json", backend.versions)
    _write_json(args.output_dir / "run-summary.json", {"status": "running", "mode": args.mode, "smoke_verified": False})
    preparation = backend.prepare(train, validation)
    training = backend.train()
    adapter = backend.save_and_verify(args.output_dir / "final_adapter")
    verified = all((
        preparation.get("runtime_verified") is True,
        preparation.get("mask_verified") is True,
        preparation.get("negative_supervision_verified") is True,
        preparation.get("forward_backward_verified") is True,
        training.get("training_verified") is True,
        training.get("best_model_selected") is True,
        adapter.get("adapter_weights_changed") is True,
        adapter.get("reload_verified") is True,
    ))
    if not verified:
        raise RuntimeError("Execution verification evidence is incomplete")
    # This is the only held-out-test read site, after checked selection evidence.
    evaluation = (
        split_records("test") if args.mode == "full"
        else select_smoke_records(validation, config.smoke_generation_examples)
    )
    baseline, tuned = backend.evaluate_pair(evaluation)
    if baseline["documents"]["total"] != len(evaluation) or tuned["documents"]["total"] != len(evaluation):
        raise RuntimeError("Incomplete paired generation evaluation")
    for name, result in (("baseline-metrics.json", baseline), ("tuned-metrics.json", tuned)):
        _write_json(args.output_dir / name, result)
    _write_json(args.output_dir / "loss-history.json", backend.loss_history())
    summary = {
        "status": "completed", "mode": args.mode, "smoke_verified": args.mode == "smoke",
        "model_id": MODEL_ID, "model_revision": MODEL_REVISION, "seed": config.seed,
        "evaluation_split": "test" if args.mode == "full" else "validation",
        "train_examples": len(train), "validation_examples": len(validation),
        "generation_examples_per_model": len(evaluation), "generation_verified": True,
        "dataset": manifest,
        "preparation": preparation, "training": training, "adapter": adapter,
        "baseline": baseline, "tuned": tuned, "elapsed_seconds": time.monotonic() - started,
    }
    _write_json(args.output_dir / "run-summary.json", summary)
    emit_progress({"completed": 1, "smoke_verified": int(args.mode == "smoke"),
                   "elapsed_seconds": summary["elapsed_seconds"]})
    return summary


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("smoke", "full"), required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--steps", type=int)
    parser.add_argument("--eval-batch-size", type=int, default=1)
    args = parser.parse_args(argv)
    if args.steps is not None and args.steps < 1:
        parser.error("--steps must be positive")
    if args.eval_batch_size < 1:
        parser.error("--eval-batch-size must be positive")
    return args


def main():
    args = parse_args()
    try:
        run_training(args)
    except Exception as error:
        # Exception messages/tracebacks from tokenizers and data libraries can
        # contain document text. Only emit the error class, never its contents.
        print(json.dumps({"status": "failed", "error_type": type(error).__name__,
                          "smoke_verified": False}), file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
