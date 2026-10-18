# ブロックチェーンの基礎

> **最終更新**: 2026年9月12日

## このドキュメントの対象

- なぜ一部の台帳は検証を複製するのか、full node、light client、permissioned model の違い
- Consensus、Merkle tree、P2P、finality の役割と、各要素が基盤運用にもたらす制約
- ブロックチェーン node を通常の stateful service と別に扱う理由

## 問題の定義: 信頼できる仲介者なしで合意する

ブロックチェーンを理解するとき、出発点は技術ではなく**制約**です。

一般的な分散システムとして Kubernetes の etcd cluster を考えてください。etcd も node 間で consensus を取りますが、1つの前提があります。**参加 node は同じ組織が運用し、故障することはあっても嘘はつかない。** Node の停止や network partition（crash fault）には対応しますが、node が意図的に異なる値を主張する場合は対象外です。

ブロックチェーンは異なる前提に基づきます。

| 項目 | etcd（Raft） | ブロックチェーン |
|---|---|---|
| **参加者** | 同じ組織の既知の member | 相互に未知で、入れ替わる参加者 |
| **想定する障害** | Crash fault（停止、partition） | **Byzantine fault**（虚偽、共謀、攻撃） |
| **参加資格** | Operator が指定 | Public chain では**誰でも** |
| **取り消し可能か** | Operator が介入できる | Protocol が許す範囲のみ |

多くの public chain では、**full node** が transaction と consensus rule をそれぞれ独立して検証します。Light client、pruned／snapshot-sync node、permissioned design では、検証や data 配布の方法が異なります。Permissioned な member 制御だけで consensus algorithm が Byzantine fault tolerant になるわけではありません。

ここからブロックチェーンの基本的な性質が導かれます。

> **ブロックチェーンは throughput のために設計されたシステムではありません。** 検証可能性と改ざん耐性のために、**意図的に冗長性を受け入れる**システムです。

これを理解すると、以下の運用特性が自然に説明できます。

## Block と Chain: なぜ「Chain」なのか

Transaction をまとめたものが **block** であり、各 block には**直前の block の hash**が含まれます。

```text
Block N-1               Block N                 Block N+1
┌──────────────┐       ┌──────────────┐        ┌──────────────┐
│ prev_hash:.. │       │ prev_hash: ──┼────────│ prev_hash: ──┤
│ merkle_root  │   ┌───│ merkle_root  │        │ merkle_root  │
│ transactions │───┘   │ transactions │        │ transactions │
└──────────────┘       └──────────────┘        └──────────────┘
      hash ────────────────┘
```

これにより**改ざんが後続へ伝播**します。Block N の transaction を変更すると block N の hash が変わり、block N+1 の `prev_hash` が一致しなくなり、その後の block もすべて無効になります。

PoW chain で履歴を書き換えるには、受け入れられた十分な work を再構築する必要があります。ほかの chain では異なる finality と governance の前提を使います。Hash link は改ざんの検知に役立ちますが、それだけで finality を確立したり、あらゆる blockchain を経済的に変更不能にしたりするものではありません。

### Merkle tree: なぜ必要なのか

Block 内の transaction をどう要約するかが問題です。すべてを単純に連結して hash にすることもできますが、その場合「**この transaction が block に含まれるか」の確認に block 全体が必要**です。

Merkle tree は、transaction を pair ごとに上位へ hash していく binary tree です。

```text
                merkle_root
               /            \
         H(AB)                H(CD)
        /     \              /     \
     H(A)    H(B)         H(C)    H(D)
      |        |            |        |
     tx A     tx B         tx C     tx D
```

ここから得られる性質が **Merkle proof** です。Transaction C がこの block に含まれることを証明するには、block 全体ではなく **`H(D)` と `H(AB)`** があれば足ります。受信側は `H(C)` → `H(CD)` → `merkle_root` を計算し、比較します。

Proof size は transaction 数 N に対して **log N** で増えます。100万 transaction の block でも proof は約20 hash です。

**実用上の意義**: これにより light client が実現できます。Chain 全体を保持せずに、特定 transaction の包含を検証できます。既存システムに blockchain を統合するときの「full node を動かすか、light verification で十分か」という選択の基礎になります。

## Consensus: 次の Block を誰が書くのか

Consensus algorithm は2つのことを決めます。**誰が block を提案するか**、そして**競合時にどちらを正規 chain とするか**です。

### 主な方式

| 方式 | Proposer の選択 | 実際に必要となるコスト | 例 |
|---|---|---|---|
| **PoW**（Proof of Work） | 計算問題を最初に解いた node | **電力と hardware** | Bitcoin |
| **PoS**（Proof of Stake） | Stake に比例する確率で選択 | **Stake した資本 + 違反時の slashing** | Ethereum |
| **BFT 系** | 定義した Byzantine fault 上限のもとで投票 | Membership／validator と quorum の前提 | Tendermint、Fabric 3.x SmartBFT |
| **CFT permissioned ordering** | 既知 replica が crash-fault-tolerant consensus を使う | 任意の Byzantine ordering behavior には耐えない | Fabric Raft |

### なぜコストが必要か

この問いは consensus を理解する鍵です。**Block 提案が無料なら、無制限の候補を作って network を麻痺させられます。** 匿名参加が許される環境では、identity だけでこの問題を防げません（Sybil attack: 1つの主体が多数の identity を作る）。

PoW は**計算**をコストにし、PoS は**資本と slashing のリスク**をコストにします。BFT 系は最初に**参加者を制限**することで問題を回避するため、consortium chain に適しています。

### ここで Public と Private が分かれる

| 種類 | 参加 | Consensus | Throughput | 主な用途 |
|---|---|---|---|---|
| **Public**（permissionless） | 誰でも | PoW／PoS | 低い | Public asset、相互運用 |
| **Private／consortium**（permissioned） | 承認された member | BFT／Raft | 比較的高い | 企業間台帳、規制環境 |

Permissioned design では既知の member と明示的な governance を使い、実際の threat model に応じて CFT／BFT を選べます。金融 application は異なる制御のもとで permissioned／public network を使う場合があります。Membership も consensus の名称も、それだけで規制準拠を証明しません。

## Finality: 運用上、最も重要な概念

**Finality は protocol の security 前提のもとで settlement が確定した状態を表します。** あらゆる攻撃、governance による介入、application-level の補償 transaction に対する無条件の保証ではありません。確率的な確信、経済的 finality、決定論的 consensus 保証を区別してください。

### 確率的 finality と絶対的 finality

| 種類 | 意味 | 例 |
|---|---|---|
| **確率的** | Block が積み重なるほど巻き戻し確率が指数関数的に減る。**厳密にゼロにはならない** | Bitcoin PoW |
| **経済的** | Finalized checkpoint は stake／slashing の前提のもとで保護される。巻き戻しが物理的に不可能なわけではない | Ethereum PoS |
| **即時** | Consensus round の終了時に確定 | BFT 系 |

### なぜ運用上の問題になるのか

**Node が返す data は、まだ final ではない可能性があります。**

Blockchain node に「この transaction の結果を教えて」と問い合わせると、node は**認識している最新 chain に基づいて**回答します。その最新 block が後から再編成（reorg）されると、回答も変わります。

実際に起きる運用上の問題:

| Pattern | 結果 |
|---|---|
| 最新 block をもとに deposit を確認して処理する | すでに withdrawal を送った後に reorg で deposit が消える |
| Health check が「node が生きている」ことだけ確認する | Sync が遅れた node が**古い data を返す** |
| Load balancer が複数 node に分散する | Node ごとに chain height が異なり、同じ問いに**異なる回答**が返る |

**したがって application 設計には「N confirmation の後に処理する」という規則（confirmation depth）が必要で、その値は chain の finality 特性によって決まります。** これは基盤だけでは解決できず、application との契約になります。

基盤側でできること:

- **Health check に sync 状態を含める**: readiness を単なる「稼働中」ではなく「chain head から N block 以内」と定義する。
- **Node 間の chain-height 差を監視する**: 差が大きくなったら load balancing から外す。
- **Reorg 発生を metric として公開**し、application が対応できるようにする。

## P2P Networking: 通常の Service と異なる理由

Blockchain node は client-server ではなく**peer-to-peer**で通信します。そのため Kubernetes の network model との間に摩擦が生じます。

### Gossip protocol

新しい block や transaction が現れると、**近隣 peer に伝播し、peer はさらに次の peer へ伝播**させます。こうして全 node に情報が届きます。

特性:

- 中央 broker がないため単一障害点がない。
- **同じ data が複数経路から重複して届く**ため、重複分の帯域を消費する。
- 伝播に時間がかかるため、各 node が認識する「最新」が異なる（前述の finality の問題につながる）。

### Kubernetes 環境で生じる摩擦

| Blockchain P2P が必要とするもの | Kubernetes の既定 |
|---|---|
| **安定した peer identity**（node ID、address） | Restart 時に Pod IP が変わる |
| **Inbound connection の受け入れ**（他 peer から接続される） | 既定では Pod は外部から直接到達できない |
| **Peer list の永続化** | Pod 交換で state が失われる |
| **固定 port の広告** | Service の port mapping |

そのため、Blockchain node には安定した名前と順序が必要で、既定では **StatefulSet + headless Service** を使います。Inbound P2P の受け入れには追加の公開設計が必要です。詳細は[Running Blockchain Nodes on EKS](./02-nodes-on-eks.md)を参照してください。

## State と Storage: 再構築が難しい理由

Blockchain node は2種類の data を保持します。

| Data | 性質 | Size |
|---|---|---|
| **Block history** | Append-only log。過去は不変 | 継続的に増加 |
| **Current state** | Balance、contract storage。Block の再生で導出可能 | 増えるが history より小さい |

**重要な性質: State は history から再構築できますが、その処理に長い時間がかかります。**

Genesis からすべての block を再生／検証する full sync にかかる時間は chain の経過年数に比例します。そのため別の sync method があります。

| Method | 処理内容 | Trade-off |
|---|---|---|
| **full sync** | Genesis からすべてを検証して再生 | 確信度が最も高いが、**最も遅い** |
| **snap／fast sync** | 受け入れられた state root に照らして検証する proof 付きで state を取得。History の確認は client／mode による | 高速。Consensus／checkpoint と実装への trust 前提を明示する。任意の peer を無条件に信頼する方式ではない |
| **checkpoint sync** | 信頼できる checkpoint から開始 | 最速だが checkpoint の提供元を信頼する |
| **Snapshot restore** | Operator が保持する data directory を復元 | 高速だが snapshot の新しさと一貫性を管理する必要がある |

**運用上の結論**: Pod を交換するときに state を失ってはいけません。失うと、node が service を提供できないまま長時間 sync することになります。そのため blockchain node に persistent volume は**任意ではなく必須**です。

### Archive node: 別途判断が必要

任意の過去時点における state を query できる node が archive node です。すべての中間 state を保持するため、通常の node より**はるかに多くの storage** が必要です。

**ここでは設計判断が必要です。** まず本当に archive 機能が必要か確認してください。多くの application が必要とするのは直近の state だけです。履歴 query が必要なら、indexing service や data warehouse で処理するほうが費用対効果に優れます。

## Key Management: 失うと取り戻せない

Blockchain では、**Identity と権限は private key にあります。** これは既存システムと決定的に異なる点です。

| 既存システム | Blockchain |
|---|---|
| Password を忘れたら reset する | **Key を失うと asset／権限は永久に失われる** |
| 管理者が侵害された account を freeze できる | Protocol が許さない限り、取り消す主体は存在しない |
| Audit log で事後追跡できる | Final になった署名済み transaction は巻き戻せない |

**そのため、backup 戦略の性質が異なります。** Chain data は network から再取得できるため、backup の価値は低いです。一方で key は**必ず backup が必要**であり、**backup 自体が漏えいリスク**になります。

これが blockchain 基盤で HSM、AWS KMS／CloudHSM が重要な理由です。特に Validator は、**署名のために key を online にする必要がある一方、漏えいさせてはならない**という相反する要件があります。この問題は[金融サービスの視点](./04-financial-services.md)で扱います。

## 運用特性: ここまでの内容から導かれること

これらの概念から導かれる運用特性をまとめます。

| Blockchain の設計 | 導かれる運用特性 | Kubernetes での意味 |
|---|---|---|
| Full node による検証の複製 | Replica を増やしても base chain の write capacity 自体は増えない | 集約 RPC／read capacity と可用性は増やせる |
| State がローカルに蓄積する | **Pod 交換の費用が非常に高い** | StatefulSet + persistent volume が必須。Node affinity も検討 |
| Chain sync が遅れる | **「稼働中」と「応答可能」は異なる** | Readiness に sync 状態を含める |
| Finality が即時ではない | **最新 data は final data とは限らない** | Confirmation depth を application との契約にする |
| P2P gossip | **Inbound 接続と安定した identity が必要** | Headless Service と追加の公開設計 |
| Hard fork は定められた時点に rule が有効化される | 有効化前に互換 binary に upgrade | Canary と rolling upgrade で fleet を事前準備 |
| Key が権限を持つ | **Key の喪失は永続的な喪失** | KMS／HSM を使い、key と data の backup を分ける |
| 冗長検証が目的 | **CPU と IOPS を継続的に消費する** | Burst 前提の resource 設定には不向き |

**この表がこの節の要点です。** ドキュメント2の各具体的な推奨事項は、ここから導かれます。

## Hard Fork: Kubernetes の運用モデルと最も衝突するもの

後方互換性のない protocol 変更を **hard fork** と呼びます。Network 全体が指定 block height／時刻に新しい rule に切り替わり、**切り替えない node は別の chain に残ります。**

Kubernetes の一般的な考え方と衝突する点:

| Kubernetes での慣習 | Hard fork の場合 |
|---|---|
| Rolling update で徐々に移行 | 期限までに必要な全 node が新 rule に対応すれば有効化前に可能 |
| 一部を Canary にする | 有効化前に fork 対応 binary をテストし、適切な testnet／mainnet 段階で挙動を比較 |
| 問題があれば rollback | Rollback すると、その node は旧 chain に残る |
| Upgrade 時期は運用チームが決める | **日程は外部で定められる** |

**実務上の推奨**: Hard fork を通常の deployment ではなく、**期限付きの migration**として扱ってください。Client の release note を購読し、fork 日より十分前に upgrade し、まず testnet で検証します。

Ethereum は2025年に Pectra と Fusaka を実施し、より頻繁な upgrade を進めています。**年2回の固定日程を前提にせず、公開された有効化日時と client release note** を使って保守を計画してください。

## まとめ

- 採用する consensus と trust model を比較してください。**etcd／Raft は crash fault tolerant** です。Blockchain の一部は BFT を使い、permissioned Fabric は CFT Raft または SmartBFT を使えます。Blockchain という名称だけでは Byzantine fault tolerance を意味しません。
- 多くの full-node design は検証を複製します。Light-client／permissioned model は異なり、RPC／read capacity は base-chain write と別に scale できます。
- `prev_hash` の連鎖は改ざんを後続へ伝播させ、**Merkle tree** は log-N の包含 proof を可能にします（light client の基礎）。
- Consensus に費用が必要なのは **Sybil 対策**のためです。参加者を制限する consortium はこの問題を避け、分散性との引き換えに高い throughput と finality を持つ BFT を使えます。
- **Finality は運用上、最も重要な概念です。** 最新 data は final data ではありません。Readiness に sync 状態を含め、confirmation depth を application との契約にしてください。
- State は再生できますが、**再生に長い時間がかかる**ため persistent volume が必須です。
- Hard fork は外部で調整された時点に有効になります。互換 client を事前に準備し、有効化後の rollback は別途評価してください。

次の[Running Blockchain Nodes on EKS](./02-nodes-on-eks.md)では、こうした特性を実際の設定に落とし込みます。

## 参考資料

- [Ethereum Developer Documentation](https://ethereum.org/developers/docs/): consensus、node、client
- [Ethereum: Proof of Stake](https://ethereum.org/developers/docs/consensus-mechanisms/pos/)
- [Hyperledger Fabric Documentation](https://hyperledger-fabric.readthedocs.io/): permissioned chain の構造
- [Bitcoin Developer Guide](https://developer.bitcoin.org/devguide/): PoW と Merkle tree
- [Cluster Architecture: etcd と Raft](../core/01-cluster-architecture.md): crash-fault consensus との比較

- [Fabric ordering service](https://hyperledger-fabric.readthedocs.io/en/latest/orderer/ordering_service.html): CFT Raft と SmartBFT の違い
