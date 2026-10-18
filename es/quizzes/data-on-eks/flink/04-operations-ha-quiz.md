# Cuestionario sobre operaciones, alta disponibilidad y Flink administrado

Compruebe las rutas de recopilación, los límites de memoria y recuperación, y el soporte de servicios administrados.

1. ¿Qué recurso utiliza la elección de líder de HA de Kubernetes revisada?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** ConfigMapLock de Fabric8, que depende de la disponibilidad del plano de control de Kubernetes.

**Explicación:** No añade un servidor de elección de líder independiente ni necesariamente usa recursos Lease. ZooKeeper HA también es una alternativa compatible.

</details>

2. ¿Los HA ConfigMaps, HA storageDir y los directorios de checkpoints almacenan los mismos datos?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** Los ConfigMaps contienen información/referencias de líder, HA storageDir contiene metadatos de recuperación del JM/grafos de trabajos y los directorios de checkpoints conservan el estado de los checkpoints.

**Explicación:** Una sola configuración de ruta de HA no prepara todos los archivos de estado ni los permisos de recuperación.

</details>

3. ¿Un Role de ConfigMap solo para HA proporciona todos los permisos que necesita Flink Native?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** No. La administración de recursos Native también requiere permisos adecuados para pods/servicios y otros recursos.

**Explicación:** Compruebe las necesidades de cada invocador e inspeccione errores de API, registros y reinicios; los fallos no siempre son silenciosos.

</details>

4. ¿Qué ajustan principalmente los autoscalers de Flink y de nodos?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** El paralelismo de Vertex y la capacidad de los nodos, respectivamente.

**Explicación:** La presión, las cuotas, la recuperación del estado y la ubicación acoplan los ciclos; Flink no actúa siempre primero.

</details>

5. ¿Karpenter debe crear un nodo para cada Pod en estado Pending?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** No. Distinga los pods que no se pueden programar de los problemas de descarga de imágenes, PVC, admisión y otras causas.

**Explicación:** Las restricciones, las solicitudes de recursos, la disponibilidad de instancias y las cuotas pueden impedir el aprovisionamiento.

</details>

6. ¿Un retraso de consolidación más largo que el tiempo de estabilización de Flink evita las interrupciones?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** No se garantiza. Los fallos de nodos, la recuperación de instancias Spot y el drift pueden ocurrir de forma independiente.

**Explicación:** Pruebe conjuntamente el aprovisionamiento, la restauración, la recuperación del retraso acumulado y las políticas de interrupción/PDB.

</details>

7. ¿El soporte de Flink administrado 2.3 implica que están disponibles todas las funciones upstream?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** No. Compruebe la combinación de Java 17/Python 3.12 y las exclusiones específicas del servicio.

**Explicación:** Las restricciones incluyen Java 21, ForSt, Native S3, telemetría personalizada y Studio. Distinga la alta disponibilidad de la infraestructura de AWS de las responsabilidades de la aplicación y el estado.

</details>

8. ¿Cómo se deben comparar los costos de KPU administradas con los de Spot en EKS?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** Compare el costo total y las operaciones con throughput, latencia y objetivos de recuperación equivalentes.

**Explicación:** Incluya los costos de orquestación y del almacenamiento/red relacionados para KPU, y los costos de interrupción/recuperación para Spot.

</details>

9. ¿La memoria administrada de RocksDB y los buffers de red comparten un mismo pool?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** No; pertenecen a regiones de presupuesto separadas.

**Explicación:** En la configuración revisada de 4 GiB, cambiar la fracción administrada de 0.4 a 0.5 no modificó la red y redujo el heap de tareas. Los presupuestos son distintos del RSS medido.

</details>

10. ¿Qué se debe comprobar cuando hay un PodMonitor, pero no tiene targets?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** Los selectores de monitor/namespace de Prometheus, las etiquetas reales de los pods, los puertos con nombre, los namespaces de destino y los permisos de descubrimiento.

**Explicación:** El pod de Operator de este chart no tenía una etiqueta instance predeterminada. Los metadatos de Deployment no se convierten automáticamente en etiquetas del pod.

</details>

11. ¿block-cache-usage es una proporción, y un Counter de Flink siempre es un Counter de Prometheus?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** No. El uso de caché se mide en bytes y el reporter revisado exporta los Counters de Flink como Gauges.

**Explicación:** Interprete también la capacidad, los aciertos y los fallos de caché. Los histogramas se asignan a Summaries; inspeccione TYPE y las etiquetas exportadas.

</details>

12. ¿Se debe establecer directamente kubernetes.cluster-id en un CR administrado por Operator?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** No. El validador de 1.15 lo prohíbe; la identidad se administra a partir del nombre/namespace del CR.

**Explicación:** No copie a ciegas configuraciones de CLI de bajo nivel. kubernetes.namespace y high-availability.cluster-id también están restringidos.

</details>

13. ¿Dos réplicas de JM y una lista de comprobación completada garantizan una recuperación instantánea y sin interrupciones?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** No. Valide la elección, la ubicación entre nodos/AZ, el almacenamiento, la restauración del estado, el tiempo de repetición y los resultados reales.

**Explicación:** Puede ser válido conservar los valores predeterminados. Más allá de la configuración, importan los resultados de SLO/recuperación medidos y quién se encarga de las operaciones.

</details>

---

[Volver a los materiales de aprendizaje](../../../data-on-eks/flink/04-operations-ha.md) | [Flink](../../../data-on-eks/flink/README.md)
