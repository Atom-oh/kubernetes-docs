# パート8: EKSとの統合

> **確認済みベースライン**: Calico 3.32.2 / Tigera Operator 1.42.6 / CalicoがテストしたKubernetes 1.34～1.36。**最終更新**: 2026年10月12日

## 概要

このガイドでは、Amazon VPC CNIを使う**通常のLinux EC2ワーカーノード**にCalicoのポリシーを適用します。VPC CNIがPod IPを割り当ててVPCネットワークを構成し、Calicoはノードのデータプレーンにポリシーを設定します。以下のインストールではIptablesデータプレーンとkube-proxyを維持します。CalicoネットワーキングやeBPFを使う構成は別の選択肢であり、それぞれ追加の前提条件があります。

このレビュー時点で、EKSの標準サポート対象は1.34～1.37、延長サポート対象は1.31～1.33です（[EKS Kubernetesバージョンのライフサイクル](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)）。Calico 3.32が公開しているKubernetesのテスト範囲は1.34～1.36です。EKSでの提供状況、上流Kubernetesのリリース、Calicoの互換性は、それぞれ別に確認してください。EKSで1.37を使えても、1.37がCalico 3.32のテスト対象に含まれるわけではありません。インストール前に、対象リージョンのEKSとアドオンのバージョンを確認してください。

## VPC CNIとCalicoのアーキテクチャ

![VPC CNIがPodインターフェイスとVPC IPの割り当てを管理し、Felixがノードのポリシーデータプレーンを設定する。これは制御と設定の関係を示しており、パケットが各プロセスを通過する経路を示すものではない。](../../.gitbook/assets/en-networking-calico-08-eks-integration-0.png)

[🔍 インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-08-eks-integration-0.html)

図は各コンポーネントの責務をまとめています。パケットは、転送プロキシとしてpauseコンテナやFelixプロセスを通過するわけではありません。FelixはLinuxカーネルが評価するルールを設定します。`iptables / eBPF` というラベルはデータプレーンの選択肢を示し、このガイドでインストールするのはIptablesです。Typhaとkube-controllersは顧客のワーカーノード上で動作し、AWS管理のEKSコントロールプレーン内で動作するものではありません。

| コンポーネント | この構成における責務 |
| --- | --- |
| `aws-node` / IPAMDとVPC CNIプラグイン | ENIとIPの割り当てを管理し、Podの接続を構成する |
| `calico-node`内のFelix | ローカルエンドポイント向けのポリシールールを設定する |
| Typha | データストアの更新をFelixに配信する。スケーリングはOperatorが管理する |
| kube-controllers | CalicoのデータをKubernetesリソースと同期する |
| kube-proxy | このベースラインでKubernetes Serviceの転送を担う |

ノード間通信では、カーネルが該当するポリシーを評価し、VPC経由でパケットを送ります。同一ノード内の通信はホスト内にとどまる場合があります。破棄されたパケットは破棄され、ポリシーによる拒否が送信元へ応答として返ることはありません。通信を許可するには、該当する送信元のegress制御と宛先のingress制御の両方が許可する必要があります。

## ポリシーエンジンとインストール方法を選ぶ

| 選択肢 | インストールするもの | ライフサイクルと管理範囲 |
| --- | --- | --- |
| Amazon VPC CNIのネットワークポリシー | AWSのポリシー実装 | 互換性のある`vpc-cni`アドオンを構成する。Calicoはインストールしない |
| Tigera Operatorのマニフェスト | OperatorとCalicoカスタムリソース | リリースを固定し、CRDを管理してからInstallationを調整する |
| Tigera OperatorのHelmチャート | Helmで構成を管理する同じOperator | valuesをレンダリングして確認し、アップグレードには既存のリリースを使う |
| Operatorを使わないCalicoマニフェスト | Calicoコンポーネント | プラットフォーム固有の設定を維持し、アップグレード手順を自分で管理する |

EKSアドオンは、新しいバージョンが公開されたりクラスターのマイナーバージョンが変わったりしても、自動更新されません。AWS、Marketplace、コミュニティのアドオンでは、サポートを担当する組織も異なります。`calico`という名前のアドオンがある、またはMarketplace製品がこのOSSインストールと同じだと決めつけないでください。実際のカタログで、提供元、バージョン、ライセンス、コンピュートとの互換性を確認してください。

**同じエンドポイントに適用するネットワークポリシーエンジンは1つにしてください。** CalicoのEKSガイドでは、AWS VPC CNIのネットワークポリシーを無効にするよう求めています。移行には、ポリシー、ノードの状態、可用性を確認したうえでの引き継ぎが必要です。両方のエンジンを動かしたままフラグだけを切り替えても、移行手順にはなりません。AWSは、ポリシーエージェントを削除してもルールが残る可能性があると警告し、サードパーティ製エンジンから移行する場合は影響を受けるノードの置き換えを推奨しています。[AWSのポリシーに関する注意事項](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html)と[無効化の手順](https://docs.aws.amazon.com/eks/latest/userguide/network-policy-disable.html)を参照してください。

## 既存のVPC CNIインストールを準備する

次のコマンドは、既存の管理対象`vpc-cni`アドオンを調べます。実際のリージョンとクラスター名を指定してください。セルフマネージドのVPC CNIは、そのマニフェストまたはHelmの管理元を通じて変更します。

```bash
EKS_CLUSTER=my-cluster
EKS_REGION=us-east-1
EKS_VERSION=$(aws eks describe-cluster --name "$EKS_CLUSTER" \
  --region "$EKS_REGION" --query cluster.version --output text)

aws eks describe-addon-versions --addon-name vpc-cni \
  --kubernetes-version "$EKS_VERSION" --region "$EKS_REGION" \
  --query 'addons[0].addonVersions[].{version:addonVersion,compatibility:compatibilities,compute:computeTypes}'

aws eks describe-addon --cluster-name "$EKS_CLUSTER" \
  --addon-name vpc-cni --region "$EKS_REGION" > vpc-cni-current.json

VPC_CNI_VERSION=$(jq -r '.addon.addonVersion' vpc-cni-current.json)
aws eks describe-addon-configuration --addon-name vpc-cni \
  --addon-version "$VPC_CNI_VERSION" --region "$EKS_REGION" \
  --query configurationSchema --output text > vpc-cni-schema.json
```

Calicoでは、VPC CNIが`vpc.amazonaws.com/pod-ips`を速やかに公開できるよう、`ANNOTATE_POD_IP=true`を設定する必要があります。`aws-node`のServiceAccountにはPodを更新する権限が必要です。現在のVPC CNIドキュメントによると、EKSアドオンがこの権限を自動で更新します。既存のClusterRoleを上書きせず、権限を確認してください。

```bash
kubectl auth can-i patch pods --all-namespaces \
  --as=system:serviceaccount:kube-system:aws-node
```

この権限確認には、対象のServiceAccountになり代わって操作する権限が必要です。その権限がない場合は、既存のルールを置き換えず、別のRoleBindingで必要なルールを追加できます。標準構成と異なる場合は、実際のServiceAccount名を指定してください。

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: calico-vpc-pod-annotations
rules:
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["patch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: calico-vpc-pod-annotations
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: calico-vpc-pod-annotations
subjects:
  - kind: ServiceAccount
    name: aws-node
    namespace: kube-system
```

レビュー済みの**新規構成またはすでにポリシー専用となっている構成**では、現在のアドオン設定を保ったまま、次の候補を準備します。

```bash
jq '(.addon.configurationValues // "") as $current
  | (if $current == "" then {} else ($current | fromjson) end)
  | .enableNetworkPolicy = "false"
  | .env.ANNOTATE_POD_IP = "true"
  | del(.env.NETWORK_POLICY_ENFORCING_MODE)' \
  vpc-cni-current.json > vpc-cni-calico.json
```

このコマンドはJSON形式の設定値を想定しています。既存の値がYAMLの場合は、フィールドを落とさないように解析・変換してから候補を作成してください。解析に失敗したら中止します。取得したEKSビルドスキーマで候補を検証し、差分を確認してください。`NETWORK_POLICY_ENFORCING_MODE`はAWSのポリシーエージェント用の変数です。エージェントがないのに設定を残すと、Podを作成できなくなる場合があります。現在AWSのポリシーが有効なら、この候補を使う前に移行計画を完了してください。承認済みの設定はアドオンの管理元を通じて適用します。

```bash
aws eks update-addon --cluster-name "$EKS_CLUSTER" \
  --addon-name vpc-cni --region "$EKS_REGION" \
  --configuration-values file://vpc-cni-calico.json \
  --resolve-conflicts PRESERVE
```

返された更新ステータスと、更新後のDaemonSetを確認してください。競合を保持する設定があると、目的のフィールドが反映されない場合があります。JSONの解析に成功したことや更新要求が受理されたことを、ポリシーが適用された証拠として扱わないでください。

## OperatorでCalicoをインストールする

新規インストールでは、以下のマニフェスト方式かHelm方式の**どちらか一方**を選んでください。既存リリースの上に2つ目のOperatorをインストールしないでください。以下の例は、通常のEC2 Linuxワーカー、到達可能なKubernetes APIとDNS、互換性のあるVPC CNI、競合するポリシーエンジンがない環境を想定しています。

### Operatorマニフェスト方式

Calico 3.32では、CalicoのCRDとOperatorマニフェストが分離されています。

```bash
kubectl create -f https://raw.githubusercontent.com/projectcalico/calico/v3.32.2/manifests/v1_crd_projectcalico_org.yaml
kubectl create -f https://raw.githubusercontent.com/projectcalico/calico/v3.32.2/manifests/tigera-operator.yaml
```

次の内容を`calico-eks-installation.yaml`として保存します。

```yaml
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
    linuxDataplane: Iptables
  nodeUpdateStrategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
---
apiVersion: operator.tigera.io/v1
kind: APIServer
metadata:
  name: default
spec: {}
---
apiVersion: operator.tigera.io/v1
kind: Goldmane
metadata:
  name: default
spec: {}
---
apiVersion: operator.tigera.io/v1
kind: Whisker
metadata:
  name: default
spec: {}
```

```bash
kubectl apply -f calico-eks-installation.yaml
kubectl get tigerastatus
kubectl get pods -n calico-system
```

APIサーバー、Goldmaneフロー集約機能、Whisker UIはOSSで利用できます。環境に応じてアクセス方法と必要なリソース容量を設定してください。`cni.type: AmazonVPC`を指定すると、IPAMとネットワーク設定をVPC CNIに委譲します。`bgp: Disabled`だけではCNIは選択されません。Typhaのレプリカ数はOperatorに管理させてください。`typhaDeployment.spec.replicas`は、サポート対象のInstallation上書き設定ではありません。[スケーリングの詳細](07-advanced-topics.md)を参照してください。

### Helm方式

次の内容を`calico-eks-values.yaml`として保存します。`installation`はInstallation APIに対応します。トップレベルの`nodeSelector`が制御するのはOperator Podであり、すべてのCalicoコンポーネントではありません。Helmはサポート対象外の値を警告なしに無視する場合があるため、レンダリング後のリソースを確認してください。

```yaml
installation:
  enabled: true
  kubernetesProvider: EKS
  cni:
    type: AmazonVPC
  calicoNetwork:
    bgp: Disabled
    linuxDataplane: Iptables
  nodeUpdateStrategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
apiServer:
  enabled: true
goldmane:
  enabled: true
whisker:
  enabled: true
manageCRDs: true
```

```bash
helm repo add projectcalico https://docs.tigera.io/calico/charts
helm repo update projectcalico
helm template calico projectcalico/tigera-operator \
  --version v3.32.2 --namespace tigera-operator \
  -f calico-eks-values.yaml > calico-rendered.yaml

# After reviewing the rendered configuration for the prepared cluster:
helm install calico projectcalico/tigera-operator \
  --version v3.32.2 --namespace tigera-operator --create-namespace \
  -f calico-eks-values.yaml
```

`manageCRDs: true`の場合、起動後のCRD管理はOperatorが行います。新しいフィールドをすぐ使うアップグレードでは、既存の管理元を通じて対応するCRDを先に適用してください。[Calicoのアップグレード手順](https://docs.tigera.io/calico/latest/operations/upgrading/kubernetes-upgrade)に従ってください。Helmのロールバックだけでは、CRDや保存データの移行が取り消されるとは限りません。

## 代替案: AWSネイティブのネットワークポリシー

AWS VPC CNIの標準NetworkPolicy対応は、EKS 1.14ではなく**VPC CNI 1.14**で始まりました。現在のAWSガイドでは、標準ポリシーと管理者ポリシーの両方でVPC CNI **1.21以降**、互換性のあるEKS／プラットフォームバージョン、Linuxカーネル5.10以降が必要です。古い起動バージョンの例ではなく、最新の互換性情報を確認してください。

AWSは、namespace単位の`networking.k8s.io/v1` NetworkPolicyに加え、AdminとBaselineのtierを含む`networking.k8s.aws/v1alpha1` **ClusterNetworkPolicy**を公開しています。これはCalico GlobalNetworkPolicyやCalicoで構成可能なtierとは異なるAPIです。AWSネイティブのポリシーがnamespace単位のルールだけに限定される、と説明しないでください。

| 機能 | AWSネイティブの実装 | このガイドのCalico OSS |
| --- | --- | --- |
| Kubernetes NetworkPolicy | 対象となるEC2 Linuxノードで対応 | 管理対象エンドポイントで対応 |
| クラスター全体のポリシー | 独自のルールと前提条件を持つAWS ClusterNetworkPolicy | Calico GlobalNetworkPolicyとTier |
| ポリシーの可観測性 | エージェントのメトリクスとイベントログ。CloudWatchへの配信は別途設定する | Felix／Typhaメトリクス、GoldmaneとWhiskerのフロー可観測性 |
| アプリケーション層のポリシー | L3／L4ネットワークポリシーから推測しない | 別途Dikastes／Istio統合が必要。このインストールでは有効にならない |
| CalicoのDNS／FQDNポリシー | Calico APIの実装ではない | ドメインベースのポリシー機能は商用Calicoエディションが必要 |

AWSネイティブの方式では、互換性のあるVPC CNIアドオンまたはHelm設定から`enableNetworkPolicy`を構成します。`aws-node`に存在しない`ENABLE_NETWORK_POLICY`環境変数を設定するだけでは不十分です。ネイティブの`standard`起動モードでは、ポリシーの設定中に最初は通信が許可されます。`strict`モードは拒否状態で開始するため、DNSを含む必要な通信経路を許可してください。これらのAWS設定はCalicoの起動動作を構成しません。

AWSネイティブの適用には、EC2 Linuxのみ、Podのプライマリインターフェイスのみ、IPファミリーの制約、コントローラー管理Podでの確実な動作など、公開済みの制限があります。ポート／プロトコルの制限とServiceポートの要件も確認してください。AWS管理のPolicyEndpointリソースは、コントローラーの管理下に維持します。設定と移行の詳細は[現在のVPC CNIガイド](../01-vpc-cni.md)を参照してください。

## ノード種別とネットワーク構成

| 構成 | 適用範囲 |
| --- | --- |
| 通常の管理対象またはセルフマネージドEC2 Linuxノード + VPC CNI | 上記のポリシー専用ベースライン。管理方式だけではCalicoの対応可否は決まらない |
| EC2ノード + Calico CNI全体 | Tigeraが別途説明する構成。Podアドレス、コントロールプレーンへの到達性、CNIの管理元、サポート範囲が変わる |
| EKS Fargate | これらのPodではCalicoノードエージェントもVPC CNIのネイティブネットワークポリシーも動作しない。Pod用セキュリティグループは別の対応済み制御手段 |
| EKS Auto Mode | AWSのネットワーク機能とポリシー機能が組み込まれている。代替CNIとネットワークポリシープラグインには非対応 |
| EKS Hybrid Nodes | VPC CNIには非対応。専用CNIガイドにAWS管理のCilium 1.17／1.18ビルドが掲載されている。サポート上の注意事項も参照 |
| Windowsノード | Windows／VPC CNIとCalico HNSに専用手順がある。CalicoのeBPFデータプレーンには非対応。[Windowsの制限](07-advanced-topics.md)を参照 |

専用Hybrid CNIガイドにはAWS管理のCiliumビルドが掲載され、別ページにあるCalicoの例へのリンクもあります。一方、[代替CNIの総合ページ](https://docs.aws.amazon.com/eks/latest/userguide/alternate-cni-plugins.html)では、Hybrid Nodes向けのCilium／Calicoの基本対応が現在も説明されています。例の掲載場所が変わったことからCalicoのサポート終了を推測したり、任意の上流バージョンをAWS対応とみなしたりしないでください。ディストリビューションと機能ごとのサポート範囲を確認してください。

EC2エンドポイント上のCalicoポリシーは、Fargate側のピアに関係する当該エンドポイントの通信を制限できます。ただし、Fargate内部でCalicoポリシーが適用されるわけではありません。複数のコンピュート方式を併用するクラスターでは、すべてのワーカーを「Calico完全対応」とひとまとめにせず、スケジューリングとポリシー適用範囲を明確にしてください。

VPC CNIの`enableNetworkPolicy`をfalseにしても、Calico CNI全体が有効になるわけではありません。Tigeraの新規クラスター手順では、ワーカーを追加する前に競合するCNIを削除します。既存の本番クラスターから`aws-node`を削除して移行を済ませようとしないでください。公開済みのオーバーレイ構成では、Admission Webhookなど、APIサーバーからPodへの通信にも特別な検討が必要です。信頼された`hostNetwork`コンポーネントを使う方法は、ドキュメントに記載された回避策の一つです。この構成を採用する前に、Pod CIDR、戻り経路、MTU、必要に応じたノードIAM／送信元・宛先チェック、AWSとTigeraのサポート範囲を確認してください。

Auto Modeでは、VPC CNIの環境変数やENIConfig設定で管理対象のネットワークサービスを構成することはできません。NodeClassを使ってください。Auto ModeではCoreDNSがノードのシステムサービスとして動作します。Auto Modeのみのクラスターに従来のCoreDNS Deploymentは不要ですが、Auto Mode以外のノードも混在する場合は引き続き必要です。最初のDNS問い合わせがノード内で処理されても、その後の転送通信はノード外へ出る場合があります。

## IAM、IRSA、Pod Identity

基本的なポリシー専用CalicoインストールではKubernetes RBACを使うため、`calico-node`に広範なEC2探索やCloudWatch用IAMロールは必要ありません。VPC CNIには、別途ドキュメントに記載されたAWS権限が必要です。ログエクスポーターや商用クラウド統合を別に使う場合は、**そのコンポーネントの**ServiceAccountに追加権限が必要になることがあります。

IRSAはクラスターのOIDCプロバイダーと適切に範囲を絞った信頼ポリシーを使い、ServiceAccountにAWS認証情報を渡します。コンポーネント、SDK、コンピュート方式が対応していれば、EKS Pod Identityも選択できます。IAMポリシーを追加するだけでも、存在しない`Installation.spec.nodeMetadata`を設定しても、ワークロードに認証情報は渡りません。対象コンポーネントの設定に従い、Operatorが管理するServiceAccountと競合しないようにしてください。[VPC CNIのIAM設定](https://docs.aws.amazon.com/eks/latest/userguide/cni-iam-role.html)を参照してください。

## セキュリティグループとCalicoポリシー

![セキュリティグループ、Calicoポリシー、アプリケーション認証が、それぞれ異なるアクセス制御層を構成する。](../../.gitbook/assets/en-networking-calico-08-eks-integration-3.png)

[🔍 インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-08-eks-integration-3.html)

図は概念的な階層を示しており、評価順を固定するものではありません。Calicoはtier／順序とルールの意味に従ってポリシーを評価します。NetworkPolicyが常にGlobalNetworkPolicyより先に適用されるわけではありません。CloudTrailに記録されるのはAWS APIの操作であり、パケットの判定ではありません。VPC Flow Logsと設定済みのポリシーログツールは、別々のトラフィック情報を提供します。アプリケーションのmTLSと認可は別途導入してください。

セキュリティグループはENIにアタッチされます。**Pod用セキュリティグループ**はSecurityGroupPolicyでワークロードを選択できるため、「セキュリティグループが選択するのはインスタンスだけ」という説明は正しくありません。Pod用セキュリティグループとCalicoポリシーを併用するには、AWSの要件としてVPC CNI 1.11以降と`POD_SECURITY_GROUP_ENFORCING_MODE=standard`が必要です。strictモードでは、該当Podの通信にCalicoポリシーが適用されません。モード変更後はbranch ENIとインスタンスの対応状況を確認し、該当Podを作り直してください。Pod用セキュリティグループはWindowsとAuto Modeには対応していません。

VPC CNIで通常の外部SNATが有効になっているstandardモード（`AWS_VPC_K8S_CNI_EXTERNALSNAT=false`）では、VPC外への通信にノードのプライマリENI IPとセキュリティグループが使われます。Pod用セキュリティグループのegressルールが、すべての通信経路を対象にすると考えないでください。[AWSが示す適用条件](https://docs.aws.amazon.com/eks/latest/userguide/security-groups-for-pods.html)を参照してください。

### Namespace単位のアプリケーションポリシー

この例は、準備済みの`calico-eks-demo` namespaceにある`app=frontend` Podだけを選択します。同じnamespaceの**クラスター内ゲートウェイPod**からTCP 8080への接続を許可し、frontendから同一namespaceのbackend PodへのTCP 8080のegressを許可します。`k8s-app=kube-dns`ラベルを持つ通常のCoreDNS Podを想定しています。NodeLocal DNSなど別のリゾルバーには、異なる宛先が必要です。他のポリシーやtierによって結果が変わるため、最終的に有効なポリシー一式を確認してください。

```yaml
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: frontend-policy
  namespace: calico-eks-demo
spec:
  selector: app == 'frontend'
  types: [Ingress, Egress]
  ingress:
    - action: Allow
      protocol: TCP
      source:
        selector: app == 'gateway'
      destination:
        ports: [8080]
  egress:
    - action: Allow
      protocol: TCP
      destination:
        selector: app == 'backend'
        ports: [8080]
    - action: Allow
      protocol: UDP
      destination:
        namespaceSelector: projectcalico.org/name == 'kube-system'
        selector: k8s-app == 'kube-dns'
        ports: [53]
    - action: Allow
      protocol: TCP
      destination:
        namespaceSelector: projectcalico.org/name == 'kube-system'
        selector: k8s-app == 'kube-dns'
        ports: [53]
```

宛先セレクターとポートは、**同じ**`destination`マッピングの下に置いてください。YAMLで同じキーを重複させるとセレクターが黙って削除され、意図しないエンドポイントにTCP 8080を許可するおそれがあります。ALB／NLBは`app=load-balancer`を持つKubernetes Podではありません。[ロードバランサーガイド](../03-aws-lb-controller.md)を使い、ターゲットモード、ヘルスチェック、実際に観測される送信元アドレスを別途考慮してください。

`all()`を選択する空のクラスター全体向けGlobalNetworkPolicyは、DNS、API、モニタリング、アプリケーション通信を妨げるおそれがあります。まず対象を選んだテスト用namespaceでdefault-denyを構成し、依存通信を明示的に許可してください。[ネットワークポリシー](05-network-policy.md)を参照してください。

## アップグレードと復旧

1. EKSコントロールプレーン、ノードOS／kubelet、VPC CNI、kube-proxy、Calico／Operator／CRD、calicoctlの各バージョンを一覧にします。管理下にある設定とポリシーをエクスポートします。
2. **予定する移行の前後両方**と互換性のあるCalicoバージョンを選びます。「必ず先に／後にCalicoをアップグレードする」という共通ルールはありません。インストール方式に合った手順とCRD移行の注意事項に従ってください。
3. EKSアップグレードインサイト、削除済みAPI、すべてのアドオンとの互換性を確認します。EKSコントロールプレーンを一度に1つのマイナーバージョンずつアップグレードし、その後、ノードと該当するアドオンを互換性のあるバージョンに更新します。
4. 段階的な更新の途中も含め、新しく作成したPodと拒否される通信を確認し、ポリシーとServiceの動作を検証します。設定の管理元とロールバックの前提条件を明確にしてください。

```bash
aws eks describe-cluster --name "$EKS_CLUSTER" --region "$EKS_REGION" \
  --query 'cluster.{version:version,platform:platformVersion,status:status}'
kubectl get nodes -o wide
kubectl get daemonset calico-node -n calico-system -o wide
kubectl get tigerastatus
helm get values calico -n tigera-operator -o yaml
```

現在のEKSでは、インプレースアップグレード後7日以内であれば、条件を満たした場合に**直前のマイナーバージョンへロールバック**できます。クラスターが公開されている適格性と準備要件を満たす必要があり、一般的なダウングレード機能ではありません。通常の管理対象／セルフマネージド／ハイブリッドノードや、互換性のないアドオンは、コントロールプレーンより先に準備が必要です。Auto Modeはノードのロールバックを処理しますが、Fargateのワークロードには別の対応が必要です。CalicoとEKSアドオンは自動では元に戻りません。etcdデータを保持しても、互換性のないリソースが安全になるわけではありません。未解決の互換性問題を隠すために`--force`を使わず、[現在のロールバック手順](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html)に従ってください。対象期間外では、別のサポート対象クラスターへの移行を計画してください。

古いOperatorマニフェストを適用したり`helm rollback`を実行したりしても、安全にCalicoをダウングレードできた証明にはなりません。復旧方法を選ぶ前に、対象リリースのサポート状況とスキーマ／データ変更を確認してください。`calicoctl node status`が示すのはノードローカルのBGP状態であり、ポリシー専用EKS構成の受け入れテストではありません。

## コストとパフォーマンス

| 要素 | 確認する内容 |
| --- | --- |
| ワーカーのリソース | 実際のポリシーやエンドポイントの変化量に応じたFelix、Typha、コントローラー、フロー集約の負荷を測る。CPUリクエストはAWSの別料金項目ではない |
| VPCのIP容量 | Prefix Delegationはアドレスの割り当てと密度に影響するが、ENIの接続料金が自動的に割引されるわけではない |
| ログ／メトリクス | 保持、取り込み、クエリ、エクスポーター配信にはそれぞれ費用がある。メトリクスはフローログではない |
| AZ間通信 | 実際の送信元／宛先経路とサービス料金を確認する。配置場所は可用性にも影響する |
| EKSのライフサイクル | 延長サポートでクラスター料金が追加される場合がある。現在のサポート日程を確認する |

以前のコンポーネントごとの金額例には、リージョン、インスタンス料金、費用配分の前提がありませんでした。そのまま使えるコストモデルではありません。任意のリソース上限から毎月の固定節約額を主張するのではなく、実測したリソース需要と該当するAWS料金を使ってください。

### Prefix Delegation

通常のVPC CNIノードでは、`ENABLE_PREFIX_DELEGATION`、`WARM_PREFIX_TARGET`、`MINIMUM_IP_TARGET`、`WARM_IP_TARGET`を、**アドオンの`env`設定**か、管理元となるDaemonSet／Helm設定に記述します。ConfigMapに小文字で`enable-prefix-delegation`を追加しても、IPAMDの設定にはなりません。

まず、ドキュメントに記載された割り当て方式を1つ選んでください。`WARM_IP_TARGET`と`MINIMUM_IP_TARGET`は`WARM_PREFIX_TARGET`より優先されるため、すべて設定しても効果は累積しません。IPv4のprefixには連続した`/28`サブネット領域と対応するインスタンスタイプが必要です。サブネットの断片化、予約済みアドレス、max-Pods／kubelet設定、ロールアウト計画を確認してください。[AWSのPrefix Delegation手順](https://docs.aws.amazon.com/eks/latest/userguide/cni-increase-ip-addresses-procedure.html)を参照してください。

### EKS上のCalico eBPF

CalicoはeBPFデータプレーンについて、EKSと互換性のあるVPC CNIネットワーキングを公開しています。ただしServiceの処理方法が変わり、別途移行が必要です。[パート6](06-ebpf-dataplane.md)に従ってください。カーネル／プラットフォームの確認、APIサーバーFQDNへの直接接続と起動時DNS、kube-proxyの管理元、ヘルスポート、ロールバック状態はいずれも重要です。

VPC CNIを使う場合に、常にkube-proxyを動かし続ける必要があるわけでは**ありません**。kube-proxyとの共存が必要な場合、記載済みの競合を避けるためCalicoでは`bpfKubeProxyIptablesCleanupEnabled: false`と`bpfKubeProxyHealthzPort: 0`の両方が必要です。汎用的なDaemonSetセレクターのパッチは、管理元によって元に戻される可能性があります。また、関係のないセレクターを上書きしてはいけません。DSRはEKSの既定の最適化ではありません。AWSサブネット／送信元アドレスのチェックや外部ロードバランサーの制約を別途検証してください。このベースラインではIptablesとkube-proxyを維持します。

一般的なsysctl設定一式、根拠のない最小値までのメモリ削減、conntrackの有効期間短縮だけでは、性能改善を立証できません。実際のワークロードでベンチマークを取り、戻り経路、確立済み接続、障害からの復旧を維持してください。

## eksctlによるクラスター計画例

これは**通常の管理対象Linuxノード向けの計画例**であり、本番で検証済みの手順でもAuto Modeからの変換手順でもありません。プロビジョニング前に`describe-addon-versions`で対応アドオンのビルドを確認し、承認済みのビルドを設定に固定してください。アドオンバージョンを省略すると互換性のある既定値が選ばれますが、今後のすべてのリリースが承認されたことを意味しません。プライベートAPIに接続するには、VPC内への管理経路が必要です。NAT、ログ、ワーカー容量、IPアドレス範囲は環境ごとに設計してください。

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: calico-eks-demo
  region: us-east-1
  version: "1.36"
iam:
  withOIDC: true
vpc:
  cidr: 10.0.0.0/16
  clusterEndpoints:
    publicAccess: false
    privateAccess: true
managedNodeGroups:
  - name: linux-workers
    instanceType: m5.large
    amiFamily: AmazonLinux2023
    desiredCapacity: 3
    minSize: 3
    maxSize: 6
    privateNetworking: true
    volumeType: gp3
    volumeSize: 100
addons:
  - name: vpc-cni
    attachPolicyARNs:
      - arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy
    configurationValues: |
      enableNetworkPolicy: "false"
      env:
        ANNOTATE_POD_IP: "true"
  - name: coredns
  - name: kube-proxy
cloudWatch:
  clusterLogging:
    enableTypes: [api, audit, authenticator, controllerManager, scheduler]
```

IPv4 CNIポリシーに必要なIAM権限はCalicoではなくVPC CNIのIDに付与します。他のIPファミリーやID方式では、IAM設定を見直してください。承認済みのクラスターが作成されたら、アノテーションとRBACの確認を行い、上記のCalicoインストール方式から**1つだけ**実施してください。

## 設定結果を検証する

```bash
kubectl get tigerastatus
kubectl rollout status daemonset/calico-node -n calico-system --timeout=300s
kubectl get pods -n calico-system -o wide
kubectl get pods -n calico-eks-demo -o json \
  | jq '.items[] | {name: .metadata.name, ip: .status.podIP,
      annotatedIPs: .metadata.annotations["vpc.amazonaws.com/pod-ips"]}'
kubectl get networkpolicies.projectcalico.org -n calico-eks-demo
```

コントローラーが管理するテスト用ワークロードを使い、同じノード内、ノード／AZ間、Podの再作成後、更新中について、許可される通信と拒否される通信を確認してください。DNS、アプリケーションに必要なAPI／IDエンドポイント、Service通信、ロードバランサーのヘルスチェックも検証します。PodがRunningであることやノードがReadyであることだけでは、意図した拒否が機能していることも、起動時にポリシー適用の空白がないことも証明できません。IPv6は別途テストしてください。Calicoの最新EKSガイドでは、`ENABLE_V4_EGRESS=true`を設定したIPv6 Podへのポリシー適用は対象外です。

このドキュメントの例は、公開済みスキーマとレンダリング済みチャートに照らして確認しています。検証のためにEKSクラスター、IAMリソース、本番トラフィックを作成・使用したわけではありません。

## 参考資料

- [EKSでのCalico](https://docs.tigera.io/calico/latest/getting-started/kubernetes/managed-public-cloud/eks)
- [Calicoの要件](https://docs.tigera.io/calico/latest/getting-started/kubernetes/requirements)
- [CalicoのHelmインストール](https://docs.tigera.io/calico/latest/getting-started/kubernetes/helm)
- [Calicoのアップグレード](https://docs.tigera.io/calico/latest/operations/upgrading/kubernetes-upgrade)
- [VPC CNI 1.23設定リファレンス](https://github.com/aws/amazon-vpc-cni-k8s/blob/v1.23.0/README.md)
- [EKSネイティブネットワークポリシー](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html)
- [EKSアドオンの更新](https://docs.aws.amazon.com/eks/latest/userguide/updating-an-add-on.html)
- [EKSバージョンのライフサイクル](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)
- [EKS Auto Modeのネットワーキング](https://docs.aws.amazon.com/eks/latest/userguide/auto-networking.html)
- [EKS Hybrid NodesのCNI](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html)

## 次のステップとクイズ

[運用手順](09-operations.md)に進み、[高度なトピック](07-advanced-topics.md)や[用語集](glossary.md)を確認してください。[EKS統合クイズ](../../quizzes/networking/calico/08-eks-integration-quiz.md)で理解度も確認できます。
