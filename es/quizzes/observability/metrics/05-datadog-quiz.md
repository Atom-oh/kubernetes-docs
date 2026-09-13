# Cuestionario de Datadog

> **Última actualización**: September 13, 2026

1. ¿Qué sigue siendo responsabilidad del equipo con Datadog SaaS?

   - A) Nada después de instalar el Agent
   - B) Solo seleccionar un color de dashboard
   - C) Collectors, identidad, instrumentación, manejo de datos, monitors y costo
   - D) Los servidores físicos de bases de datos de Datadog

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

SaaS administra el backend. APM, profiling, logs y otros productos tienen derechos y facturación distintos; un Agent no incluye todo.

</details>

2. ¿Qué afirmación sobre credenciales/integración es correcta?

   - A) La ingestión básica del Agent necesita una API key; las application keys y los roles de cuenta de AWS sirven para funcionalidades adicionales y específicas
   - B) Cada Agent necesita una application key y un rol amplio de lectura de AWS
   - C) Agregar IRSA configura automáticamente la integración de AWS de Datadog SaaS
   - D) Un nombre de service account adivinado es suficiente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

El proveedor de métricas externas necesita permisos de API/configuración de key adicionales. La integración de AWS de SaaS usa un rol autorizado entre cuentas/external ID. Resuelva el Agent SA representado real.

</details>

3. ¿admission.datadoghq.com/enabled=true por sí solo prueba la inyección del SDK de APM?

   - A) Sí, incluidos automáticamente todos los lenguajes/versiones
   - B) No; configure las anotaciones del SDK o los destinos de SSI y, después, verifique los Pods recién admitidos y los datos de traces reales
   - C) Sí, incluso en el namespace de Cluster Agent
   - D) Sí, si existe un trace socket

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

La configuración de mutación/conexión y la inyección de bibliotecas son distintas. La inyección local actual excluye kube-system y el namespace de Cluster Agent. La compatibilidad de bibliotecas, runtime, mount y seguridad sigue siendo importante.

</details>

4. ¿Cómo debe un Pod de aplicación alcanzar el Agent DogStatsD del nodo?

   - A) Usar siempre el localhost de la aplicación
   - B) Poner la API key en cada paquete UDP
   - C) Crear un ConfigMap no relacionado
   - D) Usar el endpoint accesible configurado, como un directorio Linux UDS montado

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D**

El localhost de la aplicación no es un Agent de nodo. Las rutas UDS, los permisos y los formatos de argumentos del SDK deben coincidir. Los datagramas no confirman la ingestión de SaaS; los contadores no son un registro exactamente una vez.

</details>

5. ¿Qué interpretación de métricas es correcta?

   - A) kubernetes.cpu.usage.total es un porcentaje
   - B) Todas las métricas faltantes del catálogo heredado fueron eliminadas
   - C) kubernetes.cpu.usage.total está en nanocores; las métricas de reinicio de Kubelet son gauges acumulativos
   - D) Sumar muestras de reinicios repetidas cuenta los reinicios nuevos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

system.cpu.idle es un porcentaje. Kubelet y State Core tienen nombres de métricas y tags válidos distintos. El monitor de reinicios de ejemplo evalúa explícitamente un total; los aumentos recientes necesitan validación que considere los reinicios del contador.

</details>

6. ¿Qué calcula la ruta de proporción de errores .as_count()?

   - A) La proporción de conteos de errores y totales agregados en el tiempo
   - B) Una suma de cada proporción de intervalo de tiempo
   - C) Un p95 global
   - D) Éxito automático del 100 % cuando no hay tráfico

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

Use agregación sum y grupos coincidentes. El helper emite explícitamente conteos de buenos/errores en cero. Sin tráfico, datos faltantes y tráfico sin errores siguen siendo estados diferentes.

</details>

7. ¿Qué afirmación sobre la configuración de OpenMetrics/log es correcta?

   - A) Cualquier ConfigMap se monta automáticamente
   - B) Use anotaciones de contenedor/campos de check actuales coincidentes; las reglas de Grok de Logs usan match_rules/support_rules
   - C) prometheus.enabled en la raíz del chart configura todo
   - D) Las keys camelCase y snake_case de Grok son equivalentes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

El check actual de OpenMetrics usa openmetrics_endpoint. datadog.confd proporciona el montaje administrado por el chart; los ConfigMaps independientes no se instalan por sí mismos. La validación del esquema de solicitud no es un scrape en vivo ni un parse de Grok.

</details>

8. ¿Qué debe preservar la correlación manual de trace-log?

   - A) Solo dd.trace_id, eliminando todos los demás campos MDC
   - B) Una conversión numérica arbitraria de un ID de 128 bits
   - C) Un trace ID exitoso codificado de forma rígida
   - D) El contexto MDC previo del llamador, IDs de cadena y los requisitos de instrumentación/datos reales

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D**

El helper restaura el contexto incluso cuando el código de la aplicación genera un error. Es síncrono. La inyección/parse automáticos, los tags de servicio coherentes y los traces disponibles son requisitos independientes.

</details>

9. ¿Qué tiene de incorrecto calcular el precio de 50 servicios como 50 hosts de APM?

   - A) APM siempre es gratis
   - B) La ingestión de logs constituye toda la factura de logs
   - C) Los servicios y los hosts facturables son unidades diferentes; se deben contar las asignaciones y el uso del producto/contrato
   - D) Cada clúster tiene un host

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

La estimación anterior no era una factura medida. La indexación/retención, las asignaciones de spans, las custom metrics y otros productos importan. nonLocalTraffic es conectividad, no una cuota de costos.

</details>

10. ¿Qué práctica de Watchdog/SLO/diagnóstico es correcta?

   - A) Un insight de Watchdog prueba que se entregó una página
   - B) Haga coincidir el modelo SLO y la política de buenos/totales, pruebe el enrutamiento e inspeccione los bundles de diagnóstico locales antes de compartirlos
   - C) Un flare local autoriza automáticamente la carga
   - D) Vuelque todos los valores de entorno DD_ cuando falten traces

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Datadog admite SLOs de métricas, monitor y time-slice. El comportamiento de notificación y sin datos necesita validación. Los volcados de env pueden exponer keys; --local mantiene local la recopilación inicial del flare.

</details>

---

[Volver a la guía](../../../observability/metrics/05-datadog.md)
