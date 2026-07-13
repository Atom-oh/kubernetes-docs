# Kubescape 测验

通过以下问题测试你对 Kubescape 安全态势管理的理解。

---

## 问题

### 1. Kubescape 在 CNCF 中的项目状态是什么？

- A) 毕业项目
- B) 孵化项目
- C) Sandbox project
- D) 不是 CNCF 项目

<details>
<summary>显示答案</summary>

**答案：C) Sandbox project**

**解释：**
Kubescape 于 2022 年被接纳为 CNCF Sandbox project。它最初由 ARMO 开发，并捐赠给 CNCF。作为 Sandbox project，它是一个早期阶段项目，CNCF 认为它具有增长潜力。

</details>

---

### 2. Kubescape 支持哪些安全框架用于合规扫描？

- A) 仅 NSA-CISA
- B) 仅 CIS Benchmarks
- C) NSA-CISA、CIS Benchmarks 和 MITRE ATT&CK
- D) 仅 OWASP 和 PCI-DSS

<details>
<summary>显示答案</summary>

**答案：C) NSA-CISA、CIS Benchmarks 和 MITRE ATT&CK**

**解释：**
Kubescape 支持多个安全框架：

```bash
# Scan with NSA-CISA framework
kubescape scan framework nsa

# Scan with CIS Kubernetes Benchmark
kubescape scan framework cis-v1.23-t1.0.1

# Scan with MITRE ATT&CK
kubescape scan framework mitre
```

- **NSA-CISA**：来自美国政府机构的 Kubernetes Hardening Guide
- **CIS**：Center for Internet Security Kubernetes Benchmarks
- **MITRE ATT&CK**：基于威胁的安全框架，用于映射攻击技术

</details>

---

### 3. 使用 Kubescape 扫描 Kubernetes cluster 的正确 CLI 语法是什么？

- A) kubescape check cluster
- B) kubescape scan
- C) kubescape audit cluster
- D) kubescape analyze

<details>
<summary>显示答案</summary>

**答案：B) kubescape scan**

**解释：**
Kubescape CLI 扫描命令：

```bash
# Scan current cluster
kubescape scan

# Scan specific namespace
kubescape scan --include-namespaces production

# Scan YAML files before deployment
kubescape scan *.yaml

# Scan with specific framework
kubescape scan framework nsa

# Scan specific control
kubescape scan control C-0034
```

`scan` 子命令是所有扫描操作的主要接口。

</details>

---

### 4. Kubescape Operator 和 CLI 模式之间的关键区别是什么？

- A) Operator 模式只扫描 nodes
- B) CLI 模式提供持续监控，Operator 是一次性的
- C) Operator 通过集群内组件提供持续监控，CLI 是一次性扫描
- D) 没有区别

<details>
<summary>显示答案</summary>

**答案：C) Operator 通过集群内组件提供持续监控，CLI 是一次性扫描**

**解释：**
Kubescape 部署模式：

**CLI 模式：**
```bash
# One-time scan from local machine
kubescape scan
```
- 临时扫描
- CI/CD 集成
- 本地开发

**Operator 模式：**
```bash
# Install in-cluster operator
helm repo add kubescape https://kubescape.github.io/helm-charts
helm install kubescape kubescape/kubescape-operator
```
- 持续监控
- 定期扫描
- 集群内漏洞扫描
- 与 ARMO 平台集成以实现可视化

</details>

---

### 5. Kubescape 如何计算 controls 的风险评分？

- A) 仅二元通过/失败
- B) 基于严重性乘以受影响的 resources 数量
- C) 随机分配
- D) 基于 namespace 优先级

<details>
<summary>显示答案</summary>

**答案：B) 基于严重性乘以受影响的 resources 数量**

**解释：**
Kubescape 风险评分：

```
Risk Score = Severity Score x (Failed Resources / Total Resources)
```

示例输出：
```
┌──────────────────────────────────────────────────┬────────────────┬───────┐
│ Control Name                                      │ Failed Resources│ Score │
├──────────────────────────────────────────────────┼────────────────┼───────┤
│ Privileged container                              │ 3/50           │ 18%   │
│ Resource limits                                   │ 25/50          │ 35%   │
│ Non-root containers                               │ 10/50          │ 42%   │
└──────────────────────────────────────────────────┴────────────────┴───────┘
```

更高的评分表示风险更大，需要立即关注。

</details>

---

### 6. 哪个标志会在 CI/CD pipelines 中强制执行合规阈值？

- A) --min-score
- B) --compliance-threshold
- C) --fail-threshold
- D) --severity-threshold

<details>
<summary>显示答案</summary>

**答案：B) --compliance-threshold**

**解释：**
在 CI/CD pipelines 中使用 Kubescape：

```bash
# Fail pipeline if compliance drops below 80%
kubescape scan --compliance-threshold 80

# Example GitLab CI
kubescape-scan:
  script:
    - kubescape scan framework nsa --compliance-threshold 75
    - kubescape scan framework cis --compliance-threshold 80
```

阈值是百分比（0-100）。如果整体合规评分低于该阈值，扫描会失败（非零退出）。

```bash
# Exit codes
# 0: Passed threshold
# 1: Failed threshold
# 2: Error during scan
```

</details>

---

### 7. Kubescape 与 kube-bench 有何不同？

- A) kube-bench 只扫描 applications，Kubescape 扫描 infrastructure
- B) Kubescape 扫描 workload 配置，kube-bench 侧重于 node-level CIS benchmarks
- C) 它们是完全相同的工具
- D) kube-bench 仅适用于 cloud providers

<details>
<summary>显示答案</summary>

**答案：B) Kubescape 扫描 workload 配置，kube-bench 侧重于 node-level CIS benchmarks**

**解释：**
Kubescape 与 kube-bench 对比：

| 功能 | Kubescape | kube-bench |
|---------|-----------|------------|
| 重点 | Workload/config 安全 | Node/control plane 安全 |
| 范围 | Deployments, Pods, RBAC | kubelet, API server, etcd |
| 框架 | NSA, CIS, MITRE | 仅 CIS Benchmarks |
| 运行位置 | 集群外部（CLI）或集群内 | 必须在每个 node 上运行 |
| Image 扫描 | 是（使用 Grype） | 否 |
| RBAC 分析 | 是 | 否 |

结合使用两者以获得全面安全性：
- kube-bench：Cluster infrastructure 加固
- Kubescape：Workload 和配置安全

</details>

---

### 8. Kubescape 为 RBAC 安全分析提供了什么功能？

- A) RBAC policy 生成
- B) RBAC 可视化，显示权限和风险
- C) 自动 RBAC 修复
- D) RBAC 迁移工具

<details>
<summary>显示答案</summary>

**答案：B) RBAC 可视化，显示权限和风险**

**解释：**
Kubescape RBAC 分析能力：

```bash
# Scan RBAC configurations
kubescape scan control C-0035  # Cluster-admin binding
kubescape scan control C-0036  # Wildcard permissions
kubescape scan control C-0039  # Risky service accounts
```

RBAC 可视化功能：
- 将 ServiceAccounts 映射到 Roles/ClusterRoles
- 识别权限过大的 bindings
- 突出显示危险权限（secrets access、pod exec）
- 显示通过 RBAC 的攻击路径

示例发现：
```
ServiceAccount 'default' in namespace 'production' has:
- Cluster-admin binding (CRITICAL)
- Secrets list/get permissions (HIGH)
- Pod exec permissions (HIGH)
```

</details>

---

### 9. Kubescape 集成了哪个漏洞扫描器用于 image 扫描？

- A) Trivy
- B) Clair
- C) Grype
- D) Anchore

<details>
<summary>显示答案</summary>

**答案：C) Grype**

**解释：**
Kubescape 与 Grype（由 Anchore 提供）集成，用于 container image 漏洞扫描：

```bash
# Enable image scanning
kubescape scan --enable-host-scan

# Operator mode includes automatic image scanning
helm install kubescape kubescape/kubescape-operator \
  --set capabilities.vulnerabilityScan=enable
```

Grype 集成提供：
- container images 中的 CVE 检测
- SBOM（Software Bill of Materials）生成
- 基于严重性的优先级排序
- 与安全发现集成

结果会将配置问题与漏洞数据结合起来，以进行全面的风险评估。

</details>

---

### 10. Kubescape 如何处理 control exceptions？

- A) 不支持 exceptions
- B) 使用 exception YAML 文件，指定要排除的 controls 和 resources
- C) 仅通过 command-line flags
- D) 通过修改源代码

<details>
<summary>显示答案</summary>

**答案：B) 使用 exception YAML 文件，指定要排除的 controls 和 resources**

**解释：**
Kubescape 通过配置文件支持 exceptions：

```yaml
# exceptions.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: kubescape-exceptions
data:
  exceptions: |
    - name: "Allow privileged kube-system pods"
      policyType: postureExceptionPolicy
      actions:
        - alertOnly
      resources:
        - designatorType: Attributes
          attributes:
            namespace: kube-system
      posturePolicies:
        - controlID: C-0057  # Privileged container
```

应用 exceptions：
```bash
kubescape scan --exceptions exceptions.yaml
```

这允许：
- 抑制已知误报
- 接受特定 resources 的风险
- 保持扫描报告整洁

</details>

---

## 评分计算

- **9-10 correct**：优秀 - 你对 Kubescape 有深入理解。
- **7-8 correct**：良好 - 你扎实掌握了关键概念。
- **5-6 correct**：一般 - 有些领域需要进一步学习。
- **4 or fewer**：请再次查阅文档。

## 相关文档

- [使用 Kubescape 进行安全态势管理](../../security/11-kubescape.md)
