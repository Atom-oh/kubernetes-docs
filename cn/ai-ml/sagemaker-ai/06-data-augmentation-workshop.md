# 工作坊：合成 PII 数据与数据增强

> **最后更新**：2026 年 9 月 15 日

此合成数据练习使用 Python 3.12，不需要模型权重、AWS 账户或 GPU。

数据增强应添加**系统实际会失败的输入条件**，而不只是增加文件数量。复制文档或生成错位标签，可能增加训练工作，却让评估更不可信。

先定义标注策略，再拆分文档系列，之后再执行保留标签含义的转换。先完成小型 CPU 练习，再用最后几节规划更大的领域数据集。

## 1. 定义学习目标

源文本、实体标注和模型目标必须一致。

```json
{
  "id": "synthetic-train-example",
  "source_text": "신청인 김가상, 이메일 synthetic.01@example.com",
  "entities": [
    {"type": "PERSON", "original": "김가상"},
    {"type": "EMAIL", "original": "synthetic.01@example.com"}
  ],
  "target_tsv": "PERSON\t김가상\nEMAIL\tsynthetic.01@example.com"
}
```

`source_text` 是输入文档；`target_tsv` 是作为监督信号的 assistant 补全结果。`entities` 用于审计和评估。这与训练模型生成整篇脱敏文档不同。

首先编写标注指南。

| 决策 | 示例 | 未明确时的失败情况 |
|---|---|---|
| 类型语义 | 个人联系方式属于 PHONE；根据本策略，公司总机属于负例 | 相似字符串被赋予互相矛盾的标签 |
| 精确边界 | 保留源文本中的姓名空格和电话号码分隔符 | 源文本 / 目标不匹配 |
| 按上下文分类 | 区分证件号码和账户号码 | 将所有数字都视为敏感信息 |
| 重复 / 重叠 | 重复姓名、地址中的姓名 | 标注与替换结果不一致 |
| 无实体 | `entities=[]`、`target_tsv=""` | 模型学习对每篇文档都提取内容 |
| 不确定情况 | 无法读取或不支持的输入、上下文含糊 | 将猜测的金标引入训练集 |

公司总机规则只是本示例的策略，并非所有组织都适用的通用规则。文档级 `(TYPE, ORIGINAL)` 标签无法分别标注同一字符串的不同出现位置。如果不同位置含义不同，应同步扩展 offset / span schema、评估器和替换代码。

## 2. 区分合成数据和数据增强

- **合成**：通过模板、合成值或生成模型创建新文档。
- **数据增强**：更改获批准训练样例的值、措辞、布局或噪声，同时保留预期标签。
- **验证**：检查转换后的源文本和目标内容是否仍一致。成功生成并不保证标签正确。

也应将外部模型输出视为候选数据。不要默认将源值发送给外部 API，也不要未经审查就将生成结果视为金标。

## 3. 先拆分数据系列，再进行增强

将原文及其译文、OCR 变体和释义文本归入同一个 `family_id`。先把数据系列分配到 train / validation / test，再仅针对训练集系列生成派生样例。

```text
family-001 → train      → base + context + layout
family-002 → validation → base
family-003 → test       → base
```

增强后再随机拆分，可能会将几乎相同的文档分别放入训练集和测试集。分组键需要有来源记录；仅仅分配一个新记录 ID 并不会产生独立客户或来源系列。

| 拆分维度 | 用于防止的泄漏 | 其他评估 |
|---|---|---|
| 系列 | 原始样例及其派生样例跨数据集拆分 | 新转换方式 / 噪声 |
| 实体 / 客户 | 同一人物 / 标识符出现在拆分两侧 | 未见过的姓名、标识符、客户 |
| 模板 | 记住布局 | 未见过的模板 |
| 领域 / 时间 | 依赖某种业务 / 时间分布 | 新领域或未来时间段 |

此 CPU 练习检查**系列隔离和 NFC 规范化后的完全相同源文本重复项**。部分姓名、模板和领域会重复；这并不能证明实体 / 模板 / 领域相互独立。

## 4. 运行小型数据增强练习

从仓库根目录开始。生成器只接受一个尚不存在的输出目录，因此不要把已经创建的目录本身传给 `--output-dir`。

```bash
cd examples/ai-ml/qwen-pii-finetuning
mkdir -p "${XDG_CACHE_HOME:-$HOME/.cache}/qwen-pii-lab"
export PII_AUG_RUN="$(mktemp -d "${XDG_CACHE_HOME:-$HOME/.cache}/qwen-pii-lab/run.XXXXXX")"
export PII_AUG_DIR="$PII_AUG_RUN/dataset"

python3 -m data.augmentation_lab --output-dir "$PII_AUG_DIR" --seed 42
python3 -m data.augmentation_lab --audit-dir "$PII_AUG_DIR"

python3 - <<'PY'
import json
import os
from collections import Counter
from pathlib import Path

root = Path(os.environ["PII_AUG_DIR"])
for split in ("train", "validation", "test"):
    rows = [
        json.loads(line)
        for line in (root / f"{split}.jsonl").read_text().splitlines()
    ]
    print(split, {
        "records": len(rows),
        "families": len({r["provenance"]["family_id"] for r in rows}),
        "negative": sum(not r["entities"] for r in rows),
        "languages": dict(Counter(r["language"] for r in rows)),
    })
PY
```

输出文件为 `train.jsonl`、`validation.jsonl`、`test.jsonl` 和 `augmentation-manifest.json`。

| 拆分 | 数据系列 | 记录 | 韩语 / 英语 | 负例记录 |
|---|---:|---:|---:|---:|
| train | 24 | 72 | 36 / 36 | 36 |
| validation | 8 | 8 | 4 / 4 | 4 |
| test | 8 | 8 | 4 / 4 | 4 |

40 个数据系列按语言和正 / 负例进行分层，每个分层中分别分配 6 / 2 / 2 个数据系列。训练集包含基例和两个变体；验证 / 测试集只保留基例。50% 负例和 50/50 语言配比是为了使练习便于比较；它们并不是生产数据中正负例的比例估计。

紧凑型练习涵盖 PERSON、EMAIL 和 PHONE。它的用途不同于历史上的九类型生成器。该小型集合无法评估 RRN、CARD 或其他未包含类型的效果。

## 5. 查看来源链和转换

保留现有 loader 字段，并添加 `provenance`。

| 字段 | 含义 |
|---|---|
| `id` | 每个变体的唯一 ID |
| `language`、`domain` | 汇总 / 错误分析类别 |
| `provenance.family_id` | 原始记录及其变体所属的同一系列 |
| `provenance.split` | 在变体生成前确定的拆分 |
| `provenance.parent_id` | 变体派生自哪个基例记录 |
| `provenance.augmentation` | 应用的转换名称 |

来源信息和正 / 负例状态是审计元数据。与现有 loader 一样，user prompt 中只能放入 `source_text`；不要附加拆分、是否存在金标或金标提示。将 `target_tsv` 放入经过监督的 assistant 补全结果。

可执行示例包含两种变体：

1. **上下文包装**：更改合成周围上下文，但保留 PII 值和标注含义。
2. **布局 / Unicode**：更改字段顺序 / 布局，并对韩语变体使用 NFD。将源文本和原始值一并渲染，然后按照新源文本中的顺序重新生成 TSV。

NFD 使用分解表示，包括韩文 jamo；NFC 使用规范组合表示。视觉相同的文本可能有不同的字节，因此精确源文本比较前会先规范化为 NFC。

转换后的负例记录仍保持空标注和空目标。重新排序或 Unicode 规范化不得凭空生成实体。这些变体并不声称能够再现实验室之外真实扫描器或 OCR 引擎的噪声分布。

## 6. 对实体替换重新渲染源文本和标签

以下是创建新训练候选项时，同类型合成值替换的最小模式。它不是通用的无限制字符串替换函数。

```python
def render_training_candidate(person, email):
    source = f"신청인: {person}\n이메일: {email}"
    entities = [
        {"type": "PERSON", "original": person},
        {"type": "EMAIL", "original": email},
    ]
    target = "\n".join(
        f"{entity['type']}\t{entity['original']}" for entity in entities
    )
    assert all(entity["original"] in source for entity in entities)
    return {"source_text": source, "entities": entities, "target_tsv": target}

base = render_training_candidate("김가상", "synthetic.base@example.com")
variant = render_training_candidate("이샘플", "synthetic.variant@example.com")
assert base["source_text"] != variant["source_text"]
```

真实的数据增强流水线应使用经过批准的训练实体库，并记录系列、父记录、seed 和操作版本。将留出集的值或失败样例导入该实体库，可能破坏数据隔离策略。此独立教学示例不是前述 CLI 会自动运行的第三种操作。

## 7. 使用明确的标签检查来扩展操作

| 方法 | 目标失败情况 | 必需检查 |
|---|---|---|
| 同类型替换 | 记住姓名 / 数字 | 保留类型并更新所有出现位置 / 金标 |
| 布局渲染 | 表格、表单和客服记录 | 字段顺序 / TSV 一致性及字段遗漏检查 |
| 有界 OCR / 间距变换 | 分隔符、换行、Unicode 形式 | 确认转换后源文本中的金标和边界 |
| 上下文改述 | 依赖单一句式模板 | 检查 PII 的新增 / 删除和语义一致性 |
| 回译 | 措辞变化有限 | 检查更改后的姓名 / 地址 / 数字并重新标注 |
| 困难负例 | 将证件号码 / 金额误分类 | 表面形式相似但上下文不同的样例 |
| 稀有类型扩充 | RRN / CARD 样例稀少 | 检查每种受支持类型的数量和上下文多样性 |
| 长文 / 边界案例 | 截断和分块边界漏检 | token 长度、offset、重复项 / 边界 |
| 嵌入式指令 | 将源文本当成指令 | 将源文本视为数据；保留 TSV 契约 |

改述和回译可能保留自动检查无法发现的标注错误。源文本中存在对应字符串，并不能证明其语义正确或金标覆盖完整。纳入训练前，应先审查并批准候选数据。

## 8. 理解审计拒绝的情况

`--audit-dir` 会检查本实验生成数据的契约：

- 文件哈希 / 清单以及拆分 / 语言 / 负例计数。
- 重复 ID 和 NFC 规范化后的完全相同源文本。
- 数据系列拆分归属，以及父记录 / 转换关系。
- 错放在 validation / test 中的训练变体。
- 允许的标签、源文本匹配，以及 entities / TSV 一致性。
- 与基于 seed 的确定性再生成结果一致。

最后一项检查即使重新计算文件哈希，也可能拒绝漏掉的金标。这是**针对固定合成练习的可复现性检查**，不是适用于任意客户文档的通用金标验证器。哈希值不是能认证数据生产者身份的签名。

在训练前检查这些条件，能避免之后把数据污染误诊为模型问题。近似重复项、标注语义、tokenizer 长度和完整 PII 覆盖情况仍然需要单独检查。

## 9. 解读历史上的 2,200 条记录语料

[第 2 部分](02-pii-data-tokenization.md)保留了 generator 1.0.0、seed 42 和原始拆分哈希。本次审查使用 CPU 重新生成数据，结果复现了这些哈希。

对历史语料中的完整源文本进行 NFC 规范化后比较，发现以下交集：

| 拆分组合 | 相同 NFC 源文本数 |
|---|---:|
| train / validation | 22 |
| train / test | 36 |
| validation / test | 9 |

共有 51 个唯一源文本组跨越两个或更多拆分。逐对交集会重复计入同时存在于三个拆分的源文本，因此交集之和不等于唯一组总数。这说明不能将历史语料重新标记为无泄漏评估集。

新练习不会覆盖历史数据，也不会发布修改后的模型性能。包含九种类型的生产数据集需要记录系列 / 客户 / 模板来源并生成新清单 / 评估版本，而不能盲目地按旧值 / 模板随机重分数据。

## 10. 将数据扩展为 SageMaker 输入版本

实验 JSONL 包含现有 `src.dataset` prompt / completion 辅助函数使用的字段。其 augmentation manifest 不能直接替代上传器的 `dataset-manifest.json`。

真实训练版本应一起准备以下内容：

1. 获批的 train / validation / test 拆分，以及标注 / 数据增强策略。
2. 包含实际计数和 SHA-256 值的上传器输入清单。
3. 反映数据集大小、模型和训练预算的 `config/experiment.yaml`。
4. 包含该配置以及相匹配的本地提交配置的源代码包。
5. 已验证受支持的运行时，以及作业内观察到的输入哈希 / 计数。

当前 bundler / uploader 使用固定的软件包路径。生成 `--output-dir` 目录并不会自动将其接入 SageMaker 训练。应在单独的工作副本中集成并验证新的数据集版本，然后按照 [QLoRA 工作坊](05-qlora-finetuning-workshop.md)和[执行约定](03-sagemaker-mlflow-execution.md)操作。

应使用相同验证集、解码方式和对比预算，比较原始数据与增强数据上的训练效果。数据大小 / 长度发生变化时，即使步数相同，看到的样例数或 token 数也可能不同；还应记录样例 / token 预算。

## 检查理解情况

1. 为什么增强后再拆分有风险？**同一源文档的变体可能跨越训练集 / 留出集边界。**
2. 一个新 ID 是否消除了客户泄漏？**没有；还要检查客户和来源链。**
3. 姓名更改后，TSV 能保持不变吗？**不可以；源文本和金标必须同时更新。**
4. 该练习能证明模型在未见模板上的表现吗？**不能；模板有重复，也没有评估模型。**
5. 如果更多数据增强反而降低质量怎么办？**检查标签、重复项、分布变化和训练预算，并在验证集上进行比较。**

## 参考资料

- [训练 / 测试集隔离和预处理泄漏](https://scikit-learn.org/stable/common_pitfalls.html)
- [分组交叉验证](https://scikit-learn.org/stable/modules/cross_validation.html)
- [Dai 和 Adel：用于 NER 的数据增强](https://aclanthology.org/2020.coling-main.343/)
- [CheckList：NLP 模型行为测试](https://aclanthology.org/2020.acl-main.442/)
- [历史数据和替换实现](02-pii-data-tokenization.md)

下一步：[QLoRA 训练](05-qlora-finetuning-workshop.md) · [评估和脱敏](07-pii-evaluation-release.md)

[工作坊测验](../../quizzes/ai-ml/sagemaker-ai/06-data-augmentation-workshop-quiz.md)
