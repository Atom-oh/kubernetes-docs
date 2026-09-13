# Gestión de la postura de seguridad con Kubescape

> **Última actualización**: September 13, 2026
> **Base de validación**: CLI 4.0.14 y Operator chart 1.40.4. La imagen del escáner del chart es 4.0.13, independiente de la CLI. Los hashes de las políticas se registran en el directorio de ejemplos.

Kubescape evalúa la configuración de Kubernetes y datos seleccionados de imágenes/runtime. **Superar un análisis no es una garantía de seguridad ni una certificación de cumplimiento; la cobertura no disponible debe identificarse por separado.** Esta guía se comprobó con YAML local, paquetes de políticas, la CLI real y el renderizado del chart. No se realizó ningún análisis de clúster activo, instalación de node-agent, análisis de imagen/DB de registro ni envío a SaaS.

<span id="what-kubescape-solves"></span>
<span id="cncf-sandbox-project"></span>
<span id="comparison-with-similar-tools"></span>
<span id="kubescape-architecture"></span>

## Descripción general

Kubescape se unió a CNCF el 13 de diciembre de 2022 y pasó a **Incubating el 13 de enero de 2025**. La anterior descripción de Sandbox y la tabla desactualizada de comparación de madurez de herramientas no constituyen una guía actual.

La CLI realiza análisis explícitos de archivos o clústeres; el Operator proporciona un comportamiento continuo/programado según las capacidades habilitadas. Los controles de configuración, el análisis de RBAC, las CVE de imágenes y la detección en runtime tienen alcances diferentes. Compare las comprobaciones de node/CIS de kube-bench, las políticas de workloads de Polaris y los análisis de imagen/configuración de Trivy con requisitos versionados, en lugar de hacer afirmaciones amplias de superioridad.

![Entradas de Kubescape, controles, resultados separados y salidas opcionales](../.gitbook/assets/en-security-11-kubescape-0.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-security-11-kubescape-0.html)


<span id="linux-and-macos"></span>
<span id="windows"></span>
<span id="container-image"></span>
<span id="helm-operator-installation-in-cluster"></span>
<span id="operator-configuration-values"></span>
<span id="kubescape-cloud-saas"></span>

## Instalación

### Instalación de la CLI

Descargue el recurso correspondiente al OS/CPU desde la [versión oficial 4.0.14](https://github.com/kubescape/kubescape/releases/tag/v4.0.14) y verifique su checksum. Este ejemplo para Linux AMD64 fija el hash del archivo revisado; ARM64 necesita un archivo/hash diferente.

```bash
curl --fail --location \
  https://github.com/kubescape/kubescape/releases/download/v4.0.14/kubescape_4.0.14_linux_amd64.tar.gz \
  --output kubescape.tgz
printf '%s  %s\n' '1d253b70f88e80b74f68af73ccd422f897381468300be7cc486fdd656d907a40' kubescape.tgz | sha256sum --check
tar -xzf kubescape.tgz kubescape
./kubescape version
./kubescape scan --help
```

Compruebe la versión real del paquete al usar Homebrew/Krew u otros instaladores. Limite la ejecución del instalador y la exposición de kubeconfig al alcance previsto. Omitir un destino de archivo de `kubescape scan` puede analizar el clúster actual.

### Instalación del Helm Operator

Descargue el [directorio de ejemplos](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/security/kubescape) y ejecute estos comandos desde `examples/security/kubescape`. El perfil se centra en comprobaciones de postura y métricas, deshabilitando explícitamente las capacidades de node/image/runtime/remediation.

```bash
helm repo add kubescape https://kubescape.github.io/helm-charts
helm repo update kubescape
helm upgrade --install kubescape kubescape/kubescape-operator \
  --version 1.40.4 --namespace kubescape --create-namespace \
  --values operator-values.yaml
```

```yaml
clusterName: documentation-cluster
defaultFrameworks:
- nsa
- mitre
capabilities:
  continuousScan: enable
  configurationScan: enable
  nodeScan: disable
  nodeSbomGeneration: disable
  vulnerabilityScan: disable
  relevancy: disable
  runtimeObservability: disable
  networkPolicyService: disable
  networkEventsStreaming: disable
  runtimeDetection: disable
  nodeProfileService: disable
  admissionController: disable
  httpDetection: disable
  seccompProfileService: disable
  prometheusExporter: enable
  riskAcceptance: disable
  remediation: disable
  manageWorkloads: disable
global:
  enableClusterWideSecretAccess: false
persistence:
  storageClass: gp3
kubescapeScheduler:
  scanSchedule: 0 8 * * *
```


Prepare el StorageClass/controlador CSI gp3 y verifique los namespaces, RBAC, CRD y la disponibilidad de la API agregada. EKS Auto Mode y los StorageClasses ordinarios de EBS CSI pueden usar provisioners diferentes. El renderizado de Helm no establece la instalación, la persistencia ni el éxito del análisis.

credentials.cloudSecret es un nombre de Secret existente, no un ID de cuenta. Configure y autorice explícitamente el alcance de backend/account/accessKey/data cuando se necesite SaaS. La solicitud de la CLI --submit realiza un envío; los ejemplos locales usan --keep-local y una caché aislada. Habilite las características de node/runtime por separado después de comprobar los privilegios del host, los kernels/BTF y los tipos de node compatibles.

<span id="nsa-cisa-kubernetes-hardening-guide"></span>
<span id="cis-kubernetes-benchmark"></span>
<span id="mitre-att-ck-framework"></span>
<span id="framework-comparison"></span>

## Frameworks de seguridad

### Frameworks y controles

Los nombres de los frameworks y el número de controles dependen del paquete de políticas. La descarga revisada contenía los frameworks NSA, MITRE, SOC2, ArmoBest, DevOpsBest, AllControls y CIS versionados. NSA contenía 26 controles, no todos aplicables a un Pod local.

```bash
kubescape list frameworks
kubescape list controls --framework NSA
kubescape list controls --framework NSA --search container
```

Los nombres de ejemplo del paquete revisado incluyen cis-v1.12.0 y cis-eks-t1.8.0. No suponga que cis-v1.23 o cis es un alias universal. Las actualizaciones de políticas cambian la cobertura/puntuación; registre conjuntamente las versiones del binario y los hashes de las políticas.

| ID de control | Nombre del paquete revisado |
|---|---|
| C-0004 | Resources memory limit and request |
| C-0009 | Resource limits |
| C-0013 | Non-root containers |
| C-0016 | Allow privilege escalation |
| C-0034 | Automatic mapping of service account |
| C-0035 | Administrative Roles |
| C-0036 | Validate admission controller (validating) |
| C-0039 | Validate admission controller (mutating) |
| C-0057 | Privileged container |

C-0036/0039 no son controles de wildcard-RBAC/risky-ServiceAccount. La severidad también depende del paquete: el C-0057 revisado era High, no universalmente Critical.

### Frameworks personalizados

--use-from carga un objeto de política local. Un nombre YAML y una lista sin resolver de ID de controles no son necesariamente un framework ejecutable. El ejemplo policies/nsa.json es el paquete probado con registros de licencia, procedencia y SHA. Cree/pruebe nuevos controles Rego con características actuales de la CLI, como kubescape policy init y kubescape policy test, y después revise los requisitos de la organización.

<span id="scanning-pipeline-flow"></span>
<span id="cluster-scanning"></span>
<span id="specific-control-scanning"></span>
<span id="yaml-and-helm-manifest-scanning-shift-left"></span>
<span id="image-vulnerability-scanning"></span>
<span id="rbac-visualization-and-analysis"></span>

## Análisis con la CLI

![Entrada de Kubescape, evaluación, campos de puntuación y formatos de informe](../.gitbook/assets/en-security-11-kubescape-1.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-security-11-kubescape-1.html)


### Clúster frente a entrada local

```bash
# This accesses the current cluster; check authorization and scope first.
kubescape scan framework nsa --include-namespaces production
# Explicit local-file scan:
kubescape scan framework nsa secure-pod.yaml \
  --use-from policies/nsa.json --controls-config policies/controls-inputs.json \
  --exceptions no-exceptions.json --keep-local \
  --format json --output report.json
```

--format/-f selecciona el formato; --output/-o asigna el nombre del archivo. `-o json > report.json` no selecciona una salida JSON. La versión 4.0.14 admite JSON/SARIF/HTML/PDF/JUnit/gitlab-sast y otros formatos; elija el que espera la herramienta receptora.

Renderice Helm/Kustomize localmente antes de analizar para hacer explícitos los valores efectivos. Las comprobaciones locales no reproducen el defaulting de API, admission, la autorización de IAM ni el comportamiento de red. --include-api-audit, --custom-framework y --sort-by eran desconocidos en la CLI revisada. No presente scan rbac como un subcomando actual independiente.

### Resultados locales reales

insecure-pod.yaml es un **fixture de análisis sintético, no una receta de Deployment**. Usa campos reales privileged/runAsUser en lugar del inexistente runAsRoot. secure-pod.yaml también demuestra solo la configuración; reemplace su imagen de aplicación antes de cualquier Deployment real.

| Entrada local | Cumplimiento | puntuación | Resultado |
|---|---:|---:|---|
| Pod inseguro | 55 | 62.5 | Fallos High |
| Pod seguro | 95 | 6.818182 | La puerta High se supera; no todos los controles se superan |

Estos valores se aplican a la instantánea de políticas adjunta y a un Pod local. No miden la seguridad ni la explotabilidad del clúster.

### Análisis de imágenes y RBAC

Solicite explícitamente el análisis de imágenes con kubescape scan image IMAGE. La CLI 4.0.14 usa Grype 0.104.1 y Syft 1.42.3 en sus dependencias de origen; el componente kubevuln del Operator está versionado por separado. Verifique las credenciales del registro, la plataforma, la actualidad de la base de datos y los errores del análisis. El análisis del host difiere del análisis de imágenes y puede requerir acceso adicional al host/creación de recursos.

Los controles RBAC evalúan los Roles/Bindings recopilados dentro del alcance de API autorizado. Un RoleBinding concede acceso dentro de su namespace, no en todos los namespaces. El análisis estático no establece por sí solo permisos no utilizados, autorización IAM externa ni todas las rutas de acceso efectivas.

<span id="continuous-scanning-architecture"></span>
<span id="operator-components"></span>
<span id="scheduled-scanning-configuration"></span>
<span id="vulnerability-scanning-integration"></span>
<span id="runtime-threat-detection-node-agent-with-ebpf"></span>
<span id="kubernetes-api-attack-detection"></span>

## Modo Operator (en el clúster)

![Coordinación del operador de Kubescape y API de almacenamiento agregada](../.gitbook/assets/en-security-11-kubescape-2.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-security-11-kubescape-2.html)


Use los campos kubescapeScheduler.scanSchedule y requestBody.commands[].args.scanV1 del chart. defaultFrameworks proporciona valores predeterminados para solicitudes sin destinos; targetNames explícito tiene prioridad. Un ConfigMap arbitrario con scanSchedule no establece que un controlador lo consuma.

Los resultados de spdx.softwarecomposition.kubescape.io/v1beta1 se sirven mediante la **API agregada** del componente de almacenamiento, no todos los CRD ordinarios. Los CRD independientes incluyen SecurityException, ClusterSecurityException y OperatorCommand. Descubra los nombres/alcances reales antes de consultar resultados.

```bash
kubectl get apiservices v1beta1.spdx.softwarecomposition.kubescape.io
kubectl api-resources --api-group=spdx.softwarecomposition.kubescape.io
kubectl get pods,pvc -n kubescape
```

No presente los ejemplos antiguos de ScanSchedule, VulnerabilityScanConfig, ThreatDetectionConfig, AcceptedRisk y ScanConfiguration como API instaladas por este chart. Los perfiles/detección de node-agent deben usar las API/capacidades reales para la imagen elegida. La configuración habilitada no es prueba de recopilación o detección saludable en todos los nodes.

<span id="risk-score-calculation"></span>
<span id="severity-levels"></span>
<span id="viewing-risk-scores"></span>
<span id="prioritization-strategy"></span>

## Puntuación de riesgo

summaryDetails.complianceScore y summaryDetails.score son agregados diferentes. Un cumplimiento mayor indica que se superan más comprobaciones; la puntuación de riesgo no es el mismo valor ni simplemente 100-cumplimiento. No presente pesos de severidad ni SLA de respuesta inventados como una fórmula universal de Kubescape.

```bash
jq '{compliance: .summaryDetails.complianceScore, risk: .summaryDetails.score,
     failed: [.summaryDetails.controls[] | select(.status == "failed") | {controlID, name, severity}]}' report.json
```

Use --compliance-threshold como una **puntuación mínima de cumplimiento**, y --severity-threshold para la severidad de controles fallidos. Una puntuación local de 55 devolvió exit 0 con el umbral 55 y exit 1 con 56. --min-severity filtra la salida; no sustituye los cálculos de puerta actuales.

**La versión 4.0.14 acepta --fail-threshold como flag de compatibilidad obsoleta, pero ignora su valor.** La prueba devolvió exit 0 con hallazgos fallidos cuando solo se proporcionó --fail-threshold 0. Distinga ese flag inerte de opciones que aún se procesan, como --scan-images/--skip-controls, y flags realmente desconocidos.

<span id="ci-cd-integration-workflow"></span>
<span id="github-actions-workflow"></span>
<span id="gitlab-ci-cd-integration"></span>
<span id="jenkins-pipeline-integration"></span>
<span id="threshold-based-gates"></span>

<span id="cicd-integration"></span>

## Integración de CI/CD

![Puertas de CI basadas en cumplimiento mínimo, severidad y salida del comando](../.gitbook/assets/en-security-11-kubescape-3.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-security-11-kubescape-3.html)


### Puerta de seguridad compartida

```bash
#!/usr/bin/env bash
# Scan explicit local manifests with an isolated Kubernetes/client configuration.
set -euo pipefail
if [[ $# -ne 2 ]]; then
  printf 'Usage: %s LOCAL_MANIFEST OUTPUT_JSON\n' "$0" >&2
  exit 2
fi
manifest_path=$1
report_path=$2
if [[ ! -f $manifest_path ]]; then
  printf 'Expected an existing local manifest file: %s\n' "$manifest_path" >&2
  exit 2
fi
# An absolute operand cannot be parsed as a flag such as --help.
manifest_path="$(cd -- "$(dirname -- "$manifest_path")" && pwd)/$(basename -- "$manifest_path")"
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
: "${KUBESCAPE_BIN:=kubescape}"
: "${COMPLIANCE_MINIMUM:=90}"
: "${SEVERITY_LIMIT:=high}"
umask 077
scan_temp_dir=$(mktemp -d "${TMPDIR:-/tmp}/kubescape-local.XXXXXX")
trap 'rm -rf -- "$scan_temp_dir"' EXIT
mkdir -- "$scan_temp_dir/cache"
cat > "$scan_temp_dir/kubeconfig" <<'YAML'
apiVersion: v1
kind: Config
clusters: []
contexts: []
users: []
current-context: ''
YAML
# Block inherited in-cluster discovery as well as kubeconfig and cached backend state.
env -u KUBERNETES_SERVICE_HOST -u KUBERNETES_SERVICE_PORT -u KUBERNETES_PORT -u KUBERNETES_MASTER \
  KUBECONFIG="$scan_temp_dir/kubeconfig" KS_CACHE_DIR="$scan_temp_dir/cache" \
  "$KUBESCAPE_BIN" --cache-dir "$scan_temp_dir/cache" scan framework nsa "$manifest_path" \
  --kubeconfig "$scan_temp_dir/kubeconfig" --host-scan=false \
  --use-from "$script_dir/policies/nsa.json" \
  --controls-config "$script_dir/policies/controls-inputs.json" \
  --exceptions "$script_dir/no-exceptions.json" \
  --honor-inline-exceptions=false \
  --keep-local \
  --compliance-threshold "$COMPLIANCE_MINIMUM" \
  --severity-threshold "$SEVERITY_LIMIT" \
  --format json --output "$report_path"
```


La puerta de CI ignora las anotaciones skip-control, usa un kubeconfig vacío y una caché nueva, y borra el descubrimiento en clúster heredado. --keep-local por sí solo no impide el acceso a la API de Kubernetes. Cinco pruebas nativas con un contexto de API loopback hostil produjeron cero solicitudes y los códigos de fallo/éxito esperados.

La entrada ausente, los errores de análisis y los umbrales fallidos devuelven un valor distinto de cero. No los oculte con continue-on-error ni `|| true`. La carga del informe puede ejecutarse después de un fallo, pero no determina el éxito. Excluir un control cambia el denominador evaluado y debe registrarse.

### GitHub Actions

El [workflow validado](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/kubescape/github-actions.yaml) fija el binario/checksum y analiza solo k8s/rendered.yaml mediante la instantánea de políticas local. El proyecto debe producir primero ese archivo; su ausencia hace fallar el job. Los permisos son contents:read, sin comentarios de PR ni envío a SaaS.

### GitLab y Jenkins

Ambos sistemas pueden conservar el mismo código de salida de scan-manifests.sh y archivar informes. El JSON genérico de Kubescape no es el esquema SAST ni Code Quality de GitLab. Para informes SAST integrados, valide la salida actual de --format gitlab-sast frente a la versión receptora. Jenkins readJSON/publishHTML requiere plugins; no publique un archivo HTML que el pipeline nunca generó.

<span id="eks-specific-controls"></span>
<span id="aws-auth-configmap-analysis"></span>
<span id="irsa-iam-roles-for-service-accounts-validation"></span>
<span id="eks-security-best-practices-scan"></span>

## Guía específica para EKS

Los análisis de manifests de Kubernetes no validan completamente la configuración del control plane de EKS, IAM, las access entries, Pod Identity/IRSA ni las políticas de node. aws-auth es una ruta de autenticación heredada; inspeccione el modo de autenticación y las access entries actuales. system:masters o un usuario IAM de emergencia no es un ejemplo de mínimo privilegio.

C-0034 comprueba el automounting de tokens de service account, no la confianza/aud/sub/política IAM completa de IRSA. Distinga el token STS proyectado del montaje automático de tokens de API de Kubernetes. Valide por separado la identidad de workload real y las operaciones de AWS permitidas.

Revise los permisos/mutaciones de host-scanning y remediation antes de habilitarlos. El ejemplo deshabilita el acceso a Secret de todo el clúster y remediation, mientras que los operadores aún deben inspeccionar el RBAC de scanner/operator/storage necesario para su instalación.

<span id="exception-policies"></span>
<span id="applying-exceptions-via-cli"></span>
<span id="accepted-risks-documentation"></span>
<span id="inline-resource-exceptions"></span>

## Gestión de excepciones de controles

### Excepciones de CLI

```json
[
  {
    "name": "documentation-privileged-exception",
    "policyType": "postureExceptionPolicy",
    "actions": [
      "alertOnly"
    ],
    "resources": [
      {
        "designatorType": "Attributes",
        "attributes": {
          "namespace": "demo-app",
          "kind": "Pod",
          "name": "insecure-example"
        }
      }
    ],
    "posturePolicies": [
      {
        "controlID": "C-0057"
      }
    ]
  }
]
```


Esto es un **array JSON** consumido por la CLI, no un envoltorio de ConfigMap. La excepción alertOnly probada marcó C-0057 como acknowledged y preservó el fallo y el cumplimiento 55. --exclude-controls C-0057 eliminó el control de la evaluación, cambiando el denominador y la puntuación. Una excepción no es una remediation.

### Excepciones en el clúster

```yaml
apiVersion: kubescape.io/v1beta1
kind: SecurityException
metadata:
  name: documentation-privileged-exception
  namespace: demo-app
spec:
  author: documentation-security-team
  reason: Synthetic scan example; replace with an approved owner and justification.
  expiresAt: '2026-09-30T00:00:00Z'
  match:
    resources:
      - apiGroup: ''
        kind: Pod
        name: insecure-example
  posture:
    - controlID: C-0057
      action: alert_only
```


Las API actuales son kubescape.io/v1beta1 SecurityException/ClusterSecurityException. Establezca el alcance de namespace, la coincidencia, la acción de postura, la caducidad y la propiedad conforme a la política aprobada. El éxito del esquema no establece la aplicación por el controlador, RBAC ni el comportamiento de CEL. CLI alertOnly difiere de CRD alert_only. No confíe en anotaciones ignore inventadas para el procesamiento de excepciones.

<span id="periodic-scanning-schedule"></span>
<span id="scanning-configuration"></span>
<span id="compliance-reporting"></span>
<span id="remediation-workflow"></span>
<span id="integration-with-other-security-tools"></span>
<span id="prometheus-metrics-integration"></span>

## Prácticas recomendadas

![Verificación de remediation y aceptación de riesgo registrada por separado](../.gitbook/assets/en-security-11-kubescape-4.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-security-11-kubescape-4.html)


Registre el alcance, las comprobaciones superadas/fallidas/no disponibles, los hashes de políticas, las imágenes de herramientas, los propietarios de excepciones y las fechas de caducidad. Compare puntuaciones solo entre entradas/políticas equivalentes. El análisis de node, el análisis de imágenes y la detección en runtime son fuentes de evidencia independientes.

### Integración con Prometheus

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PodMonitor
metadata:
  name: kubescape-posture
  namespace: monitoring
spec:
  namespaceSelector:
    matchNames: [kubescape]
  selector:
    matchLabels:
      app.kubernetes.io/name: kubescape-operator
      app.kubernetes.io/instance: kubescape
      app.kubernetes.io/component: prometheus-exporter
  podMetricsEndpoints:
    - port: metrics
      path: /metrics
      interval: 60s
```


El Pod exporter revisado nombra metrics al puerto de contenedor 8080, mientras que su puerto Service no tiene nombre. Por tanto, este ejemplo usa un PodMonitor que coincide con las etiquetas reales del Pod y el puerto con nombre. Prometheus Operator y la selección de PodMonitor de Prometheus son requisitos previos independientes.

Los ejemplos reales de gauges del exporter 0.2.23 son kubescape_controls_total_cluster_high y kubescape_controls_total_workload_high. Un sufijo _total no los convierte en counters. Los antiguos nombres kubescape_compliance_score/critical_findings/last_scan_timestamp no son métricas comunes establecidas. Supervise por separado los scrapes ausentes y los datos obsoletos.

<span id="table-of-contents"></span>
<span id="key-takeaways"></span>
<span id="quick-reference-commands"></span>
<span id="references"></span>
<span id="related-documentation"></span>

## Resumen y referencias

La validación local cubrió binario/checksum, instantánea de políticas, límites de umbral/severidad/puerta obsoleta, comportamiento de excepción/exclusión, la puerta shell publicada, el renderizado de Helm, el esquema de SecurityException, el direccionamiento de PodMonitor, la sintaxis de GitHub Actions y treinta casos de navegador de diagramas. No se realizaron operaciones reales de AWS/Kubernetes/registro/notificación/SaaS.

- [Historial de Kubescape en CNCF](https://www.cncf.io/projects/kubescape/)
- [Documentación de Kubescape](https://kubescape.io/docs/)
- [Frameworks y controles](https://kubescape.io/docs/frameworks-and-controls/)
- [Documentación de Operator](https://kubescape.io/docs/operator/)
- [CLI 4.0.14](https://github.com/kubescape/kubescape/releases/tag/v4.0.14)
- [Flags fijados de la CLI](https://github.com/kubescape/kubescape/blob/v4.0.14/cmd/scan/scan.go)
- [Operator chart 1.40.4](https://github.com/kubescape/helm-charts/releases/tag/kubescape-operator-1.40.4)
- [Biblioteca de políticas](https://github.com/kubescape/regolibrary)
- [Métricas del exporter 0.2.23](https://github.com/kubescape/prometheus-exporter/blob/v0.2.23/metrics/metrics.go)
- [Seguridad en runtime](./08-runtime-security.md)
- [Prácticas de seguridad de EKS](./06-eks-security-best-practices.md)
