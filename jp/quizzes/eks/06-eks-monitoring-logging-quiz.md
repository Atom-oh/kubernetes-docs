# Amazon EKS のモニタリングとログ記録に関するクイズ

> **最終更新日**: 2026年10月16日

このクイズでは、Amazon EKS のモニタリングとログ記録の機能、ツール、ベストプラクティスへの理解を確認します。

## クイズの概要
- EKS クラスターのモニタリング
- コンテナとアプリケーションのログ記録
- パフォーマンスメトリクスの収集と分析
- アラートと異常検知
- モニタリングおよびログ記録のアーキテクチャ
- ベストプラクティスとツール

## 選択式問題

### 1. EKS のモニタリングソリューションを設計する際の適切な原則はどれですか？

- A. CloudWatch はアプリケーションのトレースを収集できない。
- B. Grafana をインストールすれば、すべての Pod メトリクスが自動的に収集される。
- C. 必要なシグナルを選び、所有者が明確なコレクターとデータソースを設定し、配信状況とカバレッジを検証する。
- D. CloudWatch、Prometheus、Grafana、X-Ray をすべてインストールすれば、常に完全な可視性が得られる。

<details>
<summary>回答を表示</summary>

**回答: C. シグナル、コレクター、バックエンドの設計を選び、検証する。**

**解説:**

複数のツールを組み合わせる方法は有効ですが、必要なシグナルと運用上の制約に基づいて設計を決めます。CloudWatch は基本的なインフラストラクチャメトリクスに限らず、対応するワークロードの Application Signals によるトレース/APM もサポートします。Grafana は AWS やトレースのデータソースを照会できますが、UI 自体がすべてのシグナルを収集するわけではありません。コレクター、計装、ID、到達可能なエンドポイント、互換性のある設定を明示的に接続する必要があります。製品を並べるだけで完全なカバレッジが保証されることはありません。

**有効な各レイヤーを維持する:**

| レイヤー | シグナルの例 | 主な依存関係 |
| --- | --- | --- |
| インフラストラクチャ | ノードの CPU/メモリ、ディスク、ネットワーク | 対応するノードコレクターと正しいメトリクスディメンション |
| Kubernetes | オブジェクトの状態、Ready 状態、API アクティビティ | Exporter/API/監査権限と実際のターゲット |
| アプリケーション | リクエストレイテンシ、エラー、ビジネスメトリクス | アプリケーションの計装と上限を定めたメトリクススキーマ |
| 分散リクエスト | トレーススパンとサービス間の関係 | コンテキスト伝播、サンプリング、正常なエクスポート |

**導入の順序:**

1. [原文の章](../../eks/06-eks-monitoring-logging.md)に従い、所有する CloudWatch アドオンのカタログ、スキーマ、ID を確認します。Auto Monitor v5 以降と再起動設定を検討してください。競合を確認せず、すでに計装されたワークロードに別のエージェントを重ねてはいけません。
2. Prometheus による収集やクエリが必要な場合は、原文の KPS 92.9.0 の値と、準備済みのストレージ、Grafana Secret、kubelet の serving CA 前提条件を使います。Operator は ServiceMonitor/PrometheusRule を処理します。単独の Prometheus インストールは同等ではありません。導入後に実際のターゲットを確認してください。
3. 明示的な ADOT 経路には、原文の Operator 0.158/Collector 0.50 の v1beta1 例を使います。設定はオブジェクト形式で、TLS と準備済み ServiceAccount が必要です。Collector のリリースには Operator のインストールマニフェストは含まれません。この経路はトレースのみを X-Ray に送ります。アプリケーション側の計装と伝播も必要です。
4. AMP では実際のワークスペースのリモート書き込みエンドポイントと書き込み用 ID を設定します。Grafana/AMG のデータソース照会用 ID は別途設定します。AMG 12 以降では AMP プラグインを使います。awsemf Exporter の出力先は CloudWatch であり、自動的に AMP へ送られるわけではありません。

**データ経路の例:**

```text
EKS control-plane logs -------------------------------> CloudWatch Logs
Container stdout/stderr -> chosen log collector ------> configured log store
Application spans ------> ADOT OTLP receiver ----------> X-Ray
Metric targets ----------> Prometheus -----------------> local TSDB
                              |-- SigV4 remote_write -> AMP
Grafana/AMG -- configured queries --> Prometheus / AMP / CloudWatch / X-Ray
```

ここに示すのは選択可能な経路であり、すべてのコレクターがすべてのバックエンドへエクスポートするという意味ではありません。ダッシュボードに依存する前に、権限、TLS、検出/セレクター、破棄されたデータ、代表的なクエリを検証してください。アラートの優先度とエスカレーションを定義し、カーディナリティ、サンプリング、保持期間を管理します。自動応答は別途テストしてください。

**Terraform の計画例:**

次のリソース例では AWS provider 6.69.1 を使います。対象アカウント/リージョン、既存のレビュー済み Grafana ワークスペースロール、対応する AMG バージョン、利用可能な IAM Identity Center の構成が前提です。既存リソースを扱う場合は、その所有者のインポート/変更手順に従います。アプリケーションロググループ名は原文のコレクターパスと一致します。アドオンや別のスタックがすでに管理するグループを重複して所有しないでください。

```hcl
terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "= 6.69.1"
    }
  }
}

variable "region" {
  type = string
}

variable "account_id" {
  type = string
  validation {
    condition     = can(regex("^[0-9]{12}$", var.account_id))
    error_message = "Use the approved 12-digit AWS account ID."
  }
}

variable "cluster_name" {
  type = string
}

variable "grafana_workspace_role_arn" {
  type = string
}

variable "grafana_version" {
  type        = string
  description = "A reviewed AMG version supported in the selected Region."
}

provider "aws" {
  region              = var.region
  allowed_account_ids = [var.account_id]
}

resource "aws_prometheus_workspace" "eks_monitoring" {
  alias = "${var.cluster_name}-monitoring"
}

resource "aws_grafana_workspace" "eks_monitoring" {
  name                     = "${var.cluster_name}-monitoring"
  account_access_type      = "CURRENT_ACCOUNT"
  authentication_providers = ["AWS_SSO"]
  permission_type          = "CUSTOMER_MANAGED"
  role_arn                 = var.grafana_workspace_role_arn
  grafana_version          = var.grafana_version
}

resource "aws_cloudwatch_log_group" "application" {
  name              = "/aws/containerinsights/${var.cluster_name}/application"
  log_group_class   = "STANDARD"
  retention_in_days = 30
}

output "amp_workspace_id" {
  value = aws_prometheus_workspace.eks_monitoring.id
}

output "amp_prometheus_endpoint" {
  value = aws_prometheus_workspace.eks_monitoring.prometheus_endpoint
}

output "grafana_workspace_id" {
  value = aws_grafana_workspace.eks_monitoring.id
}
```

これはリソース定義であり、収集やログインが動作する経路を作るものではありません。実際のワークスペース ARN に対する照会権限をロールに設定し、ユーザー/グループを割り当て、データソースを追加して、返された ID/エンドポイントを使ってコレクターを接続してください。CUSTOMER_MANAGED は IAM 管理を所有者に明示的に委ねます。以前の SERVICE_MANAGED/data_sources の断片は、API で作成したワークスペースに必要なロールや接続が備わる証拠ではありません。暗号化、保持、アクセス、コスト要件は個別に検討してください。この監査では Terraform の plan/apply、ログイン、実際のテレメトリクエリを実行していません。

**他の選択肢が不適切な理由:** A は現在の CloudWatch 機能を過小評価しています。B は可視化と収集を混同しています。D はインストールをカバレッジの保証とみなしています。所有者、エラー、適用範囲が明確なら、限定的な自動化や確認にカスタムスクリプトが役立つことはあります。

</details>

### 2. コンテナログを一元的な保持・分析につなぐ適切な方法はどれですか？

- A. ノード上のファイルを定期的に手作業でコピーすれば、完全で永続的なログ経路になると考える。
- B. コンテナ内のファイルはコンテナやノードの交換後も必ず残ると考える。
- C. ランタイムに合ったパーサー、権限、ストレージ、設定済みバックエンドを備える、所有者が明確なコレクターを使う。
- D. 同じファイルを読むコレクターを2つ導入すれば、ロスレス配信が保証されると考える。

<details>
<summary>回答を表示</summary>

**回答: C. 所有者を明確にした収集経路を設定して検証する。**

**解説:**

アプリケーションは通常、適切に構造化したレコードを stdout/stderr に書き、プラットフォーム側で収集と保持を行います。stdout は有用なインターフェイスですが、それ自体が永続的な一元ストアではありません。コレクターは解析、フィルタリング、バッファリング、ルーティングを行えますが、ローテーション、有限のバッファ、ノード障害、再試行はカバレッジや重複に影響します。完全性やロスレス配信を保証すると主張せず、アクセス、機密フィールド、保持期間を管理してください。

**接続済み Fluent Bit の基本構成:**

[原文の章](../../eks/06-eks-monitoring-logging.md)を参照し、無関係な master ブランチのマニフェストを適用しないでください。単独の例は AWS chart 0.2.0/image 3.4.14、ネイティブ cloudWatchLogs 設定、CRI 解析、読み取り専用ノードログ、個別の状態/バッファ、レビュー済み RBAC post-renderer を使います。実際のロググループと IAM ID を準備してください。CloudWatch アドオンがすでに Fluent Bit を所有している場合は、誤って同じログを二重に読む構成を作らず、その所有者の設定を使ってください。

OpenSearch にも送る場合は、次の原文オーバーレイを完全なベース値および post-renderer と合わせ、所有者のインストール/アップグレード手順に組み込みます。

```yaml
opensearch:
  enabled: true
  host: vpc-eks-logs-EXAMPLE.us-west-2.es.amazonaws.com
  port: '443'
  tls: 'On'
  awsAuth: 'On'
  awsRegion: us-west-2
  index: eks-logs
  generateId: 'On'
  suppressTypeName: 'On'
  extraOutputs: 'tls.verify On

    storage.total_limit_size 512M

    '
```

エンドポイント/リージョンを確認済みのドメイン値に置き換えます。SigV4 権限、ドメインポリシー、FGAC ロールマッピング、TLS 検証はそれぞれ別の要件です。1つのリクエストで Basic 認証情報と SigV4 を併用しないでください。各出力の成功/再試行は独立しています。CloudWatch への成功は OpenSearch への配信を証明しません。対応する record-accessor テンプレートとフォールバックのストリーム名を使ってください。log_stream_prefix は Kubernetes レコードフィールドを展開する任意のシェル式ではありません。

**Fluentd の選択肢: プラグインと入力の前提条件を明示する**

所有するイメージに必要なパーサー、Kubernetes メタデータ、OpenSearch プラグインが含まれていれば、Fluentd も選択肢になります。containerd/CRI-O の外包をデコードしてから、アプリケーション本文を JSON として扱います。tail 入力、メタデータ権限、コレクターごとの位置/バッファストレージ、マウント済み設定を構成します。次は OpenSearch 出力の断片にすぎず、ConfigMap/DaemonSet の完全なインストール例ではありません。

```text
<match kubernetes.**>
  @type opensearch
  ssl_verify true
  logstash_format false
  include_timestamp true
  index_name eks-logs
  suppress_type_name true
  <endpoint>
    url "#{ENV.fetch('OPENSEARCH_URL')}"
    region "#{ENV.fetch('AWS_REGION')}"
    assume_role_arn "#{ENV.fetch('AWS_ROLE_ARN')}"
    assume_role_web_identity_token_file "#{ENV.fetch('AWS_WEB_IDENTITY_TOKEN_FILE')}"
  </endpoint>
  <buffer>
    @type file
    path /var/lib/fluentd/opensearch
    total_limit_size 256m
    chunk_limit_size 2m
    retry_timeout 1h
    overflow_action block
  </buffer>
</match>
```

この設定では公式 fluent-plugin-opensearch の IRSA エンドポイント用フィールドと固定インデックスを使います。OPENSEARCH_URL と IRSA が注入するロール/トークンファイル環境変数を準備してください。logstash_format=true の場合 index_name は無視されます。任意の Pod 単位インデックス式は、検証済みのルーティング/保持設計の代わりにはなりません。上限のあるインデックス/エイリアスを選び、ロールオーバーポリシーを確認してください。ファイルバッファには適切で書き込み可能な分離ストレージパスが必要です。ブロックや再試行を設定しても、ローテーションやノード障害後に未読ログが失われる可能性があります。この監査ではプラグインと入力の組み合わせを実行していません。

**選択したコンポーネントでサポートされる ADOT ログ収集:**

ADOT 0.50.0 には filelog、file_storage、awscloudwatchlogs が含まれます。対応する upstream 0.158 の CloudWatch Logs Exporter は alpha とされています。これは前提条件を明示したバージョン固有の例であり、本番対応の主張ではありません。Fluent Bit を誤って二重起動するのではなく、対象データセット用の代替コレクターとして使ってください。

Operator 0.158、logging 名前空間、レビュー済み IRSA ロールと AWS ログ書き込み権限を持つ adot-logs ServiceAccount を準備します。信頼ポリシーはこのクラスターの OIDC プロバイダー、sub=system:serviceaccount:logging:adot-logs、aud=sts.amazonaws.com に限定し、必要な STS/Logs ネットワーク経路を提供してください。この例は標準 Linux EC2 ノード用です。読み取り専用の /var/log/pods と専用の書き込み可能な状態ディレクトリをマウントする root ノードエージェントを許可する admission 設定が必要です。既定の namespace include フィルターはエクスポート対象を制限しますが、ノード全体の host マウントがファイルシステムのセキュリティ境界になるわけではありません。ノード配置/taint、ファイル所有権、namespace ポリシーを確認してください。デプロイ前に実際のリージョン/ロググループ値を設定します。

```yaml
apiVersion: opentelemetry.io/v1beta1
kind: OpenTelemetryCollector
metadata:
  name: adot-logs
  namespace: logging
spec:
  mode: daemonset
  image: public.ecr.aws/aws-observability/aws-otel-collector:v0.50.0
  serviceAccount: adot-logs
  nodeSelector:
    kubernetes.io/os: linux
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
        - matchExpressions:
          - key: eks.amazonaws.com/compute-type
            operator: NotIn
            values: [fargate, auto, hybrid]
  env:
  - name: AWS_REGION
    value: us-west-2
  - name: AWS_EC2_METADATA_DISABLED
    value: "true"
  - name: K8S_NODE_NAME
    valueFrom:
      fieldRef:
        fieldPath: spec.nodeName
  - name: LOG_GROUP_NAME
    value: /aws/containerinsights/my-owned-cluster/application
  resources:
    requests:
      cpu: 100m
      memory: 256Mi
    limits:
      cpu: "1"
      memory: 512Mi
  podSecurityContext:
    runAsUser: 0
    runAsGroup: 0
    runAsNonRoot: false
    seccompProfile:
      type: RuntimeDefault
  securityContext:
    allowPrivilegeEscalation: false
    readOnlyRootFilesystem: true
    capabilities:
      drop: [ALL]
  volumes:
  - name: pod-logs
    hostPath:
      path: /var/log/pods
      type: Directory
  - name: collector-state
    hostPath:
      path: /var/lib/adot-logs
      type: DirectoryOrCreate
  volumeMounts:
  - name: pod-logs
    mountPath: /var/log/pods
    readOnly: true
  - name: collector-state
    mountPath: /var/lib/adot-logs
  config:
    extensions:
      file_storage:
        directory: /var/lib/adot-logs/checkpoints
        create_directory: true
      health_check:
        endpoint: 0.0.0.0:13133
    receivers:
      filelog:
        include: [/var/log/pods/default_*/*/*.log]
        include_file_path: true
        start_at: end
        storage: file_storage
        retry_on_failure:
          enabled: true
          max_elapsed_time: 5m
        operators:
        - type: container
          add_metadata_from_filepath: true
          max_log_size: 1MiB
    processors:
      memory_limiter:
        check_interval: 1s
        limit_mib: 384
        spike_limit_mib: 64
      batch: {}
    exporters:
      awscloudwatchlogs:
        region: us-west-2
        log_group_name: ${env:LOG_GROUP_NAME}
        log_stream_name: ${env:K8S_NODE_NAME}
        log_retention: 30
        raw_log: false
        sending_queue:
          num_consumers: 2
          queue_size: 100
    service:
      extensions: [file_storage, health_check]
      pipelines:
        logs:
          receivers: [filelog]
          processors: [memory_limiter, batch]
          exporters: [awscloudwatchlogs]
```

コンテナ Operator は CRI 外包/部分レコードを処理し、log.file.path から Pod メタデータを導出します。未加工 CRI 行に汎用 JSON パーサーを適用するのは誤りです。ストリーム名は Downward API のノード名を Collector 環境変数展開で取得します。未対応の {pod_name}.{container_name} プレースホルダーは使いません。

Exporter はグループ/ストリームを作成できます。log_retention は新規作成グループに適用されるため、既存グループの保持期間はその所有者が設定してください。文書化された EMF 処理では設定したグループ/ストリーム名が上書きされることがあります。IAM の宛先範囲を制限し、実際のデータ形式を確認してください。設定文字列だけでは認可境界になりません。

file_storage が保持するのは受信位置であり、未送信のすべてのバッチではありません。この例はインメモリ送信キューと有限回の再試行を使います。チェックポイント状態、バッチ、hostPath データでは、障害時やライフサイクルの挙動が異なります。初回読み込み時に保存済みオフセットがないと、start_at=end は既存内容を読み飛ばします。再試行、キュー/ドロップ/ストレージエラー、ノードローテーションを監視してください。この監査では Collector プロセス、マウント、AWS 認証フロー、ログ取り込みをテストしていません。

**分析とインフラストラクチャの確認:**

原文の Fluent Bit スキーマでは、実際の namespace/container フィールドを使って構造化エラーを調べます。ADOT ラッパーや別のコレクターでは、保存されるスキーマが異なる場合があります。

```
fields @timestamp, @log, kubernetes.pod_name, data.level, data.message
| filter kubernetes.namespace_name = "default"
| filter toupper(data.level) = "ERROR"
| sort @timestamp desc
| limit 100
```

独立した Terraform の確認例は、承認済みの既存 OpenSearch ドメインを参照します。

```hcl
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.69.1"
    }
  }
}

variable "aws_region" {
  type    = string
  default = "us-west-2"
}

variable "opensearch_domain_name" {
  type        = string
  description = "Existing domain approved for this workload's logs"
}

provider "aws" {
  region = var.aws_region
}

data "aws_opensearch_domain" "eks_logs" {
  domain_name = var.opensearch_domain_name
}

output "opensearch_endpoint" {
  value = coalesce(
    data.aws_opensearch_domain.eks_logs.endpoint_v2,
    data.aws_opensearch_domain.eks_logs.endpoint
  )
}

output "opensearch_domain_arn" {
  value = data.aws_opensearch_domain.eks_logs.arn
}
```

このデータソースはネットワーク、IAM/ドメインポリシー、FGAC、配信設定を構成しません。管理用アクセスと取り込み用アクセスを分離し、マスターパスワードをコード/state に保存せず、リソース/アドレスの移行があれば確認してください。クエリとアクセスのテストには実環境が必要です。Terraform の検証はそれらのテストを行いません。

**他の選択肢が不適切な理由:** 手作業によるファイル調査は診断に役立ちますが、完全な一元ログ経路ではありません。コンテナ/ノードの寿命やボリューム種別によって、ファイルが残るかどうかが決まります。読み取り元を重複させるとデータやコストが重複する可能性があり、それでも障害は起こりえます。バッファと再試行には、容量測定と障害テストが必要です。

参考資料: [ADOT コンポーネント](https://github.com/aws-observability/aws-otel-collector/tree/v0.50.0)、[コンテナパーサー](https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/v0.158.0/pkg/stanza/docs/operators/container.md)、[CloudWatch Logs Exporter](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/v0.158.0/exporter/awscloudwatchlogsexporter)、[Fluentd OpenSearch プラグイン](https://github.com/fluent/fluent-plugin-opensearch)。

</details>

### 3. EKS の効果的で検証可能なアラート経路を作る方法はどれですか？

- A. 手作業でログを確認すれば、即時検知が保証されると考える。
- B. CloudWatch アラームを1つ作成すれば、すべての Kubernetes/アプリケーション障害を網羅できると考える。
- C. 任意の alertmanager-config ConfigMap を作れば、Operator がそれを読み込むと考える。
- D. 必要なシグナルを選び、メトリクス/イベントルールを認可済みの通知先につなぎ、それぞれの配信をテストする。

<details>
<summary>回答を表示</summary>

**回答: D. 必要なアラート経路を接続して検証する。**

**解説:**

CloudWatch アラーム、Prometheus/Alertmanager、EventBridge は、異なるシグナルやルーティングの用途を持ち、意図的に組み合わせられます。CloudWatch はアプリケーション/カスタムメトリクスもサポートします。Prometheus も適切な AWS Exporter からデータを取得できます。「インフラストラクチャ専用」と一括りにして、どちらかを退けるべきではありません。インストールだけでは、メトリクスのカバレッジ、正しいしきい値、発行権限、通知の正常な配信は成立しません。

**実在する時系列と単位に合ったメトリクスルール:**

次の PrometheusRule は、原文の章の KPS セレクターと実際の node-exporter/kube-state-metrics 時系列を使います。CPU と利用可能メモリの計算結果は明示的にパーセンテージなので、しきい値 80 に意味があります。CrashLoopBackOff では任意の再起動回数ではなく waiting reason を使います。Running Pod の Ready=false は含め、終了済み Pod は除外します。複数クラスターをまとめる場合は安定したクラスター識別子を加え、同等の組み込みルールを重複して導入しないよう確認してください。

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: eks-observability-alerts
  namespace: monitoring
  labels:
    release: monitoring
spec:
  groups:
  - name: eks-observability-example
    rules:
    - alert: NodeHighCPU
      expr: (100 * (1 - avg by (cluster, instance) (max by (cluster, instance, cpu) (rate(node_cpu_seconds_total{job="node-exporter",mode="idle"}[5m]))))) > 80
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: High non-idle CPU on {{ $labels.instance }}
        description: The node-exporter percentage has exceeded the example threshold; inspect workload and metric health.
    - alert: NodeMemoryFilling
      expr: (100 * (1 - max by (cluster, instance) (node_memory_MemAvailable_bytes{job="node-exporter"}) / max by (cluster, instance) (node_memory_MemTotal_bytes{job="node-exporter"}))) > 80 and on (cluster, instance) (max by (cluster, instance) (node_memory_MemTotal_bytes{job="node-exporter"}) > 0)
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: Low available memory on {{ $labels.instance }}
        description: This is a MemAvailable-based estimate, not a MemoryPressure condition or Pod request utilization.
    - alert: KubernetesPodCrashLooping
      expr: max by (cluster, namespace, pod, uid, container) (max_over_time(kube_pod_container_status_waiting_reason{job="kube-state-metrics",reason="CrashLoopBackOff"}[5m])) >= 1
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: CrashLoopBackOff observed for {{ $labels.namespace }}/{{ $labels.pod }}
        description: Inspect container {{ $labels.container }} logs and events; the rule tracks recent waiting reasons, not a restart-count guarantee.
    - alert: PodNotReady
      expr: (max by (cluster, namespace, pod, uid) (kube_pod_status_ready{job="kube-state-metrics",condition="true"}) == 0) and on (cluster, namespace, pod, uid) (max by (cluster, namespace, pod, uid) (kube_pod_status_phase{job="kube-state-metrics",phase=~"Pending|Running|Unknown"}) == 1)
      for: 15m
      labels:
        severity: warning
      annotations:
        summary: Active Pod {{ $labels.namespace }}/{{ $labels.pod }} is not ready
        description: Inspect Ready conditions and probes; terminal Succeeded/Failed Pods are excluded from this example.
```

これらは例示的なしきい値と継続時間です。MemAvailable は回収可能なメモリ量の推定値であり、kubelet の MemoryPressure 条件でも Pod リクエストに対する割合でもありません。時系列が欠落/古いことは、正常または使用量ゼロを意味しません。スクレイプの失敗とルール評価も別途監視してください。

**実際の Alertmanager 設定を接続する:**

原文の alertmanager-routing Secret (キー alertmanager.yaml)、alertmanager-values.yaml、通知用認証情報のマウントを使います。実際の Slack webhook と PagerDuty Events API v2 routing key をその Secret に準備してください。ネイティブ SNS を使う場合は、Alertmanager の実際の ServiceAccount に、トピック単位の発行権限と必要な KMS 権限を持つ AWS ID を準備します。別コンポーネントの IRSA ロールが自動的に共有されるわけではありません。

例の SNS アカウント/リージョン/トピックを置き換えてください。この完全なルーティング例では、critical アラートを PagerDuty、warning を Slack、未照合アラートを SNS に送ります。例示の Watchdog ルートは、別途 heartbeat 監視を構成するまでは破棄します。

```yaml
global:
  resolve_timeout: 5m
route:
  group_by:
  - cluster
  - namespace
  - alertname
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  receiver: sns-notifications
  routes:
  - matchers:
    - alertname="Watchdog"
    receiver: discard
  - matchers:
    - severity="critical"
    receiver: pagerduty-notifications
  - matchers:
    - severity="warning"
    receiver: slack-notifications
receivers:
- name: discard
- name: slack-notifications
  slack_configs:
  - api_url_file: /etc/alertmanager/secrets/notification-credentials/slack-url
    channel: '#eks-alerts'
    send_resolved: true
    title: '[{{ .Status | toUpper }}] {{ .CommonLabels.alertname }}'
    text: "{{ range .Alerts }}{{ .Annotations.summary }} \u2014 {{ .Annotations.description }}{{ \"\\n\" }}{{ end }}"
- name: sns-notifications
  sns_configs:
  - sigv4:
      region: us-west-2
    topic_arn: arn:aws:sns:us-west-2:123456789012:eks-alerts
    send_resolved: true
    subject: EKS {{ .CommonLabels.alertname }}
- name: pagerduty-notifications
  pagerduty_configs:
  - routing_key_file: /etc/alertmanager/secrets/notification-credentials/pagerduty-routing-key
    send_resolved: true
    severity: '{{ if eq .CommonLabels.severity "critical" }}critical{{ else }}warning{{ end }}'
    description: '{{ .CommonLabels.alertname }}'
```

既定レシーバーはフォールバックであり、子ルートが一致したときに自動的に同報するものではありません。意図した同報が必要な場合に限り、continue や明示的な兄弟ルートを設定してください。対応する amtool でファイル全体を検証し、ルートラベルをテストします。未定義の sns-forwarder サービスや、認証情報を含む ConfigMap は不要です。

**CloudWatch と EventBridge の発行権限:**

- Container Insights アラームでは、原文の章に記載された実際のメトリクスとディメンションを使います。マネージドノードグループ名が EC2 Auto Scaling グループ名と一致するとは限りません。AWS/EC2 ディメンション値を創作しないでください。
- CloudWatch アラームの発行元には、適切な SNS トピックポリシーが必要です。トピックが暗号化されている場合、CloudWatch アラームには alias/aws/sns では不十分であると AWS は説明しています。適切な制限の下で必要な発行操作を許可する、カスタマー管理 KMS キーを使ってください。
- EventBridge が利用できるのは、公開済み EKS アドオンヘルスイベントや、サポート対象の CloudTrail API イベントです。EKS Cluster Control Plane Health は EKS の直接イベントカタログにありません。API 呼び出しを試みただけでは、更新完了の証明になりません。
- SNS ターゲットには、EventBridge 実行ロールまたは文書化されたリソースポリシー方式を準備します。PutTargets の失敗と配信メトリクスを確認してください。トピックの存在やルール API の成功応答は配信の証明ではありません。

**Terraform の計画例:**

この独立した例は、所有者が管理する既存の標準 SNS トピックと準備済みのターゲットロールを参照します。トピック/キーのポリシー、サブスクリプション、実際の ContainerInsights データが前提です。ノード CPU アラームは、選択した ClusterName 時系列の Maximum を使い、アドオンイベントルールはアカウント/リージョン全体に適用されます。確認できるよう、アクションとルールは無効状態で始まります。

```hcl
terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "= 6.69.1"
    }
  }
}

variable "region" {
  type = string
}

variable "account_id" {
  type = string
  validation {
    condition     = can(regex("^[0-9]{12}$", var.account_id))
    error_message = "Use the approved 12-digit AWS account ID."
  }
}

variable "cluster_name" {
  type = string
}

variable "sns_topic_arn" {
  type        = string
  description = "Prepared standard SNS topic with reviewed publisher/subscription/key permissions."
}

variable "eventbridge_role_arn" {
  type        = string
  description = "Prepared target execution role allowed to publish to the selected topic."
}

provider "aws" {
  region              = var.region
  allowed_account_ids = [var.account_id]
}

resource "aws_cloudwatch_metric_alarm" "node_cpu" {
  alarm_name          = "${var.cluster_name}-node-cpu-warning"
  alarm_description   = "Example node CPU Maximum threshold; confirm actual ContainerInsights data."
  namespace           = "ContainerInsights"
  metric_name         = "node_cpu_utilization"
  dimensions          = { ClusterName = var.cluster_name }
  statistic           = "Maximum"
  period              = 300
  evaluation_periods  = 2
  datapoints_to_alarm = 2
  threshold           = 80
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "missing"
  actions_enabled     = false
  alarm_actions       = [var.sns_topic_arn]
}

resource "aws_cloudwatch_event_rule" "addon_health" {
  name_prefix = "eks-addon-health-"
  description = "Account/Region add-on health events; not filtered to a single cluster."
  state       = "DISABLED"
  event_pattern = jsonencode({
    source      = ["aws.eks"]
    account     = [var.account_id]
    region      = [var.region]
    detail-type = ["EKS Addon Health Degraded", "EKS Addon Health Restored"]
  })
}

resource "aws_cloudwatch_event_target" "sns" {
  rule      = aws_cloudwatch_event_rule.addon_health.name
  target_id = "ops-sns"
  arn       = var.sns_topic_arn
  role_arn  = var.eventbridge_role_arn
}
```

CPU の例では、5分間の最大値で2回しきい値を超えることを条件にしており、10分間連続で CPU 使用率が 80% になることを意味しません。欠損データを自動的に正常とは扱いません。有効化する前に、リソースの所有関係、発行アクセス、メトリクスデータ、想定される通知を確認してください。この抜粋はトピックポリシーやサブスクリプションを作成/置換せず、AWS に対して plan/apply も行っていません。

**SNS サブスクリプションと任意の Lambda 処理:**

メールサブスクリプションは確認が必要です。Lambda サブスクリプションには、対象 SNS トピックからの呼び出しを関数が許可するポリシーが必要です。サブスクリプションを作成しても呼び出し権限は付与されません。標準トピックの場合、SNS は Lambda を非同期で呼び出すため、重複処理が起きる可能性があります。カスタムアダプターには、実際の配信コード、パッケージ済み依存関係、保護された認証情報、入力検証、冪等性、障害/再試行処理、観測可能な結果が必要です。

send 関数の中身が pass で、それでも「正常に処理した」と返す古いプレースホルダーハンドラーをデプロイしてはいけません。HTTP のような statusCode を返しても、非同期 SNS 呼び出しへの通知応答にはなりません。配信失敗を正しく表面化し、文書化された SNS レコード形式を調べてください。任意の AlarmName 部分文字列から重大度を推測しないでください。サブスクリプション配信の失敗と Lambda 実行の失敗は別々に設定します。SQS によるバッファリングも、実際のキュー/event-source mapping と個別の障害制御が必要な任意の設計であり、アーキテクチャ図から暗黙に構成されるものではありません。

**経路を正しく分離する:**

```text
CloudWatch alarm -----------------------------> SNS -> confirmed subscribers
EventBridge rule -- authorized target role ---> SNS -> confirmed subscribers
Prometheus -> Alertmanager -- default --------> SNS
                         |-- warning --------> Slack
                         |-- critical -------> PagerDuty
Optional SNS subscriber -> implemented Lambda adapter -> chosen external channel
```

関連アラートをグループ化し、再通知間隔を制限し、重大度/対応時間を明示します。根拠と影響を添え、承認済みのテスト先で発火/解決と障害の代表的な経路を試してください。ツールをインストールしただけでは、完全なカバレッジも配信成功も保証されません。この監査ではトピック、サブスクリプション、アラーム、Lambda 呼び出し、通知を作成/実行していません。

参考資料: [原文の章](../../eks/06-eks-monitoring-logging.md)、[Alertmanager レシーバー](https://prometheus.io/docs/alerting/latest/configuration/)、[EKS イベント](https://docs.aws.amazon.com/eventbridge/latest/ref/events-ref-eks.html)、[SNS/Lambda](https://docs.aws.amazon.com/lambda/latest/dg/with-sns.html)、[CloudWatch アラーム向け暗号化 SNS](https://repost.aws/knowledge-center/cloudwatch-configure-alarm-sns)。

</details>

### 4. 有用な証拠を保つアプリケーションオブザーバビリティの設計はどれですか？

- A. ノード CPU だけを見れば、アプリケーションレイテンシのすべての原因が分かると考える。
- B. 受信したすべての service.name 属性を単一の共有 Collector 名で上書きする。
- C. 実際の経路を検証しつつ、選んだメトリクス、ログ、トレースを相関させ、サービス ID を保つ。
- D. 10% の head sampling なら、すべてのエラーや遅いリクエストを必ず保存できると考える。

<details>
<summary>回答を表示</summary>

**回答: C. ID を失わず、検証済みのシグナル経路を相関させる。**

**解説:**

メトリクスは率/分布/リソース状態を表し、ログはイベントの詳細を補い、トレースは計装された処理を結び付けます。調査には役立ちますが、完全な可視性や根本原因の特定を保証するわけではありません。明示的に有効化して確認すれば、プロファイリングから CPU/割り当て/ヒープの証拠を得られますが、すべてのトレースコレクターが自動的に提供する機能ではありません。

**正しい Collector とシグナル経路を使う:**

原文の Operator 0.158/ADOT 0.50 による所有済み TLS トレース専用設定と、Q2 の個別に範囲を限定したログ収集の選択肢を使います。Operator マニフェストは Collector のリリースではなく、Operator 自身のリリースから取得します。service.name はアプリケーション境界で保ちます。共有 resource processor が order-service、payment-service など複数の呼び出し元に、単一のグローバル値を上書き設定してはいけません。

Prometheus メトリクスでは、原文に記載された接続済み ServiceMonitor/Service 経路か、別途検証済みの Prometheus receiver を使います。アノテーションによる検出だけでは、正しいポート/パス、RBAC、レプリカ間のターゲット分散は設定されません。awsemf は CloudWatch にエクスポートします。AMP には実際のリモート書き込みエンドポイントと SigV4 ID が必要です。設定が awsemf だけなのに AMP への経路を図示しないでください。

**Java 計装の例:**

Spring Boot starter の代わりに、上流の OpenTelemetry Java agent を使う方法があります。確認したリリースは 2.31.1 です。レビュー済み JAR と互換性のあるアプリケーション/JVM を、アプリケーションのビルド手順で準備します。これにより、Gradle 宣言と application.properties を Java ソースブロックに混在させたり、整合しない 1.18-alpha starter をコピーしたりせずに済みます。すでに CloudWatch Auto Monitor や別の所有者によって計装されているプロセスに、別の agent を追加しないでください。

これはアプリケーションの実行時設定であり、監査テスト用コマンドではありません。原文の TLS receiver 向け OTLP/HTTP トレースを選択し、別経路の SDK メトリクス/ログ出力は無効のままにします。信頼する CA をマウントし、ほかに必要な JVM 起動オプションを維持してください。

```bash
set -euo pipefail
: "${OTEL_JAVA_AGENT_JAR:?Set the reviewed OpenTelemetry Java agent 2.31.1 JAR path}"
: "${APP_JAR:?Set the application JAR path}"
test -r "$OTEL_JAVA_AGENT_JAR"
test -r "$APP_JAR"
export OTEL_SERVICE_NAME=order-service
export OTEL_RESOURCE_ATTRIBUTES=k8s.cluster.name=my-owned-cluster
export OTEL_TRACES_EXPORTER=otlp
export OTEL_METRICS_EXPORTER=none
export OTEL_LOGS_EXPORTER=none
export OTEL_EXPORTER_OTLP_TRACES_PROTOCOL=http/protobuf
export OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=https://adot-traces-collector.tracing-demo.svc:4318/v1/traces
export OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE=/etc/otel/ca.crt
export OTEL_PROPAGATORS=tracecontext,baggage
export OTEL_TRACES_SAMPLER=parentbased_traceidratio
export OTEL_TRACES_SAMPLER_ARG=0.1
java "-javaagent:$OTEL_JAVA_AGENT_JAR" -jar "$APP_JAR"
```

Java agent 2.x の既定は http/protobuf ですが、この例では明示しています。シグナル固有の HTTP エンドポイントには /v1/traces を含めます。4317 の gRPC エンドポイントは別プロトコルなので、ポートだけ変えて代用することはできません。リリース/設定メタデータを確認済みであり、Java agent、JDK、アプリケーションはここでは実行していません。

**Python 計装の例:**

原文の RequestTracing adapter には Python 3.10 以降と、整合する SDK/HTTP exporter 1.44.0 を使います。payment アプリケーションの環境に次の値を設定し、例のクラスター名を置き換えて信頼する CA をマウントしてください。

```bash
export OTEL_SERVICE_NAME=payment-service
export CLUSTER_NAME=my-owned-cluster
export OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=https://adot-traces-collector.tracing-demo.svc:4318/v1/traces
export OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE=/etc/otel/ca.crt
```

次に adapter を示します。ライフサイクルとリクエスト境界が分かるよう、コードを掲載しています。

```python
import os
from urllib.parse import urlsplit

from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased
from opentelemetry.trace import SpanKind
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator


class RequestTracing:
    def __init__(self):
        endpoint = os.environ["OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"]
        parsed = urlsplit(endpoint)
        if parsed.scheme != "https" or parsed.path != "/v1/traces":
            raise ValueError("Set the HTTPS OTLP/HTTP traces endpoint including /v1/traces")
        self.provider = TracerProvider(
            resource=Resource.create({
                "service.name": os.environ["OTEL_SERVICE_NAME"],
                "k8s.cluster.name": os.environ["CLUSTER_NAME"],
            }),
            sampler=ParentBased(TraceIdRatioBased(0.1)),
        )
        exporter = OTLPSpanExporter(
            endpoint=endpoint,
            certificate_file=os.environ["OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE"],
            timeout=10,
        )
        self.provider.add_span_processor(BatchSpanProcessor(exporter))
        self.tracer = self.provider.get_tracer("example.request-handler")
        self.propagator = TraceContextTextMapPropagator()

    def handle_request(self, incoming_headers, operation):
        parent = self.propagator.extract(incoming_headers)
        with self.tracer.start_as_current_span("request", context=parent, kind=SpanKind.SERVER):
            outgoing_headers = {}
            self.propagator.inject(outgoing_headers)
            return operation(outgoing_headers)

    def close(self):
        self.provider.shutdown()
```

アプリケーション起動時にインスタンスを1つ作成し、実際のフレームワークハンドラーから正規化した受信ヘッダー名と実際の業務操作を指定して handle_request を呼び、正常なシャットダウン時に close を呼びます。これは Flask サーバーや決済実装ではありません。app/request/jsonify/process_transaction が存在すると暗黙に仮定しません。フレームワークでサポートされる方法を使って、渡されたコンテキストを実際のアウトバウンド呼び出しや非同期処理へ伝播します。

監査では SDK のエクスポートを無効にした状態でこの adapter を動かし、業務結果/エラーの保持と伝播/サンプリングだけを確認しました。実際のスパンエクスポートやデプロイ済み Collector を示す証拠ではありません。

**IRSA の信頼、権限、ServiceAccount を一致させる:**

次の独立した Terraform 例は、原文の tracing-demo/adot-traces Collector ID に一致します。宣言済み入力と、実クラスターの issuer に対する既存 IAM OIDC provider を使います。信頼条件には sub と aud の両方を含めます。X-Ray の PutTraceSegments はリソースレベル ARN で範囲を限定できないため、ポリシーでは必要な wildcard resource を使用しつつ、アクション/リージョンと信頼を限定します。無関係な CloudWatch/AMP 権限は付与しません。

```hcl
terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "= 6.69.1"
    }
  }
}

variable "region" {
  type = string
}

variable "account_id" {
  type = string
  validation {
    condition     = can(regex("^[0-9]{12}$", var.account_id))
    error_message = "Use the approved 12-digit AWS account ID."
  }
}

variable "cluster_oidc_issuer_url" {
  type        = string
  description = "The actual EKS cluster OIDC issuer URL; its IAM OIDC provider must already exist."
  validation {
    condition     = startswith(var.cluster_oidc_issuer_url, "https://")
    error_message = "Use the HTTPS issuer returned by the owned cluster."
  }
}

provider "aws" {
  region              = var.region
  allowed_account_ids = [var.account_id]
}

data "aws_partition" "current" {}

locals {
  oidc_hostpath     = trimsuffix(trimprefix(var.cluster_oidc_issuer_url, "https://"), "/")
  oidc_provider_arn = "arn:${data.aws_partition.current.partition}:iam::${var.account_id}:oidc-provider/${local.oidc_hostpath}"
}

resource "aws_iam_role" "adot_traces" {
  name = "adot-traces-example"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = local.oidc_provider_arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "${local.oidc_hostpath}:aud" = "sts.amazonaws.com"
          "${local.oidc_hostpath}:sub" = "system:serviceaccount:tracing-demo:adot-traces"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "xray_write" {
  name = "xray-trace-write"
  role = aws_iam_role.adot_traces.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["xray:PutTraceSegments"]
      Resource = "*"
      Condition = {
        StringEquals = { "aws:RequestedRegion" = var.region }
      }
    }]
  })
}

resource "aws_xray_group" "applications" {
  group_name        = "EKS-Applications"
  filter_expression = "service(\"order-service\") OR service(\"payment-service\")"
}

output "adot_traces_role_arn" {
  value = aws_iam_role.adot_traces.arn
}
```

Collector を作成する前に、準備済み namespace 内で新しい所有 ServiceAccount にロールアノテーションを付けて一括作成できます。既存の ServiceAccount/ロールを変更する場合は、その所有者の更新/インポート手順に従ってください。別の ID を上書きしたり、無関係な Pod Identity association を組み合わせたりしないでください。

```bash
set -euo pipefail
: "${ADOT_ROLE_ARN:?Set the reviewed role ARN from the owned Terraform stack}"
python3 - "$ADOT_ROLE_ARN" <<'PY' | kubectl create -f -
import json
import sys
print(json.dumps({
    "apiVersion": "v1",
    "kind": "ServiceAccount",
    "metadata": {
        "name": "adot-traces",
        "namespace": "tracing-demo",
        "annotations": {"eks.amazonaws.com/role-arn": sys.argv[1]},
    },
}))
PY
```

アノテーションを変えても、稼働中 Pod に認証情報が遡及的に注入されることはありません。必要なロールアウトを確認してください。実際の issuer/provider、トークン audience、引き受けたロール、ネットワーク経路を検証します。X-Ray グループは条件に合うトレースを絞り込みますが、アプリケーションを計装したり Collector に権限を与えたりはしません。不完全な AMG 作成コマンドを重複させるのではなく、Q1 のワークスペース/データソース設定を使います。この監査では IAM ロール/グループ/ServiceAccount を作成していません。

**ブラウザー RUM は別の経路:**

CloudWatch RUM web client は PutRumEvents データを CloudWatch RUM に送り、ADOT OTLP receiver へ自動的に送るわけではありません。X-Ray tracing を有効にすると、許可された HTTP リクエストに X-Amzn-Trace-Id を追加できます。クライアント/サーバーのトレースは既定では接続されません。対応するサーバー伝播/ブリッジと CORS の許可ヘッダーを確認してください。上記の W3C 専用例は X-Ray ヘッダーを自動的に取り込みません。汎用 OpenTelemetry ブラウザクライアントには、独自のサポート対象 OTLP エンドポイント/認証/CORS 設計が必要です。

```text
Browser CloudWatch RUM client -----> CloudWatch RUM
                 | optional X-Ray header/segment integration
Java order-service <--- propagated requests ---> Python payment-service
       | OTLP/HTTP TLS                              | OTLP/HTTP TLS
       +--------------> ADOT traces collector <-----+
                              |
                              v
                            X-Ray
Application metrics -> configured Prometheus -> optional SigV4 remote_write -> AMP
Application stdout  -> chosen log collector -> configured log store
Grafana/AMG         -> queries the configured data sources
```

**カバレッジ、サンプリング、プライバシー:**

- 対象母集団と時間枠を定義し、レイテンシ分布、スループット、エラー率、飽和を測定します。サンプリングされたトレース集合は、自動的に偏りのないメトリクス分布になるわけではありません。
- 上限のあるサービス名、正規化したルート、バージョン/環境、クラスター/namespace ID を使います。顧客/テナント ID と未加工リクエスト URL はカーディナリティやプライバシーの問題になるため、既定のメトリクスラベルにしません。
- head sampling はリクエストの最終結果より前に決定します。すべてのエラー/遅いリクエストを保証できず、tail sampling でも上流ですでに破棄されたスパンは復元できません。tail sampling にはトレース単位のアフィニティルーティングと十分なバッファ/時間枠が必要です。
- RUM のセッション/ユーザーデータ、ログ、スパン、プロファイルには、適切なアクセス、同意/収集ポリシー、保持期間が必要です。相関 ID はメタデータであり、認証情報ではありません。
- パフォーマンステストやプロファイリングは実行時シグナルを補完します。この例から、新たなベンチマークや本番性能の測定結果を主張するものではありません。

参考資料: [Java agent の設定](https://opentelemetry.io/docs/zero-code/java/agent/configuration/)、[Java SDK の設定](https://opentelemetry.io/docs/languages/java/configuration/)、[CloudWatch RUM/X-Ray](https://docs.aws.amazon.com/xray/latest/devguide/xray-services-RUM.html)、[原文の章](../../eks/06-eks-monitoring-logging.md)。

</details>

### 5. AWS 管理の EKS コントロールプレーンログを監視する方法はどれですか？

- A. AWS 管理のコントロールプレーンノードに直接 SSH 接続する。
- B. 必要な EKS ログ種別を設定し、CloudWatch Logs への配信を検証して、適切なクエリ/アクセス制御を適用する。
- C. ワーカーノードの DaemonSet が、管理対象コントロールプレーンのファイルシステムを読めると考える。
- D. ログダッシュボードを作れば、ErrorCount メトリクスも自動的に発行されると考える。

<details>
<summary>回答を表示</summary>

**回答: B. 管理されたログ経路を設定して検証する。**

**解説:**

EKS は選択したコントロールプレーンログ種別を、アカウント内の CloudWatch Logs に直接送信します。ワーカーコレクターはこれらの管理対象ログの取得元ではありません。これによりコントロールプレーンへの SSH なしで診断/監査証跡を得られますが、すべての API 呼び出しが記録されることや、コンプライアンスが証明されることを保証しません。利用できる記録は、監査ポリシー、ステージ、有効化時点、取り込み、保持期間で決まります。

**ログ種別と対象範囲:**

| 種別 | 用途 |
| --- | --- |
| api | API server の診断情報やエラー。完全なリクエスト/レスポンス記録ではない |
| audit | Kubernetes API の監査イベントと ID/リソース/ステータスフィールドの記録 |
| authenticator | IAM 認証/マッピングの診断。認証と RBAC 認可を区別する |
| controllerManager | コントローラーの調整処理に関する診断 |
| scheduler | スケジューリング判断/失敗と関連する診断 |

最初に既存クラスター設定を確認してください。5種すべてを変更する承認済みの操作では、原文の章の更新手順のように update ID を記録し、状態を確認します。成功するまで確認を続けたうえで、実際のログ配信も検証してください。

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the owned cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query 'cluster.{ARN:arn,Status:status,Logging:logging}'
```

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the reviewed cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
UPDATE_ID=$(aws eks update-cluster-config \
  --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}' \
  --query 'update.id' --output text)
if [[ -z "$UPDATE_ID" || "$UPDATE_ID" == None ]]; then
  printf '%s\n' 'No update ID returned; inspect the request result.' >&2
  exit 1
fi
aws eks describe-update --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --update-id "$UPDATE_ID" \
  --query 'update.{ID:id,Status:status,Errors:errors}'
```

最後の DescribeUpdate 呼び出しは状態確認であり、waiter でも取り込みテストでもありません。一部の種別だけを選ぶ場合も、既存の必須種別をすべて維持してください。api/audit を有効にするためだけに authenticator/controllerManager/scheduler を明示的に無効化するブロックをコピーしないでください。新規クラスターでは、レビュー済みの作成/IaC 設定にログ記録を含めます。モニタリング設定だけのために別の不完全なクラスターを作らないでください。EKS Capabilities のコントローラーログには、原文で説明する別の配信経路があります。

**実際の JSON フィールドをクエリする:**

所有する /aws/eks/CLUSTER/cluster グループと、範囲を限定した時間帯を選択します。記録された 5xx 応答の例:

```
fields @timestamp, auditID, user.username, verb, objectRef.resource, responseStatus.code
| filter apiVersion = "audit.k8s.io/v1" and stage = "ResponseComplete"
| filter responseStatus.code >= 500
| sort @timestamp desc
| limit 100
```

監査ログのユーザー名が分かっている場合は、user.username という文字列を検索するのではなく、ネストした JSON フィールドを使ってください。例のユーザー名は、実際の記録で確認した ID に置き換えます。

```
fields @timestamp, auditID, user.username, verb, objectRef.resource, responseStatus.code
| filter apiVersion = "audit.k8s.io/v1"
| filter user.username = "example-user"
| sort @timestamp desc
| limit 100
```

形式に依存する失敗フィルターを定義する前に、authenticator の記録を調べてください。failed/denied という部分文字列では実際のケースを見逃したり、無関係な文字列に一致したりすることがあります。また IAM 認証メッセージだけで Kubernetes の認可結果がすべて分かるわけではありません。

**ダッシュボードだけではメトリクスは発行されない:**

Logs Insights ウィジェットはクエリを実行します。カスタムメトリクスのアラームには、メトリクスフィルターなど実際の発行元が必要です。次の独立した Terraform 例は STANDARD ロググループ、フィルター、そのメトリクス、アラーム、ダッシュボードを接続します。この設定の前に、既存ロググループを実際の所有者経由で管理/インポートし、KMS キーと SNS トピック/発行権限を準備してください。新しい EKS クラスターや KMS キーは作成しません。

```hcl
terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "= 6.69.1"
    }
  }
}

variable "region" {
  type = string
}

variable "account_id" {
  type = string
}

variable "cluster_name" {
  type = string
}

variable "logs_kms_key_arn" {
  type        = string
  description = "Prepared symmetric key in the log-group Region with reviewed Logs/caller permissions."
}

variable "sns_topic_arn" {
  type        = string
  description = "Prepared standard SNS topic with confirmed subscriptions and publisher/key permissions."
}

provider "aws" {
  region              = var.region
  allowed_account_ids = [var.account_id]
}

locals {
  metric_namespace = "EKS/ControlPlane"
  metric_name      = "${var.cluster_name}-AuditResponse5xxCount"
  filter_pattern   = "{ ($.apiVersion = \"audit.k8s.io/v1\") && ($.stage = \"ResponseComplete\") && ($.responseStatus.code >= 500) }"
}

resource "aws_cloudwatch_log_group" "control_plane" {
  name              = "/aws/eks/${var.cluster_name}/cluster"
  log_group_class   = "STANDARD"
  retention_in_days = 90
  kms_key_id        = var.logs_kms_key_arn
}

resource "aws_cloudwatch_log_metric_filter" "audit_5xx" {
  name           = "${var.cluster_name}-audit-response-5xx"
  log_group_name = aws_cloudwatch_log_group.control_plane.name
  pattern        = local.filter_pattern

  metric_transformation {
    namespace     = local.metric_namespace
    name          = local.metric_name
    value         = "1"
    default_value = 0
    unit          = "Count"
  }
}

resource "aws_cloudwatch_metric_alarm" "audit_5xx" {
  alarm_name          = "${var.cluster_name}-audit-response-5xx"
  alarm_description   = "Example threshold for ingested audit ResponseComplete records with code>=500."
  namespace           = local.metric_namespace
  metric_name         = local.metric_name
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  datapoints_to_alarm = 1
  threshold           = 10
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "missing"
  actions_enabled     = false
  alarm_actions       = [var.sns_topic_arn]
}

resource "aws_cloudwatch_dashboard" "control_plane" {
  dashboard_name = "${var.cluster_name}-control-plane"
  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "log"
        x      = 0
        y      = 0
        width  = 24
        height = 6
        properties = {
          region = var.region
          title  = "Recorded audit 5xx responses per five minutes"
          view   = "timeSeries"
          query  = "SOURCE '${aws_cloudwatch_log_group.control_plane.name}' | fields @timestamp\n| filter apiVersion = \"audit.k8s.io/v1\" and stage = \"ResponseComplete\" and responseStatus.code >= 500\n| stats count(*) as recordedResponses by bin(5m)"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 24
        height = 6
        properties = {
          region  = var.region
          title   = "Metric filter: new ingested audit 5xx records"
          view    = "timeSeries"
          metrics = [[local.metric_namespace, local.metric_name]]
          period  = 300
          stat    = "Sum"
        }
      }
    ]
  })
}
```

このフィルターは、新たに取り込まれた audit ResponseComplete レコードのうち responseStatus.code>=500 のものを数えます。クラスター名を先頭につけたメトリクス名により、監査 JSON にない ClusterName ディメンションを創作せずにクラスターを区別します。フィルター、アラーム、メトリクスウィジェットは、同じ namespace/name とディメンションなしの設定を使います。ダッシュボードクエリは過去のレコードを対象にできますが、メトリクスフィルターは履歴を遡って補完しません。ここで数えるのは記録されたイベントであり、API エラー率でも重複排除済みリクエスト数でもありません。重複配信の可能性があります。

ログは届いたが一致するものがなかった場合、default_value の 0 が発行されます。ログが届かなければデータ欠落になることがあります。メトリクスフィルターは default value とディメンションを併用できません。このアラームはアクションを無効にして開始し、データ欠落時の扱いを明示し、例示的なしきい値を使っています。有効にする前に、新しいメトリクスデータポイント、権限、サブスクリプション、管理された配信テストを確認してください。

jsonencode を使うと、旧ダッシュボードコマンドで起きていたシェルのクォート破損を避けられます。代わりに CLI を使う場合は、--dashboard-body file://dashboard.json に有効な JSON ファイルを渡し、DashboardValidationMessages を確認してください。PutDashboard は既存の本文を置換するため、所有者のウィジェットと設定を保ちます。ローカルでの HCL/JSON 検証は AWS のフィルター/クエリエンジンの実行ではありません。

**KMS と保持期間:**

CloudWatch Logs は既定でログデータを暗号化します。カスタマー管理の対称 KMS キーを関連付けると、新たに取り込むデータの暗号化が変更されます。これは最初の暗号化レイヤーではなく、既存記録を再暗号化もしません。ロググループと同じリージョンのキーを使い、過去データが必要な間は古いキーと権限を保持し、キーの関連付け権限とログ読み取り権限を区別してください。関連付けを解除すると、新しいデータは既定の暗号化に戻ります。古いキーを無効化/削除すると、保持中のデータが読めなくなることがあります。

リージョンの Logs サービスにはキー使用権限が必要です。次はキー所有者が管理者/委任に関するステートメントを維持しつつ、既存ポリシーに統合するためのステートメント断片にすぎません。例示の識別子をすべて一貫して置き換えてください。完全な置換用キー ポリシーとして使わないでください。

```json
{
  "Sid": "AllowLogsServiceForOneGroup",
  "Effect": "Allow",
  "Principal": {
    "Service": "logs.us-west-2.amazonaws.com"
  },
  "Action": [
    "kms:Encrypt",
    "kms:Decrypt",
    "kms:ReEncrypt*",
    "kms:GenerateDataKey*",
    "kms:DescribeKey"
  ],
  "Resource": "*",
  "Condition": {
    "ArnEquals": {
      "kms:EncryptionContext:aws:logs:arn": "arn:aws:logs:us-west-2:123456789012:log-group:/aws/eks/my-cluster/cluster"
    }
  }
}
```

暗号化コンテキスト内のロググループ ARN には末尾の :* がありません。キーを関連付ける担当者には、文書化された Logs 権限と kms:DescribeKey が必要です。読み書きする呼び出し元には、リージョンの Logs サービスを介して、各操作に適した KMS 権限が必要です。キーのローテーションや短い削除待機期間を設定しても、過去データの復号アクセスを保持する必要はなくなりません。保持期間 90 は例であり、コンプライアンスや不変性を保証しません。

**読み取りアクセスの範囲を正しく限定する:**

次の例示的な ID ポリシーは、選択したグループとそのストリーム、および Logs 経由で1つのキーを復号する権限を許可します。キー ポリシーも対象プリンシパルを許可する必要があります。ログ管理やキー管理のアクションは許可しません。

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ReadAndQueryThisLogGroup",
      "Effect": "Allow",
      "Action": [
        "logs:DescribeLogStreams",
        "logs:FilterLogEvents",
        "logs:StartQuery",
        "logs:GetQueryResults"
      ],
      "Resource": "arn:aws:logs:us-west-2:123456789012:log-group:/aws/eks/my-cluster/cluster:*"
    },
    {
      "Sid": "ReadThisGroupStreams",
      "Effect": "Allow",
      "Action": "logs:GetLogEvents",
      "Resource": "arn:aws:logs:us-west-2:123456789012:log-group:/aws/eks/my-cluster/cluster:log-stream:*"
    },
    {
      "Sid": "DecryptThisGroupsDataViaLogs",
      "Effect": "Allow",
      "Action": "kms:Decrypt",
      "Resource": "arn:aws:kms:us-west-2:123456789012:key/11111111-2222-3333-4444-555555555555",
      "Condition": {
        "StringEquals": {
          "kms:ViaService": "logs.us-west-2.amazonaws.com"
        },
        "ArnEquals": {
          "kms:EncryptionContext:aws:logs:arn": "arn:aws:logs:us-west-2:123456789012:log-group:/aws/eks/my-cluster/cluster"
        }
      }
    }
  ]
}
```

現在の AWS 認可ドキュメントでは、StartQuery と GetQueryResults をロググループ単位で制限できます。古い前提に基づいて Resource:* に広げないでください。DescribeLogStreams と FilterLogEvents はグループに対するアクションで、GetLogEvents はストリームに対するアクションです。AWS の LogGroup ARN 形式は、ほとんどの IAM アクションで :* を含みます。一方 logGroupArn と暗号化コンテキスト/タグ付けでは含みません。コンソール/検出ワークフローには追加の読み取りアクションが必要な場合があります。DescribeLogGroups はリソースレベル ARN をサポートしない、別途範囲を指定する権限であり、上記ポリシーから暗黙に付与されません。

この監査ではクラスターのログ設定、ログ保持、キー ポリシー、メトリクスフィルター、ダッシュボード、アラーム、クラウドクエリを変更/実行していません。参考資料: [CloudWatch メトリクスフィルター](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/MonitoringLogData.html)、[LogGroup ARN 形式](https://docs.aws.amazon.com/AmazonCloudWatchLogs/latest/APIReference/API_LogGroup.html)、[Logs IAM アクション](https://docs.aws.amazon.com/service-authorization/latest/reference/list_logs.html)、[KMS による Logs の暗号化](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/encrypt-log-data-kms.html)。

</details>

### 6. Amazon EKS のコスト最適化を最もよく支援するモニタリング方針はどれですか？

- A. 利用目的に関係なく、利用可能なすべてのメトリクスを収集する。
- B. リソース使用量、請求の配賦、所有者がレビューした削減候補を組み合わせる。
- C. 支出を調べずにパフォーマンスだけを監視する。
- D. 月末の請求書だけを確認する。

<details>
<summary>回答を表示</summary>

**回答: B. リソース使用量、請求の配賦、所有者がレビューした削減候補を組み合わせる。**

**解説:** CPU、メモリ、ストレージ、リクエスト、制限、ワークロードの推移を配賦コストと比較します。異常や予算との差分をリソース所有者と調査してください。これらのシグナルは改善機会を見つける手掛かりであり、節約を保証したり、リソースを削除してよいと決めたりするものではありません。

**リソース効率とコスト配賦**

原文のガイドにある kube-prometheus-stack のインストール、kube-state-metrics、kubelet ServiceMonitor を、検証済み serving certificate とともに再利用してください。cAdvisor は kubelet の HTTPS metrics ポートにある `/metrics/cadvisor` を使います。`cadvisor` という別の Service ポートではありません。スクレイプを動かすために重複する monitor を追加したり、TLS 検証を無効化したりしないでください。

次の CPU/メモリ式が返すのは**コンテナごとの使用量/リクエスト比**であり、ノード容量の使用率や金額ではありません。リクエストがゼロ/欠落している場合、比率は出ず、使用量ゼロを意味しません。`max` は列挙した ID で重複したスクレイプコピーを除去します。コピーが本当に同じワークロードを表すことを確認してください。この例は1つのクラスター内の Prometheus を対象にします。共有バックエンドでは、両方のメトリクスファミリーに一貫したクラスターラベルが必要です。Pod 名の再利用やコンテナ再起動にも注意して時間範囲を解釈します。これらのコンテナメトリクスでは、Pod レベルのリソース、init container、Pod overhead に対するスケジューラーの予約全体は分かりません。

```promql
max by (cluster, namespace, pod, container) (
  rate(container_cpu_usage_seconds_total{job="kubelet",metrics_path="/metrics/cadvisor",namespace!="",container!="",container!="POD"}[5m])
)
/ on (cluster, namespace, pod, container)
(
  max by (cluster, namespace, pod, container) (
    kube_pod_container_resource_requests{job="kube-state-metrics",resource="cpu",unit="core",container!=""}
  ) > 0
)
```

```promql
max by (cluster, namespace, pod, container) (
  container_memory_working_set_bytes{job="kubelet",metrics_path="/metrics/cadvisor",namespace!="",container!="",container!="POD"}
)
/ on (cluster, namespace, pod, container)
(
  max by (cluster, namespace, pod, container) (
    kube_pod_container_resource_requests{job="kube-state-metrics",resource="memory",unit="byte",container!=""}
  ) > 0
)
```

既存の Prometheus データソースとこれらのクエリを使い、Grafana に2つのパネルを作成します。ダッシュボード名を **リソース使用量とリクエストの比較** とし、比率/パーセンテージ単位を設定して、クラスター、namespace、Pod、container の ID を保持してください。未定義の `cost-dashboard.json` を含む ConfigMap だけでは、利用可能なダッシュボードは作られません。原文の Grafana sidecar を使う場合、レビュー済み JSON ダッシュボードをプロビジョニングするには、設定済みの `grafana_dashboard: "1"` ラベルも必要です。

**OpenCost または Kubecost**

原文の既存 Prometheus を使って OpenCost を新たに評価する場合は、次を `opencost-values.yaml` として保存します。確認済みチャートは **2.5.31**、アプリケーションは **1.121.2** です。実際のクラスター ID と Prometheus URL を設定してください。ServiceMonitor のラベルは Prometheus selector と一致させ、namespace 選択では `opencost` namespace を許可します。Prometheus/node exporter を追加でインストールするものではありません。

```yaml
service:
  type: ClusterIP
opencost:
  exporter:
    defaultClusterId: my-cluster
  prometheus:
    internal:
      enabled: false
    external:
      enabled: true
      url: http://monitoring-kube-prometheus-prometheus.monitoring.svc:9090
  metrics:
    serviceMonitor:
      enabled: true
      additionalLabels:
        release: monitoring
  cloudCost:
    enabled: false
  mcp:
    enabled: false
  ui:
    enabled: true
    ingress:
      enabled: false
```

```bash
helm repo add opencost https://opencost.github.io/opencost-helm-chart
helm repo update opencost
helm template opencost opencost/opencost --version 2.5.31 \
  --namespace opencost -f opencost-values.yaml > opencost-rendered.yaml
# After reviewing RBAC, images, resources, selectors, and network access:
helm install opencost opencost/opencost --version 2.5.31 \
  --namespace opencost --create-namespace -f opencost-values.yaml
kubectl -n opencost port-forward --address 127.0.0.1 svc/opencost 9090:9090
```

port-forward 実行中に `http://localhost:9090` を開きます。この基本構成では Exporter のキャッシュを一時領域に置き、Cloud Cost の取り込みと MCP を無効にし、ClusterIP Service のみを公開します。共有利用の前に、永続化、サイズ、認証/ネットワークアクセス、RBAC、スクレイプの健全性を確認してください。ClusterIP はテナント認可の境界ではありません。オンデマンド価格の見積もりは、実際の請求、割引、Spot 価格、クレジット、共通コスト、ストレージ、ネットワーク料金と照合する必要があります。AWS 請求との連携は別設定です。サポートされる AWS service-account/default SDK 認証に長期アクセスキーを埋め込む必要はありません。

Kubecost は別の選択肢です。確認済みの **3.3.1** チャート `kubecost/kubecost` は `https://kubecost.github.io/kubecost/` にあります。旧 `cost-analyzer` リポジトリと Prometheus 用 2.x の値は、3.x のインストール手順ではありません。3.x は ClickHouse と直接 finops-agent による収集を使います。インストール/アップグレード前に、ライセンス、ストレージ、Kubernetes 互換性、文書化された 2.x からの移行を確認してください。[FinOps プラットフォームのガイド](../../ops/13-finops-cost-platform.md)と [Kubecost チャートのドキュメント](https://github.com/kubecost/cost-analyzer-helm-chart)を参照してください。

**ラベル、請求タグ、カテゴリ**

namespace ラベルは Kubernetes 側のグループ化に役立ちます。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: team-a
  labels:
    team: team-a
    cost-center: cc-123
    environment: production
```

ただし、EC2/EBS リソースに AWS タグを自動付与したり、AWS 請求タグを有効化したりはしません。請求の所有者が実際の AWS リソースタグを付け、利用可能なコスト配賦キーを有効化する必要があります。請求処理の遅延を見込み、Cost Explorer/CUR に表示されたことを確認してください。AWS の split cost allocation は、EKS Pod レベルのレコードと `aws:eks:namespace` など AWS が生成する属性を作る、別途オプトインする経路です。すべての namespace ラベルを EC2 タグにするものではありません。データソースの前提条件とレポート量の増加を確認してください。

コスト配賦タグのバックフィルで最大12か月分を補完できるのは、**その期間にリソースへ実際にタグが付いていた場合**です。存在しなかった過去のタグを作り出すことはできません。Cost Category はレビュー済みルールで請求レコードを分類するもので、ダッシュボードではありません。CLI の作成操作は `aws ce create-cost-category-definition` であり、`create-cost-category` ではありません。請求データセットに実際に存在するキー/値を使い、保存済み Cost Explorer レポートやダッシュボードは別途設定してください。

**未接続ボリュームの読み取り専用インベントリ**

意図したアカウント/リージョンと既存の所有者タグでのみ、次を実行します。AWS CLI のページネーションは有効のままで、JSON の候補リストを出力します。タグの構文制限は意図したものです。実際のタグにほかの文字が含まれる場合は JSON フィルターを調整してください。

```bash
set -euo pipefail
: "${AWS_REGION:?Set the reviewed Region}"
: "${EXPECTED_ACCOUNT_ID:?Set the reviewed 12-digit account ID}"
: "${OWNER_TAG_KEY:?Set an existing ownership tag key}"
: "${OWNER_TAG_VALUE:?Set its exact value}"
[[ "$EXPECTED_ACCOUNT_ID" =~ ^[0-9]{12}$ ]]
# This example accepts a restricted literal subset, excluding wildcards/shorthand separators.
[[ "$OWNER_TAG_KEY" =~ ^[a-zA-Z0-9_./:@+-]+$ ]]
[[ "$OWNER_TAG_VALUE" =~ ^[a-zA-Z0-9_./:@+-]+$ ]]
actual_account=$(aws sts get-caller-identity --region "$AWS_REGION" \
  --query Account --output text --no-cli-pager)
[[ "$actual_account" == "$EXPECTED_ACCOUNT_ID" ]] || {
  echo "Account mismatch" >&2
  exit 1
}
aws ec2 describe-volumes --region "$AWS_REGION" --page-size 100 \
  --filters Name=status,Values=available \
    "Name=tag:$OWNER_TAG_KEY,Values=$OWNER_TAG_VALUE" \
  --query 'Volumes[].{id:VolumeId,zone:AvailabilityZone,sizeGiB:Size,created:CreateTime,state:State}' \
  --output json --no-cli-pager
```

`available` が意味するのは現時点で未接続ということであり、未使用や削除して安全という意味ではありません。作成時刻は最終使用時刻ではありません。所有者と PV/PVC、reclaim policy、保留中のワークロード、バックアップ、スナップショット、災害復旧要件を確認してください。同様に、CPU/メモリが低いこと (任意の 5% しきい値を含む) は、Pod やロードバランサーが不要という証拠ではありません。代表的な履歴とアプリケーション/SLO シグナルを使い、メトリクス欠落時に「アイドル Pod」を空の結果で代用しないでください。

**予算の例**

この独立した Terraform 例では、実際に有効化済みの請求タグと承認済みの通知先を使います。**月額 1,000 USD の上限と 80% のアラート**は例示の設定であり、実際のコストではありません。競合する所有者を作らず、既存予算をインポート/照合してください。コスト算出基準とタグのカバレッジを検証します。タグフィルターはタグなし/共有コストを除外する可能性があります。この例を適用すると、実際の通知設定が作成されます。

```hcl
terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "= 6.69.1"
    }
  }
}

variable "account_id" {
  type = string
}

variable "region" {
  type = string
}

variable "budget_name" {
  type = string
}

variable "activated_tag_key" {
  type = string
}

variable "tag_value" {
  type = string
}

variable "notification_email" {
  type        = string
  description = "Approved budget owner; applying this example configures real email notifications."
}

provider "aws" {
  region              = var.region
  allowed_account_ids = [var.account_id]
}

resource "aws_budgets_budget" "eks_monthly" {
  account_id   = var.account_id
  name         = var.budget_name
  budget_type  = "COST"
  limit_amount = "1000"
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  cost_filter {
    name   = "TagKeyValue"
    values = [join("$", [var.activated_tag_key, var.tag_value])]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.notification_email]
  }
}
```

Budgets は処理済み請求データを使い、支出に強制的な上限を設けるものではありません。Budget Actions は IAM/SCP 制御を適用したり、対応する EC2/RDS インスタンスを対象にしたりできますが、別途権限と運用レビューが必要です。上のリソース効率ダッシュボードは請求ダッシュボードではありません。

VPA の推奨値とピーク時/SLO 履歴を確認し、HPA とノードスケーリングを調整してください。Karpenter/Cluster Autoscaler や Spot によりコストが下がるのは、ワークロード、中断、キャパシティ、disruption の制約に合う場合だけです。request を小さくするだけでは、プロビジョニング済みキャパシティや料金が変わらない限り請求額は減りません。所有者との定期レビューで合意した施策と測定結果を追跡します。

他の選択肢では、このフィードバックループを作れません。すべて収集するとテレメトリコストとノイズが増え、パフォーマンスだけを見ても支出は分からず、月末の請求確認では調査が遅れます。

**主な参考資料:** [OpenCost のインストール](https://opencost.io/docs/installation/helm)、[AWS タグの有効化](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/activating-tags.html)、[タグのバックフィル](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/cost-allocation-backfill.html)、[split cost allocation](https://docs.aws.amazon.com/cur/latest/userguide/split-cost-allocation-data.html)、[Budget Actions](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-controls.html)。

</details>
