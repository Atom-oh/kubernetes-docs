# VPC compartida y conectividad

> **Última actualización**: 13 de septiembre de 2026

## 1. Permisos del propietario y los participantes de una VPC compartida: un malentendido frecuente

Al adoptar una VPC compartida (subredes compartidas entre cuentas mediante AWS RAM), el error más común es pensar que «compartir significa que ambas partes ven las cosas por igual». En realidad, los permisos del propietario y de los participantes difieren considerablemente según el recurso.

| Recurso | Permiso del participante | Permiso del propietario |
|---|---|---|
| Subred | Solo describir | Completo |
| Tabla de rutas | Solo describir | Completo |
| NACL | Solo describir (las que haya creado el propietario) | Completo |
| **NAT Gateway** | **Ni siquiera puede describirlo** | Completo |
| Internet Gateway | Solo describir (no puede ni describir IGW de solo salida) | Completo |
| Asociación de TGW | No puede crearla | Solo el propietario |
| ENI | Completo para las propias | Solo describir las de otros |
| Security Group | Completo para las propias y puede usar las compartidas por el propietario | Solo describir las de otros |
| Flow Logs | Solo las ENI propias | Subred y todas las ENI posibles (pero el propietario no puede describir ni eliminar los Flow Logs creados por un participante) |

De esta tabla se derivan dos consecuencias prácticas.

**La propiedad de Flow Logs es asimétrica.** Los registros de VPC/subred administrados por el propietario central pueden coexistir con los registros de ENI de los participantes, con una finalidad, retención y responsabilidad de coste explícitas. AWS no exige una SCP que prohíba todos los registros de los participantes. Flow Logs observa el tráfico; no lo bloquea.

**Las etiquetas de VPC y subred no se comparten con los participantes.** Pruebe el descubrimiento con la versión, el modo y los permisos de IAM reales de Load Balancer Controller. Las anotaciones explícitas con ID de subred son una opción predecible; esto no significa que todos los modos de descubrimiento o versiones deban fallar.

Los grupos de seguridad solo admiten reglas Allow y las reglas de varios SG se combinan; una regla Allow amplia en un SG no se puede contrarrestar con un SG central más restrictivo. Los valores predeterminados ajustables son 60 reglas por SG (entrada/salida × IPv4/IPv6, cada una) y 5 SG por ENI, y existe la restricción **«número de reglas × SG por ENI ≤ 1,000».** Las políticas comunes de SG de Firewall Manager consumen este mismo presupuesto.

Las cuotas de ENI/SG de un participante se contabilizan en la cuenta de ese participante. Los valores predeterminados de 5,000 ENI por zona de disponibilidad y 2,500 SG por región aún pueden convertirse en cuellos de botella para cada cuenta y se pueden ajustar. Evalúe la capacidad por separado de la autorización de SG.

<span id="_2-the-real-ceiling-on-shared-vpc-—-it-s-not-the-cidr"></span>

## 2. Calcular las cuotas de VPC compartida según su alcance real

El orden de los cuellos de botella depende de la carga de trabajo. Separe las cuotas predeterminadas de las aplicadas y proyecte el crecimiento dentro de cada alcance.

| Alcance | Cuota predeterminada | Interpretación |
|---|---|---|
| Rutas no propagadas por tabla de rutas de VPC | 500 para IPv4 y 500 para IPv6; ajustable hasta 1,000 | Incluye rutas estáticas con destino a un TGW |
| Rutas propagadas por tabla de rutas de VPC | 100; fija | Límite de propagación de VGW, independiente de los totales de las tablas de TGW |
| Rutas estáticas + dinámicas combinadas entre todas las tablas de TGW | 10,000 por TGW | Contacte con SA/TAM para aumentarlo |
| Cuentas participantes por VPC | 100; ajustable | Principales con los que se comparte |
| Subredes compartidas por cuenta receptora | 100; ajustable | Combinaciones de zona de disponibilidad/finalidad |
| NAU por VPC | 64,000; ajustable hasta 256,000 | Incluye IP de Pods, ENI y entradas de listas de prefijos administradas |
| Subredes y tablas de rutas por VPC | 200 de cada una; ajustable | Cantidad de configuración |
| CIDR de IPv4 por VPC | 5; ajustable hasta 50 | Evalúe también el consumo y la fragmentación de direcciones |

**Las rutas de TGW no se propagan automáticamente a las tablas de rutas de VPC.** El propietario de la VPC añade rutas estáticas con el TGW como destino; la propagación de asociaciones se administra en las tablas de rutas de TGW. Por tanto, es incorrecto afirmar que «más de 100 prefijos de TGW detienen la VPC compartida». Que una ruta predeterminada preserve o evite la inspección depende de las asociaciones de rutas y las rutas de retorno reales.

### Grupo mínimo de VPC compartida frente a varias VPC compartidas por grupo de cargas de trabajo

Al comparar «una configuración mínima que agrupa todas las cargas de trabajo en una sola VPC compartida» con «varias VPC compartidas dedicadas, una por grupo de cargas de trabajo», hay una perspectiva fácil de pasar por alto.

- **Solo se permite una asociación de VPC para cada par TGW–VPC.** Una VPC puede conectarse a un máximo de 5 TGW. La capacidad predeterminada de una asociación es de hasta 100 Gbps en cada dirección/7.5 MPPS por zona de disponibilidad; consulte con SA/TAM para ampliar la capacidad.
- En la configuración mínima, el tráfico local y externo de todas las cargas de trabajo converge en esta única asociación; se comparten tanto el **radio de impacto** como los **límites de ancho de banda y PPS**.
- La configuración por grupo de cargas de trabajo asigna a cada VPC su propia asociación, repartiendo ese límite de rendimiento. **Poder repartir el límite de rendimiento del TGW es la verdadera razón práctica para elegir «varias VPC compartidas dedicadas».**

En última instancia, es mejor entender la elección entre una configuración mínima y otra por grupo como un **equilibrio entre «riesgo de cambios en la canalización de red central» y «riesgo de fallo compartido a nivel de VPC»**, no como «coste frente a aislamiento». Ambas dependen de la calidad de la canalización central; por tanto, el factor decisivo es medir «con qué rapidez podemos detectar y recuperar un cambio incorrecto de una ruta central» en ambas opciones. También conviene considerar una opción híbrida (configuración mínima para las cargas de trabajo generales y configuración dedicada para las cargas con mucho tráfico local/externo, separadas por zona de confianza).

### Cuotas principales de Transit Gateway

| Cuota | Valor predeterminado | Ajustable |
|---|---|---|
| TGW / cuenta | 5 | Sí |
| Asociaciones / TGW | 5,000 | Sí |
| **TGW / VPC** | **5** | **No** |
| Tablas de rutas de TGW / TGW | 20 | Sí |
| Rutas totales / TGW | 10,000 | Consulte con SA/TAM |
| **Asociaciones para el mismo par TGW–VPC** | **1** | **No** |

**Compruebe la MTU de toda la ruta.** TGW admite 8,500 bytes para las rutas de VPC/DX/Connect/peering; VPN tiene límites de túnel distintos. Al migrar de peering de VPC a TGW, pruebe los ajustes de trama jumbo de ambos extremos y PMTUD. La limitación de MSS afecta a TCP y no resuelve problemas de MTU en todos los protocolos de paquetes, como UDP.

La NAU con peering cuenta una VPC y las VPC con las que tiene peering directo en la misma región (128,000 predeterminadas, máximo de 512,000); no cuenta todas las VPC de la organización ni un grafo de conectividad transitiva.

## 3. ID de zona de disponibilidad y VPC compartida

Los nombres de zona de disponibilidad (`ap-northeast-2a`, etc.) pueden corresponder a zonas físicas distintas en diferentes cuentas. Para ubicar recursos entre cuentas, use **ID de zona de disponibilidad (`apne2-az*`)**, no los nombres de zona de disponibilidad.

Para las redes personalizadas de VPC CNI, use los ID de zona de disponibilidad para asignar las subredes del propietario a las zonas físicas de disponibilidad de los nodos participantes. Los nombres de ENIConfig deben coincidir con la anotación/etiqueta seleccionada del nodo. Si `ENI_CONFIG_LABEL_DEF=topology.kubernetes.io/zone`, use el nombre de zona de disponibilidad del nodo y coloque en la especificación el ID de subred que corresponda a ese ID de zona. Asignar a ciegas a ENIConfig el nombre de un ID de zona puede impedir la búsqueda. Un CIDR secundario por sí solo no es un límite de seguridad.

## 4. NAT Gateway regional

| Elemento | Comportamiento |
|---|---|
| Escalado | Escala automáticamente hacia arriba o abajo con un único ID; no requiere una subred pública |
| NAT privado | No compatible |
| Retraso del escalado | Hasta 60 minutos (durante ese intervalo puede haber tráfico entre zonas de disponibilidad) |
| Migración de zonal a regional | Posibles reinicios de conexiones y cambios de IP |
| Zonas de disponibilidad restringidas | **No compatible** (compruébelo de antemano) |

Regional NAT Gateway ofrece mejores límites de IP y conexiones que Zonal: Regional permite 32 IP por zona de disponibilidad (Zonal: 8), y cada IP añade 55,000 conexiones simultáneas al mismo destino (IP de destino + puerto + protocolo). Esto beneficia directamente los patrones en los que **un número reducido de destinos recibe un volumen elevado de conexiones** (por ejemplo, procesadores de pagos e integraciones de envío) porque evita el agotamiento de puertos.

Puede elegir el modo automático (AWS administra el escalado de IP/zona de disponibilidad; recomendado) o el modo manual (lo administra usted directamente). **Si necesita una IP de salida fija registrada en la lista de permitidos de un socio externo, necesita el modo manual o la integración con la política de asignación de IPv4 pública de IPAM.** Las tablas de rutas de Regional NAT Gateway admiten TGW como ruta válida, por lo que se pueden combinar la inspección central mediante TGW y Regional NAT; no son opciones mutuamente excluyentes.

## 5. TGW + Network Firewall (inspección central)

Hay dos formas de inspeccionar el tráfico este-oeste de manera centralizada.

- **Mediante una VPC de inspección**: requiere modo appliance y rutas bidireccionales.
- **Network Firewall asociado a TGW**: siempre se aplica el modo appliance.

Network Firewall **no admite el enrutamiento asimétrico.** Si la cuenta propietaria de TGW y la cuenta propietaria del firewall son distintas, encontrará restricciones relacionadas con los permisos de eliminación y la visibilidad.

Desde la perspectiva de AWS, no hay ninguna condición que haga obligatoria la inspección central. En la mayoría de los casos es razonable usar **un enfoque híbrido (controles distribuidos dentro de una zona de confianza e imposición central solo entre zonas de confianza o en rutas reguladas).**

## 6. API de AWS y endpoints de VPC

Compruebe la compatibilidad de los endpoints y las políticas de endpoint según el servicio, la región y la función. Una política de endpoint predeterminada con acceso total no concede nuevos permisos de IAM. Combine un inventario de describe-vpc-endpoint-services con la documentación del servicio, comprobaciones de DNS privado y validaciones reales de permitir/denegar.

## 7. Route 53 Profiles y DNS híbrido

Un Route 53 Profile se puede asociar a una zona alojada privada, reglas de Resolver (reenvío/sistema), un grupo de reglas de DNS Firewall, un **endpoint de VPC de interfaz** y una configuración de registro de consultas de VPC Resolver. Una VPC solo puede tener asociado un Profile.

**La regla de prioridad es el aspecto que más probablemente se malinterprete.** No es «siempre prevalece la VPC local», sino **«prevalece el nombre más específico».**

| Consulta DNS | Regla del Profile | Regla local de la VPC | Regla aplicada |
|---|---|---|---|
| `example.com` | `example.com` | `example.com` | VPC local (mismo nombre → prevalece la local) |
| `test.example.com` | `test.example.com` | `example.com` | **Profile (prevalece el nombre más específico)** |
| `marketing.example.com` | ninguna | `marketing.example.com` | VPC local |

Como muestra la segunda fila, **un nombre más específico registrado en el Profile central prevalece sobre la regla local de la carga de trabajo.** Si no se entiende esto, las cargas de trabajo pueden sufrir fallos de resolución de nombres inexplicables. **Recomendamos formalizar la regla de que «el Profile central nunca posea un nombre más específico que el espacio de nombres delegado a una carga de trabajo».** En la práctica, funciona bien centralizar la gobernanza del espacio de nombres y delegar los subdominios que dependen de él a los equipos de cargas de trabajo. Route 53 Profiles es compatible en la región de Seúl.

## 8. Opciones de conectividad entre VPC

No son opciones mutuamente excluyentes: son patrones que se eligen para cada conexión según los requisitos del tráfico.

| Opción | Adecuada para | Restricciones |
|---|---|---|
| VPC Peering | Conectividad bidireccional directa entre un número reducido de VPC | Límite de NAU con peering de 128,000 (→512,000), sin CIDR solapados y sin transitividad |
| Transit Gateway | Muchas VPC, conexiones locales y externas, inspección central | Calcule por separado los totales de las tablas de TGW, las rutas estáticas de VPC, las asociaciones por par y el rendimiento |
| PrivateLink | Exponer un servicio específico en una dirección | Coste del endpoint y operaciones permanentes para el proveedor y el consumidor |
| **VPC Lattice** | Conectividad a nivel de aplicación entre servicios y recursos, incluidos casos con CIDR solapados | Compare los protocolos, la autorización y el coste con alternativas como PrivateLink/NAT |
| Enrutamiento local dentro de la misma VPC | Misma zona de confianza y recursos que pueden compartir una VPC | Comparte los fallos de rutas/DNS/IP |

### Restricciones de VPC Lattice

A menudo se habla de Lattice con más ligereza de la que justifican sus restricciones reales.

| Elemento | Valor | Impacto |
|---|---|---|
| Asociaciones de redes de servicios por VPC | **Solo 1** | Para usar varias redes, se necesita un endpoint de VPC del tipo service-network |
| **Duración máxima de una conexión para un servicio Lattice** | **10 minutos** | Pruebe la reconexión, los reintentos y la idempotencia; distinga las conexiones de recursos |
| Tiempo de espera de inactividad del servicio Lattice | 60 s predeterminado (60–600 s) | |
| Tiempo de espera de inactividad del recurso Lattice | 350 s, sin límite de duración de conexión | Los recursos TCP tienen menos restricciones |
| Ancho de banda/RPS por servicio y zona de disponibilidad | 10 Gbps / 10,000 RPS (ampliables) | |
| Listeners por servicio / reglas por listener | 2 / 10 | |
| Redes de servicios por región | 50 | |
| MTU | 8,500 bytes | |

Evalúe por separado el tráfico de larga duración para servicios y recursos. La duración de 10 minutos de un servicio difiere del tiempo de espera de inactividad de 350 segundos de un recurso. Los listeners HTTP/HTTPS no admiten WebSockets de forma nativa; los listeners TLS o los recursos de Lattice ofrecen rutas alternativas. Elija una opción después de validar los protocolos, la reconexión, SNI, la autorización y la carga.

## 9. Opciones de inspección este-oeste

| Opción | Configuración |
|---|---|
| Controles de política distribuidos | SG/NACL/rutas/NetworkPolicy + Flow Logs |
| Firewall distribuido por VPC | Firewall independiente para cada VPC |
| Inspección central mediante TGW | Inspección masiva del tráfico en la ruta de Transit Gateway |
| **Híbrida** | Distribuida dentro de una zona de confianza y centralizada entre zonas de confianza o rutas reguladas |

Documente la propiedad, el acceso, la retención y el coste duplicado de los registros de VPC compartida. Los registros del propietario y los participantes se pueden recopilar de forma centralizada; prohibir los registros de los participantes no es un requisito previo.

## Siguiente

Una vez definidos los límites de VPC, queda decidir cómo establecer los límites de los datos y la seguridad → [Límites de datos y seguridad](./05-data-security-boundaries.md)

## Referencias

- [Cuotas de VPC](https://docs.aws.amazon.com/vpc/latest/userguide/amazon-vpc-limits.html)
- [Responsabilidades del propietario y los participantes de una VPC compartida](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-share-limitations.html)
- [Servicios compatibles con subredes compartidas](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-sharing-service-behavior.html)
- [ID de zona de disponibilidad para subredes compartidas](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-sharing-share-subnet-working-with.html)
- [Uso compartido de grupos de seguridad](https://docs.aws.amazon.com/vpc/latest/userguide/security-group-sharing.html)
- [Reglas de grupos de seguridad](https://docs.aws.amazon.com/vpc/latest/userguide/security-group-rules.html)
- [Política de grupos de seguridad comunes de Firewall Manager](https://docs.aws.amazon.com/waf/latest/developerguide/security-group-policies-common.html)
- [Política de auditoría de grupos de seguridad de Firewall Manager](https://docs.aws.amazon.com/waf/latest/developerguide/security-group-policies-audit.html)
- [Regional NAT Gateway](https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateways-regional.html)
- [Cuotas de TGW](https://docs.aws.amazon.com/vpc/latest/tgw/transit-gateway-quotas.html)
- [Descripción general de Transit Gateway](https://docs.aws.amazon.com/vpc/latest/tgw/tgw-transit-gateways.html)
- [Network Firewall asociado a TGW](https://docs.aws.amazon.com/network-firewall/latest/developerguide/tgw-firewall.html)
- [Enrutamiento asimétrico de Network Firewall](https://docs.aws.amazon.com/network-firewall/latest/developerguide/asymmetric-routing.html)
- [Cuotas de VPC Lattice](https://docs.aws.amazon.com/vpc-lattice/latest/ug/quotas.html)
- [Descripción general de VPC Lattice](https://docs.aws.amazon.com/vpc-lattice/latest/ug/what-is-vpc-lattice.html)
- [Servicios de PrivateLink compatibles](https://docs.aws.amazon.com/vpc/latest/privatelink/aws-services-privatelink-support.html)
- [VPC Peering](https://docs.aws.amazon.com/vpc/latest/peering/vpc-peering-basics.html)
- [Documento técnico sobre opciones de conectividad de VPC](https://docs.aws.amazon.com/whitepapers/latest/aws-vpc-connectivity-options/amazon-vpc-to-amazon-vpc-connectivity-options.html)
- [Inspección centralizada de VPC](https://docs.aws.amazon.com/whitepapers/latest/building-scalable-secure-multi-vpc-network-infrastructure/centralized-network-security-for-vpc-to-vpc-and-on-premises-to-vpc-traffic.html)
- [Route 53 Profiles](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/profiles.html)
- [DNS híbrido de Route 53 Resolver](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver.html)
- [Preguntas frecuentes sobre la propagación de rutas de TGW](https://aws.amazon.com/transit-gateway/faqs/)
- [Asignación de etiquetas de ENIConfig](https://docs.aws.amazon.com/eks/latest/best-practices/custom-networking.html)
- [Protocolos de listener de Lattice](https://docs.aws.amazon.com/vpc-lattice/latest/ug/listeners.html)
