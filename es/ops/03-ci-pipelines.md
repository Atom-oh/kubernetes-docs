# Pipelines de CI basadas en EKS: compilación y publicación en ECR

> **Baseline de revisión**: GitLab Runner 19.3.1 / chart 0.92.1, ARC 0.15.0, runner 2.337.0, Docker 29.8.0, Trivy 0.76.0, Node 24
> **Última revisión**: 16 de octubre de 2026. Se comprobaron los esquemas de Helm/TOML/CI, dobles locales de prueba y una pequeña aplicación independiente de Next.js. No se ejecutó ningún trabajo de CI real, publicación en el registro ni despliegue en AWS.

< [Anterior: NLB Blue/Green](02-infrastructure-advanced.md) | [Tabla de contenido](README.md) | [Siguiente: ArgoCD Multi-Cluster](04-gitops-multi-cluster.md) >

Esta guía usa un **clúster de CI dedicado para los trabajos de publicación de confianza y protegidos**. El Docker-in-Docker que se muestra más abajo requiere privilegios. Un Pod separado no constituye por sí solo un límite de seguridad completo; no enrutes a estos runners solicitudes de cambios públicas o no confiables ni les concedas credenciales de publicación de AWS heredadas. El ejemplo de GitHub ejecuta las pruebas de solicitudes de cambios en runners alojados por GitHub y obtiene credenciales OIDC solo en los trabajos de publicación activados por push.

El contrato de la aplicación es un proyecto npm con `package-lock.json`, scripts `lint` y `test` funcionales y un Dockerfile. Adapta esos comandos a la aplicación. Las API de GitHub/GitLab, los registros, los repositorios de paquetes y los endpoints de AWS siguen siendo dependencias de red, aunque los runners se ejecuten en EKS.

## 1. Configuración del repositorio de ECR

Usa etiquetas inmutables para las aplicaciones y coloca las referencias mutables de caché de BuildKit en un **repositorio distinto**. Las etiquetas únicas basadas en el commit, la ejecución y el trabajo reducen las colisiones; despliega por el digest aprobado. Que una etiqueta tenga forma de SHA no la hace inmutable. Si vuelves a intentar una compilación ya publicada, reutiliza su digest verificado o crea un nuevo identificador de compilación en lugar de sobrescribir una etiqueta de lanzamiento.

El ejemplo de Terraform supone que ya existen el clúster de CI de EKS y el proveedor OIDC de GitHub de la cuenta. Separa el rol de caché S3 del administrador de GitLab del rol de publicación en ECR del Pod de compilación. Los Pods de trabajo de ARC no tienen un rol de publicación de Pod Identity: el workflow de confianza usa su propio rol OIDC de GitHub.

```hcl
# main.tf
terraform {
  required_version = ">= 1.10.0"
  required_providers {
    aws = { source = "hashicorp/aws", version = "6.69.1" }
  }
}
provider "aws" { region = var.region }
data "aws_caller_identity" "current" {}
data "aws_eks_cluster" "ci" { name = var.cluster_name }
locals {
  tags = { Project = var.project_name, ManagedBy = "terraform" }
}
resource "aws_ecr_repository" "application" {
  name                 = "${var.project_name}/application"
  image_tag_mutability = "IMMUTABLE"
  encryption_configuration { encryption_type = "AES256" }
  tags = local.tags
}
resource "aws_ecr_repository" "build_cache" {
  name                 = "${var.project_name}/build-cache"
  image_tag_mutability = "MUTABLE"
  encryption_configuration { encryption_type = "AES256" }
  tags = local.tags
}
# This minimal rule leaves tagged releases alone. Preview before applying any
# additional tagged-image retention rules; ECR does not know current EKS usage.
resource "aws_ecr_lifecycle_policy" "application" {
  repository = aws_ecr_repository.application.name
  policy = jsonencode({ rules = [{
    rulePriority = 1
    description  = "Expire untagged images after 14 days"
    selection    = { tagStatus = "untagged", countType = "sinceImagePushed", countUnit = "days", countNumber = 14 }
    action       = { type = "expire" }
  }] })
}
resource "aws_ecr_lifecycle_policy" "build_cache" {
  repository = aws_ecr_repository.build_cache.name
  policy = jsonencode({ rules = [{
    rulePriority = 1
    description  = "Cache is disposable, not a release retention policy"
    selection    = { tagStatus = "any", countType = "sinceImagePushed", countUnit = "days", countNumber = 14 }
    action       = { type = "expire" }
  }] })
}
resource "aws_s3_bucket" "runner_cache" {
  bucket_prefix = "docs-ci-cache-"
  tags          = local.tags
}
resource "aws_s3_bucket_public_access_block" "runner_cache" {
  bucket                  = aws_s3_bucket.runner_cache.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
resource "aws_s3_bucket_server_side_encryption_configuration" "runner_cache" {
  bucket = aws_s3_bucket.runner_cache.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}
resource "aws_s3_bucket_lifecycle_configuration" "runner_cache" {
  bucket = aws_s3_bucket.runner_cache.id
  rule {
    id     = "runner-cache"
    status = "Enabled"
    filter { prefix = "runner/" }
    expiration { days = 14 }
  }
}
resource "aws_iam_role" "gitlab" {
  for_each    = toset(["manager", "build"])
  name_prefix = "gitlab-${each.key}-"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "pods.eks.amazonaws.com" }
      Action    = ["sts:AssumeRole", "sts:TagSession"]
      Condition = { StringEquals = {
        "aws:RequestTag/eks-cluster-arn"            = data.aws_eks_cluster.ci.arn
        "aws:RequestTag/kubernetes-namespace"       = "gitlab-ci"
        "aws:RequestTag/kubernetes-service-account" = "gitlab-${each.key}"
      } }
    }]
  })
  tags = local.tags
}
resource "aws_eks_pod_identity_association" "gitlab" {
  for_each        = aws_iam_role.gitlab
  cluster_name    = var.cluster_name
  namespace       = "gitlab-ci"
  service_account = "gitlab-${each.key}"
  role_arn        = each.value.arn
}
resource "aws_iam_policy" "ecr_publish" {
  name_prefix = "docs-ci-ecr-"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = "ecr:GetAuthorizationToken", Resource = "*", Condition = { StringEquals = { "aws:RequestedRegion" = var.region } } },
      {
        Effect   = "Allow"
        Action   = ["ecr:BatchCheckLayerAvailability", "ecr:GetDownloadUrlForLayer", "ecr:BatchGetImage", "ecr:PutImage", "ecr:InitiateLayerUpload", "ecr:UploadLayerPart", "ecr:CompleteLayerUpload"]
        Resource = [aws_ecr_repository.application.arn, aws_ecr_repository.build_cache.arn]
      }
    ]
  })
}
resource "aws_iam_role_policy_attachment" "gitlab_build" {
  role       = aws_iam_role.gitlab["build"].name
  policy_arn = aws_iam_policy.ecr_publish.arn
}
resource "aws_iam_role_policy" "gitlab_manager_cache" {
  role = aws_iam_role.gitlab["manager"].name
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"], Resource = "${aws_s3_bucket.runner_cache.arn}/runner/*" },
      { Effect = "Allow", Action = "s3:GetBucketLocation", Resource = aws_s3_bucket.runner_cache.arn }
    ]
  })
}
# Reuse the account's existing GitHub OIDC provider; do not create a duplicate.
resource "aws_iam_role" "github_publish" {
  name_prefix = "github-ci-publish-"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = var.github_oidc_provider_arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = { "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com" }
        StringLike = { "token.actions.githubusercontent.com:sub" = [
          "repo:${var.github_repository}:ref:refs/heads/main",
          "repo:${var.github_repository}:ref:refs/tags/v*"
        ] }
      }
    }]
  })
  tags = local.tags
}
resource "aws_iam_role_policy_attachment" "github_publish" {
  role       = aws_iam_role.github_publish.name
  policy_arn = aws_iam_policy.ecr_publish.arn
}
```

```hcl
# variables.tf
variable "region" {
  type    = string
  default = "ap-northeast-2"
}
variable "project_name" {
  type    = string
  default = "docs-ci"
}
variable "cluster_name" { type = string }
variable "github_oidc_provider_arn" {
  description = "Existing account OIDC provider for token.actions.githubusercontent.com"
  type        = string
}
variable "github_repository" {
  description = "Exact owner/repository; protect main and v* release tags in GitHub"
  type        = string
  validation {
    condition     = can(regex("^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", var.github_repository))
    error_message = "Supply an exact owner/repository, without wildcards."
  }
}
```

```hcl
# outputs.tf
output "application_repository" { value = aws_ecr_repository.application.name }
output "application_url" { value = aws_ecr_repository.application.repository_url }
output "cache_repository" { value = aws_ecr_repository.build_cache.name }
output "cache_url" { value = aws_ecr_repository.build_cache.repository_url }
output "runner_cache_bucket" { value = aws_s3_bucket.runner_cache.id }
output "github_publish_role_arn" { value = aws_iam_role.github_publish.arn }
```

Usa un backend y un estado protegidos y distintos para esta raíz, y revisa el plan antes de aplicarlo. Incluye la salida del bucket de caché en los valores de GitLab y los nombres de los repositorios y el ARN del rol en las variables de CI. Las asociaciones de EKS Pod Identity no crean cuentas de servicio; también se necesitan las cuentas coincidentes que aparecen a continuación.

### Retención, análisis y replicación

- Las listas de prefijos o patrones de ciclo de vida son condiciones **AND aplicadas a las etiquetas de una imagen**, no una lista OR de ramas. ECR no sabe qué imágenes están ejecutando los clústeres de EKS ni qué versiones necesitas para una reversión. Previsualiza las políticas y los requisitos de retención antes de añadir reglas que eliminen imágenes etiquetadas.
- La configuración de análisis del registro abarca toda la cuenta y la región. Los eventos de análisis básico de ECR y los hallazgos de Inspector mejorado tienen esquemas distintos. El análisis continuo tiene prioridad sobre una regla coincidente de análisis al publicar; una regla continua amplia `*` no deja una regla de desarrollo más específica en modo de análisis solo al publicar.
- High y Critical son valores de gravedad alternativos, no dos campos que deban ser positivos a la vez. Un análisis fallido o incompleto no significa que la imagen esté limpia. La puerta de Trivy de CI que se muestra más adelante es independiente de las notificaciones de ECR/Inspector.
- Para extraer imágenes entre cuentas se necesitan tanto la política de recursos del repositorio como los permisos de identidad del llamador, incluido el acceso al token de autorización de ECR. Prefiere roles específicos en lugar de conceder acceso a todos los principales de una cuenta.
- La replicación entre cuentas también requiere permisos en el registro de destino. Es asíncrona y no completa automáticamente las imágenes existentes ni copia todos los ajustes de ciclo de vida, análisis o repositorio.

Consulta la [guía revisada de Amazon ECR](../container-registry/02-amazon-ecr.md) para conocer las alternativas completas a nivel de registro y las [prácticas recomendadas para registros](../container-registry/04-best-practices.md) para promoción, retención y firma. No permitas que cada stack de aplicación sobrescriba una configuración de registro compartida.

## 2. GitLab Runner en EKS

### Cuentas de servicio y registro de runners protegidos

Usa el namespace y las cuentas que se muestran a continuación. Crea **dos runners de proyecto en el servidor**, con acceso protegido y las etiquetas `eks-ci-amd64` y `eks-ci-arm64`; después, crea sus Secrets de token de autenticación. Con el flujo moderno de tokens de autenticación, configura las etiquetas, la protección y run-untagged en GitLab; no des por hecho que las antiguas opciones de registro o los valores de Helm los actualizarán.

```yaml
# gitlab-prerequisites.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: gitlab-ci
  labels:
    pod-security.kubernetes.io/enforce: privileged
---
# No Kubernetes API token is needed by build jobs. AWS Pod Identity uses its
# own projected token, provided by the configured association.
apiVersion: v1
kind: ServiceAccount
metadata:
  name: gitlab-build
  namespace: gitlab-ci
automountServiceAccountToken: false

---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: gitlab-manager
  namespace: gitlab-ci
```

Guarda los tokens fuera de Git y de los valores/estado de Terraform. El chart usa los Secrets existentes `gitlab-runner-auth-amd64` y `gitlab-runner-auth-arm64` en `gitlab-ci`. Espera las claves `runner-token` y la clave de compatibilidad `runner-registration-token` (vacía). Usa archivos protegidos o un flujo de secretos externos; no pongas los valores de los tokens en la línea de comandos del shell:

```bash
# Repeat for the ARM runner using its own protected token file and Secret name.
kubectl create secret generic gitlab-runner-auth-amd64 -n gitlab-ci \
  --from-file=runner-token=/protected/gitlab-amd64-token \
  --from-literal=runner-registration-token=''
```

Coordina la rotación de tokens con el origen real del secreto y el comportamiento de recarga/reinicio del runner. La cuenta de servicio del administrador necesita acceso a la API de Kubernetes; los Pods de compilación desactivan el token normal de la API de Kubernetes mientras Pod Identity proporciona su propio token de AWS.

### Valores estables de Helm y configuración del runner

La siguiente configuración corresponde a la versión AMD64. Usa el chart versionado, no la versión `bleeding` de una rama de desarrollo. La variante ARM cambia la arquitectura del administrador y del trabajo, y el Secret del token; ambos administradores pueden usar la cuenta de servicio creada previamente.

```yaml
# gitlab-values.yaml
# GitLab Runner chart 0.92.1 / Runner 19.3.1. Trusted protected jobs only.
gitlabUrl: https://gitlab.example.com/
concurrent: 4
checkInterval: 3
rbac:
  create: true
  clusterWideAccess: false
  rules:
    - apiGroups: [""]
      resources: [pods]
      verbs: [create, delete, get, list, watch]
    - apiGroups: [""]
      resources: [pods/attach, pods/exec]
      verbs: [create, delete, get, patch]
    - apiGroups: [""]
      resources: [pods/log]
      verbs: [get, list]
    - apiGroups: [""]
      resources: [secrets]
      verbs: [create, delete, get, update]
    - apiGroups: [""]
      resources: [services]
      verbs: [create, get]
    - apiGroups: [""]
      resources: [serviceaccounts]
      verbs: [get]
    - apiGroups: [""]
      resources: [events]
      verbs: [list, watch]
serviceAccount:
  create: false
  name: gitlab-manager
resources:
  requests: {cpu: 200m, memory: 256Mi}
  limits: {cpu: "1", memory: 512Mi}
nodeSelector:
  workload-type: ci-builder
  kubernetes.io/arch: amd64
tolerations:
  - key: ci-builder
    operator: Equal
    value: "true"
    effect: NoSchedule
service:
  enabled: true
metrics:
  enabled: true
  serviceMonitor:
    enabled: false
runners:
  secret: gitlab-runner-auth-amd64
  config: |
    [[runners]]
      executor = "kubernetes"
      [runners.kubernetes]
        namespace = "gitlab-ci"
        service_account = "gitlab-build"
        automount_service_account_token = false
        image = "docker.io/library/docker@sha256:eccaacfeed644c7de222ff047483568cb988dde95476fbaaf10ea2d04921bb66"
        privileged = true
        poll_interval = 3
        poll_timeout = 600
        cpu_request = "500m"
        cpu_limit = "2"
        memory_request = "1Gi"
        memory_limit = "4Gi"
        helper_cpu_request = "100m"
        helper_memory_request = "128Mi"
        helper_image_autoset_arch_and_os = true
        [runners.kubernetes.node_selector]
          "workload-type" = "ci-builder"
          "kubernetes.io/arch" = "amd64"
        [runners.kubernetes.node_tolerations]
          "ci-builder=true" = "NoSchedule"
        [[runners.kubernetes.volumes.empty_dir]]
          name = "docker-certs"
          mount_path = "/certs/client"
          medium = "Memory"
      [runners.cache]
        Type = "s3"
        Path = "runner"
        Shared = true
        [runners.cache.s3]
          BucketName = "REPLACE_CACHE_BUCKET"
          BucketLocation = "ap-northeast-2"
          AuthenticationType = "iam"
```

`node_tolerations` es un mapa TOML. `poll_interval` consulta si se crearon Pods de Kubernetes; Helm `checkInterval` y runner `check_interval` se refieren a la consulta de trabajos al coordinador. No son equivalentes. La versión del helper corresponde a Runner 19.3.1; la arquitectura se selecciona mediante el selector de nodos explícito, no con una sobreescritura `x86_64-latest` del helper.

Las métricas corresponden al administrador, no a cada Pod de compilación. ServiceMonitor permanece deshabilitado hasta que existan su CRD y la configuración de monitorización. S3 `AuthenticationType=iam` usa la cadena de credenciales del administrador si `RoleARN` no está definido; al establecer `RoleARN` cambia el comportamiento de las credenciales de caché y se necesita una política independiente y revisada.

```bash
# After namespace, accounts, Secrets, IAM associations, and CI nodes are ready.
helm upgrade --install gitlab-amd64 gitlab-runner \
  --repo https://charts.gitlab.io --version 0.92.1 \
  --namespace gitlab-ci --values gitlab-values.yaml
# Use a separate token and replace both amd64 selectors with arm64 in the ARM values.
helm upgrade --install gitlab-arm64 gitlab-runner \
  --repo https://charts.gitlab.io --version 0.92.1 \
  --namespace gitlab-ci --values gitlab-arm64-values.yaml
```

### Imagen de herramientas de CI y pipeline

La imagen estándar de Docker no incluye todos los comandos de AWS que usa el pipeline. Compila, analiza y publica esta imagen de herramientas en un entorno de arranque de confianza para ambas arquitecturas. Asigna a `CI_TOOLS_IMAGE` el digest de índice inmutable aprobado. Alpine 3.24 proporciona AWS CLI para AMD64 y ARM64; registra el digest de la imagen resultante en lugar de suponer que futuras reconstrucciones de paquetes producirán bytes idénticos.

```dockerfile
# Dockerfile.ci-tools
# Build in a trusted bootstrap environment, scan, and publish with an immutable digest.
FROM docker.io/library/docker@sha256:eccaacfeed644c7de222ff047483568cb988dde95476fbaaf10ea2d04921bb66
RUN apk add --no-cache bash aws-cli jq
```

El pipeline usa trabajos matriciales nativos con dependencias de compilación → análisis → publicación 1:1, compatibles con GitLab 19.3. Cada archivo se analiza antes de publicar esa misma imagen. El JSON nativo de Trivy es un artefacto descargable; no se etiqueta incorrectamente como si tuviera el esquema de informe de análisis de contenedores de GitLab. Los archivos de digest finales de cada arquitectura tienen nombres distintos para evitar que el trabajo del manifiesto sobrescriba artefactos.

```yaml
# gitlab-ci.yaml
# The registered runner must be protected and limited to this trusted project.
workflow:
  rules:
    - if: '$CI_PIPELINE_SOURCE == "push" && $CI_COMMIT_REF_PROTECTED == "true" && ($CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH || $CI_COMMIT_TAG =~ /^v[0-9]+\.[0-9]+\.[0-9]+$/)'
    - when: never
stages: [test, build, scan, publish, manifest]
variables:
  AWS_REGION: ap-northeast-2
  ECR_REGISTRY: REPLACE_ACCOUNT.dkr.ecr.ap-northeast-2.amazonaws.com
  ECR_REPOSITORY: docs-ci/application
  ECR_CACHE_REPOSITORY: docs-ci/build-cache
  # Publish Dockerfile.ci-tools first; replace with its approved immutable image URI.
  CI_TOOLS_IMAGE: registry.example.invalid/ci-tools@sha256:REPLACE_DIGEST
  DOCKER_HOST: tcp://docker:2376
  DOCKER_TLS_CERTDIR: /certs
  DOCKER_TLS_VERIFY: "1"
  DOCKER_CERT_PATH: /certs/client

default:
  tags: [eks-ci-amd64]

.native: &native
  tags: [$RUNNER]
  parallel:
    matrix:
      - ARCH: amd64
        RUNNER: eks-ci-amd64
      - ARCH: arm64
        RUNNER: eks-ci-arm64

test:
  stage: test
  image: docker.io/library/node@sha256:2fe369e969550cde8e867afc3fe370b260140cab4a23d467074295b42163d553
  script:
    - npm ci --cache .npm --prefer-offline
    - npm run lint
    - npm test
  cache:
    key:
      prefix: node24-amd64-protected
      files: [package-lock.json]
    paths: [.npm/]

.docker-job:
  image: $CI_TOOLS_IMAGE
  services:
    - name: docker.io/library/docker@sha256:5efed980cba3fc126cf54e21a5a6ff8849d05b6e0623d6e7612f48e9cd6cd17e
      alias: docker
      variables:
        HEALTHCHECK_TCP_PORT: "2376"
  before_script:
    - |
      set -euo pipefail
      for attempt in $(seq 1 60); do
        docker info >/dev/null 2>&1 && break
        sleep 1
      done
      docker info >/dev/null
      aws ecr get-login-password --region "$AWS_REGION" |
        docker login --username AWS --password-stdin "$ECR_REGISTRY"

build:
  <<: *native
  extends: .docker-job
  stage: build
  needs: [test]
  script:
    - |
      set -euo pipefail
      TAG="sha-${CI_COMMIT_SHA}-${CI_PIPELINE_ID}-${CI_JOB_ID}-${ARCH}"
      IMAGE="$ECR_REGISTRY/$ECR_REPOSITORY:$TAG"
      docker buildx create --name ci-builder --driver docker-container --use
      docker buildx build --platform "linux/$ARCH" --load \
        --cache-from "type=registry,ref=$ECR_REGISTRY/$ECR_CACHE_REPOSITORY:${ARCH}-protected" \
        --cache-to "type=registry,ref=$ECR_REGISTRY/$ECR_CACHE_REPOSITORY:${ARCH}-protected,mode=max,image-manifest=true,oci-mediatypes=true" \
        --tag "$IMAGE" .
      docker save "$IMAGE" -o image.tar
      printf 'IMAGE_TAG=%s\n' "$TAG" > build.env
  artifacts:
    paths: [image.tar]
    reports:
      dotenv: build.env
    expire_in: 1 day

scan:
  <<: *native
  stage: scan
  image:
    name: docker.io/aquasec/trivy@sha256:2416d1f74045b57274df1a340eee6b510cacd73c66a6ccb8da092b117eb7d222
    entrypoint: [""]
  needs:
    - job: build
      artifacts: true
      parallel:
        matrix:
          - ARCH: ['$[[ matrix.ARCH ]]']
            RUNNER: ['$[[ matrix.RUNNER ]]']
  script:
    - trivy image --input image.tar --scanners vuln --severity HIGH,CRITICAL --exit-code 1 --format json --output trivy-report.json
  artifacts:
    when: always
    paths: [trivy-report.json]
    expire_in: 1 week
  allow_failure: false

publish:
  <<: *native
  extends: .docker-job
  stage: publish
  needs:
    - job: build
      artifacts: true
      parallel:
        matrix:
          - ARCH: ['$[[ matrix.ARCH ]]']
            RUNNER: ['$[[ matrix.RUNNER ]]']
    - job: scan
      artifacts: false
      parallel:
        matrix:
          - ARCH: ['$[[ matrix.ARCH ]]']
            RUNNER: ['$[[ matrix.RUNNER ]]']
  script:
    - |
      set -euo pipefail
      IMAGE="$ECR_REGISTRY/$ECR_REPOSITORY"
      docker load -i image.tar
      docker push "$IMAGE:$IMAGE_TAG"
      DIGEST="$(docker buildx imagetools inspect "$IMAGE:$IMAGE_TAG" --format '{{.Manifest.Digest}}')"
      [[ "$DIGEST" =~ ^sha256:[a-f0-9]{64}$ ]]
      mkdir -p approved
      printf '%s@%s\n' "$IMAGE" "$DIGEST" > "approved/$ARCH.txt"
  artifacts:
    paths: [approved/]
    expire_in: 1 week

manifest:
  extends: .docker-job
  stage: manifest
  tags: [eks-ci-amd64]
  needs:
    - job: publish
      artifacts: true
  script:
    - |
      set -euo pipefail
      IMAGE="$ECR_REGISTRY/$ECR_REPOSITORY"
      AMD64="$(cat approved/amd64.txt)"
      ARM64="$(cat approved/arm64.txt)"
      for REF in "$AMD64" "$ARM64"; do
        [[ "$REF" == "$IMAGE@sha256:"* ]]
        [[ "${REF##*@}" =~ ^sha256:[a-f0-9]{64}$ ]]
      done
      TAG="sha-${CI_COMMIT_SHA}-${CI_PIPELINE_ID}-${CI_JOB_ID}"
      docker buildx imagetools create --tag "$IMAGE:$TAG" "$AMD64" "$ARM64"
      DIGEST="$(docker buildx imagetools inspect "$IMAGE:$TAG" --format '{{.Manifest.Digest}}')"
      [[ "$DIGEST" =~ ^sha256:[a-f0-9]{64}$ ]]
      docker buildx imagetools inspect "$IMAGE@$DIGEST" --raw | jq -e '
        [.manifests[].platform | select(.os == "linux") | .architecture]
        | unique | sort | . == ["amd64", "arm64"]
      ' >/dev/null
      printf 'APPROVED_IMAGE=%s@%s\n' "$IMAGE" "$DIGEST" > approved.env
  artifacts:
    reports:
      dotenv: approved.env
    expire_in: 1 week
```

El servicio DinD requiere la opción de privilegios y el volumen compartido `/certs/client` en la configuración del runner. Las esperas de disponibilidad tienen un límite de tiempo. El estado del daemon y de las imágenes de Docker no se conserva entre trabajos: el archivo de imagen es el mecanismo explícito de transferencia. El artefacto final identifica el índice multi-plataforma aprobado; después de la aprobación, un workflow de GitOps independiente debe actualizar los manifiestos de despliegue.

## 3. GitHub Actions Runner Controller

### Conjuntos de escalado actuales de runners

Usa los charts OCI oficiales para conjuntos de escalado. `RunnerDeployment`, `RunnerSet` y `HorizontalRunnerAutoscaler` son recursos de otro modelo de controlador y no los instalan estos charts. El listener del conjunto de escalado actual detecta la demanda; no añadas una implementación webhook heredada y ajena al controlador para habilitar el escalado desde cero.

```yaml
# arc-namespaces.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: arc-systems
---
apiVersion: v1
kind: Namespace
metadata:
  name: arc-runners
  labels:
    pod-security.kubernetes.io/enforce: privileged
```

Crea `arc-github-app` en `arc-runners` mediante el flujo de secretos aprobado. Sus claves son `github_app_id`, `github_app_installation_id` y `github_app_private_key`. Usa un archivo protegido para la clave; no la incluyas directamente en un valor de Terraform o Helm. Instala la GitHub App con los permisos y el acceso a repositorios necesarios para el alcance elegido, ya sea un repositorio o una organización.

```bash
kubectl create secret generic arc-github-app -n arc-runners \
  --from-literal=github_app_id=REPLACE_ID \
  --from-literal=github_app_installation_id=REPLACE_INSTALLATION_ID \
  --from-file=github_app_private_key=/protected/github-app.pem
```

```yaml
# arc-controller-values.yaml
replicaCount: 1
serviceAccount:
  create: true
  name: arc-controller
resources:
  requests: {cpu: 100m, memory: 128Mi}
  limits: {cpu: "1", memory: 512Mi}
```

```yaml
# arc-runner-values.yaml
# ARC 0.15.0, Kubernetes >=1.29. Dedicated CI cluster, trusted publish jobs only.
githubConfigUrl: https://github.com/REPLACE_ORG/REPLACE_REPO
githubConfigSecret: arc-github-app
runnerScaleSetName: eks-ci-amd64
minRunners: 0
maxRunners: 4
controllerServiceAccount:
  namespace: arc-systems
  name: arc-controller
# Custom DinD template derived from the versioned chart; do not also set containerMode.
template:
  spec:
    automountServiceAccountToken: false
    nodeSelector:
      workload-type: ci-builder
      kubernetes.io/arch: amd64
    tolerations:
      - key: ci-builder
        operator: Equal
        value: "true"
        effect: NoSchedule
    initContainers:
      - name: init-dind-externals
        image: ghcr.io/actions/actions-runner@sha256:e5496277be5d09bc968b3d64911b74e219ac4a3f2edce956a3ecf9271bea1ef4
        command: [cp, -r, /home/runner/externals/., /home/runner/tmpDir/]
        volumeMounts:
          - name: dind-externals
            mountPath: /home/runner/tmpDir
      - name: dind
        image: docker.io/library/docker@sha256:5efed980cba3fc126cf54e21a5a6ff8849d05b6e0623d6e7612f48e9cd6cd17e
        args: [dockerd, --host=unix:///var/run/docker.sock, "--group=$(DOCKER_GROUP_GID)"]
        env:
          - name: DOCKER_GROUP_GID
            value: "123"
        securityContext:
          privileged: true
        restartPolicy: Always
        startupProbe:
          exec:
            command: [docker, info]
          failureThreshold: 24
          periodSeconds: 5
        resources:
          requests: {cpu: 250m, memory: 512Mi}
          limits: {cpu: "2", memory: 4Gi}
        volumeMounts:
          - name: work
            mountPath: /home/runner/_work
          - name: dind-sock
            mountPath: /var/run
          - name: dind-externals
            mountPath: /home/runner/externals
    containers:
      - name: runner
        image: ghcr.io/actions/actions-runner@sha256:e5496277be5d09bc968b3d64911b74e219ac4a3f2edce956a3ecf9271bea1ef4
        command: [/home/runner/run.sh]
        env:
          - name: DOCKER_HOST
            value: unix:///var/run/docker.sock
          - name: RUNNER_WAIT_FOR_DOCKER_IN_SECONDS
            value: "120"
        resources:
          requests: {cpu: 500m, memory: 1Gi}
          limits: {cpu: "2", memory: 4Gi}
        volumeMounts:
          - name: work
            mountPath: /home/runner/_work
          - name: dind-sock
            mountPath: /var/run
    volumes:
      - name: work
        emptyDir: {}
      - name: dind-sock
        emptyDir: {}
      - name: dind-externals
        emptyDir: {}
```

Esta plantilla personalizada sigue el diseño DinD de sidecar nativo de Kubernetes ≥1.29 del chart y fija runner 2.337.0 y Docker 29.8.0. No definas también `containerMode` si proporcionas el diseño personalizado. El runner y DinD comparten las rutas de trabajo y del socket, y los ejecutables externos del runner. La cuenta de servicio generada para el runner no tiene un rol de publicación. La imagen estándar del runner incluye Docker/Buildx/jq/git, pero no AWS CLI; el workflow de abajo obtiene el digest final mediante Buildx.

Para ARM, cambia `runnerScaleSetName` a `eks-ci-arm64` y la arquitectura del nodo a `arm64`. Usa esos nombres reales de conjunto de escalado en `runs-on`; el nombre de un grupo de runners de la organización no se convierte automáticamente en la etiqueta del trabajo. ARC 0.15.0 también expone `scaleSetLabels` si se necesitan etiquetas adicionales.

```bash
helm upgrade --install arc \
  oci://ghcr.io/actions/actions-runner-controller-charts/gha-runner-scale-set-controller \
  --version 0.15.0 --namespace arc-systems --values arc-controller-values.yaml
helm upgrade --install eks-ci-amd64 \
  oci://ghcr.io/actions/actions-runner-controller-charts/gha-runner-scale-set \
  --version 0.15.0 --namespace arc-runners --values arc-runner-values.yaml
helm upgrade --install eks-ci-arm64 \
  oci://ghcr.io/actions/actions-runner-controller-charts/gha-runner-scale-set \
  --version 0.15.0 --namespace arc-runners --values arc-runner-arm64-values.yaml
```

`minRunners` es el mínimo de runners inactivos que se suma al trabajo asignado, dentro de los límites de capacidad y máximo. El valor cero reduce los Pods de runner inactivos, pero no elimina el controlador, el listener ni todos los costes del clúster. Un valor distinto de cero tampoco garantiza que no haya demora de arranque. Restringe qué repositorios y workflows pueden usar los conjuntos de escalado y protege las ramas y etiquetas de publicación.

### Workflow de GitHub

Define las variables del repositorio `AWS_PUBLISH_ROLE_ARN`, `ECR_REPOSITORY` y `ECR_CACHE_REPOSITORY`. La relación de confianza de IAM permite la rama principal y las etiquetas protegidas `v*` de este repositorio exacto. Un entorno de GitHub cambia la forma de `sub` de OIDC; modifica la relación de confianza deliberadamente si añades uno. Nunca uses `pull_request_target` con un checkout no confiable para acceder a estas credenciales.

```yaml
# github-ci.yaml
name: Test and publish native ECR images
on:
  pull_request:
    branches: [main]
  push:
    branches: [main]
    tags: ['v*']
permissions:
  contents: read
concurrency:
  group: ci-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: false
jobs:
  test:
    runs-on: ubuntu-24.04
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
      - uses: actions/setup-node@820762786026740c76f36085b0efc47a31fe5020 # v7.0.0
        with:
          node-version: '24'
          cache: npm
      - run: npm ci
      - run: npm run lint
      - run: npm test
  publish:
    if: github.event_name == 'push'
    needs: test
    strategy:
      fail-fast: false
      matrix:
        include:
          - arch: amd64
            platform: linux/amd64
            runner: eks-ci-amd64
          - arch: arm64
            platform: linux/arm64
            runner: eks-ci-arm64
    runs-on: ${{ matrix.runner }}
    timeout-minutes: 30
    permissions:
      contents: read
      id-token: write
    env:
      AWS_REGION: ap-northeast-2
      ECR_REPOSITORY: ${{ vars.ECR_REPOSITORY }}
      ECR_CACHE_REPOSITORY: ${{ vars.ECR_CACHE_REPOSITORY }}
    steps:
      - name: Verify the native runner architecture
        env:
          ARCH: ${{ matrix.arch }}
        run: |
          case "$ARCH:$(uname -m)" in
            amd64:x86_64|arm64:aarch64) ;;
            *) echo "Runner architecture does not match the matrix" >&2; exit 1 ;;
          esac
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
      - uses: aws-actions/configure-aws-credentials@cbe3b392738ccf3f987d68400dafcf4b0624a56c # v6.2.4
        with:
          role-to-assume: ${{ vars.AWS_PUBLISH_ROLE_ARN }}
          aws-region: ${{ env.AWS_REGION }}
      - uses: aws-actions/amazon-ecr-login@03f1aad4c6c7ffd436567f42f9384779290529bd # v2.1.7
        id: login
      - uses: docker/setup-buildx-action@37fe631027851001ddb9b187196cc803df7f5f0e # v4.3.0
      - name: Define a unique build tag
        id: image
        env:
          REGISTRY: ${{ steps.login.outputs.registry }}
          ARCH: ${{ matrix.arch }}
        run: |
          set -euo pipefail
          TAG="sha-${GITHUB_SHA}-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}-${ARCH}"
          printf 'tag=%s/%s:%s\n' "$REGISTRY" "$ECR_REPOSITORY" "$TAG" >> "$GITHUB_OUTPUT"
      - uses: docker/build-push-action@53b7df96c91f9c12dcc8a07bcb9ccacbed38856a # v7.3.0
        with:
          context: .
          platforms: ${{ matrix.platform }}
          load: true
          push: false
          tags: ${{ steps.image.outputs.tag }}
          cache-from: type=registry,ref=${{ steps.login.outputs.registry }}/${{ env.ECR_CACHE_REPOSITORY }}:${{ matrix.arch }}-protected
          cache-to: type=registry,ref=${{ steps.login.outputs.registry }}/${{ env.ECR_CACHE_REPOSITORY }}:${{ matrix.arch }}-protected,mode=max,image-manifest=true,oci-mediatypes=true
      - uses: aquasecurity/trivy-action@ed142fd0673e97e23eac54620cfb913e5ce36c25 # v0.36.0
        with:
          version: v0.76.0
          image-ref: ${{ steps.image.outputs.tag }}
          scan-type: image
          scanners: vuln
          severity: HIGH,CRITICAL
          exit-code: '1'
      - name: Publish only the scanned image
        env:
          TAGGED_IMAGE: ${{ steps.image.outputs.tag }}
          REGISTRY: ${{ steps.login.outputs.registry }}
          ARCH: ${{ matrix.arch }}
        run: |
          set -euo pipefail
          docker push "$TAGGED_IMAGE"
          DIGEST="$(docker buildx imagetools inspect "$TAGGED_IMAGE" --format '{{.Manifest.Digest}}')"
          [[ "$DIGEST" =~ ^sha256:[a-f0-9]{64}$ ]]
          mkdir -p approved
          printf '%s/%s@%s\n' "$REGISTRY" "$ECR_REPOSITORY" "$DIGEST" > "approved/$ARCH.txt"
      - uses: actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a # v7.0.1
        with:
          name: approved-${{ matrix.arch }}
          path: approved/${{ matrix.arch }}.txt
          if-no-files-found: error
          retention-days: 7
  manifest:
    if: github.event_name == 'push'
    needs: publish
    runs-on: eks-ci-amd64
    timeout-minutes: 10
    permissions:
      contents: read
      id-token: write
    env:
      AWS_REGION: ap-northeast-2
      ECR_REPOSITORY: ${{ vars.ECR_REPOSITORY }}
    steps:
      - uses: aws-actions/configure-aws-credentials@cbe3b392738ccf3f987d68400dafcf4b0624a56c # v6.2.4
        with:
          role-to-assume: ${{ vars.AWS_PUBLISH_ROLE_ARN }}
          aws-region: ${{ env.AWS_REGION }}
      - uses: aws-actions/amazon-ecr-login@03f1aad4c6c7ffd436567f42f9384779290529bd # v2.1.7
        id: login
      - uses: docker/setup-buildx-action@37fe631027851001ddb9b187196cc803df7f5f0e # v4.3.0
      - uses: actions/download-artifact@3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c # v8.0.1
        with:
          pattern: approved-*
          path: approved
          merge-multiple: true
      - name: Publish the index of both approved platform digests
        env:
          REGISTRY: ${{ steps.login.outputs.registry }}
        run: |
          set -euo pipefail
          IMAGE="$REGISTRY/$ECR_REPOSITORY"
          AMD64="$(cat approved/amd64.txt)"
          ARM64="$(cat approved/arm64.txt)"
          for REF in "$AMD64" "$ARM64"; do
            [[ "$REF" == "$IMAGE@sha256:"* ]]
            DIGEST="${REF##*@}"
            [[ "$DIGEST" =~ ^sha256:[a-f0-9]{64}$ ]]
          done
          TAG="sha-${GITHUB_SHA}-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}"
          docker buildx imagetools create --tag "$IMAGE:$TAG" "$AMD64" "$ARM64"
          INDEX="$(docker buildx imagetools inspect "$IMAGE:$TAG" --format '{{.Manifest.Digest}}')"
          [[ "$INDEX" =~ ^sha256:[a-f0-9]{64}$ ]]
          docker buildx imagetools inspect "$IMAGE@$INDEX" --raw | jq -e '
            [.manifests[].platform | select(.os == "linux") | .architecture]
            | unique | sort | . == ["amd64", "arm64"]
          ' >/dev/null
          printf '%s@%s\n' "$IMAGE" "$INDEX" > approved-image.txt
      - uses: actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a # v7.0.1
        with:
          name: approved-image
          path: approved-image.txt
          if-no-files-found: error
          retention-days: 7
```

Cada plataforma nativa se analiza antes de publicar su digest. El trabajo del manifiesto consume referencias inmutables aprobadas y verifica que el índice resultante incluya AMD64 y ARM64. Se comprobaron los commits de las Actions y las definiciones de entradas y entorno de ejecución. El digest final, no la salida de etiqueta de varias líneas de la acción de metadatos, es la entrada para el despliegue y la firma. Si la plataforma lo exige, añade la verificación de firmas y admisión siguiendo la [guía del registro](../container-registry/04-best-practices.md).

## 4. Nodos de CI multi-plataforma nativos

Los siguientes grupos de Auto Mode usan requisitos estándar de tipos de instancia, no claves específicas de proveedores autogestionados. Suponen que ya existe una NodeClass predeterminada. Haz coincidir los selectores del administrador y del trabajo, las tolerancias, la arquitectura del helper y las etiquetas de runner configuradas en el servidor.

```yaml
# nodepools.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: ci-amd64
spec:
  template:
    metadata:
      labels:
        workload-type: ci-builder
    spec:
      nodeClassRef: {group: eks.amazonaws.com, kind: NodeClass, name: default}
      requirements:
        - key: kubernetes.io/arch
          operator: In
          values: [amd64]
        - key: karpenter.sh/capacity-type
          operator: In
          values: [on-demand, spot]
        - key: node.kubernetes.io/instance-type
          operator: In
          values: [c7i.xlarge, m7i.xlarge]
      taints:
        - key: ci-builder
          value: "true"
          effect: NoSchedule
  limits: {cpu: "64", memory: 256Gi}
  disruption: {consolidationPolicy: WhenEmpty, consolidateAfter: 5m}
---
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: ci-arm64
spec:
  template:
    metadata:
      labels:
        workload-type: ci-builder
    spec:
      nodeClassRef: {group: eks.amazonaws.com, kind: NodeClass, name: default}
      requirements:
        - key: kubernetes.io/arch
          operator: In
          values: [arm64]
        - key: karpenter.sh/capacity-type
          operator: In
          values: [on-demand, spot]
        - key: node.kubernetes.io/instance-type
          operator: In
          values: [c7g.xlarge, m7g.xlarge]
      taints:
        - key: ci-builder
          value: "true"
          effect: NoSchedule
  limits: {cpu: "64", memory: 256Gi}
  disruption: {consolidationPolicy: WhenEmpty, consolidateAfter: 5m}
```

Spot puede interrumpir las compilaciones; elige los tipos de capacidad y los reintentos según los requisitos de la carga de trabajo. Los runners nativos y la emulación QEMU son enfoques distintos. QEMU ejecuta instrucciones de otra arquitectura; no es por sí mismo un compilador cruzado. Las compilaciones multi-plataforma en un único runner requieren emulación compatible o un diseño explícito de compilación cruzada. Una opción de plataforma por sí sola no proporciona ninguna de las dos cosas.

## 5. Optimización de compilaciones y alternativas mantenidas

### Contenedor independiente de Next.js

Node 20 llegó al fin de su vida útil en abril de 2026. Este ejemplo basado en npm usa Node 24 y supone una única raíz de aplicación Next.js con un archivo de bloqueo. La compilación necesita las dependencias de desarrollo; omítelas solo del resultado de producción trazado. Configura explícitamente la salida independiente:

```javascript
export default {
  output: 'standalone'
}
```

```dockerfile
# Dockerfile.next
# syntax=docker/dockerfile:1
FROM docker.io/library/node@sha256:2fe369e969550cde8e867afc3fe370b260140cab4a23d467074295b42163d553 AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm \
    --mount=type=secret,id=npmrc,target=/root/.npmrc npm ci

FROM docker.io/library/node@sha256:2fe369e969550cde8e867afc3fe370b260140cab4a23d467074295b42163d553 AS builder
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN mkdir -p public && npm run build

FROM docker.io/library/node@sha256:2fe369e969550cde8e867afc3fe370b260140cab4a23d467074295b42163d553 AS runner
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    PORT=3000
COPY --from=builder --chown=node:node /app/public ./public
COPY --from=builder --chown=node:node /app/.next/standalone ./
COPY --from=builder --chown=node:node /app/.next/static ./.next/static
USER node
EXPOSE 3000
CMD ["node", "server.js"]
```

Usa este `.dockerignore`:

```text
node_modules
.next
.git
coverage
.npm
.env*
!.env.example
*.log
.npmrc
```

El Dockerfile copia los recursos públicos y `.next/static`, define una dirección de enlace accesible y ejecuta el proceso como el usuario no raíz `node` de la imagen. Las credenciales privadas de npm se pueden proporcionar mediante un secreto de BuildKit (`--secret id=npmrc,src=/protected/npmrc`); no copies `.npmrc` ni incluyas secretos en argumentos de compilación. Un monorepo necesita raíces de trazado deliberadas y rutas `COPY`/server anidadas que coincidan; el diseño con `server.js` en la raíz no es universal.

Se compiló una aplicación de prueba local Next 16.3.5/React 19.3.0 con Node 24.22.0; el servidor independiente generado y el archivo estático copiado respondieron HTTP 200. Esto comprueba el contrato de salida, no el despliegue de una aplicación, contenedor o CI completo.

### Comportamiento de la caché

Las exportaciones de caché del registro guardan capas de compilación. Una caché `RUN --mount=type=cache` es local al builder a menos que se conserve por separado; `--cache-to` del registro no exporta automáticamente todos los directorios de montajes de caché. Mantén las etiquetas mutables de caché fuera del repositorio inmutable de lanzamientos y nunca almacenes en caché las credenciales del registro.

Usa reglas de cambios declaradas y grafos de dependencias en vez de una prueba superficial `HEAD~1` o comandos en segundo plano seguidos de un `wait` simple que pueda ocultar errores. No hagas referencia a una etapa Dockerfile `tester` que no exista. Reutilizar la caché es una optimización, no una prueba de que el trabajo de código, pruebas y análisis haya terminado correctamente.

### Kaniko y BuildKit sin raíz

El repositorio de Google Kaniko está archivado. Que una herramienta no use daemon no significa que todos los Dockerfiles se compilen sin root ni que las compilaciones estén completamente aisladas. Para nuevos trabajos, usa un builder mantenido actualmente y verifica sus privilegios reales, el soporte del kernel, las credenciales y la ruta de publicación de imágenes.

Este fragmento opcional de BuildKit corresponde a un **runner no privilegiado distinto y validado**, con una imagen de CI que incluya BuildKit 0.33.0, AWS CLI, jq y Bash. No es un cambio directo a la configuración DinD con privilegios de arriba. El soporte de namespace de usuario y montajes, así como la política de seguridad del clúster, deben permitir el modo sin raíz elegido.

```yaml
# rootless-buildkit.yaml
# Alternative fragment for a SEPARATE validated non-privileged runner.
# CI_ROOTLESS_IMAGE must contain BuildKit 0.33.0, aws CLI, jq, and a shell.
# Node user-namespace/mount/security-policy support is a prerequisite.
build-rootless:
  image:
    name: $CI_ROOTLESS_IMAGE
    entrypoint: [""]
  tags: [validated-rootless-runner]
  variables:
    BUILDKITD_FLAGS: --oci-worker-no-process-sandbox
  script:
    - |
      set -euo pipefail
      umask 077
      DOCKER_CONFIG="$(mktemp -d)"
      export DOCKER_CONFIG
      trap 'rm -f "$DOCKER_CONFIG/config.json"; rmdir "$DOCKER_CONFIG"' EXIT
      aws ecr get-login-password --region "$AWS_REGION" |
        awk '{printf "AWS:%s", $0}' | base64 | tr -d '\n' |
        jq -R --arg registry "$ECR_REGISTRY" \
          '{auths:{($registry):{auth:.}}}' > "$DOCKER_CONFIG/config.json"
      buildctl-daemonless.sh build --frontend dockerfile.v0 \
        --local context=. --local dockerfile=. \
        --output type=oci,dest=image.tar
  artifacts:
    paths: [image.tar]
```

La salida es un archivo OCI para entregar a un analizador/publicador compatible. BuildKit advierte que `--oci-worker-no-process-sandbox` debilita el aislamiento de procesos dentro del contenedor del daemon y no puede limpiar todos los procesos de compilación que queden en ejecución. Usarlo en Kubernetes es una concesión, no una garantía de seguridad universal. Valida la configuración del runner dedicado antes de adoptar esta alternativa.

## Referencias

- [Ejecutor de Kubernetes de GitLab](https://docs.gitlab.com/runner/executors/kubernetes/)
- [Configuración avanzada de GitLab Runner](https://docs.gitlab.com/runner/configuration/advanced-configuration/)
- [Dependencias de matrices de GitLab](https://docs.gitlab.com/ci/yaml/matrix_expressions/)
- [Conjuntos de escalado de runners de ARC](https://docs.github.com/en/actions/tutorials/use-actions-runner-controller/deploy-runner-scale-sets)
- [Requisitos de BuildKit sin raíz](https://github.com/moby/buildkit/blob/v0.33.0/docs/rootless.md)
- [Salida independiente de Next.js](https://nextjs.org/docs/app/api-reference/config/next-config-js/output)

< [Anterior: NLB Blue/Green](02-infrastructure-advanced.md) | [Tabla de contenido](README.md) | [Siguiente: ArgoCD Multi-Cluster](04-gitops-multi-cluster.md) >
