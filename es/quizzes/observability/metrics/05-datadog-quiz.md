# Cuestionario de Datadog

> **Última actualización**: 13 de septiembre de 2026

1. ¿Qué sigue siendo responsabilidad del equipo con Datadog SaaS?

   - A) Nada después de instalar el agente
   - B) Solo elegir el color de un panel
   - C) Los recopiladores, la identidad, la instrumentación, el manejo de datos, los monitores y los costos
   - D) Los servidores físicos de bases de datos de Datadog

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

Datadog SaaS administra los sistemas del servicio. APM, la creación de perfiles, los registros y otros productos tienen habilitaciones y facturación independientes; instalar un agente no incluye todas estas funciones.

</details>

2. ¿Qué afirmación sobre las credenciales y la integración es correcta?

   - A) La ingesta básica del agente necesita una clave de API; las claves de aplicación y los roles de cuenta de AWS sirven para funciones adicionales específicas
   - B) Cada agente necesita una clave de aplicación y un rol amplio de lectura de AWS
   - C) Agregar IRSA configura automáticamente la integración de AWS de Datadog SaaS
   - D) Basta con adivinar el nombre de una cuenta de servicio

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

El proveedor de métricas externas necesita permisos de API y una clave adicional. La integración de AWS de SaaS usa un rol entre cuentas autorizado y un ID externo. Comprueba cuál es la cuenta de servicio real del agente que aparece en la configuración renderizada.

</details>

3. ¿Basta con definir admission.datadoghq.com/enabled=true para demostrar que se inyectará el SDK de APM?

   - A) Sí, incluidos automáticamente todos los lenguajes/versiones
   - B) No; configura las anotaciones del SDK o los destinos de SSI y luego verifica los Pods recién admitidos y los datos de trazas reales
   - C) Sí, incluso en el espacio de nombres del Cluster Agent
   - D) Sí, si existe un socket de trazas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

La configuración de la mutación y la conexión es distinta de la inyección de bibliotecas. La configuración de inyección actual excluye kube-system y el espacio de nombres del Cluster Agent. También hay que comprobar la compatibilidad de las bibliotecas, el entorno de ejecución, los puntos de montaje y la seguridad.

</details>

4. ¿Cómo debe conectarse un Pod de aplicación al agente DogStatsD del nodo?

   - A) Usar siempre localhost desde la aplicación
   - B) Incluir la clave de API en cada paquete UDP
   - C) Crear un ConfigMap no relacionado
   - D) Usar el punto de conexión accesible configurado, por ejemplo, un directorio UDS de Linux montado

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D**

El localhost de la aplicación no es el agente del nodo. Las rutas UDS, los permisos y el formato de los argumentos del SDK deben coincidir. Los datagramas no confirman que SaaS haya ingerido los datos; los contadores no garantizan un registro de entrega exactamente una vez.

</details>

5. ¿Qué interpretación de métricas es correcta?

   - A) kubernetes.cpu.usage.total es un porcentaje
   - B) Se eliminaron todas las métricas que faltaban del catálogo anterior
   - C) kubernetes.cpu.usage.total está en nanocores; las métricas de reinicio de Kubelet son gauges acumulativos
   - D) Sumar muestras de reinicios repetidas cuenta los reinicios nuevos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

system.cpu.idle es un porcentaje. Kubelet y State Core tienen nombres de métricas y etiquetas válidos distintos. El monitor de ejemplo evalúa explícitamente el total de reinicios; para validar los aumentos recientes hay que tener en cuenta los reinicios del contador.

</details>

6. ¿Qué calcula la consulta de proporción de errores con .as_count()?

   - A) La proporción entre el total de errores y el total de eventos, ambos agregados en el tiempo
   - B) La suma de las proporciones calculadas para cada intervalo
   - C) Un p95 global
   - D) Éxito automático del 100 % cuando no hay tráfico

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

Usa la agregación sum y grupos coincidentes. La función auxiliar emite explícitamente conteos de eventos correctos y de errores, incluso cuando son cero. La ausencia de tráfico, los datos faltantes y el tráfico sin errores son situaciones distintas.

</details>

7. ¿Qué afirmación sobre la configuración de OpenMetrics y registros es correcta?

   - A) Cualquier ConfigMap se monta automáticamente
   - B) Usa anotaciones de contenedor y campos de comprobación actuales que coincidan; las reglas Grok de registros usan match_rules/support_rules
   - C) prometheus.enabled en la raíz del chart configura todo
   - D) Las keys camelCase y snake_case de Grok son equivalentes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

La comprobación actual de OpenMetrics usa openmetrics_endpoint. datadog.confd proporciona el montaje que gestiona el chart; los ConfigMaps independientes no se instalan automáticamente. Validar el esquema de una solicitud no equivale a recopilar métricas en vivo ni a analizar registros con Grok.

</details>

8. ¿Qué debe conservar la correlación manual entre trazas y registros?

   - A) Solo dd.trace_id, eliminando todos los demás campos MDC
   - B) Una conversión numérica arbitraria de un identificador de 128 bits
   - C) Un identificador de traza válido codificado de forma fija
   - D) El contexto MDC previo de quien llama, identificadores de cadena y los requisitos reales de instrumentación y datos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D**

La función auxiliar restaura el contexto incluso si el código de la aplicación lanza una excepción. Se ejecuta de forma síncrona. La inyección y el análisis automáticos, las etiquetas de servicio coherentes y la disponibilidad de trazas son requisitos independientes.

</details>

9. ¿Por qué es incorrecto calcular el precio de 50 servicios como si fueran 50 hosts de APM?

   - A) APM siempre es gratis
   - B) La ingesta de registros constituye todo el costo de los registros
   - C) Los servicios y los hosts facturables son unidades diferentes; se deben contar las asignaciones y el uso del producto/contrato
   - D) Cada clúster tiene un host

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

La estimación anterior no se basaba en una factura real. También importan la indexación y la retención, las asignaciones de spans, las métricas personalizadas y otros productos. nonLocalTraffic indica conectividad; no es un límite de costos.

</details>

10. ¿Qué práctica relacionada con Watchdog, SLO y diagnóstico es correcta?

   - A) Una señal de Watchdog demuestra que se envió una notificación
   - B) Haz coincidir el modelo de SLO y la política de eventos correctos y totales, prueba el enrutamiento e inspecciona los paquetes de diagnóstico locales antes de compartirlos
   - C) Un paquete de diagnóstico local autoriza automáticamente su carga
   - D) Vuelca todos los valores de las variables de entorno DD_ cuando falten trazas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Datadog admite SLO de métricas, de monitores y de segmentos temporales. Hay que validar el comportamiento de las notificaciones y de la ausencia de datos. Los volcados del entorno pueden exponer claves; --local mantiene en el equipo local la recopilación inicial del paquete de diagnóstico.

</details>

---

[Volver a la guía](../../../observability/metrics/05-datadog.md)
