# 工作坊：评估 PII 模型和脱敏流水线

> **最后更新**：2026 年 9 月 15 日

可执行示例使用合成记录和手工构造的 CPU 预测值。示例中的数字并非经过训练的模型性能。

训练损失下降并不能证明 PII 删除效果良好。模型可能识别出姓名，却漏掉电子邮件地址；也可能屏蔽标注策略认为不敏感的证件号码。本章会同时评估**实体提取和最终替换结果**，并将错误与下一轮数据实验关联起来。

请先阅读 [QLoRA 工作坊](05-qlora-finetuning-workshop.md)和[数据增强工作坊](06-data-augmentation-workshop.md)。命令从仓库根目录运行，并使用 Python 3.12。

## 1. 区分模型和处理流程的职责

示例模型会输出 `TYPE<TAB>ORIGINAL` 候选项，而不是重写整篇文档。

| 阶段 | 输入 → 输出 | 检查内容 |
|---|---|---|
| 提取 | 源文本 → 类型 / 值候选项 | 漏检、类型错误、凭空生成的值 |
| 校验 | 候选项 → 允许且与源文本匹配的候选项 | 语法、长度、允许类型、源文本匹配 |
| 替换 | 源文本 / 候选项 → 脱敏文本、映射、span | 重复、覆盖不全、冲突、重叠 |
| 残余检查 | 脱敏结果 → 批准或转人工审查 | 独立规则 / 检测器、策略、不支持的输入 |
| 交付 | 已批准文档 → 下游系统 | 排除映射、访问控制、日志范围 |

源文本匹配只证明候选项出现在源文本中，不能证明其语义类型正确，也不能证明不存在其他 PII。组合使用多个检测器，也不代表它们的错误彼此独立。

`pseudonymize_text()` 会创建可逆的令牌映射。保留 `[PERSON_1]` 的映射与移除某个值但不提供还原功能，目的不同。仅丢弃映射并不能证明剩余上下文无法识别个人。

## 2. 分配训练集、验证集和最终测试集的职责

1. **训练集**：更新参数并执行训练数据增强。
2. **验证集**：选择 rank、学习率、epochs / steps、数据混合方式和输出规则。
3. **锁定的测试集**：评估选定的模型和处理策略。
4. **挑战集**：单独检查 OCR、长文档、不熟悉的模板、稀有类型、嵌入式指令和其他困难情况。

如果最终测试集的失败情况影响了下一轮模型选择，该测试集就已参与开发。应记录此变化并准备另一个评估版本。应记录数据是按文档系列、客户、模板、时间还是其他维度划分。

**历史版 `src/train.py` 会在每次运行中使用 `test_records` 评估基线和调优后的预测。不要原样把这种做法用于反复运行** HPO。调优实现应使用验证集来选择候选项，并单独记录最终测试步骤。下面的 CPU 练习不会运行该启动器。

## 3. 在 CPU 上复现“F1 较高但仍有问题”

使用两篇文档：

- 一篇正例文档，其中合成姓名和 `example.com` 电子邮件已标注。
- 一篇负例文档，其中的证件号码根据本策略不属于 PII。

基线模型只找出姓名。候选模型找出了姓名和电子邮件，但错误地把负例文档中的证件号码标注为账户。这些预测值是手工构造的，没有调用模型，因此可以检查指标计算过程。两个语言版本使用相同的合成韩语样例。

```bash
cd examples/ai-ml/qwen-pii-finetuning
mkdir -p "${XDG_CACHE_HOME:-$HOME/.cache}"
export PII_EVAL_DIR="$(mktemp -d "${XDG_CACHE_HOME:-$HOME/.cache}/pii-evaluation.XXXXXX")"
python3 - <<'PY'
import json
import os
from pathlib import Path

out = Path(os.environ["PII_EVAL_DIR"])
records = [
    {
        "id": "positive-1",
        "source_text": "담당자 김가상, 이메일 synthetic.ko.01@example.com",
        "entities": [
            {"type": "PERSON", "original": "김가상"},
            {"type": "EMAIL", "original": "synthetic.ko.01@example.com"},
        ],
        "target_tsv": "PERSON\t김가상\nEMAIL\tsynthetic.ko.01@example.com",
    },
    {
        "id": "negative-1",
        "source_text": "문서번호 DOC-2026-001의 처리 상태를 확인합니다.",
        "entities": [],
        "target_tsv": "",
    },
]
baseline = [
    {"id": "positive-1", "content": "PERSON\t김가상", "parse_success": True},
    {"id": "negative-1", "content": "", "parse_success": True},
]
candidate = [
    {
        "id": "positive-1",
        "content": records[0]["target_tsv"],
        "parse_success": True,
    },
    {
        "id": "negative-1",
        "content": "ACCOUNT\tDOC-2026-001",
        "parse_success": True,
    },
]
for name, rows in (
    ("gold", records), ("baseline", baseline), ("candidate", candidate)
):
    with (out / f"{name}.jsonl").open("x", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
PY

for phase in baseline candidate; do
  python3 -m src.evaluate \
    --test-jsonl "$PII_EVAL_DIR/gold.jsonl" \
    --predictions-jsonl "$PII_EVAL_DIR/$phase.jsonl" \
    --output-json "$PII_EVAL_DIR/$phase-metrics.json" \
    --environment cpu-demo --phase "$phase-demo" \
    --model-id synthetic-fixture-no-model \
    --duration-seconds 0 --hourly-usd 0
done

python3 - <<'PY'
import json
import os
from pathlib import Path

out = Path(os.environ["PII_EVAL_DIR"])
for phase in ("baseline", "candidate"):
    m = json.loads((out / f"{phase}-metrics.json").read_text())["metrics"]
    print(phase, json.dumps({
        "entity": m["entity"],
        "leaked_documents": m["documents"]["leaked"],
        "extra_pairs": m["entities"]["over_redacted"],
        "round_trip": m["tokenization"]["round_trip_rate"],
    }))
PY
```

`--test-jsonl` 是评估 CLI 的参数名称。此处指向的是手写练习文件，并非生产环境的最终留出测试集。

预期结果：

| 指标 | 基线 | 候选 |
|---|---:|---:|
| TP / FP / FN | 1 / 0 / 1 | 2 / 1 / 0 |
| Precision | 1 | 2/3 |
| Recall | 1/2 | 1 |
| Entity F1 | 2/3 | 0.8 |
| 存在未覆盖标注的文档 | 2 篇中有 1 篇 | 2 篇中有 0 篇 |
| 额外提取的键值对 | 0 | 1 |
| 往返还原率 | 1 | 1 |

候选模型提高了 F1，但也增加了对证件号码的误屏蔽。两组预测都能正确往返还原：**成功还原不能代替良好的 PII 检测质量**。运行时间和每小时价格为零只是因为此处使用手动构造的样例，并不表示 GPU 训练无需成本。

## 4. 检查每个指标的统计单位

软件包的 `entity` 和 `per_type` 指标会比较每篇文档中的 `(TYPE, ORIGINAL)` 集合。每篇文档中重复的相同键值对只计一次。这不是基于独立 span 标注的 NER F1。

| 指标 | 用途 | 应检查的局限 |
|---|---|---|
| Per-type recall | 找出漏掉的 PII 类别 | 报告评估的稀有实体数量 |
| Per-type precision | 识别被错误屏蔽的非敏感文本 | 需要一致的标注策略 |
| 文档泄漏率 | 存在任一未覆盖标注的文档比例 | 无法测量金标中不存在的 PII |
| 实体泄漏率 | 对金标值的所有匹配位置进行覆盖率评估 | 根据值搜索推断 span，而不是使用 offset 金标 |
| `over_redaction_rate` | FP / 预测键值对 | 不代表不必要删除的字符比例 |
| `hallucination_rate` | 不在源文本中的允许 TSV 候选项 | 分母不包括不允许的类型和普通文本 |
| 解析成功率 | 调用方提供的格式处理状态 | 当前辅助程序接受仅含部分有效行的某些输出 |

应设计严格的服务端解析器，对每一行进行验证，并针对格式错误的行、被截断的补全结果和输入长度超限返回明确失败。静默丢弃错误行不能变成“未发现 PII”。当前的 `parse.success_rate` 并不能证明已经实现严格行为。

若在线文档没有金标注释，就无法获得相同的基于金标的泄漏率。应观测经过审查的样本、残余检测器，以及选择拒答 / 人工审查的比例，同时明确每个指标实际测量的内容。

## 5. 将错误转化为下一轮数据实验

应在访问受控的评估环境中调查文档级错误。普通日志应记录错误类别、长度区间、语言、模板 ID 和汇总值，而不是源文本。

| 观察到的错误 | 首先检查 | 下一项实验 |
|---|---|---|
| 找到姓名但漏掉账户信息 | 各类型计数和缺失的标注 | 添加包含账户上下文的训练样例 |
| 无法识别带空格的姓名或 OCR | 源文本 / 标签表面形式是否匹配 | 同步增强源文本和标签 |
| 将证件号码标为账户 | 负例覆盖和上下文对比 | 添加数字上下文匹配的正 / 负例 |
| 漏掉长文档末尾的 PII | Prompt 截断和补全预算 | 评估分块边界、重叠及 offset 重建 |
| 对不熟悉的姓名效果差 | 训练集 / 测试集间的实体重叠 | 按实体留出进行评估并新增训练样例系列 |
| 对新布局效果差 | 模板拆分 | 留出模板评估并使用获批准的训练模板 |
| 遵循源文本中嵌入的指令 | 将文档视为数据的处理方式 | 合成嵌入式指令样例并检查输出 schema |
| 损失下降但召回率下降 | 验证集污染、过拟合、输出限制 | 比较 checkpoint 和 early-stopping 标准 |

不要把测试失败的样例复制到训练集后，仍宣称模型在同一测试集上有提升。应记录错误分析集已影响开发，并确定新的最终评估集。

## 6. 将训练长度与推理长度一起设计

`max_sequence_length=1024` 并不表示可处理 1,024 个文档字符。Chat template、系统指令、源文本和目标补全结果都会占用 tokenizer 预算。韩语、英语和数字的字符 / token 比例各不相同。

- 验证截断不会在训练时删掉所有有监督的目标 token。
- 推理时不能把被截断输入区域中的 PII 当作不存在。
- 分块需要源文本 offset、重复项对账、跨边界实体处理和重复出现值的处理。
- 应专门测试跨越分块边界的 PII，不要假设重叠足以解决问题。
- 应明确报告输入溢出和输出不完整，不要将部分结果标记为完整。

## 7. 测量前先编写验收表

以下是团队记录证据和标准的**模板**，并不代表仓库已经达到的性能，也不是普遍适用的数值门槛。

| 方面 | 证据 | 不足时的行动 |
|---|---|---|
| 标签和数据划分 | 标注版本、系列 / 拆分 / 哈希、子组计数 | 重建评估集 |
| 候选选择 | 验证集比较、变化变量、决策 | 进行另一次受控实验 |
| 最终质量 | 锁定测试集上的分类结果和错误数量 | 暂缓部署 |
| 输出契约 | 空、格式错误和截断响应测试 | 修复解析 / 拒答行为 |
| 处理策略 | 替换 span、映射生命周期、残余检查 | 修复策略或处理流程 |
| 运维行为 | 延迟、内存、超时、按长度统计的吞吐量 | 调整容量和长度限制 |
| 复现 / 恢复 | 基础模型 / tokenizer 修订、adapter 哈希、环境、旧版本 | 完成打包 |

评估**之前**先确定特定任务的 F1、recall 和延迟标准。小样本中观测到零错误，并不能证明真实错误率为零。报告子组结果时，应显示分子和分母。

## 8. 从 SageMaker 制品到服务包

Training Job 状态达到 `Completed` 只表示训练作业已终止。Endpoint 创建、adapter 加载、输出校验以及批准脱敏结果是不同的步骤。

1. 保留 `/opt/ml/model` 和 MLflow 中的 adapter、配置和汇总结果。
2. 将确切的基础模型 / tokenizer 修订、chat template、量化设置和 parser 版本与 adapter 一并记录。
3. 在目标环境中测试重新加载和确定性解码。Adapter 单独并不是完整的基础模型。
4. 在 shadow 或有限 canary 工作流中观测长度、输出格式和错误率。
5. 将**模型 + tokenizer + parser + 策略**组合进行版本管理，以便一并回滚。

本章没有实现或部署 endpoint，也未实现严格的发布包装器。真实部署还必须测试源文本 / 补全结果 / 映射是否会通过 CloudWatch、MLflow autolog / tracing、错误记录和请求追踪暴露。Adapter 会受到训练数据影响，分享前需要单独审查。

## 检查理解情况

1. 为什么不立即部署 F1 较高的候选模型？**它在负例文档中增加了误屏蔽；两篇合成文档也不足以构成有代表性的评估。**
2. 100% 往返还原率是否表示所有 PII 都已删除？**不是。它只表示被替换值可能成功还原。**
3. 如果用同一个测试集选择了多个 rank 会怎样？**该测试集参与了模型选择，不再是独立的最终测试集。**
4. 与源文本匹配的候选项一定是 PII 吗？**不一定；证件号码就是反例。**
5. 能否仅凭未标注流量的模型输出计算此评估器的泄漏率？**不能；需要金标注释。**

## 参考资料

- [仓库中的评估 CLI](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/src/evaluate.py)
- [实际指标实现](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/src/metrics.py)
- [替换和重建](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/src/pii_tokens.py)
- [PEFT checkpoint 格式](https://huggingface.co/docs/peft/v0.17.0/en/developer_guides/checkpoint)
- [SageMaker 容器目录](https://docs.aws.amazon.com/sagemaker/latest/dg/amazon-sagemaker-toolkits.html)
- [Presidio Anonymizer 操作和还原](https://github.com/microsoft/presidio/blob/main/presidio-anonymizer/README.md)

上一页：[数据增强工作坊](06-data-augmentation-workshop.md) · [学习路径](README.md)

[工作坊测验](../../quizzes/ai-ml/sagemaker-ai/07-pii-evaluation-release-quiz.md)
