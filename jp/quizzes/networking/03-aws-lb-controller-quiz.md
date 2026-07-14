# AWS Load Balancer Controller クイズ

このクイズでは、AWS Load Balancer Controller のアーキテクチャ、ALB/NLB の設定、および運用に関する理解を確認します。

## クイズ問題

### 1. AWS Load Balancer Controller は、既存のどの Kubernetes コンポーネントを置き換えますか？

A. kube-proxy
B. in-tree AWS cloud provider
C. CoreDNS
D. CNI plugin

<details>
<summary>回答を表示</summary>

**回答: B. in-tree AWS cloud provider**

**解説:**
AWS Load Balancer Controller は、既存の Kubernetes in-tree AWS cloud provider が提供するロードバランサー機能を置き換えます。
- より多くの機能（高度な ALB、NLB 設定）
- より迅速な更新とバグ修正
- AWS services とのより優れた統合

in-tree provider は基本的な ELB Classic のみをサポートしていましたが、AWS Load Balancer Controller は ALB と NLB のすべての機能をサポートします。

</details>

### 2. ALB Ingress における `ip` と `instance` target-type annotation の正しい違いは何ですか？

A. `ip` は Pod IP を直接ターゲットにし、`instance` は NodePort 経由でルーティングする
B. `ip` は NodePort 経由でルーティングし、`instance` は Pod IP を直接ターゲットにする
C. 両方のオプションは同じように動作する
D. `ip` は IPv4 のみをサポートし、`instance` は IPv6 のみをサポートする

<details>
<summary>回答を表示</summary>

**回答: A. `ip` は Pod IP を直接ターゲットにし、`instance` は NodePort 経由でルーティングする**

**解説:**
Target Type の比較:

| Target Type | 動作 | 長所 | 短所 |
|-------------|----------|------|------|
| `ip` | Pod IP を直接登録 | 低レイテンシ、効率的 | VPC CNI が必要 |
| `instance` | Node の NodePort にルーティング | 汎用的 | 追加のホップ |

`ip` type を使用する場合は AWS VPC CNI が必要であり、Pod IP は Target Group に直接登録されます。

</details>

### 3. AWS Load Balancer Controller に IRSA（IAM Roles for Service Accounts）が必要なのはなぜですか？

A. Pod 間通信のため
B. Controller がリソースを作成・管理するために AWS API を呼び出すため
C. Kubernetes API server 認証のため
D. TLS certificate 管理のため

<details>
<summary>回答を表示</summary>

**回答: B. Controller がリソースを作成・管理するために AWS API を呼び出すため**

**解説:**
AWS Load Balancer Controller は、次のために AWS API を呼び出す必要があります。
- ALB/NLB の作成と管理
- Target Groups の作成とターゲットの登録
- Listeners とルールの設定
- security groups の管理
- ACM certificates の照会

IRSA で IAM Role を Service Account にリンクすると:
- Pods が AWS API に認証できる
- 最小権限の原則を適用できる
- クラスター全体の nodes ではなく、特定の Pods に権限を付与できる

</details>

### 4. 複数の Ingress リソースを単一の ALB に統合するにはどうしますか？

A. 同じ namespace にデプロイする
B. `alb.ingress.kubernetes.io/group.name` annotation を使用する
C. 同じ IngressClass を使用する
D. ALB は常に 1 つの Ingress のみをサポートする

<details>
<summary>回答を表示</summary>

**回答: B. `alb.ingress.kubernetes.io/group.name` annotation を使用する**

**解説:**
Ingress Group 機能:

```yaml
# Ingress 1
metadata:
  annotations:
    alb.ingress.kubernetes.io/group.name: my-app-group
    alb.ingress.kubernetes.io/group.order: "1"
---
# Ingress 2
metadata:
  annotations:
    alb.ingress.kubernetes.io/group.name: my-app-group
    alb.ingress.kubernetes.io/group.order: "2"
```

利点:
- ALB のコスト削減（複数の services で 1 つの ALB を共有）
- 集中管理
- order 指定によるルール優先度の制御

</details>

### 5. NLB Service で TLS termination を実装するための annotation は何ですか？

A. `service.beta.kubernetes.io/aws-load-balancer-ssl-cert`
B. `alb.ingress.kubernetes.io/certificate-arn`
C. `service.beta.kubernetes.io/aws-load-balancer-tls-termination`
D. `nlb.kubernetes.io/ssl-certificate`

<details>
<summary>回答を表示</summary>

**回答: A. `service.beta.kubernetes.io/aws-load-balancer-ssl-cert`**

**解説:**
NLB TLS termination 設定:

```yaml
apiVersion: v1
kind: Service
metadata:
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: "external"
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: "ip"
    service.beta.kubernetes.io/aws-load-balancer-ssl-cert: "arn:aws:acm:..."
    service.beta.kubernetes.io/aws-load-balancer-ssl-ports: "443"
spec:
  type: LoadBalancer
  ports:
    - port: 443
      targetPort: 8080
```

`alb.ingress.kubernetes.io/certificate-arn` は ALB Ingress 用の annotation です。

</details>

### 6. TargetGroupBinding CRD の主な目的は何ですか？

A. 新しい Target Groups を自動的に作成する
B. 既存の AWS Target Groups を Kubernetes Services に接続する
C. ALB Listener ルールを定義する
D. security groups を自動作成する

<details>
<summary>回答を表示</summary>

**回答: B. 既存の AWS Target Groups を Kubernetes Services に接続する**

**解説:**
TargetGroupBinding のユースケース:
1. 既存インフラの移行 - 既存の Target Groups を活用
2. マルチクラスター共有 - 複数のクラスターで 1 つの ALB/NLB を使用
3. Target Group の直接管理が必要な場合

```yaml
apiVersion: elbv2.k8s.aws/v1beta1
kind: TargetGroupBinding
metadata:
  name: my-tgb
spec:
  targetGroupARN: arn:aws:elasticloadbalancing:...
  serviceRef:
    name: my-service
    port: 80
  targetType: ip
```

</details>

### 7. WAF v2 を ALB Ingress と統合するための annotation は何ですか？

A. `alb.ingress.kubernetes.io/waf-acl-id`
B. `alb.ingress.kubernetes.io/wafv2-acl-arn`
C. `alb.ingress.kubernetes.io/web-acl`
D. `alb.ingress.kubernetes.io/firewall-rules`

<details>
<summary>回答を表示</summary>

**回答: B. `alb.ingress.kubernetes.io/wafv2-acl-arn`**

**解説:**
AWS WAF v2 統合:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  annotations:
    alb.ingress.kubernetes.io/wafv2-acl-arn: arn:aws:wafv2:us-east-1:ACCOUNT:regional/webacl/my-acl/xxx
```

WAF v2 の機能:
- SQL injection、XSS 保護
- Rate limiting
- IP ベースのブロック/許可
- Custom rules

Controller のインストール時には `enableWafv2: true` 設定が必要です。

</details>

### 8. AWS Load Balancer Controller で subnet を自動検出するための tags は何ですか？

A. `kubernetes.io/cluster/<cluster-name>=owned`
B. `kubernetes.io/role/elb=1` (public), `kubernetes.io/role/internal-elb=1` (private)
C. `aws:cloudformation:stack-name`
D. `Name=kubernetes-subnet`

<details>
<summary>回答を表示</summary>

**回答: B. `kubernetes.io/role/elb=1` (public), `kubernetes.io/role/internal-elb=1` (private)**

**解説:**
Subnet tagging ルール:

```bash
# Public subnets (for internet-facing ALB/NLB)
kubernetes.io/role/elb=1

# Private subnets (for internal ALB/NLB)
kubernetes.io/role/internal-elb=1

# Cluster ownership (optional)
kubernetes.io/cluster/<cluster-name>=shared or owned
```

これらの tags がない場合、Controller は適切な subnets を見つけられず、load balancer の作成に失敗する可能性があります。

</details>

### 9. ALB Ingress で Sticky Sessions を有効化する annotation は何ですか？

A. `alb.ingress.kubernetes.io/sticky-sessions=true`
B. `alb.ingress.kubernetes.io/target-group-attributes: stickiness.enabled=true`
C. `alb.ingress.kubernetes.io/session-affinity=cookie`
D. `alb.ingress.kubernetes.io/cookie-based-routing=true`

<details>
<summary>回答を表示</summary>

**回答: B. `alb.ingress.kubernetes.io/target-group-attributes: stickiness.enabled=true`**

**解説:**
Sticky Session 設定:

```yaml
metadata:
  annotations:
    alb.ingress.kubernetes.io/target-group-attributes: >-
      stickiness.enabled=true,
      stickiness.lb_cookie.duration_seconds=3600
```

Target Group attributes として設定します:
- `stickiness.enabled=true` - 有効化
- `stickiness.lb_cookie.duration_seconds` - Cookie の有効期間
- `stickiness.type` - lb_cookie または app_cookie

Sticky Sessions は、session state を維持する必要があるレガシーアプリケーションで役立ちます。

</details>

### 10. NLB でクライアント source IP を保持するにはどうしますか？

A. `service.beta.kubernetes.io/aws-load-balancer-proxy-protocol: "*"` を使用する
B. externalTrafficPolicy: Local を使用する
C. どちらの方法も可能
D. NLB は常に client IP を保持する

<details>
<summary>回答を表示</summary>

**回答: C. どちらの方法も可能**

**解説:**
client IP を保持する方法:

1. **Proxy Protocol v2**:
```yaml
annotations:
  service.beta.kubernetes.io/aws-load-balancer-proxy-protocol: "*"
  service.beta.kubernetes.io/aws-load-balancer-target-group-attributes: proxy_protocol_v2.enabled=true
```
- Application が Proxy Protocol をサポートしている必要がある

2. **externalTrafficPolicy: Local**:
```yaml
spec:
  externalTrafficPolicy: Local
```
- 追加のホップなしで、同じ node 上の Pods にのみルーティングする
- traffic distribution が不均一になる可能性がある

3. **IP Target Type** (ip mode):
```yaml
annotations:
  service.beta.kubernetes.io/aws-load-balancer-target-group-attributes: preserve_client_ip.enabled=true
```

</details>

### 11. ALB Ingress で HTTP を HTTPS にリダイレクトする annotation は何ですか？

A. `alb.ingress.kubernetes.io/actions.ssl-redirect`
B. `alb.ingress.kubernetes.io/ssl-redirect: "443"`
C. `alb.ingress.kubernetes.io/force-ssl-redirect: "true"`
D. `alb.ingress.kubernetes.io/http-to-https: "true"`

<details>
<summary>回答を表示</summary>

**回答: B. `alb.ingress.kubernetes.io/ssl-redirect: "443"`**

**解説:**
SSL redirect 設定:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  annotations:
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTP": 80}, {"HTTPS": 443}]'
    alb.ingress.kubernetes.io/ssl-redirect: "443"
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:...
```

動作:
- HTTP(80) に到着した requests を HTTPS(443) に 301 redirect する
- security のベストプラクティスとして推奨
- ACM certificate が必要

</details>

### 12. AWS Load Balancer Controller によって ALB が作成されない場合、確認すべきでない項目はどれですか？

A. IAM permissions を確認する
B. subnet tags を確認する
C. IngressClass specification を確認する
D. kube-proxy logs を確認する

<details>
<summary>回答を表示</summary>

**回答: D. kube-proxy logs を確認する**

**解説:**
ALB 作成に失敗した場合の確認項目:

1. **IAM permissions**: Service Account の IAM Role に必要な permissions があるか
2. **Subnet tags**: `kubernetes.io/role/elb=1` または `kubernetes.io/role/internal-elb=1`
3. **IngressClass**: `ingressClassName: alb` を指定するか、annotation で指定する
4. **Controller logs**: `kubectl logs -n kube-system deployment/aws-load-balancer-controller`
5. **Ingress events**: `kubectl describe ingress <name>`

kube-proxy は Service ClusterIP/NodePort のルーティングを処理しており、ALB の作成とは無関係です。

</details>

---

## 追加学習リソース

- [AWS Load Balancer Controller ドキュメント](https://kubernetes-sigs.github.io/aws-load-balancer-controller/)
- [EKS ユーザーガイド](https://docs.aws.amazon.com/eks/latest/userguide/aws-load-balancer-controller.html)
- [ALB Annotation リファレンス](https://kubernetes-sigs.github.io/aws-load-balancer-controller/v2.8/guide/ingress/annotations/)
