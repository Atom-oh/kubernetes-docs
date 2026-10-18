# Cuestionario sobre la ubicación de cargas de trabajo en EKS Hybrid Nodes

> **Documento relacionado**: [Ubicación de cargas de trabajo](../../eks-hybrid-nodes/06-workload-placement.md)
> **Última actualización**: 13 de septiembre de 2026

### 1. ¿Cuál no es un mecanismo directo para seleccionar o habilitar la ubicación de un Pod?

A. `nodeSelector`

B. Afinidad de nodo

C. Taints y tolerations

D. PodDisruptionBudget

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D. PodDisruptionBudget**

**Explicación:** Un PDB limita las solicitudes de expulsión voluntaria admitidas; no selecciona nodos ni garantiza la disponibilidad ante todas las rutas de eliminación. La selección de nodos, la afinidad y los taints cumplen distintas funciones de programación.

</details>

### 2. ¿Qué implica `dedicated=gpu:NoSchedule`?

A. Solo pueden ejecutarse allí contenedores que soliciten una GPU

B. Los Pods nuevos necesitan una toleration aplicable; eso por sí solo no demuestra que usen una GPU ni obliga a ubicarlos allí

C. Los Pods existentes se expulsan inmediatamente

D. El nodo anuncia automáticamente recursos de GPU

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Los Pods nuevos necesitan una toleration aplicable; eso por sí solo no demuestra que usen una GPU ni obliga a ubicarlos allí**

**Explicación:** Un Pod que solo usa CPU también puede tolerar el taint. Las solicitudes de recursos de GPU y las políticas de admisión son independientes. `NoSchedule` afecta a la programación nueva; `NoExecute` tiene semántica de expulsión distinta.

</details>

### 3. ¿Qué ofrece la afinidad de nodo preferida a una carga de trabajo que puede ampliarse a la nube?

A. Migrar automáticamente a las cargas ya programadas en la nube de vuelta a las instalaciones locales

B. Mantener una proporción fija de réplicas locales y en la nube

C. Preferir determinados nodos aptos, sujeto a las demás restricciones y a la capacidad disponible

D. Capacidad ilimitada de AWS después del octavo Pod

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Preferir determinados nodos aptos, sujeto a las demás restricciones y a la capacidad disponible**

**Explicación:** La afinidad preferida no detecta cuándo se agota la capacidad, no impone un orden estricto ni actúa como controlador de migración. La cantidad de nodos no equivale a la capacidad de Pods. Karpenter y el escalador de réplicas son ciclos de control separados; las cuotas, las ofertas, las IP y las dependencias de la carga de trabajo pueden impedir la ampliación.

</details>

### 4. Con `DoNotSchedule`, ¿cómo se interpreta `maxSkew` de topología?

A. Como límite de la cantidad total de Pods del clúster

B. En relación con el mínimo global entre los dominios aptos, incluido el comportamiento de `minDomains` cuando está configurado

C. Como garantía de distribución uniforme con `ScheduleAnyway`

D. Como recuento de cuentas de AWS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. En relación con el mínimo global entre los dominios aptos, incluido el comportamiento de `minDomains` cuando está configurado**

**Explicación:** Los dominios aptos dependen de las restricciones del Pod y de la política de topología. `ScheduleAnyway` usa una puntuación flexible y puede superar `maxSkew`. Si faltan dominios o las reglas son estrictas, los Pods pueden quedarse en estado Pending.

</details>

### 5. ¿Qué método conviene usar para datos persistentes locales?

A. Usar una etiqueta de nodo y suponer que los bytes ya están presentes

B. Usar PV y PVC locales administrados con su topología y vinculación, y planificar por separado el acceso o la replicación de datos para ubicarlos en la nube

C. Montar `/mnt/data` con `hostPath` y tratarlo como almacenamiento portátil

D. Mover el Pod a cualquier nodo de la nube sin comprobar el volumen

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Usar PV y PVC locales administrados con su topología y vinculación, y planificar por separado el acceso o la replicación de datos para ubicarlos en la nube**

**Explicación:** Las etiquetas no crean ni replican datos. La afinidad de nodo de un PV local y `WaitForFirstConsumer` coordinan la ubicación; un volumen local vinculado no queda disponible automáticamente en un nodo EC2 de respaldo.

</details>

### 6. ¿Qué ayuda a conseguir la antiafinidad requerida por hostname?

A. Una garantía completa de disponibilidad de la aplicación

B. Separar réplicas coincidentes entre nodos de Kubernetes aptos cuando hay capacidad suficiente

C. Separación garantizada entre fuentes de alimentación física independientes

D. Reparar réplicas automáticamente sin otros controladores

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Separar réplicas coincidentes entre nodos de Kubernetes aptos cuando hay capacidad suficiente**

**Explicación:** Reduce una fuente de fallos correlacionados. Las réplicas restantes aún requieren disponibilidad, dependencias y capacidad de servicio suficientes, y distintos nodos de Kubernetes pueden compartir un host físico o dominio de fallo.

</details>

### 7. ¿Puede eliminarse un Pod local con `deletion-cost: 1000` antes que un Pod en la nube con coste 0?

A. No; el valor 1000 hace que no se pueda expulsar

B. No; el coste es el primer criterio que compara ReplicaSet

C. Sí; en el controlador revisado, la asignación, la fase y la disponibilidad preceden al coste de eliminación

D. Solo si la anotación de coste no existe

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Sí; en el controlador revisado, la asignación, la fase y la disponibilidad preceden al coste de eliminación**

**Explicación:** Los criterios de Pod sin asignar, Pending/Unknown y NotReady pueden tener prioridad. El coste de eliminación es una preferencia de mejor esfuerzo entre los Pods del mismo ReplicaSet, no una protección frente a todos los controladores, despliegues, expulsiones o fallos.

</details>

### 8. ¿Por qué es incompleto el antiguo webhook mutante de ubicación que solo responde a CREATE?

A. Las solicitudes de creación de Pods nunca admiten webhooks

B. La nube no tiene etiquetas

C. Normalmente, una solicitud CREATE aún no está vinculada a un nodo, por lo que la ubicación final en un nodo no está disponible

D. El coste de eliminación solo se puede cambiar antes de programar el Pod

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Normalmente, una solicitud CREATE aún no está vinculada a un nodo, por lo que la ubicación final en un nodo no está disponible**

**Explicación:** Un proceso posterior a la vinculación puede inspeccionar `spec.nodeName`. Un webhook de producción también necesita un backend, un Service, TLS y una política de alcance válidos; uno incompleto con modo de fallo cerrado puede bloquear la creación de Pods.

</details>

### 9. ¿Karpenter 1.14.1 lee `pod-deletion-cost`?

A. No; solo ReplicaSet puede leerlo

B. Sí; como parte de una heurística de coste de expulsión normalizada junto con otros datos, pero no prohíbe las interrupciones

C. Sí; 1000 garantiza una protección 1000 veces mayor

D. Sí; sustituye los PDB y todos los presupuestos de interrupción

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Sí; como parte de una heurística de coste de expulsión normalizada junto con otros datos, pero no prohíbe las interrupciones**

**Explicación:** El código fuente etiquetado de Karpenter incluye la anotación en el coste de expulsión del Pod. Aún se tienen en cuenta la evaluación de candidatos, el estado del nodo, la prioridad y las restricciones del ciclo de vida; las anotaciones de coste no garantizan que un nodo vacío se elimine de inmediato.

</details>

### 10. ¿Qué hace más seguro el parche de anotación para un Pod individual que el antiguo CronJob de todo el clúster?

A. Suprimir todos los errores de API

B. Inferir la ubicación en la nube cuando faltan etiquetas

C. Comprobar el propietario previsto de ReplicaSet, la clasificación del nodo, el UID del Pod y `resourceVersion`, y luego revisar un parche acotado

D. Eliminar las pruebas de actualizaciones concurrentes después del primer conflicto

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Comprobar el propietario previsto de ReplicaSet, la clasificación del nodo, el UID del Pod y `resourceVersion`, y luego revisar un parche acotado**

**Explicación:** El ejemplo rechaza estados desconocidos o Pods sin programar y genera un parche revisable. Las comprobaciones de UID, `resourceVersion` y nodo rechazan estados obsoletos, y se conservan las anotaciones que no guardan relación. No recorre ni modifica todos los espacios de nombres.

</details>
