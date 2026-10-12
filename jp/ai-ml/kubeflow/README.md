# EKS 上の Kubeflow 詳細解説

> **レビュー基準**: Kubeflow Community Distribution 26.03.1
> **確認済みの最新ディストリビューション**: Community Distribution 26.03.1。コンポーネントのリリースは個別に追跡
> **最終確認**: October 12, 2026

## 概要

Kubeflow は、ML パイプライン、ノートブック、チューニング、トレーニング、サービングのための Kubernetes ベースのツールを提供します。Community Distribution は、コンポーネントのリビジョン、共有サービス、ダッシュボードをまとめています。個々のプロジェクトにもそれぞれのリリースとインストール要件があります。

このシリーズでは、ディストリビューションの KFP 2.16.1 と KServe 0.18.0 を再現の基準として使用します。

KFP 2.17.2 と KServe 0.21.0 は、後発の独立したリリースです。これらは Community Distribution 26.03.1 にはバンドルされておらず、このガイドでは両者の互換性を保証していません。ディストリビューションで固定されたインベントリを、最新のコンポーネントリリースと併せて確認してください。

CNCF は[2026 年 8 月 17 日に Kubeflow の卒業を発表しました](https://www.cncf.io/announcements/2026/08/17/cncf-announces-kubeflows-graduation-solidifying-the-standard-for-cloud-native-ai-operations/)。これは、独立したセキュリティ監査を含むプロジェクトの成熟度とガバナンスを認めるものです。特定の EKS デプロイメントのセキュリティまたは規制準拠を認定するものではありません。

## コンポーネントマップ

| コンポーネント | 目的 | API または概念 | ガイド |
| --- | --- | --- | --- |
| Dashboard、Profiles、アクセス管理 | UI ナビゲーション、Namespace の所有権とメンバーシップ | Cluster スコープの `Profile`、任意のクォータ | [パート 1](01-architecture-installation.md) |
| Pipelines | ワークフローのコンパイルと実行、実行とアーティファクトの追跡 | Pipeline/Run/Experiment API、任意の Kubernetes Native API モードにより `Pipeline`/`PipelineVersion` CRD を追加 | [パート 2](02-pipelines.md) |
| Notebooks | ユーザーノートブックのワークロード | `Notebook`、イメージと PVC の構成 | [パート 3](03-notebooks.md) |
| Katib | ハイパーパラメータ検索とトライアル | `Experiment`、`Trial`、`Suggestion` CRD | [パート 4](04-katib.md) |
| Trainer | 構成されたランタイムによる分散トレーニング | `TrainJob`、`TrainingRuntime`、`ClusterTrainingRuntime` | [パート 5](05-training-operator.md) |
| KServe | モデル推論サービス | `InferenceService`、モード固有の依存関係 | [パート 6](06-kserve.md) |

このマップはガイドの対象範囲を示すものであり、ディストリビューション全体を網羅するものではありません。リリース 26.03.1 には Hub/モデルレジストリおよび Spark Operator も含まれます。KFP Experiment は Katib の Experiment CRD とは異なります。

![ダッシュボードのナビゲーションを、明示的に構成されたパイプライン、チューニング、トレーニング、モデルデプロイメントの統合から分離して示す Kubeflow コンポーネントマップ。](../../.gitbook/assets/en-ai-ml-kubeflow-readme-0.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-kubeflow-readme-0.html)

ダッシュボードはコンポーネントの UI にリンクします。Pipelines と Katib が Trainer を使用するのは、その実装がサポート対象のトレーニングリソースを明示的に送信する場合のみです。トレーニング済みアーティファクトを KServe に接続するには別途デプロイ手順が必要です。この図はモデルの自動プロモーションを意味するものではありません。

## これを EKS で実行する理由

既存の EKS プラットフォームでは、容量管理、ストレージ統合、ワークロードアイデンティティ、モニタリングを ML ワークロードと共有できます。それでも互換性は、Kubernetes のバージョン、CPU アーキテクチャ、イメージ、ネットワーキング、ストレージドライバー、認証に依存します。Kubernetes 準拠だけでは不十分です。リリースドキュメントでは ARM64 イメージのカバレッジが不完全であることが示されています。

チームは引き続き、コンポーネント/CRD のアップグレード、テナントの認可、永続データ、認証情報、リカバリに責任を負います。[Amazon SageMaker AI](../sagemaker-ai/README.md) は一部のインフラストラクチャ責任を軽減しますが、データアクセス、アプリケーションの正確性、モデル品質、コスト管理には依然として担当者が必要です。必要なインターフェイス、運用能力、ワークロードの制約に基づいて選択してください。

## 現在カバーしている内容

1. [パート 1: EKS 上のアーキテクチャとインストール](01-architecture-installation.md) — 現在のコミュニティリリース、レガシー AWS ディストリビューションの制約、Profiles、アイデンティティ、マニフェストのレンダリング。
2. [パート 2: Pipelines](02-pipelines.md) — SDK v2、コンパイル、実行、アーティファクトストレージ。
3. [パート 3: Notebooks](03-notebooks.md) — ワークロード、Profiles、ストレージ、GPU 配置。
4. [パート 4: Katib](04-katib.md) — 実験、トライアル、検索、早期停止。
5. [パート 5: Trainer](05-training-operator.md) — レガシー Training Operator と Trainer v2 API。
6. [パート 6: KServe](06-kserve.md) — 推論リソース、デプロイメントモード、ロールアウト。

各章のコンポーネント基準を使用してください。インストールを選択する前に、[26.03.1 リリース](https://github.com/kubeflow/community-distribution/releases/tag/26.03.1)、[固定されたインベントリ](https://github.com/kubeflow/community-distribution/blob/26.03.1/README.md)、[KFP 2.17.2](https://github.com/kubeflow/pipelines/releases/tag/2.17.2)、[KServe 0.21.0](https://github.com/kserve/kserve/releases/tag/v0.21.0) を確認してください。
