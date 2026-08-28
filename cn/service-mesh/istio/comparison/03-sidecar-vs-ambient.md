# Sidecar 与 Ambient 模式选择指南（EKS 1.36 测试结果）

> **支持的版本**: Istio 1.30 / EKS 1.36
> **最后更新**: August 21, 2026

本文是一份以测试结果为依据的指南，用于决定是否应在 EKS 上的关键任务工作负载（例如加密货币交易所的订单/撮合路径）中采用 **sidecar 模式或 ambient 模式** 的 Istio。架构本身已在 [Ambient Mode](../advanced/01-ambient-mode.md) 中介绍，本文不再重复，而是针对 4 项具体需求给出测试结果和建议。

1. 必须使用 mTLS（集群内部 Pod 到 Pod 通信）
2. 必须使用 NetworkPolicy
3. 对延迟敏感的工作负载
4. 零停机 rollout——验证 ambient waypoint 的 503 隐患

> 💡 本文中的每个数据都来自专门为本轮测试构建并在测试后删除的 **独占单租户 EKS 集群**（`mesh-isolated-test`）。有关为何必须使用专用集群，请参阅 §4 末尾的[测试隔离说明](#a-note-on-test-isolation)。

## 决策摘要

| 需求 | Sidecar | Ambient（L4，无 waypoint） | Ambient（L7，waypoint） | Cilium |
|---|---|---|---|---|
| mTLS | ✅ 支持并已验证 STRICT | ✅ 支持并已验证 STRICT | ✅ 支持并已验证 STRICT | ⚠️ 本轮未测量——文档描述为身份双向认证，加上单独启用的 WireGuard/IPsec，而非一个等同于 STRICT 的单一开关（见[下文](#separate-raw-failures-from-failures-hidden-by-retry)） |
| NetworkPolicy | ✅ 现有规则无需修改即可工作，已验证 | ⚠️ 必须允许 HBONE 端口（15008），已验证 | ⚠️ 必须允许 HBONE 端口（15008），已验证 | ⚠️ 本轮未测量——CiliumNetworkPolicy 是原生机制，而非 K8s NetworkPolicy 附加组件 |
| 延迟（相对无 mesh 基线的 P50） | +1.29ms，已测量 | +0.04ms（可忽略），已测量 | +1.86ms，已测量 | 本轮未测量 |
| 零停机 rollout | 出现 503（0.5%，已测量） | **实际 503 为零**，替代为 0.3% TCP reset | 出现 503，**2.6%，约为 sidecar 的 5 倍**（已测量） | 本轮未测量 |

> ✅ **一句话结论**：不使用 waypoint 的 ambient（仅 L4）在 rollout 频繁变更期间最稳定，且延迟开销可忽略。附加 waypoint（L7）会使 503 率高于 sidecar，且延迟大致达到与 sidecar 相同的水平。证据见下文 §3–§4。纳入 Cilium 是为了进行同类安全性比较（见[下文](#separate-raw-failures-from-failures-hidden-by-retry)）；它未部署在测试集群上，因此其行仅陈述文档化属性——绝不能替代实际测量。

## 1. mTLS — 测试结果（EKS 1.36.2，Istio 1.30.2）

**测试环境**
- 独占单租户集群 `mesh-isolated-test`（独立 VPC，无其他工作负载），EKS 控制平面和工作节点均为 v1.36.2，Amazon Linux 2023（arm64，m7g.xlarge）
- 对 3 个测试 namespace（sidecar / ambient-L4 / ambient-L7）应用 namespace 范围的 `PeerAuthentication` STRICT——而非 mesh 全局范围

### 检查 1 — 明文直接 Pod-IP 访问（必须被阻止）

```
plaintext-client -> sidecar echo pod:8080
  [E] Read error, err="read tcp ...: read: connection reset by peer"
plaintext-client -> ambient-L4 echo pod:8080
  [E] Read error, err="EOF"
plaintext-client -> ambient-L7 echo pod:8080
  [E] Read error, err="EOF"
```

### 检查 2 — 通过 Service 的 mesh 内访问（必须成功）

```
sidecar client -> http://echo:8080/     => HTTP/1.1 200 OK (server: envoy)
ambient-L4 client -> http://echo:8080/  => HTTP/1.1 200 OK (no envoy headers, pure L4 passthrough)
ambient-L7 client -> http://echo:8080/  => HTTP/1.1 200 OK (server: istio-envoy, x-envoy-decorator-operation)
```

### 检查 3 — SPIFFE 证书

通过 `istioctl ztunnel-config certificates` / `istioctl proxy-config secret` 验证：

| 工作负载 | 证书颁发者 | SPIFFE ID | 根 CA |
|---|---|---|---|
| ambient-L4 echo | ztunnel | `spiffe://cluster.local/ns/mesh-test-ambient-l4/sa/default` | 共享 |
| ambient-L7 echo | ztunnel | `spiffe://cluster.local/ns/mesh-test-ambient-l7/sa/default` | 共享 |
| sidecar echo | istio-proxy | `spiffe://cluster.local/ns/mesh-test-sidecar/sa/default` | 共享 |

> ✅ **结论**：三种模式都会立即阻止明文访问，只有 mesh 内流量返回 200，并且每个工作负载都具有由同一根 CA 签发的独立 SPIFFE ID。Sidecar 和 ambient 都满足“集群内部 Pod 到 Pod 流量必须使用 mTLS”的要求。

**差异所在**：ambient 以透明方式应用 mTLS——`istio-cni` 在 Pod 的网络 namespace 内设置流量重定向，ztunnel 通过 15008 端口上的 HBONE（mTLS）隧道承载流量——不需要应用程序代码或 sidecar 注入。Sidecar 则通过应用程序 Pod 内的 istio-proxy 容器实现同样效果。有关两种模式的证书轮换和迁移策略详情，请参阅 [mTLS](../security/01-mtls.md)。

## 2. NetworkPolicy — 测试结果

Ambient 会通过 HBONE 隧道（TCP 15008）将 Pod 的实际流量转发到 ztunnel，然后由 ztunnel 解密并交付至目标。这意味着**仅允许应用程序端口（例如 8080）的 NetworkPolicy 将阻止进入已加入 ambient 的 Pod 的入站流量**，因为数据包实际到达的是 15008 端口。要将 ambient 与 NetworkPolicy 一同使用，必须在目标 Pod 上**增加一条允许 TCP 15008 入站的规则**。

**测试配置**：在专用 `mesh-isolated-test` 集群上启用了 VPC CNI NetworkPolicy 强制执行（`enableNetworkPolicy=true`、`aws-network-policy-agent v1.3.5-eksbuild.3`、eBPF）——我们无法在早期一轮所用的共享集群上安全执行此操作，因为这会同时激活属于其他团队的 13 个既有休眠 NetworkPolicy。专用单租户集群完全消除了该影响范围问题。

> ⚠️ **测试中发现的运维陷阱**：在启用 `enableNetworkPolicy` *之前*创建的 Pod 不会被追溯强制执行——eBPF hook 仅会在 Pod 网络设置（CNI ADD）时附加。一项健全性检查直接确认了这一点：对已运行的 Pod 应用仅允许端口 9999 的 policy 后，端口 8080 流量仍可不受阻碍地通过。启用 addon 后，必须执行 `kubectl rollout restart`（重新创建 Pod），任何 NetworkPolicy 才会生效。在生产集群启用 NetworkPolicy 前，这是一个值得了解的真实陷阱。

**测试 1 — 入站仅限 TCP 8080**（新建 Pod，已确认强制执行处于活动状态）

| 模式 | 结果 |
|---|---|
| sidecar | ✅ 200 OK——不受影响 |
| ambient-L4 | ❌ 被阻止（`i/o timeout`） |
| ambient-L7 | ❌ 被阻止（`i/o timeout`） |

**测试 2 — 入站允许 TCP 8080 + TCP 15008（HBONE）**

| 模式 | 结果 |
|---|---|
| ambient-L4 | ✅ 200 OK——已恢复 |
| ambient-L7 | ✅ 200 OK——已恢复 |

> ✅ **结论**：通过真实流量证实了上述假设。Ambient 在工作负载 Pod 网络 namespace 上的真实入站数据包到达 ztunnel HBONE 端口（15008），而非应用程序端口（8080）；仅限应用端口的 NetworkPolicy 会悄然破坏已加入 ambient 的 Pod。Sidecar 不受影响，因为 sidecar 的流量捕获完全发生在 Pod 自身网络 namespace 内，此时数据包已到达应用程序端口。

我们建议采用纵深防御：同时应用网络层（NetworkPolicy）和身份层（AuthorizationPolicy）控制。Sidecar 模式中 mTLS 与 NetworkPolicy 的冲突请参阅 [mTLS and NetworkPolicy Conflict](../security/01-mtls.md#7-mtls-and-networkpolicy-conflict)。

## 3. 延迟 — 测试结果（T5）

**测试配置**：fortio 负载，200 qps，60 秒，16 个连接，每个 case 12,000 个请求，稳态（未运行 rollout restart）——无 mesh 基线（未加入 mesh 的 namespace）与 sidecar、ambient-L4、ambient-L7 对比，均在相同 `mesh-isolated-test` Graviton（m7g.xlarge）节点上进行。所有 case 均返回 100% Code 200。

| Case | P50 | P75 | P90 | P99 | P99.9 |
|---|---|---|---|---|---|
| no-mesh（基线） | 0.82ms | 1.33ms | 1.73ms | 1.97ms | 2.00ms |
| sidecar | 2.11ms | 2.60ms | 2.89ms | 3.91ms | 8.00ms |
| ambient-L4（无 waypoint） | 0.86ms | 1.34ms | 1.74ms | 1.98ms | 2.93ms |
| ambient-L7（waypoint） | 2.68ms | 3.06ms | 3.63ms | 3.98ms | 7.67ms |

**相对无 mesh 基线的 P50 开销**：sidecar +1.29ms · ambient-L4 +0.04ms（可忽略）· ambient-L7 +1.86ms

> ✅ **结论**：与先前引用的已发布 ambient 模式基准测试一致（仅 L4 低于 sidecar，waypoint 与 sidecar 大致相当或略高）——这些现在是第一方测量，而非引用。对于加密货币交易路径这类延迟敏感工作负载，这与下文 §4 的结论一致：**避免使用 waypoint 有助于改善延迟和 rollout 稳定性**。

## 4. 零停机 Rollout — 503 测试结果（核心发现）

### 背景

Ambient 的担忧在于：**L7 waypoint（Envoy）会从其连接池中复用连接，连接池以目标 IP:Port 为键**，而**ztunnel 不会在 Pod 终止时通知 waypoint**。如果终止 Pod 的 IP 被重新分配给新 Pod，waypoint 可能复用现已失效的连接并返回 503。Sidecar 也可能遭遇类似的 Pod 终止竞争条件（机制请参阅 [Connection Errors During Pod Termination](../troubleshooting/common-errors.md#connection-errors-during-pod-termination)）。我们在 EKS 1.36 上正面对比测量了两种失败模式。

**测试环境**
- 独占单租户集群 `mesh-isolated-test`，EKS 控制平面和工作节点均为 v1.36.2，arm64（Graviton m7g.xlarge），Istio 1.30.2
- 3 个 namespace（sidecar / ambient-L4 / ambient-L7）运行**字节完全相同的工作负载**（具有 6 个副本的 echo server Deployment + 一个 fortio client）——仅 namespace label 不同
- 当目标 namespace 的 `echo` Deployment 被反复执行 `rollout restart` 时，fortio client 保持 100 req/s 的 keepalive 连接
- 每种模式收集 60,000 个请求（= 100 qps × 600 秒）

### 结果

| 模式 | Rollout 周期 | 请求数 | 503 数量 | 503 比率 | 其他错误（-1、TCP reset/EOF） | 已使用 Socket |
|---|---|---|---|---|---|---|
| sidecar | 42 | 60,000 | 324 | **0.5%** | 2（0.0%） | 350 |
| ambient-L4（无 waypoint） | 64 | 60,000 | **0** | **0%** | 195（0.3%） | 1,652 |
| ambient-L7（waypoint） | 65 | 59,913 | 1,528 | **2.6%** | 84（0.1%） | 2,486 |

> 理想的 keepalive 意味着使用 16 个 socket。Ambient-L7 在运行结束时还留下 60,000 个调用中的 87 个未完成，并且其平均延迟（50.4ms）远高于另外两种模式（约 2-3ms）。

<details>
<summary>原始 fortio 运行输出</summary>

```
[sidecar]      42 rollouts, Sockets used: 350 (16 would be perfect keepalive)
  Code 200 : 59674 (99.5 %)
  Code 503 : 324 (0.5 %)
  Code  -1 : 2   (0.0 %)

[ambient-L4]   64 rollouts, Sockets used: 1652
  Code 200 : 59805 (99.7 %)
  Code  -1 : 195 (0.3 %)   <- connection dropped with no HTTP response, not a 503

[ambient-L7]   65 rollouts, Sockets used: 2486
  Code 200 : 58301 (97.3 %)
  Code 503 : 1528 (2.6 %)
  Code  -1 : 84  (0.1 %)
  (59,913 of 60,000 calls completed; avg latency 50.4ms vs. ~2-3ms for the other two modes)
```

</details>

**结论**

1. 在此专用集群上，**Ambient-L7（waypoint）的 503 比率（2.6%）约为 sidecar（0.5%）的 5 倍**——差距甚至大于同一天在共享、存在争用的集群上早先测量所暗示的结果（见下方隔离说明），这进一步而非削弱了原始担忧：在 rollout 频繁变更期间，“waypoint 的连接池会复用陈旧连接并产生 503”。
2. **Ambient-L4（无 waypoint）再次产生零个实际 HTTP 503。**相反，它出现了 0.3% 的连接层 TCP 错误（“-1”，无响应）。在 L4 中，失败表现为*连接丢失*，而非*503 响应*——重连处理留给 client/application，而非由代理合成错误响应。
3. Ambient-L7 还表现出较大的平均延迟飙升，以及 87 个在运行期间从未完成的请求——这与 waypoint 在 rollout 频繁变更和持续负载叠加时难以应对相一致，有别于另外两种模式。
4. 在相同 600 秒窗口内完成的 rollout 周期（sidecar / ambient-L4 / ambient-L7 分别为 42 / 64 / 65）远高于先前在繁忙共享集群上的测量，因为该专用集群没有其他租户争用 CPU/网络——*相对*排序（sidecar 最慢，ambient-L4 最快）得以保持，但绝对 rollout 速度高度依赖集群争用，不应过度解读为任何模式的固有属性。

### 后续：graceful-shutdown 加固后

上述基线数据反映了**完全没有 shutdown 调优**的情况。我们在新增两项变更后重新运行了相同 T1 测试（100 qps × 600 秒，每种模式 60,000 个请求）：

- **所有三种模式**：在 `echo` 容器上设置 `lifecycle.preStop.sleep.seconds: 10`（K8s 1.29+ 原生 sleep action——无需 exec/shell），并设置 `terminationGracePeriodSeconds: 40`，在 Pod 实际停止接受连接前，为 Endpoint 移除在整个集群传播提供时间
- **仅 Sidecar**：通过 `proxy.istio.io/config` Pod annotation 向 istio-proxy 注入 `EXIT_ON_ZERO_ACTIVE_CONNECTIONS=true` + `terminationDrainDuration: 30s`（已确认存在于 istio-proxy init container 的实际 env 中）——在活跃连接降至零时立即退出，而非始终等待完整 30 秒

| 模式 | Rollout 周期 | Code 200 | Code 503 | Code -1 | 已使用 Socket | 平均延迟 |
|---|---|---|---|---|---|---|
| sidecar（加固后） | 42 | 60,000（100%） | **0** | **0** | 16（理想 keepalive） | 2.630ms |
| ambient-L4（加固后） | 38 | 60,000（100%） | **0** | **0** | 395 | 1.189ms |
| ambient-L7（加固后） | 45 | 59,352（98.9%） | 648（1.1%） | **0** | 678 | 3.843ms |

**基线 → 加固后对比**

| 模式 | 基线错误率 | 加固后错误率 | 变化 |
|---|---|---|---|
| sidecar | 0.5% 503 + 0% TCP | 0% 503 + 0% TCP | **503 完全消除** |
| ambient-L4 | 0% 503 + 0.3% TCP | 0% 503 + 0% TCP | **TCP 错误也完全消除** |
| ambient-L7 | 2.6% 503 + 0.1% TCP | 1.1% 503 + 0% TCP | 503 比率降低超过一半 |

> ✅ **结论**：测量证实了以下假设：这些 503 源于 Pod 在其 Endpoint 移除传播前未能优雅关闭——仅使用 `preStop sleep 10` 就完全消除了 sidecar 和 ambient-L4 的错误。Ambient-L7（waypoint）也显著改善，但未降至零——这意味着 waypoint 自身的陈旧连接复用机制（上方 §4 的核心发现）无法仅靠工作负载侧 graceful-shutdown 调优完全解决。如果通过 waypoint 路由，请将此加固作为基线，并仍要为其无法消除的剩余 503 风险预留预算。

### 将 retry 作为缓解措施的风险 — 测试结果（T2）

**测试配置**：测试工具由 `order`（6 个副本，非幂等 `POST /order`，在 handler 内延迟 0.1 秒，并向 `collector` 报告其 request ID）、`collector`（统计不同 request ID，并标记任何多次出现的 ID）和 `order-client`（以每个请求唯一 UUID 持续发送 POST 负载）组成。通过相同 Istio VirtualService config，对 sidecar（istio-proxy）和 ambient-L7（waypoint）应用 retry policy（`attempts: 3, perTryTimeout: 2s, retryOn: 503,reset,connect-failure`）。每种模式均在并发对 `order` Deployment 执行 `rollout restart` 时运行 300 秒。

| 模式 | Rollout 周期 | 已发送请求 | Client 可见失败（所有 3 次 retry 均耗尽） | 重复执行 |
|---|---|---|---|---|
| sidecar（VirtualService retry） | 11 | 9,135 | 15（0.16%） | **0** |
| ambient-L7（waypoint retry） | 12 | 7,229 | 21（0.29%） | **0** |

> ✅ **结论**：未观察到任一模式的重复非幂等执行。较低的 client 可见失败率证实 retry 正在触发，并且主要掩盖了短暂的 rollout 频繁变更错误——然而，没有任何成功 retry 导致相同逻辑请求被处理两次。

> ⚠️ **这并不意味着该竞争条件不可能发生。**它仅表示在这些特定条件下未出现（perTryTimeout=2s、20 req/s、6 个副本、默认 graceful shutdown、无 `preStop` hook）。理论上的机制——原始请求已到达 app 但响应尚未返回 caller 时，retry 被重新发送——需要连接在 app 开始处理*之后*、响应返回*之前*的狭窄窗口中断。300 秒的持续 rollout 频繁变更未捕捉到任一模式的实例，但生产环境中的非幂等路径在没有服务器端幂等键时，仍应默认将 mesh 级 retry 视为不安全：该测试降低了该竞争条件*常见*的置信度，但并未证明其是*安全*的。

### 区分原始失败与被 retry 隐藏的失败

mTLS data-plane 选择和 HTTP retry policy 是相互独立的决策。Sidecar Envoy 和 waypoint Envoy 可以在 L7 重试 HTTP 请求，而 ambient ztunnel 是一个 [L4 proxy](https://istio.io/latest/docs/ambient/architecture/data-plane/)，无法解释 HTTP 503 或重放 HTTP 请求。因此，仅比较最终 client 可见的 503 数量，无法显示 sidecar/waypoint 的原始失败是否更少，还是仅通过 retry 隐藏了失败。

为实现公平的 rollout 对比，请在 POST/PATCH 写入路由上设置 `attempts: 0`，并分别记录以下维度：

- retry 前的 HTTP 503、TCP reset/EOF 和 connection-refused 事件
- Envoy `upstream_rq_retry` 和 `upstream_rq_retry_success` counter
- 实际上游交付次数，包括原始请求
- retry 处理后的最终 client 可见成功/失败
- server 是否多次处理相同的幂等键或 command ID

| Data plane | mTLS/encryption 含义 | L7 retry 位置 | 推荐用途 |
|---|---|---|---|
| Istio sidecar | 工作负载 SPIFFE-certificate mTLS | 每 Pod Envoy | 关键非幂等路径的保守基线 |
| Istio ambient L4 | ztunnel 之间的 HBONE 工作负载 mTLS | 无 | 仅要求 Istio mTLS 和 L4 policy 时的首选候选 |
| Istio ambient L7 | HBONE 加 waypoint Envoy | 共享 waypoint | 仅添加到需要 HTTP routing 或 L7 policy 的 Service |
| Cilium | 身份双向认证和 WireGuard/IPsec 等传输加密分别选择 | L3/L4 encryption layer 中无 | 需要身份 policy 和网络加密的既有 Cilium data plane |

> **运维规则：**如果唯一要求是 mTLS，请先验证 ambient L4，并仅为需要 L7 policy 或东西向 HTTP routing 的 Service 添加 waypoint。当在禁用写入 retry 的条件下测得 ambient rollout 错误超出工作负载错误预算时，对关键非幂等路径保留 sidecar 作为基线。

### 测试隔离说明

<details>
<summary>为何需要专用集群，以及仍然发生的问题（点击展开）</summary>

同日较早一轮 T1/T3 测试在一个共享集群（`fsi-demo-cluster`）的 4 个专用 namespace 中运行。该集群的 `benchmark` namespace 当时正在同时运行覆盖 100 多种 EC2 instance type 的大型 Kafka benchmark job sweep，而 ambient-L7 T1 负载完成后不久，该轮创建的所有资源（全部 4 个 namespace、`istio-system` 以及所有 Istio/Gateway API CRD）在没有确认根因的情况下同时消失（未发现匹配的 ArgoCD Application、Kyverno/Gatekeeper policy）——导致 T2、T4、T5 未运行，并使在该资源争用下收集的 T1 数据有效性产生一些疑问。

本轮专门使用全新的单租户集群（`mesh-isolated-test`、独立 VPC、无其他工作负载）来消除这类干扰，并端到端完成了 T1–T5，未出现资源异常。然而，出现了另一种隔离缺口：在新集群首次 T1 尝试进行到中途时，本地工作站共享的 `~/.kube/config` current-context 悄然从 `mesh-isolated-test` 切换到了无关集群——使该次尝试无效（context 切换后，rollout-restart loop 开始以 `namespace not found` 失败，尽管已建立的正在运行 fortio load connection 不受影响）。通过显式 kubeconfig 检查确认，`mesh-isolated-test` 上的 namespace 和资源始终完全完好——这是工作站级别的 context 混淆，而非集群侧删除。解决方案：使用仅限于 `mesh-isolated-test` 的 kubeconfig 文件，每个测试脚本显式引用该文件，并设置如果 context 再次漂移便中止的 guard。本文所有最终数据均来自修正后、context 锁定的重跑。

</details>

## 5. 建议：分层方法

与其做出二元的“sidecar 或 ambient”选择，我们建议**按工作负载层级应用不同 mesh 模式**。这与 [Ambient Mode](../advanced/01-ambient-mode.md#use-cases) 中的使用场景指南相符，而本轮测试以证据支持了该建议。

| 层级 | 示例 | 建议 | 理由 |
|---|---|---|---|
| 核心（订单创建/撮合/结算，非幂等） | Trading API | **仅 Ambient L4（无 waypoint）或保留 sidecar** | §4：通过 waypoint 路由时，503 比率约为 sidecar 的 5 倍；仅 L4 的 503 为零。如果确实需要 L7 功能，sidecar 是更成熟的选择。T2 未发现任一模式在 retry 下存在重复执行实例，但这并不能证明安全——无论 mesh 模式如何，在此层级默认关闭 retry。 |
| 半核心（幂等读取 API） | 价格/余额查询 | Ambient（L4，需要时 L7） | 幂等请求可以安全 retry，因此 waypoint 风险影响较小 |
| 外围（查询、通知、批处理） | Dashboard、告警 | 积极采用 ambient | 最大化资源/运维收益；测试已验证 mTLS 和 rollout 行为安全 |

本轮测试实际验证了**namespace 级混合部署**——sidecar、ambient-L4 和 ambient-L7 namespace 在同一集群上并行运行，每个均独立强制执行 STRICT mTLS。

### 仅 L4 的限制——仍可进行 canary deployment 吗？

Ambient 仅 L4 没有 waypoint，因此 ztunnel 永远不会查看 HTTP 请求内部。这意味着**L7 功能——基于 HTTP header/path 的 routing、retry、circuit breaking、traffic mirroring——无法应用于仅 L4 的 Service。**这是否实际阻碍 canary deployment，取决于流量从何处进入。

> ✅ **Ingress canary 不受影响。**无论后端工作负载运行于 ambient 还是 sidecar 模式，Istio Ingress Gateway 或 Gateway API `Gateway` 始终是独立的、完整的 Envoy proxy（其自身的 Deployment）。通过 `VirtualService`/`HTTPRoute` 在 v1/v2 subset 之间的加权拆分完全在 gateway 处决定；ztunnel（L4）只会在随后将连接隧道传输到已选定的目标 Pod。对于外部暴露 API 的 canary deployment，使用仅 L4 后端完全可行。

> ⚠️ **Mesh 内部（东西向）canary 需要该特定 Service 使用 L7。**如果 Service A 在 mesh 内调用 Service B，并且希望按百分比在 B-v1 与 B-v2 之间分割流量，则必须有某个组件在 L7 做出 routing 决策——ztunnel 无法做到。要使该 canary 正常工作，需要**在 B 前方部署 waypoint（将 B 切换为 ambient-L7），或为 B 运行 sidecar**。

**总结**：对于外部暴露 API 的 canary deployment，使用仅 L4 完全可行。只为需要 mesh 内部 canary 的特定 Service 使用 waypoint 或 sidecar——这正是上述分层建议在实践中应如何应用。

**采用前检查清单**

- [ ] 订单/撮合/结算路径是否确实需要 L7 功能（HTTP routing、retry、traffic split）？若不需要，ambient 仅 L4 是首选候选
- [ ] 是否已更新 NetworkPolicy 以允许 HBONE 端口（15008）？（§2，已验证——如果首次在生产集群上启用 `enableNetworkPolicy`，请重新创建既有 Pod，因为强制执行不会追溯生效）
- [ ] 是否对非幂等 API 路径应用了 retry policy？（§4——T2 测试中未发现重复执行，但在没有服务器端幂等键时，非幂等路径默认应保持禁用 retry）
- [ ] 是否已针对自身工作负载重新测量延迟？（§3，已在本集群的 Graviton 节点上验证——如果 instance type 或工作负载 profile 存在实质差异，请再次测量）

## 附录：复现这些测试

以下是产生本文所有数据的实际 config file 和过程。可直接复制它们，以便在自己的集群上复现结果。

### A. 集群配置（eksctl）

专用单租户集群使用 eksctl 创建，采用完全公有子网且没有 NAT gateway（仅测试用的捷径，以避免需要新的 Elastic IP——生产集群请启用 NAT）。

<details>
<summary>eksctl-cluster.yaml</summary>

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: mesh-isolated-test
  region: ap-northeast-2
  version: "1.36"
  tags:
    purpose: istio-sidecar-vs-ambient-retest
    ephemeral: "true"

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
      ephemeral: "true"

addons:
  - name: vpc-cni
  - name: coredns
  - name: kube-proxy
  - name: eks-pod-identity-agent
```

</details>

```bash
eksctl create cluster -f eksctl-cluster.yaml
```

### B. Istio 安装（Gateway API CRD + ambient profile）

Ambient 模式的 waypoint 是 Gateway API `Gateway` resource，因此必须在安装 Istio 前存在 Gateway API CRD。

```bash
# 1) Gateway API CRDs (v1.1.0, compatible with Istio 1.30)
kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.1.0/standard-install.yaml

# 2) Istio 1.30.2 ambient profile (via istioctl, not Helm)
istioctl install -f ambient-overlay.yaml -y
```

<details>
<summary>ambient-overlay.yaml（将 CNI/ztunnel/istiod 调度到 arm64 节点）</summary>

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
                values: ["arm64"]
    ztunnel:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: kubernetes.io/arch
                operator: In
                values: ["arm64"]
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
                  values: ["arm64"]
```

</details>

### C. Namespace 和工作负载 manifest

4 个 namespace——`mesh-test-base`（未加入 mesh，用于延迟基线）、`mesh-test-sidecar`、`mesh-test-ambient-l4`、`mesh-test-ambient-l7`。仅 label 不同；其他内容均字节完全相同。

<details>
<summary>namespaces.yaml</summary>

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

</details>

<details>
<summary>工作负载 manifest（echo server、6 个副本 + fortio client）——全部 4 个 namespace 相同，仅 namespace field 变化</summary>

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: echo
  namespace: mesh-test-sidecar   # swap for base / ambient-l4 / ambient-l7
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
      containers:
      - name: echo
        image: fortio/fortio:1.69.4
        args: ["server", "-http-port", "8080"]
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
      containers:
      - name: fortio-client
        image: fortio/fortio:1.69.4
        command: ["/usr/bin/fortio"]
        args: ["server", "-http-port", "8081", "-redirect-port", "disabled"]
        resources:
          requests:
            cpu: 50m
            memory: 32Mi
          limits:
            cpu: 300m
            memory: 128Mi
```

</details>

### D. mTLS — PeerAuthentication（§1）

<details>
<summary>peerauth-strict.yaml</summary>

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

</details>

ambient-L7 namespace 还需要部署 waypoint：

```bash
istioctl waypoint apply -n mesh-test-ambient-l7 --enroll-namespace --wait
```

### E. NetworkPolicy（§2）

通过 addon config 启用基于 eBPF 的 VPC CNI NetworkPolicy 强制执行。如 §2 所述，这**仅适用于此后创建或重新创建的 Pod**。

```bash
aws eks update-addon --cluster-name mesh-isolated-test --addon-name vpc-cni --region ap-northeast-2 \
  --configuration-values '{"enableNetworkPolicy":"true"}' --resolve-conflicts OVERWRITE

# recreate existing pods so the eBPF hooks attach
kubectl rollout restart deployment/echo deployment/fortio-client -n mesh-test-sidecar
kubectl rollout restart deployment/echo deployment/fortio-client -n mesh-test-ambient-l4
kubectl rollout restart deployment/echo deployment/fortio-client -n mesh-test-ambient-l7
```

<details>
<summary>NetworkPolicy manifest（测试 1：仅 8080 → 测试 2：8080 + 15008）</summary>

```yaml
# Test 1 — this blocks ambient
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-8080-only
  namespace: mesh-test-ambient-l4   # apply the same to ambient-l7 and sidecar
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
# Test 2 — adding the HBONE port restores ambient
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

</details>

### F. 运行零停机 rollout 测试（T1，§4）

同时运行 fortio load generator（前台，阻塞至测试持续时间结束）和 `rollout restart` loop（后台），然后在 load 完成后停止 loop。

```bash
NS=mesh-test-sidecar   # repeat for ambient-l4, ambient-l7
DUR=600
CLIENT=$(kubectl get pods -n "$NS" -l app=fortio-client -o jsonpath='{.items[0].metadata.name}')

# ① rollout-restart loop (background) for DUR seconds
(
  START=$(date +%s)
  while [ $(( $(date +%s) - START )) -lt "$DUR" ]; do
    kubectl rollout restart deployment/echo -n "$NS"
    kubectl rollout status deployment/echo -n "$NS" --timeout=60s
  done
) &
ROLLOUT_PID=$!

# ② fortio load generator (foreground, 100qps x 600s = 60,000 requests)
kubectl exec -n "$NS" "$CLIENT" -c fortio-client -- \
  fortio load -qps 100 -t "${DUR}s" -c 16 -allow-initial-errors http://echo:8080/

kill "$ROLLOUT_PID" 2>/dev/null
```

> 💡 如果没有 `-allow-initial-errors`，当 fortio 的 warmup request 恰好在 rollout 期间落到目标并获得 503 时，它会中止整个运行。对于与 rollout churn 重叠的任何 load test，都必须使用此 flag。

**Graceful-shutdown 加固 patch**（用于 §4 中“加固后”重新运行，通过 `kubectl patch --type strategic` 应用于现有 Deployment）：

```yaml
# common to all 3 modes — ambient-l4/l7 get only this patch
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
```

```yaml
# sidecar namespace only, additionally (EXIT_ON_ZERO_ACTIVE_CONNECTIONS)
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

```bash
kubectl patch deployment/echo -n mesh-test-sidecar --type strategic --patch-file patch-prestop-sidecar.yaml
kubectl patch deployment/echo -n mesh-test-ambient-l4 --type strategic --patch-file patch-prestop-ambient.yaml
kubectl patch deployment/echo -n mesh-test-ambient-l7 --type strategic --patch-file patch-prestop-ambient.yaml
```

### G. 运行延迟测试（T5，§3）

使用相同 fortio command，在没有 rollout loop 的稳态下运行。

```bash
kubectl exec -n "$NS" "$CLIENT" -c fortio-client -- \
  fortio load -qps 200 -t 60s -c 16 -allow-initial-errors http://echo:8080/
```

### H. Retry / 重复执行测试工具（T2，§4）

一个 3 Pod 测试工具——`order`（处理非幂等 POST）、`collector`（检测重复 request ID）、`order-client`（持续 load）——相同地部署到 sidecar 和 ambient-L7 namespace 中。

<details>
<summary>ConfigMap — order_server.py / collector.py / client.py</summary>

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: t2-scripts
  namespace: mesh-test-sidecar   # deploy the same into ambient-l7
data:
  order_server.py: |
    import http.server, urllib.request, time, os

    COLLECTOR_URL = os.environ.get("COLLECTOR_URL", "http://collector.mesh-test-sidecar.svc.cluster.local:9090/record")

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            if self.path != "/order":
                self.send_response(404); self.end_headers(); return
            rid = self.headers.get("X-Request-Id", "unknown")
            time.sleep(0.1)  # widen the SIGTERM-mid-request race window
            try:
                req = urllib.request.Request(COLLECTOR_URL, data=rid.encode(), method="POST")
                urllib.request.urlopen(req, timeout=2)
            except Exception as e:
                print(f"collector report failed for {rid}: {e}", flush=True)
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
            length = int(self.headers.get("Content-Length", 0))
            rid = self.rfile.read(length).decode().strip()
            with lock:
                counts[rid] = counts.get(rid, 0) + 1
            self.send_response(200); self.send_header("Content-Length","0"); self.end_headers()

        def do_GET(self):
            with lock:
                total = len(counts)
                dupes = {k: v for k, v in counts.items() if v > 1}
            if self.path == "/dupes":
                body = json.dumps({"total_ids": total, "dupe_count": len(dupes), "dupes": dupes}).encode()
            elif self.path == "/stats":
                body = json.dumps({"total_ids": total, "dupe_count": len(dupes)}).encode()
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
    import urllib.request, uuid, time, os

    TARGET = os.environ.get("TARGET_URL", "http://order.mesh-test-sidecar.svc.cluster.local:8080/order")
    RPS = float(os.environ.get("RPS", "20"))
    interval = 1.0 / RPS
    sent = 0
    failed = 0
    while True:
        rid = str(uuid.uuid4())
        t0 = time.time()
        try:
            req = urllib.request.Request(TARGET, data=b"{}", method="POST", headers={"X-Request-Id": rid})
            urllib.request.urlopen(req, timeout=3)
            sent += 1
        except Exception:
            failed += 1
        dt = time.time() - t0
        if dt < interval:
            time.sleep(interval - dt)
```

</details>

<details>
<summary>order / collector / order-client Deployment + Service</summary>

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
      containers:
      - name: collector
        image: python:3.12-alpine
        command: ["python3", "/scripts/collector.py"]
        ports:
        - containerPort: 9090
        volumeMounts:
        - name: scripts
          mountPath: /scripts
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
      containers:
      - name: order
        image: python:3.12-alpine
        command: ["python3", "/scripts/order_server.py"]
        env:
        - name: COLLECTOR_URL
          value: "http://collector.mesh-test-sidecar.svc.cluster.local:9090/record"
        ports:
        - containerPort: 8080
        volumeMounts:
        - name: scripts
          mountPath: /scripts
      volumes:
      - name: scripts
        configMap:
          name: t2-scripts
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: order-client
  namespace: mesh-test-sidecar
spec:
  replicas: 1
  selector:
    matchLabels:
      app: order-client
  template:
    metadata:
      labels:
        app: order-client
    spec:
      nodeSelector:
        kubernetes.io/arch: arm64
      containers:
      - name: order-client
        image: python:3.12-alpine
        command: ["python3", "/scripts/client.py"]
        env:
        - name: TARGET_URL
          value: "http://order.mesh-test-sidecar.svc.cluster.local:8080/order"
        - name: RPS
          value: "20"
        volumeMounts:
        - name: scripts
          mountPath: /scripts
      volumes:
      - name: scripts
        configMap:
          name: t2-scripts
```

</details>

将 retry policy 应用于 `order` Service（sidecar 的 istio-proxy 和 ambient-L7 已部署的 waypoint 都会获取此 VirtualService）：

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: order-retry
  namespace: mesh-test-sidecar   # deploy the same into ambient-l7
spec:
  hosts:
  - order
  http:
  - route:
    - destination:
        host: order
        port:
          number: 8080
    retries:
      attempts: 3
      perTryTimeout: 2s
      retryOn: 503,reset,connect-failure
```

运行过程与 (F) 中的 rollout loop 相同，但目标为 `order` Deployment，在测量前重置 `collector` 的 counter，并在之后查询重复数量：

```bash
kubectl rollout restart deployment/collector -n "$NS"   # reset the counter

# ... same rollout-loop pattern as §F, targeting `order`, for 300s ...

CLIENT=$(kubectl get pods -n "$NS" -l app=order-client -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n "$NS" "$CLIENT" -c order-client -- python3 -c \
  "import urllib.request; print(urllib.request.urlopen('http://collector.$NS.svc.cluster.local:9090/dupes', timeout=5).read().decode())"
```

## 参考资料

- [Ambient Mode](../advanced/01-ambient-mode.md) — ztunnel/waypoint 架构、与 sidecar 的资源对比
- [mTLS](../security/01-mtls.md) — STRICT/PERMISSIVE 模式、证书管理、NetworkPolicy 冲突
- [Istio VirtualService Retry](https://istio.io/latest/docs/reference/config/networking/virtual-service/#HTTPRetry) — `attempts: 0` 和 retry 条件
- [Envoy Retry Statistics](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/router_filter) — retry 行为和可观测性
- [Troubleshooting: Connection Errors During Pod Termination](../troubleshooting/common-errors.md#connection-errors-during-pod-termination)
- [Sidecar Injection](../advanced/07-sidecar-injection.md)
- [Service Mesh Solution Comparison](01-service-mesh-comparison.md)
