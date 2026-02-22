# Part 1: Infrastructure Setup

> **Difficulty**: Intermediate
> **Estimated Time**: 60 minutes
> **Last Updated**: February 2025

## Learning Objectives

- Provision two EKS clusters (Managed and Service) using Terraform and eksctl
- Configure AWS Managed Services (Aurora, OpenSearch, AMP, AMG, MWAA, SQS/SNS)
- Set up ArgoCD for multi-cluster deployment
- Configure IRSA (IAM Roles for Service Accounts) for secure AWS access

## Prerequisites

- [ ] AWS CLI configured with appropriate permissions
- [ ] Terraform >= 1.7 installed
- [ ] eksctl >= 0.175 installed
- [ ] kubectl >= 1.29 installed
- [ ] Helm >= 3.14 installed
- [ ] Completed [EKS Cluster Creation](../../eks/02-eks-cluster-creation-part1.md) learning

> **Cost Warning**: This lab creates significant AWS resources. Estimated cost is ~$2.50/hour. Complete cleanup after finishing.

---

## Exercise 1: Environment Setup

### Steps

**Step 1.1: Set environment variables**

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

**Step 1.2: Create working directory**

```bash
mkdir -p ~/obs-lab/{terraform,k8s,scripts}
cd ~/obs-lab
```

**Step 1.3: Verify tool versions**

```bash
aws --version
terraform version
eksctl version
kubectl version --client
helm version
```

---

## Exercise 2: Managed Cluster (EKS) Setup

### Steps

**Step 2.1: Create VPC and EKS cluster configuration**

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

**Step 2.2: Create Managed Cluster**

```bash
eksctl create cluster -f ~/obs-lab/managed-cluster.yaml
```

> This process takes approximately 15-20 minutes.

**Step 2.3: Verify cluster creation**

```bash
kubectl config use-context $(kubectl config get-contexts -o name | grep obs-managed)
kubectl get nodes -o wide
kubectl get pods -n kube-system
```

### Verification

```bash
kubectl get nodes
# Expected: 3 nodes in Ready state
```

---

## Exercise 3: Service Cluster (EKS) Setup

### Steps

**Step 3.1: Create Service Cluster configuration with Karpenter support**

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

**Step 3.2: Create Service Cluster**

```bash
eksctl create cluster -f ~/obs-lab/service-cluster.yaml
```

**Step 3.3: Configure Karpenter NodePool**

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

### Verification

```bash
kubectl get nodepools
kubectl get ec2nodeclasses
# Expected: default NodePool and EC2NodeClass created
```

---

## Exercise 4: AWS Managed Services Setup

### Steps

**Step 4.1: Create SQS Queue and SNS Topic**

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

**Step 4.2: Create Aurora PostgreSQL cluster**

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

**Step 4.3: Create MWAA Environment**

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

**Step 4.4: Create Amazon Managed Prometheus (AMP) Workspace**

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

**Step 4.5: Create Amazon Managed Grafana (AMG) Workspace**

```bash
# Create AMG workspace (requires SSO or IAM Identity Center)
# Note: AMG creation via CLI requires additional IAM setup
# Use AWS Console for initial setup

echo "For AMG setup, use AWS Console: Amazon Managed Grafana > Create workspace"
echo "Enable data sources: Amazon Managed Prometheus, CloudWatch, X-Ray"
```

**Step 4.6: Create OpenSearch Domain**

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

### Verification

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

## Exercise 5: ArgoCD Setup on Managed Cluster

### Steps

**Step 5.1: Switch to Managed Cluster**

```bash
kubectl config use-context $(kubectl config get-contexts -o name | grep obs-managed)
kubectl config current-context
```

**Step 5.2: Install ArgoCD**

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

**Step 5.3: Get ArgoCD credentials**

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

**Step 5.4: Install ArgoCD CLI and login**

```bash
# Install ArgoCD CLI
curl -sSL -o /usr/local/bin/argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
chmod +x /usr/local/bin/argocd

# Login to ArgoCD
argocd login $ARGOCD_SERVER --username admin --password $ARGOCD_PASSWORD --insecure
```

**Step 5.5: Register Service Cluster with ArgoCD**

```bash
# Get Service Cluster context name
SERVICE_CONTEXT=$(kubectl config get-contexts -o name | grep obs-service)

# Add Service Cluster to ArgoCD
argocd cluster add $SERVICE_CONTEXT --name obs-service --yes

# Verify cluster registration
argocd cluster list
```

### Verification

```bash
argocd cluster list
# Expected: Two clusters listed (in-cluster and obs-service)
```

---

## Exercise 6: Argo Rollouts Setup on Service Cluster

### Steps

**Step 6.1: Switch to Service Cluster**

```bash
kubectl config use-context $(kubectl config get-contexts -o name | grep obs-service)
```

**Step 6.2: Install Argo Rollouts**

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

**Step 6.3: Get Argo Rollouts Dashboard URL**

```bash
ROLLOUTS_DASHBOARD=$(kubectl -n argo-rollouts get svc argo-rollouts-dashboard \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

echo "Argo Rollouts Dashboard: http://$ROLLOUTS_DASHBOARD:3100"
```

### Verification

```bash
kubectl get pods -n argo-rollouts
kubectl get svc -n argo-rollouts
# Expected: argo-rollouts-controller and dashboard running
```

---

## Exercise 7: IRSA Configuration

### Steps

**Step 7.1: Create IRSA for Prometheus (remote write to AMP)**

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

**Step 7.2: Create IRSA for OpenSearch and CloudWatch**

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

**Step 7.3: Create IRSA for Service Cluster (OTel Agent)**

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

### Verification

```bash
# Check service accounts
kubectl config use-context $(kubectl config get-contexts -o name | grep obs-managed)
kubectl get sa -n monitoring prometheus-server -o yaml | grep -A5 annotations

kubectl config use-context $(kubectl config get-contexts -o name | grep obs-service)
kubectl get sa -n opentelemetry otel-collector -o yaml | grep -A5 annotations
```

---

## Summary

In this lab, you have:

| Component | Status | Details |
|-----------|--------|---------|
| Managed Cluster | Created | 3x m5.xlarge nodes with observability stack |
| Service Cluster | Created | Karpenter-enabled for dynamic scaling |
| SQS Queue | Created | obs-lab-orders for event messaging |
| SNS Topic | Created | obs-lab-alerts for notifications |
| Aurora PostgreSQL | Created | db.r6g.large multi-AZ |
| AMP Workspace | Created | For Prometheus remote write |
| OpenSearch | Created | 2x m6g.large.search nodes |
| ArgoCD | Installed | Multi-cluster deployment configured |
| Argo Rollouts | Installed | Canary deployment ready |
| IRSA | Configured | Secure AWS service access |

## Cleanup

> **Important**: Run cleanup after completing all labs to avoid ongoing costs.

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

## Troubleshooting

<details>
<summary>EKS cluster creation fails</summary>

- Verify IAM permissions include EKS, EC2, VPC, CloudFormation
- Check VPC/subnet limits in your region
- Run `eksctl utils describe-stacks --region=$AWS_REGION --cluster=<cluster-name>`
</details>

<details>
<summary>ArgoCD cannot connect to Service Cluster</summary>

- Verify both cluster contexts exist: `kubectl config get-contexts`
- Re-run cluster addition: `argocd cluster add <context> --name obs-service --yes`
- Check ArgoCD logs: `kubectl logs -n argocd -l app.kubernetes.io/name=argocd-server`
</details>

<details>
<summary>IRSA not working</summary>

- Verify OIDC provider is associated: `aws eks describe-cluster --name <cluster> --query cluster.identity.oidc`
- Check service account annotations: `kubectl get sa <sa-name> -n <namespace> -o yaml`
- Verify IAM role trust policy includes the correct OIDC provider
</details>

## Next Steps

Continue to [Part 2: Observability Stack Deployment](./02-observability-stack-lab.md) to deploy the complete observability stack.

## References

- [EKS Cluster Creation](../../eks/02-eks-cluster-creation-part1.md)
- [EKS Networking](../../eks/03-eks-networking-part1.md)
- [Karpenter Documentation](../../autoscaling/02-karpenter.md)
- [ArgoCD Documentation](../../gitops/argocd/README.md)
