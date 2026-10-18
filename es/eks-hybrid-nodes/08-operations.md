# Operaciones y mantenimiento

< [Anterior: Administración del ciclo de vida de los nodos](./07-node-lifecycle.md) | [Tabla de contenido](./README.md) | [Siguiente: Configuración del sistema operativo en bare metal](./09-bare-metal-os-setup.md) >

> **Base de validación**: nodeadm 1.0.20; CRD de Cilium 1.18.3; Prometheus Operator 0.94.1; kube-prometheus-stack 92.9.0; Harbor 2.15.4. Son referencias revisadas, no una matriz universal de versiones compatibles.
> **Última actualización**: October 18, 2026

Este documento abarca las tareas diarias de operaciones y mantenimiento de entornos de EKS Hybrid Nodes, incluidas la supervisión, las copias de seguridad y la resolución de problemas.

## Automatización del análisis de vulnerabilidades de Harbor

Use el programador integrado de Harbor para analizar todo, en lugar de un CronJob que contenga una contraseña de administrador y enumere solo la etiqueta más reciente. En la interfaz de usuario del administrador del sistema, abra **Administration → Interrogation Services → Vulnerability → Schedule to scan all**. Se admiten programaciones por hora, diarias, semanales y personalizadas; en la interfaz documentada, «Diaria» significa a medianoche. Para una ventana de mantenimiento a las 02:00, verifique la sintaxis de la programación personalizada, la zona horaria y la próxima ejecución para la versión implementada.

Harbor 2.15.4 expone GET/POST/PUT `/api/v2.0/system/scanAll/schedule`. Use la interfaz de usuario o una integración de API aprobada con validación de una CA de confianza, credenciales protegidas y los permisos requeridos a nivel del sistema. Los permisos de robot de un proyecto no otorgan autoridad para configurar análisis globales. No coloque una contraseña de administrador en los argumentos del comando o el entorno de un Pod, ni desactive la verificación de TLS.

Registre la disponibilidad del escáner, la actualidad de la base de datos de vulnerabilidades, la finalización real de los análisis y los errores. El envío de una solicitud o una respuesta vacía de la API no constituyen una evaluación de vulnerabilidades satisfactoria. Los artefactos no compatibles requieren un tratamiento aparte, y los análisis globales consumen recursos. La automatización de artefactos seleccionados debe enumerar todas las páginas y los resúmenes criptográficos requeridos, codificar correctamente las rutas de los repositorios y comprobar cada respuesta; un bucle que solo abarque la etiqueta más reciente no cubre el registro.

Consulte la [guía de Harbor](../container-registry/03-harbor.md) y el [procedimiento oficial de programación](https://github.com/goharbor/website/blob/main/docs/administration/vulnerability-scanning/schedule-scans.md).

## Procedimiento de copia de seguridad de la base de datos

Defina el objetivo de recuperación y haga un inventario antes de copiar los datos. La recuperación de Harbor requiere metadatos de base de datos compatibles, blobs del registro/almacenamiento de objetos, configuración y secretos/claves de cifrado protegidos. Un volcado de PostgreSQL por sí solo no es una copia de seguridad completa. Las versiones modernas de Harbor ya no incluyen Notary v1; no dé por sentado que existen las bases de datos notarysigner/notaryserver.

El [procedimiento oficial de Velero para Harbor](https://github.com/goharbor/website/blob/main/docs/administration/backup-restore/_index.md) utiliza el modo de solo lectura del repositorio y recursos/PV de Kubernetes seleccionados. Su copia de seguridad es **coherente ante fallos, no coherente con la aplicación**, excluye Redis, puede perder metadatos/sesiones no sincronizados y dejar tareas que requieran reparación. Cubre la base de datos interna, no una base de datos externa administrada. Seleccione complementos compatibles de instantáneas/copia de archivos/movimiento de datos y verifique que el sitio de recuperación pueda acceder a todos los datos necesarios de volúmenes/objetos; una referencia a una instantánea no es necesariamente una copia portátil.

Lo siguiente es solo un **ejemplo de volcado del componente de base de datos** para el Pod de PostgreSQL interno verificado, con pg_dump/pg_restore y autenticación local ya configurados. Las bases de datos externas usan su propio proceso autenticado de copia de seguridad/restauración. Las credenciales no se pasan en los argumentos del comando. Deténgase ante errores y mantenga privada cualquier salida parcial; no la publique como un volcado completo.

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

La lista de un archivo no demuestra que la restauración se haya realizado correctamente. Pruebe la restauración con versiones compatibles de PostgreSQL/Harbor y valide la descarga de artefactos, los metadatos, los permisos y las integraciones. Proteja y compruebe la suma de verificación del inventario completo de copias de seguridad, y coordine el modo de solo lectura, los trabajos y la actividad de carga/GC. No desactive automáticamente el modo de solo lectura después de una operación fallida sin evaluar su estado.

BGSAVE de Redis es asíncrono; copiar dump.rdb inmediatamente puede capturar una generación anterior. Si un diseño independiente incluye persistencia de Redis, verifique con su operador que se haya completado y compruebe el estado y la generación. No mezcle silenciosamente ese diseño personalizado con el tutorial oficial que excluye Redis. No se ejecutó ninguna copia de seguridad ni restauración para este capítulo.

## Recopilación de métricas de Prometheus

Mantenga separadas las métricas del host, de kubelet/contenedores y de GPU. `node_cpu_seconds_total` y `node_memory_*` provienen de Node Exporter, no de un endpoint de kubelet. Use un perfil de Node Exporter/DCGM instalado y revisado, y verifique los montajes reales del host, los privilegios, la ubicación de los nodos y la disponibilidad de las métricas. Container Insights no proporciona métricas de nivel de host de Hybrid a través de EC2 IMDS.

El siguiente ejemplo de descubrimiento utiliza las etiquetas/el puerto del Service de Node Exporter de kube-prometheus-stack 92.9.0 con la versión `kube-prom` en `monitoring`. La parte de DCGM presupone Pods verificados con la etiqueta `app: nvidia-dcgm-exporter` en `gpu-operator` y un puerto de contenedor llamado `metrics`; ajústela al exportador instalado. Ninguno de estos recursos instala un exportador. Haga coincidir los selectores de monitores/espacios de nombres del recurso de Prometheus y evite recopilar dos veces las métricas del mismo exportador mediante un monitor existente.

`attachMetadata.node` pone a disposición los metadatos de descubrimiento de Node; no copia automáticamente las etiquetas en las métricas. Requiere Prometheus >=2.37 para ServiceMonitor o >=2.35 para PodMonitor y permisos `list`/`watch` de Node para Prometheus. La configuración de relabeling conserva los nodos que realmente tienen `eks.amazonaws.com/compute-type=hybrid` y crea etiquetas estables `node`/`compute_type` para el destino. No deduzca la ubicación Hybrid a partir del prefijo del nombre de Node de SSM.

Estos ejemplos usan los endpoints HTTP protegidos de métricas de los exportadores, no el endpoint HTTPS de kubelet. Restrinja la conectividad del recopilador. Si el tráfico cruza un límite no confiable, configure TLS/autenticación del exportador o un proxy revisado, junto con la configuración correspondiente de CA/autorización; no use `insecureSkipVerify`. Mantenga la recopilación de métricas de kubelet en su configuración aparte, con autenticación y verificación de CA.

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

### Ejemplos de consultas para el panel de Grafana

Estas consultas requieren las etiquetas de destino anteriores y métricas de exportador compatibles. Verifique las unidades, la identidad de GPU/MIG, los indicadores de valores/errores no compatibles, las recopilaciones ausentes y las series duplicadas. El uso de memoria de framebuffer de GPU divide por la capacidad total (`used + free`), no por la capacidad libre; se excluyen las series con capacidad cero. Las consultas son expresiones que se pueden probar localmente, no mediciones de este entorno.

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

Separe un plan de pruebas de una garantía de servicio de AWS. Los ejemplos anteriores de RTT <5ms, variación <2ms, pérdida <0.01% y rendimiento >1Gbps son objetivos ilustrativos de planificación, no resultados medidos ni promesas universales de Direct Connect. Elija objetivos para la ubicación, el circuito, el endpoint, la carga de trabajo y la capacidad contratada reales; confirme que la ruta medida usa Direct Connect y no una VPN u otra ruta.

`ping` informa el RTT de ICMP y, en Linux iputils, el RTT mdev. Esa dispersión no es la misma estadística que la variación del retardo unidireccional ni que el jitter UDP de iperf3. El filtrado/priorización de ICMP puede diferir del tráfico de aplicaciones. Una prueba de 1,000 paquetes tiene incrementos de pérdida del 0.1%; observar cero pérdidas no demuestra una tasa de pérdida a largo plazo inferior al 0.01%.

Use un servidor de pruebas privado aprobado con iperf3 ya en ejecución, una ventana coordinada, un límite deliberado de tráfico y almacenamiento protegido de resultados. No ejecute iperf3 contra un endpoint de la API de EKS. El ejemplo acotado siguiente requiere Bash, Python3, ping de iputils, GNU timeout e iperf3 con las opciones indicadas. Un fallo detiene la secuencia; la falta de herramientas, el JSON no válido o un error de iperf3 no constituyen una prueba de rendimiento aprobada.

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

Esta prueba TCP limitada no establece la capacidad máxima del enlace. Revise el rendimiento del receptor, las retransmisiones, la dirección, la duración y la congestión. Para una prueba UDP aprobada por separado, use `--udp` y una tasa de bits explícita; después, conserve e interprete la pérdida/jitter del receptor en el JSON de esa versión. Registre las pruebas fallidas/omitidas como tales. Durante esta auditoría no se ejecutó ninguna prueba de carga de red.

## Administración de la renovación de certificados

Identifique qué certificado se está comprobando: el certificado del servidor TLS de Harbor, su cadena de CA, un certificado de servicio de kubelet, la CA del plano de control de EKS o el certificado del host de IAM Roles Anywhere. Un certificado de CA válido no demuestra que el certificado de servidor final sea válido, y un heartbeat de Node Ready no demuestra la fecha de expiración del certificado. AWS administra los certificados del plano de control de EKS; no ejecute comandos de renovación de kubeadm como procedimiento de reparación de EKS.

Esta comprobación local de expiración falla si el certificado falta, no se puede leer, no es válido o vence dentro del período de advertencia de ejemplo de 30 días. No valida la cadena, el nombre de host, la revocación ni si el servicio presenta realmente ese certificado. Use la conexión TLS verificada siguiente para el endpoint servido y el [procedimiento del ciclo de vida de credenciales](./07-node-lifecycle.md) para renovar el certificado del host.

```bash
set -euo pipefail
: "${CERT_PATH:?Set the actual certificate file to inspect}"
test -r "$CERT_PATH"
openssl x509 -in "$CERT_PATH" -checkend 2592000 -noout
```

Haga seguimiento del emisor/responsable real, la ruta configurada del certificado, la expiración y la entrega de alertas. Las rutas de credenciales de servicio/cliente de kubelet dependen de la configuración; habilitar solo serverTLSBootstrap no aprueba las CSR de servicio ni rota un certificado de IAM Roles Anywhere.

## Configuración de Ingress

### Ingress de ALB (modo de destino ip)

El AWS Load Balancer Controller autoadministrado puede registrar IP de Pod de Hybrid enrutables mediante `alb.ingress.kubernetes.io/target-type: ip`. Las rutas, el tráfico de retorno, los grupos de seguridad/cortafuegos y la configuración de red de Pod remoto de EKS deben ser coherentes.

La receta de AWS para el webhook de modo mixto coloca el controlador en nodos de la nube. Es una recomendación de ubicación para ese diseño, no una incapacidad universal para ejecutar un webhook en Hybrid Nodes: la guía del complemento permite la ubicación Hybrid cuando el plano de control puede acceder al CIDR de Pod remoto configurado. Prefiera etiquetas de ubicación administrativas positivas en vez de `compute-type NotIn [hybrid]`, que también coincide con nodos que no tienen esa etiqueta. La etiqueta de ejemplo siguiente solo debe asignarse a nodos de la nube cuya elegibilidad se haya verificado.

```yaml
# Fragment under the controller Deployment's spec.template.spec:
nodeSelector:
  infrastructure.example.com/location: aws
```

### Cilium Ingress Controller

Los ejemplos de Cilium Ingress y Gateway API de esta sección requieren una configuración de Cilium con L7 habilitado. No se aplican a la misma instalación de Cilium configurada para [EKS Hybrid Nodes Gateway](./10-hybrid-nodes-gateway.md): su [configuración de VTEP requerida por AWS](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-gateway-cni.html) establece `vtep.enabled=true` y `l7Proxy=false`. Elija el diseño de red antes de habilitar estas funciones. Esta restricción se refiere a las funciones de proxy L7 de Cilium; no prohíbe que las aplicaciones HTTP usen la ruta de red enrutada del gateway.

Los requisitos previos de Ingress de Cilium 1.18.3 upstream incluyen compatibilidad con NodePort (o sustitución de kube-proxy), compatibilidad con el proxy L7 y una vía disponible de exposición del balanceador de carga. El fragmento siguiente no autoriza a cambiar el CNI de los nodos de la nube en un clúster mixto. Conserve la configuración revisada de Cilium Hybrid y confirme los límites de compatibilidad de AWS para funciones adicionales. Cambiar el modo dedicado/compartido puede cambiar las direcciones e interrumpir las conexiones existentes.

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

Instale las CRD y las versiones de recursos de Gateway API compatibles con la versión del controlador elegida, verifique los requisitos previos de NodePort/sustitución de kube-proxy y L7, y compruebe las condiciones de GatewayClass/Gateway/Route. Establecer una sola opción de Helm no instala esas CRD ni establece accesibilidad externa.

```yaml
# Required Gateway API CRDs and controller prerequisites must already be met:
gatewayAPI:
  enabled: true
```

### IPAM de LoadBalancer (Cilium)

El siguiente grupo usa la API `cilium.io/v2` verificada con la CRD 1.18.3 y selecciona únicamente Services etiquetados explícitamente. Sustituya el CIDR ilustrativo por un rango de direcciones reservado y no superpuesto del inventario de red. La asignación de IP no anuncia la dirección a los enrutadores ni garantiza una ruta de datos funcional.

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

Para el AWS Load Balancer Controller autoadministrado, use un Service `LoadBalancer` de su propiedad con `spec.loadBalancerClass: service.k8s.aws/nlb` y `service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip`, o la ruta documentada de propiedad `aws-load-balancer-type: external` para el controlador elegido. Una anotación de tipo de destino por sí sola no selecciona el controlador. Los destinos de Pod de Hybrid y las rutas de retorno deben ser accesibles desde AWS; elija deliberadamente la exposición interna/pública, las subredes y los controles de acceso.

Esta no es una receta de propiedad de EKS Auto Mode. No cambie la clase/controlador de un Service existente como migración in situ sin revisar los efectos en el reemplazo y el tráfico.

### Cilium LB + BGP

Use los esquemas `cilium.io/v2` instalados. Los tipos de dirección de Service pertenecen en `advertisements[].service.addresses`. El ejemplo anuncia únicamente las IP de LoadBalancer de los Services etiquetados `exposure: onprem-bgp`; no usa un selector `NotIn` que seleccione efectivamente todos los Services.

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

Configure la selección de nodos/peers de CiliumBGPClusterConfig y las familias de CiliumBGPPeerConfig. El selector de anuncios de la configuración del peer debe coincidir con `advertise: hybrid-services`; el selector de Service debe coincidir con las etiquetas reales del Service. Habilite el plano de control BGP revisado, establezca sesiones con los enrutadores y valide las rutas aceptadas, los siguientes saltos, las rutas de retorno y la política de tráfico. Un IPPool/Advertisement por sí solo está incompleto. Consulte los [fundamentos de redes](./02-network-configuration.md) y la documentación BGP de la versión instalada antes de aplicar cambios.

## Configuración detallada de complementos

### Agente de observabilidad de CloudWatch

Use la configuración compatible de Pod Identity y verifique la asociación IAM real y los permisos de la carga de trabajo. La variable de compatibilidad Hybrid `RUN_WITH_IRSA` sigue siendo obligatoria en el procedimiento actual de AWS, pese a su nombre. Añádala a la **lista spec.env** del recurso `AmazonCloudWatchAgent` existente, conservando entradas como `K8S_NODE_NAME`; no es un `env` arbitrario de nivel superior en configurationValues del complemento de EKS.

```yaml
# Add this item to the existing AmazonCloudWatchAgent.spec.env list:
- name: RUN_WITH_IRSA
  value: "True"
```

Inspeccione `amazoncloudwatchagents/cloudwatch-agent` en el espacio de nombres `amazon-cloudwatch` antes de editar y revise cómo el complemento/operador reconcilia esa configuración. Confirme después el despliegue progresivo del agente y la recopilación. Las métricas de clúster/carga de trabajo/Pod/contenedor Hybrid están disponibles, pero las métricas de nivel de nodo de Container Insights no están disponibles porque falta su dependencia de EC2 IMDS. Si su operador se ejecuta en Hybrid Nodes, garantice la accesibilidad del webhook desde el plano de control.

### Agente de EKS Pod Identity

| Sistema operativo del host | Mínimo documentado | DaemonSet Hybrid / ruta de credenciales |
| --- | --- | --- |
| Ubuntu, RHEL, AL2023 | Complemento 1.3.3-eksbuild.1 | `hybrid`; `/eks-hybrid/.aws/credentials` |
| Bottlerocket (variantes VMware compatibles) | Complemento 1.3.7-eksbuild.2 y SO 1.39.0 | `hybrid-bottlerocket`; `/var/eks-hybrid/.aws/credentials` |

Estos son requisitos mínimos de funcionalidad, no una recomendación para instalar una versión antigua. Seleccione una versión del complemento compatible en la actualidad e inspeccione su esquema de configuración. En Ubuntu/RHEL/AL2023, combine este fragmento con el NodeConfig completo existente de cada host:

```yaml
# Merge this fragment into each host's complete, protected NodeConfig:
spec:
  hybrid:
    enableCredentialsFile: true
```

AWS requiere una reconciliación planificada de `nodeadm init -c file:///path/to/nodeconfig.yaml` en cada host afectado, incluidos los nodos que ya se unieron. No vuelva a inicializar a ciegas todos los nodos de producción: conserve la identidad/configuración, siga el procedimiento del ciclo de vida y valide un host a la vez. Bottlerocket usa la ruta de configuración documentada en lugar de este fragmento de nodeadm. Estos archivos temporales de credenciales son sensibles; no los imprima.

Para el DaemonSet Hybrid que no es de Bottlerocket, la configuración del complemento incluye:

```json
{
  "daemonsets": {
    "hybrid": {
      "create": true
    }
  }
}
```

Para Bottlerocket, use la configuración documentada `hybrid-bottlerocket` de la versión seleccionada. Inspeccione y combine los ajustes existentes. Cree un complemento solo si no existe; actualice uno existente con un tratamiento de conflictos revisado, en lugar de usar a ciegas create o OVERWRITE. El agente y el archivo de credenciales no crean la asociación de Pod Identity de cada aplicación: verifique el espacio de nombres, la ServiceAccount, la confianza/permisos del rol de IAM, la resolución de credenciales del SDK y la autorización satisfactoria.

## Operaciones de webhooks en modo mixto

En el patrón compatible de modo mixto de AWS, VPC CNI se ejecuta en nodos de la nube y Cilium/Calico en Hybrid Nodes. AWS recomienda ubicar los webhooks en la nube en ese patrón. Un webhook alojado en Hybrid necesita además un CIDR de Pod remoto enrutable y accesibilidad desde el plano de control; inspeccione el endpoint real en lugar de suponer que todos los webhooks deben o pueden ejecutarse en cualquier lugar.

### Ubicación de CoreDNS

AWS recomienda al menos una réplica de CoreDNS en nodos de la nube y otra en Hybrid Nodes para este diseño de modo mixto. Verifique que haya al menos dos réplicas deseadas, capacidad elegible, selectores, tolerancias y endpoints reales. `maxSkew: 1` por sí solo no crea dos dominios ni garantiza un Pod por dominio, y es posible que los nodos de la nube no tengan la etiqueta `eks.amazonaws.com/compute-type`.

En clústeres compatibles con `minDomains`, este fragmento de especificación de Pod usa una etiqueta administrativa explícita de dos dominios. Etiquete solo los nodos DNS previstos y asigne a cada nodo elegible un valor `location` verificado que sea exactamente `aws` o `onprem`. Mantenga la afinidad/tolerancias existentes compatibles, verifique las etiquetas del Pod de CoreDNS y reconcilie los cambios mediante el mecanismo de configuración compatible del complemento.

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

Con dos dominios elegibles y al menos dos réplicas, la distribución estricta restringe la programación entre ambos. Si un dominio no tiene capacidad, las nuevas réplicas pueden permanecer en estado Pending; es una compensación de disponibilidad, no una conmutación por error garantizada. Pruebe el Service/EndpointSlices de DNS real y la resolución local/remota. En clústeres que contienen Auto Mode, distinga su servicio de sistema DNS local al nodo del Deployment que sigue siendo necesario para los nodos que no son Auto.

<span id="per-add-on-nodeaffinity-settings-guide"></span>

### Guía de ubicación por complemento

| Complemento | Ubicación en este diseño | Comprobación requerida |
| --- | --- | --- |
| AWS Load Balancer Controller | Nodos de la nube en la receta de modo mixto de AWS | Accesibilidad del webhook, etiquetas positivas, destinos IP de Hybrid enrutables |
| Agente/operador de CloudWatch | Agente en los nodos de destino compatibles; preferentemente operador en la nube para los webhooks | Estado de IAM/agente; se excluyen las métricas de nivel de nodo de Hybrid |
| cert-manager | Preferentemente webhook en la nube; es posible una ubicación enrutable en Hybrid | Acceso desde el plano de control y red de Pod remoto |
| Metrics Server | Ubicación en la nube o endpoint de Pod Hybrid accesible | Rutas del plano de control al Pod y de Metrics Server a kubelet |
| CoreDNS | Verifique las réplicas en nodos de la nube y Hybrid | Dominios elegibles, capacidad y tráfico DNS real |
| Cilium/Calico | Hybrid Nodes en el diseño de CNI mixto compatible con AWS | Conservar VPC CNI en los nodos de la nube |

## Comportamiento y preparación ante interrupciones de red

Esta sección describe qué sigue funcionando y qué se detiene cuando Direct Connect o VPN se interrumpe brevemente o la red deja de responder. Hybrid Nodes no están diseñados para entornos DDIL con interrupciones frecuentes y presuponen una conexión fiable con AWS (consulte la [descripción general](./README.md)).

### Clúster y cargas de trabajo durante una interrupción

| Área | Comportamiento |
|---|---|
| Pods en ejecución | Siguen ejecutándose en el nodo. Kubelet no puede renovar su Lease, por lo que la condición Ready del Node pasa a `Unknown` y se añade la taint `node.kubernetes.io/unreachable` (`NoSchedule`, y `NoExecute` cuando se cumplen las condiciones). |
| Conmutación por error de Pod | El plano de control expulsa los Pods sin una tolerancia después de los 300 segundos predeterminados y se crean Pods de reemplazo en otros nodos. Los Pods de DaemonSet toleran esta taint de forma predeterminada y permanecen en el nodo. |
| Etiqueta de zona | Si los nodos tienen `topology.kubernetes.io/zone`, Kubernetes cancela las expulsiones de una zona cuando todos los nodos de esa zona están inaccesibles. Los nodos Hybrid no tienen cloud-controller-manager, así que establezca una zona por centro de datos con `--node-labels` de nodeadm. |
| Cilium | El estado del agente depende del acceso al plano de control, por lo que el agente sigue reiniciándose durante una interrupción y las sesiones de Cilium BGP Control Plane pueden caer (CFP #31702, mejora opcional en Cilium 1.17). El modo L2 de MetalLB utilizado en el ejemplo de AWS permaneció estable durante las interrupciones. |
| Dependencias de servicios de AWS | Los servicios regionales como las descargas de imágenes de ECR, CloudWatch y Amazon Managed Service for Prometheus, ALB/NLB, S3 y RDS no están disponibles durante la interrupción. |
| Resolución de problemas local | No se puede acceder al servidor de API; por ello, use `crictl pods`, `crictl ps` y `crictl logs <container>` en el host en vez de `kubectl`. |

### Credenciales y reconexión

| Elemento | Activaciones híbridas de SSM | IAM Roles Anywhere |
|---|---|---|
| Credenciales temporales | Fijadas en una hora (no se pueden cambiar). Se rotan automáticamente antes de expirar, sin afectar a los nodos ni a las aplicaciones en condiciones normales de funcionamiento. | Una hora de forma predeterminada, hasta 12 horas con `durationSeconds` del perfil. `MaxSessionDuration` del rol de IAM del nodo debe ser mayor. |
| Durante la interrupción | La actualización falla porque no se puede acceder al endpoint regional de SSM; las credenciales pueden expirar durante una interrupción prolongada. | No se pueden obtener credenciales nuevas sin AWS. |
| Después de restablecerse la conexión | Los reintentos usan retroceso exponencial, con un máximo de 30 minutos en el agente de SSM **3.3.808.0 y posteriores**. **Es posible que los nodos no se reconecten hasta 30 minutos después de restablecerse la red**, y los nodos se reconectan en momentos distintos, por lo que los Pods pueden conmutar por error a los nodos que se reconectaron primero. | Kubelet obtiene credenciales bajo demanda mediante `aws_signing_helper credential-process`, por lo que la reconexión suele ocurrir **en cuestión de segundos**. |
| Recuperación más rápida | Reinicie el agente de SSM para forzar una actualización (comandos más abajo). | No es necesario realizar ninguna acción mientras el certificado sea válido. Configure notificaciones de expiración del certificado. |

Versión, reinicio y registros del agente de SSM:

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

Durante una interrupción, el registro repite `Retrieve credentials produced error: RequestError: send request failed` y `Sleeping for ... before retrying retrieve credentials`; cuando la actualización se completa correctamente, se registra `Credentials ready`.

### Lista de comprobación de preparación

- **Conectividad redundante:** Haga que Direct Connect sea redundante o mantenga una VPN Site-to-Site como respaldo.
- **Detectar interrupciones:** Habilite los registros de Controller Manager del plano de control de EKS y cree un filtro de métricas y una alarma de CloudWatch para el mensaje `Recording status change event message for node` con `status="NodeNotReady"`. Configure alarmas si `BytesIn`/`BytesOut` de TGW o `TunnelDataIn`/`TunnelDataOut` de VGW caen por debajo de lo normal. CloudWatch Network Monitor muestra la pérdida y la latencia.
- **Versión del agente de SSM:** Mantenga la versión 3.3.808.0 o posterior para que el intervalo de reintento tenga un máximo de 30 minutos.
- **Etiqueta de zona:** Establezca `topology.kubernetes.io/zone` por centro de datos.
- **Ajustar la expulsión:** Para aplicaciones que no se pueden mover fácilmente, aumente `tolerationSeconds`. Los valores más largos también retrasan el traslado de Pods desde nodos que realmente han fallado.

```yaml
# Fragment under the Deployment's spec.template.spec
tolerations:
  - key: "node.kubernetes.io/unreachable"
    operator: "Exists"
    effect: "NoExecute"
    tolerationSeconds: 1800
```

- **Proveedor de credenciales:** Si las interrupciones son frecuentes y es importante reconectarse rápidamente, considere IAM Roles Anywhere con un `durationSeconds` más prolongado. Use un solo proveedor dentro de un clúster.
- **Ruta de observabilidad secundaria:** Configure el recopilador de ADOT para enviar datos a varios backends, de modo que mantenga la visibilidad cuando los servicios regionales no estén disponibles.

Referencias:
- [Credenciales del host durante interrupciones de red](https://docs.aws.amazon.com/eks/latest/best-practices/hybrid-nodes-host-creds.html)
- [Prácticas recomendadas para mantener la estabilidad durante interrupciones de red](https://docs.aws.amazon.com/eks/latest/best-practices/hybrid-nodes-network-disconnection-best-practices.html)
- [Conmutación por error de Pods de Kubernetes durante interrupciones de red](https://docs.aws.amazon.com/eks/latest/best-practices/hybrid-nodes-kubernetes-pod-failover.html)

## Resolución de problemas comunes

### Diagnóstico de ImagePullBackOff

Lea los eventos del Pod e inspeccione el nombre/tipo del Secret al que se hace referencia sin decodificar ni imprimir las credenciales del registro. El Secret debe estar en el espacio de nombres del Pod. Confirme el nombre de host del registro, el permiso requerido para el repositorio y la expiración de las credenciales con su responsable; los metadatos por sí solos no pueden demostrar que la autenticación funcione.

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

Ejecute una comprobación de TLS desde la ruta de red/host real, con la CA de confianza y la verificación del nombre de host habilitadas. No use curl -k ni interprete una respuesta 401 no autenticada del registro como un fallo de TLS. Este ejemplo requiere Bash, OpenSSL y GNU timeout.

```bash
set -euo pipefail
: "${HARBOR_HOST:?Set the registry DNS name, without scheme or port}"
: "${HARBOR_CA_FILE:?Set the approved CA bundle file}"
timeout 10s openssl s_client -connect "$HARBOR_HOST:443" \
  -servername "$HARBOR_HOST" -verify_hostname "$HARBOR_HOST" \
  -verify_return_error -CAfile "$HARBOR_CA_FILE" </dev/null
```

Para probar DNS/red dentro de un Pod, use una imagen de diagnóstico aprobada fijada por resumen criptográfico, un espacio de nombres dedicado y una ubicación explícita en el Hybrid Node afectado. Un Pod de depuración arbitrario sin fijar puede ejecutarse en un nodo de la nube y probar la ruta equivocada. Revise por separado la creación/eliminación del Pod y conserve los resultados con el alcance limitado.

### Problemas de resolución de DNS

Inspeccione el Deployment/Pods, el Service y los EndpointSlices reales de CoreDNS, su ubicación en la nube/en las instalaciones, la configuración DNS y la accesibilidad de red. Pruebe el nombre del registro y kubernetes.default.svc.cluster.local desde el entorno de la carga de trabajo afectada. Los fallos de acceso a la API, al DNS o a los registros son observaciones desconocidas, no comprobaciones satisfactorias.

No reinicie todos los Pods de CoreDNS como acción de diagnóstico predeterminada. Determine primero qué capa falla y coordine cualquier reinicio con las comprobaciones de redundancia y recuperación. Los clústeres mixtos con Auto Mode pueden tener un comportamiento de DNS local al nodo; determine qué ruta del resolver usa realmente el Pod que falla.

### Problemas de conectividad de nodos

Use el nombre real del Node del inventario y el host asociado. Los nombres de Node respaldados por SSM no tienen por qué empezar por hybrid- ni resolverse como nombres de host.

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

Compruebe el proveedor de credenciales y la unidad del agente específica del sistema operativo (incluida la instalación de SSM basada en snap de Ubuntu cuando corresponda). Para diagnosticar la red/autenticación, use el procedimiento verificado `nodeadm debug -c file:///etc/eks/nodeconfig.yaml` con privilegios de root y almacenamiento privado de la salida. Se comunica con AWS y el clúster; no registre las credenciales emitidas ni desactive la verificación de TLS.

No hay un subcomando `nodeadm reset` en la CLI revisada 1.0.20. NotReady no es motivo para anular el registro o volver a inicializar un host a ciegas. Siga el procedimiento de [recuperación y reconciliación de identidad](./07-node-lifecycle.md) después de determinar la causa del fallo, conservando los montajes/datos y registrando las identidades de nodo/SSM.

## Alcance de la validación y referencias

Las comprobaciones locales cubren esquemas de recursos fijados, cuatro expresiones PromQL con muestras sintéticas y once casos de dobles de prueba de comandos de copia de seguridad/red. No se ejecutaron cambios de AWS/Kubernetes, una copia de seguridad/restauración real, una prueba de carga de red, una sesión BGP, una recopilación de métricas de exportador ni un despliegue progresivo de producción. Seleccione combinaciones de EKS/SO/CNI/complementos a partir de la documentación actual de compatibilidad de AWS antes del despliegue.

- [Complementos de AWS Hybrid](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-add-ons.html)
- [Webhooks de AWS Hybrid](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-webhooks.html)
- [Actualizaciones de AWS Hybrid](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-upgrade.html)
- [API de Prometheus Operator](https://prometheus-operator.dev/docs/api-reference/api/)
- [Requisitos previos de Cilium 1.18.3 Ingress](https://github.com/cilium/cilium/blob/v1.18.3/Documentation/network/servicemesh/ingress.rst)
- [CRD de Cilium 1.18.3 LoadBalancer IPPool](https://github.com/cilium/cilium/blob/v1.18.3/pkg/k8s/apis/cilium.io/client/crds/v2/ciliumloadbalancerippools.yaml)
- [Invocación de iperf3](https://software.es.net/iperf/invoking.html)
- [Tolerancias de taints de Kubernetes](https://kubernetes.io/docs/concepts/scheduling-eviction/taint-and-toleration/)


---

< [Anterior: Administración del ciclo de vida de los nodos](./07-node-lifecycle.md) | [Tabla de contenido](./README.md) | [Siguiente: Configuración del sistema operativo en bare metal](./09-bare-metal-os-setup.md) >
