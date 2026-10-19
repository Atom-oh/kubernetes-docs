# Despliegue de Argo CD en varios clusters e IAM Identity Center

> **Versiones de referencia de la revisión**: Argo CD 3.5.5 / chart 10.10.5, Terraform 1.15.7 / Helm Provider 3.3.0, ESO 2.12.0\
> **Última revisión**: 16 de octubre de 2026. Se comprobaron localmente los esquemas, el renderizado y los dobles de prueba. No se realizó una instalación real en EKS, un inicio de sesión SSO ni una lectura de Secrets Manager.

< [Anterior: Pipelines de CI](03-ci-pipelines.md) | [Índice](README.md) | [Siguiente: Automatización GitOps](05-gitops-automation.md) >

Este capítulo utiliza Argo CD en un cluster EKS de administración (hub) para gestionar dos clusters de cargas de trabajo (spokes). CI genera digests de imágenes aprobados; los cambios revisados en Git seleccionan el digest que se desplegará. La administración centralizada no sustituye la autenticación, la autorización ni la configuración de red de cada cluster.

## Arquitectura con varios clusters

| Ubicación | Responsabilidad | Acceso necesario |
|---|---|---|
| Application Controller del hub | Comparar y sincronizar el estado deseado | API EKS de destino y recursos Kubernetes permitidos |
| Server/ApplicationSet del hub | Solicitudes de usuarios y operaciones relacionadas con clusters | Credenciales necesarias para esas funciones y Secrets del hub |
| Repo Server | Renderizar fuentes de Git/Helm | Repositorios aprobados y credenciales válidas de los repositorios |
| Spoke | Ejecutar aplicaciones y NodePools | Access Entry de EKS y RBAC del principal IAM de destino |
| ESO | Sincronizar valores externos con Secrets de Kubernetes | Acceso del rol real del controlador a los secretos indicados |

Blue y green identifican clusters. Los NodePools de ejemplo se restringen a distintas AZ, mientras que los planos de control EKS son regionales. Un fallo del hub no tiene por qué detener inmediatamente los Pods existentes en los spokes, pero puede detener el despliegue y la reconciliación. Unas credenciales comprometidas del hub pueden afectar a varios spokes. El historial de Git por sí solo no audita todos los cambios manuales, inicios de sesión u operaciones de bases de datos.

### Requisitos de los destinos

1. Configure Pod Identity o IRSA compatibles para las cuentas de Application Controller y Server/ApplicationSet del hub que necesitan autenticarse en los destinos. El acceso de Repo Server a Git/ECR es independiente.
2. Permita que el rol de administración asuma **los ARN exactos de los roles de destino** y restrinja la relación de confianza de cada rol de destino al rol de administración previsto.
3. Compruebe el modo de autenticación EKS del destino y cree la Access Entry del rol. Separe las políticas de acceso/RBAC para los recursos necesarios del namespace `demo-app` de la administración de NodePools a nivel de cluster. En este ejemplo, cree el namespace previamente.
4. Verifique DNS, rutas y acceso mediante grupos de seguridad desde el hub a los endpoints API privados de destino. Los permisos IAM no proporcionan conectividad de red.

Utilice las guías revisadas de [instalación de Argo CD](../gitops/argocd/01-installation.md) y [gestión de acceso a EKS](../eks/02-eks-cluster-creation-part3.md) para los roles y las Access Entries. No reemplace el valor completo de `aws-auth.mapRoles` ni use `system:masters` como opción predeterminada.

La ruta `awsAuthConfig.roleARN` de Argo CD 3.5.5 asume un rol, pero no expone un campo ExternalId. Una condición de confianza que exija un ExternalId que esta ruta no envía impide la autenticación. Si esa condición es necesaria, diseñe una ruta de autenticación independiente y compatible.

### Registro declarativo con endpoints reales

Ejecute este script por separado para cada destino. Cambiar `CLUSTER_COLOR`, el nombre del cluster y el rol crea Secrets distintos sin cambiar el contexto predeterminado de kubeconfig. El acceso a namespaces se limita a `demo-app`; se habilita el acceso a recursos del cluster para los NodePools. Esto no concede los permisos RBAC correspondientes en el destino.

```bash
# fixtures/register-cluster.sh
#!/usr/bin/env bash
set -euo pipefail
: "${ARGOCD_CONTEXT:?Set the hub kubeconfig context}"
: "${TARGET_EKS_NAME:?Set the actual target EKS cluster name}"
: "${TARGET_AWS_REGION:?Set the target AWS region}"
: "${TARGET_ROLE_ARN:?Set the pre-authorized target role ARN}"
: "${CLUSTER_COLOR:?Set blue or green}"
case "$CLUSTER_COLOR" in blue|green) ;; *) exit 2 ;; esac
[[ "$TARGET_ROLE_ARN" =~ ^arn:aws:iam::[0-9]{12}:role/.+ ]] || exit 2
umask 077
REVIEW_TMP="$(mktemp -d)"
trap 'rm -rf -- "$REVIEW_TMP"' EXIT
aws eks describe-cluster --name "$TARGET_EKS_NAME" --region "$TARGET_AWS_REGION" \
  --query 'cluster.{name:name,server:endpoint,ca:certificateAuthority.data}' \
  --output json > "$REVIEW_TMP/cluster.json"
jq -e '(.name | type == "string" and length > 0)
  and (.server | type == "string" and startswith("https://"))
  and (.ca | type == "string" and length > 0)' "$REVIEW_TMP/cluster.json" >/dev/null
jq --arg role "$TARGET_ROLE_ARN" --arg color "$CLUSTER_COLOR" '{
  apiVersion:"v1",kind:"Secret",
  metadata:{name:("workload-"+$color),namespace:"argocd",labels:{
    "argocd.argoproj.io/secret-type":"cluster",
    "environment":"production","cluster-color":$color,"gitops-target":"true"
  }},
  type:"Opaque",
  stringData:{
    name:("workload-"+$color),server:.server,namespaces:"demo-app",
    clusterResources:"true",
    config:({
      awsAuthConfig:{clusterName:.name,roleARN:$role},
      tlsClientConfig:{insecure:false,caData:.ca}
    }|tojson)
  }
}' "$REVIEW_TMP/cluster.json" > "$REVIEW_TMP/secret.json"
kubectl --context "$ARGOCD_CONTEXT" apply -f "$REVIEW_TMP/secret.json"
```

El operador que descubre el cluster y el rol utilizado por los Pods del hub son identidades diferentes. No invente un nombre de host EKS ni un certificado. Para añadir namespaces, actualice conjuntamente el Secret del cluster, el AppProject y los permisos de destino. Revise la configuración de caché, como `resource.respectRBAC`, junto con el RBAC de destino para evitar observar recursos innecesariamente.

`argocd cluster add <kubeconfig-context>` es una alternativa que puede crear ServiceAccounts y RBAC en el destino; no es un comando de solo lectura. Use un inicio de sesión interactivo o SSO para la CLI, en lugar de pasar la contraseña como argumento.

## Instalación de Argo CD con Terraform

Este módulo raíz presupone un hub existente, permisos de instalación y AWS CLI en el entorno de ejecución. Helm Provider 3 utiliza la sintaxis de objeto `kubernetes = { ... }`. La autenticación exec obtiene un token EKS de corta duración sin guardar un token de un data source de autenticación EKS en el estado de Terraform. Si solo AWS Provider asume un rol, configure también su proceso independiente de AWS CLI exec para utilizar las credenciales previstas.

```hcl
# terraform/main.tf
terraform {
  required_version = ">= 1.10, < 2.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "= 6.69.1"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "= 3.3.0"
    }
  }
  backend "s3" {}
}

provider "aws" {
  region = var.aws_region
}

data "aws_eks_cluster" "hub" {
  name = var.management_cluster_name
}

provider "helm" {
  kubernetes = {
    host                   = data.aws_eks_cluster.hub.endpoint
    cluster_ca_certificate = base64decode(data.aws_eks_cluster.hub.certificate_authority[0].data)
    exec = {
      api_version = "client.authentication.k8s.io/v1beta1"
      command     = "aws"
      args        = ["eks", "get-token", "--cluster-name", var.management_cluster_name, "--region", var.aws_region]
    }
  }
}

resource "helm_release" "argocd" {
  name             = "argocd"
  namespace        = "argocd"
  create_namespace = true
  repository       = "https://argoproj.github.io/argo-helm"
  chart            = "argo-cd"
  version          = "10.10.5"
  timeout          = 900
  wait             = true
  values           = [file("${path.module}/argocd-values.yaml")]
}
```

```hcl
# terraform/variables.tf
variable "aws_region" {
  type    = string
  default = "ap-northeast-2"
}

variable "management_cluster_name" {
  type = string
  validation {
    condition     = can(regex("^[A-Za-z0-9][A-Za-z0-9_-]{0,99}$", var.management_cluster_name))
    error_message = "Use the actual EKS management cluster name."
  }
}
```

Configure un archivo independiente `backend.hcl` con el bucket específico de la cuenta y el entorno del [capítulo 01](01-infrastructure-setup.md), una clave de estado única, `encrypt = true` y `use_lockfile = true`. Ejecute `terraform init -backend-config=backend.hcl` y revise el plan. No copie una configuración obsoleta de bloqueo con DynamoDB ni la clave de estado de otro módulo raíz.

Guarde este `argocd-values.yaml` junto a los archivos Terraform. Reutiliza la configuración inicial de alta disponibilidad de la [guía de instalación revisada](../gitops/argocd/01-installation.md). Evite que otro recurso Terraform o un flujo de kubectl compita con Helm por el mismo ConfigMap.

```yaml
# fixtures/argocd-values.yaml
fullnameOverride: argocd
global:
  domain: argocd.example.com
configs:
  params:
    server.insecure: false
  cm:
    url: https://argocd.example.com
    users.anonymous.enabled: 'false'
    exec.enabled: 'false'
controller:
  replicas: 2
  resources:
    requests:
      cpu: 250m
      memory: 512Mi
    limits:
      cpu: '1'
      memory: 2Gi
  pdb:
    enabled: true
    minAvailable: 1
server:
  replicas: 2
  service:
    type: ClusterIP
  ingress:
    enabled: false
  resources:
    requests:
      cpu: 100m
      memory: 128Mi
    limits:
      cpu: 500m
      memory: 512Mi
  pdb:
    enabled: true
    minAvailable: 1
repoServer:
  replicas: 2
  resources:
    requests:
      cpu: 100m
      memory: 256Mi
    limits:
      cpu: '1'
      memory: 1Gi
  pdb:
    enabled: true
    minAvailable: 1
applicationSet:
  replicas: 2
  pdb:
    enabled: true
    minAvailable: 1
notifications:
  enabled: true
redis:
  enabled: false
redis-ha:
  enabled: true
  replicas: 3
  persistentVolume:
    enabled: false
  haproxy:
    enabled: true
    replicas: 3
```

La configuración inicial expone un ClusterIP HTTPS y deshabilita el ingress externo. Un SSO real requiere un dominio HTTPS accesible con rutas correctas. Si añade el ejemplo ALB de la guía de instalación, haga coincidir su backend HTTPS con `server.insecure=false`. Si cambia a HTTP, cambie juntos los protocolos del backend y de las comprobaciones de salud. Distinga las rutas de gRPC nativo y gRPC-Web.

Las réplicas de Application Controller implementan **particionamiento por clusters**, no un único líder activo con todas las demás réplicas en espera. ApplicationSet tiene su propia elección de líder. Server es stateless y no necesita sesiones persistentes por el simple hecho de tener varias réplicas. Mantenga Dex con su réplica única predeterminada para la configuración de almacenamiento incluida.

Redis es una caché reconstruible; la configuración principal reside en objetos Kubernetes. Redis HA no garantiza el funcionamiento ininterrumpido ante cualquier fallo. Diseñe conjuntamente las réplicas, PDB, ubicación de nodos y capacidad de reserva; los PDB no impiden fallos de AZ ni todas las terminaciones forzadas. Habilite ServiceMonitor solo cuando exista su CRD de Prometheus Operator.

## Gestión de NodePools con GitOps

Los NodePools son recursos personalizados de Kubernetes y pueden gestionarse con Argo CD. Esto no significa que Terraform no pueda gestionarlos. Elija un único responsable por recurso y migre su gestión de forma deliberada, en lugar de adoptar accidentalmente recursos integrados o gestionados por Terraform con el mismo nombre.

El ejemplo siguiente utiliza el NodeClass `default` existente de Auto Mode. Sus selectores de subred deben incluir la AZ deseada. Cree la estructura completa de archivos:

```text
nodepools/
  base/kustomization.yaml
  base/nodepool.yaml
  overlays/blue/kustomization.yaml
  overlays/green/kustomization.yaml
```

```yaml
# nodepools/base/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - nodepool.yaml
```

```yaml
# nodepools/base/nodepool.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: workloads
  annotations:
    argocd.argoproj.io/sync-options: Prune=confirm,Delete=confirm
spec:
  template:
    metadata:
      labels:
        workload-type: applications
    spec:
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      requirements:
        - key: kubernetes.io/arch
          operator: In
          values: [amd64, arm64]
        - key: karpenter.sh/capacity-type
          operator: In
          values: [on-demand]
        - key: node.kubernetes.io/instance-type
          operator: In
          values: [m7i.large, m7i.xlarge, m7g.large, m7g.xlarge]
  limits:
    cpu: "100"
    memory: 200Gi
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 10m
    budgets:
      - nodes: "10%"
```

```yaml
# nodepools/overlays/blue/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - ../../base
patches:
  - target:
      group: karpenter.sh
      version: v1
      kind: NodePool
      name: workloads
    patch: |
      - op: add
        path: /spec/template/metadata/labels/cluster-color
        value: blue
      - op: add
        path: /spec/template/spec/requirements/-
        value:
          key: topology.kubernetes.io/zone
          operator: In
          values: [ap-northeast-2a]
```

```yaml
# nodepools/overlays/green/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - ../../base
patches:
  - target:
      group: karpenter.sh
      version: v1
      kind: NodePool
      name: workloads
    patch: |
      - op: add
        path: /spec/template/metadata/labels/cluster-color
        value: green
      - op: add
        path: /spec/template/spec/requirements/-
        value:
          key: topology.kubernetes.io/zone
          operator: In
          values: [ap-northeast-2c]
```

Revise tanto `kustomize build nodepools/overlays/blue` como su equivalente green. Los requisitos estándar de tipos de instancia evitan mezclar las claves `karpenter.k8s.aws/*` de Karpenter autogestionado con Auto Mode. Haga coincidir los selectores, la arquitectura y los requisitos de ubicación de las cargas con los pools.

No copie campos de `EC2NodeClass` autogestionado, como `amiSelectorTerms`, `blockDeviceMappings` o `instanceStorePolicy`, en un `NodeClass` de Auto Mode. Las clases personalizadas de Auto Mode utilizan roles de nodo reales, selectores de subred/grupos de seguridad y campos compatibles, como `ephemeralStorage`; otro rol de nodo también necesita su Access Entry de nodos de Auto Mode. Diseñe por separado el almacenamiento persistente de las bases de datos y los discos efímeros. Consulte la [guía de NodePool/NodeClass](../eks-auto-mode/02-nodepool-configuration.md).

### Proyectos y aprobación manual

Cree estos AppProjects en el hub y sustituya las URL Git por repositorios aprobados. Los nombres de destino coinciden con el script de registro. El proyecto de infraestructura permite NodePools; el de aplicaciones permite únicamente los tipos de recursos con namespace necesarios. Los AppProjects no sustituyen el RBAC de Kubernetes ni aíslan código no confiable.

```yaml
# fixtures/projects.yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: infrastructure
  namespace: argocd
spec:
  sourceRepos: [https://github.com/REPLACE_ORG/infra-manifests.git]
  destinations:
    - name: workload-blue
      namespace: demo-app
    - name: workload-green
      namespace: demo-app
  clusterResourceWhitelist:
    - group: karpenter.sh
      kind: NodePool
  namespaceResourceWhitelist: []
---
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: applications
  namespace: argocd
spec:
  sourceRepos: [https://github.com/REPLACE_ORG/app-manifests.git]
  destinations:
    - name: workload-blue
      namespace: demo-app
    - name: workload-green
      namespace: demo-app
  clusterResourceWhitelist: []
  namespaceResourceWhitelist:
    - group: apps
      kind: Deployment
    - group: ""
      kind: Service
    - group: ""
      kind: ConfigMap
    - group: autoscaling
      kind: HorizontalPodAutoscaler
    - group: policy
      kind: PodDisruptionBudget
```

```yaml
# fixtures/nodepool-application.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: nodepools-blue
  namespace: argocd
spec:
  project: infrastructure
  source:
    repoURL: https://github.com/REPLACE_ORG/infra-manifests.git
    targetRevision: main
    path: nodepools/overlays/blue
  destination:
    name: workload-blue
    namespace: demo-app
  syncPolicy:
    syncOptions:
      - ServerSideApply=true
    retry:
      limit: 3
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 1m
```

Para green, cambie conjuntamente el nombre de Application, el destino y la ruta del overlay. Este ejemplo de infraestructura mantiene deshabilitada la sincronización automática para permitir su revisión. Omite un finalizer de borrado en cascada de Application y exige confirmación para podar o eliminar NodePools. `automated.prune=false` por sí solo no bloquea todas las vías de eliminación.

Los cambios en NodePool pueden generar drift y reemplazar nodos. Los presupuestos de interrupción limitan las interrupciones voluntarias a las que se aplican, no toda expiración, interrupción Spot o eliminación forzada. Considere conjuntamente los límites de vida de nodos de Auto Mode, los PDB, el tiempo de drenaje y la capacidad de reemplazo.

## Estrategias de ApplicationSet

Examine las Applications generadas y sus rutas reales antes de habilitar la reconciliación. Estos ejemplos usan el namespace `demo-app` existente. Cada directorio de aplicación necesita una Kustomization válida y nombres de recursos sin colisiones.

### Generador de clusters

Seleccione únicamente clusters registrados con la etiqueta `gitops-target=true`. Este ejemplo y el siguiente ejemplo Matrix son **alternativas**: evite que ambos gestionen los mismos recursos frontend.

```yaml
# fixtures/cluster-appset.yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: frontend-clusters
  namespace: argocd
spec:
  goTemplate: true
  goTemplateOptions: [missingkey=error]
  syncPolicy:
    preserveResourcesOnDeletion: true
  generators:
    - clusters:
        selector:
          matchLabels:
            gitops-target: "true"
            environment: production
  template:
    metadata:
      name: '{{.nameNormalized}}-frontend'
    spec:
      project: applications
      source:
        repoURL: https://github.com/REPLACE_ORG/app-manifests.git
        targetRevision: main
        path: 'apps/frontend/overlays/{{index .metadata.labels "cluster-color"}}'
      destination:
        name: '{{.name}}'
        namespace: demo-app
      syncPolicy:
        automated:
          prune: false
          selfHeal: true
```

`nameNormalized` es adecuado para nombres Kubernetes; `name` es el nombre del destino registrado. Use `index` de Go template para claves de etiquetas que contengan guiones. En los generadores de archivos Git, prefiera un campo de configuración como `sourcePath` para evitar colisiones con los metadatos `.path` generados.

### Generadores Matrix y de directorios Git

```yaml
# fixtures/matrix-appset.yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: application-matrix
  namespace: argocd
spec:
  goTemplate: true
  goTemplateOptions: [missingkey=error]
  syncPolicy:
    preserveResourcesOnDeletion: true
  generators:
    - matrix:
        generators:
          - clusters:
              selector:
                matchLabels:
                  gitops-target: "true"
                  environment: production
          - git:
              repoURL: https://github.com/REPLACE_ORG/app-manifests.git
              revision: main
              directories:
                - path: apps/*
                - path: apps/internal
                  exclude: true
  template:
    metadata:
      name: '{{.nameNormalized}}-{{.path.basenameNormalized}}'
    spec:
      project: applications
      source:
        repoURL: https://github.com/REPLACE_ORG/app-manifests.git
        targetRevision: main
        path: '{{.path.path}}/overlays/{{index .metadata.labels "cluster-color"}}'
      destination:
        name: '{{.name}}'
        namespace: demo-app
      syncPolicy:
        automated:
          prune: false
          selfHeal: true
```

Este Matrix tiene **dos generadores hijos**. Dos clusters y tres aplicaciones coincidentes producen seis combinaciones. Los generadores de combinación no pueden anidarse a cualquier profundidad. Excluya el propio `apps/internal`; excluir únicamente `apps/internal/*` no elimina necesariamente su directorio padre.

Las plantillas Go se aplican a campos de texto. No coloque una plantilla de texto en un campo booleano, como `prune: '{{.prune}}'`, ni use una expresión `if` como clave YAML. Use booleanos explícitos o un `templatePatch` validado para objetos condicionales. Permitir que entradas externas seleccionen libremente rutas de origen, proyectos o destinos puede abrir vías de escalada de privilegios.

`preserveResourcesOnDeletion=true` permite conservar recursos cuando se eliminan las Applications generadas. No es una migración que quite finalizers existentes y es distinto de la poda explícita o la eliminación manual de recursos. Defina quién limpia los recursos retirados de Git.

### Orden de despliegue y entornos de vista previa de PR

- Una sync wave ordena recursos dentro de la sincronización de una Application. Las anotaciones wave en las Applications generadas no serializan por sí solas los despliegues de ApplicationSet entre clusters.
- Para la aprobación y progresión según la salud entre clusters, use un flujo de promoción independiente o RollingSync compatible de ApplicationSet. Siga la [guía de ApplicationSet](../gitops/argocd/04-applicationsets.md) para configurar la función, los controles de salud y las restricciones de sincronización automática.
- Los generadores de PR pueden ejecutar código y manifiestos de la PR. Utilice un cluster de vista previa independiente y protegido, AppProject/RBAC restringidos, cuotas de recursos y digests de imágenes verificados. Una etiqueta `preview` no establece un límite de confianza.
- Al cerrar una PR, esta desaparece de la salida del generador y se aplica el comportamiento de eliminación configurado. `info` no es un TTL, y no se garantiza que un namespace creado mediante `CreateNamespace=true` se elimine junto con la Application. Defina los finalizers, la conservación de recursos y el responsable de limpiar namespaces.

Los ejemplos validados de PR, templatePatch y RollingSync están en el [capítulo de ApplicationSet](../gitops/argocd/04-applicationsets.md).

## SSO con IAM Identity Center

Este capítulo utiliza **SAML 2.0 con Dex**, la ruta que Argo CD documenta para IAM Identity Center. La funcionalidad OAuth/de propagación de identidad de confianza de Identity Center no debe reinterpretarse como un emisor OIDC genérico para Argo CD. Una URL de inicio de sesión SAML no es un endpoint de descubrimiento OIDC.

1. Cree una aplicación SAML 2.0 administrada por el cliente en **Applications** de IAM Identity Center.
2. Haga coincidir su URL ACS y audiencia con `https://argocd.example.com/api/dex/callback`, utilizando el dominio real. Asigne a esta aplicación los usuarios/grupos permitidos.
3. Obtenga la URL de inicio de sesión y el certificado de firma de **esta aplicación**. No los confunda con los metadatos de origen de identidad utilizados para conectar un IdP externo a Identity Center.
4. Mapee los atributos de usuario necesarios, como `email`, mediante asignaciones compatibles. Verifique el subject y los atributos exactos en una aserción real.
5. Codifique en base64 el PEM completo, incluidas las líneas BEGIN/END, para `caData`. Mantenga habilitada la verificación de firmas.

Integre estos parámetros en el archivo `argocd-values.yaml` gestionado por Helm. Las URL/certificados de marcador y un PEM sin codificar en `caData` no proporcionan una autenticación funcional:

```yaml
# fixtures/sso-values.yaml
# Merge into the Helm-owned argocd-values.yaml after configuring the SAML app.
dex:
  enabled: true
configs:
  cm:
    url: https://argocd.example.com
    dex.config: |
      connectors:
        - type: saml
          id: identity-center
          name: AWS IAM Identity Center
          config:
            ssoURL: https://REPLACE_WITH_APPLICATION_SIGN_IN_URL
            caData: BASE64_OF_COMPLETE_APPLICATION_SIGNING_CERTIFICATE_PEM
            entityIssuer: https://argocd.example.com/api/dex/callback
            redirectURI: https://argocd.example.com/api/dex/callback
            usernameAttr: email
            emailAttr: email
  rbac:
    policy.default: role:authenticated
    scopes: '[email]'
    policy.csv: |
      p, role:application-viewer, applications, get, applications/*, allow
      p, role:application-operator, applications, get, applications/*, allow
      p, role:application-operator, applications, sync, applications/*, allow
      g, viewer@example.com, role:application-viewer
      g, operator@example.com, role:application-operator
```

El ejemplo mínimo mapea explícitamente **claims de correo electrónico verificados** de Identity Center. Sustituya los ejemplos por identidades exactas controladas por la organización y mantenga las asignaciones cuando cambien las cuentas o se den de baja. El rol predeterminado `role:authenticated` no tiene permisos. Usar `role:readonly` como predeterminado concedería esos permisos a todos los usuarios autenticados; las políticas de denegación posteriores no pueden retirar los permisos del rol predeterminado.

**Asignar un grupo a la aplicación y recibir una aserción de grupos son cosas distintas.** La propia guía de Argo CD para Identity Center describe el mapeo del atributo de grupos como una solución alternativa no admitida oficialmente por la documentación de AWS. No presuponga propagación automática de grupos ni intercambie nombres visibles y Group IDs. Si necesita RBAC por grupos, verifique primero la ruta IdP compatible y los claims reales; después alinee `groupsAttr`, `scopes` y los valores exactos de las políticas.

El SSO de Argo CD no requiere crear un proveedor IAM SAML ni un rol `sts:AssumeRoleWithSAML`; eso corresponde a otro flujo de federación de roles de AWS. El RBAC de Argo CD, IAM de EKS y RBAC de Kubernetes tampoco conceden automáticamente accesos idénticos.

Deshabilite el administrador local solo después de verificar los usuarios SSO, al menos un administrador aprobado y la vía de recuperación. Los registros de depuración y las aserciones SAML pueden contener datos personales y de autenticación; no los imprima en registros compartidos. Diagnostique por separado ACS/audiencia, certificado/hora, asignación, atributos y RBAC.

## Gestión de secretos

Instale ESO 2.12.0 y sus CRD v1 en cada spoke. Reutilice la asociación Pod Identity del [capítulo 01](01-infrastructure-setup.md) para el namespace/ServiceAccount `external-secrets` y los permisos de lectura de los secretos indicados. Los Pods ESO de los spokes no heredan un rol asociado únicamente al hub.

```yaml
# fixtures/eso-values.yaml
# Reuse the existing external-secrets ServiceAccount Pod Identity association.
installCRDs: true
replicaCount: 2
leaderElect: true
serviceAccount:
  create: true
  name: external-secrets
  annotations: {}
serviceMonitor:
  enabled: false
```

```bash
helm repo add external-secrets https://charts.external-secrets.io
helm repo update
helm upgrade --install external-secrets external-secrets/external-secrets \
  --version 2.12.0 --namespace external-secrets --create-namespace \
  --kube-context "$TARGET_CONTEXT" --values eso-values.yaml
```

Pod Identity utiliza la cadena predeterminada de credenciales AWS del **controlador ESO en ejecución**. No añada `auth.jwt.serviceAccountRef` ni una anotación IRSA a esta ruta. ESO no puede suplantar el ServiceAccount de otro namespace para obtener su asociación Pod Identity.

```yaml
# fixtures/external-secrets.yaml
apiVersion: external-secrets.io/v1
kind: SecretStore
metadata:
  name: application-config
  namespace: demo-app
spec:
  provider:
    aws:
      service: SecretsManager
      region: ap-northeast-2
---
apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: database-credentials
  namespace: demo-app
spec:
  refreshPolicy: Periodic
  refreshInterval: 1h
  secretStoreRef:
    name: application-config
    kind: SecretStore
  target:
    name: database-credentials
    creationPolicy: Owner
    deletionPolicy: Retain
  data:
    - secretKey: username
      remoteRef:
        key: myapp/production/database
        property: username
    - secretKey: password
      remoteRef:
        key: myapp/production/database
        property: password
        version: AWSCURRENT
    - secretKey: host
      remoteRef:
        key: myapp/production/database
        property: host
    - secretKey: port
      remoteRef:
        key: myapp/production/database
        property: port
    - secretKey: database
      remoteRef:
        key: myapp/production/database
        property: dbname
```

El secreto `myapp/production/database` debe contener los campos username/password/host/port/dbname y la política IAM del controlador debe permitir su ARN exacto. Una clave KMS administrada por el cliente también necesita permiso de descifrado limitado y una política de clave compatible. Es un ejemplo de lectura por nombre, sin permisos de descubrimiento ni escritura.

Construya las URL de conexión con el generador de URL de la aplicación, en lugar de concatenar contraseñas que contengan `@`, `:` o `/`. Las variables de entorno de secretos no se actualizan automáticamente dentro de los Pods existentes; establezca la estrategia de recarga o reinicio de la aplicación.

Los SecretStores con namespace que utilizan un mismo rol de controlador no proporcionan automáticamente aislamiento IAM. Diseñe roles y ámbitos de controlador separados o configure, tras revisarla, la asunción de roles mediante `provider.aws.role`, junto con los permisos de modificación de Stores y las políticas de admisión. IRSA con `auth.jwt.serviceAccountRef` es otra ruta de autenticación que requiere su propia relación de confianza OIDC y ServiceAccount.

### Responsabilidad, actualización y rotación

- Git/Argo CD gestiona el ExternalSecret; ESO gestiona el Secret generado. Evite que Helm/Git/ESO sobrescriban repetidamente los mismos campos. Instale primero el CRD, el controlador y el Store y compruebe que estén listos.
- `refreshInterval` vuelve a leer los valores; no rota contraseñas de Secrets Manager ni emite certificados. Las funciones de rotación, las redes, los permisos de bases de datos y la rotación específica de cada servicio requieren configuración independiente.
- `AWSCURRENT` y `AWSPREVIOUS` son etapas de versión. Exigir `AWSPREVIOUS` antes de que exista puede hacer fallar toda la sincronización. No garantiza que la contraseña anterior siga siendo válida ni proporciona una reversión de la base de datos.
- `creationPolicy: Owner` y `deletionPolicy: Retain` afectan a eventos de ciclo de vida distintos. Conservar el Secret cuando desaparece un valor externo no anula su limpieza mediante la referencia al propietario al eliminar el propio ExternalSecret.
- `IgnoreExtraneous` afecta al estado de comparación; no excluye automáticamente un ExternalSecret gestionado de la sincronización o la poda.
- `PushSecret` escribe en AWS y no funciona con un rol de solo lectura. Revise los permisos de creación/actualización/etiquetado, los permisos de funciones opcionales, los conflictos de gestión, la eliminación y el cifrado. Evite crear accidentalmente un bucle de sincronización bidireccional.

## Orden de verificación

Verifique la instalación/HTTPS del hub, los roles/Access Entries/RBAC/red de destino, los Secrets de clusters, AppProjects, NodePools revisados manualmente, Applications generadas, casos reales de permiso y denegación SSO, y disponibilidad de ESO y recarga de aplicaciones. Examine estados y condiciones sin imprimir los valores de Secrets.

## Referencias

- [SAML de Identity Center para Argo CD](https://argo-cd.readthedocs.io/en/stable/operator-manual/user-management/identity-center/)
- [Aplicaciones SAML administradas por el cliente en IAM Identity Center](https://docs.aws.amazon.com/singlesignon/latest/userguide/customermanagedapps-saml2-setup.html)
- [Asignación de atributos de IAM Identity Center](https://docs.aws.amazon.com/singlesignon/latest/userguide/mapawsssoattributestoapp.html)
- [Autenticación AWS en ESO 2.12](https://external-secrets.io/v2.12.0/provider/aws-access/)
- [Helm Provider](https://registry.terraform.io/providers/hashicorp/helm/3.3.0/docs)
- [Proyectos y RBAC](../gitops/argocd/06-projects-rbac.md)
- [Cuestionario del capítulo](../quizzes/ops/04-gitops-multi-cluster-quiz.md)

< [Anterior: Pipelines de CI](03-ci-pipelines.md) | [Índice](README.md) | [Siguiente: Automatización GitOps](05-gitops-automation.md) >
