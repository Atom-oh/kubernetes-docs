# Buenas prácticas de Cilium Service Mesh

> **Línea base revisada**: Cilium 1.20.3 y Cilium CLI 0.20.1.
> **Última revisión**: 16 de octubre de 2026. Consulte la [guía de instalación](./README.md) para comprobar por separado la compatibilidad de Kubernetes, EKS y los componentes opcionales.

## Descripción general

Un plan operativo debe coordinar la propiedad del CNI, las funciones del proxy, la aplicación de políticas, la capacidad y la recuperación. Los valores siguientes son ejemplos que deben revisarse para cada clúster. No son garantías de dimensionamiento probadas en producción, un procedimiento de migración de CNI ni una instalación completa de EKS.

## Lista de verificación para el despliegue en producción

- [ ] Elija una combinación compatible de Kubernetes, Cilium y plataforma, además de la arquitectura de CPU y el sistema operativo de los nodos. El kernel mínimo general es 5.10 o un equivalente documentado, como 4.18 de RHEL 8.10; las funciones avanzadas pueden requerir kernels más recientes.
- [ ] Registre el CNI y el IPAM actuales, los CIDR de Pods/Services/VPC, las rutas, la MTU y quién administra kube-proxy. Compruebe que se puede alcanzar la dirección del servidor de API antes de habilitar su reemplazo.
- [ ] Elija quién administrará L7 para cada carga de trabajo. Cilium Ingress/Gateway requiere los prerrequisitos documentados de reemplazo de kube-proxy y L7; la coexistencia con Istio usa una configuración distinta.
- [ ] Decida por separado la autenticación, el cifrado y la autorización. Valide los flujos permitidos y denegados, DNS y el acceso esencial a la infraestructura antes de aplicar denegación predeterminada.
- [ ] Defina los objetivos de métricas, las etiquetas reales, los registros, el enrutamiento de alertas y la renovación de certificados. Pruebe el comportamiento cuando faltan datos.
- [ ] Proporcione suficientes nodos elegibles para ubicar réplicas y realizar mantenimiento. Compruebe la disponibilidad de Operator/Relay, los presupuestos de interrupción y la estrategia de actualización del DaemonSet.
- [ ] Registre un punto de reversión probado, los charts/valores/CRD que se conservarán y el inventario de cargas y políticas. Ensaye el procedimiento en un entorno representativo.

### Valores de Helm que se deben revisar

Combine esta **superposición de recursos y disponibilidad** con la configuración de la plataforma de la guía de instalación. Deliberadamente, no elige un rango IP universal, no deshabilita kube-proxy ni habilita todas las funciones de seguridad opcionales.

```yaml
agent: true
resources:
  requests:
    cpu: 500m
    memory: 512Mi
  limits:
    cpu: 2000m
    memory: 2Gi
operator:
  replicas: 2
  podDisruptionBudget:
    enabled: true
    maxUnavailable: 1
  resources:
    requests:
      cpu: 100m
      memory: 128Mi
    limits:
      cpu: 1000m
      memory: 1Gi
l7Proxy: true
envoy:
  enabled: true
  updateStrategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
  resources:
    requests:
      cpu: 200m
      memory: 256Mi
    limits:
      cpu: 2000m
      memory: 2Gi
hubble:
  enabled: true
  relay:
    enabled: true
    replicas: 2
    podDisruptionBudget:
      enabled: true
      maxUnavailable: 1
    affinity:
      podAntiAffinity:
        requiredDuringSchedulingIgnoredDuringExecution:
        - topologyKey: kubernetes.io/hostname
          labelSelector:
            matchLabels:
              k8s-app: hubble-relay
    resources:
      requests:
        cpu: 100m
        memory: 128Mi
      limits:
        cpu: 1000m
        memory: 1Gi
updateStrategy:
  type: RollingUpdate
  rollingUpdate:
    maxUnavailable: 1
```

`agent` es un booleano. Las solicitudes y los límites de recursos del Agent se configuran en `resources` de nivel superior, no en `agent.resources`. Se consolidaron las dos definiciones de recursos que antes entraban en conflicto. Estas cantidades de CPU/memoria son valores iniciales de ejemplo; mídalas con el número de políticas, la frecuencia de cambios, el tráfico y los escenarios de fallo del clúster.

La afinidad del chart de Operator separa las réplicas por nombre de host. La anti-afinidad de Relay también requiere aquí dos nodos elegibles. No impone separación entre zonas de disponibilidad; añada reglas de topología adecuadas para el clúster. Dos réplicas sin ubicación programable ni dependencias funcionales no proporcionan alta disponibilidad. Los PDB rigen los desalojos voluntarios que cumplen sus condiciones, no todas las interrupciones ni la actualización de un controlador DaemonSet; eliminar un Pod directamente también omite la protección de desalojo.

Usar etcd externo es una decisión arquitectónica con sus propios requisitos operativos; no es una incorporación obligatoria al alcanzar cierto número de nodos. Mantenga coherente el modo elegido para asignar identidades y siga el procedimiento de migración documentado si lo cambia.

### Autenticación y cifrado

El siguiente perfil opcional combina autenticación fuera de banda y WireGuard:

```yaml
encryption:
  enabled: true
  type: wireguard
  nodeEncryption: false
authentication:
  enabled: true
  mutual:
    spire:
      enabled: true
```

Habilítelo solo si se cumplen los prerrequisitos de kernel, puertos, almacenamiento/identidad SPIRE y políticas de la [guía de seguridad](./03-security.md). Además de la configuración de SPIRE, se requiere `authentication.enabled`. Para aplicar la autenticación, una regla debe exigirla. WireGuard protege el tráfico elegible entre nodos; la autenticación fuera de banda basada en SPIRE no convierte cada conexión de aplicación en una sesión mTLS como en Istio. `nodeEncryption` tiene una condición de habilitación independiente y permanece en `false` en este ejemplo.

Cilium 1.20.3 también ofrece mTLS de cargas de trabajo con ztunnel en estado **Beta**, documentado por separado en la guía de seguridad. La CA interna predeterminada, la inscripción de espacios de nombres y las limitaciones de TCP/HBONE/políticas son distintas de la ruta SPIRE fuera de banda. Elija un diseño explícito: ni una casilla marcada ni una opción de Helm demuestran que la cobertura de seguridad sea equivalente.

## Guías de dimensionamiento

### Medición por componente

| Componente | Factores de capacidad que se deben medir | Comprobaciones antes de aumentar los límites |
|---|---|---|
| Agent | Endpoints, identidades, selectores/reglas de políticas, cambios de conexiones, mapas BPF y volumen de eventos | Conjunto de trabajo, CPU/limitación, presión de mapas, regeneración de políticas y motivos de descarte |
| Envoy | Conexiones/flujos simultáneos, carga TLS, tamaño de solicitudes/respuestas, almacenamiento en búfer y coste de filtros | Heap/RSS, CPU, colas, saturación de upstream y p99 con una carga fija |
| Operator | Cambios de IPAM/identidad/nodos y latencia/límites de tasa de la API | Cola de reconciliación, limitación de EC2/Kubernetes y fallos de asignación |
| Hubble Relay/UI | Volumen de flujos observados, observadores simultáneos, búfer de flujos y alcance de consultas | Eventos perdidos, recursos de Relay, latencia de consultas y ubicación de réplicas |

La tabla anterior por número de nodos y las fórmulas `512Mi + Pods × 1Mi` y `256Mi + conexiones/segundo × 0.1Mi` no tenían pruebas de benchmark. No son modelos de memoria universales válidos. Importan las conexiones simultáneas máximas, la duración de los búferes, la mezcla de tráfico y la cardinalidad de políticas; las solicitudes por segundo por sí solas no determinan la memoria retenida. Fije las solicitudes según las necesidades de programación medidas, deje margen probado y verifique los límites durante picos y la pérdida de un nodo.

### Dimensionamiento de mapas eBPF

Este es un ejemplo concreto de dimensionamiento estático, no varias alternativas dentro de una sola asignación YAML:

```yaml
bpf:
  ctTcpMax: 2097152
  ctAnyMax: 1048576
  natMax: 2097152
  policyMapMax: 65536
```

Las claves actuales del chart son `ctTcpMax`, `ctAnyMax` y `natMax`; se ignoran los valores antiguos `ctGlobalTcpMax`, `ctGlobalAnyMax` y `natGlobalMax`. Las opciones del ConfigMap del Agent siguen usando nombres como `bpf-ct-global-tcp-max`; no confunda las claves del chart con las opciones del daemon. La capacidad NAT no debe superar dos tercios de la capacidad CT combinada de TCP y otras conexiones; estos valores respetan ese límite. El máximo de entradas de un mapa no garantiza una cantidad determinada de sesiones de aplicación.

Aumentar el tamaño de los mapas consume memoria del kernel y del nodo. Cambiar su tamaño o implementación puede interrumpir el estado y las conexiones. Inspeccione el ConfigMap renderizado y el uso real de los mapas; no deduzca la capacidad a partir del número de nodos ni interprete las líneas de salida legible de la CLI como una medición precisa de ocupación.

## Ajuste del rendimiento

### Configuración de eBPF

```yaml
bpf:
  preallocateMaps: true
  mapDynamicSizeRatio: 0.0025
bpfClockProbe: false
```

La preasignación intercambia más memoria inicial por evitar parte del trabajo de asignación; no es una opción para ahorrar memoria. Esta alternativa usa la proporción de dimensionamiento dinámico. No la combine sin cuidado con el ejemplo de mapas estáticos: los tamaños explícitos prevalecen sobre el dimensionamiento derivado y LRU distribuido tiene restricciones adicionales. `bpfClockProbe` es una clave de nivel superior; cambiar la representación de reloj con estado CT existente requiere las precauciones de migración documentadas.

`socketLB` también es una clave de nivel superior, no está anidada bajo `bpf`. Para la coexistencia con Istio, su ajuste `hostNamespaceOnly` es significativo; activar la aceleración de sockets indiscriminadamente puede evitar la intercepción prevista del proxy. `bpf.lbBypassFIBLookup`, la opción antigua, no es un valor compatible del chart.

El perfil netkit/BIG TCP de la guía de ajuste publicada tiene prerrequisitos de kernel/NIC y migración (incluido kernel 6.8 para ese perfil). Los Pods veth existentes no se pueden convertir simplemente cambiando un valor. Use el método documentado de migración por nodo/nodos nuevos y valide el cifrado, el enrutamiento y el comportamiento de las aplicaciones antes de ampliar el cambio.

### Pila de red

Empiece por leer la configuración de los nodos:

```bash
sysctl net.core.somaxconn net.ipv4.tcp_max_syn_backlog \
  net.core.netdev_max_backlog net.ipv4.tcp_fin_timeout net.ipv4.tcp_tw_reuse
```

Cambie un sysctl solo después de identificar el cuello de botella pertinente de cola o estado de conexión y comprobar la semántica del kernel de destino. La antigua lista global de `sysctl -w` no era un resultado de ajuste específico para una carga. En particular, `tcp_fin_timeout` no es un ajuste universal para limpiar TIME_WAIT, y reutilizar TIME_WAIT no es una solución general de latencia. Conserve los valores originales y use la configuración administrada de nodos para aplicar un cambio revisado.

### Envoy

`CiliumEnvoyConfig.spec.resources` admite tipos concretos de recursos xDS; **no** admite un objeto Bootstrap. El objeto Bootstrap con overload manager que se incluía antes dentro de un CEC no se aplicaría. Un monitor de heap fijo tampoco define por sí solo una acción de sobrecarga.

Use los límites de recursos del chart y el [ejemplo completo del grupo de conexiones](./05-ingress-gateway.md#connection-pool-configuration) para sus respectivos propósitos. El overload manager pertenece al bootstrap del proceso y requiere acciones y umbrales compatibles. Si usa `envoy.bootstrapConfigMap`, conserve el cableado de bootstrap que Cilium necesita y valídelo con la imagen exacta de Envoy publicada. Sustituir todo el bootstrap es una integración avanzada, no un parche CEC parcial seguro.

### Evidencia de benchmarks

La cifra anterior afirmaba latencias p99 de 0,1/0,3/2,5 ms para Cilium nativo/Cilium/Istio sin fuente, versión, topología, carga, configuración de cifrado ni datos reproducibles. No se conserva como medición histórica. Mantenga versiones/fechas reales de los benchmarks cuando exista evidencia; no atribuya un resultado antiguo a una versión nueva.

Una comparación útil registra hardware, versiones de kernel/CNI/malla, tamaño de solicitudes, concurrencia, conexiones, configuración TLS/políticas/filtros, calentamiento, número de muestras, rendimiento, tasa de errores y latencia de cola. Compare un comportamiento L4 o L7/de seguridad equivalente, en vez de suponer que todas las rutas de Cilium son una malla sin Envoy.

## Migración desde una malla sidecar

### Separar la migración de CNI de la migración de malla

Instalar un segundo CNI junto al existente no es suficiente. El procedimiento oficial de migración con dos overlays requiere CIDR de Pods y encapsulación distintos, control por nodo, reciclaje de cargas de trabajo y decisiones explícitas sobre la aplicación de políticas. Tiene combinaciones que no se han probado. Ensaye el caso real de la plataforma; el diagrama antiguo, con su paso genérico de «instalar junto al CNI existente», omitía requisitos esenciales.

Cuando Cilium ya proporciona la red, la coexistencia con la malla es otra tarea. La integración de Istio de Cilium describe una ruta con kube-proxy presente:

```yaml
kubeProxyReplacement: false
cni:
  exclusive: false
```

Para una ruta planificada que reemplace kube-proxy por completo:

```yaml
kubeProxyReplacement: true
socketLB:
  hostNamespaceOnly: true
cni:
  exclusive: false
```

Conserve la configuración necesaria del servidor de API, CNI/IPAM y la plataforma. `cni.exclusive: false` mantiene otra configuración CNI, como Istio CNI; `socketLB.hostNamespaceOnly: true` evita interferir con la captura del proxy a nivel de Pod. La clave obsoleta `tunnel: vxlan` no es un procedimiento de migración vigente. Si selecciona un overlay por separado, las claves actuales son `routingMode` y `tunnelProtocol`, con los requisitos de enrutamiento/MTU correspondientes.

### Transferir las cargas de trabajo de forma deliberada

Antes de cambiar nada, registre `istio-injection`, las etiquetas de revisión, las anotaciones de inyección de Pods, la inscripción ambient y los sidecars existentes. Una etiqueta de espacio de nombres afecta admisiones futuras; no quita un sidecar que ya está en ejecución. Las etiquetas de revisión y los ajustes por Pod pueden imponerse a un plan simplista basado en el espacio de nombres. Recree solo las cargas seleccionadas después de revisar su disponibilidad y validar la política sustituta.

Durante la transición, asigne un solo responsable de políticas L7 a cada carga de trabajo. Cilium no puede aplicar reglas HTTP dentro del tráfico cifrado por Istio. Deshabilitar mTLS de Istio solo para obtener visibilidad HTTP cambia la seguridad y no es un paso de conversión automático. HBONE ambient también cambia lo que Cilium puede observar en L4; mantenga a Istio como responsable de la identidad de carga y de la política del tráfico interno mientras se conserve esa ruta.

### Ejemplo de conversión de enrutamiento

Prerrequisito: Pods `app: reviews` listos con `version: v1` o `v2`, que sirven HTTP en el puerto 9080 del Pod. Los Services separados hacen explícita la selección de versión:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: reviews
  namespace: default
spec:
  selector:
    app: reviews
  ports:
  - name: http
    port: 9080
    targetPort: 9080
---
apiVersion: v1
kind: Service
metadata:
  name: reviews-v1
  namespace: default
spec:
  selector:
    app: reviews
    version: v1
  ports:
  - name: http
    port: 9080
    targetPort: 9080
---
apiVersion: v1
kind: Service
metadata:
  name: reviews-v2
  namespace: default
spec:
  selector:
    app: reviews
    version: v2
  ports:
  - name: http
    port: 9080
    targetPort: 9080
```

Una configuración de enrutamiento de Istio requiere tanto el VirtualService como las definiciones de subconjuntos:

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews-route
  namespace: default
spec:
  hosts:
  - reviews
  http:
  - match:
    - headers:
        end-user:
          exact: jason
    route:
    - destination:
        host: reviews
        subset: v2
  - route:
    - destination:
        host: reviews
        subset: v1
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-subsets
  namespace: default
spec:
  host: reviews
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
```

Para las cargas cuya administración L7 se haya transferido, un CEC completo de Cilium puede implementar este comportamiento de selección por encabezado:

```yaml
apiVersion: cilium.io/v2
kind: CiliumEnvoyConfig
metadata:
  name: reviews-route
  namespace: default
spec:
  services:
  - name: reviews
    namespace: default
    ports:
    - 9080
    listener: reviews-listener
  backendServices:
  - name: reviews-v1
    namespace: default
  - name: reviews-v2
    namespace: default
  resources:
  - '@type': type.googleapis.com/envoy.config.listener.v3.Listener
    name: reviews-listener
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: reviews-migration
          route_config:
            name: reviews-routes
            virtual_hosts:
            - name: reviews
              domains:
              - '*'
              routes:
              - match:
                  prefix: /
                  headers:
                  - name: end-user
                    string_match:
                      exact: jason
                route:
                  cluster: default/reviews-v2
              - match:
                  prefix: /
                route:
                  cluster: default/reviews-v1
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/reviews-v1
    type: EDS
    connect_timeout: 5s
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/reviews-v2
    type: EDS
    connect_timeout: 5s
```

El CEC incluye un Listener, HCM/router, ambos clústeres EDS y referencias reales a los Services de backend. Cilium proporciona la configuración dinámica de endpoints. `end-user: jason` es una entrada de enrutamiento no confiable, no una autenticación. Este ejemplo no copia todo el comportamiento de Istio en cuanto a tiempos de espera, reintentos, mTLS o telemetría; compárelos por separado y use la [guía de reintentos](./02-traffic-management.md#retry-configuration) para proteger escrituras. No asocie ambas implementaciones a la misma ruta de tráfico activa suponiendo que la propiedad sea equivalente.

### La autorización no es una traducción mecánica

Para una carga de trabajo `app: httpbin` administrada por Istio en el puerto 8080 del Pod, exija mTLS entrante y permita el principal autenticado específico de la cuenta de servicio:

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: httpbin-strict
  namespace: default
spec:
  selector:
    matchLabels:
      app: httpbin
  mtls:
    mode: STRICT
---
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: httpbin
  namespace: default
spec:
  selector:
    matchLabels:
      app: httpbin
  action: ALLOW
  rules:
  - from:
    - source:
        principals:
        - cluster.local/ns/default/sa/sleep
    to:
    - operation:
        methods:
        - GET
        paths:
        - /info*
        ports:
        - '8080'
```

Una política candidata de Cilium para la misma selección de etiquetas de espacio de nombres/cuenta de servicio e intención GET/ruta es:

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: httpbin
  namespace: default
spec:
  endpointSelector:
    matchLabels:
      k8s:app: httpbin
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: default
        k8s:io.cilium.k8s.policy.serviceaccount: sleep
    authentication:
      mode: required
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
      rules:
        http:
        - method: ^GET$
          path: ^/info.*$
```

Esto requiere instalar por separado el sistema de autenticación de Cilium; no consume el principal del certificado de Istio. Las identidades de seguridad, el dominio de confianza, el intercambio de autenticación y la cobertura de cifrado son distintos. El puerto es el **puerto de destino del Pod**, no un puerto de Service supuesto. Las políticas allow adicionales pueden ampliar el acceso en cualquiera de los sistemas, y la salida de Cilium no queda denegada por esta regla de entrada. Antes de afirmar que la migración es equivalente, pruebe GET permitido, métodos/rutas denegados, una cuenta de servicio incorrecta, la falta de autenticación y las rutas cifradas/sin cifrar.

### Plan de reversión

Conserve en el sistema de despliegue las plantillas de cargas originales, etiquetas, políticas, Secrets/propiedad de certificados y valores de Helm. Registre exactamente qué recursos pertenecen a la migración. Primero restaure la ruta anterior de tráfico/política elegida y compruebe su identidad y aplicación; después elimine solo los recursos de migración sustituidos en el orden probado.

El script anterior eliminaba **todas las CiliumNetworkPolicy de un espacio de nombres**, lo que podía quitar protecciones de denegación predeterminada que no pertenecían a la migración. Se eliminó. Volver a habilitar una etiqueta de inyección y reiniciar todos los Deployments tampoco basta para una inyección administrada por revisión, la inscripción ambient, StatefulSets o Jobs. Revertir CNI/IPAM puede requerir recrear nodos y Pods y constituye un procedimiento de recuperación independiente.

## Adopción gradual

Si Cilium debe proporcionar solo redes y políticas L3/L4, deshabilite deliberadamente las funciones L7 pertinentes de Cilium:

```yaml
l7Proxy: false
envoy:
  enabled: false
ingressController:
  enabled: false
gatewayAPI:
  enabled: false
```

Por sí solo, `envoy.enabled: false` selecciona el modo Envoy integrado cuando L7 sigue habilitado; no desactiva todas las funciones L7 de Cilium. Antes de quitar su funcionalidad, inventaríe las políticas L7, los recursos Ingress/Gateway y los CEC existentes. Con Istio ambient, Cilium ve el transporte HBONE, no el flujo interno original de la carga de la misma manera que ve el tráfico de texto sin cifrar habitual.

| Fase | Propiedad L7 y criterios de salida |
|---|---|
| Establecer la red | Verifique el comportamiento de Cilium CNI/L3/L4 mientras la malla actual conserva la propiedad prevista del tráfico |
| Transferir cargas seleccionadas | Separe la propiedad por carga; compare enrutamiento, identidad, cifrado, reintentos y telemetría con pruebas negativas |
| Retirar componentes antiguos | Quítelos solo después de verificar todas las cargas dependientes y los procedimientos de recuperación |

La figura anterior de transición repetía una reversión que borraba políticas indiscriminadamente y simplificaba en exceso la coexistencia; esta tabla sustituye esos pasos.

## Supervisión y alertas

### Etiquetas de scrape explícitas

Instale primero los CRD de Prometheus Operator y configure sus selectores ServiceMonitor/PrometheusRule. Esta superposición fija los nombres de ejemplo de los jobs y una etiqueta de clúster; sustituya `example-cluster` de forma coherente por la identidad real del clúster y adapte el selector `release`:

```yaml
prometheus:
  enabled: true
  serviceMonitor:
    enabled: true
    labels:
      release: prometheus
    relabelings:
    - sourceLabels:
      - __meta_kubernetes_pod_node_name
      targetLabel: node
    - targetLabel: cluster
      replacement: example-cluster
    - targetLabel: job
      replacement: cilium-agent
envoy:
  prometheus:
    enabled: true
    serviceMonitor:
      enabled: true
      labels:
        release: prometheus
      relabelings:
      - sourceLabels:
        - __meta_kubernetes_pod_node_name
        targetLabel: node
      - targetLabel: cluster
        replacement: example-cluster
      - targetLabel: job
        replacement: cilium-envoy
```

El contexto HTTPv2 de Hubble y las reglas de grabación se configuran por separado en la [guía de observabilidad](./04-observability.md). Las observaciones L7 solo existen para el tráfico con la visibilidad requerida. Use una ruta de métricas interna confiable; estos valores no configuran la accesibilidad de Prometheus remoto.

### Reglas operativas

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: cilium-operational-signals
  namespace: monitoring
  labels:
    release: prometheus
spec:
  groups:
  - name: cilium.operational
    rules:
    - alert: CiliumMetricsScrapeFailed
      expr: up{job=~"cilium-agent|cilium-envoy"} == 0
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: Known Cilium metrics target cannot be scraped
    - alert: HighObservedPacketDrops
      expr: sum by (cluster, node, direction, reason) (rate(cilium_drop_count_total[5m]))
        > 1000
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: High observed packet drop count
    - alert: HighBPFMapPressure
      expr: cilium_bpf_map_pressure > 0.8
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: High pressure in an instrumented BPF map
```

Un scrape fallido de `up` indica que no se pudo acceder al destino, no necesariamente que el proceso Agent/Envoy se haya detenido. Si el descubrimiento elimina un destino, su serie `up` puede desaparecer por completo; compare por separado el inventario esperado de nodos/DaemonSets. `cilium_proxy_redirects` cuenta las redirecciones instaladas y puede ser legítimamente cero; no indica que Envoy esté activo.

La proporción antigua `cilium_datapath_conntrack_active/max` usaba métricas inexistentes. Las observaciones de CT GC no son una métrica instantánea de capacidad total. Las métricas de presión de mapas cubren los mapas instrumentados y sus reglas de emisión; compruebe cuáles existen. Los umbrales de descarte y presión anteriores son ilustrativos y deben calibrarse según el tráfico, el motivo, la duración y las denegaciones de políticas esperadas.

### Importar el dashboard

Este es un JSON de dashboard clásico independiente para importar desde la interfaz de Grafana, no un wrapper de API HTTP. Seleccione el origen de datos de Prometheus e instale primero las reglas de grabación `cilium_hubble:*` de la guía de observabilidad:

```json
{
  "__inputs": [
    {
      "name": "DS_PROMETHEUS",
      "label": "Prometheus",
      "type": "datasource",
      "pluginId": "prometheus",
      "pluginName": "Prometheus"
    }
  ],
  "id": null,
  "uid": "cilium-operational",
  "title": "Cilium operational signals",
  "tags": [
    "cilium",
    "hubble"
  ],
  "schemaVersion": 38,
  "version": 1,
  "timezone": "browser",
  "time": {
    "from": "now-1h",
    "to": "now"
  },
  "refresh": "30s",
  "panels": [
    {
      "id": 10,
      "title": "Successfully scraped agent targets",
      "type": "stat",
      "gridPos": {
        "x": 0,
        "y": 0,
        "w": 12,
        "h": 8
      },
      "datasource": {
        "type": "prometheus",
        "uid": "${DS_PROMETHEUS}"
      },
      "targets": [
        {
          "refId": "A",
          "expr": "sum by (cluster) (up{job=\"cilium-agent\"})",
          "legendFormat": "{{cluster}}"
        }
      ]
    },
    {
      "id": 1,
      "title": "Observed HTTP responses/s",
      "type": "timeseries",
      "gridPos": {
        "x": 12,
        "y": 0,
        "w": 12,
        "h": 8
      },
      "datasource": {
        "type": "prometheus",
        "uid": "${DS_PROMETHEUS}"
      },
      "targets": [
        {
          "refId": "A",
          "expr": "cilium_hubble:http_responses:rate5m",
          "legendFormat": "{{cluster}} / {{destination_namespace}} / {{destination_workload}}"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "unit": "reqps"
        },
        "overrides": []
      }
    },
    {
      "id": 2,
      "title": "Observed HTTP5xx (%)",
      "type": "timeseries",
      "gridPos": {
        "x": 0,
        "y": 8,
        "w": 12,
        "h": 8
      },
      "datasource": {
        "type": "prometheus",
        "uid": "${DS_PROMETHEUS}"
      },
      "targets": [
        {
          "refId": "A",
          "expr": "cilium_hubble:http_5xx_percent:rate5m",
          "legendFormat": "{{cluster}} / {{destination_namespace}} / {{destination_workload}}"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "unit": "percent"
        },
        "overrides": []
      }
    },
    {
      "id": 3,
      "title": "Observed HTTP P99",
      "type": "timeseries",
      "gridPos": {
        "x": 12,
        "y": 8,
        "w": 12,
        "h": 8
      },
      "datasource": {
        "type": "prometheus",
        "uid": "${DS_PROMETHEUS}"
      },
      "targets": [
        {
          "refId": "A",
          "expr": "histogram_quantile(0.99, cilium_hubble:http_latency_bucket:rate5m)",
          "legendFormat": "{{cluster}} / {{destination_namespace}} / {{destination_workload}}"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "unit": "s"
        },
        "overrides": []
      }
    }
  ]
}
```

El panel de estado cuenta los destinos Agent scrapeados correctamente, no los «Pods sanos». Los paneles HTTP heredan el límite del lado del servidor, el alcance de espacio de nombres/carga/clúster y el comportamiento de numerador ausente de las reglas de grabación. La ausencia de datos no equivale a cero fallos; el dashboard requiere las fuentes y etiquetas indicadas.

## Estrategia de actualización

### Revisar antes de implementar

Cilium prueba las actualizaciones y reversiones **solo entre versiones menores consecutivas**. Primero actualice la versión menor actual a su último parche y lea los cambios requeridos de cada versión intermedia. El destino de abajo es 1.20.3; no es un salto directo compatible desde los ejemplos antiguos de 1.16/1.17.

Registre la **versión menor instalada inicialmente** para `upgradeCompatibility`, no una versión de destino/actual seleccionada arbitrariamente. Exporte los valores existentes del usuario, revise las claves renombradas/eliminadas y guarde la configuración revisada como `reviewed-values.yaml`. Mantenga este archivo y los valores exportados en privado si contienen material sensible:

```bash
set -eu
umask 077
CILIUM_TARGET_VERSION=1.20.3
: "${INITIAL_CILIUM_MINOR:?Set the initial installed Cilium minor, for example 1.19}"
helm get values cilium -n kube-system -o yaml > old-values.yaml
helm history cilium -n kube-system
helm repo add cilium https://helm.cilium.io/
helm repo update cilium
test -s reviewed-values.yaml
helm template cilium cilium/cilium -n kube-system \
  --version "$CILIUM_TARGET_VERSION" -f reviewed-values.yaml \
  --set-string "upgradeCompatibility=$INITIAL_CILIUM_MINOR" > candidate.yaml
```

Antes del siguiente paso, revise los recursos generados y el procedimiento oficial de comprobación previa. `helm diff` es un complemento opcional que se instala por separado, no una función integrada de Helm. Evite `--reuse-values` al cambiar de versión; puede ocultar los valores predeterminados nuevos del chart.

Solo después de confirmar una ruta compatible y un plan de mantenimiento/recuperación, la misma sesión de shell puede realizar el cambio revisado:

```bash
set -eu
: "${CILIUM_TARGET_VERSION:?Use the previously reviewed target version}"
: "${INITIAL_CILIUM_MINOR:?Use the previously reviewed initial installed minor}"
helm upgrade cilium cilium/cilium -n kube-system \
  --version "$CILIUM_TARGET_VERSION" -f reviewed-values.yaml \
  --set-string "upgradeCompatibility=$INITIAL_CILIUM_MINOR" --wait --timeout 10m
cilium status --wait
kubectl -n kube-system get daemonset cilium cilium-envoy
kubectl -n kube-system get deployment cilium-operator hubble-relay
```

`cilium connectivity test` es una validación **activa** útil: crea cargas de prueba y tráfico de red. Ejecútela en el entorno de prueba planificado, no como si fuera un comando de estado de solo lectura. Compruebe también las pruebas negativas de políticas específicas de la aplicación y las conexiones de larga duración, además de la disponibilidad de los componentes.

### Estrategia canary

Una etiqueta de nodo por sí sola no selecciona una versión distinta de Cilium. No despliegue un segundo DaemonSet de Cilium que se superponga para crear un canary: los Agents comparten recursos de red a nivel de nodo y la configuración del clúster. Primero valide la versión en un clúster de pruebas representativo. Cualquier actualización controlada por nodo debe usar un mecanismo compatible de propietario único, tener en cuenta los cambios de Operator/ConfigMap compartidos y limitar la diferencia temporal de versiones. En estado estable, todos los componentes de Cilium deben ejecutar la misma versión.

### Reversión

Elija una revisión de Helm **cuya compatibilidad se haya revisado**, después de comprobar si los CRD, funciones o estados nuevos impiden volver a una versión anterior de forma segura:

```bash
set -eu
helm history cilium -n kube-system
: "${CILIUM_ROLLBACK_REVISION:?Set the reviewed, compatible Helm revision}"
helm rollback cilium "$CILIUM_ROLLBACK_REVISION" \
  -n kube-system --wait --timeout 10m
cilium status --wait
```

No vuelva a una versión anterior a 1.15 a ciegas ni suponga que la reversión de una revisión de Helm deshace los cambios de red de los nodos, los esquemas de CRD y todas las funciones utilizadas recientemente. Conserve los prerrequisitos de reversión específicos de la versión y las pruebas de recuperación junto con el cambio.

## Solución de problemas

### Estado de nodos y políticas

```bash
cilium status --wait
kubectl -n kube-system get pods -l k8s-app=cilium -o wide
kubectl -n kube-system exec ds/cilium -- cilium-dbg endpoint list
kubectl -n kube-system exec ds/cilium -- cilium-dbg policy get
kubectl -n kube-system exec ds/cilium -- cilium-dbg service list
kubectl -n kube-system exec ds/cilium -- cilium-dbg bpf ct list global
```

La CLI `cilium` del host administra la instalación; `cilium-dbg` dentro de un Agent inspecciona el estado local del datapath. `exec ds/cilium` elige un Pod; durante un incidente, diríjase al Pod del nodo realmente afectado. Enumerar entradas CT puede producir mucha salida; `wc -l` no es una medición fiable de ocupación.

### Envoy y latencia

```bash
kubectl -n kube-system exec ds/cilium -- cilium-dbg status --verbose
kubectl -n kube-system exec ds/cilium -- cilium-dbg envoy admin config listeners
kubectl -n kube-system exec ds/cilium -- cilium-dbg envoy admin config routes
kubectl -n kube-system exec ds/cilium -- cilium-dbg envoy admin config clusters
kubectl -n kube-system exec ds/cilium -- cilium-dbg envoy admin metrics
```

Use la ruta compatible del comando/socket administrativo, en lugar de dar por sentado que hay un listener TCP sin autenticación en el puerto 9901 o un binario `curl` dentro del contenedor. Distinga entre ausencia de redirección L7, upstream no disponible, denegación por política, saturación de conexiones y respuestas lentas de la aplicación. Use la unidad y las etiquetas correctas del histograma observado según las guías de Ingress/Gateway y observabilidad.

### Depuración temporal y registros

```yaml
debug:
  enabled: true
  verbose: flow envoy policy
```

`debug.verbose` es una cadena separada por espacios, no un mapa de valores booleanos. Durante una investigación acotada, habilite solo los grupos necesarios y después restaure el nivel de registro original.

```bash
kubectl -n kube-system logs -l k8s-app=cilium -c cilium-agent --since=30m --tail=1000
kubectl -n kube-system logs -l k8s-app=cilium-envoy -c cilium-envoy --since=30m --tail=1000
cilium sysdump --output-filename cilium-audit
```

El DaemonSet independiente de Envoy usa el selector `k8s-app=cilium-envoy`. Un sysdump recopila datos con acceso al clúster y puede incluir configuración/registros sensibles; inspeccione el archivo antes de compartirlo. No es una invocación directa de `cilium-bugtool` en el host.

## Guía específica para EKS

### Modo ENI y encadenamiento de AWS VPC CNI

Son diseños distintos. El IPAM ENI de Cilium administra interfaces y direcciones mediante su Operator; el encadenamiento de AWS VPC CNI deja la asignación de direcciones en manos de AWS VPC CNI y tiene sus propias limitaciones de L7/cifrado. Use el procedimiento de instalación que corresponda.

Una superposición IPv4 de ENI es:

```yaml
eni:
  enabled: true
ipam:
  mode: eni
routingMode: native
ipv4:
  enabled: true
ipv6:
  enabled: false
cluster:
  name: example-cluster
```

`eni.enabled` selecciona el comportamiento del Operator de AWS y los valores predeterminados asociados del chart. Use un nombre de clúster único para evitar que la propiedad de la recolección de ENI resulte ambigua. No añada un rango universal de cluster-pool `10.0.0.0/8` al modo ENI ni fije una interfaz de masquerade sin comprobar los dispositivos reales de los nodos y los requisitos de enrutamiento.

`enableAWSSecurityGroups` no es un valor del chart. Los grupos de seguridad de ENI proceden de `eni.nodeSpec.securityGroups`/`securityGroupTags`, que sí son compatibles, o del comportamiento de herencia documentado. Esto no traduce automáticamente políticas de Kubernetes en objetos AWS SecurityGroupPolicy.

La **referencia general de IPAM ENI documenta IPv6 como Beta**, incluidos los prerrequisitos de subred/prefijo dual-stack y de IAM, mientras que la página de instalación de EKS para 1.20.3 aún indica solo IPv4. Este ejemplo usa IPv4 deliberadamente y deja constancia de esa discrepancia entre fuentes. No oculte la función Beta ni afirme que la referencia general por sí sola proporciona una receta IPv6 de EKS completamente validada.

EKS Auto Mode y Fargate no admiten esta ruta de instalación de un DaemonSet CNI alternativo. EKS Hybrid Nodes tiene su propia guía y matriz de compatibilidad de Cilium respaldadas por AWS; no transfiera esa afirmación de compatibilidad a cualquier versión de Cilium autogestionada en EC2.

### Sistema operativo y capacidad de nodos

EKS dejó de publicar AMI optimizadas para EKS basadas en AL2 el **26 de noviembre de 2025**; la serie 1.32 fue la última de Kubernetes para esas AMI. Elija una AMI AL2023 o Bottlerocket compatible y compruebe el kernel y la arquitectura reales, además de los requisitos de las funciones de Cilium. Una mención general de AL2 en una tabla de compatibilidad de Linux no representa el ciclo de vida vigente de las AMI de EKS.

Elija familias y tamaños de instancias a partir de CPU, memoria, límites de red/paquetes, capacidad ENI/IP, disponibilidad y coste medidos. La antigua recomendación fija de m6i/c6i/r6i no era un benchmark de dimensionamiento. Si usa arquitecturas mixtas, verifique cada imagen de DaemonSet y carga de trabajo en AMD64 y Arm64.

### IAM

Use un rol dedicado al Operator de Cilium mediante el mecanismo de identidad compatible de la instalación; revise por separado su política de confianza y el acceso a credenciales. A la política anterior le faltaban operaciones requeridas, como `AttachNetworkInterface`, `DescribeInstanceTypes`, `DescribeRouteTables` y `CreateTags`, por lo que no era una política completa para asignar ENI.

La referencia ENI versionada enumera permisos de API básicos y condicionales. Tenga en cuenta la recolección de ENI, la liberación de IP excedentes, los filtros de instancias y la asignación IPv6 opcional. Separe permisos de lectura/listado y de modificación según la compatibilidad de autorización de cada servicio de AWS; limite las modificaciones compatibles a la región/recursos/etiquetas previstos. Algunas operaciones describe requieren `Resource: "*"`; el comodín por sí solo no demuestra ni que los permisos sean correctos ni que sean excesivos. Una política completa de privilegio mínimo requiere además el contexto IAM/de recursos real de la cuenta y validar las API; esta guía no afirma haber aprovisionado una.

## Lecturas adicionales

Continúe con las guías completas de [seguridad](./03-security.md), [observabilidad](./04-observability.md) e [Ingress/Gateway](./05-ingress-gateway.md) para consultar sus prerrequisitos y ejemplos.

- [Valores Helm de Cilium 1.20.3](https://github.com/cilium/cilium/blob/v1.20.3/install/kubernetes/cilium/values.yaml)
- [Requisitos del sistema](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/operations/system_requirements.rst)
- [Ajuste del rendimiento](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/operations/performance/tuning.rst)
- [Procedimiento de actualización](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/operations/upgrade.rst)
- [Restricciones de actualización y reversión](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/operations/upgrade-warning.rst)
- [Integración con Istio](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/servicemesh/istio.rst)
- [Migración de CNI](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/installation/k8s-install-migration.rst)
- [Analizador de recursos CEC](https://github.com/cilium/cilium/blob/v1.20.3/pkg/ciliumenvoyconfig/cec_resource_parser.go)
- [Asignación ENI, grupos de seguridad y permisos](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/concepts/ipam/eni.rst)
- [Advertencias de instalación en EKS](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/installation/requirements-eks.rst)
- [Retirada de AMI AL2 de EKS](https://docs.aws.amazon.com/eks/latest/userguide/eks-ami-deprecation-faqs.html)
- [Compatibilidad de CNI alternativos en EKS](https://docs.aws.amazon.com/eks/latest/userguide/alternate-cni-plugins.html)
- [Diagnóstico de Envoy de Cilium](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/cmdref/cilium-dbg_envoy_admin_config.md)
- [Sysctls TCP de Linux](https://docs.kernel.org/networking/ip-sysctl.html)
- [Presupuestos de interrupción de Kubernetes](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/)
- [Diagnóstico de permisos IAM a nivel de recurso](https://docs.aws.amazon.com/IAM/latest/UserGuide/troubleshoot_policies.html)
