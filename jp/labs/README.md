# ラボガイド


> **最終更新**: September 13, 2026

このセクションでは、Kubernetes および関連技術を実践するためのハンズオンラボガイドを提供します。各ラボには手順ごとの説明と検証方法が含まれており、理論で学んだ内容を実際の環境で確認できます。

## ラボ一覧

| # | ラボ | 難易度 | 前提条件 |
|---|-----|------------|---------------|
| 1 | [Linux 基礎ラボ](basics/01-linux-basics-lab.md) | 初級 | Linux ターミナルへのアクセス |
| 2 | [Linux 応用スキルラボ](basics/02-linux-advanced-lab.md) | 初級 | Linux の基礎を完了済み |
| 3 | [コンテナ技術ラボ](basics/03-container-technology-lab.md) | 初級 | Docker をインストール済み |
| 4 | [Pod とワークロードラボ](core/02-pods-and-workloads-lab.md) | 初級 | kubectl、K8s クラスター |
| 5 | [Service とネットワーキングラボ](core/03-services-networking-lab.md) | 中級 | kubectl、K8s クラスター |
| 6 | [ストレージラボ](core/04-storage-lab.md) | 中級 | kubectl、K8s クラスター |
| 7 | [ConfigMap と Secret ラボ](core/05-configuration-secrets-lab.md) | 初級 | kubectl、K8s クラスター |
| 8 | [EKS クラスター作成ラボ](eks/01-eks-cluster-creation-lab.md) | 中級 | AWS CLI、eksctl |
| 9 | [Observability E2E: シリーズ紹介](observability/README.md) | 上級 | 承認済みの AWS 環境、Helm、Python |
| 10 | [Observability E2E: インフラストラクチャセットアップ](observability/01-infrastructure-setup-lab.md) | 中級 | シリーズ紹介を完了し、ネットワーキングの準備が完了済み |
| 11 | [Observability E2E: Observability スタック](observability/02-observability-stack-lab.md) | 上級 | パート 1 を完了済み |
| 12 | [Observability E2E: MSA デプロイメントと Canary](observability/03-msa-deployment-lab.md) | 上級 | パート 2 を完了済み |
| 13 | [Observability E2E: 負荷テストとオートスケーリング](observability/04-load-testing-scaling-lab.md) | 中級 | パート 3 を完了済み |
| 14 | [Observability E2E: アラートと AIOps](observability/05-alerting-aiops-lab.md) | 上級 | パート 4 を完了済み |
| 15 | [Observability E2E: 分散トレーシング分析](observability/06-distributed-tracing-lab.md) | 上級 | パート 5 を完了済み |

## 推奨学習パス

1. **基礎ラボ** (1→2→3): Linux とコンテナ技術を学ぶ
2. **コアラボ** (4→7→5→6): Kubernetes のコアリソースを扱う
3. **EKS ラボ** (8): 実際のクラウド環境でクラスターを運用する
4. **Observability ラボ** (9→10→11→12→13→14→15): エンドツーエンドの Observability スタックを構築・運用する

## ラボ環境のセットアップ

### ローカル環境（基礎／コンテナラボ向け）
- Linux ターミナル（WSL2、macOS Terminal、または Linux）
- Docker Desktop または Docker Engine

### Kubernetes 環境（コアラボ向け）
OS/CPU アーキテクチャに合ったツールをインストールし、各ラボのクラスター／バージョン要件に従ってください。macOS や ARM 上で Linux AMD64 バイナリをそのままインストールしないでください。

```bash
kubectl version --client
kubectl config current-context
```

### AWS 環境（EKS ラボ向け）
- AWS アカウントと設定済みの AWS CLI
- eksctl をインストール済み

## ラボのヒント

- まず各ラボの **前提条件** を確認する
- コマンドを実行した後、**期待される出力** と比較して正しく動作していることを確認する
- 行き詰まった場合は **ヒント** を使用する
- ラボを完了したら、必ず **クリーンアップ** セクションのコマンドを実行してリソースを削除する
