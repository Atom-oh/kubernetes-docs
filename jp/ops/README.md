# 運用ガイド

> **最終更新日**: 2026年9月12日

このセクションでは、EKS Auto Mode 環境の本番運用ガイドを提供します。Terraform によるインフラのプロビジョニング、CI/CD パイプライン、GitOps によるデプロイ、スケーリング、オブザーバビリティ、リソース最適化、アップグレードを扱います。

---

## 対象読者

- **プラットフォームエンジニア**: EKS Auto Mode の本番環境を構築する方
- **インフラエンジニア**: Terraform／Terragrunt ベースの IaC を運用する方
- **DevOps エンジニア**: GitLab CI と ArgoCD で CI/CD パイプラインを構築する方
- **SRE**: Prometheus、Grafana、Loki のオブザーバビリティスタックを運用する方

---

## 前提条件

この運用ガイドを始める前に、以下の知識や経験があることを確認してください。

- [EKS Auto Mode の開始方法](../eks-auto-mode/01-getting-started.md)
- Terraform の基礎 (リソース、モジュール、state 管理)
- [Kubernetes の基本概念](../core/01-cluster-architecture.md)
- kubectl と Helm CLI の使用経験

---

## 目次

| # | ドキュメント | 主なトピック |
|---|----------|------------|
| 01 | [Terraform の 3 層インフラ設定](./01-infrastructure-setup.md) | VPC、EKS Auto Mode、3 層 Terraform による Pod Identity |
| 02 | [NLB の重み付けルーティングと Blue/Green](./02-infrastructure-advanced.md) | デュアルクラスター構成、NLB の重み、DNS ルーティング |
| 03 | [CI パイプライン](./03-ci-pipelines.md) | ECR、GitLab Runner、GitHub ARC、マルチプラットフォームビルド |
| 04 | [ArgoCD のマルチクラスター運用](./04-gitops-multi-cluster.md) | ハブ・スポーク、ApplicationSet、IAM Identity Center SSO |
| 05 | [GitOps の自動化](./05-gitops-automation.md) | Atlantis、FluxCD、Terraform Cloud、AIOps |
| 06 | [スケーリング戦略](./06-scaling-strategies.md) | HPA カスタムメトリクス、KEDA、VPA、Spot の活用 |
| 07 | [運用アラートの設定](./07-observability-alerts.md) | ネットワーク／CPU／ディスク／Auto Mode ノード終了のアラート |
| 08 | [オブザーバビリティ分析](./08-observability-analysis.md) | ログ／メトリクス／トレースの相関、PromQL、LogQL、TraceQL |
| 09 | [オブザーバビリティスタックの運用](./09-observability-stack.md) | Loki、Tempo、Prometheus／AMP の導入と運用 |
| 10 | [リソース最適化](./10-resource-optimization.md) | Requests／Limits、JVM 調整、フレームワーク別ガイド |
| 11 | [EKS のアップグレード](./11-upgrade-operations.md) | 段階的な Auto Mode アップグレード、Blue/Green 戦略 |
| 12 | [イベント時のキャパシティ計画](./12-event-capacity-planning.md) | トラフィックイベント、キャパシティと復旧の計画 |
| 13 | [FinOps コスト管理](./13-finops-cost-platform.md) | コストの可視化、配賦、最適化 |
| 14 | [Tekton パイプライン](./14-tekton-pipelines.md) | Kubernetes ネイティブ CI パイプライン |
| 15 | [ゾーン別クラスター運用](./15-zonal-operations-guide.md) | LB の重み切り替えと TargetGroupBinding、ネイティブロールバック、Kafka／Redis／Aurora の AZ 固定読み取り |
| 16 | [トラブルシューティング手順書](./16-troubleshooting-playbook.md) | 症状から診断、原因、修正まで: Pending／ImagePull／CrashLoop／NotReady／PVC、IRSA、VPC CNI、Karpenter、kubectl チートシート |
| 17 | [EKS Spot の本番実験](./17-spot-production-experiments.md) | 中断、並行する回収、フォールバック、結果記録、SLO／コスト評価、ロールバック |

---

## 学習パス

### 推奨順序

1. **インフラストラクチャ** (01–02): Terraform で VPC／EKS をプロビジョニングする
2. **CI/CD** (03–05): パイプラインと GitOps によるデプロイを構築する
3. **スケーリング** (06): ワークロードのスケーリング戦略を確立する
4. **オブザーバビリティ** (07–09): 監視、アラート、分析の仕組みを構築する
5. **最適化** (10): リソース効率とコストを最適化する
6. **アップグレード** (11): 可用性と復旧手順を検証する
7. **専門的な運用** (12–16): キャパシティイベント、FinOps、Tekton、ゾーン別運用、トラブルシューティング

### ロール別

| ロール | 優先して読むドキュメント |
|------|-------------------|
| プラットフォームエンジニア | 01, 02, 04, 11 |
| DevOps エンジニア | 03, 04, 05 |
| SRE | 06, 07, 08, 09, 10 |
| インフラエンジニア | 01, 02, 11 |

---

## 既存ドキュメントとの関係

この運用ガイドは、概念ドキュメントを実践的でコードを中心とした手順で補完します。

### 概念ドキュメント

- [EKS Auto Mode](../eks-auto-mode/README.md) - アーキテクチャと概念
- [ArgoCD](../gitops/argocd/README.md) - GitOps の基礎
- [KEDA](../autoscaling/01-keda.md) - イベント駆動型オートスケーリングの概念
- [Karpenter](../autoscaling/02-karpenter.md) - ノードプロビジョニングの概念

### この運用ガイド

- 本番インフラ向け Terraform HCL コード
- Kubernetes リソースの YAML マニフェスト
- オブザーバビリティ用 PromQL／LogQL クエリ
- 運用自動化用 Bash スクリプト
- 検証手順を含む段階的な手順

---

## クイックリファレンス

### よくある運用作業

| 作業 | ドキュメント | セクション |
|------|----------|---------|
| 新しい EKS クラスターを作成する | [01-infrastructure-setup](./01-infrastructure-setup.md) | 3 層 Terraform |
| ArgoCD にアプリケーションを追加する | [04-gitops-multi-cluster](./04-gitops-multi-cluster.md) | ApplicationSet |
| カスタムメトリクスで HPA を設定する | [06-scaling-strategies](./06-scaling-strategies.md) | カスタムメトリクス |
| 新しいサービスのアラートを設定する | [07-observability-alerts](./07-observability-alerts.md) | アラートルール |
| EKS バージョンをアップグレードする | [11-upgrade-operations](./11-upgrade-operations.md) | Auto Mode のアップグレード |

### 緊急時の手順

| 状況 | ドキュメント | セクション |
|----------|----------|---------|
| デプロイをロールバックする | [04-gitops-multi-cluster](./04-gitops-multi-cluster.md) | ロールバック |
| EKS アップグレードをロールバックする | [11-upgrade-operations](./11-upgrade-operations.md) | ネイティブロールバックの適用条件または Blue/Green の切り戻し |
| 需要と可用性を確認してキャパシティを調整する | [06-scaling-strategies](./06-scaling-strategies.md) | キャパシティとスケーリングポリシー |
| Pod の障害をデバッグする | [16-troubleshooting-playbook](./16-troubleshooting-playbook.md) | 症状に基づく診断 |

---

## コントリビューション

新しい運用手順を追加するときは、次の点を守ってください。

1. 実用的なコード例 (Terraform、YAML、bash) を含める
2. 各手順に検証方法を示す
3. 該当する場合はロールバック手順を記載する
4. 監視用の関連 PromQL／LogQL クエリを追加する
5. 関連する概念ドキュメントへのリンクを追加する
