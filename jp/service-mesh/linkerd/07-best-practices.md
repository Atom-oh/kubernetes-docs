# Linkerdベストプラクティス

> **最終更新日**: 2026年10月16日 · Linkerd edge-26.10.1 / charts 2026.10.1

選択したバージョンと前提条件は、[導入](01-installation.md)、[セキュリティ](04-security.md)、[可観測性](05-observability.md)、[マルチクラスター](06-multi-cluster.md)の各ガイドで確認してください。本章では各手順を運用レビューにつなげますが、環境が本番運用に適していると認定するものではありません。

変更を加える前に、対象のKubernetesコンテキスト、APIエンドポイント、リソースの所有者を選び、内容を確認してください。以下のコマンドでは現在のコンテキストと例示用の名前空間／ワークロード名を使います。このレビューでは実際のアップグレード、ロールバック、移行、負荷テストは行っていません。

## 準備状況レビュー

- [ ] Kubernetes、Linkerd、Gateway APIの互換性と、選択したディストリビューションのリリースノートを確認する。
- [ ] 実際のレプリカ数、配置、容量、障害時の動作、admission policyを確認する。
- [ ] ルート証明書、issuer、ワークロード証明書の有効期間を分け、それぞれの更新・復旧手順を検証する。
- [ ] 拒否される呼び出し元やメッシュに参加していない経路も含め、必要なID・認可動作をテストする。
- [ ] メトリクス、ログ、トレースの要件、アラート配信、データ欠損の検出を確認する。
- [ ] リソースの所有者、保護されたバックアップ、バージョンごとの更新・復旧手順、運用責任者を記録する。

信頼の共有が必要なのは、意図したメッシュ接続先との間だけであり、無関係なすべてのクラスターに広げる必要はありません。ServiceProfileは常に必要な準備要件ではありません。現行のGateway APIポリシーと互換性プロファイルでは、役割と優先順位が異なります。

```bash
linkerd version
linkerd check
linkerd check --proxy
kubectl -n linkerd get deployments,pods,poddisruptionbudgets
kubectl -n my-app get pods -o wide
```

checkコマンドの出力全体と終了ステータスを保存してください。「valid」をgrepすると「invalid」にも一致するうえ、grepが成功することで元のコマンドの失敗が隠れる場合があります。

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

コマンドが成功しても警告を確認してください。コントロールプレーンのcheckが正常でも、アプリケーションのSLOやリージョン切り替え時の動作が保証されるわけではありません。

## リソース割り当て

リクエスト数と同時接続数、プロトコル、ペイロード／ストリームのサイズ、サービス検出の規模、テレメトリーのカーディナリティ、メモリ圧迫、CPUスロットリングなど、実際のワークロードの挙動に基づいてリソースを決めます。RPSだけではプロキシに必要なリソースは判断できません。

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

整合性のある1つのYAMLマッピングを使ってください。同じマッピング内で`proxy:`を3回繰り返すのは不正です。寛容なローダーでは、エラーを出さず最後の値だけが残ることがあります。

既存のワークロードに適用する場合は、この**マージパッチ**を`proxy-resources-patch.yaml`として保存します。

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

`kubectl top pod --containers`はコンテナごとのデータを取得するコマンドで、`-c linkerd-proxy`による絞り込みには対応していません。メトリクス基盤がネイティブsidecarを想定どおり報告しているか確認してください。単一の表示だけで不在と判断せず、Podのspecとstatus、リソースメトリクスを合わせて確認します。

### ランタイムワーカーとCPUクォータ

CPUのrequestsとlimitsは、スケジューリングとCPU割り当てを設定します。limitを4にしても、プロキシのワーカースレッドが4つになるわけではありません。選択したチャートでは、ランタイムワーカー数に別の上下限を設定します。

```yaml
proxy:
  runtime:
    workers:
      minimum: 1
      maximum: 4
      maximumCPURatio: 1
```

これは独立したvaluesの抜粋です。最上位のキーを重複させず、ネストしたフィールドをマージしてください。リリース済みチャートはワーカー数の最小値・最大値とCPU比率を、KubernetesのCPU limitとは別に出力します。ランタイムの挙動は利用可能なCPUと負荷にも左右されるため、上限だけを増やしても性能が改善するとは限りません。従来の固定値`proxy.cores`はテンプレートで非推奨になっています。

## 高可用性

### 中核コントロールプレーン

**同じチャートリリースのHAプロファイル**を基準にし、証明書設定を含むレビュー済みvaluesと組み合わせます。

```bash
set -euo pipefail
umask 077
# Use the same reviewed chart version for the profile and render.
curl --fail --show-error --location \
  https://raw.githubusercontent.com/linkerd/linkerd2/edge-26.10.1/charts/linkerd-control-plane/values-ha.yaml \
  -o values-ha.yaml
helm template linkerd-control-plane linkerd-edge/linkerd-control-plane \
  --version 2026.10.1 -n linkerd \
  -f reviewed-core-values.yaml -f values-ha.yaml > reviewed-ha.yaml
```

同梱のプロファイルは、コントローラーのレプリカを3つにし、コントロールプレーンのPDBを3つ設定します。また、コンポーネントごとの必須node anti-affinity、ゾーン分散の優先ルール、fail-closedの注入に加え、リソースとロールアウトの設定も行います。レンダリング後のDeployment、PDB、Webhookの各オブジェクトと、実際に配置可能なノードを確認してください。valuesファイルは順番にマージされるため、HAプロファイルが先に指定したリソース設定を上書きすることがあります。最終結果を確認し、追加の上書きを行う場合も重要なHA設定を維持してください。

旧ネスト`destination.replicas/resources`、`identity.replicas/resources`、`proxyInjector.replicas/resources`は無視されました。対応resourceには`destinationResources`、`identityResources`、`proxyInjectorResources`と同梱profileの他フィールドがあります。任意の`podAntiAffinity`、`topologySpreadConstraints`、`podDisruptionBudget`が自動的にPod設定へ変換されるわけではありません。

レプリカが3つあってもquorumは保証されません。配置可能なノードが少なければレプリカはPendingになり、ゾーン分散の優先ルールも各ゾーンに1つずつ配置される保証にはなりません。PDBが制限するのは対応する自発的な退避であり、すべての障害やコントローラー主導のロールアウトを防ぐものではありません。

### Vizとメトリクス可用性

保持期間、認証、高可用性を適切に設定した外部のPrometheus／queryエンドポイントを用意している場合、次のvaluesでステートレスなVizコンポーネントをスケールできます。

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

レプリカ数だけでは、障害ドメインの分離、中断への保護、メトリクスの可用性は確保できません。実際の配置と、レプリカ間の重複排除を含む外部query構成を検証してください。

別の方法として、**単一のローカルPrometheus**にデータを永続化できます。

```yaml
prometheus:
  enabled: true
  persistence:
    accessMode: ReadWriteOnce
    size: 50Gi
```

動作するdefault StorageClass、またはチャートで適切なストレージクラスを明示する設定が必要です。選択したVizチャートではPrometheusは1レプリカで、PVCとRecreate戦略を使います。旧設定の`prometheus.replicas:2`は無視され、accessModeを指定しない`persistence.enabled:true`は無効なPVCを生成しました。永続化は再起動後もデータを保持する助けになりますが、Prometheusの高可用性を実現するものではありません。

## 更新と復旧

### 版変更前に経路を選ぶ

公開Linkerdの配布物はedgeトラックを使います。ベンダーが提供するstableディストリビューションでは、サポート対象の更新手順が異なることがあります。公開版のインストーラーは、stable版の導入やダウングレードに使える汎用インストーラーではありません。導入ガイドに従って、選択したCLIを取得して検証してください。

edgeのバージョン番号は、semverに基づく互換性を保証しません。リリース固有の変更点と許容されるcontrol plane／data planeのバージョン差を確認し、必要なら中間リリースを経由してください。`check --pre`はインストール前の確認であり、既存メッシュがアップグレード可能かを判定するテストではありません。

リソースの所有者と連携して、必要なvaluesと認証情報をバックアップし、秘密鍵を保護したうえで復元をテストしてください。`helm get values`の出力にはissuerの機密情報が含まれる可能性があるため、公開してはいけません。旧チャートが計算したdefault値を新しいチャートにそのまま適用せず、レビュー済みの更新先valuesを準備してください。

### CLIで管理するインストール

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

### Helmで管理するインストール

target例2026.10.1は、実導入版からの経路を検証した場合のみ使えます。

```bash
set -euo pipefail
umask 077
helm get values linkerd-control-plane -n linkerd > current-core-values.yaml
helm get values linkerd-viz -n linkerd-viz > current-viz-values.yaml
# Prepare reviewed target values and approved migration steps before these changes.
helm upgrade linkerd-crds linkerd-edge/linkerd-crds \
  --version 2026.10.1 -n linkerd --wait --timeout 10m
helm upgrade linkerd-control-plane linkerd-edge/linkerd-control-plane \
  --version 2026.10.1 -n linkerd -f reviewed-core-values.yaml \
  --wait --timeout 10m
linkerd check
helm upgrade linkerd-viz linkerd-edge/linkerd-viz \
  --version 2026.10.1 -n linkerd-viz -f reviewed-viz-values.yaml \
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

以前の「blue-green」例では第2のnamespaceを作成して`proxy-version`を変更していました。このannotationが選択するのはproxy imageであり、control planeではありません。どちらのnamespaceも、既定のレンダリングではadmission webhookなどのクラスター全体で一意な名前を共有します。namespaceを2つ作るだけでは、隔離した共存や安全なワークロード移行にはなりません。リソースの所有者とトラフィック／IDの選択を明示できる、ディストリビューションがサポートする設計を使い、復旧手段を検証できるまで確保してください。


## メッシュへの参加とプロトコル処理

新しいPodを名前空間単位でメッシュに参加させるには、次のように設定します。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: my-app
  annotations:
    linkerd.io/inject: enabled
```

既存のワークロードを対象外にする場合は、Deployment全体ではなくPodテンプレートへのマージパッチを使います。

```yaml
spec:
  template:
    metadata:
      annotations:
        linkerd.io/inject: disabled
```

アノテーションを変更しただけでは、稼働中のproxyや手動で埋め込んだproxyは削除されません。ワークロードの実際のマニフェストを整合させ、必要に応じてリソースの所有者を通じて再作成してください。`containers`と`initContainers`の両方を確認します。通常のコンテナ一覧に表示されないことだけを理由に、native sidecarが存在しないと判断してはいけません。

Opaque portではHTTPプロトコル検出をスキップしますが、関連するTCP proxy経路、mTLS、ポリシーは維持されます。構成済みのMySQLワークロードには、Podテンプレートへのパッチと整合するServiceアノテーションを使ってください。

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

PodとServiceのポートマッピングは一致させる必要があります。選択したServerリソースの`proxyProtocol`もプロトコル処理に影響します。Opaque modeでは、そのストリームのHTTP route metricsは提供されません。

一方、skip-inbound-portsやskip-outbound-portsはproxy経路を迂回するため、メッシュ暗号化、ポリシー、テレメトリーが失われる可能性があります。Redis、Memcached、データベースのポートを、汎用的な遅延最適化としてスキップすることは推奨しないでください。

ServiceProfileのroute timeoutはリクエストの期限であり、接続プールの設定ではありません。また、すべてのアプリケーションでHTTP/1接続がエンドツーエンドでHTTP/2になることを保証するものでもありません。調整する前に、実際の接続再利用、バッファリング、プロトコルの挙動を測定してください。

## 証明書運用

公開ルート証明書、issuerの認証情報、proxyのリーフ証明書、Webhook証明書は、それぞれ異なるライフサイクルと所有者を持つものとして扱ってください。既定の短命なproxyリーフ証明書は、「残存期間が60日以上」といった一般的なチェックリストを満たせません。設定された有効期間と更新に必要なリードタイムに基づいて、しきい値を決めます。

セキュリティガイドにある、検証済みの認証情報の確認方法、issuerのreloadとイベント、cert-managerの所有権設定例を使ってください。`isCA:true`を設定するだけでは、Issuerの作成、信頼ルートの配布、すべての利用側でのローテーション、アラート配信は行われません。

以前の証明書確認CronJobは、未検証の古いCLIイメージを使い、必要なRBACが不足し、grepによってcheckの失敗を隠していました。定期確認には、サポートされるランタイム、範囲を限定した認証情報、明示的な失敗処理、検証済みの通知経路が必要です。上記のcheckとログの例は終了ステータスを保持し、セキュリティガイドにはメトリクスに基づくアラートの例があります。通知連携がなければ、どちらも完成した通知サービスとはいえません。

## 証拠に基づくトラブルシューティング

proxy注入の問題では、namespaceと実際のPodテンプレート／Podのメタデータ、両方のコンテナ種別、Webhook設定、injectorのログを確認してください。

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

遅延や不安定さがある場合は、アプリケーションの挙動、リソースの圧迫、Pending状態のPod、endpoint、DNS、プロトコル検出、証明書やポリシーのエラーを比較してください。timeoutを延ばしたりcontrol plane全体を再起動したりするだけでは、原因の診断になりません。

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

`linkerd identity`は公開リーフ証明書を取得します。proxyイメージ内に固定の`end-entity.crt`ファイルがあると想定しないでください。ServiceProfileの`viz routes`や現行ポリシーの診断は、実際に設定されているリソースに対してのみ使います。ログを読むときは、対象となるcontrollerのコンテナを明示してください。

対象修正後はコマンド成功だけでなく元の失敗経路を検証します。

## Istioからの移行

移行を設計する前に、各ワークロードで使われている機能とセキュリティ特性を棚卸ししてください。以下は**機能の一部を比較したもの**であり、マニフェストを機械的に変換できることを示すものではありません。

| Istio概念 | Linkerdでの考慮 |
|---|---|
| VirtualService | 対応するGateway APIのルーティング機能を使います。ServiceProfileは互換性のためのインターフェースで、完全な代替ではありません |
| DestinationRule | 負荷分散、failure accrual、接続の挙動、TLS要件を個別に見直します |
| PeerAuthentication STRICT | Linkerdの既定ポリシーはメッシュに参加していない平文通信を許可する場合があるため、自動mTLSだけでは不十分です。適切な認可を必須にしてください |
| AuthorizationPolicy | Linkerdでは対象リソースと認証のモデルが異なります。JWTやユーザーclaimなどの条件は別途設計が必要です |
| Sidecar通信範囲 | 注入アノテーションやネットワークファイアウォールと一律に同等とはみなせません |
| Gateway | 適切なIngress／Gatewayの実装とLinkerdとの統合を選択して設定します |

従来の注入ラベル、revisionラベル／tag、Podアノテーション、手動注入マニフェスト、ambientへの参加はそれぞれ異なります。`istio-injection`だけを削除しても、すべての参加方法には対応できません。ワークロードを変更する前に、実際のIstio／Linkerd CNIとproxyへの参加状況を確認してください。

IstioとLinkerdのメッシュmTLSが自動的に相互運用すると想定しないでください。両者が混在する移行段階では、トラフィックとセキュリティの境界を明示し、アプリケーションの挙動を検証する必要があります。同じワークロードを両方のトラフィック捕捉経路に誤って参加させないでください。依存関係がnamespaceをまたぐ場合、namespaceだけを安全な移行単位とすることはできません。

実務上は、まず依存関係とポリシーを棚卸しして隔離環境で再現し、許可・拒否される通信と復旧をテストしてから、意図的に選んだワークロード群を移行します。正しい参加制御を整合させ、想定したproxy経路だけが使われていることを確認し、代表的なトラフィックを測定してから対象を広げてください。必要な利用側がなく、選択した復旧計画を実行できると確認してから、古いcontrol planeやリソースを削除します。

この手順は、無条件にnamespaceラベルを変更して再起動・アンインストールする方法や、図にあった誤った1対1の機能対応に代わるものです。アプリケーションの互換性と本番環境での移行は、環境ごとに検証してください。

## 参考資料

- [選択HA profile](https://github.com/linkerd/linkerd2/blob/edge-26.10.1/charts/linkerd-control-plane/values-ha.yaml)
- [Proxy設定](https://linkerd.io/docs/reference/proxy-configuration/)
- [リリースproxy runtime template](https://github.com/linkerd/linkerd2/blob/edge-26.10.1/charts/partials/templates/_proxy.tpl)
- [更新ガイダンス](https://linkerd.io/docs/tasks/upgrade/)
- [認可ポリシー](https://linkerd.io/docs/reference/authorization-policy/)
- [Istio注入](../istio/advanced/07-sidecar-injection.md)と[ambientモード](../istio/advanced/01-ambient-mode.md)
