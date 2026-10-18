# Cuestionario del glosario de Calico

> **Documento relacionado**: [Glosario de Calico](../../../networking/calico/glossary.md)
> **Última actualización**: 12 de septiembre de 2026

## Cuestionario

1. ¿Cuál es la función principal de Felix en la arquitectura de Calico?
   - A) Administrar la base de datos etcd
   - B) Programar reglas de políticas de red y rutas en cada nodo
   - C) Balancear el tráfico de los servicios
   - D) Proporcionar resolución DNS para los servicios

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Programar reglas de políticas de red y rutas en cada nodo**

**Explicación:** Felix programa en cada nodo el plano de datos de políticas seleccionado y las rutas pertinentes. El complemento CNI crea y configura las interfaces normales de los Pods e invoca IPAM; Felix mantiene el estado de los endpoints y programa reglas, pero no reenvía cada paquete en espacio de usuario.

</details>

2. ¿Qué significa BIRD y cuál es su función en Calico?
   - A) Binary Internet Routing Daemon: administra el DNS de los contenedores
   - B) BIRD Internet Routing Daemon: distribuye información de enrutamiento mediante BGP
   - C) Basic Internal Route Distribution: gestiona el descubrimiento de servicios
   - D) Broadcast IP Routing Distributor: administra el tráfico multicast

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) BIRD Internet Routing Daemon: distribuye información de enrutamiento mediante BGP**

**Explicación:** BIRD intercambia rutas mediante BGP en los perfiles de Calico que tienen BGP habilitado. El diseño de enrutamiento y encapsulación determina si el tráfico usa enrutamiento directo o un túnel; la presencia de BGP por sí sola no garantiza que no se use una red superpuesta (overlay).

</details>

3. ¿Qué función cumple Typha en las implementaciones de Calico?
   - A) Cifrar el tráfico entre Pods
   - B) Almacenar en caché y distribuir actualizaciones del almacén de datos a las instancias de Felix
   - C) Proporcionar balanceo de carga de entrada
   - D) Administrar la rotación de certificados

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Almacenar en caché y distribuir actualizaciones del almacén de datos a las instancias de Felix**

**Explicación:** Typha almacena en caché y distribuye los cambios del almacén de datos a Felix, con lo que reduce la carga de las suscripciones de observación de cada cliente. Puede tener varias réplicas y distintos tipos de sincronización/observación; no es un mecanismo único y universal de watch ni un servicio de federación de políticas. El operador escala Typha según el perfil instalado.

</details>

4. ¿Cuál es la diferencia entre IPPool e IPAM en Calico?
   - A) Son lo mismo con nombres distintos
   - B) IPPool define los rangos CIDR disponibles; IPAM administra la asignación desde esos rangos
   - C) IPPool es para IPv4 e IPAM para IPv6
   - D) IPPool está obsoleto y ha sido reemplazado por IPAM

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) IPPool define los rangos CIDR disponibles; IPAM administra la asignación desde esos rangos**

**Explicación:** IPPool define un rango de direcciones y también parámetros de encapsulación, NAT y elegibilidad para la asignación. Calico IPAM asigna direcciones desde los pools elegibles para los usos compatibles. No es el asignador que usa VPC CNI en modo solo de políticas, y un IPPool no es un alias del PodCIDR de un nodo de Kubernetes.

</details>

5. ¿En qué se diferencia GlobalNetworkPolicy de Kubernetes NetworkPolicy?
   - A) GlobalNetworkPolicy solo funciona con IPv6
   - B) GlobalNetworkPolicy tiene alcance de clúster y admite funciones adicionales, como tiers y reglas de denegación
   - C) GlobalNetworkPolicy tiene alcance de espacio de nombres, igual que Kubernetes NetworkPolicy
   - D) GlobalNetworkPolicy está obsoleto

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) GlobalNetworkPolicy tiene alcance de clúster y admite funciones adicionales, como tiers y reglas de denegación**

**Explicación:** GlobalNetworkPolicy tiene alcance de clúster, y sus selectores determinan a qué cargas de trabajo o endpoints de host afecta. Añade acciones, orden y tiers de Calico; no afecta automáticamente a todos los Pods ni habilita inspección L7 sin la integración necesaria.

</details>

6. ¿Qué es un Tier en el modelo de políticas de Calico?
   - A) Un segmento de red para aislar el tráfico
   - B) Una agrupación jerárquica que controla el orden de evaluación de las políticas
   - C) Un nivel de precios de Calico Enterprise
   - D) Un tipo de cifrado de red

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Una agrupación jerárquica que controla el orden de evaluación de las políticas**

**Explicación:** Los tiers agrupan las políticas por prioridad. Primero se evalúa el tier con el valor numérico de orden más bajo y, dentro de ese tier, se usa el orden de las políticas. Allow/Deny termina la evaluación; Pass delega en el siguiente tier aplicable y, finalmente, en los perfiles. Los nombres de ejemplo security/platform/application los define el usuario; no son una jerarquía predeterminada obligatoria.

</details>

7. ¿Qué representa un WorkloadEndpoint en Calico?
   - A) Un endpoint de un Service de Kubernetes
   - B) Una interfaz de red asociada a un Pod o a una carga de trabajo de VM
   - C) Un endpoint de una API externa
   - D) Un punto de montaje de almacenamiento

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Una interfaz de red asociada a un Pod o a una carga de trabajo de VM**

**Explicación:** WorkloadEndpoint representa una interfaz de carga de trabajo con información de IP/MAC/interfaz, etiquetas y referencias a perfiles que se usan para calcular la política. Normalmente, el complemento o el orquestador administra su ciclo de vida. No es un EndpointSlice de un Service ni una lista almacenada de todas las decisiones de política efectivas.

</details>

8. ¿Qué relación hay entre BGPPeer y BGPConfiguration en Calico?
   - A) Son alias del mismo recurso
   - B) BGPConfiguration establece los ajustes globales de BGP; BGPPeer define sesiones de peering específicas
   - C) BGPPeer es para peers internos y BGPConfiguration para externos
   - D) BGPConfiguration está obsoleto y ha sido reemplazado por BGPPeer

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) BGPConfiguration establece los ajustes globales de BGP; BGPPeer define sesiones de peering específicas**

**Explicación:** La configuración predeterminada de BGPConfiguration define valores del clúster, como el ASN y los ajustes de malla y anuncio de servicios; las anulaciones compatibles por nodo se configuran por separado. BGPPeer identifica las relaciones de peering previstas mediante una dirección del peer o selectores. Esto no garantiza que la sesión ni las rutas necesarias estén establecidas.

</details>

9. ¿Qué es un NetworkSet en Calico y cuál es su equivalente en Cilium?
   - A) Un grupo de Services, equivalente a Cilium ServiceGroup
   - B) Un conjunto etiquetado de IP/CIDR; CiliumCIDRGroup, referenciado desde políticas CIDR, es un concepto relacionado
   - C) Una colección de espacios de nombres, equivalente a Cilium ClusterPolicy
   - D) Una configuración de zona DNS, equivalente a Cilium DNSPolicy

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Un conjunto etiquetado de IP/CIDR; CiliumCIDRGroup, referenciado desde políticas CIDR, es un concepto relacionado**

**Explicación:** NetworkSet tiene alcance de espacio de nombres, mientras que GlobalNetworkSet tiene alcance de clúster; ambos proporcionan conjuntos etiquetados de IP/CIDR. CiliumCIDRGroup tiene alcance de clúster y se puede referenciar mediante cidrGroupRef o cidrGroupSelector en reglas CIDR de Cilium. Son conceptos relacionados con API distintas, no reglas DNS ni manifiestos intercambiables.

</details>

10. ¿Para qué sirve un HostEndpoint en Calico?
    - A) Definir endpoints de contenedores
    - B) Aplicar políticas de red a interfaces del host (tráfico que no es de Pods)
    - C) Configurar DNS para el host
    - D) Administrar etiquetas de nodos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Aplicar políticas de red a interfaces del host (tráfico que no es de Pods)**

**Explicación:** HostEndpoint representa una interfaz del host para aplicar políticas al tráfico del host y, si se configura, al tráfico reenviado. Antes de crearlo o aplicar las políticas, revisa los perfiles, las reglas de seguridad de emergencia (failsafes) y las rutas de administración. Los ámbitos de las políticas de cargas de trabajo y del host son distintos, aunque el tráfico reenviado de los Pods también puede verse afectado.

</details>
