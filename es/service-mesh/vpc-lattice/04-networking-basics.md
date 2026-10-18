# Fundamentos: enlace local y SNI

> **Alcance**: API de servicios y recursos de VPC Lattice y AWS Gateway API Controller; compruebe la versión seleccionada y los CRD instalados.
> **Última actualización**: 13 de septiembre de 2026

## Qué cubre este documento

- Qué son las direcciones de enlace local, por qué Lattice las eligió y los dos problemas operativos que se derivan
- Por qué SNI debe enviarse en texto sin cifrar: el problema circular de selección de certificados
- La diferencia entre la visibilidad del listener de servicio y la conectividad TCP a recursos, que tiene un modelo de acceso separado

## Direcciones de enlace local

### Qué son

Una dirección de enlace local pertenece a un rango **válido solo dentro de un único enlace** (el mismo dominio de difusión). La definición consiste en no atravesar un enrutador.

| Rango | Protocolo | Alcance | Estándar |
|---|---|---|---|
| `169.254.0.0/16` | IPv4 | Enlace local | RFC 3927 |
| `fe80::/10` | IPv6 | Enlace local | RFC 4291 |

Estos rangos existen para cumplir el requisito de que **«aunque no haya servidor DHCP ni configuración de enrutamiento, se debe poder comunicar con los vecinos inmediatos».** Por consiguiente, estas direcciones no necesitan ser únicas globalmente y se pueden reutilizar en cada enlace.

### Dónde las usa ya AWS

El patrón ya resulta familiar a quien haya utilizado EC2.

| Dirección | Finalidad |
|---|---|
| `169.254.169.254` | **EC2 Instance Metadata Service (IMDS)**: metadatos de la propia instancia y credenciales del rol de IAM |
| `169.254.170.2` | Endpoint de credenciales de tareas ECS |
| `169.254.170.23` | **EKS Pod Identity Agent** (IPv4) |
| `fd00:ec2::23` | EKS Pod Identity Agent (IPv6) |
| `169.254.171.0/24` | **VPC Lattice** (IPv4) |

AWS asigna un comportamiento especial a estas direcciones, pero no todas comparten el mismo alcance ni la misma implementación. Hay que distinguir entre el enlace local IPv4, la ULA IPv6 y los endpoints de agentes de nodo. Los estándares de direcciones por sí solos no implican una interceptación en el hipervisor.

En el caso de Lattice, describa el **comportamiento de direccionamiento específico de VPC documentado**, no una definición general del direccionamiento de enlace local ni una implementación interna inferida de AWS.

### Los rangos de Lattice: IPv4 e IPv6 son distintos por naturaleza

El nombre DNS de un servicio de VPC Lattice se resuelve en dos tipos de direcciones.

| Rango | Tipo | Naturaleza |
|---|---|---|
| `169.254.171.0/24` | IPv4 | **Enlace local** (dentro de `169.254.0.0/16`) |
| `fd00:ec2:80::/64` | IPv6 | **Unique Local Address (ULA)** (dentro de `fc00::/7`, RFC 4193), **no** es de enlace local |

> Una ULA IPv6 **no es una dirección de enlace local ni pertenece a la clase obsoleta de direcciones site-local**. Las direcciones ULA se pueden enrutar dentro de redes privadas y tienen alcance global; el alcance de una dirección y la alcanzabilidad de enrutamiento prevista son cosas distintas. Para Lattice, siga la documentación de DNS y conectividad de AWS en vez de deducir la implementación a partir del prefijo de la dirección.

Pese a la diferencia en el nombre, ambas gamas comparten las propiedades operativas importantes: **no son globalmente únicas, se reutilizan dentro de cada VPC y la infraestructura las intercepta.**

### Por qué Lattice usa este enfoque

Como se explicó en el [documento 01](./01-appmesh-vs-lattice.md), Lattice debe gestionar el tráfico **sin un sidecar**. Si no hay sidecar, ¿quién intercepta el tráfico? La respuesta son las direcciones de enlace local.

El mecanismo es el siguiente:

1. El cliente resuelve el nombre DNS del servicio de Lattice.
2. DNS devuelve una dirección de `169.254.171.x` (o del rango `fd00:ec2:80::`).
3. El cliente se conecta normalmente a esa dirección; **la aplicación no sabe que existe Lattice**.
4. Los paquetes con destino a ese rango se **dirigen a un endpoint de entrada de Lattice dentro de la VPC**.
5. Lattice evalúa las reglas del listener, elige un Target y reenvía el tráfico a la IP real del Pod.

El tráfico atraviesa la infraestructura sin modificar el código de la aplicación, las especificaciones de los Pods ni las reglas iptables. **Este rango de direcciones permite a Lattice conservar un punto de interceptación del tráfico mientras elimina el sidecar.**

## Dos problemas derivados de elegir direcciones de enlace local

El diseño es elegante, pero tiene costes. El plan de migración debe abordar ambos problemas.

### Problema 1: conflicto con la interceptación iptables de Envoy

Las mallas con sidecar (App Mesh, Istio) **usan un contenedor de inicialización para instalar reglas iptables** que dirigen el tráfico del Pod al proxy. Normalmente, se trata de «redirigir todo el tráfico saliente de este Pod al puerto de Envoy».

Un REDIRECT saliente amplio puede capturar el tráfico de Lattice. Que esto sea un problema depende de la política de la malla, las rutas configuradas y el diseño de firma. Verifíquelos antes de añadir una excepción CIDR explícita.

La solución es **registrar una excepción CIDR**: excluir el rango de Lattice de la interceptación para que el tráfico evite Envoy.

| Malla | Cómo registrar la excepción |
|---|---|
| App Mesh | Añadir el rango de Lattice a la lista de CIDR que se excluyen del tráfico saliente en la configuración del CNI/contenedor de inicialización de App Mesh |
| Istio | Añadir el rango de Lattice a la anotación `traffic.sidecar.istio.io/excludeOutboundIPRanges` |

Mientras coexistan los sistemas, verifique la política de salida de la malla, los destinos externos registrados, la ruta de firma y ambas familias de direcciones. Algunas configuraciones de Envoy reenvían los destinos desconocidos, mientras que las configuraciones restringidas los rechazan. Excluir un CIDR es un diseño deliberado para evitar la malla, no una prueba de que todas las mallas en coexistencia fallen sin esa excepción.

También es posible el uso inverso. El patrón de proxy de salida del [documento 03](./03-auth-flow.md) usa iptables para seleccionar **solo el rango de Lattice** y enviarlo al proxy de firma: la misma herramienta empleada con el propósito contrario.

### Problema 2: pierden sentido la observabilidad y el control basados en IP de destino

Las direcciones de enlace local **no son globalmente únicas ni identifican un servicio.** Eso rompe las suposiciones de las herramientas operativas existentes.

| Qué deja de funcionar | Por qué |
|---|---|
| **Identificar al par mediante la IP de destino de los registros de flujo** | El destino solo aparece como `169.254.171.x`. No se puede saber a qué servicio de Lattice correspondía |
| **Reglas de salida de Security Group basadas en CIDR de destino** | Todos los servicios de Lattice están en el mismo rango. No se puede permitir/denegar por servicio |
| **NetworkPolicy basada en IP de destino** | Igual que arriba. `ipBlock` de Kubernetes NetworkPolicy no distingue servicios de Lattice |
| **Paneles y alarmas de supervisión basados en IP** | La atribución basada solo en IP no permite identificar servicios estables de manera fiable; enriquézcala con DNS, ID de solicitud y registros con información del servicio |
| **Inventario de activos basado en rangos de IP** | Los servicios de Lattice no aparecen como direcciones IP en el inventario |

**La alternativa consiste en trasladar la capa de control.**

- **Exprese la autorización mediante políticas de autorización, no IP**: condiciones de principal, ruta, método y encabezados ([documento 03](./03-auth-flow.md)).
- **Use los registros de acceso de Lattice, no los de flujo, para observar**: estos indican a qué servicio se llamó.
- **Abra los grupos de seguridad mediante listas de prefijos administradas, no CIDR** (a continuación).

No se trata de cambiar una herramienta por otra, sino de un **cambio en el modelo de control**: de «control por IP y puerto» a «control por identidad y política». Gran parte de los recursos operativos existentes del equipo de redes simplemente no funciona en este rango. En el sector financiero, esto puede convertirse en una cuestión de límites de responsabilidad organizativa, por lo que debe acordarse pronto con el equipo de redes.

### Abrir los grupos de seguridad mediante listas de prefijos

Para recibir tráfico de Lattice, los grupos de seguridad de los nodos deben permitirlo. En lugar de escribir CIDR directamente, la opción correcta es usar **listas de prefijos administradas por AWS**.

| Nombre de la lista de prefijos | Finalidad |
|---|---|
| `com.amazonaws.<region>.vpc-lattice` | IPv4 |
| `com.amazonaws.<region>.ipv6.vpc-lattice` | IPv6 |

```bash
# Read-only lookup; apply the reviewed ingress rule through CDK/Terraform.
: "${AWS_REGION:?Set the reviewed AWS Region}"
aws ec2 describe-managed-prefix-lists --region "$AWS_REGION" \
  --query "PrefixLists[?PrefixListName=='com.amazonaws.$AWS_REGION.vpc-lattice'].{Id:PrefixListId,Name:PrefixListName}" \
  --output json
```

En la infraestructura como código revisada, permita la lista de prefijos de Lattice correspondiente **solo en los puertos y protocolos necesarios de destino y comprobación de estado**, en el SG real de destino (del nodo o del Pod, según la configuración). Evite la entrada de todos los protocolos. Verifique por separado los SG asociados con el cliente/la red de servicios; la consulta anterior no modifica ningún SG.

## SNI (Server Name Indication)

### Por qué hay que enviar el dominio en texto sin cifrar

SNI es una extensión TLS que transporta **el nombre de dominio del servidor al que se desea acceder en texto sin cifrar dentro de `ClientHello`.** Puede parecer extraño incluir el dominio de destino en texto sin cifrar en el primer mensaje de un protocolo de cifrado, pero existe una dependencia circular inevitable.

**El problema del huevo y la gallina:**

1. Para iniciar una conexión TLS, el servidor debe elegir **qué certificado presentar**.
2. Los certificados están vinculados a dominios (el certificado de `api.example.com` es distinto del de `www.example.com`).
3. Si una misma dirección IP:puerto sirve a varios dominios, el servidor **debe saber qué dominio quiere el cliente** para elegir un certificado.
4. Pero el dominio que quiere el cliente está en el encabezado HTTP `Host`, y **ese encabezado `Host` llega cifrado dentro de TLS**.
5. Por tanto, **para iniciar el cifrado hace falta conocer el dominio, pero para conocer el dominio hace falta haber iniciado el cifrado**.

TLS normal envía SNI en ClientHello para que el servidor pueda seleccionar un certificado antes de leer HTTP. No es el único diseño concebible: ECH cifra un ClientHello interno con una clave obtenida por adelantado. TLS passthrough de Lattice actualmente requiere SNI visible y no admite ECH/ESNI.

En resumen, **que SNI se exponga en texto sin cifrar no es un error de diseño, sino una solución deliberada a la circularidad.** Gracias a esta solución, **los dispositivos intermedios que no terminan TLS aún pueden conocer el dominio de destino**; esto permite el enrutamiento TLS Passthrough.

### Qué hace Lattice con SNI

En un listener TLS Passthrough, Lattice no termina TLS. Entonces, **¿cómo elige el Target?** Mediante SNI. Lee el campo SNI sin cifrar de `ClientHello` y enruta únicamente con ese dato.

## Listener HTTPS frente a TLS Passthrough: qué puede ver Lattice

| Información | Listener HTTPS (TLS Terminate) | TLS Passthrough |
|---|---|---|
| **SNI (dominio)** | ✅ | ✅ |
| **Ruta HTTP** | ✅ | ❌ |
| **Método HTTP** | ✅ | ❌ |
| **Encabezados HTTP** | ✅ | ❌ |
| **Cadena de consulta** | ✅ | ❌ |
| **Encabezado `Authorization` (SigV4)** | Legible; admite solicitudes de IAM autenticadas | Cifrado; no se dispone de identidad autenticada mediante SigV4 |
| **Cuerpo de la solicitud** | ✅ (pasa a través) | ❌ |
| **Enrutamiento basado en ruta/encabezado** | ✅ | ❌ (solo SNI) |
| **Claves de condición para ruta/método/encabezado** | ✅ | ❌ |
| **Detalles HTTP en los registros de acceso** | ✅ | Limitados |
| **Se conserva el cifrado de extremo a extremo** | ❌ (Lattice lo termina una vez) | ✅ |
| **mTLS del propio endpoint** | ❌ (Lattice no solicita certificados de cliente) | ✅ (el propio endpoint lo hace) |
| **Protocolo de Target Group** | HTTP / HTTPS | **TCP** |
| **Recurso de Gateway API** | `HTTPRoute` / `GRPCRoute` (`tls.mode: Terminate`) | `TLSRoute` (`tls.mode: Passthrough`) |

Esta tabla muestra la compensación más importante de esta sección.

> **TLS passthrough conserva TLS del endpoint y puede transportar mTLS del endpoint, pero Lattice no puede inspeccionar campos HTTP ni autenticar sus encabezados SigV4.** Las políticas de autorización anónimas basadas en el contexto de red son distintas de la identidad autenticada del solicitante.

Elija el límite de confianza **para cada listener/ruta**, sin afirmar que un servicio no puede usar tipos distintos de listener. TLS passthrough puede usar políticas de autorización anónimas basadas en el contexto de red, pero no proporciona la identidad del solicitante firmada. Configure por separado el protocolo del backend: un listener HTTPS puede reenviar HTTP o HTTPS, y Lattice no valida los certificados de destino en una conexión HTTPS al destino.

## Protocolos que admite Lattice

| Protocolo del listener | Protocolo de aplicación | Protocolo de Target Group |
|---|---|---|
| **HTTP** | HTTP/1.1 | HTTP |
| **HTTPS** | HTTP/1.1, HTTP/2, gRPC (**negociado mediante ALPN**; HTTP/1.1 cuando no hay ALPN) | HTTP / HTTPS |
| **TLS_PASSTHROUGH** | (Lattice no lo interpreta) | **TCP** |

**No hay un listener TCP sin procesar independiente.** TCP solo existe como protocolo de Target Group para TLS_PASSTHROUGH.

### Listeners de servicio y conectividad TCP a recursos

Los **listeners de servicio** de VPC Lattice exponen HTTP, HTTPS y TLS_PASSTHROUGH. Por separado, las **configuraciones y gateways de recursos admiten recursos TCP**. Las políticas de autorización de red de servicios no se aplican a esas configuraciones de recursos; evalúe por separado cómo se comparten, los controles de endpoint/red y la autenticación de recursos.

Elija el modelo de servicio si necesita el enrutamiento/autenticación HTTP compatible y evalúe la conectividad a recursos si necesita acceso TCP sin esas funciones de servicio. La ausencia de un **listener de servicio** TCP sin procesar es un límite de capacidad de API, no una imposibilidad matemática de redes.

- El enrutamiento de servicios HTTP/HTTPS usa los campos de aplicación admitidos.
- TLS passthrough requiere que SNI coincida con el dominio personalizado configurado.
- La conectividad a recursos TCP usa una configuración de recursos/gateway de recursos y su propio modelo de asociación/acceso.

Para los protocolos de destino de servicio HTTP/2 y gRPC, **AWS requiere un listener HTTPS**; el transporte del grupo de destino puede ser HTTP o HTTPS, según sea compatible. No confunda HTTP/2 en texto sin cifrar en un backend con el acceso del cliente h2c en texto sin cifrar a un listener de servicio. Una base de datos que negocia TLS después de mensajes iniciales en texto sin cifrar también es distinta de un listener que espera ClientHello desde el principio.

> La restricción publicada de los listeners de servicio no excluye el acceso a recursos TCP. Evalúe los gateways de recursos, la conectividad privada existente o un NLB según los modelos de enrutamiento y autorización requeridos.

Consulte las referencias actuales de [configuración de recursos](https://docs.aws.amazon.com/vpc-lattice/latest/ug/resource-configuration.html) y [listener TLS](https://docs.aws.amazon.com/vpc-lattice/latest/ug/tls-listeners.html). Compruebe por separado la compatibilidad del controlador con esas API de AWS; no equivale a comprobar la disponibilidad del servicio.

## Nota de seguridad: implicaciones de SNI en texto sin cifrar

### Qué queda expuesto

TLS protege el contenido de la comunicación, pero **los observadores de la ruta pueden ver el dominio al que se conectó el cliente**. Esta es una propiedad general de TLS y SNI, no una característica de Lattice.

Como esta comunicación ocurre dentro de una VPC, los observadores externos no son el motivo de preocupación, pero conviene tener presentes dos cosas:

- **Los observadores internos pueden ver las relaciones entre llamadas de servicio.** Cualquiera que pueda observar el tráfico dentro de la VPC puede reconstruir el grafo de llamadas a partir de SNI.
- **Las IP de destino de los registros de flujo no aportan información, pero SNI sí.** Esto también significa que el problema de «la observabilidad basada en IP de destino deja de funcionar» se puede compensar en parte mediante la observación basada en SNI.

### ECH: respuesta a la exposición de SNI en texto sin cifrar

**Encrypted Client Hello (ECH)** es un estándar que cifra el propio `ClientHello` para evitar que se exponga SNI. Distribuye con antelación por DNS la clave pública del servidor y cifra con ella las partes confidenciales de `ClientHello`, **usando DNS para sortear** el problema del huevo y la gallina descrito anteriormente.

::: note Requisito de TLS passthrough
AWS indica explícitamente que los listeners TLS no admiten ECH ni ESNI, requieren un dominio personalizado y usan SNI para seleccionar el servicio. Antes de migrar protocolos de larga duración, compruebe los límites de inactividad/duración y las comprobaciones de estado TCP del destino.
:::

### Impacto en entornos con dispositivos de control basados en SNI

Muchas organizaciones, incluidas las del sector financiero, operan **dispositivos que controlan el tráfico según SNI** (listas de permitidos de dominios, registros basados en SNI e imposición de políticas por dominio). La adopción de Lattice afecta a esos entornos de dos maneras.

| Configuración | Impacto desde la perspectiva del dispositivo SNI |
|---|---|
| **Listener HTTPS** | El SNI que envía el cliente es el dominio del servicio de Lattice. Hay que **añadir el dominio de Lattice (`*.vpc-lattice-svcs.<region>.on.aws` o el dominio personalizado) a las listas de permitidos existentes.** Además, el segmento Lattice→Target queda fuera de la visibilidad del dispositivo |
| **TLS Passthrough** | SNI se conserva de extremo a extremo, por lo que encaja bien con el control basado en SNI. Pero se renuncia a IAM Auth |
| **Rango de enlace local** | Se neutralizan los dispositivos de control basados en IP de destino (véase «Problema 2» arriba) |

**Si usa un dominio personalizado, aquí se encuentra con el problema del encabezado Host del [documento 03](./03-auth-flow.md).** Si añade un dominio personalizado para controlar SNI, pero la lógica de firma sigue usando el dominio generado por Lattice, recibirá errores 403. La introducción de un dominio personalizado debe resolver a la vez el control SNI, el valor Host firmado y la administración de certificados.

## Resumen

- Una dirección de enlace local es una **marca que significa «la infraestructura gestiona este paquete».** Pertenece a la misma familia que IMDS y Pod Identity Agent, y es el mecanismo que permite a Lattice intervenir en el tráfico sin un sidecar.
- IPv4 usa `169.254.171.0/24` (enlace local), pero **IPv6 usa `fd00:ec2:80::/64`, una ULA, no una dirección de enlace local.** El tráfico de Lattice debe enrutarse dentro de la VPC; el alcance del enlace no basta.
- Valide el enrutamiento durante la coexistencia y la atribución con información del servicio; use IaC revisada de listas de prefijos y correlacione los registros de red y aplicación.
- SNI va en texto sin cifrar debido al **problema circular de selección de certificados**; es una concesión deliberada que también permite el enrutamiento TLS Passthrough.
- Sin terminar TLS, Lattice no puede autenticar los encabezados HTTP SigV4 cifrados; las políticas de autorización anónimas basadas en el contexto de red y la autenticación del endpoint siguen siendo controles separados.
- TCP sin procesar no es un protocolo de listener de servicio; las configuraciones de recursos TCP son un modelo de conectividad compatible aparte.

A continuación: [Migración de identidad de cargas de trabajo](./05-spiffe-to-iam.md) analiza hasta dónde puede IAM asumir las funciones que tenía SPIRE.

## Referencias

- [Gestión de la resolución DNS con Amazon VPC Lattice y recursos de VPC](https://aws.amazon.com/blogs/networking-and-content-delivery/managing-dns-resolution-with-amazon-vpc-lattice-and-vpc-resources/)
- [Estrategias y prácticas recomendadas para migrar DNS de Amazon VPC Lattice](https://aws.amazon.com/blogs/networking-and-content-delivery/amazon-vpc-lattice-dns-migration-strategies-and-best-practices/)
- [AWS Gateway API Controller: implementar el controlador (configuración de la lista de prefijos)](https://www.gateway-api-controller.eks.aws.dev/latest/guides/deploy/)
- [AWS Gateway API Controller: TLS Passthrough](https://www.gateway-api-controller.eks.aws.dev/latest/guides/tls-passthrough/)
- [Habilitar cifrado de extremo a extremo con TLS passthrough de Amazon VPC Lattice](https://aws.amazon.com/blogs/networking-and-content-delivery/enabling-end-to-end-encryption-with-amazon-vpc-lattice-tls-passthrough/)
- [Listeners HTTPS para servicios de VPC Lattice](https://docs.aws.amazon.com/vpc-lattice/latest/ug/https-listeners.html)
- [RFC 3927: direcciones IPv4 de enlace local](https://datatracker.ietf.org/doc/html/rfc3927) / [RFC 4193: direcciones IPv6 de unidifusión locales únicas](https://datatracker.ietf.org/doc/html/rfc4193)
- [RFC 6066: extensiones TLS: Server Name Indication](https://datatracker.ietf.org/doc/html/rfc6066)
- [Fundamentos de redes, parte 2: capa de transporte y TLS](../../basics/06-network-fundamentals-part2.md)


- [Grupos de destino y versiones de protocolo](https://docs.aws.amazon.com/vpc-lattice/latest/ug/target-groups.html): comportamiento de certificados HTTPS de destino y requisitos de listeners HTTP/2/gRPC

También importan los límites operativos de los listeners TLS: solo se admite una regla de reenvío predeterminada, se excluyen los destinos Lambda, la duración de las conexiones se limita a 10 minutos y el tiempo de espera de inactividad del servicio se puede configurar entre 60 y 600 segundos. **Las comprobaciones de estado TCP de Target Group están deshabilitadas de forma predeterminada**; para habilitarlas, se necesita un protocolo/versión de sonda compatible. Antes de adoptar conexiones de larga duración, compruebe los ajustes actuales de la API/región.
