# Amazon VPC CNI

> **レビュー基準**: VPC CNI / Helm chart 1.23.0、network policy agent 1.4.1。
> **最終更新**: October 12, 2026。
>
> **現在の EKS add-on リスト**: AWS は Kubernetes 1.31–1.37 向けに `v1.23.1-eksbuild.1` を掲載しています。
>
> **例の固定バージョン**: 以下の設定例では upstream/Helm 1.23.0 を使用します。Upstream、Helm、EKS の `eksbuild` バージョンは別個の識別子です。実際の cluster バージョンと Region で利用可能か確認してください。

## 目次

- [VPC CNI の概要](#vpc-cni-overview)
- [ネットワーキングモデル](#networking-model)
- [インストールと設定](#installation-and-configuration)
- [IP アドレス管理](#ip-address-management)
- [Network Policy サポート](#network-policy-support)
- [高度な機能](#advanced-features)
- [トラブルシューティング](#troubleshooting)
- [ベストプラクティス](#best-practices)

## VPC CNI の概要

Amazon VPC CNI は、標準の EKS EC2 node に VPC ネイティブな Pod ネットワーキングを提供します。このガイドの `aws-node` DaemonSet コマンドはそのインストールを対象としています。Auto Mode はマネージドネットワーキングコンポーネントを node service として実行します。Fargate と Windows は異なる管理経路を使用します。別の compute mode に EC2/Linux の手順を適用する前に、[概要](README.md)を参照してください。

Pod は overlay encapsulation を必要とせず、VPC でルーティング可能なアドレスを使用します。ルーティング、security group、network policy、ENI/IP 上限、およびアプリケーションの動作は、引き続き接続性とパフォーマンスを左右します。EKS は cluster 作成時に選択する **IPv4 または IPv6 の Pod/Service アドレッシング**をサポートします。dual-stack の Pod または Service はサポートしません。dual-stack VPC や IPv6 Pod の IPv4 egress helper は別の概念です。

### アーキテクチャ

| コンポーネント | 責務 |
|---|---|
| Container runtime / CNI binary | runtime は Pod sandbox に対して CNI を呼び出します。AWS plugin はアドレスを要求し、その network namespace を設定します。 |
| IPAMD | Linux EC2 node 上のアドレスプールを維持し、必要な通常の ENI/IP を管理します。 |
| EKS network policy controller / node agent | マネージド controller は policy endpoint を解決します。有効化されている場合、`aws-eks-nodeagent` は eBPF を使用してサポート対象の policy を適用します。 |
| VPC resource controller | branch/trunk interface や Windows アドレス割り当てなどの機能を、それぞれの前提条件の下で管理します。 |

以前の図では、CNI binary が kubelet から直接呼び出されるものとして示されていました。現在の Kubernetes は、CNI 管理を container runtime に委譲します。

### IP 割り当てモード

| プロパティ | Secondary IPv4 address | Prefix delegation |
|---|---|---|
| 割り当て | ENI 上の個別の secondary address | 16 個のアドレスを持つ IPv4 `/28` prefix。IPv6 は `/80` prefix を使用 |
| 容量 | interface/address slot と kubelet 設定により制約される | サポート対象ハードウェア、空き prefix、kubelet/resource 上限に従い、slot あたりのアドレス数が多い |
| 割り当てのトレードオフ | きめ細かいアドレス割り当て | ブロックを一度に割り当てる。warm target は未使用アドレスを予約することがある |
| 選択 | 互換性と測定済み需要に応じて使用 | Nitro サポート、subnet fragmentation、workload churn、機能の組み合わせを確認 |

Prefix delegation は大規模 cluster の普遍的な要件ではなく、枯渇した subnet にアドレス空間を生成するものでもありません。

## ネットワーキングモデル

### ENI アーキテクチャ

通常の secondary-IPv4 モードでは、各 ENI は primary address と、CNI が利用できる追加アドレスを持ちます。primary ENI は node の primary address も担います。追加 ENI はさらに多くの secondary Pod address を供給できます。custom networking は Pod address を供給する interface/subnet を変更します。prefix モードと branch-ENI モードには異なる割り当て規則があります。

```text
Linux EC2 node — ordinary secondary-IPv4 illustration
├── Primary ENI: node primary IP + secondary IPs for Pods
├── Additional ENI: its primary IP + secondary IPs for Pods
└── Additional ENI: its primary IP + secondary IPs for Pods
```

### Instance Type ENI/IP 上限

| Instance type | 最大 ENI 数 | ENI あたりの IPv4 slot | 旧来の secondary-IP bootstrap maxPods |
|---|---|---|---|
| t3.medium | 3 | 6 | 17 |
| t3.large | 3 | 12 | 35 |
| m5.large | 3 | 10 | 29 |
| m5.xlarge | 4 | 15 | 58 |
| m5.2xlarge | 4 | 15 | 58 |
| c5.4xlarge | 8 | 30 | 234 |
| m5.8xlarge | 8 | 30 | 234 |

歴史的な計算式は **`ENIs × (IPv4 slots per ENI − 1) + 2`** です。`+2` は、この bootstrap 計算における 2 つの host-network system Pod を表します。m5.large の場合、`3 × 9 + 2 = 29` です。これは、すべての現在の Deployment が常に host-network Pod を正確に 2 つ持つことを意味するものではありません。

これらは旧来の bootstrap 値であり、現在の普遍的な Pod density の推奨値ではありません。Prefix delegation、custom networking、branch interface、複数 network card、CPU/memory、kubelet の `maxPods` はすべて重要です。EKS managed node group は、30 vCPU 未満の instance では `maxPods` を 110 に、それ以外では 250 に制限します。実際の node の allocatable capacity を確認してください。

### Prefix Delegation

Linux IPv4 prefix モード向けの EKS managed add-on 設定フラグメントは次のとおりです。

```json
{
  "env": {
    "ENABLE_PREFIX_DELEGATION": "true",
    "WARM_PREFIX_TARGET": "1"
  }
}
```

これを、以下の管理手順を使用して、意図した add-on 設定とマージします。Helm が所有するインストールでは、同等の `env` mapping は Helm values に含めます。直接の `kubectl set env` 編集は、選択した manager により再調整される可能性があります。

IPv4 の割り当てには、単に `AvailableIpAddressCount` が正であるだけでなく、適切な連続した `/28` block が必要です。subnet reservation/fragmentation とサポート対象 Nitro instance を確認してください。prefix を有効にしても、既存のすべての kubelet の Pod 上限が自動的に上がることや、branch-ENI Pod 上限が増えることはありません。

## インストールと設定

### 所有権と互換性の確立

対象 cluster 用に設定済みの AWS CLI credentials と Kubernetes context を使用します。まず読み取りから始めます。

```bash
EKS_REGION=ap-northeast-2
CLUSTER_NAME=my-cluster
KUBERNETES_MINOR="$(aws eks describe-cluster --region "$EKS_REGION" \
  --name "$CLUSTER_NAME" --query cluster.version --output text)"
aws eks describe-addon-versions --region "$EKS_REGION" \
  --addon-name vpc-cni --kubernetes-version "$KUBERNETES_MINOR"
aws eks describe-addon --region "$EKS_REGION" \
  --cluster-name "$CLUSTER_NAME" --addon-name vpc-cni
kubectl -n kube-system get daemonset aws-node -o yaml
```

`describe-addon` に対する EKS の `ResourceNotFoundException` は、CNI がインストールされていないことの証明にはなりません。self-managed である可能性があります。**1 つ**の manager を選択する前に、既存の DaemonSet、ServiceAccount、Helm release、設定、および IAM model を確認してください。Auto Mode networking はこの workflow ではインストールされません。

### 既存の EKS Managed Add-on

既存設定を export し、選択した互換 build の schema を確認します。

```bash
umask 077
aws eks describe-addon --region "$EKS_REGION" \
  --cluster-name "$CLUSTER_NAME" --addon-name vpc-cni > vpc-cni-before.json
jq -r '.addon.configurationValues // "{}"' vpc-cni-before.json > vpc-cni-config.json
: "${VPC_CNI_ADDON_VERSION:?Select a compatible EKS add-on build from the metadata}"
aws eks describe-addon-configuration --region "$EKS_REGION" \
  --addon-name vpc-cni --addon-version "$VPC_CNI_ADDON_VERSION"
```

必要な中間 upgrade version と release change を確認してください。`vpc-cni-config.json` を編集して、意図した既存設定を保持し、選択した変更だけを組み込みます。部分的な payload や conflict flag が、すべての設定を自動的に保持すると仮定しないでください。CNI の IAM permission と、設定されている IRSA/Pod Identity role を確認してください。IPv6 には対応する permission が必要です。

すでに managed である add-on には、レビュー済みの update として次を使用できます。

```bash
set -eu
VPC_CNI_UPDATE_ID="$(aws eks update-addon --region "$EKS_REGION" \
  --cluster-name "$CLUSTER_NAME" --addon-name vpc-cni \
  --addon-version "$VPC_CNI_ADDON_VERSION" \
  --configuration-values file://vpc-cni-config.json --resolve-conflicts PRESERVE \
  --query update.id --output text)"
aws eks describe-update --region "$EKS_REGION" --name "$CLUSTER_NAME" \
  --addon-name vpc-cni --update-id "$VPC_CNI_UPDATE_ID"
```

`PRESERVE` は明示的な conflict-handling の選択です。結果として得られる environment、image、動作を確認してください。捕捉した update ID を、その status が `Successful` になるまで再確認します。`Failed` または `Cancelled` の場合は、続行する前に error を確認してください。その後にのみ、結果の add-on と DaemonSet を確認します。

```bash
aws eks describe-addon --region "$EKS_REGION" \
  --cluster-name "$CLUSTER_NAME" --addon-name vpc-cni
kubectl -n kube-system rollout status daemonset/aws-node --timeout=10m
```

受け付けられた API request や以前の DaemonSet の ready state は、この update と network validation が完了した証拠にはなりません。

インストール/所有権準備後に managed add-on が存在しない場合、create operation は別です。

```bash
aws eks create-addon --region "$EKS_REGION" \
  --cluster-name "$CLUSTER_NAME" --addon-name vpc-cni \
  --addon-version "$VPC_CNI_ADDON_VERSION" \
  --configuration-values file://vpc-cni-config.json
```

個別機能を有効にするために `create-addon` を繰り返し呼び出さないでください。また、migration plan なしに、既存のカスタマイズ済みインストールを `OVERWRITE` で強制的に上書きしないでください。

### Helm 所有のインストール

chart 全体を固定します。これにより、対応する init と policy-agent component も選択されます。2 つの image tag だけを上書きしても、chart の残りは更新されません。

```bash
helm repo add eks https://aws.github.io/eks-charts
helm repo update eks
helm show values eks/aws-vpc-cni --version 1.23.0 > chart-defaults.yaml
helm template aws-vpc-cni eks/aws-vpc-cni --namespace kube-system \
  --version 1.23.0 -f helm-values.yaml > rendered-cni.yaml
```

実際の IP family、CNI ServiceAccount/IAM、および選択した機能に合わせて `helm-values.yaml` を準備します。このガイドの基本的な Linux 例では IPv4 を使用します。適用前に render 済み resource を確認してください。

```bash
helm upgrade --install aws-vpc-cni eks/aws-vpc-cni --namespace kube-system \
  --version 1.23.0 -f helm-values.yaml --wait --timeout 10m
```

これらのコマンドは、クリーンなインストールまたは Helm 所有のインストールを前提としています。既存の EKS-managed または bootstrap-owned resource には、計画された ownership migration が必要です。EKS partition/registry access と image-pull の前提条件も環境に適合する必要があります。

### 重要な設定値

| 設定 | 意味 | ベースライン/デフォルトの区別 |
|---|---|---|
| `WARM_IP_TARGET` | 新しい通常 Pod 割り当てに対する、望ましい空きアドレス数 | デフォルトでは未設定。ハードな最大値ではない |
| `MINIMUM_IP_TARGET` | 割り当て済みアドレス総数の下限 | デフォルトでは未設定。使用時は正の warm-IP target と組み合わせる |
| `WARM_ENI_TARGET` | 望ましい warm ENI capacity | リリース済みデフォルト: 1。IP target がこれを上書きする |
| `WARM_PREFIX_TARGET` | 望ましい空き IPv4 prefix 数 | リリース済み chart/manifest は 1 を設定。bare daemon documentation では未設定 |
| `ENABLE_PREFIX_DELEGATION` | prefix allocation を選択 | Linux chart デフォルト: `"false"` |
| `AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG` | custom-networking behavior を選択 | デフォルト: `"false"` |
| `ENI_CONFIG_LABEL_DEF` | ENIConfig を選択する node label key | Daemon デフォルト: `k8s.amazonaws.com/eniConfig`。zone-based 例ではこれを上書きする |
| `ENABLE_POD_ENI` | EC2 Pod-ENI integration を有効化 | デフォルト: `"false"`。その他の SGPP 前提条件は引き続き適用される |
| `POD_SECURITY_GROUP_ENFORCING_MODE` | SGPP routing/SNAT/security-group behavior | デフォルト: `strict` |
| `NETWORK_POLICY_ENFORCING_MODE` | 新しい Pod の rule を設定中の network-policy behavior | デフォルト: `standard` |

2 つの enforcing-mode 設定は異なる system を制御します。EKS 設定 payload の environment value は string です。

### Custom Networking (ENIConfig)

対象の VPC/AZ に実際の Pod subnet と security group を作成してから、その ID を参照します。

```yaml
apiVersion: crd.k8s.amazonaws.com/v1alpha1
kind: ENIConfig
metadata:
  name: ap-northeast-2a
spec:
  subnet: subnet-0123456789abcdef0
  securityGroups:
  - sg-0123456789abcdef0
---
apiVersion: crd.k8s.amazonaws.com/v1alpha1
kind: ENIConfig
metadata:
  name: ap-northeast-2b
spec:
  subnet: subnet-0abcdef0123456789
  securityGroups:
  - sg-0123456789abcdef0
```

custom networking を有効にし、node の実際の zone label を使用します。

```json
{
  "env": {
    "AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG": "true",
    "ENI_CONFIG_LABEL_DEF": "topology.kubernetes.io/zone"
  }
}
```

明示的な ENIConfig node annotation は label より優先されます。ENIConfig object だけでは custom networking は有効になりません。routing、DNS/security rule、address capacity、workload/node transition を計画してください。新しい CIDR または ENIConfig が存在するだけでは、現在の Pod は新しい subnet に移動しません。

## IP アドレス管理

### Warm-pool Tuning

測定済みの Pod demand と churn、利用可能な address space、EC2 API limit を使用します。これらは cluster size だけに基づく処方ではなく、代替となる example target です。

```json
{
  "env": {
    "WARM_IP_TARGET": "2",
    "MINIMUM_IP_TARGET": "4"
  }
}
```

```json
{
  "env": {
    "WARM_IP_TARGET": "5",
    "MINIMUM_IP_TARGET": "10"
  }
}
```

`MINIMUM_IP_TARGET` は総割り当て量の下限です。`WARM_IP_TARGET` は空きアドレスを対象とします。これらは ENI/prefix warm-target strategy より優先されます。prefix delegation では、割り当ては引き続き prefix サイズ単位で行われます。warm capacity を増やすと割り当て待ちを減らせますが、アドレスを消費し、積極的な変更は API call を増やす可能性があります。

### Secondary CIDR の追加

まず既存の association、接続済み network との overlap、VPC CIDR restriction、および subnet/routing requirement を確認します。

```bash
VPC_ID=vpc-0123456789abcdef0
aws ec2 describe-vpcs --region "$EKS_REGION" --vpc-ids "$VPC_ID" \
  --query 'Vpcs[0].CidrBlockAssociationSet'
```

次では例示的な ID と address space を使用しています。レビュー済みの VPC plan の一部としてのみ実行してください。

```bash
aws ec2 associate-vpc-cidr-block --region "$EKS_REGION" \
  --vpc-id "$VPC_ID" --cidr-block 100.64.0.0/16
aws ec2 describe-vpcs --region "$EKS_REGION" --vpc-ids "$VPC_ID" \
  --query 'Vpcs[0].CidrBlockAssociationSet'
```

その CIDR 内に subnet を作成する前に、新しい CIDR association がまだ associating 中ではなく **associated** であることを確認します。

```bash
aws ec2 create-subnet --region "$EKS_REGION" --vpc-id "$VPC_ID" \
  --cidr-block 100.64.0.0/19 --availability-zone ap-northeast-2a
```

subnet には、意図した route table、security rule、CNI selection も必要です。既存の Pod は、計画された transition まで現在の networking を維持します。RFC 6598 の `100.64.0.0/10` は共有アドレス空間であり、グローバルに一意な private capacity ではありません。接続されるすべての環境との overlap を確認してください。

### IPv6 Cluster Configuration

IP family は cluster 作成時に選択し、その後は変更できません。公式の `eksctl` interface は `--ip-family` flag ではなく、**configuration file** を使用します。schema の例は次のとおりです。

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: ipv6-example
  region: ap-northeast-2
  version: '1.35'
kubernetesNetworkConfig:
  ipFamily: IPv6
iam:
  withOIDC: true
addons:
- name: vpc-cni
- name: coredns
- name: kube-proxy
managedNodeGroups:
- name: linux-nitro
  amiFamily: AmazonLinux2023
  instanceType: m5.large
  desiredCapacity: 2
  privateNetworking: true
```

例の version/Region を置き換え、サポート対象の node image を選択し、作成前に VPC endpoint/access と IAM 設定を確認してください。ここで省略した add-on version は、サポート対象の EKS/eksctl path を通じて解決されます。制御された Deployment のために、必要な互換 build を確認して固定してください。`iam.withOIDC` と managed add-on/node group は、文書化された eksctl IPv6 prerequisite を反映しています。

```bash
eksctl create cluster --config-file ipv6-cluster.yaml
```

この監査では cluster を作成していません。ローカル CLI の help/schema check では eksctl 0.229.0 を使用しました。これらは networking、IAM、または Region で利用可能な build のライブ検証ではありません。

IPv6 にはサポート対象の Linux Nitro/Fargate path と prefix allocation が必要です。Windows はサポートされません。IPv6 Pod は egress-only IPv4 helper interface を持つ場合があります。policy agent の documentation では、primary interface 上の IPv6 policy は、その helper の IPv4 traffic を保護しないと説明されています。設計でその path を削除する必要がある場合は、IPv6 policy だけでブロックされると仮定せず、`ENABLE_V4_EGRESS`、dependency、Pod rollout を確認してください。

## Network Policy サポート

### Native Enforcement

標準の native eBPF policy support は VPC CNI 1.14 で導入されました。現在の EKS documentation では、標準の `NetworkPolicy` と Admin `ClusterNetworkPolicy` の両方に VPC CNI 1.21.0 以降を挙げています（[EKS network policy requirements](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html)）。レビュー済みの 1.23 baseline は、引き続き cluster と platform に適合させる必要があります。

```json
{
  "enableNetworkPolicy": "true"
}
```

`"enableNetworkPolicy": "true"` は文書化された string-valued configuration です。サポート対象の EC2 Linux node はこの implementation を使用できます。Fargate と Windows はその enforcement を使用しません。Auto Mode には独自の managed implementation があります。EKS の `ClusterNetworkPolicy` Admin/Baseline control と Auto Mode DNS の `ApplicationNetworkPolicy` は、標準の `NetworkPolicy` の別名ではなく extension です。

standard mode では、new Pod は policy rule が解決される間、最初は traffic を許可します。より厳格な startup behavior を意図的に選択できます。

```json
{
  "enableNetworkPolicy": "true",
  "env": {
    "NETWORK_POLICY_ENFORCING_MODE": "strict"
  }
}
```

strict mode では、workload の開始前に DNS やその他の必要な traffic を正しく policy でカバーする必要があります。SGPP の別個の `POD_SECURITY_GROUP_ENFORCING_MODE` を設定するものではありません。

### NetworkPolicy の例

前提条件: `app` namespace には controller-managed frontend/backend workload が含まれ、backend Pod は TCP 8080 で listen しています。AWS は現在、信頼できる enforcement には `metadata.ownerReferences` が重要であると文書化しており、Service/container port number の一致（named port では name の一致も）を要求しています。

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
  namespace: app
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 8080
```

source Pod selector は同じ namespace に限定されます。この rule は、選択した backend ingress を分離し、matching frontend traffic の 8080 への接続を許可します。backend egress を拒否するものでも、application user を認証するものでもありません。他の matching policy と Admin-tier behavior を考慮してください。standalone diagnostic Pod に頼らず、Deployment/Job-managed Pod を使用して許可および拒否の両方の flow を検証してください。

### 検証と診断

```bash
kubectl -n kube-system logs -l k8s-app=aws-node -c aws-eks-nodeagent --tail=200
kubectl get networkpolicy -A
kubectl get policyendpoints.networking.k8s.aws -A
```

これらは **node-agent** log です。policy controller は EKS-managed control plane で実行されます。PolicyEndpoint object は生成された state であり、気軽に edit/delete する object ではありません。

インストール済み policy CLI を持つ、許可された Linux node で次を実行します。

```bash
sudo /opt/cni/bin/aws-eks-na-cli ebpf progs
sudo /opt/cni/bin/aws-eks-na-cli ebpf maps
```

この tool は `aws-eks-na-cli` であり、`ebpf-sdk list-maps` ではありません。affected node を確認し、process log を設定済みの policy-event log や CloudWatch delivery と区別してください。外部 log delivery を有効にするには、適切な IAM/configuration も必要です。

## 高度な機能

### Pod の Security Group

選択した security group は、適切な DNS、API、application、return-path rule を持ってあらかじめ存在している必要があります。

```yaml
apiVersion: vpcresources.k8s.aws/v1beta1
kind: SecurityGroupPolicy
metadata:
  name: my-security-group-policy
  namespace: app
spec:
  podSelector:
    matchLabels:
      app: database
  securityGroups:
    groupIds:
    - sg-0123456789abcdef0
    - sg-0abcdef0123456789
```

standard SGPP behavior を選択する **EC2** 設定の例は次のとおりです。

```json
{
  "env": {
    "ENABLE_POD_ENI": "true",
    "POD_SECURITY_GROUP_ENFORCING_MODE": "standard"
  }
}
```

これは完全な SGPP installation ではありません。サポート対象の trunking instance type、cluster role の VPC resource-controller permission、CNI permission、subnet capacity、および該当する EKS prerequisite を確認してください。T-family instance は Nitro-based であるだけでは trunking をサポートしません。新規作成/再作成された選択対象 Pod は、意図した setup を受け取ります。

managed resource controller は **追加の trunk ENI** を attach し、それに branch ENI を関連付けます。trunk は node の primary `eth0` ENI ではありません。選択対象 Pod は security group を持つ branch interface を使用します。prefix delegation は branch-Pod 上限を増やしません。Fargate security group は別個の managed path を使用します。

| モード / 機能 | 確認する結果 |
|---|---|
| SGPP `strict` | Branch security-group behavior と Pod source NAT なし。NodeLocal DNSCache および `externalTrafficPolicy: Local` を持つ instance-target LoadBalancer/NodePort には文書化された制限がある |
| SGPP `standard` | 文書化された combined policy/DNS path をサポート。デフォルトの external-SNAT behavior では、VPC 外向け traffic は node primary address/security group を使用する |
| Custom networking と SGPP | Pod security group は ENIConfig security group より優先される |
| IPv6 | EC2 CNI 1.16+ を含む version/platform condition の下で EKS service guide がサポート。古い README feature-table の「No」cell はこの詳細な guidance を上書きしてはならない |
| Windows / Auto Mode | この SGPP mechanism はサポートされない。Auto Mode には別個の node-class networking control がある |

mode の変更は新たに launch された Pod に影響します。再作成を計画し、traffic path を検証してください。SNAT 後に同じ security group がすべての packet を制御すると仮定しないでください。

### Multiple Interface と Multus

VPC CNI 1.20+ は、複数の network card を持つ適切な instance 向けに native multi-NIC support を備えています。その `ENABLE_MULTI_NIC` と Pod NIC configuration は Multus とは別物であり、application は利点を得るために追加 interface を使用する必要があります。

Multus は meta-plugin です。AWS がサポートする Multus arrangement では、VPC CNI を **primary delegate** として使用します。高次の interface に VPC CNI を使用することはサポートされません。追加 interface には、それぞれ互換性のある plugin、address assignment、lifecycle management が必要です。

| 追加 interface の要件 | 重要な理由 |
|---|---|
| 専用で識別された interface | hard-coded の `eth1` は IPAMD が管理する interface を指す場合がある |
| 追加 ENI に対する `node.k8s.amazonaws.com/no_manage=true` | VPC CNI が Multus interface を管理するのを防ぐ |
| AWS 割り当て/ルーティング可能な address と正しい subnet/SG/route | 任意の `192.168.1.0/24` 割り当ては、EC2 ENI 上で自動的に有効になるわけではない |
| 協調された IPAM | 共有の `host-local` range は異なる node で重複を割り当てる可能性がある |
| Interface 固有の policy test | extra interface と IPv4 helper path は、すべての primary-interface policy に自動的にカバーされるわけではない |

NetworkAttachmentDefinition の `spec.config` には、サポート対象 version、plugin、実際の parent interface、IPAM configuration を含む、選択された CNI JSON が入ります。以前の汎用的な `ipvlan`/`eth1`/`host-local` manifest は上記の前提条件を省略しており、これらの implementation requirement に置き換えられました。このガイドは、デプロイ済みの Multus/IPAM solution を主張するものではありません。

### Windows

Windows は VPC resource-controller IPAM path を使用します。cluster role permission、Windows node-role authentication/access entry（該当する場合は `EC2_WINDOWS`）、および CoreDNS 用 Linux/Fargate capacity を準備してください。Windows Fargate、Auto Mode、Hybrid Nodes、IPv6、custom networking、SGPP、native VPC-CNI network policy には文書化された制限があります。

controller の結果の ConfigMap には、次の Windows IPAM entry を含める必要があります。これは必要な data を示すものであり、manager-owned ConfigMap を上書きする指示ではありません。

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: amazon-vpc-cni
  namespace: kube-system
data:
  enable-windows-ipam: 'true'
```

**Helm 所有の**インストールでは、Windows prefix target は Linux と異なる key を使用します。

```yaml
enableWindowsIpam: 'true'
enableWindowsPrefixDelegation: 'true'
warmWindowsPrefixTarget: 1
warmWindowsIPTarget: 0
minimumWindowsIPTarget: 0
```

対応する build の schema、field ownership、結果の ConfigMap を確認してください。Helm value が EKS add-on configuration property として変更なしに受け入れられると仮定しないでください。Windows chart flag は `enable-windows-ipam` と `enable-windows-prefix-delegation` に map されます。ここでの warm-target field も Windows 固有です。

これらの prerequisite と AMI/version check の後、node-group command には次を使用できます。

```bash
eksctl create nodegroup --region "$EKS_REGION" --cluster "$CLUSTER_NAME" \
  --name windows-example --managed --node-type m5.large --nodes 2 \
  --node-ami-family WindowsServer2022FullContainer
```

Windows secondary-IP mode は通常、Linux multi-ENI formula ではなく、1 つの ENI とその address-slot limit を使用します。prefix delegation と実際の kubelet limit には個別の sizing が必要です。

## トラブルシューティング

### IP 割り当てと Scheduling

Pod event を確認し、scheduling failure と sandbox/CNI allocation failure を区別します。

```bash
kubectl -n kube-system logs -l k8s-app=aws-node -c aws-node --tail=300
kubectl get nodes -o json | jq '.items[] | {name: .metadata.name, allocatablePods: .status.allocatable.pods}'
SUBNET_ID=subnet-0123456789abcdef0
aws ec2 describe-subnets --region "$EKS_REGION" --subnet-ids "$SUBNET_ID" \
  --query 'Subnets[].{SubnetId:SubnetId,AvailableIPs:AvailableIpAddressCount}'
```

`allocatablePods` は kubelet の scheduling capacity であり、現在の IP utilization ではありません。subnet の available-address count は、連続した `/28` が利用可能かを示しません。対策を選択する前に、IPAMD log、allocation mode、warm target、ENI limit、API error、affected node を確認してください。

### ENI 数

```bash
INSTANCE_ID=i-0123456789abcdef0
aws ec2 describe-instances --region "$EKS_REGION" --instance-ids "$INSTANCE_ID" \
  --query 'Reservations[].Instances[].{InstanceId:InstanceId,AttachedENIs:length(NetworkInterfaces)}'
aws ec2 describe-instance-types --region "$EKS_REGION" --instance-types m5.large \
  --query 'InstanceTypes[].NetworkInfo.{MaxENI:MaximumNetworkInterfaces,IPv4PerENI:Ipv4AddressesPerInterface}'
```

元の projection は interface 自体ではなく、interface の nested list を数えていました。修正した query は instance ごとの count を報告します。複数の card、unmanaged/trunk interface、instance 固有の limit は、引き続き解釈が必要です。

### Introspection と Metrics

affected node の実際の `aws-node` Pod を選択し、この forwarding session を開いたままにします。

```bash
kubectl -n kube-system get pods -l k8s-app=aws-node -o wide
AWS_NODE_POD=aws-node-example
kubectl -n kube-system port-forward "pod/$AWS_NODE_POD" 61678:61678 61679:61679
```

別のローカル terminal から実行します。

```bash
curl --fail http://127.0.0.1:61679/v1/enis
curl --fail http://127.0.0.1:61678/metrics
```

IPAMD introspection のデフォルトは loopback **61679**、Prometheus metrics は **61678** を使用します。`/v1/enis` は metrics endpoint ではありません。これらのコマンドは Kubernetes forwarding path を通じてローカル curl を使用します。CNI image 内に curl binary は必要ありません。

### Cluster を変更する前の Error の分類

| 観測 | 操作前に調査すること |
|---|---|
| `InsufficientFreeAddressesInSubnet` | 実際の空きアドレス、warm allocation、選択された subnet、計画された capacity expansion |
| `InsufficientCidrBlocks` | 連続 prefix の可用性/fragmentation と subnet reservation |
| ENI/SG limit error | 特定の quota、instance/interface type、使用中の object。無関係な security group を削除しないこと |
| ENI creation failure | 詳細な AWS error、CNI credential role、permission/condition、quota、API connectivity |
| Pod IP の待機 | IPAMD state、controller/API delay、throttling、sandbox event、address readiness |

IPAMD の restart、instance の拡大、node-role permission の追加は普遍的な対策ではありません。まず evidence を収集し、実際に失敗している operation を所有する component にレビュー済みの変更を適用してください。

## ベストプラクティス

期待される Pod、warm pool、成長、failure/replacement の重複から subnet capacity を計画します。`/19` や RFC 6598 range は、普遍的な要件ではなく example design choice です。新しい CIDR を associate し、必要な subnet/route を作成し、CNI/workload adoption をまとめて計画してください。

warm-pool strategy は 1 つ選びます。free-IP および total-IP target を使用する IPv4 prefix の例は次のとおりです。

```json
{
  "env": {
    "ENABLE_PREFIX_DELEGATION": "true",
    "WARM_IP_TARGET": "5",
    "MINIMUM_IP_TARGET": "10"
  }
}
```

これらの IP target が設定されている場合、追加の `WARM_PREFIX_TARGET` を独立した有効 target と解釈しないでください。cluster size のみから安全性を推測するのではなく、allocation failure と実際の resource constraint を監視してください。

### Metrics と Alert

リリース済み IPAMD code は `awscni_total_ip_addresses`、`awscni_assigned_ip_addresses`、および counter `awscni_no_available_ip_addresses` を export します。total/assigned gauge は、VPC subnet space 全体ではなく、**IPAMD allocated pool** を示します。小さな warm target では assigned/total ratio が高くなることがあります。cooldown、branch interface、IP family、kubelet capacity には追加の context が必要です。

Prometheus Operator CRD と selector は、すでに設定されている必要があります。Helm 所有の CNI では、chart がこの **IPv4-cluster 例**の PodMonitor を作成できます。

```yaml
podMonitor:
  create: true
  labels:
    release: prometheus
  interval: 30s
  relabelings:
  - sourceLabels:
    - __meta_kubernetes_pod_node_name
    targetLabel: node
  - targetLabel: cluster
    replacement: example-cluster
  - targetLabel: ip_family
    replacement: ipv4
  - targetLabel: job
    replacement: aws-vpc-cni
```

例の cluster label を置き換え、`release` selector を調整し、IP-family label を正しく設定してください。label は cluster の family を検出しません。chart は Agent の名前付き `metrics` port と、有効な policy agent の `agentmetrics` port を scrape します。EKS-managed add-on には、2 つ目の CNI Helm release をインストールする代わりに、独立して設定した scraper/PodMonitor が必要です。

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: vpc-cni-signals
  namespace: monitoring
  labels:
    release: prometheus
spec:
  groups:
  - name: vpc-cni
    rules:
    - record: vpc_cni:allocated_ipv4_pool_utilization:ratio
      expr: (awscni_assigned_ip_addresses{job="aws-vpc-cni",ip_family="ipv4"} / awscni_total_ip_addresses{job="aws-vpc-cni",ip_family="ipv4"})
        and (awscni_total_ip_addresses{job="aws-vpc-cni",ip_family="ipv4"} > 0)
    - alert: CniHighAllocatedIPv4PoolUtilization
      expr: vpc_cni:allocated_ipv4_pool_utilization:ratio > 0.9
      for: 5m
      labels:
        severity: info
      annotations:
        summary: Most currently allocated IPAMD IPv4 addresses are assigned
        description: This is allocated-pool utilization, not subnet exhaustion. Check
          warm targets, assignment failures and available subnet space.
    - alert: CniIPAssignmentFailures
      expr: increase(awscni_no_available_ip_addresses{job="aws-vpc-cni"}[5m]) > 0
      for: 1m
      labels:
        severity: warning
      annotations:
        summary: IPAMD could not assign an available IP address
    - alert: CniMetricsScrapeFailed
      expr: up{job="aws-vpc-cni"} == 0
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: A known CNI metrics endpoint cannot be scraped
```

pool ratio は IPv4 と正の観測済み denominator に限定されます。これは informational tuning signal であり、subnet exhaustion の証明ではありません。assignment-failure counter は実際に失敗した allocation を示します。scrape failure は disappeared target とは異なります。期待される node/component inventory は別に比較してください。データなしは健全なゼロではありません。実際の monitoring environment で threshold、label、notification routing を調整してください。

## 参照

- [VPC CNI 1.23.0 documentation](https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.23.0/README.md)
- [VPC CNI Helm values](https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.23.0/charts/aws-vpc-cni/values.yaml)
- [Chart version metadata](https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.23.0/charts/aws-vpc-cni/Chart.yaml)
- [Released CNI manifest](https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.23.0/config/master/aws-k8s-cni.yaml)
- [IPAMD implementation](https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.23.0/pkg/ipamd/ipamd.go)
- [IPAMD introspection server](https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.23.0/pkg/ipamd/introspect.go)
- [IPAM datastore](https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.23.0/pkg/ipamd/datastore/data_store.go)
- [IPAMD metric definitions](https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.23.0/utils/prometheusmetrics/prometheusmetrics.go)
- [Network policy agent 1.4.1](https://github.com/aws/aws-network-policy-agent/blob/v1.4.1/README.md)
- [AWS Helm chart index](https://aws.github.io/eks-charts/index.yaml)
- [EKS security groups for Pods](https://docs.aws.amazon.com/eks/latest/userguide/security-groups-for-pods.html)
- [SGPP operating considerations](https://docs.aws.amazon.com/eks/latest/best-practices/sgpp.html)
- [EKS Multus support boundaries](https://docs.aws.amazon.com/eks/latest/userguide/pod-multus.html)
- [EKS Windows networking](https://docs.aws.amazon.com/eks/latest/userguide/windows-support.html)
- [EKS IPv6 support](https://docs.aws.amazon.com/eks/latest/userguide/cni-ipv6.html)
- [eksctl IPv6 configuration](https://docs.aws.amazon.com/eks/latest/eksctl/vpc-ip-family.html)
- [CNI IAM configuration](https://docs.aws.amazon.com/eks/latest/userguide/cni-iam-role.html)
- [EKS VPC CNI management](https://docs.aws.amazon.com/eks/latest/userguide/managing-vpc-cni.html)
- [EKS network policy conditions](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html)
- [Enable EKS network policy](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy-configure.html)
- [Prefix allocation and Pod-capacity limits](https://docs.aws.amazon.com/eks/latest/userguide/cni-increase-ip-addresses-procedure.html)

## クイズ

[VPC CNI Quiz](../quizzes/networking/01-vpc-cni-quiz.md) で理解度を確認してください。
