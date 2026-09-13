# Istio比較クイズ

> **過去の報告**: Istio 1.30.2 / EKS 1.36.2。現在のサポート表ではありません
> **最終更新**: September 11, 2026

このクイズはサイドカーとambientの選択基準、特に報告されたEKS測定の限界について理解を確認します。監査では実験を再現していません。

## 選択問題（1-6）

### 問1: ambient waypointの503に関する証拠

集計されたロールアウト件数だけから、報告されたwaypoint 503の原因について何が結論付けられますか？

A. IP重複割り当てが証明された

B. 接続ライフサイクルの競合は仮説であり、原因確定にはプロキシ応答フラグとエンドポイント/接続の時系列が必要

C. NetworkPolicyが全失敗の原因と証明された

D. 件数はSTRICT mTLSが未対応と証明する

<details>
<summary>解答と解説</summary>

**正解: B**

**解説:**

HTTP状態コードの集計では根本原因は特定できません。Pod終了、エンドポイント伝播、アプリ/プロキシのドレイン、タイムアウト、接続プールすべてが寄与し得ます。元のIP再利用/ztunnel通知という説明には保持された診断時系列の裏付けがありません。仮説を証明済みの仕組みとして教えず、実際の上流ホスト、応答フラグ、Pod UID、接続イベントを調査してください。

**参考資料:**

- [サイドカーとAmbientモードの選択ガイド](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)
- [Ambientモード: Waypointプロキシ](../../../service-mesh/istio/advanced/01-ambient-mode.md)

</details>

---

### 問2: 報告されたEKS結果の解釈

未調整サンプルでは、サイドカーは60,000呼び出し中HTTP 503が324件、非HTTPエラー2件、ambient L4は60,000中0件と195件、ambient L7は59,913中1,528件と84件でした。裏付けられる解釈はどれですか？

A. Ambientは常により安定している

B. L7サンプルの観測HTTP 503割合が高く、L4のHTTP 503が0でも非HTTP失敗195件は残る

C. 全エラーカテゴリの根底に同じ原因があると証明された

D. Fortio SocketCountはwaypointの上流プールを直接測定する

<details>
<summary>解答と解説</summary>

**正解: B**

**解説:**

測定割合はサイドカー0.54%、L7約2.55%で、このサンプルでは比率約4.72です。製品固有の倍率ではありません。HTTP 503が0でも総失敗0ではありません。Fortioの非HTTPコード-1は、詳細なしでは特定のreset/EOF/timeout原因を示しません。SocketCountはクライアントソケットで、最多はL7（2,486）でありL4（1,652）ではありません。要求QPS×時間は正確な完了呼び出し数を保証せず、異なるロールアウト回数も因果比較を制限します。

**参考資料:**

- [サイドカーとAmbientモードの選択ガイド: 無停止ロールアウトの結果](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)

</details>

---

### 問3: NetworkPolicyとambient

報告されたVPC CNI実験では適用が確認され、8080だけを許すIngressルールが観測HBONE経路を遮断しました。次に何を確認すべきですか？

A. 全NetworkPolicyを削除する

B. 適切な範囲で必要なTCP 15008トンネル経路を許し、送信元、ID、内側ポートのポリシー境界を確認する

C. mTLSをPERMISSIVEに変える

D. CNIを再起動してポリシーが正しいと想定する

<details>
<summary>解答と解説</summary>

**正解: B**

**解説:**

報告された通信はTCP 15008許可後に回復しました。そのテスト経路の証拠であり、全CNIや既存ポリシーが同じ動作をする証明ではありません。外側トンネル許可は内側通信の完全な最小権限ポリシーではありません。送信元セレクター、waypoint経由、DNS/コントロールプレーン依存関係、実際の適用を検証します。サイドカーのアプリポートに関する観測も同様に範囲限定です。

**参考資料:**

- [サイドカーとAmbientモードの選択ガイド: NetworkPolicy](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)

</details>

---

### 問4: 非冪等APIと再試行

注文作成などの非冪等なコマンド経路で、メッシュ再試行をデフォルトで明示的に無効にすべき理由は何ですか？

A. 再試行は常にアプリよりCPUを消費する

B. 応答の失敗/喪失でサーバー側の結果が不明となり、再送がコミット済みコマンドを繰り返す場合がある

C. 再試行はSTRICT mTLSと互換性がない

D. AmbientにL7再試行機能がない

<details>
<summary>解答と解説</summary>

**正解: B**

**解説:**

タイムアウト、リセット、エラー応答はコマンドが無効果だった証明とは限りません。サーバーが適切な永続的冪等性/トランザクション意味を提供しなければ、結果不明な書き込みの再送で処理が重複し得ます。特定のwaypoint競合を証明しなくてもこのリスクは存在します。旧T2報告の重複0件では、安全性も信頼できる頻度推定も成立しません。クライアントは無制限、件数は記載時間/レートと矛盾し、観測者エラーが隠れる可能性がありました。制限を付けた改訂観測者も業務トランザクション台帳ではありません。安定したコマンドIDと応答喪失ケースを完全な観測で測定してください。

**参考資料:**

- [サイドカーとAmbientモードの選択ガイド: 緩和策としての再試行のリスク](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)

</details>

---

### 問5: データプレーン動作の公平な比較

失敗と再試行で隠れた失敗を分けるため、必要な実験の出発点はどれですか？

A. 最終GET成功数だけを比較する

B. サイドカー再試行は残しambientだけ無効にする

C. 両モードの書き込みルートをattempts: 0にし、生のHTTP/非HTTPエラー、再試行カウンター、上流配信、最終結果を収集する

D. 平均CPUが最も低いモードを選ぶ

<details>
<summary>解答と解説</summary>

**正解: C**

**解説:**

サイドカーとwaypoint EnvoyはL7再試行ができますが、ztunnelはHTTP 503を解釈したりHTTP要求を再送したりできません。両方で同様に書き込み再試行を無効にし、upstream_rq_retry、実配信、安定コマンドID、クライアント側集計を記録します。負荷、版、リソース、ロールアウトへの露出も揃え、実験を繰り返します。より公平に観測を分けられますが、1回で製品固有の安定性は証明されません。

**参考資料:**

- [サイドカーとAmbientモードの選択ガイド: 生の失敗測定](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)
- [再試行とタイムアウト](../../../service-mesh/istio/traffic-management/05-retry-timeout.md)

</details>

---

### 問6: Ciliumの認証と暗号化

Ciliumの文書化された帯域外相互認証で、authenticationをrequiredにすると何を意味しますか？

A. 全ペイロードが自動的にワークロードTLSを使う

B. 帯域外ピアIDハンドシェイクとペイロード暗号化は別で、暗号化は別途設定・検証が必要

C. 実装と成熟度がIstio PeerAuthentication STRICTと同一

D. 認可ポリシーが不要になる

<details>
<summary>解答と解説</summary>

**正解: B**

**解説:**

リリース済みCilium 1.20.1文書はこの機能をBetaとし、アプリデータ経路と別の帯域外ハンドシェイクを説明します。認証ポリシーだけではアプリペイロードは暗号化されません。プラットフォームと対象通信制限も含め、対応WireGuard/IPsec暗号化を別に評価します。Cilium 1.20.1には、名前空間参加、TCP専用、ポリシー/プラットフォーム制限を持つ別のztunnel暗号化ベータもあります。この帯域外認証ポリシー設定では有効になりません。

**参考資料:**

- [Ciliumサービスメッシュのセキュリティ](../../../service-mesh/cilium-service-mesh/03-security.md)

</details>

---

## 採点

- 6問中の正答数を数えてください。
- 6/6: 実測証拠を使い、サイドカー、ambient、Ciliumの選択と再試行リスクを説明できます。
- 4-5/6: 生の失敗測定か、認証と暗号化の違いを復習してください。
- 0-3/6: [サイドカーとAmbientモードの選択ガイド](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)を最初から読み直してください。

## 学習資料

- [サイドカーとAmbientモードの選択ガイド](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)
- [Ambientモード](../../../service-mesh/istio/advanced/01-ambient-mode.md)
- [mTLS](../../../service-mesh/istio/security/01-mtls.md)
- [Ciliumサービスメッシュのセキュリティ](../../../service-mesh/cilium-service-mesh/03-security.md)

## 公式の根拠

- [Istio ambient L7機能の状態](https://github.com/istio/istio.io/blob/release-1.30/content/en/docs/ambient/usage/l7-features/index.md)
- [Cilium 1.20.1相互認証](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/servicemesh/mutual-authentication/mutual-authentication.rst)
