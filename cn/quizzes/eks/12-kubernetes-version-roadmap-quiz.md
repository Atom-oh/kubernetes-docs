# Kubernetes 版本特性和路线图测验

1. Kubernetes 的发布节奏是什么？
   - A) 每年一次，包含主要特性
   - B) 每年大约 3 个版本，约每 4 个月一次
   - C) 每月发布补丁版本，每季度发布特性版本
   - D) 每年两次，与 AWS re:Invent 和 Summit 对齐

<details>
<summary>显示答案</summary>

**答案: B) 每年大约 3 个版本，约每 4 个月一次**

**解析:**
Kubernetes 遵循约 4 个月的发布周期，每年大约发布 3 个 minor version。每个版本都会经历 enhancement freeze、code freeze 和 release candidate 阶段。近期版本包括：1.33 (Apr 2025)、1.34 (Aug 2025)、1.35 (Dec 2025)、1.36 (Apr 2026)。之后，每个版本都会通过 patch release 维护大约 14 个月。

</details>

---

2. EKS Standard Support 和 Extended Support 有什么区别？
   - A) Standard 是免费的，Extended 需要 Enterprise license
   - B) Standard 持续 14 个月，费用为 $0.10/cluster/hour；Extended 额外增加 12 个月，费用为 $0.60/cluster/hour
   - C) Standard 支持 3 个版本，Extended 支持所有版本
   - D) Standard 每月提供补丁，Extended 每周提供补丁

<details>
<summary>显示答案</summary>

**答案: B) Standard 持续 14 个月，费用为 $0.10/cluster/hour；Extended 额外增加 12 个月，费用为 $0.60/cluster/hour**

**解析:**
EKS 上的每个 Kubernetes 版本都会获得 14 个月的 standard support（$0.10/cluster/hour），随后是 12 个月的 extended support（$0.60/cluster/hour — 成本为 6 倍）。每个版本的总支持期为 26 个月。Extended support 默认启用。当某个版本退出 extended support 时，cluster 会自动升级。这种定价差异旨在鼓励保持在受支持的版本上。

</details>

---

3. Sidecar Containers 在哪个 Kubernetes 版本中升级到 GA？
   - A) 1.28（首次作为 alpha 引入时）
   - B) 1.31
   - C) 1.33
   - D) 1.35

<details>
<summary>显示答案</summary>

**答案: C) 1.33**

**解析:**
原生 Sidecar Containers (KEP-753) 遵循以下升级路径：v1.28 (Aug 2023) 中为 alpha，v1.29 (Dec 2023) 中为 beta，v1.33 (Apr 2025) 中为 GA。Sidecar 被定义为带有 `restartPolicy: Always` 的 init containers，确保它们在 application containers 之前启动，在整个 Pod 生命周期中运行，并在 main containers 之后终止，从而解决 Jobs 中长期存在的 “zombie sidecar” 问题。

</details>

---

4. In-Place Pod Resize 特性是什么，它何时达到 GA？
   - A) 无需重新部署即可更改 Pod replicas；在 1.30 中达到 GA
   - B) 无需重启即可修改正在运行的 Pods 上的 CPU/memory requests 和 limits；在 1.35 中达到 GA
   - C) 在线调整 PersistentVolumes 大小的能力；在 1.31 中达到 GA
   - D) 更改正在运行的 Pods 上的 container images 的能力；在 1.34 中达到 GA

<details>
<summary>显示答案</summary>

**答案: B) 无需重启即可修改正在运行的 Pods 上的 CPU/memory requests 和 limits；在 1.35 中达到 GA**

**解析:**
In-Place Pod Resize (KEP-1287) 让正在运行的 Pods 上的 CPU 和 memory requests/limits 可变。升级路径：v1.27 中为 alpha，v1.33 中为 beta，v1.35 (Dec 2025) 中为 GA。从 v1.33 开始，修改使用 `/resize` subresource。`resizePolicy` 字段控制每种 resource type 是否需要重启 container。此特性对 VPA 集成具有变革性意义，可在不中断 Pod 的情况下实现 resource right-sizing。

</details>

---

5. Kubernetes 1.31 中 Dynamic Resource Allocation (DRA) 发生了什么重大变化？
   - A) DRA 被弃用，并由 Device Plugins v2 取代
   - B) Classic DRA 被移除；只保留 Structured Parameters DRA（后者随后在 1.34 中达到 GA）
   - C) DRA 直接从 alpha 升级到 GA
   - D) DRA 在 GPUs 之外增加了对 network devices 的支持

<details>
<summary>显示答案</summary>

**答案: B) Classic DRA 被移除；只保留 Structured Parameters DRA（后者随后在 1.34 中达到 GA）**

**解析:**
DRA 经历了一次重大重新设计。Classic DRA（KEP-3063，自 v1.26 起为 alpha）使用不透明的 vendor parameters，scheduler 和 cluster autoscaler 无法对其进行推理。Structured Parameters DRA (KEP-4381) 用 Kubernetes-native 格式替代了它，该格式使用 `ResourceSlice` objects。在 v1.31 中，classic DRA 被完全移除。Structured DRA 的进展为：v1.32 中为 beta，v1.34 中为 GA。这对于 AI/ML workloads 中的 GPU/accelerator scheduling 至关重要。

</details>

---

6. 哪个特性在 Kubernetes 1.30 中升级到 GA，使无需 webhooks 的声明式 admission control 成为可能？
   - A) OPA Gatekeeper v4
   - B) Kyverno Native Policies
   - C) 使用 CEL expressions 的 ValidatingAdmissionPolicy
   - D) Pod Security Standards enforcement

<details>
<summary>显示答案</summary>

**答案: C) 使用 CEL expressions 的 ValidatingAdmissionPolicy**

**解析:**
ValidatingAdmissionPolicy (KEP-3488) 使用 Common Expression Language (CEL) expressions 提供进程内验证，消除了对外部 webhook servers 的需求。升级路径：v1.26 中为 alpha，v1.28 中为 beta，v1.30 (Apr 2024) 中为 GA。它使用三种 resource types：ValidatingAdmissionPolicy（rules）、ValidatingAdmissionPolicyBinding（binding to resources）以及可选的 parameter CRDs。与基于 webhook 的 admission control 相比，这降低了延迟、复杂性和 failure domains。

</details>

---

7. KYAML 是什么，它当前的状态是什么？
   - A) Kubernetes YAML linter；在 1.35 中达到 GA
   - B) 一个用于 Kubernetes 的更安全、歧义更少的 YAML 子集，使用严格格式；在 1.35 中为 beta，默认启用
   - C) YAML-to-JSON converter tool；在 1.34 中为 alpha
   - D) Kubernetes manifest validation schema；自 1.30 起稳定

<details>
<summary>显示答案</summary>

**答案: B) 一个用于 Kubernetes 的更安全、歧义更少的 YAML 子集，使用严格格式；在 1.35 中为 beta，默认启用**

**解析:**
KYAML 是专为 Kubernetes 设计的更严格 YAML 子集，可消除 YAML 臭名昭著的歧义。它使用花括号 ({}) 表示 maps，方括号 ([]) 表示 lists，并对所有 strings 使用双引号。它在 v1.34 中作为 alpha 引入，在 v1.35 (Dec 2025) 中升级到 beta，并默认启用。可以使用 `KUBECTL_KYAML=false` 禁用它。这解决了 YAML 中长期存在的问题，例如 “Norway problem”（NO 被解释为 boolean false）。

</details>

---

8. EKS clusters 推荐的版本升级规划策略是什么？
   - A) 跳过版本以尽量减少升级频率（例如，1.29 → 1.33）
   - B) 每次升级一个 minor version，在 staging 中测试 feature gates，在生产前验证 API 兼容性和 add-on 对齐
   - C) 始终使用最新版本，并依赖 extended support 进行 rollback
   - D) 等到某个版本进入 extended support 后再升级，以确保稳定性

<details>
<summary>显示答案</summary>

**答案: B) 每次升级一个 minor version，在 staging 中测试 feature gates，在生产前验证 API 兼容性和 add-on 对齐**

**解析:**
EKS 要求按顺序进行 minor version upgrades（1.33 → 1.34 → 1.35；不支持跳过）。最佳实践：(1) 首先在 staging environments 中测试新的 feature gates 和 API changes，(2) 验证 add-on compatibility 是否符合目标版本，(3) 运行 `kubectl convert` 检查 deprecated APIs，(4) 先升级 control plane，然后升级 add-ons，最后升级 node groups。保持在 standard support 上可以避免 extended support 带来的 6 倍成本增加，并确保能够获得最新的 security patches。

</details>
