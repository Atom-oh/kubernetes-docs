# Workshop quiz: QLoRA fine-tuning for PII extraction

> **Last Updated**: September 15, 2026

> **Last Updated**: September 15, 2026

## Multiple Choice Questions

1. Which statement correctly describes QLoRA with `load_in_4bit=True`, `bnb_4bit_quant_type="nf4"` and `bnb_4bit_compute_dtype=torch.bfloat16`?
   - A) Activations and optimizer state become four-bit along with the base weights.
   - B) Supported base weights are stored in four-bit form and frozen, the quantized linear path uses BF16 computation, and adapters are trained.
   - C) BF16 computation cancels NF4, so all base weights are stored in 16-bit form.
   - D) Double quantization means training the base weights twice.

<details>
<summary>Show Answer</summary>

**Answer: B**

Weight storage, compute dtype and trainable parameters are separate choices. NF4 reduces base-weight storage, while BF16 specifies the compute dtype of that path. Double quantization quantizes quantization constants. Memory for adapters, gradients, optimizer state, activations and higher-precision modules must be accounted for separately.
</details>

2. A linear layer has input width 2,048 and output width 768. Standard LoRA uses rank 16 and alpha 32, with no trainable biases or additional modules. What are the adapter parameter count and `alpha/r` scale?
   - A) 1,572,864 parameters and 2
   - B) 45,056 parameters and 32
   - C) 45,056 parameters and 2
   - D) 32,768 parameters and 0.5

<details>
<summary>Show Answer</summary>

**Answer: C**

`A` has shape `(16, 2048)` and `B` has shape `(768, 16)`, giving `16 × (2048 + 768) = 45,056` parameters. Standard LoRA scales the update by `32 / 16 = 2`. The value `2048 × 768 = 1,572,864` counts the base matrix, not the adapter. Rank-stabilized LoRA uses a different scaling rule.
</details>

3. How should Qwen's “30.5B total /3.3B active parameters” be interpreted when planning training memory?
   - A) The active count describes sparse computation for a token; total weights, adapters, gradients, optimizer state and activations must be considered separately.
   - B) Only 3.3B parameters are ever loaded, so the other experts consume no memory.
   - C) Since `30.5B × 4 bits = 15.25GB`, total training memory is exactly 15.25GB.
   - D) Selecting eight experts per token means LoRA is inserted into only eight experts in the entire model.

<details>
<summary>Show Answer</summary>

**Answer: A**

The active parameter count concerns a token's computation path; it does not replace the total-model storage budget. The 15.25 decimal GB calculation is an idealized four-bit weight estimate that omits quantization metadata and other training memory. Adapter insertion targets and the experts actually selected by a particular batch are also different concepts.
</details>

4. There are 1,600 training records, microbatch 1, gradient accumulation 8, one data-parallel worker and 80 optimizer updates. Assuming no packing or incomplete final batches, what are the effective batch, example presentations and epoch fraction?
   - A) 1, 80 presentations and 0.05 epoch
   - B) 8, 1,280 presentations and 0.8 epoch
   - C) 80, 6,400 presentations and 4 epochs
   - D) 8, 640 presentations and 0.4 epoch

<details>
<summary>Show Answer</summary>

**Answer: D**

The effective batch is `1 × 8 × 1 = 8`, and example presentations are `80 × 8 = 640`. One epoch requires `1600 / 8 = 200` updates, so 80 updates represent 0.4 epoch. The current “full” label names an execution mode, not a completed epoch or convergence. Different sequence lengths can also yield different training-token counts for the same number of examples.
</details>

5. For a document with no entities and an empty assistant-content target, what should be checked under completion-only loss?
   - A) Every label is `-100`, so the record contributes nothing to training.
   - B) Prompt and padding positions are ignored, but valid completion tokens such as the assistant's EOS remain supervised.
   - C) Only EOS is ignored, while the entire source prompt is trained as the extraction answer.
   - D) NF4 makes EOS and loss masks unnecessary, so no check is needed.

<details>
<summary>Show Answer</summary>

**Answer: B**

A negative record should teach the model to finish its answer without extracting entities. This model uses `<|im_end|>` as EOS. After the actual chat template and truncation, verify that some supervised labels remain. A real completion can include extra tokens such as a newline; an all-ignored label sequence should not be treated as normal negative-example training.
</details>

6. How should evaluation sets be used when comparing rank and augmentation choices?
   - A) Select candidates under consistent validation conditions, freeze the configuration, then make the final baseline/candidate comparison on locked test.
   - B) Inspect the test score for every candidate and select the highest one.
   - C) Generate all augmentation descendants first, then randomly divide them among train, validation and test.
   - D) Deploy once loss falls on the tiny overfit subset, without checking generalization.

<details>
<summary>Show Answer</summary>

**Answer: A**

Tune with validation and keep test locked for the final comparison. The current trainer evaluates test before and after every run, including smoke, so it is not already a safe HPO loop. A teaching tuning path needs a separate modification. Split original families before augmentation and augment training descendants only; a tiny overfit check diagnoses the learning path rather than proving generalization.
</details>

7. What is the correct way to check the current seven LoRA target suffixes for the Qwen3 MoE implementation in Transformers 4.57.6?
   - A) Replace them with `"all-linear"` and skip inspection because the selected modules are identical.
   - B) Always switch to `target_parameters` because every MoE uses raw parameters.
   - C) Inspect actual module names/counts and confirm coverage of attention projections and expert `gate_proj`/`up_proj`/`down_proj`, while excluding the separate router `gate`.
   - D) Expect only seven linear modules in the entire model because there are seven target names.

<details>
<summary>Show Answer</summary>

**Answer: C**

This version implements experts as `nn.Linear` projections within a `ModuleList`. A suffix repeats across layers and experts, so the number of suffixes is not the module count. For the published configuration, compare the expected `48 × (4 + 3 × 128) = 18,624` linear targets with the actual inventory. `"all-linear"` can add modules such as the router, while `target_parameters` addresses a different implementation using raw parameters.
</details>

8. You find a currently supported AL2023 PyTorch DLC in the catalog. What is the appropriate next step before re-enabling GPU execution for the historical example?
   - A) Change only the image tag and install the old lock, including `torch==2.8.0`.
   - B) Remove the date guard and submit a full run because the image exists in ECR.
   - C) Record GPU quantized loading and backward as successful because the CPU exercises passed.
   - D) Validate the image repository/tag/digest, Python/CUDA/driver, dependencies, toolkit and MLflow cohort, perform an authorized GPU smoke test, and retain the existing guard while the replacement remains unvalidated.

<details>
<summary>Show Answer</summary>

**Answer: D**

The PyTorch 2.8 DLC reached end of patch on August 6, 2026. A newer catalog entry is not a validated replacement cohort for this package. The new family can also use a repository different from `pytorch-training`, and installing the old torch pin can undo the migration. A GPU preflight is a future test procedure; CPU checks or image lookup do not establish successful GPU execution.
</details>

---

[Return to learning materials](../../../ai-ml/sagemaker-ai/05-qlora-finetuning-workshop.md)
