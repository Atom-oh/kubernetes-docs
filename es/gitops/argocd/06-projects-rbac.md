# Proyectos y RBAC de ArgoCD

> **Revisado con respecto a**: Argo CD 3.5.2; actualizado al parche 3.5.4 tras revisar las notas de la versión (los ejemplos no se volvieron a ejecutar)
> **Última actualización**: October 12, 2026

## Tabla de contenidos
- [Descripción general de AppProject](#appproject-overview)
- [Proyecto predeterminado](#default-project)
- [Proyectos personalizados](#custom-projects)
- [Configuración de RBAC](#rbac-configuration)
- [Patrones de multi-tenancy](#multi-tenancy-patterns)
- [Tokens JWT para CI/CD](#jwt-tokens-for-cicd)
- [Monitoreo de recursos huérfanos](#orphaned-resource-monitoring)

## Descripción general de AppProject

Los AppProjects proporcionan agrupación lógica de Applications y definen controles de acceso para los recursos que se pueden desplegar, dónde se pueden desplegar y quién puede administrarlos.

AppProject restringe las fuentes, los destinos, los tipos de recursos renderizados y los permisos de la API de Argo CD. No reemplaza Kubernetes RBAC, Pod Security Admission, NetworkPolicy ni ResourceQuota. Denegar el tipo Pod no evita que un Deployment cree Pods privilegiados.

Proporcione URL reales de repositorios, grupos, clústeres registrados y namespaces. Los administradores de la plataforma crean previamente los namespaces de aplicación y son responsables de sus políticas de seguridad/cuotas. Los proyectos de equipo/entorno siguientes no permiten recursos con ámbito de clúster; el proyecto de plataforma independiente es para administradores de confianza. Los ejemplos completos de proyectos son alternativas independientes, incluidos aquellos que comparten un nombre.

### Capacidades clave

| Característica | Descripción |
|---------|-------------|
| Restricciones de fuente | Limitan qué repositorios Git se pueden usar |
| Restricciones de destino | Limitan los clústeres y namespaces de destino |
| Lista de permitidos/lista de denegados de recursos | Controla qué recursos de K8s se pueden crear |
| Definiciones de roles | Define roles de RBAC específicos del proyecto |
| Ventanas de sincronización | Define cuándo se pueden sincronizar las aplicaciones |

### Ejemplo de configuración de AppProject

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: my-project
  namespace: argocd
  finalizers:
  - resources-finalizer.argocd.argoproj.io
spec:
  description: Project description
  sourceRepos:
  - https://github.com/myorg/*
  - https://stefanprodan.github.io/podinfo
  destinations:
  - namespace: my-app-*
    server: https://kubernetes.default.svc
  - namespace: my-project-*
    server: https://production.k8s.local
  clusterResourceWhitelist: []
  namespaceResourceWhitelist:
  - group: '*'
    kind: '*'
  namespaceResourceBlacklist:
  - group: ''
    kind: LimitRange
  - group: ''
    kind: ResourceQuota
  roles:
  - name: developer
    description: Developer access
    policies:
    - p, proj:my-project:developer, applications, get, my-project/*, allow
    - p, proj:my-project:developer, applications, sync, my-project/*, allow
    groups:
    - my-org:developers
  syncWindows:
  - kind: allow
    schedule: 0 9 * * 1-5
    duration: 8h
    applications:
    - '*'
    timeZone: Asia/Seoul
  orphanedResources:
    warn: true
    ignore:
    - group: ''
      kind: ConfigMap
      name: kube-root-ca.crt
```

## Proyecto predeterminado

ArgoCD crea un proyecto predeterminado que permite todas las fuentes, destinos y tipos de recursos. Se puede restringir, pero no eliminar.

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
- Equipos pequeños sin requisitos de multi-tenancy

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
  sourceRepos: []
  destinations: []
  sourceNamespaces: []
  clusterResourceWhitelist: []
  namespaceResourceBlacklist:
  - group: '*'
    kind: '*'
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
  clusterResourceWhitelist: []
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
    - p, proj:team-frontend:developer, applications, action/apps/Deployment/restart, team-frontend/*, allow
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
  - namespace: prod-*
    server: https://production.k8s.local
  - namespace: prod-*
    server: https://production-dr.k8s.local
  clusterResourceWhitelist: []
  namespaceResourceBlacklist:
  - group: ''
    kind: ResourceQuota
  - group: ''
    kind: LimitRange
  syncWindows:
  - kind: allow
    schedule: 0 9 * * 1-5
    duration: 8h
    applications:
    - '*'
    manualSync: true
    timeZone: Asia/Seoul
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

### Proyecto de infraestructura de la plataforma

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
  - https://grafana-community.github.io/helm-charts
  - https://charts.jetstack.io
  - docker.io/envoyproxy
  destinations:
  - namespace: kube-system
    server: https://dev-cluster.example.com
  - namespace: kube-system
    server: https://staging-cluster.example.com
  - namespace: kube-system
    server: https://prod-cluster.example.com
  - namespace: monitoring
    server: https://dev-cluster.example.com
  - namespace: monitoring
    server: https://staging-cluster.example.com
  - namespace: monitoring
    server: https://prod-cluster.example.com
  - namespace: logging
    server: https://dev-cluster.example.com
  - namespace: logging
    server: https://staging-cluster.example.com
  - namespace: logging
    server: https://prod-cluster.example.com
  - namespace: envoy-gateway-system
    server: https://dev-cluster.example.com
  - namespace: envoy-gateway-system
    server: https://staging-cluster.example.com
  - namespace: envoy-gateway-system
    server: https://prod-cluster.example.com
  - namespace: cert-manager
    server: https://dev-cluster.example.com
  - namespace: cert-manager
    server: https://staging-cluster.example.com
  - namespace: cert-manager
    server: https://prod-cluster.example.com
  clusterResourceWhitelist:
  - group: '*'
    kind: '*'
  roles:
  - name: platform-admin
    description: Platform team admin
    policies:
    - p, proj:platform:platform-admin, applications, *, platform/*, allow
    - p, proj:platform:platform-admin, clusters, *, platform/*, allow
    - p, proj:platform:platform-admin, repositories, *, platform/*, allow
    groups:
    - myorg:platform-team
```

### Interpretación del ámbito y verificación

- Un destino de AppProject coincide con `(server OR registered name) AND namespace`; especificar ambos identificadores de clúster no agrega una restricción AND. Estos ejemplos usan solo server. El destino de una Application requiere, en cambio, elegir server o name.
- ResourceQuota y LimitRange tienen ámbito de namespace; clusterResourceBlacklist no puede bloquearlos. Use namespaceResourceBlacklist para la ruta de despliegue de Argo CD.
- Omitir namespaceResourceWhitelist permite tipos con ámbito de namespace de forma predeterminada; las listas explícitas de permitidos/denegados se evalúan conjuntamente. Los tipos con ámbito de clúster requieren una lista de permitidos. Argo CD 3.5.4 también admite patrones de nombre en listas de recursos de clúster.
- Si delega la administración de Namespace, restrinja también su nombre (group:'', kind:Namespace, name:team-a-*). Esto aún permite cambios de etiquetas de Namespace; el aprovisionamiento previo y los controles de admisión son más seguros para los límites de tenants.
- manualSync permite excepciones manuales fuera de una ventana de autorización; no deshabilita la sincronización automatizada ni limita la excepción a un rol de guardia. Revise las ventanas de denegación superpuestas y las zonas horarias explícitas en el capítulo de sincronización.
- Mueva las Applications existentes a proyectos explícitos y verifique el acceso antes de restringir default.

## Configuración de RBAC

ArgoCD RBAC se configura en el ConfigMap `argocd-rbac-cm`.

### Sintaxis de la política RBAC

```
p, <subject>, <resource>, <action>, <object>, <effect>
g, <subject>, <role>
```

| Campo | Descripción |
|-------|-------------|
| `subject` | Usuario, grupo o rol |
| `resource` | applications, clusters, repositories, etc. |
| `action` | get, create, update, delete, sync, etc. |
| `object` | Identificador de recurso (project/app o *) |
| `effect` | allow o deny |

### Roles integrados

| Rol | Descripción |
|------|-------------|
| `role:readonly` | Acceso de solo lectura a todos los recursos |
| `role:admin` | Acceso completo a todos los recursos |

### Configuración completa de RBAC

Este ejemplo no concede acceso implícito a las aplicaciones y asigna permisos explícitos a grupos. Los desarrolladores están limitados a team-frontend. Deje role:authenticated sin entradas de política. Los permisos concedidos por la política predeterminada no se pueden eliminar mediante una denegación de usuario; establecer role:readonly como predeterminado expone lecturas entre proyectos. No copie ni redefina reglas de roles integrados en policy.csv.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-rbac-cm
  namespace: argocd
  labels:
    app.kubernetes.io/part-of: argocd
data:
  policy.default: role:authenticated
  policy.matchMode: glob
  scopes: '[groups]'
  policy.csv: |
    # Built-in role:admin and role:readonly are already provided by Argo CD.
    p, role:developer, applications, get, team-frontend/*, allow
    p, role:developer, applications, sync, team-frontend/*, allow
    p, role:developer, applications, action/apps/Deployment/restart, team-frontend/*, allow
    p, role:developer, logs, get, team-frontend/*, allow
    p, role:viewer, applications, get, team-frontend/*, allow
    p, role:frontend-admin, applications, *, team-frontend/*, allow
    p, role:frontend-admin, logs, get, team-frontend/*, allow
    p, role:backend-admin, applications, *, team-b/*, allow
    p, role:backend-admin, logs, get, team-b/*, allow
    p, role:sre, applications, get, production/*, allow
    p, role:sre, applications, sync, production/*, allow
    p, role:sre, applications, action/apps/Deployment/restart, production/*, allow
    p, role:sre, logs, get, production/*, allow
    p, role:sre, exec, create, production/*, allow
    p, role:security-auditor, applications, get, */*, allow
    p, role:security-auditor, projects, get, *, allow
    p, role:security-auditor, repositories, get, *, allow
    g, platform-team, role:admin
    g, developers, role:developer
    g, frontend-team, role:frontend-admin
    g, backend-team, role:backend-admin
    g, viewers, role:viewer
    g, sre-team, role:sre
    g, security-team, role:security-auditor
    p, role:developer, projects, get, team-frontend, allow
    p, role:viewer, projects, get, team-frontend, allow
    p, role:frontend-admin, projects, get, team-frontend, allow
    p, role:backend-admin, projects, get, team-b, allow
    p, role:sre, projects, get, production, allow
```

Combine fragmentos de políticas adicionales en los datos existentes del ConfigMap mediante Kustomize/Helm. Argo CD agrega las claves policy.example-N.csv a policy.csv. No aplique cada fragmento como un reemplazo de todo el ConfigMap ni acumule ejemplos de autorización amplios no relacionados.

El RBAC de la API de Argo CD es independiente del Kubernetes RBAC. El objeto project/app no identifica un namespace de destino; las Applications fuera del namespace del plano de control también usan project/application-namespace/app. La coincidencia glob no trata la barra inclinada como separador, así que incluya rutas completas de recurso-acción.

Con el valor predeterminado de 3.x, los permisos de actualización/eliminación de Application no conceden automáticamente la misma operación sobre los recursos secundarios de Kubernetes. Use `update/<group>/<kind>/<namespace>/<name>` o `delete/...` para esas operaciones, teniendo en cuenta `server.rbac.disableApplicationFineGrainedRBACInheritance`.

sync puede crear, actualizar y eliminar mediante prune los recursos desplegados. Denegar la eliminación de Application no evita la eliminación mediante sync/prune. La API de rollback también verifica sync; no existe un permiso independiente action/rollback ni uno exclusivo para rollback. override permite el reemplazo de fuentes, como manifests locales, no solo force sync. application.sync.requireOverridePrivilegeForRevisionSync puede requerir override cuando se proporciona una revisión.

### Permisos específicos de recursos

```yaml
policy.example-1.csv: |
  # Applications - fine-grained permissions
  p, role:deployer, applications, get, production/*, allow
  p, role:deployer, applications, sync, production/*, allow
  p, role:deployer, applications, update, production/*, deny
  p, role:deployer, applications, delete, production/*, deny

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
  p, role:debugger, exec, create, production/*, allow
  p, role:debugger, applications, get, production/*, allow
```

### Acciones específicas de Application

```yaml
policy.example-2.csv: |
  # Sync-only role (for CI/CD)
  p, role:sync-only, applications, get, production/*, allow
  p, role:sync-only, applications, sync, production/*, allow

  # Explicit Deployment restart resource action
  p, role:operator, applications, action/apps/Deployment/restart, production/*, allow

  # Rollback API requires sync; update is for changing the Application
  p, role:operator, applications, sync, production/*, allow
  p, role:operator, applications, get, production/*, allow
```

## Patrones de multi-tenancy

### Un namespace por equipo

![El equipo A, el equipo B y el equipo de plataforma reciben roles de aplicación en un AppProject de ArgoCD cuyos destinos restringen los despliegues de Argo CD a sus propios namespaces, team-a, team-b y los namespaces compartidos de monitoring y logging.](../../.gitbook/assets/en-gitops-argocd-06-projects-rbac-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-argocd-06-projects-rbac-0.html)

Implementación:

```yaml
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
  clusterResourceWhitelist: []
  roles:
  - name: admin
    policies:
    - p, proj:team-a:admin, applications, *, team-a/*, allow
    groups:
    - team-a-admins
---
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
  - https://github.com/myorg/dev-*
  destinations:
  - namespace: dev-*
    server: https://dev.k8s.local
  clusterResourceWhitelist: []
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
  - namespace: prod-*
    server: https://prod.k8s.local
  clusterResourceWhitelist: []
  syncWindows:
  - kind: deny
    schedule: 0 0 * * 6
    duration: 48h
    applications:
    - '*'
    timeZone: Asia/Seoul
  namespaceResourceBlacklist:
  - group: ''
    kind: ResourceQuota
  - group: ''
    kind: LimitRange
```

<span id="jwt-tokens-for-cicd"></span>

## Tokens JWT para CI/CD

Cree tokens con ámbito de proyecto para la automatización.

### Crear token JWT

Un operador autorizado para actualizar el proyecto emite/revoca tokens; el propio rol de CI solo tiene get/sync. Prepare primero my-project, su rol ci-deployer y la Application my-app. Rote antes de la expiración; el valor predeterminado de la CLI no tiene expiración.

```bash
set -euo pipefail
umask 077
# Run as an operator authorized to update my-project.
argocd proj role create-token my-project ci-deployer \
  --expires-in 24h --token-only > ./argocd-ci.token
# Store this file's value in the approved CI secret store; do not commit or print it.
```

Use `--id UNIQUE_ID` cuando se necesite un identificador explícito; --token-id no es una opción de 3.5.4. expires-in acepta una duración como 24h. El valor del token firmado se devuelve en la emisión, no se almacena para recuperarlo más adelante.

### Usar token en CI/CD

Combine este rol en el AppProject my-project existente; no crea por sí solo permisos de fuente/destino ni una Application:

```yaml
spec:
  roles:
  - name: ci-deployer
    policies:
    - p, proj:my-project:ci-deployer, applications, get, my-project/*, allow
    - p, proj:my-project:ci-deployer, applications, sync, my-project/*, allow
```

El flujo de trabajo sincroniza la revisión declarada por la Application, en lugar de forzar el SHA del flujo de trabajo. Fije targetRevision en Git cuando se requieran revisiones inmutables. Revise la configuración de override del servidor antes de usar --revision. Configure por separado las reglas de aprobación/protección del Environment de producción.

```yaml
name: Sync declared Argo CD application
'on':
  push:
    branches:
    - main
  workflow_dispatch: {}
permissions: {}
concurrency:
  group: argocd-my-project-my-app
  cancel-in-progress: false
jobs:
  sync:
    runs-on: ubuntu-24.04
    timeout-minutes: 15
    environment: production
    steps:
    - name: Install verified CLI
      shell: bash
      run: |
        set -euo pipefail
        ARGOCD_VERSION=v3.5.4
        case "$(uname -m)" in
          x86_64) cli_arch=amd64 ;;
          aarch64|arm64) cli_arch=arm64 ;;
          *) echo "Unsupported runner architecture" >&2; exit 1 ;;
        esac
        cli_asset="argocd-linux-${cli_arch}"
        cli_dir="$(mktemp -d)"
        trap 'rm -rf "$cli_dir"' EXIT
        cli_base="https://github.com/argoproj/argo-cd/releases/download/${ARGOCD_VERSION}"
        curl --fail --location --retry 3 "$cli_base/$cli_asset" -o "$cli_dir/$cli_asset"
        curl --fail --location --retry 3 "$cli_base/cli_checksums.txt" -o "$cli_dir/checksums.txt"
        awk -v artifact="$cli_asset" '$2 == artifact { print }' "$cli_dir/checksums.txt" > "$cli_dir/selected.sha256"
        test -s "$cli_dir/selected.sha256"
        (cd "$cli_dir" && sha256sum --check selected.sha256)
        install -m 0755 "$cli_dir/$cli_asset" "$RUNNER_TEMP/argocd"
    - name: Sync and wait
      shell: bash
      env:
        ARGOCD_SERVER: ${{ secrets.ARGOCD_SERVER }}
        ARGOCD_AUTH_TOKEN: ${{ secrets.ARGOCD_TOKEN }}
      run: |
        set -euo pipefail
        "$RUNNER_TEMP/argocd" app sync my-app --server "$ARGOCD_SERVER" --grpc-web --timeout 300
        "$RUNNER_TEMP/argocd" app wait my-app --server "$ARGOCD_SERVER" --grpc-web --sync --health --timeout 300
```

### Gestión de tokens

Los metadatos del token se almacenan/normalizan en los registros de rol/status del proyecto. Declarar manualmente iat/exp/id no emite un token firmado. Los cambios en la política de rol afectan a los tokens ya emitidos. Use credenciales de operador para revocar un token por su entero ISSUED AT, no por su etiqueta ID:

```bash
argocd proj role list-tokens my-project ci-deployer --unixtime

# Select one token's ISSUED AT value from the list, using operator credentials.
: "${SELECTED_ISSUED_AT:?Set the selected integer ISSUED AT value}"
argocd proj role delete-token my-project ci-deployer "$SELECTED_ISSUED_AT"
```

### Almacenamiento de tokens para CI dentro del clúster

Un Secret de Kubernetes puede almacenar un token emitido previamente para un trabajo de CI. No es un emisor de tokens de Argo CD y no existe un tipo especial de Secret argocd-token. Use el namespace del trabajo de CI y una entrada de archivo segura, por ejemplo:

```bash
kubectl create secret generic argocd-ci-token -n ci \
  --from-file=token=./argocd-ci.token
```

Aprovisione primero el namespace ci y el RBAC del trabajo. Monte/lea el Secret solo en el trabajo de CI autorizado y rote su valor antes de la expiración del token. No coloque el valor del token en Git.

## Monitoreo de recursos huérfanos

Detecte recursos en namespaces de destino que no administra ArgoCD.

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
    - group: ''
      kind: ConfigMap
      name: kube-root-ca.crt
    - group: ''
      kind: ServiceAccount
      name: default
    - group: ''
      kind: Secret
      name: default-token-*
  clusterResourceWhitelist: []
```

### Ver recursos huérfanos

```bash
argocd app resources my-app --orphaned

: "${ARGOCD_AUTH_TOKEN:?Provide an authorized token securely}"
curl --fail --silent --show-error --max-time 30 \
  -H "Authorization: Bearer $ARGOCD_AUTH_TOKEN" \
  https://argocd.example.com/api/v1/applications/my-app/resource-tree \
  | jq '.orphanedNodes'
```

Las advertencias son opcionales: warn:false aún permite ver candidatos huérfanos. Los recursos denegados por el proyecto y los objetos predeterminados integrados tienen excepciones; limite los namespaces monitoreados para evitar análisis grandes de kube-system.

### Revisar antes de limpiar

El monitoreo de huérfanos informa recursos de nivel superior con ámbito de namespace que no son rastreados por una Application de Argo CD. Aun así, pueden pertenecer a otro operador o administrarse intencionalmente fuera de GitOps. El selector de etiquetas `managed-by!=argocd` también coincide con recursos sin dicha etiqueta y no implementa el seguimiento de Argo CD. No convierta ese selector en un trabajo de eliminación PostSync.

Inspeccione la lista de huérfanos, las referencias de propietario, los metadatos reales de seguimiento de Argo CD y el controlador propietario antes de decidir si un recurso está obsoleto. Excluya recursos legítimos con reglas de ignorar del monitoreo de huérfanos de alcance limitado. Cualquier eliminación debe usar una lista de recursos revisada explícitamente y el procedimiento adecuado de copia de seguridad/recuperación; los ejemplos de aquí solo informan candidatos.

## Validación de políticas

Guarde el ejemplo base de ConfigMap como argocd-rbac-cm.yaml. La CLI también inicializa un kubeconfig válido, pero las comprobaciones de archivos de políticas no modifican configuraciones activas. Compruebe por separado los roles dinámicos de AppProject, las reclamaciones SSO reales y la admisión de Kubernetes.

```bash
argocd admin settings rbac validate --policy-file ./argocd-rbac-cm.yaml
argocd admin settings rbac can developers sync applications team-frontend/my-app \
  --policy-file ./argocd-rbac-cm.yaml
# Expected: No (exit 1)
argocd admin settings rbac can developers get applications team-b/my-app \
  --policy-file ./argocd-rbac-cm.yaml
```

validate puede advertir que el role:admin integrado está ausente del CSV del usuario. can incluye la política integrada de forma predeterminada; no duplique roles integrados para silenciar la advertencia. Compruebe las colisiones de usuario local/grupo SSO y las reclamaciones de grupo reales. Una política exec no habilita por sí misma la terminal: compruebe también exec.enabled y los permisos subyacentes de Kubernetes.

## Referencias

- [Argo CD 3.5.4 RBAC](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/operator-manual/rbac.md)
- [Coincidencia y validación de proyectos](https://github.com/argoproj/argo-cd/blob/v3.5.4/pkg/apis/application/v1alpha1/app_project_types.go)
- [Integridad de la fuente](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/user-guide/source-integrity-git-gpg.md)
- [CLI de tokens de proyecto](https://github.com/argoproj/argo-cd/blob/v3.5.4/cmd/argocd/commands/project_role.go)

## Cuestionario

Para comprobar lo que ha aprendido, pruebe el [cuestionario de proyectos y RBAC de ArgoCD](../../quizzes/gitops/argocd/06-projects-rbac-quiz.md).
