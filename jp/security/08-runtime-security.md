# ランタイムセキュリティ

> **最終更新**: 2026年10月16日
> **検証ベースライン**: Falco 0.45.0 / chart 9.2.0、Falcosidekick 2.35.0 / chart 0.14.0、Tetragon 1.7.1。実際のカーネル、OS、ノード種別に対するサポートを確認してください。

ランタイムセキュリティはプロセス、ファイル、ネットワークの活動を監視し、検証済みのポリシーを通じて選択した操作を制限します。 **アラートは侵害の証拠ではありません。検知と防止には、それぞれ別のテストが必要です**。 このガイドはローカルCLI、スキーマ、Helm、合成イベントを使って確認しました。実際のクラスター、カーネルBPFプログラム、通知チャネルは使用していません。

<span id="container-runtime-threats"></span>
<span id="detection-technologies"></span>

## ランタイム脅威の全体像

| 観測点 | 確認できること | 限界 |
|---|---|---|
| システムコール／カーネルフック | プロセス実行、ファイルアクセス、接続の試行 | イベントの欠落、権限、カーネルサポート、フィルターを確認する |
| Kubernetes監査 | APIの要求者、verb、オブジェクト、応答ステータス | Pod内のすべてのプロセス／ファイル操作は表示しない |
| ネットワークフロー | 接続、ドロップ、ポリシーの判定 | ポートや暗号化された接続だけでは悪意を示せない |
| イメージ／Admissionポリシー | 脆弱性、署名、Pod設定 | デプロイ後のすべての挙動を検知するものではない |

eBPFだけで低オーバーヘッドや安全性が保証されるわけではありません。実際のノードでフック、イベント量、フィルタリング、出力コスト、CPU、メモリを測定してください。コマンド名が指標と一致するという理由だけで、本番プロセスを自動終了させないでください。

<span id="default-rule-examples"></span>

## Falco

### Falcoの概要

Falcoはイベントをルールと照合して評価します。一般的なシステムコールの流れは `Linux event → modern eBPF/kmod capture → Falco filter/rule → JSON output → Falcosidekick → notification/storage` です。SlackとPagerDutyは後段の連携先であり、Falcoルールエンジン内にSlack用クライアントがあるわけではありません。

0.45.0の配布物にはcontainer plugin 0.7.4が同梱されています。このプラグインは`container.id`などのフィールドを提供するため、すべてのプラグインを無効にすると、これらのフィールドを使うルールをコンパイル／実行できません。ランタイムソケット、Kubernetesメタデータの収集、アクセス権限を確認してください。

### Falcoのインストール（EKS）

この例は、ホストへのアクセスを自分で管理するLinux EC2ノードを対象としています。DaemonSetがFargateやその他の制限されたホスト上で実行できると想定しないでください。modern eBPFに必要なカーネル、BTF、ケイパビリティを確認してください。chart 9.2.0で明示できるドライバー種別は`modern_ebpf`と`kmod`です。古い`ebpf`設定を残さないでください。

[サンプルディレクトリをダウンロード](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/security/runtime-security)し、`examples/security/runtime-security`から次のコマンドを実行します。[サンプルREADME](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/runtime-security/README.md)に、3つのvaluesファイルとルールの説明があります。

```bash
helm repo add falcosecurity https://falcosecurity.github.io/charts
helm repo update falcosecurity
helm upgrade --install falcosidekick falcosecurity/falcosidekick \
  --version 0.14.0 --namespace falco --create-namespace \
  --values falcosidekick-values.yaml
helm upgrade --install falco falcosecurity/falco \
  --version 9.2.0 --namespace falco \
  --values falco-values.yaml
```

Sidekick chartのappVersionはデフォルトのイメージタグと異なるため、この例では`image.tag`を2.35.0に固定しています。先に出力用の認証情報SecretとPrometheus OperatorのCRDを準備してください。SecretがないとPodが起動できない場合があります。最小構成のラボでは、使わない通知／メトリクス機能を無効にしてください。

```yaml
driver:
  kind: modern_ebpf
metrics:
  enabled: true
serviceMonitor:
  create: true
falcosidekick:
  enabled: false
falco:
  json_output: true
  json_include_output_property: true
  http_output:
    enabled: true
    url: http://falcosidekick.falco.svc:2801
customRules:
  documentation-rules.yaml: |-
    - macro: doc_spawned
      condition: evt.type in (execve, execveat) and evt.res = SUCCESS
    - macro: doc_container
      condition: container.id != host
    - rule: Documentation shell execution
      desc: Observe successful shell process execution in a container; not proof of compromise.
      condition: doc_spawned and doc_container and proc.name in (bash, sh, dash, zsh)
      output: Shell process observed (proc=%proc.name command=%proc.cmdline container=%container.id)
      priority: NOTICE
      tags:
      - documentation
      - process
    - rule: Documentation service account token read
      desc: Observe read access to the default projected service account token path; legitimate
        clients also read it.
      condition: evt.type in (open, openat, openat2) and evt.is_open_read
        = true and fd.num >= 0 and doc_container and fd.name startswith /var/run/secrets/kubernetes.io/serviceaccount/
      output: Service account path read (proc=%proc.name file=%fd.name container=%container.id)
      priority: NOTICE
      tags:
      - documentation
      - credential_access
```


この設定は、別途インストールしたfalcosidekick ClusterIP ServiceにHTTPで送信します。同じnamespaceを使っても通信が認証または暗号化されるわけではありません。実際の信頼境界に応じてアクセスポリシーとTLS/mTLSを設定し、ノードとFalco間の接続を確認してください。Falcoは`json_output`や`http_output`のようなsnake_caseフィールドを使います。古い`jsonOutput`／`httpOutput`や削除済みのgRPC設定は、0.45.0のスキーマで失敗します。

### Falcoルールの構造

このルールは必要なマクロを独自に定義し、デフォルトのルール名を置き換えません。既存のルールを意図的に変更するときは、固定したルールセットのoverride構文を使ってください。

```yaml
- macro: doc_spawned
  condition: evt.type in (execve, execveat) and evt.res = SUCCESS
- macro: doc_container
  condition: container.id != host
- rule: Documentation shell execution
  desc: Observe successful shell process execution in a container; not proof of compromise.
  condition: doc_spawned and doc_container and proc.name in (bash, sh, dash, zsh)
  output: Shell process observed (proc=%proc.name command=%proc.cmdline container=%container.id)
  priority: NOTICE
  tags:
  - documentation
  - process
- rule: Documentation service account token read
  desc: Observe read access to the default projected service account token path; legitimate
    clients also read it.
  condition: evt.type in (open, openat, openat2) and evt.is_open_read
    = true and fd.num >= 0 and doc_container and fd.name startswith /var/run/secrets/kubernetes.io/serviceaccount/
  output: Service account path read (proc=%proc.name file=%fd.name container=%container.id)
  priority: NOTICE
  tags:
  - documentation
  - credential_access
```


enterイベントの削除後、Falco 0.45.0では`evt.dir`が非推奨であるという警告が出ます。この例では成功したexecイベントとreadイベントを直接選択します。正当なKubernetesクライアントもservice account tokenを読み取るため、readイベントだけでは「不正アクセス」の証拠になりません。ワークロードの通常状態、承認済みバイナリ、Podのidentityと組み合わせてください。

### カスタムルールの作成

| パターン | 考えられる兆候 | 必要な留意点 |
|---|---|---|
| マイニングの疑い | プロセス名、pool／stratum文字列、通常と異なるリソース使用 | 名前の変更や正当な計算処理によって、ヒューリスティックが回避されたり誤検知したりする |
| reverse shellの疑い | shellのargv内の接続文字列、通常と異なる外向き通信 | execイベントの`fd.name`はネットワーク接続の証拠ではない |
| 権限昇格 | 認証情報の変更、SUID設定、ケイパビリティ | `user.uid`／`proc.uid`／`proc.suid`の意味と操作の成否を確認する |
| 脱出の疑い | namespace／host-pathへのアクセス、通常と異なるmount | `nsenter`や`/.dockerenv`という文字列だけでは脱出の成功を示せない |

ルールのコンパイルだけでは検知の有効性を測れません。段階的に展開する前に、合成イベントまたは許可されたラボイベント、通常のワークロード、欠落メタデータ、ドロップカウンターをテストしてください。引数、パス、ログには秘密情報が含まれる可能性があります。イベントフィールド、保持期間、アクセスを制限してください。

### Falcoアラートの設定

```yaml
config:
  existingSecret: falcosidekick-output-credentials
  slack:
    minimumpriority: warning
  pagerduty:
    minimumpriority: critical
  aws:
    region: ap-northeast-2
    cloudwatchlogs:
      loggroup: /falco/alerts
      logstream: documentation
      minimumpriority: warning
  elasticsearch:
    minimumpriority: warning
    checkcert: true
webui:
  enabled: false
serviceMonitor:
  enabled: true
image:
  tag: 2.35.0
```


`falcosidekick-output-credentials`は、`envFrom`を通じて読み取る同一namespace内の既存Secretです。Secret管理の手順を使って、`SLACK_WEBHOOKURL`、`PAGERDUTY_ROUTINGKEY`、`ELASTICSEARCH_HOSTPORT`／`USERNAME`／`PASSWORD`など、承認された出力先が必要とする変数だけを設定してください。Helm valuesに`${ELASTIC_PASSWORD}`と書いても、シェルによる変数展開は行われません。認証情報をGit、コマンドライン、レビュー用ログに露出させないでください。

AWS設定は`config.aws`の下に置きます。ワークロードidentityを確認し、IAMアクションとリソースを対象のロググループ／ストリームに限定してください。`minimumpriority`で使えるのはemergency／alert／critical／error／warning／notice／informational／debugであり、`high`ではありません。各出力先の有効化条件、再試行、失敗メトリクスを確認してください。この例ではWeb UIを無効にしています。

<span id="tetragon-installation"></span>
<span id="tracingpolicy-basic-structure"></span>
<span id="process-monitoring"></span>

## Tetragon

### Tetragonの概要

TetragonはCilium CNIとは独立して実行できます。組み込みの`process_exec`／`process_exit`イベントと、追加のTracingPolicyフックを区別してください。処理の流れは`kernel hook → selector → Post/supported action → JSON/gRPC/metrics`です。Kubernetes CRD自体がカーネル内で実行されるわけではありません。

```bash
helm repo add cilium https://helm.cilium.io
helm repo update cilium
helm upgrade --install tetragon cilium/tetragon \
  --version 1.7.1 --namespace kube-system --values tetragon-values.yaml
```

```yaml
tetragon:
  enableProcessCred: true
  enableProcessNs: true
```


operator／CRDの準備状況と、各ノードのカーネル、BTF、ケイパビリティを確認してください。Helmのレンダリングだけではフックのアタッチを確認できません。namespace付きの例はdemo-appワークロードを対象としています。選んだポリシー種別で実際に適用される範囲とフックを確認してください。

### ファイルアクセスの監視

```yaml
apiVersion: cilium.io/v1alpha1
kind: TracingPolicyNamespaced
metadata:
  name: documentation-file-observe
  namespace: demo-app
spec:
  kprobes:
  - call: security_file_permission
    syscall: false
    args:
    - index: 0
      type: file
    - index: 1
      type: int
    selectors:
    - matchArgs:
      - index: 0
        operator: Prefix
        values:
        - /etc/shadow
        - /root/.ssh/
      - index: 1
        operator: Mask
        values:
        - '4'
      matchActions:
      - action: Post
```


`security_file_permission(struct file *, int mask)`の第2引数は権限マスクであり、`MAY_READ=4`、`MAY_WRITE=2`です。引数が1つの`security_file_open`関数で「index 1をopen flag」として扱うのは誤りです。`O_WRONLY=1`／`O_RDWR=2`というopen flagも、この権限マスクとは異なります。このフックだけでは、すべてのmmap／truncate／ファイル変更を捕捉できません。

### ネットワークの監視

```yaml
apiVersion: cilium.io/v1alpha1
kind: TracingPolicyNamespaced
metadata:
  name: documentation-outbound-observe
  namespace: demo-app
spec:
  kprobes:
  - call: tcp_connect
    syscall: false
    args:
    - index: 0
      type: sock
    selectors:
    - matchArgs:
      - index: 0
        operator: DPort
        values:
        - '22'
        - '4444'
        - '5555'
      matchActions:
      - action: Post
```


tcp_connectはTCP接続の試行を監視します。宛先ポートだけで悪意ある通信やポリシーによる拒否を示すことはできません。UDPポート53の活動だけでは、DNSの問い合わせと応答を完全に分析できません。適切なDNSテレメトリ経路を使ってください。

### ランタイムでの強制

まずPost／monitorの動作から始め、通常の操作と誤検知を確認してください。Sigkillはシグナルを送りますが、フックやカーネルの挙動によっては、すでに発生した副作用を取り消せません。戻り値の上書きには、対応するシステムコールまたはsecurity関数、カーネル設定、適切なエラー値が必要です。すべてのkprobeがこれをサポートするわけではありません。

ファイル名やargvの文字列だけで、マイニングやreverse shellを常に防げると説明しないでください。execveのargvは文字列1つではなくポインターの配列です。これを単一の文字列として読む方法では、意図したとおりにコマンドライン全体を調べられません。プロセスイベントの引数フィルタリングとカーネルアクションを区別し、承認された範囲の小さなラボで強制動作を検証してください。

### Tetragon CLIの使い方

```bash
kubectl exec -n kube-system ds/tetragon -c tetragon -- tetra getevents -o json
kubectl exec -n kube-system ds/tetragon -c tetragon -- \
  tetra getevents -o compact --namespace production --process curl
# Filter stored synthetic events locally:
tetra getevents -o json --namespace demo-app < events.jsonl
```

DaemonSetを指定して実行すると、特定Pod／ノードのagentが選ばれます。クラスター全体の集約ではありません。ここで試したのはstdinを使うフィルタリング経路のみです。1.7.1の`tetra tracingpolicy modify`実装はgRPCクライアントも作成するため、オフラインの検証には使いませんでした。

<span id="feature-comparison-table"></span>
<span id="use-case-recommendations"></span>

## FalcoとTetragonの比較

| 比較項目 | Falco | Tetragon |
|---|---|---|
| ポリシー | イベント条件とルールセット | カーネルフック、selector、action |
| 主な用途 | 通知／保存との連携を伴う検知 | プロセスの可視化と明示的なフックによる強制 |
| 運用上の確認事項 | ドライバー／プラグイン／ランタイムメタデータ、イベントの欠落 | BTF／フックのサポート、ポリシーの適用範囲、副作用 |
| 性能 | 実際の負荷でCPU、メモリ、イベント欠落を測定 | 同じワークロードを使う。eBPFだけでは優位性を示せない |

両方をデプロイすることが常に最善とは限りません。重複収集、ノード権限、コスト、運用の複雑さ、必要な強制制御を検討してください。

## Kubernetes監査ログ

### 監査ポリシーの設定

このポリシーは**自分で管理するKubernetes APIサーバー**向けです。このYAMLを適用しても、EKSのマネージド監査ポリシーは置き換わりません。EKSコントロールプレーンの監査ログを有効にし、CloudWatchへのアクセス、保持期間、暗号化を設定してください。

```yaml
apiVersion: audit.k8s.io/v1
kind: Policy
omitStages:
- RequestReceived
rules:
- level: Metadata
  resources:
  - group: ''
    resources:
    - secrets
    - serviceaccounts/token
- level: Metadata
  resources:
  - group: ''
    resources:
    - pods/exec
    - pods/attach
    - pods/portforward
- level: Request
  resources:
  - group: rbac.authorization.k8s.io
    resources:
    - roles
    - rolebindings
    - clusterroles
    - clusterrolebindings
  verbs:
  - create
  - update
  - patch
  - delete
- level: Metadata
```


Secretと`serviceaccounts/token`に対してRequest／RequestResponseを記録すると、認証情報の本文が保存される可能性があるため、Metadataを使ってください。監査ルールは先に一致したものが適用されます。機密リソースのルールを先に置いてください。`system:anonymous`だけでは、すべての認証失敗を捕捉できません。監査stage、`responseStatus`、認証ログを確認してください。execの監査レコードは、terminal session内のすべてのコマンドを記録するものではありません。

### EKS監査ログの分析

```text
fields @timestamp, user.username, verb, objectRef.resource, objectRef.name, responseStatus.code
| filter objectRef.resource = "secrets"
| sort @timestamp desc
| limit 100
```

これはCloudWatch Logs Insightsのクエリであり、Bashではありません。403は拒否された応答です。成功したreadは別に分類してください。ロギングを有効にした後に収集を確認し、保持期間を設定してください。

<span id="cryptocurrency-mining-detection"></span>
<span id="reverse-shell-detection"></span>
<span id="privilege-escalation-detection"></span>

## ランタイム脅威の検知パターン

Seccompはシステムコールを制限しますが、拒否されても必ずプロセスが終了するとは限りません。actionはERRNOを返す、終了させる、または通知することができます。RuntimeDefaultはランタイムのプロファイルを意味します。明示的に設定するか、kubeletの`seccompDefault`を確認してください。Kubernetes 1.27+であることだけを理由に、すべてのPodへ自動適用されるわけではありません。

AppArmorにはノード側のサポートとロード済みプロファイルが必要です。Complainモードは通常の違反を記録しますが、明示的なdenyルールは引き続きブロックできます。`readOnlyRootFilesystem`はコンテナのsecurityContextフィールドです。書き込み可能なvolumeの悪用、ネットワークアクセス、メモリ操作は防ぎません。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: runtime-security-demo
  namespace: demo-app
  labels:
    app: runtime-security-demo
spec:
  automountServiceAccountToken: false
  securityContext:
    runAsNonRoot: true
    runAsUser: 10001
    runAsGroup: 10001
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: app
    image: registry.example.com/team/app:REPLACE_WITH_APPROVED_VERSION
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
        - ALL
    resources:
      requests:
        cpu: 100m
        memory: 64Mi
      limits:
        cpu: 500m
        memory: 128Mi
    volumeMounts:
    - name: tmp
      mountPath: /tmp
  volumes:
  - name: tmp
    emptyDir:
      sizeLimit: 64Mi
```


現在のGuardDuty Runtime MonitoringはEKS EC2ノードとEKS Auto Modeをサポートしていますが、EKS Hybrid NodesとEKS Fargateは対象外です。公式のOS／カーネル／アーキテクチャ／agent versionの対応表とカバレッジの状態を確認してください。この機能を有効にしても、すべてのノードが正常にカバーされるとは限りません。

Hubbleの`--verdict DROPPED`はドロップを示します。すべてのドロップがNetworkPolicyによる拒否とは限りません。ドロップ理由とポリシー判定を合わせて確認してください。

<span id="forensics-container"></span>

## インシデント対応

### Podの隔離手順

標準のNetworkPolicyは許可ルールの和集合として適用されます。ingress／egressが空のリストを持つポリシーを追加しても、別のポリシーが許可する接続を上書きしません。アプリケーションのラベルが、そのアプリケーションに属する複数のPodを選択する場合があります。

1. namespace、Pod UID、ノード、owner、既存のNetworkPolicyを特定します。
2. 承認された隔離方式を選びます。CNI固有の明示的denyや既存allowの変更では、対象、影響、復旧方法を具体的に確認します。
3. 既存接続と新しい接続をテストし、hostNetwork、ノード通信、CNIの制限を考慮します。
4. 証拠を保護し、隔離、中断、復旧についての判断を記録します。

### 証拠の収集とフォレンジック

```bash
#!/usr/bin/env bash
# Authorized read-only Kubernetes API collection. Sensitive output stays in a private directory.
set -euo pipefail
if [[ $# -ne 3 ]]; then
  printf 'Usage: %s NAMESPACE POD OUTPUT_DIRECTORY\n' "$0" >&2
  exit 2
fi
namespace=$1
pod_name=$2
evidence_dir=$3
if [[ ! $namespace =~ ^[a-z0-9]([-a-z0-9]*[a-z0-9])?$ ]] || [[ ! $pod_name =~ ^[a-z0-9]([-a-z0-9.]*[a-z0-9])?$ ]]; then
  printf 'Invalid namespace or pod name\n' >&2
  exit 2
fi
umask 077
mkdir -- "$evidence_dir"
kubectl get pod "$pod_name" -n "$namespace" -o json > "$evidence_dir/pod.json"
kubectl describe pod "$pod_name" -n "$namespace" > "$evidence_dir/describe.txt"
kubectl logs "$pod_name" -n "$namespace" --all-containers=true --timestamps=true > "$evidence_dir/logs.txt"
# Previous logs may not exist. Record this separately instead of calling collection complete silently.
if ! kubectl logs "$pod_name" -n "$namespace" --all-containers=true --previous=true --timestamps=true > "$evidence_dir/previous-logs.txt" 2> "$evidence_dir/previous-logs-error.txt"; then
  printf 'Previous logs unavailable; inspect previous-logs-error.txt\n' >&2
fi
(
  cd -- "$evidence_dir"
  sha256sum -- pod.json describe.txt logs.txt previous-logs.txt previous-logs-error.txt > SHA256SUMS
)
printf 'API evidence written to %s. This is not a memory or filesystem snapshot.\n' "$evidence_dir"
```


このスクリプトはAPI経由でPodのメタデータとログを収集し、チェックサムを記録します。実際のクラスターではなく、subprocessの代替実装を使って、失敗時の動作と権限0700の非公開出力ディレクトリを含めてテストしました。Pod specやログには秘密情報や個人情報が含まれる可能性があります。承認された保存先とアクセス制御を使ってください。

新しいフォレンジックPodが対象ノード上で実行されたり、対象プロセスのnamespaceを共有したりするとは限りません。hostPath `/proc`、SYS_PTRACE、NET_ADMINは大きな権限を与えます。必要な場合は承認された手順に従ってください。emptyDirは永続的な証拠保存先ではありません。ephemeral containerの`/`をアーカイブしても、対象コンテナのファイルシステムのsnapshotになるとは限りません。

<span id="falco-to-elasticsearch"></span>
<span id="prometheus-grafana-dashboard"></span>

<span id="siemsoar-integration"></span>

## SIEM／SOARとの連携

ServiceMonitorのnamespace、selector、portを実際のServiceと照合してください。Falco chartにはmetrics Serviceがあり、FalcosidekickはHTTP portでメトリクスを公開します。Sidekick chartがServiceMonitorを生成するのは、`monitoring.coreos.com/v1`が利用できる場合のみです。

```promql
sum by (priority) (rate(falcosecurity_falcosidekick_falco_events_total[5m]))
```

これはFalcosidekick 2.35.0の受信イベントカウンターです。元の`falco_events_total`を常に使えるメトリクス名として扱わないでください。累積件数と一定期間のレートを区別し、実際のラベル、リセット、出力失敗、scrapeの欠落を確認してください。合成Slack／PagerDuty／SIEM通知のテストであっても、受信者と運用手順を調整してください。

<span id="table-of-contents"></span>
<span id="recommendations"></span>

## まとめ

ローカル検証では、2つのFalcoルール、4つの設定スキーマケース、3つのTetragon JSONフィルターと2つのCRD、3つのHelm chart、4つの証拠収集スクリプトの成功／失敗ケースを確認しました。カーネルへのアタッチ、検知の有効性、実際の強制動作、GuardDutyのカバレッジ、監査ログ／CloudWatchの収集、外部通知は実行していません。

## 参考資料

- [FalcoのKubernetesインストール](https://falco.org/docs/setup/kubernetes/)
- [Falco 0.45.0の設定](https://github.com/falcosecurity/falco/blob/0.45.0/falco.yaml)
- [Falcosidekick 2.35.0の設定](https://github.com/falcosecurity/falcosidekick/blob/2.35.0/config_example.yaml)
- [Tetragonのtracing policy](https://tetragon.io/docs/concepts/tracing-policy/)
- [Tetragonの強制制御](https://tetragon.io/docs/concepts/enforcement/)
- [Tetragon 1.7.1のファイル監視](https://github.com/cilium/tetragon/blob/v1.7.1/examples/quickstart/file_monitoring.yaml)
- [Kubernetes監査](https://kubernetes.io/docs/tasks/debug/debug-cluster/audit/)
- [NetworkPolicyの意味と動作](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Seccomp](https://kubernetes.io/docs/tutorials/security/seccomp/)
- [AppArmor](https://kubernetes.io/docs/tutorials/security/apparmor/)
- [EKSコントロールプレーンログ](https://docs.aws.amazon.com/eks/latest/userguide/control-plane-logs.html)
- [GuardDuty EKSランタイム監視の要件](https://docs.aws.amazon.com/guardduty/latest/ug/prereq-runtime-monitoring-eks-support.html)
- [MITRE ATT&CKコンテナ](https://attack.mitre.org/matrices/enterprise/containers/)
