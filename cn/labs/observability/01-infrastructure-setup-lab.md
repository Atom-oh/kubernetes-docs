# 第 1 部分：基础设施设置

> **难度**：中级
> **预计时间**：60 分钟
> **最后更新**：February 22, 2026

## 学习目标

- 使用 Terraform 和 eksctl 预置两个 EKS 集群（Managed 和 Service）
- 配置 AWS Managed Services（Aurora、OpenSearch、AMP、AMG、MWAA、SQS/SNS）
- 设置 ArgoCD 以进行多集群部署
- 配置 IRSA（IAM Roles for Service Accounts），以实现安全的 AWS 访问

## 前提条件

- [ ] 已配置具有适当权限的 AWS CLI
- [ ] 已安装 Terraform >= 1.7
- [ ] 已安装 eksctl >= 0.175
- [ ] 已安装 kubectl >= 1.29
- [ ] 已安装 Helm >= 3.14
- [ ] 已完成 [EKS Cluster Creation](../../eks/02-eks-cluster-creation-part1.md) 学习

> **成本警告**：本实验会创建大量 AWS 资源。预计成本约为 $2.50/小时。完成后请进行完整清理。

---

## 练习 1：环境设置

### 步骤

**步骤 1.1：设置环境变量**

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

**步骤 1.2：创建工作目录**

```bash
mkdir -p ~/obs-lab/{terraform,k8s,scripts}
cd ~/obs-lab
```

**步骤 1.3：验证工具版本**

```bash
aws --version
terraform version
eksctl version
kubectl version --client
helm version
```

---

## 练习 2：Managed Cluster（EKS）设置

### 步骤

**步骤 2.1：创建 VPC 和 EKS 集群配置**

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

**步骤 2.2：创建 Managed Cluster**

```bash
eksctl create cluster -f ~/obs-lab/managed-cluster.yaml
```

> 此过程大约需要 15-20 分钟。

**步骤 2.3：验证集群创建**

```bash
kubectl config use-context $(kubectl config get-contexts -o name | grep obs-managed)
kubectl get nodes -o wide
kubectl get pods -n kube-system
```

### 验证

```bash
kubectl get nodes
# Expected: 3 nodes in Ready state
```

---

## 练习 3：Service Cluster（EKS）设置

### 步骤

**步骤 3.1：创建支持 Karpenter 的 Service Cluster 配置**

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

**步骤 3.2：创建 Service Cluster**

```bash
eksctl create cluster -f ~/obs-lab/service-cluster.yaml
```

**步骤 3.3：配置 Karpenter NodePool**

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

### 验证

```bash
kubectl get nodepools
kubectl get ec2nodeclasses
# Expected: default NodePool and EC2NodeClass created
```

---

## 练习 4：AWS Managed Services 设置

### 步骤

**步骤 4.1：创建 SQS Queue 和 SNS Topic**

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

**步骤 4.2：创建 Aurora PostgreSQL 集群**

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

**步骤 4.3：创建 MWAA Environment**

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

**步骤 4.4：创建 Amazon Managed Prometheus（AMP）Workspace**

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

**步骤 4.5：创建 Amazon Managed Grafana（AMG）Workspace**

```bash
# Create AMG workspace (requires SSO or IAM Identity Center)
# Note: AMG creation via CLI requires additional IAM setup
# Use AWS Console for initial setup

echo "For AMG setup, use AWS Console: Amazon Managed Grafana > Create workspace"
echo "Enable data sources: Amazon Managed Prometheus, CloudWatch, X-Ray"
```

**步骤 4.6：创建 OpenSearch Domain**

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

### 验证

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

## 练习 5：Managed Cluster 上的 ArgoCD 设置

### 步骤

**步骤 5.1：切换到 Managed Cluster**

```bash
kubectl config use-context $(kubectl config get-contexts -o name | grep obs-managed)
kubectl config current-context
```

**步骤 5.2：安装 ArgoCD**

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

**步骤 5.3：获取 ArgoCD 凭证**

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

**步骤 5.4：安装 ArgoCD CLI 并登录**

```bash
# Install ArgoCD CLI
curl -sSL -o /usr/local/bin/argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
chmod +x /usr/local/bin/argocd

# Login to ArgoCD
argocd login $ARGOCD_SERVER --username admin --password $ARGOCD_PASSWORD --insecure
```

**步骤 5.5：使用 ArgoCD 注册 Service Cluster**

```bash
# Get Service Cluster context name
SERVICE_CONTEXT=$(kubectl config get-contexts -o name | grep obs-service)

# Add Service Cluster to ArgoCD
argocd cluster add $SERVICE_CONTEXT --name obs-service --yes

# Verify cluster registration
argocd cluster list
```

### 验证

```bash
argocd cluster list
# Expected: Two clusters listed (in-cluster and obs-service)
```

---

## 练习 6：Service Cluster 上的 Argo Rollouts 设置

### 步骤

**步骤 6.1：切换到 Service Cluster**

```bash
kubectl config use-context $(kubectl config get-contexts -o name | grep obs-service)
```

**步骤 6.2：安装 Argo Rollouts**

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

**步骤 6.3：获取 Argo Rollouts Dashboard URL**

```bash
ROLLOUTS_DASHBOARD=$(kubectl -n argo-rollouts get svc argo-rollouts-dashboard \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

echo "Argo Rollouts Dashboard: http://$ROLLOUTS_DASHBOARD:3100"
```

### 验证

```bash
kubectl get pods -n argo-rollouts
kubectl get svc -n argo-rollouts
# Expected: argo-rollouts-controller and dashboard running
```

---

## 练习 7：IRSA 配置

### 步骤

**步骤 7.1：为 Prometheus 创建 IRSA（远程写入 AMP）**

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

**步骤 7.2：为 OpenSearch 和 CloudWatch 创建 IRSA**

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

**步骤 7.3：为 Service Cluster（OTel Agent）创建 IRSA**

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

### 验证

```bash
# Check service accounts
kubectl config use-context $(kubectl config get-contexts -o name | grep obs-managed)
kubectl get sa -n monitoring prometheus-server -o yaml | grep -A5 annotations

kubectl config use-context $(kubectl config get-contexts -o name | grep obs-service)
kubectl get sa -n opentelemetry otel-collector -o yaml | grep -A5 annotations
```

---

## 总结

在本实验中，你已完成：

| 组件 | 状态 | 详情 |
|-----------|--------|---------|
| Managed Cluster | 已创建 | 3 个 m5.xlarge 节点，配备可观测性堆栈 |
| Service Cluster | 已创建 | 已启用 Karpenter 以进行动态扩缩容 |
| SQS Queue | 已创建 | 用于事件消息传递的 obs-lab-orders |
| SNS Topic | 已创建 | 用于通知的 obs-lab-alerts |
| Aurora PostgreSQL | 已创建 | db.r6g.large 多可用区 |
| AMP Workspace | 已创建 | 用于 Prometheus 远程写入 |
| OpenSearch | 已创建 | 2 个 m6g.large.search 节点 |
| ArgoCD | 已安装 | 已配置多集群部署 |
| Argo Rollouts | 已安装 | 已准备好 Canary 部署 |
| IRSA | 已配置 | 安全的 AWS 服务访问 |

## 清理

> **重要**：完成所有实验后请运行清理，以避免持续产生费用。

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

## 故障排除

<details>
<summary>EKS 集群创建失败</summary>

- 验证 IAM 权限包含 EKS、EC2、VPC、CloudFormation
- 检查所在区域的 VPC/子网限制
- 运行 `eksctl utils describe-stacks --region=$AWS_REGION --cluster=<cluster-name>`
</details>

<details>
<summary>ArgoCD 无法连接到 Service Cluster</summary>

- 验证两个集群上下文均存在：`kubectl config get-contexts`
- 重新运行集群添加：`argocd cluster add <context> --name obs-service --yes`
- 检查 ArgoCD 日志：`kubectl logs -n argocd -l app.kubernetes.io/name=argocd-server`
</details>

<details>
<summary>IRSA 未正常工作</summary>

- 验证 OIDC provider 已关联：`aws eks describe-cluster --name <cluster> --query cluster.identity.oidc`
- 检查 Service Account 注解：`kubectl get sa <sa-name> -n <namespace> -o yaml`
- 验证 IAM role 信任策略包含正确的 OIDC provider
</details>

## 后续步骤

继续学习 [第 2 部分：可观测性堆栈部署](./02-observability-stack-lab.md)，以部署完整的可观测性堆栈。

## 参考资料

- [EKS Cluster Creation](../../eks/02-eks-cluster-creation-part1.md)
- [EKS Networking](../../eks/03-eks-networking-part1.md)
- [Karpenter Documentation](../../autoscaling/02-karpenter.md)
- [ArgoCD Documentation](../../gitops/argocd/README.md)
