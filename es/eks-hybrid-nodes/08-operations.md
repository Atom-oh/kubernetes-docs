# Operaciones y mantenimiento

< [Anterior: Gestión del ciclo de vida de los nodos](./07-node-lifecycle.md) | [Tabla de contenido](./README.md) | [Siguiente: Configuración del SO en bare metal](./09-bare-metal-os-setup.md) >

> **Referencia de validación**: nodeadm 1.0.20; CRD de Cilium 1.18.3; Prometheus Operator 0.94.1; kube-prometheus-stack 92.9.0; Harbor 2.15.4. Son referencias revisadas, no una matriz universal de versiones compatibles.
> **Última actualización**: 18 de octubre de 2026

Este documento abarca las tareas cotidianas de operación y mantenimiento de los entornos de EKS Hybrid Nodes, incluidas la supervisión, las copias de seguridad y la resolución de problemas.

## Automatización del análisis de vulnerabilidades de Harbor

Usa el programador integrado de Harbor para analizarlo todo en lugar de recurrir a un CronJob que almacene una contraseña de administrador y enumere únicamente la etiqueta más reciente. En la interfaz de usuario de administración del sistema, abre **Administration → Interrogation Services → Vulnerability → Schedule to scan all**. Se admiten programaciones por hora, diarias, semanales y personalizadas; en la interfaz documentada, «Diario» significa a medianoche. Para una ventana de mantenimiento a las 02:00, verifica la sintaxis de la programación personalizada, la zona horaria y la próxima ejecución de la versión desplegada.

Harbor 2.15.4 expone `GET/POST/PUT /api/v2.0/system/scanAll/schedule`. Usa la interfaz de usuario o una integración de API aprobada con validación de una CA de confianza, credenciales protegidas y los permisos necesarios a nivel de sistema. Los permisos de robot de un proyecto no implican autoridad para configurar análisis globales. No incluyas una contraseña de administrador en las variables de entorno ni en los argumentos de comandos de un Pod, y no desactives la verificación de TLS.

Registra la disponibilidad del escáner, la vigencia de la base de datos de vulnerabilidades, la finalización efectiva de los análisis y los errores. El envío de una solicitud o una respuesta de API vacía no constituye una evaluación de vulnerabilidades satisfactoria. Los artefactos no compatibles necesitan un tratamiento aparte, y los análisis globales consumen recursos. La automatización de artefactos seleccionados debe enumerar todas las páginas y los resúmenes criptográficos necesarios, codificar correctamente las rutas de los repositorios y comprobar cada respuesta; un bucle que solo cubra la etiqueta más reciente no abarca el registro.

Consulta la [guía de Harbor](../container-registry/03-harbor.md) y el [procedimiento oficial de programación](https://github.com/goharbor/website/blob/main/docs/administration/vulnerability-scanning/schedule-scans.md).

## Procedimiento de copia de seguridad de la base de datos

Define el objetivo de recuperación y el inventario antes de copiar los datos. Para recuperar Harbor se necesitan metadatos de base de datos compatibles, blobs del registro o almacenamiento de objetos, configuración y secretos/llaves de cifrado protegidos. Un volcado de PostgreSQL por sí solo no es una copia de seguridad completa. Las versiones modernas de Harbor ya no incluyen Notary v1; no des por hecho que existen las bases de datos notarysigner/notaryserver.

El [procedimiento oficial de Harbor Velero](https://github.com/goharbor/website/blob/main/docs/administration/backup-restore/_index.md) utiliza un modo de solo lectura del repositorio y recursos de Kubernetes/PV seleccionados. Su copia de seguridad es **consistente ante fallos, no consistente a nivel de aplicación**, excluye Redis, puede perder metadatos/sesiones no sincronizados y puede dejar tareas que necesiten reparación. Abarca la base de datos interna, no una base de datos externa administrada. Selecciona complementos compatibles para instantáneas, copias de archivos o movimiento de datos, y verifica que el sitio de recuperación pueda acceder a todos los datos necesarios de volúmenes/objetos; una referencia a una instantánea no es necesariamente una copia portátil.

Lo siguiente es solo un **ejemplo de volcado del componente de base de datos** para el Pod verificado de PostgreSQL interno, con pg_dump/pg_restore y autenticación local ya configurados. Las bases de datos externas usan su propio proceso autenticado de copia de seguridad/restauración. Las credenciales no se pasan en los argumentos de los comandos. Detente si se producen errores y mantén privada cualquier salida parcial; no la publiques como un volcado completado.

```bash
set -euo pipefail
umask 077
: "${KUBE_CONTEXT:?Set the approved cluster context}"
: "${HARBOR_NAMESPACE:?Set the Harbor namespace}"
: "${HARBOR_DB_POD:?Set the verified internal PostgreSQL Pod}"
: "${HARBOR_DB_USER:?Set the approved backup database user}"
: "${HARBOR_DB_NAME:?Set the actual Harbor database name}"
: "${PRIVATE_BACKUP_ROOT:?Set an existing protected durable directory}"
BACKUP_DIR=$(mktemp -d "$PRIVATE_BACKUP_ROOT/harbor-db.XXXXXX")
kubectl --context "$KUBE_CONTEXT" -n "$HARBOR_NAMESPACE" exec "$HARBOR_DB_POD" -- \
  pg_dump --format=custom --username "$HARBOR_DB_USER" --dbname "$HARBOR_DB_NAME" \
  > "$BACKUP_DIR/registry.dump.partial"
test -s "$BACKUP_DIR/registry.dump.partial"
kubectl --context "$KUBE_CONTEXT" -n "$HARBOR_NAMESPACE" exec -i "$HARBOR_DB_POD" -- \
  pg_restore --list < "$BACKUP_DIR/registry.dump.partial" > "$BACKUP_DIR/archive-toc.private.txt"
mv "$BACKUP_DIR/registry.dump.partial" "$BACKUP_DIR/registry.dump"
printf 'Database archive created: %s; full Harbor recovery requires separate evidence.\n' "$BACKUP_DIR"
```

La lista del archivo no demuestra que la restauración se haya realizado correctamente. Prueba la restauración con versiones compatibles de PostgreSQL/Harbor y valida la descarga de artefactos, los metadatos, los permisos y las integraciones. Protege y comprueba el inventario completo de la copia de seguridad, y coordina el modo de solo lectura, los trabajos y la actividad de carga/recolección de basura (GC). No desactives automáticamente el modo de solo lectura tras una operación fallida sin evaluar su estado.

BGSAVE de Redis es asíncrono; copiar dump.rdb inmediatamente puede capturar una generación anterior. Si un diseño independiente incluye persistencia de Redis, verifica con su operador que se haya completado y comprueba su estado y generación. No mezcles silenciosamente ese diseño personalizado con el tutorial oficial, que excluye Redis. No se ejecutó ninguna copia de seguridad ni restauración para este capítulo.

## Recopilación de métricas con Prometheus

Mantén separadas las métricas del host, de kubelet/contenedores y de GPU. `node_cpu_seconds_total` y `node_memory_*` provienen de Node Exporter, no de un endpoint de kubelet. Usa un perfil de Node Exporter/DCGM instalado y revisado, y verifica los montajes reales del host, los privilegios, la ubicación de los nodos y la disponibilidad de las métricas. Container Insights no proporciona métricas de nivel de host para Hybrid a través de EC2 IMDS.

El siguiente ejemplo de descubrimiento usa las etiquetas/puerto del Service de Node Exporter de kube-prometheus-stack 92.9.0, con el release `kube-prom` en `monitoring`. La parte de DCGM presupone Pods verificados etiquetados con `app: nvidia-dcgm-exporter` en `gpu-operator`, con un puerto de contenedor llamado `metrics`; ajústala al exportador instalado. Ninguno de estos recursos instala un exportador. Haz coincidir los selectores de monitores/espacios de nombres del recurso Prometheus y evita recopilar dos veces métricas del mismo exportador mediante un monitor existente.

`attachMetadata.node` hace que estén disponibles los metadatos de descubrimiento de Node; no copia automáticamente las etiquetas a las métricas. Requiere Prometheus >=2.37 para ServiceMonitor o >=2.35 para PodMonitor, y permisos `list`/`watch` sobre Node para Prometheus. La nueva asignación de etiquetas conserva los nodos que realmente tienen `eks.amazonaws.com/compute-type=hybrid` y crea etiquetas de destino estables `node`/`compute_type`. No deduzcas la ubicación Hybrid a partir del prefijo del nombre de un Node de SSM.

Estos ejemplos usan los endpoints HTTP protegidos de métricas de los exportadores, no el endpoint HTTPS de kubelet. Restringe la conectividad con los colectores. Si el tráfico atraviesa un límite no confiable, configura TLS/autenticación para el exportador o un proxy revisado, junto con la CA y los ajustes de autorización correspondientes; no uses `insecureSkipVerify`. Mantén la recopilación de métricas de kubelet en su configuración separada, con autenticación y verificación de CA.

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: hybrid-node-exporter
  namespace: monitoring
  labels:
    release: kube-prom
spec:
  attachMetadata:
    node: true
  selector:
    matchLabels:
      app.kubernetes.io/name: prometheus-node-exporter
      app.kubernetes.io/instance: kube-prom
  namespaceSelector:
    matchNames: [monitoring]
  endpoints:
  - port: http-metrics
    interval: 30s
    relabelings:
    - sourceLabels: [__meta_kubernetes_node_label_eks_amazonaws_com_compute_type]
      regex: hybrid
      action: keep
    - sourceLabels: [__meta_kubernetes_pod_node_name]
      targetLabel: node
    - targetLabel: compute_type
      replacement: hybrid
---
apiVersion: monitoring.coreos.com/v1
kind: PodMonitor
metadata:
  name: hybrid-gpu-metrics
  namespace: monitoring
  labels:
    release: kube-prom
spec:
  attachMetadata:
    node: true
  selector:
    matchLabels:
      app: nvidia-dcgm-exporter
  namespaceSelector:
    matchNames: [gpu-operator]
  podMetricsEndpoints:
  - port: metrics
    interval: 30s
    relabelings:
    - sourceLabels: [__meta_kubernetes_node_label_eks_amazonaws_com_compute_type]
      regex: hybrid
      action: keep
    - sourceLabels: [__meta_kubernetes_pod_node_name]
      targetLabel: node
    - targetLabel: compute_type
      replacement: hybrid
```

### Ejemplos de consultas para paneles de Grafana

Estas consultas requieren las etiquetas de destino anteriores y métricas de exportadores compatibles. Verifica las unidades, la identidad de GPU/MIG, los valores centinela de error/no compatibles, las recopilaciones que falten y las series duplicadas. El uso de memoria framebuffer de GPU se calcula dividiendo por la capacidad total (`used + free`), no por la capacidad libre; se excluyen las series con capacidad cero. Las consultas son expresiones que se pueden probar localmente, no mediciones de este entorno.

```promql
# Host CPU utilization percent
100 * (1 - avg by (node) (rate(node_cpu_seconds_total{mode="idle",compute_type="hybrid"}[5m])))

# Host memory utilization percent
100 * (1 - node_memory_MemAvailable_bytes{compute_type="hybrid"} / node_memory_MemTotal_bytes{compute_type="hybrid"})

# GPU utilization: this metric is already a percentage
DCGM_FI_DEV_GPU_UTIL{compute_type="hybrid"}

# GPU framebuffer usage: used / (used + free), excluding zero capacity
(100 * DCGM_FI_DEV_FB_USED{compute_type="hybrid"} /
 (DCGM_FI_DEV_FB_USED{compute_type="hybrid"} + DCGM_FI_DEV_FB_FREE{compute_type="hybrid"}))
and
((DCGM_FI_DEV_FB_USED{compute_type="hybrid"} + DCGM_FI_DEV_FB_FREE{compute_type="hybrid"}) > 0)
```

## Validación del rendimiento de Direct Connect

Distingue un plan de pruebas de una garantía del servicio de AWS. Los ejemplos anteriores de RTT <5ms, variación <2ms, pérdida <0.01% y rendimiento >1Gbps son objetivos ilustrativos para la planificación, no resultados medidos ni promesas universales de Direct Connect. Elige objetivos adecuados para la ubicación, el circuito, el endpoint, la carga de trabajo y la capacidad contratada reales; confirma que la ruta medida utiliza Direct Connect, no una VPN u otra ruta.

`ping` informa el RTT de ICMP y, en Linux iputils, el mdev del RTT. Esa dispersión no es la misma estadística que la variación del retardo unidireccional ni que el jitter UDP de iperf3. El filtrado o la priorización reducida de ICMP pueden diferir del tráfico de la aplicación. Una prueba de 1.000 paquetes tiene incrementos de pérdida del 0,1%; observar cero pérdidas no demuestra que la tasa de pérdida a largo plazo sea inferior al 0,01%.

Usa un servidor de pruebas privado aprobado con iperf3 ya en ejecución, una ventana coordinada, un límite de tráfico deliberado y almacenamiento protegido de los resultados. No ejecutes iperf3 contra un endpoint de la API de EKS. El siguiente ejemplo acotado requiere Bash, Python3, ping de iputils, GNU timeout e iperf3 con las opciones indicadas. Si hay un error, la secuencia se detiene; la ausencia de herramientas, un JSON no válido o un error de iperf3 no constituyen una prueba de rendimiento aprobada.

```bash
set -euo pipefail
umask 077
: "${PROBE_HOST:?Set the approved private test host}"
: "${TEST_BITRATE:?Set an approved traffic cap, for example 10M}"
: "${PRIVATE_RESULTS_ROOT:?Set an existing protected results directory}"
if [[ ! "$TEST_BITRATE" =~ ^[1-9][0-9]*[KMGT]?$ ]]; then
  printf 'TEST_BITRATE must be a positive integer with an optional K/M/G/T suffix.\n' >&2
  exit 2
fi
RUN_DIR=$(mktemp -d "$PRIVATE_RESULTS_ROOT/dx-check.XXXXXX")
date -u +%FT%TZ > "$RUN_DIR/started-at.txt"
LC_ALL=C ping -n -c 100 -W 2 "$PROBE_HOST" > "$RUN_DIR/ping.txt"
timeout 45s iperf3 --client "$PROBE_HOST" --connect-timeout 3000 \
  --time 10 --bitrate "$TEST_BITRATE" --json > "$RUN_DIR/iperf-tcp.json"
python3 - "$RUN_DIR/iperf-tcp.json" <<'PY'
import json, math, sys
with open(sys.argv[1]) as stream:
    result = json.load(stream)
if result.get("error") or not isinstance(result.get("end"), dict):
    raise SystemExit("iperf3 result is incomplete or reports an error")
received = result["end"].get("sum_received", {})
for field in ("bits_per_second", "bytes", "seconds"):
    value = received.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise SystemExit("Missing or invalid TCP receiver statistics")
if received["seconds"] <= 0:
    raise SystemExit("Invalid TCP test duration")
print("Saved a completed iperf3 result; compare receiver statistics with the approved test plan.")
PY
printf 'Private observations: %s; this does not establish an AWS latency/throughput guarantee.\n' "$RUN_DIR"
```

Esta prueba TCP con límite no determina la capacidad máxima del enlace. Examina el rendimiento en el receptor, las retransmisiones, la dirección, la duración y la congestión. Para una prueba UDP aprobada por separado, usa `--udp` y una tasa de bits explícita; luego conserva e interpreta la pérdida/jitter del receptor en el JSON de esa versión. Registra las pruebas fallidas/omitidas como tales. Durante esta auditoría no se ejecutó ninguna prueba de carga de red.

## Gestión de la renovación de certificados

Identifica qué certificado se está comprobando: el certificado TLS del servidor Harbor, su cadena de CA, un certificado de servicio de kubelet, la CA del plano de control de EKS o el certificado del host de IAM Roles Anywhere. Un certificado de CA válido no demuestra que el certificado hoja del servidor sea válido, y un heartbeat Node Ready no es evidencia de vencimiento del certificado. AWS administra los certificados del plano de control de EKS; no ejecutes comandos de renovación de kubeadm como procedimiento de reparación de EKS.

Esta comprobación local del vencimiento falla si falta el certificado, no se puede leer, no es válido o vence dentro del plazo de advertencia de ejemplo de 30 días. No valida la cadena, el nombre de host, la revocación ni si el servicio presenta realmente ese certificado. Usa la conexión TLS verificada que aparece a continuación para el endpoint publicado y el [procedimiento del ciclo de vida de las credenciales](./07-node-lifecycle.md) para renovar el certificado del host.

```bash
set -euo pipefail
: "${CERT_PATH:?Set the actual certificate file to inspect}"
test -r "$CERT_PATH"
openssl x509 -in "$CERT_PATH" -checkend 2592000 -noout
```

Registra el emisor/responsable real, la ruta del certificado configurado, el vencimiento y la entrega de alertas. Las rutas de las credenciales de servicio/cliente de kubelet dependen de la configuración; habilitar solo serverTLSBootstrap no aprueba las CSR de servicio ni renueva un certificado de IAM Roles Anywhere.

## Configuración de Ingress

### Ingress de ALB (modo de destino ip)

El AWS Load Balancer Controller autoadministrado puede registrar IP de Pod de Hybrid enrutables mediante `alb.ingress.kubernetes.io/target-type: ip`. Las rutas, el tráfico de retorno, los grupos de seguridad/cortafuegos y la configuración de la red remota de Pod de EKS deben ser coherentes.

La receta del webhook de AWS para el modo mixto coloca el controlador en nodos de la nube. Es una recomendación de ubicación para ese diseño, no una afirmación de que sea imposible ejecutar un webhook en Hybrid Nodes: la guía del complemento permite ubicarlo en Hybrid cuando el plano de control puede llegar al CIDR de Pod remoto configurado. Es preferible usar etiquetas de ubicación administrativas positivas a `compute-type NotIn [hybrid]`, que también coincide con nodos que no tienen esa etiqueta. La etiqueta del ejemplo siguiente solo debe asignarse a nodos de la nube cuya elegibilidad se haya verificado.

```yaml
# Fragment under the controller Deployment's spec.template.spec:
nodeSelector:
  infrastructure.example.com/location: aws
```

### Cilium Ingress Controller

Los ejemplos de Cilium Ingress y Gateway API de esta sección requieren una configuración de Cilium con L7 habilitado. No se aplican a la misma instalación de Cilium configurada para [EKS Hybrid Nodes Gateway](./10-hybrid-nodes-gateway.md): su [configuración VTEP requerida por AWS](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-gateway-cni.html) establece `vtep.enabled=true` y `l7Proxy=false`. Elige el diseño de red antes de habilitar estas funciones. Esta restricción afecta a las funciones de proxy L7 de Cilium; no impide que las aplicaciones HTTP utilicen la ruta de red enrutada del gateway.

Los requisitos previos de Ingress de Cilium 1.18.3 upstream incluyen compatibilidad con NodePort (o sustitución de kube-proxy), compatibilidad con proxy L7 y una ruta disponible de exposición mediante balanceador de carga. El fragmento siguiente no autoriza a cambiar la CNI de los nodos de la nube en un clúster mixto. Conserva la configuración revisada de Cilium para Hybrid y confirma los límites de compatibilidad de AWS para las funciones adicionales. Cambiar entre modo dedicado y compartido puede modificar direcciones e interrumpir conexiones existentes.

```yaml
# Merge into the reviewed Cilium release values, not a full installation:
nodePort:
  enabled: true
l7Proxy: true
ingressController:
  enabled: true
  loadbalancerMode: dedicated
```

### Cilium Gateway API

Instala las CRD de Gateway API y las versiones de recursos compatibles con el release del controlador elegido, verifica sus requisitos previos de NodePort/sustitución de kube-proxy y L7, y comprueba las condiciones de GatewayClass/Gateway/Route. Establecer una sola opción de Helm no instala esas CRD ni garantiza la accesibilidad externa.

```yaml
# Required Gateway API CRDs and controller prerequisites must already be met:
gatewayAPI:
  enabled: true
```

### LoadBalancer IPAM (Cilium)

El siguiente pool usa la API `cilium.io/v2`, verificada con la CRD 1.18.3, y selecciona únicamente Services etiquetados de forma explícita. Sustituye el CIDR ilustrativo por un rango de direcciones reservado y no superpuesto del inventario de red. La asignación de IP no anuncia la dirección a los routers ni garantiza una ruta de datos funcional.

```yaml
apiVersion: cilium.io/v2
kind: CiliumLoadBalancerIPPool
metadata:
  name: on-prem-pool
spec:
  blocks:
  - cidr: "10.80.100.0/24"
  serviceSelector:
    matchLabels:
      exposure: onprem-bgp
```

## Balanceo de carga

### NLB (modo de destino ip)

Para AWS Load Balancer Controller autoadministrado, usa un Service `LoadBalancer` bajo su control con `spec.loadBalancerClass: service.k8s.aws/nlb` y `service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip`, o la ruta de control documentada `aws-load-balancer-type: external` para el controlador elegido. Una anotación de tipo de destino por sí sola no selecciona el controlador. Los destinos de Pod de Hybrid y las rutas de retorno deben ser accesibles desde AWS; elige deliberadamente la exposición interna/pública, las subredes y los controles de acceso.

Esta no es una receta de control de EKS Auto Mode. No cambies la clase/controlador de un Service existente como migración en el mismo lugar sin revisar los efectos de sustitución y tráfico.

### Cilium LB + BGP

Usa los esquemas `cilium.io/v2` instalados. Los tipos de dirección del Service deben estar en `advertisements[].service.addresses`. El ejemplo anuncia únicamente las IP de LoadBalancer de los Services etiquetados con `exposure: onprem-bgp`; no utiliza un selector `NotIn` que, en la práctica, seleccione todos los Services.

```yaml
apiVersion: cilium.io/v2
kind: CiliumBGPAdvertisement
metadata:
  name: hybrid-service-advertisement
  labels:
    advertise: hybrid-services
spec:
  advertisements:
  - advertisementType: Service
    service:
      addresses: [LoadBalancerIP]
    selector:
      matchLabels:
        exposure: onprem-bgp
```

Configura la selección de nodos/peers de CiliumBGPClusterConfig y las familias de CiliumBGPPeerConfig. El selector de anuncios de la configuración de peers debe coincidir con `advertise: hybrid-services`; el selector de Service debe coincidir con las etiquetas reales del Service. Habilita el plano de control BGP revisado, establece sesiones con los routers y valida las rutas aceptadas, los siguientes saltos, las rutas de retorno y la política de tráfico. Un IPPool/Advertisement por sí solo no es suficiente. Consulta la [base de redes](./02-network-configuration.md) y la documentación BGP de la versión instalada antes de aplicar cambios.

## Configuración detallada de complementos

### Agente de observabilidad de CloudWatch

Usa la configuración compatible de Pod Identity y verifica la asociación y los permisos IAM reales de la carga de trabajo. La variable de compatibilidad `RUN_WITH_IRSA` para Hybrid sigue siendo necesaria según el procedimiento actual de AWS, pese a su nombre. Añádela a la **lista spec.env** del recurso existente `AmazonCloudWatchAgent`, conservando entradas como `K8S_NODE_NAME`; no es un campo `env` arbitrario de nivel superior en configurationValues del complemento de EKS.

```yaml
# Add this item to the existing AmazonCloudWatchAgent.spec.env list:
- name: RUN_WITH_IRSA
  value: "True"
```

Inspecciona `amazoncloudwatchagents/cloudwatch-agent` en el espacio de nombres `amazon-cloudwatch` antes de editarlo y revisa cómo el complemento/operador reconcilia esa configuración. Después, confirma el despliegue gradual del agente y la recopilación. Las métricas de clúster/carga de trabajo/Pod/contenedor de Hybrid están disponibles, pero no lo están las métricas de Container Insights de nivel de nodo, porque no se cuenta con la dependencia de EC2 IMDS. Si el operador se ejecuta en Hybrid Nodes, garantiza la conectividad del webhook con el plano de control.

### EKS Pod Identity Agent

| SO del host | Mínimo documentado | DaemonSet de Hybrid / ruta de credenciales |
| --- | --- | --- |
| Ubuntu, RHEL, AL2023 | Complemento 1.3.3-eksbuild.1 | `hybrid`; `/eks-hybrid/.aws/credentials` |
| Bottlerocket (variantes compatibles de VMware) | Complemento 1.3.7-eksbuild.2 y SO 1.39.0 | `hybrid-bottlerocket`; `/var/eks-hybrid/.aws/credentials` |

Estas son versiones mínimas para la función, no una recomendación para instalar una versión antigua. Elige una versión del complemento actualmente compatible y revisa su esquema de configuración. En Ubuntu/RHEL/AL2023, combina este fragmento con el NodeConfig completo existente de cada host:

```yaml
# Merge this fragment into each host's complete, protected NodeConfig:
spec:
  hybrid:
    enableCredentialsFile: true
```

AWS requiere una reconciliación planificada de `nodeadm init -c file:///path/to/nodeconfig.yaml` en cada host afectado, incluidos los nodos que ya se hayan unido. No vuelvas a inicializar a ciegas todos los nodos de producción: conserva la identidad/configuración, sigue el procedimiento del ciclo de vida y valida un host a la vez. Bottlerocket utiliza la ruta de configuración documentada, no este fragmento de nodeadm. Estos archivos temporales de credenciales son sensibles; no los muestres.

Para el DaemonSet de Hybrid que no es Bottlerocket, la configuración del complemento incluye lo siguiente:

```json
{
  "daemonsets": {
    "hybrid": {
      "create": true
    }
  }
}
```

Para Bottlerocket, usa la configuración documentada `hybrid-bottlerocket` para la versión seleccionada. Inspecciona y combina los ajustes existentes. Crea un complemento solo si no existe; actualiza uno existente con una gestión de conflictos revisada, en lugar de usar create u OVERWRITE a ciegas. El agente y el archivo de credenciales no crean la asociación de Pod Identity de cada aplicación: verifica el espacio de nombres, el ServiceAccount, la confianza/permisos del rol IAM, la resolución de credenciales del SDK y la autorización correcta.

## Operaciones de webhooks en modo mixto

En el patrón de modo mixto compatible con AWS, VPC CNI se ejecuta en nodos de la nube y Cilium/Calico en Hybrid Nodes. AWS recomienda ubicar los webhooks en la nube en ese patrón. Un webhook alojado en Hybrid también necesita un CIDR de Pod remoto enrutable y conectividad con el plano de control; inspecciona el endpoint real en vez de dar por hecho que todos los webhooks deben o pueden ejecutarse en cualquier lugar.

### Ubicación de CoreDNS

AWS recomienda al menos una réplica de CoreDNS en nodos de la nube y otra en Hybrid Nodes para este diseño de modo mixto. Verifica que haya al menos dos réplicas deseadas, capacidad apta, selectores, tolerancias y endpoints reales. `maxSkew: 1` por sí solo no crea dos dominios ni garantiza un Pod por dominio, y es posible que los nodos de la nube no tengan la etiqueta `eks.amazonaws.com/compute-type`.

En clústeres compatibles con `minDomains`, este fragmento de Pod-spec utiliza una etiqueta administrativa explícita de dos dominios. Etiqueta solo los nodos DNS previstos y asigna a cada nodo apto un valor `location` verificado que sea exactamente `aws` u `onprem`. Mantén la compatibilidad con las reglas de afinidad/tolerancias existentes, verifica las etiquetas de los Pods de CoreDNS y reconcilia los cambios mediante el mecanismo de configuración compatible del complemento.

```yaml
# Fragment under CoreDNS Deployment.spec.template.spec.
# Label eligible nodes with exactly aws or onprem in this administrative domain.
nodeSelector:
  infrastructure.example.com/dns-eligible: "true"
topologySpreadConstraints:
- maxSkew: 1
  minDomains: 2
  topologyKey: infrastructure.example.com/location
  whenUnsatisfiable: DoNotSchedule
  labelSelector:
    matchLabels:
      k8s-app: kube-dns
```

Con dos dominios aptos y al menos dos réplicas, la distribución estricta limita la programación entre ellos. Si un dominio no tiene capacidad, las réplicas nuevas pueden permanecer en estado Pending; es una concesión en materia de disponibilidad, no una conmutación por error garantizada. Prueba el Service/EndpointSlices de DNS reales y la resolución local/remota. En clústeres que contienen Auto Mode, distingue su servicio de DNS del sistema local al nodo del Deployment que sigue siendo necesario para los nodos que no son de Auto Mode.

<span id="per-add-on-nodeaffinity-settings-guide"></span>

### Guía de ubicación por complemento

| Complemento | Ubicación en este diseño | Comprobación necesaria |
| --- | --- | --- |
| AWS Load Balancer Controller | Nodos de la nube en la receta de modo mixto de AWS | Accesibilidad del webhook, etiquetas positivas, destinos IP de Hybrid enrutables |
| Agente/operador de CloudWatch | Agente en los nodos de destino compatibles; preferiblemente, webhooks del operador en la nube | Estado de IAM/agente; se excluyen las métricas de nivel de nodo de Hybrid |
| cert-manager | Preferiblemente, webhook en la nube; también es posible ubicarlo en Hybrid si es enrutable | Acceso al plano de control y red de Pod remota |
| Metrics Server | En la nube o en un endpoint de Pod de Hybrid accesible | Rutas del plano de control al Pod y de Metrics Server a kubelet |
| CoreDNS | Verificar las réplicas en nodos de la nube y Hybrid | Dominios aptos, capacidad y tráfico DNS real |
| Cilium/Calico | Nodos Hybrid en el diseño de CNI mixto compatible con AWS | Mantener VPC CNI en los nodos de la nube |

## Comportamiento y preparación ante interrupciones de red

En esta sección se describe qué sigue funcionando y qué se detiene cuando Direct Connect o VPN se desconecta brevemente o la red deja de responder. Hybrid Nodes no está pensado para entornos DDIL con desconexiones frecuentes y presupone una conexión fiable con AWS (consulta la [descripción general](./README.md)).

### Clúster y cargas de trabajo durante una desconexión

| Área | Comportamiento |
|---|---|
| Pods en ejecución | Siguen ejecutándose en el nodo. Kubelet no puede renovar su Lease, por lo que la condición Ready del Node pasa a ser `Unknown` y se añade el taint `node.kubernetes.io/unreachable` (`NoSchedule` y `NoExecute` cuando se cumplen las condiciones). |
| Conmutación por error de Pods | Los Pods ordinarios reciben una tolerancia predeterminada de 300 segundos para los taints `not-ready` y `unreachable` de tipo NoExecute. Una vez aplicado el taint NoExecute correspondiente y vencida esa tolerancia, el plano de control marca el Pod para su eliminación; un controlador puede crear un reemplazo en un nodo apto. Un Pod que no tenga una tolerancia coincidente se expulsa sin esperar esos 300 segundos. El contenedor original de un nodo inaccesible puede seguir ejecutándose hasta que kubelet se vuelva a conectar. Por defecto, los Pods de DaemonSet toleran estos taints indefinidamente. |
| Etiqueta de zona | Una etiqueta de zona por sí sola no evita la expulsión. Si toda una zona queda inaccesible, pero otra zona aún tiene nodos Ready, las expulsiones pueden continuar. Si no hay nodos Ready en ninguna zona, Kubernetes cancela las expulsiones; también influyen otros umbrales de estado de zona y el tamaño del clúster. Consulta los escenarios de la [guía de conmutación por error de Pods de AWS](https://docs.aws.amazon.com/eks/latest/best-practices/hybrid-nodes-kubernetes-pod-failover.html). Los nodos Hybrid no tienen un cloud-controller-manager, así que configura una zona por centro de datos con nodeadm `--node-labels`. |
| Cilium | El estado del agente está ligado al acceso al plano de control, por lo que el agente sigue reiniciándose durante una desconexión y las sesiones de Cilium BGP Control Plane pueden interrumpirse (CFP #31702, mejora optativa en Cilium 1.17). El modo L2 de MetalLB utilizado en el ejemplo de AWS se mantuvo estable durante las desconexiones. |
| Dependencias de servicios de AWS | Los servicios regionales, como las descargas de imágenes de ECR, CloudWatch y Amazon Managed Service for Prometheus, ALB/NLB, S3 y RDS, no están disponibles durante la desconexión. |
| Resolución local de problemas | No se puede acceder al servidor API, así que usa `crictl pods`, `crictl ps` y `crictl logs <container>` en el host en lugar de `kubectl`. |

### Credenciales y reconexión

| Elemento | Activaciones híbridas de SSM | IAM Roles Anywhere |
|---|---|---|
| Credenciales temporales | Fijadas en una hora (no se puede cambiar). Se renuevan automáticamente antes de vencer, sin afectar a los nodos ni a las aplicaciones durante el funcionamiento normal. | Una hora de forma predeterminada, hasta 12 horas con `durationSeconds` del perfil. `MaxSessionDuration` del rol IAM del nodo debe ser mayor. |
| Durante la desconexión | La renovación falla porque no se puede acceder al endpoint regional de SSM; las credenciales pueden vencer durante una desconexión prolongada. | No se pueden obtener credenciales nuevas sin AWS. |
| Tras restablecerse la conexión | Los reintentos utilizan retroceso exponencial, con un máximo de 30 minutos en SSM agent **3.3.808.0 y versiones posteriores**. **Es posible que los nodos tarden hasta 30 minutos en volver a conectarse después de restablecerse la red**, y los nodos se reconectan en distintos momentos, por lo que los Pods pueden pasar a nodos que se hayan reconectado antes. | Kubelet obtiene credenciales a petición mediante `aws_signing_helper credential-process`, por lo que la reconexión suele producirse **en cuestión de segundos**. |
| Recuperación más rápida | Reinicia el SSM agent para forzar una renovación (comandos siguientes). | No es necesario hacer nada mientras el certificado sea válido. Configura notificaciones de vencimiento del certificado. |

Versión, reinicio y registros de SSM agent:

```bash
# Version (AL2023, RHEL / Ubuntu)
yum info amazon-ssm-agent
snap list amazon-ssm-agent

# Force a credential refresh after the network is restored
systemctl restart amazon-ssm-agent                          # AL2023, RHEL
systemctl restart snap.amazon-ssm-agent.amazon-ssm-agent    # Ubuntu

# Watch the CredentialRefresher lines
tail -f /var/log/amazon/ssm/amazon-ssm-agent.log
```

Durante una desconexión, el registro repite `Retrieve credentials produced error: RequestError: send request failed` y `Sleeping for ... before retrying retrieve credentials`; cuando la renovación se realiza correctamente, se registra `Credentials ready`.

### Lista de preparación

- **Conectividad redundante:** implementa redundancia para Direct Connect o mantén una VPN de Site-to-Site como respaldo.
- **Detectar desconexiones:** habilita los registros de Controller Manager del plano de control de EKS y crea un filtro de métricas y una alarma de CloudWatch para el mensaje `Recording status change event message for node` con `status="NodeNotReady"`. Activa una alarma cuando `BytesIn`/`BytesOut` de TGW o `TunnelDataIn`/`TunnelDataOut` de VGW caigan por debajo de lo normal. CloudWatch Network Monitor muestra la pérdida y la latencia.
- **Versión de SSM agent:** mantén la versión 3.3.808.0 o posterior para limitar el intervalo de reintento a 30 minutos.
- **Etiqueta de zona:** configura un `topology.kubernetes.io/zone` por centro de datos.
- **Ajustar la expulsión:** para aplicaciones difíciles de trasladar, aumenta `tolerationSeconds`. Los valores más altos también retrasan la retirada de Pods de nodos que realmente han fallado.

```yaml
# Fragment under the Deployment's spec.template.spec
tolerations:
  - key: "node.kubernetes.io/unreachable"
    operator: "Exists"
    effect: "NoExecute"
    tolerationSeconds: 1800
```

- **Proveedor de credenciales:** si las desconexiones son frecuentes y es importante reconectarse rápidamente, considera IAM Roles Anywhere con un `durationSeconds` más largo. Usa un único proveedor en cada clúster.
- **Ruta secundaria de observabilidad:** configura el colector ADOT para enviar datos a varios backends y así mantener la visibilidad cuando los servicios regionales no estén accesibles.

Referencias:
- [Credenciales del host durante las desconexiones de red](https://docs.aws.amazon.com/eks/latest/best-practices/hybrid-nodes-host-creds.html)
- [Prácticas recomendadas de estabilidad durante las desconexiones de red](https://docs.aws.amazon.com/eks/latest/best-practices/hybrid-nodes-network-disconnection-best-practices.html)
- [Conmutación por error de Pods de Kubernetes durante las desconexiones de red](https://docs.aws.amazon.com/eks/latest/best-practices/hybrid-nodes-kubernetes-pod-failover.html)

## Resolución de problemas comunes

### Diagnóstico de ImagePullBackOff

Lee los eventos del Pod e inspecciona el nombre/tipo del Secret mencionado sin descodificar ni mostrar las credenciales del registro. El Secret debe estar en el espacio de nombres del Pod. Confirma el nombre de host del registro, los permisos necesarios del repositorio y el vencimiento de las credenciales con el responsable de estas; los metadatos por sí solos no demuestran que la autenticación funcione.

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?Set the approved cluster context}"
: "${NAMESPACE:?Set the workload namespace}" "${POD:?Set the affected Pod}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" describe pod "$POD"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pod "$POD" \
  -o jsonpath='{.spec.imagePullSecrets[*].name}{"\n"}'
: "${PULL_SECRET:?Set a referenced imagePullSecret in that namespace}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get secret "$PULL_SECRET" \
  -o jsonpath='{.type}{"\n"}'
```

Ejecuta una comprobación de TLS desde la ruta real del host/red, con la CA de confianza y la verificación del nombre de host habilitadas. No uses curl -k ni interpretes una respuesta 401 de un registro sin autenticar como un fallo de TLS. Este ejemplo requiere Bash, OpenSSL y GNU timeout.

```bash
set -euo pipefail
: "${HARBOR_HOST:?Set the registry DNS name, without scheme or port}"
: "${HARBOR_CA_FILE:?Set the approved CA bundle file}"
timeout 10s openssl s_client -connect "$HARBOR_HOST:443" \
  -servername "$HARBOR_HOST" -verify_hostname "$HARBOR_HOST" \
  -verify_return_error -CAfile "$HARBOR_CA_FILE" </dev/null
```

Para probar DNS/red dentro de un Pod, usa una imagen de diagnóstico aprobada fijada por resumen criptográfico, un espacio de nombres dedicado y una ubicación explícita en el Hybrid Node afectado. Un Pod de depuración cualquiera sin fijar puede ejecutarse en un nodo de la nube y probar la ruta equivocada. Revisa por separado la creación/eliminación del Pod y conserva los resultados acotados.

### Problemas de resolución DNS

Inspecciona el Deployment/Pods de CoreDNS reales, el Service y los EndpointSlices, su ubicación en la nube/local y la configuración DNS y accesibilidad de red. Prueba el nombre del registro y kubernetes.default.svc.cluster.local desde el entorno de la carga de trabajo afectada. Los fallos de acceso a la API, al DNS o a los registros son observaciones desconocidas, no comprobaciones satisfactorias.

No reinicies todos los Pods de CoreDNS como medida de diagnóstico predeterminada. Determina primero qué capa falla y coordina cualquier reinicio con las comprobaciones de redundancia y recuperación. Los clústeres mixtos con Auto Mode pueden tener comportamiento de DNS local al nodo; identifica qué ruta de resolución utiliza realmente el Pod que falla.

### Problemas de conectividad de nodos

Usa el nombre real del Node del inventario y el host asociado. Los nombres de Node respaldados por SSM no tienen por qué empezar por hybrid- ni resolverse como nombres de host.

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?Set the approved cluster context}" "${NODE:?Set the actual registered Node name}"
kubectl --context "$KUBE_CONTEXT" get node "$NODE" -o wide
kubectl --context "$KUBE_CONTEXT" describe node "$NODE"
```

```bash
# Run on the mapped host, not a hostname guessed from the Node name.
sudo systemctl status kubelet containerd --no-pager
sudo journalctl -u kubelet -u containerd --since '10 minutes ago' \
  --no-pager -n 200
```

Comprueba el proveedor de credenciales y la unidad del agente específica del SO (incluida la instalación de SSM basada en snap de Ubuntu cuando corresponda). Para diagnosticar la red/autenticación, sigue el procedimiento verificado `nodeadm debug -c file:///etc/eks/nodeconfig.yaml` con privilegios de root y conserva la salida de forma privada. Se conecta a AWS y al clúster; no registres las credenciales emitidas ni desactives la verificación de TLS.

No existe el subcomando `nodeadm reset` en la CLI revisada 1.0.20. NotReady no es motivo para dar de baja y volver a inicializar un host a ciegas. Sigue el procedimiento de [recuperación y reconciliación de identidad](./07-node-lifecycle.md) después de determinar el fallo, conservando los montajes/datos y registrando las identidades del nodo/SSM.

## Alcance de la validación y referencias

Las comprobaciones locales abarcan esquemas de recursos fijados, cuatro expresiones PromQL con muestras sintéticas y once casos con dobles de comandos para copias de seguridad/red. No se ejecutaron cambios en AWS/Kubernetes, copias de seguridad/restauraciones reales, pruebas de carga de red, sesiones BGP, recopilaciones de exportadores ni despliegues en producción. Antes del despliegue, selecciona combinaciones de EKS/SO/CNI/complementos conforme a la documentación de compatibilidad vigente de AWS.

- [Complementos de AWS Hybrid](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-add-ons.html)
- [Webhooks de AWS Hybrid](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-webhooks.html)
- [Actualizaciones de AWS Hybrid](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-upgrade.html)
- [API de Prometheus Operator](https://prometheus-operator.dev/docs/api-reference/api/)
- [Requisitos previos de Cilium 1.18.3 Ingress](https://github.com/cilium/cilium/blob/v1.18.3/Documentation/network/servicemesh/ingress.rst)
- [CRD de Cilium 1.18.3 LoadBalancer IPPool](https://github.com/cilium/cilium/blob/v1.18.3/pkg/k8s/apis/cilium.io/client/crds/v2/ciliumloadbalancerippools.yaml)
- [Invocación de iperf3](https://software.es.net/iperf/invoking.html)
- [Tolerancias de taints de Kubernetes](https://kubernetes.io/docs/concepts/scheduling-eviction/taint-and-toleration/)


---

< [Anterior: Gestión del ciclo de vida de los nodos](./07-node-lifecycle.md) | [Tabla de contenido](./README.md) | [Siguiente: Configuración del SO en bare metal](./09-bare-metal-os-setup.md) >
