# Cuestionario sobre arquitectura de clústeres

Este cuestionario evalúa tu comprensión de la arquitectura de clústeres de Kubernetes, sus componentes principales, las rutas de comunicación y las configuraciones de alta disponibilidad.

## Preguntas de opción múltiple

1. ¿Cuál de los siguientes NO es un componente principal del plano de control de Kubernetes?
   - A) kube-apiserver
   - B) etcd
   - C) kube-proxy
   - D) kube-scheduler
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) kube-proxy**

**Explicación:**
kube-proxy es un componente de nodo, no del plano de control. Los componentes principales del plano de control son kube-apiserver, etcd, kube-scheduler, kube-controller-manager y cloud-controller-manager. kube-proxy se ejecuta en cada nodo, mantiene las reglas de red y reenvía las conexiones.
</details>

2. ¿Qué componente de Kubernetes actúa como la «fuente de verdad» que almacena el estado de la API?
   - A) kube-apiserver
   - B) etcd
   - C) kube-controller-manager
   - D) kubelet
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) etcd**

**Explicación:**
etcd es un almacén de clave-valor coherente y de alta disponibilidad que guarda el estado de la API de Kubernetes y actúa como su «fuente de verdad». El estado, la configuración y los metadatos del clúster se almacenan en etcd. Los demás componentes del plano de control leen y escriben esa información a través de kube-apiserver.
</details>

3. ¿Cuál de los siguientes NO es un componente de nodo de Kubernetes?
   - A) kubelet
   - B) kube-proxy
   - C) Runtime de contenedores
   - D) kube-controller-manager
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: D) kube-controller-manager**

**Explicación:**
kube-controller-manager es un componente del plano de control, no de nodo. Los componentes de nodo son kubelet, kube-proxy y un runtime de contenedores, como containerd o CRI-O. kube-controller-manager se ejecuta en el plano de control y ejecuta varios procesos de controladores, como el controlador de nodos y el de replicación.
</details>

4. ¿Qué componente del plano de control de Kubernetes selecciona los nodos donde se ejecutarán los Pods recién creados?
   - A) kube-apiserver
   - B) kube-scheduler
   - C) kubelet
   - D) kube-controller-manager
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) kube-scheduler**

**Explicación:**
kube-scheduler es el componente del plano de control que selecciona los nodos donde se ejecutarán los Pods nuevos. Primero filtra los nodos aptos y luego asigna puntuaciones a los candidatos antes de elegir el nodo más adecuado. Considera los requisitos de recursos, las restricciones de hardware, software y políticas, las reglas de afinidad y antiafinidad, la localidad de los datos y la interferencia entre cargas de trabajo.
</details>

5. ¿Qué componente del plano de control interactúa con las API del proveedor de nube?
   - A) kube-apiserver
   - B) etcd
   - C) cloud-controller-manager
   - D) kubelet
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) cloud-controller-manager**

**Explicación:**
cloud-controller-manager es un componente del plano de control que contiene lógica específica de la nube e interactúa con las API del proveedor de nube. Así se separa el núcleo de Kubernetes de esas API. cloud-controller-manager ejecuta controladores específicos de la nube, como los de nodos, rutas y servicios. Los controladores CSI y sus plugins de nodo se encargan del aprovisionamiento, la conexión y el montaje del almacenamiento.
</details>

6. ¿Qué agente se ejecuta en cada nodo y administra la ejecución de contenedores dentro de los Pods?
   - A) kube-proxy
   - B) kubelet
   - C) containerd
   - D) kube-scheduler
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) kubelet**

**Explicación:**
kubelet es un agente que se ejecuta en cada nodo y administra los contenedores de los Pods. Recibe PodSpecs por varios mecanismos y procura que los contenedores se ejecuten de acuerdo con esas especificaciones. Entre sus funciones están iniciar los contenedores, supervisar e informar su estado, administrar su ciclo de vida y los montajes de volúmenes, informar el estado del nodo y realizar comprobaciones de estado.
</details>

7. ¿Qué componente de nodo de Kubernetes mantiene las reglas de red para las IP de los Service y reenvía las conexiones?
   - A) kubelet
   - B) kube-proxy
   - C) CNI plugin
   - D) containerd
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) kube-proxy**

**Explicación:**
kube-proxy es un proxy de red que se ejecuta en cada nodo e implementa el concepto de Service de Kubernetes. Mantiene reglas de red y reenvía conexiones a las IP y los puertos de Service. También proporciona balanceo de carga y detección de servicios. En Linux admite los modos iptables y nftables; en Windows, kernelspace. IPVS dejó de estar recomendado en Kubernetes 1.35 y el modo userspace se eliminó.
</details>

8. ¿Cuál es la interfaz estándar para ejecutar contenedores en Kubernetes?
   - A) CRI (Container Runtime Interface)
   - B) CNI (Container Network Interface)
   - C) CSI (Container Storage Interface)
   - D) CPI (Container Platform Interface)
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: A) CRI (Container Runtime Interface)**

**Explicación:**
CRI (Container Runtime Interface) es la interfaz estándar para ejecutar contenedores en Kubernetes. Mediante CRI, Kubernetes admite distintos runtimes de contenedores, como containerd y CRI-O. CRI define las API para la comunicación entre kubelet y el runtime, lo que permite crear, iniciar, detener y eliminar contenedores. CNI (Container Network Interface) proporciona la interfaz de red y CSI (Container Storage Interface), la de almacenamiento.
</details>

9. ¿Qué interfaz se usa para implementar la red de Pods en clústeres de Kubernetes?
   - A) CRI (Container Runtime Interface)
   - B) CNI (Container Network Interface)
   - C) CSI (Container Storage Interface)
   - D) API (Application Programming Interface)
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) CNI (Container Network Interface)**

**Explicación:**
CNI (Container Network Interface) es la interfaz estándar para implementar la red de Pods de Kubernetes. Los plugins de CNI conectan las interfaces de red a los Pods y les asignan direcciones IP. Entre los plugins disponibles están Calico, Cilium y Flannel, cada uno con distintas funciones y características de rendimiento. CNI permite que Kubernetes use diferentes soluciones de red.
</details>

10. ¿Qué interfaz proporciona una conexión estándar entre Kubernetes y los sistemas de almacenamiento?
    - A) CRI (Container Runtime Interface)
    - B) CNI (Container Network Interface)
    - C) CSI (Container Storage Interface)
    - D) CPI (Cloud Provider Interface)
    
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) CSI (Container Storage Interface)**

**Explicación:**
CSI (Container Storage Interface) proporciona una interfaz estándar entre Kubernetes y los sistemas de almacenamiento. Los proveedores pueden desarrollar drivers de almacenamiento sin modificar el código de Kubernetes. CSI define API para crear y eliminar volúmenes, y para montarlos y desmontarlos. Hay distintos drivers CSI, como AWS EBS CSI, Azure Disk CSI y GCP PD CSI.
</details>

## Preguntas de respuesta corta

11. ¿Cómo se llama el componente del plano de control de Kubernetes que ejecuta varios procesos de controladores?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: kube-controller-manager**

**Explicación:**
kube-controller-manager ejecuta varios procesos de controladores, cada uno responsable de un aspecto del clúster. Entre ellos están los controladores de nodos, replicación, endpoints, cuentas de servicio y tokens, Jobs, CronJobs, DaemonSets, StatefulSets, PV y namespaces, además del recolector de basura.
</details>

12. ¿Qué algoritmo de consenso utiliza Kubernetes para garantizar la consistencia de los datos de etcd?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: Raft**

**Explicación:**
etcd usa el algoritmo de consenso Raft para mantener la coherencia de los datos en sistemas distribuidos. Raft alcanza el consenso mediante la elección de líder, la replicación del log y propiedades de seguridad. Los clústeres de etcd suelen tener 3 o 5 nodos y pueden seguir funcionando mientras esté operativa la mayoría (quorum).
</details>

13. ¿Qué modo usa kube-proxy de forma predeterminada en Linux si no se selecciona explícitamente ninguno?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: iptables**

**Explicación:**
El modo predeterminado de kube-proxy es iptables. En ese modo, kube-proxy usa iptables de Linux para implementar NAT y dirigir a los Pods el tráfico destinado a las IP de Service. nftables es otro modo de Linux y es estable desde Kubernetes 1.33; antes de migrar, comprueba la compatibilidad del kernel y de CNI. IPVS dejó de estar recomendado en 1.35; se prevé deshabilitarlo de forma predeterminada en 1.40 y eliminarlo en 1.43. El modo userspace se eliminó. Windows usa kernelspace.
</details>

14. ¿Cómo se llama el archivo de configuración que se usa para comunicarse con el API server de un clúster de Kubernetes?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: kubeconfig**

**Explicación:**
kubeconfig es el archivo de configuración que se usa para comunicarse con el servidor de la API de Kubernetes. Contiene información del clúster, credenciales de autenticación (certificados, tokens, etc.) y contextos, que combinan clústeres y usuarios. kubectl usa $HOME/.kube/config de forma predeterminada, pero puedes indicar otro archivo mediante la opción --kubeconfig o la variable de entorno KUBECONFIG.
</details>

15. ¿Cuál es el número mínimo recomendado habitualmente de nodos del plano de control para configurar un clúster de Kubernetes de alta disponibilidad?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: 3**

**Explicación:**
El mínimo recomendado habitualmente es de 3 nodos del plano de control, porque los clústeres de etcd requieren una mayoría (quorum). Con 3 nodos, el clúster sigue funcionando si falla 1 (2 forman la mayoría). Con 5 nodos, puede tolerar el fallo de 2 (3 forman la mayoría). En general, se recomienda usar un número impar de nodos.
</details>

## Preguntas prácticas

16. Escribe un comando para crear una copia de seguridad de la base de datos de etcd. El archivo debe guardarse en `/backup/etcd-snapshot-$(date +%Y%m%d).db`, el endpoint de etcd es `https://127.0.0.1:2379`, y los archivos de certificado están en el directorio `/etc/kubernetes/pki/etcd/`.

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
Este comando establece ETCDCTL_API=3 para usar la API v3 de etcdctl y crea una instantánea de la base de datos con snapshot save. El parámetro --endpoints indica el endpoint del servidor etcd; --cacert, --cert y --key especifican los certificados necesarios para la autenticación TLS. El archivo de copia de seguridad se guarda en el directorio /backup con un nombre que incluye la fecha actual.
</details>

17. Escribe un archivo de configuración de kube-scheduler (YAML) que cumpla los siguientes requisitos:
    - Nombre del scheduler: custom-scheduler
    - Elección de líder habilitada
    - Plugin de puntuación: establecer el peso de NodeResourcesBalancedAllocation en 2
    - Plugin de filtrado: mantener habilitado NodeUnschedulable para excluir los nodos marcados como no programables

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
            weight: 2
        disabled: []
```

**Explicación:**
Este archivo YAML define un objeto KubeSchedulerConfiguration. leaderElection.leaderElect: true habilita elección de líder, y la sección profiles define un perfil de scheduler llamado custom-scheduler. En la sección plugins, el peso de NodeResourcesBalancedAllocation se establece en 2 en los plugins de puntuación. El filtro NodeUnschedulable permanece habilitado y excluye los nodos marcados como no programables; deshabilitarlo permitiría programar Pods en nodos acordonados.
</details>

18. Escribe un comando de inicio de etcd para configurar un clúster etcd de alta disponibilidad que cumpla los siguientes requisitos:
    - Nombre del nodo: etcd-1
    - Nombre del clúster: etcd-cluster
    - URL de cliente: https://192.168.1.10:2379
    - URL de comunicación entre pares: https://192.168.1.10:2380
    - Clúster inicial: etcd-1=https://192.168.1.10:2380,etcd-2=https://192.168.1.11:2380,etcd-3=https://192.168.1.12:2380
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
--client-cert-auth=true \
--peer-cert-file=/etc/kubernetes/pki/etcd/peer.crt \
--peer-key-file=/etc/kubernetes/pki/etcd/peer.key \
--peer-trusted-ca-file=/etc/kubernetes/pki/etcd/ca.crt \
--peer-client-cert-auth=true
```

**Explicación:**
Este comando inicia un nodo etcd llamado etcd-1. --initial-advertise-peer-urls y --listen-peer-urls especifican las URL para la comunicación entre pares; --listen-client-urls y --advertise-client-urls especifican las URL para la comunicación con clientes. --initial-cluster-token define un identificador único del clúster, y --initial-cluster enumera sus nodos. --initial-cluster-state=new indica que se crea un clúster nuevo. --data-dir indica dónde se almacenarán sus datos. Por último, los parámetros de certificados especifican los archivos necesarios para la comunicación TLS.
</details>

## Preguntas avanzadas

19. Diseña una arquitectura de alta disponibilidad para un clúster de Kubernetes y explica los métodos de despliegue para los componentes del plano de control y etcd, la configuración del balanceador de carga y las medidas de respuesta para escenarios de fallo.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

**Diseño de una arquitectura de alta disponibilidad para Kubernetes**

1. **Despliegue de los componentes del plano de control**:
  - Distribuye al menos 3 nodos del plano de control entre varias zonas de disponibilidad.
  - Despliega kube-apiserver, kube-scheduler y kube-controller-manager en cada nodo.
  - Ejecuta kube-scheduler y kube-controller-manager con elección de líder; solo una instancia está activa a la vez.
  - kube-apiserver escala horizontalmente: todas sus instancias pueden estar activas al mismo tiempo.

2. **Métodos de despliegue de etcd**:
  - Topología apilada: despliega etcd junto con los nodos del plano de control.
  - Topología externa: despliega etcd en nodos separados para lograr mayor aislamiento y escalabilidad.
  - Distribuye al menos 3 nodos de etcd entre varias zonas de disponibilidad. Elige 3 o 5 según la tolerancia a fallos y la latencia.
  - El clúster de etcd usa el consenso Raft para mantener la coherencia de los datos.

3. **Configuración del balanceador de carga**:
  - Coloca un balanceador de carga delante de kube-apiserver.
  - Usa paso TCP de capa 4 para conservar TLS de extremo a extremo y la autenticación mediante certificados de cliente.
  - Detecta con comprobaciones de estado las instancias de kube-apiserver que no estén sanas y exclúyelas del tráfico.
  - En la nube, usa balanceadores administrados por el proveedor, como AWS ELB o GCP Cloud Load Balancer.
  - En instalaciones locales, puedes usar HAProxy, NGINX o keepalived.

4. **Escenarios de fallo y medidas de respuesta**:
  - **Fallo de un nodo del plano de control**:
    - kube-apiserver: el balanceador dirige el tráfico a nodos sanos.
    - kube-scheduler y kube-controller-manager: la elección de líder activa una instancia de otro nodo.
    - etcd: el clúster sigue operando si la mayoría permanece sana (2 de 3 o 3 de 5).
  - **Fallo de una zona de disponibilidad**:
    - Distribuye los nodos entre varias zonas para tolerar el fallo de una zona.
    - Distribuye también los nodos de trabajo entre varias zonas.
  - **Partición de red**:
    - etcd usa la mayoría para evitar el split brain durante una partición.
    - La minoría no puede confirmar escrituras ni atender lecturas linealizables. Las lecturas serializables solicitadas explícitamente pueden devolver datos locales obsoletos.
  - **Corrupción o pérdida de datos de etcd**:
    - Realiza copias de seguridad periódicas de etcd.
    - Documenta y prueba los procedimientos de recuperación a partir de las copias.

5. **Consideraciones adicionales**:
  - **Administración de certificados**: supervisa su vencimiento y renovación automática.
  - **Registro de auditoría**: habilita registros de auditoría para operaciones importantes y almacénalos fuera del clúster.
  - **Supervisión y alertas**: configura la supervisión y las alertas del estado de los componentes del plano de control.
  - **Recuperación automatizada**: implementa mecanismos de recuperación, por ejemplo, el reinicio automático mediante systemd.

Con esta arquitectura de alta disponibilidad, el clúster de Kubernetes puede seguir funcionando aunque falle un nodo, una zona de disponibilidad o algunos componentes.
</details>

20. Explica la arquitectura de red de un clúster de Kubernetes, cómo funcionan la comunicación de Pod a Pod, la red de Service y la comunicación externa, y qué función cumplen los plugins de CNI. Explica también cómo restringir la comunicación entre Pods mediante NetworkPolicy.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

**Arquitectura de red de Kubernetes**

1. **Modelo de red de Kubernetes**:
  - Todos los Pods tienen direcciones IP únicas.
  - Los Pods pueden comunicarse sin NAT.
  - Los nodos y los Pods pueden comunicarse sin NAT.
  - Los contenedores de un mismo Pod se comunican mediante localhost.

2. **Comunicación de Pod a Pod**:
  - **Pods en el mismo nodo**: se comunican a través del plano de datos local, que puede usar un bridge, enrutamiento o eBPF según el plugin.
  - **Pods en nodos distintos**: se comunican mediante una red superpuesta o tablas de enrutamiento.
  - Los plugins de CNI asignan las direcciones IP de los Pods y configuran el enrutamiento.

3. **Red de los Services**:
  - **ClusterIP**: IP virtual accesible solo dentro del clúster.
  - **kube-proxy**: dirige a los Pods el tráfico destinado a las IP de Service.
  - Modo iptables: implementa NAT mediante reglas de iptables de Linux.
  - Modo nftables: programa el plano de datos de nftables en Linux; IPVS está obsoleto.
  - **CoreDNS**: servicio DNS que resuelve los nombres de Service a ClusterIP.
  - **Detección de servicios**: permite descubrir Services mediante variables de entorno o DNS.

4. **Comunicación externa**:
  - **Ingress**: dirige el tráfico HTTP/HTTPS a los Services.
  - **NodePort**: expone Services en puertos específicos de los nodos.
  - **LoadBalancer**: expone Services mediante un balanceador del proveedor de nube.
  - **ExternalName**: crea registros CNAME para servicios externos.

5. **Función de los plugins CNI (Container Network Interface)**:
  - Conectan interfaces de red a los Pods.
  - Asignan y administran direcciones IP.
  - Configuran tablas de enrutamiento.
  - Implementan políticas de red.
  - Algunos plugins de CNI:
    - **Calico**: red basada en BGP, compatible con políticas de red y de alto rendimiento.
    - **Cilium**: red y seguridad basadas en eBPF, políticas de seguridad L3-L7 y alto rendimiento.
    - **Flannel**: red superpuesta sencilla y fácil de configurar.

6. **Restricción de la comunicación entre Pods mediante NetworkPolicy**:
  - Controla la comunicación entre Pods con recursos NetworkPolicy.
  - Si no hay políticas, de forma predeterminada todos los Pods pueden comunicarse entre sí.
  - Una NetworkPolicy incluye:
    - **podSelector**: selecciona los Pods a los que se aplica la política.
    - **policyTypes**: Ingress (entrada), Egress (salida) o ambos.
    - **ingress**: reglas para el tráfico entrante.
    - **egress**: reglas para el tráfico saliente.
  - **Ejemplo de política de denegación predeterminada**:
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
  - **Ejemplo de política que solo permite la comunicación entre Pods específicos**:
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
  - **Ejemplo de control de comunicación entre namespaces**:
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

7. **Consideraciones para implementar NetworkPolicy**:
  - Los plugins de CNI implementan las políticas de red.
  - No todos los plugins de CNI las admiten.
  - Comprueba su comportamiento en un entorno de pruebas antes de aplicar las políticas.
  - Conviene empezar con una política de denegación predeterminada y permitir solo la comunicación necesaria.

La arquitectura de red de Kubernetes permite una comunicación flexible y escalable entre contenedores, y ofrece un control de seguridad detallado mediante políticas de red.
</details>

---

[Volver a los materiales de aprendizaje](../../core/01-cluster-architecture.md) | [Siguiente cuestionario: Pods y cargas de trabajo](../core/02-pods-and-workloads-quiz.md)
