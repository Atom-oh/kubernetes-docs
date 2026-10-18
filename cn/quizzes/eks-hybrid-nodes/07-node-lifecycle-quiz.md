# Node 生命周期管理测验

> 本测验用于检验你对 [节点生命周期管理](../../eks-hybrid-nodes/07-node-lifecycle.md) 文档的理解。

---

1. 在 NodeConfig 的 kubelet 配置中设置 `systemReserved` 和 `kubeReserved`，主要目的是什么？
   - A) 自动调整 Pod 的资源请求
   - B) 计算 Node Allocatable 时，为系统进程和 Kubernetes 组件预留资源
   - C) 增加 Node 上的总可用资源
   - D) 确定 Pod 的调度优先级

<details>
<summary>显示答案</summary>

**答案：B) 计算 Node Allocatable 时，为系统进程和 Kubernetes 组件预留资源**

**解释：**
`systemReserved` 为操作系统和系统守护进程（如 sshd、udev）预留资源；`kubeReserved` 为 kubelet 和 containerd 预留资源。这些预留会减少可分配给 Pod 的容量。要通过 cgroup 强制限制主机进程资源，还需额外配置；仅设置这两个字段并不能保证系统稳定。

</details>

---

2. kubelet 的 `evictionHard` 和 `evictionSoft` 有什么区别？
   - A) `evictionHard` 是软阈值，`evictionSoft` 是硬阈值
   - B) `evictionHard` 没有软阈值的持续观察宽限期；`evictionSoft` 要求阈值持续一段时间
   - C) `evictionHard` 只驱逐 Pod，而 `evictionSoft` 会关闭 Node
   - D) 两者行为完全相同，只是名称不同

<details>
<summary>显示答案</summary>

**答案：B) `evictionHard` 没有软阈值的持续观察宽限期；`evictionSoft` 要求阈值持续一段时间**

**解释：**
kubelet 会先尝试在 Node 级别回收资源，必要时再驱逐 Pod。硬阈值没有软阈值的观察期，触发后会驱逐 Pod，且不给 Pod 终止宽限期。软阈值必须持续达到 `evictionSoftGracePeriod` 指定的时间；`evictionMaxPodGracePeriod` 则单独限制 Pod 的终止宽限期。这些设置不能阻止硬阈值驱逐或 OOM。

</details>

---

3. 根据 Kubernetes 版本偏差策略，在历史示例中 API server 为 1.31 时（不考虑当前 EKS 是否提供相应版本），可运行的最旧 kubelet 版本是什么？
   - A) 1.27
   - B) 1.28
   - C) 1.29
   - D) 1.30

<details>
<summary>显示答案</summary>

**答案：B) 1.28**

**解释：**
根据 Kubernetes 版本偏差策略，kubelet 最多可以比 API server 低三个次要版本。API server 为 1.31 时，兼容的 kubelet 版本包括 1.31、1.30、1.29 和 1.28。1.27 比 API server 低四个次要版本（n-4），不受支持。

</details>

---

4. 金丝雀升级策略的核心原则是什么？
   - A) 同时升级所有 Node
   - B) 先升级一个 Node 并验证，再继续升级其余 Node
   - C) 删除 Node 并创建新 Node
   - D) 执行零停机的就地升级

<details>
<summary>显示答案</summary>

**答案：B) 先升级一个 Node 并验证，再继续升级其余 Node**

**解释：**
金丝雀升级会先升级一个“金丝雀”Node 并验证结果。确认没有问题后，再对其余 Node 执行滚动升级，以降低风险。

</details>

---

5. 初始化 hybrid nodes 时，nodeadm 会自动分配哪个标签？
   - A) `node-role.kubernetes.io/hybrid=true`
   - B) `topology.kubernetes.io/zone=on-premises`
   - C) `eks.amazonaws.com/compute-type=hybrid`
   - D) `kubernetes.io/os=hybrid`

<details>
<summary>显示答案</summary>

**答案：C) `eks.amazonaws.com/compute-type=hybrid`**

**解释：**
nodeadm 会在初始化 hybrid node 时自动分配 `eks.amazonaws.com/compute-type=hybrid` 标签。无需将此标签手动添加到 `--node-labels`；它可用于 Cilium 亲和性规则、工作负载放置等场景。

</details>

---

6. SSM activation 已过期，但对应的 Node 已经注册。正确做法是什么？
   - A) 延长现有 activation 的有效期
   - B) 保留现有注册；只有需要注册新 Node 时才使用新的 activation
   - C) 切换到 IAM Roles Anywhere
   - D) 重启 kubelet 以自动续期

<details>
<summary>显示答案</summary>

**答案：B) 保留现有注册；只有需要注册新 Node 时才使用新的 activation**

**解释：**
activation 过期会阻止新的注册。已注册的 Node 会继续受 Systems Manager 管理，直到被显式注销。不要仅因 activation 过期就卸载或重新注册运行正常的 Node。SSM Agent 凭证、IAM 角色权限和网络连接是彼此独立的问题。

</details>

---

7. Node 已与 control plane 处于相同的次要版本。要升级到下一个次要版本，应按什么顺序操作？
   - A) 先升级 Node，再升级 control plane
   - B) 同时升级 control plane 和 Node
   - C) 先升级 control plane（EKS），再升级 Node
   - D) 顺序无关紧要

<details>
<summary>显示答案</summary>

**答案：C) 先升级 control plane（EKS），再升级 Node**

**解释：**
根据 Kubernetes 版本偏差策略，kubelet 不能比 API server 更新。因此，在这个跨次要版本的升级中，应先升级 control plane，再升级 Node。落后于 control plane 的 Node 可以先升级到当前 control plane 版本；这种追平版本的操作不违反版本偏差策略。

</details>

---

8. 如果配置了 `shutdownGracePeriod: 60s` 和 `shutdownGracePeriodCriticalPods: 20s`，为普通 Pod 组分配的关机窗口总时长是多少？
   - A) 20 秒
   - B) 40 秒
   - C) 60 秒
   - D) 80 秒

<details>
<summary>显示答案</summary>

**答案：B) 40 秒**

**解释：**
`shutdownGracePeriodCriticalPods` 包含在 `shutdownGracePeriod` 总时长内。总计 60 秒中，为关键 Pod 预留 20 秒，剩下 40 秒供普通 Pod 终止；最后的 20 秒分配给关键 Pod。这表示配置的时间窗口，并不保证强制关机时每个 Pod 都能获得相同的终止宽限期；单个 Pod 的 `terminationGracePeriodSeconds` 也会影响其终止时间。

</details>
