# サービスとネットワークのクイズ

このクイズでは、Service の種類、Ingress、NetworkPolicy、Service ディスカバリーなど、Kubernetes のネットワーク概念への理解を確認します。

## 選択問題

1. Kubernetes でデフォルトの Service type はどれですか？
   - A) NodePort
   - B) LoadBalancer
   - C) ClusterIP
   - D) ExternalName

<details>

<summary>解答を表示</summary>

**答え: C) ClusterIP**

**解説:**
ClusterIP は Kubernetes のデフォルト Service type で、クラスター内からのみアクセスできる IP アドレスを提供します。これにより、クラスター内の他のアプリケーションから Service にアクセスできますが、クラスター外部からはアクセスできません。
</details>

2. クラスター外部からクラスター内の Service への HTTP／HTTPS ルートを公開する API オブジェクトはどれですか？
   - A) Service
   - B) Ingress
   - C) Endpoint
   - D) NetworkPolicy

<details>

<summary>解答を表示</summary>

**答え: B) Ingress**

**解説:**
Ingress は、クラスター外部からクラスター内の Service への HTTP／HTTPS ルートを公開する API オブジェクトです。ロードバランシング、SSL 終端、名前ベースの仮想ホスティングを提供します。
</details>

3. Kubernetes に組み込まれている Service ディスカバリー方式を2つ選んでください。
   - A) 環境変数
   - B) DNS
   - C) Service Mesh
   - D) ConfigMap

<details>

<summary>解答を表示</summary>

**答え: A) 環境変数、B) DNS**

**解説:**
Kubernetes が提供する主な Service ディスカバリー方式は、環境変数と DNS の2つです。ConfigMap は設定データの保存に使うもので、Service ディスカバリーの仕組みではありません。
</details>

4. すべてのノード上の特定ポートを通じて Service にアクセスできるようにする Service type はどれですか？
   - A) ClusterIP
   - B) NodePort
   - C) LoadBalancer
   - D) ExternalName

<details>

<summary>解答を表示</summary>

**答え: B) NodePort**

**解説:**
NodePort Service は、すべてのノード上の特定ポートを通じてアクセスできます。各ノードの IP アドレスと NodePort 値を使い、デフォルトでは 30000～32767 の範囲で割り当てられます。
</details>

5. クラスター IP を持たず、各 Pod の DNS レコードを作成する Service type はどれですか？
   - A) NodePort Service
   - B) LoadBalancer Service
   - C) Headless Service
   - D) ExternalName Service

<details>

<summary>解答を表示</summary>

**答え: C) Headless Service**

**解説:**
Headless Service は `clusterIP: None` を設定した Service です。クラスター IP を割り当てず、各 Pod の DNS レコードを作成します。Service の背後にある特定の Pod にクライアントが直接アクセスする必要がある場合に便利です。
</details>

6. Kubernetes で Pod 間の通信を制御する方法を提供するリソースはどれですか？
   - A) Service
   - B) Ingress
   - C) NetworkPolicy
   - D) EndpointSlice

<details>

<summary>解答を表示</summary>

**答え: C) NetworkPolicy**

**解説:**
NetworkPolicy を使うと Pod 間の通信を制御できます。NetworkPolicy により、Pod 間の ingress および egress トラフィックを制限できます。
</details>

7. Kubernetes クラスターの DNS サーバーとして使われるものはどれですか？
   - A) kube-dns
   - B) CoreDNS
   - C) NodeDNS
   - D) ClusterDNS

<details>

<summary>解答を表示</summary>

**答え: B) CoreDNS**

**解説:**
CoreDNS は Kubernetes クラスターで使われる柔軟かつ拡張可能な DNS サーバーです。Kubernetes 1.11 で GA となり、1.13 以降のデフォルト DNS サーバーです。
</details>

8. Cilium が利用する Linux カーネル技術はどれですか？
   - A) iptables
   - B) netfilter
   - C) eBPF
   - D) nftables

<details>

<summary>解答を表示</summary>

**答え: C) eBPF**

**解説:**
Cilium は Linux カーネルの eBPF (extended Berkeley Packet Filter) を利用し、コンテナ化されたアプリケーションにネットワーク接続、セキュリティ、可観測性を提供します。
</details>

9. 次のうち、Service Mesh の主な機能ではないものはどれですか？
   - A) Service ディスカバリー
   - B) 負荷分散
   - C) 永続ストレージの提供
   - D) 暗号化通信

<details>

<summary>解答を表示</summary>

**答え: C) 永続ストレージの提供**

**解説:**
Service Mesh はマイクロサービス間の通信を管理するインフラストラクチャ層です。Service ディスカバリー、負荷分散、暗号化、認証、認可、可観測性などを提供します。永続ストレージの提供は、Service Mesh の主な機能ではありません。
</details>

10. 外部 Service の別名を提供する Kubernetes の Service type はどれですか？
    - A) ClusterIP
    - B) NodePort
    - C) LoadBalancer
    - D) ExternalName

<details>

<summary>解答を表示</summary>

**答え: D) ExternalName**

**解説:**
ExternalName Service は外部 Service の別名を提供します。この Service type は、DNS 名を外部 Service の DNS 名に対応付けます。
</details>

## 短答問題

1. Service が参照する Pod の IP アドレスとポートを保存する Kubernetes リソースは何ですか？

<details>

<summary>解答を表示</summary>

**答え: EndpointSlice**

**解説:**
EndpointSlice は Service のバックエンドのアドレスとポートを保存します。selector を持つ Service の場合、controller が EndpointSlice を管理します。従来の Endpoints も同様の役割を果たしますが、v1.33 以降は非推奨です。
</details>

2. AWS EKS で Application Load Balancer をプロビジョニングする ingress controller の名前は何ですか？

<details>

<summary>解答を表示</summary>

**答え: AWS Load Balancer Controller**

**解説:**
AWS Load Balancer Controller は、AWS EKS で Application Load Balancer をプロビジョニングする ingress controller です。この controller は Kubernetes Ingress リソースを AWS ALB に変換します。
</details>

3. Pod が実行されているノードの DNS 設定を引き継ぐ Kubernetes の Pod DNS policy は何ですか？

<details>

<summary>解答を表示</summary>

**答え: Default**

**解説:**
`Default` DNS policy は、Pod が実行されているノードの DNS 設定を引き継ぎます。つまり、ノードの `/etc/resolv.conf` ファイルをそのまま Pod に使用します。
</details>

4. eBPF を使ってネットワークフローを監視し、問題の調査に役立てる Cilium の可観測性レイヤーは何ですか？

<details>

<summary>解答を表示</summary>

**答え: Hubble**

**解説:**
Hubble は eBPF を使ってネットワークフローを監視し、問題の調査に役立てる Cilium の可観測性レイヤーです。ネットワークフローの監視、サービス依存関係のマッピング、セキュリティ状況の観測、性能分析、トラブルシューティングなどの機能を提供します。
</details>

5. Endpoints に代わるスケーラブルなリソースで、大規模クラスターでより高い性能を提供するものは何ですか？

<details>

<summary>解答を表示</summary>

**答え: EndpointSlice**

**解説:**
EndpointSlice は Endpoints に代わるスケーラブルなリソースで、大規模クラスターの性能を向上させます。エンドポイントを複数の Slice に分割して管理するため、大規模な Service での性能改善につながります。
</details>

## 応用問題

1. Service Mesh (例: Istio) が Kubernetes 上のマイクロサービス間通信をどのように管理するか、またその利点を説明してください。

<details>

<summary>解答を表示</summary>

**答え:**

Service Mesh はマイクロサービス間の通信を管理するインフラストラクチャ層であり、次のように実装されます。

1. **Sidecar パターン**: Envoy などのプロキシコンテナを各 Pod に注入し、すべてのネットワークトラフィックを傍受して制御します。

2. **Control Plane**: Istio の istiod などの集中管理コンポーネントが、すべての sidecar proxy を構成、管理します。

3. **トラフィック管理**:

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews
spec:
  hosts:
    - reviews
  http:
    - match:
      - headers:
          end-user:
            exact: jason
      route:
        - destination:
            host: reviews
            subset: v2
    - route:
      - destination:
          host: reviews
          subset: v1
```

4. **セキュリティポリシー**:

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: httpbin
  namespace: foo
spec:
  selector:
    matchLabels:
      app: httpbin
  action: ALLOW
  rules:
    - from:
      - source:
          principals: ["cluster.local/ns/default/sa/sleep"]
      to:
        - operation:
            methods: ["GET"]
            paths: ["/info*"]
```

**利点:**

1. **トラフィック管理**: 高度なルーティング、負荷分散、トラフィック分割、カナリアデプロイなどをサポートします。

2. **セキュリティ**: サービス間の相互 TLS (mTLS) 暗号化、認証、認可を提供します。

3. **可観測性**: 分散トレーシング、メトリクス収集、ログによってサービス間通信を監視します。

4. **耐障害性**: サーキットブレーカー、リトライ、タイムアウト、障害注入を通じてシステムの耐障害性を高めます。

5. **ポリシー適用**: レート制限、クォータ、アクセス制御などのポリシーを適用できます。

6. **プラットフォーム非依存**: アプリケーションコードを変更せずに、これらの機能を追加できます。

Service Mesh は複雑なマイクロサービスアーキテクチャにおけるサービス間通信の複雑さを抽象化し、開発者がビジネスロジックに集中できるようにします。
</details>

2. Cilium の eBPF 技術が iptables などの従来のネットワーク方式と比べて提供する利点を説明し、AWS EKS で Cilium を最適化する方法を提案してください。

<details>

<summary>解答を表示</summary>

**答え:**

**Cilium の eBPF 技術の利点:**

1. **性能**: eBPF はカーネル内で直接動作し、パケット処理経路を最適化します。iptables はルール数が多い場合に線形検索を行いますが、eBPF はハッシュテーブルなどの効率的なデータ構造を利用できます。

2. **スケーラビリティ**: eBPF は大規模クラスターでも一貫した性能を維持します。iptables はルール数の増加に伴って急速に性能が低下します。

3. **プログラミング可能性**: eBPF は C に似た言語でプログラムでき、複雑なネットワーク処理ロジックを実装できます。iptables がサポートするのは限られたルールセットです。

4. **可観測性**: eBPF はネットワークフローの詳細なメトリクスを収集できるため、問題の調査や性能の最適化に役立ちます。

5. **L7 ポリシー**: Cilium は eBPF とユーザー空間の Envoy を組み合わせて HTTP／L7 を検査します。この処理のすべてがカーネル内の eBPF で行われるわけではありません。

**AWS EKS で Cilium を最適化する方法:**

1. **IPAM とルーティング方式を慎重に選択する**: AWS VPC CNI chaining では `aws-node` が引き続き必要です。Cilium ENI mode では EC2 権限が必要であり、ENI の所有権を制御しながら移行する必要があります。この章でレビュー済みの Helm 値と公式のインストール手順を使ってください。

2. **ノードのネットワーク容量を見積もる**: 実際のインスタンス ENI／IP 上限、サブネット容量、Pod 密度を確認します。インスタンスファミリー名だけでは十分な判断材料になりません。

3. **調整前に測定する**: 適切な場合、現在の Helm 値は `routingMode: native` と真偽値の `kubeProxyReplacement: true` を使います。削除された `tunnel=disabled` や `kubeProxyReplacement=strict` は使いません。kube-proxy の置き換えには API server への接続性と移行計画も必要です。DSR と XDP は、互換性のある AWS ネットワーク、NIC、カーネル、および測定による検証が必要です。すべての設定を有効にすることが普遍的な最適化策ではありません。

4. **Hubble を有効にする**:

```bash
cilium hubble enable --ui
```

Hubble を有効にすると、ネットワークフローの監視と問題の調査ができます。

5. **クラスター間接続**:
Cilium Cluster Mesh を構成し、複数の EKS クラスター間のネットワーク接続を実現します。

6. **監視との統合**:
Prometheus と Grafana を設定し、Cilium のメトリクスを収集、可視化します。

これらの最適化により、AWS EKS で Cilium の性能、セキュリティ、可観測性を高められます。
</details>

## まとめ

このクイズでは、Kubernetes Service とネットワークについて、Service type、Ingress、NetworkPolicy、Service ディスカバリー、CoreDNS、Cilium などを確認しました。これらの概念を理解して活用することで、安全でスケーラブルな Kubernetes アプリケーションを構築できます。
