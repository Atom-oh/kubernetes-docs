# Cuestionario sobre LLM Gateway (puerta de enlace de inferencia)

Este cuestionario comprueba las garantías y los límites del diseño propuesto: reservas, semántica de caché, autorización, streaming, PII, guardrails y enrutamiento con conocimiento del contexto. No afirma que todas las puertas de enlace mencionadas implementen este diseño.

## Preguntas de opción múltiple

### 1. ¿Por qué una puerta de enlace reserva recursos antes del despacho y liquida después?

- A. SSE requiere dos autenticaciones
- B. El uso final se desconoce al admitir la solicitud, por lo que las solicitudes simultáneas necesitan reservas atómicas de cuota y dinero
- C. Todos los errores HTTP son gratuitos
- D. Una estimación de tokens de entrada garantiza un límite monetario estricto

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. El uso final se desconoce al admitir la solicitud, por lo que las solicitudes simultáneas necesitan reservas atómicas de cuota y dinero**

**Explicación:**
Antes del despacho, reserve en función de la entrada inspeccionada de cada llamada y de un límite de costo conservador, incluidas las llamadas facturables al enrutador, los filtros, los guardrails y los reintentos. Rechazar la solicitud principal no elimina los cargos auxiliares ya incurridos. Descontar solo TPM no reserva dinero. Sustituya las reservas por los cargos reales de forma idempotente; los flujos interrumpidos pueden no incluir el uso final, así que mantenga una reserva adecuada hasta la conciliación en lugar de suponer que el costo es cero.

</details>

### 2. ¿Qué afirmación sobre la conservación de la caché de prompts es correcta?

- A. Cada byte JSON HTTP sin procesar forma parte de la clave de caché de todos los proveedores
- B. Conserve los prefijos de prompt y tokens específicos del proveedor, junto con los controles de caché compatibles; el formato del contenedor JSON, por sí solo, no tiene por qué invalidar la reutilización
- C. Las tasas de aciertos de caché de los agentes de programación siempre superan el 90 %
- D. La conversión entre protocolos nunca puede preparar la caché de destino

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Conserve los prefijos de prompt y tokens específicos del proveedor, junto con los controles de caché compatibles; el formato del contenedor JSON, por sí solo, no tiene por qué invalidar la reutilización**

**Explicación:**
Anthropic describe segmentos de prompt idénticos mediante puntos de ruptura de caché; vLLM aplica hash a bloques de tokens y al contexto adicional. Una conversión estable puede producir prefijos reutilizables en el lado de destino. Las transformaciones obligatorias por política tienen prioridad sobre el reenvío sin cambios, y el ahorro de caché debe medirse para el modelo, el TTL y la carga de trabajo seleccionados.

</details>

### 3. ¿Por qué hay que volver a autorizar después de una conmutación por error o de sustituir el modelo por otro de una categoría de presupuesto inferior?

- A. Todas las alternativas son automáticamente más baratas
- B. Es posible que el nuevo modelo, proveedor o región no haya superado las comprobaciones originales de autorización y privacidad
- C. Los interruptores automáticos conceden permisos temporales
- D. Un nombre de modelo parecido demuestra que las capacidades son equivalentes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Es posible que el nuevo modelo, proveedor o región no haya superado las comprobaciones originales de autorización y privacidad**

**Explicación:**
Vuelva a comprobar el modelo, la región, la privacidad, las capacidades necesarias y el presupuesto para el destino real. Mantenga el modelo original solo si sigue superando todas las comprobaciones; de lo contrario, deniegue la solicitud. La resolución de alias y el orden lexicográfico de versiones no constituyen autorización.

</details>

### 4. ¿Cuándo debe detenerse la conmutación por error transparente de una respuesta transmitida en streaming?

- A. Solo después del primer token de texto imprimible
- B. Una vez que se hayan enviado encabezados al cliente o se hayan emitido eventos con estado o de herramientas, incluso antes de que haya tokens de texto
- C. Solo después del evento de uso final
- D. Nunca; dos proveedores pueden compartir de forma segura una respuesta

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Una vez que se hayan enviado encabezados al cliente o se hayan emitido eventos con estado o de herramientas, incluso antes de que haya tokens de texto**

**Explicación:**
Una vez que la respuesta quedó comprometida hacia el cliente, un reintento transparente puede duplicar contenido o actividad de herramientas y generar cargos adicionales. Termine con la semántica de error del protocolo del cliente y registre el uso incompleto. Antes de comprometer la respuesta, los reintentos siguen necesitando límites de intentos/plazo y contabilización de los posibles cargos del proveedor. La salida debe inspeccionarse antes de publicarse; el almacenamiento en búfer puede aumentar el TTFT percibido por el usuario.

</details>

### 5. ¿Cómo deben interactuar los requisitos de privacidad con el costo de la caché?

- A. Desactive el enmascaramiento siempre que no haya un acierto en la caché de prefijos
- B. Aplique los controles de privacidad obligatorios, use transformaciones estables y acotadas cuando sean seguras, y mida el impacto en caché/latencia
- C. Inspeccione solo el texto del usuario porque los argumentos de herramientas nunca contienen PII
- D. Restaure cualquier marcador de posición proporcionado por el cliente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Aplique los controles de privacidad obligatorios, use transformaciones estables y acotadas cuando sean seguras, y mida el impacto en caché/latencia**

**Explicación:**
Los datos sensibles pueden aparecer en herramientas, resultados y archivos adjuntos, además de en el texto. Si no se puede realizar una inspección compatible, se debe bloquear o usar un destino aprobado. Asocie los mapeos al tenant, principal y sesión autenticados, y autorice su restauración; perderlos puede afectar a la corrección. La detección tiene falsos negativos, así que ni una puerta de enlace ni un clasificador demuestran que no haya ninguna divulgación.

</details>

### 6. ¿Qué integración de Bedrock Guardrails es adecuada?

- A. Crear un guardrail hace que se aplique automáticamente a todas las llamadas
- B. Use los campos de guardrail de la API seleccionada, valide el alcance y exija los identificadores y versiones aprobados cuando la API lo permita
- C. Use el modo asíncrono para garantizar el enmascaramiento de información sensible
- D. Use los mismos campos JSON de nivel superior en todas las API de Bedrock

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Use los campos de guardrail de la API seleccionada, valide el alcance y exija los identificadores y versiones aprobados cuando la API lo permita**

**Explicación:**
Converse usa `guardrailConfig`; InvokeModel usa los parámetros de operación `guardrailIdentifier`/`guardrailVersion` (encabezados HTTP). `guardContent` puede delimitar la evaluación, y ApplyGuardrail evalúa contenido por separado sin invocar el modelo. Las condiciones de IAM adecuadas y la prevención de elusiones refuerzan la política de la puerta de enlace. El streaming asíncrono puede publicar contenido antes de inspeccionarlo y no admite el enmascaramiento de información sensible; los registros y trazas también necesitan protección.

</details>

### 7. ¿Qué importa al insertar un prompt de política de puerta de enlace cerca de un punto de ruptura de caché?

- A. Se garantiza un acierto en la caché para todas las solicitudes posteriores
- B. Mantenga estable el contenido de la política dentro del límite de caché previsto y elimine duplicados solo en los metadatos autenticados de la puerta de enlace
- C. Un bloque posterior a un marcador de caché siempre invalida el segmento anterior
- D. Un hash coincidente proporcionado por el cliente demuestra que se aplicó la política

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Mantenga estable el contenido de la política dentro del límite de caché previsto y elimine duplicados solo en los metadatos autenticados de la puerta de enlace**

**Explicación:**
La reutilización de caché depende de que los segmentos compatibles sean idénticos, de los requisitos del modelo, la longitud mínima, el alcance y el TTL. Un bloque posterior queda fuera de un segmento almacenado antes en caché, en lugar de invalidarlo necesariamente. Un marcador de política copiado no debe evitar la inserción obligatoria ni el análisis. Los prompts orientan, pero no constituyen una autorización ejecutable.

</details>

### 8. ¿Dónde debe aplicarse en última instancia la autorización de herramientas?

- A. Solo en un prompt del sistema
- B. Solo mediante coincidencia con expresiones regulares de cadenas de shell peligrosas
- C. En el ejecutor de herramientas, con comprobaciones de salida de la puerta de enlace como capa adicional
- D. Solo después de que el proveedor devuelva el uso final

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. En el ejecutor de herramientas, con comprobaciones de salida de la puerta de enlace como capa adicional**

**Explicación:**
Las puertas de enlace deben almacenar en búfer y validar los argumentos completos de las llamadas a herramientas, pero no pueden cubrir las vías de elusión ni las herramientas del proveedor que ya se hayan ejecutado. El ejecutor necesita identidad autenticada, autorización de recursos/argumentos, validación de esquema, privilegio mínimo, aislamiento y aprobación de acciones sensibles. Las etiquetas de rol del modelo y los nombres de herramientas por sí solos no demuestran confianza.

</details>

### 9. ¿Qué invariante respalda los presupuestos monetarios distribuidos conservadores?

- A. Cada réplica puede gastar de forma independiente el límite completo del equipo
- B. Lo gastado más las concesiones reservadas pendientes se mantiene dentro del límite; las reservas y la conciliación son duraderas e idempotentes
- C. La suma de las concesiones es automáticamente el límite máximo de exceso de gasto
- D. Las concesiones vencidas siempre se pueden volver a emitir de inmediato

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Lo gastado más las concesiones reservadas pendientes se mantiene dentro del límite; las reservas y la conciliación son duraderas e idempotentes**

**Explicación:**
Las concesiones descontadas del presupuesto disponible son capacidad reservada, no una asignación para gastar por encima del límite. Use límites de costo conservadores, admisión local atómica, ID duraderos y conciliación. El vencimiento detiene nuevas admisiones, pero el trabajo o los informes sin resolver impiden recuperar la capacidad de forma segura. Las llamadas facturables a componentes auxiliares, al modelo principal y a las comprobaciones de salida consumen el mismo presupuesto mediante sus propias reservas. Las concesiones monetarias no convierten automáticamente los contadores de velocidad en algo global.

</details>

### 10. ¿Cómo puede influir el contexto de infraestructura en el enrutamiento?

- A. Una región permitida lenta autoriza cualquier región más rápida
- B. El estado de salud y la carga pueden seleccionar entre destinos ya autorizados, pero nunca ampliar los permisos de modelo/región/privacidad
- C. La región de un endpoint de origen demuestra que todo el procesamiento ocurre allí
- D. Un fallo del clasificador desactiva la política de presupuesto

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. El estado de salud y la carga pueden seleccionar entre destinos ya autorizados, pero nunca ampliar los permisos de modelo/región/privacidad**

**Explicación:**
Aplique las señales de salud a decisiones de disponibilidad/endpoint dentro del límite de la política. Los perfiles de inferencia de Bedrock pueden enrutar fuera de la región de origen, así que compruebe todos los destinos. La adecuación final del contexto debe incluir la entrada transformada más la asignación de salida/razonamiento del destino. Solo se permite volver al modelo original si sigue superando todas las comprobaciones obligatorias.

</details>

### 11. ¿Cómo debe gestionar una puerta de enlace los endpoints de recuento de tokens?

- A. Siempre devuelve HTTP 200, incluso para solicitudes no autorizadas
- B. Conserve la autenticación, la autorización, los errores de validación y los límites de frecuencia independientes; identifique cualquier alternativa aproximada opcional
- C. Presupone que una estimación de bytes/4 es el recuento exacto del proveedor
- D. Ignora el tamaño de la solicitud y los límites de CPU porque el recuento no es inferencia

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Conserve la autenticación, la autorización, los errores de validación y los límites de frecuencia independientes; identifique cualquier alternativa aproximada opcional**

**Explicación:**
El recuento puede tener errores de validación específicos del proveedor y sus propios límites de RPM. No es un cargo por gasto de inferencia, pero consume recursos de la puerta de enlace/del proveedor. Una alternativa aproximada opcional no puede anular una denegación, ocultar su procedencia ni garantizar una adecuación exacta al contexto. Una capa de compatibilidad específica de un producto no es un requisito universal de API.

</details>

### 12. ¿Por qué se deben evitar los ID de usuario/clave y los prompts sin procesar en las etiquetas de métricas?

- A. Para comprimir SSE
- B. Para limitar la cardinalidad y reducir la exposición de identidades/contenido; aun así, se debe restringir el acceso de lectura
- C. Porque las métricas nunca pueden contener etiquetas de equipo
- D. Porque el cifrado elimina todos los riesgos de las etiquetas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Para limitar la cardinalidad y reducir la exposición de identidades/contenido; aun así, se debe restringir el acceso de lectura**

**Explicación:**
Use etiquetas acotadas y revisadas, como el modelo/proveedor canónico y, cuando corresponda, el equipo configurado. Proteja los endpoints de métricas/administración y evite incluir prompts en atributos de traza o errores. Versione las convenciones semánticas y verifique los nombres del exportador. Una cardinalidad baja no autoriza por sí sola el acceso público.

</details>
