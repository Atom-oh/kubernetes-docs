# eBPF Dataplane クイズ

> **関連ドキュメント**: [eBPF Dataplane](../../../networking/calico/06-ebpf-dataplane.md)
> **最終更新**: February 22, 2026

## クイズ

1. Calico の eBPF dataplane に必要な最小 Linux kernel バージョンは何ですか？
   - A) 4.15+
   - B) 5.0+
   - C) 5.3+
   - D) 5.10+

<details>
<summary>回答を表示</summary>

**回答: C) 5.3+**

**解説:**
Calico の eBPF dataplane には、最小 kernel バージョンとして 5.3 が必要です。ただし、デバッグおよびイントロスペクション機能を向上させる BTF (BPF Type Format) を含む最適なパフォーマンスと完全な機能サポートのためには、kernel 5.8+ が推奨されます。

</details>

2. Calico で iptables から eBPF dataplane に切り替えると、通常どの程度のパフォーマンス向上が期待できますか？
   - A) スループットが 5～10% 向上
   - B) スループットが 20～40% 向上
   - C) スループットが 50～60% 向上
   - D) スループットが 100% 向上

<details>
<summary>回答を表示</summary>

**回答: B) スループットが 20～40% 向上**

**解説:**
eBPF dataplane は通常、iptables と比較して 20～40% のスループット向上をもたらします。これは、eBPF が iptables chain をたどるオーバーヘッドなしに kernel 内で直接パケットを処理するためです。このオーバーヘッドは、rule の数が増えるほど大きくなる可能性があります。

</details>

3. BTF は何の略であり、Calico の eBPF dataplane にとってなぜ重要ですか？
   - A) Binary Transfer Format - ネットワークパケットのエンコード用
   - B) BPF Type Format - デバッグおよび CO-RE サポート用
   - C) Byte Translation Function - アドレス変換用
   - D) Block Transfer Filter - レート制限用

<details>
<summary>回答を表示</summary>

**回答: B) BPF Type Format - デバッグおよび CO-RE サポート用**

**解説:**
BTF (BPF Type Format) は BPF program に型情報を提供します。これにより CO-RE (Compile Once, Run Everywhere) がサポートされ、eBPF program は再コンパイルなしで異なる kernel バージョン間で実行できます。また、BTF は bpftool などのツールによるデバッグ機能も向上させます。

</details>

4. Calico の eBPF dataplane における Direct Server Return (DSR) とは何ですか？
   - A) Pod が Kubernetes API server に直接接続するための方法
   - B) 戻りトラフィックが load balancer をバイパスする load balancing 最適化
   - C) Service discovery のための DNS 解決手法
   - D) Persistent Volume のストレージアクセスパターン

<details>
<summary>回答を表示</summary>

**回答: B) 戻りトラフィックが load balancer をバイパスする load balancing 最適化**

**解説:**
Direct Server Return (DSR) は、backend server からの応答トラフィックが load balancer node をバイパスして client に直接送られる load balancing 最適化です。これによりレイテンシと load balancer の帯域幅消費が削減され、Service の全体的なパフォーマンスが向上します。

</details>

5. Calico の eBPF dataplane における connect-time load balancing とは何ですか？
   - A) node が cluster に参加する際に発生する load balancing
   - B) TCP connection の確立時に実行される Service IP の変換
   - C) backend Pod のための health check メカニズム
   - D) connection が切断された際の自動フェイルオーバー

<details>
<summary>回答を表示</summary>

**回答: B) TCP connection の確立時に実行される Service IP の変換**

**解説:**
Connect-time load balancing は、パケットごとではなく TCP connection が確立された時点で Service IP から Pod IP への変換を実行します。これにより、より効率的な load balancing が実現し、client socket が選択された backend に直接接続するため、DSR のような機能を利用できます。

</details>

6. Calico の eBPF dataplane を有効にすると、kube-proxy はどうなりますか？
   - A) kube-proxy は eBPF と並行して稼働し続ける
   - B) eBPF が同等の機能を提供するため、kube-proxy は無効化できる
   - C) kube-proxy は eBPF を使用するよう自動的にアップグレードされる
   - D) kube-proxy が IPv6 を処理し、eBPF が IPv4 を処理する

<details>
<summary>回答を表示</summary>

**回答: B) eBPF が同等の機能を提供するため、kube-proxy は無効化できる**

**解説:**
Calico の eBPF dataplane は、Service load balancing に関して kube-proxy を完全に置き換えることができます。eBPF mode を有効にすると、重複した処理や潜在的な競合を回避するために kube-proxy を無効化できます。eBPF dataplane は ClusterIP、NodePort、および LoadBalancer Service を直接処理します。

</details>

7. BPF map は Calico の eBPF dataplane で何に使用されますか？
   - A) ジオルーティング用の地理的位置データの保存
   - B) kernel と userspace 間で共有される状態および設定データの保存
   - C) DNS 名から IP アドレスへのマッピング
   - D) ネットワークトポロジ図の作成

<details>
<summary>回答を表示</summary>

**回答: B) kernel と userspace 間で共有される状態および設定データの保存**

**解説:**
BPF map は、kernel 内で実行される eBPF program と userspace application の両方からアクセス可能な状態および設定データを保存する key-value データ構造です。Calico は BPF map を使用して、connection tracking の状態、policy rule、Service endpoint、その他の networking metadata を保存します。

</details>

8. eBPF program における XDP と TC attachment point の違いは何ですか？
   - A) XDP は TC よりもネットワークスタックの早い段階でパケットを処理する
   - B) TC は XDP よりもネットワークスタックの早い段階でパケットを処理する
   - C) XDP は ingress 専用で、TC は egress 専用である
   - D) 違いはなく、これらはエイリアスである

<details>
<summary>回答を表示</summary>

**回答: A) XDP は TC よりもネットワークスタックの早い段階でパケットを処理する**

**解説:**
XDP (eXpress Data Path) は、kernel が sk_buff を割り当てる前でさえ、ネットワークスタック内の可能な限り早い時点でパケットを処理します。TC (Traffic Control) hook は、sk_buff が割り当てられた後の、より遅い段階でパケットを処理します。XDP は最高のパフォーマンスを提供しますが機能は限定的であり、TC はわずかなパフォーマンスコストでより多くの機能を提供します。

</details>

9. Calico で eBPF dataplane を有効にする FelixConfiguration 設定はどれですか？
   - A) dataplaneMode: eBPF
   - B) bpfEnabled: true
   - C) useEBPF: yes
   - D) felixBackend: ebpf

<details>
<summary>回答を表示</summary>

**回答: B) bpfEnabled: true**

**解説:**
eBPF dataplane は、FelixConfiguration resource で `bpfEnabled: true` を設定することで有効になります。`bpfExternalServiceMode`、`bpfKubeProxyIptablesCleanupEnabled` などの eBPF 固有の追加設定も、同じ resource で構成できます。

</details>

10. Calico の bpfExternalServiceMode 設定は何を制御しますか？
    - A) Pod が cluster 外部の Service にアクセスする方法
    - B) 外部 client が NodePort および LoadBalancer Service にアクセスする方法
    - C) Service discovery に使用される外部 DNS server
    - D) 外部 API アクセスの認証 mode

<details>
<summary>回答を表示</summary>

**回答: B) 外部 client が NodePort および LoadBalancer Service にアクセスする方法**

**解説:**
`bpfExternalServiceMode` 設定は、Calico が外部ソースから NodePort および LoadBalancer Service へのトラフィックを処理する方法を制御します。選択肢には "Tunnel"（デフォルト。カプセル化により source IP を保持）と "DSR"（パフォーマンスを向上させる Direct Server Return）があります。

</details>

11. Calico の eBPF program と map のデバッグおよび調査に一般的に使用されるツールはどれですか？
    - A) tcpdump
    - B) bpftool
    - C) netstat
    - D) iptables-save

<details>
<summary>回答を表示</summary>

**回答: B) bpftool**

**解説:**
bpftool は、eBPF program と map を調査およびデバッグするための標準 utility です。ロード済み BPF program の一覧表示、map の内容のダンプ、program 統計情報の表示、BTF 情報の表示ができます。これは Calico の eBPF dataplane のトラブルシューティングに不可欠です。

</details>

12. Calico で iptables から eBPF dataplane へ移行する際の推奨シーケンスは何ですか？
    - A) すべての node で eBPF を同時にただちに有効化する
    - B) まず kube-proxy を無効化してから eBPF を有効化する
    - C) Calico で eBPF を有効化し、動作を検証してから kube-proxy を無効化する
    - D) eBPF を有効にした状態で Calico を最初から再インストールする

<details>
<summary>回答を表示</summary>

**回答: C) Calico で eBPF を有効化し、動作を検証してから kube-proxy を無効化する**

**解説:**
推奨される移行手順は次のとおりです。1) FelixConfiguration で eBPF dataplane を有効化する、2) networking と Service が正しく動作することを検証する、3) eBPF の動作を確認した後に kube-proxy を無効化する。これにより、移行中に問題が見つかった場合でも安全にロールバックできます。

</details>
