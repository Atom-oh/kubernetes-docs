# Amazon EKS 升级测验

> **最后更新**：2026 年 9 月 12 日

本测验用于测试你对 Amazon EKS 集群升级流程、最佳实践、故障排除及相关注意事项的理解。

## 测验概览

- EKS 集群升级规划
- 控制平面升级
- 节点组升级
- 附加组件和组件升级
- 升级测试与验证
- 升级故障排除

## 选择题

### 1. 规划 Amazon EKS 集群升级时，最重要的第一步是什么？

- A. 立即升级控制平面
- B. 一次性升级所有工作负载
- C. 检查兼容性并制定测试和恢复计划
- D. 同时升级所有节点组

<details>
<summary>显示答案</summary>

**答案：C. 检查兼容性并制定测试和恢复计划**

在选择变更顺序之前，请检查目标 EKS 版本、API 变更和工作负载依赖项。兼容性清单有助于做出决策，但不能证明服务可用。

**兼容性检查**

- 检查清单、Helm 发布、API 客户端、CRD、转换/准入 Webhook 和运算符。还应包括 CNI/DNS、负载均衡器、服务网格、存储、监控、日志记录和备份组件。
- 使用 EKS 集群版本目录查询受支持的集群版本。`describe-addon-versions` 则会列出与某个 Kubernetes 版本兼容的附加组件。
- 在有代表性的时间窗口内查看 EKS Upgrade Insights 以及可用的审计/指标证据。在可查看的情况下，`apiserver_requested_deprecated_apis` 是相关的 API 服务器指标。没有指标序列、请求被拒绝或扫描结果为空，都不能证明不存在使用已弃用 API 的客户端。Insights 可能会在其观测窗口内保留历史使用情况。
- 对象当前的 `.apiVersion` 是其返回的表示形式，不一定是客户端最初请求的 API 版本。请检查已部署的配置、源代码和运行时调用方。

从[源指南](../../eks/08-eks-upgrades.md)保存 `eks-upgrade-preflight.py`，检查其前提条件，然后运行只读的账户/上下文/目标清单：

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${EXPECTED_ACCOUNT_ID:?}"
: "${KUBE_CONTEXT:?}"; : "${TARGET_VERSION:?}"
export CLUSTER_NAME AWS_REGION EXPECTED_ACCOUNT_ID KUBE_CONTEXT TARGET_VERSION
umask 077
python3 eks-upgrade-preflight.py > preflight.json
# Review this evidence and the workload/backup/capacity plan before a separate change step.
```

如果查询出错，该辅助程序会失败。请检查 `preflight.json` 中的每项发现；它既不会执行升级，也不会证明兼容性。使用当前 AWS 目录，选择比当前版本高一个、且受支持的次版本。

使用经过审核的 Pluto 版本扫描渲染后的清单、Helm 元数据和 last-applied 配置：

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${TARGET_VERSION:?}"; : "${MANIFEST_DIR:?}"
pluto detect-files --directory "$MANIFEST_DIR" --target-versions "k8s=v${TARGET_VERSION}.0" --output wide
pluto detect-helm --kube-context "$KUBE_CONTEXT" --target-versions "k8s=v${TARGET_VERSION}.0" --output wide
pluto detect-api-resources --kube-context "$KUBE_CONTEXT" --target-versions "k8s=v${TARGET_VERSION}.0" --output wide
```

如果之前的命令以非零状态退出，shell 会停止执行此代码块以便调查；处理该结果后，再完成剩余检查。API 资源检测依赖已存储的注解，无法观测所有运行时请求。kube-no-trouble 项目提供的是 `kubent` 二进制文件，而不是 `kubectl-no-trouble`。

**历史 API 移除示例**（迁移历史，并非当前 EKS 升级目标）：

| Kubernetes 发布版本 | 移除的服务 API / 迁移 |
| --- | --- |
| 1.22 | 移除了多个 beta API，包括 `networking.k8s.io/v1beta1` Ingress；迁移到稳定 API 及其字段架构 |
| 1.25 | `policy/v1beta1` PodSecurityPolicy：迁移策略实施方式。`batch/v1beta1` CronJob → `batch/v1` |
| 1.26 | `autoscaling/v2beta2` HPA → `autoscaling/v2`；移除了 flow-control `v1beta1` |
| 1.27 | `storage.k8s.io/v1beta1` CSIStorageCapacity → `storage.k8s.io/v1` |
| 1.29 / 1.32 | 分别移除了 FlowSchema / PriorityLevelConfiguration `v1beta2` / `v1beta3`；使用 `flowcontrol.apiserver.k8s.io/v1`，并迁移字段/默认值 |

对于 kubelet 1.25 及更高版本，上游策略允许 kubelet 最多比 API 服务器旧三个次版本，但 kubelet 绝不能比 API 服务器新；较旧的 kubelet 最多只能旧两个次版本。在高可用升级期间，API 服务器版本混合会进一步缩小此范围。这是支持边界，并不能证明每个附加组件或应用都能正常工作。保守的 EKS 准备方式是在下一次控制平面升级前，先让节点版本与**当前**控制平面版本一致。

**演练和计划模板**

使用经过审核的基础设施定义准备一个独立环境，其中包含有代表性的网络、IAM、计算类型、数据和控制器。记录与生产环境的差异、成本和清理责任方。从开发/暂存环境开始，测试业务功能、扩缩容、恢复和告警；不要在生产环境中顺带进行故障注入。旧的 1.27→1.28 示例仅供历史参考，并非当前的配置建议。

```markdown
# EKS upgrade plan: fill from evidence, not assumed results

- Account / Region / cluster ARN / kube context: TBD
- Current / target minor and EKS support status: TBD
- Node groups, Fargate, Auto Mode, hybrid nodes: inventory required
- Add-on / controller / CRD / webhook versions and owner: TBD
- Compatibility evidence, observation window and unresolved findings: TBD
- Backup coverage, application consistency, restore test and RPO/RTO: TBD
- Subnet IPs, EC2 quotas, placement, surge capacity and cost: TBD
- Rehearsal environment and differences from production: TBD

## Ordered change gates

- [ ] Align nodes to the current control-plane version; verify supported skew
- [ ] Complete API migrations and any required bridge add-on versions
- [ ] Complete a representative non-production rehearsal
- [ ] Upgrade the control plane by one minor; verify the exact update ID
- [ ] Upgrade nodes/add-ons in their reviewed dependency order
- [ ] Verify workloads and monitor agreed SLOs before retiring old capacity

## Test coverage and evidence

- [ ] Deployments: create, readiness, rollout and scaling
- [ ] StatefulSets / PVCs: write, reschedule, read and restore
- [ ] Services, DNS, Ingress / Gateway and external dependencies
- [ ] Jobs / CronJobs, operators, CRDs and admission webhooks
- [ ] API latency, Pod startup, network and resource baselines
- [ ] Controlled node/network/resource-pressure recovery in a test environment
- [ ] Alert delivery and incident ownership
- Result / timestamp / environment / evidence location: NOT RUN

## Recovery decision

- Stop criteria and incident owner: TBD
- Previous minor, upgrade completion time and 7-day rollback deadline: TBD
- Rollback eligibility, compute-type order and add-on compatibility: TBD
- Data restore or forward-fix procedure when version rollback is unsuitable: TBD
```

记录观测结果，不要预先填入“全部兼容”或“没有 CRD 变更”。版本回滚不会恢复应用数据；问题 5 介绍回滚资格和计算类型顺序。A、B 和 D 都跳过了证据，或将变更范围扩大到难以诊断和恢复的程度。

来源：[API 迁移指南](https://kubernetes.io/docs/reference/using-api/deprecation-guide/)、[版本偏差策略](https://kubernetes.io/releases/version-skew-policy/)、[EKS 升级](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html)、[Pluto](https://pluto.docs.fairwinds.com/)、[kube-no-trouble](https://github.com/doitintl/kube-no-trouble)。

</details>

### 2. 完成必要的节点版本对齐后，原地升级到下一个次版本的正确顺序是什么？

- A. 在 API 服务器仍处于较旧次版本时，将 kubelet 升级到目标次版本
- B. 将控制平面升级到目标次版本，然后分阶段升级到目标版本的节点组
- C. 同时启动所有控制平面和目标版本节点变更
- D. 每次升级次版本都必须创建新集群

<details>
<summary>显示答案</summary>

**答案：B. 将控制平面升级到目标次版本，然后分阶段升级到目标版本的节点组**

让节点版本与**当前**控制平面次版本一致属于准备工作。只有在控制平面支持**目标**次版本后，才能将节点升级到该版本。EKS 每次只升级一个次版本。受支持的版本偏差不保证应用兼容性。请遵循每个组件的依赖要求，包括控制平面变更前可能需要的桥接附加组件版本。

**准备与执行**

1. 确认账户、上下文、当前/目标版本支持情况、集群/节点健康状况、Insights、子网 IP 容量和访问权限。规划替换容量和工作负载中断控制。
2. 验证备份和恢复。EKS 用户无法针对托管控制平面运行 `etcdctl`。`kubectl get all` 会遗漏许多资源和持久数据。使用适当配置的 AWS Backup EKS 或 Velero/应用备份，并测试其覆盖范围和恢复能力。
3. 查看问题 1 中的预检查结果。在此独立变更步骤之前，为经审核的目标保存[源指南](../../eks/08-eks-upgrades.md)中的 `eks-wait-update.py`，并确保没有冲突的更新。

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the reviewed cluster}"
: "${AWS_REGION:?Set the reviewed Region}"
: "${TARGET_VERSION:?Set the next supported EKS minor version}"
umask 077
aws eks update-cluster-version \
  --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --kubernetes-version "$TARGET_VERSION" --output json --no-cli-pager \
  > control-plane-update.json
UPDATE_ID=$(jq -er '.update.id | select(type == "string" and length > 0)' control-plane-update.json)
export CLUSTER_NAME AWS_REGION UPDATE_ID
unset NODEGROUP_NAME ADDON_NAME
python3 eks-wait-update.py
```

轮询程序会跟踪此确切请求。只有 `Successful` 才表示成功；失败、取消、未知状态和 API 错误都会使流程停止。客户端超时不会取消 AWS 操作。仅有 `ACTIVE` 状态不能证明此更新成功，而且 `aws eks wait update-successful` 并不是 EKS CLI waiter。

或者，`eksctl upgrade cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" --version "$TARGET_VERSION"` 会预览变更；`--approve` 会启动变更。请选择一个负责人和执行路径，不要同时提交 CLI 和 Terraform 变更。

**请求成功后**

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${KUBE_CONTEXT:?}"
aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query 'cluster.{version:version,status:status,platformVersion:platformVersion}'
aws eks list-nodegroups --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION"
kubectl --context "$KUBE_CONTEXT" get --raw='/readyz'
kubectl --context "$KUBE_CONTEXT" get nodes -o wide
kubectl --context "$KUBE_CONTEXT" get pods -n kube-system
kubectl --context "$KUBE_CONTEXT" get events -A --sort-by='.metadata.creationTimestamp'
```

API 就绪端点需要相应权限，而且只是一个信号。请检查实际工作负载、DNS 和控制器，而不要依赖已过时的 `ComponentStatus` 对象或假定存在的托管 etcd Pod。纯 Auto Mode 使用节点级 CoreDNS；混合集群会为非 Auto 节点保留 DNS。缺少标准的 `aws-node`、kube-proxy 或 CoreDNS Deployments，并不一定是 Auto Mode 故障。`kubectl top` 需要 Metrics Server；指标是否可用与请求是否成功是两回事。

按照经审核的节点组/金丝雀以及所需的附加组件顺序继续操作，并验证每个阶段。控制平面升级后，Auto Mode 会管理节点。现有 Fargate Pods 会保留其 kubelet 版本；请协调由相应负责人发起的替换和可用性保障。

**可用性和耗时**

旧的“20–30 分钟”估算没有提供测量依据，仅作为历史规划示例保留，并不保证实际耗时。应根据演练结果预留变更窗口。API 服务器替换时，API 客户端必须重新连接。现有容器可能会继续运行，但依赖 API 的控制器和应用仍可能受到影响。正常的控制平面升级一旦启动，就无法暂停或取消。请保留更新 ID/错误信息，并视需要联系 AWS Support；之后的版本回滚有单独的资格要求。

**Terraform 所有权示例**

修改现有资源/模块，保留其余设置和依赖关系。此处只是片段，并非完整定义，也不是为现有集群创建第二个资源：

```hcl
# Fragment of the existing, state-managed cluster resource.
resource "aws_eks_cluster" "main" {
  name     = var.cluster_name
  role_arn = var.cluster_role_arn
  version  = var.target_version

  vpc_config {
    subnet_ids         = var.subnet_ids
    security_group_ids = [var.cluster_security_group_id]
  }

  lifecycle {
    prevent_destroy = true
  }
}
```

提供现有 IAM、子网和安全组值以及经过审核的目标版本。检查 provider plan，确认没有意外替换或无关变更。`prevent_destroy` 保护的是 Terraform 销毁操作，并不能防止服务中断。空的 `ignore_changes = []` 既不会等待升级，也不会验证升级；provider 有自己的 waiter/超时设置。IaC 超时不会取消服务操作，Git revert 也不等于 EKS 版本回滚。变更后请使用问题 6 中有时限的验证方式。本次审查未对在线集群执行任何操作。

A 会使 kubelet 版本高于 API 服务器。C 会取消验证关卡。D 不正确：迁移到新集群是可选方案，而且有不同的流量/数据迁移成本。

来源：[EKS 更新流程](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html)、[EKS 备份](https://docs.aws.amazon.com/eks/latest/userguide/integration-backup.html)、[Terraform EKS 资源](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eks_cluster)。

</details>

### 3. 哪种方法有助于可控地升级 EKS 节点组？

- A. 同时终止所有节点
- B. 分阶段更新托管节点组，或执行经过验证的蓝绿迁移
- C. 无限期保留节点版本不变
- D. 在托管节点上逐个替换 kubelet 二进制文件

<details>
<summary>显示答案</summary>

**答案：B. 分阶段更新托管节点组，或执行经过验证的蓝绿迁移**

请根据工作负载对中断的容忍度、容量、有状态存储和计算资源负责人来选择策略。托管更新和蓝绿迁移都不能保证服务不中断。

**托管节点组**

`DEFAULT` 更新策略会先创建替换容量，再移除旧节点；`MINIMAL` 则先移除旧容量。`maxUnavailable` 用于限制并发不可用数量。正常的滚动驱逐流程会遵循 PDB，但强制更新可能绕过 PDB。这些策略与控制台中的滚动/强制选项不同。更新失败**不**代表会自动回滚整个节点组。

保存源指南中的 `eks-wait-update.py`，并完成问题 1 中的账户/上下文/容量检查。对于使用 EKS 优化 AMI 的现有节点组，请明确选择 Kubernetes 版本和兼容的 AMI 版本：

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${NODEGROUP_NAME:?}"
: "${TARGET_VERSION:?Set the reviewed target, no newer than the control plane}"
: "${TARGET_AMI_RELEASE:?Set the reviewed EKS-optimized AMI release}"
umask 077
aws eks describe-nodegroup --cluster-name "$CLUSTER_NAME" --nodegroup-name "$NODEGROUP_NAME" \
  --region "$AWS_REGION" --output json > nodegroup-before.json
if jq -e '.nodegroup.amiType == "CUSTOM"' nodegroup-before.json >/dev/null; then
  echo "Use the custom launch-template path for this node group" >&2
  exit 1
fi
aws eks update-nodegroup-version \
  --cluster-name "$CLUSTER_NAME" --nodegroup-name "$NODEGROUP_NAME" --region "$AWS_REGION" \
  --kubernetes-version "$TARGET_VERSION" --release-version "$TARGET_AMI_RELEASE" \
  --output json > nodegroup-update.json
UPDATE_ID=$(jq -er '.update.id | select(type == "string" and length > 0)' nodegroup-update.json)
export CLUSTER_NAME AWS_REGION UPDATE_ID NODEGROUP_NAME
unset ADDON_NAME
python3 eks-wait-update.py
```

如果请求或轮询失败，此操作会停止。在继续更新下一个节点组之前，请检查实际节点版本/就绪情况、Pod 调度位置、事件和应用 SLO。对于自定义 AMI，请使用经过审核的新版本**同一个原始启动模板**，并省略 `--kubernetes-version` 和 `--release-version`；按照源指南中的独立自定义 AMI 流程操作。不要在原地编辑 kubelet 软件包，并假定 AMI/运行时/引导配置也已升级。

`eksctl upgrade nodegroup` 使用 `--kubernetes-version`；`eksctl create nodegroup` 使用 `--version`。创建节点组时，请将经过审核的子网、IAM、AMI、标签和污点保留在现有集群配置中，不要使用不受支持的 `--taints` 标志，也不要依赖不完整的单行命令方案。

**蓝绿迁移步骤**

1. 保留蓝色容量。由基础设施负责人创建绿色容量，版本不得高于控制平面，并匹配 AMI/架构、私有网络和足够的配额/IP/AZ 容量。
2. 确认绿色节点为 Ready，并测试 DNS、网络、存储和工作负载依赖项。在适当的工作负载能够容忍污点之前，将绿色节点设为带污点状态，以便运行金丝雀。
3. 分阶段迁移工作负载 Pod 模板。首选亲和性只是偏好，不会迁移现有 Pod。如果必须指定调度位置，请使用明确的选择条件，并由工作负载负责人启动受控滚动更新。
4. 检查每个旧节点上的工作负载，然后逐个执行 drain。驱逐失败时应停止；不要在 drain 失败后继续终止节点。
5. 只有在审查了工作负载/数据/流量证据和恢复窗口后，才能退役蓝色容量。弹出“是”提示或看到节点列表为 Ready，都不能证明迁移已完成。

以下是一个完整的**独立金丝雀样例配置**，并非现有应用的替换清单。请有计划地准备其命名空间。由于配置了必需的主机名反亲和性，至少需要三个符合条件的 Linux 绿色节点。容忍设置允许 Pod 使用带污点的节点；节点选择器则用于选择绿色节点。应用镜像/配置、中断策略和滚动更新参数需另行调整。

```yaml
# Independent fixture in an explicitly prepared test namespace.
apiVersion: apps/v1
kind: Deployment
metadata:
  name: upgrade-canary
  namespace: upgrade-canary
spec:
  replicas: 3
  selector:
    matchLabels:
      app: upgrade-canary
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 0
      maxUnavailable: 1
  template:
    metadata:
      labels:
        app: upgrade-canary
    spec:
      automountServiceAccountToken: false
      nodeSelector:
        kubernetes.io/os: linux
        example.com/upgrade: green
      tolerations:
        - key: example.com/upgrade
          operator: Equal
          value: green
          effect: NoSchedule
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            - labelSelector:
                matchLabels:
                  app: upgrade-canary
              topologyKey: kubernetes.io/hostname
      securityContext:
        runAsNonRoot: true
        runAsUser: 65532
        runAsGroup: 65532
        fsGroup: 65532
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: http
          image: docker.io/library/busybox@sha256:73aaf090f3d85aa34ee199857f03fa3a95c8ede2ffd4cc2cdb5b94e566b11662
          command: [sh, -ec]
          args:
            - mkdir -p /tmp/www; printf 'ok\n' > /tmp/www/index.html; exec httpd -f -p 8080 -h /tmp/www
          ports:
            - name: http
              containerPort: 8080
          readinessProbe:
            httpGet:
              path: /
              port: http
            periodSeconds: 5
          resources:
            requests:
              cpu: 10m
              memory: 16Mi
            limits:
              cpu: 100m
              memory: 64Mi
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: [ALL]
          volumeMounts:
            - name: tmp
              mountPath: /tmp
      volumes:
        - name: tmp
          emptyDir: {}
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: upgrade-canary
  namespace: upgrade-canary
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: upgrade-canary
```

Deployment 自身的滚动更新由其策略控制，而不是由 PDB 控制。PDB 管理的是自愿驱逐，不会管理常规 Deployment/ReplicaSet 缩容，也不会管理所有基础设施终止操作。如果合适容量消失，必需的反亲和性可能会阻止调度。本示例不声称已运行任何镜像或集群。

对于一个经过审核的旧节点，源指南中有时限的 drain 命令会保留对非托管 Pod 和 `emptyDir` 数据的保护：

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?Set the reviewed cluster context}"
: "${NODE_NAME:?Set one reviewed old node}"
kubectl --context "$KUBE_CONTEXT" get node "$NODE_NAME" -o wide
kubectl --context "$KUBE_CONTEXT" get node "$NODE_NAME" \
  -o jsonpath='{.spec.providerID}{"\n"}'
kubectl --context "$KUBE_CONTEXT" get pods --all-namespaces \
  --field-selector "spec.nodeName=$NODE_NAME" -o wide
# Stop on failure. Do not terminate the instance or delete the node group here.
kubectl --context "$KUBE_CONTEXT" drain "$NODE_NAME" --ignore-daemonsets --timeout=10m
```

drain 失败可能会使节点处于 cordon 状态或部分排空状态；请谨慎调查并恢复。不要只是为了完成迁移而添加 `--force`、`--delete-emptydir-data` 或 `--disable-eviction`。

**Terraform 蓝绿示例**

保留现有资源地址/设置。这些 EKS 优化 AMI 片段会让**两个**节点组都保持正容量；绿色节点的污点与上述金丝雀配置相匹配。

```hcl
# Existing blue resource address is retained; green is separate capacity.
# Inputs describe reviewed EKS-optimized AMIs, not a custom launch template.
variable "capacity" {
  type    = object({ desired = number, min = number, max = number })
  default = { desired = 3, min = 3, max = 6 }
  validation {
    condition = (
      var.capacity.min >= 1 &&
      var.capacity.desired >= var.capacity.min &&
      var.capacity.max >= var.capacity.desired &&
      alltrue([for n in values(var.capacity) : floor(n) == n])
    )
    error_message = "Retain positive integer capacity: 1 <= min <= desired <= max."
  }
}

resource "aws_eks_node_group" "blue" {
  cluster_name    = var.cluster_name
  node_group_name = "blue-nodegroup"
  node_role_arn   = var.node_role_arn
  subnet_ids      = var.private_subnet_ids
  version         = var.blue_version
  release_version = var.blue_ami_release
  ami_type        = var.ami_type
  instance_types  = var.instance_types
  scaling_config {
    desired_size = var.capacity.desired
    min_size     = var.capacity.min
    max_size     = var.capacity.max
  }
  labels = { "example.com/upgrade" = "blue" }
  update_config {
    max_unavailable = 1
  }
  lifecycle {
    ignore_changes = [scaling_config[0].desired_size]
  }
}

resource "aws_eks_node_group" "green" {
  cluster_name    = var.cluster_name
  node_group_name = "green-nodegroup"
  node_role_arn   = var.node_role_arn
  subnet_ids      = var.private_subnet_ids
  version         = var.green_version
  release_version = var.green_ami_release
  ami_type        = var.ami_type
  instance_types  = var.instance_types
  scaling_config {
    desired_size = var.capacity.desired
    min_size     = var.capacity.min
    max_size     = var.capacity.max
  }
  labels = { "example.com/upgrade" = "green" }
  taint {
    key    = "example.com/upgrade"
    value  = "green"
    effect = "NO_SCHEDULE"
  }
  update_config {
    max_unavailable = 1
  }
  lifecycle {
    ignore_changes = [scaling_config[0].desired_size]
  }
}
```

提供现有集群/角色/子网、兼容的实例类型/AMI 系列，以及分别经过审核的蓝色/绿色版本和 AMI 发布版本。绿色版本必须已受到控制平面支持。`desired_size` 忽略规则假定此字段由自动扩缩器管理；如果 Terraform 是预定负责人，请移除此规则。最小值/最大值变更仍会生效，而且更改托管节点组的扩缩配置**不会**遵循 PDB。不要使用布尔开关在创建绿色容量时将蓝色容量缩减为零，也不要将 `max_size = 0`（无效）。节点创建、工作负载迁移和节点退役属于不同的变更；仅靠 Terraform 依赖关系无法证明工作负载已就绪。

请事先制定恢复标准。只要保留蓝色容量，工作负载调度位置就可能可逆，但仍受 API/数据兼容性限制。控制平面回滚和 MNG 版本回滚还需满足问题 5 中的额外条件。A、C 和 D 会扩大中断范围、导致版本偏差累积，或绕过托管替换生命周期。

来源：[托管节点更新](https://docs.aws.amazon.com/eks/latest/userguide/update-managed-node-group.html)、[更新行为](https://docs.aws.amazon.com/eks/latest/userguide/managed-node-update-behavior.html)、[PDB](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/)、[Terraform 节点组](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eks_node_group)。

</details>

### 4. EKS 升级期间，管理附加组件的正确方法是什么？

- A. 忽略附加组件升级
- B. 不考虑兼容性，在控制平面升级前升级所有附加组件
- C. 选择兼容版本，并遵循每个组件的依赖关系和桥接版本顺序
- D. 移除所有附加组件并重新安装

<details>
<summary>显示答案</summary>

**答案：C. 选择兼容版本，并遵循每个组件的依赖关系和桥接版本顺序**

并不存在适用于所有情况的“控制平面升级后再升级所有附加组件”规则。有些组件需要先升级到一个同时兼容新旧控制平面版本的中间版本；其他组件则应在控制平面升级后升级。请查看每个版本的 Kubernetes、架构、计算类型、API 支持情况和升级路径。EKS 托管附加组件不会随控制平面版本自动升级，而“托管”也不意味着会自动安装每个安全版本。

**检查、选择并保留配置**

对于一个已安装且由你负责的托管附加组件，请检查当前状态、兼容的候选版本，以及经审核候选版本的架构。数组中的第一个元素并不意味着“最新兼容版本”。

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${ADDON_NAME:?}"
: "${TARGET_VERSION:?Set the Kubernetes version for this stage}"
umask 077
aws eks describe-addon --cluster-name "$CLUSTER_NAME" --addon-name "$ADDON_NAME" \
  --region "$AWS_REGION" --output json > addon-before.json
aws eks describe-addon-versions --addon-name "$ADDON_NAME" \
  --kubernetes-version "$TARGET_VERSION" --region "$AWS_REGION" \
  --output json > addon-candidates.json
# Select ADDON_VERSION after reviewing compatibility, architecture, compute type, and upgrade path.
: "${ADDON_VERSION:?Set the reviewed add-on version}"
aws eks describe-addon-configuration --addon-name "$ADDON_NAME" \
  --addon-version "$ADDON_VERSION" --region "$AWS_REGION" \
  --output json > addon-schema.json
jq -r '.addon.configurationValues // "{}"' addon-before.json > addon-config-candidate.json
```

`addon-before.json` 包含版本/配置/身份信息。单个 `aws-node` ConfigMap 并不是完整的 CNI 备份；DaemonSet 设置、自定义资源和 IAM/Pod Identity 也可能需要考虑。请保护好证据文件。`addon-config-candidate.json` 只是待审核的输入，并不保证自动成为有效的目标配置。请根据新架构合并预期设置，并检查被移除/设为默认值的字段和发行说明。

完成审核后，请使用源指南中用于跟踪确切请求的轮询程序和完整目标配置文件：

```bash
umask 077
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${ADDON_NAME:?}"; : "${ADDON_VERSION:?}"
: "${REVIEWED_ADDON_CONFIG_FILE:?Provide the complete reviewed target configuration JSON}"
aws eks update-addon --cluster-name "$CLUSTER_NAME" --addon-name "$ADDON_NAME" \
  --addon-version "$ADDON_VERSION" --region "$AWS_REGION" \
  --configuration-values "file://$REVIEWED_ADDON_CONFIG_FILE" \
  --resolve-conflicts PRESERVE --output json > addon-update.json
UPDATE_ID=$(jq -er '.update.id | select(type == "string" and length > 0)' addon-update.json)
export CLUSTER_NAME AWS_REGION UPDATE_ID ADDON_NAME
unset NODEGROUP_NAME
python3 eks-wait-update.py
aws eks describe-addon --cluster-name "$CLUSTER_NAME" --addon-name "$ADDON_NAME" \
  --region "$AWS_REGION" --output json
```

`PRESERVE` 用于处理现有字段冲突；但这不保证显式配置负载会被完全合并、接受或在功能上正确。`NONE` 遇到冲突时会失败；`OVERWRITE` 可能会用 EKS 默认值替换自定义项。不要将 overwrite 用作自动恢复捷径。在处理下一个依赖项之前，请检查更新是否成功，**并且**确认附加组件健康状况/工作负载行为正常；等待 30 秒并不能确认操作已完成。

**特定组件检查**

| 组件 | 继续操作前的检查 |
| --- | --- |
| VPC CNI | 受支持的升级路径、IP 分配、节点/Pod 网络、自定义网络和 IAM |
| CoreDNS | DNS 解析、Corefile/架构变更、调度/就绪状况和 PDB 设置 |
| kube-proxy | Kubernetes 版本偏差、Service 可达性和集群的实际数据平面 |
| Cluster Autoscaler | 受支持的 Kubernetes 次版本、发现/IAM 和扩缩容所有权 |
| Metrics Server | 受支持的版本、APIService 可用性和 kubelet TLS/访问 |
| Load Balancer Controller / ExternalDNS / mesh | 控制器/chart/CRD/API 兼容性、IAM、Webhook 和流量行为 |

纯 Auto Mode 提供节点级 DNS/网络，不需要以同样的方式安装这些标准节点附加组件。混合集群必须保留非 Auto 节点所需的组件，包括 CoreDNS Deployment 覆盖范围。在升级或移除任何内容前，请先确认其所有者。

**由 Terraform 管理的附加组件**

在现有状态管理资源中使用经过审核的版本/配置映射，并保留其 IAM/Pod Identity 设置。以下片段适用于标准节点附加组件，并非适用于所有 Auto Mode 安装方式：

```hcl
# Fragments of existing, imported/state-managed standard-node add-ons.
# Preserve each resource's existing IAM/Pod Identity settings as applicable.
resource "aws_eks_addon" "vpc_cni" {
  cluster_name                = var.cluster_name
  addon_name                  = "vpc-cni"
  addon_version               = var.addon_versions["vpc-cni"]
  configuration_values        = file(var.addon_config_files["vpc-cni"])
  resolve_conflicts_on_create = "NONE"
  resolve_conflicts_on_update = "PRESERVE"
}

resource "aws_eks_addon" "coredns" {
  cluster_name                = var.cluster_name
  addon_name                  = "coredns"
  addon_version               = var.addon_versions["coredns"]
  configuration_values        = file(var.addon_config_files["coredns"])
  resolve_conflicts_on_create = "NONE"
  resolve_conflicts_on_update = "PRESERVE"
}

resource "aws_eks_addon" "kube_proxy" {
  cluster_name                = var.cluster_name
  addon_name                  = "kube-proxy"
  addon_version               = var.addon_versions["kube-proxy"]
  configuration_values        = file(var.addon_config_files["kube-proxy"])
  resolve_conflicts_on_create = "NONE"
  resolve_conflicts_on_update = "PRESERVE"
}
```

当前 provider 将 `resolve_conflicts_on_create` 和 `resolve_conflicts_on_update` 分开设置。创建时不能使用 `PRESERVE`；`NONE` 会有意显示迁移冲突。不要为了更新附加组件而添加重复的集群资源。只更改当前阶段计划更新的组件；列出三个独立资源并不能形成安全的升级顺序。资源销毁或设置变更需要单独审核。

**自管理 Helm 发布**

使用现有发布的负责人、经过审核的 chart 引用/版本和已迁移的 values。安装、所有权迁移和升级是不同的操作。保留 CRD、身份、ServiceAccount、资源/调度设置和当前行为：

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${RELEASE:?}"; : "${ADDON_NAMESPACE:?}"
: "${CHART_REF:?Set the verified repository/chart or OCI reference}"
: "${CHART_VERSION:?Set a reviewed compatible chart version}"
: "${REVIEWED_VALUES_FILE:?Set the complete reviewed target values file}"
umask 077
helm get values "$RELEASE" --namespace "$ADDON_NAMESPACE" --kube-context "$KUBE_CONTEXT" \
  --all > addon-values-before.yaml
helm show values "$CHART_REF" --version "$CHART_VERSION" > addon-values-defaults.yaml
# Merge/migrate values and handle CRDs/IAM through the owner before this step.
helm upgrade "$RELEASE" "$CHART_REF" --version "$CHART_VERSION" \
  --namespace "$ADDON_NAMESPACE" --kube-context "$KUBE_CONTEXT" \
  -f "$REVIEWED_VALUES_FILE" --wait --timeout 15m
```

请在执行最后一条命令前准备好经过审核的 values。`--wait` 不能证明应用 SLO 正常，也无法处理所有 CRD 迁移。不要批量安装第二个控制器，也不要在升级期间更改无关的自动扩缩器标志。验证每个发布的 Pods、事件和代表性功能；记录失败情况，不要无条件打印完成信息。

A 忽略了安全与兼容性维护。B 可能会在控制平面仍处于旧版本时安装不兼容的版本。D 会不必要地丢弃所有权/配置，并可能中断网络或 DNS。

来源：[更新 EKS 附加组件](https://docs.aws.amazon.com/eks/latest/userguide/updating-an-add-on.html)、[Auto Mode 网络](https://docs.aws.amazon.com/eks/latest/userguide/auto-networking.html)、[Terraform 附加组件](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eks_addon)、[Helm upgrade](https://helm.sh/docs/helm/helm_upgrade/)。

</details>

### 5. 在 EKS 升级期间出现问题时，最有效的方法是什么？

- A. 立即创建新集群
- B. 不收集证据，只依赖 AWS Support
- C. 使用系统化的故障排除、日志和假设验证
- D. 忽略升级问题

<details>
<summary>显示答案</summary>

**答案：C. 使用系统化的故障排除、日志和假设验证**

明确症状、开始时间、受影响的工作负载和业务影响，并将这些信息与具体变更相关联。先收集证据，再验证假设。只有在审查预期影响后，才能实施有针对性的修正；之后验证是否恢复，并记录预防措施。可能原因并不等于已确认的根本原因。

**只读诊断**

确认账户/上下文和确切的操作 ID。以下收集程序会在查询前验证操作类型，并使用新的私有证据目录。如果查询失败，程序会停止；已写入的文件只是部分证据，并不代表诊断成功。

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${KUBE_CONTEXT:?}"
: "${UPDATE_ID:?Set the exact affected update ID}"
: "${ISSUE_KIND:?Set control-plane, nodegroup, or addon}"
: "${EVIDENCE_PARENT:?Set an existing private evidence directory}"
args=(--name "$CLUSTER_NAME" --region "$AWS_REGION" --update-id "$UPDATE_ID")
case "$ISSUE_KIND" in
  control-plane) ;;
  nodegroup) : "${NODEGROUP_NAME:?}"; args+=(--nodegroup-name "$NODEGROUP_NAME") ;;
  addon) : "${ADDON_NAME:?}"; args+=(--addon-name "$ADDON_NAME") ;;
  *) echo "Unknown ISSUE_KIND" >&2; exit 2 ;;
esac
umask 077
EVIDENCE_DIR=$(mktemp -d "$EVIDENCE_PARENT/eks-upgrade-diagnosis.XXXXXXXX")
printf 'Evidence directory: %s\n' "$EVIDENCE_DIR"
aws eks describe-update "${args[@]}" --output json --no-cli-pager \
  > "$EVIDENCE_DIR/update.json" 2> "$EVIDENCE_DIR/update.stderr"
aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query 'cluster.{version:version,status:status,health:health,logging:logging}' \
  --output json --no-cli-pager > "$EVIDENCE_DIR/cluster.json"
kubectl --context "$KUBE_CONTEXT" get nodes -o wide > "$EVIDENCE_DIR/nodes.txt"
kubectl --context "$KUBE_CONTEXT" get pods -A -o wide > "$EVIDENCE_DIR/pods.txt"
kubectl --context "$KUBE_CONTEXT" get events -A --sort-by='.metadata.creationTimestamp' \
  > "$EVIDENCE_DIR/events.txt"
printf 'Snapshots collected; review errors and workload evidence before changing anything.\n'
```

对于节点组或附加组件操作，还应检查该资源的 `health.issues`，并通过 `describe-nodegroup` 或 `describe-addon` 检查其版本/配置。根据具体情况检查节点 ProviderID、EC2 状态、IAM/引导配置/AMI/网络和调度约束。不要仅凭更新的 `Failed` 状态推断原因。

在有时限的窗口内读取现有控制平面日志：

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${KUBE_CONTEXT:?}"
: "${START_TIME_MS:?Set the reviewed start timestamp in epoch milliseconds}"
: "${END_TIME_MS:?Set the reviewed analysis-window end timestamp}"
aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query 'cluster.logging' --output json --no-cli-pager
# Read existing logs; enabling logging is a separate change and does not backfill history.
aws logs filter-log-events --region "$AWS_REGION" \
  --log-group-name "/aws/eks/$CLUSTER_NAME/cluster" \
  --start-time "$START_TIME_MS" --end-time "$END_TIME_MS" \
  --max-items 200 --output json --no-cli-pager
```

启用日志记录是一项单独的集群变更，不会补录之前发生的事件。日志组不存在、权限错误或查询结果为空，都表示可见性受限。如果存在相关 Pod，请明确检查：

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${AFFECTED_NAMESPACE:?}"; : "${AFFECTED_POD:?}"
kubectl --context "$KUBE_CONTEXT" -n "$AFFECTED_NAMESPACE" describe pod "$AFFECTED_POD"
kubectl --context "$KUBE_CONTEXT" -n "$AFFECTED_NAMESPACE" logs "$AFFECTED_POD" \
  --all-containers=true --prefix=true --since=15m --tail=100
```

Pod 代理日志并不包含所有主机 kubelet/运行时日志。Auto Mode、Fargate 和标准 EC2 的诊断访问方式各不相同。请保护好快照，并在与 AWS Support 分享之前对敏感配置进行脱敏；避免不加区分地导出整个集群。

| 症状 | 通过证据检验的假设 |
| --- | --- |
| 控制平面请求失败 | 确切的更新错误、前提条件、子网 IP/安全组和 AWS 服务端故障 |
| 节点未 Ready / Pod Pending | AMI/引导配置、EC2 容量、IAM/网络/CNI、污点、亲和性、PVC 拓扑或资源 |
| 附加组件 CrashLoopBackOff | 配置/架构、身份、镜像/启动、资源或版本兼容性 |
| 应用 API 错误 | 已移除 API 的调用方、准入/转换 Webhook、权限或应用回归 |

重试、删除节点组或覆盖附加组件配置都不算诊断。附加组件恢复需要兼容的版本**和**经过审核的配置/身份，并按照问题 4 中的方法监控确切更新。

**当前 EKS 回滚条件**

当前 EKS 指南支持原地回滚控制平面。这与恢复应用数据或替换故障节点是不同的操作。

- 必须在原地升级完成后七天内，回滚到紧邻的上一个次版本。以当前版本创建的集群不符合资格；不支持连续回滚到更早的次版本。
- 目标版本必须仍受支持。扩展支持目标需要使用 `EXTENDED` 策略，并产生相应费用。扩展支持期结束时发生的自动升级无法回滚；标准支持结束时的情况需满足文档规定的策略条件。
- 检查 `ACTIVE` 状态、冲突更新、向后不兼容的功能和其他前提条件。`ROLLBACK_READINESS` Insights 中的 `ERROR`/`UNKNOWN` 会阻止回滚；`WARNING` 仅供参考。`--force` 会绕过 Insights 检查，但不会绕过资格/前提条件或 Auto Mode 中断控制。这与普通升级中对 Insights 强制检查暂时回滚的 `--force` 用法不同。

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${KUBE_CONTEXT:?}"
aws eks list-insights --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --filter '{"categories":["ROLLBACK_READINESS"]}' --output json --no-cli-pager
kubectl --context "$KUBE_CONTEXT" get nodes -o wide
```

使用 `describe-insight --id "$INSIGHT_ID"` 检查单项发现。不要将 Insights 列表为空视为所有前提条件均已满足的证明。

| 计算类型 | 顺序与限制 |
| --- | --- |
| 托管节点组 | 按照源指南和自定义 AMI 要求，在控制平面回滚前，使用 `UpdateNodegroupVersion` 回滚适用的节点组；验证实际节点 |
| 自管理 / 混合节点 | 由负责人在控制平面回滚前协调兼容节点和工作负载迁移 |
| Auto Mode | 服务先回滚节点，再回滚控制平面；即使节点阶段期间集群状态为 `ACTIVE`，也要跟踪更新 ID |
| Fargate | 无法原地回滚 kubelet；协调 Pod/控制器/HPA/GitOps/Job 行为和可用性，确保替换 Pod 不会在控制平面回滚前立即重新创建使用较新 kubelet 的 Pod |

在验证适用的节点顺序和所有前提条件后，控制平面请求使用 `update-cluster-version`，而不是 `rollback-cluster` 命令。请先保存源指南中的轮询程序：

```bash
umask 077
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${ROLLBACK_VERSION:?}"
: "${WAIT_TIMEOUT_SECONDS:?Set an explicit client wait for the approved rollback}"
aws eks update-cluster-version --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --kubernetes-version "$ROLLBACK_VERSION" --output json --no-cli-pager > rollback-update.json
UPDATE_ID=$(jq -er '.update.id | select(type == "string" and length > 0)' rollback-update.json)
export CLUSTER_NAME AWS_REGION UPDATE_ID WAIT_TIMEOUT_SECONDS
unset NODEGROUP_NAME ADDON_NAME
python3 eks-wait-update.py
```

对于 Auto Mode，请使用源指南中的替代请求 `--rollback-config timeoutMinutes=...`，不要同时发送第二个请求。默认值为 720 分钟，支持范围为 120–10080；这并不是精确的完成时限。漂移预算为零或节点中断排除项可能会阻止操作继续进行。PDB/Pod 中断排除项会与终止宽限期相互影响，并不意味着无限期保护。`--force` 不会绕过这些控制。

只有在 Auto Mode 的节点阶段、控制平面回滚之前，才支持尽力而为的 `CancelUpdate`；正在进行的中断仍可能完成。超时/取消会使控制平面保持不变，节点会重新协调到与其版本相符的状态。仅客户端超时不会取消操作。重试仍受原始资格窗口限制。

回滚会保留 etcd/工作负载/PV 数据，而不是恢复备份；附加组件不会自动回滚。上一个次版本会获得其最新的平台版本，不一定是之前使用的确切平台版本。CloudFormation 回滚或 Git revert 并不是此服务操作。请使用源指南中的完整决策流程；本次审查未对 AWS 执行任何命令。

**事件记录**

以下保留了原始时间戳。由于没有提供事件证据，场景和所声称的原因仍只是带有假设的示例：

```markdown
# Upgrade troubleshooting report (illustrative, not a verified incident)

## Problem description

- Example symptom: CoreDNS Pods in CrashLoopBackOff after a node-group update
- Example impact: service discovery and application connections affected
- Original illustrative timestamp: 2023-07-15 14:30 UTC
- Provenance: no incident logs or measurement evidence supplied

## Investigation

1. Record the exact update ID, versions, changes and affected workloads.
2. Inspect CoreDNS logs/events, node conditions and resource availability.
3. Compare the owned Corefile/configuration with the reviewed baseline.
4. Check connectivity, network policies, scheduling and dependency changes.

## Hypotheses, not established findings

- A configuration parsing error is one possible explanation.
- A ConfigMap modification requires a diff/audit record and relevant log evidence.
- Record evidence that supports or rejects each hypothesis.

## Conditional remediation

1. If a configuration regression is demonstrated, restore compatible reviewed settings.
2. Coordinate any restart with replicas, readiness, PDB and DNS availability.
3. Verify service discovery and application SLOs, not just Pod phase.

## Prevention and record

- Version and back up owned configuration; rehearse restoration.
- Add regression checks and staged rollout gates.
- Actual actions, results and evidence: NOT RUN / TO BE RECORDED.
```

与 AWS Support 分享确切的更新 ID、有时限的日志/错误、影响和已尝试的操作。A 可能会在未确定原因的情况下引入计划外迁移；B 忽略了有用证据；D 会使可靠性/安全问题得不到处理。

来源：[EKS 回滚](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html)、[Auto Mode 回滚](https://docs.aws.amazon.com/eks/latest/userguide/rollback-automode.html)、[EKS 故障排除](https://docs.aws.amazon.com/eks/latest/userguide/troubleshooting.html)。

</details>

### 6. 最全面的升级后验证方法是什么？

- A. 只统计节点数量
- B. 只验证集群版本
- C. 分阶段验证请求状态、组件、工作负载功能和有代表性的性能
- D. 不经验证就立即发送所有生产流量

<details>
<summary>显示答案</summary>

**答案：C. 分阶段验证请求状态、组件、工作负载功能和有代表性的性能**

首先验证确切的更新请求、版本和节点/附加组件状态。然后测试功能，并将应用指标与记录的基线进行比较。冒烟测试通过，并不等于已证明生产环境就绪或满足 SLO。

| 范围 | 证据 |
| --- | --- |
| 控制平面 | 更新结果、API 就绪/响应情况和受支持的指标/日志；无法直接访问托管 etcd |
| 节点 | Ready 状态、预期的 kubelet/AMI/运行时、调度情况和特定计算类型的健康状况 |
| 网络 | Pod/Service/DNS、Ingress/Gateway、出口流量和依赖项连接 |
| 存储 | 配置、跨使用方读写、拓扑、重新调度和应用一致性恢复 |
| 安全 | 预期的身份验证/授权、Pod 安全性、NetworkPolicy 和加密行为 |
| 工作负载 | Deployment 滚动更新/扩缩容、StatefulSets、Jobs/CronJobs、CRD/运算符和 Webhook |
| 性能 | 可比较的请求速率、延迟/错误分布、启动时间和资源使用情况，并覆盖有代表性的时间窗口 |

在检查上下文、兼容的 StorageClass、CSI 驱动程序/IAM、调度、准入/网络策略和成本后，使用源指南中的 `eks-upgrade-smoke.py` 执行有时限的 Linux EC2 测试。将提供的实现保存到本地；这并不是指向未定义的验证镜像或脚本。

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?Set the reviewed test cluster context}"
: "${TEST_STORAGE_CLASS:?Set an existing compatible test StorageClass}"
export KUBE_CONTEXT TEST_STORAGE_CLASS
export RUN_SMOKE_TEST=yes
export CLEANUP_ON_SUCCESS=no
python3 eks-upgrade-smoke.py
```

该辅助程序会创建唯一的命名空间、记录其 UID、运行 Deployment 滚动更新/扩缩容和 20 个 HTTP 请求，并使用独立的 Jobs 写入和读取 PVC 标记。写入器会在等待绑定之前创建，因此 `WaitForFirstConsumer` 可以调度一个使用者；写入器会在读取器之前删除。失败时会保留证据/资源。可选的成功后清理操作要求命名空间 UID 相同；`Retain` PV 可能仍会产生费用。该测试不会覆盖所有工作负载、恢复流程、Fargate/Auto 配置、性能限制或安全控制。

请根据表格选择其他由相应负责人审核的功能测试和负载测试。`kubectl top` 依赖 Metrics Server，只显示当前资源使用情况，并不能证明吞吐量或延迟。不要对生产环境执行不受限的 wget 循环。记录目标流量、时长、成功/错误标准、基线、环境差异和实际结果；不要根据合成样例推断基准性能。

**可选 Terraform 样例**

这个独立管理的样例保留了命名空间/Deployment/Service/PVC 学习示例。请为经过审核的上下文配置 provider，提供新的命名空间和兼容的 StorageClass，并检查 plan。不要接管或销毁已有命名空间。它只是样例，并非自动验证结论。

```hcl
# Separate disposable fixture; configure the Kubernetes provider/context externally.
variable "validation_namespace" {
  type = string
  validation {
    condition     = can(regex("^eks-upgrade-validation-[a-z0-9]{8,16}$", var.validation_namespace))
    error_message = "Supply a new, unique namespace with the required validation prefix."
  }
}
variable "test_storage_class" {
  type = string
  validation {
    condition     = length(trimspace(var.test_storage_class)) > 0
    error_message = "Select an existing compatible test StorageClass."
  }
}

resource "kubernetes_namespace_v1" "validation" {
  metadata {
    name = var.validation_namespace
  }
}

resource "kubernetes_persistent_volume_claim_v1" "validation_pvc" {
  metadata {
    name      = "validation-pvc"
    namespace = kubernetes_namespace_v1.validation.metadata[0].name
  }
  wait_until_bound = false
  spec {
    access_modes       = ["ReadWriteOnce"]
    storage_class_name = var.test_storage_class
    resources {
      requests = { storage = "1Gi" }
    }
  }
}

resource "kubernetes_deployment_v1" "validation_app" {
  metadata {
    name      = "validation-app"
    namespace = kubernetes_namespace_v1.validation.metadata[0].name
  }
  wait_for_rollout = true
  spec {
    replicas = 1
    strategy {
      type = "Recreate"
    }
    selector {
      match_labels = { app = "validation-app" }
    }
    template {
      metadata {
        labels = { app = "validation-app" }
      }
      spec {
        automount_service_account_token = false
        node_selector                   = { "kubernetes.io/os" = "linux" }
        security_context {
          run_as_non_root = true
          run_as_user     = 65532
          run_as_group    = 65532
          fs_group        = "65532"
          seccomp_profile {
            type = "RuntimeDefault"
          }
        }
        container {
          name    = "http"
          image   = "docker.io/library/busybox@sha256:73aaf090f3d85aa34ee199857f03fa3a95c8ede2ffd4cc2cdb5b94e566b11662"
          command = ["sh", "-ec"]
          args = [
            "test -f /data/index.html || printf 'fixture\\n' > /data/index.html; exec httpd -f -p 8080 -h /data"
          ]
          port {
            container_port = 8080
          }
          readiness_probe {
            http_get {
              path = "/"
              port = "8080"
            }
            period_seconds = 5
          }
          resources {
            requests = { cpu = "10m", memory = "16Mi" }
            limits   = { cpu = "100m", memory = "64Mi" }
          }
          security_context {
            allow_privilege_escalation = false
            read_only_root_filesystem  = true
            capabilities {
              drop = ["ALL"]
            }
          }
          volume_mount {
            name       = "data"
            mount_path = "/data"
          }
        }
        volume {
          name = "data"
          persistent_volume_claim {
            claim_name = kubernetes_persistent_volume_claim_v1.validation_pvc.metadata[0].name
          }
        }
      }
    }
  }
}

resource "kubernetes_service_v1" "validation_service" {
  metadata {
    name      = "validation-service"
    namespace = kubernetes_namespace_v1.validation.metadata[0].name
  }
  spec {
    selector = { app = "validation-app" }
    type     = "ClusterIP"
    port {
      port        = 80
      target_port = "8080"
    }
  }
}
```

`wait_until_bound = false` 允许 Terraform 在 `WaitForFirstConsumer` PVC 绑定之前创建使用者。Deployment 会等待滚动更新/就绪完成。一个副本和 `Recreate` 策略避免了对 RWO 卷进行多节点滚动挂载的假设，但这会造成停机。PVC 确实已挂载，但提供文件服务并不能证明替换后持久性正常，也不能证明备份恢复成功。请使用独立的写入/重建/读取和恢复证据。清理前请检查 PV 回收策略。`_v1` 资源字段已根据 provider 文档检查；本次未执行 Kubernetes provider apply 或在线样例。

**验证仪表板**

以下 ConfigMap 假设现有 Grafana dashboard sidecar 正在监视带有标签 `grafana_dashboard=1` 的 `monitoring`，数据源 UID 为 `prometheus`，并采用单集群 kube-prometheus-stack 抓取布局。请根据实际安装情况调整这些设置和 job 标签。不要为此样例安装第二套监控堆栈。

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: cluster-validation-dashboard
  namespace: monitoring
  labels:
    grafana_dashboard: "1"
data:
  cluster-validation.json: |
    {
      "uid": "eks-upgrade-validation",
      "title": "EKS Upgrade Validation",
      "schemaVersion": 39,
      "version": 1,
      "timezone": "utc",
      "refresh": "30s",
      "time": {
        "from": "now-1h",
        "to": "now"
      },
      "panels": [
        {
          "id": 1,
          "title": "Ready nodes",
          "type": "stat",
          "gridPos": {
            "h": 8,
            "w": 12,
            "x": 0,
            "y": 0
          },
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          },
          "fieldConfig": {
            "defaults": {
              "unit": "short"
            },
            "overrides": []
          },
          "targets": [
            {
              "refId": "A",
              "expr": "sum(max by (node) (kube_node_status_condition{job=\"kube-state-metrics\",condition=\"Ready\",status=\"true\"}))"
            }
          ]
        },
        {
          "id": 2,
          "title": "Ready active Pods (%)",
          "type": "stat",
          "gridPos": {
            "h": 8,
            "w": 12,
            "x": 12,
            "y": 0
          },
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          },
          "fieldConfig": {
            "defaults": {
              "unit": "percent"
            },
            "overrides": []
          },
          "targets": [
            {
              "refId": "A",
              "expr": "100 * sum(max by (namespace, pod, uid) (kube_pod_status_ready{job=\"kube-state-metrics\",condition=\"true\"}) and on (namespace, pod, uid) (max by (namespace, pod, uid) (kube_pod_status_phase{job=\"kube-state-metrics\",phase=~\"Pending|Running|Unknown\"}) == 1)) / sum(max by (namespace, pod, uid) (kube_pod_status_phase{job=\"kube-state-metrics\",phase=~\"Pending|Running|Unknown\"}))"
            }
          ]
        },
        {
          "id": 3,
          "title": "API requests / second",
          "type": "timeseries",
          "gridPos": {
            "h": 8,
            "w": 12,
            "x": 0,
            "y": 8
          },
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          },
          "fieldConfig": {
            "defaults": {
              "unit": "reqps"
            },
            "overrides": []
          },
          "targets": [
            {
              "refId": "A",
              "expr": "sum by (code) (rate(apiserver_request_total{job=\"apiserver\"}[5m]))"
            }
          ]
        },
        {
          "id": 4,
          "title": "Node CPU busy (%)",
          "type": "timeseries",
          "gridPos": {
            "h": 8,
            "w": 12,
            "x": 12,
            "y": 8
          },
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          },
          "fieldConfig": {
            "defaults": {
              "unit": "percent"
            },
            "overrides": []
          },
          "targets": [
            {
              "refId": "A",
              "expr": "100 * (1 - avg by (instance) (max by (instance, cpu) (rate(node_cpu_seconds_total{job=\"node-exporter\",mode=\"idle\"}[5m]))))"
            }
          ]
        },
        {
          "id": 5,
          "title": "Node memory used (%)",
          "type": "timeseries",
          "gridPos": {
            "h": 8,
            "w": 12,
            "x": 0,
            "y": 16
          },
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          },
          "fieldConfig": {
            "defaults": {
              "unit": "percent"
            },
            "overrides": []
          },
          "targets": [
            {
              "refId": "A",
              "expr": "100 * (1 - max by (instance) (node_memory_MemAvailable_bytes{job=\"node-exporter\"}) / max by (instance) (node_memory_MemTotal_bytes{job=\"node-exporter\"}))"
            }
          ]
        }
      ]
    }
```

“Ready active Pods”使用就绪状态，并排除已完成/失败的生命周期阶段；仅处于 `Running` 状态并不代表就绪。CPU 面板使用 idle 计数器的速率，内存则使用单独的百分比面板。在上述单集群范围内，重复的 exporter 样本会被合并。对于多集群数据源，请在合并序列前按集群标签进行筛选/分组。缺失指标或活跃 Pod 分母为零时，必须保持为未知/无数据，不能替换成表示健康的零值。此仪表板本身不会验证升级或强制执行发布关卡。

请将更新 ID、冒烟测试证据、测试环境/时间、指标查询/时间窗口、失败情况和未解决的覆盖缺口保存到私有结果目录中。在增加生产流量之前，先观察金丝雀流量和恢复标准。A 和 B 是有用的局部检查，但都无法覆盖功能。D 会在完成这些检查之前让用户承担风险。

来源：[持久卷](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)、[Pod 生命周期](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/)、[Terraform PVC](https://registry.terraform.io/providers/hashicorp/kubernetes/latest/docs/resources/persistent_volume_claim_v1)、[Prometheus 函数](https://prometheus.io/docs/prometheus/latest/querying/functions/)。

</details>
