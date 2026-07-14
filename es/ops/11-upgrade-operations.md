# Actualizaciones de EKS: actualización de Auto Mode sin tiempo de inactividad

> **Versiones compatibles**: EKS 1.28+, Terraform 1.5+, Karpenter 1.0+
> **Última actualización**: July 10, 2026

< [Anterior: Optimización de recursos](./10-resource-optimization.md) | [Tabla de contenidos](./README.md) | [Siguiente: Planificación de capacidad para eventos](./12-event-capacity-planning.md) >

---

## Descripción general

Este documento proporciona una guía completa para actualizar clusters de EKS Auto Mode sin tiempo de inactividad. Cubre la planificación de versiones, la validación previa a la actualización, el proceso de actualización en sí y la verificación posterior a la actualización. Se detallan tanto las actualizaciones in-place como las estrategias blue/green con ejemplos prácticos de código.

---

## 1. Planificación de la actualización

### Política de soporte de versiones de Kubernetes

Kubernetes sigue una **política de soporte N-3**, lo que significa que el proyecto mantiene ramas de lanzamiento para las tres versiones menores más recientes, además de la versión actual.

| Versión | Fecha de lanzamiento | Fin del soporte | Estado |
|---------|-------------|----------------|--------|
| 1.32 | Dec 2024 | Dec 2025 | Actual |
| 1.31 | Aug 2024 | Aug 2025 | Compatible |
| 1.30 | Apr 2024 | Apr 2025 | Compatible |
| 1.29 | Dec 2023 | Feb 2025 | Soporte extendido |
| 1.28 | Aug 2023 | Nov 2024 | Soporte extendido |

### Ciclo de vida de EKS: soporte estándar frente a soporte extendido

AWS EKS proporciona dos niveles de soporte:

**Soporte estándar (14 meses)**
- Incluido en el precio base de EKS
- Parches de seguridad y correcciones de errores
- Soporte completo de AWS

**Soporte extendido (12 meses adicionales)**
- Costo adicional: $0.60 por cluster por hora
- Solo parches críticos de seguridad
- Permite más tiempo para la planificación de actualizaciones

```hcl
# Terraform: Enable extended support
resource "aws_eks_cluster" "main" {
  name    = "prod-cluster"
  version = "1.29"

  upgrade_policy {
    support_type = "EXTENDED"  # or "STANDARD"
  }
}
```

### Matriz de compatibilidad de versiones

Antes de actualizar, verifica la compatibilidad entre todos los componentes:

| Componente | EKS 1.29 | EKS 1.30 | EKS 1.31 | EKS 1.32 |
|-----------|----------|----------|----------|----------|
| VPC CNI | 1.15+ | 1.16+ | 1.18+ | 1.19+ |
| CoreDNS | 1.10.1+ | 1.11.1+ | 1.11.1+ | 1.11.3+ |
| kube-proxy | 1.29.x | 1.30.x | 1.31.x | 1.32.x |
| EBS CSI | 1.25+ | 1.28+ | 1.31+ | 1.33+ |
| Karpenter | 0.33+ | 0.35+ | 0.37+ | 0.39+ |
| AWS LB Controller | 2.6+ | 2.7+ | 2.8+ | 2.9+ |
| Cert Manager | 1.13+ | 1.14+ | 1.15+ | 1.16+ |
| ArgoCD | 2.9+ | 2.10+ | 2.11+ | 2.12+ |

### Requisitos de versión de add-ons

Compara las versiones actuales de los add-ons con la versión objetivo de Kubernetes:

```bash
#!/bin/bash
# check-addon-compatibility.sh

CLUSTER_NAME="prod-cluster"
TARGET_VERSION="1.31"

echo "=== Current Add-on Versions ==="
aws eks list-addons --cluster-name $CLUSTER_NAME --query 'addons[]' --output text | while read addon; do
  version=$(aws eks describe-addon --cluster-name $CLUSTER_NAME --addon-name $addon \
    --query 'addon.addonVersion' --output text)
  echo "$addon: $version"
done

echo ""
echo "=== Compatible Versions for EKS $TARGET_VERSION ==="
for addon in vpc-cni coredns kube-proxy aws-ebs-csi-driver; do
  echo "--- $addon ---"
  aws eks describe-addon-versions \
    --addon-name $addon \
    --kubernetes-version $TARGET_VERSION \
    --query 'addons[0].addonVersions[*].addonVersion' \
    --output text | head -5
done
```

### Política de obsolescencia de Kubernetes

Kubernetes proporciona una línea de tiempo estructurada de obsolescencia:

1. **Anuncio de obsolescencia**: API marcada como obsoleta en las notas de lanzamiento
2. **Periodo de advertencia**: kubectl advierte al usar APIs obsoletas (mínimo 2 releases)
3. **Eliminación**: API eliminada de la base de código

**Obsolescencias clave por versión:**

| Versión | APIs obsoletas/eliminadas |
|---------|------------------------|
| 1.29 | flowcontrol.apiserver.k8s.io/v1beta2 eliminado |
| 1.30 | CSIStorageCapacity v1beta1 eliminado |
| 1.31 | PodSecurityPolicy completamente eliminado |
| 1.32 | Varias APIs beta promovidas a estables |

### Recomendaciones de cronograma

**Cronograma de actualización en producción:**

| Fase | Duración | Actividades |
|-------|----------|------------|
| Planificación | 2 semanas | Revisión de compatibilidad, auditoría de obsolescencia |
| Dev/Test | 2 semanas | Actualizar non-prod, validar workloads |
| Staging | 1 semana | Simulación completa de producción |
| Producción | 1 semana | Rolling upgrade con monitoreo |
| Estabilización | 2 semanas | Monitorear, documentar, actualizar runbooks |

**Cadencia de actualización recomendada:**
- Mantente dentro de N-1 de la versión estable actual
- Actualiza cada 4-6 meses
- Nunca omitas más de una versión menor

---

## 2. Checklist previa a la actualización

### Detección de APIs obsoletas con Pluto

[Pluto](https://github.com/FairwindsOps/pluto) escanea APIs obsoletas y eliminadas:

```bash
#!/bin/bash
# detect-deprecated-apis.sh

# Install pluto
curl -L -o pluto.tar.gz https://github.com/FairwindsOps/pluto/releases/download/v5.19.0/pluto_5.19.0_linux_amd64.tar.gz
tar -xzf pluto.tar.gz
sudo mv pluto /usr/local/bin/

# Scan live cluster
echo "=== Scanning Live Cluster ==="
pluto detect-all-in-cluster --target-versions k8s=v1.31.0 -o wide

# Scan Helm releases
echo ""
echo "=== Scanning Helm Releases ==="
pluto detect-helm --target-versions k8s=v1.31.0 -o wide

# Scan local manifests
echo ""
echo "=== Scanning Local Manifests ==="
pluto detect-files -d ./k8s-manifests/ --target-versions k8s=v1.31.0

# Generate report
pluto detect-all-in-cluster --target-versions k8s=v1.31.0 -o json > deprecated-apis-report.json
```

**Salida de ejemplo:**
```
NAME                           KIND                VERSION              REPLACEMENT                    REMOVED   DEPRECATED   REPL AVAIL
my-ingress                     Ingress             extensions/v1beta1   networking.k8s.io/v1           true      true         true
my-pdb                         PodDisruptionBudget policy/v1beta1       policy/v1                      false     true         true
```

### Auditoría de PodDisruptionBudget

Los PDBs pueden bloquear el drenaje de nodes durante las actualizaciones:

```bash
#!/bin/bash
# audit-pdbs.sh

echo "=== PodDisruptionBudget Audit ==="

# List all PDBs with their configuration
kubectl get pdb -A -o custom-columns=\
'NAMESPACE:.metadata.namespace,'\
'NAME:.metadata.name,'\
'MIN-AVAILABLE:.spec.minAvailable,'\
'MAX-UNAVAILABLE:.spec.maxUnavailable,'\
'CURRENT:.status.currentHealthy,'\
'DESIRED:.status.desiredHealthy,'\
'DISRUPTIONS-ALLOWED:.status.disruptionsAllowed'

echo ""
echo "=== Blocking PDBs (disruptionsAllowed=0) ==="
kubectl get pdb -A -o json | jq -r '
  .items[] |
  select(.status.disruptionsAllowed == 0) |
  "\(.metadata.namespace)/\(.metadata.name): currentHealthy=\(.status.currentHealthy), desiredHealthy=\(.status.desiredHealthy)"
'

echo ""
echo "=== PDBs with minAvailable=100% (potentially blocking) ==="
kubectl get pdb -A -o json | jq -r '
  .items[] |
  select(.spec.minAvailable == "100%" or .spec.maxUnavailable == 0 or .spec.maxUnavailable == "0%") |
  "\(.metadata.namespace)/\(.metadata.name)"
'
```

**Mejores prácticas para PDBs durante actualizaciones:**
- Configura `maxUnavailable: 1` en lugar de `minAvailable: 100%`
- Asegúrate de que replicas > mínimo del PDB
- Relaja temporalmente los PDBs para ventanas de mantenimiento

### Estrategia de backup de ETCD

EKS gestiona el control plane, pero el backup del estado de la aplicación es crítico:

```yaml
# velero-schedule.yaml
apiVersion: velero.io/v1
kind: Schedule
metadata:
  name: pre-upgrade-backup
  namespace: velero
spec:
  schedule: "0 */6 * * *"  # Every 6 hours
  template:
    includedNamespaces:
      - "*"
    excludedNamespaces:
      - kube-system
      - velero
    includedResources:
      - "*"
    excludedResources:
      - events
      - events.events.k8s.io
    storageLocation: aws-s3
    volumeSnapshotLocations:
      - aws-ebs
    ttl: 168h  # 7 days retention
    snapshotVolumes: true
    defaultVolumesToFsBackup: false
```

### Verificación de snapshot y restauración de Velero

```bash
#!/bin/bash
# velero-backup-verify.sh

BACKUP_NAME="pre-upgrade-$(date +%Y%m%d-%H%M%S)"

echo "=== Creating Pre-Upgrade Backup ==="
velero backup create $BACKUP_NAME \
  --include-namespaces=app-prod,app-staging \
  --snapshot-volumes \
  --wait

echo ""
echo "=== Verifying Backup ==="
velero backup describe $BACKUP_NAME --details

echo ""
echo "=== Backup Logs ==="
velero backup logs $BACKUP_NAME | tail -50

echo ""
echo "=== Test Restore (dry-run equivalent) ==="
# Create restore to different namespace for verification
velero restore create test-restore-$BACKUP_NAME \
  --from-backup $BACKUP_NAME \
  --namespace-mappings app-prod:restore-test \
  --include-namespaces app-prod \
  --wait

echo ""
echo "=== Verify Restored Resources ==="
kubectl get all -n restore-test

echo ""
echo "=== Cleanup Test Restore ==="
kubectl delete namespace restore-test
velero restore delete test-restore-$BACKUP_NAME --confirm
```

### Script de comprobación de compatibilidad de add-ons

```bash
#!/bin/bash
# addon-compatibility-check.sh

CLUSTER_NAME="${1:-prod-cluster}"
TARGET_VERSION="${2:-1.31}"

echo "=============================================="
echo "Add-on Compatibility Check"
echo "Cluster: $CLUSTER_NAME"
echo "Target Version: $TARGET_VERSION"
echo "=============================================="

# Get current cluster version
CURRENT_VERSION=$(aws eks describe-cluster --name $CLUSTER_NAME \
  --query 'cluster.version' --output text)
echo "Current Version: $CURRENT_VERSION"
echo ""

# Check each add-on
check_addon() {
  local addon_name=$1

  # Get current version
  current=$(aws eks describe-addon --cluster-name $CLUSTER_NAME \
    --addon-name $addon_name --query 'addon.addonVersion' --output text 2>/dev/null)

  if [ "$current" == "None" ] || [ -z "$current" ]; then
    echo "[$addon_name] Not installed"
    return
  fi

  # Get recommended version for target
  recommended=$(aws eks describe-addon-versions \
    --addon-name $addon_name \
    --kubernetes-version $TARGET_VERSION \
    --query 'addons[0].addonVersions[?compatibilities[0].defaultVersion==`true`].addonVersion' \
    --output text 2>/dev/null)

  # Get all compatible versions
  compatible=$(aws eks describe-addon-versions \
    --addon-name $addon_name \
    --kubernetes-version $TARGET_VERSION \
    --query 'addons[0].addonVersions[*].addonVersion' \
    --output text 2>/dev/null | head -1)

  if echo "$compatible" | grep -q "$current"; then
    echo "[$addon_name] OK - Current: $current, Recommended: $recommended"
  else
    echo "[$addon_name] UPGRADE REQUIRED - Current: $current, Recommended: $recommended"
  fi
}

ADDONS=("vpc-cni" "coredns" "kube-proxy" "aws-ebs-csi-driver" "aws-efs-csi-driver" "snapshot-controller")

for addon in "${ADDONS[@]}"; do
  check_addon "$addon"
done

echo ""
echo "=== Helm Release Versions ==="
helm list -A -o json | jq -r '.[] | "\(.name) (\(.namespace)): \(.chart)"' | sort
```

### Verificación de salud de nodes y aplicaciones

```bash
#!/bin/bash
# health-verification.sh

echo "=== Node Health Check ==="
kubectl get nodes -o wide
echo ""

# Check for NotReady nodes
NOT_READY=$(kubectl get nodes --no-headers | grep -v " Ready " | wc -l)
if [ "$NOT_READY" -gt 0 ]; then
  echo "WARNING: $NOT_READY nodes are not Ready"
  kubectl get nodes --no-headers | grep -v " Ready "
fi

echo ""
echo "=== Pod Health Check ==="
# Pods not in Running/Completed state
kubectl get pods -A --field-selector=status.phase!=Running,status.phase!=Succeeded \
  --no-headers 2>/dev/null | head -20

echo ""
echo "=== Deployment Health ==="
kubectl get deployments -A -o custom-columns=\
'NAMESPACE:.metadata.namespace,'\
'NAME:.metadata.name,'\
'READY:.status.readyReplicas,'\
'DESIRED:.spec.replicas,'\
'AVAILABLE:.status.availableReplicas' | \
awk 'NR==1 || $3!=$4 {print}'

echo ""
echo "=== StatefulSet Health ==="
kubectl get statefulsets -A -o custom-columns=\
'NAMESPACE:.metadata.namespace,'\
'NAME:.metadata.name,'\
'READY:.status.readyReplicas,'\
'DESIRED:.spec.replicas' | \
awk 'NR==1 || $3!=$4 {print}'

echo ""
echo "=== Recent Events (Warnings) ==="
kubectl get events -A --field-selector type=Warning \
  --sort-by='.lastTimestamp' | tail -20

echo ""
echo "=== Resource Pressure ==="
kubectl top nodes 2>/dev/null || echo "Metrics server not available"
```

### Script completo previo a la actualización

```bash
#!/bin/bash
# pre-upgrade-checklist.sh

set -e

CLUSTER_NAME="${1:-prod-cluster}"
TARGET_VERSION="${2:-1.31}"
REPORT_DIR="./upgrade-reports/$(date +%Y%m%d-%H%M%S)"

mkdir -p $REPORT_DIR

echo "=============================================="
echo "EKS Pre-Upgrade Checklist"
echo "Cluster: $CLUSTER_NAME"
echo "Target: $TARGET_VERSION"
echo "Report: $REPORT_DIR"
echo "=============================================="

# 1. Current state snapshot
echo ""
echo "[1/8] Capturing current state..."
kubectl cluster-info > $REPORT_DIR/cluster-info.txt
kubectl get nodes -o wide > $REPORT_DIR/nodes.txt
kubectl get pods -A -o wide > $REPORT_DIR/pods.txt
kubectl get pv,pvc -A > $REPORT_DIR/storage.txt
aws eks describe-cluster --name $CLUSTER_NAME > $REPORT_DIR/eks-cluster.json

# 2. Deprecated API check
echo "[2/8] Checking deprecated APIs..."
pluto detect-all-in-cluster --target-versions k8s=v${TARGET_VERSION}.0 -o json \
  > $REPORT_DIR/deprecated-apis.json 2>/dev/null || echo "Pluto not installed"

DEPRECATED_COUNT=$(cat $REPORT_DIR/deprecated-apis.json | jq 'length' 2>/dev/null || echo "0")
echo "  Found $DEPRECATED_COUNT deprecated API usages"

# 3. PDB audit
echo "[3/8] Auditing PodDisruptionBudgets..."
kubectl get pdb -A -o json > $REPORT_DIR/pdbs.json
BLOCKING_PDBS=$(cat $REPORT_DIR/pdbs.json | jq '[.items[] | select(.status.disruptionsAllowed == 0)] | length')
echo "  Found $BLOCKING_PDBS blocking PDBs"

# 4. Add-on compatibility
echo "[4/8] Checking add-on compatibility..."
aws eks list-addons --cluster-name $CLUSTER_NAME --output json > $REPORT_DIR/addons.json

# 5. Helm releases
echo "[5/8] Documenting Helm releases..."
helm list -A -o json > $REPORT_DIR/helm-releases.json

# 6. Custom resources
echo "[6/8] Documenting custom resources..."
kubectl api-resources --verbs=list -o name | while read resource; do
  count=$(kubectl get $resource -A --no-headers 2>/dev/null | wc -l)
  if [ "$count" -gt 0 ]; then
    echo "$resource: $count"
  fi
done > $REPORT_DIR/resource-counts.txt

# 7. Backup verification
echo "[7/8] Verifying backups..."
if command -v velero &> /dev/null; then
  velero backup get -o json > $REPORT_DIR/velero-backups.json
  RECENT_BACKUP=$(velero backup get --selector='velero.io/schedule-name' -o json | \
    jq -r '.items | sort_by(.status.completionTimestamp) | last | .metadata.name')
  echo "  Most recent backup: $RECENT_BACKUP"
else
  echo "  Velero not installed"
fi

# 8. Health summary
echo "[8/8] Generating health summary..."

cat > $REPORT_DIR/summary.md << EOF
# Pre-Upgrade Summary

**Cluster**: $CLUSTER_NAME
**Current Version**: $(aws eks describe-cluster --name $CLUSTER_NAME --query 'cluster.version' --output text)
**Target Version**: $TARGET_VERSION
**Generated**: $(date -Iseconds)

## Checklist

| Item | Status | Details |
|------|--------|---------|
| Deprecated APIs | $([ "$DEPRECATED_COUNT" == "0" ] && echo "PASS" || echo "REVIEW") | $DEPRECATED_COUNT found |
| Blocking PDBs | $([ "$BLOCKING_PDBS" == "0" ] && echo "PASS" || echo "REVIEW") | $BLOCKING_PDBS found |
| Node Health | $(kubectl get nodes --no-headers | grep -v " Ready " | wc -l | xargs -I{} sh -c '[ {} -eq 0 ] && echo "PASS" || echo "FAIL"') | |
| Backup Status | $([ -n "$RECENT_BACKUP" ] && echo "PASS" || echo "REVIEW") | $RECENT_BACKUP |

## Action Items

$([ "$DEPRECATED_COUNT" != "0" ] && echo "- [ ] Update deprecated APIs (see deprecated-apis.json)")
$([ "$BLOCKING_PDBS" != "0" ] && echo "- [ ] Review blocking PDBs before maintenance window")
- [ ] Notify stakeholders of upgrade window
- [ ] Prepare rollback procedure
EOF

echo ""
echo "=============================================="
echo "Pre-upgrade checklist complete"
echo "Review report at: $REPORT_DIR/summary.md"
echo "=============================================="

cat $REPORT_DIR/summary.md
```

---

## 3. Actualización de Auto Mode

### Orden de actualización de Terraform en 3 capas

Las actualizaciones de EKS Auto Mode siguen un orden estricto para mantener la estabilidad:

1. **Capa 02 (Cluster)**: Actualizar la versión del control plane
2. **Esperar**: Permitir que la actualización del control plane se complete
3. **Capa 03 (Plataforma)**: Actualizar add-ons a versiones compatibles
4. **Automático**: Los node pools rotan mediante detección de drift de Karpenter

```
┌─────────────────────────────────────────────────────────────┐
│                    Upgrade Sequence                         │
├─────────────────────────────────────────────────────────────┤
│  1. Control Plane (02-cluster)                              │
│     └─> aws_eks_cluster.version = "1.31"                    │
│                                                             │
│  2. Wait for Control Plane (~15-20 minutes)                 │
│     └─> Verify: kubectl get nodes, cluster status           │
│                                                             │
│  3. Platform Add-ons (03-platform)                          │
│     └─> Update add-on versions in Terraform                 │
│     └─> Apply: CoreDNS, VPC CNI, kube-proxy, etc.           │
│                                                             │
│  4. Node Rotation (Automatic)                               │
│     └─> Karpenter detects AMI drift                         │
│     └─> Nodes cordoned, drained, replaced                   │
│     └─> PDBs respected during drain                         │
└─────────────────────────────────────────────────────────────┘
```

### Actualización del cluster en la capa 02

```hcl
# 02-cluster/main.tf

variable "kubernetes_version" {
  description = "Target Kubernetes version"
  type        = string
  default     = "1.31"  # Upgrade: 1.30 -> 1.31
}

resource "aws_eks_cluster" "main" {
  name     = var.cluster_name
  version  = var.kubernetes_version
  role_arn = aws_iam_role.cluster.arn

  vpc_config {
    subnet_ids              = var.subnet_ids
    endpoint_private_access = true
    endpoint_public_access  = true
    security_group_ids      = [aws_security_group.cluster.id]
  }

  # Auto Mode configuration
  compute_config {
    enabled       = true
    node_pools    = ["general-purpose", "system"]
    node_role_arn = aws_iam_role.node.arn
  }

  kubernetes_network_config {
    ip_family         = "ipv4"
    service_ipv4_cidr = var.service_cidr
    elastic_load_balancing {
      enabled = true
    }
  }

  storage_config {
    block_storage {
      enabled = true
    }
  }

  upgrade_policy {
    support_type = "STANDARD"
  }

  access_config {
    authentication_mode                         = "API_AND_CONFIG_MAP"
    bootstrap_cluster_creator_admin_permissions = false
  }

  # Prevent accidental destruction
  lifecycle {
    prevent_destroy = true
    ignore_changes  = [
      access_config[0].bootstrap_cluster_creator_admin_permissions
    ]
  }

  tags = var.tags
}

# Output for dependency management
output "cluster_version" {
  value = aws_eks_cluster.main.version
}

output "cluster_status" {
  value = aws_eks_cluster.main.status
}
```

**Aplicar la actualización:**

```bash
#!/bin/bash
# upgrade-control-plane.sh

cd terraform/02-cluster

echo "=== Current Version ==="
terraform output cluster_version

echo ""
echo "=== Planning Upgrade ==="
terraform plan -var="kubernetes_version=1.31" -out=upgrade.plan

echo ""
read -p "Proceed with control plane upgrade? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
  echo "Upgrade cancelled"
  exit 1
fi

echo ""
echo "=== Applying Upgrade ==="
terraform apply upgrade.plan

echo ""
echo "=== Waiting for Cluster Status ==="
aws eks wait cluster-active --name prod-cluster
echo "Control plane upgrade complete"

echo ""
echo "=== Verify ==="
kubectl version --short
kubectl get nodes
```

### Actualización de add-ons de plataforma en la capa 03

```hcl
# 03-platform/addons.tf

variable "addon_versions" {
  description = "Add-on versions compatible with target K8s version"
  type = object({
    vpc_cni       = string
    coredns       = string
    kube_proxy    = string
    ebs_csi       = string
    efs_csi       = string
  })
  default = {
    # Versions for EKS 1.31
    vpc_cni    = "v1.18.3-eksbuild.1"
    coredns    = "v1.11.1-eksbuild.9"
    kube_proxy = "v1.31.0-eksbuild.5"
    ebs_csi    = "v1.35.0-eksbuild.1"
    efs_csi    = "v2.0.7-eksbuild.1"
  }
}

resource "aws_eks_addon" "vpc_cni" {
  cluster_name                = var.cluster_name
  addon_name                  = "vpc-cni"
  addon_version               = var.addon_versions.vpc_cni
  resolve_conflicts_on_update = "OVERWRITE"

  configuration_values = jsonencode({
    enableNetworkPolicy = "true"
    env = {
      ENABLE_PREFIX_DELEGATION = "true"
      WARM_PREFIX_TARGET       = "1"
    }
  })

  tags = var.tags
}

resource "aws_eks_addon" "coredns" {
  cluster_name                = var.cluster_name
  addon_name                  = "coredns"
  addon_version               = var.addon_versions.coredns
  resolve_conflicts_on_update = "OVERWRITE"

  configuration_values = jsonencode({
    replicaCount = 3
    resources = {
      limits = {
        cpu    = "200m"
        memory = "256Mi"
      }
      requests = {
        cpu    = "100m"
        memory = "128Mi"
      }
    }
  })

  tags = var.tags
}

resource "aws_eks_addon" "kube_proxy" {
  cluster_name                = var.cluster_name
  addon_name                  = "kube-proxy"
  addon_version               = var.addon_versions.kube_proxy
  resolve_conflicts_on_update = "OVERWRITE"

  tags = var.tags
}

resource "aws_eks_addon" "ebs_csi" {
  cluster_name                = var.cluster_name
  addon_name                  = "aws-ebs-csi-driver"
  addon_version               = var.addon_versions.ebs_csi
  service_account_role_arn    = var.ebs_csi_role_arn
  resolve_conflicts_on_update = "OVERWRITE"

  tags = var.tags
}

resource "aws_eks_addon" "efs_csi" {
  cluster_name                = var.cluster_name
  addon_name                  = "aws-efs-csi-driver"
  addon_version               = var.addon_versions.efs_csi
  service_account_role_arn    = var.efs_csi_role_arn
  resolve_conflicts_on_update = "OVERWRITE"

  tags = var.tags
}
```

### Rotación automática de NodePool

EKS Auto Mode con Karpenter gestiona automáticamente la rotación de nodes mediante detección de drift:

```yaml
# NodePool configuration for Auto Mode
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: general-purpose
spec:
  template:
    spec:
      requirements:
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64", "arm64"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand", "spot"]
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["c", "m", "r"]
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
    # Drift detection triggers node replacement when AMI changes
    budgets:
      - nodes: "10%"      # Max 10% of nodes disrupted at once
      - nodes: "1"        # Or at least 1 node
        schedule: "0 9 * * *"   # Maintenance window
        duration: 8h
```

**Estrategia de actualización de AMI:**

```yaml
# EC2NodeClass with AMI selection
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: default
spec:
  amiSelectorTerms:
    # Auto Mode uses EKS-optimized AMIs
    - alias: al2023@latest

  role: "KarpenterNodeRole-prod-cluster"

  subnetSelectorTerms:
    - tags:
        karpenter.sh/discovery: "prod-cluster"

  securityGroupSelectorTerms:
    - tags:
        karpenter.sh/discovery: "prod-cluster"

  # Block device configuration
  blockDeviceMappings:
    - deviceName: /dev/xvda
      ebs:
        volumeSize: 100Gi
        volumeType: gp3
        iops: 3000
        throughput: 125
        encrypted: true
```

### Monitoreo del progreso de la actualización

**Comandos kubectl:**

```bash
#!/bin/bash
# monitor-upgrade.sh

echo "=== Cluster Version ==="
kubectl version --short

echo ""
echo "=== Node Versions ==="
kubectl get nodes -o custom-columns=\
'NAME:.metadata.name,'\
'VERSION:.status.nodeInfo.kubeletVersion,'\
'OS-IMAGE:.status.nodeInfo.osImage,'\
'AGE:.metadata.creationTimestamp'

echo ""
echo "=== Node Conditions ==="
kubectl get nodes -o json | jq -r '
  .items[] |
  "\(.metadata.name): \([.status.conditions[] | select(.status=="True") | .type] | join(", "))"
'

echo ""
echo "=== Karpenter Drift Status ==="
kubectl get nodeclaims -o custom-columns=\
'NAME:.metadata.name,'\
'NODE:.status.nodeName,'\
'READY:.status.conditions[?(@.type=="Ready")].status,'\
'AGE:.metadata.creationTimestamp'

echo ""
echo "=== Add-on Status ==="
aws eks list-addons --cluster-name prod-cluster --query 'addons[]' --output text | while read addon; do
  status=$(aws eks describe-addon --cluster-name prod-cluster --addon-name $addon \
    --query 'addon.status' --output text)
  version=$(aws eks describe-addon --cluster-name prod-cluster --addon-name $addon \
    --query 'addon.addonVersion' --output text)
  echo "$addon: $status ($version)"
done
```

**Consultas Prometheus para monitoreo:**

```promql
# Node rotation progress
count(kube_node_info) by (kubelet_version)

# Pods being rescheduled during upgrade
sum(rate(kube_pod_container_status_restarts_total[5m])) by (namespace)

# Node drain rate
rate(karpenter_nodes_terminated_total[10m])

# PDB blocking status
kube_poddisruptionbudget_status_pod_disruptions_allowed == 0

# Add-on health
kube_daemonset_status_number_ready{daemonset=~"aws-node|kube-proxy|ebs-csi-node"}
```

**Panel de Grafana dashboard:**

```json
{
  "title": "Upgrade Progress",
  "panels": [
    {
      "title": "Node Versions",
      "type": "piechart",
      "targets": [{
        "expr": "count(kube_node_info) by (kubelet_version)"
      }]
    },
    {
      "title": "Node Rotation Timeline",
      "type": "timeseries",
      "targets": [{
        "expr": "sum(karpenter_nodes_created_total)",
        "legendFormat": "Created"
      }, {
        "expr": "sum(karpenter_nodes_terminated_total)",
        "legendFormat": "Terminated"
      }]
    }
  ]
}
```

### Manejo de actualizaciones bloqueadas

```bash
#!/bin/bash
# unstick-upgrade.sh

echo "=== Identifying Stuck Nodes ==="
kubectl get nodes -l "karpenter.sh/lifecycle!=spot" \
  -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.conditions[?(@.type=="Ready")].status}{"\n"}{end}'

echo ""
echo "=== Checking for PDB Blocks ==="
kubectl get pdb -A -o json | jq -r '
  .items[] |
  select(.status.disruptionsAllowed == 0) |
  "BLOCKED: \(.metadata.namespace)/\(.metadata.name) - expectedPods:\(.status.expectedPods), currentHealthy:\(.status.currentHealthy)"
'

echo ""
echo "=== Pods Preventing Drain ==="
# Find pods on nodes being drained
for node in $(kubectl get nodes -o jsonpath='{.items[?(@.spec.unschedulable==true)].metadata.name}'); do
  echo "Node: $node"
  kubectl get pods --all-namespaces --field-selector spec.nodeName=$node \
    -o custom-columns='NAMESPACE:.metadata.namespace,NAME:.metadata.name,OWNER:.metadata.ownerReferences[0].kind'
done

echo ""
echo "=== Force Drain Options ==="
echo "1. Temporarily relax PDB:"
echo "   kubectl patch pdb <name> -n <ns> -p '{\"spec\":{\"maxUnavailable\":1}}'"
echo ""
echo "2. Delete stuck pods (use with caution):"
echo "   kubectl delete pod <name> -n <ns> --grace-period=0 --force"
echo ""
echo "3. Skip PDB check (emergency only):"
echo "   kubectl drain <node> --ignore-daemonsets --delete-emptydir-data --disable-eviction"
```

### Limitaciones de rollback

EKS Auto Mode tiene restricciones específicas de rollback:

| Componente | Rollback posible | Método |
|-----------|------------------|--------|
| Control Plane | No | Crear un nuevo cluster |
| Add-ons | Sí | Terraform apply de la versión anterior |
| Node AMI | Sí | Actualizar EC2NodeClass amiSelectorTerms |
| Aplicaciones | Sí | ArgoCD sync a la revisión anterior |

**Procedimiento de rollback (solo aplicaciones):**

```bash
#!/bin/bash
# rollback-applications.sh

APP_NAME="$1"
TARGET_REVISION="$2"

if [ -z "$APP_NAME" ] || [ -z "$TARGET_REVISION" ]; then
  echo "Usage: $0 <app-name> <target-revision>"
  exit 1
fi

echo "=== Current Application State ==="
argocd app get $APP_NAME

echo ""
echo "=== Available Revisions ==="
argocd app history $APP_NAME

echo ""
echo "=== Rolling Back to $TARGET_REVISION ==="
argocd app rollback $APP_NAME $TARGET_REVISION

echo ""
echo "=== Verify Rollback ==="
argocd app wait $APP_NAME --health --timeout 300
```

---

## 4. Estrategia de actualización Blue/Green

### Descripción general de la estrategia

Las actualizaciones Blue/Green proporcionan la ruta de actualización más segura al ejecutar dos clusters completos en paralelo:

```
┌─────────────────────────────────────────────────────────────┐
│                Blue/Green Upgrade Flow                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐   │
│   │   BLUE      │     │    NLB      │     │   GREEN     │   │
│   │  (Current)  │◄────│  Weighted   │────►│   (New)     │   │
│   │  EKS 1.30   │     │  Routing    │     │  EKS 1.31   │   │
│   └─────────────┘     └─────────────┘     └─────────────┘   │
│         │                   │                   │           │
│         ▼                   ▼                   ▼           │
│   100% → 90% → 50% → 10% → 0%            0% → 10% → ...     │
│                                                             │
│   Phase 1: Green cluster created                            │
│   Phase 2: Platform deployed                                │
│   Phase 3: ArgoCD deploys apps                              │
│   Phase 4: Traffic shifted gradually                        │
│   Phase 5: Blue decommissioned                              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Actualización Blue/Green paso a paso

#### Paso 1: Crear el cluster Green

```hcl
# terraform/02-cluster-green/main.tf

variable "cluster_version" {
  default = "1.31"
}

variable "cluster_suffix" {
  default = "green"
}

resource "aws_eks_cluster" "green" {
  name     = "prod-cluster-${var.cluster_suffix}"
  version  = var.cluster_version
  role_arn = data.aws_iam_role.cluster.arn

  vpc_config {
    subnet_ids              = data.aws_subnets.private.ids
    endpoint_private_access = true
    endpoint_public_access  = true
    security_group_ids      = [aws_security_group.cluster.id]
  }

  compute_config {
    enabled       = true
    node_pools    = ["general-purpose", "system"]
    node_role_arn = data.aws_iam_role.node.arn
  }

  kubernetes_network_config {
    ip_family         = "ipv4"
    service_ipv4_cidr = "10.101.0.0/16"  # Different from blue
    elastic_load_balancing {
      enabled = true
    }
  }

  storage_config {
    block_storage {
      enabled = true
    }
  }

  tags = merge(var.tags, {
    Environment = "production"
    Cluster     = "green"
    Version     = var.cluster_version
  })
}

output "cluster_name" {
  value = aws_eks_cluster.green.name
}

output "cluster_endpoint" {
  value = aws_eks_cluster.green.endpoint
}

output "cluster_ca_data" {
  value     = aws_eks_cluster.green.certificate_authority[0].data
  sensitive = true
}
```

#### Paso 2: Desplegar componentes de plataforma

```bash
#!/bin/bash
# deploy-platform-green.sh

GREEN_CLUSTER="prod-cluster-green"

echo "=== Updating kubeconfig ==="
aws eks update-kubeconfig --name $GREEN_CLUSTER --alias green

echo ""
echo "=== Deploying Platform Add-ons ==="
cd terraform/03-platform
terraform workspace select green || terraform workspace new green
terraform apply -var="cluster_name=$GREEN_CLUSTER" -auto-approve

echo ""
echo "=== Installing Cert Manager ==="
helm upgrade --install cert-manager jetstack/cert-manager \
  --namespace cert-manager --create-namespace \
  --version v1.15.0 \
  --set installCRDs=true

echo ""
echo "=== Installing AWS Load Balancer Controller ==="
helm upgrade --install aws-load-balancer-controller eks/aws-load-balancer-controller \
  --namespace kube-system \
  --set clusterName=$GREEN_CLUSTER \
  --set serviceAccount.create=false \
  --set serviceAccount.name=aws-load-balancer-controller

echo ""
echo "=== Installing External DNS ==="
helm upgrade --install external-dns bitnami/external-dns \
  --namespace external-dns --create-namespace \
  --set provider=aws \
  --set aws.zoneType=public \
  --set txtOwnerId=$GREEN_CLUSTER

echo ""
echo "=== Platform deployment complete ==="
kubectl get pods -A
```

#### Paso 3: Registrar con ArgoCD Hub

```yaml
# argocd/cluster-secret-green.yaml
apiVersion: v1
kind: Secret
metadata:
  name: prod-cluster-green
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: cluster
    environment: production
    cluster-color: green
    kubernetes-version: "1.31"
type: Opaque
stringData:
  name: prod-cluster-green
  server: https://XXXXXXXXXXXXXXXX.gr7.us-west-2.eks.amazonaws.com
  config: |
    {
      "awsAuthConfig": {
        "clusterName": "prod-cluster-green",
        "roleARN": "arn:aws:iam::ACCOUNT_ID:role/argocd-hub-role"
      },
      "tlsClientConfig": {
        "insecure": false,
        "caData": "BASE64_ENCODED_CA_DATA"
      }
    }
```

```bash
#!/bin/bash
# register-argocd-cluster.sh

GREEN_CLUSTER="prod-cluster-green"
GREEN_ENDPOINT=$(aws eks describe-cluster --name $GREEN_CLUSTER \
  --query 'cluster.endpoint' --output text)
GREEN_CA=$(aws eks describe-cluster --name $GREEN_CLUSTER \
  --query 'cluster.certificateAuthority.data' --output text)

# Create cluster secret
cat <<EOF | kubectl apply -f - --context argocd-hub
apiVersion: v1
kind: Secret
metadata:
  name: $GREEN_CLUSTER
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: cluster
    environment: production
    cluster-color: green
    kubernetes-version: "1.31"
type: Opaque
stringData:
  name: $GREEN_CLUSTER
  server: $GREEN_ENDPOINT
  config: |
    {
      "awsAuthConfig": {
        "clusterName": "$GREEN_CLUSTER",
        "roleARN": "arn:aws:iam::${AWS_ACCOUNT_ID}:role/argocd-hub-role"
      },
      "tlsClientConfig": {
        "insecure": false,
        "caData": "$GREEN_CA"
      }
    }
EOF

echo "Cluster registered with ArgoCD"
argocd cluster list
```

#### Paso 4: ApplicationSet despliega aplicaciones

```yaml
# argocd/applicationset-production.yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: production-apps
  namespace: argocd
spec:
  goTemplate: true
  goTemplateOptions: ["missingkey=error"]
  generators:
    - matrix:
        generators:
          # Generator 1: Clusters
          - clusters:
              selector:
                matchLabels:
                  environment: production
          # Generator 2: Applications
          - git:
              repoURL: https://github.com/company/k8s-apps.git
              revision: HEAD
              directories:
                - path: apps/*
  template:
    metadata:
      name: '{{.path.basename}}-{{.name}}'
      labels:
        app: '{{.path.basename}}'
        cluster: '{{.name}}'
        cluster-color: '{{index .metadata.labels "cluster-color"}}'
    spec:
      project: production
      source:
        repoURL: https://github.com/company/k8s-apps.git
        targetRevision: HEAD
        path: '{{.path.path}}'
        helm:
          valueFiles:
            - values.yaml
            - 'values-{{index .metadata.labels "cluster-color"}}.yaml'
      destination:
        server: '{{.server}}'
        namespace: '{{.path.basename}}'
      syncPolicy:
        automated:
          prune: true
          selfHeal: true
        syncOptions:
          - CreateNamespace=true
          - PrunePropagationPolicy=foreground
```

#### Paso 5: Smoke tests

```bash
#!/bin/bash
# smoke-test-green.sh

GREEN_CLUSTER="prod-cluster-green"
aws eks update-kubeconfig --name $GREEN_CLUSTER --alias green

echo "=== Application Health Check ==="
APPS=("api-gateway" "user-service" "order-service" "payment-service")

for app in "${APPS[@]}"; do
  echo "Checking $app..."

  # Deployment status
  ready=$(kubectl get deployment $app -n $app -o jsonpath='{.status.readyReplicas}')
  desired=$(kubectl get deployment $app -n $app -o jsonpath='{.spec.replicas}')

  if [ "$ready" == "$desired" ]; then
    echo "  Deployment: OK ($ready/$desired)"
  else
    echo "  Deployment: FAIL ($ready/$desired)"
    exit 1
  fi

  # Pod health
  unhealthy=$(kubectl get pods -n $app -o jsonpath='{.items[?(@.status.phase!="Running")].metadata.name}')
  if [ -z "$unhealthy" ]; then
    echo "  Pods: OK"
  else
    echo "  Pods: FAIL - $unhealthy"
    exit 1
  fi

  # Service endpoint
  endpoint=$(kubectl get svc $app -n $app -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
  if [ -n "$endpoint" ]; then
    echo "  Service: OK ($endpoint)"
  else
    echo "  Service: Internal only"
  fi
done

echo ""
echo "=== HTTP Health Checks ==="
# Internal health check via port-forward
for app in "${APPS[@]}"; do
  kubectl port-forward svc/$app 8080:80 -n $app &
  PID=$!
  sleep 2

  status=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/health)
  kill $PID 2>/dev/null

  if [ "$status" == "200" ]; then
    echo "$app health check: PASS"
  else
    echo "$app health check: FAIL ($status)"
    exit 1
  fi
done

echo ""
echo "=== All smoke tests passed ==="
```

#### Paso 6: Transición de peso de NLB

```hcl
# terraform/04-routing/nlb-weights.tf

variable "blue_weight" {
  description = "Traffic weight for blue cluster (0-100)"
  type        = number
  default     = 100
}

variable "green_weight" {
  description = "Traffic weight for green cluster (0-100)"
  type        = number
  default     = 0
}

resource "aws_lb_target_group" "blue" {
  name        = "prod-api-blue"
  port        = 443
  protocol    = "TCP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 2
    interval            = 10
    protocol            = "TCP"
  }

  tags = {
    Cluster = "blue"
  }
}

resource "aws_lb_target_group" "green" {
  name        = "prod-api-green"
  port        = 443
  protocol    = "TCP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 2
    interval            = 10
    protocol            = "TCP"
  }

  tags = {
    Cluster = "green"
  }
}

resource "aws_lb_listener" "api" {
  load_balancer_arn = aws_lb.api.arn
  port              = 443
  protocol          = "TCP"

  default_action {
    type = "forward"

    forward {
      target_group {
        arn    = aws_lb_target_group.blue.arn
        weight = var.blue_weight
      }

      target_group {
        arn    = aws_lb_target_group.green.arn
        weight = var.green_weight
      }

      stickiness {
        enabled  = true
        duration = 3600
      }
    }
  }
}

output "current_weights" {
  value = {
    blue  = var.blue_weight
    green = var.green_weight
  }
}
```

**Script de transición de peso:**

```bash
#!/bin/bash
# shift-traffic.sh

set -e

BLUE_WEIGHT=${1:-100}
GREEN_WEIGHT=${2:-0}

if [ $((BLUE_WEIGHT + GREEN_WEIGHT)) -ne 100 ]; then
  echo "Error: Weights must sum to 100"
  exit 1
fi

echo "=== Shifting Traffic ==="
echo "Blue: $BLUE_WEIGHT%"
echo "Green: $GREEN_WEIGHT%"

cd terraform/04-routing
terraform apply \
  -var="blue_weight=$BLUE_WEIGHT" \
  -var="green_weight=$GREEN_WEIGHT" \
  -auto-approve

echo ""
echo "=== Verifying Shift ==="
aws elbv2 describe-listeners \
  --load-balancer-arn $(terraform output -raw nlb_arn) \
  --query 'Listeners[0].DefaultActions[0].ForwardConfig.TargetGroups[*].{ARN:TargetGroupArn,Weight:Weight}' \
  --output table

echo ""
echo "=== Monitoring ==="
echo "Watch error rates: https://grafana.company.com/d/traffic-shift"
```

**Cronograma recomendado de transición de peso:**

| Etapa | Blue | Green | Duración | Validación |
|-------|------|-------|----------|------------|
| 1 | 100% | 0% | Inicial | Smoke tests de Green aprobados |
| 2 | 90% | 10% | 30 min | Tasa de errores estable |
| 3 | 50% | 50% | 1 hora | Comparación de latencia |
| 4 | 10% | 90% | 30 min | Validación final |
| 5 | 0% | 100% | - | Migración completa |

### Procedimiento de rollback

```bash
#!/bin/bash
# rollback-to-blue.sh

echo "=== Emergency Rollback to Blue Cluster ==="

# Immediate traffic shift
cd terraform/04-routing
terraform apply \
  -var="blue_weight=100" \
  -var="green_weight=0" \
  -auto-approve

echo ""
echo "=== Traffic restored to blue cluster ==="

# Document the rollback
cat >> upgrade-log.md << EOF

## Rollback Event - $(date -Iseconds)

**Reason**: [Document reason]
**Action**: Traffic shifted 100% to blue cluster
**Next Steps**:
- [ ] Investigate green cluster issues
- [ ] Review application logs
- [ ] Plan retry attempt
EOF

echo ""
echo "=== Post-Rollback Verification ==="
aws eks update-kubeconfig --name prod-cluster-blue --alias blue
kubectl --context blue get pods -A | grep -v Running
```

### Consideraciones de migración de datos

Cuando existan workloads con estado, planifica cuidadosamente la migración de datos:

```bash
#!/bin/bash
# data-migration-checklist.sh

echo "=== Stateful Workload Inventory ==="
kubectl get pvc -A -o custom-columns=\
'NAMESPACE:.metadata.namespace,'\
'NAME:.metadata.name,'\
'STORAGE-CLASS:.spec.storageClassName,'\
'SIZE:.spec.resources.requests.storage,'\
'STATUS:.status.phase'

echo ""
echo "=== Database Instances ==="
kubectl get pods -A -l 'app.kubernetes.io/component in (database,db,postgresql,mysql,mongodb)'

echo ""
echo "=== Migration Strategies ==="
cat << 'EOF'
1. AWS Native (RDS, ElastiCache, etc.)
   - No migration needed - external to cluster
   - Verify security group access from green cluster

2. In-Cluster StatefulSets
   - Option A: Velero backup/restore
   - Option B: Application-level replication
   - Option C: Shared EFS storage

3. PersistentVolumes
   - EBS: Snapshot and restore to new AZ
   - EFS: Mount same filesystem from both clusters

EOF
```

### Alternativa: actualización in-place zonal con rollback nativo

Dado que Amazon EKS agregó rollback nativo de versiones de Kubernetes (julio de 2026), los equipos que ya ejecutan un cluster por zona detrás del NLB ponderado de [NLB Weighted Target Groups](02-infrastructure-advanced.md#2-nlb-weighted-target-groups) tienen una opción más ligera que mantener indefinidamente una segunda flota completa de clusters: actualizar cada cluster zonal in-place, una zona a la vez, usando el enrutamiento ponderado existente solo para drenar tráfico durante la ventana de actualización, y confiando en el rollback nativo de EKS — no en un segundo cluster — como red de seguridad.

```
┌────────────────────────────────────────────────────────────┐
│      Zonal In-Place Upgrade (rollback as safety net)       │
├────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌─────────────┐     ┌─────────────┐    ┌─────────────┐   │
│   │   AZ-a      │◄────│    NLB      │───►│   AZ-c      │   │
│   │  1.30→1.31  │     │  Weighted   │    │   1.30      │   │
│   └─────────────┘     └─────────────┘    └─────────────┘   │
│                                                              │
│   1. Shift NLB weight: AZ-a -> 0%, AZ-c -> 100%             │
│   2. Upgrade AZ-a's control plane + nodes in place          │
│   3. Validate AZ-a, shift weight back to 50/50              │
│   4. Repeat for AZ-c                                        │
│   5. If AZ-a misbehaves post-upgrade: use EKS's native      │
│      rollback (control plane only, N -> N-1, within 7 days) │
│      instead of standing up a third cluster                 │
└────────────────────────────────────────────────────────────┘
```

**Cuándo encaja mejor que una flota Blue/Green permanente:**
- Ya ejecutas clusters zonales por disponibilidad, no específicamente para actualizaciones
- Quieres evitar el costo en estado estable de ejecutar dos flotas completas de clusters
- Tu ventana de actualización puede tolerar la elegibilidad de rollback de ~7 días en lugar de un failback instantáneo a nivel de cluster

**Cuándo mantener en su lugar la flota Blue/Green completa de esta sección:**
- Necesitas validar la nueva versión contra tráfico real de producción en un cluster completamente separado antes de hacer el corte — el rollback nativo solo revierte el control plane, no los cambios de node/AMI/add-on realizados in-place
- No se cumplen las condiciones de elegibilidad de rollback (cluster creado en la versión objetivo, más de 7 días transcurridos, otra actualización ya aplicada o una característica incompatible hacia atrás habilitada) — consulta [Estrategias de actualización de EKS — Procedimiento de rollback](../eks/08-eks-upgrades.md#rollback-procedure)

(Fuente: [Amazon EKS anuncia rollback de versiones de Kubernetes](https://aws.amazon.com/about-aws/whats-new/2026/07/amazon-eks-version-rollback), julio de 2026)

---

## 5. Validación posterior a la actualización

### Script completo de verificación de salud

```bash
#!/bin/bash
# post-upgrade-validation.sh

set -e

CLUSTER_NAME="${1:-prod-cluster}"
REPORT_DIR="./post-upgrade-reports/$(date +%Y%m%d-%H%M%S)"

mkdir -p $REPORT_DIR

echo "=============================================="
echo "Post-Upgrade Validation"
echo "Cluster: $CLUSTER_NAME"
echo "=============================================="

# 1. Cluster version verification
echo ""
echo "[1/7] Verifying cluster version..."
CLUSTER_VERSION=$(aws eks describe-cluster --name $CLUSTER_NAME \
  --query 'cluster.version' --output text)
echo "Cluster version: $CLUSTER_VERSION"

# 2. Node status
echo ""
echo "[2/7] Checking node status..."
kubectl get nodes -o wide | tee $REPORT_DIR/nodes.txt

NOT_READY=$(kubectl get nodes --no-headers | grep -v " Ready " | wc -l)
if [ "$NOT_READY" -gt 0 ]; then
  echo "WARNING: $NOT_READY nodes not ready"
  kubectl get nodes --no-headers | grep -v " Ready "
fi

# Verify all nodes on target version
NODE_VERSIONS=$(kubectl get nodes -o jsonpath='{.items[*].status.nodeInfo.kubeletVersion}' | tr ' ' '\n' | sort -u)
echo "Node versions: $NODE_VERSIONS"

# 3. Pod status
echo ""
echo "[3/7] Checking pod status..."
PROBLEM_PODS=$(kubectl get pods -A --field-selector=status.phase!=Running,status.phase!=Succeeded \
  --no-headers 2>/dev/null | wc -l)

if [ "$PROBLEM_PODS" -gt 0 ]; then
  echo "WARNING: $PROBLEM_PODS pods not in Running/Succeeded state"
  kubectl get pods -A --field-selector=status.phase!=Running,status.phase!=Succeeded
fi

# 4. Service connectivity
echo ""
echo "[4/7] Testing service connectivity..."
SERVICES=("api-gateway:api-gateway" "user-service:user-service")

for svc in "${SERVICES[@]}"; do
  ns="${svc%%:*}"
  name="${svc##*:}"

  endpoint=$(kubectl get endpoints $name -n $ns -o jsonpath='{.subsets[0].addresses[0].ip}' 2>/dev/null)
  if [ -n "$endpoint" ]; then
    echo "  $ns/$name: OK (endpoint: $endpoint)"
  else
    echo "  $ns/$name: WARNING - no endpoints"
  fi
done

# 5. Ingress reachability
echo ""
echo "[5/7] Testing ingress reachability..."
INGRESS_HOST=$(kubectl get ingress -n api-gateway -o jsonpath='{.items[0].status.loadBalancer.ingress[0].hostname}' 2>/dev/null)

if [ -n "$INGRESS_HOST" ]; then
  HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "https://$INGRESS_HOST/health" --connect-timeout 5 || echo "timeout")
  echo "  Ingress ($INGRESS_HOST): $HTTP_STATUS"
else
  echo "  No ingress found or not yet provisioned"
fi

# 6. Add-on status
echo ""
echo "[6/7] Verifying add-ons..."
for addon in vpc-cni coredns kube-proxy aws-ebs-csi-driver; do
  status=$(aws eks describe-addon --cluster-name $CLUSTER_NAME --addon-name $addon \
    --query 'addon.status' --output text 2>/dev/null || echo "NOT_INSTALLED")
  version=$(aws eks describe-addon --cluster-name $CLUSTER_NAME --addon-name $addon \
    --query 'addon.addonVersion' --output text 2>/dev/null || echo "-")
  echo "  $addon: $status ($version)"
done

# 7. Critical workload health
echo ""
echo "[7/7] Checking critical workloads..."
CRITICAL_DEPLOYMENTS=("kube-system:coredns" "kube-system:aws-load-balancer-controller" "argocd:argocd-server")

for deploy in "${CRITICAL_DEPLOYMENTS[@]}"; do
  ns="${deploy%%:*}"
  name="${deploy##*:}"

  ready=$(kubectl get deployment $name -n $ns -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo "0")
  desired=$(kubectl get deployment $name -n $ns -o jsonpath='{.spec.replicas}' 2>/dev/null || echo "0")

  if [ "$ready" == "$desired" ] && [ "$ready" != "0" ]; then
    echo "  $ns/$name: OK ($ready/$desired)"
  else
    echo "  $ns/$name: WARNING ($ready/$desired)"
  fi
done

echo ""
echo "=============================================="
echo "Validation complete. Review any warnings above."
echo "=============================================="
```

### Smoke tests

```bash
#!/bin/bash
# smoke-tests.sh

echo "=== HTTP Smoke Tests ==="

# Define test endpoints
declare -A ENDPOINTS=(
  ["api-gateway"]="https://api.company.com/health"
  ["web-app"]="https://www.company.com/"
  ["admin-portal"]="https://admin.company.com/health"
)

for name in "${!ENDPOINTS[@]}"; do
  url="${ENDPOINTS[$name]}"

  start_time=$(date +%s%N)
  status=$(curl -s -o /dev/null -w "%{http_code}" "$url" --connect-timeout 10 || echo "timeout")
  end_time=$(date +%s%N)

  latency=$(( (end_time - start_time) / 1000000 ))

  if [ "$status" == "200" ]; then
    echo "  $name: PASS (${latency}ms)"
  else
    echo "  $name: FAIL (status: $status)"
  fi
done

echo ""
echo "=== Database Connectivity ==="
# Test via application pods
kubectl exec -n api-gateway deploy/api-gateway -- \
  /bin/sh -c 'nc -zv $DB_HOST 5432 2>&1' || echo "DB connectivity test failed"

echo ""
echo "=== Message Queue Connectivity ==="
kubectl exec -n api-gateway deploy/api-gateway -- \
  /bin/sh -c 'nc -zv $MQ_HOST 5672 2>&1' || echo "MQ connectivity test failed"

echo ""
echo "=== Cache Connectivity ==="
kubectl exec -n api-gateway deploy/api-gateway -- \
  /bin/sh -c 'nc -zv $REDIS_HOST 6379 2>&1' || echo "Cache connectivity test failed"
```

### Comparación de métricas con PromQL

Compara métricas clave antes y después de la actualización:

```promql
# Error rate comparison (5xx errors)
# Run before upgrade, save value, compare after

# Current error rate
sum(rate(http_requests_total{status=~"5.."}[5m]))
/
sum(rate(http_requests_total[5m])) * 100

# P99 latency comparison
histogram_quantile(0.99,
  sum(rate(http_request_duration_seconds_bucket[5m])) by (le, service)
)

# Resource utilization - CPU
avg(rate(container_cpu_usage_seconds_total{namespace!~"kube-system|monitoring"}[5m])) by (namespace)

# Resource utilization - Memory
avg(container_memory_working_set_bytes{namespace!~"kube-system|monitoring"}) by (namespace) / 1024 / 1024

# Pod restart rate (should be near zero post-upgrade stabilization)
sum(increase(kube_pod_container_status_restarts_total[1h])) by (namespace)
```

**Grafana dashboard de comparación:**

```json
{
  "title": "Upgrade Comparison",
  "templating": {
    "list": [{
      "name": "comparison_time",
      "type": "custom",
      "options": [
        {"value": "now-1d", "text": "Yesterday"},
        {"value": "now-7d", "text": "Last Week"}
      ]
    }]
  },
  "panels": [
    {
      "title": "Error Rate: Before vs After",
      "type": "timeseries",
      "targets": [
        {
          "expr": "sum(rate(http_requests_total{status=~\"5..\"}[5m])) / sum(rate(http_requests_total[5m])) * 100",
          "legendFormat": "Current"
        },
        {
          "expr": "sum(rate(http_requests_total{status=~\"5..\"}[5m] offset 1d)) / sum(rate(http_requests_total[5m] offset 1d)) * 100",
          "legendFormat": "Before Upgrade"
        }
      ]
    },
    {
      "title": "P99 Latency: Before vs After",
      "type": "timeseries",
      "targets": [
        {
          "expr": "histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))",
          "legendFormat": "Current"
        },
        {
          "expr": "histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m] offset 1d)) by (le))",
          "legendFormat": "Before Upgrade"
        }
      ]
    }
  ]
}
```

### Periodo de monitoreo

**Checklist de monitoreo posterior a la actualización:**

| Periodo | Áreas de enfoque | Acciones |
|-----------|-------------|---------|
| 0-1 hora | Fallos críticos | Vigilar tasas de error, reinicios de pods |
| 1-4 horas | Regresión de rendimiento | Comparar latencia, throughput |
| 4-24 horas | Estabilidad | Fugas de memoria, degradación gradual |
| 1-7 días | Casos límite | Batch jobs, tareas programadas |

```bash
#!/bin/bash
# monitoring-period-alerts.sh

# Create temporary high-sensitivity alerts for post-upgrade period
cat <<EOF | kubectl apply -f -
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: post-upgrade-alerts
  namespace: monitoring
  labels:
    release: prometheus
spec:
  groups:
    - name: post-upgrade
      rules:
        - alert: PostUpgradeHighErrorRate
          expr: |
            sum(rate(http_requests_total{status=~"5.."}[5m]))
            / sum(rate(http_requests_total[5m])) > 0.01
          for: 2m
          labels:
            severity: warning
            context: post-upgrade
          annotations:
            summary: "Error rate elevated post-upgrade"

        - alert: PostUpgradeLatencyIncrease
          expr: |
            histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))
            >
            histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m] offset 1d)) by (le)) * 1.5
          for: 5m
          labels:
            severity: warning
            context: post-upgrade
          annotations:
            summary: "P99 latency increased >50% vs yesterday"

        - alert: PostUpgradePodRestarts
          expr: |
            sum(increase(kube_pod_container_status_restarts_total[30m])) by (namespace) > 5
          labels:
            severity: warning
            context: post-upgrade
          annotations:
            summary: "Elevated pod restarts in {{ \$labels.namespace }}"
EOF

echo "Post-upgrade alerts created. Remove after stabilization:"
echo "  kubectl delete prometheusrule post-upgrade-alerts -n monitoring"
```

### Actualización del runbook

Después de una actualización exitosa, actualiza la documentación operativa:

```markdown
# Post-Upgrade Runbook Update Checklist

## Version Information
- [ ] Update cluster version in documentation
- [ ] Update add-on version matrix
- [ ] Document any new features enabled

## Configuration Changes
- [ ] Document any API changes made
- [ ] Update Terraform module versions
- [ ] Update Helm chart versions

## Lessons Learned
- [ ] Document any issues encountered
- [ ] Note workarounds or fixes applied
- [ ] Update pre-upgrade checklist based on experience

## Timeline
- [ ] Record actual upgrade duration
- [ ] Note any deviations from plan
- [ ] Update time estimates for future upgrades
```

---

## Documentación relacionada

- [Actualizaciones de versiones de EKS](../eks/08-eks-upgrades.md) - Conceptos principales de actualización
- [Gestión del ciclo de vida de nodes](../eks-auto-mode/07-node-lifecycle.md) - Rotación de nodes de Auto Mode
- [ArgoCD Multi-Cluster](./04-gitops-multi-cluster.md) - Configuración de ApplicationSet
- [Stack de observabilidad](./09-observability-stack.md) - Configuración de monitoreo

---

< [Anterior: Optimización de recursos](./10-resource-optimization.md) | [Tabla de contenidos](./README.md) | [Siguiente: Planificación de capacidad para eventos](./12-event-capacity-planning.md) >
