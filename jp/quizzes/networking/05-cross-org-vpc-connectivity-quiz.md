# クロス組織間 VPC 接続クイズ

報告された測定値と AWS プラットフォームの要件を区別してください。

## 1. TGW を所有するアカウントの Organization 外にあるアカウントと共有するには、何が必要ですか？

- A. 2 つの Organization を統合する
- B. 共有で外部プリンシパルを許可し、受信側アカウントで AWS RAM の招待を承諾する
- C. 両方の Organization の管理アカウントを VPN で接続する
- D. AWS Support チケットで承認を得る

<details>
<summary>回答を表示</summary>

B. 共有で外部アカウントを許可し、受信側が招待を承諾してから共有リソースを使用できます。`CreateResourceShare` では `allowExternalPrincipals` の既定値が `true` なので、文字列どおりの `--allow-external-principals` フラグが常に必要とは限りません。有効な設定と IAM および共有の制限を確認してください。

</details>

## 2. `AutoAcceptSharedAttachments` が無効の場合、共有 TGW への有効なクロスアカウント VPC attachment に何が必要ですか？

- A. 承諾は不要
- B. TGW の所有者が保留中の共有 attachment を承諾する
- C. Organization をまたぐ attachment は存在できない
- D. 常に 24 時間後に有効になる

<details>
<summary>回答を表示</summary>

B. 共有 attachment の自動承諾はデフォルトで無効です。AWS RAM 共有の承諾と VPC attachment の承諾は別の手順です。自動承諾を有効にすると、2 つ目の手順が変わります。TGW 所有者は TGW route table を管理し、受信側アカウントは自分の VPC route とセキュリティ設定を管理します。

</details>

## 3. レポートの TCP_RR 比較 M3−M2 から何が分かりますか？

- A. TGW の各 hop は常に同じ片道レイテンシを追加する
- B. 報告された経路の中央値の差は 0.619−0.048 = 0.571 ms である
- C. AWS が保証するレイテンシ SLA
- D. GPU トレーニングのスループット

<details>
<summary>回答を表示</summary>

B. これは報告された往復時間の中央値の差であり、特定コンポーネントだけの測定値でも、hop ごとの一定値でもありません。この測定では、2 つの TGW を経由する経路の TCP_RR 中央値は、1 つの TGW を経由する経路より低くなっています。より広い結論を出すには、生サンプル、不確実性、ワークロードの測定が必要です。このレビューではベンチマークを再現していません。

</details>

## 4. テストした Lattice HTTP service／VPC association 経路では、ターゲットの Security Group で何を確認すべきですか？

- A. すべての inbound と outbound port を開放する
- B. 実際のターゲット port とヘルスチェック port で、リージョンと IP family に合った managed prefix list を許可する
- C. Security Group を NACL に置き換える
- D. バックエンドにかかわらず TCP 443 だけを許可する

<details>
<summary>回答を表示</summary>

B. Lattice のトラフィックは managed prefix list 内のアドレスから到達することがあるため、クライアント VPC の CIDR だけを許可しても不十分です。過去の例にある `169.254.171.0/24` は、すべての経路に当てはまる完全なアドレス定義ではありません。文書化された prefix list と構成済みの port を使用してください。endpoint 経路と resource gateway 経路には、それぞれ別の制御があります。

</details>

## 5. CIDR が重複する VPC 間で、重複範囲どうしを直接ルーティングせずにサービスを公開できるパターンはどれですか？

- A. 直接 VPC peering
- B. 変更を加えない直接 TGW routing
- C. PrivateLink service access または VPC Lattice service access
- D. どのアーキテクチャでも対応できない

<details>
<summary>回答を表示</summary>

C. これらは、VPC 間の制約のない双方向 routing ではなく、サービスへのアクセスを提供します。CIDR が重複している VPC 同士を直接 VPC peering で接続することはできず、routing を使う設計では曖昧さのないアドレス計画が必要です。NAT やアドレスの再設計も選択肢なので、PrivateLink と Lattice だけが唯一の方式というわけではありません。

</details>

## 6. 直接 TGW-to-TGW peering の routing について、正しい説明はどれですか？

- A. peering によってすべての route が BGP 経由で自動伝播する
- B. peer route と必要な VPC route を明示的に構成する
- C. VPC route table だけを変更すればよい
- D. 承諾すると必要な route がすべて自動作成される

<details>
<summary>回答を表示</summary>

B. peering attachment では static route を使用し、自動化でそれらを管理できます。TGW は最長一致の prefix を優先し、同じ prefix では static route が伝播 route より優先されます。保留中の peering request は、accepter 側のリージョンでその attachment ID を使って承諾してください。`NotFound` だけでは、requester 側と accepter 側の ID が異なる必要があるとは判断できません。

</details>

[ガイドに戻る](../../networking/05-cross-org-vpc-connectivity.md)
