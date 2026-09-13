# AWS Controllers for Kubernetes (ACK)

> **最后更新**: September 12, 2026

## 概念与架构

ACK 通过特定服务的 controller（控制器）将 Kubernetes 自定义资源连接到 AWS API。CRD 定义输入；controller 将期望状态与观测到的 AWS 状态进行协调（reconcile）。创建 CR 并不意味着 AWS 资源已就绪。请检查 status 以及该服务自身的就绪状态。

ACK 复用了 Kubernetes API、RBAC 和 GitOps 工具，但 Kubernetes 授权与 AWS IAM 仍然是相互独立的。用户的 CR 通常会以 controller 的 AWS 权限触发操作。因此，写入 CR 的权限相当于委派了通过该 controller 请求 AWS 操作的能力。

ACK 并非 CloudFormation 或 Terraform 的强制继任者。AWS 持有实际资源；Kubernetes 持有 CR 的 spec/status。漂移（drift）处理取决于所支持的字段和 controller 逻辑。请指定唯一的变更所有者，而不要让多个工具或集群协调同一个 AWS 资源。

![ACK reconciles Kubernetes custom resources through AWS APIs](../.gitbook/assets/en-platform-engineering-02-ack-0.png)

[交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-platform-engineering-02-ack-0.html)

## 版本与支持

| Controller | Version |
| --- | --- |
| s3 | 1.12.1 |
| iam | 1.9.0 |
| sqs | 1.7.0 |
| sns | 1.10.1 |
| elbv2 | 1.7.0 |
| route53 | 1.6.0 |
| rds | 1.12.0 |

这些版本已对照官方 release 和 OCI chart 进行核对。完整的覆盖范围以及 Alpha/Beta/GA 状态请查阅官方服务列表。GA 并不意味着覆盖了每一项 AWS API 功能或每一项运维需求。CRD 的 v1alpha1 API 字符串与 controller 的成熟度是两回事。

历史上要求的 Kubernetes 1.16 最低版本并不是当前的运维基线。请一并验证受支持的 Kubernetes/EKS 版本、controller 兼容性、Helm 版本以及 CRD 升级流程。

## 安装准备与离线检查

请使用下面的 OCI chart 路径，而不是以前的 eks-charts s3-chart 路径。此命令仅渲染 manifest，不会安装到集群中。

```bash
helm template ack-s3 \
  oci://public.ecr.aws/aws-controllers-k8s/s3-chart \
  --version 1.12.1 --namespace infra \
  --set aws.region=us-west-2 \
  --set installScope=namespace --set watchNamespace=infra \
  --set enableCARM=false --set enableCrossNamespace=false \
  --set serviceAccount.create=false \
  --set serviceAccount.name=ack-s3-controller \
  --set metrics.service.create=true --set deletionPolicy=retain
```

在进行实际安装/升级之前，请准备好 infra namespace 和 controller 的 ServiceAccount，然后配置 IRSA 或受支持的 EKS Pod Identity。请验证针对该 namespace/ServiceAccount 的 IRSA OIDC 信任条件，或者 Pod Identity agent/SDK 的兼容性与关联关系。仅创建 IAM role 并不会把权限附加到 ServiceAccount 上。

请针对所管理的资源审查 controller 的读取/创建/更新/删除/打标签以及任何 PassRole 权限。AmazonS3FullAccess 或 Resource:"*" 不是最小权限示例。子指南中的数据访问策略并不是完整的 controller 策略。

渲染成功并不能验证 IAM、AWS API 约束、admission、CRD 安装、endpoint 连通性或资源创建。安装 controller 与变更 CRD 是两项独立的运维变更。

## Namespace 与账户隔离

installScope 默认为 cluster。仅仅把 release 安装到 dev/prod namespace 中，可能会导致两个 controller 都在监视同一批 CR。本示例设置了 installScope=namespace 和 watchNamespace=infra，并禁用了 CARM 与跨 namespace 引用。对于其他团队，请使用各自独立的监视范围、ServiceAccount、IAM role 和 RBAC。

即使在 namespace 模式下，当前 chart 仍会渲染一个 ClusterRole，为其 namespace 缓存授予对 namespace 的 get/list/watch 权限。namespace 模式并不会移除所有集群级权限。请检查渲染出的 Role、ClusterRole、Binding 以及 Secret/FieldExport 访问权限。修改 namespace annotation、role 映射和引用目标的权限同样会影响隔离性。

CARM 是跨账户管理，需要目标 role 的信任关系、AssumeRole 权限以及 controller 配置。它不能保证多个集群并发变更是安全的。请将只读引用与变更所有权分开。

## 创建、引用与状态

各服务的 schema 各不相同。S3 policy 属于 Bucket.spec.policy；不存在单独的 BucketPolicy CRD。IAM 托管策略通过 Role.policies/policyRefs 附加。子指南展示了 SQS 的 queueName/string 属性以及 SNS 专用的 Topic/Subscription 字段。

- [S3 / IAM](ack/01-s3-iam.md)
- [SQS / SNS](ack/02-sqs-sns.md)
- [ELBv2 / Route 53 / Aurora](ack/03-elbv2-route53-rds.md)

```bash
kubectl get buckets.s3.services.k8s.aws -n infra
kubectl get bucket.s3.services.k8s.aws app-data -n infra -o json
kubectl describe bucket.s3.services.k8s.aws app-data -n infra
kubectl logs -n infra \
  -l app.kubernetes.io/instance=ack-s3 --all-containers --tail=100
kubectl get events -n infra \
  --field-selector involvedObject.name=app-data
```

ACK.ResourceSynced=True 描述的是 controller 的同步情况；它不是数据库连接检查，也不是应用就绪性检查。请检查其他 condition，例如 ACK.Terminal/ACK.Recoverable 以及服务状态。当资源提供了 ARN 时，它位于 status.ackResourceMetadata.arn；NLB 和 TargetGroup 的 ARN 也使用这一路径。

受支持的 Ref 字段可以连接同一 namespace 内的资源。应用多个 YAML 文档并不构成一次覆盖整个 AWS 的事务。请验证被引用资源的就绪状态以及外部标识符/ARN。

## 接管（Adoption）与保留

请使用下面的 ResourceAdoption annotation。当前的 S3 chart 已启用该 feature gate。在接管之前，请审查标识符、账户和区域，并规划好从其他工具转移所有权的方案。

```yaml
apiVersion: s3.services.k8s.aws/v1alpha1
kind: Bucket
metadata:
  name: existing-data
  namespace: infra
  annotations:
    services.k8s.aws/adoption-policy: adopt
    services.k8s.aws/adoption-fields: '{"name":"REPLACE_WITH_EXISTING_BUCKET"}'
    services.k8s.aws/deletion-policy: retain
spec:
  name: REPLACE_WITH_EXISTING_BUCKET
```

runtime 接受 adopt 和 adopt-or-create。adopt 会把现有状态读入 spec/status；adopt-or-create 可以创建缺失的资源。之后的常规协调过程可能会变更已接管的资源，因此接管并不只是只读访问。只读行为是一项独立功能，有自己的 gate 和生命周期。以前的 resource-imported:"true" annotation 不用于配置接管。官方文档也指出 AdoptedResource 是较早的做法。

保留值为 **retain**。当前 runtime 不接受 orphan。优先级顺序为：单个 CR 的 services.k8s.aws/deletion-policy，然后是 namespace 上特定服务的 deletion-policy，最后是 controller 默认值。保留 AWS 资源会带来持续的成本、所有权和备份责任。

## 可观测性、伸缩与恢复

启用 metrics.service.create，并与下面的目标 namespace 和端口名称保持一致。Prometheus Operator CRD 以及 Prometheus ServiceMonitor 的 selector 是独立的前提条件。

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: ack-s3
  namespace: monitoring
spec:
  namespaceSelector:
    matchNames: [infra]
  selector:
    matchLabels:
      app.kubernetes.io/name: s3-chart
      app.kubernetes.io/instance: ack-s3
  endpoints:
    - port: metricsport
      interval: 30s
```

所审查的 runtime 定义了 ack_outbound_api_requests_total 和 ack_outbound_api_requests_error_total。请不要臆造协调成功/失败或 API 延迟的指标名称。请在实际 endpoint 上验证 controller-runtime 的指标名称、标签和版本。CloudTrail 审计取决于服务/API 的日志支持以及所配置的事件。

副本配置项是 deployment.replicas；运行多个副本时请检查 leaderElection.enabled。replicaCount 不是此 chart 的配置项。增加参与 leader 选举的副本并不会自动提升并行吞吐量。请结合观测到的配额、限流和资源使用情况来调整协调并发度/resync。

请在 Git 中对各环境专用的 manifest 和 chart 进行版本管理，并将凭证排除在外。恢复不仅需要 CR，还需要 AWS 数据/备份、标识符、保留策略和所有权。在另一个区域创建 CR 并不等于实现了数据复制或恢复。

## 故障排查

对于创建失败，请检查 condition/event、controller 镜像/日志、账户/区域、IAM 信任关系/策略、引用以及服务约束。请区分 Kubernetes RBAC 错误与 AWS IAM 错误。对于处于 Terminating 状态的资源，请找出 finalizer 正在等待的 AWS 删除操作、依赖关系或保留条件。

不要习惯性地清除 finalizer。这样做可能会留下无人跟踪的 AWS 资源。请先解决根本原因；只有在审查了实际资源状态、备份以及后续所有权之后，才可将其作为最后手段的恢复步骤。

## 验证与参考

已阅读韩文/英文的八个原始指南文件和两个测验，其中包含 56 个唯一的代码块。已渲染七个官方 OCI chart，并针对带版本的 CRD（启用未知 spec 字段拒绝）检查了 18 个资源示例。未测试任何 AWS 资源创建、controller 执行、admission/CEL、消息投递或数据库连通性。

- [ACK services](https://aws-controllers-k8s.github.io/community/docs/community/services/)
- [Resource adoption](https://aws-controllers-k8s.github.io/community/docs/user-docs/features/#resourceadoption)
- [Retention](https://aws-controllers-k8s.github.io/community/docs/user-docs/deletion-policy/)
- [S3 chart 1.12.1](https://github.com/aws-controllers-k8s/s3-controller/tree/v1.12.1/helm)
- [Runtime 0.63.0](https://github.com/aws-controllers-k8s/runtime/tree/v0.63.0)

[ACK 测验](../quizzes/platform-engineering/02-ack-quiz.md)
