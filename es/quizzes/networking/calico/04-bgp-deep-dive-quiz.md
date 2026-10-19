# Cuestionario de inmersión profunda en BGP

> **Documento relacionado**: [Inmersión profunda en BGP](../../../networking/calico/04-bgp-deep-dive.md)
> **Última actualización**: 12 de septiembre de 2026

## Cuestionario

1. ¿Qué significan las siglas BGP?
   - A) Basic Gateway Protocol
   - B) Border Gateway Protocol
   - C) Bridge Gateway Protocol
   - D) Bandwidth Gateway Protocol

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Border Gateway Protocol**

**Explicación:**
BGP significa Border Gateway Protocol. Es el protocolo de enrutamiento que impulsa Internet y permite que los sistemas autónomos intercambien información de rutas. En Calico, BGP distribuye rutas de red de los Pods entre los nodos y, de manera opcional, hacia infraestructura de red externa.

</details>

2. ¿Cuál es la diferencia entre iBGP y eBGP?
   - A) iBGP es más rápido y eBGP es más seguro
   - B) iBGP se usa dentro del mismo AS y eBGP entre AS distintos
   - C) iBGP usa TCP y eBGP usa UDP
   - D) iBGP es para IPv4 y eBGP para IPv6

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) iBGP se usa dentro del mismo AS y eBGP entre AS distintos**

**Explicación:**
iBGP (Internal BGP) designa sesiones BGP entre routers del mismo Sistema Autónomo (AS). eBGP (External BGP) designa sesiones entre routers de Sistemas Autónomos distintos. En clústeres de Calico, los nodos suelen usar iBGP dentro del clúster (mismo AS) y pueden usar eBGP para establecer peering con infraestructura de red externa (otro AS).

</details>

3. ¿Qué rango está reservado para los ASN privados de 16 bits?
   - A) 1-64511
   - B) 64512-65534
   - C) 65535-65600
   - D) 100000-200000

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) 64512-65534**

**Explicación:**
Los rangos de ASN privados son 64512–65534 (16 bits) y 4200000000–4294967294 (32 bits). Identifican sistemas autónomos; no son direcciones IP inherentemente no enrutables. Antes de anunciar esas rutas a Internet global, elimina los ASN privados del atributo AS_PATH. El ASN predeterminado de Calico es 64512.

</details>

4. En una topología BGP de malla completa, ¿cuántas sesiones BGP se establecen en un clúster con N nodos?
   - A) N sesiones
   - B) N * 2 sesiones
   - C) N * (N-1) / 2 sesiones
   - D) N^2 sesiones

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) N * (N-1) / 2 sesiones**

**Explicación:**
En una topología de malla completa, cada nodo establece peering con todos los demás. El número de sesiones es N * (N-1) / 2, donde N es el número de nodos. Por ejemplo, un clúster de 10 nodos tendría 10 * 9 / 2 = 45 sesiones BGP. Por eso se recomiendan Route Reflectors para clústeres grandes.

</details>

5. ¿Cuál es la función principal de un Route Reflector BGP?
   - A) Cifrar el tráfico BGP
   - B) Reducir el número de sesiones BGP reflejando rutas a los clientes
   - C) Filtrar rutas maliciosas
   - D) Convertir iBGP en eBGP

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Reducir el número de sesiones BGP reflejando rutas a los clientes**

**Explicación:**
Un Route Reflector reduce el número de sesiones BGP necesarias en el clúster: recibe rutas de sus clientes y las refleja a otros clientes. En vez de las N*(N-1)/2 sesiones de una malla completa, los clientes solo necesitan establecer peering con uno o varios Route Reflectors. Esto permite escalar BGP en clústeres grandes.

</details>

6. ¿Para qué sirve el Cluster ID en una configuración de Route Reflector?
   - A) Identificar el clúster de Kubernetes
   - B) Evitar bucles de enrutamiento entre Route Reflectors
   - C) Asignar direcciones IP a los nodos
   - D) Cifrar las sesiones BGP

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Evitar bucles de enrutamiento entre Route Reflectors**

**Explicación:**
Un Route Reflector rechaza una ruta reflejada si su CLUSTER_LIST ya contiene el propio Cluster ID. Los RR redundantes que atienden a los mismos clientes pueden compartir un ID; define ID distintos de forma deliberada para los diferentes grupos de RR o niveles jerárquicos. Este ID no identifica el clúster de Kubernetes.

</details>

7. ¿Qué controla el campo nodeSelector de un recurso BGPPeer?
   - A) Qué Pods pueden usar BGP
   - B) Qué nodos deben establecer la sesión de peering BGP
   - C) Qué rutas se anuncian
   - D) Qué namespaces pueden usar el peer

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Qué nodos deben establecer la sesión de peering BGP**

**Explicación:**
El campo `nodeSelector` de un recurso BGPPeer especifica qué nodos deben establecer una sesión BGP con el peer definido. Esto resulta útil para el peering según el rack: solo los nodos de un rack concreto se conectan al switch ToR local, en vez de todos los nodos del clúster.

</details>

8. ¿Qué ajuste de BGPConfiguration deshabilita la malla automática entre nodos?
   - A) meshEnabled: false
   - B) nodeToNodeMeshEnabled: false
   - C) disableMesh: true
   - D) bgpMesh: disabled

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) nodeToNodeMeshEnabled: false**

**Explicación:**
Este ajuste deshabilita las sesiones automáticas de malla. Antes de deshabilitar la malla, establece y verifica las sesiones sustitutas de RR o de la estructura de red, las rutas recibidas y exportadas, los siguientes saltos y el tráfico representativo. Marcar un nodo como RR lo retira de inmediato de la malla automática; prepara los nodos adecuados antes de convertirlos.

</details>

9. ¿Qué tipos de IP de Service puede anunciar Calico mediante BGP?
   - A) Solo ClusterIPs
   - B) Solo IP de LoadBalancer
   - C) ClusterIPs, ExternalIPs e IP de LoadBalancer
   - D) Solo Services NodePort

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) ClusterIPs, ExternalIPs e IP de LoadBalancer**

**Explicación:**
Los campos son serviceClusterIPs, serviceExternalIPs y serviceLoadBalancerIPs. Anuncian direcciones existentes; la asignación, el estado de los endpoints y la ruta de retorno son requisitos independientes. El nombre de host de un balanceador de carga en la nube no es un prefijo BGP. Kubernetes marcó spec.externalIPs como obsoleto desde la versión 1.36, pero no lo eliminó.

</details>

10. ¿Para qué se usan las comunidades BGP en Calico?
    - A) Crear grupos de usuarios para controlar el acceso
    - B) Etiquetar rutas con metadatos para tomar decisiones de políticas
    - C) Cifrar rutas específicas
    - D) Comprimir tablas de enrutamiento

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Etiquetar rutas con metadatos para tomar decisiones de políticas**

**Explicación:**
Las comunidades etiquetan rutas para que los routers apliquen políticas. Una comunidad estándar contiene dos valores de 16 bits; una comunidad grande, tres valores de 32 bits. Nombres como high-priority o internal-only no hacen cumplir automáticamente esa política. prefixAdvertisements etiqueta rutas existentes que coinciden; no origina una ruta agregada.

</details>

11. ¿Qué método de autenticación puede proteger las sesiones BGP en Calico?
    - A) Certificados TLS
    - B) Autenticación MD5
    - C) Tokens OAuth
    - D) Kerberos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Autenticación MD5**

**Explicación:**
La opción de firma TCP MD5 autentica el tráfico BGP con un secreto compartido al que hace referencia BGPPeer. No cifra el tráfico ni demuestra que las rutas anunciadas por un peer autenticado sean legítimas. Configura por separado credenciales coincidentes y filtros de enrutamiento.

</details>

12. ¿Qué significa Graceful Restart en el contexto de BGP?
    - A) Un método para reiniciar BGP sin perder la configuración
    - B) Un mecanismo para conservar el estado de reenvío mientras se reinicia el daemon BGP
    - C) Una forma de añadir gradualmente peers BGP
    - D) Una técnica para retirar rutas lentamente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Un mecanismo para conservar el estado de reenvío mientras se reinicia el daemon BGP**

**Explicación:**
Los peers negocian la capacidad Graceful Restart y pueden conservar rutas durante un intervalo limitado mientras se reinicia un daemon BGP. Solo ayuda si la ruta de reenvío sigue funcionando; las rutas obsoletas que se conservan pueden enviar el tráfico a un agujero negro. No garantiza actualizaciones ininterrumpidas.

</details>

13. ¿Qué comando permite comprobar el estado de los protocolos BGP del daemon BIRD?
    - A) bird status
    - B) birdcl -s /var/run/calico/bird.ctl show protocols
    - C) bird show peers
    - D) birdctl status bgp

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) birdcl -s /var/run/calico/bird.ctl show protocols**

**Explicación:**
Ejecuta el comando dentro del contenedor calico-node previsto y usa explícitamente el socket de control IPv4. Enumera los protocolos, incluidos BGP, kernel y device; para consultar detalles, usa show protocols all con el nombre real de un protocolo. Para IPv6, usa birdcl6 y /var/run/calico/bird6.ctl. Una instalación con BGP deshabilitado quizá no tenga un daemon BIRD.

</details>

14. En una topología de centro de datos Spine-Leaf, ¿con qué dispositivos suelen establecer peering los nodos de Calico?
    - A) Todos los nodos establecen peering con todos los switches Spine
    - B) Los nodos establecen peering con sus switches ToR (Leaf) locales
    - C) Solo los nodos maestros establecen peering con la infraestructura de red
    - D) Los nodos establecen peering directamente entre sí y omiten los switches

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Los nodos establecen peering con sus switches ToR (Leaf) locales**

**Explicación:**
En una topología Spine-Leaf, los nodos de Calico suelen establecer peering con sus switches Top-of-Rack (ToR/Leaf) locales. Los switches Leaf establecen peering con los switches Spine. Este diseño respeta la jerarquía de la red del centro de datos y usa nodeSelector en los recursos BGPPeer para que cada nodo se conecte solo al ToR de su rack.

</details>

15. ¿Qué puede ocurrir mientras nodeToNodeMeshEnabled está en true y se introducen sesiones explícitas con Route Reflectors?
    - A) Los Route Reflectors tienen prioridad y deshabilitan la malla
    - B) Las sesiones de malla de los clientes que no son RR pueden coexistir con sesiones explícitas de RR durante la transición
    - C) Se produce un error de configuración y Calico no se inicia
    - D) Se ignoran los Route Reflectors

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Las sesiones de malla de los clientes que no son RR pueden coexistir con sesiones explícitas de RR durante la transición**

**Explicación:**
Los nodos RR quedan excluidos de la malla automática cuando se establece routeReflectorClusterID. Los clientes restantes que no son RR pueden mantener sus sesiones de malla mientras se preparan y prueban las sesiones explícitas de RR. Retira la malla solo después de verificar las sesiones sustitutas, las rutas, los siguientes saltos y el tráfico.

</details>

16. ¿Qué regla de importación solo coincide con la ruta predeterminada IPv4?
    - A) Aceptar con In 0.0.0.0/0
    - B) Aceptar con Equal 0.0.0.0/0
    - C) Rechazar con NotIn 0.0.0.0/0
    - D) Un filtro sin reglas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Aceptar con Equal 0.0.0.0/0**

**Explicación:**
Equal coincide con el prefijo /0 exacto. In /0 coincide con todas las rutas IPv4; NotIn /0 no coincide con ninguna. BGPFilter acepta de forma predeterminada las rutas que no coinciden, así que una lista permitida también necesita un Reject incondicional al final.

</details>

17. ¿Qué hace prefixAdvertisements para 10.244.0.0/16?
    - A) Siempre origina una nueva ruta /16
    - B) Reemplaza todas las rutas /26 por una /16
    - C) Añade comunidades a las rutas existentes que coinciden con ese rango
    - D) Asigna IP de Service

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Añade comunidades a las rutas existentes que coinciden con ese rango**

**Explicación:**
El renderizador actual de Calico añade comunidades a las rutas existentes que coinciden, incluidas las rutas de Pods. No origina el prefijo, no asigna direcciones ni agrega bloques. Un BGPFilter de exportación explícito con Accept anterior puede omitir ese etiquetado integrado; quizá se necesite una operación para las rutas aceptadas.

</details>


---

[Volver a los materiales de aprendizaje](../../../networking/calico/04-bgp-deep-dive.md) | [Cuestionario anterior: modos de red](./03-networking-modes-quiz.md) | [Cuestionario siguiente: política de red](./05-network-policy-quiz.md)
