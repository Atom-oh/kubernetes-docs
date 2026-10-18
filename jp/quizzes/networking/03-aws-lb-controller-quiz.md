# AWS Load Balancer Controller クイズ

セルフマネージド版 LBC v3.6.0 ガイドに基づきます。

## 1. AWS Load Balancer Controller が管理するものは何ですか？

- A. ノードのライフサイクルを含む、クラウドプロバイダーのすべての責務
- B. Kubernetes リソースから調整される、サポート対象の AWS ロードバランサーリソース
- C. kube-proxy によるパケット転送
- D. すべての Pod の CoreDNS レコード

<details>
<summary>解答を表示</summary>

B. LBC は、サポート対象の ALB/NLB、ターゲットグループ、リスナー、および関連リソースを管理します。kube-proxy、CNI、DNS、またはすべてのクラウドコントローラーの責務を置き換えるものではありません。従来の AWS プロバイダーの動作と EKS Auto Mode は別の実装です。LBC がすべての ELB 製品のすべての機能を実装するとは限りません。

</details>

## 2. ALB の `ip` ターゲットと `instance` ターゲットの違いは何ですか？

- A. `ip` は Pod IP を登録し、`instance` はノードの NodePort を経由する
- B. `ip` は常に NodePort を経由する
- C. 両者は同じ
- D. `instance` は IPv6 専用

<details>
<summary>解答を表示</summary>

A. IP ターゲットには、サポート対象で VPC から到達可能な Pod アドレスと、エンドポイント／ENI の検出が必要です。EKS では Amazon VPC CNI が一般的ですが、互換性のある別の CNI 構成も使用できます。Instance ターゲットには NodePort に対応する Service と適切なノードネットワークが必要です。直接ターゲットにすることで、あらゆるワークロードのレイテンシーが改善すると証明されるわけではありません。

</details>

## 3. Controller に IRSA または EKS Pod Identity 経由の IAM ロールが必要なのはなぜですか？

- A. Pod ネットワーキングを置き換えるため
- B. AWS API 呼び出しを認証し、認可するため
- C. Kubernetes RBAC を置き換えるため
- D. すべてのバックエンドリクエストを認証するため

<details>
<summary>解答を表示</summary>

B. Controller はロードバランサー、ターゲットグループ、リスナー、および関連するセキュリティグループを作成／管理するために AWS API を呼び出します。IRSA とサポート対象の Pod Identity 構成は、どちらかを選択できます。ロールで付与されるのは、そのロールにアタッチされたポリシーの権限です。ロールを使うだけで、そのポリシーが自動的に最小権限になるわけではありません。Kubernetes RBAC とアプリケーション認証は別の仕組みです。

</details>

## 4. 複数の Ingress で 1 つの ALB を共有するにはどうしますか？

- A. 同じ namespace に配置する
- B. 同じ `alb.ingress.kubernetes.io/group.name` を使う
- C. すべての Ingress は常に 1 つの ALB を共有する
- D. 同じ Pod 名を設定する

<details>
<summary>解答を表示</summary>

B. IngressGroup により、ALB とそのルール領域を共有できます。小さい `group.order` の値が先に評価され、値が同じ場合は namespace／name の順になります。グループに参加できる信頼されていないユーザーがルーティングに影響できるため、強制された信頼境界の内側でのみ使ってください。すべての構成でコストが下がると決めつけず、annotation のマージ／排他動作や制限、コストを確認してください。

</details>

## 5. NLB の TLS 証明書を指定する annotation はどれですか？

- A. `service.beta.kubernetes.io/aws-load-balancer-ssl-cert`
- B. `alb.ingress.kubernetes.io/certificate-arn`
- C. `service.beta.kubernetes.io/aws-load-balancer-tls-termination`
- D. `nlb.kubernetes.io/ssl-certificate`

<details>
<summary>解答を表示</summary>

A. セルフマネージド LBC での Service 全体の例です。

```yaml
apiVersion: v1
kind: Service
metadata:
  name: nlb-tls-service
  namespace: default
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip
    service.beta.kubernetes.io/aws-load-balancer-scheme: internal
    service.beta.kubernetes.io/aws-load-balancer-ssl-cert: arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012
    service.beta.kubernetes.io/aws-load-balancer-ssl-ports: '443'
    service.beta.kubernetes.io/aws-load-balancer-backend-protocol: tcp
spec:
  type: LoadBalancer
  loadBalancerClass: service.k8s.aws/nlb
  selector:
    app: my-app
  ports:
  - name: https
    port: 443
    targetPort: 8080
    protocol: TCP
```

証明書 ARN を置き換え、8080 で待ち受けるバックエンド Pod を用意してください。クライアント側の TLS は NLB で終端します。ここで `tcp` を指定すると、バックエンドへの接続は TLS で暗号化されません。適切な証明書／セキュリティポリシーとネットワーク制御を使ってください。Auto Mode は独自の `loadBalancerClass` とサポート対象 annotation を使用します。

</details>

## 6. 独立して作成した TargetGroupBinding の目的は何ですか？

- A. すべてのロードバランサーとリスナーを自動作成する
- B. Kubernetes Service のターゲットを既存のターゲットグループに登録する
- C. ALB の HTTP リスナールーティングルールを定義する
- D. IAM 認可を置き換える

<details>
<summary>解答を表示</summary>

B. ロードバランサー、リスナー、ターゲットグループはすでに存在し、Service／ターゲットのプロトコル、アドレスファミリー、ポートに一致している必要があります。

```yaml
apiVersion: elbv2.k8s.aws/v1beta1
kind: TargetGroupBinding
metadata:
  name: my-tgb
  namespace: default
spec:
  targetGroupARN: arn:aws:elasticloadbalancing:us-east-1:123456789012:targetgroup/my-tg/1234567890abcdef
  serviceRef:
    name: my-service
    port: 80
  targetType: ip
```

複数のクラスター／TGB で共有するターゲットグループでは、作成時からすべての参加者に `multiClusterTargetGroup: true` が必要です。既定ではターゲットグループ全体を所有するとみなされ、ほかの参加者のターゲットを登録解除する場合があります。`nodeSelector` は instance ターゲットに適用され、IP モードの Pod を絞り込むものではありません。TGB の権限は信頼されたユーザーに限定してください。

</details>

## 7. ALB にリージョンの WAF v2 Web ACL を関連付ける annotation はどれですか？

- A. `alb.ingress.kubernetes.io/waf-acl-id`
- B. `alb.ingress.kubernetes.io/wafv2-acl-arn`
- C. `alb.ingress.kubernetes.io/web-acl`
- D. `alb.ingress.kubernetes.io/firewall-rules`

<details>
<summary>解答を表示</summary>

B. ALB と同じリージョンにある既存の Web ACL ARN を指定し、そのルールを構成して、Controller に必要な権限を付与してください。WAF v2 統合を有効にする必要がありますが、既定で有効なため、`enableWafv2` を明示的に設定することが常に必要なわけではありません。統合が無効なら、この annotation は適用されません。WAF と有料の Shield Advanced 保護は別の機能です。

</details>

## 8. 従来のサブネットロールタグはどれですか？

- A. `kubernetes.io/cluster/CLUSTER_NAME` のみ
- B. パブリック用 `kubernetes.io/role/elb` とプライベート用 `kubernetes.io/role/internal-elb`
- C. `aws:cloudformation:stack-name`
- D. `Name=kubernetes-subnet` のみ

<details>
<summary>解答を表示</summary>

B. セルフマネージド LBC の検出では、値に `1` または空文字列を指定できます。v2.12.1 以降は、一致するロールタグがない場合、既定の到達可能性ベースの代替判定によりルートテーブルからサブネットを分類できます。明示的なサブネット指定や IngressClassParams のタグフィルターも選択方法です。Auto Mode では、引き続き文書化されたタグが必要です。クラスタータグ、空き IP 数、AZ 要件を確認してください。タグでルーティングが変更されることはありません。

</details>

## 9. ALB のスティッキーセッションはどのように構成しますか？

- A. `alb.ingress.kubernetes.io/sticky-sessions=true`
- B. `stickiness.enabled=true` を含む `target-group-attributes`
- C. Ingress の `session-affinity=cookie`
- D. 常に既定で有効

<details>
<summary>解答を表示</summary>

B. `alb.ingress.kubernetes.io/target-type: ip` を設定し、適切な cookie 属性と `stickiness.enabled=true` を 1 つの `target-group-attributes` annotation に指定します。slow start や deregistration delay の設定で YAML キーを重複させないでください。重複キーがあると設定が破棄される場合があります。重み付き forward action では、文書化されているとおり、ターゲットグループのスティッキー設定を整合させてください。

</details>

## 10. NLB のクライアント識別情報について正しい説明はどれですか？

- A. Proxy Protocol v2 は IP パケットの送信元をクライアントアドレスに変更する
- B. `externalTrafficPolicy: Local` はすべてのターゲットモードで保持を保証する
- C. Proxy Protocol はメタデータを伝える。パケット送信元の保持は、ネットワーク／プロトコル上の制約がある別の設定である
- D. NLB は常にクライアント IP を保持する

<details>
<summary>解答を表示</summary>

C. バックエンドはアプリケーションデータより前に Proxy Protocol v2 を解析し、該当するヘルスチェックにも対応する必要があります。`preserve_client_ip.enabled` は、サポートされる場合に IP パケットの送信元保持を制御します。Instance／NodePort モードでは、`externalTrafficPolicy: Local` により後段の kube-proxy による SNAT を避けられる場合がありますが、すべての NLB 経路や IP ファミリー変換に対応するわけではありません。重み付き NLB ターゲットでは、通常の重み変更は新しい接続に影響しますが、重みを 0 にすると、短時間のうちに既存接続も閉じられます。

</details>

## 11. ALB の HTTP から HTTPS へのリダイレクトを設定する annotation はどれですか？

- A. `alb.ingress.kubernetes.io/force-ssl-redirect`
- B. `alb.ingress.kubernetes.io/ssl-redirect: "443"`
- C. `alb.ingress.kubernetes.io/http-to-https`
- D. HTTPRoute が常に必要

<details>
<summary>解答を表示</summary>

B. HTTP リスナーと転送先の HTTPS リスナーの両方、および適切な証明書を構成してください。有効にすると、HTTP リスナーは既定アクションとしてリダイレクトを使い、そのほかのルーティングルールは無視されます。IngressGroup 全体に影響するため、グループ全体の動作を確認してください。Cognito／OIDC／JWT 認証には HTTPS が必要です。リダイレクトだけではアプリケーションの認可になりません。

</details>

## 12. ALB が作成されないとき、最初に何を確認しますか？

- A. kube-proxy のログのみ
- B. アプリケーションの cookie の内容
- C. Controller のログ／イベント、クラス選択、IAM、サブネットの適格性、webhook／CRD の正常性
- D. Pod レプリカ数のみ

<details>
<summary>解答を表示</summary>

C. まず調整／コントロールプレーンの経路を確認します。kube-proxy または eBPF による置き換えは、その後のノード／Service トラフィックに影響することがありますが、AWS の `CreateLoadBalancer` 操作が失敗したときの最初の診断対象ではありません。`kubectl apply` が成功しても、AWS 側の調整が成功した証明にはなりません。実際のリソース ID、namespace、出力範囲を限定したログを使ってください。

</details>

[ガイドに戻る](../../networking/03-aws-lb-controller.md)
