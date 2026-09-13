# Seguridad de imágenes de contenedores

> **Última actualización**: September 13, 2026
> **Versiones de referencia para la validación**: Trivy 0.74.0, Trivy Operator 0.34.0/chart 0.36.0, Cosign 3.1.3, Kyverno 1.19.1, Connaisseur 3.12.0/chart 2.12.0. Son referencias de CLI/configuración, no una afirmación de que se hayan probado los despliegues en todas las versiones de Kubernetes.

La seguridad de las imágenes comienza por confirmar que **el artefacto compilado, analizado y desplegado es el mismo**. El análisis identifica vulnerabilidades conocidas y problemas de configuración; las firmas vinculan un firmante con un digest. Ninguno de los dos garantiza la seguridad de la aplicación.

## Índice

1. [Descripción general del análisis de imágenes](#image-scanning-overview)
2. [Trivy](#trivy)
3. [Análisis de imágenes en Amazon ECR](#amazon-ecr-image-scanning)
4. [Firma de imágenes con Cosign/Sigstore](#image-signing-with-cosignsigstore)
5. [Verificación de imágenes en el control de admisión](#image-verification-in-admission-control)
6. [Seguridad de la cadena de suministro](#supply-chain-security)
7. [Selección de la imagen base](#base-image-selection)
8. [Buenas prácticas para registros de imágenes](#image-registry-best-practices)
9. [Integración en la canalización de CI/CD](#cicd-pipeline-integration)

<span id="shift-left-security"></span>
<span id="scan-targets"></span>

## Descripción general del análisis de imágenes {#image-scanning-overview}

El enfoque shift-left introduce comprobaciones en el IDE, las PR y la compilación. Después de publicar aparecen nuevas CVE, por lo que los nuevos análisis del registro y la detección en tiempo de ejecución siguen siendo requisitos independientes.

| Objetivo | Comprobación | Herramientas de ejemplo |
|---|---|---|
| Paquetes del sistema operativo y de lenguajes | Identificación, antigüedad de la base de datos, versiones corregidas, decisiones VEX | Trivy, Grype |
| IaC/Dockerfiles | Ejecución sin root, permisos, configuración | Trivy misconfig, Checkov |
| Secretos | Credenciales en capas de imagen o código fuente | Trivy secret, TruffleHog |
| Licencias/SBOM | Cobertura de detección de componentes y licencias | Syft, Trivy |
| Comportamiento en ejecución | Llamadas al sistema, procesos y red en vivo | Herramientas independientes como Falco |

El flujo es `source checks → build once → scan that artifact → push → sign/verify digest → admission checks → rescan`. Las organizaciones definen controles de severidad y asignan a cada excepción un responsable, una justificación y una fecha de caducidad.

<span id="trivy-installation"></span>
<span id="image-scanning"></span>
<span id="filesystem-scanning"></span>
<span id="trivy-configuration-file"></span>
<span id="trivy-operator-kubernetes-integration"></span>

## Trivy {#trivy}

### Instalación y análisis

Verifique el paquete oficial de la versión correspondiente al sistema operativo y la arquitectura de CPU, y su suma de comprobación. No instale un binario amd64 en Linux ARM64 ni utilice instrucciones retiradas de apt-key. Fije las versiones de CLI/actions en la automatización.

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

`IMAGE_REF` es un marcador intencionado que requiere un digest real. Utilice `misconfig`, no `--scanners config`. `--ignore-unfixed` oculta vulnerabilidades sin corrección disponible, por lo que no debe habilitarse indiscriminadamente en el control predeterminado. Compruebe los requisitos de red y caché para los registros, las bases de datos de vulnerabilidades/Java y los paquetes de comprobaciones. `trivy config` no tiene la opción `--offline-scan`.

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

Esta es una configuración de referencia para analizar imágenes y sistemas de archivos. No añada vulnerability.type ni una lista de exclusión de nivel superior, ya que no se admiten. Gestione las excepciones mediante .trivyignore o formatos compatibles de políticas de exclusión, distinguiendo las excepciones de secretos de las de vulnerabilidades. El .trivyignore de ejemplo no incluye exclusiones predeterminadas.

<span id="trivy-overview"></span>

### Trivy Operator

```bash
helm repo add aqua https://aquasecurity.github.io/helm-charts/
helm repo update aqua
helm upgrade --install trivy-operator aqua/trivy-operator   --version 0.36.0 --namespace trivy-system --create-namespace   --values trivy-operator-values.yaml
kubectl get vulnerabilityreports -A
```

El chart 0.36.0 despliega la aplicación 0.34.0. El [archivo de valores](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/image-security/trivy-operator-values.yaml) establece explícitamente ignoreUnfixed:false. Los informes son resultados generados por el operador; no aplique un manifiesto inventado de CVE/versiones de paquetes como prueba de análisis. Compruebe el esquema real del informe, los namespaces vigilados, las credenciales del registro, los privilegios de los Jobs de análisis y sus recursos. Esta auditoría solo generó los manifiestos del chart.

<span id="basic-scanning-vs-enhanced-scanning"></span>
<span id="enabling-enhanced-scanning"></span>
<span id="retrieving-scan-results"></span>
<span id="notifications-via-eventbridge"></span>

## Análisis de imágenes en Amazon ECR {#amazon-ecr-image-scanning}

| Propiedad | Basic | Enhanced |
|---|---|---|
| Motor actual | Analizador nativo de AWS | Amazon Inspector |
| Cobertura | Vulnerabilidades de paquetes del sistema operativo | Paquetes del sistema operativo y de lenguajes compatibles |
| Frecuencia | Manual o al cargar imágenes | Al cargar imágenes o continua |
| Resultados | imageScanFindings.findings | imageScanFindings.enhancedFindings |
| Eventos | Finalización del análisis básico de ECR | Eventos de análisis/hallazgos de Inspector2 |

Distinga las antiguas descripciones de Clair del motor Basic actual. Cambiar de modo de análisis puede modificar la visibilidad de resultados existentes. La cobertura de Enhanced depende de los filtros de repositorios, el periodo de nuevos análisis y los criterios de imágenes compatibles; no todas las imágenes se analizan indefinidamente. Las imágenes archivadas deben restaurarse antes de analizarlas.

```bash
aws ecr put-registry-scanning-configuration --scan-type ENHANCED --rules '[
  {"repositoryFilters":[{"filter":"production/*","filterType":"WILDCARD"}],"scanFrequency":"CONTINUOUS_SCAN"},
  {"repositoryFilters":[{"filter":"development/*","filterType":"WILDCARD"}],"scanFrequency":"SCAN_ON_PUSH"}
]'
# Enhanced results. For Basic, query findings instead of enhancedFindings.
aws ecr describe-image-scan-findings --repository-name production/my-app   --image-id imageDigest=sha256:REPLACE_WITH_64_HEX_DIGEST   --query 'imageScanFindings.enhancedFindings[?severity==`CRITICAL`]'
```

El comando de configuración escribe opciones del registro y no se ejecutó durante esta auditoría. Utilice DescribeImageScanFindings en lugar de depender del resumen Basic heredado de DescribeImages. Habilitar el análisis de ECR no bloquea automáticamente la carga, descarga ni despliegue de imágenes vulnerables.

### Alertas de Inspector y permisos

Filtre los hallazgos de Enhanced mediante source aws.inspector2, detail-type Inspector2 Finding y detail.severity/status/resources[].type. No lo mezcle con ECR Image Scan de Basic ni con finding-severity-counts. Un campo cuyo valor numérico es cero sigue existiendo; exists:true no significa que la cantidad de vulnerabilidades sea positiva.

El [ejemplo completo de CloudFormation](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/image-security/inspector-alerts.yaml) conecta un tema SNS cifrado a un rol de ejecución de EventBridge. Requiere una clave KMS simétrica existente, administrada por el cliente y de la misma cuenta y región, cuya política permita la delegación mediante IAM; las suscripciones aprobadas de consumidores SNS se gestionan por separado. EventBridge admite actualmente roles de ejecución para destinos SNS. No copie las condiciones KMS SourceArn/SourceAccount del bus de eventos a la ruta directa entre el principal de servicio y SNS cifrado. La plantilla superó cfn-lint; la entrega real, la autorización KMS y los reintentos requieren pruebas en el entorno de despliegue.

<span id="cosign-overview"></span>
<span id="cosign-installation"></span>
<span id="key-based-signing"></span>
<span id="keyless-signing-oidc-based"></span>
<span id="github-actions-integration"></span>



## Firma de imágenes con Cosign/Sigstore {#image-signing-with-cosignsigstore}

### Orden de firma y confianza

En el flujo habitual con un registro, cargue la imagen, obtenga su digest y firme ese digest. Verifique una clave confiable o el emisor y la identidad OIDC exactos, el digest y las pruebas de transparencia y sellado de tiempo exigidas. Una firma por sí sola no demuestra que el firmante esté aprobado ni que no existan vulnerabilidades.

```bash
cosign version
cosign generate-key-pair
cosign sign --key cosign.key "$IMAGE_REF"
cosign verify --key cosign.pub "$IMAGE_REF"
```

No incluya claves privadas en commits. Gestione su ciclo de vida mediante gestores de credenciales/KMS o controles equivalentes. La firma sin claves en GitHub Actions utiliza id-token:write y el entorno OIDC de Actions. GITHUB_TOKEN es una credencial de registro/API, no el propio token de identidad OIDC.

```bash
cosign sign --yes "$IMAGE_REF"
cosign verify   --certificate-identity 'https://github.com/example-org/example-app/.github/workflows/secure-build.yaml@refs/heads/main'   --certificate-oidc-issuer 'https://token.actions.githubusercontent.com'   "$IMAGE_REF"
```

Sustituya la identidad por el workflow aprobado. --certificate-identity-regexp acepta una expresión regular, no un patrón glob. Prefiera una identidad exacta o una expresión regular anclada a expresiones permisivas como `https://github.com/org/repo/*`. Compruebe la compatibilidad de los bundles y los OCI referrers de Cosign 3 con los verificadores que los consumen.

<span id="kyverno-imageverify"></span>

## Verificación de imágenes en el control de admisión {#image-verification-in-admission-control}

Kyverno 1.19.1 advierte de que ClusterPolicy está obsoleta. Los nuevos ejemplos utilizan ValidatingPolicy e ImageValidatingPolicy de policies.kyverno.io/v1. La regla heredada verifyImages no es el nombre del nuevo tipo de política.

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

Esto abarca contenedores ordinarios, init y efímeros, incluidas las actualizaciones de pods/ephemeralcontainers. Sustituya example-org por los repositorios aprobados. El formato de digest fija una dirección de contenido; no verifica firmas ni vulnerabilidades.

### Política de firma del workflow

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

La verificación de imágenes puede omitir las imágenes que no coincidan con matchImageReferences, por lo que también debe aplicar la política de registro. Diseñe las excepciones de namespaces, el acceso a PolicyException, la disponibilidad y los tiempos de espera del webhook, las credenciales del registro y la confianza TLS; después pruebe solicitudes reales de admisión. La política de firma se comprobó con el esquema de la CRD; esto no demuestra una verificación real contra el registro/Fulcio/Rekor. Los ejemplos de producción no deshabilitan las comprobaciones de transparencia.

<span id="connaisseur"></span>

### Alternativa Connaisseur: ruta de firmas heredadas

**Connaisseur 3.12.0 no consume los bundles predeterminados de Cosign 3.** Utiliza la ruta de verificación de cosign/v2 con etiquetas de firma heredadas y cargas SimpleSigning. Utilice un productor de compatibilidad independiente. El [script de firma heredada](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/image-security/connaisseur-sign-legacy.sh) establece explícitamente `--new-bundle-format=false --registry-referrers-mode=legacy` de Cosign 3.1.3, manteniendo la carga y verificación de transparencia. La configuración de firma adjunta selecciona explícitamente Rekor v1 para el formato de registro del verificador heredado. Proporcione claves reales aprobadas y un digest. Esta ruta es independiente del formato de bundle predeterminado de secure-build.yaml; no entregue directamente la salida predeterminada de ese workflow a Connaisseur. Los flags heredados están obsoletos, por lo que debe planificarse una migración coordinada del productor y el verificador. Se comprobaron las opciones de CLI y los contratos de ambos códigos fuente; no se ejecutó la integración del registro y las firmas.

Connaisseur 3.12.0/chart 2.12.0 es otra opción. En el [ejemplo de valores](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/image-security/connaisseur-values.yaml), validators y policy pertenecen a application, y deny es un validador estático definido explícitamente. La clave pública incluida es una clave sintética de prueba que debe sustituirse por la clave real de confianza.

```bash
helm repo add connaisseur https://sse-secure-systems.github.io/connaisseur/charts
helm upgrade --install connaisseur connaisseur/connaisseur   --version 2.12.0 --namespace connaisseur --create-namespace   --values connaisseur-values.yaml
kubectl label namespace production securesystemsengineering.connaisseur/webhook=validate
```

El ejemplo utiliza namespaced-validation en modo validate y solo comprueba namespaces con esa etiqueta. Una identidad autorizada a cambiar etiquetas de namespaces puede eludir esta selección, por lo que esos permisos deben controlarse. Kyverno y Connaisseur son alternativas; no es obligatorio instalar ambos. La generación de manifiestos con Helm no sustituye las pruebas reales de aceptación y rechazo de firmas.

<span id="sbom-software-bill-of-materials-generation"></span>
<span id="sbom-based-vulnerability-scanning"></span>
<span id="slsa-supply-chain-levels-for-software-artifacts"></span>

## Seguridad de la cadena de suministro {#supply-chain-security}

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

Los comandos de generación de Syft/Trivy son alternativas. Una SBOM registra los componentes que detecta la herramienta; no se garantizan su integridad ni la seguridad. cosign attach sbom está obsoleto, y un adjunto simple difiere de una atestación firmada. Valide conjuntamente el contenido del predicado, el digest del sujeto, el firmante, el momento de verificación y la política.

### Procedencia SLSA

La procedencia registra las relaciones entre las entradas de compilación, el constructor y el artefacto. Invocar una acción de generación no satisface automáticamente SLSA Build Level 3. Evalúe por separado los requisitos pertinentes de aislamiento, resistencia a la falsificación de procedencia y políticas de código fuente.

Para los workflows reutilizables existentes de slsa-github-generator, compruebe la cadena de herramientas compatible y los requisitos del invocador. El nuevo workflow siguiente utiliza la acción actual actions/attest. La versión 4 de attest-build-provenance es una envoltura; las nuevas implementaciones se orientan a actions/attest. Compruebe las diferencias de planes de GitHub y raíces de confianza de Sigstore entre repositorios públicos y privados.

<span id="image-type-comparison"></span>
<span id="using-distroless-images"></span>
<span id="using-chainguard-images"></span>
<span id="alpine-security-hardening"></span>

## Selección de la imagen base {#base-image-selection}

| Imagen | Características | Comprobación |
|---|---|---|
| Distroless | Las imágenes estándar de ejecución omiten el shell y el gestor de paquetes | Las variantes de depuración, bibliotecas y dependencias de la aplicación difieren |
| Alpine | Distribución pequeña basada en musl | Compatibilidad con glibc, periodo de mantenimiento, digest real |
| Chainguard | Variantes mínimas de ejecución y de desarrollo diferenciadas | No dé por supuesto que las imágenes de ejecución contienen shell/pip |
| Ubuntu/Debian | Selección más amplia de paquetes y herramientas | El tamaño por sí solo no determina la cantidad de vulnerabilidades |
| Scratch | Imagen base vacía | Los binarios copiados, los archivos de CA y las dependencias de la aplicación aún pueden ser vulnerables |

No confunda los antiguos ejemplos de Go 1.22/Alpine 3.19 con versiones de referencia actualmente soportadas. Al actualizar, compruebe el mantenimiento, el fin de vida del sistema operativo, la ABI de CPU, los digests y los hallazgos de análisis. Distroless recibe binarios de una etapa de compilación; siga el patrón de Chainguard Python que prepara dependencias/venv en una etapa de desarrollo y los copia a la etapa de ejecución. En este documento no se ejecutaron compilaciones de Dockerfiles ni se compararon cantidades de vulnerabilidades.

### Ejemplos de compilación con imágenes base mínimas

El [contexto de compilación completo](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/security/image-security/base-images) contiene programas Go/Python que imprimen un mensaje fijo y tres Dockerfiles. Seleccione un Dockerfile para comparar los patrones; no son ejemplos de servidores web. Se comprobaron los digests de los índices de imágenes base y la disponibilidad de amd64/arm64, pero no se compilaron ni ejecutaron los contenedores.

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

Las aplicaciones se ejecutaron directamente con Go 1.27.1 y Python 3.12, y los tres Dockerfiles superaron las comprobaciones de configuración HIGH/CRITICAL. En este conjunto de prueba, los requisitos de Python están vacíos. Añadir dependencias reales requiere archivos de bloqueo y hashes, comprobaciones de ABI entre compilación y ejecución, y análisis de vulnerabilidades. Gestione por separado los repositorios apk de Alpine y las actualizaciones de digests de las imágenes base.

<span id="using-private-registries"></span>
<span id="image-pull-policies"></span>
<span id="immutable-tag-policy-kyverno"></span>

## Buenas prácticas para registros de imágenes {#image-registry-best-practices}

- Las imágenes privadas necesitan identidades aprobadas para descargarlas. Los roles de ejecución de ECR para kubelet/nodos/Fargate difieren de la Pod Identity de la aplicación.
- Los registros externos pueden utilizar un Secret kubernetes.io/dockerconfigjson válido y imagePullSecrets de ServiceAccount. Base64 no es cifrado.
- imagePullPolicy:Always controla la comprobación de referencias del registro, no la verificación de firmas. Configure por separado la fijación de digests, la verificación de admisión y los controles de análisis.
- Un patrón que solo prohíba latest puede no detectar etiquetas omitidas ni imágenes init/efímeras. Pruebe la cobertura con la política de registro/digest anterior.
- La descarga anónima de imágenes publicadas intencionadamente no es una vulnerabilidad por sí misma. Separe los requisitos de confidencialidad, permisos de carga, procedencia, límites de frecuencia y licencias.
- Asegúrese de que la retención y la recolección de elementos no utilizados no eliminen digests activos ni referrers necesarios de firmas o atestaciones; pruebe la recuperación.

<span id="complete-image-security-pipeline"></span>



## Integración en la canalización de CI/CD {#cicd-pipeline-integration}

Revise el [archivo completo del workflow](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/image-security/secure-build.yaml) antes de colocarlo en .github/workflows/secure-build.yaml del repositorio de la aplicación. Se requieren un Dockerfile real y un contexto de compilación. Sus propiedades previstas son:

1. El análisis de PR utiliza un job de solo lectura sin publicación en el registro ni firma OIDC.
2. El job de publicación activado por un push a main compila una vez y analiza esa imagen local.
3. Carga la imagen sin recompilar y captura el RepoDigest.
4. La firma, la verificación, la atestación SBOM y la procedencia utilizan ese mismo digest.
5. Las actions están fijadas a SHA de commits revisados; se deshabilitan los registros separados de almacenamiento de artefactos.

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

Configure los permisos de paquetes de GHCR, OIDC de Actions, el soporte de atestaciones del plan y el acceso de red. Se comprobaron el YAML del workflow, las entradas de las actions y la sintaxis de shell, pero no se ejecutó ningún workflow de compilación, carga, firma y atestación en un runner de GitHub. No ignore los fallos de SBOM/firmas ni propague digests vacíos. Si añade cargas SARIF, gestione por separado los permisos security-events de PR procedentes de forks y la conservación de resultados tras un fallo de análisis.

## Comprobaciones realizadas y límites

- Trivy 0.74: dos casos sintéticos de secretos y dos comprobaciones de ejecución sin root en Dockerfiles. No se utilizó una base de datos real de CVE ni se analizaron imágenes remotas.
- Cosign 3.1.3: verificación local sintética con clave y blob válidos o alterados. Omitir la transparencia en ese conjunto privado de prueba no constituye evidencia de verificación del registro/OIDC en producción.
- Kyverno 1.19.1: seis casos de objetos CEL de registro/digest que incluyen contenedores init/efímeros, además de dos esquemas CRD fijados a versiones concretas. No se realizaron admisiones reales ni verificación de firmas por red.
- Se ejecutaron la generación de manifiestos Helm de Trivy Operator/Connaisseur, pruebas sintéticas de modelos de API de ECR/JMESPath, lint de CloudFormation y actionlint. No se actuó sobre recursos AWS, no se enviaron notificaciones ni se cargaron imágenes en registros.

<span id="summary"></span>
<span id="recommendations"></span>

## Referencias

- [Versiones de Trivy](https://github.com/aquasecurity/trivy/releases/tag/v0.74.0)
- [Documentación de Trivy](https://aquasecurity.github.io/trivy/)
- [Chart de Trivy Operator](https://github.com/aquasecurity/trivy-operator/tree/v0.34.0/deploy/helm)
- [Análisis de ECR](https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-scanning.html)
- [Esquemas de eventos de Inspector](https://docs.aws.amazon.com/inspector/latest/user/eventbridge-integration.html)
- [Autorización de destinos de EventBridge](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-use-resource-based.html)
- [Compatibilidad KMS de SNS](https://docs.aws.amazon.com/sns/latest/dg/sns-key-management.html)
- [Cosign 3.1.3](https://github.com/sigstore/cosign/releases/tag/v3.1.3)
- [Verificación de Sigstore](https://docs.sigstore.dev/cosign/verifying/verify/)
- [Migración de Kyverno a CEL](https://kyverno.io/docs/guides/migration-to-cel/)
- [ImageValidatingPolicy de Kyverno](https://kyverno.io/docs/policy-types/image-validating-policy/)
- [Validación por namespace de Connaisseur](https://github.com/sse-secure-systems/connaisseur/blob/v3.12.0/docs/features/namespaced_validation.md)
- [Requisitos SLSA](https://slsa.dev/spec/v1.2/build-requirements)
- [Acción attest de GitHub](https://github.com/actions/attest/tree/v4.2.2)
- [Distroless](https://github.com/GoogleContainerTools/distroless)
- [Chainguard Python](https://images.chainguard.dev/directory/image/python/overview)
