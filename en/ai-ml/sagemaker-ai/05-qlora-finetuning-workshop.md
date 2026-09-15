# Workshop: QLoRA fine-tuning for PII extraction

> **Last Updated**: September 15, 2026

Primary sources were checked on September 15, 2026.

The goal of this workshop is to explain an experiment you can reason about: what the model predicts, which parameters change, what a training step means, and what evidence would justify keeping the resulting adapter. A completed Training Job is only one part of that experiment.

We follow the repository's [Qwen PII trainer](https://github.com/Atom-oh/kubernetes-docs/blob/b89fc1d3334717031227a00a894a8c0927986ba3/examples/ai-ml/qwen-pii-finetuning/src/train.py), using synthetic documents. Keep [Part 3's submission, ownership, export and cleanup contracts](03-sagemaker-mlflow-execution.md) alongside this chapter. Continue with the [data augmentation workshop](06-data-augmentation-workshop.md) and [PII evaluation and release workshop](07-pii-evaluation-release.md).

**Execution status:** the committed GPU path intentionally stops because its PyTorch 2.8 DLC reached end of patch on August 6, 2026. Keep `src/runtime_contract.py` intact. The CPU exercises below do not load model weights. Model-loading and training excerpts explain the pinned implementation; GPU exercises require a separately validated runtime migration. They are not records of successful GPU training.

## 1. Define the prediction before choosing the training method

Consider this entirely synthetic document:

```text
Synthetic contact Alex Example; email alex@example.com.
```

The desired model response is a list of entities copied from that document:

```text
PERSON	Alex Example
EMAIL	alex@example.com
```

The model is learning **structured extraction**, not how to rewrite the whole document. Its output contract is zero or more `TYPE<TAB>ORIGINAL` lines. The allowed types are `PERSON`, `RRN`, `DOB`, `REL`, `ADDRESS`, `PHONE`, `EMAIL`, `ACCOUNT` and `CARD`. A response such as “I found a person and an email” is not the required output, even when its meaning is correct.

After extraction, deterministic code validates the types and source matches and replaces selected spans with tokens such as `[PERSON_1]`. This separation makes errors observable. A missed entity is an extraction error; a wrong replacement boundary is a replacement error; a malformed response is a format error. Combining everything into “the LLM redacts the document” hides these distinctions.

### CPU exercise: extraction output to reversible tokens

Run from `examples/ai-ml/qwen-pii-finetuning` in the package's Python 3.12 environment. This uses existing local helpers and synthetic strings; it does not call a model or AWS.

```python
from src.pii_tokens import parse_tsv, pseudonymize_text, reassemble_text

source = "Synthetic contact Alex Example; email alex@example.com."
completion = "PERSON\tAlex Example\nEMAIL\talex@example.com"

entities = parse_tsv(completion, source)
result = pseudonymize_text(source, entities)

assert result.masked_text == (
    "Synthetic contact [PERSON_1]; email [EMAIL_1]."
)
assert reassemble_text(result.masked_text, result.mapping) == source
print(result.masked_text)
```

The mapping makes this **reversible pseudonymization**. Do not call it irreversible removal or proof of anonymization. In a real workflow, the source, mapping, raw predictions and trained adapter need appropriate access and retention controls. A round-trip test verifies reversibility; even replacing nothing can pass that test.

The current `parse_tsv()` is deliberately tolerant: it can discard malformed rows and retain valid ones. `train.py` can count an empty completion as parseable because zero-entity documents are valid inputs. Therefore, “parse success” alone does not establish correct extraction. The PII evaluation workshop separates strict format validity, entity recall and residual PII.

### Choose a baseline that matches the problem

| Method | A useful first experiment | What it does not solve automatically |
|---|---|---|
| Regex and deterministic rules | Stable phone/email formats and exact replacement rules | Context-dependent names, relationships, OCR variation and ambiguous numbers |
| A token-classification/NER model | Span labels with a stable entity taxonomy | New domain coverage, annotation quality and downstream replacement policy |
| Prompt-only generation | Establish the base model's extraction and TSV behavior | Reliable formatting, complete recall or immunity to instructions inside documents |
| LoRA | Adapt a pretrained model with trainable low-rank updates | Reduce the storage of the unquantized base model |
| QLoRA | Train adapters through a frozen quantized base when memory is constrained | Make activations, optimizer state or every model tensor four-bit |

Start with a deterministic baseline and a prompt-only baseline. If the prompt-only model is already adequate for a constrained task, training may add complexity without enough benefit. If it misses domain-specific entities or repeatedly violates the output contract, a supervised adapter experiment has a clearer purpose.

## 2. Understand what LoRA changes

For a linear layer with input width `d_in` and output width `d_out`, let:

- `W` have shape `(d_out, d_in)`;
- `A` have shape `(r, d_in)`;
- `B` have shape `(d_out, r)`.

Standard LoRA uses:

```text
W_effective = W + (alpha / r) * B @ A
y = W @ x + (alpha / r) * B @ A @ x
```

The base matrix `W` is frozen. The optimizer updates `A` and `B`, which contain `r × (d_in + d_out)` parameters instead of `d_in × d_out`. Gradients still propagate through the computation involving the base model; “frozen” does not mean that the base model is absent from the forward or backward computation. See the [LoRA paper](https://arxiv.org/abs/2106.09685).

For a `2048 → 768` projection with rank 16:

```python
d_in, d_out, rank, alpha = 2048, 768, 16, 32
base_parameters = d_in * d_out
adapter_parameters = rank * (d_in + d_out)

assert base_parameters == 1_572_864
assert adapter_parameters == 45_056
assert alpha / rank == 2
print(base_parameters, adapter_parameters, alpha / rank)
```

Rank controls the capacity of the update, not the number of training epochs. `lora_alpha` controls scaling; with this configuration, `alpha/r` is 2. Increasing rank without considering alpha also changes that scale. PEFT's optional rank-stabilized LoRA uses a different scaling rule; the committed configuration does not enable it.

In the default [PEFT 0.17.1 initialization](https://huggingface.co/docs/peft/v0.17.1/en/developer_guides/lora), the adapter initially behaves as a no-op because `B` starts at zero. Do not require every adapter tensor to have a nonzero gradient on the first backward pass. In a MoE model, some experts may not be selected by a particular batch either. A useful diagnostic checks finite gradients where present and changes in the expected adapter parameters after an optimizer step.

## 3. Budget QLoRA memory beyond the four-bit weights

The [QLoRA paper](https://arxiv.org/abs/2305.14314) combines a frozen quantized base with trainable adapters. The following settings in the committed trainer are different decisions:

| Setting or memory category | Meaning in this example |
|---|---|
| `load_in_4bit=True` | Load supported base linear weights through four-bit quantization |
| `bnb_4bit_quant_type="nf4"` | Use NormalFloat4, designed for normally distributed weights |
| `bnb_4bit_use_double_quant=True` | Quantize quantization constants to reduce additional storage |
| `bnb_4bit_compute_dtype=torch.bfloat16` | Use BF16 computation for the quantized linear path; not four-bit arithmetic everywhere |
| LoRA parameters and gradients | Trainable tensors with their own dtypes and memory requirements |
| Optimizer state | Additional state for trainable parameters; NF4 does not automatically make it eight-bit |
| Activations and temporary tensors | Depend on sequence length, microbatch, attention implementation and checkpointing |
| Unquantized modules | Embeddings, normalization and other tensors may use higher precision |

Double quantization does not mean “quantize the model to two bits.” BF16 is not a guarantee that every tensor occupies two bytes: k-bit preparation and adapter handling can retain or promote selected tensors to FP32. Inspect actual dtypes and trainable parameters rather than inferring the entire memory footprint from one configuration field. The [versioned bitsandbytes guide](https://huggingface.co/docs/transformers/v4.57.6/en/quantization/bitsandbytes) explains NF4, compute dtype and nested quantization separately.

Gradient checkpointing saves selected activations by recomputing them during backward. It trades computation for memory. Gradient accumulation combines several microbatches before an optimizer update; it does not require storing all of those microbatches' activation graphs simultaneously. Neither feature eliminates optimizer state.

### Total parameters and active MoE parameters are different budgets

The [Qwen model card](https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507) describes **30.5B total parameters and 3.3B activated parameters**, with 48 layers, 128 experts and 8 selected experts per token. Activated parameters describe the sparse computation for a token. They do not mean only 3.3B parameters need to be loaded.

An idealized `30.5 billion × 4 bits` calculation is **15.25 decimal GB**. This is a lower-bound illustration for weight storage, not a prediction of GPU memory usage. It excludes quantization metadata, unquantized tensors, adapters, gradients, optimizer state, activations and allocation overhead. It cannot prove that a particular single-GPU instance will fit.

## 4. Inspect this model's adapter targets

The historical package pins these relevant versions:

| Package | Pin |
|---|---|
| PyTorch | `2.8.0` |
| Transformers | `4.57.6` |
| PEFT | `0.17.1` |
| TRL | `0.24.0` |
| bitsandbytes | `0.48.2` |
| Accelerate | `1.10.1` |
| datasets | `3.6.0` |

In the [pinned Qwen3 MoE implementation](https://github.com/huggingface/transformers/blob/v4.57.6/src/transformers/models/qwen3_moe/modeling_qwen3_moe.py), experts are a `ModuleList` of modules with `gate_proj`, `up_proj` and `down_proj` linear layers. Attention uses `q_proj`, `k_proj`, `v_proj` and `o_proj`. The routing gate is separately named `gate`.

The committed `LoraConfig` targets those seven projection suffixes. It does **not** target the router merely because `gate_proj` contains the word “gate.” Conversely, replacing the list with `"all-linear"` can include additional linear modules, including the router. That is a different experiment.

```python
# Inspection hook after an authorized model load, before adapter insertion.
from collections import Counter

targets = {
    "q_proj", "k_proj", "v_proj", "o_proj",
    "gate_proj", "up_proj", "down_proj",
}
matched = [
    name for name, module in model.named_modules()
    if name.rsplit(".", 1)[-1] in targets
]
counts = Counter(name.rsplit(".", 1)[-1] for name in matched)
assert set(counts) == targets
assert not any(name.endswith(".gate") for name in matched)
print(dict(sorted(counts.items())))  # Module names/counts, not training data.
```

For the published model configuration, source-based arithmetic at rank 16 gives approximately **13.37 million** adapter parameters for the four attention projections, plus **830.47 million** for the three projections in every expert: **843,841,536** in total. This is arithmetic from the model dimensions, not a measured GPU result. Confirm the actual result after adapter insertion with `trainer.model.print_trainable_parameters()`.

You can reproduce the count without importing a model. The [model configuration](https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507/blob/main/config.json) gives hidden size 2,048, head dimension 128, 32 query heads, 4 key/value heads and expert intermediate size 768. Thus Q projects `2048 → 4096`, K/V each project `2048 → 512`, and O projects `4096 → 2048`. Each expert has two `2048 → 768` projections and one `768 → 2048` projection.

```python
# CPU arithmetic from this model/version's configuration; not a GPU benchmark.
layers, experts, rank = 48, 128, 16
hidden, head_dim, q_heads, kv_heads = 2048, 128, 32, 4
expert_hidden = 768
q_width, kv_width = q_heads * head_dim, kv_heads * head_dim

attention = layers * rank * (
    (hidden + q_width)
    + 2 * (hidden + kv_width)
    + (q_width + hidden)
)
expert_adapters = layers * experts * 3 * rank * (hidden + expert_hidden)
total = attention + expert_adapters

assert attention == 13_369_344
assert expert_adapters == 830_472_192
assert total == 843_841_536
assert layers * (4 + 3 * experts) == 18_624  # Targeted linear modules.
print(attention, expert_adapters, total)
```

This count assumes the published 48-layer model's expert layout and the seven target suffixes above, with no additional trainable modules or biases. It is an expectation to compare with the real adapter inventory, not a substitute for that inventory.

This explains why “LoRA uses few parameters” is incomplete guidance for a large MoE target list. Comparing attention-only targets with attention-plus-expert targets can be a useful controlled experiment, but changing targets requires an instructional modification: the current trainer's target list is hard-coded.

Some newer or different MoE implementations use raw two- or three-dimensional `nn.Parameter` tensors instead of `nn.Linear` experts. [PEFT 0.17.1 documents `target_parameters`](https://github.com/huggingface/peft/blob/v0.17.1/docs/source/developer_guides/lora.md) for that case, including its expert-axis and multiple-adapter limitations. Inspect the implementation of the chosen model and version; do not copy a parameter-targeting recipe into this module-based implementation.

## 5. Follow one record through chat formatting and the loss mask

The actual [dataset loader](https://github.com/Atom-oh/kubernetes-docs/blob/b89fc1d3334717031227a00a894a8c0927986ba3/examples/ai-ml/qwen-pii-finetuning/src/dataset.py) returns conversational **prompt/completion** data:

```python
from src.dataset import SYSTEM_INSTRUCTION

record = {
    "source_text": "Synthetic contact Alex Example.",
    "target_tsv": "PERSON\tAlex Example",
}
row = {
    "prompt": [
        {"role": "system", "content": SYSTEM_INSTRUCTION},
        {"role": "user", "content": record["source_text"]},
    ],
    "completion": [
        {"role": "assistant", "content": record["target_tsv"]},
    ],
}
assert row["completion"][0]["role"] == "assistant"
```

The unused `format_training_text()` function in `train.py` produces `### Instruction` text. It is **not** the current dataset path. Do not teach that string format as what `SFTTrainer` actually receives.

In [TRL 0.24.0](https://huggingface.co/docs/trl/v0.24.0/en/sft_trainer), the trainer applies the tokenizer's chat template to the prompt and to prompt-plus-completion. It builds a completion mask from that boundary. With `completion_only_loss=True`, prompt positions are assigned label `-100`; completion positions contribute to the causal-language-model loss. Padding is also ignored.

### An empty extraction target is not an empty training signal

A document with no target entities uses an empty assistant content string. Its answer should still finish the assistant turn. For this model, the [tokenizer configuration](https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507/blob/main/tokenizer_config.json) uses `<|im_end|>` as EOS and `<|endoftext|>` as padding.

```python
# CPU-only illustration of a mask, not actual tokenizer output.
input_ids = [101, 102, 103, 104, 151645]
completion_mask = [0, 0, 0, 0, 1]
labels = [
    token if keep else -100
    for token, keep in zip(input_ids, completion_mask)
]
assert labels == [-100, -100, -100, -100, 151645]
assert sum(label != -100 for label in labels) == 1
```

The example illustrates supervising EOS for a negative record. The real template can include additional completion tokens, such as a newline. Verify the real tokenized row; do not assume the illustrative prompt IDs or a fixed completion length.

The Instruct-2507 model card states that it is **non-thinking** and does not require `enable_thinking=False`. The current prediction code passes that argument, but it does not turn this checkpoint into a reasoning model. `assistant_only_loss=True` is a different option that requires appropriate assistant-mask support from the template; it is not necessary for this single-response prompt/completion contract.

### Inspect the prepared data before the first training step

The following hook belongs after constructing a trainer in an authorized, compatible environment. It checks counts and masks without printing source text or decoded labels.

```python
# Instructional inspection hook; not currently present in src/train.py.
prepared = trainer.train_dataset
for example in prepared:
    mask = example["completion_mask"]
    assert len(mask) == len(example["input_ids"])
    assert any(mask), "No supervised completion survived preprocessing"

examples = [prepared[i] for i in range(min(4, len(prepared)))]
batch = trainer.data_collator(examples)
supervised = (batch["labels"] != -100).sum(dim=1)
assert bool((supervised > 0).all())
if "attention_mask" in batch:
    padding = batch["attention_mask"] == 0
    assert bool((batch["labels"][padding] == -100).all())
print({"examples": len(examples), "target_tokens": supervised.tolist()})
```

Also inspect pre-truncation prompt-plus-completion lengths and confirm the answer EOS is retained. `max_length=1024` applies to the combined training sequence, not only to the document. A long prompt can consume the entire budget and remove the answer. Inference truncation can similarly hide PII while evaluation still expects entities from the complete document.

Choose a documented policy: reject overflow, shorten only nonessential prompt instructions, or chunk the source while updating the annotation contract. Keep chunks and augmentation descendants in the same document family/split. Do not simply raise the sequence length without revisiting activation memory, microbatch and inference output length.

## 6. Read the pinned training configuration in execution order

The following is a **code-reading excerpt**, not an instruction to launch the blocked GPU runtime. Names and arguments match PEFT 0.17.1, Transformers 4.57.6 and TRL 0.24.0.

First locate these stages in `run_training()`:

| Order | What the committed entry point does |
|---|---|
| 1 | Run the support guard, before importing the training stack |
| 2 | Resolve configuration and seed, prepare MLflow, and read the dataset files |
| 3 | Load the quantized model/tokenizer and evaluate the baseline on test |
| 4 | Prepare k-bit training and construct the adapter and conversational datasets |
| 5 | Train, with intermediate evaluation on validation |
| 6 | Save the model output and log the final adapter files |
| 7 | Evaluate the tuned model on test and write aggregate results |

The test access in stages 3 and 7 is current behavior, not the recommended candidate-selection workflow in section 8.

```python
import torch
from peft import LoraConfig, prepare_model_for_kbit_training
from transformers import BitsAndBytesConfig

quantization = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_use_double_quant=True,
    bnb_4bit_compute_dtype=torch.bfloat16,
)

# `model` has already been loaded by the reviewed loading path.
model.config.use_cache = False
model = prepare_model_for_kbit_training(
    model, use_gradient_checkpointing=True
)
lora_config = LoraConfig(
    r=16,
    lora_alpha=32,
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",
    target_modules=[
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ],
)
```

The committed loader uses `AutoModelForCausalLM.from_pretrained(..., quantization_config=..., device_map="auto", torch_dtype=torch.bfloat16)`. Automatic placement must be inspected; CPU/disk offload is not a substitute for demonstrating a valid training placement. A proposed single-GPU experiment can use explicit placement after confirming memory fit. This chapter does not change the loader.

The current code also sets `output_router_logits=True`. For the pinned MoE implementation, router auxiliary loss can contribute to the reported loss. That does not make the router a LoRA target. Record this choice when comparing runs.

```python
from trl import SFTConfig, SFTTrainer

sft_args = SFTConfig(
    output_dir=str(output_dir / "checkpoints"),
    max_steps=80,
    per_device_train_batch_size=1,
    per_device_eval_batch_size=1,
    gradient_accumulation_steps=8,
    learning_rate=0.0002,
    lr_scheduler_type="cosine",
    warmup_ratio=0.03,
    logging_steps=1,
    eval_strategy="steps",
    eval_steps=20,
    save_strategy="steps",
    save_steps=80,
    save_total_limit=1,
    bf16=True,
    gradient_checkpointing=True,
    gradient_checkpointing_kwargs={"use_reentrant": False},
    max_length=1024,
    packing=False,
    completion_only_loss=True,
    report_to="none",
    seed=42,
    data_seed=42,
)
trainer = SFTTrainer(
    model=model,
    args=sft_args,
    train_dataset=train_dataset,
    eval_dataset=validation_dataset,
    processing_class=tokenizer,
    peft_config=lora_config,
)
```

This excerpt shows the configured **full-run** values and assumes the existing model, tokenizer, datasets and output directory. It intentionally shows `max_length` and `processing_class`; do not substitute older `max_seq_length`/`tokenizer` examples without checking the version. The pinned `SFTConfig` does not have a configuration-level `chat_template_kwargs` field. Version 0.24.0 supports per-example template kwargs instead.

The actual tokenizer already has the appropriate EOS. An explicit `eos_token="<|im_end|>"` is supported by this SFTConfig if a lesson wants to make that contract visible, but omitting it here is not evidence that the current tokenizer has a wrong EOS.

`config/experiment.yaml` contains `quantization`, `double_quant` and `compute_dtype`, but the loader currently hard-codes NF4/double quantization/BF16. Changing only those YAML values does not implement an ablation. Either keep them fixed and explain that fact, or make a separately reviewed instructional modification that actually wires the choice into the loader.

### From optimization to a generated extraction

After the prerequisites and inspection hooks pass in a validated GPU environment, the committed sequence calls `trainer.train()`, saves the model output, and evaluates the tuned model. The following excerpt shows those boundaries; it is not a CPU exercise.

```python
# Code-reading excerpt: assumes an approved, constructed GPU trainer.
train_result = trainer.train()
trainer.save_model(str(output_dir))
trainer.model.config.use_cache = True
```

For generation, the prompt must stop at the assistant generation prefix; do not include the gold completion. Remove the prompt tokens from generated IDs before parsing the answer. Here is a proposed single-record diagnostic using the synthetic `row` and `record` above:

```python
# Instructional inference hook; not a replacement for the committed CLI.
trainer.model.eval()
prompt = tokenizer.apply_chat_template(
    row["prompt"], tokenize=False, add_generation_prompt=True
)
inputs = tokenizer(prompt, return_tensors="pt", add_special_tokens=False)
prompt_length = inputs["input_ids"].shape[1]
if prompt_length > 1024:
    raise ValueError("Apply the reviewed long-document policy first")
inputs = inputs.to(trainer.model.device)

with torch.inference_mode():
    generated = trainer.model.generate(
        **inputs,
        do_sample=False,
        max_new_tokens=512,
        pad_token_id=tokenizer.pad_token_id,
        eos_token_id=tokenizer.eos_token_id,
    )
completion = tokenizer.decode(
    generated[0, prompt_length:], skip_special_tokens=True
)
entities = parse_tsv(completion, record["source_text"])
# Evaluate aggregate metrics; do not log raw completions from real documents.
```

The current `_predict_records()` batches examples with left padding and enables truncation. The hook above instead rejects an overlong single prompt to make the instructional boundary visible. Its 512-token output cap is a separate limit: a long TSV answer can still be cut off. Check response termination and format in addition to prompt length.

## 7. Count examples, optimizer updates and epochs

For ordinary data parallel training:

```text
effective batch ≈ microbatch per device × accumulation × data-parallel workers
```

In the committed single-instance, single-GPU example, that is `1 × 8 × 1 = 8`. Gradient accumulation of eight means one optimizer update follows eight microbatches. It does not mean each microbatch has eight examples.

```python
from math import ceil

records = 1600
microbatch, accumulation, workers = 1, 8, 1
effective_batch = microbatch * accumulation * workers
updates_per_epoch = ceil(records / effective_batch)

assert effective_batch == 8
assert updates_per_epoch == 200
assert 10 * effective_batch == 80
assert 80 * effective_batch == 640
assert 80 / updates_per_epoch == 0.4
```

Thus the configured smoke run has 10 optimizer updates, about 80 example presentations. The “full” run has 80 updates, about 640 presentations, or 0.4 of a 1,600-record epoch under these divisible, unpacked assumptions. “Full” is a mode label, not a claim of convergence or a complete epoch.

`max_steps` determines the update budget. With variable sequence lengths, equal steps do not imply equal supervised tokens or compute. When comparing a longer context or augmented dataset, record examples and target tokens seen, not only wall time and loss. Distributed tail batches and packing require additional accounting; they are not part of the arithmetic above.

## 8. Separate a tiny overfit diagnostic from model selection

Before spending a full training budget, define a proposed diagnostic with 8–16 **training** records. Include a simple positive example, repeated entities, formatting variation and a no-PII example. Keep this subset separate from validation and locked test.

After runtime migration, check the following sequence: model loads; the prompt/completion masks are correct; one forward/backward step produces finite values; expected adapter parameters change; the small subset becomes easier to fit; the saved adapter reloads with the same base model and reproduces deterministic decoding.

For example, eight records with an effective batch of eight and 20 optimizer updates produce about 20 passes over that tiny subset. That is a deliberate diagnostic budget, not a recommendation for the full dataset. Compare exact extraction on those eight records and inspect the negative record's termination; a lower loss alone is not the acceptance condition.

This is intentionally an overfit check. Success tells you the training path can learn these examples. It does not demonstrate generalization, production recall or removal of all PII. Failure is useful: fix masks, targets, data correspondence or optimization before increasing the model or dataset size.

### Why the current trainer is not a safe HPO loop

The committed trainer reads the test file and evaluates it **both before and after every run**, including smoke. It uses validation for intermediate trainer evaluation, but final baseline/tuned metrics are calculated on test each time. Do not repeatedly inspect those test results while choosing hyperparameters.

For a teaching tuning workflow, make a clearly labeled modification to use a smoke subset for execution diagnostics and validation for candidate comparison. Keep test unavailable to ordinary tuning runs, freeze the chosen configuration and only then perform a final baseline/candidate test comparison. This separation is explained further in the [PII evaluation and release workshop](07-pii-evaluation-release.md).

| Experiment | Hold fixed | Change deliberately | Choose using validation |
|---|---|---|---|
| Adapter capacity | Data, targets, learning rate, token budget | Rank, for example 8 versus 16, with scaling policy stated | Recall, residual PII, over-redaction and training stability |
| Target scope | Data, rank, decoding and budget | Attention-only versus current attention-plus-expert targets | Quality benefit against trainable parameters and measured memory |
| Optimization | Data, targets, rank, sequence policy | One learning-rate choice at a time | Loss trajectory and extraction metrics, not loss alone |
| Sequence policy | Evaluation records and label contract | Reject/chunk policy or a justified larger token budget | Long-document coverage and truncation rate |
| Augmentation | Original families and evaluation sets | One train-only transformation family | Rare-type, formatting and negative-example behavior |

These rows are an experimental design, not implemented CLI switches or recommended winning values. Augmentation descendants must remain with their source family. Family separation does not automatically guarantee exact-text, entity, template or domain separation; the [data augmentation workshop](06-data-augmentation-workshop.md) makes those audits explicit.

The data augmentation workshop's CPU exercise uses a separate dataset. The 1,600-record calculations here describe the historical training configuration; do not silently reuse those counts for the new lab output.

## 9. Map the experiment onto SageMaker AI

Use the [actual launcher](https://github.com/Atom-oh/kubernetes-docs/blob/b89fc1d3334717031227a00a894a8c0927986ba3/examples/ai-ml/qwen-pii-finetuning/launch/sagemaker_train.py) to connect local concepts to job inputs and outputs.

| Step | Current mapping | Evidence to inspect |
|---|---|---|
| Local configuration | `config/experiment.yaml` plus `requirements.lock` | Config, source and dependency versions |
| Source bundle | `generated/source.tar.gz` contains source/config/requirements | Bundle inventory and SHA-256; no recursive credential/data bundling |
| S3 inputs | Separate `source/` and `dataset/` prefixes for the experiment | Uploaded-object hashes and intended account/bucket/prefix |
| Source inside the job | `/opt/ml/code/config/experiment.yaml`; `SAGEMAKER_PROGRAM=src/train.py` | Toolkit invocation and config existence |
| Dataset channel | One File-mode channel named `dataset` | `/opt/ml/input/data/dataset/{train,validation,test}.jsonl` and manifest |
| Trainer evaluation | Validation dataset during training; current final comparisons use test | Actual split IDs/hashes and the distinction above |
| MLflow | Configuration/version/manifest files, aggregate metrics and final adapter files | Run identity, artifact availability and client/App compatibility |
| SageMaker model output | Current `output-dir=/opt/ml/model` | Final directory contents and the S3 model-artifact URI |

Channel names determine the input paths. Having a channel named `dataset` does not make all its contents “training data”: this channel contains three different splits. Recompute and compare observed file hashes before learning from them; a manifest that was merely logged is not proof that the loaded files matched it.

### Understand what gets saved

The current SFT output directory is `/opt/ml/model/checkpoints`, because checkpoints are placed below `output_dir`. SageMaker packages the model directory for upload, so the resulting model artifact can include those checkpoints as well as the final adapter and JSON files. MLflow's explicit adapter-file allowlist does not change SageMaker's directory packaging.

For a proposed cleaner layout, separate final adapter files under `/opt/ml/model`, aggregate outputs under `/opt/ml/output/data`, and recoverable checkpoints under `/opt/ml/checkpoints`. S3 checkpoint synchronization requires the appropriate job configuration; creating a local directory alone is not a backup mechanism. See [AWS's storage-path table](https://docs.aws.amazon.com/sagemaker/latest/dg/model-train-storage-env-var-summary.html) and [training-output contract](https://docs.aws.amazon.com/sagemaker/latest/dg/your-algorithms-training-algo-output.html).

An adapter is not a self-contained replacement for the base model. Reloading needs the correct base model/revision, tokenizer, adapter configuration and compatible runtime. The current code does not pin a model revision; record one in a separately reviewed reproducibility improvement.

## 10. Diagnose the job stage before changing hyperparameters

SageMaker status and model-stage diagnostics answer different questions. `SecondaryStatus` can indicate downloading, training or uploading; a job can remain in `Training` while the application is loading weights, evaluating a baseline or saving an adapter.

The following is a read-only diagnostic command for an **existing authorized job**, not a command executed in this workshop:

```bash
: "${TRAINING_JOB_NAME:?Set the existing reviewed job name}"
: "${AWS_REGION:?Set its Region}"
aws sagemaker describe-training-job \
  --region "$AWS_REGION" \
  --training-job-name "$TRAINING_JOB_NAME" \
  --query '{
    status:TrainingJobStatus,
    phase:SecondaryStatus,
    stages:SecondaryStatusTransitions,
    failure:FailureReason,
    model:ModelArtifacts.S3ModelArtifacts,
    trainingSeconds:TrainingTimeInSeconds,
    billableSeconds:BillableTimeInSeconds
  }'
```

Keep failure details private until reviewed. Use the job's streams in `/aws/sagemaker/TrainingJobs` and bounded log windows, not a dump of unrelated jobs or training examples. AWS documents [secondary status transitions](https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_SecondaryStatusTransition.html) and [CloudWatch logging](https://docs.aws.amazon.com/sagemaker/latest/dg/logging-cloudwatch.html).

Add aggregate-only stage markers to a future instructional trainer: data validated, model loaded, baseline completed, adapters inserted, first backward pass completed, optimization completed, artifacts saved and evaluation completed. These markers make a stall diagnosable without logging source documents.

| Symptom | First distinction to make | A useful next action |
|---|---|---|
| Failure before model loading | Runtime guard, package/toolkit failure or missing path | Read the stage and exact config/channel mapping; do not tune rank |
| OOM while loading | Base weights/placement versus optimizer memory | Check total model size, quantization, unquantized tensors and actual placement |
| OOM on backward | Activations versus adapter/optimizer state | Reduce microbatch/sequence budget; verify checkpointing and target scope |
| NaN loss | Bad targets versus numerical/optimization problems | Check nonzero supervised labels, finite values, BF16 support and learning rate |
| Loss falls but recall stays low | Format learning versus entity coverage | Inspect validation by type, language, length and negative/positive records |
| Output is prose or malformed TSV | Chat template/EOS/masking versus task ambiguity | Verify the actual prepared example and decoding contract before adding training steps |
| High parse/round-trip score but PII remains | Parser tolerance and reversible replacement | Inspect residual PII and entity recall; do not treat parser success as privacy success |
| Job completed but result cannot reload | Wrong artifact directory or mismatched base/revision | Inspect artifact contents and perform a separate adapter reload check |

The current `peak_gpu_memory_bytes` measures PyTorch allocated-memory peak on the default CUDA device after a reset following model load. It is not total GPU memory, the loading peak or a sum across devices. Label future measurements precisely.

## 11. Treat runtime migration as a tested cohort

The [AWS DLC support policy](https://aws.github.io/deep-learning-containers/reference/support_policy/) and [image catalog](https://aws.github.io/deep-learning-containers/reference/available_images/) were checked on September 15, 2026. The old `pytorch-training` image family and the newer `pytorch` family must not be confused.

| Catalog entry | SageMaker tag, excluding registry hostname | Python / OS | End of patch |
|---|---|---|---|
| Current historical example | `pytorch-training:2.8.0-gpu-py312-cu129-ubuntu22.04-sagemaker` | 3.12 / Ubuntu 22.04 | 2026-08-06 |
| New family 2.11 | `pytorch:2.11.0-cu130-amzn2023-sagemaker` | 3.12 / AL2023 | 2027-04-30 |
| New family 2.12 | `pytorch:2.12.1-cu130-amzn2023-sagemaker` | 3.12 / AL2023 | 2027-07-02 |
| New family 2.13 | `pytorch:2.13.0-cu133-amzn2023-sagemaker` | 3.12 / AL2023 | 2027-07-20 |

These are verified catalog entries, **not validated replacement environments for this package**. AWS also warns that Ubuntu-based PyTorch 2.8–2.10 cannot be fully patched and recommends AL2023 PyTorch 2.11 or later. The launcher fixes both an old repository name and a tag; replacing a version number alone is insufficient.

A migration must align the image repository/tag/digest, Region availability, Python, CUDA/driver/architecture, PyTorch, HF/PEFT/TRL/bitsandbytes dependencies, training toolkit and MLflow client/service. Installing the current `torch==2.8.0` lock into a newer DLC could undo the intended framework migration.

Only after those choices are reviewed should an authorized GPU preflight test actual CUDA/BF16 support, quantized loading, expected targets/dtypes, a forward/backward step, finite loss, adapter updates and save/reload. That is a **test procedure**, not evidence that it has succeeded. Retain the historical guard while developing and validating the replacement cohort.

## 12. Check your understanding

1. With microbatch 1 and accumulation 8 on one worker, how many example presentations do 80 updates represent? **About 640**, under the unpacked/divisible assumptions used here.
2. Does “3.3B active” imply only 3.3B parameters need memory? **No.** It describes sparse computation; total weights and training state still matter.
3. What should a negative document teach? **A valid empty extraction response ending the assistant turn**, not an all-ignored label sequence.
4. Can you select rank using a test score after every run? **No.** Select on validation, freeze the candidate and use locked test for the final comparison.
5. Does a successful round trip prove PII was removed? **No.** It proves reversibility of the replacement path; missed PII can remain untouched.
6. Is a supported DLC tag sufficient to enable the current launcher? **No.** Its repository, dependencies, toolkit, hardware and integration contracts must form a validated cohort.

## Primary references

All references below were checked on **2026-09-15**. Versioned sources govern the code-reading examples.

- [LoRA paper](https://arxiv.org/abs/2106.09685) and [QLoRA paper](https://arxiv.org/abs/2305.14314)
- [PEFT 0.17.1 LoRA guide](https://huggingface.co/docs/peft/v0.17.1/en/developer_guides/lora) and [k-bit preparation source](https://github.com/huggingface/peft/blob/v0.17.1/src/peft/utils/other.py)
- [Transformers 4.57.6 bitsandbytes quantization](https://huggingface.co/docs/transformers/v4.57.6/en/quantization/bitsandbytes)
- [bitsandbytes 0.48.2 four-bit modules](https://github.com/bitsandbytes-foundation/bitsandbytes/blob/0.48.2/docs/source/reference/nn/linear4bit.mdx)
- [TRL 0.24.0 SFT guide](https://huggingface.co/docs/trl/v0.24.0/en/sft_trainer), [SFTConfig](https://github.com/huggingface/trl/blob/v0.24.0/trl/trainer/sft_config.py) and [SFTTrainer](https://github.com/huggingface/trl/blob/v0.24.0/trl/trainer/sft_trainer.py)
- [Qwen model card](https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507), [model configuration](https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507/blob/main/config.json) and [pinned Transformers implementation](https://github.com/huggingface/transformers/blob/v4.57.6/src/transformers/models/qwen3_moe/modeling_qwen3_moe.py)
- [AWS DLC support](https://aws.github.io/deep-learning-containers/reference/support_policy/) and [available images](https://aws.github.io/deep-learning-containers/reference/available_images/)
- [SageMaker storage/environment variables](https://docs.aws.amazon.com/sagemaker/latest/dg/model-train-storage-env-var-summary.html) and [training output](https://docs.aws.amazon.com/sagemaker/latest/dg/your-algorithms-training-algo-output.html)

Next: [Data Augmentation Workshop](06-data-augmentation-workshop.md)

## Quiz

Check the concepts and calculations in the [QLoRA Fine-Tuning Workshop Quiz](../../quizzes/ai-ml/sagemaker-ai/05-qlora-finetuning-workshop-quiz.md).
