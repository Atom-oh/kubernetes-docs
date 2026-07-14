# Proyectos y RBAC de ArgoCD

> **Versiones compatibles**: ArgoCD v2.9+
> **Última actualización**: February 22, 2026

## Tabla de contenido
- [Descripción general de AppProject](#appproject-overview)
- [Proyecto predeterminado](#default-project)
- [Proyectos personalizados](#custom-projects)
- [Configuración de RBAC](#rbac-configuration)
- [Patrones de multi-tenencia](#multi-tenancy-patterns)
- [Tokens JWT para CI/CD](#jwt-tokens-for-cicd)
- [Monitoreo de recursos huérfanos](#orphaned-resource-monitoring)

## Descripción general de AppProject

Los AppProjects proporcionan una agrupación lógica de Applications y definen controles de acceso para los recursos que se pueden desplegar, dónde se pueden desplegar y quién puede administrarlos.

### Capacidades clave

| Característica | Descripción |
|---------|-------------|
| Restricciones de origen | Limita qué repositorios Git se pueden usar |
| Restricciones de destino | Limita los clústeres y namespaces de destino |
| Lista de permisos/denegación de recursos | Controla qué recursos de K8s se pueden crear |
| Definiciones de roles | Define roles de RBAC específicos del proyecto |
| Ventanas de sincronización | Define cuándo las aplicaciones pueden sincronizarse |

### Estructura del CRD de AppProject

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: my-project
  namespace: argocd
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  description: "Project description"

  # Source repositories
  sourceRepos:
    - https://github.com/myorg/*
    - https://charts.helm.sh/stable

  # Allowed destinations
  destinations:
    - namespace: my-app-*
      server: https://kubernetes.default.svc
    - namespace: '*'
      server: https://production.k8s.local

  # Cluster resource allowlist
  clusterResourceWhitelist:
    - group: ''
      kind: Namespace
    - group: rbac.authorization.k8s.io
      kind: ClusterRole
    - group: rbac.authorization.k8s.io
      kind: ClusterRoleBinding

  # Cluster resource denylist
  clusterResourceBlacklist:
    - group: ''
      kind: ResourceQuota

  # Namespace resource allowlist (default: allow all)
  namespaceResourceWhitelist:
    - group: '*'
      kind: '*'

  # Namespace resource denylist
  namespaceResourceBlacklist:
    - group: ''
      kind: LimitRange

  # Project roles
  roles:
    - name: developer
      description: Developer access
      policies:
        - p, proj:my-project:developer, applications, get, my-project/*, allow
        - p, proj:my-project:developer, applications, sync, my-project/*, allow
      groups:
        - my-org:developers

  # Sync windows
  syncWindows:
    - kind: allow
      schedule: '0 9 * * 1-5'
      duration: 8h
      applications:
        - '*'

  # Orphaned resource monitoring
  orphanedResources:
    warn: true
    ignore:
      - group: ''
        kind: ConfigMap
        name: kube-root-ca.crt
```

## Proyecto predeterminado

ArgoCD incluye un proyecto `default` que permite todos los orígenes, destinos y recursos.

### Especificación del proyecto predeterminado

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: default
  namespace: argocd
spec:
  description: Default project
  sourceRepos:
    - '*'
  destinations:
    - namespace: '*'
      server: '*'
  clusterResourceWhitelist:
    - group: '*'
      kind: '*'
```

### Cuándo usar el proyecto predeterminado

- Entornos de desarrollo
- Pruebas rápidas
- Equipos pequeños sin requisitos de multi-tenencia

### Restricción del proyecto predeterminado

Para producción, restrinja el proyecto predeterminado:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: default
  namespace: argocd
spec:
  description: Restricted default project
  sourceRepos: []  # No repos allowed
  destinations: []  # No destinations allowed
```

## Proyectos personalizados

### Proyecto basado en equipos

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: team-frontend
  namespace: argocd
spec:
  description: Frontend team project

  sourceRepos:
    - https://github.com/myorg/frontend-*
    - https://github.com/myorg/shared-libs

  destinations:
    - namespace: frontend-*
      server: https://kubernetes.default.svc
    - namespace: frontend-*
      server: https://staging.k8s.local
    - namespace: frontend-*
      server: https://production.k8s.local

  clusterResourceWhitelist:
    - group: ''
      kind: Namespace

  namespaceResourceBlacklist:
    # Prevent privileged workloads
    - group: ''
      kind: Pod
    # Use Deployments instead

  roles:
    - name: admin
      description: Project admin
      policies:
        - p, proj:team-frontend:admin, applications, *, team-frontend/*, allow
        - p, proj:team-frontend:admin, repositories, *, team-frontend/*, allow
      groups:
        - myorg:frontend-leads

    - name: developer
      description: Developer access
      policies:
        - p, proj:team-frontend:developer, applications, get, team-frontend/*, allow
        - p, proj:team-frontend:developer, applications, sync, team-frontend/*, allow
        - p, proj:team-frontend:developer, applications, action/*, team-frontend/*, allow
      groups:
        - myorg:frontend-devs

    - name: viewer
      description: Read-only access
      policies:
        - p, proj:team-frontend:viewer, applications, get, team-frontend/*, allow
      groups:
        - myorg:frontend-viewers
```

### Proyecto basado en entornos

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: production
  namespace: argocd
spec:
  description: Production environment project

  sourceRepos:
    - https://github.com/myorg/gitops-prod

  destinations:
    - namespace: '*'
      server: https://production.k8s.local
    - namespace: '*'
      server: https://production-dr.k8s.local

  clusterResourceWhitelist:
    - group: ''
      kind: Namespace
    - group: networking.k8s.io
      kind: IngressClass
    - group: storage.k8s.io
      kind: StorageClass

  # Restrict certain namespaced resources in production
  namespaceResourceBlacklist:
    - group: ''
      kind: Pod  # Force use of controllers
    - group: batch
      kind: Job  # Jobs should go through CI/CD

  syncWindows:
    # Only allow sync during business hours
    - kind: allow
      schedule: '0 9 * * 1-5'
      duration: 8h
      applications:
        - '*'
      manualSync: true

    # Emergency window (manual only)
    - kind: allow
      schedule: '0 0 * * *'
      duration: 24h
      applications:
        - '*'
      manualSync: true

  roles:
    - name: sre
      description: SRE team with full access
      policies:
        - p, proj:production:sre, applications, *, production/*, allow
      groups:
        - myorg:sre-team

    - name: deployer
      description: CI/CD deployment access
      policies:
        - p, proj:production:deployer, applications, sync, production/*, allow
        - p, proj:production:deployer, applications, get, production/*, allow
```

### Proyecto de infraestructura de plataforma

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: platform
  namespace: argocd
spec:
  description: Platform infrastructure components

  sourceRepos:
    - https://github.com/myorg/platform-*
    - https://prometheus-community.github.io/helm-charts
    - https://grafana.github.io/helm-charts
    - https://charts.jetstack.io
    - https://kubernetes.github.io/ingress-nginx

  destinations:
    - namespace: kube-system
      server: '*'
    - namespace: monitoring
      server: '*'
    - namespace: logging
      server: '*'
    - namespace: ingress-nginx
      server: '*'
    - namespace: cert-manager
      server: '*'

  # Platform needs cluster-wide resources
  clusterResourceWhitelist:
    - group: '*'
      kind: '*'

  roles:
    - name: platform-admin
      description: Platform team admin
      policies:
        - p, proj:platform:platform-admin, applications, *, platform/*, allow
        - p, proj:platform:platform-admin, clusters, *, *, allow
        - p, proj:platform:platform-admin, repositories, *, *, allow
      groups:
        - myorg:platform-team
```

## Configuración de RBAC

El RBAC de ArgoCD se configura en el ConfigMap `argocd-rbac-cm`.

### Sintaxis de la política de RBAC

```
p, <subject>, <resource>, <action>, <object>, <effect>
g, <subject>, <role>
```

| Campo | Descripción |
|-------|-------------|
| `subject` | Usuario, grupo o rol |
| `resource` | applications, clusters, repositories, etc. |
| `action` | get, create, update, delete, sync, etc. |
| `object` | Identificador de recurso (proyecto/app o *) |
| `effect` | allow o deny |

### Roles integrados

| Rol | Descripción |
|------|-------------|
| `role:readonly` | Acceso de solo lectura a todos los recursos |
| `role:admin` | Acceso completo a todos los recursos |

### Configuración completa de RBAC

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-rbac-cm
  namespace: argocd
data:
  # Default policy for authenticated users
  policy.default: role:readonly

  # Scope RBAC policies to specific AppProjects
  scopes: '[groups]'

  policy.csv: |
    # Built-in admin role (full access)
    p, role:admin, applications, *, */*, allow
    p, role:admin, clusters, *, *, allow
    p, role:admin, repositories, *, *, allow
    p, role:admin, projects, *, *, allow
    p, role:admin, accounts, *, *, allow
    p, role:admin, gpgkeys, *, *, allow
    p, role:admin, certificates, *, *, allow
    p, role:admin, logs, *, *, allow
    p, role:admin, exec, *, */*, allow

    # Built-in readonly role
    p, role:readonly, applications, get, */*, allow
    p, role:readonly, clusters, get, *, allow
    p, role:readonly, repositories, get, *, allow
    p, role:readonly, projects, get, *, allow
    p, role:readonly, logs, get, */*, allow

    # Custom organization roles
    # Org admins
    p, role:org-admin, applications, *, */*, allow
    p, role:org-admin, clusters, get, *, allow
    p, role:org-admin, repositories, *, *, allow
    p, role:org-admin, projects, *, *, allow

    # Developers (can sync and view, but not delete)
    p, role:developer, applications, get, */*, allow
    p, role:developer, applications, sync, */*, allow
    p, role:developer, applications, action/*, */*, allow
    p, role:developer, logs, get, */*, allow
    p, role:developer, exec, create, */*, allow

    # Viewers
    p, role:viewer, applications, get, */*, allow
    p, role:viewer, logs, get, */*, allow

    # Group to role mappings
    g, myorg:admins, role:admin
    g, myorg:org-admins, role:org-admin
    g, myorg:developers, role:developer
    g, myorg:viewers, role:viewer

    # User to role mappings
    g, admin@example.com, role:admin
    g, ci-bot, role:developer

    # Project-scoped roles (defined in AppProject)
    # These are auto-generated: proj:<project>:<role>
```

### Permisos específicos de recursos

```yaml
policy.csv: |
  # Applications - fine-grained permissions
  p, role:deployer, applications, get, */*, allow
  p, role:deployer, applications, sync, */*, allow
  p, role:deployer, applications, update, */*, deny
  p, role:deployer, applications, delete, */*, deny

  # Cluster management
  p, role:cluster-admin, clusters, *, *, allow
  p, role:cluster-viewer, clusters, get, *, allow

  # Repository management
  p, role:repo-admin, repositories, *, *, allow
  p, role:repo-viewer, repositories, get, *, allow

  # Project-specific permissions
  p, role:team-a-admin, applications, *, team-a/*, allow
  p, role:team-a-admin, projects, get, team-a, allow

  # Exec into running pods (debugging)
  p, role:debugger, exec, create, */*, allow
  p, role:debugger, applications, get, */*, allow
```

### Acciones específicas de Applications

```yaml
policy.csv: |
  # Sync-only role (for CI/CD)
  p, role:sync-only, applications, get, */*, allow
  p, role:sync-only, applications, sync, */*, allow

  # Override action (allows syncing with force)
  p, role:operator, applications, action/apps/Deployment/restart, */*, allow

  # Rollback permission
  p, role:operator, applications, update, */*, allow
```

## Patrones de multi-tenencia

### Un namespace por equipo

```mermaid
flowchart TB
    subgraph ARGOCD["ArgoCD"]
        PROJ_A["Project: team-a"]
        PROJ_B["Project: team-b"]
        PROJ_P["Project: platform"]
    end

    subgraph CLUSTER["Kubernetes Cluster"]
        NS_A["Namespace: team-a"]
        NS_B["Namespace: team-b"]
        NS_P["Namespaces: kube-system, monitoring"]
    end

    PROJ_A -->|"can deploy to"| NS_A
    PROJ_B -->|"can deploy to"| NS_B
    PROJ_P -->|"can deploy to"| NS_P

    classDef project fill:#EB6E85,stroke:#333,color:white
    classDef namespace fill:#326CE5,stroke:#333,color:white

    class PROJ_A,PROJ_B,PROJ_P project
    class NS_A,NS_B,NS_P namespace
```

Implementación:

```yaml
# Team A Project
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: team-a
  namespace: argocd
spec:
  sourceRepos:
    - https://github.com/myorg/team-a-*
  destinations:
    - namespace: team-a
      server: https://kubernetes.default.svc
    - namespace: team-a-*
      server: https://kubernetes.default.svc
  clusterResourceWhitelist: []  # No cluster resources
  roles:
    - name: admin
      policies:
        - p, proj:team-a:admin, applications, *, team-a/*, allow
      groups:
        - team-a-admins
---
# Team B Project
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: team-b
  namespace: argocd
spec:
  sourceRepos:
    - https://github.com/myorg/team-b-*
  destinations:
    - namespace: team-b
      server: https://kubernetes.default.svc
    - namespace: team-b-*
      server: https://kubernetes.default.svc
  clusterResourceWhitelist: []
  roles:
    - name: admin
      policies:
        - p, proj:team-b:admin, applications, *, team-b/*, allow
      groups:
        - team-b-admins
```

### Un clúster por entorno

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: development
  namespace: argocd
spec:
  sourceRepos:
    - '*'
  destinations:
    - namespace: '*'
      server: https://dev.k8s.local
  # Relaxed for development
  clusterResourceWhitelist:
    - group: '*'
      kind: '*'
---
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: production
  namespace: argocd
spec:
  sourceRepos:
    - https://github.com/myorg/gitops-prod
  destinations:
    - namespace: '*'
      server: https://prod.k8s.local
  # Strict for production
  clusterResourceWhitelist:
    - group: ''
      kind: Namespace
  syncWindows:
    - kind: deny
      schedule: '0 0 * * 0,6'  # No weekend deploys
      duration: 48h
      applications:
        - '*'
```

## Tokens JWT para CI/CD

Cree tokens con alcance de proyecto para la automatización.

### Crear un token JWT

```bash
# Create token for project role
argocd proj role create-token my-project deployer

# Create token with expiration
argocd proj role create-token my-project deployer --expires-in 24h

# Create token with ID (for revocation)
argocd proj role create-token my-project deployer --token-id ci-pipeline-1
```

### Usar el token en CI/CD

```yaml
# GitHub Actions example
name: Deploy to ArgoCD
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install ArgoCD CLI
        run: |
          curl -sSL -o argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
          chmod +x argocd
          sudo mv argocd /usr/local/bin/

      - name: Login to ArgoCD
        run: |
          argocd login ${{ secrets.ARGOCD_SERVER }} \
            --auth-token ${{ secrets.ARGOCD_TOKEN }} \
            --grpc-web

      - name: Sync Application
        run: |
          argocd app sync my-app --prune
          argocd app wait my-app --health
```

### Administración de tokens

```bash
# List tokens
argocd proj role list-tokens my-project deployer

# Delete token
argocd proj role delete-token my-project deployer <token-id>
```

### Token mediante Secret

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: argocd-ci-token
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: argocd-token
stringData:
  token: <jwt-token>
```

## Monitoreo de recursos huérfanos

Detecte recursos en los namespaces de destino que no estén administrados por ArgoCD.

### Habilitar el monitoreo de recursos huérfanos

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: my-project
  namespace: argocd
spec:
  orphanedResources:
    warn: true
    ignore:
      # Ignore specific resources
      - group: ''
        kind: ConfigMap
        name: kube-root-ca.crt
      - group: ''
        kind: ServiceAccount
        name: default
      # Ignore by pattern
      - group: ''
        kind: Secret
        name: 'default-token-*'
```

### Ver recursos huérfanos

```bash
# Via CLI
argocd app resources my-app --orphaned

# Via API
curl -s https://argocd.example.com/api/v1/applications/my-app/resource-tree | jq '.orphanedNodes'
```

### Limpieza automática

Actualmente, ArgoCD solo advierte sobre recursos huérfanos. Para realizar una limpieza automática, use un hook post-sync:

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: cleanup-orphans
  annotations:
    argocd.argoproj.io/hook: PostSync
    argocd.argoproj.io/hook-delete-policy: HookSucceeded
spec:
  template:
    spec:
      serviceAccountName: orphan-cleaner
      restartPolicy: Never
      containers:
        - name: cleaner
          image: bitnami/kubectl:latest
          command:
            - /bin/sh
            - -c
            - |
              # Custom cleanup logic
              kubectl get configmaps -n my-namespace -l managed-by!=argocd -o name | xargs -r kubectl delete -n my-namespace
```

## Cuestionario

Para comprobar lo que ha aprendido, pruebe el [cuestionario de proyectos y RBAC de ArgoCD](../../quizzes/gitops/argocd/06-projects-rbac-quiz.md).
