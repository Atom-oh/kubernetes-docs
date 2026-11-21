# ラボガイド


> **最終更新日**: 2026年11月21日

このセクションでは、Kubernetesおよび関連技術を実践的に学ぶためのラボガイドを紹介します。各ラボには、手順と検証方法が含まれており、理論で学んだ内容を実際の環境で確認できます。

## ラボ一覧

| # | ラボ | 難易度 | 前提条件 |
|---|-----|------------|---------------|
| 1 | [Linux基礎ラボ](basics/01-linux-basics-lab.md) | 初級 | Linuxターミナルへのアクセス |
| 2 | [Linux応用スキルラボ](basics/02-linux-advanced-lab.md) | 初級 | Linux基礎の完了 |
| 3 | [コンテナ技術ラボ](basics/03-container-technology-lab.md) | 初級 | Dockerのインストール |
| 4 | [Podとワークロードのラボ](core/02-pods-and-workloads-lab.md) | 初級 | kubectl、K8sクラスター |
| 5 | [Serviceとネットワーキングのラボ](core/03-services-networking-lab.md) | 中級 | kubectl、K8sクラスター |
| 6 | [ストレージラボ](core/04-storage-lab.md) | 中級 | kubectl、K8sクラスター |
| 7 | [ConfigMapとSecretのラボ](core/05-configuration-secrets-lab.md) | 初級 | kubectl、K8sクラスター |
| 8 | [EKSクラスター作成ラボ](eks/01-eks-cluster-creation-lab.md) | 中級 | AWS CLI、eksctl |
| 9 | [Observability E2E：シリーズ紹介](observability/README.md) | 上級 | 承認済みのAWS環境、Helm、Python |
| 10 | [Observability E2E：インフラストラクチャのセットアップ](observability/01-infrastructure-setup-lab.md) | 中級 | シリーズ紹介の完了、ネットワーキングの準備完了 |
| 11 | [Observability E2E：オブザーバビリティスタック](observability/02-observability-stack-lab.md) | 上級 | パート1の完了 |
| 12 | [Observability E2E：MSAのデプロイとカナリア](observability/03-msa-deployment-lab.md) | 上級 | パート2の完了 |
| 13 | [Observability E2E：負荷テストとオートスケーリング](observability/04-load-testing-scaling-lab.md) | 中級 | パート3の完了 |
| 14 | [Observability E2E：アラートとAIOps](observability/05-alerting-aiops-lab.md) | 上級 | パート4の完了 |
| 15 | [Observability E2E：分散トレーシングの分析](observability/06-distributed-tracing-lab.md) | 上級 | パート5の完了 |
| 16 | [EKSワークロードIAM移行ラボ](security/17-eks-workload-identity-migration-lab.md) | 上級 | 既存のEKSクラスター、AWS CLI、kubectl、jq |

## 推奨学習パス

1. **基礎ラボ** (1→2→3)：Linuxとコンテナ技術を学ぶ
2. **コアラボ** (4→7→5→6)：Kubernetesのコアリソースを扱う
3. **EKSラボ** (8)：実際のクラウド環境でクラスターを運用する
4. **オブザーバビリティラボ** (9→10→11→12→13→14→15)：エンドツーエンドのオブザーバビリティスタックを構築・運用する
5. **セキュリティラボ** (16)：EKSワークロードのIAMをノードロールからIRSAおよびPod Identityに移行する

## ラボ環境のセットアップ

### ローカル環境（基礎／コンテナラボ向け）
- Linuxターミナル（WSL2、macOSのターミナル、またはLinux）
- Docker DesktopまたはDocker Engine

### Kubernetes環境（コアラボ向け）
お使いのOS／CPUアーキテクチャに対応するツールをインストールし、各ラボで指定されたクラスターとバージョンの要件に従ってください。Linux AMD64バイナリをmacOSやARMにそのままインストールしないでください。

```bash
kubectl version --client
kubectl config current-context
```

### AWS環境（EKSラボ向け）
- AWSアカウントと設定済みのAWS CLI
- eksctlのインストール

## ラボのヒント

- まず各ラボの**前提条件**を確認してください
- コマンドを実行したら、**期待される出力**と照らし合わせて正しく動作したことを確認してください
- 行き詰まったら**ヒント**を活用してください
- ラボの完了後は、必ず**クリーンアップ**セクションのコマンドを実行してリソースを削除してください
