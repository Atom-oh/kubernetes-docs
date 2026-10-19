# Amazon EKS 高度なデバッグクイズ

> **最終更新日**: 2026年9月12日

[ソース章](../../eks/11-eks-advanced-debugging.md)では、現在のAPI、対象範囲、安全上の前提を定義しています。例は実稼働クラスターやベンチマークの結果ではありません。このレビューではクラウドやクラスターに対する操作を実行していません。

このクイズでは、インシデント対応、コントロールプレーンのデバッグ、ノードのトラブルシューティング、kubectl debug、PromQLクエリ、オブザーバビリティなど、Amazon EKSの高度なデバッグ手法に関する理解を確認します。

## クイズの概要
- インシデント対応プロセス
- EKSコントロールプレーンのデバッグ
- ノードとkubeletのトラブルシューティング
- kubectl debugコマンドの使用
- PromQLクエリとメトリクス分析
- 分散トレーシングとログ分析

## 選択問題

### 1. 有効化したEKSコントロールプレーン監査ログは、通常どこで検索しますか？

A. 顧客が管理する/var/log/kubernetesディレクトリ
B. Amazon CloudWatch Logs
C. AWS管理etcdへの直接アクセス
D. AWS管理コントロールプレーンPodに対するkubectl logs

<details>
<summary>回答を表示</summary>

**回答: B. Amazon CloudWatch Logs**

正しいリージョンとアカウントで`/aws/eks/<cluster-name>/cluster`を使います。利用できるログ種別はapi、audit、authenticator、controllerManager、schedulerの5つで、任意に有効化する必要があります。有効化しても過去のログは復元されません。403は認可拒否を示しますが、それだけでIAM認証の失敗とは限りません。Logs Insights QLのクエリは個別に実行し、時間範囲を明示してください。

```bash
# Read-only: confirm logging is enabled before searching the owned group.
: "${AWS_REGION:?}"; : "${CLUSTER_NAME:?}"
aws eks describe-cluster --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --query cluster.logging
```
```text
fields @timestamp, user.username, verb, objectRef.resource, responseStatus.code
| filter @logStream like /kube-apiserver-audit/
| filter responseStatus.code = 403
| sort @timestamp desc
| limit 100
```

</details>

### 2. Podの別コピーを作成するkubectl debugフラグはどれですか？

A. --attach
B. --copy-to
C. --ephemeral
D. --sidecar

<details>
<summary>回答を表示</summary>

**回答: B. --copy-to**

前の問題では、元のPodにコンテナを追加する操作を誤って説明していました。--copy-toは別のPodを作成します。既存Podをエフェメラルコンテナでデバッグする際、このフラグや--ephemeralフラグは使いません。ランタイムが対応している場合、--targetでプロセス名前空間を指定します。コピーにはServiceAccount、環境変数やSecretへの参照、ボリューム、その他の通常コンテナが引き継がれる場合があります。initコンテナを無効にしてコマンドを1つ変更しても、データから隔離された複製にはなりません。

```bash
# MUTATION: separate reviewed reproduction Pod, not an ephemeral container in the original.
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${POD_NAME:?}"; : "${CONTAINER_NAME:?}"
: "${DEBUG_POD_NAME:?Choose a new owned name}"; : "${DEBUG_IMAGE:?Reviewed image providing sleep}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" debug "$POD_NAME" \
  --copy-to="$DEBUG_POD_NAME" --container="$CONTAINER_NAME" --image="$DEBUG_IMAGE" \
  --keep-init-containers=false --share-processes=true --profile=general -- sleep 3600
```

</details>

### 3. NotReadyノードの状態とハートビートを確認した後、どの証拠が有用ですか？

A. 無関係なアプリケーションログのみ
B. 該当するkubelet/ランタイムの状態とログを、ネットワーク/EC2の証拠と照合する
C. AWS管理etcdを直接操作する
D. CoreDNSログだけを証拠とする

<details>
<summary>回答を表示</summary>

**回答: B. 該当するkubelet/ランタイムの状態とログを、ネットワーク/EC2の証拠と照合する**

以前の「最も一般的な原因」という主張を裏付ける測定頻度はありません。Ready=False、ハートビートの喪失/Unknown、リソース圧迫、インスタンス停止はそれぞれ異なるシグナルです。対応OSのノードでは承認済みのホストアクセスを使い、Auto ModeではNodeDiagnosticまたは文書化されたデバッグ手順を利用します。SSHやsystemctlを常に使えるとは限りません。別途レビューした再起動や置換を行う前に、範囲を限定してログを収集してください。

```bash
# Read-only Kubernetes evidence first; no automatic kubelet restart.
: "${KUBE_CONTEXT:?}"; : "${NODE_NAME:?}"
kubectl --context "$KUBE_CONTEXT" get node "$NODE_NAME" -o json | jq '{
  uid:.metadata.uid,providerID:.spec.providerID,nodeInfo:.status.nodeInfo,conditions:.status.conditions
}'
```

</details>

### 4. 正のCPU limitに対するコンテナのCPU使用率を測る計算はどれですか？

A. 仮定上のcpu_usageメトリクスが80を超える
B. 分母を使わず、CPU秒/秒が0.8を超える
C. CPUコア数で表した使用量 / 対応する正のCPU limit（コア数）
D. 仮定上のcontainer_cpu_percentメトリクス

<details>
<summary>回答を表示</summary>

**回答: C. CPUコア数で表した使用量 / 対応する正のCPU limit（コア数）**

rate(cpu_usage_seconds_total)はCPUコア数であり、それだけではパーセンテージになりません。クラスターの対象範囲、namespace、Pod、containerで対応づけ、正の値を持つlimitを使います。limitが未設定または存在しないコンテナの使用率は0%ではありません。HPAの使用率は通常requestsに対する比率で、別の計算です。次のクエリは、ソース章で定めた単一クラスター/ラベル/スクレイプの前提に従い、0.8を超える比率を示します。

```promql
(sum by (namespace,pod,container) (
  rate(container_cpu_usage_seconds_total{namespace="diagnostics-example",container!="",container!="POD"}[5m])
)
/ on (namespace,pod,container)
max by (namespace,pod,container) (
  kube_pod_container_resource_limits{namespace="diagnostics-example",resource="cpu",unit="core"} > 0
)) > 0.8
```
```promql
(max by (namespace,pod,container) (container_memory_working_set_bytes{namespace="diagnostics-example",container!="",container!="POD"})
/ on (namespace,pod,container)
max by (namespace,pod,container) (kube_pod_container_resource_limits{namespace="diagnostics-example",resource="memory",unit="byte"} > 0)) > 0.8
```

</details>

### 5. EKS管理クラスターでノード間ネットワークを顧客が診断する際、通常使わないツールはどれですか？

A. 承認されたキャプチャでのtcpdump
B. 承認済みキャプチャファイルを使うWireshark
C. ワークロードから実行する範囲限定のcurl/DNSテスト
D. AWS管理etcdエンドポイントに対するetcdctl

<details>
<summary>回答を表示</summary>

**回答: D. AWS管理etcdエンドポイントに対するetcdctl**

顧客にAWS管理etcdの直接エンドポイントは提供されません。ただし、セルフマネージドetcdシステムのネットワーク診断にetcdctlが使える場合まで否定するものではありません。パケットキャプチャには適切な権限/ホストコンテキスト、範囲制限、機密データの安全な取り扱いが必要です。新しいデバッグPodは、障害が起きているワークロードとポリシーやDNS経路が異なる場合があります。スループットのカウンターはレイテンシの測定値ではありません。

```bash
# Deliberate bounded request from an owned workload with curl installed.
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${POD_NAME:?}"; : "${CONTAINER_NAME:?}"
: "${HEALTH_URL:?Set a reviewed safe health URL}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$POD_NAME" -c "$CONTAINER_NAME" \
  -- curl --silent --show-error --connect-timeout 5 --max-time 10 \
  --output /dev/null --write-out 'HTTP status: %{http_code}\n' "$HEALTH_URL"
```

</details>

### 6. すべてのしきい値を単純に下げずに検知の遅れを減らすには、どの方法が適切ですか？

A. 手動での観察だけを増やす
B. すべてのメトリクスに可能な限り低いしきい値を設定する
C. 実測に基づく適切なアラート、カバレッジ確認、エスカレーション
D. 保持期間だけを延長する

<details>
<summary>回答を表示</summary>

**回答: C. 実測に基づく適切なアラート、カバレッジ確認、エスカレーション**

実際のSLOと障害モードに合わせて調整します。しきい値を低くしすぎるとアラート疲れを招きます。以下のHTTPカウンターとステータスラベルには、アプリケーション側の計装が必要です。リクエスト数の分母が0または欠損している場合も、正常の証拠にはなりません。すべての再起動をクラッシュループとみなさず、CrashLoopBackOffの待機理由を確認します。Prometheusでルール/namespaceが選択されていることと、通知の配送は別々に確認してください。ここではMTTDの結果を測定していません。

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: reviewed-quiz-alerts
  namespace: monitoring
  labels:
    release: REPLACE_WITH_SELECTED_PROMETHEUS_RELEASE
spec:
  groups:
  - name: reviewed-quiz-alerts
    rules:
    - alert: HighErrorRate
      expr: "(\n  sum(rate(http_requests_total{namespace=\"diagnostics-example\",job=\"\
        owned-app\",status=~\"5..\"}[5m]))\n  / sum(rate(http_requests_total{namespace=\"\
        diagnostics-example\",job=\"owned-app\"}[5m]))\n) > 0.05\nand on() (sum(rate(http_requests_total{namespace=\"\
        diagnostics-example\",job=\"owned-app\"}[5m])) > 0)"
      for: 2m
      labels:
        severity: critical
    - alert: PodCrashLooping
      expr: max by (namespace,pod,container) (kube_pod_container_status_waiting_reason{namespace="diagnostics-example",reason="CrashLoopBackOff"}
        == 1)
      for: 5m
      labels:
        severity: warning
```

</details>

### 7. ノード上に診断用Podを作成するコマンド形式はどれですか？

A. `kubectl debug node/<node-name> --image=<reviewed-image>`
B. `kubectl exec node/<node-name> -- sh`
C. `kubectl attach node/<node-name>`
D. `kubectl run debug --node=<node-name>`

<details>
<summary>回答を表示</summary>

**回答: A. `kubectl debug node/<node-name> --image=<reviewed-image>`**

テスト済みのgeneralプロファイルは/hostをマウントし、ホスト名前空間を使いますが、privilegedではありません。明示的なsysadminプロファイルはより広い権限を与えます。chroot/nsenter/ツール/SELinuxの挙動はプラットフォームと権限に左右されます。Podの作成は受動的な調査ではなく変更操作です。kubelet/ランタイムに障害があるとPodを起動できない場合があります。作成した名前/UIDを記録し、レビュー済みのクリーンアップ手順に従ってください。

```bash
# MUTATION: creates a node diagnostic Pod; general is not automatically privileged.
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${NODE_NAME:?}"; : "${NODE_DEBUG_IMAGE:?Reviewed image}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" debug "node/$NODE_NAME" \
  --image="$NODE_DEBUG_IMAGE" --profile=general --attach=false -- true
```

</details>

### 8. 分散トレーシングにおけるSpanとは何ですか？

A. エンドツーエンドのリクエスト全体の所要時間だけ
B. 時間情報と関連メタデータを持つ作業単位
C. ネットワークレイテンシだけ
D. ログのタイムスタンプ

<details>
<summary>回答を表示</summary>

**回答: B. 時間情報と関連メタデータを持つ作業単位**

SpanはHTTP呼び出し、データベース操作などの作業単位を表します。Trace IDでSpanを関連づけ、親子関係やリンクで関連する処理を表現します。実際に何が見えるかは、コンテキスト伝播とサンプリングに左右されます。Baggageは伝播されるコンテキストであり、自動的にSpan属性になるわけではありません。秘密情報を含めないでください。以下のJSONは人が読むための例であり、OTLPのワイヤーペイロードでも測定済みリクエストでもありません。Collector設定には、ソース章の現在のv1beta1オブジェクト形式の例と、対応バックエンド/OTLP経路を使ってください。以前のjaeger exporter/14250の手順は現在の推奨ではありません。

```json
{
  "exampleOnly": true,
  "trace_id": "0123456789abcdef0123456789abcdef",
  "span_id": "0123456789abcdef",
  "parent_span_id": "fedcba9876543210",
  "name": "GET /api/products",
  "kind": "SERVER",
  "duration_ms": 85
}
```

</details>

### 9. DeploymentベースのCoreDNSでDNSエラーを調査する際、どの証拠が有用ですか？

A. 対象を絞ったCoreDNS Podのログ/状態と、ワークロードのリゾルバー確認
B. describe service kubernetesだけ
C. AWSクラスターのメタデータだけ
D. 古いEndpointsリストだけ

<details>
<summary>回答を表示</summary>

**回答: A. 対象を絞ったCoreDNS Podのログ/状態と、ワークロードのリゾルバー確認**

すべてのDNSクエリがデフォルトでログに記録されるわけではありません。リゾルバー設定、Pod/Serviceの状態、上流エラーを照合してください。完全なAuto ModeではノードのシステムDNSを使います。混在クラスターではAuto Mode以外のノード向けにDeploymentが残ります。ツールが利用できる場合は、無関係なdefault namespaceの古いイメージのPodではなく、該当するPod/containerからテストします。nslookupのデバッグフラグはツールごとに異なり、共通ではありません。

```bash
# Deployment-based CoreDNS only; use the Auto Mode path when applicable.
kubectl --context "$KUBE_CONTEXT" -n kube-system get pods -l k8s-app=kube-dns -o wide
kubectl --context "$KUBE_CONTEXT" -n kube-system logs -l k8s-app=kube-dns --since=15m --tail=100
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$POD_NAME" -c "$CONTAINER_NAME" \
  -- nslookup kubernetes.default.svc.cluster.local.
```

</details>

### 10. resource-metrics APIからPodの直近のリソースサンプルを表示するコマンドはどれですか？

A. kubectl describe pod
B. kubectl top pods
C. kubectl get pods -o wide
D. kubectl logs

<details>
<summary>回答を表示</summary>

**回答: B. kubectl top pods**

kubectl topには、一般にMetrics Serverなどの正常なmetrics.k8s.ioプロバイダーが必要です。瞬間値や履歴ではなく、直近にサンプリングされたCPU/メモリデータを表示します。メトリクス欠損は使用量0を意味しません。requests/limitsは別途比較し、履歴分析には監視バックエンドを使います。

```bash
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" top pods --containers
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" top pods --sort-by=memory
kubectl --context "$KUBE_CONTEXT" top nodes
```

</details>

## 短答問題

### 1. 有効化済みEKSコントロールプレーンログのCloudWatch Logsグループのパターンは何ですか？

<details>
<summary>回答を表示</summary>

**回答:** `/aws/eks/<cluster-name>/cluster`。クラスターでログ種別を有効にしておく必要があります。有効化しても過去のイベントは復元されません。正しいアカウント、リージョン、ロググループ、時間範囲を選択してください。次のLogs Insights QLクエリは個別に実行します。監査ログに記録されたユーザー名は識別子であり、短縮されたIAMロール名とは限りません。

```sql
fields @timestamp, @message
| filter @logStream like /kube-apiserver/
| filter @logStream not like /kube-apiserver-audit/
| filter @message like /error|Error|ERROR/
| sort @timestamp desc
| limit 50
```
```sql
fields @timestamp, user.username, verb, objectRef.resource, responseStatus.code
| filter @logStream like /kube-apiserver-audit/
| filter user.username = "REPLACE_WITH_EXACT_AUDIT_USERNAME"
| sort @timestamp desc
| limit 100
```

</details>

### 2. 現在のKubernetesで、古いEphemeralContainers feature gateを有効にする必要がありますか？

<details>
<summary>回答を表示</summary>

**回答:** いいえ。`EphemeralContainers`は過去のfeature gateです。この機能は1.23でベータ、1.25で安定版になりました。現在のバージョンでは、代わりに`pods/ephemeralcontainers`に対するRBAC、admission policy、イメージアクセス、ランタイム対応を確認します。追加するとPodが変更され、そのエントリは後から変更も削除もできません。`--target`によるプロセス可視性はランタイムの対応状況に依存します。作成手順にはソース章の明示的にレビュー済みの方法を使ってください。以下のコマンドはメタデータの一覧表示だけを行います。

```bash
# Read-only inventory; adding an ephemeral container is a separate mutation.
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${POD_NAME:?}"
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n "$NAMESPACE" \
  get pod "$POD_NAME" -o json | jq '{
    uid:.metadata.uid,
    ephemeralContainers:[.spec.ephemeralContainers[]? | {name,image,targetContainerName}],
    ephemeralStatuses:.status.ephemeralContainerStatuses
  }'
```

</details>

### 3. PromQLのrate()とirate()はどのように異なりますか？

<details>
<summary>回答を表示</summary>

`rate()`は選択した範囲でのカウンター増加量を1秒あたりに換算し、カウンターのリセットを考慮して範囲の境界まで外挿します。`irate()`は同じ範囲内の直近2サンプルのみを使い、リセットを考慮します。どちらも十分なサンプルが必要で、サンプリングされなかった急増は捉えられません。系列ごとのリセットを検出できるよう、集約する前に関数を適用します。通常、アラートには`rate()`を使います。`irate()`は変動の大きいカウンターの調査に役立つことがありますが、インシデントの検知を必ず改善するものではありません。どちらもカウンター用の関数で、一般的なゲージの変化率ではありません。最初の2例はアプリケーションで計装したカウンターを使い、最後の例はCPUコア数を返します（パーセンテージではありません）。単一クラスターとソース章のラベル/スクレイプ条件を前提とします。

```promql
sum by (namespace,service) (
  rate(http_requests_total{namespace="diagnostics-example",service="api-gateway"}[5m])
)
```
```promql
sum by (namespace,service) (
  irate(http_requests_total{namespace="diagnostics-example",service="api-gateway"}[5m])
)
```
```promql
rate(container_cpu_usage_seconds_total{namespace="diagnostics-example",container!="",container!="POD"}[5m])
```

</details>

### 4. kubectl debug nodeはホストファイルシステムをどこにマウントし、何が可能になりますか？

<details>
<summary>回答を表示</summary>

**回答:** `/host`。`general`プロファイルは自動的にprivilegedになるわけではありません。ホストをマウントしても、`chroot`、`systemctl`、保護されたホストファイルの読み取りが必ずできるとは限りません。イメージに必要なツールが含まれている必要があり、admission、capability、SELinux、OS、ノードの健全性も影響します。明示的にprivilegedな`sysadmin`プロファイルには、別途承認された診断手順が必要です。Auto Modeでは文書化されたノードデバッグ手順が利用できますが、直接SSHや通常のホストパスを常に使えるわけではありません。Podの作成とクリーンアップには選択問題7とソース章を参照し、kubeconfigや認証情報のファイルを表示しないでください。

</details>

### 5. 二重計上を避けながら、インシデントの復旧時間をどのように分解できますか？

<details>
<summary>回答を表示</summary>

「MTTR」を使う前に、測定方法を決めます。検知時点から測るチームもあれば、インシデント開始時点から測るチームもあり、resolve/repair/recoverの意味も異なります。ここでは`t0 = service impact starts`、`t1 = detected`、`t2 = actionable diagnosis`、`t3 = service restored`とします。重複しない時間区間は、検知`t1−t0`、調査`t2−t1`、復旧`t3−t2`で、その合計は`t3−t0`です。同じ定義を使って同じインシデント群を平均すれば、この合計関係は保たれます。1件の45分は所要時間であり、実測された平均ではありません。根本原因の確認やフォローアップが復旧後に行われる場合もあるため、すべてのインシデントを無理にこの順序に当てはめないでください。監視範囲、ランブック、検証済みの復旧手順を改善し、実際の結果を測定します。

</details>

## 実践演習

### 1. 5分間の再起動増加数が2回以上と推定されるproductionコンテナを見つけてください。

<details>
<summary>回答を表示</summary>

1つのクラスターと、`namespace`、`pod`、`uid`、`container`ラベルを持つkube-state-metricsを使います。`increase()`はカウンターのリセットを考慮して外挿するため、結果が小数になる場合があり、完全なイベント台帳ではありません。`max`は同一のexporterレプリカを合算しないようにしますが、あらゆるHA構成で重複を解消する方法ではありません。スクレイプの健全性とバックエンドの重複排除を確認してください。同じ名前で置き換えられたPodを区別できるよう、Pod UIDを保持します。以下のバリエーションは、累積回数が5より大きいもの、1時間のコンテナ別増加数を合計した上位10個の**Pod**、グラフ用の秒あたり再起動率を示します。系列の欠損は再起動0回を意味しません。

```promql
max by (namespace,pod,uid,container) (
  increase(kube_pod_container_status_restarts_total{namespace="production"}[5m])
) >= 2
```
```promql
max by (namespace,pod,uid,container) (
  kube_pod_container_status_restarts_total{namespace="production"}
) > 5
```
```promql
topk(10,
  sum by (namespace,pod,uid) (
    max by (namespace,pod,uid,container) (
      increase(kube_pod_container_status_restarts_total{namespace="production"}[1h])
    )
  )
)
```
```promql
max by (namespace,pod,uid,container) (
  rate(kube_pod_container_status_restarts_total{namespace="production"}[5m])
)
```

</details>

### 2. ワークロードを変更する前に、CrashLoopBackOffのコンテナに関する範囲を絞った証拠を集めてください。

<details>
<summary>回答を表示</summary>

`CrashLoopBackOff`はコンテナの待機理由であり、Podのphaseは`Running`のままの場合があります。実際のcontext、namespace、Pod、障害コンテナを選びます。ログ収集前に現在のUIDを確認してください。名前を指定するログ取得とUID確認は原子的ではありません。まず以下のように範囲を限定して調査し、終了コード/理由、アプリケーションエラー、設定参照、ノードの圧迫、依存先の障害を調べます。startup/liveness probeの失敗はコンテナを再起動させることがありますが、readinessの失敗だけでは再起動しません。Secretや設定データが欠けていると、クラッシュループではなくコンテナ作成自体を妨げることもあります。すべての環境変数、Secret値、設定ファイルを出力しないでください。

```bash
# Read-only, bounded evidence for one owned Pod and container.
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${POD_NAME:?}"; : "${CONTAINER_NAME:?}"
k=(kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n "$NAMESPACE")
pod_state=$("${k[@]}" get pod "$POD_NAME" -o json | jq '{
  uid:.metadata.uid, phase:.status.phase, conditions:.status.conditions,
  containers:[.status.containerStatuses[]? | {name,ready,restartCount,state,lastState}],
  initContainers:[.status.initContainerStatuses[]? | {name,ready,restartCount,state,lastState}]
}')
printf '%s\n' "$pod_state"
pod_uid=$(jq -er '.uid' <<<"$pod_state")
"${k[@]}" get events --field-selector "involvedObject.uid=$pod_uid" \
  --sort-by='.metadata.creationTimestamp'
# These logs can contain sensitive application data; keep the terminal/evidence private.
# A missing previous instance/log is an evidence gap, not an empty successful result.
if ! "${k[@]}" logs "$POD_NAME" -c "$CONTAINER_NAME" --previous \
  --tail=100 --limit-bytes=65536 --timestamps; then
  printf '%s\n' 'Previous container log unavailable; retain this limitation.' >&2
fi
"${k[@]}" logs "$POD_NAME" -c "$CONTAINER_NAME" \
  --since=15m --tail=100 --limit-bytes=65536 --timestamps
```

再現が必要な場合は、コピーの識別情報、Secret参照、ボリューム、他のコンテナ、外部への副作用を確認してから、選択問題2/ソース章の手順を使います。イメージ/コマンドを1つ差し替え、initコンテナを無効にしても、他のリソースから隔離されるわけではありません。適切な環境でサニタイズした再現を優先し、新しい名前/UIDを記録して、クリーンアップを別途レビューします。debug用コンテナがsleep状態になっただけでは、アプリケーションが修復された証拠になりません。

</details>

### 3. 過去1時間のEKS監査ログから403イベントを検索し、クエリ完了を確認してください。

<details>
<summary>回答を表示</summary>

監査ログは事前に有効化されている必要があります。対象アカウント/リージョンと`/aws/eks/<cluster-name>/cluster`を選び、コンソールでは過去1時間の時間範囲を指定します。各ブロックは個別のLogs Insights QLクエリです。キーの順番を固定して解析せず、検出済みのJSONフィールドを使います。これは監査イベントの件数であり、一意のリクエスト数とは限りません。複数の監査段階で同じ監査IDが繰り返されることがあります。403は認可拒否ですが、それだけで原因となったIAM/RBACポリシーを特定できるわけではありません。CLI例にはAWS CLI、Bash、jq、Pythonが必要です。最大100件を問い合わせ、結果をプライベートに保存します。実行中のクエリに行が返っていても、最終結果は`Complete`の場合だけです。ポーリングのタイムアウトはサービス側のクエリをキャンセルしません。

```sql
fields @timestamp, user.username, verb, objectRef.namespace, objectRef.resource, responseStatus.code
| filter @logStream like /kube-apiserver-audit/
| filter responseStatus.code = 403
| sort @timestamp desc
| limit 100
```
```sql
filter @logStream like /kube-apiserver-audit/
| filter responseStatus.code = 403
| stats count(*) as deniedEvents by user.username, verb, objectRef.resource
| sort deniedEvents desc
| limit 100
```
```bash
# Read-only query with possible CloudWatch scan charges; no log configuration changes.
set -euo pipefail
umask 077
: "${AWS_REGION:?}"; : "${CLUSTER_NAME:?}"
evidence_dir=$(mktemp -d "$PWD/eks-audit403.XXXXXX")
printf 'Private evidence directory: %s\n' "$evidence_dir"
read -r start_epoch end_epoch < <(python3 - <<'PY'
import time
end = int(time.time())
print(end - 3600, end)
PY
)
query_string='fields @timestamp, user.username, verb, objectRef.namespace, objectRef.resource, responseStatus.code
| filter @logStream like /kube-apiserver-audit/
| filter responseStatus.code = 403
| sort @timestamp desc
| limit 100'
query_id=$(aws logs start-query --region "$AWS_REGION" --no-cli-pager \
  --log-group-name "/aws/eks/$CLUSTER_NAME/cluster" \
  --start-time "$start_epoch" --end-time "$end_epoch" \
  --query-string "$query_string" --query queryId --output text)
if [[ ! "$query_id" =~ ^[0-9a-fA-F-]{36}$ ]]; then
  printf '%s\n' 'No valid query ID returned.' >&2
  exit 1
fi
printf '%s\n' "$query_id" > "$evidence_dir/query-id.txt"
for attempt in {1..15}; do
  aws logs get-query-results --region "$AWS_REGION" --no-cli-pager \
    --query-id "$query_id" --output json > "$evidence_dir/result.json"
  status=$(jq -er '.status' "$evidence_dir/result.json")
  case "$status" in
    Complete)
      printf 'Query complete; inspect private file %s/result.json\n' "$evidence_dir"
      exit 0
      ;;
    Scheduled|Running) sleep 2 ;;
    *)
      printf 'Query ended without complete results: %s\n' "$status" >&2
      exit 1
      ;;
  esac
done
printf 'Polling limit reached; query %s may still run. Partial results are not final.\n' "$query_id" >&2
exit 2
```

</details>

## 応用問題

### 1. APIのレイテンシが断続的に高くなる場合、トレーシング、メトリクス、ログを使った調査手順を作成してください。

<details>
<summary>回答を表示</summary>

**1. 測定条件を定義する。** 1つのクラスター、`diagnostics-example`内で計装された`api-gateway`、秒単位で計測するclassic histogram、値の範囲を限定した`endpoint`ラベル、`le="0.5"`バケットを使います。バケットとカウントの系列範囲が一致することを確認してください。Kubernetesがこれらのアプリケーションメトリクスを自動提供するわけではありません。影響のあるルート、トラフィック量、時間範囲を比較します。以下のクエリはp99、ヒートマップ用の累積バケットレート、0.5秒を超えた割合を示します。レートを単純に差し引いた値はリクエスト/秒であり、比率ではありません。トラフィックが0の場合、比率は定義できません。

```promql
histogram_quantile(0.99, sum by (le,namespace,service,endpoint) (
  rate(http_request_duration_seconds_bucket{namespace="diagnostics-example",service="api-gateway"}[5m])
))
```
```promql
sum by (le,namespace,service,endpoint) (rate(http_request_duration_seconds_bucket{namespace="diagnostics-example",service="api-gateway"}[1m]))
```
```promql
(
  (sum by (namespace,service,endpoint) (rate(http_request_duration_seconds_count{namespace="diagnostics-example",service="api-gateway"}[5m])) - sum by (namespace,service,endpoint) (rate(http_request_duration_seconds_bucket{namespace="diagnostics-example",service="api-gateway",le="0.5"}[5m])))
  / sum by (namespace,service,endpoint) (rate(http_request_duration_seconds_count{namespace="diagnostics-example",service="api-gateway"}[5m]))
)
and on (namespace,service,endpoint) (sum by (namespace,service,endpoint) (rate(http_request_duration_seconds_count{namespace="diagnostics-example",service="api-gateway"}[5m])) > 0)
```

**2. トレースを調べる。** バックエンドのUIでサービス`api-gateway`、影響のある時間範囲、2秒超の所要時間、`GET /api/products`などの該当オペレーションを選択します。バックエンドで実際に使われている属性名で、エラースパンと下流呼び出しを調べます。これはUI上の検索条件であり、インポート可能なJaeger YAML設定ではありません。まず伝播とサンプリングを確認してください。スパンがないことは呼び出しがなかった証拠ではありません。並列スパンの時間を単純に合計して、リクエスト所要時間としないでください。

**3. ログを関連づける。** 構造化ログに`trace_id`がある場合、プレースホルダーを実際のTrace IDに置き換え、所有するアプリケーションロググループ/時間範囲で別のLogs Insights QLクエリを実行します。アプリケーションの計装が必要です。トークン、リクエスト本文、伝播されたSecretをログに記録しないでください。相関によって仮説は絞れますが、因果関係が証明されるわけではありません。

```sql
fields @timestamp, @message
| filter trace_id = "REPLACE_WITH_ACTUAL_TRACE_ID"
| sort @timestamp asc
| limit 100
```

**4. インフラストラクチャの証拠を比較する。** 次のクエリは順に、スロットリングされたCPU秒/秒、受信バイト/秒、JVM GC一時停止秒/秒を返します。ネットワークスループットは**ネットワークレイテンシではありません**。レイテンシの測定には、範囲を適切に絞ったクライアント/サーバースパンか、承認された範囲限定RTTテストを使います。GC一時停止のレートは各リクエストの遅延時間ではありません。メトリクス名/ラベルはexporterとランタイムによって異なります。無関係なクラスター全体の集計ではなく、対象ノード/Podと時間間隔を比較してください。

```promql
rate(container_cpu_cfs_throttled_seconds_total{namespace="diagnostics-example",container!="",container!="POD"}[5m])
```
```promql
rate(container_network_receive_bytes_total{namespace="diagnostics-example",pod!=""}[5m])
```
```promql
rate(jvm_gc_pause_seconds_sum{namespace="diagnostics-example",service="api-gateway"}[5m])
```

**5. ダッシュボードを設計する。** この表はパネルの設計案であり、Grafanaのインポートファイルではありません。インストール済みGrafanaのバージョンに対応した編集/エクスポート形式と、実際のdatasource UIDを使います。

| パネル | 測定内容 |
|---|---|
| p50/p95/p99レイテンシ | 0.50、0.95、0.99を使う3つの個別histogram-quantileクエリ |
| ステータス別リクエストレート | 計装したリクエストカウンターのレートを、実際のステータスラベルでグループ化 |
| ヒートマップ | `le`とルートの範囲を保持した、対応するclassic histogramバケットのレート |
| 下流レイテンシ | 下流サービス固有のhistogramとラベル条件 |
| Podリソース | CPUカウンターのレート（コア数）、メモリworking-setゲージ（バイト） |

```promql
rate(container_cpu_usage_seconds_total{namespace="diagnostics-example",container!="",container!="POD"}[5m])
```
```promql
container_memory_working_set_bytes{namespace="diagnostics-example",container!="",container!="POD"}
```

**6. 比較アラートを評価する。** Prometheusでこのルール/namespaceを選び、releaseラベルを置き換えます。50%のしきい値と5分間の継続条件は、トラフィック/SLOに基づく調整が必要な例です。長い時間範囲のp99は**1時間の平均レイテンシではなく**、直近5分も含みます。これは比較ルールであり、予測モデルではありません。正の値を持つ基準値が必要です。欠損/NaNデータは正常の証拠ではありません。メトリクス収集と低トラフィックを別々に確認し、通知の配送もテストします。

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: latency-comparison-example
  namespace: monitoring
  labels:
    release: REPLACE_WITH_SELECTED_PROMETHEUS_RELEASE
spec:
  groups:
  - name: latency-comparison-example
    rules:
    - record: diagnostics:http_duration_seconds:p99_5m
      expr: "histogram_quantile(0.99, sum by (le,namespace,service,endpoint) (\n \
        \ rate(http_request_duration_seconds_bucket{namespace=\"diagnostics-example\"\
        ,service=\"api-gateway\"}[5m])\n))"
    - record: diagnostics:http_duration_seconds:p99_1h
      expr: "histogram_quantile(0.99, sum by (le,namespace,service,endpoint) (\n \
        \ rate(http_request_duration_seconds_bucket{namespace=\"diagnostics-example\"\
        ,service=\"api-gateway\"}[1h])\n))"
    - alert: LatencyComparedWithLongerWindow
      expr: "(\n  diagnostics:http_duration_seconds:p99_5m\n  / diagnostics:http_duration_seconds:p99_1h\
        \ > 1.5\n)\nand on (namespace,service,endpoint) (diagnostics:http_duration_seconds:p99_1h\
        \ > 0)"
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: Five-minute p99 exceeds one-hour p99 by over 50%; investigate.
```

仮説は分けて扱います。エンドポイント固有の挙動、下流呼び出し、CPUスロットリング、GC、ネットワーク経路、トラフィック変化には、それぞれ裏付けとなる証拠が必要です。ここではレイテンシの低下もベンチマークも測定していません。

</details>

### 2. NotReadyが断続的に発生するノードについて、証拠に基づく根本原因分析（RCA）手順を確立してください。

<details>
<summary>回答を表示</summary>

**1. 識別情報と時刻を集める。** `Ready=False`と、ハートビート喪失による`Unknown`を区別します。ノードUID、provider ID、OS/ランタイムのバージョン、conditionの遷移時刻、leaseの更新時刻を記録してください。イベントの保持期間は限られるため、一覧が空でも過去の障害がなかったとは言えません。停止中のノードではnode-debug自体を使えない場合があります。

```bash
# Read-only scoped node evidence; confirm account/cluster/Region first.
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NODE_NAME:?}"
k=(kubectl --context "$KUBE_CONTEXT" --request-timeout=15s)
node_state=$("${k[@]}" get node "$NODE_NAME" -o json | jq '{
  uid:.metadata.uid,providerID:.spec.providerID,
  nodeInfo:.status.nodeInfo,conditions:.status.conditions
}')
printf '%s\n' "$node_state"
node_uid=$(jq -er '.uid' <<<"$node_state")
"${k[@]}" get events --all-namespaces \
  --field-selector "involvedObject.uid=$node_uid" --sort-by='.metadata.creationTimestamp'
"${k[@]}" -n kube-node-lease get lease "$NODE_NAME" \
  -o jsonpath='{.spec.renewTime}{"\n"}'
```

対応するEC2インスタンスの`Maximum=1`は、その時間バケット内にステータスチェック失敗のサンプルが1つ以上あったことを示します。`Sum`は停止時間ではなく、データポイント欠損は成功を意味しません。FargateとHybrid Nodesでは、それぞれに対応したインフラストラクチャの証拠が必要です。

```bash
# EC2-backed nodes only: resolve the actual instance from providerID, not a guessed name.
: "${AWS_REGION:?}"; : "${INSTANCE_ID:?Verified EC2 instance ID}"
read -r start_time end_time < <(python3 - <<'PY'
from datetime import datetime, timedelta, timezone
end = datetime.now(timezone.utc)
print((end-timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ"),
      end.strftime("%Y-%m-%dT%H:%M:%SZ"))
PY
)
aws cloudwatch get-metric-statistics --region "$AWS_REGION" --no-cli-pager \
  --namespace AWS/EC2 --metric-name StatusCheckFailed \
  --dimensions "Name=InstanceId,Value=$INSTANCE_ID" \
  --start-time "$start_time" --end-time "$end_time" --period 300 \
  --statistics Maximum --query 'sort_by(Datapoints,&Timestamp)'
```

**2. 該当するホストの証拠を収集する。** 承認済みホストアクセス、NodeDiagnostic、またはソース章に記載されたAuto Modeの診断経路を使います。`general`はprivilegedなchroot用ショートカットではありません。以下の読み取りは、systemdを使う対応済みLinuxホスト向けであり、すべてのデバッグイメージやBottlerocket/Auto Mode経路で使えるわけではありません。ログには機密情報が含まれる場合があるため、別途レビューした修復に着手する前に安全な場所へ収集します。

```bash
# Only inside an already authorized, compatible systemd Linux host context.
# These are bounded reads, not instructions to restart or prune the node.
journalctl -u kubelet --since '24 hours ago' -n 200 --no-pager
journalctl -u containerd --since '24 hours ago' -n 200 --no-pager
dmesg | tail -n 100
free -h
vmstat 1 5
cat /proc/pressure/memory /proc/pressure/cpu
```

**3. 該当するネットワーク経路を調べる。** このリクエストは、選択したkubeconfigでTLSを検証し、`/readyz`へのアクセス権限を必要とします。確認するのは呼び出し元の経路であり、障害ノードの経路とは限りません。401/403はHTTP応答があったことを示しますが、readinessが正常とは証明しません。DNS、timeout、証明書エラーはそれぞれ別に診断します。信頼性検証を隠す目的で`curl -k`を使わないでください。

```bash
# Uses the selected kubeconfig CA and authentication; do not disable TLS verification.
: "${KUBE_CONTEXT:?}"
kubectl --context "$KUBE_CONTEXT" --request-timeout=10s get --raw='/readyz'
```

標準VPC CNIの場合に限り、実際のaws-node Podと障害対象インスタンスのENIを調べます。Auto Modeは管理されたネットワーク経路を使います。DaemonSetが見つからないことだけで障害と判断しないでください。

```bash
# Standard VPC CNI on an EC2 node; choose the aws-node Pod on the affected node.
: "${KUBE_CONTEXT:?}"; : "${AWS_NODE_POD:?}"; : "${AWS_REGION:?}"; : "${INSTANCE_ID:?}"
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n kube-system \
  logs "$AWS_NODE_POD" -c aws-node --since=15m --tail=100 --limit-bytes=65536
aws ec2 describe-network-interfaces --region "$AWS_REGION" --no-cli-pager \
  --filters "Name=attachment.instance-id,Values=$INSTANCE_ID" \
  --query 'NetworkInterfaces[].{ENI:NetworkInterfaceId,Subnet:SubnetId,Status:Status,IPv4Prefixes:Ipv4Prefixes,PrivateIPs:PrivateIpAddresses[].PrivateIpAddress}'
```

**4. リソースのシグナルを解釈する。** 次の単一クラスター向けクエリは、メモリの余裕、ルートファイルシステムの空き容量、システムのスレッド上限に対する使用率、実際のkubelet圧迫conditionを示します。対応するNode Exporter/kube-state-metricsの系列と、正しいホストマウント/ラベルが必要です。Node Exporterでは`processes`がデフォルトで無効です。`node_processes_max_threads`はLinuxの`threads-max`です。この比率はkubeletのPIDPressure判定でも、コンテナの`pids.max`でもありません。ファイルシステム/inode/imagefs/cgroupの上限とスクレイプ失敗は別に確認してください。ここでのしきい値は例であり、デフォルト値ではありません。

```promql
(1 - node_memory_MemAvailable_bytes / (node_memory_MemTotal_bytes > 0)) * 100 > 90
```
```promql
(1 - node_filesystem_avail_bytes{mountpoint="/",fstype!~"tmpfs|overlay"} / (node_filesystem_size_bytes{mountpoint="/",fstype!~"tmpfs|overlay"} > 0)) * 100 > 85
```
```promql
node_processes_threads / (node_processes_max_threads > 0) * 100 > 80
```
```promql
max by (node) (kube_node_status_condition{condition=~"MemoryPressure|DiskPressure|PIDPressure",status="true"}) == 1
```

**5. 仮説を検証する。** カーネルOOM記録を、終了したプロセス、ワークロードのメモリ、limitと照合します。ディスク/inodeの枯渇は、影響を受けたファイルシステムと照合します。時刻を合わせてkubelet/ランタイムログ、ノードからAPIへの到達性、CNI/IPの証拠、EC2の状態を比較してください。メモリ使用量が高いことやprobeに失敗したことだけでは、メモリリークやインフラ障害の証明になりません。

**6. 実際のコンピューティングモデルに合わせて再発を防ぐ。** Auto Modeにはノード監視と修復が含まれます。マネージドノードグループでは修復設定を確認してください。セルフマネージドKarpenterの修復には、互換性のあるリリース、`NodeRepair=true`、該当するcondition/修復ポリシーが必要です。診断エージェントが追加のconditionを供給します。現在のKarpenterポリシーは`Ready=False/Unknown`が30分続いた場合に修復を許可し、NodePoolの20%を超えるノードがunhealthyなら修復を停止します。また通常のgraceful drainではなく、強制終了を行う場合があります。自発的なdisruption budget/PDBがあれば常に修復を保証できるとは考えないでください。EKSの修復はデフォルトでは`MemoryPressure`、`DiskPressure`、`PIDPressure`を修復しません。ワークロード側の圧迫に対処してください。これらのEKS監視/修復機能はLinuxのみを対象とし、監視エージェントはFargateでは利用できません。不完全なprivileged Node Problem Detector DaemonSetを導入したり、既存エージェントを重複配備したりせず、ソース章と現在のプロバイダー設定を確認してください。

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: node-health-example
  namespace: monitoring
  labels:
    release: REPLACE_WITH_SELECTED_PROMETHEUS_RELEASE
spec:
  groups:
  - name: node-health-example
    rules:
    - alert: NodeHighMemoryUse
      expr: (1 - node_memory_MemAvailable_bytes / (node_memory_MemTotal_bytes > 0))
        * 100 > 90
      for: 5m
      labels:
        severity: warning
    - alert: NodeRootFilesystemLowSpace
      expr: (1 - node_filesystem_avail_bytes{mountpoint="/",fstype!~"tmpfs|overlay"}
        / (node_filesystem_size_bytes{mountpoint="/",fstype!~"tmpfs|overlay"} > 0))
        * 100 > 85
      for: 5m
      labels:
        severity: warning
    - alert: NodeNotReady
      expr: max by (node) (kube_node_status_condition{condition="Ready",status="true"})
        == 0
      for: 2m
      labels:
        severity: critical
```

Prometheusでこれらのルールを選択する必要があります。condition/exporter系列の欠損には、収集状況/インベントリを別途監視するアラートが必要です。容量アラートは別のシグナルを測っているため、kubeletの圧迫conditionと同じ名前にはしていません。

Linux kubeletを設定できる場合、次は**既存設定にレビューのうえマージする断片**です。完全な設定ファイルでも、EKSノード上のファイルを上書きするコマンドでもありません。OS/provisionerがサポートするbootstrap手順を使います。`mergeDefaultEvictionSettings`を有効にすると未指定のhard defaultが保持されます。そうしないと部分的な上書きによって、省略したしきい値が0に設定される場合があります。soft thresholdには対応するgrace periodが必要で、`evictionMaxPodGracePeriod`は終了時の猶予期間を制限します。以下の値はワークロード/容量に照らした検証が必要な例であり、Auto Modeのカスタマイズ手順ではありません。

```json
{
  "mergeDefaultEvictionSettings": true,
  "evictionHard": {
    "memory.available": "500Mi",
    "nodefs.available": "10%",
    "imagefs.available": "15%"
  },
  "evictionSoft": {
    "memory.available": "1Gi",
    "nodefs.available": "15%"
  },
  "evictionSoftGracePeriod": {
    "memory.available": "1m",
    "nodefs.available": "1m"
  },
  "evictionMaxPodGracePeriod": 60
}
```

**過去のRCAテンプレート: 未検証の例であり、インシデント報告ではありません。** 元の日付、数量、現地時間帯の表記は維持されています。PSTとKSTの例が同じ瞬間を示すとは限りません。メモリリークの断定、実際の修復、完了状況を裏付けるソース証拠はありません。運用で使う前に、プレースホルダーを証拠で置き換えてください。

```markdown
## Incident summary (illustrative)
- Start: 2024-01-15 14:30 PST
- Example impact: 3 nodes, 45 Pods
- Example restoration: 2024-01-15 15:15 PST (duration 45 minutes, not a measured mean)

## Example timeline (evidence required for every entry)
- 14:30 NodeNotReady alert
- 14:35 Investigation starts
- 14:50 Hypothesis: memory pressure killed kubelet; confirm with kernel/process evidence
- 15:00 Proposed drain/restart; record actual authorization, effects and data safety checks
- 15:15 Proposed restoration point; supply workload/SLO verification

## Root-cause hypothesis
A memory leak could exhaust node memory; not established by this template.

## Follow-up proposals (no completion asserted)
1. Validate application memory behavior and appropriate requests/limits.
2. Evaluate alert threshold change from 90% to 80% against noise and capacity.
3. Review existing node monitoring before considering Node Problem Detector.
```

</details>

**この演習の主な参考資料:**

- [Prometheusの関数](https://prometheus.io/docs/prometheus/latest/querying/functions/)
- [Karpenterのdisruptionとノード修復](https://karpenter.sh/docs/concepts/disruption/)
- [EKSのノード監視と修復](https://docs.aws.amazon.com/eks/latest/userguide/node-health.html)
- [Kubeletによるノード圧迫時のeviction](https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/)
- [Node Exporterのcollector](https://github.com/prometheus/node_exporter#disabled-by-default)
