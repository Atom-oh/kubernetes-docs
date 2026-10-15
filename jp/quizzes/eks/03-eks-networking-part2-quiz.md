# EKS ネットワーキングクイズ - パート 2

> **最終更新**: October 12, 2026

これらの回答では、[パート 2](../../eks/03-eks-networking-part2.md) のコントローラーの所有範囲と前提条件（LBC 3.5.0 および Gateway API 1.6.0）を使用します。コマンドは実行時にリソースを変更する例です。ローカルのスキーマ/モックテストは EKS デプロイメントを構成しません。アカウント/Region/リソースのプレースホルダーを置き換え、意図した kubeconfig を使用し、プラットフォームの IAM/Helm/IaC 所有範囲を維持してください。

### 1. AWS Load Balancer Controller は、Kubernetes Ingress リソースに対してデフォルトでどの種類の AWS ロードバランサーをプロビジョニングしますか？

A. Classic Load Balancer (CLB) B. Network Load Balancer (NLB) C. Application Load Balancer (ALB) D. Gateway Load Balancer (GWLB)

<details>

<summary>回答を表示</summary>

**回答: C. Application Load Balancer (ALB)**

**解説:** AWS Load Balancer Controller は、Kubernetes Ingress リソースに対してデフォルトで Application Load Balancer (ALB) をプロビジョニングします。ALB は HTTP/HTTPS トラフィックを処理する Layer 7 ロードバランサーであり、Ingress リソースの要件を満たすために、パスベースルーティング、ホストベースルーティング、TLS 終端などの機能を提供します。

LBC は Ingress class を選択する必要があります。別のコントローラーが Ingress を異なる方法で実装することもあります。以下の public scheme には、意図的に設定された public subnet、クライアントの SG アクセス、および準備完了したバックエンド Service が必要です。

**主な機能:**

1. **パスベースルーティング**: ALB は URL パスに基づいて異なる Service にトラフィックをルーティングできるため、Ingress でパスベースのルーティングルールを実装するのに適しています。
2. **ホストベースルーティング**: 単一の ALB で複数のドメインを処理でき、複数のホストルールを持つ Ingress をサポートします。
3. **TLS 終端**: ALB は SSL/TLS 証明書を管理し、HTTPS トラフィックを終端できます。
4. **WebSockets サポート**: ALB は WebSockets プロトコルをサポートしており、リアルタイムアプリケーションに適しています。
5. **認証統合**: Amazon Cognito または OIDC と統合して、アプリケーションレベルの認証を提供できます。

**設定例:**

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: example-ingress
  annotations:
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
spec:
  ingressClassName: alb
  rules:
  - host: example.com
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: api-service
            port:
              number: 80
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend-service
            port:
              number: 80
```

**主なアノテーション:**

* `spec.ingressClassName: alb`: コントローラーが `ingress.k8s.aws/alb` である IngressClass を選択します
* `alb.ingress.kubernetes.io/scheme: internet-facing`: internet-facing ALB を作成します
* `alb.ingress.kubernetes.io/target-type: ip`: ターゲットとして（instance ではなく）Pod IP を使用します
* `alb.ingress.kubernetes.io/listen-ports: '[{"HTTP": 80}, {"HTTPS": 443}]'`: リスナーポートを設定します
* `alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:region:account-id:certificate/certificate-id`: SSL 証明書を指定します

他の選択肢に関する問題点:

* **A. Classic Load Balancer (CLB)**: AWS Load Balancer Controller は Ingress リソースに CLB を使用しません。CLB はレガシーロードバランサーと見なされています。
* **B. Network Load Balancer (NLB)**: NLB は主に Service type LoadBalancer に使用され、Ingress リソースにはデフォルトでは使用されません。
* **D. Gateway Load Balancer (GWLB)**: GWLB はネットワーク仮想アプライアンス用であり、Kubernetes Ingress リソースでは使用されません。

</details>

### 2. internal ALB を選択する Ingress アノテーションはどれですか？

- A. Service アノテーション `aws-load-balancer-internal`
- B. Ingress アノテーション `alb.ingress.kubernetes.io/scheme: internal`
- C. `internal-alb` という名前の任意の class
- D. `aws-load-balancer-type: internal`

<details>
<summary>回答を表示</summary>

**回答: B. `alb.ingress.kubernetes.io/scheme: internal`**

internal ALB は private アドレスを持ちます。接続された VPC またはオンプレミスネットワーク内のルーティングされたクライアントも、ルーティング、DNS、およびセキュリティ制御によって許可される場合にアクセスできます。定義上、Pod または自身の VPC に限定されるものではありません。
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: internal-ingress
  annotations:
    alb.ingress.kubernetes.io/scheme: internal
    alb.ingress.kubernetes.io/target-type: ip
spec:
  ingressClassName: alb
  rules:
  - host: app.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: internal-service
            port:
              number: 80
```
Subnet discovery または明示的な subnet ID によって配置を選択し、SG がアクセスを制御します。`inbound-cidrs` はコントローラーが作成するフロントエンド SG を設定しますが、カスタム SG が指定されている場合は無視されます。Route 53 private alias/CNAME は別途作成する必要があります。ALB ログ属性は DNS レコードを作成しません。`internal-alb` などのカスタム IngressClass 名は、実際に一致する IngressClass/コントローラー設定が存在する場合には可能ですが、名前だけでは scheme は選択されません。

</details>

### 3. Pod IP ターゲットを選択する Ingress アノテーションはどれですか？

- A. `target-type: pod`
- B. `alb.ingress.kubernetes.io/target-type: ip`
- C. `service.beta.kubernetes.io/aws-load-balancer-target-type: ip`
- D. `aws-load-balancer-target-node-labels: ip-mode=true`

<details>
<summary>回答を表示</summary>

**回答: B. `alb.ingress.kubernetes.io/target-type: ip`**

`ip` はルーティング可能な Pod IP と解決された Service ターゲットポートを登録します。`instance` は通常、ノードと NodePort を登録します（コントローラー/IngressClass のデフォルトに従います）。IP ターゲットは EKS Fargate で必要です。IP ターゲットを選択しても、それ自体で Pod security group が作成されたり、ノード障害がなくなったり、より高いパフォーマンスが保証されたりするわけではありません。
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ip-ingress
  annotations:
    alb.ingress.kubernetes.io/scheme: internal
    alb.ingress.kubernetes.io/target-type: ip
spec:
  ingressClassName: alb
  rules:
  - host: app.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: example-service
            port:
              number: 80
```
| プロパティ | IP ターゲット | Instance ターゲット |
|---|---|---|
| パス | LB → Pod ターゲット | LB → NodePort → 選択された endpoint |
| ノード障害 | 障害ノード上の Pod は失われます。health check/reconciliation が収束します | 障害ノードターゲットは削除され、他の正常なノードは維持される場合があります |
| Service type | ClusterIP で十分です | NodePort、または NodePort が割り当てられた LoadBalancer |
| Fargate | サポートされるパス | EC2 NodePort ターゲットなし |

VPC でルーティング可能な Pod ネットワーキングを使用し、アプリケーションと health check の両方のトラフィックを許可してください。Native VPC CNI は通常の EC2 パスです。サポートされる hybrid/network 設計には、それぞれ独自の到達可能性の検証が必要です。`service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip` は NLB Service に対応するアノテーションです。`nlb` を省略した選択肢は正しいアノテーションではありません。

</details>

### 4. NLB-IP アノテーションは PrivateLink endpoint service を作成しますか？

- A. 任意の `LoadBalancer` Service が PrivateLink を作成する
- B. `nlb-ip` が自動的に作成および認可する
- C. NLB、endpoint service、および consumer 設定を分けて行う
- D. PrivateLink を使用できるのは instance ターゲットのみ

<details>
<summary>回答を表示</summary>

**回答: C. いいえ。NLB、endpoint-service 設定、および consumer アクセスを別々に作成します。**

元の `nlb-ip` の回答は、ターゲット選択と PrivateLink プロビジョニングを混同していました。endpoint service は NLB（またはアプライアンス用の GWLB）を使用します。IP ターゲットも internal NLB も必要ありません。この例では、private Pod アクセスのために internal IP-target NLB を意図的に選択しています。
```yaml
apiVersion: v1
kind: Service
metadata:
  name: privatelink-service
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-scheme: internal
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip
spec:
  type: LoadBalancer
  loadBalancerClass: service.k8s.aws/nlb
  allocateLoadBalancerNodePorts: false
  selector:
    app: my-app
  ports:
  - port: 80
    targetPort: 8080
```
この Service を、準備完了した一致 Pod がある意図した namespace に作成し、NLB を待ちます。hostname をハイフンで分割するのではなく、正確な DNSName で識別してください:
```bash
set -euo pipefail
: "${AWS_REGION:?Set the provider Region}"
: "${SERVICE_NAMESPACE:?Set the Service namespace}"
NLB_DNS=$(kubectl -n "$SERVICE_NAMESPACE" get service privatelink-service \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
test -n "$NLB_DNS"
aws elbv2 describe-load-balancers --region "$AWS_REGION" --output json > privatelink-load-balancers.json
NLB_ARN=$(python3 - "$NLB_DNS" <<'PY'
import json, sys
with open("privatelink-load-balancers.json") as stream:
    matches = [lb for lb in json.load(stream)["LoadBalancers"]
               if lb["DNSName"] == sys.argv[1] and lb["Type"] == "network"]
if len(matches) != 1:
    raise SystemExit("Expected exactly one matching NLB; check Region, account and readiness")
print(matches[0]["LoadBalancerArn"])
PY
)
printf '%s\n' "$NLB_ARN"
```
以下の provider 側コマンドは、課金対象のリソースを作成し、1 つの consumer アカウントに endpoint-service アクセスを許可します。レビュー済みのインフラストラクチャ所有者のもとで実行し、返された ID を記録し、冪等であるかのように作成を再実行しないでください。この例は商用 AWS partition 用です。別の partition 用に ARN を調整してください。
```bash
set -euo pipefail
: "${AWS_REGION:?Set the provider Region}"
: "${NLB_ARN:?Use the NLB ARN verified above}"
: "${CONSUMER_ACCOUNT_ID:?Set the allowed consumer account}"
aws ec2 create-vpc-endpoint-service-configuration \
  --region "$AWS_REGION" --network-load-balancer-arns "$NLB_ARN" \
  --acceptance-required --output json > endpoint-service-created.json
SERVICE_ID=$(python3 -c 'import json; print(json.load(open("endpoint-service-created.json"))["ServiceConfiguration"]["ServiceId"])')
SERVICE_NAME=$(python3 -c 'import json; print(json.load(open("endpoint-service-created.json"))["ServiceConfiguration"]["ServiceName"])')
aws ec2 modify-vpc-endpoint-service-permissions \
  --region "$AWS_REGION" --service-id "$SERVICE_ID" \
  --add-allowed-principals "arn:aws:iam::$CONSUMER_ACCOUNT_ID:root"
printf 'Service name: %s\n' "$SERVICE_NAME"
```
consumer アカウントでは、サポートされる AZ を選択し（アカウント間で AZ ID を比較）、意図したクライアントを許可する endpoint SG と、正確に返された service name を使用してください。この同一 Region の例は、cross-Region PrivateLink を設定しません。
```bash
set -euo pipefail
: "${CONSUMER_REGION:?Set the consumer Region}"
: "${CONSUMER_VPC_ID:?Set the consumer VPC}"
: "${CONSUMER_SUBNET_A:?Set a subnet in an available service AZ}"
: "${CONSUMER_SUBNET_B:?Set another supported AZ subnet}"
: "${CONSUMER_SG_ID:?Set the endpoint security group}"
: "${SERVICE_NAME:?Copy the exact name returned by the provider}"
aws ec2 create-vpc-endpoint \
  --region "$CONSUMER_REGION" --vpc-id "$CONSUMER_VPC_ID" \
  --service-name "$SERVICE_NAME" --vpc-endpoint-type Interface \
  --subnet-ids "$CONSUMER_SUBNET_A" "$CONSUMER_SUBNET_B" \
  --security-group-ids "$CONSUMER_SG_ID"
```
acceptance が必須であるため、provider は特定の保留中 endpoint request を承認する必要があります。オプションの private DNS では、consumer が有効化する前にドメイン所有権の検証が必要です。正常なターゲット、endpoint state、およびアプリケーション認証を検証してください。ターゲットでの PrivateLink source IP は NLB アドレスです。バックエンドが対応している場合、Proxy Protocol v2 は consumer メタデータを伝達できます。これはコンプライアンスを自動的に満たすものでも、アプリケーションリクエストを認可するものでもありません。それぞれの所有者を通じて、consumer endpoint、endpoint-service association、および Kubernetes load-balancer リソースを廃止してください。

</details>

### 5. Amazon VPC CNI と連携できる追加の policy engine はどれですか？

- A. AWS Network Firewall
- B. Calico
- C. Security Groups for Pods
- D. VPC Flow Logs

<details>
<summary>回答を表示</summary>

**回答: B. Calico**

Calico は、VPC CNI が IPAM/ネットワーキングを維持したままポリシーを強制できます。これは native VPC CNI policy engine の代替であり、必須の add-on ではありません。サポート対象バージョン、`cni.type: AmazonVPC`、`ANNOTATE_POD_IP`、および必要な Pod patch 権限を含む[公式の policy-only EKS 手順](https://docs.tigera.io/calico/latest/getting-started/kubernetes/managed-public-cloud/eks)に従ってください。両方の engine を同時に有効化したり、実行中のクラスターに VXLAN 置換 manifest を適用したりしないでください。

Calico API は、順序付き/階層化ルール、GlobalNetworkPolicy、NetworkSet、service-account selector、および host-endpoint policy も提供します。これらのセマンティクスは、加算的な Kubernetes NetworkPolicy とは異なります。NetworkSet は、Calico policy が参照するまでトラフィックを制限しません。グローバルな allow-all policy は最小権限のベースラインではありません。すべての VPC CNI mode に互換性があると想定しないでください。現在の Calico EKS ガイドでは、`ENABLE_V4_EGRESS=true` の IPv6 Pod に対する強制を明確に除外しています。

namespace が所有する Kubernetes policy の例として、`policy-lab` と、`role=frontend` のラベルを持つコントローラー管理 Pod を作成します。この egress policy は、他のすべての加算的 policy に従い、通常の CoreDNS と承認済み HTTPS 宛先のみを許可します。ドキュメントの CIDR を実際の宛先に置き換え、NodeLocal DNS に合わせて DNS を調整してください。
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: frontend-egress
  namespace: policy-lab
spec:
  podSelector:
    matchLabels:
      role: frontend
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
  - to:
    - ipBlock:
        cidr: 203.0.113.0/24
    ports:
    - protocol: TCP
      port: 443
```
強制に依存する前に、ベースライン接続性と許可/拒否された TCP パスを検証してください。NetworkPolicy にはポータブルな audit-only mode はありません。利用可能な場合は、選択した engine で文書化されている logging/staging 機能を使用してください。SG for Pods と VPC firewall は別の制御であり、Flow Logs はこの API を強制するのではなくトラフィックを監視します。

</details>

### 6. カスタム ALB フロントエンド security group とバックエンドルールはどのように異なりますか？

<details>
<summary>回答を表示</summary>

**回答: `alb.ingress.kubernetes.io/security-groups`**

このアノテーションフラグメントを意図した Ingress にマージしてください。SG ID は曖昧ではありません。名前の lookup は EC2 `groupName` 属性ではなく、AWS `Name` tag と一致します。
```yaml
metadata:
  annotations:
    alb.ingress.kubernetes.io/security-groups: sg-0123456789abcdef0
    alb.ingress.kubernetes.io/manage-backend-security-group-rules: "true"
    alb.ingress.kubernetes.io/tags: Environment=training,Team=platform
```
カスタムフロントエンド inbound/outbound ルールは自分で設定してください。指定されたフロントエンド SG では、`inbound-cidrs` と prefix-list アノテーションは無視されます。`manage-backend-security-group-rules: "true"` は、コントローラーがバックエンド SG メカニズムを通じてターゲットアクセスを管理することを認可します。これは、カスタムフロントエンド SG のクライアントアクセスを制限するルールを作成するものではありません。これがない場合は、ノード/Pod SG アクセスを自分で手配してください。アプリケーションおよび health-check ポートを許可し、ターゲット ENI に複数の SG がある場合は SG 選択 tag を確認してください。

release IAM policy には、コントローラー全体に必要な EC2/ELB 権限が含まれます。短い SG アクションリストは完全な role policy ではありません。trust domain をまたいで SG を再利用すると、露出範囲が広がり、変更の結合度が増加します。実際のルールと VPC Flow Log の拒否を確認してください。`tags` はサポートされるリソース tag を追加します。`load_balancing.cross_zone.enabled` は tag ではなく balancing 属性です。レガシー policy 名を現行ガイダンスとしてコピーするのではなく、クライアント互換性と要件に基づいてサポートされる TLS security policy を選択してください。

</details>

### 7. NLB のクライアント IP 保持はどのように設定され、その制限は何ですか？

<details>
<summary>回答を表示</summary>

**回答: `service.beta.kubernetes.io/aws-load-balancer-target-group-attributes: preserve_client_ip.enabled=true`**

TCP/TLS target group では、この属性は設定可能です。instance ターゲットではデフォルトで有効、IP ターゲットではデフォルトで無効です。UDP/TCP_UDP/QUIC/TCP_QUIC target group は常にクライアント IP を保持し、無効化できません。この IPv4 IP-target TCP の例は、設定可能なケースを変更します:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-service
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-target-group-attributes: preserve_client_ip.enabled=true
    service.beta.kubernetes.io/aws-load-balancer-scheme: internal
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip
spec:
  type: LoadBalancer
  loadBalancerClass: service.k8s.aws/nlb
  allocateLoadBalancerNodePorts: false
  selector:
    app: my-app
  ports:
  - port: 80
    targetPort: 8080
```
アプリケーションが認識するアドレスは、依然として完全なパスに依存します。NodePort forwarding は、local traffic policy/topology がこれを保持しない限り SNAT する可能性があります。ALB は HTTP forwarded header を使用します。IPv6-to-IPv4 変換と PrivateLink は元の packet source を保持しません。保持には、サポートされる direct same-VPC または same-Region peering パスが必要で、transit gateway 経由では機能しません。登録済みの同じターゲットに戻る internal-NLB hairpin 接続は失敗する場合があります。

Proxy Protocol v2 は元のアドレスメタデータを伝達できますが、互換性のある listener/parser が必要です。安易に有効化しないでください。framework の `remote_addr` または TCP `RemoteAddr()` は、元のインターネットクライアントではなく直接の peer を報告します。明示的に信頼する proxy からの forwarded header のみを信頼してください。保持の変更は新しい TCP 接続に影響します。`deregistration_delay.timeout_seconds` は draining を制御するものであり、TCP keep-alive を制御するものではありません。サポートされていないオーバーヘッド値を割り当てるのではなく、パフォーマンスを測定してください。

</details>

### 8. AWS WAF は LBC 管理の ALB にどのようにアタッチされますか？

<details>
<summary>回答を表示</summary>

**回答: 同一 Region の REGIONAL Web ACL を使用する `alb.ingress.kubernetes.io/wafv2-acl-arn`。**

実際の `regional/webacl/...` ARN を使用してください。CloudFront の `global/webacl/...` ARN は regional ALB にアタッチできません。association はその ALB を通るトラフィックを保護します。WAF を Pod、NLB、または Kubernetes API server にアタッチするものではありません。
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: waf-ingress
  annotations:
    alb.ingress.kubernetes.io/scheme: internal
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/wafv2-acl-arn: arn:aws:wafv2:us-west-2:123456789012:regional/webacl/eks-ingress-protection/00000000-0000-4000-8000-000000000000
spec:
  ingressClassName: alb
  rules:
  - host: app.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: example-service
            port:
              number: 80
```
空の Web ACL は、デフォルトが Allow の場合、何もブロックしません。分離したルール開発の例として、以下の配列を `waf-rules.json` として保存します。このルールは `/admin` prefix をブロックするのではなく**カウント**します。これは認証制御でも完全な managed-rule ベースラインでもありません。
```json
[
  {
    "Name": "count-admin-path",
    "Priority": 1,
    "Action": {
      "Count": {}
    },
    "VisibilityConfig": {
      "SampledRequestsEnabled": true,
      "CloudWatchMetricsEnabled": true,
      "MetricName": "count-admin-path"
    },
    "Statement": {
      "ByteMatchStatement": {
        "SearchString": "/admin",
        "FieldToMatch": {
          "UriPath": {}
        },
        "TextTransformations": [
          {
            "Priority": 0,
            "Type": "NONE"
          }
        ],
        "PositionalConstraint": "STARTS_WITH"
      }
    }
  }
]
```
セキュリティ所有者は以下のコマンドでそのトレーニング ACL を作成できます。association の際は返された ARN を使用してください。binary-format flag により、AWS CLI v2 では JSON SearchString が literal bytes になります。
```bash
set -euo pipefail
: "${AWS_REGION:?Set the ALB Region}"
aws wafv2 create-web-acl --region "$AWS_REGION" \
  --name eks-ingress-training --scope REGIONAL \
  --default-action '{"Allow":{}}' --rules file://waf-rules.json \
  --cli-binary-format raw-in-base64-out \
  --visibility-config SampledRequestsEnabled=true,CloudWatchMetricsEnabled=true,MetricName=eks-ingress-training
```
Managed SQLi/XSS、bot、reputation、rate-based、および custom rule は、設定とチューニング後にのみそれぞれの保護を提供します。料金/機能は異なります。強制を有効化する前に、Count mode で false positive を確認してください。rule がカウントしている間、デフォルト Allow は許容的なままです。

ALB の `access_logs.s3.*` 属性は S3 の ALB access log を設定するものであり、WAF log や CloudWatch Logs ではありません。承認済みの CloudWatch Logs/S3/Firehose 宛先と必要な権限を使用して WAF logging を別途設定してください。sampled request と CloudWatch metric は完全な request log とは別のものです。association にはレビュー済み release controller IAM policy を、ACL の作成/rule/logging には別の security-administration role を使用してください。サポートされる場合はリソース権限をスコープしてください。制約のない standalone wildcard policy を完全な controller role として貼り付けないでください。

</details>

### 9. 識別可能な 3 つのバックエンドに対するパスルーティングを構築して検証します。

<details>
<summary>回答を表示</summary>

**回答: Ingress + ClusterIP Service + 準備完了した HTTP ワークロード。**

前提条件: レビュー済み IAM/subnet を持つ LBC、ルーティング可能な private test client、自身が制御する hostname 用の ACM 証明書、および専用 namespace を作成する権限。この例では internal ALB を作成します。`/admin` はルーティングラベルにすぎず、認証はありません。これは範囲を限定したトレーニング演習であり、production readiness の証拠ではありません。`set -euo pipefail` を使用して 1 つの shell でブロックを実行し、cleanup まで LAB_NS/LAB_UID を保持してください。
```bash
set -euo pipefail
LAB_NS="alb-paths-$(date -u +%Y%m%d%H%M%S)-$RANDOM"
kubectl create namespace "$LAB_NS"
LAB_UID=$(kubectl get namespace "$LAB_NS" -o jsonpath='{.metadata.uid}')
test -n "$LAB_UID"
kubectl label namespace "$LAB_NS" \
  pod-security.kubernetes.io/enforce=restricted \
  pod-security.kubernetes.io/enforce-version=v1.36
printf 'Namespace: %s UID: %s\n' "$LAB_NS" "$LAB_UID"
```
HTTP server は実際に 8080 で listen し、`/health` およびすべてのリクエストされたパスにバックエンド名で応答します。`containerPort: 8080` を宣言するだけでは、デフォルトの nginx server は再設定されません。mutable Python tag は例示的な runtime です。再現可能な使用のために、承認済みの image digest を pin してください。
```bash
for APP in api admin frontend; do
  kubectl -n "$LAB_NS" apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: $APP
spec:
  replicas: 2
  selector:
    matchLabels:
      app: $APP
  template:
    metadata:
      labels:
        app: $APP
    spec:
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 10001
        runAsGroup: 10001
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: http
        image: python:3.13-alpine
        command: ["python", "-u", "-c"]
        args:
        - |
          import os
          from http.server import BaseHTTPRequestHandler, HTTPServer
          class Handler(BaseHTTPRequestHandler):
              def do_GET(self):
                  self.send_response(200)
                  self.end_headers()
                  self.wfile.write((os.environ["APP_NAME"] + "\\n").encode())
          HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
        env:
        - name: APP_NAME
          value: $APP
        ports:
        - name: http
          containerPort: 8080
        readinessProbe:
          httpGet:
            path: /health
            port: http
        resources:
          requests:
            cpu: 50m
            memory: 32Mi
          limits:
            cpu: 200m
            memory: 64Mi
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop: ["ALL"]
---
apiVersion: v1
kind: Service
metadata:
  name: $APP-service
spec:
  type: ClusterIP
  selector:
    app: $APP
  ports:
  - port: 80
    targetPort: http
EOF
  kubectl -n "$LAB_NS" rollout status "deployment/$APP" --timeout=180s
done
```

```bash
set -euo pipefail
: "${LAB_NS:?Run the namespace setup first}"
: "${LAB_HOST:?Set a DNS hostname you control, for example app.example.com}"
: "${ACM_CERT_ARN:?Set a matching certificate ARN in the ALB Region}"
: "${CLIENT_CIDR:?Set the permitted private client CIDR}"
kubectl -n "$LAB_NS" apply -f - <<EOF
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: multi-path-ingress
  annotations:
    alb.ingress.kubernetes.io/scheme: internal
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/inbound-cidrs: "$CLIENT_CIDR"
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTP":80},{"HTTPS":443}]'
    alb.ingress.kubernetes.io/certificate-arn: "$ACM_CERT_ARN"
    alb.ingress.kubernetes.io/ssl-redirect: "443"
    alb.ingress.kubernetes.io/healthcheck-path: /health
spec:
  ingressClassName: alb
  rules:
  - host: "$LAB_HOST"
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: api-service
            port:
              number: 80
      - path: /admin
        pathType: Prefix
        backend:
          service:
            name: admin-service
            port:
              number: 80
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend-service
            port:
              number: 80
EOF
kubectl -n "$LAB_NS" get ingress multi-path-ingress
kubectl -n "$LAB_NS" get endpointslices
```
ALB hostname、正常なターゲット、および controller reconciliation を待ちます。失敗した場合は、Ingress event、controller log、EndpointSlice、および SG/health-check パスを調査してください。許可された private client から、このテストは ALB hostname に直接接続しながら Host header と TLS SNI を保持します。DNS record は必要なく、証明書検証も無効化しません。
```bash
ALB_DNS=$(kubectl -n "$LAB_NS" get ingress multi-path-ingress \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
test -n "$ALB_DNS"
for ROUTE in api admin frontend; do
  URL_PATH="/$ROUTE"
  test "$ROUTE" != frontend || URL_PATH=/
  RESPONSE=$(curl --fail --show-error --silent --max-time 15 \
    --connect-to "$LAB_HOST:443:$ALB_DNS:443" "https://$LAB_HOST$URL_PATH")
  test "$RESPONSE" = "$ROUTE" || { printf 'Unexpected backend: %s\n' "$RESPONSE"; exit 1; }
done
```
永続的な DNS には、適切な Route 53 alias を作成してください。CNAME は zone apex ではなく subdomain で使用できます。public CA placeholder ARN や、証明書の不一致を隠す `curl -k` を使用しないでください。

オプションの weighted routing は、既存の `service-v1`/`service-v2` バックエンドを使用する別の例です。action は `use-annotation` バックエンドから参照される必要があります。action アノテーションを追加するだけでは効果がありません。意図した namespace で実行し、競合する route を避けてください。
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: weighted-ingress
  annotations:
    alb.ingress.kubernetes.io/scheme: internal
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/actions.weighted-routing: >-
      {"type":"forward","forwardConfig":{"targetGroups":[{"serviceName":"service-v1","servicePort":"80","weight":80},{"serviceName":"service-v2","servicePort":"80","weight":20}]}}
spec:
  ingressClassName: alb
  rules:
  - http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: weighted-routing
            port:
              name: use-annotation
```
保存した UID を確認した後で、この演習の namespace のみを cleanup してください。namespace を削除する前に、LBC に Ingress load balancer を削除させてください。finalization が失敗した場合は、controller/IAM/deletion-protection state を診断してください。finalizer を強制削除しないでください。共有証明書、controller role、および DNS record はこのブロックでは削除されません。
```bash
set -euo pipefail
: "${LAB_NS:?Use the namespace from this exercise}"
: "${LAB_UID:?Use the UID saved when that namespace was created}"
case "$LAB_NS" in alb-paths-*) ;; *) echo "Unexpected namespace"; exit 1 ;; esac
CURRENT_UID=$(kubectl get namespace "$LAB_NS" -o jsonpath='{.metadata.uid}')
test "$CURRENT_UID" = "$LAB_UID" || { echo "Namespace identity changed"; exit 1; }
kubectl -n "$LAB_NS" delete ingress multi-path-ingress --ignore-not-found --wait=true --timeout=300s
kubectl delete namespace "$LAB_NS" --wait=true --timeout=300s
```

</details>

### 10. service mesh は EKS ネットワーキングをどのように変更し、何を検証する必要がありますか？

<details>
<summary>回答を表示</summary>

**回答: 互換性のある Pod network の上にトラフィック/セキュリティ/telemetry 処理を追加します。**

control plane は設定と workload identity を配布し、data-plane proxy は登録されたトラフィックを処理します。sidecar 設計では、アプリケーションと proxy は**同じ Pod network namespace/IP**を共有します。sidecar が本質的に別の VPC IP や ENI を消費することはありません。追加の mesh gateway/control-plane Pod はリソース/IP を消費します。ambient 設計では代わりに node proxy とオプションの waypoint を使用するため、「すべての Pod が sidecar を得る」は普遍的ではありません。
```text
Client application → client proxy → Pod network → destination proxy → destination application
```
これは論理的な sidecar パスであり、すべての packet が Service virtual IP を通過する、または intercept されるという保証ではありません。除外される port、UDP、host-network トラフィック、namespace enrollment、および mode が影響します。VPC route、SG、および NetworkPolicy は引き続き適用されます。L3/L4 policy は、必要な data-plane、DNS、control-plane、および health パスを許可する必要があります。mTLS は mesh peer を認証/暗号化するものであり、アプリケーション認可を置き換えるものではありません。

Istio では、compute type に対して文書化された 1 つの sidecar/ambient installation を選択してください。Fargate では、一部の mode で必要な node DaemonSet/privileged component を実行できません。普遍的な互換性を主張するのではなく、サポートを検証してください。1 つの namespace で 2 つの mesh injector を有効化しないでください。無関係な `pilot.resources` で injector ConfigMap を上書きするのではなく、サポートされる Helm/install/workload 設定を通じて proxy リソースを設定してください。Prometheus/tracing deployment と mesh export 設定は分けてください。削除された `IstioOperator.addonComponents.prometheus` と架空の App Mesh `Mesh.spec.tracing` は使用可能な installation recipe ではありません。

**歴史的比較:** AWS は **September 30, 2026** に App Mesh のサポートを終了しました。その console とリソースは利用できなくなっています。既存の App Mesh デプロイメントは移行する必要があります。これを新しい EKS のデフォルトとして導入しないでください。その歴史的な Fargate 統合は将来のサポートを保証するものではありません。ECS Service Connect は ECS の選択肢であり、直接的な EKS の代替ではありません。サポートされる EKS mesh/data-plane 設計を使用し、routing、retry、certificate、authorization、tracing、および failure handling の feature parity を検証してください。

元の「通常 <10 ms」のレイテンシーおよび「10–15%」の CPU/メモリオーバーヘッドの数値には、このドキュメント内で検証済みの測定ソースがありません。これらは benchmark や sizing guarantee ではなく、**未検証の歴史的推定値**としてここに残されています。enrollment の前後で、同じ request mix、TLS、telemetry sampling、および load を用いて、p50/p95/p99 レイテンシー、throughput、error、CPU/メモリを測定してください。proxy rollout、node loss、control-plane loss、certificate rotation、および retry amplification のテストを含めてください。

専用 namespace で段階的に導入し、1 つの injector、準備完了したワークロード、mTLS、および肯定/否定 policy テストを検証してから拡張してください。mesh ingress gateway の前に LBC を配置する場合は、gateway Service を公開してターゲット port/probe を検証してください。Ingress API object は設定であり、別の proxy hop ではありません。必要に応じてスコープされた controller IAM を使用してください。`cloudmap:*` は `servicediscovery` IAM service prefix の有効な代替ではありません。prefix delegation は IP-capacity の設計上の選択であり、sidecar の前提条件ではありません。実装については、維持管理されている [Istio installation](../../service-mesh/istio/01-installation.md) および [AWS integration](../../service-mesh/istio/04-aws-integration.md) の章を参照してください。

</details>

### 11. Kubernetes Gateway API で L7 load balancing (ALB) に使用する routing resource はどれですか？

A. IngressRoute B. HTTPRoute C. VirtualService D. ServiceRoute

<details>

<summary>回答を表示</summary>

**回答: B. HTTPRoute**

**解説:** Kubernetes Gateway API では、HTTPRoute リソースが L7 load balancing に使用されます。HTTPRoute は HTTP/HTTPS トラフィックを Service にルーティングするルールを定義し、AWS Load Balancer Controller とともに使用すると、ALB を通じてトラフィックを分散します。

**Gateway API リソース階層:**

1. **GatewayClass**: ロードバランサータイプを定義します（例: `amazon-alb`、`amazon-nlb`）
2. **Gateway**: 実際のロードバランサーインスタンス（listener port、TLS 設定など）
3. **HTTPRoute**: L7 ルーティングルール（host、path、header-based routing）
4. **TCPRoute**: L4 ルーティングルール（TCP トラフィック）

LBC は個別の ALB および NLB Gateway を使用します。controllerName は任意の GatewayClass object 名ではなく実装を選択します。release conformance table でサポートされる filter を確認してください。

**主な HTTPRoute 機能:**

* パスおよびホストベースルーティング
* native weight-based traffic splitting
* header および query parameter matching
* 複数のバックエンド Service へのルーティング

他の選択肢に関する問題点:

* **A. IngressRoute**: これは標準 Gateway API リソースではありません。
* **C. VirtualService**: これは Istio service mesh のリソースです。
* **D. ServiceRoute**: このリソースは存在しません。

</details>

### 12. LBC 3.5.0 Gateway controller はどのように有効化されますか？

- A. 常に `--enable-gateway-api` を渡す
- B. 実際のデフォルト有効 gate で互換性のある CRD を検出する
- C. `--feature-gates=EnableGatewayAPI=true` を使用する
- D. 1.2.1 の experimental CRD のみをインストールする

<details>
<summary>回答を表示</summary>

**回答: B. 必要な CRD を検出します。ALBGatewayAPI/NLBGatewayAPI はデフォルトで有効です。**

release 互換の Gateway API 1.6.0 standard CRD と LBC 固有の Gateway CRD をインストールしてください。デフォルト gate は `ALBGatewayAPI` と `NLBGatewayAPI` です。`EnableGatewayAPI` は不明な feature 名です。TCPRoute/UDPRoute は現在 standard channel では v1 として提供されています。以前の controller release には異なる互換性/gating 要件があります。L4 サポートは 2.13.3、L7 は 2.14.0 から開始されます。CRD インストール後に controller startup/log を確認してください。CRD だけでは IAM、subnet、またはアプリケーションバックエンドは提供されません。

</details>

### 13. Gateway API で NLB を介して L4-level TCP トラフィックをルーティングするために使用するリソースはどれですか？

A. HTTPRoute B. TLSRoute C. TCPRoute D. GRPCRoute

<details>

<summary>回答を表示</summary>

**回答: C. TCPRoute**

**解説:** Gateway API では、TCPRoute リソースは L4-level TCP トラフィックのルーティングに使用されます。AWS Load Balancer Controller とともに使用すると、TCPRoute は NLB (Network Load Balancer) を通じて TCP トラフィックをバックエンド Service に転送します。

**TCPRoute 設定例:**

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: TCPRoute
metadata:
  name: db-route
  namespace: gateway-demo
spec:
  parentRefs:
  - name: my-nlb-gateway
    sectionName: tcp
  rules:
  - backendRefs:
    - name: postgres-service
      port: 5432
```

**Gateway API routing resource の使用法:**

| リソース | プロトコル | AWS LB タイプ |
| --------- | ---------- | ----------- |
| HTTPRoute | HTTP/HTTPS | ALB         |
| TCPRoute  | TCP        | NLB         |
| TLSRoute  | TLS        | NLB         |
| GRPCRoute | gRPC       | ALB         |

他の選択肢に関する問題点:

* **A. HTTPRoute**: ALB を使用した HTTP/HTTPS L7 トラフィックに使用されます。
* **B. TLSRoute**: TLS トラフィックルーティング用ですが、TCP-level routing には TCPRoute が適切です。
* **D. GRPCRoute**: gRPC プロトコル専用の routing resource です。

</details>
`my-nlb-gateway` listener とバックエンド Service は `gateway-demo` に存在する必要があります。この実装における TLSRoute は SNI-based NLB routing を提供しません。すべての Gateway API 実装が同様に動作すると仮定するのではなく、release 固有の TLS 動作を使用してください。

### 14. LBC 3.5.0 は ALB Gateway の static certificate をどのように設定しますか？

- A. tls-cert という名前の任意の Secret を作成する
- B. LoadBalancerConfiguration で ACM ARN を使用する
- C. Route hostname のみを追加する
- D. バックエンド Service port を 443 に設定する

<details>
<summary>回答を表示</summary>

**回答: B. `LoadBalancerConfiguration.spec.listenerConfigurations[].defaultCertificate`**

HTTPS listener には、有効な同一 Region の ACM certificate ARN を使用してください。Kubernetes Secret `certificateRefs` はこの実装ではサポートされていません。hostname discovery にも、既存の一致する ACM certificate と secure listener が必要です。backend port 443 のみを持つ HTTPRoute は、client-side HTTPS を設定しません。

</details>

### 15. フロントエンドのみの ingress policy は、既存の同一 namespace allow-all policy を狭めますか？

- A. はい。最新の policy が優先されます
- B. はい。最も具体的な selector が優先されます
- C. いいえ。一致する allow は和集合を形成します
- D. policy 名が最初にソートされる場合のみ

<details>
<summary>回答を表示</summary>

**回答: C. いいえ。一致する NetworkPolicy allow は加算的です。**

両方の policy が backend を選択するため、より広範な同一 namespace allow は、他の同一 namespace caller を引き続き許可します。その所有者を通じてより広範な policy を削除または狭め、その後で許可および拒否される接続をテストしてください。ingress と egress の isolation は独立しています。DNS egress と宛先 ingress のそれぞれがテスト結果に影響する可能性があります。

</details>

公式リファレンス: [LBC Gateway API](https://kubernetes-sigs.github.io/aws-load-balancer-controller/latest/guide/gateway/gateway/), [PrivateLink](https://docs.aws.amazon.com/vpc/latest/privatelink/create-endpoint-service.html), [NLB client IP](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/edit-target-group-attributes.html), [WAF associations](https://docs.aws.amazon.com/waf/latest/developerguide/web-acl-associating-aws-resource.html), [App Mesh retirement](https://docs.aws.amazon.com/app-mesh/latest/userguide/what-is-app-mesh.html).