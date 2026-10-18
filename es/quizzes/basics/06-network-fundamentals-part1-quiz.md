# Cuestionario de fundamentos de redes, parte 1: modelo por capas, enlace y enrutamiento

> **Última actualización**: 14 de septiembre de 2026

Comprueba tus conocimientos sobre los 11 protocolos y mecanismos de la capa de enlace y de las capas de Internet/enrutamiento.

## Preguntas de opción múltiple

1. En una red VPN o superpuesta, se produce un fallo en el que «el ping funciona, pero las respuestas grandes se quedan bloqueadas». ¿Qué debería sospechar primero?
   - A) El TTL de DNS es demasiado largo
   - B) La encapsulación reduce la MTU efectiva y se bloquea ICMP (un agujero negro de MTU)
   - C) Los algoritmos de control de congestión de TCP no coinciden
   - D) Venció la entrada de la caché ARP

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) La encapsulación reduce la MTU efectiva y se bloquea ICMP (un agujero negro de MTU)**

**Explicación:**
La encapsulación reduce el tamaño del paquete interno que cabe en la ruta. Los routers no pueden fragmentar los paquetes IPv4 con DF activado; PMTUD clásico necesita ICMP tipo 3, código 4. Los routers IPv6 nunca fragmentan y usan ICMPv6 Packet Too Big (tipo 2). El bloqueo de esos mensajes puede provocar agujeros negros, aunque PLPMTUD puede sondear tamaños sin depender de ICMP.

</details>

2. En una configuración de alta disponibilidad basada en VIP, ¿por qué el nuevo nodo activo envía un ARP gratuito inmediatamente después de la conmutación por error?
   - A) Para volver a registrar su dirección IP en el servidor DHCP
   - B) Para actualizar las tablas MAC de los conmutadores y las cachés ARP de los hosts vecinos, de modo que apunten al nuevo nodo
   - C) Para obligar a la puerta de enlace a recalcular su tabla de enrutamiento
   - D) Para renegociar las sesiones TLS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Para actualizar las tablas MAC de los conmutadores y las cachés ARP de los hosts vecinos, de modo que apunten al nuevo nodo**

**Explicación:**
La VIP se mantiene, pero cambia su propietario o la ubicación de la MAC/puerto. ARP gratuito anuncia a los vecinos la asignación IP-MAC, mientras el conmutador puede aprender la MAC de origen en su nuevo puerto. Algunos diseños de alta disponibilidad conservan la misma MAC virtual. Si esta actualización se retrasa, la conmutación por error tarda más.

</details>

3. ¿Qué afirmación describe con mayor precisión la diferencia entre OSPF y BGP?
   - A) OSPF selecciona rutas según políticas, mientras que BGP se centra en calcular la ruta más corta
   - B) OSPF se usa para el enrutamiento entre AS y BGP para el enrutamiento dentro de un AS
   - C) OSPF calcula las rutas más cortas con Dijkstra dentro de un AS, mientras que BGP selecciona rutas entre AS según políticas
   - D) Ambos son protocolos de estado de enlace y solo se diferencian en dónde se usan

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) OSPF calcula las rutas más cortas con Dijkstra dentro de un AS, mientras que BGP selecciona rutas entre AS según políticas**

**Explicación:**
OSPF es un IGP de estado de enlace: todos los routers de un área comparten la misma topología y calculan sobre ella las rutas más cortas. BGP es un protocolo de vector de rutas que selecciona «la ruta que prefiere la política» mediante atributos como AS_PATH, Local Preference y MED. Direct Connect usa BGP; Site-to-Site VPN admite BGP o enrutamiento estático en las configuraciones compatibles. BGP también tiene sesiones iBGP dentro de un AS.

</details>

4. ¿Qué explica mejor por qué se dice que NAT «infringe el modelo por capas»?
   - A) Modifica directamente las tramas de la capa de enlace
   - B) Es un dispositivo L3 que reescribe puertos L4 y rompe el principio de conectividad de extremo a extremo
   - C) Descifra paquetes cifrados
   - D) No usa tablas de enrutamiento

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Es un dispositivo L3 que reescribe puertos L4 y rompe el principio de conectividad de extremo a extremo**

**Explicación:**
NAT con traducción de puertos (PAT/NAPT) reescribe tanto las direcciones IP como los puertos y depende de una tabla de asignaciones por sesión. Como resultado, las conexiones P2P directas se volvieron difíciles y WebRTC lo resuelve con STUN/TURN (ICE). En la nube, los problemas prácticos son el agotamiento de puertos de NAT Gateway y los cargos por procesamiento de datos.

</details>

5. En una organización que adopta IPv6 mediante doble pila, ¿qué brecha de seguridad se debe comprobar?
   - A) IPv6 no admite cifrado
   - B) Solo se mantienen reglas de firewall IPv4 y faltan las reglas para la ruta IPv6
   - C) Las direcciones IPv6 son más fáciles de explorar
   - D) SLAAC deshabilita el servidor DHCP

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Solo se mantienen reglas de firewall IPv4 y faltan las reglas para la ruta IPv6**

**Explicación:**
La doble pila implica mantener dos conjuntos de reglas de firewall y políticas de seguridad. La falta de reglas IPv6 es un riesgo, pero una dirección IPv6 por sí sola no implica que se pueda acceder desde Internet. Siguen aplicándose las rutas, los grupos de seguridad y las NACL; una puerta de enlace de Internet solo de salida puede impedir conexiones IPv6 entrantes no solicitadas.

</details>

6. Para `192.0.2.130/26` en una subred IPv4 de difusión ordinaria, ¿qué red, dirección de difusión y rango de hosts son correctos?
   - A) Red `.0`, difusión `.255`, hosts `.1`–`.254`
   - B) Red `.130`, difusión `.193`, hosts `.131`–`.192`
   - C) Red `.128`, difusión `.191`, hosts `.129`–`.190`
   - D) Red `.128`, difusión `.190`, hosts `.129`–`.189`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Red `.128`, difusión `.191`, hosts `.129`–`.190`**

**Explicación:**
La máscara es `255.255.255.192`. Seis bits de host proporcionan 64 direcciones, y `.130` pertenece al bloque `.128`–`.191`. Al reservar las direcciones de red y difusión, quedan 62 direcciones de host ordinarias. Todas las direcciones de este ejemplo comparten el prefijo `192.0.2` y son direcciones de documentación.

</details>

7. Un host `192.0.2.130/26` tiene una ruta en enlace para su subred. La tabla de enrutamiento seleccionada también contiene `198.51.100.0/24` vía `.129`, `198.51.100.128/25` vía `.190` y una ruta predeterminada vía `.129` (las puertas de enlace están en `192.0.2`). Para el destino `198.51.100.140`, ¿qué ruta y destino ARP se aplican si falta la entrada del vecino?
   - A) Ruta predeterminada; ARP para `192.0.2.129`
   - B) Ruta `/25`; ARP para `192.0.2.190`
   - C) Ruta `/24`; ARP para `198.51.100.140`
   - D) Ruta `/25`; ARP para `198.51.100.140`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Ruta `/25`; ARP para `192.0.2.190`**

**Explicación:**
Las tres rutas remotas coinciden, pero `/25` es el prefijo más largo. ARP resuelve la puerta de enlace en enlace, así que la trama se envía a la MAC de esa puerta de enlace mientras el destino IP sigue siendo `198.51.100.140` (si no hay NAT). Una métrica inferior para la ruta predeterminada no prevalecería sobre la coincidencia más específica.

</details>

8. Un host `192.0.2.130/26` tiene una ruta en enlace `192.0.2.128/26` y una ruta predeterminada vía `192.0.2.129`. Sin una ruta más específica ni una entrada de vecino en caché, ¿cómo envía tráfico a `192.0.2.150`?
   - A) Envía una solicitud ARP para `192.0.2.150` y luego directamente a su MAC
   - B) Envía una solicitud ARP para `192.0.2.129`, porque todo el tráfico IP necesita una puerta de enlace
   - C) Envía una solicitud ARP para `192.0.2.191` y luego difunde el paquete IP
   - D) Envía a la puerta de enlace predeterminada sin un destino de capa de enlace

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Envía una solicitud ARP para `192.0.2.150` y luego directamente a su MAC**

**Explicación:**
La ruta `/26` seleccionada marca este destino como en enlace. El propio host de destino es el siguiente salto. La puerta de enlace predeterminada configurada solo se usa cuando la búsqueda de ruta la selecciona; el mero hecho de tenerla no obliga a enviar por ella el tráfico local.

</details>

9. ¿Qué afirmación contempla correctamente las excepciones al cálculo ordinario de «direcciones totales menos dos»?
   - A) Un `/31` siempre tiene cero endpoints utilizables
   - B) Un `/32` siempre proporciona un host y una dirección de puerta de enlace independiente
   - C) Todas las subredes `/26` de la nube permiten asignar las 62 direcciones de host ordinarias
   - D) Un `/31` compatible punto a punto usa ambas direcciones; un `/32` identifica una dirección; las reservas de la nube requieren una comprobación aparte

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Un `/31` compatible punto a punto usa ambas direcciones; un `/32` identifica una dirección; las reservas de la nube requieren una comprobación aparte**

**Explicación:**
RFC 3021 permite usar las dos direcciones `/31` como endpoints punto a punto. Una ruta de host `/32` coincide con una dirección y por sí sola no establece que sea alcanzable en enlace. Las subredes IPv4 VPC estándar de AWS reservan cinco direcciones, por lo que una `/26` tiene 59 direcciones asignables; los modos como BYOIP tienen reglas diferentes.

</details>

10. Un traceroute UDP recibe ICMP tipo 11, código 0 de un router intermedio y luego tipo 3, código 3 del destino. ¿Qué significa normalmente?
   - A) El TTL de una sonda venció durante el tránsito; una sonda posterior llegó a un puerto UDP no utilizado del destino
   - B) El destino respondió con datos UDP en cada salto
   - C) El router informó de un problema de MTU de ruta y luego el destino completó TLS
   - D) Traceroute cambió silenciosamente todas las sondas salientes por solicitudes ICMP Echo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) El TTL de una sonda venció durante el tránsito; una sonda posterior llegó a un puerto UDP no utilizado del destino**

**Explicación:**
El protocolo de la sonda y el de la respuesta difieren: las sondas UDP pueden provocar errores ICMP. Las variantes de traceroute con ICMP Echo y TCP SYN también reciben Time Exceeded en los saltos intermedios, pero las respuestas finales pueden ser Echo Reply o TCP SYN/ACK/RST. Fragmentation Needed es tipo 3, código 4, no ninguno de los códigos de esta pregunta.

</details>

11. Un salto de traceroute muestra `* * *`, mientras que los saltos posteriores y el destino responden. ¿Qué conclusión está justificada?
   - A) El router silencioso descarta todo el tráfico de extremo a extremo
   - B) No llegó una respuesta coincidente para esas sondas dentro del tiempo de espera; hace falta más evidencia para afirmar que hay pérdida de extremo a extremo
   - C) Las rutas de ida y vuelta son idénticas
   - D) Todos los tamaños de paquetes de aplicación caben en la MTU de la ruta

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) No llegó una respuesta coincidente para esas sondas dentro del tiempo de espera; hace falta más evidencia para afirmar que hay pérdida de extremo a extremo**

**Explicación:**
El filtrado, la supresión/limitación de frecuencia de respuestas o la pérdida en la ruta de retorno pueden provocar tiempos de espera. Compare sondas repetidas con los resultados del destino y de la aplicación. El RTT incluye la ruta de retorno, y que funcionen las sondas pequeñas no descarta un agujero negro de PMTU con paquetes mayores.

</details>

---

[Volver al material de estudio](../../basics/06-network-fundamentals-part1.md) | [Siguiente cuestionario: parte 2](./06-network-fundamentals-part2-quiz.md)

Repase el [ejemplo CIDR](../../basics/06-network-fundamentals-part1.md#ipv4-cidr-subnet), el [razonamiento del siguiente salto](../../basics/06-network-fundamentals-part1.md#longest-prefix-next-hop) y la [interpretación de ICMP](../../basics/06-network-fundamentals-part1.md#icmp-traceroute-interpretation), incluidas sus referencias principales.

## Referencias de verificación

- https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/network_mtu.html
- https://www.rfc-editor.org/rfc/rfc894
- https://www.rfc-editor.org/rfc/rfc6691
- https://www.rfc-editor.org/rfc/rfc4638
- https://www.rfc-editor.org/rfc/rfc5227
- https://www.rfc-editor.org/rfc/rfc792
- https://www.rfc-editor.org/rfc/rfc8899
- https://www.rfc-editor.org/rfc/rfc2328
- https://www.rfc-editor.org/rfc/rfc6811
- https://docs.kernel.org/networking/bridge.html
- https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Internet_Gateway.html
- https://docs.aws.amazon.com/vpc/latest/userguide/egress-only-internet-gateway.html
- https://docs.aws.amazon.com/vpn/latest/s2svpn/VPNRoutingTypes.html
- https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateway-scenarios.html
- https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateway-pricing.html
