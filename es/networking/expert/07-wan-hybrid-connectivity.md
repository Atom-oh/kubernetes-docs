# 07. Diseño de conectividad WAN e híbrida

> **Última actualización**: 19 de noviembre de 2026
> **Límite del laboratorio**: Solo revisión de diseño (comprobación de escritorio). Este cuaderno no crea circuitos, VPN, conexiones de Direct Connect ni Transit Gateways.
> **Estado de verificación**: Se consultaron las guías de usuario de AWS Direct Connect, Site-to-Site VPN y Transit Gateway, así como los RFC citados; al redactar este capítulo no se **configuró ni midió** ninguna conexión.

Al terminar este cuaderno, deberías poder **predecir la ruta en cada dirección** entre sitios locales y una región de AWS, y explicar, con pruebas, qué regla determina la siguiente ruta cuando falla un enlace, cuánto tarda y qué se reduce (ancho de banda, MTU).

Completa primero [Política de enrutamiento y convergencia medida](02-routing-policy-convergence.md). Ese capítulo explica qué significan LOCAL_PREF, AS_PATH, MED y las comunidades; este solo pregunta **hasta qué punto** AWS las respeta. Revisa los tipos de circuitos en [Fundamentos de redes, parte 5: tipos de WAN](../../basics/06-network-fundamentals-part5.md#wan-types) y NAT/CGNAT en [Parte 5: NAT, PAT y CGNAT](../../basics/06-network-fundamentals-part5.md#nat-pat-cgnat).

**Preparación:** no se necesita una cuenta ni un circuito. Todas las tareas se evalúan según las tablas de este capítulo y la documentación oficial. Implementar el mismo diseño en un entorno real genera cargos por el puerto de Direct Connect, la conexión VPN, la asociación de Transit Gateway y la transferencia de datos; **es responsabilidad del estudiante asumir esos costos y limpiar los recursos**. No crees recursos fuera de una cuenta de laboratorio aprobada y existente.

## 1. Lee con una pregunta que responder

El temario del examen solo determina qué leer. Los números y comportamientos proceden de los documentos oficiales de la primera columna.

| Lectura | Tema del examen relacionado | Pregunta que debes responder con tus propias palabras |
|---|---|---|
| [MEF 70.2](https://www.mplify.net/resources/mef-70-2-sd-wan-service-attributes-and-service-framework/), [guía de alta disponibilidad de Cisco Catalyst SD-WAN](https://www.cisco.com/c/en/us/td/docs/routers/sdwan/configuration/ha-scaling/ios-xe-17/high-availability-book-xe/m-high-availability-and-scaling.html) | ENCOR 350-401, arquitectura: elementos del plano de control y del plano de datos de SD-WAN | ¿Qué ocurre con los túneles de datos cuando el plano de control de la superposición queda inaccesible? |
| [Opciones de túnel de Site-to-Site VPN](https://docs.aws.amazon.com/vpn/latest/s2svpn/VPNTunnels.html), [opciones de enrutamiento](https://docs.aws.amazon.com/vpn/latest/s2svpn/VPNRoutingTypes.html) | ANS-C01, dominio 1: diseño de redes; dominio 2: implementación de redes | ¿Por cuál de los dos túneles envía tráfico AWS y qué puede cambiar esa elección? |
| [Políticas de enrutamiento y comunidades BGP de Direct Connect](https://docs.aws.amazon.com/directconnect/latest/UserGuide/routing-and-bgp.html) | ANS-C01, dominios 1 y 2 | ¿En qué orden compara AWS el mismo prefijo anunciado a través de dos VIF? |
| [Cómo funciona Transit Gateway](https://docs.aws.amazon.com/vpc/latest/tgw/how-transit-gateways-work.html) | ANS-C01, dominios 1 y 2 | Cuando el mismo CIDR llega por DX y VPN, ¿cuál gana y afecta AS_PATH a la elección? |
| [Cuotas de Direct Connect](https://docs.aws.amazon.com/directconnect/latest/UserGuide/limits.html), [cuotas de VPN](https://docs.aws.amazon.com/vpn/latest/s2svpn/vpn-limits.html), [cuotas de TGW](https://docs.aws.amazon.com/vpc/latest/tgw/transit-gateway-quotas.html) | ANS-C01, dominio 1 | ¿Qué límite alcanza primero el diseño: el ancho de banda, la cantidad de rutas o la MTU? |
| [RFC 5880 (BFD)](https://www.rfc-editor.org/rfc/rfc5880.html), [RFC 7296 (IKEv2)](https://www.rfc-editor.org/rfc/rfc7296.html) | Principios de protocolos | ¿Qué dos valores se multiplican para calcular el tiempo de detección de fallos? |

Después de leer, dibuja los sitios, los circuitos y los componentes de AWS, y representa con estilos de línea diferentes las **sesiones BGP** y los **enlaces que realmente atraviesan los paquetes**. Como mostró el [cuaderno 02](02-routing-policy-convergence.md), una sesión no implica que los datos circulen por ella; el Direct Connect gateway de abajo es el ejemplo típico.

## 2. Underlay y overlay

Registra el diseño WAN en dos capas. El **underlay** es el circuito que realmente transporta los paquetes (MPLS, acceso a Internet, Direct Connect); el **overlay** son los túneles y las políticas construidos sobre él (IPsec VPN, SD-WAN). Un overlay no puede cambiar la latencia, la pérdida ni la ruta física compartida del underlay: dos túneles sobre dos circuitos que comparten un conducto siguen teniendo un único punto de fallo.

| Modelo | Plano de control (quién decide la ruta) | Plano de datos (por dónde circulan los paquetes) | Qué verificar en un diseño |
|---|---|---|---|
| MPLS L3VPN | Los PE del proveedor separan las rutas de los clientes en VRF y las intercambian mediante BGP; entre CE y PE se usa enrutamiento estático, OSPF, BGP, etc. | La red MPLS del proveedor; el cliente nunca ve las etiquetas | Protocolo entre CE y PE, SLA del proveedor, separación física de otros operadores |
| Internet + IPsec | Ambos extremos, mediante rutas estáticas o BGP dentro del túnel | ESP a través de la Internet pública, con servicio de mejor esfuerzo | Número de túneles, tránsito por NAT, MTU según el algoritmo |
| SD-WAN | Un controlador central distribuye las políticas y las rutas | Túneles IPsec entre los bordes WAN, con varios underlay simultáneos | Comportamiento cuando los controladores son inaccesibles, medición de la ruta por túnel, política por aplicación |

**Cómo entender SD-WAN como planos de control y de datos:** MEF 70.2 define el servicio SD-WAN por separado de los servicios de conectividad subyacentes del underlay y define los túneles entre sitios (TVC) y la política por flujo de aplicación como atributos distintos (términos de la [parte 5](../../basics/06-network-fundamentals-part5.md#wan-types)). En Cisco Catalyst SD-WAN, los SD-WAN Controllers orquestan el plano de control e intercambian información de control mediante sesiones de peering OMP; el Validator autentica dispositivos y orquesta las conexiones de control entre los Controllers y los routers. Los datos circulan por conexiones IPsec entre routers, y BFD se ejecuta automáticamente en esas conexiones para detectar fallos. Por tanto, decir que «SD-WAN detecta fallos rápidamente» se refiere a **BFD en los túneles de datos**; la redundancia de los controladores es un elemento de diseño aparte.

En AWS, un dispositivo SD-WAN de una VPC establece una sesión BGP con un Transit Gateway a través de una asociación Connect. Un peer Connect (túnel GRE) transporta hasta 5 Gbps y una asociación puede tener hasta 4 peers. El ejercicio de este capítulo no usa Connect, pero la sección 8 lo incluye en la comparación de ancho de banda.

## 3. Site-to-Site VPN IPsec

**Definición:** cada conexión de AWS Site-to-Site VPN tiene **dos túneles**, cada uno con una dirección IP pública única y terminación en una Availability Zone distinta. Configura ambos para tener redundancia; cuando un túnel deja de estar disponible (por ejemplo, durante el mantenimiento), el tráfico pasa automáticamente al otro túnel de esa conexión.

**Comportamiento:**

- **Versión de IKE:** los túneles pueden permitir IKEv1 e IKEv2. AWS recomienda encarecidamente IKEv2 y usar IKEv1 solo si el dispositivo no admite IKEv2.
- **Uso de los túneles según la dirección:** el tráfico de las instalaciones a AWS usa ambos túneles. El tráfico de AWS a las instalaciones prefiere un túnel y conmuta al otro si se produce un fallo en el lado de AWS, por lo que el customer gateway debe **permitir el enrutamiento asimétrico**. En un virtual private gateway (VGW), se selecciona un túnel de entre todas las conexiones VPN de la gateway como ruta de salida, y no se admite ECMP.
- **BGP frente a enrutamiento estático:** elige el enrutamiento dinámico si el dispositivo admite BGP. AWS recomienda dispositivos compatibles con BGP porque las comprobaciones de disponibilidad de BGP ayudan a conmutar al segundo túnel. Si se elige BGP, no se pueden especificar también rutas estáticas.
- **ECMP:** las VPN de un Transit Gateway pueden agregar túneles mediante ECMP **solo con enrutamiento dinámico**; las VPN con enrutamiento estático no admiten ECMP.
- **Ancho de banda:** un túnel estándar transporta hasta 1.25 Gbps (hasta 140,000 PPS). Un Large Bandwidth Tunnel transporta hasta 5 Gbps, pero solo está disponible para VPN asociadas a un Transit Gateway o a Cloud WAN; ambos túneles deben usar la misma configuración de ancho de banda, y no se admite Accelerated VPN.
- **Disponibilidad:** el tiempo de espera de Dead Peer Detection es de 30 segundos o más, y la acción al agotar el tiempo es `Clear` (finalizar la sesión IKE, detener el túnel y borrar las rutas), `None` o `Restart`. AWS Knowledge Center indica que el tiempo de espera predeterminado de BGP para una VPN es de 30 segundos.
- **Customer gateway detrás de NAT:** una gateway detrás de NAT usa la transversal de NAT (NAT-T, RFC 3948), que encapsula ESP en UDP. La tabla de MTU de la sección 7 muestra que habilitar NAT-T reduce la MTU con el mismo algoritmo. Una sucursal detrás de CGNAT no puede aceptar primero una sesión entrante (consulta la [parte 5](../../basics/06-network-fundamentals-part5.md#nat-pat-cgnat)), así que diseña esa sucursal para que inicie el túnel.

**En la práctica:** no concluyas que «hay dos túneles, así que la redundancia está resuelta». Los dos túneles redundan el endpoint de AWS; si comparten un customer gateway y un circuito de Internet, esos dos elementos siguen siendo puntos únicos de fallo. Para tener redundancia del lado del cliente, añade un segundo customer gateway y una segunda conexión VPN.

## 4. Direct Connect

**Definición:** Direct Connect enlaza tu red con un router de AWS en una ubicación de Direct Connect mediante un cable de fibra óptica Ethernet estándar. Creas **interfaces virtuales (VIF)** en él para acceder a las VPC o a los servicios públicos de AWS, sin pasar por proveedores de servicios de Internet en la ruta. El dispositivo debe admitir VLAN 802.1Q, BGP y autenticación BGP MD5.

**Tipos de conexión:**

| Tipo | Velocidad | VIF | Notas |
|---|---|---|---|
| Dedicada | 1, 10, 100, 400 Gbps | Hasta 50 VIF públicas/privadas más hasta 4 VIF de tránsito, 51 en total (no se puede aumentar) | Fibra monomodo, estándar de transceptor fijo según la velocidad del puerto |
| Hospedada | Valores aprovisionados por el socio, de 50 Mbps a 25 Gbps | 1 (no se puede aumentar) | Solo los socios que cumplen los requisitos ofrecen 1 Gbps o más; 25 Gbps solo donde hay puertos de 100 Gbps. AWS limita el tráfico y descarta el exceso |

**Tipos de VIF:**

- **VIF privada:** accede a una VPC mediante IP privadas. Asociada directamente a un VGW, llega a una VPC de la misma región; asociada a un Direct Connect gateway, llega a VGW de distintas cuentas y regiones.
- **VIF pública:** accede a servicios públicos de AWS mediante IP públicas. Los prefijos públicos que anuncies deben ser tuyos, y AWS filtra el tráfico entrante para comprobar que su origen sea uno de tus prefijos anunciados.
- **VIF de tránsito:** accede a Transit Gateway asociados a un Direct Connect gateway, a través de cualquier conexión dedicada o hospedada, independientemente de su velocidad.

**Direct Connect gateway:** recurso global asociado a VGW, Transit Gateway o una red central de Cloud WAN. AWS lo describe como un **conjunto distribuido de reflectores de rutas BGP** que funciona fuera de la ruta del tráfico de datos, por lo que no crea un punto único de fallo. Al igual que el reflector de rutas del cuaderno 02, refleja rutas, pero no transporta paquetes. Una gateway admite hasta 20 VGW, 6 Transit Gateway y 30 VIF privadas o de tránsito.

**Límites de rutas:** pueden causar interrupciones directamente, así que inclúyelos en la tabla de diseño.

- De las instalaciones a AWS, a través de una VIF privada o de tránsito, una sesión BGP acepta de forma predeterminada 100 rutas IPv4 y 100 rutas IPv6; con controles de prefijos, el límite se puede aumentar a 1,000 de cada tipo. **Si se anuncian más rutas que las asignadas, la sesión BGP pasa a estado inactivo y se informa como DOWN.**
- Una sesión BGP de VIF pública acepta 1,000 rutas.
- De AWS a las instalaciones, a través de una VIF de tránsito, cada Transit Gateway anuncia hasta 200 prefijos en total, combinando IPv4 e IPv6.

**Prefijos permitidos:** para una asociación de Transit Gateway, el Direct Connect gateway anuncia **exactamente** los prefijos permitidos que introduzcas. Con el CIDR de VPC `10.20.0.0/16` y un prefijo permitido de `10.0.0.0/8`, las instalaciones reciben solo `10.0.0.0/8`. En cambio, para una asociación de VGW, los prefijos permitidos actúan como filtro que deja pasar CIDR iguales o más pequeños. La trampa de la sección 6 empieza aquí.

<a id="dx-lag"></a>

**LAG:** un grupo de agregación de enlaces usa LACP para agrupar varias conexiones en un único endpoint de Direct Connect y convertirlas en una conexión lógica. Reglas:

- Todas las conexiones deben ser dedicadas y tener el mismo ancho de banda.
- Un LAG admite hasta 4 conexiones por debajo de 100 Gbps, o hasta 2 conexiones de 100 o 400 Gbps.
- Todas las conexiones deben terminar en el mismo endpoint de Direct Connect; no se admite el LAG de varios chasis (MLAG).
- Todas las conexiones funcionan en modo activo/activo. Un LAG tiene un atributo de enlaces mínimos (0 de forma predeterminada); si se establece, todo el LAG deja de funcionar cuando hay menos conexiones operativas que las indicadas, lo que evita sobrecargar las conexiones que siguen activas.

Un LAG añade **capacidad**, pero termina en el mismo dispositivo y en la misma ubicación, así que no resiste el fallo de una ubicación. Como señaló la parte 5, un flujo sigue sin poder superar la velocidad de un enlace miembro. Diseña la redundancia de ubicación con los modelos de Resiliency Toolkit: **Maximum resiliency** apunta a un SLA del 99.99% y **High resiliency** al 99.9%, pero solo si se cumplen todos los requisitos del SLA de Direct Connect; **Development and test** distribuye las conexiones entre dispositivos distintos en una misma ubicación.

**MACsec:** está disponible en conexiones **dedicadas** de 10, 100 y 400 Gbps en ubicaciones seleccionadas; no está disponible en conexiones dedicadas de 1 Gbps ni en conexiones hospedadas. Es un cifrado L2 salto a salto, por lo que el dispositivo necesita adyacencia L2 directa con el dispositivo de AWS y cualquier segmento de última milla debe ser transparente para L2. Solo se admiten claves de 256 bits, y las conexiones de 100/400 Gbps requieren numeración extendida de paquetes (XPN). En un LAG, se usa una sola clave MACsec en todos los enlaces en cualquier momento.

## 5. Transit Gateway

**Definición:** un Transit Gateway es un router virtual regional para el tráfico entre VPC y redes locales. Una asociación es tanto origen como destino de paquetes; se pueden asociar VPC, conexiones VPN, VPN Concentrators, Direct Connect gateways, asociaciones Connect y conexiones de emparejamiento.

**Reglas de la tabla de rutas:**

- Una asociación se **asocia a una** tabla de rutas y puede **propagarse a muchas**. Las rutas propagadas no se pueden filtrar.
- Una VPN con enrutamiento dinámico anuncia por BGP a la customer gateway las rutas de la tabla de rutas asociada. Una asociación de Direct Connect gateway anuncia sus prefijos permitidos.
- Para un mismo destino, una ruta estática prevalece sobre una ruta propagada, y la ruta propagada no se muestra en la tabla.
- Transit Gateway solo muestra la ruta preferida. Cuando la misma ruta llega por DX y VPN, la tabla muestra la ruta de DX; la ruta de VPN aparece solo cuando deja de anunciarse la ruta de DX.
- Las asociaciones de emparejamiento solo admiten rutas estáticas.

**Orden de evaluación de rutas:** primero gana la ruta más específica. Para el mismo CIDR procedente de distintos tipos de asociación, el orden de prioridad es:

1. Rutas estáticas (por ejemplo, rutas estáticas de Site-to-Site VPN)
2. Rutas del sistema (para NAT 1:1)
3. Rutas referenciadas por listas de prefijos
4. Rutas propagadas por VPC
5. Rutas propagadas por Direct Connect gateway
6. Rutas propagadas por Transit Gateway Connect
7. Rutas de Site-to-Site VPN propagadas a través de Direct Connect privado
8. Rutas propagadas por Site-to-Site VPN
9. Rutas propagadas por Site-to-Site VPN Concentrator
10. Rutas propagadas por Client VPN
11. Rutas propagadas por el emparejamiento de Transit Gateway (Cloud WAN)

Solo se comparan los atributos BGP para el mismo CIDR procedente del **mismo tipo de asociación**: primero, el AS_PATH más corto; después, el MED más bajo; y, donde se admita, eBGP antes que iBGP. Las rutas anunciadas sin MED reciben un valor predeterminado de 0 en las asociaciones de Direct Connect y de 100 en las asociaciones de VPN y Connect. No se admite ECMP entre distintos tipos de asociación (por ejemplo, VPN y VPC); se selecciona una sola ruta mediante el orden de evaluación anterior.

**MTU y ancho de banda:** el tráfico entre asociaciones de VPC, Direct Connect, Connect y emparejamiento tiene una MTU de 8500 bytes; el tráfico que pasa por VPN tiene una MTU de 1500. Transit Gateway aplica ajuste de MSS a todos los paquetes. Path MTU Discovery solo se admite para el tráfico que entra por asociaciones de VPC y Connect, no por asociaciones de VPN, Direct Connect o emparejamiento. El ancho de banda de una asociación de VPC y de un Direct Connect gateway es de hasta 100 Gbps por dirección y por Availability Zone.

<a id="failover-design"></a>

## 6. Diseño de conmutación por error: DX principal, VPN de respaldo

Lee esta sección **por dirección**. La ruta de las instalaciones a AWS la elige **la política de tu router**; la ruta de AWS a las instalaciones la elige **el orden de evaluación de AWS**. Si cambias solo un lado, las rutas se vuelven asimétricas y un firewall con estado podría descartar las respuestas.

![Animación de conmutación por error híbrida. ① El router local (AS 65010, 10.10.0.0/16) aprende dos rutas BGP a la VPC 10.20.0.0/16, una por DX y otra por VPN; elige la ruta DX con LOCAL_PREF 200 y envía un paquete a 10.20.1.10 por la VLAN 802.1Q 101 de la conexión DX (VIF de tránsito). ② Después de la ubicación DX, el paquete llega al Transit Gateway sin que cambie su destino, y la tabla de rutas del TGW lo reenvía a la asociación de la VPC. El DX gateway solo refleja rutas BGP y no forma parte de la ruta de datos. ③ Se corta el enlace DX. Cuando BFD deja de recibir tres respuestas, separadas por intervalos de 300 ms, la sesión BGP se interrumpe, se retiran las rutas DX de ambos lados y la mejor ruta local cambia al túnel VPN con LOCAL_PREF 100. ④ El siguiente paquete toma la ruta VPN: IPsec añade ESP y una cabecera IP externa (origen 203.0.113.10, destino 198.51.100.10) y el paquete cruza Internet. ⑤ En la asociación VPN de Transit Gateway se elimina ESP y el paquete original con destino 10.20.1.10 se reenvía a la VPC. El tráfico de retorno también usa la ruta propagada por VPN porque la ruta DX ya no está.](../../.gitbook/assets/en-networking-expert-07-wan-hybrid-connectivity-anim-0.svg)

### De AWS a las instalaciones: la ruta que elige AWS

**En un Transit Gateway**, se aplica tal cual el orden de evaluación de la sección 5:

1. **Primero, el prefijo más largo.** Si las instalaciones anuncian `10.10.1.0/24` por VPN y `10.10.0.0/16` por DX, el tráfico a `10.10.1.0/24` pasa por VPN. Para mantener DX como ruta principal, anuncia **prefijos idénticos** por ambas rutas.
2. **Para el mismo CIDR, el tipo de asociación prevalece sobre AS_PATH.** Las rutas propagadas por Direct Connect gateway siempre prevalecen sobre las rutas propagadas por VPN, así que añadir prefijos a AS_PATH en los anuncios de VPN no afecta a la elección entre DX y VPN. En cambio, una **ruta estática** en la VPN prevalece sobre la ruta propagada por DX y hace que la VPN sea la ruta principal sin avisar. Configura la VPN de respaldo con BGP.
3. **Los atributos BGP solo se comparan dentro del mismo tipo**, por ejemplo, entre varias VIF DX o varias conexiones VPN.

**En un VGW**, el orden es diferente: para el mismo prefijo, las rutas BGP de Direct Connect prevalecen sobre las rutas estáticas de VPN, que prevalecen sobre las rutas BGP de VPN; entre rutas BGP de VPN, gana el AS_PATH más corto y luego el MED más bajo si el primer AS coincide. No combines las dos listas.

**Entre varias VIF DX**, AWS compara las rutas de VIF privadas y de tránsito en este orden:

| Orden | Criterio | Cómo se utiliza en los diseños |
|---|---|---|
| 1 | Prefijo más largo | Expresar una configuración activa/pasiva con rutas más específicas |
| 2 | Comunidad de preferencia local | `7224:7300` (alta), `7224:7200` (media), `7224:7100` (baja); comunidades estándar que se evalúan antes de AS_PATH. Las comunidades extendidas, como los route targets, no se evalúan para determinar la preferencia y se pueden eliminar |
| 3 | Longitud de AS_PATH | Añadir prefijos cuando el prefijo y la preferencia local sean iguales |
| 4 | MED | La prioridad más baja; AWS no recomienda depender de él |
| Empate | ECMP | Con la misma longitud de AS_PATH y los mismos atributos, el tráfico se distribuye entre las VIF |

Si no se usan comunidades, una región de AWS prefiere las ubicaciones de Direct Connect **asociadas a esa región**. Para una configuración activa/activa, aplica la misma comunidad (por ejemplo, `7224:7200`) a todas las VIF; para una configuración activa/pasiva, aplica `7224:7300` a la VIF principal y `7224:7100` a la VIF de respaldo. Estas comunidades determinan la preferencia del tráfico **de retorno** a las instalaciones.

**Prevención de bucles:** AWS considera que una ruta cuyo AS_PATH contiene dos o más veces el ASN `7224` de Direct Connect forma un bucle y no la instala. Esto ocurre cuando se vuelven a anunciar por otra VIF las rutas aprendidas de AWS a través de una VIF; filtra las rutas aprendidas de AWS para que no formen parte de lo que anuncias a AWS.

### De las instalaciones a AWS: la ruta que elige tu router

AWS anuncia la misma ruta de VPC por DX (los prefijos permitidos) y por VPN (las rutas de la tabla de rutas del TGW). Tu router las compara mediante las reglas de selección de BGP del cuaderno 02, así que un LOCAL_PREF mayor en las rutas aprendidas por DX convierte DX en la ruta principal. Los valores LOCAL_PREF 200/100 de la animación representan esa política.

**La trampa de los prefijos permitidos:** si el prefijo permitido está resumido como `10.0.0.0/8`, mientras que VPN anuncia `10.20.0.0/16` desde la tabla de rutas del TGW, tu router elige el **prefijo VPN más largo**. LOCAL_PREF solo compara rutas para el mismo prefijo, así que no puede corregirlo. Haz que la longitud del prefijo permitido coincida con la del lado VPN, o resume de la misma manera en tu router las rutas aprendidas por VPN.

### Presupuesto de tiempo de detección

| Mecanismo | Valor | Naturaleza de la fuente |
|---|---|---|
| BFD en DX | BFD asíncrono se habilita automáticamente en el lado de AWS, pero solo entra en funcionamiento cuando se configura en el router; intervalo mínimo de 300 ms, multiplicador 3 | Preguntas frecuentes y guía de usuario de Direct Connect |
| BGP de DX sin BFD | La sesión se interrumpe tras un tiempo de espera de 90 segundos sin mensajes de mantenimiento | AWS Knowledge Center |
| BGP de VPN | Tiempo de espera predeterminado de 30 segundos | AWS Knowledge Center |
| DPD de VPN | 30 segundos o más; acción al agotar el tiempo: `Clear`, `None` o `Restart` | Guía de usuario de VPN |

Cuando BFD detecta un fallo, la relación con el vecino BGP se interrumpe rápidamente en vez de esperar a que venza el tiempo de espera. Según el RFC 5880, el tiempo de detección de BFD es el multiplicador remoto por el intervalo negociado, así que 300 ms × 3 son aproximadamente 0.9 segundos. Pero **el tiempo de detección no es el tiempo de recuperación**. La recuperación también incluye retirar y propagar rutas, programar la FIB en ambos routers y conmutar la dirección inversa; AWS no publica valores fijos para esos procesos. En un documento de diseño, cita los valores de detección y marca el resto como **suposiciones hasta que se mida**, usando los puntos de medición del cuaderno 02 (tiempo de actuación, primer cambio, cambio de FIB, recuperación sostenida).

## 7. MTU y MSS a través de túneles

| Segmento | MTU | Notas |
|---|---|---|
| Site-to-Site VPN | Hasta 1446 bytes, MSS 1406 | Sin tramas jumbo ni Path MTU Discovery; menor con algunos algoritmos y con NAT-T |
| VIF privada | 1500 o 9001 | Tramas de capa de enlace de 1522 o 9023 bytes |
| VIF de tránsito | 1500 o 8500 | Las tramas jumbo en Transit Gateway solo admiten 8500 |
| Transit Gateway | 8500 entre VPC, DX, Connect y emparejamiento; 1500 por VPN | Ajuste de MSS en todos los paquetes; PMTUD solo para el tráfico entrante desde VPC y Connect |

Por ejemplo, estos son los valores de MTU/MSS de VPN recomendados por AWS (MSS de IPv4):

| Cifrado | Integridad | NAT-T | MTU | MSS |
|---|---|---|---|---|
| AES-GCM-16 | N/A | deshabilitado | 1446 | 1406 |
| AES-GCM-16 | N/A | habilitado | 1438 | 1398 |
| AES-CBC | SHA1/SHA2-256 | deshabilitado | 1438 | 1398 |
| AES-CBC | SHA2-512 | habilitado | 1406 | 1366 |

**Comportamiento:**

- AWS recomienda que el customer gateway fragmente **antes del cifrado**. La VPN vuelve a ensamblar los fragmentos antes de reenviarlos, así que comprueba también que el paquete reensamblado quepa en el siguiente segmento (por ejemplo, Direct Connect).
- Cambiar una VIF a una MTU jumbo puede actualizar la conexión subyacente y provocar una interrupción de hasta 30 segundos en todas las VIF que la utilizan; haz el cambio durante una ventana de mantenimiento.
- Si dos VIF privadas anuncian la misma ruta con diferentes MTU, o una Site-to-Site VPN anuncia la misma ruta, se usa una MTU de 1500.

**Consideración de diseño:** en un diseño de conmutación por error, **la MTU importante es la de la ruta de respaldo**. Una conexión TCP establecida por DX con un MSS grande que pasa a VPN puede descartar sin aviso sus paquetes grandes con el bit DF activado en segmentos que no admiten PMTUD. En este ejercicio, compara dos opciones: limitar en tu router el MSS de los flujos híbridos al valor de VPN correspondiente al algoritmo elegido, o mantener la VIF en 1500 mientras VPN sea la ruta de respaldo.

## 8. Compensaciones entre ancho de banda, latencia y costo

| Conexión | Ancho de banda (límite oficial) | Latencia y calidad | Unidad de redundancia | Elementos de costo |
|---|---|---|---|---|
| DX dedicada | 1/10/100/400 Gbps, agrupadas con LAG | Ruta dedicada que evita los proveedores de servicios de Internet | Conexión, dispositivo, ubicación (modelos de Resiliency Toolkit) | Horas de puerto, transferencia de datos salientes |
| DX hospedada | De 50 Mbps a 25 Gbps | Pasa por la red del socio; AWS limita el tráfico a la velocidad contratada | Cada conexión hospedada, red del socio | Los mismos conceptos de AWS más los cargos del socio |
| Túnel VPN estándar | Hasta 1.25 Gbps, 140,000 PPS por túnel | Ruta por Internet, con servicio de mejor esfuerzo | Dos túneles (lado de AWS); el customer gateway y el circuito son independientes | Horas de conexión, transferencia de datos salientes, IPv4 pública por túnel |
| VPN Large Bandwidth Tunnel | Hasta 5 Gbps por túnel (solo TGW y Cloud WAN) | Como la estándar; mismo límite de MTU | Como arriba | Precio independiente por hora de conexión |
| ECMP de VPN en TGW | Suma de varios túneles con enrutamiento dinámico | Distribución por flujo; un flujo está limitado a un túnel | Por túnel y conexión | Cargos de VPN más horas de asociación de TGW y procesamiento por GB |
| Connect (SD-WAN) | 5 Gbps por peer, 4 peers por asociación | Depende del transporte subyacente (VPC o DX) | Por peer y asociación | Horas de asociación de TGW más el procesamiento de la asociación de transporte |

Transit Gateway cobra por hora de asociación y por GB de datos procesados desde asociaciones de VPC, Direct Connect y VPN. Los precios unitarios varían según la región y el tiempo, por lo que el diseño solo registra **los elementos de costo**; calcula los importes con las páginas de precios el día que los consultes.

## 9. Ejercicio de diseño: dos sitios y una región

Esta es una comprobación de escritorio que no crea recursos. Etiqueta los resultados como **revisión de diseño**.

**Datos de entrada:**

| Ubicación | Direcciones y ASN | Conectividad |
|---|---|---|
| Sitio A (centro de datos de la sede central) | `10.10.0.0/16`, AS 65010 | Una conexión dedicada de 10 Gbps en cada una de dos ubicaciones DX distintas (DX-1, DX-2), una VIF de tránsito en cada una; un circuito de Internet con un customer gateway |
| Sitio B (sucursal) | `10.30.0.0/16`, AS 65030 | Dos circuitos de Internet de operadores diferentes, un customer gateway y una conexión VPN por circuito; sin DX |
| Región | VPC `10.20.0.0/16`, un Transit Gateway (ASN de Amazon de ejemplo: 64512), un Direct Connect gateway (ASN de ejemplo: 64513) | El DX gateway y las tres VPN se asocian al mismo TGW |

El tráfico entre el sitio A y el sitio B usa el servicio MPLS existente y queda fuera del alcance. Supón que todas las VPN usan BGP, IKEv2 y AES-GCM con NAT-T deshabilitado.

**Objetivos de nivel de servicio:** son objetivos de diseño del estudiante, no SLA de AWS.

- Sitio A → VPC: mantener al menos 5 Gbps cuando falle cualquier conexión, dispositivo o ubicación DX, y procurar que la recuperación de la ruta de datos en ambas direcciones ocurra en los 5 segundos posteriores a la detección del fallo. Si fallan ambas conexiones DX, se acepta un funcionamiento degradado por VPN.
- Sitio B → VPC: mantener la conexión cuando falle un circuito o un customer gateway; se acepta la conmutación dentro del tiempo de espera de BGP.

**Tareas:**

1. **Tabla de anuncios:** para cada ruta, registra quién anuncia qué prefijos: los prefijos permitidos del DX gateway, las rutas de la tabla del TGW que recibe cada VPN y lo que los sitios A y B anuncian a AWS. Compara los valores con las cuotas (100 por sesión BGP de DX de forma predeterminada, 200 por TGW).
2. **Tabla de políticas:** configura el LOCAL_PREF del sitio A (DX-1, DX-2, VPN), la preferencia local de las comunidades en las VIF DX y las asociaciones y propagaciones de la tabla de rutas del TGW. Decide si las dos conexiones DX estarán en modo activo/activo o activo/pasivo, según el objetivo de 5 Gbps.
3. **Predicción de rutas:** para cada situación de abajo, registra las rutas Sitio A → VPC, VPC → Sitio A, Sitio B → VPC y VPC → Sitio B, así como **el paso de la regla** que determina cada ruta (por ejemplo, «paso 5 del orden de evaluación de TGW, propagada por Direct Connect gateway»).
4. **Presupuesto de tiempo:** para cada situación, registra el mecanismo de detección y su valor, enumera los elementos que mantienes como suposiciones hasta que se midan y determina si se cumple o no el objetivo.
5. **Decisión sobre MTU:** elige la MTU de la VIF de tránsito y el ajuste de MSS del sitio A, e indica el motivo.

| Situación | Sitio A → VPC | VPC → Sitio A | Regla aplicada | Detección | Ancho de banda restante | Veredicto |
|---|---|---|---|---|---|---|
| Normal | | | | | | |
| Falla la conexión DX-1 | | | | | | |
| Falla por completo la ubicación DX 1 | | | | | | |
| Fallan DX-1 y DX-2 | | | | | | |
| Falla DX-1 sin que BFD esté configurado en el router del sitio A | | | | | | |
| Falla un circuito del sitio B | | | | | | |
| DX-1 se recupera | | | | | | |

**Criterios de revisión:** cada celda cita al menos una regla de los documentos fuente. Comprueba lo siguiente:

- ¿Explicaste por qué VPC → Sitio A usa DX en condiciones normales según el orden de evaluación de TGW y no porque «DX es más rápido»?
- ¿Evitaste las rutas estáticas en VPN? Si usaste una, ¿comprobaste que VPN gana incluso en condiciones normales?
- ¿Tienen la misma longitud los prefijos permitidos y los anunciados por VPN? Si no, ¿en qué dirección se desvía el tráfico a VPN?
- ¿Determinaste que la situación sin BFD no cumple el objetivo de 5 segundos (tiempo de espera de BGP de 90 segundos)?
- Cuando las dos conexiones DX están caídas, ¿registraste que el ancho de banda se reduce a los límites de VPN (1.25 Gbps por túnel estándar, la suma de los túneles con ECMP) y que un flujo no puede superar la capacidad de un túnel?
- ¿Calculaste la MTU a partir de la ruta de respaldo?

## 10. Observar el fallo y la recuperación

Si no tienes un entorno real, esta sección sirve para practicar cómo determinar **qué pruebas confirmarían cada veredicto**. Si más adelante puedes reproducir una situación en un entorno aprobado y existente, recopila estas pruebas.

| Capa | Qué observar | Qué no demuestra por sí sola esa prueba |
|---|---|---|
| Tabla BGP de tu router | Ambas rutas candidatas, LOCAL_PREF, indicador de mejor ruta | La ruta de retorno del lado de AWS |
| FIB de tu router y una captura | Interfaz de salida real, ESP en la interfaz del túnel | El éxito de todos los flujos de aplicación |
| Tabla de rutas de TGW | La única ruta preferida; la ruta VPN de respaldo aparece solo después de retirar la ruta DX | La ruta que realmente siguieron los paquetes |
| CloudWatch | `TunnelState` de VPN, `VirtualInterfaceBgpStatus` de VIF DX | Cuándo empezó y terminó la pérdida en el plano de datos |
| Sondeos específicos del origen | Intervalo de pérdida, inicio de la recuperación sostenida | Paquetes grandes o todos los puertos |

**La conmutación de vuelta también es un fallo.** Cuando DX vuelve y se restablece BGP, la ruta propagada por Direct Connect gateway vuelve a ganar en TGW y la ruta DX con LOCAL_PREF más alto vuelve a ganar en tu router. Por tanto, el tráfico cambia de ruta **automáticamente**, con otro cambio de ruta y de MTU. Un enlace inestable puede hacer que la ruta cambie repetidamente; define por adelantado el criterio de recuperación sostenida (por ejemplo, respuestas consecutivas y una ventana de observación). Como en el cuaderno 02, que no se observe pérdida solo significa que la resolución del muestreo no detectó una interrupción.

## 11. Entregables y criterios de finalización

| Entregable | Se considera terminado cuando |
|---|---|
| Diagrama de topología | Las sesiones y los enlaces de datos se distinguen, y el DX gateway queda fuera de la ruta de datos |
| Tablas de anuncios y políticas | Se registran todos los prefijos permitidos, anuncios de VPN, LOCAL_PREF, comunidades y asociaciones/propagaciones de TGW, y se comprueban frente a las cuotas |
| Tabla de situaciones | Las siete situaciones incluyen las rutas en ambas direcciones, la regla aplicada, los valores de detección, el ancho de banda restante y un veredicto |
| Decisión sobre MTU | Se incluye un valor de MSS calculado a partir de la ruta de respaldo y la tabla de origen |
| Lista de incógnitas | Los elementos sin valores fijos publicados, como el tiempo de propagación de rutas y el tiempo de programación de la FIB, se indican como suposiciones hasta que se midan |

Has terminado cuando puedes explicar, con fuentes, las reglas de selección por dirección, la relación entre el orden de los tipos de asociación y AS_PATH, la trampa de los prefijos permitidos, la diferencia entre el tiempo de detección y el tiempo de recuperación y por qué la ruta de respaldo determina la MTU. Incorpora las tablas de resultados a la revisión de cambios del [proyecto integrador de automatización](06-automation-capstone.md) y continúa con las rutas dentro de la nube en [Diseño de nube y CNI](05-cloud-cni-design.md). Para ver opciones de VPC entre organizaciones, consulta [Conectividad de VPC entre organizaciones](../05-cross-org-vpc-connectivity.md); para conocer los requisitos de red de EKS Hybrid Nodes, consulta [Configuración de red de Hybrid Nodes](../../eks-hybrid-nodes/02-network-configuration.md). Por último, completa el [cuestionario](../../quizzes/networking/expert/07-wan-hybrid-connectivity-quiz.md).

## Referencias

AWS Direct Connect

- [¿Qué es Direct Connect?](https://docs.aws.amazon.com/directconnect/latest/UserGuide/Welcome.html) (tipos de VIF, requisitos de red, BFD, elementos de precios)
- [Cuotas de Direct Connect](https://docs.aws.amazon.com/directconnect/latest/UserGuide/limits.html)
- [Conexiones hospedadas](https://docs.aws.amazon.com/directconnect/latest/UserGuide/hosted_connection.html)
- [Interfaces virtuales y MTU](https://docs.aws.amazon.com/directconnect/latest/UserGuide/WorkingWithVirtualInterfaces.html)
- [Políticas de enrutamiento y comunidades BGP](https://docs.aws.amazon.com/directconnect/latest/UserGuide/routing-and-bgp.html)
- [Direct Connect gateways](https://docs.aws.amazon.com/directconnect/latest/UserGuide/direct-connect-gateways-intro.html), [Interacciones de los prefijos permitidos](https://docs.aws.amazon.com/directconnect/latest/UserGuide/allowed-to-prefixes.html)
- [Grupos de agregación de enlaces](https://docs.aws.amazon.com/directconnect/latest/UserGuide/lags.html), [Seguridad MAC](https://docs.aws.amazon.com/directconnect/latest/UserGuide/MACsec.html), [Resiliency Toolkit](https://docs.aws.amazon.com/directconnect/latest/UserGuide/resiliency_toolkit.html)
- [Preguntas frecuentes sobre Direct Connect](https://aws.amazon.com/directconnect/faqs/) (valores predeterminados de BFD, conexiones compatibles con MACsec)
- [AWS Knowledge Center: habilitar BFD para Direct Connect](https://repost.aws/knowledge-center/enable-bfd-direct-connect) (tiempo de espera de BGP de 90 segundos sin BFD)
- [Métricas de CloudWatch para el estado de BGP de las interfaces virtuales de Direct Connect](https://aws.amazon.com/blogs/networking-and-content-delivery/introducing-cloudwatch-metrics-for-aws-direct-connect-virtual-interface-bgp-health-and-prefix-count/)

AWS Site-to-Site VPN

- [Opciones de túnel](https://docs.aws.amazon.com/vpn/latest/s2svpn/VPNTunnels.html), [Configurar las opciones de túnel](https://docs.aws.amazon.com/vpn/latest/s2svpn/tunnel-configure.html)
- [Opciones de enrutamiento](https://docs.aws.amazon.com/vpn/latest/s2svpn/VPNRoutingTypes.html), [Enrutamiento estático y dinámico](https://docs.aws.amazon.com/vpn/latest/s2svpn/vpn-static-dynamic.html), [Tablas de rutas y prioridad de rutas](https://docs.aws.amazon.com/vpn/latest/s2svpn/vpn-route-priority.html)
- [Cuotas de Site-to-Site VPN](https://docs.aws.amazon.com/vpn/latest/s2svpn/vpn-limits.html) (ancho de banda, PPS, MTU, cantidad de rutas)
- [Prácticas recomendadas para un dispositivo customer gateway](https://docs.aws.amazon.com/vpn/latest/s2svpn/cgw-best-practice.html) (IKEv2, fragmentación antes del cifrado, MTU/MSS según el algoritmo)
- [Supervisar túneles VPN con CloudWatch](https://docs.aws.amazon.com/vpn/latest/s2svpn/monitoring-cloudwatch-vpn.html)
- [AWS Knowledge Center: solucionar problemas de un túnel VPN con registros de BGP](https://repost.aws/knowledge-center/vpn-bgp-logs-troubleshoot-tunnel) (tiempo de espera predeterminado de 30 segundos)
- [Precios de AWS VPN](https://aws.amazon.com/vpn/pricing/)

AWS Transit Gateway

- [Cómo funciona AWS Transit Gateway](https://docs.aws.amazon.com/vpc/latest/tgw/how-transit-gateways-work.html) (asociaciones, asociación y propagación, orden de evaluación de rutas, ECMP)
- [Cuotas de Transit Gateway](https://docs.aws.amazon.com/vpc/latest/tgw/transit-gateway-quotas.html) (ancho de banda, MTU, ajuste de MSS, PMTUD)
- [Precios de AWS Transit Gateway](https://aws.amazon.com/transit-gateway/pricing/)

Estándares y documentos de proveedores

- [RFC 5880: detección de reenvío bidireccional](https://www.rfc-editor.org/rfc/rfc5880.html)
- [RFC 7296: IKEv2](https://www.rfc-editor.org/rfc/rfc7296.html), [RFC 4303: ESP](https://www.rfc-editor.org/rfc/rfc4303.html), [RFC 3948: encapsulación UDP de paquetes ESP de IPsec](https://www.rfc-editor.org/rfc/rfc3948.html)
- [RFC 4271: BGP-4](https://www.rfc-editor.org/rfc/rfc4271.html), [RFC 1997: comunidades BGP](https://www.rfc-editor.org/rfc/rfc1997.html), [RFC 6996: reserva de sistemas autónomos para uso privado](https://www.rfc-editor.org/rfc/rfc6996.html)
- [RFC 1918](https://www.rfc-editor.org/rfc/rfc1918.html), [RFC 5737](https://www.rfc-editor.org/rfc/rfc5737.html) (direcciones de ejemplo)
- [MEF 70.2: atributos del servicio SD-WAN y marco del servicio](https://www.mplify.net/resources/mef-70-2-sd-wan-service-attributes-and-service-framework/)
- [Guía de configuración de alta disponibilidad de Cisco Catalyst SD-WAN](https://www.cisco.com/c/en/us/td/docs/routers/sdwan/configuration/ha-scaling/ios-xe-17/high-availability-book-xe/m-high-availability-and-scaling.html)

Temario del examen (se usa únicamente para seleccionar los temas)

- [Guía del examen AWS Certified Advanced Networking - Specialty (ANS-C01)](https://docs.aws.amazon.com/aws-certification/latest/advanced-networking-specialty-01/advanced-networking-specialty-01.html)
- [Cisco 350-401 ENCOR](https://www.cisco.com/site/us/en/learn/training-certifications/exams/encor.html)
