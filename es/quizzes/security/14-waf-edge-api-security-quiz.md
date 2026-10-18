# Cuestionario sobre WAF y protección del origen

> **Última actualización**: October 15, 2026

[Lea el capítulo y las fuentes principales](../../security/14-waf-edge-api-security.md)

### 1. ¿Qué recurso de API Gateway admite la asociación directa de WAF documentada?

- A) REST API
- B) Todas las HTTP API
- C) Todas las WebSocket API
- D) Cualquier listener de NLB

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) REST API**

**Explicación:** Use la lista de recursos compatibles. La protección de CloudFront delante de un recurso es distinta de la asociación directa.

</details>

### 2. ¿Qué ocurre después de que coincide un Allow amplio al principio?

- A) Siempre se siguen evaluando las reglas posteriores
- B) La evaluación termina y puede omitir protecciones posteriores
- C) Solo las reglas Count detienen la evaluación
- D) Block predeterminado siempre lo anula

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) La evaluación termina y puede omitir protecciones posteriores**

**Explicación:** Allow y Block terminan la evaluación; Count continúa. Revise la prioridad de las reglas y las excepciones con alcance restringido.

</details>

### 3. ¿Qué comparación de límites de cuerpo es correcta?

- A) ALB siempre inspecciona 64 KB
- B) Todos los recursos tienen límites idénticos
- C) ALB está fijado en 8 KB; CloudFront usa 16 KB de forma predeterminada, con aumentos compatibles hasta 64 KB
- D) Los límites del cuerpo son iguales a los de carga

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) ALB está fijado en 8 KB; CloudFront usa 16 KB de forma predeterminada, con aumentos compatibles hasta 64 KB**

**Explicación:** Los tamaños de inspección son distintos de los límites de carga de la aplicación; la documentación de AWS también excluye la inspección del cuerpo gRPC.

</details>

### 4. ¿Oversize MATCH siempre bloquea la solicitud?

- A) Sí, sin importar la acción
- B) Sí, incluso dentro de NOT
- C) Sí, incluso después de un Allow anterior
- D) No; coincide con la instrucción y el comportamiento final depende de la acción y la composición

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) No; coincide con la instrucción y el comportamiento final depende de la acción y la composición**

**Explicación:** Compruebe la acción, la composición lógica y las reglas de terminación anteriores. MATCH no es por sí sola una acción Block.

</details>

### 5. ¿Por qué el rango de direcciones de CloudFront no basta para identificar la distribución propia?

- A) Otras rutas de CloudFront pueden usar la misma infraestructura
- B) CloudFront no admite HTTPS
- C) ALB no tiene reglas de listener
- D) Todos los encabezados de origen son firmas criptográficas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Otras rutas de CloudFront pueden usar la misma infraestructura**

**Explicación:** Combine las restricciones de red con una condición protegida de encabezado de origen/listener o un diseño compatible con VPC origin, y pruebe las rutas de elusión.

</details>

### 6. ¿Qué ocurre con una instrucción directa de IP reenviada cuando no existe su encabezado y no hay un NOT que la envuelva?

- A) El fallback siempre bloquea
- B) La instrucción no coincide; la ausencia no es lo mismo que el fallback por formato no válido
- C) El encabezado se autentica automáticamente
- D) Siempre se usa la última dirección

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) La instrucción no coincide; la ausencia no es lo mismo que el fallback por formato no válido**

**Explicación:** La ausencia de encabezados no activa el fallback por formato no válido. Un NOT envolvente puede invertir un resultado sin coincidencia y convertirlo en coincidencia. Geo/ASN/rate usan la primera dirección; los IP sets usan la selección FIRST/LAST/ANY configurada.

</details>

### 7. ¿Qué afirmación sobre las reglas de rate es correcta?

- A) Son cuotas exactas por segundo
- B) Cambiar la ventana conserva todos los contadores
- C) El seguimiento es aproximado y los cambios pertinentes de configuración reinician los contadores
- D) Las claves de agregación controladas por el cliente impiden la evasión

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) El seguimiento es aproximado y los cambios pertinentes de configuración reinician los contadores**

**Explicación:** Pruebe la ventana, la agregación, los reinicios, el NAT compartido y la variación de claves controlada por el atacante; aplique las cuotas empresariales en la aplicación.

</details>

### 8. ¿Qué demuestra automáticamente el enmascaramiento de logs de WAF?

- A) Que todas las solicitudes muestreadas están enmascaradas
- B) Que no puede aparecer información sensible en ningún lugar
- C) Que no se pueden perder logs
- D) Solo el tratamiento configurado de campos de log; el muestreo y la protección de datos requieren una revisión aparte

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Solo el tratamiento configurado de campos de log; el muestreo y la protección de datos requieren una revisión aparte**

**Explicación:** Inspeccione los datos realmente recopilados. El enmascaramiento de logs no protege automáticamente el muestreo de solicitudes ni la recopilación de Security Lake.

</details>
