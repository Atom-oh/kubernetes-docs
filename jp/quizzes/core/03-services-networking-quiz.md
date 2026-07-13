# Services and Networking Quiz

このクイズでは、Service type、Ingress、network policy、service discovery など、Kubernetes networking concepts の理解を確認します。

## Multiple Choice Questions

1. Kubernetes におけるデフォルトの Service type は何ですか？
   - A) NodePort
   - B) LoadBalancer
   - C) ClusterIP
   - D) ExternalName
   
<details>

<summary>答えを表示</summary>

**答え: C) ClusterIP**

**解説:**
ClusterIP は Kubernetes のデフォルト Service type で、cluster 内からのみアクセス可能な IP address を提供します。この Service により、cluster 内の他の application は Service にアクセスできますが、cluster 外部からはアクセスできません。
</details>

2. cluster 外部から cluster 内の Service へ HTTP および HTTPS route を公開する API object はどれですか？
   - A) Service
   - B) Ingress
   - C) Endpoint
   - D) NetworkPolicy
   
<details>

<summary>答えを表示</summary>

**答え: B) Ingress**

**解説:**
Ingress は、cluster 外部から cluster 内の Service へ HTTP および HTTPS route を公開する API object です。Ingress は load balancing、SSL termination、name-based virtual hosting を提供します。
</details>

3. 次のうち、Kubernetes が service discovery のために提供する方法ではないものはどれですか？
   - A) Environment variables
   - B) DNS
   - C) Service Mesh
   - D) ConfigMap
   
<details>

<summary>答えを表示</summary>

**答え: D) ConfigMap**

**解説:**
Kubernetes は主に 2 つの service discovery 方法、environment variables と DNS を提供します。ConfigMap は configuration data を保存するために使用されるもので、service discovery mechanism ではありません。
</details>

4. Kubernetes のどの Service type が、すべての node 上の特定の port を通じて Service にアクセスできるようにしますか？
   - A) ClusterIP
   - B) NodePort
   - C) LoadBalancer
   - D) ExternalName
   
<details>

<summary>答えを表示</summary>

**答え: B) NodePort**

**解説:**
NodePort Service は、すべての node 上の特定の port を通じて Service にアクセスできるようにします。この Service type では、各 node の IP address と NodePort value（デフォルトでは 30000-32767 の範囲で割り当て）を通じて Service にアクセスできます。
</details>

5. cluster IP を持たず、各 pod の DNS record を作成する Service type は何ですか？
   - A) NodePort service
   - B) LoadBalancer service
   - C) Headless service
   - D) ExternalName service
   
<details>

<summary>答えを表示</summary>

**答え: C) Headless service**

**解説:**
Headless service は `clusterIP: None` で構成された Service で、cluster IP を割り当てず、各 pod の DNS record を作成します。これは、client が Service の背後にある特定の pod に直接アクセスする必要がある場合に役立ちます。
</details>

6. Kubernetes で pod 間の通信を制御する方法を提供する resource はどれですか？
   - A) Service
   - B) Ingress
   - C) NetworkPolicy
   - D) EndpointSlice
   
<details>

<summary>答えを表示</summary>

**答え: C) NetworkPolicy**

**解説:**
NetworkPolicy は、pod 間の通信を制御する方法を提供します。network policy を使用すると、pod 間の ingress および egress traffic を制限できます。
</details>

7. Kubernetes cluster の DNS server として使用されるものは何ですか？
   - A) kube-dns
   - B) CoreDNS
   - C) NodeDNS
   - D) ClusterDNS
   
<details>

<summary>答えを表示</summary>

**答え: B) CoreDNS**

**解説:**
CoreDNS は、Kubernetes cluster の DNS server として使用される柔軟で拡張可能な DNS server です。Kubernetes 1.11 以降、CoreDNS がデフォルト DNS server として使用されています。
</details>

8. Cilium はどの Linux kernel technology を利用していますか？
   - A) iptables
   - B) netfilter
   - C) eBPF
   - D) nftables
   
<details>

<summary>答えを表示</summary>

**答え: C) eBPF**

**解説:**
Cilium は Linux kernel の eBPF (extended Berkeley Packet Filter) technology を利用して、containerized application に network connectivity、security、observability を提供します。
</details>

9. 次のうち、service mesh の主な機能ではないものはどれですか？
   - A) Service discovery
   - B) Load balancing
   - C) Providing persistent storage
   - D) Encrypted communication
   
<details>

<summary>答えを表示</summary>

**答え: C) Providing persistent storage**

**解説:**
service mesh は、microservices 間の通信を管理する infrastructure layer であり、service discovery、load balancing、encryption、authentication、authorization、observability などの機能を提供します。persistent storage の提供は、service mesh の主な機能ではありません。
</details>

10. Kubernetes のどの Service type が external service の alias を提供しますか？
    - A) ClusterIP
    - B) NodePort
    - C) LoadBalancer
    - D) ExternalName
    
<details>

<summary>答えを表示</summary>

**答え: D) ExternalName**

**解説:**
ExternalName Service は external service の alias を提供します。この Service type は、DNS name を external service の DNS name に mapping します。
</details>

## Short Answer Questions

1. Service によって指し示される pod の IP address と port を保存する Kubernetes の resource の名前は何ですか？

<details>

<summary>答えを表示</summary>

**答え: Endpoints**

**解説:**
Endpoints は、Service によって指し示される pod の IP address と port を保存する resource です。Service の selector に一致する pod がある場合、Kubernetes は endpoint object を自動的に作成して管理します。
</details>

2. AWS EKS で Application Load Balancer を provision するために使用される ingress controller の名前は何ですか？

<details>

<summary>答えを表示</summary>

**答え: AWS ALB Ingress Controller**

**解説:**
AWS ALB Ingress Controller は、AWS EKS で Application Load Balancer を provision するために使用される ingress controller です。この controller は Kubernetes Ingress resource を AWS ALB に変換します。
</details>

3. pod が実行されている node の DNS settings を継承する Kubernetes の pod DNS policy の名前は何ですか？

<details>

<summary>答えを表示</summary>

**答え: Default**

**解説:**
`Default` DNS policy は、pod が実行されている node の DNS settings を継承します。これは、node の `/etc/resolv.conf` file をそのまま pod に使用することを意味します。
</details>

4. eBPF を使用して network flow を監視し、問題を troubleshoot する Cilium の observability layer の名前は何ですか？

<details>

<summary>答えを表示</summary>

**答え: Hubble**

**解説:**
Hubble は、eBPF を使用して network flow を監視し、問題を troubleshoot する Cilium の observability layer です。Hubble は network flow monitoring、service dependency mapping、security observation、performance analysis、troubleshooting などの機能を提供します。
</details>

5. Endpoints に代わる scalable な resource で、大規模 cluster でより優れた performance を提供する Kubernetes の resource の名前は何ですか？

<details>

<summary>答えを表示</summary>

**答え: EndpointSlice**

**解説:**
EndpointSlice は Endpoints に代わる scalable な resource で、大規模 cluster でより優れた performance を提供します。EndpointSlice は、endpoint を複数の slice に分割して管理することで、大規模 Service の performance を向上させます。
</details>

## Advanced Questions

1. service mesh（例: Istio）が Kubernetes で microservices 間の通信を管理するためにどのように使用されるか、およびその利点を説明してください。

<details>

<summary>答えを表示</summary>

**答え:**

service mesh は microservices 間の通信を管理する infrastructure layer であり、次のような方法で実装されます。

1. **Sidecar pattern**: Proxy container（例: Envoy）が各 pod に注入され、すべての network traffic を intercept して制御します。

2. **Control plane**: 集中管理 component（例: Istio の istiod）がすべての sidecar proxy を構成して管理します。

3. **Traffic management**:
```yaml
apiVersion: networking.istio.io/v1alpha3
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

4. **Security policies**:
```yaml
apiVersion: security.istio.io/v1beta1
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

**Benefits**:

1. **Traffic management**: advanced routing、load balancing、traffic splitting、canary deployment などをサポートします。

2. **Security**: Service 間で mutual TLS (mTLS) encryption、authentication、authorization を提供します。

3. **Observability**: distributed tracing、metric collection、logging を通じて Service 間の通信を監視します。

4. **Resilience**: circuit breaker、retry、timeout、fault injection によって system resilience を向上させます。

5. **Policy enforcement**: rate limiting、quota、access control などの policy を適用できます。

6. **Platform independence**: application code を変更せずにこれらの機能を追加できます。

Service mesh は、複雑な microservice architecture における Service 間通信の複雑さを抽象化し、developer が business logic に集中できるようにします。
</details>

2. Cilium の eBPF technology が従来の networking approach（例: iptables）と比較して提供する利点を説明し、AWS EKS で Cilium を最適化する方法を提案してください。

<details>

<summary>答えを表示</summary>

**答え:**

**Benefits of Cilium's eBPF Technology**:

1. **Performance**: eBPF は kernel 内で直接実行され、packet processing path を最適化するため、iptables よりもはるかに高い performance を提供します。特に、iptables は rules が多い場合に linear search を実行しますが、eBPF は hash table のような効率的な data structure を使用できます。

2. **Scalability**: eBPF は大規模 cluster でも一貫した performance を維持します。iptables は rule 数が増えるにつれて performance が急速に低下します。

3. **Programmability**: eBPF は C-like language で program できるため、複雑な networking logic を実装できます。iptables は限られた rule set のみをサポートします。

4. **Observability**: eBPF は network flow に関する詳細な metrics を収集でき、troubleshooting と performance optimization に役立ちます。

5. **L7 awareness**: eBPF は application layer (L7) まで認識できるため、HTTP、gRPC、Kafka などの protocol に対して fine-grained policy を適用できます。

**Ways to Optimize Cilium in AWS EKS**:

1. **Enable AWS ENI mode**:
```bash
helm install cilium cilium/cilium \
   --namespace kube-system \
   --set eni.enabled=true \
   --set ipam.mode=eni \
   --set egressMasqueradeInterfaces=eth0 \
   --set tunnel=disabled
```
この configuration は AWS Elastic Network Interfaces (ENI) を活用して VPC-native IP address を pod に割り当て、overlay network なしで VPC-native networking を提供します。

2. **Node group optimization**:
  - 十分な ENI と IP address を提供する instance type（例: m5.large 以上）を選択します
  - 適切な最大 pod 数を構成します（instance type によって異なります）

3. **Performance optimization**:
```bash
helm install cilium cilium/cilium \
   --namespace kube-system \
   --set eni.enabled=true \
   --set ipam.mode=eni \
   --set tunnel=disabled \
   --set bpf.masquerade=true \
   --set kubeProxyReplacement=strict \
   --set loadBalancer.mode=dsr \
   --set loadBalancer.acceleration=native
```
この configuration は kube-proxy を置き換え、Direct Server Return (DSR) mode と native load balancing acceleration を有効にします。

4. **Enable Hubble**:
```bash
helm upgrade cilium cilium/cilium \
   --namespace kube-system \
   --reuse-values \
   --set hubble.enabled=true \
   --set hubble.relay.enabled=true \
   --set hubble.ui.enabled=true
```
Hubble を有効にして、network flow monitoring と troubleshooting capabilities を提供します。

5. **Cross-cluster connectivity**:
Cilium Cluster Mesh を構成して、複数の EKS cluster 間で seamless networking を提供します。

6. **Monitoring integration**:
Prometheus と Grafana を設定して、Cilium metrics を収集および visualize します。

これらの最適化により、AWS EKS における Cilium の performance、security、observability を最大化できます。
</details>

## Conclusion

このクイズを通じて、Kubernetes Service と networking の理解を確認しました。扱った concepts には、Service type、Ingress、network policy、service discovery、CoreDNS、Cilium が含まれます。これらの concepts を理解して活用することで、安全で scalable な Kubernetes application を構築できます。
