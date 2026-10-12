# EKS 上の MLflow 詳細解説

> **レビュー基準**: MLflow 3.16.0
> **確認した最新パッチ**: MLflow 3.16.1（2026年9月17日）
> **レビューしたドキュメント**: 2026年10月12日

## 概要

MLflow は、実験の追跡、モデルのログ記録と登録、バージョン管理、GenAI 評価、トレーシングを提供します。トレーシングは 2.14.0 で導入され、3.x では LoggedModel、評価、UI 統合が拡張されました。バージョン 3.16.0 は 2026-09-04 にリリースされました。

パッチ 3.16.1 は 2026-09-17 に続いてリリースされ、同梱されていたデフォルトの basic-auth 管理者パスワードが削除されました。以下の例は 3.16.0 で確認したものであり、3.16.1 では再実行していません。MLflow 3.17.0（2026-10-07）は後続のマイナーリリースであり、SQL ベースのサーバーでは連携した SQL スキーマアップグレードが必要です。このシリーズでは扱いません。

SDK と SQLite を使ってローカルで利用することも、SQL メタデータストアとアーティファクトストアを分離した HTTP Tracking サービスを運用することもできます。論理的なサービスは、単一の Pod やストレージシステムである必要はありません。このシリーズでは Tracking、Registry、EKS デプロイを扱います。すべての MLflow 機能や GPU トレーニングの成功を検証するものではありません。

## コンポーネントマップ

| 概念 | 解決する課題 | 詳細解説 |
|---------|--------------------|-----------|
| **Tracking** | 実験のパラメータ、メトリクス、アーティファクト、モデル、GenAI トレースをログ記録・照会する | [パート 1](01-tracking.md) |
| **Model Registry** | いずれか1つのトレーニング実行から独立した、安定してバージョン管理されるモデル ID を付与する | [パート 2](02-model-registry.md) |
| **EKS Deployment** | EKS で Tracking サーバー、バックエンドストア、アーティファクトストアを実行する | [パート 3](03-eks-deployment.md) |

![MLflow Tracking（実験、実行、トレース）が Model Registry（登録済みモデル、エイリアス）に流れ、さらにこのドキュメントシリーズの対象外である Serving ステージによって解決される、3 段階のパイプライン図。](../../.gitbook/assets/en-ai-ml-mlflow-readme-0.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-mlflow-readme-0.html)

## EKS でこれを実行する理由

トレードオフは、このドキュメントサイトのデータ/ML セクションで別途扱っているものと同じです。すでに EKS を運用しているチームは、マネージド型の代替手段を使用する代わりに Tracking サーバー、バックエンドデータベース、アーティファクトストアを直接運用することになりますが、クラスター上の他のすべてと同様に、MLflow の Tracking サーバーに同じデプロイ、IAM（IRSA/Pod Identity）、オブザーバビリティのパターンを再利用できます。

[SageMaker AI ガイドブック](../sagemaker-ai/README.md)では、Qwen の比較設計を説明しています。この例には個別の過去バージョン固定があり、その DLC はパッチ提供終了に達したため、現在は GPU 実行がブロックされています。このシリーズでの MLflow 3.16.0 のローカル確認は、その例のエンドツーエンド検証ではありません。

Model Registry の登録は、任意のライフサイクルステップです。Serving システムは、個別の設定を通じてモデル URI またはエイリアスを使用します。登録またはエイリアスの変更によって、モデルが自動的にデプロイされることはありません。

## 現在対象としている内容

1. [パート 1: MLflow Tracking](01-tracking.md) — 実験、実行、autologging、MLflow 3 の `LoggedModel` への移行、GenAI トレーシング
2. [パート 2: MLflow Model Registry](02-model-registry.md) — Registered Models、Model Versions、エイリアス、リネージ
3. [パート 3: EKS への MLflow のデプロイ](03-eks-deployment.md) — Tracking サーバー、PostgreSQL バックエンドストア、S3 アーティファクトストア、IAM アクセス

## 主要な情報源

- [MLflow 3.16.1 リリース](https://github.com/mlflow/mlflow/releases/tag/v3.16.1)
- [MLflow 3.16.0 レビュー基準](https://github.com/mlflow/mlflow/releases/tag/v3.16.0)
- [MLflow 2.14.0 で導入されたトレーシング](https://github.com/mlflow/mlflow/releases/tag/v2.14.0)
- [バックエンドストア](https://mlflow.org/docs/3.16.0/self-hosting/architecture/backend-store/)
