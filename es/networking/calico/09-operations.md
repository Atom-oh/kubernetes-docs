# Parte 9: Guía de operaciones de Calico {#part-9-calico-operations-guide}

> **Versiones de referencia**: Calico 3.32.2 / Operator 1.42.6 / Kubernetes 1.34–1.36, versiones probadas por Calico.
> **Última actualización**: 12 de septiembre de 2026

## Descripción general {#overview}

Este capítulo explica la instalación, la supervisión, la resolución de problemas, las actualizaciones y las prácticas de operación de Calico en entornos de producción.

La operación sigue un ciclo de comprobación y mejora: valide la instalación, observe su comportamiento, investigue los cambios y conserve la configuración y el estado necesarios para recuperarse antes de actualizar. Exportar la configuración y probar la recuperación del almacén de datos sirven para fines distintos.

## Guía de instalación {#installation-guide}

Utilice un único método para gestionar la instalación y un perfil adecuado para la plataforma. El ejemplo siguiente corresponde a un **clúster Linux autogestionado nuevo con Calico como CNI completo**, Iptables y VXLAN. Prepare un CIDR de pods sin solapamientos, un sistema operativo y un kernel compatibles, conectividad con la API de Kubernetes y comunicación UDP 4789 por la red subyacente entre los nodos correspondientes. Esta no es la configuración de aplicación de políticas con VPC CNI; para EKS, consulte la [parte 8](08-eks-integration.md). Revise los [modos de red](03-networking-modes.md) antes de elegir otro diseño de overlay o BGP.

### Manifiestos de Tigera Operator {#tigera-operator-manifests}

Calico 3.32 requiere instalar sus CRD independientes además del manifiesto del operador:

```bash
kubectl create -f https://raw.githubusercontent.com/projectcalico/calico/v3.32.2/manifests/v1_crd_projectcalico_org.yaml
kubectl create -f https://raw.githubusercontent.com/projectcalico/calico/v3.32.2/manifests/tigera-operator.yaml
kubectl wait --for=condition=Available deployment/tigera-operator \
  -n tigera-operator --timeout=300s
```

Guarde el siguiente contenido en `installation.yaml` y sustituya el CIDR de pods del ejemplo por el preparado para el clúster. Omita MTU para utilizar la detección del operador; mida la ruta real antes de fijar un valor.

```yaml
apiVersion: operator.tigera.io/v1
kind: Installation
metadata:
  name: default
spec:
  variant: Calico
  cni:
    type: Calico
  calicoNetwork:
    bgp: Disabled
    linuxDataplane: Iptables
    ipPools:
    - cidr: 10.244.0.0/16
      blockSize: 26
      encapsulation: VXLAN
      natOutgoing: Enabled
      nodeSelector: all()
    nodeAddressAutodetectionV4:
      kubernetes: NodeInternalIP
  nodeUpdateStrategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
---
apiVersion: operator.tigera.io/v1
kind: APIServer
metadata:
  name: default
spec: {}
---
apiVersion: operator.tigera.io/v1
kind: Goldmane
metadata:
  name: default
spec: {}
---
apiVersion: operator.tigera.io/v1
kind: Whisker
metadata:
  name: default
spec: {}
```

```bash
kubectl apply -f installation.yaml
```

En este ejemplo con VXLAN, BGP está deshabilitado. Los diagnósticos de BGP solo se aplican si el perfil elegido lo habilita. Calico API server, Goldmane y Whisker son componentes de código abierto. La guía actual de registros de flujos de la edición OSS considera esta función una vista previa tecnológica; evalúe ese estado antes de depender de ella en la operación.

Deje que el operador gestione los recursos de los componentes y el escalado de Typha hasta que las mediciones justifiquen ajustes admitidos. Los límites de memoria arbitrarios, los cambios no admitidos en `typhaDeployment.spec.replicas`/`minReadySeconds` y una entrada `KubeControllers` en la lista antigua `componentResources` no constituyen una configuración de producción adecuada. Consulte la API Installation de la versión utilizada y las secciones de [arquitectura](02-architecture.md) y [escalado](07-advanced-topics.md).

### Alternativa con Helm {#helm-alternative}

El chart de Helm instala el mismo operador. Guarde los ajustes siguientes en `calico-values.yaml` y elija este método como alternativa a los manifiestos; no instale un segundo operador.

```yaml
installation:
  enabled: true
  variant: Calico
  cni:
    type: Calico
  calicoNetwork:
    bgp: Disabled
    linuxDataplane: Iptables
    ipPools:
    - cidr: 10.244.0.0/16
      blockSize: 26
      encapsulation: VXLAN
      natOutgoing: Enabled
      nodeSelector: all()
    nodeAddressAutodetectionV4:
      kubernetes: NodeInternalIP
  nodeUpdateStrategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
apiServer:
  enabled: true
goldmane:
  enabled: true
whisker:
  enabled: true
manageCRDs: true
```

```bash
helm repo add projectcalico https://docs.tigera.io/calico/charts
helm repo update projectcalico
helm template calico projectcalico/tigera-operator \
  --namespace tigera-operator --version v3.32.2 \
  -f calico-values.yaml > calico-rendered.yaml

# Apply only after reviewing the prepared cluster and rendered resources.
helm install calico projectcalico/tigera-operator \
  --namespace tigera-operator --create-namespace --version v3.32.2 \
  -f calico-values.yaml
```

El campo `podAnnotations` del nivel superior se aplica al pod del operador. No habilita las métricas de Felix ni configura su recopilación por Prometheus para todos los componentes. Configure las métricas expresamente en la sección siguiente. `manageCRDs: true` permite al operador gestionar los CRD después de iniciarse; más adelante se explica el orden de actualización necesario para utilizar campos nuevos.

### Alternativa con manifiestos directos {#direct-manifest-alternative}

Si la instalación ya se gestiona mediante manifiestos directos, utilice la versión y el perfil correspondientes y conserve sus ajustes. Revise el archivo descargado antes de aplicarlo:

```bash
curl -fL https://raw.githubusercontent.com/projectcalico/calico/v3.32.2/manifests/calico.yaml \
  -o calico.yaml
```

Edite los ajustes pertinentes, incluido el CIDR de pods y el modo de red habilitado. Una sustitución global con `sed` puede cambiar un ejemplo o un valor comentado sin configurar el pool de IP real. Evite mezclar recursos de manifiestos directos en `kube-system` con una instalación del operador en `calico-system`.

### Validar la instalación {#validate-installation}

```bash
kubectl get tigerastatus
kubectl get installation default -o yaml
kubectl rollout status daemonset/calico-node -n calico-system --timeout=300s
kubectl get pods -n calico-system -o wide
kubectl get nodes -o wide
```

Con manifiestos directos, compruebe los espacios de nombres y los recursos reales. Que los componentes estén disponibles no demuestra que se apliquen las políticas ni que las aplicaciones sean accesibles. Pruebe las rutas de Service y DNS necesarias, además de conexiones permitidas y denegadas, con cargas de trabajo gestionadas por controladores. Para comprobar el acceso a la API, utilice el endpoint HTTPS real del servidor y la autenticación adecuada; una petición HTTP a `kubernetes.default` no es una comprobación autenticada de su estado.

## Referencia de comandos de calicoctl {#calicoctl-command-reference}

Instale el binario oficial de la versión **3.32.2** y compruebe su suma de verificación como se indica en el [capítulo de instalación](01-introduction.md). La versión ofrece archivos para Linux AMD64/ARM64, macOS AMD64/ARM64 y Windows AMD64; elija la arquitectura del equipo. No ejecute comandos de descarga de PowerShell en Bash ni utilice un cliente antiguo después de actualizar sin investigar el aviso de incompatibilidad.

Para acceder al almacén de datos de Kubernetes, una configuración habitual en un shell Unix es:

```bash
export DATASTORE_TYPE=kubernetes
export KUBECONFIG="$HOME/.kube/config"
calicoctl version
calicoctl get nodes -o wide
calicoctl get networkpolicy -A
calicoctl get globalnetworkpolicy
calicoctl get tier
calicoctl get networkset -A
calicoctl get globalnetworkset
calicoctl get workloadendpoint -A
calicoctl get hostendpoint
calicoctl get ippool -o yaml
calicoctl get bgpconfiguration default -o yaml
calicoctl get bgppeer -o wide
calicoctl get felixconfiguration default -o yaml
```

El kubeconfig debe seleccionar el clúster previsto y disponer de los permisos RBAC necesarios. Puede indicar un archivo de configuración de la API de Calico con `--config`; no dé por hecho que se detecta automáticamente cualquier ruta bajo `~/.config`. Para acceder directamente a un almacén etcdv3, utilice la configuración admitida y valide los certificados. Es otro perfil de despliegue y no proporciona acceso a un servicio etcd gestionado por EKS.

### Diagnóstico del nodo local {#local-node-diagnostics}

`calicoctl node status` muestra el **estado de BGP del nodo local**. Configurar un kubeconfig no lo convierte en una comprobación remota de la disponibilidad de todo el clúster. Ejecútelo en el nodo previsto con el acceso documentado o examine el socket de BIRD de ese nodo como se muestra más adelante.

`calicoctl node diags` reúne un archivo de diagnóstico en el nodo seleccionado. La opción admitida `--log-dir` indica el **directorio de registros de entrada**; en 3.32.2 no existe `--output-dir`. La implementación necesita permisos de root y puede ejecutar un contenedor de diagnóstico privilegiado y enviar una señal a Felix para volcar su estado. Utilícelo como una recopilación deliberada de evidencias, no como una comprobación pasiva. Proteja el archivo resultante y utilice la ruta de salida que muestre el comando.

### IPAM de Calico {#calico-ipam}

Ejecute estos comandos únicamente cuando **Calico IPAM** asigne las direcciones. Si utiliza VPC CNI, host-local u otro IPAM, investigue el asignador correspondiente.

```bash
calicoctl ipam show
calicoctl ipam show --show-blocks
calicoctl ipam show --show-borrowed
calicoctl ipam show --show-configuration
calicoctl ipam show --ip=10.244.0.15
calicoctl ipam check --show-problem-ips -o ipam-report.json
```

`--show-blocks` muestra la utilización de los bloques. Para asociar un bloque a un nodo, consulte los registros BlockAffinity; esta asociación no equivale al PodCIDR del Node de Kubernetes. `--ip` consulta una asignación sin modificarla. Un informe puede señalar casos que investigar, pero la ausencia de un pod no demuestra por sí sola que sea seguro liberar la dirección.

La CLI revisada no admite las opciones `ipam release --block` ni `--handle`. La liberación mediante informes comprueba la secuencia de asignación y sigue requiriendo el procedimiento de limpieza de [IPAM avanzado](07-advanced-topics.md). `ipam split NUMBER --cidr=...` sí existe, pero divide un **pool de IP**, no un bloque de asignación; exige bloquear el almacén de datos y elegir un número de divisiones que sea potencia de dos. Es una migración planificada, no una solución rutinaria para un pod bloqueado.

### Cambios y exportaciones de recursos {#resource-changes-and-exports}

`get`, `create`, `apply`, `replace`, `patch` y `delete` actúan sobre los tipos de recursos admitidos. Indique el tipo y el espacio de nombres, revise el conjunto completo de políticas y conserve los campos ajenos al cambio al aplicar un parche. Por ejemplo, los ajustes de registro deben incorporarse al FelixConfiguration existente o a su configuración gestionada por GitOps, en lugar de sustituir el objeto por otro que solo contenga el campo nuevo.

`calicoctl get all` no crea una copia de todos los recursos. Enumere los tipos necesarios e incluya por separado las políticas de Kubernetes y los recursos del operador. La opción `calicoctl get ... --export` existe, pero la CLI revisada la ignora cuando no se indica un nombre de recurso. Tampoco convierte una lista exportada en una copia portátil completa para recuperación ante desastres. Consulte la sección de copias de seguridad.

## Métricas de Prometheus {#prometheus-metrics}

Confirme los nombres, los tipos y las etiquetas en la **salida `/metrics` de la versión instalada**. Las series específicas de un plano de datos pueden faltar en otros perfiles; una serie ausente no equivale a cero. Los nombres siguientes se contrastaron con el código de Calico 3.32.2 y las referencias oficiales de métricas.

### Habilitar las métricas de los componentes {#enable-component-metrics}

Las métricas de Felix están deshabilitadas de forma predeterminada; su puerto predeterminado es **9091**. Las de Typha también están deshabilitadas; el binario utiliza **9091** de forma predeterminada, mientras que el ejemplo del operador selecciona expresamente **9093**. Las métricas de kube-controllers están habilitadas de forma predeterminada en **9094**.

Si ya utiliza una instalación del operador, incorpore estos ajustes mediante el sistema que gestione su configuración:

```bash
kubectl patch felixconfiguration default --type=merge \
  -p '{"spec":{"prometheusMetricsEnabled":true,"prometheusMetricsPort":9091}}'
kubectl patch installation default --type=merge \
  -p '{"spec":{"typhaMetricsPort":9093}}'
kubectl get service calico-typha-metrics -n calico-system
kubectl get service calico-kube-controllers-metrics -n calico-system
```

El operador crea el Service de métricas de Typha cuando se configura `typhaMetricsPort`; no lo sustituya por un Service que entre en conflicto. Una instalación mediante manifiestos directos necesita configurar por separado el entorno de Typha y su Service. Limite el acceso a las métricas: los endpoints de la red del host pueden necesitar controles adicionales de host o de red, además de NetworkPolicy.

### Nombres y significado de las métricas {#metric-names-and-meaning}

| Métrica | Tipo y significado |
| --- | --- |
| `felix_active_local_endpoints` | Gauge: endpoints locales de cargas de trabajo **y del host**. Cero puede ser válido y no comprueba la disponibilidad |
| `felix_active_local_policies` | Gauge: políticas activas en este nodo. Su suma cuenta instancias locales, no políticas únicas del clúster |
| `felix_cluster_num_hosts`, `felix_cluster_num_policies` | Gauges del clúster observados por cada Felix; no sume copias idénticas de varios nodos |
| `felix_int_dataplane_failures` | Counter: actualizaciones fallidas del plano de datos que se reintentarán; el nombre revisado no lleva el sufijo `_total` |
| `felix_int_dataplane_apply_time_seconds` | **Summary** de la duración de las actualizaciones incrementales; expone cuantiles, `_sum` y `_count`, no buckets de un histograma |
| `felix_iptables_restore_calls`, `felix_iptables_restore_errors` | Counters de llamadas y errores de iptables-restore en el plano de datos iptables |
| `felix_log_errors`, `felix_logs_dropped` | Errores al escribir registros del proceso y registros descartados al bloquearse la salida; no cuentan entradas de nivel ERROR ni paquetes denegados |
| `typha_connections_active` | Gauge: conexiones abiertas, incluidas las que negocian el establecimiento de la conexión |
| `typha_connections_streaming{syncer="..."}` | Gauge: clientes que completaron la negociación y reciben actualizaciones en flujo |
| `typha_connections_accepted` | Counter: conexiones aceptadas |
| `typha_connections_dropped` | Counter: conexiones cerradas **para redistribuir la carga**, no un contador general de fallos de red |
| `typha_cache_size{syncer="..."}` | Gauge: entradas de clave y valor en la caché |
| `typha_updates_total{syncer="..."}` | Counter: actualizaciones **recibidas del** sincronizador del almacén de datos |
| `ipam_allocations_in_use{ippool="...",node="..."}` | Gauge de kube-controllers: direcciones de Calico IPAM asignadas a cargas de trabajo o interfaces |
| `ipam_ippool_size{ippool="..."}` | Gauge de kube-controllers: total de direcciones en el CIDR del pool |
| `ipam_allocations_gc_candidates` | Posibles asignaciones abandonadas que deben investigarse; no autoriza a liberar direcciones |

El socket de control de BIRD no es un exportador de Prometheus. Las métricas `bird_protocol_up` y `calico_bgp_peer_status` necesitan un exportador o colector elegido por separado, con etiquetas y significado comprobados; esta instalación no produce esas series. Utilice los diagnósticos de BGP siguientes o el [método con CalicoNodeStatus](04-bgp-deep-dive.md) y añada alertas del exportador después de comprobar su salida real.

### Configuración de ServiceMonitor {#servicemonitor-wiring}

El ejemplo presupone que ya existen los CRD de Prometheus Operator y el espacio de nombres `monitoring`. Haga coincidir las etiquetas del ServiceMonitor con `serviceMonitorSelector` del recurso Prometheus y compruebe que su `serviceMonitorNamespaceSelector` incluya ese espacio de nombres. Las etiquetas de PrometheusRule también deben coincidir con `ruleSelector`. Un recurso válido que no se seleccione no genera recopilación de métricas ni carga reglas.

Los **Service independientes** siguientes evitan modificar los gestionados por el operador y proporcionan a los tres un puerto llamado `http-metrics`. Si ya recopila estos endpoints, reutilice esa configuración para evitar duplicados. El campo `jobLabel` del ServiceMonitor genera los jobs `calico-felix`, `calico-typha` y `calico-kube-controllers` utilizados a continuación.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: calico-audit-felix-metrics
  namespace: calico-system
  labels:
    audit.calico/component: calico-felix
spec:
  clusterIP: None
  selector:
    k8s-app: calico-node
  ports:
  - name: http-metrics
    port: 9091
    targetPort: 9091
    protocol: TCP
---
apiVersion: v1
kind: Service
metadata:
  name: calico-audit-typha-metrics
  namespace: calico-system
  labels:
    audit.calico/component: calico-typha
spec:
  clusterIP: None
  selector:
    k8s-app: calico-typha
  ports:
  - name: http-metrics
    port: 9093
    targetPort: 9093
    protocol: TCP
---
apiVersion: v1
kind: Service
metadata:
  name: calico-audit-kube-controllers-metrics
  namespace: calico-system
  labels:
    audit.calico/component: calico-kube-controllers
spec:
  clusterIP: None
  selector:
    k8s-app: calico-kube-controllers
  ports:
  - name: http-metrics
    port: 9094
    targetPort: 9094
    protocol: TCP
---
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: calico-components
  namespace: monitoring
  labels:
    app.kubernetes.io/part-of: calico-monitoring
spec:
  jobLabel: audit.calico/component
  selector:
    matchExpressions:
    - key: audit.calico/component
      operator: Exists
  namespaceSelector:
    matchNames:
    - calico-system
  endpoints:
  - port: http-metrics
    interval: 30s
    scrapeTimeout: 10s
    path: /metrics
```

Compruebe el descubrimiento de endpoints, el RBAC, el acceso de red y la página Targets de Prometheus. `endpoints.port` de ServiceMonitor selecciona el **nombre del puerto del Service**, no el número de puerto del contenedor. Confirme cada destino descubierto; recopilar métricas de una dirección balanceada del Service no demuestra que estén representados todos los nodos.

## Panel de Grafana {#grafana-dashboard}

Utilice la fuente de datos de Prometheus configurada y los paneles actuales de series temporales y estadísticas. Lo siguiente son consultas para paneles, no un dashboard completo que pueda importarse. Seleccione las métricas de un solo clúster; una fuente de datos central para varios clústeres necesita conservar la etiqueta del clúster en los selectores y las agregaciones.

| Panel | PromQL |
| --- | --- |
| Endpoints por nodo | `felix_active_local_endpoints{job="calico-felix"}` |
| Políticas activas por nodo | `felix_active_local_policies{job="calico-felix"}` |
| Número de políticas del clúster observado | `max(felix_cluster_num_policies{job="calico-felix"})` |
| Reintentos del plano de datos por segundo | `rate(felix_int_dataplane_failures{job="calico-felix"}[5m])` |
| Conexiones de Typha que transmiten actualizaciones | `typha_connections_streaming{job="calico-typha"}` |
| p99 local de Summary | `felix_int_dataplane_apply_time_seconds{job="calico-felix",quantile="0.99"}` |

El cuantil de Summary de un proceso no es el p99 de todo el clúster y no puede combinarse con `histogram_quantile`. Para calcular la duración media de las actualizaciones incrementales mientras se producen:

```promql
rate(felix_int_dataplane_apply_time_seconds_sum{job="calico-felix"}[5m])
/ rate(felix_int_dataplane_apply_time_seconds_count{job="calico-felix"}[5m])
```

Sin observaciones, la media queda indefinida (`0/0`); no demuestra una latencia de cero. Esta Summary no genera series `_bucket`, y las consultas no verificadas de `felix_iptables_restore_time_seconds` deben sustituirse por los contadores de operaciones y la métrica de duración del plano de datos disponibles.

Puede examinar la utilización de direcciones de Calico IPAM con:

```promql
sum by (ippool) (
  max by (ippool, node) (ipam_allocations_in_use{job="calico-kube-controllers",ippool!="no_ippool"})
)
/ max by (ippool) (ipam_ippool_size{job="calico-kube-controllers",ippool!="no_ippool"})
```

El `max` por pool y nodo evita contar varias veces observaciones idénticas de los controladores; la suma posterior reúne las asignaciones de los nodos. Mide la **utilización de direcciones**, no los bloques consumidos ni la capacidad de asignación disponible para un nodo concreto. También influyen los selectores de pool, la afinidad estricta, los límites de bloques, las direcciones reservadas o de túneles y otras restricciones. No describe las asignaciones de VPC CNI; investigue por separado las métricas vacías, ausentes o con capacidad cero.

## Reglas de alerta {#alert-rules}

Estas reglas de ejemplo presuponen los jobs anteriores, un único clúster seleccionado y kube-state-metrics para la métrica del DaemonSet. Habilite reglas de destinos ausentes solo para los componentes que espera ejecutar. Si reutiliza la supervisión existente, adapte los selectores y ajuste los umbrales y las duraciones a su carga de trabajo.

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: calico-alerts
  namespace: monitoring
  labels:
    app.kubernetes.io/part-of: calico-monitoring
spec:
  groups:
  - name: calico.rules
    rules:
    - alert: CalicoDaemonSetUnavailable
      expr: kube_daemonset_status_number_unavailable{namespace="calico-system",daemonset="calico-node"}
        > 0
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: Calico DaemonSet has unavailable Pods
        description: Inspect the affected node, rollout and kube-state-metrics data.
    - alert: CalicoMetricsScrapeFailed
      expr: up{job=~"calico-(felix|typha|kube-controllers)"} == 0
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: Calico scrape failed for {{ $labels.job }} on {{ $labels.instance
          }}
    - alert: CalicoMetricsTargetsMissing
      expr: |-
        absent(up{job="calico-felix"})
        or absent(up{job="calico-typha"})
        or absent(up{job="calico-kube-controllers"})
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: No discovered metrics targets for {{ $labels.job }}
    - alert: CalicoDataplaneRetries
      expr: rate(felix_int_dataplane_failures{job="calico-felix"}[5m]) > 0
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: Dataplane updates are being retried on {{ $labels.instance }}
    - alert: CalicoDataplaneMeanSlow
      expr: |-
        (rate(felix_int_dataplane_apply_time_seconds_sum{job="calico-felix"}[5m])
        / rate(felix_int_dataplane_apply_time_seconds_count{job="calico-felix"}[5m])) > 0.5
        and (rate(felix_int_dataplane_apply_time_seconds_count{job="calico-felix"}[5m]) > 0)
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: Mean dataplane update time exceeds 0.5s on {{ $labels.instance }}
    - alert: CalicoIPAMHighAddressUsage
      expr: |-
        (sum by (ippool) (
          max by (ippool, node) (ipam_allocations_in_use{job="calico-kube-controllers",ippool!="no_ippool"})
        )
        / max by (ippool) (ipam_ippool_size{job="calico-kube-controllers",ippool!="no_ippool"})) > 0.8
        and on (ippool)
        (max by (ippool) (ipam_ippool_size{job="calico-kube-controllers",ippool!="no_ippool"}) > 0)
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: High address utilization in Calico IP pool {{ $labels.ippool }}
        description: Address utilization is {{ $value | humanizePercentage }}; inspect
          per-node eligibility and block constraints.
```

`up == 0` detecta un destino descubierto cuya recopilación ha fallado. No detecta uno que haya desaparecido por completo; las reglas `absent` detectan la pérdida de **todos** los destinos de un componente esperado. Para detectar un solo nodo ausente entre otros sanos, compare con el inventario esperado de nodos y del DaemonSet. Que no aparezca una alerta en la interfaz no demuestra que todo funcione si nunca se cargaron su métrica o su regla.

Las conexiones de Typha pueden disminuir y su contador de redistribución puede aumentar durante el escalado. Antes de declarar una incidencia, contraste el retraso persistente de los clientes que reciben actualizaciones con la disponibilidad de los componentes. Del mismo modo, cero endpoints locales no significa que Felix no esté disponible. Consulte la disponibilidad y el estado reales del despliegue y realice pruebas sintéticas independientes de conexiones permitidas y denegadas.

## Análisis de registros y resolución de problemas {#log-analysis-and-troubleshooting}

### Empezar por la carga de trabajo y el nodo afectados {#start-with-the-affected-workload-and-node}

Un pod Pending puede no ser programable antes de que se invoque ningún CNI. Examine primero los eventos y `spec.nodeName`. Si existe un error de CNI o de asignación de IP, identifique el asignador y examine los registros de kubelet y CNI del nodo afectado; el registro del proceso Felix no contiene todos los errores de IPAM de los pods.

```bash
CALICO_NAMESPACE=calico-system
WORKLOAD_NAMESPACE=calico-demo
WORKLOAD_POD=replace-with-actual-pod

kubectl describe pod "$WORKLOAD_POD" -n "$WORKLOAD_NAMESPACE"
CALICO_NODE=$(kubectl get pod "$WORKLOAD_POD" -n "$WORKLOAD_NAMESPACE" \
  -o jsonpath='{.spec.nodeName}')
test -n "$CALICO_NODE" || { echo "Pod is not scheduled to a node" >&2; exit 1; }
kubectl get pods -n "$CALICO_NAMESPACE" -l k8s-app=calico-node \
  --field-selector "spec.nodeName=$CALICO_NODE" -o wide

# Select the actual agent Pod on this node, including during a rollout.
CALICO_POD=replace-with-actual-calico-node-pod
kubectl logs -n "$CALICO_NAMESPACE" "$CALICO_POD" -c calico-node \
  --since=15m --tail=200 --timestamps
```

Limite expresamente el período y el número de líneas recuperadas. Con selectores, `kubectl logs` puede devolver pocas líneas de forma predeterminada; solicitar una ventana temporal no demuestra que se hayan recuperado todas sus líneas. Para un contenedor reiniciado, consulte también el registro anterior si está disponible. Conserve los errores de recuperación en lugar de interpretarlos como ausencia de errores.

Los registros del proceso Felix describen la programación del plano de datos y la actividad de los componentes. Establecer `logSeverityScreen` en Debug no crea un registro de decisiones de política por paquete. Antes de un cambio temporal, anote el valor original y el sistema que gestiona su configuración; después restaure ese valor exacto o la ausencia del campo, sin suponer que antes era Info. La salida a archivo o syslog también depende de la ruta configurada y del entorno de ejecución.

### Asignación de direcciones y conectividad {#address-allocation-and-connectivity}

| Síntoma | Comprobaciones antes de modificar el estado |
| --- | --- |
| No hay nodo asignado | Eventos del planificador, capacidad, afinidad y taints; todavía no es un diagnóstico de IPAM |
| Error de asignación de CNI | Registros del asignador real, capacidad de pools y direcciones, elegibilidad por selectores, límites de bloques y afinidad, y acceso a la API |
| La IP del pod responde, pero falla el Service | Endpoints y EndpointSlices, puertos del Service, gestión de Service con kube-proxy o BPF, DNS y políticas |
| Funcionan los paquetes pequeños, pero no los grandes | MTU de la red subyacente y del overlay, fragmentación, PMTUD y ruta de retorno |
| La política prevista no bloquea el tráfico | Identidad y etiquetas del endpoint real, dirección, selectores de espacio de nombres, tier y orden, reglas de permiso anteriores, limitaciones de red del host y otras interfaces, y conexiones establecidas |

```bash
kubectl exec -n "$CALICO_NAMESPACE" "$CALICO_POD" -c calico-node -- ip route show
kubectl exec -n "$CALICO_NAMESPACE" "$CALICO_POD" -c calico-node -- ip -d link show
calicoctl get networkpolicy -n "$WORKLOAD_NAMESPACE" -o yaml
calicoctl get globalnetworkpolicy -o yaml
calicoctl get tier -o yaml
calicoctl get workloadendpoint -n "$WORKLOAD_NAMESPACE" -o yaml
kubectl get pod "$WORKLOAD_POD" -n "$WORKLOAD_NAMESPACE" --show-labels
```

No elija el primer pod `calico-node` del clúster suponiendo que está en el nodo de la carga de trabajo afectada. El resultado de ICMP por sí solo no valida políticas TCP ni HTTP. Utilice una carga de diagnóstico aprobada con herramientas conocidas y el protocolo y el puerto reales de la aplicación.

Para Calico IPAM, utilice los comandos de consulta anteriores y el [procedimiento de limpieza de IPAM](07-advanced-topics.md). El CIDR del pool y blockSize son inmutables; añadir un pool elegible sin solapamientos es un cambio de capacidad planificado, no una ampliación del CIDR existente. No libere direcciones ni reinicie un agente antes de demostrar la causa.

En instalaciones del operador, la MTU y la detección automática de direcciones se configuran en `Installation.spec.calicoNetwork`, junto con los campos de Felix específicos del túnel cuando estén documentados. `FelixConfiguration.spec.mtu` e `ipAutoDetectionMethod` no pertenecen a las API revisadas. Siga la [guía de MTU y redes](03-networking-modes.md), conserve los demás ajustes y valide por separado los pods nuevos y los existentes.

### Diagnósticos de BGP {#bgp-diagnostics}

Ejecute estas comprobaciones únicamente si el perfil utiliza BGP. En el pod `calico-node` seleccionado, utilice el socket real de BIRD:

```bash
kubectl exec -n "$CALICO_NAMESPACE" "$CALICO_POD" -c calico-node -- \
  birdcl -s /var/run/calico/bird.ctl show protocols all
kubectl exec -n "$CALICO_NAMESPACE" "$CALICO_POD" -c calico-node -- \
  birdcl -s /var/run/calico/bird.ctl show route
calicoctl get bgpconfiguration -o yaml
calicoctl get bgppeer -o yaml
calicoctl get bgpfilter -o yaml
```

Utilice `bird6.ctl` para el demonio IPv6 correspondiente cuando esté desplegado. Compruebe los ASN local y del vecino, la dirección de origen seleccionada, TCP 179 en ambos sentidos, la autenticación, los ajustes de TTL, los filtros de rutas y los anuncios esperados. Una conexión TCP correcta no demuestra que se haya establecido la sesión ni aceptado los prefijos necesarios. Revise la configuración incluida antes de dar por hecho que existe un archivo de registro; los scripts de ejecución y registro de BIRD del contenedor publicado determinan dónde escribe. Consulte el [análisis detallado de BGP](04-bgp-deep-dive.md).

## Automatización de comprobaciones de estado {#health-check-automation}

La siguiente **comprobación de estado de una instalación del operador** se ejecuta desde un entorno de administración con Bash, jq y un kubectl compatible. Realiza consultas de API y registros sin modificar recursos, comprueba la generación observada y la disponibilidad de réplicas del DaemonSet, y falla si una consulta falla. No examina sockets de BGP ni valida el reenvío de paquetes ni demuestra que todas las políticas sean correctas.

```bash
#!/usr/bin/env bash
# calico-status-check.sh: operator component status and bounded log collection.
set -euo pipefail
CALICO_NAMESPACE=${CALICO_NAMESPACE:-calico-system}

if ! calico_ds_json=$(kubectl get daemonset calico-node -n "$CALICO_NAMESPACE" \
  --request-timeout=20s -o json); then
  echo "Unable to read calico-node DaemonSet status" >&2
  exit 2
fi
if ! jq -e '
  .status.desiredNumberScheduled as $desired
  | ($desired > 0)
    and (.status.observedGeneration >= .metadata.generation)
    and (.status.updatedNumberScheduled == $desired)
    and (.status.numberReady == $desired)
    and (.status.numberAvailable == $desired)
    and ((.status.numberUnavailable // 0) == 0)
' <<<"$calico_ds_json" >/dev/null; then
  echo "Calico DaemonSet is not fully observed, updated and available" >&2
  exit 1
fi

if ! calico_status_json=$(kubectl get tigerastatus --request-timeout=20s -o json); then
  echo "Unable to read operator component status" >&2
  exit 2
fi
if ! jq -e '
  (.items | length) > 0 and all(.items[];
    any(.status.conditions[]?; .type == "Available" and .status == "True")
    and any(.status.conditions[]?; .type == "Progressing" and .status == "False")
    and any(.status.conditions[]?; .type == "Degraded" and .status == "False")
  )
' <<<"$calico_status_json" >/dev/null; then
  echo "Operator components are unavailable, progressing, degraded or missing conditions" >&2
  exit 1
fi

if ! calico_logs=$(kubectl logs -n "$CALICO_NAMESPACE" -l k8s-app=calico-node \
  -c calico-node --since=15m --tail=200 --timestamps --prefix \
  --request-timeout=20s); then
  echo "Unable to retrieve selected Calico logs; do not report no errors" >&2
  exit 2
fi
printf '%s\n' "$calico_logs"
echo "Component status checks passed; review these bounded logs and test application policy separately."
```

Un DaemonSet vacío o sin pods programados, un estado desactualizado o la ausencia de condiciones de los componentes no constituyen una comprobación correcta. Los registros están limitados al período y al número de líneas seleccionados y requieren interpretación. Un contador o la palabra ERROR por sí solos no equivalen a una interrupción en curso.

Para programar la comprobación como CronJob, empaquete y valide primero las herramientas y el script en una imagen aprobada. Utilice una ServiceAccount dedicada con permisos de lectura sobre el DaemonSet, los pods, sus registros y TigeraStatus; no reutilice la identidad privilegiada de `calico-node`. Configure la concurrencia, los plazos de ejecución y la notificación de fallos. La imagen `calico/ctl` no es un entorno de diagnóstico general con Bash y kubectl. Un Job ordinario tampoco puede examinar el socket de BIRD de otro nodo sin acceso adicional deliberado. Este script local no presupone un CronJob funcional dentro del clúster.

## Actualización de versión y recuperación {#version-upgrade-and-recovery}

### Preparar la transición {#prepare-the-transition}

```bash
calicoctl version
kubectl version --output=yaml
kubectl get deployment tigera-operator -n tigera-operator \
  -o jsonpath='{.spec.template.spec.containers[*].image}'
kubectl get tigerastatus
kubectl get daemonset calico-node -n calico-system -o wide
helm get values calico -n tigera-operator -o yaml
```

El comando de Helm solo se aplica a una instalación gestionada por Helm. Inventaríe las imágenes instaladas, los CRD, el almacén de datos, el sistema operativo y el kernel de los nodos, el plano de datos y la compatibilidad con Kubernetes. Conserve los manifiestos y valores gestionados, las políticas y un plan de recuperación probado. `kubectl version --short` ya no es una opción vigente.

Siga el [procedimiento de actualización a 3.32](https://docs.tigera.io/calico/latest/operations/upgrading/kubernetes-upgrade) correspondiente a la versión de origen y al método de instalación. Revise las notas de migración de OwnerReference y UID cuando cruce las versiones pertinentes. Fije la versión de destino y actualice también calicoctl.

Con Helm, aplique los CRD de Calico correspondientes mediante el sistema que los gestione antes de actualizar el operador, o utilice `manageCRDs: true` y espere a que el operador los instale antes de usar campos nuevos. Actualizar el operador no justifica sobrescribir indiscriminadamente la propiedad de los campos con `--force-conflicts`. Después del cambio revisado, supervise el operador, calico-node y los demás componentes configurados, y pruebe las conexiones permitidas y denegadas durante y después de la actualización.

El operador reconcilia el DaemonSet que gestiona. Retirar el agente de nodos «canary» con un parche de afinidad no constituye un despliegue canary seguro y puede dejar esos nodos sin aplicación de políticas. Pruebe la versión y la configuración en un entorno aislado representativo y siga los mecanismos admitidos para controlar el despliegue. No añada un segundo DaemonSet de nodos que compita con el primero.

### Límites de la recuperación {#recovery-limits}

`helm rollback`, aplicar un operador antiguo o importar una exportación de configuración no revierte automáticamente las migraciones de CRD o de datos ni restaura el estado del procesamiento de paquetes. Antes de elegir una recuperación, compruebe el procedimiento de descenso de versión admitido para las versiones de origen y destino y los datos almacenados. Que siga existiendo un recurso Installation no demuestra que no se hayan perdido datos.

Para recuperar el plano de control de EKS, consulte los requisitos actuales y el límite de siete días para la reversión descritos en la [parte 8](08-eks-integration.md). La compatibilidad de Calico, los complementos y las aplicaciones sigue siendo una responsabilidad independiente.

## Copias de seguridad y recuperación ante desastres {#backup-and-disaster-recovery}

### Separar el inventario de configuración de la recuperación del estado {#separate-configuration-inventory-from-state-recovery}

| Material | Finalidad y limitaciones |
| --- | --- |
| Manifiestos y valores de Helm gestionados en Git, y registro de versiones | Configuración deseada y responsabilidad de gestión; conserve las definiciones de CRD y las imágenes correspondientes |
| Políticas, tiers, conjuntos, pools, configuración BGP y filtros, y configuración de controladores de Calico | Inventario de configuración; incluya los recursos por espacio de nombres, las políticas en modo staged y los recursos globales que utilice |
| NetworkPolicy de Kubernetes, etiquetas de espacios de nombres y ServiceAccount, y RBAC relacionado | Identidad y dependencias de las políticas que una exportación exclusiva de Calico omite |
| Estado de hosts, nodos, endpoints e IPAM | Datos dependientes de la topología y del entorno de ejecución; no restaure sin revisión direcciones de nodos ni asignaciones antiguas en otro clúster |
| Copias del almacén de datos y datos de aplicaciones | Un mecanismo de recuperación coherente y credenciales y datos protegidos por separado; las listas YAML no son una instantánea atómica del almacén |

No existe el comando `kubectl export`. `calicoctl get TYPE -o yaml` exporta recursos; la opción `--export` tiene la limitación de recursos con nombre indicada anteriormente. En Kubernetes y etcd autogestionados, siga el [procedimiento de copia y recuperación de etcd de Kubernetes](https://kubernetes.io/docs/tasks/administer-cluster/configure-upgrade-etcd/) con versiones compatibles y pruebas de restauración. Los servicios gestionados requieren su mecanismo de recuperación admitido; este procedimiento no proporciona acceso al etcd de EKS.

### Ejemplo de inventario de configuración protegido {#protected-configuration-inventory-example}

Este script exporta un **subconjunto declarado** de una instalación del operador 3.32 que utiliza Calico IPAM. Requiere Bash, calicoctl, kubectl y sha256sum. El directorio de destino no debe existir; una exportación parcial conserva `STATE=incomplete`. No reúne Secrets, IAM externo, dispositivos de red, todos los recursos personalizados del operador ni el estado completo de asignación de IPAM. Amplíe el inventario expresamente según las funciones instaladas y proteja la copia independiente de credenciales.

```bash
#!/usr/bin/env bash
# calico-config-inventory.sh: protected configuration inventory, not a datastore snapshot.
set -euo pipefail
umask 077
CALICO_EXPORT_DIR=${1:?Usage: calico-config-inventory.sh NEW_EXPORT_DIRECTORY}
mkdir -m 700 -- "$CALICO_EXPORT_DIR"
printf '%s\n' incomplete > "$CALICO_EXPORT_DIR/STATE"

for calico_kind in node ippool ipreservation bgpconfiguration bgppeer bgpfilter \
  globalnetworkpolicy stagedglobalnetworkpolicy globalnetworkset \
  felixconfiguration kubecontrollersconfiguration ipamconfiguration \
  tier hostendpoint profile; do
  calicoctl get "$calico_kind" -o yaml > "$CALICO_EXPORT_DIR/$calico_kind.yaml"
done
for calico_kind in networkpolicy stagednetworkpolicy stagedkubernetesnetworkpolicy \
  networkset workloadendpoint; do
  calicoctl get "$calico_kind" -A -o yaml > "$CALICO_EXPORT_DIR/$calico_kind.yaml"
done
kubectl get installation default -o yaml > "$CALICO_EXPORT_DIR/installation.yaml"
kubectl get networkpolicies.networking.k8s.io -A -o yaml \
  > "$CALICO_EXPORT_DIR/kubernetes-networkpolicies.yaml"
kubectl get namespaces -o yaml > "$CALICO_EXPORT_DIR/namespaces.yaml"
kubectl get serviceaccounts -A -o yaml > "$CALICO_EXPORT_DIR/serviceaccounts.yaml"
(
  cd -- "$CALICO_EXPORT_DIR"
  sha256sum ./*.yaml > SHA256SUMS
)
printf '%s\n' complete > "$CALICO_EXPORT_DIR/STATE"
echo "Configuration inventory completed: $CALICO_EXPORT_DIR"
```

La marca `complete` indica que terminaron las consultas declaradas y sus sumas de verificación; no demuestra consistencia transaccional ni que se haya probado la recuperación ante desastres. Trate las exportaciones como datos sensibles de infraestructura. Compruebe las sumas, conserve copias fuera del dominio de fallo y ensaye la recuperación con el almacén de datos y las versiones reales.

### Planificar la restauración {#restore-planning}

1. Restaure un plano de control y un almacén de datos compatibles, junto con los CRD y el operador necesarios, mediante el método de recuperación elegido. Los requisitos de identidad e IPAM difieren entre un clúster nuevo y la recuperación del mismo clúster.
2. Revise la identidad de los espacios de nombres y de las ServiceAccount, las etiquetas y el RBAC. Restaure después la configuración declarativa gestionada en orden de dependencias, incluidos los tiers y los conjuntos antes de las políticas que los utilizan.
3. Revise los metadatos específicos del clúster, los objetos generados o gestionados por controladores, las direcciones antiguas de nodos y sus asignaciones. Un volcado sin procesar no es un manifiesto portátil del estado deseado.
4. Verifique la unicidad de las asignaciones de IP, las rutas, el cifrado, el funcionamiento de Service y DNS, y el tráfico permitido y denegado antes de reanudar los cambios normales.

`calicoctl datastore migrate export/import` es un procedimiento real de **migración de etcd a Kubernetes**, con bloqueo del almacén de datos y límites de reversión. No es un atajo de copia de seguridad general para un almacén Kubernetes existente. El bloqueo afecta a los pods nuevos y la migración documentada no puede revertirse después de desbloquear el almacén Kubernetes. Consulte el [procedimiento de migración](https://docs.tigera.io/calico/latest/operations/datastore-migration).

## Prácticas de operación recomendadas {#operational-best-practices}

### Políticas y acceso {#policy-and-access}

Empiece por validar la denegación predeterminada en un espacio de nombres de prueba seleccionado, con las dependencias necesarias de DNS, API, identidad, supervisión y aplicación. Una política global vacía con `all()` o un selector de etiquetas inexistente para el servidor de API o los nodos puede interrumpir tráfico esencial. Los endpoints de pods y de hosts siguen rutas de políticas distintas; consulte la [parte 5](05-network-policy.md) para ver ejemplos con alcance limitado, la semántica de tiers y los controles de endpoints de host. Mantenga una vía de recuperación utilizable de forma independiente y pruebe los casos de denegación antes de ampliar el alcance.

### Observación de flujos {#flow-observability}

Las instalaciones actuales de la edición OSS mediante operador o Helm pueden utilizar Goldmane y Whisker. La [guía OSS de registros de flujos](https://docs.tigera.io/calico/latest/observability/view-flow-logs) considera esta función una vista previa tecnológica y describe flujos agregados, no un registro por paquete o conexión. Los campos antiguos del registrador de archivos o DNS y nombres no válidos como `FlowLogsFileReporter` no constituyen una configuración OSS válida.

```bash
kubectl get goldmane,whisker
kubectl port-forward -n calico-system service/whisker 8081:8081
```

El reenvío de puertos escucha localmente de forma predeterminada. Whisker y Goldmane contienen datos sensibles de cargas de trabajo y redes; configure autenticación y controles de acceso antes de exponerlos en otro lugar. Si actualiza desde una versión anterior a estos componentes, habilite expresamente los recursos personalizados correspondientes. Los registros de depuración de procesos, las acciones Log de políticas, los registros de flujos agregados y las métricas de Prometheus responden a preguntas distintas.

### Rendimiento y recursos {#performance-and-resources}

Mida los cambios frecuentes de endpoints y políticas, la duración de la programación del plano de datos, las colas, la memoria y el tráfico real de las aplicaciones. Los intervalos de resincronización y actualización no son intervalos de consulta periódica de la API de Kubernetes; aumentarlos no optimiza de forma universal la carga de la API. Utilice el campo de duración `iptablesPostWriteCheckInterval`, no la denominación retirada `...Secs`. Conserve los ajustes de recursos admitidos por el sistema que gestiona la instalación y el escalado del operador.

No habilite BPF, DSR ni un patrón de interfaces supuesto como ajuste general de rendimiento. La [parte 6](06-ebpf-dataplane.md) explica los requisitos del kernel y de la plataforma, la gestión de Service, los conflictos con kube-proxy y la reversión. Los mapas conntrack más grandes consumen memoria y no eliminan todos los cuellos de botella. Si está justificado cambiar el plano de datos o los recursos, repita las pruebas pertinentes de carga de trabajo y fallos.

Las comprobaciones que acompañan a esta guía validan esquemas, consultas y casos de prueba de scripts sin conexión. No demuestran capacidad de producción, una actualización correcta del clúster ni recuperación ante desastres.

## Referencias {#references}

- [Requisitos de Calico](https://docs.tigera.io/calico/latest/getting-started/kubernetes/requirements)
- [API Installation de Calico](https://docs.tigera.io/calico/latest/reference/installation/api)
- [Supervisión de métricas de los componentes](https://docs.tigera.io/calico/latest/operations/monitor/monitor-component-metrics)
- [Métricas de Felix](https://docs.tigera.io/calico/latest/reference/felix/prometheus)
- [Métricas de Typha](https://docs.tigera.io/calico/latest/reference/typha/prometheus)
- [Métricas de kube-controllers](https://docs.tigera.io/calico/latest/reference/kube-controllers/prometheus)
- [Resolución de problemas de Calico](https://docs.tigera.io/calico/latest/operations/troubleshoot/troubleshooting)
- [Procedimiento de actualización de Calico](https://docs.tigera.io/calico/latest/operations/upgrading/kubernetes-upgrade)
- [API de Prometheus Operator](https://prometheus-operator.dev/docs/api-reference/api/)

## Próximos pasos y cuestionario {#next-steps-and-quiz}

Repase el [glosario](glossary.md), los [temas avanzados](07-advanced-topics.md), la [integración con EKS](08-eks-integration.md) y el [cuestionario de operaciones](../../quizzes/networking/calico/09-operations-quiz.md).
