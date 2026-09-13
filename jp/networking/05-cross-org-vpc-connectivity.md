# クロス組織 VPC 接続

> **最終更新**: September 1, 2026

このドキュメントでは、**2 つの異なる AWS Organizations 間で VPC を接続する** 5 つの方法を扱います。たとえば、GPU ワークロードを既存の MSP 支払いアカウントとは別の支払いアカウント（別の Organization）で契約する場合です。ここで示すすべての数値は、実際の 2 つの Organizations をまたいだ構築・計測による検証結果です（ap-northeast-2、両アカウントとも ZoneId `apne2-az1` に固定）。

## 目次

1. [クロス組織接続が必要な理由](#why-cross-org-connectivity)
2. [5 つの選択肢の比較](#comparing-the-five-options)
3. [実地検証結果](#field-verification-results)
4. [レイテンシ計測（M1–M7）](#latency-measurements-m1m7)
5. [実地で得られた運用上の知見](#operational-findings-from-the-field)
6. [シナリオ別の推奨アーキテクチャ](#recommended-architecture-by-scenario)
7. [結論](#conclusion)

## クロス組織接続が必要な理由

GPU インスタンス（P5/P6 など）はコストが非常に大きいため、組織では既存の MSP 支払いアカウントではなく、**別の支払いアカウント（別の AWS Organization）** で契約することが増えています。一般的な動機は以下のとおりです。

- **請求の分離**: GPU 固有のボリュームディスカウント / EDP 最適化
- **Service quota の分離**: GPU vCPU 上限と Capacity Blocks を個別に管理
- **影響範囲の封じ込め**: SCP の誤設定やセキュリティインシデントを既存の本番環境から隔離
- **規制コンプライアンス**: AI/ML ワークロードのデータ境界と監査証跡を分離

主な課題は、既存環境（ORG A）と GPU 環境（ORG B）を接続することです。EKS の観点では、これはトレーニングクラスター（ORG B）から既存のデータパイプライン（ORG A）へ到達すること、または推論 API を既存サービスに公開することを対象とします。

## 5 つの選択肢の比較

| 観点 | ① TGW RAM Sharing | ② VPC Peering | ③ PrivateLink | ④ TGW Peering | ⑤ VPC Lattice |
|---|---|---|---|---|---|
| 仕組み | RAM 経由で外部アカウントに TGW を共有 | 1:1 VPC 接続 | NLB ベースの endpoint | ORG ごとの TGW 間 Peering | L7 Service network |
| 重複する CIDR | ❌ | ❌ | ✅ (ENI ベース) | ❌ | ✅ (link-local ベース) |
| 方向 | 双方向 L3 | 双方向 L3 | 一方向（Consumer→Provider） | 双方向 L3 | 一方向（Consumer→Provider） |
| 推移的ルーティング | ✅ TGW RT 経由 | ❌ | ❌ | ✅ | ❌（Service ごと） |
| ルーティング制御 | **TGW 所有アカウント（ORG A）** | 両側で独立 | Provider が principals を制御 | **各 ORG が独立** | Service network 所有者 |
| プロビジョニング時間（計測値） | TGW 約 3 分 + 承諾手順 | **1 分未満** | Endpoint 約 3 分 | **約 7 分（最長）** | 約 5 分 |

## 実地検証結果

5 つの選択肢はすべて、異なる 2 つの Organizations のアカウント間で構築し、コントロールプレーン（接続確立）とデータプレーン（実トラフィック）の両方でテストしました。**5 つすべてが実装可能です。** Organization 境界そのものによる制限はなく、境界で必要になるのは明示的な手順、すなわち **アカウント ID の指定と受信側での承諾** だけです。

![クロス組織の 5 経路計測トポロジー](../../assets/cross-org-5paths-latency.png)

## レイテンシ計測（M1–M7）

**計測設計** — シグナルはサブミリ秒単位のため、計測誤差はシグナルより小さくする必要があります。

- **c7g.large** インスタンス（バースト可能タイプは不使用）。応答側は **1 台の EC2 インスタンス（nginx 固定 200）** であり、ロードバランサーは構造上必要な場所（③⑤、および NLB hop を分離するための M7）にのみ使用します
- 応答側には 3 つの ENI（経路ごとの subnet と個別の戻り Route table）があるため、**M1–M7 は Route の入れ替えなしにラウンドロビンで交互実行し、5 ラウンド** 計測します
- 主指標: **永続 TCP_RR ping-pong、1 経路あたり 1,500 サンプル**（プロセス起動および handshake コストを除外）。副指標: ICMP 100/経路、HTTP keep-alive 275/経路

| ID | 経路 | ICMP p50 | TCP_RR p50 | RR p99 | RR sd | HTTP KA p50 | TTL |
|---|---|---|---|---|---|---|---|
| M1 | 同一 VPC → EC2（ベースライン） | 0.121 | **0.049** | 0.062 | 0.007 | 0.087 | 127 |
| M2 | ② VPC Peering → EC2 | 0.125 | **0.048** | 0.057 | 0.011 | 0.080 | 127 |
| M3 | ① 共有 TGW（RAM）→ EC2 | 0.535 | **0.619** | 0.695 | 0.141 | 0.686 | 126 |
| M4 | ④ TGW Peering（2 hops）→ EC2 | 0.912 | **0.599** | 0.855 | 0.133 | 0.488 | 125 |
| M5 | ③ PrivateLink → NLB → EC2 | 未計測 | **0.961** | 1.084 | 0.035 | 0.711 | — |
| M6 | ⑤ VPC Lattice → EC2 target | 未計測 | 未計測（L7 のみ） | — | — | **1.635** | — |
| M7 | ② Peering → NLB → EC2（NLB hop 分離） | 未計測 | **0.841** | 0.909 | 0.119 | 0.883 | — |

**導出指標（p50、ms）:**

| 指標 | 定義 | TCP_RR | ICMP |
|---|---|---|---|
| TGW 1-hop コスト | M3 − M2 | **+0.571** | +0.410 |
| TGW 2-hop コスト | M4 − M2 | **+0.551** | +0.787 |
| NLB hop コスト | M7 − M2 | **+0.793** | — |
| 純粋な PrivateLink ENI オーバーヘッド | M5 − M7 | **+0.120** | — |
| Lattice proxy コスト（HTTP） | M6 − M2 | +1.555 | — |

**判定:**

> **同一 AZ 内では、TGW hop は p50 で 0.4–0.6 ms を追加します** — 一般に観測される「hop あたりサブミリ秒」と整合します。
> **VPC Peering のレイテンシコストは計測限界内でゼロです**（M2 0.048 ≈ M1 ベースライン 0.049）。
> **PrivateLink ENI 自体が追加するのは +0.12 ms のみです** — PrivateLink の合計レイテンシ（0.96 ms）の大部分は、構造上必要な **NLB hop（+0.79 ms）** によるものです。Lattice の L7 proxy コストは +1.6 ms です。

**追加計測 — Service 前段配置での公平な比較（すべての経路に NLB）:** 実際のデプロイでは、Peering および TGW の経路でも Service 前段に NLB を置くため、すべての L3 経路について NLB 前段配置の構成を追加で構築・計測しました（subnet ごとの NLB、IP target、同一手法）。

| 構成 | TCP_RR p50 | HTTP KA p50 |
|---|---|---|
| ② Peering → NLB → EC2 | **0.622** | 0.648 |
| ③ PrivateLink → NLB → EC2 | **0.658** | 0.845 |
| ① 共有 TGW → NLB → EC2 | **1.273** | 1.257 |
| ④ TGW Peering → NLB → EC2 | **1.425** | 1.279 |
| ⑤ Lattice（LB 自体として機能 — NLB は不要） | — | **1.680** |

> **Service 公開フレームでの判定:** 純粋な PrivateLink ENI コストは +0.036 ms（N5−N2）であり、事実上ゼロです。応答側前段の NLB が共通のベースラインとなる実際の Service 公開構成では、**③ PrivateLink は Peering+NLB と同等であり、TGW 経路 + NLB より約 2 倍高速です。** 「直接 TGW は PrivateLink より高速」という結論は、LB を使わない直接接続フレームでのみ成り立ちます。Lattice はロードバランサー自体として機能するため個別の NLB は不要であり、同じフレームでの TGW+NLB との差は +0.3–0.4 ms に縮まります。

**手法から得た教訓**（以前の計測ラウンドを破棄して再実施した理由）: バースト可能インスタンス（t-family）、2 段の NLB→ALB proxy chain、リクエストごとの新規接続（curl）を組み合わせると、サブミリ秒のシグナルがノイズに埋もれます（経路に依存しない p95 は約 7 ms）。新規 TCP flow では、TGW/NLB を通る最初の RTT に実際に +0.6–1.6 ms の flow-setup コストがかかります。そのため、**keep-alive/長時間接続のワークロード（gRPC、NCCL、DB pool）と単発接続のワークロードでは、レイテンシを分けて評価してください**。

## 実地で得られた運用上の知見

1. **クロス組織 RAM 共有には、明示的な招待承諾ステップが必要です** — `--allow-external-principals` なしでは共有が拒否され、受信側が `accept-resource-share-invitation` を実行するまでリソースは表示されません（TGW と Lattice で同様です）。自動化パイプラインにはこの承諾ステップが必要です。
2. **共有 TGW への外部 ORG の attachment は `pendingAcceptance` で停止します** — TGW 所有者が承諾する必要があります。「所有者側での中央制御」は API レベルで強制されます。
3. **TGW Peering では各側で異なる attachment ID が表示されます** — リクエスター側の ID で accept API を呼び出すと `NotFound` が返ります。承諾側アカウントは自身の ID を一覧で見つける必要があり、propagation には約 2 分かかります。
4. **TGW Peering は BGP をサポートしません** — 両方の TGW Route table に static route を手動で追加する必要があります。
5. **Lattice のデータプレーンは link-local（169.254.171.0/24）から到達します** — target SG が VPC CIDR のみを許可している場合、すべての health check が UNHEALTHY になります。managed prefix list `com.amazonaws.<region>.vpc-lattice` を SG に追加してください。
6. **static TGW route は propagated route より優先されます** — 両者が共存する場合は、意図しない経路選択に注意してください。
7. **アカウント自動化は teardown を妨げます** — GuardDuty Runtime Monitoring の managed SG は VPC 削除をブロックし（DependencyViolation）、自動アタッチされた IAM policy は role 削除をブロックします。また、残存する Lattice target group も VPC 削除をブロックします。

## シナリオ別の推奨アーキテクチャ

| シナリオ | 第一選択 | 根拠（計測結果） |
|---|---|---|
| GPU ORG の完全分離、双方向の大量転送（トレーニングデータ） | **④ TGW Peering** | ORG ごとに独立したルーティング + 0.4–0.6 ms/hop のペナルティは無視できる |
| 推論 API のみを公開（一方向） | **③ PrivateLink** | 最小限の公開範囲、重複 CIDR に対応可能、Service 前段配置の比較では Peering+NLB と同等（TGW 経路 + NLB より約 2 倍高速） |
| 回避できない CIDR 重複（M&A、MSP 移行） | **③ PrivateLink / ⑤ Lattice** | ENI / link-local ベース — CIDR 非依存 |
| 既存 TGW に GPU アカウントだけを追加 | **① TGW RAM Sharing** | 既存 hub を再利用。外部 ORG はルーティングを変更できない |
| 小規模 PoC（1–2 VPCs） | **② VPC Peering** | 設定は 1 分未満、レイテンシコスト ≈ 0、追加インフラ不要 |
| L7 auth/governance が必要な Service 公開 | **⑤ VPC Lattice** | 組み込みの IAM Auth と Service discovery（+1.6 ms の proxy コストを許容） |

大半の GPU 分離シナリオでは、**④ TGW Peering（双方向インフラストラクチャ）+ ③ PrivateLink（推論 API 公開）** のハイブリッドが最適であり、計測結果もこの推奨を裏付けています。

## 結論

- 5 つすべての選択肢は、純粋に API を介して異なる Organizations 間で構成できます。Organization 境界は「アカウント ID の指定 + 受信側での承諾」としてのみ現れます。
- 同一 AZ 内: TGW は 0.4–0.6 ms/hop、VPC Peering ≈ 0、NLB hop は +0.79 ms、PrivateLink ENI は +0.12 ms、Lattice proxy は +1.6 ms — レイテンシコストは hop と proxy layer に応じて正直に増加します。
- EKS では、大量のトレーニングデータ転送（長時間接続）は TGW 経由でルーティングし、推論 API は PrivateLink 経由で公開します。

**制限事項（未計測）:** Network Firewall 検査を通る経路、Cross-Region、CIDR が重複する環境（機能面のみ確認）、および throughput/concurrency の軸。

---

## 参考資料

- [スケーラブルな Multi-VPC ネットワークインフラストラクチャの構築（AWS Whitepaper）](https://docs.aws.amazon.com/whitepapers/latest/building-scalable-secure-multi-vpc-network-infrastructure/welcome.html)
- [RAM を使用した TGW クロス組織共有（AWS Prescriptive Guidance）](https://docs.aws.amazon.com/prescriptive-guidance/latest/integrate-third-party-services/architecture-3-1.html)
- [単一 Organization と複数 Organizations の選択（AWS Architecture Blog）](https://aws.amazon.com/blogs/architecture/choosing-between-single-or-multiple-organizations-in-aws-organizations/)
- [VPC Lattice（このシリーズ）](02-vpc-lattice.md)
