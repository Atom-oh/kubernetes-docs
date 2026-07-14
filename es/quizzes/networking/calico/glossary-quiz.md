# Cuestionario del glosario de Calico

> **Documento relacionado**: [Calico Glossary](../../../networking/calico/glossary.md)
> **Última actualización**: February 22, 2026

## Cuestionario

1. ¿Cuál es la función principal de Felix en la arquitectura de Calico?
   - A) Administrar la base de datos etcd
   - B) Programar reglas y rutas de network policy en cada nodo
   - C) Realizar balanceo de carga del tráfico de Service
   - D) Proporcionar resolución DNS para Services

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Programar reglas y rutas de network policy en cada nodo**

**Explicación:**
Felix es el agente por nodo de Calico (se ejecuta como un DaemonSet), responsable de programar reglas de network policy (iptables o eBPF), rutas y ACL en cada nodo. Supervisa el datastore para detectar actualizaciones de políticas y endpoints, y las traduce en reglas a nivel de kernel.

</details>

2. ¿Qué significa BIRD y cuál es su función en Calico?
   - A) Binary Internet Routing Daemon - administra el DNS de contenedores
   - B) BIRD Internet Routing Daemon - distribuye información de enrutamiento mediante BGP
   - C) Basic Internal Route Distribution - gestiona el descubrimiento de Service
   - D) Broadcast IP Routing Distributor - administra el tráfico multicast

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) BIRD Internet Routing Daemon - distribuye información de enrutamiento mediante BGP**

**Explicación:**
BIRD (BIRD Internet Routing Daemon - un acrónimo recursivo) es el daemon BGP que Calico utiliza para distribuir información de enrutamiento entre nodos. Establece sesiones de peering BGP y anuncia rutas CIDR de pod, lo que permite la comunicación directa de pod a pod sin encapsulación overlay.

</details>

3. ¿Cuál es la función de Typha en las implementaciones de Calico?
   - A) Cifrar el tráfico de pod a pod
   - B) Almacenar en caché y distribuir las actualizaciones del datastore a las instancias de Felix
   - C) Proporcionar balanceo de carga de ingress
   - D) Administrar la rotación de certificados

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Almacenar en caché y distribuir las actualizaciones del datastore a las instancias de Felix**

**Explicación:**
Typha actúa como un proxy de caché entre las instancias de Felix y el datastore (Kubernetes API o etcd). Reduce la carga del datastore al agregar las observaciones de varias instancias de Felix en una única observación y, posteriormente, distribuir las actualizaciones a todos los daemons Felix conectados.

</details>

4. ¿Cuál es la diferencia entre un IPPool e IPAM en Calico?
   - A) Son lo mismo con nombres diferentes
   - B) IPPool define los rangos CIDR disponibles; IPAM administra la asignación desde esos rangos
   - C) IPPool es para IPv4 e IPAM para IPv6
   - D) IPPool está obsoleto en favor de IPAM

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) IPPool define los rangos CIDR disponibles; IPAM administra la asignación desde esos rangos**

**Explicación:**
Un IPPool es un recurso de Calico que define un rango de direcciones IP (CIDR) disponible para la asignación de pod, junto con configuraciones como los ajustes de NAT y encapsulación. IPAM (IP Address Management) es el sistema que administra la asignación real de IP individuales desde estos pools a pods y nodos.

</details>

5. ¿En qué se diferencia GlobalNetworkPolicy de Kubernetes NetworkPolicy?
   - A) GlobalNetworkPolicy solo funciona con IPv6
   - B) GlobalNetworkPolicy tiene alcance de clúster y admite funciones adicionales como tiers y reglas deny
   - C) GlobalNetworkPolicy tiene alcance de namespace como Kubernetes NetworkPolicy
   - D) GlobalNetworkPolicy está obsoleto

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) GlobalNetworkPolicy tiene alcance de clúster y admite funciones adicionales como tiers y reglas deny**

**Explicación:**
GlobalNetworkPolicy es un recurso específico de Calico que se aplica a todo el clúster sin restricciones de namespace. A diferencia de Kubernetes NetworkPolicy, admite reglas deny explícitas, tiers de políticas para el ordenamiento, reglas de capa de aplicación (L7) y selectores para recursos sin namespace, como HostEndpoints.

</details>

6. ¿Qué es un Tier en el modelo de políticas de Calico?
   - A) Un segmento de red para aislar tráfico
   - B) Una agrupación jerárquica que controla el orden de evaluación de políticas
   - C) Un nivel de precios para Calico Enterprise
   - D) Un tipo de cifrado de red

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Una agrupación jerárquica que controla el orden de evaluación de políticas**

**Explicación:**
Los tiers proporcionan una forma de organizar y ordenar las políticas de red de Calico. Las políticas en tiers de mayor orden se evalúan antes que las de tiers de menor orden. Esto permite patrones como las políticas de seguridad a nivel de plataforma que tienen precedencia sobre las políticas de los equipos de aplicaciones, lo que admite la administración de políticas multi-tenant.

</details>

7. ¿Qué representa un WorkloadEndpoint en Calico?
   - A) Un endpoint de Kubernetes Service
   - B) Una interfaz de red asociada con una carga de trabajo de pod o VM
   - C) Un endpoint de API externo
   - D) Un punto de montaje de almacenamiento

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Una interfaz de red asociada con una carga de trabajo de pod o VM**

**Explicación:**
Un WorkloadEndpoint representa una interfaz de red conectada a una carga de trabajo (pod, VM o contenedor). Contiene información sobre las direcciones IP de la interfaz, el host donde se ejecuta, las etiquetas para la selección de políticas y el perfil o las políticas aplicadas. Calico crea automáticamente WorkloadEndpoints para los pods.

</details>

8. ¿Cuál es la relación entre BGPPeer y BGPConfiguration en Calico?
   - A) Son alias del mismo recurso
   - B) BGPConfiguration establece la configuración BGP global; BGPPeer define sesiones de peering específicas
   - C) BGPPeer es para peers internos y BGPConfiguration para externos
   - D) BGPConfiguration está obsoleto en favor de BGPPeer

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) BGPConfiguration establece la configuración BGP global; BGPPeer define sesiones de peering específicas**

**Explicación:**
BGPConfiguration es un recurso global que define configuraciones BGP para todo el clúster, como el número AS, la habilitación de la malla de nodo a nodo y el logging. Los recursos BGPPeer definen relaciones específicas de peering BGP con routers externos o route reflectors, incluidas sus direcciones IP, números AS y selectores de nodo.

</details>

9. ¿Qué es un NetworkSet en Calico y cuál es su equivalente en Cilium?
   - A) Un grupo de Services; equivalente a Cilium ServiceGroup
   - B) Un conjunto con nombre de direcciones IP/CIDR para usar en políticas; similar a Cilium CiliumNetworkPolicy con reglas CIDR
   - C) Una colección de namespaces; equivalente a Cilium ClusterPolicy
   - D) Una configuración de zona DNS; equivalente a Cilium DNSPolicy

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Un conjunto con nombre de direcciones IP/CIDR para usar en políticas; similar a Cilium CiliumNetworkPolicy con reglas CIDR**

**Explicación:**
Un NetworkSet es un recurso de Calico que define una colección con nombre de direcciones IP, CIDR o dominios que se puede referenciar en políticas de red. Esto simplifica la administración de políticas cuando el mismo conjunto de IP externas aparece en varias políticas. Cilium logra una funcionalidad similar mediante reglas basadas en CIDR en CiliumNetworkPolicy.

</details>

10. ¿Cuál es el propósito de un HostEndpoint en Calico?
    - A) Definir endpoints de contenedor
    - B) Aplicar políticas de red a interfaces de host (tráfico que no es de pod)
    - C) Configurar DNS para el host
    - D) Administrar etiquetas de nodo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Aplicar políticas de red a interfaces de host (tráfico que no es de pod)**

**Explicación:**
Un HostEndpoint representa una interfaz de red en un nodo host (no un pod). Permite que las políticas de red de Calico controlen el tráfico hacia y desde procesos del host, lo que protege Services a nivel de nodo como kubelet, SSH u otros daemons del sistema que no se ejecutan como pods.

</details>
