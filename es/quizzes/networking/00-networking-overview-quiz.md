# Cuestionario de introducción a redes de Kubernetes

Este cuestionario evalúa tu comprensión de los fundamentos de redes de Kubernetes, CNI (Container Network Interface) y diversas soluciones de CNI.

## Preguntas del cuestionario

### 1. ¿Cuál NO es un requisito fundamental del modelo de redes de Kubernetes?

A. Cada Pod puede comunicarse con cualquier otro Pod sin NAT
B. Cada Node puede comunicarse con cada Pod sin NAT
C. La IP que un Pod ve como propia es la misma IP que otros ven para él
D. Cada Pod debe tener una dirección IP estática que persista después de los reinicios

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D. Cada Pod debe tener una dirección IP estática que persista después de los reinicios**

**Explicación:**
Los requisitos fundamentales del modelo de redes de Kubernetes son estos tres:
1. Cada Pod puede comunicarse con cualquier otro Pod sin NAT
2. Cada Node puede comunicarse con cada Pod sin NAT
3. La IP que un Pod ve como propia es la misma IP que otros ven para él

Las direcciones IP de los Pods son efímeras: cuando un Pod se reinicia, obtiene una IP nueva. Esta es exactamente la razón por la que se necesitan los Services.

</details>

### 2. ¿Cuál es la función principal de CNI (Container Network Interface)?

A. Comunicarse con el API server de Kubernetes para tomar decisiones de programación de Pods
B. Crear interfaces de red de contenedores y asignar direcciones IP
C. Implementar balanceo de carga para los Services de Kubernetes
D. Descargar y almacenar en caché imágenes de contenedores

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Crear interfaces de red de contenedores y asignar direcciones IP**

**Explicación:**
CNI es una interfaz estándar para la conectividad de red de contenedores. Sus funciones principales son:
- Crear interfaces de red cuando se crean contenedores (pares veth)
- Asignar direcciones IP (IPAM)
- Configurar reglas de enrutamiento
- Limpiar recursos de red cuando se eliminan contenedores

Kubelet llama al plugin de CNI para configurar las redes de los Pods.

</details>

### 3. ¿Cuál es la diferencia correcta entre las redes Overlay y Underlay (Native Routing)?

A. Overlay proporciona mayor rendimiento, mientras que Underlay implica más sobrecarga
B. Overlay construye una red virtual sobre la red existente, mientras que Underlay enruta directamente en la red física
C. Overlay usa BGP, mientras que Underlay usa VXLAN
D. Overlay solo está disponible en AWS, mientras que Underlay es solo para entornos on-premises

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Overlay construye una red virtual sobre la red existente, mientras que Underlay enruta directamente en la red física**

**Explicación:**
- **Overlay Network**: Usa encapsulación como VXLAN, IPIP para construir una red virtual sobre la red existente. Es sencilla de configurar, pero tiene sobrecarga de encapsulación.
- **Underlay (Native Routing)**: Enruta directamente en la red física para obtener mayor rendimiento. Usa BGP, etc., y requiere integración con la infraestructura de red.

</details>

### 4. ¿Qué tipo de Service de Kubernetes solo es accesible desde dentro del cluster?

A. NodePort
B. LoadBalancer
C. ClusterIP
D. ExternalName

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. ClusterIP**

**Explicación:**
Características de los tipos de Service de Kubernetes:
- **ClusterIP**: Asigna una IP virtual accesible solo dentro del cluster (predeterminado)
- **NodePort**: Acceso externo mediante puertos específicos (30000-32767) en todos los nodes
- **LoadBalancer**: Aprovisiona un balanceador de carga en la nube para el acceso externo
- **ExternalName**: Crea un registro CNAME para un nombre DNS externo

</details>

### 5. ¿Qué CNI utiliza la tecnología eBPF como base?

A. Flannel
B. Weave Net
C. Cilium
D. AWS VPC CNI

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Cilium**

**Explicación:**
Cilium es un CNI que utiliza eBPF (extended Berkeley Packet Filter) como su tecnología principal. Beneficios de eBPF:
- Alto rendimiento con procesamiento de red a nivel de kernel
- Procesamiento de paquetes más eficiente en comparación con iptables
- Visibilidad de L7 y aplicación de políticas
- Puede reemplazar kube-proxy

Aunque Calico también admite el modo eBPF, Cilium fue diseñado desde el principio con eBPF como base.

</details>

### 6. ¿Cuál NO es una característica de AWS VPC CNI?

A. Asigna direcciones IP reales de VPC a cada Pod
B. Utiliza ENI (Elastic Network Interfaces) de instancias EC2
C. La cantidad de IP que se puede asignar por Pod está limitada por el tipo de instancia
D. Admite de forma nativa Network Policy de L7

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D. Admite de forma nativa Network Policy de L7**

**Explicación:**
Características de AWS VPC CNI:
- Asigna direcciones IP reales de VPC a los Pods (nativo de VPC)
- Usa IP secundarias de ENI de EC2
- El número máximo de Pods está limitado por el tipo de instancia (cantidad de ENI × IP por ENI)
- Solo admite Network Policy de L3-L4 de forma predeterminada (L7 requiere Calico o Cilium)

Para Network Policy de L7, se necesitan soluciones adicionales como Cilium.

</details>

### 7. ¿Qué combinación de CNI admite BGP (Border Gateway Protocol)?

A. Flannel, Weave Net
B. Calico, Cilium
C. AWS VPC CNI, Flannel
D. Weave Net, AWS VPC CNI

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Calico, Cilium**

**Explicación:**
CNI que admiten BGP:
- **Calico**: BGP es una funcionalidad principal; admite peering con switches ToR y Route Reflector
- **Cilium**: Admite BGP (v1.10+), útil en entornos multi-cluster

CNI que no admiten BGP:
- **Flannel**: Red overlay sencilla, sin soporte de BGP
- **Weave Net**: Usa su propio protocolo de enrutamiento, sin soporte de BGP
- **AWS VPC CNI**: Usa enrutamiento nativo de VPC, sin soporte de BGP

</details>

### 8. ¿Qué tipo de tráfico NO está sujeto a Kubernetes Network Policy?

A. Tráfico de un Pod a otro Pod
B. Tráfico de un Pod a Internet externo
C. Tráfico localhost entre contenedores en el mismo Pod
D. Tráfico que llega al Pod desde fuentes externas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Tráfico localhost entre contenedores en el mismo Pod**

**Explicación:**
Network Policy controla el tráfico entre Pods. Los contenedores dentro del mismo Pod:
- Comparten el mismo espacio de nombres de red
- Se comunican mediante localhost (127.0.0.1)
- No están sujetos a Network Policy

Tráfico sujeto a Network Policy:
- Tráfico Ingress/Egress entre Pods
- Tráfico Egress desde un Pod hacia el exterior
- Tráfico Ingress desde el exterior hacia un Pod

</details>

### 9. ¿Cuál es la consideración más importante al elegir un CNI para clusters de Kubernetes a gran escala (más de 500 nodes)?

A. Si se proporciona un dashboard de UI
B. Escalabilidad del control plane y eficiencia de sincronización de datos
C. Diseño del logotipo y calidad de la documentación
D. Frecuencia de lanzamientos de nuevas versiones

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Escalabilidad del control plane y eficiencia de sincronización de datos**

**Explicación:**
Consideraciones al seleccionar un CNI para clusters grandes:

1. **Escalabilidad del Control Plane**:
   - Calico: El componente Typha reduce la carga del API server
   - Cilium: Sincronización eficiente con el modo Operator

2. **Sincronización de datos**:
   - Uso de recursos por agente de node
   - Tiempo de propagación de actualizaciones de políticas

3. **Rendimiento**:
   - Las soluciones basadas en eBPF escalan mejor que las basadas en iptables
   - Degradación del rendimiento a medida que aumenta la cantidad de reglas

</details>

### 10. ¿Cuál es la diferencia correcta entre Ingress y Service?

A. Ingress opera en L4, mientras que Service opera en L7
B. Ingress define reglas de enrutamiento HTTP/HTTPS, mientras que Service proporciona endpoints de red para un conjunto de Pods
C. Ingress solo admite comunicación interna del cluster, mientras que Service solo admite comunicación externa
D. Ingress solo admite TCP, mientras que Service solo admite UDP

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Ingress define reglas de enrutamiento HTTP/HTTPS, mientras que Service proporciona endpoints de red para un conjunto de Pods**

**Explicación:**
- **Service**: Proporciona endpoints de red estables para un conjunto de Pods (L4)
  - Tipos ClusterIP, NodePort, LoadBalancer
  - Admite protocolos TCP/UDP

- **Ingress**: Define reglas de enrutamiento de tráfico HTTP/HTTPS (L7)
  - Enrutamiento basado en host
  - Enrutamiento basado en ruta
  - Terminación de TLS
  - Ingress Controller proporciona la implementación real

Ingress finalmente reenvía el tráfico a los Services de backend.

</details>

---

## Recursos de aprendizaje adicionales

- [Kubernetes Networking Model](https://kubernetes.io/docs/concepts/cluster-administration/networking/)
- [CNI Specification](https://github.com/containernetworking/cni/blob/master/SPEC.md)
- [Network Policy Guide](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
