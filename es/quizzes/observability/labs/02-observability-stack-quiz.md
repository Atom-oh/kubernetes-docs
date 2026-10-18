# Cuestionario del Lab 02 de Observabilidad

<span id="observability-lab-part-2-observability-stack-quiz"></span>

> **Última actualización**: 13 de septiembre de 2026

1. ¿Qué endpoint debe usar la recolección entre clústeres?
   - A) Solo el DNS del Service del otro clúster.
   - B) Un endpoint privado con enrutamiento, DNS y TLS reales.
   - C) Deshabilitar siempre la verificación TLS.
   - D) Usar el archivo kubeconfig como URL.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Un endpoint privado con enrutamiento, DNS y TLS reales.**

El NLB reenvía TCP y el servidor valida los certificados de cliente.

</details>

---

2. ¿Cuál es el orden de análisis de los registros de CRI?
   - A) Solo un analizador JSON de Docker.
   - B) El analizador de contenedor/CRI seguido del análisis de JSON.
   - C) Tratar todo el prefijo como un campo JSON.
   - D) Convertir cada trace ID en una etiqueta de stream.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El parser de Container/CRI seguido del análisis JSON.**

Verifica que se conserven los campos `service`, `level` y `trace_id` del cuerpo de la aplicación.

</details>

---

3. ¿Cómo se debe sondear Prometheus con mTLS?
   - A) Los sondeos HTTPS predeterminados sin certificados siempre tienen éxito.
   - B) Un sondeo de tipo exec de promtool con la configuración del certificado de cliente.
   - C) Eliminar todos los sondeos.
   - D) Devolver siempre readiness como true.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Un sondeo exec de promtool usando configuración de certificado de cliente.**

Se probaron la fusión real del Operator y el comportamiento de los endpoints ready/healthy de Prometheus con TLS.

</details>

---

4. ¿Qué cambio de configuración de Tempo 3 es importante?
   - A) Copiar solo los valores antiguos del ingester de Tempo2.
   - B) Usar el backend live-store con sus componentes scheduler y worker, además de los valores actuales del chart.
   - C) Copiar la configuración de Loki.
   - D) Las versiones del chart y de la aplicación siempre son idénticas.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Usar el backend live-store con sus componentes scheduler y worker, además de los valores actuales del chart.**

Comprueba por separado el renderizado del chart y la configuración y el arranque reales del binario.

</details>

---

5. ¿Qué significa la línea base de una sola instancia de Loki/Tempo?
   - A) La HA de producción es automática.
   - B) Una instancia persistente para el laboratorio, no una garantía de alta disponibilidad ni de capacidad.
   - C) No hay costos de almacenamiento.
   - D) Las copias de seguridad están garantizadas automáticamente.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Una instancia persistente para el laboratorio, no una garantía de alta disponibilidad ni de capacidad.**

Verifica la retención, los PVC, la limpieza y el impacto de los fallos.

</details>

---

6. ¿Qué JSON necesita la integración de AIOps con CloudWatch?
   - A) Solo cadenas de consulta.
   - B) Registros estructurados que conserven los campos service/level/trace_id.
   - C) Todas las contraseñas en texto plano.
   - D) Los traces crean logs automáticamente.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Registros estructurados que conserven los campos service/level/trace_id.**

Se comprobó localmente el comportamiento de `raw_log` y los mensajes reales de `PutLogEvents` del exportador.

</details>

---

7. ¿Qué se requiere para la correlación en Grafana?
   - A) Solo habilitar una opción de la interfaz.
   - B) UID coincidentes, nombres de los campos, datos reales y retención.
   - C) Solo hacer coincidir los nombres visibles.
   - D) Poner siempre trace_id en mayúsculas.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) UID coincidentes, nombres de campo, datos reales y retención.**

Alinea los UID de Prometheus/Loki/Tempo y las expresiones escapadas de los campos derivados.

</details>

---

8. ¿Qué hay que comprobar para conservar exemplars en el envío remoto de Prometheus?
   - A) Se conservan siempre automáticamente.
   - B) Verifica `sendExemplars`, la recepción y el almacenamiento, y el vínculo con la fuente de datos.
   - C) Una etiqueta crea automáticamente un trace.
   - D) Toda solicitud se almacena necesariamente.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Verifica `sendExemplars`, la recepción y el almacenamiento, y el vínculo con la fuente de datos.**

Verifica que exista la traza representativa, no solo que esté habilitada la opción de transporte.

</details>

---

9. ¿Cómo se deben tratar los permisos del DaemonSet de logs de nodo?
   - A) Habilitar siempre `hostPID` y todas las capacidades.
   - B) Permitir solo montajes del host de solo lectura y limitados a lo necesario, RBAC de solo lectura y la excepción explícita para root.
   - C) cluster-admin completo.
   - D) Las rutas de logs del host no tienen implicaciones de permisos.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Permitir solo montajes del host de solo lectura y limitados a lo necesario, RBAC de solo lectura y la excepción explícita para root.**

Valida conjuntamente la admisión del espacio de nombres y los permisos reales de los archivos.

</details>

---

10. ¿Cómo se deben describir los backends opcionales y las colas duraderas?
   - A) Todos los backends ya están desplegados.
   - B) Requieren validación por separado; la configuración base no garantiza la persistencia de offsets ni de colas.
   - C) Es imposible que haya pérdidas o duplicados al reiniciar.
   - D) Una retención de 24 horas demuestra un SLO de 30 días.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Requieren validación por separado; la configuración base no garantiza la persistencia de offsets ni de colas.**

Registra como exitosa únicamente la configuración y validación reales.

</details>

---

[Volver a la guía](../../../labs/observability/02-observability-stack-lab.md)
