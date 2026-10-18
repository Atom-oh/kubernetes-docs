# eBPF データプレーン クイズ

> **関連ドキュメント**: [eBPF データプレーン](../../../networking/calico/06-ebpf-dataplane.md)
> **最終更新**: 2026年9月12日

## クイズ

1. RHEL の backport 例外を除き、現在の Calico 3.32 eBPF ガイドが一般的な最低要件として示す Linux kernel バージョンはどれですか？
   - A) 4.15 以降
   - B) 5.0 以降
   - C) 5.3 以降
   - D) 5.10 以降

<details>
<summary>回答を表示</summary>

**回答: D) 5.10 以降**

**解説:**
一般的な最低基準は 5.10 です。ガイドでは backport の例外として、RHEL 8.4 の kernel `4.18.0-305` 以降を記載しています。一部機能にはさらに新しいバージョンが必要です。eBPF Log rule には 5.16、文書化された QoS bandwidth control には 6.6／TCX が必要です。OS または kernel のバージョンだけでは、プラットフォーム全体の互換性は確認できません。

</details>

2. Calico eBPF に切り替えた場合の性能向上は、どのように評価すべきですか？
   - A) スループットが 5～10% 向上するとみなす
   - B) 実際のワークロードと構成を測定する。共通の向上率はない
   - C) スループットが 50～60% 向上するとみなす
   - D) スループットが 100% 向上するとみなす

<details>
<summary>回答を表示</summary>

**回答: B) 実際のワークロードと構成を測定する。共通の向上率はない**

**解説:**
どちらのデータプレーンも kernel 内でパケットを処理します。改善幅はトラフィック経路、rule、conntrack、CPU/NIC、logging、負荷によって変わります。ガイドに残る異なる過去の報告値には、生の測定根拠がありません。20～40% の向上や policy 負荷が一定であることを約束する値ではありません。

</details>

3. BTF は何の略で、Calico の eBPF データプレーンではどのような役割がありますか？
   - A) Binary Transfer Format — ネットワークパケットを符号化する
   - B) BPF Type Format — デバッグと CO-RE を支援する
   - C) Byte Translation Function — アドレスを変換する
   - D) Block Transfer Filter — rate limit を行う

<details>
<summary>回答を表示</summary>

**回答: B) BPF Type Format — デバッグと CO-RE を支援する**

**解説:**
BTF は、ツールと CO-RE relocation が使う型メタデータを提供します。verifier による安全性検査とは別のもので、コンパイル済みプログラムがすべての kernel で動作する保証にはなりません。Calico はバージョンに応じた object の選択と機能検査を行います。ファイルが存在することだけでは、準備完了を確認できません。

</details>

4. Calico の eBPF データプレーンにおける Direct Server Return (DSR) とは何ですか？
   - A) Pod が Kubernetes API server に直接接続する方法
   - B) 戻りトラフィックが load balancer を経由しないようにする負荷分散の最適化
   - C) Service discovery のための DNS 解決方式
   - D) persistent volume へのアクセス方式

<details>
<summary>回答を表示</summary>

**回答: B) 戻りトラフィックが load balancer を経由しないようにする負荷分散の最適化**

**解説:**
DSR では、リモート backend node が、Service 要求を最初に転送した Kubernetes node を経由せずに応答を返せます。Calico は送信元アドレス変換を行います。互換性のある network fabric と戻り経路が必要です。すべての外部クラウド load balancer を自動的に迂回できるわけではなく、どの環境でも動作するわけではありません。

</details>

5. Calico の eBPF データプレーンにおける connect-time load balancing とは何ですか？
   - A) node がクラスターに参加した時点で行う負荷分散
   - B) TCP connection の確立時に行う Service IP の変換
   - C) backend Pod の health check
   - D) connection が切断された場合の自動 failover

<details>
<summary>回答を表示</summary>

**回答: B) TCP connection の確立時に行う Service IP の変換**

**解説:**
対応する TCP socket では、CTLB が packet processing より前の `connect()` 時に Service 宛先を変換します。有効化した mode では UDP socket hook も含む場合があります。これにより Service DNAT 経路は回避しますが、policy、routing、conntrack、その他の NAT までなくなるわけではありません。DSR は外部への戻り経路に関する別の最適化です。

</details>

6. Calico eBPF と kube-proxy の連携について、正しい説明はどれですか？
   - A) eBPF を使っても kube-proxy の設定は常にそのままにする
   - B) Calico はプラットフォームごとに kube-proxy と連携しながら Service を処理できる
   - C) kube-proxy は自動的に eBPF を使うよう更新される
   - D) kube-proxy が IPv6 を、eBPF が IPv4 を処理する

<details>
<summary>回答を表示</summary>

**回答: B) Calico はプラットフォームごとに kube-proxy と連携しながら Service を処理できる**

**解説:**
インストールの管理主体が提供する手順に従ってください。条件を満たす場合、bootstrap が kube-proxy を管理できます。一方、管理対象 proxy を残すプラットフォームでは、cleanup を無効にし、health-server の設定が競合しないようにする必要があります。cleanup flag だけでは Service 処理を有効にできず、kube-proxy の削除も一律に適用できる手順ではありません。

</details>

7. Calico の eBPF データプレーンで BPF map は何に使われますか？
   - A) 地理的な位置情報を保存して geo-routing を行う
   - B) kernel と userspace で共有する状態および構成データを保存する
   - C) DNS 名を IP アドレスに対応付ける
   - D) ネットワーク構成図を作成する

<details>
<summary>回答を表示</summary>

**回答: B) kernel と userspace で共有する状態および構成データを保存する**

**解説:**
map には route、NAT、conntrack、affinity、ならびにプログラム／counter／IP set を支援するデータが格納されます。map の種類には hash、LRU hash、LPM trie などがあります。policy は BPF program にコンパイルされます。あらゆる policy が一つの汎用的な constant-time の tuple-to-action map に格納されるわけではありません。

</details>

8. native driver XDP と TC attachment point の違いはどれですか？
   - A) XDP は TC よりネットワーク stack の早い段階で packet を処理する
   - B) TC は XDP よりネットワーク stack の早い段階で packet を処理する
   - C) XDP は ingress 専用で、TC は egress 専用である
   - D) 違いはなく、同じものを指す別名である

<details>
<summary>回答を表示</summary>

**回答: A) XDP は TC よりネットワーク stack の早い段階で packet を処理する**

**解説:**
native driver XDP は skb の割り当て前に動作できますが、TC は skb ベースの packet context で動作します。generic XDP はさらに後段で動作し、その時点では skb がすでにあります。driver、hardware、program の各対応状況が関係します。hook の名称だけでは、一定の性能向上は保証されません。

</details>

9. Calico で eBPF データプレーンを有効にする FelixConfiguration 設定はどれですか？
   - A) `dataplaneMode: eBPF`
   - B) `bpfEnabled: true`
   - C) `useEBPF: yes`
   - D) `felixBackend: ebpf`

<details>
<summary>回答を表示</summary>

**回答: B) `bpfEnabled: true`**

**解説:**
standalone manifest の手順では、Felix の `bpfEnabled: true` field を使います。Operator のインストールでは `Installation.spec.calicoNetwork.linuxDataplane: BPF` を選択します。インストールの管理主体、API への直接アクセス、proxy との連携、サポートされるクラスター全体の切り替え手順を守ってください。

</details>

10. Calico の `bpfExternalServiceMode` 設定は何を制御しますか？
    - A) Pod がクラスター外部の Service にアクセスする方法
    - B) 外部 client が NodePort および LoadBalancer Service にアクセスする方法
    - C) Service discovery に使用する外部 DNS server
    - D) 外部 API access の認証 mode

<details>
<summary>回答を表示</summary>

**回答: B) 外部 client が NodePort および LoadBalancer Service にアクセスする方法**

**解説:**
リモートに Service backend がある場合、Tunnel mode は要求と応答に ingress node／tunnel 経路を使います。DSR mode は要求を tunnel 経由で送り、応答は backend node から直接返します。どちらの mode にも、該当する VXLAN／MTU 経路が必要です。DSR には送信元検証と外部 load balancer に関する制約が追加されます。

</details>

11. Calico の eBPF program と map のデバッグ、調査に一般的に使われるツールはどれですか？
    - A) tcpdump
    - B) bpftool
    - C) netstat
    - D) iptables-save

<details>
<summary>回答を表示</summary>

**回答: B) bpftool**

**解説:**
`bpftool` では、実際の BPF program／map の ID、type、state を調べられます。Calico node image には `calico-node -bpf` も含まれています。help subcommand と `policy dump <interface> <hook>` のような完全な引数を使ってください。一覧を表示できても、アプリケーションの接続性が証明されるわけではありません。

</details>

12. Calico 3.32 のデータプレーンを移行する際に適切な方法はどれですか？
    - A) すべての node で直ちに同時に eBPF を有効にする
    - B) 先に kube-proxy を無効にし、その後 eBPF を有効にする
    - C) 互換性と API への直接アクセスを確認し、管理主体に沿った協調的な移行／ロールバック手順に従う
    - D) eBPF を有効にして Calico を最初から再インストールする

<details>
<summary>回答を表示</summary>

**回答: C) 互換性と API への直接アクセスを確認し、管理主体に沿った協調的な移行／ロールバック手順に従う**

**解説:**
Operator による自動 bootstrap には限定された前提条件があります。それ以外のインストールでは、文書化された手動／プラットフォーム別の手順が必要です。テスト準備なしに混在 mode の canary を常設したり、すべての kube-proxy instance を無効にしたりしないでください。公式のローリング切り替えは NodePort traffic を中断する可能性があり、ロールバックで connection が reset される場合もあります。

</details>
