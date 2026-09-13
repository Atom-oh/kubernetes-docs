# Linkerd 最佳实践

> **最后更新**：2026 年 9 月 11 日 · Linkerd edge-26.9.1 / chart 2026.9.1

所选版本和前提条件参阅[安装](01-installation.md)、[安全](04-security.md)、[可观测性](05-observability.md)和[多集群](06-multi-cluster.md)指南。本章将这些流程结合为运维审查；不认证环境已生产就绪。

任何更改前选择并验证目标 Kubernetes 上下文、API 端点和资源所有者。以下命令使用当前上下文及示例命名空间/工作负载名。本审计未执行实际升级、回滚、迁移或负载测试。

## 就绪审查

- [ ] 验证 Kubernetes/Linkerd/Gateway API 兼容性及所选发行版发布说明。
- [ ] 确认实际副本、放置、容量、中断行为和准入策略。
- [ ] 区分根、签发者和工作负载证书寿命；验证续订和恢复流程。
- [ ] 测试所需身份/授权行为，包括被拒绝调用方和非网格路径。
- [ ] 确认指标、日志、追踪要求、警报交付及缺失数据检测。
- [ ] 记录资源所有权、受保护备份、版本专属升级/恢复步骤和运维责任。

共享信任用于目标关联网格关系，不是每个无关集群都需要。ServiceProfile 不是通用就绪要求：当前 Gateway API 策略和兼容配置文件有不同作用和优先级。

```bash
linkerd version
linkerd check
linkerd check --proxy
kubectl -n linkerd get deployments,pods,poddisruptionbudgets
kubectl -n my-app get pods -o wide
```

保留完整检查输出及退出状态。grep “valid” 可匹配“invalid”，也可能以 grep 成功退出隐藏命令失败：

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

即使命令成功退出也要审核警告。控制平面检查健康不确立应用 SLO 或区域故障转移行为。

## 资源分配

根据实测工作负载行为规划：请求/连接并发、协议、载荷/流大小、发现规模、遥测基数、内存压力和 CPU 节流。仅 RPS 不决定代理资源。

这是**示意起始配置**，不是容量保证：

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

使用一个一致 YAML 映射。同一映射重复 `proxy:` 三次无效；宽松加载器可能默默只保留最后配置。

对于现有工作负载，将此**合并补丁**保存为 `proxy-resources-patch.yaml`：

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

`kubectl top pod --containers` 请求每容器数据；该命令没有 `-c linkerd-proxy` 过滤器。确认指标管道按预期报告原生初始化 Sidecar。结合 Pod spec/status 和资源指标，不要从单一视图推断缺失。

### 运行时工作线程与 CPU 配额

CPU requests/limits 配置调度和 CPU 分配。limit 为 4 不直接请求四个代理工作线程。所选 chart 有独立运行时工作线程上下界：

```yaml
proxy:
  runtime:
    workers:
      minimum: 1
      maximum: 4
      maximumCPURatio: 1
```

这是独立 values 摘录；合并嵌套字段，不重复顶层 YAML 键。发布 chart 将工作线程最小/最大/CPU 比率设置与 Kubernetes CPU limits 分开输出。运行时行为还取决于可用 CPU 和需求；仅提高上界不是性能提升。旧固定 `proxy.cores` 配置在模板中已弃用。

## 高可用

### 核心控制平面

从**同一 chart 版本的 HA 配置档**开始，与安装已审核 values 叠加，包括证书配置：

```bash
set -euo pipefail
umask 077
# Use the same reviewed chart version for the profile and render.
curl --fail --show-error --location \
  https://raw.githubusercontent.com/linkerd/linkerd2/edge-26.9.1/charts/linkerd-control-plane/values-ha.yaml \
  -o values-ha.yaml
helm template linkerd-control-plane linkerd-edge/linkerd-control-plane \
  --version 2026.9.1 -n linkerd \
  -f reviewed-core-values.yaml -f values-ha.yaml > reviewed-ha.yaml
```

打包配置档配置三个控制器副本、三个控制平面 PDB、各组件必需节点反亲和性、优先可用区分离及失败时拒绝的注入。它还提供资源和发布设置。确认渲染的 Deployment/PDB/webhook 对象及实际合格节点。Values 文件按顺序合并，因此 HA 配置档可覆盖更早资源设置；检查最终结果，叠加额外覆盖时保留关键 HA 控制。

此前嵌套 `destination.replicas/resources`、`identity.replicas/resources` 和 `proxyInjector.replicas/resources` 示例被此 chart 忽略。受支持控制器资源值包括 `destinationResources`、`identityResources`、`proxyInjectorResources` 及打包配置档其他字段。任意 `podAntiAffinity`、`topologySpreadConstraints` 或 `podDisruptionBudget` 键不会自动转换为 Pod 字段。

三个副本不是法定人数保证。适当节点过少时，必需放置可使副本 Pending；优先可用区规则不保证每区一个副本。PDB 约束受支持自愿驱逐，不约束每次故障或每种控制器驱动发布。

### Viz 和指标可用性

对于单独准备、具有预期保留、身份验证和高可用行为的 Prometheus/查询端点，这些 values 扩缩无状态 Viz 组件：

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

仅副本数不确立故障域分离、中断保护或指标可用性。验证实际放置和外部查询架构，包括副本去重。

另一方案是让**单个本地 Prometheus** 持久化数据：

```yaml
prometheus:
  enabled: true
  persistence:
    accessMode: ReadWriteOnce
    size: 50Gi
```

需要正常默认 StorageClass，或适当显式 chart 存储类设置。所选 Viz chart 将 Prometheus 保持单副本，带 PVC 时使用 Recreate。旧 `prometheus.replicas:2` 被忽略，没有 accessMode 的 `persistence.enabled:true` 产生无效 PVC。持久化帮助数据经重启保留；不是 Prometheus 高可用。

## 升级和恢复

### 更改版本前选择路径

公共 Linkerd 制品使用 edge 分支；厂商稳定发行版可能有不同受支持升级说明。公共安装器不是通用稳定版本/降级安装器。按安装指南获取并验证所选 CLI。

Edge 版本号不是语义版本兼容性保证。审核特定发布更改及允许的控制/数据平面偏差，按需使用中间版本。`check --pre` 是安装前检查，不是现有网格升级资格测试。

通过所有者备份期望 values 和必要凭证，保护存储密钥材料并测试恢复。`helm get values` 可能暴露签发者材料；不要发布输出。准备已审核目标 values，不要盲目将旧计算默认值应用到新 chart。

### CLI 管理安装

批准受支持路径并保留当前配置/凭证后：

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

先升级 CRD，再核心、兼容扩展，最后工作负载代理。当前扩展 CLI 使用带完整配置的 `install`；不存在 `linkerd viz upgrade`。审核特定版本清理/迁移说明，删除前检查陈旧资源候选。

多集群保留多集群指南中的期望 Helm `controllers` 列表及当前 Link/凭证所有权。不要将重建已弃用旧 link 管理控制器作为自动升级步骤。

### Helm 管理安装

下方示例目标为 2026.9.1；只有验证实际安装版本到该目标的路径后才可用：

```bash
set -euo pipefail
umask 077
helm get values linkerd-control-plane -n linkerd > current-core-values.yaml
helm get values linkerd-viz -n linkerd-viz > current-viz-values.yaml
# Prepare reviewed target values and approved migration steps before these changes.
helm upgrade linkerd-crds linkerd-edge/linkerd-crds \
  --version 2026.9.1 -n linkerd --wait --timeout 10m
helm upgrade linkerd-control-plane linkerd-edge/linkerd-control-plane \
  --version 2026.9.1 -n linkerd -f reviewed-core-values.yaml \
  --wait --timeout 10m
linkerd check
helm upgrade linkerd-viz linkerd-edge/linkerd-viz \
  --version 2026.9.1 -n linkerd-viz -f reviewed-viz-values.yaml \
  --wait --timeout 10m
linkerd viz check
```

保持 CRD、核心、CNI 和扩展由既定所有者管理。不要仅因清单相似就在 Helm 管理发布中混入 CLI apply 流程。

### 工作负载发布

选择实际网格工作负载控制器，包括相关 StatefulSet/DaemonSet/Job，并协调应用专属发布行为。命名空间范围循环会重启无关工作负载，固定 30 秒休眠不是稳定性测试。

```bash
# One explicitly selected meshed Deployment, after checking disruption/capacity.
kubectl -n my-app rollout restart deployment/api
kubectl -n my-app rollout status deployment/api --timeout=5m
linkerd check --proxy -n my-app
linkerd viz stat deployment/api -n my-app
```

继续下一个工作负载前，验证就绪、身份/策略和代表性应用流量。命名空间注解影响新 Pod，不原地更新运行中的 Sidecar。

### 恢复和多个控制平面

为特定版本和 CRD 定义经过测试的恢复计划。仅回滚核心 Helm 发布不会同时还原独立管理 CRD、全部凭证更改或已运行工作负载代理。下载任意旧 CLI 并运行 upgrade 不是通用降级流程。

旧“蓝绿”示例安装第二命名空间并更改 `proxy-version`。该注解选择代理镜像，不选择控制平面。两命名空间默认 chart 渲染还共享集群作用域名称，包括准入 webhook。因此第二命名空间不建立隔离共存或安全工作负载迁移。使用发行版支持的设计，明确资源所有权和流量/身份选择，并保留恢复能力直到验证。


## 纳管和协议处理

新 Pod 的命名空间纳管：

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: my-app
  annotations:
    linkerd.io/inject: enabled
```

现有工作负载退出纳管应使用 Pod 模板合并补丁，不是完整 Deployment：

```yaml
spec:
  template:
    metadata:
      annotations:
        linkerd.io/inject: disabled
```

仅改变注解不移除运行中或手动嵌入的代理。协调实际工作负载清单，适当时通过所有者重建。同时检查 `containers` 和 `initContainers`；普通容器列表不显示原生 Sidecar，不代表它缺失。

不透明端口跳过 HTTP 协议检测，同时保留相关 TCP 代理路径、mTLS 和策略。准备好的 MySQL 工作负载使用 Pod 模板补丁及一致 Service 注解：

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

Pod 和 Service 端口映射必须一致。所选 Server 的 `proxyProtocol` 也影响协议处理。不透明模式不为该流提供 HTTP 路由指标。

相反，skip-inbound/outbound-ports 绕过代理路径，可移除网格加密、策略和遥测。不要将跳过 Redis、Memcached 或数据库端口作为通用延迟优化。

ServiceProfile 路由超时是期限，不是连接池配置。同样，协议处理不保证每个应用 HTTP/1 连接都端到端变为 HTTP/2。调优前测量实际连接复用、缓冲和协议行为。

## 证书运维

将公有根、签发者凭证、代理叶证书和 webhook 证书视为各有所有者的独立生命周期。默认短期代理叶证书不能满足通用“剩余 60 天”的检查项。阈值应依据配置寿命和提前续订时间选择。

使用安全指南中已验证的凭证检查、签发者重载/事件及 cert-manager 所有权示例。仅设置 `isCA:true` 不安装 Issuer、不分发信任根、不轮换每个使用方，也不配置警报交付。

旧证书 CronJob 使用未经验证的旧 CLI 镜像、缺少必需 RBAC，并用 grep 隐藏检查失败。定时检查需要受支持运行时、限定凭证、显式失败处理和已测试交付路径。上方检查/日志示例保留退出状态；安全指南提供基于指标警报。没有相应集成，两者都不是完整通知服务。

## 基于证据排障

注入问题检查命名空间、实际 Pod 模板/Pod 元数据、两类容器、webhook 配置和注入器日志：

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

延迟或不稳定问题应比较应用行为、资源压力、Pending Pod、端点、DNS、协议检测和证书/策略错误。提高超时或重启整个控制平面不是诊断。

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

`linkerd identity` 获取公有叶证书；不要假定代理镜像中存在固定 `end-entity.crt` 文件。仅对实际配置资源使用 ServiceProfile `viz routes` 或当前策略诊断。读取日志时明确相关控制器容器。

针对性修复后验证原始失败路径，不只看命令成功完成。

## 从 Istio 迁移

设计转换前清点各工作负载使用的功能和安全属性。这些是**部分能力比较**，不是机械清单转换：

| Istio 概念 | Linkerd 注意事项 |
|---|---|
| VirtualService | 受支持 Gateway API 路由功能；ServiceProfile 是兼容接口，不是完整等价物 |
| DestinationRule | 分别重新评估负载均衡、故障累积、连接行为和 TLS 要求 |
| PeerAuthentication STRICT | 仅自动 mTLS 不够，因为默认 Linkerd 策略可接受非网格明文；需要适当授权 |
| AuthorizationPolicy | 不同 Linkerd 目标/身份验证模型；JWT/用户声明和其他条件需独立设计 |
| Sidecar 流量范围 | 不全面等同于注入注解或网络防火墙 |
| Gateway | 选择并配置适当入口/网关实现及 Linkerd 集成 |

经典注入标签、修订标签、Pod 注解、手动注入清单和 Ambient 纳管是不同机制。仅移除 `istio-injection` 无法覆盖全部。更改工作负载前检查实际 Istio/Linkerd CNI 和代理纳管。

不要假定 Istio 与 Linkerd 网格 mTLS 自动互通。混合迁移阶段需要明确流量/安全边界和已验证应用行为；避免将同一工作负载意外纳入两条拦截路径。依赖跨边界时，命名空间本身不是安全迁移单位。

实际审查顺序可为：清点依赖/策略，在隔离环境复现，测试允许/拒绝流量及恢复，再迁移有意选定工作负载组。协调正确纳管控制，验证恰好经过预期代理路径，扩大转换前测量代表性流量。仅在无必需使用方且所选恢复计划可行后移除旧控制平面/资源。

这替代无条件命名空间标签/重启/卸载方案及图中错误的一对一功能映射。应用兼容性和生产迁移仍是需要验证的环境专属工作。

## 参考资料

- [所选高可用配置档](https://github.com/linkerd/linkerd2/blob/edge-26.9.1/charts/linkerd-control-plane/values-ha.yaml)
- [代理配置](https://linkerd.io/docs/reference/proxy-configuration/)
- [发布的代理运行时模板](https://github.com/linkerd/linkerd2/blob/edge-26.9.1/charts/partials/templates/_proxy.tpl)
- [升级指南](https://linkerd.io/docs/tasks/upgrade/)
- [授权策略](https://linkerd.io/docs/reference/authorization-policy/)
- [Istio 注入](../istio/advanced/07-sidecar-injection.md)和 [Ambient 模式](../istio/advanced/01-ambient-mode.md)
