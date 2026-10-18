# パート9: オーバーレイとネイティブルーティングの詳細クイズ

> **Cilium 1.20.2 · 2026-10-15**

## トンネルの仕組み

1. **Ciliumはカプセル化パケットの24ビットVNIに何を設定しますか？**
   - A) 宛先ノードID
   - B) 送信元エンドポイントのセキュリティID
   - C) CiliumのクラスターID
   - D) 受信側が`cilium_tunnel_map`で対応付けるノードごとのランダム値

   <details>
   <summary>回答を表示</summary>

   **回答: B) 送信元エンドポイントのセキュリティID**

   VNIには送信元IDが含まれます（`world-ipv4`/`world-ipv6`は`world`として送信され、`host`は`remote-node`に書き換えられます）。受信側はipcacheも持つため、VNIは最適化であり唯一の情報源ではありません。`cilium_tunnel_map`は1.18でデータパスから削除されました（agentは残存するマップのpinを解除するだけです）。Goパッケージは1.19で削除され、トンネルエンドポイントはipcacheの値に含まれます。

   </details>

2. Ciliumでは、IDの伝送に関してGeneveとVXLANでどのような違いがありますか？
   - A) GeneveはTLVオプションでIDを運び、VXLANはVNIでIDを運ぶ
   - B) GeneveはIDを運ばず、ポリシーは送信側だけで評価される
   - C) Geneveは外側UDPの送信元ポートでIDを運ぶ
   - D) 違いはない。どちらもVNIでIDを運び、GeneveオプションはDSRのサービスアドレスとポートにだけ使われる

   <details>
   <summary>回答を表示</summary>

   **回答: D) 違いはない。どちらもVNIでIDを運び、GeneveオプションはDSRのサービスアドレスとポートにだけ使われる**

   Ciliumが挿入するGeneveオプション（クラス`0x014B`、タイプ`0x81`）はDSR用だけです。外側の送信元ポート範囲（`tunnelSourcePortRange`）はエントロピーにだけ影響し、IDとは無関係です。

   </details>

3. トンネルモードでは、外側のUDP/IPヘッダーをどのコンポーネントが作成しますか？
   - A) パケットにヘッダーを書き込む`bpf_lxc`プログラム
   - B) ユーザー空間のcilium-agent
   - C) BPFがトンネルキーを設定してリダイレクトした後に、フローベースの`cilium_vxlan`/`cilium_geneve`デバイスの背後にあるカーネルのvxlan/geneveドライバーが作成する
   - D) NICファームウェア

   <details>
   <summary>回答を表示</summary>

   **回答: C) BPFがトンネルキーを設定してリダイレクトした後に、フローベースの`cilium_vxlan`/`cilium_geneve`デバイスの背後にあるカーネルのvxlan/geneveドライバーが作成する**

   BPFは`bpf_skb_set_tunnel_key`を呼び出し、トンネルデバイスのifindexへリダイレクトします。カプセル化はカーネルドライバーが行います。受信側ではカーネルがカプセル化を解除し、`cil_from_overlay`がトンネルキーを読み取ります。

   </details>

4. Cilium 1.20.2で`routingMode: tunnel`と`autoDirectNodeRoutes: true`を同時に設定すると、どうなりますか？
   - A) パケットをトンネルデバイス経由にする必要があるため、agentが致命的エラーで終了する
   - B) サブネット内では直接ルートを使い、サブネット間ではトンネルを使う
   - C) 警告を出してフラグを無視する
   - D) ネイティブルーティングにフォールバックする

   <details>
   <summary>回答を表示</summary>

   **回答: A) パケットをトンネルデバイス経由にする必要があるため、agentが致命的エラーで終了する**

   `daemon_main.go`では`TunnelingEnabled() && EnableAutoDirectRouting`を検査します。サブネット単位のフォールバックはありません。v1.21.0-pre.3のメッセージは「requires native routing mode」と表現されていますが、やはり致命的エラーになります。

   </details>

## MTU、マスカレード、ホストルーティング

5. IPv4のアンダーレイが1500バイトで、VXLANとWireGuardを両方有効にした場合、Podから見えるルートMTUはいくつですか？
   - A) 1450
   - B) 1405
   - C) 1373
   - D) 1355

   <details>
   <summary>回答を表示</summary>

   **回答: D) 1355**

   ルートMTUはベースMTUから（WireGuard 95 + トンネル 50）を差し引いた値です。1450はVXLANのみ、1405はWireGuardを使うネイティブルーティング、1373はIPsecを使うVXLAN（50 + 77）の値です。

   </details>

6. `routingMode: tunnel`でDSRを使うために必要な設定はどれですか？
   - A) `dsrDispatch: opt`を使うVXLAN
   - B) `tunnelProtocol: geneve`と`loadBalancer.dsrDispatch: geneve`
   - C) `loadBalancer.mode: hybrid`を使うVXLAN
   - D) `dsrDispatch: ipip`を使い、他には何も変更せずに任意のトンネルプロトコルを使う

   <details>
   <summary>回答を表示</summary>

   **回答: B) `tunnelProtocol: geneve`と`loadBalancer.dsrDispatch: geneve`**

   agentはVXLANトンネルでの`dsr`/`hybrid`を拒否します。トンネルモードのDSRではGeneve dispatchが必要で、Geneve dispatchを使うにはGeneveトンネルプロトコルが必要です。

   </details>

7. netkitに対応していないカーネルのノードで`bpf.datapathMode: auto`を設定するとどうなりますか？
   - A) agentが起動に失敗する
   - B) agentが`netkit-l2`に切り替える
   - C) agentがvethにフォールバックし、警告を記録する。明示的に`netkit`を指定した場合は致命的エラーになる
   - D) agentはnetkitを再試行し続け、Podの作成が止まる

   <details>
   <summary>回答を表示</summary>

   **回答: C) agentがvethにフォールバックし、警告を記録する。明示的に`netkit`を指定した場合は致命的エラーになる**

   1.20で追加された`auto`は機能をプローブして、ログに「datapath autodiscovery failed, reverting from netkit to veth」と記録しながら降格します。netkitにはBPFマスカレードとKPRが必要で、従来のホストルーティングは使えません。

   </details>

8. BPFホストルーティングがデフォルトですが、kube-proxy replacementを有効にしたままiptablesマスカレードを使っています。agentはどう動作しますか？
   - A) BPFホストルーティングにはBPFマスカレードが必要だと記録し、警告なしで従来のホストルーティングにフォールバックする
   - B) 起動を拒否する
   - C) BPFマスカレードを自動的に有効にする
   - D) kube-proxy replacementを無効にする

   <details>
   <summary>回答を表示</summary>

   **回答: A) BPFホストルーティングにはBPFマスカレードが必要だと記録し、警告なしで従来のホストルーティングにフォールバックする**

   ホストルーティングはベストエフォートです。netkit、Pod向けBBR、BIG TCPなど、明示的に有効化され、ホストルーティングを必要とする機能は致命的エラーになります。`cilium-dbg status`の`Routing:`行にある`Host:`フィールド（`Host: Legacy`）で確認してください。

   </details>

9. バンド幅マネージャーを有効にした状態で、`kubernetes.io/egress-bandwidth: "10M"`を設定すると、Podの何を制限しますか？
   - A) 10 MB/秒
   - B) ReplicaSetごとに10 Mbit/秒
   - C) BBRも有効にしない限り何も制限しない
   - D) 10 Mbit/秒

   <details>
   <summary>回答を表示</summary>

   **回答: D) 10 Mbit/秒**

   この値はビット単位のKubernetes Quantityです。PodごとのegressはEDTとFQで制御され、BBRは任意です。IPsecを使うと、マネージャーは警告なく無効になります。

   </details>

10. BPFマスカレードをデフォルト設定で使った場合、Podからリモートノードへのトラフィックはどのように扱われますか？
    - A) 常にマスカレードされる
    - B) マスカレードされない
    - C) ネイティブルーティングではマスカレードされず、トンネルモードでは（ipcacheエントリに`skip_tunnel`がない限り）マスカレードされる
    - D) 宛先がRFC1918範囲外の場合だけマスカレードされる

    <details>
    <summary>回答を表示</summary>

    **回答: C) ネイティブルーティングではマスカレードされず、トンネルモードでは（ipcacheエントリに`skip_tunnel`がない限り）マスカレードされる**

    これは`bpf/lib/nat.h`にある判定順序のステップ5です。`enable-remote-node-masquerade=true`（1.19以降、`extraConfig`で設定）にすると、どちらのモードでもマスカレードされます。

    </details>
