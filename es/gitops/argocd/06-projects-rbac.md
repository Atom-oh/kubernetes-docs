# Proyectos y RBAC de Argo CD

> **Revisado con respecto a**: Argo CD 3.5.2; actualizado al parche 3.5.5 tras revisar las notas de la versión (los ejemplos no se volvieron a ejecutar)
> **Última actualización**: 16 de octubre de 2026

## Tabla de contenido
- [Descripción general de AppProject](#appproject-overview)
- [Proyecto predeterminado](#default-project)
- [Proyectos personalizados](#custom-projects)
- [Configuración de RBAC](#rbac-configuration)
- [Patrones multiinquilino](#multi-tenancy-patterns)
- [Tokens JWT para CI/CD](#jwt-tokens-for-cicd)
- [Supervisión de recursos huérfanos](#orphaned-resource-monitoring)

## Descripción general de AppProject {#appproject-overview}

Los AppProject agrupan Applications de forma lógica y definen controles de acceso para determinar qué recursos pueden desplegarse, dónde y quién puede administrarlos.

Un AppProject restringe los repositorios de origen, los destinos, los tipos de recursos renderizados y los permisos de la API de Argo CD. No sustituye RBAC de Kubernetes, Pod Security Admission, NetworkPolicy ni ResourceQuota. Denegar el tipo de recurso Pod no impide que un Deployment cree Pods privilegiados.

Usa URL reales de repositorios, grupos, clústeres registrados y espacios de nombres. Los administradores de la plataforma crean de antemano los espacios de nombres de las aplicaciones y son responsables de sus políticas de seguridad y cuotas. Los proyectos de equipo y entorno que aparecen a continuación no permiten recursos con ámbito de clúster; el proyecto de plataforma independiente es para administradores de confianza. Los ejemplos completos de proyectos son alternativas independientes, incluso cuando comparten un nombre.

### Capacidades principales

| Característica | Descripción |
|---------|-------------|
| Restricciones de origen | Limita qué repositorios Git se pueden usar |
| Restricciones de destino | Limita los clústeres y espacios de nombres de destino |
| Lista de permitidos/denegados de recursos | Controla qué recursos de Kubernetes se pueden crear |
| Definiciones de roles | Define roles RBAC específicos del proyecto |
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

## Proyecto predeterminado {#default-project}

Argo CD crea un proyecto predeterminado que permite todos los orígenes, destinos y tipos de recursos. Se puede restringir, pero no eliminar.

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
- Equipos pequeños sin requisitos multiinquilino

### Restricción del proyecto predeterminado

En producción, restringe el proyecto predeterminado:

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

## Proyectos personalizados {#custom-projects}

### Proyecto por equipo

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

### Proyecto por entorno

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

- Un destino de AppProject coincide con `(server OR registered name) AND namespace`; indicar ambos identificadores de clúster no añade una condición AND. Estos ejemplos usan solo server. En cambio, el destino de una Application requiere elegir server o name.
- ResourceQuota y LimitRange tienen ámbito de espacio de nombres; clusterResourceBlacklist no puede bloquearlos. Usa namespaceResourceBlacklist para la ruta de despliegue de Argo CD.
- Si se omite namespaceResourceWhitelist, se permiten de forma predeterminada los tipos con ámbito de espacio de nombres; las listas explícitas de permitidos y denegados se evalúan conjuntamente. Los tipos con ámbito de clúster requieren una lista de permitidos. Argo CD 3.5.4 también admite patrones de nombre en las listas de recursos de clúster.
- Si delegas la gestión de Namespace, restringe también su nombre (group:'', kind:Namespace, name:team-a-*). Aun así se pueden cambiar las etiquetas de Namespace; el aprovisionamiento previo y los controles de admisión ofrecen límites multiinquilino más seguros.
- manualSync permite excepciones manuales fuera de una ventana permitida; no deshabilita la sincronización automática ni limita la excepción a un rol de guardia. Revisa las ventanas de denegación superpuestas y las zonas horarias explícitas en el capítulo de sincronización.
- Migra las Applications existentes a proyectos explícitos y verifica el acceso antes de restringir el proyecto predeterminado.

## Configuración de RBAC {#rbac-configuration}

RBAC de Argo CD se configura en el ConfigMap `argocd-rbac-cm`.

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
| `object` | Identificador del recurso (project/app o *) |
| `effect` | allow o deny |

### Roles integrados

| Rol | Descripción |
|------|-------------|
| `role:readonly` | Acceso de solo lectura a todos los recursos |
| `role:admin` | Acceso completo a todos los recursos |

### Configuración completa de RBAC

Este ejemplo no concede acceso implícito a las aplicaciones y asigna permisos explícitos a los grupos. El acceso de los desarrolladores se limita a team-frontend. Deja role:authenticated sin entradas de política. Los permisos concedidos por la política predeterminada no se pueden revocar mediante una denegación del usuario; usar role:readonly como rol predeterminado expone lecturas entre proyectos. No copies ni redefinas en policy.csv las reglas de los roles integrados.

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

Combina fragmentos adicionales de política con los datos del ConfigMap existente mediante Kustomize o Helm. Argo CD agrega las claves policy.example-N.csv a policy.csv. No apliques cada fragmento como sustitución de todo el ConfigMap ni acumules ejemplos amplios de permisos allow que no estén relacionados.

El RBAC de la API de Argo CD es independiente del RBAC de Kubernetes. El objeto project/app no identifica un espacio de nombres de destino; las Applications que están fuera del espacio de nombres del plano de control también usan project/application-namespace/app. La coincidencia glob no trata la barra como separador, por lo que debes incluir las rutas completas de recurso y acción.

Con el valor predeterminado de 3.x, los permisos de actualización y eliminación de una Application no conceden automáticamente las mismas operaciones sobre sus recursos secundarios de Kubernetes. Usa `update/<group>/<kind>/<namespace>/<name>` o `delete/...` para esas operaciones y ten en cuenta `server.rbac.disableApplicationFineGrainedRBACInheritance`.

sync puede crear, actualizar y eliminar mediante prune los recursos desplegados. Denegar la eliminación de una Application no impide que se eliminen recursos mediante sync/prune. La API de rollback también comprueba sync; no existe un permiso independiente action/rollback ni otro exclusivo para rollback. override permite reemplazar el origen, por ejemplo con manifiestos locales, no se limita a forzar una sincronización. application.sync.requireOverridePrivilegeForRevisionSync puede exigir override cuando se proporciona una revisión.

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

## Patrones multiinquilino {#multi-tenancy-patterns}

### Un espacio de nombres por equipo

![Los equipos A, B y de plataforma reciben roles de aplicación en un AppProject de Argo CD cuyos destinos limitan los despliegues a sus propios espacios de nombres, team-a y team-b, y a los espacios compartidos de monitorización y registro.](../../.gitbook/assets/en-gitops-argocd-06-projects-rbac-0.png)

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

Crea tokens con ámbito de proyecto para la automatización.

### Crear un token JWT

Un operador autorizado para actualizar el proyecto emite y revoca los tokens; el rol de CI solo tiene get/sync. Prepara primero my-project, su rol ci-deployer y la Application my-app. Rota el token antes de que venza; de forma predeterminada, la CLI no establece una fecha de expiración.

```bash
set -euo pipefail
umask 077
# Run as an operator authorized to update my-project.
argocd proj role create-token my-project ci-deployer \
  --expires-in 24h --token-only > ./argocd-ci.token
# Store this file's value in the approved CI secret store; do not commit or print it.
```

Usa `--id UNIQUE_ID` cuando necesites un identificador explícito; --token-id no es una opción de la versión 3.5.4. expires-in acepta una duración, como 24h. El valor del token firmado se devuelve al emitirlo y no se almacena para recuperarlo después.

### Usar el token en CI/CD

Integra este rol en el AppProject my-project existente; por sí solo no crea permisos de origen o destino ni una Application:

```yaml
spec:
  roles:
  - name: ci-deployer
    policies:
    - p, proj:my-project:ci-deployer, applications, get, my-project/*, allow
    - p, proj:my-project:ci-deployer, applications, sync, my-project/*, allow
```

El workflow sincroniza la revisión declarada por la Application, en lugar de forzar el SHA del propio workflow. Fija targetRevision en Git cuando necesites revisiones inmutables. Revisa la opción override del servidor antes de usar --revision. Configura aparte las reglas de aprobación y protección del entorno de producción.

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
        ARGOCD_VERSION=v3.5.5
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

Los metadatos del token se guardan y normalizan en los registros de roles y status del proyecto. Declarar manualmente iat/exp/id no emite un token firmado. Los cambios en la política del rol afectan a los tokens que ya se emitieron. Usa credenciales de operador para revocar un token por el valor entero del campo ISSUED AT, no por la etiqueta ID:

```bash
argocd proj role list-tokens my-project ci-deployer --unixtime

# Select one token's ISSUED AT value from the list, using operator credentials.
: "${SELECTED_ISSUED_AT:?Set the selected integer ISSUED AT value}"
argocd proj role delete-token my-project ci-deployer "$SELECTED_ISSUED_AT"
```

### Guardar tokens para CI dentro del clúster

Un Secret de Kubernetes puede guardar un token emitido previamente para un trabajo de CI. No emite tokens de Argo CD y no existe un tipo especial de Secret argocd-token. Usa el espacio de nombres del trabajo de CI y una entrada segura desde archivo, por ejemplo:

```bash
kubectl create secret generic argocd-ci-token -n ci \
  --from-file=token=./argocd-ci.token
```

Aprovisiona primero el espacio de nombres ci y el RBAC del trabajo. Monta y lee el Secret solo desde el trabajo de CI autorizado, y rota su valor antes de que venza el token. No pongas el valor del token en Git.

## Supervisión de recursos huérfanos {#orphaned-resource-monitoring}

Detecta recursos en espacios de nombres de destino que Argo CD no gestiona.

### Activar la supervisión de recursos huérfanos

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

Las advertencias son opcionales: warn:false sigue permitiendo ver candidatos huérfanos. Los recursos denegados por el proyecto y los objetos integrados por defecto tienen excepciones; limita los espacios de nombres supervisados para evitar un análisis excesivo de kube-system.

### Revisar antes de limpiar

La supervisión de huérfanos informa sobre recursos de nivel superior con ámbito de espacio de nombres que no rastrea ninguna Application de Argo CD. Aun así, pueden pertenecer a otro operador o gestionarse intencionalmente fuera de GitOps. El selector `managed-by!=argocd` también coincide con recursos que no tienen esa etiqueta y no aplica el seguimiento de Argo CD. No conviertas ese selector en un trabajo PostSync que elimine recursos.

Antes de decidir si un recurso está obsoleto, inspecciona la lista de huérfanos, las referencias de propietario, los metadatos reales de seguimiento de Argo CD y el controlador responsable. Excluye los recursos legítimos mediante reglas de omisión de alcance limitado para la supervisión de huérfanos. Cualquier eliminación debe usar una lista de recursos revisada explícitamente y el procedimiento de copia de seguridad y recuperación adecuado; los ejemplos de aquí solo informan de candidatos.

## Validación de políticas

Guarda el ejemplo base del ConfigMap como argocd-rbac-cm.yaml. La CLI también inicializa un kubeconfig válido, pero las comprobaciones de los archivos de política no modifican la configuración activa. Comprueba por separado los roles dinámicos de AppProject, las claims de SSO reales y la admisión de Kubernetes.

```bash
argocd admin settings rbac validate --policy-file ./argocd-rbac-cm.yaml
argocd admin settings rbac can developers sync applications team-frontend/my-app \
  --policy-file ./argocd-rbac-cm.yaml
# Expected: No (exit 1)
argocd admin settings rbac can developers get applications team-b/my-app \
  --policy-file ./argocd-rbac-cm.yaml
```

validate puede advertir que role:admin, un rol integrado, no aparece en el CSV del usuario. can incluye la política integrada de forma predeterminada; no dupliques roles integrados para silenciar esa advertencia. Comprueba colisiones entre usuarios locales y grupos de SSO, así como las claims reales de grupo. Una política exec no habilita por sí sola la terminal: comprueba también exec.enabled y los permisos subyacentes de Kubernetes.

## Referencias

- [RBAC de Argo CD 3.5.4](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/operator-manual/rbac.md)
- [Coincidencia y validación de proyectos](https://github.com/argoproj/argo-cd/blob/v3.5.4/pkg/apis/application/v1alpha1/app_project_types.go)
- [Integridad del origen](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/user-guide/source-integrity-git-gpg.md)
- [CLI de tokens de proyecto](https://github.com/argoproj/argo-cd/blob/v3.5.4/cmd/argocd/commands/project_role.go)

## Cuestionario

Para comprobar lo que aprendiste, prueba el [cuestionario de proyectos y RBAC de Argo CD](../../quizzes/gitops/argocd/06-projects-rbac-quiz.md).
