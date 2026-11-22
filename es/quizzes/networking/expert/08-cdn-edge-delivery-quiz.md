# 08. Cuestionario sobre diseño de CDN y entrega en el borde

> **Última actualización**: 19 de noviembre de 2026

Vuelve al [cuaderno](../../../networking/expert/08-cdn-edge-delivery.md).
Elige una respuesta por pregunta y explica qué regla del cuaderno la respalda.
Estos son ejercicios de razonamiento sobre diseño, no afirmaciones de que se haya creado una distribución.

1. Un POP no encuentra un objeto en la caché al recibir una solicitud. ¿En qué caso el POP la envía **directamente al origen** en vez de consultar la caché de borde regional?
   - A) Un `GET` para una imagen que nunca se había solicitado.
   - B) Un `POST` a una ruta de API.
   - C) Un `HEAD` para una hoja de estilo en caché cuyo TTL ha vencido.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Un `POST` a una ruta de API.**

**Explicación:** Los métodos HTTP de proxy (`PUT`, `POST`, `PATCH`, `OPTIONS`, `DELETE`) van directamente del POP al origen y no pasan por las cachés de borde regionales. Las solicitudes dinámicas y los orígenes de S3 que están en la misma Región que la caché de borde regional óptima también la omiten. Un `GET` por primera vez es justamente para lo que sirve la caché de borde regional.

</details>

2. Una distribución usa la clave de caché predeterminada. Dos usuarios solicitan `/content/stories/example-story.html` con cadenas de consulta, valores de `User-Agent` y cookies `session_id` distintos. ¿Qué ocurre con la segunda solicitud?
   - A) Es un acierto de caché, porque, de forma predeterminada, la clave solo contiene el nombre de dominio de la distribución y la ruta de la URL.
   - B) Es un fallo de caché, porque la cadena de consulta es distinta.
   - C) Es un fallo de caché, porque las cookies siempre forman parte de la clave de caché.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Es un acierto de caché, porque, de forma predeterminada, la clave solo contiene el nombre de dominio de la distribución y la ruta de la URL.**

**Explicación:** Las cadenas de consulta, los encabezados y las cookies no forman parte de la clave de caché predeterminada. Una política de caché los añade solo cuando cambian la respuesta; una política de solicitud al origen reenvía valores al origen sin dividir la caché.

</details>

3. El origen envía `Cache-Control: max-age=600, s-maxage=86400`. La política de caché tiene un TTL mínimo de 0 y un TTL máximo de 3600. ¿Durante cuánto tiempo almacena CloudFront el objeto en caché y durante cuánto tiempo lo hacen los navegadores?
   - A) CloudFront, 600 segundos; los navegadores, 86.400 segundos.
   - B) CloudFront, 86.400 segundos; los navegadores, 600 segundos.
   - C) CloudFront, 3.600 segundos; los navegadores, 600 segundos.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) CloudFront, 3.600 segundos; los navegadores, 600 segundos.**

**Explicación:** Cuando están presentes ambas directivas y el TTL mínimo es 0, CloudFront almacena en caché durante el menor de estos valores: `s-maxage` y el TTL máximo; los navegadores usan `max-age`. La RFC 9111 da prioridad a `s-maxage` en las cachés compartidas; el TTL máximo de la distribución sigue limitándolo.

</details>

4. El TTL mínimo de la política de caché es de 300 segundos, y el origen envía `Cache-Control: no-cache` para las páginas de cuenta. ¿Qué hace CloudFront y cómo puedes evitar que sirva una copia antigua cuando el origen no está disponible?
   - A) CloudFront nunca almacena en caché las respuestas `no-cache`, así que no hace falta cambiar nada.
   - B) CloudFront almacena el objeto en caché durante el TTL mínimo a pesar de `no-cache`, y puede servir la copia anterior si el origen no está disponible; añadir `Cache-Control: stale-if-error=0` lo impide.
   - C) CloudFront lo almacena en caché durante el TTL predeterminado de 24 horas.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) CloudFront almacena el objeto en caché durante el TTL mínimo a pesar de `no-cache`, y puede servir la copia anterior si el origen no está disponible; añadir `Cache-Control: stale-if-error=0` lo impide.**

**Explicación:** La Guía para desarrolladores advierte que un TTL mínimo superior a 0 prevalece sobre `no-cache`, `no-store` y `private`, y que, cuando el origen no está disponible y el TTL mínimo o máximo es superior a 0, CloudFront sirve el objeto que obtuvo anteriormente. Por lo tanto, reducir solo el TTL mínimo no impide que se sirva la copia obsoleta; `stale-if-error=0` hace que CloudFront devuelva un error en su lugar.

</details>

5. El origen envía `Cache-Control: max-age=3600, stale-while-revalidate=600`. ¿Qué ocurre con una solicitud realizada 65 minutos después de almacenar el objeto en caché?
   - A) CloudFront sirve inmediatamente la copia obsoleta y obtiene una nueva del origen en segundo plano.
   - B) CloudFront bloquea al usuario hasta que el origen devuelva una copia nueva.
   - C) CloudFront devuelve `504` porque el objeto está obsoleto.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) CloudFront sirve inmediatamente la copia obsoleta y obtiene una nueva del origen en segundo plano.**

**Explicación:** Una vez transcurrida la hora de vigencia, `stale-while-revalidate=600` permite a CloudFront servir la copia obsoleta durante un máximo de 10 minutos mientras la revalida de forma asíncrona (RFC 5861). El contenido obsoleto solo se sirve durante el menor de estos períodos: el indicado por la directiva y el TTL máximo.

</details>

6. Después de una implementación defectuosa, invalidas `/app.js`. Algunos usuarios detrás de un proxy corporativo siguen recibiendo el archivo antiguo. ¿Qué lo evitará la próxima vez?
   - A) Invalidar `/*` en vez de `/app.js`.
   - B) Reducir el TTL mínimo a 0.
   - C) Usar nombres de archivo versionados (por ejemplo, `app.3f9c.js`) y actualizar la página que los referencia.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Usar nombres de archivo versionados (por ejemplo, `app.3f9c.js`) y actualizar la página que los referencia.**

**Explicación:** Una invalidación elimina el objeto solo de los POP y las cachés de borde regionales; las cachés de los navegadores y de los proxies corporativos conservan la copia antigua hasta que caduque. Un nombre nuevo crea una clave de caché nueva para cada caché. El versionado también es más económico: no tiene costo de invalidación, mientras que una ruta `/*` sigue contando como una ruta de invalidación.

</details>

7. Ejecutas `curl -sI` dos veces para el mismo recurso. Ambas respuestas dicen `x-cache: Miss from cloudfront`, y `x-amz-cf-pop` es distinto en cada una. ¿Cuál es la explicación más probable?
   - A) Las dos solicitudes llegaron a POP distintos, y cada ubicación de borde almacena en caché solo los objetos que recibió.
   - B) El almacenamiento en caché de la distribución no funciona.
   - C) Las solicitudes `HEAD` nunca se almacenan en caché.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Las dos solicitudes llegaron a POP distintos, y cada ubicación de borde almacena en caché solo los objetos que recibió.**

**Explicación:** Ni el enrutamiento DNS ni el anycast garantizan que las solicitudes consecutivas lleguen al mismo POP. Compara `x-amz-cf-pop` antes de sacar conclusiones; la expulsión de la caché, el contenido de la clave de caché y `Cache-Control` del origen son las otras causas que enumera el Centro de conocimiento.

</details>

8. Una respuesta muestra `x-cache: Hit from cloudfront`, `date: Thu, 19 Nov 2026 09:00:00 GMT` y `age: 7200`. ¿Qué puedes concluir?
   - A) El origen generó esta respuesta hace dos horas y el borde sirvió la copia almacenada; `date` más `age` corresponde aproximadamente a la hora actual: las 11:00 GMT.
   - B) Se contactó al origen para esta solicitud y tardó 7.200 ms en responder.
   - C) El objeto vencerá dentro de 7.200 segundos.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) El origen generó esta respuesta hace dos horas y el borde sirvió la copia almacenada; `date` más `age` corresponde aproximadamente a la hora actual: las 11:00 GMT.**

**Explicación:** La RFC 9111 define `Age` como los segundos transcurridos desde que la respuesta se generó o validó en el origen, y su presencia implica que el origen no generó la respuesta para esta solicitud. La vigencia restante es la duración de vigencia (según `s-maxage` o `max-age`, dentro de los ajustes del TTL) menos `Age`, no `Age` en sí.

</details>

9. Un ALB interno es un origen de VPC de CloudFront. ¿Qué origen de entrada para el grupo de seguridad es la opción **más restrictiva** que ofrece la Guía para desarrolladores?
   - A) La lista de prefijos administrada de CloudFront `com.amazonaws.global.cloudfront.origin-facing`.
   - B) El grupo de seguridad administrado por el servicio `CloudFront-VPCOrigins-Service-SG`.
   - C) El CIDR de la VPC.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El grupo de seguridad administrado por el servicio `CloudFront-VPCOrigins-Service-SG`.**

**Explicación:** La lista de prefijos administrada contiene todos los servidores de CloudFront que se comunican con los orígenes, por lo que permite cualquier distribución; el grupo de servicio de origen de VPC restringe el tráfico a tus distribuciones y solo existe después de crear el origen de VPC. No edites ese grupo ni crees otro con el mismo prefijo de nombre. El CIDR de la VPC no es en absoluto el origen del tráfico de CloudFront.

</details>

10. Un cliente de Internet resuelve el nombre DNS del ALB interno e intenta conectarse. ¿Por qué falla antes incluso de que se evalúe alguna regla del grupo de seguridad?
   - A) El nombre DNS de un balanceador de carga interno no se resuelve fuera de la VPC.
   - B) Los nodos de un balanceador de carga interno solo tienen direcciones IP privadas, así que nada en Internet puede enrutar tráfico hacia ellos; el nombre se resuelve públicamente, pero apunta a esas direcciones privadas.
   - C) CloudFront bloquea al cliente.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Los nodos de un balanceador de carga interno solo tienen direcciones IP privadas, así que nada en Internet puede enrutar tráfico hacia ellos; el nombre se resuelve públicamente, pero apunta a esas direcciones privadas.**

**Explicación:** La guía de ELB indica que el nombre DNS de un balanceador de carga interno se resuelve públicamente a las direcciones IP privadas de los nodos, por lo que solo los clientes con acceso a la VPC pueden alcanzarlo. Es una propiedad del enrutamiento, así que se mantiene incluso si después se flexibiliza una regla del grupo de seguridad. CloudFront ni siquiera forma parte de la ruta de este cliente.

</details>

11. Un revisor objeta que la VPC que está detrás de un origen de VPC tiene conectado un gateway de Internet. ¿Qué afirmación es correcta?
   - A) El gateway de Internet es necesario; indica que la VPC puede recibir tráfico de Internet, pero no se usa para enrutar al origen y no hace falta cambiar la tabla de rutas.
   - B) El gateway de Internet significa que la subred del origen debe convertirse en pública.
   - C) Hay que quitar el gateway de Internet para que funcione un origen de VPC.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) El gateway de Internet es necesario; indica que la VPC puede recibir tráfico de Internet, pero no se usa para enrutar al origen y no hace falta cambiar la tabla de rutas.**

**Explicación:** CloudFront llega al origen a través de una ENI administrada por el servicio en la subred privada. El origen permanece en una subred privada sin una dirección pública; el gateway de Internet es solo un requisito previo a nivel de VPC.

</details>

12. Origin Shield está habilitado. En los registros estándar, ¿qué campo y valor indican que una solicitud fue atendida por Origin Shield y no por un POP o una caché regional?
   - A) `x-edge-result-type` = `RefreshHit`.
   - B) `x-edge-detailed-result-type` = `OriginShieldHit`.
   - C) `x-edge-result-type` = `Miss`.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) `x-edge-detailed-result-type` = `OriginShieldHit`.**

**Explicación:** `x-edge-detailed-result-type` repite `x-edge-result-type`, salvo en casos como los aciertos de Origin Shield. Una solicitud enrutada a la caché de borde regional que actúa como Origin Shield se registra como `Hit`, no como `OriginShieldHit`.

</details>

Finalización: explica cada respuesta con una regla del cuaderno y adjunta tus observaciones sobre los encabezados o etiqueta el trabajo como **revisión de diseño**.
