# Automatización GitOps: Atlantis, HCP Terraform, Flux, AIOps

> **Base de revisión**: Atlantis 0.47.1 / chart 6.15.0, HCP Terraform Provider 0.80.0, Sentinel 0.41.0, Flux 2.9.5 (el pin de Flux se actualizó al parche 2.9.6 el 12 de octubre de 2026 después de revisar las notas de lanzamiento; no se volvió a ejecutar)\
> **Última revisión**: 11 de septiembre de 2026. Se comprobó con CLI locales, charts, esquemas y dobles de prueba. No se realizaron comentarios reales en PR, Terraform apply, creación de recursos HCP, despliegue de clúster ni llamadas externas de IA.

< [Anterior: Multi-Cluster](04-gitops-multi-cluster.md) | [Contenido](README.md) | [Siguiente: Scaling](06-scaling-strategies.md) >

Separe la ejecución de infraestructura de la reconciliación de aplicaciones. No permita que Atlantis y HCP Terraform se ejecuten simultáneamente contra el mismo estado, ni que Flux y Argo CD compitan por los mismos campos de Kubernetes.

| Herramienta | Responsabilidad | Requisitos previos independientes |
|---|---|---|
| Atlantis | Ejecutar planes/applies de Terraform basados en PR | Runtime, credenciales, estado, bloqueos y autorización de comandos |
| HCP Terraform | Workspaces/runs/estado administrados y colaboración | Conexión VCS, agentes, políticas y permisos de workspace |
| Flux | Reconciliar el estado de Kubernetes/Helm desde fuentes | Identidades de controlador, RBAC de tenant y permisos de repositorio |
| Análisis AIOps | Resumir observaciones y proponer respuestas | Datos validados, aprobación y un ejecutor limitado por separado |

## 1. Atlantis en EKS

Atlantis ejecuta Terraform desde pull requests. **La planificación puede ejecutar providers, fuentes de datos externas y comandos personalizados.** Exigir aprobación para apply no hace seguro un plan no confiable. Este ejemplo es para un repositorio privado de infraestructura controlado y un equipo de operaciones aprobado, con PR de forks y planificación automática deshabilitados.

### Requisitos previos de identidad e instalación

- Configure la asociación de Pod Identity de EKS Auto Mode para el namespace/ServiceAccount `atlantis`. No la mezcle con una anotación IRSA. Los nodos convencionales necesitan la configuración compatible de agente y SDK.
- Limite el acceso a las claves exactas de estado y `.tflock`, las claves KMS necesarias y los recursos administrados. Distinga lectura/escritura de objetos de estado de lectura/escritura/eliminación de objetos de bloqueo. `eks:*` amplio, creación de roles IAM y PassRole no constituyen una política universal de mínimo privilegio.
- Restrinja las asunciones de roles a ARN exactos y la confianza prevista. Use condiciones de etiquetas de solicitud compatibles de clúster/namespace/ServiceAccount para Pod Identity.
- Proteja las credenciales y el JSON de planes sensibles de la salida de PR. Terraform `sensitive=true` no evita que los valores se almacenen en el estado.

El runtime necesita acceso a AWS, Git, registros de providers/módulos y API privadas de EKS. No dependa de scripts de instalación no verificados ni de herramientas ausentes de la imagen. Terraform 1.15.7 debe estar presente u obtenerse mediante la ruta de descarga permitida para `defaultTFVersion`.

### Valores Helm versionados

Si `auto-gp3` no existe ya, prepare una StorageClass de Auto Mode como esta. Su provisioner difiere del EBS CSI convencional. Use una alternativa apropiada en un modo de clúster diferente.

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

Prepare estos Secrets en el namespace `atlantis` utilizando el mecanismo de gestión de secretos aprobado. No incluya valores reales en Git ni en valores Helm.

| Secret | Claves requeridas |
|---|---|
| `atlantis-vcs` | `github-token`, `webhook-secret` |
| `atlantis-web-auth` | `username`, `password` |

Conceda al bot/token de GitHub los permisos necesarios de repositorio, PR y consulta de equipo, y rótelo. Sustituya `platform` por el equipo de organización autorizado real. Use la lista de permitidos de equipos de Atlantis en vez de hacer coincidencias de subcadenas de nombres de usuario en un shell hook.

```yaml
# fixtures/atlantis-values.yaml
fullnameOverride: atlantis
replicaCount: 1
image:
  repository: ghcr.io/runatlantis/atlantis
  tag: v0.47.1
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
  --version 6.15.0 --namespace atlantis --create-namespace \
  --kube-context "$ATLANTIS_CONTEXT" --values atlantis-values.yaml
```

Estos valores crean solamente un ClusterIP. Conecte `atlantis.example.com` y `/events` mediante un proxy HTTPS/Ingress aprobado, y luego configure el secreto de webhook de GitHub correspondiente. La verificación de webhook y la autenticación de la interfaz web son distintas. No amplíe la ruta de eventos a una omisión general de autenticación.

El chart 6.15.0 usa `orgAllowlist`, `volumeClaim`, un mapa `environment` y `containerSecurityContext`. El PVC grabable contiene datos de checkout, plan y bloqueo de servidor; no lo superponga con un ConfigMap de solo lectura. Aumentar las réplicas por sí solo no hace altamente disponible un despliegue con un único PVC RWO/BoltDB. Gestione la retención, copia de seguridad, recuperación y eventual limpieza de volúmenes retenidos.

### Política de servidor y proyectos de repositorio

El `repoConfig` incorporado pertenece al servidor. `allowed_overrides: []` y `allow_custom_workflows: false` impiden que un PR cambie los requisitos de aprobación o los comandos de ejecución. Configure por separado la protección de ramas de GitHub y las comprobaciones obligatorias. `approved` no implica inherentemente dos aprobaciones distintas y actuales del último commit.

Exigir el propio apply como requisito para `mergeable` puede crear una dependencia circular. Alinee las dependencias de plan/comprobación/revisión/apply con las reglas del repositorio. Este ejemplo usa comandos explícitos `atlantis plan -p ...`; revise y vuelva a planificar los cambios realizados después de la aprobación.

Coloque este archivo en la raíz del repositorio. Cada directorio de proyecto usa la raíz correspondiente del [capítulo 01](01-infrastructure-setup.md), con su propio backend/estado y `backend.hcl` y `terraform.tfvars` revisados.

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

Revise y aplique los cambios de red antes de planificar/revisar/aplicar los cambios de clúster y plataforma. `depends_on` no transmite salidas de estado remoto ni actualiza automáticamente un plan descendente guardado previamente. Vuelva a planificar los cambios descendentes cuando cambien las dependencias.

```text
atlantis plan -p network-prod
atlantis apply -p network-prod
atlantis plan -p cluster-prod
atlantis apply -p cluster-prod
atlantis plan -p platform-prod
atlantis apply -p platform-prod
```

Estos son comandos de comentarios de PR. El flujo ordinario de Atlantis es **plan en el PR → cumplir los requisitos de aprobación → aplicar ese plan guardado → fusionar**. Fusionar por sí solo no aplica infraestructura. `automerge` es una opción independiente para fusionar después de applies exitosos.

Las etapas integradas `plan`/`apply` usan el archivo de plan administrado por Atlantis. Los comandos personalizados deben respetar `$PLANFILE`. No lo sustituya por un `-out=tfplan` independiente ni pase valores nuevos de `-var-file` al aplicar un plan guardado. Los archivos de plan y el JSON pueden contener datos sensibles.

### Bloqueos, políticas y manejo de fallos

Los bloqueos de PR/proyecto/workspace de Atlantis difieren de los bloqueos de estado del backend de Terraform. La base de datos de servidor predeterminada actual es BoltDB; las configuraciones Redis compatibles requieren un diseño independiente. No llame a DynamoDB la base de datos de bloqueo predeterminada de Atlantis ni invente ConfigMaps `lock_groups`/`apply_priority`.

`atlantis unlock` **elimina** un bloqueo; no es una consulta. Compruebe primero los runs activos, planes guardados y bloqueos de estado. `atlantis lock`, `atlantis locks` y `unlock --force` no son comandos generales de PR en la versión de este ejemplo. Use la interfaz compatible o la API autenticada para inspeccionar bloqueos.

Buscar en el código fuente y contar recursos en el estado actual no valida toda la infraestructura planificada. Considere módulos, fuentes de datos, providers y valores de crear/actualizar/eliminar/desconocidos. Convertir operaciones fallidas de fmt/validate/policy/API en advertencias o `|| true` elimina la compuerta.

## 2. HCP Terraform

Terraform Cloud ahora se llama **HCP Terraform**. Es una alternativa a Atlantis con capacidades de workspace/run/estado/política. Compruebe el plan y contrato actuales para funciones, precios, concurrencia, agentes y Sentinel. El hosting administrado sigue requiriendo una configuración deliberada de VCS, permisos, red y aprobaciones.

### Workspaces y credenciales dinámicas de AWS

Este ejemplo presupone una organización/proyecto existente, conexión OAuth de VCS y **agent pool** con acceso a red privada. La ejecución por agente requiere un plan elegible y una versión compatible del agente. No suponga que un runner remoto público puede llegar directamente a una API privada de EKS.

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

Esta raíz configura recursos HCP. Proteja su backend/estado por separado de los workspaces de infraestructura. Antes de usar estado administrado por HCP para una raíz existente, decida la propiedad y migre deliberadamente su backend S3 original. No aplique el mismo estado desde dos sistemas de ejecución.

AWS ya debe tener el provider OIDC `app.terraform.io` y roles limitados de plan/apply. Restrinja la audiencia/sujeto de confianza a la organización/proyecto/workspace exacto y a `run_phase:plan` o `run_phase:apply`. Las variables `TFC_AWS_*` son identificadores de roles, no claves de acceso de larga duración almacenadas. Verifique la compatibilidad de credenciales dinámicas en las versiones reales de provider y agente.

`queue_all_runs=false` retiene los runs activados por VCS durante la configuración inicial del workspace. No es un interruptor permanente de deshabilitación de ejecución después del primer run manual.

### Disparadores de run y salidas compartidas

Un apply ascendente exitoso pone en cola un run descendente. **`auto_apply_run_trigger` es independiente de `auto_apply` ordinario.** Ambos son falsos aquí, lo que requiere revisión antes de apply. Un disparador no es ni prueba de que todas las dependencias están listas ni un mecanismo de transferencia de salidas.

El ejemplo no comparte globalmente el estado del workspace. Si deben consumirse salidas, configure consumidores/permisos aprobados y considere `tfe_outputs`. Las credenciales capaces de leer `terraform_remote_state` pueden acceder al estado sensible completo, no solo a las salidas mostradas por la fuente de datos. Conecte el acceso a salidas y las entradas de módulo según el diseño real.

### Políticas Sentinel

Estas son tres **políticas de ejemplo** probadas con Sentinel 0.41.0, no programas Python. Se requieren un conjunto de políticas, workspaces objetivo y configuración de aplicación antes de que puedan bloquear runs de HCP.

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

Comprobar `tags_all` incluye etiquetas predeterminadas de AWS Provider. Este ejemplo comprueba acciones create/update para los tipos de recursos listados y excluye la eliminación. Las etiquetas requeridas ausentes, vacías, null o desconocidas no pasan. No cubre todos los tipos de recursos AWS.

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

Esto se aplica a instancias EC2 y grupos de nodos administrados con `instance_types` especificados directamente. Los grupos solo con launch template, los NodePools de Auto Mode y otros servicios de cómputo requieren políticas adicionales. Una lista de tipos vacía o desconocida no se trata como un conjunto vacío aprobado.

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

Use `tfrun.cost_estimate`, no una ruta inexistente como `tfplan.workspace`. El ejemplo permite una estimación mensual proporcionada de hasta 5.000, rechazando valores ausentes, negativos, NaN e infinitos. No puede garantizar un límite completo de facturación de AWS que cubra recursos no compatibles, tráfico e infraestructura existente.

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

Adjunte el conjunto de políticas a los workspaces previstos y separe la administración de políticas de las operaciones de recursos. Una regla llamada simplemente `soft_main` no cambia la aplicación a soft-mandatory. No convierta evaluaciones fallidas o errores de API en éxito.

## 3. Flux

Esta sección usa la [guía de Flux 2.9.6](../gitops/02-fluxcd.md). Argo CD y Flux reconcilian estado declarativo. Argo CD también tiene varios componentes; Flux no es universalmente más ligero ni más aislado. La separación de namespaces por sí sola no completa la autorización de tenant.

Los controladores de reflector y automatización de imágenes son **componentes opcionales**. Bootstrap realiza commits en Git e instala controladores. Verifique la suma de comprobación del CLI, la versión compatible de Kubernetes, kubecontext y el acceso al repositorio antes de ejecutarlo.

```bash
flux check --pre
flux bootstrap github \
  --owner=REPLACE_ORG --repository=fleet-infra --branch=main \
  --path=clusters/production --version=v2.9.6 \
  --components-extra=image-reflector-controller,image-automation-controller
```

Proporcione de forma segura credenciales autorizadas de GitHub. No agregue `--personal` a un ejemplo de organización. Distinga los archivos `flux-system` predeterminados generados por bootstrap de los directorios de infraestructura/apps que agregue usted mismo.

### Automatización de imágenes y aprobación de Git

El ejemplo requiere un Secret de escritura Git preparado, credenciales de lectura de ECR en image-reflector-controller mediante Pod Identity/IRSA, y la Kustomization/HelmRelease de Flux que despliega la aplicación. Estos son independientes del rol de extracción de imagen del nodo. No combine sin cuidado `provider: aws` con una ruta de autenticación de secreto de registro diferente.

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

La política presupone **versiones semver inmutables publicadas después de la aprobación**. Las etiquetas únicas SHA/build del [capítulo de CI](03-ci-pipelines.md) no coinciden con ella. Un proceso de promoción independiente debe etiquetar el digest de índice aprobado como una versión, o la política debe usar un esquema de build revisado y monótonamente creciente de un sistema CI.

```yaml
# fixtures/flux-values.yaml
# apps/production/application/values.yaml -- actual Helm values file
# Replace repository and initial digest with the already approved application.
image:
  repository: REPLACE_ACCOUNT.dkr.ecr.ap-northeast-2.amazonaws.com/docs-ci/application # {"$imagepolicy": "flux-system:application:name"}
  tag: "1.0.0" # {"$imagepolicy": "flux-system:application:tag"}
  digest: sha256:REPLACE_APPROVED_DIGEST # {"$imagepolicy": "flux-system:application:digest"}
```

El chart real de la aplicación debe usar `image.repository`, `tag` y `digest` al construir la URI de imagen del contenedor. Agregar un valor de digest no hace que un chart existente lo consuma. Compruebe que el manifiesto renderizado apunte al digest aprobado. Alinee las rutas Setters, los marcadores de política y el nombre de GitRepository.

La plantilla de commit actual de ImageUpdateAutomation usa **`.Changed`**. No la sustituya por la eliminada `.Updated`. La automatización realiza push a su rama dedicada `flux/image-updates`; la creación y aprobación de PR en main requieren otro workflow. Alinee los permisos de escritura Git y la protección de ramas. La selección de etiquetas no sustituye la verificación de vulnerabilidades/firmas.

### Fuentes, Helm y notificaciones

- Los ejemplos actuales usan las API v1 de `GitRepository`, `OCIRepository`, `Bucket` e imágenes. HelmRelease es v2; su CRD actual admite tanto `test.enable` como `test.timeout`. Valide juntos las versiones/valores del chart y los CRD.
- Kustomization `dependsOn` espera la condición Ready del objeto Flux referenciado. Configure wait/healthChecks para observar la salud de la carga de trabajo; no es una barrera global entre clústeres.
- No permita que Terraform Helm Provider y Flux posean simultáneamente el mismo release Helm. Migrar la propiedad de instalación de Argo CD requiere una migración deliberada de estado/configuración.
- No exponga buckets de estado de Terraform como fuentes ordinarias de manifiestos Flux. Use un bucket de artefactos de manifiestos independiente con acceso limitado por prefijo, y evite patrones de ignore que incluyan `.git` en los artefactos.
- Almacene los webhooks de notificación en Secrets y verifique el tipo de receptor y autenticación reales. Pruebe los eventos seleccionados por gravedad y filtros. No presente una interfaz no instalada o una integración retirada como parte de la instalación predeterminada.

La [guía de Flux](../gitops/02-fluxcd.md) contiene ejemplos completos de source/Kustomization/HelmRelease/notificación.

## 4. AIOps: de la observación a propuestas revisables

### Revisión de PR asistida por LLM

Configure la revisión de código de GitHub Copilot mediante sus ajustes compatibles de revisor/revisión automática, con los permisos de repositorio necesarios y el plan disponible. Un endpoint ficticio como `api.copilot.example.com` no es un ejemplo de API ejecutable.

Una integración LLM personalizada debe implementar el contrato actual de API/modelo/SDK del servicio real, timeout, manejo de errores HTTP y validación de salida. Los diffs y los nombres de archivo son datos no confiables. Pase valores estructurados en vez de interpolarlos en cadenas de shell, JavaScript o JSON. Las instrucciones dentro del contenido revisado no otorgan autoridad de ejecución.

Informe del truncamiento y los fallos de API. No entregue secretos a PR externos de forks ni convierta una respuesta de modelo por sí sola en aprobación, merge o apply. Defina la divulgación permitida de código fuente y el alcance de coste antes de usar un servicio externo. No se llamó a ningún servicio externo de IA durante la revisión de este documento.

### Unidades métricas y calidad de datos

Un promedio de contador de CPU no es utilización de CPU. `rate(container_cpu_usage_seconds_total[...])` produce núcleos de CPU; `averageUtilization` de HPA es un porcentaje de las **solicitudes** de CPU. No compare ese porcentaje con RPS. Resuelva el scaleTargetRef del HPA y la propiedad real del Pod en vez de suponer que el HPA y el Deployment comparten un nombre.

El p95 temporal de RPS difiere de un cuantil de histograma de duración de solicitudes:

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

Haga coincidir los nombres/etiquetas de métricas con la recopilación real. Series ausentes, tráfico cero, NaN, observaciones obsoletas y brechas de recopilación no son evidencia de salud. Combine tráfico, errores, latencia y capacidad. La CPU media por sí sola no puede establecer un “objetivo óptimo de HPA”; importan las pruebas de carga, los SLO y el comportamiento de reducción de escala.

### Ejemplo ejecutable de solo análisis

Esta herramienta lee desde stdin una serie JSON de una sola métrica ya normalizada y emite **solo un informe de recomendación**. No cambia API, HPA, NLB, Git ni Slack. Estar dentro de la línea base no establece la salud de la aplicación.

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

La entrada contiene `unit`, `periodSeconds` y `points`; cada punto tiene una marca de tiempo UTC Unix y un valor no negativo finito. Proporcione al menos 30 puntos de línea base más la observación. Las proporciones están en 0–1. El recopilador debe comprobar errores de API, paginación y resultados parciales y seleccionar una serie agregada claramente definida.

La observación se excluye de la línea base de mediana/MAD. Los márgenes son **umbrales ilustrativos**, no un modelo entrenado ni un sistema de predicción estacional. La herramienta ordena los puntos y rechaza brechas, duplicados y observaciones obsoletas. `review_required` no es permiso para ejecutar; `actionTaken` sigue siendo `none`.

Al adaptar la recopilación de CloudWatch, use el namespace/dimensiones reales de la métrica y ordene los `Timestamps`/`Values` emparejados. No suponga que `Values[-1]` es el más reciente con el orden de respuesta predeterminado. `RequestCount` y las métricas específicas de grupo de destino tienen contratos de dimensiones distintos; maneje NextToken, StatusCode y puntos ausentes.

### Límites de aprobación y ejecución

Una propuesta debe identificar el ARN/namespace objetivo, la revisión de configuración actual, diff, evidencia/tiempo de métricas, expiración, aprobador y condiciones de rollback. Antes de la ejecución, vuelva a comprobar autorización, expiración, revisión, capacidad y salud del destino. Una lista de permitidos de cadenas o un ConfigMap de guardrail no utilizado de otro modo no es un mecanismo de aplicación.

Una interfaz de aprobación necesita verificación real de firma de solicitud, autorización de aprobador, estado persistente, protección contra repetición y manejo de timeout. Enviar botones de Slack y luego esperar el estado de un objeto en memoria sin modificar no es un sistema de aprobación completo. No afirme que un ejecutor no implementado realizó una acción.

Use el [flujo de propuesta restringida/ejecución opcional del capítulo 02](02-infrastructure-advanced.md) para cambios de NLB. No sobrescriba cada listener ni restaure una división arbitraria de 100/0 simplemente porque no se detectó ninguna anomalía. El peso cero de NLB cierra las conexiones existentes tras un período corto, a diferencia de los ajustes ordinarios de peso distinto de cero.

Para entrega progresiva, use los servicios, enrutamiento y AnalysisTemplates de la [guía validada de Argo Rollouts](../gitops/argocd/05-traffic-management.md). Alinee métricas, argumentos, namespaces, manejo de vacío/NaN y condiciones de fallo específicas del canary. El fallo de análisis no revierte automáticamente los cambios de base de datos, y los ajustes de pausa/abort no resuelven todos los problemas de recuperación.

## Referencias

- [Seguridad de Atlantis](https://www.runatlantis.io/docs/security.html)
- [Política del lado del servidor de Atlantis](https://www.runatlantis.io/docs/server-side-repo-config.html)
- [Credenciales dinámicas de AWS de HCP Terraform](https://developer.hashicorp.com/terraform/cloud-docs/dynamic-provider-credentials/aws-configuration)
- [Disparadores de run de HCP Terraform](https://developer.hashicorp.com/terraform/cloud-docs/workspaces/settings/run-triggers)
- [Sentinel tfrun](https://developer.hashicorp.com/terraform/cloud-docs/policy-enforcement/import-reference/tfrun)
- [Flux ImageUpdateAutomation v1](https://github.com/fluxcd/image-automation-controller/blob/v1.2.5/docs/spec/v1/imageupdateautomations.md)
- [Revisión de código de GitHub Copilot](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/request-a-code-review/use-code-review)
- [Cuestionario del capítulo](../quizzes/ops/05-gitops-automation-quiz.md)

< [Anterior: Multi-Cluster](04-gitops-multi-cluster.md) | [Contenido](README.md) | [Siguiente: Scaling](06-scaling-strategies.md) >
