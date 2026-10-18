# EKS ネットワーキングクイズ - 第1部

> **最終更新**: 2026年9月11日

このクイズでは、EKS のネットワーキング、アドレス設計、ポリシー、コントローラーの責任範囲を確認します。特に記載がない限り、例は一般的な Linux EC2 ネットワーキングを前提とします。API と設定は公式資料およびローカルスキーマで確認しました。クラウドのネットワーキング変更や実際のパケットテストは実施していません。

## 選択問題

1. 一般的な EKS の EC2 ノードでデフォルトの CNI はどれですか？
   * A) Calico
   * B) Flannel
   * C) Amazon VPC CNI
   * D) Weave Net

<details>
<summary>回答を表示</summary>

**正解: C) Amazon VPC CNI**

一般的な EKS EC2 ノードでは Amazon VPC CNI を使用します。Auto Mode は管理されたネットワーキング機能を提供し、Hybrid Nodes はサポート対象の別の CNI を使用するため、「すべての EKS クラスターでこの DaemonSet が動く」とするのは範囲が広すぎます。

CNI は、セカンダリ IP、プレフィックス、Pod 用セキュリティグループなど、複数の方式で VPC アドレスを使った通常の Pod ネットワーキングを構成します。到達可能なアドレスであっても、ルート、セキュリティグループ、NACL、ポリシーを迂回できるわけではありません。また、オーバーレイを使わないことは、測定済みの性能保証にはなりません。

Linux では、キーが小文字の `warm-ip-target` や `enable-pod-eni` の旧 `amazon-vpc-cni` ConfigMap は、ここで示す設定方法ではありません。実際のアドオンスキーマや Helm 値、または設定の所有者が管理するサポート対象の `aws-node` 環境変数を使用してください。まずインストール済みビルドを確認します。

```bash
set -euo pipefail
CNI_ADDON_VERSION=$(aws eks describe-addon --cluster-name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --addon-name vpc-cni --query addon.addonVersion --output text)
aws eks describe-addon-configuration --region "$EXAMPLE_REGION" --addon-name vpc-cni \
  --addon-version "$CNI_ADDON_VERSION" --query configurationSchema --output text
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" -n kube-system get daemonset aws-node \
  -o jsonpath='{range .spec.template.spec.containers[*]}{.name}{": "}{.image}{"\n"}{end}'
```

たとえば、次は Kubernetes ConfigMap ではなく、**アドオン設定の断片**です。値はウォームプールの例です。レビュー済みの既存設定に統合し、選択したバージョンのスキーマを確認してください。Windows IPAM の ConfigMap 設定は別のインターフェイスです。

```json
{"env":{"WARM_IP_TARGET":"5","MINIMUM_IP_TARGET":"10"}}
```

Pod 用セキュリティグループとネイティブ NetworkPolicy には、それぞれ追加の前提条件があります。IP プールの例と無関係な副作用として有効にしたり、稼働中のクラスターへ未設定の第 2 CNI を適用したりしないでください。

</details>

2. IPv4 セカンダリ IP モードでは、通常の Pod にどのようにアドレスを割り当てますか？
   * A) Pod ごとの専用 VPC から割り当てる
   * B) ノードの ENI/IP プールから割り当てる
   * C) オーバーレイアドレスだけを割り当てる
   * D) Pod ごとに別のサブネットを使う

<details>
<summary>回答を表示</summary>

**正解: B) ノードの ENI/IP プールから割り当てる**

通常の IPv4 セカンダリ IP モードでは、ノード上の IPAMD が ENI/IP プールを管理し、CNI のセットアップ時にプールのアドレスを Pod のネットワーク名前空間へ割り当てます。CNI のクリーンアップと該当する再利用待ち時間が終わると、アドレスはウォームプールへ戻ることがあります。EC2 から直ちに割り当て解除されるとは限りません。

次の従来型 max-Pods 計算はこのモード向けです。各 ENI のプライマリアドレスは予約され、末尾の `+ 2` は hostNetwork を使うシステム Pod を考慮した歴史的な値です。

```text
ENIs × (IPv4 addresses per ENI − 1) + 2
m5.large: 3 × (10 − 1) + 2 = 29
```

これはすべてのワークロードに共通する上限ではありません。サブネットのアドレス空間、kubelet の `maxPods`、コンピュートリソース、カスタムネットワーキング、branch ENI の上限も関係します。プレフィックスモードでは `/28` が ENI のアドレススロットを 1 つ使い、ENI ごとに必ず 1 プレフィックスとなるわけではありません。Pod 用セキュリティグループは別の branch ENI 経路を使います。hostNetwork Pod はノードのネットワーキングを共有するため、「Pod 1 つにつきセカンダリ IP 1 つ」という単純な説明には当てはまりません。

</details>

3. 通常の VPC CNI で VPC 内ルーティングが可能になるのはなぜですか？
   * A) すべての Pod が同じサブネットを使うから
   * B) すべての Pod がホストネットワークを共有するから
   * C) 必要なルートと制御の下で、VPC からルーティング可能な Pod アドレスを使うから
   * D) サービスメッシュが必須だから

<details>
<summary>回答を表示</summary>

**正解: C) 必要なルートと制御の下で、VPC からルーティング可能な Pod アドレスを使うから**

通常の VPC CNI 経路では、Pod は VPC からルーティング可能なアドレスを持ちます。ノード間通信にはノード/ENI と VPC のルーティングを利用でき、同一ノード内の通信はホストのネットワーキングスタック内に留まる場合があります。到達性は引き続き、セキュリティグループ、NACL、ポリシールール、カスタム検査ルートで決まります。

例の `10.0.1.23 → 10.0.2.45` は一般的な VPC 内通信を示すもので、すべてのパケットが常に VPC ルートテーブルを通る、または設定済みのアプライアンス経路を通らないという証明ではありません。同一ノード内の Pod 通信は VPC Flow Logs から完全には見えません。ほとんどの Pod は独自のネットワーク名前空間を持ちますが、hostNetwork Pod は例外です。

オーバーレイを使わないことから、レイテンシーやスループットの向上が保証されるとは推論しないでください。実際の経路を測定し、AZ 間転送、ターゲット種別、SNAT、ワークロードの動作を考慮してください。サービスメッシュは追加できる任意のレイヤーであり、通常の Pod ルーティングの前提条件ではありません。

</details>

4. Pod の ingress/egress ポリシーを表す Kubernetes リソースはどれですか？
   * A) Service
   * B) Ingress
   * C) NetworkPolicy
   * D) SecurityContext

<details>
<summary>回答を表示</summary>

**正解: C) NetworkPolicy**

NetworkPolicy は Pod を選択し、指定されたトラフィック方向だけを隔離します。ポリシーが Pod と方向を選択していなければ、そのトラフィックは隔離されません。ポリシーは加算的です。制限が厳しく見えるポリシーを追加しても、別のポリシーがすでに許可している通信は取り消せません。

互換性のある適用機構を使ってください。現在の Amazon VPC CNI は、有効にするとネイティブネットワークポリシーをサポートします。適用できないという古い説明は誤りです。マネージドアドオンでは `ENABLE_NETWORK_POLICY` 環境変数ではなく、`enableNetworkPolicy` 設定フィールドを使います。

```json
{"enableNetworkPolicy":"true"}
```

これは選択したアドオンのバージョン/スキーマへ統合する断片です。テスト前に、ポリシーエージェントと AWS のコンピュート、カーネル、Pod 所有者、インターフェイスに関する制約を確認してください。標準の起動モードでは、ポリシーが Pod に関連付けられるまで一時的に通信が許可される場合があります。strict 起動モードでは、必要なシステム通信と DNS の許可がすべて必要です。サポート対象の移行設計なしに、固定されていない Calico マニフェストとネイティブポリシー適用を同時に導入しないでください。

次はレビュー済みのラボ用 namespace とコントローラー管理下のワークロードを対象とします。同じ peer item 内の namespace selector と Pod selector は AND 条件です。peer item を分けると OR 条件になります。DNS の例外は明示しています。

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-allow
  namespace: policy-lab
spec:
  podSelector:
    matchLabels: {app: api}
  policyTypes: [Ingress, Egress]
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: frontend-lab
      podSelector:
        matchLabels: {role: frontend}
    ports:
    - {protocol: TCP, port: 8080}
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: database-lab
      podSelector:
        matchLabels: {app: database}
    ports:
    - {protocol: TCP, port: 5432}
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels: {k8s-app: kube-dns}
    ports:
    - {protocol: UDP, port: 53}
    - {protocol: TCP, port: 53}
```

実際の namespace/Pod ラベルと listener port を使ってください。NodeLocal DNSCache など別の DNS 経路には、異なる許可設定が必要です。Service/Ingress はトラフィックをルーティングしますが、L3/L4 のアクセスルールを置き換えるものではありません。SecurityContext が制御するのはワークロードの権限であり、宣言的なネットワーク許可リストではありません。

</details>

5. 一般的な EKS クラスターのサービスディスカバリーには、通常どの DNS コンポーネントを設定しますか？
   * A) Route 53 の private hosted zone だけ
   * B) CoreDNS
   * C) 古い kube-dns Deployment が必須
   * D) Cloud Map だけ

<details>
<summary>回答を表示</summary>

**正解: B) CoreDNS**

一般的な EKS では、クラスター DNS に CoreDNS を使用します。すべての EKS モードで CoreDNS Deployment が自動的に可視化されるとは限りません。Auto Mode は管理された DNS を提供し、デフォルトのブートストラップアドオンを無効にするツールを使う場合は、選択したアドオンを明示的に設定する必要があります。

EKS マネージド CoreDNS アドオンでは、サポート対象の `corefile` 設定値と正確なバージョンのスキーマを使ってカスタム設定を保持してください。ConfigMap を直接編集するとアドオンに上書きされることがあります。セルフマネージド CoreDNS では、マニフェスト/GitOps の所有者を通じて設定を変更してください。一般的なサンプルで ConfigMap 全体を置き換えるのではなく、必要な `ready`、転送先、Kubernetes zone、再読み込み動作を確認してください。

DNS 応答はリソースの種類によって異なります。

| リソース | 一般的な DNS の動作 |
| --- | --- |
| 通常の Service | `<service>.<namespace>.svc.<cluster-domain>` は Service の IP family に対応する IP に解決される |
| Headless Service | readiness/公開設定に応じた Endpoint アドレスを返す |
| ExternalName Service | 設定された外部名への CNAME を返す |
| 旧形式の IPv4 Pod record | CoreDNS の `pods` mode に応じて、`10-0-1-23.<namespace>.pod.<cluster-domain>` のようなハイフン区切りアドレスを返す |

`cluster.local` は一般的なデフォルトですが、すべての環境で共通するドメインではありません。`pods insecure` は Pod の存在を検証せずに、旧形式の IP ベース応答を返します。これはセキュリティ保証ではありません。DNS は任意のラップトップの resolver ではなく、許可されたクラスター内の診断ワークロードからテストしてください。

互換性のあるアドオンバージョンでは、EKS マネージド CoreDNS の自動スケーリングを設定できます。レプリカ数を管理する所有者を 1 つにしてください。マネージド自動スケーリング/HPA が有効な場合、手動の `kubectl scale` は適切な制御ループではありません。

次は既存の cache stanza をレビュー後に置き換える **Corefile の断片**です。YAML ではありません。CoreDNS 1.14.7 は `denial 1000` を受け付けますが、実効最小容量の 1024 に正規化します。この例ではその容量を明示しています。`success 10000` は 9984 に切り下げられます。

```text
cache {
    success 10000
    denial 1024
    prefetch 10 10m 20%
}
```

cache 容量、TTL、prefetch 設定はワークロードの測定に基づいて決めてください。これは性能ベンチマークではありません。制御された変更後に DNS エラー、cache の動作、CPU/メモリを観察してください。

</details>

## 短答問題

6. Pod 密度を制限する要因は何ですか。また、プレフィックス委任でどう変わりますか？

<details>
<summary>回答を表示</summary>

次の 3 つの上限を分けて考えてください。EC2 インターフェイス/アドレス容量、利用可能なサブネットアドレス、Kubernetes/コンピュート容量です。それぞれに異なる対処が必要です。通常の IPv4 セカンダリ IP モードで使われてきた計算式は `ENIs × (IPs per ENI − 1) + 2` で、t3.small は 11、m5.large は 29、c5.4xlarge は 234 になります。これは式から得られる値であり、すべてのマネージドグループで有効な上限ではありません。

IPv4 プレフィックスモードでは、1 つの `/28` が 16 アドレスを提供し、セカンダリアドレス用スロットを 1 つ使います。1 つの ENI に複数のプレフィックスを割り当てられます。「ENI ごとにプレフィックスは 1 つだけ」として m5.large が 47 になる旧計算は誤りでした。互換性のあるマネージドグループでは、30 vCPU 未満なら maxPods は 110、30 vCPU 以上なら 250 が上限です。CPU/メモリや実際の CNI 設定によって、使用可能なワークロード容量はさらに小さくなる場合があります。

マネージドアドオン設定の例です。

```json
{"env":{"ENABLE_PREFIX_DELEGATION":"true","WARM_PREFIX_TARGET":"1"}}
```

統合前に、正確なバージョンのスキーマと既存設定を確認してください。`WARM_PREFIX_TARGET` は空きプレフィックス容量であり、ENI ごとにプレフィックスを 1 つまでにする設定ではありません。`WARM_IP_TARGET`/`MINIMUM_IP_TARGET` を設定すると、これらがその動作を上書きします。プレフィックスモードには連続した `/28` アドレス空間と、サポート対象のインスタンス/CNI が必要です。サブネット自体のアドレス空間は増えません。

プレフィックス委任と Pod 用セキュリティグループは併用できます。ただし、branch ENI を使う Pod にはインスタンスごとの branch 容量の上限があり、プレフィックスによって増えることはありません。変数を切り替えれば既存 Pod と maxPods がすべて変更されると想定せず、新規/再作成ノードと PDB に配慮した移行を計画してください。カスタム AL2023 AMI では、レビュー済み NodeConfig の maxPods 設定が必要な場合があります。kubelet の上限だけを上げても、IP や CPU は増えません。

```bash
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" get nodes \
  -o custom-columns=NAME:.metadata.name,PODS:.status.allocatable.pods,POD_ENI:.status.allocatable.vpc\\.amazonaws\\.com/pod-eni
```

実際の割り当て可能容量と CNI/EC2 の割り当て状況を確認してください。`aws-node` コンテナに `curl` が含まれるとは限りません。インストール済みビルドと選択したノード向けの、文書化された introspection/debug 手順を使ってください。

</details>

7. 一般的な EKS EC2 ノードで、選択した Pod にセキュリティグループを割り当てるにはどうしますか？

<details>
<summary>回答を表示</summary>

Pod 用セキュリティグループでは、ノード上の **trunk ENI と、選択した Pod 用の branch ENI** を使用します。EKS VPC resource controller は、`AmazonEKSVPCResourceController` を含む **クラスター IAM ロール**の権限を使ってこの経路を作成/管理します。これは単純な Pod ごとの ServiceAccount 権限ではありません。

一般的な Linux EC2 の例では、trunking 対応のインスタンスタイプ（すべての Nitro タイプが対象ではありません）、互換性のある VPC CNI、設定の所有者を通じた `ENABLE_POD_ENI=true` を確認してください。`POD_SECURITY_GROUP_ENFORCING_MODE`、DNS/プローブ、ルート、セキュリティグループルールも確認します。strict mode と standard mode では、SNAT と、特に VPC 外やノードローカルの経路で適用されるセキュリティグループが異なります。

専用の `sgp-lab` namespace を作成し、セキュリティグループの仮値を同じ VPC 内の承認済みグループに置き換えます。コントローラー管理下のスリープ中の client で、選択動作を確認します。データベースに接続できることを示すものではありません。

```yaml
apiVersion: vpcresources.k8s.aws/v1beta1
kind: SecurityGroupPolicy
metadata:
  name: db-client-policy
  namespace: sgp-lab
spec:
  podSelector:
    matchLabels: {role: db-client}
  securityGroups:
    groupIds: [sg-REPLACE_WITH_APPROVED_GROUP]
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: db-client
  namespace: sgp-lab
spec:
  replicas: 1
  selector:
    matchLabels: {role: db-client}
  template:
    metadata:
      labels: {role: db-client}
    spec:
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        seccompProfile: {type: RuntimeDefault}
      containers:
      - name: client
        image: public.ecr.aws/docker/library/busybox:1.38.0
        command: [sleep, '3600']
        resources:
          requests: {cpu: 10m, memory: 16Mi}
          limits: {cpu: 100m, memory: 32Mi}
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities: {drop: [ALL]}
```

必要に応じて `podSelector` または `serviceAccountSelector` を使ってください。新しく作成された Pod、CNINode/branch 容量、許可/拒否されるアプリケーション接続を検証します。SecurityGroupPolicy の選択を変更しても、実行中の Pod に遡って適用されるわけではありません。セキュリティグループルール自体の変更には、別途 connection tracking の挙動があります。host-network Pod はノードのネットワーキングを使います。

プレフィックス委任とは併用できますが、branch ENI を使う Pod の容量は増えません。従来の SecurityGroupPolicy 機能は、Auto Mode の NodeClass による Pod サブネット/セキュリティグループ選択機能とは別です。同一のものとして扱わず、適用するコンピュート方式に合った API を使用してください。

</details>

8. LoadBalancer Service に対して AWS Load Balancer Controller が作成するロードバランサーと、所有権の設定方法は何ですか？

<details>
<summary>回答を表示</summary>

AWS Load Balancer Controller は LoadBalancer Service を **NLB** に調整します。CLB ではありません。旧クイズでは、これを従来の組み込み Service controller と混同していました。現在の LBC では所有権を明示する `service.k8s.aws/nlb` を使い、v2.2 以降に新規作成される NLB のデフォルトは **internal** です。意図した scheme を明示的に設定してください。

これは、レビュー済みの既存 `app=echo` ワークロードに対する `lb-lab` namespace 内の新しい Service です。controller のインストールと権限設定を行い、対象サブネット/セキュリティグループの適合性を確認した後に使ってください。課金対象となる internal NLB が作成されるため、本番 namespace に不用意に適用しないでください。

```yaml
apiVersion: v1
kind: Service
metadata:
  name: echo-nlb
  namespace: lb-lab
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-scheme: internal
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip
spec:
  type: LoadBalancer
  loadBalancerClass: service.k8s.aws/nlb
  allocateLoadBalancerNodePorts: false
  selector: {app: echo}
  ports:
  - name: http
    port: 8080
    targetPort: 8080
    protocol: TCP
```

IP target は対象となる Pod IP に直接トラフィックを送ります。instance target はノード/NodePort 経路を使います。IP mode の例では未使用の NodePort 割り当てを無効化しています。Auto Mode は専用の所有クラス `eks.amazonaws.com/nlb` とサポート対象の設定一式を使います。既存の legacy Service で controller 選択用 annotation/class を変更して、未レビューの移行を試みないでください。リソースが残留したり、意図せず公開されたりすることがあります。

**設定の選択肢**は、選択した controller バージョンと listener 設計に合わせてください。表の annotation 名からは、共通の `service.beta.kubernetes.io/` prefix を省いています。

| 要件 | 現行の設定/考慮事項 |
| --- | --- |
| internal/public scheme | `aws-load-balancer-scheme: internal` または `internet-facing`。ルート/サブネットも合わせる |
| IP target | `aws-load-balancer-nlb-target-type: ip` |
| 独自の frontend SG | `aws-load-balancer-security-groups`。backend ルール管理と health check 経路を確認する |
| 明示的なサブネット | `aws-load-balancer-subnets`。適合性/AZ/IP の制約は引き続き適用される |
| cross-zone 動作 | `aws-load-balancer-attributes` の `load_balancing.cross_zone.enabled`。可用性、トポロジー、コストを評価する |
| 旧形式の S3 access log | `aws-load-balancer-attributes` の `access_logs.s3.*`。NLB access log が対象とするのは TLS request のみ。レビュー済みの bucket と配信権限が必要 |
| TLS termination | `aws-load-balancer-ssl-cert` と、Service listener port に対応する `aws-load-balancer-ssl-ports`。これは NLB の TLS termination で、ALB の HTTP routing ではない |

旧 `aws-load-balancer-internal`、cross-zone、access-log annotation は非推奨であり、scheme/attribute 設定が推奨されています。現在の NLB は CloudWatch log 配信の拡張機能も提供しています。S3 annotation で設定できると想定せず、文書化された統合方法を選んでください。access log は best effort で、すべての request を記録するものではありません。

**ALB を使う場合:** `alb` IngressClass を設定した Ingress と、ClusterIP backend への IP target を使用します。これにより、同じ backend の例に NLB と ALB の両方を誤って作成することを避けられます。

```yaml
apiVersion: v1
kind: Service
metadata:
  name: echo-backend
  namespace: lb-lab
spec:
  type: ClusterIP
  selector: {app: echo}
  ports:
  - {port: 8080, targetPort: 8080, protocol: TCP}
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: echo-alb
  namespace: lb-lab
  annotations:
    alb.ingress.kubernetes.io/scheme: internal
    alb.ingress.kubernetes.io/target-type: ip
spec:
  ingressClassName: alb
  rules:
  - http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: echo-backend
            port: {number: 8080}
```

インストール前に、controller の ServiceAccount と最小権限の IAM permission を準備してください。確認した chart 3.5.0 には controller v3.5.0 が含まれます。IMDS による検出ができない環境では、Region/VPC を明示します。デプロイ前に render して内容を確認してください。

```bash
helm repo add eks https://aws.github.io/eks-charts
helm repo update eks
helm template aws-load-balancer-controller eks/aws-load-balancer-controller \
  --version 3.5.0 --kube-version 1.36.0 --namespace kube-system \
  --set-string clusterName="${EXAMPLE_CLUSTER:?}" \
  --set-string region="${EXAMPLE_REGION:?}" --set-string vpcId="${EXAMPLE_VPC_ID:?}" \
  --set serviceAccount.create=false --set-string serviceAccount.name=aws-load-balancer-controller \
  > lbc-reviewed.yaml
```

| 機能 | CLB（legacy） | NLB | ALB |
| --- | --- | --- | --- |
| 主なルーティング層 | L4/L7 legacy listener | L4 | HTTP/HTTPS L7 |
| IP target へ直接転送 | いいえ | はい | はい |
| AZ ごとの静的アドレス選択肢 | いいえ | はい | ネイティブの静的 frontend IP はなし |
| HTTP path routing | いいえ | いいえ | はい |

NLB は現在、TCP、TLS、UDP、TCP_UDP、QUIC、TCP_QUIC listener をサポートします。controller 側のサポート/設定は別途確認してください（LBC 3.5 は QUIC port annotation を文書化しています）。旧クイズの定性的な「良い/非常に良い」という性能表はベンチマークではありません。アプリケーションに合わせて選択・測定してください。cross-zone を一律に有効化したり、普遍的なレイテンシー順位を本番ルールにしたりしないでください。

</details>

## ハンズオン問題

9. 同一 namespace 内の通信を許可し、DNS の例外を設けつつ、namespace をまたぐ TCP 通信を遮断して検証してください。

<details>
<summary>回答を表示</summary>

対象 namespace 内のすべての Pod を選択するポリシーを使い、同一 namespace の peer と明示的な DNS 例外だけを許可します。これは L3/L4 ポリシーであり、テナントやノードを完全に隔離できる証明ではありません。

**前提条件:** 承認済みの一般的な IPv4 Linux テストクラスターで、サポート対象の所有者/設定を通じて VPC CNI のネイティブ NetworkPolicy が有効になっていること、テスト Pod がコントローラー管理下にあること、CoreDNS が動作していること、組織全体に適用される競合ポリシーがないこと。ラボの一部として Calico をインストールしたり、架空の `ENABLE_NETWORK_POLICY` 変数を切り替えたりしないでください。

新しい namespace を 2 つ作成し、それぞれの UID を記録します。以降のスニペットは、1 つの Bash session で実行してください。

```bash
set -euo pipefail
umask 077
: "${EXAMPLE_KUBECONFIG:?Use the reviewed IPv4 Linux lab cluster kubeconfig}"
NP_LAB_DIR=$(mktemp -d /tmp/eks-network-policy.XXXXXX)
NP_LAB_ID="$(date +%s)-$$"
NP_NAMESPACE_A="np-a-$NP_LAB_ID"
NP_NAMESPACE_B="np-b-$NP_LAB_ID"
for ns in "$NP_NAMESPACE_A" "$NP_NAMESPACE_B"; do
  kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" create namespace "$ns" -o json \
    > "$NP_LAB_DIR/$ns-created.json"
  jq -e '.metadata.uid | type == "string" and length > 0' \
    "$NP_LAB_DIR/$ns-created.json" >/dev/null
done
```

HTTP server は既知の Python TCP 診断も提供します。各 Service と container は port 8080 を使います。これはテスト用ワークロードであり、本番向けのサイジング例ではありません。再現性のため image digest を記録してください。

```bash
for ns in "$NP_NAMESPACE_A" "$NP_NAMESPACE_B"; do
  kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n "$ns" create -f - <<'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: network-probe
spec:
  replicas: 1
  selector:
    matchLabels: {app: network-probe}
  template:
    metadata:
      labels: {app: network-probe}
    spec:
      automountServiceAccountToken: false
      nodeSelector: {kubernetes.io/os: linux}
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        seccompProfile: {type: RuntimeDefault}
      containers:
      - name: probe
        image: python:3.13-alpine
        command: [python, -m, http.server, "8080", --directory, /tmp]
        ports:
        - containerPort: 8080
        readinessProbe:
          tcpSocket: {port: 8080}
        resources:
          requests: {cpu: 50m, memory: 64Mi}
          limits: {cpu: 200m, memory: 128Mi}
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities: {drop: [ALL]}
---
apiVersion: v1
kind: Service
metadata:
  name: network-probe
spec:
  type: ClusterIP
  selector: {app: network-probe}
  ports:
  - {port: 8080, targetPort: 8080, protocol: TCP}
EOF
  kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n "$ns" \
    rollout status deployment/network-probe --timeout=180s
done
```

**baseline:** ポリシーを適用する前に、同一 namespace と namespace 間の TCP 接続がどちらも成功することを確認してください。DNS/exec の失敗と、拒否された TCP 接続は区別します。ICMP ping は NetworkPolicy 適用を検証する汎用的な方法ではありません。

```bash
check_tcp() {
  kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n "$1" exec deployment/network-probe \
    -c probe -- python -c '
import socket, sys
try:
    address = socket.gethostbyname(sys.argv[1])
except OSError as error:
    print("DNS failed:", error, file=sys.stderr)
    sys.exit(43)
try:
    connection = socket.create_connection((address, 8080), timeout=3)
    connection.close()
except OSError as error:
    print("TCP failed:", error, file=sys.stderr)
    sys.exit(42)
print("TCP succeeded")
' "network-probe.$2"
}

# All four paths must work before applying the policy.
check_tcp "$NP_NAMESPACE_A" "$NP_NAMESPACE_A"
check_tcp "$NP_NAMESPACE_B" "$NP_NAMESPACE_B"
check_tcp "$NP_NAMESPACE_A" "$NP_NAMESPACE_B"
check_tcp "$NP_NAMESPACE_B" "$NP_NAMESPACE_A"
```

**namespace A のみへ適用:** 空の peer `podSelector` は、そのポリシーが属する namespace 内の Pod を選択します。DNS peer は `kube-system` namespace と CoreDNS Pod label を組み合わせます。NodeLocal DNSCache など別の DNS 経路では、許可ルールを調整してください。標準モードではポリシーの関連付けは非同期で行われるため、正常系の通信確認を行い、双方向の遮断経路もテストして反映を確認します。

```bash
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n "$NP_NAMESPACE_A" create -f - <<'EOF'
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: namespace-boundary
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
  ingress:
  - from:
    - podSelector: {}
  egress:
  - to:
    - podSelector: {}
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - {protocol: UDP, port: 53}
    - {protocol: TCP, port: 53}
EOF

expect_tcp_block() {
  if check_tcp "$1" "$2"; then
    return 1
  else
    result=$?
    [ "$result" -eq 42 ] || {
      printf '%s\n' 'DNS or exec failure is not proof of policy denial.' >&2
      exit 1
    }
    return 0
  fi
}
NP_VERIFIED=false
for attempt in $(seq 1 30); do
  check_tcp "$NP_NAMESPACE_A" "$NP_NAMESPACE_A"
  check_tcp "$NP_NAMESPACE_B" "$NP_NAMESPACE_B"
  if expect_tcp_block "$NP_NAMESPACE_A" "$NP_NAMESPACE_B" &&
     expect_tcp_block "$NP_NAMESPACE_B" "$NP_NAMESPACE_A"; then
    # Repeat positive controls after observing both blocked cross-namespace paths.
    check_tcp "$NP_NAMESPACE_A" "$NP_NAMESPACE_A"
    check_tcp "$NP_NAMESPACE_B" "$NP_NAMESPACE_B"
    NP_VERIFIED=true
    break
  fi
  sleep 2
done
[ "$NP_VERIFIED" = true ] || {
  printf '%s\n' 'Expected policy behavior was not observed; inspect the enforcement path.' >&2
  exit 1
}
```

成功とするには、DNS と server の稼働確認が通ったうえで、テストした TCP 経路が期待どおりに動作する必要があります。これですべての protocol/interface がフィルタリングされると証明されるわけではありません。プラットフォームのノード、metadata service、セキュリティグループの制御は別途維持してください。

**拡張:** 同一 namespace 内でも特定の Pod や port だけ許可する場合は、広範な同一 namespace 許可を置き換えるかレビューしてください。より限定的なポリシーを追加しても、既存の広い許可は取り消せません。レビュー済みの外部 API への通信では、必要な CIDR/port を選択する追加の egress policy を使えます。ここに示す documentation 用の prefix は実際の宛先ではありません。

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-reviewed-external-api
  namespace: app-namespace
spec:
  podSelector:
    matchLabels: {app: web}
  policyTypes: [Egress]
  egress:
  - to:
    - ipBlock:
        cidr: 203.0.113.0/24
    ports:
    - {protocol: TCP, port: 443}
```

標準の NetworkPolicy は FQDN 許可リストを提供しません。NAT/endpoint の選択によって評価対象の IP が変わる場合があります。RFC1918 範囲だけを除外した包括的な `0.0.0.0/0` は、特定の外部サービス向けルールではなく、link-local metadata endpoint に対する完全な保護でもありません。

テスト後は、記録した namespace だけを削除してください。

```bash
for ns in "${NP_NAMESPACE_A:?}" "${NP_NAMESPACE_B:?}"; do
  expected_uid=$(jq -er '.metadata.uid' "${NP_LAB_DIR:?}/$ns-created.json") || exit 1
  current_uid=$(kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" get namespace "$ns" \
    --ignore-not-found -o jsonpath='{.metadata.uid}') || exit 1
  if [ -z "$current_uid" ]; then
    continue
  elif [ "$current_uid" = "$expected_uid" ]; then
    kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" delete namespace "$ns" --wait=true || exit 1
  else
    printf '%s\n' 'Namespace UID changed; no deletion attempted for this namespace.' >&2
    exit 1
  fi
done
```

</details>

## 応用問題

10. VPC CNI のアドレス枯渇に対する対策を比較し、ノード密度と総アドレス空間の違いを説明してください。

<details>
<summary>回答を表示</summary>

最初に枯渇したリソースを特定してください。サブネットアドレス、連続する prefix block、ノードごとの ENI slot、branch ENI、kubelet の maxPods、コンピュート容量では、必要な対策が異なります。「プレフィックス委任が常に最も簡単」という従来の結論は広く言いすぎです。

| 方法 | 効果がある対象 | 重要な制約 |
| --- | --- | --- |
| プレフィックス委任 | 通常の ENI slot あたりの Pod アドレス数、割り当て効率 | 連続した `/28` が必要。IPv4 空間や branch ENI 容量は増えない |
| warm/minimum pool の調整 | 事前に割り当てる未使用アドレス | 割り当て準備と API call を、アドレス消費とトレードオフする |
| カスタムネットワーキング | ノードと Pod のサブネット需要を分離する | 同一 VPC/AZ の要件、ルート/セキュリティグループ、新規ノードへの計画的な移行が必要 |
| VPC CIDR/サブネットの追加 | 割り当て可能なアドレス空間 | 重複、quota、ルーティング、control plane との整合性を確認する |
| 新規のより大きなサブネット範囲 | 計画的なアドレス拡張 | 既存サブネットの単純なサイズ変更はできない。範囲は関連付け済み VPC CIDR に含まれる必要がある |
| IPv6 クラスター設計 | 共有 IPv4 Pod アドレスへの圧力の大部分 | 新規クラスター/IP family の計画、サポート対象コンピュート/CNI、egress 要件が必要 |
| 別の CNI | 異なる IPAM/ルーティングモデル | サポート対象でテスト済みの移行が必要。マニフェストの切り替えだけでは済まない |
| Fargate | ノード/IP 割り当て運用を委譲する | 各 Pod は引き続き VPC/サブネットアドレスを消費する。枯渇したサブネットは解消しない |

**プレフィックスモード:** 通常の IPv4 prefix は `/28` block で、各 block が 1 つのアドレス slot を消費します。従来示されていた「最大 5 倍」という値は、検証されていない一般的な主張であり、ベンチマークではありません。実際のインスタンス/CNI/kubelet 上限を使用してください。Pod 用セキュリティグループは併用できますが、branch Pod には別の上限があります。fragmentation を調べ、必要に応じて prefix 用の空き領域や新しいサブネットを確保してください。未使用の個別 IP 数だけを見て、連続 block があるとは判断しないでください。

**warm pool:** `WARM_IP_TARGET` は空きアドレス数の余力、`MINIMUM_IP_TARGET` は最低割り当て数です。設定によって、prefix/ENI の warm-target 動作を上書きすることがあります。例の 5/10 はワークロードと API call の予算に合わせて調整してください。

```json
{"env":{"WARM_IP_TARGET":"5","MINIMUM_IP_TARGET":"10"}}
```

`MAX_ENI` は、ノード割り当てを EC2 インスタンスタイプの上限まで制限します。5 に設定しても、より少ない ENI しかサポートしないタイプで 5 ENI が使えるようにはなりません。上限を変更する前に、実際の割り当てメトリクスを確認してください。

**カスタムネットワーキング:** 同じ VPC/AZ 内の Pod subnet とセキュリティグループを準備した後、既存の CNI 管理者を通じて設定を統合してください。安定した zone label は非推奨の beta label ではなく `topology.kubernetes.io/zone` です。

```json
{
  "env": {
    "AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG": "true",
    "ENI_CONFIG_LABEL_DEF": "topology.kubernetes.io/zone"
  }
}
```

```yaml
apiVersion: crd.k8s.amazonaws.com/v1alpha1
kind: ENIConfig
metadata:
  name: us-west-2a
spec:
  subnet: subnet-REPLACE_WITH_POD_SUBNET_IN_SAME_VPC_AND_AZ
  securityGroups:
  - sg-REPLACE_WITH_APPROVED_POD_GROUP
```

使用する各 AZ に対応する ENIConfig を作成してください。ノード annotation による上書きも確認します。正しい zone label を持つ置き換えノードでは既存の ENIConfig を再利用できます。ノードを入れ替えるたびに再作成する必要はありません。既存の Pod のネットワーキングが一斉に直ちに変更されるわけではありません。新しいノードを検証し、容量、PDB、データを確認しながら移行してください。

**CIDR/サブネットの変更:** IaC の所有者を通じて、重複しない適格な CIDR と関連サブネットを追加し、ルート、セキュリティ、endpoint、discovery tag を確認します。新たに関連付けた VPC CIDR が control plane の操作から認識されるまで、EKS では最大 1 時間かかる場合があります。/16 のサブネットを作成するには、関連付け済みの /16 範囲も必要です。「大きくする」ことは VPC の制限を回避する方法ではありません。

**別の CNI/IPv6:** control plane、DNS、Service/ロードバランサー、ポリシー、bootstrap、rollback の経路をすべて計画してください。稼働中のクラスターで一般的な切り替え手順として、固定されていない Calico overlay manifest を適用して `aws-node` を無効化しないでください。既存 EKS クラスターの IP family を IPv6 に単純に切り替えることはできません。サポートと AWS 連携は、具体的なコンピュート/CNI モードに依存します。

**Fargate:** namespace label を付けても profile は作成されません。また、`eks.amazonaws.com/v1alpha1 kind: FargateProfile` は組み込み Kubernetes API ではありません。EKS API、eksctl、または明示的にインストールしたサポート対象 controller を使ってください。この API の例には、未使用の profile 名、レビュー済み private subnet、execution role が必要です。

```bash
# New profile example; this does not create or enlarge subnet address space.
aws eks create-fargate-profile --cluster-name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --fargate-profile-name "${NEW_FARGATE_PROFILE:?}" \
  --pod-execution-role-arn "${FARGATE_EXECUTION_ROLE_ARN:?}" \
  --subnets "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" \
  --selectors '[{"namespace":"ipam-fargate"}]'
```

対応する namespace/workload も別途作成し、profile の有効化を確認してください。Fargate は運用上の責任を移しますが、選択したサブネットの有限なアドレス容量は変えません。すべての戦略を同時に適用せず、測定した需要に対して対策を比較してください。この監査ではネットワーク移行や性能ベンチマークを実施していません。

</details>

## VPC の基本確認問題

11. パブリック `10.0.0.0/24` と `10.0.1.0/24` を避け、境界に整列している private subnet の組み合わせはどれですか？
   * A) `10.0.2.0/22` と `10.0.6.0/22`
   * B) `10.0.4.0/22` と `10.0.8.0/22`
   * C) `10.0.0.0/22` と `10.0.1.0/22`
   * D) 異なる文字列ならどの 2 つでもよい

<details>
<summary>回答を表示</summary>

**正解: B) `10.0.4.0/22` と `10.0.8.0/22`**

`/22` は第 3 オクテットが 4 刻みの境界から始まります。`10.0.2.0/22` を正規化すると `10.0.0.0/22` となり、パブリック範囲と重複します。

</details>

12. AWS の通常の IPv4 `/24` サブネットで、リソースに割り当てる前に利用できるアドレスはいくつですか？
   * A) 256
   * B) 254
   * C) 251
   * D) 常に 240

<details>
<summary>回答を表示</summary>

**正解: C) 251**

AWS は通常のサブネットで先頭 4 個と末尾 1 個のアドレスを予約します。合計 256 個のうち、割り当て可能な数は 251 個です。BYOIP には文書化された例外があります。

</details>

13. `elb` サブネットの role tag を付けると Internet Gateway route が作成されますか？
   * A) はい
   * B) いいえ。route 設定と controller の discovery は別です
   * C) private subnet の場合だけ
   * D) すべてのセキュリティグループも開放される

<details>
<summary>回答を表示</summary>

**正解: B) いいえ。route 設定と controller の discovery は別です**

tag は、controller、バージョン、feature gate によってはリソースの discovery に影響します。しかし、route を作成するものでも、セキュリティ境界でもありません。

</details>

14. すべての EKS ノードに public internet 経路が必須ですか？
   * A) はい。必ず NAT gateway 経由
   * B) はい。必ず IGW 経由
   * C) いいえ。必要な service には適切な private endpoint/mirror で接続できる
   * D) ネットワークアクセスは不要

<details>
<summary>回答を表示</summary>

**正解: C) いいえ。必要な service には適切な private endpoint/mirror で接続できます**

実際の API、registry、DNS、ワークロード依存関係を計画してください。AWS EKS service endpoint は Kubernetes クラスター API endpoint とは別です。

</details>

15. control plane と通信する kubelet の通常の宛先 port はどれですか？
   * A) TCP 1025–65535 の全て
   * B) TCP 10250
   * C) デフォルトですべての NodePort
   * D) UDP 53 だけ

<details>
<summary>回答を表示</summary>

**正解: B) TCP 10250**

private API の TCP 443、DNS の TCP/UDP 53、実際の webhook/workload port、実際のセキュリティグループ関連付けは別々に確認してください。stateful なセキュリティグループの戻り通信は、stateless な NACL rule とは異なります。

</details>

## 参考資料

- [VPC/サブネットの要件](https://docs.aws.amazon.com/eks/latest/userguide/network-reqs.html)
- [VPC CNI 1.23.0](https://github.com/aws/amazon-vpc-cni-k8s/blob/v1.23.0/README.md)
- [NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [EKS ネイティブポリシー](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html)
- [LBC 3.5 Service annotation](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/docs/guide/service/annotations.md)
- [LBC のサブネット検出](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/docs/deploy/subnet_discovery.md)
- [NLB listener](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/load-balancer-listeners.html)
- [NLB log](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/load-balancer-access-logs.html)
- [CoreDNS cache plugin](https://coredns.io/plugins/cache/)
- [CoreDNS cache の実装](https://github.com/coredns/coredns/blob/v1.14.7/plugin/pkg/cache/cache.go)
