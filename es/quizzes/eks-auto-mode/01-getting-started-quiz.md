# Cuestionario de introducción a EKS Auto Mode

> **Documento relacionado**: [Introducción a EKS Auto Mode](../../eks-auto-mode/01-getting-started.md)

## Preguntas de opción múltiple

### 1. ¿Cuál es la tecnología subyacente que impulsa EKS Auto Mode?

- A) Cluster Autoscaler
- B) Karpenter
- C) AWS Fargate
- D) EC2 Auto Scaling Groups

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Karpenter**

**Explicación:**
EKS Auto Mode se basa en Karpenter, pero se ejecuta dentro del control plane (plano de control) administrado por AWS. Los usuarios no necesitan instalar ni configurar por separado ningún componente de administración de nodes (nodos); AWS administra todo.

**Características de EKS Auto Mode:**
- Administración automatizada de nodes basada en Karpenter
- Se ejecuta en el control plane de AWS
- Selección automática de la instancia óptima según los requisitos del workload (carga de trabajo)
- Escalado rápido en decenas de segundos

</details>

### 2. ¿Cuál es la versión mínima de EKS requerida para usar EKS Auto Mode?

- A) 1.27
- B) 1.28
- C) 1.29
- D) 1.30

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) 1.29**

**Explicación:**
EKS Auto Mode solo está disponible en la versión 1.29 de EKS y superiores.

**Limitaciones clave:**
- Versión mínima de EKS: 1.29
- Máximo de NodePools por cluster: 100
- Máximo de nodes por NodePool: 1000
- Máximo de nodes por cluster: 5000

</details>

### 3. ¿Cuál es la forma correcta de crear un cluster nuevo con Auto Mode habilitado usando eksctl?

- A) `eksctl create cluster --auto-mode`
- B) `eksctl create cluster --enable-auto-mode`
- C) `eksctl create cluster --with-auto-mode`
- D) `eksctl create cluster --compute autoMode=enabled`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) `eksctl create cluster --enable-auto-mode`**

**Explicación:**
Con eksctl 0.200.0 o posterior, puedes usar el flag `--enable-auto-mode` para crear un cluster con Auto Mode habilitado.

```bash
# Create new cluster with Auto Mode enabled
eksctl create cluster \
    --name my-cluster \
    --region us-west-2 \
    --enable-auto-mode

# Enable Auto Mode on existing cluster
eksctl update cluster \
    --name my-cluster \
    --enable-auto-mode
```

</details>

### 4. ¿Cuál es el tiempo típico esperado para el aprovisionamiento de nodes en Auto Mode?

- A) 5-10 segundos
- B) 40-90 segundos
- C) 3-5 minutos
- D) 10-15 minutos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) 40-90 segundos**

**Explicación:**
La línea de tiempo del aprovisionamiento de nodes para EKS Auto Mode es la siguiente:
- Lanzamiento de la instancia EC2: 10-30 segundos
- Arranque de AMI: 20-40 segundos
- Registro de kubelet: 5-10 segundos
- Programación de Pod: 1-5 segundos
- **Tiempo total esperado: 40-90 segundos**

Usar Bottlerocket AMI puede lograr tiempos de arranque más rápidos en comparación con AL2023.

</details>

### 5. ¿Qué bloque debe agregarse para habilitar Auto Mode en un cluster de EKS existente usando Terraform?

- A) `auto_mode_config { enabled = true }`
- B) `compute_config { enabled = true }`
- C) `karpenter_config { enabled = true }`
- D) `node_config { auto_mode = true }`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) `compute_config { enabled = true }`**

**Explicación:**
Con Terraform AWS Provider 5.79.0 o posterior, usa el bloque `compute_config` para habilitar Auto Mode.

```hcl
resource "aws_eks_cluster" "main" {
  name     = "my-cluster"
  role_arn = aws_iam_role.cluster.arn
  version  = "1.31"

  compute_config {
    enabled       = true
    node_pools    = ["general-purpose", "system"]
    node_role_arn = aws_iam_role.node.arn
  }

  kubernetes_network_config {
    elastic_load_balancing {
      enabled = true
    }
  }

  storage_config {
    block_storage {
      enabled = true
    }
  }

  vpc_config {
    subnet_ids = var.subnet_ids
  }
}
```

</details>

### 6. ¿Qué service principal debe permitirse en la relación de confianza del rol de IAM requerido para los clusters de Auto Mode?

- A) eks.amazonaws.com
- B) ec2.amazonaws.com
- C) eks-auto.amazonaws.com
- D) karpenter.amazonaws.com

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) ec2.amazonaws.com**

**Explicación:**
El rol de IAM usado por los nodes de Auto Mode debe confiar en el service principal de EC2 porque los nodes se ejecutan como instancias EC2.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

Políticas administradas requeridas:
- `AmazonEKSWorkerNodeMinimalPolicy`
- `AmazonEC2ContainerRegistryPullOnly`

</details>
