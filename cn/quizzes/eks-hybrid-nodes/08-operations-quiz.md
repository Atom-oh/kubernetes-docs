# EKS Hybrid Nodes 运维测验

> **最后更新**: 2026 年 9 月 13 日

> **相关文档**: [运维](../../eks-hybrid-nodes/08-operations.md)

## 选择题

<span id="_1-what-is-the-recommended-tool-combination-for-node-monitoring-in-hybrid-nodes-environments"></span>

### 1. 哪种组合可为 Hybrid Nodes 提供主机指标和仪表板？

- A) 记事本和手动记录
- B) Prometheus、Grafana 和正确配置的 Node Exporter
- C) 仅使用电子邮件通知
- D) 仅手动审查日志

<details>
<summary>显示答案</summary>

**答案：B) Prometheus、Grafana 和正确配置的 Node Exporter**

**说明：**
Prometheus 负责采集指标，Grafana 用于展示，Node Exporter 暴露主机指标，DCGM Exporter 暴露受支持的 GPU 指标，Alertmanager 则负责路由告警。这是一种有效方案，但不是唯一受支持的方案。应安装经过审查的 chart/插件，并核实主机挂载、身份、部署位置、TLS、身份验证和实际抓取目标。若 DaemonSet 的 selector 与模板标签不匹配，即使创建了部分资源也无法正常工作。由于无法使用 EC2 IMDS，Container Insights 无法提供 Hybrid 主机级指标。

</details>

<span id="_2-how-do-you-check-when-kubelet-certificate-renewal-is-needed"></span>

### 2. 应如何检查已配置的节点证书或服务证书何时到期？

- A) 假定证书永不过期
- B) 用 OpenSSL 检查实际证书，并确认其颁发者和续期负责人
- C) 等到 Node 变为 NotReady
- D) 每天手动续期所有证书

<details>
<summary>显示答案</summary>

**答案：B) 用 OpenSSL 检查实际证书，并确认其颁发者和续期负责人**

**说明：**
首先区分 kubelet serving/client 证书、EKS 控制平面 CA、Harbor TLS 证书和 IAM Roles Anywhere 主机证书。Hybrid IAM 身份验证并不意味着一定存在 kubelet-client-current.pem 文件。kubeadm 续期命令不会管理 EKS 控制平面。检查到期时间也不同于验证证书链、主机名、吊销状态和实时身份验证。仅设置 serverTLSBootstrap 不会自动批准 serving CSR，也不会续期 IAM Roles Anywhere 证书。
```bash
set -euo pipefail
: "${CERT_PATH:?Set the actual certificate file}"
openssl x509 -in "$CERT_PATH" -checkend 604800 -noout
```
此示例会在证书将在七天内到期时发出提示；阈值应根据证书有效期和续期策略选择。文件缺失或无效时命令会失败。

</details>

<span id="_3-what-is-the-first-troubleshooting-step-when-kubelet-is-not-responding-on-a-hybrid-node"></span>

### 3. Hybrid Node 上的 kubelet 停止响应时，应先检查什么？

- A) 重启整个集群
- B) 检查映射到该节点的主机服务状态、近期日志和相关依赖
- C) 未经调查就创建替代节点
- D) 删除所有 Pod

<details>
<summary>显示答案</summary>

**答案：B) 检查映射到该节点的主机服务状态、近期日志和相关依赖**

**说明：**
先识别已注册的 Node 和它实际对应的主机，再检查 kubelet/containerd 状态、有限范围的近期日志、磁盘/内存，以及已验证的网络和凭证路径。不要禁用 TLS、导出注册表凭证，也不要运行 nodeadm reset：该子命令不在本次审查的 Hybrid CLI 中。重启或重新注册属于单独的恢复决策；应保留诊断信息并遵循生命周期指南。
```bash
# On the verified host, not a hostname guessed from its Kubernetes Node name:
sudo systemctl status kubelet containerd --no-pager
sudo journalctl -u kubelet -u containerd --since '10 minutes ago' --no-pager -n 200
```

</details>

<span id="_4-what-command-is-used-to-safely-move-workloads-for-node-maintenance"></span>

### 4. 计划进行节点维护时，哪个命令会请求驱逐工作负载？

- A) kubectl delete node
- B) kubectl drain
- C) 仅运行 kubectl cordon
- D) kubectl delete pods --all

<details>
<summary>显示答案</summary>

**答案：B) kubectl drain**

**说明：**
drain 会将 Node 标记为不可调度，通常通过 Eviction API 请求驱逐，并遵守适用的 PDB。控制器可能创建替代 Pod；该命令不会迁移内存，也不保证应用连续运行。执行 drain 前，应检查剩余容量、放置位置、存储和本地数据。不要例行绕过 eviction、丢弃 emptyDir 数据，或覆盖所有 Pod 的终止期限。只有在主机和工作负载验证成功后，且该 Node 原本可调度时，才运行 uncordon。

| 命令 | 作用 |
| --- | --- |
| cordon | 阻止通常的新调度 |
| drain | 执行 cordon 并请求驱逐，仍受豁免项和约束影响 |
| uncordon | 恢复调度；它不是健康检查 |

当有三个匹配且健康的副本时，minAvailable: 2 的 PDB 只允许一次自愿中断。PDB 不能防止节点丢失或所有应用故障。

</details>

<span id="_5-what-is-the-recommended-solution-for-centralizing-logs-from-hybrid-nodes"></span>

### 5. 哪种方案可集中收集 Hybrid 工作负载日志？

- A) 手动复制每个日志文件
- B) 使用已配置的 Fluent Bit/Fluentd 收集器和受保护的集中式后端
- C) 不收集任何日志
- D) 只查看控制台输出

<details>
<summary>显示答案</summary>

**答案：B) 使用已配置的 Fluent Bit/Fluentd 收集器和受保护的集中式后端**

**说明：**
应配置实际的容器运行时日志路径和解析器、Kubernetes 元数据权限、缓冲区/检查点、重试机制，以及经过身份验证的 TLS 输出。Containerd 通常通过 /var/log/containers 下的符号链接访问 /var/log/pods；不要照搬只适用于旧 Docker 的 /var/lib/docker/containers 清单。收集器需要适当的只读主机挂载，并应明确其状态数据的存储策略。日志采集不保证零丢失。
```text
Hybrid Nodes → configured collectors → CloudWatch Logs / Loki / Elasticsearch
                       ↓
              protected buffers and checkpoints
```

</details>

<span id="_6-what-is-the-default-wait-time-before-automatically-rescheduling-pods-to-other-nodes-when-a-node-fails"></span>

### 6. 在采用默认准入行为且没有显式覆盖时，普通 Pod 因 not-ready 和 unreachable 获得的 NoExecute 容忍时长是多少？

- A) 0 秒
- B) 30 秒
- C) 300 秒
- D) 1 小时

<details>
<summary>显示答案</summary>

**答案：C) 300 秒**

**说明：**
除非显式设置其他值，Kubernetes 通常会为这两种污点添加 tolerationSeconds: 300。这是污点容忍时长，并不保证节点故障后恰好五分钟替代工作负载就会 Ready。故障检测、添加污点、控制器行为、容量、卷和启动时间都会带来额外约束。DaemonSet Pod 通常会无限期容忍这些污点。缩短时长并不能证明网络分区时旧进程已经停止；有状态写入方可能需要 fencing。
```yaml
# Fragment under Pod spec or a workload's PodTemplate.spec, not a complete Pod:
tolerations:
- key: node.kubernetes.io/not-ready
  operator: Exists
  effect: NoExecute
  tolerationSeconds: 60
- key: node.kubernetes.io/unreachable
  operator: Exists
  effect: NoExecute
  tolerationSeconds: 60
```
显式设置 60 秒的示例需要经过测试的可用性/数据安全决策；它不代表 60 秒的恢复 SLO。

</details>

<span id="_7-what-is-the-recommended-strategy-for-eks-hybrid-nodes-upgrades"></span>

### 7. 哪种做法符合 AWS 对 Hybrid Nodes 的升级指导？

- A) 同时升级所有节点
- B) 优先使用新主机并受控切换；否则按一次一个节点执行已验证的原地升级步骤
- C) 每次升级都删除并重建集群
- D) 永不升级

<details>
<summary>显示答案</summary>

**答案：B) 优先使用新主机并受控切换；否则按一次一个节点执行已验证的原地升级步骤**

**说明：**
有额外容量时，AWS 更倾向于使用替代主机并迁移工作负载。原地执行 nodeadm upgrade 会造成中断，并且需要传入 Kubernetes major.minor 版本参数。应遵循生命周期指南检查版本偏差、drain 和数据、实际主机操作、Node UID/完整版本/新 Lease，以及工作负载状态。固定等待一段时间或看到旧的 Ready 条件都不能作为验收依据。不要声称滚动升级一定不会中断服务。

每个升级批次前，应检查备份、PDB、可用容量、版本兼容性、凭证身份和恢复方案。遇到错误时停止并保留证据；不要自动对故障节点运行 uncordon。

</details>
