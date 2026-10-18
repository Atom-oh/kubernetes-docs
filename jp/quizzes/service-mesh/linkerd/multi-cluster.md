# Linkerdマルチクラスタークイズ

[マルチクラスターガイド](../../../service-mesh/linkerd/06-multi-cluster.md)に基づき、2026年9月11日に確認。

### 1. Linkerdマルチクラスターの中核となる仕組みは何ですか？

- A. Kubernetes clusterの統合
- B. Service mirroring
- C. すべてのアプリケーションwriteの自動複製
- D. 必須のglobal load balancer

<details>
<summary>解答を表示</summary>

**解答: B**

**解説:** source controllerはtarget Kubernetes APIを通じて選択されたService情報を監視し、ローカルにdiscovery resourceを作成します。これはrequest shadowingでもdata replicationでもありません。hierarchical、flat、federated各modeではネットワーク要件が異なります。

</details>

### 2. mesh mTLSのためにcluster間で信頼する必要があるものは何ですか？

- A. 同一のissuer private key
- B. 該当するpublic trust-anchor bundleとissuer chain
- C. 共有のworkload private key
- D. すべての場所で同一のKubernetes Secret object

<details>
<summary>解答を表示</summary>

**解答: B**

**解説:** 共通rootが最も単純な構成です。適切な共有bundleに複数のrootを含めることもできます。clusterごとに異なるkeyを持つissuerを使えます。既存proxyには、調整したtrust-bundle切り替えが必要です。また、public rootと署名用keyを区別してください。

</details>

### 3. hierarchical gateway-mode mirroringで使われるexport labelのdefaultはどれですか？

- A. `linkerd.io/exported: "true"`
- B. `mirror.linkerd.io/exported: "true"`
- C. `multicluster.linkerd.io/export: "enabled"`
- D. `linkerd.io/multicluster: "export"`

<details>
<summary>解答を表示</summary>

**解答: B**

**解説:** hierarchical modeのdefault selectorは`mirror.linkerd.io/exported=true`に一致します。flat modeでは`remote-discovery`、federated membershipでは`mirror.linkerd.io/federated=member`を使います。labelは、該当するLink/RBACにおけるdiscovery対象を決めますが、access-control boundaryではありません。

</details>

### 4. mirroringされたServiceの一般的な名前はどれですか？

- A. `<service>.<cluster>`
- B. `<service>-<Link cluster name>`
- C. `<cluster>-<service>`
- D. `<service>@<cluster>`

<details>
<summary>解答を表示</summary>

**解答: B**

**解説:** `west`という名前のLinkから取り込まれる`web` Serviceは、通常、対応するnamespace内で`web-west`になります。Link cluster nameはaliasであり、EKSの物理cluster名と一致する必要はありません。namespaceの作成はdefaultでは有効になっていません。

</details>

### 5. 現行の`link-gen` commandが生成するものは何ですか？

- A. VPC routeとgateway load balancer
- B. source cluster向けのLinkと2つのcredential Secret
- C. 複製されたアプリケーションdatabase
- D. すべてのPod用の新しいworkload certificate

<details>
<summary>解答を表示</summary>

**解答: B**

**解説:** contextを`west`にして生成し、`east`に適用すると、EastからWestをdiscoveryできます。chartの`controllers`一覧にはsource mirror controllerを指定します。旧`link` commandはdeprecatedです。生成されたkubeconfig dataは機密情報です。接続可能なAPI endpointと利用可能なCA dataを含めてください。

</details>

### 6. target gatewayのprobe統計を表示するcommandはどれですか？

- A. `linkerd multicluster status`
- B. `linkerd multicluster gateways`
- C. `kubectl get gateway`
- D. `linkerd gateway inspect`

<details>
<summary>解答を表示</summary>

**解答: B**

**解説:** `gateways`が表示するのは設定済みtarget gatewayのprobeであり、個々のアプリケーションのhealthではありません。probeはsource mirror controllerが実行します。flat-only Linkにはgatewayが不要なので、Link/endpoint/Podの接続診断を使ってください。

</details>

### 7. ガイドのAWS Load Balancer Controller例では、どのload balancer設定を使いますか？

- A. mesh TLSを終端するpublic ALB
- B. Region間で自動到達可能な任意のClusterIP
- C. `service.k8s.aws/nlb`で選択するinternal TCP NLB
- D. legacyのnlb annotationを使えば、IP targetの所有者も自動的に確定する

<details>
<summary>解答を表示</summary>

**解答: C**

**解説:** この例は、該当controller、サポート対象のannotation、準備済みのprivate connectivityを前提とします。EKS Auto Modeではclass/ownerが異なります。gateway data、probe、remote Kubernetes APIへの各経路の到達性は、別々に確認してください。

</details>

### 8. 現行のHTTPRoute例では、local/remoteの振り分けにどのbackendを使えますか？

- A. local Serviceと、別API serverにある任意のremote Pod IP
- B. local backend Serviceと、ローカルにimportされたmirror Service
- C. local Serviceのみ
- D. 自動database replica set

<details>
<summary>解答を表示</summary>

**解答: B**

**解説:** この例では`web-local`と`web-west`をapex Service経由で使います。相対weightは自動standby policyではありません。`100/0`に設定しても、障害時にweight 0のbackendへ自動で切り替わるとは限りません。SMI/Failover extensionはdeprecatedであり、flat federationには別の要件と動作があります。

</details>

### 9. mirror controllerの役割ではないものはどれですか？

- A. 選択されたremote Serviceを監視する
- B. ローカルmirrorを作成・更新する
- C. workload certificateを発行する
- D. modeに応じたdiscovery/endpoint情報を維持する

<details>
<summary>解答を表示</summary>

**解答: C**

**解説:** Identityがworkload certificateを発行します。選択されたmirror controllerは、hierarchical Service用のlegacy Endpointsを維持します。一方、`remote-discovery` modeでは、ローカルEndpointsを意図的に削除し、接続先側のremote discoveryを使う場合があります。

</details>

### 10. 適切に構成すれば、private VPC間のroute接続を提供できるものはどれですか？

- A. Route53のみ
- B. VPC peeringまたは適切なTransit Gateway routing
- C. CloudFrontのみ
- D. EKS management interface endpointだけでflat Pod routingを自動提供する

<details>
<summary>解答を表示</summary>

**解答: B**

**解説:** route、重複しない到達可能なaddress、DNS、security controlも必要です。PrivateLinkは選択したservice/resourceへのアクセスを提供するもので、VPC peeringと同じではありません。EKS interface endpointはclusterのKubernetes API endpointではありません。

</details>

### 11. 最終serverで、維持されたremote workload identityを認可するにはどうしますか？

- A. AWS account名をmesh identityとして暗黙に信頼する
- B. flat/federated modeで、実際のDNS形式identityを使ったLinkerd authorizationを適用する
- C. 非推奨のSPIFFE URI例を、どのgateway経由でも使う
- D. public export labelがcallerを認証するとみなす

<details>
<summary>解答を表示</summary>

**解答: B**

**解説:** hierarchical gatewayを使うと、最終serverでは元のcaller identityが失われます。flat/federated経路ではidentityが維持されます。同じServiceAccount/namespace/trust-domain名が複数clusterに存在する場合があるため、このpolicyだけでEast由来だと証明できるわけではありません。

</details>

### 12. マルチクラスターのinfrastructure checkで確認できないものは何ですか？

- A. Link設定で検出可能なerrorがあるか
- B. 設定済みremote access/probeで検出可能なfailureがあるか
- C. アプリケーションのbusiness correctnessや、保証されたregional recovery
- D. mirror componentに検出可能な設定問題があるか

<details>
<summary>解答を表示</summary>

**解答: C**

**解説:** checkは設定、credential、infrastructureの診断に役立ちます。data consistency、安全なwrite retry、capacity、failover後のbusiness動作までは確認しません。実際のworkloadの結果を別途検証してください。

</details>
