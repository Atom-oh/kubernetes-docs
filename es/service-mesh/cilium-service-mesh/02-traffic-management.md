# Gestión del tráfico en Cilium Service Mesh {#cilium-service-mesh-traffic-management}

> **Versiones de referencia revisadas**: Cilium 1.20.3 y Gateway API 1.6.3, 16 de octubre de 2026. Consulte la [descripción general](./README.md) para conocer las matrices de pruebas de Kubernetes/EKS y los requisitos de cada plataforma.

## Descripción general {#overview}

La gestión del tráfico en Cilium Service Mesh combina el balanceo de carga L4 basado en eBPF con el enrutamiento L7 mediante Envoy. Este capítulo explica las funciones avanzadas de gestión del tráfico mediante CiliumEnvoyConfig, las reglas L7 de CiliumNetworkPolicy y la integración con Gateway API.

## Arquitectura de gestión del tráfico {#traffic-management-architecture}

![Una solicitud del cliente atraviesa tres capas de gestión del tráfico de Cilium —enrutamiento HTTP L7 con Envoy, balanceo de carga L4 con eBPF y enrutamiento IP L3 con eBPF— antes de llegar al servidor. Las demás funciones de cada capa se agrupan junto a ella.](../../.gitbook/assets/en-service-mesh-cilium-service-mesh-02-traffic-management-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-cilium-service-mesh-02-traffic-management-0.html)

El diagrama agrupa las funciones por capas; no impone un orden de procesamiento de paquetes. El tráfico que solo necesita L3/L4 puede evitar Envoy. La ruta real de salida, entrada o acceso a un Service depende de la configuración.

## CiliumEnvoyConfig {#ciliumenvoyconfig}

Estos son **ejemplos de configuración independientes**, no recursos que deban instalarse juntos. Varios ejemplos usan el mismo Service de entrada; asigne un único responsable de configuración para evitar conflictos entre listeners. Los ejemplos requieren una instalación de Cilium preparada con `l7Proxy: true`, `envoyConfig.enabled: true`, los ajustes adecuados de sustitución de kube-proxy y enrutamiento, y las CRD necesarias.

Cada Service de entrada o de backend mencionado debe existir previamente en `default`, con el puerto **8080**, los selectores adecuados y endpoints HTTP listos. Las secciones de Kafka y gRPC especifican sus propios requisitos de espacio de nombres y puerto. Los ejemplos de CEC no crean cargas de trabajo, Services ni certificados.

`services` selecciona un Service de entrada para redirigir su tráfico y sincroniza sus backends. `backendServices` sincroniza otros backends sin redirigir el tráfico de entrada de sus propios Services. También deben existir los recursos Cluster de EDS. Cilium proporciona deliberadamente las direcciones de Listener y las fuentes xDS omitidas. Que Kubernetes acepte el recurso no basta: examine los errores del agente y de Envoy y compruebe solicitudes reales. Consulte el [capítulo de arquitectura](./01-architecture.md) para conocer los límites de responsabilidad y validación.

### Estructura básica {#basic-structure}

CiliumEnvoyConfig define la configuración de Envoy para Services concretos:

```yaml
apiVersion: cilium.io/v2
kind: CiliumEnvoyConfig
metadata:
  name: my-service-config
  namespace: default
spec:
  services:
  - name: my-service
    namespace: default
    ports:
    - 8080
  backendServices:
  - name: backend-v1
    namespace: default
  - name: backend-v2
    namespace: default
  resources:
  - '@type': type.googleapis.com/envoy.config.listener.v3.Listener
    name: my-service-listener
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: my-service-listener
          route_config:
            name: my-service-listener-routes
            virtual_hosts:
            - name: api
              domains:
              - '*'
              routes:
              - match:
                  prefix: /
                route:
                  weighted_clusters:
                    clusters:
                    - name: default/backend-v1
                      weight: 50
                    - name: default/backend-v2
                      weight: 50
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/backend-v1
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/backend-v2
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
```

Este ejemplo completo distribuye las solicitudes entre dos backends identificados de forma explícita. El Listener, la ruta HTTP y los Clusters de EDS son componentes distintos: enumerar los Services de backend no define por sí solo esos Clusters.

### Enrutamiento HTTP {#http-routing}

#### Enrutamiento por ruta {#path-based-routing}

```yaml
apiVersion: cilium.io/v2
kind: CiliumEnvoyConfig
metadata:
  name: path-routing
  namespace: default
spec:
  services:
  - name: api-gateway
    namespace: default
    ports:
    - 8080
  backendServices:
  - name: users-service
    namespace: default
  - name: orders-service
    namespace: default
  - name: products-service
    namespace: default
  resources:
  - '@type': type.googleapis.com/envoy.config.listener.v3.Listener
    name: api-gateway-listener
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: api-gateway
          codec_type: AUTO
          route_config:
            name: api_routes
            virtual_hosts:
            - name: api
              domains:
              - '*'
              routes:
              - match:
                  path_separated_prefix: /users
                route:
                  cluster: default/users-service
              - match:
                  path_separated_prefix: /orders
                route:
                  cluster: default/orders-service
              - match:
                  path_separated_prefix: /products
                route:
                  cluster: default/products-service
              - match:
                  prefix: /
                direct_response:
                  status: 404
                  body:
                    inline_string: Not Found
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/orders-service
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/products-service
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/users-service
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
```

Envoy evalúa estas rutas en el orden mostrado. `path_separated_prefix` coincide con `/users` y `/users/123`, pero no con `/users-old`. La regla final `/` atiende las solicitudes que no coinciden con las anteriores. Este comportamiento difiere de la coincidencia con cualquier prefijo de cadena.

#### Enrutamiento por encabezados {#header-based-routing}

```yaml
apiVersion: cilium.io/v2
kind: CiliumEnvoyConfig
metadata:
  name: header-routing
  namespace: default
spec:
  services:
  - name: api-service
    namespace: default
    ports:
    - 8080
  backendServices:
  - name: api-v1
    namespace: default
  - name: api-v2
    namespace: default
  - name: api-beta
    namespace: default
  resources:
  - '@type': type.googleapis.com/envoy.config.listener.v3.Listener
    name: header-routing-listener
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: api-service
          route_config:
            name: header_routes
            virtual_hosts:
            - name: api
              domains:
              - '*'
              routes:
              - match:
                  prefix: /
                  headers:
                  - name: X-API-Version
                    string_match:
                      exact: v2
                route:
                  cluster: default/api-v2
              - match:
                  prefix: /
                  headers:
                  - name: X-Beta-User
                    string_match:
                      exact: 'true'
                route:
                  cluster: default/api-beta
              - match:
                  prefix: /
                route:
                  cluster: default/api-v1
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/api-beta
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/api-v1
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/api-v2
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
```

Se usa la primera regla que coincida: una solicitud con ambos encabezados selecciona v2. Los encabezados de versión o beta controlados por el cliente orientan el enrutamiento; no demuestran que el usuario esté autorizado a acceder a ese backend.

#### Enrutamiento por método {#method-based-routing}

```yaml
apiVersion: cilium.io/v2
kind: CiliumEnvoyConfig
metadata:
  name: method-routing
  namespace: default
spec:
  services:
  - name: rest-api
    namespace: default
    ports:
    - 8080
  backendServices:
  - name: read-service
    namespace: default
  - name: write-service
    namespace: default
  resources:
  - '@type': type.googleapis.com/envoy.config.listener.v3.Listener
    name: method-routing-listener
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: rest-api
          route_config:
            name: method_routes
            virtual_hosts:
            - name: api
              domains:
              - '*'
              routes:
              - match:
                  prefix: /
                  headers:
                  - name: :method
                    string_match:
                      safe_regex:
                        google_re2: {}
                        regex: ^(GET|HEAD)$
                route:
                  cluster: default/read-service
              - match:
                  prefix: /
                  headers:
                  - name: :method
                    string_match:
                      safe_regex:
                        google_re2: {}
                        regex: ^(POST|PUT|DELETE|PATCH)$
                route:
                  cluster: default/write-service
              - match:
                  prefix: /
                direct_response:
                  status: 405
                response_headers_to_add:
                - header:
                    key: allow
                    value: GET, HEAD, POST, PUT, DELETE, PATCH
                  append_action: OVERWRITE_IF_EXISTS_OR_ADD
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/read-service
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/write-service
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
```

GET y HEAD seleccionan el Service de lectura; POST, PUT, DELETE y PATCH seleccionan el de escritura. Los demás métodos reciben una respuesta 405. Configure de forma explícita OPTIONS/CORS o cualquier comportamiento específico que necesite la aplicación. Enviar una escritura a un backend dedicado no implementa por sí solo autorización ni idempotencia.

## Políticas de tráfico L7 {#l7-traffic-policies}

### Reglas L7 de CiliumNetworkPolicy {#ciliumnetworkpolicy-l7-rules}

CiliumNetworkPolicy permite controlar el tráfico de forma precisa en la capa L7:

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: l7-http-policy
  namespace: default
spec:
  endpointSelector:
    matchLabels:
      k8s:app: backend-api
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:app: frontend
        k8s:io.kubernetes.pod.namespace: default
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
      rules:
        http:
        - method: ^GET$
          path: ^/api/users/.*$
        - method: ^GET$
          path: ^/api/products/.*$
        - method: ^POST$
          path: ^/api/orders$
        - method: ^GET$
          path: ^/api/admin/.*$
          headerMatches:
          - name: X-API-Version
            value: v1
```

Las reglas son alternativas; la condición del encabezado solo se aplica a la regla de la ruta de administración. `X-API-Version: v1` es una condición exacta de versión o enrutamiento, no una credencial de administrador. Implemente la autenticación y la autorización de usuarios en la aplicación. La política selecciona el tráfico de entrada del espacio de nombres indicado; otras políticas aplicables pueden ampliar los permisos.

### Compatibilidad con distintos protocolos {#various-protocol-support}

#### Kafka: límites de red y ACL del broker {#kafka-network-boundaries-and-broker-acls}

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: kafka-l4-policy
  namespace: kafka
spec:
  endpointSelector:
    matchLabels:
      k8s:app: kafka-broker
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:app: kafka-producer
        k8s:io.kubernetes.pod.namespace: kafka
    toPorts:
    - ports:
      - port: '9092'
        protocol: TCP
  - fromEndpoints:
    - matchLabels:
        k8s:app: kafka-consumer
        k8s:io.kubernetes.pod.namespace: kafka
    toPorts:
    - ports:
      - port: '9092'
        protocol: TCP
```

La API de políticas L7 de Cilium 1.20.3 admite HTTP y DNS; la antigua API `rules.kafka` ya no existe. La CRD publicada rechaza ese objeto de reglas de Kafka. Eliminar sus reglas L7 solo dejaría permisos L4, sin autorización por tema. El ejemplo de sustitución únicamente permite que los clientes enumerados se conecten al listener del broker, previamente configurado en TCP 9092. Configure por separado TLS/SASL de Kafka y las ACL del broker para los temas, los grupos de consumidores y las operaciones. Aquí, la política de red no puede distinguir entre producir y recuperar mensajes.

#### Política L7 de DNS {#dns-l7-policy}

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: dns-l7-policy
  namespace: default
spec:
  endpointSelector:
    matchLabels:
      k8s:app: web-app
  egress:
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
        k8s:k8s-app: kube-dns
    toPorts:
    - ports:
      - port: '53'
        protocol: UDP
      - port: '53'
        protocol: TCP
      rules:
        dns:
        - matchPattern: '*.example.com'
        - matchPattern: api.external-service.io
        - matchName: database.internal.svc.cluster.local
```

Este ejemplo permite **únicamente consultas DNS**, por UDP y TCP, al resolver del clúster seleccionado. No permite conexiones HTTPS ni de base de datos a las direcciones obtenidas; añada reglas separadas de `toFQDNs` o endpoints y puertos para los destinos previstos. `*.example.com` no incluye el dominio raíz `example.com` ni cualquier subdominio anidado. Tenga también en cuenta las consultas de la lista de búsqueda del resolver. NodeLocal DNS requiere una regla de destino distinta y verificada. Restringir los nombres no garantiza la protección frente a la exfiltración de datos, DoH ni el uso indebido de los dominios permitidos.

#### Política L7 de gRPC {#grpc-l7-policy}

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: grpc-l7-policy
  namespace: default
spec:
  endpointSelector:
    matchLabels:
      k8s:app: grpc-server
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:app: grpc-client
        k8s:io.kubernetes.pod.namespace: default
    toPorts:
    - ports:
      - port: '50051'
        protocol: TCP
      rules:
        http:
        - method: ^POST$
          path: ^/myapp\.UserService/GetUser$
        - method: ^POST$
          path: ^/myapp\.UserService/ListUsers$
        - method: ^POST$
          path: ^/myapp\.OrderService/.*$
```

Estas reglas HTTP/2 coinciden con la ruta gRPC `POST /package.Service/Method`. El punto del nombre del paquete está escapado y las expresiones están ancladas. Se requiere una ruta HTTP/2 compatible que pueda inspeccionarse; el tráfico cifrado de la aplicación necesita la configuración TLS correspondiente. Los métodos de salud, reflexión y demás métodos no quedan permitidos de forma implícita. La política HTTP tampoco puede autorizar campos dentro de un mensaje protobuf.

## Balanceo de carga {#load-balancing}

### Balanceo de carga L4 con eBPF {#l4-load-balancing-ebpf}

El balanceo de carga L4 basado en eBPF sustituye a kube-proxy:

```yaml
kubeProxyReplacement: true
k8sServiceHost: <reachable-api-server-host>
k8sServicePort: 6443
loadBalancer:
  algorithm: maglev
  mode: snat
nodePort:
  enableHealthCheck: true
```

El endpoint de la API debe ser accesible durante el arranque. Use su puerto real, normalmente 443 en EKS, y conserve los ajustes de IPAM y enrutamiento de la plataforma elegida. `nodePort.enableHealthCheck` es la clave del chart; la antigua `loadBalancer.healthCheckNodePort` no la configuraba. `loadBalancer.serviceTopology` se refiere al enrutamiento según la topología, no a la afinidad de sesión ClientIP. Las combinaciones de despacho y enrutamiento DSR requieren un diseño aparte. Las opciones de despacho documentadas son `opt` y `geneve`, no `ipip`. Consulte la [explicación de arquitectura](./01-architecture.md#kube-proxy-replacement).

#### Hashing Maglev {#maglev-hashing}

Maglev asigna una clave de flujo a un backend mediante una tabla de consulta para el tráfico externo al que se aplica. Minimiza la reasignación cuando cambia el conjunto de backends; no conserva una sesión en un backend eliminado ni sustituye a `Service.spec.sessionAffinity: ClientIP`.

El tamaño predeterminado de la tabla Maglev de eBPF en Cilium 1.20.3 es **16.381**. Entre los tamaños admitidos está **65.521**. En cambio, **65.537** corresponde al ejemplo independiente de MAGLEV de Envoy que aparece más adelante y no es un valor admitido de `maglev.tableSize` en Cilium. Todos los nodos deben tener una configuración coherente. La traducción de Services entre cargas internas a nivel de socket no pasa por esta ruta de Maglev.

### Balanceo de carga L7 con Envoy {#l7-load-balancing-envoy}

Envoy proporciona el balanceo de carga L7:

```yaml
apiVersion: cilium.io/v2
kind: CiliumEnvoyConfig
metadata:
  name: l7-load-balancing
  namespace: default
spec:
  services:
  - name: api-service
    namespace: default
    ports:
    - 8080
  backendServices:
  - name: api-backend
    namespace: default
  resources:
  - '@type': type.googleapis.com/envoy.config.listener.v3.Listener
    name: l7-load-balancer
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: l7-load-balancer
          route_config:
            name: l7-load-balancer-routes
            virtual_hosts:
            - name: api
              domains:
              - '*'
              routes:
              - match:
                  prefix: /
                route:
                  cluster: default/api-backend
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/api-backend
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
    outlier_detection:
      consecutive_5xx: 5
      interval: 10s
      base_ejection_time: 30s
      max_ejection_percent: 50
    health_checks:
    - timeout: 5s
      interval: 10s
      unhealthy_threshold: 3
      healthy_threshold: 2
      http_health_check:
        path: /health
        expected_statuses:
        - start: 200
          end: 300
    circuit_breakers:
      thresholds:
      - priority: DEFAULT
        max_connections: 1000
        max_pending_requests: 1000
        max_requests: 1000
        max_retries: 3
```

Las sondas activas de `/health`, la detección pasiva de endpoints anómalos y los límites de capacidad del mecanismo de circuit breaker son distintos. El intervalo de estados HTTP saludables es `[200, 300)`, por lo que incluye 299. El backend debe implementar el endpoint de salud y la política debe permitir la ruta de la sonda. La expulsión de endpoints anómalos no garantiza que todas las solicitudes eviten un endpoint averiado. `max_retries` en `circuit_breakers.thresholds` limita los recursos de reintento concurrentes; no indica el número de reintentos de cada solicitud.

#### Opciones de algoritmo de balanceo de carga {#load-balancing-algorithm-options}

Elija **un solo** fragmento de Cluster de los siguientes. Son alternativas, no un único objeto YAML con claves `lb_policy` repetidas. RING_HASH y MAGLEV también necesitan una `hash_policy` adecuada en la ruta si las solicitudes deben usar siempre una clave de aplicación. Si no se proporciona un hash, la selección puede recurrir a una clave aleatoria. La tabla MAGLEV L7 de Envoy es distinta de la tabla Maglev eBPF de Cilium.

```yaml
lb_policy: ROUND_ROBIN
```

```yaml
lb_policy: LEAST_REQUEST
least_request_lb_config:
  choice_count: 2
```

```yaml
lb_policy: RANDOM
```

```yaml
lb_policy: RING_HASH
ring_hash_lb_config:
  hash_function: XX_HASH
  minimum_ring_size: 1024
  maximum_ring_size: 8388608
```

```yaml
lb_policy: MAGLEV
maglev_lb_config:
  table_size: 65537
```

## Distribución del tráfico para despliegues canary {#traffic-splitting-canary-deployment}

### Distribución del tráfico por pesos {#weight-based-traffic-splitting}

```yaml
apiVersion: cilium.io/v2
kind: CiliumEnvoyConfig
metadata:
  name: canary-deployment
  namespace: default
spec:
  services:
  - name: frontend
    namespace: default
    ports:
    - 8080
  backendServices:
  - name: frontend-stable
    namespace: default
  - name: frontend-canary
    namespace: default
  resources:
  - '@type': type.googleapis.com/envoy.config.listener.v3.Listener
    name: canary-listener
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: frontend
          route_config:
            name: canary_routes
            virtual_hosts:
            - name: frontend
              domains:
              - '*'
              routes:
              - match:
                  prefix: /
                route:
                  weighted_clusters:
                    clusters:
                    - name: default/frontend-stable
                      weight: 90
                    - name: default/frontend-canary
                      weight: 10
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/frontend-canary
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/frontend-stable
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
```

Los pesos 90 y 10 expresan probabilidades relativas de selección; no garantizan un reparto exacto en cada grupo de diez solicitudes ni por usuario o sesión. La versión actual de Envoy usa la suma de los pesos; se omite el campo obsoleto `total_weight`. Esta configuración solo selecciona tráfico y no incluye un ciclo automático de análisis de salud, promoción ni reversión.

### Selección de canary mediante encabezados {#header-based-canary}

```yaml
apiVersion: cilium.io/v2
kind: CiliumEnvoyConfig
metadata:
  name: header-canary
  namespace: default
spec:
  services:
  - name: api
    namespace: default
    ports:
    - 8080
  backendServices:
  - name: api-stable
    namespace: default
  - name: api-canary
    namespace: default
  resources:
  - '@type': type.googleapis.com/envoy.config.listener.v3.Listener
    name: header-canary-listener
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: api
          route_config:
            name: header_canary_routes
            virtual_hosts:
            - name: api
              domains:
              - '*'
              routes:
              - match:
                  prefix: /
                  headers:
                  - name: X-Canary
                    string_match:
                      exact: 'true'
                route:
                  cluster: default/api-canary
              - match:
                  prefix: /
                route:
                  cluster: default/api-stable
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/api-canary
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/api-stable
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
```

Solo el valor exacto `X-Canary: true` selecciona canary; las demás solicitudes seleccionan stable. Trate este encabezado como un dato no fiable salvo que un punto de control autenticado controle su valor. Incluya en el plan de despliegue los requisitos de estado y compatibilidad de las aplicaciones stable y canary.

## Reintentos y tiempos de espera {#retry-and-timeout}

### Configuración de reintentos {#retry-configuration}

```yaml
apiVersion: cilium.io/v2
kind: CiliumEnvoyConfig
metadata:
  name: retry-config
  namespace: default
spec:
  services:
  - name: api-service
    namespace: default
    ports:
    - 8080
  backendServices:
  - name: api-backend
    namespace: default
  resources:
  - '@type': type.googleapis.com/envoy.config.listener.v3.Listener
    name: retry-listener
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: api-service
          route_config:
            name: retry_routes
            virtual_hosts:
            - name: api
              domains:
              - '*'
              routes:
              - match:
                  prefix: /
                  headers:
                  - name: :method
                    string_match:
                      exact: GET
                route:
                  cluster: default/api-backend
                  timeout: 7s
                  retry_policy:
                    retry_on: 5xx,reset,connect-failure
                    num_retries: 2
                    per_try_timeout: 2s
                    retry_back_off:
                      base_interval: 0.025s
                      max_interval: 0.25s
                    retriable_request_headers:
                    - name: :method
                      string_match:
                        exact: GET
              - match:
                  prefix: /
                route:
                  cluster: default/api-backend
                  timeout: 7s
                  retry_policy:
                    num_retries: 0
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
          early_header_mutation_extensions:
          - name: envoy.http.early_header_mutation.header_mutation
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.http.early_header_mutation.header_mutation.v3.HeaderMutation
              mutations:
              - remove: x-envoy-retry-on
              - remove: x-envoy-retry-grpc-on
              - remove: x-envoy-max-retries
              - remove: x-envoy-hedge-on-per-try-timeout
              - remove: x-envoy-retriable-header-names
              - remove: x-envoy-retriable-status-codes
              - remove: x-envoy-upstream-rq-timeout-ms
              - remove: x-envoy-upstream-rq-per-try-timeout-ms
              - remove: x-envoy-expected-rq-timeout-ms
              - remove: x-envoy-upstream-stream-duration-ms
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/api-backend
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
```

Solo las solicitudes GET se reintentan: como máximo **dos intentos adicionales**, con dos segundos de tiempo de espera por intento y siete segundos para la ruta. El tiempo de espera por intento también se aplica al intento inicial; no es la pausa entre reintentos. El retroceso entre reintentos se configura por separado. La ruta para las solicitudes distintas de GET establece explícitamente `num_retries: 0`.

La extensión de modificación temprana de encabezados elimina los encabezados que permiten sobrescribir los reintentos y tiempos de espera de Envoy antes del enrutamiento y del cálculo del tiempo de espera. Está compilada en la imagen del proxy de Cilium 1.20.3; los filtros HTTP habituales `header_mutation` y Lua no están habilitados en esa compilación. La antigua extensión de prioridad de reintentos `previous_priorities` tampoco está disponible en esta imagen. No dé por hecho que todas las extensiones del proyecto Envoy están disponibles en esta imagen.

Use este ejemplo con endpoints HTTP cuya operación GET pueda repetirse de forma segura. La aplicación, el cliente u otro proxy pueden reintentar de manera independiente. Mantenga las escrituras con un único intento salvo que la aplicación disponga de un mecanismo de idempotencia revisado. `retriable_headers` se refiere a los encabezados de la **respuesta del upstream** y se consulta con `retry_on: retriable-headers`; `retriable_request_headers`, en cambio, restringe qué solicitudes pueden reintentarse. Estos campos no son intercambiables. `retriable-4xx` no implica reintentar todas las respuestas 4xx.

### Configuración de tiempos de espera {#timeout-configuration}

```yaml
apiVersion: cilium.io/v2
kind: CiliumEnvoyConfig
metadata:
  name: timeout-config
  namespace: default
spec:
  services:
  - name: slow-service
    namespace: default
    ports:
    - 8080
  resources:
  - '@type': type.googleapis.com/envoy.config.listener.v3.Listener
    name: timeout-listener
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: slow-service
          common_http_protocol_options:
            idle_timeout: 300s
            headers_with_underscores_action: REJECT_REQUEST
          stream_idle_timeout: 60s
          request_timeout: 0s
          route_config:
            name: timeout_routes
            virtual_hosts:
            - name: slow-service
              domains:
              - '*'
              routes:
              - match:
                  path_separated_prefix: /long-running
                route:
                  cluster: default/slow-service
                  timeout: 300s
                  idle_timeout: 300s
                  retry_policy:
                    num_retries: 0
              - match:
                  path_separated_prefix: /stream
                route:
                  cluster: default/slow-service
                  timeout: 0s
                  idle_timeout: 60s
                  retry_policy:
                    num_retries: 0
              - match:
                  prefix: /
                route:
                  cluster: default/slow-service
                  timeout: 60s
                  retry_policy:
                    num_retries: 0
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
          early_header_mutation_extensions:
          - name: envoy.http.early_header_mutation.header_mutation
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.http.early_header_mutation.header_mutation.v3.HeaderMutation
              mutations:
              - remove: x-envoy-retry-on
              - remove: x-envoy-retry-grpc-on
              - remove: x-envoy-max-retries
              - remove: x-envoy-hedge-on-per-try-timeout
              - remove: x-envoy-retriable-header-names
              - remove: x-envoy-retriable-status-codes
              - remove: x-envoy-upstream-rq-timeout-ms
              - remove: x-envoy-upstream-rq-per-try-timeout-ms
              - remove: x-envoy-expected-rq-timeout-ms
              - remove: x-envoy-upstream-stream-duration-ms
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/slow-service
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
```

Las rutas específicas preceden a la ruta general: `/long-running` recibe un límite de 300 segundos para la ruta y la inactividad del flujo; `/stream` desactiva solo el tiempo de espera global de respuesta de la ruta y conserva un límite de inactividad de 60 segundos. Las demás rutas usan un tiempo de espera de 60 segundos. `/streaming` no coincide con `/stream`.

El `connect_timeout` del Cluster de destino limita el establecimiento de la conexión. `common_http_protocol_options.idle_timeout` limita la inactividad de la conexión con el cliente. El `request_timeout` del HCM limita la recepción de la solicitud del cliente, no el procesamiento del backend; aquí está desactivado para las solicitudes en streaming. Por ello, los servicios expuestos necesitan los controles correspondientes en el borde, los encabezados, el cuerpo y las conexiones. Un tiempo de inactividad de flujo distinto de cero, los plazos del cliente, los límites de infraestructura o la pérdida de conexión pueden seguir terminando un flujo. `timeout: 0s` no garantiza una conexión ilimitada.

## Limitación de la tasa de solicitudes {#rate-limiting}

### Limitación local de la tasa {#local-rate-limiting}

```yaml
apiVersion: cilium.io/v2
kind: CiliumEnvoyConfig
metadata:
  name: local-ratelimit
  namespace: default
spec:
  services:
  - name: api-service
    namespace: default
    ports:
    - 8080
  resources:
  - '@type': type.googleapis.com/envoy.config.listener.v3.Listener
    name: ratelimit-listener
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: api-service
          route_config:
            name: ratelimit_routes
            virtual_hosts:
            - name: api
              domains:
              - '*'
              routes:
              - match:
                  prefix: /
                route:
                  cluster: default/api-service
          http_filters:
          - name: envoy.filters.http.local_ratelimit
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
              stat_prefix: http_local_rate_limiter
              token_bucket:
                max_tokens: 1000
                tokens_per_fill: 100
                fill_interval: 1s
              status:
                code: TooManyRequests
              filter_enabled:
                default_value:
                  numerator: 100
                  denominator: HUNDRED
              filter_enforced:
                default_value:
                  numerator: 100
                  denominator: HUNDRED
              enable_x_ratelimit_headers: DRAFT_VERSION_03
              local_rate_limit_per_downstream_connection: false
          - name: envoy.filters.http.router
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/api-service
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
```

Este depósito de tokens admite una ráfaga de 1.000 y repone 100 tokens por segundo **en cada proceso Envoy**, de forma compartida entre sus workers. No es una cuota para todo el clúster. Los porcentajes de activación y aplicación son explícitos. `enable_x_ratelimit_headers: DRAFT_VERSION_03` solicita los encabezados reales del filtro con el límite, los tokens restantes y el reinicio. Una clave inventada de metadatos dinámicos no proporciona un recuento fiable de los tokens restantes.

### Limitación de la tasa por ruta {#per-route-rate-limiting}

```yaml
apiVersion: cilium.io/v2
kind: CiliumEnvoyConfig
metadata:
  name: per-route-ratelimit
  namespace: default
spec:
  services:
  - name: api-service
    namespace: default
    ports:
    - 8080
  resources:
  - '@type': type.googleapis.com/envoy.config.listener.v3.Listener
    name: per-route-ratelimit-listener
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: api-service
          route_config:
            name: ratelimit_routes
            virtual_hosts:
            - name: api
              domains:
              - '*'
              routes:
              - match:
                  path_separated_prefix: /auth
                route:
                  cluster: default/api-service
                typed_per_filter_config:
                  envoy.filters.http.local_ratelimit:
                    '@type': type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
                    stat_prefix: auth_rate_limiter
                    token_bucket:
                      max_tokens: 10
                      tokens_per_fill: 5
                      fill_interval: 60s
                    filter_enabled:
                      default_value:
                        numerator: 100
                        denominator: HUNDRED
                    filter_enforced:
                      default_value:
                        numerator: 100
                        denominator: HUNDRED
                    local_rate_limit_per_downstream_connection: false
                    enable_x_ratelimit_headers: DRAFT_VERSION_03
              - match:
                  path_separated_prefix: /search
                route:
                  cluster: default/api-service
                typed_per_filter_config:
                  envoy.filters.http.local_ratelimit:
                    '@type': type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
                    stat_prefix: search_rate_limiter
                    token_bucket:
                      max_tokens: 100
                      tokens_per_fill: 50
                      fill_interval: 1s
                    filter_enabled:
                      default_value:
                        numerator: 100
                        denominator: HUNDRED
                    filter_enforced:
                      default_value:
                        numerator: 100
                        denominator: HUNDRED
                    local_rate_limit_per_downstream_connection: false
                    enable_x_ratelimit_headers: DRAFT_VERSION_03
              - match:
                  prefix: /
                route:
                  cluster: default/api-service
                typed_per_filter_config:
                  envoy.filters.http.local_ratelimit:
                    '@type': type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
                    stat_prefix: default_rate_limiter
                    token_bucket:
                      max_tokens: 1000
                      tokens_per_fill: 100
                      fill_interval: 1s
                    filter_enabled:
                      default_value:
                        numerator: 100
                        denominator: HUNDRED
                    filter_enforced:
                      default_value:
                        numerator: 100
                        denominator: HUNDRED
                    local_rate_limit_per_downstream_connection: false
                    enable_x_ratelimit_headers: DRAFT_VERSION_03
          http_filters:
          - name: envoy.filters.http.local_ratelimit
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
              stat_prefix: http_local_rate_limiter
          - name: envoy.filters.http.router
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/api-service
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
```

Cada ruta proporciona una configuración local completa, incluidos los porcentajes de activación y aplicación. La ruta de autenticación admite una ráfaga de 10 y repone 5 tokens cada 60 segundos; la de búsqueda admite una ráfaga de 100 y repone 50 por segundo; la ruta predeterminada admite una ráfaga de 1.000 y repone 100 por segundo. Estos depósitos pertenecen a cada proceso, no son límites por usuario. Un depósito sin fracciones de activación y aplicación no impone, de forma predeterminada, un límite efectivo.

## Reescritura de URL y modificación de encabezados {#url-rewriting-and-header-manipulation}

### Reescritura de URL {#url-rewriting}

```yaml
apiVersion: cilium.io/v2
kind: CiliumEnvoyConfig
metadata:
  name: url-rewrite
  namespace: default
spec:
  services:
  - name: api-gateway
    namespace: default
    ports:
    - 8080
  backendServices:
  - name: users-service
    namespace: default
  resources:
  - '@type': type.googleapis.com/envoy.config.listener.v3.Listener
    name: rewrite-listener
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: api-gateway
          route_config:
            name: rewrite_routes
            virtual_hosts:
            - name: api
              domains:
              - '*'
              routes:
              - match:
                  path_separated_prefix: /api/v1/users
                route:
                  cluster: default/users-service
                  prefix_rewrite: /users
              - match:
                  safe_regex:
                    google_re2: {}
                    regex: ^/v([0-9]+)/(.*)$
                route:
                  cluster: default/users-service
                  regex_rewrite:
                    pattern:
                      google_re2: {}
                      regex: ^/v([0-9]+)/([^?]*)(\?.*)?$
                    substitution: /api/v\1/\2\3
              - match:
                  path: /legacy
                route:
                  cluster: default/users-service
                  host_rewrite_literal: legacy.internal.svc.cluster.local
                  prefix_rewrite: /
              - match:
                  prefix: /legacy/
                route:
                  cluster: default/users-service
                  host_rewrite_literal: legacy.internal.svc.cluster.local
                  prefix_rewrite: /
              - match:
                  prefix: /
                direct_response:
                  status: 404
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/users-service
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
```

`/api/v1/users/123` se convierte en `/users/123`; `/v2/users?active=1` se convierte en `/api/v2/users?active=1`, conservando la cadena de consulta existente. Las coincidencias separadas para la raíz y las rutas secundarias del prefijo antiguo evitan barras dobles accidentales. La reescritura del host cambia la autoridad HTTP enviada al Cluster seleccionado; no resuelve por sí sola un Service de backend distinto.

### Modificación de encabezados {#header-manipulation}

```yaml
apiVersion: cilium.io/v2
kind: CiliumEnvoyConfig
metadata:
  name: header-manipulation
  namespace: default
spec:
  services:
  - name: api-service
    namespace: default
    ports:
    - 8080
  resources:
  - '@type': type.googleapis.com/envoy.config.listener.v3.Listener
    name: header-listener
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: api-service
          route_config:
            name: header_routes
            virtual_hosts:
            - name: api
              domains:
              - '*'
              request_headers_to_add:
              - header:
                  key: X-Forwarded-By
                  value: cilium-envoy
                append_action: OVERWRITE_IF_EXISTS_OR_ADD
              response_headers_to_add:
              - header:
                  key: X-Served-By
                  value: cilium-service-mesh
                append_action: OVERWRITE_IF_EXISTS_OR_ADD
              response_headers_to_remove:
              - server
              - x-powered-by
              routes:
              - match:
                  prefix: /
                route:
                  cluster: default/api-service
                request_headers_to_add:
                - header:
                    key: X-Request-Start
                    value: '%START_TIME(%s.%3f)%'
                  append_action: OVERWRITE_IF_EXISTS_OR_ADD
                - header:
                    key: X-Envoy-Original-Path
                    value: '%REQ(:PATH)%'
                  append_action: OVERWRITE_IF_EXISTS_OR_ADD
                response_headers_to_add:
                - header:
                    key: X-Response-Time
                    value: '%RESPONSE_DURATION%ms'
                  append_action: OVERWRITE_IF_EXISTS_OR_ADD
                - header:
                    key: X-Upstream-Host
                    value: '%UPSTREAM_HOST%'
                  append_action: OVERWRITE_IF_EXISTS_OR_ADD
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/api-service
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
```

Las modificaciones de encabezados de la ruta deben colocarse junto a la acción `route`, no dentro de `RouteAction`. El formateador del tiempo de respuesta se evalúa al crear los encabezados de respuesta; no puede indicar cuándo termina un cuerpo que aún no se ha transmitido. El encabezado de diagnóstico del host de destino expone información interna de enrutamiento. Use estos encabezados de diagnóstico únicamente en una interfaz interna o de pruebas apropiada.

## Integración con Gateway API {#gateway-api-integration}

### GatewayClass y Gateway {#gatewayclass-and-gateway}

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: GatewayClass
metadata:
  name: cilium
spec:
  controllerName: io.cilium/gateway-controller
---
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: api-gateway
  namespace: default
spec:
  gatewayClassName: cilium
  listeners:
  - name: http
    protocol: HTTP
    port: 80
    allowedRoutes:
      namespaces:
        from: Same
  - name: https
    protocol: HTTPS
    port: 443
    tls:
      mode: Terminate
      certificateRefs:
      - kind: Secret
        name: api-gateway-tls
    allowedRoutes:
      namespaces:
        from: Same
```

Se requieren las CRD de Gateway API 1.6.3 y los valores `gatewayAPI.enabled: true`, `kubeProxyReplacement: true` y `l7Proxy: true` de Cilium. El GatewayClass mostrado describe la asociación con el controlador. Si las herramientas de instalación ya administran `cilium`, reutilícelo para evitar responsables en conflicto. Prepare `api-gateway-tls` como un Secret TLS válido en `default`, con un certificado para el nombre de host. La exposición y las direcciones de LoadBalancer dependen de la plataforma. Compruebe las condiciones Accepted y Programmed de GatewayClass/Gateway y las referencias de los listeners. Este manifiesto no configura un diseño completo de exposición en EKS.

### HTTPRoute {#httproute}

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: api-routes
  namespace: default
spec:
  parentRefs:
  - name: api-gateway
    namespace: default
    sectionName: https
  hostnames:
  - api.example.com
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /users
    backendRefs:
    - name: users-service
      port: 8080
  - matches:
    - path:
        type: PathPrefix
        value: /orders
    backendRefs:
    - name: orders-service
      port: 8080
  - matches:
    - path:
        type: PathPrefix
        value: /
      headers:
      - name: X-API-Version
        value: v2
    backendRefs:
    - name: api-v2
      port: 8080
  - matches:
    - path:
        type: PathPrefix
        value: /
    backendRefs:
    - name: api-stable
      port: 8080
      weight: 90
    - name: api-canary
      port: 8080
      weight: 10
```

Esta ruta se asocia únicamente al listener `https`. Los puertos 80/443 de los listeners de entrada son distintos del puerto 8080 de los Services de backend. El listener HTTP no redirige automáticamente a HTTPS; configure una ruta independiente para ese listener si la necesita. Gateway API aplica la precedencia definida por su especificación, como la especificidad de la ruta y las coincidencias de encabezados. No suponga que todas las reglas se evalúan únicamente en el orden del YAML. Compruebe Accepted, ResolvedRefs y el estado real del listener.

### Funciones avanzadas de HTTPRoute {#httproute-advanced-features}

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: advanced-routes
  namespace: default
spec:
  parentRefs:
  - name: api-gateway
    sectionName: https
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /api
    filters:
    - type: RequestHeaderModifier
      requestHeaderModifier:
        set:
        - name: X-Doc-Route
          value: api-v1
        remove:
        - X-Internal-Header
    - type: ResponseHeaderModifier
      responseHeaderModifier:
        add:
        - name: X-Frame-Options
          value: DENY
        - name: X-Content-Type-Options
          value: nosniff
    - type: URLRewrite
      urlRewrite:
        path:
          type: ReplacePrefixMatch
          replacePrefixMatch: /v1
    backendRefs:
    - name: api-service
      port: 8080
  - matches:
    - path:
        type: Exact
        value: /old-endpoint
      method: GET
    filters:
    - type: RequestRedirect
      requestRedirect:
        scheme: https
        hostname: new.example.com
        path:
          type: ReplaceFullPath
          replaceFullPath: /new-endpoint
        statusCode: 301
  hostnames:
  - api.example.com
```

Los valores de los encabezados son configuración literal y portable de Gateway API. La API no define las plantillas `%REQ(...)%` de Envoy. Conserve o genere los identificadores de solicitud en la capa adecuada de aplicación o proxy. No fuerce `X-Forwarded-Proto: https` con independencia del transporte real. URLRewrite cambia la ruta de destino sin redirigir al cliente. La redirección de la ruta antigua solo coincide con GET: una respuesta 301 puede cambiar el método en algunos clientes, por lo que no debe redirigir escrituras arbitrarias de forma inadvertida.

## Duplicación del tráfico {#traffic-mirroring}

```yaml
apiVersion: cilium.io/v2
kind: CiliumEnvoyConfig
metadata:
  name: traffic-mirror
  namespace: default
spec:
  services:
  - name: production-service
    namespace: default
    ports:
    - 8080
  backendServices:
  - name: production-backend
    namespace: default
  - name: shadow-backend
    namespace: default
  resources:
  - '@type': type.googleapis.com/envoy.config.listener.v3.Listener
    name: mirror-listener
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: production-service
          route_config:
            name: mirror_routes
            virtual_hosts:
            - name: production
              domains:
              - '*'
              routes:
              - match:
                  prefix: /
                  headers:
                  - name: :method
                    string_match:
                      safe_regex:
                        google_re2: {}
                        regex: ^(GET|HEAD)$
                route:
                  cluster: default/production-backend
                  request_mirror_policies:
                  - cluster: default/shadow-backend
                    runtime_fraction:
                      default_value:
                        numerator: 100
                        denominator: HUNDRED
                    trace_sampled: false
              - match:
                  prefix: /
                route:
                  cluster: default/production-backend
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/production-backend
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/shadow-backend
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
```

El backend de copia recibe el 100 % de las **solicitudes GET/HEAD seleccionadas**; la ruta para los demás métodos no tiene política de duplicación. Pruebe con tráfico sintético o tráfico de solo lectura aprobado y un backend de pruebas aislado que no pueda modificar el estado de producción ni provocar efectos externos. La duplicación consume recursos, copia los datos de las solicitudes y puede añadir `-shadow` a la autoridad, salvo que se configure otro comportamiento. Las respuestas de la copia no se devuelven al cliente, pero eso no garantiza que los usuarios no sufran ningún impacto.

## Próximos pasos {#next-steps}

- [Seguridad](./03-security.md): Revise la autenticación, el cifrado y las políticas de red L7
- [Observabilidad](./04-observability.md): Supervise el tráfico con Hubble
- [Ingress y Gateway](./05-ingress-gateway.md): Gestión del tráfico externo

## Referencias {#references}

- [Políticas L7 de Cilium 1.20.3](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/security/policy/layer7.rst)
- [Políticas L3/FQDN de Cilium](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/security/policy/layer3.rst)
- [Ejemplo de CEC de Cilium](https://github.com/cilium/cilium/blob/v1.20.3/examples/kubernetes/servicemesh/envoy/envoy-traffic-management-test.yaml)
- [Analizador de configuración de Envoy de Cilium](https://github.com/cilium/cilium/blob/v1.20.3/pkg/ciliumenvoyconfig/cec_resource_parser.go)
- [Sustitución de kube-proxy con Cilium](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/kubernetes/kubeproxy-free.rst)
- [Instalación de Gateway API con Cilium](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/servicemesh/gateway-api/installation.rst)
- [Valores del chart de Cilium 1.20.3](https://github.com/cilium/cilium/blob/v1.20.3/install/kubernetes/cilium/values.yaml)
- [Lista de extensiones de la imagen del proxy de Cilium](https://github.com/cilium/proxy/blob/766ccfb37260a43e9d228837aa84ce3faf9f64e7/envoy_build_config/extensions_build_config.bzl)
- [API de enrutamiento de Envoy 1.38.6](https://github.com/envoyproxy/envoy/blob/v1.38.6/api/envoy/config/route/v3/route_components.proto)
- [Implementación de reintentos de Envoy](https://github.com/envoyproxy/envoy/blob/v1.38.6/source/common/router/retry_state_impl.cc)
- [Tiempos de enrutamiento y procesamiento de encabezados de Envoy](https://github.com/envoyproxy/envoy/blob/v1.38.6/source/common/router/router.cc)
- [Modificación temprana de encabezados de Envoy](https://github.com/envoyproxy/envoy/blob/v1.38.6/api/envoy/extensions/http/early_header_mutation/header_mutation/v3/header_mutation.proto)
- [Limitación local de la tasa en Envoy](https://github.com/envoyproxy/envoy/blob/v1.38.6/api/envoy/extensions/filters/http/local_ratelimit/v3/local_rate_limit.proto)
- [Definiciones de tiempos de espera de Envoy](https://github.com/envoyproxy/envoy/blob/v1.38.6/docs/root/faq/configuration/timeouts.rst)
- [Especificación de HTTPRoute de Gateway API 1.6.3](https://github.com/kubernetes-sigs/gateway-api/blob/v1.6.3/apis/v1/httproute_types.go)
- [ACL de los brokers de Kafka](https://kafka.apache.org/41/security/authorization-and-acls/)
