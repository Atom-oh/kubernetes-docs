# Kube Resource Orchestrator (kro)

> **最后更新**：2026年9月12日 · **基准版本**：kro 0.9.4

## 概念与范围

官方名称为 Kube Resource Orchestrator，它是 Kubernetes SIG Cloud Provider 的一个子项目。ResourceGraphDefinition (RGD) 定义 Kubernetes 资源之间的输入模式、关系和状态。经过验证和编译后，kro 会动态协调生成的 CRD 实例。

RGD 定义的是 API 和资源图，而不是应用实例。实例的 spec 提供输入，spec.resources 模板则创建 Deployment 和 Service 等对象。现有 CRD（例如 ACK 资源）可以参与其中，但 kro 不提供这些资源的控制器或 AWS IAM 权限。

YAML 中的 `${...}` 表达式使用 CEL。旧版的 .parent、.children、childResources、resourceKind、statusMappings 和 Go 模板示例并不属于此 API。不要独立创建相同的应用 CRD，以免与 RGD 争夺所有权。

## 与 Helm、Kustomize 和 Operator 的比较

| 工具 | 主要作用和边界 |
| --- | --- |
| Helm | 渲染 Go 模板 chart 并管理发布历史。v2 chart 的依赖项在 Chart.yaml 中声明。 |
| Kustomize | 使用 bases 和 patches 转换清单；它不是运行时控制器。 |
| 自定义 operator | 可以在代码中实现特定领域的恢复、迁移和备份。 |
| kro | 根据 CEL 引用推断资源图并协调实例；它不会生成数据库恢复算法。 |

Helm chart 可以安装 kro，同时由 GitOps 管理 RGD 和实例。这些工具可以协同工作。从 Helm 迁移到 kro 不会自动改善安全性、恢复能力或运维。Kubernetes Deployment 控制器也会继续管理最初由 Helm 创建的 Deployment。

## 安装和权限

官方仓库是 kubernetes-sigs/kro；较早的 kro-run 路径可能会重定向。这是对固定 OCI chart 的**离线检查**。不要使用旧版 kro-project 下载 URL 或杜撰的 CLI 安装方法。此版本不单独分发 CLI 二进制文件；请使用 kubectl 和 Helm。

```bash
helm template kro oci://registry.k8s.io/kro/charts/kro \
  --version 0.9.4 --namespace kro-system \
  --set rbac.mode=aggregation --include-crds
```

安装前，请检查受支持的 Kubernetes 版本、准入策略、命名空间以及现有 CRD/控制器。旧版的 1.31–1.33 列表不代表当前支持版本。Helm upgrade 不会自动更新 crds/；请通过单独流程审查 0.9.4 版本发布内容和 CRD 变更。

默认的 rbac.mode=unrestricted 会授予广泛的集群访问权限。此示例渲染的是 aggregation 模式，其中仍包含针对 CRD、RGD、GraphRevision 和 ConfigMap 的基础权限。请为生成的应用 API 和子资源添加权限。此 ClusterRole 允许访问示例中的资源类型，并可能授予整个集群范围的访问权限。应由可信的平台管理员控制 RGD 和聚合标签。

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: kro:controller:reviewed-nginxapps
  labels:
    rbac.kro.run/aggregate-to-controller: "true"
rules:
  - apiGroups: [platform.example.com]
    resources: [nginxapps]
    verbs: [get, list, watch, create, update, patch, delete]
  - apiGroups: [platform.example.com]
    resources: [nginxapps/status, nginxapps/finalizers]
    verbs: [get, update, patch]
  - apiGroups: [apps]
    resources: [deployments]
    verbs: [get, list, watch, create, update, patch, delete]
  - apiGroups: [""]
    resources: [services]
    verbs: [get, list, watch, create, update, patch, delete]
  - apiGroups: [networking.k8s.io]
    resources: [ingresses]
    verbs: [get, list, watch, create, update, patch, delete]
```

## 完整的 NginxApp 示例

RGD、实例和 RBAC 文件也位于 examples/platform/kro 中。Ingress 默认禁用。启用前，请准备经过批准的 IngressClass/控制器、主机 DNS，以及位于同一命名空间中的 TLS Secret。字符串 className=internal 本身并不会配置内部负载均衡器。

该镜像使用与 Helm 示例相同的 nginx-unprivileged 标签。配置了非 root UID、只读根文件系统和 /tmp 卷，但未测试镜像运行情况。部署前请验证摘要、架构和策略。

### ResourceGraphDefinition

```yaml
apiVersion: kro.run/v1alpha1
kind: ResourceGraphDefinition
metadata:
  name: reviewed-nginxapps
spec:
  schema:
    apiVersion: v1alpha1
    group: platform.example.com
    kind: NginxApp
    scope: Namespaced
    spec:
      replicas: integer | default=2 minimum=1 maximum=5
      image: string | default="nginxinc/nginx-unprivileged:1.30.6-alpine"
      ingress:
        enabled: boolean | default=false
        className: string | default="internal"
        host: string | default="app.example.com"
        tlsSecret: string | default="app-tls"
    status:
      availableReplicas: ${deployment.status.availableReplicas}
      serviceIP: ${service.spec.clusterIP}
  resources:
    - id: deployment
      readyWhen:
        - ${deployment.status.availableReplicas >= deployment.spec.replicas}
        - ${deployment.status.observedGeneration >= deployment.metadata.generation}
      template:
        apiVersion: apps/v1
        kind: Deployment
        metadata:
          name: ${schema.metadata.name}
          namespace: ${schema.metadata.namespace}
          labels:
            app.kubernetes.io/name: ${schema.metadata.name}
        spec:
          replicas: ${schema.spec.replicas}
          selector:
            matchLabels:
              app.kubernetes.io/name: ${schema.metadata.name}
          template:
            metadata:
              labels:
                app.kubernetes.io/name: ${schema.metadata.name}
            spec:
              automountServiceAccountToken: false
              securityContext:
                runAsNonRoot: true
                runAsUser: 101
                runAsGroup: 101
                fsGroup: 101
                seccompProfile:
                  type: RuntimeDefault
              containers:
                - name: web
                  image: ${schema.spec.image}
                  ports:
                    - name: http
                      containerPort: 8080
                  securityContext:
                    allowPrivilegeEscalation: false
                    readOnlyRootFilesystem: true
                    capabilities:
                      drop: [ALL]
                  resources:
                    requests:
                      cpu: 100m
                      memory: 64Mi
                    limits:
                      cpu: 500m
                      memory: 128Mi
                  readinessProbe:
                    httpGet:
                      path: /
                      port: http
                  volumeMounts:
                    - name: tmp
                      mountPath: /tmp
              volumes:
                - name: tmp
                  emptyDir:
                    sizeLimit: 64Mi
    - id: service
      template:
        apiVersion: v1
        kind: Service
        metadata:
          name: ${schema.metadata.name}
          namespace: ${schema.metadata.namespace}
          labels:
            app.kubernetes.io/name: ${schema.metadata.name}
        spec:
          type: ClusterIP
          selector: ${deployment.spec.selector.matchLabels}
          ports:
            - name: http
              port: 8080
              targetPort: http
    - id: ingress
      includeWhen:
        - ${schema.spec.ingress.enabled}
      template:
        apiVersion: networking.k8s.io/v1
        kind: Ingress
        metadata:
          name: ${schema.metadata.name}
          namespace: ${schema.metadata.namespace}
          labels:
            app.kubernetes.io/name: ${schema.metadata.name}
        spec:
          ingressClassName: ${schema.spec.ingress.className}
          tls:
            - hosts:
                - ${schema.spec.ingress.host}
              secretName: ${schema.spec.ingress.tlsSecret}
          rules:
            - host: ${schema.spec.ingress.host}
              http:
                paths:
                  - path: /
                    pathType: Prefix
                    backend:
                      service:
                        name: ${service.metadata.name}
                        port:
                          number: 8080
```

### 实例

```yaml
apiVersion: platform.example.com/v1alpha1
kind: NginxApp
metadata:
  name: reviewed-web
  namespace: example
spec:
  replicas: 2
  image: nginxinc/nginx-unprivileged:1.30.6-alpine
  ingress:
    enabled: false
    className: internal
    host: app.example.com
    tlsSecret: app-tls
```

schema.spec 中的 SimpleSchema 描述类型、默认值和取值范围；kro 会将其转换为生成的 CRD 的 OpenAPI 架构。CEL 中的 schema.metadata/spec 指向实例，而 deployment/service 指向资源 ID。在 schema.status 下定义投影状态。

此示例中的 readyWhen 会检查 Deployment 自身的 availableReplicas 和 observedGeneration。如果没有就绪条件，只要资源存在且引用可解析，就可能继续推进。readyWhen 必须返回 Boolean 值，且只能引用其自身的资源 ID。应用 SLO 和数据库检查仍需单独处理。

Service 引用 Deployment 选择器，Ingress 引用 Service 名称，从而形成依赖关系。互相独立的资源可以处于同一波次；循环依赖会被拒绝。includeWhen 控制条件包含，并可在条件变化时添加或裁剪资源。对现有资源使用 externalRef，与接管所有权以创建或删除资源不同。

### 应用顺序和检查

在获准的集群中，先应用经过审查的 RBAC 和 RGD，确认 RGD 状态为 Active，且生成的 nginxapps.platform.example.com CRD 已 Established，然后再应用实例。kubectl apply 成功并不能证明资源图已编译或应用已就绪。

```bash
kubectl get rgd reviewed-nginxapps -o yaml
kubectl get graphrevisions \
  -l internal.kro.run/resource-graph-definition-name=reviewed-nginxapps
kubectl get crd nginxapps.platform.example.com -o yaml
kubectl get nginxapps.platform.example.com reviewed-web -n example -o yaml
kubectl get deployments,services,ingresses -n example \
  -l app.kubernetes.io/name=reviewed-web
```

## GraphRevision 和变更

0.9.4 版本会在 RGD spec 变更时记录并编译不可变的 GraphRevision。最新 revision 失败时，不会自动回退到之前的 revision；实例推进可能因此停止。请检查 GraphAccepted、GraphVerified、GraphRevisionsResolved 和错误消息，然后应用有效的 spec。

GraphRevision 是 internal.kro.run API。可用它进行检查和诊断，但不要假定外部工具接口契约稳定。回退 Git spec 仍需在新的 revision 中进行验证，而且不会以事务方式回滚数据库数据或外部副作用。

RGD 中的 group、kind、apiVersion 和 scope 均不可变。请区分兼容的架构演进与迁移到新 API，并审查现有实例和存储数据。不要假设系统会自动生成转换 webhook。

## 删除和所有权

删除实例时，kro 会使用 ApplySet 清单和删除波次，优先删除依赖项，并在受管资源消失前保留其实例的 finalizer。子资源的 finalizer 可能会阻止后续波次。外部引用是只读的，kro 永远不会删除它们。

声称所有子资源都会立即被垃圾回收是不准确的。请检查 ResourcesReady=Unknown/UnderDeletion、清单和子资源的 finalizer。在移除控制器之前，应规划实例、RGD、CRD 和数据的清理与保留方式。删除 CRD 也会影响实例数据。

## 迁移和运维

请审查名称、选择器、所有权、字段管理器和 GitOps 控制器，避免 Helm 与 kro 争相管理同一对象。应选择经过验证的全新名称资源图并切换流量，或采用经过审查的所有权转移流程。不要随意卸载拥有 StatefulSet、PVC 或数据库的 release 来进行迁移。

在各个环境中使用相同的 API 契约和经过审查的镜像摘要，并为命名空间、副本数、Ingress 和策略创建不同实例。ApplicationSet 等 Fleet 工具要求每个目标集群中都部署 kro、RGD 并配置相应权限。kro 不会自动连接到任意远程集群。

有状态应用仍然需要数据库 operator 或托管服务提供备份、恢复、故障转移和迁移功能。仅靠资源协调无法恢复数据。请限制资源图规模和权限，定义可复用单元，并仅公开有用的状态。不要将 Secret 内容复制到状态、标签或日志中。

## 验证和参考资料

已审阅原始的两份 504 行指南和两份 423 行测验，其中每种语言包含 16 个不同代码块和 20 个问题主题。已在 aggregation 模式下渲染官方 kro 0.9.4 chart，并检查 RGD 结构。其 cel-go 0.31.0 依赖项编译并评估了 14 个不同的已发布表达式。四个合成测试用例覆盖了 Ingress 开启/关闭、副本数不足和 observedGeneration 过期的情况。

这些是使用动态合成输入进行的 CEL 检查，并非通过完整 kro 资源图编译器、Kubernetes API 发现、生成的 CRD 准入或运行中的控制器进行验证。未实际运行容器、Ingress/TLS、数据库或集群资源。

- [kro 0.9.4](https://github.com/kubernetes-sigs/kro/releases/tag/v0.9.4)
- [版本化 API 和源代码](https://github.com/kubernetes-sigs/kro/tree/v0.9.4)
- [RGD 架构](https://github.com/kubernetes-sigs/kro/blob/v0.9.4/website/docs/docs/concepts/rgd/01-schema.md)
- [访问控制](https://github.com/kubernetes-sigs/kro/blob/v0.9.4/website/docs/docs/advanced/01-access-control.md)
- [资源图修订版本](https://github.com/kubernetes-sigs/kro/blob/v0.9.4/website/docs/docs/advanced/05-graph-revisions.md)
- [实例删除](https://github.com/kubernetes-sigs/kro/blob/v0.9.4/website/docs/docs/advanced/06-instance-deletion.md)

[kro 测验](../quizzes/platform-engineering/03-kro-quiz.md)
