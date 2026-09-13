# 平台工程概述

> **最后更新**: September 12, 2026

## 1. 什么是平台工程？

### 定义

平台工程是**为开发者自助服务而设计、构建和运营工具、工作流与基础设施的学科**。平台工程团队构建**内部开发者平台（Internal Developer Platform, IDP）**，使开发者能够快速、安全地部署应用，而无需直接面对基础设施的复杂性。

### 内部开发者平台（IDP）

IDP 是一个自助服务平台，它对基础设施预配、部署和监控等运维工作进行抽象，让开发者可以专注于编写代码。

**IDP 的核心价值：**

- **自助服务**：通过 API、CLI 或门户申请已批准的资源/操作
- **护栏（Guardrails）**：实施并验证安全策略、审批与审计路径
- **标准化**：通过 Golden Path（黄金路径）实现一致的部署模式
- **自动化**：消除重复性工作，降低认知负荷

### 平台工程 vs DevOps vs SRE

| 方面 | 平台工程 | DevOps | SRE |
|--------|---------------------|--------|-----|
| **关注点** | 开发者体验与自助服务平台建设 | 开发与运维的文化融合 | 服务可靠性与运维自动化 |
| **主要交付物** | 内部开发者平台 | CI/CD 流水线、自动化脚本 | SLO/SLI、错误预算、繁琐工作自动化 |
| **核心指标** | 开发者生产力、上手时间 | 部署频率、交付前置时间 | 可用性、错误预算消耗率 |
| **团队结构** | 专职平台团队 | 跨职能团队 | SRE 团队或嵌入式 SRE |
| **相互关系** | 与 DevOps 和 SRE 协作的产品化平台实践 | 文化与方法论 | 运维工程实践 |

> **注意**：这三种方式是互补的，而非互斥。平台工程的本质是**把 DevOps 原则与 SRE 实践作为产品来打包交付**。

### 平台团队的角色与结构

**关键角色：**

| 角色 | 职责 |
|------|---------------|
| **平台产品经理（Platform Product Manager）** | 分析开发者需求，管理 IDP 路线图，定义成功指标 |
| **平台工程师（Platform Engineer）** | 构建 IDP 核心基础设施，Kubernetes/云自动化 |
| **平台 SRE（Platform SRE）** | 平台自身的可靠性、监控与事件响应 |
| **开发者体验（DX）工程师** | CLI 工具、文档、上手工作流 |

---

## 2. AWS CAF 平台视角

### AWS 云采用框架简介

[AWS CAF 平台视角](https://docs.aws.amazon.com/whitepapers/latest/overview-aws-cloud-adoption-framework/platform-perspective.html)包含七项能力：平台架构、数据架构、平台工程、数据工程、预配与编排、现代应用开发，以及持续集成/持续交付。本指南聚焦于平台工程。

### 成熟度模型：START → ADVANCE → EXCEL

AWS 的平台工程详细指南将改进任务划分为 Start、Advance 和 Excel 三个阶段。下文的 Kubernetes 映射/检查清单是本指南的教学示例，并非官方认证评分表，也不是每个组织都必须遵循的顺序。

#### START：奠定基础

建立基础设施底座并设置安全护栏的阶段。

| 能力 | 说明 | Kubernetes 生态映射 |
|-----------|-------------|------------------------------|
| **Landing Zone 与护栏** | 多账户环境、预防性/检测性控制 | EKS 集群配置、[OPA Gatekeeper](../security/09-opa-gatekeeper.md) / [Kyverno](../security/01-kyverno-policy-management.md) |
| **身份认证** | 集中式身份管理、IdP 集成 | [K8s 认证与授权](../security/02-kubernetes-auth-authz.md)、OIDC、IRSA |
| **网络** | 集中式网络管理 | VPC CNI、[Calico](../networking/calico/README.md)、[Cilium](../networking/cilium/README.md) |
| **可观测性** | 收集/保护日志、指标与链路追踪 | [Prometheus](../observability/metrics/01-prometheus.md)、[Loki](../observability/logging/01-loki.md)、[OpenTelemetry](../observability/tracing/03-opentelemetry.md) |
| **控制措施** | 以编程方式实现安全控制 | [Pod Security Standards](../security/03-pod-security-standards.md)、[Network Policies](../security/04-network-policies.md) |
| **成本管理** | 标签策略、成本分摊 | 账单标签、用量与成本分摊、[EKS 成本优化](../eks/07-eks-cost-optimization.md) |

#### ADVANCE：运维规模化

扩展自动化并构建集中式可观测性的阶段。

| 能力 | 说明 | Kubernetes 生态映射 |
|-----------|-------------|------------------------------|
| **基础设施自动化** | IaC、自助服务产品 | [ACK](./02-ack.md)、[KRO](./03-kro.md)、Crossplane、[Helm](./01-helm.md) |
| **集中式可观测性** | 日志/指标/链路追踪关联分析 | [Grafana](../observability/grafana/README.md) 技术栈、[CloudWatch](../observability/metrics/04-cloudwatch-metrics.md) |
| **系统管理** | 镜像标准化、补丁管理 | [镜像安全](../security/07-image-security.md)、[Kyverno](../security/01-kyverno-policy-management.md) |
| **凭证管理** | 临时凭证、自动轮换 | [Secrets 管理](../security/05-secrets-management.md)、IRSA |
| **安全工具** | XDR、细粒度监控 | [运行时安全](../security/08-runtime-security.md)、Trivy、GuardDuty |

#### EXCEL：持续优化

实现自动化治理与持续改进的阶段。

| 能力 | 说明 | Kubernetes 生态映射 |
|-----------|-------------|------------------------------|
| **自动化身份管理** | 通过 IaC 对角色/策略进行版本管理 | 基于 [GitOps](../gitops/README.md) 的 RBAC 管理 |
| **异常检测** | 主动漏洞评估、异常模式检测 | [运行时安全](../security/08-runtime-security.md)（Falco）、审计日志分析 |
| **威胁分析** | 对照行业基准持续监控 | CIS Benchmark、kube-bench |
| **权限精细化** | 自动化的最小权限原则 | 基于 K8s 审计日志的 RBAC 优化 |
| **平台指标** | 与组织目标对齐的指标 | DORA 指标、SLI/SLO |

---

## 3. IDP 参考架构

### 基于 Kubernetes 的 IDP 分层结构

```
┌─────────────────────────────────────────────────────┐
│            Developer Interface Layer                  │
│      (Backstage, Port, CLI, GitOps UI)               │
├─────────────────────────────────────────────────────┤
│         Integration/Orchestration Layer               │
│      (ArgoCD, FluxCD, Crossplane, KRO)               │
├─────────────────────────────────────────────────────┤
│                Resource Layer                         │
│      (ACK, Helm Charts, Operators, CRDs)             │
├─────────────────────────────────────────────────────┤
│              Infrastructure Layer                     │
│      (EKS, VPC, IAM, S3, RDS, ...)                   │
└─────────────────────────────────────────────────────┘
```

### 各层的作用与工具映射

| 层次 | 作用 | 主要工具 | 仓库文档 |
|-------|------|-----------|-----------|
| **开发者接口层** | 开发者直接交互的 UI/CLI | Backstage、Port、Argo Workflows UI | [Backstage](./06-backstage-idp.md) |
| **集成/编排层** | 声明式状态管理、部署自动化 | ArgoCD、FluxCD、KRO | [GitOps](../gitops/README.md)、[KRO](./03-kro.md) |
| **资源层** | 对云/K8s 资源进行抽象 | ACK、Helm、Operators | [ACK](./02-ack.md)、[Helm](./01-helm.md)、[K8s 扩展机制](./04-kubernetes-extensions.md) |
| **基础设施层** | 实际的计算/网络/存储 | EKS、VPC、IAM | [EKS](../eks/01-eks-introduction.md) |

### 自助服务目录模式（KRO RGD + ACK）

将 [KRO](./03-kro.md) 的 ResourceGraphDefinition（RGD）与 [ACK](./02-ack.md) 结合，可以实现强大的自助服务模式：

```yaml
# Single manifest written by developers
apiVersion: kro.run/v1alpha1
kind: WebApplication
metadata:
  name: my-app
spec:
  name: my-app
  image: my-app:v1.0
  replicas: 3
  database:
    engine: postgresql
    instanceClass: db.t3.medium
```

上面的 WebApplication 是**必须事先定义的自定义平台 API**，并不是 Kubernetes/kro 内置的 kind。如果没有对应的 RGD 及其生成的 CRD，该对象无法被 apply。本概述文档不提供完整的 RGD，也不会创建资源。

当 RGD 显式声明 Deployment、Service 以及 ACK RDS/IAM 资源时，kro 负责管理 Kubernetes 对象及其依赖关系，相应的 ACK 服务控制器则调用 AWS API。最终生成的资源集合取决于该 RGD。控制器/CRD、RBAC/IAM、配额、就绪状态/错误、凭证下发以及删除/保留策略都需要分别验证。创建一个 CR 并不能保证 AWS 侧立即就绪，也不保证预配过程具备事务性。参见 [ExampleCorp 示例](./05-example-corp-app.md)与 [kro 指南](./03-kro.md)。

### Golden Path 概念

Golden Path（黄金路径）是平台团队提供的**推荐部署路径**：

- **目的**：引导开发者使用经过验证的方法快速上手
- **特点**：受支持的推荐路径；例外情况需遵循组织审批流程，且不能绕过强制性的安全/数据策略
- **示例**：
  - “新建微服务部署”Golden Path：经验证的 Helm 模板 → 集成 ArgoCD → 配置指标发布/采集
  - “数据库预配”Golden Path：经验证的 RGD → ACK RDS 生命周期 → 经批准的凭证下发

---

## 4. 平台工程工具生态

本节说明本仓库所涵盖的工具在平台工程全景图中的位置。

| 类别 | 工具 | 仓库文档链接 |
|----------|-------|---------------|
| **包管理** | Helm、Kustomize | [Helm](./01-helm.md) |
| **AWS IaC** | ACK、CloudFormation | [ACK](./02-ack.md) |
| **资源编排** | KRO、Crossplane | [KRO](./03-kro.md) |
| **扩展机制** | CRD、Operators | [Kubernetes 扩展机制](./04-kubernetes-extensions.md) |
| **GitOps** | ArgoCD、FluxCD | [GitOps 章节](../gitops/README.md) |
| **策略/治理** | Kyverno、OPA Gatekeeper | [Kyverno](../security/01-kyverno-policy-management.md)、[OPA Gatekeeper](../security/09-opa-gatekeeper.md) |
| **可观测性** | Prometheus、Grafana、OTel | [可观测性章节](../observability/README.md) |
| **弹性伸缩** | KEDA、Karpenter | [KEDA](../autoscaling/01-keda.md)、[Karpenter](../autoscaling/02-karpenter.md) |
| **服务网格** | Istio、Cilium | [Istio](../service-mesh/istio/README.md)、[Cilium Service Mesh](../service-mesh/cilium-service-mesh/README.md) |
| **安全** | Falco、Trivy、PSS | [运行时安全](../security/08-runtime-security.md)、[镜像安全](../security/07-image-security.md)、[PSS](../security/03-pod-security-standards.md) |

---

## 5. 平台成熟度自评检查清单

评估你所在组织的平台工程成熟度。每一项都链接到本仓库中的相关文档。

### START 阶段

| 检查 | 项目 | 相关文档 |
|-------|------|-------------|
| [ ] | EKS 集群是否以标准化方式创建？ | [EKS 集群创建](../eks/02-eks-cluster-creation-part1.md) |
| [ ] | 是否定义并强制执行 RBAC 策略？ | [认证与授权](../security/02-kubernetes-auth-authz.md) |
| [ ] | 是否应用了网络策略？ | [Network Policies](../security/04-network-policies.md) |
| [ ] | 是否配置了基础监控与日志？ | [EKS 监控](../eks/06-eks-monitoring-logging.md) |
| [ ] | 是否应用了 Pod Security Standards？ | [PSS](../security/03-pod-security-standards.md) |
| [ ] | 是否设置了资源配额与限制？ | [EKS 成本优化](../eks/07-eks-cost-optimization.md) |

### ADVANCE 阶段

| 检查 | 项目 | 相关文档 |
|-------|------|-------------|
| [ ] | 基础设施是否用 IaC 管理？（ACK、Terraform 等） | [ACK](./02-ack.md) |
| [ ] | 是否建立了 GitOps 工作流？ | [GitOps](../gitops/README.md) |
| [ ] | 是否运行着集中式可观测性技术栈？ | [可观测性](../observability/README.md) |
| [ ] | 是否用策略引擎实现了治理自动化？ | [Kyverno](../security/01-kyverno-policy-management.md) |
| [ ] | 是否从外部存储自动管理 Secrets？ | [Secrets 管理](../security/05-secrets-management.md) |
| [ ] | 容器镜像扫描是否已自动化？ | [镜像安全](../security/07-image-security.md) |

### EXCEL 阶段

| 检查 | 项目 | 相关文档 |
|-------|------|-------------|
| [ ] | 是否向开发者提供了自助服务目录？ | [KRO](./03-kro.md)、[ExampleCorp](./05-example-corp-app.md) |
| [ ] | 是否在合适的服务范围内度量/改进 DORA 指标？ | [当前 DORA 定义](https://dora.dev/guides/dora-metrics/) |
| [ ] | 运行时安全监控是否已投入运行？ | [运行时安全](../security/08-runtime-security.md) |
| [ ] | 弹性伸缩是否针对工作负载做了优化？ | [KEDA](../autoscaling/01-keda.md)、[Karpenter](../autoscaling/02-karpenter.md) |
| [ ] | 是否定义并跟踪平台 SLO？ | [可观测性分析](../ops/08-observability-analysis.md) |
| [ ] | 是否定义并记录了 Golden Path？ | 本文档（第 3 节） |

---

### 指标与平台产品的成功

当前的 DORA 指南描述了五个指标：变更前置时间、部署频率、失败部署恢复时间、变更失败率和部署返工率。不要把旧版的四个指标或通用的 MTTR 与当前定义混用。应在服务/团队的语境中使用它们来改进交付与稳定性，而不是给个人排名。同时还要度量上手时间、任务成功率、用户满意度和采用率。度量工作不必等到 Excel 阶段才开始。

IDP 不只是一个门户：它还包括 API、CLI、模板、文档、支持以及运营责任。它并不会把应用安全的全部责任从开发团队转移出去。要对护栏的执行情况、例外、变更与恢复进行验证。

## 6. 参考资料

- [AWS CAF Platform Perspective - Platform Engineering](https://docs.aws.amazon.com/prescriptive-guidance/latest/aws-caf-platform-perspective/platform-eng.html)
- [CNCF Platform White Paper](https://tag-app-delivery.cncf.io/whitepapers/platforms/)
- [Backstage.io - Open Source IDP Framework](https://backstage.io/)
- [Internal Developer Platform](https://internaldeveloperplatform.org/)

- [Current DORA metrics](https://dora.dev/guides/dora-metrics/)
