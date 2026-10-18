# Amazon Managed Blockchain

> **最終更新**: 2026年10月12日

## このドキュメントの対象

- Amazon Managed Blockchain（AMB）が[自己運用](./02-nodes-on-eks.md)のどの負担を引き受け、何ができないか
- マネージドと自己運用を選ぶ基準、および判断に含める必要がある変数
- AWS の台帳／ブロックチェーン関連ポートフォリオの変化が、アーキテクチャの判断に与える影響

## AMB の構成

AMB は単一のサービスではなく、それぞれ性質の異なるコンポーネントの集合です。

| 提供機能 | 内容 | 費用／運用の境界 |
|---|---|---|
| **Hyperledger Fabric** | 許可型ネットワーク、メンバー、peer のリソース | コンポーネント／ノード／ストレージとネットワークの料金。アプリケーション、channel、ID の責任は利用者に残る |
| **専用 Ethereum node** | 対応ネットワークでのマネージド node アクセス | 該当する場合、node／ストレージ／ネットワークの料金 |
| **Serverless AMB Access** | 専用 node を用意せずに使える、対応パブリックチェーンの RPC アクセス | リクエスト料金。対応チェーン、method、リージョンを確認する |
| **AMB Query** | インデックス化されたブロックチェーンデータ API | API／リクエスト料金と対応 query 範囲。任意の full-node RPC の代替ではない |

提供機能ごとに、プロビジョニング、API、課金、責任のモデルは異なります。まず必要なネットワークと method を選び、AMB をあらゆる用途に使えるノード単位の単一サービスとして扱わないでください。

::: warning 要確認
AMB の**対応 framework／chain、リージョンごとの提供状況、preview／GA の状態はコンポーネントごとに時間とともに変化します。** 確認済みの変更には、Ethereum Goerli testnet のサポート終了（2024年4月1日）、Polygon Mumbai testnet のサポート終了（2024年4月15日）、Polygon PoS mainnet が一時期 **Public Preview** として提供されたことが含まれます。

**設計を確定する前に、[AMB の公式ドキュメント](https://docs.aws.amazon.com/managed-blockchain/)とリージョンごとの提供状況を直接確認してください。** このドキュメントは特定チェーンの現行サポート状況を断定しません。
:::

## AMB が引き受けること

[自己運用に関するドキュメント](./02-nodes-on-eks.md)で扱う負担と比較すると、境界が明確になります。

| 自己運用時の負担 | AMB を使う場合 |
|---|---|
| StatefulSet、volume、storage class の設計 | **対応済み** |
| ディスク増加の監視と volume の拡張 | **対応済み** |
| 初期同期と snapshot の管理 | **対応済み** |
| P2P の公開と advertised address の設定 | **対応済み** |
| クライアントバージョンのアップグレード | **対応済み** |
| Hard fork への対応 | **対応済み**（マネージド node） |
| Fabric 証明書発行基盤 | **大部分に対応**（マネージド CA） |
| node の可用性と監視基盤 | **対応済み** |

マネージド提供者は、選択した offering が約束する node／サービスの保守を担います。対応ネットワーク、アップグレード通知、API の動作、利用者側に残るアプリケーション責任を確認してください。プロトコルの更新頻度だけでは、AWS サービスの保証内容は決まりません。

## AMB ではできないこと

これが判断の要点です。

| 項目 | 制約 |
|---|---|
| **クライアントの選択** | AMB が提供するクライアントとバージョンに限定される。[クライアント多様性](./02-nodes-on-eks.md)の戦略を直接制御できない |
| **細かなチューニング** | cache size、pruning mode、kernel parameter を調整できない |
| **対応チェーン** | AMB が対応するものに限られる。新しい chain や小規模な chain は一般に非対応 |
| **Archive mode** | 対応範囲が限られる場合がある |
| **Validator の運用** | マネージド node は一般に**照会とトランザクション送信**向け。staking validator の運用は別の問題 |
| **リージョンとネットワーク設定** | AMB が対応するリージョンと接続方法に限定される |
| **料金体系** | Offering によって異なる。プロビジョニング済み node／component の費用、または serverless の request／API 料金。等しい範囲と使用量で測定する |

**Validator の運用は特に重要な違いです。** AMB Access のパブリックチェーン node は、chain data の読み取りとトランザクション送信を目的とします。**PoS validator として参加して staking 報酬を得るには、別の要件**（鍵管理、署名の可用性、slashing リスク）があります。staking が目的なら、AMB では解決できません。

## 選択基準

| 状況 | 推奨 |
|---|---|
| chain data の**読み取りのみ** | **AMB Query**（node 自体が不要） |
| 照会と送信が必要で、運用要員が限られる | **AMB Access のマネージド node** |
| 特定のクライアントや調整が必要 | **自己運用** |
| **Validator／staking** | **自己運用**（または staking 専用サービス） |
| AMB 非対応の chain | **自己運用** |
| Consortium Fabric をすぐに始めたい | **AMB Access Fabric** |
| Fabric を細かく制御したい | **Operator を使った自己運用** |
| トラフィックが多く、コスト最適化が目的 | **自己運用**（比較が必要） |

### 判断の順序

**ステップ1: 本当に node が必要ですか。** データを照会するだけなら、AMB Query やサードパーティの RPC provider で十分な場合があります。node の運用は費用と負担が大きいため、**まず必要性を確認してください。**

**ステップ2: 制御が必要ですか。** クライアント選択、調整、archive、validator 参加のいずれかが必要なら、自己運用を選びます。

**ステップ3: コストはどうですか。** 選んだ offering に応じて、専用リソース、serverless request、Query API の費用を算出します。同じ範囲と可用性で EC2／EKS、ストレージ、転送、冗長化、要員のコストと比較してください。node 数だけを基準にした、普遍的な損益分岐点の実測値はありません。

**ステップ4: 組み合わせられますか。** 通常は可能で、実務上も有効なことが多くあります。たとえば一般的な query にマネージドを使い、特殊な用途には自己運用を使います。

## AWS の台帳／ブロックチェーン関連ポートフォリオの変化: 考慮すべき変数

このドキュメントで最も重要な点です。**技術面の比較だけで決めると、リスクを見落とします。**

### Amazon QLDB の終了

Amazon QLDB（Quantum Ledger Database）は、**暗号学的に検証できる改ざん不能なトランザクションログ**を提供するマネージド台帳データベースでした。2018年の re:Invent で発表され、2019年に GA となりました。

| 日付 | 出来事 |
|---|---|
| 2018年 | re:Invent で発表 |
| 2019年 | GA |
| 2024年7月 | サポート終了を発表 |
| **2025年7月31日** | **サービス終了** |

AWS が提示した移行先は **Amazon Aurora PostgreSQL** でした。ただし重要な点として、**Aurora PostgreSQL に移行すると、QLDB の中核価値だった暗号学的な検証可能性が失われます。** 拡張機能を使って台帳に似た機能を実装できますが、「改ざんがないことを数学的に証明する」性質は置き換えられません。

### これが意味すること

QLDB と AMB は別のサービスであり、**QLDB のサポート終了だけで AMB の終了が示されたわけではありません**。AMB 自体のサポート終了は別途発表されています（以下を参照）。それでも、アーキテクチャを決める上での教訓は当てはまります。

| 教訓 | 実務での適用 |
|---|---|
| **マネージドサービスも終了することがある** | 特に利用者の少ない特殊用途のサービス |
| **移行先が機能的に同等とは限らない** | 「代替がある」は「同じ機能を提供する」ことではない |
| **告知期間が短い場合がある** | 移行に必要な期間を事前に見積もる |
| **標準技術は移行しやすい** | オープンソースのプロトコルを基盤にすれば自己運用へ移行できる |

::: warning サポート終了の発表
**AWS は Amazon Managed Blockchain（AMB）のサポート終了を発表しています。** 2026年10月29日から新規顧客の受け入れを停止します。既存顧客は2027年9月29日まで利用でき、その日以降はアクセスできなくなります。

AMB Access Ethereum／Bitcoin／Polygon については、[AMB 移行ガイド](https://docs.aws.amazon.com/managed-blockchain/latest/ethereum-dev/migrating-node-rpc-workloads.html)で、AWS 上の自己管理 node（blueprint がある場合は AWS Blockchain Node Runners）またはサードパーティの RPC provider が案内されています。[AMB のサポート終了ページ](https://docs.aws.amazon.com/managed-blockchain/latest/hyperledger-fabric-dev/managed-blockchain-end-of-support.html)では、AMB Access Hyperledger Fabric の移行先として、別のマネージド Fabric network、Amazon EC2／Amazon EKS 上の自己管理 Fabric、または AWS database を挙げています。AMB Query の移行先はマネージドの blockchain data provider です（2026年10月12日確認）。

**現在、AMB に依存する設計には、期限を定めた移行計画が必要です。** 金融サービスのようにシステムの寿命が長い環境では、技術比較にも直接影響します。
:::

### サービス終了リスクを抑える設計

このリスクをなくすことはできず、**軽減することしかできません。**

| 軽減策 | 内容 |
|---|---|
| **標準プロトコルを使う** | Ethereum や Fabric のようなオープンプロトコルなら、マネージド offering が終了した場合に自己運用または別 provider へ移行できる |
| **抽象化レイヤー** | アプリケーションが AMB API に直接依存しないようにする。RPC interface を抽象化すれば backend を簡単に交換できる |
| **データの独立性** | chain data を自前の index／warehouse にも保持する。provider を変更しても履歴データが残る |
| **鍵の復旧と離脱** | KMS の private signing key は export できない。資金を入れる、または ID を登録する前に復旧／離脱を計画する。public key の download、import した鍵の backup、CloudHSM の backup／wrapping ルール、account／contract の rotation 方法を区別する |
| **移行時間を見積もる** | node の再同期やデータ移行にかかる時間を測定し、告知期間内に対応できるか判断する |

**「抽象化レイヤー」が最も効果的な対策です。** アプリケーションが標準 RPC interface（Ethereum JSON-RPC など）を使えば、backend を AMB、自己運用、サードパーティのいずれにもできます。AMB 固有 API に直接結合すると、この柔軟性を失います。

## AWS サービスとの連携

AMB の実質的な利点の1つは、AWS エコシステムとの連携です。

| 連携 | 用途 |
|---|---|
| **IAM** | chain node access に適用する IAM policy によるアクセス制御 |
| **CloudWatch** | metric と log |
| **CloudTrail** | 管理 API 呼び出しの監査 |
| **VPC endpoint／PrivateLink** | プライベート接続 |
| **KMS** | 鍵管理 |

**IAM 連携は特に有用です。** 自己運用 node の RPC endpoint には独自の認証方式（またはネットワーク層だけでの制御）が必要ですが、AMB は IAM で制御でき、社内の権限モデルに沿って一貫して管理できます。

プライベート接続には、[VPC Lattice の節](../service-mesh/vpc-lattice/README.md)の概念が当てはまる場合があります。ただし、**AMB と Lattice が直接連携するかは別途確認してください**（[VPC Lattice の制約](../service-mesh/vpc-lattice/06-constraints.md)で未確認事項としているものと同様です）。

## 自己運用との比較

| 項目 | AMB | 自己運用（EKS／EC2） |
|---|---|---|
| **初期構築時間** | 短い | 長い（同期時間を含む） |
| **運用要員** | 少ない | 多い |
| **Hard fork への対応** | AWS | **利用者** |
| **ディスク増加の管理** | AWS | **利用者** |
| **クライアントの選択** | 限定 | **自由** |
| **調整できる範囲** | 限定 | **すべて** |
| **Validator の運用** | 困難 | **可能** |
| **対応チェーン** | AMB のリスト | **制限なし** |
| **料金体系** | Offering により異なる。node／component のプロビジョニング料金、または serverless request／API 料金。同等の範囲と利用量で測定する |
| **IAM 連携** | **組み込み済み** | 自前で構築 |
| **サービスライフサイクルのリスク** | マネージド offering の提供／サポートが変わる可能性がある | オープンソース／client の保守、プロトコル、基盤への依存も残る |
| **可搬性** | 標準プロトコルなら可能 | - |

## まとめ

- AMB は、コンソーシアム network 向けの **AMB Access Fabric**、node 運用を委譲する **AMB Access のパブリック node**、node を使わずにデータを取得する **AMB Query** をまとめたもので、それぞれ異なる課題を解決します。
- マネージド保守で node 運用の負担は減らせますが、offering ごとの責任、アップグレード通知、アプリケーションの検証は引き続き必要です。
- できないことの中で最も重要な違いは **Validator の運用**です。マネージド node は query と送信向けであり、staking には別の要件があります。
- 判断の順序は **① node が本当に必要か → ② 制御が必要か → ③ コスト → ④ 組み合わせられるか** です。多くの場合、ステップ1で候補を絞れます。
- **QLDB は2025年7月31日に終了**し、移行先の Aurora PostgreSQL は**暗号学的な検証可能性を提供しません**。マネージドサービスの終了と、代替サービスが機能的に同等とは限らないことを示す事例です。
- 最も効果的な軽減策は、**標準プロトコルと抽象化レイヤー**です。AMB 固有 API への直接の結合を避ければ、backend を変更できます。
- **AWS は AMB のサポート終了を発表しています。** 2026年10月29日から新規顧客を受け入れず、2027年9月29日にアクセスを終了します。AMB に依存する設計には期限付きの移行計画が必要です。

次の「[金融サービスの視点](./04-financial-services.md)」では、規制、プライバシー、審査委員会の観点を扱います。

## 参考資料

- [Amazon Managed Blockchain のドキュメント](https://docs.aws.amazon.com/managed-blockchain/)
- [AMB Hyperledger Fabric Developer Guide](https://docs.aws.amazon.com/managed-blockchain/latest/hyperledger-fabric-dev/what-is-managed-blockchain.html)
- [Amazon Managed Blockchain FAQ](https://aws.amazon.com/managed-blockchain/faqs/)
- [AMB Query のドキュメント履歴](https://docs.aws.amazon.com/managed-blockchain/latest/ambq-dg/doc-history.html)
- [AMB Access Polygon のドキュメント履歴](https://docs.aws.amazon.com/managed-blockchain/latest/ambp-dg/doc-history.html)
- [EKS での blockchain node 運用](./02-nodes-on-eks.md): 自己運用時の負担

- [Offering ごとの AMB 料金](https://aws.amazon.com/managed-blockchain/pricing/)
- [AWS KMS 非対称鍵の仕様](https://docs.aws.amazon.com/kms/latest/developerguide/asymmetric-key-specs.html): public key にアクセスしても private key は export されない
