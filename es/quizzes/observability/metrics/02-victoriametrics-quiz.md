# Cuestionario de VictoriaMetrics

Pon a prueba tus conocimientos sobre VictoriaMetrics.

---

1. ¿Cuál NO es una ventaja principal de VictoriaMetrics en comparación con Prometheus?
   - A) Compresión de datos hasta 7 veces más eficiente
   - B) Rendimiento hasta 20 veces más rápido en consultas complejas
   - C) Requiere aprender un lenguaje de consulta independiente
   - D) Capacidad de escalado horizontal

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Requiere aprender un lenguaje de consulta independiente**

**Explicación:**
VictoriaMetrics utiliza el lenguaje de consulta MetricsQL, que es un superconjunto de PromQL. Todas las consultas existentes de PromQL funcionan y solo proporciona funcionalidades de conveniencia adicionales. Por lo tanto, no es necesario aprender un lenguaje de consulta independiente.

</details>

---

2. ¿Cuál NO es un componente del modo de clúster de VictoriaMetrics?
   - A) vminsert
   - B) vmstorage
   - C) vmselect
   - D) vmoperator

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) vmoperator**

**Explicación:**
El modo de clúster de VictoriaMetrics consta de tres componentes principales: vminsert (enrutamiento de solicitudes de escritura), vmstorage (almacenamiento de datos), vmselect (procesamiento de consultas). vmoperator es un Operator de Kubernetes independiente, no un componente principal del modo de clúster.

</details>

---

3. ¿Cuál es la función principal de vmagent?
   - A) Almacenamiento de datos a largo plazo
   - B) Renderizado de dashboards
   - C) Recopilación de métricas y transmisión mediante Remote Write
   - D) Enrutamiento de alertas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Recopilación de métricas y transmisión mediante Remote Write**

**Explicación:**
vmagent es un agente ligero que recopila métricas y las envía a VictoriaMetrics u otro almacenamiento remoto. Es compatible con la configuración de scrape de Prometheus y proporciona funcionalidades como almacenamiento en búfer de datos, retransmisión y reetiquetado de labels.

</details>

---

4. ¿Cuál es el propósito de la función `keep_last_value()` en MetricsQL?
   - A) Conservar el valor máximo
   - B) Conservar el último valor (relleno de huecos)
   - C) Conservar el primer valor
   - D) Conservar el valor promedio

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Conservar el último valor (relleno de huecos)**

**Explicación:**
`keep_last_value()` es una función de extensión de MetricsQL que rellena los valores faltantes (huecos) en los datos de series temporales con el último valor conocido. Es útil para evitar huecos en dashboards y alertas cuando hay fallos de scrape o pérdida temporal de datos.

</details>

---

5. ¿Cuál es la función de la bandera `--dedup.minScrapeInterval` en VictoriaMetrics?
   - A) Establecer el intervalo mínimo de scrape
   - B) Eliminar muestras duplicadas dentro del intervalo especificado
   - C) Establecer el intervalo de compresión de datos
   - D) Establecer el intervalo de evaluación de alertas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Eliminar muestras duplicadas dentro del intervalo especificado**

**Explicación:**
`--dedup.minScrapeInterval` elimina muestras duplicadas de la misma serie temporal dentro del intervalo de tiempo especificado. Por ejemplo, `--dedup.minScrapeInterval=30s` combina en uno los puntos de datos duplicados dentro de 30 segundos. Es útil en configuraciones de HA donde varias instancias de Prometheus hacen scrape de los mismos targets.

</details>

---

6. ¿Cuál es el criterio correcto para elegir entre vmsingle y vmcluster?
   - A) Usar siempre vmcluster
   - B) Se recomienda vmsingle para menos de 100M de muestras/día sin requisitos de alta disponibilidad
   - C) vmsingle no admite funcionalidades de consulta
   - D) vmcluster solo funciona en un único nodo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Se recomienda vmsingle para menos de 100M de muestras/día sin requisitos de alta disponibilidad**

**Explicación:**
vmsingle (modo de nodo único) es sencillo de configurar y adecuado para entornos pequeños y medianos. Se recomienda vmsingle cuando las muestras diarias son inferiores a 100M y la alta disponibilidad no es esencial. Utiliza vmcluster para entornos a gran escala o cuando se requiera alta disponibilidad.

</details>

---

7. ¿Qué significa la configuración `replicationFactor=2` en el clúster de VictoriaMetrics?
   - A) Usar solo 2 nodos de almacenamiento
   - B) Replicar cada punto de datos en 2 nodos de almacenamiento
   - C) Ejecutar consultas solo en 2 nodos
   - D) Aplicar una compresión de 2 veces

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Replicar cada punto de datos en 2 nodos de almacenamiento**

**Explicación:**
`replicationFactor=2` configura vminsert para replicar cada punto de datos en 2 nodos vmstorage. Esto permite que el servicio continúe sin pérdida de datos incluso si falla un nodo de almacenamiento. Esta es una configuración recomendada para alta disponibilidad.

</details>

---

8. ¿Cuál es el propósito del operador `default` en MetricsQL?
   - A) Establecer labels predeterminados
   - B) Devolver un valor predeterminado cuando no hay resultado
   - C) Establecer la función de agregación predeterminada
   - D) Establecer el rango de tiempo predeterminado

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Devolver un valor predeterminado cuando no hay resultado**

**Explicación:**
El operador `default` en MetricsQL devuelve un valor predeterminado cuando el resultado de la consulta está vacío o es NaN. Por ejemplo, `rate(http_requests_total[5m]) / rate(http_requests_total[5m]) default 0` devuelve 0 en lugar de un error de división por cero. En PromQL, se necesitan condicionales complejos para este manejo.

</details>

---

9. ¿Cuál es la función correcta de vmalert?
   - A) Recopilación de métricas
   - B) Almacenamiento de datos
   - C) Evaluación de reglas de alerta y generación de alertas
   - D) Creación de dashboards

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Evaluación de reglas de alerta y generación de alertas**

**Explicación:**
vmalert evalúa las reglas de alerta y envía alertas a Alertmanager cuando se cumplen las condiciones, de forma similar a la funcionalidad de alertas de Prometheus. Puede utilizar VictoriaMetrics o Prometheus como fuentes de datos y también admite reglas de registro.

</details>

---

10. ¿Cuál es el propósito principal de vmbackup en VictoriaMetrics?
    - A) Replicación de datos en tiempo real
    - B) Crear backups en almacenamiento de objetos
    - C) Backup de logs
    - D) Backup de archivos de configuración

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Crear backups en almacenamiento de objetos**

**Explicación:**
vmbackup es una herramienta que realiza backups de datos de VictoriaMetrics en almacenamiento de objetos como S3, GCS y Azure Blob. Crea backups consistentes mediante la funcionalidad de snapshot y se puede restaurar con vmrestore. Es una herramienta esencial para la recuperación ante desastres y la protección de datos.

</details>

---
