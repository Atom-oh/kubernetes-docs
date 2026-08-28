# Cuestionario sobre el operador KubeRay

Este cuestionario evalúa tu comprensión de KubeRay: qué es, sus tres CRD principales, el modelo de autoescalado de dos niveles que comparte con Karpenter y cómo gestiona la programación de GPU.

## Preguntas de opción múltiple

1. ¿Qué es KubeRay?
   - A) Un servicio administrado de AWS para ejecutar clústeres de Ray
   - B) Un operador de Kubernetes que administra clústeres de Ray como recursos personalizados nativos de Kubernetes, traduciendo la estructura de nodo principal/nodo de trabajo en Pods, Services y objetos relacionados
   - C) Un reemplazo de kubectl específico de Ray
   - D) Un panel de monitoreo para clústeres de Ray sin capacidad de administración de clústeres

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Un operador de Kubernetes que administra clústeres de Ray como recursos personalizados nativos de Kubernetes, traduciendo la estructura de nodo principal/nodo de trabajo en Pods, Services y objetos relacionados**

**Explicación:**
KubeRay es lo que hace que "Ray en Kubernetes" sea declarativo en vez de una cuestión de escribir manualmente especificaciones de Pod: reconcilia una especificación declarada de RayCluster/RayJob/RayService con los Pods, Services y demás objetos que Kubernetes necesita.
</details>

2. ¿Qué CRD representa un clúster de Ray sin procesar compuesto por un Pod principal y uno o más grupos de trabajadores?
   - A) RayJob
   - B) RayService
   - C) RayCluster
   - D) RayNodePool

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) RayCluster**

**Explicación:**
RayCluster es el CRD fundamental: un Pod principal más uno o más grupos de trabajadores, cada uno un conjunto de Pods de trabajo homogéneos (por ejemplo, un grupo de trabajadores de CPU y un grupo independiente de trabajadores de GPU), reconciliados por el operador para coincidir con la especificación deseada.
</details>

3. ¿Qué hace que RayJob sea adecuado para cargas de trabajo por lotes únicas o programadas?
   - A) Solo puede ejecutarse en un RayCluster preexistente y en ejecución permanente
   - B) Puede crear el RayCluster, ejecutar el trabajo enviado y desmontar el clúster cuando termina el trabajo, por lo que ningún clúster permanece inactivo entre ejecuciones
   - C) Desactiva por completo el autoescalador de Ray
   - D) Requiere que primero se ejecute un RayService independiente

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Puede crear el RayCluster, ejecutar el trabajo enviado y desmontar el clúster cuando termina el trabajo, por lo que ningún clúster permanece inactivo entre ejecuciones**

**Explicación:**
RayJob envía un trabajo por lotes y puede administrar opcionalmente el ciclo de vida completo del clúster subyacente — creación, ejecución del trabajo y desmontaje — lo que evita pagar por un clúster inactivo entre ejecuciones.
</details>

4. ¿Qué distingue a RayService de RayCluster?
   - A) RayService no puede ejecutar ninguna aplicación de Ray Serve
   - B) RayService administra un RayCluster más una aplicación de Ray Serve sobre él, y admite actualizaciones graduales sin tiempo de inactividad
   - C) RayService solo se ejecuta en un único Pod sin grupos de trabajadores
   - D) RayService está obsoleto en favor de RayCluster

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) RayService administra un RayCluster más una aplicación de Ray Serve sobre él, y admite actualizaciones graduales sin tiempo de inactividad**

**Explicación:**
RayService está dirigido al servicio de modelos en producción: administra tanto el RayCluster como la aplicación de Ray Serve desplegada en él, y admite actualizaciones graduales orientadas a cero tiempo de inactividad — consulta las notas de la versión actual de KubeRay sobre la madurez de esa ruta de actualización antes de depender de ella en producción.
</details>

5. En el patrón de autoescalado de dos niveles descrito para Ray en EKS, ¿qué decide el autoescalador de Ray y qué decide Karpenter?
   - A) El autoescalador de Ray decide los tipos de nodo EC2; Karpenter decide la colocación de tareas de Ray
   - B) El autoescalador de Ray decide cuántos Pods de trabajo de Ray se necesitan (ajustando los recuentos de réplicas de los grupos de trabajadores de RayCluster); Karpenter decide cuántos nodos EC2 aprovisionar para los Pods pendientes resultantes
   - C) Ambos bucles de control deciden redundante y simultáneamente lo mismo, para tolerancia a fallos
   - D) Karpenter decide el número de Pods; el autoescalador de Ray decide el número de nodos

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) El autoescalador de Ray decide cuántos Pods de trabajo de Ray se necesitan (ajustando los recuentos de réplicas de los grupos de trabajadores de RayCluster); Karpenter decide cuántos nodos EC2 aprovisionar para los Pods pendientes resultantes**

**Explicación:**
Un bucle de control (el autoescalador de Ray, coordinado mediante KubeRay) es responsable del número de Pods; otro independiente (Karpenter o Kubernetes Cluster Autoscaler) es responsable del número de nodos. Solo se comunican indirectamente, mediante el estado ordinario de programación de Pods pendientes — el mismo patrón de dos niveles que este sitio de documentación describe para Flink y Katib.
</details>

6. ¿Qué controla la configuración `idleTimeoutSeconds` del autoescalador de Ray y cuál es su valor predeterminado?
   - A) Cuánto tiempo espera el operador KubeRay antes de instalar CRD; valor predeterminado: 60 segundos
   - B) Cuánto tiempo debe permanecer inactivo un Pod de trabajo, sin tareas, actores ni objetos referenciados, antes de que el autoescalador lo reduzca; valor predeterminado: 60 segundos
   - C) Cuánto tiempo espera Karpenter antes de aprovisionar un nuevo nodo EC2; valor predeterminado: 60 segundos
   - D) El TTL para el Pod principal de un RayJob completado; valor predeterminado: 60 segundos

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Cuánto tiempo debe permanecer inactivo un Pod de trabajo, sin tareas, actores ni objetos referenciados, antes de que el autoescalador lo reduzca; valor predeterminado: 60 segundos**

**Explicación:**
`idleTimeoutSeconds` tiene un valor predeterminado de 60 segundos y es el período de espera que el autoescalador de Ray aplica antes de reducir un Pod de trabajo inactivo.
</details>

7. ¿Cómo determina KubeRay cuántas GPU ven los procesos de Ray de un grupo de trabajadores?
   - A) Lee un campo `numGPUs` independiente en los metadatos de nivel superior de la especificación de RayCluster
   - B) Lee el límite de recursos de GPU (por ejemplo, `nvidia.com/gpu`) establecido en la especificación de Pod del grupo de trabajadores, lo anuncia al programador y al autoescalador de Ray, y establece automáticamente el indicador `--num-gpus` del proceso de Ray para que coincida
   - C) El número de GPU debe establecerse manualmente con un comando `kubectl ray gpu-config` independiente después de que se inicien los Pods
   - D) KubeRay siempre asume exactamente una GPU por Pod de trabajo independientemente de la especificación de Pod

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Lee el límite de recursos de GPU (por ejemplo, `nvidia.com/gpu`) establecido en la especificación de Pod del grupo de trabajadores, lo anuncia al programador y al autoescalador de Ray, y establece automáticamente el indicador `--num-gpus` del proceso de Ray para que coincida**

**Explicación:**
La especificación de Pod de un grupo de trabajadores de GPU es la única fuente de verdad: KubeRay anuncia los límites de recursos de GPU del contenedor tanto al programador como al autoescalador de Ray, y configura `--num-gpus` en el proceso de Ray para que coincida, por lo que no hay un lugar independiente donde mantener sincronizado manualmente un recuento de GPU.
</details>

8. Según este documento, ¿cuál es la forma estándar de instalar el operador KubeRay?
   - A) Aplicar manualmente manifiestos sin procesar descargados de un gist aleatorio de GitHub
   - B) El chart oficial de Helm, añadido mediante `helm repo add kuberay https://ray-project.github.io/kuberay-helm/`
   - C) Un comando de una línea `kubectl create clusterrole kuberay`
   - D) No existe ningún método de instalación compatible; KubeRay debe compilarse desde el código fuente

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) El chart oficial de Helm, añadido mediante `helm repo add kuberay https://ray-project.github.io/kuberay-helm/`**

**Explicación:**
El repositorio `ray-project/kuberay-helm` aloja el chart oficial de Helm para instalar el operador KubeRay, su controlador y los CRD de RayCluster/RayJob/RayService.
</details>

## Preguntas de respuesta corta

9. Nombra los tres CRD principales que expone KubeRay e indica brevemente para qué se utiliza cada uno.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
- RayCluster: un clúster de Ray sin procesar con un Pod principal y uno o más grupos de trabajadores, reconciliado para coincidir con una especificación declarada.
- RayJob: envía un trabajo por lotes a un clúster de Ray y puede administrar opcionalmente el ciclo de vida completo de creación-ejecución-desmontaje de ese clúster para cargas de trabajo únicas o programadas.
- RayService: administra un RayCluster más una aplicación de Ray Serve sobre él para el servicio de modelos en producción, y admite actualizaciones graduales sin tiempo de inactividad.

**Explicación:**
Cada CRD está dirigido a un patrón de uso diferente — administración de clúster sin procesar, ejecución de trabajos por lotes y servicio en producción — construido sobre el mismo modelo de reconciliación subyacente.
</details>

10. Explica por qué el autoescalado de Ray en EKS necesita dos bucles de control independientes en lugar de uno, y de qué es responsable cada bucle.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
El autoescalador de Ray comprende el estado de nivel de Ray (tareas y actores pendientes), pero no sabe nada sobre la capacidad de EC2; Karpenter comprende los Pods pendientes a nivel de Kubernetes y el aprovisionamiento de EC2, pero no sabe nada sobre las tareas o actores de Ray. El autoescalador de Ray decide cuántos Pods de trabajo de Ray se necesitan y los solicita mediante el recuento de réplicas del grupo de trabajadores de RayCluster; Karpenter reacciona por separado a los Pods pendientes resultantes y aprovisiona nodos EC2 coincidentes para ejecutarlos.

**Explicación:**
Ningún bucle puede sustituir al otro porque cada uno opera con información que el otro no tiene. Esta división en dos niveles — un bucle para el número de Pods y otro para el número de nodos, que se comunican únicamente mediante el estado ordinario de programación de Kubernetes — es el mismo patrón que este sitio de documentación utiliza para describir el autoescalado de Flink y Katib.
</details>

---

[Volver a los materiales de aprendizaje](../../../ai-ml/ray/02-kuberay-operator.md) | [Siguiente cuestionario: Ray Train y Tune](./03-ray-train-tune-quiz.md)
