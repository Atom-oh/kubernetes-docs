# Operations Guide

> **Last Updated**: June 2025

This section provides a production operations guide for EKS Auto Mode environments. It covers infrastructure provisioning with Terraform, CI/CD pipelines, GitOps-based deployment, scaling, observability, resource optimization, and upgrades.

---

## Target Audience

- **Platform Engineers** building production environments with EKS Auto Mode
- **Infrastructure Engineers** operating Terraform/Terragrunt-based IaC
- **DevOps Engineers** building CI/CD pipelines with GitLab CI and ArgoCD
- **SREs** operating Prometheus, Grafana, and Loki observability stacks

---

## Prerequisites

Before starting this operations guide, ensure familiarity with:

- [Getting Started with EKS Auto Mode](../eks-auto-mode/01-getting-started.md)
- Terraform basics (resources, modules, state management)
- [Kubernetes Core Concepts](../core/01-cluster-architecture.md)
- kubectl and Helm CLI experience

---

## Table of Contents

| # | Document | Key Topics |
|---|----------|------------|
| 01 | [Terraform 3-Layer Infrastructure Setup](./01-infrastructure-setup.md) | VPC, EKS Auto Mode, Pod Identity with 3-Layer Terraform |
| 02 | [NLB Weighted Routing and Blue/Green](./02-infrastructure-advanced.md) | Dual cluster architecture, NLB weights, DNS routing |
| 03 | [CI Pipelines](./03-ci-pipelines.md) | ECR, GitLab Runner, GitHub ARC, multi-platform builds |
| 04 | [ArgoCD Multi-Cluster](./04-gitops-multi-cluster.md) | Hub-spoke, ApplicationSet, IAM Identity Center SSO |
| 05 | [GitOps Automation](./05-gitops-automation.md) | Atlantis, FluxCD, Terraform Cloud, AIOps |
| 06 | [Scaling Strategies](./06-scaling-strategies.md) | HPA custom metrics, KEDA, VPA, Spot utilization |
| 07 | [Operational Alert Configuration](./07-observability-alerts.md) | Network/CPU/Disk/Auto Mode node termination alerts |
| 08 | [Observability Analysis](./08-observability-analysis.md) | Logs/Metrics/Traces correlation, PromQL, LogQL, TraceQL |
| 09 | [Observability Stack Operations](./09-observability-stack.md) | Loki, Tempo, Prometheus/AMP installation and operations |
| 10 | [Resource Optimization](./10-resource-optimization.md) | Requests/Limits, JVM tuning, framework-specific guide |
| 11 | [EKS Upgrades](./11-upgrade-operations.md) | Auto Mode zero-downtime upgrade, blue/green strategy |

---

## Learning Path

### Recommended Order

1. **Infrastructure** (01-02): Provision VPC/EKS with Terraform
2. **CI/CD** (03-05): Build pipelines and GitOps deployment
3. **Scaling** (06): Establish scaling strategies for workloads
4. **Observability** (07-09): Build monitoring, alerting, and analysis systems
5. **Optimization** (10): Resource efficiency and cost optimization
6. **Upgrades** (11): Establish zero-downtime upgrade procedures

### By Role

| Role | Priority Documents |
|------|-------------------|
| Platform Engineer | 01, 02, 04, 11 |
| DevOps Engineer | 03, 04, 05 |
| SRE | 06, 07, 08, 09, 10 |
| Infrastructure Engineer | 01, 02, 11 |

---

## Relationship with Existing Documentation

This operations guide complements existing concept documentation with practical, code-focused guides:

### Concept Documentation
- [EKS Auto Mode](../eks-auto-mode/README.md) - Architecture and concepts
- [ArgoCD](../gitops/01-argocd.md) - GitOps fundamentals
- [KEDA](../autoscaling/01-keda.md) - Event-driven autoscaling concepts
- [Karpenter](../autoscaling/02-karpenter.md) - Node provisioning concepts

### This Operations Guide
- Terraform HCL code for production infrastructure
- YAML manifests for Kubernetes resources
- PromQL/LogQL queries for observability
- Bash scripts for operational automation
- Step-by-step procedures with validation

---

## Quick Reference

### Common Operations

| Task | Document | Section |
|------|----------|---------|
| Create new EKS cluster | [01-infrastructure-setup](./01-infrastructure-setup.md) | 3-Layer Terraform |
| Add new application to ArgoCD | [04-gitops-multi-cluster](./04-gitops-multi-cluster.md) | ApplicationSet |
| Configure HPA with custom metrics | [06-scaling-strategies](./06-scaling-strategies.md) | Custom Metrics |
| Set up alerting for new service | [07-observability-alerts](./07-observability-alerts.md) | Alert Rules |
| Upgrade EKS version | [11-upgrade-operations](./11-upgrade-operations.md) | Auto Mode Upgrade |

### Emergency Procedures

| Scenario | Document | Section |
|----------|----------|---------|
| Rollback deployment | [04-gitops-multi-cluster](./04-gitops-multi-cluster.md) | Rollback |
| Rollback EKS upgrade | [11-upgrade-operations](./11-upgrade-operations.md) | Blue/Green Rollback |
| Scale down for cost | [06-scaling-strategies](./06-scaling-strategies.md) | Emergency Scale |
| Debug failing pods | [08-observability-analysis](./08-observability-analysis.md) | Log Analysis |

---

## Contributing

When adding new operational procedures:

1. Include practical code examples (Terraform, YAML, bash)
2. Provide validation steps for each procedure
3. Document rollback procedures where applicable
4. Add relevant PromQL/LogQL queries for monitoring
5. Cross-reference related concept documentation
