# マルチアカウント・マルチクラスター EKS アーキテクチャクイズ

> このクイズでは、[マルチアカウント・マルチクラスター EKS アーキテクチャ](../../governance/03-eks-multi-account-multi-cluster.md)の理解度を確認します。

---

1. 2クラスターの A/B EKS 構成で妥当な検証目標はどれですか？
   - A) 単一 AZ の EKS control plane を修正する
   - B) アップグレード/add-on/webhook の障害を一方のクラスター内に封じ込められるかテストする
   - C) すべての Region の障害に自動的に対応する
   - D) コストの削減を保証する

<details>
<summary>回答を表示</summary>

**回答: B) アップグレード/add-on/webhook の障害を一方のクラスター内に封じ込められるかテストする**

**解説:**
クラスター固有の障害を封じ込められることは、この設計を採用する根拠になります。共有 VPC、DNS、Account、データの依存関係は別途分析が必要です。

</details>

---

2. ARC zonal shift のフェイルセーフ動作を正しく説明しているのはどれですか？
   - A) zonal shift が発生すると、ワークロードを問わず直ちにトラフィックが遮断される
   - B) ワークロードのエンドポイントが影響を受けた AZ にしかない場合、EKS はその AZ にトラフィックを送り続ける
   - C) すべてのワークロードが別の AZ に自動的に移動する
   - D) この動作は EKS Fargate でのみ発生する

<details>
<summary>回答を表示</summary>

**回答: B) ワークロードのエンドポイントが影響を受けた AZ にしかない場合、EKS はその AZ にトラフィックを送り続ける**

**解説:**
これがフェイルセーフの動作です。単一 AZ のみにデプロイされたワークロードは、zonal shift では保護されません。N-1 負荷と単一 AZ の例外をテストしてください。演習を行うと、そのワークロードが常に停止するという意味ではありません。

</details>

---

3. EC2 の link-local における毎秒1,024パケットの上限から、何が分かりますか？
   - A) DNS/IMDS/NTP の合計トラフィックと実際の DNS メトリクスを確認する
   - B) DNS 専用に予約された無制限の容量
   - C) AZ ごとの100 Gbpsの上限
   - D) CoreDNS が最も一般的な障害原因である証拠

<details>
<summary>回答を表示</summary>

**回答: A) DNS/IMDS/NTP の合計トラフィックと実際の DNS メトリクスを確認する**

**解説:**
共有される link-local の上限と、VPC DNS ENI の上限を確認します。Pod 密度だけから原因を推測せず、linklocal_allowance_exceeded と DNS latency を確認してください。

</details>

---

4. ALB target group の cross-zone balancing を無効化する際に確認すべきことは何ですか？
   - A) ALB の cross-zone 転送コストが必ず節約される
   - B) AZ ごとの容量を確認し、AZ にターゲットがない場合の503と、異常なターゲットへの failover を区別する
   - C) クラスターが自動的に再起動する
   - D) すべてのターゲットが healthy になる

<details>
<summary>回答を表示</summary>

**回答: B) AZ ごとの容量を確認し、AZ にターゲットがない場合の503と、異常なターゲットへの failover を区別する**

**解説:**
ターゲットの stickiness と Lambda ターゲットには制限があります。また、ターゲットが存在しない場合と異常な場合は異なります。ALB の cross-zone によるリージョン内のデータ転送に追加料金はありません。

</details>
