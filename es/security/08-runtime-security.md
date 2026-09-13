# Seguridad en tiempo de ejecución

> **Última actualización**: September 13, 2026
> **Base de validación**: Falco 0.44.1 / chart 9.1.0, Falcosidekick 2.35.0 / chart 0.14.0, Tetragon 1.7.1. Verifique la compatibilidad con el kernel, el SO y el tipo de nodo reales.

La seguridad en tiempo de ejecución observa la actividad de procesos, archivos y red, y restringe operaciones seleccionadas mediante políticas probadas. **Una alerta no es prueba de una vulneración; la detección y la prevención requieren pruebas separadas.** Esta guía se verificó con CLI locales, esquemas, Helm y eventos sintéticos. No se utilizó ningún clúster real, programa BPF del kernel ni canal de notificación.

<span id="container-runtime-threats"></span>
<span id="detection-technologies"></span>

## Panorama de amenazas en tiempo de ejecución

| Punto de observación | Qué puede mostrar | Límites |
|---|---|---|
| Hook de syscall/kernel | Ejecución de procesos, acceso a archivos, intentos de conexión | Compruebe eventos descartados, privilegios, compatibilidad del kernel y filtros |
| Auditoría de Kubernetes | Solicitante de API, verbo, objeto, estado de respuesta | No muestra cada operación de proceso/archivo dentro de un Pod |
| Flujo de red | Conexiones, descartes, veredictos de política | Un puerto o una conexión cifrada por sí solos no establecen intención maliciosa |
| Política de imagen/admisión | Vulnerabilidades, firmas, configuración de Pod | No detecta todos los comportamientos posteriores al Deployment |

eBPF por sí solo no garantiza baja sobrecarga ni seguridad. Mida hooks, volumen de eventos, filtrado, coste de salida, CPU y memoria en los nodos reales. No finalice automáticamente un proceso de producción simplemente porque el nombre de su comando coincida con un indicador.

<span id="default-rule-examples"></span>

## Falco

### Descripción general de Falco

Falco evalúa eventos frente a reglas. Una ruta típica de syscall es `Linux event → modern eBPF/kmod capture → Falco filter/rule → JSON output → Falcosidekick → notification/storage`. Slack y PagerDuty son integraciones posteriores, no clientes nativos de Slack dentro del motor de reglas de Falco.

La distribución 0.44.1 incluye el plugin de contenedores 0.7.1. Proporciona campos como container.id, por lo que deshabilitar todos los plugins evita que las reglas que usan esos campos se compilen o ejecuten. Verifique los sockets del runtime, la recopilación de metadatos de Kubernetes y los permisos de acceso.

### Instalación de Falco (EKS)

Este ejemplo se dirige a nodos Linux EC2 cuyo acceso al host administra. No suponga que un DaemonSet puede ejecutarse en Fargate u otros hosts restringidos. Verifique los requisitos de kernel/BTF/capacidades de eBPF moderno. El chart 9.1.0 admite los tipos explícitos de driver `modern_ebpf` y `kmod`; no conserve la configuración antigua `ebpf`.

Descargue el [directorio de ejemplo](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/security/runtime-security) y ejecute estos comandos desde `examples/security/runtime-security`. El [README de ejemplo](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/runtime-security/README.md) describe los tres archivos de valores y las reglas.

```bash
helm repo add falcosecurity https://falcosecurity.github.io/charts
helm repo update falcosecurity
helm upgrade --install falcosidekick falcosecurity/falcosidekick \
  --version 0.14.0 --namespace falco --create-namespace \
  --values falcosidekick-values.yaml
helm upgrade --install falco falcosecurity/falco \
  --version 9.1.0 --namespace falco \
  --values falco-values.yaml
```

El appVersion del chart Sidekick difiere de su etiqueta de imagen predeterminada, por lo que el ejemplo fija explícitamente image.tag en 2.35.0. Prepare primero el Secret de credenciales de salida y los CRD de Prometheus Operator. La ausencia de un Secret puede impedir el inicio de un Pod. Deshabilite las opciones de notificación/métricas que no use en un laboratorio mínimo.

```yaml
driver:
  kind: modern_ebpf
metrics:
  enabled: true
serviceMonitor:
  create: true
falcosidekick:
  enabled: false
falco:
  json_output: true
  json_include_output_property: true
  http_output:
    enabled: true
    url: http://falcosidekick.falco.svc:2801
customRules:
  documentation-rules.yaml: |-
    - macro: doc_spawned
      condition: evt.type in (execve, execveat) and evt.res = SUCCESS
    - macro: doc_container
      condition: container.id != host
    - rule: Documentation shell execution
      desc: Observe successful shell process execution in a container; not proof of compromise.
      condition: doc_spawned and doc_container and proc.name in (bash, sh, dash, zsh)
      output: Shell process observed (proc=%proc.name command=%proc.cmdline container=%container.id)
      priority: NOTICE
      tags:
      - documentation
      - process
    - rule: Documentation service account token read
      desc: Observe read access to the default projected service account token path; legitimate
        clients also read it.
      condition: evt.type in (open, openat, openat2) and evt.is_open_read
        = true and fd.num >= 0 and doc_container and fd.name startswith /var/run/secrets/kubernetes.io/serviceaccount/
      output: Service account path read (proc=%proc.name file=%fd.name container=%container.id)
      priority: NOTICE
      tags:
      - documentation
      - credential_access
```


La configuración envía HTTP al Service ClusterIP de falcosidekick instalado por separado. Compartir un namespace no autentica ni cifra el tráfico. Configure la política de acceso y TLS/mTLS según el límite de confianza real, y verifique la conectividad del nodo/Falco. Falco usa campos snake_case como json_output y http_output. Las configuraciones antiguas jsonOutput/httpOutput y las opciones grpc eliminadas fallan con el esquema 0.44.1.

### Estructura de reglas de Falco

Estas reglas definen sus propias macros requeridas y evitan reemplazar nombres de reglas predeterminadas. Use la sintaxis de anulación del ruleset fijado cuando cambie intencionalmente una regla existente.

```yaml
- macro: doc_spawned
  condition: evt.type in (execve, execveat) and evt.res = SUCCESS
- macro: doc_container
  condition: container.id != host
- rule: Documentation shell execution
  desc: Observe successful shell process execution in a container; not proof of compromise.
  condition: doc_spawned and doc_container and proc.name in (bash, sh, dash, zsh)
  output: Shell process observed (proc=%proc.name command=%proc.cmdline container=%container.id)
  priority: NOTICE
  tags:
  - documentation
  - process
- rule: Documentation service account token read
  desc: Observe read access to the default projected service account token path; legitimate
    clients also read it.
  condition: evt.type in (open, openat, openat2) and evt.is_open_read
    = true and fd.num >= 0 and doc_container and fd.name startswith /var/run/secrets/kubernetes.io/serviceaccount/
  output: Service account path read (proc=%proc.name file=%fd.name container=%container.id)
  priority: NOTICE
  tags:
  - documentation
  - credential_access
```


Después de eliminar los eventos enter, Falco 0.44.1 advierte que evt.dir está obsoleto. Estos ejemplos seleccionan directamente los eventos exitosos de exec y lectura. Los clientes legítimos de Kubernetes leen tokens de cuentas de servicio, por lo que la señal de lectura por sí sola no es «acceso no autorizado». Combínela con líneas base de cargas de trabajo, binarios aprobados e identidad de Pod.

### Escritura de reglas personalizadas

| Patrón | Posible señal | Matiz requerido |
|---|---|---|
| Minería sospechosa | Nombres de proceso, cadenas de pool/stratum, uso inusual de recursos | El cambio de nombre y el cómputo legítimo pueden evadir o activar heurísticas |
| Shell inversa sospechosa | Cadenas de conexión en argv de shell y flujos salientes inusuales | El fd.name de un evento exec no prueba una conexión de red |
| Escalada de privilegios | Cambios de credenciales, configuraciones SUID, capacidades | Compruebe el significado de user.uid/proc.uid/proc.suid y que la operación tuvo éxito |
| Escape sospechoso | Acceso a namespace/ruta de host y montajes inusuales | Las cadenas nsenter o /.dockerenv no establecen un escape exitoso |

La compilación de reglas no mide la eficacia de la detección. Pruebe eventos sintéticos/autorizados de laboratorio, cargas de trabajo normales, metadatos ausentes y contadores de descartes antes de un despliegue gradual. Los argumentos, rutas y logs pueden contener secretos; restrinja los campos de eventos, la retención y el acceso.

### Configuración de alertas de Falco

```yaml
config:
  existingSecret: falcosidekick-output-credentials
  slack:
    minimumpriority: warning
  pagerduty:
    minimumpriority: critical
  aws:
    region: ap-northeast-2
    cloudwatchlogs:
      loggroup: /falco/alerts
      logstream: documentation
      minimumpriority: warning
  elasticsearch:
    minimumpriority: warning
    checkcert: true
webui:
  enabled: false
serviceMonitor:
  enabled: true
image:
  tag: 2.35.0
```


falcosidekick-output-credentials es un Secret existente en el mismo namespace que se lee mediante envFrom. Proporcione solo las variables de las salidas aprobadas, como SLACK_WEBHOOKURL, PAGERDUTY_ROUTINGKEY y ELASTICSEARCH_HOSTPORT/USERNAME/PASSWORD, mediante su proceso de administración de secretos. Escribir `${ELASTIC_PASSWORD}` dentro de los valores de Helm no realiza sustitución de shell. No exponga credenciales en Git, líneas de comandos ni logs de revisión.

La configuración de AWS pertenece a config.aws. Verifique la identidad de la carga de trabajo y limite las acciones/recursos IAM a los grupos/streams de logs previstos. minimumpriority usa emergency/alert/critical/error/warning/notice/informational/debug, no `high`. Compruebe las condiciones de activación, los reintentos y las métricas de fallos de cada salida. El ejemplo deshabilita la interfaz web.

<span id="tetragon-installation"></span>
<span id="tracingpolicy-basic-structure"></span>
<span id="process-monitoring"></span>

## Tetragon

### Descripción general de Tetragon

Tetragon puede ejecutarse independientemente del CNI de Cilium. Distinga los eventos integrados process_exec/exit de los hooks adicionales de TracingPolicy. El flujo es `kernel hook → selector → Post/supported action → JSON/gRPC/metrics`; el CRD de Kubernetes por sí mismo no se ejecuta dentro del kernel.

```bash
helm repo add cilium https://helm.cilium.io
helm repo update cilium
helm upgrade --install tetragon cilium/tetragon \
  --version 1.7.1 --namespace kube-system --values tetragon-values.yaml
```

```yaml
tetragon:
  enableProcessCred: true
  enableProcessNs: true
```


Compruebe la preparación del operador/CRD y el kernel, BTF y las capacidades de cada nodo. El renderizado de Helm no establece la vinculación de hooks. Los ejemplos con namespace se dirigen a las cargas de trabajo demo-app; confirme el alcance efectivo para el tipo de política y hook elegidos.

### Monitorización de acceso a archivos

```yaml
apiVersion: cilium.io/v1alpha1
kind: TracingPolicyNamespaced
metadata:
  name: documentation-file-observe
  namespace: demo-app
spec:
  kprobes:
  - call: security_file_permission
    syscall: false
    args:
    - index: 0
      type: file
    - index: 1
      type: int
    selectors:
    - matchArgs:
      - index: 0
        operator: Prefix
        values:
        - /etc/shadow
        - /root/.ssh/
      - index: 1
        operator: Mask
        values:
        - '4'
      matchActions:
      - action: Post
```


El segundo argumento de `security_file_permission(struct file *, int mask)` es una máscara de permisos: MAY_READ=4, MAY_WRITE=2. Asignar «índice 1 = flags de apertura» a la función security_file_open de un solo argumento es incorrecto. Los flags de apertura O_WRONLY=1/O_RDWR=2 también difieren de esta máscara de permisos. Este hook por sí solo no cubre cada mutación de mmap/truncate/archivo.

### Monitorización de red

```yaml
apiVersion: cilium.io/v1alpha1
kind: TracingPolicyNamespaced
metadata:
  name: documentation-outbound-observe
  namespace: demo-app
spec:
  kprobes:
  - call: tcp_connect
    syscall: false
    args:
    - index: 0
      type: sock
    selectors:
    - matchArgs:
      - index: 0
        operator: DPort
        values:
        - '22'
        - '4444'
        - '5555'
      matchActions:
      - action: Post
```


tcp_connect observa los intentos de conexión TCP. Un puerto de destino por sí solo no implica tráfico malicioso ni rechazo de política. La actividad del puerto UDP 53 no proporciona un análisis completo de preguntas/respuestas DNS; use la ruta de telemetría DNS adecuada.

### Aplicación en tiempo de ejecución

Comience con el comportamiento Post/monitor y compruebe las operaciones normales y los falsos positivos. Sigkill envía una señal; según el comportamiento del hook y del kernel, no puede deshacer efectos que ya ocurrieron. La anulación del valor de retorno requiere una syscall/función de seguridad compatible, configuración del kernel y un resultado de error adecuado. No todos los kprobes arbitrarios lo admiten.

No afirme prevención universal de minería/shell inversa a partir de nombres de archivo o cadenas argv. execve argv es un array de punteros, no un argumento de cadena único. Leerlo como una sola cadena no inspecciona la línea de comandos completa como se pretende. Distinga el filtrado de argumentos de eventos de proceso de las acciones del kernel y valide la aplicación en un laboratorio aprobado y con alcance limitado.

### Uso de la CLI de Tetragon

```bash
kubectl exec -n kube-system ds/tetragon -c tetragon -- tetra getevents -o json
kubectl exec -n kube-system ds/tetragon -c tetragon -- \
  tetra getevents -o compact --namespace production --process curl
# Filter stored synthetic events locally:
tetra getevents -o json --namespace demo-app < events.jsonl
```

Ejecutar contra un DaemonSet selecciona el agente de un Pod/nodo; esto no es agregación en todo el clúster. Aquí solo se ejercitó la ruta de filtrado stdin. La implementación 1.7.1 de tetra tracingpolicy modify también crea un cliente gRPC, por lo que no se usó como validador sin conexión.

<span id="feature-comparison-table"></span>
<span id="use-case-recommendations"></span>

## Comparación entre Falco y Tetragon

| Criterio | Falco | Tetragon |
|---|---|---|
| Política | Condiciones de eventos y rulesets | Hooks de kernel, selectores, acciones |
| Uso común | Detección con integración de notificación/almacenamiento | Visibilidad de procesos y aplicación explícita de hooks |
| Comprobaciones operativas | Metadatos de driver/plugin/runtime y eventos descartados | Compatibilidad BTF/hook, alcance de política, efectos secundarios |
| Rendimiento | Mida CPU/memoria/pérdida de eventos bajo carga real | Use la misma carga de trabajo; eBPF por sí solo no establece superioridad |

Desplegar ambos no es automáticamente la mejor opción. Considere la recopilación duplicada, los privilegios de nodo, el coste, la complejidad operativa y la aplicación requerida.

## Registro de auditoría de Kubernetes

### Configuración de la política de auditoría

Esta política es para un **servidor de API de Kubernetes autogestionado**. La política de auditoría administrada de EKS no se reemplaza al aplicar este YAML. Habilite los logs de auditoría del plano de control de EKS y configure el acceso, la retención y el cifrado de CloudWatch.

```yaml
apiVersion: audit.k8s.io/v1
kind: Policy
omitStages:
- RequestReceived
rules:
- level: Metadata
  resources:
  - group: ''
    resources:
    - secrets
    - serviceaccounts/token
- level: Metadata
  resources:
  - group: ''
    resources:
    - pods/exec
    - pods/attach
    - pods/portforward
- level: Request
  resources:
  - group: rbac.authorization.k8s.io
    resources:
    - roles
    - rolebindings
    - clusterroles
    - clusterrolebindings
  verbs:
  - create
  - update
  - patch
  - delete
- level: Metadata
```


El registro Request/RequestResponse de Secrets y serviceaccounts/token puede conservar cuerpos de credenciales, así que use Metadata. Las reglas de auditoría siguen la primera coincidencia; coloque primero las reglas de recursos confidenciales. system:anonymous por sí solo no captura todos los fallos de autenticación. Examine las etapas de auditoría, responseStatus y los logs de autenticación. Un registro de auditoría exec no es una grabación de cada comando dentro de la sesión de terminal.

### Análisis de logs de auditoría de EKS

```text
fields @timestamp, user.username, verb, objectRef.resource, objectRef.name, responseStatus.code
| filter objectRef.resource = "secrets"
| sort @timestamp desc
| limit 100
```

Esta es una consulta de CloudWatch Logs Insights, no Bash. Un 403 es una respuesta rechazada; clasifique por separado las lecturas exitosas. Verifique la recopilación después de habilitar el registro y configure la retención.

<span id="cryptocurrency-mining-detection"></span>
<span id="reverse-shell-detection"></span>
<span id="privilege-escalation-detection"></span>

## Patrones de detección de amenazas en tiempo de ejecución

Seccomp restringe syscalls, pero el rechazo no siempre termina un proceso. Las acciones pueden devolver ERRNO, matar o notificar. RuntimeDefault se refiere al perfil del runtime; configúrelo explícitamente o verifique kubelet seccompDefault. Kubernetes 1.27+ por sí solo no lo aplica automáticamente a cada Pod.

AppArmor necesita compatibilidad de nodo y perfiles cargados. El modo Complain registra infracciones ordinarias, mientras que las reglas explícitas deny aún pueden bloquear. readOnlyRootFilesystem es un campo securityContext de contenedor; no impide el uso malicioso de volúmenes escribibles, acceso de red o memoria.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: runtime-security-demo
  namespace: demo-app
  labels:
    app: runtime-security-demo
spec:
  automountServiceAccountToken: false
  securityContext:
    runAsNonRoot: true
    runAsUser: 10001
    runAsGroup: 10001
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: app
    image: registry.example.com/team/app:REPLACE_WITH_APPROVED_VERSION
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
        - ALL
    resources:
      requests:
        cpu: 100m
        memory: 64Mi
      limits:
        cpu: 500m
        memory: 128Mi
    volumeMounts:
    - name: tmp
      mountPath: /tmp
  volumes:
  - name: tmp
    emptyDir:
      sizeLimit: 64Mi
```


La monitorización de runtime actual de GuardDuty admite nodos EKS EC2 y el modo automático de EKS, pero no EKS Hybrid Nodes ni EKS Fargate. Compruebe la matriz oficial de SO/kernel/arquitectura/versión de agente y el estado de cobertura. Habilitar la característica no establece una cobertura saludable para cada nodo.

Hubble `--verdict DROPPED` muestra descartes; no todos los descartes son una denegación de NetworkPolicy. Inspeccione juntos el motivo del descarte y el veredicto de política.

<span id="forensics-container"></span>

## Respuesta a incidentes

### Procedimiento de aislamiento de Pod

Las NetworkPolicy estándar permiten combinar como una unión. Agregar una política con listas ingress/egress vacías no anula las conexiones permitidas por otra política. Una etiqueta de app puede seleccionar varios Pods que pertenecen a la aplicación.

1. Identifique el namespace, UID de Pod, nodo, propietario y políticas de red existentes.
2. Elija un mecanismo de aislamiento aprobado. Para una denegación explícita específica de CNI o cambios en las autorizaciones existentes, revise los objetivos exactos, el impacto y la recuperación.
3. Pruebe las conexiones establecidas y nuevas; tenga en cuenta hostNetwork, el tráfico de nodo y las limitaciones del CNI.
4. Proteja las evidencias y registre las decisiones de aislamiento, interrupción y recuperación.

### Recopilación de evidencias y análisis forense

```bash
#!/usr/bin/env bash
# Authorized read-only Kubernetes API collection. Sensitive output stays in a private directory.
set -euo pipefail
if [[ $# -ne 3 ]]; then
  printf 'Usage: %s NAMESPACE POD OUTPUT_DIRECTORY\n' "$0" >&2
  exit 2
fi
namespace=$1
pod_name=$2
evidence_dir=$3
if [[ ! $namespace =~ ^[a-z0-9]([-a-z0-9]*[a-z0-9])?$ ]] || [[ ! $pod_name =~ ^[a-z0-9]([-a-z0-9.]*[a-z0-9])?$ ]]; then
  printf 'Invalid namespace or pod name\n' >&2
  exit 2
fi
umask 077
mkdir -- "$evidence_dir"
kubectl get pod "$pod_name" -n "$namespace" -o json > "$evidence_dir/pod.json"
kubectl describe pod "$pod_name" -n "$namespace" > "$evidence_dir/describe.txt"
kubectl logs "$pod_name" -n "$namespace" --all-containers=true --timestamps=true > "$evidence_dir/logs.txt"
# Previous logs may not exist. Record this separately instead of calling collection complete silently.
if ! kubectl logs "$pod_name" -n "$namespace" --all-containers=true --previous=true --timestamps=true > "$evidence_dir/previous-logs.txt" 2> "$evidence_dir/previous-logs-error.txt"; then
  printf 'Previous logs unavailable; inspect previous-logs-error.txt\n' >&2
fi
(
  cd -- "$evidence_dir"
  sha256sum -- pod.json describe.txt logs.txt previous-logs.txt previous-logs-error.txt > SHA256SUMS
)
printf 'API evidence written to %s. This is not a memory or filesystem snapshot.\n' "$evidence_dir"
```


Este script recopila metadatos/logs de Pod mediante la API y registra sumas de comprobación. Se probó con un doble de subproceso, incluidos fallos y directorios de salida privados 0700, no contra un clúster real. Las especificaciones y logs de Pod pueden contener secretos/información personal; use almacenamiento y controles de acceso aprobados.

Un Pod forense nuevo no se ejecuta automáticamente en el nodo objetivo ni comparte el namespace de procesos objetivo. hostPath /proc, SYS_PTRACE y NET_ADMIN otorgan un acceso considerable; use un procedimiento aprobado cuando sea necesario. emptyDir no es almacenamiento de evidencias duradero. Archivar el `/` de un contenedor efímero no es automáticamente una instantánea del sistema de archivos del contenedor objetivo.

<span id="falco-to-elasticsearch"></span>
<span id="prometheus-grafana-dashboard"></span>

<span id="siemsoar-integration"></span>

## Integración con SIEM/SOAR

Compare los namespaces, selectores y puertos de ServiceMonitor con los Services reales. El chart de Falco tiene un Service de métricas; Falcosidekick expone métricas en su puerto HTTP. El chart Sidekick renderiza un ServiceMonitor solo cuando monitoring.coreos.com/v1 está disponible.

```promql
sum by (priority) (rate(falcosecurity_falcosidekick_falco_events_total[5m]))
```

Este es el contador de eventos recibidos de Falcosidekick 2.35.0. No trate el falco_events_total original como un nombre de métrica universal. Distinga los recuentos acumulados de las tasas por intervalo; compruebe las etiquetas reales, reinicios, fallos de salida y scrapes ausentes. Coordine incluso las pruebas de notificaciones sintéticas de Slack/PagerDuty/SIEM con los destinatarios y el proceso operativo.

<span id="table-of-contents"></span>
<span id="recommendations"></span>

## Resumen

Las comprobaciones locales cubrieron dos reglas de Falco, cuatro casos de esquema de configuración, tres filtros JSON de Tetragon y dos CRD, tres charts de Helm y cuatro casos de éxito/fallo del script de evidencias. No se ejecutaron la vinculación al kernel, la eficacia de detección, la aplicación real, la cobertura de GuardDuty, la recopilación de auditoría/CloudWatch ni las notificaciones externas.

## Referencias

- [Instalación de Falco en Kubernetes](https://falco.org/docs/setup/kubernetes/)
- [Configuración de Falco 0.44.1](https://github.com/falcosecurity/falco/blob/0.44.1/falco.yaml)
- [Configuración de Falcosidekick 2.35.0](https://github.com/falcosecurity/falcosidekick/blob/2.35.0/config_example.yaml)
- [Políticas de trazado de Tetragon](https://tetragon.io/docs/concepts/tracing-policy/)
- [Aplicación de Tetragon](https://tetragon.io/docs/concepts/enforcement/)
- [Monitorización de archivos de Tetragon 1.7.1](https://github.com/cilium/tetragon/blob/v1.7.1/examples/quickstart/file_monitoring.yaml)
- [Auditoría de Kubernetes](https://kubernetes.io/docs/tasks/debug/debug-cluster/audit/)
- [Semántica de NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Seccomp](https://kubernetes.io/docs/tutorials/security/seccomp/)
- [AppArmor](https://kubernetes.io/docs/tutorials/security/apparmor/)
- [Logs del plano de control de EKS](https://docs.aws.amazon.com/eks/latest/userguide/control-plane-logs.html)
- [Requisitos de runtime de GuardDuty para EKS](https://docs.aws.amazon.com/guardduty/latest/ug/prereq-runtime-monitoring-eks-support.html)
- [Contenedores de MITRE ATT&CK](https://attack.mitre.org/matrices/enterprise/containers/)
