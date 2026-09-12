# Cuestionario de arquitectura de Ray

## Preguntas de opción múltiple

1. ¿Cómo se envía una función remota?
   - A) Llamar a f(...) normalmente
   - B) Usar f.remote(...) en la función @ray.remote
   - C) Llamar únicamente a ray.get(f)
   - D) Crear un Pod para cada llamada

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

El ejemplo de retorno único produce un ObjectRef; ray.get lee su valor.
</details>

2. ¿Todas las tareas de Ray son independientes y no tienen efectos secundarios?
   - A) Sí; Ray nunca rastrea dependencias
   - B) No; se deben considerar las dependencias de ObjectRef, los efectos secundarios y los reintentos
   - C) Solo los actors devuelven ObjectRefs
   - D) Cada función se ejecuta exactamente una vez

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Una unidad de ejecución sin estado no garantiza pureza ni ejecución exactamente una vez.
</details>

3. ¿Qué afirmación sobre el estado de un actor es correcta?
   - A) La memoria de la instancia persiste entre llamadas; la recuperación ante fallos es independiente
   - B) Todo el estado es automáticamente duradero
   - C) Los actors se ejecutan solo en el head
   - D) Habilitar reinicios restaura la memoria anterior

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

max_restarts vuelve a ejecutar el constructor; no reemplaza la recuperación mediante checkpoints.
</details>

4. ¿Qué alcance de zero-copy se verificó?
   - A) Todos los objetos de Python y la memoria de GPU
   - B) Una RAM física compartida por cada nodo
   - C) Vistas de memoria compartida de NumPy de solo lectura en el mismo nodo
   - D) Costo de transferencia de red cero en todos los casos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

La mutación requiere una copia. No lo generalices a otros objetos, GPU ni transferencias entre nodos.
</details>

5. ¿Cuál es el nombre y la función de GCS?
   - A) Global Control Service; metadatos del clúster, como actors, nodos y placement groups
   - B) GPU Copy Store para todos los pesos
   - C) Global Control Store; el único propietario de todos los metadatos de ObjectRef
   - D) Reemplazo del servidor de API de Kubernetes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

Los metadatos de propiedad de objetos pertenecen al proceso que crea el ObjectRef original, no universalmente al GCS.
</details>

6. ¿Pueden dos nodos con una CPU libre cada uno ejecutar una tarea de dos CPU?
   - A) Siempre, porque su suma es dos
   - B) Ray divide automáticamente la tarea por la mitad
   - C) No; la tarea debe caber en un único nodo viable
   - D) Los requisitos de CPU nunca importan si hay memoria disponible

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

La selección a nivel de clúster sigue dependiendo de la viabilidad de recursos a nivel de nodo.
</details>

7. ¿Qué significa num_cpus=1?
   - A) El SO fija todos los threads a un core
   - B) Un requisito lógico de scheduling/admisión de Ray, independiente de los límites del SO
   - C) Un core físico dedicado garantizado
   - D) Un límite automático de memoria de GPU

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Los límites del contenedor y la configuración de threads de las bibliotecas son independientes.
</details>

8. ¿Qué hace KubeRay?
   - A) Elige automáticamente Train, Tune o Serve para la aplicación
   - B) Reconcilia los CR de Ray y los ciclos de vida de los Pod en Kubernetes
   - C) Reemplaza kube-scheduler
   - D) Crea una nueva instancia EC2 para cada tarea de Ray

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

El scheduling del trabajo de Ray, la ubicación de Pod y el aprovisionamiento de EC2 son capas independientes.
</details>

## Preguntas de respuesta corta

9. ¿Por qué un actor es adecuado para mantener un modelo residente entre solicitudes?

<details>
<summary>Mostrar respuesta</summary>

Una instancia remota explícita posee el estado. No dependas para la corrección de la reutilización incidental de la caché global del task-worker. Los fallos de actor siguen requiriendo un diseño de checkpoints y recuperación.
</details>

10. ¿Por qué separar la recuperación de GCS de la recuperación de objetos y actors de la aplicación?

<details>
<summary>Mostrar respuesta</summary>

Los metadatos duraderos del clúster, la recuperación de propiedad/linaje/valor de objetos y los checkpoints de actors resuelven problemas diferentes. La configuración de Redis o RocksDB alpha por sí sola no restaura todos los valores ni el estado de la aplicación.
</details>

---

[Volver a los materiales de aprendizaje](../../../ai-ml/ray/01-architecture.md)
