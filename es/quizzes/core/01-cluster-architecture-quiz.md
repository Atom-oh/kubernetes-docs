# Cuestionario de arquitectura de cluster

Este cuestionario evalúa tu comprensión de la arquitectura de cluster de Kubernetes, sus componentes principales, las rutas de comunicación y las configuraciones de alta disponibilidad.

## Preguntas de opción múltiple

1. ¿Cuál de los siguientes NO es un componente principal del control plane de Kubernetes?
   - A) kube-apiserver
   - B) etcd
   - C) kube-proxy
   - D) kube-scheduler
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) kube-proxy**

**Explicación:**
kube-proxy es un componente de node, no un componente del control plane. Los componentes principales del control plane son kube-apiserver, etcd, kube-scheduler, kube-controller-manager y cloud-controller-manager. kube-proxy se ejecuta en cada node, mantiene las reglas de red y realiza el reenvío de conexiones.
</details>

2. ¿Qué componente en Kubernetes actúa como la "fuente de verdad" que almacena todos los datos del cluster?
   - A) kube-apiserver
   - B) etcd
   - C) kube-controller-manager
   - D) kubelet
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) etcd**

**Explicación:**
etcd es un almacén clave-valor consistente y de alta disponibilidad que guarda todos los datos del cluster y actúa como la "fuente de verdad" de Kubernetes. Todo el estado, la configuración y los metadatos del cluster se almacenan en etcd, y todos los demás componentes del control plane interactúan a través de kube-apiserver para leer y escribir información en etcd.
</details>

3. ¿Cuál de los siguientes NO es un componente de node de Kubernetes?
   - A) kubelet
   - B) kube-proxy
   - C) Container runtime
   - D) kube-controller-manager
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: D) kube-controller-manager**

**Explicación:**
kube-controller-manager es un componente del control plane, no un componente de node. Los componentes de node son kubelet, kube-proxy y container runtime (containerd, CRI-O, etc.). kube-controller-manager se ejecuta en el control plane y ejecuta varios procesos de controller, como node controller y replication controller.
</details>

4. ¿Qué componente del control plane en Kubernetes selecciona los nodes para ejecutar pods recién creados?
   - A) kube-apiserver
   - B) kube-scheduler
   - C) kubelet
   - D) kube-controller-manager
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) kube-scheduler**

**Explicación:**
kube-scheduler es el componente del control plane que selecciona los nodes para ejecutar pods recién creados. El proceso de scheduling consta de filtering (identificar los nodes que pueden ejecutar el pod) y scoring (asignar puntuaciones a los nodes adecuados), y finalmente asigna el pod al node óptimo. kube-scheduler considera requisitos de recursos, restricciones de hardware/software/política, especificaciones de affinity/anti-affinity, localidad de datos e interferencia de workload.
</details>

5. ¿Qué componente del control plane interactúa con las APIs del cloud provider?
   - A) kube-apiserver
   - B) etcd
   - C) cloud-controller-manager
   - D) kubelet
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) cloud-controller-manager**

**Explicación:**
cloud-controller-manager es un componente del control plane que contiene lógica de control específica de la cloud e interactúa con las APIs del cloud provider. Esto permite separar el core de Kubernetes de las APIs del cloud provider. cloud-controller-manager ejecuta controllers específicos de la cloud, como node controller, route controller, service controller y volume controller.
</details>

6. ¿Cuál es el agent que se ejecuta en cada node y gestiona la ejecución de containers dentro de pods?
   - A) kube-proxy
   - B) kubelet
   - C) containerd
   - D) kube-scheduler
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) kubelet**

**Explicación:**
kubelet es un agent que se ejecuta en cada node y gestiona la ejecución de containers dentro de pods. kubelet recibe PodSpecs mediante varios mecanismos y garantiza que los containers se ejecuten de forma saludable según esas especificaciones. Las funciones clave incluyen ejecutar containers según los PodSpecs, supervisar e informar el estado de los containers, gestionar el ciclo de vida de los containers, gestionar los mounts de volumes, informar el estado del node y realizar health checks de containers.
</details>

7. ¿Qué componente de node en Kubernetes mantiene las reglas de red para las IPs de Service y realiza el reenvío de conexiones?
   - A) kubelet
   - B) kube-proxy
   - C) CNI plugin
   - D) containerd
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) kube-proxy**

**Explicación:**
kube-proxy es un proxy de red que se ejecuta en cada node y es responsable de implementar el concepto de Service de Kubernetes. Mantiene reglas de red en los nodes y realiza el reenvío de conexiones. Las funciones clave incluyen mantener reglas de red para IPs y puertos de Service, reenvío de conexiones, implementación de load balancing y soporte para service discovery. kube-proxy admite varios modos de operación, incluidos userspace mode, iptables mode e IPVS mode.
</details>

8. ¿Cuál es la interfaz estándar para ejecutar containers en Kubernetes?
   - A) CRI (Container Runtime Interface)
   - B) CNI (Container Network Interface)
   - C) CSI (Container Storage Interface)
   - D) CPI (Container Platform Interface)
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: A) CRI (Container Runtime Interface)**

**Explicación:**
CRI (Container Runtime Interface) es la interfaz estándar para ejecutar containers en Kubernetes. A través de CRI, Kubernetes puede admitir varios container runtimes como containerd y CRI-O. CRI define APIs para la comunicación entre kubelet y container runtimes, lo que permite operaciones como crear, iniciar, detener y eliminar containers. CNI (Container Network Interface) es la interfaz para networking, y CSI (Container Storage Interface) es la interfaz para storage.
</details>

9. ¿Qué interfaz se utiliza para implementar pod networking en clusters de Kubernetes?
   - A) CRI (Container Runtime Interface)
   - B) CNI (Container Network Interface)
   - C) CSI (Container Storage Interface)
   - D) API (Application Programming Interface)
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) CNI (Container Network Interface)**

**Explicación:**
CNI (Container Network Interface) es la interfaz estándar para implementar pod networking en Kubernetes. Los CNI plugins son responsables de conectar interfaces de red a pods y asignar direcciones IP. Existen varios CNI plugins, incluidos Calico, Cilium, Flannel y Weave Net, cada uno con diferentes características y rendimiento. A través de CNI, Kubernetes puede admitir diversas soluciones de networking.
</details>

10. ¿Qué proporciona una interfaz estándar con sistemas de storage en clusters de Kubernetes?
    - A) CRI (Container Runtime Interface)
    - B) CNI (Container Network Interface)
    - C) CSI (Container Storage Interface)
    - D) CPI (Cloud Provider Interface)
    
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) CSI (Container Storage Interface)**

**Explicación:**
CSI (Container Storage Interface) proporciona una interfaz estándar entre Kubernetes y los sistemas de storage. A través de CSI, los storage providers pueden desarrollar sus propios storage drivers sin modificar el código de Kubernetes. CSI define APIs estandarizadas para operaciones como creación, eliminación, mounting y unmounting de volumes. Existen varios CSI drivers, incluidos AWS EBS CSI driver, Azure Disk CSI driver y GCP PD CSI driver.
</details>

## Preguntas de respuesta corta

11. ¿Cuál es el nombre del componente en el control plane de Kubernetes que ejecuta múltiples procesos de controller?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: kube-controller-manager**

**Explicación:**
kube-controller-manager es el componente del control plane que ejecuta múltiples procesos de controller. Cada controller gestiona un aspecto específico del cluster. Los controllers principales incluyen node controller, replication controller, endpoint controller, service account & token controller, job controller, cronjob controller, daemonset controller, statefulset controller, PV controller, namespace controller y garbage collector.
</details>

12. ¿Qué algoritmo de consenso utiliza Kubernetes para garantizar la consistencia de los datos de etcd?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: Raft**

**Explicación:**
etcd utiliza el algoritmo de consenso Raft para garantizar una consistencia fuerte de los datos en sistemas distribuidos. Raft logra consenso en sistemas distribuidos mediante leader election, log replication y safety. Los clusters de etcd suelen estar compuestos por 3 o 5 nodes, y el cluster puede seguir operando mientras una mayoría (quorum) de nodes funcione normalmente.
</details>

13. ¿Cuál es el modo de operación predeterminado de kube-proxy en Kubernetes?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: iptables**

**Explicación:**
El modo de operación predeterminado de kube-proxy es iptables mode. En este modo, kube-proxy usa Linux iptables para implementar NAT y enrutar el tráfico hacia las IPs de Service a pods. Otros modos de operación incluyen userspace mode (legacy) e IPVS mode (alto rendimiento). IPVS mode proporciona mejor rendimiento para clusters grandes, pero requiere el módulo IPVS en el kernel de Linux.
</details>

14. ¿Cuál es el nombre del archivo de configuración para comunicarse con el API server en un cluster de Kubernetes?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: kubeconfig**

**Explicación:**
kubeconfig es un archivo de configuración para comunicarse con el Kubernetes API server. Este archivo contiene información del cluster, información de autenticación (certificados, tokens, etc.) y contexts (combinaciones de clusters y users). El comando kubectl usa el archivo $HOME/.kube/config de forma predeterminada, pero se puede especificar otro archivo mediante la flag --kubeconfig o la variable de entorno KUBECONFIG.
</details>

15. ¿Cuántos control plane nodes se recomiendan generalmente como mínimo para configurar un cluster de alta disponibilidad en Kubernetes?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: 3**

**Explicación:**
El número mínimo generalmente recomendado de control plane nodes para un cluster de alta disponibilidad en Kubernetes es 3. Esto se debe a que los clusters de etcd operan sobre una base de mayoría (quorum). Con 3 nodes, el cluster puede seguir operando incluso si falla 1 node (2 es la mayoría). Con 5 nodes, el cluster puede seguir operando incluso si fallan 2 nodes (3 es la mayoría). Generalmente se recomienda usar un número impar de nodes.
</details>

## Preguntas prácticas

16. Escribe un comando para crear un backup de la base de datos de etcd. El archivo de backup debe guardarse en `/backup/etcd-snapshot-$(date +%Y%m%d).db`, el endpoint de etcd es `https://127.0.0.1:2379`, y los archivos de certificado están en el directorio `/etc/kubernetes/pki/etcd/`.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```bash
ETCDCTL_API=3 etcdctl snapshot save /backup/etcd-snapshot-$(date +%Y%m%d).db \
--endpoints=https://127.0.0.1:2379 \
--cacert=/etc/kubernetes/pki/etcd/ca.crt \
--cert=/etc/kubernetes/pki/etcd/server.crt \
--key=/etc/kubernetes/pki/etcd/server.key
```

**Explicación:**
Este comando establece la variable de entorno ETCDCTL_API en 3 para usar la API etcdctl v3 y crea un snapshot de la base de datos de etcd con el comando snapshot save. La flag --endpoints especifica el endpoint del servidor etcd, y las flags --cacert, --cert, --key especifican los archivos de certificado necesarios para la autenticación TLS. El archivo de backup se guarda en el directorio /backup con un nombre que incluye la fecha actual.
</details>

17. Escribe un archivo de configuración de kube-scheduler (YAML) que cumpla los siguientes requisitos:
    - Nombre del scheduler: custom-scheduler
    - Leader election habilitada
    - Plugin de scoring: establecer el peso de NodeResourcesBalancedAllocation en 2
    - Plugin de filtering: deshabilitar NodeUnschedulable

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
leaderElection:
  leaderElect: true

profiles:
  - schedulerName: custom-scheduler
    plugins:
      score:
        enabled:
          - name: NodeResourcesBalancedAllocation
        disabled: []
      filter:
        disabled:
          - name: NodeUnschedulable
```

**Explicación:**
Este archivo YAML define un objeto KubeSchedulerConfiguration. leaderElection.leaderElect: true habilita leader election, y la sección profiles define un perfil de scheduler llamado custom-scheduler. En la sección plugins, el peso de NodeResourcesBalancedAllocation se establece en 2 en los plugins de score, y NodeUnschedulable se deshabilita en los plugins de filter.
</details>

18. Escribe un comando de inicio de etcd para configurar un cluster etcd de alta disponibilidad que cumpla los siguientes requisitos:
    - Nombre del node: etcd-1
    - Nombre del cluster: etcd-cluster
    - URL de cliente: https://192.168.1.10:2379
    - Peer URL: https://192.168.1.10:2380
    - Cluster inicial: etcd-1=https://192.168.1.10:2380,etcd-2=https://192.168.1.11:2380,etcd-3=https://192.168.1.12:2380
    - Directorio de datos: /var/lib/etcd
    - Los archivos de certificado están en el directorio /etc/kubernetes/pki/etcd/

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```bash
etcd \
--name=etcd-1 \
--initial-advertise-peer-urls=https://192.168.1.10:2380 \
--listen-peer-urls=https://192.168.1.10:2380 \
--listen-client-urls=https://192.168.1.10:2379,https://127.0.0.1:2379 \
--advertise-client-urls=https://192.168.1.10:2379 \
--initial-cluster-token=etcd-cluster \
--initial-cluster=etcd-1=https://192.168.1.10:2380,etcd-2=https://192.168.1.11:2380,etcd-3=https://192.168.1.12:2380 \
--initial-cluster-state=new \
--data-dir=/var/lib/etcd \
--cert-file=/etc/kubernetes/pki/etcd/server.crt \
--key-file=/etc/kubernetes/pki/etcd/server.key \
--trusted-ca-file=/etc/kubernetes/pki/etcd/ca.crt \
--peer-cert-file=/etc/kubernetes/pki/etcd/peer.crt \
--peer-key-file=/etc/kubernetes/pki/etcd/peer.key \
--peer-trusted-ca-file=/etc/kubernetes/pki/etcd/ca.crt
```

**Explicación:**
Este comando inicia un node etcd llamado etcd-1. --initial-advertise-peer-urls y --listen-peer-urls especifican URLs para la comunicación entre peers, y --listen-client-urls y --advertise-client-urls especifican URLs para la comunicación con clientes. --initial-cluster-token especifica un identificador único para el cluster, y --initial-cluster enumera todos los nodes del cluster. --initial-cluster-state=new indica que se está creando un cluster nuevo. --data-dir especifica el directorio donde se almacenarán los datos de etcd. Finalmente, las flags relacionadas con certificados especifican los archivos de certificado para la comunicación TLS.
</details>

## Preguntas avanzadas

19. Diseña una arquitectura de alta disponibilidad para un cluster de Kubernetes y explica los métodos de despliegue para los componentes del control plane y etcd, la configuración del load balancer y las medidas de respuesta para escenarios de fallo.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

**Diseño de arquitectura de cluster Kubernetes de alta disponibilidad**

1. **Despliegue de componentes del control plane**:
  - Distribuir al menos 3 control plane nodes entre múltiples availability zones
  - Desplegar kube-apiserver, kube-scheduler y kube-controller-manager en cada node
  - Ejecutar kube-scheduler y kube-controller-manager en modo leader election (solo una instancia activa a la vez)
  - kube-apiserver es escalable horizontalmente (todas las instancias activas simultáneamente)

2. **Métodos de despliegue de etcd**:
  - Topología stacked: desplegar etcd junto con los control plane nodes
  - Topología external: desplegar etcd en nodes separados (mayor aislamiento y escalabilidad)
  - Distribuir al menos 3 etcd nodes entre múltiples availability zones (se recomiendan 5)
  - El cluster etcd usa el algoritmo de consenso Raft para garantizar la consistencia de los datos

3. **Configuración del load balancer**:
  - Colocar el load balancer delante de kube-apiserver
  - El load balancer puede operar a nivel L4 (TCP) o L7 (HTTP/HTTPS)
  - Detectar instancias no saludables de kube-apiserver mediante health checks y excluir el tráfico
  - En entornos cloud, usar load balancers gestionados por el cloud provider (AWS ELB, GCP Cloud Load Balancer, etc.)
  - En entornos on-premises, usar HAProxy, NGINX, keepalived, etc.

4. **Escenarios de fallo y medidas de respuesta**:
  - **Fallo de un solo control plane node**:
  - kube-apiserver: el load balancer enruta el tráfico a nodes saludables
  - kube-scheduler/kube-controller-manager: la instancia en otro node se activa mediante leader election
  - etcd: el cluster sigue operando si la mayoría está saludable (2 de 3, 3 de 5)

  - **Fallo de availability zone**:
  - Distribuir nodes entre múltiples availability zones para manejar fallos de una sola zone
  - Distribuir también worker nodes entre múltiples availability zones

  - **Partición de red**:
  - etcd opera sobre una base de mayoría para evitar "split brain" durante particiones de red
  - Los nodes de etcd en la partición minoritaria cambian a modo read-only

  - **Corrupción/pérdida de datos de etcd**:
  - Realizar backups regulares de etcd
  - Documentar y probar procedimientos de recuperación desde backups

5. **Consideraciones adicionales**:
  - **Gestión de certificados**: monitorizar la expiración de certificados y la renovación automática
  - **Audit logging**: habilitar audit logs para operaciones importantes y almacenarlos externamente
  - **Monitoring and alerting**: configurar monitoring y alerting para el estado de los componentes del control plane
  - **Recuperación automatizada**: implementar mecanismos de recuperación automatizada (por ejemplo, reinicio automático del servicio systemd)

Con esta arquitectura de alta disponibilidad, el cluster de Kubernetes puede seguir operando incluso si falla un solo node, una sola availability zone o algunos componentes.
</details>

20. Explica la arquitectura de networking de un cluster de Kubernetes, describe cómo funcionan la comunicación pod-to-pod, service networking y la comunicación externa, y explica el rol de los CNI plugins. También explica cómo restringir la comunicación pod-to-pod usando NetworkPolicy.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

**Arquitectura de networking de Kubernetes**

1. **Modelo de networking de Kubernetes**:
  - Todos los pods tienen direcciones IP únicas
  - Los pods pueden comunicarse sin NAT
  - Los nodes y pods pueden comunicarse sin NAT
  - Los containers dentro de un pod se comunican a través de localhost

2. **Comunicación pod-to-pod**:
  - **Entre pods en el mismo node**: comunicación a través de la red bridge local del node
  - **Entre pods en diferentes nodes**: comunicación a través de una overlay network o tablas de routing
  - Los CNI plugins gestionan la asignación de direcciones IP de pods y el routing

3. **Service networking**:
  - **ClusterIP**: IP virtual accesible solo dentro del cluster
  - **kube-proxy**: enruta el tráfico hacia IPs de Service a pods
  - iptables mode: implementa NAT usando reglas de Linux iptables
  - IPVS mode: proporciona load balancing de alto rendimiento usando IP Virtual Server del kernel de Linux
  - **CoreDNS**: Service DNS que resuelve nombres de Service a ClusterIPs
  - **Service discovery**: descubre Services mediante variables de entorno o DNS

4. **Comunicación externa**:
  - **Ingress**: enruta tráfico HTTP/HTTPS a Services
  - **NodePort**: expone Services a través de puertos específicos en nodes
  - **LoadBalancer**: expone Services a través del load balancer del cloud provider
  - **ExternalName**: crea registros CNAME para Services externos

5. **Rol de los CNI (Container Network Interface) Plugins**:
  - Conectar interfaces de red a pods
  - Asignar y gestionar direcciones IP
  - Configurar tablas de routing
  - Implementar NetworkPolicy
  - CNI plugins principales:
  - **Calico**: networking basado en BGP, soporte de NetworkPolicy, alto rendimiento
  - **Cilium**: networking y seguridad basados en eBPF, políticas de seguridad L3-L7, alto rendimiento
  - **Flannel**: overlay network simple, configuración sencilla
  - **Weave Net**: networking de containers multi-host, soporte de cifrado

6. **Restricción de comunicación pod-to-pod usando NetworkPolicy**:
  - Controlar la comunicación pod-to-pod usando recursos NetworkPolicy
  - De forma predeterminada, todos los pods pueden comunicarse entre sí (cuando no existen políticas)
  - Componentes de una NetworkPolicy:
  - **podSelector**: selecciona los pods a los que se aplica la política
  - **policyTypes**: Ingress (entrante), Egress (saliente) o ambos
  - **ingress**: reglas para tráfico entrante
  - **egress**: reglas para tráfico saliente

  - **Ejemplo de política default deny**:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
```

  - **Ejemplo de política que permite comunicación solo entre pods específicos**:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
spec:
  podSelector:
    matchLabels:
      app: backend
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

  - **Ejemplo de control de comunicación namespace-to-namespace**:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-monitoring
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
    - Ingress
  ingress:
    - from:
      - namespaceSelector:
          matchLabels:
            purpose: monitoring
      ports:
        - protocol: TCP
          port: 9090
```

7. **Consideraciones para la implementación de NetworkPolicy**:
  - Las NetworkPolicies son implementadas por CNI plugins
  - No todos los CNI plugins admiten NetworkPolicy
  - Verificar en un entorno de prueba antes de aplicar políticas
  - Se recomienda comenzar con una política default deny y permitir solo la comunicación necesaria

La arquitectura de networking de Kubernetes permite la comunicación entre containers de una manera flexible y escalable, y proporciona control de seguridad granular mediante NetworkPolicy.
</details>

---

[Volver a los materiales de aprendizaje](../../core/01-cluster-architecture.md) | [Siguiente cuestionario: Pods y Workloads](../core/02-pods-and-workloads-quiz.md)
