# Cilium セキュリティと可視性クイズ

> **対応バージョン**: Cilium 1.17
> **最終更新**: February 22, 2026

## Network Policy の基本

1. **Kubernetes NetworkPolicy と Cilium NetworkPolicy の主な違いは何ですか？**
   - A) Cilium NetworkPolicy は L7 ポリシーをサポートしていない
   - B) Kubernetes NetworkPolicy は L7 ポリシーをサポートしていない
   - C) Cilium NetworkPolicy は特定の Node にのみ適用できる
   - D) Kubernetes NetworkPolicy の方が高いパフォーマンスを提供する

   <details>
   <summary>回答を表示</summary>
   <p><strong>回答</strong>: B) Kubernetes NetworkPolicy は L7 ポリシーをサポートしていない</p>
   <p><strong>解説</strong>: Kubernetes NetworkPolicy は L3/L4 レベルのポリシーのみをサポートしますが、Cilium NetworkPolicy は L3 から L7 までのより幅広いポリシーをサポートします。</p>
   </details>

2. **Cilium NetworkPolicy の API group は何ですか？**
   - A) networking.k8s.io
   - B) cilium.io
   - C) policy.cilium.io
   - D) network.cilium.io

   <details>
   <summary>回答を表示</summary>
   <p><strong>回答</strong>: B) cilium.io</p>
   <p><strong>解説</strong>: Cilium NetworkPolicy は cilium.io API group を使用します。</p>
   </details>

3. **Cilium NetworkPolicy における 'endpointSelector' の役割は何ですか？**
   - A) ポリシーが適用される対象 Pod を選択する
   - B) ポリシーが適用される対象 Node を選択する
   - C) ポリシーが適用される対象 namespace を選択する
   - D) ポリシーが適用される対象 Service を選択する

   <details>
   <summary>回答を表示</summary>
   <p><strong>回答</strong>: A) ポリシーが適用される対象 Pod を選択する</p>
   <p><strong>解説</strong>: endpointSelector は、ポリシーが適用される対象 Pod（endpoint）を選択するために使用します。</p>
   </details>

4. **Cilium NetworkPolicy の 'ingress' ルールは何を制御しますか？**
   - A) 選択した Pod への受信トラフィック
   - B) 選択した Pod からの送信トラフィック
   - C) 選択した Pod 内の内部トラフィック
   - D) cluster 外部へのトラフィック

   <details>
   <summary>回答を表示</summary>
   <p><strong>回答</strong>: A) 選択した Pod への受信トラフィック</p>
   <p><strong>解説</strong>: Ingress ルールは、選択した Pod への受信トラフィックを制御します。</p>
   </details>

5. **Cilium NetworkPolicy の 'egress' ルールは何を制御しますか？**
   - A) 選択した Pod への受信トラフィック
   - B) 選択した Pod からの送信トラフィック
   - C) 選択した Pod 内の内部トラフィック
   - D) cluster 外部からのトラフィック

   <details>
   <summary>回答を表示</summary>
   <p><strong>回答</strong>: B) 選択した Pod からの送信トラフィック</p>
   <p><strong>解説</strong>: Egress ルールは、選択した Pod からの送信トラフィックを制御します。</p>
   </details>

## L7 ポリシー

6. **Cilium の L7 HTTP ポリシーでフィルタリングできない属性はどれですか？**
   - A) Path
   - B) Method
   - C) Headers
   - D) Response Time

   <details>
   <summary>回答を表示</summary>
   <p><strong>回答</strong>: D) Response Time</p>
   <p><strong>解説</strong>: Cilium の L7 HTTP ポリシーでは、path、method、headers などの HTTP リクエスト属性をフィルタリングできますが、response time はフィルタリング対象ではありません。</p>
   </details>

7. **Cilium の L7 Kafka ポリシーでフィルタリングできる属性はどれですか？**
   - A) Topic
   - B) Partition
   - C) Offset
   - D) 上記すべて

   <details>
   <summary>回答を表示</summary>
   <p><strong>回答</strong>: A) Topic</p>
   <p><strong>解説</strong>: Cilium の L7 Kafka ポリシーでは、主に topic、API key、および類似の属性に基づいてフィルタリングできます。</p>
   </details>

8. **Cilium の L7 DNS ポリシーにおいて、'matchPattern' ルールで可能になることは何ですか？**
   - A) 完全一致の domain name マッチング
   - B) wildcard を使用した domain name パターンマッチング
   - C) IP address マッチング
   - D) port number マッチング

   <details>
   <summary>回答を表示</summary>
   <p><strong>回答</strong>: B) wildcard を使用した domain name パターンマッチング</p>
   <p><strong>解説</strong>: matchPattern ルールは、wildcard（*）を含む domain name パターンにマッチできます。例: *.example.com</p>
   </details>

9. **Cilium の L7 ポリシーを適用するために必要な component は何ですか？**
   - A) kube-proxy
   - B) Envoy proxy
   - C) NGINX ingress controller
   - D) HAProxy

   <details>
   <summary>回答を表示</summary>
   <p><strong>回答</strong>: B) Envoy proxy</p>
   <p><strong>解説</strong>: Cilium は L7 ポリシーを適用するために Envoy proxy を使用します。</p>
   </details>

10. **Cilium の L7 ポリシーでサポートされていない protocol はどれですか？**
    - A) HTTP
    - B) gRPC
    - C) Kafka
    - D) SMTP

    <details>
    <summary>回答を表示</summary>
    <p><strong>回答</strong>: D) SMTP</p>
    <p><strong>解説</strong>: Cilium は HTTP、gRPC、Kafka などの L7 protocol をサポートしますが、SMTP はデフォルトではサポートされていません。</p>
    </details>

## 暗号化とセキュリティ

11. **Cilium で network traffic の暗号化に使用できる protocol はどれですか？**
    - A) IPsec
    - B) WireGuard
    - C) A と B の両方
    - D) TLS

    <details>
    <summary>回答を表示</summary>
    <p><strong>回答</strong>: C) A と B の両方</p>
    <p><strong>解説</strong>: Cilium は IPsec と WireGuard の両方を使用して Node 間のトラフィックを暗号化できます。</p>
    </details>

12. **Cilium の暗号化機能はどのトラフィックを保護しますか？**
    - A) Node 間のトラフィックのみ
    - B) Pod 間のトラフィックのみ
    - C) Node から Pod へのトラフィックのみ
    - D) すべての cluster トラフィック

    <details>
    <summary>回答を表示</summary>
    <p><strong>回答</strong>: B) Pod 間のトラフィックのみ</p>
    <p><strong>解説</strong>: Cilium の暗号化機能は主に Pod 間のトラフィックを保護します。</p>
    </details>

13. **Cilium の Host Firewall 機能は何を保護しますか？**
    - A) Pod network interface
    - B) Host network interface
    - C) Service endpoint
    - D) Container runtime

    <details>
    <summary>回答を表示</summary>
    <p><strong>回答</strong>: B) Host network interface</p>
    <p><strong>解説</strong>: Cilium の Host Firewall は Host 自身の network interface を保護し、Host レベルのセキュリティを強化します。</p>
    </details>

14. **次の説明に該当する Cilium のセキュリティ機能はどれですか？「特定の application layer protocol の特定の field または pattern に基づいてトラフィックをフィルタリングする」**
    - A) Network policies
    - B) L7 policies
    - C) Encryption
    - D) Intrusion detection

    <details>
    <summary>回答を表示</summary>
    <p><strong>回答</strong>: B) L7 policies</p>
    <p><strong>解説</strong>: L7（application layer）ポリシーは、HTTP、gRPC、Kafka などの protocol 内の特定の field または pattern に基づいてトラフィックをフィルタリングできます。</p>
    </details>

15. **Cilium の Identity-based security model は何に基づいていますか？**
    - A) Pod name
    - B) Node name
    - C) Labels
    - D) IP address

    <details>
    <summary>回答を表示</summary>
    <p><strong>回答</strong>: C) Labels</p>
    <p><strong>解説</strong>: Cilium の Identity は Pod labels に基づいているため、IP address が変更されても一貫したセキュリティポリシーを適用できます。</p>
    </details>

## 可視性とモニタリング

16. **Hubble とは何ですか？**
    - A) Cilium の network visibility tool
    - B) Cilium の load balancer
    - C) Cilium の encryption protocol
    - D) Cilium の DNS server

    <details>
    <summary>回答を表示</summary>
    <p><strong>回答</strong>: A) Cilium の network visibility tool</p>
    <p><strong>解説</strong>: Hubble は、eBPF に基づいて network flow を監視および分析できる Cilium の network visibility tool です。</p>
    </details>

17. **Hubble UI で提供されない機能はどれですか？**
    - A) Service dependency map
    - B) Network flow visualization
    - C) Policy violation alert
    - D) Code deployment management

    <details>
    <summary>回答を表示</summary>
    <p><strong>回答</strong>: D) Code deployment management</p>
    <p><strong>解説</strong>: Hubble UI は Service dependency map、network flow visualization、policy violation alert を提供しますが、code deployment management は提供しません。</p>
    </details>

18. **Hubble CLI を使用して特定の Pod の network flow を監視する command は何ですか？**
    - A) `hubble observe --pod <pod-name>`
    - B) `hubble watch --pod <pod-name>`
    - C) `hubble monitor --pod <pod-name>`
    - D) `hubble inspect --pod <pod-name>`

    <details>
    <summary>回答を表示</summary>
    <p><strong>回答</strong>: A) <code>hubble observe --pod &lt;pod-name&gt;</code></p>
    <p><strong>解説</strong>: <code>hubble observe --pod &lt;pod-name&gt;</code> command を使用すると、特定の Pod の network flow をリアルタイムで監視できます。</p>
    </details>

19. **Hubble が収集しない metric はどれですか？**
    - A) HTTP status code
    - B) TCP connection status
    - C) Dropped packet count
    - D) Container CPU usage

    <details>
    <summary>回答を表示</summary>
    <p><strong>回答</strong>: D) Container CPU usage</p>
    <p><strong>解説</strong>: Hubble は network 関連の metric（HTTP status code、TCP connection status、dropped packet count など）を収集しますが、container CPU usage などの system metric は収集しません。</p>
    </details>

20. **Cilium を Prometheus と統合するにはどうすればよいですか？**
    - A) Cilium Operator に Prometheus annotation を追加する
    - B) Prometheus server に Cilium plugin をインストールする
    - C) Cilium 用の ServiceMonitor resource を作成する
    - D) Cilium dashboard を Prometheus に import する

    <details>
    <summary>回答を表示</summary>
    <p><strong>回答</strong>: C) Cilium 用の ServiceMonitor resource を作成する</p>
    <p><strong>解説</strong>: Prometheus Operator を使用する場合、Cilium 用の ServiceMonitor resource を作成することで Cilium metric を収集できます。</p>
    </details>
