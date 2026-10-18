# Cuestionario de VictoriaMetrics

> Referencia de revisión: VictoriaMetrics 1.151.0 · chart de stack 0.92.1

1. ¿Qué afirmación es correcta al migrar consultas de Prometheus a VictoriaMetrics?
   - A) Todas las cargas de trabajo logran exactamente una compresión 7 veces mejor
   - B) Todas las instalaciones tienen un límite fijo de 100 millones de series
   - C) Hay que comparar las consultas reales porque MetricsQL difiere intencionalmente de PromQL
   - D) Prometheus no puede conservar datos durante más de 15 días

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

Que la sintaxis resulte familiar no significa que el comportamiento de `rate`/`increase`, `NaN`, escalares o la API sea idéntico. Las pruebas de rendimiento deben usar las versiones, los datos y el hardware reales; los valores de retención predeterminados no son límites máximos.

</details>

---

2. ¿Cuál de estos elementos no es un componente del plano de datos de almacenamiento y consulta del clúster?
   - A) vminsert
   - B) vmstorage
   - C) vmselect
   - D) VictoriaMetrics Operator

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D**

vminsert enruta las escrituras, vmstorage almacena los datos y vmselect los consulta. El Operator reconcilia recursos de Kubernetes y es un componente de control independiente.

</details>

---

3. ¿Qué función cumple vmagent?
   - A) Sustituye todo el almacenamiento persistente
   - B) Renderiza dashboards
   - C) Recopila métricas y las reenvía a destinos de escritura remota
   - D) Sustituye el enrutamiento de notificaciones de Alertmanager

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

Su cola almacena datos temporalmente durante las interrupciones, pero tiene capacidad finita: al alcanzar el límite de disco configurado, descarta los datos en cola más antiguos, y un `emptyDir` se pierde cuando se reemplaza el Pod. La persistencia y la supervisión de la cola son decisiones de diseño independientes.

</details>

---

4. ¿Qué hace `keep_last_value(q)` y qué precaución requiere?
   - A) Devuelve el valor almacenado máximo
   - B) Rellena los huecos evaluados con un valor anterior, lo que puede ocultar la falta de telemetría
   - C) Restaura todas las muestras perdidas durante el scrape
   - D) Garantiza que las alertas de disponibilidad indiquen un estado correcto

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Rellena los huecos solo cuando ese comportamiento tenga el significado deseado. Mantener un valor antiguo que indicaba un estado saludable puede ocultar que se ha interrumpido la recopilación; supervisa por separado la ausencia de datos.

</details>

---

5. ¿Qué controla `dedup.minScrapeInterval`?
   - A) El intervalo de programación del scraper de destinos
   - B) La conservación de una muestra por intervalo discreto para una misma serie
   - C) Una compresión genérica sin pérdida
   - D) La frecuencia de evaluación de las alertas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

El intervalo puede eliminar muestras legítimas de mayor resolución, no solo copias idénticas en bytes. Alinea la configuración de vmstorage y vmselect con el diseño elegido para el almacenamiento y la replicación de los scrapers.

</details>

---

6. ¿Cómo se deben elegir los modos de nodo único y de clúster?
   - A) Elegir siempre el modo de clúster
   - B) Medir la carga, las series activas y su rotación, las consultas, la retención y los requisitos de recuperación
   - C) Usar 100 millones de muestras al día como umbral universal
   - D) El modo de nodo único no ofrece una API de consulta

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Evalúa la capacidad de un solo servidor y el costo de escalar insert, storage y select por separado. El almacenamiento replicado o dos procesos por sí solos no proporcionan alta disponibilidad comprobada del servicio.

</details>

---

7. ¿Qué solicita `replicationFactor=2` en vminsert?
   - A) Exactamente dos miembros de almacenamiento en total
   - B) Dos copias en miembros de almacenamiento distintos, sujeto a la disponibilidad y al historial reales
   - C) Consultas en exactamente dos miembros
   - D) El doble de compresión

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Para mantener dos copias durante la falla de un nodo de almacenamiento se necesitan al menos tres miembros, además de la capacidad y las condiciones de dominios de falla correspondientes. Configura vmselect y la deduplicación de forma coherente; esta opción no completa el historial con réplicas, no garantiza escrituras sin pérdida en condiciones degradadas ni sustituye las copias de seguridad.

</details>

---

8. ¿Cuál es el alcance del operador `default` de MetricsQL?
   - A) Siempre crea las etiquetas de servicio correctas
   - B) Rellena los puntos que faltan con la expresión de la derecha; la falta de datos no equivale automáticamente a tráfico cero
   - C) Garantiza que todas las razones sean significativas
   - D) Cambia el intervalo de ingesta de las métricas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

No añadas `default 0` como solución universal para los errores. Agrega de forma coherente las etiquetas de estado, rellena un numerador ausente solo para series con un denominador conocido y excluye el tráfico cero. El conjunto de prueba nativo da 0, 1 y 0,1 para el tráfico saludable, todo fallido y con un 10 % de fallos; los servicios sin datos o con tráfico cero siguen sin aparecer.

</details>

---

9. ¿De qué se encarga vmalert?
   - A) Recopilar todas las métricas de las aplicaciones
   - B) Almacenar todas las muestras a largo plazo
   - C) Evaluar reglas de alertas y de registro, y enviar alertas a un notificador configurado
   - D) Renderizar dashboards de Grafana

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

Deben existir las entradas de las reglas y los exportadores, las URL de las fuentes de datos, la persistencia del estado y la configuración del notificador y del enrutamiento. Un número elevado de reinicios no demuestra por sí solo que haya un `CrashLoopBackOff`. Registrar series derivadas no compacta ni elimina los datos sin procesar.

</details>

---

10. ¿Cuál es el flujo de trabajo correcto para vmbackup?
   - A) Hacer una copia de seguridad solo de la configuración de vminsert
   - B) Leer una instantánea del directorio de almacenamiento correspondiente y proteger un destino de copias de seguridad independiente
   - C) Montar cualquier PVC de acceso `RWO` en cualquier nodo sin comprobarlo
   - D) Considerar que la replicación del almacenamiento es una copia de seguridad completa

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Haz una copia de seguridad de cada miembro de vmstorage en un prefijo independiente o del almacenamiento previsto para un nodo único. Se admiten destinos S3, GCS, Azure y locales. Verifica la ubicación conjunta de los recursos, la identidad del PVC, las credenciales de la carga de trabajo, la retención y una restauración real; una instantánea local no es una copia independiente.

</details>

---

[Volver al material de aprendizaje](../../../observability/metrics/02-victoriametrics.md)
