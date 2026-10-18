# Kubernetes 版本特性与路线图测验

> **最后更新**：2026 年 9 月 12 日

请参阅[源章节](../../eks/12-kubernetes-version-roadmap.md)，了解各版本的前提条件以及审计证据的局限。

1. Kubernetes 次要版本的发布节奏是什么？

   - A) 每年发布一个特性版本
   - B) 每年大约发布三个次要版本，间隔约四个月
   - C) 每月发布次要版本
   - D) 按 AWS 大会日程固定发布

<details>
<summary>显示答案</summary>

**答案：B) 每年大约发布三个次要版本，间隔约四个月**

上游次要版本通常每年发布约三次；补丁版本遵循另一套节奏。上游补丁支持政策大致为 14 个月（12 个月常规支持，加 2 个月维护支持）。EKS 标准支持也持续 14 个月，但从该版本在 EKS 上正式可用时开始计算，因此这两个日历不能混为一谈。

</details>

---

2. EKS 标准支持和扩展版本支持的费用有何不同？

   - A) 标准支持免费
   - B) 标准支持：14 个月，每集群小时 $0.10；扩展支持：再延长 12 个月，每集群小时总计 $0.60
   - C) 扩展支持意味着所有旧版本都会永久受支持
   - D) 扩展支持不提供安全补丁

<details>
<summary>显示答案</summary>

**答案：B) 标准支持：14 个月，每集群小时 $0.10；扩展支持：再延长 12 个月，每集群小时总计 $0.60**

这些是版本支持费用，不包含计算、存储和网络等全部账单。`EXTENDED` 是默认升级策略；标准支持结束后，`STANDARD` 策略可能导致集群自动升级。扩展支持期间也会提供相关安全补丁。请参考当前版本日历，并结合实际支持结束日期和工作负载风险进行规划。

</details>

---

3. 原生 sidecar 容器何时达到稳定版？

   - A) 1.28
   - B) 1.31
   - C) 1.33
   - D) 1.35

<details>
<summary>显示答案</summary>

**答案：C) 1.33**

其发布路径为：1.28 Alpha → 1.29 Beta → 1.33 稳定版。可重启的 init container 使用 `restartPolicy:Always`。启动顺序取决于 `started`/`startupProbe` 状态；优雅终止使用 Pod 共享的终止时间预算。功能达到 GA 并不保证每个辅助容器都能优雅退出，也不代表代理镜像配置正确。

</details>

---

4. 容器原地调整大小可以做什么，何时达到稳定版？

   - A) 扩缩副本；1.30
   - B) 调整现有 Pod 的 CPU/内存分配；1.35，但受重启和运行时限制
   - C) 扩展 PVC；1.31
   - D) 不重启进程就更新镜像；1.34

<details>
<summary>显示答案</summary>

**答案：B) 调整现有 Pod 的 CPU/内存分配；1.35，但受重启和运行时限制**

此功能在 1.27 为 Alpha、1.33 为 Beta、1.35 达到稳定版。容器的 `resizePolicy` 控制重启行为，资源调整也可能保持待处理或无法满足。PATCH 请求被接受或 `containerID` 未变化，都不能证明 cgroup 调整已经完成或没有造成中断。请对比期望资源与上报资源、generation 和 conditions。VPA 模式各有自己的版本与功能门控。

</details>

---

5. Kubernetes 1.31 中的 DRA 状态是什么？

   - A) 经典 DRA 被 Device Plugins v2 取代
   - B) DRA 仍处于 Alpha；结构化 API 持续演进，而经典分配仍由单独的功能门控控制
   - C) DRA 已经达到 GA
   - D) 稳定版 v1 请求语法与所有旧版 Alpha API 完全相同

<details>
<summary>显示答案</summary>

**答案：B) DRA 仍处于 Alpha；结构化 API 持续演进，而经典分配仍由单独的功能门控控制**

1.31 版本及源章节显示，`DRAControlPlaneController` 仍是默认禁用的 Alpha 功能门控；它在 1.32 中被移除。DRA 核心功能在 1.32 达到 Beta，并在 1.34 达到稳定版。当前 v1 请求使用 `exactly`；还必须核验实际驱动程序、ResourceSlices 和属性。原测验中关于“1.31 已移除”的答案是错误的。

</details>

---

6. 哪项原生 CEL admission validation 功能在 1.30 达到稳定版？

   - A) OPA Gatekeeper v4
   - B) 强制要求参数 CRD
   - C) ValidatingAdmissionPolicy
   - D) 所有变更型 admission 机制

<details>
<summary>显示答案</summary>

**答案：C) ValidatingAdmissionPolicy**

ValidatingAdmissionPolicy 由 policy 和 binding 组成；它可以使用参数对象，但参数对象不一定要是 CRD。对于适用的逻辑，它可以避免使用外部验证 webhook，但错误或 `failurePolicy` 仍可能影响请求。请限定 binding 的作用范围，并区分 Audit 与 Deny。MAP 变更功能是另一项独立特性，于 1.36 达到稳定版。

</details>

---

7. 根据已核实的发布历史，KYAML 是什么？

   - A) API server 验证器，会拒绝所有普通 YAML anchor
   - B) kubectl 的输出格式：1.34 Alpha、1.35–1.36 Beta、1.37 稳定版
   - C) 需要通过支持工单启用的 EKS 服务端新特性
   - D) 要求将每份输入 manifest 转换为 YAML 1.2

<details>
<summary>显示答案</summary>

**答案：B) kubectl 的输出格式：1.34 Alpha、1.35–1.36 Beta、1.37 稳定版**

KYAML 对应 KEP-5295。原生 `kubectl 1.36.2` 测试接受了普通 YAML anchor，并输出 KYAML。`KUBECTL_KYAML=false` 会禁用该输出打印器；即使如此，KYAML 输入仍可解析并输出为 JSON。格式化与 schema/admission validation 是两个不同环节。审查时，上游 1.37 已经发布；这并不意味着 EKS 已提供 1.37。

</details>

---

8. 适当的 EKS 升级规划方式是什么？

   - A) 跳过次要版本以节省时间
   - B) 逐个演练次要版本升级，核实实际兼容性和资源所有权，并准备恢复方案
   - C) 将扫描器返回码为 0 视为完整证明
   - D) 控制平面升级后始终按固定顺序更新所有 add-on

<details>
<summary>显示答案</summary>

**答案：B) 逐个演练次要版本升级，核实实际兼容性和资源所有权，并准备恢复方案**

请使用当前支持日历、manifest 与客户端使用情况证据、准确的 add-on 兼容性信息，以及适合具体计算类型的操作顺序。有些前置条件必须在控制平面更新前满足。记录实际 update ID；验证就绪状态和数据，并区分 Pod 原地调整、节点替换和扩缩容。EKS 原生回滚有条件：必须在原地升级完成后的 7 天内执行。它不等同于数据库回滚，也不能作为绕过其他控制措施的许可。

</details>
