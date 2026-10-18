# EKS 上の Ray 詳細ガイド

> **レビュー基準**: Ray 2.58.0、KubeRay v1.7.1
> **最新リリース確認**: Ray 2.59.0（2026年10月2日）、2026年10月16日に確認。例では 2.58.0 を使用
> **ドキュメントレビュー日**: 2026年10月16日

## 概要

Ray は task、actor、ObjectRef、およびノードごとの object store を使って Python の処理を分散します。Train、Tune、Serve はこの基盤を利用しながら、トレーニング、探索、サービングのポリシーを追加します。object store を経由するだけで、あらゆる通信や復旧の課題が自動的に解決するわけではありません。

KubeRay は、RayCluster、RayJob、RayService を調整する Kubernetes operator です。アプリケーションが使う ML ライブラリをディスパッチャーとして選択するものではありません。Ray の処理スケジューリング、Kubernetes Pod の配置、EC2 node のプロビジョニングは、それぞれ別のレイヤーです。

## コンポーネント一覧

| 概念 | 解決する課題 | 詳細ガイド |
|---------|--------------------|-----------|
| **アーキテクチャ** | 他の機能の基盤となる task、actor、object store | [パート1](01-architecture.md) |
| **KubeRay Operator** | Ray cluster をネイティブな Kubernetes リソース（`RayCluster`/`RayJob`/`RayService`）として実行 | [パート2](02-kuberay-operator.md) |
| **Ray Train と Tune** | 分散モデル学習とハイパーパラメーター探索 | [パート3](03-ray-train-tune.md) |
| **Ray Serve** | 専用の LLM サービング構成要素を含むモデルサービング | [パート4](04-ray-serve.md) |

![Train、Tune、Serve などのアプリケーションライブラリは Ray Core の task と actor を使用し、KubeRay は Kubernetes 上の Ray リソースを個別に管理します。](../../.gitbook/assets/en-ai-ml-ray-readme-0.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-ray-readme-0.html)

## EKS 上で実行する理由

トレードオフは、このドキュメントサイトのデータ／ML セクションで扱う他のケースと同じです。すでに EKS を運用しているチームは、マネージドサービスを使わず KubeRay operator と RayCluster／RayJob／RayService リソースを直接運用することで、Ray workload にもクラスター内の他の workload と同じ node-pool 自動スケーリング（Karpenter 経由）、IAM、可観測性のパターンを再利用できます。

基盤を確認するテストは、小規模な単一ノードの Ray 実行です。これは GPU トレーニング、複数ノード障害時の復旧、稼働中の EKS 環境、または自動スケーリングを実証するものではありません。

Ray 2.59.0 では、ローカルクラスターの token 認証がデフォルトで有効になります。`~/.ray/auth_token` が存在しない状態でアドレスを指定せず `ray.init()` を呼び出すと、token が生成されます。`RAY_AUTH_MODE=disabled` を設定すると無効になります。リリースノートでは、2.61 以降にリモートおよび複数ノードのクラスターにもデフォルト設定を拡張する予定とされています。このシリーズの例は 2.58.0 で確認しており、2.59.0 では再実行していません。

## 現在扱っている内容

1. [パート1: Ray アーキテクチャ](01-architecture.md): task、actor、object store、head／worker クラスターモデル
2. [パート2: KubeRay Operator](02-kuberay-operator.md): RayCluster、RayJob、RayService、および Karpenter を使う二層の自動スケーリング構成
3. [パート3: Ray Train と Ray Tune](03-ray-train-tune.md): 分散トレーニングとハイパーパラメーターチューニング
4. [パート4: Ray Serve](04-ray-serve.md): モデルサービング、Ray Serve LLM、RayService を用いた本番デプロイ

## 主な情報源

- [Ray 2.58.0](https://github.com/ray-project/ray/releases/tag/ray-2.58.0)
- [Ray 2.59.0（確認した最新バージョン）](https://github.com/ray-project/ray/releases/tag/ray-2.59.0)
- [KubeRay 1.7.1](https://github.com/ray-project/kuberay/releases/tag/v1.7.1)
