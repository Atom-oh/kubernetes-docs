# Cuestionario de Ray Serve

Este cuestionario evalúa tu comprensión del modelo de Deployment de Ray Serve, Ray Serve LLM, el autoescalado a nivel de Serve, la inferencia con GPU y cómo RayService gestiona una aplicación de Serve en producción en EKS.

## Preguntas de opción múltiple

1. ¿Cómo se implementa un Deployment de Ray Serve por debajo de la capa de enrutamiento de Ray Serve?
   - A) Como un contenedor independiente sin relación con las primitivas principales de Ray
   - B) Como un actor de Ray, o un grupo de réplicas de actores, al que Ray Serve enruta solicitudes HTTP/gRPC
   - C) Como un Kubernetes CronJob que se ejecuta según un calendario fijo
   - D) Como una única tarea de Ray que se vuelve a ejecutar para cada solicitud entrante

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Un actor de Ray, o un grupo de réplicas de actores, al que Ray Serve enruta solicitudes HTTP/gRPC**

**Explicación:**
Ray Serve se basa directamente en la primitiva de actor de Ray. Un Deployment es un actor o un grupo de réplicas de actores, y Ray Serve enruta las solicitudes HTTP/gRPC entrantes a esas réplicas; por eso un modelo cargado una vez en la memoria de una réplica puede responder a muchas solicitudes sin volver a cargarse.
</details>

2. ¿Qué es una "aplicación" en la terminología de Ray Serve?
   - A) Un único Deployment sin capacidad de escalar
   - B) Uno o más Deployments compuestos — por ejemplo, un Deployment de preprocesamiento que alimenta a un Deployment de inferencia de modelos — que forman una canalización de servicio
   - C) Un RayJob que se ejecuta una vez y luego se desmonta
   - D) El namespace de Kubernetes en el que se ejecuta un RayCluster

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Uno o más Deployments compuestos — por ejemplo, un Deployment de preprocesamiento que alimenta a un Deployment de inferencia de modelos — que forman una canalización de servicio**

**Explicación:**
Ray Serve permite que varios Deployments se compongan en una canalización de servicio denominada aplicación, como un paso de preprocesamiento que alimenta su salida a un paso de inferencia de modelos. Cada Deployment de esa canalización aún puede escalar, versionarse y recibir recursos de forma independiente.
</details>

3. ¿Qué es `ray.serve.llm` y qué motor de inferencia documenta como su motor compatible?
   - A) Un módulo genérico de procesamiento por lotes sin relación con los LLM; admite cualquier motor
   - B) Un conjunto dedicado de componentes para servir LLM, construido sobre el modelo general de Deployment de Ray Serve, que documenta vLLM como su motor de inferencia compatible
   - C) Un reemplazo de Ray Serve que no utiliza actores
   - D) Un módulo exclusivo para entrenar LLM, no para servirlos

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Un conjunto dedicado de componentes para servir LLM, construido sobre el modelo general de Deployment de Ray Serve, que documenta vLLM como su motor de inferencia compatible**

**Explicación:**
`ray.serve.llm` proporciona construcciones de nivel superior adaptadas a patrones de servicio de LLM, superpuestas sobre el modelo general de Deployment de Ray Serve. Documenta vLLM como su motor de inferencia compatible y ofrece una API compatible con OpenAI diseñada para alinearse estrechamente con el propio servidor compatible con OpenAI de vLLM.
</details>

4. ¿Qué decide el propio autoescalador de Ray Serve y qué compara para tomar esa decisión?
   - A) Cuántos nodos EC2 debe aprovisionar Karpenter, según datos de facturación
   - B) Cuántas réplicas de actores necesita un Deployment específico, comparando las solicitudes en curso por réplica (en cola y en proceso) con un valor objetivo
   - C) Cuántos Pods de worker necesita un RayCluster, según la colocación de tareas pendientes
   - D) En qué región de AWS implementar el RayCluster

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Cuántas réplicas de actores necesita un Deployment específico, comparando las solicitudes en curso por réplica (en cola y en proceso) con un valor objetivo**

**Explicación:**
El autoescalador de Ray Serve es una capa independiente del autoescalado a nivel de clúster. Compara las solicitudes en curso por réplica con un objetivo y aumenta o reduce el número de réplicas de ese Deployment dentro de un mínimo y un máximo configurados.
</details>

5. En el esquema de autoescalado de tres niveles para una aplicación de Ray Serve en EKS, ¿qué capa se encuentra directamente por encima de Karpenter?
   - A) El AWS Load Balancer Controller
   - B) El autoescalador de Ray/KubeRay, que decide el número de Pods de worker según la colocación de actores pendientes
   - C) Un Kubernetes Horizontal Pod Autoscaler independiente que supervisa el uso de CPU
   - D) La aplicación cliente que realiza solicitudes

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) El autoescalador de Ray/KubeRay, que decide el número de Pods de worker según la colocación de actores pendientes**

**Explicación:**
Los tres niveles son: el autoescalador de Ray Serve decide el número de réplicas, el autoescalador de Ray/KubeRay decide el número de Pods de worker según la colocación de actores pendientes (incluidas las réplicas solicitadas por el autoescalador de Serve) y Karpenter decide el número de nodos para ejecutar esos Pods.
</details>

6. ¿Cómo solicita una GPU un Deployment de Ray Serve respaldado por GPU?
   - A) Mediante una API de reserva de GPU independiente y exclusiva de Ray Serve
   - B) Mediante el mecanismo normal de solicitud de recursos por actor de Ray, el mismo que usan los workers de Ray Train y Ray Tune
   - C) Conectándose manualmente mediante SSH a un nodo worker y configurando una variable de entorno
   - D) Los Deployments de Ray Serve no pueden solicitar GPU en absoluto

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Mediante el mecanismo normal de solicitud de recursos por actor de Ray, el mismo que usan los workers de Ray Train y Ray Tune**

**Explicación:**
Un Deployment de inferencia de modelos que necesita una GPU solicita una mediante el mismo mecanismo de solicitud de recursos a nivel de actor que utilizan Ray Train y Ray Tune, y la especificación del Pod del grupo de workers es la que anuncia la capacidad de GPU al planificador de Ray.
</details>

7. ¿Qué sucede cuando el autoescalador de Ray Serve solicita una nueva réplica de GPU pero ningún Pod de worker con GPU existente tiene espacio para ella?
   - A) La solicitud se descarta silenciosamente y nunca se crea una nueva réplica
   - B) La solicitud de réplica se convierte en un Pod pendiente, y Karpenter debe aprovisionar un nuevo nodo EC2 respaldado por GPU antes de que esa réplica pueda comenzar a atender tráfico
   - C) Ray Serve recurre automáticamente a ejecutar el modelo en CPU
   - D) El autoescalador de Ray omite completamente Karpenter y crea por sí mismo la instancia EC2

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) La solicitud de réplica se convierte en un Pod pendiente, y Karpenter debe aprovisionar un nuevo nodo EC2 respaldado por GPU antes de que esa réplica pueda comenzar a atender tráfico**

**Explicación:**
El autoescalado de Ray Serve y el tiempo de aprovisionamiento de nodos de Karpenter interactúan de la misma manera que para otras cargas de trabajo de GPU: un Pod pendiente hace que Karpenter aprovisione un nodo coincidente, y una aplicación de servicio que escale de forma agresiva las réplicas de GPU debe tener en cuenta ese tiempo de espera.
</details>

8. ¿Qué gestiona el CRD RayService en producción y qué capacidad admite específicamente?
   - A) Solo la aplicación de Serve, sin relación con el RayCluster subyacente
   - B) El RayCluster subyacente y la aplicación de Serve implementada sobre él de forma conjunta, admitiendo actualizaciones graduales sin tiempo de inactividad
   - C) Solo trabajos por lotes que se ejecutan una vez y se desmontan, sin capacidad de servicio
   - D) Una instantánea estática e inmutable de un clúster de Ray que no se puede actualizar

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) El RayCluster subyacente y la aplicación de Serve implementada sobre él de forma conjunta, admitiendo actualizaciones graduales sin tiempo de inactividad**

**Explicación:**
RayService gestiona un RayCluster junto con su aplicación de Serve como una unidad y es el recurso que admite actualizaciones graduales sin tiempo de inactividad para implementar una nueva versión de la aplicación o una especificación de RayCluster sin interrumpir las solicitudes en proceso -- consulta las notas de la versión actual de KubeRay para conocer la madurez de esa ruta de actualización antes de depender de ella en producción.
</details>

## Preguntas de respuesta corta

9. Explica por qué el autoescalador de Ray Serve y el autoescalador de Ray/KubeRay se describen como capas independientes que "solo ven la capa inmediatamente inferior".

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
El autoescalador de Ray Serve solo decide cuántas réplicas de actores necesita un Deployment específico según la carga de solicitudes; no tiene visibilidad sobre si una nueva réplica se ubica en un Pod de worker existente o requiere uno nuevo. El autoescalador de Ray/KubeRay, una capa más abajo, solo reacciona a la colocación de actores pendientes (incluidas las réplicas solicitadas por el autoescalador de Serve) para decidir el número de Pods de worker, sin saber nada acerca de las métricas a nivel de solicitud. Karpenter, otra capa más abajo, solo reacciona a Pods pendientes para decidir el número de nodos.

**Explicación:**
Cada bucle de control responde a una pregunta más acotada que la capa superior, y las capas se comunican solo de forma indirecta — mediante el estado normal que produce cada capa (las solicitudes de réplicas se convierten en Pods pendientes, los Pods pendientes se convierten en nodos pendientes) — no mediante coordinación directa.
</details>

10. Un equipo está implementando en producción en EKS una aplicación de Ray Serve de dos pasos (preprocesamiento y luego inferencia de modelos respaldada por GPU). Describe cómo encajan la topología de implementación, el autoescalado y la gestión del ciclo de vida descritos en este documento para esa aplicación.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
La aplicación se compone de dos Deployments — un Deployment de preprocesamiento y un Deployment de inferencia de modelos — cada uno implementado como réplicas de actores, donde la salida del Deployment de preprocesamiento alimenta al Deployment de inferencia. Cada Deployment autoescala su propio número de réplicas de forma independiente mediante el autoescalador de Ray Serve, según su propia carga de solicitudes. Las réplicas de actores del Deployment de inferencia solicitan GPU mediante el mecanismo normal de recursos por actor de Ray, y si el autoescalador de Ray Serve necesita más réplicas de GPU de las que los Pods de worker existentes pueden alojar, el autoescalador de Ray/KubeRay solicita más Pods de worker y Karpenter aprovisiona nodos EC2 coincidentes respaldados por GPU. En producción, un objeto `RayService` gestiona conjuntamente el RayCluster y la implementación de Serve de toda la aplicación, incluidas las actualizaciones sin tiempo de inactividad cuando cambia la aplicación o la especificación del clúster.

**Explicación:**
Esto reúne todos los conceptos del documento: el modelo de Deployment/aplicación basado en actores, la propia capa de autoescalado de Serve, la división del autoescalado en tres niveles con Ray/KubeRay y Karpenter, las solicitudes de recursos de GPU y RayService como gestor del ciclo de vida de producción para todo ello.
</details>

---

[Volver a los materiales de aprendizaje](../../../ai-ml/ray/04-ray-serve.md)
