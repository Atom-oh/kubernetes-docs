# Kubernetes 版本功能与路线图

> **历史覆盖范围**：Kubernetes 1.29–1.36；当前 EKS 支持情况另行列出
> **最后更新**：2026年10月12日

Kubernetes 发展迅速，每年发布三个版本，引入新功能、推动现有功能晋级，并弃用旧 API。对于运行 Amazon EKS 的企业团队而言，了解版本全貌对于规划升级、在合适的时机采用新能力，以及避免因弃用而造成中断至关重要。本文档按版本全面介绍 Kubernetes 1.29 至 1.36，并为每个版本提供 EKS 专项指导。

## 目录

1. [概述与学习目标](#1-overview-and-learning-objectives)
2. [Kubernetes 发布周期](#2-kubernetes-release-cycle)
3. [EKS 版本支持矩阵](#3-eks-version-support-matrix)
4. [逐版本功能指南](#4-version-by-version-feature-guide)
5. [重要功能晋级时间表](#5-key-feature-graduation-timeline)
6. [弃用与移除](#6-deprecations-and-removals)
7. [EKS 专项注意事项](#7-eks-specific-considerations)
8. [版本升级规划](#8-version-upgrade-planning)
9. [未来展望](#9-future-outlook)
10. [参考资料](#10-references)

---

<span id="1-overview-and-learning-objectives"></span>

## 1. 概述与学习目标

### 本文档的目的

本文档是以下内容的集中参考：

- Kubernetes 1.29 至 1.36 中引入的**各版本新功能**
- 跟踪功能从 Alpha 到 Beta 再到 GA 演进的**功能晋级时间表**
- **弃用时间表**及所需的迁移操作
- 包含标准支持和扩展支持日期的 **EKS 支持窗口**
- 面向企业团队的**升级规划指导**

### 学习目标

阅读本文档后，你将能够：

1. 说明 Kubernetes 发布周期和功能成熟度模型
2. 确定各 Kubernetes 版本提供了哪些功能
3. 将功能门控对应到具体版本，并了解其生命周期
4. 根据功能可用性和弃用时间表规划版本升级
5. 了解 EKS 专属版本支持策略，包括标准支持与扩展支持的区别
6. 评估继续使用旧版本的成本与风险权衡
7. 跟踪未来功能时，区分已发布的里程碑和提议的时间表

### 适用读者

| 受众 | 重点章节 |
|----------|-------------|
| **平台工程师** | 版本功能指南、升级规划、弃用 |
| **集群管理员** | EKS 支持矩阵、升级规划、EKS 专项注意事项 |
| **应用开发人员** | 功能指南（Sidecar Containers、In-Place Resize、DRA）、功能晋级时间表 |
| **安全团队** | 弃用、各版本安全相关功能、StructuredAuthz、User Namespaces |
| **工程经理** | 概述、支持矩阵、扩展支持的成本影响 |

---

<span id="2-kubernetes-release-cycle"></span>

## 2. Kubernetes 发布周期

### 发布节奏与阶段

Kubernetes 通常每年发布约三个**次要版本**，间隔大约四个月。补丁版本采用单独的、通常按月进行的发布节奏。上游补丁分支的支持期约为 14 个月：约 12 个月的常规维护，随后有两个月的维护期，用于处理 CVE 和关键修复。这与 EKS 的 14 个月标准支持窗口不同；EKS 的支持窗口从 EKS 发布日期开始计算。

发布团队会公布增强功能纳入、代码冻结、稳定化和候选版本的截止日期。原来的“第 15 周”图示只是示意性周期，并非保证的时间表，也不是通用的周数表。请遵循目标版本的时间表和例外处理流程。

![工作流图展示 Kubernetes 年度发布周期：每年发布三次，每次发布都经过增强功能冻结、代码冻结以及测试与稳定化阶段，然后大约每四个月正式发布一次。](../.gitbook/assets/en-eks-12-kubernetes-version-roadmap-1.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-12-kubernetes-version-roadmap-1.html)

### 功能成熟度、API 稳定性与功能门控

| 阶段 | 说明 |
|---|---|
| Alpha | 通常默认禁用；行为/API 可能更改或消失。请检查具体的门控和前置条件。 |
| Beta | 测试范围更广，但默认设置和兼容性仍取决于具体功能/版本。一些 Beta 门控仍处于禁用状态。 |
| Stable / GA | 适用 API 稳定性承诺；这并不证明特定工作负载、驱动程序、操作系统或部署是安全的。 |

从 1.24 开始，**新的 Beta API** 默认禁用；此前已启用的 Beta API 和现有 Beta API 的新版本则按不同方式处理。API 提供配置与功能门控相关，但二者并不相同。不要由此推断所有 Beta 功能都需要显式启用，也不要认为所有稳定功能都不需要配置工作负载。

在同一个 Kubernetes 主版本中，不能移除 GA API 版本。这条规则与功能门控的移除不同：从 Beta 晋级到 GA 的门控，最短弃用期为六个月或两个版本，以较长者为准。必须核实实际移除版本。已锁定或已移除的门控不能被视为受支持的禁用开关。例如，已发布的 1.36.2 源码仍包含已锁定的 `SidecarContainers` 门控；它在 1.33 达到 GA，本身并不能证明该门控已在 1.35 移除。

以下是一个**历史配置片段**，不是完整的 KubeletConfiguration，也不是对 EKS 控制平面的修改。在当前节点上，应使用其确切版本所支持的配置；不要把已退役的门控复制到新的引导文件中。

```yaml
# Historical fragment for a self-managed Kubernetes 1.33 test node.
# Merge through the supported node bootstrap/configuration mechanism.
featureGates:
  InPlacePodVerticalScaling: true
  UserNamespacesSupport: true
```

AWS 管理 EKS 控制平面配置；客户不能编辑 EKS kube-apiserver 静态 Pod，也不能传入任意服务器标志。EKS 版本常见问题说明 Alpha 功能不受支持。在自行管理的节点上更改门控，无法启用控制平面不可用的 API。请查看 AWS 针对具体功能的指导，以及节点运行时/操作系统要求。

节点的 `configz` 端点显示所选 kubelet 的配置；该输出无法证明被省略的默认值或控制平面行为。`/metrics` 需要适当的非资源 URL 授权，而且功能指标可能不可用或带有额外标签。输出缺失或访问错误都不表示“已禁用”。

```bash
# Authorized, read-only diagnostics; these endpoints may be restricted.
: "${KUBE_CONTEXT:?}"; : "${NODE_NAME:?Choose the actual node}"
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s \
  get --raw="/api/v1/nodes/$NODE_NAME/proxy/configz" | jq '.kubeletconfig.featureGates'
```

```bash
# Run separately; absence of a metric is not proof that a feature is disabled.
: "${KUBE_CONTEXT:?}"
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get --raw='/metrics' \
  | awk '/^kubernetes_feature_enabled/ { print }'
```

### SIG 与增强功能提案

各 SIG 负责相关领域：Node（运行时/生命周期）、Auth（身份验证/授权）、Network（Service 路由）、Storage（CSI/卷）、Scheduling、Apps、API Machinery、Instrumentation 和 Autoscaling。重要增强功能通过 KEP 管理，其中包含动机、设计、晋级标准、测试和生产就绪评审。计划中的里程碑并非发布承诺；请确认已发布的 API 和功能门控历史。

[上游补丁策略](https://kubernetes.io/releases/patch-releases/) · [功能门控](https://kubernetes.io/docs/reference/command-line-tools-reference/feature-gates/) · [弃用策略](https://kubernetes.io/docs/reference/deprecation-policy/) · [Kubernetes 1.36.2 门控实现](https://github.com/kubernetes/kubernetes/blob/v1.36.2/pkg/features/kube_features.go)

---

<span id="3-eks-version-support-matrix"></span>

## 3. EKS 版本支持矩阵

### 支持期限与价格依据

| 层级 | 自 EKS 提供该版本起的期限 | 版本支持费用 |
|---|---|---|
| 标准 | 前 14 个月 | 每集群小时 $0.10 |
| 扩展 | 随后 12 个月 | 每集群小时总计 $0.60（$0.10 + $0.50） |

这些是已公布的版本支持费用，不是集群总运营成本。Provisioned Control Plane 层级、计算、Auto Mode/Hybrid Nodes、其他能力、存储和网络都可能产生额外费用。按全年 365 天费率不变计算，相应费用分别为每个集群 $876 和 $5,256，额外增加 $4,380。按每月 730 小时估算，则分别为 $73 和 $438。这些是算术示例，不是实测账单。

### 已核实的支持日历：2026年10月12日（UTC）

| 版本 | 上游发布日期 | EKS 发布日期 | 标准支持结束日期 | 扩展支持结束日期 | 审核日状态 |
|---|---|---|---|---|---|
| 1.31 | 2024-08-13 | 2024-09-26 | 2025-11-26 | 2026-11-26 | 扩展支持 |
| 1.32 | 2024-12-11 | 2025-01-23 | 2026-03-23 | 2027-03-23 | 扩展支持 |
| 1.33 | 2025-04-23 | 2025-05-29 | 2026-07-29 | 2027-07-29 | 扩展支持 |
| 1.34 | 2025-08-27 | 2025-10-02 | 2026-12-02 | 2027-12-02 | 标准支持 |
| 1.35 | 2025-12-17 | 2026-01-27 | 2027-03-27 | 2028-03-27 | 标准支持 |
| 1.36 | 2026-04-22 | 2026-06-02 | 2027-08-02 | 2028-08-02 | 标准支持 |
| 1.37 | 2026-08-26 | 2026-10-01 | 2027-12-01 | 2028-12-01 | 标准支持 |

AWS 当前日历提供 EKS 1.31–1.37。此处列出 1.29 和 1.30，是历史功能覆盖范围，并非受支持的部署目标。

扩展支持计费从所列标准支持结束日期的 00:00 UTC 开始。安排变更前请重新核实实时日历或 API；对于 AWS 只列出月份的未来日期，这里给出的是估算值。

EKS 1.35 于**2026年1月27日**提供，1.36 于**2026年6月2日**提供，1.37 于**2026年10月1日**提供。EKS Distro 公告属于单独的发布事件；较早的 1 月 28 日合并标签不能取代 EKS 日历。

以下各版本章节保留了运行时和准入要求。有关 EKS 回滚和控制平面扩缩容/SLA 的主题，请参阅 [EKS 升级](08-eks-upgrades.md)。

```bash
# Read-only when executed with your normal authorized AWS identity.
: "${AWS_REGION:?Choose the intended Region}"
aws eks describe-cluster-versions --region "$AWS_REGION" --no-cli-pager \
  --query clusterVersions --output json
```

此命令会输出服务的版本记录，而不是假定数组第一项就是最新版本，也不会沿用旧示例的状态。本次审核未执行任何 AWS 查询。

### 升级策略与自动升级

`EXTENDED` 是集群升级策略的默认值。采用 `STANDARD` 的集群在标准支持结束后可能会自动升级；在扩展支持期内继续使用某个版本，是经过权衡的成本/生命周期选择。扩展支持结束后，EKS 会逐步将仍在运行的控制平面升级到受支持的版本。AWS 不承诺确切的升级时间，并表示自动更新之前不会立即发送通知。至少提前 60 天通知，指的是已公布的**标准支持结束**，而非扩展支持结束后新增加的 60 天宽限期，也不代表一定会按照 60/30/7 天的顺序发送通知。

Managed node groups、自行管理的节点、Fargate Pods 和 Hybrid Nodes 都需要各自的更新/替换流程。Auto Mode 节点可以自动更新；普通已安装的 add-ons 仍需核查兼容性和管理责任。实际条件允许时，应保持节点和控制平面版本匹配，而不是把最大支持偏差视为目标。应检查工作负载就绪情况和实际更新状态，而不只是控制平面版本字符串。EKS 原生的七天功能不能用于回滚扩展支持结束时的自动升级；有关资格条件和“先回滚节点”的顺序，请参阅升级章节。

[EKS 支持日历与常见问题](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html) · [EKS 定价](https://aws.amazon.com/eks/pricing/)

<!-- Parent diagram repair pending: stage/default guarantees and support status/notification timing are stale.
![Lifecycle diagram of the three-stage Kubernetes feature maturity model, Alpha graduating to Beta and then to GA, with the stability and production-readiness guarantees of each stage.](../.gitbook/assets/en-eks-12-kubernetes-version-roadmap-2.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-12-kubernetes-version-roadmap-2.html)

![Diagram of the Amazon EKS version lifecycle: 14 months of standard support then 12 months of extended support at six times the price, with versions 1.29 to 1.36 grouped by release year and their release and support end dates.](../.gitbook/assets/en-eks-12-kubernetes-version-roadmap-3.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-12-kubernetes-version-roadmap-3.html)

![Flowchart showing what happens when an EKS Kubernetes version approaches end of life: clusters may continue on paid extended support, but once a 60-day deprecation notice expires without a user upgrade, AWS force-upgrades the cluster.](../.gitbook/assets/en-eks-12-kubernetes-version-roadmap-5.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-12-kubernetes-version-roadmap-5.html)

-->

---

<span id="4-version-by-version-feature-guide"></span>

## 4. 逐版本功能指南

本节详细介绍 Kubernetes 1.29 至 1.36 各版本中引入、晋级和弃用的功能。

### 4.1 Kubernetes 1.29 “Mandala”（2023年12月）

2023年12月13日的发布公告列出了 **49 项增强功能：11 项稳定、19 项 Beta、19 项 Alpha**。这些是历史发布数量，并不表示 EKS 仍支持 1.29。图中的默认启用/生产就绪标签是概括性表述；请使用前文所述的具体功能门控历史和运行时要求。

![Kubernetes 1.29“Mandala”的49项增强功能按成熟度阶段划分为11项稳定（GA）、19项Beta和19项Alpha，并列出各阶段的代表性功能。](../.gitbook/assets/en-eks-12-kubernetes-version-roadmap-6.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-12-kubernetes-version-roadmap-6.html)

#### KMS v2 静态加密：GA

KMS v2 通过从秘密种子派生一次性数据加密密钥来提升信封加密性能，并在保护/轮换该种子时使用 KMS 插件，而不是每次写入对象都执行新的远程加密操作。两种信封加密设计都使用数据加密层和密钥加密层；KMS v1 并不是“单层”设计。这种改进不保证延迟恒定。

KMS v1 在 1.28 中弃用，并在 1.29 中默认禁用。当前上游 KMS 指南仍记录其旧版实现；此前声称它在 1.31 移除的说法不正确。优先采用受支持的 v2 迁移路径。

此配置适用于由管理员管理的上游 API server，且要求已审核的 v2 插件安装在指定套接字处。它**不是 EKS 控制平面清单**。KMS v2 不接受 `cachesize`。末尾的 `identity` 提供程序允许迁移期间读取现有明文；当首个提供程序无法加密写入时，它不会回退到明文。请审核加密迁移，并且只有在验证迁移后才移除明文读取支持。

```yaml
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
- resources:
  - secrets
  providers:
  - kms:
      apiVersion: v2
      name: reviewed-kms-provider
      endpoint: unix:///var/run/kmsplugin/socket.sock
      timeout: 3s
  - identity: {}
```

**EKS 区别：** AWS 当前指导说明，EKS 1.28 及更高版本默认使用 KMS v2 信封加密保护所有 Kubernetes API 数据；除非配置客户管理密钥，否则使用 AWS 所有的密钥。这涵盖 Secrets 和 ConfigMaps 等 API 数据，不包括任意节点或 EBS 卷数据。不要推断它仅从 EKS 1.29 才开始，也不要将此上游文件应用于 EKS。

#### ReadWriteOncePod：GA

`ReadWriteOncePod` 将 PVC 限制为整个集群中的一个 Pod。`ReadWriteOnce` 则允许同一节点上有多个 Pod 使用该卷。RWOP 需要兼容的 CSI 卷/驱动程序；上游侧车最低版本为 csi-provisioner 3.0.0、csi-attacher 3.3.0 和 csi-resizer 1.3.0。这些是功能最低版本，并非建议使用的当前版本。请为实际集群和 provisioner 选择受支持的版本。

此示例要求已有 `version-lab` 命名空间和合适的 `reviewed-csi-class`。访问模式协调不是针对特权主机访问的内核安全边界，不是数据库主节点选举协议，也不能替代应用 fencing 和备份。

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: database-pvc
  namespace: version-lab
spec:
  accessModes:
  - ReadWriteOncePod
  storageClassName: reviewed-csi-class
  resources:
    requests:
      storage: 100Gi
```

#### 部分 Beta 和 Alpha 功能

| 功能 | 1.29 中的状态 | 含义 |
|---|---|---|
| SidecarContainers | Beta，默认启用 | 可重启的 init containers；1.28 为 Alpha，1.33 达到 GA |
| NFTablesProxyMode | Alpha，默认禁用 | Linux Service 代理后端；必须检查内核、CNI 和 NodePort 行为 |
| LoadBalancerIPMode | Alpha | 由控制器报告的 LoadBalancer ingress 状态模式，不是任意 Pod 字段 |
| PodSchedulingReadiness | Beta | 调度门控会延迟调度器对 Pod 的处理 |
| NodeLogQuery | Alpha | 节点日志查询支持需要相应的 kubelet 配置/访问权限 |
| KubeletTracing | Beta | 它并未在 1.29 达到 GA；GA 版本为 1.34 |
| MinDomainsInPodTopologySpread | Beta | 随后在 1.30 达到 GA |

原生 sidecar 使用以下 **Pod 规格片段**。请将示例镜像替换为已审核的实现，并配置实际日志管道。这不是已安装的 Fluent Bit 部署。sidecar 启动后（如果配置了启动探针，则还要等启动探针成功）就会继续启动流程；就绪状态和优雅关闭仍需要正确的探针、应用行为和充足的终止时间预算。

```yaml
initContainers:
- name: log-helper
  image: example.invalid/version-lab/log-helper:reviewed
  restartPolicy: Always
```

该版本还推动 CSI `NodeExpandSecret` 达到稳定状态，使驱动程序的节点端扩容请求能够携带适当凭据。已弃用的 `flowcontrol.apiserver.k8s.io/v1beta2` 端点在 1.29 停止提供；应改用稳定版 `v1` API 并审核字段变更。`SecurityContextDeny` 早在 1.29 之前就已弃用，并在 1.30 移除，并非 1.29 新近弃用。此处没有确立通用的“5,000 个 Services”性能阈值，也没有实测代理基准数据。

[Kubernetes 1.29 发布公告](https://kubernetes.io/blog/2023/12/13/kubernetes-v1-29-release/) · [KMS provider](https://kubernetes.io/docs/tasks/administer-cluster/kms-provider/) · [EKS 信封加密](https://docs.aws.amazon.com/eks/latest/userguide/envelope-encryption.html) · [Persistent volumes 与 RWOP](https://kubernetes.io/docs/concepts/storage/persistent-volumes/) · [API 迁移指南](https://kubernetes.io/docs/reference/using-api/deprecation-guide/)

---

### 4.2 Kubernetes 1.30 “Uwubernetes”（2024年4月）

4月17日发布的版本包含 **45 项增强功能：17 项稳定、18 项 Beta、10 项 Alpha**。成熟度标签不能替代针对具体功能的配置和运行时检查。

![Kubernetes 1.30“Uwubernetes”的45项增强功能分为17项稳定、18项Beta和10项Alpha，其中 ValidatingAdmissionPolicy 等主要 GA 功能归入稳定组。](../.gitbook/assets/en-eks-12-kubernetes-version-roadmap-7.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-12-kubernetes-version-roadmap-7.html)

#### ValidatingAdmissionPolicy：GA

ValidatingAdmissionPolicy 在 API server 内评估 CEL。它可以替代许多准入 Webhook 及其网络/证书/服务器依赖，但错误策略、评估错误或 fail-closed 配置仍可能拒绝请求。策略、绑定和可选参数对象各有不同作用；参数可以是内置资源或自定义资源，并不一定需要第三种 CRD 类型。

以下示例使用当前稳定的 `v1` API。其绑定为**仅审计**模式，并选择带有 `version-lab-policy=enabled` 标签的命名空间；违规只会添加审计注释，不会拒绝请求。请配置审计日志收集以观察这些注释，并控制谁可以设置该命名空间标签。先评估正向和负向测试用例，再在确实需要强制执行时有意选择 `Deny`。这些示例不能证明生产环境中的准入行为。

资源策略检查常规容器和 init containers 是否声明 CPU/内存限制字段。它不会验证是否设置了合适的正数值：字段存在但值为零，并不是有用的硬限制。应使用合适的 LimitRange/资源策略满足容量要求。Ephemeral containers 不能声明此类限制，因此不纳入检查。当前集群包含 `pods/resize`；该子资源是在最初的 1.30 VAP 晋级之后引入的。

```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicy
metadata:
  name: version-lab-resource-limits
spec:
  failurePolicy: Fail
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
      - pods/resize
  validations:
  - expression: "object.spec.containers.all(c,\n  has(c.resources) && has(c.resources.limits)\
      \ &&\n  has(c.resources.limits.cpu) && has(c.resources.limits.memory)\n) &&\n\
      (!has(object.spec.initContainers) || object.spec.initContainers.all(c,\n  has(c.resources)\
      \ && has(c.resources.limits) &&\n  has(c.resources.limits.cpu) && has(c.resources.limits.memory)\n\
      ))"
    message: Regular and init containers must declare CPU and memory limits.
    reason: Invalid
---
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicyBinding
metadata:
  name: version-lab-resource-limits
spec:
  policyName: version-lab-resource-limits
  validationActions:
  - Audit
  matchResources:
    namespaceSelector:
      matchLabels:
        version-lab-policy: enabled
```

镜像策略使用完整的 registry/repository 前缀，包括 `/` 分隔边界。旧的 `123456789012.dkr.ecr.` 前缀也会接受外观相似的域名。请将示例账号、Region 和公共别名替换为已批准的来源。该策略检查镜像引用，不检查签名、漏洞状态或摘要是否不可变。可选 init/ephemeral 列表均受到保护，并且明确匹配 ephemeral-container 子资源。

```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicy
metadata:
  name: version-lab-image-registries
spec:
  failurePolicy: Fail
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
  validations:
  - expression: object.spec.containers.all(c, c.image.startsWith('123456789012.dkr.ecr.us-west-2.amazonaws.com/')
      || c.image.startsWith('public.ecr.aws/approved-alias/'))
    message: Regular container images must use an approved registry/repository prefix.
  - expression: '!has(object.spec.initContainers) || object.spec.initContainers.all(c,
      c.image.startsWith(''123456789012.dkr.ecr.us-west-2.amazonaws.com/'') || c.image.startsWith(''public.ecr.aws/approved-alias/''))'
    message: Init container images must use an approved registry/repository prefix.
  - expression: '!has(object.spec.ephemeralContainers) || object.spec.ephemeralContainers.all(c,
      c.image.startsWith(''123456789012.dkr.ecr.us-west-2.amazonaws.com/'') || c.image.startsWith(''public.ecr.aws/approved-alias/''))'
    message: Ephemeral container images must use an approved registry/repository prefix.
---
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicyBinding
metadata:
  name: version-lab-image-registries
spec:
  policyName: version-lab-image-registries
  validationActions:
  - Audit
  matchResources:
    namespaceSelector:
      matchLabels:
        version-lab-policy: enabled
```

其他**验证列表片段**展示了常规容器的有效 `runAsNonRoot` 继承，以及非空应用标签的检查。容器级设置会覆盖 Pod 设置。这些片段需要配套的策略和绑定；它们不会验证所有 Pod Security Standard、init/ephemeral container 或镜像用户。包含 `/` 的映射键使用成员关系测试；`has(map["key"])` 不是合法的 CEL 宏语法。

```yaml
- expression: "object.spec.containers.all(c,\n  has(c.securityContext) && has(c.securityContext.runAsNonRoot)\n\
    \    ? c.securityContext.runAsNonRoot\n    : (has(object.spec.securityContext)\
    \ &&\n       has(object.spec.securityContext.runAsNonRoot) &&\n       object.spec.securityContext.runAsNonRoot)\n\
    )"
  message: Regular containers must effectively set runAsNonRoot.
- expression: 'has(object.metadata.labels) &&

    ''app.kubernetes.io/name'' in object.metadata.labels &&

    ''app.kubernetes.io/version'' in object.metadata.labels &&

    object.metadata.labels[''app.kubernetes.io/name''] != '''' &&

    object.metadata.labels[''app.kubernetes.io/version''] != '''' '
  message: Nonempty application name and version labels are required.
```

#### Pod Scheduling Readiness：GA

调度门控可使 Pod 暂不进入调度考虑范围。创建/准入时可以设置门控，之后可以移除，但 Pod 创建后不能再添加新门控。仅有被门控的 Pod 本身不会触发常规不可调度 Pod 的节点预置；外部审批/预置工作流必须满足条件。仅靠门控不能实现原子化的 gang 调度。

此示例要求使用自有命名空间，将示例镜像替换为已审核镜像，并准备合适的 GPU 容量/驱动程序。两个门控名称代表外部配额审批和安全扫描；Kubernetes 不会因为门控具有这些名称就执行相应操作。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: gated-training
  namespace: version-lab
spec:
  schedulingGates:
  - name: example.com/gpu-quota-approved
  - name: example.com/security-scan-passed
  containers:
  - name: trainer
    image: example.invalid/version-lab/training:reviewed
    resources:
      limits:
        nvidia.com/gpu: 4
```

独立验证指定条件后，此变更只会移除对应门控。JSON Patch 测试可保护 UID、resourceVersion 和指定门控名称；并发更新或对象替换都会导致失败。前置条件失败时应重新读取并重新评估，而不是移除猜测的索引。只有移除全部门控后，Pod 才有资格被调度；常规放置和容量限制仍然适用。

```bash
# MUTATION: remove only the named gate after independently verifying its condition.
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${POD_NAME:?}"; : "${GATE_NAME:?}"
gate_patch=$(kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n "$NAMESPACE" \
  get pod "$POD_NAME" -o json | jq -ce --arg gate "$GATE_NAME" '
    .metadata as $m |
    [(.spec.schedulingGates // []) | to_entries[] | select(.value.name == $gate)] as $matches |
    if ($matches | length) != 1 then error("Expected exactly one matching gate")
    else ($matches[0].key | tostring) as $i | [
      {op:"test", path:"/metadata/uid", value:$m.uid},
      {op:"test", path:"/metadata/resourceVersion", value:$m.resourceVersion},
      {op:"test", path:("/spec/schedulingGates/" + $i + "/name"), value:$gate},
      {op:"remove", path:("/spec/schedulingGates/" + $i)}
    ] end')
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n "$NAMESPACE" \
  patch pod "$POD_NAME" --type=json --patch "$gate_patch"
```

#### HPA ContainerResource 指标：GA（KEP-2702）

ContainerResource 以指定容器为目标，因此日志/代理 sidecar 不必扭曲应用的利用率信号。目标 Deployment 必须已存在于 `version-lab` 中，并包含一个具有适当 requests 的 `app` 容器。还需要可用的资源指标提供程序。利用率相对于 requests 计算，而非相对于 limits。存在多个指标时，HPA 使用较大的副本数建议；指标缺失、就绪状态和稳定窗口都可能影响扩缩容。副本数 2–50 的范围只是示例容量输入，并非实测最优设置。

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: web-app-hpa
  namespace: version-lab
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web-app
  minReplicas: 2
  maxReplicas: 50
  metrics:
  - type: ContainerResource
    containerResource:
      name: cpu
      container: app
      target:
        type: Utilization
        averageUtilization: 70
  - type: ContainerResource
    containerResource:
      name: memory
      container: app
      target:
        type: Utilization
        averageUtilization: 80
```

#### 其他选定变更

| 功能 | 1.30 中的状态 |
|---|---|
| MinDomainsInPodTopologySpread | GA |
| StableLoadBalancerNodeSet | GA |
| PodDisruptionConditions | Beta；1.31 达到 GA |
| NodeLogQuery | Beta，默认禁用；1.36 达到 GA |
| UserNamespacesSupport | Beta，默认禁用 |
| ContextualLogging | Beta；调用点必须提供/使用上下文日志记录器，并非每条消息都会自动带上 Pod/节点字段 |
| RecursiveReadOnlyMounts | Alpha；需要合适的内核/运行时支持 |
| RelaxedEnvironmentVariableValidation | Alpha；改变允许的环境变量**名称**，而非值 |
| ServiceAccountTokenJTI | Beta；令牌包含用于追踪的标识符 |

`SecurityContextDeny` 在 1.30 中移除；请评估 Pod Security Admission 以及环境所需的策略。功能成熟度本身不是迁移测试。

[Kubernetes 1.30 发布公告](https://kubernetes.io/blog/2024/04/17/kubernetes-v1-30-release/) · [ValidatingAdmissionPolicy](https://kubernetes.io/docs/reference/access-authn-authz/validating-admission-policy/) · [调度就绪](https://kubernetes.io/docs/concepts/scheduling-eviction/pod-scheduling-readiness/) · [HPA 容器指标](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/#container-resource-metrics)

---

### 4.3 Kubernetes 1.31 “Elli”（2024年8月）

8月13日发布的版本列出 **45 项增强功能：11 项稳定、22 项 Beta、12 项 Alpha**。

<!-- Parent repair: DRA structured parameters remained alpha in 1.31, not beta as drawn.
![Diagram showing the 45 enhancements in Kubernetes 1.31 "Elli" split into 11 Stable (GA), 22 Beta, and 12 Alpha, with the representative features covered on this page grouped under each maturity stage.](../.gitbook/assets/en-eks-12-kubernetes-version-roadmap-8.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-12-kubernetes-version-roadmap-8.html)
-->

#### AppArmor 原生字段：GA

AppArmor 配置从 1.30 开始支持原生字段，并在 1.31 达到 GA。它取代了旧的每容器 Beta 注解。主机必须实际启用 AppArmor，运行时必须支持它，并且必须在每个符合条件的节点上加载 `Localhost` 配置文件。自定义节点标签只能记录操作员已验证的前置条件，并不会安装或强制执行该配置文件。

第一个示例使用预先安装的配置文件；第二个示例补齐了旧 Deployment 示例中缺少的选择器和 Pod 标签。请替换示例镜像并准备好命名空间。`RuntimeDefault` 表示运行时的配置文件，`Unconfined` 则禁用 AppArmor 限制。并非所有 EKS 操作系统/计算类型都普遍支持已配置的配置文件。AppArmor、seccomp 和 SELinux 是不同的控制机制，不能互换使用。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: apparmor-local-profile
  namespace: version-lab
spec:
  nodeSelector:
    version-lab.example.com/apparmor-profile: reviewed
  containers:
  - name: app
    image: example.invalid/version-lab/app:reviewed
    securityContext:
      appArmorProfile:
        type: Localhost
        localhostProfile: reviewed-app-profile
```

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: apparmor-runtime-default
  namespace: version-lab
spec:
  replicas: 1
  selector:
    matchLabels:
      app: apparmor-runtime-default
  template:
    metadata:
      labels:
        app: apparmor-runtime-default
    spec:
      containers:
      - name: app
        image: example.invalid/version-lab/app:reviewed
        securityContext:
          appArmorProfile:
            type: RuntimeDefault
```

#### PersistentVolume 最后阶段转换时间：GA

PV 状态字段 `.status.lastPhaseTransitionTime` 记录最近一次阶段转换。可结合事件和后端证据进行生命周期诊断；它并非完整转换历史，也不能重建缺失的旧事件。以下命令不会修改或删除卷。

```bash
# Read-only, for one owned cluster-scoped PV.
: "${KUBE_CONTEXT:?}"; : "${PV_NAME:?}"
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get pv "$PV_NAME" -o json | jq '{
  name:.metadata.name,phase:.status.phase,lastPhaseTransitionTime:.status.lastPhaseTransitionTime
}'
```

#### DRA 结构化参数：1.31 中仍为 Alpha

DRA 重设计通过结构化 API 和 ResourceSlices，使设备信息和请求对 Kubernetes 可见，从而支持调度器侧的分配。**Classic DRA 在 1.31 中仍可用**，受单独的、默认禁用的 `DRAControlPlaneController` 门控控制。已发布的 1.31 源码包含此门控；1.32 源码则将其移除。因此，旧问答中“Classic DRA 已在 1.31 移除”的说法不正确。

DRA 在 1.31 中仍为 Alpha，并在 1.32 晋级到 Beta；之后其核心 API 在 1.34 稳定。此前的 `resource.k8s.io/v1beta1` 示例并不能正确表示 1.31 的 API 版本。对于当前语法，请使用 1.34 章节中的稳定 DRA 示例，并核实已安装驱动程序的 DeviceClasses、ResourceSlices、属性和能力。Kubernetes API 本身不会安装 GPU 驱动程序，也不会实现 time-slicing/MIG。

#### Service 流量分布：Beta

核心 `v1` Service 字段 `trafficDistribution: PreferClose` 会请求优先选择同一区域的端点。这是路由偏好，不是严格的本地性规则、地理距离计算，也不保证消除跨 AZ 费用。端点是否可用、实际代理实现及流量策略优先级都会产生影响。选择器必须匹配实际工作负载 Pod；此示例不会创建这些端点。

```yaml
apiVersion: v1
kind: Service
metadata:
  name: zone-preference
  namespace: version-lab
spec:
  trafficDistribution: PreferClose
  selector:
    app: web-app
  ports:
  - port: 80
    targetPort: 8080
```

#### 其他选定变更

| 功能 | 1.31 中的状态 |
|---|---|
| NFTablesProxyMode | Beta，默认启用；选择代理模式与检查 Linux/内核/CNI 兼容性是两个不同步骤 |
| MultiCIDRServiceAllocator | Beta，默认禁用 |
| VolumeAttributesClass | Beta，默认禁用；需要驱动程序/控制器/API 支持 |
| ImageVolume | Alpha，默认禁用 |
| PodDisruptionConditions | GA |
| JobPodReplacementPolicy | Beta；1.34 达到 GA |
| SidecarContainers | 自 1.29 起已为 Beta，并非 1.31 新晋级为 Beta |

nftables 后端并不会自动执行网络迁移。NodePort 和防火墙行为可能与 iptables 不同；更改生产代理模式前，应评估实际实现。

[Kubernetes 1.31 发布公告](https://kubernetes.io/blog/2024/08/13/kubernetes-v1-31-release/) · [AppArmor 前置条件](https://kubernetes.io/docs/tutorials/security/apparmor/) · [1.31 功能源码](https://github.com/kubernetes/kubernetes/blob/v1.31.0/pkg/features/kube_features.go) · [1.32 功能源码](https://github.com/kubernetes/kubernetes/blob/v1.32.0/pkg/features/kube_features.go)

---

### 4.4 Kubernetes 1.32 “Penelope”（2024年12月）

12月11日发布的版本列出 **44 项增强功能：13 项稳定、12 项 Beta、19 项 Alpha**。图中的默认启用标签是简化后的成熟度图例；以下部分 Beta 功能仍可能处于禁用状态。

![Kubernetes 1.32“Penelope”的44项增强功能按成熟度阶段分为13项稳定（GA）、12项Beta和19项Alpha，并突出显示通往稳定阶段的路径。](../.gitbook/assets/en-eks-12-kubernetes-version-roadmap-9.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-12-kubernetes-version-roadmap-9.html)

#### 结构化授权配置：GA

`AuthorizationConfiguration` 使用 `apiserver.config.k8s.io/v1` 作为稳定配置格式。它是授权模式标志的替代方案，并不意味着 `--authorization-mode` 已移除。不要混用标志和配置文件机制。EKS 管理此控制平面配置；以下文件适用于由管理员管理的 API server，不是通过 kubectl 应用的资源，也不是 EKS 自定义接口。

授权器按顺序运行，明确的允许/拒绝结果会结束处理链。在此示例中，只有 Node 和 RBAC 尚未作出决定、且匹配 `version-lab` 的资源请求，才会交给 Webhook。因此，**它不会对已经被 RBAC 允许的请求施加拒绝筛选**。CEL 匹配条件负责选择哪些请求会调用 Webhook；CEL 不是另一种独立的授权器类型。请求是 SubjectAccessReview 规格，因此命名空间位于 `request.resourceAttributes` 下，并且对非资源请求提供了存在性保护。

```yaml
apiVersion: apiserver.config.k8s.io/v1
kind: AuthorizationConfiguration
authorizers:
- type: Node
  name: node
- type: RBAC
  name: rbac
- type: Webhook
  name: reviewed-webhook
  webhook:
    authorizedTTL: 5m
    unauthorizedTTL: 30s
    timeout: 3s
    subjectAccessReviewVersion: v1
    matchConditionSubjectAccessReviewVersion: v1
    failurePolicy: Deny
    connectionInfo:
      type: KubeConfigFile
      kubeConfigFile: /etc/kubernetes/reviewed-authz-webhook.kubeconfig
    matchConditions:
    - expression: has(request.resourceAttributes) && request.resourceAttributes.namespace
        == 'version-lab'
```

使用前应准备实际 Webhook、TLS 信任配置和受保护的 kubeconfig。`failurePolicy: Deny` 适用于相关 Webhook/条件失败；缓存的决策可能延迟后端策略变更的生效。所有 API server 上应使用一致的配置。支持重新加载配置，但不能借此添加或移除 Node/RBAC 授权器；请先在非生产环境中验证完整策略和恢复流程。

#### StatefulSet PVC 保留策略：GA

1.32 中相关功能晋级的是**删除/保留从 StatefulSet volume claim templates 创建的 PVC**，并不是保证所有未使用的 PVC 保护 finalizer 都会立即消失。`whenDeleted` 控制删除 StatefulSet 时的行为，`whenScaled` 控制缩容时的行为；二者都支持 `Retain` 或 `Delete`。默认值会保留数据。以下片段应在现有 StatefulSet 中审核：

```yaml
spec:
  persistentVolumeClaimRetentionPolicy:
    whenDeleted: Retain
    whenScaled: Retain
```

选择 `Delete` 会改变数据生命周期：删除 PVC 也可能根据 PV 回收策略删除后端存储。Pod 所有权、垃圾回收、CSI 操作和 finalizer 仍会影响操作完成时间。PVC 使用中保护早在 1.32 之前就已存在；遇到卡住的 claim，应调查消费者/UID/attachment/controller，而不是一概移除 finalizer 或假定升级会修复问题。

#### VolumeAttributesClass：1.32 中仍为 Beta

VAC 在 1.31 进入 Beta，并在 1.34 达到 GA。其 Beta API 为 `storage.k8s.io/v1beta1`；当集群和 CSI 驱动程序支持时，当前示例应采用 1.34 章节的稳定 API。类的参数不可变；PVC 可以更改类引用，以请求驱动程序支持的其他属性，例如 EBS IOPS 或吞吐量。

这是异步存储修改，不是通用的零停机保证。请确认驱动程序/控制器版本、API 可用性、IAM/KMS 权限、卷类型限制、修改冷却时间和状态。不要把不完整的 PVC 对象当作完整的创建清单来应用。以下读取操作会比较目标类与报告的进度：

```bash
# Read-only: inspect one existing owned PVC and the CSI modification state.
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${PVC_NAME:?}"
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n "$NAMESPACE" \
  get pvc "$PVC_NAME" -o json | jq '{
    requestedClass:.spec.volumeAttributesClassName,
    currentClass:.status.currentVolumeAttributesClassName,
    modification:.status.modifyVolumeStatus,
    conditions:.status.conditions
  }'
```

AWS 的 1.34 说明区分了稳定的 VAC API 与早期 Beta sidecar 支持。仅凭 EKS 控制平面版本，无法证明任意 EBS CSI 版本仍与 VAC API 兼容。

#### User namespaces：1.32 中为 Beta，默认禁用

User namespaces 在 1.30 进入 Beta，在 1.33 默认启用，并于 1.36 达到 GA。Pod 通过 `hostUsers: false` 启用此功能。容器内的 UID 0 会映射到实现所选的非 root 主机 UID，并不存在通用的 `65534 + offset` 公式。这需要兼容的内核、文件系统和 CRI/运行时，而且不意味着所有工作负载或主机访问模式都兼容。

此示例特意展示容器 UID 0，以说明映射关系；请替换示例镜像，并在受支持的测试环境中使用。它属于纵深防御，不能保证免受所有内核/容器逃逸漏洞影响，也不能替代其他安全控制。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: userns-example
  namespace: version-lab
spec:
  hostUsers: false
  containers:
  - name: app
    image: example.invalid/version-lab/app:reviewed
    securityContext:
      runAsUser: 0
```

#### 其他选定变更

| 功能 | 1.32 中的状态 |
|---|---|
| CustomResourceFieldSelectors | GA；CRD 作者必须声明支持的可选字段 |
| RetryGenerateName | GA；可重试名称冲突，但不保证创建一定成功 |
| SizeMemoryBackedVolumes | GA；memory-backed emptyDir 限制仍会影响 Pod/节点内存 |
| ServiceAccountTokenJTI | GA；提供令牌标识符，不是新增授权权限 |
| JobManagedBy | Beta；1.35 达到 GA |
| DynamicResourceAllocation | Beta，默认禁用；核心 API 随后在 1.34 稳定 |
| MultiCIDRServiceAllocator | 仍为 Beta，默认禁用 |
| NFTablesProxyMode | 仍为 Beta；1.33 达到 GA |
| MutatingAdmissionPolicy | Alpha；1.34 进入 Beta，1.36 达到 GA |

`StableLoadBalancerNodeSet` 已在 1.30 达到 GA。请将这些历史阶段与特定 EKS 集群当前启用的功能区分开来。

[Kubernetes 1.32 发布公告](https://kubernetes.io/blog/2024/12/11/kubernetes-v1-32-release/) · [Authorization configuration](https://kubernetes.io/docs/reference/access-authn-authz/authorization/) · [StatefulSet PVC 保留](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/#persistentvolumeclaim-retention) · [EKS 版本说明](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions-standard.html)

---

### 4.5 Kubernetes 1.33 “Octarine”（2025年4月）

4月23日发布的版本列出 **64 项增强功能：18 项稳定、20 项 Beta、24 项 Alpha，另有 2 项已弃用或撤回**。图表以总数 64 为基数展示三个成熟度组（共 62 项）的占比；另外两项未绘入图中。这是 2025 年的一次大型发布，并不证明所有工作负载的性能或就绪度都更高。

![Kubernetes 1.33“Octarine”发布的64项增强功能按成熟度阶段分为18项稳定（GA）、20项Beta和24项Alpha，并突出显示通向稳定阶段的路径。](../.gitbook/assets/en-eks-12-kubernetes-version-roadmap-10.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-12-kubernetes-version-roadmap-10.html)

#### 原生 sidecar：GA

该功能从 1.28 的 Alpha 发展到 1.29 的 Beta，并在 1.33 达到 GA。可重启的 init container 设置 `restartPolicy: Always`。当 sidecar 的 `started` 状态变为 true 后，kubelet 就会继续处理下一个 init container：如果没有启动探针，则进程运行即满足条件；如果有启动探针，则必须等其成功。就绪状态是独立信号。下面的常规 init container 会在两个 sidecar 都启动后运行，之后应用才会启动。

这是结构性示例。所有 `example.invalid` 镜像都必须替换为已审核实现；代理必须提供所声明的就绪端点，日志代理需要实际的管道配置。仅仅选择 Envoy/Istio/Fluent Bit 镜像，并不会自动配置服务网格或日志目的地。实际数据库迁移也需要协调/幂等处理；不能假定它对每个副本运行一次就是安全的。

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sidecar-lifecycle
  namespace: version-lab
spec:
  replicas: 2
  selector:
    matchLabels:
      app: sidecar-lifecycle
  template:
    metadata:
      labels:
        app: sidecar-lifecycle
    spec:
      terminationGracePeriodSeconds: 60
      initContainers:
      - name: proxy-helper
        image: example.invalid/version-lab/reviewed-proxy:reviewed
        restartPolicy: Always
        startupProbe:
          httpGet:
            path: /ready
            port: 15021
          periodSeconds: 2
          failureThreshold: 30
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 256Mi
      - name: log-helper
        image: example.invalid/version-lab/reviewed-log-agent:reviewed
        restartPolicy: Always
        volumeMounts:
        - name: app-logs
          mountPath: /var/log/app
        resources:
          requests:
            cpu: 50m
            memory: 64Mi
          limits:
            cpu: 200m
            memory: 128Mi
      - name: initialize-app
        image: example.invalid/version-lab/reviewed-init:reviewed
        volumeMounts:
        - name: app-logs
          mountPath: /var/log/app
      containers:
      - name: app
        image: example.invalid/version-lab/reviewed-app:reviewed
        volumeMounts:
        - name: app-logs
          mountPath: /var/log/app
      volumes:
      - name: app-logs
        emptyDir: {}
```

正常优雅终止期间，主容器先于 sidecar 停止，sidecar 按启动顺序的反向顺序停止。Pod 的共享宽限期预算仍然适用：如果主容器关闭时间过长，sidecar 可能没有多少甚至完全没有优雅退出时间。原生 sidecar 不会在 Job 主容器结束后导致 Job 一直无法完成；这种行为并非到 GA 才首次出现。规划容量时应计算重叠的 init/sidecar/应用资源和 Pod 开销。此处没有测量生命周期时长或应用可用性。

![时序图展示 kubelet 启动两个 sidecar 容器，然后启动一个必须运行至完成的 init 容器，最后启动主容器；Pod 关闭时，kubelet 先终止主容器，最后按启动顺序的反向顺序终止 sidecar。](../.gitbook/assets/en-eks-12-kubernetes-version-roadmap-11.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-12-kubernetes-version-roadmap-11.html)

#### 容器资源原地调整：1.33 中为 Beta

原地调整可以改变期望的 CPU/内存分配而不重新创建 Pod，但 `resizePolicy` 仍可能要求重启容器。该功能在 1.35 达到稳定状态。以下当前 Schema 示例保持 `Burstable` QoS，并将 CPU 设置为 `NotRequired`、将内存设置为 `RestartContainer`。因此，按策略进行内存变更会请求容器重启；这并不意味着所有内存变更天生都会重启。

请使用兼容的 Linux 运行时和节点策略、受支持的 kubectl 版本偏差、自有命名空间及已审核镜像。1.36 指南不包括 Windows 以及默认 static CPU/Memory-manager 情况；对单独设门控的能力还须按版本进行评估。此 API 不会自动改写 Deployment/StatefulSet 模板，也不会与 HPA/VPA/GitOps 资源所有者协调。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: resizable-app
  namespace: version-lab
spec:
  containers:
  - name: app
    image: example.invalid/version-lab/app:reviewed
    resources:
      requests:
        cpu: 500m
        memory: 256Mi
      limits:
        cpu: '1'
        memory: 512Mi
    resizePolicy:
    - resourceName: cpu
      restartPolicy: NotRequired
    - resourceName: memory
      restartPolicy: RestartContainer
```

审核容量和所有权后，以下仅针对 CPU 的示例请求 1 个核、限制为 2 个核。它按名称选择容器，保留现有的 Burstable 类别，拒绝需要重启的 CPU 策略，并在变更前测试 Pod UID/resourceVersion。它不会修改内存。遇到冲突时，应重新读取并评估目标，而不是强制更新。

```bash
# MUTATION: reviewed CPU-only resize; desired request=1 core and limit=2 cores.
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${POD_NAME:?}"; : "${CONTAINER_NAME:?}"
resize_patch=$(kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n "$NAMESPACE" \
  get pod "$POD_NAME" -o json | jq -ce --arg container "$CONTAINER_NAME" '
    . as $pod |
    [(.spec.containers | to_entries[]) | select(.value.name == $container)] as $matches |
    if .status.phase != "Running" or .metadata.deletionTimestamp != null
       or ($matches | length) != 1
    then error("Expected one target container in a non-deleting Running Pod")
    elif .status.qosClass != "Burstable"
    then error("This example preserves an existing Burstable QoS class")
    elif $matches[0].value.resources.requests.cpu == null
         or $matches[0].value.resources.limits.cpu == null
    then error("This example requires existing CPU request and limit keys")
    elif any($matches[0].value.resizePolicy[]?; .resourceName == "cpu" and .restartPolicy == "RestartContainer")
    then error("This example requires CPU resize policy NotRequired")
    elif ([.status.containerStatuses[]? | select(.name == $container and .state.running != null)] | length) != 1
    then error("Target container is not reported running")
    else ($matches[0].key | tostring) as $i | [
      {op:"test",path:"/metadata/uid",value:$pod.metadata.uid},
      {op:"test",path:"/metadata/resourceVersion",value:$pod.metadata.resourceVersion},
      {op:"test",path:("/spec/containers/" + $i + "/name"),value:$container},
      {op:"replace",path:("/spec/containers/" + $i + "/resources/requests/cpu"),value:"1"},
      {op:"replace",path:("/spec/containers/" + $i + "/resources/limits/cpu"),value:"2"}
    ] end')
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n "$NAMESPACE" \
  patch pod "$POD_NAME" --subresource=resize --type=json --patch "$resize_patch"
```

使用当前状态字段，而不是旧的 `.status.resize` 字符串。`PodResizePending=True` 可以报告 `Deferred` 或 `Infeasible`；`PodResizeInProgress=True` 表示调整仍在进行。请比较期望的 spec、已确认的 generation，以及指定容器的 `status.containerStatuses[].resources`。`allocatedResources` 是高级分配字段，并非证明运行时限制已生效的唯一依据。没有条件信息或 PATCH 被接受，都不能证明工作负载运行正常。

```bash
# Read-only observation; an accepted patch is not proof of completed actuation.
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${POD_NAME:?}"; : "${CONTAINER_NAME:?}"
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n "$NAMESPACE" \
  get pod "$POD_NAME" -o json | jq --arg container "$CONTAINER_NAME" '{
    uid:.metadata.uid,generation:.metadata.generation,
    observedGeneration:.status.observedGeneration,qosClass:.status.qosClass,
    resizeConditions:[.status.conditions[]? | select(.type == "PodResizePending" or .type == "PodResizeInProgress")],
    desired:[.spec.containers[] | select(.name == $container) | .resources],
    reported:[.status.containerStatuses[]? | select(.name == $container) |
      {name,resources,allocatedResources,containerID,restartCount,ready}]
  }'
```

调整不能改变 Pod 的 QoS 类别。Guaranteed Pod 必须保持 CPU 和内存 requests/limits 相等；上述示例特意采用 Burstable。将内存缩小且设置为 `NotRequired` 时属于尽力而为，如果使用量超过新限制，调整可能一直处于进行中；竞争条件仍可能导致 OOM kill。不可重启的 init container 和 ephemeral container 不能调整。功能成熟度并不意味着零停机、延迟或调整成功的保证。

#### 当前 VPA 集成是单独的版本决策

这是一个**2026 年的配套组件示例**，并不表示 Kubernetes 1.33 发布时 VPA 1.8 已经存在。已发布的 VPA **1.8.0** API 支持 `InPlace`；该模式在 1.7.0 引入为 Alpha，在 1.8.0 中仍为 Alpha。它要求在 admission-controller 和 updater 上都启用 VPA `InPlace` 功能门控，并要求 Kubernetes 1.33+ 支持原地调整；VPA 1.8.x 自身记录的兼容版本为 Kubernetes 1.36–1.38。它会避免 VPA 通过驱逐 Pod 进行回退，但不保证调整一定完成，也不保证所有容器策略都无需重启。如果只想观察建议，应从 `Off` 开始。

以下仅涉及 CPU 的策略对现有 Deployment/container 使用示例范围。启用变更前，请审核控制器部署标志和容量。`InPlaceOrRecreate` 是另一种模式：它可以回退到重建方式，在 VPA 1.6 达到 GA，其旧门控在 1.7 移除。不要启用已移除的门控，也不要只根据 Kubernetes 的 GA 状态推断 VPA 行为。

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: current-in-place-example
  namespace: version-lab
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web-app
  updatePolicy:
    updateMode: InPlace
  resourcePolicy:
    containerPolicies:
    - containerName: app
      minAllowed:
        cpu: 100m
      maxAllowed:
        cpu: '4'
      controlledResources:
      - cpu
      controlledValues: RequestsAndLimits
```

#### ServiceCIDR 和 IPAddress：GA

在启用分配器/API 的情况下，上游 Kubernetes 可以通过额外的 `networking.k8s.io/v1` ServiceCIDR 对象扩展可用的 Service 地址。名为 `kubernetes` 的默认对象代表 API server 的初始范围。添加范围前请审核 IPAM、地址族和路由重叠；finalizer 会阻止删除可能导致已分配 Service IP 孤立的范围。ServiceCIDR 不是 VPC 子网，也不是 Pod 地址 CIDR。

此 IPv4 清单是上游示例，并非已执行的 EKS 地址范围扩展。EKS 的 `serviceIpv4Cidr` 创建参数在集群创建后不可变。创建另一个 Kubernetes ServiceCIDR 是不同的操作；本次审核的 AWS 资料没有确立经过测试的 EKS 操作流程。在 EKS 上使用前，请确认供应商支持、准入策略和目标网络。仅发现 API 并不构成验证。

```yaml
apiVersion: networking.k8s.io/v1
kind: ServiceCIDR
metadata:
  name: reviewed-extra-service-range
spec:
  cidrs:
  - 10.200.0.0/16
```

```bash
# Read-only discovery; do not interpret availability alone as an approved EKS change.
set -euo pipefail
: "${KUBE_CONTEXT:?}"
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s api-resources --api-group=networking.k8s.io
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get servicecidrs
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get ipaddresses
```

#### 拓扑感知路由与流量分布：GA

拓扑感知端点提示和 Service `trafficDistribution` 偏好相关但并不相同。以下示例使用 `PreferClose` 表达同一区域优先；它不是严格的同区域保证、区域间距离计算，也不意味着某个注解在所有情况下都已弃用。就绪端点分布、代理实现以及 `internalTrafficPolicy`/`externalTrafficPolicy` 都可能影响路由。

跨 AZ 流量可能产生费用，但之前简单写成 `$0.01/GB` 的说法并不是完整的定价模型。费用取决于服务、路径以及计费的入站/出站方向；部分同 Region 流量存在例外。应比较实际流量和账单数据，而不是承诺固定节省金额。

```yaml
apiVersion: v1
kind: Service
metadata:
  name: same-zone-preference
  namespace: version-lab
spec:
  trafficDistribution: PreferClose
  selector:
    app: web-app
  ports:
  - port: 80
    targetPort: 8080
```

#### Job 成功策略：GA

成功策略适用于 Indexed Jobs。此处要求索引 0 成功；只有当应用实现相应协议时，它才代表主节点。Kubernetes 不会自行判断分布式结果是否完整或持久。失败策略和剩余 Pod 的终止仍然重要。Job 模板明确设置了 `restartPolicy: Never`，旧示例中缺少此项。

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: indexed-success-example
  namespace: version-lab
spec:
  completionMode: Indexed
  completions: 8
  parallelism: 8
  backoffLimit: 2
  successPolicy:
    rules:
    - succeededIndexes: '0'
      succeededCount: 1
  template:
    spec:
      restartPolicy: Never
      containers:
      - name: trainer
        image: example.invalid/version-lab/training:reviewed
        env:
        - name: JOB_COMPLETION_INDEX
          valueFrom:
            fieldRef:
              fieldPath: metadata.annotations['batch.kubernetes.io/job-completion-index']
```

#### OCI 镜像卷：1.33 中为 Beta，默认禁用

镜像卷将 OCI 镜像内容提供给 Pod，例如模型数据，而无需将其嵌入应用镜像。它需要受支持的运行时、适当的功能配置和容器镜像仓库拉取身份。挂载为只读，不是可写 PVC。请审核并固定应用镜像和数据镜像。ImageVolume 在 1.35 默认启用，并于 1.36 稳定，而非在 1.34 达到 GA。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: image-volume-example
  namespace: version-lab
spec:
  containers:
  - name: inference
    image: example.invalid/version-lab/inference:reviewed
    volumeMounts:
    - name: model
      mountPath: /models
      readOnly: true
  volumes:
  - name: model
    image:
      reference: example.invalid/version-lab/model:reviewed
      pullPolicy: IfNotPresent
```

#### 1.33 中其他选定阶段

| 功能 | 状态 |
|---|---|
| NFTablesProxyMode、RecursiveReadOnlyMounts | GA |
| CRDValidationRatcheting | GA；不代表可以绕过对已变更无效字段的验证 |
| MatchLabelKeysInPodAffinity、NodeInclusionPolicyInPodTopologySpread | GA |
| PersistentVolume 回收策略删除保护 | GA；与 PVC 使用中保护不同 |
| UserNamespacesSupport | Beta，现在默认启用 |
| PodLevelResources | 仍为 Alpha；1.34 进入 Beta |
| StructuredAuthenticationConfiguration | Beta；1.34 达到 GA |
| MutatingAdmissionPolicy | 仍为 Alpha；1.34 进入 Beta |
| PodLifecycleSleepAction | Beta；1.34 达到 GA |
| JobManagedBy | Beta；1.35 达到 GA |

LoadBalancerIPMode 和 RetryGenerateName 已在 1.32 达到 GA。KYAML 在 1.34 引入，并非 1.33。

[Kubernetes 1.33 发布公告](https://kubernetes.io/blog/2025/04/23/kubernetes-v1-33-release/) · [版本化的 1.36 调整指南](https://github.com/kubernetes/website/blob/release-1.36/content/en/docs/tasks/configure-pod-container/resize-container-resources.md) · [VPA 1.8.0 功能](https://github.com/kubernetes/autoscaler/blob/vertical-pod-autoscaler-1.8.0/vertical-pod-autoscaler/docs/features.md) · [VPA 1.8.0 兼容性](https://github.com/kubernetes/autoscaler/blob/vertical-pod-autoscaler-1.8.0/vertical-pod-autoscaler/docs/installation.md#compatibility) · [扩展 Service 地址范围](https://kubernetes.io/docs/tasks/network/extend-service-ip-ranges/) · [EKS 网络配置 API](https://docs.aws.amazon.com/eks/latest/APIReference/API_KubernetesNetworkConfigRequest.html) · [数据传输费用说明](https://docs.aws.amazon.com/cur/latest/userguide/cur-data-transfers-charges.html)

---

### 4.6 Kubernetes 1.34 “Of Wind & Will”（2025年8月）

8月27日发布的版本列出 **58 项增强功能：23 项稳定、22 项 Beta、13 项 Alpha**。各 Beta 功能的默认状态不同；图中的通用“默认启用”箭头不是启用状态矩阵。

![Kubernetes 1.34“Of Wind & Will”的58项增强功能按成熟度阶段分为23项稳定（GA）、22项Beta和13项Alpha，并突出显示晋级GA的路径、默认启用的Beta和需要功能门控的Alpha。](../.gitbook/assets/en-eks-12-kubernetes-version-roadmap-12.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-12-kubernetes-version-roadmap-12.html)

#### DRA 核心 API：GA

DeviceClass、ResourceClaim、ResourceClaimTemplate 和 ResourceSlice 是内置的 `resource.k8s.io/v1` API，并非需要安装的 DRA 核心 CRD。驱动程序通过 ResourceSlices 发布设备清单；调度器分配符合条件的资源，kubelet 再与驱动程序协调设备准备。架构图展示的是逻辑流程，并省略了 API server/ResourceSlice 传输过程。

DRA 不会移除现有 device-plugin 模型，也不会自动提供所有厂商的 time-slicing、MPS、MIG、NUMA 或网络功能。高级 DRA 功能有各自独立的门控和阶段。不要在没有受支持协调模型的情况下，让两个独立分配器管理同一批设备。

![Dynamic Resource Allocation 架构图，该功能在 Kubernetes 1.34 达到 GA：DeviceClass 将 ResourceClaims 和 ResourceClaimTemplates 提供给感知设备的调度器；调度器还会从 DRA 驱动程序获取设备信息，然后由 kubelet 准备设备。](../.gitbook/assets/en-eks-12-kubernetes-version-roadmap-13.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-12-kubernetes-version-roadmap-13.html)

以下示例采用**明确的合成驱动程序契约**：`gpu.example.com` 发布字符串 `model` 属性和 `numa` 属性。这并非关于实际 NVIDIA 驱动属性名称或配置的说法。检查已安装驱动程序的 ResourceSlices 后，再替换驱动程序/属性。在稳定版请求中，`deviceClassName`、`allocationMode` 和 `count` 属于 `exactly` 之下；旧的根级写法不正确。`matchAttribute` 是对请求设备的硬性相等约束，而不是 NUMA 偏好。

```yaml
apiVersion: resource.k8s.io/v1
kind: DeviceClass
metadata:
  name: example-a100
spec:
  selectors:
  - cel:
      expression: 'device.driver == "gpu.example.com" &&

        "gpu.example.com" in device.attributes &&

        "model" in device.attributes["gpu.example.com"] &&

        device.attributes["gpu.example.com"].model == "A100"'
---
apiVersion: resource.k8s.io/v1
kind: ResourceClaim
metadata:
  name: training-gpus
  namespace: version-lab
spec:
  devices:
    requests:
    - name: gpu
      exactly:
        deviceClassName: example-a100
        allocationMode: ExactCount
        count: 4
    constraints:
    - requests:
      - gpu
      matchAttribute: gpu.example.com/numa
---
apiVersion: resource.k8s.io/v1
kind: ResourceClaimTemplate
metadata:
  name: four-gpu-template
  namespace: version-lab
spec:
  spec:
    devices:
      requests:
      - name: gpu
        exactly:
          deviceClassName: example-a100
          allocationMode: ExactCount
          count: 4
      constraints:
      - requests:
        - gpu
        matchAttribute: gpu.example.com/numa
```

请根据预期生命周期，选择显式管理的 claim，或从模板为每个 Pod 创建 claim。以下示例展示两种选择。模板请求四个设备，因此与 `--tensor-parallel-size 4` 相符；先前只请求一个设备的模板并不匹配。推理镜像必须实现此参数，且所有镜像均为占位符。一个副本需要四个符合条件的设备；三个这样的副本需要十二个。此处没有运行 GPU 分配或模型服务基准测试。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: direct-gpu-claim
  namespace: version-lab
spec:
  resourceClaims:
  - name: accelerators
    resourceClaimName: training-gpus
  containers:
  - name: trainer
    image: example.invalid/version-lab/trainer:reviewed
    resources:
      claims:
      - name: accelerators
        request: gpu
```

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: four-gpu-serving
  namespace: version-lab
spec:
  replicas: 1
  selector:
    matchLabels:
      app: four-gpu-serving
  template:
    metadata:
      labels:
        app: four-gpu-serving
    spec:
      resourceClaims:
      - name: accelerators
        resourceClaimTemplateName: four-gpu-template
      containers:
      - name: inference
        image: example.invalid/version-lab/inference:reviewed
        args:
        - --tensor-parallel-size
        - '4'
        resources:
          claims:
          - name: accelerators
            request: gpu
```

#### VolumeAttributesClass：GA

VAC 从 1.34 起使用 `storage.k8s.io/v1`。这些类针对标准 `ebs.csi.aws.com` 驱动程序和现有的兼容区域 gp3 卷；它们并不是可直接用于 Auto Mode 的存储配方。更改 PVC 的类之前，请确认驱动程序/sidecar 支持、API 版本、权限、卷大小/类型、修改冷却时间和实例 EBS 限制。

当前区域 gp3 上限为 **80,000 IOPS 和 2,000 MiB/s**；超过 3,000 IOPS 基准后，每 GiB 可提供 500 IOPS，每个已配置 IOPS 对应 0.25 MiB/s。因此，原先的 64,000 IOPS 值可能有效（卷至少 128 GiB），而 4,000 MiB/s 不是有效的 gp3 吞吐量值。此示例将其更正为 2,000，并假定已验证卷容量为 500 GiB。Outposts 的上限较低（16,000 IOPS / 1,000 MiB/s）。已配置的卷限制不能保证应用或实例能够持续达到该性能。

```yaml
apiVersion: storage.k8s.io/v1
kind: VolumeAttributesClass
metadata:
  name: high-iops
driverName: ebs.csi.aws.com
parameters:
  iops: '16000'
  throughput: '1000'
---
apiVersion: storage.k8s.io/v1
kind: VolumeAttributesClass
metadata:
  name: standard
driverName: ebs.csi.aws.com
parameters:
  iops: '3000'
  throughput: '125'
---
apiVersion: storage.k8s.io/v1
kind: VolumeAttributesClass
metadata:
  name: io-intensive
driverName: ebs.csi.aws.com
parameters:
  iops: '64000'
  throughput: '2000'
---
apiVersion: storage.k8s.io/v1
kind: VolumeAttributesClass
metadata:
  name: throughput-optimized
driverName: ebs.csi.aws.com
parameters:
  iops: '3000'
  throughput: '750'
```

类的参数不可变；应通过现有 PVC 选择另一个类，而不是原地编辑类或创建不完整的 PVC。请确认 `.status.currentVolumeAttributesClassName`、`.status.modifyVolumeStatus`、事件和实际 EBS 状态。请求被接受不代表性能变更已完成。

旧的工作日 CronJob 示例缺少身份/RBAC 以及时区/重叠处理。以下完整的**暂停状态骨架**仍只是未经执行的运维示例：需准备 `version-lab`、自有的 `database-pvc`、兼容类，以及包含 kubectl/jq 和可信客户端配置的已审核镜像。其 ServiceAccount 只能在该命名空间中对指定 PVC 执行 get/patch；RBAC 不限制 patch 可以更改哪些 PVC 字段。

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: vac-scheduler
  namespace: version-lab
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: vac-scheduler
  namespace: version-lab
rules:
- apiGroups:
  - ''
  resources:
  - persistentvolumeclaims
  resourceNames:
  - database-pvc
  verbs:
  - get
  - patch
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: vac-scheduler
  namespace: version-lab
subjects:
- kind: ServiceAccount
  name: vac-scheduler
  namespace: version-lab
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: vac-scheduler
```

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: vac-business-hours
  namespace: version-lab
spec:
  schedule: 0 8 * * 1-5
  timeZone: Asia/Seoul
  suspend: true
  concurrencyPolicy: Forbid
  startingDeadlineSeconds: 300
  successfulJobsHistoryLimit: 1
  failedJobsHistoryLimit: 3
  jobTemplate:
    spec:
      backoffLimit: 0
      activeDeadlineSeconds: 120
      template:
        spec:
          serviceAccountName: vac-scheduler
          restartPolicy: Never
          containers:
          - name: request-class
            image: example.invalid/version-lab/kubectl-jq:reviewed
            command:
            - /bin/sh
            - -c
            - "set -eu\n: \"${POD_NAMESPACE:?}\"; : \"${TARGET_CLASS:?}\"\ncase \"\
              $TARGET_CLASS\" in high-iops|standard|io-intensive|throughput-optimized)\
              \ ;; *) exit 2 ;; esac\nstate=$(kubectl --request-timeout=15s -n \"\
              $POD_NAMESPACE\" get pvc database-pvc -o json)\npatch=$(printf '%s\\\
              n' \"$state\" | jq -ce --arg class \"$TARGET_CLASS\" '\n  if .metadata.deletionTimestamp\
              \ != null or .status.phase != \"Bound\"\n  then error(\"Expected an\
              \ existing non-deleting Bound PVC\")\n  elif .status.modifyVolumeStatus\
              \ != null\n  then error(\"Existing modification needs review before\
              \ another request\")\n  elif .spec.volumeAttributesClassName == $class\n\
              \  then []\n  else [\n    {op:\"test\",path:\"/metadata/uid\",value:.metadata.uid},\n\
              \    {op:\"test\",path:\"/metadata/resourceVersion\",value:.metadata.resourceVersion},\n\
              \    {op:\"add\",path:\"/spec/volumeAttributesClassName\",value:$class}\n\
              \  ] end')\nif [ \"$patch\" = '[]' ]; then\n  printf '%s\\n' 'Class\
              \ already requested; verify actual modification status separately.'\n\
              else\n  kubectl --request-timeout=15s -n \"$POD_NAMESPACE\" patch pvc\
              \ database-pvc --type=json --patch \"$patch\"\n  printf '%s\\n' 'Class\
              \ change requested; this is not proof of completed EBS modification.'\n\
              fi\n"
            env:
            - name: POD_NAMESPACE
              valueFrom:
                fieldRef:
                  fieldPath: metadata.namespace
            - name: TARGET_CLASS
              value: io-intensive
            resources:
              requests:
                cpu: 50m
                memory: 64Mi
              limits:
                cpu: 200m
                memory: 128Mi
---
apiVersion: batch/v1
kind: CronJob
metadata:
  name: vac-off-hours
  namespace: version-lab
spec:
  schedule: 0 22 * * 1-5
  timeZone: Asia/Seoul
  suspend: true
  concurrencyPolicy: Forbid
  startingDeadlineSeconds: 300
  successfulJobsHistoryLimit: 1
  failedJobsHistoryLimit: 3
  jobTemplate:
    spec:
      backoffLimit: 0
      activeDeadlineSeconds: 120
      template:
        spec:
          serviceAccountName: vac-scheduler
          restartPolicy: Never
          containers:
          - name: request-class
            image: example.invalid/version-lab/kubectl-jq:reviewed
            command:
            - /bin/sh
            - -c
            - "set -eu\n: \"${POD_NAMESPACE:?}\"; : \"${TARGET_CLASS:?}\"\ncase \"\
              $TARGET_CLASS\" in high-iops|standard|io-intensive|throughput-optimized)\
              \ ;; *) exit 2 ;; esac\nstate=$(kubectl --request-timeout=15s -n \"\
              $POD_NAMESPACE\" get pvc database-pvc -o json)\npatch=$(printf '%s\\\
              n' \"$state\" | jq -ce --arg class \"$TARGET_CLASS\" '\n  if .metadata.deletionTimestamp\
              \ != null or .status.phase != \"Bound\"\n  then error(\"Expected an\
              \ existing non-deleting Bound PVC\")\n  elif .status.modifyVolumeStatus\
              \ != null\n  then error(\"Existing modification needs review before\
              \ another request\")\n  elif .spec.volumeAttributesClassName == $class\n\
              \  then []\n  else [\n    {op:\"test\",path:\"/metadata/uid\",value:.metadata.uid},\n\
              \    {op:\"test\",path:\"/metadata/resourceVersion\",value:.metadata.resourceVersion},\n\
              \    {op:\"add\",path:\"/spec/volumeAttributesClassName\",value:$class}\n\
              \  ] end')\nif [ \"$patch\" = '[]' ]; then\n  printf '%s\\n' 'Class\
              \ already requested; verify actual modification status separately.'\n\
              else\n  kubectl --request-timeout=15s -n \"$POD_NAMESPACE\" patch pvc\
              \ database-pvc --type=json --patch \"$patch\"\n  printf '%s\\n' 'Class\
              \ change requested; this is not proof of completed EBS modification.'\n\
              fi\n"
            env:
            - name: POD_NAMESPACE
              valueFrom:
                fieldRef:
                  fieldPath: metadata.namespace
            - name: TARGET_CLASS
              value: throughput-optimized
            resources:
              requests:
                cpu: 50m
                memory: 64Mi
              limits:
                cpu: 200m
                memory: 128Mi
```

调度明确使用 Asia/Seoul。`Forbid` 只分别作用于各个 CronJob，并不是两个计划之间或与其他操作员共享的锁。UID/resourceVersion 测试保护 API patch，不会保护整个异步 EBS 操作。命令会拒绝已有修改，并且只报告已请求的类变更。在确定工作负载影响、后端状态检查、协调和恢复措施前，应保持调度暂停；本文不声称此方案已达到生产就绪状态。

#### 有序删除命名空间：GA

此变更会先删除 Pod，再删除其他命名空间资源，以帮助避免 Pod 仍在运行时网络策略等安全控制已被移除的情况。它不会计算任意依赖图，也不保证每次命名空间删除都能完成：不可用的 API、控制器和 finalizer 仍可能阻塞操作。应检查实际条件，而不是强制移除 finalizer 或把示例记录当作实测修复结果。

#### KYAML：客户端输出格式，1.34 中为 Alpha

KYAML 对应 **KEP-5295**，不是 KEP-4222。它是一种歧义更少、与 YAML 兼容的输出格式，使用显式分隔符和带引号的字符串值。它不是 API server 准入验证器，不是全局 YAML 1.2 迁移，也不要求每个清单都移除锚点。它在 kubectl 1.35 中成为 Beta/默认启用，1.36 中仍为 Beta，并在 1.37 晋级为稳定版。

将以下普通 YAML 保存为 `format-example.yaml`。此本地示例已使用 kubectl 1.36.2 实际检查：它接受锚点，并在输出中保留两个 `"no"` 字符串。它不会连接集群。

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: kyaml-local-example
data:
  first: &string_value "no"
  norway: *string_value
```

```bash
# Local formatting example, checked with kubectl 1.36.2; no cluster request.
kubectl --kubeconfig=/dev/null --server=https://127.0.0.1:1 --request-timeout=1s \
  label --local --dry-run=client -f format-example.yaml \
  audit.example.com/checked=true -o kyaml
```

在 kubectl 1.36.2 中，`KUBECTL_KYAML=false` 会禁用 `-o kyaml` 输出器，但 KYAML 格式的输入仍会作为 YAML 被其他输出格式解析。它不会更改 EKS 控制平面设置。Schema/准入验证与格式化是两项不同的检查。此前有关 KYAML 警告/拒绝的输出并不是对服务器端功能的有效演示。

#### MutatingAdmissionPolicy：1.34 中为 Beta

MAP 在 1.32 进入 Alpha、1.34 进入 Beta（默认禁用），并在 1.36 达到 GA。以下是**当前 1.36+ 稳定格式**，不是可以原样应用于 1.34 的清单；历史 Beta API 为 `v1beta1`，需要相应的 API 提供/门控配置。EKS 控制平面门控仍由 AWS 管理。

此策略为 Deployment 添加默认标签，同时保留已有的显式值。根据命名空间生成的成本标签仅作示意，并非经过验证的财务分摊规则。绑定只选择明确启用的命名空间。`failurePolicy: Fail` 仍可能因评估错误而阻止匹配请求。此表达式已使用 Kubernetes 1.36.2 原生 mutation compiler/patcher 对合成 Deployment 进行测试；没有测试完整准入链或生产环境。CEL 的确定性不意味着所有组合策略都必然幂等，也不能消除重新调用/顺序方面的考量。

```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: MutatingAdmissionPolicy
metadata:
  name: version-lab-default-labels
spec:
  failurePolicy: Fail
  reinvocationPolicy: IfNeeded
  matchConstraints:
    resourceRules:
    - apiGroups:
      - apps
      apiVersions:
      - v1
      operations:
      - CREATE
      resources:
      - deployments
  mutations:
  - patchType: ApplyConfiguration
    applyConfiguration:
      expression: "Object{\n  metadata: Object.metadata{\n    labels: {\n      \"\
        app.kubernetes.io/managed-by\":\n        has(object.metadata.labels) && \"\
        app.kubernetes.io/managed-by\" in object.metadata.labels\n        ? object.metadata.labels[\"\
        app.kubernetes.io/managed-by\"] : \"platform-team\",\n      \"cost-center\"\
        :\n        has(object.metadata.labels) && \"cost-center\" in object.metadata.labels\n\
        \        ? object.metadata.labels[\"cost-center\"] : request.namespace\n \
        \   }\n  }\n}"
---
apiVersion: admissionregistration.k8s.io/v1
kind: MutatingAdmissionPolicyBinding
metadata:
  name: version-lab-default-labels
spec:
  policyName: version-lab-default-labels
  matchResources:
    namespaceSelector:
      matchLabels:
        version-lab-policy: enabled
```

#### 1.34 中其他选定阶段

| 功能 | 状态 |
|---|---|
| PodLevelResources | Beta，默认启用；尚未 GA |
| ImageVolume | Beta，直到 1.35 前默认禁用 |
| UserNamespacesSupport | Beta，默认启用；1.36 达到 GA |
| NFTablesProxyMode、MatchLabelKeysInPodAffinity、CRDValidationRatcheting | 已于 1.33 达到 GA |
| KubeletTracing、PodLifecycleSleepAction | GA；后者涵盖 PreStop sleep 动作 |
| JobPodReplacementPolicy、RecoverVolumeExpansionFailure | GA |
| StructuredAuthenticationConfiguration、AnonymousAuthConfigurableEndpoints | GA |
| NodeLogQuery | 仍为 Beta；1.36 达到 GA |

这些示例没有标准的 `IfNotPresentOrNewer` 镜像拉取策略；应使用受支持的 `Always`、`IfNotPresent` 或 `Never` 语义，并单独审核镜像不可变性。

[Kubernetes 1.34 发布公告](https://kubernetes.io/blog/2025/08/27/kubernetes-v1-34-release/) · [DRA](https://kubernetes.io/docs/concepts/scheduling-eviction/dynamic-resource-allocation/) · [EBS gp3 限制](https://docs.aws.amazon.com/ebs/latest/userguide/general-purpose.html) · [KYAML KEP-5295](https://github.com/kubernetes/enhancements/tree/master/keps/sig-cli/5295-kyaml) · [Kubernetes 1.37 变更日志](https://github.com/kubernetes/kubernetes/blob/v1.37.0/CHANGELOG/CHANGELOG-1.37.md) · [MutatingAdmissionPolicy](https://kubernetes.io/docs/reference/access-authn-authz/mutating-admission-policy/)

---

### 4.7 Kubernetes 1.35 “Timbernetes”（2025年12月）

12月17日的公告报告 **60 项增强功能**，标题中的成熟度分类为 **17 项稳定、19 项 Beta、22 项 Alpha**。这三项合计为 58；该分类没有逐项说明另外两项。此处保留原始公布总数，不臆造其他类别，也不将其解读为性能测量结果。

![Kubernetes 1.35“Timbernetes”增强功能生命周期图，按 Alpha、Beta、Stable 晋级路径划分成熟度：总计60项，其中22项Alpha、19项Beta、17项Stable（GA），突出显示Stable，并列出各阶段的主要功能。](../.gitbook/assets/en-eks-12-kubernetes-version-roadmap-15.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-12-kubernetes-version-roadmap-15.html)

#### 容器资源原地调整：GA

该功能历经 1.27 Alpha、1.33 Beta，在 1.35 稳定。最初的 Alpha 阶段并非简单地“到 1.33 前只能调整 CPU”。GA 使 API 稳定，但不保证所有内存调整、运行时、节点策略或应用都不会受到干扰。请使用前文调整示例中的 UID/resourceVersion 检查和当前状态字段，并审核按版本列出的限制。

正常的 Deployment 模板更新仍会触发其滚动更新行为。不能仅因 Pod API 已达 GA，就认为 Deployment 会自动进行“滚动原地调整”。调整受管理的 Pod 与修改其控制器模板是两种不同操作。替换 Pod 会经过模板/准入流程，因此应协调 HPA、VPA、GitOps 及任何自定义调整器，避免多个资源所有者相互竞争。

此 Deployment 提供前述 VPA 示例使用的 `web-app`/`app` 目标。镜像和资源值仍需审核；应用必须实际实现诸如 8080 端口的 Service 端点。此处没有在 EKS 上测试滚动更新、资源调整或服务可用性。

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
  namespace: version-lab
spec:
  replicas: 2
  selector:
    matchLabels:
      app: web-app
  template:
    metadata:
      labels:
        app: web-app
    spec:
      containers:
      - name: app
        image: example.invalid/version-lab/app:reviewed
        resources:
          requests:
            cpu: 500m
            memory: 256Mi
          limits:
            cpu: '1'
            memory: 512Mi
        resizePolicy:
        - resourceName: cpu
          restartPolicy: NotRequired
        - resourceName: memory
          restartPolicy: RestartContainer
```

VPA 有独立的版本。`InPlaceOrRecreate` 在 VPA 1.6 达到 GA，并可能在原地更新失败时重建 Pod；`InPlace` 是 VPA 1.7 的 Alpha 模式，需要单独启用门控。其不驱逐 Pod 的行为，并不意味着所有容器调整策略都无需重启，也不意味着所有建议都能应用。前文当前版本的 VPA 示例已说明这些要求。单凭 Kubernetes 1.35 并不能启用 VPA 模式。

#### PreferSameNode 流量分布：GA

`PreferSameTrafficDistribution` 功能在 1.35 稳定。`PreferSameNode` 表示有本地节点端点可用时优先使用，并允许回退；它不同于严格的 `internalTrafficPolicy: Local` 规则。请核实实际 Service 实现、就绪端点和流量策略优先级。它不是对 ALB/NLB 路由的通用控制，也不保证跨可用区流量为零。

```yaml
apiVersion: v1
kind: Service
metadata:
  name: prefer-same-node
  namespace: version-lab
spec:
  trafficDistribution: PreferSameNode
  selector:
    app: web-app
  ports:
  - port: 80
    targetPort: 8080
```

#### KYAML：Beta，在 kubectl 中默认启用

KYAML 在 1.35 中的 Beta/默认启用状态针对 `-o kyaml` 输出格式。它不会让所有 API server 输入都改用新的严格解析器，不会对每个 YAML 锚点发出警告，也不要求向 EKS 支持团队提交工单来更改服务器功能门控。前文的本地格式化示例和原生 1.36.2 检查展示了实际行为。KYAML 在 1.37 才稳定，而非 1.36。

#### 原生 gang 调度：Alpha，KEP-4671

Kubernetes 1.35 引入了原生、感知工作负载的/gang 调度概念。它们在 1.36 中仍为 Alpha，需要启用 `GenericWorkload`/`GangScheduling` 以及相应的 API/调度器配置。EKS 版本常见问题不支持 Alpha 功能；在自行管理的节点上设置门控无法启用 EKS 控制平面不可用的 API。

以下是**上游实验环境的 1.36 `v1alpha2` Schema 示例**，并非旧版 1.35 Schema，也不是 GA EKS 配方。它使用 `spec.schedulingPolicy.gang.minCount` 和 Pod `spec.schedulingGroup.podGroupName`。旧字段 `minMember`/`scheduleTimeoutSeconds`，以及单独的 Pod 标签/调度门控，都不能定义此原生 API。第三方 PodGroup CRD 有自己的契约。

```yaml
apiVersion: scheduling.k8s.io/v1alpha2
kind: PodGroup
metadata:
  name: experimental-training
  namespace: version-lab
spec:
  schedulingPolicy:
    gang:
      minCount: 8
```

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: experimental-training
  namespace: version-lab
spec:
  completionMode: Indexed
  completions: 8
  parallelism: 8
  backoffLimit: 0
  template:
    spec:
      restartPolicy: Never
      schedulingGroup:
        podGroupName: experimental-training
      containers:
      - name: worker
        image: example.invalid/version-lab/worker:reviewed
        resources:
          requests:
            cpu: 100m
            memory: 64Mi
          limits:
            cpu: '1'
            memory: 256Mi
```

最小组大小、Job parallelism 和 completions 都是 8。这是独立的组示例：所有者/控制器必须管理组生命周期，并在 Pod 调度期间保持其关联稳定。调度决策并不保证进程同时启动、就绪、分布式计算成功，或不存在任何死锁。应用仍需要屏障、超时/恢复逻辑和兼容的容量。这些对象仅通过了 Schema 检查；没有执行组放置实验。

#### 选定的版本与升级注意事项

| 主题 | 正确解释 |
|---|---|
| JobManagedBy | 在 1.35 达到 GA |
| ImageVolume | Beta，现在默认启用；1.36 达到 GA |
| PodLevelResources | 在 1.34 晋级为 Beta 后仍为 Beta |
| UserNamespacesSupport | 仍为 Beta；1.36 达到 GA |
| ContextualLogging | 仍为 Beta，并未在 1.35 达到 GA |
| CRDValidationRatcheting | 已于 1.33 达到 GA |
| NodeInclusionPolicyInPodTopologySpread | 已于 1.33 达到 GA |
| RecoverVolumeExpansionFailure / 可配置匿名端点 | 已于 1.34 达到 GA |

升级节点时，应检查 cgroup/运行时要求，而不是假设“GA 就意味着生产安全”。EKS 的 1.35 说明介绍了 kubelet 默认拒绝 cgroup v1 的行为，以及 Fargate 等特定供应商场景；不要编辑由 AWS 管理的 Fargate 主机设置。根据该指导，Kubernetes 1.35 是最后一个支持 containerd 1.x 的版本，并且 kubelet 的 `--pod-infra-container-image` 标志已移除。应使用当前 EKS 节点/AMI 流程和升级章节；不要盲目覆盖引导标志。

[Kubernetes 1.35 发布公告](https://kubernetes.io/blog/2025/12/17/kubernetes-v1-35-release/) · [版本化的 1.36 功能门控](https://github.com/kubernetes/kubernetes/blob/v1.36.2/pkg/features/kube_features.go) · [Kubernetes 1.36.2 API Schema](https://github.com/kubernetes/kubernetes/blob/v1.36.2/api/openapi-spec/swagger.json) · [EKS 版本说明](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions-standard.html)

---

### 4.8 Kubernetes 1.36 “Haru”（2026年4月）

4月22日的公告报告 **70 项增强功能**，成熟度分类包括 **18 项稳定、25 项 Beta、25 项 Alpha**。这三组总计 68 项；原章节错误地将该小计用作发布总数。EKS 提供该版本的时间另见支持日历。

<!-- Parent repair: release total is70, not68; verify stage/default/provider labels before restoring.
![Kubernetes 1.36 "Haru" enhancement breakdown: 68 enhancements split by maturity stage into 25 Alpha, 25 Beta, and 18 Stable (GA), with Stable highlighted and EKS 1.36 availability across all regions including GovCloud (US).](../.gitbook/assets/en-eks-12-kubernetes-version-roadmap-17.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-12-kubernetes-version-roadmap-17.html)
-->

#### MutatingAdmissionPolicy：GA

MAP 的稳定资源是 `admissionregistration.k8s.io/v1` 中的 `MutatingAdmissionPolicy` 和 `MutatingAdmissionPolicyBinding`。对于受支持的变更，进程内 CEL 无需独立 Webhook，但策略失败、成本限制、执行顺序和重新调用仍需考虑。确定性不构成普遍的幂等性保证。

以下 resize 策略示例明确采用 opt-in。它只为尚未设置有效 `resizePolicy` 的容器添加默认值，并保留现有的显式策略。Kubernetes CEL 支持 `indexOf()`；原表达式有效，但会覆盖现有策略。使用 Kubernetes 1.36.2 原生 compiler/patcher 的测试验证了原行为及此修正。`resizePolicy` 是原子列表，因此 ApplyConfiguration patcher 会拒绝对该字段进行变更；这里适合使用 JSONPatch。此实现中，MAP 内 JSONPatch 的 `test` 失败会作为无操作处理，不会自动拒绝准入。

```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: MutatingAdmissionPolicy
metadata:
  name: inject-resizepolicy
spec:
  failurePolicy: Fail
  reinvocationPolicy: Never
  matchConstraints:
    resourceRules:
    - apiGroups:
      - ''
      apiVersions:
      - v1
      operations:
      - CREATE
      resources:
      - pods
  matchConditions:
  - name: only-resize-enabled
    expression: has(object.metadata.annotations) && ("resize.example.com/enabled"
      in object.metadata.annotations) && object.metadata.annotations["resize.example.com/enabled"]
      == "true"
  mutations:
  - patchType: JSONPatch
    jsonPatch:
      expression: "object.spec.containers.filter(c, !has(c.resizePolicy)).map(c, JSONPatch{\n\
        \  op: \"add\",\n  path: \"/spec/containers/\" + string(object.spec.containers.indexOf(c))\
        \ + \"/resizePolicy\",\n  value: [\n    {\"resourceName\": \"cpu\",    \"\
        restartPolicy\": \"NotRequired\"},\n    {\"resourceName\": \"memory\", \"\
        restartPolicy\": \"RestartContainer\"}\n  ]\n})"
---
apiVersion: admissionregistration.k8s.io/v1
kind: MutatingAdmissionPolicyBinding
metadata:
  name: inject-resizepolicy-binding
spec:
  policyName: inject-resizepolicy
  matchResources:
    namespaceSelector:
      matchLabels:
        map-demo: 'true'
```

绑定只应选择带标签的自有测试命名空间。如果求值失败，`failurePolicy: Fail` 仍可能拒绝匹配 Pod 的创建。在工作负载中启用前，请验证策略就绪状态、负向用例和完整准入链；固定等待一段时间并不能保证策略已就绪。仅观察到字段被注入，并不能确定是哪个准入组件生成了它。

#### 原地调整与 Pod 级预算

每容器资源调整已在 1.35 达到 GA。独立的 `InPlacePodLevelResourcesVerticalScaling` 功能在 1.36 进入 Beta/默认启用，同时 PodLevelResources 仍为 Beta。Pod 级预算和容器限制需要采用不同的核算和策略检查。以下示例不受下面的 CPU 降配原型管理；该原型会有意拒绝 Pod 级预算。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: pod-budget-example
  namespace: version-lab
spec:
  os:
    name: linux
  nodeSelector:
    kubernetes.io/os: linux
  resources:
    requests:
      cpu: '2'
      memory: 4Gi
    limits:
      cpu: '4'
      memory: 8Gi
  containers:
  - name: app
    image: example.invalid/version-lab/app:reviewed
    resources:
      requests:
        cpu: '1'
        memory: 2Gi
  - name: helper
    image: example.invalid/version-lab/helper:reviewed
    resources:
      requests:
        cpu: 500m
        memory: 512Mi
```

CPUManager 检查点改进并不能证明所有 static CPU/Memory-manager 工作负载都能调整资源或保留特定 NUMA 放置。这些路径有单独的功能/支持要求。`NotRequired` 表示策略不强制重启，并不排除所有可能的干扰。使用 `RestartContainer` 时，资源变更会请求重启；使用 `NotRequired` 时，内存缩小属于尽力而为，可能停滞或与 OOM 竞争。请监控实际容器资源和应用行为。

#### User namespaces、kubelet 授权与设备健康

UserNamespacesSupport 在 **1.36** 达到 GA；已发布的 1.36.2 源码中仍存在该门控，并且已锁定。Pod 通过 `hostUsers: false` 启用此功能，并要求兼容的内核/文件系统/运行时。UID 重映射是纵深防御，不能证明所有逃逸都无害，也不能证明所有应用都无需变更。

KubeletFineGrainedAuthz 也达到 GA。它会在较广泛的 `nodes/proxy` 回退之前，对 `/pods`、`/runningPods`、`/configz` 和 `/healthz` 进行更细粒度的检查。`/metrics`、`/stats` 和 `/logs` 已有各自的子资源区分。不要将此功能与控制 kubelet 访问 API server 的 Node 授权器规则混淆；请检查调用者的实际权限，并在较窄的访问权限足够时避免授予宽泛的代理权限。

ResourceHealthStatus 在 1.36 进入 Beta，并可报告 device plugins 和 DRA 的逐设备健康情况。请检查 `status.containerStatuses[].allocatedResourcesStatus`；而 `status.resourceClaimStatuses` 映射的是 claim 引用/生成的名称。缺少、Unknown 或 Unhealthy 状态需要结合驱动程序/节点/应用信息排查；它本身不能证明根因，也不授权重置设备。

```bash
# Read-only per-container resource health; no device reset or Pod deletion.
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${POD_NAME:?}"
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n "$NAMESPACE" get pod "$POD_NAME" -o json |
  jq '{uid:.metadata.uid,containers:[.status.containerStatuses[]? |
       {name,allocatedResourcesStatus}]}'
```

LegacyServiceAccountTokenCleanUp 早在 **1.30** 就已达到 GA，并非 1.36 新近晋级 GA。清理逻辑会依据 ServiceAccount 引用以及其他使用/挂载条件区分自动生成的旧版令牌 Secret。默认情况下，令牌闲置一年后会失效，并在再经过一段闲置时间后删除。这不表示所有旧令牌或手动创建的令牌都会被移除。应优先使用有时限的 TokenRequest 令牌；不要为了审计而打印令牌值。

#### SELinux、网络与其他兼容性变更

已发布的 1.36.2 门控定义将 **SELinuxMountReadWriteOncePod** 和 **SELinuxChangePolicy**（GA）与 **SELinuxMount**（仍为 Beta/默认关闭）区分开来。部分概要文档对此作了更宽泛的描述。请检查实际节点和供应商配置、CSI 支持及卷共享模式，而不要声称所有卷现在都采用相同的挂载标签行为。共享卷使用不同的 SELinux 标签时，可能需要专门审核。

`StrictIPCIDRValidation` 在 1.36 进入 Beta/默认启用。创建或更改经检查的内置字段时，应使用规范 IP/CIDR 值；已有存储值可能通过 validation-ratcheting 兼容，这并不会自动规范化所有 CRD。尽管 API Schema 仍接受 `gitRepo` 卷字段，该卷驱动程序在 1.36 中永久禁用：kubelet 会拒绝运行此类卷。升级前应迁移相应工作负载模式。

Service 的 `externalIPs` 在 1.36 弃用；公布的移除目标是未来计划，并非在此版本移除。上游 1.36.2 仍包含并实例化 IPVS proxier。AWS 版本摘要中的移除措辞与该上游代码相矛盾；不要将其扩展为通用的上游移除结论，也不要假定特定 EKS add-on 镜像仍受支持。应单独核实所选 EKS add-on 和迁移路径。此处没有测试 EKS IPVS 运行环境。

ImageVolume 和 NodeLogQuery 在 1.36 达到 GA。DRA 可分区设备、可消耗容量和设备绑定条件各有自己的 Beta 门控。KYAML 在 1.36 中仍是 kubectl Beta 功能（1.37 稳定），而 GenericWorkload/GangScheduling 在 1.36 中仍为 Alpha。不要把此前已 GA 的功能重新标记为 1.36 新晋级的功能。

#### 感知阶段的 CPU 降配原型

启动阶段 CPU 密集的应用可能受益于不同的稳态 CPU 分配，但应针对该应用测量合适的下限。Kubernetes 的 `Running` 不是预热完成信号。以下**实验性、未在集群中执行的控制器**默认使用真实的 startupProbe 信号，并采用范围有限的仅 CPU 契约。它不是生产就绪控制器，也不保证可用性。

它要求提供一个 `WATCH_NAMESPACE` 和一个经过审核的正数 `MIN_STEADY_CPU`。它只监视该命名空间中带 `resize.example.com/managed=true` 标签的 Pod，并且还要求存在 opt-in 注解。标签/注解选择不是授权边界；该命名空间中的工作负载写入者必须可信。此示例仅接受显式选择的 Linux、容器级 Guaranteed Pod，其应用/init 的 CPU 和内存 requests 必须等于 limits。它会拒绝内存变更、升配、无效目标、不受支持的 CPU 重启策略、待处理的调整，以及未经确认/数值不相等的观测资源。

默认的 StartupProbePassed 要求每个目标都配置实际的 startupProbe，且 `started=true`。Ready 和 Delay 是明确的替代触发条件；Ready 需要有意义的就绪信号，而 Delay 只是计时器，不能证明预热完成。30 秒重新同步间隔及 API/协调延迟意味着这些时间都不是精确保证。

请使用相匹配的依赖项（审核使用 Go 1.27.1 和 Kubernetes 库 v0.36.2）：

```text
module example.com/pod-resizer

go 1.26.0

require (
    k8s.io/api v0.36.2
    k8s.io/apimachinery v0.36.2
    k8s.io/client-go v0.36.2
)
```

```go
// Experimental CPU-downscale controller for Kubernetes 1.36.
// Not a production-readiness or zero-downtime guarantee.
package main

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log"
	"os"
	"os/signal"
	"strconv"
	"strings"
	"sync"
	"syscall"
	"time"

	corev1 "k8s.io/api/core/v1"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
	"k8s.io/apimachinery/pkg/api/resource"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/types"
	"k8s.io/apimachinery/pkg/util/validation"
	"k8s.io/client-go/informers"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/cache"
	"k8s.io/client-go/util/workqueue"
)

const (
	managedLabel = "resize.example.com/managed"
	annEnabled   = "resize.example.com/enabled"
	annTrigger   = "resize.example.com/trigger"
	annDelay     = "resize.example.com/delay-seconds"
	annSteady    = "resize.example.com/steady-resources"
)

type config struct {
	namespace string
	minCPU    resource.Quantity
}

type resourceValues struct {
	Requests map[string]string `json:"requests"`
	Limits   map[string]string `json:"limits"`
}

type patchOperation struct {
	Op    string `json:"op"`
	Path  string `json:"path"`
	Value any    `json:"value"`
}

func main() {
	namespace := os.Getenv("WATCH_NAMESPACE")
	minCPU, err := resource.ParseQuantity(os.Getenv("MIN_STEADY_CPU"))
	if len(validation.IsDNS1123Label(namespace)) != 0 || err != nil || minCPU.Sign() <= 0 {
		log.Fatal("Set one valid WATCH_NAMESPACE and a reviewed positive MIN_STEADY_CPU")
	}
	cfg := config{namespace: namespace, minCPU: minCPU}
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	clientConfig, err := rest.InClusterConfig()
	if err != nil {
		log.Fatal("In-cluster client configuration unavailable")
	}
	clientConfig.QPS, clientConfig.Burst = 5, 10
	client, err := kubernetes.NewForConfig(clientConfig)
	if err != nil {
		log.Fatal("Client initialization failed")
	}
	factory := informers.NewSharedInformerFactoryWithOptions(client, 30*time.Second,
		informers.WithNamespace(namespace),
		informers.WithTweakListOptions(func(options *metav1.ListOptions) {
			options.LabelSelector = managedLabel + "=true"
		}))
	informer := factory.Core().V1().Pods().Informer()
	queue := workqueue.NewTypedRateLimitingQueue(workqueue.DefaultTypedControllerRateLimiter[string]())
	enqueue := func(obj any) {
		key, err := cache.MetaNamespaceKeyFunc(obj)
		if err == nil {
			queue.Add(key)
		}
	}
	_, err = informer.AddEventHandler(cache.ResourceEventHandlerFuncs{
		AddFunc: enqueue, UpdateFunc: func(_, current any) { enqueue(current) },
	})
	if err != nil {
		log.Fatal("Informer handler registration failed")
	}
	factory.Start(ctx.Done())
	if !cache.WaitForCacheSync(ctx.Done(), informer.HasSynced) {
		queue.ShutDown()
		return
	}
	log.Printf("Cache synchronized; watching one namespace: %s", namespace)
	var workers sync.WaitGroup
	workers.Add(1)
	go func() {
		defer workers.Done()
		for {
			key, shutdown := queue.Get()
			if shutdown {
				return
			}
			obj, exists, err := informer.GetIndexer().GetByKey(key)
			if err == nil && exists {
				pod, ok := obj.(*corev1.Pod)
				if ok {
					err = requestResize(ctx, client, pod, cfg, time.Now())
				}
			}
			if err != nil && ctx.Err() == nil && queue.NumRequeues(key) < 5 {
				queue.AddRateLimited(key)
			} else {
				queue.Forget(key)
				if err != nil {
					log.Printf("Request failed for %s (%s); later events/resync may retry", key, apierrors.ReasonForError(err))
				}
			}
			queue.Done(key)
		}
	}()
	<-ctx.Done()
	queue.ShutDown()
	workers.Wait()
}

func requestResize(ctx context.Context, client kubernetes.Interface, pod *corev1.Pod, cfg config, now time.Time) error {
	patch, err := buildResizePatch(pod, cfg, now)
	if err != nil {
		// Do not log annotation values, credentials or entire Pod objects.
		log.Printf("Configuration needs review for %s/%s: %v", pod.Namespace, pod.Name, err)
		return nil // Retry only on a later event/resync, not a tight error loop.
	}
	if len(patch) == 0 {
		return nil
	}
	requestCtx, cancel := context.WithTimeout(ctx, 10*time.Second)
	defer cancel()
	_, err = client.CoreV1().Pods(pod.Namespace).Patch(requestCtx, pod.Name,
		types.JSONPatchType, patch, metav1.PatchOptions{}, "resize")
	if err == nil {
		log.Printf("RESIZE_REQUESTED %s/%s uid=%s; verify kubelet status separately",
			pod.Namespace, pod.Name, pod.UID)
	}
	return err
}

func buildResizePatch(pod *corev1.Pod, cfg config, now time.Time) ([]byte, error) {
	if pod == nil || pod.Namespace != cfg.namespace || pod.Labels[managedLabel] != "true" ||
		pod.Annotations[annEnabled] != "true" || pod.DeletionTimestamp != nil ||
		pod.Status.Phase != corev1.PodRunning {
		return nil, nil
	}
	if pod.UID == "" || pod.ResourceVersion == "" {
		return nil, errors.New("missing Pod identity/version")
	}
	// This prototype deliberately handles only container-level Guaranteed Linux Pods.
	if pod.Spec.OS == nil || pod.Spec.OS.Name != corev1.Linux ||
		pod.Spec.NodeSelector[corev1.LabelOSStable] != "linux" ||
		pod.Spec.Resources != nil || pod.Status.QOSClass != corev1.PodQOSGuaranteed {
		return nil, errors.New("prototype requires declared Linux, container-level Guaranteed resources")
	}
	for _, c := range append(append([]corev1.Container{}, pod.Spec.Containers...), pod.Spec.InitContainers...) {
		for _, name := range []corev1.ResourceName{corev1.ResourceCPU, corev1.ResourceMemory} {
			request, hasRequest := c.Resources.Requests[name]
			limit, hasLimit := c.Resources.Limits[name]
			if !hasRequest || !hasLimit || request.Sign() <= 0 || request.Cmp(limit) != 0 {
				return nil, errors.New("all app/init resources must satisfy the Guaranteed contract")
			}
		}
	}
	if pod.Status.ObservedGeneration < pod.Generation {
		return nil, nil
	}
	for _, condition := range pod.Status.Conditions {
		if condition.Status == corev1.ConditionTrue &&
			(condition.Type == corev1.PodResizePending || condition.Type == corev1.PodResizeInProgress) {
			return nil, nil
		}
	}
	raw := pod.Annotations[annSteady]
	if len(raw) == 0 || len(raw) > 4096 {
		return nil, errors.New("missing or oversized steady-resources annotation")
	}
	var desired map[string]resourceValues
	decoder := json.NewDecoder(strings.NewReader(raw))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&desired); err != nil {
		return nil, errors.New("invalid steady-resources JSON shape")
	}
	if err := decoder.Decode(new(any)); err != io.EOF || len(desired) == 0 {
		return nil, errors.New("expected one nonempty steady-resources object")
	}
	trigger := pod.Annotations[annTrigger]
	if trigger == "" {
		trigger = "StartupProbePassed"
	}
	delay := 0
	switch trigger {
	case "StartupProbePassed", "Ready":
	case "Delay":
		var err error
		delay, err = strconv.Atoi(pod.Annotations[annDelay])
		if err != nil || delay < 1 || delay > 3600 {
			return nil, errors.New("Delay requires an integer from1 to3600 seconds")
		}
	default:
		return nil, errors.New("unknown trigger")
	}
	podReady := false
	for _, condition := range pod.Status.Conditions {
		if condition.Type == corev1.PodReady && condition.Status == corev1.ConditionTrue {
			podReady = true
		}
	}
	statuses := make(map[string]corev1.ContainerStatus, len(pod.Status.ContainerStatuses))
	for _, status := range pod.Status.ContainerStatuses {
		statuses[status.Name] = status
	}
	ops := []patchOperation{
		{Op: "test", Path: "/metadata/uid", Value: string(pod.UID)},
		{Op: "test", Path: "/metadata/resourceVersion", Value: pod.ResourceVersion},
	}
	matched := 0
	for i, container := range pod.Spec.Containers {
		values, selected := desired[container.Name]
		if !selected {
			continue
		}
		matched++
		if len(values.Requests) != 1 || len(values.Limits) != 1 ||
			values.Requests["cpu"] == "" || values.Limits["cpu"] == "" {
			return nil, errors.New("only explicit CPU request and limit are supported")
		}
		request, errRequest := resource.ParseQuantity(values.Requests["cpu"])
		limit, errLimit := resource.ParseQuantity(values.Limits["cpu"])
		current := container.Resources.Requests[corev1.ResourceCPU]
		if errRequest != nil || errLimit != nil || request.Sign() <= 0 ||
			request.Cmp(limit) != 0 || request.Cmp(cfg.minCPU) < 0 || request.Cmp(current) > 0 {
			return nil, errors.New("CPU target must be equal, positive, above the floor and no larger than current")
		}
		for _, policy := range container.ResizePolicy {
			if policy.ResourceName == corev1.ResourceCPU && policy.RestartPolicy == corev1.RestartContainer {
				return nil, errors.New("CPU restart policy is incompatible with this prototype")
			}
		}
		status, exists := statuses[container.Name]
		if !exists || status.State.Running == nil || status.Resources == nil {
			return nil, nil
		}
		observedRequest, rqOK := status.Resources.Requests[corev1.ResourceCPU]
		observedLimit, lmOK := status.Resources.Limits[corev1.ResourceCPU]
		if !rqOK || !lmOK || observedRequest.Cmp(current) != 0 || observedLimit.Cmp(current) != 0 {
			return nil, nil
		}
		switch trigger {
		case "StartupProbePassed":
			if container.StartupProbe == nil {
				return nil, errors.New("StartupProbePassed requires a real startupProbe on every target")
			}
			if status.Started == nil || !*status.Started {
				return nil, nil
			}
		case "Ready":
			if !podReady {
				return nil, nil
			}
		case "Delay":
			if status.State.Running.StartedAt.IsZero() ||
				now.Sub(status.State.Running.StartedAt.Time) < time.Duration(delay)*time.Second {
				return nil, nil
			}
		}
		if request.Cmp(current) == 0 {
			continue
		}
		base := fmt.Sprintf("/spec/containers/%d", i)
		ops = append(ops,
			patchOperation{Op: "test", Path: base + "/name", Value: container.Name},
			patchOperation{Op: "replace", Path: base + "/resources/requests/cpu", Value: request.String()},
			patchOperation{Op: "replace", Path: base + "/resources/limits/cpu", Value: request.String()})
	}
	if matched != len(desired) {
		return nil, errors.New("steady-resources contains an unknown regular container")
	}
	if len(ops) == 2 {
		return nil, nil
	}
	return json.Marshal(ops)
}
```

成功的 PATCH 会记录为 `RESIZE_REQUESTED`，而不会标记为已完成。UID/resourceVersion 测试可拒绝过期名称或已更改对象。工作队列限制重试次数、处理取消并避免旧版不断增长的已处理 UID 映射表。该原型不会在现有 Pod 内的容器重启后恢复启动阶段 CPU，不会协调其他 HPA/VPA/GitOps 写入者，也不包含部署打包/就绪/高可用策略，更不能证明应用 SLO。不同工作负载控制器都可以创建符合条件的 Pod，但仍需集成测试其滚动更新/替换/存储行为。

ServiceAccount 对 Pod 具有命名空间范围的读取权限，只能写入 resize 子资源；它没有通用 Pod patch 或 Secret 读取权限。请准备好现有命名空间/标签，构建并审核控制器镜像，以此 ServiceAccount 身份运行，并设置两个必需环境变量。示例下限 `50m` 仅供说明，并非通用生产建议。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: version-lab
  labels:
    map-demo: 'true'
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: pod-resizer
  namespace: version-lab
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: pod-resizer
  namespace: version-lab
rules:
- apiGroups:
  - ''
  resources:
  - pods
  verbs:
  - get
  - list
  - watch
- apiGroups:
  - ''
  resources:
  - pods/resize
  verbs:
  - patch
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: pod-resizer
  namespace: version-lab
subjects:
- kind: ServiceAccount
  name: pod-resizer
  namespace: version-lab
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: pod-resizer
```

以下工作负载符合控制器契约。它用 sleep 模拟预热，而非实际 CPU 工作，并保留历史示例的 200m→50m/64Mi 输入。使用前请审核/固定镜像。启动进程会创建就绪文件，探针只检查该文件。这修正了原来的探针：它在默认超时只有一秒时睡眠八秒，并依赖主进程从未创建的文件。

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: phase-aware-demo
  namespace: version-lab
spec:
  replicas: 2
  selector:
    matchLabels:
      app: phase-aware-demo
  template:
    metadata:
      labels:
        app: phase-aware-demo
        resize.example.com/managed: 'true'
      annotations:
        resize.example.com/enabled: 'true'
        resize.example.com/trigger: StartupProbePassed
        resize.example.com/steady-resources: '{"app":{"requests":{"cpu":"50m"},"limits":{"cpu":"50m"}}}'
    spec:
      os:
        name: linux
      nodeSelector:
        kubernetes.io/os: linux
      automountServiceAccountToken: false
      containers:
      - name: app
        image: busybox:1.36
        command:
        - sh
        - -ec
        - 'echo ''starting illustrative warmup''

          sleep 10

          touch "$READY_FILE"

          echo ''readiness file created''

          exec sleep 86400'
        env:
        - name: READY_FILE
          value: /tmp/ready
        resizePolicy:
        - resourceName: cpu
          restartPolicy: NotRequired
        - resourceName: memory
          restartPolicy: RestartContainer
        resources:
          requests:
            cpu: 200m
            memory: 64Mi
          limits:
            cpu: 200m
            memory: 64Mi
        startupProbe:
          exec:
            command:
            - sh
            - -ec
            - test -f "$READY_FILE"
          initialDelaySeconds: 1
          periodSeconds: 2
          timeoutSeconds: 1
          failureThreshold: 30
```

```bash
# Read-only observation for the owned example.
set -euo pipefail
: "${KUBE_CONTEXT:?}"
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n version-lab \
  get pods -l app=phase-aware-demo -o json | jq '.items[] | {
    name:.metadata.name,uid:.metadata.uid,generation:.metadata.generation,
    observedGeneration:.status.observedGeneration,qosClass:.status.qosClass,
    desired:[.spec.containers[] | {name,resources}],
    reported:[.status.containerStatuses[]? | {name,started,ready,resources,restartCount,containerID}],
    conditions:.status.conditions
  }'
```

本地审核对模拟 Kubernetes/RFC6902 行为的假 Kubernetes 执行了 50 个叶级单元测试，另做了 Schema 和主机 shell 探针测试。它没有在 EKS 上运行 informer 循环、启动 BusyBox、测量预热时间或验证 cgroup/应用性能。VPA 1.7 还提供 Alpha 的 CPUStartupBoost 功能，但其触发条件是 Pod Ready 加可选时长，而不是此处的 StartupProbePassed 契约；它有单独的标志和运维权衡。

#### 原始报告的 EKS 快照：来源未核实

此前章节声称使用 EKS 1.36.1、containerd 2.2.3、AL2023、cgroup v2 和 arm64/Graviton。未提供原始执行产物/来源。以下原始表格和日志行保留为**未经核实的报告结果**，不是重新执行的结果、当前控制器输出，也不是零停机的独立证明。两个 MAP 表格重复了原始说法，并非两次独立测量。

| 案例 | 注解 | 注入的 resizePolicy | 结果 |
|------|-----------|------------------------|--------|
| with-annotation | 存在 | `[{cpu:NotRequired},{memory:RestartContainer}]` | ✅ 已注入（无需 Webhook） |
| without-annotation | 不存在 | `[]`（无） | ✅ 未注入（matchCondition 生效） |

```text
2026/06/28 09:12:03 pod-resizer starting; watching pods annotated resize.example.com/enabled=true
2026/06/28 09:12:03 informer cache synced; ready
2026/06/28 09:12:41 RESIZED resize-demo/busybox-resize-demo-7f8b9c6d4-k2xnm [ReplicaSet] trigger=StartupProbePassed patch={"spec":{"containers":[{"name":"busybox","resources":{"limits":{"cpu":"50m"},"requests":{"cpu":"50m"}}}]}}
2026/06/28 09:12:41 RESIZED resize-demo/busybox-resize-demo-7f8b9c6d4-p9wvj [ReplicaSet] trigger=StartupProbePassed patch={"spec":{"containers":[{"name":"busybox","resources":{"limits":{"cpu":"50m"},"requests":{"cpu":"50m"}}}]}}
2026/06/28 09:13:05 RESIZED resize-demo/busybox-resize-ds-xq7zt [DaemonSet] trigger=StartupProbePassed patch={"spec":{"containers":[{"name":"busybox","resources":{"limits":{"cpu":"50m"},"requests":{"cpu":"50m"}}}]}}
2026/06/28 09:13:22 RESIZED resize-demo/busybox-resize-sts-0 [StatefulSet] trigger=StartupProbePassed patch={"spec":{"containers":[{"name":"busybox","resources":{"limits":{"cpu":"50m"},"requests":{"cpu":"50m"}}}]}}
```

| 工作负载 | QoS | CPU（请求/限制） | restartCount | containerID |
|----------|-----|---------------|--------------|-------------|
| Deployment（x2） | Guaranteed -> **Guaranteed** | 200m -> **50m** | 0 -> **0** | **相同** |
| DaemonSet | Guaranteed -> **Guaranteed** | 200m -> **50m** | 0 -> **0** | **相同** |
| StatefulSet | Guaranteed -> **Guaranteed** | 200m -> **50m** | 0 -> **0** | **相同** |

| 案例 | 是否存在注解 | 注入的 resizePolicy | 结论 |
|------|-------------------|----------------------|---------|
| with-annotation | 是 | `[{cpu:NotRequired},{memory:RestartContainer}]` | 已注入（无需 Webhook） |
| without-annotation | 否 | `[]`（无） | 未注入（matchCondition 生效） |

旧的 `RESIZED` 日志是在 API PATCH 成功后发出的。containerID/restartCount 不变以及期望 spec 的变更，单独来看不能证明 cgroup 已生效、应用延迟如何或是否存在请求丢失。验证需要匹配 Pod UID/时间窗口、kubelet 报告的实际资源/generation，以及适当的运行时/应用观测。没有把任何历史数值升级为新 Kubernetes 版本的结果，也没有将其作为新测量结果呈现。

[Kubernetes 1.36 发布公告](https://kubernetes.io/blog/2026/04/22/kubernetes-v1-36-release/) · [1.36.2 功能定义](https://github.com/kubernetes/kubernetes/blob/v1.36.2/pkg/features/kube_features.go) · [Kubelet 授权](https://kubernetes.io/docs/reference/access-authn-authz/kubelet-authn-authz/) · [ServiceAccount 管理](https://kubernetes.io/docs/reference/access-authn-authz/service-accounts-admin/) · [SELinux 安全上下文](https://kubernetes.io/docs/tasks/configure-pod-container/security-context/) · [已发布的 IPVS 选择路径](https://github.com/kubernetes/kubernetes/blob/v1.36.2/cmd/kube-proxy/app/server_linux.go) · [VPA 1.7.1 功能](https://github.com/kubernetes/autoscaler/blob/vertical-pod-autoscaler-1.7.1/vertical-pod-autoscaler/docs/features.md)

---

<span id="5-key-feature-graduation-timeline"></span>

## 5. 重要功能晋级时间表

此表汇总了**截至 Kubernetes 1.36** 的部分上游历史，主要依据已发布的 1.36.2 门控定义和官方已移除门控历史。“Beta”指首次进入 Beta 的版本，并不一定代表默认启用。短横线不承诺未来里程碑。API 可用性、运行时/驱动程序前置条件和 EKS 支持仍需单独核实。

| 功能 | 首次 Alpha | 首次 Beta | 截至 1.36 已稳定 |
|---|---|---|---|
| Sidecar containers | 1.28 | 1.29 | 1.33 |
| 容器原地调整 | 1.27 | 1.33 | 1.35 |
| Pod 调度就绪 | 1.26 | 1.27 | 1.30 |
| Job 成功策略 | 1.30 | 1.31 | 1.33 |
| Pod 级资源 | 1.32 | 1.34 | - |
| ValidatingAdmissionPolicy | 1.26 | 1.28 | 1.30 |
| MutatingAdmissionPolicy | 1.32 | 1.34 | 1.36 |
| 结构化授权 | 1.29 | 1.30 | 1.32 |
| AppArmor 原生字段 | - | 1.30 | 1.31 |
| User namespaces | 1.25 | 1.30 | 1.36 |
| ServiceCIDR/IPAddress | 1.27 | 1.31 | 1.33 |
| 拓扑感知提示 | 1.21 | 1.23 | 1.33 |
| nftables 代理 | 1.29 | 1.31 | 1.33 |
| Service 流量分布 | 1.30 | 1.31 | 1.33 |
| 同节点/区域偏好 | 1.33 | 1.34 | 1.35 |
| ReadWriteOncePod | 1.22 | 1.27 | 1.29 |
| VolumeAttributesClass | 1.29 | 1.31 | 1.34 |
| PV 最后阶段转换时间 | 1.28 | 1.29 | 1.31 |
| 卷扩容恢复 | 1.23 | 1.32 | 1.34 |
| Gang scheduling | 1.35 | - | - |
| 最小拓扑域数 | 1.24 | 1.25 | 1.30 |
| DRA 核心功能 | 1.26 | 1.32 | 1.34 |
| HPA 容器指标 | 1.20 | 1.27 | 1.30 |
| 镜像卷 | 1.31 | 1.33 | 1.36 |
| 节点日志查询 | 1.27 | 1.30 | 1.36 |
| KMS v2 | 1.25 | 1.27 | 1.29 |
| Kubelet tracing | 1.25 | 1.27 | 1.34 |
| KYAML | 1.34 | 1.35 | - |

重要的沿革细节：

- AppArmor 注解从 1.4 起以 Beta 形式存在；此行追踪的是较新的原生字段（1.30 Beta、1.31 GA）。
- User namespace 相关工作从早期有限/无状态支持开始；已发布的门控历史记录了 1.25 Alpha、1.30 Beta、1.33 默认启用和 1.36 GA。不要根据 GA 日期推断门控已移除。
- DRA 的 1.26 Alpha 属于原始设计。后来的结构化参数重设计（KEP-4381）并非沿用不变的 API；Classic DRA 在 1.31 仍受门控控制，并于 1.32 移除。当前稳定请求语法使用 `exactly`。
- 原生 gang scheduling 对应 KEP-4671，截至 1.36 仍为 Alpha。KYAML 对应 KEP-5295，并在 1.37 才于上游稳定，超出此表的覆盖范围；二者在 1.36 都没有达到 GA。
- Beta 功能的默认值彼此独立变化：UserNamespacesSupport 在 1.33 默认启用，ImageVolume 在 1.35 默认启用，PodLevelResources 则首次在 1.34 进入 Beta。

Gateway API 是单独发布的 API/CRD 项目。不要将它的发布渠道、kind 版本或功能一致性归入 Kubernetes 的“1.18 Alpha / 1.26 GA”。同样，VPA 更新模式、Karpenter 和 CSI 驱动程序也各自有独立的发布/支持矩阵。核心 API 晋级不能认证这些组件，也不会让所有示例自动达到生产就绪状态。

<!-- Parent repair: graduation diagram has stale DRA/Gang and other milestone assertions.
![Six major Kubernetes features, from ValidatingAdmissionPolicy to Gang Scheduling, laid out in GA graduation order with the release in which each reached Alpha, Beta, and GA between 1.30 and 1.36.](../.gitbook/assets/en-eks-12-kubernetes-version-roadmap-14.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-12-kubernetes-version-roadmap-14.html)
-->

[已发布的 Kubernetes 1.36.2 功能历史](https://github.com/kubernetes/kubernetes/blob/v1.36.2/pkg/features/kube_features.go) · [功能门控](https://kubernetes.io/docs/reference/command-line-tools-reference/feature-gates/) · [已移除的门控](https://kubernetes.io/docs/reference/command-line-tools-reference/feature-gates-removed/) · [KYAML 历史](https://github.com/kubernetes/enhancements/tree/master/keps/sig-cli/5295-kyaml)

---

<span id="6-deprecations-and-removals"></span>

## 6. 弃用与移除

### 区分 API 版本、字段、实现和门控

在同一个 Kubernetes 主版本中，不能移除 GA **API 版本**。这与 CLI 标志、功能门控、单个字段或卷实现不同。Beta API 退役有自己的最短期限：弃用后九个月或三个次要版本，以较长者为准。Alpha API 可能更改或消失，不享有此保证。此前“GA API 可在 12 个月/3 个版本后移除”的规则不正确。

门控弃用/移除遵循单独规则，必须核实实际版本。不要仅通过在 GA 版本号上加二来移除/禁用门控。前文各版本章节和已发布代码区分了默认启用、锁定状态和实际移除。

### 选定的 API 退役节点

| API 和 kind | 自哪个版本起不再提供 | 当前替代项 / 迁移注意事项 |
|---|---|---|
| `autoscaling/v2beta1` HPA | 1.25 | `autoscaling/v2`；检查指标 Schema |
| `autoscaling/v2beta2` HPA | 1.26 | `autoscaling/v2` |
| `batch/v1beta1` CronJob | 1.25 | `batch/v1` |
| `policy/v1beta1` PDB | 1.25 | `policy/v1`；空选择器的语义不同 |
| `flowcontrol.apiserver.k8s.io/v1beta2` FlowSchema/PriorityLevelConfiguration | 1.29 | `v1`；检查并发份额字段/默认值变更 |
| `flowcontrol.apiserver.k8s.io/v1beta3` FlowSchema/PriorityLevelConfiguration | 1.32 | `v1` |
| `admissionregistration.k8s.io/v1beta1` ValidatingAdmissionPolicy/Binding | 1.34 | `v1`；不要与同一 group/version 中的 MutatingAdmissionPolicy 混淆 |
| `resource.k8s.io/v1alpha3` ResourceClaim/Template、DeviceClass、ResourceSlice | 1.34 | 当前使用稳定的 `v1`；旧的已存储表示需要依照具体版本制定迁移计划 |
| `storage.k8s.io/v1beta1` CSIDriver、CSINode、StorageClass、VolumeAttachment | 1.22 | `storage.k8s.io/v1` |
| `storage.k8s.io/v1beta1` CSIStorageCapacity | 1.27 | `storage.k8s.io/v1` |
| Beta Ingress / CRD / admission-webhook 配置 API | 1.22 | 稳定版 `v1`；转换涉及 Schema/字段变更 |

该 resource group 仍包含其他 `v1alpha3` kind，因此不要仅因四种核心 DRA kind 退役，就宣称整个 group/version 已移除。1.34 变更日志还对旧的已存储 DRA 表示提出警告。请协调备份、工作负载/claim 所有权和指定迁移/重建路径；不要盲目删除所有 claim，也不要只修改 `apiVersion` 字符串。

### 1.36 实现中仍有记录的 Beta API

已发布的 1.36.2 生命周期元数据和 REST storage 仍区分这些版本。未来的移除值是记录的目标，并不保证未来版本一定不变，也不表示托管服务默认会启用所有 API。

| API 和 kind | 元数据中标记为弃用的版本 | 记录的移除目标 |
|---|---|---|
| DRA 核心 `resource.k8s.io/v1beta1` | 1.35 | 1.38 |
| DRA 核心 `resource.k8s.io/v1beta2` | 1.36 | 1.39 |
| VAC `storage.k8s.io/v1beta1` | 1.34 | 1.37 |
| MutatingAdmissionPolicy/Binding `admissionregistration.k8s.io/v1beta1` | 1.37 | 1.40 |

晋级到 GA 并不意味着 Beta API 会立即移除。反过来，如果后续已发布变更日志更改了实现，那么旧 Alpha 移除预测也不具有权威性。

其他重要更正：KMS v1 已弃用/默认禁用，但没有在 1.31 移除；`--authorization-mode` 仍是结构化授权配置的替代方案；iptables 代理模式没有在 1.34 移除；IPVS 已弃用，但在上游 1.36.2 中仍有实现。旧版 ServiceAccount Secret 自动生成在 1.24 改变，而非 1.33。不要把旧的 `kubectl --export` 移除说成 1.35 的新变更。对于树内存储插件，应核实具体插件和版本、CSI 迁移状态、卷标识符及驱动就绪情况，不要套用通用时间表。

### 分别审核已存储清单与实际客户端使用情况

GET 响应使用所请求/首选的 API 表示，可能会隐藏客户端最初使用的 API 版本。`kubectl get flowschemas -o json`、API discovery 或 CRD conversion webhook 列表，都不能证明正在使用已弃用 API。并非所有 `v1beta1` API 都已弃用。应综合检查渲染后的 Git/Helm 清单、可用时原始应用配置、API 使用指标/审计日志、EKS Insights 和目标版本测试。应单独检查 CRD 提供/存储版本和转换行为。

该指标可以显示服务 API 进程观察到的已弃用请求；它不是完整的历史请求计数，也不能保证覆盖每个 API server 副本。指标缺失/访问错误不代表检查结果正常。

```bash
# Read-only, explicitly selected cluster; metrics access may be restricted.
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${EVIDENCE_PARENT:?Existing private directory}"
umask 077
evidence_dir=$(mktemp -d "$EVIDENCE_PARENT/api-usage.XXXXXXXX")
kubectl --context "$KUBE_CONTEXT" --request-timeout=20s get --raw='/metrics' > "$evidence_dir/metrics.prom"
awk '/^apiserver_requested_deprecated_apis/ {print}' "$evidence_dir/metrics.prom"
```

### 有限的离线生命周期检查器

以下示例需要 Python/PyYAML 和一个存放已渲染 YAML/JSON 清单的自有目录。它使用固定到 1.36.2 审核结果的有限目录，并接受 1.29–1.36 的目标版本。它区分同一 API 版本中的不同 kind，拒绝解析错误/空目录，且绝不打印资源正文。它**不是完整的 Schema、客户端使用情况或运行时兼容性审核工具**。它不会发现所有已弃用 API、语义变更或所有 YAML/Schema 问题；还应使用包含实际 CRD 的版本化 Schema 验证器。`notInCatalog` 必须经过审核。

退出码 1 表示发现生命周期问题，退出码 2 表示输入/解析问题，退出码 0 仅表示在已解析输入中没有发现目录已知问题。不要忽略这些失败，也不要把部分扫描称为“兼容”。

```python
"""Limited offline GVK lifecycle audit, snapshot: Kubernetes 1.36.2.
Requires PyYAML. This is not a schema, runtime or complete client-usage audit.
"""
import argparse
import json
import re
from pathlib import Path

import yaml


CATALOG = {}


def add(api, kinds, deprecated, removed, replacement):
    for kind in kinds.split(","):
        CATALOG[(api, kind)] = (deprecated, removed, replacement)


add("autoscaling/v2beta1", "HorizontalPodAutoscaler", 22, 25, "autoscaling/v2")
add("autoscaling/v2beta2", "HorizontalPodAutoscaler", 23, 26, "autoscaling/v2")
add("batch/v1beta1", "CronJob", 21, 25, "batch/v1")
add("policy/v1beta1", "PodDisruptionBudget", 21, 25, "policy/v1")
add("networking.k8s.io/v1beta1", "Ingress", 19, 22, "networking.k8s.io/v1")
add("extensions/v1beta1", "Ingress", 14, 22, "networking.k8s.io/v1")
add("apiextensions.k8s.io/v1beta1", "CustomResourceDefinition", 16, 22, "apiextensions.k8s.io/v1")
add("admissionregistration.k8s.io/v1beta1", "MutatingWebhookConfiguration,ValidatingWebhookConfiguration", 16, 22, "admissionregistration.k8s.io/v1")
add("admissionregistration.k8s.io/v1beta1", "ValidatingAdmissionPolicy,ValidatingAdmissionPolicyBinding", 31, 34, "admissionregistration.k8s.io/v1")
add("admissionregistration.k8s.io/v1beta1", "MutatingAdmissionPolicy,MutatingAdmissionPolicyBinding", 37, 40, "admissionregistration.k8s.io/v1")
add("flowcontrol.apiserver.k8s.io/v1beta1", "FlowSchema,PriorityLevelConfiguration", 23, 26, "flowcontrol.apiserver.k8s.io/v1")
add("flowcontrol.apiserver.k8s.io/v1beta2", "FlowSchema,PriorityLevelConfiguration", 26, 29, "flowcontrol.apiserver.k8s.io/v1")
add("flowcontrol.apiserver.k8s.io/v1beta3", "FlowSchema,PriorityLevelConfiguration", 29, 32, "flowcontrol.apiserver.k8s.io/v1")
add("storage.k8s.io/v1beta1", "CSIDriver", 19, 22, "storage.k8s.io/v1")
add("storage.k8s.io/v1beta1", "CSINode", 17, 22, "storage.k8s.io/v1")
add("storage.k8s.io/v1beta1", "StorageClass", 19, 22, "storage.k8s.io/v1")
add("storage.k8s.io/v1beta1", "VolumeAttachment", 19, 22, "storage.k8s.io/v1")
add("storage.k8s.io/v1beta1", "CSIStorageCapacity", 24, 27, "storage.k8s.io/v1")
add("storage.k8s.io/v1beta1", "VolumeAttributesClass", 34, 37, "storage.k8s.io/v1")
# Alpha core DRA kinds were actually removed in 1.34, overriding older plans.
add("resource.k8s.io/v1alpha3", "ResourceClaim,ResourceClaimTemplate,DeviceClass,ResourceSlice", 34, 34, "resource.k8s.io/v1")
add("resource.k8s.io/v1beta1", "ResourceClaim,ResourceClaimTemplate,DeviceClass,ResourceSlice", 35, 38, "resource.k8s.io/v1")
add("resource.k8s.io/v1beta2", "ResourceClaim,ResourceClaimTemplate,DeviceClass,ResourceSlice", 36, 39, "resource.k8s.io/v1")


def resources(obj, seen=None):
    seen = set() if seen is None else seen
    if obj is None:
        return
    if not isinstance(obj, dict):
        raise ValueError("expected a resource mapping")
    if id(obj) in seen:
        raise ValueError("recursive resource List")
    if len(seen) >= 32:
        raise ValueError("resource List nesting exceeds32")
    seen.add(id(obj))
    try:
        if obj.get("kind") == "List":
            for item in obj.get("items", []):
                yield from resources(item, seen)
        else:
            yield obj
    finally:
        seen.remove(id(obj))


def audit(directory, target_minor):
    findings, errors, skipped = [], [], 0
    files = sorted(p for p in directory.rglob("*") if p.is_file() and p.suffix.lower() in {".yaml", ".yml", ".json"})
    if len(files) > 5000:
        raise ValueError("limit exceeded: 5000 rendered files")
    if not files:
        errors.append({"path": str(directory), "errorType": "NoManifestFiles", "line": None})
    for path in files:
        try:
            if path.is_symlink() or path.stat().st_size > 16 * 1024 * 1024:
                raise ValueError("symlink or file exceeds16MiB")
            for document in yaml.safe_load_all(path.read_text(encoding="utf-8")):
                for obj in resources(document):
                    key = (obj.get("apiVersion"), obj.get("kind"))
                    entry = CATALOG.get(key)
                    if entry is None:
                        skipped += 1
                        continue
                    deprecated, removed, replacement = entry
                    if target_minor < deprecated:
                        continue
                    metadata = obj.get("metadata") or {}
                    if not isinstance(metadata, dict) or any(
                        metadata.get(k) is not None and not isinstance(metadata[k], str)
                        for k in ("name", "namespace")
                    ):
                        raise ValueError("invalid metadata identity fields")
                    findings.append({
                        "path": str(path), "apiVersion": key[0], "kind": key[1],
                        "namespace": metadata.get("namespace"), "name": metadata.get("name"),
                        "state": "removed" if target_minor >= removed else "deprecated",
                        "replacement": replacement,
                    })
        except (OSError, UnicodeError, ValueError, TypeError, yaml.YAMLError) as exc:
            # Do not print parser snippets or resource/Secret bodies.
            mark = getattr(exc, "problem_mark", None)
            errors.append({"path": str(path), "errorType": type(exc).__name__,
                           "line": mark.line + 1 if mark is not None else None})
    return {"snapshot": "Kubernetes1.36.2", "files": len(files), "findings": findings,
            "errors": errors, "notInCatalog": skipped,
            "limit": "Selected GVK lifecycle checks only; no matches do not certify compatibility."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--target-version", required=True)
    args = parser.parse_args()
    match = re.fullmatch(r"1\.(\d+)(?:\.\d+)?", args.target_version)
    if not match or not 29 <= int(match[1]) <= 36 or not args.directory.is_dir():
        parser.error("provide a rendered directory and a reviewed target from1.29 through1.36")
    try:
        result = audit(args.directory, int(match[1]))
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2))
    raise SystemExit(2 if result["errors"] else 1 if result["findings"] else 0)
```

```bash
# Save the Python example as api-version-audit.py; requires PyYAML.
: "${MANIFEST_DIR:?Directory containing owned rendered manifests}"
python3 api-version-audit.py --directory "$MANIFEST_DIR" --target-version 1.36.0
```

### Pluto、kubent 与 Helm 的边界

Pluto 可作为额外检测器，但工具/规则的新旧程度并不能证明结果正确。此审核使用原生 **Pluto 5.24.3** 测试用例时，未能发现已移除的 VAP Beta API；对格式错误的 YAML 返回退出码 0；尽管上文已发布的 1.36.2 生命周期/storage 证据表明 DRA beta1 尚未移除，却将其标记为 1.36 已移除。请将结果视为需要与一手资料核对的线索。其默认退出码 2/3/4 分别表示弃用/移除/无可用替代项发现；其他失败也需要调查。使用 `--components k8s` 可避免悄悄采用其他组件的捆绑版本默认值。

```bash
# Advisory only: record the reviewed Pluto version and its rule coverage.
: "${MANIFEST_DIR:?Directory containing owned rendered manifests}"
pluto detect-files --directory "$MANIFEST_DIR" \
  --target-versions k8s=v1.36.0 --components k8s --output json
```

```bash
# Read-only cluster/Helm inspection can require access to release Secrets.
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?Owned namespace}"
pluto detect-all-in-cluster --kube-context "$KUBE_CONTEXT" --namespace "$NAMESPACE" \
  --target-versions k8s=v1.36.0 --components k8s --output json
```

```bash
# Inspect names with their namespaces; a Helm release name is not globally unique.
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${RELEASE_NAME:?}"
helm list --kube-context "$KUBE_CONTEXT" --namespace "$NAMESPACE" --output json
# If exporting manifests, use a private file: they can contain Secret values.
: "${PRIVATE_MANIFEST_FILE:?Choose a private destination}"
umask 077
helm get manifest --kube-context "$KUBE_CONTEXT" --namespace "$NAMESPACE" \
  "$RELEASE_NAME" > "$PRIVATE_MANIFEST_FILE"
```

kubent 是另一种针对原始清单的检测器，并不是 API server 的权威来源。此处观察到的最新标签版本为 0.7.3（2024年8月）；请核实其对较新目标 API 的规则覆盖情况。其文档中的 `--context`、`--target-version` 和 `--exit-error` 标志值得关注；收集 Helm 信息需要 release Secret/ConfigMap 权限。`kubectl convert` 用于转换受支持的对象表示，不是已弃用客户端 API 使用情况扫描器。配置了 CRD conversion webhook 并不意味着它本身已弃用。

[Kubernetes 弃用策略](https://kubernetes.io/docs/reference/deprecation-policy/) · [API 迁移指南](https://kubernetes.io/docs/reference/using-api/deprecation-guide/) · [1.34 变更日志](https://github.com/kubernetes/kubernetes/blob/v1.34.0/CHANGELOG/CHANGELOG-1.34.md) · [1.36.2 DRA REST storage](https://github.com/kubernetes/kubernetes/blob/v1.36.2/pkg/registry/resource/rest/storage_resource.go) · [Pluto](https://github.com/FairwindsOps/pluto) · [Kubent](https://github.com/doitintl/kube-no-trouble)

---

<span id="7-eks-specific-considerations"></span>

## 7. EKS 专项注意事项

### 发布与功能可用性

EKS 有自己的资格认证和支持日历。第 3 节中的日期是已核实的发布记录，并不保证每个未来版本都在固定延迟后发布。上游 API 成熟度、EKS API 可用性和节点/运行时能力是不同的问题。AWS 管理 EKS 控制平面标志；编辑 kube-apiserver Pod、应用 kubeadm 配置或更改单个节点门控，都不是 EKS 控制平面的配置方式。

EKS 常见问题支持普遍可用的 Kubernetes API，说明新的 Beta API 默认不启用，并且不支持 Alpha 功能。已有 Beta API/现有 Beta API 的新版本则按不同方式处理。请查看具体 EKS 版本说明和计算实现，不要假设每个 Beta 字段都可用，或认为所有 GA 功能都能在不配置驱动程序或兼容节点的情况下使用。

![双轨时间线将 1.33 至 1.36 上游 Kubernetes 发布月份与 Amazon EKS 可用日期并列，显示两者之间大致稳定的两个月延迟，并突出显示作为最新 EKS 版本的 1.36。](../.gitbook/assets/en-eks-12-kubernetes-version-roadmap-20.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-12-kubernetes-version-roadmap-20.html)

### 查询兼容性记录，而不是猜测最低版本表

此前的 `v1.x+` add-on 矩阵不能证明 EKS 构建、平台、架构或计算兼容性，而且混用了 collector/chart/add-on 版本体系。首先记录自有账号、Region、集群版本和已安装组件。IRSA 角色字段为 null，并不能证明 add-on 没有 AWS 访问权限；它可能使用 Pod Identity 或供应商管理的身份。Auto Mode 内置组件可能不会显示为常规已安装 add-on。

```bash
# Read-only inventory in the explicitly selected account/Region/cluster.
set -euo pipefail
: "${AWS_REGION:?}"; : "${CLUSTER_NAME:?}"; : "${EXPECTED_ACCOUNT_ID:?}"
actual_account=$(aws sts get-caller-identity --region "$AWS_REGION" --query Account --output text)
test "$actual_account" = "$EXPECTED_ACCOUNT_ID" || { printf '%s\n' 'Account mismatch' >&2; exit 1; }
aws eks describe-cluster --region "$AWS_REGION" --name "$CLUSTER_NAME" --no-cli-pager \
  --query 'cluster.{version:version,platform:platformVersion,compute:computeConfig,upgradePolicy:upgradePolicy}' --output json
aws eks list-addons --region "$AWS_REGION" --cluster-name "$CLUSTER_NAME" --no-cli-pager --output json
```

```bash
# Inspect one addon, not a guessed first element or a bare component version.
: "${AWS_REGION:?}"; : "${CLUSTER_NAME:?}"; : "${ADDON_NAME:?}"
aws eks describe-addon --region "$AWS_REGION" --cluster-name "$CLUSTER_NAME" \
  --addon-name "$ADDON_NAME" --no-cli-pager \
  --query 'addon.{name:addonName,version:addonVersion,status:status,issues:health.issues,role:serviceAccountRoleArn,podIdentityAssociations:podIdentityAssociations}' --output json
```

以下候选项查询会在每条兼容性记录中匹配**请求的 Kubernetes 版本**。它会保留架构、计算类型、平台版本、默认选择以及配置/IAM 要求。数组第一项和字典序最大的版本都不代表“最新兼容版本”。AWS 默认标志针对具体兼容性记录，并非全局排名。

```bash
# Read-only candidates; no addon is installed or changed.
set -euo pipefail
: "${AWS_REGION:?}"; : "${TARGET_K8S_VERSION:?For example1.36}"; : "${ADDON_NAME:?}"
aws eks describe-addon-versions --region "$AWS_REGION" --no-cli-pager \
  --kubernetes-version "$TARGET_K8S_VERSION" --addon-name "$ADDON_NAME" --output json |
  jq -e --arg target "$TARGET_K8S_VERSION" --arg name "$ADDON_NAME" '
    [.addons[]? | select(.addonName == $name) | . as $addon |
      .addonVersions[]? as $release | $release.compatibilities[]? |
      select(.clusterVersion == $target) |
      {addon:$addon.addonName,version:$release.addonVersion,
       architecture:$release.architecture,computeTypes:$release.computeTypes,
       requiresConfiguration:$release.requiresConfiguration,requiresIamPermissions:$release.requiresIamPermissions,
       platformVersions:.platformVersions,defaultForThisCompatibility:.defaultVersion}] |
    if length == 0 then error("No matching compatibility record; do not infer support")
    else . end'
```

这些只是候选项，不是部署决策。请检查目标平台、节点架构/计算组合、发布说明、必需配置和 AWS 权限。结果为空或 CLI 失败时必须停止选择。读取确切的 add-on 配置 Schema，并在单独审核更新前保留有意设置的现有值。不要盲目使用 OVERWRITE、降级到任意旧版本，也不要假设控制平面更新会升级所有 add-on。本次审核使用假响应/当前 CLI 模型测试了这些命令，并未查询实时 AWS 目录。

### Auto Mode 与混合集群

Auto Mode 管理其内置计算/网络/存储组件；这并不意味着永远遵守 `n−1` 节点版本约束，也不意味着所有第三方 add-on 都会自动维护。工作负载限制和中断控制可能延迟节点替换。请检查实际更新状态和节点版本，并审核自定义 NodePool 兼容性。Managed node groups、自行管理的/Hybrid 节点以及 Fargate Pods 都有各自的更新/替换流程。

当前 Auto Mode 节点将 CoreDNS 作为**节点系统服务**运行。当所有适用工作负载都迁移到 Auto Mode 节点后，纯 Auto Mode 集群可以移除传统 CoreDNS Deployment。混合 Auto/非 Auto 集群必须保留 Deployment，以供非 Auto 节点使用。Auto Mode 下没有普通 CoreDNS/VPC CNI/kube-proxy Pods，并不自动表示故障；这些 Pod 存在也不代表预期模式运行正常。

```bash
# Read-only node inventory; the label is evidence, not an availability check.
set -euo pipefail
: "${KUBE_CONTEXT:?}"
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get nodes -o json | jq '[
  .items[] | {name:.metadata.name,kubelet:.status.nodeInfo.kubeletVersion,
             computeType:.metadata.labels["eks.amazonaws.com/compute-type"]}]'
```

包含新 `metadata.version` 的 eksctl ClusterConfig 本身并不构成升级执行。应使用经过审核的更新流程，并跟踪其返回的 update ID。PDB 不保证可用性；应了解哪些替换操作会遵守它，以及哪些扩容/删除路径不同。请将应用就绪、存储和回滚准备纳入计划。

### 扩展支持的成本背景

已核实的版本支持费用差为每集群小时 $0.50。按示例年份 365 天计算，1 个集群额外费用为 $4,380，5 个为 $21,900，10 个为 $43,800，25 个为 $109,500，50 个为 $219,000。这些数字不包括计算、预置控制平面层级、网络和其他费用。每月 730 小时是规划假设，并不代表每个日历月。

集群数量只是规划维度之一：一个关键集群的运维风险可能高于许多简单集群。接近标准支持结束时应提高规划优先级，但不能以此为由跳过预发布验证，或在几乎不检查的情况下直接升级生产环境。在适用时，应比较受控升级与明确接受扩展支持成本这两种选择。

![升级优先级矩阵按机群复杂度和扩展支持成本紧迫度为五种 EKS 机群配置定位：从“监控”象限中的单个简单集群，到“规划并安排”象限中具有最高成本风险的 50 个以上集群企业机群。](../.gitbook/assets/en-eks-12-kubernetes-version-roadmap-19.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-12-kubernetes-version-roadmap-19.html)

<!-- Parent repair: imminent-support-end path must not recommend direct production upgrade with minimal validation.
![Decision flow that branches on the time left in Standard Support into a planned upgrade, an immediate upgrade, or an Extended Support cost review, ending in either a production upgrade or staying on Extended Support.](../.gitbook/assets/en-eks-12-kubernetes-version-roadmap-16.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-12-kubernetes-version-roadmap-16.html)
-->

[EKS 支持策略](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html) · [DescribeAddonVersions](https://docs.aws.amazon.com/eks/latest/APIReference/API_DescribeAddonVersions.html) · [Auto Mode 网络和 DNS](https://docs.aws.amazon.com/eks/latest/userguide/auto-networking.html) · [EKS 定价](https://aws.amazon.com/eks/pricing/) · [经审核的 EKS 升级指南](08-eks-upgrades.md)

---

<span id="8-version-upgrade-planning"></span>

## 8. 版本升级规划

### 为每次跨一个次要版本的升级制定可执行计划

EKS 升级每次只能跨一个次要版本。请使用已核实的发布/支持日历、目标版本兼容性记录和当前 EKS 升级指南；不要根据上游最新标签推断升级资格。此前的准备一至两周、执行一至两天只是规划示例，并非实测时长或截止期限。

1. 记录自有账号/Region/集群、控制平面和节点版本、计算模式、add-on 构建版本、API 使用情况、Operator 和工作负载所有者。在进行下一次控制平面升级前，先将节点升级到安全的当前版本。受支持的版本偏差是兼容性边界，不是建议让节点落后三个次要版本，也不是对所有 API 强制执行路径的通用说明。
2. 审核目标版本变更、已弃用/移除 API 和已存储版本迁移要求、运行时/操作系统/AMI 支持、CRD 和准入策略。工具退出码为 0、转换后的 GET 响应或 GA 标签，都不是完整的兼容性测试。
3. 适当备份应用状态和 Kubernetes 配置，并测试恢复。EKS 管理其 etcd；客户无法检查托管 etcd 备份计划，也不能像拥有控制平面那样执行 etcd snapshot 命令。Git 不能替代数据库/PVC 备份。
4. 在有代表性的非生产环境中演练实际版本升级步骤和组件顺序。验证应用就绪、网络/DNS、存储、自动扩缩容、身份和可观测性。生产环境操作前先决定回滚/数据恢复标准。
5. 执行已批准的控制平面更新，并跟踪返回的 update ID，直至成功的最终状态。按文档规定的顺序升级节点和适用组件。一些兼容性/迁移工作必须在控制平面更新前完成；并不存在适用于所有版本和计算模式的通用“kube-proxy → CoreDNS → VPC CNI → CSI”顺序。
6. 每个阶段结束后验证客户可见行为、副本就绪状态、API/更新状态和组件健康情况。Pod 处于 Running 本身不能证明已就绪。请保留证据并更新操作手册。

截至本次审核，EKS 更新指南指出，针对某些**升级**洞察问题、必须使用 `--force` 的强制要求已暂时撤回。这与回滚就绪检查不同。Insights 仍是规划的重要依据；撤回强制要求并不表示可以忽略兼容性问题。

### 功能测试与计算资源管理责任

不要把过时的门控名称或不受支持的 `managedNodeGroups[].kubelet.featureGates` 格式复制到 eksctl。应使用节点操作系统/配置器所支持的引导机制，以及[集群创建指南](02-eks-cluster-creation.md)中的当前 Schema。EKS 控制平面标志仍由 AWS 管理。使用兼容客户端，并区分离线 Schema 检查、server-side dry-run 和实际运行时测试。

Auto Mode 管理节点替换，但工作负载就绪/中断限制可能造成延迟。混合集群仍需满足非 Auto DNS/add-on 要求。Managed node group 滚动更新与 desired/min/max 扩缩容是不同操作；PDB 并非扩缩容、直接删除或所有恢复路径的通用保护。Fargate 和 Hybrid Nodes 需要各自的生命周期流程。

### EKS 原生回滚与恢复选项

版本回滚是 EKS 的真实功能，但必须在**原地升级完成后的七天内**发起，且只能回到上一个次要版本，还必须满足版本/集群资格条件。以当前版本创建的集群、后续又进行的升级、资格期限已过或不兼容的 EKS 功能，都可能导致无法回滚。扩展支持结束时的自动升级不符合资格。选择扩展支持目标版本也会影响升级策略/计费。

操作员发起回滚后，Auto Mode 会先回滚节点，再回滚控制平面。Managed node groups 必须单独先通过 UpdateNodegroupVersion 回滚；自行管理的/Hybrid 节点需要各自准备。Fargate 工作节点不能原地回滚：官方流程要求在控制平面回滚前后协调计划性移除/重新部署。不要把绕过的 kubelet 版本偏差当作受支持配置，也不要盲目删除正在运行的 Fargate 工作负载。

`--force` 可以绕过 ERROR/WARNING/UNKNOWN 回滚洞察检查，但不能绕过资格/前置条件验证或 Auto Mode 中断控制。这不是安全的默认做法。请遵循详细的 [EKS 升级](08-eks-upgrades.md)流程，包括确切的更新状态跟踪以及 Auto Mode 阶段/超时/取消限制。控制平面回滚不等于应用/数据库回滚；EKS 会保留 etcd/客户数据，不会把所有应用恢复到早期状态。

| 层级 | 恢复规划 |
|---|---|
| 控制平面 | 符合条件时使用原生回滚；不可用时采用预先准备的并行集群恢复路径 |
| 节点 | 使用兼容版本并受控替换/驱逐；添加 taint 本身不会迁移已有 Pod 或流量 |
| 工作负载 | 审核 GitOps/Helm 版本回滚及应用/数据兼容性 |
| Add-ons | 使用确切兼容构建版本，审核配置/IAM 和受支持的降级行为；不要盲目使用 OVERWRITE |
| 持久数据 | 独立于集群版本测试备份/恢复及应用一致性恢复 |

### 在现有项目中使用 Terraform 编辑升级配置

以下是现有、由 state 管理的资源的**属性片段**，不是独立 Terraform 部署。请保留项目其他 IAM、网络、访问、加密、launch-template 和扩缩容配置。根据实际清单定义已审核变量并检查 plan；复制最小化的替代资源可能会重置设置或创建不同的集群。

对于现有集群资源，请有意选择跨一个次要版本的目标版本和支持策略。标准支持结束后，STANDARD 可能触发自动升级；EXTENDED 则接受后续的付费支持期。

```hcl
# Edit these arguments inside the existing aws_eks_cluster.main resource.
version = var.reviewed_target_version

upgrade_policy {
  support_type = var.reviewed_support_type
}
```

完整的 managed node group 资源需要 `node_role_arn`、`subnet_ids` 和 `scaling_config`；旧示例漏掉了前两项。请保留现有值。此前的 desired3/min2/max10 和 33% 更新预算都是示例输入，并非升级默认值或可用性保证。

```hcl
# Relevant arguments inside the existing aws_eks_node_group.main resource.
# Retain the rest of the existing resource, including its scaling_config.
node_role_arn = var.existing_node_role_arn
subnet_ids    = var.existing_node_subnet_ids
version       = aws_eks_cluster.main.version

update_config {
  max_unavailable_percentage = 33
}
```

对于每个现有 add-on，应在审核兼容性后使用已审核的 EKS 构建版本和明确的更新冲突策略。PRESERVE 是更新选项，不是 CreateAddon 冲突选项。它不能免除配置 Schema、身份或回滚检查。

```hcl
# Edit one already-managed aws_eks_addon resource after compatibility review.
addon_version               = var.reviewed_addon_version
resolve_conflicts_on_update = "PRESERVE"
```

<!-- Parent repair: execution graphic needs operation-specific ordering and validation gates beyond API-server health.
![Workflow diagram of the five-phase EKS cluster upgrade -- assessment, staging test, preparation, execution, and validation -- with staging and validation retried on failure, and API server health as the one hard gate during execution that routes to contacting AWS Support on failure.](../.gitbook/assets/en-eks-12-kubernetes-version-roadmap-18.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-12-kubernetes-version-roadmap-18.html)
-->

[EKS 更新流程](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html) · [EKS 回滚前置条件与顺序](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html) · [Terraform EKS node group 参考](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eks_node_group) · [Terraform EKS add-on 参考](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eks_addon)

---

<span id="9-future-outlook"></span>

## 9. 未来展望

### 区分已发布的上游变更与 EKS 可用性

截至2026年10月12日，Kubernetes **1.37 已在 EKS 上提供**。AWS 于 10 月 1 日提供该版本；上游于 8 月 26 日发布。

本文逐版本详述的内容截至 1.36。示例主要依据 1.36.2 检查，并未悄然升级到 1.37。

升级前请阅读 EKS 发布说明，并核实 add-on、节点镜像、CSI 驱动程序和工作负载兼容性。

| EKS 1.37 变更 | 当前行为 | 升级影响 |
|---|---|---|
| Auto Mode NodePool 整合 | 若新的自定义 NodePool 未指定 `spec.disruption.consolidationPolicy`，默认值为 `Balanced`。内置的 `general-purpose` 和 `system` 池使用 `Balanced`，且不可更改。 | 如果自定义池需要其他行为，应设置明确策略。 |
| SELinux 卷挂载 | 对受支持的 CSI 和 Pod 配置，该功能稳定并默认启用。 | 升级节点前，请检查驱动程序支持情况，以及跨不同 SELinux 标签共享卷的工作负载。 |

| 已核实的上游 1.37 项目 | 说明 |
|---|---|
| KYAML | 稳定的 kubectl 输出格式；不是新的 API server YAML 验证器 |
| GenericWorkload | Beta，默认禁用；仅因单独的 GangScheduling 门控发生变化，并不意味着原生组调度已达 GA |
| DRADeviceTaints / DRAResourceClaimDeviceStatus | 晋级为稳定；仍有驱动程序/报告要求 |
| PodLevelResources / Pod 级原地调整 | 根据已发布的门控历史，仍为 Beta，并未像此前预测的那样达到 GA |
| DRAPartitionableDevices | 仍为 Beta；不承诺通用 GPU 共享实现 |

应使用已发布代码/变更日志和具体 KEP，而不是未经核实的“预计下一个版本”日期。即使功能稳定，门控默认值/锁定状态和 API/驱动程序可用性仍可能不同。

### 生态系统趋势并非 Kubernetes 发布承诺

DRA 驱动程序、设备共享、拓扑感知放置和批处理协调仍在不断发展。GPU time-slicing/MIG/RDMA 行为取决于实际硬件和驱动程序，不仅取决于核心 API 版本。供应链签名/验证、机密容器、GitOps、平台工程、OpenTelemetry 和 Wasm 都属于生态系统集成主题，各自有独立项目和发布策略。它们不会自动全部内置于 Kubernetes，也不保证在某个指定年份实现。

应根据支持期限、兼容性和业务风险，保持定期升级/演练节奏。“每季度”和上游约四个月的发布节奏并不是同一时间表。停留在合适的标准支持版 EKS 上可以避免额外版本费用，但通用的 `latest−1` 规则不能替代应用验证，也不要求立即无风险地采用每个 GA 功能。

### 历史规划模板：不是当前部署建议

此前的韩文版本章节包含以下示例清单和计划月份。版本/数量/月数均保留为历史示例输入，不代表实际发现的机群、已执行升级或已验证的组件组合。尤其不能把旧 Istio/Argo CD/chart 版本视为与较新 Kubernetes 版本兼容。制定新计划时，应使用实际清单和当前兼容性证据替换这些值。以下审核操作更正了有关自动启用 nftables、DRA CRD 和 KYAML 的旧假设，但没有虚构重新执行结果。

```yaml
historical_planning_example:
  provenance: Illustrative prior chapter inputs; no executed upgrade or verified component
    compatibility.
  starting_state:
    cluster_version: '1.33'
    node_count: 50
    workload_count: 200
    component_versions:
    - name: istio
      version: '1.22'
    - name: argocd
      version: '2.11'
    - name: prometheus-stack
      version: '60.0'
  target_version: '1.36'
  upgrade_path:
  - '1.33'
  - '1.34'
  - '1.35'
  - '1.36'
  phases:
  - target: '1.34'
    historical_planned_month: 2025-11
    review:
    - DRA API/driver and VAC compatibility
    - Proxy backend migration only if deliberately selected; not automatic
  - target: '1.35'
    historical_planned_month: 2026-03
    review:
    - In-place resize and the actual VPA release/mode
    - KYAML is a client output format, not a server parsing migration
  - target: '1.36'
    historical_planned_month: 2026-07
    review:
    - Pod-level resource policies and supported compute/runtime
    - Gang scheduling is still alpha in1.36; not a GA EKS prerequisite
```

---

<span id="10-references"></span>

## 10. 参考资料

针对具体版本的来源和供应商 API 文档优先于旧摘要表或工具捆绑的假设。实际变更前，请重新核实目标版本、供应商、组件发布版本和功能配置。

- [Kubernetes 发布版本](https://kubernetes.io/releases/)
- [补丁支持策略](https://kubernetes.io/releases/patch-releases/)
- [功能门控](https://kubernetes.io/docs/reference/command-line-tools-reference/feature-gates/)
- [已移除的功能门控](https://kubernetes.io/docs/reference/command-line-tools-reference/feature-gates-removed/)
- [API 弃用策略](https://kubernetes.io/docs/reference/deprecation-policy/)
- [API 迁移指南](https://kubernetes.io/docs/reference/using-api/deprecation-guide/)
- [Kubernetes 1.36.2 源码](https://github.com/kubernetes/kubernetes/tree/v1.36.2)
- [Kubernetes 1.37 变更日志](https://github.com/kubernetes/kubernetes/blob/v1.37.0/CHANGELOG/CHANGELOG-1.37.md)
- [EKS 支持日历](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)
- [EKS 版本说明](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions-standard.html)
- [EKS 升级](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html)
- [EKS 回滚](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html)
- [EKS add-on 兼容性 API](https://docs.aws.amazon.com/eks/latest/APIReference/API_DescribeAddonVersions.html)
- [EKS Auto Mode 网络](https://docs.aws.amazon.com/eks/latest/userguide/auto-networking.html)
- [EKS 最佳实践](https://docs.aws.amazon.com/eks/latest/best-practices/introduction.html)
- [EKS 定价](https://aws.amazon.com/eks/pricing/)
- [VPA 1.8.0 功能](https://github.com/kubernetes/autoscaler/blob/vertical-pod-autoscaler-1.8.0/vertical-pod-autoscaler/docs/features.md)
- [Pluto](https://github.com/FairwindsOps/pluto)
- [Kubent](https://github.com/doitintl/kube-no-trouble)

### 官方发布公告

- [Kubernetes 1.29](https://kubernetes.io/blog/2023/12/13/kubernetes-v1-29-release/)
- [Kubernetes 1.30](https://kubernetes.io/blog/2024/04/17/kubernetes-v1-30-release/)
- [Kubernetes 1.31](https://kubernetes.io/blog/2024/08/13/kubernetes-v1-31-release/)
- [Kubernetes 1.32](https://kubernetes.io/blog/2024/12/11/kubernetes-v1-32-release/)
- [Kubernetes 1.33](https://kubernetes.io/blog/2025/04/23/kubernetes-v1-33-release/)
- [Kubernetes 1.34](https://kubernetes.io/blog/2025/08/27/kubernetes-v1-34-release/)
- [Kubernetes 1.35](https://kubernetes.io/blog/2025/12/17/kubernetes-v1-35-release/)
- [Kubernetes 1.36](https://kubernetes.io/blog/2026/04/22/kubernetes-v1-36-release/)

## 测验与后续步骤

- [版本功能与路线图测验](../quizzes/eks/12-kubernetes-version-roadmap-quiz.md)
- [EKS 升级](08-eks-upgrades.md)
- [EKS 高级调试](11-eks-advanced-debugging.md)
- [EKS 集群创建实验](../labs/eks/01-eks-cluster-creation-lab.md)
- [EKS Auto Mode](../eks-auto-mode/README.md)

< [上一章：EKS 高级调试](11-eks-advanced-debugging.md) | [目录](../README.md) >
