# EKS 集群创建测验 - 第 5 部分

> **最后更新**：September 11, 2026

本测验涵盖 EKS 运维、日志记录、策略强制执行和租户隔离。最后几道题将这些主题与概念指南中的访问验证和退役流程联系起来。执行命令前，需要审核集群/Region/kubeconfig、IAM 和控制器前置条件；本次审计未执行云部署或生产环境测试。

## 选择题

1. 哪种方法可以结合非 Spot 基线容量与可中断容量？
   * A) 所有节点都使用 On-Demand
   * B) 分别使用 On-Demand 和 Spot 组，并放置工作负载
   * C) 将每个组的 capacityType 都设为 Reserved
   * D) 所有工作负载都必须使用 Fargate

<details>
<summary>显示答案</summary>

**答案：B) 分别使用 On-Demand 和 Spot 组，并放置工作负载**

混合使用可以满足对中断敏感的基线容量和可容忍中断的容量需求。为 On-Demand 和 Spot 分别使用独立的托管组，并明确放置工作负载。这并非适用于所有情况的“最有效”成本策略：结果取决于工作负载利用率、可靠性要求、Region/实例定价和运维投入。

AWS 宣称 Spot 相比 On-Demand 最多可节省 90%，但这并不意味着每个容量池都能保证获得折扣，也不代表本指南测量了实际节省。On-Demand 不会被 Spot 回收，但仍面临维护/故障风险。对 Spot 而言，检查点、重试和备用容量都很重要。

其他选项包括合理调整资源规格、使用 Cluster Autoscaler/Karpenter、采用兼容的 Graviton 镜像，以及适当使用承诺折扣。Reserved Instances/Savings Plans 是计费安排，并非普通托管组的另一种容量设置。Fargate 可能适用于某些需求模式；应比较预置容量和总成本，而不是假定某种计算类型总是最优。

</details>

2. 为什么要将适合的工作负载分布到多个 AZ？
   * A) 始终降低延迟
   * B) 保证更高吞吐量
   * C) 降低单个 AZ 故障的影响
   * D) 自动跨 Region 复制

<details>
<summary>显示答案</summary>

**答案：C) 降低单个 AZ 故障的影响**

使用多个 AZ 可以降低对单一故障域的依赖。托管 EKS control plane 分布在多个 AZ 中，但要让应用保持可用，还需要合理分布副本、健康的端点、备用容量，以及兼容的网络/存储。

Kubernetes 控制器可以创建替代 Pod；裸 Pod 不会自动重新创建，容量不足、硬亲和性或区域级 EBS 卷也可能阻碍恢复。仅仅列出多个子网，并不能确保每个应用副本都分布在这些子网上。应检查拓扑分布/反亲和性以及实际放置情况。

PDB 管理的是自愿驱逐，而不是 AZ 故障。滚动更新和跨 AZ 故障转移需要经过应用层验证，并制定数据恢复方案。多个 AZ 不会自动提供跨 Region 复制，还可能产生跨 AZ 数据传输成本。

</details>

3. 常规 EKS EC2 节点的默认 CNI 是什么？
   * A) Calico
   * B) Flannel
   * C) Amazon VPC CNI
   * D) Weave Net

<details>
<summary>显示答案</summary>

**答案：C) Amazon VPC CNI**

常规 EKS EC2 节点默认使用 Amazon VPC CNI。它通过受支持的辅助 IP 或前缀模式分配 VPC 地址。Auto Mode 提供自己的托管网络功能；Hybrid Nodes 使用受支持的替代 CNI。不要在现有 CNI 上安装未配置的替代方案。

Pod 的安全组需要各自受支持的实例/CNI 配置和策略选择；并非每个 Pod 都会自动获得独立安全组。原生 NetworkPolicy 也需要受支持的计算资源并显式启用。

在这种设计中，VPC 原生路由可避免使用传统覆盖网络，但这并不构成经过测量的性能保证。应验证带宽、路由、IP 容量、策略行为和应用要求。Load Balancer Controller 等集成也需要各自的安装和权限。

</details>

4. 哪种工作负载身份机制使用 EKS OIDC issuer 和投射的 ServiceAccount token？
   * A) IAM Roles for Service Accounts (IRSA)
   * B) EKS access policy
   * C) 仅使用 Kubernetes RoleBinding
   * D) 节点标签

<details>
<summary>显示答案</summary>

**答案：A) IAM Roles for Service Accounts (IRSA)**

**IAM Roles for Service Accounts (IRSA)** 使用投射的 ServiceAccount token、集群的 OIDC issuer 和 IAM 信任关系来获取 STS 临时凭证。应将信任范围限定为预期的受众 (`sts.amazonaws.com`) 和确切的 namespace/ServiceAccount subject，然后只授予所需的 AWS 操作/资源权限。

在 Pod 中使用预期的 ServiceAccount，并采用兼容的 SDK 凭证链。验证实际承担的角色身份；仅仅成功访问 AWS，也可能是通过其他凭证实现的。IRSA 本身并不能阻止访问节点 IMDS 凭证。

EKS Pod Identity 是另一种角色与 ServiceAccount 关联的机制，但使用不同的 agent/关联流程。它支持符合条件的 EC2/Auto Mode 和经过专门配置的 Hybrid Nodes；Fargate 则需要另一种受支持的机制，例如 IRSA。这两种机制都不是 EKS access entry：工作负载的 AWS 权限与对 Kubernetes API 的访问权限是分开的。

</details>

5. 哪个控制器会根据 Kubernetes 调度需求扩缩现有 EKS 托管节点组的 ASG？
   * A) Horizontal Pod Autoscaler
   * B) Vertical Pod Autoscaler
   * C) Cluster Autoscaler
   * D) ResourceQuota

<details>
<summary>显示答案</summary>

**答案：C) Cluster Autoscaler**

Cluster Autoscaler 会调整已发现的现有节点组/ASG。它需要兼容的安装、Kubernetes RBAC、专用 AWS 权限以及正确的发现标签；仅仅设置最小/最大容量并不会自动安装它。

它会根据调度请求/约束进行扩容，并根据重新调度/中断条件进行缩容。并非每个 Pending Pod 都能通过添加节点解决；其缩容利用率逻辑也不同于 HPA 的 CPU 使用率阈值。

HPA 会调整副本数，VPA 会建议/调整 Pod 请求，两者都可能间接改变节点需求。Karpenter 是使用 NodePools/NodeClaims 的独立容量预置器，并不是普遍更快的替代方案，也不是 ASG 控制器。应验证各控制环路和工作负载约束。

</details>

## 简答题

6. 如何启用并验证 EKS control plane 日志记录到 CloudWatch？

<details>
<summary>答案与说明</summary>

启用所需的 control plane 日志类型：`api`、`audit`、`authenticator`、`controllerManager` 和 `scheduler`。在 EKS 控制台中使用 **Observability → Control plane logging → Manage logging**，不要使用旧的 Logging 标签页说明。

以下示例启用全部五种日志类型；应根据环境选择经过审核的集合：

```bash
set -euo pipefail
LOG_UPDATE_ID=$(aws eks update-cluster-config \
  --name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}' \
  --query update.id --output text)
aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --update-id "$LOG_UPDATE_ID" --query 'update.{status:status,errors:errors}'
```
轮询返回的 update ID，直到状态变为 `Successful`；如有失败，应先处理后再进行其他更改。eksctl 替代方案需要使用 `--approve` 来应用日志记录更改：

```bash
# Alternative to the AWS CLI update, not a second concurrent update.
eksctl utils update-cluster-logging --cluster "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" \
  --enable-types=api,audit,authenticator,controllerManager,scheduler --approve
```
日志会发送到集群所在 Region 中的 `/aws/eks/<cluster-name>/cluster`。日志流会轮换，每种类型可能有多个日志流；日志传递是尽力而为的，通常会在几分钟内完成。应验证已启用的配置、当前日志流时间戳和相关实际事件。仅有日志组并不能证明日志已正常传递。应设置保留期和访问控制，考虑摄取/存储成本，并避免公开敏感审计事件。工作节点和应用日志需要单独的收集器。

</details>

7. 如何将常规 EKS Linux 节点上的 kubelet 日志收集到 CloudWatch？

<details>
<summary>答案与说明</summary>

kubelet 日志属于节点日志，与 EKS control plane 日志记录分开。对于 EKS 优化的 AL2023 Linux 路径，应检查 `kubelet.service` 的 systemd journal；不要假定 `/var/log/kubelet.log` 或 `/var/log/kube-proxy.log` 一定存在。kube-proxy 通常以容器形式记录日志。VPC CNI 日志文件/stdout 取决于其配置。

托管的 **Amazon CloudWatch Observability EKS add-on** 会安装 agent/operator 和 Fluent Bit。原始快速入门清单并不是这个托管 add-on。不要覆盖现有 ServiceAccount，也不要在未审核所有者的情况下替换整个 Fluent Bit ConfigMap。

以下示例适用于 **Linux EC2 实验环境**，要求 Pod Identity Agent 已就绪，并且已有获批角色信任此集群的 `amazon-cloudwatch/cloudwatch-agent` ServiceAccount。应审核其 CloudWatch 权限；`CloudWatchAgentServerPolicy` 是 AWS 托管的基准策略，并不意味着其中每项权限对于你的日志范围而言都是最小权限。当前 chart 中的 Fluent Bit 使用同一个 ServiceAccount；此设置不需要另建 `fluent-bit` IAM ServiceAccount。

首先选择兼容的 add-on 构建版本并检查其架构。Helm chart 版本与 EKS add-on 构建字符串并不相同：

```bash
set -euo pipefail
: "${EXAMPLE_CLUSTER:?}" "${EXAMPLE_REGION:?}"
CLUSTER_VERSION=$(aws eks describe-cluster --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --query cluster.version --output text)
aws eks describe-addon-versions --region "$EXAMPLE_REGION" \
  --addon-name amazon-cloudwatch-observability --kubernetes-version "$CLUSTER_VERSION"
: "${CLOUDWATCH_ADDON_VERSION:?Choose a reviewed compatible build with the configuration fields below}"
aws eks describe-addon-configuration --region "$EXAMPLE_REGION" \
  --addon-name amazon-cloudwatch-observability --addon-version "$CLOUDWATCH_ADDON_VERSION" \
  --query configurationSchema --output text > cloudwatch-addon-schema.json
```
将以下内容保存为 `cloudwatch-addon-values.yaml`。该配置使用官方 chart 6.6.0 渲染。完整的 Linux `dataplane-log.conf` 覆盖配置只收集 kubelet journal 记录；将应用/主机文件设为空，可禁用这些默认日志路由。其他全局 Fluent Bit 配置段保留默认值。该 add-on 还会收集 Container Insights 指标，因此这并非仅安装日志 agent。为避免在此练习中自动对服务进行插桩，已明确禁用 Application Signals 自动监控。

```yaml
manager:
  applicationSignals:
    autoMonitor:
      monitorAllServices: false
containerLogs:
  fluentBit:
    config:
      extraFiles:
        application-log.conf: ''
        host-log.conf: ''
        dataplane-log.conf: |
          [INPUT]
            Name                systemd
            Tag                 dataplane.kubelet
            Systemd_Filter      _SYSTEMD_UNIT=kubelet.service
            DB                  /var/fluent-bit/state/kubelet.db
            Path                /var/log/journal
            Read_From_Tail      On

          [FILTER]
            Name                modify
            Match               dataplane.kubelet
            Rename              _HOSTNAME hostname
            Rename              MESSAGE message

          [OUTPUT]
            Name                cloudwatch_logs
            Match               dataplane.kubelet
            region              ${AWS_REGION}
            log_group_name      /aws/containerinsights/${CLUSTER_NAME}/dataplane
            log_stream_prefix   ${HOST_NAME}-
            auto_create_group   true
```
确认目标节点上已挂载 journal 路径，且状态目录可写。这些 Linux 覆盖配置不适用于 Windows 日志收集；混合、Hybrid 和 Auto Mode 环境需要使用相应文档中描述的路径。检查所选 add-on 的架构，并在将其用于更新之前保留任何无关的现有配置。

```bash
# New installation only, after the schema/role/configuration review.
: "${CLOUDWATCH_ROLE_ARN:?Existing approved Pod Identity role}"
CW_ASSOCIATIONS=$(jq -cn --arg role "$CLOUDWATCH_ROLE_ARN" \
  '[{serviceAccount:"cloudwatch-agent",roleArn:$role}]')
aws eks create-addon --cluster-name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --addon-name amazon-cloudwatch-observability --addon-version "$CLOUDWATCH_ADDON_VERSION" \
  --pod-identity-associations "$CW_ASSOCIATIONS" \
  --configuration-values file://cloudwatch-addon-values.yaml --resolve-conflicts NONE
aws eks describe-addon --cluster-name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --addon-name amazon-cloudwatch-observability --query 'addon.{status:status,health:health,version:addonVersion}'
```
等待特定的 add-on 操作完成，并检查健康错误、agent/Fluent Bit Pod，以及 `/aws/containerinsights/<cluster>/dataplane` 下的新事件。Helm 渲染成功或日志组存在，都不能证明日志收集正常。应审核 IAM、网络端点、日志保留期以及摄取/指标成本。已有的可观测性安装需要有计划地迁移；不要运行第二个会重复采集日志的收集器，也不要在未通知的情况下启用应用重启。本处未测试实际 agent 安装、journal 收集或 CloudWatch 日志传递。

</details>

8. PSP 被什么取代了，应该如何评估等效的准入控制？

<details>
<summary>答案与说明</summary>

PodSecurityPolicy 在 Kubernetes 1.21 中弃用，并在 1.25 中移除。当前受支持的 EKS 版本不提供该 API。Pod Security Admission (PSA) 会强制执行 Pod Security Standards (PSS) 配置文件，但并非 PSP 每项功能的一对一替代方案。

对于新的 EKS 1.36 实验 namespace，应固定配置文件版本，以免未来集群升级时悄然更改所选策略版本：

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: psa-lab
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.36
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: v1.36
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: v1.36
```
对于现有生产 namespace，应先评估 audit/warn 结果和应用兼容性，再强制执行 Restricted。PSA 会进行验证，但不会提供 PSP 旧有的变更/默认值设置行为。应将原有的 host namespace、capability、volume、ID 和 seccomp 控制映射到合适的替代方案。

**Kyverno 替代方案：**以下示例使用基于 CEL 的 `policies.kyverno.io/v1` ValidatingPolicy，适用于经过审核的 Kyverno 1.19.1/chart 3.9.1 路径。Legacy ClusterPolicy 在 1.19 中已弃用；这并不意味着它已被移除。需单独安装兼容的 controller/CRD，并使用经过审核的 `policy-engine-lab` namespace。示例会检查所有普通、init 和 ephemeral 容器：

```yaml
apiVersion: policies.kyverno.io/v1
kind: ValidatingPolicy
metadata:
  name: disallow-privileged-lab
spec:
  validationActions:
  - Deny
  evaluation:
    background:
      enabled: true
  matchConstraints:
    resourceRules:
    - apiGroups:
      - ''
      apiVersions:
      - v1
      operations:
      - CREATE
      - UPDATE
      resources:
      - pods
      - pods/ephemeralcontainers
  matchConditions:
  - name: lab-only
    expression: object.metadata.namespace == 'policy-engine-lab'
  validations:
  - expression: object.spec.containers.all(c, !has(c.securityContext) || !has(c.securityContext.privileged) || !c.securityContext.privileged)
    message: Privileged containers are not allowed.
  - expression: '!has(object.spec.initContainers) || object.spec.initContainers.all(c, !has(c.securityContext) ||
      !has(c.securityContext.privileged) || !c.securityContext.privileged)'
    message: Privileged initContainers are not allowed.
  - expression: '!has(object.spec.ephemeralContainers) || object.spec.ephemeralContainers.all(c, !has(c.securityContext)
      || !has(c.securityContext.privileged) || !c.securityContext.privileged)'
    message: Privileged ephemeralContainers are not allowed.
```
**Gatekeeper 替代方案：**仅有 ConstraintTemplate 并不能强制执行规则。以下模板和 Constraint 是经过审核的 Gatekeeper 3.23.1 示例；`templates.gatekeeper.sh/v1` 和生成的 Constraint API 使用不同的版本：

```yaml
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: k8snoprivilegedlab
spec:
  crd:
    spec:
      names:
        kind: K8sNoPrivilegedLab
      validation:
        openAPIV3Schema:
          type: object
  targets:
  - target: admission.k8s.gatekeeper.sh
    rego: |
      package k8snoprivilegedlab

      containers[c] {
        c := input.review.object.spec.containers[_]
      }
      containers[c] {
        c := input.review.object.spec.initContainers[_]
      }
      containers[c] {
        c := input.review.object.spec.ephemeralContainers[_]
      }
      violation[{"msg": msg}] {
        c := containers[_]
        c.securityContext.privileged == true
        msg := sprintf("Privileged container is not allowed: %v", [c.name])
      }
---
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sNoPrivilegedLab
metadata:
  name: no-privileged-lab
spec:
  enforcementAction: deny
  match:
    scope: Namespaced
    namespaces:
    - policy-engine-lab
    kinds:
    - apiGroups:
      - ''
      kinds:
      - Pod
```
这两个引擎示例是替代方案，只演示一项控制，并不等同于完整的 PSP 功能，也不是生产环境加固策略。应测试允许的/缺少 securityContext 的情况，以及启用 privileged 的普通/init/ephemeral 容器。应考虑准入失败策略、webhook 可用性和豁免项。GuardDuty、Security Hub 和 Inspector 能为受支持的资源提供互补的威胁/安全态势/漏洞能力，但不能取代准入时拒绝 Pod。

</details>

## 实践题

9. 配置独立的 On-Demand 和 Spot 组，并设置放置控制和自动扩缩前置条件。

<details>
<summary>答案与说明</summary>

使用**独立的**托管组：On-Demand 组为关键工作负载提供 2–5 个节点，Spot 组为可容忍中断的工作负载提供 2–10 个节点。这些只是示例，并非经过测量的节省或容量保证。应先选择一种创建方法和未使用的组名称，并验证私有子网出口/端点、IAM 以及 AMI/镜像兼容性。

eksctl 配置使用受支持的 `managedNodeGroups` 和 `spot` 字段。不要向每个节点授予 autoscaler-controller 权限：

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: critical-workloads
  amiFamily: AmazonLinux2023
  instanceType: m5.xlarge
  privateNetworking: true
  desiredCapacity: 2
  minSize: 2
  maxSize: 5
  spot: false
  labels:
    workload-type: critical
    node-lifecycle: on-demand
- name: general-workloads
  amiFamily: AmazonLinux2023
  instanceTypes: [m5.large, m5a.large, m5d.large, m5ad.large]
  privateNetworking: true
  desiredCapacity: 3
  minSize: 2
  maxSize: 10
  spot: true
  labels:
    workload-type: general
    node-lifecycle: spot
  taints:
  - key: spot
    value: "true"
    effect: PreferNoSchedule
```
保存并审核该文件，然后对现有集群使用 `eksctl create nodegroup -f nodegroups.yaml`。以下是 AWS CLI 替代方案。与 Kubernetes/eksctl 中的 CamelCase 不同，EKS API 的 taint effect 使用大写名称和结构化值：

```bash
set -euo pipefail
# Alternative to eksctl; use unused group names and approved role/subnet IDs.
aws eks create-nodegroup --cluster-name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --nodegroup-name "${CRITICAL_NODEGROUP_NAME:?}" --scaling-config minSize=2,maxSize=5,desiredSize=2 \
  --instance-types m5.xlarge --capacity-type ON_DEMAND --ami-type AL2023_x86_64_STANDARD \
  --subnets "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" --node-role "${NODE_ROLE_ARN:?}" \
  --labels workload-type=critical,node-lifecycle=on-demand
aws eks wait nodegroup-active --cluster-name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --nodegroup-name "$CRITICAL_NODEGROUP_NAME"

aws eks create-nodegroup --cluster-name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --nodegroup-name "${GENERAL_NODEGROUP_NAME:?}" --scaling-config minSize=2,maxSize=10,desiredSize=3 \
  --instance-types m5.large m5a.large m5d.large m5ad.large --capacity-type SPOT \
  --ami-type AL2023_x86_64_STANDARD --subnets "$PRIVATE_SUBNET_A" "$PRIVATE_SUBNET_B" \
  --node-role "$NODE_ROLE_ARN" --labels workload-type=general,node-lifecycle=spot \
  --taints '[{"key":"spot","value":"true","effect":"PREFER_NO_SCHEDULE"}]'
aws eks wait nodegroup-active --cluster-name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --nodegroup-name "$GENERAL_NODEGROUP_NAME"
```
在新的、经过审核的 `placement-lab` namespace 中，以下休眠容器仅用于演示调度。若要声称其行为代表实际应用，应先将它们替换为经过审核的真实应用镜像。关键工作负载选择器要求使用 On-Demand 标签。通用工作负载优先使用 Spot，但也可以回退到其他位置；toleration 允许放置，但不强制放置，`PreferNoSchedule` 是软性控制。

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: critical-app
  namespace: placement-lab
spec:
  replicas: 3
  selector:
    matchLabels:
      app: critical-app
  template:
    metadata:
      labels:
        app: critical-app
    spec:
      automountServiceAccountToken: false
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: workload-type
                operator: In
                values:
                - critical
              - key: node-lifecycle
                operator: In
                values:
                - on-demand
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: placement-check
        image: public.ecr.aws/docker/library/busybox:1.38.0
        command:
        - sleep
        - '3600'
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            cpu: 1000m
            memory: 2Gi
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: general-app
  namespace: placement-lab
spec:
  replicas: 5
  selector:
    matchLabels:
      app: general-app
  template:
    metadata:
      labels:
        app: general-app
    spec:
      automountServiceAccountToken: false
      affinity:
        nodeAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 1
            preference:
              matchExpressions:
              - key: node-lifecycle
                operator: In
                values:
                - spot
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: placement-check
        image: public.ecr.aws/docker/library/busybox:1.38.0
        command:
        - sleep
        - '3600'
        resources:
          requests:
            cpu: 250m
            memory: 512Mi
          limits:
            cpu: 500m
            memory: 1Gi
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
      tolerations:
      - key: spot
        operator: Equal
        value: 'true'
        effect: PreferNoSchedule
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: critical-app-pdb
  namespace: placement-lab
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: critical-app
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: general-app-hpa
  namespace: placement-lab
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: general-app
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```
保留的请求/限制值仅用于说明。PDB 保护适用于自愿驱逐，无法阻止 Spot 容量回收或 AZ 故障。HPA 需要 Metrics Server，以及有意义的负载/指标关系；休眠示例不是扩缩基准测试。

准备专用的 Cluster Autoscaler ServiceAccount/角色，授予受标签范围限制的 AWS 权限，并设置实际 ASG 发现标签。节点组标签不能证明 ASG 上也有相应标签。对于 EKS 1.36，应渲染经过审核的 chart/镜像组合，并在安装前检查：

```bash
helm repo add autoscaler https://kubernetes.github.io/autoscaler
helm repo update autoscaler
helm template cluster-autoscaler autoscaler/cluster-autoscaler \
  --version 9.59.0 --namespace kube-system \
  --set-string autoDiscovery.clusterName="${EXAMPLE_CLUSTER:?}" \
  --set-string awsRegion="${EXAMPLE_REGION:?}" \
  --set-string image.tag=v1.36.1 \
  --set rbac.serviceAccount.create=false \
  --set-string rbac.serviceAccount.name=cluster-autoscaler \
  > cluster-autoscaler-reviewed.yaml
```
除非单独审核后确认应更改，否则应保留本地存储/系统 Pod 保护措施。对于 CA 管理的混合实例组，CPU/内存/GPU 规格的可比性很重要。托管节点组已经具备 Spot 再平衡/排空处理；不要不加判断地再添加第二个 Node Termination Handler。自管理容量需要单独审核生命周期处理。应在具有代表性的工作负载条件下验证中断恢复、放置、数据持久性和总成本。

</details>

## 进阶题

10. 比较 EKS 租户隔离方法及其实际边界。

<details>
<summary>答案与说明</summary>

应根据实际信任、数据、可用性和治理要求选择租户边界。以下是**可选设计**，并非要求将所有示例组合到一个共享 namespace 中。

**独立集群/账户：**专用 API/control plane 资源可减少耦合，并允许独立选择生命周期，但运维成本较高。它们不会自动隔离共享 IAM、VPC、存储、配额或外部服务，也无法保证一个租户绝不会影响另一个租户。应使用经过审核的集群创建指南，而不是执行两条未经限定的默认 `eksctl create cluster` 命令。

**带强制控制的 namespace：**namespace 可以隔离名称，但不能隔离所有安全或容量。平台管理员负责创建新的租户 namespace，并管理其策略标签、配额和 RBAC 边界：

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: tenant-a
  labels:
    tenant: a
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.36
---
apiVersion: v1
kind: Namespace
metadata:
  name: tenant-b
  labels:
    tenant: b
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.36
```
以下完整的 tenant-a 示例包含旧 RoleBinding 中缺少的 Role、明确的工作负载权限、namespace 内流量和受限 DNS、ResourceQuota 及 LimitRange。应单独配置经过身份验证的 `tenant-a-users` 组，并创建经过审核的 tenant-b 等效资源：

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: tenant-workloads
  namespace: tenant-a
rules:
- apiGroups: ["apps"]
  resources: ["deployments", "statefulsets", "deployments/scale", "statefulsets/scale"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: ["batch"]
  resources: ["jobs", "cronjobs"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: [""]
  resources: ["services", "configmaps", "persistentvolumeclaims"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: [""]
  resources: ["pods", "pods/log", "events"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: tenant-a-access
  namespace: tenant-a
subjects:
- kind: Group
  name: tenant-a-users
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: tenant-workloads
  apiGroup: rbac.authorization.k8s.io
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: tenant-boundary
  namespace: tenant-a
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
  ingress:
  - from:
    - podSelector: {}
  egress:
  - to:
    - podSelector: {}
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - {protocol: UDP, port: 53}
    - {protocol: TCP, port: 53}
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: tenant-quota
  namespace: tenant-a
spec:
  hard:
    requests.cpu: "10"
    requests.memory: 20Gi
    limits.cpu: "20"
    limits.memory: 40Gi
    pods: "50"
    services: "20"
    persistentvolumeclaims: "30"
    secrets: "100"
    configmaps: "100"
---
apiVersion: v1
kind: LimitRange
metadata:
  name: tenant-limits
  namespace: tenant-a
spec:
  limits:
  - default:
      cpu: 500m
      memory: 512Mi
    defaultRequest:
      cpu: 100m
      memory: 256Mi
    type: Container
```
此策略需要兼容的强制执行引擎，并假定使用常规的 CoreDNS 标签；如果采用 NodeLocal DNSCache 路径，应相应调整。配额是准入限制，并非预留节点或带宽保证。工作负载创建操作可以使用 namespace 本地的 ServiceAccount 和 Secret，因此应通过准入控制限制这些资源，并将平台凭证保留在租户 namespace 之外。共享内核/control plane 资源仍需进行威胁模型审查。

**虚拟集群：**虚拟 API/control plane 可以隔离集群级配置，但运行在共享节点上的工作负载仍共用宿主机内核/CNI/CSI。经过审核的 vCluster 0.36.1 配置使用当前的 `sync.fromHost.nodes` 字段，并将宿主机节点同步保持为禁用状态。创建租户并不需要启用它；启用后可能暴露宿主机元数据。私有/专用节点架构有不同的前置条件和隔离属性。

将以下内容保存为 `vcluster-values.yaml`，并将存储类替换为获批且可用的存储类。使用由平台控制的独立宿主机 namespace，避免租户通过宿主机 RoleBinding 修改具有特权的 syncer/controller：

```yaml
sync:
  fromHost:
    nodes:
      enabled: false
controlPlane:
  statefulSet:
    persistence:
      volumeClaim:
        enabled: true
        storageClass: REPLACE_WITH_APPROVED_STORAGE_CLASS
        size: 5Gi
        retentionPolicy: Retain
    imagePullPolicy: IfNotPresent
```

```bash
helm repo add vcluster https://charts.loft.sh
helm repo update vcluster
helm template vcluster-tenant-a vcluster/vcluster --version 0.36.1 --kube-version 1.36.0 \
  --namespace vcluster-a-host -f vcluster-values.yaml > tenant-a-reviewed.yaml
helm template vcluster-tenant-b vcluster/vcluster --version 0.36.1 --kube-version 1.36.0 \
  --namespace vcluster-b-host -f vcluster-values.yaml > tenant-b-reviewed.yaml
```
检查渲染后的 RBAC、存储、资源请求、镜像和同步配置，然后通过经过审核的 Helm/GitOps 所有者进行部署。发布的 chart 默认会渲染 `vcluster-pro:0.36.1`；部署前应审核所选版本、功能可用性和许可。渲染并不能验证授权、持久性、集群启动或生产环境隔离。删除虚拟集群或其宿主机 namespace 前，应备份租户状态，并了解 PVC/PV 的保留行为。

**AWS 身份和治理：**使用租户专属的 IRSA 或受支持的 Pod Identity 角色，并为其设置范围受限的信任和资源权限。这些 AWS 身份与 Kubernetes 授权互为补充。SCP 为受其覆盖的成员账户主体设定权限上限；它既不会授予访问权限，也无法区分 Kubernetes namespace。

以下 S3 拒绝策略示例展示了仅附加到**租户 A 的成员账户/OU**、并针对经过审核的租户 B 存储桶的 SCP。不要将其附加到共享账户后，期待它能区分 A 与 B：

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "DenyTenantBStoreFromTenantAAccount",
    "Effect": "Deny",
    "Action": ["s3:*"],
    "Resource": [
      "arn:aws:s3:::amzn-s3-demo-tenant-b",
      "arn:aws:s3:::amzn-s3-demo-tenant-b/*"
    ]
  }]
}
```
SCP 不限制管理账户或服务关联角色，也不会直接限制无关的外部账户主体。仍然需要资源策略、IAM 权限和数据保护措施。这只是账户级防护措施之一，并非完整的租户隔离策略。应根据所选设计测试实际生效的访问权限及回滚/保留行为；本处未创建集群、虚拟集群或 SCP。

</details>


## 访问与生命周期检查

11. update-kubeconfig 会授予 Kubernetes 权限吗？
   * A) 会，自动授予 cluster-admin
   * B) 不会；它配置客户端，权限由 access entry/policy/RBAC 决定
   * C) 会，通过 CA 证书授予
   * D) 仅对新建 namespace 生效

<details>
<summary>显示答案</summary>

**答案：B) 不会；它配置客户端，权限由 access entry/policy/RBAC 决定**

初始管理权限取决于引导/工具配置。应保留已知管理员身份，并明确测试预期角色。

</details>

12. namespace RoleBinding 能缩小 EKS cluster-admin access policy 授予的权限范围吗？
   * A) 可以，RBAC 始终优先
   * B) 不可以，授权会累加
   * C) 可以，只要组名是 system:masters
   * D) 仅通过 kubectl --as 实现

<details>
<summary>显示答案</summary>

**答案：B) 不可以，授权会累加**

应使用预期的 access-policy 范围或自定义 RBAC 组。--as/--as-group 会强制使用 Kubernetes RBAC，但不会测试 EKS access policy 授予的权限。

</details>

13. Pod 处于 Running 状态之外，还需要检查什么？
   * A) 不需要检查其他内容
   * B) 只需要日志组名称
   * C) Readiness、rollout/健康状况和预期应用路径
   * D) 每个 Job 都必须永远保持运行

<details>
<summary>显示答案</summary>

**答案：C) Readiness、rollout/健康状况和预期应用路径**

Running 状态下的容器仍可能未就绪；已正确完成的 Job 可以处于 Succeeded 状态。应验证预期计算资源和实际 DNS/Service 行为。

</details>

14. 哪种 EKS 升级计划比较合适？
   * A) 使用最新的任意上游版本
   * B) 一次跨越两个次要版本
   * C) 使用 EKS 版本发布/就绪信息，并一次升级一个次要版本
   * D) 假设回滚会恢复所有持久化数据

<details>
<summary>显示答案</summary>

**答案：C) 使用 EKS 版本发布/就绪信息，并一次升级一个次要版本**

七天内的条件性回滚不会还原 etcd、工作负载或数据。应单独审核组件兼容性和备份。

</details>

15. 退役集群之前应做什么？
   * A) 立即删除所有 PVC
   * B) 按名称删除通用 IAM 角色
   * C) 先删除 VPC
   * D) 审核身份/所有权、备份/回收策略、依赖项、保护措施和能力

<details>
<summary>显示答案</summary>

**答案：D) 审核身份/所有权、备份/回收策略、依赖项、保护措施和能力**

应使用原始 IaC 所有者、明确且经过审核的资源以及完成检查。保留共享资源和恢复凭证。

</details>

## 参考资料

- [CloudWatch Observability add-on](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/install-CloudWatch-Observability-EKS-addon.html)
- [EKS access policies](https://docs.aws.amazon.com/eks/latest/userguide/access-policies.html)
- [EKS managed node groups](https://docs.aws.amazon.com/eks/latest/userguide/managed-node-groups.html)
- [EKS Cluster Autoscaler](https://docs.aws.amazon.com/eks/latest/best-practices/cas.html)
- [Kubernetes multi-tenancy](https://kubernetes.io/docs/concepts/security/multi-tenancy/)
- [vCluster 0.36.1 configuration](https://github.com/loft-sh/vcluster/blob/v0.36.1/chart/values.yaml)
- [SCP scope](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps.html)
- [EKS rollback](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html)
