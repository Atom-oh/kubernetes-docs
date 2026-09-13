# Seguridad de imágenes de contenedor

> **Última actualización**: September 13, 2026
> **Base de validación**: Trivy 0.74.0, Trivy Operator 0.34.0/chart 0.36.0, Cosign 3.1.3, Kyverno 1.19.1, Connaisseur 3.12.0/chart 2.12.0. Estas son bases de referencia de CLI/configuración, no una afirmación de pruebas de implementación en todas las versiones de Kubernetes.

La seguridad de las imágenes comienza confirmando que **el artefacto compilado, escaneado y desplegado es el mismo**. El escaneo identifica vulnerabilidades conocidas y problemas de configuración; las firmas vinculan a un firmante con un digest. Ninguno garantiza la seguridad de la aplicación.

## Tabla de contenido

1. [Descripción general del escaneo de imágenes](#image-scanning-overview)
2. [Trivy](#trivy)
3. [Escaneo de imágenes de Amazon ECR](#amazon-ecr-image-scanning)
4. [Firma de imágenes con Cosign/Sigstore](#image-signing-with-cosignsigstore)
5. [Verificación de imágenes en el control de admisión](#image-verification-in-admission-control)
6. [Seguridad de la cadena de suministro](#supply-chain-security)
7. [Selección de imagen base](#base-image-selection)
8. [Prácticas recomendadas para el registro de imágenes](#image-registry-best-practices)
9. [Integración de la canalización de CI/CD](#cicd-pipeline-integration)

<span id="shift-left-security"></span>
<span id="scan-targets"></span>

## Descripción general del escaneo de imágenes

Shift-left introduce verificaciones en el IDE, PR y compilación. Aparecen nuevos CVE después del lanzamiento, por lo que el reescaneo del registro y la detección en tiempo de ejecución siguen siendo requisitos independientes.

| Objetivo | Verificación | Herramientas de ejemplo |
|---|---|---|
| Paquetes de SO/lenguaje | Identificación, antigüedad de la base de datos, versiones corregidas, decisiones VEX | Trivy, Grype |
| IaC/Dockerfiles | Ejecución sin root, permisos, configuración | Trivy misconfig, Checkov |
| Secretos | Credenciales en capas de imagen o código fuente | Trivy secret, TruffleHog |
| Licencias/SBOM | Cobertura de detección de componentes y licencias | Syft, Trivy |
| Comportamiento en tiempo de ejecución | Syscalls, procesos y red activos | Herramientas independientes como Falco |

El flujo es `source checks → build once → scan that artifact → push → sign/verify digest → admission checks → rescan`. Las organizaciones definen controles por gravedad y asignan a las excepciones un responsable, una justificación y una fecha de vencimiento.

<span id="trivy-installation"></span>
<span id="image-scanning"></span>
<span id="filesystem-scanning"></span>
<span id="trivy-configuration-file"></span>
<span id="trivy-operator-kubernetes-integration"></span>

## Trivy

### Instalación y escaneo

Verifique el paquete de lanzamiento oficial para el sistema operativo/arquitectura de CPU y su suma de verificación. No instale un binario amd64 en Linux ARM64 ni use instrucciones apt-key retiradas. Fije las versiones de CLI/action en la automatización.

```bash
trivy --version
# Replace with an immutable reference that you actually own.
IMAGE_REF='registry.example.com/team/app@sha256:REPLACE_WITH_64_HEX_DIGEST'
trivy image --severity HIGH,CRITICAL --exit-code 1 "$IMAGE_REF"
trivy image --format json --output results.json "$IMAGE_REF"
trivy image --format sarif --output results.sarif "$IMAGE_REF"
trivy image --scanners vuln,secret "$IMAGE_REF"
trivy fs --scanners vuln,secret,misconfig .
trivy config ./k8s/
trivy config ./charts/my-app/ --helm-values ./charts/my-app/values.yaml
```

`IMAGE_REF` es un marcador de posición intencional que requiere un digest real. Use `misconfig`, no `--scanners config`. `--ignore-unfixed` oculta vulnerabilidades sin correcciones, por lo que no lo habilite indiscriminadamente en el control predeterminado. Verifique los requisitos de red/caché para registros, bases de datos de vulnerabilidades/Java y paquetes de verificaciones. `trivy config` no tiene una opción `--offline-scan`.

### Configuración y excepciones

```yaml
# Baseline for image/filesystem scans; explicitly review exceptions in .trivyignore.
severity:
  - HIGH
  - CRITICAL
exit-code: 1
ignorefile: .trivyignore
scan:
  scanners:
    - vuln
    - secret
    - misconfig
  parallel: 2
  disable-telemetry: true
vulnerability:
  ignore-unfixed: false
```

Esta es una base de referencia de escaneo de imágenes/sistema de archivos. No añada vulnerability.type no compatible ni una lista de ignorados de nivel superior. Administre las excepciones mediante los formatos .trivyignore/política de ignorados compatibles, diferenciando las excepciones de secretos y de vulnerabilidades. El ejemplo de .trivyignore no tiene exclusiones predeterminadas.

<span id="trivy-overview"></span>

### Trivy Operator

```bash
helm repo add aqua https://aquasecurity.github.io/helm-charts/
helm repo update aqua
helm upgrade --install trivy-operator aqua/trivy-operator   --version 0.36.0 --namespace trivy-system --create-namespace   --values trivy-operator-values.yaml
kubectl get vulnerabilityreports -A
```

Chart 0.36.0 despliega la aplicación 0.34.0. El [archivo de valores](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/image-security/trivy-operator-values.yaml) establece explícitamente ignoreUnfixed:false. Los informes son resultados generados por el Operator; no aplique un manifiesto fabricado de CVE/versión de paquete como evidencia de escaneo. Verifique el esquema real de los informes, los namespaces observados, las credenciales de registro, los privilegios del scan-Job y los recursos. Esta auditoría solo renderizó el chart.

<span id="basic-scanning-vs-enhanced-scanning"></span>
<span id="enabling-enhanced-scanning"></span>
<span id="retrieving-scan-results"></span>
<span id="notifications-via-eventbridge"></span>

## Escaneo de imágenes de Amazon ECR

| Propiedad | Básico | Mejorado |
|---|---|---|
| Motor actual | Escáner nativo de AWS | Amazon Inspector |
| Cobertura | Vulnerabilidades de paquetes de SO | Paquetes de SO y de lenguaje compatibles |
| Frecuencia | Manual o scan-on-push | Scan-on-push o continuo |
| Resultados | imageScanFindings.findings | imageScanFindings.enhancedFindings |
| Eventos | Finalización del escaneo básico de ECR | Eventos de escaneo/hallazgos de Inspector2 |

Distinga las descripciones antiguas de Clair del motor Basic actual. Cambiar los modos de escaneo puede modificar la visibilidad de los resultados establecidos. La cobertura mejorada depende de los filtros de repositorio, la duración del reescaneo y los criterios de imágenes compatibles; no todas las imágenes se escanean para siempre. Las imágenes archivadas deben restaurarse antes del escaneo.

```bash
aws ecr put-registry-scanning-configuration --scan-type ENHANCED --rules '[
  {"repositoryFilters":[{"filter":"production/*","filterType":"WILDCARD"}],"scanFrequency":"CONTINUOUS_SCAN"},
  {"repositoryFilters":[{"filter":"development/*","filterType":"WILDCARD"}],"scanFrequency":"SCAN_ON_PUSH"}
]'
# Enhanced results. For Basic, query findings instead of enhancedFindings.
aws ecr describe-image-scan-findings --repository-name production/my-app   --image-id imageDigest=sha256:REPLACE_WITH_64_HEX_DIGEST   --query 'imageScanFindings.enhancedFindings[?severity==`CRITICAL`]'
```

El comando de configuración escribe la configuración del registro y no fue ejecutado por esta auditoría. Use DescribeImageScanFindings en lugar de depender del resumen Basic heredado en DescribeImages. Habilitar el escaneo de ECR no bloquea automáticamente que las imágenes vulnerables se envíen, extraigan o desplieguen.

### Alertas y permisos de Inspector

Filtre los hallazgos Enhanced mediante source aws.inspector2, detail-type Inspector2 Finding y detail.severity/status/resources[].type. No mezcle esto con Basic ECR Image Scan y finding-severity-counts. Un campo cuyo valor numérico es cero sigue existiendo; exists:true no implica un recuento de vulnerabilidades positivo.

El [ejemplo completo de CloudFormation](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/image-security/inspector-alerts.yaml) conecta un tema SNS cifrado a un rol de ejecución de EventBridge. Requiere una clave KMS simétrica administrada por el cliente, existente y de la misma cuenta/Region, cuya política permita la delegación de IAM; las suscripciones aprobadas de consumidores de SNS son independientes. EventBridge actual admite roles de ejecución para destinos SNS. No copie las condiciones SourceArn/SourceAccount de KMS del bus de eventos en la ruta directa del principal de servicio a SNS cifrado. La plantilla pasó cfn-lint; la entrega real, la autorización KMS y los reintentos requieren pruebas en el entorno de despliegue.

<span id="cosign-overview"></span>
<span id="cosign-installation"></span>
<span id="key-based-signing"></span>
<span id="keyless-signing-oidc-based"></span>
<span id="github-actions-integration"></span>

## Firma de imágenes con Cosign/Sigstore

### Orden de firma y confianza

Para el flujo habitual de registro, envíe la imagen, obtenga su digest y firme ese digest. Verifique una clave de confianza o un emisor/identidad OIDC exactos, el digest y la evidencia requerida de transparencia/marca de tiempo. Una firma por sí sola no establece un firmante aprobado ni la ausencia de vulnerabilidades.

```bash
cosign version
cosign generate-key-pair
cosign sign --key cosign.key "$IMAGE_REF"
cosign verify --key cosign.pub "$IMAGE_REF"
```

No incluya claves privadas en commits. Administre su ciclo de vida mediante administradores de credenciales/KMS o controles equivalentes. GitHub Actions sin clave usa id-token:write y el entorno OIDC de Actions. GITHUB_TOKEN es una credencial de registro/API, no el token de ID OIDC en sí.

```bash
cosign sign --yes "$IMAGE_REF"
cosign verify   --certificate-identity 'https://github.com/example-org/example-app/.github/workflows/secure-build.yaml@refs/heads/main'   --certificate-oidc-issuer 'https://token.actions.githubusercontent.com'   "$IMAGE_REF"
```

Reemplace la identidad por el workflow aprobado. --certificate-identity-regexp acepta una expresión regular, no un glob. Prefiera una identidad exacta o una expresión regular anclada en lugar de expresiones permisivas como `https://github.com/org/repo/*`. Verifique la compatibilidad de los bundles/referrers OCI de Cosign 3 con los verificadores posteriores.

<span id="kyverno-imageverify"></span>

## Verificación de imágenes en el control de admisión

Kyverno 1.19.1 advierte que ClusterPolicy está obsoleto. Los nuevos ejemplos usan policies.kyverno.io/v1 ValidatingPolicy e ImageValidatingPolicy. La regla verifyImages heredada no es el nombre del nuevo tipo de política.

### Política de registro y digest

```yaml
apiVersion: policies.kyverno.io/v1
kind: ValidatingPolicy
metadata:
  name: approved-registry-and-digest
spec:
  failurePolicy: Fail
  validationActions: [Deny]
  evaluation:
    background:
      enabled: false
  matchConstraints:
    resourceRules:
      - apiGroups: [""]
        apiVersions: [v1]
        operations: [CREATE, UPDATE]
        resources: [pods, pods/ephemeralcontainers]
  variables:
    - name: containers
      expression: >-
        object.spec.containers +
        (has(object.spec.initContainers) ? object.spec.initContainers : []) +
        (has(object.spec.ephemeralContainers) ? object.spec.ephemeralContainers : [])
  validations:
    - expression: >-
        variables.containers.all(c,
          c.image.matches('^ghcr[.]io/example-org/[a-z0-9._/-]+@sha256:[a-f0-9]{64}$'))
      message: All container images must use the approved repository and a SHA-256 digest.
```

Esto cubre contenedores ordinarios, init y efímeros, incluidas las actualizaciones de pods/ephemeralcontainers. Reemplace example-org por repositorios aprobados. Un formato de digest fija una dirección de contenido; no realiza verificación de firma ni de vulnerabilidades.

### Política de firma de workflow

```yaml
apiVersion: policies.kyverno.io/v1
kind: ImageValidatingPolicy
metadata:
  name: verify-approved-workflow
spec:
  failurePolicy: Fail
  validationActions: [Deny]
  evaluation:
    background:
      enabled: false
  matchConstraints:
    resourceRules:
      - apiGroups: [""]
        apiVersions: [v1]
        operations: [CREATE, UPDATE]
        resources: [pods, pods/ephemeralcontainers]
  matchImageReferences:
    - glob: ghcr.io/example-org/*
  validationConfigurations:
    mutateDigest: false
    verifyDigest: true
    required: true
  images:
    - name: workloadImages
      expression: >-
        (object.spec.containers +
        (has(object.spec.initContainers) ? object.spec.initContainers : []) +
        (has(object.spec.ephemeralContainers) ? object.spec.ephemeralContainers : []))
        .map(c, c.image)
  attestors:
    - name: githubRelease
      cosign:
        keyless:
          identities:
            - issuer: https://token.actions.githubusercontent.com
              subject: https://github.com/example-org/example-app/.github/workflows/secure-build.yaml@refs/heads/main
        ctlog:
          url: https://rekor.sigstore.dev
          insecureIgnoreTlog: false
          insecureIgnoreSCT: false
  validations:
    - expression: >-
        images.workloadImages.map(image,
          verifyImageSignatures(image, [attestors.githubRelease]))
          .all(result, result > 0)
      message: Image signature must match the approved workflow and transparency proof.
```

Las imágenes fuera de matchImageReferences se pueden omitir mediante la verificación de imágenes, por lo que aplique también la política de registro. Diseñe excepciones de namespace, acceso a PolicyException, disponibilidad/tiempos de espera de webhook, credenciales de registro y confianza TLS, y luego pruebe las solicitudes de admisión reales. La política de firma se verificó con el esquema CRD; esto no es evidencia de verificación activa de registro/Fulcio/Rekor. Los ejemplos de producción no deshabilitan las verificaciones de transparencia.

<span id="connaisseur"></span>

### Alternativa Connaisseur — ruta de firma heredada

**Connaisseur 3.12.0 no consume bundles predeterminados de Cosign 3.** Usa la ruta de verificación cosign/v2 con tags de firma heredados y cargas útiles SimpleSigning. Use un productor de compatibilidad independiente. El [script de firma heredada](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/image-security/connaisseur-sign-legacy.sh) establece explícitamente Cosign 3.1.3 `--new-bundle-format=false --registry-referrers-mode=legacy` mientras mantiene la carga/verificación de transparencia. La configuración de firma complementaria selecciona explícitamente Rekor v1 para el formato de registro del verificador heredado. Proporcione claves aprobadas reales y un digest. Esta ruta es independiente del formato de bundle predeterminado de secure-build.yaml; no proporcione directamente a Connaisseur la salida predeterminada de ese workflow. Los flags heredados están obsoletos, así que planifique una migración coordinada de productor/verificador. Se verificaron las opciones de CLI y ambos contratos fuente; no se ejecutó la integración de registro/firma.

Connaisseur 3.12.0/chart 2.12.0 es otra opción. En el [ejemplo de valores](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/image-security/connaisseur-values.yaml), los validadores y la política pertenecen a application, y deny es un validador estático definido explícitamente. La clave pública incluida es una clave de prueba sintética que se debe reemplazar con la clave de confianza real.

```bash
helm repo add connaisseur https://sse-secure-systems.github.io/connaisseur/charts
helm upgrade --install connaisseur connaisseur/connaisseur   --version 2.12.0 --namespace connaisseur --create-namespace   --values connaisseur-values.yaml
kubectl label namespace production securesystemsengineering.connaisseur/webhook=validate
```

El ejemplo usa el modo validate de namespaced-validation y solo verifica los namespaces con esa etiqueta. Una identidad autorizada para cambiar etiquetas de namespace puede omitir esta selección, así que gestione esos permisos. Kyverno y Connaisseur son alternativas, no un requisito para instalar ambos. El renderizado de Helm no sustituye las pruebas reales de permitir/denegar firmas.

<span id="sbom-software-bill-of-materials-generation"></span>
<span id="sbom-based-vulnerability-scanning"></span>
<span id="slsa-supply-chain-levels-for-software-artifacts"></span>

## Seguridad de la cadena de suministro

### SBOM y atestaciones

```bash
syft "$IMAGE_REF" -o spdx-json=sbom.spdx.json
trivy image --format spdx-json --output sbom.spdx.json "$IMAGE_REF"
trivy sbom sbom.spdx.json
# Alternatively, Grype:
# grype sbom:sbom.spdx.json
cosign attest --yes --type spdxjson --predicate sbom.spdx.json "$IMAGE_REF"
cosign verify-attestation --type spdxjson   --certificate-identity 'https://github.com/example-org/example-app/.github/workflows/secure-build.yaml@refs/heads/main'   --certificate-oidc-issuer 'https://token.actions.githubusercontent.com' "$IMAGE_REF"
```

Los comandos de generación Syft/Trivy son alternativas. Un SBOM inventaría lo que detecta la herramienta; no se garantiza su integridad ni seguridad. cosign attach sbom está obsoleto y un adjunto simple difiere de una atestación firmada. Valide conjuntamente el contenido del predicado, el digest del sujeto, el firmante, el momento de verificación y la política.

### Procedencia SLSA

La procedencia registra relaciones entre las entradas de compilación, el constructor y el artefacto. Invocar una acción de generación no satisface automáticamente el nivel de compilación 3 de SLSA. Evalúe por separado los requisitos pertinentes de aislamiento, resistencia a la falsificación de procedencia y política de código fuente.

Para los workflows reutilizables existentes de slsa-github-generator, verifique la cadena de herramientas compatible y los requisitos del llamador. El nuevo workflow a continuación usa actions/attest actual. La versión 4 de attest-build-provenance es un wrapper; las nuevas implementaciones se dirigen a actions/attest. Verifique las diferencias de plan de GitHub y raíz de confianza de Sigstore para repositorios públicos frente a privados.

<span id="image-type-comparison"></span>
<span id="using-distroless-images"></span>
<span id="using-chainguard-images"></span>
<span id="alpine-security-hardening"></span>

## Selección de imagen base

| Imagen | Características | Verificación |
|---|---|---|
| Distroless | Los runtimes estándar omiten shell/administrador de paquetes | Las variantes de depuración, bibliotecas y dependencias de la aplicación difieren |
| Alpine | Distribución pequeña basada en musl | Compatibilidad con glibc, duración del mantenimiento, digest real |
| Chainguard | Variantes diferenciadas mínimas de runtime y desarrollo | No suponga que las imágenes de runtime contienen shell/pip |
| Ubuntu/Debian | Selección más amplia de paquetes/herramientas | El tamaño por sí solo no determina el recuento de vulnerabilidades |
| Scratch | Imagen base vacía | Los binarios copiados, archivos CA y dependencias de la aplicación aún pueden ser vulnerables |

No confunda los antiguos ejemplos de Go 1.22/Alpine 3.19 con bases de referencia compatibles actuales. Verifique el mantenimiento, EOL del SO, ABI de CPU, digests y hallazgos de escaneo al actualizar. Distroless recibe binarios de una etapa de compilación; siga el patrón de Python de Chainguard de preparar dependencias/venv en una etapa de desarrollo y copiarlas al runtime. Este documento no ejecutó compilaciones de Dockerfile ni comparó recuentos de vulnerabilidades.

### Ejemplos de compilación de imágenes base mínimas

El [contexto de compilación completo](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/security/image-security/base-images) contiene programas Go/Python que imprimen un mensaje fijo y tres Dockerfiles. Seleccione un Dockerfile para comparar los patrones; estos no son ejemplos de servidores web. Se verificaron los digests de índice de base y la disponibilidad amd64/arm64, pero no se ejecutaron compilaciones/runtimes de contenedores.

**Dockerfile.distroless**

```dockerfile
FROM golang:1.27.1@sha256:f44f6e88636cfb311f9ebace870ded69d943f227bb3cb27d32ffd84ea18c43ea AS builder
WORKDIR /src
COPY go.mod main.go ./
RUN CGO_ENABLED=0 go build -trimpath -o /out/app .
FROM gcr.io/distroless/static-debian13:nonroot@sha256:1c2c046bc09ed40fad370b599a0b1ae7987f55b01e247cf27a7c27cd97e5bbc7
COPY --from=builder /out/app /app
USER 65532:65532
ENTRYPOINT ["/app"]
```

**Dockerfile.chainguard**

```dockerfile
FROM cgr.dev/chainguard/python:latest-dev@sha256:b0bc807f4334fea6adaac0f4dfbde255b9938ca957facb26eaed8bb448fce473 AS builder
WORKDIR /app
COPY requirements.txt ./
RUN python -m venv /app/venv && /app/venv/bin/pip install --no-cache-dir -r requirements.txt
FROM cgr.dev/chainguard/python:latest@sha256:b5decb00aa1cb65ab71bb3f6632a44bb8e6fd8d661de1f0342fd513a06837b9a
WORKDIR /app
COPY --from=builder /app/venv /app/venv
COPY app.py /app/app.py
USER 65532:65532
ENTRYPOINT ["/app/venv/bin/python", "/app/app.py"]
```

**Dockerfile.alpine**

```dockerfile
FROM alpine:3.24.1@sha256:28bd5fe8b56d1bd048e5babf5b10710ebe0bae67db86916198a6eec434943f8b
RUN apk add --no-cache python3 && addgroup -g 10001 app && adduser -D -u 10001 -G app app
WORKDIR /app
COPY --chown=10001:10001 app.py /app/app.py
USER 10001:10001
ENTRYPOINT ["python3", "/app/app.py"]
```

Las aplicaciones se ejecutaron directamente con Go 1.27.1 y Python 3.12, y los tres Dockerfiles superaron las verificaciones de configuración HIGH/CRITICAL. Los requisitos de Python están vacíos en este fixture. Añadir dependencias reales requiere locks/hashes, verificaciones ABI de compilador/runtime y escaneo de vulnerabilidades. Administre por separado los repositorios apk de Alpine y las actualizaciones del digest base.

<span id="using-private-registries"></span>
<span id="image-pull-policies"></span>
<span id="immutable-tag-policy-kyverno"></span>

## Prácticas recomendadas para el registro de imágenes

- Las imágenes privadas necesitan identidades de extracción aprobadas. Los roles de ejecución de ECR kubelet/node/Fargate difieren de Pod Identity de la aplicación.
- Los registros externos pueden usar un Secret kubernetes.io/dockerconfigjson válido y ServiceAccount imagePullSecrets. Base64 no es cifrado.
- imagePullPolicy:Always controla la comprobación de referencias del registro, no la verificación de firmas. Configure por separado la fijación de digest, la verificación de admisión y los controles de escaneo.
- Un patrón que prohíbe solo latest puede omitir tags y las imágenes init/efímeras sin especificar. Pruebe el alcance con la política de registro/digest anterior.
- La extracción anónima de imágenes deliberadamente públicas no es inherentemente una vulnerabilidad. Separe los requisitos de confidencialidad, permisos de envío, procedencia, límites de tasa y licencias.
- Asegúrese de que la retención/recolección de basura no elimine digests activos ni referrers de firma/atestación necesarios; pruebe la recuperación.

<span id="complete-image-security-pipeline"></span>

## Integración de la canalización de CI/CD

Revise el [archivo de workflow completo](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/image-security/secure-build.yaml) antes de colocarlo en .github/workflows/secure-build.yaml en el repositorio de la aplicación. Un Dockerfile y un contexto de compilación reales son requisitos previos. Sus propiedades previstas son:

1. El escaneo de PR usa un job de solo lectura sin publicación en el registro/firma OIDC.
2. El job de lanzamiento al enviar a main compila una vez y escanea esa imagen local.
3. Envía sin recompilar y captura el RepoDigest.
4. La firma, verificación, atestación SBOM y procedencia usan ese mismo digest.
5. Las Actions se fijan a SHA de commits revisados; se deshabilitan los registros independientes de almacenamiento de artefactos.

```yaml
name: Secure Image Build
on:
  pull_request:
    branches: [main]
  push:
    branches: [main]
permissions:
  contents: read
jobs:
  pull-request-scan:
    if: github.event_name == 'pull_request'
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false
      - uses: docker/setup-buildx-action@37fe631027851001ddb9b187196cc803df7f5f0e # v4.3.0
      - uses: docker/build-push-action@53b7df96c91f9c12dcc8a07bcb9ccacbed38856a # v7.3.0
        with:
          context: .
          load: true
          tags: local/audit-app:${{ github.sha }}
      - uses: aquasecurity/trivy-action@ed142fd0673e97e23eac54620cfb913e5ce36c25 # v0.36.0
        with:
          version: v0.74.0
          scan-type: image
          image-ref: local/audit-app:${{ github.sha }}
          scanners: vuln,secret
          severity: HIGH,CRITICAL
          exit-code: '1'
          ignore-unfixed: 'false'
  release:
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    runs-on: ubuntu-24.04
    permissions:
      contents: read
      packages: write
      id-token: write
      attestations: write
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false
      - name: Normalize the registry image name
        id: image
        shell: bash
        run: |
          set -euo pipefail
          repository="ghcr.io/${GITHUB_REPOSITORY,,}"
          printf 'repository=%s\ntag=%s:%s\n' "$repository" "$repository" "$GITHUB_SHA" >> "$GITHUB_OUTPUT"
      - uses: docker/setup-buildx-action@37fe631027851001ddb9b187196cc803df7f5f0e # v4.3.0
      - name: Build once into the local image store
        uses: docker/build-push-action@53b7df96c91f9c12dcc8a07bcb9ccacbed38856a # v7.3.0
        with:
          context: .
          load: true
          tags: ${{ steps.image.outputs.tag }}
      - name: Scan the exact local artifact that will be pushed
        uses: aquasecurity/trivy-action@ed142fd0673e97e23eac54620cfb913e5ce36c25 # v0.36.0
        with:
          version: v0.74.0
          scan-type: image
          image-ref: ${{ steps.image.outputs.tag }}
          scanners: vuln,secret
          severity: HIGH,CRITICAL
          exit-code: '1'
          ignore-unfixed: 'false'
      - uses: docker/login-action@dbcb813823bdd20940b903addbd779551569679f # v4.6.0
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - name: Push without rebuilding and capture the registry digest
        id: published
        env:
          IMAGE_TAG: ${{ steps.image.outputs.tag }}
          IMAGE_REPOSITORY: ${{ steps.image.outputs.repository }}
        shell: bash
        run: |
          set -euo pipefail
          docker push "$IMAGE_TAG"
          ref=$(docker image inspect "$IMAGE_TAG" --format '{{index .RepoDigests 0}}')
          digest="${ref##*@}"
          [[ "$ref" == "$IMAGE_REPOSITORY"@* ]]
          [[ "$digest" =~ ^sha256:[a-f0-9]{64}$ ]]
          printf 'ref=%s\ndigest=%s\n' "$ref" "$digest" >> "$GITHUB_OUTPUT"
      - uses: sigstore/cosign-installer@6f9f17788090df1f26f669e9d70d6ae9567deba6 # v4.1.2
        with:
          cosign-release: v3.1.3
      - name: Sign and verify the immutable image
        env:
          IMAGE_REF: ${{ steps.published.outputs.ref }}
        shell: bash
        run: |
          set -euo pipefail
          cosign sign --yes "$IMAGE_REF"
          cosign verify --certificate-identity "${GITHUB_SERVER_URL}/${GITHUB_WORKFLOW_REF}"             --certificate-oidc-issuer https://token.actions.githubusercontent.com "$IMAGE_REF"
      - name: Generate SBOM for the pushed digest
        uses: anchore/sbom-action@3ad7283483fc7af8ff2b4ea19663c2d5ca935e26 # v0.24.2
        with:
          image: ${{ steps.published.outputs.ref }}
          syft-version: v1.51.1
          format: spdx-json
          output-file: sbom.spdx.json
          upload-artifact: false
      - name: Sign the SBOM as an attestation
        env:
          IMAGE_REF: ${{ steps.published.outputs.ref }}
        shell: bash
        run: |
          set -euo pipefail
          cosign attest --yes --type spdxjson --predicate sbom.spdx.json "$IMAGE_REF"
          cosign verify-attestation --type spdxjson             --certificate-identity "${GITHUB_SERVER_URL}/${GITHUB_WORKFLOW_REF}"             --certificate-oidc-issuer https://token.actions.githubusercontent.com "$IMAGE_REF"
      - name: Publish build provenance
        uses: actions/attest@1e69f48acb82d1966a394da916b4c1698aa569d6 # v4.2.2
        with:
          subject-name: ${{ steps.image.outputs.repository }}
          subject-digest: ${{ steps.published.outputs.digest }}
          push-to-registry: true
          create-storage-record: false
```

Configure los permisos de paquete de GHCR, OIDC de Actions, soporte del plan de atestaciones y acceso de red. Se verificaron las entradas YAML/action del workflow y la sintaxis de shell, pero no se ejecutó ningún workflow de compilación/envío/firma/atestación en GitHub runner. No ignore los errores de SBOM/firma ni continúe con digests vacíos. Si añade cargas de SARIF, gestione por separado los permisos security-events de PR de forks y la conservación de resultados tras un fallo de escaneo.

## Verificaciones realizadas y límites

- Trivy 0.74: dos casos de secretos sintéticos y dos verificaciones de Dockerfile sin root. No hubo una base de datos CVE real ni escaneo de imágenes remotas.
- Cosign 3.1.3: verificación de clave/blob local sintética válida/manipulada. Omitir la transparencia en ese fixture privado no es evidencia de verificación de registro/OIDC de producción.
- Kyverno 1.19.1: seis casos de objetos CEL de registro/digest, incluidos contenedores init/efímeros, más dos esquemas CRD fijados. Sin admisión activa ni verificación de firma en red.
- Se ejecutaron el renderizado Helm de Trivy Operator/Connaisseur, fixtures sintéticos de modelo de API ECR/JMESPath, lint de CloudFormation y actionlint. No se ejecutaron recursos de AWS, notificaciones ni envíos al registro.

<span id="summary"></span>
<span id="recommendations"></span>

## Referencias

- [Lanzamientos de Trivy](https://github.com/aquasecurity/trivy/releases/tag/v0.74.0)
- [Documentación de Trivy](https://aquasecurity.github.io/trivy/)
- [Chart de Trivy Operator](https://github.com/aquasecurity/trivy-operator/tree/v0.34.0/deploy/helm)
- [Escaneo de ECR](https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-scanning.html)
- [Esquemas de eventos de Inspector](https://docs.aws.amazon.com/inspector/latest/user/eventbridge-integration.html)
- [Autorización de destino de EventBridge](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-use-resource-based.html)
- [Compatibilidad de KMS con SNS](https://docs.aws.amazon.com/sns/latest/dg/sns-key-management.html)
- [Cosign 3.1.3](https://github.com/sigstore/cosign/releases/tag/v3.1.3)
- [Verificación de Sigstore](https://docs.sigstore.dev/cosign/verifying/verify/)
- [Migración CEL de Kyverno](https://kyverno.io/docs/guides/migration-to-cel/)
- [Kyverno ImageValidatingPolicy](https://kyverno.io/docs/policy-types/image-validating-policy/)
- [Validación por namespace de Connaisseur](https://github.com/sse-secure-systems/connaisseur/blob/v3.12.0/docs/features/namespaced_validation.md)
- [Requisitos de SLSA](https://slsa.dev/spec/v1.2/build-requirements)
- [Acción attest de GitHub](https://github.com/actions/attest/tree/v4.2.2)
- [Distroless](https://github.com/GoogleContainerTools/distroless)
- [Chainguard Python](https://images.chainguard.dev/directory/image/python/overview)
