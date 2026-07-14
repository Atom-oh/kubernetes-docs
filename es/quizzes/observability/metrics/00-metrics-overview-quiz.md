# Cuestionario de introducción a las métricas

Pon a prueba tu comprensión de los conceptos básicos de métricas y las soluciones de monitorización.

---

1. Entre los cuatro tipos básicos de métricas de Prometheus, ¿qué tipo solo puede aumentar de valor y se restablece a 0 al reiniciarse?
   - A) Gauge
   - B) Counter
   - C) Histogram
   - D) Summary

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Counter**

**Explicación:**
Counter es un tipo de métrica que realiza un seguimiento de valores acumulativos; estos valores solo pueden aumentar y se restablecen a 0 al reiniciarse. Se utiliza para realizar un seguimiento de los recuentos de solicitudes HTTP, recuentos de errores, recuentos de tareas completadas, etc. Gauge puede aumentar y disminuir, mientras que Histogram y Summary miden distribuciones.

</details>

---

2. ¿Qué afirmación describe correctamente la cardinalidad?
   - A) Se refiere al intervalo de recopilación de métricas
   - B) Se refiere al número de combinaciones únicas de series temporales
   - C) Se refiere a la tasa de compresión de los datos de métricas
   - D) Se refiere al período de retención de las métricas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Se refiere al número de combinaciones únicas de series temporales**

**Explicación:**
La cardinalidad se refiere al número de combinaciones únicas de etiquetas en las métricas. Una cardinalidad alta afecta directamente al uso de almacenamiento y al rendimiento de las consultas. Usar como etiquetas valores que pueden crecer infinitamente, como user_id o request_id, provoca que la cardinalidad se dispare.

</details>

---

3. ¿Qué afirmación sobre los modelos Pull y Push NO es correcta?
   - A) Prometheus es un sistema basado en Pull
   - B) En el modelo Pull, los objetivos y los intervalos de recopilación se controlan de forma centralizada
   - C) El modelo Push es adecuado para recopilar métricas de trabajos de corta duración
   - D) El modelo Pull accede fácilmente a objetivos detrás de NAT/firewalls

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) El modelo Pull accede fácilmente a objetivos detrás de NAT/firewalls**

**Explicación:**
En el modelo Pull, el servidor de monitorización envía solicitudes HTTP directamente a los objetivos para recopilar métricas, lo que dificulta el acceso a objetivos detrás de NAT/firewalls. En cambio, el modelo Push permite que los objetivos envíen métricas directamente, lo que resulta ventajoso en entornos con NAT/firewalls. Mediante Pushgateway, el modelo Pull también puede recopilar métricas de trabajos de corta duración.

</details>

---

4. ¿Qué afirmación describe correctamente la diferencia entre Histogram y Summary?
   - A) Histogram calcula cuantiles en el cliente
   - B) Summary permite la agregación entre varias instancias
   - C) Histogram calcula cuantiles en el servidor (en el momento de la consulta)
   - D) Summary tiene una mayor eficiencia de almacenamiento que Histogram

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Histogram calcula cuantiles en el servidor (en el momento de la consulta)**

**Explicación:**
Histogram almacena datos en buckets y calcula cuantiles en el servidor en el momento de la consulta. Summary calcula y almacena cuantiles en el cliente. Histogram permite la agregación entre varias instancias, pero Summary no. Histogram se recomienda para la medición de SLO/SLI y los sistemas distribuidos.

</details>

---

5. ¿Cuál NO es una convención recomendada para nombrar métricas?
   - A) Usar snake_case
   - B) Incluir unidades como sufijo (_seconds, _bytes)
   - C) Usar camelCase
   - D) Usar un prefijo de aplicación/dominio

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Usar camelCase**

**Explicación:**
Las convenciones de nomenclatura de métricas de estilo Prometheus usan snake_case en lugar de camelCase. Los buenos nombres de métricas como `http_requests_total`, `http_request_duration_seconds` usan minúsculas y guiones bajos, incluyen las unidades como sufijo y usan prefijos de aplicación/dominio.

</details>

---

6. ¿Cuál NO es una razón apropiada por la que Prometheus requiere una solución independiente para el almacenamiento a largo plazo?
   - A) Una baja tasa de compresión aumenta el uso de disco
   - B) La arquitectura de un solo nodo limita la escalabilidad
   - C) PromQL no admite consultas complejas
   - D) No se admite clustering HA nativo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) PromQL no admite consultas complejas**

**Explicación:**
PromQL es un lenguaje de consulta muy potente que admite consultas complejas. Las razones por las que Prometheus no es adecuado para el almacenamiento a largo plazo incluyen una tasa de compresión relativamente baja, límites de escalabilidad de la arquitectura de un solo nodo, falta de clustering HA nativo y velocidad de consulta lenta para datos a largo plazo.

</details>

---

7. ¿Qué comparación de soluciones NO es correcta?
   - A) VictoriaMetrics proporciona una mayor tasa de compresión que Prometheus
   - B) CloudWatch es un servicio totalmente administrado
   - C) Mimir solo admite disco local
   - D) Datadog se ofrece como modelo SaaS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Mimir solo admite disco local**

**Explicación:**
Grafana Mimir es un almacén de métricas distribuido que requiere almacenamiento de objetos (S3, GCS, Azure Blob, etc.). Utiliza almacenamiento de objetos en la nube en lugar de disco local para proporcionar escalabilidad ilimitada y retención a largo plazo. VictoriaMetrics admite tanto disco local como almacenamiento de objetos.

</details>

---

8. ¿Cuál NO es un método apropiado para prevenir problemas de cardinalidad alta?
   - A) No usar el ID de usuario como etiqueta de métrica
   - B) No usar el ID de solicitud como etiqueta de métrica
   - C) Agrupar códigos de estado HTTP (200 → 2xx)
   - D) Mantener únicos todos los valores de las etiquetas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Mantener únicos todos los valores de las etiquetas**

**Explicación:**
Para prevenir una cardinalidad alta, los valores de las etiquetas no deben crecer infinitamente. Los valores que pueden crecer infinitamente, como el ID de usuario, el ID de solicitud y el ID de sesión, no deben utilizarse como etiquetas. Es mejor agrupar los códigos de estado HTTP (200 → 2xx) y normalizar las rutas URL (/users/123 → /users/{id}).

</details>

---

9. ¿Cuál relaciona correctamente las principales fuentes y funciones de métricas en entornos Kubernetes?
   - A) node-exporter - métricas de estado de objetos Kubernetes
   - B) kube-state-metrics - métricas de hardware a nivel de Node
   - C) cAdvisor - métricas de recursos a nivel de Container
   - D) metrics-server - almacenamiento de métricas a largo plazo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) cAdvisor - métricas de recursos a nivel de Container**

**Explicación:**
cAdvisor (Container Advisor) recopila métricas de recursos como CPU, memoria e I/O por Container. node-exporter proporciona métricas de hardware/OS a nivel de Node, kube-state-metrics proporciona métricas de estado de objetos de la API de Kubernetes (Pod, Deployment, Node, etc.), y metrics-server proporciona métricas de recursos en tiempo real para HPA/VPA.

</details>

---

10. ¿Cuál NO es una consideración apropiada al seleccionar una solución de métricas?
    - A) Capacidades operativas y tamaño del equipo
    - B) Requisitos de multi-cloud
    - C) Estructura de costes y presupuesto
    - D) Longitud de los nombres de las métricas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Longitud de los nombres de las métricas**

**Explicación:**
Al seleccionar una solución de métricas, debes considerar las capacidades operativas del equipo, los requisitos de multi-cloud, la estructura de costes, los requisitos de escalabilidad y la integración con los ecosistemas existentes. La longitud de los nombres de las métricas no afecta a la selección de la solución. En su lugar, la cardinalidad, el período de retención de datos y el rendimiento de las consultas son consideraciones importantes.

</details>

---
