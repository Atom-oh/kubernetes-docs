# Políticas de red

> **Base de revisión**: Kubernetes 1.35 OpenAPI, Cilium 1.20.1, Calico 3.32.2 y la documentación actual de AWS. Las comprobaciones sin conexión no establecen la compatibilidad con el clúster.
> **Última actualización**: September 13, 2026

Las Network Policies de Kubernetes son reglas de firewall que controlan el tráfico entre Pods. Este documento cubre NetworkPolicy básico y extensiones de Cilium/Calico. Las secciones son ejemplos independientes; combinar todas las políticas cambiaría los permisos efectivos. No se realizó ningún despliegue de clúster/nube ni una prueba de conectividad en vivo.

## Tabla de contenido

1. [Descripción general de las Network Policies](#network-policy-overview)
2. [Especificación Kubernetes NetworkPolicy](#kubernetes-networkpolicy-spec)
3. [Políticas de denegación predeterminada](#default-deny-policies)
4. [Orden y evaluación de políticas](#policy-order-and-evaluation)
5. [Extensiones de Cilium Network Policy](#cilium-network-policy-extensions)
6. [Extensiones de Calico Network Policy](#calico-network-policy-extensions)
7. [Patrones de diseño](#design-patterns)
8. [Prueba de Network Policies](#testing-network-policies)
9. [Consideraciones de EKS](#eks-considerations)
10. [Herramientas de visualización](#visualization-tools)

---

## Descripción general de Network Policy {#network-policy-overview}

### ¿Qué es una Network Policy?

Kubernetes NetworkPolicy selecciona Pods en su propio namespace y controla el tráfico de entrada y salida compatible. Un Pod sin una política seleccionadora para una dirección no queda aislado por NetworkPolicy en esa dirección; el enrutamiento, los security groups, las NACL y otros motores de políticas aún pueden impedir la conectividad.

**Ambos extremos deben permitir** una conexión de Pod a Pod: las reglas de salida efectivas del origen y las reglas de entrada efectivas del destino deben permitirla. El tráfico de retorno de una conexión permitida se permite implícitamente. Las políticas son implementadas de forma asíncrona por un plugin de red compatible; un objeto de API por sí solo no demuestra su aplicación. El tráfico de Node/hostNetwork y los protocolos fuera de TCP/UDP/SCTP requieren una revisión específica de la implementación. Los diagramas siguientes muestran la intención de la política, no una garantía de accesibilidad.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    No Network Policy (Default State)                     │
│                                                                         │
│    ┌─────────┐        ┌─────────┐        ┌─────────┐                   │
│    │  Pod A  │◀──────▶│  Pod B  │◀──────▶│  Pod C  │                   │
│    └─────────┘        └─────────┘        └─────────┘                   │
│         ▲                  ▲                  ▲                         │
│         │                  │                  │                         │
│         └──────────────────┴──────────────────┘                         │
│              Free communication between all Pods                         │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                    With Network Policy Applied                           │
│                                                                         │
│    ┌─────────┐        ┌─────────┐        ┌─────────┐                   │
│    │  Pod A  │───────▶│  Pod B  │        │  Pod C  │                   │
│    └─────────┘        └─────────┘        └─────────┘                   │
│                            ▲                                            │
│                            │ Allowed                                    │
│                       ┌────┴────┐                                       │
│                       │Controlled│                                      │
│                       │by Policy │                                      │
│                       └─────────┘                                       │
└─────────────────────────────────────────────────────────────────────────┘
```

### Características de Network Policy

| Propiedad | Descripción |
|----------|-------------|
| **Con ámbito de namespace** | NetworkPolicy se aplica a recursos dentro de un namespace |
| **Aditiva** | Las reglas Allow de las Kubernetes NetworkPolicies seleccionadoras forman una unión para cada dirección; las denegaciones de Cilium, los tiers de Calico y las políticas administrativas de AWS tienen semánticas distintas |
| **Aplicación selectiva** | Pods de destino especificados mediante podSelector |
| **Control direccional** | Control independiente para Ingress (entrada) y Egress (salida) |
| **Dependiente de CNI** | El plugin de CNI debe admitir NetworkPolicy |

### Compatibilidad de CNI con NetworkPolicy

| CNI | NetworkPolicy básico | Extensiones | Política L7 |
|-----|---------------------|------------|-----------|
| **Cilium** | ✓ | CiliumNetworkPolicy, CiliumClusterwideNetworkPolicy | ✓ |
| **Calico** | ✓ | GlobalNetworkPolicy, NetworkSet, Tier | Integración opcional de Istio/Dikastes; verifique el producto y las versiones desplegados |
| **Weave Net (proyecto archivado)** | Compatibilidad histórica | Referencia heredada; evalúe una implementación mantenida para nuevos despliegues | ✗ |
| **Flannel solo** | No aplica políticas por sí solo | Se necesita un motor de políticas compatible independiente | ✗ |
| **Amazon VPC CNI** | ✓ cuando está habilitado en Node EC2 Linux compatibles | NetworkPolicy estándar; ClusterNetworkPolicy con VPC CNI 1.21+ | Egress DNS en Nodes EKS Auto Mode; consulte las consideraciones de EKS |

---

## Especificación Kubernetes NetworkPolicy {#kubernetes-networkpolicy-spec}

### Estructura básica

Especifique `policyTypes` explícitamente. Si se omite, Kubernetes usa Ingress de forma predeterminada y agrega Egress cuando hay al menos una regla de salida. Los arrays de reglas vacíos por sí solos no implican ambas direcciones.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: example-policy
  namespace: default
spec:
  # Select Pods to apply policy
  podSelector:
    matchLabels:
      app: web

  # Policy types (auto-inferred if omitted)
  policyTypes:
    - Ingress
    - Egress

  # Ingress rules (inbound traffic)
  ingress:
    - from:
        - podSelector:
            matchLabels:
              role: frontend
        - namespaceSelector:
            matchLabels:
              project: myproject
        - ipBlock:
            cidr: 172.17.0.0/16
            except:
              - 172.17.1.0/24
      ports:
        - protocol: TCP
          port: 80
        - protocol: TCP
          port: 443

  # Egress rules (outbound traffic)
  egress:
    - to:
        - podSelector:
            matchLabels:
              role: database
      ports:
        - protocol: TCP
          port: 5432
```

### podSelector

Selecciona los Pods a los que se aplica la política en su propio namespace. Los siguientes son fragmentos alternativos de especificación, no recursos de API independientes.

```yaml
# Apply to Pods with specific labels
spec:
  podSelector:
    matchLabels:
      app: api
      version: v1

---
# Apply to all Pods (empty selector)
spec:
  podSelector: {}

---
# Using matchExpressions
spec:
  podSelector:
    matchExpressions:
      - key: app
        operator: In
        values:
          - api
          - web
      - key: environment
        operator: NotIn
        values:
          - development
```

### namespaceSelector

Selecciona namespaces por etiquetas, incluido el namespace actual si coincide. `name` no es una etiqueta de namespace asignada automáticamente. Use la etiqueta integrada e inmutable `kubernetes.io/metadata.name` para un nombre de namespace exacto; restrinja quién puede cambiar las etiquetas de tenancy personalizadas.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-from-monitoring
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
    - Ingress
  ingress:
    - from:
        # Allow all Pods from monitoring namespace
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: monitoring
        # Allow specific Pods from production namespace
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: production
          podSelector:
            matchLabels:
              role: frontend
```

**Nota:** distinción entre AND y OR al usar `namespaceSelector` y `podSelector` juntos:

```yaml
# OR condition (two separate peer entries)
ingress:
  - from:
      - namespaceSelector:    # Rule 1
          matchLabels:
            kubernetes.io/metadata.name: team-a
      - podSelector:          # Rule 2
          matchLabels:
            role: frontend

---
# AND condition (single rule)
ingress:
  - from:
      - namespaceSelector:    # Both conditions must be met
          matchLabels:
            kubernetes.io/metadata.name: team-a
        podSelector:
          matchLabels:
            role: frontend
```

### ipBlock

Un `ipBlock` permite un CIDR menos sus rangos `except` en esa regla. Una excepción no es una denegación global y otra política puede permitirla. La traducción de direcciones de Service/load-balancer puede cambiar el origen o destino visible para el CNI; verifique la ruta real. Los CIDR de documentación siguientes son ilustrativos, no endpoints de producción accesibles.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-external-traffic
  namespace: default
spec:
  podSelector:
    matchLabels:
      app: public-api
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        # Example private source range; not a guarantee of the load balancer source IP
        - ipBlock:
            cidr: 10.0.0.0/8
        # Allow specific external IP
        - ipBlock:
            cidr: 203.0.113.0/24
  egress:
    - to:
        # Allow external API server access
        - ipBlock:
            cidr: 0.0.0.0/0
            except:
              - 10.0.0.0/8      # Exclude internal networks
              - 172.16.0.0/12
              - 192.168.0.0/16
      ports:
        - protocol: TCP
          port: 443
```

### ports

Especifique los puertos y protocolos permitidos. `endPort` requiere un puerto inicial numérico y compatibilidad de CNI para rangos; un puerto con nombre no puede ser el inicio de un rango. La aceptación por la API por sí sola no demuestra la aplicación por cada plugin.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: port-specific-policy
  namespace: default
spec:
  podSelector:
    matchLabels:
      app: web
  policyTypes:
    - Ingress
  ingress:
    - ports:
        # Specific ports
        - protocol: TCP
          port: 80
        - protocol: TCP
          port: 443
        # Port range (Kubernetes 1.25+)
        - protocol: TCP
          port: 8000
          endPort: 8080
        # Named port
        - protocol: TCP
          port: http
```

---

## Políticas de denegación predeterminada {#default-deny-policies}

Una línea base vacía no aporta permisos; otras políticas seleccionadoras aún pueden permitir tráfico. El comportamiento de conexiones existentes después de un cambio de política depende de la implementación y debe probarse por separado.

### Denegación predeterminada de Ingress

Una línea base de aislamiento de entrada sin permisos propios. Otras políticas seleccionadoras aún pueden permitir Ingress:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
  namespace: production
spec:
  podSelector: {}  # Apply to all Pods
  policyTypes:
    - Ingress
  # No ingress rules = block all inbound traffic
```

### Denegación predeterminada de Egress

Una línea base de aislamiento de salida sin permisos propios. Otras políticas seleccionadoras aún pueden permitir Egress:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-egress
  namespace: production
spec:
  podSelector: {}
  policyTypes:
    - Egress
  # No egress rules = block all outbound traffic
```

### Denegación total (Ingress + Egress)

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: production
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
```

### Denegación predeterminada con DNS permitido

Este perfil presupone CoreDNS basado en Pod en `kube-system` con `k8s-app=kube-dns`. Permite TCP y UDP 53. Si DNS tiene aislamiento de entrada, su política también debe permitir los clientes. NodeLocal DNSCache y CoreDNS local del Node de Auto Mode necesitan su perfil real de resolver/IP; no aplique aquí este podSelector sin cambios.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-egress-allow-dns
  namespace: production
spec:
  podSelector: {}
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
```

### Política predeterminada de arquitectura Zero Trust

Están presentes ambas direcciones frontend→API. Esto no permite tráfico de entrada al frontend ni API→database; agregue solo los flujos revisados. Use la hipótesis de DNS basado en Pod anterior.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: zero-trust-default
  namespace: production
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress: []
  egress: []
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
  namespace: production
spec:
  podSelector: {}
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-api
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 8080
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: frontend-api-egress
  namespace: production
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
```

## Orden y evaluación de políticas {#policy-order-and-evaluation}

### Reglas de evaluación de políticas

Para cada endpoint y dirección, evalúe únicamente las **Kubernetes NetworkPolicies** seleccionadoras como se indica a continuación. Después compruebe la dirección del otro endpoint y todos los demás controles de red. Una política solo de entrada no aísla la salida.

```
┌─────────────────────────────────────────────────────────────────┐
│                  NetworkPolicy Evaluation Flow                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Are there policies that apply to the Pod?                   │
│     │                                                           │
│     ├─ No → Allow all traffic (default behavior)                │
│     │                                                           │
│     └─ Yes → Start policy evaluation                            │
│              │                                                  │
│              ▼                                                  │
│  2. Is there a policy for this direction (Ingress/Egress)?      │
│     │                                                           │
│     ├─ No → Allow traffic in that direction                     │
│     │                                                           │
│     └─ Yes → Start rule matching                                │
│              │                                                  │
│              ▼                                                  │
│  3. Does traffic match one or more rules?                       │
│     │                                                           │
│     ├─ Matched → Allow traffic                                  │
│     │                                                           │
│     └─ Not matched → Block traffic                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Combinación de varias políticas

Cuando varias NetworkPolicies se aplican al mismo Pod, se combinan todas las reglas de política (unión):

```yaml
---
# Policy 1: Allow traffic from frontend
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
    - Ingress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: frontend
      ports:
        - protocol: TCP
          port: 8080
---
# Policy 2: Allow traffic from monitoring
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-monitoring
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: monitoring
      ports:
        - protocol: TCP
          port: 8080
        - protocol: TCP
          port: 9090
```

**Resultado:** el Ingress de la API permite Pods frontend en 8080 y Pods del namespace monitoring en 8080/9090. Sus reglas de Egress, listeners reales y otros controles de red también deben permitir la conexión.

### Orden de evaluación de políticas

La API Kubernetes NetworkPolicy no tiene prioridad ni regla explícita de denegación. Su unión de permisos no describe el orden o las acciones de tier de las políticas Calico, las denegaciones explícitas de Cilium ni la evaluación de políticas administrativas de AWS:

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   Policy A    Policy B    Policy C                              │
│   (allow X)   (allow Y)   (allow Z)                             │
│       │           │           │                                 │
│       └───────────┼───────────┘                                 │
│                   │                                             │
│                   ▼                                             │
│           ┌───────────────┐                                     │
│           │     Union     │                                     │
│           │ (X OR Y OR Z) │                                     │
│           └───────────────┘                                     │
│                   │                                             │
│                   ▼                                             │
│           Final allowed traffic:                                │
│           X, Y, Z all allowed                                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Extensiones de Cilium Network Policy {#cilium-network-policy-extensions}

Estos ejemplos usan el esquema de políticas publicado de Cilium 1.20.1, no son una instrucción para actualizar todos los clústeres. Las reglas HTTP necesitan una ruta de proxy L7 compatible. El chaining de AWS VPC CNI tiene limitaciones documentadas de características avanzadas, incluidas las políticas L7; no presuponga que estos ejemplos HTTP funcionan en ese modo. Una identidad de seguridad numérica de Cilium es una asignación para un conjunto de etiquetas, no un ID de aplicación permanente.

### CiliumNetworkPolicy

Cilium extiende NetworkPolicy básico con funcionalidades más potentes.

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: cilium-l7-policy
  namespace: production
spec:
  # Endpoint selection
  endpointSelector:
    matchLabels:
      app: api

  # L3/L4 rules (similar to basic NetworkPolicy)
  ingress:
    - fromEndpoints:
        - matchLabels:
            app: frontend
      toPorts:
        - ports:
            - port: "8080"
              protocol: TCP
          # L7 rules (Cilium extension)
          rules:
            http:
              - method: GET
                path: "/api/v1/.*"
              - method: POST
                path: "/api/v1/users"
                headers:
                  - 'Content-Type: application/json'
```

### Política HTTP L7

Las reglas HTTP de Cilium filtran las solicitudes visibles para su proxy L7; no autentican API keys ni establecen roles de administrador. Un llamador puede proporcionar un encabezado `X-User-Role`. Este ejemplo filtra métodos, rutas y un `Content-Type` exacto. Aplique autenticación y autorización en la aplicación o en un gateway autenticado. TLS de extremo a extremo no se descifra automáticamente para la inspección HTTP. Revise otras políticas que puedan permitir el mismo tráfico en L4.

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: http-api-policy
  namespace: production
spec:
  endpointSelector:
    matchLabels:
      app: api-server
  ingress:
  - fromEndpoints:
    - matchLabels:
        app: web-frontend
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
      rules:
        http:
        - method: GET
          path: /api/v1/products
        - method: GET
          path: /api/v1/products/[0-9]+
        - method: POST
          path: /api/v1/orders
          headerMatches:
          - name: Content-Type
            value: application/json
```

[HTTP API — Cilium 1.20.1](https://github.com/cilium/cilium/blob/v1.20.1/pkg/policy/api/http.go)

### Política Kafka L7

El esquema CNP publicado de Cilium 1.20.1 admite reglas L7 HTTP y DNS, pero no tiene `rules.kafka`. La anterior receta `role`, `topic` y `clientID` no es una API desplegable actual. Restrinja la conectividad del broker con una política de red y después aplique permisos de productor/consumidor para `orders` y `events` mediante autenticación y ACL de Kafka. Un ID de cliente no es un principal autenticado.

Este ejemplo L4 presupone un listener de broker TLS ya configurado en TCP 9093, clientes en el mismo namespace y Egress/DNS de clientes autorizado por separado. No configura TLS, ACL de broker ni permisos de topics.

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: kafka-client-network-access
  namespace: data
spec:
  endpointSelector:
    matchLabels:
      app: kafka
  ingress:
  - fromEndpoints:
    - matchLabels:
        app: producer
    - matchLabels:
        app: consumer
    toPorts:
    - ports:
      - port: '9093'
        protocol: TCP
```

[CNP schema — Cilium 1.20.1](https://github.com/cilium/cilium/blob/v1.20.1/pkg/k8s/apis/cilium.io/client/crds/v2/ciliumnetworkpolicies.yaml)

### Política DNS L7

Este ejemplo utiliza CoreDNS basado en Pod. `ANY` en el puerto 53 cubre UDP y TCP. El permiso de consulta DNS y el permiso para conectarse a una IP devuelta son independientes: resolver el nombre de database siguiente no permite conexiones a la base de datos. Reemplace el dominio de ejemplo, tenga en cuenta los sufijos de búsqueda/caché/TTL de DNS y verifique el perfil real del resolver. Las reglas FQDN aprenden IP de DNS; no autentican un tenant SaaS ni sustituyen TLS/autorización de aplicación.

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: dns-policy
  namespace: production
spec:
  endpointSelector:
    matchLabels:
      app: web
  egress:
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
        k8s:k8s-app: kube-dns
    toPorts:
    - ports:
      - port: '53'
        protocol: ANY
      rules:
        dns:
        - matchName: api.example.com
        - matchName: database.production.svc.cluster.local
  - toFQDNs:
    - matchName: api.example.com
    toPorts:
    - ports:
      - port: '443'
        protocol: TCP
```

### CiliumClusterwideNetworkPolicy

El recurso tiene ámbito de clúster, mientras que su selector lo limita explícitamente a `production/app=api`. Permite Pods de gateway en TCP8080. Controla solo Ingress; el aislamiento de Egress/DNS y el Egress del propio gateway requieren las políticas correspondientes. El ejemplo anterior de permiso de cluster/world para todos los endpoints no era una política de denegación predeterminada.

```yaml
apiVersion: cilium.io/v2
kind: CiliumClusterwideNetworkPolicy
metadata:
  name: production-api-from-edge
spec:
  endpointSelector:
    matchLabels:
      k8s:io.kubernetes.pod.namespace: production
      app: api
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: gateway-system
        app: edge-proxy
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
```

### Política basada en entidades de Cilium

`host` incluye el Node local y sus contenedores host-network; `cluster` incluye más que Pods de aplicaciones. `world` abarca endpoints fuera del clúster y no es una allowlist detallada de Internet/SaaS. Use reglas CIDR/FQDN explícitas al restringir el acceso externo. Este ejemplo ofrece únicamente a un cliente Kubernetes API etiquetado acceso TCP443; configure por separado el endpoint de API, la confianza TLS, las credenciales y RBAC. La identidad de origen puede cambiar entre rutas de red de planos de control administrados, por lo que debe inspeccionar la identidad de flujo real en lugar de ampliar el Ingress a todo el clúster.

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: kubernetes-api-client
  namespace: production
spec:
  endpointSelector:
    matchLabels:
      app: kubernetes-api-client
  egress:
  - toEntities:
    - kube-apiserver
    toPorts:
    - ports:
      - port: '443'
        protocol: TCP
```

## Extensiones de Calico Network Policy {#calico-network-policy-extensions}

Los ejemplos de políticas/Tier siguen los recursos de Calico Open Source 3.32.2. `projectcalico.org/v3` requiere el API server de Calico compatible o un flujo de trabajo `calicoctl` equivalente; no es la API de almacenamiento Kubernetes sin procesar `crd.projectcalico.org/v1`. Verifique el datastore/API instalado antes de aplicar. Las acciones ordenadas de Calico y la delegación de tiers difieren de la API aditiva Kubernetes NetworkPolicy.

La documentación actual de Open Source también describe la [integración de capa de aplicación Istio/Dikastes](https://docs.tigera.io/calico/latest/network-policy/istio/app-layer-policy). La API HTTPMatch requiere esa configuración independiente y admite reglas Allow de Ingress. Los ejemplos Calico siguientes cubren política L3/L4; esta revisión no desplegó ni probó la integración L7.

### Calico NetworkPolicy

```yaml
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: calico-policy
  namespace: production
spec:
  # Policy order (lower = evaluated first)
  order: 100

  selector: app == 'api'

  types:
    - Ingress
    - Egress

  ingress:
    - action: Allow
      protocol: TCP
      source:
        selector: app == 'frontend'
      destination:
        ports:
          - 8080

  egress:
    - action: Allow
      protocol: TCP
      destination:
        selector: app == 'database'
        ports:
          - 5432
```

### GlobalNetworkPolicy

Estos dos recursos globales seleccionan solo workloads en el namespace `production`. Un `selector: all()` sin restricciones también puede afectar endpoints de host; no aplique una denegación para todo el clúster sin un ámbito explícito y una vía de recuperación. El `order` más bajo se evalúa primero dentro del tier. El ejemplo permite DNS basado en Pod y, de otro modo, proporciona una línea base de denegación; agregue los flujos de aplicación revisados y tenga en cuenta las acciones de tiers superiores.

```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: production-default-deny
spec:
  namespaceSelector: projectcalico.org/name == 'production'
  selector: all()
  order: 1000
  types:
  - Ingress
  - Egress
  ingress: []
  egress: []
---
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: production-allow-dns
spec:
  namespaceSelector: projectcalico.org/name == 'production'
  selector: all()
  order: 100
  types:
  - Egress
  egress:
  - action: Allow
    protocol: UDP
    destination:
      selector: k8s-app == 'kube-dns'
      namespaceSelector: projectcalico.org/name == 'kube-system'
      ports:
      - 53
  - action: Allow
    protocol: TCP
    destination:
      selector: k8s-app == 'kube-dns'
      namespaceSelector: projectcalico.org/name == 'kube-system'
      ports:
      - 53
```

### NetworkSet

Los selectores NetworkSet coinciden con `metadata.labels`, no con el nombre del recurso. El primer conjunto tiene ámbito de namespace; el conjunto bloqueado es global y se consume en el ejemplo de security-tier siguiente. Todos los CIDR aquí son rangos de documentación y deben reemplazarse por destinos revisados. El ejemplo de Egress permite TCP443 al conjunto etiquetado con ámbito de namespace; DNS es una regla independiente.

```yaml
apiVersion: projectcalico.org/v3
kind: NetworkSet
metadata:
  name: external-apis
  namespace: production
  labels:
    network-role: external-api
spec:
  nets:
  - 203.0.113.0/24
  - 198.51.100.10/32
---
apiVersion: projectcalico.org/v3
kind: GlobalNetworkSet
metadata:
  name: blocked-ips
  labels:
    network-role: blocked
spec:
  nets:
  - 192.0.2.0/24
---
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: allow-external-apis
  namespace: production
spec:
  selector: app == 'web'
  types:
  - Egress
  egress:
  - action: Allow
    protocol: TCP
    destination:
      selector: network-role == 'external-api'
      ports:
      - 443
```

### Políticas basadas en Tier

Los tiers están disponibles en la versión de Calico Open Source referenciada, no solo en Enterprise. Un tier seleccionador toma `Deny` como valor predeterminado cuando no actúa ninguna regla. Por lo tanto, el tier deny-known-threats usa explícitamente `defaultAction: Pass` para que el tráfico no relacionado pueda llegar a las políticas posteriores. `Pass` es delegación, no permiso. `global()` pertenece a `namespaceSelector`; el selector de etiqueta independiente identifica el GlobalNetworkSet. Complete las políticas de application-tier y verifique cualquier comportamiento final de profile/default-tier antes del despliegue; crear un Tier vacío no es una política completa de aislamiento de aplicaciones.

```yaml
apiVersion: projectcalico.org/v3
kind: Tier
metadata:
  name: security
spec:
  order: 100
  defaultAction: Pass
---
apiVersion: projectcalico.org/v3
kind: Tier
metadata:
  name: platform
spec:
  order: 200
  defaultAction: Pass
---
apiVersion: projectcalico.org/v3
kind: Tier
metadata:
  name: application
spec:
  order: 300
  defaultAction: Deny
---
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: security.block-known-threats
spec:
  tier: security
  order: 100
  selector: all()
  namespaceSelector: projectcalico.org/name == 'production'
  types:
  - Ingress
  ingress:
  - action: Deny
    source:
      selector: network-role == 'blocked'
      namespaceSelector: global()
---
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: platform.allow-dns
spec:
  tier: platform
  order: 100
  selector: all()
  namespaceSelector: projectcalico.org/name == 'production'
  types:
  - Egress
  egress:
  - action: Allow
    protocol: UDP
    destination:
      selector: k8s-app == 'kube-dns'
      namespaceSelector: projectcalico.org/name == 'kube-system'
      ports:
      - 53
  - action: Allow
    protocol: TCP
    destination:
      selector: k8s-app == 'kube-dns'
      namespaceSelector: projectcalico.org/name == 'kube-system'
      ports:
      - 53
```

## Patrones de diseño {#design-patterns}

Estos son **perfiles de política alternativos**, no un conjunto para aplicar juntos. Reutilizar `production` no hace compatibles ejemplos no relacionados: sus reglas Allow se acumularían. Prepare primero los namespaces, las etiquetas de workload, los puertos de escucha y el perfil DNS real. Los ejemplos se comprobaron localmente en cuanto a esquema/intención, pero no se ejecutaron en un clúster.

### Microsegmentación

Este perfil permite frontend→API TCP8080 y API→database TCP5432 en ambos lados, además de DNS. Deliberadamente no tiene Egress a Internet ni Ingress externo al frontend. Si se requiere, agregue un CIDR/puerto de destino aprobado o un perfil de egress gateway autenticado; excluir RFC1918 de 0.0.0.0/0 no es una allowlist SaaS.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: production
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress: []
  egress: []
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
  namespace: production
spec:
  podSelector: {}
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: frontend-api-egress
  namespace: production
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
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: frontend-to-api
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 8080
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-to-database
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
  - Egress
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: database
    ports:
    - protocol: TCP
      port: 5432
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: database-from-api
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: database
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: api
    ports:
    - protocol: TCP
      port: 5432
```

### Aislamiento de namespace

El perfil de equipo incluye Ingress **y Egress** para el mismo equipo, además de DNS. Los servicios compartidos también necesitan Ingress de destino que permita team-a y un listener TLS443 real. Restrinja la administración de las etiquetas de namespace; una etiqueta de equipo no es un límite de confianza independiente.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: team-a
  labels:
    team: team-a
    environment: production
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-same-team
  namespace: team-a
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - &id001
      namespaceSelector:
        matchLabels:
          team: team-a
  egress:
  - to:
    - *id001
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-shared-services
  namespace: team-a
spec:
  podSelector: {}
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          shared-services: 'true'
      podSelector:
        matchLabels:
          exposed: 'true'
    ports:
    - protocol: TCP
      port: 443
```

### Protección de base de datos

El namespace `database` debe existir. Los llamadores de producción y los Pods de monitoring necesitan sus propios permisos de Egress. Las reglas de pares TCP5432 permiten únicamente el transporte de replicación PostgreSQL supuesto; configure la autenticación/TLS de la base de datos por separado. TCP9187 presupone un exporter instalado por separado.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: database-protection
  namespace: database
spec:
  podSelector:
    matchLabels:
      app: postgresql
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          environment: production
      podSelector:
        matchLabels:
          database-access: 'true'
    ports:
    - protocol: TCP
      port: 5432
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: monitoring
      podSelector:
        matchLabels:
          app: prometheus
    ports:
    - protocol: TCP
      port: 9187
  - from:
    - podSelector:
        matchLabels:
          app: postgresql
    ports:
    - protocol: TCP
      port: 5432
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: postgresql
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
```

### Política de arquitectura de 3 niveles

Suponga un workload existente `gateway-system/app=edge-proxy` que termina TLS de cliente y puede alcanzar los Pods web en TCP80. La política de Egress del gateway está fuera de este namespace. El Ingress y Egress de pares de datos usan TCP5432/6379; los puertos adicionales de replicación/bus de clúster/backup dependen de la base de datos elegida y no están implícitos. Separe los selectores PostgreSQL y Redis en un despliegue real.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: three-tier-default-deny
  namespace: production
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress: []
  egress: []
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: web-tier-policy
  namespace: production
spec:
  podSelector:
    matchLabels:
      tier: web
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: gateway-system
      podSelector:
        matchLabels:
          app: edge-proxy
    ports:
    - protocol: TCP
      port: 80
  egress:
  - to:
    - podSelector:
        matchLabels:
          tier: app
    ports:
    - protocol: TCP
      port: 8080
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: app-tier-policy
  namespace: production
spec:
  podSelector:
    matchLabels:
      tier: app
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          tier: web
    ports:
    - protocol: TCP
      port: 8080
  egress:
  - to:
    - podSelector:
        matchLabels:
          tier: data
    ports:
    - protocol: TCP
      port: 5432
    - protocol: TCP
      port: 6379
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: data-tier-policy
  namespace: production
spec:
  podSelector:
    matchLabels:
      tier: data
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          tier: app
    ports:
    - protocol: TCP
      port: 5432
    - protocol: TCP
      port: 6379
  - from:
    - podSelector:
        matchLabels:
          tier: data
    ports:
    - protocol: TCP
      port: 5432
    - protocol: TCP
      port: 6379
  egress:
  - to:
    - podSelector:
        matchLabels:
          tier: data
    ports:
    - protocol: TCP
      port: 5432
    - protocol: TCP
      port: 6379
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: three-tier-dns
  namespace: production
spec:
  podSelector:
    matchExpressions:
    - key: tier
      operator: In
      values:
      - web
      - app
      - data
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
```

---

## Prueba de Network Policies {#testing-network-policies}

### Pruebas con netshoot

Use Pods de diagnóstico aprobados y ya aprovisionados con imágenes fijadas y permisos revisados. Seleccione etiquetas/namespace/ubicación de Node de origen que realmente ejerciten la política; un Pod genérico sin etiquetas no representa la aplicación. Aprovisionar netshoot crea un workload y puede entrar en conflicto con la admisión Pod Security. No cree/elimine un nombre fijo compartido `test-pod` como parte de un script de observación. Ejecute sondeos solo contra endpoints de prueba propios.

### Pruebas con kubectl exec

Establezca explícitamente el contexto, namespace, Pod existente y contenedor. El éxito de DNS no equivale al éxito de TCP; el rechazo de conexión, un listener no saludable, un error TLS y una caída por política son resultados distintos. Estos comandos prueban solo la conectividad y no imprimen cuerpos de respuesta. No se ejecutaron contra un clúster durante esta revisión.

```bash
# Both Pods already exist in the approved test environment.
kubectl --context="$CONTEXT" -n "$NAMESPACE" get pods --show-labels
kubectl --context="$CONTEXT" -n "$NAMESPACE" exec "$ALLOW_POD" \
  -c "$PROBE_CONTAINER" -- nslookup api-service.production.svc.cluster.local
kubectl --context="$CONTEXT" -n "$NAMESPACE" exec "$ALLOW_POD" \
  -c "$PROBE_CONTAINER" -- curl --silent --show-error --output /dev/null \
  --connect-timeout 3 --max-time 5 http://api-service.production.svc.cluster.local:8080/health
```

### Prueba de conectividad de Cilium

`cilium connectivity test` crea recursos y tráfico de prueba; no es un comando de estado de solo lectura. Use un clúster/namespace aislado aprobado, CLI e imágenes compatibles, destinos externos definidos y un plan de limpieza. Consulte `cilium connectivity test --help` para conocer los filtros de la CLI instalada en lugar de suponer que los nombres de prueba históricos aún existen. Una suite superada no demuestra cada política de aplicación ni cada característica de CNI chaining.

### Script de prueba automatizada

Este script solo ejecuta sondeos curl limitados en dos Pods existentes; no crea ni elimina recursos de clúster. Establezca `CONTEXT`, `NAMESPACE`, `ALLOW_POD`, `DENIED_POD`, `PROBE_CONTAINER` y un `TARGET_URL` no secreto que termine en `/health`. Ambos contenedores necesitan `sh` y `curl`. El primer Pod es un control positivo conocido como permitido para el mismo destino. Las respuestas de error HTTP aún establecen accesibilidad de red porque esta prueba no es validación del estado de la aplicación.

Exit1 significa que el sujeto bloqueado se conectó inesperadamente; exit2 significa desconocido/error; exit3 significa tiempo de espera que requiere corroboración. Un tiempo de espera **nunca** se convierte en PASS automático: correlacione el origen/destino/puerto/hora exactos con un veredicto de caída de política CNI, comprobando a la vez el estado del endpoint, las rutas y los controles SG/NACL. Las pruebas simuladas locales no afirman aplicación en vivo.

```bash
#!/usr/bin/env bash
set -euo pipefail
: "${CONTEXT:?Set an approved kubectl context}"
: "${NAMESPACE:?Set the test namespace}"
: "${ALLOW_POD:?Set an existing positive-control Pod}"
: "${DENIED_POD:?Set a different existing policy-subject Pod}"
: "${PROBE_CONTAINER:?Set a container with sh and curl in both Pods}"
: "${TARGET_URL:?Set the same non-secret health URL for both probes}"
if [[ "$ALLOW_POD" == "$DENIED_POD" ||
      ! "$TARGET_URL" =~ ^https?://[A-Za-z0-9.-]+(:[0-9]+)?/health$ ]]; then
  echo "Invalid probe inputs: use different Pods and a plain /health URL." >&2
  exit 2
fi
work=$(mktemp -d "${TMPDIR:-/tmp}/network-policy-probe.XXXXXX")
trap 'rm -rf -- "$work"' EXIT
probe() {
  local pod=$1 result
  if ! result=$(kubectl --context="$CONTEXT" --request-timeout=15s \
      -n "$NAMESPACE" exec "$pod" -c "$PROBE_CONTAINER" -- \
      sh -c 'rc=0
        curl --silent --output /dev/null --connect-timeout 3 --max-time 5 "$1" || rc=$?
        printf "PROBE_EXIT=%s\n" "$rc"' sh "$TARGET_URL" \
      2>"$work/transport-error"); then
    echo "UNKNOWN: kubectl exec/authorization/transport failed." >&2
    return 2
  fi
  if [[ ! "$result" =~ ^PROBE_EXIT=([0-9]+)$ ]]; then
    echo "UNKNOWN: missing or malformed remote probe result." >&2
    return 2
  fi
  printf '%s\n' "${BASH_REMATCH[1]}"
}
allowed=$(probe "$ALLOW_POD") || exit 2
if [[ "$allowed" != 0 ]]; then
  echo "UNKNOWN: positive control could not reach the target." >&2
  exit 2
fi
denied=$(probe "$DENIED_POD") || exit 2
case "$denied" in
  0) echo "FAIL: the intended blocked Pod reached the target."; exit 1 ;;
  28) echo "INCONCLUSIVE: timeout; correlate an actual policy-drop verdict."; exit 3 ;;
  *) echo "UNKNOWN: DNS/TLS/refused/tool error is not proof of a policy drop."; exit 2 ;;
esac
```

## Consideraciones de EKS {#eks-considerations}

### Amazon VPC CNI y NetworkPolicy

Amazon VPC CNI admite políticas de red después de la habilitación. La guía actual de AWS requiere VPC CNI 1.21+ para las políticas estándar y administrativas, una plataforma EKS compatible y Linux kernel 5.10+. La aplicación corresponde a Nodes EC2 Linux compatibles, no Fargate ni Windows. Use una versión EKS actualmente compatible y verifique su versión de add-on compatible; no infiera la compatibilidad EKS a partir de versiones Kubernetes upstream.

Para un add-on VPC CNI **administrado por EKS**, conserve su configuración actual al establecer el string documentado `"enableNetworkPolicy": "true"`. Lo siguiente cambia el clúster seleccionado tras la revisión; no actualiza la versión del add-on. Si la versión instalada es incompatible, deténgase y siga primero el procedimiento de actualización documentado.

```bash
# Requires AWS CLI, kubectl and jq; use an approved test cluster.
set -euo pipefail
: "${CLUSTER_NAME:?Set the approved test-cluster name}"
umask 077
aws eks describe-addon --cluster-name "$CLUSTER_NAME" --addon-name vpc-cni   --output json > vpc-cni-before.json
jq -e '(.addon.configurationValues // "{}") | if . == "" then {} else fromjson end
  | .enableNetworkPolicy = "true"' vpc-cni-before.json > vpc-cni-network-policy.json
# Review the saved current version/configuration and the complete merged JSON first.
aws eks update-addon --cluster-name "$CLUSTER_NAME" --addon-name vpc-cni   --configuration-values file://vpc-cni-network-policy.json --resolve-conflicts PRESERVE
```

Compruebe el estado de la actualización y el comportamiento de la política antes del rollout. `--resolve-conflicts PRESERVE` no fusiona por usted un documento JSON de sustitución; el ejemplo conserva explícitamente los valores existentes. Mantenga la instantánea para recuperación. Una instalación propiedad de Helm usa su chart/values revisados y `enableNetworkPolicy: true`; no tome su propiedad mediante este comando de add-on administrado. Establecer la variable de entorno inventada `ENABLE_NETWORK_POLICY` no es el procedimiento de habilitación.

El modo de inicio estándar puede permitir inicialmente un Pod nuevo hasta que se programe su política. `NETWORK_POLICY_ENFORCING_MODE=strict` inicia Pods elegibles denegados y requiere una matriz completa de permisos, incluido DNS; cambiarlo puede interrumpir workloads. Los Pods administrados por controladores son el destino de prueba fiable. La aplicación ocurre en la interfaz de Pod principal, por lo que inspeccione por separado interfaces adicionales, Egress IPv6 a IPv4, host networking y NAT. No instale dos motores para administrar las mismas políticas estándar ni elimine `aws-node` como atajo de migración.

### Políticas de seguridad de red mejoradas de EKS (diciembre de 2025)

> **Anunciado**: December 15, 2025 · [Fuente](https://aws.amazon.com/about-aws/whats-new/2025/12/amazon-eks-enhanced-network-security-policies/)

La característica es real, pero sus recursos usan **`networking.k8s.aws/v1alpha1`**. `ClusterNetworkPolicy` tiene ámbito de clúster y un `tier` obligatorio; el Egress basado en DNS usa `ApplicationNetworkPolicy` para el ejemplo de namespace siguiente. La compatibilidad de políticas VPC CNI estándar/administrativas en EC2 Linux no implica que todos los modos de cómputo sean compatibles. Las reglas DNS se aplican solo en **instancias EC2 lanzadas por Auto Mode**, incluso en un clúster mixto.

**Requisito previo de Auto Mode:** habilite su Network Policy Controller antes de aplicar las políticas siguientes. Actualizar un add-on `vpc-cni` administrado por EKS es una ruta independiente y no habilita la aplicación de políticas para un clúster Auto Mode puro. El ajuste requerido es ConfigMap `kube-system/amazon-vpc-cni`, `data.enable-network-policy-controller: "true"`. El flujo siguiente conserva otros datos de ConfigMap con un merge patch, crea solo si está ausente y se detiene ante una lectura o escritura fallida. Revise el contexto del clúster y la configuración existente antes de ejecutarlo.

```bash
set -euo pipefail
config="$(kubectl get configmap amazon-vpc-cni -n kube-system --ignore-not-found -o name)"
if [ -n "$config" ]; then
  kubectl patch configmap amazon-vpc-cni -n kube-system --type merge \
    -p '{"data":{"enable-network-policy-controller":"true"}}'
else
  kubectl create configmap amazon-vpc-cni -n kube-system \
    --from-literal=enable-network-policy-controller=true
fi
kubectl get configmap amazon-vpc-cni -n kube-system -o json \
  | jq -e '.data["enable-network-policy-controller"] == "true"'
```

Después de habilitarlo, inspeccione los objetos `PolicyEndpoints` correspondientes y pruebe tanto el tráfico permitido como el denegado en los Nodes Auto Mode seleccionados. Una marca almacenada o un objeto de política aceptado no prueba la aplicación. Consulte la [configuración de Network Policy de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/auto-net-pol.html). No se realizó una prueba de aplicación en clúster para esta auditoría de documentación.

Este ejemplo de nivel Admin deniega el tráfico entrante desde Pods seleccionados por namespace hacia `isolated-demo`, incluidos los Pods de ese mismo namespace. No es un firewall externo/host-network completo ni una política de permiso DNS. Una denegación Admin no puede sobrescribirse mediante una NetworkPolicy de namespace. Revise el CRD realmente instalado antes de agregar otras acciones: el esquema actual del controlador AWS upstream llama `Accept` a su acción de permiso, mientras que el texto de la guía de usuario usa “Allow”.

```yaml
apiVersion: networking.k8s.aws/v1alpha1
kind: ClusterNetworkPolicy
metadata:
  name: isolate-demo-namespace
spec:
  tier: Admin
  priority: 10
  subject:
    namespaces:
      matchLabels:
        kubernetes.io/metadata.name: isolated-demo
  ingress:
  - name: deny-pod-ingress
    action: Deny
    from:
    - namespaces:
        matchLabels: {}
```

El ejemplo FQDN selecciona `app=backend` en `production`. **Reemplace `10.100.0.10/32` por la IP CoreDNS Auto Mode real de su clúster**: es la dirección de red Service CIDR más 10 (`::a/128` para IPv6). CoreDNS Auto Mode puro se ejecuta en el Node; un podSelector CoreDNS convencional no es intercambiable. Permita DNS TCP y UDP. Use un nombre de recurso único que no colisione con una NetworkPolicy de ese namespace.

```yaml
apiVersion: networking.k8s.aws/v1alpha1
kind: ApplicationNetworkPolicy
metadata:
  name: approved-api-egress
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
  - Egress
  egress:
  - to:
    - ipBlock:
        cidr: 10.100.0.10/32
    ports:
    - protocol: TCP
      port: 53
    - protocol: UDP
      port: 53
  - to:
    - domainNames:
      - api.stripe.com
    ports:
    - protocol: TCP
      port: 443
```

El proxy DNS observa respuestas permitidas y sus TTL y después la ruta de datos permite las IP/puertos de destino aprendidos. Esto no autentica una cuenta SaaS ni prueba la identidad HTTP del par; las IP compartidas y el comportamiento DNS requieren pruebas. La verificación de certificados TLS, la autorización de aplicación, las rutas y cualquier regla de Route 53 DNS Firewall siguen siendo pertinentes. Deben revisarse conjuntamente otras políticas aplicables y rutas directas de backend.

[AWS NetworkPolicy](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html) · [Configuración](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy-configure.html) · [Políticas de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/auto-net-pol.html)

### Security Groups para Pods

Este ejemplo de binding presupone EKS VPC Resource Controller, sus permisos de **rol de clúster**, Nodes EC2 Linux compatibles con trunking y una configuración VPC CNI revisada. La guía AWS actual excluye Windows y EKS Auto Mode. Fargate usa un modelo Pod-SG independiente y no obtiene compatibilidad VPC-CNI NetworkPolicy simplemente por tener un security group. Aplique el binding a nuevos Pods de workload coincidentes mediante su owner; los Pods existentes no se actualizan automáticamente.

Para Calico más Pod SG, AWS documenta VPC CNI1.11.0+ con `POD_SECURITY_GROUP_ENFORCING_MODE=standard`; use también los requisitos de CNI actuales, en lugar de tratar ese mínimo como una versión recomendada. El SNAT externo en modo estándar puede usar el SG del Node en vez del SG del Pod. Verifique la ruta exacta. El antiguo Pod PostgreSQL básico carecía de credenciales/almacenamiento y no era un despliegue de base de datos funcional.

```yaml
# Binding example only: use an existing reviewed security group.
apiVersion: vpcresources.k8s.aws/v1beta1
kind: SecurityGroupPolicy
metadata:
  name: database-sg-policy
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: database
  securityGroups:
    groupIds:
      - sg-0123456789abcdef0
```

El fragmento Terraform permite Ingress de DB desde un SG de aplicación revisado y no inicia conexiones Egress nuevas. El tráfico de retorno con estado se permite mediante seguimiento SG; agregue por separado solo el DNS, replicación, backup o Egress externo requeridos. Las variables son entradas de operador existentes; no se ejecutó ningún Terraform plan/apply.

```hcl
# Fragment for an existing reviewed Terraform configuration.
# Supply the actual VPC and application SG; this is not a standalone module.
resource "aws_security_group" "database_pods" {
  name_prefix = "database-pods-"
  vpc_id      = var.vpc_id
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [var.application_security_group_id]
  }
  egress = []
}
```

### Combinación de controles de nivel VPC con NetworkPolicy

NetworkPolicy, los SG realmente aplicados y las NACL deben permitir todos la ruta pertinente. Esta NetworkPolicy solo de Ingress no restringe el Egress de database; agregue el perfil Egress seleccionado y el Egress del Pod de origen. Varios SG combinan sus permisos. Las NACL son **sin estado**, por lo que una regla de subnet que permite inbound5432 necesita una ruta de retorno coincidente hacia los puertos efímeros del cliente, además de reglas adecuadas en la subnet del cliente. Los fragmentos siguientes no sustituyen un conjunto completo de reglas ACL revisado.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: database-policy
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: database
  policyTypes: [Ingress]
  ingress:
    - from:
        - podSelector:
            matchLabels:
              database-access: "true"
      ports:
        - protocol: TCP
          port: 5432
```

```hcl
# Fragments for a DB subnet NACL and an explicitly reviewed client CIDR.
# Choose the client's actual ephemeral port range; also review its subnet NACL.
resource "aws_network_acl_rule" "database_inbound" {
  network_acl_id = var.database_network_acl_id
  rule_number    = 100
  egress         = false
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = var.application_subnet_cidr
  from_port      = 5432
  to_port        = 5432
}
resource "aws_network_acl_rule" "database_return" {
  network_acl_id = var.database_network_acl_id
  rule_number    = 100
  egress         = true
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = var.application_subnet_cidr
  from_port      = var.client_ephemeral_port_start
  to_port        = var.client_ephemeral_port_end
}
```

### Uso de Cilium en EKS

Elija **AWS VPC CNI chaining** o una migración CNI/IPAM completa diseñada por separado. En modo chaining AWS VPC CNI conserva la responsabilidad ENI/IPAM y Cilium adjunta su datapath. Conserve `aws-node`; eliminarlo no es un atajo de instalación. Revise el owner existente del add-on/Helm y evite motores de aplicación de políticas superpuestos. Los Pods existentes necesitan una recreación controlada antes de que se aplique la política chaining; planifique la interrupción y la reversión.

La guía oficial de chaining 1.20.1 ofrece estos valores, pero también documenta limitaciones L7/IPsec. Contiene salidas ilustrativas antiguas; no validan su entorno EKS actual. Prepare el repositorio/paquete de chart, verifique la procedencia y renderice primero:

```bash
# Render locally after verifying the official chart/package provenance.
# Rendering alone does not change a cluster or validate a migration.
helm template cilium cilium/cilium --version 1.20.1 \
  --namespace kube-system \
  --set cni.chainingMode=aws-cni \
  --set cni.exclusive=false \
  --set enableIPv4Masquerade=false \
  --set routingMode=native > cilium-reviewed.yaml
```

[AWS VPC CNI chaining — Cilium 1.20.1](https://docs.cilium.io/en/stable/installation/cni-chaining-aws-cni/)

## Herramientas de visualización {#visualization-tools}

### Editor de Cilium Network Policy

Un editor de políticas ayuda a crear políticas; **Hubble UI visualiza flujos de servicio observados**. Son herramientas distintas. Habilitar Hubble/UI cambia la configuración del clúster y corresponde al owner de la instalación. Con un servicio Hubble ya instalado y autenticado, inspeccione el servicio existente y use un port-forward local. No exponga la UI públicamente como atajo de depuración.

```bash
kubectl --context="$CONTEXT" -n kube-system port-forward --address=127.0.0.1 svc/hubble-ui 12000:80
```

### Comprobación de veredictos de políticas Cilium

Use una conexión Hubble autenticada. `DROPPED` incluye motivos distintos de las políticas; inspeccione el motivo de caída, la identidad del endpoint, la hora y la dirección. Una observación `FORWARDED` en un punto no garantiza la entrega de extremo a extremo.


```bash
# Inspect observed policy decisions
hubble observe --verdict DROPPED
hubble observe --verdict FORWARDED

# Check traffic for specific Pod
hubble observe --pod production/api-server

# Output in JSON format
hubble observe --output json | jq '.flow.verdict'
```

### UI de Calico Enterprise

La UI de administración Enterprise requiere el producto con licencia y su configuración real de servicio/TLS/autenticación; no se instala automáticamente con Calico Open Source. Inspeccione el nombre/puerto del servicio instalado y la política de acceso antes de hacer forwarding. No suponga que `cnx-manager` existe en todas las instalaciones.

### Herramientas de visualización de Network Policy

Use `kubectl get networkpolicy -n <namespace>` y `kubectl describe networkpolicy <name> -n <namespace>` para inspeccionar selectores/reglas de políticas Kubernetes, y las herramientas de flujo autenticadas del motor instalado para inspeccionar la aplicación. La disponibilidad de viewers/plugins de terceros y sus flags deben comprobarse frente a la versión actual de ese proyecto. Un gráfico de YAML por sí solo no puede demostrar la aplicación en dataplane.

### Pruebas de seguridad con Kube-hunter

kube-hunter es un escáner de exposición/seguridad de clústeres, no un verificador Allow/Deny de NetworkPolicy. Sus escaneos pueden generar tráfico intrusivo; use un destino/ámbito explícitamente aprobados y una versión/imagen revisada. No despliegue un escáner sin versión fijada en un namespace activo desde un tutorial general de políticas. Esta revisión no ejecutó un escáner.

## Mejores prácticas

### 1. Aplicar política de denegación predeterminada

```yaml
# Applies only to this production namespace
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: production
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
```

### 2. Principio de mínimo privilegio

Permita explícitamente solo el tráfico necesario:

```yaml
# Explicit and specific rules
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-minimal-access
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: api
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: frontend
      ports:
        - port: 8080
          protocol: TCP
```

### 3. Documentar políticas

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-ingress
  namespace: production
  annotations:
    description: "Allow traffic from frontend to API on port 8080"
    owner: "platform-team"
    review-ticket: "REPLACE_WITH_APPROVED_CHANGE"
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes: [Ingress]
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: frontend
      ports:
        - protocol: TCP
          port: 8080
```

### 4. Auditorías periódicas de políticas

Este inventario de solo lectura enumera por separado las líneas base de permisos vacíos en todo el namespace para Ingress y Egress. Se gestionan tanto `[]` vacío como arrays de reglas ausentes, mientras que una regla `{}` permite tráfico y no es una línea base de denegación. Los errores de API/autorización fallan en vez de mostrarse como cero políticas. Una línea base enumerada **no prueba aislamiento**: otras reglas Allow, políticas de extensión, Pods no cubiertos y el estado CNI aún requieren revisión.

```bash
#!/usr/bin/env bash
set -euo pipefail
: "${CONTEXT:?Set an approved kubectl context}"
work=$(mktemp -d "${TMPDIR:-/tmp}/network-policy-inventory.XXXXXX")
trap 'rm -rf -- "$work"' EXIT
if ! kubectl --context="$CONTEXT" --request-timeout=15s get namespaces -o json >"$work/namespaces.json"; then
  echo "UNKNOWN: namespace inventory failed." >&2
  exit 2
fi
if ! kubectl --context="$CONTEXT" --request-timeout=15s get networkpolicies -A -o json >"$work/policies.json"; then
  echo "UNKNOWN: policy inventory failed." >&2
  exit 2
fi
jq -n --slurpfile ns "$work/namespaces.json" --slurpfile np "$work/policies.json" '
  def directions:
    (.spec.policyTypes // []) as $types |
    if ($types | length) > 0 then $types
    else ["Ingress"] + (if ((.spec.egress // []) | length) > 0 then ["Egress"] else [] end)
    end;
  def selects_all:
    ((.spec.podSelector.matchLabels // {}) | length) == 0 and
    ((.spec.podSelector.matchExpressions // []) | length) == 0;
  def empty_baseline($direction; $rules):
    select(selects_all and ((directions | index($direction)) != null) and
           ((.spec[$rules] // []) | length) == 0) | .metadata.name;
  {
    note: "Inventory only: other allow rules, extension policies and CNI enforcement are not evaluated.",
    namespaces: [
      $ns[0].items[] | .metadata.name as $name |
      [$np[0].items[] | select(.metadata.namespace == $name)] as $policies |
      {
        namespace: $name,
        policyCount: ($policies | length),
        ingressBaselines: [$policies[] | empty_baseline("Ingress"; "ingress")],
        egressBaselines: [$policies[] | empty_baseline("Egress"; "egress")]
      }
    ]
  }
'
```

## Resumen

Las Kubernetes Network Policies son un mecanismo de seguridad fundamental para controlar la comunicación de Pods dentro de los clústeres:

1. **NetworkPolicy básico**: con ámbito de namespace, admite podSelector/namespaceSelector/ipBlock
2. **Extensiones de Cilium**: políticas L7, políticas basadas en DNS FQDN, políticas para todo el clúster
3. **Extensiones de Calico**: GlobalNetworkPolicy, NetworkSet, políticas basadas en Tier
4. **Consideraciones de EKS**: activación VPC CNI NetworkPolicy, Security Groups para Pods, ClusterNetworkPolicy y control de Egress basado en DNS (FQDN)

### Recomendaciones

- Aplique una política de denegación predeterminada a todos los namespaces de producción
- Permita solo el tráfico necesario siguiendo el principio de mínimo privilegio
- Realice auditorías y pruebas de políticas periódicamente
- Considere Cilium cuando se necesiten políticas L7

---

## Referencias

- [Documentación oficial de Kubernetes Network Policies](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Documentación de Cilium Network Policy](https://docs.cilium.io/en/stable/security/policy/index.html)
- [Documentación de Calico Network Policy](https://docs.tigera.io/calico/latest/reference/resources/networkpolicy)
- [Mejores prácticas de seguridad de EKS - Seguridad de red](https://docs.aws.amazon.com/eks/latest/best-practices/network-security.html)
- [Políticas de seguridad de red mejoradas de Amazon EKS (2025-12-15)](https://aws.amazon.com/about-aws/whats-new/2025/12/amazon-eks-enhanced-network-security-policies/)

- [Security groups de Pods de EKS](https://docs.aws.amazon.com/eks/latest/userguide/security-groups-for-pods.html)
- [Calico Tier](https://docs.tigera.io/calico/latest/reference/resources/tier)
- [Calico NetworkSet](https://docs.tigera.io/calico/latest/reference/resources/networkset)
