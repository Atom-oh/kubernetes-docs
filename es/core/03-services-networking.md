# Servicios y redes

> **Versiones compatibles**: Kubernetes 1.32, 1.33, 1.34
> **Última actualización**: February 23, 2026

En Kubernetes, un Service es una capa de abstracción que proporciona un único punto de acceso para un conjunto de Pods. En este capítulo, exploraremos en detalle los conceptos de redes de Kubernetes, incluidos varios tipos de Service, Ingress, políticas de red y más.

## Configuración del entorno de laboratorio

Para seguir los ejemplos de este documento, necesitarás las siguientes herramientas y el siguiente entorno:

### Herramientas necesarias
- kubectl v1.34 o posterior
- Un clúster de Kubernetes en funcionamiento (EKS, minikube, kind, etc.)

### Implementar la aplicación de ejemplo

```bash
# Create namespace
kubectl create namespace networking-demo

# Deploy a simple application
kubectl -n networking-demo apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
  labels:
    app: web
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      containers:
      - name: nginx
        image: nginx:1.21
        ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: web-service
spec:
  selector:
    app: web
  ports:
  - port: 80
    targetPort: 80
  type: ClusterIP
EOF

# Verify services
kubectl -n networking-demo get svc,pods
```

## Tabla de contenidos

1. [Tipos de Service](#service-types)
2. [Ingress](#ingress)
3. [Endpoints](#endpoints)
4. [Descubrimiento de servicios](#service-discovery)
5. [CoreDNS](#coredns)
6. [Políticas de red](#network-policies)
7. [Service Mesh](#service-mesh)
8. [CNI (Container Network Interface)](#cnicontainer-network-interface)
9. [Cilium](#cilium)
   - [Introducción a Cilium](#introduction-to-cilium)
   - [Tecnología eBPF](#ebpf-technology)
   - [Modelo de red de Cilium](#cilium-networking-model)
   - [Políticas de red de Cilium](#cilium-network-policies)
   - [Visibilidad de red con Hubble](#network-visibility-with-hubble)
   - [Configuración de Cilium en Amazon EKS](#configuring-cilium-on-amazon-eks)

## Tipos de Service

> **Concepto clave**: Los Services de Kubernetes proporcionan endpoints de red estables para un conjunto de Pods y controlan el acceso interno y externo mediante varios tipos.

Kubernetes proporciona varios tipos de Services para admitir múltiples formas de exponer aplicaciones.

### Arquitectura de Service

![Los clientes externos llegan a ClusterIP a través de LoadBalancer o NodePort; los clientes internos del clúster resuelven nombres mediante CoreDNS y acceden a ClusterIP, que se enruta a través de Endpoints a los Pods de backend, mientras que ExternalName crea un alias de un servicio externo mediante DNS CNAME.](../.gitbook/assets/en-core-03-services-networking-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-03-services-networking-0.html)

### Comparación de tipos de Service

| Tipo de Service | Ámbito de acceso | IP externa | Caso de uso | Características |
|-------------|-------------|-------------|----------|----------|
| **ClusterIP** | Interno del clúster | No | Comunicación interna entre microservicios | Tipo de Service predeterminado, accesible solo dentro del clúster |
| **NodePort** | Externo al clúster | No | Entornos de desarrollo y prueba | Acceso mediante un puerto específico (30000-32767) en todos los nodos |
| **LoadBalancer** | Externo al clúster | Sí | Servicios externos de producción | Aprovisiona un balanceador de carga del proveedor de nube |
| **ExternalName** | Interno del clúster | No | Alias interno para servicios externos | Redirección mediante registro DNS CNAME |
| **Headless** | Interno del clúster | No | Cuando se necesita acceso directo a la IP del Pod | Service especial sin ClusterIP |

### ClusterIP

ClusterIP es el tipo de Service más básico y proporciona una dirección IP fija accesible solo dentro del clúster.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-service
spec:
  selector:
    app: MyApp
  ports:
  - protocol: TCP
    port: 80
    targetPort: 9376
  type: ClusterIP  # Default, can be omitted
```

### NodePort

Los Services NodePort permiten acceder al Service a través de un puerto específico en todos los nodos.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-service
spec:
  selector:
    app: MyApp
  ports:
  - protocol: TCP
    port: 80        # Port used within cluster
    targetPort: 9376 # Pod's port
    nodePort: 30007  # Port exposed on nodes (30000-32767)
  type: NodePort
```

ClusterIP es el tipo de Service predeterminado y proporciona una dirección IP accesible solo dentro del clúster.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-service
spec:
  selector:
    app: MyApp
  ports:
  - port: 80
    targetPort: 9376
  type: ClusterIP
```

Se puede acceder a este Service como `my-service:80` dentro del clúster.

### NodePort

Los Services NodePort permiten acceder al Service a través de un puerto específico en todos los nodos.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-service
spec:
  selector:
    app: MyApp
  ports:
  - port: 80
    targetPort: 9376
    nodePort: 30007  # Optional, auto-assigned from 30000-32767 if not specified
  type: NodePort
```

Se puede acceder a este Service como `<Node IP>:30007` en todos los nodos del clúster.

### LoadBalancer

Los Services LoadBalancer aprovisionan un balanceador de carga del proveedor de nube para exponer el Service externamente.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-service
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: nlb  # Use NLB on AWS
spec:
  selector:
    app: MyApp
  ports:
  - port: 80
    targetPort: 9376
  type: LoadBalancer
```

Se puede acceder a este Service externamente a través del balanceador de carga del proveedor de nube.

### ExternalName

Los Services ExternalName proporcionan un alias para servicios externos.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-service
spec:
  type: ExternalName
  externalName: my.database.example.com
```

Este Service asigna el nombre DNS `my-service` a `my.database.example.com`.

### Service Headless

Un Service Headless es un Service sin una IP de clúster que crea registros DNS para cada Pod.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-service
spec:
  clusterIP: None  # Headless service
  selector:
    app: MyApp
  ports:
  - port: 80
    targetPort: 9376
```

Este Service no asigna una IP de clúster y crea registros DNS para cada Pod.

### IP externa

Los Services pueden especificar IP externas para exponer recursos externos como Services de Kubernetes.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-service
spec:
  selector:
    app: MyApp
  ports:
  - port: 80
    targetPort: 9376
  externalIPs:
  - 80.11.12.10
```

## Ingress

Ingress es un objeto de API que expone rutas HTTP y HTTPS desde fuera del clúster hacia Services dentro del clúster. Ingress proporciona balanceo de carga, terminación SSL y alojamiento virtual basado en nombres.

![La solicitud de un cliente externo pasa por un balanceador de carga y un controlador Ingress hasta un único recurso Ingress, cuyas reglas de host/ruta se distribuyen a Service A y Service B, cada uno con balanceo de carga entre sus propios Pods de backend (A-1, A-2 / B-1, B-2).](../.gitbook/assets/en-core-03-services-networking-1.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-03-services-networking-1.html)

### Controlador Ingress

Para usar recursos Ingress, debe ejecutarse un controlador Ingress en el clúster. Existen varios controladores Ingress:

- NGINX Ingress Controller
- AWS ALB Ingress Controller
- GCE Ingress Controller
- Traefik
- HAProxy
- Istio Ingress

### Ingress básico

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: minimal-ingress
spec:
  ingressClassName: nginx  # Ingress controller class to use
  rules:
  - host: example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: example-service
            port:
              number: 80
```

Este Ingress enruta todas las solicitudes al host `example.com` hacia `example-service:80`.

### Enrutamiento basado en rutas

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: path-based-ingress
spec:
  ingressClassName: nginx
  rules:
  - host: example.com
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: api-service
            port:
              number: 80
      - path: /web
        pathType: Prefix
        backend:
          service:
            name: web-service
            port:
              number: 80
```

Este Ingress enruta las solicitudes que comienzan con `example.com/api` a `api-service` y las solicitudes que comienzan con `example.com/web` a `web-service`.

### Alojamiento virtual basado en nombres

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: name-based-ingress
spec:
  ingressClassName: nginx
  rules:
  - host: foo.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: foo-service
            port:
              number: 80
  - host: bar.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: bar-service
            port:
              number: 80
```

Este Ingress enruta las solicitudes a `foo.example.com` a `foo-service` y las solicitudes a `bar.example.com` a `bar-service`.

### Configuración TLS

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: tls-ingress
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - example.com
    secretName: example-tls
  rules:
  - host: example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: example-service
            port:
              number: 80
```

Este Ingress termina las conexiones HTTPS a `example.com` mediante el certificado TLS almacenado en el Secret `example-tls`.

Creación de Secret TLS:

```bash
kubectl create secret tls example-tls --cert=path/to/cert.crt --key=path/to/key.key
```

### AWS ALB Ingress Controller

En AWS EKS, puedes usar AWS ALB Ingress Controller para aprovisionar Application Load Balancers.

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: alb-ingress
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTP": 80}, {"HTTPS": 443}]'
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:region:account-id:certificate/certificate-id
spec:
  rules:
  - host: example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: example-service
            port:
              number: 80
```

Este Ingress usa AWS ALB para gestionar las solicitudes a `example.com`.

## Endpoints

Los Endpoints son recursos que almacenan las direcciones IP y los puertos de los Pods a los que apunta un Service. Cuando hay Pods que coinciden con el selector del Service, Kubernetes crea y administra automáticamente el objeto Endpoints.

```yaml
apiVersion: v1
kind: Endpoints
metadata:
  name: my-service
subsets:
- addresses:
  - ip: 192.168.1.1
  ports:
  - port: 9376
```

Este Endpoints hace que `my-service` apunte a `192.168.1.1:9376`.

### EndpointSlice

EndpointSlice es una alternativa escalable a Endpoints que proporciona mejor rendimiento en clústeres grandes.

```yaml
apiVersion: discovery.k8s.io/v1
kind: EndpointSlice
metadata:
  name: my-service-abc
  labels:
    kubernetes.io/service-name: my-service
addressType: IPv4
ports:
- name: http
  protocol: TCP
  port: 80
endpoints:
- addresses:
  - "10.1.2.3"
  conditions:
    ready: true
  hostname: pod-1
  topology:
    kubernetes.io/hostname: node-1
    topology.kubernetes.io/zone: us-west-2a
```

## Descubrimiento de servicios

Kubernetes proporciona dos métodos principales de descubrimiento de servicios:

1. **Variables de entorno**: Kubernetes inyecta variables de entorno de los Services activos en los Pods cuando se crean.
2. **DNS**: Kubernetes proporciona registros DNS para los Services a través del servidor DNS del clúster.

### Variables de entorno

Cuando se crea un Pod, Kubernetes inyecta en el Pod variables de entorno para todos los Services que existen en ese momento. Por ejemplo, si hay un Service llamado `my-service`, se crean las siguientes variables de entorno:

```
MY_SERVICE_SERVICE_HOST=10.0.0.11
MY_SERVICE_SERVICE_PORT=80
```

### DNS

El DNS de Kubernetes crea registros DNS para los Services. Los Pods pueden acceder a los Services mediante el nombre del Service.

- Service normal: `my-service.my-namespace.svc.cluster.local`
- Pod de un Service Headless: `pod-name.my-service.my-namespace.svc.cluster.local`

## CoreDNS

CoreDNS es un servidor DNS flexible y extensible que se utiliza como servidor DNS para los clústeres de Kubernetes.

### Configuración de CoreDNS

CoreDNS se configura mediante un ConfigMap:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: coredns
  namespace: kube-system
data:
  Corefile: |
    .:53 {
        errors
        health {
            lameduck 5s
        }
        ready
        kubernetes cluster.local in-addr.arpa ip6.arpa {
            pods insecure
            fallthrough in-addr.arpa ip6.arpa
            ttl 30
        }
        prometheus :9153
        forward . /etc/resolv.conf
        cache 30
        loop
        reload
        loadbalance
    }
```

Esta configuración proporciona las siguientes características:

- `errors`: Registro de errores
- `health`: Endpoint de comprobación de estado
- `ready`: Endpoint de comprobación de disponibilidad
- `kubernetes`: Registros DNS para Services y Pods de Kubernetes
- `prometheus`: Exposición de métricas de Prometheus
- `forward`: Reenvío de consultas DNS externas
- `cache`: Almacenamiento en caché de respuestas DNS
- `loop`: Detección de bucles
- `reload`: Recarga automática ante cambios en el archivo de configuración
- `loadbalance`: Balanceo de carga

### Política DNS

La política DNS de un Pod se puede configurar mediante el campo `dnsPolicy`:

- `ClusterFirst`: Predeterminada; utiliza primero el servidor DNS de Kubernetes y reenvía a servidores de nombres ascendentes si no encuentra coincidencias.
- `Default`: Hereda la configuración DNS del nodo donde se ejecuta el Pod.
- `ClusterFirstWithHostNet`: Política recomendada para Pods con `hostNetwork: true`.
- `None`: Todas las configuraciones DNS deben proporcionarse mediante el campo `dnsConfig`.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: custom-dns
spec:
  containers:
  - name: nginx
    image: nginx
  dnsPolicy: "None"
  dnsConfig:
    nameservers:
    - 1.1.1.1
    - 8.8.8.8
    searches:
    - ns1.svc.cluster.local
    - my.dns.search.suffix
    options:
    - name: ndots
      value: "2"
    - name: edns0
```

## Políticas de red

Las políticas de red proporcionan una forma de controlar la comunicación entre Pods. Para usar políticas de red, el complemento de red debe admitirlas (por ejemplo, Calico, Cilium, Weave Net).

![Las políticas de red permiten que el Pod Frontend llegue al Pod API y que el Pod API llegue al Pod Database, y permiten que un Pod Monitoring de otro namespace llegue al Pod API, mientras bloquean directamente que el Pod Frontend y el Pod Monitoring lleguen al Pod Database.](../.gitbook/assets/en-core-03-services-networking-2.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-03-services-networking-2.html)

### Política de red básica

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
spec:
  podSelector: {}  # Applies to all Pods
  policyTypes:
  - Ingress
```

Esta política de red bloquea el tráfico de entrada a todos los Pods.

### Permitir entrada a Pods específicos

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-nginx-ingress
spec:
  podSelector:
    matchLabels:
      app: nginx
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          access: allowed
    ports:
    - protocol: TCP
      port: 80
```

Esta política de red permite tráfico de entrada en el puerto TCP 80 desde Pods con la etiqueta `access: allowed` hacia Pods con la etiqueta `app: nginx`.

### Política basada en namespace

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-from-prod-namespace
spec:
  podSelector:
    matchLabels:
      app: db
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          purpose: production
```

Esta política de red permite tráfico de entrada desde todos los Pods en namespaces con la etiqueta `purpose: production` hacia Pods con la etiqueta `app: db`.

### Política de salida

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: limit-egress
spec:
  podSelector:
    matchLabels:
      app: frontend
  policyTypes:
  - Egress
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: api
    ports:
    - protocol: TCP
      port: 8080
  - to:
    - namespaceSelector:
        matchLabels:
          purpose: monitoring
```

Esta política de red permite tráfico de salida desde Pods con la etiqueta `app: frontend` hacia el puerto TCP 8080 en Pods con la etiqueta `app: api` y hacia todos los Pods en namespaces con la etiqueta `purpose: monitoring`.

### Política basada en CIDR

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-external-traffic
spec:
  podSelector:
    matchLabels:
      app: web
  policyTypes:
  - Ingress
  ingress:
  - from:
    - ipBlock:
        cidr: 192.168.1.0/24
        except:
        - 192.168.1.1/32
```

Esta política de red permite tráfico de entrada desde el bloque CIDR `192.168.1.0/24` (excepto 192.168.1.1) hacia Pods con la etiqueta `app: web`.

## Service Mesh

Un service mesh es una capa de infraestructura que administra la comunicación entre microservicios. Los service meshes proporcionan características como descubrimiento de servicios, balanceo de carga, cifrado, autenticación, autorización y observabilidad.

![El plano de control de Istio envía configuración a través de canales de control discontinuos a los proxies sidecar inyectados en tres Pods; cada Service se comunica solo con su propio sidecar, y los sidecars intercambian tráfico de Service a Service entre sí en lugar de que los Services se conecten directamente.](../.gitbook/assets/en-core-03-services-networking-3.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-03-services-networking-3.html)

### Istio

Istio es una de las implementaciones populares de service mesh. Istio usa el patrón sidecar para inyectar proxies Envoy en cada Pod.

#### Istio Virtual Service

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: VirtualService
metadata:
  name: reviews
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
```

Este VirtualService enruta las solicitudes con el encabezado `end-user: jason` al subconjunto `v2` del Service `reviews` y todas las demás solicitudes al subconjunto `v1`.

#### Istio Destination Rule

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: DestinationRule
metadata:
  name: reviews
spec:
  host: reviews
  trafficPolicy:
    loadBalancer:
      simple: RANDOM
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
    trafficPolicy:
      loadBalancer:
        simple: ROUND_ROBIN
```

Este DestinationRule define dos subconjuntos (`v1` y `v2`) para el Service `reviews` y establece políticas de balanceo de carga para cada subconjunto.

### Linkerd

Linkerd es un service mesh ligero caracterizado por una instalación y un uso sencillos.

#### Linkerd Service Profile

```yaml
apiVersion: linkerd.io/v1alpha2
kind: ServiceProfile
metadata:
  name: nginx.default.svc.cluster.local
  namespace: default
spec:
  routes:
  - name: GET /
    condition:
      method: GET
      pathRegex: /
    responseClasses:
    - condition:
        status:
          min: 500
          max: 599
      isFailure: true
  retryBudget:
    retryRatio: 0.2
    minRetriesPerSecond: 10
    ttl: 10s
```

Este ServiceProfile define rutas y políticas de reintento para el Service `nginx`.

## Cilium

![Kubernetes delega las redes a través de Container Network Interface en Cilium, que carga programas eBPF en el kernel de Linux para implementar la ruta de datos y también alimenta a Hubble para la observabilidad de los flujos de red.](../.gitbook/assets/en-core-03-services-networking-4.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-03-services-networking-4.html)

[Detalles de Cilium](../networking/cilium/README.md)

### Introducción a Cilium

Cilium es software de código abierto que aprovecha la potente tecnología eBPF del kernel de Linux para proporcionar conectividad de red, seguridad y observabilidad para aplicaciones en contenedores. Está diseñado para proporcionar redes, seguridad y observabilidad para plataformas de orquestación de contenedores como Kubernetes, Docker y Mesos.

#### Características principales

- **Basado en eBPF**: Proporciona características de red y seguridad de alto rendimiento a través de una ruta de datos programable dentro del kernel
- **Redes con reconocimiento de API**: Admite políticas de seguridad de red con reconocimiento de API en las capas L3-L7
- **Integración con Kubernetes**: Proporciona una implementación CNI (Container Network Interface) de Kubernetes
- **Balanceo de carga distribuido**: Balanceo de carga distribuido para una comunicación eficiente de Service a Service
- **Visibilidad de red**: Monitoreo y solución de problemas de flujos de red mediante Hubble
- **Compatibilidad con múltiples clústeres**: Compatibilidad con redes y políticas de seguridad entre clústeres

#### Aspectos diferenciadores de Cilium

Cilium proporciona varias ventajas únicas en comparación con otras soluciones CNI.

**Diferenciación técnica**:
- **Uso de eBPF**: Alto rendimiento y flexibilidad a través de una ruta de datos programable dentro del kernel
- **Redes con reconocimiento de API**: Compatibilidad con políticas de red hasta la capa L7
- **XDP (eXpress Data Path)**: Optimización del rendimiento de procesamiento de paquetes
- **Reemplazo de Kube-proxy**: Balanceo de carga de Service más eficiente
- **Integración con Hubble**: Potente herramienta de observabilidad de red

**Beneficios por caso de uso**:
- **Arquitectura de microservicios**: Políticas de red y observabilidad detalladas
- **Implementación en múltiples clústeres**: Redes sin interrupciones entre clústeres
- **Entorno centrado en la seguridad**: Políticas de seguridad de red sólidas
- **Requisitos de alto rendimiento**: Ruta de datos optimizada
- **Integración con Service Mesh**: Integración con service meshes como Istio

### Tecnología eBPF

eBPF (extended Berkeley Packet Filter) es una tecnología que permite que los programas se ejecuten de forma segura dentro del kernel de Linux. Cilium usa eBPF para implementar características de red, seguridad y observabilidad.

#### Características principales de eBPF

1. **Ejecución en el kernel**: Los programas eBPF se ejecutan directamente dentro del kernel y proporcionan alto rendimiento.
2. **Seguridad**: El verificador de eBPF garantiza que los programas no dañen el kernel.
3. **Carga dinámica**: Los programas eBPF se pueden cargar y descargar sin reiniciar el kernel.
4. **Mapas**: Los mapas eBPF se utilizan para almacenar y compartir datos entre el espacio de usuario y el espacio del kernel.

#### Uso de eBPF en Cilium

Cilium usa eBPF de las siguientes maneras:

1. **Ruta de datos de red**: Los programas eBPF procesan y enrutan paquetes de red.
2. **Aplicación de políticas**: Los programas eBPF aplican políticas de red.
3. **Balanceo de carga**: Los programas eBPF realizan el balanceo de carga para Services.
4. **Observabilidad**: Los programas eBPF recopilan métricas sobre los flujos de red.

#### eBPF frente a enfoques de red tradicionales

| Característica | eBPF | Enfoque tradicional (iptables) |
|---------|------|--------------------------------|
| Rendimiento | Muy alto | Medio |
| Escalabilidad | Muy alta | Limitada |
| Programabilidad | Alta | Limitada |
| Observabilidad | Alta | Limitada |
| Complejidad de implementación | Alta | Media |

### Modelo de red de Cilium

Cilium admite varios modelos de red que se pueden configurar para adaptarse a diferentes entornos y requisitos.

#### Redes overlay

Cilium implementa redes overlay de forma predeterminada mediante VXLAN, pero también admite otros protocolos de encapsulación como Geneve.

**Cómo funciona**:
1. Los paquetes se crean en el nodo de origen.
2. Cilium encapsula el paquete envolviendo el paquete original con encabezados de encapsulación.
3. El paquete encapsulado se transmite al nodo de destino a través de la red física.
4. En el nodo de destino, Cilium desencapsula el paquete para extraer el paquete original.
5. El paquete extraído se entrega al contenedor de destino.

**Ventajas**:
- Compatibilidad con la infraestructura de red existente
- Independencia de la topología de red
- Prevención de conflictos de IP en entornos de múltiples clústeres

**Desventajas**:
- Impacto en el rendimiento debido a la sobrecarga de encapsulación
- Tamaño de MTU reducido
- Uso adicional de CPU

#### Enrutamiento nativo

El enrutamiento nativo utiliza enrutamiento directo sin encapsulación. En este modo, la infraestructura de red subyacente debe poder enrutar las direcciones IP de los Pods.

**Cómo funciona**:
1. Cada nodo anuncia el bloque CIDR de los Pods que se ejecutan en ese nodo.
2. Las tablas de enrutamiento se configuran para enrutar cada bloque CIDR de Pods al nodo correspondiente.
3. Los paquetes se enrutan directamente al nodo de destino sin encapsulación.

**Ventajas**:
- Sin sobrecarga de encapsulación
- Rendimiento de red mejorado
- Menor uso de CPU

**Desventajas**:
- Dependencia de la infraestructura de red subyacente
- Restricciones de topología de red
- Complejidad de la administración de direcciones IP

#### Modo híbrido

Cilium también admite un modo híbrido que combina redes overlay y enrutamiento nativo.

**Cómo funciona**:
1. Usa enrutamiento nativo cuando es posible.
2. Recurre a redes overlay cuando el enrutamiento nativo no es posible.

**Ventajas**:
- Equilibrio entre flexibilidad y rendimiento
- Compatibilidad con varias topologías de red
- Posibilidad de migración gradual

#### Modo AWS ENI

En AWS EKS, Cilium puede aprovechar las AWS Elastic Network Interfaces (ENI) para asignar direcciones IP de VPC nativas a los Pods.

**Características principales**:
- Asigna direcciones IP nativas de VPC a los Pods
- Redes nativas de VPC sin red overlay
- Integración con AWS security groups y políticas de red
- Rendimiento de red mejorado

### Políticas de red de Cilium

Cilium amplía las políticas de red de Kubernetes para proporcionar políticas de seguridad de red detalladas en las capas L3-L7.

#### Políticas L3/L4

Cilium admite políticas de red estándar de Kubernetes para definir políticas basadas en direcciones IP, puertos y protocolos.

```yaml
apiVersion: "cilium.io/v2"
kind: CiliumNetworkPolicy
metadata:
  name: "l3-l4-policy"
spec:
  endpointSelector:
    matchLabels:
      app: myapp
  ingress:
  - fromEndpoints:
    - matchLabels:
        app: frontend
    toPorts:
    - ports:
      - port: "80"
        protocol: TCP
```

Esta política permite tráfico de entrada en el puerto TCP 80 desde Pods con la etiqueta `app: frontend` hacia Pods con la etiqueta `app: myapp`.

#### Políticas L7

Cilium admite políticas L7 (capa de aplicación) para definir políticas detalladas para protocolos como HTTP, gRPC y Kafka.

```yaml
apiVersion: "cilium.io/v2"
kind: CiliumNetworkPolicy
metadata:
  name: "l7-policy"
spec:
  endpointSelector:
    matchLabels:
      app: myapp
  ingress:
  - fromEndpoints:
    - matchLabels:
        app: frontend
    toPorts:
    - ports:
      - port: "80"
        protocol: TCP
      rules:
        http:
        - method: "GET"
          path: "/api/v1/products"
```

Esta política permite únicamente solicitudes HTTP GET a la ruta `/api/v1/products` desde Pods con la etiqueta `app: frontend` hacia Pods con la etiqueta `app: myapp`.

#### Políticas para todo el clúster

Cilium admite políticas de red para todo el clúster para definir políticas que se aplican a todos los Pods.

```yaml
apiVersion: "cilium.io/v2"
kind: CiliumClusterwideNetworkPolicy
metadata:
  name: "cluster-wide-policy"
spec:
  endpointSelector:
    matchLabels: {}  # Applies to all Pods
  ingress:
  - fromEndpoints:
    - matchLabels:
        io.kubernetes.pod.namespace: kube-system
```

Esta política permite tráfico de entrada desde Pods en el namespace `kube-system` hacia todos los Pods.

### Visibilidad de red con Hubble

Hubble es la capa de observabilidad de Cilium que usa eBPF para monitorear flujos de red y solucionar problemas.

#### Características principales de Hubble

1. **Monitoreo de flujos de red**: Monitorea la comunicación de Pod a Pod en tiempo real.
2. **Mapeo de dependencias de Services**: Visualiza las dependencias de Service a Service.
3. **Observación de seguridad**: Detecta infracciones de políticas de red.
4. **Análisis de rendimiento**: Analiza la latencia y el rendimiento de la red.
5. **Solución de problemas**: Diagnostica problemas de conectividad de red.

#### Arquitectura de Hubble

Hubble consta de los siguientes componentes:

1. **Hubble Server**: Servidor integrado en el agente de Cilium que recopila datos de flujos de red.
2. **Hubble Relay**: Agrega datos de varios Hubble Servers.
3. **Hubble UI**: Interfaz web para visualizar flujos de red.
4. **Hubble CLI**: Herramienta de línea de comandos para consultar flujos de red.

#### Ejemplos de uso de Hubble

```bash
# Install Hubble CLI
curl -L --remote-name-all https://github.com/cilium/hubble/releases/latest/download/hubble-linux-amd64.tar.gz
sudo tar xzvfC hubble-linux-amd64.tar.gz /usr/local/bin
rm hubble-linux-amd64.tar.gz

# Enable Hubble
cilium hubble enable

# Observe network flows
hubble observe

# Observe HTTP requests
hubble observe --protocol http

# Observe network flows for specific Pod
hubble observe --pod app=myapp

# Observe network policy violations
hubble observe --verdict DROPPED
```

### Configuración de Cilium en Amazon EKS

Existen varias formas de configurar Cilium en Amazon EKS. Aquí veremos algunos métodos de configuración comunes.

#### Instalación básica

```bash
# Install Cilium CLI
curl -L --remote-name-all https://github.com/cilium/cilium-cli/releases/latest/download/cilium-linux-amd64.tar.gz
sudo tar xzvfC cilium-linux-amd64.tar.gz /usr/local/bin
rm cilium-linux-amd64.tar.gz

# Install Cilium
cilium install

# Check installation status
cilium status

# Test connectivity
cilium connectivity test
```

#### Configuración del modo AWS ENI

```bash
# Install Cilium with AWS ENI mode
cilium install --config aws-eni-mode=true

# Or install using Helm
helm install cilium cilium/cilium \
  --namespace kube-system \
  --set eni.enabled=true \
  --set ipam.mode=eni \
  --set egressMasqueradeInterfaces=eth0 \
  --set tunnel=disabled
```

#### Habilitar Hubble

```bash
# Enable Hubble
cilium hubble enable --ui

# Access Hubble UI
kubectl port-forward -n kube-system svc/hubble-ui 12000:80
```

#### Ejemplo de política de red de Cilium

```yaml
apiVersion: "cilium.io/v2"
kind: CiliumNetworkPolicy
metadata:
  name: "eks-app-policy"
spec:
  endpointSelector:
    matchLabels:
      app: api
  ingress:
  - fromEndpoints:
    - matchLabels:
        app: frontend
    toPorts:
    - ports:
      - port: "8080"
        protocol: TCP
      rules:
        http:
        - method: "GET"
          path: "/api/v1/.*"
  egress:
  - toEndpoints:
    - matchLabels:
        app: database
    toPorts:
    - ports:
      - port: "3306"
        protocol: TCP
```

Esta política permite únicamente solicitudes HTTP GET a la ruta `/api/v1/` desde Pods con la etiqueta `app: frontend` hacia Pods con la etiqueta `app: api`, y permite tráfico de salida en el puerto TCP 3306 desde Pods con la etiqueta `app: api` hacia Pods con la etiqueta `app: database`.

#### Optimización de Cilium en EKS

1. **Configuración de grupos de nodos**:
   - Selecciona tipos de instancias que proporcionen suficientes ENI y direcciones IP
   - Configura un recuento máximo de Pods adecuado

2. **Optimización de rendimiento**:
   - Usa el modo de enrutamiento directo
   - Habilita la aceleración XDP
   - Habilita el algoritmo de control de congestión BBR

3. **Monitoreo y registro**:
   - Habilita Hubble
   - Recopilación de métricas de Prometheus
   - Integración con CloudWatch

## Conclusión

En este capítulo, aprendimos sobre Services y redes de Kubernetes. Los Services proporcionan endpoints estables para un conjunto de Pods, e Ingress enruta el tráfico externo a Services dentro del clúster. Las políticas de red controlan la comunicación entre Pods, y los service meshes administran la comunicación de Service a Service en arquitecturas de microservicios. También exploramos cómo implementar características avanzadas de red a través de CNI y Cilium.

Comprender y utilizar las características de red de Kubernetes te permite crear aplicaciones seguras y escalables.

En el próximo capítulo, aprenderemos sobre las opciones de almacenamiento de Kubernetes.

## Referencias

- [Documentación oficial de Kubernetes - Services](https://kubernetes.io/docs/concepts/services-networking/service/)
- [Documentación oficial de Kubernetes - Ingress](https://kubernetes.io/docs/concepts/services-networking/ingress/)
- [Documentación oficial de Kubernetes - Políticas de red](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Documentación oficial de Kubernetes - DNS para Services y Pods](https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/)
- [Documentación oficial de Istio](https://istio.io/latest/docs/)
- [Documentación oficial de Linkerd](https://linkerd.io/2.11/overview/)
- [Documentación oficial de Cilium](https://docs.cilium.io/)
- [Documentación oficial de CNI](https://github.com/containernetworking/cni)

## Cuestionario

Para poner a prueba lo que aprendiste en este capítulo, intenta el [Cuestionario de Services y redes](../quizzes/core/03-services-networking-quiz.md).
