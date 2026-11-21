# 08. Diseño de CDN y entrega en el edge

> **Última actualización**: 19 de noviembre de 2026
> **Límites del laboratorio**: Observación de solo lectura. El ejercicio envía unas pocas solicitudes `curl` a un recurso público servido por CloudFront; este cuaderno no crea ninguna distribución, origen, VPC ni balanceador de carga.
> **Estado de verificación**: Se comprobaron la Guía para desarrolladores de Amazon CloudFront, las páginas del Centro de conocimiento de AWS y los RFC 9111/5861. Mientras se redactaba este cuaderno, se observaron encabezados de un recurso público servido por CloudFront y **solo se vieron respuestas Hit** (no se capturó ningún Miss); no se **configuró ni midió** ninguna distribución.

Al terminar este cuaderno, deberías poder predecir **dónde se responde una solicitud** (POP de edge, caché de edge regional, Origin Shield o el origen), explicar a partir de los encabezados de respuesta por qué se respondió allí y dibujar la ruta del edge al origen de modo que solo se pueda acceder al origen a través de CloudFront.

Este capítulo da por sentados los conceptos básicos. El almacenamiento en caché de DNS y el comportamiento de TTL se explican en [Fundamentos de redes, parte 3](../../basics/06-network-fundamentals-part3.md), incluido [cómo se estructura un mensaje HTTP/1.1](../../basics/06-network-fundamentals-part3.md#http11-message-structure); el protocolo de enlace TLS, SNI y los puntos de terminación se explican en la [parte 2](../../basics/06-network-fundamentals-part2.md); y las funciones de CloudFront, ALB y ACM se describen en la [parte 4](../../basics/06-network-fundamentals-part4.md). La parte 3 cubre el almacenamiento en caché de DNS, pero no el almacenamiento en caché de HTTP, así que la sección 6 define los términos de caché HTTP que necesita este capítulo. El enrutamiento anycast con BGP se basa en el [cuaderno 02](02-routing-policy-convergence.md), y la conectividad privada detrás de un origen, en el [cuaderno 07](07-wan-hybrid-connectivity.md).

**Requisitos previos:** un shell con `curl` y conexión a Internet. No se necesita una cuenta de AWS. Crear tú mismo el diseño de referencia genera cargos por solicitudes y transferencia de datos de CloudFront, rutas de invalidación por encima de la franquicia gratuita, solicitudes de Origin Shield, horas de balanceador de carga y horas de instancia; **es responsabilidad del alumno asumir esos costos y realizar la limpieza**. No crees recursos fuera de una cuenta de laboratorio existente y aprobada.

## 1. Lee con una pregunta que responder

El alcance del examen solo determina qué leer. Las cifras y los comportamientos proceden de los documentos oficiales de la primera columna.

| Lectura | Correspondencia con el alcance del examen | Pregunta que debes responder con tus propias palabras |
|---|---|---|
| [Cómo entrega contenido CloudFront](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/HowCloudFrontWorks.html), [Origin Shield](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/origin-shield.html) | ANS-C01, dominio 1, Diseño de redes, tarea 1.1 (servicios de red de edge) | ¿Qué solicitudes omiten la caché de edge regional y cuáles omiten Origin Shield? |
| [Comprender la clave de caché](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/understanding-the-cache-key.html), [Controlar las solicitudes al origen con una política](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/controlling-origin-requests.html) | ANS-C01, dominios 1 y 2 (Implementación de redes) | ¿Qué debería recibir el origen que **no** debe formar parte de la clave de caché? |
| [Administrar cuánto tiempo permanece el contenido en la caché](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Expiration.html), [RFC 9111](https://www.rfc-editor.org/rfc/rfc9111.html), [RFC 5861](https://www.rfc-editor.org/rfc/rfc5861.html) | ANS-C01, dominio 2; principios de protocolo | ¿Qué prevalece cuando no coinciden `s-maxage` del origen y el TTL máximo de la política de caché? |
| [Restringir el acceso con orígenes de VPC](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-vpc-origins.html), [Restringir el acceso a un origen de Amazon S3](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-s3.html) | ANS-C01, dominio 4, Seguridad, cumplimiento y gobernanza de redes | ¿Qué impide que se acceda al origen por otra vía que no sea CloudFront? |
| [Ver las métricas de CloudFront](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/viewing-cloudfront-metrics.html), [Campos de registro estándar](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/standard-logs-reference.html) | ANS-C01, dominio 3, Administración y operación de redes | ¿Qué campo permite distinguir un hit del POP de un hit de Origin Shield? |

Después de leer, dibuja el viewer, el POP, la caché de edge regional, Origin Shield (si se usa) y el origen, con **niveles de caché** y **tramos de conexión** representados con estilos de línea distintos. Cada tramo tiene su propia conexión TCP o QUIC y su propia sesión TLS, así que «HTTPS de extremo a extremo» es una afirmación sobre cada tramo, no sobre uno solo.

## 2. Por qué una CDN

Una CDN cambia tres cosas, y un diseño debería indicar cuál de ellas busca obtener.

| Objetivo | Mecanismo | Límite que se debe indicar en un diseño |
|---|---|---|
| **Menor latencia (RTT)** | Los protocolos de enlace TCP/QUIC y TLS del viewer terminan en un POP cercano, en vez de hacerlo en un origen distante; un hit de caché elimina por completo el viaje de ida y vuelta al origen | Un miss sigue pagando el trayecto del POP al origen. En la parte 2 se mostró que un protocolo de enlace TLS 1.3 completo cuesta aproximadamente 1 RTT; ahora ese RTT es el corto entre el viewer y el POP |
| **Descarga del origen** | Los hits nunca llegan al origen; las cachés de edge regionales, Origin Shield y la consolidación de solicitudes reducen los misses que sí llegan | La tasa de hits depende de la clave de caché y los TTL que elijas (secciones 5 y 6), no solo de la CDN |
| **Absorción** | El tráfico llega a un edge distribuido de gran escala en lugar de a un único origen | La absorción protege el origen solo si no se puede acceder a él evitando la CDN (sección 9). Las defensas contra ataques volumétricos y de capa 7 son el tema del próximo cuaderno, [seguridad de edge](./09-edge-security-waf-ddos.md) |

CloudFront enruta cada solicitud a la ubicación de edge que mejor pueda atenderla, normalmente la que tenga la menor latencia, y transporta el tráfico de origen a través de la red de AWS.

## 3. Dirección de solicitudes: basada en DNS y anycast

Algo debe decidir **con qué POP** se comunica un viewer. Hay dos métodos habituales.

| Método | Cómo se elige el POP | Conmutación por error y granularidad | Dónde se utiliza |
|---|---|---|---|
| **Basado en DNS** | El DNS autoritativo de la CDN responde al resolver del viewer con la dirección de un POP adecuado | Los cambios entran en vigor cuando los resolvers vuelven a consultar, sujetos a las respuestas almacenadas en caché (parte 3: reducir un TTL ahora no acorta una respuesta que ya está almacenada en caché). El servidor autoritativo ve la dirección del **resolver**, no la del viewer, a menos que el resolver envíe información de la subred del cliente ([RFC 7871](https://www.rfc-editor.org/rfc/rfc7871.html)) | Valor predeterminado de CloudFront: «DNS enruta la solicitud al POP de CloudFront (ubicación de edge) que mejor pueda atenderla» |
| **Anycast** | Muchos sitios anuncian el **mismo** prefijo mediante BGP; el enrutamiento normal entrega cada paquete al anunciante topológicamente más cercano ([RFC 4786](https://www.rfc-editor.org/rfc/rfc4786.html)) | La conmutación por error sigue la retirada de rutas BGP y su convergencia (cuaderno 02). El RFC 4786 advierte que la selección de nodo debe permanecer estable durante más tiempo que una transacción, porque un cambio de enrutamiento puede enviar el resto de una sesión a otro nodo | **Direcciones IP estáticas Anycast** de CloudFront: una lista opcional de direcciones IPv4 estáticas dedicadas (o IPv4 e IPv6), para listas de permitidos o para apuntar a un dominio raíz con registros A; funciona con SNI |

**En la práctica:** con el direccionamiento basado en DNS, un viewer que se encuentre detrás de un resolver distante puede acabar en un POP lejos del viewer. Con anycast, «más cercano» significa que hay menos saltos BGP o que estos son más preferidos, no que la latencia sea menor. Ninguno de los dos métodos garantiza que dos solicitudes consecutivas lleguen al mismo POP o al mismo servidor, algo importante para el ejercicio de la sección 11.

## 4. Jerarquía de caché: POP, caché de edge regional, Origin Shield y origen

**Cómo se atiende una solicitud GET:**

1. DNS dirige el viewer a un POP. Si el objeto está almacenado en caché allí y es válido, el POP lo devuelve.
2. Si hay un miss en el POP, este **normalmente** consulta la **caché de edge regional** más cercana. Las cachés de edge regionales tienen una caché más grande que la de un POP individual, así que los objetos que ya no son lo bastante populares para permanecer en un POP se mantienen almacenados en caché aquí durante más tiempo.
3. Si hay un miss regional, CloudFront reenvía la solicitud al origen (a través de Origin Shield, si está habilitado). La respuesta vuelve a través de la caché de edge regional hasta el POP, y **ambos** almacenan una copia. CloudFront comienza a reenviarla en cuanto llega el primer byte.

![Animación de CDN con un MISS seguido de un HIT. ① El cliente A resuelve el nombre de la distribución; DNS responde con el POP de edge que tiene la menor latencia y A envía GET /img/logo.png. ② El POP de edge no tiene ningún objeto para esa clave de caché, así que se produce un MISS; consulta la caché de edge regional, que tampoco lo tiene. ③ El origen, un ALB interno al que se accede a través de un origen de VPC de CloudFront, devuelve 200 con Cache-Control: max-age=3600. ④ Al volver, la caché de edge regional y el POP almacenan una copia cada uno, y el cliente A recibe x-cache: Miss from cloudfront. ⑤ El cliente B solicita el mismo objeto al mismo POP: se produce un HIT, el POP responde desde su caché con Age: 42 y x-cache: Hit from cloudfront, y ninguna solicitud llega al origen.](../../.gitbook/assets/en-networking-expert-08-cdn-edge-delivery-anim-0.svg)

**Solicitudes que omiten la caché de edge regional** (Guía para desarrolladores):

- Los métodos HTTP de proxy `PUT`, `POST`, `PATCH`, `OPTIONS` y `DELETE` van directamente del POP al origen.
- Las solicitudes dinámicas, determinadas en el momento de la solicitud, van directamente al origen.
- Cuando el origen es un bucket de S3 y la caché de edge regional óptima para la solicitud está en la misma región que el bucket, el POP va directamente al bucket.

Las cachés de edge regionales tienen las mismas funciones que los POP: una invalidación elimina el objeto de ambos.

**Origin Shield** es una capa adicional opcional entre las cachés de edge regionales y el origen. Todas las solicitudes al origen desde todas las capas de caché de CloudFront pasan por ella, por lo que cada objeto puede obtenerse con tan solo una solicitud al origen; las solicitudes realizadas en la misma región que el origen la omiten. Elige la región de Origin Shield con la menor latencia al origen (solo se ofrece donde CloudFront tiene una caché de edge regional). Se cobra por cada solicitud que llega a Origin Shield como una capa **adicional**: las solicitudes dinámicas (`PUT`, `POST`, `PATCH`, `DELETE` y `GET`/`HEAD` con un TTL inferior a 3600 segundos o con el almacenamiento en caché deshabilitado) siempre se cuentan, mientras que las solicitudes almacenables en caché solo se cuentan cuando llegan desde una caché de edge regional situada en otra región. AWS indica que el contenido dinámico enviado por proxy, la baja capacidad de almacenamiento en caché y el contenido solicitado con poca frecuencia no son buenos candidatos.

**Consolidación de solicitudes:** si llegan más solicitudes con la misma clave de caché mientras el primer miss sigue esperando al origen, CloudFront las pausa y responde a todas con la primera respuesta. Solo se consolidan las solicitudes que tengan la misma clave de caché. En los registros, la primera aparece como `Miss` y las solicitudes consolidadas, como `Hit`.

## 5. Diseño de la clave de caché y tasa de hits

La **clave de caché** es el identificador único de un objeto en la caché. Se produce un hit cuando una solicitud genera la misma clave de caché que una solicitud anterior y el objeto está almacenado en caché y es válido. El RFC 9111 define la clave mínima como el método de solicitud y el URI de destino, y `Vary` permite añadir encabezados de solicitud.

**Valor predeterminado de CloudFront:** el nombre de dominio de la distribución y la ruta URL. De forma predeterminada, las cadenas de consulta, los encabezados y las cookies **no** forman parte de la clave. La Guía para desarrolladores muestra dos solicitudes a `/content/stories/example-story.html` con cadenas de consulta, `User-Agent`, `Referer` y la cookie `session_id` diferentes: la segunda sigue siendo un hit. Las respuestas a `OPTIONS` se almacenan en caché por separado de las de `GET` y `HEAD`.

**Dos políticas, dos funciones:**

| Política | Controla | Regla |
|---|---|---|
| **Política de caché** | Qué se incluye en la clave de caché, además de los TTL mínimo, predeterminado y máximo | Incluye un valor solo cuando cambia la respuesta |
| **Política de solicitud al origen** | Qué recibe el origen en un miss, **sin** añadirlo a la clave | Todo lo que esté en la clave de caché se reenvía automáticamente; usa esta política para los valores que el origen necesita, pero que no deben dividir la caché (analítica, telemetría) |

Una solicitud al origen siempre incluye la ruta URL, cualquier cuerpo y los encabezados que CloudFront añade automáticamente, como `Host`, `User-Agent` y `X-Amz-Cf-Id`.

**Qué divide la clave y qué hacer en su lugar:**

| Candidato | Problema | Alternativa |
|---|---|---|
| `Accept-Language` | `en-US,en`, `en,en-US`, `en-US, en` y `en-US` significan inglés, pero crean objetos separados | Incluye el idioma en la URL (`/en-US/...`) |
| `User-Agent` | Miles de variantes | Déjalo fuera de la clave |
| Cookies de sesión | Son únicas para cada usuario, así que cada uno recibe una copia privada | Déjalas fuera de la clave o marca la respuesta como no almacenable en caché |
| Cadenas de consulta que el origen ignora | Objetos duplicados | Exclúyelas o incluye solo parámetros con nombre |

La **tasa de hits** es la proporción de solicitudes de viewers que son hits. Auméntala incluyendo solo los valores mínimos necesarios en la clave, usando TTL más largos cuando la vigencia lo permita y con Origin Shield cuando los viewers estén distribuidos en varias regiones.

## 6. TTL, Cache-Control e invalidación

**Términos de caché HTTP que se usan aquí** (RFC 9111): una respuesta almacenada está **vigente** hasta que transcurre su periodo de vigencia; después queda **caducada**. Una caché compartida (una CDN) calcula el periodo de vigencia usando, en este orden, el primero disponible: `s-maxage`, luego `max-age` y luego `Expires` menos `Date`. Para usar una respuesta caducada normalmente se necesita **validarla** con el origen (una solicitud condicional que puede devolver `304 Not Modified`). El encabezado `Age` es la estimación del emisor de los segundos transcurridos desde que se generó o validó la respuesta en el origen; su presencia implica que el origen no generó la respuesta para esta solicitud. Una respuesta permanece vigente mientras su periodo de vigencia sea mayor que su antigüedad actual, así que el tiempo restante es el periodo de vigencia menos `Age`. `no-cache` significa que una respuesta almacenada no debe reutilizarse sin una validación satisfactoria; `no-store` significa que no se debe almacenar.

**Cómo combina CloudFront los encabezados del origen con los TTL de la política de caché:**

| Lo que envía el origen | TTL mínimo = 0 | TTL mínimo > 0 |
|---|---|---|
| `Cache-Control: max-age` | CloudFront almacena en caché durante el menor de `max-age` y el TTL máximo | Limitado: si es inferior al TTL mínimo, se usa el mínimo; si supera el máximo, se usa el máximo |
| `max-age` **y** `s-maxage` | CloudFront usa `s-maxage` (limitado por el TTL máximo); los navegadores usan `max-age` | `s-maxage` limitado entre el TTL mínimo y el máximo |
| No hay `max-age` | TTL predeterminado | El mayor entre el TTL mínimo y el predeterminado |
| `Expires` | Hasta esa fecha o el TTL máximo, lo que ocurra primero | Limitado entre el TTL mínimo y el máximo |
| `no-cache`, `no-store` o `private` | CloudFront y los navegadores respetan los encabezados | CloudFront almacena en caché de todos modos durante el **TTL mínimo** |

Otras reglas:

- Si están presentes tanto `max-age` como `Expires`, CloudFront solo usa `max-age`.
- Un `Cache-Control` o `Pragma` de un viewer en una solicitud GET no puede obligar a CloudFront a volver al origen; CloudFront los ignora.
- Sin una política de caché (configuración heredada), el TTL predeterminado es de 24 horas.
- **Trampa:** si el TTL mínimo es mayor que 0, la respuesta de un origen que envía `no-cache` sigue almacenándose en caché durante el TTL mínimo. Si después el origen deja de estar disponible y el TTL mínimo **o** máximo es mayor que 0, CloudFront sirve el objeto que obtuvo antes, así que reducir solo el TTL mínimo no lo evita. Añade `Cache-Control: stale-if-error=0` a la respuesta del origen para que CloudFront devuelva un error en su lugar.

**Servir contenido caducado deliberadamente:** CloudFront admite las extensiones del [RFC 5861](https://www.rfc-editor.org/rfc/rfc5861.html).

- `max-age=3600, stale-while-revalidate=600`: después de una hora, CloudFront sirve la copia caducada hasta 10 minutos mientras obtiene una copia nueva en segundo plano.
- `max-age=3600, stale-if-error=86400`: si el origen deja de estar disponible o devuelve un error 5xx después de una hora, CloudFront sigue sirviendo la copia caducada hasta 24 horas.
- En cualquiera de los dos casos, el contenido caducado solo se sirve hasta el menor valor entre la directiva y el **TTL máximo**.

**Invalidación frente a nombres de archivo versionados:**

| | Invalidación | Nombres versionados (`app.3f9c.js`) |
|---|---|---|
| Efecto | Elimina el objeto de los POP y de las cachés de edge regionales; la siguiente solicitud va al origen | Una URL nueva es una clave de caché nueva; las versiones antigua y nueva coexisten |
| Cachés del navegador y de proxies corporativos | No se ven afectadas: los usuarios pueden conservar la copia antigua hasta que caduque allí | La página hace referencia al nombre nuevo, así que todas las cachés lo obtienen |
| Costo | Las primeras 1.000 rutas de invalidación al mes son gratuitas por cuenta; después se cobra por ruta; una ruta comodín `*` cuenta como una ruta, independientemente del número de archivos que elimine | No hay cargos por invalidación; aun así, pagas por transferir las versiones nuevas al edge |
| Cuotas de tasa | 150 rutas o etiquetas por segundo y 1 invalidación comodín por segundo (página de cuotas de la Guía para desarrolladores) | Ninguna |
| Reversión | Vuelve a invalidar | Haz que la página apunte al nombre antiguo |

AWS recomienda usar nombres de archivo versionados para los archivos que actualizas con frecuencia. Las preguntas frecuentes de CloudFront y un artículo del Centro de conocimiento todavía describen los límites antiguos de invalidaciones «en curso al mismo tiempo» (3.000 archivos individuales y 15 rutas comodín por distribución); la página de cuotas de la Guía para desarrolladores es la fuente actual, así que consúltala el día en que diseñes.

## 7. TLS en el edge y hacia el origen

El tramo del viewer y el tramo del origen son dos sesiones TLS independientes (parte 2: la terminación no cifra el siguiente salto).

**Del viewer a CloudFront:**

- La política de protocolo del viewer puede permitir HTTP y HTTPS, redirigir HTTP a HTTPS o exigir solo HTTPS.
- Un certificado de ACM para una distribución de CloudFront debe solicitarse o importarse en **US East (N. Virginia)**; CloudFront lo distribuye a sus ubicaciones.
- HTTP/2 requiere un viewer compatible con TLS 1.2 o posterior y SNI; HTTP/3 requiere TLS 1.3 y SNI.

**De CloudFront al origen:**

- La política de protocolo del origen puede ser solo HTTP, solo HTTPS o coincidir con el viewer (elige «coincidir con el viewer» solo cuando la política del viewer sea redirigir a HTTPS o exigir solo HTTPS).
- El certificado del origen debe coincidir con el nombre de dominio del origen en la distribución o con el encabezado `Host`, si lo reenvías. CloudFront también envía ese nombre como SNI. Si el certificado no coincide, no procede de una CA de confianza, tiene una cadena incompleta o ha caducado, CloudFront cierra la conexión y devuelve `502` al viewer.
- Para un origen ALB, el certificado del ALB reside en **la región del ALB**, separada de la del certificado del viewer en us-east-1.
- Con un **origen de VPC**, CloudFront llega al ALB interno mediante su ARN, no mediante una búsqueda de DNS público; el nombre de host que configuras se usa solo para SNI y la coincidencia del certificado, así que no es necesario que ningún registro de DNS público apunte al ALB interno (blog de AWS Networking, 2026).

**En la práctica:** registra para cada tramo el protocolo, el certificado y su región, la versión mínima de TLS y quién renueva el certificado. En una revisión de diseño, «HTTPS» significa que se han completado ambas filas.

## 8. Aceleración dinámica, HTTP/2 y HTTP/3

No todo se puede almacenar en caché, pero una CDN sigue siendo útil para el tráfico que no se puede almacenar:

- **Protocolos de enlace más cortos para el viewer:** los protocolos de enlace TCP/QUIC y TLS se establecen con un POP cercano.
- **Conexiones persistentes con el origen:** después de una respuesta, CloudFront mantiene abierta la conexión al origen durante varios segundos (tiempo de espera configurable para conexiones persistentes de orígenes personalizados y de VPC), así que la siguiente solicitud evita un nuevo protocolo de enlace TCP y TLS.
- **Red de AWS:** el tráfico entre el edge y un origen en una región de AWS permanece en la red de AWS.
- **Las solicitudes dinámicas omiten la caché de edge regional** (sección 4), así que no se ralentizan por una consulta de caché adicional.

**Versiones de protocolo por tramo:**

| Tramo | Versiones | Notas |
|---|---|---|
| Viewer ↔ CloudFront | HTTP/1.0 y 1.1 habilitados de forma predeterminada; se pueden habilitar HTTP/2 y HTTP/3 | HTTP/3 se ejecuta sobre QUIC por UDP y CloudFront admite la migración de conexiones, de modo que el viewer puede cambiar de red sin perder la conexión |
| CloudFront → origen personalizado | HTTP/1.1 | La multiplexación de HTTP/2 del lado del viewer no llega al origen; planifica en consecuencia la capacidad de conexiones del origen |

HTTP/2 y HTTP/3 mantienen la semántica de HTTP y cambian el enmarcado (parte 3), así que la clave de caché y el TTL funcionan igual en todas las versiones.

## 9. Correspondencias de CloudFront y ruta del edge al origen

| Concepto | Función de CloudFront | Nota de diseño |
|---|---|---|
| Clave de caché y TTL | Política de caché | Valores mínimos en la clave; TTL por comportamiento |
| Reenviar sin dividir la caché | Política de solicitud al origen | Valores que necesita el origen, pero que no deben variar en la caché |
| Comportamiento por ruta | Comportamientos de caché (patrones de ruta) | Por ejemplo, TTL largo para `/assets/*` con nombres versionados; almacenamiento en caché deshabilitado para `/api/*` |
| Origen privado de S3 | Control de acceso al origen (OAC) | Recomendado frente al OAI heredado |
| Origen privado de ALB, NLB o EC2 | Origen de VPC | El diseño de referencia de la casa que se muestra a continuación |

**OAC para S3:** CloudFront firma las solicitudes al origen y la política del bucket permite únicamente esa distribución. AWS recomienda OAC en lugar de OAI porque admite buckets de S3 en todas las regiones (incluidas las regiones de activación opcional lanzadas después de diciembre de 2022), SSE-KMS y solicitudes dinámicas (`PUT`, `DELETE`). Con OAC, la propiedad de los objetos de S3 debe ser **Bucket owner enforced** (el valor predeterminado para los buckets nuevos). Un **punto de conexión de sitio web** de S3 es un origen personalizado y no puede usar OAC.

<a id="edge-origin-path"></a>

### Ruta del edge al origen: origen de VPC a un ALB interno

**Diseño de referencia:** CloudFront → **origen de VPC** → ALB **interno** en subredes privadas → grupo de destino. El origen no tiene una dirección pública y su único acceso entrante procede de CloudFront. No coloques un balanceador de carga orientado a Internet detrás de CloudFront y nunca añadas una regla entrante que permita un CIDR público al origen.

![Animación de la ruta del edge al origen. ① Un viewer envía una solicitud GET /menu.json almacenable en caché por HTTPS; TLS termina en el POP de edge y la solicitud produce un miss tanto en el POP como en la caché de edge regional. ② CloudFront se conecta al origen a través del origen de VPC: una ENI administrada por el servicio en una subred privada (por ejemplo, 10.0.11.25) abre la conexión al ALB interno (10.0.12.40). ③ El grupo de seguridad del ALB solo permite tráfico de CloudFront-VPCOrigins-Service-SG (o de la lista de prefijos administrada de cara al origen de CloudFront). ④ El listener del ALB reenvía la solicitud al grupo de destino, cuyos destinos solo aceptan tráfico del grupo de seguridad del ALB. ⑤ Un cliente de Internet intenta llegar directamente al ALB y no lo consigue: un ALB interno solo tiene direcciones privadas, así que nada en Internet puede enrutar hacia él y el intento nunca llega a la VPC. La VPC tiene un gateway de Internet conectado, pero no se usa para enrutar este trayecto.](../../.gitbook/assets/en-networking-expert-08-cdn-edge-delivery-anim-1.svg)

**Requisitos de los orígenes de VPC** (Guía para desarrolladores):

- **Tipos de origen:** un ALB, un NLB o una instancia EC2 en una subred privada, completamente desplegados y en estado Active. Los Gateway Load Balancers y los NLB con listeners TLS no pueden ser orígenes, y un NLB debe tener un grupo de seguridad asociado.
- **VPC:** la VPC debe tener un **gateway de Internet conectado**; esto indica que la VPC puede recibir tráfico de Internet, pero **no se usa para enrutar** hacia el origen y no es necesario cambiar la tabla de rutas.
- **Subred:** CloudFront crea una ENI administrada por el servicio en la subred privada, que necesita al menos una dirección IPv4 libre (y una dirección IPv6 para doble pila).
- **Grupo de seguridad:** el origen debe tener uno. Permite el tráfico entrante desde la **lista de prefijos administrada por CloudFront** (`com.amazonaws.global.cloudfront.origin-facing`, más la lista IPv6 para doble pila), que se puede añadir de antemano, o desde **`CloudFront-VPCOrigins-Service-SG`**, el grupo administrado por el servicio que estará disponible después de crear el origen de VPC y es más restrictivo porque solo permite tus distribuciones. No modifiques ese grupo ni crees uno propio con ese prefijo en el nombre.
- **No compatible:** gRPC y los triggers de solicitud al origen y de respuesta del origen de Lambda@Edge. Las reglas entrantes de NACL no se evalúan para el tráfico de CloudFront al origen, pero sí se evalúan las reglas **salientes** de NACL en el trayecto de retorno y deben permitir los puertos TCP efímeros 1024–65535 hacia los rangos de cara al origen de CloudFront.
- **Cuotas:** 25 orígenes de VPC por cuenta (ajustable) y 50 distribuciones por origen de VPC.

**Por qué no se puede llegar a un ALB interno evitando CloudFront:** los nodos de un balanceador de carga interno solo tienen direcciones IP privadas. Su nombre DNS se puede resolver públicamente, pero se resuelve a esas direcciones privadas, por lo que solo pueden llegar a él clientes con acceso a la VPC. Es una propiedad de enrutamiento, no un filtro, y se mantiene incluso si más adelante se relaja una regla del grupo de seguridad. Si el ALB procede de un Ingress de Kubernetes, el [AWS Load Balancer Controller](../03-aws-lb-controller.md) lo configura con `alb.ingress.kubernetes.io/scheme: internal`.

**Lista de prefijos o grupo de seguridad del servicio:** la lista de prefijos administrada contiene todos los servidores de CloudFront de cara al origen, así que permite **cualquier** distribución; el grupo de servicio del origen de VPC solo permite las tuyas. Como regla entrante, la lista de prefijos cuenta con un peso de 55 reglas para la cuota de reglas del grupo de seguridad. [Seguridad de WAF, edge y API](../../security/14-waf-edge-api-security.md) trata la ubicación de WAF y compara este diseño con el origen más débil basado en un ALB público (lista de prefijos más un encabezado secreto), que no se usa en el diseño de referencia de la casa; el siguiente cuaderno, [seguridad de edge](./09-edge-security-waf-ddos.md), desarrolla la perspectiva del atacante sobre esta ruta.

## 10. Observabilidad: qué demuestra cada señal

| Señal | Dónde | Qué te indica |
|---|---|---|
| Encabezado de respuesta `x-cache` | Respuesta al viewer | `Hit from cloudfront`, `RefreshHit from cloudfront` (copia caducada validada de nuevo con el origen) o `Miss from cloudfront` |
| `Age` | Respuesta al viewer | Segundos transcurridos desde que se generó o validó la copia en el origen; `Date` más `Age` es aproximadamente la hora actual cuando hay un hit |
| `x-amz-cf-pop` | Respuesta al viewer | El POP que respondió; compáralo entre solicitudes antes de sacar conclusiones de un segundo Miss |
| `Via` | Respuesta al viewer | Los intermediarios que gestionaron el mensaje ([RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html)); el identificador del servidor puede ser distinto entre dos solicitudes al mismo POP |
| `x-edge-result-type` | Registros estándar | `Hit`, `RefreshHit`, `Miss`, `LimitExceeded`, `CapacityExceeded`, `Error`, `Redirect`; WebSocket y gRPC siempre son `Miss` |
| `x-edge-detailed-result-type` | Registros estándar | El mismo valor que `x-edge-result-type`, salvo en los casos indicados; `OriginShieldHit` cuando lo sirvió Origin Shield (una solicitud enrutada a la caché de edge regional que actúa como Origin Shield se registra como `Hit`) |
| `time-to-first-byte` | Registros estándar | Segundos desde que se recibe la solicitud hasta que se escribe el primer byte, medidos en el servidor |
| Tasa de hits de caché, latencia del origen | Métricas adicionales de CloudWatch (de pago, hasta 8 por distribución, publicadas en us-east-1) | La tasa de hits solo cuenta las solicitudes que se pueden almacenar en caché (`POST`, `PUT` y los errores quedan excluidos); la latencia del origen es la latencia hasta el primer byte de las solicitudes atendidas desde el origen |

**Por qué una segunda solicitud todavía puede ser un Miss** (Centro de conocimiento de AWS): cada ubicación de edge almacena en caché solo lo que ha recibido, así que una solicitud que llega a otro POP produce un miss; un objeto solicitado con poca frecuencia puede desalojarse antes de caducar; los encabezados, las cookies o las cadenas de consulta incluidos en la clave de caché dividen las solicitudes; y `Cache-Control` o `Expires` del origen pueden acortar el periodo de vigencia.

## 11. Ejercicio: interpreta un miss y un hit a partir de los encabezados de respuesta

Esta es una observación de solo lectura. Etiqueta los resultados como **observación de una distribución de terceros**: no puedes ver su política de caché, así que todas las conclusiones son inferencias a partir de los encabezados.

**Elige un objetivo:** cualquier recurso estático público (imagen, CSS o archivo JavaScript) cuya respuesta incluya `x-cache: ... from cloudfront` y `x-amz-cf-pop`. No des por sentado que un sitio en particular se comporta de una forma concreta; comprueba primero los encabezados. Si tienes tu propia distribución aprobada, úsala, porque entonces podrás comparar los resultados con una política conocida.

```bash
URL='https://<cloudfront-served-host>/<path-to-static-asset>'
curl -sI "$URL" | grep -iE '^(HTTP|date|age|cache-control|x-cache|via|x-amz-cf-pop)'
sleep 5
curl -sI "$URL" | grep -iE '^(HTTP|date|age|cache-control|x-cache|via|x-amz-cf-pop)'
```

`curl -I` envía `HEAD`. La Guía para desarrolladores indica que solo las respuestas a `OPTIONS` se almacenan en caché por separado de las de `GET` y `HEAD`, así que los encabezados describen el mismo objeto almacenado en caché que usaría una solicitud `GET`. Para repetir el ejercicio con una solicitud `GET` real que descarte el cuerpo, usa `curl -s -o /dev/null -D - "$URL"`.

**Salida ilustrativa** (solo como ejemplo de formato, no se ha capturado de un sitio específico; los valores serán diferentes):

```text
HTTP/2 200
date: Thu, 19 Nov 2026 09:00:00 GMT
cache-control: max-age=86400
x-cache: Miss from cloudfront
via: 1.1 <edge-server-id-1>.cloudfront.net (CloudFront)
x-amz-cf-pop: <POP-code>

HTTP/2 200
date: Thu, 19 Nov 2026 09:00:00 GMT
cache-control: max-age=86400
x-cache: Hit from cloudfront
via: 1.1 <edge-server-id-2>.cloudfront.net (CloudFront)
x-amz-cf-pop: <POP-code>
age: 5
```

**Reglas de interpretación:**

| Lo que ves | Conclusión | Qué comprobar después |
|---|---|---|
| Miss y luego Hit, con el mismo `x-amz-cf-pop` | La primera solicitud llenó la caché de este POP (o una caché regional desde la que este leyó después); la segunda se atendió sin llegar al origen | `age` es aproximadamente el tiempo entre las solicitudes; `date` no cambia |
| Hit en la **primera** solicitud | Otro viewer ya había llenado la caché | `date` + `age` ≈ ahora; si `age` se acerca a `max-age`, caducará pronto |
| Miss y luego Miss | POP distinto, desalojo, una clave de caché que incluye algún valor que ha cambiado o una respuesta que no se puede almacenar en caché | Compara `x-amz-cf-pop`; comprueba si `cache-control` contiene `no-store`, `private` o `max-age=0` |
| `RefreshHit` | La copia había caducado y se volvió a validar con el origen | Espera que `age` se reinicie cerca de 0 |
| Cambia el identificador del servidor de `via`, pero el POP es el mismo | Respondió otro servidor del mismo POP; el objeto seguía estando en la caché | No hay nada que corregir |

**Tareas:**

1. Ejecuta las dos solicitudes y registra `x-amz-cf-pop`, `x-cache`, `age`, `date` y `cache-control` de cada una.
2. Calcula `date` + `age` y compáralo con tu reloj. Explica la diferencia.
3. A partir de `cache-control`, indica cuánto tiempo puede una caché compartida considerar vigente la copia y qué valor (`s-maxage` o `max-age`) usaría una CDN. Indica qué cambios podrían causar los TTL mínimo y máximo de la distribución, citando la tabla de la sección 6.
4. Si la primera solicitud ya fue un Hit, explica por qué. Una cadena de consulta para invalidar la caché no garantiza que se fuerce un Miss: cuando la política de caché excluye las cadenas de consulta de la clave (valor predeterminado de CloudFront), `?x=1` obtiene el mismo objeto. Si lo pruebas, envía como máximo una solicitud de este tipo al sitio de otra persona y explica el resultado según la clave de caché.
5. **Parte de diseño (revisión en papel):** para un sitio con `/assets/*` (nombres de archivo versionados), `/index.html` y `/api/*`, escribe la tabla de comportamientos de caché: contenido de la clave de caché, TTL, política de solicitud al origen, plan de invalidación y si Origin Shield vale el costo por solicitud. Luego dibuja la ruta del origen siguiendo la sección 9 y enumera sus reglas de grupo de seguridad.

**Criterios de revisión:**

- Cada conclusión cita un encabezado y una regla de las secciones 4–6 o 10.
- No se informa de un segundo Miss como «el almacenamiento en caché está roto» antes de comparar los códigos POP.
- La parte de diseño no incluye ningún balanceador de carga orientado a Internet ni CIDR públicos en reglas entrantes, y `/api/*` no almacena nada en caché o tiene una clave que incluye todos los valores que cambian la respuesta.

## 12. Observación de fallos y recuperación

Usa esta tabla para decidir **qué evidencia permitiría confirmar cada veredicto**. Si más adelante reproduces un escenario en un entorno existente y aprobado, recopila esa evidencia.

| Fallo | Comportamiento esperado | Evidencia | Qué no demuestra por sí sola esa evidencia |
|---|---|---|---|
| Origen caído, objeto todavía vigente | Los hits continúan; los misses fallan | `x-cache: Hit` con `age` creciente; resultados `Error` en los registros de los misses | Que todos los objetos estén almacenados en caché |
| Origen caído, objeto caducado, `stale-if-error` configurado | Se sirve la copia caducada hasta el menor entre la directiva y el TTL máximo | `age` superior a `max-age`; errores del origen en los registros | Cuánto duró la interrupción |
| Origen caído, TTL mínimo o máximo > 0, `no-cache` sin `stale-if-error=0` | Se puede servir una copia obtenida previamente (trampa de la sección 6) | Respuestas donde esperabas errores | Que esto sea aceptable para ese contenido |
| Aumenta la clave de caché (se añade un encabezado o una cookie) | Baja la tasa de hits, aumenta la latencia del origen y aumenta la carga del origen | Tasa de hits de caché de CloudWatch, recuento de solicitudes al origen | Qué valor dividió la clave (compara las políticas) |
| Certificado del origen no coincidente o caducado | Se devuelve `502` a los viewers en los misses | `502` del viewer; errores TLS del origen | Si los hits se vieron afectados (no se vieron) |
| Un cambio del grupo de seguridad elimina el origen de CloudFront | Los misses no consiguen conectarse; los hits continúan | `504` en los misses (un firewall del origen o una regla de seguridad que bloquea el tráfico de CloudFront devuelve 504); historial de reglas del grupo de seguridad | Que el ALB interno haya pasado a ser accesible desde Internet (no puede: no tiene dirección pública) |
| Se corrige una implementación defectuosa mediante una invalidación | Los edges vuelven a obtener el contenido; los navegadores y los proxies pueden conservar la copia antigua | Estado de la invalidación; `x-cache: Miss` y luego `Hit` | Que se hayan actualizado los navegadores de los usuarios (solo lo hacen los nombres versionados) |

**La recuperación genera carga.** Después de una invalidación o una interrupción del origen, muchos POP producen un miss al mismo tiempo. Las cachés de edge regionales, Origin Shield y la consolidación de solicitudes reducen el número de solicitudes al origen, pero planifica la capacidad del origen para volver a llenar las cachés. Que no se observen errores solo significa que el muestreo no capturó ninguno.

## 13. Entregables y criterios de finalización

| Entregable | Se considera terminado cuando |
|---|---|
| Dibujo de la ruta | Se han dibujado el viewer, el POP, la caché de edge regional, Origin Shield (si se usa) y el origen; se distinguen los niveles de caché y los tramos de conexión, y se marcan las solicitudes que omiten la caché de edge regional |
| Observación de encabezados | Se han registrado dos solicitudes con el POP, `x-cache`, `age`, `date` y `cache-control`, y cada conclusión se vincula a una regla |
| Tabla de comportamientos de caché | Se especifican la clave de caché, los TTL, la política de solicitud al origen y el plan de invalidación o versionado para cada ruta, y se justifica la decisión sobre Origin Shield |
| Ruta y reglas del origen | Se incluyen el origen de VPC hacia un ALB interno, el origen de la regla del grupo de seguridad (grupo de servicio o lista de prefijos) y la tabla TLS por tramo |
| Tabla de fallos | Cada fila incluye el comportamiento esperado, la evidencia y sus limitaciones |

Has terminado cuando puedes explicar, con fuentes, cómo se dirige una solicitud a un POP, qué nivel la responde y por qué, cómo deciden la tasa de hits las reglas de clave de caché y TTL, en qué se diferencian la invalidación y los nombres versionados, y por qué solo se puede acceder al origen a través de CloudFront. Continúa con el siguiente cuaderno, [seguridad de edge](./09-edge-security-waf-ddos.md), para estudiar el lado del ataque de esta misma ruta; repasa la ubicación de WAF en [Seguridad de WAF, edge y API](../../security/14-waf-edge-api-security.md); y completa el [cuestionario](../../quizzes/networking/expert/08-cdn-edge-delivery-quiz.md).

## Referencias

Guía para desarrolladores de Amazon CloudFront

- [¿Qué es Amazon CloudFront?](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Introduction.html) (enrutamiento de menor latencia, red de AWS)
- [Cómo entrega contenido CloudFront](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/HowCloudFrontWorks.html) (enrutamiento DNS al POP, cachés de edge regionales, solicitudes que las omiten)
- [Usar Amazon CloudFront Origin Shield](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/origin-shield.html) (omisión, regiones, base del costo, `OriginShieldHit`)
- [Comprender la clave de caché](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/understanding-the-cache-key.html), [Controlar las solicitudes al origen con una política](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/controlling-origin-requests.html)
- [Administrar cuánto tiempo permanece el contenido en la caché (expiración)](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Expiration.html) (tabla de TTL, `stale-while-revalidate`, `stale-if-error`, advertencia sobre el TTL mínimo)
- [Invalidar archivos para eliminar contenido](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Invalidation.html), [Pagar por invalidar archivos](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/PayingForInvalidation.html)
- [Cuotas](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/cloudfront-limits.html) (tasas de invalidación, orígenes de VPC, controles de acceso al origen)
- [Comportamiento de las solicitudes y respuestas para orígenes personalizados](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/RequestAndResponseBehaviorCustomOrigin.html) (HTTP/1.1 al origen, conexiones persistentes, consolidación de solicitudes, `Via`, protocolo del origen)
- [Referencia de configuración de distribuciones](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/DownloadDistValuesGeneral.html) (versiones HTTP compatibles, requisitos de HTTP/2 y HTTP/3)
- [Exigir HTTPS entre CloudFront y el origen personalizado](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/using-https-cloudfront-to-custom-origin.html) (política de protocolo del origen, nombres de certificado del origen)
- [Restringir el acceso a un origen de Amazon S3](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-s3.html) (OAC)
- [Restringir el acceso con orígenes de VPC](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-vpc-origins.html) (requisitos, grupos de seguridad, restricciones)
- [Ubicaciones y rangos de direcciones IP de los servidores de edge de CloudFront](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/LocationsOfEdgeServers.html) (lista de prefijos administrada)
- [Solicitar direcciones IP estáticas Anycast](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/request-static-ips.html)
- [Ver las métricas de CloudFront y las funciones de edge](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/viewing-cloudfront-metrics.html) (tasa de hits de caché, latencia del origen), [Campos de los archivos de registro estándar](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/standard-logs-reference.html)
- [Restringir el acceso a Application Load Balancers](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/restrict-access-to-load-balancer.html) (región del certificado del ALB frente al certificado del viewer de us-east-1)
- [Código de estado HTTP 504 (tiempo de espera agotado en el gateway)](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/http-504-gateway-timeout.html) (firewall del origen que bloquea CloudFront)

Otras fuentes de AWS

- [Cómo funciona Elastic Load Balancing](https://docs.aws.amazon.com/elasticloadbalancing/latest/userguide/how-elastic-load-balancing-works.html) (esquema de balanceador de carga interno)
- [Documento técnico de AWS: configuración de HTTPS del origen](https://docs.aws.amazon.com/whitepapers/latest/secure-content-delivery-amazon-cloudfront/origin-https-configuration.html) (condiciones del certificado del origen, SNI, `502`)
- [Centro de conocimiento de AWS: ¿Qué protocolos admite CloudFront?](https://repost.aws/knowledge-center/cloudfront-supported-protocols) (HTTP/1.0 y 1.1 habilitados de forma predeterminada, HTTP/1.1 hacia orígenes personalizados)
- [Centro de conocimiento de AWS: X-Cache: Miss from CloudFront](https://repost.aws/knowledge-center/cloudfront-x-cachemiss-error), [Almacenamiento en caché de objetos personalizados y encabezados del origen](https://repost.aws/knowledge-center/cloudfront-custom-object-caching) (valores de `x-cache`, `x-amz-cf-pop`)
- [Centro de conocimiento de AWS: asociar un certificado en US East (N. Virginia)](https://repost.aws/knowledge-center/migrate-ssl-cert-us-east)
- [Preguntas frecuentes sobre Amazon CloudFront](https://aws.amazon.com/cloudfront/faqs/) (límites antiguos de invalidaciones simultáneas), [Precios de Amazon CloudFront](https://aws.amazon.com/cloudfront/pricing/)
- [Blog de AWS Networking: agente de IA privado mediante CloudFront VPC Origins](https://aws.amazon.com/blogs/networking-and-content-delivery/private-ai-agent-with-websocket-streaming-over-cloudfront-vpc-origins-and-the-next-generation-of-opensearch-serverless-for-knowledge-retrieval/) (enrutamiento del origen de VPC mediante ARN, certificado del origen)
- [Blog de AWS Networking: lista de prefijos administrada para CloudFront](https://aws.amazon.com/blogs/networking-and-content-delivery/limit-access-to-your-origins-using-the-aws-managed-prefix-list-for-amazon-cloudfront/) (peso de regla 55)

Estándares

- [RFC 9111: almacenamiento en caché HTTP](https://www.rfc-editor.org/rfc/rfc9111.html) (clave de caché, vigencia, `Age`, `no-cache`, `s-maxage`)
- [RFC 5861: extensiones de Cache-Control de HTTP para contenido caducado](https://www.rfc-editor.org/rfc/rfc5861.html)
- [RFC 9110: semántica de HTTP](https://www.rfc-editor.org/rfc/rfc9110.html) (`Via`)
- [RFC 4786: funcionamiento de servicios Anycast](https://www.rfc-editor.org/rfc/rfc4786.html), [RFC 7871: subred del cliente en consultas DNS](https://www.rfc-editor.org/rfc/rfc7871.html)
- [RFC 1918](https://www.rfc-editor.org/rfc/rfc1918.html) (direcciones de ejemplo)

Alcance del examen (se utiliza solo para elegir los temas)

- [Guía del examen AWS Certified Advanced Networking - Specialty (ANS-C01)](https://docs.aws.amazon.com/aws-certification/latest/advanced-networking-specialty-01/advanced-networking-specialty-01.html)
