# Linkerd 最佳实践

> **最后更新**：October 16, 2026 · Linkerd edge-26.10.1 / charts 2026.10.1

请参阅[安装](01-installation.md)、[安全](04-security.md)、[可观测性](05-observability.md)和[多集群](06-multi-cluster.md)指南，了解所选版本及其前置条件。本章将这些流程整合为一份运维审查指南；它不会认证某个环境已达到生产就绪状态。

进行任何更改之前，请选择并验证预期的 Kubernetes context、API endpoint 和资源所有者。以下命令使用当前 context 和示例 namespace/workload 名称。本次审计未执行实时升级、回滚、迁移或负载测试。

## 就绪情况审查

- [ ] 验证 Kubernetes/Linkerd/Gateway API 的兼容性，以及所选发行版的发行说明。
- [ ] 确认实际副本数、部署位置、容量、中断行为和准入策略。
- [ ] 区分根证书、签发者证书和工作负载证书的有效期；验证其续期和恢复流程。
- [ ] 测试所需的身份验证/授权行为，包括被拒绝的调用方和未加入网格的路径。
- [ ] 确认指标、日志、追踪要求、告警送达情况和缺失数据检测。
- [ ] 记录资源所有权、受保护的备份、特定版本的升级/恢复步骤和运维责任。

预期建立链接关系的网格之间需要共享信任，但无关集群之间并非如此。ServiceProfiles 并非通用的就绪要求：当前的 Gateway API 策略和兼容性配置文件各有不同的用途和优先级。

```bash
linkerd version
linkerd check
linkerd check --proxy
kubectl -n linkerd get deployments,pods,poddisruptionbudgets
kubectl -n my-app get pods -o wide
```

保留完整的检查输出及其退出状态。使用 grep 搜索“valid”可能会匹配到“invalid”，并且可能因为 grep 成功退出而掩盖命令失败：

```bash
#!/usr/bin/env bash
set -euo pipefail
umask 077
if linkerd check --proxy > linkerd-check.log 2>&1; then
  cat linkerd-check.log
else
  check_status=$?
  cat linkerd-check.log >&2
  exit "$check_status"
fi
```

即使命令成功退出，也要检查警告。控制平面检查正常并不能证明应用程序符合 SLO，也不能证明具备区域故障转移能力。

## 资源分配

根据测得的工作负载行为确定资源配置：请求/连接并发数、协议、负载/流大小、服务发现规模、遥测基数、内存压力和 CPU 限流情况。仅凭 RPS 无法确定代理资源需求。

这是一个**示例起始配置**，并非容量保证：

```yaml
proxy:
  resources:
    cpu:
      request: 100m
      limit: 1000m
    memory:
      request: 64Mi
      limit: 250Mi
```

使用一份连贯的 YAML 映射。在同一映射中重复出现三次 `proxy:` 是无效的；宽松的加载器可能会悄悄只保留最后一个配置文件。

对于现有工作负载，请将此**合并补丁**保存为 `proxy-resources-patch.yaml`：

```yaml
spec:
  template:
    metadata:
      annotations:
        config.linkerd.io/proxy-cpu-request: 500m
        config.linkerd.io/proxy-cpu-limit: 2000m
        config.linkerd.io/proxy-memory-request: 128Mi
        config.linkerd.io/proxy-memory-limit: 500Mi
```

```bash
# A merge patch for one existing, reviewed workload; this starts a rollout.
kubectl -n my-app patch deployment/api --type merge --patch-file proxy-resources-patch.yaml
kubectl -n my-app rollout status deployment/api --timeout=5m
kubectl -n my-app top pod --containers
```

`kubectl top pod --containers` 会请求每个容器的数据；该命令没有 `-c linkerd-proxy` 过滤选项。确认指标管道按预期报告原生 init sidecar。应结合 Pod 的 spec/status 和资源指标进行判断，而不是根据单个视图推断某项资源缺失。

### 运行时 worker 与 CPU 配额

CPU requests/limits 用于配置调度和 CPU 分配。将 limit 设为 4 并不会直接请求四个代理 worker 线程。所选 chart 另有独立的运行时 worker 数量范围：

```yaml
proxy:
  runtime:
    workers:
      minimum: 1
      maximum: 4
      maximumCPURatio: 1
```

这是独立的 values 片段；合并其嵌套字段，而不是重复顶层 YAML 键。已发布的 chart 会单独生成 worker 最小值/最大值/CPU 比率设置，与 Kubernetes CPU limits 分开。运行时行为还取决于可用 CPU 和需求；仅提高上限并不能提升性能。模板中较早的固定 `proxy.cores` 配置已弃用。

## 高可用性

### 核心控制平面

从**同一 chart 发行版中的 HA 配置文件**开始，并将其与安装时经过审查的 values（包括证书配置）叠加：

```bash
set -euo pipefail
umask 077
# Use the same reviewed chart version for the profile and render.
curl --fail --show-error --location \
  https://raw.githubusercontent.com/linkerd/linkerd2/edge-26.10.1/charts/linkerd-control-plane/values-ha.yaml \
  -o values-ha.yaml
helm template linkerd-control-plane linkerd-edge/linkerd-control-plane \
  --version 2026.10.1 -n linkerd \
  -f reviewed-core-values.yaml -f values-ha.yaml > reviewed-ha.yaml
```

打包的配置文件会设置三个 controller 副本、三个控制平面 PDB、各组件的必需节点反亲和性、优先级较低的区域分散策略，以及失败时关闭的注入行为。它还提供资源和滚动更新设置。请确认渲染出的 Deployment/PDB/webhook 对象以及实际符合条件的节点。Values 文件按顺序合并，因此 HA 配置文件可能覆盖较早的资源设置；请检查最终结果，并在叠加额外覆盖项时保留必要的 HA 控制。

先前的嵌套 `destination.replicas/resources`、`identity.replicas/resources` 和 `proxyInjector.replicas/resources` 示例会被此 chart 忽略。受支持的 controller 资源值包括 `destinationResources`、`identityResources`、`proxyInjectorResources` 以及打包配置文件中的其他字段。任意 `podAntiAffinity`、`topologySpreadConstraints` 或 `podDisruptionBudget` 键都不会自动转换成 Pod 字段。

三个副本并不保证构成法定人数。如果符合条件的节点过少，必需的放置规则可能导致副本处于 Pending 状态；优先级较低的区域规则无法保证每个区域都有一个副本。PDB 只约束受支持的自愿驱逐，不涵盖所有故障或所有由 controller 驱动的滚动更新。

### Viz 和指标可用性

对于已单独准备、具有预期保留策略、身份验证和 HA 行为的 Prometheus/query endpoint，可以使用以下 values 扩展无状态 Viz 组件：

```yaml
prometheus:
  enabled: false
prometheusUrl: http://prometheus.monitoring.svc.cluster.local:9090
tap:
  replicas: 2
metricsAPI:
  replicas: 2
tapInjector:
  replicas: 2
dashboard:
  replicas: 2
```

仅设置副本数并不能确保故障域分离、中断保护或指标可用性。请验证实际放置情况和外部查询架构，包括是否需要对副本进行去重。

或者，**单个本地 Prometheus** 可以持久化其数据：

```yaml
prometheus:
  enabled: true
  persistence:
    accessMode: ReadWriteOnce
    size: 50Gi
```

这需要可用的默认 StorageClass，或者正确设置 chart 的显式存储类选项。所选 Viz chart 将 Prometheus 保持为单个副本，并在其 PVC 上使用 Recreate 策略。旧的 `prometheus.replicas:2` 会被忽略；未设置 accessMode 的 `persistence.enabled:true` 会生成无效 PVC。持久化有助于数据在重启后保留，但并不等于 Prometheus HA。

## 升级和恢复

### 更改版本之前先选定升级路径

公开发布的 Linkerd 构件使用 edge 跟踪通道；供应商的稳定发行版可能有不同的受支持升级说明。公开安装程序并非通用的稳定版本/降级安装程序。请按照安装指南获取并验证所选 CLI。

Edge 版本号并不保证符合语义化版本兼容规则。请查看特定版本的变更和控制平面/数据平面允许的版本偏差；必要时使用中间版本。`check --pre` 是安装前检查，并非对现有网格进行升级资格测试。

通过相应所有者备份预期的 values 和所需凭据，保护已存储的密钥材料，并测试恢复流程。`helm get values` 可能会暴露签发者材料；请勿发布其输出。准备经过审查的目标 values，而不要将旧的计算后默认值盲目应用到新 chart。

### 由 CLI 管理的安装

批准受支持的路径并保留当前配置/凭据后：

```bash
set -euo pipefail
# The selected, verified target CLI must already be on PATH.
linkerd version --client
linkerd check
linkerd check --proxy
linkerd upgrade --crds | kubectl apply -f -
linkerd upgrade | kubectl apply -f -
linkerd check
# CLI-owned Viz only; preserve its complete reviewed configuration.
linkerd viz install -f reviewed-viz-values.yaml | kubectl apply -f -
linkerd viz check
```

先升级 CRD，再升级核心，然后升级兼容的扩展，最后升级工作负载代理。当前的扩展 CLI 使用 `install` 并指定完整配置；`linkerd viz upgrade` 并不存在。请查看特定版本的资源清理/迁移说明，并在删除任何内容之前检查可能过时的资源。

对于多集群部署，请保留多集群指南中预期的 Helm `controllers` 列表以及当前 Link/凭据所有权。不要将重新创建已弃用的旧式 link 管理 controller 作为自动升级步骤。

### 由 Helm 管理的安装

以下示例目标版本为 2026.10.1；只有在验证了从实际已安装版本升级的路径后才能使用：

```bash
set -euo pipefail
umask 077
helm get values linkerd-control-plane -n linkerd > current-core-values.yaml
helm get values linkerd-viz -n linkerd-viz > current-viz-values.yaml
# Prepare reviewed target values and approved migration steps before these changes.
helm upgrade linkerd-crds linkerd-edge/linkerd-crds \
  --version 2026.10.1 -n linkerd --wait --timeout 10m
helm upgrade linkerd-control-plane linkerd-edge/linkerd-control-plane \
  --version 2026.10.1 -n linkerd -f reviewed-core-values.yaml \
  --wait --timeout 10m
linkerd check
helm upgrade linkerd-viz linkerd-edge/linkerd-viz \
  --version 2026.10.1 -n linkerd-viz -f reviewed-viz-values.yaml \
  --wait --timeout 10m
linkerd viz check
```

CRD、核心、CNI 和扩展应由既定的所有者管理。不要仅仅因为清单看起来相似，就将 CLI apply 工作流混入由 Helm 管理的发行版。

### 工作负载滚动更新

选择实际加入网格的工作负载 controller，包括相关的 StatefulSet/DaemonSet/job，并协调其特定于应用程序的滚动更新行为。针对整个 namespace 的循环会重启无关工作负载，而固定等待 30 秒并不能测试系统是否稳定。

```bash
# One explicitly selected meshed Deployment, after checking disruption/capacity.
kubectl -n my-app rollout restart deployment/api
kubectl -n my-app rollout status deployment/api --timeout=5m
linkerd check --proxy -n my-app
linkerd viz stat deployment/api -n my-app
```

在继续处理其他工作负载之前，请验证就绪状态、身份/策略和有代表性的应用程序流量。Namespace 注解会影响新建的 Pod；它们不会原地更新正在运行的 sidecar。

### 恢复和多个控制平面

针对特定版本和 CRD 制定并测试恢复计划。仅回滚核心 Helm 发行版并不会同时恢复单独管理的 CRD、所有凭据变更或已运行的工作负载代理。下载任意旧版 CLI 并运行 upgrade 并非通用的降级流程。

之前的“蓝绿”示例安装了第二个 namespace 并更改 `proxy-version`。该注解选择的是代理镜像，而非控制平面。两个 namespace 的默认 chart 渲染结果还会共享集群范围的名称，包括准入 webhook。因此，第二个 namespace 并不能实现隔离共存或安全的工作负载迁移。应采用发行版支持的设计，明确资源所有权和流量/身份选择，并在验证之前保留恢复能力。


## 加入网格和协议处理

为新建的 Pod 配置 namespace 加入网格：

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: my-app
  annotations:
    linkerd.io/inject: enabled
```

对现有工作负载选择退出时，应使用 Pod 模板合并补丁，而不是完整的 Deployment：

```yaml
spec:
  template:
    metadata:
      annotations:
        linkerd.io/inject: disabled
```

仅更改注解不会移除正在运行或手动嵌入的代理。请协调工作负载的实际清单，并在适当时通过其所有者重新创建工作负载。检查 `containers` 和 `initContainers`；不能仅仅因为常规容器列表中没有显示原生 sidecar 就认为它不存在。

不透明端口会跳过 HTTP 协议检测，同时保留相关的 TCP 代理路径、mTLS 和策略。对于已准备好的 MySQL 工作负载，请使用 Pod 模板补丁和一致的 Service 注解：

```yaml
spec:
  template:
    metadata:
      annotations:
        config.linkerd.io/opaque-ports: '3306'
---
apiVersion: v1
kind: Service
metadata:
  name: mysql
  namespace: my-app
  annotations:
    config.linkerd.io/opaque-ports: '3306'
spec:
  selector:
    app: mysql
  ports:
  - name: mysql
    port: 3306
    targetPort: 3306
```

Pod 和 Service 的端口映射必须一致。所选 Server 的 `proxyProtocol` 也会影响协议处理。不透明模式不会为该流提供 HTTP 路由指标。

相比之下，skip-inbound/outbound-ports 会绕过代理路径，并可能移除网格加密、策略和遥测。不要将跳过 Redis、Memcached 或数据库端口作为通用延迟优化建议。

ServiceProfile 路由超时是截止时间，并非连接池配置。同样，协议处理也不能保证每个应用程序的 HTTP/1 连接端到端都变成 HTTP/2。调整配置之前，请测量实际的连接复用、缓冲和协议行为。

## 证书运维

将公共根证书、签发者凭据、代理叶证书和 webhook 证书视为各自独立生命周期的对象，并为每项指定所有者。默认的短有效期代理叶证书无法满足通用的“剩余有效期至少 60 天”检查清单。请根据配置的有效期和续期提前量选择阈值。

请使用安全指南中经过验证的凭据检查、签发者重载/事件以及 cert-manager 所有权示例。仅设置 `isCA:true` 并不会安装 Issuer、分发信任根、轮换所有使用方或配置告警送达。

之前的证书 CronJob 使用了未经验证的旧 CLI 镜像，缺少所需的 RBAC，并通过 grep 隐藏了检查失败。定时检查需要受支持的运行环境、范围受限的凭据、明确的失败处理和经过测试的通知送达路径。上面的检查/日志示例会保留退出状态；安全指南提供了基于指标的告警。若未集成相应机制，两者都不能算是完整的通知服务。

## 根据证据进行故障排查

对于注入问题，请检查 namespace 和实际的 Pod 模板/Pod 元数据、两种容器类型、webhook 配置以及 injector 日志：

```bash
kubectl get namespace my-app -o yaml
kubectl -n my-app get deployment api -o yaml
# Set this to an actual API Pod.
api_pod=api-example-pod
kubectl -n my-app get pod "$api_pod" -o json | jq '{
  annotations: .metadata.annotations,
  containers: [.spec.containers[]? | {name,image,resources}],
  initContainers: [.spec.initContainers[]? | {name,image,restartPolicy,resources}],
  status: .status
}'
kubectl get mutatingwebhookconfiguration linkerd-proxy-injector-webhook-config
kubectl -n linkerd logs deployment/linkerd-proxy-injector -c proxy-injector --tail=100
```

对于延迟或不稳定问题，请比较应用程序行为、资源压力、处于 Pending 状态的 Pod、端点、DNS、协议检测以及证书/策略错误。提高超时或重启整个控制平面并不能构成诊断。

```bash
linkerd check
linkerd check --proxy
linkerd viz stat deploy -n my-app
linkerd viz tap deployment/api -n my-app --max-rps 20
linkerd viz edges deploy -n my-app
linkerd identity -n my-app -l app=api
kubectl -n my-app top pod --containers
kubectl -n my-app logs deployment/api -c linkerd-proxy --tail=100
kubectl -n linkerd logs deployment/linkerd-destination -c destination --tail=100
kubectl -n linkerd logs deployment/linkerd-identity -c identity --tail=100
kubectl -n linkerd get events --sort-by=.lastTimestamp
```

`linkerd identity` 会检索公共叶证书；不要假设代理镜像中一定存在固定的 `end-entity.crt` 文件。只有对实际配置的资源，才使用 ServiceProfile `viz routes` 或当前策略诊断工具。读取日志时，请明确指定相关 controller 容器。

实施有针对性的修复后，应验证原先失败的路径，而不只是确认命令成功完成。

## 从 Istio 迁移

在设计迁移方案之前，先清点每个工作负载使用的功能和安全属性。以下是**部分功能比较**，并非可机械执行的清单转换：

| Istio 概念 | Linkerd 方面的考虑 |
|---|---|
| VirtualService | 受支持的 Gateway API 路由功能；ServiceProfile 是兼容接口，并非完整等价实现 |
| DestinationRule | 分别重新评估负载均衡、故障累积、连接行为和 TLS 要求 |
| PeerAuthentication STRICT | 仅有自动 mTLS 并不足够，因为默认的 Linkerd 策略可能接受未加入网格的明文流量；必须要求适当的授权 |
| AuthorizationPolicy | Linkerd 的目标/身份验证模型不同；JWT/用户声明和其他条件需要单独设计 |
| Sidecar 流量范围 | 不存在与注入注解或网络防火墙完全等价的通用机制 |
| Gateway | 选择并配置合适的入口/网关实现及其与 Linkerd 的集成 |

经典注入标签、revision 标签/标记、Pod 注解、手动注入的清单和 ambient 加入网格是不同的机制。仅移除 `istio-injection` 并不能涵盖所有这些机制。在更改工作负载之前，请检查实际的 Istio/Linkerd CNI 和代理加入网格情况。

不要假设 Istio 和 Linkerd 网格的 mTLS 会自动互通。混合迁移阶段需要明确的流量/安全边界，并验证应用程序行为；避免意外地让同一个工作负载同时进入两种流量拦截路径。如果依赖关系跨越 namespace 边界，仅以 namespace 为单位迁移并不安全。

一种实用的审查顺序是：清点依赖关系/策略，在隔离环境中复现，测试允许和拒绝的流量以及恢复流程，然后迁移经过审慎选择的一组工作负载。协调正确的加入网格控制项，验证实际启用的代理路径恰好符合预期，并在扩大迁移范围之前测量有代表性的流量。只有在不再有必需的使用方且所选恢复计划可行之后，才移除旧的控制平面/资源。

本文取代了无条件的 namespace 标签/重启/卸载操作步骤，以及图中错误的一对一功能映射。应用程序兼容性和生产环境迁移仍需结合具体环境进行验证。

## 参考资料

- [所选 HA 配置文件](https://github.com/linkerd/linkerd2/blob/edge-26.10.1/charts/linkerd-control-plane/values-ha.yaml)
- [代理配置](https://linkerd.io/docs/reference/proxy-configuration/)
- [已发布的代理运行时模板](https://github.com/linkerd/linkerd2/blob/edge-26.10.1/charts/partials/templates/_proxy.tpl)
- [升级指南](https://linkerd.io/docs/tasks/upgrade/)
- [授权策略](https://linkerd.io/docs/reference/authorization-policy/)
- [Istio 注入](../istio/advanced/07-sidecar-injection.md)和[ambient 模式](../istio/advanced/01-ambient-mode.md)
