# Cuestionario de AWS X-Ray

Pon a prueba tus conocimientos sobre AWS X-Ray.

---

1. ¿Cuál NO es una característica principal de AWS X-Ray?
   - A) Visualización del mapa de servicios
   - B) Trazado distribuido
   - C) Agregación de logs
   - D) Análisis de rendimiento

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Agregación de logs**

**Explicación:**
AWS X-Ray proporciona trazado distribuido, visualización del mapa de servicios y análisis de rendimiento. La agregación de logs es una característica de CloudWatch Logs. X-Ray puede integrarse con CloudWatch Logs para vincular traces y logs, pero no recopila ni almacena logs por sí mismo.

</details>

---

2. ¿Cuál es la forma recomendada de desplegar el daemon de X-Ray en EKS?
   - A) Deployment
   - B) StatefulSet
   - C) DaemonSet
   - D) Job

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) DaemonSet**

**Explicación:**
Se recomienda desplegar el X-Ray Daemon como un DaemonSet. Un DaemonSet ejecuta un Pod en cada nodo, lo que permite que todos los Pods de aplicación de ese nodo envíen datos de trace al X-Ray Daemon local. Esto minimiza la latencia de red y garantiza una transmisión de datos fiable.

</details>

---

3. ¿Cuál NO es un parámetro utilizado al configurar reglas de sampling centralizadas en X-Ray?
   - A) FixedRate
   - B) ReservoirSize
   - C) Priority
   - D) RetentionDays

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) RetentionDays**

**Explicación:**
Las reglas de sampling de X-Ray incluyen FixedRate (proporción fija de sampling), ReservoirSize (muestras mínimas por segundo) y Priority (prioridad de la regla). RetentionDays no es un parámetro de regla de sampling, sino que está relacionado con la configuración de retención de datos de X-Ray. El período de retención de datos predeterminado es de 30 días.

</details>

---

4. ¿Cuál es la diferencia entre Annotation y Metadata en X-Ray?
   - A) El máximo de Annotation es 100, Metadata es ilimitada
   - B) Annotation está indexada y se puede filtrar, Metadata no está indexada
   - C) Annotation solo admite cadenas, Metadata admite todos los tipos
   - D) Annotation se genera automáticamente, Metadata se agrega manualmente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Annotation está indexada y se puede filtrar, Metadata no está indexada**

**Explicación:**
Las Annotations están indexadas y se pueden buscar mediante expresiones de filtro en la consola de X-Ray (máximo 50). Metadata no está indexada y no se puede buscar, pero se utiliza para almacenar información detallada. Usa Annotations para identificadores importantes (user_id, order_id, etc.) y Metadata para información detallada, como los cuerpos de solicitud/respuesta.

</details>

---

5. ¿Cuál NO es una ventaja de utilizar el Collector de ADOT (AWS Distro for OpenTelemetry)?
   - A) Utiliza estándares neutrales para proveedores
   - B) Compatibilidad con múltiples backends
   - C) Optimización específica de X-Ray
   - D) Compatibilidad con el protocolo OpenTelemetry

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Optimización específica de X-Ray**

**Explicación:**
El ADOT Collector es neutral para proveedores y se basa en OpenTelemetry; puede enviar datos a diversos backends (Prometheus, Jaeger, Datadog, etc.) además de X-Ray. La optimización específica de X-Ray es una característica del X-Ray Daemon. Las ventajas de ADOT son la instrumentación estandarizada y la compatibilidad con múltiples backends.

</details>

---

6. ¿Cuándo aparece un nodo en rojo en el mapa de servicios de X-Ray?
   - A) Cuando el tiempo de respuesta es lento
   - B) Cuando el tráfico es alto
   - C) Cuando la tasa de errores es alta
   - D) Cuando es un servicio recién agregado

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Cuando la tasa de errores es alta**

**Explicación:**
Los colores de los nodos en el mapa de servicios de X-Ray indican el estado de salud del servicio. El rojo indica servicios con tasas de error elevadas, el amarillo indica servicios con problemas de nivel de advertencia y el verde indica servicios normales. Esto permite identificar rápidamente los servicios problemáticos.

</details>

---

7. ¿Qué configuración se necesita para recibir datos de trace de OpenTelemetry en X-Ray?
   - A) Instalar X-Ray SDK
   - B) Configurar AWS X-Ray Propagator e ID Generator
   - C) Instalar CloudWatch Agent
   - D) Agregar Lambda Layer

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Configurar AWS X-Ray Propagator e ID Generator**

**Explicación:**
Para enviar datos de trace desde OpenTelemetry a X-Ray, debes configurar AWS X-Ray Propagator (propagación de contexto) y AWS X-Ray ID Generator (genera TraceIDs en formato X-Ray). Esto permite generar datos de trace compatibles con X-Ray mientras se utilizan los estándares de OpenTelemetry.

</details>

---

8. ¿Cuál es la consulta de expresión de filtro de X-Ray correcta para encontrar solicitudes con un tiempo de respuesta superior a 2 segundos?
   - A) `duration > 2`
   - B) `responsetime > 2`
   - C) `latency >= 2000`
   - D) `time > 2s`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) responsetime > 2**

**Explicación:**
En las expresiones de filtro de X-Ray, la palabra clave `responsetime` se utiliza para el tiempo de respuesta y la unidad es segundos. `responsetime > 2` filtra las solicitudes que tardaron más de 2 segundos. Otros filtros útiles incluyen `fault = true` (errores del servidor), `error = true` (errores del cliente) y `service("name")` (servicio específico).

</details>

---

9. ¿Cuál NO es una característica proporcionada al integrar X-Ray con CloudWatch ServiceLens?
   - A) Vista integrada de traces y métricas
   - B) Mostrar alarmas de CloudWatch en el mapa de servicios
   - C) Instrumentación automática del código
   - D) Vincular logs y traces

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Instrumentación automática del código**

**Explicación:**
CloudWatch ServiceLens proporciona una vista integrada de traces de X-Ray, métricas de CloudWatch y logs. Muestra las alarmas de CloudWatch en el mapa de servicios y ofrece características para vincular logs y traces. Sin embargo, la instrumentación automática del código debe realizarse mediante X-Ray SDK o la instrumentación automática de OpenTelemetry.

</details>

---

10. ¿Cuál es el propósito principal de los X-Ray Groups?
    - A) Gestión de permisos de usuarios
    - B) Agrupación y alertas de traces basadas en filtros
    - C) Asignación de costos de recursos
    - D) Configuración de políticas de retención de datos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Agrupación y alertas de traces basadas en filtros**

**Explicación:**
Los X-Ray Groups utilizan expresiones de filtro para agrupar traces. Por ejemplo, puedes crear grupos para entornos de producción, servicios específicos, solicitudes con errores, etc. Para cada grupo, puedes configurar alarmas de CloudWatch para recibir alertas sobre condiciones específicas (como el aumento de las tasas de error).

</details>

---
