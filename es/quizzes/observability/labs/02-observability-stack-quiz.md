# Cuestionario del Lab 02 de Observabilidad

<span id="observability-lab-part-2-observability-stack-quiz"></span>

> **Última actualización**: September 13, 2026

1. ¿Qué endpoint debe usar la recolección entre clústeres?
   - A) Solo el DNS del service del otro clúster.
   - B) Un endpoint privado con enrutamiento, DNS y TLS reales.
   - C) Deshabilitar siempre la verificación TLS.
   - D) Usar el archivo kubeconfig como URL.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Un endpoint privado con enrutamiento, DNS y TLS reales.**

El NLB reenvía TCP y el servidor valida los certificados de cliente.

</details>

---

2. ¿Cuál es el orden de análisis de logs de CRI?
   - A) Solo un parser JSON de Docker.
   - B) El parser de Container/CRI seguido del análisis JSON.
   - C) Tratar todo el prefijo como un campo JSON.
   - D) Convertir cada trace ID en una etiqueta de stream.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El parser de Container/CRI seguido del análisis JSON.**

Verifica la conservación de service/level/trace_id del cuerpo de la aplicación.

</details>

---

3. ¿Cómo se debe sondear Prometheus con mTLS?
   - A) Los sondeos HTTPS predeterminados sin certificados siempre tienen éxito.
   - B) Un sondeo exec de promtool usando configuración de certificado de cliente.
   - C) Eliminar todos los sondeos.
   - D) Devolver siempre readiness como true.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Un sondeo exec de promtool usando configuración de certificado de cliente.**

Se probó la fusión real del Operator y el comportamiento ready/healthy de TLS en Prometheus.

</details>

---

4. ¿Qué cambio de configuración de Tempo3 es importante?
   - A) Copiar solo los valores antiguos del ingester de Tempo2.
   - B) Usar live-store/backend scheduler/worker y los valores actuales del chart.
   - C) Copiar la configuración de Loki.
   - D) Las versiones del chart y de la aplicación siempre son idénticas.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Usar live-store/backend scheduler/worker y los valores actuales del chart.**

Comprueba el renderizado del chart por separado de la configuración/arranque real del binario.

</details>

---

5. ¿Qué significa la línea base de una sola instancia de Loki/Tempo?
   - A) La HA de producción es automática.
   - B) Una instancia de laboratorio duradera, no una garantía de HA/capacidad.
   - C) No hay costos de almacenamiento.
   - D) Las copias de seguridad están garantizadas automáticamente.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Una instancia de laboratorio duradera, no una garantía de HA/capacidad.**

Verifica la retención, los PVC, la limpieza y el impacto de los fallos.

</details>

---

6. ¿Qué JSON necesita la ruta de CloudWatch de AIOps?
   - A) Solo cadenas de consulta.
   - B) Logs estructurados que conserven service/level/trace_id.
   - C) Todas las contraseñas en texto plano.
   - D) Los traces crean logs automáticamente.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Logs estructurados que conserven service/level/trace_id.**

Se comprobó localmente el comportamiento de raw_log y los mensajes reales de PutLogEvents del exporter.

</details>

---

7. ¿Qué se requiere para la correlación en Grafana?
   - A) Solo habilitar una opción de la interfaz.
   - B) UID coincidentes, nombres de campo, datos reales y retención.
   - C) Solo hacer coincidir los nombres visibles.
   - D) Poner siempre trace_id en mayúsculas.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) UID coincidentes, nombres de campo, datos reales y retención.**

Alinea los UID de prometheus/loki/tempo y las expresiones escapadas de los derived fields.

</details>

---

8. ¿Cómo gestiona los exemplars el remote-write de Prometheus del servicio?
   - A) Se conservan siempre automáticamente.
   - B) Verificar sendExemplars, la recepción/almacenamiento y el enlace del datasource.
   - C) Una etiqueta crea automáticamente un trace.
   - D) Toda solicitud se almacena necesariamente.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Verificar sendExemplars, la recepción/almacenamiento y el enlace del datasource.**

Verifica que el trace representativo exista, no solo la opción de transporte.

</details>

---

9. ¿Cómo se deben tratar los permisos del DaemonSet de logs de nodo?
   - A) Habilitar siempre hostPID y todas las capabilities.
   - B) Permitir solo montajes de host de solo lectura y con alcance limitado, RBAC de lectura y la excepción explícita de root.
   - C) cluster-admin completo.
   - D) Las rutas de logs del host no tienen implicaciones de permisos.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Permitir solo montajes de host de solo lectura y con alcance limitado, RBAC de lectura y la excepción explícita de root.**

Valida conjuntamente la admisión del namespace y los permisos reales de los archivos.

</details>

---

10. ¿Cómo se deben describir los backends opcionales y las colas duraderas?
   - A) Todos los backends ya están desplegados.
   - B) Requieren validación por separado; la línea base no garantiza offsets/colas persistentes.
   - C) Es imposible que haya pérdidas o duplicados al reiniciar.
   - D) Una retención de 24 horas demuestra un SLO de 30 días.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Requieren validación por separado; la línea base no garantiza offsets/colas persistentes.**

Registra como exitosa solo la configuración y validación reales.

</details>

---

[Volver a la guía](../../../labs/observability/02-observability-stack-lab.md)
