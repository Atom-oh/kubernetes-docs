# Parte 1: Configuración de la infraestructura

> **Dificultad**: Intermedia
> **Tiempo estimado**: 60 minutos
> **Última actualización**: February 22, 2026

## Objetivos de aprendizaje

- Aprovisionar dos clusters EKS (Managed y Service) mediante Terraform y eksctl
- Configurar servicios administrados de AWS (Aurora, OpenSearch, AMP, AMG, MWAA, SQS/SNS)
- Configurar ArgoCD para el despliegue en múltiples clusters
- Configurar IRSA (IAM Roles for Service Accounts) para un acceso seguro a AWS

## Requisitos previos

- [ ] AWS CLI configurado con los permisos adecuados
- [ ] Terraform >= 1.7 instalado
- [ ] eksctl >= 0.175 instalado
- [ ] kubectl >= 1.29 instalado
- [ ] Helm >= 3.14 instalado
- [ ] Haber completado el aprendizaje de [Creación de clusters EKS](../../eks/02-eks-cluster-creation-part1.md)

> **Advertencia de costos**: Este laboratorio crea recursos de AWS significativos. El costo estimado es de ~$2.50/hora. Realiza la limpieza al finalizar.

---

## Ejercicio 1: Configuración del entorno

### Pasos

**Paso 1.1: Configurar variables de entorno**

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

**Paso 1.2: Crear directorio de trabajo**

```bash
mkdir -p ~/obs-lab/{terraform,k8s,scripts}
cd ~/obs-lab
```

**Paso 1.3: Verificar las versiones de las herramientas**

```bash
aws --version
terraform version
eksctl version
kubectl version --client
helm version
```

---

## Ejercicio 2: Configuración del Managed Cluster (EKS)

### Pasos

**Paso 2.1: Crear la configuración de VPC y del cluster EKS**

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

**Paso 2.2: Crear el Managed Cluster**

```bash
eksctl create cluster -f ~/obs-lab/managed-cluster.yaml
```

> Este proceso tarda aproximadamente 15-20 minutos.

**Paso 2.3: Verificar la creación del cluster**

```bash
kubectl config use-context $(kubectl config get-contexts -o name | grep obs-managed)
kubectl get nodes -o wide
kubectl get pods -n kube-system
```

### Verificación

```bash
kubectl get nodes
# Expected: 3 nodes in Ready state
```

---

## Ejercicio 3: Configuración del Service Cluster (EKS)

### Pasos

**Paso 3.1: Crear la configuración del Service Cluster con soporte para Karpenter**

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

**Paso 3.2: Crear el Service Cluster**

```bash
eksctl create cluster -f ~/obs-lab/service-cluster.yaml
```

**Paso 3.3: Configurar el NodePool de Karpenter**

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

### Verificación

```bash
kubectl get nodepools
kubectl get ec2nodeclasses
# Expected: default NodePool and EC2NodeClass created
```

---

## Ejercicio 4: Configuración de servicios administrados de AWS

### Pasos

**Paso 4.1: Crear una SQS Queue y un SNS Topic**

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

**Paso 4.2: Crear un cluster Aurora PostgreSQL**

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

**Paso 4.3: Crear un entorno MWAA**

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

**Paso 4.4: Crear un Workspace de Amazon Managed Prometheus (AMP)**

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

**Paso 4.5: Crear un Workspace de Amazon Managed Grafana (AMG)**

```bash
# Create AMG workspace (requires SSO or IAM Identity Center)
# Note: AMG creation via CLI requires additional IAM setup
# Use AWS Console for initial setup

echo "For AMG setup, use AWS Console: Amazon Managed Grafana > Create workspace"
echo "Enable data sources: Amazon Managed Prometheus, CloudWatch, X-Ray"
```

**Paso 4.6: Crear un dominio OpenSearch**

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

### Verificación

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

## Ejercicio 5: Configuración de ArgoCD en el Managed Cluster

### Pasos

**Paso 5.1: Cambiar al Managed Cluster**

```bash
kubectl config use-context $(kubectl config get-contexts -o name | grep obs-managed)
kubectl config current-context
```

**Paso 5.2: Instalar ArgoCD**

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

**Paso 5.3: Obtener las credenciales de ArgoCD**

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

**Paso 5.4: Instalar ArgoCD CLI e iniciar sesión**

```bash
# Install ArgoCD CLI
curl -sSL -o /usr/local/bin/argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
chmod +x /usr/local/bin/argocd

# Login to ArgoCD
argocd login $ARGOCD_SERVER --username admin --password $ARGOCD_PASSWORD --insecure
```

**Paso 5.5: Registrar el Service Cluster en ArgoCD**

```bash
# Get Service Cluster context name
SERVICE_CONTEXT=$(kubectl config get-contexts -o name | grep obs-service)

# Add Service Cluster to ArgoCD
argocd cluster add $SERVICE_CONTEXT --name obs-service --yes

# Verify cluster registration
argocd cluster list
```

### Verificación

```bash
argocd cluster list
# Expected: Two clusters listed (in-cluster and obs-service)
```

---

## Ejercicio 6: Configuración de Argo Rollouts en el Service Cluster

### Pasos

**Paso 6.1: Cambiar al Service Cluster**

```bash
kubectl config use-context $(kubectl config get-contexts -o name | grep obs-service)
```

**Paso 6.2: Instalar Argo Rollouts**

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

**Paso 6.3: Obtener la URL del Dashboard de Argo Rollouts**

```bash
ROLLOUTS_DASHBOARD=$(kubectl -n argo-rollouts get svc argo-rollouts-dashboard \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

echo "Argo Rollouts Dashboard: http://$ROLLOUTS_DASHBOARD:3100"
```

### Verificación

```bash
kubectl get pods -n argo-rollouts
kubectl get svc -n argo-rollouts
# Expected: argo-rollouts-controller and dashboard running
```

---

## Ejercicio 7: Configuración de IRSA

### Pasos

**Paso 7.1: Crear IRSA para Prometheus (remote write a AMP)**

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

**Paso 7.2: Crear IRSA para OpenSearch y CloudWatch**

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

**Paso 7.3: Crear IRSA para el Service Cluster (OTel Agent)**

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

### Verificación

```bash
# Check service accounts
kubectl config use-context $(kubectl config get-contexts -o name | grep obs-managed)
kubectl get sa -n monitoring prometheus-server -o yaml | grep -A5 annotations

kubectl config use-context $(kubectl config get-contexts -o name | grep obs-service)
kubectl get sa -n opentelemetry otel-collector -o yaml | grep -A5 annotations
```

---

## Resumen

En este laboratorio, has realizado lo siguiente:

| Componente | Estado | Detalles |
|-----------|--------|---------|
| Managed Cluster | Creado | 3 nodos m5.xlarge con stack de observabilidad |
| Service Cluster | Creado | Karpenter habilitado para escalado dinámico |
| SQS Queue | Creada | obs-lab-orders para mensajería de eventos |
| SNS Topic | Creado | obs-lab-alerts para notificaciones |
| Aurora PostgreSQL | Creado | db.r6g.large multi-AZ |
| AMP Workspace | Creado | Para remote write de Prometheus |
| OpenSearch | Creado | 2 nodos m6g.large.search |
| ArgoCD | Instalado | Despliegue en múltiples clusters configurado |
| Argo Rollouts | Instalado | Despliegue canary preparado |
| IRSA | Configurado | Acceso seguro a servicios de AWS |

## Limpieza

> **Importante**: Ejecuta la limpieza después de completar todos los laboratorios para evitar costos continuos.

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

## Solución de problemas

<details>
<summary>Falla la creación del cluster EKS</summary>

- Verifica que los permisos de IAM incluyan EKS, EC2, VPC y CloudFormation
- Comprueba los límites de VPC/subnet en tu región
- Ejecuta `eksctl utils describe-stacks --region=$AWS_REGION --cluster=<cluster-name>`
</details>

<details>
<summary>ArgoCD no puede conectarse al Service Cluster</summary>

- Verifica que existan ambos contextos de cluster: `kubectl config get-contexts`
- Vuelve a ejecutar la incorporación del cluster: `argocd cluster add <context> --name obs-service --yes`
- Revisa los logs de ArgoCD: `kubectl logs -n argocd -l app.kubernetes.io/name=argocd-server`
</details>

<details>
<summary>IRSA no funciona</summary>

- Verifica que el proveedor de OIDC esté asociado: `aws eks describe-cluster --name <cluster> --query cluster.identity.oidc`
- Comprueba las anotaciones de la service account: `kubectl get sa <sa-name> -n <namespace> -o yaml`
- Verifica que la política de confianza de IAM incluya el proveedor de OIDC correcto
</details>

## Próximos pasos

Continúa con la [Parte 2: Despliegue del stack de observabilidad](./02-observability-stack-lab.md) para desplegar el stack de observabilidad completo.

## Referencias

- [Creación de clusters EKS](../../eks/02-eks-cluster-creation-part1.md)
- [Redes de EKS](../../eks/03-eks-networking-part1.md)
- [Documentación de Karpenter](../../autoscaling/02-karpenter.md)
- [Documentación de ArgoCD](../../gitops/argocd/README.md)
