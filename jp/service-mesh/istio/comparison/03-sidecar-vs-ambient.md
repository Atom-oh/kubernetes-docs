# Sidecar と Ambient Mode の選択ガイド（EKS 1.36 テスト結果）

> **対応バージョン**: Istio 1.30 / EKS 1.36
> **最終更新**: August 21, 2026

このドキュメントは、EKS 上のミッションクリティカルなワークロード（例: 暗号資産取引所の注文・マッチング経路）で Istio を **sidecar mode と ambient mode のどちらで採用するか** を判断するための、テスト結果に基づくガイドです。アーキテクチャ自体は [Ambient Mode](../advanced/01-ambient-mode.md) ですでに扱っているため、本書では繰り返しません。代わりに、4 つの具体的な要件に対するテスト結果と推奨事項を示します。

1. mTLS が必須（クラスター内部の Pod 間通信）
2. NetworkPolicy が必須
3. レイテンシーに敏感なワークロード
4. ダウンタイムゼロの rollout — ambient waypoint の 503 懸念を検証

> 💡 本書のすべての数値は、このテストサイクル専用に構築され、その後削除された **専用シングルテナント EKS クラスター**（`mesh-isolated-test`）から取得しています。専用クラスターが必要だった理由は、§4 の末尾にある [テスト分離に関する注記](#テスト分離に関する注記) を参照してください。

## 判断の概要

| 要件 | Sidecar | Ambient（L4、waypoint なし） | Ambient（L7、waypoint） | Cilium |
|---|---|---|---|---|
| mTLS | ✅ STRICT 対応、検証済み | ✅ STRICT 対応、検証済み | ✅ STRICT 対応、検証済み | ⚠️ このサイクルでは未計測 — 単一の STRICT 相当スイッチではなく、アイデンティティ相互認証と個別に有効化する WireGuard/IPsec として文書化されています（[下記](#リトライによって隠される障害と生の障害を分離する)を参照） |
| NetworkPolicy | ✅ 既存のルールがそのまま機能、検証済み | ⚠️ HBONE ポート（15008）を許可する必要あり、検証済み | ⚠️ HBONE ポート（15008）を許可する必要あり、検証済み | ⚠️ このサイクルでは未計測 — CiliumNetworkPolicy がネイティブな仕組みであり、K8s NetworkPolicy のアドオンではありません |
| レイテンシー（no-mesh ベースラインに対する P50） | +1.29ms、計測済み | +0.04ms（無視できるレベル）、計測済み | +1.86ms、計測済み | このサイクルでは未計測 |
| ダウンタイムゼロの rollout | 503 が発生（0.5%、計測済み） | **実際の 503 はゼロ**、0.3% の TCP reset に置換 | 503 が発生 **2.6%、sidecar の約 5 倍**（計測済み） | このサイクルでは未計測 |

> ✅ **一文での結論**: waypoint なしの ambient（L4 のみ）は、rollout の変動下で最も安定しており、レイテンシーのオーバーヘッドも無視できるレベルでした。waypoint（L7）を付加すると、503 率は sidecar を上回り、レイテンシーは sidecar とほぼ同水準になります。根拠は以下の §3–§4 にあります。Cilium は同等のセキュリティ比較のために含めています（[下記](#リトライによって隠される障害と生の障害を分離する)を参照）。テストクラスターにはデプロイしていないため、その行は文書化された特性のみを示しており、計測の代替にはなりません。

## 1. mTLS — テスト結果（EKS 1.36.2、Istio 1.30.2）

**テスト環境**
- 専用シングルテナントクラスター `mesh-isolated-test`（専用 VPC、他のワークロードなし）、EKS control plane と worker node はともに v1.36.2、Amazon Linux 2023（arm64、m7g.xlarge）
- Namespace スコープの `PeerAuthentication` STRICT を 3 つのテスト Namespace（sidecar / ambient-L4 / ambient-L7）に適用 — mesh 全体ではない

### チェック 1 — 平文による直接 Pod-IP アクセス（ブロックされる必要がある）

```
plaintext-client -> sidecar echo pod:8080
  [E] Read error, err="read tcp ...: read: connection reset by peer"
plaintext-client -> ambient-L4 echo pod:8080
  [E] Read error, err="EOF"
plaintext-client -> ambient-L7 echo pod:8080
  [E] Read error, err="EOF"
```

### チェック 2 — Service 経由の mesh 内アクセス（成功する必要がある）

```
sidecar client -> http://echo:8080/     => HTTP/1.1 200 OK (server: envoy)
ambient-L4 client -> http://echo:8080/  => HTTP/1.1 200 OK (no envoy headers, pure L4 passthrough)
ambient-L7 client -> http://echo:8080/  => HTTP/1.1 200 OK (server: istio-envoy, x-envoy-decorator-operation)
```

### チェック 3 — SPIFFE 証明書

`istioctl ztunnel-config certificates` / `istioctl proxy-config secret` を使用して検証済み:

| Workload | 証明書発行者 | SPIFFE ID | Root CA |
|---|---|---|---|
| ambient-L4 echo | ztunnel | `spiffe://cluster.local/ns/mesh-test-ambient-l4/sa/default` | 共有 |
| ambient-L7 echo | ztunnel | `spiffe://cluster.local/ns/mesh-test-ambient-l7/sa/default` | 共有 |
| sidecar echo | istio-proxy | `spiffe://cluster.local/ns/mesh-test-sidecar/sa/default` | 共有 |

> ✅ **判定**: 3 つの mode はすべて平文アクセスを即座にブロックし、mesh 内トラフィックだけが 200 を返し、各 Workload は同じ Root CA から発行された固有の SPIFFE ID を保持しています。sidecar と ambient はどちらも「クラスター内部の Pod 間トラフィックは mTLS でなければならない」という要件を満たします。

**違い**: ambient は mTLS を透過的に適用します — `istio-cni` が Pod の network namespace 内でトラフィックリダイレクトをセットアップし、ztunnel がポート 15008 上の HBONE（mTLS）トンネルでトラフィックを運搬します — アプリケーションコードや sidecar injection は不要です。sidecar はアプリケーション Pod 内の istio-proxy container により同じことを実現します。両 mode の証明書ローテーションと移行戦略の詳細は [mTLS](../security/01-mtls.md) を参照してください。

## 2. NetworkPolicy — テスト結果

Ambient は Pod の実トラフィックを HBONE トンネル（TCP 15008）経由で ztunnel に転送し、ztunnel が復号して宛先に配信します。つまり、**アプリケーションポート（例: 8080）のみを許可する NetworkPolicy は ambient に参加している Pod へのインバウンドトラフィックをブロックします**。これはパケットが実際には 15008 に到達するためです。ambient を NetworkPolicy と併用するには、対象 Pod に対する **TCP 15008 のインバウンド許可ルールを追加する必要があります**。

**テスト設定**: 専用 `mesh-isolated-test` クラスターで VPC CNI NetworkPolicy enforcement（`enableNetworkPolicy=true`、`aws-network-policy-agent v1.3.5-eksbuild.3`、eBPF）を有効化しました。これは、以前のラウンドで使用した共有クラスターでは安全に実施できませんでした。有効化すると、他チームに属する既存の休眠状態の NetworkPolicy 13 個が同時に有効になるためです。専用シングルテナントクラスターにより、この影響範囲の懸念を完全に排除しました。

> ⚠️ **テスト中に判明した運用上の注意点**: `enableNetworkPolicy` を有効にする *前* に作成された Pod には、遡及して enforcement が適用されません — eBPF hook は Pod network setup（CNI ADD）の時点でのみアタッチされます。sanity check によりこれを直接確認しました。すでに実行中の Pod にポート 9999 *のみ* を許可する policy を適用しても、ポート 8080 のトラフィックはブロックされずに通過しました。NetworkPolicy を有効にした後で Pod を再作成する `kubectl rollout restart` が、NetworkPolicy が有効になる前に必要でした。これは本番稼働中のクラスターで NetworkPolicy を有効化する前に知っておくべき、実際の注意点です。

**テスト 1 — ingress を TCP 8080 のみに制限**（新規 Pod、enforcement が有効であることを確認済み）

| Mode | 結果 |
|---|---|
| sidecar | ✅ 200 OK — 影響なし |
| ambient-L4 | ❌ ブロック（`i/o timeout`） |
| ambient-L7 | ❌ ブロック（`i/o timeout`） |

**テスト 2 — ingress が TCP 8080 + TCP 15008（HBONE）を許可**

| Mode | 結果 |
|---|---|
| ambient-L4 | ✅ 200 OK — 復旧 |
| ambient-L7 | ✅ 200 OK — 復旧 |

> ✅ **判定**: 実トラフィックにより上記の仮説を確認しました。ambient の Workload Pod の network namespace に到達する実際のインバウンドパケットは、アプリケーションポート（8080）ではなく ztunnel HBONE ポート（15008）に到達します。アプリケーションポートのみの NetworkPolicy は ambient に参加している Pod を暗黙に破壊します。sidecar は、パケットがすでにアプリケーションポートに到達した後に Pod 自身の network namespace 内だけで sidecar によるトラフィックキャプチャが行われるため、影響を受けません。

多層防御を推奨します。network level（NetworkPolicy）と identity level（AuthorizationPolicy）の制御を併用してください。sidecar mode における mTLS と NetworkPolicy の競合は [mTLS and NetworkPolicy Conflict](../security/01-mtls.md#7-mtls-and-networkpolicy-conflict) で扱っています。

## 3. レイテンシー — テスト結果（T5）

**テスト設定**: fortio load、200 qps、60 秒、16 connections、ケースあたり 12,000 requests、steady state（rollout restart は実行していない）— no-mesh baseline（mesh 未参加の Namespace）対 sidecar 対 ambient-L4 対 ambient-L7。すべて同じ `mesh-isolated-test` Graviton（m7g.xlarge）node 上で実行しました。全ケースで 100% Code 200 を返しました。

| ケース | P50 | P75 | P90 | P99 | P99.9 |
|---|---|---|---|---|---|
| no-mesh（ベースライン） | 0.82ms | 1.33ms | 1.73ms | 1.97ms | 2.00ms |
| sidecar | 2.11ms | 2.60ms | 2.89ms | 3.91ms | 8.00ms |
| ambient-L4（waypoint なし） | 0.86ms | 1.34ms | 1.74ms | 1.98ms | 2.93ms |
| ambient-L7（waypoint） | 2.68ms | 3.06ms | 3.63ms | 3.98ms | 7.67ms |

**no-mesh ベースラインに対する P50 オーバーヘッド**: sidecar +1.29ms · ambient-L4 +0.04ms（無視できるレベル）· ambient-L7 +1.86ms

> ✅ **判定**: 以前に引用した公開済み ambient mode benchmark（L4 のみは sidecar より低く、waypoint は sidecar とほぼ同等またはやや上）と整合しています — これらは現在、引用ではなくファーストパーティの計測値です。暗号資産取引経路のようなレイテンシーに敏感な Workload では、これは以下の §4 と一致します。**waypoint を避けることはレイテンシーと rollout の安定性の両方に役立ちます**。

## 4. ダウンタイムゼロの Rollout — 503 テスト結果（主な発見）

### 背景

Ambient での懸念は、**L7 waypoint（Envoy）が宛先 IP:Port をキーにした pool の connection を再利用する一方、** **Pod が終了しても ztunnel は waypoint に通知しない**ことです。終了した Pod の IP が新しい Pod に再割り当てされると、waypoint は無効になった connection を再利用して 503 を返す可能性があります。sidecar も類似した Pod termination race の影響を受ける可能性があります（仕組みは [Connection Errors During Pod Termination](../troubleshooting/common-errors.md#connection-errors-during-pod-termination) を参照）。EKS 1.36 で両方の障害 mode を直接比較して計測しました。

**テスト環境**
- 専用シングルテナントクラスター `mesh-isolated-test`、EKS control plane と worker node はともに v1.36.2、arm64（Graviton m7g.xlarge）、Istio 1.30.2
- 3 Namespace（sidecar / ambient-L4 / ambient-L7）で **バイト単位で同一の Workload**（6 replicas の echo server Deployment + fortio client）を実行 — 異なるのは Namespace label のみ
- fortio client は 100 req/s の keepalive connection を維持する一方、対象 Namespace の `echo` Deployment に対して `rollout restart` を繰り返し実行
- mode ごとに 60,000 requests を収集（= 100 qps × 600 秒）

### 結果

| Mode | Rollout cycles | Requests | 503 count | 503 rate | その他のエラー（-1、TCP reset/EOF） | 使用した socket |
|---|---|---|---|---|---|---|
| sidecar | 42 | 60,000 | 324 | **0.5%** | 2（0.0%） | 350 |
| ambient-L4（waypoint なし） | 64 | 60,000 | **0** | **0%** | 195（0.3%） | 1,652 |
| ambient-L7（waypoint） | 65 | 59,913 | 1,528 | **2.6%** | 84（0.1%） | 2,486 |

> 完全な keepalive であれば、使用 socket 数は 16 になります。ambient-L7 では実行終了時に 60,000 calls のうち 87 件が未完了であり、平均レイテンシー（50.4ms）は他の 2 mode（約 2–3ms）を大幅に上回りました。

<details>
<summary>fortio 実行出力（生データ）</summary>

```
[sidecar]      42 rollouts, Sockets used: 350 (16 would be perfect keepalive)
  Code 200 : 59674 (99.5 %)
  Code 503 : 324 (0.5 %)
  Code  -1 : 2   (0.0 %)

[ambient-L4]   64 rollouts, Sockets used: 1652
  Code 200 : 59805 (99.7 %)
  Code  -1 : 195 (0.3 %)   <- connection dropped with no HTTP response, not a 503

[ambient-L7]   65 rollouts, Sockets used: 2486
  Code 200 : 58301 (97.3 %)
  Code 503 : 1528 (2.6 %)
  Code  -1 : 84  (0.1 %)
  (59,913 of 60,000 calls completed; avg latency 50.4ms vs. ~2-3ms for the other two modes)
```

</details>

**判定**

1. **Ambient-L7（waypoint）の 503 率（2.6%）は、この専用クラスター上で sidecar（0.5%）の約 5 倍です** — 共有され競合状態にあったクラスターでの同日中の以前の計測が示したよりも大きな差です（下記の分離に関する注記を参照）。これにより、rollout の変動下で「waypoint の connection pool が stale connection を再利用して 503 を発生させる」という当初の懸念は弱まるどころか裏付けられました。
2. **Ambient-L4（waypoint なし）は、再び実際の HTTP 503 をゼロ件にしました。** 代わりに、0.3% の connection level TCP error（応答なしの「-1」）が発生しました。L4 では障害は *503 response* ではなく *dropped connection* として表面化します — error response を生成する proxy ではなく、client/application に再接続処理を委ねます。
3. Ambient-L7 では大きな平均レイテンシーの急増と、実行中に完了しなかった 87 requests も確認されました。これは rollout の変動と持続的な負荷が組み合わさった際に waypoint が苦戦していることと整合し、他の 2 mode とは異なります。
4. 同じ 600 秒のウィンドウ内で完了した rollout cycles（sidecar / ambient-L4 / ambient-L7 で 42 / 64 / 65）は、CPU/network を競合する他の tenant がこの専用クラスターに存在しなかったため、混雑した共有クラスターでの以前の計測よりはるかに多くなりました。*相対的な* 順序（sidecar が最も遅く、ambient-L4 が最も速い）は維持されましたが、絶対的な rollout 速度はクラスターの競合に大きく依存するため、いずれの mode にも固有の特性として過度に解釈すべきではありません。

### フォローアップ: graceful shutdown の強化後

上記のベースライン数値は **shutdown tuning をまったく行っていない**状態を反映しています。次の 2 つの変更を加えた後、同じ T1 test（100 qps × 600 秒、60,000 requests/mode）を再実行しました。

- **3 つの mode すべて**: `echo` container に `lifecycle.preStop.sleep.seconds: 10`（K8s 1.29+ のネイティブな sleep action — exec/shell は不要）と `terminationGracePeriodSeconds: 40` を設定し、Pod が実際に connection を受け付けなくなる前に Endpoint removal がクラスター全体へ伝播する時間を確保
- **Sidecar のみ**: `proxy.istio.io/config` Pod annotation 経由で `EXIT_ON_ZERO_ACTIVE_CONNECTIONS=true` + `terminationDrainDuration: 30s` を istio-proxy に注入（istio-proxy init container の実際の env に存在することを確認済み）— 常に 30 秒待機するのではなく、active connection がゼロになるとすぐ終了

| Mode | Rollout cycles | Code 200 | Code 503 | Code -1 | 使用した socket | 平均レイテンシー |
|---|---|---|---|---|---|---|
| sidecar（強化後） | 42 | 60,000（100%） | **0** | **0** | 16（完全な keepalive） | 2.630ms |
| ambient-L4（強化後） | 38 | 60,000（100%） | **0** | **0** | 395 | 1.189ms |
| ambient-L7（強化後） | 45 | 59,352（98.9%） | 648（1.1%） | **0** | 678 | 3.843ms |

**ベースライン → 強化後の比較**

| Mode | ベースラインエラー率 | 強化後エラー率 | 変化 |
|---|---|---|---|
| sidecar | 0.5% 503 + 0% TCP | 0% 503 + 0% TCP | **503 を完全に排除** |
| ambient-L4 | 0% 503 + 0.3% TCP | 0% 503 + 0% TCP | **TCP エラーも完全に排除** |
| ambient-L7 | 2.6% 503 + 0.1% TCP | 1.1% 503 + 0% TCP | 503 率を半分以上削減 |

> ✅ **判定**: この計測は、これらの 503 が Pod の Endpoint removal が伝播する前に Pod が graceful shutdown されないことに起因するという仮説を確認します — `preStop sleep 10` だけで sidecar と ambient-L4 のエラーは完全に解消されました。Ambient-L7（waypoint）も大幅に改善しましたがゼロには至りませんでした。つまり、waypoint 自体の stale-connection-reuse の仕組み（上記の主な §4 の発見）は、Workload 側の graceful-shutdown tuning だけでは完全には解決されません。waypoint 経由でルーティングする場合は、この強化をベースラインとして適用し、それでも解消できない残存 503 リスクを見込んでください。

### 緩和策としてのリトライのリスク — テスト結果（T2）

**テスト設定**: `order`（6 replicas、non-idempotent `POST /order`。handler 内の 0.1s delay があり、request ID を `collector` に報告）、`collector`（重複しない request ID をカウントし、複数回確認された ID を検出）、`order-client`（request ごとに一意な UUID を付けて 20 req/s で連続 POST 負荷を発生）の harness。リトライ policy（`attempts: 3, perTryTimeout: 2s, retryOn: 503,reset,connect-failure`）を、同じ Istio VirtualService config により sidecar（istio-proxy）と ambient-L7（waypoint）の両方に適用しました。各 mode は `order` Deployment の `rollout restart` と並行して 300 秒間実行しました。

| Mode | Rollout cycles | 送信 Requests | Client から見える障害（3 回のリトライをすべて使い切ったもの） | 重複実行 |
|---|---|---|---|---|
| sidecar（VirtualService retry） | 11 | 9,135 | 15（0.16%） | **0** |
| ambient-L7（waypoint retry） | 12 | 7,229 | 21（0.29%） | **0** |

> ✅ **判定**: いずれの mode でも、non-idempotent な重複実行は観測されませんでした。低い client-visible failure rate は、リトライが実際に発火し、一時的な rollout-churn error の多くを隠していることを確認しています — しかし、成功したリトライのどれも、同じ論理リクエストが 2 回処理される結果にはなりませんでした。

> ⚠️ **これは race が不可能であることを意味しません。** これは、特定の条件（perTryTimeout=2s、20 req/s、6 replicas、デフォルトの graceful shutdown、`preStop` hook なし）では発現しなかったことを意味します。理論上の仕組み — 元の request がすでに app に到達したものの、その response が caller に返る前にリトライが再送される — では、app が処理を開始した *後* かつ response が返る *前* の狭い window で connection が切断される必要があります。300 秒間の連続 rollout churn ではいずれの mode でも例を捕捉できませんでしたが、本番の non-idempotent path は、server-side idempotency key がない限り、mesh-level retry をデフォルトで安全でないものとして扱うべきです。このテストは race が *頻繁* であるという確信を下げますが、*安全* であることを立証するものではありません。

### リトライによって隠される障害と生の障害を分離する

mTLS data-plane の選択と HTTP retry policy は独立した判断です。sidecar Envoy と waypoint Envoy は L7 で HTTP request をリトライできますが、ambient ztunnel は HTTP 503 を解釈したり HTTP request を再実行したりできない [L4 proxy](https://istio.io/latest/docs/ambient/architecture/data-plane/) です。したがって、最終的に client から見える 503 count だけを比較しても、sidecar/waypoint の生の障害数が少なかったのか、リトライで隠しただけなのかは分かりません。

公平な rollout 比較のため、POST/PATCH write route では `attempts: 0` に設定し、以下の指標を個別に記録してください。

- リトライ前の HTTP 503、TCP reset/EOF、connection-refused event
- Envoy `upstream_rq_retry` および `upstream_rq_retry_success` counter
- 元の request を含む、実際の upstream delivery count
- retry 処理後に client から見える最終的な success/failure
- server が同じ idempotency key または command ID を複数回処理したかどうか

| Data plane | mTLS/encryption の意味 | L7 retry の場所 | 推奨用途 |
|---|---|---|---|
| Istio sidecar | Workload SPIFFE-certificate mTLS | Pod ごとの Envoy | 重要な non-idempotent path の保守的なベースライン |
| Istio ambient L4 | ztunnel 間の HBONE workload mTLS | なし | Istio mTLS と L4 policy だけが必要な場合の最初の候補 |
| Istio ambient L7 | HBONE + waypoint Envoy | 共有 waypoint | HTTP routing または L7 policy が必要な Service にのみ追加 |
| Cilium | Identity mutual authentication と WireGuard/IPsec などの transport encryption は個別に選択 | L3/L4 encryption layer にはなし | identity policy と network encryption を必要とする既存 Cilium data plane |

> **運用ルール:** mTLS だけが要件である場合は、まず ambient L4 を検証し、L7 policy または east-west HTTP routing が必要な Service にのみ waypoint を追加してください。write retry を無効にして計測した ambient rollout error が Workload の error budget を超える場合、重要な non-idempotent path では sidecar をベースラインとして維持してください。

### テスト分離に関する注記

<details>
<summary>専用クラスターが必要だった理由と、依然として発生した問題（クリックして展開）</summary>

初回の同日 T1/T3 テストラウンドは、4 つの専用 Namespace にまたがる共有クラスター（`fsi-demo-cluster`）上で実行しました。このクラスターの `benchmark` Namespace では、100 を超える EC2 instance type を対象にした大規模な Kafka benchmark job sweep が同時に実行されていました。ambient-L7 T1 の load 完了直後、このラウンドで作成されたすべての resource（4 つすべての Namespace、`istio-system`、およびすべての Istio/Gateway API CRD）が、原因未確認のまま同時に消失しました（一致する ArgoCD Application、Kyverno/Gatekeeper policy は見つかりませんでした）。そのため T2、T4、T5 は未実行のままとなり、その resource contention 下で収集した T1 の数値の妥当性にも疑念が生じました。

今回のラウンドでは、この種の干渉を排除するために、まったく新しいシングルテナントクラスター（`mesh-isolated-test`、専用 VPC、他の Workload なし）を使用し、resource anomaly なしに T1–T5 を end to end で完了しました。代わりに *別の* 分離の欠落が判明しました。新クラスターでの最初の T1 試行の途中、ローカル workstation の共有 `~/.kube/config` の current-context が、`mesh-isolated-test` から無関係なクラスターへと黙って切り替わりました。このため、その試行は無効になりました（context が切り替わると rollout-restart loop が `namespace not found` で失敗し始めましたが、すでに確立されていた進行中の fortio load connection は影響を受けませんでした）。`mesh-isolated-test` の Namespace と resource が完全に無傷であることは、明示的な kubeconfig check により全期間を通して確認しました。これは cluster 側の deletion ではなく、workstation level の context 混同です。修正として、`mesh-isolated-test` のみにスコープを絞った kubeconfig file を作成し、すべての test script から明示的に参照させ、context が再びずれた場合は abort する guard を追加しました。本書の最終数値はすべて、修正済みで context を lock した再実行から得ています。

</details>

## 5. 推奨事項: 階層化アプローチ

二者択一の「sidecar か ambient か」という選択ではなく、**Workload tier ごとに異なる mesh mode を適用すること**を推奨します。これは [Ambient Mode](../advanced/01-ambient-mode.md#use-cases) のユースケースガイドと一致しており、今回のテストラウンドはその根拠を示しています。

| Tier | 例 | 推奨事項 | 根拠 |
|---|---|---|---|
| Core（注文作成/マッチング/決済、non-idempotent） | Trading API | **Ambient L4 のみ（waypoint なし）または sidecar を維持** | §4: waypoint 経由でルーティングすると 503 率は sidecar の約 5 倍。L4 のみでは 503 はゼロでした。L7 feature が真に必要であれば、sidecar の方がより成熟した選択肢です。T2 では、いずれの mode の retry でも duplicate-execution instance は見つかりませんでしたが、安全性を確立するものではありません — mesh mode にかかわらず、この tier ではデフォルトで retry を無効にしてください。 |
| Semi-core（idempotent な read API） | Price/balance query | Ambient（L4、必要に応じて L7） | Idempotent request は retry しても安全なため、waypoint のリスクは小さい |
| Periphery（query、notification、batch） | Dashboard、alerting | ambient を積極的に採用 | resource/operational benefit を最大化。mTLS と rollout behavior はテストで安全性を検証済み |

**Namespace level の混在デプロイ**は、このテストラウンドで実際に検証しました — sidecar、ambient-L4、ambient-L7 の Namespace を同じクラスター上で同時に実行し、それぞれが独立して STRICT mTLS を強制しました。

### L4 のみの制限 — それでも canary deployment は可能か？

Ambient L4 のみには waypoint がないため、ztunnel は HTTP request の内部を確認しません。つまり、**HTTP header/path ベースの routing、retry、circuit breaking、traffic mirroring といった L7 feature は、L4 のみの Service には適用できません。** これが実際に canary deployment を妨げるかは、トラフィックの入口によって異なります。

> ✅ **Ingress canary は影響を受けません。** Istio Ingress Gateway または Gateway API `Gateway` は、backend Workload が ambient または sidecar mode のどちらで実行されているかに関係なく、常に独立した完全な Envoy proxy（独自の Deployment）です。`VirtualService`/`HTTPRoute` による v1/v2 subset 間の weighted split は完全に gateway で決定されます。ztunnel（L4）は、その後にすでに選択された宛先 Pod への connection をトンネルするだけです。外部公開 API の canary deployment は L4 のみの backend でも問題なく機能します。

> ⚠️ **Mesh 内（east-west）の canary には、その特定の Service で L7 が必要です。** Service A が mesh 内で Service B を呼び出し、B-v1 と B-v2 の間でトラフィックを割合により分割したい場合、何らかのコンポーネントが L7 で routing decision を行う必要があります — ztunnel にはできません。その canary を機能させるには、**B の前に waypoint をデプロイする（B を ambient-L7 に切り替える）か、B を sidecar で実行する**必要があります。

**結論**: 外部公開 API の canary deployment は L4 のみで問題なく機能します。mesh 内 canary を必要とする特定の Service に対してのみ waypoint または sidecar を使用してください — これこそが、上記の階層化した推奨事項を実務で適用する意図です。

**採用前のチェックリスト**

- [ ] 注文/マッチング/決済経路は本当に L7 feature（HTTP routing、retry、traffic split）を必要としますか？必要なければ、ambient L4 のみが第一候補です
- [ ] NetworkPolicy は HBONE ポート（15008）を許可するよう更新されていますか？（§2、検証済み — さらに、稼働中クラスターで `enableNetworkPolicy` を初めて有効化する場合、enforcement は遡及しないため既存 Pod を再作成してください）
- [ ] retry policy は non-idempotent API path に適用されていますか？（§4 — T2 ではテスト時に重複実行は見つかりませんでしたが、server-side idempotency key がない non-idempotent path ではデフォルトで retry を無効にしてください）
- [ ] 自身の Workload でレイテンシーを再計測しましたか？（§3、このクラスターの Graviton node で検証済み — instance type または Workload profile が大きく異なる場合は再計測してください）

## 付録: これらのテストを再現する

以下は、本書のすべての数値を生成した実際の config file と手順です。自身のクラスターで結果を再現するには直接コピーしてください。

### A. クラスターのプロビジョニング（eksctl）

専用シングルテナントクラスターは eksctl で作成しました。NAT gateway を持たない完全な public subnet を使用しています（新しい Elastic IP を必要としないテスト専用のショートカットです。本番クラスターでは NAT を有効にしてください）。

<details>
<summary>eksctl-cluster.yaml</summary>

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: mesh-isolated-test
  region: ap-northeast-2
  version: "1.36"
  tags:
    purpose: istio-sidecar-vs-ambient-retest
    ephemeral: "true"

availabilityZones:
  - ap-northeast-2a
  - ap-northeast-2c

vpc:
  nat:
    gateway: Disable

managedNodeGroups:
  - name: mesh-test-ng-arm64
    instanceType: m7g.xlarge
    amiFamily: AmazonLinux2023
    desiredCapacity: 3
    minSize: 3
    maxSize: 3
    volumeSize: 40
    privateNetworking: false
    labels:
      role: istio-mesh-test
    tags:
      ephemeral: "true"

addons:
  - name: vpc-cni
  - name: coredns
  - name: kube-proxy
  - name: eks-pod-identity-agent
```

</details>

```bash
eksctl create cluster -f eksctl-cluster.yaml
```

### B. Istio のインストール（Gateway API CRD + ambient profile）

Ambient mode の waypoint は Gateway API の `Gateway` resource であるため、Istio をインストールする前に Gateway API CRD が存在する必要があります。

```bash
# 1) Gateway API CRDs (v1.1.0, compatible with Istio 1.30)
kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.1.0/standard-install.yaml

# 2) Istio 1.30.2 ambient profile (via istioctl, not Helm)
istioctl install -f ambient-overlay.yaml -y
```

<details>
<summary>ambient-overlay.yaml（CNI/ztunnel/istiod を arm64 node にスケジュール）</summary>

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  profile: ambient
  values:
    cni:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: kubernetes.io/arch
                operator: In
                values: ["arm64"]
    ztunnel:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: kubernetes.io/arch
                operator: In
                values: ["arm64"]
  components:
    pilot:
      k8s:
        affinity:
          nodeAffinity:
            requiredDuringSchedulingIgnoredDuringExecution:
              nodeSelectorTerms:
              - matchExpressions:
                - key: kubernetes.io/arch
                  operator: In
                  values: ["arm64"]
```

</details>

### C. Namespace および Workload manifest

4 つの Namespace — `mesh-test-base`（レイテンシーベースライン用の mesh 未参加）、`mesh-test-sidecar`、`mesh-test-ambient-l4`、`mesh-test-ambient-l7`。異なるのは label のみで、ほかはすべてバイト単位で同一です。

<details>
<summary>namespaces.yaml</summary>

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: mesh-test-base
---
apiVersion: v1
kind: Namespace
metadata:
  name: mesh-test-sidecar
  labels:
    istio-injection: enabled
---
apiVersion: v1
kind: Namespace
metadata:
  name: mesh-test-ambient-l4
  labels:
    istio.io/dataplane-mode: ambient
---
apiVersion: v1
kind: Namespace
metadata:
  name: mesh-test-ambient-l7
  labels:
    istio.io/dataplane-mode: ambient
```

</details>

<details>
<summary>Workload manifest（echo server、6 replicas + fortio client）— 4 つすべての Namespace で同一、変更するのは namespace field のみ</summary>

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: echo
  namespace: mesh-test-sidecar   # swap for base / ambient-l4 / ambient-l7
  labels:
    app: echo
spec:
  replicas: 6
  selector:
    matchLabels:
      app: echo
  template:
    metadata:
      labels:
        app: echo
    spec:
      nodeSelector:
        kubernetes.io/arch: arm64
      containers:
      - name: echo
        image: fortio/fortio:1.69.4
        args: ["server", "-http-port", "8080"]
        ports:
        - containerPort: 8080
        readinessProbe:
          httpGet:
            path: /fortio/
            port: 8080
          initialDelaySeconds: 2
          periodSeconds: 3
        resources:
          requests:
            cpu: 50m
            memory: 32Mi
          limits:
            cpu: 300m
            memory: 128Mi
---
apiVersion: v1
kind: Service
metadata:
  name: echo
  namespace: mesh-test-sidecar
spec:
  selector:
    app: echo
  ports:
  - port: 8080
    targetPort: 8080
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fortio-client
  namespace: mesh-test-sidecar
  labels:
    app: fortio-client
spec:
  replicas: 1
  selector:
    matchLabels:
      app: fortio-client
  template:
    metadata:
      labels:
        app: fortio-client
    spec:
      nodeSelector:
        kubernetes.io/arch: arm64
      containers:
      - name: fortio-client
        image: fortio/fortio:1.69.4
        command: ["/usr/bin/fortio"]
        args: ["server", "-http-port", "8081", "-redirect-port", "disabled"]
        resources:
          requests:
            cpu: 50m
            memory: 32Mi
          limits:
            cpu: 300m
            memory: 128Mi
```

</details>

### D. mTLS — PeerAuthentication（§1）

<details>
<summary>peerauth-strict.yaml</summary>

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: strict
  namespace: mesh-test-sidecar
spec:
  mtls:
    mode: STRICT
---
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: strict
  namespace: mesh-test-ambient-l4
spec:
  mtls:
    mode: STRICT
---
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: strict
  namespace: mesh-test-ambient-l7
spec:
  mtls:
    mode: STRICT
```

</details>

ambient-L7 Namespace には、追加で waypoint をデプロイする必要があります:

```bash
istioctl waypoint apply -n mesh-test-ambient-l7 --enroll-namespace --wait
```

### E. NetworkPolicy（§2）

addon config を通じて、VPC CNI の eBPF ベースの NetworkPolicy enforcement を有効にします。§2 で扱ったとおり、これは **この時点以降に作成または再作成された Pod にのみ適用されます**。

```bash
aws eks update-addon --cluster-name mesh-isolated-test --addon-name vpc-cni --region ap-northeast-2 \
  --configuration-values '{"enableNetworkPolicy":"true"}' --resolve-conflicts OVERWRITE

# recreate existing pods so the eBPF hooks attach
kubectl rollout restart deployment/echo deployment/fortio-client -n mesh-test-sidecar
kubectl rollout restart deployment/echo deployment/fortio-client -n mesh-test-ambient-l4
kubectl rollout restart deployment/echo deployment/fortio-client -n mesh-test-ambient-l7
```

<details>
<summary>NetworkPolicy manifest（テスト 1: 8080 のみ → テスト 2: 8080 + 15008）</summary>

```yaml
# Test 1 — this blocks ambient
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-8080-only
  namespace: mesh-test-ambient-l4   # apply the same to ambient-l7 and sidecar
spec:
  podSelector:
    matchLabels:
      app: echo
  policyTypes:
  - Ingress
  ingress:
  - ports:
    - protocol: TCP
      port: 8080
```

```yaml
# Test 2 — adding the HBONE port restores ambient
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-8080-only
  namespace: mesh-test-ambient-l4
spec:
  podSelector:
    matchLabels:
      app: echo
  policyTypes:
  - Ingress
  ingress:
  - ports:
    - protocol: TCP
      port: 8080
    - protocol: TCP
      port: 15008
```

</details>

### F. ダウンタイムゼロ rollout test の実行（T1、§4）

fortio load generator（foreground、テスト期間中ブロック）と `rollout restart` loop（background）を並行して実行し、load 完了後に loop を停止します。

```bash
NS=mesh-test-sidecar   # repeat for ambient-l4, ambient-l7
DUR=600
CLIENT=$(kubectl get pods -n "$NS" -l app=fortio-client -o jsonpath='{.items[0].metadata.name}')

# ① rollout-restart loop (background) for DUR seconds
(
  START=$(date +%s)
  while [ $(( $(date +%s) - START )) -lt "$DUR" ]; do
    kubectl rollout restart deployment/echo -n "$NS"
    kubectl rollout status deployment/echo -n "$NS" --timeout=60s
  done
) &
ROLLOUT_PID=$!

# ② fortio load generator (foreground, 100qps x 600s = 60,000 requests)
kubectl exec -n "$NS" "$CLIENT" -c fortio-client -- \
  fortio load -qps 100 -t "${DUR}s" -c 16 -allow-initial-errors http://echo:8080/

kill "$ROLLOUT_PID" 2>/dev/null
```

> 💡 `-allow-initial-errors` がない場合、fortio の warmup request が rollout 中に到達して 503 を受け取ると、fortio は実行全体を abort します。この flag は rollout churn と重なる load test では必須です。

**Graceful-shutdown 強化 patch**（§4 の「強化後」再実行に使用。既存の Deployment に対して `kubectl patch --type strategic` で適用）:

```yaml
# common to all 3 modes — ambient-l4/l7 get only this patch
apiVersion: apps/v1
kind: Deployment
metadata:
  name: echo
spec:
  template:
    spec:
      terminationGracePeriodSeconds: 40
      containers:
      - name: echo
        lifecycle:
          preStop:
            sleep:
              seconds: 10
```

```yaml
# sidecar namespace only, additionally (EXIT_ON_ZERO_ACTIVE_CONNECTIONS)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: echo
  namespace: mesh-test-sidecar
spec:
  template:
    metadata:
      annotations:
        proxy.istio.io/config: |
          terminationDrainDuration: 30s
          proxyMetadata:
            EXIT_ON_ZERO_ACTIVE_CONNECTIONS: "true"
    spec:
      terminationGracePeriodSeconds: 40
      containers:
      - name: echo
        lifecycle:
          preStop:
            sleep:
              seconds: 10
```

```bash
kubectl patch deployment/echo -n mesh-test-sidecar --type strategic --patch-file patch-prestop-sidecar.yaml
kubectl patch deployment/echo -n mesh-test-ambient-l4 --type strategic --patch-file patch-prestop-ambient.yaml
kubectl patch deployment/echo -n mesh-test-ambient-l7 --type strategic --patch-file patch-prestop-ambient.yaml
```

### G. レイテンシー test の実行（T5、§3）

同じ fortio command を使用し、rollout loop のない steady state で実行します。

```bash
kubectl exec -n "$NS" "$CLIENT" -c fortio-client -- \
  fortio load -qps 200 -t 60s -c 16 -allow-initial-errors http://echo:8080/
```

### H. Retry / duplicate-execution test harness（T2、§4）

3-Pod harness — `order`（non-idempotent POST を処理）、`collector`（重複 request ID を検出）、`order-client`（連続負荷）— を sidecar と ambient-L7 Namespace に同一にデプロイします。

<details>
<summary>ConfigMap — order_server.py / collector.py / client.py</summary>

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: t2-scripts
  namespace: mesh-test-sidecar   # deploy the same into ambient-l7
data:
  order_server.py: |
    import http.server, urllib.request, time, os

    COLLECTOR_URL = os.environ.get("COLLECTOR_URL", "http://collector.mesh-test-sidecar.svc.cluster.local:9090/record")

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            if self.path != "/order":
                self.send_response(404); self.end_headers(); return
            rid = self.headers.get("X-Request-Id", "unknown")
            time.sleep(0.1)  # widen the SIGTERM-mid-request race window
            try:
                req = urllib.request.Request(COLLECTOR_URL, data=rid.encode(), method="POST")
                urllib.request.urlopen(req, timeout=2)
            except Exception as e:
                print(f"collector report failed for {rid}: {e}", flush=True)
            self.send_response(201)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def log_message(self, fmt, *args):
            pass

    if __name__ == "__main__":
        http.server.ThreadingHTTPServer(("", 8080), Handler).serve_forever()
  collector.py: |
    import http.server, json, threading

    lock = threading.Lock()
    counts = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            rid = self.rfile.read(length).decode().strip()
            with lock:
                counts[rid] = counts.get(rid, 0) + 1
            self.send_response(200); self.send_header("Content-Length","0"); self.end_headers()

        def do_GET(self):
            with lock:
                total = len(counts)
                dupes = {k: v for k, v in counts.items() if v > 1}
            if self.path == "/dupes":
                body = json.dumps({"total_ids": total, "dupe_count": len(dupes), "dupes": dupes}).encode()
            elif self.path == "/stats":
                body = json.dumps({"total_ids": total, "dupe_count": len(dupes)}).encode()
            else:
                self.send_response(404); self.end_headers(); return
            self.send_response(200)
            self.send_header("Content-Type","application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt, *args):
            pass

    if __name__ == "__main__":
        http.server.ThreadingHTTPServer(("", 9090), Handler).serve_forever()
  client.py: |
    import urllib.request, uuid, time, os

    TARGET = os.environ.get("TARGET_URL", "http://order.mesh-test-sidecar.svc.cluster.local:8080/order")
    RPS = float(os.environ.get("RPS", "20"))
    interval = 1.0 / RPS
    sent = 0
    failed = 0
    while True:
        rid = str(uuid.uuid4())
        t0 = time.time()
        try:
            req = urllib.request.Request(TARGET, data=b"{}", method="POST", headers={"X-Request-Id": rid})
            urllib.request.urlopen(req, timeout=3)
            sent += 1
        except Exception:
            failed += 1
        dt = time.time() - t0
        if dt < interval:
            time.sleep(interval - dt)
```

</details>

<details>
<summary>order / collector / order-client Deployment + Service</summary>

```yaml
apiVersion: v1
kind: Service
metadata:
  name: collector
  namespace: mesh-test-sidecar
spec:
  selector:
    app: collector
  ports:
  - port: 9090
    targetPort: 9090
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: collector
  namespace: mesh-test-sidecar
spec:
  replicas: 1
  selector:
    matchLabels:
      app: collector
  template:
    metadata:
      labels:
        app: collector
    spec:
      nodeSelector:
        kubernetes.io/arch: arm64
      containers:
      - name: collector
        image: python:3.12-alpine
        command: ["python3", "/scripts/collector.py"]
        ports:
        - containerPort: 9090
        volumeMounts:
        - name: scripts
          mountPath: /scripts
      volumes:
      - name: scripts
        configMap:
          name: t2-scripts
---
apiVersion: v1
kind: Service
metadata:
  name: order
  namespace: mesh-test-sidecar
spec:
  selector:
    app: order
  ports:
  - port: 8080
    targetPort: 8080
    name: http
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: order
  namespace: mesh-test-sidecar
spec:
  replicas: 6
  selector:
    matchLabels:
      app: order
  template:
    metadata:
      labels:
        app: order
    spec:
      nodeSelector:
        kubernetes.io/arch: arm64
      containers:
      - name: order
        image: python:3.12-alpine
        command: ["python3", "/scripts/order_server.py"]
        env:
        - name: COLLECTOR_URL
          value: "http://collector.mesh-test-sidecar.svc.cluster.local:9090/record"
        ports:
        - containerPort: 8080
        volumeMounts:
        - name: scripts
          mountPath: /scripts
      volumes:
      - name: scripts
        configMap:
          name: t2-scripts
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: order-client
  namespace: mesh-test-sidecar
spec:
  replicas: 1
  selector:
    matchLabels:
      app: order-client
  template:
    metadata:
      labels:
        app: order-client
    spec:
      nodeSelector:
        kubernetes.io/arch: arm64
      containers:
      - name: order-client
        image: python:3.12-alpine
        command: ["python3", "/scripts/client.py"]
        env:
        - name: TARGET_URL
          value: "http://order.mesh-test-sidecar.svc.cluster.local:8080/order"
        - name: RPS
          value: "20"
        volumeMounts:
        - name: scripts
          mountPath: /scripts
      volumes:
      - name: scripts
        configMap:
          name: t2-scripts
```

</details>

Retry policy を `order` Service に適用します（sidecar の istio-proxy と ambient-L7 で既にデプロイされた waypoint は、どちらもこの VirtualService を取得します）。

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: order-retry
  namespace: mesh-test-sidecar   # deploy the same into ambient-l7
spec:
  hosts:
  - order
  http:
  - route:
    - destination:
        host: order
        port:
          number: 8080
    retries:
      attempts: 3
      perTryTimeout: 2s
      retryOn: 503,reset,connect-failure
```

実行手順は（F）の rollout loop と同様ですが、対象を `order` Deployment にし、計測前に `collector` の counter をリセットして、後で duplicate count を問い合わせます。

```bash
kubectl rollout restart deployment/collector -n "$NS"   # reset the counter

# ... same rollout-loop pattern as §F, targeting `order`, for 300s ...

CLIENT=$(kubectl get pods -n "$NS" -l app=order-client -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n "$NS" "$CLIENT" -c order-client -- python3 -c \
  "import urllib.request; print(urllib.request.urlopen('http://collector.$NS.svc.cluster.local:9090/dupes', timeout=5).read().decode())"
```

## 参考資料

- [Ambient Mode](../advanced/01-ambient-mode.md) — ztunnel/waypoint アーキテクチャ、sidecar との resource 比較
- [mTLS](../security/01-mtls.md) — STRICT/PERMISSIVE mode、証明書管理、NetworkPolicy の競合
- [Istio VirtualService Retry](https://istio.io/latest/docs/reference/config/networking/virtual-service/#HTTPRetry) — `attempts: 0` と retry 条件
- [Envoy Retry Statistics](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/router_filter) — retry behavior と observability
- [Troubleshooting: Connection Errors During Pod Termination](../troubleshooting/common-errors.md#connection-errors-during-pod-termination)
- [Sidecar Injection](../advanced/07-sidecar-injection.md)
- [Service Mesh Solution Comparison](01-service-mesh-comparison.md)
