# Kube Resource Orchestrator (kro)

> **最后更新**: September 12, 2026 · **基线**: kro 0.9.4

## 概念与范围

正式名称为 Kube Resource Orchestrator，是 Kubernetes SIG Cloud Provider 的子项目。ResourceGraphDefinition (RGD) 定义 Kubernetes 资源之间的输入架构、关系和状态。验证和编译后，kro 会动态协调生成的 CRD 实例。

RGD 定义的是 API 和资源图，而不是应用实例。实例的 spec 提供输入，spec.resources 模板则创建 Deployment 和 Service 等对象。ACK 资源等现有 CRD 可以参与其中，但 kro 不提供其控制器或 AWS IAM 权限。

YAML 中的 `${...}` 表达式使用 CEL。之前的 .parent、.children、childResources、resourceKind、statusMappings 和 Go-template 示例并非此 API。不要独立创建相同的应用 CRD 并与 RGD 争夺所有权。

## 与 Helm、Kustomize 和 Operator 的比较

| 工具 | 主要角色与边界 |
| --- | --- |
| Helm | 渲染 Go-template chart 并管理发布历史。v2 chart 依赖项在 Chart.yaml 中声明。 |
| Kustomize | 使用 base 和 patch 转换清单；它不是运行时控制器。 |
| 自定义 operator | 可以通过代码实现特定领域的恢复、迁移和备份。 |
| kro | 从 CEL 引用推断资源图并协调实例；它不会生成数据库恢复算法。 |

Helm chart 可以安装 kro，而 GitOps 管理 RGD 和实例。这些工具可以配合使用。从 Helm 迁移到 kro 不会自动改善安全性、恢复能力或运维。Kubernetes Deployment 控制器也会继续管理最初由 Helm 创建的 Deployment。

## 安装与权限

官方仓库为 kubernetes-sigs/kro；较旧的 kro-run 路径可能会重定向。以下是对固定 OCI chart 的**离线检查**。不要使用之前的 kro-project 下载 URL 或虚构的 CLI 安装方式。此版本不发布单独的 CLI 二进制文件；请使用 kubectl 和 Helm。

```bash
helm template kro oci://registry.k8s.io/kro/charts/kro \
  --version 0.9.4 --namespace kro-system \
  --set rbac.mode=aggregation --include-crds
```

安装前，请验证受支持的 Kubernetes 版本、准入策略、命名空间以及现有的 CRD/控制器。之前的 1.31–1.33 列表并非当前支持范围。Helm upgrade 不会自动更新 crds/；请通过单独流程审查 0.9.4 版本和 CRD 变更。

默认的 rbac.mode=unrestricted 会授予广泛的集群访问权限。该示例渲染 aggregation 模式，仍包含 CRD、RGD、GraphRevision 和 ConfigMap 的基础权限。请为生成的应用 API 和子资源添加权限。此 ClusterRole 允许示例中的资源类型，并且可以授予整个集群范围内的访问权限。受信任的平台管理员应控制 RGD 和聚合标签。

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

## 完整 NginxApp 示例

RGD、实例和 RBAC 文件也位于 examples/platform/kro。Ingress 默认禁用。在启用之前，请在同一命名空间中准备已批准的 IngressClass/控制器、主机 DNS 和 TLS Secret。仅设置字符串 className=internal 并不会配置内部负载均衡器。

该镜像使用与 Helm 示例相同的 nginx-unprivileged 标签。已配置非 root UID、只读根目录和 /tmp 卷，但未测试镜像执行。部署前请验证摘要、架构和策略。

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
      image: string | default="nginxinc/nginx-unprivileged:1.30.4-alpine"
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
  image: nginxinc/nginx-unprivileged:1.30.4-alpine
  ingress:
    enabled: false
    className: internal
    host: app.example.com
    tlsSecret: app-tls
```

schema.spec 中的 SimpleSchema 描述类型、默认值和边界；kro 会将其转换为生成的 CRD 的 OpenAPI 架构。CEL schema.metadata/spec 指向实例，而 deployment/service 指向资源 ID。在 schema.status 下定义投影的状态。

此示例的 readyWhen 检查 Deployment 自身的 availableReplicas 和 observedGeneration。若没有就绪条件，资源存在且引用可解析可能就足以推进。readyWhen 必须返回 Boolean 值，并且只能引用自身的资源 ID。应用 SLO 和数据库检查仍需保持独立。

Service 引用 Deployment selector，Ingress 引用 Service 名称，从而创建依赖关系。独立资源可以共享一个 wave；循环会被拒绝。includeWhen 控制条件性包含，并可在条件变化时添加或修剪资源。指向现有资源的 externalRef 不同于取得其所有权以创建或删除它。

### 应用顺序与检查

在已批准的集群中，应用经过审查的 RBAC 和 RGD，验证 RGD 为 Active 且生成的 nginxapps.platform.example.com CRD 为 Established，然后再应用实例。kubectl apply 成功并不能证明图已编译或应用已就绪。

```bash
kubectl get rgd reviewed-nginxapps -o yaml
kubectl get graphrevisions \
  -l internal.kro.run/resource-graph-definition-name=reviewed-nginxapps
kubectl get crd nginxapps.platform.example.com -o yaml
kubectl get nginxapps.platform.example.com reviewed-web -n example -o yaml
kubectl get deployments,services,ingresses -n example \
  -l app.kubernetes.io/name=reviewed-web
```

## GraphRevision 与变更

当 RGD spec 变更时，0.9.4 版本会记录并编译不可变的 GraphRevision。最新 revision 失败时不会自动回退至先前版本；实例进展可能停止。检查 GraphAccepted、GraphVerified、GraphRevisionsResolved 和错误信息，然后应用有效 spec。

GraphRevision 是 internal.kro.run API。请将其用于检查和诊断，而不要假定外部工具契约稳定。将 Git spec 回退仍需要在新的 revision 中进行验证，并且不会以事务方式回滚数据库数据或外部影响。

组、kind、apiVersion 和 scope 在 RGD 内不可变。请区分兼容的 schema 演进与迁移至新 API，并审查现有实例和存储的数据。不要假定 conversion webhook 会自动生成。

## 删除与所有权

删除实例时，kro 使用 ApplySet 清单和删除 wave 先移除依赖其他资源的对象（依赖方），并在托管资源消失前保留其 finalizer。子资源 finalizer 可能阻塞后续 wave。外部引用为只读，kro 绝不会将其删除。

声称所有子资源都会立即被垃圾回收并不准确。请检查 ResourcesReady=Unknown/UnderDeletion、清单和子资源 finalizer。在移除控制器之前，请规划实例、RGD、CRD 和数据的清理与保留。删除 CRD 也会影响实例数据。

## 迁移与运维

审查名称、selector、所有权、field manager 和 GitOps 控制器，确保 Helm 和 kro 不会争夺同一对象。选择经过验证的新名称图并进行流量切换，或采用经过审查的所有权转移流程。不要通过随意卸载拥有 StatefulSet、PVC 或数据库的 release 来迁移。

在各环境中使用相同的 API 契约和经过审查的镜像摘要，并为命名空间、副本数、Ingress 和策略使用独立实例。ApplicationSet 等 fleet 工具要求每个目标集群都具备 kro、RGD 和权限。kro 不会自动连接任意远程集群。

有状态应用仍需要数据库 operator 或托管服务提供备份、恢复、故障转移和迁移行为。仅资源协调并不等于数据恢复。限制图的规模和权限，定义可复用单元，并且只公开有用的状态。不要将 Secret 内容复制到状态、标签或日志中。

## 验证与参考资料

已审查两份原始 504 行指南和 423 行测验，包括每种语言中的 16 个唯一代码块和 20 个问题主题。官方 kro 0.9.4 chart 已在 aggregation 模式下渲染，并已检查 RGD 结构。其 cel-go 0.31.0 依赖项已编译并评估了 14 个唯一的已发布表达式。四个合成场景覆盖了 Ingress 开启/关闭、副本不足和 observedGeneration 过期。

这些是使用动态合成输入进行的 CEL 检查，而非通过完整 kro 图编译器、Kubernetes API 发现、生成 CRD 准入或运行中的控制器进行的验证。未执行容器、Ingress/TLS、数据库和集群资源。

- [kro 0.9.4](https://github.com/kubernetes-sigs/kro/releases/tag/v0.9.4)
- [版本化 API 和源代码](https://github.com/kubernetes-sigs/kro/tree/v0.9.4)
- [RGD 架构](https://github.com/kubernetes-sigs/kro/blob/v0.9.4/website/docs/docs/concepts/rgd/01-schema.md)
- [访问控制](https://github.com/kubernetes-sigs/kro/blob/v0.9.4/website/docs/docs/advanced/01-access-control.md)
- [图 revision](https://github.com/kubernetes-sigs/kro/blob/v0.9.4/website/docs/docs/advanced/05-graph-revisions.md)
- [实例删除](https://github.com/kubernetes-sigs/kro/blob/v0.9.4/website/docs/docs/advanced/06-instance-deletion.md)

[kro 测验](../quizzes/platform-engineering/03-kro-quiz.md)
