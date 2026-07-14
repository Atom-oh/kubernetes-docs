# Cuestionario de inmersión profunda en BGP

> **Documento relacionado**: [Inmersión profunda en BGP](../../../networking/calico/04-bgp-deep-dive.md)
> **Última actualización**: February 22, 2026

## Cuestionario

1. ¿Qué significa BGP?
   - A) Basic Gateway Protocol
   - B) Border Gateway Protocol
   - C) Bridge Gateway Protocol
   - D) Bandwidth Gateway Protocol

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Border Gateway Protocol**

**Explicación:**
BGP significa Border Gateway Protocol. Es el protocolo de enrutamiento que impulsa Internet y permite que los sistemas autónomos intercambien información de enrutamiento. En Calico, BGP se usa para distribuir rutas de red de Pod entre Nodes y, opcionalmente, hacia infraestructura de red externa.

</details>

2. ¿Cuál es la diferencia entre iBGP y eBGP?
   - A) iBGP es más rápido, eBGP es más seguro
   - B) iBGP está dentro del mismo AS, eBGP está entre AS diferentes
   - C) iBGP usa TCP, eBGP usa UDP
   - D) iBGP es para IPv4, eBGP es para IPv6

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) iBGP está dentro del mismo AS, eBGP está entre AS diferentes**

**Explicación:**
iBGP (Internal BGP) se refiere a sesiones BGP entre routers dentro del mismo Autonomous System (AS). eBGP (External BGP) se refiere a sesiones BGP entre routers en Autonomous Systems diferentes. En los clústeres de Calico, los Nodes normalmente usan iBGP dentro del clúster (el mismo AS) y pueden usar eBGP para establecer peering con infraestructura de red externa (AS diferente).

</details>

3. ¿Cuál es el rango de números AS privados que se puede usar para clústeres de Calico?
   - A) 1-64511
   - B) 64512-65534
   - C) 65535-65600
   - D) 100000-200000

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) 64512-65534**

**Explicación:**
El rango de números AS privados es 64512-65534 (para ASN de 16 bits) y 4200000000-4294967294 (para ASN de 32 bits). Estos rangos están designados para uso privado y no se pueden enrutar globalmente, de forma similar a los rangos de direcciones IP privadas. Los clústeres de Calico usan comúnmente números AS en el rango 64512-65534.

</details>

4. En una topología BGP full-mesh, ¿cuántas sesiones BGP se establecen en un clúster con N Nodes?
   - A) N sesiones
   - B) N * 2 sesiones
   - C) N * (N-1) / 2 sesiones
   - D) N^2 sesiones

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) N * (N-1) / 2 sesiones**

**Explicación:**
En una topología BGP full-mesh, cada Node establece peering con todos los demás Nodes. El número de sesiones se calcula como N * (N-1) / 2, donde N es el número de Nodes. Por ejemplo, un clúster de 10 Nodes tendría 10 * 9 / 2 = 45 sesiones BGP. Por esta razón, se recomiendan Route Reflectors para clústeres más grandes.

</details>

5. ¿Cuál es la función principal de un BGP Route Reflector?
   - A) Cifrar el tráfico BGP
   - B) Reducir el número de sesiones BGP reflejando rutas a los clientes
   - C) Filtrar rutas maliciosas
   - D) Convertir iBGP en eBGP

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Reducir el número de sesiones BGP reflejando rutas a los clientes**

**Explicación:**
Un Route Reflector reduce el número de sesiones BGP necesarias en un clúster al recibir rutas de los clientes y "reflejarlas" a otros clientes. En lugar de N*(N-1)/2 sesiones en una full mesh, los clientes solo necesitan establecer peering con el Route Reflector o los Route Reflectors. Esto es esencial para escalar BGP en clústeres grandes.

</details>

6. ¿Cuál es el propósito del Cluster ID en una configuración de Route Reflector?
   - A) Identificar el clúster de Kubernetes
   - B) Evitar bucles de enrutamiento entre Route Reflectors
   - C) Asignar direcciones IP a los Nodes
   - D) Cifrar sesiones BGP

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Evitar bucles de enrutamiento entre Route Reflectors**

**Explicación:**
El Cluster ID se usa para evitar bucles de enrutamiento cuando se implementan varios Route Reflectors. Cuando un Route Reflector recibe una ruta con su propio Cluster ID, sabe que la ruta ya pasó por este clúster de RR y la descarta. Todos los Route Reflectors del mismo clúster deben compartir el mismo Cluster ID.

</details>

7. ¿Qué controla el campo nodeSelector en un recurso BGPPeer?
   - A) Qué Pods pueden usar BGP
   - B) Qué Nodes deben establecer el peering BGP
   - C) Qué rutas se anuncian
   - D) Qué namespaces pueden usar el peer

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Qué Nodes deben establecer el peering BGP**

**Explicación:**
El campo `nodeSelector` en un recurso BGPPeer especifica qué Nodes deben establecer una sesión BGP con el peer definido. Esto es útil para peering consciente del rack, donde solo los Nodes de un rack específico deben establecer peering con el switch ToR (Top of Rack) local, en lugar de todos los Nodes del clúster.

</details>

8. ¿Qué configuración de BGPConfiguration deshabilita la malla automática de Node a Node?
   - A) meshEnabled: false
   - B) nodeToNodeMeshEnabled: false
   - C) disableMesh: true
   - D) bgpMesh: disabled

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) nodeToNodeMeshEnabled: false**

**Explicación:**
Establecer `nodeToNodeMeshEnabled: false` en el recurso BGPConfiguration deshabilita el peering BGP full-mesh automático entre todos los Nodes. Esto debe hacerse al usar Route Reflectors o peering BGP externo, ya que la full mesh se vuelve innecesaria y genera sobrecarga en implementaciones más grandes.

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
Calico puede anunciar varios tipos de IP de Service mediante BGP: ClusterIPs (IP de Service internas), ExternalIPs (IP externas asignadas a Services) e IP de LoadBalancer. Esto se configura en el recurso BGPConfiguration mediante los campos `serviceClusterIPs`, `serviceExternalIPs` y `serviceLoadBalancerIPs`, respectivamente.

</details>

10. ¿Cuál es el propósito de las comunidades BGP en Calico?
    - A) Crear grupos de usuarios para control de acceso
    - B) Etiquetar rutas con metadatos para decisiones de políticas
    - C) Cifrar rutas específicas
    - D) Comprimir tablas de enrutamiento

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Etiquetar rutas con metadatos para decisiones de políticas**

**Explicación:**
Las comunidades BGP son etiquetas adjuntas a las rutas que los routers pueden usar para tomar decisiones de políticas. En Calico, puedes configurar etiquetas de comunidad para prefijos anunciados, lo que permite que los routers posteriores apliquen políticas específicas (como ingeniería de tráfico o filtrado) según estas etiquetas. Las comunidades se expresan como pares AS:valor (por ejemplo, 64512:100).

</details>

11. ¿Qué método de autenticación se puede usar para proteger sesiones BGP en Calico?
    - A) Certificados TLS
    - B) Autenticación MD5
    - C) Tokens OAuth
    - D) Kerberos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Autenticación MD5**

**Explicación:**
Calico admite autenticación MD5 para proteger sesiones BGP. Es una opción de firma TCP MD5 que autentica mensajes BGP entre peers. Aunque no proporciona cifrado, evita que dispositivos no autorizados establezcan sesiones BGP con tus Nodes. La contraseña se configura en el recurso BGPPeer.

</details>

12. ¿Qué es Graceful Restart en el contexto de BGP?
    - A) Un método para reiniciar BGP sin perder la configuración
    - B) Un mecanismo para preservar el estado de reenvío durante el reinicio del daemon BGP
    - C) Una forma de agregar gradualmente nuevos peers BGP
    - D) Una técnica para retirar rutas lentamente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Un mecanismo para preservar el estado de reenvío durante el reinicio del daemon BGP**

**Explicación:**
Graceful Restart es una capacidad de BGP que permite que el plano de reenvío siga funcionando durante el reinicio de un daemon BGP. El router que se reinicia informa a sus peers que se está reiniciando, y los peers conservan las rutas de ese router durante un período de gracia. Esto evita la interrupción del tráfico durante actualizaciones de software o fallas breves.

</details>

13. ¿Qué comando se usa para comprobar el estado del protocolo BGP en el daemon BIRD?
    - A) bird status
    - B) birdcl show protocols
    - C) bird show peers
    - D) birdctl status bgp

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) birdcl show protocols**

**Explicación:**
El comando `birdcl show protocols` muestra el estado de todos los protocolos BGP en el daemon BIRD. Muestra si las sesiones BGP están establecidas, el estado del peer y estadísticas de intercambio de rutas. Otros comandos útiles incluyen `birdcl show route` para mostrar la tabla de enrutamiento y `birdcl show protocols all <name>` para obtener información detallada de la sesión.

</details>

14. En una topología de centro de datos Spine-Leaf, ¿con quiénes deben establecer peering normalmente los Nodes de Calico?
    - A) Todos los Nodes establecen peering con todos los switches Spine
    - B) Los Nodes establecen peering con sus switches ToR (Leaf) locales
    - C) Solo los Nodes maestros establecen peering con la infraestructura de red
    - D) Los Nodes establecen peering directamente entre sí, omitiendo los switches

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Los Nodes establecen peering con sus switches ToR (Leaf) locales**

**Explicación:**
En una topología Spine-Leaf, los Nodes de Calico normalmente establecen peering con sus switches Top-of-Rack (ToR/Leaf) locales. Los switches Leaf luego establecen peering con los switches Spine. Esto sigue el diseño jerárquico de la red del centro de datos y usa nodeSelector en los recursos BGPPeer para garantizar que los Nodes solo establezcan peering con el switch ToR de su rack.

</details>

15. ¿Qué ocurre cuando nodeToNodeMeshEnabled es true y también configuras Route Reflectors?
    - A) Los Route Reflectors tienen prioridad; la malla se deshabilita
    - B) Se establecen tanto la malla como las sesiones de Route Reflector (subóptimo)
    - C) Error de configuración; Calico no se inicia
    - D) Los Route Reflectors se ignoran

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Se establecen tanto la malla como las sesiones de Route Reflector (subóptimo)**

**Explicación:**
Si nodeToNodeMeshEnabled permanece en true mientras se configuran Route Reflectors, se establecerán tanto las sesiones full mesh como las sesiones de Route Reflector. Esto es subóptimo y desperdicia recursos. Al usar Route Reflectors, debes establecer `nodeToNodeMeshEnabled: false` para deshabilitar la malla automática y depender únicamente de los Route Reflectors para la distribución de rutas.

</details>

---

[Volver a los materiales de aprendizaje](../../../networking/calico/04-bgp-deep-dive.md) | [Cuestionario anterior: Modos de red](./03-networking-modes-quiz.md) | [Siguiente cuestionario: Política de red](./05-network-policy-quiz.md)
