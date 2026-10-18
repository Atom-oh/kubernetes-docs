# Cuestionario con perspectiva de servicios financieros

Este cuestionario evalúa tu comprensión de la elección de consorcio, la privacidad, la gestión de claves y las cuestiones de revisión.

## Preguntas de opción múltiple

1. ¿Qué criterio se propone para determinar si un problema requiere blockchain?
   - A) Si el volumen de datos es suficientemente grande
   - B) Si puedes expresar en una oración «por qué este problema debe carecer de árbitro»; si no, compara primero las alternativas
   - C) Si participan cinco instituciones o más
   - D) Si se requiere procesamiento en tiempo real

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Si puedes expresar en una oración «por qué este problema debe carecer de árbitro»; si no, compara primero las alternativas**

**Explicación:**
El capítulo parte de la pregunta «¿se puede llegar a un acuerdo sin un árbitro de confianza?» para comparar los costos y beneficios de blockchain. Si una organización controla los datos o las partes confían en un árbitro, empieza por comparar alternativas de bases de datos/registros de auditoría y evalúa los requisitos reales de verificación independiente y gobernanza. No deduzcas que el valor siempre es nulo a partir de la cantidad de instituciones. Cuando el requisito principal es detectar manipulaciones, pueden bastar registros de solo anexado firmados, cadenas de hash o almacenamiento WORM, con operaciones más sencillas.
</details>

2. ¿Qué debe evaluarse antes de afirmar que una elección de red cumple los requisitos financieros?
   - A) El rendimiento y las comisiones
   - B) Los requisitos de identificación de contrapartes y de ubicación de datos para la actividad y jurisdicción concretas
   - C) La gobernanza y la gestión de errores
   - D) La comodidad de desarrollo y la contratación

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Los requisitos de identificación de contrapartes y de ubicación de datos para la actividad y jurisdicción concretas**

**Explicación:**
Los sistemas públicos y los autorizados pueden usar controles distintos. La pertenencia a un consorcio por sí sola no demuestra cumplimiento de KYC/AML ni de privacidad; solicita la evaluación jurídica y de cumplimiento correspondiente.
</details>

3. ¿Qué valor sustancial queda al elegir una cadena de consorcio y por qué conviene definirlo así durante la revisión?
   - A) La resistencia a la censura, un valor que también reconocen los reguladores
   - B) La reducción del costo de conciliación entre instituciones, porque decir «descentralizado, funciona sin confianza» no resiste la pregunta «entonces, ¿quién controla la membresía?»
   - C) La participación sin permisos, porque garantiza la escalabilidad
   - D) No se necesita un árbitro, porque no queda ninguna parte operadora

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) La reducción del costo de conciliación entre instituciones, porque decir «descentralizado, funciona sin confianza» no resiste la pregunta «entonces, ¿quién controla la membresía?»**

**Explicación:**
Al pasar a un consorcio desaparece gran parte del valor de una cadena pública (resistencia a la censura, participación sin permisos y ausencia de árbitro), porque una parte controla la membresía y esa parte, en la práctica, es el árbitro. Lo que queda como valor sustancial es **«hacer que las instituciones vean los mismos datos para eliminar el trabajo de conciliación»**, un beneficio real. Definir el valor de esta manera desde el principio es defendible durante una revisión.
</details>

4. ¿Cuál es el riesgo concreto de almacenar datos cifrados en una blockchain?
   - A) La degradación del rendimiento debida al cifrado
   - B) Pueden persistir copias históricas del texto cifrado y una clave comprometida puede exponer los registros cifrados con esa clave
   - C) Los datos cifrados quedan fuera del consenso
   - D) La clave de cifrado se almacena junto con los datos en la cadena

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Pueden persistir copias históricas del texto cifrado y una clave comprometida puede exponer los registros cifrados con esa clave**

**Explicación:**
Volver a cifrar los registros nuevos no elimina las copias anteriores. La purga de datos privados autorizados tiene una semántica distinta; valida los requisitos de retención, ciclo de vida de claves y obligaciones jurídicas en lugar de afirmar que todas las cadenas tienen el mismo comportamiento de eliminación.
</details>

5. ¿En qué punto entra en conflicto la gestión de claves de validadores PoS con las prácticas habituales de alta disponibilidad?
   - A) Las claves deben replicarse en varias regiones
   - B) Firmantes sin coordinación pueden producir mensajes conflictivos que exponen al mismo validador al slashing
   - C) Los HSM no admiten varias instancias
   - D) Rotar las claves requiere una interrupción

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Firmantes sin coordinación pueden producir mensajes conflictivos que exponen al mismo validador al slashing**

**Explicación:**
Usa fencing y conserva el historial de protección contra slashing. Un firmante distribuido de forma deliberada requiere coordinación probada; las firmas duplicadas idénticas no equivalen automáticamente a un conflicto que pueda provocar slashing.
</details>

6. ¿Qué tipo de respuesta requiere la pregunta de revisión «¿cómo reviertes una transacción incorrecta?»?
   - A) Presentar un procedimiento técnico para revertir la cadena
   - B) Un proceso, no tecnología: conservar la original y emitir una transacción compensatoria que corrija el resultado, igual que un asiento de reversión contable
   - C) Que el operador del consorcio elimine el bloque
   - D) Explicar que la inmutabilidad es una ventaja y no hace falta revertir nada

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Un proceso, no tecnología: conservar la original y emitir una transacción compensatoria que corrija el resultado, igual que un asiento de reversión contable**

**Explicación:**
La inmutabilidad que se presenta como una ventaja supone un problema en las operaciones financieras. Ocurren transacciones incorrectas, transferencias equivocadas y errores del sistema, y las instituciones tienen obligaciones y procedimientos para corregirlos. La respuesta es emitir una transacción compensatoria en lugar de «revertir la cadena»; la revisión requiere documentar el procedimiento y la autoridad que lo aprueba. Esto también se relaciona con la ausencia de atomicidad al integrar con la infraestructura existente (patrones Saga/outbox).
</details>

7. ¿Qué dos aspectos se señalan como los menos preparados para una revisión de servicios financieros?
   - A) La medición del rendimiento y la estimación de costos
   - B) Los procedimientos de corrección de errores y la estrategia de salida
   - C) La configuración de red y la política de firewall
   - D) La dotación de personal de desarrollo y los planes de capacitación

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Los procedimientos de corrección de errores y la estrategia de salida**

**Explicación:**
En una revisión, «no se puede revertir» se convierte en un punto débil; la respuesta debe prepararse como un proceso (transacciones compensatorias), no como tecnología. Casi nunca se prepara una estrategia de salida: ante la disolución del consorcio, la retirada de un miembro o el cierre del sistema, los datos financieros tienen obligaciones de retención, así que **«apagamos la cadena» no es el final**. El formato de exportación del libro mayor, la parte responsable de la retención, la gestión de los datos del miembro que se retira y el acceso a los registros deben figurar en el acuerdo del consorcio, y el diseño técnico debe respaldarlos.
</details>

8. ¿Cuál es la dificultad más sustancial al integrar con la infraestructura financiera existente y cómo debe abordarse?
   - A) La brecha de rendimiento: se resuelve agregando nodos de cadena
   - B) La ausencia de atomicidad: una transacción en una base de datos existente y una transacción en la cadena no pueden vincularse en una sola unidad atómica, así que hay que incorporar desde el principio diseños de consistencia eventual como Saga/outbox
   - C) La sincronización horaria: se resuelve configurando NTP
   - D) Las diferencias de protocolo: se resuelven con una traducción de gateway

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) La ausencia de atomicidad: una transacción en una base de datos existente y una transacción en la cadena no pueden vincularse en una sola unidad atómica, así que hay que incorporar desde el principio diseños de consistencia eventual como Saga/outbox**

**Explicación:**
Un fallo entre escribir en la base de datos y enviar la transacción a la cadena crea una inconsistencia, y no es posible vincular ambas operaciones en una transacción distribuida. Se necesitan patrones Saga u outbox, conectados con el procedimiento de transacción compensatoria. Como es una decisión arquitectónica, debe **abordarse pronto en el diseño**; si se agrega más adelante, los problemas de coherencia de datos aparecen en producción. Añadir réplicas de nodos completos no aumenta automáticamente la capacidad de escritura/consenso de la cadena base, aunque puede elevar la capacidad agregada de lectura/RPC y la disponibilidad.
</details>

9. ¿Qué etapa debe preceder a la validación técnica en una ruta de adopción realista?
   - A) Prueba de concepto y piloto
   - B) Acordar las funciones de los participantes, la gobernanza y el beneficio medible frente a alternativas más sencillas
   - C) Dimensionar la infraestructura y estimar los costos
   - D) Crear la pila de monitorización

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Acordar las funciones de los participantes, la gobernanza y el beneficio medible frente a alternativas más sencillas**

**Explicación:**
No afirmes que un acuerdo institucional tiene siempre un valor nulo ni que cumple automáticamente los requisitos. La revisión trata de requisitos explícitos, supuestos de confianza y responsabilidades operativas.
</details>
