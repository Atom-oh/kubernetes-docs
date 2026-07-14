# 運用クイズ

> **関連ドキュメント**: [運用](../../../networking/calico/09-operations.md)
> **最終更新**: February 22, 2026

## クイズ

1. Calico の主なインストール方法は 3 つありますか？
   - A) Docker、Podman、containerd
   - B) Manifest-based (kubectl)、Operator-based (Tigera)、Helm
   - C) CLI、GUI、API
   - D) バイナリ、パッケージマネージャー、ソースからのコンパイル

<details>
<summary>回答を表示</summary>

**回答: B) Manifest-based (kubectl)、Operator-based (Tigera)、Helm**

**解説:**
Calico は、1) YAML Manifest に対して kubectl apply を使用する Manifest-based インストール、2) Tigera Operator を使用する Operator-based インストール（推奨）、3) カスタマイズ可能な Deployment のための Helm chart を使用してインストールできます。Operator の方法は Calico のライフサイクルを管理するため、通常は本番環境に推奨されます。

</details>

2. BGP peer のステータスを含む Calico node のステータスを表示する calicoctl コマンドはどれですか？
   - A) calicoctl get nodes
   - B) calicoctl node status
   - C) calicoctl describe node
   - D) calicoctl show peers

<details>
<summary>回答を表示</summary>

**回答: B) calicoctl node status**

**解説:**
`calicoctl node status` コマンドは、BGP peering 情報を含む Calico node のステータスを表示し、確立済みの peer、その状態、および接続の問題を示します。これは BGP routing の問題をトラブルシューティングするために不可欠です。

</details>

3. node 間の IPAM block 割り当てを表示するコマンドはどれですか？
   - A) calicoctl ipam show --show-blocks
   - B) calicoctl get ipamblocks
   - C) kubectl get ipamblocks -o wide
   - D) calicoctl describe ipam

<details>
<summary>回答を表示</summary>

**回答: A) calicoctl ipam show --show-blocks**

**解説:**
`calicoctl ipam show --show-blocks` コマンドは、どの IP block がどの node に割り当てられているか、各 block の使用率、全体の IP pool 統計など、詳細な IPAM 情報を表示します。これは IP 割り当ての問題を診断するうえで重要です。

</details>

4. Felix のパフォーマンスと policy 統計を公開する Prometheus metrics endpoint はどれですか？
   - A) :9090/metrics
   - B) :9091/metrics
   - C) :9094/metrics
   - D) :8080/metrics

<details>
<summary>回答を表示</summary>

**回答: B) :9091/metrics**

**解説:**
Felix はデフォルトでポート 9091 に Prometheus metrics を公開します。これらの metrics には、policy rule 数、dataplane プログラミングのレイテンシ、iptables/eBPF 統計、エラー数が含まれます。これは FelixConfiguration で `prometheusMetricsEnabled: true` を使用して有効にする必要があります。

</details>

5. Typha が Prometheus metrics endpoint に使用するポートはどれですか？
   - A) :9091/metrics
   - B) :9093/metrics
   - C) :9094/metrics
   - D) :9095/metrics

<details>
<summary>回答を表示</summary>

**回答: B) :9093/metrics**

**解説:**
Typha はデフォルトでポート 9093 に Prometheus metrics を公開します。Typha metrics には、Felix instance への接続数、datastore sync のレイテンシ、cache 統計が含まれます。大規模 cluster における datastore fan-out のパフォーマンスを理解するためには、Typha の監視が重要です。

</details>

6. Pod が IP address を取得できません。最初に確認すべきことは何ですか？
   - A) kube-proxy logs
   - B) IPPool の可用性と IPAM block 割り当て
   - C) DNS 設定
   - D) Node CPU 使用率

<details>
<summary>回答を表示</summary>

**回答: B) IPPool の可用性と IPAM block 割り当て**

**解説:**
Pod が IP を取得できない場合、まず `calicoctl ipam show` を使用して IPPool に利用可能な address があるか確認します。IPAM block を node に割り当てられること、および IPPool selector が node に一致することを確認します。IPAM 関連のエラーについて Felix logs も確認してください。

</details>

7. node 間の BGP peering が確立できない場合、何を確認すべきですか？
   - A) Pod DNS 解決
   - B) BGP port (179) でのネットワーク接続、BGPConfiguration、および node selector
   - C) Persistent volume binding
   - D) Service account token

<details>
<summary>回答を表示</summary>

**回答: B) BGP port (179) でのネットワーク接続、BGPConfiguration、および node selector**

**解説:**
BGP peering の問題では、次を確認します。1) TCP port 179 での node 間のネットワーク接続、2) BGPConfiguration および BGPPeer resource が正しく定義されていること、3) Node selector が対象の node に一致すること、4) 特定の peering エラーについて `calicoctl node status` と BIRD logs を確認すること。

</details>

8. network policy は適用されていますが、トラフィックがブロックされません。考えられる原因は何ですか？
   - A) cluster が使用するメモリが多すぎる
   - B) Policy selector が対象の Pod に一致しない、または policy の順序/tier が正しくない
   - C) node を再起動する必要がある
   - D) Kubernetes version が古すぎる

<details>
<summary>回答を表示</summary>

**回答: B) Policy selector が対象の Pod に一致しない、または policy の順序/tier が正しくない**

**解説:**
policy が期待どおりに機能しない場合、次を確認します。1) Pod selector が対象の Pod に正しく一致すること（label を確認）、2) Namespace selector が正しいこと、3) Policy tier の順序（優先度が高い tier が先に評価されます）、4) 評価順序の前段に競合する Allow policy がないこと。適用済みの policy を確認するには `calicoctl get policy` を使用します。

</details>

9. Calico version をアップグレードするための推奨手順は何ですか？
   - A) すべての resource を削除して再インストールする
   - B) version 固有の migration guide に従ってインプレースでアップグレードする
   - C) 新しい cluster を作成して workload を移行する
   - D) Calico は Kubernetes とともに自動的にアップグレードされる

<details>
<summary>回答を表示</summary>

**回答: B) version 固有の migration guide に従ってインプレースでアップグレードする**

**解説:**
Calico のアップグレードでは、使用しているインストール方法に対応する公式のアップグレードドキュメントに従う必要があります。通常、Operator または Manifest を新しい version に更新します。一部のアップグレードでは追加の手順が必要になるため、version 固有の migration note を確認してください。まずは非本番環境でテストします。

</details>

10. Calico network policy における default deny のベストプラクティスは何ですか？
    - A) deny policy は決して使用しない
    - B) Namespace に default deny policy を適用し、その後に必要なトラフィックを明示的に許可する
    - C) 外部ソースからのトラフィックのみを拒否する
    - D) すべての egress を拒否し、すべての ingress を許可する

<details>
<summary>回答を表示</summary>

**回答: B) Namespace に default deny policy を適用し、その後に必要なトラフィックを明示的に許可する**

**解説:**
セキュリティのベストプラクティスは、Namespace 内の Pod へのすべての ingress（および必要に応じて egress）トラフィックをブロックする default deny policy を適用し、その後に必要なトラフィック flow のみを許可する特定の policy を作成することです。これにより、network access に最小権限の原則が実装されます。

</details>

11. network visibility のために flow log をエクスポートするよう Calico を設定するにはどうすればよいですか？
    - A) kube-apiserver flag で有効にする
    - B) FelixConfiguration で FlowLogsFileReporter または FlowLogsNetworkReporter を設定する
    - C) flow log はデフォルトで常に有効である
    - D) 別の flow log Operator をインストールする

<details>
<summary>回答を表示</summary>

**回答: B) FelixConfiguration で FlowLogsFileReporter または FlowLogsNetworkReporter を設定する**

**解説:**
flow log は、FlowLogsFileReporter（file に書き込む）または FlowLogsNetworkReporter（collector に送信する）を有効にして、FelixConfiguration で設定します。log interval、aggregation level、キャプチャする flow などの parameter を設定します。注: 完全な flow log 機能には Calico Enterprise が必要です。

</details>

12. calicoctl が datastore に接続するために設定する必要がある environment variable は何ですか？
    - A) CALICO_HOST および CALICO_PORT
    - B) DATASTORE_TYPE および KUBECONFIG（または etcd datastore の ETCD_ENDPOINTS）
    - C) CALICO_API_SERVER および CALICO_TOKEN
    - D) CNI_PATH および CNI_CONFIG

<details>
<summary>回答を表示</summary>

**回答: B) DATASTORE_TYPE および KUBECONFIG（または etcd datastore の ETCD_ENDPOINTS）**

**解説:**
calicoctl を datastore に接続するには、`DATASTORE_TYPE=kubernetes` を設定し、KUBECONFIG が有効な kubeconfig file を指すことを確認します。etcd datastore の場合は、`DATASTORE_TYPE=etcdv3` を `ETCD_ENDPOINTS` とともに設定し、安全な接続のために必要に応じて TLS 関連の variable も設定します。

</details>
