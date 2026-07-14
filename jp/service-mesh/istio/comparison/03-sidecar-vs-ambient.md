# Sidecar vs Ambient Mode 選択ガイド（EKS 1.36 テスト結果）

> **サポート対象バージョン**: Istio 1.30 / EKS 1.36
> **最終更新**: July 7, 2026

本ドキュメントは、EKS 上のミッションクリティカルなワークロード（例: 暗号資産取引所の注文・マッチング経路）で、Istio を **sidecar mode と ambient mode のどちらで採用するか**を判断するための、テスト結果に基づくガイドです。アーキテクチャ自体はすでに [Ambient Mode](../advanced/01-ambient-mode.md) で扱っているため、ここでは繰り返しません。代わりに、4 つの具体的な要件に対するテスト結果と推奨事項を示します。

1. mTLS が必要（クラスタ内部の pod-to-pod 通信）
2. NetworkPolicy が必要
3. レイテンシーに敏感なワークロード
4. 無停止 rollout — ambient waypoint の 503 に関する懸念の検証

> 💡 本ドキュメント内の数値はすべて、このテストサイクル専用に構築され、その後削除された **専用シングルテナント EKS cluster**（`mesh-isolated-test`）から得たものです。専用 cluster が必要だった理由は、§4 の末尾にある[テスト分離に関する注記](#a-note-on-test-isolation)を参照してください。

## 判断の要約

| 要件 | Sidecar | Ambient（L4、waypoint なし） | Ambient（L7、waypoint あり） |
|---|---|---|---|
| mTLS | ✅ STRICT をサポート、検証済み | ✅ STRICT をサポート、検証済み | ✅ STRICT をサポート、検証済み |
| NetworkPolicy | ✅ 既存ルールがそのまま機能、検証済み | ⚠️ HBONE port（15008）の許可が必要、検証済み | ⚠️ HBONE port（15008）の許可が必要、検証済み |
| レイテンシー（mesh なしのベースラインに対する P50） | +1.29ms、計測値 | +0.04ms（無視できるレベル）、計測値 | +1.86ms、計測値 |
| 無停止 rollout | 503 が発生（0.5%、計測値） | **実際の 503 はゼロ**、0.3% の TCP reset に置き換わる | 503 が発生、**2.6%、sidecar の約 5 倍**（計測値） |

> ✅ **結論の一言**: waypoint なし（L4-only）の ambient は、rollout の変動下で最も安定しており、レイテンシーのオーバーヘッドも無視できるレベルでした。waypoint（L7）をアタッチすると、503 率は sidecar を上回り、レイテンシーもおおむね sidecar と同程度になります。根拠は以下の §3–§4 にあります。

## 1. mTLS — テスト結果（EKS 1.36.2、Istio 1.30.2）

**テスト環境**
- 専用シングルテナント cluster `mesh-isolated-test`（専用 VPC、他ワークロードなし）。EKS control plane と worker node はともに v1.36.2、Amazon Linux 2023（arm64、m7g.xlarge）
- 3 つのテスト namespace（sidecar / ambient-L4 / ambient-L7）に namespace-scoped `PeerAuthentication` STRICT を適用 — mesh 全体には未適用

### チェック 1 — plaintext による pod-IP への直接アクセス（ブロックされる必要あり）

```
plaintext-client -> sidecar echo pod:8080
  [E] Read error, err="read tcp ...: read: connection reset by peer"
plaintext-client -> ambient-L4 echo pod:8080
  [E] Read error, err="EOF"
plaintext-client -> ambient-L7 echo pod:8080
  [E] Read error, err="EOF"
```

### チェック 2 — Service 経由の mesh 内アクセス（成功する必要あり）

```
sidecar client -> http://echo:8080/     => HTTP/1.1 200 OK (server: envoy)
ambient-L4 client -> http://echo:8080/  => HTTP/1.1 200 OK (no envoy headers, pure L4 passthrough)
ambient-L7 client -> http://echo:8080/  => HTTP/1.1 200 OK (server: istio-envoy, x-envoy-decorator-operation)
```

### チェック 3 — SPIFFE 証明書

`istioctl ztunnel-config certificates` / `istioctl proxy-config secret` で検証:

| Workload | 証明書発行元 | SPIFFE ID | Root CA |
|---|---|---|---|
| ambient-L4 echo | ztunnel | `spiffe://cluster.local/ns/mesh-test-ambient-l4/sa/default` | 共有 |
| ambient-L7 echo | ztunnel | `spiffe://cluster.local/ns/mesh-test-ambient-l7/sa/default` | 共有 |
| sidecar echo | istio-proxy | `spiffe://cluster.local/ns/mesh-test-sidecar/sa/default` | 共有 |

> ✅ **判定**: 3 つの mode はすべて plaintext アクセスを即座にブロックし、mesh 内トラフィックのみが 200 を返し、各 workload は同じ root CA から発行された固有の SPIFFE ID を保持します。sidecar と ambient のどちらも、「クラスタ内部の pod-to-pod トラフィックは mTLS でなければならない」という要件を満たします。

**相違点**: ambient は mTLS を透過的に適用します。`istio-cni` が pod の network namespace 内で traffic redirection を設定し、ztunnel が port 15008 の HBONE（mTLS）tunnel を介して転送するため、アプリケーションコードも sidecar injection も不要です。Sidecar は、アプリケーション pod 内の istio-proxy container を通じて同じことを実現します。両 mode の certificate rotation と migration strategy の詳細は [mTLS](../security/01-mtls.md) を参照してください。

## 2. NetworkPolicy — テスト結果

Ambient は pod の実際のトラフィックを HBONE tunnel（TCP 15008）経由で ztunnel に転送し、ztunnel がそれを復号して宛先に配信します。つまり、**アプリケーション port（例: 8080）のみを許可する NetworkPolicy は ambient に enrollment された pod への inbound traffic をブロックします**。これは、packet が実際には 15008 に到着するためです。ambient を NetworkPolicy と併用するには、対象 pod に対して **TCP 15008 の inbound allow rule を追加する必要があります**。

**テスト設定**: 専用 `mesh-isolated-test` cluster で VPC CNI NetworkPolicy enforcement（`enableNetworkPolicy=true`、`aws-network-policy-agent v1.3.5-eksbuild.3`、eBPF）を有効にしました。これは以前のラウンドで使った共有 cluster では安全に実施できませんでした。実施すると、他チームに属する既存の休眠状態の NetworkPolicy 13 件が同時に有効化されるためです。専用シングルテナント cluster によって、この blast radius の懸念は完全に取り除かれました。

> ⚠️ **テスト中に見つかった運用上の注意点**: `enableNetworkPolicy` を有効にする*前*に作成された pod には、遡って enforcement が適用されません。eBPF hook は pod-network-setup（CNI ADD）時にのみアタッチされます。sanity check でこれを直接確認しました。すでに実行中の pod に port 9999 *のみ*を許可する policy を適用しても、port 8080 のトラフィックはブロックされずに通過しました。NetworkPolicy が有効になる前に、addon を有効化した後で `kubectl rollout restart`（pod の再作成）が必要でした。これは、稼働中 cluster で NetworkPolicy を有効にする前に知っておくべき実際の注意点です。

**テスト 1 — ingress を TCP 8080 のみに制限**（新規 pod、enforcement が有効であることを確認済み）

| Mode | 結果 |
|---|---|
| sidecar | ✅ 200 OK — 影響なし |
| ambient-L4 | ❌ ブロック（`i/o timeout`） |
| ambient-L7 | ❌ ブロック（`i/o timeout`） |

**テスト 2 — ingress で TCP 8080 + TCP 15008（HBONE）を許可**

| Mode | 結果 |
|---|---|
| ambient-L4 | ✅ 200 OK — 復旧 |
| ambient-L7 | ✅ 200 OK — 復旧 |

> ✅ **判定**: 実トラフィックにより、上記の仮説を確認しました。Ambient の workload pod の network namespace への実際の inbound packet は、アプリケーションの port（8080）ではなく、ztunnel の HBONE port（15008）に到着します。そのため、app-port-only の NetworkPolicy は ambient に enrollment された pod を暗黙的に壊します。Sidecar は影響を受けません。sidecar の traffic capture は、packet がすでにアプリケーション port に到着した後、pod 自身の network namespace 内だけで行われるためです。

defense-in-depth を推奨します。network-level（NetworkPolicy）と identity-level（AuthorizationPolicy）の control を併用してください。sidecar mode における mTLS と NetworkPolicy の conflict は、[mTLS and NetworkPolicy Conflict](../security/01-mtls.md#7-mtls-and-networkpolicy-conflict) で扱っています。

## 3. レイテンシー — テスト結果（T5）

**テスト設定**: fortio load、200 qps、60s、16 connections、ケースごとに 12,000 requests、steady state（rollout restart は実行なし）。同じ `mesh-isolated-test` の Graviton（m7g.xlarge）node 上で、no-mesh baseline（unmeshed namespace）と sidecar、ambient-L4、ambient-L7 を比較しました。すべてのケースで Code 200 が 100% 返されました。

| ケース | P50 | P75 | P90 | P99 | P99.9 |
|---|---|---|---|---|---|
| no-mesh（ベースライン） | 0.82ms | 1.33ms | 1.73ms | 1.97ms | 2.00ms |
| sidecar | 2.11ms | 2.60ms | 2.89ms | 3.91ms | 8.00ms |
| ambient-L4（waypoint なし） | 0.86ms | 1.34ms | 1.74ms | 1.98ms | 2.93ms |
| ambient-L7（waypoint） | 2.68ms | 3.06ms | 3.63ms | 3.98ms | 7.67ms |

**no-mesh baseline に対する P50 オーバーヘッド**: sidecar +1.29ms · ambient-L4 +0.04ms（無視できるレベル） · ambient-L7 +1.86ms

> ✅ **判定**: 以前に引用した公開 ambient-mode benchmark（L4-only は sidecar より低く、waypoint は sidecar とほぼ同等かやや高い）と一致しています。これらは現在、引用ではなく first-party の計測値です。暗号資産取引の経路のようなレイテンシーに敏感な workload では、これは下記の §4 と整合します。**waypoint を回避することは、レイテンシーと rollout 安定性の両方に役立ちます**。

## 4. 無停止 Rollout — 503 テスト結果（主要な発見）

### 背景

ambient に関する懸念は、**L7 waypoint（Envoy）が destination IP:Port を key とした pool から connection を再利用する**一方で、**pod が terminate したときに ztunnel が waypoint へ通知しない**ことです。terminate された pod の IP が新しい pod に再割り当てされると、waypoint は無効になった connection を再利用し、503 を返す可能性があります。Sidecar でも同様の pod-termination race が発生することがあります（その仕組みは [Connection Errors During Pod Termination](../troubleshooting/common-errors.md#connection-errors-during-pod-termination) を参照）。EKS 1.36 で、両方の failure mode を直接比較して計測しました。

**テスト環境**
- 専用シングルテナント cluster `mesh-isolated-test`。EKS control plane と worker node はともに v1.36.2、arm64（Graviton m7g.xlarge）、Istio 1.30.2
- **byte-identical な workload**（6 replicas の echo server Deployment + fortio client）を実行する 3 つの namespace（sidecar / ambient-L4 / ambient-L7）。異なるのは namespace label のみ
- fortio client は 100 req/s で keepalive connection を維持し、その間に対象 namespace の `echo` Deployment を繰り返し `rollout restart` した
- mode ごとに 60,000 requests を収集（= 100 qps × 600s）

### 結果

| Mode | Rollout cycles | Requests | 503 count | 503 rate | その他のエラー（-1、TCP reset/EOF） | 使用 socket 数 |
|---|---|---|---|---|---|---|
| sidecar | 42 | 60,000 | 324 | **0.5%** | 2 (0.0%) | 350 |
| ambient-L4（waypoint なし） | 64 | 60,000 | **0** | **0%** | 195 (0.3%) | 1,652 |
| ambient-L7（waypoint） | 65 | 59,913 | 1,528 | **2.6%** | 84 (0.1%) | 2,486 |

> 完全な keepalive であれば、使用 socket 数は 16 になります。Ambient-L7 では、実行終了時に 60,000 calls 中 87 件が未完了のままであり、平均レイテンシー（50.4ms）も他の 2 mode（約 2～3ms）を大きく上回りました。

<details>
<summary>fortio 実行の生出力</summary>

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

1. **Ambient-L7（waypoint）の 503 rate（2.6%）は、この専用 cluster では sidecar（0.5%）の約 5 倍です**。これは、共有かつ競合した cluster での同日早期計測が示唆した差よりもさらに大きいものでした（下記の分離に関する注記を参照）。このことは、rollout の変動下で「waypoint の connection pool が stale connection を再利用して 503 を発生させる」という当初の懸念を弱めるのではなく、むしろ補強しています。
2. **Ambient-L4（waypoint なし）は、再び実際の HTTP 503 をゼロにしました。**その代わりに、0.3% の connection-level TCP error（応答なしの「-1」）が見られました。L4 では failure は *503 response* ではなく *dropped connection* として表面化します。したがって、error response を生成する proxy ではなく、client/application が reconnection handling を担うことになります。
3. Ambient-L7 では大きな平均レイテンシーの spike と、実行中に完了しなかった 87 requests も見られました。これは、他の 2 mode とは異なり、waypoint が rollout の変動と継続負荷の組み合わせに苦戦していることと一致します。
4. 同じ 600 秒の window 内で完了した rollout cycles（sidecar / ambient-L4 / ambient-L7 で 42 / 64 / 65）は、busy な共有 cluster での以前の計測よりはるかに多くなりました。これは、この専用 cluster では他の tenant が CPU/network を競合しなかったためです。*相対的な*順序（sidecar が最も遅く、ambient-L4 が最も速い）は維持されましたが、絶対的な rollout speed は cluster の競合に大きく依存するため、どの mode にも固有の特性として過度に解釈すべきではありません。

### フォローアップ: graceful shutdown の強化後

上記の baseline の数値は、**shutdown tuning を一切行わない**状態を反映しています。次の 2 つの変更を加えた後、同じ T1 test（100 qps × 600s、60,000 requests/mode）を再実行しました。

- **3 つの mode すべて**: `echo` container に `lifecycle.preStop.sleep.seconds: 10`（K8s 1.29+ の native sleep action。exec/shell は不要）と `terminationGracePeriodSeconds: 40` を設定。pod が実際に connection の受け付けを停止する前に、Endpoint removal が cluster 全体に伝播する時間を確保
- **Sidecar のみ**: `proxy.istio.io/config` pod annotation を介して、`EXIT_ON_ZERO_ACTIVE_CONNECTIONS=true` + `terminationDrainDuration: 30s` を istio-proxy に injection（istio-proxy init container の実際の env に存在することを確認済み）。常に完全な 30s を待つ代わりに、active connection がゼロになるとすぐ終了

| Mode | Rollout cycles | Code 200 | Code 503 | Code -1 | 使用 socket 数 | 平均レイテンシー |
|---|---|---|---|---|---|---|
| sidecar（強化済み） | 42 | 60,000 (100%) | **0** | **0** | 16（完全な keepalive） | 2.630ms |
| ambient-L4（強化済み） | 38 | 60,000 (100%) | **0** | **0** | 395 | 1.189ms |
| ambient-L7（強化済み） | 45 | 59,352 (98.9%) | 648 (1.1%) | **0** | 678 | 3.843ms |

**Baseline → 強化済みの比較**

| Mode | Baseline error rate | 強化済み error rate | 変化 |
|---|---|---|---|
| sidecar | 0.5% 503 + 0% TCP | 0% 503 + 0% TCP | **503 を完全に排除** |
| ambient-L4 | 0% 503 + 0.3% TCP | 0% 503 + 0% TCP | **TCP error も完全に排除** |
| ambient-L7 | 2.6% 503 + 0.1% TCP | 1.1% 503 + 0% TCP | 503 rate を半分以上削減 |

> ✅ **判定**: これにより、これらの 503 は、pod の Endpoint removal が伝播する前に pod が graceful shutdown していないことに起因するという仮説が計測により確認されました。`preStop sleep 10` だけで sidecar と ambient-L4 の error は完全になくなりました。Ambient-L7（waypoint）も大幅に改善しましたが、ゼロにはなりませんでした。これは、waypoint 自身の stale-connection-reuse mechanism（上記の主要な §4 の発見）が、workload 側の graceful-shutdown tuning だけでは完全に解決しないことを意味します。waypoint を経由して routing する場合は、この強化を baseline として適用し、それでも排除できない残存 503 risk を見込んでください。

### 緩和策としての retry のリスク — テスト結果（T2）

**テスト設定**: `order`（6 replicas、非 idempotent な `POST /order`。handler 内で 0.1s delay を設け、request ID を `collector` に報告）、`collector`（異なる request ID をカウントし、同じ ID を複数回確認すると flag を立てる）、`order-client`（request ごとに一意な UUID を使い、20 req/s で連続 POST load）から成る harness を使用しました。retry policy（`attempts: 3, perTryTimeout: 2s, retryOn: 503,reset,connect-failure`）は、sidecar（istio-proxy）と ambient-L7（waypoint）の両方に、同一の Istio VirtualService config を介して適用しました。各 mode は、`order` Deployment の同時 `rollout restart` とともに 300s 実行しました。

| Mode | Rollout cycles | 送信 requests | Client から見える failures（3 retries すべてを使い切る） | 重複実行 |
|---|---|---|---|---|
| sidecar（VirtualService retry） | 11 | 9,135 | 15 (0.16%) | **0** |
| ambient-L7（waypoint retry） | 12 | 7,229 | 21 (0.29%) | **0** |

> ✅ **判定**: どちらの mode でも、非 idempotent な実行の重複は観測されませんでした。低い client-visible failure rate は、retry が実際に発火し、一時的な rollout-churn error の大部分を隠していたことを確認しています。しかし、成功した retry によって同じ logical request が 2 度処理されることはありませんでした。

> ⚠️ **これは race が不可能であることを意味しません。**これは、特定の条件（perTryTimeout=2s、20 req/s、6 replicas、default graceful shutdown、`preStop` hook なし）では現れなかったことを意味します。理論的な mechanism、すなわち元の request がすでに app に到達しているものの response が caller に戻る前に retry が再送される状況は、app が処理を開始した*後*かつ response が返る*前*という狭い window で connection が drop する必要があります。300s の連続 rollout churn では、どちらの mode でもその例を捕捉できませんでした。ただし、production の非 idempotent な経路では、server-side idempotency key がない限り、mesh-level retry は default で unsafe と扱うべきです。この test は race が*一般的*であるという確信を下げますが、*安全*であることを立証するものではありません。

### テスト分離に関する注記

<details>
<summary>専用 cluster が必要だった理由と、それでも発生した問題（クリックして展開）</summary>

同日の早期に行った T1/T3 testing は、共有 cluster（`fsi-demo-cluster`）上の 4 つの専用 namespace で実施しました。その cluster の `benchmark` namespace では、100 種類以上の EC2 instance type にわたる大規模な Kafka benchmark job sweep が同時に実行されていました。ambient-L7 T1 load が完了した直後に、そのラウンドで作成されたすべての resource（4 つの namespace、`istio-system`、およびすべての Istio/Gateway API CRD）が、確認済みの root cause なしに同時に消失しました（一致する ArgoCD Application も Kyverno/Gatekeeper policy も見つかりませんでした）。その結果、T2、T4、T5 は未実施となり、その resource contention 下で収集した T1 の数値の妥当性にも疑問が生じました。

このラウンドでは、この種の干渉を排除するために、まったく新しいシングルテナント cluster（`mesh-isolated-test`、専用 VPC、他 workload なし）を使用し、resource anomaly なしに T1–T5 を end-to-end で完了しました。しかし別の分離の隙間が見つかりました。新しい cluster で最初の T1 を試行している途中で、ローカル workstation の共有 `~/.kube/config` の current-context が、`mesh-isolated-test` から無関係な cluster へ黙って切り替わりました。そのため、その試行は無効になりました（context が切り替わると rollout-restart loop は `namespace not found` で失敗し始めましたが、すでに確立していた in-flight の fortio load connection は影響を受けませんでした）。`mesh-isolated-test` の namespace と resource は、明示的な kubeconfig check によって全体を通じて完全に無傷であることを確認しました。これは cluster 側の deletion ではなく、workstation-level の context の取り違えでした。修正は、`mesh-isolated-test` のみに scope を絞った kubeconfig file を用意してすべての test script から明示的に参照し、context が再び drift した場合は abort する guard を追加することです。本ドキュメントの最終数値はすべて、修正後の context-locked rerun から得たものです。

</details>

## 5. 推奨事項: Tiered Approach

二者択一の「sidecar か ambient か」ではなく、**workload tier ごとに異なる mesh mode を適用すること**を推奨します。これは [Ambient Mode](../advanced/01-ambient-mode.md#use-cases) の use-case guidance に一致しており、今回の testing は証拠によってこれを裏付けています。

| Tier | 例 | 推奨事項 | 根拠 |
|---|---|---|---|
| Core（注文作成/マッチング/決済、非 idempotent） | Trading API | **Ambient L4-only（waypoint なし）または sidecar を維持** | §4: waypoint を経由すると 503 rate は sidecar の約 5 倍。L4-only の 503 はゼロ。L7 feature が本当に必要なら、より成熟した選択肢は sidecar。T2 ではどちらの mode でも retry による重複実行は見つからなかったが、安全性は立証されない。この tier では、mesh mode に関係なく default で retry をオフにする。 |
| Semi-core（idempotent な read API） | 価格/残高照会 | Ambient（L4、必要に応じて L7） | Idempotent request は安全に retry できるため、waypoint risk の重要度は低い |
| Periphery（query、notification、batch） | Dashboard、alerting | Ambient を積極的に採用 | resource/operational benefit を最大化。mTLS と rollout behavior はテストで安全性を検証済み |

**namespace-level の mixed deployment** は、今回の testing で実際に検証されました。sidecar、ambient-L4、ambient-L7 の namespace は同じ cluster 上で同時に実行され、それぞれが独立して STRICT mTLS を強制していました。

### L4-only の制限 — canary deployment は引き続き実施できるか？

Ambient L4-only には waypoint がないため、ztunnel は HTTP request の内部を確認しません。つまり、**HTTP header/path-based routing、retry、circuit breaking、traffic mirroring といった L7 feature は、L4-only Service には適用できません。**これが実際に canary deployment を妨げるかどうかは、traffic がどこから入るかによります。

> ✅ **Ingress canary は影響を受けません。**Istio Ingress Gateway または Gateway API `Gateway` は、backend workload が ambient と sidecar のどちらの mode で実行されるかにかかわらず、常に別個の完全な Envoy proxy（独自の Deployment）です。`VirtualService`/`HTTPRoute` による v1/v2 subset 間の weighted split は gateway で完全に決定され、その後 ztunnel（L4）はすでに選択済みの destination pod への connection を tunnel するだけです。外部公開 API の canary deployment は L4-only backend でも問題なく機能します。

> ⚠️ **mesh-internal（east-west）の canary には、その特定の Service で L7 が必要です。**Service A が mesh 内で Service B を呼び出し、B-v1 と B-v2 の間で percentage により traffic を split したい場合、L7 でその routing decision を行うものが必要です。ztunnel にはできません。この canary を機能させるには、**B の前に waypoint を deploy する（B を ambient-L7 に切り替える）か、B を sidecar で実行する**必要があります。

**要点**: 外部公開 API の canary deployment は L4-only で問題なく機能します。mesh-internal canary を必要とする特定の Service に対してのみ waypoint または sidecar を選択してください。これはまさに、上記の tiered recommendation を実際に適用する方法です。

**採用前のチェックリスト**

- [ ] 注文/マッチング/決済経路では、本当に L7 feature（HTTP routing、retry、traffic split）が必要か？必要でなければ、ambient L4-only が最有力候補
- [ ] NetworkPolicy は HBONE port（15008）を許可するように更新済みか？（§2、検証済み。稼働中 cluster で初めて `enableNetworkPolicy` を有効にする場合は、enforcement は遡及されないため、既存 pod を再作成すること）
- [ ] 非 idempotent な API path に retry policy を適用していないか？（§4 — T2 では testing 中に重複実行は見つからなかったが、server-side idempotency key がない非 idempotent path では default で retry を無効にすること）
- [ ] 自身の workload に対してレイテンシーを再計測したか？（§3、この cluster の Graviton node で検証済み。instance type または workload profile が大きく異なる場合は再計測すること）

## Appendix: これらのテストの再現

以下は、本ドキュメントのすべての数値を得た実際の config file と手順です。自身の cluster で結果を再現するには、そのまま copy してください。

### A. Cluster provisioning（eksctl）

専用シングルテナント cluster は eksctl で作成しました。NAT gateway なしの完全 public subnet を使用しています（新しい Elastic IP を必要としない、テスト専用の簡略化です。production cluster では NAT を有効にしてください）。

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

### B. Istio install（Gateway API CRD + ambient profile）

Ambient mode の waypoint は Gateway API `Gateway` resource であるため、Istio を install する前に Gateway API CRD が存在している必要があります。

```bash
# 1) Gateway API CRDs (v1.1.0, compatible with Istio 1.30)
kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.1.0/standard-install.yaml

# 2) Istio 1.30.2 ambient profile (via istioctl, not Helm)
istioctl install -f ambient-overlay.yaml -y
```

<details>
<summary>ambient-overlay.yaml（CNI/ztunnel/istiod を arm64 node に schedule）</summary>

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

### C. Namespace および workload manifest

4 つの namespace — レイテンシー baseline 用の `mesh-test-base`（unmeshed）、`mesh-test-sidecar`、`mesh-test-ambient-l4`、`mesh-test-ambient-l7`。異なるのは label のみで、それ以外は byte-identical です。

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
<summary>Workload manifest（echo server、6 replicas + fortio client） — 4 つの namespace すべてで同一、異なるのは namespace field のみ</summary>

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

ambient-L7 namespace には、追加で waypoint を deploy する必要があります。

```bash
istioctl waypoint apply -n mesh-test-ambient-l7 --enroll-namespace --wait
```

### E. NetworkPolicy（§2）

addon config を通じて、VPC CNI の eBPF-based NetworkPolicy enforcement を有効にします。§2 で述べたとおり、これは**この時点より後に作成または再作成された pod にのみ適用されます**。

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

### F. 無停止 rollout test の実行（T1、§4）

fortio load generator（foreground。test duration の間 block）と `rollout restart` loop（background）を同時に実行し、load の終了後に loop を停止します。

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

> 💡 `-allow-initial-errors` がない場合、fortio は warmup request が rollout 中に 503 を受け取ると実行全体を abort します。rollout churn と重なる load test では、この flag が必要です。

**Graceful-shutdown hardening patch**（§4 の「強化後」rerun で使用。既存 Deployment に対して `kubectl patch --type strategic` で適用）:

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

同じ fortio command を、rollout loop なしの steady state で実行します。

```bash
kubectl exec -n "$NS" "$CLIENT" -c fortio-client -- \
  fortio load -qps 200 -t 60s -c 16 -allow-initial-errors http://echo:8080/
```

### H. Retry / 重複実行 test harness（T2、§4）

3-pod harness — `order`（非 idempotent な POST を処理）、`collector`（重複 request ID を検出）、`order-client`（連続 load）— を sidecar と ambient-L7 の namespace に同一に deploy します。

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

retry policy を `order` Service に適用します（sidecar の istio-proxy と ambient-L7 のすでに deploy 済み waypoint は、どちらもこの VirtualService を取得します）。

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

実行手順は（F）の rollout loop と同様ですが、対象を `order` Deployment とし、計測前に `collector` の counter を reset し、終了後に duplicate count を query します。

```bash
kubectl rollout restart deployment/collector -n "$NS"   # reset the counter

# ... same rollout-loop pattern as §F, targeting `order`, for 300s ...

CLIENT=$(kubectl get pods -n "$NS" -l app=order-client -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n "$NS" "$CLIENT" -c order-client -- python3 -c \
  "import urllib.request; print(urllib.request.urlopen('http://collector.$NS.svc.cluster.local:9090/dupes', timeout=5).read().decode())"
```

## 参考資料

- [Ambient Mode](../advanced/01-ambient-mode.md) — ztunnel/waypoint architecture、sidecar との resource comparison
- [mTLS](../security/01-mtls.md) — STRICT/PERMISSIVE mode、certificate management、NetworkPolicy conflict
- [Troubleshooting: Connection Errors During Pod Termination](../troubleshooting/common-errors.md#connection-errors-during-pod-termination)
- [Sidecar Injection](../advanced/07-sidecar-injection.md)
- [Service Mesh Solution Comparison](01-service-mesh-comparison.md)
