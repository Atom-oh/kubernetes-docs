# 实战：用于 PII 提取的 QLoRA 微调

> **最后更新**：2026 年 9 月 16 日

主要资料已于 2026 年 9 月 15 日核查。

本实战旨在讲解一个可进行推理的实验：模型会预测什么、哪些参数会变化、训练步骤意味着什么，以及有什么证据足以决定保留训练得到的 adapter。Training Job 完成只是实验的一部分。

我们使用仓库中的 [Qwen PII trainer](https://github.com/Atom-oh/kubernetes-docs/blob/b89fc1d3334717031227a00a894a8c0927986ba3/examples/ai-ml/qwen-pii-finetuning/src/train.py)，并使用合成文档。请同时参阅[第 3 部分中的提交、所有权、导出和清理约定](03-sagemaker-mlflow-execution.md)。之后继续学习[数据增强实战](06-data-augmentation-workshop.md)和 [PII 评估与发布实战](07-pii-evaluation-release.md)。

**执行状态**：本章讲解的历史 `src/train.py` 路径会有意停止，因为它所用的 PyTorch 2.8 DLC 于 2026 年 8 月 6 日结束补丁支持。请保持 `src/runtime_contract.py` 不变。下方的 CPU 练习不会加载模型权重；训练代码片段用于解释这一固定版本实现。另有一条 PyTorch 2.11 路径于 2026 年 9 月 16 日完成真实 GPU 烟雾训练以及保存/重新加载验证。[学习路径执行记录](README.md#sagemaker-execution-readiness)说明了其小型验证样本和完整作业提交情况。不要将下方历史代码片段误解为新执行路径已经成功的证据。

## 1. 选择训练方法前先定义预测目标

看下面完全合成的文档：

```text
Synthetic contact Alex Example; email alex@example.com.
```

期望模型返回从该文档复制的实体列表：

```text
PERSON	Alex Example
EMAIL	alex@example.com
```

模型要学习的是**结构化提取**，而非改写整个文档。其输出约定为零行或多行 `TYPE<TAB>ORIGINAL`。允许的类型包括 `PERSON`、`RRN`、`DOB`、`REL`、`ADDRESS`、`PHONE`、`EMAIL`、`ACCOUNT` 和 `CARD`。即使“我找到了一个人名和一个电子邮件地址”在语义上正确，也不是要求的输出格式。

提取完成后，确定性代码会验证类型和原文匹配，并将选定文本范围替换为 `[PERSON_1]` 等 token。这种分离使错误可观测：漏掉实体是提取错误；替换范围不正确是替换错误；响应格式错误是格式错误。如果将所有步骤都合称为“LLM 对文档执行脱敏”，这些区别就会被掩盖。

### CPU 练习：将提取结果替换为可逆 token

在软件包的 Python 3.12 环境中，从 `examples/ai-ml/qwen-pii-finetuning` 目录运行。此练习使用现有本地辅助函数和合成字符串，不会调用模型或 AWS。

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

此映射实现了**可逆假名化**。不要称其为不可逆删除，也不要当作匿名化证明。在真实工作流中，源文档、映射、原始预测和训练好的 adapter 都需要适当的访问与保留控制。往返测试验证的是可逆性；即使一个值都未替换，也可能通过该测试。

当前的 `parse_tsv()` 有意采用宽松策略：它可以丢弃格式错误的行并保留有效行。`train.py` 可能会将空 completion 计为可解析，这是因为零实体文档属于有效输入。因此，“解析成功”本身并不能证明实体提取正确。PII 评估实战会分别评估严格格式有效性、实体召回率和残余 PII。

### 选择符合问题的基线

| 方法 | 适合作为第一项实验的场景 | 不会自动解决的问题 |
|---|---|---|
| 正则表达式和确定性规则 | 稳定的电话/邮箱格式和精确替换规则 | 依赖上下文的人名、关系、OCR 差异和歧义数字 |
| Token 分类/NER 模型 | 使用稳定实体类别体系标注文本范围 | 新领域覆盖、标注质量和下游替换策略 |
| 仅用提示词生成 | 确定基础模型的提取能力和 TSV 行为 | 格式可靠、完整召回，或不会遵从文档内部指令 |
| LoRA | 使用可训练的低秩更新适配预训练模型 | 减少未量化基础模型本身的存储量 |
| QLoRA | 内存受限时，通过冻结的量化基础模型训练 adapter | 让激活值、优化器状态或所有模型张量都变成 4 位 |

先建立确定性基线和仅提示词基线。如果仅提示词模型对受限任务已足够，训练可能只会增加复杂度，而收益有限。如果它漏掉领域实体或反复违反输出约定，则有监督 adapter 实验就有了明确目标。

## 2. 理解 LoRA 改变了什么

对于输入宽度为 `d_in`、输出宽度为 `d_out` 的线性层，定义：

- `W` 的形状为 `(d_out, d_in)`；
- `A` 的形状为 `(r, d_in)`；
- `B` 的形状为 `(d_out, r)`。

标准 LoRA 使用：

```text
W_effective = W + (alpha / r) * B @ A
y = W @ x + (alpha / r) * B @ A @ x
```

基础矩阵 `W` 保持冻结。优化器更新包含 `r × (d_in + d_out)` 个参数的 `A` 和 `B`，而不是更新 `d_in × d_out` 个参数。梯度仍会通过涉及基础模型的计算传播；“冻结”并不意味着前向或反向计算中不包含基础模型。参见 [LoRA 论文](https://arxiv.org/abs/2106.09685)。

对于秩为 16 的 `2048 → 768` 投影层：

```python
d_in, d_out, rank, alpha = 2048, 768, 16, 32
base_parameters = d_in * d_out
adapter_parameters = rank * (d_in + d_out)

assert base_parameters == 1_572_864
assert adapter_parameters == 45_056
assert alpha / rank == 2
print(base_parameters, adapter_parameters, alpha / rank)
```

秩控制更新的容量，而不是训练 epoch 数。`lora_alpha` 控制缩放；此配置下 `alpha/r` 为 2。如果不考虑 alpha 就增大秩，也会改变缩放值。PEFT 可选的 rank-stabilized LoRA 使用不同缩放规则；已提交配置没有启用该选项。

根据默认的 [PEFT 0.17.1 初始化方式](https://github.com/huggingface/peft/blob/v0.17.1/docs/source/developer_guides/lora.md)，由于 `B` 初始值为零，adapter 一开始等同于不做任何更新。不要要求每个 adapter 张量在第一次反向传播时都有非零梯度。在 MoE 模型中，特定批次也可能不会选中某些专家。有效的诊断应检查存在时的梯度是否有限，以及执行优化器更新后预期 adapter 参数是否发生变化。

## 3. 除 4 位权重外，还要估算 QLoRA 内存

[QLoRA 论文](https://arxiv.org/abs/2305.14314)将冻结的量化基础模型与可训练 adapter 结合。已提交 trainer 中的下列设置分别代表不同决策：

| 设置或内存类别 | 在此示例中的含义 |
|---|---|
| `load_in_4bit=True` | 通过 4 位量化加载支持此功能的基础线性层权重 |
| `bnb_4bit_quant_type="nf4"` | 使用专为正态分布权重设计的 NormalFloat4 |
| `bnb_4bit_use_double_quant=True` | 量化量化常数以减少额外存储 |
| `bnb_4bit_compute_dtype=torch.bfloat16` | 量化线性计算路径使用 BF16；并非所有地方都采用 4 位计算 |
| LoRA 参数与梯度 | 可训练张量，有各自的数据类型和内存需求 |
| 优化器状态 | 可训练参数的额外状态；NF4 不会自动将其变成 8 位 |
| 激活值和临时张量 | 取决于序列长度、microbatch、注意力实现及 checkpointing |
| 未量化模块 | Embedding、normalization 和其他张量可能使用更高精度 |

双重量化不等于“将模型量化到 2 位”。BF16 也不保证每个张量只占 2 字节：k-bit 准备和 adapter 处理可能让部分张量保留或提升为 FP32。不要仅根据某个配置字段推断全部内存占用；应检查实际数据类型和可训练参数。[带版本的 bitsandbytes 指南](https://github.com/huggingface/transformers/blob/v4.57.6/docs/source/en/quantization/bitsandbytes.md)分别说明 NF4、计算数据类型和嵌套量化。

梯度 checkpointing 会保存选定的激活值，并在反向传播时重新计算，以节省内存；这是用计算量换内存。梯度累积会将多个 microbatch 合并到一次优化器更新中，但不需要同时保存这些 microbatch 的全部激活图。这两种功能都不会消除优化器状态。

### 总参数量与 MoE 活跃参数预算不同

[Qwen 模型卡](https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507)记载模型有**总计 30.5B 个参数，其中每个 token 激活 3.3B 个参数**，包含 48 层、128 个专家，每个 token 选择 8 个专家。活跃参数描述单个 token 的稀疏计算，并不表示只需加载 3.3B 个参数。

理想化的 `30.5 billion × 4 bits` 计算结果为 **15.25 十进制 GB**。这只是权重存储下限的说明，不是 GPU 内存占用预测。它未计入量化元数据、未量化张量、adapter、梯度、优化器状态、激活值和分配开销。因此无法证明特定单 GPU 实例一定能容纳模型。

## 4. 检查此模型的 adapter 目标

历史软件包固定了以下相关版本：

| 软件包 | 固定版本 |
|---|---|
| PyTorch | `2.8.0` |
| Transformers | `4.57.6` |
| PEFT | `0.17.1` |
| TRL | `0.24.0` |
| bitsandbytes | `0.48.2` |
| Accelerate | `1.10.1` |
| datasets | `3.6.0` |

在[固定版本的 Qwen3 MoE 实现](https://github.com/huggingface/transformers/blob/v4.57.6/src/transformers/models/qwen3_moe/modeling_qwen3_moe.py)中，专家是由 `gate_proj`、`up_proj` 和 `down_proj` 线性层组成的 `ModuleList`。注意力层使用 `q_proj`、`k_proj`、`v_proj` 和 `o_proj`。路由门是独立命名的 `gate`。

已提交的 `LoraConfig` 以这七个投影层的后缀名为目标。它不会因为 `gate_proj` 中包含单词 “gate” 就将 router 作为目标。相反，将列表替换为 `"all-linear"` 可能会包括其他线性模块，其中也可能包含 router；这是另一项实验。

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

根据已发布的模型配置，针对秩 16 执行基于源码的计算，四个注意力投影大约有 **13.37 million** 个 adapter 参数，所有专家中的三个投影则约有 **830.47 million** 个；合计 **843,841,536** 个。这是根据模型维度推算的数量，并非 GPU 实测结果。插入 adapter 后，应使用 `trainer.model.print_trainable_parameters()` 确认实际数量。

无需导入模型即可重现该计数。[模型配置](https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507/blob/main/config.json)列出了隐藏维度 2,048、头维度 128、32 个查询头、4 个键/值头以及专家中间维度 768。因此 Q 投影是 `2048 → 4096`，K/V 分别是 `2048 → 512`，O 投影是 `4096 → 2048`。每个专家包含两个 `2048 → 768` 投影和一个 `768 → 2048` 投影。

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

该计数假设使用已发布的 48 层模型专家布局和上述七个目标后缀，不包含其他可训练模块或偏置项。应将它作为与实际 adapter 清单对照的预期值，不能替代真实清单。

这解释了为什么对于大型 MoE 目标列表，“LoRA 使用的参数很少”是不完整的建议。对比仅注意力目标与注意力加专家目标，可能是一项有用的受控实验；但更改目标需要修改教学代码：当前 trainer 中的目标列表是硬编码的。

有些较新或不同的 MoE 实现使用原始的二维或三维 `nn.Parameter` 张量，而非 `nn.Linear` 专家。[PEFT 0.17.1 文档中的 `target_parameters`](https://github.com/huggingface/peft/blob/v0.17.1/docs/source/developer_guides/lora.md)支持这类情况，但也说明专家轴和多个 adapter 的限制。请检查所选模型和版本的实际实现；不要将面向参数目标的配方直接复制到这种基于模块的实现中。

## 5. 跟踪一条记录的 chat 格式和 loss mask

实际的[数据集加载器](https://github.com/Atom-oh/kubernetes-docs/blob/b89fc1d3334717031227a00a894a8c0927986ba3/examples/ai-ml/qwen-pii-finetuning/src/dataset.py)会返回对话式 **prompt/completion** 数据：

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

`train.py` 中未使用的 `format_training_text()` 函数会生成 `### Instruction` 文本。当前数据集路径**不会**使用它。不要将这个字符串格式说成是 `SFTTrainer` 实际接收的内容。

在 [TRL 0.24.0](https://huggingface.co/docs/trl/v0.24.0/en/sft_trainer)中，trainer 会对 prompt 和 prompt 加 completion 应用 tokenizer 的 chat template，并根据两者边界构建 completion mask。设置 `completion_only_loss=True` 时，prompt 位置的 label 为 `-100`，completion 位置则参与因果语言模型 loss。Padding 同样会被忽略。

### 空提取目标并不表示没有训练信号

不包含目标实体的文档会使用空 assistant content。其答案仍应以结束 assistant turn 的 token 结束。此模型的 [tokenizer 配置](https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507/blob/main/tokenizer_config.json)使用 `<|im_end|>` 作为 EOS，使用 `<|endoftext|>` 作为 padding。

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

此示例说明如何让模型针对负样本学习 EOS。实际模板可能包括更多 completion token，例如换行符。请验证真实的 tokenized 数据行；不要假定示例中的 prompt ID 或 completion 长度固定。

Instruct-2507 模型卡说明它是**非思考型**，不需要 `enable_thinking=False`。当前预测代码传入了该参数，但它不会将这个 checkpoint 变成推理模型。`assistant_only_loss=True` 是另一个选项，需要模板提供适当的 assistant mask 支持；对于此处单次响应的 prompt/completion 约定，它不是必需的。

### 首次训练前检查准备好的数据

以下 hook 应放在已授权且兼容环境中构建 trainer 之后。它会检查计数和 mask，不会打印源文本或解码后的标签。

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

还应检查截断前的 prompt 加 completion 长度，并确认答案 EOS 仍被保留。`max_length=1024` 限制整个训练序列的长度，而不只是文档长度。长 prompt 可能耗尽所有 token 预算，导致答案被移除。推理时的截断也可能隐藏 PII，而评估仍期待模型从完整文档中提取实体。

选择并记录明确策略：拒绝超长样本、仅缩短不重要的 prompt 指令，或分块处理源文本并更新标注约定。分块及增强后的衍生记录应与原文档家族保留在同一 split。不要只提高序列长度而不重新评估激活内存、microbatch 和推理输出长度。

## 6. 按执行顺序阅读固定版本的训练配置

下面是**代码阅读片段**，并非指示你启动被阻止的 GPU runtime。名称和参数对应 PEFT 0.17.1、Transformers 4.57.6 和 TRL 0.24.0。

首先在 `run_training()` 中找到以下阶段：

| 顺序 | 已提交入口点的行为 |
|---|---|
| 1 | 导入训练栈之前先运行支持性检查 |
| 2 | 解析配置和 seed，准备 MLflow，并读取数据集文件 |
| 3 | 加载量化模型/tokenizer，并在 test 上评估基线 |
| 4 | 准备 k-bit 训练，并构造 adapter 和对话式数据集 |
| 5 | 训练期间在 validation 上进行中间评估 |
| 6 | 保存模型输出并记录最终 adapter 文件 |
| 7 | 在 test 上评估调优后的模型并写入聚合结果 |

第 3 和第 7 阶段访问 test 是当前实现行为，并不是第 8 节建议的候选模型选择流程。

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

已提交的加载器使用 `AutoModelForCausalLM.from_pretrained(..., quantization_config=..., device_map="auto", torch_dtype=torch.bfloat16)`。必须检查自动设备放置结果；CPU/磁盘卸载不能替代对有效训练放置的证明。拟议的单 GPU 实验可以在确认内存足够后使用显式放置。本章不会更改加载器。

当前代码还设置了 `output_router_logits=True`。对于固定版本的 MoE 实现，路由器辅助损失可能计入报告的 loss。这并不意味着 router 是 LoRA 目标。比较运行结果时应记录此设置。

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

此片段显示已配置的**完整运行**值，并假定现有模型、tokenizer、数据集和输出目录均已准备好。这里有意展示 `max_length` 和 `processing_class`；未核对版本前，不要替换成旧式 `max_seq_length`/`tokenizer` 示例。固定版本的 `SFTConfig` 没有配置级 `chat_template_kwargs` 字段；0.24.0 支持按样本提供模板参数。

当前 tokenizer 已有正确 EOS。如课程需要显式呈现这一约定，可以在此 SFTConfig 中设置 `eos_token="<|im_end|>"`；此处省略并不表示当前 tokenizer 的 EOS 错误。

`config/experiment.yaml` 包含 `quantization`、`double_quant` 和 `compute_dtype`，但加载器目前将 NF4、双重量化和 BF16 硬编码。只更改这些 YAML 值并未真正执行 ablation。应保持这些值不变并说明原因，或另行审核教学代码修改，确保加载器实际使用所选配置。

### 从优化到生成提取结果

在经过验证的 GPU 环境中完成前置检查和检查 hook 后，已提交的流程会调用 `trainer.train()`，保存模型输出并评估调优后的模型。以下代码片段显示这些操作边界，并非 CPU 练习。

```python
# Code-reading excerpt: assumes an approved, constructed GPU trainer.
train_result = trainer.train()
trainer.save_model(str(output_dir))
trainer.model.config.use_cache = True
```

用于生成的 prompt 必须在 assistant 开始生成的前缀处停止；不要包含正确答案 completion。从生成的 ID 中删除 prompt token 后，才解析答案。以下是使用上文合成 `row` 和 `record` 的单记录诊断建议：

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

当前的 `_predict_records()` 会对样本进行左侧 padding 批处理，并启用截断。上面的 hook 则会拒绝单个过长 prompt，以显式展示教学所需边界。其 512 token 输出上限是另一项独立限制：较长的 TSV 答案仍可能被截断。除 prompt 长度外，还要检查响应是否正常结束以及格式是否正确。

## 7. 计算样本数、优化器更新次数和 epoch

对于普通数据并行训练：

```text
effective batch ≈ microbatch per device × accumulation × data-parallel workers
```

在已提交的单实例、单 GPU 示例中，计算结果为 `1 × 8 × 1 = 8`。梯度累积为 8 表示每 8 个 microbatch 执行一次优化器更新，不是每个 microbatch 包含 8 个样本。

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

因此，配置的烟雾训练会执行 10 次优化器更新，大约呈现 80 个样本。 “完整”训练会执行 80 次更新，大约呈现 640 个样本；在这些可整除且未打包的假设下，相当于 1,600 条记录 epoch 的 0.4 倍。“完整”只是模式标签，不代表已收敛或走完完整 epoch。

`max_steps` 决定更新预算。序列长度不同时，步数相同并不意味着监督 token 数或计算量相等。比较更长的上下文或增强数据集时，应记录看到的样本数和目标 token 数，而不只是运行时间和 loss。分布式尾部批次和打包方式需要额外计算；上面的算术不涵盖这些情况。

## 8. 区分小规模过拟合诊断与模型选择

在投入完整训练预算前，应先定义一个拟议诊断，使用 8–16 条**训练集**记录。包含简单正例、重复实体、格式变化和无 PII 例子。该子集必须与 validation 和锁定的 test 集分开。

runtime 迁移后，按以下顺序检查：模型加载成功；prompt/completion mask 正确；一次前向/反向步骤得到有限数值；预期 adapter 参数发生变化；模型更容易拟合小样本；使用相同基础模型重新加载 adapter 后能复现确定性解码。

例如，对 8 条记录采用有效批次大小 8 并执行 20 次优化器更新，相当于在这个小子集上训练约 20 轮。这是有意设置的诊断预算，并非完整数据集的建议。准确比较这 8 条记录的提取结果，并检查负例是否正确结束；仅 loss 降低并不是验收条件。

这是刻意设计的过拟合检查。成功只能说明训练流程可以学习这些样例，不能证明泛化能力、生产召回率或所有 PII 都会被移除。失败也很有用：先修复 mask、目标、数据对应关系或优化问题，再增大模型或数据集。

### 为什么当前 trainer 不是安全的超参搜索循环

已提交的 trainer 会读取 test 文件，并且每次运行（包括 smoke）都在**运行前和运行后**评估 test。它会在 trainer 训练期间使用 validation 做中间评估，但每次都会在 test 上计算最终基线/调优指标。选择超参数时不要反复查看 test 结果。

作为教学调参流程，应明确标注一项修改：使用 smoke 子集进行执行诊断，使用 validation 比较候选模型。普通调参运行应无法访问 test；冻结所选配置后，才进行最终基线/候选模型 test 比较。[PII 评估与发布实战](07-pii-evaluation-release.md)进一步说明了这种分离方式。

| 实验 | 保持不变 | 有意更改 | 根据 validation 选择 |
|---|---|---|---|
| Adapter 容量 | 数据、目标层、学习率、token 预算 | 秩，例如 8 与 16，并说明缩放策略 | 召回率、残余 PII、过度脱敏和训练稳定性 |
| 目标范围 | 数据、秩、解码和预算 | 仅注意力层与当前注意力+专家层目标 | 相较于可训练参数量和实测内存所带来的质量收益 |
| 优化 | 数据、目标层、秩、序列策略 | 每次只改变一个学习率选择 | loss 走势和提取指标，而不只是 loss |
| 序列策略 | 评估记录和标签约定 | 拒绝/分块策略，或有理据支持的更大 token 预算 | 长文档覆盖率及截断率 |
| 数据增强 | 原始文档家族和评估集 | 只使用一种训练集转换方式 | 稀有类型、格式和负例行为 |

这些行描述的是实验设计，不是已实现的 CLI 开关，也不是推荐的最佳数值。增强数据的衍生记录必须与源文档家族放在一起。分开文档家族并不自动保证精确文本、实体、模板或领域完全隔离；[数据增强实战](06-data-augmentation-workshop.md)会明确审计这些内容。

数据增强实战的 CPU 练习使用单独数据集。此处的 1,600 条记录计算依据历史训练配置；不要将这些数字直接套用到新实验的输出。

## 9. 将实验映射到 SageMaker AI

使用[实际启动器](https://github.com/Atom-oh/kubernetes-docs/blob/b89fc1d3334717031227a00a894a8c0927986ba3/examples/ai-ml/qwen-pii-finetuning/launch/sagemaker_train.py)，将本地概念与作业输入/输出对应起来。

| 步骤 | 当前映射 | 应检查的证据 |
|---|---|---|
| 本地配置 | `config/experiment.yaml` 和 `requirements.lock` | 配置、源码和依赖版本 |
| 源码包 | `generated/source.tar.gz` 包含源码/配置/requirements | 软件包清单及 SHA-256；不应递归打入凭据/数据 |
| S3 输入 | 实验分别使用 `source/` 和 `dataset/` 前缀 | 上传对象哈希，以及预期账户/bucket/prefix |
| 作业内源码 | `/opt/ml/code/config/experiment.yaml`；`SAGEMAKER_PROGRAM=src/train.py` | Toolkit 调用及配置文件是否存在 |
| 数据集 channel | 一个名为 `dataset` 的 File-mode channel | `/opt/ml/input/data/dataset/{train,validation,test}.jsonl` 及 manifest |
| Trainer 评估 | 训练期间使用 validation；当前最终比较使用 test | 实际 split ID/哈希以及两者的区别 |
| MLflow | 配置/版本/manifest 文件、聚合指标及最终 adapter 文件 | 运行身份、artifact 是否可用及 client/App 兼容性 |
| SageMaker 模型输出 | 当前 `output-dir=/opt/ml/model` | 最终目录内容及 S3 模型 artifact URI |

Channel 名称决定输入路径。channel 名称为 `dataset` 并不表示其中所有内容都是“训练数据”：该 channel 包含三个不同 split。训练前应重新计算并比较观察到的文件哈希；仅记录 manifest 并不能证明实际加载的文件与之匹配。

### 理解哪些文件会被保存

当前 SFT 输出目录是 `/opt/ml/model/checkpoints`，因为 checkpoint 位于 `output_dir` 下。SageMaker 会打包模型目录并上传，因此生成的模型 artifact 可能同时包含这些 checkpoint、最终 adapter 和 JSON 文件。MLflow 显式的 adapter 文件 allowlist 不会改变 SageMaker 的目录打包行为。

若要采用更清晰的拟议布局，应将最终 adapter 文件放在 `/opt/ml/model`，聚合输出放在 `/opt/ml/output/data`，可恢复 checkpoint 放在 `/opt/ml/checkpoints`。要同步 checkpoint 到 S3，需要相应的作业配置；仅创建本地目录并不构成备份。请参见 [AWS 存储路径表](https://docs.aws.amazon.com/sagemaker/latest/dg/model-train-storage-env-var-summary.html)和[训练输出约定](https://docs.aws.amazon.com/sagemaker/latest/dg/your-algorithms-training-algo-output.html)。

Adapter 不是可以独立替代基础模型的文件。重新加载需要正确的基础模型/版本、tokenizer、adapter 配置和兼容 runtime。当前代码没有固定模型 revision；应在单独审核的可复现性改进中记录这一版本。

## 10. 先诊断作业阶段，再更改超参数

SageMaker 状态与模型阶段诊断回答的是不同问题。`SecondaryStatus` 可以表示正在下载、训练或上传；应用可能正在加载权重、评估基线或保存 adapter，但作业仍显示 `Training`。

以下是针对**现有且已授权作业**的只读诊断命令，并非本实战执行的命令：

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

查看错误详情前应妥善保护其隐私。查看 `/aws/sagemaker/TrainingJobs` 下该作业的日志流及范围受限的日志窗口；不要导出无关作业或训练示例。AWS 文档参见 [SecondaryStatus 状态转换](https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_SecondaryStatusTransition.html)和 [CloudWatch 日志记录](https://docs.aws.amazon.com/sagemaker/latest/dg/logging-cloudwatch.html)。

今后的教学 trainer 应添加只包含聚合信息的阶段标记：数据已验证、模型已加载、基线已完成、adapter 已插入、首次反向传播已完成、优化已完成、artifact 已保存和评估已完成。这样即使不记录源文档，也能诊断停滞阶段。

| 症状 | 首先要区分的问题 | 可采取的下一步措施 |
|---|---|---|
| 模型加载前失败 | Runtime guard、软件包/toolkit 故障或路径缺失 | 查看阶段和确切配置/channel 映射；不要调秩 |
| 加载时 OOM | 基础权重/放置与优化器内存 | 检查模型总大小、量化、未量化张量和实际放置 |
| 反向传播时 OOM | 激活值与 adapter/优化器状态 | 减少 microbatch/序列预算；确认 checkpointing 和目标范围 |
| Loss 为 NaN | 错误目标与数值/优化问题 | 检查非零监督 label、有限数值、BF16 支持和学习率 |
| Loss 下降但召回率仍低 | 格式学习与实体覆盖的区别 | 按类型、语言、长度和负/正样本检查 validation |
| 输出是散文或格式错误 TSV | Chat template/EOS/masking 与任务歧义 | 增加训练步数前，验证实际准备的样例和解码约定 |
| 解析/往返得分高但仍有 PII | Parser 宽松策略与可逆替换 | 检查残余 PII 和实体召回；不要把 parser 成功当成隐私保护成功 |
| 作业完成但结果无法加载 | Artifact 目录错误或基础模型/revision 不匹配 | 检查 artifact 内容，并单独执行 adapter 重新加载验证 |

当前 `peak_gpu_memory_bytes` 测量的是模型加载后重置峰值统计时，在默认 CUDA 设备上观测到的 PyTorch 已分配内存峰值。它不是 GPU 总内存、模型加载峰值或多设备内存之和。未来报告测量值时，应精确标注含义。

## 11. 将 runtime 迁移视为经过测试的一组配置

[AWS DLC 支持策略](https://aws.github.io/deep-learning-containers/reference/support_policy/)和[映像目录](https://aws.github.io/deep-learning-containers/reference/available_images/)已于 2026 年 9 月 15 日核查。不要混淆旧 `pytorch-training` 映像系列与新的 `pytorch` 系列。

| 目录条目 | SageMaker tag（不含 Registry 主机名） | Python / OS | 补丁支持结束时间 |
|---|---|---|---|
| 当前历史示例 | `pytorch-training:2.8.0-gpu-py312-cu129-ubuntu22.04-sagemaker` | 3.12 / Ubuntu 22.04 | 2026-08-06 |
| 新系列 2.11 | `pytorch:2.11.0-cu130-amzn2023-sagemaker` | 3.12 / AL2023 | 2027-04-30 |
| 新系列 2.12 | `pytorch:2.12.1-cu130-amzn2023-sagemaker` | 3.12 / AL2023 | 2027-07-02 |
| 新系列 2.13 | `pytorch:2.13.0-cu133-amzn2023-sagemaker` | 3.12 / AL2023 | 2027-07-20 |

这些都是已验证的目录条目，**并不代表已验证历史 `src/train.py`/托管 MLflow 路径的替代方案**。单独的 `src/train_execution.py` 路径通过 2.11 GPU 烟雾测试的情况记录在[执行记录](README.md#sagemaker-execution-readiness)中；2.12 和 2.13 仍只是尚未执行的目录参考。AWS 还提醒，Ubuntu 系 PyTorch 2.8–2.10 无法完整打补丁，并建议使用 AL2023 PyTorch 2.11 或更高版本。历史启动器同时固定了旧仓库名和 tag；只替换版本号并不足够。

迁移时必须协调映像仓库/tag/digest、区域可用性、Python、CUDA/驱动/架构、PyTorch、HF/PEFT/TRL/bitsandbytes 依赖、训练 toolkit 以及 MLflow client/service。将当前 `torch==2.8.0` 锁定版本安装到较新的 DLC 中，可能会撤销预期的框架迁移。

只有审核完上述选择后，授权 GPU 预检才应测试实际 CUDA/BF16 支持、量化加载、预期目标/dtype、前向/反向步骤、有限 loss、adapter 更新以及保存/重新加载。**仅描述测试流程不能证明测试已实际成功**。实际 2.11 证据应以单独记录为准，并保留历史路径的防护检查。

## 12. 检查理解情况

1. 单 worker 的 microbatch 为 1、梯度累积为 8 时，80 次更新相当于呈现了多少样本？**约 640 条**，前提是未打包且相关数量可整除。
2. “活跃 3.3B”是否表示只需为 3.3B 参数分配内存？**不是**。它描述稀疏计算；仍需考虑全部权重和训练状态。
3. 无 PII 文档应教模型什么？**以 assistant turn 结束 token 结尾的有效空提取响应**，而非全被忽略的 label 序列。
4. 能否每次运行后依据 test 分数选择秩？**不能**。应依据 validation 选择，冻结候选方案，然后只在最终比较中使用锁定的 test 集。
5. 往返测试成功是否证明 PII 已移除？**不能**。它只证明替换路径可逆；漏掉的 PII 可能仍未被处理。
6. DLC tag 受支持是否足以启用当前启动器？**不足**。仓库、依赖、toolkit、硬件和集成约定必须形成经过验证的一组配置。

## 主要参考资料

以下参考资料均于 **2026 年 9 月 15 日**核查。代码阅读示例以带版本的来源为准。

- [LoRA 论文](https://arxiv.org/abs/2106.09685)和 [QLoRA 论文](https://arxiv.org/abs/2305.14314)
- [PEFT 0.17.1 LoRA 指南](https://github.com/huggingface/peft/blob/v0.17.1/docs/source/developer_guides/lora.md)和 [k-bit 准备源码](https://github.com/huggingface/peft/blob/v0.17.1/src/peft/utils/other.py)
- [Transformers 4.57.6 bitsandbytes 量化指南](https://github.com/huggingface/transformers/blob/v4.57.6/docs/source/en/quantization/bitsandbytes.md)
- [bitsandbytes 0.48.2 4 位模块](https://github.com/bitsandbytes-foundation/bitsandbytes/blob/0.48.2/docs/source/reference/nn/linear4bit.mdx)
- [TRL 0.24.0 SFT 指南](https://huggingface.co/docs/trl/v0.24.0/en/sft_trainer)、[SFTConfig](https://github.com/huggingface/trl/blob/v0.24.0/trl/trainer/sft_config.py)和 [SFTTrainer](https://github.com/huggingface/trl/blob/v0.24.0/trl/trainer/sft_trainer.py)
- [Qwen 模型卡](https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507)、[模型配置](https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507/blob/main/config.json)和[固定版本的 Transformers 实现](https://github.com/huggingface/transformers/blob/v4.57.6/src/transformers/models/qwen3_moe/modeling_qwen3_moe.py)
- [AWS DLC 支持](https://aws.github.io/deep-learning-containers/reference/support_policy/)和[可用映像](https://aws.github.io/deep-learning-containers/reference/available_images/)
- [SageMaker 存储/环境变量](https://docs.aws.amazon.com/sagemaker/latest/dg/model-train-storage-env-var-summary.html)和[训练输出](https://docs.aws.amazon.com/sagemaker/latest/dg/your-algorithms-training-algo-output.html)

下一步：[数据增强实战](06-data-augmentation-workshop.md)

## 测验

请完成 [QLoRA 微调实战测验](../../quizzes/ai-ml/sagemaker-ai/05-qlora-finetuning-workshop-quiz.md)，检查相关概念和计算。
