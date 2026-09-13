# Linkerdベストプラクティス

> **最終更新**: September 11, 2026 · Linkerd edge-26.9.1 / charts 2026.9.1

選択版と前提条件は[導入](01-installation.md)、[セキュリティ](04-security.md)、[可観測性](05-observability.md)、[マルチクラスター](06-multi-cluster.md)を使います。本章は手順を運用レビューへつなぎ、環境の本番準備を認定しません。

変更前に意図Kubernetes context、API endpoint、所有者を選び確認します。以下は現在のcontextと例の名前空間/workload名を使います。監査では実更新、rollback、移行、負荷テストをしていません。

## 準備状況レビュー

- [ ] Kubernetes/Linkerd/Gateway API互換性と選択ディストリビューションのrelease noteを確認。
- [ ] 実レプリカ、配置、容量、中断、admissionを確認。
- [ ] Root、issuer、workload証明書の寿命を分け、更新/復旧手順を検証。
- [ ] 拒否callerと未参加経路も含む必要ID/認可動作をテスト。
- [ ] メトリクス、ログ、トレース要件、通知配信、欠損検出を確認。
- [ ] 所有権、保護バックアップ、版別更新/復旧手順、運用責任を記録。

共有信頼が必要なのは意図したリンク関係で、無関係な全clusterではありません。ServiceProfileは普遍的準備要件ではなく、現Gateway API policyと互換profileは役割/優先順位が異なります。

```bash
linkerd version
linkerd check
linkerd check --proxy
kubectl -n linkerd get deployments,pods,poddisruptionbudgets
kubectl -n my-app get pods -o wide
```

全check出力と終了コードを保持します。「valid」のgrepは「invalid」にも一致し、grep成功の裏にコマンド失敗を隠し得ます。

```bash
#!/usr/bin/env bash
set -euo pipefail
umask 077
if linkerd check --proxy > linkerd-check.log 2>&1; then
  cat linkerd-check.log
else
  check_status=$?
  cat linkerd-check.log >&2
  exit "$check_status"
fi
```

終了成功でも警告を確認します。健全control-plane checkはアプリSLOや地域切り替え動作を証明しません。

## リソース割り当て

要求/接続同時数、protocol、payload/streamサイズ、検出規模、telemetry cardinality、メモリ圧力、CPU throttlingなど実動作から決めます。RPSだけではproxy resourceは決まりません。

これは**初期設定例**で容量保証ではありません。

```yaml
proxy:
  resources:
    cpu:
      request: 100m
      limit: 1000m
    memory:
      request: 64Mi
      limit: 250Mi
```

一貫した1 YAML mappingを使います。同じmapで`proxy:`を3回繰り返すのは不正で、寛容loaderは最後だけ黙って残す場合があります。

既存workloadにはこの**マージパッチ**を`proxy-resources-patch.yaml`へ保存します。

```yaml
spec:
  template:
    metadata:
      annotations:
        config.linkerd.io/proxy-cpu-request: 500m
        config.linkerd.io/proxy-cpu-limit: 2000m
        config.linkerd.io/proxy-memory-request: 128Mi
        config.linkerd.io/proxy-memory-limit: 500Mi
```

```bash
# A merge patch for one existing, reviewed workload; this starts a rollout.
kubectl -n my-app patch deployment/api --type merge --patch-file proxy-resources-patch.yaml
kubectl -n my-app rollout status deployment/api --timeout=5m
kubectl -n my-app top pod --containers
```

`kubectl top pod --containers`はcontainer別データを要求し、`-c linkerd-proxy`フィルターはありません。native init sidecarをmetrics pipelineが期待どおり報告するか確認します。1表示から不在と推測せず、Pod spec/statusとresource metricsを併用します。

### ランタイムワーカーとCPUクォータ

CPU requests/limitsは配置/CPU割り当てを設定します。limit 4はproxy worker thread 4つを直接要求しません。選択チャートには別runtime worker範囲があります。

```yaml
proxy:
  runtime:
    workers:
      minimum: 1
      maximum: 4
      maximumCPURatio: 1
```

独立values抜粋で、最上位キーを重複させずネストフィールドをマージします。チャートはworker min/max/CPU比をKubernetes CPU limitと別に出力します。runtimeは利用可能CPUと需要にも依存し、上限増加だけで性能改善ではありません。旧固定`proxy.cores`はtemplateで非推奨です。

## 高可用性

### 中核コントロールプレーン

**同じチャートreleaseのHA profile**から始め、証明書を含むreview済みvaluesと重ねます。

```bash
set -euo pipefail
umask 077
# Use the same reviewed chart version for the profile and render.
curl --fail --show-error --location \
  https://raw.githubusercontent.com/linkerd/linkerd2/edge-26.9.1/charts/linkerd-control-plane/values-ha.yaml \
  -o values-ha.yaml
helm template linkerd-control-plane linkerd-edge/linkerd-control-plane \
  --version 2026.9.1 -n linkerd \
  -f reviewed-core-values.yaml -f values-ha.yaml > reviewed-ha.yaml
```

同梱profileはcontroller 3レプリカ、制御PDB 3つ、component別必須node anti-affinity、希望zone分離、fail-closed注入を設定し、resourceとrollout設定も供給します。render済みDeployment/PDB/Webhookと実適格nodeを確認します。valuesは順にmergeするためHAが前のresourceを上書きし得ます。最終結果を調べ、追加上書きでも重要HAを保持します。

旧ネスト`destination.replicas/resources`、`identity.replicas/resources`、`proxyInjector.replicas/resources`は無視されました。対応resourceには`destinationResources`、`identityResources`、`proxyInjectorResources`と同梱profileの他フィールドがあります。任意の`podAntiAffinity`、`topologySpreadConstraints`、`podDisruptionBudget`が自動的にPod設定へ変換されるわけではありません。

3レプリカはquorum保証ではありません。適格node不足ではPendingになり、希望zone規則は各zone 1つを保証しません。PDBは対応自発evictionを制限し、全障害/全controller rolloutは防ぎません。

### Vizとメトリクス可用性

意図した保持、認証、HAを持つ別途準備済みPrometheus/query endpoint向けに、次はステートレスVizを拡張します。

```yaml
prometheus:
  enabled: false
prometheusUrl: http://prometheus.monitoring.svc.cluster.local:9090
tap:
  replicas: 2
metricsAPI:
  replicas: 2
tapInjector:
  replicas: 2
dashboard:
  replicas: 2
```

数だけでは障害domain分離、中断保護、metrics可用性は成立しません。実配置とreplica重複排除を含む外部query構成を検証します。

代替として**単一local Prometheus**で永続化できます。

```yaml
prometheus:
  enabled: true
  persistence:
    accessMode: ReadWriteOnce
    size: 50Gi
```

動作するdefault StorageClassか適切な明示設定が必要です。選択VizはPrometheusを1レプリカとしPVCでRecreateを使います。旧`prometheus.replicas:2`は無視され、accessModeなしの`persistence.enabled:true`は無効PVCを作りました。永続化は再起動をまたぐ保持を助けますがHAではありません。

## 更新と復旧

### 版変更前に経路を選ぶ

公開Linkerdはedge系列で、ベンダーstableは対応更新手順が異なり得ます。公開installerは汎用stable/降格installerではありません。導入ガイドの方法で選択CLIを取得・検証します。

edge版番号はsemver互換性保証ではありません。release固有変更と許可control/data-plane skewを確認し、必要なら中間版を使います。`check --pre`は導入前確認で既存メッシュ更新適格テストではありません。

所有者経由で希望valuesと必要認証情報をバックアップし、鍵を保護して復元テストします。`helm get values`はissuer素材を露出し得るので公開しません。旧計算defaultを新チャートへ盲目的適用せずreviewしたtarget valuesを用意します。

### CLI所有の導入

対応経路を承認し、現設定/認証情報を保持した後:

```bash
set -euo pipefail
# The selected, verified target CLI must already be on PATH.
linkerd version --client
linkerd check
linkerd check --proxy
linkerd upgrade --crds | kubectl apply -f -
linkerd upgrade | kubectl apply -f -
linkerd check
# CLI-owned Viz only; preserve its complete reviewed configuration.
linkerd viz install -f reviewed-viz-values.yaml | kubectl apply -f -
linkerd viz check
```

CRD、core、互換拡張、workload proxyの順で更新します。現拡張CLIは完全設定の`install`で、`linkerd viz upgrade`はありません。release別pruning/移行を確認し、古いresource候補は削除前に調べます。

multiclusterはガイドの希望Helm `controllers`と現Link/credential所有権を保持します。自動更新手順として非推奨の旧link管理controllerを再作成しません。

### Helm所有の導入

target例2026.9.1は、実導入版からの経路を検証した場合のみ使えます。

```bash
set -euo pipefail
umask 077
helm get values linkerd-control-plane -n linkerd > current-core-values.yaml
helm get values linkerd-viz -n linkerd-viz > current-viz-values.yaml
# Prepare reviewed target values and approved migration steps before these changes.
helm upgrade linkerd-crds linkerd-edge/linkerd-crds \
  --version 2026.9.1 -n linkerd --wait --timeout 10m
helm upgrade linkerd-control-plane linkerd-edge/linkerd-control-plane \
  --version 2026.9.1 -n linkerd -f reviewed-core-values.yaml \
  --wait --timeout 10m
linkerd check
helm upgrade linkerd-viz linkerd-edge/linkerd-viz \
  --version 2026.9.1 -n linkerd-viz -f reviewed-viz-values.yaml \
  --wait --timeout 10m
linkerd viz check
```

CRD、core、CNI、拡張を既存所有者の下に保持します。マニフェストが似ていてもHelm所有にCLI applyを混ぜないでください。

### ワークロードのロールアウト

関連StatefulSet/DaemonSet/Jobも含む実メッシュcontrollerを選び、アプリ固有rolloutを調整します。namespace全体ループは無関係workloadを再起動し、固定30秒sleepは安定化テストではありません。

```bash
# One explicitly selected meshed Deployment, after checking disruption/capacity.
kubectl -n my-app rollout restart deployment/api
kubectl -n my-app rollout status deployment/api --timeout=5m
linkerd check --proxy -n my-app
linkerd viz stat deployment/api -n my-app
```

次へ進む前にreadiness、ID/policy、代表通信を確認します。namespaceアノテーションは新Podに作用し、稼働sidecarをその場で更新しません。

### 復旧と複数コントロールプレーン

特定版/CRD向けの検証済み復旧を定義します。core Helm rollbackだけでは別管理CRD、全認証変更、稼働proxyも戻りません。任意の旧CLIを取得してupgradeしても普遍的降格手順にはなりません。

旧「blue-green」例は第2namespaceを作り`proxy-version`を変更しました。その指定はproxy imageでcontrol planeではありません。両namespaceのdefault renderはadmission webhookなどcluster全体名も共有します。第2namespaceだけでは隔離共存/安全移行は成立しません。明示所有権とtraffic/ID選択を持つ対応設計を使い、確認まで復旧能力を保持します。


## 参加とプロトコル処理

新Podの名前空間参加:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: my-app
  annotations:
    linkerd.io/inject: enabled
```

既存workloadの除外はPodテンプレートmerge patchで、完全Deploymentではありません。

```yaml
spec:
  template:
    metadata:
      annotations:
        linkerd.io/inject: disabled
```

アノテーションだけでは稼働/手動埋込proxyを除去しません。実マニフェストを整合し必要なら所有者経由で再作成します。`containers`と`initContainers`両方を見ます。通常一覧にないだけでnative sidecar不在とはなりません。

opaque portはHTTP検出をskipし、関連TCP proxy経路、mTLS、policyは保持します。準備済みMySQLにはPodテンプレートpatchと整合Serviceアノテーションを使います。

```yaml
spec:
  template:
    metadata:
      annotations:
        config.linkerd.io/opaque-ports: '3306'
---
apiVersion: v1
kind: Service
metadata:
  name: mysql
  namespace: my-app
  annotations:
    config.linkerd.io/opaque-ports: '3306'
spec:
  selector:
    app: mysql
  ports:
  - name: mysql
    port: 3306
    targetPort: 3306
```

Pod/Service port対応は一致が必要です。選択Serverの`proxyProtocol`も影響します。opaque modeはそのstreamのHTTP route metricsを提供しません。

一方skip-inbound/outbound-portsはproxyを迂回し、暗号化、policy、telemetryを失い得ます。Redis、Memcached、DB portを汎用遅延最適化としてskipするよう勧めないでください。

ServiceProfile route timeoutは期限で接続pool設定ではありません。また全アプリHTTP/1接続がend-to-end HTTP/2になる保証でもありません。調整前に実接続再利用、buffer、protocolを測ります。

## 証明書運用

公開root、issuer、proxy leaf、Webhook証明書を別ライフサイクル/所有者として扱います。既定短命leafは一般的な残存60日checklistを満たせません。設定寿命と更新余裕からしきい値を選びます。

securityガイドの検証済み確認、issuer reload/event、cert-manager所有権例を使います。`isCA:true`だけではIssuer導入、root配布、全consumer rotation、alert配信は設定されません。

旧証明書CronJobは未検証旧CLI、必要RBAC不足、grepで失敗を隠す構成でした。定期確認には対応runtime、限定認証情報、明示失敗処理、検証済み配信経路が必要です。上のcheck/logは終了コードを保持し、securityガイドはmetrics alertを示します。統合なしではどちらも完成した通知サービスではありません。

## 証拠に基づくトラブルシューティング

注入問題ではnamespaceと実Podテンプレート/Pod metadata、両container種別、Webhook設定、injectorログを確認します。

```bash
kubectl get namespace my-app -o yaml
kubectl -n my-app get deployment api -o yaml
# Set this to an actual API Pod.
api_pod=api-example-pod
kubectl -n my-app get pod "$api_pod" -o json | jq '{
  annotations: .metadata.annotations,
  containers: [.spec.containers[]? | {name,image,resources}],
  initContainers: [.spec.initContainers[]? | {name,image,restartPolicy,resources}],
  status: .status
}'
kubectl get mutatingwebhookconfiguration linkerd-proxy-injector-webhook-config
kubectl -n linkerd logs deployment/linkerd-proxy-injector -c proxy-injector --tail=100
```

遅延/不安定ではアプリ動作、resource圧力、Pending、endpoint、DNS、protocol検出、証明書/policyエラーを比較します。timeout延長やcontrol plane全体再起動は診断ではありません。

```bash
linkerd check
linkerd check --proxy
linkerd viz stat deploy -n my-app
linkerd viz tap deployment/api -n my-app --max-rps 20
linkerd viz edges deploy -n my-app
linkerd identity -n my-app -l app=api
kubectl -n my-app top pod --containers
kubectl -n my-app logs deployment/api -c linkerd-proxy --tail=100
kubectl -n linkerd logs deployment/linkerd-destination -c destination --tail=100
kubectl -n linkerd logs deployment/linkerd-identity -c identity --tail=100
kubectl -n linkerd get events --sort-by=.lastTimestamp
```

`linkerd identity`は公開leafを取得します。proxy内に固定`end-entity.crt`があると想定しません。ServiceProfileの`viz routes`や現policy診断は実設定resourceにだけ使い、ログ読取時は関連controller containerを明示します。

対象修正後はコマンド成功だけでなく元の失敗経路を検証します。

## Istioからの移行

移行設計前に各workloadの機能/security特性を棚卸しします。これは**部分的な機能比較**で機械的なマニフェスト変換ではありません。

| Istio概念 | Linkerdでの考慮 |
|---|---|
| VirtualService | 対応Gateway API routing。ServiceProfileは互換用で完全同等ではない |
| DestinationRule | 負荷分散、failure accrual、接続、TLSを個別再評価 |
| PeerAuthentication STRICT | 既定Linkerdは未参加平文を受け得るため自動mTLSだけでは不足。適切な認可が必要 |
| AuthorizationPolicy | target/認証モデルが異なる。JWT/user claimなどは別設計 |
| Sidecar通信範囲 | 注入アノテーションやnetwork firewallと一律同等ではない |
| Gateway | 適切なIngress/GatewayとLinkerd統合を選択・設定 |

従来注入ラベル、revision/tag、Podアノテーション、手動注入、ambient参加は別です。`istio-injection`だけを除去しても全対応にはなりません。変更前に実Istio/Linkerd CNIとproxy参加を確認します。

両mesh mTLSが自動相互運用すると想定しないでください。混在段階は明示traffic/security境界と検証済みアプリ動作が必要で、同workloadを両捕捉経路へ誤参加させないようにします。依存が越境するならnamespaceだけでは安全な移行単位ではありません。

実用的順序は依存/policyの棚卸し、隔離環境で再現、許可/拒否と復旧をテスト、意図的に選んだworkload群の移動です。正しい参加制御を整合し、意図したproxy経路だけを確認し、代表通信測定後に拡大します。必要consumerがなく、復旧計画が実行可能になってから旧control plane/resourceを除去します。

これは無条件のnamespace label/restart/uninstall手順と、図の誤った1対1機能対応を置き換えます。アプリ互換性と本番移行は環境固有の検証作業です。

## 参考資料

- [選択HA profile](https://github.com/linkerd/linkerd2/blob/edge-26.9.1/charts/linkerd-control-plane/values-ha.yaml)
- [Proxy設定](https://linkerd.io/docs/reference/proxy-configuration/)
- [リリースproxy runtime template](https://github.com/linkerd/linkerd2/blob/edge-26.9.1/charts/partials/templates/_proxy.tpl)
- [更新ガイダンス](https://linkerd.io/docs/tasks/upgrade/)
- [認可ポリシー](https://linkerd.io/docs/reference/authorization-policy/)
- [Istio注入](../istio/advanced/07-sidecar-injection.md)と[ambientモード](../istio/advanced/01-ambient-mode.md)
