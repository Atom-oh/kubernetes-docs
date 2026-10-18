# Cuestionario sobre la arquitectura de App Mesh frente a VPC Lattice

Este cuestionario evalúa tu comprensión de las diferencias estructurales entre los modelos de sidecar y plano de datos administrado, la correspondencia entre recursos y las brechas de funciones.

## Preguntas de opción múltiple

1. ¿Cómo se deben evaluar las brechas de funciones durante una migración?
   - A) AWS simplemente aún no las ha implementado y las agregará pronto
   - B) Compara las API reales de App Mesh y Lattice; la ubicación del proxy por sí sola no demuestra que una función sea imposible
   - C) Esas funciones no funcionan con HTTP/2
   - D) No son necesarias porque las políticas de IAM pueden reemplazarlas

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Compara las API reales de App Mesh y Lattice; la ubicación del proxy por sí sola no demuestra que una función sea imposible**

**Explicación:**
Las funciones genéricas de Envoy/Istio no son automáticamente funciones de App Mesh. Haz un inventario de los controles configurados y elige reemplazos en la aplicación o el proxy para las brechas de la API actual del producto.
</details>

2. ¿Por qué se dice que App Mesh VirtualNode no se corresponde uno a uno con un Target Group de VPC Lattice?
   - A) Se pueden crear muchos VirtualNode, pero solo un Target Group
   - B) Los atributos de identidad, backend, pool de conexiones y detección de valores atípicos que incluía VirtualNode se distribuyen entre varios recursos o desaparecen
   - C) Target Groups no admiten Lambda
   - D) VirtualNode depende de Cloud Map, lo que hace imposible la conversión

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Los atributos de identidad, backend, pool de conexiones y detección de valores atípicos que incluía VirtualNode se distribuyen entre varios recursos o desaparecen**

**Explicación:**
VirtualNode agrupaba «quién es esta carga de trabajo (identidad), a dónde se dirige (backends) y dónde recibe tráfico (listeners, comprobaciones de estado, pools de conexiones y detección de valores atípicos)» en un único recurso. En Lattice, solo el conjunto de destinos y las comprobaciones de estado se convierten en un Target Group; «a dónde se dirige» pasa a depender de las políticas de autenticación y los permisos de IAM; «quién es» pasa a ser un rol de IAM; y los pools de conexiones y la detección de valores atípicos no tienen un recurso equivalente. La tabla de correspondencias asigna nombres de recursos, no capacidades.
</details>

3. ¿Qué tarea de observabilidad es adecuada para una migración?
   - A) Disyuntores: son lo más difícil de implementar
   - B) Conserva el rastreo de la aplicación y reemplaza la telemetría que proporcionaba realmente el proxy anterior
   - C) Duplicación de tráfico: no hay ninguna alternativa
   - D) Inyección de fallos: es esencial para la respuesta a incidentes de producción

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Conserva el rastreo de la aplicación y reemplaza la telemetría que proporcionaba realmente el proxy anterior**

**Explicación:**
Lattice no tiene spans de seguimiento nativos, pero los spans de la aplicación siguen siendo posibles. Correlaciónalos con los ID de solicitud de Lattice, la temporización de los registros de acceso y las observaciones del cliente/servidor.
</details>

4. ¿Qué ocurre si AWS Gateway API Controller se detiene?
   - A) Todo el tráfico se bloquea de inmediato
   - B) El tráfico sigue fluyendo, pero los pods que se inician no se registran como destinos y los pods detenidos no se dan de baja
   - C) Los servicios de Lattice se eliminan automáticamente
   - D) La autenticación de IAM se deshabilita

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) El tráfico sigue fluyendo, pero los pods que se inician no se registran como destinos y los pods detenidos no se dan de baja**

**Explicación:**
La tarea principal del controlador es mantener sincronizados el estado declarado de Kubernetes y la lista real de destinos de Lattice: observa los cambios de endpoints en los Services a los que se hace referencia en `backendRefs` y registra o da de baja destinos. Si se detiene, Lattice sigue reenviando tráfico con la última lista conocida, pero esta queda obsoleta. Por eso, la disponibilidad y los permisos de IAM del Deployment del controlador están directamente relacionados con la fiabilidad del plano de datos.
</details>

5. En un entorno que también ejecuta ingress-nginx, ¿qué afirmación sobre el alcance de la migración es correcta?
   - A) ingress-nginx también debe reemplazarse por Lattice
   - B) AWS Gateway API Controller actualmente se centra solo en el tráfico Este-Oeste mediante Lattice; el tráfico Norte-Sur que gestiona ingress-nginx queda fuera del alcance, y lo habitual es que ambas rutas coexistan
   - C) ingress-nginx y Lattice no se pueden usar al mismo tiempo
   - D) Gateway API Controller también gestiona el tráfico Norte-Sur, por lo que ingress-nginx se debería eliminar de inmediato

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) AWS Gateway API Controller actualmente se centra solo en el tráfico Este-Oeste mediante Lattice; el tráfico Norte-Sur que gestiona ingress-nginx queda fuera del alcance, y lo habitual es que ambas rutas coexistan**

**Explicación:**
Kubernetes Gateway API se diseñó para cubrir tanto el tráfico Norte-Sur (Ingress) como el Este-Oeste (Mesh), pero AWS Gateway API Controller actualmente se centra solo en el tráfico Este-Oeste. Las funciones Norte-Sur del tipo ALB/NLB pertenecen a AWS Load Balancer Controller. Por lo tanto, la ruta de ingreso que ofrece ingress-nginx no está dentro del alcance de esta migración; solo el tráfico Este-Oeste pasa a Lattice y se espera que ambas rutas coexistan.
</details>

6. ¿Por qué se usa un readiness gate de pod en un entorno de Lattice?
   - A) Para limitar el uso de CPU de un pod
   - B) Para que un pod no se marque como Ready hasta que su estado de Target Group de Lattice sea Healthy, y así evitar que una actualización progresiva termine los pods antiguos antes de que estén sanos los nuevos
   - C) Para bloquear el tráfico hasta que las credenciales de IAM estén listas
   - D) Para esperar la inyección del sidecar de Envoy

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Para que un pod no se marque como Ready hasta que su estado de Target Group de Lattice sea Healthy, y así evitar que una actualización progresiva termine los pods antiguos antes de que estén sanos los nuevos**

**Explicación:**
Kubernetes puede considerar Ready un pod mientras el Target Group de Lattice todavía no lo ve como Healthy. Si una actualización progresiva termina los pods antiguos en ese estado, se produce un intervalo sin ningún destino sano. Un readiness gate de pod vincula la evaluación de salud de Lattice a la condición Ready del pod y evita ese intervalo; es un mecanismo importante para lograr una migración sin interrupciones.
</details>
