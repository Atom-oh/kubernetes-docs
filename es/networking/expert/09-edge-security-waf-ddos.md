# 09. Seguridad perimetral: WAF y defensa contra DDoS

> **Última actualización**: 19 de noviembre de 2026
> **Límites del laboratorio**: Solo es un ejercicio de escritorio. Escribirás en papel un plan de reglas en modo Count; este cuaderno no crea ninguna ACL web, distribución, suscripción a Shield, balanceador de carga ni objeto de Kubernetes, y no envía tráfico de ataque ni de carga a ningún sistema.
> **Estado de verificación**: Se consultaron las guías para desarrolladores de AWS WAF, AWS Shield y Amazon CloudFront, la referencia de la API de AWS WAF, el documento técnico de AWS sobre resiliencia frente a DDoS, RFC 4987 y la página de OWASP Top 10 2021. No se implementó ninguna regla ni se midió tráfico; las cifras del ejercicio corresponden a un escenario resuelto, no a observaciones.

Al terminar este cuaderno, deberías poder nombrar la capa a la que apunta un ataque, indicar **en qué punto de la ruta** se detiene y mediante qué control, elaborar un plan de reglas de AWS WAF que empiece en modo Count con expectativas medidas y un desencadenante de reversión, y explicar por qué un origen al que se puede acceder directamente desde Internet hace que todos los controles perimetrales sean opcionales para el atacante.

Este capítulo se basa en la ruta del perímetro al origen de [workbook 08](./08-cdn-edge-delivery.md#edge-origin-path) (CloudFront → origen de VPC → ALB interno) y no vuelve a enseñarla. Los firewalls de host en el propio servidor se explican en [beginner 06](../beginner/06-firewalls-host-security.md). La ubicación de WAF, los problemas con el orden de las reglas, los límites de inspección del cuerpo de las solicitudes, las IP de cliente reenviadas y la lista completa de campos de registro se explican en [WAF, Edge and API Security](../../security/14-waf-edge-api-security.md); este cuaderno enlaza a esas secciones en vez de repetirlas. Las reglas a nivel de Pod se explican en [Network Policies](../../security/04-network-policies.md), y el lado de Ingress, en [AWS Load Balancer Controller](../03-aws-lb-controller.md). Los ejemplos del documento del controlador usan `alb.ingress.kubernetes.io/scheme: internet-facing`; **en el diseño perimetral de este curso, el ALB es interno** (`alb.ingress.kubernetes.io/scheme: internal`) y está detrás de un origen de VPC de CloudFront, así que lee esos ejemplos cambiando ese valor. El enrutamiento anycast con BGP se explica en [workbook 02](./02-routing-policy-convergence.md), y el protocolo de enlace TCP, en [Network Fundamentals Part 2](../../basics/06-network-fundamentals-part2.md).

**Preparación:** un editor de texto y la documentación de AWS. No necesitas una cuenta de AWS. Crear el diseño por tu cuenta genera cargos por AWS WAF (por ACL web, por regla y por millón de solicitudes, además de tarifas adicionales para Bot Control, la prevención de toma de control de cuentas, el grupo de reglas Anti-DDoS —salvo que esté cubierto por Shield Advanced—, CAPTCHA y Challenge, la capacidad que supere 1.500 WCU y el registro), CloudFront y el balanceador de carga; además, si te suscribes, AWS Shield Advanced (la página de precios indica una tarifa mensual que comienza en 3.000 USD con un plazo de un año). **Es responsabilidad del alumno asumir esos costos y realizar la limpieza.** Nunca hagas pruebas con tráfico de ataque, ni siquiera contra tus propios recursos, sin un plan de pruebas escrito y aprobado.

## 1. Lee buscando una respuesta

El alcance del examen solo determina qué leer. Las cifras y el comportamiento se basan en las páginas oficiales de la primera columna.

| Lectura | Correspondencia con el alcance del examen | Pregunta que debes responder con tus propias palabras |
|---|---|---|
| [Descripción general de AWS Shield Standard](https://docs.aws.amazon.com/waf/latest/developerguide/ddos-standard-summary.html), [Lógica de mitigación de Shield para CloudFront y Route 53](https://docs.aws.amazon.com/waf/latest/developerguide/ddos-event-mitigation-logic-continuous-inspection.html) | ANS-C01, dominio 4: Seguridad de redes, cumplimiento y gobernanza, tarea 4.1 (protección de los flujos de tráfico entrante con AWS WAF y AWS Shield) | ¿Por qué una inundación SYN dirigida a una distribución de CloudFront no se convierte en una inundación SYN en el origen? |
| [Uso de las acciones de reglas](https://docs.aws.amazon.com/waf/latest/developerguide/waf-rule-action.html), [Configuración de reglas basadas en tasas](https://docs.aws.amazon.com/waf/latest/developerguide/waf-rule-statement-type-rate-based-high-level-settings.html), [Etiquetado de solicitudes web](https://docs.aws.amazon.com/waf/latest/developerguide/waf-labels.html) | Dominio 4, tarea 4.1 (modelos de amenazas, estrategias de mitigación) | ¿Qué acciones finalizan la evaluación de una solicitud y cuáles permiten que las reglas posteriores la vean? |
| [Capacidades de AWS Shield Advanced](https://docs.aws.amazon.com/waf/latest/developerguide/ddos-advanced-summary-capabilities.html), [Grupo de reglas administradas Anti-DDoS](https://docs.aws.amazon.com/waf/latest/developerguide/aws-managed-rule-groups-anti-ddos.html) | Dominio 4, tarea 4.1 | ¿Qué aporta Shield Advanced que no ofrezca Shield Standard y qué se necesita antes de usarlo? |
| [Pruebas y ajuste de las protecciones](https://docs.aws.amazon.com/waf/latest/developerguide/web-acl-testing.html), [Registro del tráfico de ACL web](https://docs.aws.amazon.com/waf/latest/developerguide/logging.html), [Visualización de solicitudes muestreadas](https://docs.aws.amazon.com/waf/latest/developerguide/web-acl-testing-view-sample.html) | Dominio 4, tarea 4.2 (validar y auditar la seguridad con supervisión y registros) | ¿Qué campo del registro indica que una regla en modo Count habría coincidido? |
| [OWASP Top 10 2021](https://owasp.org/Top10/2021/) | Dominio 4, tarea 4.1 (amenazas de seguridad comunes) | ¿Cuáles de las diez categorías puede reducir un WAF perimetral y cuáles solo puede corregir la aplicación? |

Después de leer, dibuja la ruta desde el cliente hasta el Pod e indica dónde se detiene cada ataque de la sección 2. Una revisión del diseño que no pueda señalar el lugar donde se detiene un ataque no ha cubierto ese ataque.

## 2. Capas de amenazas: qué agota cada ataque

Es más fácil ubicar los ataques si te preguntas qué recurso intentan agotar: el ancho de banda del enlace, el estado de las conexiones, la CPU para TLS o el trabajo de la aplicación.

| Capa | Ataque | Mecanismo | Qué agota |
|---|---|---|---|
| L3 | **Reflexión UDP** | El atacante falsifica la dirección de la víctima como origen de solicitudes UDP pequeñas a servidores de terceros (DNS, NTP, SSDP, CLDAP, Memcached, CharGen, QOTD), que envían respuestas mucho más grandes a la víctima. Para DNS, el documento técnico de AWS da un factor de amplificación de entre 28 y 54 veces | Capacidad del enlace y de la red |
| L4 | **Inundación SYN** | Muchos SYN que nunca completan el protocolo de enlace de tres vías ([Part 2](../../basics/06-network-fundamentals-part2.md)) | La cola de conexiones semiabiertas del listener ([RFC 4987](https://www.rfc-editor.org/rfc/rfc4987.html), §2.2); el ataque no necesita llenar el enlace |
| L6 | **Abuso de TLS** | Datos ilegibles presentados como un protocolo de enlace, renegociación interminable o apertura y cierre rápidos de sesiones | CPU del lado que termina TLS |
| L7 | **Inundación HTTP** | Solicitudes que parecen las de un usuario legítimo, a veces imitando la navegación humana | Capacidad de la aplicación; pueden bastar volúmenes bajos |
| L7 | **Elusión de caché** | Una inundación HTTP que varía la cadena de consulta para que la CDN tenga que reenviar cada solicitud ([workbook 08](./08-cdn-edge-delivery.md), sección 5) | Capacidad del origen detrás de la caché |
| L7 | **Intentos de explotación** | Cargas útiles dirigidas a clases de vulnerabilidades conocidas (sección 4) | Confidencialidad e integridad, no capacidad |
| L7 | **Bots, extracción automatizada de datos, relleno de credenciales** | Robo automatizado de contenido e intentos de inicio de sesión con pares filtrados de nombres de usuario y contraseñas | Lógica de negocio y cuentas; el documento técnico señala que no son estrictamente DDoS, aunque se le parecen |

De esto se desprenden dos consecuencias. Primero, un ataque de reflexión requiere la capacidad de falsificar direcciones de origen, y las redes que aplican validación de direcciones de origen ([BCP 38](https://www.rfc-editor.org/info/bcp38)) lo impiden. Segundo, un ataque L7 es tráfico bien formado, así que ningún control que solo compruebe la validez de los paquetes puede detenerlo: se necesita un control que lea la solicitud.

## 3. Dónde se detiene cada ataque

| Ataque | Se detiene en | Mecanismo | Responsable |
|---|---|---|---|
| Reflexión UDP | Perímetro de CloudFront | Las mitigaciones de Shield solo dejan pasar tráfico válido para aplicaciones web; CloudFront acepta únicamente conexiones bien formadas | AWS (automático) |
| Inundación SYN | Perímetro de CloudFront | El proxy TCP SYN de Shield verifica el protocolo de enlace (cookies SYN sin estado) antes de que una conexión llegue al servicio | AWS (automático) |
| Abuso de TLS | Perímetro de CloudFront | TLS termina en el perímetro, por lo que el origen solo ve solicitudes bien formadas ([workbook 08](./08-cdn-edge-delivery.md), sección 7) | AWS (automático) |
| Inundación HTTP, elusión de caché | ACL web de WAF en el perímetro | Reglas basadas en tasas, grupo de reglas administradas Anti-DDoS, Challenge | Tú |
| Intentos de explotación | ACL web de WAF y luego la aplicación | Grupos de reglas administradas como primer filtro; validación de entradas y autorización en la aplicación | Tú |
| Relleno de credenciales | WAF (prevención de toma de control de cuentas) y luego la aplicación | Comprobaciones de credenciales robadas y límites de volumen de inicios de sesión; MFA y política de bloqueo en la aplicación | Tú |
| Cualquier ataque dirigido directamente al origen | **En ninguna parte**, salvo que el origen no tenga una ruta pública | Ocultamiento del origen (sección 8) | Tú |

Las **cookies SYN** permiten que un listener no conserve estado para una conexión en estado SYN-RECEIVED: el servidor codifica lo que necesita en el número de secuencia de su SYN-ACK y reconstruye el estado cuando vuelve un ACK válido ([RFC 4987](https://www.rfc-editor.org/rfc/rfc4987.html), §3.6). El documento técnico de AWS describe la mitigación sin estado de inundaciones SYN de los servicios perimetrales como la verificación de las conexiones entrantes mediante cookies SYN antes de reenviarlas, y señala que los sistemas operativos modernos activan las cookies SYN de forma predeterminada. CloudFront también mantiene conexiones persistentes con el origen, por lo que una conexión nueva de un usuario no implica una conexión nueva al origen. Ni AWS WAF ni un grupo de seguridad sustituyen a este mecanismo: AWS WAF inspecciona solicitudes HTTP, así que solo actúa cuando ya existe una conexión; un grupo de seguridad permite o deniega el tráfico según el origen, el protocolo y el puerto, pero no limita la tasa.

La **absorción** requiere una capacidad superior a la de la inundación. La página de AWS sobre la mitigación de Shield para CloudFront dice que CloudFront combina la dirección del tráfico DNS y el enrutamiento anycast para mitigar ataques cerca del origen y aislar fallos. Esto concuerda con workbook 08: DNS dirige a cada usuario a un POP, y el tráfico de ataque llega a muchos POP en vez de a un solo origen. La mitigación de Shield está integrada con los servicios perimetrales, y el documento técnico afirma que esto reduce el tiempo de mitigación de minutos a menos de un segundo.

**Costo del tráfico rechazado:** el documento técnico indica que no se te cobran las solicitudes HTTP ni la transferencia de datos saliente de las solicitudes que CloudFront o AWS WAF rechazan. Una solicitud bloqueada por WAF genera un costo de inspección de solicitudes de WAF, no de capacidad del origen.

**Punto práctico:** el perímetro detiene el volumen, pero no decide quién puede hacer qué. AWS WAF reduce la superficie de explotación y abuso, pero [la autorización sigue siendo responsabilidad de la aplicación](../../security/14-waf-edge-api-security.md) (sección 1 de ese capítulo). Un diseño en el que WAF sea el único control de una acción de negocio tiene un único punto de fallo.

## 4. OWASP Top 10 2021 y lo que puede hacer un WAF perimetral

[OWASP Top 10 2021](https://owasp.org/Top10/2021/) incluye diez categorías de riesgos para aplicaciones web, de A01 a A10. Desde entonces, OWASP publicó una edición de 2025; este cuaderno usa la lista de 2021. AWS describe su conjunto de reglas principal como protección contra «algunas de las vulnerabilidades de alto riesgo y más comunes» descritas en publicaciones de OWASP, como Top 10. Trata las reglas administradas como un filtro para patrones de solicitudes conocidos, no como cobertura de una categoría.

| Categoría de 2021 | Aporte del WAF perimetral (ejemplos de grupos de reglas administradas de AWS) | Qué solo puede hacer la aplicación o la plataforma |
|---|---|---|
| A01 Control de acceso roto | Poco: la solicitud parece legítima | Autorización a nivel de objeto en cada solicitud |
| A02 Fallos criptográficos | Ninguno en WAF | TLS en cada tramo ([workbook 08](./08-cdn-edge-delivery.md), sección 7), gestión de claves y datos |
| A03 Inyección | Reglas contra la inyección SQL (`AWSManagedRulesSQLiRuleSet`, 200 WCU) y reglas contra el scripting entre sitios en el conjunto de reglas principal | Consultas parametrizadas, codificación de salida |
| A04 Diseño inseguro | Ninguno | Modelado de amenazas, límites de negocio |
| A05 Configuración incorrecta de seguridad | Indirecto | Revisión de la configuración; un origen accesible públicamente es una configuración incorrecta del diseño perimetral (sección 8) |
| A06 Componentes vulnerables y obsoletos | Entradas maliciosas conocidas (`AWSManagedRulesKnownBadInputsRuleSet`, 200 WCU), por ejemplo, patrones de Log4j y deserialización de Java | Aplicar parches; una regla de WAF solo da tiempo |
| A07 Fallos de identificación y autenticación | Prevención de toma de control de cuentas (`AWSManagedRulesATPRuleSet`, 50 WCU, de pago) | MFA, bloqueo, gestión de sesiones |
| A08 Fallos de integridad del software y los datos | Ninguno | Artefactos firmados, controles de la cadena de suministro |
| A09 Fallos de registro y supervisión de seguridad | Los registros y las métricas de WAF son una de las fuentes de datos (sección 9) | Correlación y alertas entre capas |
| A10 Falsificación de solicitudes del lado del servidor (SSRF) | Reglas del conjunto principal que buscan intentos de exfiltrar metadatos de EC2 (`EC2MetaDataSSRF_*`) | Control de salida y validación de URL en la aplicación |

El conjunto de reglas principal (`AWSManagedRulesCommonRuleSet`) cuesta 700 WCU. También aplica límites de tamaño; por ejemplo, `SizeRestrictions_BODY` bloquea cuerpos de solicitud de más de 8 KB, una causa común de falsos positivos en rutas de carga (sección 10).

## 5. El modelo de AWS WAF

**ACL web.** La consola de AWS WAF ahora llama a una ACL web **paquete de protección (ACL web)**; en este cuaderno se usa «ACL web». Una ACL web contiene reglas y grupos de reglas, además de una **acción predeterminada** (Allow o Block) para cualquier solicitud que ninguna regla termine de evaluar. Cada recurso se puede asociar con un máximo de una ACL web, y una misma ACL web puede proteger muchos recursos.

**Alcance.** Una ACL web para CloudFront es **global**: tiene la región fija US East (N. Virginia). Con la CLI se pasan `--scope=CLOUDFRONT --region=us-east-1`, y con la API y los SDK se usa el endpoint `us-east-1`. Una ACL web asociada a una distribución de CloudFront no se puede asociar también a otro tipo de recurso; un recurso regional, como un ALB, necesita una ACL web `REGIONAL` independiente en su propia región.

**Reglas, grupos de reglas y orden.** Una regla es una instrucción y una acción. Un grupo de reglas es un conjunto reutilizable de reglas, propio o de un **grupo de reglas administradas** (AWS Managed Rules, vendedores de AWS Marketplace). AWS WAF evalúa las reglas desde la prioridad numérica más baja hasta que una regla termina la evaluación o se agotan las reglas; dentro de un grupo de reglas, usa las prioridades propias de ese grupo. Los problemas con el orden (un Allow amplio al principio, eximir un grupo entero) se explican en [security/14, sección 3](../../security/14-waf-edge-api-security.md).

**Acciones:**

| Acción | ¿Finaliza la evaluación? | Comportamiento |
|---|---|---|
| Allow | Sí | Reenvía la solicitud al recurso protegido; tus propias reglas pueden insertar encabezados de solicitud personalizados |
| Block | Sí | El recurso protegido responde `403 (Forbidden)` de forma predeterminada; tus propias reglas pueden definir una respuesta personalizada |
| Count | No | Cuenta la coincidencia y continúa con la regla siguiente; puede añadir etiquetas y encabezados de solicitud personalizados |
| CAPTCHA | Depende del token | Token válido y no vencido: funciona como Count. Si falta el token, no es válido o está vencido: bloquea y envía un acertijo CAPTCHA cuando el cliente pueda mostrarlo |
| Challenge | Depende del token | La misma lógica de tokens, pero con un desafío silencioso del navegador en lugar de un acertijo |

CAPTCHA y Challenge solo funcionan cuando los navegadores acceden a endpoints HTTPS en un contexto seguro, y ambos generan tarifas adicionales. Un cliente de API que no sea un navegador no puede responder a esos desafíos, así que prueba las API de máquina por separado; AWS WAF también ofrece SDK de integración con aplicaciones que añaden tokens a las solicitudes de las aplicaciones. AWS también incorporó la acción **Monetize** (HTTP `402 Payment Required`, solo para ACL web de CloudFront, termina la evaluación y no se permite en reglas basadas en tasas); queda fuera del alcance de este cuaderno.

**Reglas basadas en tasas.** Una regla basada en tasas cuenta las solicitudes de cada **instancia de agregación** (por ejemplo, cada IP de origen) durante una **ventana de evaluación** de 60, 120, 300 o 600 segundos (300 de forma predeterminada) y aplica su acción a las solicitudes coincidentes posteriores de una instancia que supere el **límite** (mínimo de 10). La acción puede ser cualquiera excepto Allow. Una **instrucción de reducción del alcance** limita las solicitudes que se cuentan y a las que se aplica la acción; por ejemplo, solo `POST` a `/login`. Aspectos de comportamiento que hay que tener en cuenta en el diseño:

- AWS WAF estima la tasa con un algoritmo que asigna más peso a las solicitudes recientes, por lo que limita cerca del valor configurado, pero no exactamente en ese valor.
- La guía indica que la tasa se comprueba con frecuencia e independientemente de la ventana; la referencia de la API especifica que esto ocurre aproximadamente cada 10 segundos. Las solicitudes pueden llegar demasiado rápido durante varios minutos antes de que empiece la limitación, y esta puede continuar después de que la tasa baje, por lo general durante menos de 30 segundos.
- Cambiar el límite, la ventana, la agregación, la configuración de IP reenviada o el alcance **restablece los recuentos** y puede pausar la limitación de tasa durante un máximo de un minuto.
- Una instrucción basada en tasas no puede estar anidada dentro de otra instrucción (por ejemplo, una `NotStatement`), pero su instrucción de reducción del alcance sí puede contener otra.
- Si la agregación se basa únicamente en IP, `GetRateBasedStatementManagedKeys` enumera las direcciones que se están limitando en ese momento.

En [security/14, sección 5](../../security/14-waf-edge-api-security.md) se explica qué dirección de cliente agregar en la ruta CloudFront → ALB → Ingress.

**Etiquetas.** Una etiqueta es metadato que una regla coincidente añade a la solicitud; permanece durante el resto de la evaluación de esa ACL web, y las reglas posteriores la leen mediante una **instrucción de coincidencia de etiquetas**. Tus etiquetas tienen el formato `awswaf:<account id>:<rulegroup or webacl>:<name>:<namespace>:...:<label name>`, y las etiquetas de grupos de reglas administradas, el formato `awswaf:managed:<vendor>:<rule group name>:...`; por ejemplo, `awswaf:managed:aws:core-rule-set:NoUserAgent_Header`. Todos los grupos de reglas de AWS Managed Rules añaden etiquetas. El patrón principal es configurar una regla en Count para que solo etiquete y, luego, añadir una regla posterior que decida según la combinación de etiquetas. Las etiquetas también generan métricas de etiquetas en CloudWatch.

**Anulación de reglas administradas.** Existen dos opciones distintas:

| Anulación | Qué ocurre | ¿Sirve para pruebas? |
|---|---|---|
| **Anulación de acción de regla** (`RuleActionOverrides`, por regla dentro del grupo) | Las solicitudes coincidentes se procesan exactamente como si la acción de esa regla fuera la acción anulada, por ejemplo Count; el grupo sigue evaluando sus otras reglas | Sí, es la forma documentada de probar un grupo de reglas |
| **Anulación de la acción devuelta por el grupo de reglas a Count** | El grupo evalúa normalmente y se detiene en su primera coincidencia que termina la evaluación; solo el resultado devuelto a la ACL web pasa a ser Count | No: la guía indica que esto no cambia la evaluación del grupo, así que las reglas posteriores del grupo nunca se ejecutan para esa solicitud |

`RuleActionOverrides` sustituyó la configuración anterior `ExcludedRules` en octubre de 2022.

**Capacidad (WCU).** Las unidades de capacidad de ACL web miden los recursos operativos que necesitan las reglas; no cambian la forma en que se inspecciona el tráfico. Las instrucciones sencillas cuestan menos que, por ejemplo, los conjuntos de patrones regex o la inspección de cuerpos JSON. Un grupo de reglas tiene una **capacidad inmutable** establecida al crearse (máximo de 5.000 WCU), y usar un grupo en una ACL web cuesta esa capacidad, no la de su contenido actual. Una ACL web puede usar hasta 5.000 WCU; el precio base incluye 1.500 y la capacidad adicional está sujeta a tarifas escalonadas. La API `CheckCapacity` devuelve la capacidad de una lista de reglas antes de implementarla.

**Propagación.** Los cambios tardan desde unos segundos hasta varios minutos en llegar a todas las ubicaciones, así que durante un breve periodo una ubicación puede aplicar la acción nueva mientras otra sigue aplicando la anterior.

## 6. AWS Shield Standard y Shield Advanced

| | Shield Standard | Shield Advanced |
|---|---|---|
| Costo y activación | Se activa automáticamente para todos los clientes de AWS, sin costo adicional | Suscripción; la página de precios indica una tarifa mensual que comienza en 3.000 USD con un plazo de un año que se renueva automáticamente. Protege solo los recursos que añadas explícitamente (o mediante una política de Shield Advanced de AWS Firewall Manager) |
| Cobertura | Los ataques más comunes y frecuentes contra las capas de red y transporte; las distribuciones de CloudFront, las zonas alojadas de Route 53 y los aceleradores estándar de Global Accelerator reciben protección contra todos los ataques conocidos contra las capas de red y transporte | CloudFront, zonas alojadas de Route 53, aceleradores estándar de Global Accelerator, direcciones IP elásticas (y las instancias EC2 y los NLB que haya detrás), ALB y Classic Load Balancers |
| Capa de aplicación (L7) | Ninguna por sí solo; L7 corresponde a WAF | Usa ACL web de AWS WAF; se cubren las tarifas estándar de WAF para recursos protegidos hasta 1.500 WCU y el tamaño de cuerpo predeterminado. No se cubren Bot Control, CAPTCHA, la capacidad superior a 1.500 WCU ni la inspección de cuerpos de mayor tamaño. La suscripción también incluye el grupo de reglas Anti-DDoS sin costo adicional y cubre las tarifas de solicitudes de AWS WAF hasta 50.000 millones de solicitudes al mes por pagador (después, 0,15 USD por millón) |
| Mitigación automática de L7 | Ninguna | Consulta el párrafo siguiente |
| Equipo de respuesta | Ninguno | **Shield Response Team (SRT)** para recibir ayuda durante un ataque y mitigaciones personalizadas; requiere un plan de Business Support o Enterprise Support (el documento técnico sobre resiliencia frente a DDoS lo describe como Business Support+ o Enterprise Support) |
| Detección | Automática | Detección basada en el estado, con comprobaciones de estado de Route 53; la **interacción proactiva** (el SRT se pone en contacto contigo) requiere estas comprobaciones |
| Protección de costos | Ninguna | Créditos de servicio de Shield Advanced para algunos cargos de escalado causados por un ataque |
| Visibilidad | Ninguna más allá de las métricas del servicio | Detalles de eventos en la consola, la API y las métricas de CloudWatch; grupos de protección |

**Mitigación automática de L7 en 2026.** Desde el 26 de marzo de 2026, el **grupo de reglas administradas Anti-DDoS** (`AWSManagedRulesAntiDDoSRuleSet`, 50 WCU; genera tarifas adicionales con AWS WAF sin suscripción, pero se incluye sin costo adicional con una suscripción a Shield Advanced) es la solución predeterminada de AWS para las inundaciones de solicitudes HTTP y reemplaza la mitigación automática de la capa 7 de Shield Advanced, que los clientes actuales pueden seguir usando. El grupo de reglas compara el tráfico con la línea base del recurso, etiqueta cada solicitud durante un evento (`awswaf:managed:aws:anti-ddos:event-detected`) y las fuentes sospechosas según su nivel de confianza (`low-`, `medium-`, `high-suspicion-ddos-request`), envía un Challenge silencioso como mitigación suave (solo las solicitudes `GET` pueden etiquetarse como aptas para Challenge) y bloquea como mitigación estricta. La función heredada de Shield Advanced añade un grupo de reglas de 150 WCU, necesita entre 24 horas y 30 días para aprender una línea base, puede contar o bloquear, y funciona peor en un ALB detrás de una CDN porque esta podría no reenviar los atributos del cliente original; AWS recomienda activarla en la distribución de CloudFront.

## 7. Defensa en profundidad en la ruta de referencia

![Animación de seguridad perimetral. ① Una botnet envía una inundación L3/L4 (reflexión UDP e inundación SYN) al perímetro de CloudFront; Shield la absorbe allí y nada llega al origen. ② Un bot envía una inundación HTTPS bien formada a /login; supera las comprobaciones L3/L4, pero una regla basada en tasas de la ACL web de WAF, llamada por ejemplo rate-login, la bloquea y el cliente recibe 403 Forbidden. ③ Una solicitud GET legítima supera Shield y, como ninguna regla de WAF termina su evaluación, la acción predeterminada de la ACL web Allow la reenvía. ④ CloudFront se conecta mediante un origen de VPC: una ENI administrada por el servicio en una subred privada, 10.0.11.25, abre una conexión con un ALB interno, 10.0.12.40, cuyo grupo de seguridad solo admite CloudFront-VPCOrigins-Service-SG o la lista de prefijos orientada al origen. ⑤ El ALB, creado a partir de un Ingress con el esquema internal, reenvía la solicitud a una IP de Pod, 10.0.13.31, cuya NetworkPolicy solo admite la subred del ALB, y el Pod devuelve 200. No hay ningún balanceador de carga orientado a Internet ni ninguna regla de entrada que admita un CIDR público.](../../.gitbook/assets/en-networking-expert-09-edge-security-waf-ddos-anim-0.svg)

| Capa | Control | Qué admite | Evidencia de que funcionó |
|---|---|---|---|
| Red perimetral | Shield Standard, CloudFront (dirección DNS, anycast, proxy SYN, TLS en el perímetro) | Conexiones HTTP(S) bien formadas | La carga del origen no cambia durante un evento de capa de red; datos del evento de Shield Advanced si hay una suscripción |
| Aplicación perimetral | ACL web global (alcance `CLOUDFRONT`, us-east-1) | Solicitudes cuya evaluación no termina con ninguna regla; después, se aplica la acción predeterminada | Registros de WAF: `terminatingRuleId`, `action`, etiquetas |
| Ruta al origen | Origen de VPC a un ALB interno ([workbook 08](./08-cdn-edge-delivery.md#edge-origin-path)) | Solo CloudFront; el ALB tiene únicamente direcciones privadas | No hay ninguna ruta de Internet con la que probar |
| Grupo de seguridad del ALB | Solo entrada desde `CloudFront-VPCOrigins-Service-SG` (tu distribución) o desde la lista de prefijos administrada `com.amazonaws.global.cloudfront.origin-facing` (cualquier distribución) | ENI del origen de VPC de CloudFront | Reglas del grupo de seguridad; se espera que los registros de acceso del ALB muestren únicamente direcciones de la subred del origen de VPC |
| Ingress | AWS Load Balancer Controller con `alb.ingress.kubernetes.io/scheme: internal` y `target-type: ip` ([AWS Load Balancer Controller](../03-aws-lb-controller.md)) | Reglas de listener que definiste | Eventos de Ingress, estado de los destinos |
| Pod | Ingreso de NetworkPolicy desde un `ipBlock` con las subredes del ALB ([Network Policies](../../security/04-network-policies.md#kubernetes-networkpolicy-spec)) | Conexiones desde los nodos del ALB | Conexiones denegadas en los registros de políticas de la CNI, si están habilitados |
| Host | Firewall de host ([beginner 06](../beginner/06-firewalls-host-security.md)) | Puertos que el nodo debe atender | Contadores del firewall |
| Aplicación | Autenticación y autorización | Acciones que el usuario tiene permitido realizar | Registro de auditoría de la aplicación |

**Qué dirección de origen ve el Pod.** Un ALB actúa como proxy: la guía de ELB indica que los registros de acceso del servidor contienen solo la dirección IP del balanceador de carga, y que la dirección del cliente llega en `X-Forwarded-For`, que solo es confiable cuando la añaden sistemas debidamente protegidos. Por tanto, un destino con IP de Pod ve la dirección privada del nodo del ALB, razón por la que la NetworkPolicy anterior especifica las subredes del ALB. La documentación de Kubernetes advierte que el cambio de dirección puede producirse antes o después del procesamiento de NetworkPolicy, según el complemento de red, el proveedor de nube y la implementación de Service; por eso, confirma la dirección de origen observada en tu CNI antes de depender de la regla y recuerda que NetworkPolicy no tiene efecto sin un complemento que la aplique.

**¿Una ACL web o dos?** La ACL web de CloudFront no se puede asociar también al ALB. Si añades una ACL web regional al ALB, será una segunda inspección independiente, con sus propios registros y costos; [security/14, sección 2](../../security/14-waf-edge-api-security.md) explica en qué casos vale la pena.

## 8. Ocultamiento del origen: por qué un origen accesible permite eludir el perímetro

Todos los controles de las filas perimetrales de la tabla anterior se aplican **solo a las solicitudes que pasan por la distribución**. Si un atacante descubre una dirección o un nombre DNS con el que se pueda acceder al origen desde Internet, enviará allí las solicitudes y eludirá de una sola vez la absorción perimetral de Shield, la ACL web global, las reglas basadas en tasas y la terminación de TLS de CloudFront. El origen se enfrentará entonces a inundaciones SYN e inundaciones HTTP sin más protección que su propia capacidad, y los registros de WAF no mostrarán nada.

**Ocultamiento** significa que el origen no tiene ninguna ruta desde Internet. En el diseño de referencia, es una propiedad de enrutamiento, no un filtro: el ALB interno solo tiene direcciones privadas, así que un grupo de seguridad más permisivo que se configure después tampoco hará que sea accesible desde Internet ([workbook 08](./08-cdn-edge-delivery.md#edge-origin-path)). Compáralo con el diseño más débil que describe [security/14, opción A](../../security/14-waf-edge-api-security.md): un ALB público que admite la lista de prefijos de CloudFront y comprueba un encabezado secreto. La lista de prefijos admite **cualquier** distribución de CloudFront, incluso una que cree un atacante, y el encabezado es un secreto compartido que deja de servir una vez que se divulga. Este curso no usa ese diseño.

**Lista de posibles rutas de elusión para una revisión:** registros DNS antiguos que todavía apuntan a un origen público anterior, otros balanceadores de carga o Services de tipo `LoadBalancer` en el mismo clúster, NodePorts, endpoints de administración y entornos de prueba que sirvan la misma aplicación. Que una ruta tenga una etiqueta de origen privado no demuestra que no exista ninguna otra ruta.

## 9. Registros y métricas: qué demuestra cada señal

| Señal | Ubicación | Qué indica | Limitación |
|---|---|---|---|
| Registros de WAF | Grupo de registros de CloudWatch, bucket de S3 o flujo de Amazon Data Firehose cuyo nombre empieza por `aws-waf-logs-` | Por solicitud: `terminatingRuleId` y `action`, coincidencias de Count en `nonTerminatingMatchingRules`, `ruleGroupId`, `labels` | Se cobran por separado; puedes filtrar qué solicitudes conservar y enmascarar campos (que aparecen como `xxx`) |
| Métricas de CloudWatch | Métricas de AWS WAF | Coincidencias agrupadas por acción (las coincidencias de una regla Count aparecen como métricas Count), métricas de cada etiqueta | Las reglas con acción Count dentro de grupos de reglas no emiten métricas con dimensiones de ACL web, solo dimensiones Rule, RuleGroup y Region |
| Solicitudes muestreadas | Pestaña de la ACL web en la consola o `GetSampledRequests` | Hasta 100 solicitudes que coincidieron con una regla y 100 que usaron la acción predeterminada, de las tres horas anteriores, con la regla, la acción y el URI | Requiere que el muestreo esté habilitado; la vista de la ACL web no muestra muestras de reglas Count dentro de grupos de reglas; el enmascaramiento de los registros no se aplica al muestreo |
| Paneles de resumen del tráfico | Consola de WAF | Resúmenes casi en tiempo real de las métricas de CloudWatch | Son resúmenes, no pruebas de solicitudes |
| Eventos de Shield Advanced | Consola de Shield, API, CloudWatch | Eventos detectados y mitigaciones en recursos protegidos | Solo con suscripción |
| Registros de CloudFront | [workbook 08, sección 10](./08-cdn-edge-delivery.md) | Códigos de estado y tipos de resultado por solicitud en el perímetro | La regla coincidente aparece en los registros de WAF; por eso hay que correlacionar ambos |

La lista completa de campos de registro de WAF está en [security/14, sección 6](../../security/14-waf-edge-api-security.md). Para las reglas en Count, **los registros y las métricas de etiquetas** son las pruebas fiables, porque las solicitudes muestreadas y las métricas de ACL web pueden ocultar coincidencias Count dentro de grupos de reglas administradas.

## 10. Ejercicio: un plan de reglas en modo Count con un desencadenante de reversión

Ejercicio de escritorio. Escribe un plan que alguien pudiera ejecutar más adelante en una cuenta aprobada; no lo implementes. Marca el resultado como **escenario resuelto, no medido**.

**Escenario.** Una tienda sirve `/assets/*`, `/login` (`POST`, formulario de navegador), `/api/*` (una aplicación móvil, no un navegador) y `/api/upload` (imágenes de hasta 5 MB) a través de la ruta de referencia de la sección 7. Siete días de registros de CloudFront proporcionan esta línea base:

| Ruta | Volumen | Pico por IP en cualquier periodo de 5 minutos | Notas |
|---|---|---|---|
| `POST /login` | 1,2 millones al día, tasa de éxito del 96 % | p99 de 18 solicitudes; una dirección, `198.51.100.20`, llega a un pico de 640 | `198.51.100.20` es la NAT de la oficina de un socio, compartida por muchos empleados |
| `/api/upload` | 40.000 al día | p99 de 6 | El cuerpo de cada solicitud supera los 8 KB |
| `/api/*` (otras) | 9 millones al día | p99 de 120 | Aplicación móvil, no puede usar Challenge ni CAPTCHA |

La acción predeterminada de la ACL web es Allow.

**Plan (completa o comprueba cada fila):**

| Prioridad | Regla | Acción de prueba | Coincidencias esperadas durante la prueba | Decisión antes de pasar a Block |
|---|---|---|---|---|
| 10 | `AWSManagedRulesCommonRuleSet` con todas las reglas anuladas a Count mediante `RuleActionOverrides` | Count (por regla) | `SizeRestrictions_BODY` en prácticamente todas las 40.000 solicitudes diarias a `/api/upload` (cuerpos de más de 8 KB); otras reglas casi no coinciden con usuarios reales | Excluir `/api/upload` del grupo mediante una instrucción de reducción del alcance, o dejar `SizeRestrictions_BODY` en Count y añadir una regla de coincidencia de etiquetas para las otras rutas |
| 20 | `AWSManagedRulesSQLiRuleSet`, con las reglas anuladas a Count | Count (por regla) | Casi ninguna coincidencia con usuarios reales | Investigar todas las coincidencias de un cliente conocido antes de promover la regla |
| 30 | `rate-login`: regla basada en tasas, agrega por IP, ventana de 300 s, límite de 100, reducción del alcance para `POST` y rutas que empiecen por `/login` | Count | Los usuarios habituales nunca coinciden (p99 de 18 está muy por debajo de 100); `198.51.100.20` coincide siempre que supera 100: en una ráfaga aislada de 5 minutos de 640 solicitudes después de un periodo sin actividad, se cuentan unas 540 solicitudes (las que exceden el límite); si se mantiene por encima de 100 durante más tiempo, se cuenta casi todo el tráfico posterior de esa dirección, porque la regla sigue actuando hasta que la tasa estimada cae por debajo del límite | Falso positivo: añade `NOT` (un conjunto de IP que contenga `198.51.100.20`) dentro de la reducción del alcance, o establece un límite más alto para esa dirección |

A continuación se muestra un fragmento de la fila 30. Muestra la regla **después** de decidir cómo tratar el falso positivo, con la exclusión `PartnerNat` añadida; durante la prueba descrita en la tabla, se omite la `NotStatement`. Es **una regla dentro de una ACL web**, no una ACL web completa ni un comando de implementación; `PartnerNat` es un conjunto de IP que habría que crear.

```json
{
  "Name": "rate-login",
  "Priority": 30,
  "Statement": {
    "RateBasedStatement": {
      "Limit": 100,
      "EvaluationWindowSec": 300,
      "AggregateKeyType": "IP",
      "ScopeDownStatement": {
        "AndStatement": {
          "Statements": [
            { "ByteMatchStatement": { "SearchString": "POST", "FieldToMatch": { "Method": {} },
                "TextTransformations": [{ "Priority": 0, "Type": "NONE" }], "PositionalConstraint": "EXACTLY" } },
            { "ByteMatchStatement": { "SearchString": "/login", "FieldToMatch": { "UriPath": {} },
                "TextTransformations": [{ "Priority": 0, "Type": "NONE" }], "PositionalConstraint": "STARTS_WITH" } },
            { "NotStatement": { "Statement": { "IPSetReferenceStatement": {
                "ARN": "arn:aws:wafv2:us-east-1:111122223333:global/ipset/PartnerNat/<id>" } } } }
          ]
        }
      }
    }
  },
  "Action": { "Count": {} },
  "VisibilityConfig": { "SampledRequestsEnabled": true, "CloudWatchMetricsEnabled": true, "MetricName": "rate-login" }
}
```

**Tareas:**

1. Completa el plan: para cada fila, indica qué pruebas leerás (campo del registro, métrica o etiqueta), la duración de la prueba y quién tomará la decisión.
2. Explica por qué la fila 10 usa anulaciones de `RuleActionOverrides` por regla y no la anulación de la acción devuelta por el grupo de reglas (sección 5).
3. Calcula las coincidencias Count esperadas para `rate-login`, con y sin la exclusión `PartnerNat`, tanto para una ráfaga aislada como para un pico sostenido, e indica por qué la cifra real será distinta (recuento aproximado, demora en la detección y continuación breve de la limitación después de que baje la tasa).
4. Escribe un **desencadenante de reversión** para cada regla que promuevas a Block. Debe incluir un umbral medible, una ventana de tiempo, un responsable y la acción exacta. Ejemplo: «Después de que `rate-login` pase a Block, si la tasa de éxito de `/login` se mantiene más de 2 puntos porcentuales por debajo de la línea base del 96 % durante 10 minutos consecutivos, o si se bloquea cualquier solicitud de la comprobación sintética de inicio de sesión, el ingeniero de guardia vuelve a poner `rate-login` en Count y registra el cambio». Ten en cuenta que la reversión tarda de segundos a minutos en propagarse y que, en una regla basada en tasas, restablece los recuentos.
5. Decide qué se aplicará al tráfico móvil `/api/*` en lugar de Challenge o CAPTCHA, y explica por qué.
6. Decide si el grupo de reglas administradas Anti-DDoS debe formar parte del plan y en qué posición respecto a la fila 30.

**Criterios de revisión:**

- Todos los números esperados se derivan de la tabla de línea base y se muestra el cálculo.
- Cada promoción a Block tiene una fuente de evidencia que puede ver coincidencias Count dentro de grupos de reglas administradas (registros o etiquetas, no solo solicitudes muestreadas).
- El plan cambia una regla a la vez y deja tiempo para la propagación antes de evaluar el resultado.
- Nada del plan expone el origen, añade un balanceador de carga orientado a Internet ni admite un CIDR público.

## 11. Observación de fallos y recuperación

Esta tabla es un ejercicio para identificar **qué pruebas confirman cada diagnóstico**. Si más adelante reproduces un escenario en un entorno aprobado, recopila exactamente estas pruebas.

| Fallo | Comportamiento esperado | Pruebas | Qué no demuestran esas pruebas |
|---|---|---|---|
| Una regla administrada bloquea cargas legítimas | `403` en `/api/upload` justo después de la promoción | Los registros de WAF muestran `terminatingRuleId` = el grupo, regla `SizeRestrictions_BODY`; aumenta la tasa de `403` de CloudFront | Que las otras reglas del grupo sean seguras |
| Se cambió un límite de tasa durante un ataque | La limitación se pausa hasta un minuto | Registro del cambio; las métricas Count o Block disminuyen y luego vuelven a subir | Que el nuevo límite sea adecuado |
| Reversión de Block a Count | Algunas ubicaciones siguen bloqueando durante un breve periodo | La métrica Block disminuye en cuestión de segundos a minutos | Que todas las ubicaciones tengan la nueva configuración en un momento dado |
| Solicitudes directas a un origen expuesto | El origen se sobrecarga mientras las métricas de WAF permanecen estables | Los registros de acceso del origen muestran fuentes que no son ENI de CloudFront | Qué ruta encontró el atacante (consulta la lista de la sección 8) |
| Inundación L3/L4 contra la distribución | El origen no se ve afectado | Las métricas del origen permanecen estables; evento de Shield Advanced si hay suscripción | Que la capa de aplicación sea segura |
| Evento Anti-DDoS | Todas las solicitudes, legítimas o no, reciben la etiqueta `event-detected` | Métricas de etiquetas | Que una solicitud etiquetada fuera maliciosa (solo las etiquetas de sospecha lo indican) |
| Challenge aplicado a la API móvil | Fallan las solicitudes de la aplicación | Los registros de WAF muestran la regla Challenge como regla que termina la evaluación del tráfico de la aplicación; aumenta la tasa de errores de la aplicación | Que los clientes sean bots |

**La recuperación también es un cambio.** Cada reversión es una actualización de la ACL web con el mismo comportamiento de propagación que el cambio que causó el incidente. Escribe el comando de reversión y quién es responsable en el plan antes de pasar la regla a Block, no durante el incidente.

## 12. Entregables y criterios de finalización

| Entregable | Criterios de finalización |
|---|---|
| Mapa de amenazas | Cada ataque de la sección 2 está ubicado en la ruta, con su control de detención y responsable |
| Decisión sobre Shield | Solo Standard, o Advanced con las funciones que se usarán, sus requisitos previos (plan de soporte, comprobaciones de estado) y el costo |
| Plan de reglas | Prioridades, acciones de prueba, coincidencias esperadas con cálculos, decisiones sobre falsos positivos y desencadenantes de reversión para cada regla |
| Revisión de la ruta al origen | Se confirma el ocultamiento en la ruta de referencia, se comprueba la lista de posibles rutas de elusión y no hay ningún balanceador de carga orientado a Internet ni ingreso de un CIDR público |
| Plan de pruebas | Para cada regla, el campo del registro o la métrica que demuestra que hubo coincidencia y sus puntos ciegos conocidos |

El trabajo está terminado cuando puedes explicar, con fuentes, a qué capa apunta cada ataque y dónde se detiene, cómo evalúa AWS WAF las reglas y las acciones, por qué las pruebas en modo Count usan anulaciones por regla, qué aporta Shield Advanced frente a Standard y por qué el origen no debe tener una ruta pública. Revisa la ubicación de WAF en [WAF, Edge and API Security](../../security/14-waf-edge-api-security.md), vuelve a consultar la ruta al origen en [workbook 08](./08-cdn-edge-delivery.md#edge-origin-path) y completa el [cuestionario](../../quizzes/networking/expert/09-edge-security-waf-ddos-quiz.md).

## Referencias

AWS WAF Developer Guide

- [Uso de las acciones de reglas en AWS WAF](https://docs.aws.amazon.com/waf/latest/developerguide/waf-rule-action.html) (Allow, Block y su `403` predeterminado, Count, CAPTCHA, Challenge, Monetize)
- [Configuración de la prioridad de las reglas](https://docs.aws.amazon.com/waf/latest/developerguide/web-acl-processing-order.html)
- [Configuración general de reglas basadas en tasas](https://docs.aws.amazon.com/waf/latest/developerguide/waf-rule-statement-type-rate-based-high-level-settings.html), [Consideraciones sobre las reglas basadas en tasas](https://docs.aws.amazon.com/waf/latest/developerguide/waf-rule-statement-type-rate-based-caveats.html)
- [Etiquetado de solicitudes web](https://docs.aws.amazon.com/waf/latest/developerguide/waf-labels.html), [Sintaxis de etiquetas y requisitos de nomenclatura](https://docs.aws.amazon.com/waf/latest/developerguide/waf-rule-label-requirements.html)
- [Anulación de acciones de grupos de reglas](https://docs.aws.amazon.com/waf/latest/developerguide/web-acl-rule-group-override-options.html)
- [Unidades de capacidad de ACL web (WCU)](https://docs.aws.amazon.com/waf/latest/developerguide/aws-waf-capacity-units.html)
- [Asociación o desasociación de protección a un recurso de AWS](https://docs.aws.amazon.com/waf/latest/developerguide/web-acl-associating-aws-resource.html) (ACL web global en US East (N. Virginia), una ACL web por recurso)
- [Grupos de reglas de referencia](https://docs.aws.amazon.com/waf/latest/developerguide/aws-managed-rule-groups-baseline.html) (conjunto de reglas principal, entradas maliciosas conocidas), [Grupos de reglas específicos de casos de uso](https://docs.aws.amazon.com/waf/latest/developerguide/aws-managed-rule-groups-use-case.html) (base de datos SQL), [Grupo de reglas de prevención de toma de control de cuentas](https://docs.aws.amazon.com/waf/latest/developerguide/aws-managed-rule-groups-atp.html), [Grupo de reglas Anti-DDoS](https://docs.aws.amazon.com/waf/latest/developerguide/aws-managed-rule-groups-anti-ddos.html)
- [Pruebas y ajuste de las protecciones de AWS WAF](https://docs.aws.amazon.com/waf/latest/developerguide/web-acl-testing.html), [Supervisión y ajuste](https://docs.aws.amazon.com/waf/latest/developerguide/web-acl-testing-activities.html) (modo Count, mitigación de falsos positivos, propagación)
- [Registro del tráfico de ACL web](https://docs.aws.amazon.com/waf/latest/developerguide/logging.html), [Destinos de registro](https://docs.aws.amazon.com/waf/latest/developerguide/logging-destinations.html), [Configuración del registro](https://docs.aws.amazon.com/waf/latest/developerguide/logging-management-configure.html) (prefijo `aws-waf-logs-`, enmascaramiento, filtros)
- [Visualización de muestras de solicitudes web](https://docs.aws.amazon.com/waf/latest/developerguide/web-acl-testing-view-sample.html)

AWS Shield (en la misma guía)

- [AWS Shield](https://docs.aws.amazon.com/waf/latest/developerguide/shield-chapter.html), [Descripción general de Shield Standard](https://docs.aws.amazon.com/waf/latest/developerguide/ddos-standard-summary.html)
- [Lógica de mitigación de Shield para CloudFront y Route 53](https://docs.aws.amazon.com/waf/latest/developerguide/ddos-event-mitigation-logic-continuous-inspection.html) (solo tráfico web válido, proxy TCP SYN, TLS en el perímetro, DNS y anycast)
- [Descripción general de Shield Advanced](https://docs.aws.amazon.com/waf/latest/developerguide/ddos-advanced-summary.html), [capacidades y opciones](https://docs.aws.amazon.com/waf/latest/developerguide/ddos-advanced-summary-capabilities.html), [recursos protegidos](https://docs.aws.amazon.com/waf/latest/developerguide/ddos-advanced-summary-protected-resources.html)
- [Automatización de la mitigación de DDoS de la capa de aplicación con Shield Advanced](https://docs.aws.amazon.com/waf/latest/developerguide/ddos-automatic-app-layer-response.html) (el grupo de reglas Anti-DDoS es la opción predeterminada desde el 26 de marzo de 2026; 150 WCU; línea base de 24 horas a 30 días; ALB detrás de una CDN)
- [Precios de AWS Shield](https://aws.amazon.com/shield/pricing/)

Otras fuentes de AWS

- [Referencia de la API de AWS WAF: CreateWebACL](https://docs.aws.amazon.com/waf/latest/APIReference/API_CreateWebACL.html) (alcance `CLOUDFRONT` y `us-east-1`, acción predeterminada), [RateBasedStatement](https://docs.aws.amazon.com/waf/latest/APIReference/API_RateBasedStatement.html) (rango del límite, ventana, comprobación de tasa aproximadamente cada 10 segundos, anidamiento)
- [Prácticas recomendadas de AWS para la resiliencia frente a DDoS: ataques a la capa de infraestructura](https://docs.aws.amazon.com/whitepapers/latest/aws-best-practices-ddos-resiliency/infrastructure-layer-attacks.html), [Ataques de reflexión UDP](https://docs.aws.amazon.com/whitepapers/latest/aws-best-practices-ddos-resiliency/udp-reflection-attacks.html), [Ataques de inundación SYN](https://docs.aws.amazon.com/whitepapers/latest/aws-best-practices-ddos-resiliency/syn-flood-attacks.html), [Ataques a la capa de aplicación](https://docs.aws.amazon.com/whitepapers/latest/aws-best-practices-ddos-resiliency/application-layer-attacks.html), [Técnicas de mitigación](https://docs.aws.amazon.com/whitepapers/latest/aws-best-practices-ddos-resiliency/mitigation-techniques.html), [Entrega de aplicaciones web en el perímetro (BP1)](https://docs.aws.amazon.com/whitepapers/latest/aws-best-practices-ddos-resiliency/web-application-delivery-at-the-edge-bp1.html)
- [Amazon CloudFront Developer Guide: Uso de protecciones de AWS WAF](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/distribution-web-awswaf.html), [Restricción de acceso con orígenes de VPC](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-vpc-origins.html)
- [Elastic Load Balancing: encabezados HTTP y Application Load Balancers](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/x-forwarded-headers.html) (dirección del balanceador de carga en los registros del servidor, `X-Forwarded-For`)

Estándares y otras fuentes primarias

- [RFC 4987: Ataques de inundación TCP SYN y mitigaciones comunes](https://www.rfc-editor.org/rfc/rfc4987.html) (§2.2, §3.6)
- [BCP 38](https://www.rfc-editor.org/info/bcp38) (validación de direcciones de origen)
- [OWASP Top 10 2021](https://owasp.org/Top10/2021/)
- [Kubernetes: Network Policies](https://kubernetes.io/docs/concepts/services-networking/network-policies/) (`ipBlock`, reescritura de origen, requisito del complemento)
- [RFC 1918](https://www.rfc-editor.org/rfc/rfc1918.html), [RFC 5737](https://www.rfc-editor.org/rfc/rfc5737.html) (direcciones de ejemplo)

Alcance del examen (se usa solo para elegir los temas)

- [AWS Certified Advanced Networking - Specialty (ANS-C01): dominio 4](https://docs.aws.amazon.com/aws-certification/latest/advanced-networking-specialty-01/advanced-networking-specialty-01-domain4.html)
