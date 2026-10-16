# Cuestionario de introducción a EKS Auto Mode

> **Documento relacionado**: [Introducción a EKS Auto Mode](../../eks-auto-mode/01-getting-started.md)

## Preguntas de opción múltiple

### 1. ¿Qué tecnología sustenta el aprovisionamiento de compute administrado de EKS Auto Mode?

- A) Cluster Autoscaler
- B) Karpenter
- C) AWS Fargate
- D) EC2 Auto Scaling Groups

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Karpenter**

**Explicación:**
Auto Mode utiliza controllers basados en Karpenter operados por AWS. No instalas un controller de Karpenter independiente para Auto Mode. Aun así, configuras las solicitudes de workload, NodePools/NodeClasses, las restricciones de interrupción y el escalado automático de aplicaciones; la automatización de la infraestructura no transfiere a AWS la responsabilidad sobre la disponibilidad de las aplicaciones.

</details>

### 2. ¿Cómo debes elegir la versión de Kubernetes para un nuevo clúster de Auto Mode?

- A) Cualquier versión upstream de Kubernetes está disponible inmediatamente en EKS
- B) Usa siempre la 1.29 porque el límite inferior de la funcionalidad original garantiza soporte actual
- C) Consulta el calendario actual de soporte de AWS EKS y la disponibilidad regional
- D) Selecciona siempre una versión con soporte extendido

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Consulta el calendario actual de soporte de AWS EKS y la disponibilidad regional**

**Explicación:**
El límite inferior de funcionalidad original de 1.29+ no es una garantía de soporte actual. El 12 de octubre de 2026, EKS 1.34–1.37 cuentan con soporte estándar; el capítulo mantiene su referencia revisada de 1.36. Consulta el [calendario de versiones de AWS](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html) y las tarifas aplicables. Consulta las cuotas de servicio aplicadas y la capacidad de las subredes en lugar de basarte en las anteriores cantidades fijas no fundamentadas de NodePool/nodos.

</details>

### 3. ¿Qué flag de eksctl habilita Auto Mode al crear un clúster nuevo?

- A) `eksctl create cluster --auto-mode`
- B) `eksctl create cluster --enable-auto-mode`
- C) `eksctl create cluster --with-auto-mode`
- D) `eksctl create cluster --compute autoMode=enabled`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) `eksctl create cluster --enable-auto-mode`**

**Explicación:**
El flag de creación `--enable-auto-mode` es válido en la versión comprobada de eksctl 0.229.0. El capítulo utiliza un archivo de configuración revisado con `autoModeConfig.enabled`, `nodePools` y `nodeRoleARN` para hacer explícitos los roles y la red.

Para un clúster existente administrado por eksctl, usa `eksctl update auto-mode-config --config-file <reviewed-config>`. `eksctl update cluster` es un comando obsoleto de actualización del control plane, no el comando para habilitar Auto Mode. No añadas el drenaje de node groups únicamente para habilitar la funcionalidad. Consulta la [referencia de eksctl](https://docs.aws.amazon.com/eks/latest/eksctl/auto-mode.html).

</details>

### 4. ¿Qué afirmación sobre el tiempo de aprovisionamiento de Auto Mode es defendible?

- A) Cada node y Pod están listos en un plazo de 5–10 segundos
- B) La capacidad, el bootstrap, las descargas de imágenes y las restricciones de scheduling afectan la disponibilidad; mide el workload
- C) AWS garantiza que todo el aprovisionamiento se completa en un plazo de cinco minutos
- D) Un control plane ACTIVE demuestra que todas las aplicaciones están listas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) La capacidad, el bootstrap, las descargas de imágenes y las restricciones de scheduling afectan la disponibilidad; mide el workload**

**Explicación:**
No hay una garantía fija de disponibilidad integral en este ejemplo. Distingue entre el inicio de node, la disponibilidad de node y la disponibilidad de la aplicación.

El cuestionario anterior indicaba **40–90 segundos** con inicio de EC2 de **10–30**, arranque de AMI de **20–40**, registro de kubelet de **5–10** y scheduling de **1–5 segundos**. Se conservan aquí como **estimaciones didácticas históricas no verificadas**, no como resultados medidos ni un SLO actual; no fue posible establecer su procedencia en esta auditoría. Auto Mode selecciona su variante administrada de Bottlerocket, por lo que la antigua sugerencia de elegir AL2023 frente a Bottlerocket para un arranque más rápido de Auto Mode era engañosa.

</details>

### 5. ¿Qué bloque configura compute en el recurso `aws_eks_cluster` de Terraform?

- A) `auto_mode_config { enabled = true }`
- B) `compute_config { enabled = true }`
- C) `karpenter_config { enabled = true }`
- D) `node_config { auto_mode = true }`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) `compute_config { enabled = true }`**

**Explicación:**
El recurso utiliza `compute_config`, pero compute por sí solo es insuficiente: compute, balanceo de carga y almacenamiento en bloques de Auto Mode deben configurarse conjuntamente, con acceso basado en API y un node role adecuado para los pools predeterminados. Este fragmento presupone que los roles, el provider y las variables revisados están definidos en otra parte; no es un despliegue independiente.

```hcl
resource "aws_eks_cluster" "main" {
  name     = var.cluster_name
  role_arn = var.auto_cluster_role_arn
  version  = "1.36"

  access_config {
    authentication_mode                         = "API"
    bootstrap_cluster_creator_admin_permissions = true # Dedicated lab only.
  }
  compute_config {
    enabled       = true
    node_pools    = ["general-purpose", "system"]
    node_role_arn = var.auto_node_role_arn
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
    subnet_ids              = var.private_subnet_ids
    endpoint_public_access  = true
    endpoint_private_access = true
    public_access_cidrs     = [var.api_client_cidr]
  }
}
```

El capítulo utiliza el módulo EKS 21.25.0, que requiere AWS provider 6.59 o posterior, y validó el provider 6.64.0. Su entrada de módulo también se denomina `compute_config`; la entrada de módulo-v20 anterior, `cluster_compute_config`, no es el nombre del bloque de recurso. Revisa el plan guardado y las políticas de roles requeridas antes de aplicar.

</details>

### 6. ¿En qué service principal debe confiar el **node IAM role** de Auto Mode?

- A) eks.amazonaws.com
- B) ec2.amazonaws.com
- C) eks-auto.amazonaws.com
- D) karpenter.amazonaws.com

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) ec2.amazonaws.com**

**Explicación:**
El node role se asigna a instancias administradas de EC2 y confía en `ec2.amazonaws.com`. El **cluster role** independiente confía en `eks.amazonaws.com` y requiere `sts:TagSession` además de `sts:AssumeRole` para Auto Mode.

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "ec2.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
```

El node role utiliza `AmazonEKSWorkerNodeMinimalPolicy` y `AmazonEC2ContainerRegistryPullOnly`. Los permisos de AWS de las aplicaciones pertenecen a roles de workload independientes, por ejemplo mediante Pod Identity. Consulta los [requisitos de roles de AWS](https://docs.aws.amazon.com/eks/latest/userguide/automode-get-started-cli.html).

</details>
