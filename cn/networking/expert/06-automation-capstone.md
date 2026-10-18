# 6. 网络自动化与最终评估

> **最后更新**：2026 年 9 月 15 日

**前提条件**：第 1、2、4 章提供了通用的观测技能。若要完成 EVPN / 网络架构综合实验，请再学习第 3 章；若要完成云相关综合实验，请再学习第 5 章。Linux 主机综合实验使用第 4 章中范围受控的实验。验证器练习只需要 Python 3.9+ 和一个由你自行创建的新目录。

**目标**：将预期意图与观测结果分开，并提交可复现的正常、禁止、失败和恢复状态。自动化不能把缺失的证据当作成功。

## 1. 修改前先检查意图 {#intent}

| 范围 | 修改前定义 | 修改后验证 |
|---|---|---|
| 可达性 | 谁应能访问哪个服务？ | 实际响应和观测点 |
| 隔离 | 哪些流量必须被禁止？ | 与探测结果一并核验的策略证据 |
| 路由策略 | 应向哪个对等端 / VRF 通告哪些前缀？ | 同一范围内的通告、选路和转发状态 |
| 韧性 | 单点故障发生后必须保留什么？ | 服务连续性及收敛 / 恢复时间 |
| 运维边界 | 管理访问、变更范围和停止条件 | 未执行范围外变更，且状态已恢复 |

仅为了匹配新的输出而修改预期值，可能会掩盖回归问题。应先检查意图，并记录其修订版本 / 哈希值。观测适配器在规范化实际输出的同时，会保留单位、范围和时间信息。

例如，FRR 对等端的通告、Linux 主机的整个 FIB，以及 TGW 路由表是不同的数据集。下面的前缀约定比较的是**通告给指定对等端的前缀集合**。偏好值、ECMP 数量、FIB 安装情况和实际转发需要分别提供证据。

## 2. 小型验证器练习 {#record-validator}

以下数据是**合成数据**，不会配置网络或发送数据包。验证器会检查给定意图和记录是否一致；它不会证明 PCAP 或计数器是真实可信的。

在实验虚拟机或本地学习终端中创建一个新目录。

```bash
EVIDENCE_DIR=$(mktemp -d /tmp/network-evidence.XXXXXX)
printf '%s\n' "$EVIDENCE_DIR"
```

将此 JSON 保存为该目录中的 `intent.json`。实际自动化应将其作为单独审查的输入。

```json
{
  "schema": 1,
  "scenario": "tenant-isolation",
  "phase": "steady",
  "route_scope": "r2:export-to-r1",
  "maximum_window_seconds": 60,
  "exported_prefixes": ["203.0.113.0/24"],
  "flows": {"a-to-web": "allow", "b-to-a": "deny"}
}
```

将以下内容保存为 `observations.json`。地址、时间和工件名称都只是示例。

```json
{
  "schema": 1,
  "scenario": "tenant-isolation",
  "phase": "steady",
  "route_scope": "r2:export-to-r1",
  "evidence_kind": "synthetic",
  "window": {"start": "2026-09-15T00:00:00Z", "end": "2026-09-15T00:00:10Z"},
  "exported_prefixes": ["203.0.113.0/24"],
  "route_artifact": "synthetic:advertised-routes",
  "flows": {
    "a-to-web": {
      "verdict": "allow",
      "artifacts": {"probe": "synthetic:http-response"}
    },
    "b-to-a": {
      "verdict": "deny",
      "artifacts": {"probe": "synthetic:blocked-probe", "policy": "synthetic:policy-decision"}
    }
  }
}
```

将以下 Python 代码保存为同一目录中的 `check_record.py`。

```python
import ipaddress
import json
import sys
from datetime import datetime
from pathlib import Path


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON key: " + key)
        result[key] = value
    return result


def load(path):
    return json.loads(Path(path).read_text(), object_pairs_hook=unique_object)


def prefixes(values):
    require(isinstance(values, list), "prefixes must be a list")
    return {str(ipaddress.ip_network(value, strict=True)) for value in values}


def timestamp(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(parsed.tzinfo is not None, "timestamp needs a timezone")
    return parsed


require(len(sys.argv) == 3, "usage: check_record.py intent.json observations.json")
intent, seen = load(sys.argv[1]), load(sys.argv[2])
for record in (intent, seen):
    require(type(record.get("schema")) is int and record["schema"] == 1, "schema")
for key in ("scenario", "phase", "route_scope"):
    require(intent[key] == seen[key], "scope mismatch: " + key)
require(seen["evidence_kind"] in {"synthetic", "supplied", "measured"}, "evidence kind")
duration = (timestamp(seen["window"]["end"]) - timestamp(seen["window"]["start"])).total_seconds()
require(0 < duration <= intent["maximum_window_seconds"], "invalid observation window")
require(prefixes(intent["exported_prefixes"]), "empty intended prefix scope")
require(prefixes(seen["exported_prefixes"]) == prefixes(intent["exported_prefixes"]), "prefix mismatch")
require(isinstance(seen.get("route_artifact"), str) and seen["route_artifact"].strip(), "route evidence missing")
require(intent["flows"] and set(intent["flows"]) == set(seen["flows"]), "flow coverage mismatch")
for name, wanted in intent["flows"].items():
    require(wanted in {"allow", "deny"}, "unsupported intent")
    actual = seen["flows"][name]
    require(actual["verdict"] == wanted, "flow mismatch: " + name)
    needed = {"probe"} if wanted == "allow" else {"probe", "policy"}
    artifacts = actual["artifacts"]
    require(all(isinstance(artifacts.get(k), str) and artifacts[k].strip() for k in needed),
            "evidence missing: " + name)
print("CONSISTENT_RECORD kind=" + seen["evidence_kind"] + "; live behavior not attested")
```

运行它：

```bash
python3 "${EVIDENCE_DIR:?}/check_record.py" \
  "${EVIDENCE_DIR:?}/intent.json" "${EVIDENCE_DIR:?}/observations.json"
```

预期输出为 `CONSISTENT_RECORD kind=synthetic; live behavior not attested`。这表示该记录满足了所要求的条件，并不表示网络流量已成功，也不代表已批准运维发布。显式异常处理能确保 Python 优化模式移除 `assert` 语句后，检查仍然生效。

### 必须失败的输入

保留原始文件，将 `observations.json` 复制为 `observations-bad.json`，然后**每次只修改一项**。使用同一条命令，并将该副本作为最后一个参数。

| 修改 | 预期结果 |
|---|---|
| 删除 `b-to-a` 观测 | `flow coverage mismatch` |
| 将 `b-to-a.verdict` 设为 `unknown` 或 `allow` | `flow mismatch` |
| 删除禁止流量对应的 `policy` 工件 | `evidence missing` |
| 在通告中加入 `0.0.0.0/0`，或清空列表 | `prefix mismatch` |
| 将结束时间设置为早于开始时间 | `invalid observation window` |
| 修改 `phase` | `scope mismatch` |

不要把空输出或超时规范化为 `deny`。对于被禁止的结果，必须有与探测相关联的策略 / 执行证据。仅仅命名某个工件，并不能证明它确实存在，也不能证明它是在正确的观测点采集的。

将此练习扩展为真实采集器时，应根据原始证据检查文件是否存在、哈希值、时间范围、采集器和设备 / 账户身份。还应单独验证规范化为集合时丢失的属性，例如路径属性或每个端点的就绪状态。

## 3. 设计变更流水线 {#pipeline}

明确每个阶段的输入、输出和失败责任方。

| 阶段 | 检查内容 | 传递给下一阶段的结果 |
|---|---|---|
| 意图审查 | 允许 / 禁止的流量、路由、管理访问和故障边界 | 已审查的意图修订版本 |
| 静态验证 | 语法、支持的功能、重叠地址和策略范围 | 针对确切工具 / 提供方版本的结果 |
| 变更预览 | 目标、影响、预期差异和可恢复性 | 可供人工审查的变更计划 |
| 实验环境应用 | 单项变更、受限的时间 / 资源、保留管理访问 | 变更前 / 后状态和执行记录 |
| 行为检查 | 允许、禁止、失败、恢复及缺失证据 | 与原始证据关联的结构化结果 |
| 运维决策 | 验证范围、未知项、发布 / 回滚条件 | 通过独立运维流程批准或拒绝 |

本课程不提供自动化生产环境审批流水线。请提前阅读恢复命令；如果变更可能影响管理连接，应预先建立独立的恢复访问方式，例如控制台。

## 4. 选择综合实验 {#capstones}

### A. 路由 / 网络架构

使用[第 2 章](02-routing-policy-convergence.md)或[第 3 章](03-datacenter-evpn.md)中的一个已准备好的实验环境。

1. 为特定对等端 / VRF 定义允许的前缀和禁止的路由 / 流量。
2. 记录正常情况下的通告、选路、FIB 和服务探测结果。
3. 从该章选择一个可恢复的策略 / 路径故障。
4. 将控制平面变更时间与实际服务恢复时间分开记录。
5. 恢复原配置，并重新检查可达性和隔离情况。

不要用会话状态变为 Established 的时间代替服务收敛时间。比较不同设备的时钟时，应记录时钟同步 / 不确定性，或统一使用同一观测者的时间轴。

### B. Linux / 云 / SRE

从[第 4 章](04-linux-performance.md)选择一个范围受控的主机实验，或使用[第 5 章](05-cloud-cni-design.md)中经过批准的云证据。

1. 标记正向 / 返回路径和至少两个观测点。
2. 针对延迟、丢包、排队或策略选择一个假设，并定义如何证伪。
3. 将观测结果与源 / 命名空间、时间和单位关联起来。
4. 如果执行了实验，应精确恢复环境，并重复相同检查。
5. 如果只分析了设计或给定证据，应相应限制结论的范围。

如果没有设备或账户，请提交设计分析或给定证据的分析。只有在提供了你自己受控实验的原始证据和恢复证据时，才将**实际执行**标记为已完成。

## 5. 评估 {#assessment}

对每个项目评为 `met / unmet / unobserved`（已满足 / 未满足 / 未观测）。不要把缺少的强制证据隐藏在总分中。

| 项目 | 通过标准 |
|---|---|
| 范围 / 可复现性 | 可还原拓扑、环境、权限、版本 / 修订、输入和时间 |
| 协议推理 | 解释数据包、路由和应用之间的关系；至少证伪一个假设 |
| 正向 / 负向检查 | 分别评估允许流量和隔离；绝不把缺失视为成功 |
| 故障 / 恢复 | 根据相同标准检查单项变更的影响和恢复后的状态 |
| 自动化质量 | 拒绝范围错误、遗漏、未知项和意图不匹配；原始证据可追溯 |
| 结论可靠性 | 区分实测、给定、合成、设计和未观测证据 |

如果强制项目未满足，请返回相关章节。存在未观测项目时，不要宣称实时验证已完成。审查者必须能够根据同一组证据还原结论。

## 清理与后续学习

清理验证器练习前，先检查创建的文件。

```bash
ls -la -- "${EVIDENCE_DIR:?}"
rm -- "${EVIDENCE_DIR:?}/intent.json" "${EVIDENCE_DIR:?}/observations.json" \
  "${EVIDENCE_DIR:?}/check_record.py"
```

如果创建了副本，只删除**已验证的副本**，然后运行 `rmdir -- "${EVIDENCE_DIR:?}"`。实际实验的原始证据遵循独立的批准保留策略，不属于这个临时合成示例。

可以在能力较弱的领域增加实验：[协议](01-protocol-projects.md)、[路由](02-routing-policy-convergence.md)、[EVPN](03-datacenter-evpn.md)、[Linux 性能](04-linux-performance.md)或[云设计](05-cloud-cni-design.md)。

参考资料：[Python JSON](https://docs.python.org/3/library/json.html)、[ipaddress](https://docs.python.org/3/library/ipaddress.html)、[datetime](https://docs.python.org/3/library/datetime.html)。

[上一章：云 / CNI](05-cloud-cni-design.md) · [测验](../../quizzes/networking/expert/06-automation-capstone-quiz.md) · [课程](README.md)
