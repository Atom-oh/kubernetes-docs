# Políticas de red

> **Referencia de revisión**: OpenAPI de Kubernetes 1.35, Cilium 1.20.3, Calico 3.32.2 y documentación actual de AWS. Las comprobaciones sin conexión no establecen la compatibilidad con el clúster.
> **Última actualización**: 16 de octubre de 2026

Las NetworkPolicy de Kubernetes son reglas de firewall que controlan el tráfico entre Pods. Este documento cubre NetworkPolicy básica y las extensiones de Cilium/Calico. Las secciones son ejemplos independientes; combinar todas las políticas cambiaría los permisos efectivos. No se realizó ningún despliegue en un clúster o en la nube ni ninguna prueba de conectividad en vivo.

## Tabla de contenido

1. [Descripción general de las políticas de red](#network-policy-overview)
2. [Especificación de NetworkPolicy de Kubernetes](#kubernetes-networkpolicy-spec)
3. [Políticas de denegación predeterminada](#default-deny-policies)
4. [Orden y evaluación de las políticas](#policy-order-and-evaluation)
5. [Extensiones de políticas de red de Cilium](#cilium-network-policy-extensions)
6. [Extensiones de políticas de red de Calico](#calico-network-policy-extensions)
7. [Patrones de diseño](#design-patterns)
8. [Pruebas de políticas de red](#testing-network-policies)
9. [Consideraciones para EKS](#eks-considerations)
10. [Herramientas de visualización](#visualization-tools)

---

## Descripción general de las políticas de red {#network-policy-overview}

### ¿Qué es una política de red?

NetworkPolicy de Kubernetes selecciona Pods en su propio espacio de nombres y controla el tráfico de entrada y salida que admite. Un Pod que no tenga una política que lo seleccione para una dirección no está aislado por NetworkPolicy en esa dirección; el enrutamiento, los grupos de seguridad, las NACL y otros motores de políticas aún pueden impedir la conectividad.

**Ambos extremos deben permitir** una conexión entre Pods: las reglas efectivas de salida del origen y las reglas efectivas de entrada del destino deben permitirla. El tráfico de respuesta de una conexión permitida se permite implícitamente. Un complemento de red compatible implementa las políticas de forma asíncrona; la existencia de un objeto de API no demuestra que se apliquen. El tráfico de nodos/hostNetwork y los protocolos que no sean TCP/UDP/SCTP requieren una revisión específica de la implementación. Los diagramas siguientes muestran la intención de la política, no garantizan la alcanzabilidad.

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

### Características de las políticas de red

| Propiedad | Descripción |
|----------|-------------|
| **Limitada al espacio de nombres** | NetworkPolicy se aplica a los recursos de un espacio de nombres |
| **Aditiva** | Las reglas de permiso de las NetworkPolicy de Kubernetes que seleccionan un Pod se combinan en una unión para cada dirección; las denegaciones de Cilium, los niveles de Calico y las políticas administrativas de AWS tienen semánticas propias |
| **Aplicación selectiva** | Los Pods de destino se especifican mediante podSelector |
| **Control direccional** | Control independiente de Ingress (entrada) y Egress (salida) |
| **Dependiente de CNI** | El complemento CNI debe admitir NetworkPolicy |

### Compatibilidad con NetworkPolicy de CNI

| CNI | NetworkPolicy básica | Extensiones | Política L7 |
|-----|---------------------|------------|-----------|
| **Cilium** | ✓ | CiliumNetworkPolicy, CiliumClusterwideNetworkPolicy | ✓ |
| **Calico** | ✓ | GlobalNetworkPolicy, NetworkSet, Tier | Integración opcional con Istio/Dikastes; verifique el producto y las versiones implementados |
| **Weave Net (proyecto archivado)** | Compatibilidad histórica | Referencia heredada; evalúe una implementación mantenida para nuevos despliegues | ✗ |
| **Solo Flannel** | No aplica políticas por sí solo | Se necesita un motor de políticas compatible independiente | ✗ |
| **Amazon VPC CNI** | ✓ cuando está habilitado en nodos Linux EC2 compatibles | NetworkPolicy estándar; ClusterNetworkPolicy con VPC CNI 1.21+ | Egress DNS en nodos EKS Auto Mode; consulte las consideraciones para EKS |

---

## Especificación de NetworkPolicy de Kubernetes {#kubernetes-networkpolicy-spec}

### Estructura básica

Especifique `policyTypes` explícitamente. Si se omite, Kubernetes toma Ingress como valor predeterminado y agrega Egress cuando hay al menos una regla de salida. Las matrices de reglas vacías, por sí solas, no implican ambas direcciones.

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

Selecciona los Pods a los que se aplica la política en su propio espacio de nombres. Los siguientes son fragmentos alternativos de la especificación, no recursos de API independientes.

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

Selecciona espacios de nombres por sus etiquetas, incluido el espacio de nombres actual si coincide. `name` no es una etiqueta de espacio de nombres que se asigne automáticamente. Use la etiqueta inmutable integrada `kubernetes.io/metadata.name` para un nombre de espacio de nombres exacto; restrinja quién puede cambiar las etiquetas de tenencia personalizadas.

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

**Nota:** distinción entre AND y OR cuando se usan juntos `namespaceSelector` y `podSelector`:

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

Un `ipBlock` permite un CIDR menos los rangos `except` de esa regla. Una excepción no es una denegación global y otra política puede permitirla. La traducción de direcciones de Service o balanceador de carga puede cambiar el origen o el destino que ve el CNI; verifique la ruta real. Los CIDR de documentación siguientes son ilustrativos, no extremos de producción alcanzables.

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

Especifique los puertos y protocolos permitidos. `endPort` requiere un puerto inicial numérico y compatibilidad del CNI con rangos; un puerto con nombre no puede ser el inicio de un rango. La aceptación por parte de la API no demuestra que todos los complementos apliquen la regla.

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

Una línea base vacía no aporta permisos; otras políticas que seleccionen el Pod aún pueden permitir el tráfico. El comportamiento de las conexiones existentes después de un cambio de política depende de la implementación y debe probarse por separado.

### Denegación predeterminada de entrada

Una línea base de aislamiento de entrada que no permite nada por sí misma. Otras políticas que seleccionen el Pod aún pueden permitir el tráfico de entrada:

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

### Denegación predeterminada de salida

Una línea base de aislamiento de salida que no permite nada por sí misma. Otras políticas que seleccionen el Pod aún pueden permitir el tráfico de salida:

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

Este perfil supone CoreDNS basado en Pods en `kube-system` con `k8s-app=kube-dns`. Permite TCP y UDP en el puerto 53. Si DNS tiene aislamiento de entrada, su política también debe permitir el acceso de los clientes. NodeLocal DNSCache y CoreDNS local al nodo en Auto Mode necesitan el perfil real de la ruta/IP del resolvedor; no aplique allí sin cambios este selector de Pods.

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

Se incluyen ambas direcciones del flujo frontend→API. Esto no permite el tráfico entrante al frontend ni el flujo API→database; agregue únicamente los flujos revisados. Use la suposición anterior de DNS basado en Pods.

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

## Orden y evaluación de las políticas {#policy-order-and-evaluation}

### Reglas de evaluación de políticas

Para cada extremo y dirección, evalúe únicamente las **NetworkPolicy de Kubernetes** que lo seleccionen, como se indica a continuación. Después, compruebe la dirección del otro extremo y los demás controles de red. Una política que solo rige Ingress no aísla Egress.

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

Cuando varias NetworkPolicy se aplican al mismo Pod, todas las reglas de las políticas se combinan (unión):

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

**Resultado:** Ingress de la API permite Pods frontend en el puerto 8080 y Pods del espacio de nombres monitoring en los puertos 8080/9090. Sus reglas de Egress, los procesos que realmente escuchan y los demás controles de red también deben permitir la conexión.

### Orden de evaluación de las políticas

La API de NetworkPolicy de Kubernetes no tiene prioridades ni una regla explícita de denegación. La unión de permisos no describe el orden/las acciones de los niveles de políticas de Calico, las denegaciones explícitas de Cilium ni la evaluación de políticas administrativas de AWS:

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

## Extensiones de políticas de red de Cilium {#cilium-network-policy-extensions}

Estos ejemplos utilizan el esquema de políticas publicado para Cilium 1.20.3; no indican que haya que actualizar todos los clústeres. Las reglas HTTP necesitan una ruta de proxy L7 compatible. El encadenamiento de AWS VPC CNI tiene limitaciones documentadas para funciones avanzadas, incluidas las políticas L7; no dé por sentado que estos ejemplos HTTP funcionan en ese modo. Una identidad de seguridad numérica de Cilium es una asignación para un conjunto de etiquetas, no un ID de aplicación permanente.

### CiliumNetworkPolicy

Cilium amplía la NetworkPolicy básica con funciones más potentes.

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

Las reglas HTTP de Cilium filtran las solicitudes visibles para su proxy L7; no autentican claves de API ni establecen roles de administrador. Una persona que llama puede enviar un encabezado `X-User-Role`. Este ejemplo filtra métodos, rutas y un `Content-Type` exacto. Aplique la autenticación y la autorización en la aplicación o en una puerta de enlace autenticada. El tráfico TLS de extremo a extremo no se descifra automáticamente para inspeccionar HTTP. Revise otras políticas que puedan permitir el mismo tráfico en L4.

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

[API HTTP (Cilium 1.20.3)](https://github.com/cilium/cilium/blob/v1.20.3/pkg/policy/api/http.go)

### Política Kafka L7

El esquema CNP publicado para Cilium 1.20.3 admite reglas L7 de HTTP y DNS, pero no tiene `rules.kafka`. La receta anterior con `role`, `topic` y `clientID` no es una API actual desplegable. Restrinja la conectividad con el broker mediante una política de red y, después, aplique los permisos de productor/consumidor para `orders` y `events` mediante la autenticación de Kafka y las ACL. Un ID de cliente no es una entidad autenticada.

Este ejemplo L4 presupone un listener TLS del broker ya configurado en TCP 9093, clientes en el mismo espacio de nombres y Egress de clientes/DNS autorizado por separado. No configura TLS, ACL del broker ni permisos de temas.

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

[Esquema CNP (Cilium 1.20.3)](https://github.com/cilium/cilium/blob/v1.20.3/pkg/k8s/apis/cilium.io/client/crds/v2/ciliumnetworkpolicies.yaml)

### Política DNS L7

Este ejemplo utiliza CoreDNS basado en Pods. `ANY` en el puerto 53 cubre UDP y TCP. El permiso para consultas DNS y el permiso para conectarse a una IP devuelta son independientes: resolver el nombre de la base de datos que aparece a continuación no permite conexiones a esa base de datos. Reemplace el dominio de ejemplo, tenga en cuenta los sufijos de búsqueda DNS, la caché y el TTL, y verifique el perfil real del resolvedor. Las reglas FQDN aprenden IP a partir de DNS; no autentican a un inquilino de SaaS ni sustituyen la autorización TLS/de la aplicación.

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

El recurso tiene alcance de clúster, pero su selector limita explícitamente la selección a `production/app=api`. Permite el tráfico de Pods de puerta de enlace por TCP 8080. Solo controla Ingress; el aislamiento de Egress/DNS y el Egress propio de la puerta de enlace requieren sus políticas correspondientes. El ejemplo anterior que permitía todos los extremos/todo el mundo en el clúster no era una política de denegación predeterminada.

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

### Política de Cilium basada en entidades

`host` incluye el nodo local y sus contenedores host-network; `cluster` incluye más que los Pods de aplicaciones. `world` abarca extremos fuera del clúster y no es una lista de permisos detallada para Internet/SaaS. Use reglas CIDR/FQDN explícitas para restringir el acceso externo. Este ejemplo solo permite el acceso TCP 443 de un cliente de la API de Kubernetes etiquetado; configure por separado el extremo de la API, la confianza TLS, las credenciales y RBAC. La identidad de origen puede cambiar a través de las rutas de red del plano de control administrado, así que inspeccione la identidad real del flujo en lugar de ampliar Ingress a todo el clúster.

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

## Extensiones de políticas de red de Calico {#calico-network-policy-extensions}

Los ejemplos de políticas/Tier siguen los recursos de Calico Open Source 3.32.2. `projectcalico.org/v3` requiere el servidor de API de Calico compatible o el flujo de trabajo correspondiente de `calicoctl`; no es la API de almacenamiento sin procesar de Kubernetes `crd.projectcalico.org/v1`. Verifique el almacén de datos/la API instalados antes de aplicar. Las acciones ordenadas y la delegación entre niveles de Calico son distintas de la API aditiva de NetworkPolicy de Kubernetes.

La documentación actual de Open Source también describe la [integración de capa de aplicación Istio/Dikastes](https://docs.tigera.io/calico/latest/network-policy/istio/app-layer-policy). La API HTTPMatch requiere esa configuración independiente y admite reglas de permiso para Ingress. Los ejemplos de Calico que siguen cubren políticas L3/L4; esta revisión no desplegó ni probó la integración L7.

### NetworkPolicy de Calico

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

Estos dos recursos globales seleccionan únicamente cargas de trabajo del espacio de nombres `production`. Un `selector: all()` sin restricciones también puede afectar a los extremos del host; no aplique una denegación en todo el clúster sin un alcance explícito y un método de recuperación. Dentro del nivel, se evalúa primero el valor menor de `order`. El ejemplo permite DNS basado en Pods y proporciona, por lo demás, una línea base de denegación; agregue los flujos de aplicación revisados y tenga en cuenta las acciones de los niveles superiores.

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

Los selectores de NetworkSet coinciden con las etiquetas de `metadata.labels`, no con el nombre del recurso. El primer conjunto tiene ámbito de espacio de nombres; el conjunto bloqueado es global y lo utiliza el ejemplo del nivel de seguridad que aparece a continuación. Todos los CIDR son rangos de documentación y deben reemplazarse por destinos revisados. El ejemplo de Egress permite TCP 443 al conjunto etiquetado del espacio de nombres; DNS es una regla independiente.

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

### Políticas basadas en niveles

Los niveles están disponibles en la versión de Calico Open Source a la que se hace referencia, no solo en Enterprise. Si no se aplica ninguna regla de un nivel que selecciona tráfico, su acción predeterminada es `Deny`. Por ello, el nivel deny-known-threats usa explícitamente `defaultAction: Pass` para que el tráfico no relacionado pueda llegar a las políticas posteriores. `Pass` es delegación, no permiso. `global()` debe estar en `namespaceSelector`; el selector de etiquetas independiente identifica el GlobalNetworkSet. Defina las políticas del nivel de aplicación y verifique el comportamiento de cualquier perfil/nivel predeterminado final antes del despliegue; crear un Tier vacío no es una política completa de aislamiento de aplicaciones.

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

Estos son **perfiles de políticas alternativos**, no un conjunto para aplicar en bloque. Reutilizar `production` no hace compatibles los ejemplos que no guardan relación: sus reglas de permiso se acumularían. Prepare primero los espacios de nombres, las etiquetas de las cargas de trabajo, los puertos de escucha y el perfil DNS real. Los ejemplos se comprobaron localmente en cuanto a esquema/intención, pero no se ejecutaron en un clúster.

### Microsegmentación

Este perfil permite frontend→API por TCP 8080 y API→database por TCP 5432 en ambos lados, además de DNS. Deliberadamente, no hay Egress a Internet ni Ingress externo al frontend. Si se necesita, agregue un CIDR/puerto de destino aprobado o un perfil de puerta de enlace de Egress autenticada; excluir RFC1918 de 0.0.0.0/0 no constituye una lista de permisos para SaaS.

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

### Aislamiento de espacios de nombres

El perfil del equipo incluye Ingress **y Egress** del mismo equipo, además de DNS. Los servicios compartidos también necesitan Ingress de destino que permita team-a y un listener TLS 443 real. Restrinja la administración de etiquetas de espacios de nombres; una etiqueta de equipo no es un límite de confianza independiente.

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

### Protección de bases de datos

Debe existir el espacio de nombres `database`. Los clientes de producción y los Pods de monitoring necesitan sus propios permisos de Egress. Las reglas de pares TCP 5432 solo permiten el transporte de replicación de PostgreSQL que se presupone; configure aparte la autenticación/TLS de la base de datos. TCP 9187 presupone que se instaló un exportador independiente.

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

Suponga que ya existe una carga de trabajo `gateway-system/app=edge-proxy` que termina el TLS de los clientes y puede llegar a los Pods web por TCP 80. La política de Egress de la puerta de enlace queda fuera de este espacio de nombres. Ingress y Egress para los pares de datos usan TCP 5432/6379; no se infieren los puertos adicionales de replicación, bus de clúster o copia de seguridad, ya que dependen de la base de datos elegida. En un despliegue real, separe los selectores de PostgreSQL y Redis.

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

## Pruebas de políticas de red {#testing-network-policies}

### Pruebas con netshoot

Use Pods de diagnóstico aprobados y ya aprovisionados, con imágenes fijadas y permisos revisados. Elija etiquetas de origen, espacio de nombres y ubicación de nodo que realmente pongan a prueba la política; un Pod genérico sin etiquetas no representa la aplicación. Aprovisionar netshoot crea una carga de trabajo y puede entrar en conflicto con la admisión de Pod Security. No cree ni elimine un nombre fijo compartido como `test-pod` en un script de observación. Ejecute pruebas únicamente contra extremos de prueba de su propiedad.

### Pruebas con kubectl exec

Establezca explícitamente el contexto, el espacio de nombres, el Pod existente y el contenedor. Que DNS funcione no significa que TCP funcione; un rechazo de conexión, un listener que no esté en buen estado, un error TLS y una caída por política son resultados distintos. Estos comandos solo prueban conectividad y no imprimen cuerpos de respuesta. No se ejecutaron contra un clúster durante esta revisión.

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

`cilium connectivity test` crea recursos de prueba y tráfico; no es un comando de estado de solo lectura. Utilice un clúster/espacio de nombres aislado aprobado, una CLI e imágenes compatibles, destinos externos definidos y un plan de limpieza. Consulte `cilium connectivity test --help` para ver los filtros de la CLI instalada, en vez de suponer que siguen existiendo nombres de pruebas históricos. Que la suite pase no demuestra todas las políticas de aplicación ni todas las funciones de encadenamiento de CNI.

### Script de prueba automatizada

Este script solo ejecuta pruebas curl acotadas en dos Pods existentes; no crea ni elimina recursos del clúster. Establezca `CONTEXT`, `NAMESPACE`, `ALLOW_POD`, `DENIED_POD`, `PROBE_CONTAINER` y un `TARGET_URL` que no contenga secretos y termine en `/health`. Ambos contenedores necesitan `sh` y `curl`. El primer Pod es un control positivo conocido como permitido para el mismo destino. Las respuestas de error HTTP también confirman que hay conectividad de red, porque esta prueba no valida el estado de la aplicación.

El código de salida 1 significa que el sujeto bloqueado se conectó de forma inesperada; el código 2 indica resultado desconocido/error; el código 3 indica tiempo de espera que requiere corroboración. Un tiempo de espera **nunca** se convierte automáticamente en PASS: correlacione el origen/destino/puerto/hora exactos con un veredicto de descarte por política del CNI, mientras comprueba el estado de los extremos, las rutas y los controles de SG/NACL. Las pruebas locales simuladas no afirman que se haya aplicado ninguna política en vivo.

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

## Consideraciones para EKS {#eks-considerations}

### Amazon VPC CNI y NetworkPolicy

Amazon VPC CNI admite políticas de red después de habilitarlas. La guía actual de AWS exige VPC CNI 1.21+ para las políticas estándar y administrativas, una plataforma EKS compatible y un kernel Linux 5.10 o posterior. La aplicación de políticas se limita a los nodos Linux EC2 compatibles, no a Fargate ni a Windows. Use una versión de EKS compatible actualmente y verifique la versión compatible del complemento; no deduzca la compatibilidad de EKS a partir de las versiones de Kubernetes upstream.

Para un complemento de VPC CNI **administrado por EKS**, conserve su configuración existente y establezca el valor de cadena documentado `"enableNetworkPolicy": "true"`. El siguiente procedimiento modifica el clúster seleccionado después de revisarlo; no actualiza la versión del complemento. Si la versión instalada no es compatible, deténgase y siga primero el procedimiento de actualización documentado.

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

Compruebe el estado de la actualización y el comportamiento de las políticas antes del despliegue. `--resolve-conflicts PRESERVE` no combina por usted un documento JSON de reemplazo; el ejemplo conserva explícitamente los valores existentes. Guarde la instantánea para poder recuperarse. Una instalación administrada por Helm usa el chart/valores revisados; establezca `enableNetworkPolicy: true`. No transfiera su administración mediante este comando para complementos administrados. Establecer la variable de entorno inventada `ENABLE_NETWORK_POLICY` no es el procedimiento de habilitación.

El modo de inicio estándar puede permitir inicialmente el tráfico de un Pod nuevo hasta que se programe su política. `NETWORK_POLICY_ENFORCING_MODE=strict` inicia los Pods aptos en estado denegado y requiere una matriz completa de permisos, incluido DNS; cambiarlo puede interrumpir las cargas de trabajo. Los Pods administrados por controladores son el objetivo de prueba más fiable. La aplicación se realiza en la interfaz principal del Pod, así que inspeccione por separado las interfaces adicionales, el Egress de IPv6 a IPv4, el uso de red del host y NAT. No instale dos motores para administrar las mismas políticas estándar ni elimine `aws-node` como atajo para una migración.

### Políticas mejoradas de seguridad de red de EKS (diciembre de 2025)

> **Anunciado**: 15 de diciembre de 2025 · [Fuente](https://aws.amazon.com/about-aws/whats-new/2025/12/amazon-eks-enhanced-network-security-policies/)

La función existe, pero sus recursos usan **`networking.k8s.aws/v1alpha1`**. `ClusterNetworkPolicy` tiene alcance de clúster y requiere `tier`; para Egress basado en DNS se utiliza `ApplicationNetworkPolicy` en el ejemplo de espacio de nombres que aparece a continuación. Que las políticas estándar/administrativas de VPC CNI sean compatibles con Linux EC2 no significa que sean compatibles con todos los modos de cómputo. Las reglas DNS solo se aplican en **instancias EC2 lanzadas con Auto Mode**, incluso en un clúster mixto.

**Requisito previo de Auto Mode:** habilite su Network Policy Controller antes de aplicar las políticas siguientes. Actualizar un complemento `vpc-cni` administrado por EKS es una ruta distinta y no habilita la aplicación de políticas para un clúster de Auto Mode puro. El ajuste necesario es el ConfigMap `kube-system/amazon-vpc-cni`, `data.enable-network-policy-controller: "true"`. El procedimiento siguiente conserva los demás datos del ConfigMap con un parche de fusión, solo lo crea si no existe y se detiene si falla la lectura o escritura. Revise el contexto del clúster y la configuración existente antes de ejecutarlo.

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

Después de habilitarlo, inspeccione los objetos `PolicyEndpoints` correspondientes y pruebe tanto el tráfico permitido como el denegado en los nodos Auto Mode seleccionados. Una opción guardada o un objeto de política aceptado no demuestra que se aplique. Consulte la [configuración de políticas de red de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/auto-net-pol.html). No se realizó ninguna prueba de aplicación de políticas en un clúster para esta auditoría de documentación.

Este ejemplo del nivel Admin deniega el tráfico entrante de Pods seleccionados por espacio de nombres a `isolated-demo`, incluidos los Pods de ese mismo espacio de nombres. No es un firewall completo para tráfico externo/de host-network ni una política de permisos DNS. Admin Deny no puede anularse con una NetworkPolicy del espacio de nombres. Revise la CRD realmente instalada antes de agregar otras acciones: el esquema actual upstream del controlador de AWS denomina `Accept` a la acción que permite, mientras que el texto de la guía de usuario usa “Allow”.

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

El ejemplo FQDN selecciona `app=backend` en `production`. **Reemplace `10.100.0.10/32` por la IP real de CoreDNS de Auto Mode de su clúster**: es la dirección de red del CIDR de Service más 10 (`::a/128` para IPv6). En Auto Mode puro, CoreDNS se ejecuta en el nodo; un selector de Pods convencional para CoreDNS no es equivalente. Permita DNS tanto por TCP como por UDP. Use un nombre de recurso único que no coincida con una NetworkPolicy de ese espacio de nombres.

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

El proxy DNS observa las respuestas permitidas y sus TTL; después, la ruta de datos permite las IP/puertos de destino aprendidos. Esto no autentica una cuenta de SaaS ni demuestra la identidad HTTP del par; hay que probar las IP compartidas y el comportamiento de DNS. Siguen siendo relevantes la verificación de certificados TLS, la autorización de la aplicación, las rutas y las reglas de Route 53 DNS Firewall. Las demás políticas aplicables y las rutas directas al backend deben revisarse en conjunto.

[NetworkPolicy de AWS](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html) · [Configuración](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy-configure.html) · [Políticas de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/auto-net-pol.html)

### Grupos de seguridad para Pods

Este ejemplo de asociación presupone el EKS VPC Resource Controller, sus permisos de **cluster-role**, nodos Linux EC2 compatibles con trunking y una configuración revisada de VPC CNI. La guía actual de AWS excluye Windows y EKS Auto Mode. Fargate utiliza un modelo independiente de grupos de seguridad para Pods y no obtiene compatibilidad con NetworkPolicy de VPC CNI por el mero hecho de tener un grupo de seguridad. Aplique la asociación a los nuevos Pods de carga de trabajo coincidentes a través de su propietario; los Pods existentes no se actualizan automáticamente.

Para Calico con grupos de seguridad para Pods, AWS documenta VPC CNI 1.11.0+ con `POD_SECURITY_GROUP_ENFORCING_MODE=standard`; use también los requisitos actuales de CNI, en vez de tratar ese mínimo como una versión recomendada. El SNAT externo del modo estándar puede usar el grupo de seguridad del nodo en vez del grupo de seguridad del Pod. Verifique la ruta exacta. El Pod de PostgreSQL básico anterior no tenía credenciales ni almacenamiento y no era un despliegue funcional de base de datos.

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

El fragmento de Terraform permite Ingress a la base de datos desde un único grupo de seguridad de aplicación revisado y no inicia nuevas conexiones de Egress. El seguimiento de los grupos de seguridad permite el tráfico de respuesta de estado; agregue aparte solo el Egress necesario para DNS, replicación, copias de seguridad o destinos externos. Las variables son entradas existentes del operador; no se ejecutó ningún plan/aplicación de Terraform.

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

### Combinación de controles a nivel de VPC con NetworkPolicy

NetworkPolicy, los grupos de seguridad aplicados realmente y las NACL deben permitir la ruta pertinente. Esta NetworkPolicy solo de Ingress no restringe el Egress de la base de datos; agregue el perfil de Egress seleccionado y el Egress del Pod de origen. Los permisos de varios grupos de seguridad se combinan. Las NACL son **sin estado**, de modo que una regla de subred que permita entrada por el puerto 5432 necesita una ruta de retorno correspondiente a los puertos efímeros del cliente, además de reglas adecuadas en la subred del cliente. Los fragmentos siguientes no sustituyen un conjunto completo y revisado de reglas de ACL.

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

Elija **encadenamiento de AWS VPC CNI** o una migración completa de CNI/IPAM diseñada por separado. En el modo de encadenamiento, AWS VPC CNI conserva la responsabilidad de ENI/IPAM y Cilium conecta su plano de datos. Conserve `aws-node`; eliminarlo no es un atajo de instalación. Revise quién administra el complemento/chart existente y evite motores de aplicación de políticas superpuestos. Es necesario recrear de forma controlada los Pods existentes antes de que se apliquen las políticas de encadenamiento; planifique la interrupción y la reversión.

La guía oficial de encadenamiento 1.20.3 proporciona estos valores, pero también documenta limitaciones de L7/IPsec. Incluye salidas ilustrativas antiguas, que no validan el entorno EKS actual. Prepare el repositorio/paquete del chart, verifique su procedencia y renderícelo primero:

```bash
# Render locally after verifying the official chart/package provenance.
# Rendering alone does not change a cluster or validate a migration.
helm template cilium cilium/cilium --version 1.20.3 \
  --namespace kube-system \
  --set cni.chainingMode=aws-cni \
  --set cni.exclusive=false \
  --set enableIPv4Masquerade=false \
  --set routingMode=native > cilium-reviewed.yaml
```

[Encadenamiento de AWS VPC CNI (Cilium 1.20.3)](https://docs.cilium.io/en/stable/installation/cni-chaining-aws-cni/)

## Herramientas de visualización {#visualization-tools}

### Editor de políticas de red de Cilium

Un editor de políticas ayuda a crear políticas; **Hubble UI visualiza los flujos de servicio observados**. Son herramientas distintas. Habilitar Hubble/UI cambia la configuración del clúster y corresponde al responsable de la instalación. Si ya hay un servicio Hubble autenticado e instalado, inspeccione el servicio existente y use un reenvío de puertos local. No exponga la interfaz de usuario públicamente como atajo de depuración.

```bash
kubectl --context="$CONTEXT" -n kube-system port-forward --address=127.0.0.1 svc/hubble-ui 12000:80
```

### Comprobación de veredictos de políticas de Cilium

Use una conexión Hubble autenticada. `DROPPED` incluye motivos distintos de las políticas; inspeccione el motivo de la caída, la identidad del extremo, la hora y la dirección. Una observación `FORWARDED` en un punto no garantiza la entrega de extremo a extremo.


```bash
# Inspect observed policy decisions
hubble observe --verdict DROPPED
hubble observe --verdict FORWARDED

# Check traffic for specific Pod
hubble observe --pod production/api-server

# Output in JSON format
hubble observe --output json | jq '.flow.verdict'
```

### Interfaz de usuario de Calico Enterprise

La interfaz de administración de Enterprise requiere el producto con licencia y su configuración real de servicio/TLS/autenticación; Calico Open Source no la instala automáticamente. Inspeccione el nombre/puerto del servicio instalado y la política de acceso antes de reenviar puertos. No suponga que `cnx-manager` existe en todas las instalaciones.

### Herramientas de visualización de políticas de red

Use `kubectl get networkpolicy -n <namespace>` y `kubectl describe networkpolicy <name> -n <namespace>` para inspeccionar los selectores/reglas de las políticas de Kubernetes, y las herramientas autenticadas de flujo del motor instalado para inspeccionar su aplicación. La disponibilidad de visores/complementos de terceros y sus indicadores debe comprobarse en la versión actual del proyecto correspondiente. Un gráfico basado solo en YAML no puede demostrar la aplicación en el plano de datos.

### Pruebas de seguridad con Kube-hunter

kube-hunter es un escáner de exposición/seguridad de clústeres, no un verificador de permisos/denegaciones de NetworkPolicy. Sus análisis pueden generar tráfico intrusivo; use un objetivo/alcance aprobado explícitamente y una versión/imagen revisada. No despliegue un escáner sin fijar su versión en un espacio de nombres activo a partir de un tutorial general de políticas. Esta revisión no ejecutó ningún escáner.

## Prácticas recomendadas

### 1. Aplicar una política de denegación predeterminada

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

### 2. Principio de privilegio mínimo

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

### 3. Documentar las políticas

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

Este inventario de solo lectura enumera por separado las líneas base vacías de permisos aplicadas a todo un espacio de nombres para Ingress y Egress. Se admiten tanto `[]` como la ausencia de matrices de reglas, mientras que una regla `{}` permite el tráfico y no constituye una línea base de denegación. Los errores de API/autorización provocan un fallo en vez de parecer que no hay políticas. Una línea base enumerada **no demuestra el aislamiento**: es necesario revisar las demás reglas de permiso, las políticas de extensión, los Pods no cubiertos y el estado de CNI.

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

## Conexión de NetworkPolicy con la inspección perimetral

NetworkPolicy aplica las conexiones de Pods mediante un CNI compatible; no crea todas las rutas de WAF o de firewall central. No suponga que el tráfico en el mismo nodo, dentro de la VPC, por PrivateLink, por peering o IPv6 atraviesa automáticamente la inspección central de TGW.

Conecte las aplicaciones públicas a la [protección de WAF/origen](./14-waf-edge-api-security.md) y el tráfico de salida/entre VPC a [Palo Alto/Fortinet](./15-ngfw-paloalto-fortinet.md) y [GWLB/GENEVE](./16-gwlb-geneve-inspection.md). Verifique las tuplas SNAT de Pod/nodo y de solicitud/respuesta, y pruebe los resultados de las políticas por separado del paso por los dispositivos. Consulte [Defensa en profundidad y respuesta a incidentes](./13-defense-in-depth-incident-response.md) para investigar webhooks y permisos de Secret.

## Resumen

Las NetworkPolicy de Kubernetes son un mecanismo de seguridad fundamental para controlar la comunicación entre Pods en los clústeres:

1. **NetworkPolicy básica**: limitada al espacio de nombres, admite podSelector/namespaceSelector/ipBlock
2. **Extensiones de Cilium**: políticas L7, políticas DNS basadas en FQDN, políticas para todo el clúster
3. **Extensiones de Calico**: GlobalNetworkPolicy, NetworkSet, políticas basadas en Tier
4. **Consideraciones para EKS**: activación de NetworkPolicy en VPC CNI, grupos de seguridad para Pods, ClusterNetworkPolicy y control de Egress basado en DNS (FQDN)

### Recomendaciones

- Aplique una política de denegación predeterminada a todos los espacios de nombres de producción
- Permita solo el tráfico necesario siguiendo el principio de privilegio mínimo
- Realice auditorías y pruebas de políticas periódicas
- Considere Cilium cuando se necesiten políticas L7

---

## Referencias

- [Documentación oficial de Network Policies de Kubernetes](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Documentación de políticas de red de Cilium](https://docs.cilium.io/en/stable/security/policy/index.html)
- [Documentación de políticas de red de Calico](https://docs.tigera.io/calico/latest/reference/resources/networkpolicy)
- [Prácticas recomendadas de seguridad de EKS: seguridad de red](https://docs.aws.amazon.com/eks/latest/best-practices/network-security.html)
- [Políticas mejoradas de seguridad de red de Amazon EKS (2025-12-15)](https://aws.amazon.com/about-aws/whats-new/2025/12/amazon-eks-enhanced-network-security-policies/)

- [Grupos de seguridad para Pods de EKS](https://docs.aws.amazon.com/eks/latest/userguide/security-groups-for-pods.html)
- [Tier de Calico](https://docs.tigera.io/calico/latest/reference/resources/tier)
- [NetworkSet de Calico](https://docs.tigera.io/calico/latest/reference/resources/networkset)
