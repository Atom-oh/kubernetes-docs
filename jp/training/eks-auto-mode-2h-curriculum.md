# EKS Auto Mode 運用者向けトレーニングカリキュラム（2時間）

> **対象者**: EKS を運用するインフラストラクチャ／プラットフォームエンジニア
> **前提条件**: Kubernetes の基礎知識と EKS の運用経験
> **最終更新日**: 2026年9月12日

## 学習目標

AWS が管理する責任範囲と運用者が所有する範囲を区別し、Auto Mode の NodePool／NodeClass リソースを設計し、ワークロード／コスト／可用性の根拠に基づいて改善を評価し、ノードの中断を調査できるようになることを目指します。一定の削減率やプロビジョニング時間が成果として保証されるわけではありません。

## スケジュールと準備

| パート | 所要時間 | 内訳 |
| --- | --- | --- |
| 1: アーキテクチャと配置 | 40分 | アーキテクチャ10分 + NodePool／NodeClass 15分 + スケーリング15分 |
| 2: 最適化とライフサイクル | 35分 | Spot 10分 + コスト10分 + ワークロード10分 + ライフサイクル5分 |
| 休憩 | 10分 | |
| 3: 可観測性と診断 | 25分 | ノード8分 + シグナルの相関付け8分 + シナリオ9分 |
| 4: IaC／GitOps | 10分 | IaC 5分 + ArgoCD 5分 |

合計: 120分。現在の API、準備済みのラボ環境、アカウント／リージョン／kubeconfig、権限、コスト制限を[Auto Mode ガイド](../eks-auto-mode/README.md)で確認してください。講義のみの場合は、記録済みのイベント、NodeClaim、メトリクスを使えます。このカリキュラムによって、実際の FIS 障害注入やノード削除が自動的に実行されることはありません。

行数やキーワードの出現数では、ドキュメントの品質や網羅性が十分かどうかを判断できないため、以前の評価表は削除しました。以下の参考資料を使い、利用中のバージョンに合わせて組織固有の Terragrunt／運用手順を補ってください。

## パート1: アーキテクチャと配置（40分）

### 1-1. 管理境界（10分）

[導入ガイド](../eks-auto-mode/01-getting-started.md)を使って、Auto Mode、マネージドノードグループ、セルフマネージド Karpenter を比較します。Auto Mode は Karpenter ベースのマネージドコンピュートを提供しますが、ワークロードのリクエスト、PDB、サポート対象の NodeClass ネットワーク／ストレージ／ID 設定は、引き続き運用者が管理します。

Auto Mode は、利用者が AL2023／Bottlerocket AMI を選んだり、任意の userData、SSH、SSM アクセスを使ったりする方式ではなく、AWS 管理の Bottlerocket バリアントを使用します。汎用／システムプールが実際に有効化されているか、存在するかを確認してください。管理対象コントローラーが通常のクラスター内 Pod として表示されると想定しないでください。

### 1-2. NodePool と NodeClass（15分）

[設定ガイド](../eks-auto-mode/02-nodepool-configuration.md)で、`eks.amazonaws.com` ラベルと NodeClass API を確認します。セルフマネージド Karpenter の `karpenter.k8s.aws` インスタンスラベル／EC2NodeClass と混同しないでください。カスタム NodeClass はサポートされています。AWS がすべての設定を代わりに選択するわけではありません。

以下の**スキーマ例**は、デフォルトの NodeClass がすでに存在し、Arm 互換イメージを使うことを前提としています。CPU／メモリの上限は、請求額に対する絶対的な上限ではありません。また、同時プロビジョニングによって一時的に上限を超える場合があります。あらゆる GPU／Spot ワークロードに使える汎用プールではありません。

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: web-tier-training
spec:
  template:
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - m
        - c
      - key: eks.amazonaws.com/instance-generation
        operator: Gt
        values:
        - '5'
      - key: kubernetes.io/arch
        operator: In
        values:
        - arm64
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  limits:
    cpu: '16'
    memory: 64Gi
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 5m
```

Pod のセレクター／アフィニティ、リクエスト、taint/toleration、プールの制約を比較してください。Arm への移行では、イメージマニフェスト、ネイティブ依存関係、パフォーマンスの検証が必要です。

### 1-3. スケーリング（15分）

[スケーリングガイド](../eks-auto-mode/03-scaling-behavior.md)に従い、スケジュール不能な Pod、プールの制約、ノードのプロビジョニング、Pod の Ready 化を確認します。40～90秒で完了する保証はありません。イメージの取得、IP／クォータ／キャパシティ、ボリューム依存関係を測定してください。

WhenEmpty、WhenEmptyOrUnderutilized、consolidateAfter を比較します。Pod のリクエスト量が実際の使用量と異なるワークロードも対象にしてください。統合処理は、手動での最適化や負荷検証に代わるものではありません。drift が発生しても、すべての変更で常に1台ずつ即時に置き換わるとは限りません。

## パート2: 最適化とライフサイクル（35分）

### 2-1. Spot（10分）

[Spot ガイド](../eks-auto-mode/04-spot-strategies.md)で、互換性のあるインスタンスタイプの多様性、クリティカルなキャパシティ、中断と復旧を確認します。Spot のみを要求する設定はハードな制約です。On-Demand へ自動フォールバックする優先設定を表すものではありません。do-not-disrupt や PDB によって、Spot の回収やノード障害を防ぐことはできません。

### 2-2. コスト（10分）

[コストガイド](../eks-auto-mode/06-cost-management.md)では、EC2、Auto Mode の料金、EBS、ロードバランサー／NAT／転送、可観測性のコストを分けて扱います。Graviton、Spot、統合による仮定上の削減率を掛け合わせ、測定結果として提示しないでください。

対象となる EC2 Instance Savings Plans／RI は、条件に従い、Compute Savings Plans と並行して EC2 使用量に適用できます。Auto Mode の別料金が自動的に割り引かれるわけではなく、Spot に追加適用されるものでもありません。Savings Plans はキャパシティ予約ではありません。購入判断は、対象となる時間あたりのベースラインと既存の適用状況を使って個別に行ってください。

### 2-3. ワークロード設計（10分）

[ワークロードガイド](../eks-auto-mode/08-workload-optimization.md)を使い、Web、バッチ、GPU、システムの各ワークロードについて、リクエスト、イメージ／アーキテクチャ、ストレージ、SLO を比較します。HPA はレプリカ数を制御し、VPA は CPU／メモリを推奨または更新し、Auto Mode はノードを提供します。GPU ワークロードには互換性のあるモデル／ドライバーが必要です。VPA が GPU インスタンスを選択するわけではありません。

VPA の Off は推奨のみを行います。プールの分離は、チーム、可用性、認可、キャパシティの要件に基づきます。taint／ラベルはテナントのセキュリティ境界ではありません。

### 2-4. ノードのライフサイクル（5分）

[ライフサイクルガイド](../eks-auto-mode/07-node-lifecycle.md)を使い、AWS が文書化している**デフォルトの有効期限336時間（14日）、NodeClaim 終了猶予期間のデフォルト24時間、マネージドインスタンスの最大有効期間21日**を区別します。以前の720時間（30日）の例は Auto Mode の標準値ではありません。また、いずれの有効期間も稼働時間の保証ではありません。

Budget は、任意の drift／空状態／統合による変更をレート制限します。営業時間外に、すべての有効期限切れ／中断／修復を延期できるわけではありません。保存されている NodeClaim の値、PDB、終了時刻、アプリケーションの復旧を確認してください。

## 休憩（10分）

## パート3: 可観測性と診断（25分）

### 3-1. ノードの観測（8分）

[運用ガイダンス](../eks-auto-mode/05-operations.md)を使って、NodePool／NodeClass／NodeClaim の Condition、イベント、ノード／ワークロードのメトリクスを確認します。AWS 管理コントローラーに、通常の Karpenter スクレイプエンドポイントや Deployment のログがあると想定しないでください。サポート対象のマネージドコンポーネントログと、実際の CloudWatch／Prometheus の発行元を設定してください。

以下の基本アラートは kube-state-metrics を使い、クラスター全体を対象にします。Auto Mode 専用のビューを作るには、利用可能なコンピュートタイプのラベルと正しい結合が必要です。削除済みノードや欠落した時系列については、データなし／履歴の調査を別途行ってください。

```yaml
groups:
- name: node-health
  rules:
  - alert: NodeNotReady
    expr: kube_node_status_condition{condition="Ready",status="true"} == 0
    for: 5m
  - alert: NodeMemoryPressure
    expr: kube_node_status_condition{condition="MemoryPressure",status="true"} ==
      1
    for: 2m
```

単位をそろえて、NodePool の `status.resources` と `spec.limits` を比較してください。実在しない `karpenter_nodeclaims_state/karpenter_nodepool_usage_limit` の比率は削除しました。CloudWatch Events と EventBridge は、順番に呼び出す2つのサービスではありません。実際のイベントソース、ルール、ターゲット、遅延を検証してください。

### 3-2. シグナルの相関付け（8分）

[可観測性ガイド](../observability/09-observability-optimization.md)と[Grafana ガイド](../observability/grafana/README.md)を使い、trace-to-logs、derived fields、exemplars を区別します。TraceID をインデックス付き Loki ラベルにする必要はありません。ログフィールド／構造化メタデータとクエリを使って、高カーディナリティを避けてください。

`tracesToLogsV2`、データソース UID／URL、ラベルマッピング、サンプリング、保持期間など、バージョン固有の設定を確認します。Exemplar を使うには、互換性のある発行元、収集、ストレージ、UI が必要です。フラグを1つ設定しただけで、既存データのトレースリンクが作られるわけではありません。講義用に、実際に相関付けされたリクエストの例を準備してください。

### 3-3. 根拠に基づくシナリオ（9分）

| 症状 | 根拠 | 早まって結論付けないこと |
| --- | --- | --- |
| 新しいノードが追加されず Pending | Pod イベント、PVC、アフィニティ、taint、Class／Pool の Condition、クォータ／IP／キャパシティ、API エラー | 常にキャパシティ不足が原因だとすること |
| ノードが消えた | 削除／中断イベント、NodeClaim、マネージドログ、EC2／CloudTrail、復旧状況 | 常に統合または OOM が原因だとすること |
| 応答レイテンシ | エラー／レイテンシの分布、キュー、トレース／ログ、CPU／RAM／ネットワーク／ストレージ | 1つのトレースや温度だけで原因を断定すること |

CloudTrail に記録されるのは API アクションであり、すべてのスケジューリング失敗の確定的な原因ではありません。EC2 API が呼び出されなかった場合は、Kubernetes の Condition／イベントが重要です。欠落した過去のテレメトリを復元できたかのように説明しないでください。

## パート4: IaC／GitOps（10分）

### 4-1. IaC の境界（5分）

[インフラストラクチャガイド](../ops/01-infrastructure-setup.md)を使って、共有バックエンド設定とネットワーク／クラスター／プラットフォームのデプロイ層を区別します。ファイルや state を分けただけで、ネットワークの変更がクラスターに影響しない保証が得られるわけではありません。プロバイダー／モジュールの Auto Mode 設定、ロック、出力の依存関係、適用順序を検証してください。

### 4-2. GitOps 運用（5分）

[ArgoCD Applications](../gitops/argocd/02-applications.md)と[ApplicationSets](../gitops/argocd/04-applicationsets.md)で、権限、ジェネレーター、同期ポリシーを比較します。Auto-sync／self-heal／prune が、自動的に安全なロールアウトになるわけではありません。NodePool／NodeClass の削除による影響と drift の管理主体を確認し、Progressive Sync の有効化状況とバージョン対応を検証してください。

## 評価とラボの準備

- [導入と管理境界](../quizzes/eks-auto-mode/01-getting-started-quiz.md)
- [NodePool／NodeClass](../quizzes/eks-auto-mode/02-nodepool-configuration-quiz.md)
- [スケーリング](../quizzes/eks-auto-mode/03-scaling-behavior-quiz.md)
- [Spot](../quizzes/eks-auto-mode/04-spot-strategies-quiz.md)
- [コスト](../quizzes/eks-auto-mode/06-cost-management-quiz.md)
- [ワークロード](../quizzes/eks-auto-mode/08-workload-optimization-quiz.md)
- [ノードのライフサイクル](../quizzes/eks-auto-mode/07-node-lifecycle-quiz.md)
- [運用](../quizzes/eks-auto-mode/05-operations-quiz.md)

アカウント／クラスターの確認、サポート対象 API／イメージ、テレメトリ、クリーンアップ手順を準備し、実際に実行した内容を明記してください。[移行ガイド](../eks-auto-mode/09-migration-guide.md)と[本番環境での Spot 実験](../ops/17-spot-production-experiments.md)を参照してください。障害注入は別の範囲を限定したラボであり、専用環境、停止条件、復旧の根拠が必要です。

## レビューの根拠

検証では、120分のスケジュール、リンク、NodePool の構造スキーマ、ノードアラートルールを確認しました。クラスター作成、ノード置換、FIS 実験、削減額の測定、可観測性バックエンドのデプロイは行っていません。

- [Auto Mode NodePool のデフォルト](https://docs.aws.amazon.com/eks/latest/userguide/create-node-pool.html)
- [マネージドインスタンスの最大有効期間](https://docs.aws.amazon.com/eks/latest/userguide/auto-security.html)
- [Auto Mode の責任範囲と OS](https://docs.aws.amazon.com/eks/latest/userguide/automode.html)
- [マネージドコンポーネントのログ](https://docs.aws.amazon.com/eks/latest/userguide/auto-managed-component-logs.html)
- [Grafana Tempo の設定](https://grafana.com/docs/grafana/latest/datasources/tempo/configure-tempo-data-source/)
- [Loki のラベルカーディナリティ](https://grafana.com/docs/loki/latest/get-started/labels/)
