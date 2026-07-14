# Cilium 上級クイズ

> **対応バージョン**: Cilium 1.17
> **最終更新**: February 22, 2026

## eBPF テクノロジー

1. **eBPF プログラムはどこで実行されますか？**
   - A) User Space
   - B) Kernel Space
   - C) コンテナ内
   - D) 仮想マシン内

   <details>
   <summary>回答を表示</summary>
   <p><strong>回答</strong>: B) Kernel Space</p>
   <p><strong>解説</strong>: eBPF プログラムは Linux kernel 内で安全に実行され、kernel 機能を拡張・変更できます。</p>
   </details>

2. **eBPF プログラムの安全性を保証するメカニズムは何ですか？**
   - A) Virtualization
   - B) Containerization
   - C) Static Verifier
   - D) Encryption

   <details>
   <summary>回答を表示</summary>
   <p><strong>回答</strong>: C) Static Verifier</p>
   <p><strong>解説</strong>: eBPF verifier は、無限ループや kernel クラッシュを防ぐため、ロード前にプログラムの安全性を確認します。</p>
   </details>

3. **Cilium で eBPF を使用する主な利点ではないものはどれですか？**
   - A) kernel module を使用しないネットワーキング機能の実装
   - B) 高性能かつ低オーバーヘッド
   - C) きめ細かな network policy の適用
   - D) Hardware acceleration が必要

   <details>
   <summary>回答を表示</summary>
   <p><strong>回答</strong>: D) Hardware acceleration が必要</p>
   <p><strong>解説</strong>: eBPF は Hardware acceleration を必要とせず、ソフトウェアベースで高性能を提供できます。</p>
   </details>

## ネットワーキングモデル

4. **Cilium でサポートされていない data path mode はどれですか？**
   - A) VXLAN
   - B) Geneve
   - C) Direct Routing
   - D) MPLS

   <details>
   <summary>回答を表示</summary>
   <p><strong>回答</strong>: D) MPLS</p>
   <p><strong>解説</strong>: Cilium は VXLAN、Geneve、Direct Routing をサポートしますが、MPLS はサポートしていません。</p>
   </details>

5. **kube-proxy replacement mode で Cilium が使用する技術は何ですか？**
   - A) iptables
   - B) IPVS
   - C) eBPF-based XDP
   - D) netfilter

   <details>
   <summary>回答を表示</summary>
   <p><strong>回答</strong>: C) eBPF-based XDP</p>
   <p><strong>解説</strong>: Cilium は eBPF と XDP (eXpress Data Path) を使用して kube-proxy を置き換え、より高い性能を提供します。</p>
   </details>

6. **Pod 間通信中の packet path を追跡する、Cilium の network model の機能は何ですか？**
   - A) tcpdump
   - B) Hubble Flow Monitoring
   - C) Wireshark
   - D) Prometheus

   <details>
   <summary>回答を表示</summary>
   <p><strong>回答</strong>: B) Hubble Flow Monitoring</p>
   <p><strong>解説</strong>: Hubble は Cilium の network flow monitoring tool であり、Pod 間通信をリアルタイムで追跡・可視化できます。</p>
   </details>

## IPAM と Network Policy

7. **AWS EKS と統合される Cilium の IPAM (IP Address Management) mode はどれですか？**
   - A) Cluster Pool
   - B) Kubernetes Host Scope
   - C) AWS ENI
   - D) CRD-based

   <details>
   <summary>回答を表示</summary>
   <p><strong>回答</strong>: C) AWS ENI</p>
   <p><strong>解説</strong>: Cilium は AWS ENI (Elastic Network Interface) mode を通じて EKS と統合し、VPC IP address を Pod に直接割り当てます。</p>
   </details>

8. **Cilium network policy の 'toFQDNs' rule では何が許可されますか？**
   - A) 特定の IP address への traffic
   - B) 特定の port への traffic
   - C) 特定の domain name への traffic
   - D) 特定の protocol の traffic

   <details>
   <summary>回答を表示</summary>
   <p><strong>回答</strong>: C) 特定の domain name への traffic</p>
   <p><strong>解説</strong>: toFQDNs rule は特定の domain name (FQDN) への traffic を許可します。Cilium は DNS lookup を監視し、それらの domain に対応する IP address を動的に許可します。</p>
   </details>

9. **Cilium CiliumNetworkPolicy でサポートされていない selector はどれですか？**
   - A) endpointSelector
   - B) nodeSelector
   - C) namespaceSelector
   - D) serviceSelector

   <details>
   <summary>回答を表示</summary>
   <p><strong>回答</strong>: D) serviceSelector</p>
   <p><strong>解説</strong>: Cilium は endpointSelector、nodeSelector、namespaceSelector をサポートしますが、serviceSelector は直接サポートしていません。</p>
   </details>

## L2-L7 ネットワーキング

10. **HTTP request に対する Cilium の L7 policy で filter できない attribute はどれですか？**
    - A) Path
    - B) Method
    - C) Headers
    - D) Response Time

    <details>
    <summary>回答を表示</summary>
    <p><strong>回答</strong>: D) Response Time</p>
    <p><strong>解説</strong>: Cilium の L7 policy は path、method、header などの HTTP request attribute を filter できますが、response time は filter の対象ではありません。</p>
    </details>

11. **Cilium の Service Mesh 機能で提供されないものは何ですか？**
    - A) Mutual TLS (mTLS)
    - B) Traffic Splitting
    - C) Service Discovery
    - D) User Authentication

    <details>
    <summary>回答を表示</summary>
    <p><strong>回答</strong>: D) User Authentication</p>
    <p><strong>解説</strong>: Cilium Service Mesh は mutual TLS、traffic splitting、service discovery を提供しますが、user authentication は通常、別の authentication system が処理します。</p>
    </details>

12. **Cilium の Envoy integration はどの機能を提供しますか？**
    - A) L7 load balancing
    - B) L7 visibility
    - C) L7 policy enforcement
    - D) 上記すべて

    <details>
    <summary>回答を表示</summary>
    <p><strong>回答</strong>: D) 上記すべて</p>
    <p><strong>解説</strong>: Cilium は Envoy proxy と統合し、L7 load balancing、visibility、policy enforcement を提供します。</p>
    </details>

## セキュリティと可視性

13. **Hubble UI で提供されない機能はどれですか？**
    - A) Service dependency map
    - B) Network flow visualization
    - C) Policy violation alert
    - D) Code deployment management

    <details>
    <summary>回答を表示</summary>
    <p><strong>回答</strong>: D) Code deployment management</p>
    <p><strong>解説</strong>: Hubble UI は service dependency map、network flow visualization、policy violation alert を提供しますが、code deployment management は提供しません。</p>
    </details>

14. **Cilium で network traffic encryption に使用できる protocol はどれですか？**
    - A) IPsec and WireGuard
    - B) TLS and SSH
    - C) SSL and HTTPS
    - D) DTLS and QUIC

    <details>
    <summary>回答を表示</summary>
    <p><strong>回答</strong>: A) IPsec and WireGuard</p>
    <p><strong>解説</strong>: Cilium は IPsec および WireGuard protocol を使用して、node 間の network traffic を暗号化できます。</p>
    </details>

15. **次の説明に該当する Cilium の security feature はどれですか？「特定の application layer protocol の特定の field または pattern に基づいて traffic を filter する」**
    - A) Network policies
    - B) L7 policies
    - C) Encryption
    - D) Intrusion detection

    <details>
    <summary>回答を表示</summary>
    <p><strong>回答</strong>: B) L7 policies</p>
    <p><strong>解説</strong>: L7 (application layer) policy は、HTTP、gRPC、Kafka などの protocol 内にある特定の field または pattern に基づいて traffic を filter できます。</p>
    </details>

## 上級トピックと実運用のユースケース

16. **Cilium Cluster Mesh の主な機能ではないものはどれですか？**
    - A) Cross-cluster service discovery
    - B) Cross-cluster network policies
    - C) Cross-cluster load balancing
    - D) Cross-cluster storage sharing

    <details>
    <summary>回答を表示</summary>
    <p><strong>回答</strong>: D) Cross-cluster storage sharing</p>
    <p><strong>解説</strong>: Cilium Cluster Mesh は cross-cluster service discovery、network policy、load balancing を提供しますが、storage sharing は提供しません。</p>
    </details>

17. **Cilium の Bandwidth Manager feature は何を提供しますか？**
    - A) Network bandwidth monitoring
    - B) Network bandwidth limiting and QoS
    - C) Network bandwidth optimization
    - D) Network bandwidth prediction

    <details>
    <summary>回答を表示</summary>
    <p><strong>回答</strong>: B) Network bandwidth limiting and QoS</p>
    <p><strong>解説</strong>: Cilium の Bandwidth Manager は eBPF を使用して、Pod ごとの network bandwidth limiting と QoS (Quality of Service) を提供します。</p>
    </details>

18. **Cilium の Host Firewall feature は何を保護しますか？**
    - A) Container 間通信のみ
    - B) Node 間通信のみ
    - C) host 自身の network interface
    - D) 外部 cloud service

    <details>
    <summary>回答を表示</summary>
    <p><strong>回答</strong>: C) host 自身の network interface</p>
    <p><strong>解説</strong>: Cilium の Host Firewall は host 自身の network interface を保護し、host level の security を強化します。</p>
    </details>

19. **Cilium の Egress Gateway feature の主な目的は何ですか？**
    - A) 外部 traffic の source IP address を保持する
    - B) 外部 traffic の destination IP address を変更する
    - C) 外部 traffic を暗号化する
    - D) 外部 traffic をブロックする

    <details>
    <summary>回答を表示</summary>
    <p><strong>回答</strong>: A) 外部 traffic の source IP address を保持する</p>
    <p><strong>解説</strong>: Cilium の Egress Gateway は、Pod から cluster 外部への outbound traffic を特定の IP に SNAT し、一貫した source IP を提供します。</p>
    </details>

20. **Cilium の BGP support で実現できないものは何ですか？**
    - A) External router との route exchange
    - B) LoadBalancer Service の external IP の advertising
    - C) cluster 間の direct routing
    - D) DNS record の自動作成

    <details>
    <summary>回答を表示</summary>
    <p><strong>回答</strong>: D) DNS record の自動作成</p>
    <p><strong>解説</strong>: Cilium の BGP support は external router との route exchange、LoadBalancer Service の external IP の advertising、cluster 間の direct routing を提供しますが、DNS record の自動作成は提供しません。</p>
    </details>

## パフォーマンスとトラブルシューティング

21. **packet processing latency を大幅に削減する Cilium の performance optimization technology はどれですか？**
    - A) TCP BBR
    - B) XDP (eXpress Data Path)
    - C) DPDK
    - D) TSO (TCP Segmentation Offload)

    <details>
    <summary>回答を表示</summary>
    <p><strong>回答</strong>: B) XDP (eXpress Data Path)</p>
    <p><strong>解説</strong>: XDP は network driver level で packet を処理し、kernel networking stack を bypass することで latency を大幅に削減します。</p>
    </details>

22. **Cilium で network connectivity issue を診断する command は何ですか？**
    - A) `cilium status`
    - B) `cilium connectivity test`
    - C) `cilium monitor`
    - D) `cilium endpoint list`

    <details>
    <summary>回答を表示</summary>
    <p><strong>回答</strong>: B) `cilium connectivity test`</p>
    <p><strong>解説</strong>: `cilium connectivity test` command は、issue を診断するために cluster 内のさまざまな network connectivity scenario をテストします。</p>
    </details>

23. **Cilium で特定の Pod の network policy status を確認する command は何ですか？**
    - A) `cilium endpoint list`
    - B) `cilium policy get`
    - C) `cilium endpoint get <endpoint-id>`
    - D) `cilium status --all-endpoints`

    <details>
    <summary>回答を表示</summary>
    <p><strong>回答</strong>: C) <code>cilium endpoint get &lt;endpoint-id&gt;</code></p>
    <p><strong>解説</strong>: <code>cilium endpoint get &lt;endpoint-id&gt;</code> command は、特定の endpoint (Pod) の詳細情報と適用されている network policy status を表示します。</p>
    </details>

24. **Cilium で BPF map status を確認する command は何ですか？**
    - A) `cilium map list`
    - B) `cilium bpf maps`
    - C) `cilium status --maps`
    - D) `cilium bpf map list`

    <details>
    <summary>回答を表示</summary>
    <p><strong>回答</strong>: B) `cilium bpf maps`</p>
    <p><strong>解説</strong>: `cilium bpf maps` command は、Cilium が使用するすべての BPF map の一覧と status を表示します。</p>
    </details>

25. **Cilium で network packet capture と analysis を行う command は何ですか？**
    - A) `cilium tcpdump`
    - B) `cilium capture`
    - C) `cilium monitor`
    - D) `cilium packet-capture`

    <details>
    <summary>回答を表示</summary>
    <p><strong>回答</strong>: C) `cilium monitor`</p>
    <p><strong>解説</strong>: `cilium monitor` command は、Cilium の eBPF data path を通過する packet をリアルタイムで capture・analysis できます。</p>
    </details>
