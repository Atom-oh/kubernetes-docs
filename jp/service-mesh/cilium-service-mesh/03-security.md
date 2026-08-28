# Cilium Service Mesh セキュリティ

> **サポート対象バージョン**: Cilium 1.16+, Kubernetes 1.28+
> **最終更新**: August 21, 2026

## 概要

Cilium のセキュリティには、明確に分かれた 3 つのレイヤーがあります。

1. **Identity ベースの認可:** Cilium Identity と eBPF policy が、通信を許可される workload を決定します。
2. **相互認証:** SPIFFE/SPIRE を使用する Cilium 相互認証は、application data connection とは分離された **帯域外（out-of-band）** ハンドシェイクを通じて peer identity を検証します。
3. **データ暗号化:** 確立済みの実装では、payload を暗号化するために WireGuard/IPsec を別途有効にする必要があります。サポートされている場合、native ztunnel mTLS preview は TLS により workload traffic を暗号化します。

これらの機能は組み合わせることができますが、Istio `PeerAuthentication` `STRICT` workload mTLS と自動的に同等になるわけではありません。Identity authorization、peer authentication、および転送中の encryption を個別の要件として評価してください。

## セキュリティアーキテクチャ

![Workload traffic は Cilium Identity と eBPF policy によって認可され、SPIFFE/SPIRE ベースの帯域外相互認証と WireGuard/IPsec または native ztunnel mTLS の payload encryption は別個のレイヤーとして機能します。](../../.gitbook/assets/en-service-mesh-cilium-service-mesh-03-security-0.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-cilium-service-mesh-03-security-0.html)

## 相互認証とデータ暗号化

### 確立済みの Cilium 相互認証

Cilium 相互認証は、接続が許可される前に両方の endpoint identity を検証しますが、確立済みの authentication handshake は application data path とは分離されています。`authentication.mode: required` のみで、既存の data connection の payload が TLS 暗号化されると想定しないでください。データの機密性が必要な場合は、[WireGuard または IPsec](https://docs.cilium.io/en/stable/security/network/encryption/) を設定してください。

![Pod A の接続要求は、policy により許可された data connection に至る前に、Cilium agent、SPIRE SVID authentication、および帯域外 auth handshake を通過します。](../../.gitbook/assets/en-service-mesh-cilium-service-mesh-03-security-1.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-cilium-service-mesh-03-security-1.html)

### ztunnel 経由の Native mTLS（2026 年更新）

2026 年 3 月に発表された Cilium native mTLS design は、ztunnel model を使用して、workload-mTLS path 上で相互認証と実際の payload encryption を組み合わせます。これは、確立済みの帯域外相互認証と WireGuard/IPsec とは異なる data plane です。この stack は、連携する次の 3 つの component で構成されます。

- **SPIRE** — workload identity と X.509 certificate を発行します（以下の SPIRE ベース設定と同じ役割）
- **Cilium** — outbound Pod traffic を port 15001 の ztunnel に透過的に redirect する iptables rule をインストールします
- **ztunnel** — 実際の mTLS handshake を実行し、Pod-to-Pod traffic を暗号化する、node ごとの proxy（Pod ごとの sidecar ではない）

これにより、TLS handshake は専用の node ごとの process で実行される一方で、「Pod ごとの sidecar なし、application の変更なし」という特性が維持されます。導入前に現在の preview status と platform support を確認してください。運用面で成熟した Istio `STRICT` mTLS path の自動的な代替と見なしてはいけません。

完全な architecture の解説については、[native mTLS に関する Cilium のブログ記事](https://cilium.io/blog/2026/03/23/native-mtls-cilium/)を参照してください。

### mTLS に Cilium と Istio のどちらを選択するか

- 要件が、すでに Cilium を実行している data plane における効率的な L3/L4 Identity policy と network encryption である場合は、**Cilium を選択**してください。追加の sidecar や service ごとの proxy を運用する必要がなく、CiliumNetworkPolicy/CiliumClusterwideNetworkPolicy で必要な access rule をすでに表現できます。
- 要件が `PeerAuthentication` `STRICT` semantics を持つ成熟した workload-certificate mTLS、または Istio native の L7 policy/routing（[sidecar と ambient の比較](../istio/comparison/03-sidecar-vs-ambient.md)で扱う `AuthorizationPolicy`、retry、traffic-shifting rule のようなもの）である場合は、**Istio を選択**してください。Cilium の確立済み相互認証は帯域外であり、その policy surface を備えていません。
- encryption layer だけで判断しないでください。Cilium の WireGuard/IPsec と native ztunnel mTLS preview はどちらも payload を暗号化しますが、どちらも単独では、workload identity issuance、policy enforcement、payload encryption を 1 つの switch で組み合わせる Istio `PeerAuthentication` `STRICT` を再現しません。

### SPIRE ベースの相互認証設定

```yaml
# values.yaml - SPIRE integration configuration
authentication:
  mutual:
    spire:
      enabled: true
      install:
        enabled: true
        namespace: cilium-spire

        server:
          # SPIRE Server configuration
          replicas: 1
          dataStorage:
            enabled: true
            size: 1Gi
            storageClass: gp3

          # Trust Domain configuration
          trustDomain: cluster.local

          # CA configuration
          ca:
            # Use internal CA
            keyType: ec-p256
            ttl: 24h

          # Node Attestor configuration
          nodeAttestor:
            k8sPsat:
              enabled: true

        agent:
          # SPIRE Agent configuration
          socketPath: /run/spire/sockets/agent.sock

          # Workload Attestor configuration
          workloadAttestor:
            k8s:
              enabled: true
              disableContainerSelectors: false
```

### 相互認証 policy の適用

```yaml
# Require mutual authentication cluster-wide
apiVersion: cilium.io/v2
kind: CiliumClusterwideNetworkPolicy
metadata:
  name: enforce-mtls
spec:
  endpointSelector: {}
  authentication:
  - mode: required
```

### Namespace ごとの相互認証

```yaml
# Apply mutual authentication to a specific namespace
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: namespace-mtls
  namespace: production
spec:
  endpointSelector: {}
  ingress:
  - fromEndpoints:
    - {}
    authentication:
    - mode: required
  egress:
  - toEndpoints:
    - {}
    authentication:
    - mode: required
```

### Service ごとの相互認証

```yaml
# Enforce mutual authentication between specific services
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: service-mtls
  namespace: default
spec:
  endpointSelector:
    matchLabels:
      app: backend

  ingress:
  - fromEndpoints:
    - matchLabels:
        app: frontend
    authentication:
    - mode: required
    toPorts:
    - ports:
      - port: "8080"
        protocol: TCP
```

## CiliumNetworkPolicy L7 ルール

### HTTP L7 セキュリティ policy

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: http-security-policy
  namespace: default
spec:
  endpointSelector:
    matchLabels:
      app: api-server

  ingress:
  # Read-only access
  - fromEndpoints:
    - matchLabels:
        role: reader
    toPorts:
    - ports:
      - port: "8080"
        protocol: TCP
      rules:
        http:
        - method: GET
          path: "/api/.*"

  # Admin access
  - fromEndpoints:
    - matchLabels:
        role: admin
    toPorts:
    - ports:
      - port: "8080"
        protocol: TCP
      rules:
        http:
        - method: ".*"
          path: "/api/.*"
          headers:
          - "Authorization: Bearer .*"

  # Health checks
  - fromEndpoints:
    - matchLabels:
        app: monitoring
    toPorts:
    - ports:
      - port: "8080"
        protocol: TCP
      rules:
        http:
        - method: GET
          path: "/health"
        - method: GET
          path: "/metrics"
```

### Kafka L7 セキュリティ policy

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: kafka-security
  namespace: kafka
spec:
  endpointSelector:
    matchLabels:
      app: kafka

  ingress:
  # Producer - allow writing to specific topics only
  - fromEndpoints:
    - matchLabels:
        role: producer
    toPorts:
    - ports:
      - port: "9092"
        protocol: TCP
      rules:
        kafka:
        - apiKey: produce
          topic: "orders"
        - apiKey: produce
          topic: "events"
        - apiKey: metadata

  # Consumer - allow reading from specific topics only
  - fromEndpoints:
    - matchLabels:
        role: consumer
    toPorts:
    - ports:
      - port: "9092"
        protocol: TCP
      rules:
        kafka:
        - apiKey: fetch
          topic: "orders"
        - apiKey: fetch
          topic: "events"
        - apiKey: listoffsets
          topic: "orders"
        - apiKey: listoffsets
          topic: "events"
        - apiKey: metadata
        - apiKey: findcoordinator
        - apiKey: joingroup
        - apiKey: heartbeat
        - apiKey: leavegroup
        - apiKey: syncgroup
        - apiKey: offsetcommit
          topic: "orders"
        - apiKey: offsetfetch
          topic: "orders"
```

### DNS L7 セキュリティ policy

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: dns-security
  namespace: default
spec:
  endpointSelector:
    matchLabels:
      app: web-application

  egress:
  # Restrict DNS queries
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
        k8s-app: kube-dns
    toPorts:
    - ports:
      - port: "53"
        protocol: UDP
      rules:
        dns:
        # Allow internal services only
        - matchPattern: "*.svc.cluster.local"
        # Allow specific external domains only
        - matchName: "api.stripe.com"
        - matchName: "api.aws.amazon.com"
        - matchPattern: "*.s3.amazonaws.com"

  # Egress to allowed external services
  - toFQDNs:
    - matchName: "api.stripe.com"
    - matchName: "api.aws.amazon.com"
    - matchPattern: "*.s3.amazonaws.com"
    toPorts:
    - ports:
      - port: "443"
        protocol: TCP
```

## 相互認証

> このセクションでは `authentication.mode` policy の例を設定します。相互認証でカバーされることとカバーされないこと（payload encryption から分離された帯域外 handshake）については、上記の[相互認証とデータ暗号化](#mutual-authentication-and-data-encryption)を参照してください。

### 認証モード

```yaml
# Cilium authentication mode options

# 1. disabled - no authentication (default)
authentication:
- mode: disabled

# 2. optional - use authentication if possible, otherwise allow
authentication:
- mode: optional

# 3. required - authentication required
authentication:
- mode: required

# 4. test-always-fail - for testing (always fails)
authentication:
- mode: test-always-fail
```

### 相互認証 policy の例

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: mutual-auth-policy
  namespace: production
spec:
  endpointSelector:
    matchLabels:
      app: secure-service

  ingress:
  # Allow authenticated clients only
  - fromEndpoints:
    - matchLabels:
        app: trusted-client
    authentication:
    - mode: required
    toPorts:
    - ports:
      - port: "443"
        protocol: TCP

  # Optional authentication for monitoring
  - fromEndpoints:
    - matchLabels:
        app: prometheus
    authentication:
    - mode: optional
    toPorts:
    - ports:
      - port: "9090"
        protocol: TCP
```

### SPIFFE ID ベースの認証

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: spiffe-auth
  namespace: default
spec:
  endpointSelector:
    matchLabels:
      app: database

  ingress:
  # Allow specific SPIFFE ID only
  - fromEndpoints:
    - matchLabels:
        app: backend
    authentication:
    - mode: required
      # SPIFFE ID verification is performed automatically
      # spiffe://cluster.local/ns/default/sa/backend
```

## 暗号化

> このセクションでは、上記の[相互認証とデータ暗号化](#mutual-authentication-and-data-encryption)で概念的に導入した payload-encryption mechanism（WireGuard/IPsec）を設定します。暗号化は相互認証とは別の選択であり、その副産物ではありません。

### WireGuard 透過的暗号化

WireGuard は、Linux kernel level ですべての Pod-to-Pod traffic を暗号化します。

```yaml
# values.yaml - Enable WireGuard
encryption:
  enabled: true
  type: wireguard

  wireguard:
    # Userspace fallback (when kernel support unavailable)
    userspaceFallback: true

  # Node-to-node encryption
  nodeEncryption: true
```

```bash
# Check WireGuard status
cilium status | grep Encryption

# Expected output
Encryption:              Wireguard  [NodeEncryption: Enabled, cilium_wg0 (Pubkey: xxx, Port: 51871, Peers: 2)]

# Check WireGuard peers
cilium encrypt status

# Expected output
Encryption: Wireguard
Keys in use: 1
Max Seq. Number: 0x0
Errors: 0
```

#### WireGuard アーキテクチャ

![Node A と Node B 上の cilium_wg0 WireGuard interface は、ChaCha20-Poly1305 で暗号化された tunnel を介して Pod-to-Pod traffic を運びます。](../../.gitbook/assets/en-service-mesh-cilium-service-mesh-03-security-2.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-cilium-service-mesh-03-security-2.html)

### IPsec 暗号化

```yaml
# values.yaml - Enable IPsec
encryption:
  enabled: true
  type: ipsec

  ipsec:
    # IPsec interface
    interface: ""

    # Key rotation interval
    keyRotationDuration: "5m"

    # Encryption interface
    mountPath: /etc/ipsec

# Generate IPsec key
# kubectl create secret generic -n kube-system cilium-ipsec-keys \
#   --from-literal=keys="3 rfc4106(gcm(aes)) $(openssl rand -hex 20) 128"
```

### 暗号化の比較

| 機能 | WireGuard | IPsec |
|---------|-----------|-------|
| パフォーマンス | 非常に高い | 高い |
| 設定の複雑さ | 低い | 中程度 |
| Kernel サポート | 5.6+（組み込み） | 全バージョン |
| 暗号化アルゴリズム | ChaCha20Poly1305 | AES-GCM など |
| Key 管理 | 自動 | 手動/自動 |
| 標準 | 非標準 | IETF 標準 |

## Identity ベースのセキュリティ

### Cilium Identity

Cilium は IP ではなく Identity に基づいて security policy を適用します。

![Pod の label set は数値 Identity に hash 化され、それを使用して eBPF policy map を検索し、allow/deny decision を生成します。](../../.gitbook/assets/en-service-mesh-cilium-service-mesh-03-security-3.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-cilium-service-mesh-03-security-3.html)

### Identity コンポーネント

```bash
# Identity label composition
# - k8s:io.kubernetes.pod.namespace
# - k8s:io.cilium.k8s.policy.serviceaccount
# - k8s:app
# - k8s:version
# - Other user-defined labels

# List identities
cilium identity list

# Example output
IDENTITY   LABELS
1          reserved:host
2          reserved:world
3          reserved:unmanaged
4          reserved:health
5          reserved:init
6          reserved:remote-node
12345      k8s:app=frontend,k8s:io.kubernetes.pod.namespace=default
12346      k8s:app=backend,k8s:io.kubernetes.pod.namespace=default
```

### Identity ベースの policy

```yaml
# Identity-based network policy
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: identity-based-policy
  namespace: default
spec:
  endpointSelector:
    matchLabels:
      app: backend

  ingress:
  # Allow only Pods with specific labels (Identity)
  - fromEndpoints:
    - matchLabels:
        app: frontend
        environment: production
    toPorts:
    - ports:
      - port: "8080"

  # Allow specific service from another namespace
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: monitoring
        app: prometheus
    toPorts:
    - ports:
      - port: "9090"
```

### IP と Identity の比較

![IP ベースの security では Pod IP が変更されるたびに policy update が必要ですが、Identity ベースの security は IP churn の影響を受けません。](../../.gitbook/assets/en-service-mesh-cilium-service-mesh-03-security-4.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-cilium-service-mesh-03-security-4.html)

## 外部 PKI 統合

### cert-manager 統合

```yaml
# Certificate management with cert-manager
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: cilium-ca-issuer
spec:
  ca:
    secretName: cilium-ca-secret
---
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: cilium-spire-ca
  namespace: cilium-spire
spec:
  secretName: spire-ca-secret
  duration: 8760h  # 1 year
  renewBefore: 720h  # Renew 30 days before expiry
  isCA: true
  privateKey:
    algorithm: ECDSA
    size: 256
  subject:
    organizations:
    - Cilium
  commonName: SPIRE CA
  issuerRef:
    name: cilium-ca-issuer
    kind: ClusterIssuer
```

### Vault 統合

```yaml
# Use Vault as CA in SPIRE
apiVersion: v1
kind: ConfigMap
metadata:
  name: spire-server-config
  namespace: cilium-spire
data:
  server.conf: |
    server {
      trust_domain = "cluster.local"

      ca_subject = {
        country = ["US"]
        organization = ["MyOrg"]
        common_name = ""
      }

      # Vault UpstreamAuthority
      UpstreamAuthority "vault" {
        plugin_data {
          vault_addr = "https://vault.vault.svc:8200"
          pki_mount_path = "pki"
          ca_cert_path = "/vault/ca/ca.crt"
          token_path = "/vault/token/token"
        }
      }
    }
```

## Zero Trust ネットワーキング

### Default Deny policy

```yaml
# Cluster-wide default deny
apiVersion: cilium.io/v2
kind: CiliumClusterwideNetworkPolicy
metadata:
  name: default-deny
spec:
  endpointSelector: {}
  ingress:
  - fromEndpoints:
    - matchLabels:
        reserved:host: ""
  egress:
  - toEndpoints:
    - matchLabels:
        reserved:host: ""
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
        k8s-app: kube-dns
    toPorts:
    - ports:
      - port: "53"
        protocol: UDP
```

### 最小権限アクセス

```yaml
# Production namespace security policy
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: production-security
  namespace: production
spec:
  # Apply to all Pods
  endpointSelector: {}

  # Default deny
  ingressDeny:
  - fromEntities:
    - world

  # Allow rules
  ingress:
  # Allow communication within same namespace
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: production
    authentication:
    - mode: required

  # Allow access from Ingress Controller
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: ingress-nginx
        app: nginx-ingress
    toPorts:
    - ports:
      - port: "8080"

  egress:
  # DNS
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
        k8s-app: kube-dns
    toPorts:
    - ports:
      - port: "53"
        protocol: UDP

  # Communication within same namespace
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: production
    authentication:
    - mode: required
```

### マイクロセグメンテーション

```yaml
# 3-tier architecture security
---
# Frontend policy
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: frontend-policy
  namespace: app
spec:
  endpointSelector:
    matchLabels:
      tier: frontend

  ingress:
  - fromEntities:
    - world
    toPorts:
    - ports:
      - port: "443"

  egress:
  - toEndpoints:
    - matchLabels:
        tier: backend
    toPorts:
    - ports:
      - port: "8080"
---
# Backend policy
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: backend-policy
  namespace: app
spec:
  endpointSelector:
    matchLabels:
      tier: backend

  ingress:
  - fromEndpoints:
    - matchLabels:
        tier: frontend
    toPorts:
    - ports:
      - port: "8080"
    authentication:
    - mode: required

  egress:
  - toEndpoints:
    - matchLabels:
        tier: database
    toPorts:
    - ports:
      - port: "5432"
    authentication:
    - mode: required
---
# Database policy
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: database-policy
  namespace: app
spec:
  endpointSelector:
    matchLabels:
      tier: database

  ingress:
  - fromEndpoints:
    - matchLabels:
        tier: backend
    toPorts:
    - ports:
      - port: "5432"
    authentication:
    - mode: required

  # No external egress (data exfiltration prevention)
  egressDeny:
  - toEntities:
    - world
```

## セキュリティ監査とモニタリング

### Policy Audit Mode

```yaml
# Test policy in audit mode
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: audit-policy
  namespace: default
  annotations:
    # Audit mode - logging only, no blocking
    cilium.io/audit-mode: "true"
spec:
  endpointSelector:
    matchLabels:
      app: backend

  ingress:
  - fromEndpoints:
    - matchLabels:
        app: frontend
    toPorts:
    - ports:
      - port: "8080"
```

### Policy 違反のモニタリング

```bash
# Observe policy violations with Hubble
hubble observe --verdict DROPPED

# Dropped traffic in specific namespace
hubble observe --namespace production --verdict DROPPED

# Policy violation statistics
hubble observe --verdict DROPPED -o json | jq -r '.flow | "\(.source.namespace)/\(.source.pod_name) -> \(.destination.namespace)/\(.destination.pod_name)"' | sort | uniq -c | sort -rn
```

### Prometheus メトリクス

```yaml
# Collect security-related metrics
hubble:
  metrics:
    enabled:
    - dns
    - drop
    - flow
    - http
    - icmp
    - port-distribution
    - tcp

# Useful metrics
# - cilium_drop_count_total: Packets dropped by policy
# - cilium_policy_verdict: Policy decisions (allow/deny)
# - cilium_forward_count_total: Forwarded packets
```

## 次のステップ

- [Observability](./04-observability.md): Hubble を使用したセキュリティモニタリング
- [Ingress & Gateway](./05-ingress-gateway.md): 外部 traffic のセキュリティ
- [ベストプラクティス](./06-best-practices.md): 本番環境のセキュリティ設定

## 参考資料

- [Cilium Network Policy ドキュメント](https://docs.cilium.io/en/stable/security/policy/)
- [Cilium 相互認証](https://docs.cilium.io/en/stable/network/servicemesh/mutual-authentication/)
- [Cilium 暗号化ドキュメント](https://docs.cilium.io/en/stable/security/network/encryption/)
- [Cilium Native mTLS](https://cilium.io/blog/2026/03/23/native-mtls-cilium/)
- [Istio PeerAuthentication](https://istio.io/latest/docs/reference/config/security/peer_authentication/)
- [SPIFFE/SPIRE ドキュメント](https://spiffe.io/docs/latest/)
- [Zero Trust Architecture - NIST](https://www.nist.gov/publications/zero-trust-architecture)
