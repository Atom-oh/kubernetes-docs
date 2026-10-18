# Istio 高级主题测验

> **验证基线**：Istio 1.31.0、Kubernetes 1.32–1.37、Argo Rollouts 1.10.1
> **上次审阅**：October 16, 2026

这些问题旨在区分配置、运行时行为和证据。各示例彼此独立；请选择相关拓扑，并保留链接指南中的先决条件。下文中的历史计算输入不是当前价格，也不是新的基准测试结果。

## 选择题（1–5）

### 问题 1：Ambient 和 Sidecar 模式

在 ambient 模式中，哪项架构变更可以降低每个工作负载的代理开销？

- A. Ambient 始终比 sidecar 提供更多功能。
- B. 每个节点上的 ztunnel 处理 L4 流量，并为需要 L7 处理的场景单独部署 waypoint。
- C. 可以保证安装速度提高十倍。
- D. 无需更改配置即可增强所有策略。

<details>
<summary>显示答案</summary>

**答案：B**

Ambient 无需在每个加入的工作负载 Pod 中都部署一个 sidecar 代理。ztunnel 提供 L4 安全覆盖网络；目标 waypoint 的加入情况和所支持的 L7 策略决定了额外的处理路径。waypoint 并非一个通用的共享跳点，不能由任意一个 ztunnel 随意选择。

| 方面 | 正确的比较方式 |
|---|---|
| CPU/内存 | 在流量、策略、遥测、节点数和 waypoint 副本数相当的条件下进行测量。不存在普遍适用的 98% 节省。 |
| 加入方式 | Ambient 可以在不重启应用的情况下，让现有且无 sidecar 的 Pod 加入；移除已有 sidecar 则需要替换工作负载。 |
| 功能 | 支持情况各不相同。Waypoint 不支持 EnvoyFilter；ambient 多集群也有其自身的 Beta 拓扑限制。 |
| 成熟度 | Ambient 核心功能在 Istio 1.24 中达到 GA；这并不意味着之后推出的每项功能都已达到 GA。 |
| 安全 | mTLS 和策略取决于实际流量路径以及支持的策略附加方式；若 L7 强制执行是必需的，则必须确保流量经过 waypoint。 |

例如，**假设**有 1,000 个 sidecar，每个占用 50 MB/0.1 vCPU，总计为 50,000 MB/100 vCPU。假设有 10 个 ztunnel，每个占用 50 MB/0.1 vCPU，再加上一个占用 200 MB/0.5 vCPU 的 waypoint，则总计为 700 MB/1.5 vCPU。按算术计算，降幅为 98.6%/98.5%；这些任意设定的输入既不是基准测试结果，也不是容量保证。

安装受支持的 ambient 组件并检查现有 revision/injection 标签后，可按以下方式加入：

```bash
kubectl label namespace ambient-demo istio.io/dataplane-mode=ambient --overwrite
kubectl get daemonset ztunnel -n istio-system
istioctl ztunnel-config workloads --workload-namespace ambient-demo
```

命名空间必须已存在、确实应使用 ambient，并且其中的工作负载必须兼容。这些命令本身不会安装 CNI/ztunnel、配置 waypoint，也无法安全迁移已注入的 Pod。

[Ambient 指南](../../../service-mesh/istio/advanced/01-ambient-mode.md)

</details>

### 问题 2：多集群发现

在 Istio sidecar 多集群网格中，哪个组件会读取经过授权的 Kubernetes 服务注册表，并生成代理发现配置？

- A. Istiod
- B. 只有 CoreDNS
- C. 只有东西向网关
- D. 只有 ServiceEntry 对象

<details>
<summary>显示答案</summary>

**答案：A**

每个主集群中的 Istiod 都会读取其有权访问的 Kubernetes API。在主集群-远程集群拓扑中，远程工作负载使用主集群的控制平面；远程安装并不是由“超级主集群”管理的第二个完整 Istiod。在多主集群拓扑中，各主集群有自己的控制平面，并执行经过授权的远程发现。

Istiod 会生成/分发代理配置；它不会将 VirtualService/DestinationRule Kubernetes 对象或应用数据复制到每个集群。请单独分发配置。必须有意配置共享信任；相同的 meshID 值不会创建共同 CA。

CoreDNS 可以使用转发和其他配置，但它不是 Istio 的跨集群注册表。网关负责传输跨网络流量。ServiceEntry 会添加注册表条目，包括外部服务或其他显式注册的服务。

不要臆造 `data.kubeconfig` 字段，应生成实际的远程 secret：

```bash
# After the remote installation; contexts must identify the intended clusters.
istioctl create-remote-secret --context="$CTX_CLUSTER2" --name=cluster2   | kubectl --context="$CTX_CLUSTER1" apply -f -
```

该 secret 授予主集群访问**远程 API**的权限。请保护其中的凭证并检查生成的 RBAC。它不会将网络互联，也不会复制策略对象。

[多集群指南](../../../service-mesh/istio/advanced/02-multi-cluster.md)

</details>

### 问题 3：EnvoyFilter 的用途

EnvoyFilter 的主要用途是什么？

- A. 创建 Kubernetes Service。
- B. 自动生成每个 VirtualService。
- C. 自定义选定的、已生成的 Envoy 代理配置。
- D. 替换所有 Istiod 安装设置。

<details>
<summary>显示答案</summary>

**答案：C**

应优先使用受支持的路由、遥测、安全或扩展 API 来完成任务。当这些 API 无法提供所需的受支持行为，且已理解生成的配置时，才适合使用 EnvoyFilter。例如，下面这个仅适用于 sidecar 的 Lua filter 会更改一个示例性的出站请求标头：

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: quiz-header
  namespace: default
spec:
  workloadSelector:
    labels:
      app: reviews
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: SIDECAR_OUTBOUND
      listener:
        filterChain:
          filter:
            name: envoy.filters.network.http_connection_manager
            subFilter:
              name: envoy.filters.http.router
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.lua
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.http.lua.v3.Lua
          default_source_code:
            inline_string: |
              function envoy_on_request(handle)
                handle:headers():replace("x-quiz-example", "yes")
              end
```

命名空间和选择器必须与目标代理相匹配。通常，不设选择器会覆盖该资源所在命名空间中的代理；位于根命名空间的资源则可能作用于整个网格。不要在同一个 YAML 对象中写两个 `workloadSelector` 键。Lua 插入的标头并不是经过身份验证的身份信息。

其他用途需要具备完整依赖：Wasm 模块需要经过验证的制品/运行时以及挂载方式，或使用受支持的 WasmPlugin 分发路径；全局限流需要可访问的服务、匹配的 descriptor 和故障策略。仅仅插入 filter 名称并不能提供这些系统。Ambient waypoint 不支持 EnvoyFilter。

升级期间，请验证准确的 Istio/Envoy 版本、实际生效范围、filter 顺序、类型化载荷和生成的代理配置。Istiod 的安装值仍使用 Helm/istioctl 配置；IstioOperator YAML 仍然是 istioctl 的输入，尽管集群内 operator 已被移除。

[EnvoyFilter 指南](../../../service-mesh/istio/advanced/03-envoy-filter.md)

</details>

### 问题 4：Sidecar 注入

哪些设置可以为新创建的 Pod 禁用自动 sidecar 注入？

- A. 显式将命名空间标签设为 `istio-injection=disabled`。
- B. 将工作负载 Pod 模板标签设为 `sidecar.istio.io/inject: "false"`。
- C. 在不更改配置的情况下重启 Istiod。
- D. A 和 B。

<details>
<summary>显示答案</summary>

**答案：D**

```bash
kubectl label namespace example istio-injection=disabled --overwrite
kubectl get namespace example -L istio-injection,istio.io/rev
```

下面这段配置属于现有 Deployment 的 spec；保留其 image、选择器及其他字段：

```yaml
spec:
  template:
    metadata:
      labels:
        sidecar.istio.io/inject: 'false'
```

禁用注入的命名空间标签或 Pod 标签具有优先效力。特别是，Pod 选择加入注入**不会**覆盖 `istio-injection=disabled`。只移除 `istio-injection=enabled` 并不能在所有情况下禁用注入：还必须检查 revision 标签、Pod 注入选择和注入器默认设置。旧版 inject annotation 已弃用，应改用标签；避免新旧设置互相冲突。

更改只影响新建的 Pod，不影响已注入代理的 Pod。要更改现有 Pod，请使用工作负载经过审查的 rollout。混合配置的命名空间可以启用注入，同时让选定工作负载模板选择退出；这也会改变该工作负载参与网格/安全策略的方式。

```bash
kubectl get pod "$POD" -n "$NAMESPACE" -o json   | jq '{containers: [.spec.containers[].name],
         initContainers: [.spec.initContainers[]? | {name, restartPolicy}]}'
```

原生 sidecar 可能会以 `restartPolicy: Always` 的形式出现在 initContainers 中；只检查普通容器或期待恰好 `2/2` Ready 都不够。Ambient 加入是另一种独立机制。

[注入指南](../../../service-mesh/istio/advanced/07-sidecar-injection.md)

</details>

### 问题 5：Argo Rollouts 流量拆分

Argo Rollouts 会更新哪个 Istio **声明式资源**中的 HTTP 路由权重？

- A. Rollouts 控制器进程
- B. VirtualService
- C. 只有 Kubernetes Service
- D. 只有 Gateway

<details>
<summary>显示答案</summary>

**答案：B**

Rollouts 会更新指定路由的权重，Istiod 会转换配置，而 **Envoy 执行**路由。VirtualService 不是处理数据包的进程。10% 是概率路由权重，并不保证每 100 个请求中恰好有 10 个到达 canary。重试和长连接会影响观察结果。

基于 subset 的替代方案需要一个选择该应用的 Service、两个 subset，以及由 Rollouts 管理它们的 revision 标签：

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: test-subsets
  namespace: rollouts-demo
spec:
  host: test
  subsets:
  - name: stable
    labels:
      app: test
  - name: canary
    labels:
      app: test
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: test-subsets
  namespace: rollouts-demo
spec:
  hosts:
  - test
  - test.rollouts-demo.svc.cluster.local
  http:
  - name: primary
    route:
    - destination:
        host: test
        port:
          number: 8080
        subset: stable
      weight: 100
    - destination:
        host: test
        port:
          number: 8080
        subset: canary
      weight: 0
    retries:
      attempts: 0
```

将此策略片段合并到指南中完整且匹配的 Rollout 中；不要将其作为不完整资源应用，也不要与其他主机级流量拆分策略组合使用：

```yaml
spec:
  strategy:
    canary:
      trafficRouting:
        istio:
          virtualService:
            name: test-subsets
            routes:
            - primary
          destinationRule:
            name: test-subsets
            canarySubsetName: canary
            stableSubsetName: stable
      steps:
      - setWeight: 10
      - pause: {}
```

必须存在名为 `test` 的 Service、完整的 Rollout 选择器/模板、控制器/RBAC，以及 `rollouts-demo` 命名空间。Rollouts 会更新 subset revision 标签。`retries.attempts: 0` 会禁用此路由上的网格重试；应用自身的重试行为则是另一回事。

只有经过配置才会执行流量分析。自动分析失败可以中止 rollout，但不会撤销应用/数据库副作用。请使用指南中的完整主机级或 subset 示例，每次只采用一种策略。

[Argo Rollouts 指南](../../../service-mesh/istio/advanced/08-argo-rollouts.md)

</details>

## 简答题（6–10）

### 问题 6：Ambient 资源与成本分析

使用原先假设的输入（500 个 Pod、五个 r5.xlarge 节点、每月 730 小时、每节点每小时 $0.252），计算代理资源，并说明账单节省是否会随之而来。每个 sidecar 使用 50 MB/0.1 vCPU；每个 ztunnel 使用 50 MB/0.1 vCPU；假设 waypoint 使用 200 MB/0.5 vCPU。

<details>
<summary>参考答案</summary>

价格和资源数值是**练习输入**，不是当前 AWS 报价或实测的 Istio 用量。以下 MB/GB 算术采用十进制单位。

| 资源 | Sidecar | 假设五个节点上的 Ambient | 算术降幅 |
|---|---|---|---|
| 内存 | 500 × 50 = 25,000 MB | 5 × 50 + 200 = 450 MB | 24,550 MB，98.2% |
| CPU | 500 × 0.1 = 50 vCPU | 5 × 0.1 + 0.5 = 1 vCPU | 49 vCPU，98% |

一个 r5.xlarge 有四个 vCPU 和 32 GiB 内存。五个节点在满足系统/应用需求之前只有 20 个 vCPU，因此在这个固定的五节点场景中，假设的 50 vCPU sidecar 需求本身就不可行。仅考虑代理 CPU 的最低节点数为 ceil(50/4) = 13；此数值未计入应用 CPU、系统预留、内存、IP 限制、调度和弹性要求。

不要将这个 13 节点最低值与“一个 ambient 节点”比较，同时仍按五个节点计算 ztunnel 资源。请按**实际保留的节点数**重新计算 ztunnel 资源需求，并计入 waypoint 的高可用/流量容量和所有其他工作负载。

按假设费率计算：

- 一个节点月的费用为 `0.252 × 730 = $183.96`。
- 五个节点不变时，两种模式每月都需支付 `$919.80`：单靠测得的代理余量不会降低此账单。
- 13 个节点月的费用应为 `$2,391.48`，这是对先前算术的修正；这并不证明生产环境确实需要这样的集群。
- 如果经过验证的集群分别包含 Nₛ 和 Nₐ 个节点，则计算资源费用差为 `(Nₛ − Nₐ) × $183.96/month`，还未计入其他成本或承诺用量。

完整比较还应包括 EKS/控制平面费用、负载均衡器、跨 AZ/Region 传输、存储、遥测以及实际采购承诺。Sidecar 确实使用本地通信；Ambient 不会自动消除网络费用或 OOM。

如果练习中的迁移成本为 $6,000，则只有在实测净月节省 S 为正数时，回本时间才是 `6000 / S` 个月。若计费容量不变，S 可能为零，这样的回本计算就没有有限结果。不要仅凭代理算术就断言此前的账单节省 92% 或 2.7 个月 ROI。

[Ambient 指南](../../../service-mesh/istio/advanced/01-ambient-mode.md)

</details>


### 问题 7：主集群-远程 EKS 网格

描述两个现有 EKS 集群（分别位于 us-east-1 和 us-west-2）的主集群-远程集群设计，包括发现、信任、网络先决条件和跨集群验证示例。

<details>
<summary>参考答案</summary>

这是一个 **sidecar** 设计。Ambient 当前的多集群 Beta 支持多主集群/多网络，不支持这种主集群-远程集群模型。主 Istiod 为远程代理提供服务；不存在一个必须从上级主集群接收配置的完整远程 Istiod。

安装之前，应建立经过审查的共同信任、API 访问、DNS、安全组/防火墙以及所需的 L4 控制/数据路径。不同的网络 ID 用于标识不同网络，但不会建立网络连通性。对于多网络，双方都需要适当的东西向网关，以便访问远程端点。跨 Region 网络成本和故障恢复仍需单独负责。

主集群的必要配置是 istioctl 输入：

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  values:
    global:
      meshID: mesh1
      externalIstiod: true
      multiCluster:
        clusterName: cluster1
      network: network1
```

对于远程集群，**198.51.100.10 是文档占位符**，不是 EKS 端点：

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  profile: remote
  values:
    istiodRemote:
      injectionPath: /inject/cluster/cluster2/net/network2
    global:
      meshID: mesh1
      multiCluster:
        clusterName: cluster2
      network: network2
      remotePilotAddress: 198.51.100.10
```

远程命名空间还需要标识管理它的主集群：

```bash
kubectl --context="$CTX_CLUSTER2" annotate namespace istio-system   topology.istio.io/controlPlaneClusters=cluster1 --overwrite
```

请按照维护中的指南准备信任、使用相同的 Istio 版本生成网关、公开主集群发现/注入服务，并在创建问题 2 中所示的远程访问 secret 之前安装远程 profile。在这个双网络示例中，远程注入路径以 `net/network2` 结尾。

EKS NLB 通常会提供 DNS 名称。该版本可以将 DNS 值表示为 remotePilotAddress，但仅渲染 chart 并不能证明发现/注入连通性或证书名称正确。请完成官方的外部控制平面 DNS/证书/注入 URL 设计；不要用任意地址替代缺失的负载均衡器 IP。

验证时，请使用同一 Istio 发行版中的 `helloworld` 和 `curl` 示例。按照文档，在两个集群中创建相同的命名空间/Service 身份，并部署带版本号的工作负载。即使 Service 没有本地端点，它仍可提供本地 Kubernetes DNS，同时由 Istio 发现远程端点：

```yaml
apiVersion: v1
kind: Service
metadata:
  name: helloworld
  namespace: sample
spec:
  selector:
    app: helloworld
  ports:
  - name: http
    port: 5000
    targetPort: 5000
```

单独创建此 Service 不会部署任何应用。示例中的实际后端监听端口 5000；仅仅声明 containerPort 8080 并不会让标准 nginx 进程在该端口监听。完成整个示例部署后，选择已知的 curl Pod/容器，并检查数据平面配置和响应：

```bash
kubectl --context="$CTX_CLUSTER1" get service,endpointslice -n sample
kubectl --context="$CTX_CLUSTER2" get service,endpointslice -n sample
istioctl --context="$CTX_CLUSTER1" proxy-status
istioctl --context="$CTX_CLUSTER1" proxy-config endpoints "$CURL_POD" -n sample   --cluster 'outbound|5000||helloworld.sample.svc.cluster.local'
kubectl --context="$CTX_CLUSTER1" exec -n sample "$CURL_POD" -c curl --   curl --fail --max-time 5 http://helloworld.sample.svc.cluster.local:5000/hello
```

在多网络场景中，客户端看到的可能是东西向网关端点，而不是可直接访问的远程 Pod IP。一次响应只能证明那一次调用；还要测试两个方向、端点版本、信任、策略和故障场景。

两个目标具有**相同 host/subset/port** 的加权目标，并不意味着本地 80%/远程 20%。应使用明确且受支持的 locality，或使用具有合格端点的显式目标模型。观察跨集群流量时，选择一个 telemetry reporter，并使用真实的 source_cluster/destination_cluster 标签。

[多集群指南](../../../service-mesh/istio/advanced/02-multi-cluster.md)

</details>

### 问题 8：共享的按用户限流

为 `/api/premium/*` 实现共享的每分钟 100 个请求配额。说明身份、descriptor 和故障约定。

<details>
<summary>参考答案</summary>

请求路径为：**经过身份验证的入口 → 专用 Envoy 网关 → 共享限流服务/Redis 决策 → 后端或拒绝**。本地代理令牌桶并不是跨网关副本共享的配额。

以下条件示例假定：

- `istio-system` 中有一个专用网关，实际标签为 `app: premium-gateway`，并且匹配 TLS/路由配置以及已有的后端 Service。
- 可信的身份验证层会移除调用方提供的 x-user-id，并提供一个非空的规范用户身份。只有经过身份验证的路径才能访问该网关/后端。原始的、由调用方控制的标头不代表用户身份。
- 下方显示的现有隔离实验环境 Redis 端点可访问。生产环境的 Redis 身份验证/TLS、持久化、高可用、故障转移和适当连接设置必须另行设计；仅设置副本数并不能实现这些功能。

匹配的 descriptor 是一个**包含两个条目的序列**：`(header_match=premium, user_id=<trusted user>)`。服务端配置必须将动态 user 条目嵌套在 premium 条目之下。顶层只有 user_id 的 descriptor 不会与之匹配。

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ratelimit-config
  namespace: istio-system
data:
  config.yaml: |
    domain: premium-ratelimit
    descriptors:
    - key: header_match
      value: premium
      descriptors:
      - key: user_id
        rate_limit:
          unit: minute
          requests_per_unit: 100
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ratelimit
  namespace: istio-system
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ratelimit
  template:
    metadata:
      labels:
        app: ratelimit
        sidecar.istio.io/inject: 'true'
    spec:
      containers:
      - name: ratelimit
        image: docker.io/envoyproxy/ratelimit:8fe6ea42@sha256:a61547259607d40aff153050c2a87873ca1676d1d9f5f06937d412000dcc2df1
        ports:
        - containerPort: 8080
          name: http
        - containerPort: 8081
          name: grpc
        env:
        - name: LOG_LEVEL
          value: info
        - name: CONFIG_TYPE
          value: FILE
        - name: RUNTIME_ROOT
          value: /data
        - name: RUNTIME_SUBDIRECTORY
          value: ratelimit
        - name: RUNTIME_APPDIRECTORY
          value: config
        - name: RUNTIME_WATCH_ROOT
          value: 'false'
        - name: RUNTIME_IGNOREDOTFILES
          value: 'true'
        - name: USE_STATSD
          value: 'false'
        - name: REDIS_SOCKET_TYPE
          value: tcp
        - name: REDIS_URL
          value: redis-ratelimit.istio-system.svc.cluster.local:6379
        - name: HOST
          value: '::'
        - name: GRPC_HOST
          value: '::'
        - name: HEALTHY_WITH_AT_LEAST_ONE_CONFIG_LOADED
          value: 'true'
        volumeMounts:
        - name: config-volume
          mountPath: /data/ratelimit/config
          readOnly: true
        command:
        - /bin/ratelimit
        resources:
          requests:
            memory: 128Mi
            cpu: 100m
          limits:
            memory: 512Mi
            cpu: 500m
        readinessProbe:
          httpGet:
            path: /healthcheck
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: config-volume
        configMap:
          name: ratelimit-config
---
apiVersion: v1
kind: Service
metadata:
  name: ratelimit
  namespace: istio-system
spec:
  ports:
  - port: 8080
    name: http
    targetPort: 8080
  - port: 8081
    name: grpc
    targetPort: 8081
  selector:
    app: ratelimit
```

该镜像使用带摘要的已验证上游提交 8fe6ea42，而不是会变动的 master 标签。gRPC 端口为 **8081**，HTTP 健康检查端口为 **8080**。此工作负载需要匹配的注入器以及实际的网格/网络访问。请通过适当的 Secret/挂载机制配置受保护的 Redis 凭证。确保已加载新配置；此处显示的文件模式设置并不能证明支持热加载。

使用生成的 Istio gRPC 集群，以便沿用已建立的服务发现/TLS 策略：

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: premium-ratelimit
  namespace: istio-system
spec:
  workloadSelector:
    labels:
      app: premium-gateway
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: GATEWAY
      listener:
        filterChain:
          filter:
            name: envoy.filters.network.http_connection_manager
            subFilter:
              name: envoy.filters.http.router
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.ratelimit
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.http.ratelimit.v3.RateLimit
          domain: premium-ratelimit
          failure_mode_deny: true
          timeout: 0.1s
          rate_limit_service:
            grpc_service:
              envoy_grpc:
                cluster_name: outbound|8081||ratelimit.istio-system.svc.cluster.local
                authority: ratelimit.istio-system.svc.cluster.local
            transport_api_version: V3
---
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: premium-ratelimit-actions
  namespace: istio-system
spec:
  workloadSelector:
    labels:
      app: premium-gateway
  configPatches:
  - applyTo: VIRTUAL_HOST
    match:
      context: GATEWAY
    patch:
      operation: MERGE
      value:
        rate_limits:
        - actions:
          - header_value_match:
              descriptor_value: premium
              headers:
              - name: :path
                string_match:
                  prefix: /api/premium/
          - request_headers:
              header_name: x-user-id
              descriptor_key: user_id
              skip_if_absent: false
```

这组 action 刻意限定在专用网关上；若使用共享网关，则应进一步缩小到实际生成的 vhost 范围。前缀之外的请求不会生成 premium descriptor。应确保路由/路径规范化和身份验证策略一致，包括编码路径及其他后端访问路径。

在请求有机会绕过 descriptor 生成之前，拒绝 premium 路径上缺失/为空的身份：

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: premium-requires-identity
  namespace: istio-system
spec:
  selector:
    matchLabels:
      app: premium-gateway
  action: DENY
  rules:
  - to:
    - operation:
        paths:
        - /api/premium/*
    when:
    - key: request.headers[x-user-id]
      notValues:
      - '*'
```

此 DENY 策略仅用于防止缺少标头。它不会验证已提供的值，也不能替代强制要求的可信入口/绕过控制、现有 ALLOW 策略、TLS 或应用授权。

当 `failure_mode_deny: true` 时，限流服务错误通常会导致 HTTP 500，超过限额的决策则会导致 429。100 ms RPC 超时预算只是一个示例，必须根据 Redis 和网络延迟进行测试。仅凭一个标头/统计计数器无法证明配额已生效。

| 验证场景 | 要测试的预期约定 |
|---|---|
| 一个身份经过两个网关副本 | 使用一个共享的 descriptor/窗口配额 |
| 第二个身份 | 使用独立的用户 descriptor |
| 身份缺失或伪造 | 由防护策略/身份验证边界拒绝；不能免费绕过配额 |
| 不在 premium 前缀内的路径 | 不生成 premium descriptor；其他安全/限流策略仍然适用 |
| Redis/RLS 不可用 | 按预期故障关闭，并观察状态码/延迟 |
| 窗口边界或 Redis 重启 | 测量计数器/窗口行为；不要承诺在不同测试运行中第 101 个请求一定会被拒绝 |

请针对获准的只读端点发送数量受限的请求，并使用新的测试身份/窗口。先发送 50 个请求，再发送 150 个请求，并不会启动两个独立的干净配额。响应限流标头需要受支持的服务响应和 filter 配置；不要伪造剩余数量/重置值。

检查 RLS 健康状态、已加载配置和实际 Envoy 统计信息（HTTP 统计前缀下的 `ratelimit.ok`、`ratelimit.over_limit`、`ratelimit.error`）。验证实际导出的 Prometheus 名称/标签，不要臆造 `rejected_total`。不要在大型生产 keyspace 中运行 Redis `KEYS *`，也不要把实现相关的计数器解释为剩余配额。固定版本的 distroless RLS 镜像不是 redis-cli shell。

[限流指南](../../../service-mesh/istio/resilience/02-rate-limiting.md) · [EnvoyFilter 指南](../../../service-mesh/istio/advanced/03-envoy-filter.md)

</details>


### 问题 9：带分析的 Blue/Green

配置带有 preview 和 promotion 后分析的 Blue/Green Rollout。说明流量切换和失败行为，不要把缺失的指标当作成功。

<details>
<summary>参考答案</summary>

这是问题 5 中 canary 策略的一个**替代方案**。它假定已安装 Argo Rollouts 1.10 控制器/CRD、启用了 Istio 注入的演示工作负载和调用方、Prometheus 正在采集匹配的 source-reporter 指标，并且具备运行已验证演示镜像所需的 Linux amd64 容量。这是实验室示例，不是经过测试的生产部署。

在现有的 `rollouts-demo` 命名空间中创建 Service 和完整的 Rollout。Rollouts 会管理 Service 的 revision-hash 选择器；GitOps 不应覆盖这些动态字段。

```yaml
apiVersion: v1
kind: Service
metadata:
  name: test-active
  namespace: rollouts-demo
spec:
  selector:
    app: test
  ports:
  - name: http
    port: 8080
    targetPort: http
---
apiVersion: v1
kind: Service
metadata:
  name: test-preview
  namespace: rollouts-demo
spec:
  selector:
    app: test
  ports:
  - name: http
    port: 8080
    targetPort: http
---
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: test
  namespace: rollouts-demo
spec:
  replicas: 3
  revisionHistoryLimit: 2
  selector:
    matchLabels:
      app: test
  template:
    metadata:
      labels:
        app: test
    spec:
      nodeSelector:
        kubernetes.io/os: linux
        kubernetes.io/arch: amd64
      terminationGracePeriodSeconds: 45
      containers:
      - name: app
        image: argoproj/rollouts-demo@sha256:3225193a6415b14b3fcdd160c40248b2bfd62f8c77326480559b91a41ced6e20
        ports:
        - name: http
          containerPort: 8080
        readinessProbe:
          httpGet:
            path: /
            port: http
          initialDelaySeconds: 3
          periodSeconds: 5
          timeoutSeconds: 1
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 200m
            memory: 256Mi
  strategy:
    blueGreen:
      activeService: test-active
      previewService: test-preview
      autoPromotionEnabled: true
      prePromotionAnalysis:
        templates:
        - templateName: preview-analysis
        args:
        - name: service-name
          value: test-preview
        - name: namespace
          value: rollouts-demo
      postPromotionAnalysis:
        templates:
        - templateName: active-analysis
        args:
        - name: service-name
          value: test-active
        - name: namespace
          value: rollouts-demo
      scaleDownDelaySeconds: 600
```

初始镜像是已验证的蓝色演示摘要；更新时，指南会提供相应的绿色摘要。创建新 revision 后，preview 会指向候选版本。预分析成功后，`autoPromotionEnabled: true` 允许自动 promotion。如果需要有意手动 promotion，则设为 false；这是另一项策略选择。

此处流量来自经网格接入的客户端，并发送至内部 Service。生产环境的边缘公开需要真实的 Gateway、TLS、匹配的主机绑定和授权。仅创建第二个 VirtualService 主机名并不会将其添加到 Gateway，也无法保护 preview 访问。

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: test-bluegreen
  namespace: rollouts-demo
spec:
  hosts:
  - test-active
  - test-active.rollouts-demo.svc.cluster.local
  http:
  - name: active
    route:
    - destination:
        host: test-active
        port:
          number: 8080
      weight: 100
    retries:
      attempts: 0
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: test-preview-route
  namespace: rollouts-demo
spec:
  hosts:
  - test-preview
  - test-preview.rollouts-demo.svc.cluster.local
  http:
  - name: preview
    route:
    - destination:
        host: test-preview
        port:
          number: 8080
      weight: 100
    retries:
      attempts: 0
```

这两条路由都显式禁用了网格重试。promotion 时，preview Service 不会自动切换到旧的 stable 版本。active Service 选择器会切换到新 revision；旧 ReplicaSet 最终会被**缩容**，但不一定会删除。已有连接和应用/数据库副作用不会因选择器变更而撤销。

在 preview 分析之前/期间，应通过 preview Service 生成有代表性的、经过授权的流量。Prometheus 查询不会生成流量。此示例要求每两分钟预计至少有 20 个请求、有限的 2xx 成功率 ≥95%、p95 ≤0.5 秒，并且 5xx/零状态错误 ≤1%：

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: preview-analysis
  namespace: rollouts-demo
spec:
  args:
  - name: service-name
  - name: namespace
  metrics:
  - name: request-volume
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >= 20
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: sum(increase(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
    initialDelay: 5m
  - name: http-2xx-success
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >= 0.95
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: |-
          (sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}",response_code=~"2.."}[2m])) or vector(0))
          /
          sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
    initialDelay: 5m
  - name: latency-p95
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] <= 0.5
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: |-
          histogram_quantile(0.95,
            sum by (le) (rate(istio_request_duration_milliseconds_bucket{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
          ) / 1000
    count: 5
    initialDelay: 5m
  - name: http-error-rate
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] <= 0.01
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: |-
          (sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}",response_code=~"5..|0"}[2m])) or vector(0))
          /
          sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
    initialDelay: 5m
---
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: active-analysis
  namespace: rollouts-demo
spec:
  args:
  - name: service-name
  - name: namespace
  metrics:
  - name: request-volume
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >= 20
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: sum(increase(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
    initialDelay: 5m
  - name: http-2xx-success
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >= 0.95
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: |-
          (sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}",response_code=~"2.."}[2m])) or vector(0))
          /
          sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
    initialDelay: 5m
  - name: latency-p95
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] <= 0.5
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: |-
          histogram_quantile(0.95,
            sum by (le) (rate(istio_request_duration_milliseconds_bucket{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
          ) / 1000
    count: 5
    initialDelay: 5m
  - name: http-error-rate
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] <= 0.01
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: |-
          (sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}",response_code=~"5..|0"}[2m])) or vector(0))
          /
          sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
    initialDelay: 5m
```

这两个模板有意使用相同的门限定义，但 Service 参数不同。`initialDelay: 5m` 为两分钟窗口提供时间，使其越过切换阶段；但仍需验证数据新鲜度和实际流量。不要将旧 active 版本的样本当作候选版本的证据。

Prometheus 返回的是 vector，因此条件会先检查长度和有限值，再读取 `result[0]`。分子的 `or vector(0)` 可处理没有 2xx/全部为 5xx，以及没有 5xx/健康的情况；分母和请求量检查则可避免缺失或空闲遥测导致误通过。成功指标只统计 2xx；4xx 会降低成功率，即使它不计入 5xx/零状态错误分子。

`failureLimit: 0` 表示首次测量失败即中止。如果设为 2，则第三次失败会超出限制；允许出现失败的五个样本并不意味着必须有五次成功。每 30 秒采样一次、共五个样本，并不能保证整个阶段恰好持续 2.5 分钟，尤其是存在初始延迟和 provider 错误时。

promotion 前失败会保留旧的 active 目标。promotion 后失败会中止，并根据控制器规则恢复之前的 active 选择，只要旧 ReplicaSet 仍然可用。这并不保证在所有情况下都能即时回滚。应保留足够的旧版本容量，并验证传播、会话、连接排空和数据库兼容性。

```bash
kubectl argo rollouts get rollout test -n rollouts-demo --watch
kubectl get analysisrun -n rollouts-demo
kubectl get service test-active test-preview -n rollouts-demo -o yaml
```

应检查实际 AnalysisRun 条件和 revision 树，而不是复制状态输出或使用不存在的指标名称。Rollout 缩容、端点传播和应用恢复都必须在目标环境中测试。

[Argo Rollouts 指南](../../../service-mesh/istio/advanced/08-argo-rollouts.md)

</details>

### 问题 10：DNS 行为与测量

说明 Istio DNS capture 与 Envoy 上游 DNS 解析的区别，展示有效配置，并设计可复现的性能比较。评估原先未经验证的基准测试数据，但不要将其说成新的测量结果。

<details>
<summary>参考答案</summary>

应用 DNS、Istio DNS capture、CoreDNS/缓存行为以及 Envoy 上游解析彼此不同。新的 HTTP 请求不一定会执行新的 DNS 查询或建立新连接。DNS capture 并不是适用于任意上游响应的通用缓存。

在 sidecar 模式下，istio-agent 会处理捕获到的 DNS 请求；ambient 使用其文档所述的 DNS 路径，并从 Istio 1.25 起默认启用 capture。名称表中已知的网格名称可以直接响应；未知名称则会被转发。Envoy 会独立解析基于 DNS 的上游端点。

使用有效的 ServiceEntry 注册由应用发起的外部 HTTPS 服务：

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-api
  namespace: default
spec:
  hosts:
  - api.github.com
  ports:
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL
  resolution: DNS
```

这不会再发起一层 TLS、创建出口防火墙，也不会让 sidecar 看到加密 HTTP 请求路径。仍然需要适当的网络策略和应用 TLS 验证。

要进行 sidecar capture，请将此 istioctl 输入合并到现有安装值中，并按照常规变更流程滚动受影响的工作负载：

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    defaultConfig:
      proxyMetadata:
        ISTIO_META_DNS_CAPTURE: 'true'
```

不存在 DestinationRule `trafficPolicy.dnsRefreshRate`，而且 `consecutiveErrors` 不是当前的 outlier 字段。Istio 1.31 中生成的 DNS 集群会遵循 DNS TTL；对于相关的 fallback 行为，mesh `dnsRefreshRate` 默认为 60 秒。五分钟设置并不会普遍固定刷新间隔，也不会覆盖正数 TTL。

不要插入臆造的 `envoy.filters.network.dns_cache` filter/type。Dynamic forward proxy 和当前的 DYNAMIC_DNS ServiceEntry 模式是两种独立的受支持设计，各有自身要求，并非通用缓存开关。若确有需要，请使用 DNS 指南中范围明确且经过版本验证的集群定制方案。

要进行有界测试，请使用已知包含 curl 的调用方容器，并使用自有/获准的、DNS/TTL 可控的 HTTPS 测试端点。显式设置 BENCH_URL。该测试采样的是进程级耗时，不是 Envoy 专属 DNS 延迟：

```bash
: "${BENCH_URL:?Set an authorized HTTPS benchmark endpoint}"
for i in $(seq 1 20); do
  curl --silent --show-error --fail --max-time 5 --output /dev/null     --write-out '%{http_code},%{time_namelookup},%{time_connect},%{time_appconnect},%{time_starttransfer},%{time_total}
'     "$BENCH_URL" || break
  sleep 0.2
done
```

记录客户端/image、Istio/Kubernetes 版本、代理模式、TTL/答案变化、DNS 路径、连接复用、并发度、负载、TLS 和预热/冷启动流程。每个新的 curl 进程都会重置其进程本地状态；应单独控制连接复用。不要对公共 GitHub API 进行负载测试，也不要假设 curl 镜像同时包含 ApacheBench。在计算统计数据前，必须明确处理失败样本。

原始韩文文本声称使用 EKS 1.34、Istio 1.28.0、r5.xlarge/us-east-1 和 api.github.com，但没有提供原始样本或可复现的基准测试制品。应保留这一**历史背景**，不要将其重新标注为 Istio 1.31 的结果：

| 原始未验证数据 | 之前 | 之后 | 仅作算术计算 |
|---|---:|---:|---:|
| 平均响应时间 |287 ms|152 ms|降低 47.04%|
| p95 |350 ms|180 ms|降低 48.57%|
| p99 |420 ms|210 ms|降低 50%|
| 吞吐量 |12.34 RPS|23.15 RPS|提高 87.60%|
| 声称的缓存命中率 |0%|99%|未提供有效命中/未命中证据|
| 声称的连接复用率 |0%|95%|未提供有效复用测量|

总响应时间的差异不能全部归因于 DNS。并发数为 10 时，ApacheBench 的 mean time per request 约为 `1000 × 10 / RPS` ms，而其 “across all concurrent requests” 数值为 `1000 / RPS` ms；原来的标签标反了。这些修正并不能证明该基准测试真实有效。

可用于 capture 的指标包括 `istio_agent_dns_requests_total`、`istio_agent_dns_upstream_requests_total`、`istio_agent_dns_upstream_failures_total`，以及实际导出时的上游耗时直方图。上游成功数/(成功数+失败数) 衡量的是查询成功率，而不是缓存命中率。`envoy_cluster_upstream_cx_active` 是 gauge；对它应用 rate() 并不能衡量连接复用。

检查生成的集群 DNS 配置、已验证导出的计数器以及实际 resolver/连接跟踪。除了平均延迟，也要测试 DNS 变更和故障恢复；没有工作负载证据时，不要建议 5–15 分钟刷新间隔或声称固定的性能提升。

[DNS 指南](../../../service-mesh/istio/advanced/04-dns-cache.md)

</details>

## 评分

- 问题 1–5：每题 10 分，共 50 分。答案：**B、A、C、D、B**。
- 问题 6–10：每题 10 分，共 50 分。正确说明工作机制、完整先决条件、有效配置、有意义的验证和诚实的测量限制，均可得分。
- 总分：100 分。测验分数表示对这些问题的理解，不代表具备运维专业能力认证。

## 学习资料

- [Ambient](../../../service-mesh/istio/advanced/01-ambient-mode.md)
- [多集群](../../../service-mesh/istio/advanced/02-multi-cluster.md)
- [EnvoyFilter](../../../service-mesh/istio/advanced/03-envoy-filter.md)
- [DNS](../../../service-mesh/istio/advanced/04-dns-cache.md)
- [gRPC](../../../service-mesh/istio/advanced/05-grpc.md)
- [WebSocket](../../../service-mesh/istio/advanced/06-websocket.md)
- [注入](../../../service-mesh/istio/advanced/07-sidecar-injection.md)
- [Argo Rollouts](../../../service-mesh/istio/advanced/08-argo-rollouts.md)
- [KEDA](../../../service-mesh/istio/advanced/10-keda-autoscaling.md)
