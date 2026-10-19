# Amazon EKS のトラブルシューティング

> **最終更新**: 2026年9月12日

Amazon EKS クラスターの運用では、さまざまな問題が発生する可能性があります。このドキュメントでは、EKS クラスターでよく起きる問題と、その解決方法を説明します。

## 目次

1. [トラブルシューティングの基本](#troubleshooting-basics)
2. [クラスターの作成と管理に関する問題](#cluster-creation-and-management-issues)
3. [ネットワークに関する問題](#networking-issues)
4. [ノードと Pod に関する問題](#node-and-pod-issues)
5. [IAM と認証に関する問題](#iam-and-authentication-issues)
6. [ストレージに関する問題](#storage-issues)
7. [ログとモニタリングに関する問題](#logging-and-monitoring-issues)
8. [パフォーマンスに関する問題](#performance-issues)
9. [アップグレードに関する問題](#upgrade-issues)
10. [よくあるエラーメッセージと解決方法](#common-error-messages-and-solutions)

## トラブルシューティングの基本 {#troubleshooting-basics}

![EKS トラブルシューティングの基本: 症状を特定し、証拠を収集して仮説を検証し、修復、確認、記録を行います。](../.gitbook/assets/en-eks-09-eks-troubleshooting-0.png)

[🔍 インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-09-eks-troubleshooting-0.html)

### トラブルシューティングの進め方

1. 症状、影響を受けるユーザーや workload、発生時間帯を特定します。
2. リソースを変更する前に、関連する状態、ログ、イベント、メトリクスを収集します。
3. 複数の仮説を証拠と照らし合わせます。一般的なエラーだけで原因が確定したと判断しないでください。
4. データや可用性への影響が分かっている、対象を絞った修正を、責任者が管理する経路で適用します。
5. コマンドの終了コードだけでなく、アプリケーションの動作とメトリクスで復旧を確認します。
6. 原因、変更、結果、残る不確実性、再発防止策を記録します。

この章のコマンドは、レビュー済み環境に合わせて使うテンプレートであり、上から順に実行する単一スクリプトではありません。リソースの照会、デバッグ workload の作成、コンポーネントの再起動、インフラストラクチャの削除では影響が異なります。このレビューでは、AWS や Kubernetes に対する実操作は行っていません。

### 必要なツールとコマンド

**既存**クラスターでは、対象のアカウント、リージョン、クラスター、kubectl コンテキストを明示し、それらが一致することを確認します。任意のコンテキスト別名からクラスター名を推測しないでください。有効なクラスターができる前に作成が失敗した場合は、代わりに「クラスターの作成」節のアカウント、リージョン、元のリクエストやスタックの証拠を使います。

```bash
set -euo pipefail
: "${AWS_REGION:?Set the intended Region}"
: "${CLUSTER_NAME:?Set the existing cluster name}"
: "${EXPECTED_ACCOUNT_ID:?Set the intended 12-digit account ID}"
: "${KUBE_CONTEXT:?Set the explicit kubectl context}"
ACTUAL_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
if [ "$ACTUAL_ACCOUNT_ID" != "$EXPECTED_ACCOUNT_ID" ]; then
  echo "Account mismatch" >&2; exit 1
fi
CLUSTER_ENDPOINT=$(aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query cluster.endpoint --output text)
KUBE_ENDPOINT=$(kubectl config view --context "$KUBE_CONTEXT" --minify \
  -o jsonpath='{.clusters[0].cluster.server}')
if [ "$CLUSTER_ENDPOINT" != "$KUBE_ENDPOINT" ]; then
  echo "kubectl context does not match the selected EKS cluster" >&2; exit 1
fi
export AWS_REGION CLUSTER_NAME EXPECTED_ACCOUNT_ID KUBE_CONTEXT
```

#### AWS CLI と eksctl

```bash
aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query 'cluster.{arn:arn,status:status,version:version,health:health,access:accessConfig}'
aws eks list-nodegroups --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION"
aws eks list-addons --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION"
eksctl get nodegroup --cluster "$CLUSTER_NAME" --region "$AWS_REGION"
```

これらのコマンドで一覧できるのは、マネージドノードグループとインストール済みの EKS アドオンです。すべてのセルフマネージドコントローラーやコンピューティングリソースが表示されるわけではありません。手順を選ぶ前に、実際の所有者とコンピューティングタイプを記録します。

#### kubectl

```bash
kubectl --context "$KUBE_CONTEXT" get nodes -o wide
kubectl --context "$KUBE_CONTEXT" get pods -A -o wide
kubectl --context "$KUBE_CONTEXT" get services -A
kubectl --context "$KUBE_CONTEXT" get events -A --sort-by='.metadata.creationTimestamp'
: "${NAMESPACE:?}"; : "${POD_NAME:?}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" describe pod "$POD_NAME"
```

対象の namespace、Pod、コンテナ、ノードを明示します。`describe` の出力やアプリケーションログには、機微な運用情報が含まれることがあります。`kubectl auth can-i` は特定の操作に対する認可を確認します。`aws sts get-caller-identity` は AWS 資格情報の主体を識別します。どちらも単独ではネットワーク接続や Kubernetes 権限全体を証明しません。

### ログの収集と分析

#### EKS コントロールプレーンログ

既存のログ設定と、対象を絞った障害時間帯を確認します。

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"
: "${START_TIME_MS:?Set the incident-window start in epoch milliseconds}"
: "${END_TIME_MS:?Set the incident-window end in epoch milliseconds}"
aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query cluster.logging --output json
aws logs filter-log-events --region "$AWS_REGION" \
  --log-group-name "/aws/eks/$CLUSTER_NAME/cluster" \
  --start-time "$START_TIME_MS" --end-time "$END_TIME_MS" \
  --max-items 200 --output json --no-cli-pager
```

コントロールプレーンログの有効化は、独自の update ID、権限、CloudWatch 料金を伴う別個の `UpdateClusterConfig` 変更です。過去のログは復元されず、アプリケーションやホストのログ収集も有効になりません。ロググループがない、リクエストが拒否された、対象時間帯のログが空、といった状態は可視性上の制限を示します。アプリケーションやホストのログには `/aws/containerinsights/<cluster>/...` または実際の collector の保存先を使います。

#### ノードログ

オペレーターがアクセスできる標準 Linux EC2 ノードでは、セッションを開始する前にノードの `spec.providerID`、アカウント、リージョン、SSM の前提条件を確認します。

```bash
: "${INSTANCE_ID:?Verify the node EC2 ProviderID and account/Region first}"
aws ssm start-session --target "$INSTANCE_ID" --region "$AWS_REGION"
```

次のコマンドはローカル端末ではなく、**そのノードへのセッション内で**実行します。これらの systemd/containerd の例は、ノードイメージに該当ツールがあることを前提としています。Bottlerocket、Fargate、Auto Mode では、サポートされている診断経路を使ってください。

```bash
sudo journalctl -u kubelet --since "15 minutes ago" --no-pager
sudo journalctl -u containerd --since "15 minutes ago" --no-pager
df -h
df -i
free -m
```

現在の EKS 最適化 Linux ノードは containerd を使います。そのノードで Docker daemon のログを調べても、kubelet のランタイムログにはなりません。イメージを prune したり、journal を vacuum したり、何かを再起動したりする前に、ログ、ディスク使用量、inode の証拠を保存してください。不健全なノードで `kubectl top` のメトリクスがないことだけでは、CPU やメモリが枯渇したとは判断できません。

#### Pod ログ

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${POD_NAME:?}"; : "${CONTAINER_NAME:?}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" logs "$POD_NAME" \
  -c "$CONTAINER_NAME" --since=15m --tail=200 --timestamps=true
# Run only when a previous container instance exists in this same Pod.
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" logs "$POD_NAME" \
  -c "$CONTAINER_NAME" --previous --tail=200 --timestamps=true
```

`--previous` が参照するのは、**同じ Pod 内**で以前に終了した、指定コンテナのインスタンスです。削除済みの前任 Pod のログは取得できません。保持された履歴はログバックエンドで確認します。通常コンテナと init container の状態、readiness、終了理由も調べてください。

### 診断情報の収集

```bash
set -euo pipefail
: "${EVIDENCE_PARENT:?Set an existing private directory}"
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"
umask 077
EVIDENCE_DIR=$(mktemp -d "$EVIDENCE_PARENT/eks-diagnosis.XXXXXXXX")
kubectl --context "$KUBE_CONTEXT" get nodes -o wide > "$EVIDENCE_DIR/nodes.txt"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pods -o wide > "$EVIDENCE_DIR/pods.txt"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get services -o wide > "$EVIDENCE_DIR/services.txt"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get events \
  --sort-by='.metadata.creationTimestamp' > "$EVIDENCE_DIR/events.txt"
printf 'Evidence saved to %s; assess the findings before remediation.\n' "$EVIDENCE_DIR"
```

照会に失敗すると、この例は停止します。既存ファイルは部分的な証拠です。対象を絞った一覧で足りる場合は、無差別に `cluster-info dump` を実行したり、全 Pod の詳細を取得したりしないでください。共有前に証拠を確認し、機微情報を削除します。

リソース圧力を調べるときは、requests/limits、ノードの割り当て可能リソース、Metrics Server がある場合は `kubectl top` を比較します。アクセス可能なノードでは `df -h` と `df -i` の両方を確認します。空きバイト数があっても inode 枯渇は起こり得ます。ノードデバッグ Pod に固有の root filesystem があり、ホストの root は `/host` にマウントされています。対象パスを指定せずに `df -h` を実行すると、別の filesystem を調べる場合があります。この種の Pod を作成するには、レビュー済みの namespace、イメージ、debug profile、権限、cleanup が必要です。

ネットワーク診断では、送信元 Pod/namespace/ノード、宛先、protocol、port を特定します。最初に適用対象の policy と送信元の resolver を確認してください。新しく作った debug Pod は、問題の workload と label、identity、DNS、routing が異なる場合があります。ICMP ping の成功は、TCP/UDP アプリケーションに到達できる証明にはなりません。許可された経路で範囲を限定してテストし、名前の衝突する unpinned `dnsutils`/`netshoot` Pod を何度も作らず、所有者と相談してツールと cleanup を準備します。

参考資料: [EKS トラブルシューティング](https://docs.aws.amazon.com/eks/latest/userguide/troubleshooting.html)、[Kubernetes logs](https://kubernetes.io/docs/reference/kubectl/generated/kubectl_logs/)、[ノードデバッグ](https://kubernetes.io/docs/tasks/debug/debug-cluster/kubectl-node-debug/)。

## クラスターの作成と管理に関する問題 {#cluster-creation-and-management-issues}

![クラスターの作成、endpoint アクセス、削除に関する症状と調査すべき仮説。](../.gitbook/assets/en-eks-09-eks-troubleshooting-1.png)

[🔍 インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-09-eks-troubleshooting-1.html)

### クラスター作成の失敗

#### よくある原因

正確な失敗リクエストまたは CloudFormation event を調べ、呼び出し元の権限、クラスター service role の信頼関係と policy、service quota、サポートされる subnet/AZ の選択、IP 容量、名前の競合、service の可用性を確認します。これらは仮説であり、実際のエラーによって可能性が異なります。

#### トラブルシューティング手順

```bash
set -euo pipefail
: "${AWS_REGION:?}"; : "${CLUSTER_ROLE_NAME:?}"; : "${VPC_ID:?}"
aws sts get-caller-identity
aws iam get-role --role-name "$CLUSTER_ROLE_NAME" \
  --query 'Role.{Arn:Arn,Trust:AssumeRolePolicyDocument}'
aws iam list-attached-role-policies --role-name "$CLUSTER_ROLE_NAME"
aws iam list-role-policies --role-name "$CLUSTER_ROLE_NAME"
aws ec2 describe-subnets --region "$AWS_REGION" --filters "Name=vpc-id,Values=$VPC_ID" \
  --query 'Subnets[].{Id:SubnetId,AZ:AvailabilityZone,AZId:AvailabilityZoneId,AvailableIPs:AvailableIpAddressCount,CIDR:CidrBlock}'
aws service-quotas list-service-quotas --service-code eks --region "$AWS_REGION"
aws cloudtrail lookup-events --region "$AWS_REGION" \
  --lookup-attributes AttributeKey=EventName,AttributeValue=CreateCluster \
  --max-items 20 --output json
```

アタッチされた policy だけでは呼び出し元の実効権限を判断できません。inline policy、permissions boundary、session policy、Organizations の制御も含めて確認してください。`AmazonEKSClusterPolicy` は EKS クラスターの service role に付与するものです。人の IAM user に付けても、必要な `eks:CreateCluster`/`iam:PassRole` 権限や Kubernetes アクセスは与えられません。service-linked role の作成にも、独自の権限とライフサイクルがあります。

ネットワークの確認には、選択したクラスター subnet と正確な route/security group/NACL 設定を使います。クラスター subnet の要件と、ノード/Pod/LB のアドレス容量計画は別の課題です。private cluster は、NAT gateway や一般的なインターネット接続なしで必要な service endpoint を使える場合があります。`kubernetes.io/cluster/...` subnet tag は、コントロールプレーン作成に対する万能の修正ではありません。

quota エラーでは、エラーに記載された service/quota を特定し、増枠を申請する前に現在の適用値を照会します。EKS cluster quota、EC2 vCPU/instance family quota、VPC 制限はそれぞれ別です。「limit is 5」のような過去のメッセージは例であり、現在のアカウント上限ではありません。

#### よくある解決策

インフラストラクチャの所有者を通じ、確認できた権限、service role の信頼関係、subnet 選択、IP 割り当て、quota の問題だけを修正してから、再試行を検討します。`UnsupportedAvailabilityZoneException` は、指定されたクラスター subnet がそのアカウントで EKS をサポートしない AZ にあることを示します。例外で報告されたサポート対象 AZ を使ってください。EC2 instance type の提供状況だけから原因を判断するものではありません。

service event がないか AWS Health を確認します。別リージョンへの変更は別個の配置、データ、ネットワーク設計であり、クラスターも追加で作成される可能性があります。既定のトラブルシューティング再試行ではありません。`eksctl create cluster --verbose ...` と AWS CLI の debug flag も、実際にクラスターを作成します。新しい provisioning request を出す前に、既存の stack event と request ID を確認します。

### クラスター endpoint へのアクセス問題

#### DNS、transport、TLS、認証、認可を切り分ける

endpoint mode、許可された public CIDR、cluster security group を調べ、クラスター CA と timeout を指定してテストします。

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${EVIDENCE_PARENT:?}"
umask 077
ENDPOINT_DIR=$(mktemp -d "$EVIDENCE_PARENT/eks-endpoint.XXXXXXXX")
aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --output json > "$ENDPOINT_DIR/cluster.json"
jq -er '.cluster.certificateAuthority.data' "$ENDPOINT_DIR/cluster.json" \
  | base64 --decode > "$ENDPOINT_DIR/cluster-ca.crt"
ENDPOINT=$(jq -er '.cluster.endpoint' "$ENDPOINT_DIR/cluster.json")
jq '.cluster.resourcesVpcConfig | {endpointPublicAccess,endpointPrivateAccess,publicAccessCidrs,clusterSecurityGroupId,vpcId}' \
  "$ENDPOINT_DIR/cluster.json"
curl --silent --show-error --connect-timeout 5 --max-time 10 \
  --cacert "$ENDPOINT_DIR/cluster-ca.crt" --output /dev/null \
  --write-out 'HTTP status: %{http_code}\n' "$ENDPOINT"
```

この操作では Kubernetes bearer token を送りません。401/403 応答は、アクセスを拒否されたとしても DNS/TCP/TLS が到達できたことを示す場合があります。HTTP 応答に成功しても、アプリケーションの正常性を証明しません。`curl -k` は証明書検証の失敗を隠します。DNS lookup が必要な場合は、endpoint URL の `https://` URL 全体を `nslookup` に渡さず、hostname を使います。

public endpoint では、クライアントの実際の egress/NAT address が許可 CIDR に含まれるかを確認します。private endpoint では、VPC/接続済みネットワークの経路、DNS 解決、security group access を調べます。interface endpoint `com.amazonaws.<region>.eks` が提供するのは **EKS 管理 API** であり、Kubernetes API server ではありません。有効化しただけでは kubectl のアクセスは修復されません。クラスターの Kubernetes private endpoint は別のものです。

#### kubeconfig と権限

資格情報そのものを表示せず、context 名と server を調べます。診断用の kubeconfig を別に作成するには、明示的な path と alias を使います。`NAMESPACE` には意図した認可範囲を設定します。

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"
: "${NAMESPACE:?Set the namespace for the authorization check}"
: "${DIAGNOSTIC_KUBECONFIG:?Set a separate writable kubeconfig path}"
: "${KUBE_CONTEXT:?Choose an explicit alias for this cluster}"
umask 077
aws eks update-kubeconfig --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --kubeconfig "$DIAGNOSTIC_KUBECONFIG" --alias "$KUBE_CONTEXT"
export KUBECONFIG="$DIAGNOSTIC_KUBECONFIG"
kubectl --context "$KUBE_CONTEXT" auth can-i get pods --namespace "$NAMESPACE"
```

kubeconfig の作成には `eks:DescribeCluster` が必要です。Kubernetes の認証/認可は別途必要です。role を引き受ける場合は、レビュー済みの `--role-arn` と、その信頼関係/STS 権限を使います。session token を表示せず、設定済み SSO session など、実際の credential provider を通じて資格情報を更新します。

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"
aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query 'cluster.accessConfig'
# Use the next command when API or API_AND_CONFIG_MAP authentication is enabled.
aws eks list-access-entries --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION"
```

access-entry 認証が有効な場合は、該当する entry と関連する policy の範囲を確認します。従来の `CONFIG_MAP` や混合 mode では `aws-auth` も使われる場合があります。既存の node mapping を保持し、計画的に移行してください。一般的な access 修正として `system:masters` を付与したり、ConfigMap 全体を上書きしたりしないでください。IRSA の IAM OIDC provider は workload の AWS 資格情報用であり、人の IAM principal に Kubernetes 認可を与える mapping ではありません。

#### 正しいアクセス経路を修正する

接続済みの private 管理経路、または endpoint mode に合ったレビュー済み public CIDR allow-list を使います。診断コマンドを動かすためだけに `0.0.0.0/0` を開放しないでください。public access を削除する前に private path をテストし、無関係な VPC 設定を保持し、設定更新の update ID を追跡します。計画的な変更には[セキュリティ章の endpoint 手順](./05-eks-security.md)を参照してください。

#### ワンクリック CloudShell access

2026年4月30日に発表されたワンクリック機能が利用できます。クラスター詳細ページで **Connect** を選ぶと、kubectl が設定された CloudShell が開きます。public と private の両 API endpoint に対応しています。private endpoint の場合、CloudShell VPC environment が自動で起動し、その名前の入力が求められます。この機能自体の追加料金は EKS リージョンでは発生しません。

ただし、コンソール経由でも該当する IAM/CloudShell/VPC environment 権限、Kubernetes access、動作する network 設定が必要です。ローカル設定が不要になるだけで、認可確認はなくなりません。該当するリソース/データ転送の料金と、session の identity を確認してからコマンドを実行してください。

参考資料: [kubeconfig と CloudShell](https://docs.aws.amazon.com/eks/latest/userguide/create-kubeconfig.html)、[ワンクリック機能のお知らせ](https://aws.amazon.com/about-aws/whats-new/2026/04/amazon-eks-one-click-cluster-access/)、[EKS PrivateLink の違い](https://docs.aws.amazon.com/eks/latest/userguide/vpc-interface-endpoints.html)、[EKS クラスタートラブルシューティング](https://docs.aws.amazon.com/eks/latest/userguide/troubleshooting.html)。

### クラスター削除の問題

#### 削除を妨げる依存関係を特定する

クラスター削除は意図的な teardown であり、一般的なトラブルシューティング手段ではありません。正確な EKS/CloudFormation error、cluster ARN/account/Region、update state、deletion-protection 設定を確認します。deletion protection とインストール済み EKS Capabilities は、マネージドノードグループや Fargate profile 以外にも削除を妨げる場合があります。削除が完了するまでクラスターの IAM/service role を保持します。

選択したクラスターを一覧し、endpoint が明示した kubectl context と一致するか確認します。以下は読み取り専用のコマンドであり、削除対象を自動選択しません。

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the cluster being deliberately retired}"
: "${AWS_REGION:?}"; : "${KUBE_CONTEXT:?}"; : "${EXPECTED_ACCOUNT_ID:?}"
ACTUAL_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
if [ "$ACTUAL_ACCOUNT_ID" != "$EXPECTED_ACCOUNT_ID" ]; then
  echo "Account mismatch; stop" >&2
  exit 1
fi
aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query 'cluster.{arn:arn,status:status,deletionProtection:deletionProtection,endpoint:endpoint}'
kubectl config view --context "$KUBE_CONTEXT" --minify \
  -o jsonpath='{.clusters[0].cluster.server}{"\n"}'
# Compare the endpoints before inspecting Kubernetes resources.
kubectl --context "$KUBE_CONTEXT" get services -A \
  -o custom-columns='NAMESPACE:.metadata.namespace,NAME:.metadata.name,TYPE:.spec.type,CLASS:.spec.loadBalancerClass,ADDRESS:.status.loadBalancer.ingress'
kubectl --context "$KUBE_CONTEXT" get ingress -A
kubectl --context "$KUBE_CONTEXT" get pvc -A
kubectl --context "$KUBE_CONTEXT" get pv \
  -o custom-columns='NAME:.metadata.name,CLAIM_NS:.spec.claimRef.namespace,CLAIM:.spec.claimRef.name,RECLAIM:.spec.persistentVolumeReclaimPolicy,DRIVER:.spec.csi.driver,HANDLE:.spec.csi.volumeHandle'
aws eks list-nodegroups --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION"
aws eks list-fargate-profiles --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION"
aws eks list-capabilities --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION"
aws eks list-addons --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION"
```

Service の `EXTERNAL-IP` 出力だけでは所有者を特定できません。controller 管理の `LoadBalancer` Service、手動設定の external IP、その他の Service type を区別します。namespace/name/UID、controller の所有関係、AWS resource ARN、関連 tag を記録します。controller がインストールされている場合は Ingress、Gateway/TargetGroupBinding resource も含め、target や load balancer が共有されていないか確認します。

#### 所有者が定めた順序でリソースを廃止する

1. traffic と workload を移行し、アプリケーション整合性のある backup/restore とデータ保持要件を確認します。PVC YAML を保存してもデータの backup にはなりません。`Delete` reclaim policy では claim 削除時に保存先が削除される場合があります。`Retain` ではデータ/ストレージの扱いを別途決める必要があります。
2. 必要な load-balancer controller が動作している間に、load balancer を所有するレビュー済み Kubernetes resource だけを削除します。finalizer の処理を待ち、対応する AWS resource が解放されたことを確認します。ノードを削除する前に controller の IAM/依存関係の失敗を解消します。cleanup の失敗を隠すためだけに finalizer を削除しないでください。
3. EKS Capabilities は文書化された所有権/resource 削除の仕様に従って削除します。マネージドノードグループと Fargate profile をレビュー済みの順序で削除し、完了を待ちます。セルフマネージドノード/stack は別途 teardown が必要です。addon の削除で Kubernetes component も消える場合があります。依存する cleanup が終わるまで networking/storage controller を保持してください。
4. teardown を明示的に決定した場合に限り deletion protection を無効にし、元のインフラストラクチャ所有者を通じてクラスターを削除します。Auto Mode ではクラスター削除に伴いマネージドノードと load balancer も削除されます。その範囲と組み込み TargetGroupBinding の target-group lifecycle を考慮してください。
5. 専用 stack/VPC、volume/snapshot、load balancer、IAM resource、log、Prometheus scraper など、残るリソースを正確な所有者ごとに確認します。共有リソースと保持データはそれぞれ独立した lifecycle があり、料金が継続する場合があります。

例として、以下は先行する traffic/data 確認後に明示的に選択した Service 1つを削除します。リソースを検出しながら一括削除する処理ではありません。

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${SERVICE_NAMESPACE:?}"; : "${SERVICE_NAME:?}"
# Separate approved teardown step after traffic/data migration and owner review.
kubectl --context "$KUBE_CONTEXT" -n "$SERVICE_NAMESPACE" get service "$SERVICE_NAME" -o yaml
kubectl --context "$KUBE_CONTEXT" -n "$SERVICE_NAMESPACE" delete service "$SERVICE_NAME" \
  --wait=true --timeout=10m
```

timeout になっても AWS load balancer が保持された、または削除された証明にはなりません。finalizer、controller event、該当する AWS ARN を確認します。Kubernetes と AWS の resource cleanup は異なるタイミングで完了する場合があります。

#### 削除エラーと force 動作

EKS update の詳細と CloudFormation stack event を使い、依存関係、認可、処理中 operation の失敗を特定します。eksctl 0.229 では `delete cluster --force` が有効で、エラー発生時にも削除を続けられます。これは cleanup の完了や orphan の所有者を安全に特定した証明ではありません。`--disable-nodegroup-eviction` は別の option で、削除によって PDB の確認を迂回します。どちらも既定の障害対応にしないでください。

account/Region 全体の ELB/ELBv2 一覧を delete command に pipe したり、依存関係エラーを解消するために全 Service、PVC、namespace を削除したりしないでください。orphan を手動削除する必要がある場合は、まず正確な cluster/stack の所有者とデータ/traffic への影響を確定し、該当 service のレビュー済み teardown 手順を使います。

参考資料: [EKS クラスター削除](https://docs.aws.amazon.com/eks/latest/userguide/delete-cluster.html)、[削除トラブルシューティング](https://repost.aws/knowledge-center/eks-delete-cluster-issues)、[persistent volume の lifecycle](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)。

## ネットワークに関する問題 {#networking-issues}

![Pod 間通信、Service access、load balancing、DNS、CNI/IP 割り当てに分類したネットワーク上の症状。](../.gitbook/assets/en-eks-09-eks-troubleshooting-2.png)

[🔍 インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-09-eks-troubleshooting-2.html)

最初に実際のコンピューティング/data plane を特定します。open-source VPC CNI を使う標準 EC2 ノード、Fargate、Auto Mode では、agent も設定方法も同じではありません。Auto Mode では `NodeClass` の networking control を使います。`aws-node` DaemonSet や `ENIConfig` を変更しても Auto Mode node は設定されません。

### Pod 間通信の問題

#### 失敗している経路を追跡する

送信元/宛先 Pod、namespace、node/AZ、IP family、protocol、宛先 port を記録します。承認済みのテストで違いを切り分けられる場合は、同一ノード内とノード間の動作を比較します。その経路に対して policy、security group、route/NACL、CNI state、IP 割り当て、path MTU を確認します。

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${POD_NAME:?}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pod "$POD_NAME" -o wide
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pod "$POD_NAME" \
  -o jsonpath='{.metadata.labels}{"\n"}{.spec.nodeName}{"\n"}{.spec.hostNetwork}{"\n"}'
kubectl --context "$KUBE_CONTEXT" get namespace "$NAMESPACE" --show-labels
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get networkpolicies
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get events \
  --sort-by='.metadata.creationTimestamp'
```

標準の `networking.k8s.io/v1` NetworkPolicy は許可 traffic を加算します。priority や「最後に評価した policy が勝つ」という動作はありません。送信元と宛先の両方が隔離されている場合は、送信元の egress と宛先の ingress がその通信を許可する必要があります。admin/cluster-wide policy API や vendor 固有 policy engine は別の仕様です。namespace label と、`namespaceSelector`/`podSelector` が同じ peer 内の AND 条件か、別 peer の OR 条件かも確認します。

VPC CNI は native network-policy enforcement に対応しています。third-party policy Pod が見当たらないという理由だけで Calico/Cilium をインストールしないでください。対応する CNI/platform/kernel と、有効になっている policy-agent 設定を確認します。標準 startup mode では、policy が設定されるまで新規 Pod の traffic が一時的に許可されます。strict mode では起動時から deny されるため、必要な DNS/dependency policy が必要です。host-network の動作やその他の適用範囲には、利用する実装に固有の制限があります。

標準 VPC CNI installation で対象 container がある場合は、実際の `aws-node` Pod の `aws-network-policy-agent` log を調べます。`kubectl get pods -l ...` が成功しても一覧が空なら、plugin がインストールされている証拠にはなりません。Auto Mode では組み込み policy control を使います。

#### 意図した通信だけを修正する

namespace 全体の allow-all ingress/egress を追加したり policy を削除したりせず、許可する通信の全体像をレビューします。次の例は backend API Pod を選択し、frontend の web Pod からの TCP 8080 だけを許可します。

```yaml
# Example ingress policy only: review both peers and the complete allowed-flow matrix.
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-from-web
  namespace: backend
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: frontend
          podSelector:
            matchLabels:
              app: web
      ports:
        - protocol: TCP
          port: 8080
```

この policy を適用すると、他の policy で許可しない限り、選択した backend Pod への別の ingress も隔離されます。client egress、DNS、すべての依存先は設定しません。それらは別々に positive/negative test で確認します。例の namespace/name をそのままコピーせず、実際の workload を使ってください。

security group については、該当する場合は Pod group/custom Pod subnet も含め、送信元と宛先 ENI の group を調べます。必要な送信元/port だけを所有者経由で許可してください。一般的な修正として全 protocol や広範な CIDR を追加しないでください。MTU の 1500 や 9001 は path に依存する値です。CNI 設定を変更したり Pod を置換したりする前に、失敗を測定して encapsulation を考慮します。

### Service access の問題

Service selector、実際の Pod readiness、endpoint condition、port mapping を合わせて確認します。

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${SERVICE_NAME:?}"
SERVICE_JSON=$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get service "$SERVICE_NAME" -o json)
printf '%s\n' "$SERVICE_JSON" | jq '{metadata: {name: .metadata.name, namespace: .metadata.namespace}, spec: .spec, status: .status}'
SELECTOR=$(printf '%s\n' "$SERVICE_JSON" | jq -r '(.spec.selector // {}) | to_entries | map("\(.key)=\(.value)") | join(",")')
if [ -n "$SELECTOR" ]; then
  kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pods -l "$SELECTOR" -o wide
  kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pods -l "$SELECTOR" -o json \
    | jq '.items[] | {name:.metadata.name,phase:.status.phase,ready:[.status.conditions[]? | select(.type=="Ready")],containers:.status.containerStatuses}'
else
  printf 'No selector: inspect ExternalName or explicitly managed EndpointSlices as applicable.\n'
fi
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get endpointslices \
  -l "kubernetes.io/service-name=$SERVICE_NAME" -o yaml
```

非推奨の Endpoints API に頼らず EndpointSlice を確認します。`ready`、`serving`、`terminating` condition と、`publishNotReadyAddresses`、`externalTrafficPolicy`、`internalTrafficPolicy` などの Service option を調べます。Pod が Running でも Ready とは限りません。

`ExternalName` Service では選択対象 Pod を探すのではなく DNS alias を調べます。headless Service の `clusterIP: None` は意図した設定です。selector のない Service では、所有者が管理する EndpointSlice を使う場合があります。Service の `port` は `targetPort` と異なることがあります。container port を宣言しても、アプリケーションがそこで listen するとは限りません。

label や port が誤っている場合、release 設定を通じて、所有 controller が管理する Service/Pod template を修正します。controller 管理 Pod 1つだけに label を付け直しても恒久対策にはなりません。patch 前に port 一覧全体と immutable field を確認します。原因を調べる前に Service を削除/再作成したり、ClusterIP を変更したり、すべての kube-proxy Pod を再起動したりしないでください。

同じ送信元と protocol を使い、policy で許可された場合に限って Pod 直通と Service 経由の接続を比較します。iptables/nftables/eBPF の動作を調べる前に、data plane が kube-proxy、別実装、Auto Mode のどれかを確認してください。kube-proxy Pod がないことは、常に障害を意味するわけではありません。

### Load balancer の問題

Service/Ingress class、annotation、所有者から controller を特定します。標準の AWS Load Balancer Controller と EKS Auto Mode では、class/API と lifecycle rule が異なります。その所有者について controller event、subnet 選択、IAM、security group、target 登録、health check を確認してください。

workload に関連する正確な load balancer と target group の ARN を使います。

```bash
set -euo pipefail
: "${AWS_REGION:?}"; : "${LOAD_BALANCER_ARN:?}"; : "${TARGET_GROUP_ARN:?}"
aws elbv2 describe-load-balancers --region "$AWS_REGION" \
  --load-balancer-arns "$LOAD_BALANCER_ARN"
aws elbv2 describe-tags --region "$AWS_REGION" \
  --resource-arns "$LOAD_BALANCER_ARN" "$TARGET_GROUP_ARN"
aws elbv2 describe-load-balancer-attributes --region "$AWS_REGION" \
  --load-balancer-arn "$LOAD_BALANCER_ARN"
aws elbv2 describe-target-groups --region "$AWS_REGION" \
  --target-group-arns "$TARGET_GROUP_ARN"
aws elbv2 describe-target-health --region "$AWS_REGION" \
  --target-group-arn "$TARGET_GROUP_ARN"
```

`describe-load-balancer-attributes` は属性を表示し、稼働状態は表示しません。状態は `describe-load-balancers` で確認します。target health reason code、health-check protocol/port/path、listener/rule routing、application response を調べます。instance target は通常 node/NodePort に到達し、IP target は Pod target port に到達します。security group rule を実際の経路に合わせます。

subnet role tag は自動検出に影響します。public/internal scheme、route table、空き IP、AZ coverage を確認してください。同じ subnet に public と private の両 role tag を付けても修正にはなりません。明示的な subnet 選択や controller version によって tag 要件が変わる場合があります。health check の失敗を回避するために frontend/backend security group を `0.0.0.0/0` に開放しないでください。

所有者が管理する現在の scheme/type 設定を使います。古い `aws-load-balancer-internal` や `aws-load-balancer-type: nlb` の例は、現在の controller class と同じ意味ではありません。controller の所有者や LB scheme の変更には、計画的な置換と traffic 移行が必要な場合があります。annotation を編集しても、その場で変換されるとは限りません。Auto Mode は self-managed controller が既に管理している load balancer を引き継ぎません。

Service 削除により load balancer も削除される場合があります。export した Service YAML だけでは、traffic/data rollback の全手順にはなりません。手動で ALB を作っても Kubernetes Service には自動接続されません。所有者を決めたうえで[ネットワークガイド](./03-eks-networking-part2.md)を確認します。

### DNS の問題

#### 影響を受けた Pod が使う resolver を調べる

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${POD_NAME:?}"; : "${CONTAINER_NAME:?}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pod "$POD_NAME" \
  -o jsonpath='{.spec.dnsPolicy}{"\n"}{.spec.dnsConfig}{"\n"}{.spec.hostNetwork}{"\n"}'
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$POD_NAME" \
  -c "$CONTAINER_NAME" -- cat /etc/resolv.conf
# Where this container actually includes nslookup, test the intended name.
: "${DNS_TEST_NAME:?Set the intended Service FQDN or reviewed external hostname}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$POD_NAME" \
  -c "$CONTAINER_NAME" -- nslookup "$DNS_TEST_NAME"
```

イメージに shell や DNS tool がない場合、それは tool 上の制限であって、DNS query が失敗した証拠ではありません。関連するネットワーク/identity context を維持する、レビュー済みの debug 手段を準備します。新しい debug Pod では DNS/policy 設定が異なる場合があります。

標準 non-Auto node では、インストール済み CoreDNS Deployment/Service、設定、EndpointSlice を確認します。

```bash
kubectl --context "$KUBE_CONTEXT" -n kube-system get deployment coredns
kubectl --context "$KUBE_CONTEXT" -n kube-system get pods -l k8s-app=kube-dns -o wide
kubectl --context "$KUBE_CONTEXT" -n kube-system get service kube-dns
kubectl --context "$KUBE_CONTEXT" -n kube-system get endpointslices \
  -l kubernetes.io/service-name=kube-dns
kubectl --context "$KUBE_CONTEXT" -n kube-system get configmap coredns -o yaml
kubectl --context "$KUBE_CONTEXT" -n kube-system logs -l k8s-app=kube-dns \
  --all-containers=true --prefix=true --since=15m --tail=100
```

**Auto Mode node** では CoreDNS が node system service として動作します。Auto Mode のみのクラスターは、従来の CoreDNS Deployment なしで動作できます。Auto/non-Auto 混在クラスターでは、non-Auto node 用に Deployment を残す必要があります。Auto Mode の対処として NodeLocal DNSCache をインストールしたり、存在しない Deployment を再起動したりしないでください。

Pod の nameserver、CoreDNS/NodeLocal の upstream、VPC resolver を区別します。`169.254.20.10` はよく使われる NodeLocal DNSCache address であり、すべての環境で共通の VPC DNS server ではありません。`8.8.8.8` などの public resolver は Kubernetes Service zone や private AWS DNS の代替になりません。

```bash
set -euo pipefail
: "${AWS_REGION:?}"; : "${VPC_ID:?}"
aws ec2 describe-vpc-attribute --region "$AWS_REGION" --vpc-id "$VPC_ID" \
  --attribute enableDnsSupport
aws ec2 describe-vpc-attribute --region "$AWS_REGION" --vpc-id "$VPC_ID" \
  --attribute enableDnsHostnames
aws ec2 describe-vpcs --region "$AWS_REGION" --vpc-ids "$VPC_ID" \
  --query 'Vpcs[].{VpcId:VpcId,DhcpOptionsId:DhcpOptionsId}'
```

DNS attribute の確認には `describe-vpc-attribute` を使います。`describe-vpcs` の戻り値には含まれません。DHCP option は返された ID を使って照会します。他の workload への影響を確認せずに、共有 VPC の DHCP 設定を置き換えないでください。

#### 対象を絞った DNS 修正を適用する

必要に応じて UDP/TCP 53、実際の CoreDNS readiness/configuration、upstream 到達性、DNS policy、独自の search 設定を確認します。cluster DNS を使う意図で `hostNetwork` Pod を動かす場合は、通常 `ClusterFirstWithHostNet` が必要です。`dnsPolicy: None` では resolver を意図どおり完全に設定しなければなりません。DNS だけを許可する egress policy でも、別 policy が許可しない限り、選択された Pod の他の egress は隔離されます。

所有者が管理する Corefile の独自設定を保持し、addon のサポート対象 configuration schema を使います。CoreDNS の replica/resources/PDB/scheduling と、autoscaling の所有者を確認してから scale/restart します。DNS Pod をすべて削除したり、推測した「latest」image を最初の対処としてインストールしたりしないでください。update ID を記録し、実際に DNS が機能することを確認します。

### VPC CNI の問題

以下は**open-source VPC CNI を使う標準 EC2 node** の調査手順です。`kubectl exec` は label selector を受け付けないため、対象 Pod を明示します。

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NODE_NAME:?}"
kubectl --context "$KUBE_CONTEXT" get node "$NODE_NAME" \
  -o jsonpath='{.spec.providerID}{"\n"}{.status.nodeInfo}{"\n"}{.status.allocatable.pods}{"\n"}'
kubectl --context "$KUBE_CONTEXT" -n kube-system get daemonset aws-node -o json \
  | jq '.spec.template.spec | {containers:[.containers[] | {name,image,args,env}],initContainers:[.initContainers[]? | {name,image,args,env}]}'
kubectl --context "$KUBE_CONTEXT" -n kube-system get pods \
  -l k8s-app=aws-node --field-selector "spec.nodeName=$NODE_NAME" -o wide
kubectl --context "$KUBE_CONTEXT" get pods -A \
  --field-selector "spec.nodeName=$NODE_NAME" -o wide
: "${AWS_NODE_POD:?Select the aws-node Pod on that exact node}"
kubectl --context "$KUBE_CONTEXT" -n kube-system logs "$AWS_NODE_POD" \
  -c aws-node --since=15m --tail=200
```

addon の `configurationValues`、DaemonSet の environment、関連する custom resource を確認します。`aws-node` ConfigMap にすべての設定があるとは限りません。node の `.spec.podCIDR` は VPC CNI Pod address の正確な一覧ではありません。実際の Pod IP、EC2 ENI、prefix、subnet を調べます。

```bash
set -euo pipefail
: "${AWS_REGION:?}"; : "${INSTANCE_ID:?Verify it from the selected node ProviderID}"
aws ec2 describe-instances --region "$AWS_REGION" --instance-ids "$INSTANCE_ID" \
  --query 'Reservations[].Instances[].{Id:InstanceId,Type:InstanceType,Subnet:SubnetId,SGs:SecurityGroups,ENIs:NetworkInterfaces}'
: "${SUBNET_ID:?Set the actual node or custom Pod subnet being investigated}"
aws ec2 describe-subnets --region "$AWS_REGION" --subnet-ids "$SUBNET_ID" \
  --query 'Subnets[].{Id:SubnetId,CIDR:CidrBlock,AvailableIPs:AvailableIpAddressCount}'
: "${INSTANCE_TYPE:?Set the selected instance type}"
aws ec2 describe-instance-types --region "$AWS_REGION" --instance-types "$INSTANCE_TYPE" \
  --query 'InstanceTypes[].{Type:InstanceType,Network:NetworkInfo}'
```

有効な場合、IPAMD introspection は node で設定された introspection endpoint（通常 loopback の port 61679）にあります。必要な tool がある、許可された node/agent 診断手段を使ってください。CNI image に curl がないことは IPAM の障害ではありません。

#### 割り当て上限を切り分ける

- **subnet の枯渇/断片化:** 空き address と prefix を比較します。prefix delegation には対応 instance/configuration と、連続した prefix block が必要です。空き IP の合計だけでは `/28` を割り当てられる証拠になりません。
- **instance の ENI/IP 上限:** `NetworkInfo` と既存 ENI を確認します。node group の desired/min/max を拡張しても node 数が変わるだけで、instance type や instance あたりの上限は変わりません。instance configuration の変更には、レビュー済みの新しい group、または元の launch-template を使ったサポート対象の更新経路を使います。
- **custom networking:** 有効化前に、対応する `ENIConfig`、Pod subnet/security group、node selector を準備します。secondary ENI/Pod IP の割り当て元は変わりますが、容量が無制限になるわけではありません。
- **warm target:** `WARM_IP_TARGET` は空き IP の余裕を制御し、`MINIMUM_IP_TARGET` は割り当て済み総 IP 数の下限を定めます。文書化されたとおり、これらは warm-ENI の動作を上書きします。また prefix mode で IP/minimum target を設定すると warm-prefix の動作にも影響します。warm headroom を正の値にしないまま minimum だけを指定すると、その後の割り当てを妨げる場合があります。根拠のない 1/2/5 の値をコピーせず、workload/IP budget から決めます。
- **identity/所有権:** 実際の CNI IRSA/Pod Identity、または該当する node role と IPv4/IPv6 policy を確認します。すべての node role に IPv4 CNI policy を付けても、万能な対処にはなりません。

Auto Mode では `NodeClass` の subnet/security-group/policy control を使い、これらの warm-IP/ENI や `ENIConfig` の設定は受け付けません。管理されたネットワーク model を維持してください。

CNI の所有者を通じ、サポート対象の中間 version と configuration schema に従って、レビュー済みの version/configuration を適用します。正確な addon update を監視し、完了後にネットワークを検証するには[アップグレードガイド](./08-eks-upgrades.md)を使ってください。container image を1つだけ置き換えたり、設定を無条件に上書きしたり、IP 割り当て失敗を隠すために全 workload を再起動したりしないでください。

参考資料: [VPC CNI policy 設定](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy-configure.html)、[Auto Mode networking](https://docs.aws.amazon.com/eks/latest/userguide/auto-networking.html)、[custom networking](https://docs.aws.amazon.com/eks/latest/best-practices/custom-networking.html)、[CNI 設定](https://github.com/aws/amazon-vpc-cni-k8s)、[Kubernetes NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)、[EndpointSlice](https://kubernetes.io/docs/concepts/services-networking/endpoint-slices/)。

## ノードと Pod に関する問題 {#node-and-pod-issues}

![node、Pod のリソース、kubelet、network、workload、scaling の仮説に関する症状。](../.gitbook/assets/en-eks-09-eks-troubleshooting-3.png)

[🔍 インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-09-eks-troubleshooting-3.html)

### Node NotReady の問題

#### condition と実際の node を調べる

`Ready=False` と `Ready=Unknown` では必要な証拠が異なります。kubelet/runtime の異常では failure が報告されますが、heartbeat が途絶えた場合は接続断や node の停止が考えられます。memory、disk、PID pressure は別個の condition であり、必ずしも `NotReady` を意味しません。label ひとつから原因を推測せず、condition の reason/time、lease、event を調べてください。

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NODE_NAME:?}"
NODE_JSON=$(kubectl --context "$KUBE_CONTEXT" get node "$NODE_NAME" -o json)
printf '%s\n' "$NODE_JSON" | jq '{name:.metadata.name,uid:.metadata.uid,labels:.metadata.labels,providerID:.spec.providerID,taints:.spec.taints,unschedulable:.spec.unschedulable,nodeInfo:.status.nodeInfo,conditions:.status.conditions,capacity:.status.capacity,allocatable:.status.allocatable}'
NODE_UID=$(printf '%s\n' "$NODE_JSON" | jq -er '.metadata.uid')
kubectl --context "$KUBE_CONTEXT" get events -A --field-selector "involvedObject.uid=$NODE_UID" \
  --sort-by='.metadata.creationTimestamp'
kubectl --context "$KUBE_CONTEXT" get pods -A --field-selector "spec.nodeName=$NODE_NAME" -o wide
```

EC2 を確認するときは正確な ProviderID を使います。IP を `grep` して一致させると別の resource を選ぶ可能性があります。マネージドノードグループでは health、image/release、repair 設定を確認します。

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${NODEGROUP_NAME:?}"
aws eks describe-nodegroup --cluster-name "$CLUSTER_NAME" --nodegroup-name "$NODEGROUP_NAME" \
  --region "$AWS_REGION" \
  --query 'nodegroup.{status:status,health:health,version:version,releaseVersion:releaseVersion,amiType:amiType,nodeRepairConfig:nodeRepairConfig,updateConfig:updateConfig,scalingConfig:scalingConfig}'
```

node access がサポートされる場合は、基本節の remote-session 手順で kubelet/containerd journal、networking、disk byte/inode、memory を調べます。秘密鍵を表示せず、実際に設定された certificate/kubeconfig path を確認してください。`kubeadm certs renew` は EKS managed control plane の修復ではなく、`eksctl replace nodegroup` はサポート対象の eksctl command ではありません。AL2023 は nodeadm 設定を使います。すべての image に AL2 の `/etc/eks/bootstrap.sh` 手順を再実行しないでください。

#### 復旧と自動 repair

証拠を保存してから、所有者が管理する復旧操作を選びます。kubelet/containerd の再起動、reboot、node 置換は workload に影響し、継続中の IAM/network/bootstrap 問題は解決しない場合があります。reboot API の応答は instance や kubelet の復旧を意味しません。uncordon する前に、同じ node/instance と workload を確認してください。

計画的な置換では、capacity、stateful data、PDB、置換リソースの所有者を確認します。選択した node 1台を timeout 付きで drain します。

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?Set the reviewed cluster context}"
: "${NODE_NAME:?Set one reviewed old node}"
kubectl --context "$KUBE_CONTEXT" get node "$NODE_NAME" -o wide
kubectl --context "$KUBE_CONTEXT" get node "$NODE_NAME" \
  -o jsonpath='{.spec.providerID}{"\n"}'
kubectl --context "$KUBE_CONTEXT" get pods --all-namespaces \
  --field-selector "spec.nodeName=$NODE_NAME" -o wide
# Stop on failure. Do not terminate the instance or delete the node group here.
kubectl --context "$KUBE_CONTEXT" drain "$NODE_NAME" --ignore-daemonsets --timeout=10m
```

drain が失敗したら、EC2 termination に進んだり、既定で `emptyDir` data を破棄したりしないでください。途中まで drain された node は cordon 状態のままになる場合があります。PDB が保護するのは eviction path であり、すべてのインフラ障害、termination、controller scale-down ではありません。package を node 上で直接変更せず、マネージド置換については[node upgrade procedure](./08-eks-upgrades.md)を参照してください。

EKS automatic node repair は実在する別の機構です。Auto Mode では既定で有効です。managed node group では `nodeRepairConfig` を有効化でき、Karpenter には別の機能/設定要件があります。Node monitoring が追加 condition を報告しても、それだけで repair は有効になりません。現在の既定 table では、`Ready`、runtime、kernel、networking、storage の継続的な failure に対する置換が含まれますが、`MemoryPressure` と `DiskPressure` には**既定の repair action はありません**。repair threshold/parallelism、unhealthy-fleet/ARC control は新しい action を停止する場合がある一方、進行中 action は続く可能性があります。独自 Lambda、ASG tag、`maxUnavailable` が自動的にこの動作を提供すると約束しないでください。

### Pod が起動しない問題

#### state、event、所有 controller を読む

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${POD_NAME:?}"
POD_JSON=$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pod "$POD_NAME" -o json)
printf '%s\n' "$POD_JSON" | jq '{
  name:.metadata.name,uid:.metadata.uid,owners:.metadata.ownerReferences,
  node:.spec.nodeName,serviceAccount:.spec.serviceAccountName,
  imagePullSecrets:.spec.imagePullSecrets,
  containers:[.spec.containers[] | {name,image,imagePullPolicy,resources}],
  initContainers:[.spec.initContainers[]? | {name,image,resources}],
  phase:.status.phase,reason:.status.reason,message:.status.message,
  conditions:.status.conditions,containerStatuses:.status.containerStatuses,
  initContainerStatuses:.status.initContainerStatuses
}'
POD_UID=$(printf '%s\n' "$POD_JSON" | jq -er '.metadata.uid')
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get events \
  --field-selector "involvedObject.uid=$POD_UID" --sort-by='.metadata.creationTimestamp'
```

基本節にあるコンテナ別 log 手順を使います。`Pending`、`ContainerCreating`、image pull 待ち、init-container failure、readiness failure、`OOMKilled`、restart backoff はそれぞれ別の問題です。`CrashLoopBackOff` は container failure を繰り返した後の backoff 状態であり、root cause ではありません。

| 証拠 | 次に確認する項目 |
| --- | --- |
| image pull error | registry/name/tag/digest/architecture、node 側の DNS/TLS/route、rate limit、実際の pull identity |
| FailedScheduling | request と allocatable capacity、Pod 数、taint/affinity/topology、quota、PVC consumer 制約 |
| FailedMount / attach | PVC/PV/StorageClass、CSI/identity、AZ、現在の attachment。ストレージ節を参照 |
| OOMKilled / Evicted | container termination state、limit、node pressure、usage history。memory leak と決めつけない |
| Forbidden / admission failure | 正確な API actor、RBAC/admission policy。Pod list 権限を追加しても、無関係な registry/filesystem access は直らない |

`imagePullPolicy` を `Always` にしても、存在しない image や不正な資格情報は修正されません。laptop 上の Docker で image を pull しても、node の経路/identity は検証できません。また、Docker に読み込ませただけでは containerd runtime に自動で image が登録されません。

#### registry 資格情報と workload の変更

private ECR では、実際の node/Fargate execution identity と repository policy を確認します。application IRSA/Pod Identity は、起動前に image を pull する主体ではありません。private ECR の通信に ECR API/DKR と S3 への access が必要な場合があります。ECR endpoint は任意の registry への private access を提供しません。

image-pull Secret を必要とする registry では、正しい registry credential を含む、保護された自己完結型の Docker auth JSON file を使います。`.dockerconfigjson` や password を log/command argument に出さないでください。desktop の credential-helper 参照だけでは、kubelet が使える資格情報になりません。

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${DEPLOYMENT_NAME:?}"
: "${PULL_SECRET_NAME:?Choose an application-specific secret name}"
: "${DOCKER_CONFIG_JSON:?Provide a protected registry auth JSON file}"
# Separate reviewed change; an existing Secret causes create to fail rather than replacing it.
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" create secret generic "$PULL_SECRET_NAME" \
  --type=kubernetes.io/dockerconfigjson \
  --from-file=".dockerconfigjson=$DOCKER_CONFIG_JSON"
PATCH=$(jq -n --arg name "$PULL_SECRET_NAME" \
  '{spec:{template:{spec:{imagePullSecrets:[{name:$name}]}}}}')
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" patch deployment "$DEPLOYMENT_NAME" \
  --type=strategic --patch "$PATCH"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" rollout status \
  "deployment/$DEPLOYMENT_NAME" --timeout=5m
```

Secret は Pod と同じ namespace に置きます。strategic Pod-template patch は名前ごとに pull-secret entry を merge し、制御された Deployment rollout を開始します。release の所有権と他の設定を保持してください。既存 Pod の `imagePullSecrets` は一般に編集できる field ではありません。ServiceAccount の既定値は新たに admission される Pod に影響します。namespace 全体の default ServiceAccount を変えると、関係のない workload にも影響する場合があります。共有 Secret を定期的に削除/再作成せず、所有者を通じて期限切れの資格情報を更新します。

その他の設定変更では、controller の宣言済み template を修正し、rollout/readiness を確認します。適切な controller がなければ Pod を削除しても再作成されません。また、有用な証拠が失われる場合があります。debug 用 `--copy-to` Pod は application の副作用も複製し得ます。稼働中の application に package を追加するのではなく、権限と cleanup を明記した、レビュー済み診断手段と image を使ってください。

### リソース制約の問題

```bash
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get resourcequotas,limitranges
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pods -o wide
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" top pods --containers
kubectl --context "$KUBE_CONTEXT" top nodes
```

metrics command には Metrics Server と、動作する kubelet access が必要です。scheduler は現在の `kubectl top` 使用率ではなく、resource request と node allocatable capacity を使います。該当する場合は init container、Pod overhead、ephemeral storage、extended resource、Pod 数の上限も含めてください。namespace quota と LimitRange は別の制約です。

実測した workload の要件から必要だと判断できる場合に限り request を下げます。memory request を下げても `Insufficient pods` は修正されず、container が limit 内に収まる保証もありません。limit を上げると node pressure が高まる場合があります。log/cache を削除する前に disk/inode と image/filesystem 使用量を調べ、障害の証拠を保存します。

node 数を増やしても instance あたりの capacity は変わりません。managed group では、autoscaler と desired/min/max の設定を調整します。scaling 設定を縮小しても PDB は守られません。instance type を変える場合は、適切な新しい group または元の launch-template/version を使うサポート対象の手順を使います。Pod を scheduling させるためだけに taint、affinity、topology 制約を削除しないでください。

### autoscaling の問題

replica scaling（HPA）、resource の推奨/更新（VPA）、node provisioning（CA、Karpenter、Auto Mode）、application bottleneck を切り分けます。別の node provisioner が capacity を管理している場合、CA Pod がないのは正常です。

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get hpa -o json \
  | jq '.items[] | {name:.metadata.name,target:.spec.scaleTargetRef,min:.spec.minReplicas,max:.spec.maxReplicas,current:.status.currentReplicas,desired:.status.desiredReplicas,metrics:.status.currentMetrics,conditions:.status.conditions}'
kubectl --context "$KUBE_CONTEXT" get apiservice v1beta1.metrics.k8s.io
kubectl --context "$KUBE_CONTEXT" get --raw "/apis/metrics.k8s.io/v1beta1/namespaces/$NAMESPACE/pods"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get events \
  --sort-by='.metadata.creationTimestamp'
```

`AbleToScale`、`ScalingActive`、`ScalingLimited` などの HPA condition、現在の metric、behavior を確認します。desired と current replica が一時的に異なっても、直ちに障害とは限りません。CPU/memory utilization target には resource request が必要です。custom/external metric には各 API adapter または KEDA integration を使います。metric error によって scale-down が止まる場合があります。

CA では、インストール済み release、対応する Kubernetes minor、identity、discovery tag、unschedulable Pod の制約、node-group 上限/quota を調べます。CA は平均 node CPU が高いというだけで node を追加しません。Karpenter/Auto Mode では、対応する NodePool/NodeClaim/provider 上限と event を確認します。万能な対処として CA をインストールしないでください。

VPA では、推奨のみの `Off`、作成時に適用する `Initial`、意図的な update mode を区別します。`Auto` は非推奨で `Recreate` が代替です。mode 変更は workload を中断させ、同じ CPU/memory signal を使う HPA と競合する場合があります。API query の失敗だけでは VPA CRD がないと証明できません。

これは custom metric 設定ではなく、**resource metric** による HPA の例です。

```yaml
# Resource metrics example, not a custom/external-metrics adapter configuration.
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: app-hpa
  namespace: applications
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: app
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
```

70%/80%、replica 上限/下限、stabilization window は例示値であり、実測に基づく推奨値ではありません。対象 Deployment が存在し、適切な request と capacity が必要です。複数 metric がある場合、HPA は最大の replica 推奨値を選びます。memory behavior と adapter failure は workload ごとにテストしてください。replica scaling の所有者を1つにし、Terraform/GitOps が `.spec.replicas` を継続して元に戻さないようにします。

[autoscaling の概念](../core/09-cluster-administration.md)と、インストール済み controller の文書化された設定を参照してください。未レビューの `master` manifest を適用したり、node role に `AutoScalingFullAccess` を付けたりせず、実際の Helm value/identity と署名・固定した release を確認します。

参考資料: [EKS node repair](https://docs.aws.amazon.com/eks/latest/userguide/node-repair.html)、[Pod lifecycle](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/)、[private image pull](https://kubernetes.io/docs/tasks/configure-pod-container/pull-image-private-registry/)、[HPA](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)、[VPA](https://github.com/kubernetes/autoscaler/tree/master/vertical-pod-autoscaler)。

## IAM と認証に関する問題 {#iam-and-authentication-issues}

<!-- Audit 2026-09-11: parent diagram repair pending; see core-audit/eks-troubleshooting/diagram-review.json.
![IAM and Kubernetes authorization symptoms; use the cluster authentication mode and actual caller to select the diagnostic path.](../.gitbook/assets/en-eks-09-eks-troubleshooting-4.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-09-eks-troubleshooting-4.html)
-->

### クラスター access の拒否

AWS caller、EKS API 権限、kubeconfig/STS 認証、クラスター identity mapping、Kubernetes 認可を切り分けます。EKS control plane が使う IAM role は、オペレーターの role ではありません。AWS `DescribeCluster` に成功しても Kubernetes access は付与されません。

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"
aws sts get-caller-identity
aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query 'cluster.{arn:arn,endpoint:endpoint,access:accessConfig}'
kubectl config view --context "$KUBE_CONTEXT" --minify \
  -o jsonpath='{.contexts[0].name}{"\n"}{.clusters[0].cluster.server}{"\n"}'
kubectl --context "$KUBE_CONTEXT" auth can-i get pods -n "$NAMESPACE"
```

transport error では、access 節にある endpoint/CA 確認を使います。資格情報が失効した場合は、設定済み SSO/federated/assumed-role session を更新し、選択した profile/role を確認します。`sts get-session-token` は万能の更新 command ではありません。また、その出力を表示すると資格情報が漏れる場合があります。

identity mapping の仕組みを判断する前に、クラスターの authentication mode を調べます。

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${PRINCIPAL_ARN:?Set the exact IAM principal}"
# These APIs apply to clusters with API or API_AND_CONFIG_MAP authentication.
aws eks list-access-entries --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION"
aws eks describe-access-entry --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --principal-arn "$PRINCIPAL_ARN"
aws eks list-associated-access-policies --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --principal-arn "$PRINCIPAL_ARN"
```

API ベースの access では、正確な principal、entry type、Kubernetes group、access policy に関連付けられた namespace/cluster scope を確認します。`aws-auth` は `CONFIG_MAP` mode と mixed mode の legacy 側で使われます。`aws-auth` がないだけで、すべての access が壊れたとは限りません。既存の node mapping を保持し、authentication mode を変更する前に文書化された移行方法を使います。

一般的な修正として `aws-auth` を短い例で置き換えたり、`system:masters` を付与したりしないでください。namespace-scoped の grant では、別の binding/access policy による既存の広い grant は取り消されません。access の所有者を通じて、意図した経路を修正します。

### RBAC の問題

認証失敗、Kubernetes `Forbidden` response、impersonation request の失敗はそれぞれ別の証拠です。正確な API verb、resource/subresource、namespace、subject kind を確認します。

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get roles,rolebindings
kubectl --context "$KUBE_CONTEXT" get clusterroles,clusterrolebindings
: "${SUBJECT_NAME:?Set the exact subject name}"
kubectl --context "$KUBE_CONTEXT" get rolebindings -A -o json \
  | jq --arg name "$SUBJECT_NAME" '.items[] | select(any(.subjects[]?; .name == $name)) | {namespace:.metadata.namespace,name:.metadata.name,roleRef,subjects}'
kubectl --context "$KUBE_CONTEXT" get clusterrolebindings -o json \
  | jq --arg name "$SUBJECT_NAME" '.items[] | select(any(.subjects[]?; .name == $name)) | {name:.metadata.name,roleRef,subjects}'
```

この query は subject name の候補を探します。同じ文字列でも subject の `kind`、ServiceAccount namespace、`roleRef` を確認してください。`kubectl auth can-i --as=...` には impersonation 権限が必要です。impersonated RBAC check と `--list` の出力では、EKS access policy によるすべての grant は再現されません。実際に認証する主体でもテストします。

例えば、標準 IAM access entry を意図的に `eks-troubleshoot-readers` に mapping した後、以下の Role は namespace 内の Pod/Service/event/EndpointSlice の read と Pod log だけを許可します。

```yaml
# Example for a deliberately mapped Kubernetes group in an existing namespace.
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: troubleshooting-reader
  namespace: applications
rules:
  - apiGroups: [""]
    resources: [pods, services, events]
    verbs: [get, list, watch]
  - apiGroups: [""]
    resources: [pods/log]
    verbs: [get]
  - apiGroups: [discovery.k8s.io]
    resources: [endpointslices]
    verbs: [get, list, watch]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: troubleshooting-readers
  namespace: applications
subjects:
  - kind: Group
    name: eks-troubleshoot-readers
    apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: troubleshooting-reader
  apiGroup: rbac.authorization.k8s.io
```

namespace が既に存在し、group mapping を別途レビュー済みである必要があります。application ServiceAccount では、`kind: ServiceAccount`、正確な name と namespace を指定した別の binding を使います。node/namespace read は cluster-scoped であり、レビュー済みの ClusterRole が必要です。すべての診断ユーザーに cluster-admin access を付与しないでください。この Role は Secret read 権限を持ちませんが、log access から application data が漏れる可能性はあります。

### IRSA と Pod Identity の問題

IRSA が提供するのは**workload の AWS 資格情報**です。そのクラスターの IAM OIDC provider は、人の IAM principal が Kubernetes RBAC access を得る仕組みではありません。Pod ServiceAccount、trust/permission policy、SDK credential chain、service endpoint 到達性を確認します。

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${KUBE_CONTEXT:?}"
: "${NAMESPACE:?}"; : "${SERVICE_ACCOUNT:?}"; : "${POD_NAME:?}"; : "${ROLE_NAME:?}"
aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query cluster.identity.oidc.issuer --output text
aws iam get-role --role-name "$ROLE_NAME" --query 'Role.{Arn:Arn,Trust:AssumeRolePolicyDocument}'
aws iam list-attached-role-policies --role-name "$ROLE_NAME"
aws iam list-role-policies --role-name "$ROLE_NAME"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get serviceaccount "$SERVICE_ACCOUNT" -o json \
  | jq '{name:.metadata.name,namespace:.metadata.namespace,annotations:.metadata.annotations}'
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pod "$POD_NAME" -o json \
  | jq '{serviceAccount:.spec.serviceAccountName,containers:[.spec.containers[] | {name,awsEnvironmentNames:[.env[]? | select(.name | startswith("AWS_")) | .name]}]}'
```

ここに表示しているのは AWS environment variable 名だけです。identity の調査で Pod の全 environment value や projected token を出力しないでください。IRSA では、サポート対象 SDK が projected web-identity token と設定した role を使うことを確認します。先に評価される static/default credential source が優先される場合があります。

次の trust statement は、1つの ServiceAccount subject と STS audience に結び付きます。共有 role をそのまま上書きする policy として使わず、account、partition、Region、issuer ID、subject を確認済みの値に置き換えてください。

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::123456789012:oidc-provider/oidc.eks.us-west-2.amazonaws.com/id/EXAMPLE"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "oidc.eks.us-west-2.amazonaws.com/id/EXAMPLE:aud": "sts.amazonaws.com",
          "oidc.eks.us-west-2.amazonaws.com/id/EXAMPLE:sub": "system:serviceaccount:applications:app"
        }
      }
    }
  ]
}
```

所有対象の role を変更するときも、正当な trust statement は保持します。role assumption に成功しても、IAM permission policy、resource policy、KMS grant、Organization control によって AWS action が拒否される場合があります。ServiceAccount annotation を変更しても、既存 Pod に environment/volume 設定が遡及して注入されることはありません。workload owner と調整して rollout します。

現在の EKS guide では、OIDC discovery/JWKS 用に `com.amazonaws.<region>.oidc-eks` PrivateLink endpoint を別途サポートしています。これは EKS 管理 endpoint、Pod Identity 用の `eks-auth`、STS とは別です。private OIDC access だけで IAM provider が作成されたり、role trust が付与されたり、STS に到達できたりするわけではありません。

EKS Pod Identity では、正確な namespace/ServiceAccount に対する association を確認します。

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${NAMESPACE:?}"; : "${SERVICE_ACCOUNT:?}"
aws eks list-pod-identity-associations --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --namespace "$NAMESPACE" --service-account "$SERVICE_ACCOUNT"
```

その後、返された association ID、role trust/permission、サポートされる agent/SDK/compute の要件を確認します。IRSA annotation がないことは Pod Identity の障害を意味しません。association update、credential cache、先に評価される SDK credential provider も関係します。全 consumer を確認する前に identity mechanism を切り替えたり、既存 IRSA trust を削除したりしないでください。現在の設定/移行経路は[セキュリティ章](./05-eks-security.md)を参照します。

### Node Join の失敗

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${NODEGROUP_NAME:?}"
aws eks describe-nodegroup --cluster-name "$CLUSTER_NAME" --nodegroup-name "$NODEGROUP_NAME" \
  --region "$AWS_REGION" \
  --query 'nodegroup.{name:nodegroupName,status:status,health:health,nodeRole:nodeRole,subnets:subnets,amiType:amiType,release:releaseVersion,launchTemplate:launchTemplate}'
aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query 'cluster.{endpoint:endpoint,access:accessConfig,vpc:resourcesVpcConfig}'
```

managed group では `health.issues`、launch-template/AMI/bootstrap の詳細、実際の EC2 instance 状態を確認します。self-managed/hybrid node では、managed-node API で状態を把握できると決めつけず、独自の bootstrap と登録方式を調べます。

instance-profile ARN ではなく IAM **role ARN** を確認し、適切な node authentication mapping/access entry を使います。managed node group と Fargate では service 管理の identity 動作があり、その mapping を上書きしないでください。node access entry は、一般的な人間用 entry と type/semantics が異なります。role path と legacy `aws-auth` の制限も、該当する authentication-mode guidance に従います。

必要な node policy と ECR pull 権限を確認します。サポートされる場合は、CNI/CSI/application の権限を実際の各 identity に付与します。node role に `AmazonEKSClusterPolicy` や CNI/storage の全権限を追加しても、一般的な node 登録の解決策にはなりません。

node から API server への HTTPS、API server から kubelet への port 10250、実際に必要な webhook/dependency 経路を確認します。DNS、route/NACL、security group の方向も含みます。backend webhook 用の rule があるからといって、すべての node で全方向からの inbound 443 が必要なわけではありません。

AMI 固有の bootstrap model を使います。AL2023/nodeadm、Bottlerocket setting、custom AMI では前提条件が異なります。AL2 script を再実行したり kubelet だけを置き換えたりしても、どの AMI でも修復できるわけではありません。証拠を保持し、原因を確認した後に所有者が管理する node replacement 手順を使います。

参考資料: [EKS access entry](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html)、[RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)、[IRSA](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)、[OIDC PrivateLink](https://docs.aws.amazon.com/eks/latest/userguide/irsa-fetch-keys.html)、[EKS Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html)。

## ストレージに関する問題 {#storage-issues}

### PVC、PV、consumer の診断

正確な namespace/claim/UID、provisioner、consumer から調べます。`WaitForFirstConsumer` の `Pending` は、適切な consumer Pod が scheduling されるまで正常な場合があります。その Pod の scheduling/zone/capacity 制約だけでなく、storage controller も確認します。

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${PVC_NAME:?}"
PVC_JSON=$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pvc "$PVC_NAME" -o json)
printf '%s\n' "$PVC_JSON" | jq '{name:.metadata.name,uid:.metadata.uid,status:.status,spec:.spec,storageClassFieldPresent:(.spec | has("storageClassName"))}'
PVC_UID=$(printf '%s\n' "$PVC_JSON" | jq -er '.metadata.uid')
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get events \
  --field-selector "involvedObject.uid=$PVC_UID" --sort-by='.metadata.creationTimestamp'
SC_NAME=$(printf '%s\n' "$PVC_JSON" | jq -r '.spec.storageClassName // empty')
if [ -n "$SC_NAME" ]; then
  kubectl --context "$KUBE_CONTEXT" get storageclass "$SC_NAME" -o yaml
else
  printf 'Inspect absent versus explicitly empty storageClassName and default/static binding intent.\n'
fi
PV_NAME=$(printf '%s\n' "$PVC_JSON" | jq -r '.spec.volumeName // empty')
if [ -n "$PV_NAME" ]; then
  kubectl --context "$KUBE_CONTEXT" get pv "$PV_NAME" -o yaml
  kubectl --context "$KUBE_CONTEXT" get volumeattachments -o json \
    | jq --arg pv "$PV_NAME" '.items[] | select(.spec.source.persistentVolumeName == $pv) | {name:.metadata.name,spec,status}'
fi
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pods -o json \
  | jq --arg pvc "$PVC_NAME" '.items[] | select(any(.spec.volumes[]?; .persistentVolumeClaim.claimName == $pvc)) | {name:.metadata.name,node:.spec.nodeName,phase:.status.phase,conditions:.status.conditions}'
```

`spec.volumes.persistentVolumeClaim.claimName` に対するサポート済み Pod field selector はありません。上記の JSON query は、この無効な API filter を使わず consumer を抽出します。`storageClassName` の省略と空文字列の明示では、default/static binding の意図が異なります。`<default>` という文字列の StorageClass を照会しないでください。

PVC YAML は object の設定であり、内容の backup ではありません。claim を削除/再作成すると、`Delete` の下では保存先が削除される場合があります。または保持された PV が意図的な再割り当てを待つ場合があります。Pending/FailedMount に対する一般的な修正として使わないでください。lifecycle を変更する前に reclaim policy、snapshot/backup、workload/data の所有者を調べます。claim が Bound でも、application が mount/read できる証明にはなりません。

### EBS volume の問題

#### driver と実際の volume を確認する

標準 `ebs.csi.aws.com`、Auto Mode の `ebs.csi.eks.amazonaws.com`、legacy/migrated volume とその所有者を区別します。標準 EBS CSI controller の権限は通常設定済み IAM identity から付与されます。node IAM role だけを見ても不十分です。実際の key に必要な KMS 権限と、controller/node component の状態も含めて確認します。

Auto Mode node の root/data volume が暗号化されていても、すべての workload PVC が暗号化されるとは限りません。現行の [Auto Mode StorageClass reference](https://docs.aws.amazon.com/eks/latest/userguide/create-storage-class.html) では `encrypted` の既定値は `false` です。EBS provisioner のどちらでも `encrypted: "true"` を明示して、実際の EBS volume/key を確認してください。アカウントの暗号化既定値や snapshot の属性も結果に影響する場合があります。

Auto Mode の独自 volume に標準 EBS CSI controller を別途インストールする必要はありません。EBS volume は Fargate Pod に mount できず、EBS CSI driver/volume は EKS Hybrid Node でサポートされません。Fargate で controller を動かしても、Fargate workload が EBS を mount できるようにはなりません。

```bash
set -euo pipefail
: "${AWS_REGION:?}"; : "${VOLUME_ID:?Verify it from the selected PV CSI volumeHandle}"
aws ec2 describe-volumes --region "$AWS_REGION" --volume-ids "$VOLUME_ID" \
  --query 'Volumes[].{Id:VolumeId,State:State,AZ:AvailabilityZone,Type:VolumeType,Size:Size,Encrypted:Encrypted,KmsKey:KmsKeyId,Attachments:Attachments}'
aws ec2 describe-volume-status --region "$AWS_REGION" --volume-ids "$VOLUME_ID"
```

選択した Pod/node と EBS volume が同じ AZ を使えることを確認し、attachment 上限、CSI error、現在の VolumeAttachment/EC2 state を調べます。PVC name だけでは namespace や過去の volume を一意に特定できません。PV から正確な volume を確認します。

#### attachment と mount の復旧

Multi-Attach では、古い consumer がまだ稼働または書き込み中か、その node が到達可能/隔離済みか、rollout で別 node に第2の consumer を配置したかを調べます。`ReadWriteOnce` は単一 node の access mode であり、単一 Pod の lock ではありません。workload 停止と CSI unmount/detach を調整します。Pod object を削除しただけで、process も停止したと決めつけないでください。

手動の attach/detach は CSI reconciliation の代わりにはなりません。手動介入が必要な場合、書き込み元が停止したこととデータ保護を確認し、EBS recovery 手順に従います。mount 中の volume を detach するとデータが破損するおそれがあります。node を何度も reboot したり force detach したりして attachment error を回避しないでください。

#### StorageClass と provisioning

**新規**の標準 driver class では、暗号化、遅延 binding、保持を明示する次の例を使えます。

```yaml
# New, explicitly selected StorageClass for standard EBS CSI, not an in-place edit.
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: diagnostic-ebs-gp3
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  encrypted: "true"
  csi.storage.k8s.io/fstype: ext4
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
reclaimPolicy: Retain
```

この例で既存 PVC の class は変更されません。既存 StorageClass の provisioner/parameter/binding mode は自由に変更できません。default class の切り替えは他の claim にも影響します。`Retain` は意図的に storage を残すため、別途 cleanup を判断し、継続課金も考慮します。拡張には driver/class/filesystem のサポートが必要です。PVC の要求サイズを書き換えて縮小することはできません。

互換性のある CSI addon を既存 owner 経由で選んで設定し、実際の IRSA/Pod Identity と全 configuration を含めます。`eksctl create iamserviceaccount --role-only` は role を作成するだけで、addon と関連付けるわけではありません。検査した addon identity と update 手順を使い、`--force` で再インストールしないでください。

Auto Mode への移行では、[EBS guide](https://docs.aws.amazon.com/eks/latest/userguide/ebs-csi.html) が snapshot 移行を説明しています。[Auto Mode migration guide](https://docs.aws.amazon.com/eks/latest/userguide/migrate-auto.html) では、workload を停止して Retain/static PV にする方法も説明されています。選択する前に、該当 driver、tag/IAM、claim/finalizer lifecycle、recovery plan を確認します。Bound claim の provisioner string を書き換えても移行にはなりません。snapshot を利用する場合は、CSI snapshot controller/CRD と該当 class/権限も必要です。

### EFS volume の問題

#### provisioning と mount access を個別に追跡する

PV から filesystem/access point、consumer node/AZ、mount target の稼働状態、DNS、NFS 経路を確認します。access point を作成する controller API の権限と、client が file を mount/access する権限は異なります。filesystem policy、TLS/IAM 要件、access-point の POSIX identity/root-directory ownership、application UID/GID を確認してください。

```bash
set -euo pipefail
: "${AWS_REGION:?}"; : "${FILE_SYSTEM_ID:?Verify the filesystem from the PV}"
aws efs describe-file-systems --region "$AWS_REGION" --file-system-id "$FILE_SYSTEM_ID"
aws efs describe-mount-targets --region "$AWS_REGION" --file-system-id "$FILE_SYSTEM_ID"
aws efs describe-access-points --region "$AWS_REGION" --file-system-id "$FILE_SYSTEM_ID"
: "${MOUNT_TARGET_ID:?Choose the mount target on the affected path}"
aws efs describe-mount-target-security-groups --region "$AWS_REGION" \
  --mount-target-id "$MOUNT_TARGET_ID"
```

実際の client network identity と mount target の間で NFS TCP 2049 が許可されていることを調べます。route/NACL と security group も確認します。control plane の subnet から node subnet を推測しないでください。workload の AZ/topology に適した mount target を使います。別の mount target の作成は独立したインフラストラクチャ変更です。

対応 EC2 環境では、インストール済み EFS CSI controller/node plugin と現在互換性のある version を確認します。Fargate には文書化された static provisioning 経路の組み込み EFS mount 機能があります。現行 EKS guide では Fargate node での dynamic provisioning はサポートされません。EFS CSI driver は Windows container/EKS Hybrid Node ではサポートされません。古い `release-1.5` manifest を無条件にインストールしたり、managed addon を重複させたりしないでください。

#### dynamic provisioning と static provisioning は別の選択肢

dynamic provisioning は**既存** EFS filesystem 内に access point を作成します。filesystem や mount target 自体は作成しません。例の ID を実際の値に置き換え、access point の所有権/権限、quota、保持を確認します。

```yaml
# Dynamic EFS access-point provisioning example for a supported EC2-node setup.
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: diagnostic-efs-ap
provisioner: efs.csi.aws.com
parameters:
  provisioningMode: efs-ap
  fileSystemId: fs-0123456789abcdef0
  directoryPerms: "700"
mountOptions:
  - tls
reclaimPolicy: Retain
```

別の方法として、事前に用意した既存 access point を static PV から参照できます。

```yaml
# Alternative static provisioning: replace the filesystem/access-point IDs.
apiVersion: v1
kind: PersistentVolume
metadata:
  name: diagnostic-efs-static
spec:
  capacity:
    storage: 5Gi
  volumeMode: Filesystem
  accessModes:
    - ReadWriteMany
  persistentVolumeReclaimPolicy: Retain
  storageClassName: ""
  mountOptions:
    - tls
  csi:
    driver: efs.csi.aws.com
    volumeHandle: fs-0123456789abcdef0::fsap-0123456789abcdef0
```

static PV と、`storageClassName: ""`、意図した `volumeName` を指定したレビュー済み claim を組み合わせます。binding/claimRef の意味を保ちます。dynamic class と併用して、新しい claim を意図せず filesystem root に bind しないでください。`5Gi` capacity field は Kubernetes の binding metadata であり、EFS directory や filesystem の実効容量 quota ではありません。

mount の診断では、まず既存 Pod/CSI event と log を使います。診断 Pod も claim と同じ namespace に置き、互換性のある node/identity を使います。`df` を実行するために application PVC を read-write で mount すると、新たな書き込み元になる可能性があります。probe が必要なら、明示的にレビューした read-only mount、準備済み image、期間の上限、所有者を考慮した cleanup を使ってください。ストレージの「テスト」として、無関係な EBS volume を作成したり、device を手動で attach したりしないでください。

参考資料: [EBS CSI](https://docs.aws.amazon.com/eks/latest/userguide/ebs-csi.html)、[EFS CSI](https://docs.aws.amazon.com/eks/latest/userguide/efs-csi.html)、[persistent volume](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)、[StorageClass](https://kubernetes.io/docs/concepts/storage/storage-classes/)。

## ログとモニタリングに関する問題 {#logging-and-monitoring-issues}

### CloudWatch Logs と Container Insights

EKS control-plane log 配信、Fluent Bit などの collector による application/host log 収集、CloudWatch agent metric、application instrumentation を区別します。cluster logging を有効にしても application collector はインストールされません。また collector が実行中でも、意図した account/Region/log group にデータが届いた証明にはなりません。

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${KUBE_CONTEXT:?}"
aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query cluster.logging
aws logs describe-log-groups --region "$AWS_REGION" \
  --log-group-name-prefix "/aws/eks/$CLUSTER_NAME/"
aws logs describe-log-groups --region "$AWS_REGION" \
  --log-group-name-prefix "/aws/containerinsights/$CLUSTER_NAME/"
: "${COLLECTOR_NAMESPACE:?}"; : "${COLLECTOR_POD:?}"; : "${COLLECTOR_CONTAINER:?}"
kubectl --context "$KUBE_CONTEXT" -n "$COLLECTOR_NAMESPACE" get pod "$COLLECTOR_POD" -o wide
kubectl --context "$KUBE_CONTEXT" -n "$COLLECTOR_NAMESPACE" logs "$COLLECTOR_POD" \
  -c "$COLLECTOR_CONTAINER" --since=15m --tail=200 --timestamps=true
```

名前/label の慣例を推測せず、インストール済み collector の namespace、Pod、container、configuration、destination を確認します。input path、parser、filter、buffering/backpressure、filesystem 容量、timestamp、output error、DNS/TLS/endpoint、quota を調べます。log group がない場合、配信されていない、別 destination に届いている、query 権限がない可能性があります。log group を作成するだけでは producer は修復されません。

実際の IRSA/Pod Identity または他のサポートされた identity を確認します。node policy や ServiceAccount annotation があるだけでは、collector が使う資格情報を証明しません。CloudWatch Observability EKS addon を使用している場合は、その identity/health も調べます。

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"
# Only for an installation actually owned by this EKS add-on.
aws eks describe-addon --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --addon-name amazon-cloudwatch-observability \
  --query 'addon.{status:status,version:addonVersion,health:health,role:serviceAccountRoleArn,podIdentity:podIdentityAssociations}'
```

API error が出ても addon が存在しない証明にはなりません。error と実際の Helm/addon owner を確認します。update 時は owner と独自設定を保持してください。古い未rendered Fluentd/Fluent Bit quickstart を適用したり、一般的な復旧として既存 ServiceAccount を上書きしたりしないでください。Windows、Fargate、Auto Mode、EC2 では collection 経路が異なります。

Container Insights では、実際の metric namespace、dimension、time window を query します。metric 一覧は metadata であり、最新 datapoint や alarm/notification の動作を証明しません。collection log と比較しながら期間を絞った query を使います。log 設定と証拠を保護し、retention/KMS 変更は log group owner を通じて行います。

### Metrics Server と resource metric

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"
kubectl --context "$KUBE_CONTEXT" get apiservice v1beta1.metrics.k8s.io -o yaml
kubectl --context "$KUBE_CONTEXT" get --raw "/apis/metrics.k8s.io/v1beta1/namespaces/$NAMESPACE/pods"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" top pods --containers
kubectl --context "$KUBE_CONTEXT" top nodes
```

resource Metrics API、kube-state-metrics object metric、Prometheus/cAdvisor sample はデータソースが異なります。APIService condition、aggregator/RBAC access、Metrics Server log、各 kubelet への接続を調べます。

`Unauthorized` では、どの caller と endpoint が資格情報を拒否したか確認します。`Forbidden` では該当する RBAC verb/resource を調べます。scrape failure は routing、kubelet address/port、証明書検証、認証、kubelet の異常で起こる場合があります。古い未認証 port 10255 を有効にしたり、万能の修正として `--kubelet-insecure-tls` を使ったりしないでください。

`v1.Pod` resource-not-found error だけでは EKS API server の設定不良を証明できません。kubeconfig/URL、API discovery、client 互換性、proxy response を確認します。証拠を収集する前に Metrics Server を再インストールしたり、すべての Pod を再起動したりすると、問題が隠れる場合があります。

### Prometheus と Grafana

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${MONITORING_NAMESPACE:?}"; : "${MONITORING_RELEASE:?}"
helm status "$MONITORING_RELEASE" --namespace "$MONITORING_NAMESPACE" --kube-context "$KUBE_CONTEXT"
helm history "$MONITORING_RELEASE" --namespace "$MONITORING_NAMESPACE" --kube-context "$KUBE_CONTEXT"
kubectl --context "$KUBE_CONTEXT" -n "$MONITORING_NAMESPACE" get pods,services,pvc
kubectl --context "$KUBE_CONTEXT" -n "$MONITORING_NAMESPACE" get events \
  --sort-by='.metadata.creationTimestamp'
```

実際の chart/operator、release namespace、Service port、storage、selector を特定します。standalone chart である `prometheus-community/prometheus` をインストールしても、ServiceMonitor resource を reconcile する Prometheus Operator は提供されません。Operator ベースの stack には、追加の CRD、Prometheus custom resource、selector/RBAC 要件があります。

既存 Prometheus endpoint を調べる場合は、localhost 限定の次の port-forward を1つ目の terminal で開いたままにします。

```bash
: "${KUBE_CONTEXT:?}"; : "${MONITORING_NAMESPACE:?}"
: "${PROMETHEUS_SERVICE:?Select the actual Prometheus Service}"
: "${PROMETHEUS_SERVICE_PORT:?Select its Service port}"
kubectl --context "$KUBE_CONTEXT" -n "$MONITORING_NAMESPACE" port-forward \
  --address 127.0.0.1 "service/$PROMETHEUS_SERVICE" "9090:$PROMETHEUS_SERVICE_PORT"
```

2つ目の local terminal では、access が許可されている endpoint に対して次を実行します。

```bash
set -euo pipefail
curl --fail --silent --show-error --max-time 10 \
  http://127.0.0.1:9090/api/v1/targets \
  | jq '.data.activeTargets[] | {scrapePool,health,lastError,lastScrape}'
```

scheme と認証を実際の endpoint に合わせます。access control を迂回しないでください。scrape error、relabeling、target discovery、query time window、retention を確認します。query 結果が空でも、data/label がない可能性があり、使用量が正常にゼロという意味ではありません。

#### ServiceMonitor の選択

この例では、既存 application の名前付き metrics port と Operator ServiceMonitor を接続します。

```yaml
# Requires an existing application exporting metrics on a named container port "metrics".
apiVersion: v1
kind: Service
metadata:
  name: app-metrics
  namespace: applications
  labels:
    app: metrics-demo
spec:
  selector:
    app: metrics-demo
  ports:
    - name: metrics
      port: 9090
      targetPort: metrics
---
# Requires Prometheus Operator and a Prometheus CR selecting this namespace/label.
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: app-metrics
  namespace: monitoring
  labels:
    release: observability
spec:
  namespaceSelector:
    matchNames:
      - applications
  selector:
    matchLabels:
      app: metrics-demo
  endpoints:
    - port: metrics
      path: /metrics
      interval: 30s
```

namespace、label、release selector を実際の installation に置き換えます。3つの選択が関係します。Prometheus は ServiceMonitor の namespace を選択し、その `serviceMonitorSelector` が monitor label を選び、monitor の `namespaceSelector` と `selector` が Service を選択します。`endpoints.port` が指定するのは、任意の container port ではなく**Service port**です。application が想定される metrics path で実際に listen して公開する必要があります。Prometheus には discovery 権限、network/TLS/auth access も必要です。

#### 設定を保護して変更を確認する

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${MONITORING_NAMESPACE:?}"; : "${MONITORING_RELEASE:?}"
: "${EVIDENCE_PARENT:?Set an existing private directory}"
umask 077
MONITORING_EVIDENCE=$(mktemp -d "$EVIDENCE_PARENT/monitoring-config.XXXXXXXX")
helm get values "$MONITORING_RELEASE" --namespace "$MONITORING_NAMESPACE" \
  --kube-context "$KUBE_CONTEXT" --all > "$MONITORING_EVIDENCE/values.yaml"
printf 'Protected configuration snapshot: %s\n' "$MONITORING_EVIDENCE"
```

保護された file に書き込んでも、value に機微情報が含まれることがあります。共有前に削除してください。更新対象 chart/version の既定値、CRD migration、独自 value、workload resource、PVC 容量を確認します。既存 owner 経由で更新し、その後 scrape/alert 動作を検証してください。stack を重複してインストールしたり、診断せず resource limit を patch したりしないでください。

Grafana では datasource UID/URL/authentication、network access、query label/time range、dashboard provisioning/sidecar selection を確認します。期待する sidecar label/namespace がない ConfigMap は、dashboard として自動で取り込まれません。既存の login/SSO を使い、administrator password をトラブルシューティング log に出力しないでください。

レビュー済み installation、query、alert 手順は[EKS monitoring and logging](./06-eks-monitoring-logging.md)を参照してください。上記の例は診断/設定用 template であり、実際の log 配信、monitoring coverage、本番適性を検証したものではありません。

参考資料: [CloudWatch EKS addon](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Container-Insights-setup-EKS-addon.html)、[Metrics Server](https://github.com/kubernetes-sigs/metrics-server)、[Prometheus Operator troubleshooting](https://prometheus-operator.dev/docs/platform/troubleshooting/)。

## パフォーマンスに関する問題 {#performance-issues}

### 比較可能な基準値を設定する

影響を受けた workload、request rate、latency/error 分布、resource request/limit、node/AMI/runtime、配置、対象時間帯を記録します。現在の使用量は予約 capacity や飽和状態と同じではありません。また、memory が増えただけで leak と証明されません。node、Pod、storage、network、application の bottleneck を切り分けます。

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${POD_NAME:?}"; : "${NODE_NAME:?}"
kubectl --context "$KUBE_CONTEXT" top nodes
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" top pods --containers
kubectl --context "$KUBE_CONTEXT" get node "$NODE_NAME" -o json \
  | jq '{nodeInfo:.status.nodeInfo,allocatable:.status.allocatable,conditions:.status.conditions}'
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pod "$POD_NAME" -o json \
  | jq '{containers:[.spec.containers[] | {name,resources}],status:.status}'
```

metric は収集経路が動作している場合にのみ有効です。状況に応じて CPU throttling、working set/RSS/heap の挙動、OOM termination state、disk latency/queue、network drop を確認します。application load と関連付けてください。無関係な workload に同じ 100m/128Mi の resource 値を勧めないでください。

### Node のパフォーマンス問題

該当ツールを使えることを確認した remote Linux node session で、期間を絞って調査します。

```bash
top -b -n 1
free -m
df -h
df -i
iostat -x 1 5
ip -s link
ss -s
```

これらの command を実行するために、本番 application container に tool をインストールしないでください。準備済み diagnostic image またはサポートされる node access method を使い、host を変更する前に証拠を保存します。

node 数の増加は scheduling 可能な capacity には役立ちますが、node あたりの network/ENI/EBS 上限は変わりません。instance type を変えるには、node group がサポートする replacement/launch-template 経路を使います。`update-nodegroup-config --launch-template` は有効な command ではありません。owner の管理外で resize せず、autoscaling と workload 配置を調整します。

#### kernel 設定

tuning を考える前に、対象の host または Pod namespace で関連設定を調べます。

```bash
sysctl net.ipv4.ip_local_port_range net.ipv4.tcp_fin_timeout
sysctl net.core.somaxconn net.ipv4.tcp_max_syn_backlog fs.file-max
```

多くの network sysctl は namespace ごとに適用されます。`hostPID: true` だけでは container は host network namespace に入りません。privileged DaemonSet が node 全体の設定も変更しながら、異なる network namespace を変更する場合があります。許可された namespace 固有設定にはサポート対象の Pod `securityContext.sysctls` を使い、node-level 設定には owner が管理する node configuration を使います。変更前に kernel/Kubernetes policy のサポート状況、分離、影響を確認してください。任意の cluster-wide privileged sysctl tuning は performance diagnosis ではありません。

#### EBS パフォーマンスの変更

変更前に実 volume の type/IOPS/throughput と、instance の EBS bandwidth を調べます。EC2 `modify-instance-attribute` の block-device mapping は EBS の type/IOPS/throughput を調整する interface ではありません。該当する EBS operation は `ModifyVolume` です。CSI 管理 storage は、対応する storage-owner workflow を使い、drift を起こさず設定を調整します。

以下の任意の**変更操作**は、volume owner がサポート上限/比率、instance capability、料金、現在の modification state、application/data への影響を確認していることを前提とします。

```bash
set -euo pipefail
: "${AWS_REGION:?}"; : "${VOLUME_ID:?Verify the owned EBS volume}"
: "${TARGET_IOPS:?Set a reviewed supported gp3 IOPS value}"
: "${TARGET_THROUGHPUT:?Set a reviewed supported gp3 MiB/s value}"
: "${EVIDENCE_PARENT:?Set an existing private directory}"
umask 077
EBS_CHANGE_DIR=$(mktemp -d "$EVIDENCE_PARENT/ebs-performance.XXXXXXXX")
aws ec2 describe-volumes --region "$AWS_REGION" --volume-ids "$VOLUME_ID" \
  --output json > "$EBS_CHANGE_DIR/before.json"
# Separate approved volume change; this is not a diagnostic read.
aws ec2 modify-volume --region "$AWS_REGION" --volume-id "$VOLUME_ID" \
  --volume-type gp3 --iops "$TARGET_IOPS" --throughput "$TARGET_THROUGHPUT" \
  --output json > "$EBS_CHANGE_DIR/request.json"
aws ec2 describe-volumes-modifications --region "$AWS_REGION" --volume-ids "$VOLUME_ID" \
  --output json
```

request は非同期です。`modifying`、`optimizing`、`completed`、`failed` を追跡します。最初の応答は完了を意味しません。適用される modification rate 上限を考慮し、次の request の前に現在の変更が完了するまで待ちます。容量を増やした場合は、filesystem の拡張を別途検討します。以前の 16000 IOPS/1000 MiB/s の例は設定例であり、一般的な最適値を測定したものではありません。このレビューでは EBS 変更を実行していません。

### Pod のパフォーマンスと memory の問題

container ごとの使用量/limit、restart/termination reason を request load と関連付けます。`OOMKilled` は container status から確認でき、Event に文字列として現れない場合もあります。node に空き memory があっても cgroup limit が原因で OOM になることがあります。cache 増加、allocator の挙動、workload burst、参照が残る object では調査方法が異なります。定期的な garbage collection や node reboot は一般的な leak 対策ではありません。

実際の runtime/version に対応する profiler を選び、レビュー済み手順で対象 process に接続します。`node --inspect` は新しい process を開始するため、稼働中の application に自動接続はしません。JVM/Python/Go profiler には tool、symbol、code、endpoint の前提条件があります。heap dump は workload を停止させたり、disk を使い切ったり、secret を含んだりする場合があります。採取範囲を限定して artifact を保護してください。この章では profile や benchmark を実行していません。

実測した要件から request/limit を調整し、runtime overhead も含めます。resource quota、rollout、HPA/VPA の所有者を確認します。preferred anti-affinity と `ScheduleAnyway` topology spread は希望条件であって保証ではありません。strict rule では適格 node が不足して Pod が Pending になります。replica を増やしても、single-thread、storage、downstream service の bottleneck は直らない場合があります。

### Network のパフォーマンス問題

実際の CNI/policy/SG 経路、instance bandwidth/PPS/connection 上限、MTU、DNS 挙動、送信元/宛先の配置を確認します。MTU を 9001 にする、ENA を有効化する、launch-template version を置き換える、といった変更はどの環境でも使える即時修正ではありません。platform/state の前提条件を確認し、owner が管理する rollout を行います。Auto Mode には node DNS と独自の networking configuration が既にあります。

テストを実施する場合は、互換 client/server image、resource、node/AZ 配置、隔離された試験範囲で許可する TCP 5201 access を準備します。image/version、方向、topology を記録します。次の範囲を限定した例は、元の30秒の実行時間を保ちつつ、1 stream あたりの target bitrate を制限します。

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?Set the approved test context}"
: "${TEST_NAMESPACE:?}"; : "${CLIENT_POD:?}"; : "${CLIENT_CONTAINER:?}"
: "${SERVER_IP:?Set the prepared test server IP}"
# Existing prepared test client/server only: one stream, 30 seconds, 10 Mbit/s target.
kubectl --context "$KUBE_CONTEXT" -n "$TEST_NAMESPACE" exec "$CLIENT_POD" \
  -c "$CLIENT_CONTAINER" -- iperf3 -c "$SERVER_IP" -P 1 -t 30 -b 10M -J
```

10 Mbit/s は試験時の pacing であり、期待性能や network ceiling の証明ではありません。複数 stream ではそれぞれに bitrate 上限が適用されます。command 実行前に server/client readiness を待ち、その後は準備した試験 resource だけを cleanup します。DNS 時間では cache hit、upstream lookup、command/exec overhead を区別します。実際の証拠がないまま、本番 throughput、latency、benchmark 成功を主張しないでください。

参考資料: [Kubernetes sysctl](https://kubernetes.io/docs/tasks/administer-cluster/sysctl-cluster/)、[EBS ModifyVolume](https://docs.aws.amazon.com/botocore/latest/reference/services/ec2/client/modify_volume.html)、[iperf manual](https://software.es.net/iperf/invoking.html)。

## アップグレードに関する問題 {#upgrade-issues}

### 実行した operation を特定する

cluster/node-group が `ACTIVE` でも、特定 request の結果を意味しません。update ID、operation の範囲、意図した version/configuration、最後に成功した段階、error を記録します。

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${UPDATE_ID:?}"
: "${UPDATE_KIND:?Set control-plane, nodegroup, or addon}"
args=(--name "$CLUSTER_NAME" --region "$AWS_REGION" --update-id "$UPDATE_ID")
case "$UPDATE_KIND" in
  control-plane) ;;
  nodegroup) : "${NODEGROUP_NAME:?}"; args+=(--nodegroup-name "$NODEGROUP_NAME") ;;
  addon) : "${ADDON_NAME:?}"; args+=(--addon-name "$ADDON_NAME") ;;
  *) echo "Invalid UPDATE_KIND" >&2; exit 2 ;;
esac
aws eks describe-update "${args[@]}" --output json --no-cli-pager
```

処理中の operation では、[EKS upgrades](./08-eks-upgrades.md)にある対象 ID を限定した poller を使います。成功と判断できるのは `Successful` だけです。failure/cancellation/unknown state や query error は調査が必要です。local timeout で AWS operation が取り消されることはありません。

### Control plane と API 互換性

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${TARGET_VERSION:?}"
FILTER=$(jq -n --arg target "$TARGET_VERSION" \
  '{categories:["UPGRADE_READINESS"],kubernetesVersions:[$target]}')
aws eks list-insights --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --filter "$FILTER" --output json
aws eks describe-addon-versions --kubernetes-version "$TARGET_VERSION" --region "$AWS_REGION" \
  --output json
```

addon catalog は cluster-version catalog とは別です。cluster catalog と実際の current version から、次にサポートされる EKS minor を選びます。upstream release から EKS のサポートを推測しないでください。保守的な準備として node を現在の control-plane version に合わせますが、それとサポートされる version skew の境界は区別します。一部 addon では control-plane 変更前に bridge version が必要です。

元の manifest/Helm metadata、runtime が呼び出す API、upgrade insight、admission/conversion webhook を調べます。container image list や、現在返される object の `.apiVersion` を見ても、client が削除済み API を使っていない証明にはなりません。migration guide と、source upgrade chapter で確認済みの Pluto command を使います。`kubectl convert` は別の plugin であり、組み込みの汎用 migration/test command ではありません。

現行 EKS guide では、通常 upgrade insight に対する `--force` enforcement は一時的に rollback されています。これは `ROLLBACK_READINESS` の block condition とは別の話です。前の command が timeout しただけで upgrade を再送信しないでください。また、開始済みの通常 control-plane upgrade を取り消せると決めつけないでください。

### Node group と addon の復旧

PDB の許可済み disruption 数、replica/readiness、置換用 EC2/IP capacity、AMI/bootstrap、実際の managed-node update error を調べます。`kubectl drain --force` は管理されていない Pod の削除を許可しますが、PDB eviction check は回避しません。`--disable-eviction` と managed-node force update は異なる破壊的動作です。error を消すためだけに `minAvailable: 0` にしたり、`emptyDir` data を破棄したりしないでください。

EKS 最適化 AMI では Kubernetes version と AMI release の両方を確認します。custom-AMI group では、元の launch template と正しい API/option を使った、レビュー済みの新 version が必要です。update に失敗しても fleet が自動 rollback するとは限りません。すぐに group を追加・削除するのではなく、現在の node/Pod 節と段階的 upgrade 手順を使います。

addon では version/configuration/schema、IAM/Pod Identity、所有者を保持します。`PRESERVE` は設定を完全に merge したり機能を保証したりしません。`OVERWRITE` は独自設定を破棄する場合があります。networking/storage addon を削除・再作成すると、依存 cleanup や workload access に影響する場合があります。汎用 `{"key":"value"}` payload や、CoreDNS と偽った VPC CNI manifest は有効な修正ではありません。

### rollback は別途判断する

現行 EKS では、in-place upgrade 完了後7日以内なら、条件付きで直前の minor に rollback できます。対象資格、support policy、feature 前提条件、compute type ごとの順序、`ROLLBACK_READINESS` が適用されます。managed-node rollback は control plane より先に行います。Auto Mode は先に node を調整します。timeout/cancellation/disruption rule は通常 upgrade と異なります。

`--force` で rollback insight は無視できますが、前提条件の検証や Auto Mode disruption control は回避されません。version rollback で保持されるのは workload/data の現状であり、backup が復元されるわけではありません。addon も自動 rollback されません。Fargate、hybrid/custom node、support policy、recovery 条件は[rollback の全手順](./08-eks-upgrades.md)に従います。Git/CloudFormation の rollback は EKS service operation の代わりではありません。

参考資料: [EKS update](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html)、[managed-node update](https://docs.aws.amazon.com/eks/latest/userguide/update-managed-node-group.html)、[EKS rollback](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html)、[Auto Mode rollback](https://docs.aws.amazon.com/eks/latest/userguide/rollback-automode.html)。

## よくあるエラーメッセージと解決方法 {#common-error-messages-and-solutions}

以下は例示の message/pattern であり、すべての現行 controller が必ず同じ文字列を出すわけではありません。実際の error code、resource UID、request ID、condition を確認します。提案した原因は証拠で裏付けるまで仮説です。

| message / pattern | 証拠と次の適切な手順 |
| --- | --- |
| `UnsupportedAvailabilityZoneException` | 選択した cluster subnet/AZ が、そのアカウントでは EKS 非対応です。EC2 instance 提供状況だけでなく、error に記載された対応 AZ を調べます |
| `ResourceLimitExceeded` / quota error | 該当 service/quota と現在の適用上限を特定します。過去の「limit 5」という記述は現在の上限ではありません |
| `InvalidParameterException: Error in role params` | role の存在/trust、caller の `iam:PassRole`、必要な権限、正確な request を確認します。共有 role を安易に新規作成しないでください |
| `ClusterUnreachable` | endpoint の DNS、route、SG/NACL、TLS を調べます。kubeconfig を再作成しても transport は直りません |
| `You must be logged in ... (Unauthorized)` / `the server has asked for the client to provide credentials` | credential provider、role/profile、exec authentication、cluster authentication mode/access entry または legacy mapping を確認します |
| `Forbidden` | 認証済み subject、verb/resource/subresource/namespace と該当する全 grant を確認します。impersonation 失敗も区別します |
| `error loading ... .kube/config ... permission denied` | 選択された file、owner、親 directory の権限を確認します。所有者/path が正しくなければ mode 600 にしても解決しません |
| `dial tcp: lookup ... no such host` | endpoint hostname を解決し、実際の resolver/private path を調べます。DNS lookup に HTTPS URL 全体を渡さないでください |
| `FailedScheduling ... Insufficient memory` | request/overhead、配置、quota、eligible node の allocatable capacity を比較します。現在の空き memory/`top` だけでは scheduler の計算を再現できません |
| `Insufficient pods` | node の割り当て可能 Pod slot と現在の割り当てを調べます。memory request を下げても Pod slot は増えません |
| `CrashLoopBackOff` | container/init-container の現在と直前の termination state、前回 instance の log、configuration、probe を確認します |
| `ImagePullBackOff` | image/digest/platform、node 側 registry 経路/TLS/rate limit、実際の pull identity を error から確認します。診断目的でも資格情報を公開しないでください |
| `Evicted` | Pod reason/message と node pressure/時間帯を読み、関連するデータ/可用性の復旧手順を使います |
| `FailedCreateServiceEndpoints` / EndpointSlice update error | Service selector/type、Pod Ready/endpoint condition、named port、controller event を調べます |
| `EniLimitExceeded` / IPAM allocation error | 実際の ENI/IP/subnet/prefix 制約と quota/error context を確認します。prefix/custom networking ですべての上限がなくなるわけではありません |
| `FailedLoadBalancerCreation` / controller provisioning error | 正確な controller owner、subnet 選択、IAM、target health、SG 経路を確認します。すべての subnet に tag を付けたり、全 traffic を許可したりしないでください |
| `FailedAttachVolume: Multi-Attach ...` | consumer と attachment/fencing state を特定します。force detach せず、CSI unmount/detach と data safety を調整します |
| `FailedMount ... timeout ...` | CSI controller/node plugin、identity/KMS、topology、filesystem、attachment event を確認します。node restart は自動的な修正ではありません |
| `PersistentVolumeClaim is not bound` | 予定された delayed binding と class/provisioner/identity/consumer scheduling の問題を区別します。claim を削除しないでください |
| `Failed to list *v1.Pod: Unauthorized` | error を返した endpoint/caller と token/identity を特定します。Metrics Server を再起動しても資格情報は修復されません |
| `Failed to scrape node` | 認証付き kubelet scrape 経路、証明書、address/port、networking、node health を調べます |
| `Failed to list *v1.Pod: the server could not find the requested resource` | EKS control-plane 設定のせいと決めつける前に API URL/context/discovery と client/proxy response を確認します |

該当する節を使い、範囲を絞った証拠を収集して所有者が管理する修正を選びます。結果と未解決の前提を記録してください。これらの例示 message だけでは、診断や復旧を証明できません。

## クイズ

この章で学んだ内容を確認するには、[トピック quiz](../quizzes/eks/09-eks-troubleshooting-quiz.md)に挑戦してください。
