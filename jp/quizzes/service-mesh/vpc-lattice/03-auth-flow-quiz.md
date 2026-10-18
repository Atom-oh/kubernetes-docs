# IAM認証フロークイズ

このクイズでは、Lattice IAM Authの4段階のフロー、SigV4署名での注意点、403エラーの診断について理解度を確認します。

## 多肢選択問題

1. VPC LatticeデータプレーンへのリクエストをSigV4で署名する際、どのサービス名を使いますか？
   - A) `vpc-lattice`
   - B) `vpc-lattice-svcs`
   - C) `lattice`
   - D) `execute-api`

<details>

<summary>回答を表示</summary>

**回答: B) `vpc-lattice-svcs`**

**解説:**
`vpc-lattice-svcs`はデータプレーンリクエストの署名に使うサービス名です。サービス、リスナーなどを作成するLatticeコントロールプレーンAPIのサービス名`vpc-lattice`と混同しやすいので注意してください。サービス名は署名キーの導出に使われます（シークレットキー → 日付 → リージョン → サービス名 → 終端文字列という4段階のHMAC-SHA256演算）。誤った名前を使うと署名を検証できません。この名前はサービスのDNS名とも一貫しており、`...vpc-lattice-svcs.<region>.on.aws`という形式になります。
</details>

2. Lattice IAM Authで403が発生する最も一般的な原因は何ですか？
   - A) Latticeサービスの認証ポリシーにプリンシパルが含まれていない
   - B) 呼び出し元IAM Roleのアイデンティティベースポリシーに`vpc-lattice-svcs:Invoke`がない
   - C) ノードのSecurity GroupでLatticeのプレフィックスリストが許可されていない
   - D) Target Groupのヘルスチェックが失敗している

<details>

<summary>回答を表示</summary>

**回答: B) 呼び出し元IAM Roleのアイデンティティベースポリシーに`vpc-lattice-svcs:Invoke`がない**

**解説:**
「サービスの認証ポリシーがこのRoleを許可しているから完了」と考えがちですが、呼び出し元RoleにもInvoke権限が必要です。リソースポリシーだけでは通過できません。実際のエラーメッセージは`because no identity-based policy allows the vpc-lattice-svcs:Invoke action`で終わるため、403が発生したらまずこの節を確認してください。なお、Cの場合は403ではなく、接続失敗またはタイムアウトになります。
</details>

3. カスタムドメインを導入した直後に403が発生し始めた場合、最初に何を確認すべきですか？
   - A) Target Groupのプロトコル設定
   - B) `Host`ヘッダー。SigV4では常に署名対象となるため、署名時に使ったHostと実際のリクエストのHostが一致する必要がある
   - C) Latticeのクォータを超過したかどうか
   - D) VPCのDNS解決設定

<details>

<summary>回答を表示</summary>

**回答: B) `Host`ヘッダー。SigV4では常に署名対象となるため、署名時に使ったHostと実際のリクエストのHostが一致する必要がある**

**解説:**
SigV4では`Host`ヘッダーが常に署名に含まれます。カスタムドメインを関連付けると、クライアントはそのドメインにリクエストを送信するため、その値を使って署名する必要があります。署名ロジックで引き続きLattice生成ドメインを使うと、署名が一致しません。この問題は移行開始時ではなく、カスタムドメインを関連付けた時点で発生するため、見落としやすい点です。カスタムドメインを導入するときは、SNIの制御、署名対象のHost値、証明書管理をまとめて決めてください。
</details>

4. 「特定の1台のノード上のPodだけで断続的に403が発生する」場合、最も可能性が高い原因は何ですか？
   - A) そのノードのSecurity Group設定ミス
   - B) そのノードの時刻同期。`x-amz-date`は署名対象であり、SigV4の許容範囲は約5分
   - C) そのノードでGateway API Controllerが動作していない
   - D) そのノードのkubeletバージョンが古すぎる

<details>

<summary>回答を表示</summary>

**回答: B) そのノードの時刻同期。`x-amz-date`は署名対象であり、SigV4の許容範囲は約5分**

**解説:**
AWSの一般的なSigV4ガイダンスでは、ほとんどのリクエストはタイムスタンプから5分以内に到着する必要があります。実際のサービスエラーとUTCの時刻を確認してください。これをLattice固有の保証として別途測定されたもののように扱わないでください。
</details>

5. 署名からLatticeの検証までの間に、何を確認する必要がありますか？
   - A) プロキシが複数あるとレイテンシーが増える
   - B) 正規化された署名対象フィールドが変更されると検証に失敗する可能性がある。Latticeは`UNSIGNED-PAYLOAD`を必須とするため、本文の完全性にはTLSやアプリケーション側の制御も必要
   - C) プロキシは認証情報をキャッシュできない
   - D) 1つのIAM Roleを関連付けられるプロキシは1つだけ

<details>

<summary>回答を表示</summary>

**回答: B) 正規化された署名対象フィールドが変更されると検証に失敗する可能性がある。Latticeは`UNSIGNED-PAYLOAD`を必須とするため、本文の完全性にはTLSやアプリケーション側の制御も必要**

**解説:**
署名対象のHost、パス、クエリ値はリクエストと一致する必要があります。正規化時にソートされるため、クエリの並び順が異なっても必ずしも変更とは限りません。Latticeはペイロード署名に対応しないため、`x-amz-content-sha256: UNSIGNED-PAYLOAD`ヘッダーを指定します。
</details>

6. クラスター内のトラフィックに認証ポリシーが適用されないことがあるのはなぜですか？
   - A) 認証ポリシーはIPv6トラフィックに対応していない
   - B) クライアントがKubernetes ServiceのDNSを直接呼び出すとLatticeを迂回し、認証ポリシーが評価されない
   - C) 認証ポリシーはクロスアカウント呼び出しにしか適用されない
   - D) Gateway API Controllerがまだポリシーを調整していない

<details>

<summary>回答を表示</summary>

**回答: B) クライアントがKubernetes ServiceのDNSを直接呼び出すとLatticeを迂回し、認証ポリシーが評価されない**

**解説:**
AWS Gateway API Controllerのドキュメントにはこの点が明記されています。`IAMAuthPolicy`が認可を行うのは、Gateways、HTTPRoutes、GRPCRoutesを通るトラフィックだけです。`http://svc.ns.svc.cluster.local`宛てに送るとLatticeを迂回するため、ポリシーは評価されません。移行中に両方の経路が共存すると、認可が適用される経路と適用されない経路が同時に存在するため、NetworkPolicyなどの補完的な制御が必要です。もう1つよくある原因は、`authType`が`AWS_IAM`ではなく`NONE`になっていることです。
</details>

7. AS-IS（App Mesh + SPIRE mTLS）からTO-BE（Lattice IAM Auth）へ移行すると、認証の「範囲」と「方向性」はどのように変わりますか？
   - A) 接続単位の双方向認証 → リクエスト単位の双方向認証
   - B) 接続単位の双方向相互認証 → リクエスト単位の一方向認証（クライアントの証明）とTLSサーバー証明書
   - C) リクエスト単位の一方向認証 → 接続単位の双方向認証
   - D) 範囲も方向性も変わらない

<details>

<summary>回答を表示</summary>

**回答: B) 接続単位の双方向相互認証 → リクエスト単位の一方向認証（クライアントの証明）とTLSサーバー証明書**

**解説:**
mTLSは接続確立時に両方のピアをSVIDで認証します。Lattice IAM Authはリクエストごとに呼び出し元のSigV4署名を検証し、パス/メソッド/ヘッダーに対するポリシー条件を適用できます。SigV4は正規化された署名対象フィールドを保護します。Latticeは`UNSIGNED-PAYLOAD`を必須とし、ペイロード署名には対応しません。リクエスト署名があらゆる接続乗っ取りを防ぐと主張せず、本文はTLSで保護し、認証情報の窃取、リクエストの鮮度、リプレイを別途評価してください。HTTPSリスナーの設計では、サーバー認証にピアのSPIFFE IDではなくTLSサーバー証明書を使います。
</details>
