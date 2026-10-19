# EKS クラスター作成クイズ - Part 2

> **最終更新日**: 2026年9月11日

> 問題例はそれぞれ独立した選択肢です。Part 1 の前提条件を確認し、明示的に選択したトレーニング用アカウント／クラスターを使ってください。各演習の手順は、同じ Bash セッション内で順に実行します。以下のクラウド／ホストコマンドは内容をレビューしたものですが、この監査中に AWS やノード上で実行していません。

このクイズでは、Amazon EKS クラスターの作成に関する高度な概念、セキュリティ設定、ネットワーク構成を確認します。クラスターセキュリティ、ネットワークポリシー、サービスアカウントなどを扱います。

## 基本概念の問題

1. EKS クラスターで IRSA を使う主な目的は何ですか？
   * A) Kubernetes 管理者アクセスを付与する
   * B) EC2 ノードの IAM ロールを割り当てる
   * C) Kubernetes サービスアカウントを通じてワークロードに一時的な AWS 権限を与える
   * D) EKS コントロールプレーンのロールを変更する

<details>
<summary>答えを表示</summary>

**答え: C) Kubernetes サービスアカウントを通じてワークロードに一時的な AWS 権限を与える**

IRSA では、ワークロードが Kubernetes サービスアカウントの ID を使って一時的な AWS 認証情報を取得します。IAM ロールの権限ポリシーが、実行できる AWS 操作を決めます。これは Kubernetes RBAC や EKS コントロールプレーン／EC2 ノードの IAM ロールとは別の仕組みです。

**信頼の流れ:** EKS が投影されたサービスアカウントトークンを発行します。クラスターの実際の OIDC issuer を IAM OIDC プロバイダーとして登録し、意図した audience と namespace／service-account subject を信頼するよう設定します。対応する AWS SDK のデフォルト認証情報チェーンがトークンを STS の `AssumeRoleWithWebIdentity` に渡します。次の例では、実際のプロバイダー ARN／issuer と正確なサービスアカウント ID を使ってください。

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "Federated": "arn:aws:iam::123456789012:oidc-provider/oidc.eks.us-west-2.amazonaws.com/id/EXAMPLE"
    },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "oidc.eks.us-west-2.amazonaws.com/id/EXAMPLE:aud": "sts.amazonaws.com",
        "oidc.eks.us-west-2.amazonaws.com/id/EXAMPLE:sub": "system:serviceaccount:irsa-lab:my-service-account"
      }
    }
  }]
}
```

サービスアカウントにロール ARN を annotation し、Pod からそのアカウントを参照します。先に未使用の `irsa-lab` namespace を作成してください。次の2つの manifest は、以下の eksctl によるサービスアカウント作成の代替です。別アプリケーションのサービスアカウントを上書きしないでください。

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-service-account
  namespace: irsa-lab
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/ReviewedIrsaRole
```

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: irsa-identity-check
  namespace: irsa-lab
spec:
  serviceAccountName: my-service-account
  restartPolicy: Never
  containers:
    - name: aws-cli
      image: public.ecr.aws/aws-cli/aws-cli:2.36.43
      command: ["aws"]
      args: ["sts", "get-caller-identity"]
```

Pod は検証済みの AWS CLI v2 イメージタグを使い、秘密鍵や web-identity token ではなく呼び出し元の identity を表示します。返されたロールが意図したワークロードロールであることを確認します。STS identity の成功だけでは S3 などの対象リソースへのアクセスを証明できません。演習1のように必要な操作を別途テストしてください。

**eksctl を使う場合:** 1つのバケットだけを扱う作業に広範な AWS 管理 S3 ポリシーを使わず、対象リソースと操作に限定したポリシーを使います。既存のサービスアカウントとロールの所有者を先に確認してください。`--override-existing-serviceaccounts` を一般的な修正策として追加しないでください。

```bash
# For a new service account and dedicated role, with a reviewed scoped policy.
eksctl utils associate-iam-oidc-provider \
  --cluster "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" --approve
KUBECONFIG="${EXAMPLE_KUBECONFIG:?}" eksctl create iamserviceaccount \
  --name "${IRSA_SERVICE_ACCOUNT:?}" --namespace "${IRSA_NAMESPACE:?}" \
  --cluster "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --attach-policy-arn "${SCOPED_POLICY_ARN:?}" --approve
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n "$IRSA_NAMESPACE" \
  get serviceaccount "$IRSA_SERVICE_ACCOUNT" -o yaml
```

**制限と責任:**

- 対応 SDK とその認証情報チェーンを使います。ハードコードした認証情報やチェーン内の先行プロバイダーが IRSA より優先される場合があります。Webhook はロール／token-file 設定を注入し、SDK が一時認証情報を更新します。token や認証情報の値を表示・コピーしないでください。
- IRSA 自体はノード IMDS へのアクセスを遮断せず、同じノード上のコンテナ間に強いセキュリティ境界を作るものでもありません。IMDS とノード権限は別途制限してください。`hostNetwork` Pod は引き続き IMDS に到達できます。
- IAM 条件でロール引き受けを限定しても、そのサービスアカウントを使う Pod を作成できる人は AWS 権限を取得できる可能性があります。Kubernetes のワークロード／サービスアカウント管理も統制してください。
- EKS Pod Identity もワークロード ID の選択肢ですが、独自のサポート要件があります。EKS Auth／agent を使う認証情報フローは、IRSA の OIDC／STS フローとは異なります。
- クラスター利用者のアクセスは、設定に応じて EKS access entry／policy または従来の `aws-auth` mapping で認可します。これらは Kubernetes アクセスを許可するもので、ワークロード IAM 権限ポリシーの代わりにはなりません。

参考資料: [IRSA](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)、[サービスアカウントへのロール割り当て](https://docs.aws.amazon.com/eks/latest/userguide/associate-service-account-role.html)、[SDK の要件](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts-minimum-sdk.html)、[Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html)。

</details>

2. EKS 設計において AWS セキュリティグループが制御するものは何ですか？
   * A) Kubernetes リソースの認可
   * B) 関連付けられたネットワークインターフェイス上の許可トラフィック。対応する Pod インターフェイスも含む
   * C) サービスアカウント token の audience
   * D) Deployment のレプリカ数

<details>
<summary>答えを表示</summary>

**答え: B) 関連付けられたネットワークインターフェイス上の許可トラフィック。対応する Pod インターフェイスも含む**

セキュリティグループはネットワークインターフェイスに関連付けるステートフルなネットワークフィルターです。EKS では、クラスターのインターフェイス、ノード間のトラフィック、および対応する Security Groups for Pods 機能を使う一部の Pod の通信を制御します。Kubernetes RBAC を実装したり、利用者を認証したりする機能ではありません。

**既定ルールと必須ルールは別です。** EKS は自己参照の inbound ルール、広い outbound アクセス、EFA 用の自己参照 outbound ルールを含む `eks-cluster-sg-<cluster>-<id>` を作成します。これらは確認対象の既定値であり、最小権限の設計例ではありません。EKS はクラスター用インターフェイスと通常は managed node のインターフェイスにクラスター SG を関連付けますが、カスタム launch template の SG はこの動作を変えます。

既定の outbound ルールを制限する場合は、以下の文書化された最小トラフィックに加え、実際のワークロードの依存関係も残してください。

| クラスター SG に必要な outbound 通信 | 宛先 |
| --- | --- |
| TCP 443 | クラスターセキュリティグループ |
| TCP 10250 | クラスターセキュリティグループ |
| TCP および UDP 53 | クラスターセキュリティグループ |

この表だけではネットワーク設計として不十分です。ノード間／アプリケーションのポート、API と registry へのアクセス、S3、DNS 経路、IPv4／IPv6 ルールを確認してください。private endpoint を使えば、一般的なインターネットへの outbound なしで AWS に接続できます。クラスター更新時に EKS が自己参照ルールを再作成することがあるため、削除すれば恒久的に制限されるとは考えないでください。

**追加 SG:** クラスターの `resourcesVpcConfig.securityGroupIds` で指定するグループはクラスターのネットワークインターフェイスに付き、node group には自動で付きません。ノード launch template がカスタム SG を指定すると EKS はクラスター SG も追加しないため、カスタム SG 側で必要なノード／API 通信を許可します。

以下の AWS CLI 例は新しいコントロールプレーンに追加 SG を選択します。ノード容量や運用者 access entry は作成しません。自動の作成者 admin access は無効なので、provisioning identity には必要な運用者 access entry を作成する権限が必要です。

```bash
# Cluster creation fragment: use reviewed roles/subnets/groups and a new name.
aws eks create-cluster --name "${NEW_CLUSTER_NAME:?}" \
  --region "${EXAMPLE_REGION:?}" --kubernetes-version 1.36 \
  --role-arn "${CLUSTER_ROLE_ARN:?}" \
  --access-config authenticationMode=API,bootstrapClusterCreatorAdminPermissions=false \
  --resources-vpc-config "subnetIds=${PRIVATE_SUBNET_A:?},${PRIVATE_SUBNET_B:?},securityGroupIds=${ADDITIONAL_CONTROL_PLANE_SG:?},endpointPrivateAccess=true,endpointPublicAccess=true,publicAccessCidrs=${APPROVED_API_CIDR:?}"
```

同等の eksctl networking 項目は [Part 2](../../eks/02-eks-cluster-creation-part2.md) のレビュー済み完全設定に含まれています。文書用 CIDR と ID はすべて置き換えてください。

```yaml
# Networking example; merge into a reviewed full ClusterConfig.
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
  version: "1.36"
vpc:
  id: vpc-0123456789abcdef0
  controlPlaneSecurityGroupIDs:
    - sg-0123456789abcdef0
  clusterEndpoints:
    publicAccess: true
    privateAccess: true
  publicAccessCIDRs:
    - 203.0.113.10/32
  subnets:
    private:
      us-west-2a:
        id: subnet-0123456789abcdef0
      us-west-2b:
        id: subnet-0123456789abcdef1
```

**public／private API:** public Kubernetes endpoint はセキュリティグループではなく `publicAccessCidrs` で制限します。クラスター SG ルールが制御するのは private endpoint の通信です。CIDR allowlist も SG ルールも、IAM／RBAC の認可を付与しません。

**Pod のセキュリティグループ:** 対応する compute でこの機能を使う場合、`SecurityGroupPolicy` を作成する前に機能と必要な IAM／VPC CNI 設定を行います。instance trunking の互換性、CNI バージョン、enforcement mode、DNS、実際の SG ルールを確認してください。Windows と EKS Auto Mode は未対応です。EC2 `t` instance family も非対応です。Fargate には別の対応手順があります。

```yaml
apiVersion: vpcresources.k8s.aws/v1beta1
kind: SecurityGroupPolicy
metadata:
  name: application-sg
  namespace: sg-lab
spec:
  podSelector:
    matchLabels:
      app: my-app
  securityGroups:
    groupIds:
      - sg-0123456789abcdef0
```

この policy は別途作成した `sg-lab` namespace の Pod を選択します。CRD object があるだけでは SG が付いた証拠になりません。標準／strict の Pod SG mode と SNAT によって VPC 外向き通信をどの SG がフィルターするかが変わります。利用構成に応じた mode ごとの動作を公式資料で確認してください。

Kubernetes NetworkPolicy は、設定済みのネットワークプラグインが適用する別の機能です。NetworkPolicy 対応クラスターだからといって Pod 通信が自動的に default-deny になるわけではありません。意図した policy 設定は問題3を参照してください。

```bash
aws eks describe-cluster --name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" \
  --query 'cluster.resourcesVpcConfig.{clusterSG:clusterSecurityGroupId,additionalSGs:securityGroupIds,publicAccess:endpointPublicAccess,privateAccess:endpointPrivateAccess,cidrs:publicAccessCidrs}'
aws ec2 describe-security-groups --region "$EXAMPLE_REGION" \
  --group-ids "${REVIEWED_SECURITY_GROUP_ID:?}"
```

参考資料: [クラスターセキュリティグループ](https://docs.aws.amazon.com/eks/latest/userguide/sec-group-reqs.html)、[API endpoint access](https://docs.aws.amazon.com/eks/latest/userguide/cluster-endpoint.html)、[Pod のセキュリティグループ](https://docs.aws.amazon.com/eks/latest/userguide/security-groups-for-pods.html)。

</details>

3. EKS で Kubernetes NetworkPolicy を適用するには何が必要ですか？
   * A) セキュリティグループのルールだけ
   * B) Amazon VPC CNI、Calico、Cilium など、対応し有効化された policy 実装
   * C) VPC Flow Logs だけ
   * D) 適用実装のない NetworkPolicy object

<details>
<summary>答えを表示</summary>

**答え: B) Amazon VPC CNI、Calico、Cilium など、対応し有効化された policy 実装**

設定済みの NetworkPolicy 実装が必要です。`NetworkPolicy` object を作るだけではトラフィックルールは適用されません。**Amazon VPC CNI は NetworkPolicy をサポート**するため、この機能だけを使う目的で Calico や Cilium が必須というわけではありません。

**Amazon VPC CNI を使う方法:** 対応するクラスター／platform、Linux kernel、CNI バージョンを確認し、add-on の管理元が提供する設定で network-policy 機能を有効にします。AWS の現行ガイダンスでは standard policy と admin policy の両方に VPC CNI 1.21.0 以降、Linux kernel 5.10 以降を使います。過去の最低バージョンを現行クラスターの upgrade 目標にしないでください。

```bash
aws eks describe-addon --cluster-name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --addon-name vpc-cni \
  --query 'addon.{version:addonVersion,status:status,configuration:configurationValues}'
aws eks describe-addon-configuration --region "$EXAMPLE_REGION" \
  --addon-name vpc-cni --addon-version "${REVIEWED_CNI_VERSION:?}" \
  --query configurationSchema --output text
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" -n kube-system \
  get daemonset aws-node -o jsonpath='{.spec.template.spec.containers[*].name}{"\n"}'
```

EKS managed add-on では、該当する設定値は次のとおりです。

```json
{
  "enableNetworkPolicy": "true"
}
```

これを**レビュー済みの完全な設定**に統合し、必要な既存設定を保ってください。新しい `configurationValues` 文書を渡す操作は JSON patch ではありません。add-on を downgrade したり、古い upstream manifest で EKS-managed DaemonSet を上書きしたりしないでください。Helm／自己管理 install では、その方式の文書化された設定を使用します。

standard startup mode では、新しい Pod に policy が設定されるまで一時的に通信を許可する場合があります。strict mode は default-deny で開始しますが、CoreDNS 依存関係も含め必要な全通信 policy を準備しておく必要があります。稼働中のクラスターで無計画に strict mode へ切り替えないでください。

**別の実装方法:**

- **Amazon VPC networking と Calico:** AWS IPAM／CNI を維持し、operator の `Installation` を `AmazonVPC` に設定します。固定した operator／CRD の手順、および公式 EKS ガイドにある AWS Pod-IP annotation／RBAC 前提を確認します。この Calico 構成では AWS 側の policy enforcement を無効にします。operator だけをインストールしたり、任意の VXLAN manifest を適用したりするのは同じ設計ではありません。

```yaml
# Installation resource for the Amazon VPC networking path, after operator/CRDs.
apiVersion: operator.tigera.io/v1
kind: Installation
metadata:
  name: default
spec:
  kubernetesProvider: EKS
  cni:
    type: AmazonVPC
  calicoNetwork:
    bgp: Disabled
```

- **Amazon VPC CNI と Cilium:** 文書化された chaining 設定が必要です。tunnel／masquerading を無効にするだけでは chaining になりません。次は公開済みの 1.20.1 guide の参考値です。release／クラスター互換性と guide の前提条件を確認してください。新しい chaining 経路を有効にするには、管理された rollout で既存 Pod を再作成する必要があります。

```yaml
# Relevant Helm values from the Cilium 1.20.1 AWS-CNI chaining guide.
# This is not a complete install or migration command.
cni:
  chainingMode: aws-cni
  exclusive: false
enableIPv4Masquerade: false
routingMode: native
```

未レビューの CNI／policy 実装を重ねず、使う enforcement 実装を選んで検証します。実装を置き換えるとノード上にルールが残る可能性があるため、計画した migration が必要です。

**policy の例:** 新規作成した `policy-lab` namespace で、frontend から backend への TCP 8080 と DNS を許可し、ほかの通信を拒否します。backend は実際に 8080 を listen する必要があります。AWS 実装では同じ Service port と container port を使ってください。DNS selector は `kube-system` の一般的な CoreDNS Pod を想定します。NodeLocal DNSCache や独自 DNS では、レビュー済みの別ルールが必要です。

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: policy-lab
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: backend-ingress
  namespace: policy-lab
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes: [Ingress]
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: frontend
      ports:
        - protocol: TCP
          port: 8080
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: frontend-egress
  namespace: policy-lab
spec:
  podSelector:
    matchLabels:
      app: frontend
  policyTypes: [Egress]
  egress:
    - to:
        - podSelector:
            matchLabels:
              app: backend
      ports:
        - protocol: TCP
          port: 8080
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: dns-egress
  namespace: policy-lab
spec:
  podSelector: {}
  policyTypes: [Egress]
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
```

両端がそれぞれ isolation されるため、frontend の egress と backend の ingress の両方を許可します。standard NetworkPolicy は許可された通信を追加し、default-deny object が allow rule を上書きするわけではありません。test namespace では DNS も許可し、アプリ通信拒否と DNS 障害を取り違えないようにします。

**意味のある検証:** frontend、backend、無関係な client を Deployment 管理下の Pod で用意します。AWS の説明では `metadata.ownerReferences` を持たない単独 Pod では enforcement が不安定なことがあるため、`kubectl run` の裸の Pod だけを証明に使わないでください。baseline 通信を確認して policy を適用し、frontend は成功、無関係な client は失敗し、DNS は引き続き動くことを確認します。policy が反映された後の新規接続を試します。CNI Pod の存在や YAML 適用成功だけでは十分ではありません。

AWS VPC CNI の policy enforcement は対応する EC2 Linux node を対象とし、Windows／Fargate は対象外です。Pod の primary interface とクラスターの IP family に適用され、追加 interface や IPv6 Pod からの IPv4 egress には制約があります。SG、Network Firewall、flow log は役割が異なり、この Kubernetes policy 設定の代替ではありません。

参考資料: [VPC CNI policy 設定](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy-configure.html)、[AWS policy の制約](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html)、[EKS の Calico](https://docs.tigera.io/calico/latest/getting-started/kubernetes/managed-public-cloud/eks)、[Cilium 1.20.1 chaining のソース](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/installation/cni-chaining-aws-cni.rst)、[Kubernetes NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)。

</details>

4. EKS 1.28 以降で Kubernetes API data の保存時暗号化について正しい説明はどれですか？
   * A) envelope encryption は既定で有効で、customer-managed KMS key は任意
   * B) Secret を暗号化するには全クラスターを作り直す必要がある
   * C) Base64 encoding が保存時暗号化になる
   * D) EKS control-plane database をアプリケーション sidecar で暗号化する

<details>
<summary>答えを表示</summary>

**答え: A) envelope encryption は既定で有効で、customer-managed KMS key は任意**

Kubernetes **1.28 以降**の EKS クラスターでは、KMS v2 の envelope encryption が既定で**すべての Kubernetes API data**に有効です。customer-managed KMS key を関連付けない場合は AWS owned key が使われます。Secret のほか、ConfigMap や保存される他の API resource も対象です。これは etcd disk encryption に加わるもので、ノードや EBS volume 上のアプリデータを暗号化するものではありません。

**変更前に状態を確認します。** `encryptionConfig` に customer-managed key ARN がないからといって、Secret が未暗号化とは限りません。console は AWS owned key mode を示しますが、その key の ARN は表示しません。

```bash
aws eks describe-cluster --name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" \
  --query 'cluster.{version:version,status:status,encryption:encryptionConfig}'

# Optional CMK inspection, only when a customer-managed key is required.
aws kms describe-key --key-id "${KMS_KEY_ARN:?Reviewed customer-managed key ARN}" \
  --region "$EXAMPLE_REGION" \
  --query 'KeyMetadata.{arn:Arn,state:KeyState,spec:KeySpec,usage:KeyUsage}'
```

**任意の customer-managed key (CMK):** customer key を管理する要件がある場合は、クラスターと同じ Region の対称暗号化 key を使います。key が使用可能であること、呼び出し元の IAM permission、key policy／grant、必要に応じて cross-account permission を確認してください。`eks.amazonaws.com` に複数の KMS action だけを許す一般的な policy では不十分です。provisioning／association identity には文書化された `kms:DescribeKey` と `kms:CreateGrant` permission が必要です。`CreateCluster` 時の `CreateGrant` を制御する条件として `kms:GrantIsForAWSResource` はサポートされません。

`CreateCluster` に provider を指定するか、eligible な既存クラスターに `AssociateEncryptionConfig` で CMK を関連付けられます。別クラスターの作成が常に必要なわけではありません。一般的な key 交換や暗号化無効化の操作として使わないでください。すでに CMK を関連付けたクラスターは、サポート対象の key 管理手順に従います。

```bash
# Optional CMK association for an eligible existing cluster.
# Review current configuration, key policy/grants and recovery procedures first.
KMS_CONFIG_DIR=$(mktemp -d /tmp/eks-kms-config.XXXXXX)
: "${KMS_CONFIG_DIR:?}"
jq -n --arg arn "${KMS_KEY_ARN:?}" \
  '[{resources:["secrets"],provider:{keyArn:$arn}}]' \
  > "$KMS_CONFIG_DIR/encryption.json" || exit 1
if ENCRYPTION_UPDATE_ID=$(aws eks associate-encryption-config \
  --cluster-name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --encryption-config "file://$KMS_CONFIG_DIR/encryption.json" \
  --query update.id --output text); then
  aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
    --update-id "$ENCRYPTION_UPDATE_ID" --query 'update.{status:status,errors:errors}'
fi
```

update ID を記録し、update が `Successful` または失敗を報告するまで確認します。要求を受理しただけでは完了ではありません。互換性のため `resources: ["secrets"]` は引き続き受け入れられます。EKS 1.28 以降では、これは暗号化を Secret に限定**しません**。この field は deprecated で、全 Kubernetes API data が envelope encryption されます。現行 API は resources list の省略／null／空も受け入れますが、応答には従来値の `["secrets"]` が残ります。Kubernetes 1.27 以前向けの旧 `enable-kms` 手順は履歴資料であり、サポート対象 version への移行目標ではありません。

クラスターが存在する間、演習後の cleanup として関連付けられた key を無効化・削除しないでください。key が使えなくなると control plane に影響し、恒久的に失うとクラスターを復旧できない可能性があります。CMK 選択前に復旧、アクセス、監視を確認します。AWS owned key による既定の暗号化には顧客側の key 設定は不要です。CMK には別途 KMS 料金がかかります。

**Secret の使い方は変わりません。** 認可済みの API client と Pod は利用可能な値を受け取ります。保存時暗号化は RBAC、ワークロード ID、log／backup 保護の代わりではありません。次の manifest は公開ダミー値を意図的に使うもので、本番用 Secret ではありません。

```yaml
# Public dummy data for a newly created secrets-lab namespace only.
apiVersion: v1
kind: Secret
metadata:
  name: example-credentials
  namespace: secrets-lab
type: Opaque
stringData:
  username: example-user
  password: public-training-placeholder
```

```bash
# Inspect keys and metadata without printing values.
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" \
  -n secrets-lab get secret example-credentials -o json |
  jq '{name:.metadata.name,type:.type,keys:(.data|keys)}'
```

実際の認証情報については、平文または Base64 値を含む manifest、shell history 上の literal、値を表示する診断を commit しないでください。Base64 は元に戻せる encoding です。AWS Secrets Manager は CSI mount file や Kubernetes Secret を同期する controller と連携できます。すべてのアプリケーションを SDK 変更する必要があるとは限りません。同期した Secret も Kubernetes の access control 対象です。sidecar で managed API server の保存時暗号化を設定することはできません。

参考資料: [既定の envelope encryption](https://docs.aws.amazon.com/eks/latest/userguide/envelope-encryption.html)、[AssociateEncryptionConfig](https://docs.aws.amazon.com/eks/latest/APIReference/API_AssociateEncryptionConfig.html)、[旧 KMS 手順と権限](https://docs.aws.amazon.com/eks/latest/userguide/enable-kms.html)、[EKS での Secrets Manager](https://docs.aws.amazon.com/secretsmanager/latest/userguide/integrating_csi_driver.html)。

</details>

5. AL2023 の EC2 managed node で kubelet 設定をカスタマイズする方法はどれですか？
   * A) console で EKS control-plane kubelet を編集する
   * B) eksctl または launch-template user data から、サポート対象の nodeadm NodeConfig を使う
   * C) kubectl edit node で status.capacity を変える
   * D) AL2023 の起動ごとに AL2 `bootstrap.sh` を実行する

<details>
<summary>答えを表示</summary>

**答え: B) eksctl または launch-template user data から、サポート対象の nodeadm NodeConfig を使う**

**AL2023 EC2 node** では `nodeadm` の `NodeConfig` とサポート対象の eksctl／launch-template 統合を使います。AL2 の `/etc/eks/bootstrap.sh` 手順や、存在を前提にした `eksctl create nodegroup --kubelet-extra-args` flag は使いません。この例で旧 `kubeletExtraArgs` map は managed node group 用のサポート対象 field ではありません。

**eksctl:** AL2023 では名前に反して、`overrideBootstrapCommand` には YAML `NodeConfig` を入れます。eksctl はこれを user data の先頭に加え、nodeadm が生成済みの node 設定と統合します。EKS 選択の native AMI では、EKS がクラスターに必要な既定設定を渡します。広く展開する前に test node で実効値を確認します。

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
  - name: custom-kubelet
    amiFamily: AmazonLinux2023
    instanceType: m5.large
    privateNetworking: true
    desiredCapacity: 2
    minSize: 2
    maxSize: 5
    labels:
      example.com/environment: test
    overrideBootstrapCommand: |
      apiVersion: node.eks.aws/v1alpha1
      kind: NodeConfig
      spec:
        kubelet:
          config:
            kubeReserved:
              cpu: 100m
              memory: 300Mi
            systemReserved:
              cpu: 200m
              memory: 512Mi
            evictionHard:
              memory.available: 500Mi
            mergeDefaultEvictionSettings: true
```

上記の resource reservation と 500 MiB eviction threshold は**説明用の値**であり、測定に基づく推奨値ではありません。これらは Pod の allocatable capacity を減らし、不適切なら eviction を起こします。`mergeDefaultEvictionSettings: true` は Kubernetes 1.36 でサポートされ、部分的な eviction map を kubelet が処理するとき未指定の既定シグナルを保ちます。適切に merge しないと、1つの signal だけを指定した結果、ほかの既定 threshold を誤ってゼロにする可能性があります。

**custom AMI／launch-template 経路:** eksctl が生成した設定の外で独自 AMI ID を使う場合は、cluster name、API endpoint、Base64 CA、service CIDR など完全なクラスター metadata を指定します。[Part 1 クイズの上級問題5](02-eks-cluster-creation-part1-quiz.md#advanced-topics) の metadata 生成手順を再利用し、レビュー済み `spec.kubelet.config` 設定を NodeConfig に加えます。kubelet だけを含む部分 object は、単独で使える完全な bootstrap 設定ではありません。

AL2023 は user data の前に `nodeadm-config`、後に `nodeadm-run` を実行します。`nodeadm init` を再実行したり、それらの service と競合する方法で kubelet を手動起動／再設定したりしないでください。Bottlerocket や Windows など、ほかの OS は別の構成方式を使います。この例は EKS Auto Mode node には適用されません。

| 設定 | 確認する内容 |
| --- | --- |
| `maxPods` / nodeadm `maxPodsExpression` | instance ENI／IP 制限、CNI mode、prefix delegation、対応する密度。110 を一律に強制しない |
| Node label／taint | managed node group の field を優先し、EKS／AZ label を上書きせず独自 label prefix を使う |
| `kubeReserved`, `systemReserved` | 実際の host／system workload 要件と Node Allocatable |
| `evictionHard`、soft threshold | memory／disk／inode signal と既定値 merge の動作。無関係な保護を無効化しない |
| Cgroup driver | 選択した OS／container runtime との互換性。レビュー済み変更が不要なら検証済み AMI の既定値を維持 |

**検証:** Node capacity／allocatable と実効 service 設定／log を調べます。Node が Ready であるだけでは、カスタム値すべてが反映された証拠になりません。この監査では設定 syntax と公式 field 定義を確認しましたが、これらの設定で node を起動していません。

```bash
# Kubernetes-side checks through the intended cluster context.
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" describe node "${EXAMPLE_NODE_NAME:?}"

# Run separately on a specifically authorized AL2023 test node.
sudo systemctl status nodeadm-config nodeadm-run kubelet --no-pager
sudo systemctl cat kubelet
sudo journalctl -u nodeadm-config -u nodeadm-run -u kubelet --since '-15 min' --no-pager
```

すべての AMI に `/etc/systemd/system/kubelet.service.d/10-kubelet-args.conf` があると思い込まず、設定対象 service の実際の config path を使います。診断 log は必要に応じて量を制限し、保護してください。

`kubectl edit node` で Node metadata は変更できますが、kubelet の起動設定は変わりません。SSM で host command を実行することはできますが、個別の host 編集は managed node の将来の置換設定として永続せず、停止を伴う再起動が必要なことがあります。レビュー済み設定を provisioning 設定に入れ、node の置換とテストを計画的に行います。

参考資料: [eksctl の AL2023 bootstrapping](https://docs.aws.amazon.com/eks/latest/eksctl/node-bootstrapping.html)、[AL2023 service](https://docs.aws.amazon.com/eks/latest/userguide/al2023.html)、[nodeadm API](https://awslabs.github.io/amazon-eks-ami/nodeadm/doc/api/)、[KubeletConfiguration](https://kubernetes.io/docs/reference/config-api/kubelet-config.v1beta1/)、[Kubernetes 1.36 field 定義](https://github.com/kubernetes/kubelet/blob/v0.36.0/config/v1beta1/types.go)。

</details>

6. EKS で削除された PodSecurityPolicy の制御を置き換える仕組みはどれですか？
   * A) EC2 セキュリティグループだけ
   * B) Pod Security Admission と、必要に応じて互換性のある policy engine
   * C) CloudWatch log retention だけ
   * D) 各 Pod に保存した IAM user access key

<details>
<summary>答えを表示</summary>

**答え: B) Pod Security Admission と、必要に応じて互換性のある policy engine**

PodSecurityPolicy は Kubernetes 1.21 で deprecated になり、1.25 で削除されました。組み込みの **Pod Security Admission (PSA)** で **Pod Security Standards (PSS)** を適用し、標準を超える要件には適切な policy engine を使います。

**PSA:** PSS の level は Privileged、Baseline、Restricted の3つで、`enforce`、`audit`、`warn` は別々の mode です。新しく作る lab namespace では Baseline を enforce し、Restricted 違反を報告する例です。policy version は EKS 1.36 の例に固定されています。実際のクラスターがサポートする version を選んでください。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: policy-engine-lab
  labels:
    pod-security.kubernetes.io/enforce: baseline
    pod-security.kubernetes.io/enforce-version: v1.36
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: v1.36
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: v1.36
```

既存の共有 namespace にラベルを無計画に付けないでください。最初は audit／warn で workload manifest の問題を直してから enforcement を強めます。PSA は Pod を compliant な状態に変更せず、稼働中 Pod を退避もしません。Pod の admission を評価します。workload template への warning／audit は、controller が Pod を作ろうとする前に違反を見つけるのに役立ちます。

**Kyverno:** この監査例で chart 3.9.1 は controller 1.19.1 を含みます。Kyverno 1.19 は従来の `ClusterPolicy`／`Policy` type を deprecated とし、migration guide は 1.20 での削除を予定しています。新しい例では現行の CEL-based policy API を使います。既存 policy は互換性のない upgrade の前に移行し、controller version だけを変えないでください。

```bash
# Optional new installation; review existing controllers and release compatibility.
helm repo add kyverno https://kyverno.github.io/kyverno/
helm repo update kyverno
helm install kyverno kyverno/kyverno --version 3.9.1 \
  --namespace kyverno --create-namespace \
  --kubeconfig "${EXAMPLE_KUBECONFIG:?}" --wait --timeout 5m
```

以下の `policies.kyverno.io/v1` **ValidatingPolicy** は、通常／init／ephemeral container の `privileged: true` を拒否し、lab namespace のみを対象にします。field の省略と false は許可します。

```yaml
apiVersion: policies.kyverno.io/v1
kind: ValidatingPolicy
metadata:
  name: disallow-privileged-lab
spec:
  validationActions:
  - Deny
  evaluation:
    background:
      enabled: true
  matchConstraints:
    resourceRules:
    - apiGroups:
      - ''
      apiVersions:
      - v1
      operations:
      - CREATE
      - UPDATE
      resources:
      - pods
      - pods/ephemeralcontainers
  matchConditions:
  - name: lab-only
    expression: object.metadata.namespace == 'policy-engine-lab'
  validations:
  - expression: object.spec.containers.all(c, !has(c.securityContext) || !has(c.securityContext.privileged) || !c.securityContext.privileged)
    message: Privileged containers are not allowed.
  - expression: '!has(object.spec.initContainers) || object.spec.initContainers.all(c, !has(c.securityContext) ||
      !has(c.securityContext.privileged) || !c.securityContext.privileged)'
    message: Privileged initContainers are not allowed.
  - expression: '!has(object.spec.ephemeralContainers) || object.spec.ephemeralContainers.all(c, !has(c.securityContext)
      || !has(c.securityContext.privileged) || !c.securityContext.privileged)'
    message: Privileged ephemeralContainers are not allowed.
```

これは1つの制御例であり、Baseline や Restricted 全体ではありません。policy engine／CRD を準備してから policy を適用し、対象クラスターで実際の admission／subresource 動作を確認します。background evaluation は既存違反を報告しますが、稼働中 workload を退避しません。

**OPA Gatekeeper の代替案:** 要件に合うレビュー済み Gatekeeper release を導入します。この例は chart／controller 3.23.1 に固定しています。

```bash
# Alternative policy-engine example, not a prerequisite for the Kyverno example.
helm repo add gatekeeper https://open-policy-agent.github.io/gatekeeper/charts
helm repo update gatekeeper
helm install gatekeeper gatekeeper/gatekeeper --version 3.23.1 \
  --namespace gatekeeper-system --create-namespace \
  --kubeconfig "${EXAMPLE_KUBECONFIG:?}" --wait --timeout 5m
```

Gatekeeper では先に `templates.gatekeeper.sh/v1` の ConstraintTemplate が必要です。template とそこから生成される constraint CRD の成立を待ってから対応する Constraint を適用してください。次の Rego 例は同じ3種類の container list を検査し、lab namespace に対象を限定します。

```yaml
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: k8snoprivilegedlab
spec:
  crd:
    spec:
      names:
        kind: K8sNoPrivilegedLab
      validation:
        openAPIV3Schema:
          type: object
  targets:
  - target: admission.k8s.gatekeeper.sh
    rego: "package k8snoprivilegedlab\n\ncontainers[c] {\n  c := input.review.object.spec.containers[_]\n\
      }\ncontainers[c] {\n  c := input.review.object.spec.initContainers[_]\n}\ncontainers[c]\
      \ {\n  c := input.review.object.spec.ephemeralContainers[_]\n}\nviolation[{\"\
      msg\": msg}] {\n  c := containers[_]\n  c.securityContext.privileged == true\n\
      \  msg := sprintf(\"Privileged container is not allowed: %v\", [c.name])\n}\n"
---
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sNoPrivilegedLab
metadata:
  name: no-privileged-lab
spec:
  enforcementAction: deny
  match:
    scope: Namespaced
    namespaces:
    - policy-engine-lab
    kinds:
    - apiGroups:
      - ''
      kinds:
      - Pod
```

Gatekeeper の `enforcementAction: deny` は該当する違反を拒否します。段階的な導入では `dryrun`／`warn` を使えます。ConstraintTemplate だけでは policy は適用されません。導入済み release がサポートする API／schema と Rego mode を使ってください。

**検証と制約:** Kyverno 1.19.1 CLI (warning を error 扱い) と Gatekeeper 3.23.1 Gator を使い、各6ケースをローカルで実行しました。ケースは明示的な false、field 省略、通常／init／ephemeral container の privileged、対象外 namespace です。両実装とも意図したローカル結果でした。クラスターへの導入や実際の admission test は行っていません。

```bash
# Offline policy logic checks using locally reviewed fixture files.
kyverno apply kyverno-policy.yaml --resource test-pod.yaml --warnings-as-errors
gator test --filename gatekeeper-policy.yaml --filename test-pod.yaml --output=json
```

PSA や別の webhook も拒否する場合、実際の拒否を特定の engine によるものと決めつけないでください。policy／controller の状態、対象範囲、実際の admission 応答と report を確認します。host namespace、hostPath、capability、privilege escalation など、PSS が求める制御全体を使ってください。

AWS Security Hub、AWS Config、EC2 security group はそれぞれ役割が異なり、Kubernetes Pod admission enforcement の代わりにはなりません。

参考資料: [PSA](https://kubernetes.io/docs/concepts/security/pod-security-admission/)、[PSS](https://kubernetes.io/docs/concepts/security/pod-security-standards/)、[Kyverno CEL migration](https://kyverno.io/docs/guides/migration-to-cel/)、[Kyverno 1.19.1](https://github.com/kyverno/kyverno/releases/tag/v1.19.1)、[Gatekeeper 3.23.1 how-to](https://github.com/open-policy-agent/gatekeeper/blob/v3.23.1/website/docs/howto.md)。

</details>

7. IRSA の web-identity trust に必要な IAM identity-provider の前提条件は何ですか？
   * A) 各 Pod に IAM user access key を保存する
   * B) cluster-admin RoleBinding
   * C) クラスターの issuer と一致する IAM OIDC provider
   * D) 各 worker node の public IP

<details>
<summary>答えを表示</summary>

**答え: C) クラスターの issuer と一致する IAM OIDC provider**

IRSA では対象クラスターの issuer と一致する IAM OIDC provider が必要です。既に存在するか確認し、重複 provider を作ったり、別クラスターの issuer を流用したりしないでください。ワークロードが IAM role を引き受ける前にこの前提を満たす必要がありますが、role 作成より先にサービスアカウントを作って後から annotation することはできます。全リソースを常に同じ順番で作成する必要があるわけではありません。

```bash
aws eks describe-cluster --name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --query cluster.identity.oidc.issuer --output text
eksctl utils associate-iam-oidc-provider \
  --cluster "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" --approve
```

eksctl または現行の IAM OIDC provider 手順を使い、古い固定 certificate thumbprint をコピーしないでください。意図する client ID／audience は `sts.amazonaws.com` にします。VPC に internet egress がない場合、VPC 内から provider を設定するには別途 `oidc-eks` interface endpoint／private DNS、または到達可能な管理経路が必要なことがあります。IRSA の token exchange には regional STS 接続も必要です。

問題1の trust policy に `aud` と `sub` の両方を含めて role policy を限定してから、正しいサービスアカウントを annotation し、それを参照する新しい Pod を作成します。既存 Pod はサービスアカウントの annotation を変更しただけでは新しい注入設定を受け取りません。通常の controller rollout で再作成します。

identity 確認には問題1の明示的な Pod manifest を使います。`kubectl run --serviceaccount` は現行でサポートされる flag ではありません。

```bash
# After deploying the identity-check Pod from question 1.
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" -n irsa-lab \
  get pod irsa-identity-check -o jsonpath='{.status.phase}{"\n"}'
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n irsa-lab logs irsa-identity-check
```

Pod の終了状態を確認し、返された account／assumed-role identity が期待値と一致するか比べます。node role の identity は IRSA 成功の証拠ではありません。次に限定したアプリ操作だけをテストしてください。単一バケット向け policy なのに bucket 指定なしの `aws s3 ls` を実行すると全バケット一覧が必要になるため不適切です。

EKS Pod Identity は別の仕組みで、クラスターごとに IAM OIDC provider を作成する必要はありません。service account association、agent、IAM trust の要件を IRSA と分けて扱ってください。

参考資料: [IAM OIDC provider の作成](https://docs.aws.amazon.com/eks/latest/userguide/enable-iam-roles-for-service-accounts.html)、[IRSA の private connectivity](https://docs.aws.amazon.com/eks/latest/userguide/private-clusters.html)、[Pod 設定](https://docs.aws.amazon.com/eks/latest/userguide/pod-configuration.html)。

</details>

8. EKS control-plane log export を有効にする方法は何ですか？
   * A) managed control-plane host に agent を導入する
   * B) EKS API、console、または eksctl でクラスター logging を設定する
   * C) worker node だけに Fluentd を導入する
   * D) managed API server に SSH して設定を編集する

<details>
<summary>答えを表示</summary>

**答え: B) EKS API、console、または eksctl でクラスター logging を設定する**

EKS control-plane log export は EKS API、console、eksctl で有効にします。AWS が control-plane host を運用するため、worker node に CloudWatch／Fluentd agent を入れても control-plane log は有効になりません。運用者が managed control-plane host に SSH することもできません。

**AWS CLI:** 現在の設定を確認して必要な type を選びます。これは非同期 update です。update ID を記録し、`describe-update` を繰り返して成功または失敗を確認します。logging update 時、EKS は各クラスター subnet に最大5個の空き IP address を必要とすることがあります。

```bash
# Enable the reviewed set of log types; this example enables all five.
if LOG_UPDATE_ID=$(aws eks update-cluster-config \
  --name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}' \
  --query update.id --output text); then
  aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
    --update-id "$LOG_UPDATE_ID" --query 'update.{status:status,errors:errors}'
fi
```

API／audit のみを有効にし、他の3種を明示的に無効にする場合は、audit／retention 要件を確認したうえで次の**別案**の logging payload を使います。2つの設定を続けて実行したり、費用削減だけを目的に必要な log を無効化したりしないでください。

```json
{
  "clusterLogging": [
    {"types": ["api", "audit"], "enabled": true},
    {"types": ["authenticator", "controllerManager", "scheduler"], "enabled": false}
  ]
}
```

**eksctl の別案:** preview と apply は別の操作です。レビュー済み変更を適用するには `--approve` が必要です。意図がある場合、`--disable-types` で指定した type を無効にできます。

```bash
# Alternative interface; do not submit a second update while one is running.
# Without --approve this previews the logging change.
eksctl utils update-cluster-logging \
  --cluster "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --enable-types api,audit,authenticator,controllerManager,scheduler

# Apply the reviewed change.
eksctl utils update-cluster-logging \
  --cluster "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --enable-types api,audit,authenticator,controllerManager,scheduler --approve
```

**Console:** クラスターを選び、**Observability** を開いて **Control plane logging → Manage logging** に進みます。各 log type を選んでレビュー済み設定を保存します。

| type | 目的 | stream prefix |
| --- | --- | --- |
| `api` | API server component の診断。最初の flag は log rotation 前に取得した場合のみ利用可能 | `kube-apiserver-` |
| `audit` | managed audit policy に記録される Kubernetes API 操作 | `kube-apiserver-audit-` |
| `authenticator` | IAM 認証の診断 | `authenticator-` |
| `controllerManager` | 組み込み Kubernetes control loop の診断 | `kube-controller-manager-` |
| `scheduler` | Pod scheduling の診断 | `kube-scheduler-` |

Audit log はアプリケーション要求すべてや、ノード上の全 process／network 操作を記録するものではありません。関連する AWS API 操作は別途 CloudTrail に記録されます。control-plane log の配信は best effort で通常は数分以内です。有効化しても、すでに rotation で失われた log は復元しません。

**export の確認:** log はクラスターの account／Region 内の `/aws/eks/<cluster-name>/cluster` にあります。stream suffix は rotation するため、恒久的な stream 名が1つあると思わず、最近の event 時刻を調べます。

```bash
aws eks describe-cluster --name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --query cluster.logging
aws logs describe-log-streams --region "$EXAMPLE_REGION" \
  --log-group-name "/aws/eks/$EXAMPLE_CLUSTER/cluster" \
  --order-by LastEventTime --descending --max-items 10
```

CloudWatch の取り込み、保存、query には料金が発生します。必要な retention／access control を設定し、必要な log type が実際に届いていることを確認してください。設定 update の成功は、期待した過去 event がすべてある証明ではありません。worker／application log collector は別の data-plane の課題です。

参考資料: [EKS control-plane logging](https://docs.aws.amazon.com/eks/latest/userguide/control-plane-logs.html)。

</details>

9. EKS managed node group の要求時に指定した instance type (custom template 内の type ではない) を変更するにはどうしますか？
   * A) console で instanceTypes field を直接編集する
   * B) 置き換え用 node group を作成し、workload migration を検証する
   * C) kubectl edit node で EC2 hardware を変更する
   * D) update-nodegroup-config に新しい instance type を渡す

<details>
<summary>答えを表示</summary>

**答え: B) 置き換え用 node group を作成し、workload migration を検証する**

この問題の対象は、custom launch template ではなく**managed node group の作成要求で指定した instance type**です。この type は `update-nodegroup-config` では変更できません。新しい group を作って workload を移行します。

別経路として、custom launch template で作成され instance type がその template 内に定義されている場合は、**同じ** template の新しい version をレビューし、`update-nodegroup-version` で適用できます。いずれも instance は置換されます。EKS 生成 template を変更したり、両方の場所に type を指定したり、異なる CPU architecture でも同じ AMI／image が動くと考えたりしないでください。

**1. 置換用容量を作成します。** instance offering、quota、architecture、CNI／IP capacity、AZ、storage、node role permission を確認します。次の2コマンドは既存 test cluster で使う別案です。

```bash
# Alternative 1: eksctl, for an unused managed node-group name.
eksctl create nodegroup --cluster "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --name "${NEW_NODEGROUP_NAME:?}" \
  --managed --node-ami-family AmazonLinux2023 --node-private-networking \
  --node-type m5.large --nodes 3 --nodes-min 1 --nodes-max 5 \
  --node-labels "example.com/migration-target=true"

# Alternative 2: AWS CLI; do not run both for the same node group.
aws eks create-nodegroup --cluster-name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --nodegroup-name "${NEW_NODEGROUP_NAME:?}" \
  --subnets "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" \
  --instance-types m5.large --ami-type AL2023_x86_64_STANDARD \
  --scaling-config minSize=1,maxSize=5,desiredSize=3 \
  --node-role "${NODE_ROLE_ARN:?}" \
  --labels '{"example.com/migration-target":"true"}'
```

**2. 新しい group を確認します。** `ACTIVE` になり、node が正常な `Ready` 状態で CNI／DNS が動くまで待ちます。label 一覧だけではアプリケーションの readiness を証明できません。

```bash
aws eks describe-nodegroup --cluster-name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --nodegroup-name "${NEW_NODEGROUP_NAME:?}" \
  --query 'nodegroup.{status:status,health:health,types:instanceTypes,subnets:subnets}'
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" get nodes \
  -l example.com/migration-target=true -o wide
```

**3. 移行してテストします。** アプリケーションごとの rolling または blue/green plan を選びます。Service は node group 名ではなく、選択した ready Pod endpoint へ traffic を送ります。rollback に必要な期間と data 互換性を理解するまで旧 capacity を残してください。

手動 drain では、古い node を1台選び、node-group label を確認し、先に PDB、余剰 capacity、local storage を確認します。この例は eviction を迂回せず、`emptyDir` data を捨てません。drain に失敗したら原因を調べてから続行し、node は cordon 状態のままの場合があります。

```bash
# One reviewed node at a time, after validating replacement capacity.
OLD_NODE_JSON=$(kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" \
  get node "${OLD_NODE_NAME:?}" -o json) || exit 1
OLD_NODE_GROUP=$(printf '%s' "$OLD_NODE_JSON" |
  jq -er '.metadata.labels["eks.amazonaws.com/nodegroup"]') || exit 1
if [ "$OLD_NODE_GROUP" != "${OLD_NODEGROUP_NAME:?}" ]; then
  printf '%s\n' 'Node is not in the intended old managed node group.' >&2
  exit 1
fi
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" cordon "$OLD_NODE_NAME" &&
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" drain "$OLD_NODE_NAME" \
  --ignore-daemonsets --timeout=15m
```

または、実際のアプリケーションの Pod template を変更して置換 group を選択します。次の完全な例は、新規 `migration-lab` namespace 用の別デモであり、既存アプリへの置換 manifest ではありません。

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: migration-demo
  namespace: migration-lab
spec:
  replicas: 3
  selector:
    matchLabels:
      app: migration-demo
  template:
    metadata:
      labels:
        app: migration-demo
    spec:
      nodeSelector:
        example.com/migration-target: "true"
      containers:
        - name: nginx
          image: nginx:1.30.6
          ports:
            - containerPort: 80
          readinessProbe:
            httpGet:
              path: /
              port: 80
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              memory: 256Mi
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: migration-demo
  namespace: migration-lab
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: migration-demo
```

PDB は voluntary eviction 中に一致する Pod を2つ healthy に保つよう要求します。replica が3つなら、他条件を満たす場合に通常は一度に1つずつ退避できます。これは可用性を保証せず、直接削除から保護せず、node-local data も維持しません。代表的な workload test で配置、readiness、Service routing、persistent volume の AZ affinity、backup を確認してください。

**4. 検証後にだけ旧 group を削除します。** 移行を完了するために eksctl と AWS の削除 command を両方実行したり、PDB を迂回したりしないでください。対象クラスター／group を確認し、この移行が所有する group だけを削除します。

```bash
# Separate final step, after application/data validation and ownership review.
if [ "${MIGRATION_VERIFIED:?Set yes only after workload and data checks}" = yes ]; then
  eksctl delete nodegroup --cluster "${EXAMPLE_CLUSTER:?}" \
    --region "${EXAMPLE_REGION:?}" --name "${OLD_NODEGROUP_NAME:?}" --approve --wait
fi
```

アプリケーションの検証に失敗したら旧 group を残してください。blue/green は一時的な容量と費用を増やすもので、stateful な変更を簡単に rollback できる保証ではありません。`kubectl edit node` は Kubernetes metadata を変えるだけで、EC2 instance type は変更しません。

参考資料: [launch-template update](https://docs.aws.amazon.com/eks/latest/userguide/launch-templates.html)、[UpdateNodegroupConfig](https://docs.aws.amazon.com/eks/latest/APIReference/API_UpdateNodegroupConfig.html)、[drain](https://kubernetes.io/docs/tasks/administer-cluster/safely-drain-node/)。

</details>

10. EKS managed node group の taint について正しい説明はどれですか？
   * A) taint は kubectl でしか設定できない
   * B) console／API または eksctl の node-group 設定で行い、既存 Node の状態は別途確認する
   * C) EKS console では taint を設定できない
   * D) toleration があれば一致する taint を持つ group に必ず配置される

<details>
<summary>答えを表示</summary>

**答え: B) console／API または eksctl の node-group 設定で行い、既存 Node の状態は別途確認する**

managed node-group taint は EKS console／API または eksctl 設定 file で構成できます。console も有効な方法なので、CLI の選択肢があるという理由で不正解にしてはいけません。直接の `kubectl taint` は個々の Node object を変えるだけで、managed group の置換 node に適用される永続設定ではありません。

**eksctl の設定:** 既存クラスターと未使用 group 名に対するレビュー済み node-group 設定として保存し、`eksctl create nodegroup -f nodegroup.yaml` を使います。推測で CLI flag を使わず、サポート対象の `taints` field を指定してください。

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
  - name: tainted-ng
    amiFamily: AmazonLinux2023
    instanceType: m5.large
    privateNetworking: true
    desiredCapacity: 3
    minSize: 2
    maxSize: 5
    labels:
      example.com/pool: batch
    taints:
      - key: dedicated
        value: batch
        effect: NoSchedule
      - key: special
        value: "true"
        effect: PreferNoSchedule
```

**AWS CLI の別案:** Kubernetes／eksctl の effect 名は CamelCase ですが、EKS API では大文字名です。

| Kubernetes / eksctl | EKS API | 効果 |
| --- | --- | --- |
| `NoSchedule` | `NO_SCHEDULE` | 一致する toleration がない新規 Pod の scheduling を拒否。既存 Pod は残る |
| `PreferNoSchedule` | `PREFER_NO_SCHEDULE` | 弱い scheduling preference であり保証ではない |
| `NoExecute` | `NO_EXECUTE` | toleration のない既存 Pod も退避。`tolerationSeconds` で遅らせられる |

```bash
# Alternative to the eksctl file: create a new group through the EKS API.
aws eks create-nodegroup --cluster-name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --nodegroup-name "${NEW_NODEGROUP_NAME:?}" \
  --subnets "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" \
  --instance-types m5.large --ami-type AL2023_x86_64_STANDARD \
  --scaling-config minSize=2,maxSize=5,desiredSize=3 \
  --node-role "${NODE_ROLE_ARN:?}" \
  --labels '{"example.com/pool":"batch"}' \
  --taints '[{"key":"dedicated","value":"batch","effect":"NO_SCHEDULE"},{"key":"special","value":"true","effect":"PREFER_NO_SCHEDULE"}]'
```

```bash
# Separate update example for the intended existing group.
if TAINT_UPDATE_ID=$(aws eks update-nodegroup-config \
  --cluster-name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --nodegroup-name "${EXAMPLE_NODEGROUP:?}" \
  --taints '{"addOrUpdateTaints":[{"key":"dedicated","value":"batch","effect":"NO_SCHEDULE"}],"removeTaints":[{"key":"special","value":"true","effect":"PREFER_NO_SCHEDULE"}]}' \
  --query update.id --output text); then
  aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
    --nodegroup-name "$EXAMPLE_NODEGROUP" --update-id "$TAINT_UPDATE_ID" \
    --query 'update.{status:status,errors:errors}'
fi
```

update は非同期です。正常完了を待ち、Node の実際の taint を確認します。group 設定に taint が残っていても、既存 Node から手動削除された taint を EKS が自動で付け直すわけではありません。Node を変更できる人を制限し、変更後の状態を確認してください。

**専用 workload の配置:** toleration は Pod の scheduling を許可しますが、taint 付き group への配置を強制しません。適切な node selector／affinity と組み合わせます。完全なデモでは新しい `taint-lab` namespace を使います。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: batch-example
  namespace: taint-lab
spec:
  nodeSelector:
    example.com/pool: batch
  tolerations:
    - key: dedicated
      operator: Equal
      value: batch
      effect: NoSchedule
  restartPolicy: Never
  containers:
    - name: task
      image: busybox:1.37
      command: ["sh", "-c", "echo batch-example-complete"]
      resources:
        requests:
          cpu: 100m
          memory: 32Mi
        limits:
          memory: 64Mi
```

GPU group では互換性のある GPU instance／AMI も選び、対応 device plugin を導入します。workload は `nvidia.com/gpu` などの拡張 resource を要求する必要があります。`dedicated=gpu` taint だけでは driver を導入せず、GPU を割り当てもしません。taint は scheduling 制御であり、tenant 間のセキュリティ境界ではありません。

**保守作業:** 一時的な node taint で通常の新規 scheduling を抑止できますが、稼働中 Pod は drain されません。以下の2つの command は、レビュー済み maintenance window の開始時と終了時に対応します。

```bash
# Individual-node maintenance example; does not evict existing Pods.
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" taint node \
  "${EXAMPLE_NODE_NAME:?}" maintenance=planned:NoSchedule

# After the maintenance window, remove only this exact example taint.
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" taint node \
  "$EXAMPLE_NODE_NAME" maintenance=planned:NoSchedule-
```

退避が必要なら、別途 PDB を考慮した drain 手順を使います。すでに稼働中 Pod がある group へ即時退避の影響を確認せず `NoExecute` を追加しないでください。node bootstrap の登録 flag もありますが、この用途では managed-group 設定の方が明確です。

参考資料: [EKS managed-node taint](https://docs.aws.amazon.com/eks/latest/userguide/node-taints-managed-node-groups.html)。

</details>

## ハンズオン演習

### 演習1: IRSA (IAM Roles for Service Accounts) の設定

**シナリオ:** 既存 EKS クラスター上の Linux workload が、1つの S3 bucket 内にある承認済み `training/` prefix を読み取る必要があります。全 node に広い S3 policy を与えるのではなく、専用 workload role を付与します。

**前提条件:** commercial AWS partition 内の利用許可を受けた training cluster、AWS CLI v2、eksctl、jq を使います。operator には演習に必要な IAM／Kubernetes 権限が必要です。承認済み bucket の `training/` 配下にある既存の非機密 object を用意し、`S3_BUCKET`／`S3_TEST_KEY` を設定します。bucket policy と customer-managed encryption key がある場合、その object の暗号化に必要な権限も含めて対象 role を許可します。object の暗号化に必要な場合にだけ、別途限定した KMS 権限を追加します。この例では bucket／object を作成しません。

<details>
<summary>解答を表示</summary>

**1. 一意な namespace、private kubeconfig、クラスター OIDC provider を準備します。** cleanup が終わるまで生成 directory と所有者記録を保管します。同じ Bash session で手順を実行してください。途中で失敗したら再試行前に記録済み resource を調べます。

```bash
# Commercial AWS partition example; use an existing approved S3 training prefix.
: "${EXAMPLE_CLUSTER:?}"
: "${EXAMPLE_REGION:?}"
: "${S3_BUCKET:?Existing bucket containing the approved training object}"
: "${S3_TEST_KEY:?Existing non-sensitive object key under training/}"
case "$S3_TEST_KEY" in training/*) ;; *) printf '%s\n' 'Use a training/ key.' >&2; exit 1 ;; esac
IRSA_LAB_DIR=$(mktemp -d /tmp/eks-irsa-lab.XXXXXX)
: "${IRSA_LAB_DIR:?}"
IRSA_LAB_ID="irsa-quiz-$(date +%s)-$$"
IRSA_NAMESPACE="$IRSA_LAB_ID"
IRSA_ROLE_NAME="$IRSA_LAB_ID"
IRSA_SERVICE_ACCOUNT=s3-reader
IRSA_KUBECONFIG="$IRSA_LAB_DIR/kubeconfig"

aws sts get-caller-identity --output json > "$IRSA_LAB_DIR/caller.json" || exit 1
IRSA_ACCOUNT_ID=$(jq -er '.Account' "$IRSA_LAB_DIR/caller.json") || exit 1
jq -e '.Arn | startswith("arn:aws:")' "$IRSA_LAB_DIR/caller.json" >/dev/null || exit 1
aws eks describe-cluster --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --query cluster --output json > "$IRSA_LAB_DIR/cluster.json" || exit 1
IRSA_ISSUER=$(jq -er '.identity.oidc.issuer' "$IRSA_LAB_DIR/cluster.json") || exit 1
case "$IRSA_ISSUER" in https://*) ;; *) printf '%s\n' 'Invalid OIDC issuer.' >&2; exit 1 ;; esac
IRSA_ISSUER_HOST="${IRSA_ISSUER#https://}"
IRSA_PROVIDER_ARN="arn:aws:iam::$IRSA_ACCOUNT_ID:oidc-provider/$IRSA_ISSUER_HOST"

aws eks update-kubeconfig --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --kubeconfig "$IRSA_KUBECONFIG" --alias "$EXAMPLE_CLUSTER" || exit 1
kubectl --kubeconfig "$IRSA_KUBECONFIG" create namespace "$IRSA_NAMESPACE" || exit 1
IRSA_NAMESPACE_UID=$(kubectl --kubeconfig "$IRSA_KUBECONFIG" \
  get namespace "$IRSA_NAMESPACE" -o jsonpath='{.metadata.uid}') || exit 1
: "${IRSA_NAMESPACE_UID:?}"
jq -n --arg namespace "$IRSA_NAMESPACE" --arg uid "$IRSA_NAMESPACE_UID" \
  '{namespace:$namespace,namespaceUID:$uid}' > "$IRSA_LAB_DIR/ownership.json" || exit 1

# The cluster's provider is shared infrastructure; eksctl checks/associates it.
eksctl utils associate-iam-oidc-provider --cluster "$EXAMPLE_CLUSTER" \
  --region "$EXAMPLE_REGION" --approve || exit 1
aws iam get-open-id-connect-provider --open-id-connect-provider-arn "$IRSA_PROVIDER_ARN" \
  --output json > "$IRSA_LAB_DIR/provider.json" || exit 1
jq -e '.ClientIDList | index("sts.amazonaws.com") != null' \
  "$IRSA_LAB_DIR/provider.json" >/dev/null || exit 1
```

IRSA では workload から STS 接続と S3 access が必要です。private-only 環境では適切な regional STS／ECR／S3 経路が必要です。VPC 内から IAM OIDC provider を作る場合には `oidc-eks` 接続も要ることがあります。IMDS と service account 利用は別々に制限してください。IRSA だけでは Pod の隔離境界になりません。

**2. 専用 role と範囲を絞った policy を作成します。** trust policy は意図した audience と正確な namespace／service-account subject の両方を要求します。policy は bucket の `training/` prefix だけを一覧でき、その prefix 内の object だけを読み取れるようにします。`ListAllMyBuckets` は許可しません。

```bash
jq -n --arg provider "${IRSA_PROVIDER_ARN:?}" --arg issuer "${IRSA_ISSUER_HOST:?}" \
  --arg subject "system:serviceaccount:${IRSA_NAMESPACE:?}:${IRSA_SERVICE_ACCOUNT:?}" \
  '{
    Version:"2012-10-17",
    Statement:[{
      Effect:"Allow",
      Principal:{Federated:$provider},
      Action:"sts:AssumeRoleWithWebIdentity",
      Condition:{StringEquals:{
        ($issuer+":aud"):"sts.amazonaws.com",
        ($issuer+":sub"):$subject
      }}
    }]
  }' > "${IRSA_LAB_DIR:?}/trust.json" || exit 1

jq -n --arg bucket "${S3_BUCKET:?}" \
  '{
    Version:"2012-10-17",
    Statement:[
      {
        Effect:"Allow",Action:"s3:ListBucket",Resource:("arn:aws:s3:::"+$bucket),
        Condition:{StringLike:{"s3:prefix":["training/","training/*"]}}
      },
      {
        Effect:"Allow",Action:"s3:GetObject",
        Resource:("arn:aws:s3:::"+$bucket+"/training/*")
      }
    ]
  }' > "$IRSA_LAB_DIR/s3-policy.json" || exit 1

# Stop on creation failure; never attach this policy to a pre-existing role.
aws iam create-role --role-name "${IRSA_ROLE_NAME:?}" \
  --assume-role-policy-document "file://$IRSA_LAB_DIR/trust.json" \
  --tags "Key=TrainingLab,Value=${IRSA_LAB_ID:?}" \
  --query Role --output json > "$IRSA_LAB_DIR/created-role.json" || exit 1
IRSA_ROLE_ARN=$(jq -er '.Arn' "$IRSA_LAB_DIR/created-role.json") || exit 1
IRSA_ROLE_ID=$(jq -er '.RoleId' "$IRSA_LAB_DIR/created-role.json") || exit 1
jq -n --arg namespace "$IRSA_NAMESPACE" --arg uid "${IRSA_NAMESPACE_UID:?}" \
  --arg roleName "$IRSA_ROLE_NAME" --arg roleArn "$IRSA_ROLE_ARN" --arg roleId "$IRSA_ROLE_ID" \
  '{namespace:$namespace,namespaceUID:$uid,roleName:$roleName,roleARN:$roleArn,roleID:$roleId}' \
  > "$IRSA_LAB_DIR/ownership.json" || exit 1
aws iam put-role-policy --role-name "$IRSA_ROLE_NAME" \
  --policy-name ScopedTrainingS3Read \
  --policy-document "file://$IRSA_LAB_DIR/s3-policy.json" || exit 1
```

role は新規作成である必要があります。作成に失敗すれば script は policy を付ける前に停止し、変更されない IAM `RoleId` を cleanup 用に記録します。これにより偶然同名の既存 role に lab policy を付けるのを防ぎます。

**3. サービスアカウントと短命の test Pod を作成します。** 3つの container が呼び出し元 identity の確認、許可 prefix 内の object を最大1個 listing、選択した object の metadata 取得を行います。出力するのは件数／長さだけで、identity metadata も記録します。token、secret key、object 内容は表示しません。

```bash
# JSON construction preserves literal object keys and prevents YAML interpolation errors.
jq -n --arg ns "${IRSA_NAMESPACE:?}" --arg sa "${IRSA_SERVICE_ACCOUNT:?}" \
  --arg role "${IRSA_ROLE_ARN:?}" --arg region "${EXAMPLE_REGION:?}" \
  --arg bucket "${S3_BUCKET:?}" --arg key "${S3_TEST_KEY:?}" '
  {
    apiVersion:"v1",kind:"List",items:[
      {
        apiVersion:"v1",kind:"ServiceAccount",
        metadata:{name:$sa,namespace:$ns,annotations:{
          "eks.amazonaws.com/role-arn":$role,
          "eks.amazonaws.com/sts-regional-endpoints":"true"
        }}
      },
      {
        apiVersion:"v1",kind:"Pod",metadata:{name:"irsa-check",namespace:$ns},
        spec:{
          serviceAccountName:$sa,nodeSelector:{"kubernetes.io/os":"linux"},restartPolicy:"Never",
          containers:[
            {name:"identity",args:["--region",$region,"sts","get-caller-identity"]},
            {name:"list-prefix",args:["--region",$region,"s3api","list-objects-v2","--bucket",$bucket,
              "--prefix","training/","--max-keys","1","--query","KeyCount","--output","json"]},
            {name:"object-metadata",args:["--region",$region,"s3api","head-object","--bucket",$bucket,
              "--key",$key,"--query","ContentLength","--output","json"]}
          ] | map(.+{
            image:"public.ecr.aws/aws-cli/aws-cli:2.36.43",command:["aws"],
            resources:{requests:{cpu:"100m",memory:"128Mi"},limits:{memory:"256Mi"}}
          })
        }
      }
    ]
  }' > "${IRSA_LAB_DIR:?}/workload.json" || exit 1
kubectl --kubeconfig "${IRSA_KUBECONFIG:?}" create -f "$IRSA_LAB_DIR/workload.json" || exit 1
kubectl --kubeconfig "$IRSA_KUBECONFIG" -n "$IRSA_NAMESPACE" \
  wait --for=jsonpath='{.status.phase}'=Succeeded pod/irsa-check --timeout=180s || exit 1
kubectl --kubeconfig "$IRSA_KUBECONFIG" -n "$IRSA_NAMESPACE" \
  logs irsa-check -c identity > "$IRSA_LAB_DIR/pod-identity.json" || exit 1
jq -e --arg account "${IRSA_ACCOUNT_ID:?}" --arg role "${IRSA_ROLE_NAME:?}" \
  '.Account == $account and (.Arn | startswith("arn:aws:sts::"+$account+":assumed-role/"+$role+"/"))' \
  "$IRSA_LAB_DIR/pod-identity.json" >/dev/null || exit 1
kubectl --kubeconfig "$IRSA_KUBECONFIG" -n "$IRSA_NAMESPACE" logs irsa-check -c list-prefix
kubectl --kubeconfig "$IRSA_KUBECONFIG" -n "$IRSA_NAMESPACE" logs irsa-check -c object-metadata
```

3つすべての container が成功し、identity 確認結果が期待する account／role と一致する必要があります。node role の identity は失敗です。Pod が失敗したら container ごとの status／log、IAM trust、prefix、bucket／key policy、接続性を調べてください。認可失敗の解決策として `AmazonS3ReadOnlyAccess` を付けないでください。

IAM の変更は反映に時間がかかる場合があります。原因を修正したら、元の失敗実行で成功が証明されたと考えず、所有 namespace 内で意図的に test Pod を作り直します。許可された操作の成功だけでは、ほかのすべての操作が拒否されることは証明できません。適用される全 IAM／resource policy を確認し、必要なら承認済みの negative test を行います。

**4. 所有する namespace と role を削除します。** namespace UID と IAM RoleId で名前の再利用を防ぎます。namespace がすでになければ、記録した role の cleanup は続行できます。予期しない inline policy や lookup 失敗があれば後続 cleanup は停止します。部分失敗を調べ、無関係な resource を削除しないでください。

```bash
# Recover the recorded values from ownership.json if this is a later shell.
IRSA_CLEANUP_NAMESPACE_OK=false
if CURRENT_IRSA_UID=$(kubectl --kubeconfig "${IRSA_KUBECONFIG:?}" \
  get namespace "${IRSA_NAMESPACE:?}" --ignore-not-found -o jsonpath='{.metadata.uid}'); then
  if [ -z "$CURRENT_IRSA_UID" ]; then
    IRSA_CLEANUP_NAMESPACE_OK=true
  elif [ "$CURRENT_IRSA_UID" = "${IRSA_NAMESPACE_UID:?Recorded UID required}" ]; then
    if kubectl --kubeconfig "$IRSA_KUBECONFIG" delete namespace "$IRSA_NAMESPACE" --wait=true; then
      IRSA_CLEANUP_NAMESPACE_OK=true
    else
      exit 1
    fi
  else
    printf '%s\n' 'Namespace UID mismatch; stop and inspect.' >&2
    exit 1
  fi
else
  printf '%s\n' 'Namespace lookup failed; stop and inspect.' >&2
  exit 1
fi

if [ "$IRSA_CLEANUP_NAMESPACE_OK" = true ]; then
  CURRENT_IRSA_ROLE_JSON=$(aws iam get-role --role-name "${IRSA_ROLE_NAME:?}" \
    --query Role --output json) || exit 1
  CURRENT_IRSA_ROLE_ID=$(printf '%s' "$CURRENT_IRSA_ROLE_JSON" | jq -er '.RoleId') || exit 1
  if [ "$CURRENT_IRSA_ROLE_ID" = "${IRSA_ROLE_ID:?Recorded IAM RoleId required}" ]; then
    IRSA_INLINE_POLICIES=$(aws iam list-role-policies --role-name "$IRSA_ROLE_NAME" \
      --query PolicyNames --output json) || exit 1
    printf '%s' "$IRSA_INLINE_POLICIES" |
      jq -e 'all(.[]; . == "ScopedTrainingS3Read")' >/dev/null || exit 1
    if printf '%s' "$IRSA_INLINE_POLICIES" | jq -e 'index("ScopedTrainingS3Read") != null' >/dev/null; then
      aws iam delete-role-policy --role-name "$IRSA_ROLE_NAME" \
        --policy-name ScopedTrainingS3Read || exit 1
    fi
    aws iam delete-role --role-name "$IRSA_ROLE_NAME"
  else
    printf '%s\n' 'IAM RoleId mismatch; no IAM deletion attempted.' >&2
    exit 1
  fi
fi
```

クラスター、共有 OIDC provider、bucket、object は残します。namespace／role の削除を確認し、どこかで失敗したら所有者記録を保管してください。Pod を停止しても、すでに発行済みの STS 認証情報が直ちにすべて無効になるとは限りません。

この監査では AWS に role を provision したり Pod を実行したりしていません。ローカル検査では生成 manifest／policy と失敗時 guard を検証しました。実際の IAM 反映、network 到達性、S3 access は環境ごとにテストしてください。

参考資料: [IRSA role 設定](https://docs.aws.amazon.com/eks/latest/userguide/associate-service-account-role.html)、[IRSA の private connectivity](https://docs.aws.amazon.com/eks/latest/userguide/private-clusters.html)、[S3 policy condition](https://docs.aws.amazon.com/AmazonS3/latest/userguide/amazon-s3-policy-keys.html)。

</details>

### 演習2: EKS クラスターセキュリティの強化

**シナリオ:** 専用 EKS 1.36 training cluster 上で具体的なセキュリティ制御を評価します。これは統合演習であり、本番で検証済みの設定ではありません。

**前提条件:** cluster 管理の承認、AWS CLI v2、kubectl、jq、互換性のある EC2 Linux node、NetworkPolicy を有効にしたサポート対象の EKS-managed VPC CNI、`kube-system` 内の一般的な CoreDNS Pod を用意します。CNI／kernel の現行要件は基本問題3を参照してください。baseline の Pod 間通信が動作することが必要です。組織全体の policy がある場合は、別途承認された test 設計が必要になることがあります。この演習のためだけに2つ目の CNI を入れないでください。

<details>
<summary>解答を表示</summary>

**1. 対象を調べ、現在の設定を保存します。** 実際に承認された運用者 egress CIDR を設定し、文書用範囲を使わないでください。この例は手順に進む前に EKS 1.36 と有効な managed CNI policy 設定を確認します。

```bash
: "${EXAMPLE_CLUSTER:?Use a dedicated EKS 1.36 training cluster}"
: "${EXAMPLE_REGION:?}"
: "${APPROVED_API_CIDR:?Actual approved administration egress CIDR}"
SECURITY_LAB_DIR=$(mktemp -d /tmp/eks-security-lab.XXXXXX)
: "${SECURITY_LAB_DIR:?}"
SECURITY_NAMESPACE="security-quiz-$(date +%s)-$$"
SECURITY_KUBECONFIG="$SECURITY_LAB_DIR/kubeconfig"

aws eks describe-cluster --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --query cluster --output json > "$SECURITY_LAB_DIR/before-cluster.json" || exit 1
jq -e '.version == "1.36" and .status == "ACTIVE"' \
  "$SECURITY_LAB_DIR/before-cluster.json" >/dev/null || exit 1
aws eks describe-addon --cluster-name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --addon-name vpc-cni --query addon --output json > "$SECURITY_LAB_DIR/cni.json" || exit 1
jq -e '(.configurationValues // "{}" | fromjson | .enableNetworkPolicy) as $enabled |
  .status == "ACTIVE" and ($enabled == true or $enabled == "true")' \
  "$SECURITY_LAB_DIR/cni.json" >/dev/null || exit 1
aws eks update-kubeconfig --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --kubeconfig "$SECURITY_KUBECONFIG" --alias "$EXAMPLE_CLUSTER" || exit 1

# Serialize cluster configuration updates. A timeout does not cancel an AWS update.
security_wait_update() {
  local update_id="$1" status attempt
  for ((attempt=1; attempt<=60; attempt++)); do
    status=$(aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
      --update-id "$update_id" --query update.status --output text) || return 1
    case "$status" in
      Successful) return 0 ;;
      Failed|Cancelled)
        printf 'EKS update %s ended as %s\n' "$update_id" "$status" >&2
        return 1 ;;
      InProgress) sleep 10 ;;
      *) printf 'Unexpected EKS update status: %s\n' "$status" >&2; return 1 ;;
    esac
  done
  printf '%s\n' 'Update still pending; inspect it before another configuration change.' >&2
  return 1
}
```

**2. endpoint／logging 設定をレビューし、順番に適用します。** 次の例は API 経路を両方維持し、public 経路を承認 CIDR に制限します。private-only の代替を選ぶ前に Part 1 の説明に従って private routing／DNS／API access を別途確認してください。polling helper が timeout しても AWS update は取り消されません。別の変更を送信する前に状態を調べます。

EKS 1.36 では Secret を含む Kubernetes API data がすでに envelope encryption されています。customer-managed key 設定が空でも平文保存の証拠ではありません。この手順のために別クラスターや重複 KMS key を作成しないでください。CMK が必要なら、基本問題4のレビュー済み手順と key lifecycle の注意に従います。

```bash
# Keep both API paths; the supplied CIDR must include the intended administration path.
SECURITY_ENDPOINT_UPDATE=$(aws eks update-cluster-config \
  --name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --resources-vpc-config "endpointPublicAccess=true,endpointPrivateAccess=true,publicAccessCidrs=${APPROVED_API_CIDR:?}" \
  --query update.id --output text) || exit 1
security_wait_update "$SECURITY_ENDPOINT_UPDATE" || exit 1
kubectl --kubeconfig "${SECURITY_KUBECONFIG:?}" get nodes || exit 1

# EKS 1.36 already has default envelope encryption; inspect rather than create a new cluster.
aws eks describe-cluster --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --query 'cluster.{version:version,encryption:encryptionConfig}'

SECURITY_LOGGING_UPDATE=$(aws eks update-cluster-config \
  --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}' \
  --query update.id --output text) || exit 1
security_wait_update "$SECURITY_LOGGING_UPDATE" || exit 1
aws eks describe-cluster --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --query cluster.logging
```

control-plane log には CloudWatch 費用がかかり、配信は best effort です。意図した type が `/aws/eks/<cluster-name>/cluster` に実際に届くことを確認し、retention／access control を設定します。endpoint 制限は IAM／Kubernetes 認可を補うもので、置き換えるものではありません。

**3. 隔離された Restricted namespace と test workload を作ります。** 3つの Deployment は安定した VPC CNI policy test 用に controller 管理下 Pod を作ります。non-root user、RuntimeDefault seccomp、capability drop、read-only root filesystem、backend の一時 file 用 `emptyDir` を使います。ServiceAccount API token は不要です。

```bash
jq -n --arg ns "${SECURITY_NAMESPACE:?}" '{
  apiVersion:"v1",kind:"Namespace",metadata:{name:$ns,labels:{
    "pod-security.kubernetes.io/enforce":"restricted",
    "pod-security.kubernetes.io/enforce-version":"v1.36",
    "pod-security.kubernetes.io/audit":"restricted",
    "pod-security.kubernetes.io/audit-version":"v1.36",
    "pod-security.kubernetes.io/warn":"restricted",
    "pod-security.kubernetes.io/warn-version":"v1.36"
  }}
}' > "${SECURITY_LAB_DIR:?}/namespace.json" || exit 1
kubectl --kubeconfig "${SECURITY_KUBECONFIG:?}" \
  create -f "$SECURITY_LAB_DIR/namespace.json" || exit 1
SECURITY_NAMESPACE_UID=$(kubectl --kubeconfig "$SECURITY_KUBECONFIG" \
  get namespace "$SECURITY_NAMESPACE" -o jsonpath='{.metadata.uid}') || exit 1
: "${SECURITY_NAMESPACE_UID:?}"
jq -n --arg ns "$SECURITY_NAMESPACE" --arg uid "$SECURITY_NAMESPACE_UID" \
  '{namespace:$ns,uid:$uid}' > "$SECURITY_LAB_DIR/namespace-owner.json" || exit 1

jq -n --arg ns "$SECURITY_NAMESPACE" '
  def deployment($name;$command):
    {
      apiVersion:"apps/v1",kind:"Deployment",metadata:{name:$name,namespace:$ns},
      spec:{replicas:1,selector:{matchLabels:{app:$name}},template:{
        metadata:{labels:{app:$name}},
        spec:{
          nodeSelector:{"kubernetes.io/os":"linux"},
          automountServiceAccountToken:false,
          securityContext:{
            runAsNonRoot:true,runAsUser:1000,runAsGroup:1000,fsGroup:1000,
            seccompProfile:{type:"RuntimeDefault"}
          },
          volumes:[{name:"tmp",emptyDir:{}}],
          containers:[({
            name:"app",image:"busybox:1.37",command:$command,
            securityContext:{
              allowPrivilegeEscalation:false,readOnlyRootFilesystem:true,
              capabilities:{drop:["ALL"]}
            },
            volumeMounts:[{name:"tmp",mountPath:"/tmp"}],
            resources:{requests:{cpu:"50m",memory:"32Mi"},limits:{memory:"64Mi"}}
          } + if $name == "backend" then {
            ports:[{name:"http",containerPort:8080}],
            readinessProbe:{httpGet:{path:"/",port:8080}}
          } else {} end)]
        }
      }}
    };
  {
    apiVersion:"v1",kind:"List",items:[
      deployment("backend";["sh","-c","mkdir -p /tmp/www && printf \"policy-test-ok\\n\" > /tmp/www/index.html && exec httpd -f -p 8080 -h /tmp/www"]),
      deployment("frontend";["sleep","3600"]),
      deployment("outsider";["sleep","3600"]),
      {
        apiVersion:"v1",kind:"Service",metadata:{name:"backend",namespace:$ns},
        spec:{selector:{app:"backend"},ports:[{name:"http",port:8080,targetPort:8080}]}
      }
    ]
  }' > "$SECURITY_LAB_DIR/workloads.json" || exit 1
kubectl --kubeconfig "$SECURITY_KUBECONFIG" create -f "$SECURITY_LAB_DIR/workloads.json" || exit 1
for app in backend frontend outsider; do
  kubectl --kubeconfig "$SECURITY_KUBECONFIG" -n "$SECURITY_NAMESPACE" \
    rollout status "deployment/$app" --timeout=180s || exit 1
done

# Establish baseline connectivity before applying the policies.
kubectl --kubeconfig "$SECURITY_KUBECONFIG" -n "$SECURITY_NAMESPACE" \
  exec deployment/frontend -- wget -qO- -T 5 http://backend:8080/ || exit 1
kubectl --kubeconfig "$SECURITY_KUBECONFIG" -n "$SECURITY_NAMESPACE" \
  exec deployment/outsider -- wget -qO- -T 5 http://backend:8080/ || exit 1
```

policy 適用前に両方の client が backend に到達する必要があります。baseline 通信に失敗した場合は先に原因を直してください。失敗を network-policy enforcement の証拠にしないでください。

**4. default-deny と必要な allow rule を適用します。** これは生成した namespace に限定した、基本問題3と同じ policy 設計です。frontend から backend への TCP 8080 と一般的な CoreDNS 通信の UDP／TCP の両方を許可します。Service port と container port は一致しています。

```bash
cat > "${SECURITY_LAB_DIR:?}/networkpolicies.yaml" << EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: ${SECURITY_NAMESPACE:?}
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: backend-ingress
  namespace: ${SECURITY_NAMESPACE:?}
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes: [Ingress]
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: frontend
      ports:
        - protocol: TCP
          port: 8080
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: frontend-egress
  namespace: ${SECURITY_NAMESPACE:?}
spec:
  podSelector:
    matchLabels:
      app: frontend
  policyTypes: [Egress]
  egress:
    - to:
        - podSelector:
            matchLabels:
              app: backend
      ports:
        - protocol: TCP
          port: 8080
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: dns-egress
  namespace: ${SECURITY_NAMESPACE:?}
spec:
  podSelector: {}
  policyTypes: [Egress]
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
EOF
kubectl --kubeconfig "${SECURITY_KUBECONFIG:?}" apply -f "$SECURITY_LAB_DIR/networkpolicies.yaml" || exit 1
```

**5. 新しい接続と positive control を確認します。** policy が反映された後、無関係な client の拒否された request を観察し、次に許可された frontend request と DNS が引き続き動くことを確認します。この結果はこの test topology に限られます。予期しない失敗を判断する際は policy／agent status と log を調べます。

```bash
# Wait briefly for the expected denied fresh connection; do not treat baseline failures as success.
SECURITY_DENY_OBSERVED=false
for ((attempt=1; attempt<=6; attempt++)); do
  if kubectl --kubeconfig "${SECURITY_KUBECONFIG:?}" -n "${SECURITY_NAMESPACE:?}" \
    exec deployment/outsider -- wget -qO- -T 5 http://backend:8080/ >/dev/null 2>&1; then
    sleep 2
  else
    SECURITY_DENY_OBSERVED=true
    break
  fi
done
[ "$SECURITY_DENY_OBSERVED" = true ] || {
  printf '%s\n' 'Expected deny was not observed; inspect policy enforcement.' >&2
  exit 1
}

# Positive controls after the denial: allowed application traffic and DNS must still work.
kubectl --kubeconfig "$SECURITY_KUBECONFIG" -n "$SECURITY_NAMESPACE" \
  exec deployment/frontend -- wget -qO- -T 5 http://backend:8080/ || exit 1
kubectl --kubeconfig "$SECURITY_KUBECONFIG" -n "$SECURITY_NAMESPACE" \
  exec deployment/outsider -- nslookup backend || exit 1
kubectl --kubeconfig "$SECURITY_KUBECONFIG" -n "$SECURITY_NAMESPACE" get networkpolicies
```

PSA は namespace の Restricted standard を適用します。PSA を超える要件には Kyverno／Gatekeeper も使えますが任意です。基本問題6の現行 API を使い、ここで test するなら namespace selector を合わせます。この lab namespace の外に作った policy は、その workload に適用されません。

**6. 代替とせず、関連制御も確認します。** read-only の `Describe*` IAM policy では AWS Load Balancer Controller を動かせません。version に一致した公式 policy と、レビュー済み resource／tag condition を使ってください。node IAM、IMDS、security group、add-on identity を調べます。`maxUnavailable` は開始済み managed-node update の disruption を制御しますが、定期的な置換を予約しません。upgrade／保守計画は別途レビューします。

**7. lab namespace を削除します。** 記録した UID を使い、cleanup に失敗したら private ownership／設定 file を残します。

```bash
CURRENT_SECURITY_UID=$(kubectl --kubeconfig "${SECURITY_KUBECONFIG:?}" \
  get namespace "${SECURITY_NAMESPACE:?}" --ignore-not-found \
  -o jsonpath='{.metadata.uid}') || exit 1
if [ -z "$CURRENT_SECURITY_UID" ]; then
  printf '%s\n' 'Lab namespace is already absent.'
elif [ "$CURRENT_SECURITY_UID" = "${SECURITY_NAMESPACE_UID:?Recorded UID required}" ]; then
  kubectl --kubeconfig "$SECURITY_KUBECONFIG" delete namespace "$SECURITY_NAMESPACE" --wait=true
else
  printf '%s\n' 'Namespace UID mismatch; no deletion attempted.' >&2
  exit 1
fi
```

クラスターを残す場合は、最終 endpoint／logging 設定と継続する log retention／費用を確認します。training cluster を削除する場合は、クラスター lifecycle guide に従い、残った CloudWatch log と個別管理 resource を調べます。namespace cleanup として関連 KMS key を削除しないでください。

この監査では AWS update も Pod networking も実行していません。ローカル検査では生成 manifest、policy logic、失敗／cleanup guard を確認しました。本番の IAM、routing、admission、可用性、復旧は実環境で検証してください。

参考資料: [network-policy 要件](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html)、[既定の envelope encryption](https://docs.aws.amazon.com/eks/latest/userguide/envelope-encryption.html)、[API endpoint access](https://docs.aws.amazon.com/eks/latest/userguide/cluster-endpoint.html)、[control-plane log](https://docs.aws.amazon.com/eks/latest/userguide/control-plane-logs.html)、[Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/)。

</details>

## 発展的なトピック

次の問題では、Amazon EKS クラスター作成に関する高度な概念と実践を確認します。

1. EKS IPv6 クラスターの要件ではないものはどれですか？
   * A) IPv4 と IPv6 の両方を扱う VPC／subnet
   * B) 対応 CNI 設定と IPv6 用 IAM permission
   * C) 対応する Nitro-based EC2 node または Fargate
   * D) IPv6 専用の別 EC2 instance family

<details>
<summary>答えを表示</summary>

**答え: D) IPv6 専用の別 EC2 instance family**

EKS に「IPv6 専用 instance family」は必要ありません。ただし**対応する Nitro-based EC2 node または Fargate**が必要です。一般の EC2 instance type なら何でも動作するという説明も誤りです。

**前提条件:**

1. **新規**クラスター作成時に IPv6 IP family を選びます。これは変更できません。既存 IPv4 クラスターで `ENABLE_IPV6` を patch しても IPv6 クラスターには変換されません。
2. VPC／subnet に IPv4 と IPv6 CIDR を関連付け、node subnet で IPv6 auto-assignment を有効にします。IPv6 route、security group、DNS、管理接続を確認してください。subnet ID は意図した VPC／AZ のものを指定します。
3. IPv6 と prefix delegation を設定した対応 VPC CNI release を使います。1.10.1 は履歴上の最低 version であり、現在の推奨 install ではありません。古い 1.10 manifest を現行 managed add-on に適用しないでください。
4. CNI 用 IPv6 IAM permission を与え、可能なら専用 workload role に付与します。IPv4 用 `AmazonEKS_CNI_Policy` は IPv6 用 policy ではありません。eksctl の IPv6／add-on workflow が生成する role／policy を確認してください。

```bash
aws ec2 describe-subnets --region "${EXAMPLE_REGION:?}" \
  --subnet-ids "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" \
  --query 'Subnets[].{id:SubnetId,az:AvailabilityZone,ipv4:CidrBlock,ipv6:Ipv6CidrBlockAssociationSet,autoIPv6:AssignIpv6AddressOnCreation}'
aws eks describe-addon-versions --region "$EXAMPLE_REGION" \
  --addon-name vpc-cni --kubernetes-version 1.36
```

**例:** 既存の準備済み dual-stack private subnet と Nitro-based AL2023 node group を使います。例示 ID と public-access CIDR を置き換えてください。eksctl の `kubernetesNetworkConfig.ipFamily: IPv6` はこの表記で正しく、EKS API では小文字の `ipv6` です。

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: ipv6-lab
  region: us-west-2
  version: "1.36"
kubernetesNetworkConfig:
  ipFamily: IPv6
vpc:
  id: vpc-0123456789abcdef0
  subnets:
    private:
      us-west-2a:
        id: subnet-0123456789abcdef0
      us-west-2b:
        id: subnet-0123456789abcdef1
  clusterEndpoints:
    publicAccess: true
    privateAccess: true
  publicAccessCIDRs:
    - 203.0.113.10/32
iam:
  withOIDC: true
addons:
  - name: vpc-cni
  - name: coredns
  - name: kube-proxy
managedNodeGroups:
  - name: ipv6-ng
    amiFamily: AmazonLinux2023
    instanceType: m5.large
    privateNetworking: true
    desiredCapacity: 2
    minSize: 2
    maxSize: 4
```

レビューした設定を `ipv6-cluster.yaml` として保存します。環境に合う互換 add-on version を選び、記録してください。上記で version を省略すると tool が互換既定値を選びます。この例は、過去の特定 CNI build の install を推奨するものではありません。

```bash
# After reviewing real IDs, routing, IAM, access and compatible addon versions.
eksctl create cluster -f ipv6-cluster.yaml --kubeconfig "${EXAMPLE_KUBECONFIG:?}"
```

この設定だけでは既存 subnet の route／IPv6 attribute を準備しません。作成された access entry と CNI permission、node／add-on readiness も確認します。この監査では IPv6 クラスターを作成していません。

**address と traffic:**

- EKS は IPv6 Pod address を公開し、IPv6 ClusterIP を割り当てます。dual-stack VPC でも EKS Pod／Service が dual-stack になるわけではありません。
- Pod IPv6 address は subnet の範囲から割り当てます。Service の IPv6 address は EKS 割り当ての `fc00::/7` 内 unique-local range を使います。固定の `fd00::/108` service CIDR と決めつけないでください。
- EC2 node は IPv4／IPv6 address を持ちます。外部 IPv4 宛先へ接続するため、Pod に表示されない host-local IPv4 address が割り当てられ、node 経由で source NAT される場合もあります。private node から IPv4 internet へ出るには引き続き NAT が必要なことがあり、IPv6 ですべての NAT 依存がなくなるわけではありません。
- native IPv6 internet traffic は通信方向と security 設計に応じて internet gateway または egress-only internet gateway を使えます。すべての IPv6 cluster に egress-only gateway が必須ではありません。
- IPv6 Pod への load balancing には IP target 対応の controller／load balancer 設定が必要です。適切な dual-stack front end で IPv4 client access も提供できます。Pod address family と client の IP family を同一視しないでください。
- Windows と VPC CNI custom networking は EKS IPv6 cluster で非対応です。family 選択前に storage driver、add-on、外部依存の対応状況を確認します。

```bash
aws eks describe-cluster --name "${IPV6_CLUSTER_NAME:?}" \
  --region "${EXAMPLE_REGION:?}" --query cluster.kubernetesNetworkConfig
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" -n kube-system get pods -o wide
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n kube-system get services -o wide
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" get nodes -o wide
```

実際の address を確認し、DNS と必要な IPv6／IPv4 宛先をテストします。IPv6 address の一覧だけでは接続性や可用性を証明できません。記録した lab resource だけを cluster lifecycle 手順に従って削除します。

参考資料: [EKS IPv6 の動作](https://docs.aws.amazon.com/eks/latest/userguide/cni-ipv6.html)、[eksctl IPv6 tutorial](https://docs.aws.amazon.com/eks/latest/userguide/deploy-ipv6-cluster.html)、[CNI IAM role](https://docs.aws.amazon.com/eks/latest/userguide/cni-iam-role.html)、[network configuration response](https://docs.aws.amazon.com/eks/latest/APIReference/API_KubernetesNetworkConfigResponse.html)。

</details>

2. VPC CNI custom networking が主に可能にすることは何ですか？
   * A) node の primary interface と異なる Pod subnet／security group を、同一 VPC 内で使う
   * B) CIDR 重複を自動的にすべて防ぐ
   * C) node 間の全通信を暗号化する
   * D) control-plane reconciliation を高速化する

<details>
<summary>答えを表示</summary>

**答え: A) node の primary interface と異なる Pod subnet／security group を、同一 VPC 内で使う**

VPC CNI custom networking により、**Linux IPv4 EC2 Pod は node と同じ VPC 内の別 subnet／security group を使えます**。Pod range は VPC に関連付けられた CIDR の外にはなりません。secondary VPC CIDR で address space を増やすことはできますが、導入しただけで他 network との重複が解消するわけではありません。

既定では VPC CNI が node の primary subnet に secondary ENI を作成し、これらと primary ENI の eligible address から Pod IP を割り当てます。custom networking では通常の Pod IP は `ENIConfig` が指定する secondary ENI から取得し、primary ENI は Pod IP の割当てに使いません。host-network Pod は引き続き host network を使います。

**設定の順序:**

1. 空き IPv4 range、routing、permission を計画します。secondary CIDR を追加するなら VPC association 制限と接続 network との重複を確認します。AWS が使う `100.64.0.0/10` shared-space の例も自分の環境で未使用とは限りません。
2. 各 node の primary subnet と**同一 VPC／対応 AZ**に代替 Pod subnet を準備します。API／DNS／workload 依存を含む subnet route と SG ルールを確認します。
3. 対象 Pod subnet ごとに `ENIConfig` を作ります。次の例は AZ ごとに1 subnet を使うため、全 ID を置き換えてください。他 deployment が所有する cluster-scoped 設定を上書きしないでください。

```yaml
apiVersion: crd.k8s.amazonaws.com/v1alpha1
kind: ENIConfig
metadata:
  name: us-west-2a
spec:
  subnet: subnet-0123456789abcdef0
  securityGroups:
    - sg-0123456789abcdef0
---
apiVersion: crd.k8s.amazonaws.com/v1alpha1
kind: ENIConfig
metadata:
  name: us-west-2b
spec:
  subnet: subnet-0123456789abcdef1
  securityGroups:
    - sg-0123456789abcdef0
```

4. CNI installation の管理者に従って custom networking と ENIConfig の選択を設定します。EKS-managed add-on では、導入 version の schema を確認し、以下の環境設定をレビュー済み完全設定に merge します。

```yaml
# Merge with existing managed-addon configuration; do not discard other env values.
env:
  AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG: "true"
  ENI_CONFIG_LABEL_DEF: topology.kubernetes.io/zone
```

自己管理 DaemonSet なら同等の変更は次のとおりです。CNI の動作は cluster 全体に影響するため、気軽なアプリ deployment ではなく計画済み migration で行います。

```bash
# Self-managed CNI alternative, after preparing ENIConfig/subnets and a rollout plan.
# For an EKS-managed addon, use its supported configuration-values workflow instead.
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" -n kube-system \
  set env daemonset/aws-node AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG=true \
  ENI_CONFIG_LABEL_DEF=topology.kubernetes.io/zone
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n kube-system \
  rollout status daemonset/aws-node --timeout=5m
```

5. 必要な設定を持つ置換 node を準備・検証してから、PDB を考慮した drain とアプリケーション test で workload を移します。環境変数変更では既存 Pod の IP は変わりません。AWS は custom-networking 設定用の新しい node を推奨します。移行の確認まで旧 capacity を維持します。

`ENI_CONFIG_LABEL_DEF=topology.kubernetes.io/zone` の場合、各 `ENIConfig` 名をその AZ 名にします。同じ AZ に複数 Pod subnet があり別設定が必要なら、固有名とレビュー済みの custom node label／annotation mapping を使います。既存 ENIConfig annotation による選択は label-based selection を上書きできます。別 AZ の subnet を使わせるために Node の実際の topology label を変更しないでください。

**capacity と security の制約:**

- primary ENI を除くと secondary-IP mode での Pod capacity は減ります。prefix delegation で address 容量を増やせますが、subnet 内の prefix 空き、対応 instance limit、kubelet `maxPods` が関係します。一律値を流用せず密度を計算して test します。
- 既定の `AWS_VPC_K8S_CNI_EXTERNALSNAT=false` では、VPC に関連付けられた CIDR 外向き traffic は node の primary interface 経由で source NAT され、その subnet／security group が使われます。ENIConfig SG が外部向け全 flow を filter すると考えないでください。
- Security Groups for Pods と併用すると、その Pod の `SecurityGroupPolicy` SG が ENIConfig SG より優先されます。対応する enforcement／SNAT mode を確認します。
- custom networking だけでは暗号化にも tenant 隔離境界にもならず、適切な network 設計なしで CIDR 重複 routing を解決するものでもありません。
- EKS IPv6／Windows node では非対応です。Fargate は EC2 node の ENIConfig mapping ではなく、その profile で subnet を選択します。

```bash
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" get eniconfigs
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" get nodes -L topology.kubernetes.io/zone
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n "${APPLICATION_NAMESPACE:?}" get pods -o wide
aws ec2 describe-subnets --region "${EXAMPLE_REGION:?}" \
  --subnet-ids "${POD_SUBNET_A:?}" "${POD_SUBNET_B:?}" \
  --query 'Subnets[].{id:SubnetId,vpc:VpcId,az:AvailabilityZone,cidr:CidrBlock,free:AvailableIpAddressCount}'
```

Pod IP が意図した subnet、node AZ に属すること、DNS／API 接続と必要なアプリ flow を検証します。`ENIConfig` の一覧だけでは移行や隔離は証明できません。この例は静的にレビューしたもので、CNI 変更、node migration、network benchmark は実行していません。

参考資料: [custom networking](https://docs.aws.amazon.com/eks/latest/userguide/cni-custom-network.html)、[設定と移行](https://docs.aws.amazon.com/eks/latest/userguide/cni-custom-network-tutorial.html)、[custom networking の考慮点](https://docs.aws.amazon.com/eks/latest/best-practices/custom-networking.html)。

</details>

3. EKS で Windows workload を動かす要件ではないものはどれですか？
   * A) Amazon Linux managed node group が少なくとも2つ
   * B) Linux-only system Pod 用の Linux または Fargate capacity
   * C) 互換性のある Windows AMI と container image
   * D) Windows IPAM と正しい IAM／node authentication

<details>
<summary>答えを表示</summary>

**答え: A) Amazon Linux managed node group が少なくとも2つ**

Amazon Linux managed node group が2つ必要という要件はありません。**CoreDNS など Linux-only system Pod 用の Linux または Fargate capacity** は必要ですが、特定の Linux distribution や2つの別 group が必要なわけではありません。availability を考える場合は、最低要件と HA 設計を混同せず、replica と障害ドメインへの配置を計画します。

**Windows の前提:**

1. 現在サポートされる EKS **IPv4** cluster と、互換性のある EKS-optimized Windows AMI を使います。AWS は Windows Server 2019／2022／2025 variant を公開しています。この例は旧 Kubernetes 1.14／1.23 support baseline ではなく2022を使います。
2. cluster IAM role に `AmazonEKSVPCResourceController` permission があることを確認し、`kube-system/amazon-vpc-cni` 設定で Windows IPAM を有効にします。
3. Windows IPAM は managed VPC resource controller に任せます。floating `master` URL から旧 data-plane resource-controller／admission-webhook manifest を導入しないでください。
4. 専用 Windows node IAM role と正しい node authentication を使います。API authentication は `EC2_WINDOWS` access entry を使い、managed node group は node access entry を管理します。従来の `aws-auth` を使う場合は、bootstrap／node group に加えて必要な `eks:kube-proxy-windows` group を維持します。

```bash
aws iam list-attached-role-policies --role-name "${EKS_CLUSTER_ROLE_NAME:?}"

# If missing, attach to the reviewed cluster role, not to every worker role.
aws iam attach-role-policy --role-name "$EKS_CLUSTER_ROLE_NAME" \
  --policy-arn arn:aws:iam::aws:policy/AmazonEKSVPCResourceController
```

Windows IPAM の設定先は既存 VPC CNI 設定です。EKS または Helm が管理する場合、ConfigMap 全体を置き換えず、その管理元のサポート対象設定を使います。

```yaml
# Relevant ConfigMap data; merge through the owning addon/Helm configuration.
data:
  enable-windows-ipam: "true"
```

**Node group の例:** 既存 cluster、subnet、AMI availability、IAM を確認して `windows-nodegroup.yaml` として保存します。taint は通常の Linux workload が誤ってこの node に配置されるのを防ぎます。Linux workload template 側も Linux を明示的に選択してください。

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
  - name: windows-ng
    amiFamily: WindowsServer2022FullContainer
    instanceType: m5.large
    desiredCapacity: 2
    minSize: 2
    maxSize: 4
    privateNetworking: true
    taints:
      - key: example.com/os
        value: windows
        effect: NoSchedule
```

```bash
# Existing, supported IPv4 cluster with Windows IPAM and IAM prerequisites ready.
eksctl create nodegroup -f windows-nodegroup.yaml
aws eks describe-nodegroup --cluster-name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --nodegroup-name windows-ng \
  --query 'nodegroup.{status:status,ami:amiType,role:nodeRole,health:health}'
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" get nodes \
  -l kubernetes.io/os=windows -L node.kubernetes.io/windows-build
```

**workload の例:** 未使用の `windows-lab` namespace を作り、node の Windows build と互換の image を deploy します。EKS-optimized Windows AMI には kubelet、**Windows kube-proxy**、containerd などの host component が含まれます。kube-proxy は Linux 専用ではありません。

既存の ServiceMonitor entrypoint を持つ公式 IIS image を使います。古い `dotnetbinaries.blob.core.windows.net` ServiceMonitor download 元は廃止されています。この例で IIS を install して各 Pod 起動時に binary を download する必要はありません。

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: windows-iis
  namespace: windows-lab
spec:
  replicas: 2
  selector:
    matchLabels:
      app: windows-iis
  template:
    metadata:
      labels:
        app: windows-iis
    spec:
      os:
        name: windows
      nodeSelector:
        kubernetes.io/os: windows
        kubernetes.io/arch: amd64
        node.kubernetes.io/windows-build: "10.0.20348"
      tolerations:
        - key: example.com/os
          operator: Equal
          value: windows
          effect: NoSchedule
      containers:
        - name: iis
          image: mcr.microsoft.com/windows/servercore/iis:windowsservercore-ltsc2022
          ports:
            - containerPort: 80
          startupProbe:
            httpGet:
              path: /
              port: 80
            periodSeconds: 10
            failureThreshold: 60
          readinessProbe:
            httpGet:
              path: /
              port: 80
          resources:
            requests:
              cpu: 500m
              memory: 512Mi
            limits:
              memory: 1Gi
```

image tag は Microsoft image README と registry metadata で確認しました。この監査中に layer を download したり Windows workload を実行したりしていません。resource 値は説明用です。本番利用の前に実際の rollout／readiness、DNS、アプリ通信、host／container build の互換性を確認してください。

**対応機能の境界:**

- Windows は EKS Fargate Pod、EKS Auto Mode node、EKS Hybrid Node では動きません。EKS IPv6、VPC CNI custom networking、Security Groups for Pods も非対応です。
- 通常の Windows Pod は privileged Linux container と異なります。Windows **HostProcess** Pod は host networking を使えるため、「Windows は常に hostNetwork 非対応」という説明は誤りです。HostProcess は別途、高い security の審査が必要です。
- Windows の networking／IP capacity は Linux と異なります。Linux の Pod density 計算をそのまま使わず、単一 ENI 制限と対応 prefix delegation を確認してください。
- Windows 対応 storage driver を選び、volume／path の動作を検証します。Linux hostPath permission やすべての CSI 機能が移植可能とは限りません。
- EKS-optimized Windows node は containerd を使います。Linux application image は Linux node に配置してください。混在 OS cluster では system add-on とアプリの配置先を確認します。

参考資料: [EKS Windows support](https://docs.aws.amazon.com/eks/latest/userguide/windows-support.html)、[最適化済み Windows AMI](https://docs.aws.amazon.com/eks/latest/userguide/eks-optimized-windows-ami.html)、[Microsoft IIS image](https://github.com/microsoft/iis-docker)、[Windows HostProcess](https://kubernetes.io/docs/tasks/configure-pod-container/create-hostprocess-pod/)。

</details>



4. EC2 instance metadata request で session token を必須にする設定はどれですか？
   * A) HttpTokens=required (IMDSv2 のみ)
   * B) 169.254.169.254 向け security-group rule
   * C) Kubernetes Node label
   * D) ServiceAccount 名だけを設定する

<details>
<summary>答えを表示</summary>

**答え: A) HttpTokens=required (IMDSv2 のみ)**

IMDSv2 (`HttpTokens: required`) を必須にすると token なしの IMDSv1 call を無効にし、多層防御になります。ただし SSRF をすべて防ぐわけでも、host を共有する container 間の security boundary になるわけでもありません。

**launch-template 設定:** 次は EC2 `LaunchTemplateData` fragment であり、`managedNodeGroups.metadataOptions` field ではありません。hop limit 1 は通常の Pod が IRSA／Pod Identity を使い node credential を取得しない前提です。

```json
{
  "MetadataOptions": {
    "HttpTokens": "required",
    "HttpPutResponseHopLimit": 1,
    "HttpEndpoint": "enabled"
  }
}
```

hop limit は IMDS token の **PUT response** に適用され、metadata request すべてに適用されるわけではありません。IMDSv2 を正当に必要とする container では hop limit 2 が必要になる場合があります。互換性を確認してアプリ権限を workload role に移します。原因不明の失敗を隠す目的だけで limit を上げないでください。

既存のレビュー済み template version は、対応する eksctl `launchTemplate.id/version` field で指定します。次の example ID を置き換えてください。`--launch-template-name` は文書化された `eksctl create nodegroup` interface ではありません。

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
  - name: imds-template-ng
    launchTemplate:
      id: lt-0123456789abcdef0
      version: "1"
    privateNetworking: true
```

**eksctl の代替:** 新規 node group には対応する `disableIMDSv1` と `disablePodIMDS` field を使用できます。先に必要な workload identity を準備します。`disablePodIMDS` は host-network でない Pod を対象とし、`withAddonPolicies` と併用できません。

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
  - name: imds-restricted-ng
    amiFamily: AmazonLinux2023
    instanceType: m5.large
    privateNetworking: true
    desiredCapacity: 2
    minSize: 2
    maxSize: 4
    disableIMDSv1: true
    disablePodIMDS: true
```

2つの設定は代替案です。実際に生成された template と node metadata 設定を確認してください。既定値は instance launch setting、account／Region の既定値、AMI metadata 対応に依存し、launch setting が優先されます。すべての AMI／node group が hop limit 1 だと想定しないでください。

**既存 node:** 同じ custom launch template の新 version を managed node-group update で展開できます。個々の running／stopped EC2 instance の metadata option も IAM／SCP 制約の範囲で変更できますが、それだけでは将来の置換 node 設定は更新されません。

```bash
# Inspect the explicitly reviewed instance before changing its metadata settings.
aws ec2 describe-instances --region "${EXAMPLE_REGION:?}" \
  --instance-ids "${REVIEWED_INSTANCE_ID:?}" \
  --query 'Reservations[].Instances[].{id:InstanceId,tags:Tags,metadata:MetadataOptions}'

# Separate transition step for a tested instance with compatible host agents.
aws ec2 modify-instance-metadata-options --region "$EXAMPLE_REGION" \
  --instance-id "$REVIEWED_INSTANCE_ID" --http-tokens required \
  --http-put-response-hop-limit 1 --http-endpoint enabled
```

option が `applied` になったことと、node agent、image pull、workload credential が引き続き動くことを確認します。アプリが IRSA を使うからといって metadata endpoint 全体を無効にしないでください。host component が node instance profile／metadata に依存する場合があります。

**追加の制御:**

- node role の権限範囲を絞り、アプリケーションには個別 role を付与します。IRSA／Pod Identity だけでは node IMDS への別経路を防ぎません。
- `hostNetwork` Pod は IMDS に到達できます。また、十分な privilege を持つ host workload は Pod network isolation を迂回できます。Pod privilege と host access を別々に制御します。
- security group は instance の link-local metadata service を filter しません。追加の host／network 制限を設ける場合、実際の Pod 経路と任意の IPv6 IMDS endpoint (`fd00:ec2::254`)、IPv4 の両方を考慮します。場当たり的な `PREROUTING -i eth0` DNAT rule は一般的な Pod IMDS 制限として信頼できません。
- 対応 SDK を使い、session token や IAM credential 値を表示せず metadata access をテストします。Kubernetes label を enforcement の証拠とせず、実際の instance metadata option を観察します。

参考資料: [IMDS option と優先順位](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/configuring-instance-metadata-options.html)、[IMDSv2 の動作](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/configuring-instance-metadata-service.html)、[eksctl security option](https://docs.aws.amazon.com/eks/latest/eksctl/security.html)、[IRSA の隔離制限](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)。

</details>

5. EC2 node bootstrap 設定の目的ではないものはどれですか？
   * A) EKS 管理の control-plane process を変更する
   * B) custom AMI にすでに導入されたレビュー済み software を構成する
   * C) workload で検証済みの host 設定を適用する
   * D) 対応する node-group label／taint を設定する

<details>
<summary>答えを表示</summary>

**答え: A) EKS 管理の control-plane process を変更する**

node bootstrap が設定するのは**node host**であり、EKS が管理する API server、scheduler、controller manager、etcd ではありません。AL2023 では `nodeadm` と対応する eksctl／launch-template 経路を使います。旧 AL2 bootstrap.sh／`kubeletExtraArgs` の例は適用されません。

**software は意図的に導入・設定します。** 対象 OS／architecture 用の検証済み package を使い、できればレビュー済み AMI に組み込みます。毎回の起動時に未検証 `latest` RPM を download する方法では、再現性のある install になりません。host agent には適切な IAM permission と private／public service 接続も必要です。

以下の任意 AL2023 host 例は CloudWatch agent がすでに導入済みである前提です。host の memory／swap metric を設定して agent を起動します。AWS 接続が動く状態で実行すると料金対象の telemetry を送信します。管理用 workstation、Bottlerocket、Auto Mode で実行する手順ではありません。

```bash
#!/bin/bash
# AL2023 host example: the reviewed AMI must already contain the verified agent package.
set -euo pipefail
AGENT_CTL=/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl
test -x "$AGENT_CTL" || {
  printf '%s\n' 'CloudWatch agent is not installed in this AMI.' >&2
  exit 1
}
cat > /opt/aws/amazon-cloudwatch-agent/etc/cloudwatch-agent.json << 'EOF'
{
  "metrics": {
    "metrics_collected": {
      "mem": {"measurement": ["mem_used_percent"]},
      "swap": {"measurement": ["swap_used_percent"]}
    }
  }
}
EOF
"$AGENT_CTL" -a fetch-config -m ec2 \
  -c file:/opt/aws/amazon-cloudwatch-agent/etc/cloudwatch-agent.json -s
```

**kernel tuning:** workload の実測と実際の kernel／CNI 要件を基に検討します。元の値は未検証の tuning 例として残してあり、一般的な性能推奨値ではありません。

| 例の設定 | 元の例示値 | レビューする要件 |
| --- | --- | --- |
| `net.ipv4.ip_forward` | `1` | node／CNI の routing 要件 |
| `net.bridge.bridge-nf-call-iptables` | `1` | bridge module と CNI datapath が必要とするか |
| `net.ipv4.tcp_keepalive_time` | `600` | アプリ／接続の timeout 動作 |
| `net.ipv4.tcp_max_syn_backlog`、`net.core.somaxconn`、`net.core.netdev_max_backlog` | `40000` | 実際の queue 圧力、memory、workload の測定値 |
| `vm.max_map_count` | `262144` | 対象アプリ固有の mapping 要件 |

この表を全 node に一括適用する script として使わないでください。baseline を記録し、test group で変更を検証して rollback 手段を残します。

**disk:** `/dev/nvme1n1` と決めつけて `mkfs` を実行しないでください。NVMe の列挙順は安定した所有者 ID ではなく、必要な data を持つ可能性があります。volume ID／serial で対象 EBS volume を識別し、新規の使い捨て device または明示的に準備した device であることを確認してから、format 前に partition／filesystem／mount を調べます。永続 mount 設定では filesystem UUID など安定した識別子を使います。

```bash
# Read-only inspection on the specifically authorized test node.
lsblk --output NAME,PATH,TYPE,SIZE,FSTYPE,UUID,MOUNTPOINTS,SERIAL
findmnt
sysctl net.ipv4.ip_forward vm.max_map_count
```

永続アプリ data には、node の使い捨て disk と結びつけず、適切な CSI／PV lifecycle を優先してください。上記の検査 command は format も mount もしません。

**label、taint、security:** managed node-group の label／taint field と自分が管理する domain を使います。provider が所有する topology／node-group label は上書きしないでください。host hardening にはレビュー済み AMI と security-group／CNI 設計を使います。bootstrap 中に場当たり的な SSH／firewall 変更をすると既存 rule と競合したりアクセスを切断したりする可能性があり、完全な hardening 手順にはなりません。

**launch-template user data:** EKS 選択の AL2023 AMI を使い、custom `ImageId` を指定しなければ、必要な既定 NodeConfig は EKS が提供します。最小限の MIME customization は次のようになります。

```text
MIME-Version: 1.0
Content-Type: multipart/mixed; boundary="EKS_BOOTSTRAP_EXAMPLE"

--EKS_BOOTSTRAP_EXAMPLE
Content-Type: text/x-shellscript; charset="us-ascii"

#!/bin/bash
set -euo pipefail
install -d -m 0755 /opt/company

--EKS_BOOTSTRAP_EXAMPLE--
```

```bash
# Prepare real EC2 UserData JSON from the reviewed MIME file; no placeholder base64.
BOOTSTRAP_DIR=$(mktemp -d /tmp/eks-bootstrap-example.XXXXXX)
: "${BOOTSTRAP_DIR:?}"
jq -n --rawfile data "${REVIEWED_MIME_FILE:?}" \
  '{UserData:($data|@base64)}' > "$BOOTSTRAP_DIR/launch-template-data.json" || exit 1
aws ec2 create-launch-template --region "${EXAMPLE_REGION:?}" \
  --launch-template-name "${NEW_LAUNCH_TEMPLATE_NAME:?}" \
  --version-description "Reviewed AL2023 customization" \
  --launch-template-data "file://$BOOTSTRAP_DIR/launch-template-data.json" \
  --query 'LaunchTemplate.{id:LaunchTemplateId,version:LatestVersionNumber}'
```

返された template ID／version は、発展問題4と同様に `managedNodeGroups[].launchTemplate` から使用します。eksctl 生成設定の外で custom AMI ID を指定する場合、基本問題5にある完全な cluster NodeConfig も渡します。kubelet を手動で起動したり、`nodeadm init` を再実行したりしないでください。

**eksctl の別案:** 以下は対応する node-group field と、害のない directory 作成 pre-bootstrap command を使います。host customization はレビュー済みのものだけを追加します。`preBootstrapCommands` は shell command 用で、AL2023 の NodeConfig customization に `overrideBootstrapCommand` が必要な場合は NodeConfig YAML を入れます。

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
  - name: custom-ng
    amiFamily: AmazonLinux2023
    instanceType: m5.large
    privateNetworking: true
    desiredCapacity: 2
    minSize: 2
    maxSize: 5
    labels:
      example.com/environment: test
      example.com/node-type: compute
    taints:
      - key: dedicated
        value: compute
        effect: NoSchedule
    preBootstrapCommands:
      - install -d -m 0755 /opt/company
```

これらの例を本番 node recipe として起動していません。環境内で package provenance、実効 nodeadm／kubelet 設定、起動時失敗、networking、workload health を検証してください。

**CoreDNS は data-plane workload／add-on**であり、通常は Linux EC2 または対応 Fargate capacity 上で動く Deployment です。EKS が管理する control-plane process ではありません。add-on／Kubernetes workflow で設定します。logging など EKS control-plane API の公開設定は node user data とは別です。

参考資料: [AL2023 initialization](https://docs.aws.amazon.com/eks/latest/userguide/al2023.html)、[eksctl bootstrapping](https://docs.aws.amazon.com/eks/latest/eksctl/node-bootstrapping.html)、[launch-template 制約](https://docs.aws.amazon.com/eks/latest/userguide/launch-templates.html)、[CloudWatch agent 設定](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Agent-Configuration-File-Details.html)。

</details>
