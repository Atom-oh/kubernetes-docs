# Parte 2: Arquitectura

> **Versiones compatibles**: Calico v3.29+ / Kubernetes 1.28+ **Última actualización**: February 23, 2026

## Descripción general

Esta sección ofrece una exploración detallada de la arquitectura de Calico. Comprender cómo funciona e interactúa cada componente es esencial para implementar, solucionar problemas y optimizar Calico eficazmente en entornos de producción.

## Diagrama completo de la arquitectura

![Plano de control de Kubernetes, plano de control de Calico (servidor API, kube-controllers, Typha) y un nodo worker donde Felix programa el plano de datos local y confd/BIRD distribuyen rutas a través de la malla BGP de nodos.](../../.gitbook/assets/en-networking-calico-02-architecture-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-02-architecture-0.html)

## Felix: el agente de Calico

Felix es el agente principal de Calico que se ejecuta en cada nodo del clúster. Es responsable de programar rutas y ACL (listas de control de acceso) en el host para proporcionar la conectividad deseada y la aplicación de políticas de red.

### Responsabilidades de Felix

![Diagrama que muestra el Datastore Watcher de Felix distribuyendo actualizaciones a sus administradores de rutas, ACL, interfaces e IPAM, que a su vez programan la tabla de enrutamiento del nodo, las reglas de iptables, los conjuntos de IP y las interfaces de red.](../../../assets/diagrams/rendered/en-networking-calico-02-architecture-1.svg)

### Funciones principales

1. **Programación de rutas**: Administra las rutas para bloques CIDR de Pod
2. **Aplicación de ACL**: Programa reglas de iptables/nftables/eBPF para políticas de red
3. **Administración de interfaces**: Configura las interfaces de endpoint de carga de trabajo
4. **Informes de estado**: Informa el estado de nodos y endpoints al datastore
5. **Coordinación de IPAM**: Administra la asignación de direcciones IP para las cargas de trabajo locales

### Opciones de plano de datos de Felix

Felix admite múltiples backends de plano de datos:

| Plano de datos   | Descripción                | Ideal para                                  |
| ------------ | -------------------------- | ------------------------------------------- |
| **iptables** | Firewall tradicional de Linux | Compatibilidad, implementaciones maduras           |
| **nftables** | Firewall moderno de Linux      | Kernels más recientes, mejor rendimiento           |
| **eBPF**     | Programable dentro del kernel     | Máximo rendimiento, reemplazo de kube-proxy |

### Recurso FelixConfiguration

```yaml
apiVersion: projectcalico.org/v3
kind: FelixConfiguration
metadata:
  name: default
spec:
  # Logging configuration
  logSeverityScreen: Info
  logSeverityFile: Warning
  logFilePath: /var/log/calico/felix.log

  # Data plane selection
  bpfEnabled: false                    # Set true for eBPF data plane
  bpfDataIfacePattern: ^((en|wl|eth).*|bond[0-9]+)$
  bpfConnectTimeLoadBalancingEnabled: true
  bpfExternalServiceMode: Tunnel

  # iptables configuration
  iptablesBackend: Auto               # Auto, Legacy, NFT
  iptablesRefreshInterval: 90s
  iptablesPostWriteCheckIntervalSecs: 1
  iptablesLockFilePath: /run/xtables.lock
  iptablesLockTimeoutSecs: 0
  iptablesLockProbeIntervalMillis: 50

  # Performance tuning
  ipipMTU: 1440
  vxlanMTU: 1410
  wireguardMTU: 1420

  # Health and metrics
  healthEnabled: true
  healthPort: 9099
  prometheusMetricsEnabled: true
  prometheusMetricsPort: 9091
  prometheusGoMetricsEnabled: true
  prometheusProcessMetricsEnabled: true

  # Policy configuration
  defaultEndpointToHostAction: Drop
  failsafeInboundHostPorts:
    - protocol: TCP
      port: 22
    - protocol: UDP
      port: 68
  failsafeOutboundHostPorts:
    - protocol: UDP
      port: 53
    - protocol: UDP
      port: 67

  # Interface configuration
  interfacePrefix: cali
  chainInsertMode: Insert

  # Reporting
  reportingIntervalSecs: 30
  reportingTTLSecs: 90
```

### Estructura de reglas de iptables de Felix

Felix organiza las reglas de iptables en cadenas para un procesamiento eficiente:

```
                         ┌─────────────────────────────────────────┐
                         │              FORWARD Chain              │
                         └─────────────────┬───────────────────────┘
                                           │
                         ┌─────────────────▼───────────────────────┐
                         │          cali-FORWARD (Calico)          │
                         └─────────────────┬───────────────────────┘
                                           │
              ┌────────────────────────────┼────────────────────────────┐
              │                            │                            │
┌─────────────▼─────────────┐ ┌────────────▼────────────┐ ┌─────────────▼─────────────┐
│   cali-from-wl-dispatch   │ │   cali-to-wl-dispatch   │ │    cali-from-host-ep     │
│  (from workload traffic)  │ │  (to workload traffic)  │ │   (from host endpoints)   │
└─────────────┬─────────────┘ └────────────┬────────────┘ └─────────────┬─────────────┘
              │                            │                            │
┌─────────────▼─────────────┐ ┌────────────▼────────────┐ ┌─────────────▼─────────────┐
│    cali-fw-caliXXXXXX     │ │    cali-tw-caliXXXXXX   │ │    Per-endpoint policy    │
│    (per-endpoint rules)   │ │   (per-endpoint rules)  │ │          chains           │
└───────────────────────────┘ └─────────────────────────┘ └───────────────────────────┘
```

### Flujo de datos de Felix

![Diagrama de secuencia que muestra a Felix recibiendo actualizaciones de políticas, endpoints y pools de IP del datastore y traduciendo cada una en reglas de iptables, entradas de tabla de rutas o configuración de interfaces de red.](../../../assets/diagrams/rendered/en-networking-calico-02-architecture-2.svg)

## BIRD: daemon de enrutamiento BGP

BIRD (BIRD Internet Routing Daemon) es el daemon BGP que Calico utiliza para distribuir rutas entre nodos.

### BIRD en la arquitectura de Calico

![Diagrama que muestra instancias de BIRD en cada nodo formando una malla iBGP completa para intercambiar rutas de Pod y, a continuación, estableciendo peering mediante eBGP con el switch top-of-rack y el router central para anunciar esas rutas externamente.](../../../assets/diagrams/rendered/en-networking-calico-02-architecture-3.svg)

### Tipos de sesión BGP

| Tipo de sesión          | Caso de uso                    | Configuración          |
| --------------------- | --------------------------- | ---------------------- |
| **Malla de nodo a nodo** | Predeterminado para clústeres pequeños  | Automática, malla completa   |
| **Route Reflector**   | Clústeres grandes (100+ nodos) | Nodos RR dedicados     |
| **Peering externo**  | Integración on-premises     | Configuración manual de pares BGP |

### Ejemplos de configuración BGP

#### Malla de nodo a nodo (predeterminada)

```yaml
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  logSeverityScreen: Info
  nodeToNodeMeshEnabled: true
  asNumber: 64512
```

#### Configuración de Route Reflector

```yaml
# Disable node-to-node mesh
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  nodeToNodeMeshEnabled: false
  asNumber: 64512
---
# Configure route reflector nodes
apiVersion: projectcalico.org/v3
kind: Node
metadata:
  name: node-rr-1
  labels:
    route-reflector: "true"
spec:
  bgp:
    routeReflectorClusterID: 224.0.0.1
---
# Configure BGP peer to route reflector
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: peer-to-rr
spec:
  nodeSelector: "!has(route-reflector)"
  peerSelector: route-reflector == "true"
```

#### Peering BGP externo

```yaml
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: tor-switch-peer
spec:
  peerIP: 10.0.0.1
  asNumber: 65001
  nodeSelector: rack == 'rack-1'
  password:
    secretKeyRef:
      name: bgp-passwords
      key: tor-password
  sourceAddress: UseNodeIP
  keepOriginalNextHop: false
```

### Proceso de propagación de rutas

![Diagrama de secuencia que muestra cómo Felix asigna la ruta de un nuevo Pod, la añade a la tabla de enrutamiento local de BIRD y la propaga a los nodos pares mediante una actualización BGP UPDATE para que la instalen y enruten Felix según corresponda.](../../../assets/diagrams/rendered/en-networking-calico-02-architecture-4.svg)

### Comandos de estado de BIRD

```bash
# Access BIRD CLI on a Calico node
kubectl exec -n calico-system calico-node-xxxxx -c calico-node -- birdcl

# Show BGP protocol status
birdcl> show protocols
name     proto    table    state  since       info
kernel1  Kernel   master   up     2024-01-01
device1  Device   master   up     2024-01-01
direct1  Direct   master   up     2024-01-01
Mesh_10_0_1_10  BGP  master  up   2024-01-01  Established
Mesh_10_0_1_11  BGP  master  up   2024-01-01  Established

# Show BGP routes
birdcl> show route protocol Mesh_10_0_1_10
192.168.1.0/26     via 10.0.1.10 on eth0 [Mesh_10_0_1_10 2024-01-01] * (100/0) [i]
192.168.1.64/26    via 10.0.1.10 on eth0 [Mesh_10_0_1_10 2024-01-01] * (100/0) [i]

# Show route details
birdcl> show route 192.168.1.0/26 all
```

## confd: administración de configuración

confd es una herramienta ligera de administración de configuración que observa el datastore de Calico y genera archivos de configuración de BIRD.

### Flujo de trabajo de confd

![Diagrama que muestra al watcher de confd reaccionando a recursos de configuración BGP, pares y nodos en el datastore de Calico, generando un archivo bird.cfg a partir de plantillas y entregándolo al proceso BIRD en ejecución.](../../../assets/diagrams/rendered/en-networking-calico-02-architecture-5.svg)

### Procesamiento de plantillas de confd

confd utiliza plantillas Go para generar la configuración de BIRD:

```
# Template: /etc/calico/confd/templates/bird.cfg.template
# Output: /etc/calico/confd/config/bird.cfg

router id {{.NodeIP}};

protocol kernel {
    learn;
    persist;
    scan time 2;
    import all;
    export {{if .ExportKernel}}all{{else}}none{{end}};
}

protocol device {
    scan time 2;
}

{{range .BGPPeers}}
protocol bgp {{.Name}} {
    local as {{$.LocalAS}};
    neighbor {{.PeerIP}} as {{.PeerAS}};
    import all;
    export {{if .ExportFilter}}filter {{.ExportFilter}}{{else}}all{{end}};
    {{if .Password}}password "{{.Password}}";{{end}}
    graceful restart;
}
{{end}}
```

## Typha: componente de escalado

Typha es un proxy de fan-out que se sitúa entre el servidor API de Kubernetes y los agentes Felix. Reduce la carga en el servidor API al almacenar en caché y distribuir actualizaciones del datastore.

### ¿Por qué Typha?

![Diagrama comparativo que muestra a cada Felix observando directamente la API de Kubernetes en un clúster pequeño frente a Pods de Typha que distribuyen actualizaciones en caché a cientos de agentes Felix en un clúster grande.](../../../assets/diagrams/rendered/en-networking-calico-02-architecture-6.svg)

### Cálculo de escalado de Typha

El número recomendado de réplicas de Typha depende del tamaño del clúster:

```
Typha Replicas = max(3, ceil(Nodes / 200))

Examples:
- 50 nodes:   3 Typha replicas (minimum)
- 200 nodes:  3 Typha replicas
- 500 nodes:  3 Typha replicas
- 1000 nodes: 5 Typha replicas
- 2000 nodes: 10 Typha replicas
```

### Configuración del Deployment de Typha

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: calico-typha
  namespace: calico-system
spec:
  replicas: 3
  revisionHistoryLimit: 2
  selector:
    matchLabels:
      k8s-app: calico-typha
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 1
  template:
    metadata:
      labels:
        k8s-app: calico-typha
    spec:
      nodeSelector:
        kubernetes.io/os: linux
      tolerations:
      - key: CriticalAddonsOnly
        operator: Exists
      priorityClassName: system-cluster-critical
      serviceAccountName: calico-typha
      containers:
      - name: calico-typha
        image: calico/typha:v3.29.0
        ports:
        - containerPort: 5473
          name: calico-typha
          protocol: TCP
        env:
        - name: TYPHA_LOGSEVERITYSCREEN
          value: "info"
        - name: TYPHA_LOGFILEPATH
          value: "none"
        - name: TYPHA_LOGSEVERITYSYS
          value: "none"
        - name: TYPHA_CONNECTIONREBALANCINGMODE
          value: "kubernetes"
        - name: TYPHA_DATASTORETYPE
          value: "kubernetes"
        - name: TYPHA_HEALTHENABLED
          value: "true"
        - name: TYPHA_PROMETHEUSMETRICSENABLED
          value: "true"
        - name: TYPHA_PROMETHEUSMETRICSPORT
          value: "9093"
        livenessProbe:
          httpGet:
            path: /liveness
            port: 9098
          periodSeconds: 30
          initialDelaySeconds: 30
        readinessProbe:
          httpGet:
            path: /readiness
            port: 9098
          periodSeconds: 10
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 1000m
            memory: 512Mi
---
apiVersion: v1
kind: Service
metadata:
  name: calico-typha
  namespace: calico-system
spec:
  ports:
  - port: 5473
    protocol: TCP
    targetPort: calico-typha
    name: calico-typha
  selector:
    k8s-app: calico-typha
```

### Arquitectura de fan-out de Typha

![Diagrama de arquitectura que muestra dos flujos de observación del servidor API alimentando dos Pods de Typha, cada uno almacenando actualizaciones localmente en caché y distribuyéndolas a aproximadamente cien agentes Felix en su grupo de nodos.](../../../assets/diagrams/rendered/en-networking-calico-02-architecture-7.svg)

## kube-controllers: integración con Kubernetes

El Pod calico-kube-controllers ejecuta un conjunto de controllers que sincronizan los recursos de Kubernetes con el datastore de Calico.

### Descripción general de controllers

| Controller                      | Propósito                                           |
| ------------------------------- | ------------------------------------------------- |
| **Node Controller**             | Sincroniza los nodos de Kubernetes con los recursos de nodos de Calico |
| **Policy Controller**           | Sincroniza NetworkPolicy de Kubernetes con la política de Calico |
| **Namespace Controller**        | Sincroniza las etiquetas de namespace para la administración de perfiles     |
| **ServiceAccount Controller**   | Sincroniza las etiquetas de service account para RBAC             |
| **WorkloadEndpoint Controller** | Limpia endpoints de carga de trabajo obsoletos                |

### Bucle de reconciliación del controller

![Diagrama de secuencia que muestra a kube-controllers listando repetidamente recursos de Kubernetes y Calico, comparándolos y escribiendo los cambios en el datastore de Calico o no realizando ninguna acción cuando ambos ya están sincronizados.](../../../assets/diagrams/rendered/en-networking-calico-02-architecture-8.svg)

### Configuración de kube-controllers

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: calico-kube-controllers-config
  namespace: calico-system
data:
  config: |
    {
      "logSeverityScreen": "info",
      "healthEnabled": true,
      "prometheusPort": 9094,
      "controllers": {
        "node": {
          "hostEndpoint": {
            "autoCreate": "Disabled"
          },
          "syncLabels": "Enabled",
          "leakGracePeriod": "15m"
        },
        "policy": {
          "reconcilerPeriod": "5m"
        },
        "workloadEndpoint": {
          "reconcilerPeriod": "5m"
        },
        "namespace": {
          "reconcilerPeriod": "5m"
        },
        "serviceAccount": {
          "reconcilerPeriod": "5m"
        }
      }
    }
```

## Opciones de datastore

Calico admite dos backends de datastore para almacenar su configuración y estado.

### Datastore de API de Kubernetes (recomendado)

![Diagrama que muestra a Felix, Typha y kube-controllers leyendo y escribiendo el estado de Calico mediante el servidor API de Kubernetes, que a su vez persiste en etcd; no se requiere un clúster etcd de Calico independiente.](../../../assets/diagrams/rendered/en-networking-calico-02-architecture-9.svg)

**Ventajas:**

* No hay un clúster etcd independiente que administrar
* Utiliza Kubernetes RBAC para el control de acceso
* Modelo operativo más sencillo
* Funciona con cualquier distribución de Kubernetes

### Datastore etcd (heredado)

![Diagrama que muestra a Felix y Typha leyendo y escribiendo directamente en un clúster etcd de Calico dedicado mientras kube-controllers conecta ese clúster con el servidor API de Kubernetes: la opción de datastore heredada y desacoplada.](../../../assets/diagrams/rendered/en-networking-calico-02-architecture-10.svg)

**Ventajas:**

* Desacoplado del servidor API de Kubernetes
* Se puede utilizar para cargas de trabajo que no son de Kubernetes (VM, bare metal)
* Opción histórica para clústeres muy grandes

### Comparación de datastores

| Característica                    | API de Kubernetes    | etcd               |
| -------------------------- | ----------------- | ------------------ |
| **Complejidad operativa** | Menor             | Mayor             |
| **Escalabilidad**            | Buena (con Typha) | Excelente          |
| **Cargas de trabajo no K8s**      | Limitadas           | Compatibilidad completa       |
| **Backup/Restore**         | Mediante K8s           | Herramientas independientes   |
| **Control de acceso**         | K8s RBAC          | Autenticación de etcd          |
| **Recomendación**         | Opción predeterminada    | Solo casos especiales |

## Secuencia de interacción de componentes

![Diagrama de secuencia que rastrea una NetworkPolicy y la creación de un Pod desde la API de Kubernetes a través de kube-controllers y Typha hasta Felix, que programa el plano de datos local y actualiza las rutas BGP.](../../../assets/diagrams/rendered/en-networking-calico-02-architecture-11.svg)

## Análisis del flujo de paquetes

### Flujo de paquetes de entrada (Pod a Pod, mismo nodo)

![Diagrama que muestra un paquete que pasa de un Pod a otro en el mismo nodo mediante sus interfaces veth y la comprobación de políticas de iptables/eBPF del host.](../../../assets/diagrams/rendered/en-networking-calico-02-architecture-12.svg)

### Flujo de paquetes de salida (Pod a Pod, nodos diferentes con IPIP)

![Diagrama que muestra un paquete que sale del Pod de un nodo mediante su veth y la comprobación de iptables, se encapsula con IPIP a través del switch de red física y se desencapsula y entrega a un Pod en un segundo nodo.](../../../assets/diagrams/rendered/en-networking-calico-02-architecture-13.svg)

### Comparación de estructuras de paquetes

```
Original Pod-to-Pod Packet:
┌─────────────────────────────────────────────────────────────┐
│ Ethernet │   IP Header    │   TCP/UDP   │     Payload      │
│  Header  │ Src: 192.168.1.10 │   Header    │                  │
│          │ Dst: 192.168.2.10 │             │                  │
└─────────────────────────────────────────────────────────────┘

IPIP Encapsulated Packet:
┌───────────────────────────────────────────────────────────────────────────────┐
│ Ethernet │   Outer IP     │   Inner IP     │   TCP/UDP   │     Payload      │
│  Header  │ Src: 10.0.1.10 │ Src: 192.168.1.10 │   Header    │                  │
│          │ Dst: 10.0.1.11 │ Dst: 192.168.2.10 │             │                  │
│          │ Proto: 4 (IPIP)│                │             │                  │
└───────────────────────────────────────────────────────────────────────────────┘
```

## Resumen

La arquitectura de Calico está diseñada para ofrecer escalabilidad, rendimiento y simplicidad operativa:

1. **Felix**: El agente principal en cada nodo, que programa rutas y ACL
2. **BIRD**: Distribuye rutas mediante BGP, lo que permite la integración con el enrutamiento nativo
3. **confd**: Conecta el datastore con la configuración de BIRD
4. **Typha**: Escala el sistema al reducir la carga del servidor API
5. **kube-controllers**: Mantiene Kubernetes y Calico sincronizados
6. **Datastore**: API de Kubernetes (recomendada) o etcd para el almacenamiento de configuración

Comprender estos componentes y sus interacciones es esencial para:

* Solucionar problemas de conectividad
* Optimizar el rendimiento a escala
* Planificar la capacidad y la arquitectura
* Integrarse con la infraestructura de red existente

[Anterior: Parte 1 - Introducción a Calico](01-introduction.md)

[Siguiente: Parte 3 - Modos de red](03-networking-modes.md)

[Volver a la descripción general de Calico](./README.md)

## Cuestionario

Para poner a prueba lo aprendido en este capítulo, prueba el [Cuestionario de arquitectura](../../quizzes/networking/calico/02-architecture-quiz.md).
