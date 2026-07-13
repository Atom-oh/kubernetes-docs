# Políticas de red

> **Versiones compatibles**: Kubernetes 1.31, 1.32, 1.33
> **Última actualización**: July 3, 2026

Las Network Policies de Kubernetes son reglas de firewall que controlan el tráfico entre Pods. Este documento cubre todo, desde NetworkPolicy básica hasta las extensiones de Cilium y Calico.

## Tabla de contenidos

1. [Descripción general de Network Policy](#network-policy-overview)
2. [Especificación NetworkPolicy de Kubernetes](#kubernetes-networkpolicy-spec)
3. [Políticas de denegación predeterminada](#default-deny-policies)
4. [Orden y evaluación de políticas](#policy-order-and-evaluation)
5. [Extensiones de Cilium Network Policy](#cilium-network-policy-extensions)
6. [Extensiones de Calico Network Policy](#calico-network-policy-extensions)
7. [Patrones de diseño](#design-patterns)
8. [Pruebas de Network Policies](#testing-network-policies)
9. [Consideraciones de EKS](#eks-considerations)
10. [Herramientas de visualización](#visualization-tools)

---

## Descripción general de Network Policy

### ¿Qué es una Network Policy?

Las Network Policies actúan como firewalls a nivel de Pod en Kubernetes. De forma predeterminada, los Pods de Kubernetes pueden comunicarse libremente con todos los demás Pods, pero las Network Policies permiten restringir este tráfico.

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
| **Namespace Scoped** | NetworkPolicy se aplica a recursos dentro de un namespace |
| **Additive** | Cuando existen varias políticas, se aplica la unión de todas las políticas |
| **Selective Application** | Los Pods objetivo se especifican mediante podSelector |
| **Directional Control** | Control separado para Ingress (entrante) y Egress (saliente) |
| **CNI Dependent** | El plugin CNI debe admitir NetworkPolicy |

### Compatibilidad de CNI con NetworkPolicy

| CNI | NetworkPolicy básica | Extensiones | Política L7 |
|-----|---------------------|------------|-----------|
| **Cilium** | ✓ | CiliumNetworkPolicy, CiliumClusterwideNetworkPolicy | ✓ |
| **Calico** | ✓ | GlobalNetworkPolicy, NetworkSet | ✓ (Enterprise) |
| **Weave Net** | ✓ | Limitadas | ✗ |
| **Flannel** | ✗ | ✗ | ✗ |
| **Amazon VPC CNI** | ✗ (requiere instalación separada) | Security Groups for Pods | ✗ |

---

## Especificación NetworkPolicy de Kubernetes

### Estructura básica

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

Selecciona los Pods a los que se aplica la política.

```yaml
# Apply to Pods with specific labels
spec:
  podSelector:
    matchLabels:
      app: api
      version: v1

# Apply to all Pods (empty selector)
spec:
  podSelector: {}

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

Selecciona Pods de otros namespaces.

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
              name: monitoring
        # Allow specific Pods from production namespace
        - namespaceSelector:
            matchLabels:
              name: production
          podSelector:
            matchLabels:
              role: frontend
```

**Nota:** distinción entre AND y OR al usar `namespaceSelector` y `podSelector` juntos:

```yaml
# OR condition (two separate rules)
ingress:
  - from:
      - namespaceSelector:    # Rule 1
          matchLabels:
            name: team-a
      - podSelector:          # Rule 2
          matchLabels:
            role: frontend

# AND condition (single rule)
ingress:
  - from:
      - namespaceSelector:    # Both conditions must be met
          matchLabels:
            name: team-a
        podSelector:
          matchLabels:
            role: frontend
```

### ipBlock

Permite o bloquea rangos de IP específicos.

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
        # Allow external load balancer IP range
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

Especifica los puertos y protocolos permitidos.

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

## Políticas de denegación predeterminada

### Denegación predeterminada de Ingress

Política predeterminada que bloquea todo el tráfico entrante:

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

Política predeterminada que bloquea todo el tráfico saliente:

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

### Denegación completa (Ingress + Egress)

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

Patrón común para permitir consultas DNS cuando se bloquea Egress:

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
    # Allow kube-dns/CoreDNS access
    - to:
        - namespaceSelector: {}
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

```yaml
---
# 1. Default deny all traffic
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
---
# 2. Allow DNS only
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
      ports:
        - protocol: UDP
          port: 53
---
# 3. Explicitly allow only required communication
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
```

---

## Orden y evaluación de políticas

### Reglas de evaluación de políticas

NetworkPolicy se evalúa según las siguientes reglas:

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

Cuando varias NetworkPolicies se aplican al mismo Pod, todas las reglas de política se combinan (Union):

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
              name: monitoring
      ports:
        - protocol: TCP
          port: 8080
        - protocol: TCP
          port: 9090
```

**Resultado:** el Pod `app: api` permite tanto el acceso del Pod frontend en 8080 como el acceso del namespace monitoring en 8080 y 9090.

### Orden de evaluación de políticas

NetworkPolicy no tiene concepto de prioridad. Todas las políticas se tratan por igual:

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

## Extensiones de Cilium Network Policy

### CiliumNetworkPolicy

Cilium extiende NetworkPolicy básica con funcionalidades más potentes.

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
            - port: "8080"
              protocol: TCP
          rules:
            http:
              # Allow only GET requests
              - method: GET
                path: "/api/v1/products"

              # Allow specific path patterns
              - method: GET
                path: "/api/v1/products/[0-9]+"

              # POST only allowed with specific headers
              - method: POST
                path: "/api/v1/orders"
                headers:
                  - "X-API-Key: .*"
                  - "Content-Type: application/json"

              # PUT/DELETE only for admin
              - method: "PUT|DELETE"
                path: "/api/v1/.*"
                headers:
                  - "X-User-Role: admin"
```

### Política Kafka L7

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: kafka-policy
  namespace: data
spec:
  endpointSelector:
    matchLabels:
      app: kafka

  ingress:
    - fromEndpoints:
        - matchLabels:
            app: producer
      toPorts:
        - ports:
            - port: "9092"
              protocol: TCP
          rules:
            kafka:
              # Allow produce only to specific topics
              - role: produce
                topic: "orders"
              - role: produce
                topic: "events"

    - fromEndpoints:
        - matchLabels:
            app: consumer
      toPorts:
        - ports:
            - port: "9092"
              protocol: TCP
          rules:
            kafka:
              # Allow consume only from specific topics
              - role: consume
                topic: "orders"
                clientID: "order-processor-.*"
```

### Política DNS L7

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
    # Allow DNS lookups
    - toEndpoints:
        - matchLabels:
            k8s:io.kubernetes.pod.namespace: kube-system
            k8s-app: kube-dns
      toPorts:
        - ports:
            - port: "53"
              protocol: UDP
          rules:
            dns:
              # Allow only specific domain lookups
              - matchPattern: "*.amazonaws.com"
              - matchPattern: "api.example.com"
              - matchName: "database.production.svc.cluster.local"

    # Allow connections to looked up domains
    - toFQDNs:
        - matchPattern: "*.amazonaws.com"
        - matchName: "api.example.com"
      toPorts:
        - ports:
            - port: "443"
              protocol: TCP
```

### CiliumClusterwideNetworkPolicy

Política para todo el cluster:

```yaml
apiVersion: cilium.io/v2
kind: CiliumClusterwideNetworkPolicy
metadata:
  name: cluster-default-deny
spec:
  # Apply to all endpoints
  endpointSelector: {}

  ingress:
    - fromEntities:
        - cluster  # Allow only internal cluster traffic

  egress:
    - toEntities:
        - cluster
        - world  # Allow external traffic (if needed)
    - toEndpoints:
        - matchLabels:
            k8s:io.kubernetes.pod.namespace: kube-system
      toPorts:
        - ports:
            - port: "53"
              protocol: UDP
```

### Política de Cilium basada en entidades

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: entity-based-policy
  namespace: production
spec:
  endpointSelector:
    matchLabels:
      app: web

  ingress:
    - fromEntities:
        - world      # Outside cluster
        - cluster    # Inside cluster

  egress:
    - toEntities:
        - world      # Internet
      toPorts:
        - ports:
            - port: "443"
              protocol: TCP

    - toEntities:
        - host       # Node itself
      toPorts:
        - ports:
            - port: "10250"  # kubelet
              protocol: TCP

    - toEntities:
        - kube-apiserver  # API server
```

---

## Extensiones de Calico Network Policy

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

Política de Calico que se aplica a todo el cluster:

```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: default-deny-all
spec:
  # Full selector instead of namespace
  selector: all()

  order: 1000  # Low priority (other policies evaluated first)

  types:
    - Ingress
    - Egress

  # No rules = block all traffic

---
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: allow-dns
spec:
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

Define conjuntos de IP reutilizables:

```yaml
apiVersion: projectcalico.org/v3
kind: NetworkSet
metadata:
  name: external-apis
  namespace: production
spec:
  nets:
    - 203.0.113.0/24     # External API servers
    - 198.51.100.10/32   # Specific service

---
apiVersion: projectcalico.org/v3
kind: GlobalNetworkSet
metadata:
  name: blocked-ips
spec:
  nets:
    - 192.0.2.0/24       # IP range to block
    - 10.0.0.5/32        # Specific blocked IP
```

Uso de NetworkSet:

```yaml
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
      destination:
        selector: projectcalico.org/name == 'external-apis'
        namespaceSelector: projectcalico.org/name == 'production'
```

### Políticas basadas en Tier

Políticas jerárquicas compatibles con Calico Enterprise:

```yaml
apiVersion: projectcalico.org/v3
kind: Tier
metadata:
  name: security
spec:
  order: 100

---
apiVersion: projectcalico.org/v3
kind: Tier
metadata:
  name: platform
spec:
  order: 200

---
apiVersion: projectcalico.org/v3
kind: Tier
metadata:
  name: application
spec:
  order: 300

---
# Security Tier policy (evaluated first)
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: security.block-known-threats
spec:
  tier: security
  order: 100
  selector: all()
  types:
    - Ingress
  ingress:
    - action: Deny
      source:
        selector: global(name == 'blocked-ips')

---
# Platform Tier policy
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: platform.allow-dns
spec:
  tier: platform
  order: 100
  selector: all()
  types:
    - Egress
  egress:
    - action: Allow
      protocol: UDP
      destination:
        ports:
          - 53
```

---

## Patrones de diseño

### Microsegmentación

Aísla cada servicio individualmente:

```yaml
---
# 1. Namespace default deny
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
---
# 2. Allow DNS
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
      ports:
        - protocol: UDP
          port: 53
---
# 3. Frontend -> API
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
# 4. API -> Database
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
# 5. API external access (if needed)
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-external-access
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
    - Egress
  egress:
    - to:
        - ipBlock:
            cidr: 0.0.0.0/0
            except:
              - 10.0.0.0/8
              - 172.16.0.0/12
              - 192.168.0.0/16
      ports:
        - protocol: TCP
          port: 443
```

### Aislamiento de namespaces

```yaml
---
# 1. Set namespace labels
apiVersion: v1
kind: Namespace
metadata:
  name: team-a
  labels:
    team: team-a
    environment: production
---
# 2. Allow communication only within same team
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-same-team
  namespace: team-a
spec:
  podSelector: {}
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              team: team-a
---
# 3. Allow access to specific services from other teams
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
              shared-services: "true"
          podSelector:
            matchLabels:
              exposed: "true"
```

### Protección de bases de datos

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
    # Allow access only from application
    - from:
        - namespaceSelector:
            matchLabels:
              environment: production
          podSelector:
            matchLabels:
              database-access: "true"
      ports:
        - protocol: TCP
          port: 5432
    # Allow monitoring access
    - from:
        - namespaceSelector:
            matchLabels:
              name: monitoring
          podSelector:
            matchLabels:
              app: prometheus
      ports:
        - protocol: TCP
          port: 9187  # postgres_exporter
  egress:
    # Access other DB instances for replication
    - to:
        - podSelector:
            matchLabels:
              app: postgresql
      ports:
        - protocol: TCP
          port: 5432
    # DNS
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: kube-system
      ports:
        - protocol: UDP
          port: 53
```

### Política de arquitectura de 3 niveles

```yaml
---
# Web Tier
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
    # Allow access from external (Ingress Controller)
    - from:
        - namespaceSelector:
            matchLabels:
              name: ingress-nginx
      ports:
        - protocol: TCP
          port: 80
  egress:
    # Communicate only with App Tier
    - to:
        - podSelector:
            matchLabels:
              tier: app
      ports:
        - protocol: TCP
          port: 8080
    # DNS
    - to:
        - namespaceSelector: {}
          podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - protocol: UDP
          port: 53
---
# App Tier
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
    # Allow access only from Web Tier
    - from:
        - podSelector:
            matchLabels:
              tier: web
      ports:
        - protocol: TCP
          port: 8080
  egress:
    # Communicate only with Data Tier
    - to:
        - podSelector:
            matchLabels:
              tier: data
      ports:
        - protocol: TCP
          port: 5432
        - protocol: TCP
          port: 6379
    # DNS
    - to:
        - namespaceSelector: {}
          podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - protocol: UDP
          port: 53
---
# Data Tier
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
    # Allow access only from App Tier
    - from:
        - podSelector:
            matchLabels:
              tier: app
      ports:
        - protocol: TCP
          port: 5432
        - protocol: TCP
          port: 6379
  egress:
    # Replication communication within same tier
    - to:
        - podSelector:
            matchLabels:
              tier: data
```

---

## Pruebas de Network Policies

### Pruebas con netshoot

```bash
# Deploy netshoot Pod
kubectl run netshoot --image=nicolaka/netshoot -it --rm -- /bin/bash

# Connection tests
curl -v http://api-service:8080/health
nc -zv database-service 5432
nslookup api-service.production.svc.cluster.local

# TCP connection test
curl --connect-timeout 5 http://target-service:8080
```

### Pruebas con kubectl exec

```bash
# Test connection from Pod to another service
kubectl exec -it frontend-pod -- curl -v http://api-service:8080

# DNS verification
kubectl exec -it frontend-pod -- nslookup api-service

# Port scan
kubectl exec -it frontend-pod -- nc -zv api-service 8080
```

### Prueba de conectividad de Cilium

```bash
# Run Cilium connectivity test
cilium connectivity test

# Run specific tests only
cilium connectivity test --test pod-to-pod
cilium connectivity test --test pod-to-service

# Policy tests
cilium connectivity test --test to-entities-world
cilium connectivity test --test to-cidr-external
```

### Script de prueba automatizado

```bash
#!/bin/bash
# network-policy-test.sh

echo "=== Network Policy Test Suite ==="

# Create test Pod
kubectl run test-pod --image=nicolaka/netshoot --restart=Never --labels="app=test" -- sleep 3600

# Wait for Pod to be ready
kubectl wait --for=condition=Ready pod/test-pod --timeout=60s

# Run test cases
run_test() {
    local name=$1
    local command=$2
    local expected=$3

    echo -n "Testing: $name... "
    result=$(kubectl exec test-pod -- timeout 5 sh -c "$command" 2>&1)

    if [[ "$expected" == "success" && $? -eq 0 ]]; then
        echo "PASS"
    elif [[ "$expected" == "fail" && $? -ne 0 ]]; then
        echo "PASS (correctly blocked)"
    else
        echo "FAIL"
        echo "  Result: $result"
    fi
}

# Test cases
run_test "DNS resolution" "nslookup kubernetes.default" "success"
run_test "API server access" "curl -k https://kubernetes.default/healthz" "success"
run_test "External access blocked" "curl -s --connect-timeout 3 http://example.com" "fail"
run_test "Database access" "nc -zv database-service 5432" "success"

# Cleanup
kubectl delete pod test-pod --force --grace-period=0
```

---

## Consideraciones de EKS

### Amazon VPC CNI y NetworkPolicy

Amazon VPC CNI no admite NetworkPolicy de forma predeterminada. Se requiere configuración adicional para usar NetworkPolicy:

```bash
# Option 1: Enable VPC CNI NetworkPolicy support (v1.14.0+)
kubectl set env daemonset aws-node -n kube-system ENABLE_NETWORK_POLICY=true

# Check VPC CNI version
kubectl describe daemonset aws-node -n kube-system | grep Image

# Option 2: Install Calico policy engine separately
kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/calico-operator.yaml
kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/calico-crs.yaml
```

### EKS Enhanced Network Security Policies (diciembre de 2025)

> **Anunciado**: December 15, 2025 · [Fuente](https://aws.amazon.com/about-aws/whats-new/2025/12/amazon-eks-enhanced-network-security-policies/)

EKS agregó dos capacidades sobre `NetworkPolicy` con ámbito de namespace:

- **ClusterNetworkPolicy**: un nuevo recurso que permite aplicar una política de red consistente en todo el cluster desde un lugar central, en lugar de administrar políticas namespace por namespace.
- **Control de Egress basado en DNS (FQDN)**: permite o bloquea el tráfico de Egress según el nombre de dominio en lugar de la IP de destino. Esto es más confiable que las reglas `ipBlock` basadas en IP para destinos cuyas IP cambian con frecuencia, como APIs SaaS o endpoints externos.

**Requisitos**:
- Disponible en clusters nuevos de Kubernetes 1.29+
- `ClusterNetworkPolicy` admite todos los modos de lanzamiento en VPC CNI v1.21.0+
- Las políticas basadas en DNS solo son compatibles con **nodos EC2 creados por EKS Auto Mode**
- Sin costo adicional

```yaml
# ClusterNetworkPolicy example: cluster-wide default deny + allow DNS
apiVersion: policy.networking.k8s.io/v1alpha1
kind: ClusterNetworkPolicy
metadata:
  name: cluster-default-deny
spec:
  priority: 100
  subject:
    namespaces: {}
  egress:
    - name: allow-dns
      action: Allow
      to:
        - namespaces:
            matchLabels:
              kubernetes.io/metadata.name: kube-system
      ports:
        - protocol: UDP
          port: 53
```

```yaml
# DNS (FQDN)-based egress policy example: allow only specific SaaS domains
apiVersion: policy.networking.k8s.io/v1alpha1
kind: ClusterNetworkPolicy
metadata:
  name: allow-saas-fqdn-egress
spec:
  priority: 200
  subject:
    namespaces:
      matchLabels:
        team: payments
  egress:
    - name: allow-external-api
      action: Allow
      to:
        - fqdns:
            - "api.stripe.com"
            - "*.datadoghq.com"
      ports:
        - protocol: TCP
          port: 443
```

### Security Groups for Pods

En EKS, puedes aplicar Security Groups directamente a Pods:

```yaml
# SecurityGroupPolicy definition
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
      - sg-0123456789abcdef0  # Database Security Group
---
# Pod automatically gets Security Group applied
apiVersion: v1
kind: Pod
metadata:
  name: database-pod
  namespace: production
  labels:
    app: database
spec:
  containers:
    - name: postgres
      image: postgres:15
```

Ejemplo de configuración de Security Group:

```hcl
# Define Security Group with Terraform
resource "aws_security_group" "database_pods" {
  name_prefix = "database-pods-"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.app_pods.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
```

### Combinación de controles a nivel de VPC con NetworkPolicy

```yaml
# NetworkPolicy (Pod level)
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: database-policy
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
              database-access: "true"
      ports:
        - protocol: TCP
          port: 5432
```

```hcl
# Security Group (VPC level)
# Provides additional network isolation
resource "aws_security_group" "database_pods" {
  # ... (see example above)
}

# NACL (Subnet level)
# Controls traffic between subnets
resource "aws_network_acl_rule" "database_subnet" {
  network_acl_id = aws_network_acl.database.id
  rule_number    = 100
  egress         = false
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = "10.0.0.0/16"
  from_port      = 5432
  to_port        = 5432
}
```

### Uso de Cilium en EKS

```bash
# Remove VPC CNI (optional)
kubectl delete daemonset aws-node -n kube-system

# Install Cilium
helm repo add cilium https://helm.cilium.io/
helm install cilium cilium/cilium --version 1.15.0 \
    --namespace kube-system \
    --set eni.enabled=true \
    --set ipam.mode=eni \
    --set egressMasqueradeInterfaces=eth0 \
    --set routingMode=native
```

---

## Herramientas de visualización

### Editor de Cilium Network Policy

Cilium proporciona un editor de políticas basado en web:

```bash
# Enable Cilium Hubble UI
cilium hubble enable --ui

# Access Hubble UI
cilium hubble ui

# Or port forward
kubectl port-forward -n kube-system svc/hubble-ui 12000:80
```

### Comprobación de veredictos de políticas de Cilium

```bash
# Check real-time policy decisions
hubble observe --verdict DROPPED
hubble observe --verdict FORWARDED

# Check traffic for specific Pod
hubble observe --pod production/api-server

# Output in JSON format
hubble observe --output json | jq '.flow.verdict'
```

### UI de Calico Enterprise

Calico Enterprise proporciona una UI de visualización de políticas:

```bash
# Access Calico Enterprise dashboard
kubectl port-forward -n calico-system svc/cnx-manager 9443:443
```

### Herramientas de visualización de Network Policy

```bash
# Install kubectl-np-viewer
kubectl krew install np-viewer

# Visualize policies
kubectl np-viewer -n production

# Check policies for specific Pod
kubectl np-viewer -n production --pod api-server
```

### Pruebas de seguridad con Kube-hunter

```bash
# Cluster security scan
kubectl run kube-hunter --image=aquasec/kube-hunter --restart=Never -- --pod

# Check results
kubectl logs kube-hunter
```

---

## Mejores prácticas

### 1. Aplicar una política de denegación predeterminada

```yaml
# Apply to all production namespaces
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

Permite explícitamente solo el tráfico requerido:

```yaml
# Explicit and specific rules
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-minimal-access
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
    last-reviewed: "2026-02-21"
spec:
  # ...
```

### 4. Auditorías periódicas de políticas

```bash
#!/bin/bash
# audit-network-policies.sh

echo "=== Network Policy Audit ==="

# Find namespaces without policies
for ns in $(kubectl get namespaces -o jsonpath='{.items[*].metadata.name}'); do
    policies=$(kubectl get networkpolicies -n "$ns" --no-headers 2>/dev/null | wc -l)
    if [[ $policies -eq 0 ]]; then
        echo "WARNING: No NetworkPolicy in namespace: $ns"
    fi
done

# Check for default deny policies
for ns in $(kubectl get namespaces -o jsonpath='{.items[*].metadata.name}'); do
    deny_policy=$(kubectl get networkpolicies -n "$ns" -o json | jq -r '.items[] | select(.spec.podSelector == {} and .spec.ingress == null) | .metadata.name')
    if [[ -z "$deny_policy" ]]; then
        echo "INFO: No default-deny policy in namespace: $ns"
    fi
done
```

---

## Resumen

Las Network Policies de Kubernetes son un mecanismo de seguridad central para controlar la comunicación de Pods dentro de clusters:

1. **NetworkPolicy básica**: con ámbito de namespace, admite podSelector/namespaceSelector/ipBlock
2. **Extensiones de Cilium**: políticas L7, políticas basadas en DNS FQDN, políticas para todo el cluster
3. **Extensiones de Calico**: GlobalNetworkPolicy, NetworkSet, políticas basadas en Tier
4. **Consideraciones de EKS**: activación de NetworkPolicy en VPC CNI, Security Groups for Pods, ClusterNetworkPolicy y control de Egress basado en DNS (FQDN)

### Recomendaciones

- Aplica una política de denegación predeterminada a todos los namespaces de producción
- Permite solo el tráfico requerido siguiendo el principio de privilegio mínimo
- Realiza auditorías y pruebas periódicas de políticas
- Considera Cilium cuando se necesiten políticas L7

---

## Referencias

- [Documentación oficial de Kubernetes Network Policies](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Documentación de Cilium Network Policy](https://docs.cilium.io/en/stable/security/policy/)
- [Documentación de Calico Network Policy](https://docs.tigera.io/calico/latest/network-policy/)
- [Mejores prácticas de seguridad de EKS - Seguridad de red](https://aws.github.io/aws-eks-best-practices/security/docs/network/)
- [Amazon EKS Enhanced Network Security Policies (2025-12-15)](https://aws.amazon.com/about-aws/whats-new/2025/12/amazon-eks-enhanced-network-security-policies/)
