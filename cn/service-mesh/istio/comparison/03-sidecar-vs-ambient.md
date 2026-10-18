# Sidecar 与 Ambient 模式选择指南（EKS 1.36 测试结果）

> **报告中的测试版本**：Istio 1.30.2 / EKS 1.36.2 / Fortio 1.69.4
> **原始报告日期**：2026 年 8 月 21 日 · **内容审阅**：2026 年 9 月 11 日

本文保留了报告中给出的 mTLS、NetworkPolicy、延迟和滚动更新测量结果。报告未附完整原始归档和准确的运行脚本，本次审阅也没有重新创建 AWS 集群。配置和算术检查并不构成对这些结果的独立复现。

附录现已修订为**实验室示例**，用于纠正具体的脚本/配置缺陷。不得将其描述为历史数据的准确来源。进行新测量时，请保留实际软件、镜像摘要、策略和产物；不要将这些结果重新标注为 Istio 1.31 或其他版本。

## 决策摘要

| 要求 | Sidecar | Ambient（L4，无 waypoint） | Ambient（L7，有 waypoint） | Cilium |
|---|---|---|---|---|
| mTLS | 报告称 STRICT 检查通过 | 报告称 STRICT 检查通过 | 报告称 STRICT 检查通过 | 未测量；身份双向认证与单独启用的 WireGuard/IPsec 并非一个等同于 STRICT 的开关 |
| NetworkPolicy | 测试中的应用端口规则有效 | 测试中的流量还需要 TCP 15008 | 测试中的流量还需要 TCP 15008 | 未测量；Cilium 可实施标准 Kubernetes NetworkPolicy 和 CiliumNetworkPolicy/集群范围扩展 |
| 报告中的高于基线的 P50 |+1.29 ms|+0.04 ms|+1.86 ms|未测量|
| 未调优的滚动更新 |324 个 HTTP 503 + 2 个非 HTTP 错误 /60,000|0 个 HTTP 503 + 195 个非 HTTP 错误 /60,000|1,528 个 HTTP 503 + 84 个非 HTTP 错误 /59,913|未测量|
| 加固后的滚动更新 |观察到 0 个错误 /60,000|观察到 0 个错误 /60,000|648 个 HTTP 503 /60,000|未测量|

在本报告中，Ambient L4 的观测到的 P50 差异较小，且相比未经调优的 sidecar，非成功响应更少。sidecar 和 Ambient L4 在加固后的样本中均记录到零错误。HTTP 503 计数为零并不等于零停机；waypoint 观测到的错误比例也无法证明存在固有故障率，或证明其原因是 IP 重用。

先选择所需功能，再根据工作负载预算验证总错误数、延迟、身份和运维情况。Cilium 列仅描述其文档所述能力；本轮测试没有部署 Cilium。

## 1. mTLS：测试结果（EKS 1.36.2、Istio 1.30.2）

原始报告提到一个专用的 `mesh-isolated-test` 集群、独立 VPC、Amazon Linux 2023 arm 64 m 7g.xlarge 节点，以及应用于三个 mesh 命名空间的命名空间级 STRICT PeerAuthentication。报告称控制平面和工作节点的 Kubernetes 版本均为 1.36.2。

记录到的明文 Pod-IP 尝试均失败：

```text
plaintext-client -> sidecar echo pod:8080  => connection reset
plaintext-client -> ambient-L4 echo:8080  => EOF
plaintext-client -> ambient-L7 echo:8080  => EOF
```

记录到的网格内 Service 调用在三种模式下均返回 HTTP 200。与 Envoy 相关的响应头有所不同，但响应头存在或缺失，不能证明加密状态或完整的代理路径。

证书命令检查的是持有/请求证书的代理。代理不是证书颁发者：

| 工作负载 | 检查的代理 | SPIFFE ID | 根 CA |
|---|---|---|---|
| ambient-L4 echo | ztunnel | `spiffe://cluster.local/ns/mesh-test-ambient-l4/sa/default` | 共享 |
| ambient-L7 echo | ztunnel | `spiffe://cluster.local/ns/mesh-test-ambient-l7/sa/default` | 共享 |
| sidecar echo | istio-proxy | `spiffe://cluster.local/ns/mesh-test-sidecar/sa/default` | 共享 |


所示 ID 是**命名空间/ServiceAccount 身份**。使用同一默认 ServiceAccount 的 Echo 和客户端 Pod 共享该身份；这些不是每个 Pod 唯一的 SPIFFE ID。工作负载证书由 Istiod 或配置的 CA 提供。

报告中的负向/正向案例与这些流量上的 STRICT 强制执行情况一致。但它们并不能证明集群中每条路径、每种协议、每个来源或每种绕过方式都受到覆盖。Ambient 使用 Istio CNI 网络命名空间捕获路径，并通过 TCP 15008 上的 HBONE 传输；sidecar 模式使用工作负载代理。有关强制执行边界，请参阅 [mTLS 指南](../security/01-mtls.md)。

## 2. NetworkPolicy：测试结果

报告使用了 VPC CNI NetworkPolicy 强制执行，并将代理版本标识为 `v1.3.5-eksbuild.3`。报告未归档完整的插件配置/版本、策略端点或节点状态证据。历史结果应保留报告中的版本。

**作者报告称已确认强制执行后记录的入站端口测试：**

| 模式 | 结果 |
|---|---|
| sidecar | ✅ 200 OK（未受影响） |
| ambient-L4 | ❌ 已阻止（`i/o timeout`） |
| ambient-L7 | ❌ 已阻止（`i/o timeout`） |


**允许 8080 和 HBONE15008 后记录的结果：**

| 模式 | 结果 |
|---|---|
| ambient-L4 | ✅ 200 OK（已恢复） |
| ambient-L7 | ✅ 200 OK（已恢复） |


这些结果说明了 HBONE 对所测路径的重要性。但这并不意味着所有现有策略都能在 sidecar 模式下原样工作，也不意味着允许 15008 就构成了完整的最小权限 Ambient 策略。源选择器、waypoint 路径、DNS/控制平面出站流量以及 CNI 实现都会产生影响。网络策略看到的是隧道端口；请为隧道内部的流量使用适当的身份/端口策略。

作者报告称，启用强制执行后重新创建 Pod，使负向对照生效。这只是所报告配置中的一次观测，并不能证明所有当前代理都只能在 CNI ADD 时附加，也不能证明策略普遍不会追溯生效。测量前请验证协调状态和实际强制执行情况。当前 AWS 文档区分了标准启动模式和严格启动模式：标准启动模式会在策略配置完成前允许流量；严格启动模式则需要明确放行必需的依赖流量。

当前 AWS 文档支持由控制器管理的 Pod，包括 Deployments、StatefulSets、DaemonSets 和 Jobs；独立 Pod 则有额外限制。Cilium 单独支持标准 NetworkPolicy 及其自身的策略 CRD。不能根据某一种实现上的结果推断另一种实现的行为。

## 3. 延迟：测试结果（T5）

报告描述了稳态 Fortio 测试：请求 200 QPS、运行 60 秒、16 个连接；在同一 Graviton 集群上，每个测试用例成功处理了 12,000 个请求：

| 测试用例 | P50 | P75 | P90 | P99 | P99.9 |
|---|---|---|---|---|---|
| no-mesh（基线） | 0.82ms | 1.33ms | 1.73ms | 1.97ms | 2.00ms |
| sidecar | 2.11ms | 2.60ms | 2.89ms | 3.91ms | 8.00ms |
| ambient-L4（无 waypoint） | 0.86ms | 1.34ms | 1.74ms | 1.98ms | 2.93ms |
| ambient-L7（有 waypoint） | 2.68ms | 3.06ms | 3.63ms | 3.98ms | 7.67ms |


报告中的 P50 差值为：sidecar 1.29 ms、Ambient L4 0.04 ms、Ambient L7 1.86 ms。这些减法计算正确。在将较小差异称为可忽略，或将其纳入交易/SLO 预算之前，还需要重复运行的方差、资源/放置细节以及实际结果 JSON。

附录使用基于持续时间的 Fortio 命令。请求 QPS × 持续时间表示名义上的提供负载，并不能保证准确的调用次数；请使用每次运行记录的 DurationHistogram.Count/RetCodes。除非重新运行实验并保留记录，否则不要更新历史版本标签。


## 4. 零停机滚动更新：503 测试结果（核心发现）

### 背景

Pod 终止、端点传播、应用/代理排空、连接池和超时都可能影响滚动更新失败。原报告将原因归结为目标 IP 重用竞争以及缺少 ztunnel 通知，这只是一个**假设**，并非展示的计数所能证实的原因。在将结果归因于某种机制之前，请通过代理响应标志、实际上游主机、端点/Pod UID 时间线和连接证据予以确认。

报告使用了六个 Echo 副本，并在每个 mesh 命名空间中运行一个 Fortio 客户端，请求 100 QPS、运行 600 秒，同时反复重启目标 Deployment。应用清单原本计划保持一致；但不同模式下，注入/共享的代理资源以及实际滚动更新暴露情况仍有所不同。

### 结果

| 模式 | 滚动更新轮次 | 请求数 | 503 数量 | 503 比例 | 非 HTTP 结果（-1） | 使用的 Socket 数 |
|---|---|---|---|---|---|---|
| sidecar | 42 | 60,000 | 324 | **0.5%** | 2 (0.0%) | 350 |
| ambient-L4（无 waypoint） | 64 | 60,000 | **0** | **0%** | 195 (0.3%) | 1,652 |
| ambient-L7（有 waypoint） | 65 | 59,913 | 1,528 | **2.6%** | 84 (0.1%) | 2,486 |


原文还提供了以下带注释的摘要，而非完整的机器可读产物：

<details>
<summary>记录的计数（已修正解释性注释）</summary>

```text
[sidecar]      42 rollouts, Sockets used: 350 (client concurrency: 16)
  Code 200 : 59674 (99.5 %)
  Code 503 : 324 (0.5 %)
  Code  -1 : 2   (0.0 %)

[ambient-L4]   64 rollouts, Sockets used: 1652
  Code 200 : 59805 (99.7 %)
  Code  -1 : 195 (0.3 %)   <- no HTTP response recorded; not a 503

[ambient-L7]   65 rollouts, Sockets used: 2486
  Code 200 : 58301 (97.3 %)
  Code 503 : 1528 (2.6 %)
  Code  -1 : 84  (0.1 %)
  (59,913 counted calls; nominal offered calls: 60,000; avg latency 50.4ms vs. ~2-3ms for the other two modes)

```

</details>

解读这些数值时须注意以下限制：

1. 根据计数调用数计算出的 HTTP 503 比例为 324/60,000 =0.54% 和 1,528/59,913 ≈2.55%；两者之比约为 4.72。原始四舍五入后的显示值 0.5%/2.6% 和“约 5 倍”描述的是这个样本，并非产品固有的倍数。
2. Ambient L4 有 195 个非 HTTP 失败，因此 HTTP 503 为零并不意味着零失败。Fortio 的 -1 表示非 HTTP 结果；具体属于 reset/EOF/timeout 中的哪一种，需要查看底层错误。
3. 与名义 60,000 次相比少了 87 次调用，这并不能证明有 87 个已启动请求从未完成。基于时间模式运行可能会统计到更少调用。请保留报告中的 59,913 和 50.4 ms 平均延迟，不要臆造缺失请求的状态。
4. Fortio 的 SocketCount 描述的是客户端 Socket，并非 waypoint 上游连接池的直接测量值。持续复用时，16 个 Socket 与配置的客户端并发数相符，但不能证明每个上游连接都正常。
5. 基线中完成的滚动更新次数为 42/64/65；滚动更新次数最多的是 Ambient L7，而不是 L4。滚动更新暴露程度不一致，且缺少资源/时间线产物，因此因果比较受到限制。

### 后续测试：优雅关闭加固后

原报告对所有模式均设置了 10 秒 preStop sleep 和 40 秒 Pod 终止宽限期。Sidecar 还设置了 EXIT_ON_ZERO_ACTIVE_CONNECTIONS=true 和 terminationDrainDuration 30s：

| 模式 | 滚动更新轮次 | Code 200 | Code 503 | Code -1 | 使用的 Socket 数 | 平均延迟 |
|---|---|---|---|---|---|---|
| sidecar（已加固） | 42 | 60,000 (100%) | **0** | **0** | 16 | 2.630ms |
| ambient-L4（已加固） | 38 | 60,000 (100%) | **0** | **0** | 395 | 1.189ms |
| ambient-L7（已加固） | 45 | 59,352 (98.9%) | 648 (1.1%) | **0** | 678 | 3.843ms |


| 模式 | 基线错误率 | 加固后错误率 | 变化 |
|---|---|---|---|
| sidecar | 0.5% 503 + 0% TCP | 0% 503 + 0% TCP | **本样本中观察到 0 个 503** |
| ambient-L4 | 0% 503 + 0.3% TCP | 0% 503 + 0% TCP | **本样本中观察到 0 个非 HTTP 错误** |
| ambient-L7 | 2.6% 503 + 0.1% TCP | 1.1% 503 + 0% TCP | 503 比例降低了一半以上 |


这些只是上述样本中的观测结果。Sidecar 改变了**两个因素**，因此不能把结果单独归因于 preStop。加固后的滚动更新次数 42/38/45 也各不相同。工作负载关闭调优改善了报告中的结果，但并不能证明剩余 waypoint 错误具有相同原因，也不能证明另外两种模式总能做到零错误。

宽限期包括 preStop 和容器终止时间。十秒 sleep 提供的是时间，并不能确认每次端点更新都已传播。在发布的 1.30.2 代码中，EXIT_ON_ZERO_ACTIVE_CONNECTIONS 会先等待配置的最短排空时长，然后每秒轮询下游监听器连接统计信息。该分支不会使用常规的 terminationDrainDuration 计时器；Kubernetes 终止时限和观测错误仍会产生影响。不要将其描述为立即退出，或无条件最多等待 30 秒。

### 将重试作为缓解措施的风险：测试结果（T2）

原报告描述了一个包含六个副本的订单服务、collector 和客户端；设置为 20 请求/秒、运行 300 秒，并使用带有三次重试和两秒单次尝试超时的 VirtualService 策略。以下数值作为**报告值保留，未经独立复现**：

| 模式 | 滚动更新轮次 | 已发送请求数 | 报告的客户端可见失败数 | 重复报告数（按报告所述） |
|---|---|---|---|---|
| sidecar（VirtualService 重试） | 11 | 9,135 | 15 (0.16%) | **0** |
| ambient-L7（waypoint 重试） | 12 | 7,229 | 21 (0.29%) | **0** |


原始附录无法支持以下解释：

- 其单个顺序客户端无限期运行，从未打印统计信息，并且仅在成功时才增加 sent 计数。在每秒最多迭代 20 次的上限下，300 秒运行无法达到 9,135 或 7,229 次迭代；服务器 0.1 秒延迟还会进一步限制实际速率。
- 三秒客户端超时可能会早于名义上的“原始请求加三次两秒尝试”完成。一条最终失败记录并不能说明所有重试都已耗尽。
- 订单服务器返回 201 时，collector 的报告错误被忽略。计数器重置与已在运行的客户端重叠，而且复制的 ambient 清单仍指向 sidecar 命名空间中的服务。
- X-Request-Id 是代理/追踪标识符，不一定是不可变的业务命令 ID。观测不完整时，重复报告计数为零并不能证明业务执行没有重复。
- 最终失败率较低并不能证明触发了重试。报告未包含有效路由、重试计数器和实际投递记录。

修订后的附录使驱动程序具有明确的运行边界和可观测性，使用独立的业务标识符，并将观测器失败视为未知/错误结果。但它无法修复旧数值的来源问题。其内存中的 collector 不是持久化事务账本，也不是幂等性实现。

### 区分原始失败与被重试掩盖的失败

mTLS 数据平面选择与 HTTP 重试策略是相互独立的决策。Sidecar Envoy 和 waypoint Envoy 可在 L7 重试 HTTP 请求；ztunnel 是 [L4 代理](https://istio.io/latest/docs/ambient/architecture/data-plane/)，无法解析 HTTP 503 或重放 HTTP 请求。

为确保基线公平，请在 POST/PUT/PATCH/DELETE 等写入路由上明确设置 attempts:0，并分别测量以下内容：

- 重试前的 HTTP 错误和非 HTTP 失败。
- 实际相关代理/集群上的 Envoy upstream_rq_retry 和 upstream_rq_retry_success 计数器。
- 上游投递/观测器记录数，包括原始请求。
- 最终客户端成功/失败结果及完整的客户端计数。
- 重复的稳定业务命令 ID、观测器失败和观测器重启。

| 数据平面 | mTLS/加密含义 | L7 重试位置 | 推荐用途 |
|---|---|---|---|
| Istio sidecar | 工作负载 SPIFFE 证书 mTLS | 每个 Pod 的 Envoy | 关键非幂等路径的保守基线 |
| Istio ambient L4 | ztunnel 之间的 HBONE 工作负载 mTLS | 无 | 仅需要 Istio mTLS 和 L4 策略时的首选候选方案 |
| Istio ambient L7 | HBONE 加 waypoint Envoy | 共享 waypoint | 仅用于需要 HTTP 路由或 L7 策略的服务 |
| Cilium 带外 + WireGuard/IPsec | 身份双向认证与 WireGuard/IPsec 等传输加密需分别选择 | L3/L4 加密层中无 | 需要身份策略和网络加密的现有 Cilium 数据平面 |


Cilium 这一项指的是其 L3/L4 认证/加密层；这并不意味着 Cilium 没有可选的 L7 代理功能。这里没有测量 Cilium 的性能或滚动更新行为。

Cilium 1.20.1 还提供独立的 [ztunnel 透明加密 Beta 功能](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/network/encryption-ztunnel.rst)，通过 `encryption.type: ztunnel` 选择。它提供带有命名空间注册机制的 TCP 工作负载 mTLS；两端都必须注册。它不支持 ClusterMesh 和使用 hostNetwork 的 Pod；已发布的指南还警告，除针对 HBONE 端口 15008 的情形外，常规 L4 策略在此路径上无法工作。这是一种独立的部署选择，有自己的 CA/引导要求。

本章报告的测量未涉及 ztunnel Beta 功能。

> **运维原则**：如果唯一要求是 mTLS，请先验证 Ambient L4，仅在需要 L7 策略或东西向 HTTP 路由的服务上添加 waypoint。如果禁用写入重试后测得的 Ambient 总错误数超过工作负载错误预算，那么对关键非幂等路径应保留 sidecar 作为基线。应用重试和幂等性仍需独立控制。

### 关于测试隔离的说明

原作者报告称，在共享集群上出现了干扰/资源消失问题，并且在首次尝试使用专用集群时，某台工作站的 current-context 曾发生更改。没有附带取证归档，因此这些报告无法确定资源删除原因，也不能证明 Istio 存在缺陷。

关键要求是明确隔离：使用受控测试集群、专用 kubeconfig/context/服务器检查、完整的资源清单，并保留产物。旧附录未包含其说明文字中提及的 context 防护措施。修订后的流程将其明确列出。仅使用不同命名空间并不能保证 CPU/网络或控制平面条件彼此独立。

## 5. 建议：分层方法

工作负载层级只是规划标签，并非安全保证：

| 工作负载要求 | 候选方案 | 所需验证 |
|---|---|---|
| 仅需 mTLS 和 L4 策略 | 优先尝试 Ambient L4；适用时保留经过验证的 sidecar 基线 | 实际身份、NetworkPolicy/内部端口强制执行、总失败数和延迟 |
| HTTP 路由或 L7 授权 | 选择合适的 waypoint、调用方 sidecar 或 gateway | 策略挂载正确、有效配置和工作负载错误预算 |
| 关键非幂等命令 | 所选数据平面均需明确写入重试策略和服务器端正确性控制 | 稳定业务 ID、持久化幂等性/事务、响应丢失和恢复测试 |
| 读取 API、通知和批处理 | 根据实际语义和所需功能选择 | 通知/批处理可能有副作用；即使可安全重试的读取请求也可能放大负载 |

报告中三个 mesh 命名空间共存的做法很有参考价值，但不能证明每种混合部署、工作负载或策略组合都安全。

### L4-only 的局限：还能否进行金丝雀部署？

ztunnel 不提供基于每个 HTTP 请求的 Header/路径路由、镜像流量或 HTTP 重试。**由 Istio 管理的** ingress gateway 可以在将流量转发至 Ambient 后端之前做出 L7 路由决策。Gateway API 本身是一种 API，不一定对应 Envoy Deployment：实际行为取决于 GatewayClass/控制器。

Istio VirtualService 可选择 DestinationRule 子集；标准 HTTPRoute backendRefs 通常选择 Services。不要把它们描述为同一种子集 API。

对于东西向 HTTP 请求路由，L7 决策必须发生在实际调用方/gateway/waypoint 路径上。仅在目标 B 上添加 sidecar，并不会使 Ambient L4 调用方通过出站 HTTP 策略选择 B-v 1/B-v 2。应使用 B 的 waypoint、合适的调用方代理，或其他经过明确设计的 L7 跳点。L4 连接级分配和基于副本的滚动更新策略，与按请求进行 HTTP 流量拆分是不同的机制。

请检查实际功能需求、CNI/策略行为、写入重试以及工作负载自身的测量结果。以下实验室示例用于收集新证据；它无法追溯证明原报告缺失的事实。


## 附录：复现这些测试

这是针对受控后续测试的修订流程，并非保证复制粘贴即可得到原始结果。本地检查覆盖语法、配置生成以及 Python 观测器/客户端行为。集群调度、网格策略挂载、CNI 强制执行和测量完整性仍需在实际实验室中验证。

### A. 集群配置（eksctl）

以下是原报告所述的**归档输入**。它说明了节点/网络选择；本次审计未执行此配置：

<details>
<summary>记录的 eksctl-cluster.yaml</summary>

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: mesh-isolated-test
  region: ap-northeast-2
  version: '1.36'
  tags:
    purpose: istio-sidecar-vs-ambient-retest
    ephemeral: 'true'
availabilityZones:
- ap-northeast-2a
- ap-northeast-2c
vpc:
  nat:
    gateway: Disable
managedNodeGroups:
- name: mesh-test-ng-arm64
  instanceType: m7g.xlarge
  amiFamily: AmazonLinux2023
  desiredCapacity: 3
  minSize: 3
  maxSize: 3
  volumeSize: 40
  privateNetworking: false
  labels:
    role: istio-mesh-test
  tags:
    ephemeral: 'true'
addons:
- name: vpc-cni
- name: coredns
- name: kube-proxy
- name: eks-pod-identity-agent
```

</details>

次要 Kubernetes 版本、未锁定版本的插件和当前 AMI 选择，无法复现原始控制平面补丁版本、节点镜像或代理版本。使用公共子网/无 NAT 的测试布局并非生产建议；应根据实际网络需求选择私有端点、IPv 6 或基于 NAT 的出站流量。

新测试请使用经批准且隔离的测试集群，并记录其 ARN/API 端点、节点/AMI/内核版本、CNI/代理配置及资源清单。不要在无关集群上启用先前未使用的策略，也不要替换共享 CRD。

### B. 安装 Istio（Gateway API CRD + ambient 配置档）

请根据目标集群记录设置以下输入。辅助函数会明确指定 kubeconfig/context，并重新检查其 API 服务器映射：

```bash
set -euo pipefail
: "${TEST_KUBECONFIG:?Set the dedicated kubeconfig file}"
: "${TEST_CONTEXT:?Set its explicit test context}"
: "${ISTIOCTL_BIN:?Set the path to the intended Istio 1.30.2 CLI}"
: "${EXPECTED_API_SERVER:?Set the approved API-server URL}"
: "${NS:?Select the test namespace}"
: "${RUN_DIR:?Set a new artifact directory for this run}"
case "$NS" in
  mesh-test-base|mesh-test-sidecar|mesh-test-ambient-l4|mesh-test-ambient-l7) ;;
  *) echo "Unexpected test namespace" >&2; exit 1 ;;
esac
check_mesh_context() {
  local actual
  actual=$(kubectl --kubeconfig "$TEST_KUBECONFIG" --context "$TEST_CONTEXT" \
    config view --minify -o jsonpath='{.clusters[0].cluster.server}') || return 1
  if [ "$actual" != "$EXPECTED_API_SERVER" ]; then
    echo "API-server mismatch; stopping" >&2
    return 1
  fi
}
kmesh() {
  check_mesh_context &&
    kubectl --kubeconfig "$TEST_KUBECONFIG" --context "$TEST_CONTEXT" "$@"
}
imesh() {
  check_mesh_context &&
    "$ISTIOCTL_BIN" --kubeconfig "$TEST_KUBECONFIG" --context "$TEST_CONTEXT" "$@"
}
check_mesh_context
mkdir -p "$RUN_DIR"
```

这可以避免依赖共享的 current-context 值，但无法防范所有并发集群或凭据更改。请妥善控制专用文件，并保留已验证的集群身份。

报告中的版本是 Istio 1.30.2。原附录中关于 Gateway API 1.1.0 兼容性的说法没有已安装软件包归档作为依据。已发布的 1.30.2 依赖项/一致性测试使用 1.5.1。对于修订后的 Gateway/HTTPRoute 测试用例，请先检查其他已安装的控制器，再使用匹配的标准软件包；不要将目录中的最新版本视为兼容性证据。

```bash
# Only for a new dedicated lab needing this compatible bundle.
kmesh apply --server-side -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.5.1/standard-install.yaml
imesh manifest generate -f ambient-overlay.yaml > "$RUN_DIR/istio-rendered.yaml"
# Review the render, existing ownership and installed version before installation.
imesh install -f ambient-overlay.yaml
```

单独使用 L4 Ambient 不需要 waypoint 资源。本实验包含一个 L7 测试用例，因此在创建 waypoint 前需要兼容的 Gateway API 资源。请使用预期的 Istio CLI/版本以及受支持的升级路径；不要悄然将历史测试升级到新版本。

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  profile: ambient
  values:
    cni:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: kubernetes.io/arch
                operator: In
                values:
                - arm64
    ztunnel:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: kubernetes.io/arch
                operator: In
                values:
                - arm64
  components:
    pilot:
      k8s:
        affinity:
          nodeAffinity:
            requiredDuringSchedulingIgnoredDuringExecution:
              nodeSelectorTerms:
              - matchExpressions:
                - key: kubernetes.io/arch
                  operator: In
                  values:
                  - arm64
```

该覆盖配置中的 CNI、ztunnel 和 Istiod arm 64 affinity 已通过原生 1.30.2 离线渲染检查。渲染检查不等同于部署测试。

### C. 命名空间和工作负载清单

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: mesh-test-base
---
apiVersion: v1
kind: Namespace
metadata:
  name: mesh-test-sidecar
  labels:
    istio-injection: enabled
---
apiVersion: v1
kind: Namespace
metadata:
  name: mesh-test-ambient-l4
  labels:
    istio.io/dataplane-mode: ambient
---
apiVersion: v1
kind: Namespace
metadata:
  name: mesh-test-ambient-l7
  labels:
    istio.io/dataplane-mode: ambient
```

以下应用模板适用于一种测试用例。请将每个 metadata.namespace 改为所选测试用例，并使用明确的 `-n "$NS"` 执行应用，这样不匹配时就会失败。应用设置应保持一致，同时也要记录不同的注入/共享代理配置。

<details>
<summary>修订后的 echo 和 Fortio 工作负载模板</summary>

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: echo
  namespace: mesh-test-sidecar
  labels:
    app: echo
spec:
  replicas: 6
  selector:
    matchLabels:
      app: echo
  template:
    metadata:
      labels:
        app: echo
    spec:
      nodeSelector:
        kubernetes.io/arch: arm64
        kubernetes.io/os: linux
      containers:
      - name: echo
        image: fortio/fortio:1.69.4@sha256:65633fc5e70f9745be8c311637fb8e484da31a366463028a11083ac0a098e3d3
        args:
        - server
        - -http-port
        - '8080'
        ports:
        - containerPort: 8080
        readinessProbe:
          httpGet:
            path: /fortio/
            port: 8080
          initialDelaySeconds: 2
          periodSeconds: 3
        resources:
          requests:
            cpu: 50m
            memory: 32Mi
          limits:
            cpu: 300m
            memory: 128Mi
---
apiVersion: v1
kind: Service
metadata:
  name: echo
  namespace: mesh-test-sidecar
spec:
  selector:
    app: echo
  ports:
  - port: 8080
    targetPort: 8080
    name: http
    appProtocol: http
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fortio-client
  namespace: mesh-test-sidecar
  labels:
    app: fortio-client
spec:
  replicas: 1
  selector:
    matchLabels:
      app: fortio-client
  template:
    metadata:
      labels:
        app: fortio-client
    spec:
      nodeSelector:
        kubernetes.io/arch: arm64
        kubernetes.io/os: linux
      containers:
      - name: fortio-client
        image: fortio/fortio:1.69.4@sha256:65633fc5e70f9745be8c311637fb8e484da31a366463028a11083ac0a098e3d3
        command:
        - /usr/bin/fortio
        args:
        - server
        - -http-port
        - '8081'
        - -redirect-port
        - disabled
        resources:
          requests:
            cpu: 50m
            memory: 32Mi
          limits:
            cpu: 300m
            memory: 128Mi
```

</details>

新的示例将报告中的 Fortio 版本固定为本次审阅时已核验的注册表摘要，并明确指定 HTTP 端口。原报告未归档镜像摘要或所有协议设置；这些修订不能证明旧测试使用了完全相同的字节内容。Fortio 镜像基于 scratch 构建：请使用其二进制文件，不要假设镜像内有 sh/curl/cat 等实用程序。

### D. mTLS：PeerAuthentication（§1）

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: strict
  namespace: mesh-test-sidecar
spec:
  mtls:
    mode: STRICT
---
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: strict
  namespace: mesh-test-ambient-l4
spec:
  mtls:
    mode: STRICT
---
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: strict
  namespace: mesh-test-ambient-l7
spec:
  mtls:
    mode: STRICT
```

对于 L7 命名空间：

```bash
imesh waypoint apply -n mesh-test-ambient-l7 --enroll-namespace --wait
kmesh -n mesh-test-ambient-l7 get gateways.gateway.networking.k8s.io -o yaml
```

负载测试前，请验证实际 Pod 注入/注册状态、证书和 Service 流量路径。直接对 Pod-IP 进行明文拒绝测试可检验 L4 强制执行，但不能证明每种可能的调用都会经过 waypoint 或 L7 策略。

### E. NetworkPolicy（§2）

请通过插件所属管理方，将 NetworkPolicy opt-in 设置合并到**经过审阅的现有**插件配置中：

```json
{"enableNetworkPolicy":"true"}
```

记录实际的 CNI/代理版本以及 standard/strict 启动模式。不要使用仅包含单个字段的更新和 OVERWRITE 来盲目替换其他插件设置。协调完成后，请检查生成的策略端点和负向对照流量。如已安装环境要求，请重新创建目标测试 Pod；历史观测并不代表普遍的非追溯生效规则。

```bash
kmesh -n "$NS" get policyendpoints.networking.k8s.aws
```

测试 1 和测试 2 是针对同一个选定工作负载/策略名称的连续替代配置：

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-8080-only
  namespace: mesh-test-ambient-l4
spec:
  podSelector:
    matchLabels:
      app: echo
  policyTypes:
  - Ingress
  ingress:
  - ports:
    - protocol: TCP
      port: 8080
```

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-8080-only
  namespace: mesh-test-ambient-l4
spec:
  podSelector:
    matchLabels:
      app: echo
  policyTypes:
  - Ingress
  ingress:
  - ports:
    - protocol: TCP
      port: 8080
    - protocol: TCP
      port: 15008
```

请在选定测试用例的命名空间中逐一应用。这些不限制来源的端口规则是可达性实验，并非完整的租户隔离方案。其他已选策略会与其叠加。请测试实际的 DNS、控制平面、来源以及内部端口/身份要求，不要假定只放行一个隧道端口就能保留所有原有策略边界。


### F. 滚动更新 + 503 测试（T1，§4）

每个测试用例都应从已就绪的工作负载和新的产物目录开始。以下有界循环会记录滚动更新间隔以及 Fortio 的实际结果。它的启动并未与负载生成器形成原子屏障：请使用时间戳确定重叠暴露的时段，包括负载停止后才结束的滚动更新。

```bash
# Run after loading the context helpers above. Requires GNU timeout.
DUR=600
kmesh -n "$NS" rollout status deployment/echo --timeout=120s
kmesh -n "$NS" rollout status deployment/fortio-client --timeout=120s
CLIENT=$(kmesh -n "$NS" get pods -l app=fortio-client \
  -o jsonpath='{.items[0].metadata.name}')
test -n "$CLIENT"
STOP_FILE="$RUN_DIR/stop-rollouts"
test ! -e "$STOP_FILE"
trap 'touch "$STOP_FILE"' EXIT INT TERM
(
  begin=$(date +%s)
  while [ $(( $(date +%s) - begin )) -lt "$DUR" ] && [ ! -e "$STOP_FILE" ]; do
    cycle_start=$(date +%s)
    kmesh --request-timeout=15s -n "$NS" rollout restart deployment/echo || exit 1
    kmesh --request-timeout=75s -n "$NS" rollout status deployment/echo \
      --timeout=60s || exit 1
    printf '%s,%s\n' "$cycle_start" "$(date +%s)" >> "$RUN_DIR/rollout-times.csv"
  done
) >"$RUN_DIR/rollouts.log" 2>&1 &
ROLLOUT_PID=$!

check_mesh_context
load_status=0
timeout --signal=TERM --kill-after=5s "$((DUR+30))s" \
  kubectl --kubeconfig "$TEST_KUBECONFIG" --context "$TEST_CONTEXT" \
  -n "$NS" exec "$CLIENT" -c fortio-client -- \
  fortio load -qps 100 -t "${DUR}s" -c 16 -allow-initial-errors \
  -json - -quiet -loglevel Error http://echo:8080/ \
  >"$RUN_DIR/fortio.json" 2>"$RUN_DIR/load.log" || load_status=$?
touch "$STOP_FILE"
rollout_status=0
wait "$ROLLOUT_PID" || rollout_status=$?
trap - EXIT INT TERM
if [ "$load_status" -ne 0 ] || [ "$rollout_status" -ne 0 ]; then
  echo "Invalid run: inspect load/rollout logs" >&2
  exit 1
fi
jq -e '.DurationHistogram.Count > 0 and (.RetCodes | type == "object")' \
  "$RUN_DIR/fortio.json" >/dev/null
```

请保留结果 JSON、两个标准错误日志、滚动更新间隔、Pod/端点时间线和代理配置。超时或滚动更新失败意味着测试未完成；不要默默将部分输出视为干净样本。`SocketCount` 测量的是 Fortio 客户端侧的 Socket。

后续测试中，请将下列相应片段合并到现有的 echo Deployment 中。这些是**战略合并片段**，不是独立的 Deployment 清单：第一段是通用应用变更；第二段还会更改 sidecar 代理的关闭设置。

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: echo
spec:
  template:
    spec:
      terminationGracePeriodSeconds: 40
      containers:
      - name: echo
        lifecycle:
          preStop:
            sleep:
              seconds: 10
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: echo
  namespace: mesh-test-sidecar
spec:
  template:
    metadata:
      annotations:
        proxy.istio.io/config: |
          terminationDrainDuration: 30s
          proxyMetadata:
            EXIT_ON_ZERO_ACTIVE_CONNECTIONS: "true"
    spec:
      terminationGracePeriodSeconds: 40
      containers:
      - name: echo
        lifecycle:
          preStop:
            sleep:
              seconds: 10
```

请使用新的运行目录重复实验，并标记变更因素。报告所用 Kubernetes 版本支持 kubelet sleep 生命周期钩子；对于较旧的集群，请单独检查功能支持情况。Pod 宽限期包括 preStop。sleep 不会确认端点已完成收敛；代理的 exit-on-zero 路径也无法保证固定的 30 秒排空上限。

### G. 延迟测试（T5，§3）

使用稳定的工作负载，不启动滚动更新循环：

```bash
# No rollout loop for this steady-state case.
kmesh -n "$NS" rollout status deployment/echo --timeout=120s
CLIENT=$(kmesh -n "$NS" get pods -l app=fortio-client \
  -o jsonpath='{.items[0].metadata.name}')
test -n "$CLIENT"
kmesh -n "$NS" exec "$CLIENT" -c fortio-client -- \
  fortio load -qps 200 -t 60s -c 16 -allow-initial-errors \
  -json - -quiet -loglevel Error http://echo:8080/ \
  >"$RUN_DIR/fortio-latency.json" 2>"$RUN_DIR/latency.log"
jq '{Version, RequestedQPS, ActualQPS, ActualDuration,
     count: .DurationHistogram.Count, RetCodes, SocketCount}' \
  "$RUN_DIR/fortio-latency.json"
```

请报告实际计数、达到的 QPS、错误代码、所有要求的百分位数以及多次运行间的方差。请求 200 QPS、持续 60 秒只是负载设置，并不能证明恰好成功处理了 12,000 次调用。

### H. 重复执行观测（T2，§4）

以下修订版测试框架替换了原先无界客户端和静默处理的观测器失败。它会为每个逻辑客户端命令记录稳定的 `Idempotency-Key`；不会将 Envoy 跟踪 Header 用作业务标识符。该框架**不会**对命令去重，也不会实现持久化业务事务。

将 ConfigMap 保存为 t 2-configmap.yaml：

<details>
<summary>有界客户端、订单服务器和内存观测器</summary>

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: t2-scripts
  namespace: mesh-test-sidecar
data:
  order_server.py: |
    import http.server
    import os
    import time
    import urllib.error
    import urllib.request

    COLLECTOR_URL = os.environ.get("COLLECTOR_URL", "http://collector:9090/record")


    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            if self.path != "/order":
                self.send_response(404)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            command_id = self.headers.get("Idempotency-Key", "").strip()
            if not command_id:
                self.send_response(400)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            self.rfile.read(int(self.headers.get("Content-Length", "0")))
            time.sleep(0.1)  # Processing delay before the observer record, not a post-commit delay.
            try:
                request = urllib.request.Request(
                    COLLECTOR_URL, data=command_id.encode(), method="POST"
                )
                with urllib.request.urlopen(request, timeout=2) as response:
                    response.read()
            except (urllib.error.URLError, TimeoutError, OSError) as error:
                if isinstance(error, urllib.error.HTTPError):
                    error.close()
                # The record may have committed before an ambiguous transport failure.
                print(f"observer outcome unknown for {command_id}: {error}", flush=True)
                self.send_response(503)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            self.send_response(201)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def log_message(self, fmt, *args):
            pass


    if __name__ == "__main__":
        http.server.ThreadingHTTPServer(("", 8080), Handler).serve_forever()
  collector.py: |
    import http.server, json, threading

    lock = threading.Lock()
    counts = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            if self.path != "/record":
                self.send_response(404); self.send_header("Content-Length", "0"); self.end_headers(); return
            length = int(self.headers.get("Content-Length", 0))
            rid = self.rfile.read(length).decode().strip()
            with lock:
                counts[rid] = counts.get(rid, 0) + 1
            self.send_response(200); self.send_header("Content-Length","0"); self.end_headers()

        def do_GET(self):
            with lock:
                total = len(counts)
                deliveries = sum(counts.values())
                dupes = {k: v for k, v in counts.items() if v > 1}
            if self.path == "/dupes":
                body = json.dumps({"total_ids": total, "delivery_count": deliveries, "dupe_count": len(dupes), "dupes": dupes}).encode()
            elif self.path == "/stats":
                body = json.dumps({"total_ids": total, "delivery_count": deliveries, "dupe_count": len(dupes)}).encode()
            else:
                self.send_response(404); self.end_headers(); return
            self.send_response(200)
            self.send_header("Content-Type","application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt, *args):
            pass

    if __name__ == "__main__":
        http.server.ThreadingHTTPServer(("", 9090), Handler).serve_forever()
  client.py: |
    import json
    import math
    import os
    import time
    import urllib.error
    import urllib.request
    import uuid


    def run():
        target = os.environ.get("TARGET_URL", "http://order:8080/order")
        rps = float(os.environ.get("RPS", "20"))
        duration = float(os.environ.get("DURATION_SECONDS", "300"))
        timeout = float(os.environ.get("TIMEOUT_SECONDS", "12"))
        if not all(math.isfinite(value) and value > 0 for value in (rps, duration, timeout)):
            raise ValueError("RPS, DURATION_SECONDS and TIMEOUT_SECONDS must be finite and positive")
        interval = 1.0 / rps
        attempted = succeeded = failed = 0
        start = time.monotonic()
        deadline = start + duration
        while time.monotonic() < deadline:
            tick = time.monotonic()
            command_id = str(uuid.uuid4())
            attempted += 1
            request = urllib.request.Request(
                target, data=b"{}", method="POST", headers={"Idempotency-Key": command_id}
            )
            try:
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    response.read()
                    if 200 <= response.status < 300:
                        succeeded += 1
                    else:
                        failed += 1
            except urllib.error.HTTPError as error:
                error.close()
                failed += 1
            except (urllib.error.URLError, TimeoutError, OSError):
                failed += 1
            pause = min(interval - (time.monotonic() - tick), deadline - time.monotonic())
            if pause > 0:
                time.sleep(pause)
        elapsed = time.monotonic() - start
        return {
            "attempted": attempted,
            "succeeded": succeeded,
            "failed": failed,
            "requested_rps_cap": rps,
            "elapsed_seconds": elapsed,
            "achieved_rps": attempted / elapsed if elapsed else 0,
        }


    if __name__ == "__main__":
        print(json.dumps(run()), flush=True)
```

</details>

订单服务器的 0.1 秒延迟发生在记录之前，**并不是**对提交事务后响应丢失的测试。collector 超时/错误会返回 503，并留下未知结果：观测器可能已完成记录，但响应丢失。在此测试框架中，客户端成功意味着收到了观测器确认，并不代表真实业务实现了恰好一次执行。

将下方前四个资源保存为 t 2-servers.yaml，最后一个 Job 保存为 order-client-job.yaml。每个测试用例都使用没有旧客户端记录的全新 collector，并确保所有 metadata.namespace 一致更改。使用短 Service 名称可确保调用发生在所选命名空间内。

<details>
<summary>Collector/订单 Deployments、Services 和有界客户端 Job</summary>

```yaml
apiVersion: v1
kind: Service
metadata:
  name: collector
  namespace: mesh-test-sidecar
spec:
  selector:
    app: collector
  ports:
  - port: 9090
    targetPort: 9090
    name: http
    appProtocol: http
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: collector
  namespace: mesh-test-sidecar
spec:
  replicas: 1
  selector:
    matchLabels:
      app: collector
  template:
    metadata:
      labels:
        app: collector
    spec:
      nodeSelector:
        kubernetes.io/arch: arm64
        kubernetes.io/os: linux
      containers:
      - name: collector
        image: python:3.12-alpine@sha256:b64631e04e4920160c50fbe8d8df828f7f35f06f425cb44aa09bca53e708a35a
        command:
        - python3
        - /scripts/collector.py
        ports:
        - containerPort: 9090
        volumeMounts:
        - name: scripts
          mountPath: /scripts
        readinessProbe:
          tcpSocket:
            port: 9090
          periodSeconds: 1
          timeoutSeconds: 1
          failureThreshold: 3
      volumes:
      - name: scripts
        configMap:
          name: t2-scripts
---
apiVersion: v1
kind: Service
metadata:
  name: order
  namespace: mesh-test-sidecar
spec:
  selector:
    app: order
  ports:
  - port: 8080
    targetPort: 8080
    name: http
    appProtocol: http
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: order
  namespace: mesh-test-sidecar
spec:
  replicas: 6
  selector:
    matchLabels:
      app: order
  template:
    metadata:
      labels:
        app: order
    spec:
      nodeSelector:
        kubernetes.io/arch: arm64
        kubernetes.io/os: linux
      containers:
      - name: order
        image: python:3.12-alpine@sha256:b64631e04e4920160c50fbe8d8df828f7f35f06f425cb44aa09bca53e708a35a
        command:
        - python3
        - /scripts/order_server.py
        env:
        - name: COLLECTOR_URL
          value: http://collector:9090/record
        ports:
        - containerPort: 8080
        volumeMounts:
        - name: scripts
          mountPath: /scripts
        readinessProbe:
          tcpSocket:
            port: 8080
          periodSeconds: 1
          timeoutSeconds: 1
          failureThreshold: 3
      volumes:
      - name: scripts
        configMap:
          name: t2-scripts
---
apiVersion: batch/v1
kind: Job
metadata:
  generateName: order-client-
  namespace: mesh-test-sidecar
spec:
  backoffLimit: 0
  activeDeadlineSeconds: 360
  template:
    metadata:
      labels:
        app: order-client
      annotations:
        sidecar.istio.io/nativeSidecar: 'true'
    spec:
      restartPolicy: Never
      nodeSelector:
        kubernetes.io/os: linux
        kubernetes.io/arch: arm64
      containers:
      - name: order-client
        image: python:3.12-alpine@sha256:b64631e04e4920160c50fbe8d8df828f7f35f06f425cb44aa09bca53e708a35a
        command:
        - python3
        - /scripts/client.py
        env:
        - name: TARGET_URL
          value: http://order:8080/order
        - name: RPS
          value: '20'
        - name: DURATION_SECONDS
          value: '300'
        - name: TIMEOUT_SECONDS
          value: '12'
        volumeMounts:
        - name: scripts
          mountPath: /scripts
          readOnly: true
      volumes:
      - name: scripts
        configMap:
          name: t2-scripts
```

</details>

该 Job 不会自动重试，并使用 native-sidecar 注解，避免所选 sidecar 注入阻止 Job 完成。此注解不会将 Pod 注册到 Ambient，也不会自行启用 sidecar 注入。请验证实际的 Job Pod 和命名空间注册情况。修订后的模板增加了 TCP readiness 检查，并将 Python 镜像固定为本次审阅时已核验的注册表摘要；旧报告未归档该摘要。本地 Python 行为是在主机 Python 3.9 标准库上测试的；本次审阅没有执行 Python 3.12 容器或部署这些资源。

客户端是**顺序执行**的：RPS20 限制的是新尝试速率，并不保证持续以恒定的开放环路 20 QPS 运行。0.1 秒的服务延迟和失败会降低实际吞吐量。DURATION_SECONDS 限制新请求的启动时段；最后一个请求可能会因其超时时间而延长总运行时间。最终 JSON 包含 attempted/succeeded/failed 和 achieved_rps，且 attempted = succeeded + failed。

先为订单命令**和观测器写入**配置明确不重试的路由，并一并保存为 order-no-retry.yaml：

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: order-retry
  namespace: mesh-test-sidecar
spec:
  hosts:
  - order
  http:
  - name: order-lab
    match:
    - method:
        exact: POST
      uri:
        exact: /order
    route:
    - destination:
        host: order
        port:
          number: 8080
    timeout: 10s
    retries:
      attempts: 0
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: collector-observer-no-retry
  namespace: mesh-test-sidecar
spec:
  hosts:
  - collector
  http:
  - name: observer-record
    match:
    - method:
        exact: POST
      uri:
        exact: /record
    route:
    - destination:
        host: collector
        port:
          number: 9090
    timeout: 10s
    retries:
      attempts: 0
```

仅在专门隔离的**重试实验**中，可将订单策略替换为下方的 order-retry-experiment.yaml。保留 collector 的不重试策略。该实验旨在暴露潜在的重复投递，不是生产写入操作的重试建议。

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: order-retry
  namespace: mesh-test-sidecar
spec:
  hosts:
  - order
  http:
  - name: order-lab
    match:
    - method:
        exact: POST
      uri:
        exact: /order
    route:
    - destination:
        host: order
        port:
          number: 8080
    timeout: 10s
    retries:
      attempts: 3
      perTryTimeout: 2s
      retryOn: 503,reset,connect-failure
```

三次重试意味着最多尝试四次。两秒单次尝试设置与十秒路由超时会受到连接/建立连接时间的共同影响；十二秒客户端超时提供了更长的观测窗口，但不能证明所有尝试都已发生。请采集实际代理配置和重试计数器。

在所报告的 Istio 1.30 系列中，VirtualService 与 Ambient 配合使用属于 Alpha 功能，而且不支持与 Gateway API 流量配置混用。此实验中不要安装相互竞争的 HTTPRoute。请检查实际客户端 sidecar 或目标 waypoint 上的有效路由；仅使用 Ambient L4 无法执行此 HTTP 重试策略。

```bash
# A fresh collector and no earlier client must be running for this case.
# Replace metadata.namespace in every input with NS; explicit -n catches mismatches.
kmesh -n "$NS" apply -f t2-configmap.yaml -f t2-servers.yaml -f order-no-retry.yaml
kmesh -n "$NS" rollout status deployment/collector --timeout=120s
kmesh -n "$NS" rollout status deployment/order --timeout=120s
kmesh -n "$NS" get pods -l app=collector -o json >"$RUN_DIR/collector-before.json"

# For the deliberate retry experiment only, replace the no-retry policy with
# order-retry-experiment.yaml and verify the effective proxy configuration first.
JOB_RESOURCE=$(kmesh -n "$NS" create -f order-client-job.yaml -o name)
JOB_NAME=${JOB_RESOURCE#*/}
if ! kmesh -n "$NS" wait --for=condition=complete "$JOB_RESOURCE" --timeout=370s; then
  kmesh -n "$NS" logs "$JOB_RESOURCE" -c order-client >"$RUN_DIR/client-failed.log" || true
  echo "Invalid/incomplete client run" >&2
  exit 1
fi
kmesh -n "$NS" logs "$JOB_RESOURCE" -c order-client >"$RUN_DIR/client.json"
jq -e '.attempted > 0 and .attempted == (.succeeded + .failed)' \
  "$RUN_DIR/client.json" >/dev/null
kmesh -n "$NS" get pods -l "batch.kubernetes.io/job-name=$JOB_NAME" \
  -o json >"$RUN_DIR/client-pods.json"
kmesh -n "$NS" get pods -l app=collector -o json >"$RUN_DIR/collector-after.json"
kmesh -n "$NS" logs -l app=order -c order --prefix --tail=-1 \
  --max-log-requests=10 >"$RUN_DIR/available-order.log"
kmesh -n "$NS" exec deployment/collector -c collector -- python3 -c \
  "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:9090/dupes', timeout=5).read().decode())" \
  >"$RUN_DIR/observer.json"
```

此驱动程序处理资源设置和计数；它**不会**启动订单滚动更新循环。如需进行负载扰动实验，请单独编写并协调一个有界版本的 §F，在 300 秒客户端运行窗口内针对 deployment/order 进行滚动更新，并保留两者的时间线。若未进行该协调，输出结果只是稳态观测器测试。

客户端运行期间不要重置观测器。请对比运行前后的 collector Pod UID 和重启次数，保留所有订单/观测器错误，并使用不会因 Pod 删除而丢失的日志保留方式。上面的命令只会提取当前 Pod 中仍可用的日志。观测器重启、日志缺失或观测器错误，都会使“重复检测完整”的说法失效。调查真实事务安全性，需要持久化的逐命令账本以及受控的提交后响应丢失测试。

## 参考资料与验证范围

- [Istio 1.30.2 版本发布](https://github.com/istio/istio/releases/tag/1.30.2)、[已发布依赖项](https://github.com/istio/istio/blob/1.30.2/go.mod)和[代理关闭实现](https://github.com/istio/istio/blob/1.30.2/pkg/envoy/agent.go)
- [Istio 1.30 Ambient L7 功能状态](https://github.com/istio/istio.io/blob/release-1.30/content/en/docs/ambient/usage/l7-features/index.md)和[流量管理](https://github.com/istio/istio.io/blob/release-1.30/content/en/docs/ambient/usage/traffic-distribution/index.md)
- [Kubernetes 容器生命周期钩子](https://kubernetes.io/docs/concepts/containers/container-lifecycle-hooks/)和[native sidecar 容器](https://kubernetes.io/docs/concepts/workloads/pods/sidecar-containers/)
- [Amazon EKS NetworkPolicy](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html)和[配置/启动模式](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy-configure.html)
- [Cilium 策略支持](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/policy/index.rst)
- [Fortio 1.69.4 源代码和用法](https://github.com/fortio/fortio/tree/v1.69.4)和[容器构建](https://github.com/fortio/fortio/blob/v1.69.4/Dockerfile)

配置生成、模式检查、算术计算和本地 HTTP 测试支持上述具体修正。这些工作并未复现历史 EKS 测量结果，也无法证明生产环境性能、未经测试的插件组合兼容性或业务层面的恰好一次执行。
