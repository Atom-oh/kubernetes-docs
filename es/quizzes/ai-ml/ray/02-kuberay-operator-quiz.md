# Cuestionario sobre el operador KubeRay

## Preguntas de opción múltiple

1. ¿Qué inicia la instalación del operador KubeRay?
   - A) Todas las cargas de trabajo de Ray automáticamente
   - B) El reconciler; aún deben crearse los CR de carga de trabajo
   - C) Todos los nodos GPU
   - D) Un Deployment para cada worker

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

La instalación del operador es independiente de la creación de recursos RayCluster, RayJob o RayService.
</details>

2. ¿Qué instala el chart 1.7.0 y cuál es el estado predeterminado de RayCronJob?
   - A) Solo existen tres CRD
   - B) Un CRD RayCronJob instalado siempre habilita la programación
   - C) Cuatro CRD, con el feature gate de RayCronJob deshabilitado de forma predeterminada
   - D) No existe API v1

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

Distinga entre RayCluster, RayJob, RayService y RayCronJob.
</details>

3. ¿Cuál es el comportamiento de limpieza predeterminado de RayJob?
   - A) Omitir shutdownAfterJobFinishes habilita la limpieza
   - B) TTL 0 elimina cada instancia EC2 y PVC
   - C) shutdownAfterJobFinishes tiene el valor predeterminado false; configure la limpieza y la preservación
   - D) Los clusters externos siempre se eliminan

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

Verifique TTL, deletionStrategy y la propiedad de los clusters compartidos frente a los creados.
</details>

4. ¿Qué requiere la actualización incremental de RayService?
   - A) Un feature gate por sí solo garantiza que no haya tiempo de inactividad
   - B) Estrategia, Gateway API/implementación, capacidad, preparación y drenaje
   - C) Solo editar la imagen de un Pod existente
   - D) Un RayJob obligatorio

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Desplaza el tráfico entre clusters; no es simplemente una actualización gradual in situ de un Pod.
</details>

5. ¿Qué secuencia de escalado es adecuada?
   - A) El autoscaler de Ray aprovisiona directamente toda la capacidad EC2
   - B) Demanda de Ray → reconciliación de Pod de KubeRay → colocación/aprovisionamiento de capacidad de Kubernetes
   - C) Karpenter llama a métodos de actor de Ray
   - D) Ambos controladores son propietarios del recurso idéntico

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Los estados Pending relacionados con imágenes, PVC o autorización no se resuelven únicamente añadiendo nodos.
</details>

6. ¿Cómo debe interpretarse idleTimeoutSeconds 60?
   - A) Cada worker desaparece exactamente 60 segundos después
   - B) Valor predeterminado global revisado; considere las anulaciones de grupo, los límites, la actividad y las condiciones de drenaje
   - C) TTL de todo RayJob
   - D) Tiempo fijo de aprovisionamiento de Karpenter

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

La duración de la configuración y la finalización real de la eliminación son diferentes.
</details>

7. ¿Qué afirmación sobre la precedencia de recursos GPU es precisa?
   - A) Solo se usan los límites de Pod; las anulaciones se ignoran
   - B) Los recursos de grupo estructurados y rayStartParams pueden anular los límites
   - C) Cada Pod siempre tiene una GPU
   - D) Las configuraciones lógicas crean más GPU físicas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Alinee los recursos lógicos de Ray con los device plugins, drivers y hardware visible.
</details>

8. ¿Una actualización de chart Helm actualiza automáticamente los esquemas CRD existentes?
   - A) Siempre los actualiza y elimina
   - B) No; verifique la compatibilidad de los CR almacenados y el procedimiento independiente de actualización de CRD
   - C) Los CRD son Pods ordinarios
   - D) Siempre es seguro eliminar primero los CRD

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Comprenda los límites del ciclo de vida de Helm crds/ y el impacto de eliminar CRD.
</details>

## Preguntas de respuesta corta

9. ¿Por qué el número de réplicas de worker y el número de Ray Pods no siempre son iguales?

<details>
<summary>Mostrar respuesta</summary>

Con numOfHosts, una réplica de grupo puede corresponder a varios hosts/Pods. Compare el spec real con los recursos generados.
</details>

10. ¿Por qué habilitar la autenticación mediante token de Ray no completa la configuración de seguridad?

<details>
<summary>Mostrar respuesta</summary>

Es independiente de TLS y no reemplaza la autenticación/autorización para cada endpoint de aplicación. Revise las rutas de acceso, la entrega de secretos, el soporte de versiones y la política organizativa.
</details>

---

[Volver a los materiales de aprendizaje](../../../ai-ml/ray/02-kuberay-operator.md)
