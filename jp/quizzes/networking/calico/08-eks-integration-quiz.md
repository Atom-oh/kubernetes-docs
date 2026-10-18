# EKS統合クイズ

> **関連ドキュメント**: [EKS統合](../../../networking/calico/08-eks-integration.md)
> **最終更新**: 2026年9月12日

## クイズ

1. このガイドの一般的な EC2 Linux VPC CNI + Calico 構成では、各コンポーネントはどのように役割を分担しますか？
   - A) VPC CNIがpolicyを適用し、CalicoがVPC IPを割り当てる
   - B) VPC CNIがPod networkingを担い、Calicoがpolicyを適用する
   - C) 両方のCNIが各Podの全インターフェイスを個別に構成する
   - D) CalicoがAWS管理のEKS control planeを置き換える

<details>
<summary>解答を表示</summary>

**正解: B) VPC CNIがPod networkingを担い、Calicoがpolicyを適用する**

**解説:**
VPC CNIはENI、Pod IPの割り当て、接続性を管理し、Calicoはpolicyルールを設定します。このガイドではIptablesとkube-proxyを使用します。別のdataplaneを選ぶ場合は、個別に計画してください。

</details>

2. EKSにCalicoをインストールする方法について、正しい説明はどれですか？
   - A) VPC CNIのnetwork policyを有効にするとCalicoもインストールされる
   - B) バージョンを固定したTigera Operatorは、manifestまたはHelm chartでインストールできる
   - C) すべてのEKS clusterに、AWSがサポートする「calico」という名前のadd-onがある
   - D) Helm rollbackを実行すれば、CalicoのCRDとデータの移行も必ず元に戻る

<details>
<summary>解答を表示</summary>

**正解: B) バージョンを固定したTigera Operatorは、manifestまたはHelm chartでインストールできる**

**解説:**
Helm chartはTigera Operatorをインストールします。AWS VPC CNIのpolicyは別の実装です。Marketplaceやcommunityの製品については、実際のcatalogとサポート担当を確認し、インストールの管理主体を一つにしてください。

</details>

3. AWSの現在のnative network policyに関する案内と一致する説明はどれですか？
   - A) 現在利用できるすべてのpolicy機能はEKS 1.14で導入された
   - B) VPC CNI 1.21以降は、文書化されたplatformとkernelの前提条件を満たすとstandard policyとadmin policyをサポートする
   - C) native policyがサポートするのはnamespace単位のpolicyだけである
   - D) native policyとCalicoは、同じendpointに必ず両方適用しなければならない

<details>
<summary>解答を表示</summary>

**正解: B) VPC CNI 1.21以降は、文書化されたplatformとkernelの前提条件を満たすとstandard policyとadmin policyをサポートする**

**解説:**
standard policyのサポートはEKS 1.14ではなくVPC CNI 1.14で始まりました。AWSの現在の案内では、VPC CNI 1.21以降を使い、対応するEKS/platformのバージョンとLinux kernel 5.10以降を満たす環境で、NetworkPolicyとAWS ClusterNetworkPolicyを利用できます。これらのAPIはCalicoのAPIとは異なります。

</details>

4. EKS Fargate上のnetwork policyには、どのような制限がありますか？
   - A) Fargateにはnetworking機能がない
   - B) Calico node-agentのpolicyもVPC CNI native network policyも、Fargate Pod内では適用されない
   - C) kubernetesProviderをEKSにすれば、Calicoのすべての機能が利用できる
   - D) FargateがサポートするのはIPv6だけである

<details>
<summary>解答を表示</summary>

**正解: B) Calico node-agentのpolicyもVPC CNI native network policyも、Fargate Pod内では適用されない**

**解説:**
Fargateではこれらのnode agentを実行しません。Pod用Security Groupは別の制御機能です。Fargate peerを含む通信でも、CalicoでEC2側のendpointを制限できる場合はありますが、それはFargate内でのpolicy適用ではありません。

</details>

5. この構成でAWS IAM権限を割り当てる方法として適切なのはどれですか？
   - A) すべてのcalico-nodeに、広範なEC2 DescribeとCloudWatchの権限を与える
   - B) 実際にAWS APIを呼び出すcomponentに権限を割り当てる。基本的なCalico policyにはKubernetes RBACを使う
   - C) InstallationのnodeMetadataフィールドを設定するとIRSA roleが作成される
   - D) IAM policyを作成すると、すべてのServiceAccountに自動的に関連付けられる

<details>
<summary>解答を表示</summary>

**正解: B) 実際にAWS APIを呼び出すcomponentに権限を割り当てる。基本的なCalico policyにはKubernetes RBACを使う**

**解説:**
VPC CNIには専用のAWS権限が必要です。exporterやcloud integrationにも別のroleが必要になる場合があります。権限は、そのcomponentがサポートするIRSAまたはPod Identityの設定で割り当てます。policyの適用だけを行う基本的なCalico構成には、広範なAWS roleは必要ありません。

</details>

6. Pod用Security GroupとCalico policyを併用するためにAWSが求める条件はどれですか？
   - A) POD_SECURITY_GROUP_ENFORCING_MODE=strictだけを設定する
   - B) VPC CNI 1.11以降とPOD_SECURITY_GROUP_ENFORCING_MODE=standardを使い、そのほかの機能要件も満たす
   - C) EC2 instanceにlabelを付ければよい
   - D) EKS Auto ModeでもPod用Security Groupを利用できる

<details>
<summary>解答を表示</summary>

**正解: B) VPC CNI 1.11以降とPOD_SECURITY_GROUP_ENFORCING_MODE=standardを使い、そのほかの機能要件も満たす**

**解説:**
strict modeでは、対象PodにCalico policyが適用されません。対応するinstanceとbranch ENIを確認し、modeを変更した後は対象Podを置き換えてください。通常のexternal SNATを使うstandard modeでは、VPC外へ出る通信にnodeのSecurity Groupが使われます。

</details>

7. EKSとCalicoをupgradeする際の適切な進め方はどれですか？
   - A) 互換性にかかわらず、必ずEKSのupgrade後にCalicoをupgradeする
   - B) 移行前後で互換性のあるCalico versionを選び、EKS、node、add-on、CRDの要件を確認する
   - C) EKSがすべてのthird-party componentを自動的にupgradeし、rollbackする
   - D) 古いoperatorを適用すれば、安全なdowngradeが保証される

<details>
<summary>解答を表示</summary>

**正解: B) 移行前後で互換性のあるCalico versionを選び、EKS、node、add-on、CRDの要件を確認する**

**解説:**
移行の前後両方で互換性を確認してください。現在のEKSには、条件を満たせば直前のminor versionへ戻せる7日間のrollback期間がありますが、CalicoやEKS add-onは自動的にはrollbackされません。復旧時にも互換性とreadinessの確認が必要です。

</details>

8. 対象のInstallationで設定されているprovider値はどれですか？
   - A) AWS
   - B) EKS
   - C) AmazonEKS
   - D) なし

<details>
<summary>解答を表示</summary>

**正解: B) EKS**

**解説:**
`spec.kubernetesProvider: EKS`を使います。Helm valuesでは`installation.kubernetesProvider: EKS`と指定します。この設定はprovider向けの構成を選択するものであり、すべてのnode type、CNI、dataplane、versionがサポートされることを示すものではありません。

</details>

9. Amazon VPC CNIにnetworkingを委ねるCNI typeはどれですか？
   - A) Calico
   - B) AmazonVPC
   - C) AWSCNI
   - D) VPC

<details>
<summary>解答を表示</summary>

**正解: B) AmazonVPC**

**解説:**
Installationで`spec.cni.type: AmazonVPC`を設定します。Calicoをpolicy-onlyで動作させるには、文書化されたPod IP annotationとRBACも必要で、policy engineは一つにしてください。`bgp: Disabled`を設定しただけでは、このCNIは選択されません。

</details>

10. backend selectorとTCP portを一つのdestination mappingにまとめる必要があるのはなぜですか？
    - A) YAMLではすべてのfieldを重複して記述する必要がある
    - B) destination keyを重複させるとselectorが失われ、意図しないendpointへの通信を許すおそれがある
    - C) portを指定すればbackend Podのlabelも自動的に設定される
    - D) keyが重複したYAMLは必ずKubernetesのvalidation errorになる

<details>
<summary>解答を表示</summary>

**正解: B) destination keyを重複させるとselectorが失われ、意図しないendpointへの通信を許すおそれがある**

**解説:**
YAML parserによっては、重複したkeyのうち最後の値だけが残ります。selectorとportを同じ項目にまとめ、validation時に重複keyを拒否し、許可・拒否される両方の通信をテストしてください。nodeがReadyであることは、policyが正しく適用されている証拠にはなりません。

</details>
