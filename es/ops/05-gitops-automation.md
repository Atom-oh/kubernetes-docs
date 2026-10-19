# Automatización GitOps: Atlantis, HCP Terraform, Flux, AIOps {#gitops-automation-atlantis-hcp-terraform-flux-aiops}

> **Versiones de referencia revisadas**: Atlantis 0.48.1 / chart 6.16.1, HCP Terraform Provider 0.80.0, Sentinel 0.41.0, Flux 2.9.6 (validado con 2.9.5; actualización del parche fijado sin repetir las pruebas)\
> **Última revisión**: 16 de octubre de 2026. Las comprobaciones se realizaron con herramientas CLI locales, charts, esquemas y dobles de prueba. No se publicaron comentarios reales en PR ni se ejecutó Terraform apply. Tampoco se crearon recursos de HCP, se desplegaron clústeres o se llamó a servicios externos de IA.

< [Anterior: Varios clústeres](04-gitops-multi-cluster.md) | [Contenido](README.md) | [Siguiente: Escalado](06-scaling-strategies.md) >

Separe la ejecución de infraestructura de la reconciliación de aplicaciones. Evite que Atlantis y HCP Terraform operen simultáneamente sobre el mismo estado o que Flux y Argo CD compitan por los mismos campos de Kubernetes.

| Herramienta | Responsabilidad | Requisitos previos independientes |
|---|---|---|
| Atlantis | Planificar y aplicar Terraform a partir de PR | Entorno de ejecución, credenciales, estado, bloqueos y autorización de comandos |
| HCP Terraform | Gestionar espacios de trabajo, ejecuciones, estado y colaboración | Conexión VCS, agentes, políticas y permisos de los espacios de trabajo |
| Flux | Reconciliar el estado de Kubernetes y Helm a partir de fuentes | Identidades de los controladores, RBAC de cada tenant y permisos de repositorio |
| Análisis AIOps | Resumir observaciones y proponer respuestas | Datos validados, aprobación y un ejecutor con restricciones independientes |

## 1. Atlantis en EKS {#1-atlantis-on-eks}

Atlantis ejecuta Terraform a partir de pull requests. **La planificación puede ejecutar proveedores, fuentes de datos externas y comandos personalizados.** Exigir aprobación para apply no hace seguro un plan procedente de una fuente no fiable. Este ejemplo está destinado a un repositorio privado de infraestructura controlado y a un equipo de operaciones autorizado; los PR de forks y la planificación automática están deshabilitados.

### Requisitos previos de identidad e instalación {#identity-and-installation-prerequisites}

- Configure la asociación de Pod Identity de EKS Auto Mode para el espacio de nombres y la ServiceAccount `atlantis`. No la mezcle con una anotación IRSA. Los nodos convencionales requieren la configuración compatible del agente y el SDK.
- Limite el acceso a las claves exactas de estado y `.tflock`, las claves KMS necesarias y los recursos gestionados. Distinga la lectura y escritura de los objetos de estado de la lectura, escritura y eliminación de los objetos de bloqueo. Los permisos amplios `eks:*`, la creación de roles IAM y PassRole no constituyen una política universal de mínimo privilegio.
- Restrinja la asunción de roles a los ARN exactos y a las relaciones de confianza previstas. Use las condiciones admitidas de etiquetas de solicitud de clúster, espacio de nombres y ServiceAccount para Pod Identity.
- Proteja las credenciales y el JSON sensible de los planes frente a su exposición en la salida de PR. Terraform `sensitive=true` no impide que los valores se almacenen en el estado.

El entorno de ejecución necesita acceso a AWS, Git, los registros de proveedores y módulos y las API privadas de EKS. No dependa de scripts de instalación sin verificar ni de herramientas ausentes de la imagen. Terraform 1.15.7 debe estar instalado o poder obtenerse por la ruta de descarga permitida para `defaultTFVersion`.

### Valores de Helm asociados a la versión {#versioned-helm-values}

Si `auto-gp3` aún no existe, prepare una StorageClass de Auto Mode como la siguiente. Su aprovisionador difiere del EBS CSI convencional. Use una alternativa adecuada si el clúster funciona en otro modo.

```yaml
# fixtures/atlantis-storage.yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: auto-gp3
provisioner: ebs.csi.eks.amazonaws.com
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Retain
allowVolumeExpansion: true
parameters:
  type: gp3
  encrypted: "true"
allowedTopologies:
  - matchLabelExpressions:
      - key: eks.amazonaws.com/compute-type
        values: [auto]
```

Prepare estos Secrets en el espacio de nombres `atlantis` mediante el mecanismo aprobado de gestión de secretos. Mantenga los valores reales fuera de Git y de los valores de Helm.

| Secret | Claves requeridas |
|---|---|
| `atlantis-vcs` | `github-token`, `webhook-secret` |
| `atlantis-web-auth` | `username`, `password` |

Conceda al bot y al token de GitHub los permisos necesarios para el repositorio, los PR y las consultas de equipos, y rote el token. Sustituya `platform` por el equipo realmente autorizado de la organización. Use la lista de equipos permitidos de Atlantis en lugar de comparar subcadenas de nombres de usuario en un hook de shell.

```yaml
# fixtures/atlantis-values.yaml
fullnameOverride: atlantis
replicaCount: 1
image:
  repository: ghcr.io/runatlantis/atlantis
  tag: v0.48.1
orgAllowlist: github.com/REPLACE_ORG/eks-infra
atlantisUrl: https://atlantis.example.com
defaultTFVersion: 1.15.7
allowForkPRs: false
disableApplyAll: true
basicAuthSecretName: atlantis-web-auth
service:
  type: ClusterIP
ingress:
  enabled: false
volumeClaim:
  enabled: true
  dataStorage: 10Gi
  storageClassName: auto-gp3
  accessModes:
  - ReadWriteOnce
serviceAccount:
  create: true
  name: atlantis
  mount: false
  annotations: {}
resources:
  requests:
    cpu: 500m
    memory: 1Gi
  limits:
    cpu: '2'
    memory: 4Gi
containerSecurityContext:
  allowPrivilegeEscalation: false
  capabilities:
    drop:
    - ALL
environment:
  ATLANTIS_GH_USER: REPLACE_BOT_USER
  ATLANTIS_GH_TEAM_ALLOWLIST: platform:plan,platform:apply
  ATLANTIS_DISABLE_AUTOPLAN: 'true'
  ATLANTIS_FAIL_ON_PRE_WORKFLOW_HOOK_ERROR: 'true'
  ATLANTIS_BLOCKED_EXTRA_ARGS: -chdir,--chdir,-plugin-dir,--plugin-dir,-target,--target,-replace,--replace,-out,--out,-var-file,--var-file,-var,--var
environmentSecrets:
- name: ATLANTIS_GH_TOKEN
  secretKeyRef:
    name: atlantis-vcs
    key: github-token
- name: ATLANTIS_GH_WEBHOOK_SECRET
  secretKeyRef:
    name: atlantis-vcs
    key: webhook-secret
repoConfig: |
  repos:
    - id: github.com/REPLACE_ORG/eks-infra
      plan_requirements: [approved]
      apply_requirements: [approved, mergeable, undiverged]
      import_requirements: [approved, mergeable, undiverged]
      workflow: reviewed
      allowed_overrides: []
      allow_custom_workflows: false
      repo_locks:
        mode: on_plan
  workflows:
    reviewed:
      plan:
        steps:
          - init:
              extra_args: [-backend-config=backend.hcl]
          - run: terraform fmt -check -diff
          - run: terraform validate
          - plan:
              extra_args: [-var-file=terraform.tfvars, -lock-timeout=300s]
      apply:
        steps:
          - apply
```

```bash
helm repo add runatlantis https://runatlantis.github.io/helm-charts
helm repo update
helm upgrade --install atlantis runatlantis/atlantis \
  --version 6.16.1 --namespace atlantis --create-namespace \
  --kube-context "$ATLANTIS_CONTEXT" --values atlantis-values.yaml
```

Estos valores crean únicamente un Service de tipo ClusterIP. Exponga `atlantis.example.com` y `/events` mediante un proxy HTTPS o Ingress aprobado y configure el secreto correspondiente del webhook de GitHub. La verificación del webhook y la autenticación de la interfaz web son mecanismos distintos. No convierta la ruta de eventos en una vía general para eludir la autenticación.

El chart 6.16.1 usa `orgAllowlist`, `volumeClaim`, un mapa `environment` y `containerSecurityContext`. El PVC escribible contiene los archivos del repositorio, los planes y los bloqueos del servidor; no lo cubra con un ConfigMap de solo lectura. Aumentar las réplicas por sí solo no proporciona alta disponibilidad a un despliegue con un único PVC RWO y BoltDB. Gestione la retención, las copias de seguridad, la recuperación y la posterior eliminación de los volúmenes retenidos.

### Política de servidor y proyectos de repositorio {#server-policy-and-repository-projects}

La configuración `repoConfig` incorporada está bajo control del servidor. `allowed_overrides: []` y `allow_custom_workflows: false` impiden que un PR modifique los requisitos de aprobación o los comandos de ejecución. Configure por separado la protección de ramas y las comprobaciones obligatorias de GitHub. `approved` no implica por sí solo dos aprobaciones distintas y vigentes del último commit.

Exigir apply como requisito previo para `mergeable` puede crear una dependencia circular. Alinee las dependencias de planificación, comprobación, revisión y aplicación con las reglas del repositorio. Este ejemplo usa comandos explícitos `atlantis plan -p ...`; revise y vuelva a planificar los cambios realizados después de la aprobación.

Coloque este archivo en la raíz del repositorio. Cada directorio de proyecto usa la raíz correspondiente del [capítulo 01](01-infrastructure-setup.md), con su propio backend y estado, y con `backend.hcl` y `terraform.tfvars` revisados.

```yaml
# fixtures/atlantis.yaml
version: 3
automerge: false
parallel_plan: false
parallel_apply: false
projects:
  - name: network-prod
    dir: 01-network
    workspace: default
    terraform_version: v1.15.7
    autoplan:
      enabled: false
      when_modified: ["*.tf", "*.tfvars", "backend.hcl", ".terraform.lock.hcl", "../modules/**/*.tf"]
  - name: cluster-prod
    dir: 02-cluster
    workspace: default
    terraform_version: v1.15.7
    depends_on: [network-prod]
    autoplan:
      enabled: false
      when_modified: ["*.tf", "*.tfvars", "backend.hcl", ".terraform.lock.hcl", "../modules/**/*.tf"]
  - name: platform-prod
    dir: 03-platform
    workspace: default
    terraform_version: v1.15.7
    depends_on: [cluster-prod]
    autoplan:
      enabled: false
      when_modified: ["*.tf", "*.tfvars", "backend.hcl", ".terraform.lock.hcl", "../modules/**/*.tf"]
```

Revise y aplique los cambios de red antes de planificar, revisar y aplicar los cambios de clúster y plataforma. `depends_on` no transfiere las salidas del estado remoto ni actualiza automáticamente un plan dependiente guardado previamente. Vuelva a planificar los cambios dependientes cuando cambien sus dependencias.

```text
atlantis plan -p network-prod
atlantis apply -p network-prod
atlantis plan -p cluster-prod
atlantis apply -p cluster-prod
atlantis plan -p platform-prod
atlantis apply -p platform-prod
```

Estos comandos se publican como comentarios en el PR. El flujo habitual de Atlantis es **planificar en el PR → cumplir los requisitos de aprobación → aplicar ese plan guardado → fusionar**. Fusionar por sí solo no aplica la infraestructura. `automerge` es una opción independiente que permite fusionar después de que los planes se hayan aplicado correctamente.

Las etapas integradas `plan`/`apply` usan el archivo de plan administrado por Atlantis. Los comandos personalizados deben respetar `$PLANFILE`. No lo sustituya por un `-out=tfplan` independiente ni pase valores nuevos de `-var-file` al aplicar un plan guardado. Los archivos de plan y el JSON pueden contener datos sensibles.

### Bloqueos, políticas y manejo de fallos {#locks-policies-and-failure-handling}

Los bloqueos de PR, proyecto y espacio de trabajo de Atlantis son distintos de los bloqueos de estado del backend de Terraform. La base de datos predeterminada actual del servidor es BoltDB; las configuraciones compatibles con Redis requieren un diseño aparte. No describa DynamoDB como la base de datos de bloqueos predeterminada de Atlantis ni invente ConfigMaps `lock_groups` o `apply_priority`.

`atlantis unlock` **elimina** un bloqueo; no es una consulta. Compruebe primero las ejecuciones activas, los planes guardados y los bloqueos de estado. `atlantis lock`, `atlantis locks` y `unlock --force` no son comandos generales de PR en la versión de este ejemplo. Use la interfaz admitida o la API autenticada para inspeccionar los bloqueos.

Buscar patrones en el código fuente y contar los recursos del estado actual no valida toda la infraestructura planificada. Tenga en cuenta los módulos, las fuentes de datos, los proveedores y los valores de creación, actualización, eliminación o aún desconocidos. Convertir en advertencias los fallos de fmt, validate, políticas o API, o añadir `|| true`, elimina el control que debía impedir avanzar.

## 2. HCP Terraform {#2-hcp-terraform}

Terraform Cloud se llama ahora **HCP Terraform**. Es una alternativa a Atlantis con funciones de espacios de trabajo, ejecuciones, estado y políticas. Compruebe el plan comercial y el contrato actuales para conocer las funciones, los precios, la concurrencia, los agentes y Sentinel disponibles. El alojamiento gestionado también requiere configurar deliberadamente VCS, permisos, red y aprobaciones.

### Espacios de trabajo y credenciales dinámicas de AWS {#workspaces-and-dynamic-aws-credentials}

Este ejemplo supone que ya existen una organización y un proyecto, una conexión OAuth con VCS y un **pool de agentes** con acceso a la red privada. La ejecución mediante agentes requiere un plan que la incluya y una versión compatible del agente. No suponga que un ejecutor remoto público puede acceder directamente a una API privada de EKS.

```hcl
# tfe/main.tf
terraform {
  required_version = ">= 1.10, < 2.0"
  required_providers {
    tfe = {
      source  = "hashicorp/tfe"
      version = "= 0.80.0"
    }
  }
}

# Supply a scoped TFE_TOKEN through the approved secret mechanism, not in Git.
provider "tfe" {
  hostname = "app.terraform.io"
}

locals {
  layers = {
    network  = "01-network"
    cluster  = "02-cluster"
    platform = "03-platform"
  }
  environment_variables = merge([
    for layer, directory in local.layers : {
      for key, value in {
        TFC_AWS_PROVIDER_AUTH  = "true"
        TFC_AWS_PLAN_ROLE_ARN  = var.workspace_roles[layer].plan
        TFC_AWS_APPLY_ROLE_ARN = var.workspace_roles[layer].apply
        AWS_REGION             = var.aws_region
      } : "${layer}:${key}" => { layer = layer, key = key, value = value }
    }
  ]...)
}

resource "tfe_workspace" "layer" {
  for_each               = local.layers
  name                   = "${each.key}-prod"
  organization           = var.organization
  project_id             = var.project_id
  terraform_version      = "1.15.7"
  working_directory      = each.value
  auto_apply             = false
  auto_apply_run_trigger = false
  queue_all_runs         = false
  tag_names              = ["production", each.key]
  vcs_repo {
    identifier     = var.repository
    branch         = "main"
    oauth_token_id = var.vcs_connection_id
  }
}

resource "tfe_workspace_settings" "layer" {
  for_each                  = local.layers
  workspace_id              = tfe_workspace.layer[each.key].id
  execution_mode            = "agent"
  agent_pool_id             = var.agent_pool_id
  global_remote_state       = false
  project_remote_state      = false
  remote_state_consumer_ids = []
}

resource "tfe_variable" "aws" {
  for_each     = local.environment_variables
  workspace_id = tfe_workspace.layer[each.value.layer].id
  category     = "env"
  key          = each.value.key
  value        = each.value.value
}

resource "tfe_run_trigger" "cluster_after_network" {
  workspace_id  = tfe_workspace.layer["cluster"].id
  sourceable_id = tfe_workspace.layer["network"].id
}

resource "tfe_run_trigger" "platform_after_cluster" {
  workspace_id  = tfe_workspace.layer["platform"].id
  sourceable_id = tfe_workspace.layer["cluster"].id
}
```

```hcl
# tfe/variables.tf
variable "organization" {
  type = string
}
variable "project_id" {
  type = string
}
variable "agent_pool_id" {
  type = string
}
variable "repository" {
  type = string
}
variable "vcs_connection_id" {
  type = string
}
variable "aws_region" {
  type    = string
  default = "ap-northeast-2"
}
variable "workspace_roles" {
  type = map(object({
    plan  = string
    apply = string
  }))
  validation {
    condition = alltrue([
      for layer in ["network", "cluster", "platform"] :
      can(regex("^arn:aws:iam::[0-9]{12}:role/.+$", var.workspace_roles[layer].plan)) &&
      can(regex("^arn:aws:iam::[0-9]{12}:role/.+$", var.workspace_roles[layer].apply))
    ])
    error_message = "Supply existing scoped plan/apply role ARNs for every layer."
  }
}
```

Este módulo raíz configura recursos de HCP. Proteja su backend y estado por separado de los espacios de trabajo de infraestructura. Antes de usar el estado gestionado por HCP para un módulo raíz existente, decida quién será responsable y migre deliberadamente su backend S3 original. Evite que dos sistemas de ejecución apliquen cambios al mismo estado.

AWS ya debe contar con el proveedor OIDC `app.terraform.io` y con roles de planificación y aplicación de alcance restringido. Limite la audiencia y el sujeto de la relación de confianza a la organización, el proyecto y el espacio de trabajo exactos, y a `run_phase:plan` o `run_phase:apply`. Las variables `TFC_AWS_*` identifican roles; no contienen claves de acceso persistentes. Compruebe que las versiones reales del proveedor y el agente admiten credenciales dinámicas.

`queue_all_runs=false` retiene las ejecuciones activadas por VCS durante la configuración inicial del espacio de trabajo. Después de la primera ejecución manual, no actúa como un interruptor permanente que impida ejecutar cambios.

### Disparadores de ejecución y salidas compartidas {#run-triggers-and-sharing-outputs}

Una aplicación correcta de los cambios de una dependencia pone en cola una ejecución dependiente. **`auto_apply_run_trigger` es independiente de la opción habitual `auto_apply`.** Ambas son false en este ejemplo, por lo que se requiere una revisión antes de aplicar cambios. Un disparador no demuestra que todas las dependencias estén listas ni transfiere sus salidas.

El ejemplo no comparte globalmente el estado del espacio de trabajo. Si otro componente necesita sus salidas, configure los consumidores y permisos aprobados y considere `tfe_outputs`. Las credenciales que permiten leer `terraform_remote_state` dan acceso al estado sensible completo, no solo a las salidas que muestra la fuente de datos. Conecte el acceso a las salidas y las entradas de los módulos según el diseño real.

### Políticas Sentinel {#sentinel-policies}

Estas son tres **políticas de ejemplo** probadas con Sentinel 0.41.0, no programas de Python. Para que puedan bloquear ejecuciones de HCP, deben existir un conjunto de políticas, espacios de trabajo de destino y una configuración que determine su aplicación obligatoria.

```text
# policies/required-tags.sentinel
import "tfplan/v2" as tfplan

required_tags = ["Environment", "Team", "CostCenter"]
taggable_types = ["aws_instance", "aws_vpc", "aws_subnet",
                 "aws_security_group", "aws_eks_cluster", "aws_eks_node_group"]

changes = filter tfplan.resource_changes as _, rc {
  rc.mode is "managed" and rc.type in taggable_types and
  (rc.change.actions contains "create" or rc.change.actions contains "update")
}

valid_tag = func(tags, key) {
  value = tags[key] else null
  return value is not null and value is not ""
}

has_required_tags = func(rc) {
  tags = rc.change.after.tags_all else {}
  unknown = rc.change.after_unknown.tags_all else false
  if tags is null or unknown is true {
    return false
  }
  if unknown is false or unknown is null {
    unknown = {}
  }
  return all required_tags as tag {
    not (unknown[tag] else false) and valid_tag(tags, tag)
  }
}

main = rule {
  all changes as _, rc { has_required_tags(rc) }
}
```

Comprobar `tags_all` incluye las etiquetas predeterminadas del proveedor de AWS. Este ejemplo examina las acciones de creación y actualización de los tipos de recursos indicados y excluye la eliminación. Las etiquetas obligatorias ausentes, vacías, null o desconocidas no superan la comprobación. La política no cubre todos los tipos de recursos de AWS.

```text
# policies/instance-types.sentinel
import "tfplan/v2" as tfplan

# Organization policy example; use a reviewed allowlist for the actual region.
allowed = ["m7i.large", "m7i.xlarge", "m7g.large", "m7g.xlarge"]
changes = filter tfplan.resource_changes as _, rc {
  rc.mode is "managed" and
  rc.type in ["aws_instance", "aws_eks_node_group"] and
  (rc.change.actions contains "create" or rc.change.actions contains "update")
}

approved_types = func(rc) {
  if rc.type is "aws_instance" {
    return (rc.change.after.instance_type else "") in allowed and
           not (rc.change.after_unknown.instance_type else false)
  }
  types = rc.change.after.instance_types else []
  return length(types) > 0 and
         not (rc.change.after_unknown.instance_types else false) and
         all types as instance_type { instance_type in allowed }
}

main = rule {
  all changes as _, rc { approved_types(rc) }
}
```

Esta política se aplica a instancias EC2 y grupos de nodos gestionados que especifican directamente `instance_types`. Los grupos que solo usan una plantilla de lanzamiento, los NodePools de Auto Mode y otros servicios de cómputo requieren políticas adicionales. Una lista de tipos vacía o desconocida no se considera un conjunto vacío aprobado.

```text
# policies/cost-limit.sentinel
import "tfrun"
import "decimal"

# This checks HCP's available estimate, not the complete future AWS bill.
param monthly_limit default "5000"
estimate = tfrun.cost_estimate.proposed_monthly_cost else null

main = rule {
  estimate is not null and
  decimal.new(estimate).greater_than_or_equals(0) and
  decimal.new(estimate).less_than_or_equals(monthly_limit)
}
```

Use `tfrun.cost_estimate`, no una ruta inexistente como `tfplan.workspace`. El ejemplo acepta una estimación mensual proporcionada de hasta 5.000 y rechaza valores ausentes, negativos, NaN o infinitos. No garantiza un límite para la factura completa de AWS que incluya recursos no admitidos, tráfico e infraestructura existente.

```hcl
# policies/sentinel.hcl
policy "required-tags" {
  source            = "./required-tags.sentinel"
  enforcement_level = "hard-mandatory"
}
policy "instance-types" {
  source            = "./instance-types.sentinel"
  enforcement_level = "hard-mandatory"
}
policy "cost-limit" {
  source            = "./cost-limit.sentinel"
  enforcement_level = "hard-mandatory"
}
```

Asocie el conjunto de políticas a los espacios de trabajo previstos y separe la administración de políticas de la operación de recursos. Llamar `soft_main` a una regla no cambia su nivel de aplicación a soft-mandatory. No convierta los fallos de evaluación o los errores de API en resultados correctos.

## 3. Flux {#3-flux}

Esta sección usa la [guía de Flux 2.9.6](../gitops/02-fluxcd.md). Tanto Argo CD como Flux reconcilian estado declarativo. Argo CD también consta de varios componentes; Flux no es siempre más ligero ni ofrece necesariamente mayor aislamiento. Separar espacios de nombres por sí solo no completa la autorización de los tenants.

Los controladores de detección y automatización de imágenes son **componentes opcionales**. Bootstrap crea commits en Git e instala controladores. Compruebe la suma de verificación de la CLI, la versión compatible de Kubernetes, el contexto de Kubernetes y el acceso al repositorio antes de ejecutarlo.

```bash
flux check --pre
flux bootstrap github \
  --owner=REPLACE_ORG --repository=fleet-infra --branch=main \
  --path=clusters/production --version=v2.9.6 \
  --components-extra=image-reflector-controller,image-automation-controller
```

Proporcione de forma segura las credenciales autorizadas de GitHub. No añada `--personal` a un ejemplo destinado a una organización. Distinga los archivos predeterminados `flux-system` que genera bootstrap de los directorios de infraestructura y aplicaciones que añada usted mismo.

### Automatización de imágenes y aprobación de Git {#image-automation-and-git-approval}

El ejemplo requiere un Secret preparado para escribir en Git, credenciales de lectura de ECR en image-reflector-controller mediante Pod Identity o IRSA, y la Kustomization o HelmRelease de Flux que despliega la aplicación. Estos permisos son distintos del rol con el que el nodo descarga imágenes. No combine sin revisar `provider: aws` con otra vía de autenticación basada en un secreto del registro.

```yaml
# fixtures/flux-images.yaml
apiVersion: source.toolkit.fluxcd.io/v1
kind: GitRepository
metadata:
  name: applications
  namespace: flux-system
spec:
  interval: 1m
  url: https://github.com/REPLACE_ORG/app-manifests.git
  ref:
    branch: main
  secretRef:
    name: applications-git-auth
---
apiVersion: image.toolkit.fluxcd.io/v1
kind: ImageRepository
metadata:
  name: application
  namespace: flux-system
spec:
  image: REPLACE_ACCOUNT.dkr.ecr.ap-northeast-2.amazonaws.com/docs-ci/application
  interval: 5m
  provider: aws
---
apiVersion: image.toolkit.fluxcd.io/v1
kind: ImagePolicy
metadata:
  name: application
  namespace: flux-system
  labels:
    app: application
spec:
  imageRepositoryRef:
    name: application
  policy:
    semver:
      range: ">=1.0.0 <2.0.0"
  digestReflectionPolicy: IfNotPresent
---
apiVersion: image.toolkit.fluxcd.io/v1
kind: ImageUpdateAutomation
metadata:
  name: application
  namespace: flux-system
spec:
  interval: 30m
  sourceRef:
    kind: GitRepository
    name: applications
  git:
    checkout:
      ref:
        branch: main
    commit:
      author:
        name: Flux automation
        email: flux@example.com
      messageTemplate: |
        Update approved application image
        {{ range .Changed.Changes -}}
        {{ .OldValue }} -> {{ .NewValue }}
        {{ end -}}
    push:
      branch: flux/image-updates
  update:
    path: ./apps/production
    strategy: Setters
  policySelector:
    matchLabels:
      app: application
```

La política supone **versiones semver inmutables publicadas después de la aprobación**. Las etiquetas únicas de SHA o compilación del [capítulo de CI](03-ci-pipelines.md) no cumplen ese patrón. Un proceso independiente de promoción debe etiquetar el digest aprobado del índice como versión, o la política debe usar un esquema revisado de números de compilación crecientes procedentes de un único sistema de CI.

```yaml
# fixtures/flux-values.yaml
# apps/production/application/values.yaml -- actual Helm values file
# Replace repository and initial digest with the already approved application.
image:
  repository: REPLACE_ACCOUNT.dkr.ecr.ap-northeast-2.amazonaws.com/docs-ci/application # {"$imagepolicy": "flux-system:application:name"}
  tag: "1.0.0" # {"$imagepolicy": "flux-system:application:tag"}
  digest: sha256:REPLACE_APPROVED_DIGEST # {"$imagepolicy": "flux-system:application:digest"}
```

El chart real de la aplicación debe usar `image.repository`, `tag` y `digest` al construir la URI de la imagen del contenedor. Añadir un valor digest no hace que un chart existente lo utilice. Compruebe que el manifiesto generado apunta al digest aprobado. Alinee las rutas de Setters, los marcadores de políticas y el nombre de GitRepository.

La plantilla actual de commit de ImageUpdateAutomation usa **`.Changed`**. No la sustituya por `.Updated`, que se ha eliminado. La automatización publica los cambios en su rama dedicada `flux/image-updates`; crear el PR y aprobar su fusión en main requiere otro flujo de trabajo. Alinee los permisos de escritura en Git con la protección de ramas. Seleccionar una etiqueta no sustituye la comprobación de vulnerabilidades y firmas.

### Fuentes, Helm y notificaciones {#sources-helm-and-notifications}

- Los ejemplos actuales usan las API v1 de `GitRepository`, `OCIRepository`, `Bucket` e imágenes. HelmRelease es v2; su CRD actual admite `test.enable` y `test.timeout`. Valide conjuntamente las versiones y los valores del chart y los CRD.
- Kustomization `dependsOn` espera a que el objeto de Flux referenciado tenga la condición Ready. Configure wait y healthChecks para observar la salud de las cargas de trabajo; esta dependencia no es una barrera global entre clústeres.
- Evite que Terraform Helm Provider y Flux gestionen simultáneamente la misma instalación de Helm. Cambiar quién gestiona la instalación de Argo CD requiere migrar deliberadamente el estado y la configuración.
- No exponga los buckets de estado de Terraform como fuentes habituales de manifiestos de Flux. Use un bucket independiente de artefactos de manifiestos, con acceso restringido por prefijo, y evite patrones de exclusión que incorporen `.git` en los artefactos.
- Almacene los webhooks de notificación en Secrets y compruebe el tipo real de receptor y su autenticación. Pruebe los eventos seleccionados por gravedad y filtros. No presente una interfaz no instalada ni una integración retirada como parte de la instalación predeterminada.

La [guía de Flux](../gitops/02-fluxcd.md) contiene ejemplos completos de fuentes, Kustomization, HelmRelease y notificaciones.

## 4. AIOps: de la observación a propuestas que se puedan revisar {#4-aiops-from-observation-to-reviewable-proposals}

### Revisión de PR asistida por LLM {#llm-assisted-pr-review}

Configure la revisión de código de GitHub Copilot mediante sus opciones admitidas de revisor y revisión automática, con los permisos de repositorio necesarios y un plan que incluya la función. Un endpoint ficticio como `api.copilot.example.com` no constituye un ejemplo de API ejecutable.

Una integración personalizada con un LLM debe respetar el contrato actual de API, modelo y SDK del servicio real, los tiempos de espera, el tratamiento de errores HTTP y la validación de las respuestas. Los diffs y nombres de archivo son datos no fiables. Pase valores estructurados en lugar de interpolarlos en cadenas de shell, JavaScript o JSON. Las instrucciones incluidas en el contenido revisado no autorizan su ejecución.

Indique cuándo se ha truncado contenido o ha fallado la API. No entregue secretos a PR de forks externos ni convierta una respuesta del modelo por sí sola en una aprobación, fusión o aplicación de cambios. Defina el alcance permitido de divulgación del código fuente y de costes antes de usar un servicio externo. Durante la revisión de este documento no se llamó a ningún servicio externo de IA.

### Unidades de las métricas y calidad de los datos {#metric-units-and-data-quality}

El promedio de un contador de CPU no representa su utilización. `rate(container_cpu_usage_seconds_total[...])` devuelve núcleos de CPU; `averageUtilization` del HPA es un porcentaje de las **solicitudes de CPU**. No compare ese porcentaje con RPS. Identifique el scaleTargetRef del HPA y qué controlador gestiona realmente los Pods, en lugar de suponer que el HPA y el Deployment comparten nombre.

El p95 temporal de RPS es distinto del cuantil de un histograma de duración de solicitudes:

```promql
# Seven-day p95 of RPS: counter -> rate -> temporal quantile
quantile_over_time(0.95,
  (sum(rate(http_requests_total{namespace="production",service="myapp"}[5m])))[7d:5m]
)

# Request-duration p95 from a classic histogram, in seconds
histogram_quantile(0.95,
  sum by (le) (rate(http_request_duration_seconds_bucket{
    namespace="production",service="myapp"
  }[5m]))
)
```

Use nombres y etiquetas de métricas que correspondan a la recopilación real. Las series ausentes, el tráfico cero, NaN, las observaciones antiguas y los intervalos sin datos no demuestran que el servicio esté sano. Combine tráfico, errores, latencia y capacidad. La CPU media por sí sola no determina un «objetivo óptimo del HPA»; también importan las pruebas de carga, los SLO y el comportamiento al reducir capacidad.

### Ejemplo ejecutable que solo genera un análisis {#executable-analysis-only-example}

Esta herramienta lee desde stdin una serie JSON previamente normalizada de una sola métrica y emite **únicamente un informe de recomendación**. No modifica API, HPA, NLB, Git ni Slack. Que el valor esté dentro del rango de referencia no demuestra que la aplicación esté sana.

```python
# fixtures/anomaly-report.py
#!/usr/bin/env python3
"""Read an already normalized metric series; emit an advisory report only."""
import argparse
import json
import math
import statistics
import sys
import time


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def assess(data, now):
    if not number(now):
        return {"status": "invalid_data", "reason": "Invalid observation clock"}
    if not isinstance(data, dict):
        return {"status": "invalid_data", "reason": "Expected an object"}
    if data.get("unit") not in {"requests_per_second", "seconds", "ratio"}:
        return {"status": "invalid_data", "reason": "Declare one supported normalized unit"}
    period = data.get("periodSeconds")
    points = data.get("points")
    if not number(period) or period <= 0 or not isinstance(points, list):
        return {"status": "invalid_data", "reason": "Invalid period or series"}
    if len(points) < 31:
        return {"status": "insufficient_data", "reason": "Need 30 baseline points and one observation"}
    if any(
        not isinstance(p, dict)
        or not number(p.get("timestamp"))
        or not number(p.get("value"))
        or p["value"] < 0
        or (data["unit"] == "ratio" and p["value"] > 1)
        for p in points
    ):
        return {"status": "invalid_data", "reason": "Non-finite, negative or incorrectly normalized point"}
    ordered = sorted(points, key=lambda p: p["timestamp"])
    gaps = [b["timestamp"] - a["timestamp"] for a, b in zip(ordered, ordered[1:])]
    if any(abs(gap - period) > period * 0.1 for gap in gaps):
        return {"status": "insufficient_data", "reason": "Duplicate or missing collection intervals"}
    age = now - ordered[-1]["timestamp"]
    if age < 0 or age > period * 2:
        return {"status": "insufficient_data", "reason": "Observation is future-dated or stale"}

    # The observation is excluded from the baseline. Use an explicit per-unit
    # absolute margin; this is a demonstration heuristic, not an SLO or ML model.
    baseline = [p["value"] for p in ordered[:-1]]
    center = statistics.median(baseline)
    mad = statistics.median(abs(value - center) for value in baseline)
    absolute_margin = {"requests_per_second": 1.0, "seconds": 0.01, "ratio": 0.001}[data["unit"]]
    margin = max(6 * 1.4826 * mad, abs(center) * 0.2, absolute_margin)
    latest = ordered[-1]["value"]
    return {
        "status": "review_required" if abs(latest - center) > margin else "within_baseline",
        "unit": data["unit"],
        "observedAt": ordered[-1]["timestamp"],
        "observedValue": latest,
        "baselineMedian": center,
        "illustrativeMargin": margin,
        "baselinePoints": len(baseline),
        "actionTaken": "none",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--now", type=float, help="Unix timestamp; omit to use the current clock")
    args = parser.parse_args()
    now = args.now if args.now is not None else time.time()
    try:
        data = json.load(sys.stdin)
        result = assess(data, now)
    except (ValueError, TypeError):
        result = {"status": "invalid_data", "reason": "Invalid JSON"}
    print(json.dumps(result, allow_nan=False))
    return 2 if result["status"] in {"invalid_data", "insufficient_data"} else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

La entrada contiene `unit`, `periodSeconds` y `points`; cada punto incluye una marca de tiempo Unix en UTC y un valor finito no negativo. Proporcione al menos 30 puntos de referencia además de la observación. Las proporciones deben estar entre 0 y 1. El recopilador debe comprobar los errores de API, la paginación y los resultados parciales y seleccionar una única serie agregada claramente definida.

La observación se excluye del conjunto de referencia usado para la mediana y MAD. Los márgenes son **umbrales ilustrativos**, no un modelo entrenado ni un sistema de predicción estacional. La herramienta ordena los puntos y rechaza los intervalos sin datos, los duplicados y las observaciones antiguas. `review_required` no autoriza a ejecutar cambios; `actionTaken` sigue siendo `none`.

Al adaptar la recopilación de CloudWatch, use el espacio de nombres y las dimensiones reales de la métrica y ordene conjuntamente los pares `Timestamps` y `Values`. No suponga que `Values[-1]` es el dato más reciente con el orden predeterminado de respuesta. `RequestCount` y las métricas específicas de grupos de destino requieren dimensiones distintas; gestione NextToken, StatusCode y los puntos ausentes.

### Límites de aprobación y ejecución {#approval-and-execution-boundaries}

Una propuesta debe identificar el ARN o espacio de nombres de destino, la revisión de la configuración actual, el diff, las métricas que la sustentan y sus fechas, la caducidad, quién la aprueba y las condiciones para revertirla. Antes de ejecutar cambios, vuelva a comprobar la autorización, la caducidad, la revisión, la capacidad y la salud del destino. Una lista de cadenas permitidas o un ConfigMap de guardrail que no se utiliza para controlar la ejecución no impone esas restricciones.

Una interfaz de aprobación necesita verificar realmente la firma de la solicitud, autorizar a quien aprueba, mantener estado persistente, impedir la repetición de solicitudes y gestionar los tiempos de espera. Enviar botones de Slack y esperar a que cambie el estado de un objeto en memoria que nadie modifica no constituye un sistema completo de aprobación. No afirme que un ejecutor sin implementar ha realizado una acción.

Use el [flujo de propuestas restringidas y ejecución opcional del capítulo 02](02-infrastructure-advanced.md) para los cambios de NLB. No sobrescriba todos los listeners ni restablezca una distribución arbitraria de 100/0 solo porque no se detectó una anomalía. Un peso cero de NLB cierra las conexiones existentes tras un breve intervalo, a diferencia de los ajustes habituales entre pesos distintos de cero.

Para la entrega progresiva, use los servicios, el enrutamiento y las AnalysisTemplates de la [guía validada de Argo Rollouts](../gitops/argocd/05-traffic-management.md). Alinee las métricas específicas del canary, los argumentos, los espacios de nombres, el tratamiento de resultados vacíos o NaN y las condiciones de fallo. Un fallo del análisis no revierte automáticamente los cambios en la base de datos, y los ajustes de pausa o cancelación no resuelven todos los problemas de recuperación.

## Referencias {#references}

- [Seguridad de Atlantis](https://www.runatlantis.io/docs/security.html)
- [Política del lado del servidor de Atlantis](https://www.runatlantis.io/docs/server-side-repo-config.html)
- [Credenciales dinámicas de AWS de HCP Terraform](https://developer.hashicorp.com/terraform/cloud-docs/dynamic-provider-credentials/aws-configuration)
- [Disparadores de ejecución de HCP Terraform](https://developer.hashicorp.com/terraform/cloud-docs/workspaces/settings/run-triggers)
- [Sentinel tfrun](https://developer.hashicorp.com/terraform/cloud-docs/policy-enforcement/import-reference/tfrun)
- [Flux ImageUpdateAutomation v1](https://github.com/fluxcd/image-automation-controller/blob/v1.2.5/docs/spec/v1/imageupdateautomations.md)
- [Revisión de código de GitHub Copilot](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/request-a-code-review/use-code-review)
- [Cuestionario del capítulo](../quizzes/ops/05-gitops-automation-quiz.md)

< [Anterior: Varios clústeres](04-gitops-multi-cluster.md) | [Contenido](README.md) | [Siguiente: Escalado](06-scaling-strategies.md) >
