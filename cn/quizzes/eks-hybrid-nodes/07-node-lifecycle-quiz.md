# Node 生命周期管理测验

> 本测验用于测试你对 [Node Lifecycle Management](../../eks-hybrid-nodes/07-node-lifecycle.md) 文档的理解。

---

1. 在 NodeConfig kubelet 配置中设置 `systemReserved` 和 `kubeReserved` 的主要目的是什么？
   - A) 自动调整 Pod 资源请求
   - B) 为系统进程和 Kubernetes 组件预留资源，以确保 Node 稳定性
   - C) 增加 Node 上可用的总资源
   - D) 确定 Pod 调度优先级

<details>
<summary>显示答案</summary>

**答案：B) 为系统进程和 Kubernetes 组件预留资源，以确保 Node 稳定性**

**解释：**
`systemReserved` 为 OS 和系统守护进程（sshd、udev 等）预留资源，而 `kubeReserved` 为 kubelet 和 containerd 预留资源。这可以防止 Pod 消耗所有 Node 资源，从而保持 Node 稳定性。

</details>

---

2. kubelet 的 `evictionHard` 和 `evictionSoft` 有什么区别？
   - A) `evictionHard` 是软限制，`evictionSoft` 是硬限制
   - B) `evictionHard` 会触发立即驱逐，而 `evictionSoft` 会在宽限期后驱逐
   - C) `evictionHard` 只会驱逐 Pod，而 `evictionSoft` 会关闭 Node
   - D) 两个设置的行为完全相同，只是名称不同

<details>
<summary>显示答案</summary>

**答案：B) `evictionHard` 会触发立即驱逐，而 `evictionSoft` 会在宽限期后驱逐**

**解释：**
当达到 `evictionHard` 阈值时，kubelet 会立即驱逐 Pod。只有当阈值持续达到 `evictionSoftGracePeriod` 中指定的时长时，`evictionSoft` 才会驱逐，从而避免突然终止 Pod。

</details>

---

3. 根据 Kubernetes 版本偏差策略，当 EKS control plane 为版本 1.31 时，可以运行的最旧 kubelet 版本是什么？
   - A) 1.27
   - B) 1.28
   - C) 1.29
   - D) 1.30

<details>
<summary>显示答案</summary>

**答案：B) 1.28**

**解释：**
根据 Kubernetes 版本偏差策略，kubelet 最多可以比 API server 旧三个次要版本。当 API server 为 1.31 时，kubelet 与 1.31、1.30、1.29 和 1.28 兼容。版本 1.27 是 n-4，因此不受支持。

</details>

---

4. 金丝雀升级策略的核心原则是什么？
   - A) 同时升级所有 Node
   - B) 先升级一个 Node，验证后再继续升级其余 Node
   - C) 删除 Node 并创建新的 Node
   - D) 执行零停机的就地升级

<details>
<summary>显示答案</summary>

**答案：B) 先升级一个 Node，验证后再继续升级其余 Node**

**解释：**
金丝雀升级会先升级一个“金丝雀”Node 并验证结果。如果未发现问题，则对其余 Node 继续执行滚动升级，从而最大限度降低风险。

</details>

---

5. 初始化 hybrid nodes 时，nodeadm 会自动分配哪个 label？
   - A) `node-role.kubernetes.io/hybrid=true`
   - B) `topology.kubernetes.io/zone=on-premises`
   - C) `eks.amazonaws.com/compute-type=hybrid`
   - D) `kubernetes.io/os=hybrid`

<details>
<summary>显示答案</summary>

**答案：C) `eks.amazonaws.com/compute-type=hybrid`**

**解释：**
nodeadm 在 hybrid node 初始化期间会自动分配 `eks.amazonaws.com/compute-type=hybrid` label。无需将此 label 手动添加到 `--node-labels`，它用于 Cilium affinity、workload 放置等场景。

</details>

---

6. 当 SSM Hybrid Activation 过期时，正确操作是什么？
   - A) 延长现有 activation 的到期日期
   - B) 创建新的 SSM Hybrid Activation 并更新 nodeconfig.yaml
   - C) 切换到 IAM Roles Anywhere
   - D) 重启 kubelet 以自动续期

<details>
<summary>显示答案</summary>

**答案：B) 创建新的 SSM Hybrid Activation 并更新 nodeconfig.yaml**

**解释：**
SSM Hybrid Activation 一旦过期，就无法延长其到期日期。你必须创建新的 activation，更新 nodeconfig.yaml 中的 `activationCode` 和 `activationId`，并在必要时重新注册 Node。

</details>

---

7. 升级 Kubernetes 组件的正确顺序是什么？
   - A) 先升级 Node，然后升级 control plane
   - B) 同时升级 control plane 和 Node
   - C) 先升级 control plane (EKS)，然后升级 Node
   - D) 顺序无关紧要

<details>
<summary>显示答案</summary>

**答案：C) 先升级 control plane (EKS)，然后升级 Node**

**解释：**
根据 Kubernetes 版本偏差策略，kubelet 不能比 API server 更新。必须始终先升级 control plane，然后升级 Node。在 control plane 之前升级 Node 会导致兼容性问题。

</details>

---

8. 如果配置了 `shutdownGracePeriod: 60s` 和 `shutdownGracePeriodCriticalPods: 20s`，普通 Pod 会获得多少终止宽限时间？
   - A) 20 秒
   - B) 40 秒
   - C) 60 秒
   - D) 80 秒

<details>
<summary>显示答案</summary>

**答案：B) 40 秒**

**解释：**
`shutdownGracePeriodCriticalPods` 包含在 `shutdownGracePeriod` 之内。从总共 60 秒的宽限期中减去为 critical pods 预留的 20 秒后，普通 Pod 终止剩余 40 秒。Critical pods（优先级类为 system-cluster-critical 或 system-node-critical）会在最后 20 秒内终止。

</details>
