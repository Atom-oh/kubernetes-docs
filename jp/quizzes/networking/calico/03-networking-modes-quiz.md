# Calico ネットワーキングモード クイズ

> **関連ドキュメント**: [Calico ネットワーキングモード](../../../networking/calico/03-networking-modes.md)
> **最終更新**: February 22, 2026

## クイズ

1. IPIP カプセル化によって追加されるオーバーヘッドは何バイトですか？
   - A) 8 bytes
   - B) 20 bytes
   - C) 50 bytes
   - D) 100 bytes

<details>
<summary>回答を表示</summary>

**回答: B) 20 bytes**

**解説:**
IPIP (IP-in-IP) カプセル化は、各パケットに 20 bytes のオーバーヘッドを追加します。これは元のパケットを包む追加の IP ヘッダーのサイズです。50 bytes のオーバーヘッドを追加する VXLAN よりも効率的であるため、カプセル化が必要な場合は IPIP の方がパフォーマンスに優れています。

</details>

2. VXLAN カプセル化によって追加されるオーバーヘッドは何バイトですか？
   - A) 20 bytes
   - B) 30 bytes
   - C) 50 bytes
   - D) 64 bytes

<details>
<summary>回答を表示</summary>

**回答: C) 50 bytes**

**解説:**
VXLAN カプセル化は、各パケットに約 50 bytes のオーバーヘッドを追加します。これには、外側の Ethernet ヘッダー (14 bytes)、外側の IP ヘッダー (20 bytes)、UDP ヘッダー (8 bytes)、および VXLAN ヘッダー (8 bytes) が含まれます。IPIP の 20 bytes よりも大きいものの、VXLAN はさまざまなネットワーク環境との互換性に優れています。

</details>

3. Calico の CrossSubnet モードは何を行いますか？
   - A) 常にカプセル化を使用する
   - B) カプセル化を決して使用しない
   - C) サブネット間トラフィックに対してのみカプセル化を使用する
   - D) 同一サブネット内のトラフィックに対してのみカプセル化を使用する

<details>
<summary>回答を表示</summary>

**回答: C) サブネット間トラフィックに対してのみカプセル化を使用する**

**解説:**
CrossSubnet モードは、トラフィックがサブネット境界を越える場合にのみカプセル化 (IPIP または VXLAN) を適用する最適化です。同じサブネット内のノード間のトラフィックには、カプセル化を行わない直接ルーティングが使用されます。これにより、可能な場合は直接ルーティングを使用し、必要な場合にのみカプセル化を使用するという両方の利点が得られます。

</details>

4. Direct（カプセル化なし）ルーティングモードの要件は何ですか？
   - A) 特殊なハードウェア NIC
   - B) 基盤となるネットワークが pod CIDR トラフィックをルーティングできる必要がある
   - C) Kernel バージョン 5.0 以降
   - D) eBPF モードを有効にする必要がある

<details>
<summary>回答を表示</summary>

**回答: B) 基盤となるネットワークが pod CIDR トラフィックをルーティングできる必要がある**

**解説:**
Direct ルーティングモードでは、基盤となるネットワークインフラストラクチャがノード間の pod CIDR トラフィックをルーティングできる必要があります。通常は、BGP を使用して pod ルートをネットワークインフラストラクチャにアドバタイズするか、静的ルートを設定することを意味します。これがない場合、他のノード上の pod IP 宛てのパケットはネットワークによって破棄されます。

</details>

5. 一般的に、IPIP と VXLAN のどちらのネットワーキングモードがより優れたパフォーマンスを提供しますか？
   - A) VXLAN は常に高速である
   - B) IPIP はオーバーヘッドが少ないため一般的に高速である
   - C) 両者のパフォーマンスは同一である
   - D) パフォーマンスは Kubernetes のバージョンに依存する

<details>
<summary>回答を表示</summary>

**回答: B) IPIP はオーバーヘッドが少ないため一般的に高速である**

**解説:**
IPIP は VXLAN よりもカプセル化のオーバーヘッドが少ないため（20 bytes 対 50 bytes）、一般的に優れたパフォーマンスを提供します。オーバーヘッドが少ないほど、実際のペイロードデータに使用できる領域が増え、カプセル化/カプセル化解除に必要な処理も少なくなります。ただし、VXLAN はより幅広い互換性と優れたハードウェアオフロードのサポートを備えています。

</details>

6. IPPool の ipipMode に有効なオプションは何ですか？
   - A) On, Off
   - B) True, False
   - C) Always, CrossSubnet, Never
   - D) Enabled, Disabled, Auto

<details>
<summary>回答を表示</summary>

**回答: C) Always, CrossSubnet, Never**

**解説:**
IPPool の ipipMode フィールドは、`Always`（常に IPIP カプセル化を使用）、`CrossSubnet`（サブネット間トラフィックに対してのみ IPIP を使用）、`Never`（IPIP を無効化）の 3 つの値を受け付けます。VXLAN カプセル化の動作を設定する vxlanMode にも、これらと同じオプションを使用できます。

</details>

7. IPPool の natOutgoing 設定は何を制御しますか？
   - A) pods が受信 NAT トラフィックを受信できるかどうか
   - B) クラスターを離れる pod トラフィックがマスカレードされるかどうか
   - C) pods 間で NAT が適用されるかどうか
   - D) ノードが外部 Service に対して NAT を実行するかどうか

<details>
<summary>回答を表示</summary>

**回答: B) クラスターを離れる pod トラフィックがマスカレードされるかどうか**

**解説:**
`natOutgoing` 設定は、この IP pool 内の pods からのトラフィックがクラスターを離れる際にマスカレード (SNAT) されるかどうかを制御します。true に設定すると、送信トラフィックの送信元 IP がノードの IP に変更されるため、pod IP がクラスター外でルーティング不可能な場合でも、pods は外部リソースと通信できます。

</details>

8. VXLAN がデフォルトで使用する UDP ポートは何ですか？
   - A) 4789
   - B) 8472
   - C) 8080
   - D) 5473

<details>
<summary>回答を表示</summary>

**回答: A) 4789**

**解説:**
VXLAN は、IANA によって規定されているとおり、デフォルトで UDP ポート 4789 を使用します。これは異なる VXLAN 実装間で使用される標準ポートです。一部の古い実装（初期の Flannel バージョンなど）ではポート 8472 が使用されていましたが、Calico は標準ポート 4789 に従います。

</details>

9. Azure 環境で IPIP より VXLAN が推奨される可能性があるのはなぜですか？
   - A) Azure が VXLAN ハードウェアアクセラレーションを提供している
   - B) IPIP (IP protocol 4) は Azure で十分にサポートされていない
   - C) VXLAN が Azure ポリシーで必須とされている
   - D) Azure が VXLAN を自動的に設定する

<details>
<summary>回答を表示</summary>

**回答: B) IPIP (IP protocol 4) は Azure で十分にサポートされていない**

**解説:**
Azure では IP protocol 4 がブロックされるか、Azure のネットワーク内で問題が発生する可能性があるため、IPIP カプセル化のサポートは限定的です。UDP ベースの VXLAN は、Azure 環境でより確実に動作します。これは、Azure Kubernetes Service (AKS) または Azure VM に Calico をデプロイする場合の一般的な推奨事項です。

</details>

10. 標準の 1500 byte ネットワーク MTU で VXLAN カプセル化を使用する場合、MTU はどのように最適化すべきですか？
    - A) pod MTU を 1500 に設定する
    - B) pod MTU を 1450（1500 - 50 bytes のオーバーヘッド）に設定する
    - C) MTU の調整は自動的に行われる
    - D) pod MTU を 1400 に設定する

<details>
<summary>回答を表示</summary>

**回答: B) pod MTU を 1450（1500 - 50 bytes のオーバーヘッド）に設定する**

**解説:**
1500 byte のネットワーク MTU で VXLAN を使用する場合、フラグメンテーションを回避するため、pod MTU は約 1450 bytes（1500 - 50 bytes の VXLAN オーバーヘッド）に設定する必要があります。IPIP の場合、pod MTU は 1480 bytes（1500 - 20 bytes のオーバーヘッド）になります。適切な MTU 設定により、パケットフラグメンテーションによるパフォーマンス上の問題を防止できます。

</details>

11. IPIP モードを有効にすると、ノード上にはどのインターフェイスが作成されますか？
    - A) vxlan.calico
    - B) tunl0
    - C) cali0
    - D) ipip0

<details>
<summary>回答を表示</summary>

**回答: B) tunl0**

**解説:**
IPIP モードを有効にすると、Calico は各ノード上に `tunl0` トンネルインターフェイスを作成します。このインターフェイスは、ノード間トラフィックの IPIP カプセル化に使用されます。tunl0 インターフェイスは、パケットが IPIP トンネルに入出する際のカプセル化とカプセル化解除を処理します。

</details>

12. 稼働中のクラスターで IPIP から VXLAN モードに移行するためのベストプラクティスは何ですか？
    - A) IPPool 設定を直接変更する
    - B) VXLAN を使用する新しい IPPool を作成し、ワークロードを移行してから古い pool を削除する
    - C) すべてのノードを同時に再起動する
    - D) 移行はサポートされていないため、クラスターを再構築する

<details>
<summary>回答を表示</summary>

**回答: B) VXLAN を使用する新しい IPPool を作成し、ワークロードを移行してから古い pool を削除する**

**解説:**
カプセル化モード間を移行する際の推奨アプローチは、目的の設定で新しい IPPool を作成し、ワークロードを新しい pool を使用するように段階的に移行して（pods を再作成するか node selector を使用して）、移行が完了したら古い pool を削除することです。このアプローチにより、中断を最小限に抑え、問題が発生した場合のロールバックが可能になります。

</details>

---

[学習資料に戻る](../../../networking/calico/03-networking-modes.md) | [前のクイズ: アーキテクチャ](./02-architecture-quiz.md) | [次のクイズ: BGP 詳細解説](./04-bgp-deep-dive-quiz.md)
