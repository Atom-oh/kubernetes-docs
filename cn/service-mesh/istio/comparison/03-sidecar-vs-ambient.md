# Sidecar 与 Ambient 模式选型指南（EKS 1.36 测试结果）

> **支持的版本**：Istio 1.30 / EKS 1.36
> **最后更新**：July 7, 2026

本文是一份以测试结果为依据的指南，用于决定 EKS 上的关键任务工作负载（例如加密货币交易所的订单/撮合路径）应采用 **sidecar 模式还是 ambient 模式** 的 Istio。架构本身已在 [Ambient Mode](../advanced/01-ambient-mode.md) 中介绍，因此本文不再重复，而是针对 4 项具体要求给出测试结果和建议。

1. 必须使用 mTLS（集群内部 pod 到 pod 通信）
2. 必须使用 NetworkPolicy
3. 对延迟敏感的工作负载
4. 零停机 rollout —— 验证 ambient waypoint 的 503 顾虑

> 💡 本文的每一个数字均来自一个**专用单租户 EKS 集群**（`mesh-isolated-test`）；该集群仅为本轮测试构建，随后已删除。关于为何必须使用专用集群，请参阅 §4 末尾的[测试隔离说明](#a-note-on-test-isolation)。

## 决策摘要

| 要求 | Sidecar | Ambient（L4，无 waypoint） | Ambient（L7，waypoint） |
|---|---|---|---|
| mTLS | ✅ 支持并已验证 STRICT | ✅ 支持并已验证 STRICT | ✅ 支持并已验证 STRICT |
| NetworkPolicy | ✅ 现有规则可直接使用，已验证 | ⚠️ 必须允许 HBONE 端口（15008），已验证 | ⚠️ 必须允许 HBONE 端口（15008），已验证 |
| 延迟（相对无 mesh 基线的 P50） | +1.29ms，已测量 | +0.04ms（可忽略），已测量 | +1.86ms，已测量 |
| 零停机 rollout | 发生 503（0.5%，已测量） | **实际 503 为零**，但有 0.3% TCP reset | 发生 503，**2.6%，约为 sidecar 的 5 倍**（已测量） |

> ✅ **一句话结论**：无 waypoint 的 ambient（仅 L4）在 rollout 波动下最稳定，且延迟开销可忽略。附加 waypoint（L7）后，503 率超过 sidecar，延迟也大致达到与 sidecar 相同的水平。证据见下文 §3–§4。

## 1. mTLS —— 测试结果（EKS 1.36.2，Istio 1.30.2）

**测试环境**
- 专用单租户集群 `mesh-isolated-test`（独立 VPC，无其他工作负载），EKS control plane 和 worker node 均为 v1.36.2，Amazon Linux 2023（arm64，m7g.xlarge）
- 对 3 个测试 namespace（sidecar / ambient-L4 / ambient-L7）应用了 namespace 范围的 `PeerAuthentication` STRICT，而非 mesh 全局范围

### 检查 1 —— 明文直接 pod-IP 访问（必须被阻止）

```
plaintext-client -> sidecar echo pod:8080
  [E] Read error, err="read tcp ...: read: connection reset by peer"
plaintext-client -> ambient-L4 echo pod:8080
  [E] Read error, err="EOF"
plaintext-client -> ambient-L7 echo pod:8080
  [E] Read error, err="EOF"
```

### 检查 2 —— 通过 Service 的 mesh 内访问（必须成功）

```
sidecar client -> http://echo:8080/     => HTTP/1.1 200 OK (server: envoy)
ambient-L4 client -> http://echo:8080/  => HTTP/1.1 200 OK (no envoy headers, pure L4 passthrough)
ambient-L7 client -> http://echo:8080/  => HTTP/1.1 200 OK (server: istio-envoy, x-envoy-decorator-operation)
```

### 检查 3 —— SPIFFE 证书

通过 `istioctl ztunnel-config certificates` / `istioctl proxy-config secret` 验证：

| 工作负载 | 证书颁发者 | SPIFFE ID | Root CA |
|---|---|---|---|
| ambient-L4 echo | ztunnel | `spiffe://cluster.local/ns/mesh-test-ambient-l4/sa/default` | 共享 |
| ambient-L7 echo | ztunnel | `spiffe://cluster.local/ns/mesh-test-ambient-l7/sa/default` | 共享 |
| sidecar echo | istio-proxy | `spiffe://cluster.local/ns/mesh-test-sidecar/sa/default` | 共享 |

> ✅ **结论**：三种模式都会立即阻止明文访问，只有 mesh 内流量返回 200，并且每个工作负载都有由同一 Root CA 签发的独立 SPIFFE ID。sidecar 和 ambient 都满足“集群内部 pod 到 pod 流量必须使用 mTLS”的要求。

**差异所在**：ambient 会透明地应用 mTLS —— `istio-cni` 在 pod 的网络 namespace 内设置流量重定向，并由 ztunnel 通过端口 15008 上的 HBONE（mTLS）隧道承载流量 —— 无需应用代码或注入 sidecar。Sidecar 则通过应用 pod 内的 istio-proxy container 实现相同功能。两种模式的证书轮换和迁移策略详情请参阅 [mTLS](../security/01-mtls.md)。

## 2. NetworkPolicy —— 测试结果

Ambient 通过 HBONE 隧道（TCP 15008）将 pod 的真实流量转发至 ztunnel，随后由 ztunnel 解密并交付给目标。这意味着**仅允许应用端口（例如 8080）的 NetworkPolicy 会阻止发往已加入 ambient 的 pod 的入站流量**，因为数据包实际到达的是 15008。要将 ambient 与 NetworkPolicy 一起使用，必须在目标 pod 上**添加一条允许 TCP 15008 入站的规则**。

**测试设置**：在专用 `mesh-isolated-test` 集群上启用 VPC CNI NetworkPolicy enforcement（`enableNetworkPolicy=true`、`aws-network-policy-agent v1.3.5-eksbuild.3`、eBPF）—— 这在早期测试所使用的共享集群上无法安全进行，因为它会同时激活属于其他团队的 13 个既有闲置 NetworkPolicy。专用单租户集群完全消除了这一影响范围顾虑。

> ⚠️ **测试期间发现的运维陷阱**：在启用 `enableNetworkPolicy` *之前*创建的 pod 不会被追溯执行策略 —— eBPF hook 仅在 pod 网络设置（CNI ADD）时附加。一次健全性检查直接证实了这一点：对已运行的 pod 应用仅允许端口 9999 的 policy 后，端口 8080 流量仍可未受阻止地通过。启用 addon 后，必须执行 `kubectl rollout restart`（重新创建 pod），NetworkPolicy 才会生效。这是在生产集群启用 NetworkPolicy 前值得了解的真实陷阱。

**测试 1 —— 入站仅限 TCP 8080**（新建 pod，已确认 enforcement 生效）

| 模式 | 结果 |
|---|---|
| sidecar | ✅ 200 OK —— 不受影响 |
| ambient-L4 | ❌ 被阻止（`i/o timeout`） |
| ambient-L7 | ❌ 被阻止（`i/o timeout`） |

**测试 2 —— 入站允许 TCP 8080 + TCP 15008（HBONE）**

| 模式 | 结果 |
|---|---|
| ambient-L4 | ✅ 200 OK —— 已恢复 |
| ambient-L7 | ✅ 200 OK —— 已恢复 |

> ✅ **结论**：通过真实流量验证了上述假设。Ambient 在工作负载 pod 网络 namespace 的真实入站数据包到达 ztunnel 的 HBONE 端口（15008），而非应用端口（8080）；仅允许应用端口的 NetworkPolicy 会悄然破坏已加入 ambient 的 pod。Sidecar 不受影响，因为 sidecar 的流量捕获完全发生在 pod 自身的网络 namespace 内，此时数据包已到达应用端口。

我们建议采用纵深防御：同时应用网络层（NetworkPolicy）和身份层（AuthorizationPolicy）控制。sidecar 模式下 mTLS 与 NetworkPolicy 的冲突详见 [mTLS and NetworkPolicy Conflict](../security/01-mtls.md#7-mtls-and-networkpolicy-conflict)。

## 3. 延迟 —— 测试结果（T5）

**测试设置**：fortio 压测，200 qps，60s，16 个连接，每个 case 12,000 个请求，稳定状态（无 rollout restart 运行）—— 在相同 `mesh-isolated-test` Graviton（m7g.xlarge）node 上比较无 mesh 基线（未加入 mesh 的 namespace）、sidecar、ambient-L4 和 ambient-L7。所有 case 均返回 100% Code 200。

| Case | P50 | P75 | P90 | P99 | P99.9 |
|---|---|---|---|---|---|
| no-mesh（基线） | 0.82ms | 1.33ms | 1.73ms | 1.97ms | 2.00ms |
| sidecar | 2.11ms | 2.60ms | 2.89ms | 3.91ms | 8.00ms |
| ambient-L4（无 waypoint） | 0.86ms | 1.34ms | 1.74ms | 1.98ms | 2.93ms |
| ambient-L7（waypoint） | 2.68ms | 3.06ms | 3.63ms | 3.98ms | 7.67ms |

**相对无 mesh 基线的 P50 开销**：sidecar +1.29ms · ambient-L4 +0.04ms（可忽略）· ambient-L7 +1.86ms

> ✅ **结论**：与此前引用的已发布 ambient 模式 benchmark 一致（仅 L4 低于 sidecar，waypoint 大致与 sidecar 持平或略高）—— 这些现已是第一方测量数据，而非引用。对于加密货币交易路径这类延迟敏感工作负载，这与下文 §4 一致：**避免使用 waypoint 可同时改善延迟和 rollout 稳定性**。

## 4. 零停机 Rollout —— 503 测试结果（核心发现）

### 背景

Ambient 的顾虑在于：**L7 waypoint（Envoy）会从其连接池中复用连接，连接池以目标 IP:Port 作为键**，而**当 pod 终止时，ztunnel 不会通知 waypoint**。如果已终止 pod 的 IP 被分配给新的 pod，waypoint 可能复用现已无效的连接并返回 503。Sidecar 也可能遭遇类似的 pod 终止竞态（机制见 [Connection Errors During Pod Termination](../troubleshooting/common-errors.md#connection-errors-during-pod-termination)）。我们在 EKS 1.36 上正面比较了这两种故障模式。

**测试环境**
- 专用单租户集群 `mesh-isolated-test`，EKS control plane 和 worker node 均为 v1.36.2，arm64（Graviton m7g.xlarge），Istio 1.30.2
- 3 个 namespace（sidecar / ambient-L4 / ambient-L7）运行**字节完全相同的工作负载**（一个具有 6 个副本的 echo server Deployment + 一个 fortio client）—— 仅 namespace label 不同
- fortio client 在目标 namespace 的 `echo` Deployment 被反复 `rollout restart` 时，以 100 req/s 保持 keepalive 连接
- 每种模式收集 60,000 个请求（= 100 qps × 600s）

### 结果

| 模式 | Rollout 周期 | 请求数 | 503 数量 | 503 比率 | 其他错误（-1，TCP reset/EOF） | 使用的 socket |
|---|---|---|---|---|---|---|
| sidecar | 42 | 60,000 | 324 | **0.5%** | 2（0.0%） | 350 |
| ambient-L4（无 waypoint） | 64 | 60,000 | **0** | **0%** | 195（0.3%） | 1,652 |
| ambient-L7（waypoint） | 65 | 59,913 | 1,528 | **2.6%** | 84（0.1%） | 2,486 |

> 完美 keepalive 应只使用 16 个 socket。ambient-L7 在运行结束时还有 60,000 次调用中的 87 次未完成，其平均延迟（50.4ms）远高于另外两种模式（约 2-3ms）。

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

1. **Ambient-L7（waypoint）的 503 比率（2.6%）约为 sidecar（0.5%）的 5 倍**，这是在该专用集群上得出的结果 —— 差距甚至大于早些时候在共享且存在资源竞争的集群上同日测量的结果所显示的差距（见下文隔离说明），从而强化而非减弱了最初的顾虑：在 rollout 波动下，“waypoint 的连接池复用陈旧连接并产生 503”。
2. **Ambient-L4（无 waypoint）再次产生了零实际 HTTP 503。**它出现的是 0.3% 的连接级 TCP 错误（“-1”，无响应）。在 L4，故障表现为*连接丢失*，而非*503 响应* —— 重连处理留给 client/application，而非由 proxy 合成错误响应。
3. Ambient-L7 还出现了较大的平均延迟尖峰，以及在运行期间始终未完成的 87 个请求 —— 这与 waypoint 在 rollout 波动和持续负载叠加时陷入困难一致，且区别于另外两种模式。
4. 在相同 600 秒窗口内完成的 rollout 周期数（sidecar / ambient-L4 / ambient-L7 分别为 42 / 64 / 65）远高于早先在繁忙共享集群上的测量，因为该专用集群没有其他租户竞争 CPU/网络资源 —— *相对*排序（sidecar 最慢、ambient-L4 最快）得以保持，但绝对 rollout 速度高度依赖集群资源竞争，不应过度解读为任何模式的内在属性。

### 后续：优雅关闭加固之后

上述基线数据反映的是**完全未进行关闭调优**的情况。添加以下两项变更后，我们重新运行了相同的 T1 测试（100 qps × 600s，每种模式 60,000 个请求）：

- **所有三种模式**：在 `echo` container 上设置 `lifecycle.preStop.sleep.seconds: 10`（K8s 1.29+ 原生 sleep action —— 无需 exec/shell），再加上 `terminationGracePeriodSeconds: 40`，从而在 pod 实际停止接受连接前，为 Endpoint removal 在整个集群中传播留出时间
- **仅 sidecar**：通过 `proxy.istio.io/config` pod annotation 向 istio-proxy 注入 `EXIT_ON_ZERO_ACTIVE_CONNECTIONS=true` + `terminationDrainDuration: 30s`（已确认存在于 istio-proxy init container 的实际 env 中）—— 活跃连接降至零时立即退出，而不是始终等待完整的 30s

| 模式 | Rollout 周期 | Code 200 | Code 503 | Code -1 | 使用的 socket | 平均延迟 |
|---|---|---|---|---|---|---|
| sidecar（加固后） | 42 | 60,000（100%） | **0** | **0** | 16（完美 keepalive） | 2.630ms |
| ambient-L4（加固后） | 38 | 60,000（100%） | **0** | **0** | 395 | 1.189ms |
| ambient-L7（加固后） | 45 | 59,352（98.9%） | 648（1.1%） | **0** | 678 | 3.843ms |

**基线 → 加固后对比**

| 模式 | 基线错误率 | 加固后错误率 | 变化 |
|---|---|---|---|
| sidecar | 0.5% 503 + 0% TCP | 0% 503 + 0% TCP | **503 被完全消除** |
| ambient-L4 | 0% 503 + 0.3% TCP | 0% 503 + 0% TCP | **TCP 错误也被完全消除** |
| ambient-L7 | 2.6% 503 + 0.1% TCP | 1.1% 503 + 0% TCP | 503 比率降低超过一半 |

> ✅ **结论**：测量结果验证了以下假设：这些 503 源于 pod 在其 Endpoint removal 传播前未优雅关闭 —— 仅 `preStop sleep 10` 就完全消除了 sidecar 和 ambient-L4 的错误。Ambient-L7（waypoint）也有显著改善，但未达到零 —— 这意味着 waypoint 自身的陈旧连接复用机制（上文 §4 的核心发现）不能仅凭工作负载侧的优雅关闭调优完全解决。如果通过 waypoint 路由，请将此加固作为基线，并仍为它无法消除的残余 503 风险留出余量。

### 将重试作为缓解措施的风险 —— 测试结果（T2）

**测试设置**：一个由 `order`（6 个副本，非幂等 `POST /order`，在 handler 中延迟 0.1s，向 `collector` 报告其 request ID）、`collector`（统计不同 request ID，并标记任何多次出现的 ID）和 `order-client`（以每个请求一个唯一 UUID 持续产生 POST 负载）组成的测试工具。通过相同的 Istio VirtualService config 对 sidecar（istio-proxy）和 ambient-L7（waypoint）应用 retry policy（`attempts: 3, perTryTimeout: 2s, retryOn: 503,reset,connect-failure`）。每种模式在 `order` Deployment 并发 `rollout restart` 的情况下运行 300s。

| 模式 | Rollout 周期 | 已发送请求 | client 可见故障（全部 3 次重试耗尽） | 重复执行 |
|---|---|---|---|---|
| sidecar（VirtualService retry） | 11 | 9,135 | 15（0.16%） | **0** |
| ambient-L7（waypoint retry） | 12 | 7,229 | 21（0.29%） | **0** |

> ✅ **结论**：两种模式均未观察到重复的非幂等执行。较低的 client 可见故障率确认重试确实被触发，并且大多掩盖了瞬态 rollout 波动错误 —— 但成功重试中没有任何一次导致同一逻辑请求被处理两次。

> ⚠️ **这不意味着该竞态不可能发生。**这意味着它未在这些特定条件下出现（perTryTimeout=2s、20 req/s、6 个副本、默认优雅关闭、无 `preStop` hook）。理论机制是：原始请求已到达 app、但其响应尚未返回调用方时，在这一狭窄窗口内连接断开后重发重试。连续 300s 的 rollout 波动未在任一模式中捕获到该情况，但生产环境的非幂等路径在没有服务端幂等性 key 时，仍应默认将 mesh 级 retry 视为不安全：此测试降低了该竞态*常见*的置信度，但并未证明其*安全*。

### 测试隔离说明

<details>
<summary>为何必须使用专用集群，以及仍然出了什么问题（点击展开）</summary>

早些时候同日进行的一轮 T1/T3 测试在共享集群（`fsi-demo-cluster`）上的 4 个专用 namespace 中运行。该集群的 `benchmark` namespace 同时正在跨 100 多种 EC2 instance type 运行大型 Kafka benchmark job sweep；ambient-L7 T1 负载完成后不久，该轮创建的所有资源（全部 4 个 namespace、`istio-system` 和所有 Istio/Gateway API CRD）在没有确认 root cause 的情况下同时消失（未发现匹配的 ArgoCD Application，也未发现 Kyverno/Gatekeeper policy）—— 导致 T2、T4 和 T5 未运行，并令在该资源竞争环境下收集的 T1 数字的有效性存在一些疑问。

本轮专门使用了一个全新的单租户集群（`mesh-isolated-test`、独立 VPC、无其他工作负载）来消除这类干扰，并在无资源异常的情况下端到端完成了 T1–T5。然而，另一个隔离缺口随之出现：新集群第一次 T1 尝试进行到一半时，本地 workstation 共享的 `~/.kube/config` current-context 悄然从 `mesh-isolated-test` 切换到了不相关的集群 —— 使该次尝试无效（context 切换后，rollout-restart loop 开始因 `namespace not found` 而失败，尽管已建立的 in-flight fortio load connection 未受影响）。通过显式 kubeconfig 检查，确认 `mesh-isolated-test` 上的 namespace 和资源始终完全完好 —— 这是 workstation 级别的 context 混淆，而非集群侧删除。修复方法是：使用仅限 `mesh-isolated-test` 的 kubeconfig 文件，在每个测试 script 中显式引用，并添加 context 再次漂移即中止的 guard。本文全部最终数字均来自修正后、context 已锁定的重跑。

</details>

## 5. 建议：分层方法

与其二选一地选择“sidecar 或 ambient”，我们建议**按工作负载层级应用不同 mesh 模式**。这与 [Ambient Mode](../advanced/01-ambient-mode.md#use-cases) 中的使用场景指导一致，本轮测试也以证据支持了它。

| 层级 | 示例 | 建议 | 理由 |
|---|---|---|---|
| 核心（订单创建/撮合/结算，非幂等） | Trading API | **仅 Ambient L4（无 waypoint）或保留 sidecar** | §4：通过 waypoint 路由时，503 比率约为 sidecar 的 5 倍；仅 L4 的 503 为零。如确实需要 L7 功能，sidecar 是更成熟的选择。T2 在任一模式的 retry 下均未发现重复执行实例，但这不能证明安全 —— 无论 mesh 模式如何，在此层级默认关闭 retry。 |
| 半核心（幂等读 API） | 价格/余额查询 | Ambient（L4，需要时 L7） | 幂等请求可以安全重试，因此 waypoint 风险影响较小 |
| 边缘（查询、通知、批处理） | Dashboard、告警 | 积极采用 ambient | 最大化资源/运维收益；测试已验证 mTLS 和 rollout 行为安全 |

本轮测试实际验证了 **namespace 级混合部署** —— sidecar、ambient-L4 和 ambient-L7 namespace 在同一集群上并发运行，并且各自独立强制执行 STRICT mTLS。

### 仅 L4 的限制 —— 仍可进行 canary deployment 吗？

仅 L4 的 Ambient 没有 waypoint，因此 ztunnel 从不查看 HTTP request 内部。这意味着**L7 功能 —— 基于 HTTP header/path 的路由、retry、circuit breaking、traffic mirroring —— 不能应用于仅 L4 的 Service。**这是否实际阻碍 canary deployment，取决于流量从何处进入。

> ✅ **Ingress canary 不受影响。**无论后端工作负载以 ambient 还是 sidecar 模式运行，Istio Ingress Gateway 或 Gateway API `Gateway` 始终是独立的完整 Envoy proxy（其自身的 Deployment）。通过 `VirtualService`/`HTTPRoute` 在 v1/v2 subset 之间进行的加权分流完全在 gateway 中决定；随后 ztunnel（L4）仅将连接隧道传输至已选定的目标 pod。面向外部公开 API 的 canary deployment 可与仅 L4 后端正常配合。

> ⚠️ **mesh 内部（east-west）canary 需要在该特定 Service 上使用 L7。**如果 Service A 在 mesh 内调用 Service B，并且希望按百分比分流 B-v1 和 B-v2 的流量，则必须由某个组件在 L7 做出该路由决定 —— ztunnel 无法做到。需要**在 B 前方部署 waypoint（将 B 切换为 ambient-L7），或让 B 运行 sidecar**，该 canary 才能工作。

**总结**：面向外部公开 API 的 canary deployment 可在仅 L4 下正常工作。只应针对需要 mesh 内部 canary 的特定 Service 使用 waypoint 或 sidecar —— 这正是上述分层建议在实践中应如何应用。

**采用前检查清单**

- [ ] 订单/撮合/结算路径是否真正需要 L7 功能（HTTP 路由、retry、traffic split）？如果不需要，仅 Ambient L4 是首选候选方案
- [ ] 是否已更新 NetworkPolicy 以允许 HBONE 端口（15008）？（§2，已验证 —— 如果首次在运行中的集群启用 `enableNetworkPolicy`，请重新创建现有 pod，因为 enforcement 不具追溯性）
- [ ] 是否对非幂等 API 路径应用了 retry policy？（§4 —— T2 测试未发现重复执行，但在没有服务端幂等性 key 时，非幂等路径默认应保持 retry 禁用）
- [ ] 是否已根据自身工作负载重新测量延迟？（§3，已在该集群的 Graviton node 上验证 —— 如果 instance type 或工作负载特征有实质差异，请再次测量）

## 附录：复现这些测试

以下是产生本文每一个数字的实际 config file 和流程。可直接复制它们，在自己的集群上复现结果。

### A. 集群配置（eksctl）

该专用单租户集群使用 eksctl 创建，采用无 NAT gateway 的完全 public subnet（这是一项仅供测试的捷径，可避免需要新的 Elastic IP —— 生产集群请启用 NAT）。

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

Ambient 模式的 waypoint 是 Gateway API `Gateway` resource，因此在安装 Istio 前必须存在 Gateway API CRD。

```bash
# 1) Gateway API CRDs (v1.1.0, compatible with Istio 1.30)
kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.1.0/standard-install.yaml

# 2) Istio 1.30.2 ambient profile (via istioctl, not Helm)
istioctl install -f ambient-overlay.yaml -y
```

<details>
<summary>ambient-overlay.yaml（将 CNI/ztunnel/istiod 调度到 arm64 node）</summary>

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

4 个 namespace —— `mesh-test-base`（未加入 mesh，用于延迟基线）、`mesh-test-sidecar`、`mesh-test-ambient-l4`、`mesh-test-ambient-l7`。仅 label 不同；其他内容字节完全相同。

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
<summary>工作负载 manifest（echo server、6 个副本 + fortio client）—— 全部 4 个 namespace 完全相同，仅 namespace field 改变</summary>

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

### D. mTLS —— PeerAuthentication（§1）

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

ambient-L7 namespace 还需要部署一个 waypoint：

```bash
istioctl waypoint apply -n mesh-test-ambient-l7 --enroll-namespace --wait
```

### E. NetworkPolicy（§2）

通过 addon config 启用 VPC CNI 基于 eBPF 的 NetworkPolicy enforcement。如 §2 所述，这**仅适用于此后创建或重新创建的 pod**。

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

同时运行 fortio load generator（前台运行，在测试期间阻塞）和 `rollout restart` loop（后台运行），然后在 load 完成后停止该 loop。

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

> 💡 如果没有 `-allow-initial-errors`，fortio 的 warmup request 恰好在 rollout 期间命中并获得 503 时，将中止整次运行。对于与 rollout 波动重叠的任何 load test，都必须使用该 flag。

**优雅关闭加固 patch**（用于 §4 中“加固后”重跑，通过 `kubectl patch --type strategic` 应用于现有 Deployment）：

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

使用相同 fortio command，在没有 rollout loop 的稳定状态下运行。

```bash
kubectl exec -n "$NS" "$CLIENT" -c fortio-client -- \
  fortio load -qps 200 -t 60s -c 16 -allow-initial-errors http://echo:8080/
```

### H. Retry / 重复执行测试工具（T2，§4）

一个包含 3 个 pod 的测试工具 —— `order`（处理非幂等 POST）、`collector`（检测重复 request ID）、`order-client`（持续负载）—— 被完全相同地部署到 sidecar 和 ambient-L7 namespace。

<details>
<summary>ConfigMap —— order_server.py / collector.py / client.py</summary>

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

运行流程与（F）中的 rollout loop 相同，但目标为 `order` Deployment，在测量前重置 `collector` 的计数器，并在之后查询重复数：

```bash
kubectl rollout restart deployment/collector -n "$NS"   # reset the counter

# ... same rollout-loop pattern as §F, targeting `order`, for 300s ...

CLIENT=$(kubectl get pods -n "$NS" -l app=order-client -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n "$NS" "$CLIENT" -c order-client -- python3 -c \
  "import urllib.request; print(urllib.request.urlopen('http://collector.$NS.svc.cluster.local:9090/dupes', timeout=5).read().decode())"
```

## 参考资料

- [Ambient Mode](../advanced/01-ambient-mode.md) —— ztunnel/waypoint 架构、与 sidecar 的资源对比
- [mTLS](../security/01-mtls.md) —— STRICT/PERMISSIVE 模式、证书管理、NetworkPolicy 冲突
- [Troubleshooting: Connection Errors During Pod Termination](../troubleshooting/common-errors.md#connection-errors-during-pod-termination)
- [Sidecar Injection](../advanced/07-sidecar-injection.md)
- [Service Mesh Solution Comparison](01-service-mesh-comparison.md)
