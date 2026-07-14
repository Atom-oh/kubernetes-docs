# Cilium IPAM と Network Policy クイズ

> **対応バージョン**: Cilium 1.17
> **最終更新**: February 22, 2026

## IPAM (IP Address Management)

1. **Cilium のデフォルト IPAM モードは何ですか？**
   - A) Kubernetes Host Scope
   - B) Cluster Scope
   - C) CRD-based
   - D) AWS ENI

   <details>
   <summary>回答を表示</summary>
   <p><strong>回答</strong>: B) Cluster Scope</p>
   <p><strong>解説</strong>: Cilium のデフォルト IPAM モードは Cluster Scope であり、クラスター全体にわたって IP アドレスを一元的に割り当てます。</p>
   </details>

2. **各 node が自身の CIDR 範囲から IP を割り当てる Cilium IPAM モードはどれですか？**
   - A) Cluster Scope
   - B) Kubernetes Host Scope
   - C) CRD-based
   - D) AWS ENI

   <details>
   <summary>回答を表示</summary>
   <p><strong>回答</strong>: B) Kubernetes Host Scope</p>
   <p><strong>解説</strong>: Kubernetes Host Scope IPAM モードでは、各 node が自身の CIDR 範囲から IP アドレスを割り当てます。</p>
   </details>

3. **AWS EKS で Cilium を使用する場合に推奨される IPAM モードはどれですか？**
   - A) Kubernetes Host Scope
   - B) Cluster Scope
   - C) AWS ENI
   - D) CRD-based

   <details>
   <summary>回答を表示</summary>
   <p><strong>回答</strong>: C) AWS ENI</p>
   <p><strong>解説</strong>: AWS EKS では、VPC IP アドレスを Pod に直接割り当てるため、AWS ENI IPAM モードの使用が推奨されます。</p>
   </details>

4. **Cilium の 'PodCIDR' IPAM モードは、どの Kubernetes 機能を利用しますか？**
   - A) NodeSpec.PodCIDR
   - B) NodeSpec.CIDR
   - C) NodeSpec.Subnet
   - D) NodeSpec.IPRange

   <details>
   <summary>回答を表示</summary>
   <p><strong>回答</strong>: A) NodeSpec.PodCIDR</p>
   <p><strong>解説</strong>: Cilium の PodCIDR IPAM モードは、Kubernetes が各 node に割り当てる NodeSpec.PodCIDR フィールドを利用します。</p>
   </details>

5. **Cilium の IPAM 設定を確認するにはどのコマンドを使用しますか？**
   - A) `cilium status --ipam`
   - B) `cilium ipam`
   - C) `cilium config get ipam`
   - D) `kubectl -n kube-system get configmap cilium-config -o yaml | grep -E 'ipam|allocator'`

   <details>
   <summary>回答を表示</summary>
   <p><strong>回答</strong>: D) `kubectl -n kube-system get configmap cilium-config -o yaml | grep -E 'ipam|allocator'`</p>
   <p><strong>解説</strong>: Cilium の IPAM 設定は cilium-config ConfigMap に保存されており、このコマンドで確認できます。</p>
   </details>

## Network Policy の基本

6. **Cilium NetworkPolicy の API バージョンは何ですか？**
   - A) networking.k8s.io/v1
   - B) cilium.io/v1
   - C) cilium.io/v2
   - D) policy.cilium.io/v1

   <details>
   <summary>回答を表示</summary>
   <p><strong>回答</strong>: C) cilium.io/v2</p>
   <p><strong>解説</strong>: Cilium NetworkPolicy は cilium.io/v2 API バージョンを使用します。</p>
   </details>

7. **Cilium NetworkPolicy における 'endpointSelector' の役割は何ですか？**
   - A) ポリシー適用対象の Pod を選択する
   - B) ポリシー適用対象の node を選択する
   - C) ポリシー適用対象の namespace を選択する
   - D) ポリシー適用対象の Service を選択する

   <details>
   <summary>回答を表示</summary>
   <p><strong>回答</strong>: A) ポリシー適用対象の Pod を選択する</p>
   <p><strong>解説</strong>: endpointSelector は、ポリシーを適用する対象の Pod（endpoint）を選択するために使用します。</p>
   </details>

8. **Cilium NetworkPolicy の 'ingress' ルールは何を制御しますか？**
   - A) 選択した Pod に入るトラフィック
   - B) 選択した Pod から出るトラフィック
   - C) 選択した Pod 内のトラフィック
   - D) クラスター外部へのトラフィック

   <details>
   <summary>回答を表示</summary>
   <p><strong>回答</strong>: A) 選択した Pod に入るトラフィック</p>
   <p><strong>解説</strong>: Ingress ルールは、選択した Pod に入るトラフィックを制御します。</p>
   </details>

9. **Cilium NetworkPolicy の 'egress' ルールは何を制御しますか？**
   - A) 選択した Pod に入るトラフィック
   - B) 選択した Pod から出るトラフィック
   - C) 選択した Pod 内のトラフィック
   - D) クラスター外部からのトラフィック

   <details>
   <summary>回答を表示</summary>
   <p><strong>回答</strong>: B) 選択した Pod から出るトラフィック</p>
   <p><strong>解説</strong>: Egress ルールは、選択した Pod から出るトラフィックを制御します。</p>
   </details>

10. **Cilium NetworkPolicy における 'labels' フィールドの役割は何ですか？**
    - A) ポリシー適用対象の Pod を選択する
    - B) ポリシー自体の識別子
    - C) ポリシー適用対象の namespace を選択する
    - D) ポリシー適用対象の node を選択する

    <details>
    <summary>回答を表示</summary>
    <p><strong>回答</strong>: B) ポリシー自体の識別子</p>
    <p><strong>解説</strong>: labels フィールドはポリシー自体の識別子として使用され、他のポリシーがこのポリシーを参照する際に使用されます。</p>
    </details>

## 高度な Network Policy

11. **Cilium NetworkPolicy の 'toCIDR' ルールでは何を許可できますか？**
    - A) 特定の IP アドレス範囲へのトラフィック
    - B) 特定のドメイン名へのトラフィック
    - C) 特定の Service へのトラフィック
    - D) 特定の port へのトラフィック

    <details>
    <summary>回答を表示</summary>
    <p><strong>回答</strong>: A) 特定の IP アドレス範囲へのトラフィック</p>
    <p><strong>解説</strong>: toCIDR ルールは、特定の IP アドレス範囲（CIDR 表記）へのトラフィックを許可するために使用します。</p>
    </details>

12. **Cilium NetworkPolicy の 'toFQDNs' ルールでは何を許可できますか？**
    - A) 特定の IP アドレスへのトラフィック
    - B) 特定の port へのトラフィック
    - C) 特定のドメイン名へのトラフィック
    - D) 特定の protocol のトラフィック

    <details>
    <summary>回答を表示</summary>
    <p><strong>回答</strong>: C) 特定のドメイン名へのトラフィック</p>
    <p><strong>解説</strong>: toFQDNs ルールは特定のドメイン名（FQDN）へのトラフィックを許可し、Cilium は DNS ルックアップを監視して、それらのドメインの IP アドレスを動的に許可します。</p>
    </details>

13. **Cilium NetworkPolicy の 'toEntities' ルールにおける 'world' entity は何を意味しますか？**
    - A) クラスター内部のすべての endpoint
    - B) すべての外部ネットワーク
    - C) すべての node
    - D) すべての namespace

    <details>
    <summary>回答を表示</summary>
    <p><strong>回答</strong>: B) すべての外部ネットワーク</p>
    <p><strong>解説</strong>: 'world' entity は、クラスター外部のすべてのネットワークを指します。</p>
    </details>

14. **Cilium NetworkPolicy の 'toServices' ルールでは何を許可できますか？**
    - A) 特定の Kubernetes Service へのトラフィック
    - B) 特定の外部 Service へのトラフィック
    - C) 特定の port へのトラフィック
    - D) 特定の protocol のトラフィック

    <details>
    <summary>回答を表示</summary>
    <p><strong>回答</strong>: A) 特定の Kubernetes Service へのトラフィック</p>
    <p><strong>解説</strong>: toServices ルールは、特定の Kubernetes Service へのトラフィックを許可するために使用します。</p>
    </details>

15. **Cilium NetworkPolicy における 'nodeSelector' の役割は何ですか？**
    - A) ポリシー適用対象の Pod を選択する
    - B) ポリシー適用対象の node を選択する
    - C) ポリシー適用対象の namespace を選択する
    - D) ポリシー適用対象の Service を選択する

    <details>
    <summary>回答を表示</summary>
    <p><strong>回答</strong>: B) ポリシー適用対象の node を選択する</p>
    <p><strong>解説</strong>: nodeSelector は、ポリシーを適用する対象の node を選択するために使用します。</p>
    </details>

## L7 Policy

16. **Cilium の L7 HTTP policy では、どの属性をフィルタリングできますか？**
    - A) Path
    - B) Method
    - C) Headers
    - D) 上記すべて

    <details>
    <summary>回答を表示</summary>
    <p><strong>回答</strong>: D) 上記すべて</p>
    <p><strong>解説</strong>: Cilium の L7 HTTP policy では、Path、Method、Headers を含むさまざまな HTTP request 属性をフィルタリングできます。</p>
    </details>

17. **Cilium の L7 Kafka policy では、どの属性をフィルタリングできますか？**
    - A) Topic
    - B) API Key
    - C) Client ID
    - D) 上記すべて

    <details>
    <summary>回答を表示</summary>
    <p><strong>回答</strong>: D) 上記すべて</p>
    <p><strong>解説</strong>: Cilium の L7 Kafka policy では、Topic、API key、Client ID を含むさまざまな Kafka request 属性をフィルタリングできます。</p>
    </details>

18. **Cilium の L7 DNS policy における 'matchPattern' ルールでは何を許可できますか？**
    - A) 完全一致のドメイン名マッチング
    - B) ワイルドカードを使用したドメイン名パターンマッチング
    - C) IP アドレスマッチング
    - D) port 番号マッチング

    <details>
    <summary>回答を表示</summary>
    <p><strong>回答</strong>: B) ワイルドカードを使用したドメイン名パターンマッチング</p>
    <p><strong>解説</strong>: matchPattern ルールでは、ワイルドカード（*）を含むドメイン名パターンにマッチさせることができます。例: *.example.com</p>
    </details>

19. **Cilium の L7 gRPC policy では、どの属性をフィルタリングできますか？**
    - A) Method 名
    - B) Service 名
    - C) Metadata
    - D) 上記すべて

    <details>
    <summary>回答を表示</summary>
    <p><strong>回答</strong>: D) 上記すべて</p>
    <p><strong>解説</strong>: Cilium の L7 gRPC policy では、Method 名、Service 名、Metadata を含むさまざまな gRPC request 属性をフィルタリングできます。</p>
    </details>

20. **Cilium の L7 policy を適用するために必要な component は何ですか？**
    - A) kube-proxy
    - B) Envoy Proxy
    - C) NGINX Ingress Controller
    - D) HAProxy

    <details>
    <summary>回答を表示</summary>
    <p><strong>回答</strong>: B) Envoy Proxy</p>
    <p><strong>解説</strong>: Cilium は L7 policy を適用するために Envoy Proxy を使用します。</p>
    </details>
