# Cuestionario de Fundamentos de Redes, parte 5: dispositivos de red, LAN y WAN

> **Última actualización**: 19 de noviembre de 2026

Evalúa tu comprensión de las decisiones de reenvío de los dispositivos, las VLAN y la redundancia, las topologías LAN, NAT, los tipos de WAN y sus equivalentes en la nube.

## Preguntas de opción múltiple

1. ¿Qué afirmación describe correctamente la decisión que toma un switch L2 dentro de una VLAN y la que toma un router entre subredes?
   - A) Ambos buscan la ruta de prefijo más largo para la IP de destino
   - B) El switch busca la MAC de destino en su tabla MAC para elegir un puerto; el router busca la IP de destino en su FIB, decrementa el TTL en 1 y escribe una nueva cabecera L2
   - C) El switch decrementa el TTL y el router aprende las MAC de origen
   - D) El router siempre sustituye las direcciones IP por la suya

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El switch busca la MAC de destino en su tabla MAC para elegir un puerto; el router busca la IP de destino en su FIB, decrementa el TTL en 1 y escribe una nueva cabecera L2**

**Explicación:**
Un switch L2 aprende las MAC de origen, elige un puerto según la MAC de destino y la VLAN, y no modifica la trama. Un router reenvía el paquete al siguiente salto de la ruta de prefijo más largo, decrementa el TTL y escribe nuevas MAC de origen y de destino. Sin NAT, las direcciones IP no cambian, así que D es incorrecta.

</details>

2. Dos switches están conectados mediante un troncal 802.1Q; ambos tienen puertos en las VLAN 10 y 20, y un router enruta entre las dos VLAN. ¿Cuántos dominios de difusión hay?
   - A) 1
   - B) 2
   - C) 4
   - D) Uno por puerto del switch

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) 2**

**Explicación:**
Una VLAN es un dominio de difusión, y una VLAN que abarca varios switches conectados mediante troncales sigue siendo un único dominio de difusión. El router no reenvía a otras interfaces un paquete recibido como difusión L2 (RFC 1812 §5.3.4), así que hay dos: VLAN 10 y VLAN 20. Uno por puerto del switch describe los dominios de colisión.

</details>

3. ¿Qué afirmación sobre la VLAN nativa en un troncal 802.1Q es correcta?
   - A) Las tramas de la VLAN nativa siempre llevan una etiqueta VID 4095
   - B) La VLAN nativa puede ser diferente en cada extremo sin que haya ningún problema
   - C) Es la VLAN que atraviesa el troncal sin etiquetar; en Cisco Catalyst el valor predeterminado es VLAN 1 y ambos extremos deben coincidir
   - D) La VLAN nativa solo se aplica a los puertos de acceso

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Es la VLAN que atraviesa el troncal sin etiquetar; en Cisco Catalyst el valor predeterminado es VLAN 1 y ambos extremos deben coincidir**

**Explicación:**
El dispositivo asigna a la VLAN nativa las tramas sin etiquetar que recibe en un troncal, y envía sin etiquetar las tramas de la VLAN nativa. Si los extremos no coinciden, las tramas de una VLAN pasan a otra, lo que rompe la separación y puede provocar bucles de spanning tree. Los VID 0 y 4095 están reservados y no se usan para las VLAN.

</details>

4. ¿Cuál es la razón fundamental por la que se necesita STP y cómo se elige el puente raíz?
   - A) Las cabeceras Ethernet no tienen TTL, así que las tramas en un bucle L2 nunca desaparecen; STP bloquea algunos puertos y el switch con el ID de puente más bajo (prioridad + MAC) se convierte en la raíz
   - B) Para aumentar el TTL de IP; el switch con más puertos se convierte en la raíz
   - C) Para combinar el ancho de banda de los enlaces; el switch con la MAC más alta se convierte en la raíz
   - D) Para enrutar entre VLAN; el switch con el valor de prioridad más alto se convierte en la raíz

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Las cabeceras Ethernet no tienen TTL, así que las tramas en un bucle L2 nunca desaparecen; STP bloquea algunos puertos y el switch con el ID de puente más bajo (prioridad + MAC) se convierte en la raíz**

**Explicación:**
Cuando hay un bucle, las difusiones siguen circulando y multiplicándose, y las tablas MAC fluctúan. STP bloquea algunos enlaces redundantes para formar un árbol. La prioridad predeterminada es 32768, así que, si no se configura nada, el switch con la MAC más baja se convierte en la raíz; en la práctica, se reduce la prioridad en los switches centrales o de distribución para fijar la raíz. Combinar el ancho de banda es tarea de LACP.

</details>

5. En un LAG que agrupa cuatro enlaces de 10 Gbps con LACP, ¿cuál es el rendimiento máximo de una única conexión TCP?
   - A) 40 Gbps: un LAG distribuye los paquetes uniformemente entre todos los enlaces
   - B) Hasta 10 Gbps: el hash mantiene un flujo en el mismo enlace miembro
   - C) 20 Gbps: la transmisión y la recepción utilizan enlaces distintos
   - D) 10 Gbps independientemente del LAG, porque STP bloquea tres enlaces

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Hasta 10 Gbps: el hash mantiene un flujo en el mismo enlace miembro**

**Explicación:**
La agregación de enlaces calcula un hash de valores como las direcciones y los puertos para asignar las tramas a un enlace miembro, por lo que un flujo permanece en un solo enlace. Los 40 Gbps agregados solo se aprovechan cuando hay muchos flujos. STP considera el LAG como un único enlace y no bloquea sus miembros.

</details>

6. En VRRPv3, un router de respaldo tiene una prioridad de 100 y el intervalo de anuncio predeterminado de 1 s. Aproximadamente, ¿cuánto tarda el router de respaldo en asumir el control después de que el router activo deja de funcionar?
   - A) Unos 1 s
   - B) Unos 3,61 s
   - C) Unos 10 s
   - D) Unos 30 s

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Unos 3,61 s**

**Explicación:**
`Active_Down_Interval = 3 × intervalo de anuncio + Skew_Time`, con `Skew_Time = ((256 − prioridad) × intervalo de anuncio) / 256`. (256 − 100) / 256 ≈ 0,61 s, así que 3 + 0,61 ≈ 3,61 s. 10 s es el tiempo de espera predeterminado de HSRP y 30 s es el tiempo de escucha más el de aprendizaje de 802.1D STP.

</details>

7. Miles de Pods llaman a la misma API externa (una IP:443) a través de una única puerta de enlace NAT de AWS con una sola dirección IPv4 pública, y las conexiones nuevas empiezan a fallar. ¿Cuál es la causa más probable y qué se debería hacer?
   - A) Ampliar el grupo de seguridad de la puerta de enlace NAT
   - B) Es posible que se haya alcanzado el límite de 55.000 conexiones simultáneas por IP pública y destino único; revisar `ErrorPortAllocation` y considerar la reutilización de conexiones, las IP secundarias y la distribución de la carga entre puertas de enlace NAT
   - C) Las puertas de enlace NAT no tienen límite de conexiones, así que la API externa debe estar fallando
   - D) Denegar el puerto 443 en la NACL

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Es posible que se haya alcanzado el límite de 55.000 conexiones simultáneas por IP pública y destino único; revisar `ErrorPortAllocation` y considerar la reutilización de conexiones, las IP secundarias y la distribución de la carga entre puertas de enlace NAT**

**Explicación:**
Un destino único es una combinación de IP, puerto y protocolo de destino, así que el tráfico concentrado en una sola API alcanza primero el límite. Se pueden asociar hasta 8 direcciones IPv4, y `ErrorPortAllocation` aumenta por encima de cero cuando no se puede asignar un puerto de origen. No se puede asociar un grupo de seguridad a una puerta de enlace NAT, así que A es incorrecta.

</details>

8. ¿Qué rango de direcciones se asigna al segmento entre el CGNAT de un operador y el equipo en las instalaciones del cliente (CPE), y qué tipo de rango es?
   - A) `172.16.0.0/12`: espacio privado RFC 1918
   - B) `169.254.0.0/16`: espacio de enlace local
   - C) `100.64.0.0/10`: espacio de direcciones compartidas de RFC 6598, separado de RFC 1918
   - D) `203.0.113.0/24`: rango público reservado para CGNAT

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) `100.64.0.0/10`: espacio de direcciones compartidas de RFC 6598, separado de RFC 1918**

**Explicación:**
RFC 6598 asignó `100.64.0.0/10` a las implementaciones de CGN para evitar conflictos con el rango RFC 1918 que el abonado utilice dentro de su red. Los paquetes y las rutas de este rango no deben atravesar los límites entre proveedores. `203.0.113.0/24` es un rango de documentación de RFC 5737.

</details>

9. Una instancia llama a una API HTTPS externa. Su grupo de seguridad permite el tráfico saliente al puerto 443; la NACL personalizada de la subred solo permite el tráfico saliente al puerto 443 y, de forma predeterminada, deniega todo el tráfico entrante. ¿Por qué no llega la respuesta?
   - A) Los grupos de seguridad no tienen estado, así que hay que permitir por separado el tráfico entrante al puerto 443
   - B) Las NACL no tienen estado, así que hay que permitir el tráfico entrante a los puertos efímeros a los que vuelve la respuesta (por ejemplo, 32768–61000 en Linux)
   - C) Las NACL evalúan todas las reglas y después solo aplican las reglas de permiso
   - D) Las reglas de denegación tienen prioridad en los grupos de seguridad

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Las NACL no tienen estado, así que hay que permitir el tráfico entrante a los puertos efímeros a los que vuelve la respuesta (por ejemplo, 32768–61000 en Linux)**

**Explicación:**
Los grupos de seguridad tienen estado, permiten automáticamente el tráfico de respuesta y solo tienen reglas de permiso. Una NACL es un filtro de subred sin estado que evalúa las reglas de permiso y denegación en orden ascendente según su número, aplica la primera coincidencia y requiere que se permita explícitamente el tráfico de respuesta.

</details>

10. En una estructura spine-leaf de dos niveles, en la que cada leaf se conecta a cada spine y los leaf no están conectados entre sí, ¿qué recorrido entre switches sigue el tráfico entre dos servidores conectados a leaf distintos?
    - A) leaf → leaf
    - B) leaf → spine → leaf (tres switches, dos enlaces entre switches)
    - C) leaf → spine → spine → leaf
    - D) Depende de dónde estén conectados los servidores y es impredecible

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) leaf → spine → leaf (tres switches, dos enlaces entre switches)**

**Explicación:**
Como los leaf no están conectados entre sí y los spine tampoco, el tráfico dirigido a otro leaf siempre atraviesa exactamente un spine. Todos los pares de servidores están a la misma distancia, por lo que la latencia es predecible y ECMP utiliza todas las rutas a través de los spine a la vez.

</details>

11. Dos clientes utilizan el rango privado `10.0.0.0/16`. ¿Por qué no se mezclan sus rutas dentro de la MPLS L3VPN del operador?
    - A) El operador traduce las direcciones de los clientes mediante CGNAT
    - B) Los routers PE asocian las conexiones de los clientes a VRF separadas y anteponen un Route Distinguisher a las rutas de los clientes
    - C) Un controlador SD-WAN bloquea las direcciones duplicadas
    - D) Las líneas arrendadas separan físicamente a los clientes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Los routers PE asocian las conexiones de los clientes a VRF separadas y anteponen un Route Distinguisher a las rutas de los clientes**

**Explicación:**
En las VPN IP BGP/MPLS de RFC 4364, los routers PE asocian los circuitos de conexión de los clientes a tablas de enrutamiento independientes llamadas VRF y anteponen un Route Distinguisher a las rutas de los clientes que se anuncian mediante BGP para formar direcciones VPN-IPv4 distintas. Así, no se mezclan las direcciones privadas superpuestas de distintos clientes. SD-WAN es un modelo de servicio de superposición sobre circuitos, y una línea arrendada es un circuito punto a punto, un servicio distinto de MPLS L3VPN.

</details>

---

[Volver al material de estudio](../../basics/06-network-fundamentals-part5.md) | [Siguiente cuestionario: Arquitectura de clústeres](../core/01-cluster-architecture-quiz.md)
