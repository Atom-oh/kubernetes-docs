# パート 1: インフラストラクチャセットアップ

> **難易度**: 中級
> **推定所要時間**: 60 分
> **最終更新**: February 22, 2026

## 学習目標

- Terraform と eksctl を使用して 2 つの EKS クラスター（Managed と Service）をプロビジョニングする
- AWS Managed Services（Aurora、OpenSearch、AMP、AMG、MWAA、SQS/SNS）を設定する
- マルチクラスター Deployment 向けに ArgoCD をセットアップする
- セキュアな AWS アクセスのために IRSA（IAM Roles for Service Accounts）を設定する

## 前提条件

- [ ] 適切な権限を持つ AWS CLI が設定済みであること
- [ ] Terraform >= 1.7 がインストール済みであること
- [ ] eksctl >= 0.175 がインストール済みであること
- [ ] kubectl >= 1.29 がインストール済みであること
- [ ] Helm >= 3.14 がインストール済みであること
- [ ] [EKS Cluster Creation](../../eks/02-eks-cluster-creation-part1.md) の学習を完了していること

> **コストに関する警告**: このラボでは大規模な AWS リソースを作成します。推定コストは約 $2.50/時間です。完了後は必ずクリーンアップしてください。

---

## 演習 1: 環境セットアップ

### 手順

**手順 1.1: 環境変数を設定する**

```bash
export AWS_REGION=us-west-2
export ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export MANAGED_CLUSTER_NAME=obs-managed
export SERVICE_CLUSTER_NAME=obs-service

echo "AWS Region: $AWS_REGION"
echo "Account ID: $ACCOUNT_ID"
echo "Managed Cluster: $MANAGED_CLUSTER_NAME"
echo "Service Cluster: $SERVICE_CLUSTER_NAME"
```

**手順 1.2: 作業ディレクトリを作成する**

```bash
mkdir -p ~/obs-lab/{terraform,k8s,scripts}
cd ~/obs-lab
```

**手順 1.3: ツールのバージョンを確認する**

```bash
aws --version
terraform version
eksctl version
kubectl version --client
helm version
```

---

## 演習 2: Managed Cluster（EKS）のセットアップ

### 手順

**手順 2.1: VPC と EKS クラスターの設定を作成する**

```bash
cat > ~/obs-lab/managed-cluster.yaml << 'EOF'
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: obs-managed
  region: us-west-2
  version: "1.31"

vpc:
  cidr: 10.10.0.0/16
  nat:
    gateway: Single

iam:
  withOIDC: true

managedNodeGroups:
  - name: obs-workers
    instanceType: m5.xlarge
    desiredCapacity: 3
    minSize: 2
    maxSize: 5
    volumeSize: 100
    volumeType: gp3
    labels:
      role: observability
    tags:
      Environment: lab
      Purpose: observability-stack
    iam:
      attachPolicyARNs:
        - arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy
        - arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy
        - arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly
        - arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore

addons:
  - name: vpc-cni
    version: latest
  - name: coredns
    version: latest
  - name: kube-proxy
    version: latest
  - name: aws-ebs-csi-driver
    version: latest
    wellKnownPolicies:
      ebsCSIController: true

cloudWatch:
  clusterLogging:
    enableTypes: ["api", "audit", "authenticator", "controllerManager", "scheduler"]
EOF
```

**手順 2.2: Managed Cluster を作成する**

```bash
eksctl create cluster -f ~/obs-lab/managed-cluster.yaml
```

> この処理には約 15～20 分かかります。

**手順 2.3: クラスターの作成を確認する**

```bash
kubectl config use-context $(kubectl config get-contexts -o name | grep obs-managed)
kubectl get nodes -o wide
kubectl get pods -n kube-system
```

### 確認

```bash
kubectl get nodes
# Expected: 3 nodes in Ready state
```

---

## 演習 3: Service Cluster（EKS）のセットアップ

### 手順

**手順 3.1: Karpenter サポートを含む Service Cluster 設定を作成する**

```bash
cat > ~/obs-lab/service-cluster.yaml << 'EOF'
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: obs-service
  region: us-west-2
  version: "1.31"
  tags:
    karpenter.sh/discovery: obs-service

vpc:
  cidr: 10.20.0.0/16
  nat:
    gateway: Single

iam:
  withOIDC: true

managedNodeGroups:
  - name: system
    instanceType: m5.large
    desiredCapacity: 2
    minSize: 2
    maxSize: 3
    volumeSize: 50
    volumeType: gp3
    labels:
      role: system
    taints:
      - key: CriticalAddonsOnly
        value: "true"
        effect: PreferNoSchedule

karpenter:
  version: '0.35.0'
  createServiceAccount: true
  withSpotInterruptionQueue: true

addons:
  - name: vpc-cni
    version: latest
  - name: coredns
    version: latest
  - name: kube-proxy
    version: latest
  - name: aws-ebs-csi-driver
    version: latest
    wellKnownPolicies:
      ebsCSIController: true

cloudWatch:
  clusterLogging:
    enableTypes: ["api", "audit", "authenticator"]
EOF
```

**手順 3.2: Service Cluster を作成する**

```bash
eksctl create cluster -f ~/obs-lab/service-cluster.yaml
```

**手順 3.3: Karpenter NodePool を設定する**

```bash
kubectl config use-context $(kubectl config get-contexts -o name | grep obs-service)

cat <<EOF | kubectl apply -f -
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: default
spec:
  template:
    spec:
      requirements:
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand", "spot"]
        - key: node.kubernetes.io/instance-type
          operator: In
          values: ["m5.large", "m5.xlarge", "m5.2xlarge", "c5.large", "c5.xlarge"]
      nodeClassRef:
        name: default
  limits:
    cpu: 100
    memory: 200Gi
  disruption:
    consolidationPolicy: WhenUnderutilized
    consolidateAfter: 30s
---
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: default
spec:
  amiFamily: AL2
  subnetSelectorTerms:
    - tags:
        karpenter.sh/discovery: obs-service
  securityGroupSelectorTerms:
    - tags:
        karpenter.sh/discovery: obs-service
  role: KarpenterNodeRole-obs-service
  tags:
    Environment: lab
    ManagedBy: karpenter
EOF
```

### 確認

```bash
kubectl get nodepools
kubectl get ec2nodeclasses
# Expected: default NodePool and EC2NodeClass created
```

---

## 演習 4: AWS Managed Services のセットアップ

### 手順

**手順 4.1: SQS Queue と SNS Topic を作成する**

```bash
# Create SQS Queue for order events
aws sqs create-queue \
  --queue-name obs-lab-orders \
  --attributes '{
    "VisibilityTimeout": "30",
    "MessageRetentionPeriod": "86400",
    "ReceiveMessageWaitTimeSeconds": "20"
  }' \
  --region $AWS_REGION

# Create SNS Topic for alerts
aws sns create-topic \
  --name obs-lab-alerts \
  --region $AWS_REGION

# Store ARNs
export SQS_QUEUE_URL=$(aws sqs get-queue-url --queue-name obs-lab-orders --query QueueUrl --output text)
export SNS_TOPIC_ARN=$(aws sns list-topics --query "Topics[?contains(TopicArn, 'obs-lab-alerts')].TopicArn" --output text)

echo "SQS Queue URL: $SQS_QUEUE_URL"
echo "SNS Topic ARN: $SNS_TOPIC_ARN"
```

**手順 4.2: Aurora PostgreSQL クラスターを作成する**

```bash
# Create DB subnet group
aws rds create-db-subnet-group \
  --db-subnet-group-name obs-lab-aurora \
  --db-subnet-group-description "Subnet group for obs-lab Aurora" \
  --subnet-ids $(aws ec2 describe-subnets \
    --filters "Name=tag:alpha.eksctl.io/cluster-name,Values=obs-service" \
    --query "Subnets[?MapPublicIpOnLaunch==\`false\`].SubnetId" \
    --output text | tr '\t' ' ')

# Create Aurora cluster
aws rds create-db-cluster \
  --db-cluster-identifier obs-lab-aurora \
  --engine aurora-postgresql \
  --engine-version 15.4 \
  --master-username obsadmin \
  --master-user-password 'ObsLab2026!' \
  --db-subnet-group-name obs-lab-aurora \
  --vpc-security-group-ids $(aws ec2 describe-security-groups \
    --filters "Name=tag:alpha.eksctl.io/cluster-name,Values=obs-service" \
    --query "SecurityGroups[0].GroupId" --output text) \
  --storage-encrypted \
  --region $AWS_REGION

# Create Aurora instance
aws rds create-db-instance \
  --db-instance-identifier obs-lab-aurora-1 \
  --db-cluster-identifier obs-lab-aurora \
  --db-instance-class db.r6g.large \
  --engine aurora-postgresql \
  --region $AWS_REGION

echo "Aurora cluster creation initiated. This takes ~10 minutes."
```

**手順 4.3: MWAA Environment を作成する**

```bash
# Create S3 bucket for MWAA DAGs
aws s3 mb s3://obs-lab-mwaa-${ACCOUNT_ID}-${AWS_REGION}

# Upload placeholder DAG
cat > /tmp/analytics_dag.py << 'DAGEOF'
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'obs-lab',
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'analytics_batch',
    default_args=default_args,
    description='Daily analytics aggregation',
    schedule_interval='0 2 * * *',
    start_date=datetime(2026, 1, 1),
    catchup=False,
) as dag:

    def run_analytics():
        print("Running analytics batch job")

    analytics_task = PythonOperator(
        task_id='run_analytics',
        python_callable=run_analytics,
    )
DAGEOF

aws s3 cp /tmp/analytics_dag.py s3://obs-lab-mwaa-${ACCOUNT_ID}-${AWS_REGION}/dags/

# Note: MWAA environment creation via CLI is complex
# Use AWS Console or Terraform for production
echo "For MWAA setup, use AWS Console: Amazon MWAA > Create environment"
echo "S3 DAGs folder: s3://obs-lab-mwaa-${ACCOUNT_ID}-${AWS_REGION}/dags/"
```

**手順 4.4: Amazon Managed Prometheus（AMP）Workspace を作成する**

```bash
# Create AMP workspace
aws amp create-workspace \
  --alias obs-lab-prometheus \
  --region $AWS_REGION

# Get workspace ID
export AMP_WORKSPACE_ID=$(aws amp list-workspaces \
  --alias obs-lab-prometheus \
  --query "workspaces[0].workspaceId" \
  --output text)

export AMP_REMOTE_WRITE_URL="https://aps-workspaces.${AWS_REGION}.amazonaws.com/workspaces/${AMP_WORKSPACE_ID}/api/v1/remote_write"
export AMP_QUERY_URL="https://aps-workspaces.${AWS_REGION}.amazonaws.com/workspaces/${AMP_WORKSPACE_ID}"

echo "AMP Workspace ID: $AMP_WORKSPACE_ID"
echo "AMP Remote Write URL: $AMP_REMOTE_WRITE_URL"
```

**手順 4.5: Amazon Managed Grafana（AMG）Workspace を作成する**

```bash
# Create AMG workspace (requires SSO or IAM Identity Center)
# Note: AMG creation via CLI requires additional IAM setup
# Use AWS Console for initial setup

echo "For AMG setup, use AWS Console: Amazon Managed Grafana > Create workspace"
echo "Enable data sources: Amazon Managed Prometheus, CloudWatch, X-Ray"
```

**手順 4.6: OpenSearch Domain を作成する**

```bash
# Create OpenSearch domain
aws opensearch create-domain \
  --domain-name obs-lab-logs \
  --engine-version OpenSearch_2.11 \
  --cluster-config '{
    "InstanceType": "m6g.large.search",
    "InstanceCount": 2,
    "DedicatedMasterEnabled": false,
    "ZoneAwarenessEnabled": true,
    "ZoneAwarenessConfig": {
      "AvailabilityZoneCount": 2
    }
  }' \
  --ebs-options '{
    "EBSEnabled": true,
    "VolumeType": "gp3",
    "VolumeSize": 100
  }' \
  --node-to-node-encryption-options Enabled=true \
  --encryption-at-rest-options Enabled=true \
  --domain-endpoint-options '{
    "EnforceHTTPS": true,
    "TLSSecurityPolicy": "Policy-Min-TLS-1-2-2019-07"
  }' \
  --region $AWS_REGION

echo "OpenSearch domain creation initiated. This takes ~15 minutes."
```

### 確認

```bash
# Check SQS
aws sqs get-queue-attributes --queue-url $SQS_QUEUE_URL --attribute-names All

# Check Aurora status
aws rds describe-db-clusters --db-cluster-identifier obs-lab-aurora \
  --query "DBClusters[0].Status"

# Check AMP
aws amp describe-workspace --workspace-id $AMP_WORKSPACE_ID

# Check OpenSearch
aws opensearch describe-domain --domain-name obs-lab-logs \
  --query "DomainStatus.Processing"
```

---

## 演習 5: Managed Cluster 上の ArgoCD セットアップ

### 手順

**手順 5.1: Managed Cluster に切り替える**

```bash
kubectl config use-context $(kubectl config get-contexts -o name | grep obs-managed)
kubectl config current-context
```

**手順 5.2: ArgoCD をインストールする**

```bash
# Create namespace
kubectl create namespace argocd

# Install ArgoCD
helm repo add argo https://argoproj.github.io/argo-helm
helm repo update

helm install argocd argo/argo-cd \
  --namespace argocd \
  --version 6.4.0 \
  --set server.service.type=LoadBalancer \
  --set configs.params."server\.insecure"=true \
  --set controller.metrics.enabled=true \
  --set server.metrics.enabled=true \
  --wait
```

**手順 5.3: ArgoCD の認証情報を取得する**

```bash
# Get admin password
ARGOCD_PASSWORD=$(kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d)

# Get ArgoCD server URL
ARGOCD_SERVER=$(kubectl -n argocd get svc argocd-server \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

echo "ArgoCD URL: http://$ARGOCD_SERVER"
echo "Username: admin"
echo "Password: $ARGOCD_PASSWORD"
```

**手順 5.4: ArgoCD CLI をインストールしてログインする**

```bash
# Install ArgoCD CLI
curl -sSL -o /usr/local/bin/argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
chmod +x /usr/local/bin/argocd

# Login to ArgoCD
argocd login $ARGOCD_SERVER --username admin --password $ARGOCD_PASSWORD --insecure
```

**手順 5.5: Service Cluster を ArgoCD に登録する**

```bash
# Get Service Cluster context name
SERVICE_CONTEXT=$(kubectl config get-contexts -o name | grep obs-service)

# Add Service Cluster to ArgoCD
argocd cluster add $SERVICE_CONTEXT --name obs-service --yes

# Verify cluster registration
argocd cluster list
```

### 確認

```bash
argocd cluster list
# Expected: Two clusters listed (in-cluster and obs-service)
```

---

## 演習 6: Service Cluster 上の Argo Rollouts セットアップ

### 手順

**手順 6.1: Service Cluster に切り替える**

```bash
kubectl config use-context $(kubectl config get-contexts -o name | grep obs-service)
```

**手順 6.2: Argo Rollouts をインストールする**

```bash
# Create namespace
kubectl create namespace argo-rollouts

# Install Argo Rollouts
helm install argo-rollouts argo/argo-rollouts \
  --namespace argo-rollouts \
  --version 2.34.0 \
  --set dashboard.enabled=true \
  --set dashboard.service.type=LoadBalancer \
  --set controller.metrics.enabled=true \
  --wait
```

**手順 6.3: Argo Rollouts Dashboard URL を取得する**

```bash
ROLLOUTS_DASHBOARD=$(kubectl -n argo-rollouts get svc argo-rollouts-dashboard \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

echo "Argo Rollouts Dashboard: http://$ROLLOUTS_DASHBOARD:3100"
```

### 確認

```bash
kubectl get pods -n argo-rollouts
kubectl get svc -n argo-rollouts
# Expected: argo-rollouts-controller and dashboard running
```

---

## 演習 7: IRSA の設定

### 手順

**手順 7.1: Prometheus 用の IRSA を作成する（AMP への remote write）**

```bash
kubectl config use-context $(kubectl config get-contexts -o name | grep obs-managed)

# Create IAM policy for AMP
cat > /tmp/amp-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "aps:RemoteWrite",
        "aps:QueryMetrics",
        "aps:GetSeries",
        "aps:GetLabels",
        "aps:GetMetricMetadata"
      ],
      "Resource": "arn:aws:aps:${AWS_REGION}:${ACCOUNT_ID}:workspace/${AMP_WORKSPACE_ID}"
    }
  ]
}
EOF

aws iam create-policy \
  --policy-name obs-lab-amp-access \
  --policy-document file:///tmp/amp-policy.json

# Create IRSA for prometheus
eksctl create iamserviceaccount \
  --cluster $MANAGED_CLUSTER_NAME \
  --namespace monitoring \
  --name prometheus-server \
  --attach-policy-arn arn:aws:iam::${ACCOUNT_ID}:policy/obs-lab-amp-access \
  --approve
```

**手順 7.2: OpenSearch と CloudWatch 用の IRSA を作成する**

```bash
# Create combined observability policy
cat > /tmp/obs-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "es:ESHttp*"
      ],
      "Resource": "arn:aws:es:${AWS_REGION}:${ACCOUNT_ID}:domain/obs-lab-logs/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogStreams"
      ],
      "Resource": "arn:aws:logs:${AWS_REGION}:${ACCOUNT_ID}:log-group:/obs-lab/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "xray:PutTraceSegments",
        "xray:PutTelemetryRecords"
      ],
      "Resource": "*"
    }
  ]
}
EOF

aws iam create-policy \
  --policy-name obs-lab-logging-access \
  --policy-document file:///tmp/obs-policy.json

# Create IRSA for fluent-bit
eksctl create iamserviceaccount \
  --cluster $MANAGED_CLUSTER_NAME \
  --namespace logging \
  --name fluent-bit \
  --attach-policy-arn arn:aws:iam::${ACCOUNT_ID}:policy/obs-lab-logging-access \
  --approve
```

**手順 7.3: Service Cluster 用の IRSA を作成する（OTel Agent）**

```bash
kubectl config use-context $(kubectl config get-contexts -o name | grep obs-service)

# Create IRSA for OTel agent
eksctl create iamserviceaccount \
  --cluster $SERVICE_CLUSTER_NAME \
  --namespace opentelemetry \
  --name otel-collector \
  --attach-policy-arn arn:aws:iam::${ACCOUNT_ID}:policy/obs-lab-logging-access \
  --approve
```

### 確認

```bash
# Check service accounts
kubectl config use-context $(kubectl config get-contexts -o name | grep obs-managed)
kubectl get sa -n monitoring prometheus-server -o yaml | grep -A5 annotations

kubectl config use-context $(kubectl config get-contexts -o name | grep obs-service)
kubectl get sa -n opentelemetry otel-collector -o yaml | grep -A5 annotations
```

---

## まとめ

このラボでは、以下を実施しました。

| コンポーネント | ステータス | 詳細 |
|-----------|--------|---------|
| Managed Cluster | 作成済み | observability stack を備えた 3x m5.xlarge ノード |
| Service Cluster | 作成済み | 動的スケーリングのために Karpenter を有効化 |
| SQS Queue | 作成済み | イベントメッセージング用の obs-lab-orders |
| SNS Topic | 作成済み | 通知用の obs-lab-alerts |
| Aurora PostgreSQL | 作成済み | db.r6g.large multi-AZ |
| AMP Workspace | 作成済み | Prometheus remote write 用 |
| OpenSearch | 作成済み | 2x m6g.large.search ノード |
| ArgoCD | インストール済み | マルチクラスター Deployment を設定済み |
| Argo Rollouts | インストール済み | Canary Deployment の準備完了 |
| IRSA | 設定済み | セキュアな AWS サービスアクセス |

## クリーンアップ

> **重要**: 継続的なコストを避けるため、すべてのラボを完了した後にクリーンアップを実行してください。

```bash
# Delete EKS clusters (deletes node groups, IRSA, etc.)
eksctl delete cluster -f ~/obs-lab/managed-cluster.yaml --wait
eksctl delete cluster -f ~/obs-lab/service-cluster.yaml --wait

# Delete Aurora
aws rds delete-db-instance --db-instance-identifier obs-lab-aurora-1 --skip-final-snapshot
aws rds delete-db-cluster --db-cluster-identifier obs-lab-aurora --skip-final-snapshot

# Delete OpenSearch
aws opensearch delete-domain --domain-name obs-lab-logs

# Delete AMP
aws amp delete-workspace --workspace-id $AMP_WORKSPACE_ID

# Delete SQS/SNS
aws sqs delete-queue --queue-url $SQS_QUEUE_URL
aws sns delete-topic --topic-arn $SNS_TOPIC_ARN

# Delete S3 bucket (MWAA)
aws s3 rb s3://obs-lab-mwaa-${ACCOUNT_ID}-${AWS_REGION} --force

# Delete IAM policies
aws iam delete-policy --policy-arn arn:aws:iam::${ACCOUNT_ID}:policy/obs-lab-amp-access
aws iam delete-policy --policy-arn arn:aws:iam::${ACCOUNT_ID}:policy/obs-lab-logging-access

# Cleanup local files
rm -rf ~/obs-lab
```

## トラブルシューティング

<details>
<summary>EKS クラスターの作成に失敗する</summary>

- IAM 権限に EKS、EC2、VPC、CloudFormation が含まれていることを確認してください
- リージョン内の VPC/subnet 制限を確認してください
- `eksctl utils describe-stacks --region=$AWS_REGION --cluster=<cluster-name>` を実行してください
</details>

<details>
<summary>ArgoCD が Service Cluster に接続できない</summary>

- 両方のクラスター context が存在することを確認してください: `kubectl config get-contexts`
- クラスターの追加を再実行してください: `argocd cluster add <context> --name obs-service --yes`
- ArgoCD ログを確認してください: `kubectl logs -n argocd -l app.kubernetes.io/name=argocd-server`
</details>

<details>
<summary>IRSA が動作しない</summary>

- OIDC provider が関連付けられていることを確認してください: `aws eks describe-cluster --name <cluster> --query cluster.identity.oidc`
- Service Account の annotations を確認してください: `kubectl get sa <sa-name> -n <namespace> -o yaml`
- IAM role の trust policy に正しい OIDC provider が含まれていることを確認してください
</details>

## 次のステップ

完全な observability stack をデプロイするには、[パート 2: Observability Stack Deployment](./02-observability-stack-lab.md) に進んでください。

## 参考資料

- [EKS Cluster Creation](../../eks/02-eks-cluster-creation-part1.md)
- [EKS Networking](../../eks/03-eks-networking-part1.md)
- [Karpenter Documentation](../../autoscaling/02-karpenter.md)
- [ArgoCD Documentation](../../gitops/argocd/README.md)
