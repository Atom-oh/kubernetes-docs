# AWS Controllers for Kubernetes (ACK)

> **最后更新**：2026 年 10 月 16 日

## 概念与架构

ACK 通过特定于服务的控制器，将 Kubernetes 自定义资源连接到 AWS API。CRD 定义输入；控制器协调期望状态与观测到的 AWS 状态。创建 CR 并不意味着 AWS 资源已就绪。请检查状态以及服务自身的就绪情况。

ACK 重用 Kubernetes API、RBAC 和 GitOps 工具，但 Kubernetes 授权与 AWS IAM 仍然彼此独立。用户的 CR 通常会触发控制器使用其 AWS 权限执行操作。因此，允许用户写入 CR，就等于授权其通过该控制器请求 AWS 操作。

ACK 并非 CloudFormation 或 Terraform 的必然继任者；实际资源由 AWS 持有，CR spec/status 则由 Kubernetes 持有。漂移处理取决于受支持的字段和控制器逻辑。应指定一个变更所有者，而不要让多个工具或集群协调同一个 AWS 资源。

![ACK 通过 AWS API 协调 Kubernetes 自定义资源](../.gitbook/assets/en-platform-engineering-02-ack-0.png)

[交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-platform-engineering-02-ack-0.html)

## 版本与支持

| 控制器 | 版本 |
| --- | --- |
| s3 | 1.13.1 |
| iam | 1.10.1 |
| sqs | 1.8.2 |
| sns | 1.11.1 |
| elbv2 | 1.8.2 |
| route53 | 1.7.1 |
| rds | 1.13.3 |

这些版本已与官方发布版本和 OCI Helm charts 逐项核对。完整的服务覆盖范围以及 Alpha/Beta/GA 状态，请参阅官方服务列表。GA 并不意味着涵盖了所有 AWS API 功能或所有运维要求。CRD 的 v1alpha1 API 字符串与控制器的成熟度是两回事。

历史上 Kubernetes 1.16 的最低版本要求并非当前的运维基线。请一并确认受支持的 Kubernetes/EKS 版本、控制器兼容性、Helm 版本和 CRD 升级流程。

## 安装准备与离线检查

请使用下面的 OCI chart 地址，不要再使用旧的 eks-charts s3-chart 路径。此命令仅渲染清单，不会安装到集群中。

```bash
helm template ack-s3 \
  oci://public.ecr.aws/aws-controllers-k8s/s3-chart \
  --version 1.13.1 --namespace infra \
  --set aws.region=us-west-2 \
  --set installScope=namespace --set watchNamespace=infra \
  --set enableCARM=false --set enableCrossNamespace=false \
  --set serviceAccount.create=false \
  --set serviceAccount.name=ack-s3-controller \
  --set metrics.service.create=true --set deletionPolicy=retain
```

在实际安装/升级之前，请先准备 infra 命名空间和控制器 ServiceAccount，然后配置 IRSA 或受支持的 EKS Pod Identity。请验证 IRSA OIDC 信任条件是否适用于该命名空间及其 ServiceAccount，或者确认 Pod Identity agent/SDK 兼容性及关联配置。仅创建 IAM 角色并不会为 ServiceAccount 关联权限。

请根据所管理的资源，检查控制器读取、创建、更新、删除和添加标签的权限，以及任何 PassRole 权限。AmazonS3FullAccess 或 Resource:"*" 并非最小权限示例。子指南中的数据访问策略并非完整的控制器策略。

渲染成功并不能验证 IAM、AWS API 限制、准入、CRD 安装、端点连接或资源创建。安装控制器和更改 CRD 是彼此独立的运维变更。

## 命名空间与账户隔离

installScope 的默认值为 cluster。仅将不同的 Helm release 分别安装到 dev/prod 命名空间，并不能避免两个控制器监视同一批 CR。此示例设置 installScope=namespace 和 watchNamespace=infra，并禁用 CARM 和跨命名空间引用。其他团队应使用独立的监视范围、ServiceAccount、IAM 角色和 RBAC。

即使在命名空间模式下，当前 chart 仍会渲染一个 ClusterRole，授予其对命名空间的 get/list/watch 权限，以支持命名空间缓存。命名空间模式并不会移除所有集群级权限。请检查渲染后的 Role、ClusterRole、Binding 以及 Secret/FieldExport 访问权限。修改命名空间注解、角色映射和引用目标的权限也会影响隔离。

CARM 是一种跨账户管理功能，需要目标 IAM 角色的信任关系、AssumeRole 权限和控制器配置。它并不能保证多个集群同时变更资源时的安全性。应将只读引用与变更所有权分开。

## 创建、引用与状态

各服务的 schema 各不相同。S3 policy 应配置在 Bucket.spec.policy 中；没有单独的 BucketPolicy CRD。IAM 托管策略通过 Role.policies/policyRefs 进行附加。子指南展示了 SQS queueName/字符串属性，以及 SNS 专用的 Topic/Subscription 字段。

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

ACK.ResourceSynced=True 表示控制器同步状态；它不是数据库连接或应用就绪检查。请检查 ACK.Terminal/ACK.Recoverable 等其他条件以及服务状态。若资源提供了 ARN，则该 ARN 位于 status.ackResourceMetadata.arn 下；NLB 和 TargetGroup ARN 也使用此路径。

受支持的 Ref 字段可以连接同一命名空间中的资源。一次应用多个 YAML 文档并不构成 AWS 范围内的事务。请确认被引用资源已就绪，并检查外部标识符/ARN。

## 资源接管与保留

请使用以下 ResourceAdoption 注解。当前 S3 chart 已启用此功能开关。接管前请检查标识符、账户和区域，并规划从其他工具转移所有权。

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

运行时接受 adopt 和 adopt-or-create。adopt 会将现有状态读入 spec/status；adopt-or-create 则可创建缺失的资源。后续的常规协调仍可能更改被接管的资源，因此接管并非单纯的只读访问。只读行为是一个独立功能，有自己的功能开关和生命周期。旧的 resource-imported:"true" 注解不能配置资源接管。官方文档还指出 AdoptedResource 是较早采用的方法。

保留值为 **retain**。当前运行时不接受 orphan。优先级依次为单个 CR 的 services.k8s.aws/deletion-policy、命名空间级别的服务专用 deletion-policy，然后是控制器默认值。保留 AWS 资源意味着仍需承担持续成本、所有权和备份责任。

## 可观测性、扩缩与恢复

启用 metrics.service.create，并匹配以下目标命名空间和端口名称。Prometheus Operator CRD 和 Prometheus ServiceMonitor 选择器是两个独立的前提条件。

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

经检查的运行时定义了 ack_outbound_api_requests_total 和 ack_outbound_api_requests_error_total。不要臆造协调成功/失败或 API 延迟指标名称。请在实际端点验证 controller-runtime 指标名称、标签和版本。CloudTrail 审计取决于服务/API 的日志记录支持情况以及已配置的事件。

副本配置项为 deployment.replicas；运行多个副本时，请检查 leaderElection.enabled。replicaCount 不是此 Helm chart 的配置项。增加参与 leader 选举的副本并不会自动提高并行吞吐量。请根据观测到的配额、限流情况和资源使用量，调整协调并发度和重新同步配置。

请在 Git 中对环境专属的清单和 Helm charts 进行版本管理，并避免将凭据纳入其中。恢复过程除了 CR 之外，还需要 AWS 数据/备份、标识符、保留策略和所有权。在另一个区域创建 CR 并不能实现数据复制或恢复。

## 故障排查

创建失败时，请检查条件/事件、控制器镜像/日志、账户/区域、IAM 信任关系/策略、引用和服务限制。区分 Kubernetes RBAC 错误与 AWS IAM 错误。对于处于 Terminating 状态的资源，请确认 finalizer 正在等待哪个 AWS 删除、依赖项或保留条件。

不要常规清除 finalizer。这样做可能会留下未跟踪的 AWS 资源。应先解决根本原因；只有在检查实际资源状态、备份和后续所有权之后，才能将最后手段恢复流程作为应急方案使用。

## 验证与参考资料

已阅读原始的八个指南文件，以及韩文/英文的两份测验，其中包含 56 个唯一代码块。七个官方 OCI Helm charts 已完成渲染，并依据带版本的 CRD 检查了 18 个资源示例，且启用了对未知 spec 字段的拒绝功能。未测试 AWS 资源创建、控制器运行、准入/CEL、消息传递或数据库连接。

- [ACK 服务](https://aws-controllers-k8s.github.io/community/docs/community/services/)
- [资源接管](https://aws-controllers-k8s.github.io/community/docs/user-docs/features/#resourceadoption)
- [保留策略](https://aws-controllers-k8s.github.io/community/docs/user-docs/deletion-policy/)
- [S3 chart 1.13.1](https://github.com/aws-controllers-k8s/s3-controller/tree/v1.13.1/helm)
- [Runtime 0.66.0](https://github.com/aws-controllers-k8s/runtime/tree/v0.66.0)

[ACK 测验](../quizzes/platform-engineering/02-ack-quiz.md)
