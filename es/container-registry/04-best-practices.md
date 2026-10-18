# Buenas prácticas para registros de contenedores

> **Última actualización**: 16 de octubre de 2026

## Introducción

Este documento reúne buenas prácticas para administrar registros de contenedores en Docker Hub, Amazon ECR y Harbor. Estas recomendaciones se aplican independientemente del registro elegido y se centran en la excelencia operativa, la seguridad y la optimización de costos.

Los valores de cuenta, región, nombre de host y repositorio en los ejemplos de API/CLI son ilustrativos. Primero prepara los recursos de destino y las credenciales. Para los ejemplos de la API de Harbor, define `HARBOR_USER` y usa el indicador de contraseña de `curl --user`. Obtén los ID de endpoint de las respuestas de creación.

## Administración de tags

### Tags inmutables

Un tag con forma de versión aún puede sobrescribirse, a menos que el registro imponga inmutabilidad. Fija en los despliegues el digest probado y aplica reglas de inmutabilidad a los tags de lanzamiento. La inmutabilidad no siempre protege un artefacto contra la eliminación; comprueba la política exacta del registro.

| Registro | Configuración |
|----------|---------------|
| Docker Hub | Ajustes de mutabilidad de tags del repositorio (Beta al momento de esta revisión) |
| Amazon ECR | `image-tag-mutability: IMMUTABLE` |
| Harbor | Reglas de inmutabilidad de tags del proyecto |

```bash
# ECR: Enable immutable tags
aws ecr put-image-tag-mutability \
  --repository-name myapp \
  --image-tag-mutability IMMUTABLE

```

### Versionado semántico

Los metadatos de compilación de SemVer (`+build`) no son directamente válidos en un tag de imagen. Conserva el SemVer completo en las etiquetas OCI y asigna los tags a la sintaxis permitida de caracteres alfanuméricos, guion bajo, punto y guion.

Usa SemVer (versionado semántico) para las imágenes de lanzamiento:

```
MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD]

Examples:
  1.0.0           - Initial release
  1.0.1           - Patch release (bug fixes)
  1.1.0           - Minor release (new features, backward compatible)
  2.0.0           - Major release (breaking changes)
  1.0.0-rc.1      - Release candidate
  1.0.0-beta.2    - Beta release
  1.0.0+build.123 - Build metadata
```

### Estrategia de tags por entorno

| Entorno | Patrón de tag | Ejemplo | Mutabilidad |
|-------------|-------------|---------|------------|
| Producción | SemVer | `1.2.3` | Inmutable |
| Preparación | SemVer-rc | `1.2.3-rc.1` | Inmutable |
| Desarrollo | Basado en SHA | `abc123f-dev` | Mutable |
| Rama de funcionalidad | Rama-SHA | `feature-auth-abc123f` | Mutable |
| Compilaciones CI | Número de compilación | `build-456` | Mutable |

### Antipatrón del tag `latest`

**Nunca uses `latest` en producción.** Problemas de `latest`:

1. **No determinista**: distintos nodos pueden descargar imágenes diferentes.
2. **Sin ruta de reversión**: no se puede volver a «latest anterior».
3. **Ambigüedad de política de descarga**: si se omite la política, al crear el objeto se usa `Always` con `latest`; aun así, se pueden reutilizar las capas en caché.
4. **Pesadilla de auditoría**: no se puede determinar qué versión está en ejecución.

```yaml
# BAD - Never do this in production
spec:
  containers:
  - name: app
    image: myregistry.com/myapp:latest
    imagePullPolicy: Always  # Checks the reference each start; cached layers can be reused

---
# GOOD - Use specific versions
spec:
  containers:
  - name: app
    image: myregistry.com/myapp:1.2.3
    # imagePullPolicy: IfNotPresent (default, efficient)
```

Cuándo sí puede aceptarse `latest`:
- Desarrollo local
- Tutoriales y ejemplos
- Imágenes base en Dockerfiles (fíjalas en producción)

### Flujos de promoción

Implementa un flujo de promoción en vez de volver a compilar las imágenes:

![Primero se compila una imagen y luego se promociona sin cambios de desarrollo a pruebas y producción, cambiando el tag del mismo digest, de modo que el artefacto que se publica en producción sea idéntico bit por bit al que se probó antes.](../.gitbook/assets/en-container-registry-04-best-practices-10.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-container-registry-04-best-practices-10.html)

Script de promoción:

```bash
#!/usr/bin/env bash
set -euo pipefail
: "${AWS_REGION:?Set the registry region}"
: "${ECR_REGISTRY:?Set account.dkr.ecr.region.amazonaws.com}"
: "${SOURCE_REPO:?Set the source repository}"
: "${SOURCE_DIGEST:?Set the scanned sha256 digest}"
: "${TARGET_REPO:?Set the pre-created destination repository}"
: "${TARGET_TAG:?Set a new immutable release tag}"
aws ecr get-login-password --region "$AWS_REGION" \
  | skopeo login --username AWS --password-stdin "$ECR_REGISTRY"
skopeo copy --all --preserve-digests \
  "docker://${ECR_REGISTRY}/${SOURCE_REPO}@${SOURCE_DIGEST}" \
  "docker://${ECR_REGISTRY}/${TARGET_REPO}:${TARGET_TAG}"
```

## Convenciones para nombrar imágenes

### Formato estándar

```
[REGISTRY/]NAMESPACE/REPOSITORY:TAG[@DIGEST]

Examples:
  nginx:1.30.6                                    # Docker Hub official
  myuser/myapp:v1.0.0                          # Docker Hub user
  123456789012.dkr.ecr.us-east-1.amazonaws.com/myapp:v1.0.0  # ECR
  harbor.example.com/production/myapp:v1.0.0   # Harbor
  ghcr.io/myorg/myapp:v1.0.0                   # GitHub Container Registry
```

### Estructura organizativa

```
REGISTRY/
├── NAMESPACE (organization/team/environment)/
│   ├── REPOSITORY (application name)/
│   │   ├── TAG (version)
│   │   └── TAG
│   └── REPOSITORY/
└── NAMESPACE/
```

Ejemplo de estructura ECR:

```
123456789012.dkr.ecr.us-east-1.amazonaws.com/
├── platform/
│   ├── ingress-controller:<supported-version>
│   ├── cert-manager:<supported-version>
│   └── external-dns:<supported-version>
├── myapp/
│   ├── api:v2.1.0
│   ├── web:v2.1.0
│   └── worker:v2.1.0
└── tools/
    ├── kubectl:<cluster-compatible-version>
    └── helm:<supported-version>
```

### Prefijos de entorno

Para estrategias con un solo repositorio:

```
myapp:v1.2.3                 # Production release
myapp:v1.2.3-staging         # Staging candidate
myapp:abc123f-dev            # Development build
myapp:abc123f-feature-auth   # Feature branch
```

### Imágenes multiarquitectura

Usa listas de manifiestos para admitir varias arquitecturas:

```bash
# Build for multiple architectures
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --tag myregistry.com/myapp:v1.0.0 \
  --push .

# Inspect manifest
docker manifest inspect myregistry.com/myapp:v1.0.0
```

Convenciones de tags para imágenes específicas de una arquitectura (si hacen falta):

```
myapp:v1.0.0           # Manifest list (preferred)
myapp:v1.0.0-amd64     # AMD64-specific
myapp:v1.0.0-arm64     # ARM64-specific
```

## Réplica y caché de registros

### ¿Por qué replicar o usar una caché?

1. **Evitar límites de frecuencia**: Docker Hub limita las descargas.
2. **Mejorar el rendimiento**: la caché local reduce la latencia.
3. **Fiabilidad**: las réplicas precargadas reducen dependencias; las fallas de caché/actualizaciones todavía requieren acceso upstream.
4. **Seguridad**: control sobre las imágenes que entran en el entorno.
5. **Ahorro de costos**: reducir los costos de transferencia entre regiones y desde Internet.

![Árbol de decisión para elegir una estrategia de caché o réplica: primero pregunta si el problema son los límites de frecuencia del registro o la disponibilidad/rendimiento; los casos de límite de frecuencia se dividen por entorno (AWS/EKS, autohospedado o una réplica simple) y los de rendimiento por necesidad de infraestructura (aislada, multirregión o perimetral).](../.gitbook/assets/en-container-registry-04-best-practices-1.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-container-registry-04-best-practices-1.html)

### Comparación de cachés pull-through

| Función | ECR Pull-Through | Proxy Harbor | Distribution |
|---------|-----------------|--------------|--------------|
| Administrado | Sí | No | No |
| Compatibilidad upstream | Upstreams admitidos por ECR | Adaptadores admitidos por Harbor | Docker Hub |
| Autenticación | Secrets Manager | Integrada | Variables de entorno |
| Análisis | Según la configuración de análisis del repositorio/registro | Según la configuración del proyecto/scanner | Sin scanner integrado |
| Alta disponibilidad | Integrada | Autoadministrada | Autoadministrada |

### Configuración de ECR Pull-Through Cache

Guarda las credenciales de Docker Hub en Secrets Manager en la misma cuenta/región, bajo el prefijo `ecr-pullthroughcache/`, con las claves `username` y `accessToken`. Resuelve el ARN real del secreto en lugar de construirlo. Consulta [Amazon ECR](02-amazon-ecr.md) para conocer los permisos de creación/importación del repositorio y el rol vinculado al servicio.

```bash
# The upstream secret must already exist in this account and region.
: "${AWS_REGION:?Set the target AWS region}"
SECRET_ARN=$(aws secretsmanager describe-secret --region "$AWS_REGION" \
  --secret-id ecr-pullthroughcache/docker-hub --query ARN --output text)
aws ecr create-pull-through-cache-rule --region "$AWS_REGION" \
  --ecr-repository-prefix docker-hub \
  --upstream-registry-url registry-1.docker.io \
  --credential-arn "$SECRET_ARN"
```

URI de descarga: `ACCOUNT.dkr.ecr.REGION.amazonaws.com/docker-hub/library/nginx:1.30.6`. Las fallas de caché y las actualizaciones todavía dependen del acceso upstream.

### Configuración de réplica de Containerd

Este ejemplo supone una réplica confiable que ofrece las mismas rutas de repositorio de Docker Hub. Containerd 2.x usa `config_path` del plugin de imágenes; 1.x usa la ruta del plugin CRI. La capacidad `resolve` confía en las decisiones de la réplica al asignar tags a digest. Esto no traduce automáticamente los prefijos de proyecto de ECR/Harbor ni sus credenciales.

```toml
# containerd 2.x: /etc/containerd/config.toml
[plugins."io.containerd.cri.v1.images".registry]
  config_path = "/etc/containerd/certs.d"
# For containerd 1.x, use plugins."io.containerd.grpc.v1.cri".registry.
```

```toml
# /etc/containerd/certs.d/docker.io/hosts.toml
server = "https://registry-1.docker.io"
[host."https://mirror.example.com"]
  capabilities = ["pull", "resolve"]
  ca = "/etc/containerd/certs.d/docker.io/mirror-ca.crt"
```

El `server` permite recurrir a Docker Hub, así que esta configuración no funciona solo sin conexión. Para redes desconectadas y cachés ECR/Harbor autenticadas, usa URI de imagen internas explícitas y valida la confianza de CA de los nodos, `imagePullSecrets` y las descargas reales.

### Configuración de caché proxy de Harbor

```bash
# 1. Create registry endpoint
curl --fail-with-body -X POST "https://harbor.example.com/api/v2.0/registries" \
  -H "Content-Type: application/json" \
  --user "$HARBOR_USER" \
  -d '{
    "name": "docker-hub",
    "type": "docker-hub",
    "url": "https://hub.docker.com",
    "credential": {
      "type": "basic",
      "access_key": "username",
      "access_secret": "password"
    }
  }'

# 2. Create proxy cache project
curl --fail-with-body -X POST "https://harbor.example.com/api/v2.0/projects" \
  -H "Content-Type: application/json" \
  --user "$HARBOR_USER" \
  -d '{
    "project_name": "dockerhub-cache",
    "registry_id": 1,
    "metadata": {"public": "true"}
  }'

# Usage: harbor.example.com/dockerhub-cache/library/nginx:latest
```

## Recuperación ante desastres

### Estrategia multirregión

```
┌─────────────────────────────────────────────────────────────────┐
│                    Primary Region (us-east-1)                    │
│  ┌─────────────┐                                                │
│  │  ECR / Harbor│──────────────────┐                            │
│  └─────────────┘                   │                            │
└────────────────────────────────────┼────────────────────────────┘
                                     │ Replication
                                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DR Region (eu-west-1)                         │
│  ┌─────────────┐                                                │
│  │  ECR / Harbor│                                                │
│  └─────────────┘                                                │
└─────────────────────────────────────────────────────────────────┘
```

### Replicación entre regiones de ECR

```hcl
resource "aws_ecr_replication_configuration" "dr" {
  replication_configuration {
    rule {
      destination {
        region      = "eu-west-1"
        registry_id = data.aws_caller_identity.current.account_id
      }

      # Only replicate production images
      repository_filter {
        filter      = "prod-"
        filter_type = "PREFIX_MATCH"
      }
    }
  }
}
```

### Réplica de Harbor para recuperación ante desastres

```bash
# Configure DR Harbor as endpoint
# Add destination credentials through the protected Harbor UI before using this endpoint.
curl --fail-with-body -X POST "https://harbor-primary.example.com/api/v2.0/registries" \
  -H "Content-Type: application/json" \
  --user "$HARBOR_USER" \
  -d '{
    "name": "harbor-dr",
    "type": "harbor",
    "url": "https://harbor-dr.example.com"
  }'

# Create event-based replication
curl --fail-with-body -X POST "https://harbor-primary.example.com/api/v2.0/replication/policies" \
  -H "Content-Type: application/json" \
  --user "$HARBOR_USER" \
  -d '{
    "name": "dr-replication",
    "dest_registry": {"id": 1},
    "trigger": {"type": "event_based"},
    "enabled": true,
    "replicate_deletion": false
  }'
```

### Procedimientos de copia de seguridad y RTO/RPO

La replicación de ECR es asíncrona y se aplica a las imágenes enviadas/restauradas después de configurarla; los artefactos existentes requieren una carga inicial retroactiva. Valida las políticas, permisos, análisis, cifrado, ajustes del ciclo de vida y descargas reales del destino. La API de configuración de replicación reemplaza la configuración del registro, así que primero combina las reglas existentes.

Mide RPO/RTO en ejercicios de recuperación que incluyan el retraso de replicación, detección, disponibilidad de artefactos/firmas y conmutación por error de clúster/DNS. La replicación de eventos no garantiza RPO cero ni un RTO de cinco minutos. La replicación de eliminaciones también puede borrar la copia de recuperación, así que diseña una copia de seguridad independiente.

Unos pocos tags descargados/guardados con Docker no constituyen una copia de seguridad completa. Conserva un inventario de digests probados, todas las plataformas de destino, manifiestos OCI, firmas/SBOM y las instrucciones de restauración. Usa un inventario/checksums explícitos como en el [procedimiento de transferencia Skopeo de Harbor](03-harbor.md); respalda de forma coherente los metadatos, blobs, configuración y claves de Harbor. Un archivo tar en S3 no es un registro desde el que Kubernetes pueda descargar; impórtalo en un registro de recuperación.

## Optimización de costos

### Estimación de costos

Estima por separado almacenamiento, transferencia regional/AZ/Internet, análisis/firma, PrivateLink/NAT, cómputo/base de datos/copias de seguridad del registro y operación. Un precio regional ilustrativo de ECR de `$0.10/GB-month` no representa la factura completa. Sumar `imageSizeInBytes` no equivale al almacenamiento facturado de capas deduplicadas. Un umbral fijo como 500 GB no determina si ECR o Harbor es más barato.

### Aspectos esenciales de la política del ciclo de vida

El siguiente ejemplo ECR expira tres prefijos de tags de desarrollo después de 30 días en un repositorio exclusivo para desarrollo. Varios patrones en un mismo `tagPatternList` funcionan como **AND**, no OR; usa una regla independiente por prefijo. No mezcles tags de lanzamiento/desarrollo en un mismo digest; usa Lifecycle Preview para proteger los digests desplegados/de reversión. Las imágenes sin tag aún pueden desplegarse por digest y no es automáticamente seguro eliminarlas.

```json
{
  "rules": [
    {
      "rulePriority": 1,
      "description": "Expire dev-* development artifacts after 30 days",
      "selection": {
        "tagStatus": "tagged",
        "tagPatternList": [
          "dev-*"
        ],
        "countType": "sinceImagePushed",
        "countNumber": 30,
        "countUnit": "days"
      },
      "action": {
        "type": "expire"
      }
    },
    {
      "rulePriority": 2,
      "description": "Expire feature-* development artifacts after 30 days",
      "selection": {
        "tagStatus": "tagged",
        "tagPatternList": [
          "feature-*"
        ],
        "countType": "sinceImagePushed",
        "countNumber": 30,
        "countUnit": "days"
      },
      "action": {
        "type": "expire"
      }
    },
    {
      "rulePriority": 3,
      "description": "Expire pr-* development artifacts after 30 days",
      "selection": {
        "tagStatus": "tagged",
        "tagPatternList": [
          "pr-*"
        ],
        "countType": "sinceImagePushed",
        "countNumber": 30,
        "countUnit": "days"
      },
      "action": {
        "type": "expire"
      }
    }
  ]
}
```

La retención de Harbor usa la unión OR de reglas de retención y un esquema distinto del de ECR. Sigue el procedimiento de vista previa en seco por UI/API de [Harbor](03-harbor.md) y verifica la recolección de basura después de eliminar.

### Optimización del tamaño de imagen

Usa imágenes de compilación y ejecución compatibles, y copia únicamente dependencias necesarias en ejecución. Este ejemplo Python transfiere un entorno virtual entre versiones iguales de la imagen base de Python. Aun así, hay que validar los requisitos de extensiones nativas/bibliotecas del sistema. Excluye secretos, entornos virtuales locales y cachés del contexto de compilación mediante `.dockerignore`.

```dockerfile
FROM python:3.14-slim AS builder
WORKDIR /app
RUN python -m venv /opt/venv
COPY requirements.txt .
RUN /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

FROM python:3.14-slim
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY --chown=10001:10001 . .
ENV PATH="/opt/venv/bin:$PATH"
USER 10001:10001
CMD ["python", "app.py"]
```

El tamaño de imagen varía según la aplicación, arquitectura, compresión y dependencias. Distroless no elimina vulnerabilidades automáticamente; valida la ABI de compilación/ejecución, certificados CA, ID de usuario y procedimientos de depuración. Fija los digests probados de imágenes base y el bloqueo de dependencias para los lanzamientos, y luego actualízalos con regularidad.

### Reducción de costos de transferencia

Usa referencias de registro locales a la región y verifica la replicación antes de la conmutación por error. Los endpoints de VPC pueden reducir el tráfico NAT, pero incluye los costos por hora/datos de los endpoints de interfaz y las rutas de ECR API/DKR más S3. Consulta [Amazon ECR](02-amazon-ecr.md) para ver overlays Kustomize regionales completos.

## Lista de comprobación de seguridad

### Análisis de imágenes

Docker Hub usa Docker Scout; ECR ofrece análisis básico nativo de AWS o análisis mejorado basado en Inspector; Harbor usa el scanner Trivy/externo que tenga configurado. Comprueba los precios, artefactos admitidos, nuevo análisis y actualidad de la base de datos. El análisis automático está separado de la aplicación de políticas de despliegue; resultados fallidos/incompletos no significan cero hallazgos. Sigue los procedimientos actuales de [ECR](02-amazon-ecr.md) y [Harbor](03-harbor.md).

### Controladores de admisión

Combina la [verificación de firmas de imágenes](../security/07-image-security.md) con las [políticas de registro de Kyverno](../security/01-kyverno-policy-management.md). Una lista permitida de registros no verifica firmas ni busca vulnerabilidades. Las atestaciones de vulnerabilidad requieren firmantes confiables, el esquema/campos reales del predicado y actualidad del análisis. No supongas que existe un campo `criticalCount` ni apliques una clave pública truncada.

Prueba contenedores normales/init/efímeros y cobertura CREATE/UPDATE en modo Audit antes de Enforce. Una restricción de Gatekeeper requiere instalar primero su ConstraintTemplate correspondiente.

### Acceso con privilegios mínimos

Esta política permite descargar de repositorios ECR seleccionados. `GetAuthorizationToken` no admite permisos de recursos a nivel de repositorio y necesita `Resource: "*"`; las acciones reales de descarga sí están acotadas por ARN. En EKS, adjunta los permisos al rol del nodo o al rol de ejecución del Pod de Fargate. El rol IRSA/Pod Identity de la aplicación no proporciona credenciales para su propia descarga inicial de imagen.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "RegistryToken",
      "Effect": "Allow",
      "Action": "ecr:GetAuthorizationToken",
      "Resource": "*"
    },
    {
      "Sid": "PullApprovedRepositories",
      "Effect": "Allow",
      "Action": [
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage"
      ],
      "Resource": [
        "arn:aws:ecr:ap-northeast-2:123456789012:repository/myapp-prod",
        "arn:aws:ecr:ap-northeast-2:123456789012:repository/base-images/*"
      ]
    }
  ]
}
```

Para Harbor, usa cuentas robot de solo descarga con alcance de proyecto y vencimiento/rotación. Sigue el esquema actual de `/api/v2.0/robots` y el procedimiento de `imagePullSecrets` limitado al namespace en [Harbor](03-harbor.md).

### Políticas de red

NetworkPolicy de Kubernetes controla el tráfico de los Pods seleccionados. No supongas que una política de salida del Pod controla las descargas de imágenes que realiza kubelet/containerd en el nodo. Valida los registros permitidos en admisión y controla el acceso del nodo al registro, DNS y ECR API/DKR/S3 en la capa de nodo/red. Las políticas de salida de Pods de aplicación también deben permitir DNS y el tráfico necesario para la aplicación.

### Administración de secretos

Se requieren CRD que sirvan la API v1 de External Secrets Operator y un ClusterSecretStore configurado. Guarda el JSON completo y válido de configuración Docker en el secreto remoto; pasar el JSON completo evita dañar contraseñas con comillas o barras invertidas durante la interpolación de cadenas. Haz referencia al Secret resultante desde un Pod/ServiceAccount del mismo namespace.

```yaml
apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: registry-credentials
  namespace: production
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: ClusterSecretStore
  target:
    name: registry-pull-secret
    creationPolicy: Owner
    template:
      engineVersion: v2
      type: kubernetes.io/dockerconfigjson
      data:
        .dockerconfigjson: "{{ .dockerconfigjson | toString }}"
  data:
  - secretKey: dockerconfigjson
    remoteRef:
      key: harbor-pull-dockerconfigjson
```

Copiar repetidamente un token ECR guardado no renueva su vigencia de 12 horas. Usa la identidad nativa de extracción de imágenes de EKS o un generador de tokens ECR configurado explícitamente. Supervisa errores de autorización, cifrado y rotación del secret store.

## Patrones de integración CI/CD

### GitHub Actions con ECR

Este ejemplo compila una sola imagen Linux/amd64 en Docker local, analiza **esa imagen**, y luego la publica y firma. Prepara el repositorio ECR, un rol IAM OIDC restringido por `aud`/`sub`, permisos de publicación y un runner compatible. Las Actions están fijadas a commits de versiones revisadas. Si volver a compilar el mismo commit entra en conflicto con un tag inmutable, reutiliza su digest verificado o asigna un ID de compilación nuevo.

```yaml
name: Build scan and publish to ECR
on:
  push:
    branches: [main]
    tags: ['v*']
permissions:
  contents: read
  id-token: write
env:
  AWS_REGION: ap-northeast-2
  ECR_REPOSITORY: myapp
jobs:
  publish:
    runs-on: ubuntu-24.04
    steps:
    - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
    - uses: aws-actions/configure-aws-credentials@e1253824e5c10ff9df46874f81ed3ec929e19cfd # v6.3.0
      with:
        role-to-assume: arn:aws:iam::123456789012:role/github-actions-ecr
        aws-region: ${{ env.AWS_REGION }}
    - uses: aws-actions/amazon-ecr-login@03f1aad4c6c7ffd436567f42f9384779290529bd # v2.1.7
      id: login
    - uses: docker/setup-buildx-action@f87e5991a6d7451dcb8d9637bfbc97413f497069 # v4.4.1
    - uses: docker/build-push-action@c3c9e263c25d99ce0380d002d59b67737d91b0dc # v7.4.0
      with:
        context: .
        platforms: linux/amd64
        load: true
        push: false
        tags: ${{ steps.login.outputs.registry }}/${{ env.ECR_REPOSITORY }}:${{ github.sha }}
        cache-from: type=gha
        cache-to: type=gha,mode=max
    - uses: aquasecurity/trivy-action@ed142fd0673e97e23eac54620cfb913e5ce36c25 # v0.36.0
      with:
        version: v0.76.0
        image-ref: ${{ steps.login.outputs.registry }}/${{ env.ECR_REPOSITORY }}:${{ github.sha }}
        scan-type: image
        scanners: vuln
        exit-code: '1'
        severity: HIGH,CRITICAL
    - name: Publish scanned image and record digest
      id: publish
      env:
        REGISTRY: ${{ steps.login.outputs.registry }}
      run: |
        set -euo pipefail
        IMAGE="$REGISTRY/$ECR_REPOSITORY"
        docker push "$IMAGE:$GITHUB_SHA"
        DIGEST=$(aws ecr describe-images --repository-name "$ECR_REPOSITORY" \
          --image-ids "imageTag=$GITHUB_SHA" --query 'imageDetails[0].imageDigest' --output text)
        [[ "$DIGEST" =~ ^sha256:[a-f0-9]{64}$ ]]
        printf 'image=%s@%s\n' "$IMAGE" "$DIGEST" >> "$GITHUB_OUTPUT"
    - uses: sigstore/cosign-installer@6f9f17788090df1f26f669e9d70d6ae9567deba6 # v4.1.2
    - name: Sign the published digest with the job OIDC identity
      env:
        SIGNED_IMAGE: ${{ steps.publish.outputs.image }}
      run: cosign sign --yes "$SIGNED_IMAGE"
```

Para un lanzamiento multiplataforma, analiza cada plataforma y promociona el digest del índice final. Usa `publish.outputs.image` para el despliegue y la verificación de firma; un tag SemVer coincidente por sí solo no aprueba un lanzamiento. La verificación sin clave necesita una política de admisión limitada al emisor/identidad OIDC de este flujo de trabajo. Si añades carga de SARIF, configura la elegibilidad de Code Scanning y `security-events: write`.

### GitLab CI con Harbor

Este ejemplo de Docker executor usa DinD con TLS habilitado. Configura el modo privilegiado necesario y un volumen compartido `/certs/client` en un runner dedicado y aislado. Proporciona credenciales robot de proyecto en variables protegidas y enmascaradas `HARBOR_USERNAME`/`HARBOR_PASSWORD`, y confía en la CA de Harbor. El análisis y la publicación usan el mismo artefacto compilado, y la publicación depende de que el análisis tenga éxito.

```yaml
stages: [build, scan, publish]
workflow:
  rules:
    - if: '$CI_COMMIT_BRANCH == "main" || $CI_COMMIT_TAG'
variables:
  HARBOR_HOST: harbor.example.com
  IMAGE_NAME: harbor.example.com/myapp/app
  DOCKER_HOST: tcp://docker:2376
  DOCKER_TLS_CERTDIR: /certs
  DOCKER_TLS_VERIFY: "1"
  DOCKER_CERT_PATH: /certs/client
.docker:
  image: docker:29.9.0-cli
  services:
    - name: docker:29.9.0-dind
      alias: docker
build:
  extends: .docker
  stage: build
  script:
    - docker build -t "$IMAGE_NAME:$CI_COMMIT_SHA" .
    - docker save "$IMAGE_NAME:$CI_COMMIT_SHA" -o image.tar
  artifacts:
    paths: [image.tar]
    expire_in: 1 day
scan:
  stage: scan
  image:
    name: aquasec/trivy:0.76.0
    entrypoint: [""]
  needs:
    - job: build
      artifacts: true
  script:
    - trivy image --input image.tar --exit-code 1 --severity HIGH,CRITICAL
publish:
  extends: .docker
  stage: publish
  needs:
    - job: build
      artifacts: true
    - job: scan
      artifacts: false
  script:
    - printf '%s' "$HARBOR_PASSWORD" | docker login "$HARBOR_HOST" --username "$HARBOR_USERNAME" --password-stdin
    - docker load -i image.tar
    - docker push "$IMAGE_NAME:$CI_COMMIT_SHA"
```

### Despliegue y actualización de imágenes

Después de las aprobaciones de análisis/firma, actualiza el repositorio GitOps con el digest verificado y aplica aprobación, verificación de admisión y comprobaciones de rollout. Argo CD Image Updater 1.x usa un recurso `ImageUpdater`; copiar únicamente las anotaciones antiguas de Application no basta. Instala sus CRD correspondientes y configura acceso de Argo CD, credenciales de registro y autorización de escritura de Git según la política de aprobación de lanzamientos.

## Administración de imágenes con skopeo

[skopeo](https://github.com/containers/skopeo) es una herramienta de línea de comandos para inspeccionar, copiar y sincronizar imágenes de contenedores entre registros. Funciona sin un daemon de Docker y no requiere privilegios de root, por lo que es ideal para canalizaciones CI/CD y escenarios aislados de la red.

### Instalación

```bash
# RHEL/CentOS/Amazon Linux
sudo yum install -y skopeo

# Ubuntu/Debian
sudo apt-get install -y skopeo

# macOS
brew install skopeo
```

### skopeo inspect: inspección de imágenes remotas

Inspecciona metadatos de una imagen sin descargarla:

```bash
# Inspect Docker Hub image
skopeo inspect docker://docker.io/library/nginx:1.30.6

# Inspect ECR image (requires AWS auth)
skopeo inspect docker://123456789012.dkr.ecr.us-east-1.amazonaws.com/myapp:v1.0.0

# View raw manifest
skopeo inspect --raw docker://docker.io/library/nginx:1.30.6 | jq .

# Inspect specific architecture
skopeo --override-arch arm64 inspect docker://docker.io/library/nginx:1.30.6
```

### skopeo copy: copia de imágenes entre registros

Copia imágenes directamente entre registros sin descargarlas al equipo local:

```bash
# Docker Hub → ECR
skopeo copy --all \
  docker://docker.io/library/nginx:1.30.6 \
  docker://123456789012.dkr.ecr.us-east-1.amazonaws.com/nginx:1.30.6

# ECR → Harbor
skopeo copy --all \
  docker://123456789012.dkr.ecr.us-east-1.amazonaws.com/myapp:v1.0.0 \
  docker://harbor.example.com/myapp/backend:v1.0.0

# Format conversion (Docker → OCI)
skopeo copy --all \
  docker://docker.io/library/nginx:1.30.6 \
  oci:nginx-oci:1.30.6

# Save as OCI archive
skopeo copy --all \
  docker://docker.io/library/nginx:1.30.6 \
  oci-archive:nginx-1.30.6.tar
```

### skopeo sync: sincronización masiva de registros

Previsualiza los tags explícitos antes de sincronizar. Especificar un repositorio sin tag puede copiar todos sus tags. Cada valor `images-by-tag-regex` es una cadena, no una lista. `--scoped` conserva los componentes de registro/ruta de origen para evitar colisiones de nombres; prepara por separado los proyectos/repositorios de destino y la autenticación.

```bash
cat > sync-manifest.yaml <<'YAML'
docker.io:
  images:
    library/nginx:
      - "1.30.6"
  images-by-tag-regex:
    library/busybox: '^1\.38\.0$'
YAML
# Preview exact source/destination paths before creating target repositories.
skopeo sync --all --scoped --dry-run --src yaml --dest docker \
  sync-manifest.yaml harbor.internal/mirror
# After reviewing the preview and preparing destinations, remove --dry-run.
```

### Transferencia a una red aislada

skopeo es excelente para transferir imágenes a entornos desconectados:

```bash
# Step 1: Export images to tar on connected environment
skopeo copy --all docker://docker.io/library/nginx:1.30.6 oci-archive:nginx-1.30.6.tar
skopeo copy --all docker://docker.io/library/redis:7-alpine oci-archive:redis-7.tar
skopeo copy --all docker://registry.k8s.io/pause:3.10 oci-archive:pause-3.10.tar

# Step 2: Transfer via USB/secure file transfer to air-gapped environment

# Step 3: Import into Harbor on air-gapped environment
skopeo copy --all oci-archive:nginx-1.30.6.tar \
  docker://harbor.internal/library/nginx:1.30.6
skopeo copy --all oci-archive:redis-7.tar \
  docker://harbor.internal/library/redis:7-alpine
skopeo copy --all oci-archive:pause-3.10.tar \
  docker://harbor.internal/k8s/pause:3.10
```

> **Consejo:** a diferencia de `docker save/load`, skopeo funciona sin un daemon Docker, así que se puede usar en servidores aislados de la red donde no está instalado Docker.

### Comparación de herramientas

| Herramienta | Función en esta guía | Condiciones que hay que verificar |
|---|---|---|
| Skopeo | Inspección remota, copia/sincronización, archivos OCI | Autenticación, conversión de manifiestos, `--all`, compatibilidad con referrers |
| Docker/Buildx | Compilación, inspección de manifiestos, publicación | Configuración del daemon/compilador; también hay configuraciones rootless |
| crane | Inspección/copia remota de imágenes | Compatibilidad de copia/exportación y firmas de la versión instalada |
| ctr | Almacén/importación/exportación de imágenes containerd | Permisos de socket de ejecución, namespace y selección de plataforma |

`--all` selecciona manifiestos de plataformas; no garantiza que se copie cada referrer de firma/SBOM. Usa `--preserve-digests` cuando sea necesario conservar el digest y trata los fallos como fallos. Sigue en [Harbor](03-harbor.md) el procedimiento de mapeo, checksums, base de datos, CA y restauración para transportar datos sin conexión.

## Resumen

### Puntos clave

1. **Administración de tags**
   - Usa tags inmutables en producción.
   - Sigue SemVer para lanzamientos.
   - Nunca uses `latest` en producción.
   - Implementa flujos de promoción.

2. **Convenciones de nombres**
   - Define una estructura de namespace uniforme.
   - Usa prefijos de entorno para estrategias con un solo repositorio.
   - Admite imágenes multiarquitectura.

3. **Réplica y caché**
   - Implementa caché pull-through para evitar límites de frecuencia.
   - Replica las imágenes externas críticas.
   - Usa rutas de réplica/autenticación validadas o URI de imagen internas explícitas.

4. **Recuperación ante desastres**
   - Habilita la replicación entre regiones.
   - Define y prueba objetivos RTO/RPO.
   - Automatiza los procedimientos de copia de seguridad.

5. **Optimización de costos**
   - Implementa políticas de ciclo de vida en todos lados.
   - Optimiza el tamaño de imagen con compilaciones multietapa.
   - Usa endpoints regionales para reducir costos de transferencia.

6. **Seguridad**
   - Habilita el análisis al publicar.
   - Implementa controladores de admisión.
   - Aplica el principio de privilegio mínimo.
   - Usa políticas de red.

7. **Integración CI/CD**
   - Automatiza canalizaciones de compilación-análisis-firma-despliegue.
   - Usa OIDC para autenticación en la nube.
   - Implementa controles de seguridad.

### Matriz de referencia rápida

| Práctica | Docker Hub | ECR | Harbor |
|----------|------------|-----|--------|
| Tags inmutables | Mutabilidad de tags (Beta) | `IMMUTABLE` | Reglas de inmutabilidad de tags |
| Políticas de ciclo de vida | Limpieza por API | Nativa | Retención de tags |
| Análisis de vulnerabilidades | Docker Scout | AWS nativo/Inspector | Trivy o scanner configurado |
| Firma de imágenes | Firma externa/artefactos OCI; verifica compatibilidad | Firmante/artefactos OCI | Cosign/Notation |
| Replicación | N/A | Entre regiones | Push/Pull |
| Caché pull-through | N/A | Nativa | Proyecto proxy |

### Lista de comprobación de nuevos despliegues

- [ ] Convención de nombres del repositorio documentada
- [ ] Estrategia de tags definida y aplicada
- [ ] Políticas de ciclo de vida configuradas
- [ ] Análisis de vulnerabilidades habilitado
- [ ] Firma de imágenes implementada
- [ ] Replicación DR configurada
- [ ] Controles de acceso (RBAC/IAM) configurados
- [ ] Canalización CI/CD integrada
- [ ] Supervisión y alertas configuradas
- [ ] Supervisión de costos habilitada
- [ ] Procedimientos de copia de seguridad probados

## Referencias

- [Tags inmutables de Docker Hub](https://docs.docker.com/docker-hub/repos/manage/hub-images/immutable-tags/)
- [Gramática de tags de imagen](https://github.com/distribution/reference/blob/main/regexp.go)
- [Configuración de registros de containerd](https://github.com/containerd/containerd/blob/main/docs/hosts.md)
- [Skopeo copy](https://github.com/containers/skopeo/blob/main/docs/skopeo-copy.1.md)
- [Skopeo sync](https://github.com/containers/skopeo/blob/main/docs/skopeo-sync.1.md)
- [Configuración Docker de External Secrets](https://external-secrets.io/latest/guides/common-k8s-secret-types/)
- [Configuración de imágenes de Argo CD Image Updater 1.3](https://github.com/argoproj-labs/argocd-image-updater/blob/v1.3.1/docs/configuration/images.md)
- [Acción Docker build-push](https://github.com/docker/build-push-action/tree/v7.4.0)
- [Acción Trivy](https://github.com/aquasecurity/trivy-action/tree/v0.36.0)
- [Docker-in-Docker TLS de GitLab](https://docs.gitlab.com/ci/docker/using_docker_build/)
