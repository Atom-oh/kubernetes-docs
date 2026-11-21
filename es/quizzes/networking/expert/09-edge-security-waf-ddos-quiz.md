# 09. Seguridad perimetral: cuestionario sobre WAF y defensa contra DDoS

> **Última actualización**: 19 de noviembre de 2026

Vuelve al [cuaderno](../../../networking/expert/09-edge-security-waf-ddos.md).
Elige una respuesta por pregunta y explica qué regla del cuaderno la respalda.
Estos son ejercicios de razonamiento de diseño, no afirmaciones de que se haya implementado una ACL web.

1. Una botnet envía una inundación SYN a una distribución de CloudFront cuyo origen es un ALB interno detrás de un VPC origin. ¿Por qué el ALB no recibe una inundación SYN?
   - A) En el perímetro, el proxy TCP SYN de Shield verifica el protocolo de enlace (cookies SYN sin estado) antes de que una conexión llegue al servicio, y CloudFront mantiene sus propias conexiones persistentes al origen.
   - B) La ACL web de WAF bloquea los paquetes SYN con una regla basada en tasa.
   - C) El grupo de seguridad del ALB descarta los paquetes SYN que llegan demasiado rápido.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) En el perímetro, el proxy TCP SYN de Shield verifica el protocolo de enlace (cookies SYN sin estado) antes de que una conexión llegue al servicio, y CloudFront mantiene sus propias conexiones persistentes al origen.**

**Explicación:** Una inundación SYN agota la cola de conexiones a medio abrir del listener. En este caso, el listener es CloudFront, y el proxy SYN de Shield solo deja pasar las conexiones que completan el protocolo de enlace; una conexión nueva de un usuario no es una conexión nueva al origen. AWS WAF inspecciona solicitudes HTTP, no segmentos TCP, y un grupo de seguridad no limita la tasa.

</details>

2. ¿Qué necesita el atacante para llevar a cabo un ataque de reflexión UDP, y qué práctica de red lo impide?
   - A) Completar un protocolo de enlace TCP con el reflector; TLS en todas partes lo impide.
   - B) Poder falsificar la dirección de la víctima como dirección de origen; la validación de direcciones de origen (BCP 38) lo impide.
   - C) Una solicitud HTTP válida; una regla de WAF basada en tasa lo impide.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Poder falsificar la dirección de la víctima como dirección de origen; la validación de direcciones de origen (BCP 38) lo impide.**

**Explicación:** El atacante envía solicitudes UDP pequeñas (DNS, NTP, SSDP, CLDAP, Memcached y otros) con la dirección de la víctima como origen, y los reflectores envían respuestas mucho más grandes a la víctima; para DNS, el documento técnico de AWS indica una amplificación de entre 28 y 54 veces. Las redes que validan las direcciones de origen impiden la falsificación.

</details>

3. Una solicitud coincide con una regla cuya acción es CAPTCHA y contiene un token CAPTCHA válido y no vencido. ¿Qué hace AWS WAF?
   - A) Bloquea la solicitud y envía un nuevo desafío.
   - B) Permite la solicitud inmediatamente y detiene la evaluación.
   - C) La trata como si la acción fuera Count y continúa con las reglas restantes.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) La trata como si la acción fuera Count y continúa con las reglas restantes.**

**Explicación:** CAPTCHA y Challenge no son acciones terminales cuando el token es válido y no ha vencido, pero sí lo son (la solicitud se bloquea, con un desafío o uno silencioso) cuando falta el token, no es válido o ha vencido. Allow y Block siempre terminan la evaluación; Count nunca lo hace. De forma predeterminada, las solicitudes bloqueadas reciben `403 (Forbidden)`.

</details>

4. ¿Qué configuración de una regla basada en tasa **no** es válida?
   - A) Ventana de evaluación de 300 segundos, límite de 100, acción Block.
   - B) Ventana de evaluación de 600 segundos, límite de 10, acción Count.
   - C) Ventana de evaluación de 300 segundos, límite de 100, acción Allow.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Ventana de evaluación de 300 segundos, límite de 100, acción Allow.**

**Explicación:** Una regla basada en tasa puede usar cualquier acción de regla excepto Allow. La ventana de evaluación puede ser de 60, 120, 300 o 600 segundos (300 de forma predeterminada), y el límite mínimo es 10, así que A y B son válidas.

</details>

5. Durante una inundación HTTP, un ingeniero reduce el límite de una regla basada en tasa que ya está bloqueando tráfico. ¿Qué debería esperar el equipo justo después del cambio?
   - A) El nuevo límite se aplica de inmediato y se conservan los conteos anteriores.
   - B) El cambio restablece los conteos de la regla y puede pausar la limitación de tasa hasta un minuto.
   - C) La regla permanece inactiva hasta que haya transcurrido la siguiente ventana de evaluación completa.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El cambio restablece los conteos de la regla y puede pausar la limitación de tasa hasta un minuto.**

**Explicación:** Cambiar el límite, la ventana de evaluación, la agregación, la configuración de IP reenviada o el alcance restablece los conteos. Además, la limitación de tasa es aproximada: puede comenzar varios minutos después de que se supere la tasa y continuar brevemente después de que esta disminuya. Planifica los cambios de límite de tasa antes de un incidente, no durante uno.

</details>

6. Quieres ver qué bloquearía cada regla de `AWSManagedRulesCommonRuleSet` antes de aplicarla. ¿Qué configuración debes usar?
   - A) Anular la acción de retorno del grupo de reglas y establecerla en Count.
   - B) Establecer la acción predeterminada de la ACL web en Count.
   - C) Anular la acción de cada regla y establecerla en Count con `RuleActionOverrides`.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Anular la acción de cada regla y establecerla en Count con `RuleActionOverrides`.**

**Explicación:** Con una anulación por regla, las solicitudes que coinciden se tratan como si la acción de esa regla fuera Count, y el grupo sigue evaluando las demás reglas. Anular la acción de retorno del grupo de reglas y establecerla en Count no cambia la forma en que el grupo evalúa las solicitudes: se detiene en la primera coincidencia terminal, por lo que las reglas posteriores del grupo nunca se ejecutan para esa solicitud. La acción predeterminada solo puede ser Allow o Block.

</details>

7. La regla `block-bad-ua`, con prioridad 50, es una instrucción de coincidencia de etiquetas para `awswaf:managed:aws:core-rule-set:NoUserAgent_Header`. El conjunto de reglas principales está en la prioridad 100, y esa regla se ha anulado para que use Count. ¿Por qué `block-bad-ua` nunca coincide?
   - A) Los grupos de reglas administradas no añaden etiquetas.
   - B) Una etiqueta solo está disponible para las reglas que se evalúan después de la regla que la añadió, y la prioridad 50 se ejecuta antes que la prioridad 100.
   - C) Se descartan las etiquetas de las reglas Count.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Una etiqueta solo está disponible para las reglas que se evalúan después de la regla que la añadió, y la prioridad 50 se ejecuta antes que la prioridad 100.**

**Explicación:** AWS WAF evalúa las reglas empezando por la prioridad numérica más baja, y la etiqueta permanece en la solicitud durante el resto de esa evaluación, donde las reglas posteriores la leen mediante una instrucción de coincidencia de etiquetas. Todos los grupos de reglas de AWS Managed Rules añaden etiquetas, y establecer una regla en Count para que solo etiquete es el patrón principal para usar etiquetas. Mueve la regla de coincidencia de etiquetas para que quede después del grupo.

</details>

8. Creas una ACL web con la CLI para proteger una distribución de CloudFront. ¿Qué afirmación es correcta?
   - A) Usa `--scope=CLOUDFRONT --region=us-east-1`; esta ACL web global no se puede asociar también al ALB.
   - B) Usa `--scope=REGIONAL` en la región del ALB de origen y asocia también al ALB la misma ACL web.
   - C) Usa `--scope=CLOUDFRONT` en cualquier región, porque CloudFront es global.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Usa `--scope=CLOUDFRONT --region=us-east-1`; esta ACL web global no se puede asociar también al ALB.**

**Explicación:** Una ACL web para CloudFront es global y usa la región fija US East (N. Virginia); la API y los SDK usan el endpoint `us-east-1`. Una ACL web asociada a una distribución de CloudFront no se puede asociar a otro tipo de recurso, así que, si quieres una segunda inspección, el ALB necesita su propia ACL web `REGIONAL`.

</details>

9. Una ACL web usa `AWSManagedRulesCommonRuleSet` (700 WCU), `AWSManagedRulesSQLiRuleSet` (200 WCU), `AWSManagedRulesKnownBadInputsRuleSet` (200 WCU) y un grupo de reglas personalizado creado con una capacidad de 500 WCU que actualmente contiene reglas por un valor de 120 WCU. ¿Cuál es el resultado?
   - A) 1.220 WCU, dentro del precio base.
   - B) 1.600 WCU: permitido, porque el máximo es 5.000, pero supera las 1.500 WCU incluidas en el precio base, por lo que se aplican cargos adicionales.
   - C) Rechazado, porque una ACL web no puede superar las 1.500 WCU.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) 1.600 WCU: permitido, porque el máximo es 5.000, pero supera las 1.500 WCU incluidas en el precio base, por lo que se aplican cargos adicionales.**

**Explicación:** Usar un grupo de reglas en una ACL web cuesta la capacidad inmutable establecida al crearlo, no la de su contenido actual, por lo que el grupo personalizado cuenta como 500. 700 + 200 + 200 + 500 = 1.600. El precio base incluye 1.500 WCU, y la capacidad por encima de ese valor conlleva cargos adicionales por niveles, hasta el máximo de 5.000 WCU.

</details>

10. Un equipo se suscribe a Shield Advanced y quiere que el Shield Response Team se ponga en contacto de forma proactiva durante un ataque. ¿Qué debe tener preparado?
   - A) Nada más; la suscripción lo incluye.
   - B) Una ACL web regional en cada ALB.
   - C) Un plan de Business Support o Enterprise Support para acceder al SRT, y detección basada en el estado de los recursos, con una comprobación de estado de Route 53 en el recurso protegido.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Un plan de Business Support o Enterprise Support para acceder al SRT, y detección basada en el estado de los recursos, con una comprobación de estado de Route 53 en el recurso protegido.**

**Explicación:** El SRT requiere uno de esos planes de soporte. La participación proactiva solo está disponible para los recursos con detección basada en el estado, que utiliza comprobaciones de estado de Route 53. Shield Advanced también protege únicamente los recursos que añades explícitamente; Shield Standard es la capa automática sin costo.

</details>

11. Un equipo propone un ALB público como origen, con un grupo de seguridad que admite la lista de prefijos administrada orientada al origen de CloudFront. ¿Por qué este curso considera que es menos seguro que un VPC origin que apunta a un ALB interno?
   - A) La lista de prefijos admite cualquier distribución de CloudFront, incluso una que cree un atacante, mientras que un ALB interno no tiene ninguna ruta desde Internet.
   - B) La lista de prefijos no incluye las direcciones IPv4 de CloudFront.
   - C) Un ALB público no puede usar TLS.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) La lista de prefijos admite cualquier distribución de CloudFront, incluso una que cree un atacante, mientras que un ALB interno no tiene ninguna ruta desde Internet.**

**Explicación:** Los controles del perímetro solo se aplican a las solicitudes que pasan por tu distribución. Una solicitud procedente de otra distribución omite tu ACL web y tus reglas basadas en tasa. Añadir un encabezado secreto solo ayuda mientras el secreto siga siendo privado. El ocultamiento mediante un ALB interno es una propiedad del enrutamiento, por lo que incluso si después se usa un grupo de seguridad menos estricto, el origen sigue sin ser accesible desde Internet.

</details>

12. Durante una prueba en modo Count, ¿qué evidencia muestra de forma fiable que habría coincidido una regla dentro de un grupo de reglas administradas?
   - A) El campo `nonTerminatingMatchingRules` y las etiquetas en los registros de WAF, además de las métricas de etiquetas.
   - B) La tabla de solicitudes de muestra en la vista de la ACL web.
   - C) El código de estado del registro estándar de CloudFront.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) El campo `nonTerminatingMatchingRules` y las etiquetas en los registros de WAF, además de las métricas de etiquetas.**

**Explicación:** Los registros de WAF enumeran las coincidencias de Count en `nonTerminatingMatchingRules` y las etiquetas añadidas a cada solicitud. La vista de la ACL web no muestra muestras de las reglas Count dentro de grupos de reglas, y las reglas con la acción Count dentro de grupos de reglas no emiten métricas de dimensión de la ACL web. Una coincidencia de Count nunca cambia el código de estado.

</details>

13. En el diseño de referencia, la NetworkPolicy del Pod admite el ingreso desde un `ipBlock` con las subredes del ALB, en lugar de desde las direcciones de los clientes. ¿Por qué?
   - A) El ALB es un proxy, así que el destino Pod IP ve la dirección privada del nodo del ALB; la dirección del cliente llega en `X-Forwarded-For`.
   - B) NetworkPolicy no puede expresar bloques CIDR IPv4.
   - C) CloudFront reescribe la dirección del cliente a la ENI del VPC origin solo para HTTP/3.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) El ALB es un proxy, así que el destino Pod IP ve la dirección privada del nodo del ALB; la dirección del cliente llega en `X-Forwarded-For`.**

**Explicación:** La guía de ELB indica que los registros de acceso del servidor contienen únicamente la dirección del balanceador de carga. La documentación de Kubernetes advierte que el momento de la reescritura —antes o después del procesamiento de NetworkPolicy— depende del plugin, el proveedor de nube y la implementación de Service, así que confirma qué origen observa tu CNI.

</details>

14. En el ejercicio del cuaderno, `rate-login` (ventana de 300 s, límite de 100, agregación por IP, acción Count) ve que `198.51.100.20`, después de una hora sin actividad, envía una única ráfaga aislada de 640 solicitudes `POST /login` en un plazo de 5 minutos. ¿Cuántas solicitudes de esa dirección cuenta la regla aproximadamente, y por qué no es una cifra exacta?
   - A) 640, porque Count cuenta todas las solicitudes que coinciden con la instrucción de reducción de alcance.
   - B) Unas 540, las solicitudes que superan el límite; es una cifra aproximada porque AWS WAF estima la tasa y detecta el exceso con retraso.
   - C) 100, porque el límite restringe el conteo.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Unas 540, las solicitudes que superan el límite; es una cifra aproximada porque AWS WAF estima la tasa y detecta el exceso con retraso.**

**Explicación:** Una regla basada en tasa aplica su acción a las solicitudes coincidentes adicionales de una instancia que supera el límite: 640 - 100 = 540. Esto se cumple en una ráfaga aislada; si la dirección permaneciera por encima del límite, se contarían casi todas sus solicitudes posteriores, porque la regla sigue actuando hasta que la tasa estimada cae por debajo del límite. AWS WAF pondera las solicitudes recientes y limita el valor cerca del valor configurado, pero no exactamente en él. La prueba revela un falso positivo (una NAT de oficina compartida), que el plan resuelve con un conjunto de IP dentro de un `NotStatement` en la instrucción de reducción de alcance.

</details>

Finalización: explica cada respuesta con una regla del cuaderno y etiqueta tu plan de reglas como **escenario resuelto, no medido**.
