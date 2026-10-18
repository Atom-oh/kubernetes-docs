# 5. 云和 CNI 网络设计练习手册

> **最后更新**：2026 年 9 月 15 日

**前提条件：**[协议](01-protocol-projects.md)、[路由](02-routing-policy-convergence.md)、[Linux 观测](04-linux-performance.md)，以及 Kubernetes Pod / Service / EndpointSlice 概念。实时观测需要已获批准的现有实验账户 / 集群和所需的只读权限。

**目标**：从 DNS 到后端和返回路径，串联设计、观测结果与策略。本章中的命令只查询现有资源，不会创建资源或注入故障。若没有账户，请完成设计练习，并将结果标记为**设计审查**。

准备 AWS CLI 和与集群兼容的 kubectl 版本，然后验证实验 profile / context。如果缺少某个工具，请按照平台特定的 [AWS CLI 安装](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)和 [kubectl 安装](https://kubernetes.io/docs/tasks/tools/)说明操作。本手册不会假设工具已自动安装或凭证已自动签发成功。

## 1. 将 AWS 范围转化为问题 {#design-questions}

[官方 AWS Advanced Networking 考试范围](https://docs.aws.amazon.com/aws-certification/latest/advanced-networking-specialty-01/advanced-networking-specialty-01.html)涵盖云 / 混合网络设计、实施、运维、安全和自动化。将每个领域转化为关于你所设计方案的问题。

| 领域 | 问题 | 证据 |
|---|---|---|
| 地址 / 路由 | 适用哪个目标前缀和下一跳？是否存在返回路径？ | VPC / 子网 / TGW 路由以及实际源 / 目标地址 |
| 名称解析 | 由哪个解析器、区域或转发规则应答？ | 查询名称 / 类型、解析器、应答、TTL 和时间 |
| 入口 | DNS 选择了哪个前端？注册了哪个后端？ | 侦听器、目标类型 / 端口、运行状况检查和实际目标 |
| 隔离 | 哪一层负责强制执行允许和禁止的流量规则？ | SG / NACL / CNI 策略的适用范围和实际执行情况 |
| 韧性 | 单个组件故障时，哪些流量会受影响？ | 故障边界、替代路径、状态 / 恢复计划 |
| 性能 / 成本 | 哪些条件会影响延迟、吞吐量、地址容量和数据传输？ | 测量时间段 / 方向 / 资源以及当前成本输入 |

考试范围用于界定学习主题。它不是部署答案指南，也不保证特定设计能达到某种性能。

## 2. 确认环境和权限 {#inventory}

将这些名称替换为**实际且已批准的实验值**。以下字符串不是可用于操作的账户信息。

```bash
LAB_AWS_PROFILE='REPLACE_WITH_LAB_PROFILE'
LAB_AWS_REGION='REPLACE_WITH_LAB_REGION'
LAB_CONTEXT='REPLACE_WITH_LAB_KUBERNETES_CONTEXT'
LAB_NAMESPACE='REPLACE_WITH_LAB_NAMESPACE'
LAB_SERVICE='REPLACE_WITH_LAB_SERVICE'
```

**由操作员批准的查询终端：**

```bash
aws --version
kubectl version --client
aws --profile "$LAB_AWS_PROFILE" --region "$LAB_AWS_REGION" \
  sts get-caller-identity
kubectl --context "$LAB_CONTEXT" auth can-i get services -n "$LAB_NAMESPACE"
kubectl --context "$LAB_CONTEXT" auth can-i list endpointslices.discovery.k8s.io \
  -n "$LAB_NAMESPACE"
```

如果账户、角色或 context 与实验目标不符，请停止。`no`、`AccessDenied` 和凭证过期都表示当前无法进行观测。不要自动授予管理员权限，也不要改用其他账户重试。应向获得授权的操作员申请所需的最低限度证据。

在经批准的笔记中保留原始账户 ID、ARN、IP 和资源名称。在公开报告中使用一致的别名。无需收集配置凭证、Secret 或令牌。

## 3. 将请求路径映射到实际资源 {#request-path}

为一条请求选定主机名、协议、端口和时间。下表中的关系需要核查，但它们未必对应不同的物理跳点。

| 观测目标 | 关系 | 常见错误 |
|---|---|---|
| DNS | 所选解析器返回的前端地址 | 把名称解析当作 TCP / HTTP 成功 |
| LB 侦听器 / 目标组 | 前端协议 / 规则和目标类型 / 端口 | 假设侦听器端口与后端端口相同 |
| Service | 选择器或单独管理的端点，以及 port / targetPort | 假设 Service 对象必然保证存在端点 |
| EndpointSlice / Pod | 实际地址 / 端口、就绪状态、节点和时间戳 | 将端点就绪状态等同于 LB 健康状态 |
| CNI / 节点 / VPC | 地址、路由、策略和转发实现 | 假设 EKS 的所有计算模式都使用相同的 DaemonSet 和路径 |
| 返回路径 | 回复目的地址、SNAT、状态跟踪和路由 | 仅凭正向可达性就认定双向连通 |

AWS Load Balancer Controller 是使用 AWS API 的**控制平面**协调器。应用请求不会经过它的 Controller Pod。

普通的 `ip` 目标会连接到注册的后端 IP；`instance` 目标则会经过节点 / NodePort 路径。请检查受支持的计算 / CNI 组合、实际注册项、代理实现和流量策略。Service 用于描述逻辑端点选择：不要总是把 ClusterIP 画成一个额外的数据包跳点。请结合 [AWS 目标类型说明](https://docs.aws.amazon.com/eks/latest/best-practices/load-balancing.html)和 [Kubernetes 虚拟 IP 实现](https://kubernetes.io/docs/reference/networking/virtual-ips/)阅读。

### 观测 Service 和 EndpointSlice

```bash
kubectl --context "$LAB_CONTEXT" -n "$LAB_NAMESPACE" \
  get service "$LAB_SERVICE" \
  -o jsonpath='{.spec.type}{"\n"}{.spec.selector}{"\n"}{.spec.ports}{"\n"}{.spec.externalTrafficPolicy}{"\n"}'
kubectl --context "$LAB_CONTEXT" -n "$LAB_NAMESPACE" \
  get endpointslices.discovery.k8s.io \
  -l "kubernetes.io/service-name=$LAB_SERVICE" -o json
```

应在**同一个端点对象内**关联地址和条件。不要将地址数组和 `ready` 数组分开摊平，再臆测两者的对应关系。`items: []` 表示针对该选择条件未观测到端点；它本身无法说明原因是 DNS 还是防火墙。还要考虑没有选择器的 Service 和手动管理的端点。

确认实际选择器后，只查询相关 Pod。

```bash
LAB_SELECTOR='REPLACE_WITH_VERIFIED_KEY=VALUE'
kubectl --context "$LAB_CONTEXT" -n "$LAB_NAMESPACE" \
  get pods -l "$LAB_SELECTOR" -o wide
kubectl --context "$LAB_CONTEXT" -n "$LAB_NAMESPACE" get networkpolicies
```

NetworkPolicy 对象列表不能证明策略引擎已启用或策略已得到执行。还应分别确认 CNI、计算模式、支持的 API、选中的 Pod、方向、端口和实际流量。其他策略 CRD 或托管策略需要由各自的所有者提供证据。

### 观测 AWS 目标和路由

指定操作员已验证的目标组和 VPC。还要记录将此目标组与选定 Service 关联起来的证据。

```bash
LAB_TARGET_GROUP_ARN='REPLACE_WITH_VERIFIED_TARGET_GROUP_ARN'
LAB_VPC_ID='REPLACE_WITH_LAB_VPC_ID'
aws --profile "$LAB_AWS_PROFILE" --region "$LAB_AWS_REGION" \
  elbv2 describe-target-groups --target-group-arns "$LAB_TARGET_GROUP_ARN" \
  --query 'TargetGroups[].{Type:TargetType,Port:Port,Protocol:Protocol,Vpc:VpcId,HealthPath:HealthCheckPath}'
aws --profile "$LAB_AWS_PROFILE" --region "$LAB_AWS_REGION" \
  elbv2 describe-target-health --target-group-arn "$LAB_TARGET_GROUP_ARN"
aws --profile "$LAB_AWS_PROFILE" --region "$LAB_AWS_REGION" \
  ec2 describe-route-tables --filters "Name=vpc-id,Values=$LAB_VPC_ID" \
  --query 'RouteTables[].{Id:RouteTableId,Associations:Associations,Routes:Routes}'
```

`healthy` 是已配置运行状况检查的结果，并不代表最终用户经过整个 DNS / TLS / 授权 / 请求路径都健康。对于值为 `null` 的字段，应先判断该协议 / 配置是否要求该字段。如果目标类型不属于本手册覆盖的 `ip` / `instance` 模型，就需要修订路径模型。

如果子网没有显式的路由表关联，请检查主路由表是否适用。根据实际源子网，将目标、目标资源和路由状态关联起来，然后检查目标的返回路径。不要用假设填补权限或遥测数据的缺失。

## 4. 混合网络设计练习 {#hybrid-design}

**设计场景**：生产 VPC A 需要共享 DNS / 服务。开发 VPC B 不得直接访问 A 的数据服务。本地数据中心客户端只能访问指定的共享服务。如果无法获得实际地址 / 账户，请使用别名。

1. 记录源、目标、协议、允许 / 拒绝意图和返回路径。
2. 区分 VPC / 子网 / TGW 路由表与 attachment（连接）。
3. 将 TGW **关联**（association）与**传播**（propagation）区分开来：关联选择 attachment 用于查找路由的路由表，传播则将学习到的路由写入路由表。一个 attachment 可以关联一张路由表，并向多张路由表传播路由。传播不会让 attachment 使用那张路由表。
4. 说明路由隔离与 SG / NACL / 工作负载策略各自承担的职责。
5. 确定私有区域、解析器、转发规则和双向 DNS 路径。
6. 分别考虑 CIDR 重叠、缺少返回路由和传播错误，并说明每种情况会影响哪些流量。

查看 [TGW 关联 / 传播说明](https://repost.aws/knowledge-center/transit-gateway-connect-vpcs-from-vpn)，并将实际环境与[跨组织 VPC 连接](../05-cross-org-vpc-connectivity.md)进行比较。BGP 策略知识有助于表达设计意图；本地设备命令不能直接应用于 TGW。

## 5. 根据观测结果分析问题 {#failure-workbook}

使用**提供的证据或经批准采集的证据**。以下是分析练习，不是修改生产账户策略的操作说明。

| 观测结果 | 下一步检查 | 无依据的结论 |
|---|---|---|
| DNS 有应答，但 TCP 失败 | 目标、端口、路由、访问控制和侦听器 | DNS 健康就证明后端健康 |
| EndpointSlice 已就绪，但目标不健康 | 已注册的 IP / 端口、运行状况检查配置和路径 | 就绪状态等于 LB 健康状态 |
| 同节点成功、跨节点失败 | 实际 CNI / 节点 / VPC 路径、策略、MTU 和返回路由 | 把原因笼统归结为“CNI 错误” |
| 只有小请求成功 | 数据包大小、PMTU 反馈、重传和应用条件 | 所有故障都是 MTU 问题 |
| TGW 只有一个方向连通 | 两侧的关联关系和路由表 | 传播会自动保证返回路径 |

数据包 / 主机观测需要单独的权限和观测位置。不要把资源 `get` 命令输出描述为实测的内核转发路径。应让获授权的操作员提供节点 / Pod 命名空间的观测结果，或者使用另行准备的实验指南。

## 6. 交付物和完成标准 {#completion}

- 允许 / 禁止流量矩阵，以及正向 / 返回路径图。
- 每个组件的实际职责：控制平面、路由、策略或应用。
- 与 context、目标和时间戳关联的 Service / EndpointSlice / 目标 / 路由证据。
- 至少两个假设，并说明其状态为已确认、已否定或未知的理由。
- 部署前检查、观测范围、恢复责任方和恢复后的检查。

没有实时证据时，应标记为**设计审查已完成**，而不是云运维验证已完成。本章中的查询不会修改资源，因此无需执行网络恢复命令。应按照经批准的保留 / 销毁规则管理已保存的原始证据。

## 相关资料

- [EKS 网络](../../eks/03-eks-networking-part1.md)、[VPC CNI](../01-vpc-cni.md)、[AWS Load Balancer Controller](../03-aws-lb-controller.md)
- [Pod 基准测试条件](../06-pod-network-benchmark.md)、[Cilium 可观测性](../cilium/06-security-visibility.md)
- [EKS 网络策略](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html)
- [NLB / EKS 支持条件](https://docs.aws.amazon.com/eks/latest/userguide/network-load-balancing.html)
- [EndpointSlice](https://kubernetes.io/docs/concepts/services-networking/endpoint-slices/)
- [AWS CLI 目标健康状态](https://docs.aws.amazon.com/cli/latest/reference/elbv2/describe-target-health.html)

[上一章：Linux 性能](04-linux-performance.md) · [测验](../../quizzes/networking/expert/05-cloud-cni-design-quiz.md) · [下一章：自动化与评估](06-automation-capstone.md)
