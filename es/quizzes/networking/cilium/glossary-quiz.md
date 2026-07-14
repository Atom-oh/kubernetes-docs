# Cuestionario de glosario

Este cuestionario evalúa tu comprensión de los términos y conceptos clave relacionados con Cilium, eBPF, Kubernetes y networking.

## Preguntas de opción múltiple

1. ¿Cuál es el nombre completo de eBPF?
   * A) Enhanced Berkeley Packet Filter
   * B) Extended Berkeley Packet Filter
   * C) Embedded BPF Filter
   * D) External Berkeley Protocol Filter

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Extended Berkeley Packet Filter**

**Explicación:** eBPF significa Extended Berkeley Packet Filter, una versión extendida de BPF (Berkeley Packet Filter) desarrollada originalmente para la captura de paquetes de red. eBPF es una tecnología que permite ejecutar programas de forma segura dentro del kernel de Linux, y se utiliza para varios fines, incluidos el procesamiento de paquetes de red, el rastreo de llamadas al sistema y la supervisión del rendimiento. Cilium aprovecha eBPF como su tecnología principal para proporcionar funciones de networking, seguridad y observabilidad de alto rendimiento.

</details>

2. ¿Cuál es la unidad básica a la que se aplican las políticas de red en Cilium?
   * A) Pod
   * B) Node
   * C) Endpoint
   * D) Service

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Endpoint**

**Explicación:** En Cilium, un Endpoint se refiere a un endpoint de red al que se aplican políticas de red, que normalmente corresponde a un Pod de Kubernetes. Cada Endpoint tiene un ID único, y Cilium aplica políticas de red y controla el tráfico según estos Endpoints. Los Endpoints son administrados por Cilium Agent y se crean automáticamente cuando se crean Pods. Puedes consultar todos los Endpoints en el Node actual mediante el comando `cilium endpoint list`.

</details>

3. ¿Cuál es la característica principal de XDP (eXpress Data Path)?
   * A) Análisis de protocolo L7
   * B) Procesamiento de paquetes a nivel de driver de red
   * C) Cifrado TLS
   * D) Resolución DNS

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Procesamiento de paquetes a nivel de driver de red**

**Explicación:** XDP (eXpress Data Path) es una tecnología basada en eBPF que procesa paquetes a nivel de driver de red (contexto de interrupción). Esto omite la pila de red del kernel para habilitar un procesamiento de paquetes de muy alto rendimiento (millones de paquetes por segundo). XDP puede procesar paquetes con acciones como DROP, PASS, TX (transmitir) y REDIRECT. Cilium utiliza XDP para implementar protección contra DDoS, balanceo de carga de alto rendimiento y filtrado de paquetes.

</details>

4. ¿Cuál es el nombre de la plataforma de observabilidad de red de Cilium?
   * A) Prometheus
   * B) Grafana
   * C) Hubble
   * D) Jaeger

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Hubble**

**Explicación:** Hubble es la plataforma de observabilidad de red de Cilium que utiliza eBPF para supervisar y analizar flujos de red en tiempo real. Las funciones principales de Hubble incluyen la supervisión de flujos de red, la generación de mapas de dependencias de servicios, la detección de infracciones de políticas de red, la recopilación de métricas de rendimiento y el seguimiento de eventos de seguridad. Hubble proporciona tanto CLI como una UI basada en web, y puede integrarse con Prometheus y Grafana para visualizar métricas.

</details>

5. ¿Cuál es el nombre completo y el propósito principal de VXLAN?
   * A) Virtual Extended LAN - Creación de red virtual
   * B) Virtual Extensible LAN - Red superpuesta L2
   * C) Very Extended LAN - Expansión de red a gran escala
   * D) Variable Extensible LAN - Configuración dinámica de red

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Virtual Extensible LAN - Red superpuesta L2**

**Explicación:** VXLAN (Virtual Extensible LAN) es una tecnología de virtualización de red que superpone redes de Layer 2 (L2) sobre redes de Layer 3 (L3). VXLAN utiliza encapsulación UDP para tunneling y admite hasta aproximadamente 16 millones de segmentos de red con un VNI (VXLAN Network Identifier) de 24 bits. En Cilium, VXLAN se utiliza como modo de networking superpuesto para la comunicación entre Pods de distintos Nodes. Las alternativas incluyen GENEVE o el modo de enrutamiento nativo.

</details>

6. ¿Cuál es la función principal de BPF Maps?
   * A) Administración de tablas de enrutamiento de red
   * B) Intercambio y almacenamiento de datos entre programas eBPF
   * C) Almacenamiento en caché de registros DNS
   * D) Almacenamiento de certificados TLS

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Intercambio y almacenamiento de datos entre programas eBPF**

**Explicación:** BPF Maps son almacenes de clave-valor utilizados por los programas eBPF para almacenar y recuperar datos. BPF Maps también se utilizan para intercambiar datos entre el espacio del kernel y el espacio de usuario. Los tipos principales incluyen Hash Map (almacén de clave-valor), Array Map (arreglo basado en índices), LRU Map (caché de uso menos reciente) y Ring Buffer (búfer circular). Cilium utiliza BPF Maps para almacenar mapas de servicios, mapas de backends, tablas de seguimiento de conexiones y más.

</details>

7. ¿Cómo se llama el identificador numérico que representa la identidad de seguridad de un Pod en Cilium?
   * A) Pod ID
   * B) Security Context
   * C) Identity
   * D) Endpoint ID

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Identity**

**Explicación:** Cilium Identity es un identificador numérico generado a partir del conjunto de labels de un Pod. Todos los Pods con los mismos labels comparten la misma Identity. Las políticas basadas en Identity utilizan Identity en lugar de direcciones IP para aplicar políticas de red, de modo que las políticas se mantienen coherentes incluso cuando cambian las IP de los Pods. Este enfoque es muy escalable y funciona de manera eficiente incluso en clusters grandes. Endpoint ID identifica una instancia específica de Pod y es diferente de Identity.

</details>

8. ¿Cuál es el nombre completo de IPAM y su función en Cilium?
   * A) IP Address Management - Asignación y administración de direcciones IP
   * B) Internet Protocol Access Manager - Administración de acceso a Internet
   * C) IP Assignment Module - Módulo de asignación de IP
   * D) Internal Protocol Address Mapper - Mapeo interno de direcciones de protocolo

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: A) IP Address Management - Asignación y administración de direcciones IP**

**Explicación:** IPAM (IP Address Management) es un sistema responsable de planificar, asignar, rastrear y administrar direcciones IP. Cilium admite varios modos IPAM: Cluster Pool (administración de pool de IP de todo el cluster), Kubernetes (uso del CIDR de Node de Kubernetes), AWS ENI (uso de AWS Elastic Network Interface), Azure (integración de networking de Azure) y GKE (integración de Google Kubernetes Engine). La selección del modo IPAM depende del entorno del cluster y de los requisitos de networking.

</details>

9. ¿Cuál es la característica principal de WireGuard y su uso en Cilium?
   * A) Herramienta de captura de paquetes - Análisis de red
   * B) Protocolo VPN moderno - Cifrado de tráfico entre Nodes
   * C) Algoritmo de balanceo de carga - Distribución de tráfico
   * D) Proxy DNS - Resolución de nombres

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Protocolo VPN moderno - Cifrado de tráfico entre Nodes**

**Explicación:** WireGuard es un protocolo de túnel VPN (Virtual Private Network) moderno, rápido y seguro. Es más simple y rápido que IPsec, con una base de código más pequeña que facilita la auditoría de seguridad. En Cilium, WireGuard se utiliza para el cifrado de tráfico entre Nodes. Cuando WireGuard está habilitado, todo el tráfico entre los Pods del cluster se cifra de forma transparente. Cilium puede implementar el cifrado con IPsec o WireGuard.

</details>

10. ¿Cuál es el nombre completo y la función de CNI?
    * A) Container Network Interface - Interfaz estándar para plugins de red de contenedores
    * B) Cloud Native Infrastructure - Infraestructura cloud native
    * C) Cluster Network Integration - Integración de red de cluster
    * D) Container Node Interconnect - Conexión de Node de contenedor

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: A) Container Network Interface - Interfaz estándar para plugins de red de contenedores**

**Explicación:** CNI (Container Network Interface) es un proyecto de CNCF que define una interfaz estándar entre los runtimes de contenedores y los plugins de red. En Kubernetes, kubelet se comunica con los plugins de red (Cilium, Calico, Flannel, etc.) mediante la interfaz CNI. CNI define una API estándar para la configuración de red cuando se agregan o eliminan contenedores, lo que permite integrar diversas soluciones de networking mediante una arquitectura de plugins. Cilium es una de las implementaciones de CNI.

</details>

## Preguntas de respuesta corta

11. ¿Cuál es el nombre del componente de código abierto que proporciona funcionalidad de proxy L7 y service mesh en Cilium?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:** Envoy

**Explicación:** Envoy es un proxy de borde y de servicios de código abierto utilizado como proxy L7 y bus de comunicación. Cilium integra Envoy para implementar políticas de red L7. Cuando defines reglas L7 (HTTP, gRPC, Kafka, DNS, etc.) en una CiliumNetworkPolicy, Cilium implementa automáticamente el proxy Envoy de forma transparente. Envoy también proporciona funciones avanzadas de balanceo de carga, división de tráfico y recopilación de métricas.

</details>

12. ¿Cuál es el nombre del componente de Cilium que se ejecuta en cada Node y es responsable de la carga de programas eBPF, la implementación de políticas de red y la administración de Endpoints?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:** Cilium Agent

**Explicación:** Cilium Agent es el componente principal de Cilium que se ejecuta como un DaemonSet en cada Node de Kubernetes. Las principales responsabilidades del Agent incluyen cargar y administrar programas eBPF en el kernel, implementar y aplicar políticas de red, realizar balanceo de carga de servicios, administración de direcciones IP (IPAM), administración de endpoints de red, recopilación de métricas y logs, y comunicación con el servidor de API de Kubernetes. Las operaciones de networking local en cada Node son gestionadas por el Cilium Agent de ese Node.

</details>

13. ¿Cuál es el nombre y número de la capa del modelo OSI responsable del enrutamiento de paquetes mediante direcciones IP?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:** L3 (Network Layer)

**Explicación:** L3 (Network Layer) es la tercera capa del modelo OSI, responsable del direccionamiento lógico mediante direcciones IP y del enrutamiento de paquetes. IP (Internet Protocol) e ICMP (Internet Control Message Protocol) operan en esta capa. Las políticas L3 de Cilium pueden filtrar tráfico según direcciones IP y bloques CIDR. L2 (Data Link Layer) utiliza direcciones MAC, y L4 (Transport Layer) utiliza números de puerto.

</details>

14. ¿Cuál es el nombre del recurso de Kubernetes que proporciona endpoints de red estables para un conjunto de Pods?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:** Service

**Explicación:** Kubernetes Service es una abstracción que proporciona endpoints de red estables (ClusterIP, nombre DNS) para un conjunto de Pods. Los Pods se crean y eliminan dinámicamente, y sus IP pueden cambiar, pero los Services proporcionan IP fijas y nombres DNS para un acceso coherente de los clientes. Cilium implementa el balanceo de carga de Service mediante eBPF, que puede sustituir a kube-proxy. Los tipos de Service incluyen ClusterIP, NodePort, LoadBalancer y ExternalName.

</details>

15. ¿Cuál es el nombre del tipo de NAT que modifica la dirección IP de origen de un paquete?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:** SNAT (Source NAT) o Masquerading

**Explicación:** SNAT (Source Network Address Translation) es un tipo de NAT que traduce la dirección IP de origen de un paquete a otra dirección IP. Masquerading es una forma especial de SNAT que traduce automáticamente la IP de origen a la IP de la interfaz de salida. En Cilium, masquerading se utiliza para traducir la IP de origen del tráfico saliente de los Pods dentro del cluster a la IP del Node. Por el contrario, DNAT (Destination NAT) modifica la IP de destino.

</details>

## Preguntas prácticas

16. Relaciona los siguientes términos relacionados con Cilium con sus definiciones: Cluster Mesh, CRD, FQDN, mTLS

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

* **Cluster Mesh**: Función de networking multi-cluster de Cilium. Conecta varios clusters de Kubernetes para habilitar el descubrimiento de servicios entre clusters, el balanceo de carga y la aplicación de políticas de red.
* **CRD (Custom Resource Definition)**: Un método para extender la API de Kubernetes mediante la definición de recursos personalizados. Cilium utiliza CRD para definir CiliumNetworkPolicy, CiliumEndpoint y más.
* **FQDN (Fully Qualified Domain Name)**: El nombre de dominio completo de un host (por ejemplo, www.example.com). Las políticas FQDN de Cilium controlan el acceso a servicios externos por nombre de dominio en lugar de IP.
* **mTLS (mutual TLS)**: Una extensión de TLS en la que tanto el cliente como el servidor se autentican mutuamente con certificados. Proporciona mayor seguridad mediante autenticación bidireccional.

**Explicación:** Estos términos se utilizan con frecuencia en el networking de Cilium y Kubernetes. Cluster Mesh es útil en entornos híbridos/multi-cloud, los CRD son fundamentales para la extensibilidad de Kubernetes, las políticas FQDN son esenciales para el control de acceso a servicios externos con IP dinámicas, y mTLS es importante para una comunicación segura entre servicios.

</details>

17. Escribe el comando para consultar todas las Identities y sus labels en el cluster actual mediante Cilium CLI.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

```bash
# Query all Identities
cilium identity list

# Or query CiliumIdentity CRD using kubectl
kubectl get ciliumidentity -A

# Query detailed information for a specific Identity
cilium identity get <identity_id>

# Query detailed information in JSON format
kubectl get ciliumidentity <identity_id> -o json

# Filter Identities with specific labels
kubectl get ciliumidentity -o json | jq '.items[] | select(.metadata.labels."k8s:app" == "frontend")'

# Check Identity from Endpoints
cilium endpoint list
kubectl exec -n kube-system ds/cilium -- cilium endpoint list
```

**Explicación:** Cilium Identity es un identificador numérico generado a partir del conjunto de labels de un Pod. El comando `cilium identity list` muestra todas las Identities y sus labels en el cluster actual. CiliumIdentity se almacena como un CRD, por lo que también se puede consultar con kubectl. Identity es la base de las políticas de red, y todos los Pods con los mismos labels comparten la misma Identity.

</details>

18. Escribe comandos para consultar el contenido de BPF Map a fin de comprobar los mapas de balanceo de carga de Service y las tablas de seguimiento de conexiones.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

```bash
# Query BPF maps from Cilium Agent pod

# Service map (Service -> Backend mapping)
kubectl exec -n kube-system ds/cilium -- cilium bpf lb list

# Backend map (backend pod information)
kubectl exec -n kube-system ds/cilium -- cilium bpf lb list --backends

# Connection Tracking table
kubectl exec -n kube-system ds/cilium -- cilium bpf ct list global

# NAT map (masquerading/SNAT information)
kubectl exec -n kube-system ds/cilium -- cilium bpf nat list

# Policy map (Identity-based policies)
kubectl exec -n kube-system ds/cilium -- cilium bpf policy get --all

# Endpoint map
kubectl exec -n kube-system ds/cilium -- cilium bpf endpoint list

# List all BPF maps
kubectl exec -n kube-system ds/cilium -- cilium bpf map list
```

**Explicación:** BPF Maps son estructuras de datos principales utilizadas en el plano de datos de Cilium. `cilium bpf lb list` muestra información de balanceo de carga de Service, lo que permite comprobar el mapeo entre la IP/puerto de Service y la IP/puerto del Pod backend. `cilium bpf ct list` muestra la tabla de seguimiento de conexiones, donde puedes comprobar el estado actual de las conexiones activas. Estos comandos son útiles para la solución de problemas de red y el análisis de rendimiento.

</details>

19. Escribe una CiliumNetworkPolicy que utilice una política de red basada en FQDN y permita que un Pod se comunique externamente solo con los dominios `api.example.com` y `*.googleapis.com`.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

```yaml
apiVersion: "cilium.io/v2"
kind: CiliumNetworkPolicy
metadata:
  name: "fqdn-egress-policy"
  namespace: default
spec:
  endpointSelector:
    matchLabels:
      app: external-client
  egress:
  # Allow DNS queries (required for FQDN policy to work)
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
        - matchPattern: "*"
  # Allow HTTPS traffic to specific FQDNs
  - toFQDNs:
    - matchName: "api.example.com"
    - matchPattern: "*.googleapis.com"
    toPorts:
    - ports:
      - port: "443"
        protocol: TCP
```

**Explicación:** Las políticas basadas en FQDN (Fully Qualified Domain Name) controlan el acceso a servicios externos por nombre de dominio en lugar de dirección IP. Para que esta política funcione, se deben permitir las consultas DNS (primera regla de egress). En `toFQDNs`, `matchName` especifica un nombre de dominio exacto y `matchPattern` especifica la coincidencia de patrones con comodines. `*.googleapis.com` permite todos los subdominios de Google API. Las políticas FQDN son especialmente útiles para el control de acceso a servicios externos con IP dinámicas.

</details>

20. Explica la función de Cilium Operator y sus diferencias respecto a Cilium Agent, y escribe comandos para comprobar el estado del Operator.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

```bash
# Check Cilium Operator status
kubectl -n kube-system get deployment cilium-operator

# Check Operator pod status
kubectl -n kube-system get pods -l name=cilium-operator

# Check Operator logs
kubectl -n kube-system logs -l name=cilium-operator

# Check Operator in overall Cilium status
cilium status --verbose

# Check CiliumIdentity resources (managed by Operator)
kubectl get ciliumidentity -A

# Check CiliumEndpoint resources
kubectl get ciliumendpoint -A
```

**Comparación de funciones de Cilium Operator y Cilium Agent:**

| Componente           | Ubicación de ejecución              | Responsabilidades principales                                                                                                                                        |
| ------------------- | ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Cilium Agent**    | Cada Node (DaemonSet)               | <p>- Carga/administración de programas eBPF<br>- Aplicación de políticas de red<br>- Administración de endpoints locales<br>- Balanceo de carga de Service<br>- IPAM a nivel de Node</p>           |
| **Cilium Operator** | Cluster (Deployment, 1-2 instancias) | <p>- Administración de CRD CiliumIdentity<br>- IPAM a nivel de cluster<br>- Sincronización de CiliumEndpoint<br>- Recolección de basura<br>- Administración de conexiones de Cluster Mesh</p> |

**Explicación:** Cilium Agent se ejecuta en cada Node y administra las operaciones de networking de ese Node. En cambio, Cilium Operator se ejecuta como una única instancia (o 2 para HA) en todo el cluster y administra tareas de coordinación a nivel de cluster. El Operator mantiene la coherencia de Identity en todo el cluster, limpia recursos no utilizados y administra IPAM a nivel de cluster.

</details>

***

[Volver a los materiales de aprendizaje](../../../networking/cilium/glossary.md) | [Lista de cuestionarios de Cilium](https://github.com/Atom-oh/kubernetes-docs/blob/main/en/quizzes/networking/cilium/README.md)
