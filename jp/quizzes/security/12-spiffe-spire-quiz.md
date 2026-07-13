# SPIFFE/SPIRE クイズ

以下の問題で、SPIFFE/SPIRE workload identity に関する理解を確認しましょう。

---

## 問題

### 1. SPIFFE ID の正しい形式はどれですか？

- A) spiffe://workload/trust-domain/path
- B) spiffe://trust-domain/path
- C) trust-domain://spiffe/path
- D) https://spiffe/trust-domain/path

<details>
<summary>答えを表示</summary>

**回答: B) spiffe://trust-domain/path**

**解説:**
SPIFFE ID の形式は、次の構造を持つ URI です。

```
spiffe://trust-domain/path
```

例:
```
spiffe://example.org/ns/production/sa/frontend
spiffe://cluster.local/k8s/ns/default/pod/nginx-abc123
spiffe://acme.com/region/us-east-1/service/payment
```

構成要素:
- **spiffe://**: 必須の scheme
- **trust-domain**: 組織の identity namespace（例: example.org）
- **path**: workload の階層的な識別子

</details>

---

### 2. X.509-SVID と JWT-SVID の主な違いは何ですか？

- A) X.509-SVID は authentication 用、JWT-SVID は authorization 用
- B) X.509-SVID は mTLS connections 用、JWT-SVID は API authentication 用
- C) 機能は同一である
- D) X.509-SVID は JWT-SVID より早く期限切れになる

<details>
<summary>答えを表示</summary>

**回答: B) X.509-SVID は mTLS connections 用、JWT-SVID は API authentication 用**

**解説:**
SPIFFE は 2 種類の SVID（SPIFFE Verifiable Identity Document）をサポートしています。

**X.509-SVID:**
- mTLS（mutual TLS）connections に使用される
- SAN（Subject Alternative Name）の URI に SPIFFE ID を含む
- 長期間有効（数時間から数日）
- 最適な用途: Service-to-service mTLS

**JWT-SVID:**
- API authentication（HTTP headers）に使用される
- `sub` claim に SPIFFE ID を含む
- 短期間有効（数分）
- 最適な用途: REST APIs、serverless、cross-network calls

```yaml
# X.509-SVID use case
service-a --mTLS--> service-b

# JWT-SVID use case
service-a --HTTP + JWT Bearer--> API Gateway
```

</details>

---

### 3. SPIRE Server の主な役割は何ですか？

- A) workloads を実行する
- B) SVIDs を発行し、workload registration を管理する
- C) traffic の load balancing を行う
- D) application secrets を保存する

<details>
<summary>答えを表示</summary>

**回答: B) SVIDs を発行し、workload registration を管理する**

**解説:**
SPIRE Server の責務:

```
┌─────────────────────────────────────────────┐
│              SPIRE Server                    │
├─────────────────────────────────────────────┤
│  - Manages trust domain CA                   │
│  - Issues X.509 and JWT SVIDs               │
│  - Stores workload registration entries     │
│  - Performs node attestation                │
│  - Maintains federation relationships       │
└─────────────────────────────────────────────┘
                    │
         ┌─────────┴─────────┐
         ▼                   ▼
   SPIRE Agent          SPIRE Agent
     (Node 1)             (Node 2)
```

主な機能:
- trust domain の Certificate Authority
- workload entries の Registration API
- node と workload の attestation verification
- SVID の signing と rotation

</details>

---

### 4. SPIRE Agent の主な役割は何ですか？

- A) cluster networking を管理する
- B) nodes 上で実行され、workloads を attest し、SVIDs を local に配布する
- C) cluster secrets を保存する
- D) pods を scheduling する

<details>
<summary>答えを表示</summary>

**回答: B) nodes 上で実行され、workloads を attest し、SVIDs を local に配布する**

**解説:**
SPIRE Agent は各 node 上で DaemonSet として実行されます。

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: spire-agent
  namespace: spire
spec:
  template:
    spec:
      containers:
      - name: spire-agent
        image: ghcr.io/spiffe/spire-agent:1.8
        volumeMounts:
        - name: spire-agent-socket
          mountPath: /run/spire/sockets
```

Agent の責務:
- SPIRE Server に対して attest する（node attestation）
- local workload identity を検証する（workload attestation）
- Server から SVIDs を取得して cache する
- local workloads に Workload API（Unix domain socket）を公開する
- SVID rotation を処理する

</details>

---

### 5. Amazon EKS で推奨される node attestation method はどれですか？

- A) aws_iid
- B) k8s_sat
- C) k8s_psat
- D) join_token

<details>
<summary>答えを表示</summary>

**回答: C) k8s_psat**

**解説:**
Kubernetes の node attestation methods:

**k8s_psat (Projected Service Account Token)** - EKS で推奨:
```yaml
# SPIRE Server configuration
nodeAttestor "k8s_psat" {
    plugin_data {
        clusters = {
            "eks-cluster" = {
                service_account_allow_list = ["spire:spire-agent"]
                kube_config_file = ""
                allowed_node_label_keys = ["topology.kubernetes.io/zone"]
            }
        }
    }
}
```

EKS で k8s_psat を使う理由:
- projected service account tokens を使用する（より secure）
- tokens は audience-bound かつ time-limited
- EKS OIDC provider と連携する
- agents に cloud provider credentials が不要

代替手段:
- **k8s_sat**: Legacy service account tokens（より secure ではない）
- **aws_iid**: EC2 instance identity（non-EKS 向け）

</details>

---

### 6. k8s workload attestation はどの selector types をサポートしていますか？

- A) Container image のみ
- B) Namespace、service account、pod labels、container image
- C) IP address のみ
- D) Node name のみ

<details>
<summary>答えを表示</summary>

**回答: B) Namespace、service account、pod labels、container image**

**解説:**
Kubernetes workload attestation selectors:

```bash
# Create registration entry with selectors
spire-server entry create \
    -spiffeID spiffe://example.org/ns/production/sa/frontend \
    -parentID spiffe://example.org/agent/node1 \
    -selector k8s:ns:production \
    -selector k8s:sa:frontend \
    -selector k8s:pod-label:app:frontend \
    -selector k8s:container-image:nginx:1.25
```

利用可能な selectors:
| Selector | Example | Description |
|----------|---------|-------------|
| k8s:ns | k8s:ns:production | Namespace |
| k8s:sa | k8s:sa:frontend | ServiceAccount |
| k8s:pod-label | k8s:pod-label:app:web | Pod labels |
| k8s:container-image | k8s:container-image:nginx | Container image |
| k8s:pod-name | k8s:pod-name:nginx-xyz | Specific pod |
| k8s:pod-uid | k8s:pod-uid:abc-123 | Pod UID |

</details>

---

### 7. SPIFFE CSI Driver の目的は何ですか？

- A) persistent volumes を管理する
- B) sidecars なしで SVIDs を pods に直接 mount する
- C) node storage を暗号化する
- D) Network policy enforcement

<details>
<summary>答えを表示</summary>

**回答: B) sidecars なしで SVIDs を pods に直接 mount する**

**解説:**
SPIFFE CSI Driver は、SVID delivery に対して sidecar-less なアプローチを提供します。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: my-workload
spec:
  containers:
  - name: app
    image: my-app:latest
    volumeMounts:
    - name: spiffe
      mountPath: /run/spiffe/certs
      readOnly: true
  volumes:
  - name: spiffe
    csi:
      driver: "csi.spiffe.io"
      readOnly: true
```

利点:
- sidecar container が不要
- SVIDs が自動的に files として mount される
- 透過的な certificate rotation
- pod の複雑さを軽減
- file-based certificates を期待する任意の application で動作する

CSI driver は SPIRE Agent と通信して SVIDs を取得し、mount します。

</details>

---

### 8. SPIFFE Federation は何を可能にしますか？

- A) Database replication
- B) 別々の SPIFFE deployments 間での cross-trust-domain communication
- C) clusters をまたいだ Pod scheduling
- D) Secret synchronization

<details>
<summary>答えを表示</summary>

**回答: B) 別々の SPIFFE deployments 間での cross-trust-domain communication**

**解説:**
SPIFFE Federation により、異なる trust domains の workloads が認証できるようになります。

```
┌─────────────────────┐      Federation      ┌─────────────────────┐
│  Trust Domain A     │◄──────────────────►│  Trust Domain B      │
│  example.org        │     Bundle Exchange │  partner.com         │
├─────────────────────┤                      ├─────────────────────┤
│  spiffe://example.  │                      │  spiffe://partner.   │
│  org/service/api    │   ─── mTLS ───►     │  com/service/db      │
└─────────────────────┘                      └─────────────────────┘
```

設定:
```yaml
# SPIRE Server federation config
federatesWith "partner.com" {
    bundleEndpointURL = "https://spire.partner.com:8443"
    bundleEndpointProfile "https_spiffe" {
        endpointSPIFFEID = "spiffe://partner.com/spire/server"
    }
}
```

ユースケース:
- Multi-cloud deployments
- Partner integrations
- Mergers and acquisitions
- Zero-trust cross-organization communication

</details>

---

### 9. SPIFFE/SPIRE は IAM Roles for Service Accounts（IRSA）と比べてどうですか？

- A) IRSA は platform-agnostic、SPIFFE は AWS-only
- B) SPIFFE は platform-agnostic identity を提供し、IRSA は AWS-specific
- C) これらは同一の technologies である
- D) SPIFFE は Azure でのみ動作する

<details>
<summary>答えを表示</summary>

**回答: B) SPIFFE は platform-agnostic identity を提供し、IRSA は AWS-specific**

**解説:**
SPIFFE/SPIRE と IRSA の比較:

| Feature | SPIFFE/SPIRE | IRSA |
|---------|--------------|------|
| Platform | Any (multi-cloud) | AWS only |
| Identity Format | SPIFFE ID (URI) | IAM Role ARN |
| Credential Type | X.509/JWT SVID | AWS STS token |
| Service-to-Service | Native mTLS | Not supported |
| AWS Service Access | Via JWT exchange | Direct |
| Setup Complexity | Higher | Lower (EKS native) |

それぞれを使う場面:
- **IRSA**: AWS services にアクセスする AWS-native workloads
- **SPIFFE/SPIRE**: Multi-cloud、service mesh、mTLS requirements

両方を併用できます。
```
Pod --SPIFFE--> Service Mesh (mTLS)
Pod --IRSA--> AWS Services (S3, DynamoDB)
```

</details>

---

### 10. SPIFFE で trust domains を naming する best practices は何ですか？

- A) random strings を使用する
- B) IP addresses を使用する
- C) 組織が管理する DNS-style names を使用する
- D) sequential numbers を使用する

<details>
<summary>答えを表示</summary>

**回答: C) 組織が管理する DNS-style names を使用する**

**解説:**
Trust domain naming の best practices:

**推奨 patterns:**
```
# Organization domain
spiffe://example.com/...

# Environment-specific
spiffe://prod.example.com/...
spiffe://staging.example.com/...

# Region-specific
spiffe://us-east.example.com/...
```

**Best practices:**
1. 所有している domains を使用する（collision を防ぐ）
2. trust domains を stable に保つ（変更は disruptive）
3. environment separation を検討する
4. 最初から federation を計画する

**避けるべき anti-patterns:**
```
# Bad: Generic names
spiffe://cluster/...
spiffe://kubernetes/...

# Bad: Temporary names
spiffe://test123/...

# Bad: IP addresses
spiffe://10.0.0.1/...
```

Trust domain names はすべての SVIDs と logs に現れるため、意味があり stable な identifiers を選びましょう。

</details>

---

## スコア計算

- **9-10 correct**: 素晴らしい - SPIFFE/SPIRE について深く理解しています。
- **7-8 correct**: 良い - 主要な concepts をしっかり把握しています。
- **5-6 correct**: まずまず - 追加学習が必要な領域があります。
- **4 or fewer**: documentation をもう一度確認してください。

## 関連ドキュメント

- [SPIFFE/SPIRE による Workload Identity](../../security/12-spiffe-spire.md)
