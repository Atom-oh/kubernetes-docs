# Platform Engineering Overview

> **Last Updated**: February 2025

## 1. What is Platform Engineering?

### Definition

Platform Engineering is **the discipline of designing, building, and operating tools, workflows, and infrastructure for developer self-service**. Platform engineering teams build an **Internal Developer Platform (IDP)** that enables developers to deploy applications quickly and securely without dealing directly with infrastructure complexity.

### Internal Developer Platform (IDP)

An IDP is a self-service platform that abstracts operational tasks such as infrastructure provisioning, deployment, and monitoring so developers can focus on writing code.

**Core Values of an IDP:**

- **Self-Service**: Developers provision infrastructure directly without filing tickets
- **Guardrails**: Security and compliance built in by default
- **Standardization**: Consistent deployment patterns through Golden Paths
- **Automation**: Reduced cognitive load by eliminating repetitive tasks

### Platform Engineering vs DevOps vs SRE

| Aspect | Platform Engineering | DevOps | SRE |
|--------|---------------------|--------|-----|
| **Focus** | Developer experience and self-service platform construction | Cultural integration of development and operations | Service reliability and operational automation |
| **Key Deliverables** | Internal Developer Platform | CI/CD pipelines, automation scripts | SLO/SLI, error budgets, toil automation |
| **Primary Metrics** | Developer productivity, onboarding time | Deployment frequency, lead time | Availability, error budget burn rate |
| **Team Structure** | Dedicated platform team | Cross-functional teams | SRE team or embedded SREs |
| **Relationship** | Product layer on top of DevOps + SRE | Culture and methodology | Operational engineering practice |

> **Note**: These three approaches are complementary, not mutually exclusive. Platform Engineering is about **packaging DevOps principles and SRE practices as a product**.

### Platform Team Roles and Structure

**Key Roles:**

| Role | Responsibility |
|------|---------------|
| **Platform Product Manager** | Analyze developer needs, manage IDP roadmap, define success metrics |
| **Platform Engineer** | Build core IDP infrastructure, Kubernetes/cloud automation |
| **Platform SRE** | Reliability of the platform itself, monitoring, incident response |
| **Developer Experience (DX) Engineer** | CLI tools, documentation, onboarding workflows |

---

## 2. AWS CAF Platform Perspective

### Introduction to AWS Cloud Adoption Framework

The [AWS Cloud Adoption Framework (CAF)](https://docs.aws.amazon.com/prescriptive-guidance/latest/aws-caf-platform-perspective/platform-eng.html) provides organizational guidelines for cloud adoption. The **Platform Perspective** covers three key areas:

1. **Platform Engineering** -- The focus of this section
2. **Platform Architecture** -- Cloud architecture design principles
3. **Data Architecture** -- Data management and analytics strategy

### Maturity Model: START → ADVANCE → EXCEL

AWS CAF defines cloud platform maturity in three stages. Let's examine how Kubernetes ecosystem tools map to each stage.

#### START: Foundation Building

The stage of establishing foundational infrastructure and setting up security guardrails.

| Capability | Description | Kubernetes Ecosystem Mapping |
|-----------|-------------|------------------------------|
| **Landing Zone & Guardrails** | Multi-account environment, preventive/detective controls | EKS cluster configuration, [OPA Gatekeeper](../security/09-opa-gatekeeper.md) / [Kyverno](../security/01-kyverno-policy-management.md) |
| **Authentication** | Centralized identity management, IdP integration | [K8s Authentication & Authorization](../security/02-kubernetes-auth-authz.md), OIDC, IRSA |
| **Networking** | Centralized network management | VPC CNI, [Calico](../networking/03-calico.md), [Cilium](../networking/01-cilium.md) |
| **Logging** | Cross-account observability | [Prometheus](../observability/metrics/01-prometheus.md), [Loki](../observability/logging/01-loki.md), [OpenTelemetry](../observability/tracing/03-opentelemetry.md) |
| **Controls** | Programmatic security controls | [Pod Security Standards](../security/03-pod-security-standards.md), [Network Policies](../security/04-network-policies.md) |
| **Cost Management** | Tagging strategy, cost allocation | Resource Quotas, LimitRange, [EKS Cost Optimization](../eks/07-eks-cost-optimization.md) |

#### ADVANCE: Operational Scaling

The stage of expanding automation and building centralized observability.

| Capability | Description | Kubernetes Ecosystem Mapping |
|-----------|-------------|------------------------------|
| **Infrastructure Automation** | IaC, self-service products | [ACK](./02-ack.md), [KRO](./03-kro.md), Crossplane, [Helm](./01-helm.md) |
| **Central Observability** | Log/metric/trace correlation | [Grafana](../observability/grafana/README.md) Stack, [CloudWatch](../observability/metrics/04-cloudwatch-metrics.md) |
| **Systems Management** | Image standardization, patch management | [Image Security](../security/07-image-security.md), [Kyverno](../security/01-kyverno-policy-management.md) |
| **Credential Management** | Temporary credentials, automatic rotation | [Secrets Management](../security/05-secrets-management.md), IRSA |
| **Security Tooling** | XDR, granular monitoring | [Runtime Security](../security/08-runtime-security.md), Trivy, GuardDuty |

#### EXCEL: Continuous Optimization

The stage of achieving automated governance and continuous improvement.

| Capability | Description | Kubernetes Ecosystem Mapping |
|-----------|-------------|------------------------------|
| **Automated Identity Management** | Version-controlled roles/policies via IaC | [GitOps](../gitops/README.md)-based RBAC management |
| **Anomaly Detection** | Proactive vulnerability assessment, anomaly pattern detection | [Runtime Security](../security/08-runtime-security.md) (Falco), audit log analysis |
| **Threat Analysis** | Continuous monitoring against industry benchmarks | CIS Benchmark, kube-bench |
| **Permission Refinement** | Automated least privilege principle | K8s audit log-based RBAC optimization |
| **Platform Metrics** | Metrics aligned with organizational goals | DORA metrics, SLI/SLO |

---

## 3. IDP Reference Architecture

### Kubernetes-Based IDP Layer Structure

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

### Role and Tool Mapping for Each Layer

| Layer | Role | Key Tools | Repo Docs |
|-------|------|-----------|-----------|
| **Developer Interface** | UI/CLI that developers interact with | Backstage, Port, Argo Workflows UI | - |
| **Integration/Orchestration** | Declarative state management, deployment automation | ArgoCD, FluxCD, KRO | [GitOps](../gitops/README.md), [KRO](./03-kro.md) |
| **Resource** | Abstraction of cloud/K8s resources | ACK, Helm, Operators | [ACK](./02-ack.md), [Helm](./01-helm.md), [K8s Extensions](./04-kubernetes-extensions.md) |
| **Infrastructure** | Actual compute/network/storage | EKS, VPC, IAM | [EKS](../eks/01-eks-introduction.md) |

### Self-Service Catalog Pattern (KRO RGD + ACK)

Combining [KRO](./03-kro.md)'s ResourceGraphDefinition (RGD) with [ACK](./02-ack.md) enables a powerful self-service pattern:

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

From this single manifest, KRO internally creates:
1. **Deployment + Service** (Kubernetes native)
2. **RDS Instance** (AWS resource via ACK)
3. **IAM Role** (Permission setup via ACK)

For detailed examples, see [ExampleCorp Integration Example](./05-example-corp-app.md).

### Golden Path Concept

A Golden Path is the **recommended deployment path** provided by the platform team:

- **Purpose**: Guide developers to get started quickly using validated methods
- **Characteristics**: Recommended, not enforced -- developers can deviate when needed, but it's the optimal choice in most cases
- **Examples**:
  - "New Microservice Deployment" Golden Path: Helm Chart template → ArgoCD integration → Automatic Prometheus metrics collection
  - "Database Provisioning" Golden Path: KRO RGD manifest → RDS creation via ACK → Automatic Secret injection

---

## 4. Platform Engineering Tool Ecosystem

This section maps where the tools covered in this repository fit within the platform engineering landscape.

| Category | Tools | Repo Doc Link |
|----------|-------|---------------|
| **Package Management** | Helm, Kustomize | [Helm](./01-helm.md) |
| **AWS IaC** | ACK, CloudFormation | [ACK](./02-ack.md) |
| **Resource Orchestration** | KRO, Crossplane | [KRO](./03-kro.md) |
| **Extension Mechanisms** | CRD, Operators | [Kubernetes Extension Mechanisms](./04-kubernetes-extensions.md) |
| **GitOps** | ArgoCD, FluxCD | [GitOps Section](../gitops/README.md) |
| **Policy/Governance** | Kyverno, OPA Gatekeeper | [Kyverno](../security/01-kyverno-policy-management.md), [OPA Gatekeeper](../security/09-opa-gatekeeper.md) |
| **Observability** | Prometheus, Grafana, OTel | [Observability Section](../observability/README.md) |
| **Autoscaling** | KEDA, Karpenter | [KEDA](../autoscaling/01-keda.md), [Karpenter](../autoscaling/02-karpenter.md) |
| **Service Mesh** | Istio, Cilium | [Istio](../service-mesh/istio/README.md), [Cilium Service Mesh](../service-mesh/cilium-service-mesh/README.md) |
| **Security** | Falco, Trivy, PSS | [Runtime Security](../security/08-runtime-security.md), [Image Security](../security/07-image-security.md), [PSS](../security/03-pod-security-standards.md) |

---

## 5. Platform Maturity Self-Assessment Checklist

Assess your organization's platform engineering maturity. Each item links to the relevant document in this repository.

### START Stage

| Check | Item | Related Docs |
|-------|------|-------------|
| [ ] | Are EKS clusters created in a standardized manner? | [EKS Cluster Creation](../eks/02-eks-cluster-creation-part1.md) |
| [ ] | Are RBAC policies defined and enforced? | [Authentication & Authorization](../security/02-kubernetes-auth-authz.md) |
| [ ] | Are network policies applied? | [Network Policies](../security/04-network-policies.md) |
| [ ] | Is basic monitoring and logging configured? | [EKS Monitoring](../eks/06-eks-monitoring-logging.md) |
| [ ] | Are Pod Security Standards applied? | [PSS](../security/03-pod-security-standards.md) |
| [ ] | Are resource quotas and limits set? | [EKS Cost Optimization](../eks/07-eks-cost-optimization.md) |

### ADVANCE Stage

| Check | Item | Related Docs |
|-------|------|-------------|
| [ ] | Is infrastructure managed with IaC? (ACK, Terraform, etc.) | [ACK](./02-ack.md) |
| [ ] | Is a GitOps workflow in place? | [GitOps](../gitops/README.md) |
| [ ] | Is a centralized observability stack operational? | [Observability](../observability/README.md) |
| [ ] | Is governance automated with a policy engine? | [Kyverno](../security/01-kyverno-policy-management.md) |
| [ ] | Are secrets automatically managed from an external store? | [Secrets Management](../security/05-secrets-management.md) |
| [ ] | Is container image scanning automated? | [Image Security](../security/07-image-security.md) |

### EXCEL Stage

| Check | Item | Related Docs |
|-------|------|-------------|
| [ ] | Is a self-service catalog provided to developers? | [KRO](./03-kro.md), [ExampleCorp](./05-example-corp-app.md) |
| [ ] | Are DORA metrics measured and improved? | - |
| [ ] | Is runtime security monitoring operational? | [Runtime Security](../security/08-runtime-security.md) |
| [ ] | Is autoscaling optimized for workloads? | [KEDA](../autoscaling/01-keda.md), [Karpenter](../autoscaling/02-karpenter.md) |
| [ ] | Are platform SLOs defined and tracked? | [Observability Analysis](../ops/08-observability-analysis.md) |
| [ ] | Are Golden Paths defined and documented? | This document (Section 3) |

---

## 6. References

- [AWS CAF Platform Perspective - Platform Engineering](https://docs.aws.amazon.com/prescriptive-guidance/latest/aws-caf-platform-perspective/platform-eng.html)
- [CNCF Platform White Paper](https://tag-app-delivery.cncf.io/whitepapers/platforms/)
- [Platform Engineering on Kubernetes (O'Reilly)](https://www.oreilly.com/library/view/platform-engineering-on/9781617299322/)
- [Backstage.io - Open Source IDP Framework](https://backstage.io/)
- [Internal Developer Platform](https://internaldeveloperplatform.org/)
