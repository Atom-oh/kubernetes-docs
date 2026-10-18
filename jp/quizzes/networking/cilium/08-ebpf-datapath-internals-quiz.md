# パート8: eBPFデータパス内部構造のクイズ

> **Cilium 1.20.2 · 2026-10-15**

1. **Cilium 1.20では、カーネルが対応している場合、デバイスごとのプログラムにどのアタッチ方式を使いますか。対応していない場合はどうなりますか？**
   - A) 常に従来の`clsact`フィルターを使う。tcxはnetkitでのみ使う
   - B) tcxの`bpf_link`（カーネル6.6以降）を使う。対応していない場合は`clsact` + `cls_bpf`のdirect-actionを使う
   - C) すべてのvethでXDPを使う。対応していない場合はagentの起動を拒否する
   - D) すべてのインターフェイスでcgroupフックを使う。対応していない場合はiptablesを使う

   <details>
   <summary>回答を表示</summary>

   **回答: B) tcxの`bpf_link`（カーネル6.6以降）を使う。対応していない場合は`clsact` + `cls_bpf`のdirect-actionを使う**

   `bpf.enableTCX`のデフォルトはtrueです。リンクは`/sys/fs/bpf/cilium/...`以下にpinされ、reload時にアトミックに更新されます。tc-bpfもtcxも動作しない場合に限り、agentは失敗します。

   </details>

2. **同じノード内のPod間トラフィックはBPFホストルーティングと`bpf_redirect_peer`を使います。宛先Podのingressポリシーはどこで適用されますか？**
   - A) 送信元の`bpf_lxc`プログラムが`cilium_call_policy[destination endpoint ID]`をtail callする
   - B) 宛先vethのtc egressフックが、送信元エンドポイント用にpinされたポリシーマップを使って適用する
   - C) agentが各エンドポイントの宛先netnsに設定したiptablesチェーン
   - D) パケットがvethに到達する前に、ノードNICのXDPプログラムが適用する

   <details>
   <summary>回答を表示</summary>

   **回答: A) 送信元の`bpf_lxc`プログラムが`cilium_call_policy[destination endpoint ID]`をtail callする**

   `redirect_peer`は宛先側のtc egressフックを通らないため、宛先の`cil_lxc_policy`はglobal prog arrayに保存され、送信側から呼び出されます。空のスロットは`DROP_EP_NOT_READY`になります。

   </details>

3. **エンドポイントごとのポリシーマップ`cilium_policy_v3_<id>`の型とキー構造は何ですか？**
   - A) リモートPodのIPアドレスと宛先ポートをキーとするHASH
   - B) ポート番号をインデックスとし、プロトコルごとに1スロットを持つARRAY
   - C) ポリシールール番号をインデックスとし、ルールごとのプログラムをtail callするPROG_ARRAY
   - D) セキュリティID、方向、プロトコル、ポートプレフィックスをキーとするLPM_TRIE

   <details>
   <summary>回答を表示</summary>

   **回答: D) セキュリティID、方向、プロトコル、ポートプレフィックスをキーとするLPM_TRIE**

   キーには`sec_label`、`egress`ビット、`protocol`、`dport`が含まれます。ポートプレフィックスを使うと、ポート範囲を少数のエントリで保存できます。また、`sec_label`が0の場合はL3のワイルドカードとして動作します。

   </details>

4. **チュートリアルに、Cilium 1.20でオーバーレイ宛先のリモートノードを調べるには`cilium_tunnel_map`を確認するとあります。正しい説明はどれですか？**
   - A) `cilium-dbg bpf tunnel list`でノードからエンドポイントへのテーブルを表示する
   - B) マップは存在するが、IPsecまたはWireGuard暗号化を有効にした場合だけ使用される
   - C) マップはなくなり、トンネルエンドポイントは`cilium_ipcache_v2`の値のフィールドに格納されている
   - D) マップがエンドポイント単位の`cilium_tunnel_map_<id>`になり、ノードごとに1つのエントリを持つ

   <details>
   <summary>回答を表示</summary>

   **回答: C) マップはなくなり、トンネルエンドポイントは`cilium_ipcache_v2`の値のフィールドに格納されている**

   1.20のBPFコードで`cilium_tunnel_map`を参照する箇所はありません。`cilium_ipcache_v2`（LPM_TRIE）は`flag_has_tunnel_ep`とともに`sec_identity`と`tunnel_endpoint`を返します。`cilium-dbg bpf ipcache list`を使ってください。

   </details>

5. **1.20.2における`--bpf-map-dynamic-size-ratio`のデフォルトと、サイズを決める対象のマップはどれですか？**
   - A) RAMの0.0025。CT、NAT、NodePort neighbor、socket reverse-NATマップ
   - B) 0（無効）。`--bpf-policy-map-max`でサイズが決まるポリシーマップだけ
   - C) RAMの0.25。LBマップとipcacheを含むすべてのBPFマップ
   - D) RAMの0.0025。ipcacheとポリシーマップだけ

   <details>
   <summary>回答を表示</summary>

   **回答: A) RAMの0.0025。CT、NAT、NodePort neighbor、socket reverse-NATマップ**

   動的サイズ設定はデフォルトで有効です。`--bpf-ct-global-tcp-max`などのサイズ指定フラグを設定すると、そのマップだけ動的サイズ設定が無効になります。LBマップには代わりに`--bpf-lb-map-max`を使います。

   </details>

6. **`--bpf-lb-map-max`（デフォルト65536）は何を制御しますか？**
   - A) `cilium_lb4_services_v2`マップだけを制御し、バックエンドとrev-NATはそれぞれのデフォルト値のままにする
   - B) Serviceごとのバックエンド数を制御し、上限を超えたエンドポイントを拒否する
   - C) 固定リストから素数を選ぶ必要があるMaglev検索テーブルのサイズ
   - D) LBマップごとにある6つのフラグ（services、backends、rev-NAT、affinity、source-range、Maglev）で使うフォールバックサイズ

   <details>
   <summary>回答を表示</summary>

   **回答: D) LBマップごとにある6つのフラグ（services、backends、rev-NAT、affinity、source-range、Maglev）で使うフォールバックサイズ**

   マップごとの6つのフラグはそれぞれデフォルトが0であり、「`lb-map-max`を使う」という意味です。Maglevテーブルのサイズは別のフラグで指定します。サイズ変更ではマップを再作成するため、再投入されるまで接続が中断します。

   </details>

7. **socket-LBが有効な場合、ClusterIPはどこで変換されますか。また、応答でアプリケーションからServiceアドレスが見えるのはなぜですか？**
   - A) すべてのパケットでveth上のDNATによって変換され、応答経路では`cilium_lb4_reverse_nat`が元に戻す
   - B) cgroupフックが`connect()`/`sendmsg()`で変換し、`recvmsg`/`getpeername`フックが`cilium_lb4_reverse_sk`を使って元に戻す
   - C) ホストnetnsのkube-proxy iptables DNATで変換し、conntrackが元のアドレスに戻す
   - D) パケットがスタックに到達する前にNICのXDPで変換し、Hubble relayが元に戻す

   <details>
   <summary>回答を表示</summary>

   **回答: B) cgroupフックが`connect()`/`sendmsg()`で変換し、`recvmsg`/`getpeername`フックが`cilium_lb4_reverse_sk`を使って元に戻す**

   ネットワーク上ではDNATが行われないため、Pod内の`tcpdump`にはバックエンドIPが表示されます。`cilium_lb4_reverse_nat`を使うパケット単位の経路は、socket-LBが適用されない場合（たとえばhost-namespace-onlyモード、L7 LB、SCTP）に限り使われます。

   </details>

8. **オーバーレイモードでパケットが`cilium_vxlan`に到着すると、`cil_from_overlay`はどのように送信元のセキュリティIDを取得しますか？**
   - A) 送信元のセキュリティIDを設定した送信側が付与したトンネルID（VNI）を、`bpf_skb_get_tunnel_key`で読み取る
   - B) 外側の送信元IPを`cilium_lxc`で検索する。このマップはノードIPとIDを対応付ける
   - C) ローカルEnvoyプロキシがリクエストへ追加したHTTPヘッダーを読む
   - D) エンドポイントラベルキャッシュを使って送信元Pod名からIDを解析する

   <details>
   <summary>回答を表示</summary>

   **回答: A) 送信元のセキュリティIDを設定した送信側が付与したトンネルID（VNI）を、`bpf_skb_get_tunnel_key`で読み取る**

   トンネルIDにホストのセキュリティIDが入っている場合は`DROP_INVALID_IDENTITY`で拒否されます。ネイティブルーティングにはVNIがないため、送信元IPから`cilium_ipcache_v2`を使って送信元のセキュリティIDを取得します（またはIPsec/WireGuard利用時にはmarkから取得します）。

   </details>

9. **管理者がCiliumNetworkPolicyを編集すると、agentはデータパスに何を行いますか？**
   - A) 影響するエンドポイントごとにclangで`bpf_lxc.c`を再コンパイルし、そのveth上のプログラムを再読み込みする
   - B) 新しいポリシーをアトミックに反映するため、すべてのデバイスでpin済みtcxリンクを置き換える
   - C) `cilium_policy_v3_<id>`のエントリを更新する。プログラムを再読み込みするのは、エンドポイントまたはノード設定のハッシュが変わった場合だけ
   - D) すべてのエンドポイントでプログラムを再生成するため、Cilium agent Podを再起動する

   <details>
   <summary>回答を表示</summary>

   **回答: C) `cilium_policy_v3_<id>`のエントリを更新する。プログラムを再読み込みするのは、エンドポイントまたはノード設定のハッシュが変わった場合だけ**

   ポリシーの変更はマップ操作（`RegenerateWithoutDatapath`）です。テンプレートオブジェクトはtemplate-config hashごとにキャッシュされ、エンドポイントごとの値は`.rodata.config`に保存されます。

   </details>

10. **1.20のHubbleイベントパイプラインに関する正しい説明はどれですか？**
    - A) BPFがring bufferへ書き込み、Hubble Relayが各ノードのBPF filesystemから直接読み取る
    - B) イベントは`cilium_events`（perf array）に入り、agent monitorとHubble queueを経由して4095件のflowを保持するメモリ内ringに入る
    - C) agentがflowをディスクに保存し、再起動後にHubble Relayへ再生する
    - D) L7イベントはプロキシリダイレクトマップが一致した際に、`bpf_lxc` tailプログラムが生成する

    <details>
    <summary>回答を表示</summary>

    **回答: B) イベントは`cilium_events`（perf array）に入り、agent monitorとHubble queueを経由して4095件のflowを保持するメモリ内ringに入る**

    `perf_event_ring_buffer`での損失や`observer_events_queue`での損失が発生することがあります。L7レコードはBPFではなく、EnvoyとDNSプロキシからagentイベントとして送られます。

    </details>
