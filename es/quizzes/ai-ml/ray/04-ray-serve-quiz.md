# Cuestionario de Ray Serve

## Preguntas de opción múltiple

1. ¿Cómo se relaciona un Serve Deployment con un Kubernetes Deployment?
   - A) Son idénticos
   - B) Es una unidad lógica de actor-réplica, no se corresponde uno a uno con Pods
   - C) Cada réplica requiere un nodo EC2
   - D) Serve no utiliza actores

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Un Ray Pod puede alojar varios actores de réplica.
</details>

2. ¿Cuál es la ubicación predeterminada del proxy en 2.58.0?
   - A) Siempre uno en el head
   - B) EveryNode en los nodos que alojan réplicas
   - C) Cada nodo EC2 incondicionalmente
   - D) Siempre Disabled

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

HeadOnly y Disabled son opciones explícitas. Distinga la documentación de arquitectura desactualizada de la API actual.
</details>

3. ¿En qué se diferencia el Deployment predeterminado de num_replicas="auto"?
   - A) Ambos inician inmediatamente 100 réplicas
   - B) Predeterminado fijo en 1; auto aplica mínimo 1/máximo 100/objetivo 2
   - C) Predeterminado GPU 1; auto GPU 100
   - D) Ninguno admite autoscaling

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Un AutoscalingConfig construido directamente establece el máximo predeterminado en 1, así que especifique el límite previsto.
</details>

4. ¿Cuál es el alcance de max_queued_requests?
   - A) Una cola global para todo el cluster
   - B) Cada llamador, como un proxy o handle
   - C) Capacidad de KV-cache de GPU
   - D) Cantidad de RayCluster Pods

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

El valor predeterminado -1 es ilimitado; exceder un límite configurado puede rechazar solicitudes HTTP o generar un handle BackPressureError.
</details>

5. ¿Un actor de réplica pendiente siempre crea un nuevo Pod y nodo EC2?
   - A) Siempre uno a uno
   - B) No; importan la capacidad existente, los límites de grupo, la colocación y la habilitación del autoscaler
   - C) Se convierte automáticamente en un modelo de CPU
   - D) Serve crea directamente nodos EC2

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Inspeccione por separado la colocación de actores, el tamaño del Pod y el aprovisionamiento de nodos.
</details>

6. ¿Qué se verificó sobre los backends de LLM en 2.58.0?
   - A) Solo existe vLLM
   - B) Existen los backends vLLM y SGLang; compruebe sus dependencias/configuración por separado
   - C) Cada kwarg de motor es idéntico entre los distintos motores
   - D) ray[serve] incluye todos los pesos de los modelos LLM

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Las dependencias de inferencia y el acceso/descarga de modelos son independientes. Las comprobaciones de CPU no validaron la ejecución de LLM.
</details>

7. ¿Qué afirmación sobre la actualización de RayService es precisa?
   - A) Es obligatoria para cada Deployment de EKS con garantía de ausencia de tiempo de inactividad
   - B) Es una ruta de ciclo de vida opcional; valide la estrategia, Gateway, capacidad, preparación y draining
   - C) Siempre solo edita la imagen de un Pod existente
   - D) Todas las transmisiones largas siempre se preservan

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Distinga los cambios de aplicación, las transiciones de cluster y la reconfiguración de actores.
</details>

8. ¿Qué verificó la prueba local de Echo?
   - A) Rendimiento de GPU
   - B) Calidad de LLM
   - C) HTTP 200 y llamadas a DeploymentHandle
   - D) Autoscaling multinodo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

Fue una pequeña prueba de CPU de un solo nodo sin un modelo, LLM, GPU ni Deployment en la nube.
</details>

## Preguntas de respuesta corta

9. ¿Por qué distinguir entre el máximo de solicitudes en curso, el objetivo de autoscaling y el límite de cola del llamador?

<details>
<summary>Mostrar respuesta</summary>

Controlan aspectos diferentes: solicitudes asignadas a réplicas, carga objetivo para el escalado y solicitudes en espera por llamador. Una configuración no establece todos los demás límites ni garantías de latencia.
</details>

10. ¿Por qué los tokens de cluster o ClusterIP no completan la seguridad de la aplicación?

<details>
<summary>Mostrar respuesta</summary>

Verifique por separado TLS, la autenticación/autorización de cada punto de entrada, los permisos de artefactos de modelo, el manejo de solicitudes/registros sensibles y las políticas de recursos/cola/timeout.
</details>

---

[Volver a los materiales de aprendizaje](../../../ai-ml/ray/04-ray-serve.md)
