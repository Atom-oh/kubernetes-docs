# EKS上でブロックチェーンノードを実行する

> **対応バージョン**: Kubernetes 1.33以降（Amazon EKS）、Hyperledger Fabric 2.5／3.x
> **最終更新日**: 2026年9月13日

## この文書で扱うこと

- [基礎編](./01-fundamentals.md)で確認した運用特性を、StatefulSet、storage、P2P公開などの実際のKubernetes設定へ反映する方法
- sync状態をhealth checkに反映する方法と、一般的なhealth checkでは不十分な理由
- Ethereum nodeとHyperledger Fabricの運用上の違い、およびhard forkの予定を管理する方法

## 最初に考えること: これはEKSで動かすべきか

設定を検討する前に、この問いを考えてください。**ブロックチェーンnodeは、Kubernetesが得意とすることの一部にうまく適合しません。**

| Kubernetesが得意なこと | ブロックチェーンnodeの場合 |
|---|---|
| 高速なscheduleとreschedule | state再構築のコストが高いため、rescheduleが負担になる |
| throughput向上のための水平scale | replicaを増やすとRPC／read容量と可用性を高められるが、base chainのwrite／consensus容量が自動的に増えるわけではない |
| 宣言的なrolling update | hard forkでは同時に切り替える |
| Podをnode間で移動する | local diskに依存する |

それでもEKSを選ぶ理由はあります。

| 理由 | 内容 |
|---|---|
| **運用の標準化** | すでにすべてをEKSで運用しているなら、別stackを増やさずに済む |
| **複数chain／環境** | mainnet、testnet、複数protocolを同じ方法で管理できる |
| **周辺componentとの統合** | indexer、API gateway、monitoringがすでにcluster内にある |
| **Fabricの公式方針** | Hyperledger Fabricには成熟したKubernetes operator ecosystemがある |

**反対に、nodeが1～3台だけで、ほかにcluster workloadがない場合は、通常のEC2の方が適しています**。この場合、EKSの抽象化は利点なしに複雑さを増やします。validatorを1つ動かすだけならEKSは必要ありません。

**判断基準は、ブロックチェーンnodeの周囲にほかのworkloadがあるかどうかです**。indexer、API、monitoringがcluster内にあるならnodeも一緒に運用するのが妥当です。nodeだけならEC2の方が簡単です。

## 基本構成: StatefulSetとheadless Service

### Deploymentを使わない理由

| 要件 | Deployment | StatefulSet |
|---|---|---|
| 安定した名前（P2P identity） | ✗ ランダムなsuffix | ✓ `node-0`、`node-1` |
| Podごとに固定されたvolume | ✗ 共有またはランダム | ✓ `volumeClaimTemplates`によるPod別PVC |
| 安定したDNS | ✗ | ✓ headless Serviceによる`node-0.svc...` |
| 順序どおりの起動／停止 | ✗ | ✓ |

[基礎編](./01-fundamentals.md)で説明した「安定したpeer identity」と「Podごとのstate」の要件に、StatefulSetはそのまま対応します。

### 不完全なテスト専用の構成（deploy可能なmanifestではない）
この断片にはStatefulSetの必須selector／template label、image／argument、headless Service、StorageClass、Merge後のEL／CL Engine API／JWT設定がありません。このまま適用してはいけません。**実際の資金やvalidator署名keyがない**隔離テスト環境で、必要なresourceを完成させて検証してください。JSON-RPCとEngine APIはprivateかつ認証済みにします。P2Pの到達性によってRPC endpointや署名endpointを公開してはいけません。

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: eth-node
spec:
  serviceName: eth-node          # headless Service name
  replicas: 2
  template:
    spec:
      terminationGracePeriodSeconds: 300   # graceful shutdown needs time
      containers:
        - name: execution
          # ... execution client
          ports:
            - { name: p2p-tcp, containerPort: 30303, protocol: TCP }
            - { name: p2p-udp, containerPort: 30303, protocol: UDP }
            - { name: rpc,     containerPort: 8545 }
          volumeMounts:
            - { name: data, mountPath: /data }
  volumeClaimTemplates:
    - metadata: { name: data }
      spec:
        accessModes: [ReadWriteOnce]
        storageClassName: gp3-high-iops
        resources: { requests: { storage: 2Ti } }
```

一般的なworkloadとは、主に3点が異なります。

**① `terminationGracePeriodSeconds`を長くします。停止時にブロックチェーンclientはメモリ内のstateをdiskへflushする必要があります**。強制終了すると**databaseが破損し、再syncが必要になる**ことがあります。既定の30秒では通常足りません。

**② P2P portはTCPとUDPの両方が必要です**。多くのprotocolはpeer discovery（UDP）と実際の接続（TCP）を分けています。片方だけ開けると、peerを見つけられないか接続できません。

**③ volumeの容量が大きくなります**。詳細は後述のstorage節で説明します。

## Storage: 最も重要な設計判断

### bottleneckは何か

ブロックチェーンnodeのdiskは、**ランダムread／writeが非常に多い**という特徴があります。state trie（Merkle Patricia Trieなど）をたどって更新するたびに、離れたkeyへアクセスするためです。

そのため**容量より先にIOPSがbottleneckになります**。空き容量があってもIOPSが足りなければsyncが遅れ、遅れているnodeはserviceを提供できません。

| 要件 | 理由 |
|---|---|
| **高いIOPS** | ランダムアクセスが多い |
| **低遅延** | state lookupはblock処理経路上にある |
| **継続的なthroughput** | burstではなく連続した負荷 |

### EBS volumeを選ぶ

| volume type | 適性 |
|---|---|
| **gp3** | 既定の選択肢。**容量と独立してIOPSとthroughputを設定できる**ことが主な利点 |
| **io2／io2 Block Express** | より高いIOPSと安定した遅延が必要な場合 |
| **gp2** | 非推奨。IOPSが容量に比例し、個別に調整できない |
| **instance store（NVMe）** | 最速だが、**instance停止時に失われる**。再syncを許容できる場合だけ使う |

**gp3の独立設定が重要な理由:** gp2は容量単位でIOPSが固定されていたため、IOPSを増やすには不要な容量も購入する必要がありました。gp3は容量とIOPSを別々に設定できるため、**実際の必要量に合わせられます**。具体的な差は[EBS gp2とgp3のbenchmark](../storage/01-ebs-gp2-gp3-benchmark.md)を参照してください。

**instance storeには明確なtrade-offがあります**。性能は最良ですが、stateが消失することがあります。snapshotからの復元手順があり、再syncにかかる時間を許容でき、複数nodeを動かして1台の再sync中もserviceが停止しない場合に選びます。

### 容量計画: 増加への備えが要点

chain dataは**単調に増加します**。そのため容量計画の性質も変わります。

| 項目 | 影響 |
|---|---|
| 継続的な増加 | **volume拡張計画が必須**で、いずれ必要になる |
| protocolの稼働状況によって増加率が変わる | 余裕を持たせ、alarmを設定する |
| pruningの選択肢 | clientは古いdataを破棄するmodeを提供する。archiveが不要なら利用する |

**EBS volumeはonline拡張に対応します**（後からfilesystemも拡張します）。そのため一般的には、`allowVolumeExpansion: true`を設定したStorageClassと、disk使用率のalarmを用意します。

### 公式hardware指針: EIP-7870

[EIP-7870](https://eips.ethereum.org/EIPS/eip-7870)と[node実行ガイド](https://ethereum.org/developers/docs/nodes-and-clients/run-a-node/)は、**初期検討の推奨値**として使います。特定のEKS instanceやEBS volumeで満たせる保証ではありません。使用client、fork、pruning、実測した増加量を確認してください。

| 項目 | 最小 | **推奨（EIP-7870、full node）** |
|---|---|---|
| **CPU** | 2 core以上 | 4 core以上（**validation時は8 core以上**） |
| **RAM** | 16 GB（32 GBを推奨） | 32 GB（**validation時は64 GB**） |
| **Disk** | **2 TB NVMe SSD** | **4 TB NVMe SSD**（DRAM-lessとQLC driveは**非推奨**） |
| **帯域** | 25 Mbit/s以上 | 下り50 Mbit/s／上り15 Mbit/s以上（**validation時は上り25 Mbit/s以上**） |

数値を読む際に重要な点が3つあります。

**① bottleneckはdiskです**。ethereum.orgも明示しています。「hardwareのbottleneckは主にdisk容量です。Ethereum blockchainのsyncは非常にI/O負荷が高い処理です。」前述のIOPSが先に問題となる理由です。

**② EIP-7870はhardware指針であり、特定のEBS構成が要件を満たす証明ではありません**。EC2／EBSの遅延、instance帯域、volume IOPS／throughputはlocal NVMeと異なります。選択したclientとstorage profileでsyncと定常時の処理を測定してください。

**③ 最小2 TBには期限があります**。ethereum.orgは2 TBを「2027年までに超える可能性が高い」と記載しています。**だからこそ、増加分を容量計画に含める必要があります。**

::: warning 要確認
上記の数値は**full node**向けです。**archive nodeにはさらに大きなstorageが必要で、実使用量はclient、pruning設定、forkによって異なります。**

特にFusakaのPeerDASはblobの扱いを変更したため、clientのrelease noteで最新要件を確認し、PoCで**自分の環境の増加率を測定してください。**
:::

### Snapshot戦略

[基礎編](./01-fundamentals.md)で説明したように、**chain dataはnetworkから再取得できますが、時間がかかります**。そのためbackupの目的は「dataを保存すること」ではなく、「**復旧時間を短縮すること**」です。

| 方法 | 特徴 |
|---|---|
| **EBS snapshot** | volume全体を取得する。復元時の初期化遅延（lazy loading）を考慮する |
| **client snapshot export** | clientが提供するexport機能。一貫性の保証範囲が明示される |
| **再sync** | backupは取らず、最初からやり直す（時間がかかる） |

**注意:** 稼働中のnode volumeを直接snapshotすると、**書き込み途中のdatabaseが取得される**ことがあります。一貫性を保つには、clientを停止するか、clientが提供する一貫性確保の仕組みを使います。

## Health check: 一般的な方法では不十分な理由

syncを考慮しないhealth checkでは、古いnodeにapplication trafficが送られる可能性があります。これは運用ミスの頻度を示す測定結果ではなく、検証が必要な設計上のriskです。

### 問題

一般的なhealth checkは「processが応答するか」を確認します。ブロックチェーンnodeでは、**それだけでは不十分で危険です。**

syncが遅れているnodeは、次の状態になります。

- RPC portが開き応答するため、livenessはpassする。
- しかし、**古いchain stateを基に回答し**、誤ったdataを返す。
- Serviceがtrafficを送るため、applicationは誤ったbalanceやstateを受け取る。

### 適切な分け方

| probe | 確認すること |
|---|---|
| **startup** | 初期syncの実行中か。時間がかかるため、`failureThreshold`を**十分大きく**する |
| **liveness** | processが生存し応答するか。ここではsyncを確認**しない**（遅れたnodeをkillすると追いつけなくなる） |
| **readiness** | chain headからN block以内か、つまりserviceを提供できるか |

**livenessとreadinessを分けることが重要です。**

- syncをlivenessに含める → 遅れたnodeが再起動され、さらに遅れる → 無限loopになる。
- readinessに含めない → 遅れたnodeにtrafficが届き、誤った応答を返す。

### 実装の方向性

sync状態はclientのRPCで確認します。protocolとclientによってmethodが異なるため、通常はwrapper scriptまたはsidecarを使って判定します。

```yaml
# Conceptual form: the actual judgment logic differs per client
readinessProbe:
  exec:
    command: ["/bin/sh", "-c", "/scripts/check-sync.sh"]   # block delta vs head
  periodSeconds: 15
  failureThreshold: 3

livenessProbe:
  httpGet: { path: /, port: rpc }     # responsiveness only
  periodSeconds: 30
  failureThreshold: 5

startupProbe:
  exec:
    command: ["/bin/sh", "-c", "/scripts/check-alive.sh"]
  periodSeconds: 30
  failureThreshold: 240               # allow a long initial sync
```

**閾値（N block）はapplication要件に基づいて設定してください。**[基礎編](./01-fundamentals.md)で説明したconfirmation depthと合わせて決定します。

## P2P公開: inbound接続を受け入れる

### inboundが重要な理由

sync自体はoutboundのみでも動作します。しかしinboundを受け付けると、次の利点があります。

- peer数が増え、**伝播が速く安定する。**
- networkに貢献できる（public chainでは相互に利益がある）。

validatorでは特に重要です。blockの伝播遅延はperformance（reward）に直接影響します。

### 方法とtrade-off

| 方法 | 特徴 |
|---|---|
| **`hostNetwork: true`** | 最も簡単。PodがnodeのIPとportを直接使う。**nodeごとに1つだけ**という制約があり、security reviewが必要 |
| **`hostPort`** | 特定portだけをnodeへ割り当てる。nodeごとにport競合を管理する必要がある |
| **NodePort Service** | Kubernetes標準。port範囲の制約、node IPを広告する際の問題がある |
| **PodごとのLoadBalancer（NLB）** | 安定したaddress。**PodごとにLB費用**が発生 |
| **inboundを省略** | outboundのみ。設定は簡単だがpeer品質が下がる |

### よくある落とし穴: 広告するaddress

P2P protocolは自分のaddressをほかのpeerへ**広告します**。container内から見えるaddress（Pod IP）と外部から到達できるaddress（nodeのpublic IPやLB address）が異なると、**ほかのpeerが接続できません。**

多くのclientには広告addressを指定するoption（`--nat extip:<addr>`など）があります。**これを指定せずにinboundを開けてもpeerは増えません。**「portを開けたのに何も起きない」となる典型的な原因です。

Podごとに異なるaddressを広告する必要があるため、各PodがStatefulSet ordinalまたはdownward APIを使って自分のaddressを検出する初期化logicが必要です。

## Resources: burstではなく継続的な負荷

ブロックチェーンnodeは**CPUとIOPSを継続的に使います**。blockが到着し続け、検証とstate更新も続くためです。

| 項目 | 推奨 |
|---|---|
| **CPU limit** | **慎重に設定する**。throttlingはblock処理遅延につながり、validatorではperformanceとrewardが結び付く。[Kernel Tuning](../kernel/03-eks-node-tuning.md)のthrottling診断を参照 |
| **Memory** | state cacheに大量のmemoryを使うclientがある。OOMはDB破損につながるため、**limitに十分な余裕を持たせる** |
| **request = limit** | Guaranteed QoSはevictionの優先度を下げる |
| **専用node** | taint／tolerationを使い他のworkloadと分離してnoisy neighborを防ぐ |
| **file descriptor** | peer connectionごとにsocketを1つ使う。limit引き上げを検討する（[Kernel Tuning](../kernel/03-eks-node-tuning.md)） |

**CPU limitの判断が最も重要です。**[kernelの文書](../kernel/01-container-primitives.md)で説明したように、CPU limitは使用可能な時間枠を制限します。期間内にquotaを使い切ると処理が止まります。block処理がその時間枠に当たると遅延が発生し、validatorは機会を逃すことがあります。

専用nodeにするとtenant間の競合は減りますが、kubelet、CNI／CSI、observability、OS serviceは引き続きnodeを共有します。applicationのCPU limitを設定しない場合でも、resource予約と余裕を保ってください。継続的な負荷をかけ、遅延、sync、node healthを検証します。

## Ethereum node: 2つのclientで構成

EthereumがPoSへ移行した後、nodeは**2つのprocessで構成されます。**

| client | 役割 | 例 |
|---|---|---|
| **Execution client（EL）** | transaction実行、state管理、EVM | Geth、Nethermind、Besu、Erigon、Reth |
| **Consensus client（CL）** | PoS consensus、block提案とattestation | Prysm、Lighthouse、Teku、Nimbus、Lodestar |

両者は**Engine API**で通信し、JWT secretを共有します。

### 配置方法の判断

| 方法 | 利点と欠点 |
|---|---|
| **1つのPodに2つのcontainer** | `localhost`で簡単に通信し、同時にschedule／restartされる。resourceをまとめて要求する |
| **別々のStatefulSet** | 個別にscale／upgradeできる。Engine API接続の管理が必要 |

**既定では1つのPodにまとめます**。2つのclientは1対1で動作し、Engine APIの遅延がperformanceに影響するため、Pod内の`localhost`通信が自然です。

**clientの多様性**も重要です。1つのclientのbugがnetwork全体に影響しないよう、communityは複数clientへ分散することを推奨しています。複数nodeを運用するなら、**異なるclientの組み合わせ**を使うことが防御策になります。

### 運用に影響する最近のprotocol変更

以下は**日付が確定したprotocol event**であり、今後の更新周期を保証するものではありません。upgradeを計画する前に、[roadmap](https://ethereum.org/roadmap/)、activation発表、使用clientのrelease noteを確認してください。

| 日付 | upgrade | 運用上の意味 |
|---|---|---|
| **2025年5月7日** | **Pectra** mainnet | EIP-7251により、対象validatorの最大effective balanceが2,048 ETHに引き上げられた。consolidationで変わるのはvalidator recordであり、process／VM数とは限らない |
| **2025年12月3日** | **Fusaka** mainnet（epoch 411392） | 主な変更は**PeerDAS**（Peer Data Availability Sampling）。blob dataを全体ではなくsamplingで検証し、blob throughputを拡張する |

validatorのidentity／keyは**独立したprocessやVMではありません**。1つのvalidator clientが共有beacon-node stack上で複数keyを管理できます。EIP-7251によるconsolidationでvalidator recordやkey管理作業が減っても、infrastructureや費用が同じ割合で削減されるとは限りません。実際のclient構成を測定し、key移行中のslashing protectionを維持してください。

**PeerDASはstorageと帯域の計画に影響します**。blobの扱いが変わるとnodeが保持・転送するdata量も変わるため、既存の容量基準を見直してください。

## Hyperledger Fabric: permissioned chainの運用

Fabricは性質が異なります。**既知の参加者によるconsortium chain**であり、consensusと運用の特性も[基礎編](./01-fundamentals.md)で説明したとおり異なります。

### component

| component | 役割 | Kubernetes上の配置 |
|---|---|---|
| **Peer** | ledgerを保持し、chaincodeを実行し、transactionを検証する | StatefulSet + persistent volume |
| **Orderer** | 設定したconsensus（CFT Raft、またはFabric 3.xのSmartBFT）に従ってtransactionを順序付ける | StatefulSet + persistent storage。peerの検証により有効なstate更新が決まる |
| **CA**（Fabric CA） | member certificateを発行する | Deployment + persistent volume |
| **Chaincode** | smart contract | external builderまたは別Pod |

### 運用上のポイント

**① ordererのpersistent volumeは必須です**。Raft logが失われるとconsensus stateが壊れます。更新時にPodはrestartするため、**persistent volumeなしではdataが失われます。**

**② certificate管理が中心作業です**。FabricはMSP（Membership Service Provider）を通じてorganizationとidentityを管理し、すべての通信にTLSを使います。管理が必要なのは次の項目です。

- MSP署名certificateとkey
- TLS certificate（peer、orderer、CAそれぞれ）
- **有効期限の管理**: certificateの期限切れは実際の停止を引き起こす。

certificate期限切れは重要な停止riskですが、ここでは発生頻度のdatasetを提示していません。MSPとTLS認証情報を監視し、更新手順をリハーサルしてください。互換性のあるoperator／client versionも検証します。

**③ operatorを使います**。FabricにはKubernetes operator ecosystemがあります。

| operator | 特徴 |
|---|---|
| [hyperledger-labs/fabric-operator](https://github.com/hyperledger-labs/fabric-operator) | CNCF operator pattern。CA、Peer、Orderer、ConsoleをCRとして宣言する |
| [bevel-operator-fabric](https://github.com/hyperledger-bevel/bevel-operator-fabric) | Hyperledger Bevel project提供。Fabric 2.3～3.xに対応 |

operatorを使うと、繰り返し必要な設定を宣言的resourceの適用に置き換えられます。Fabricの設定は複雑で手作業では誤りやすいため、**YAMLを手作業で組み立てるよりoperatorから始めることを推奨します。**

### EthereumとFabricの比較

| 項目 | Ethereum node | Hyperledger Fabric |
|---|---|---|
| **参加方式** | Permissionless | Permissioned（MSP） |
| **Consensus** | PoS | 設定したorderer mode: Raft（CFT）またはSmartBFT（Fabric 3.x） |
| **finality** | protocol上の前提に基づくcheckpoint方式 | consensusの前提のもとで順序付けはfinalとなる。ただしpeerはtransactionを検証し、順序付け済みtransactionが無効な場合もある |
| **主な運用負担** | sync、disk増加、hard fork | **certificate期限切れ**、channelとpolicy管理 |
| **P2P公開** | inboundを推奨 | organization間接続（既知のendpoint） |
| **storage増加** | 大きく、単調増加 | 比較的小さい（transaction量による） |
| **upgrade** | 外部schedule（hard fork） | consortiumの合意で決まる |

**運用上の最大の違い**は、Ethereumでは**外部が定めるschedule**（hard fork）に従う必要があり、Fabricでは**consortiumがscheduleを決める**ことです。その代わりFabricでは参加member間の合意手続きが必要です。

## Hard forkのschedule管理

[基礎編](./01-fundamentals.md)ではhard forkを「期限のある移行」と表現しました。実務上は次の手順で進めます。

| 手順 | 内容 |
|---|---|
| **1. 情報を購読する** | protocol公式blog、client release note、operator communityを確認する |
| **2. 日程を登録する** | fork block／時刻をチームのcalendarへ登録し、**余裕を持った目標日を設定する** |
| **3. testnetで検証する** | testnetのforkはmainnetより先なので、そこで検証する |
| **4. imageを準備する** | forkに対応するversionでimageをbuildし、scanする |
| **5. 順次upgradeする** | fork開始**前に完了**する。nodeが複数なら1台ずつ行う |
| **6. fork時に監視する** | chain height、peer数、forkが認識されたかを確認する |
| **7. fork後に確認する** | すべてのnodeが同じchain上にいることを確認する |

互換性のないclientを実行するnodeは、canonical chainへの追従を停止したり、activation後に分岐したりする場合があります。通常の伝播／sync遅延を考慮し、信頼できる独立した複数の情報源で**同じblock heightとfinality状態**を比較します。関連のない最新headが即座に一致するはずだと比べてはいけません。

## 監視

| 分類 | metric | 理由 |
|---|---|---|
| **Sync** | chain headとの差分block数 | serviceを提供できるかを示す中核 |
| **Sync** | block処理遅延 | 遅れ始めていることを早く検出できる |
| **P2P** | peer数 | 急減はnetworkまたは設定の問題を示す |
| **P2P** | inbound／outbound比 | inboundが0なら公開設定の失敗を示す |
| **Storage** | disk使用率と増加率 | 拡張時期を予測する |
| **Storage** | IOPS、queue depth、遅延 | bottleneckを特定する |
| **Consensus** | reorgの発生 | applicationへ通知する必要がある |
| **Validator** | 参加率、missしたduty | rewardに直接結び付く |
| **Fabric** | **certificate有効期限までの残り時間** | 停止を防ぐ |
| **Resources** | CPU throttling（`nr_throttled`） | [kernelの文書](../kernel/01-container-primitives.md)を参照 |

「**chain headとの差分block数」は最も重要な単一metricです**。増加し始めたら原因（IOPS、CPU、peer、network）を特定します。閾値を超えたnodeはreadinessから外すべきです。

## まとめ

- **まずEKSで実行するか決めてください**。nodeの周囲に別のworkloadがあるかが判断基準です。node単独ならEC2の方が簡単です。
- **StatefulSet + headless Service + persistent volume**が基本構成です。`terminationGracePeriodSeconds`は長くする必要があります（強制終了するとDB破損のriskがあります）。
- storageでは**容量より先にIOPSがbottleneckになります**。gp3で容量とIOPSを独立設定できることが主な利点で、volume拡張計画が必須です。
- processのlivenessとsyncのreadinessを分けて、両方を検証してください。この章では障害頻度の順位付けをしていません。
- inbound P2Pを開く場合、**広告addressを忘れるとpeerが接続してきません。**
- resourceはburstではなく継続的に使われます。**nodeを専有し、CPU limitを慎重に決めてください。**
- EthereumはEL／CL clientを使います。validator identity／keyの数とprocess／VMの数は別です。集約しただけでは費用削減を証明できません。
- Fabricの主な運用負担は**certificateの有効期限**です。operatorから始め、更新を自動化してください。
- hard fork後は、ほかのnodeやexplorerと**block hashを比較して**同じchain上にいることを確認してください。

次は[Amazon Managed Blockchain](./03-managed-blockchain.md)で、managed serviceがこの負担をどこまで引き受けるかを確認します。

## 参考資料

- [Ethereum: nodeの実行](https://ethereum.org/developers/docs/nodes-and-clients/run-a-node/)
- [EIP-7870: hardwareと帯域の推奨値](https://eips.ethereum.org/EIPS/eip-7870): 公式hardware指針
- [Ethereum roadmap](https://ethereum.org/roadmap/) / [Pectra](https://ethereum.org/roadmap/pectra/) / [Fusaka](https://ethereum.org/roadmap/fusaka/)
- [Pectra mainnet発表（Ethereum Foundation）](https://blog.ethereum.org/2025/04/23/pectra-mainnet)
- [Fusaka mainnet発表（Ethereum Foundation）](https://blog.ethereum.org/2025/11/06/fusaka-mainnet-announcement)
- [Hyperledger Fabric: production networkの展開](https://hyperledger-fabric.readthedocs.io/en/latest/deployment_guide_overview.html)
- [hyperledger-labs/fabric-operator](https://github.com/hyperledger-labs/fabric-operator) / [bevel-operator-fabric](https://github.com/hyperledger-bevel/bevel-operator-fabric)
- [EBS gp2とgp3のbenchmark](../storage/01-ebs-gp2-gp3-benchmark.md) / [EKS node kernel tuning](../kernel/03-eks-node-tuning.md)
