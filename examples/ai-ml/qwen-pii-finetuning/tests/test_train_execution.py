"""CPU contracts for the real execution entry; no weights or AWS access."""

import importlib
import hashlib
import json
import subprocess
import sys
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from array import array
import math

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def execution():
    return importlib.import_module("src.train_execution")


@pytest.fixture
def metrics():
    return importlib.import_module("src.execution_metrics")


def record(identifier="positive", *, negative=False, language="en"):
    return {
        "id": identifier,
        "language": language,
        "source_text": "Customer Alice." if not negative else "No private information.",
        "target_tsv": "PERSON\tAlice" if not negative else "",
        "entities": [{"type": "PERSON", "original": "Alice"}] if not negative else [],
    }


class Tokenizer:
    """Small reversible native-chat stand-in, including post-EOS whitespace."""

    eos_token_id = 2
    pad_token_id = 0
    eos_token = "<eos>"
    pad_token = "<pad>"
    padding_side = "right"

    def apply_chat_template(self, messages, *, tokenize, add_generation_prompt, **kwargs):
        assert tokenize is False
        text = "SYSTEM:" + messages[0]["content"] + "\nUSER:" + messages[1]["content"]
        text += "\nASSISTANT:"
        if not add_generation_prompt:
            text += messages[2]["content"] + self.eos_token + "\n"
        return text

    def __call__(self, text, *, add_special_tokens=False, **kwargs):
        assert kwargs.get("truncation") is not True
        ids = []
        while text:
            if text.startswith(self.eos_token):
                ids.append(self.eos_token_id)
                text = text[len(self.eos_token):]
            else:
                ids.append(ord(text[0]) + 10)
                text = text[1:]
        return {"input_ids": ids}

    def decode(self, ids, *, skip_special_tokens=False):
        return "".join(
            ("" if skip_special_tokens else self.eos_token) if value == 2
            else chr(value - 10)
            for value in ids
        )


def test_entry_and_help_do_not_import_gpu_or_tracking_dependencies():
    script = (
        "import sys; import src.train_execution as m; "
        "assert not any(n in sys.modules for n in "
        "('torch','transformers','trl','peft','datasets','mlflow')); "
        "m.parse_args(['--help'])"
    )
    result = subprocess.run(
        [sys.executable, "-B", "-c", script],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "--eval-batch-size" in result.stdout


def test_config_defaults_and_cli_step_precedence(execution, tmp_path):
    path = tmp_path / "config.json"
    path.write_text('{"training":{"max_steps":600,"evaluation_interval":100,"learning_rate":0.0001}}')
    common = ["--config", str(path), "--dataset-dir", str(tmp_path / "data"),
              "--output-dir", str(tmp_path / "model")]
    smoke = execution.parse_args([*common, "--mode", "smoke"])
    config = execution.load_config(smoke)
    assert config.max_steps == 4
    assert config.eval_steps == 4
    assert smoke.eval_batch_size == 1
    full = execution.parse_args([*common, "--mode", "full", "--steps", "230"])
    config = execution.load_config(full)
    assert config.max_steps == 230
    assert config.eval_steps == 100
    assert config.learning_rate == 0.0001


@pytest.mark.parametrize("patch", [
    {"unknown": 3}, {"max_steps": True}, {"max_steps": 0},
    {"learning_rate": float("nan")}, {"learning_rate": -1},
    {"warmup_ratio": 2}, {"smoke_generation_examples": 5},
    {"max_new_tokens": 0}, {"evaluation_interval": 0}, {"logging_steps": False},
    {"model_id": "another/model"}, {"max_sequence_length": 2048},
])
def test_invalid_config_fails_before_runtime(execution, tmp_path, patch):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"training": patch}))
    args = execution.parse_args([
        "--mode", "full", "--config", str(path),
        "--dataset-dir", str(tmp_path / "data"), "--output-dir", str(tmp_path / "model"),
    ])
    with pytest.raises(ValueError):
        execution.load_config(args)


def test_support_gate_uses_utc_boundary_and_rejects_wrong_torch(execution):
    execution.require_supported_execution(date(2027, 4, 30))
    with pytest.raises(RuntimeError):
        execution.require_supported_execution(date(2027, 5, 1))
    versions = dict(execution.EXPECTED_VERSIONS)
    execution.validate_versions(versions)
    versions["torch"] = "2.11.0+cu130"
    execution.validate_versions(versions)
    versions["torch"] = "2.8.0"
    with pytest.raises(RuntimeError):
        execution.validate_versions(versions)


@pytest.mark.parametrize("content,finished,success", [
    ("PERSON\tAlice", True, True),
    ("PERSON\tAlice\n", True, True),
    ("", True, True),
    ("", False, False),
    ("PERSON\tAlice", False, False),
    ("Here is the answer:\nPERSON\tAlice", True, False),
    ("PERSON\tAlice\nbroken", True, False),
    ("PERSON\tAlice\nEMAIL\tinvented@example.invalid", True, False),
    ("PERSON\tAlice\textra", True, False),
    ("PERSON\tAlice\n\nPERSON\tAlice", True, False),
    ("person\tAlice", True, False),
    ("<think>reasoning</think>PERSON\tAlice", True, False),
    ("```tsv\nPERSON\tAlice\n```", True, False),
])
def test_strict_parser_is_all_or_none(metrics, content, finished, success):
    assert metrics.strict_parse_success(content, "Customer Alice.", finished) is success


def test_parser_does_not_accept_normalized_numeric_hallucinations(metrics):
    assert metrics.strict_parse_success("PHONE\t01012345678", "Call 010-1234-5678", True) is False


def test_aggregate_keeps_parse_hallucination_truncation_and_subgroups(metrics):
    records = [record(), record("negative", negative=True, language="ko")]
    predictions = [
        {"id": "positive", "content": "PERSON\tAlice\nEMAIL\tmadeup@example.invalid",
         "parse_success": False, "terminated": True},
        {"id": "negative", "content": "", "parse_success": False, "terminated": False},
    ]
    result = metrics.aggregate_predictions(records, predictions)
    assert result["entity"]["tp"] == 0
    assert result["entity"]["fn"] == 1
    assert result["entities"]["hallucinated"] == 1
    assert result["parse"]["success"] == 0
    assert result["generation"]["missing_eos"] == 1
    assert result["subgroups"]["language"]["ko"]["documents"]["total"] == 1
    assert result["subgroups"]["negative"]["documents"]["total"] == 1
    assert "Alice" not in json.dumps(result)
    assert "madeup" not in json.dumps(result)


def test_completion_mask_keeps_response_and_negative_eos(execution):
    rows, report = execution.tokenize_records(
        [record(), record("negative", negative=True)], Tokenizer()
    )
    positive, negative = rows
    assert positive["input_ids"][-1] == 2
    response = [t for t, m in zip(positive["input_ids"], positive["completion_mask"]) if m]
    assert Tokenizer().decode(response) == "PERSON\tAlice<eos>"
    assert negative["completion_mask"] == [0] * (len(negative["input_ids"]) - 1) + [1]
    assert report["negative_examples"] == 1
    assert report["negative_supervised_tokens"] == 1
    assert report["response_tokens"] > 0
    assert report["eos_supervised_examples"] == 2


def test_long_source_or_missing_eos_cannot_be_silently_truncated(execution):
    long = record()
    long["source_text"] += "!" * 1100
    with pytest.raises(ValueError, match="length"):
        execution.tokenize_records([long], Tokenizer())

    class BrokenTemplate(Tokenizer):
        def apply_chat_template(self, *args, **kwargs):
            return super().apply_chat_template(*args, **kwargs).replace("<eos>", "")

    with pytest.raises(ValueError, match="EOS"):
        execution.tokenize_records([record()], BrokenTemplate())


def test_mask_inspection_catches_prompt_and_padding_leaks(execution):
    rows, _ = execution.tokenize_records([record(), record("n", negative=True)], Tokenizer())
    width = max(len(row["input_ids"]) for row in rows)
    labels = [
        [token if mask else -100 for token, mask in zip(row["input_ids"], row["completion_mask"])]
        + [-100] * (width - len(row["input_ids"]))
        for row in rows
    ]
    ids = [row["input_ids"] + [0] * (width - len(row["input_ids"])) for row in rows]
    execution.inspect_collated_labels(rows, {"input_ids": ids, "labels": labels}, 2)
    labels[0][0] = ids[0][0]
    with pytest.raises(RuntimeError, match="mask"):
        execution.inspect_collated_labels(rows, {"input_ids": ids, "labels": labels}, 2)
    labels[0][0] = -100
    labels[1][-1] = 0
    with pytest.raises(RuntimeError, match="padding"):
        execution.inspect_collated_labels(rows, {"input_ids": ids, "labels": labels}, 2)


def test_smoke_selection_preserves_negative_and_language_coverage(execution):
    records = [record(str(i)) for i in range(40)]
    records += [record("ko", language="ko"), record("n", negative=True)]
    selected = execution.select_smoke_records(records, 32)
    assert len(selected) == 32
    assert any(not row["entities"] for row in selected)
    assert {row["language"] for row in selected} == {"en", "ko"}
    assert execution.select_smoke_records(records, 32) == selected


def setup_run(execution, tmp_path, mode, *, steps=None):
    directory = tmp_path / "data"
    directory.mkdir()
    for split, count in [("train", 40), ("validation", 12), ("test", 6)]:
        rows = [record(f"{split}-{i}", negative=(i % 4 == 0), language="ko" if i % 2 else "en")
                for i in range(count)]
        (directory / f"{split}.jsonl").write_text(
            "".join(json.dumps(row) + "\n" for row in rows)
        )
    (directory / "dataset-manifest.json").write_text(json.dumps({
        "generator_version": "execution-1.0.0", "seed": 42,
        "counts": {"train": 40, "validation": 12, "test": 6},
        "sha256": {
            split: hashlib.sha256((directory / f"{split}.jsonl").read_bytes()).hexdigest()
            for split in ("train", "validation", "test")
        },
    }))
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"training": {"checkpoints_dir": str(tmp_path / "checkpoints")}}))
    args = ["--mode", mode, "--config", str(config), "--dataset-dir", str(directory),
            "--output-dir", str(tmp_path / "model")]
    if steps is not None:
        args += ["--steps", str(steps)]
    return execution.parse_args(args)


class Backend:
    """GPU boundary double. Events expose held-out data access ordering."""

    events = []
    fail_training = False

    def __init__(self, config, args):
        self.events.append("runtime")
        self.versions = {"torch": "2.11.0"}
        self.config = config

    def prepare(self, train, validation):
        self.events.append(("prepare", len(train), len(validation)))
        return {
            "trainable_parameters": 13000000, "forward_loss": 1.2,
            "runtime_verified": True, "mask_verified": True,
            "negative_supervision_verified": True, "forward_backward_verified": True,
        }

    def train(self):
        self.events.append("train")
        if self.fail_training:
            raise RuntimeError("training failed")
        return {
            "steps": self.config.max_steps, "best_eval_loss": 1.0,
            "best_model_selected": True, "training_verified": True,
        }

    def save_and_verify(self, path):
        self.events.append("selected-and-reloaded")
        path.mkdir()
        (path / "adapter_config.json").write_text("{}")
        (path / "adapter_model.safetensors").write_bytes(b"adapter")
        return {
            "state_equal": True, "changed_tensors": 1, "max_abs_reload_difference": 0.0,
            "reload_verified": True, "adapter_weights_changed": True,
        }

    def evaluate_pair(self, rows):
        self.events.append(("evaluate", len(rows)))
        return ({"documents": {"total": len(rows)}}, {"documents": {"total": len(rows)}})

    def loss_history(self):
        return [{"step": 1, "loss": 1.2}]


@pytest.mark.parametrize("mode,expected_train,expected_validation,expected_eval", [
    ("smoke", 32, 8, 4), ("full", 40, 12, 6),
])
def test_orchestration_uses_test_once_only_after_selection(
    execution, tmp_path, monkeypatch, mode, expected_train, expected_validation, expected_eval,
):
    args = setup_run(execution, tmp_path, mode)
    events = []
    monkeypatch.setattr(Backend, "events", events)
    original = execution.read_records

    def read(path, **kwargs):
        events.append(("read", Path(path).name))
        if Path(path).name == "test.jsonl":
            assert "selected-and-reloaded" in events
        return original(path, **kwargs)

    monkeypatch.setattr(execution, "read_records", read)
    if mode == "smoke":
        (args.dataset_dir / "test.jsonl").unlink()
    summary = execution.run_training(args, backend_factory=Backend)
    assert ("prepare", expected_train, expected_validation) in events
    assert ("evaluate", expected_eval) in events
    assert events.count(("read", "test.jsonl")) == (1 if mode == "full" else 0)
    assert summary["evaluation_split"] == ("test" if mode == "full" else "validation")
    assert summary["smoke_verified"] is (mode == "smoke")
    assert summary["dataset"]["verified_splits"] == (
        ["train", "validation", "test"] if mode == "full" else ["train", "validation"]
    )
    for name in ["run-summary.json", "dependency-versions.json", "loss-history.json",
                 "baseline-metrics.json", "tuned-metrics.json"]:
        value = json.loads((args.output_dir / name).read_text())
        assert "Alice" not in json.dumps(value)
    assert not (args.output_dir / "checkpoints").exists()


def test_failed_training_never_opens_test(execution, tmp_path, monkeypatch):
    args = setup_run(execution, tmp_path, "full")
    (args.dataset_dir / "test.jsonl").write_text("PRIVATE_MALFORMED_TEST")
    monkeypatch.setattr(Backend, "fail_training", True)
    monkeypatch.setattr(Backend, "events", [])
    with pytest.raises(RuntimeError, match="training failed"):
        execution.run_training(args, backend_factory=Backend)
    assert not any(isinstance(event, tuple) and event[0] == "evaluate" for event in Backend.events)


def test_output_cannot_contain_or_overlap_checkpoints(execution, tmp_path):
    args = setup_run(execution, tmp_path, "full")
    args.config.write_text(json.dumps({"training": {"checkpoints_dir": str(args.output_dir / "checkpoints")}}))
    with pytest.raises(ValueError, match="overlap"):
        execution.run_training(args, backend_factory=Backend)


def test_numeric_logging_drops_raw_text_and_rejects_nonfinite_loss(execution, capsys):
    assert execution.numeric_metrics({"loss": 1.25, "raw": "PRIVATE", "step": 2}) == {
        "loss": 1.25, "step": 2,
    }
    execution.emit_progress({"loss": 1.25, "raw": "PRIVATE"})
    assert json.loads(capsys.readouterr().out) == {"loss": 1.25}
    with pytest.raises(RuntimeError, match="finite"):
        execution.numeric_metrics({"loss": float("nan")})


def test_host_config_produces_validation_selected_checkpoints(execution):
    args = execution.parse_args([
        "--mode", "full", "--config", str(ROOT / "config/execution-20260916.json"),
        "--dataset-dir", "/data", "--output-dir", "/model", "--steps", "230",
    ])
    config = execution.load_config(args)
    settings = execution.sft_arguments(config, 1)
    # Check the actual trainer boundary: 100/200 checkpoints, no test metrics.
    assert settings["max_steps"] == 230
    assert settings["eval_steps"] == settings["save_steps"] == 100
    assert settings["eval_strategy"] == settings["save_strategy"] == "steps"
    assert settings["load_best_model_at_end"] is True
    assert settings["metric_for_best_model"] == "eval_loss"
    assert settings["greater_is_better"] is False
    assert settings["prediction_loss_only"] is True
    assert settings["optim"] == "paged_adamw_8bit"
    assert settings["gradient_accumulation_steps"] == 8
    assert settings["completion_only_loss"] is True
    assert settings["dataset_kwargs"] == {"skip_prepare_dataset": True}
    assert settings["save_only_model"] is True
    assert settings["report_to"] == "none"


def test_manifest_integrity_failure_prevents_runtime(execution, tmp_path, monkeypatch):
    args = setup_run(execution, tmp_path, "smoke")
    with (args.dataset_dir / "train.jsonl").open("a") as stream:
        stream.write("\n")
    monkeypatch.setattr(Backend, "events", [])
    with pytest.raises(ValueError, match="hash"):
        execution.run_training(args, backend_factory=Backend)
    assert Backend.events == []


@pytest.mark.parametrize("mode", ["smoke", "full"])
def test_incomplete_evidence_cannot_certify_or_open_test(execution, tmp_path, mode):
    args = setup_run(execution, tmp_path, mode)
    (args.dataset_dir / "test.jsonl").write_text("MUST_NOT_READ_UNVERIFIED_TEST")

    class Incomplete(Backend):
        def prepare(self, train, validation):
            return {"runtime_verified": True}

    with pytest.raises(RuntimeError, match="incomplete"):
        execution.run_training(args, backend_factory=Incomplete)
    assert json.loads((args.output_dir / "run-summary.json").read_text())["smoke_verified"] is False


class Array:
    def __init__(self, values):
        self.values = values

    def __getitem__(self, key):
        rows, columns = key
        return Array([row[columns] for row in self.values[rows]])

    def detach(self):
        return self

    def cpu(self):
        return self

    def tolist(self):
        return self.values


class GenerationTorch:
    bfloat16 = "bf16"

    @staticmethod
    def tensor(values, *, device):
        assert device == "cuda:0"
        return Array(values)

    @staticmethod
    @contextmanager
    def inference_mode():
        yield

    @staticmethod
    @contextmanager
    def autocast(*args, **kwargs):
        yield


def test_generation_marks_missing_eos_and_checks_entire_output(execution, capsys):
    backend = object.__new__(execution.GPUTrainingBackend)
    backend.tokenizer = Tokenizer()
    backend.torch = GenerationTorch()
    backend.args = SimpleNamespace(eval_batch_size=1)
    backend.config = execution.ExecutionConfig(max_new_tokens=64)
    texts = ["PERSON\tAlice\ninvalid<eos>", "", "PERSON\tAlice<eos>"]

    class Model:
        def generate(self, *, input_ids, attention_mask, **kwargs):
            assert kwargs["eos_token_id"] == 2
            assert kwargs["do_sample"] is False
            completion = backend.tokenizer(texts.pop(0))["input_ids"]
            return Array([input_ids.values[0] + completion])

    backend.model = Model()
    predictions = backend._predict([record("a"), record("b"), record("c")])
    assert [p["parse_success"] for p in predictions] == [False, False, True]
    assert [p["terminated"] for p in predictions] == [True, False, True]
    output = capsys.readouterr().out
    assert "Alice" not in output
    assert json.loads(output.splitlines()[-1])["generation_missing_eos"] == 1


def test_baseline_disables_adapter_and_tuned_restores_it(execution):
    backend = object.__new__(execution.GPUTrainingBackend)
    events = []

    class Model:
        enabled = True

        def eval(self):
            pass

        @contextmanager
        def disable_adapter(self):
            self.enabled = False
            try:
                yield
            finally:
                self.enabled = True

        def set_adapter(self, name):
            assert name == "reload_verified"
            self.enabled = True

        def requires_grad_(self, value):
            assert value is False

    backend.model = Model()

    def predict(rows):
        events.append(backend.model.enabled)
        return [{"id": r["id"], "content": r["target_tsv"] if backend.model.enabled else "",
                 "parse_success": True, "terminated": True} for r in rows]

    backend._predict = predict
    baseline, tuned = backend.evaluate_pair([record()])
    assert events == [False, True]
    assert baseline["entity"]["f1"] == 0
    assert tuned["entity"]["f1"] == 1


class StateTensor:
    """Minimal CPU tensor double for numerical adapter evidence, not GPU math."""

    dtype = "float32"

    def __init__(self, values):
        self.values = values
        self.shape = (len(values),)

    def float(self):
        return self

    def __sub__(self, other):
        return StateTensor([a - b for a, b in zip(self.values, other.values)])

    def abs(self):
        return StateTensor([abs(value) for value in self.values])

    def max(self):
        return SimpleNamespace(item=lambda: max(self.values))

    def contiguous(self):
        return self

    def view(self, dtype):
        return self

    def numpy(self):
        return array("f", self.values)


@pytest.fixture
def state_torch(monkeypatch):
    torch = SimpleNamespace(
        uint8="uint8",
        isfinite=lambda tensor: SimpleNamespace(all=lambda: all(math.isfinite(v) for v in tensor.values)),
        cuda=SimpleNamespace(max_memory_allocated=lambda: 100),
    )
    monkeypatch.setitem(sys.modules, "torch", torch)
    return torch


def test_adapter_evidence_detects_changes_and_exact_reload(execution, state_torch):
    before = {"lora_A": StateTensor([0.0, 1.0]), "lora_B": StateTensor([0.0])}
    after = {"lora_A": StateTensor([0.0, 1.25]), "lora_B": StateTensor([0.0])}
    assert execution._compare_states(before, after) == {
        "changed_tensors": 1, "max_abs_difference": 0.25,
    }
    assert execution._compare_states(after, after)["changed_tensors"] == 0
    assert execution._state_hash(before) != execution._state_hash(after)
    assert execution._state_hash(after) == execution._state_hash(dict(reversed(list(after.items()))))
    with pytest.raises(RuntimeError, match="Non-finite"):
        execution._compare_states(before, {**before, "lora_B": StateTensor([float("nan")])})
    with pytest.raises(RuntimeError, match="keys"):
        execution._compare_states(before, {"lora_A": after["lora_A"]})


def test_trainer_must_restore_best_checkpoint_state(execution, state_torch, monkeypatch):
    backend = object.__new__(execution.GPUTrainingBackend)
    backend.config = execution.ExecutionConfig(max_steps=2)
    backend.torch = state_torch
    backend.model = object()
    backend._history = [{"loss": 1.0}, {"eval_loss": 0.9}]
    backend.trainer = SimpleNamespace(
        train=lambda: SimpleNamespace(metrics={"train_loss": 1.0}),
        state=SimpleNamespace(global_step=2, best_model_checkpoint="/checkpoints/checkpoint-2", best_metric=0.9),
    )
    selected = {"lora_B": StateTensor([0.25])}
    monkeypatch.setattr(execution, "_state_snapshot", lambda model: selected)
    monkeypatch.setitem(sys.modules, "safetensors", SimpleNamespace())
    monkeypatch.setitem(sys.modules, "safetensors.torch", SimpleNamespace(load_file=lambda *a, **kw: selected))
    assert backend.train()["best_checkpoint_state_verified"] is True
    monkeypatch.setitem(sys.modules, "safetensors.torch", SimpleNamespace(
        load_file=lambda *a, **kw: {"lora_B": StateTensor([0.5])},
    ))
    with pytest.raises(RuntimeError, match="restore"):
        backend.train()
    backend.trainer.state.global_step = 1
    with pytest.raises(RuntimeError, match="optimizer steps"):
        backend.train()
