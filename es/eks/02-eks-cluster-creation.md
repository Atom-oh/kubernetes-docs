# EKS Cluster Creation

Hay varias formas de crear un Amazon EKS cluster (clúster). En este capítulo, aprenderemos en detalle cómo crear un EKS cluster usando varias herramientas y métodos.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Creating a Cluster Using eksctl](#creating-a-cluster-using-eksctl)
3. [Creating a Cluster Using AWS Management Console](#creating-a-cluster-using-aws-management-console)
4. [Creating a Cluster Using AWS CLI](#creating-a-cluster-using-aws-cli)
5. [Creating a Cluster Using Terraform](#creating-a-cluster-using-terraform)
6. [Creating a Cluster Using AWS CDK](#creating-a-cluster-using-aws-cdk)
7. [Configuring Cluster Access](#configuring-cluster-access)
8. [Cluster Validation](#cluster-validation)
9. [Cluster Upgrade](#cluster-upgrade)
10. [Cluster Deletion](#cluster-deletion)

## Prerequisites

Antes de crear un EKS cluster, se requieren los siguientes requisitos previos:

### 1. AWS Account

Se requiere una AWS account válida. Si no tienes una AWS account, puedes registrarte en el [sitio web de AWS](https://aws.amazon.com/).

### 2. IAM Permissions

Se requieren los siguientes IAM permissions para crear y administrar un EKS cluster:

- `eks:*`
- `ec2:*`
- `iam:*`
- `cloudformation:*`

Si tienes permisos de administrator, no se requieren configuraciones de permisos adicionales. De lo contrario, debes adjuntar la siguiente IAM policy al user o role:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "eks:*",
        "ec2:*",
        "iam:*",
        "cloudformation:*"
      ],
      "Resource": "*"
    }
  ]
}
```

### 3. Tool Installation

Las siguientes herramientas deben estar instaladas para crear y administrar un EKS cluster:

#### AWS CLI

AWS CLI es una herramienta unificada para controlar AWS services desde la línea de comandos.

**macOS**:
```bash
curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"
sudo installer -pkg AWSCLIV2.pkg -target /
```

**Linux**:
```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
```

**Windows**:
```
https://awscli.amazonaws.com/AWSCLIV2.msi
```

Después de instalar AWS CLI, ejecuta el siguiente comando para configurar las credenciales:
```bash
aws configure
```

#### kubectl

kubectl es una herramienta de línea de comandos para comunicarse con Kubernetes clusters.

**macOS**:
```bash
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/darwin/amd64/kubectl"
chmod +x ./kubectl
sudo mv ./kubectl /usr/local/bin/kubectl
```

**Linux**:
```bash
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x ./kubectl
sudo mv ./kubectl /usr/local/bin/kubectl
```

**Windows**:
```bash
curl -LO "https://dl.k8s.io/release/v1.26.0/bin/windows/amd64/kubectl.exe"
```

#### eksctl

eksctl es una herramienta CLI sencilla para crear y administrar EKS clusters.

**macOS**:
```bash
brew tap weaveworks/tap
brew install weaveworks/tap/eksctl
```

O:
```bash
curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin
```

**Linux**:
```bash
curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin
```

**Windows**:
```bash
# PowerShell
$version = (Invoke-WebRequest -Uri "https://api.github.com/repos/weaveworks/eksctl/releases/latest" | ConvertFrom-Json).tag_name
Invoke-WebRequest -Uri "https://github.com/weaveworks/eksctl/releases/download/$version/eksctl_Windows_amd64.zip" -OutFile eksctl.zip
Expand-Archive -Path eksctl.zip -DestinationPath $env:USERPROFILE\.eksctl\bin
$env:PATH += ";$env:USERPROFILE\.eksctl\bin"
```

### 4. VPC and Subnets

Un EKS cluster requiere una VPC y subnets. Puedes usar una VPC existente o crear una nueva. La VPC para un EKS cluster debe cumplir los siguientes requisitos:

- Al menos 2 subnets deben estar en diferentes availability zones.
- Las subnets deben tener acceso a internet (mediante un NAT gateway o internet gateway).
- Las subnets deben tener suficientes direcciones IP.
- Las subnets deben tener tags adecuados.

#### VPC Tags for EKS Cluster

Los siguientes tags deben aplicarse para permitir que el EKS cluster use correctamente la VPC y las subnets:

**VPC Tags**:
- `kubernetes.io/cluster/<cluster-name>`: `shared` o `owned`

**Public Subnet Tags**:
- `kubernetes.io/cluster/<cluster-name>`: `shared` o `owned`
- `kubernetes.io/role/elb`: `1`

**Private Subnet Tags**:
- `kubernetes.io/cluster/<cluster-name>`: `shared` o `owned`
- `kubernetes.io/role/internal-elb`: `1`

## Creating a Cluster Using eksctl

eksctl es la forma más sencilla de crear y administrar EKS clusters. eksctl usa CloudFormation para crear EKS clusters y recursos relacionados.

### Basic Cluster Creation

Para crear la forma más básica de un EKS cluster, ejecuta el siguiente comando:

```bash
eksctl create cluster --name my-cluster --region us-west-2
```

Este comando crea un cluster con la siguiente configuración predeterminada:
- 2 nodes m5.large
- Nueva VPC y subnets
- AMI predeterminada de Amazon Linux 2
- Última versión de Kubernetes

### Creating a Cluster Using a Configuration File

Para configuraciones más complejas, puedes definir el cluster usando un archivo YAML:

```yaml
# cluster.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: my-eks-cluster
  region: us-west-2
  version: "1.26"

vpc:
  id: vpc-12345678
  subnets:
    private:
      us-west-2a:
        id: subnet-12345678
      us-west-2b:
        id: subnet-87654321
    public:
      us-west-2a:
        id: subnet-23456789
      us-west-2b:
        id: subnet-98765432

managedNodeGroups:
  - name: ng-1
    instanceType: m5.large
    desiredCapacity: 2
    minSize: 1
    maxSize: 3
    privateNetworking: true
    volumeSize: 80
    volumeType: gp3
    iam:
      withAddonPolicies:
        imageBuilder: true
        autoScaler: true
        externalDNS: true
        certManager: true
        appMesh: true
        ebs: true
        fsx: true
        efs: true
        albIngress: true
        xRay: true
        cloudWatch: true

  - name: ng-2
    instanceType: c5.xlarge
    desiredCapacity: 2
    privateNetworking: true
    spot: true

autoModeConfig:
  enabled: true
  # Create default node pools (general-purpose, system)
  # If nodePools is not specified, defaults are used
  # nodePools: ["general-purpose", "system"]
  # nodeRoleARN: arn:aws:iam::123456789012:role/AmazonEKSAutoNodeRole

fargate:
  profiles:
    - name: fp-default
      selectors:
        - namespace: default
          labels:
            env: fargate
    - name: fp-kube-system
      selectors:
        - namespace: kube-system
          labels:
            k8s-app: kube-dns

cloudWatch:
  clusterLogging:
    enableTypes: ["api", "audit", "authenticator", "controllerManager", "scheduler"]
```

Para crear un cluster usando este archivo de configuración, ejecuta el siguiente comando:

```bash
eksctl create cluster -f cluster.yaml
```

### Creating Managed Node Groups

Para agregar un managed node group a un cluster existente, ejecuta el siguiente comando:

```bash
eksctl create nodegroup \
  --cluster my-cluster \
  --region us-west-2 \
  --name my-nodegroup \
  --node-type m5.large \
  --nodes 3 \
  --nodes-min 1 \
  --nodes-max 5 \
  --ssh-access \
  --ssh-public-key my-key
```

O puedes usar un archivo de configuración:

```yaml
# nodegroup.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: my-cluster
  region: us-west-2

managedNodeGroups:
  - name: my-nodegroup
    instanceType: m5.large
    desiredCapacity: 3
    minSize: 1
    maxSize: 5
    volumeSize: 80
    volumeType: gp3
    ssh:
      allow: true
      publicKeyName: my-key
```

```bash
eksctl create nodegroup -f nodegroup.yaml
```

### Creating an EKS Auto Mode Cluster

EKS Auto Mode es una nueva característica lanzada en 2024 que automatiza la infraestructura de Kubernetes cluster para reducir significativamente la sobrecarga operativa. Auto Mode gestiona automáticamente la infraestructura, incluidos compute, networking y storage.

#### Key Features of EKS Auto Mode

- **Automated Node Management**: Agrega/elimina nodes automáticamente según los requisitos de workload
- **Enhanced Security**: AMI inmutable, modo SELinux enforcing, sistema de archivos raíz de solo lectura
- **Automatic Upgrades**: Parches y actualizaciones de seguridad regulares con una vida útil máxima de node de 21 días
- **Integrated Components**: Pod networking, DNS, storage y soporte de GPU proporcionados de forma predeterminada
- **Cost Optimization**: Terminación automática de instancias no utilizadas y consolidación de workload

#### Basic Auto Mode Cluster Creation

```bash
eksctl create cluster --name my-auto-cluster --enable-auto-mode --region us-west-2
```

#### Creating an Auto Mode Cluster Using a Configuration File

```yaml
# auto-cluster.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: my-auto-cluster
  region: us-west-2
  version: "1.31"

# EKS Auto Mode configuration
autoModeConfig:
  enabled: true
  # Create default node pools (general-purpose, system)
  # If nodePools is not specified, defaults are used
  # nodePools: ["general-purpose", "system"]
  # nodeRoleARN: arn:aws:iam::123456789012:role/AmazonEKSAutoNodeRole

# VPC configuration (optional)
vpc:
  cidr: "10.0.0.0/16"
  nat:
    gateway: Single # Or HighlyAvailable
  clusterEndpoints:
    privateAccess: true
    publicAccess: true

# Cluster logging
cloudWatch:
  clusterLogging:
    enableTypes: ["api", "audit", "authenticator", "controllerManager", "scheduler"]

# Add-on configuration
addons:
  - name: vpc-cni
    version: latest
  - name: coredns
    version: latest
  - name: kube-proxy
    version: latest
  - name: aws-ebs-csi-driver
    version: latest
```

Crear cluster:
```bash
eksctl create cluster -f auto-cluster.yaml
```

#### Auto Mode vs Traditional Approach Comparison

| Feature | Traditional EKS | EKS Auto Mode |
|---------|-----------------|---------------|
| Node Management | Manual managed node groups | Automatic node management |
| Scaling | Cluster Autoscaler setup required | Built-in auto scaling |
| Upgrades | Manual upgrades | Automatic upgrades (21-day cycle) |
| Security | User configured | Enhanced security by default |
| Networking | CNI plugin setup | Automatic networking configuration |
| Storage | CSI driver installation required | EBS CSI automatically provided |
| GPU Support | Manual driver installation | Automatic GPU support |

#### Auto Mode Cluster Validation

Después de crear el cluster, puedes comprobar su estado con los siguientes comandos:

```bash
# Check cluster status
kubectl get nodes

# Check Auto Mode node pools
kubectl get nodepools

# Check Auto Mode node classes
kubectl get nodeclasses

# Check system pod status
kubectl get pods -n kube-system
```

#### Creating Custom Node Pools

En Auto Mode, puedes crear node pools personalizados además de los node pools predeterminados:

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: gpu-nodepool
spec:
  template:
    metadata:
      labels:
        workload-type: gpu
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
        - key: node.kubernetes.io/instance-type
          operator: In
          values: ["p3.2xlarge", "p3.8xlarge"]
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: gpu-nodeclass
  limits:
    cpu: 1000
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
---
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: gpu-nodeclass
spec:
  amiFamily: AL2
  instanceStorePolicy: RAID0
  userData: |
    #!/bin/bash
    /etc/eks/bootstrap.sh my-auto-cluster
```

#### Auto Mode Limitations

- Sin acceso directo a nodes mediante SSH o SSM
- Vida útil máxima del node de 21 días (reemplazo automático)
- No se pueden modificar los node pools y node classes predeterminados
- Es posible que existan restricciones para ciertos instance types

#### Auto Mode Monitoring

Los Auto Mode clusters están integrados con CloudWatch y recopilan métricas automáticamente:

```bash
# Check CloudWatch metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/EKS \
  --metric-name cluster_node_count \
  --dimensions Name=ClusterName,Value=my-auto-cluster \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-01T23:59:59Z \
  --period 3600 \
  --statistics Average
```

### Creating Fargate Profiles

Para crear un Fargate profile, ejecuta el siguiente comando:

```bash
eksctl create fargateprofile \
  --cluster my-cluster \
  --region us-west-2 \
  --name my-fargate-profile \
  --namespace default \
  --labels env=fargate
```

O puedes usar un archivo de configuración:

```yaml
# fargate.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: my-cluster
  region: us-west-2

fargate:
  profiles:
    - name: my-fargate-profile
      selectors:
        - namespace: default
          labels:
            env: fargate
```

```bash
eksctl create fargateprofile -f fargate.yaml
```

### Updating a Cluster

Puedes actualizar un cluster existente usando eksctl:

```bash
# Upgrade cluster version
eksctl upgrade cluster --name=my-cluster --version=1.27

# Upgrade node group
eksctl upgrade nodegroup --cluster=my-cluster --name=my-nodegroup
```

### Deleting a Cluster

Puedes eliminar un cluster usando eksctl:

```bash
eksctl delete cluster --name=my-cluster --region=us-west-2
```

## Creating a Cluster Using AWS Management Console

Los pasos para crear un EKS cluster usando AWS Management Console son los siguientes:

1. Inicia sesión en [AWS Management Console](https://console.aws.amazon.com/).
2. Busca "EKS" o selecciona "Elastic Kubernetes Service" en la lista de servicios.
3. En la página "Clusters", haz clic en el botón "Create cluster".

### Creating an EKS Auto Mode Cluster (Quick Configuration)

Usando EKS Auto Mode, puedes crear un cluster listo para producción con una configuración mínima.

#### 1. Select Quick Configuration

4. Asegúrate de que la opción "Quick configuration" esté seleccionada.
5. Ingresa la siguiente información:
   - **Nombre del cluster**: Ingresa un nombre único para el cluster.
   - **Versión de Kubernetes**: Selecciona la versión de Kubernetes que se usará (se recomienda la versión más reciente).

#### 2. Configure IAM Roles

6. Selección de **Cluster IAM role**:
   - Para tu primer Auto Mode cluster, usa la opción "Create recommended role".
   - Si tienes un role existente, puedes reutilizarlo.
   - Nombre de role recomendado: `AmazonEKSAutoClusterRole`

7. Selección de **Node IAM role**:
   - Para tu primer Auto Mode cluster, usa la opción "Create recommended role".
   - Nombre de role recomendado: `AmazonEKSAutoNodeRole`

#### 3. Configure Networking

8. **Seleccionar VPC**:
   - Crear nueva VPC: Selecciona la opción "Create VPC" para crear una nueva VPC para EKS.
   - Usar VPC existente: Selecciona una VPC de EKS creada previamente.

9. **Configuración de Subnet** (opcional):
   - EKS Auto Mode selecciona automáticamente private subnets en la VPC.
   - Puedes agregar o quitar subnets según sea necesario.

#### 4. Review Configuration and Create

10. Selecciona **View quick configuration defaults** para revisar todos los valores de configuración.
11. Haz clic en **Create cluster**. (La creación del cluster tarda aproximadamente 15 minutos)

### Creating a Cluster with Custom Configuration

Si necesitas un control más granular, puedes usar una configuración personalizada.

### Cluster Configuration

4. En la página "Configure cluster", ingresa la siguiente información:
   - **Nombre del cluster**: Ingresa un nombre único para el cluster.
   - **Versión de Kubernetes**: Selecciona la versión de Kubernetes que se usará.
   - **Cluster service role**: Crea un nuevo role o selecciona un role existente.
   - **EKS Auto Mode**: Marca la casilla para habilitar Auto Mode.
   - **Tags**: Agrega tags si es necesario.
   - Haz clic en el botón "Next".

### Specify Networking

5. En la página "Specify networking", ingresa la siguiente información:
   - **VPC**: Crea una nueva VPC o selecciona una VPC existente.
   - **Subnets**: Selecciona las subnets que se usarán para el cluster. Al menos 2 subnets deben estar en diferentes availability zones.
   - **Security groups**: Selecciona los security groups que se usarán para el cluster.
   - **Cluster endpoint access**: Configura el acceso al endpoint del API server del cluster.
     - **Public**: Se puede acceder al API server desde internet.
     - **Private**: Solo se puede acceder al API server desde dentro de la VPC.
     - **Public and Private**: Se puede acceder al API server tanto desde internet como desde dentro de la VPC.
   - Haz clic en el botón "Next".

### Configure Logging

6. En la página "Configure logging", ingresa la siguiente información:
   - **Control plane logging**: Selecciona los tipos de log que se habilitarán.
     - API server logs
     - Audit logs
     - Authenticator logs
     - Controller manager logs
     - Scheduler logs
   - Haz clic en el botón "Next".

### Select Add-ons

7. En la página "Select add-ons", ingresa la siguiente información:
   - **Amazon VPC CNI**: Plugin CNI para pod networking.
   - **CoreDNS**: Servicio DNS dentro del cluster.
   - **kube-proxy**: Proporciona proxy de red y balanceo de carga.
   - **Amazon EBS CSI Driver**: Incluido automáticamente en EKS Auto Mode.
   - Haz clic en el botón "Next".

### Review and Create

8. En la página "Review and create", revisa la configuración y haz clic en el botón "Create".

### Adding Node Groups for Non-Auto Mode Clusters

Si no estás usando EKS Auto Mode, debes agregar manualmente node groups después de la creación del cluster.

### Add Node Group

1. En la página "Node group configuration", ingresa la siguiente información:
   - **Nombre del node group**: Ingresa un nombre único para el node group.
   - **Node IAM role**: Crea un nuevo role o selecciona un role existente.
   - Haz clic en el botón "Next".

2. En la página "Set compute and scaling configuration", ingresa la siguiente información:
   - **Tipo de AMI**: Selecciona el tipo de AMI que se usará para los nodes.
   - **Instance type**: Selecciona el tipo de EC2 instance que se usará para los nodes.
   - **Tamaño de disco**: Especifica el tamaño de disco para los nodes.
   - **Node count**: Especifica el número mínimo, máximo y deseado de nodes.
   - Haz clic en el botón "Next".

3. En la página "Specify networking", ingresa la siguiente información:
   - **Subnets**: Selecciona las subnets que se usarán para el node group.
   - **Remote access configuration**: Configura el acceso SSH.
   - Haz clic en el botón "Next".

4. En la página "Review and create", revisa la configuración y haz clic en el botón "Create".

## Creating a Cluster Using AWS CLI

Puedes crear un EKS cluster usando AWS CLI. Este método es útil para automatización con scripts o pipelines CI/CD.

### Creating an EKS Auto Mode Cluster

#### 1. Create Cluster

```bash
# Create Auto Mode cluster
aws eks create-cluster \
  --name my-auto-cluster \
  --version 1.31 \
  --role-arn arn:aws:iam::123456789012:role/AmazonEKSAutoClusterRole \
  --resources-vpc-config subnetIds=subnet-12345,subnet-67890 \
  --access-config authenticationMode=API_AND_CONFIG_MAP \
  --compute-config nodeRoleArn=arn:aws:iam::123456789012:role/AmazonEKSAutoNodeRole \
  --storage-config blockStorage='{enabled=true}' \
  --kubernetes-network-config ipFamily=ipv4 \
  --region us-west-2
```

#### 2. Check Cluster Status

```bash
# Check cluster status
aws eks describe-cluster --name my-auto-cluster --region us-west-2

# Wait until cluster is ACTIVE
aws eks wait cluster-active --name my-auto-cluster --region us-west-2
```

#### 3. Update kubeconfig

```bash
# Update kubeconfig
aws eks update-kubeconfig --name my-auto-cluster --region us-west-2

# Verify cluster connection
kubectl get nodes
```

### Creating a Traditional Cluster

Así es como se crea un cluster sin usar Auto Mode.

#### Basic Cluster Creation

```bash
aws eks create-cluster \
  --name my-cluster \
  --version 1.31 \
  --role-arn arn:aws:iam::123456789012:role/eks-service-role \
  --resources-vpc-config subnetIds=subnet-12345,subnet-67890,endpointConfigPrivateAccess=true,endpointConfigPublicAccess=true \
  --region us-west-2
```

#### Check Cluster Status

```bash
aws eks describe-cluster --name my-cluster --region us-west-2
```

Una vez creado el cluster, el estado cambia a `ACTIVE`. Este proceso tarda aproximadamente entre 10 y 15 minutos.

#### Update kubeconfig

```bash
aws eks update-kubeconfig --name my-cluster --region us-west-2
```

#### Create Managed Node Group

```bash
aws eks create-nodegroup \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup \
  --subnets subnet-12345 subnet-67890 \
  --instance-types m5.large \
  --ami-type AL2_x86_64 \
  --node-role arn:aws:iam::123456789012:role/NodeInstanceRole \
  --scaling-config minSize=1,maxSize=3,desiredSize=2 \
  --disk-size 20 \
  --remote-access ec2SshKey=my-key \
  --region us-west-2
```

#### Check Node Group Status

```bash
aws eks describe-nodegroup \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup \
  --region us-west-2
```

## Creating a Cluster Using Terraform

Usar Terraform para crear un EKS cluster te permite administrar infrastructure as code.

### EKS Auto Mode Cluster Terraform Configuration

```hcl
# main.tf
terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

# VPC and subnet data sources
data "aws_vpc" "selected" {
  id = var.vpc_id
}

data "aws_subnets" "private" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.selected.id]
  }

  tags = {
    Type = "Private"
  }
}

# EKS Auto Mode cluster
resource "aws_eks_cluster" "auto_mode" {
  name     = var.cluster_name
  role_arn = aws_iam_role.cluster.arn
  version  = var.kubernetes_version

  vpc_config {
    subnet_ids              = data.aws_subnets.private.ids
    endpoint_private_access = true
    endpoint_public_access  = true
  }

  # EKS Auto Mode configuration
  compute_config {
    enabled      = true
    node_role_arn = aws_iam_role.node.arn
  }

  storage_config {
    block_storage {
      enabled = true
    }
  }

  access_config {
    authentication_mode = "API_AND_CONFIG_MAP"
  }

  enabled_cluster_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]

  depends_on = [
    aws_iam_role_policy_attachment.cluster_AmazonEKSClusterPolicy,
    aws_iam_role_policy_attachment.node_AmazonEKSWorkerNodePolicy,
    aws_iam_role_policy_attachment.node_AmazonEKS_CNI_Policy,
    aws_iam_role_policy_attachment.node_AmazonEC2ContainerRegistryReadOnly,
  ]

  tags = var.tags
}

# Cluster IAM role
resource "aws_iam_role" "cluster" {
  name = "${var.cluster_name}-cluster-role"

  assume_role_policy = jsonencode({
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "eks.amazonaws.com"
      }
    }]
    Version = "2012-10-17"
  })
}

resource "aws_iam_role_policy_attachment" "cluster_AmazonEKSClusterPolicy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
  role       = aws_iam_role.cluster.name
}

# Node IAM role
resource "aws_iam_role" "node" {
  name = "${var.cluster_name}-node-role"

  assume_role_policy = jsonencode({
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
    }]
    Version = "2012-10-17"
  })
}

resource "aws_iam_role_policy_attachment" "node_AmazonEKSWorkerNodePolicy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
  role       = aws_iam_role.node.name
}

resource "aws_iam_role_policy_attachment" "node_AmazonEKS_CNI_Policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
  role       = aws_iam_role.node.name
}

resource "aws_iam_role_policy_attachment" "node_AmazonEC2ContainerRegistryReadOnly" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
  role       = aws_iam_role.node.name
}

# Variable definitions
variable "cluster_name" {
  description = "EKS cluster name"
  type        = string
  default     = "my-auto-cluster"
}

variable "kubernetes_version" {
  description = "Kubernetes version"
  type        = string
  default     = "1.31"
}

variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default = {
    Environment = "dev"
    Project     = "eks-auto-mode"
  }
}

# Outputs
output "cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = aws_eks_cluster.auto_mode.endpoint
}

output "cluster_security_group_id" {
  description = "EKS cluster security group ID"
  value       = aws_eks_cluster.auto_mode.vpc_config[0].cluster_security_group_id
}

output "cluster_arn" {
  description = "EKS cluster ARN"
  value       = aws_eks_cluster.auto_mode.arn
}
```

### Running Terraform

```bash
# Initialize Terraform
terraform init

# Review plan
terraform plan -var="vpc_id=vpc-12345678"

# Apply
terraform apply -var="vpc_id=vpc-12345678"

# Update kubeconfig
aws eks update-kubeconfig --name my-auto-cluster --region us-west-2
```

### Traditional Terraform Configuration

Esta es la configuración de Terraform para no usar Auto Mode:

```hcl
# Traditional EKS cluster
resource "aws_eks_cluster" "main" {
  name     = var.cluster_name
  role_arn = aws_iam_role.cluster.arn
  version  = var.kubernetes_version

  vpc_config {
    subnet_ids              = data.aws_subnets.private.ids
    endpoint_private_access = true
    endpoint_public_access  = true
  }

  enabled_cluster_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]

  depends_on = [
    aws_iam_role_policy_attachment.cluster_AmazonEKSClusterPolicy,
  ]

  tags = var.tags
}

# Managed node group
resource "aws_eks_node_group" "main" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "main-nodegroup"
  node_role_arn   = aws_iam_role.node.arn
  subnet_ids      = data.aws_subnets.private.ids

  capacity_type  = "ON_DEMAND"
  instance_types = ["m5.large"]

  scaling_config {
    desired_size = 2
    max_size     = 3
    min_size     = 1
  }

  update_config {
    max_unavailable = 1
  }

  depends_on = [
    aws_iam_role_policy_attachment.node_AmazonEKSWorkerNodePolicy,
    aws_iam_role_policy_attachment.node_AmazonEKS_CNI_Policy,
    aws_iam_role_policy_attachment.node_AmazonEC2ContainerRegistryReadOnly,
  ]

  tags = var.tags
}
```

## Creating a Cluster Using AWS CDK

Puedes crear un EKS cluster usando AWS CDK (Cloud Development Kit).

### EKS Auto Mode Cluster Using TypeScript

```typescript
// lib/eks-auto-mode-stack.ts
import * as cdk from 'aws-cdk-lib';
import * as eks from 'aws-cdk-lib/aws-eks';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';

export class EksAutoModeStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Import or create VPC
    const vpc = ec2.Vpc.fromLookup(this, 'VPC', {
      vpcId: 'vpc-12345678' // Existing VPC ID
    });

    // Or create new VPC
    // const vpc = new ec2.Vpc(this, 'EksVpc', {
    //   maxAzs: 3,
    //   natGateways: 1,
    // });

    // Create EKS Auto Mode cluster
    const cluster = new eks.Cluster(this, 'AutoModeCluster', {
      clusterName: 'my-auto-cluster',
      version: eks.KubernetesVersion.V1_31,
      vpc: vpc,
      vpcSubnets: [
        {
          subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
        }
      ],
      endpointAccess: eks.EndpointAccess.PUBLIC_AND_PRIVATE,

      // Auto Mode configuration
      defaultCapacity: 0, // Set default capacity to 0 for Auto Mode

      // Enable logging
      clusterLogging: [
        eks.ClusterLoggingTypes.API,
        eks.ClusterLoggingTypes.AUDIT,
        eks.ClusterLoggingTypes.AUTHENTICATOR,
        eks.ClusterLoggingTypes.CONTROLLER_MANAGER,
        eks.ClusterLoggingTypes.SCHEDULER,
      ],
    });

    // Custom resource to enable Auto Mode
    const autoModeConfig = new cdk.CustomResource(this, 'AutoModeConfig', {
      serviceToken: this.createAutoModeProvider().serviceToken,
      properties: {
        ClusterName: cluster.clusterName,
        NodeRoleArn: this.createNodeRole().roleArn,
      },
    });

    // Outputs
    new cdk.CfnOutput(this, 'ClusterName', {
      value: cluster.clusterName,
      description: 'EKS cluster name',
    });

    new cdk.CfnOutput(this, 'ClusterEndpoint', {
      value: cluster.clusterEndpoint,
      description: 'EKS cluster endpoint',
    });
  }

  private createNodeRole(): iam.Role {
    const nodeRole = new iam.Role(this, 'NodeRole', {
      assumedBy: new iam.ServicePrincipal('ec2.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonEKSWorkerNodePolicy'),
        iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonEKS_CNI_Policy'),
        iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonEC2ContainerRegistryReadOnly'),
      ],
    });

    return nodeRole;
  }

  private createAutoModeProvider(): cdk.Provider {
    // Lambda function for enabling Auto Mode
    const onEvent = new cdk.aws_lambda.Function(this, 'AutoModeHandler', {
      runtime: cdk.aws_lambda.Runtime.PYTHON_3_9,
      handler: 'index.on_event',
      code: cdk.aws_lambda.Code.fromInline(`
import boto3
import json

def on_event(event, context):
    print(json.dumps(event))

    eks = boto3.client('eks')
    cluster_name = event['ResourceProperties']['ClusterName']
    node_role_arn = event['ResourceProperties']['NodeRoleArn']

    if event['RequestType'] == 'Create' or event['RequestType'] == 'Update':
        # Auto Mode enablement logic
        try:
            response = eks.update_cluster_config(
                name=cluster_name,
                computeConfig={
                    'enabled': True,
                    'nodeRoleArn': node_role_arn
                }
            )
            return {'PhysicalResourceId': cluster_name}
        except Exception as e:
            print(f"Error: {e}")
            raise e

    return {'PhysicalResourceId': cluster_name}
      `),
    });

    // Grant EKS permissions to Lambda function
    onEvent.addToRolePolicy(new iam.PolicyStatement({
      actions: [
        'eks:UpdateClusterConfig',
        'eks:DescribeCluster',
      ],
      resources: ['*'],
    }));

    return new cdk.Provider(this, 'AutoModeProvider', {
      onEventHandler: onEvent,
    });
  }
}
```

### CDK App Entry Point

```typescript
// bin/eks-auto-mode.ts
#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { EksAutoModeStack } from '../lib/eks-auto-mode-stack';

const app = new cdk.App();
new EksAutoModeStack(app, 'EksAutoModeStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION,
  },
});
```

### CDK Deployment

```bash
# Install CDK
npm install -g aws-cdk

# Initialize project
cdk init app --language typescript

# Install dependencies
npm install

# CDK bootstrap (only once)
cdk bootstrap

# Deploy
cdk deploy

# Update kubeconfig
aws eks update-kubeconfig --name my-auto-cluster --region us-west-2
```

## Configuring Cluster Access

Se requieren permisos y configuración adecuados para acceder a un EKS cluster.

### kubeconfig Configuration

```bash
# Update kubeconfig
aws eks update-kubeconfig --name my-cluster --region us-west-2

# Use specific profile
aws eks update-kubeconfig --name my-cluster --region us-west-2 --profile my-profile

# Use role ARN
aws eks update-kubeconfig --name my-cluster --region us-west-2 --role-arn arn:aws:iam::123456789012:role/EKSAccessRole
```

### RBAC Configuration

```yaml
# rbac.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: aws-auth
  namespace: kube-system
data:
  mapRoles: |
    - rolearn: arn:aws:iam::123456789012:role/NodeInstanceRole
      username: system:node:{{EC2PrivateDNSName}}
      groups:
        - system:bootstrappers
        - system:nodes
  mapUsers: |
    - userarn: arn:aws:iam::123456789012:user/admin
      username: admin
      groups:
        - system:masters
```

```bash
kubectl apply -f rbac.yaml
```

## Cluster Validation

Aquí se muestra cómo verificar que el cluster se haya creado correctamente.

### Basic Validation

```bash
# Check cluster info
kubectl cluster-info

# Check node status
kubectl get nodes

# Check system pod status
kubectl get pods -n kube-system

# Check service accounts
kubectl get serviceaccounts -n kube-system
```

### Auto Mode Specific Validation

```bash
# Check Auto Mode node pools
kubectl get nodepools

# Check Auto Mode node classes
kubectl get nodeclasses

# Check Karpenter status (used in Auto Mode)
kubectl get pods -n karpenter
```

### Deploy Sample Application

```yaml
# sample-app.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sample-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: sample-app
  template:
    metadata:
      labels:
        app: sample-app
    spec:
      containers:
      - name: app
        image: nginx:latest
        ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: sample-app-service
spec:
  selector:
    app: sample-app
  ports:
  - port: 80
    targetPort: 80
  type: LoadBalancer
```

```bash
kubectl apply -f sample-app.yaml
kubectl get pods
kubectl get services
```

## Cluster Upgrade

Aquí se muestra cómo actualizar la versión de Kubernetes de un EKS cluster.

### Auto Mode Cluster Upgrade

Los Auto Mode clusters se actualizan automáticamente, pero también es posible realizar una actualización manual:

```bash
# Upgrade using eksctl
eksctl upgrade cluster --name my-auto-cluster --version 1.32

# Upgrade using AWS CLI
aws eks update-cluster-version --name my-auto-cluster --kubernetes-version 1.32
```

### Traditional Cluster Upgrade

```bash
# Upgrade cluster
eksctl upgrade cluster --name my-cluster --version 1.32

# Upgrade node group
eksctl upgrade nodegroup --cluster my-cluster --name my-nodegroup
```

## Cluster Deletion

Aquí se muestra cómo eliminar un cluster.

### Delete Using eksctl

```bash
eksctl delete cluster --name my-cluster --region us-west-2
```

### Delete Using AWS CLI

```bash
# Delete node group (for non-Auto Mode)
aws eks delete-nodegroup --cluster-name my-cluster --nodegroup-name my-nodegroup

# Delete cluster
aws eks delete-cluster --name my-cluster
```

### Delete Using Terraform

```bash
terraform destroy
```

### Delete Using CDK

```bash
cdk destroy
```

## Conclusion

Hay varios métodos para crear un EKS cluster, cada uno con sus propias ventajas y desventajas:

- **EKS Auto Mode**: Proporciona clusters listos para producción con una sobrecarga operativa mínima
- **eksctl**: Creación de cluster simple y rápida
- **AWS Management Console**: Creación intuitiva mediante GUI
- **AWS CLI**: Adecuado para automatización con scripts
- **Terraform**: Administra infrastructure as code
- **AWS CDK**: Define infraestructura usando lenguajes de programación

Para entornos de producción, se recomienda usar EKS Auto Mode o Terraform/CDK para construir una infraestructura coherente y repetible.
