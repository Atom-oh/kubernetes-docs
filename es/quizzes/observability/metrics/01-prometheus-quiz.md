# Cuestionario de Prometheus

> **Última actualización**: 12 de septiembre de 2026

1. ¿Cuál es la ruta normal de recopilación de métricas de Prometheus?

   - A) Las aplicaciones deben enviar cada muestra directamente
   - B) Prometheus consulta por HTTP los destinos configurados (scrape)
   - C) Solo un registro de eventos en streaming
   - D) Solo importaciones periódicas de CSV

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

La ruta normal es pull/scrape. Remote write y las integraciones opcionales por lotes agregan otras rutas de entrega. up indica si el scrape tuvo éxito, no si la aplicación está completamente disponible.

</details>

2. ¿Qué expresión proporciona la tasa promedio por segundo de un Counter durante cinco minutos?

   - A) `rate(http_requests_total, 5m)`
   - B) `rate(http_requests_total[5m])`
   - C) `increase(http_requests_total[5m])`
   - D) `avg(http_requests_total[5m])`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

rate() utiliza un vector de rango y gestiona los reinicios y la extrapolación observados. increase() estima el incremento total, no la tasa por segundo. Aplica rate antes de la agregación y no lo interpretes como la recuperación de cada incremento perdido.

</details>

3. ¿Qué debe describir un ServiceMonitor funcional?

   - A) Un panel de Grafana
   - B) Solo una imagen de contenedor de Prometheus
   - C) Los Services seleccionados y los endpoints de scrape, con selectores/nombres de puertos que coincidan con la configuración de Prometheus
   - D) Un Deployment completo de la aplicación

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

Prometheus primero selecciona el espacio de nombres y las etiquetas del monitor; el monitor selecciona los recursos Service de destino. El puerto del endpoint es el nombre del puerto del Service. RBAC, el acceso TLS/de red y una aplicación instrumentada son requisitos adicionales.

</details>

4. ¿Qué devuelve histogram_quantile() para los histogramas clásicos?

   - A) Un percentil exacto de Summary
   - B) Una estimación de cuantiles basada en buckets
   - C) Un percentil exacto independiente de la resolución de los buckets
   - D) La tasa de solicitudes de un Counter

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Agrega los buckets clásicos compatibles y conserva la etiqueta le. El resultado interpola dentro de los buckets. Los cuantiles de Summary también tienen un error que depende del algoritmo y la ventana, y no se pueden promediar para obtener un percentil de toda la flota.

</details>

5. ¿Qué componente no forma parte del paquete kube-prometheus-stack?

   - A) Prometheus Operator
   - B) Grafana
   - C) VictoriaMetrics
   - D) Alertmanager

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

El chart empaqueta Prometheus/Alertmanager, Operator, Grafana y exporters, según los valores habilitados. VictoriaMetrics es un despliegue independiente. Fija las versiones del chart que inspeccionaste en lugar de mezclar versiones arbitrarias de imágenes.

</details>

6. ¿Para qué se utiliza remote write?

   - A) Enviar notificaciones de Alertmanager
   - B) Entrega asíncrona de muestras a un receptor externo configurado
   - C) Garantizar un búfer ilimitado durante interrupciones
   - D) Sincronizar paneles de Grafana

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Los receptores incluyen AMP, VictoriaMetrics y Mimir. Cada uno tiene su propio endpoint, identidad, cuotas y contrato de HA. El almacenamiento en búfer de WAL es finito, y la retención de Prometheus local es configurable en lugar de estar limitada universalmente a 30 días.

</details>

7. ¿Qué controla la duración del parámetro for en una regla de alerta?

   - A) La retención de métricas
   - B) Cuánto tiempo permanece pendiente el mismo conjunto de condiciones y etiquetas de la alerta antes de activarse
   - C) El intervalo de repetición de Alertmanager
   - D) El número de réplicas de Prometheus

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

La condición debe permanecer satisfecha durante las evaluaciones para esa identidad de alerta. La falta de datos o los cambios de labels pueden interrumpir el estado pendiente. La agrupación y la temporización de las notificaciones son configuraciones independientes de Alertmanager.

</details>

8. ¿Cómo debe interpretarse predict_linear()?

   - A) Como una fecha límite garantizada de fallo de disco
   - B) Como una tendencia ajustada de Gauge extrapolada hacia el futuro
   - C) Una predicción estacional triple-exponencial
   - D) Un reemplazo para todas las mediciones de capacidad

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Proyecta la tendencia lineal observada. Los cambios de carga de trabajo, la limpieza, los datos dispersos y el comportamiento no lineal pueden invalidarla. El antiguo nombre holt_winters se reemplaza en Prometheus 3 por una función de suavizado doble exponencial explícitamente experimental; no es un modelo estacional.

</details>

9. ¿Qué hace groupBy de AlertmanagerConfig?

   - A) Autoriza automáticamente alertas de todos los espacios de nombres
   - B) Agrupa notificaciones por las etiquetas seleccionadas
   - C) Define la duración for de Prometheus
   - D) Hace que se ejecute cada ruta hermana coincidente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

groupBy se convierte en group_by en la configuración nativa. Las rutas normalmente se detienen en la primera coincidencia entre rutas hermanas, a menos que se configure continue. La inhibición necesita etiquetas de identidad de recurso significativas en el parámetro equal para evitar suprimir advertencias no relacionadas de Service o Node.

</details>

10. ¿Qué proporciona el WAL de TSDB?

   - A) Una caché de resultados de consultas
   - B) Registro secuencial que admite la recuperación ante fallos antes de la persistencia en bloques
   - C) Una copia de seguridad que sobrevive a la pérdida del volumen
   - D) Una cola ilimitada de entrega de remote write

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

La reproducción de WAL es un mecanismo de durabilidad, no una promesa de pérdida cero ante corrupción, fallo del volumen o interrupciones remotas prolongadas. Los requisitos de disco de retención y de WAL/head/compactación son independientes; conserva copias de seguridad y procedimientos de recuperación verificados.

</details>

[Volver a la guía](../../../observability/metrics/01-prometheus.md)
