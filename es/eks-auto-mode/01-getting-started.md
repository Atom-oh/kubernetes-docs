# Primeros pasos con Auto Mode

> **Versiones compatibles**: EKS Auto Mode GA; línea base del ejemplo: EKS 1.36
> **Última actualización**: 12 de septiembre de 2026

Este capítulo cubre la creación de clústeres nuevos y la habilitación de Auto Mode en un clúster existente. Elige **un** método de creación; ejecutar los tres crea infraestructura independiente con cargos separados. Usa la sección de clúster existente solo para el clúster que pretendes modificar.

Los ejemplos usan la región comercial de Seúl y roles de IAM revisados y creados previamente. Se comprobaron con eksctl 0.229.0, Terraform 1.15.7/proveedor de AWS 6.64.0 y CDK 2.269.0/constructs 10.5.0 mediante validación y síntesis locales. **Durante esta revisión no se creó ni migró ningún clúster activo.** Los permisos de IAM/SCP, las cuotas, el enrutamiento, la disponibilidad de instancias y la compatibilidad de las cargas de trabajo aún requieren verificación específica del entorno. Estos ejemplos no son un despliegue de producción probado.

EKS 1.36 está en soporte estándar en la fecha de revisión. El límite mínimo original de la función Auto Mode, 1.29, no establece la elegibilidad para el soporte actual de EKS. Comprueba el calendario de versiones de AWS antes de ejecutar un ejemplo. La política de actualización `STANDARD` permite la actualización automática cuando finalice el soporte estándar; no detiene los cargos.

## Requisitos previos y roles de IAM

Usa credenciales temporales de rol, AWS CLI v2, kubectl compatible con EKS 1.36, Bash, Python 3 y jq. Pide a un administrador que apruebe los siguientes roles distintos y los permisos de aprovisionamiento/PassRole de quien realiza la llamada:

| Rol | Confianza y permisos |
|------|-----------------------|
| Rol del clúster | Confía en `eks.amazonaws.com` para `sts:AssumeRole` y `sts:TagSession`. La guía actual de AWS recomienda `AmazonEKSClusterPolicy`, `AmazonEKSComputePolicy`, `AmazonEKSBlockStoragePolicyV2`, `AmazonEKSLoadBalancingPolicy` y `AmazonEKSNetworkingPolicy` |
| Rol de nodo de Auto Mode | Confía en `ec2.amazonaws.com`; adjunta `AmazonEKSWorkerNodeMinimalPolicy` y `AmazonEC2ContainerRegistryPullOnly` |
| Rol de carga de trabajo | Permisos independientes de la aplicación, por ejemplo mediante EKS Pod Identity; no pongas permisos de aplicación en el rol del nodo |

El ARN del rol del clúster existente no se puede sustituir al habilitar Auto Mode; actualiza las políticas y la relación de confianza aprobadas mediante el flujo de trabajo de IaC que administra ese rol. No sobrescribas a ciegas una política de confianza compartida. El código siguiente utiliza roles revisados y no los crea. Es posible que los volúmenes existentes necesiten comprobaciones adicionales de migración antes de cambiar una política de almacenamiento.

Auto Mode proporciona la funcionalidad de su agente de Pod Identity; no se requiere un proveedor IAM OIDC solo para habilitar Auto Mode. Configura OIDC por separado si tus aplicaciones usan IRSA.

### Cuenta y contexto local compartidos

Establece las variables de entorno requeridas con valores reales aprobados. Para un clúster nuevo, elige un nombre único; para uno existente, verifica su identidad y quién lo administra. Ejecuta los comandos restantes en esta sesión Bash dedicada. Mantén privado el directorio generado.

```bash
set -euo pipefail
: "${EXPECTED_ACCOUNT_ID:?Set the approved account ID}"
: "${CLUSTER_NAME:?Set a unique new name, or the approved existing cluster name}"
: "${AUTO_CLUSTER_ROLE_ARN:?Set the reviewed EKS cluster role ARN}"
: "${AUTO_NODE_ROLE_ARN:?Set the reviewed Auto Mode node role ARN}"
: "${API_CLIENT_CIDR:?Set the approved public client IPv4 CIDR}"
export AWS_REGION="${AWS_REGION:-ap-northeast-2}"
test "$AWS_REGION" = ap-northeast-2 || { printf 'This concrete example uses Seoul subnets/AZs; adapt it before using another region.\n' >&2; exit 1; }
export AWS_DEFAULT_REGION="$AWS_REGION"
export EXPECTED_ACCOUNT_ID CLUSTER_NAME AUTO_CLUSTER_ROLE_ARN AUTO_NODE_ROLE_ARN API_CLIENT_CIDR
python3 - <<'PY'
import ipaddress, os, re
account = os.environ["EXPECTED_ACCOUNT_ID"]
if not re.fullmatch(r"[0-9]{12}", account):
    raise SystemExit("Invalid account")
if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,99}", os.environ["CLUSTER_NAME"]):
    raise SystemExit("Invalid cluster name")
for key in ("AUTO_CLUSTER_ROLE_ARN", "AUTO_NODE_ROLE_ARN"):
    if not re.fullmatch(r"arn:aws:iam::" + account + r":role/[A-Za-z0-9+=,.@_/-]+", os.environ[key]):
        raise SystemExit("Role account/ARN mismatch: " + key)
network = ipaddress.ip_network(os.environ["API_CLIENT_CIDR"], strict=True)
if network.version != 4 or network.prefixlen < 24:
    raise SystemExit("Use a reviewed /24 or narrower IPv4 CIDR")
PY
check_account() {
  local account
  account=$(aws sts get-caller-identity --region "$AWS_REGION" --query Account --output text) || return
  test "$account" = "$EXPECTED_ACCOUNT_ID" || { printf 'Wrong AWS account; stop.\n' >&2; return 1; }
}
check_account
umask 077
export WORK_DIR
WORK_DIR=$(mktemp -d "$PWD/auto-mode.XXXXXXXX")
export KUBECONFIG="$WORK_DIR/kubeconfig"
printf 'Private evidence/config directory: %s\n' "$WORK_DIR"
```

## Crear un clúster nuevo

### eksctl con subredes privadas aprobadas

Este ejemplo reutiliza una VPC revisada y dos subredes privadas en AZ distintas. Establece primero `VPC_ID`, `PRIVATE_SUBNET_A` y `PRIVATE_SUBNET_B`. Confirma que las tablas de rutas de las subredes proporcionan el acceso saliente necesario a servicios e imágenes mediante NAT o endpoints adecuados. `MapPublicIpOnLaunch=false` por sí solo no demuestra que una subred tenga enrutamiento privado.

Las subredes privadas seleccionadas también son las subredes del clúster. Esto importa porque el NodeClass predeterminado de Auto Mode hereda la selección de subredes del clúster; un clúster genérico creado con eksctl y subredes públicas puede lanzar allí los nodos de Auto Mode.

```bash
# Use approved PRIVATE subnets in the same VPC and at least two AZs.
: "${VPC_ID:?Set the approved VPC ID}"
: "${PRIVATE_SUBNET_A:?Set the first private subnet ID}"
: "${PRIVATE_SUBNET_B:?Set the second private subnet ID in another AZ}"
export VPC_ID
check_account
aws ec2 describe-subnets --region "$AWS_REGION" \
  --subnet-ids "$PRIVATE_SUBNET_A" "$PRIVATE_SUBNET_B" > "$WORK_DIR/subnets.json"
python3 - <<'PY'
import json, os
from pathlib import Path
out = Path(os.environ["WORK_DIR"])
subnets = json.loads((out / "subnets.json").read_text())["Subnets"]
if len(subnets) != 2 or len({s["AvailabilityZone"] for s in subnets}) != 2:
    raise SystemExit("Two subnets in distinct AZs are required")
if not all(s["VpcId"] == os.environ["VPC_ID"] and
           s["OwnerId"] == os.environ["EXPECTED_ACCOUNT_ID"] and
           s["State"] == "available" and not s["MapPublicIpOnLaunch"] for s in subnets):
    raise SystemExit("Subnet account/VPC/state/public-IP settings do not match")
config = {
    "apiVersion": "eksctl.io/v1alpha5", "kind": "ClusterConfig",
    "metadata": {"name": os.environ["CLUSTER_NAME"], "region": os.environ["AWS_REGION"], "version": "1.36"},
    "accessConfig": {"authenticationMode": "API"},
    "upgradePolicy": {"supportType": "STANDARD"},
    "iam": {"serviceRoleARN": os.environ["AUTO_CLUSTER_ROLE_ARN"], "withOIDC": False},
    "autoModeConfig": {"enabled": True, "nodePools": ["general-purpose", "system"],
                       "nodeRoleARN": os.environ["AUTO_NODE_ROLE_ARN"]},
    "vpc": {"id": os.environ["VPC_ID"],
            "controlPlaneSubnetIDs": [s["SubnetId"] for s in subnets],
            "subnets": {"private": {s["AvailabilityZone"]: {"id": s["SubnetId"]} for s in subnets}},
            "clusterEndpoints": {"publicAccess": True, "privateAccess": True},
            "publicAccessCIDRs": [os.environ["API_CLIENT_CIDR"]]}
}
(out / "cluster.json").write_text(json.dumps(config, indent=2) + "\n")
PY
# REVIEW cluster.json and routes/permissions first. Creates billed EKS resources.
check_account
eksctl create cluster --config-file "$WORK_DIR/cluster.json" \
  --write-kubeconfig=false --timeout=45m
```

`autoModeConfig.nodePools` es válido en el esquema actual de eksctl. Habilitar Auto Mode mediante eksctl coordina el cómputo, el balanceo de carga y el almacenamiento en bloques, y utiliza el rol de nodo proporcionado para los pools predeterminados. El kubeconfig resultante se crea en la sección de verificación.

Si falla la creación, conserva la configuración e inspecciona las pilas de CloudFormation indicadas. Un tiempo de espera agotado no demuestra que no se hayan creado recursos. Antes de reintentar o borrar algo, concilia la propiedad y los recursos parciales.

### Terraform

Guarda lo siguiente como `main.tf` en un directorio dedicado. Este método crea una VPC con un gateway NAT facturable; es una decisión de laboratorio que prioriza el costo frente a la alta disponibilidad y no ofrece redundancia NAT por AZ. Adapta los CIDR y las AZ para evitar conflictos antes de usarlo.

El ejemplo fija el módulo EKS 21.25.0 y el módulo VPC 5.21.0. El módulo EKS requiere el proveedor de AWS **6.59 o posterior**; conserva el archivo de bloqueo de dependencias generado. La versión 21.25.0 todavía adjunta la política anterior `AmazonEKSBlockStoragePolicy` cuando crea su propio rol de clúster, por lo que este ejemplo proporciona los roles revisados de los requisitos previos. Usa el cifrado de datos de API predeterminado de EKS en lugar de crear una clave KMS administrada por el cliente por separado.

```hcl
terraform {
  required_version = ">= 1.5.7"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 6.59, < 7.0"
    }
  }
}

variable "expected_account_id" {
  type = string
  validation {
    condition     = can(regex("^[0-9]{12}$", var.expected_account_id))
    error_message = "Set the intended 12-digit AWS account."
  }
}
variable "cluster_name" { type = string }
variable "auto_cluster_role_arn" { type = string }
variable "auto_node_role_arn" { type = string }
variable "api_client_cidr" {
  type = string
  validation {
    condition = can(cidrnetmask(var.api_client_cidr)) && try(
      tonumber(split("/", var.api_client_cidr)[1]) >= 24, false
    )
    error_message = "Use an approved narrow IPv4 CIDR (/24 through /32)."
  }
}

provider "aws" {
  region              = "ap-northeast-2"
  allowed_account_ids = [var.expected_account_id]
}

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.21.0"
  name    = "${var.cluster_name}-vpc"
  cidr    = "10.0.0.0/16"

  azs                  = ["ap-northeast-2a", "ap-northeast-2b", "ap-northeast-2c"]
  private_subnets      = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets       = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]
  enable_nat_gateway   = true
  single_nat_gateway   = true
  enable_dns_hostnames = true
  enable_dns_support   = true
  public_subnet_tags   = { "kubernetes.io/role/elb" = "1" }
  private_subnet_tags  = { "kubernetes.io/role/internal-elb" = "1" }
}

module "eks" {
  source             = "terraform-aws-modules/eks/aws"
  version            = "21.25.0"
  name               = var.cluster_name
  kubernetes_version = "1.36"
  vpc_id             = module.vpc.vpc_id
  subnet_ids         = module.vpc.private_subnets

  endpoint_public_access                   = true
  endpoint_private_access                  = true
  endpoint_public_access_cidrs             = [var.api_client_cidr]
  authentication_mode                      = "API"
  enable_cluster_creator_admin_permissions = true # Dedicated lab creator only.
  upgrade_policy                           = { support_type = "STANDARD" }

  # Reviewed pre-created roles: this module release still attaches the older
  # AmazonEKSBlockStoragePolicy when it creates the cluster role itself.
  create_iam_role      = false
  iam_role_arn         = var.auto_cluster_role_arn
  create_node_iam_role = false
  compute_config = {
    enabled       = true
    node_pools    = ["general-purpose", "system"]
    node_role_arn = var.auto_node_role_arn
  }
  # EKS default API-data encryption; no separate customer-managed KMS key here.
  create_kms_key    = false
  encryption_config = null
  enable_irsa       = false # Pod Identity does not require a cluster OIDC provider.
  tags              = { Environment = "lab", Terraform = "true" }
}

output "cluster_endpoint" { value = module.eks.cluster_endpoint }
output "cluster_name" { value = module.eks.cluster_name }
```

La entrada `compute_config` del módulo coordina los bloques de recursos de cómputo, almacenamiento y balanceo de carga de EKS que le corresponden. Es distinta del nombre anterior `cluster_compute_config` del módulo v20. Aquí se concede explícitamente acceso de administrador al creador para el laboratorio dedicado; en producción define entradas de acceso más limitadas y revisadas.

```bash
python3 - <<'PY'
import json, os
from pathlib import Path
fields = {"expected_account_id": "EXPECTED_ACCOUNT_ID", "cluster_name": "CLUSTER_NAME",
          "auto_cluster_role_arn": "AUTO_CLUSTER_ROLE_ARN", "auto_node_role_arn": "AUTO_NODE_ROLE_ARN",
          "api_client_cidr": "API_CLIENT_CIDR"}
(Path(os.environ["WORK_DIR"]) / "terraform.tfvars.json").write_text(
    json.dumps({key: os.environ[value] for key, value in fields.items()}, indent=2) + "\n")
PY
check_account
terraform init
terraform validate
terraform plan -var-file="$WORK_DIR/terraform.tfvars.json" -out="$WORK_DIR/tfplan"
# REVIEW the saved plan; this applies billed infrastructure changes.
terraform apply "$WORK_DIR/tfplan"
```

### AWS CDK

Usa esta pila en una aplicación CDK que apunte a la cuenta aprobada y a `ap-northeast-2`. Proporciona `ClusterName`, `ClusterRoleArn`, `NodeRoleArn`, `OperatorRoleArn` y `ApiClientCidr` como parámetros de CloudFormation. El parámetro del operador debe ser el rol de IAM revisado cuyas credenciales usarás con kubectl, no el ARN de una sesión de rol asumida de STS.

Esto usa un **L1 `eks.CfnCluster`** real. Convertir mediante cast el `defaultChild` del constructo L2 `eks.Cluster` original a `CfnCluster` no convierte su recurso personalizado en un `AWS::EKS::Cluster` ni configura Auto Mode de forma fiable. Aquí se declaran explícitamente las tres capacidades de Auto Mode, el acceso a la API y el rol de nodo. Una entrada de acceso concede al operador de laboratorio revisado acceso de administrador de Kubernetes; el acceso de arranque para la identidad de ejecución de CloudFormation está deshabilitado. Sustituye esta concesión para todo el clúster por ámbitos de acceso adecuados en producción. Los roles de IAM referenciados tienen un ciclo de vida externo a esta pila.

```typescript
import * as cdk from 'aws-cdk-lib/core';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as eks from 'aws-cdk-lib/aws-eks';
import { Construct } from 'constructs';

export class EksAutoModeStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);
    // Pre-created, reviewed roles; see the IAM prerequisites in this chapter.
    const clusterRole = new cdk.CfnParameter(this, 'ClusterRoleArn', { type: 'String' });
    const nodeRole = new cdk.CfnParameter(this, 'NodeRoleArn', { type: 'String' });
    const operatorRole = new cdk.CfnParameter(this, 'OperatorRoleArn', {
      type: 'String',
      allowedPattern: '^arn:aws:iam::[0-9]{12}:role/[A-Za-z0-9+=,.@_/-]+$',
      constraintDescription: 'The reviewed lab operator IAM role ARN, not an STS session ARN',
    });
    const clientCidr = new cdk.CfnParameter(this, 'ApiClientCidr', {
      type: 'String',
      allowedPattern: '^(?:[0-9]{1,3}\\.){3}[0-9]{1,3}/(?:2[4-9]|3[0-2])$',
      constraintDescription: 'An approved narrow IPv4 CIDR (/24 through /32)',
    });
    const clusterName = new cdk.CfnParameter(this, 'ClusterName', { type: 'String' });
    const vpc = new ec2.Vpc(this, 'EksVpc', {
      maxAzs: 3,
      natGateways: 1, // Lab tradeoff: billed, and not per-AZ NAT redundancy.
      subnetConfiguration: [
        { cidrMask: 24, name: 'Public', subnetType: ec2.SubnetType.PUBLIC },
        { cidrMask: 24, name: 'Private', subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
      ],
    });
    for (const subnet of vpc.publicSubnets) {
      cdk.Tags.of(subnet).add('kubernetes.io/role/elb', '1');
    }
    for (const subnet of vpc.privateSubnets) {
      cdk.Tags.of(subnet).add('kubernetes.io/role/internal-elb', '1');
    }
    // An actual L1 AWS::EKS::Cluster, not an L2 defaultChild cast.
    const cluster = new eks.CfnCluster(this, 'EksAutoModeCluster', {
      name: clusterName.valueAsString,
      version: '1.36',
      roleArn: clusterRole.valueAsString,
      accessConfig: {
        authenticationMode: 'API',
        bootstrapClusterCreatorAdminPermissions: false,
      },
      resourcesVpcConfig: {
        subnetIds: vpc.privateSubnets.map(subnet => subnet.subnetId),
        endpointPrivateAccess: true,
        endpointPublicAccess: true,
        publicAccessCidrs: [clientCidr.valueAsString],
      },
      computeConfig: {
        enabled: true,
        nodePools: ['general-purpose', 'system'],
        nodeRoleArn: nodeRole.valueAsString,
      },
      kubernetesNetworkConfig: { elasticLoadBalancing: { enabled: true } },
      storageConfig: { blockStorage: { enabled: true } },
      upgradePolicy: { supportType: 'STANDARD' },
    });
    // CloudFormation's execution role may differ from the interactive operator.
    new eks.CfnAccessEntry(this, 'LabOperatorAccess', {
      clusterName: cluster.ref,
      principalArn: operatorRole.valueAsString,
      type: 'STANDARD',
      accessPolicies: [{
        policyArn: cdk.Fn.sub('arn:${AWS::Partition}:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy'),
        accessScope: { type: 'cluster' }, // Explicit, reviewed admin access for this lab only.
      }],
    });
    new cdk.CfnOutput(this, 'ClusterNameOutput', { value: cluster.ref });
    new cdk.CfnOutput(this, 'ClusterEndpoint', { value: cluster.attrEndpoint });
  }
}
```

Crea una instancia de `EksAutoModeStack` desde tu aplicación CDK e indica la cuenta/región previstas en `StackProps.env`. Revisa `cdk synth`/`cdk diff` antes de un despliegue autorizado. La auditoría local compiló este TypeScript y comprobó las propiedades sintetizadas del clúster; no ejecutó `cdk deploy`.

## Habilitar Auto Mode en un clúster existente

Habilitar Auto Mode y trasladar cargas de trabajo a sus nodos son operaciones distintas. Antes de continuar:

- Si IaC administra el clúster, usa la configuración que lo administra en Terraform/CDK/eksctl; evita desviaciones de configuración no administradas.
- Verifica que el rol de clúster existente tenga los permisos de Auto Mode y la confianza `sts:TagSession` indicados anteriormente. El ejemplo comprueba que su ARN coincide con el rol que revisaste.
- Comprueba las versiones compatibles actuales de los complementos instalados frente a los [mínimos de migración requeridos](https://docs.aws.amazon.com/eks/latest/userguide/auto-enable-existing.html). Un mínimo histórico no recomienda instalar esa versión antigua.
- Planifica las entradas de acceso antes de habilitar la autenticación de la API. La migración de `CONFIG_MAP` a `API_AND_CONFIG_MAP` es unidireccional; conserva la ruta de ConfigMap existente y agrega entradas de acceso.
- Conserva los grupos de nodos existentes y el Deployment de CoreDNS para los nodos que no son de Auto Mode. Revisa la configuración de CNI/red admitida. Habilitar Auto Mode no migra automáticamente los volúmenes EBS ni los balanceadores de carga existentes.

Para un clúster administrado por eksctl, el comando actual es `eksctl update auto-mode-config --config-file <reviewed-config>`. No es `eksctl update cluster --enable-auto-mode`, y no debes agregar `--drain-all-nodegroups` solo para habilitar la función.

La siguiente alternativa con AWS CLI habilita el cómputo, el balanceo de carga y el almacenamiento en bloques en la misma solicitud. Es para un clúster que aún no tiene Auto Mode habilitado. Conserva cada ID de actualización y espera un resultado terminal en lugar de suponer que la aceptación de la solicitud significa que terminó:

```bash
check_account
aws eks describe-cluster --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --output json > "$WORK_DIR/before.json"
jq -e --arg role "$AUTO_CLUSTER_ROLE_ARN" '
  .cluster.status == "ACTIVE" and .cluster.roleArn == $role and
  .cluster.computeConfig.enabled != true
' "$WORK_DIR/before.json" >/dev/null

wait_update() {
  local id=$1 status
  for attempt in $(seq 1 120); do
    aws eks describe-update --region "$AWS_REGION" --name "$CLUSTER_NAME" \
      --update-id "$id" --output json > "$WORK_DIR/update-$id.json" || return
    status=$(jq -er '.update.status' "$WORK_DIR/update-$id.json") || return
    case "$status" in
      Successful) return 0 ;;
      Failed|Cancelled) printf 'Update %s: %s; inspect the private response.\n' "$id" "$status" >&2; return 1 ;;
      InProgress) sleep 15 ;;
      *) printf 'Unknown update state; stop.\n' >&2; return 1 ;;
    esac
  done
  printf 'Update wait timed out; do not assume completion or resubmit blindly.\n' >&2
  return 1
}
# One-way authentication migration; review existing access before running.
mode=$(jq -er '.cluster.accessConfig.authenticationMode' "$WORK_DIR/before.json")
case "$mode" in
  CONFIG_MAP)
    auth_id=$(aws eks update-cluster-config --region "$AWS_REGION" --name "$CLUSTER_NAME" \
      --access-config authenticationMode=API_AND_CONFIG_MAP --query update.id --output text)
    wait_update "$auth_id"
    ;;
  API|API_AND_CONFIG_MAP) ;;
  *) printf 'Unknown authentication mode; stop.\n' >&2; exit 1 ;;
esac
compute=$(jq -nc --arg role "$AUTO_NODE_ROLE_ARN" \
  '{enabled:true,nodePools:["general-purpose","system"],nodeRoleArn:$role}')
# MUTATION: compute, load balancing and block storage change together.
check_account
update_id=$(aws eks update-cluster-config --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --compute-config "$compute" \
  --kubernetes-network-config '{"elasticLoadBalancing":{"enabled":true}}' \
  --storage-config '{"blockStorage":{"enabled":true}}' \
  --query update.id --output text)
wait_update "$update_id"
```

Si una actualización falla, agota el tiempo de espera o devuelve un estado desconocido, inspecciona la respuesta privada y concilia la operación antes de reintentar. No se puede cambiar arbitrariamente el rol de nodo que usan los pools predeterminados después de habilitar el cómputo; sigue el flujo de trabajo documentado de NodeClass/entradas de acceso cuando rediseñes la identidad del nodo.

## Consola de AWS

Después de completar los mismos requisitos previos de IAM, complementos y acceso, abre la configuración **EKS Auto Mode → Manage** del clúster, habilita Auto Mode, selecciona los pools predeterminados y el rol de nodo revisado, y supervisa la actualización resultante. La creación de un clúster nuevo ofrece los ajustes correspondientes. La ubicación en la consola puede cambiar; las comprobaciones importantes son las capacidades requeridas de la API y los roles de IAM.

## Verificar la activación

Después de que se complete el método de creación elegido o la actualización del clúster existente:

```bash
check_account
aws eks describe-cluster --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --query 'cluster.{status:status,compute:computeConfig,network:kubernetesNetworkConfig,storage:storageConfig,access:accessConfig}' \
  --output json > "$WORK_DIR/after.json"
jq -e '.status == "ACTIVE" and .compute.enabled == true and
       .network.elasticLoadBalancing.enabled == true and .storage.blockStorage.enabled == true' \
  "$WORK_DIR/after.json"
aws eks update-kubeconfig --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --kubeconfig "$KUBECONFIG" --alias "$CLUSTER_NAME"
kubectl --context "$CLUSTER_NAME" --request-timeout=15s get nodepools,nodeclasses
kubectl --context "$CLUSTER_NAME" wait nodepool/general-purpose nodepool/system \
  --for=condition=Ready --timeout=300s
kubectl --context "$CLUSTER_NAME" --request-timeout=15s get nodes -L eks.amazonaws.com/compute-type
```

Un clúster inactivo puede no tener nodos de Auto Mode hasta que cargas de trabajo elegibles necesiten capacidad. El estado listo de NodePool no es una prueba de disponibilidad de la aplicación. Usa una carga de trabajo de prueba limitada, comprueba NodeClaims/nodos y la disponibilidad de la aplicación, y luego elimina esa carga de trabajo de prueba.

Los nodos de Auto Mode ejecutan CoreDNS localmente como servicio del sistema. Una migración solo a Auto Mode puede eliminar el Deployment tradicional una vez trasladadas las cargas; **los clústeres mixtos de Auto Mode y modos no Auto deben conservarlo** para los demás nodos.

## Limpieza y siguientes pasos

Elimina solo los recursos que pertenezcan al método de creación elegido, después de exportar los datos necesarios y quitar los balanceadores de carga de las aplicaciones/PVC según sus políticas de retención. Usa, según corresponda, la eliminación de eksctl con `--wait`, un plan revisado de `terraform destroy` o la eliminación de la pila CDK revisada. Estos ejemplos hacen referencia a roles de IAM existentes y el ejemplo de eksctl también reutiliza una VPC: no elimines esos requisitos compartidos como si el ejemplo los hubiera creado.

Habilitar Auto Mode en un clúster existente no es un laboratorio con un clúster desechable. No elimines los grupos de nodos antiguos ni deshabilites sus controladores hasta que se haya validado la migración de cargas de trabajo, almacenamiento, DNS y tráfico. Los nodos, volúmenes, balanceadores de carga, NAT y el plano de control pueden seguir generando cargos después de una operación interrumpida; inspecciona los recursos residuales en lugar de confiar en una espera de duración fija.

- [Configuración de NodePool](./02-nodepool-configuration.md)
- [Migración de grupos de nodos administrados](./09-migration-guide.md)
- [Cuestionario de inicio](../quizzes/eks-auto-mode/01-getting-started-quiz.md)

## Referencias

- [Creación con CLI y roles de IAM para Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/automode-get-started-cli.html)
- [Habilitar Auto Mode en un clúster existente](https://docs.aws.amazon.com/eks/latest/userguide/auto-enable-existing.html)
- [Configuración de Auto Mode en eksctl](https://docs.aws.amazon.com/eks/latest/eksctl/auto-mode.html)
- [Calendario de soporte de EKS](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)
- [Módulo Terraform EKS v21.25.0](https://github.com/terraform-aws-modules/terraform-aws-eks/tree/v21.25.0)
- [API CfnCluster de CDK](https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_eks.CfnCluster.html)
- [Acceso de principales IAM mediante entradas de acceso de EKS](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html)
- [Red y DNS de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/auto-networking.html)
- [Límites de la migración](https://docs.aws.amazon.com/eks/latest/userguide/migrate-auto.html)

< [Anterior: Descripción general](./README.md) | [Tabla de contenido](./README.md) | [Siguiente: Configuración de NodePool](./02-nodepool-configuration.md) >
