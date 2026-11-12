# Kube Resource Orchestrator (kro)

> **最后更新**：2026年10月23日 · **基线版本**：kro 0.9.4

## 概念与范围

官方名称为 Kube Resource Orchestrator，它是 Kubernetes SIG Cloud Provider 的一个子项目。ResourceGraphDefinition (RGD) 定义 Kubernetes 资源之间的输入 Schema、关系和状态。经过验证和编译后，kro 会动态协调生成的 CRD 实例。

RGD 定义的是 API 和资源图，而不是应用实例。实例的 spec 提供输入，spec.resources 模板则创建 Deployment 和 Service 等对象。现有 CRD（例如 ACK 资源）可以参与其中，但 kro 不提供这些资源的控制器或 AWS IAM 权限。

YAML 中的 `${...}` 表达式使用 CEL。以前的 .parent、.children、childResources、resourceKind、statusMappings 和 Go 模板示例都不属于此 API。不要独立创建相同的应用 CRD，以免与 RGD 争夺所有权。

## 与 Helm、Kustomize 和 Operator 的比较

| 工具 | 主要作用与边界 |
| --- | --- |
| Helm | 渲染 Go 模板 Chart 并管理发布历史。v2 Chart 的依赖项在 Chart.yaml 中声明。 |
| Kustomize | 使用 bases 和 patches 转换清单；它不是运行时控制器。 |
| 自定义 Operator | 可以在代码中实现特定业务域的恢复、迁移和备份。 |
| kro | 根据 CEL 引用推断资源图并协调实例；它不会生成数据库恢复算法。 |

Helm Chart 可以安装 kro，同时由 GitOps 管理 RGD 和实例。这些工具可以协同工作。从 Helm 迁移到 kro 并不会自动提升安全性、恢复能力或运维水平。Kubernetes Deployment 控制器也会继续管理最初由 Helm 创建的 Deployment。

## 安装与权限

官方代码仓库是 kubernetes-sigs/kro；旧的 kro-run 路径可能会重定向。这是对固定版本 OCI Chart 的**离线检查**。不要使用以前的 kro-project 下载 URL 或虚构的 CLI 安装方式。此版本不提供独立的 CLI 二进制文件；请使用 kubectl 和 Helm。

```bash
helm template kro oci://registry.k8s.io/kro/charts/kro \
  --version 0.9.4 --namespace kro-system \
  --set rbac.mode=aggregation --include-crds
```

安装之前，请确认 Kubernetes 版本受支持，并检查准入策略、命名空间以及现有 CRD 和控制器。以前列出的 1.31–1.33 不代表当前支持的版本范围。Helm upgrade 不会自动更新 crds/；请通过单独流程审查 0.9.4 发布版本及 CRD 变更。

默认的 rbac.mode=unrestricted 会授予广泛的集群访问权限。此示例渲染的是 aggregation 模式，但仍包含对 CRD、RGD、GraphRevisions 和 ConfigMaps 的基础权限。请为生成的应用 API 和子资源添加权限。此 ClusterRole 允许访问示例中的资源类型，并可能授予跨集群的访问权限。应由受信任的平台管理员管理 RGD 和聚合标签。

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

RGD、实例和 RBAC 文件也位于 examples/platform/kro 中。Ingress 默认处于禁用状态。启用之前，请准备经过批准的 IngressClass/控制器、主机 DNS，以及同一命名空间中的 TLS Secret。仅设置字符串 className=internal 并不会配置内部负载均衡器。此示例允许实例直接设置 `ingress.className` 和 `ingress.host`，在多租户集群中，这可能被用于接管其他团队的主机。在生产环境的 RGD 中，应固定 class，并根据实例名称和命名空间生成主机名。

镜像使用与 Helm 示例相同的 nginx-unprivileged 标签。已配置非 root UID、只读根文件系统和 /tmp 卷，但未测试镜像执行情况。部署前请验证摘要、架构和策略。

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

Schema.spec 中的 SimpleSchema 描述类型、默认值和取值范围；kro 会将其转换为生成的 CRD 的 OpenAPI Schema。CEL 中的 schema.metadata/spec 指向实例，而 deployment/service 指向资源 ID。请在 schema.status 下定义投影状态。

此示例的 readyWhen 会检查 Deployment 自身的 availableReplicas 和 observedGeneration。如果没有就绪条件，则资源存在且引用可解析可能就足以继续推进。readyWhen 必须返回布尔值，并且只能引用它自己的资源 ID。应用 SLO 和数据库检查仍需单独处理。

Service 引用 Deployment 选择器，Ingress 引用 Service 名称，由此形成依赖关系。互不依赖的资源可以处于同一阶段；循环依赖会被拒绝。includeWhen 控制条件包含，并可在条件变化时添加或修剪资源。对现有资源使用 externalRef，与取得所有权并创建或删除资源不同。

### 应用顺序与检查

在获准的集群中，应用经过审查的 RBAC 和 RGD，确认 RGD 处于 Active 状态且生成的 nginxapps.platform.example.com CRD 已处于 Established 状态，然后再应用实例。kubectl apply 成功并不能证明资源图已编译完成或应用已就绪。

```bash
kubectl get rgd reviewed-nginxapps -o yaml
kubectl get graphrevisions \
  -l internal.kro.run/resource-graph-definition-name=reviewed-nginxapps
kubectl get crd nginxapps.platform.example.com -o yaml
kubectl get nginxapps.platform.example.com reviewed-web -n example -o yaml
kubectl get deployments,services,ingresses -n example \
  -l app.kubernetes.io/name=reviewed-web
```

## GraphRevisions 与变更

在 0.9.4 版本中，当 RGD spec 发生变化时，kro 会记录并编译不可变的 GraphRevisions。最新版本编译失败时，不会自动回退到先前版本；实例推进可能因此停止。请检查 GraphAccepted、GraphVerified、GraphRevisionsResolved 和错误消息，然后应用有效的 spec。

GraphRevision 是一个 internal.kro.run API。可将其用于检查和诊断，但不要假设外部工具契约稳定。即使回退 Git 中的 spec，仍需在新版本中完成验证，而且不会以事务方式回滚数据库数据或外部影响。

在一个 RGD 中，Group、kind、apiVersion 和 scope 均不可变。请区分兼容的 Schema 演进与迁移到新 API，并检查现有实例和存储的数据。不要假设会自动生成转换 Webhook。

## 删除与所有权

删除实例时，kro 会使用 ApplySet 清单和删除阶段，先移除依赖资源，并保留其 finalizer，直到受管资源消失。子资源的 finalizer 可能会阻止后续阶段执行。外部引用是只读的，kro 绝不会删除它们。

声称所有子资源都会立即被垃圾回收是不准确的。请检查 ResourcesReady=Unknown/UnderDeletion、清单和子资源的 finalizer。在移除控制器之前，规划好实例、RGD、CRD 和数据的清理与保留。删除 CRD 也会影响实例数据。

## 迁移与运维

请检查名称、选择器、所有权、字段管理器和 GitOps 控制器，确保 Helm 与 kro 不会争相管理同一个对象。请选择经验证的新名称资源图并切换流量，或者采用经过审查的所有权转移流程。不要随意卸载一个拥有 StatefulSet、PVC 或数据库的发布版本来执行迁移。

在各环境中使用相同的 API 契约和经过审查的镜像摘要，并为不同命名空间、副本数、Ingress 和策略使用独立实例。ApplicationSet 等集群队列工具要求每个目标集群都具备 kro、RGD 和相应权限。kro 不会自动连接到任意远程集群。

有状态应用仍需要数据库 Operator 或托管服务提供备份、恢复、故障转移和迁移能力。仅协调资源并不能恢复数据。请限制资源图规模和权限，定义可复用单元，并且只公开有用的状态。不要将 Secret 内容复制到状态、标签或日志中。

## EKS 托管 kro

EKS Capabilities 的 kro 功能会在 AWS 拥有的基础设施上运行相同的上游控制器（测得版本为 `0.9.4-eks-1`）。2026年10月的测试使用了本章中的 `NginxApp` RGD，并修改了它以固定 Ingress 类和主机；CEL 表达式无需修改即可运行，实例生命周期的计时结果也与 OSS 一致。差异在于权限和运维方式。

- 默认访问条目策略 `AmazonEKSKROPolicy` 仅涵盖 `kro.run` 和 CRD。在访问条目中，将上方的 `kro:controller:reviewed-nginxapps` 等 ClusterRole 绑定到一个 Kubernetes 组；若没有此绑定，RGD 会报告 `ControllerReady=False` 和 `cache sync timeout`，而不是 forbidden。规则相同；只有绑定机制不同（使用组，而不是聚合标签）。
- AWS 会选择版本，你无法固定版本。控制器标志和资源限制也无法更改。
- 如果命名空间中存在与子资源同名的 CR，kro 会接管并覆盖它（OSS 的行为相同）。请为子资源名称添加特定于 RGD 的后缀。

有关测量结果和选择建议，请参阅 [EKS Capabilities](../eks/13-eks-capabilities.md)。

## 验证与参考资料

我们审查了两份原始的 504 行指南和两份 423 行测验，其中包括每种语言各 16 个不同的代码块和 20 个问题主题。我们以聚合模式渲染了官方 kro 0.9.4 Chart，并检查了 RGD 结构。其 cel-go 0.31.0 依赖项编译并评估了 14 个不同的已发布表达式。四个合成案例涵盖 Ingress 启用/禁用、副本数不足和 observedGeneration 过期。

这些是使用动态合成输入执行的 CEL 检查，并非由完整的 kro 资源图编译器、Kubernetes API 发现、生成的 CRD 准入或运行中的控制器进行的验证。未实际运行容器、Ingress/TLS、数据库或集群资源。

- [kro 0.9.4](https://github.com/kubernetes-sigs/kro/releases/tag/v0.9.4)
- [版本化 API 和源代码](https://github.com/kubernetes-sigs/kro/tree/v0.9.4)
- [RGD Schema](https://github.com/kubernetes-sigs/kro/blob/v0.9.4/website/docs/docs/concepts/rgd/01-schema.md)
- [访问控制](https://github.com/kubernetes-sigs/kro/blob/v0.9.4/website/docs/docs/advanced/01-access-control.md)
- [资源图版本](https://github.com/kubernetes-sigs/kro/blob/v0.9.4/website/docs/docs/advanced/05-graph-revisions.md)
- [实例删除](https://github.com/kubernetes-sigs/kro/blob/v0.9.4/website/docs/docs/advanced/06-instance-deletion.md)

[kro 测验](../quizzes/platform-engineering/03-kro-quiz.md)
