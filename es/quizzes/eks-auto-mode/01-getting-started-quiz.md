# Cuestionario de introducción a EKS Auto Mode

> **Documento relacionado**: [Introducción a EKS Auto Mode](../../eks-auto-mode/01-getting-started.md)

## Preguntas de opción múltiple

### 1. ¿Qué tecnología permite que EKS Auto Mode aprovisione capacidad de cómputo administrada?

- A) Cluster Autoscaler
- B) Karpenter
- C) AWS Fargate
- D) EC2 Auto Scaling Groups

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Karpenter**

**Explicación:**
Auto Mode utiliza controladores basados en Karpenter que opera AWS. No es necesario instalar un controlador de Karpenter independiente para Auto Mode. Aun así, debes configurar las solicitudes de recursos de las cargas de trabajo, NodePools/NodeClasses, las restricciones de interrupción y el escalado automático de las aplicaciones; automatizar la infraestructura no transfiere a AWS la responsabilidad de mantener disponibles las aplicaciones.

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
El requisito original de Kubernetes 1.29 o posterior para esta función no garantiza que siga teniendo soporte vigente. El 12 de octubre de 2026, EKS 1.34–1.37 cuentan con soporte estándar; el capítulo mantiene su referencia revisada de 1.36. Consulta el [calendario de versiones de AWS](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html) y las tarifas aplicables. Comprueba las cuotas de servicio vigentes y la capacidad de las subredes, en vez de confiar en los antiguos recuentos fijos no fundamentados de NodePool y nodos.

</details>

### 3. ¿Qué opción de eksctl habilita Auto Mode al crear un clúster nuevo?

- A) `eksctl create cluster --auto-mode`
- B) `eksctl create cluster --enable-auto-mode`
- C) `eksctl create cluster --with-auto-mode`
- D) `eksctl create cluster --compute autoMode=enabled`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) `eksctl create cluster --enable-auto-mode`**

**Explicación:**
La opción de creación `--enable-auto-mode` es válida en la versión 0.229.0 de eksctl que se comprobó. El capítulo utiliza un archivo de configuración revisado con `autoModeConfig.enabled`, `nodePools` y `nodeRoleARN` para hacer explícitos los roles y la red.

Para un clúster existente administrado por eksctl, usa `eksctl update auto-mode-config --config-file <reviewed-config>`. `eksctl update cluster` es un comando obsoleto para actualizar el plano de control, no para habilitar Auto Mode. No añadas el drenaje de grupos de nodos solo para habilitar esta función. Consulta la [referencia de eksctl](https://docs.aws.amazon.com/eks/latest/eksctl/auto-mode.html).

</details>

### 4. ¿Qué afirmación sobre el tiempo de aprovisionamiento de Auto Mode es válida?

- A) Todos los nodos y Pods están listos en un plazo de 5–10 segundos
- B) La capacidad, el arranque, las descargas de imágenes y las restricciones de scheduling afectan la disponibilidad; mide la carga de trabajo
- C) AWS garantiza que todo el aprovisionamiento se completa en un plazo de cinco minutos
- D) Un plano de control en estado ACTIVE demuestra que todas las aplicaciones están listas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) La capacidad, el arranque, las descargas de imágenes y las restricciones de scheduling afectan la disponibilidad; mide la carga de trabajo**

**Explicación:**
Este ejemplo no ofrece una garantía fija de disponibilidad de extremo a extremo. Distingue entre el inicio del nodo, que el nodo esté listo y que la aplicación esté disponible.

El cuestionario anterior indicaba **40–90 segundos** con inicio de EC2 de **10–30**, arranque de AMI de **20–40**, registro de kubelet de **5–10** y scheduling de **1–5 segundos**. Se conservan aquí como **estimaciones didácticas históricas no verificadas**, no como resultados medidos ni un SLO actual; no fue posible establecer su procedencia en esta auditoría. Auto Mode selecciona su variante administrada de Bottlerocket, por lo que la antigua sugerencia de elegir AL2023 frente a Bottlerocket para un arranque más rápido de Auto Mode era engañosa.

</details>

### 5. ¿Qué bloque configura el cómputo en el recurso `aws_eks_cluster` de Terraform?

- A) `auto_mode_config { enabled = true }`
- B) `compute_config { enabled = true }`
- C) `karpenter_config { enabled = true }`
- D) `node_config { auto_mode = true }`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) `compute_config { enabled = true }`**

**Explicación:**
El recurso utiliza `compute_config`, pero configurar solo el cómputo no basta: el cómputo, el balanceo de carga y el almacenamiento en bloques de Auto Mode deben habilitarse juntos, junto con el acceso mediante la API y un rol de nodo adecuado para los grupos predeterminados. Este fragmento presupone que los roles, el proveedor y las variables revisados están definidos en otra parte; no es una configuración independiente lista para desplegar.

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

El capítulo utiliza el módulo EKS 21.25.0, que requiere la versión 6.59 o posterior del proveedor de AWS, y se validó con la versión 6.64.0. La entrada del módulo también se llama `compute_config`; `cluster_compute_config`, la entrada del módulo de la versión 20, no es el nombre del bloque del recurso. Revisa el plan guardado y las políticas de los roles necesarias antes de aplicar.

</details>

### 6. ¿En qué principal de servicio debe confiar el **rol IAM del nodo** de Auto Mode?

- A) eks.amazonaws.com
- B) ec2.amazonaws.com
- C) eks-auto.amazonaws.com
- D) karpenter.amazonaws.com

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) ec2.amazonaws.com**

**Explicación:**
El rol de nodo se asigna a instancias administradas de EC2 y confía en `ec2.amazonaws.com`. El **rol del clúster**, que es independiente, confía en `eks.amazonaws.com` y requiere `sts:TagSession` además de `sts:AssumeRole` para Auto Mode.

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

El rol de nodo utiliza `AmazonEKSWorkerNodeMinimalPolicy` y `AmazonEC2ContainerRegistryPullOnly`. Los permisos de AWS de las aplicaciones deben asignarse a roles independientes para las cargas de trabajo, por ejemplo, mediante Pod Identity. Consulta los [requisitos de los roles de AWS](https://docs.aws.amazon.com/eks/latest/userguide/automode-get-started-cli.html).

</details>
