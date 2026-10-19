# Sidecar と Ambient Mode の選択ガイド（EKS 1.36 のテスト結果）

> **報告されたテストバージョン**: Istio 1.30.2 / EKS 1.36.2 / Fortio 1.69.4
> **元レポートの日付**: 2026年8月21日 · **内容レビュー**: 2026年9月11日

この文書では、報告された mTLS、NetworkPolicy、レイテンシー、ローリング更新の測定値を記録しています。完全な生データ一式と正確な実行スクリプトは添付されておらず、このレビューで AWS クラスターを再作成してもいません。設定と計算を確認したことは、これらの結果を独立して再現したことを意味しません。

付録は、具体的なスクリプトや設定の欠陥を修正した**改訂版ラボ手順の例**です。過去の数値を得た正確な手順として説明しないでください。新たな測定では実際のソフトウェア、イメージのダイジェスト、ポリシー、成果物を記録してください。また、これらの結果を Istio 1.31 や別のバージョンの結果として表記しないでください。

## 判断の概要

| 要件 | Sidecar | Ambient（L4、waypoint なし） | Ambient（L7、waypoint あり） | Cilium |
|---|---|---|---|---|
| mTLS | STRICT の確認に成功したとの報告 | STRICT の確認に成功したとの報告 | STRICT の確認に成功したとの報告 | 未測定。ID の相互認証と個別に有効化する WireGuard/IPsec は、STRICT と同等の単一スイッチではない |
| NetworkPolicy | テストしたアプリケーションポートのルールは機能 | テストした通信経路では TCP 15008 も必要 | テストした通信経路では TCP 15008 も必要 | 未測定。Cilium は標準 Kubernetes NetworkPolicy と CiliumNetworkPolicy／クラスター全体に適用する拡張を実施 |
| 報告されたベースライン比 P50 | +1.29 ms | +0.04 ms | +1.86 ms | 未測定 |
| 調整前のローリング更新 | HTTP 503 が324件、HTTP以外のエラーが2件 / 60,000件 | HTTP 503 が0件、HTTP以外のエラーが195件 / 60,000件 | HTTP 503 が1,528件、HTTP以外のエラーが84件 / 59,913件 | 未測定 |
| 強化後のローリング更新 | 観測エラー0件 / 60,000件 | 観測エラー0件 / 60,000件 | HTTP 503 が648件 / 60,000件 | 未測定 |

このレポートでは、Ambient L4 の P50 の差は小さく、調整前の Sidecar より成功しなかった応答が少なかったと観測されています。強化後のサンプルでは、Sidecar と Ambient L4 のどちらもエラーが0件でした。HTTP 503 が0件でもダウンタイムがないとは限りません。また、waypoint で観測されたエラー率は、固有の故障率を示すものでも、その原因が IP の再利用だったと証明するものでもありません。

まず必要な機能を選び、次に総エラー数、レイテンシー、ID、運用性をワークロードの予算と照らして検証してください。Cilium 欄は文書化された機能だけを示しており、このテストでは Cilium をデプロイしていません。

## 1. mTLS: テスト結果（EKS 1.36.2、Istio 1.30.2）

元レポートには、専用の `mesh-isolated-test` クラスター、専用 VPC、Amazon Linux 2023 を実行する arm64 の m7g.xlarge ノード、3つの mesh namespace を対象とした namespace スコープの STRICT PeerAuthentication が記載されています。コントロールプレーンとワーカーノードの Kubernetes バージョンはいずれも 1.36.2 と報告されています。

記録された Pod IP 宛ての平文通信の試行は失敗しました。

```text
plaintext-client -> sidecar echo pod:8080  => connection reset
plaintext-client -> ambient-L4 echo:8080  => EOF
plaintext-client -> ambient-L7 echo:8080  => EOF
```

記録された mesh 内 Service 呼び出しは、3つのモードすべてで HTTP 200 を返しました。Envoy 関連のレスポンスヘッダーには違いがありましたが、ヘッダーがあるかないかだけで暗号化や通信が通った完全なプロキシ経路を証明することはできません。

証明書のコマンドでは、証明書を保持または要求しているプロキシを調べています。プロキシは証明書の発行者ではありません。

| ワークロード | 調査したプロキシ | SPIFFE ID | ルート CA |
|---|---|---|---|
| ambient-L4 echo | ztunnel | `spiffe://cluster.local/ns/mesh-test-ambient-l4/sa/default` | 共通 |
| ambient-L7 echo | ztunnel | `spiffe://cluster.local/ns/mesh-test-ambient-l7/sa/default` | 共通 |
| sidecar echo | istio-proxy | `spiffe://cluster.local/ns/mesh-test-sidecar/sa/default` | 共通 |

表示されている ID は**namespace／ServiceAccount の ID**です。同じ default ServiceAccount を使う echo Pod と client Pod は同じ ID を共有します。Pod ごとに一意な SPIFFE ID ではありません。ワークロード証明書は Istiod または設定された CA が提供します。

報告された拒否・成功のケースは、これらの通信に対する STRICT 適用と整合します。ただし、クラスター内のすべての経路、プロトコル、送信元、迂回経路を網羅したことを示すものではありません。Ambient は Istio CNI の network namespace キャプチャ経路と TCP 15008 上の HBONE を使用します。Sidecar mode ではワークロードのプロキシを使用します。適用範囲は [mTLS ガイド](../security/01-mtls.md)を参照してください。

## 2. NetworkPolicy: テスト結果

レポートでは VPC CNI の NetworkPolicy enforcement を使用し、agent のバージョンを `v1.3.5-eksbuild.3` としています。アドオン全体の設定・バージョン、ポリシーの endpoint、ノード状態の証拠は保存されていません。過去の結果を扱うときは報告されたバージョンを維持してください。

**ingress port の記録結果（作者が enforcement の有効化を確認したと報告した後）:**

| Mode | 結果 |
|---|---|
| sidecar | ✅ HTTP 200 OK（影響なし） |
| ambient-L4 | ❌ block（`i/o timeout`） |
| ambient-L7 | ❌ block（`i/o timeout`） |

**8080 と HBONE 15008 の許可後に記録された結果:**

| Mode | 結果 |
|---|---|
| ambient-L4 | ✅ HTTP 200 OK（復旧） |
| ambient-L7 | ✅ HTTP 200 OK（復旧） |

この結果は、テストした経路で HBONE が重要であることを示します。既存のポリシーがどれも Sidecar で変更なしに機能することや、15008 を許可すれば最小権限の Ambient ポリシーが完成することを示すものではありません。送信元 selector、waypoint 経路、DNS／コントロールプレーンへの egress、CNI の実装が関係します。NetworkPolicy が認識するのはトンネルのポートです。トンネル内部の通信には、適切な ID／ポートポリシーを使用してください。

作者は enforcement の有効化後に Pod を再作成すると、negative control が有効になったと報告しています。これは報告された構成での観測であり、現在のすべての agent が CNI ADD 時にしかポリシーを適用できないことや、ポリシーが一律に遡及適用されないことの証明ではありません。測定前に reconciliation と実際の enforcement を確認してください。現在の AWS ドキュメントでは、標準 startup はポリシー設定まで通信を許可し、strict startup は必要な依存先への明示的な許可が必要と区別されています。

現在の AWS ドキュメントでは、Deployment、StatefulSet、DaemonSet、Job などコントローラーが所有する Pod がサポートされています。standalone Pod には追加の制限があります。Cilium は標準 NetworkPolicy と独自の policy CRD を別々にサポートします。別の実装で得た結果から、いずれかの挙動を推定しないでください。

## 3. レイテンシー: テスト結果（T5）

レポートによると、同じ Graviton クラスターで Fortio を定常状態にし、要求 QPS 200、60秒、接続数16で実行し、各ケースで12,000件の成功リクエストを得ています。

| ケース | P50 | P75 | P90 | P99 | P99.9 |
|---|---:|---:|---:|---:|---:|
| no-mesh（ベースライン） | 0.82ms | 1.33ms | 1.73ms | 1.97ms | 2.00ms |
| sidecar | 2.11ms | 2.60ms | 2.89ms | 3.91ms | 8.00ms |
| ambient-L4（waypoint なし） | 0.86ms | 1.34ms | 1.74ms | 1.98ms | 2.93ms |
| ambient-L7（waypoint あり） | 2.68ms | 3.06ms | 3.63ms | 3.98ms | 7.67ms |

報告された P50 の差は Sidecar が1.29 ms、Ambient L4 が0.04 ms、Ambient L7 が1.86 ms です。引き算は正しいです。小さな差を無視できると判断したり、取引システムや SLO の予算に当てはめたりするには、反復実行時のばらつき、リソース／配置の詳細、実際の結果 JSON が必要です。

付録では実行時間を指定する Fortio コマンドを使います。要求 QPS × 実行時間は予定する負荷量であり、呼び出し数の厳密な保証ではありません。各実行で記録した DurationHistogram.Count と RetCodes を使用してください。実験を再実行し、成果物を保存しない限り、過去のバージョン表記を更新しないでください。

## 4. ダウンタイムなしのローリング更新: 503 テスト結果（主要な知見）

### 背景

Pod の終了、endpoint の伝播、アプリケーション／プロキシのドレイン、接続プール、タイムアウトは、いずれもローリング更新時の失敗に影響します。宛先 IP の再利用競合と ztunnel への通知欠落が原因だという元の説明は、表示された件数から確定した原因ではなく**仮説**です。特定の仕組みに原因を帰属させる前に、プロキシの response flag、実際の upstream host、endpoint／Pod UID の時系列、接続の証拠で確認してください。

レポートでは mesh namespace ごとに echo の replica を6つと Fortio client を使い、要求 QPS 100、600秒で実行し、対象 Deployment を繰り返し再起動しました。アプリケーションの manifest は同等にする意図でしたが、注入されたプロキシや共有プロキシのリソース、実際にさらされたローリング更新の時間は mode ごとに異なりました。

### 結果

| Mode | ローリング更新回数 | リクエスト数 | 503件数 | 503率 | HTTP以外の結果（-1） | 使用ソケット数 |
|---|---:|---:|---:|---:|---:|---:|
| sidecar | 42 | 60,000 | 324 | **0.5%** | 2（0.0%） | 350 |
| ambient-L4（waypoint なし） | 64 | 60,000 | **0** | **0%** | 195（0.3%） | 1,652 |
| ambient-L7（waypoint あり） | 65 | 59,913 | 1,528 | **2.6%** | 84（0.1%） | 2,486 |

元の記事には、機械可読の完全な成果物ではなく、注釈付きの次の概要も記載されていました。

<details>
<summary>記録された件数（解釈上の注釈を修正済み）</summary>

```text
[sidecar]      42 rollouts, Sockets used: 350 (client concurrency: 16)
  Code 200 : 59674 (99.5 %)
  Code 503 : 324 (0.5 %)
  Code  -1 : 2   (0.0 %)

[ambient-L4]   64 rollouts, Sockets used: 1652
  Code 200 : 59805 (99.7 %)
  Code  -1 : 195 (0.3 %)   <- no HTTP response recorded; not a 503

[ambient-L7]   65 rollouts, Sockets used: 2486
  Code 200 : 58301 (97.3 %)
  Code 503 : 1528 (2.6 %)
  Code  -1 : 84  (0.1 %)
  (59,913 counted calls; nominal offered calls: 60,000; avg latency 50.4ms vs. ~2-3ms for the other two modes)

```

</details>

数値を解釈するときは、次の制約に注意してください。

1. 数えられた呼び出しから計算した HTTP 503 の割合は 324/60,000 = 0.54%、1,528/59,913 ≈ 2.55%、比は約4.72です。元の丸めた表示の0.5%／2.6%および「約5倍」はこのサンプルの説明であり、製品に固有の倍率ではありません。
2. Ambient L4 では HTTP 以外の失敗が195件ありました。HTTP 503 が0件でも、失敗が0件とは限りません。Fortio の -1 は HTTP 以外の結果をまとめたものです。reset／EOF／timeout の具体的な原因を知るには元のエラー記録が必要です。
3. 名目上の60,000件と87件違うからといって、開始したリクエストのうち87件が完了しなかったと確定するわけではありません。時間指定モードでは、呼び出し数が少なくなる場合があります。記録値の59,913件と平均50.4 msを維持し、「未完了リクエスト」の状態を作り上げないでください。
4. Fortio の SocketCount は client 側のソケット数です。waypoint の upstream pool を直接測定した値ではありません。接続が継続的に再利用されるなら16ソケットは設定された client concurrency と一致しますが、すべての upstream 接続が正常だったことの証明にはなりません。
5. ベースラインで完了したローリング更新数は42／64／65で、最大だったのは L4 ではなく Ambient L7 です。ローリング更新にさらされた時間が同一でなく、リソースや時系列の成果物も不足しているため、因果関係の比較には限界があります。

### 追加検証: graceful shutdown の強化後

元レポートでは全 mode に対し、10秒の preStop sleep と40秒の Pod termination grace period を設定しました。さらに Sidecar では EXIT_ON_ZERO_ACTIVE_CONNECTIONS=true と terminationDrainDuration 30s も設定しました。

| Mode | ローリング更新回数 | HTTP 200 | HTTP 503 | -1 | 使用ソケット数 | 平均レイテンシー |
|---|---:|---:|---:|---:|---:|---:|
| sidecar（強化後） | 42 | 60,000（100%） | **0** | **0** | 16 | 2.630ms |
| ambient-L4（強化後） | 38 | 60,000（100%） | **0** | **0** | 395 | 1.189ms |
| ambient-L7（強化後） | 45 | 59,352（98.9%） | 648（1.1%） | **0** | 678 | 3.843ms |

| Mode | ベースラインのエラー率 | 強化後のエラー率 | 変化 |
|---|---|---|---|
| sidecar | 503 が0.5% + TCP が0% | 503 が0% + TCP が0% | **このサンプルでは HTTP 503 の観測が0件** |
| ambient-L4 | 503 が0% + TCP が0.3% | 503 が0% + TCP が0% | **このサンプルでは HTTP 以外のエラーの観測が0件** |
| ambient-L7 | 503 が2.6% + TCP が0.1% | 503 が1.1% + TCP が0% | 503 率は半分超減少 |

これらは記載されたサンプルでの観測結果です。Sidecar は**2つの要因**を変更しているため、結果を preStop だけに帰属させることはできません。強化後のローリング更新数も42／38／45と異なります。ワークロードの shutdown 調整で報告値は改善しましたが、残る waypoint のエラーが同じ原因であることや、他の2つの mode で常にエラーが0件になることを証明するものではありません。

grace period には preStop とコンテナ終了の両方が含まれます。10秒 sleep は時間を確保するだけで、すべての endpoint 更新が伝播したことを確認するものではありません。リリース済みの 1.30.2 のコードでは、EXIT_ON_ZERO_ACTIVE_CONNECTIONS は設定された最小 drain 期間を待ってから、downstream listener の接続統計を1秒ごとに確認します。この分岐は通常の terminationDrainDuration timer を使いません。Kubernetes の終了制限や観測エラーも影響します。即時終了や、常に30秒で終了する保証として説明しないでください。

### 緩和策として retry を使うリスク: テスト結果（T2）

元レポートでは、replica 6つの order service、collector、client を用い、毎秒20リクエストの設定、300秒の実行、3回の retry と1回当たり2秒の timeout を設定した VirtualService policy が説明されていました。以下の数値は**報告値であり、独立して再現した値ではありません**。

| Mode | ローリング更新回数 | 送信リクエスト数 | client から見た失敗（報告値） | 重複報告（報告値） |
|---|---:|---:|---:|---:|
| sidecar（VirtualService retry） | 11 | 9,135 | 15（0.16%） | **0** |
| ambient-L7（waypoint retry） | 12 | 7,229 | 21（0.29%） | **0** |

元の付録では、以下の解釈を裏付けられません。

- 逐次実行する client は無期限に動作し、統計を出力せず、成功時のみ sent を増やしていました。毎秒20回の上限なら、300秒で9,135回または7,229回を説明できません。server の0.1秒 delay も実際の処理率をさらに制約します。
- client の3秒 timeout は、元の要求と2秒の retry 3回を合わせた想定時間が終わる前に切れる可能性があります。最終的な失敗だけでは retry をすべて使い切ったと分かりません。
- Collector の報告エラーは無視される一方、order server は201を返していました。実行中の client と counter の reset が重なり、ambient 用にコピーされた manifest も Sidecar namespace の Service を参照したままでした。
- X-Request-Id はプロキシ／トレース用 ID であり、変更されない業務コマンド ID とは限りません。観測が不完全な状態で重複報告が0件でも、業務処理が重複しなかった証明にはなりません。
- 最終的な失敗率が低くても retry が作動したとは限りません。レポートには有効な route、retry counter、実際の配送数が含まれていません。

改訂版の付録では、driver に終了条件と観測機能を設け、業務用の個別 ID を使用し、observer の失敗を不明／エラーの結果として扱います。過去の数値の出所を補うものではありません。メモリ内 collector は永続的な取引台帳でも idempotency 実装でもありません。

### retry によって隠れる失敗と生の失敗を分ける

mTLS の data plane 選択と HTTP retry policy は別の判断です。Sidecar Envoy と waypoint Envoy は L7 で HTTP request を retry できます。ztunnel は [L4 proxy](https://istio.io/latest/docs/ambient/architecture/data-plane/) であり、HTTP 503 を解釈したり HTTP request を再送したりできません。

公平なベースラインでは、POST／PUT／PATCH／DELETE などの書き込み route に attempts: 0 を明示し、次を別々に測定してください。

- retry 前の HTTP error と HTTP 以外の失敗。
- 実際の関連 proxy／cluster の Envoy upstream_rq_retry と upstream_rq_retry_success counter。
- 元の request を含む、upstream への配送数／observer の記録件数。
- client の最終的な成功／失敗と、client 側の完全な集計。
- 同一の業務コマンド ID が複数回記録されたか、observer の失敗や再起動があったか。

| Data plane | mTLS／暗号化の意味 | L7 retry の位置 | 推奨する用途 |
|---|---|---|---|
| Istio sidecar | ワークロード SPIFFE 証明書による mTLS | Pod ごとの Envoy | 重要な non-idempotent 経路の保守的なベースライン |
| Istio ambient L4 | ztunnel 間の HBONE workload mTLS | なし | Istio mTLS と L4 policy だけが必要な場合の最初の候補 |
| Istio ambient L7 | HBONE と waypoint Envoy | 共有 waypoint | HTTP routing または L7 policy が必要な Service にだけ追加 |
| Cilium out-of-band + WireGuard/IPsec | ID の相互認証と WireGuard/IPsec などの通信暗号化は個別に選択 | L3/L4 暗号化レイヤーにはなし | ID policy とネットワーク暗号化を必要とする既存 Cilium data plane |

Cilium 欄は L3/L4 の認証・暗号化レイヤーを指しており、Cilium に任意の L7 proxy 機能がないという意味ではありません。ここでは Cilium の性能やローリング更新挙動を測定していません。

Cilium 1.20.1 には、別機能として [ztunnel transparent-encryption beta](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/network/encryption-ztunnel.rst) もあり、`encryption.type: ztunnel` で選択します。namespace を登録して TCP workload mTLS を提供し、通信する両 endpoint を登録する必要があります。ClusterMesh と host-network Pod は対象外です。また、リリース済みガイドには、HBONE ポート15008を対象とする場合を除き、通常の L4 policy はこの経路では機能しないと記載されています。CA／bootstrap 要件も異なる独立した構成です。

この章で報告した測定に ztunnel beta は含まれていません。

> **運用ルール:** mTLS だけが要件なら、まず Ambient L4 を検証し、L7 policy または mesh 内の HTTP routing が必要な Service にのみ waypoint を追加してください。書き込み retry を無効にして測った Ambient の総エラー数がワークロードの error budget を超える場合、重要な non-idempotent 経路では Sidecar をベースラインとして維持してください。アプリケーション retry と idempotency は別途制御する必要があります。

### テストの分離に関する注記

元の作者は、共有クラスター上で干渉／リソース消失があったことと、専用クラスターでの初回試行時に workstation の current-context が変更されたことを報告しています。フォレンジック用の記録は添付されていないため、これらの報告から削除原因を特定したり Istio の不具合を立証したりすることはできません。

必要なのは明示的な分離です。制御されたテストクラスター、専用 kubeconfig／context と server の照合、完全なリソース一覧、成果物の保存を徹底してください。以前の付録では本文に記載された context guard が抜けていました。改訂した手順では明記しています。namespace を分けただけでは CPU／network や control plane の条件が独立する保証はありません。

## 5. 推奨事項: tier 別のアプローチ

ワークロード tier は計画上の分類であり、安全性の保証ではありません。

| ワークロードの要件 | 候補 | 必要な検証 |
|---|---|---|
| mTLS と L4 policy のみ | まず Ambient L4。適切な場合は実証済み Sidecar baseline も維持 | 実際の ID、NetworkPolicy／内部ポート enforcement、総失敗数、レイテンシー |
| HTTP routing または L7 authorization | 要件に合う waypoint、呼び出し元 Sidecar、または gateway | policy の正しい適用先、有効な設定、ワークロードの error budget |
| 重要な non-idempotent command | 書き込み retry policy とサーバー側の正当性制御を明示した任意の data plane | 安定した業務 ID、永続的な idempotency／transaction、応答喪失・復旧テスト |
| Read API、通知、batch | 実際の意味と必要機能に基づいて選択 | 通知／batch には副作用があり得る。retry 安全な read でも負荷を増幅し得る |

3つの mesh namespace を共存させたという報告は参考になりますが、混在デプロイ、ワークロード、policy の組み合わせがすべて安全だと証明するものではありません。

### L4 のみの制限: canary deployment は可能か？

ztunnel は HTTP request 単位の header／path routing、mirroring、HTTP retry を提供しません。**Istio が管理する** ingress gateway は、Ambient backend に転送する前に L7 routing を行えます。Gateway API 自体は API であり、必ずしも Envoy Deployment とは限りません。挙動は GatewayClass／controller によって決まります。

Istio VirtualService は DestinationRule の subset を選択できます。一方、標準 HTTPRoute の backendRefs は通常 Service を選択します。両者を同じ subset API と説明しないでください。

mesh 内の east-west HTTP routing では、実際の呼び出し元／gateway／waypoint 経路上で L7 の判断を行う必要があります。宛先 B に Sidecar を追加するだけでは、Ambient L4 の呼び出し元が送信側 HTTP policy によって B-v1／B-v2 を選ぶようにはなりません。B の waypoint、適切な呼び出し元 proxy、または明示的に設計した別の L7 hop を使ってください。L4 の接続単位の分散や replica 単位のローリング更新は、HTTP request 単位の分割とは異なります。

実際の機能要件、CNI／policy の挙動、書き込み retry、ワークロード自身の測定結果を確認してください。以下のラボ手順例は新たな証拠を集めるためのものであり、元レポートで不足している事実を遡って立証するものではありません。

## 付録: テストの再現

これは管理された追試用の改訂手順であり、元の結果を保証するコピー＆ペースト手順ではありません。ローカル検査では構文、設定生成、Python の observer／client 動作を確認しています。クラスターでのスケジューリング、mesh policy の適用、CNI enforcement、測定の完全性は、実際のラボで検証する必要があります。

### A. クラスターのプロビジョニング（eksctl）

次は元レポートに記載された**保存済みの入力**です。ノードやネットワークの選択を説明するものであり、この監査では実行していません。

<details>
<summary>記録された eksctl-cluster.yaml</summary>

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: mesh-isolated-test
  region: ap-northeast-2
  version: '1.36'
  tags:
    purpose: istio-sidecar-vs-ambient-retest
    ephemeral: 'true'
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
    ephemeral: 'true'
addons:
- name: vpc-cni
- name: coredns
- name: kube-proxy
- name: eks-pod-identity-agent
```

</details>

Kubernetes のマイナーバージョン、version 固定されていないアドオン、現在の AMI 選択では、元の control plane の patch、node image、agent version を正確に再現できません。public subnet と NAT なしのテスト構成は本番向けの推奨ではありません。private endpoint、IPv6、NAT 経由の egress は実際のネットワーク要件によって決まります。

新たなテストには承認済みの隔離されたクラスターを使用し、ARN／API endpoint、node／AMI／kernel の version、CNI／agent の設定、リソース一覧を記録してください。休眠状態だった policy を有効化したり、無関係なクラスターの共有 CRD を置き換えたりしないでください。

### B. Istio のインストール（Gateway API CRD + ambient profile）

対象クラスターの記録を基に入力値を設定してください。以下の helper は kubeconfig／context を明示的に選択し、API server の対応関係を再確認します。

```bash
set -euo pipefail
: "${TEST_KUBECONFIG:?Set the dedicated kubeconfig file}"
: "${TEST_CONTEXT:?Set its explicit test context}"
: "${ISTIOCTL_BIN:?Set the path to the intended Istio 1.30.2 CLI}"
: "${EXPECTED_API_SERVER:?Set the approved API-server URL}"
: "${NS:?Select the test namespace}"
: "${RUN_DIR:?Set a new artifact directory for this run}"
case "$NS" in
  mesh-test-base|mesh-test-sidecar|mesh-test-ambient-l4|mesh-test-ambient-l7) ;;
  *) echo "Unexpected test namespace" >&2; exit 1 ;;
esac
check_mesh_context() {
  local actual
  actual=$(kubectl --kubeconfig "$TEST_KUBECONFIG" --context "$TEST_CONTEXT" \
    config view --minify -o jsonpath='{.clusters[0].cluster.server}') || return 1
  if [ "$actual" != "$EXPECTED_API_SERVER" ]; then
    echo "API-server mismatch; stopping" >&2
    return 1
  fi
}
kmesh() {
  check_mesh_context &&
    kubectl --kubeconfig "$TEST_KUBECONFIG" --context "$TEST_CONTEXT" "$@"
}
imesh() {
  check_mesh_context &&
    "$ISTIOCTL_BIN" --kubeconfig "$TEST_KUBECONFIG" --context "$TEST_CONTEXT" "$@"
}
check_mesh_context
mkdir -p "$RUN_DIR"
```

これにより共有 current-context に依存せずに済みますが、同時に発生するあらゆるクラスター／credential の変更を防ぐものではありません。専用ファイルを管理下に置き、検証したクラスター ID を記録してください。

報告された version は Istio 1.30.2 です。元の付録にあった Gateway API 1.1.0 との互換性の説明は、インストール済み bundle の記録で裏付けられていません。リリース済みの 1.30.2 依存関係と conformance では 1.5.1 が使われています。改訂した Gateway／HTTPRoute のケースでは、他のインストール済み controller を確認した後、対応する標準 bundle を使用してください。catalog の最新版を互換性の証拠とみなさないでください。

```bash
# Only for a new dedicated lab needing this compatible bundle.
kmesh apply --server-side -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.5.1/standard-install.yaml
imesh manifest generate -f ambient-overlay.yaml > "$RUN_DIR/istio-rendered.yaml"
# Review the render, existing ownership and installed version before installation.
imesh install -f ambient-overlay.yaml
```

Ambient L4 だけなら waypoint resource は不要です。この実験には L7 ケースがあるため、waypoint を作る前に互換性のある Gateway API resource が必要です。意図した Istio CLI／version とサポートされた upgrade 経路を使用し、過去のテストを説明なく新しい release に更新しないでください。

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
                values:
                - arm64
    ztunnel:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: kubernetes.io/arch
                operator: In
                values:
                - arm64
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
                  values:
                  - arm64
```

この overlay の CNI、ztunnel、Istiod の arm 64 affinity は、ネイティブの 1.30.2 offline render で確認されています。render はデプロイテストではありません。

### C. Namespace とワークロード manifest

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

以下のアプリケーション template は1ケース分です。選択したケースの namespace にすべての metadata.namespace を変更し、不一致があれば失敗するよう明示的な `-n "$NS"` を付けて適用してください。アプリケーション設定は同等に保ちますが、注入される proxy と共有 proxy の構成の差も記録してください。

<details>
<summary>改訂版 echo／Fortio workload template</summary>

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: echo
  namespace: mesh-test-sidecar
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
        kubernetes.io/os: linux
      containers:
      - name: echo
        image: fortio/fortio:1.69.4@sha256:65633fc5e70f9745be8c311637fb8e484da31a366463028a11083ac0a098e3d3
        args:
        - server
        - -http-port
        - '8080'
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
    name: http
    appProtocol: http
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
        kubernetes.io/os: linux
      containers:
      - name: fortio-client
        image: fortio/fortio:1.69.4@sha256:65633fc5e70f9745be8c311637fb8e484da31a366463028a11083ac0a098e3d3
        command:
        - /usr/bin/fortio
        args:
        - server
        - -http-port
        - '8081'
        - -redirect-port
        - disabled
        resources:
          requests:
            cpu: 50m
            memory: 32Mi
          limits:
            cpu: 300m
            memory: 128Mi
```

</details>

新しい例では、このレビューで registry digest を確認した Fortio version を固定し、HTTP port を明記しています。元レポートには image digest や全プロトコル設定の記録がありません。したがって、改訂は過去の実行が同じ byte を使った証拠ではありません。Fortio image は scratch ベースです。image 内に sh／curl／cat があると想定せず、binary を使用してください。

### D. mTLS: PeerAuthentication（§1）

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

L7 namespace では次も適用します。

```bash
imesh waypoint apply -n mesh-test-ambient-l7 --enroll-namespace --wait
kmesh -n mesh-test-ambient-l7 get gateways.gateway.networking.k8s.io -o yaml
```

負荷をかける前に、実際の Pod 注入／enrollment、証明書、Service の通信経路を検証してください。Pod IP 宛ての平文通信が拒否される直接テストは L4 enforcement を確認するものです。すべての呼び出しが waypoint や L7 policy を経由する証明ではありません。

### E. NetworkPolicy（§2）

network-policy opt-in は、レビュー済みの既存アドオン設定に対して、その所有者を通じて統合してください。

```json
{"enableNetworkPolicy":"true"}
```

実際の CNI／agent version と standard／strict startup mode を記録してください。ほかのアドオン設定を無視し、1項目だけの更新で OVERWRITE しないでください。生成された policy endpoint と、reconciliation 後の negative-control 通信を確認します。インストール済み環境に応じて、テスト対象 Pod の再作成が必要か検証してください。過去の観測を普遍的な非遡及ルールにしないでください。

```bash
kmesh -n "$NS" get policyendpoints.networking.k8s.aws
```

Test 1 と Test 2 は、同じ対象ワークロード／policy 名に対する連続した別案です。

```yaml
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
```

```yaml
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

それぞれ選択したケースの namespace に適用してください。この port rule は送信元を制限しない到達性実験であり、tenant 分離を完全に行う設定ではありません。ほかに選んだ policy と組み合わせて適用されます。tunnel port を1つ許可すれば元の policy 境界がすべて維持されると仮定せず、DNS、control plane、送信元、内部 port／ID の要件を実際にテストしてください。

### F. ローリング更新と503のテスト（T1、§4）

ケースごとに、workload が ready であることを確認し、新しい成果物ディレクトリを使ってください。以下の上限付き loop は、Fortio の実際の結果と並べてローリング更新の時間帯を記録します。loop の開始と負荷生成開始は原子的に同期しません。更新が負荷終了後に完了する場合も含め、時刻を使って重なった期間を特定してください。

```bash
# Run after loading the context helpers above. Requires GNU timeout.
DUR=600
kmesh -n "$NS" rollout status deployment/echo --timeout=120s
kmesh -n "$NS" rollout status deployment/fortio-client --timeout=120s
CLIENT=$(kmesh -n "$NS" get pods -l app=fortio-client \
  -o jsonpath='{.items[0].metadata.name}')
test -n "$CLIENT"
STOP_FILE="$RUN_DIR/stop-rollouts"
test ! -e "$STOP_FILE"
trap 'touch "$STOP_FILE"' EXIT INT TERM
(
  begin=$(date +%s)
  while [ $(( $(date +%s) - begin )) -lt "$DUR" ] && [ ! -e "$STOP_FILE" ]; do
    cycle_start=$(date +%s)
    kmesh --request-timeout=15s -n "$NS" rollout restart deployment/echo || exit 1
    kmesh --request-timeout=75s -n "$NS" rollout status deployment/echo \
      --timeout=60s || exit 1
    printf '%s,%s\n' "$cycle_start" "$(date +%s)" >> "$RUN_DIR/rollout-times.csv"
  done
) >"$RUN_DIR/rollouts.log" 2>&1 &
ROLLOUT_PID=$!

check_mesh_context
load_status=0
timeout --signal=TERM --kill-after=5s "$((DUR+30))s" \
  kubectl --kubeconfig "$TEST_KUBECONFIG" --context "$TEST_CONTEXT" \
  -n "$NS" exec "$CLIENT" -c fortio-client -- \
  fortio load -qps 100 -t "${DUR}s" -c 16 -allow-initial-errors \
  -json - -quiet -loglevel Error http://echo:8080/ \
  >"$RUN_DIR/fortio.json" 2>"$RUN_DIR/load.log" || load_status=$?
touch "$STOP_FILE"
rollout_status=0
wait "$ROLLOUT_PID" || rollout_status=$?
trap - EXIT INT TERM
if [ "$load_status" -ne 0 ] || [ "$rollout_status" -ne 0 ]; then
  echo "Invalid run: inspect load/rollout logs" >&2
  exit 1
fi
jq -e '.DurationHistogram.Count > 0 and (.RetCodes | type == "object")' \
  "$RUN_DIR/fortio.json" >/dev/null
```

結果 JSON、両方の stderr log、ローリング更新の時間帯、Pod／endpoint の時系列、proxy 設定を保存してください。timeout や更新失敗があれば run は不完全です。部分出力を正常サンプルとして黙って扱わないでください。`SocketCount` は Fortio client 側のソケット数です。

追試では、以下の適切な fragment を既存 echo Deployment に統合してください。これらは standalone Deployment manifest ではなく**strategic-merge fragment**です。最初は共通のアプリケーション変更、2つ目は Sidecar proxy の shutdown 設定も変更します。

```yaml
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
---
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

新しい run directory で実験を繰り返し、変更した要因を記録してください。報告された Kubernetes version では kubelet の sleep lifecycle hook を利用できます。古いクラスターでは機能対応を個別に確認してください。Pod grace period には preStop が含まれます。sleep は endpoint の収束を確認するものではなく、proxy の exit-on-zero 経路も必ず30秒で drain する保証ではありません。

### G. レイテンシーテスト（T5、§3）

ローリング更新 loop を使わず、workload を安定させてください。

```bash
# No rollout loop for this steady-state case.
kmesh -n "$NS" rollout status deployment/echo --timeout=120s
CLIENT=$(kmesh -n "$NS" get pods -l app=fortio-client \
  -o jsonpath='{.items[0].metadata.name}')
test -n "$CLIENT"
kmesh -n "$NS" exec "$CLIENT" -c fortio-client -- \
  fortio load -qps 200 -t 60s -c 16 -allow-initial-errors \
  -json - -quiet -loglevel Error http://echo:8080/ \
  >"$RUN_DIR/fortio-latency.json" 2>"$RUN_DIR/latency.log"
jq '{Version, RequestedQPS, ActualQPS, ActualDuration,
     count: .DurationHistogram.Count, RetCodes, SocketCount}' \
  "$RUN_DIR/fortio-latency.json"
```

実際の件数、達成 QPS、error code、必要な全 percentile、run ごとのばらつきを報告してください。QPS 200、60秒という要求値は負荷設定であり、成功呼び出しが厳密に12,000件だった証明ではありません。

### H. 重複実行の観測（T2、§4）

次の改訂版 toy harness は、元の上限のない client と黙って失敗する observer に代わるものです。client の各論理コマンドに安定した `Idempotency-Key` を記録し、Envoy の trace header を業務 ID として使いません。意図的にコマンドを**重複排除せず**、永続的な業務 transaction も実装しません。

ConfigMap を t2-configmap.yaml として保存します。

<details>
<summary>上限付き client、order server、メモリ内 observer</summary>

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: t2-scripts
  namespace: mesh-test-sidecar
data:
  order_server.py: |
    import http.server
    import os
    import time
    import urllib.error
    import urllib.request

    COLLECTOR_URL = os.environ.get("COLLECTOR_URL", "http://collector:9090/record")


    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            if self.path != "/order":
                self.send_response(404)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            command_id = self.headers.get("Idempotency-Key", "").strip()
            if not command_id:
                self.send_response(400)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            self.rfile.read(int(self.headers.get("Content-Length", "0")))
            time.sleep(0.1)  # Processing delay before the observer record, not a post-commit delay.
            try:
                request = urllib.request.Request(
                    COLLECTOR_URL, data=command_id.encode(), method="POST"
                )
                with urllib.request.urlopen(request, timeout=2) as response:
                    response.read()
            except (urllib.error.URLError, TimeoutError, OSError) as error:
                if isinstance(error, urllib.error.HTTPError):
                    error.close()
                # The record may have committed before an ambiguous transport failure.
                print(f"observer outcome unknown for {command_id}: {error}", flush=True)
                self.send_response(503)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
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
            if self.path != "/record":
                self.send_response(404); self.send_header("Content-Length", "0"); self.end_headers(); return
            length = int(self.headers.get("Content-Length", 0))
            rid = self.rfile.read(length).decode().strip()
            with lock:
                counts[rid] = counts.get(rid, 0) + 1
            self.send_response(200); self.send_header("Content-Length","0"); self.end_headers()

        def do_GET(self):
            with lock:
                total = len(counts)
                deliveries = sum(counts.values())
                dupes = {k: v for k, v in counts.items() if v > 1}
            if self.path == "/dupes":
                body = json.dumps({"total_ids": total, "delivery_count": deliveries, "dupe_count": len(dupes), "dupes": dupes}).encode()
            elif self.path == "/stats":
                body = json.dumps({"total_ids": total, "delivery_count": deliveries, "dupe_count": len(dupes)}).encode()
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
    import json
    import math
    import os
    import time
    import urllib.error
    import urllib.request
    import uuid


    def run():
        target = os.environ.get("TARGET_URL", "http://order:8080/order")
        rps = float(os.environ.get("RPS", "20"))
        duration = float(os.environ.get("DURATION_SECONDS", "300"))
        timeout = float(os.environ.get("TIMEOUT_SECONDS", "12"))
        if not all(math.isfinite(value) and value > 0 for value in (rps, duration, timeout)):
            raise ValueError("RPS, DURATION_SECONDS and TIMEOUT_SECONDS must be finite and positive")
        interval = 1.0 / rps
        attempted = succeeded = failed = 0
        start = time.monotonic()
        deadline = start + duration
        while time.monotonic() < deadline:
            tick = time.monotonic()
            command_id = str(uuid.uuid4())
            attempted += 1
            request = urllib.request.Request(
                target, data=b"{}", method="POST", headers={"Idempotency-Key": command_id}
            )
            try:
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    response.read()
                    if 200 <= response.status < 300:
                        succeeded += 1
                    else:
                        failed += 1
            except urllib.error.HTTPError as error:
                error.close()
                failed += 1
            except (urllib.error.URLError, TimeoutError, OSError):
                failed += 1
            pause = min(interval - (time.monotonic() - tick), deadline - time.monotonic())
            if pause > 0:
                time.sleep(pause)
        elapsed = time.monotonic() - start
        return {
            "attempted": attempted,
            "succeeded": succeeded,
            "failed": failed,
            "requested_rps_cap": rps,
            "elapsed_seconds": elapsed,
            "achieved_rps": attempted / elapsed if elapsed else 0,
        }


    if __name__ == "__main__":
        print(json.dumps(run()), flush=True)
```

</details>

order server の0.1秒 delay は記録の**前**に発生するため、transaction commit 後に応答が失われる状況のテストではありません。collector の timeout／error は503を返し、結果不明の状態になります。応答が失われる前に observer が記録している可能性があります。この toy model で client が成功したという結果は observer の応答確認を意味するだけで、実際の業務処理が exactly-once である証明ではありません。

以下の最初の4 resource を t2-servers.yaml、最後の Job を order-client-job.yaml として保存します。各ケースでは、過去の client が存在しない新しい collector を使い、すべての metadata.namespace を一貫して変更してください。短い Service 名を使うことで呼び出しを選択した namespace 内に保ちます。

<details>
<summary>Collector／order の Deployment、Service、上限付き client Job</summary>

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
    name: http
    appProtocol: http
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
        kubernetes.io/os: linux
      containers:
      - name: collector
        image: python:3.12-alpine@sha256:b64631e04e4920160c50fbe8d8df828f7f35f06f425cb44aa09bca53e708a35a
        command:
        - python3
        - /scripts/collector.py
        ports:
        - containerPort: 9090
        volumeMounts:
        - name: scripts
          mountPath: /scripts
        readinessProbe:
          tcpSocket:
            port: 9090
          periodSeconds: 1
          timeoutSeconds: 1
          failureThreshold: 3
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
    appProtocol: http
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
        kubernetes.io/os: linux
      containers:
      - name: order
        image: python:3.12-alpine@sha256:b64631e04e4920160c50fbe8d8df828f7f35f06f425cb44aa09bca53e708a35a
        command:
        - python3
        - /scripts/order_server.py
        env:
        - name: COLLECTOR_URL
          value: http://collector:9090/record
        ports:
        - containerPort: 8080
        volumeMounts:
        - name: scripts
          mountPath: /scripts
        readinessProbe:
          tcpSocket:
            port: 8080
          periodSeconds: 1
          timeoutSeconds: 1
          failureThreshold: 3
      volumes:
      - name: scripts
        configMap:
          name: t2-scripts
---
apiVersion: batch/v1
kind: Job
metadata:
  generateName: order-client-
  namespace: mesh-test-sidecar
spec:
  backoffLimit: 0
  activeDeadlineSeconds: 360
  template:
    metadata:
      labels:
        app: order-client
      annotations:
        sidecar.istio.io/nativeSidecar: 'true'
    spec:
      restartPolicy: Never
      nodeSelector:
        kubernetes.io/os: linux
        kubernetes.io/arch: arm64
      containers:
      - name: order-client
        image: python:3.12-alpine@sha256:b64631e04e4920160c50fbe8d8df828f7f35f06f425cb44aa09bca53e708a35a
        command:
        - python3
        - /scripts/client.py
        env:
        - name: TARGET_URL
          value: http://order:8080/order
        - name: RPS
          value: '20'
        - name: DURATION_SECONDS
          value: '300'
        - name: TIMEOUT_SECONDS
          value: '12'
        volumeMounts:
        - name: scripts
          mountPath: /scripts
          readOnly: true
      volumes:
      - name: scripts
        configMap:
          name: t2-scripts
```

</details>

Job には自動 retry がなく、native-sidecar annotation を使用します。選択した Sidecar 注入が Job 完了を妨げないようにするためです。この annotation は Ambient Pod を登録せず、単独で Sidecar 注入を有効にするものでもありません。実際の Job Pod と namespace の登録状況を確認してください。改訂版 template では TCP readiness check を追加し、レビュー時に registry digest を確認した Python image を固定しています。元レポートにはその digest が保存されていません。ローカルで Python の挙動を確認したのはホストの Python 3.9 標準ライブラリです。このレビューでは Python 3.12 container を実行したり、これらの resource をデプロイしたりしていません。

client は**逐次実行**します。RPS20 は新しい試行の上限であり、一定の open-loop 20 QPS を保証しません。service の0.1秒 delay と失敗によって、実際の処理率は低下します。DURATION_SECONDS は新規 request の開始時間を制限します。最後の request は timeout の分だけ全体時間を延ばすことがあります。最終 JSON には attempted／succeeded／failed と achieved_rps が含まれ、attempted = succeeded + failed になります。

最初に、order command と observer への書き込み**両方**を明示的に retry しない route を設定し、order-no-retry.yaml として保存します。

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: order-retry
  namespace: mesh-test-sidecar
spec:
  hosts:
  - order
  http:
  - name: order-lab
    match:
    - method:
        exact: POST
      uri:
        exact: /order
    route:
    - destination:
        host: order
        port:
          number: 8080
    timeout: 10s
    retries:
      attempts: 0
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: collector-observer-no-retry
  namespace: mesh-test-sidecar
spec:
  hosts:
  - collector
  http:
  - name: observer-record
    match:
    - method:
        exact: POST
      uri:
        exact: /record
    route:
    - destination:
        host: collector
        port:
          number: 9090
    timeout: 10s
    retries:
      attempts: 0
```

意図的に危険な**隔離された retry 実験だけ**を行う場合は、以下の order-retry-experiment.yaml で order policy を置き換えます。collector には retry しない policy を維持してください。実験は配送の繰り返しが起こり得ることを調べるもので、本番書き込みで retry を推奨するものではありません。

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: order-retry
  namespace: mesh-test-sidecar
spec:
  hosts:
  - order
  http:
  - name: order-lab
    match:
    - method:
        exact: POST
      uri:
        exact: /order
    route:
    - destination:
        host: order
        port:
          number: 8080
    timeout: 10s
    retries:
      attempts: 3
      perTryTimeout: 2s
      retryOn: 503,reset,connect-failure
```

retry を3回設定すると最大4回の試行になります。試行ごとの2秒設定と10秒の route timeout は、接続／初期化にかかる時間と相互作用します。client timeout の12秒は観測時間を延長しますが、すべての試行が実施されたことの証明にはなりません。実際の proxy 設定と retry counter を記録してください。

報告された Istio 1.30 系では、Ambient での VirtualService 使用は Alpha であり、Gateway API の traffic configuration との混在はサポートされません。この実験に競合する HTTPRoute を追加しないでください。実際の client Sidecar または宛先 waypoint 上で有効な route を確認してください。Ambient L4 だけでは、この HTTP retry policy を適用できません。

```bash
# A fresh collector and no earlier client must be running for this case.
# Replace metadata.namespace in every input with NS; explicit -n catches mismatches.
kmesh -n "$NS" apply -f t2-configmap.yaml -f t2-servers.yaml -f order-no-retry.yaml
kmesh -n "$NS" rollout status deployment/collector --timeout=120s
kmesh -n "$NS" rollout status deployment/order --timeout=120s
kmesh -n "$NS" get pods -l app=collector -o json >"$RUN_DIR/collector-before.json"

# For the deliberate retry experiment only, replace the no-retry policy with
# order-retry-experiment.yaml and verify the effective proxy configuration first.
JOB_RESOURCE=$(kmesh -n "$NS" create -f order-client-job.yaml -o name)
JOB_NAME=${JOB_RESOURCE#*/}
if ! kmesh -n "$NS" wait --for=condition=complete "$JOB_RESOURCE" --timeout=370s; then
  kmesh -n "$NS" logs "$JOB_RESOURCE" -c order-client >"$RUN_DIR/client-failed.log" || true
  echo "Invalid/incomplete client run" >&2
  exit 1
fi
kmesh -n "$NS" logs "$JOB_RESOURCE" -c order-client >"$RUN_DIR/client.json"
jq -e '.attempted > 0 and .attempted == (.succeeded + .failed)' \
  "$RUN_DIR/client.json" >/dev/null
kmesh -n "$NS" get pods -l "batch.kubernetes.io/job-name=$JOB_NAME" \
  -o json >"$RUN_DIR/client-pods.json"
kmesh -n "$NS" get pods -l app=collector -o json >"$RUN_DIR/collector-after.json"
kmesh -n "$NS" logs -l app=order -c order --prefix --tail=-1 \
  --max-log-requests=10 >"$RUN_DIR/available-order.log"
kmesh -n "$NS" exec deployment/collector -c collector -- python3 -c \
  "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:9090/dupes', timeout=5).read().decode())" \
  >"$RUN_DIR/observer.json"
```

この driver は準備と集計を行いますが、order のローリング更新 loop は**起動しません**。churn を調べる場合は、§F を別途上限付きで変更し、300秒の client 実行期間中に deployment/order を対象として協調実行し、両方の時系列を保存してください。同期しなければ出力は定常状態の observer テストになります。

client が実行中の間、observer を reset しないでください。前後の collector Pod UID と restart 数を比較し、order／observer のすべての error を保存し、削除された Pod の log も残るようにしてください。上記のコマンドで取得できるのは、現在の Pod に残っている log だけです。observer の再起動、log 欠落、observer error があれば、重複検出が完全だったという主張は無効です。実際の取引の安全性を調べるには、コマンド単位の永続台帳と commit 後の応答喪失を制御したテストが必要です。

## 参考資料と検証範囲

- [Istio 1.30.2 release](https://github.com/istio/istio/releases/tag/1.30.2)、[リリース済み依存関係](https://github.com/istio/istio/blob/1.30.2/go.mod)、[proxy shutdown の実装](https://github.com/istio/istio/blob/1.30.2/pkg/envoy/agent.go)
- [Istio 1.30 ambient L7 の機能状態](https://github.com/istio/istio.io/blob/release-1.30/content/en/docs/ambient/usage/l7-features/index.md)、[traffic management](https://github.com/istio/istio.io/blob/release-1.30/content/en/docs/ambient/usage/traffic-distribution/index.md)
- [Kubernetes container lifecycle hook](https://kubernetes.io/docs/concepts/containers/container-lifecycle-hooks/)、[native sidecar container](https://kubernetes.io/docs/concepts/workloads/pods/sidecar-containers/)
- [Amazon EKS NetworkPolicy](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html)、[設定と startup mode](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy-configure.html)
- [Cilium policy のサポート](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/policy/index.rst)
- [Fortio 1.69.4 source と使い方](https://github.com/fortio/fortio/tree/v1.69.4)、[container build](https://github.com/fortio/fortio/blob/v1.69.4/Dockerfile)

設定生成、schema check、計算、ローカル HTTP テストでは、上記の具体的な修正点を確認しています。しかし、これらは過去の EKS 測定を再現するものではなく、本番性能、未テストのアドオン組み合わせとの互換性、業務処理の exactly-once 実行を立証しません。
