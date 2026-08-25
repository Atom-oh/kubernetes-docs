# Cuestionario de arquitectura de Ray

Este cuestionario evalúa tu comprensión de las primitivas principales de Ray (tasks, actors y el object store), la arquitectura de clúster de Ray (head node y worker nodes), y cómo las bibliotecas de nivel superior de Ray se basan en esa misma base.

## Preguntas de opción múltiple

1. ¿Qué es Ray, fundamentalmente?
   - A) Un framework específico de dominio creado únicamente para el entrenamiento distribuido de modelos
   - B) Un framework de computación distribuida de código abierto para escalar cargas de trabajo de Python, basado en un pequeño conjunto de primitivas de propósito general
   - C) Un scheduler nativo de Kubernetes que reemplaza al kube-scheduler predeterminado
   - D) Un producto administrado de serving de modelos sin API de programación

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Un framework de computación distribuida de código abierto para escalar cargas de trabajo de Python, basado en un pequeño conjunto de primitivas de propósito general**

**Explicación:**
Ray no está creado para un único tipo de carga de trabajo. Proporciona primitivas de propósito general — tasks, actors y el object store — que admiten casos de uso que van desde tasks paralelas ad hoc hasta entrenamiento distribuido, ajuste de hiperparámetros y serving de modelos.
</details>

2. ¿Qué es una task de Ray?
   - A) Un objeto remoto con estado y de larga duración creado al aplicar `@ray.remote` a una clase
   - B) Una función sin estado que Ray ejecuta de forma remota, creada al aplicar `@ray.remote` a una función
   - C) El proceso que administra los metadatos del clúster en el head node
   - D) Un fragmento del object store distribuido

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Una función sin estado que Ray ejecuta de forma remota, creada al aplicar `@ray.remote` a una función**

**Explicación:**
Una task es una función remota sin estado. Al llamarla, devuelve un future de inmediato y Ray programa la ejecución real en algún worker con capacidad disponible. Como las tasks no conservan estado entre llamadas, Ray puede ejecutar cualquier llamada en cualquier worker con capacidad.
</details>

3. ¿Qué distingue a un actor de una task?
   - A) Un actor no tiene estado, mientras que una task conserva el estado entre llamadas
   - B) Un actor es una instancia remota con estado y de larga duración creada a partir de una clase, cuyo estado persiste entre llamadas a métodos
   - C) Un actor solo puede ejecutarse en el head node
   - D) Un actor no puede crearse con el decorador `@ray.remote`

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Un actor es una instancia remota con estado y de larga duración creada a partir de una clase, cuyo estado persiste entre llamadas a métodos**

**Explicación:**
Aplicar `@ray.remote` a una clase la convierte en un actor. Ray mantiene la instancia resultante activa como un proceso remoto de larga duración, por lo que el estado almacenado en ella — como los pesos de un modelo cargado o un contador — persiste entre llamadas a métodos, a diferencia de una task sin estado.
</details>

4. ¿Qué problema resuelve principalmente el object store distribuido de Ray?
   - A) Reemplaza la necesidad de un head node en un clúster de Ray
   - B) Evita la copia innecesaria de objetos grandes al permitir leerlos desde memoria compartida en lugar de volver a serializarlos en cada proceso que los necesita
   - C) Almacena la configuración del autoscaler del clúster
   - D) Programa tasks en worker nodes específicos

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Evita la copia innecesaria de objetos grandes al permitir leerlos desde memoria compartida en lugar de volver a serializarlos en cada proceso que los necesita**

**Explicación:**
El object store es un almacén distribuido de memoria compartida para los objetos que se pasan entre tasks y actors. Para objetos grandes, como datasets o pesos de modelos, esto evita el costo de serialización y copia de duplicar el objeto en cada proceso que lo necesita.
</details>

5. ¿Qué se ejecuta en el head node de un clúster de Ray, además de lo que se ejecuta en los worker nodes?
   - A) Solo el object store distribuido
   - B) El Global Control Store (GCS), el proceso driver (si se ejecuta allí) y el autoscaler
   - C) Solo las tasks y los actors enviados por los usuarios
   - D) Un control plane de Kubernetes independiente

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) El Global Control Store (GCS), el proceso driver (si se ejecuta allí) y el autoscaler**

**Explicación:**
El head node ejecuta el GCS (metadatos del clúster), el proceso driver si allí se ejecuta un script o una sesión de nivel superior, y el autoscaler, además de aportar CPU/GPU/memoria al pool de recursos de la misma manera que lo hacen los worker nodes.
</details>

6. ¿Cómo programa Ray las tasks y los actors en un clúster?
   - A) Según los recursos de cada nodo de forma aislada, lo que requiere que el usuario elija un nodo específico para cada task
   - B) Según el pool de recursos combinado del clúster, de modo que una task puede ubicarse en cualquier nodo con suficientes recursos libres
   - C) Solo en el head node, y los worker nodes se usan únicamente para almacenamiento
   - D) De forma aleatoria, sin considerar la CPU, GPU o memoria disponibles

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Según el pool de recursos combinado del clúster, de modo que una task puede ubicarse en cualquier nodo con suficientes recursos libres**

**Explicación:**
Ray programa el trabajo según el pool de recursos de todo el clúster, en lugar de hacerlo por nodo. Una task que solicita una cantidad determinada de CPU puede ejecutarse en cualquier nodo del clúster que tenga esa capacidad libre.
</details>

7. ¿Qué tienen en común Ray Train, Ray Tune y Ray Serve desde el punto de vista arquitectónico?
   - A) Cada uno implementa su propio sistema independiente de programación y tolerancia a fallos, sin depender del núcleo de Ray
   - B) Todos se basan en las mismas tasks, actors y object store subyacentes que las primitivas principales de Ray
   - C) Solo pueden ejecutarse fuera de un clúster de Ray
   - D) Reemplazan la necesidad de un head node

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Todos se basan en las mismas tasks, actors y object store subyacentes que las primitivas principales de Ray**

**Explicación:**
Las bibliotecas de nivel superior de Ray para entrenamiento, ajuste y serving reutilizan las mismas primitivas en lugar de volver a implementar por separado la programación y el movimiento de datos para cada carga de trabajo. Esta base compartida es la distinción arquitectónica clave de Ray frente a agrupar herramientas puntuales no relacionadas.
</details>

8. ¿Por qué ejecutar Ray en Kubernetes requiere algo más allá del propio concepto de clúster de Ray?
   - A) Porque Ray no puede ejecutarse dentro de contenedores
   - B) Porque la forma de clúster head/worker de Ray es una capa distinta de la propia programación de Kubernetes, por lo que algo debe traducir esa forma a objetos de Kubernetes como Pods y Deployments
   - C) Porque Kubernetes no admite autoscaling
   - D) Porque las tasks de Ray no pueden usar recursos de CPU en los nodos de Kubernetes

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Porque la forma de clúster head/worker de Ray es una capa distinta de la propia programación de Kubernetes, por lo que algo debe traducir esa forma a objetos de Kubernetes como Pods y Deployments**

**Explicación:**
La propia noción de Ray de un clúster (head node, worker nodes y autoscaler) no se asigna automáticamente al modelo de programación de Kubernetes. Algo tiene que traducir la forma de un clúster de Ray a Pods y Deployments que el scheduler de Kubernetes entienda — esa traducción es lo que proporciona KubeRay.
</details>

## Preguntas de respuesta corta

9. Un compañero de equipo está decidiendo si implementar una parte de la lógica como una task de Ray o un actor de Ray. Necesita mantener un modelo de machine learning cargado en memoria a lo largo de muchas solicitudes entrantes, en lugar de volver a cargarlo cada vez. ¿Qué primitiva debería usar y por qué?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: Un actor, porque es una instancia remota con estado y de larga duración — el modelo cargado puede mantenerse en el estado del actor y reutilizarse en muchas llamadas a métodos, en lugar de volver a cargarse en cada llamada, como requeriría una task sin estado.**

**Explicación:**
Las tasks no tienen estado y completan una única llamada; no hay ningún lugar en una task donde mantener un modelo cargado residente entre llamadas. La instancia de un actor permanece activa como proceso remoto, por lo que el estado, como los pesos de un modelo cargado, persiste entre las llamadas realizadas mediante el handle del actor.
</details>

10. ¿Por qué Ray implementa la programación, la tolerancia a fallos y el movimiento de datos una sola vez en sus primitivas principales en vez de una vez por biblioteca de nivel superior (Train, Tune, Serve)?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: Debido a que Ray Train, Ray Tune y Ray Serve se basan todos en las mismas tasks, actors y object store, cada biblioteca reutiliza esa implementación compartida en lugar de volver a implementar por separado la programación y el movimiento de datos para su propia carga de trabajo.**

**Explicación:**
Esta base compartida es la distinción arquitectónica clave de Ray frente a un ecosistema de herramientas puntuales independientes, cada una con su propio modelo de ejecución, que simplemente se agrupan juntas. Una ejecución de entrenamiento distribuido y una exploración de hiperparámetros son ambas, internamente, workers que se ejecutan como actors o tasks de Ray e intercambian datos mediante el mismo object store.
</details>

---

[Volver a los materiales de aprendizaje](../../../ai-ml/ray/01-architecture.md) | [Siguiente cuestionario: KubeRay Operator](./02-kuberay-operator-quiz.md)
