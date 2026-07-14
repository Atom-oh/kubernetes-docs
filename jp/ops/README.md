# 運用ガイド

> **最終更新**: February 23, 2026

このセクションでは、EKS Auto Mode 環境向けの production operations guide（本番運用ガイド）を提供します。Terraform による infrastructure provisioning、CI/CD pipelines、GitOps ベースのデプロイ、scaling、observability、resource optimization、upgrades を扱います。

---

## 対象読者

- **Platform Engineers** EKS Auto Mode で production environment を構築する方
- **Infrastructure Engineers** Terraform/Terragrunt ベースの IaC を運用する方
- **DevOps Engineers** GitLab CI と ArgoCD で CI/CD pipelines を構築する方
- **SREs** Prometheus、Grafana、Loki observability stacks を運用する方

---

## 前提条件

この運用ガイドを開始する前に、以下に習熟していることを確認してください。

- [EKS Auto Mode の開始方法](../eks-auto-mode/01-getting-started.md)
- Terraform の基礎（resources、modules、state management）
- [Kubernetes Core Concepts](../core/01-cluster-architecture.md)
- kubectl と Helm CLI の経験

---

## 目次

| # | Document | Key Topics |
|---|----------|------------|
| 01 | [Terraform 3-Layer Infrastructure Setup](./01-infrastructure-setup.md) | VPC、EKS Auto Mode、3-Layer Terraform による Pod Identity |
| 02 | [NLB Weighted Routing and Blue/Green](./02-infrastructure-advanced.md) | Dual cluster architecture、NLB weights、DNS routing |
| 03 | [CI Pipelines](./03-ci-pipelines.md) | ECR、GitLab Runner、GitHub ARC、multi-platform builds |
| 04 | [ArgoCD Multi-Cluster](./04-gitops-multi-cluster.md) | Hub-spoke、ApplicationSet、IAM Identity Center SSO |
| 05 | [GitOps Automation](./05-gitops-automation.md) | Atlantis、FluxCD、Terraform Cloud、AIOps |
| 06 | [Scaling Strategies](./06-scaling-strategies.md) | HPA custom metrics、KEDA、VPA、Spot utilization |
| 07 | [Operational Alert Configuration](./07-observability-alerts.md) | Network/CPU/Disk/Auto Mode node termination alerts |
| 08 | [Observability Analysis](./08-observability-analysis.md) | Logs/Metrics/Traces correlation、PromQL、LogQL、TraceQL |
| 09 | [Observability Stack Operations](./09-observability-stack.md) | Loki、Tempo、Prometheus/AMP installation and operations |
| 10 | [Resource Optimization](./10-resource-optimization.md) | Requests/Limits、JVM tuning、framework-specific guide |
| 11 | [EKS Upgrades](./11-upgrade-operations.md) | Auto Mode zero-downtime upgrade、blue/green strategy |

---

## 学習パス

### 推奨順序

1. **Infrastructure** (01-02): Terraform で VPC/EKS をプロビジョニングする
2. **CI/CD** (03-05): Pipelines と GitOps deployment を構築する
3. **Scaling** (06): Workloads 向けの scaling strategies を確立する
4. **Observability** (07-09): Monitoring、alerting、analysis systems を構築する
5. **Optimization** (10): Resource efficiency と cost optimization
6. **Upgrades** (11): Zero-downtime upgrade procedures を確立する

### ロール別

| Role | Priority Documents |
|------|-------------------|
| Platform Engineer | 01, 02, 04, 11 |
| DevOps Engineer | 03, 04, 05 |
| SRE | 06, 07, 08, 09, 10 |
| Infrastructure Engineer | 01, 02, 11 |

---

## 既存ドキュメントとの関係

この運用ガイドは、既存の concept documentation を、実践的で code-focused なガイドで補完します。

### Concept Documentation
- [EKS Auto Mode](../eks-auto-mode/README.md) - Architecture and concepts
- [ArgoCD](../gitops/argocd/README.md) - GitOps fundamentals
- [KEDA](../autoscaling/01-keda.md) - Event-driven autoscaling concepts
- [Karpenter](../autoscaling/02-karpenter.md) - Node provisioning concepts

### この運用ガイド
- Production infrastructure 向けの Terraform HCL code
- Kubernetes resources 向けの YAML manifests
- Observability 向けの PromQL/LogQL queries
- Operational automation 向けの Bash scripts
- Validation を含む step-by-step procedures

---

## クイックリファレンス

### 一般的な運用

| Task | Document | Section |
|------|----------|---------|
| 新しい EKS cluster を作成 | [01-infrastructure-setup](./01-infrastructure-setup.md) | 3-Layer Terraform |
| ArgoCD に新しい application を追加 | [04-gitops-multi-cluster](./04-gitops-multi-cluster.md) | ApplicationSet |
| Custom metrics で HPA を設定 | [06-scaling-strategies](./06-scaling-strategies.md) | Custom Metrics |
| 新しい service 向けに alerting を設定 | [07-observability-alerts](./07-observability-alerts.md) | Alert Rules |
| EKS version をアップグレード | [11-upgrade-operations](./11-upgrade-operations.md) | Auto Mode Upgrade |

### 緊急時手順

| Scenario | Document | Section |
|----------|----------|---------|
| Deployment をロールバック | [04-gitops-multi-cluster](./04-gitops-multi-cluster.md) | Rollback |
| EKS upgrade をロールバック | [11-upgrade-operations](./11-upgrade-operations.md) | Blue/Green Rollback |
| Cost 削減のために scale down | [06-scaling-strategies](./06-scaling-strategies.md) | Emergency Scale |
| 失敗している pods をデバッグ | [08-observability-analysis](./08-observability-analysis.md) | Log Analysis |

---

## コントリビュート

新しい operational procedures を追加する場合:

1. 実践的な code examples（Terraform、YAML、bash）を含める
2. 各 procedure に validation steps を提供する
3. 該当する場合は rollback procedures を文書化する
4. Monitoring 向けの関連する PromQL/LogQL queries を追加する
5. 関連する concept documentation を cross-reference する
