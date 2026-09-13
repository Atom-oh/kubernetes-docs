# パート1: インフラストラクチャのセットアップ

<span id="cleanup"></span>
<span id="exercise-1-environment-setup"></span>
<span id="exercise-2-managed-cluster-eks-setup"></span>
<span id="exercise-3-service-cluster-eks-setup"></span>
<span id="exercise-4-aws-managed-services-setup"></span>
<span id="exercise-5-argocd-setup-on-managed-cluster"></span>
<span id="exercise-6-argo-rollouts-setup-on-service-cluster"></span>
<span id="exercise-7-irsa-configuration"></span>
<span id="learning-objectives"></span>
<span id="next-steps"></span>
<span id="references"></span>
<span id="steps"></span>
<span id="steps-1"></span>
<span id="steps-2"></span>
<span id="steps-3"></span>
<span id="steps-4"></span>
<span id="steps-5"></span>
<span id="steps-6"></span>
<span id="summary"></span>
<span id="troubleshooting"></span>
<span id="verification"></span>
<span id="verification-1"></span>
<span id="verification-2"></span>
<span id="verification-3"></span>
<span id="verification-4"></span>
<span id="verification-5"></span>

> **難易度**: 上級
> **最終更新**: September 13, 2026
2 つの EKS クラスターと、このラボ専用のデータベース/メッセージ経路を準備します。実行可能ファイルは[アプリケーション例](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/labs/observability/application)にあります。課金対象リソースを作成する前に、アカウント、Region、ネットワーク、権限、クリーンアップを確認してください。この監査では AWS リソースを作成していません。

![管理/サービスクラスターと専用ラボリソース](../../.gitbook/assets/en-labs-observability-01-infrastructure-setup-lab-0.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-labs-observability-01-infrastructure-setup-lab-0.html)

## 1. 環境と所有権を確認する {#prerequisites}

例は AWS CLI v2、eksctl 0.229.0、kubectl 1.36.2、Helm 3.21.3、Python 3.12、Docker、Git、jq でレビューしました。レビュー時点で EKS 1.36 は標準サポート期間内でした。古い 1.31 の例は延長サポート期間内であり、すでにサポート終了ではありませんでした。実行時にはバージョンおよび Region の可用性を再確認してください。

```bash
aws --version
eksctl version
kubectl version --client
helm version
python3 --version
aws sts get-caller-identity
```
承認済みの一時的なロールを使用してください。必要な EKS、EC2/VPC、CloudFormation、IAM/PassRole、RDS、SNS/SQS、KMS、Logs の操作をデプロイ計画に照らして確認してください。この演習のために、すべてのサービスに FullAccess を付与したり、長期間有効な IAM アクセスキーを作成したりしないでください。

```bash
umask 077
export LAB_STATE="$(mktemp -d "$PWD/obs-lab.XXXXXXXX")"
# Set AWS_REGION, EXPECTED_ACCOUNT_ID and a unique LAB_PREFIX first.
test "$(aws sts get-caller-identity --query Account --output text)" = "$EXPECTED_ACCOUNT_ID"
```

## 2. ネットワークと 2 つのクラスター {#clusters}

この例では、レビュー済みの VPC と異なる AZ にある 2 つのプライベートサブネットを再利用します。最初に NAT/必要な VPC エンドポイント、DNS、アドレス容量、SG/NACL ルールを準備してください。Kubernetes の Service CIDR172.20.0.0/16 および172.21.0.0/16 は、実際の VPC/接続済みネットワークと重複してはなりません。別々の VPC では、追加のピアリング/TGW、双方向ルート、DNS、送信元 IP の検証が必要です。

```bash
cd examples/labs/observability/application
python3 prepare_clusters.py --region "$AWS_REGION" --vpc-id "$VPC_ID" \
  --subnet-a "$PRIVATE_SUBNET_A" --az-a "$AZ_A" \
  --subnet-b "$PRIVATE_SUBNET_B" --az-b "$AZ_B" \
  --client-cidr "$CLIENT_CIDR" --prefix "$LAB_PREFIX" \
  --output-directory "$LAB_STATE/clusters"
```
ジェネレーターは、EKS 1.36、API アクセスエントリ、OIDC、AL2023 マネージドノード、暗号化された gp3、限定的なパブリック API クライアント CIDR を選択します。ノードのサイズ/数はラボ設定であり、測定済みのキャパシティではありません。作成前に JSON とコストを確認してください。失敗した場合は、再度何かを作成する前に、その名前で部分的に作成されたリソースを調査してください。

```bash
eksctl create cluster -f "$LAB_STATE/clusters/managed.json" --write-kubeconfig=false
eksctl create cluster -f "$LAB_STATE/clusters/service.json" --write-kubeconfig=false
export KUBECONFIG="$LAB_STATE/kubeconfig"
aws eks update-kubeconfig --name "$LAB_PREFIX-managed" --alias managed --kubeconfig "$KUBECONFIG"
aws eks update-kubeconfig --name "$LAB_PREFIX-service" --alias service --kubeconfig "$KUBECONFIG"
kubectl --context managed get nodes
kubectl --context service get nodes
```
[EKS 作成ガイド](../../eks/02-eks-cluster-creation-part1.md)および[クラスタ―ラボ](../eks/01-eks-cluster-creation-lab.md)にあるアカウント/エンドポイント/所有権のチェックを適用してください。両方の context が意図した別個のクラスターを選択していることを確認してください。

## 3. ストレージ、ロードバランサー、OIDC の前提条件 {#platform-prerequisites}

EBS CSI、レビュー済みの `gp3` StorageClass、実際に NetworkPolicy を強制する CNI、AWS Load Balancer Controller（`service.k8s.aws/nlb`）をインストールします。共有 StorageClass を無造作に上書きしないでください。各クラスターの OIDC issuer と対応する IAM provider ARN を取得してください。https:// を除いた issuer の host/path は、provider ARN のサフィックスと一致する必要があります。

```bash
aws eks describe-cluster --name "$LAB_PREFIX-managed" --query cluster.identity.oidc.issuer --output text
aws eks describe-cluster --name "$LAB_PREFIX-service" --query cluster.identity.oidc.issuer --output text
kubectl --context managed get storageclass gp3
kubectl --context service get storageclass gp3
```

## 4. Aurora、SNS/SQS、ロール {#managed-resources}

`application/infra.yaml` は、プライベート Aurora writer、マネージド master Secret、SNS fanout、個別の consumer queue/DLQ、CloudWatch log group、ロールを作成します。DB ingress は実際の service-node SG のみを許可します。単一 writer の演習は Multi-AZ HA ではありません。Region でサポートされている Aurora engine version を検出して明示的に指定してください。

```bash
aws rds describe-db-engine-versions --engine aurora-postgresql \
  --query "DBEngineVersions[].EngineVersion" --output table
```
VpcId、PrivateSubnetIds、ServiceNodeSecurityGroupId、AuroraEngineVersion、両方の OIDC provider/issuer ペアを指定し、CloudFormation change set をレビューして実行してください。アカウント、ARN、ServiceAccount の整合性を確認してください。アプリの runtime role、KEDA の queue-read identity、management Collector の log identity はそれぞれ別です。

```bash
aws cloudformation describe-stacks --stack-name "$LAB_STACK" \
  --query "Stacks[0].Outputs" --output json > "$LAB_STATE/infra-outputs.json"
```

ここでパート2用の Collector identity 入力を生成します。イメージリポジトリとイミュータブルなタグをここで選択してください。イメージのビルド/プッシュはパート3で行います。

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt PyYAML==6.0.3
.venv/bin/python prepare_values.py --outputs-file "$LAB_STATE/infra-outputs.json"   --region "$AWS_REGION" --image-repository "$IMAGE_REPOSITORY"   --image-tag "$IMAGE_TAG" --output-directory "$LAB_STATE/helm-inputs"
```

## 5. Runtime DB アカウントと次のステップ {#database-and-next}

master Secret は承認済みの環境でのみ読み取り、プライベートな JSON 接続ファイルに保存してください。RDS CA bundle と `sslmode=verify-full` を使用してください。[bootstrap_db.py の手順](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/labs/observability/application#infrastructure-and-credentials)では、既存のパスワードを上書きせずに、専用の `lab_runtime` DML アクセスを作成します。Pod CA path を `/run/database-ca/global-bundle.pem` に設定してください。

所有権インベントリに、スタック、クラスター、保持された snapshot、IAM attachment、LB、PVC を記録してください。実際の Region と使用量に対する EKS/node/NAT/EBS/Aurora/Logs/SNS/SQS/KMS/transfer のコストを見積もってください。固定の時間あたり合計を提示したり、AMG のユーザーあたり月額料金を workspace の時間あたり料金に換算したりしないでください。[パート2](./02-observability-stack-lab.md)に進んでください。

## 検証範囲

チェックでは、eksctl schema、CloudFormation lint/role structure、ローカル PostgreSQL の動作を対象としました。実際の EKS/VPC/OIDC/IRSA/Aurora/TLS、quota、プロビジョニング時間は検証していません。
