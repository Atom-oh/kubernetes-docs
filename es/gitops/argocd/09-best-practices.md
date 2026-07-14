# Buenas prácticas de ArgoCD

> **Versiones compatibles**: ArgoCD v2.9+
> **Última actualización**: February 22, 2026

## Tabla de contenido
- [Estructura del repositorio](#repository-structure)
- [Promoción de entornos](#environment-promotion)
- [Gestión de recursos](#resource-management)
- [Ajuste de rendimiento](#performance-tuning)
- [Recuperación ante desastres](#disaster-recovery)
- [Estrategias de actualización](#upgrade-strategies)
- [Solución de problemas](#troubleshooting)
- [Buenas prácticas de EKS](#eks-best-practices)
- [Lista de verificación de producción](#production-checklist)

## Estructura del repositorio

### Patrón de monorepo

Repositorio único para todas las aplicaciones y entornos:

```
gitops-repo/
├── apps/
│   ├── app-a/
│   │   ├── base/
│   │   │   ├── deployment.yaml
│   │   │   ├── service.yaml
│   │   │   └── kustomization.yaml
│   │   └── overlays/
│   │       ├── dev/
│   │       │   ├── kustomization.yaml
│   │       │   └── patch.yaml
│   │       ├── staging/
│   │       │   ├── kustomization.yaml
│   │       │   └── patch.yaml
│   │       └── production/
│   │           ├── kustomization.yaml
│   │           └── patch.yaml
│   └── app-b/
│       └── ...
├── platform/
│   ├── argocd/
│   ├── monitoring/
│   └── ingress/
└── clusters/
    ├── dev/
    ├── staging/
    └── production/
```

**Ventajas:**
- Fuente única de verdad
- Cambios sencillos entre aplicaciones
- CI/CD simplificado
- Actualizaciones atómicas de múltiples aplicaciones

**Desventajas:**
- Puede volverse grande
- Complejidad del control de acceso
- Punto único de fallo

### Patrón de polyrepo

Repositorios independientes por aplicación o equipo:

```
Organization:
├── gitops-platform/          # Platform team
│   ├── argocd/
│   ├── monitoring/
│   └── ingress/
├── gitops-team-a/            # Team A applications
│   ├── app-a/
│   └── app-b/
├── gitops-team-b/            # Team B applications
│   ├── app-c/
│   └── app-d/
└── gitops-infra/             # Infrastructure
    ├── terraform/
    └── clusters/
```

**Ventajas:**
- Propiedad clara
- Despliegues independientes
- Control de acceso detallado
- Repositorios más pequeños

**Desventajas:**
- Más difícil coordinar cambios
- Más repositorios que gestionar
- Posibilidad de desviaciones

### Estructura del repositorio App of Apps

```
gitops-root/
├── argocd-apps/
│   ├── Chart.yaml
│   ├── values.yaml
│   ├── values-dev.yaml
│   ├── values-staging.yaml
│   ├── values-production.yaml
│   └── templates/
│       ├── _helpers.tpl
│       ├── namespace.yaml
│       ├── project.yaml
│       ├── app-a.yaml
│       ├── app-b.yaml
│       └── platform-apps.yaml
└── bootstrap/
    └── root-app.yaml
```

### Convenciones de nomenclatura recomendadas

| Tipo | Patrón | Ejemplo |
|------|---------|---------|
| Application | `{app}-{env}` | `frontend-production` |
| Project | `{team}` o `{env}` | `platform`, `production` |
| Namespace | `{app}` or `{app}-{env}` | `frontend`, `frontend-prod` |
| Repositorio | `gitops-{scope}` | `gitops-platform` |

## Promoción de entornos

### Estrategia de ramas de Git

```mermaid
flowchart LR
    subgraph BRANCHES["Git Branches"]
        DEV["develop"]
        STG["staging"]
        MAIN["main"]
    end

    subgraph ENVS["Environments"]
        E_DEV["Dev Cluster"]
        E_STG["Staging Cluster"]
        E_PROD["Production Cluster"]
    end

    DEV -->|"merge"| STG
    STG -->|"merge"| MAIN

    DEV -->|"deploy"| E_DEV
    STG -->|"deploy"| E_STG
    MAIN -->|"deploy"| E_PROD

    classDef branch fill:#f9f9f9,stroke:#333,color:black
    classDef env fill:#326CE5,stroke:#333,color:white

    class DEV,STG,MAIN branch
    class E_DEV,E_STG,E_PROD env
```

### Promoción basada en directorios

```yaml
# overlays/dev/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - ../../base
images:
  - name: myapp
    newTag: dev-abc1234

# overlays/staging/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - ../../base
images:
  - name: myapp
    newTag: v1.2.3-rc1

# overlays/production/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - ../../base
images:
  - name: myapp
    newTag: v1.2.3
```

### Pipeline de promoción automatizada

```yaml
# .github/workflows/promote.yaml
name: Promote to Production
on:
  workflow_dispatch:
    inputs:
      version:
        description: 'Version to promote'
        required: true

jobs:
  promote:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Update production overlay
        run: |
          cd overlays/production
          kustomize edit set image myapp=myregistry/myapp:${{ github.event.inputs.version }}

      - name: Create Pull Request
        uses: peter-evans/create-pull-request@v5
        with:
          title: "Promote ${{ github.event.inputs.version }} to production"
          branch: promote/${{ github.event.inputs.version }}
          commit-message: "chore: promote ${{ github.event.inputs.version }} to production"
```

## Gestión de recursos

### Recursos de componentes de ArgoCD

```yaml
# Helm values for production
controller:
  resources:
    requests:
      cpu: 500m
      memory: 512Mi
    limits:
      cpu: 2000m
      memory: 2Gi

server:
  resources:
    requests:
      cpu: 250m
      memory: 256Mi
    limits:
      cpu: 1000m
      memory: 1Gi

repoServer:
  resources:
    requests:
      cpu: 500m
      memory: 512Mi
    limits:
      cpu: 2000m
      memory: 2Gi

redis:
  resources:
    requests:
      cpu: 100m
      memory: 128Mi
    limits:
      cpu: 500m
      memory: 512Mi
```

### Límites de recursos por escala

| Escala | Aplicaciones | CPU del Controller | Memoria del Controller | CPU del Repo Server | Memoria del Repo Server |
|-------|--------------|----------------|-------------------|-----------------|-------------------|
| Pequeña | < 50 | 500m | 512Mi | 500m | 512Mi |
| Mediana | 50-200 | 1000m | 1Gi | 1000m | 1Gi |
| Grande | 200-500 | 2000m | 2Gi | 2000m | 2Gi |
| Muy grande | > 500 | 4000m | 4Gi | 4000m | 4Gi |

### Horizontal Pod Autoscaler

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: argocd-repo-server
  namespace: argocd
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: argocd-repo-server
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
```

## Ajuste de rendimiento

### Optimización del Controller

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cmd-params-cm
  namespace: argocd
data:
  # Reduce reconciliation frequency
  controller.status.processors: "50"
  controller.operation.processors: "25"
  controller.self.heal.timeout.seconds: "5"

  # Increase cache TTL
  controller.repo.server.timeout.seconds: "180"

  # Sharding for large deployments
  controller.sharding.algorithm: round-robin
```

### Optimización del Repo Server

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cmd-params-cm
  namespace: argocd
data:
  # Increase parallelism
  reposerver.parallelism.limit: "10"

  # Cache settings
  reposerver.repo.cache.expiration: "24h"

  # Git optimization
  reposerver.git.request.timeout: "60s"
  reposerver.git.lsremote.parallelism: "5"
```

### Optimización de Redis

```yaml
# For high-traffic deployments, use Redis HA
redis-ha:
  enabled: true
  redis:
    config:
      maxmemory: "512mb"
      maxmemory-policy: "allkeys-lru"
  haproxy:
    enabled: true
    replicas: 3
```

### Optimización a nivel de Application

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: large-app
  namespace: argocd
spec:
  # Reduce sync frequency for stable apps
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - ApplyOutOfSyncOnly=true  # Only apply changed resources

  # Ignore frequently changing fields
  ignoreDifferences:
    - group: apps
      kind: Deployment
      jsonPointers:
        - /spec/replicas
    - group: "*"
      kind: "*"
      managedFieldsManagers:
        - kube-controller-manager
```

## Recuperación ante desastres

### Estrategia de respaldo

```bash
#!/bin/bash
# backup-argocd.sh

BACKUP_DIR="/backups/argocd/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# Backup Applications
kubectl get applications -n argocd -o yaml > $BACKUP_DIR/applications.yaml

# Backup AppProjects
kubectl get appprojects -n argocd -o yaml > $BACKUP_DIR/appprojects.yaml

# Backup Repositories
kubectl get secrets -n argocd -l argocd.argoproj.io/secret-type=repository -o yaml > $BACKUP_DIR/repositories.yaml

# Backup Repo Credentials
kubectl get secrets -n argocd -l argocd.argoproj.io/secret-type=repo-creds -o yaml > $BACKUP_DIR/repo-creds.yaml

# Backup Clusters
kubectl get secrets -n argocd -l argocd.argoproj.io/secret-type=cluster -o yaml > $BACKUP_DIR/clusters.yaml

# Backup ConfigMaps
kubectl get configmaps -n argocd -o yaml > $BACKUP_DIR/configmaps.yaml

# Backup RBAC
kubectl get configmap argocd-rbac-cm -n argocd -o yaml > $BACKUP_DIR/rbac.yaml

echo "Backup completed: $BACKUP_DIR"
```

### Procedimiento de restauración

```bash
#!/bin/bash
# restore-argocd.sh

BACKUP_DIR=$1

if [ -z "$BACKUP_DIR" ]; then
  echo "Usage: restore-argocd.sh <backup-dir>"
  exit 1
fi

# Ensure ArgoCD is installed
kubectl get namespace argocd || kubectl create namespace argocd

# Restore in order
kubectl apply -f $BACKUP_DIR/configmaps.yaml
kubectl apply -f $BACKUP_DIR/rbac.yaml
kubectl apply -f $BACKUP_DIR/repo-creds.yaml
kubectl apply -f $BACKUP_DIR/repositories.yaml
kubectl apply -f $BACKUP_DIR/clusters.yaml
kubectl apply -f $BACKUP_DIR/appprojects.yaml
kubectl apply -f $BACKUP_DIR/applications.yaml

# Restart ArgoCD components
kubectl rollout restart deployment -n argocd

echo "Restore completed"
```

### DR multirregión

```yaml
# Primary region ArgoCD manages secondary
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: argocd-dr
  namespace: argocd
spec:
  project: platform
  source:
    repoURL: https://github.com/myorg/gitops-platform.git
    targetRevision: HEAD
    path: argocd
  destination:
    server: https://dr-region.k8s.local  # DR cluster
    namespace: argocd
  syncPolicy:
    automated:
      prune: false  # Don't auto-prune in DR
      selfHeal: true
```

## Estrategias de actualización

### Lista de verificación previa a la actualización

1. **Revisa las notas de la versión** para detectar cambios incompatibles
2. **Respalda el estado actual** (applications, projects, secrets)
3. **Prueba primero en un entorno que no sea de producción**
4. **Programa una ventana de mantenimiento** si es necesario
5. **Notifica a las partes interesadas**

### Actualización gradual

```bash
# 1. Update ArgoCD manifests
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/v2.13.0/manifests/install.yaml

# 2. Wait for rollout
kubectl rollout status deployment argocd-server -n argocd
kubectl rollout status deployment argocd-repo-server -n argocd
kubectl rollout status deployment argocd-application-controller -n argocd

# 3. Verify
argocd version
argocd app list
```

### Actualización blue-green

```bash
# 1. Install new version in separate namespace
kubectl create namespace argocd-new
kubectl apply -n argocd-new -f https://raw.githubusercontent.com/argoproj/argo-cd/v2.13.0/manifests/install.yaml

# 2. Migrate configuration
kubectl get configmap argocd-cm -n argocd -o yaml | sed 's/namespace: argocd/namespace: argocd-new/' | kubectl apply -f -
kubectl get configmap argocd-rbac-cm -n argocd -o yaml | sed 's/namespace: argocd/namespace: argocd-new/' | kubectl apply -f -

# 3. Test new installation
kubectl port-forward svc/argocd-server -n argocd-new 8081:443

# 4. Switch traffic (update ingress/load balancer)
# 5. Decommission old installation
kubectl delete namespace argocd
kubectl rename namespace argocd-new argocd
```

## Solución de problemas

### Problemas comunes y soluciones

#### Fallos de sincronización

```bash
# Check application events
kubectl describe application my-app -n argocd

# Check application controller logs
kubectl logs -n argocd -l app.kubernetes.io/name=argocd-application-controller --tail=100

# Force refresh
argocd app get my-app --refresh

# Hard refresh (clear cache)
argocd app get my-app --hard-refresh
```

#### Problemas de conexión con el repositorio

```bash
# Test repository connectivity
argocd repo list
argocd repo get https://github.com/myorg/myrepo.git

# Check repo server logs
kubectl logs -n argocd -l app.kubernetes.io/name=argocd-repo-server --tail=100

# Verify credentials
kubectl get secret -n argocd -l argocd.argoproj.io/secret-type=repository
```

#### Memoria insuficiente (OOM)

```bash
# Check current memory usage
kubectl top pods -n argocd

# Increase limits
kubectl patch deployment argocd-repo-server -n argocd -p '
{
  "spec": {
    "template": {
      "spec": {
        "containers": [{
          "name": "argocd-repo-server",
          "resources": {
            "limits": {"memory": "4Gi"},
            "requests": {"memory": "2Gi"}
          }
        }]
      }
    }
  }
}'
```

#### Sincronización lenta

```bash
# Check sync duration
argocd app get my-app -o json | jq '.status.operationState.finishedAt, .status.operationState.startedAt'

# Enable debug logging
kubectl patch configmap argocd-cmd-params-cm -n argocd -p '{"data":{"controller.log.level":"debug"}}'

# Check for large manifests
argocd app manifests my-app | wc -l
```

### Hoja de referencia de comandos de depuración

```bash
# Application status
argocd app get <app-name>
argocd app get <app-name> -o json | jq '.status'

# Diff between desired and live
argocd app diff <app-name>

# View manifests
argocd app manifests <app-name>

# Sync with debug
argocd app sync <app-name> --debug

# View all applications
argocd app list -o wide

# Check cluster connectivity
argocd cluster list
argocd cluster get <cluster-url>

# View logs
kubectl logs -n argocd deployment/argocd-server --tail=100
kubectl logs -n argocd deployment/argocd-repo-server --tail=100
kubectl logs -n argocd deployment/argocd-application-controller --tail=100

# Clear application cache
argocd app get <app-name> --hard-refresh

# Force reconciliation
kubectl patch application <app-name> -n argocd -p '{"metadata":{"annotations":{"argocd.argoproj.io/refresh":"hard"}}}' --type merge
```

## Buenas prácticas de EKS

### Configuración de IRSA

```yaml
# Service account with IRSA
apiVersion: v1
kind: ServiceAccount
metadata:
  name: argocd-application-controller
  namespace: argocd
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/ArgoCD-Controller
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: argocd-repo-server
  namespace: argocd
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/ArgoCD-RepoServer
```

### ALB Ingress con WAF

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: argocd-server
  namespace: argocd
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:us-west-2:123456789012:certificate/xxx
    alb.ingress.kubernetes.io/wafv2-acl-arn: arn:aws:wafv2:us-west-2:123456789012:regional/webacl/argocd/xxx
    alb.ingress.kubernetes.io/shield-advanced-protection: "true"
    alb.ingress.kubernetes.io/ssl-policy: ELBSecurityPolicy-TLS-1-2-2017-01
spec:
  rules:
    - host: argocd.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: argocd-server
                port:
                  number: 443
```

### Actualizaciones de clústeres de EKS

Al actualizar clústeres de EKS gestionados por ArgoCD:

1. **Actualiza el secret de clúster de ArgoCD** con el nuevo endpoint de API si ha cambiado
2. **Prueba la conectividad** después de la actualización
3. **Vuelve a sincronizar las aplicaciones** para verificar la compatibilidad
4. **Actualiza la versión de Kubernetes** en los manifiestos de Application si está codificada de forma rígida

## Lista de verificación de producción

### Seguridad

- [ ] SSO configurado y probado
- [ ] Políticas de RBAC implementadas
- [ ] TLS habilitado para todos los endpoints
- [ ] Secrets almacenados externamente (no en Git)
- [ ] Políticas de red aplicadas
- [ ] Registro de auditoría habilitado
- [ ] Credenciales de repositorio protegidas
- [ ] Contraseña de administrador cambiada respecto a la predeterminada

### Alta disponibilidad

- [ ] Múltiples réplicas para todos los componentes
- [ ] Redis HA habilitado
- [ ] Sharding del Controller configurado (si hay > 100 aplicaciones)
- [ ] Límites de recursos establecidos adecuadamente
- [ ] HPA configurado para repo-server
- [ ] PodDisruptionBudgets configurados

### Monitorización

- [ ] Métricas de Prometheus habilitadas
- [ ] ServiceMonitor configurado
- [ ] Dashboards creados (Grafana)
- [ ] Alertas configuradas para:
  - [ ] Fallos de sincronización
  - [ ] Degradación del estado de salud
  - [ ] Uso elevado de memoria
  - [ ] Errores del servidor de API

### Respaldo y DR

- [ ] Script de respaldo configurado
- [ ] Programación de respaldos establecida (mínimo diario)
- [ ] Procedimiento de restauración documentado y probado
- [ ] Sitio de DR configurado (si es necesario)

### Operaciones

- [ ] Servicios de notificación configurados
- [ ] Ventanas de sincronización definidas para producción
- [ ] Projects configurados por equipo/entorno
- [ ] Estructura del repositorio documentada
- [ ] Procedimiento de actualización documentado
- [ ] Runbook creado para problemas comunes

## Cuestionario

Para comprobar lo que has aprendido, prueba el [cuestionario de buenas prácticas de ArgoCD](../../quizzes/gitops/argocd/09-best-practices-quiz.md).
