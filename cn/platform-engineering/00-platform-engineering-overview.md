# Platform Engineering 概览

> **最后更新**: February 23, 2026

## 1. 什么是 Platform Engineering？

### 定义

Platform Engineering（平台工程）是**为开发者自助服务而设计、构建和运营工具、工作流与基础设施的学科**。Platform Engineering 团队构建 **Internal Developer Platform (IDP)（内部开发者平台）**，使开发者无需直接处理基础设施复杂性，就能快速且安全地部署应用程序。

### Internal Developer Platform (IDP)

IDP 是一种自助服务平台，它抽象了基础设施配置、部署和监控等运维任务，使开发者能够专注于编写代码。

**IDP 的核心价值：**

- **自助服务**：开发者无需提交工单即可直接配置基础设施
- **护栏**：默认内置安全性与合规性
- **标准化**：通过 Golden Paths（黄金路径）实现一致的部署模式
- **自动化**：通过消除重复性任务降低认知负担

### Platform Engineering vs DevOps vs SRE

| 方面 | Platform Engineering | DevOps | SRE |
|--------|---------------------|--------|-----|
| **关注点** | 开发者体验与自助服务平台建设 | 开发与运维的文化融合 | 服务可靠性与运维自动化 |
| **关键交付物** | Internal Developer Platform | CI/CD pipelines、自动化脚本 | SLO/SLI、错误预算、繁琐工作自动化 |
| **主要指标** | 开发者生产力、入职时间 | 部署频率、交付前置时间 | 可用性、错误预算消耗率 |
| **团队结构** | 专职平台团队 | 跨职能团队 | SRE 团队或嵌入式 SRE |
| **关系** | 构建在 DevOps + SRE 之上的产品层 | 文化与方法论 | 运维工程实践 |

> **注意**：这三种方法是互补的，而不是互斥的。Platform Engineering 是关于**将 DevOps 原则和 SRE 实践封装为产品**。

### 平台团队角色与结构

**关键角色：**

| 角色 | 职责 |
|------|---------------|
| **Platform Product Manager** | 分析开发者需求，管理 IDP 路线图，定义成功指标 |
| **Platform Engineer** | 构建核心 IDP 基础设施，Kubernetes/cloud 自动化 |
| **Platform SRE** | 平台自身的可靠性、监控、事件响应 |
| **Developer Experience (DX) Engineer** | CLI 工具、文档、入职工作流 |

---

## 2. AWS CAF Platform Perspective

### AWS Cloud Adoption Framework 简介

[AWS Cloud Adoption Framework (CAF)](https://docs.aws.amazon.com/prescriptive-guidance/latest/aws-caf-platform-perspective/platform-eng.html) 为云采用提供组织层面的指南。**Platform Perspective** 涵盖三个关键领域：

1. **Platform Engineering** -- 本节的重点
2. **Platform Architecture** -- 云架构设计原则
3. **Data Architecture** -- 数据管理与分析策略

### 成熟度模型：START → ADVANCE → EXCEL

AWS CAF 将云平台成熟度定义为三个阶段。让我们看看 Kubernetes 生态系统工具如何映射到每个阶段。

#### START：基础建设

建立基础设施并设置安全护栏的阶段。

| 能力 | 描述 | Kubernetes 生态系统映射 |
|-----------|-------------|------------------------------|
| **Landing Zone & Guardrails** | 多账户环境、预防性/侦测性控制 | EKS cluster 配置、[OPA Gatekeeper](../security/09-opa-gatekeeper.md) / [Kyverno](../security/01-kyverno-policy-management.md) |
| **Authentication** | 集中式身份管理、IdP 集成 | [K8s Authentication & Authorization](../security/02-kubernetes-auth-authz.md)、OIDC、IRSA |
| **Networking** | 集中式网络管理 | VPC CNI、[Calico](../networking/calico/README.md)、[Cilium](../networking/cilium/README.md) |
| **Logging** | 跨账户可观测性 | [Prometheus](../observability/metrics/01-prometheus.md)、[Loki](../observability/logging/01-loki.md)、[OpenTelemetry](../observability/tracing/03-opentelemetry.md) |
| **Controls** | 程序化安全控制 | [Pod Security Standards](../security/03-pod-security-standards.md)、[Network Policies](../security/04-network-policies.md) |
| **Cost Management** | 标签策略、成本分摊 | Resource Quotas、LimitRange、[EKS Cost Optimization](../eks/07-eks-cost-optimization.md) |

#### ADVANCE：运维扩展

扩展自动化并构建集中式可观测性的阶段。

| 能力 | 描述 | Kubernetes 生态系统映射 |
|-----------|-------------|------------------------------|
| **Infrastructure Automation** | IaC、自助服务产品 | [ACK](./02-ack.md)、[KRO](./03-kro.md)、Crossplane、[Helm](./01-helm.md) |
| **Central Observability** | 日志/指标/追踪关联 | [Grafana](../observability/grafana/README.md) Stack、[CloudWatch](../observability/metrics/04-cloudwatch-metrics.md) |
| **Systems Management** | 镜像标准化、补丁管理 | [Image Security](../security/07-image-security.md)、[Kyverno](../security/01-kyverno-policy-management.md) |
| **Credential Management** | 临时凭证、自动轮换 | [Secrets Management](../security/05-secrets-management.md)、IRSA |
| **Security Tooling** | XDR、细粒度监控 | [Runtime Security](../security/08-runtime-security.md)、Trivy、GuardDuty |

#### EXCEL：持续优化

实现自动化治理与持续改进的阶段。

| 能力 | 描述 | Kubernetes 生态系统映射 |
|-----------|-------------|------------------------------|
| **Automated Identity Management** | 通过 IaC 进行版本控制的角色/策略 | 基于 [GitOps](../gitops/README.md) 的 RBAC 管理 |
| **Anomaly Detection** | 主动漏洞评估、异常模式检测 | [Runtime Security](../security/08-runtime-security.md) (Falco)、审计日志分析 |
| **Threat Analysis** | 对照行业基准进行持续监控 | CIS Benchmark、kube-bench |
| **Permission Refinement** | 自动化最小权限原则 | 基于 K8s 审计日志的 RBAC 优化 |
| **Platform Metrics** | 与组织目标对齐的指标 | DORA metrics、SLI/SLO |

---

## 3. IDP 参考架构

### 基于 Kubernetes 的 IDP 层次结构

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

### 各层的角色与工具映射

| 层 | 角色 | 关键工具 | 仓库文档 |
|-------|------|-----------|-----------|
| **Developer Interface** | 开发者交互使用的 UI/CLI | Backstage、Port、Argo Workflows UI | - |
| **Integration/Orchestration** | 声明式状态管理、部署自动化 | ArgoCD、FluxCD、KRO | [GitOps](../gitops/README.md)、[KRO](./03-kro.md) |
| **Resource** | 云/K8s 资源抽象 | ACK、Helm、Operators | [ACK](./02-ack.md)、[Helm](./01-helm.md)、[K8s Extensions](./04-kubernetes-extensions.md) |
| **Infrastructure** | 实际计算/网络/存储 | EKS、VPC、IAM | [EKS](../eks/01-eks-introduction.md) |

### Self-Service Catalog Pattern (KRO RGD + ACK)

将 [KRO](./03-kro.md) 的 ResourceGraphDefinition (RGD) 与 [ACK](./02-ack.md) 结合，可以实现强大的自助服务模式：

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

通过这个单一 manifest，KRO 会在内部创建：
1. **Deployment + Service** (Kubernetes native)
2. **RDS Instance** (AWS resource via ACK)
3. **IAM Role** (Permission setup via ACK)

有关详细示例，请参见 [ExampleCorp Integration Example](./05-example-corp-app.md)。

### Golden Path 概念

Golden Path 是平台团队提供的**推荐部署路径**：

- **目的**：指导开发者使用经过验证的方法快速上手
- **特征**：推荐但不强制 -- 开发者可在需要时偏离，但在大多数情况下它是最佳选择
- **示例**：
  - “New Microservice Deployment” Golden Path：Helm Chart 模板 → ArgoCD 集成 → 自动 Prometheus metrics 收集
  - “Database Provisioning” Golden Path：KRO RGD manifest → 通过 ACK 创建 RDS → 自动 Secret 注入

---

## 4. Platform Engineering 工具生态系统

本节说明本仓库涵盖的工具在 platform engineering 领域中的位置。

| 类别 | 工具 | 仓库文档链接 |
|----------|-------|---------------|
| **Package Management** | Helm、Kustomize | [Helm](./01-helm.md) |
| **AWS IaC** | ACK、CloudFormation | [ACK](./02-ack.md) |
| **Resource Orchestration** | KRO、Crossplane | [KRO](./03-kro.md) |
| **Extension Mechanisms** | CRD、Operators | [Kubernetes Extension Mechanisms](./04-kubernetes-extensions.md) |
| **GitOps** | ArgoCD、FluxCD | [GitOps Section](../gitops/README.md) |
| **Policy/Governance** | Kyverno、OPA Gatekeeper | [Kyverno](../security/01-kyverno-policy-management.md)、[OPA Gatekeeper](../security/09-opa-gatekeeper.md) |
| **Observability** | Prometheus、Grafana、OTel | [Observability Section](../observability/README.md) |
| **Autoscaling** | KEDA、Karpenter | [KEDA](../autoscaling/01-keda.md)、[Karpenter](../autoscaling/02-karpenter.md) |
| **Service Mesh** | Istio、Cilium | [Istio](../service-mesh/istio/README.md)、[Cilium Service Mesh](../service-mesh/cilium-service-mesh/README.md) |
| **Security** | Falco、Trivy、PSS | [Runtime Security](../security/08-runtime-security.md)、[Image Security](../security/07-image-security.md)、[PSS](../security/03-pod-security-standards.md) |

---

## 5. Platform 成熟度自评检查清单

评估组织的 platform engineering 成熟度。每个条目都链接到本仓库中的相关文档。

### START 阶段

| 检查 | 条目 | 相关文档 |
|-------|------|-------------|
| [ ] | EKS clusters 是否以标准化方式创建？ | [EKS Cluster Creation](../eks/02-eks-cluster-creation-part1.md) |
| [ ] | RBAC policies 是否已定义并强制执行？ | [Authentication & Authorization](../security/02-kubernetes-auth-authz.md) |
| [ ] | Network policies 是否已应用？ | [Network Policies](../security/04-network-policies.md) |
| [ ] | 是否已配置基础监控与日志记录？ | [EKS Monitoring](../eks/06-eks-monitoring-logging.md) |
| [ ] | Pod Security Standards 是否已应用？ | [PSS](../security/03-pod-security-standards.md) |
| [ ] | 是否已设置 resource quotas 和 limits？ | [EKS Cost Optimization](../eks/07-eks-cost-optimization.md) |

### ADVANCE 阶段

| 检查 | 条目 | 相关文档 |
|-------|------|-------------|
| [ ] | 基础设施是否使用 IaC 管理？(ACK、Terraform 等) | [ACK](./02-ack.md) |
| [ ] | 是否已建立 GitOps workflow？ | [GitOps](../gitops/README.md) |
| [ ] | 集中式 observability stack 是否已运行？ | [Observability](../observability/README.md) |
| [ ] | 是否使用 policy engine 自动化治理？ | [Kyverno](../security/01-kyverno-policy-management.md) |
| [ ] | Secrets 是否从外部存储自动管理？ | [Secrets Management](../security/05-secrets-management.md) |
| [ ] | Container image scanning 是否已自动化？ | [Image Security](../security/07-image-security.md) |

### EXCEL 阶段

| 检查 | 条目 | 相关文档 |
|-------|------|-------------|
| [ ] | 是否向开发者提供 self-service catalog？ | [KRO](./03-kro.md)、[ExampleCorp](./05-example-corp-app.md) |
| [ ] | DORA metrics 是否已被衡量并改进？ | - |
| [ ] | Runtime security monitoring 是否已运行？ | [Runtime Security](../security/08-runtime-security.md) |
| [ ] | Autoscaling 是否已针对 workloads 优化？ | [KEDA](../autoscaling/01-keda.md)、[Karpenter](../autoscaling/02-karpenter.md) |
| [ ] | Platform SLOs 是否已定义并跟踪？ | [Observability Analysis](../ops/08-observability-analysis.md) |
| [ ] | Golden Paths 是否已定义并记录？ | 本文档（第 3 节） |

---

## 6. 参考资料

- [AWS CAF Platform Perspective - Platform Engineering](https://docs.aws.amazon.com/prescriptive-guidance/latest/aws-caf-platform-perspective/platform-eng.html)
- [CNCF Platform White Paper](https://tag-app-delivery.cncf.io/whitepapers/platforms/)
- [Platform Engineering on Kubernetes (O'Reilly)](https://www.oreilly.com/library/view/platform-engineering-on/9781617299322/)
- [Backstage.io - Open Source IDP Framework](https://backstage.io/)
- [Internal Developer Platform](https://internaldeveloperplatform.org/)
