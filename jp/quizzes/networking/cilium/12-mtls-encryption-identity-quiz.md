# パート 12: mTLS、透過的な暗号化、ID のクイズ

> **レビュー基準**: Cilium 1.20.2 (安定版、2026-09-16); Cilium CLI 0.20.1; Hubble CLI 1.20.2。**[1.21 プレリリース]** と記した項目は v1.21.0-pre.3 に基づいており、GA 前に変更される可能性があります。
> **最終更新日**: 2026年10月15日

[ガイドに戻る](../../../networking/cilium/12-mtls-encryption-identity.md)

1. Cilium Mutual Authentication (SPIFFE/SPIRE、`authentication.mode: required`) は 1.20 と 1.21 でどのような状態ですか？
   - A) 1.20 で削除され、1.21 には存在しない
   - B) 1.20 でベータ、1.21 で安定版
   - C) 1.20 で非推奨、1.21 で削除
   - D) 1.21 で非推奨、1.22 で削除
<details>
<summary>回答を表示</summary>

**回答: C) 1.20 で非推奨、1.21 で削除**

1.20 のアップグレードノートでは非推奨とされ (ドキュメントページのタイトルは引き続き「Beta」)、ztunnel が案内されています。1.21 のアップグレードノートでは、非推奨化後に削除されたと記載されています。ポリシーの `authentication` フィールドは CRD との互換性のために維持されていますが、1.21 では使用されません。

</details>

2. 予約済み ID `reserved:world` の数値 ID は何ですか？
   - A) 1
   - B) 6
   - C) 8
   - D) 2
<details>
<summary>回答を表示</summary>

**回答: D) 2**

1 は `host`、2 は `world`、6 は `remote-node`、8 は `ingress` です。ID 9 と 10 は world を IPv4 と IPv6 のバリエーションに分けます。

</details>

3. Cilium の ztunnel mTLS にワークロードを参加させるにはどうしますか？
   - A) 各 Pod に `istio.io/dataplane-mode=ambient` をアノテーションする
   - B) namespace に `io.cilium/mtls-enabled=true` のラベルを付ける
   - C) CiliumNetworkPolicy に `authentication.mode: required` を追加する
   - D) 各 Pod に `io.cilium/mtls-enabled=true` のラベルを付ける
<details>
<summary>回答を表示</summary>

**回答: B) namespace に `io.cilium/mtls-enabled=true` のラベルを付ける**

参加設定は namespace レベルのみで、Pod レベルの参加設定はサポートされません。Istio ambient のラベルは Istio 用であり、`authentication.mode` は削除された Mutual Authentication の仕組みです。

</details>

4. ztunnel プロキシ間の HBONE トラフィックに使われ、参加ワークロードを対象とする L4 ポリシーで指定できる唯一のポートは何ですか？
   - A) 15008
   - B) 4250
   - C) 15006
   - D) 15001
<details>
<summary>回答を表示</summary>

**回答: A) 15008**

トラフィックは Pod の外に出る前に暗号化されるため、L4 ポリシーから内部ポートを見ることはできません。対象にできるのは HBONE ポート 15008 だけです。15001 と 15006 は Pod 内のアウトバウンド/平文インバウンドのリダイレクトポートで、4250 は削除された Mutual Authentication のハンドシェイク用ポートでした。

</details>

5. `encryption.ztunnel.ca.type` のデフォルト値は何ですか？
   - A) `spire`
   - B) `istiod`
   - C) `internal`
   - D) `cert-manager`
<details>
<summary>回答を表示</summary>

**回答: C) `internal`**

`internal` は Cilium 組み込みの CA を使います。1.20 で追加された `spire` は外部 SPIRE サーバーを使用し、Operator は参加 namespace のエントリを登録します。

</details>

6. 各ノードで Cilium の WireGuard トンネルエンドポイントが使う UDP ポートはどれですか？
   - A) 51820
   - B) 51871
   - C) 4789
   - D) 8472
<details>
<summary>回答を表示</summary>

**回答: B) 51871**

Cilium は WireGuard のデフォルト 51820 ではなく、51871 を使います。ノードのセキュリティグループで、パブリック CIDR ではなくノードのセキュリティグループを参照して、ノード間のこのポートを許可してください。4789 と 8472 は VXLAN ポートです。

</details>

7. 透過的な暗号化の strict mode オプションのうち、WireGuard のみで動作するのはどれですか？
   - A) `encryption.strictMode.ingress.enabled`
   - B) `encryption.strictMode.egress.allowRemoteNodeIdentities`
   - C) `encryption.strictMode.egress.enabled`
   - D) `encryption.strictMode.egress.cidr`
<details>
<summary>回答を表示</summary>

**回答: A) `encryption.strictMode.ingress.enabled`**

Ingress strict mode は、WireGuard トンネル経由で到着しなかったクラスター内の ingress を破棄するため、IPsec ではサポートされません。従来のフラットなフラグ (`encryption.strictMode.enabled` など) は、1.20 で `egress.*` 名に置き換えられました。

</details>

8. IPsec キー Secret で、トンネルごとの派生キーを必須にするものは何ですか？
   - A) `encryption.ipsec.interface` を設定する
   - B) キー ID 0 を使う
   - C) `encryption.nodeEncryption` を有効にする
   - D) キー ID の後ろに `+` を付ける。例: `3+ rfc4106(gcm(aes)) ...`
<details>
<summary>回答を表示</summary>

**回答: D) キー ID の後ろに `+` を付ける。例: `3+ rfc4106(gcm(aes)) ...`**

グローバルキーは 1.16 で非推奨になりました (GHSA-pwqm-x5x6-5586)。`encryption.ipsec.interface` は 1.20 で削除され、キー ID は 1〜15 です。

</details>

9. ID を kvstore から CRD に移行する Double Write は、どの順序で進めますか？
   - A) `doublewrite-readkvstore`、次に `doublewrite-readcrd`、次に `crd`
   - B) `crd`、次に `doublewrite-readcrd`、次に `kvstore`
   - C) `kvstore`、次に `crd`、次に `doublewrite-readcrd`
   - D) `doublewrite-readcrd`、次に `doublewrite-readkvstore`、次に `crd`
<details>
<summary>回答を表示</summary>

**回答: A) `doublewrite-readkvstore`、次に `doublewrite-readcrd`、次に `crd`**

全期間で両方のストアに書き込みます。読み取り元を kvstore から CRD に移し、最後に kvstore を削除します。各段階の前に `cilium_operator_doublewrite_*` メトリクスを監視し、`*_only_identities` の値がゼロに達するのを確認してください。

</details>

10. Cilium 1.20 で `spec` も `specs` も含まない CiliumNetworkPolicy を適用するとどうなりますか？
    - A) 受け入れられ、agent が警告をログに記録する
    - B) CEL 検証ルールによって admission で拒否される
    - C) 受け入れられ、すべて許可として扱われる
    - D) 受け入れられるが、いずれのエンドポイントも選択しない
<details>
<summary>回答を表示</summary>

**回答: B) CEL 検証ルールによって admission で拒否される**

CRD には、メッセージが「spec or specs must be provided」の `has(self.spec) || has(self.specs)` が含まれます。既存の空のポリシーは、更新されるまでは影響を受けません。

</details>
