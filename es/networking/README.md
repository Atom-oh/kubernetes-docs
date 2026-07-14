# Redes de Kubernetes

> **Última actualización**: February 22, 2026

## Descripción general

Las redes de Kubernetes constituyen la capa central de infraestructura que permite la comunicación entre aplicaciones en contenedores. Esta sección abarca desde los conceptos básicos de redes de Kubernetes hasta soluciones avanzadas de CNI (Container Network Interface) y patrones de red en entornos de AWS EKS.

## Modelo de red de Kubernetes

Kubernetes está diseñado con base en los siguientes requisitos de red:

1. **Cada Pod puede comunicarse con cualquier otro Pod sin NAT**
2. **Cada Node puede comunicarse con cada Pod sin NAT**
3. **La IP con la que un Pod se identifica es la misma IP con la que los demás lo identifican**

```mermaid
graph TB
    subgraph "Kubernetes Networking Layers"
        L1[Pod Networking<br/>Pod-to-Pod Communication]
        L2[Service Networking<br/>Service Discovery & Load Balancing]
        L3[Ingress Networking<br/>External Traffic Routing]
        L4[Network Policy<br/>Network Security]
    end

    L1 --> L2
    L2 --> L3
    L3 --> L4

    style L1 fill:#e1f5fe
    style L2 fill:#b3e5fc
    style L3 fill:#81d4fa
    style L4 fill:#4fc3f7
```

### Redes de Pods

Las redes de Pods son la capa más fundamental de las redes de Kubernetes. Cada Pod tiene una dirección IP única y puede comunicarse directamente con todos los demás Pods del clúster.

```mermaid
graph LR
    subgraph "Node 1"
        P1[Pod A<br/>10.244.1.10]
        P2[Pod B<br/>10.244.1.11]
    end

    subgraph "Node 2"
        P3[Pod C<br/>10.244.2.10]
        P4[Pod D<br/>10.244.2.11]
    end

    P1 <--> P3
    P2 <--> P4
    P1 <--> P2
    P3 <--> P4

    style P1 fill:#c8e6c9
    style P2 fill:#c8e6c9
    style P3 fill:#fff9c4
    style P4 fill:#fff9c4
```

#### Métodos de implementación de redes de Pods

| Método | Descripción | CNI de ejemplo |
|--------|-------------|-------------|
| **Overlay Network** | Red virtual construida sobre la red existente | Flannel (VXLAN), Calico (IPIP), Weave Net |
| **Underlay Network** | Enrutamiento directo en la red física | AWS VPC CNI, Calico (BGP), Cilium (Native Routing) |
| **Hybrid** | Elegir overlay/underlay según el entorno | Cilium, Calico |

### Redes de Services

Los Services proporcionan endpoints de red estables para un conjunto de Pods.

```mermaid
graph TB
    subgraph "Service Types"
        CT[ClusterIP<br/>Internal Cluster Only]
        NP[NodePort<br/>External via Node Port]
        LB[LoadBalancer<br/>External Load Balancer Integration]
        EI[ExternalName<br/>External DNS Mapping]
    end

    Client[Client] --> CT
    External[External Traffic] --> NP
    External --> LB
    App[Application] --> EI

    style CT fill:#e8eaf6
    style NP fill:#c5cae9
    style LB fill:#9fa8da
    style EI fill:#7986cb
```

#### Características de los tipos de Service

```yaml
# ClusterIP Service Example
apiVersion: v1
kind: Service
metadata:
  name: my-service
  namespace: default
spec:
  type: ClusterIP
  selector:
    app: my-app
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8080
---
# NodePort Service Example
apiVersion: v1
kind: Service
metadata:
  name: my-nodeport-service
spec:
  type: NodePort
  selector:
    app: my-app
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8080
      nodePort: 30080  # Range: 30000-32767
---
# LoadBalancer Service Example
apiVersion: v1
kind: Service
metadata:
  name: my-loadbalancer-service
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: "nlb"
spec:
  type: LoadBalancer
  selector:
    app: my-app
  ports:
    - protocol: TCP
      port: 443
      targetPort: 8443
```

### Redes de Ingress

Ingress define reglas para enrutar el tráfico HTTP/HTTPS a Services internos del clúster.

```mermaid
graph LR
    Internet[Internet] --> IC[Ingress Controller]

    subgraph "Cluster"
        IC --> S1[Service A]
        IC --> S2[Service B]
        IC --> S3[Service C]

        S1 --> P1[Pod A1]
        S1 --> P2[Pod A2]
        S2 --> P3[Pod B1]
        S3 --> P4[Pod C1]
    end

    style IC fill:#ffcc80
    style S1 fill:#a5d6a7
    style S2 fill:#a5d6a7
    style S3 fill:#a5d6a7
```

```yaml
# Ingress Example
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: my-ingress
  annotations:
    kubernetes.io/ingress.class: "alb"
    alb.ingress.kubernetes.io/scheme: "internet-facing"
spec:
  rules:
    - host: api.example.com
      http:
        paths:
          - path: /v1
            pathType: Prefix
            backend:
              service:
                name: api-v1
                port:
                  number: 80
          - path: /v2
            pathType: Prefix
            backend:
              service:
                name: api-v2
                port:
                  number: 80
    - host: web.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: web-frontend
                port:
                  number: 80
```

## CNI (Container Network Interface)

CNI es una interfaz estándar para la conectividad de red de contenedores. Kubernetes implementa las redes de Pods mediante plugins de CNI.

### Cómo funciona CNI

```mermaid
sequenceDiagram
    participant Kubelet
    participant CNI Plugin
    participant Network

    Kubelet->>CNI Plugin: ADD call (on container creation)
    CNI Plugin->>Network: Create network interface
    CNI Plugin->>Network: Assign IP address
    CNI Plugin->>Network: Configure routing rules
    CNI Plugin-->>Kubelet: Return IP address

    Note over Kubelet,Network: Pod running...

    Kubelet->>CNI Plugin: DEL call (on container deletion)
    CNI Plugin->>Network: Clean up network resources
    CNI Plugin-->>Kubelet: Complete
```

### Componentes del plugin de CNI

```mermaid
graph TB
    subgraph "CNI Plugin Architecture"
        Agent[CNI Agent/Daemon<br/>Runs on each node]
        Binary[CNI Binary<br/>/opt/cni/bin/]
        Config[CNI Config<br/>/etc/cni/net.d/]
        IPAM[IPAM Plugin<br/>IP Address Management]
    end

    Kubelet[Kubelet] --> Binary
    Binary --> Config
    Binary --> IPAM
    Agent --> Binary

    style Agent fill:#bbdefb
    style Binary fill:#90caf9
    style Config fill:#64b5f6
    style IPAM fill:#42a5f5
```

## Matriz de comparación de CNI

### Comparación de las principales soluciones de CNI

| Característica | Cilium | Calico | Flannel | AWS VPC CNI | Weave Net |
|---------|--------|--------|---------|-------------|-----------|
| **Tecnología principal** | eBPF | iptables/eBPF | VXLAN/host-gw | AWS ENI | VXLAN |
| **Network Policy** | Avanzada (L3-L7) | Avanzada (L3-L4) | Ninguna | Básica (L3-L4) | Básica |
| **Cifrado** | WireGuard/IPsec | WireGuard/IPsec | Ninguno | Ninguno | Integrado |
| **Service Mesh** | Integrado | Ninguno | Ninguno | Ninguno | Ninguno |
| **Observabilidad** | Hubble | Limitada | Ninguna | Ninguna | Ninguna |
| **Compatibilidad con BGP** | Sí | Sí | No | No | No |
| **Multiclúster** | ClusterMesh | Federation | No | No | Sí |
| **Compatibilidad con Windows** | Beta | Sí | Sí | Sí | Sí |
| **Rendimiento** | Excelente | Muy bueno | Bueno | Excelente | Bueno |
| **Complejidad** | Media-alta | Media | Baja | Baja | Baja |
| **Comunidad** | Activa | Muy activa | Activa | Compatible con AWS | Moderada |

### Comparación detallada de características

#### Modos de red

| CNI | Overlay | Native Routing | BGP | Direct Routing |
|-----|---------|----------------|-----|----------------|
| **Cilium** | VXLAN, Geneve | Sí | Sí | Sí |
| **Calico** | VXLAN, IPIP | Sí | Sí | Sí |
| **Flannel** | VXLAN | host-gw | No | No |
| **AWS VPC CNI** | No | VPC Native | No | Sí |
| **Weave Net** | VXLAN | No | No | No |

#### Características de Network Policy

| Característica | Cilium | Calico | AWS VPC CNI |
|---------|--------|--------|-------------|
| **Ingress Policy** | Sí | Sí | Sí |
| **Egress Policy** | Sí | Sí | Sí |
| **L7 Policy (HTTP)** | Sí | No | No |
| **DNS-based Policy** | Sí | Sí | No |
| **FQDN Policy** | Sí | Sí | No |
| **Host Policy** | Sí | Sí | No |
| **Global Policy** | Sí | Sí | No |
| **Policy Tiers** | Sí | Sí | No |

#### Benchmark de rendimiento (comparación relativa)

```mermaid
graph LR
    subgraph "Throughput"
        C1[Cilium eBPF: 100%]
        C2[AWS VPC CNI: 98%]
        C3[Calico eBPF: 95%]
        C4[Calico iptables: 85%]
        C5[Flannel: 80%]
        C6[Weave: 75%]
    end

    style C1 fill:#4caf50
    style C2 fill:#66bb6a
    style C3 fill:#81c784
    style C4 fill:#a5d6a7
    style C5 fill:#c8e6c9
    style C6 fill:#e8f5e9
```

## Guía de selección de CNI

### Diagrama de flujo de decisión

```mermaid
graph TD
    Start[Start CNI Selection] --> Q1{Using<br/>AWS EKS?}

    Q1 -->|Yes| Q2{Need Advanced<br/>Network Policy?}
    Q1 -->|No| Q3{Environment<br/>Complexity?}

    Q2 -->|Yes| Q4{Need L7<br/>Policy?}
    Q2 -->|No| VPCCNI[AWS VPC CNI<br/>Recommended]

    Q4 -->|Yes| CILIUM[Cilium + VPC CNI<br/>Recommended]
    Q4 -->|No| CALICO_EKS[Calico + VPC CNI<br/>Recommended]

    Q3 -->|Simple| Q5{Multi-cloud?}
    Q3 -->|Complex| Q6{Need BGP?}

    Q5 -->|Yes| CALICO[Calico Recommended]
    Q5 -->|No| FLANNEL[Flannel Recommended]

    Q6 -->|Yes| Q7{Need Built-in<br/>Service Mesh?}
    Q6 -->|No| CALICO

    Q7 -->|Yes| CILIUM2[Cilium Recommended]
    Q7 -->|No| CALICO2[Calico Recommended]

    style CILIUM fill:#4fc3f7
    style CILIUM2 fill:#4fc3f7
    style CALICO fill:#81c784
    style CALICO_EKS fill:#81c784
    style CALICO2 fill:#81c784
    style VPCCNI fill:#ffb74d
    style FLANNEL fill:#ce93d8
```

### CNI recomendado según el caso de uso

#### 1. Entorno de producción de AWS EKS

**Recomendado: AWS VPC CNI + Calico (Network Policy)**

```yaml
# eksctl cluster configuration example
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: production-cluster
  region: ap-northeast-2
vpc:
  cidr: "10.0.0.0/16"
addons:
  - name: vpc-cni
    version: latest
    configurationValues: |
      enableNetworkPolicy: "true"
  - name: coredns
  - name: kube-proxy
```

#### 2. Requisitos de seguridad avanzados

**Recomendado: Cilium**

- Compatibilidad con L7 Network Policy
- Política basada en DNS
- Políticas de seguridad a nivel de proceso/archivo
- Comunicación cifrada (WireGuard)

#### 3. Entorno on-premises/bare-metal

**Recomendado: Calico (modo BGP)**

- Integración con la infraestructura de red existente
- Emparejamiento BGP con switches ToR
- Alto rendimiento (sin overlay)

#### 4. Entorno de desarrollo/pruebas

**Recomendado: Flannel**

- Instalación y configuración sencillas
- Bajo uso de recursos
- Características básicas suficientes

#### 5. Entorno de integración de Service Mesh

**Recomendado: Cilium (Service Mesh sin Sidecar)**

- Puede sustituir a Istio/Envoy
- mTLS, gestión de tráfico
- Baja sobrecarga

## Fundamentos de redes de EKS

### Arquitectura de red predeterminada de EKS

```mermaid
graph TB
    subgraph "AWS Cloud"
        subgraph "VPC"
            subgraph "Availability Zone A"
                PubA[Public Subnet]
                PrivA[Private Subnet]
            end
            subgraph "Availability Zone B"
                PubB[Public Subnet]
                PrivB[Private Subnet]
            end

            IGW[Internet Gateway]
            NAT[NAT Gateway]

            subgraph "EKS Cluster"
                CP[Control Plane<br/>AWS Managed]

                subgraph "Node Group"
                    N1[Worker Node 1]
                    N2[Worker Node 2]
                end
            end
        end

        ALB[Application<br/>Load Balancer]
        NLB[Network<br/>Load Balancer]
    end

    Internet[Internet] --> IGW
    IGW --> ALB
    ALB --> N1
    ALB --> N2
    Internet --> NLB
    NLB --> N1

    style CP fill:#ff9800
    style N1 fill:#4caf50
    style N2 fill:#4caf50
    style ALB fill:#2196f3
    style NLB fill:#9c27b0
```

### Cómo funciona VPC CNI

AWS VPC CNI asigna direcciones IP reales de VPC a cada Pod.

```mermaid
graph TB
    subgraph "EC2 Instance (Worker Node)"
        ENI1[Primary ENI<br/>eth0]
        ENI2[Secondary ENI<br/>eth1]
        ENI3[Secondary ENI<br/>eth2]

        subgraph "Pods"
            P1[Pod 1<br/>Secondary IP]
            P2[Pod 2<br/>Secondary IP]
            P3[Pod 3<br/>Secondary IP]
            P4[Pod 4<br/>Secondary IP]
        end
    end

    ENI1 --> P1
    ENI1 --> P2
    ENI2 --> P3
    ENI2 --> P4

    style ENI1 fill:#bbdefb
    style ENI2 fill:#bbdefb
    style ENI3 fill:#bbdefb
```

#### Límites de ENI e IP

| Tipo de instancia | ENI máximos | IPv4 por ENI | Pods máximos (recomendado) |
|---------------|----------|--------------|------------------------|
| t3.medium | 3 | 6 | 17 |
| t3.large | 3 | 12 | 35 |
| m5.large | 3 | 10 | 29 |
| m5.xlarge | 4 | 15 | 58 |
| m5.2xlarge | 4 | 15 | 58 |
| c5.4xlarge | 8 | 30 | 234 |

### Consideraciones de red de EKS

#### Gestión de direcciones IP

```yaml
# VPC CNI Configuration - IP Prefix Delegation
apiVersion: v1
kind: ConfigMap
metadata:
  name: amazon-vpc-cni
  namespace: kube-system
data:
  enable-prefix-delegation: "true"
  warm-prefix-target: "1"
  minimum-ip-target: "5"
  warm-ip-target: "2"
```

#### Redes personalizadas

```yaml
# ENIConfig for Custom Subnets
apiVersion: crd.k8s.amazonaws.com/v1alpha1
kind: ENIConfig
metadata:
  name: us-east-1a
spec:
  securityGroups:
    - sg-0123456789abcdef0
  subnet: subnet-0123456789abcdef0
---
apiVersion: crd.k8s.amazonaws.com/v1alpha1
kind: ENIConfig
metadata:
  name: us-east-1b
spec:
  securityGroups:
    - sg-0123456789abcdef0
  subnet: subnet-fedcba9876543210f
```

## Subpáginas de redes

Esta sección cubre los siguientes temas en detalle:

### [VPC CNI](01-vpc-cni.md)
CNI predeterminado de EKS. Asigna IP de VPC a cada Pod para redes nativas de VPC.

### [Análisis detallado de Cilium](cilium/README.md)
Solución de CNI de alto rendimiento basada en eBPF. Proporciona características avanzadas como L7 Network Policy, Service Mesh y observabilidad (Hubble).

### [Análisis detallado de Calico](calico/README.md)
Uno de los CNI más utilizados. Network Policy potente, compatibilidad con BGP y características empresariales. Abarca introducción, arquitectura, modos de red, análisis detallado de BGP, Network Policy, eBPF, temas avanzados, integración de EKS y guía de operaciones.

### [VPC Lattice](02-vpc-lattice.md)
Servicio de red de aplicaciones administrado por AWS. Comunicación de Service a Service entre VPC y entre cuentas.

### [AWS Load Balancer Controller](03-aws-lb-controller.md)
Integra Services e Ingress de Kubernetes con AWS ELB (ALB/NLB).

### [Gateway API](04-gateway-api.md)
API de Ingress de Kubernetes de próxima generación. Modelo de recursos estandarizado y configuración basada en roles.

## Solución de problemas de red

### Problemas comunes y soluciones

#### Error de comunicación de Pod a Pod

```bash
# 1. Check Pod IPs
kubectl get pods -o wide

# 2. Test network connectivity
kubectl exec -it <pod-name> -- ping <target-pod-ip>

# 3. Test DNS resolution
kubectl exec -it <pod-name> -- nslookup <service-name>

# 4. Check CNI logs
kubectl logs -n kube-system -l k8s-app=aws-node
kubectl logs -n kube-system -l k8s-app=cilium
```

#### Service inaccesible

```bash
# 1. Check Service status
kubectl get svc <service-name> -o yaml

# 2. Check Endpoints
kubectl get endpoints <service-name>

# 3. Check kube-proxy logs
kubectl logs -n kube-system -l k8s-app=kube-proxy
```

#### Depuración de Network Policy

```bash
# For Cilium
kubectl exec -n kube-system -it <cilium-pod> -- cilium policy get
kubectl exec -n kube-system -it <cilium-pod> -- cilium endpoint list

# For Calico
kubectl get networkpolicy -A
kubectl get globalnetworkpolicy
calicoctl get policy -o yaml
```

### Pruebas de rendimiento de red

```yaml
# Network performance test using iperf3
apiVersion: v1
kind: Pod
metadata:
  name: iperf-server
  labels:
    app: iperf-server
spec:
  containers:
  - name: iperf
    image: networkstatic/iperf3
    command: ["iperf3", "-s"]
    ports:
    - containerPort: 5201
---
apiVersion: v1
kind: Pod
metadata:
  name: iperf-client
spec:
  containers:
  - name: iperf
    image: networkstatic/iperf3
    command: ["sleep", "infinity"]
```

```bash
# Run the test
kubectl exec -it iperf-client -- iperf3 -c <iperf-server-ip> -t 30
```

## Prácticas recomendadas

### 1. Planificación de direcciones IP

- Diseñar bloques CIDR lo suficientemente grandes
- Separar la red de Pods de la red de Services
- Diseñar subnets teniendo en cuenta la expansión futura

### 2. Aplicar Network Policies

- Aplicar políticas predeterminadas de denegación (Zero Trust)
- Permitir explícitamente solo el tráfico necesario
- Aislar namespaces

```yaml
# Default deny policy example
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

### 3. Optimización del rendimiento

- Elegir el CNI adecuado (según la carga de trabajo)
- Optimización de MTU
- Ajuste de parámetros del kernel

### 4. Fortalecimiento de la seguridad

- Comunicación cifrada (WireGuard, IPsec)
- Aplicar mTLS
- Auditorías de seguridad periódicas

### 5. Garantizar la observabilidad

- Recopilar métricas de red
- Habilitar logs de flujo
- Implementar trazado distribuido

## Próximos pasos

1. [VPC CNI](01-vpc-cni.md) - CNI predeterminado de EKS
2. [Análisis detallado de Cilium](cilium/README.md) - Redes basadas en eBPF
3. [Análisis detallado de Calico](calico/README.md) - CNI empresarial
4. [VPC Lattice](02-vpc-lattice.md) - Redes administradas por AWS
5. [AWS Load Balancer Controller](03-aws-lb-controller.md) - Integración con ELB
6. [Gateway API](04-gateway-api.md) - Ingress de próxima generación

---

## Referencias

- [Modelo de red de Kubernetes](https://kubernetes.io/docs/concepts/cluster-administration/networking/)
- [Especificación de CNI](https://github.com/containernetworking/cni/blob/master/SPEC.md)
- [Documentación de AWS VPC CNI](https://docs.aws.amazon.com/eks/latest/userguide/pod-networking.html)
- [Guía de Network Policy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
