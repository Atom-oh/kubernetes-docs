# Parte 1: Configuración de la infraestructura

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

> **Dificultad**: Avanzado
> **Última actualización**: 13 de septiembre de 2026
Prepare dos clústeres de EKS y una ruta dedicada de base de datos y mensajería para el laboratorio. Los archivos ejecutables están en el [ejemplo de aplicación](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/labs/observability/application). Revise la cuenta, la región, la red, los permisos y la limpieza antes de crear recursos facturables. Esta auditoría no creó recursos de AWS.

![Clústeres de administración y servicios, y recursos dedicados del laboratorio](../../.gitbook/assets/en-labs-observability-01-infrastructure-setup-lab-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-labs-observability-01-infrastructure-setup-lab-0.html)

## 1. Verifique el entorno y la propiedad {#prerequisites}

Los ejemplos se revisaron con AWS CLI v2, eksctl 0.229.0, kubectl 1.36.2, Helm 3.21.3, Python 3.12, Docker, Git y jq. EKS 1.36 tenía soporte estándar en el momento de la revisión. El ejemplo anterior de 1.31 tenía soporte extendido; todavía no había llegado al fin del soporte. Vuelva a comprobar la disponibilidad de la versión y la región al ejecutar los pasos.

```bash
aws --version
eksctl version
kubectl version --client
helm version
python3 --version
aws sts get-caller-identity
```
Use un rol temporal aprobado. Revise las operaciones necesarias de EKS, EC2/VPC, CloudFormation, IAM/PassRole, RDS, SNS/SQS, KMS y Logs frente al plan de despliegue. No otorgue FullAccess a todos los servicios ni cree claves de acceso IAM de larga duración para este ejercicio.

```bash
umask 077
export LAB_STATE="$(mktemp -d "$PWD/obs-lab.XXXXXXXX")"
# Set AWS_REGION, EXPECTED_ACCOUNT_ID and a unique LAB_PREFIX first.
test "$(aws sts get-caller-identity --query Account --output text)" = "$EXPECTED_ACCOUNT_ID"
```

## 2. Red y dos clústeres {#clusters}

El ejemplo reutiliza una VPC revisada y dos subredes privadas en distintas zonas de disponibilidad (AZ). Prepare primero NAT, los endpoints de VPC necesarios, DNS, capacidad suficiente de direcciones y las reglas de grupos de seguridad (SG) y listas de control de acceso a la red (NACL). Los CIDR de servicio de Kubernetes `172.20.0.0/16` y `172.21.0.0/16` no deben superponerse con las redes reales de VPC ni con las redes conectadas. Las VPC separadas requieren peering o Transit Gateway (TGW), rutas bidireccionales, DNS y verificación de la IP de origen.

```bash
cd examples/labs/observability/application
python3 prepare_clusters.py --region "$AWS_REGION" --vpc-id "$VPC_ID" \
  --subnet-a "$PRIVATE_SUBNET_A" --az-a "$AZ_A" \
  --subnet-b "$PRIVATE_SUBNET_B" --az-b "$AZ_B" \
  --client-cidr "$CLIENT_CIDR" --prefix "$LAB_PREFIX" \
  --output-directory "$LAB_STATE/clusters"
```
El generador selecciona EKS 1.36, entradas de acceso a la API, OIDC, nodos administrados AL2023, almacenamiento `gp3` cifrado y un CIDR limitado para los clientes de la API pública. El tamaño y la cantidad de nodos son parámetros del laboratorio, no una capacidad medida. Revise el JSON y los costos antes de crear los recursos. Si ocurre un error, inspeccione los recursos que se hayan creado parcialmente con ese nombre antes de volver a intentarlo.

```bash
eksctl create cluster -f "$LAB_STATE/clusters/managed.json" --write-kubeconfig=false
eksctl create cluster -f "$LAB_STATE/clusters/service.json" --write-kubeconfig=false
export KUBECONFIG="$LAB_STATE/kubeconfig"
aws eks update-kubeconfig --name "$LAB_PREFIX-managed" --alias managed --kubeconfig "$KUBECONFIG"
aws eks update-kubeconfig --name "$LAB_PREFIX-service" --alias service --kubeconfig "$KUBECONFIG"
kubectl --context managed get nodes
kubectl --context service get nodes
```
Aplique las comprobaciones de cuenta, endpoint y propiedad de la [guía de creación de EKS](../../eks/02-eks-cluster-creation-part1.md) y del [laboratorio de clústeres](../eks/01-eks-cluster-creation-lab.md). Verifique que ambos contextos seleccionen los clústeres distintos previstos.

## 3. Requisitos previos de almacenamiento, balanceador de carga y OIDC {#platform-prerequisites}

Instale EBS CSI, una StorageClass `gp3` revisada, un CNI que aplique realmente las NetworkPolicies y AWS Load Balancer Controller (`service.k8s.aws/nlb`). No sobrescriba a ciegas las StorageClasses compartidas. Obtenga el emisor OIDC de cada clúster y el ARN del proveedor de IAM correspondiente. El host y la ruta del emisor, sin `https://`, deben coincidir con el sufijo del ARN del proveedor.

```bash
aws eks describe-cluster --name "$LAB_PREFIX-managed" --query cluster.identity.oidc.issuer --output text
aws eks describe-cluster --name "$LAB_PREFIX-service" --query cluster.identity.oidc.issuer --output text
kubectl --context managed get storageclass gp3
kubectl --context service get storageclass gp3
```

## 4. Aurora, SNS/SQS y roles {#managed-resources}

`application/infra.yaml` crea un clúster de Aurora privado con un escritor, un secreto maestro administrado, distribución de SNS a suscriptores, colas y DLQ separadas para los consumidores, un grupo de logs de CloudWatch y roles. El tráfico entrante a la base de datos solo se permite desde el grupo de seguridad real de los nodos de servicio. Un ejercicio con un solo escritor no ofrece alta disponibilidad Multi-AZ. Consulte y proporcione explícitamente una versión del motor de Aurora compatible con la región.

```bash
aws rds describe-db-engine-versions --engine aurora-postgresql \
  --query "DBEngineVersions[].EngineVersion" --output table
```
Proporcione VpcId, PrivateSubnetIds, ServiceNodeSecurityGroupId, AuroraEngineVersion y ambos pares de proveedor/emisor OIDC; revise y ejecute el conjunto de cambios de CloudFormation. Verifique la coherencia de la cuenta, el ARN y ServiceAccount. Los roles de ejecución de la aplicación, la identidad de KEDA para leer las colas y la identidad de administración para que Collector escriba logs son independientes.

```bash
aws cloudformation describe-stacks --stack-name "$LAB_STACK" \
  --query "Stacks[0].Outputs" --output json > "$LAB_STATE/infra-outputs.json"
```

Genere aquí las entradas de identidad de Collector para la Parte 2. Elija ahora el repositorio de imágenes y la etiqueta inmutable; compile/publique la imagen en la Parte 3.

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt PyYAML==6.0.3
.venv/bin/python prepare_values.py --outputs-file "$LAB_STATE/infra-outputs.json"   --region "$AWS_REGION" --image-repository "$IMAGE_REPOSITORY"   --image-tag "$IMAGE_TAG" --output-directory "$LAB_STATE/helm-inputs"
```

## 5. Cuenta de DB de tiempo de ejecución y siguiente paso {#database-and-next}

Lea el Secret maestro solo en un entorno autorizado y almacene un archivo de conexión JSON privado. Use el paquete de CA de RDS y `sslmode=verify-full`. El [procedimiento bootstrap_db.py](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/labs/observability/application#infrastructure-and-credentials) crea acceso DML dedicado de `lab_runtime` sin sobrescribir una contraseña existente. Establezca la ruta de CA de su Pod en `/run/database-ca/global-bundle.pem`.

Registre los stacks de CloudFormation, los clústeres, las instantáneas retenidas, las asociaciones de IAM, los balanceadores de carga y los PVC en el inventario de recursos. Estime los costos de EKS, nodos, NAT, EBS, Aurora, Logs, SNS, SQS, KMS y transferencia según la región y el uso reales. No presente totales horarios fijos ni convierta los precios mensuales por usuario de AMG en cargos por hora de un espacio de trabajo. Continúe con la [Parte 2](./02-observability-stack-lab.md).

## Alcance de la validación

Las comprobaciones cubrieron los esquemas de eksctl, el análisis de lint de CloudFormation, la estructura de los roles y el comportamiento local de PostgreSQL. No se probaron entornos reales de EKS/VPC/OIDC/IRSA/Aurora/TLS, las cuotas ni la duración del aprovisionamiento.
