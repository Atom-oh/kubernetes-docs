# FluxCD

> **Línea base de revisión**: Flux 2.9.5 autogestionado; actualizado al parche 2.9.6 tras revisar las notas de la versión (los ejemplos no se volvieron a ejecutar)
> **Última actualización**: October 12, 2026

FluxCD es un conjunto de soluciones de entrega continua y progresiva para Kubernetes que son abiertas y extensibles. FluxCD se graduó de la CNCF en noviembre de 2022, lo que lo convierte en una de las herramientas GitOps más maduras del ecosistema cloud-native.

Este capítulo se orienta a **Flux 2.9.6 autogestionado**. La comprobación previa de la CLI requiere al menos Kubernetes 1.33; revise también la ventana de soporte real de la distribución. Revise el procedimiento de migración de API 2.7+ antes de actualizar desde 2.6 o una versión anterior. Las API OCIRepository/Bucket/image de abajo usan v1; Notification Provider/Alert permanecen en v1beta3.

Los ejemplos usan recursos `flux-system` confiables y propiedad de la plataforma. Las Kustomizations repetidas son alternativas o fragmentos para componer, no una secuencia de sustituciones. Prepare las URL, rutas, namespaces y Secrets reales del repositorio. El uso por tenants requiere namespaces dedicados, RBAC/impersonation mediante `spec.serviceAccountName` y restricciones de referencias entre namespaces.

## Introducción

FluxCD implementa los principios GitOps mediante repositorios Git como fuente de verdad para definir el estado deseado de sus clústeres Kubernetes. Reconcilia periódicamente los cambios de las fuentes y la desviación. Los fallos de autorización, disponibilidad y health check pueden retrasar o impedir la convergencia.

### Características principales

- **GitOps nativo**: Creado desde cero para flujos de trabajo GitOps
- **Multi-tenancy**: Admite varios equipos con configuraciones aisladas
- **Multi-cluster**: Gestiona varios clústeres desde un único repositorio Git
- **Extensible**: Arquitectura modular con controllers especializados
- **Kubernetes nativo**: Usa Custom Resource Definitions (CRDs) para la configuración

## Descripción general de la arquitectura

FluxCD consta de un conjunto de controllers especializados que trabajan juntos para implementar flujos de trabajo GitOps:

![Controllers de fuente, aplicación/entrega y notificaciones de Flux, con los controllers opcionales image-reflector e image-automation que separan los análisis del registro de las actualizaciones de Git.](../.gitbook/assets/en-gitops-02-fluxcd-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-02-fluxcd-0.html)

## Componentes principales

La instalación predeterminada incluye los controllers source/kustomize/helm/notification. La automatización de imágenes también requiere **image-reflector-controller e image-automation-controller**. El source-watcher opcional proporciona composición de fuentes mediante API como ArtifactGenerator.

| Secret | Contenido requerido |
|---|---|
| git-credentials | Nombre de usuario/contraseña de Git por HTTPS o autenticación correspondiente; las actualizaciones de imágenes también necesitan acceso de escritura al repositorio |
| registry-credentials | Un Secret kubernetes.io/dockerconfigjson para el ImageRepository privado |
| slack-bot-token | Token OAuth de Slack Bot bajo la clave `token` |
| github-webhook-token | El `token` compartido con el webhook de GitHub |

Prepare los ConfigMaps/Secrets a los que se hace referencia en el mismo namespace que el recurso Flux. Proporcione los valores reales mediante una gestión de secretos protegida, no mediante archivos Git de texto sin formato.

### Source Controller

El Source Controller se encarga de obtener artifacts de fuentes externas. Admite varios tipos de fuentes:

#### GitRepository

Realiza seguimiento de un repositorio Git y lo pone a disposición de otros controllers:

```yaml
apiVersion: source.toolkit.fluxcd.io/v1
kind: GitRepository
metadata:
  name: my-app
  namespace: flux-system
spec:
  interval: 1m
  url: https://github.com/my-org/my-app
  ref:
    branch: main
  secretRef:
    name: git-credentials
```

#### HelmRepository

Realiza seguimiento de un repositorio de charts Helm:

```yaml
apiVersion: source.toolkit.fluxcd.io/v1
kind: HelmRepository
metadata:
  name: podinfo
  namespace: flux-system
spec:
  interval: 1h
  url: https://stefanprodan.github.io/podinfo
```

#### OCIRepository

Esto describe un **artifact OCI que contiene manifests/contenido Helm para Flux**, no una imagen de contenedor de carga de trabajo. Publique primero un artifact compatible y fije su tag/digest.

Realiza seguimiento de artifacts almacenados en registros compatibles con OCI (incluidos registros de contenedores):

```yaml
apiVersion: source.toolkit.fluxcd.io/v1
kind: OCIRepository
metadata:
  name: my-artifacts
  namespace: flux-system
spec:
  interval: 5m
  url: oci://ghcr.io/my-org/my-artifacts
  ref:
    tag: v1.0.0
```

#### Bucket

El ejemplo de AWS presupone una cadena de credenciales predeterminada configurada, como IRSA/Pod Identity de source-controller. Prepare la autenticación de EKS y los permisos del bucket que se describen a continuación.

Realiza seguimiento de artifacts almacenados en almacenamiento compatible con S3:

```yaml
apiVersion: source.toolkit.fluxcd.io/v1
kind: Bucket
metadata:
  name: my-bucket
  namespace: flux-system
spec:
  interval: 5m
  provider: aws
  bucketName: my-flux-bucket
  endpoint: s3.us-east-1.amazonaws.com
  region: us-east-1
```

### Kustomize Controller

El Kustomize Controller aplica overlays de Kustomize y manifests de Kubernetes simples desde las fuentes.

#### Kustomization CRD

`targetNamespace` no crea un namespace. Créelo previamente o incluya su manifest Namespace en la Kustomization. `prune: true` puede eliminar recursos gestionados previamente que se hayan quitado de la fuente; revise los límites de la fuente y la política de eliminación.

```yaml
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: my-app
  namespace: flux-system
spec:
  interval: 10m
  targetNamespace: production
  sourceRef:
    kind: GitRepository
    name: my-app
  path: ./deploy/production
  prune: true
  healthChecks:
  - apiVersion: apps/v1
    kind: Deployment
    name: my-app
    namespace: production
  timeout: 2m
```

#### Sustitución de variables

Las entradas de `substituteFrom` sobrescriben las entradas anteriores; `substitute` en línea tiene precedencia. Las sustituciones de Secret entran en los manifests renderizados, así que controle su salida/acceso. El kustomize-controller 1.9.6 incluido con Flux 2.9.6 habilita `StrictPostBuildSubstitutions` de forma predeterminada y falla si faltan variables sin valores predeterminados. Compruebe si una implementación existente deshabilita explícitamente esa feature gate. Los campos numéricos aún deben renderizarse como valores numéricos de Kubernetes.

FluxCD admite la sustitución de variables mediante `postBuild`:

```yaml
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: my-app
  namespace: flux-system
spec:
  interval: 10m
  sourceRef:
    kind: GitRepository
    name: my-app
  path: ./deploy
  postBuild:
    substitute:
      ENVIRONMENT: production
      REPLICAS: '3'
    substituteFrom:
    - kind: ConfigMap
      name: cluster-config
    - kind: Secret
      name: cluster-secrets
  prune: true
  targetNamespace: production
```

#### Health checks

Defina health checks personalizados para los recursos implementados:

```yaml
spec:
  healthChecks:
  - apiVersion: apps/v1
    kind: Deployment
    name: frontend
    namespace: production
  - apiVersion: apps/v1
    kind: StatefulSet
    name: database
    namespace: production
  timeout: 5m
```

### Helm Controller

El Helm Controller gestiona las releases de charts Helm de forma declarativa.

#### HelmRelease CRD

```yaml
apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: podinfo
  namespace: flux-system
spec:
  interval: 5m
  chart:
    spec:
      chart: podinfo
      version: 6.15.0
      sourceRef:
        kind: HelmRepository
        name: podinfo
        namespace: flux-system
  targetNamespace: web
  install:
    createNamespace: true
    remediation:
      retries: 3
  upgrade:
    remediation:
      retries: 3
  values:
    replicaCount: 2
    service:
      type: ClusterIP
  releaseName: podinfo
```

#### Anulaciones de valores

Las entradas `valuesFrom` posteriores sobrescriben las anteriores, seguidas por los valores en línea. Una referencia `targetPath` puede sobrescribir incluso valores en línea, así que gestione explícitamente ese caso.

Anule valores Helm desde varias fuentes:

```yaml
spec:
  valuesFrom:
  - kind: ConfigMap
    name: podinfo-values
    valuesKey: values.yaml
  - kind: Secret
    name: podinfo-secrets
    valuesKey: credentials.yaml
  values:
    replicaCount: 3
```

#### Detección de desviaciones

Ignore las réplicas solo cuando otro controller, como HPA, sea su propietario. Las reglas de ignorado innecesarias pueden ocultar desviaciones manuales.

Habilite la detección de desviaciones para garantizar que los recursos implementados coincidan con el estado deseado:

```yaml
spec:
  driftDetection:
    mode: enabled
    ignore:
    - paths:
      - /spec/replicas
      target:
        kind: Deployment
```

### Notification Controller

El Notification Controller gestiona eventos entrantes y salientes.

#### Providers

El ejemplo usa la API de Slack Bot. Configure `chat:write`, invite al bot al canal de destino y sustituya channel por su ID real. Una URL de Incoming Webhook no es un token de Bot.

Configure providers de notificaciones para las alertas:

```yaml
apiVersion: notification.toolkit.fluxcd.io/v1beta3
kind: Provider
metadata:
  name: slack
  namespace: flux-system
spec:
  type: slack
  channel: C0123456789
  secretRef:
    name: slack-bot-token
  address: https://slack.com/api/chat.postMessage
```

Los providers admitidos incluyen:
- Slack
- Microsoft Teams Workflows (`msteams`)
- Discord
- PagerDuty
- Opsgenie (clientes existentes; cierre anunciado para 2027-04-05)
- GitHub
- GitLab
- Grafana
- Webhooks genéricos

#### Alerts

Defina alertas para los eventos de FluxCD:

```yaml
apiVersion: notification.toolkit.fluxcd.io/v1beta3
kind: Alert
metadata:
  name: on-call
  namespace: flux-system
spec:
  providerRef:
    name: slack
  eventSeverity: error
  eventSources:
  - kind: GitRepository
    name: '*'
  - kind: Kustomization
    name: '*'
  - kind: HelmRelease
    name: '*'
  eventMetadata:
    summary: Cluster alerts
```

#### Receivers (Webhooks)

La creación de un Receiver no expone un endpoint de Internet. Combine un ingress TLS revisado para el Service webhook-receiver con status.webhookPath, configure el mismo token en GitHub y conserve la verificación de firma para type: github.

Configure webhooks para eventos externos:

```yaml
apiVersion: notification.toolkit.fluxcd.io/v1
kind: Receiver
metadata:
  name: github-receiver
  namespace: flux-system
spec:
  type: github
  events:
  - ping
  - push
  secretRef:
    name: github-webhook-token
  resources:
  - kind: GitRepository
    name: my-app
```

### Automatización de imágenes

FluxCD puede actualizar automáticamente tags de imágenes de contenedor en repositorios Git.

#### ImageRepository

El image-reflector-controller analiza tags y evalúa ImagePolicy. No crea imágenes, analiza vulnerabilidades ni realiza pulls de imágenes de cargas de trabajo.

Analice registros de contenedores para detectar tags nuevos:

```yaml
apiVersion: image.toolkit.fluxcd.io/v1
kind: ImageRepository
metadata:
  name: my-app
  namespace: flux-system
spec:
  image: ghcr.io/my-org/my-app
  interval: 1m
  secretRef:
    name: registry-credentials
```

#### ImagePolicy

Defina políticas para seleccionar tags de imagen:

```yaml
apiVersion: image.toolkit.fluxcd.io/v1
kind: ImagePolicy
metadata:
  name: my-app
  namespace: flux-system
  labels:
    app: my-app
spec:
  imageRepositoryRef:
    name: my-app
  policy:
    semver:
      range: '>=1.0.0 <2.0.0'
  digestReflectionPolicy: IfNotPresent
```

#### ImageUpdateAutomation

Los campos YAML necesitan marcadores de política para actualizarse. IfNotPresent refleja el digest de un tag seleccionado; no es validación de firmas o vulnerabilidades. Esta automatización hace push a una rama dedicada flux/image-updates. La creación/aprobación de PR hacia main es un flujo de CI/operador independiente, no proporcionado automáticamente por Flux. Reserve la rama para la automatización y conceda acceso de escritura a sus credenciales Git.

```yaml
# Deployment Pod-template fragment; the policy marker is required.
spec:
  template:
    spec:
      containers:
        - name: app
          image: ghcr.io/my-org/my-app:1.0.0 # {"$imagepolicy": "flux-system:my-app"}
```

Automatice commits de Git cuando se detecten nuevas imágenes:

```yaml
apiVersion: image.toolkit.fluxcd.io/v1
kind: ImageUpdateAutomation
metadata:
  name: my-app
  namespace: flux-system
spec:
  interval: 30m
  sourceRef:
    kind: GitRepository
    name: my-app
  git:
    checkout:
      ref:
        branch: main
    commit:
      author:
        email: flux@my-org.com
        name: Flux
      messageTemplate: |
        Automated image update

        Automation: {{ .AutomationObject }}

        Files:
        {{ range $filename, $_ := .Changed.FileChanges -}}
        - {{ $filename }}
        {{ end -}}

        Objects:
        {{ range $resource, $changes := .Changed.Objects -}}
        - {{ $resource.Kind }} {{ $resource.Name }}
          {{- range $_, $change := $changes }}
          {{ $change.OldValue }} -> {{ $change.NewValue }}
          {{- end }}
        {{ end -}}
    push:
      branch: flux/image-updates
  update:
    path: ./deploy
    strategy: Setters
  policySelector:
    matchLabels:
      app: my-app
```

## Instalación

### Uso de la CLI de Flux

Ejemplo de instalación de la release verificada Linux amd64/arm64. Para otros sistemas operativos, siga la [guía oficial de instalación de la CLI](https://fluxcd.io/flux/installation/#install-the-flux-cli) y verifique la versión instalada.

```bash
set -euo pipefail
FLUX_VERSION=2.9.6
case "$(uname -m)" in
  x86_64)
    flux_arch=amd64
    flux_sha=b853df82adfd7736f580692f9f734473d571606307139f8fd20c2a80dd1ff473 ;;
  aarch64|arm64)
    flux_arch=arm64
    flux_sha=f3e159af616ec0b9bd0a405c2185cf09d06b74652c1de3c7f377e8166826651a ;;
  *) echo "Use the official installer for this architecture" >&2; exit 1 ;;
esac
flux_tmp="$(mktemp -d)"
trap 'rm -rf "$flux_tmp"' EXIT
curl -fsSL -o "$flux_tmp/flux.tar.gz" \
  "https://github.com/fluxcd/flux2/releases/download/v${FLUX_VERSION}/flux_${FLUX_VERSION}_linux_${flux_arch}.tar.gz"
printf '%s  %s\n' "$flux_sha" "$flux_tmp/flux.tar.gz" | sha256sum -c -
tar -xzf "$flux_tmp/flux.tar.gz" -C "$flux_tmp" flux
mkdir -p "$HOME/.local/bin"
install -m 0755 "$flux_tmp/flux" "$HOME/.local/bin/flux"
export PATH="$HOME/.local/bin:$PATH"
flux --version
```

### Bootstrap

Bootstrap escribe la configuración en Git e instala controllers en el clúster. Verifique el kubecontext y la autorización del repositorio, y elija GitHub o GitLab. my-org representa una organización/grupo; use --personal solo para una cuenta de usuario. Proporcione tokens de forma segura mediante variables de entorno. Estos ejemplos incluyen controllers de automatización de imágenes. Si automatiza el propio repositorio de bootstrap, habilite por separado el acceso de escritura para su deploy key.

```bash
kubectl config current-context
flux check --pre

# Alternative A: GitHub organization; provide authorized GITHUB_TOKEN securely.
flux bootstrap github \
  --owner=my-org \
  --repository=fleet-infra \
  --branch=main \
  --path=clusters/production \
  --version=v2.9.6 \
  --components-extra=image-reflector-controller,image-automation-controller

# Alternative B: GitLab group; provide authorized GITLAB_TOKEN securely.
flux bootstrap gitlab \
  --owner=my-org \
  --repository=fleet-infra \
  --branch=main \
  --path=clusters/production \
  --version=v2.9.6 \
  --components-extra=image-reflector-controller,image-automation-controller
```

### Verificar la instalación

```bash
# Check Flux components
flux check --components-extra=image-reflector-controller,image-automation-controller

# Get all Flux resources
flux get all

# Watch for changes
flux get kustomizations --watch
```

## Multi-cluster con Flux

FluxCD admite la gestión de varios clústeres desde un único repositorio.

### Estructura del repositorio fleet

```
fleet-infra/
├── clusters/
│   ├── production/
│   │   ├── flux-system/
│   │   │   ├── gotk-components.yaml
│   │   │   ├── gotk-sync.yaml
│   │   │   └── kustomization.yaml
│   │   └── apps.yaml
│   ├── staging/
│   │   ├── flux-system/
│   │   │   ├── gotk-components.yaml
│   │   │   ├── gotk-sync.yaml
│   │   │   └── kustomization.yaml
│   │   └── apps.yaml
│   └── development/
│       ├── flux-system/
│       │   └── gotk-sync.yaml
│       └── apps.yaml
├── infrastructure/
│   ├── base/
│   │   ├── cert-manager/
│   │   ├── envoy-gateway/
│   │   └── monitoring/
│   └── overlays/
│       ├── production/
│       └── staging/
└── apps/
    ├── base/
    │   ├── frontend/
    │   └── backend/
    └── overlays/
        ├── production/
        └── staging/
```

### Dependencias de Kustomization en un plano de control

`dependsOn` espera la condición Ready de los objetos Kustomization observados por este plano de control Flux. Son dos objetos en un clúster, no una barrera entre clústeres. `wait: true` hace que la preparación de la infraestructura incluya la salud de las cargas de trabajo. El GitRepository de bootstrap predeterminado se llama `flux-system`, que este ejemplo utiliza como su `sourceRef`.

Inicialice cada clúster independiente con su propio contexto/ruta, o configure explícitamente un `kubeConfig` remoto y la autorización. Desde Flux 2.9.5, los kubeconfigs de Secret rechazan referencias a archivos locales en `certificate-authority`, `tokenFile`, `client-certificate` y `client-key`. Proporcione las credenciales/certificados requeridos como datos en línea protegidos o use una configuración de workload identity compatible.

```yaml
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: infrastructure
  namespace: flux-system
spec:
  interval: 1h
  sourceRef:
    kind: GitRepository
    name: flux-system
  path: ./infrastructure/overlays/production
  prune: true
  wait: true
  timeout: 5m
---
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: apps
  namespace: flux-system
spec:
  dependsOn:
  - name: infrastructure
  interval: 10m
  sourceRef:
    kind: GitRepository
    name: flux-system
  path: ./apps/overlays/production
  prune: true
```

## FluxCD en Amazon EKS

### Autenticación de AWS por controller

Este ejemplo utiliza **IRSA en el nivel del controller**. Primero configure el proveedor OIDC de EKS, la confianza de rol para el subject ServiceAccount exacto y la audiencia sts.amazonaws.com, además de los permisos de recursos. Una anotación role-ARN no crea confianza ni políticas. EKS Pod Identity requiere en cambio la configuración de su asociación/agente; no se configura con la anotación de IRSA.

| Controller | Propósito del acceso a AWS |
|---|---|
| source-controller | Artifacts OCI/Helm, Buckets S3, fuentes Git de CodeCommit |
| image-reflector-controller | Análisis de tag/digest de imágenes de cargas de trabajo de ECR |
| image-automation-controller | Permisos de Git clone/push al usar directamente CodeCommit |
| kustomize-controller | Descifrado de SOPS KMS o reconciliación de EKS remoto |
| helm-controller | Reconciliación de releases Helm en EKS remoto |

Conceder un rol a source-controller no autentica todos los demás controllers. Para multi-tenancy, revise por separado la workload identity compatible en el nivel de objeto y su feature gate, ServiceAccount y configuración de RBAC.

Fusione este parche en flux-system/kustomization.yaml bajo la ruta de bootstrap y gestiónelo en Git, conservando los parches/recursos existentes. Un cambio únicamente en ServiceAccount no vuelve a inyectar IRSA en los Pods existentes; implemente de nuevo el controller afectado después de la reconciliación.

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
- gotk-components.yaml
- gotk-sync.yaml
patches:
- target:
    kind: ServiceAccount
    name: source-controller
  patch: |
    apiVersion: v1
    kind: ServiceAccount
    metadata:
      name: source-controller
      annotations:
        eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/flux-source-controller
```

```bash
kubectl rollout restart deployment/source-controller -n flux-system
kubectl rollout status deployment/source-controller -n flux-system --timeout=180s
```

### Artifacts GitOps en ECR

Estos permisos de source-controller leen un repositorio dedicado gitops-artifacts. GetAuthorizationToken no admite la delimitación al ARN del repositorio, por lo que su recurso es * con una condición de región solicitada. Las acciones de lectura de contenido están delimitadas al ARN del repositorio. Sustituya los valores de cuenta/región/repositorio.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "ecr:GetAuthorizationToken",
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": "us-east-1"
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage"
      ],
      "Resource": "arn:aws:ecr:us-east-1:123456789012:repository/gitops-artifacts"
    }
  ]
}
```

```yaml
apiVersion: source.toolkit.fluxcd.io/v1
kind: OCIRepository
metadata:
  name: gitops-artifacts
  namespace: flux-system
spec:
  interval: 5m
  url: oci://123456789012.dkr.ecr.us-east-1.amazonaws.com/gitops-artifacts
  ref:
    tag: v1.0.0
  provider: aws
```

OCIRepository lee artifacts de manifest/Helm para Flux. No implementa imágenes de contenedor de cargas de trabajo ni concede permisos de image pull de EKS node/Fargate. El análisis de ImageRepository de ECR necesita autenticación independiente de image-reflector-controller y permisos de lectura del registro.

### Fuente Bucket de S3

Use un bucket de artifacts dedicado y agregue los siguientes permisos al rol del controller. El cifrado KMS gestionado por el cliente además necesita la política de clave y kms:Decrypt; el acceso entre cuentas también requiere la política del bucket.

```yaml
apiVersion: source.toolkit.fluxcd.io/v1
kind: Bucket
metadata:
  name: artifacts
  namespace: flux-system
spec:
  interval: 5m
  provider: aws
  bucketName: my-flux-artifacts
  endpoint: s3.us-east-1.amazonaws.com
  region: us-east-1
```

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::my-flux-artifacts"
    },
    {
      "Effect": "Allow",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::my-flux-artifacts/*"
    }
  ]
}
```

### Fuente HTTPS de CodeCommit

Esta es una **integración de fuente para una instalación Flux existente**, no un procedimiento de bootstrap ni de creación de credenciales IAM. source-controller 1.9.6 (incluido con Flux 2.9.6) admite provider: aws con un endpoint HTTPS de CodeCommit e IRSA/Pod Identity. Agregue el permiso de lectura a su rol y haga referencia a este GitRepository desde la Kustomization deseada.

```yaml
apiVersion: source.toolkit.fluxcd.io/v1
kind: GitRepository
metadata:
  name: codecommit-manifests
  namespace: flux-system
spec:
  interval: 1m
  provider: aws
  url: https://git-codecommit.us-east-1.amazonaws.com/v1/repos/fleet-infra
  ref:
    branch: main
```

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "codecommit:GitPull",
      "Resource": "arn:aws:codecommit:us-east-1:123456789012:fleet-infra"
    }
  ]
}
```

Si ImageUpdateAutomation hace push a CodeCommit, su identidad de controller/objeto también necesita permisos GitPull/GitPush y una política de rama/PR dedicada. SSH requiere un ID de clave SSH registrado en IAM como nombre de usuario y la clave privada correspondiente; una URL ssh:// o una opción de generación de claves de la CLI no registra una clave IAM.

## Prácticas recomendadas

### Estructura del repositorio

- Use un monorepo para equipos pequeños
- Use repositorios separados para infraestructura y aplicaciones en organizaciones grandes
- Implemente overlays específicos por entorno con Kustomize

### Seguridad

- Gestione los ciclos de vida de Secret/clave con SOPS/Sealed Secrets o External Secrets Operator
- Configure namespaces de tenant, RBAC/impersonation basado en spec.serviceAccountName y restricciones de referencias entre namespaces
- Habilite la validación de webhooks para receivers

### Monitorización

- Configure alertas para fallos de reconciliación
- Exporte métricas a Prometheus
- Configure dashboards para los componentes de Flux

### Rendimiento

- Ajuste los intervalos de reconciliación según la frecuencia de cambios
- Use caché para repositorios Helm
- Implemente health checks con timeouts adecuados

## Referencias

- [Release de Flux 2.9.5 y aviso de endurecimiento de kubeconfig](https://github.com/fluxcd/flux2/releases/tag/v2.9.5)
- [Notas de la versión de Flux 2.9.6](https://github.com/fluxcd/flux2/releases/tag/v2.9.6)
- [Instalación de Flux](https://fluxcd.io/flux/installation/)
- [Integración de AWS](https://fluxcd.io/flux/integrations/aws/)
- [GitRepository v1](https://github.com/fluxcd/source-controller/blob/v1.9.5/docs/spec/v1/gitrepositories.md)
- [ImageUpdateAutomation v1](https://github.com/fluxcd/image-automation-controller/blob/v1.2.5/docs/spec/v1/imageupdateautomations.md)
- [Kustomization v1](https://github.com/fluxcd/kustomize-controller/blob/v1.9.5/docs/spec/v1/kustomizations.md)
- [Providers de notificaciones](https://github.com/fluxcd/notification-controller/blob/v1.9.4/docs/spec/v1beta3/providers.md)
- [Ciclo de vida de Opsgenie](https://www.atlassian.com/software/opsgenie)

## Cuestionario

Para comprobar lo que ha aprendido, pruebe el [cuestionario de FluxCD](../quizzes/gitops/02-fluxcd-quiz.md).
