# Cuestionario sobre Experiment de Argo Rollouts

Este cuestionario evalúa tu comprensión de la CRD Experiment de Argo Rollouts: su jerarquía de recursos, el aislamiento del tráfico, los veredictos del análisis y la propagación de resultados.

1. ¿Cuál es el propósito principal de la CRD Experiment?
   - A) Desviar todo el tráfico de producción a una versión nueva
   - B) Validar una versión nueva con ReplicaSets efímeros y análisis
   - C) Guardar el historial de revisiones de un Rollout
   - D) Probar la carga de los nodos del clúster

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Validar una versión nueva con ReplicaSets efímeros y análisis**

**Explicación:**
Experiment inicia ReplicaSets efímeros y los escala a cero cuando termina. Los selectores de Service y los enrutadores deben proporcionar el aislamiento previsto. Que los ReplicaSets estén separados no garantiza por sí solo que los usuarios reales no se vean afectados.

</details>

2. ¿Qué ocurre cuando un paso del experimento termina en estado Failed o Error en la estrategia canary de un Rollout?
   - A) Se omite el paso y el Rollout continúa con el siguiente
   - B) El experimento fallido se reintenta automáticamente
   - C) Se aborta el Rollout y se mantiene la versión estable
   - D) El Rollout queda en pausa

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Se aborta el Rollout y se mantiene la versión estable**

**Explicación:**
El paso del experimento bloquea la progresión. El Rollout solo continúa cuando Experiment termina en la fase Successful; Failed/Error aborta el Rollout y lo deja en estado Degraded. Inconclusive, en cambio, establece una pausa `InconclusiveExperiment` para investigar y tomar una decisión operativa. Abortar no revierte los cambios de la base de datos ni los efectos secundarios externos.

</details>

3. Cuando la actualización a la revisión 2 del Rollout `demo-app` crea un experimento en el primer paso (índice 0), ¿qué formato de nombre base es correcto si no hay colisión de nombres? (El `PodTemplateHash` de la versión nueva es `74d8d8b4fb`.)
   - A) `demo-app-experiment-1`
   - B) `demo-app-74d8d8b4fb-2-0`
   - C) `experiment-demo-app-0-2`
   - D) `demo-app-2-0-74d8d8b4fb`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) `demo-app-74d8d8b4fb-2-0`**

**Explicación:**
Experiment se nombra como `<rollout-name>-<new-version PodTemplateHash>-<revision>-<step-index>`. Los ReplicaSets que crea se nombran como `<experiment-name>-<template-name>` (por ejemplo, `demo-app-74d8d8b4fb-2-0-baseline`), y los AnalysisRuns se nombran como `<experiment-name>-<analysis-name>`.

</details>

4. En el ejemplo, Service selecciona `traffic-class=production` y los pods del experimento tienen la etiqueta `traffic-class=experiment`. ¿Por qué ese Service no incluye esos pods?
   - A) Los pods del experimento se crean en otro espacio de nombres
   - B) NetworkPolicy bloquea los pods del experimento
   - C) El selector `traffic-class` de Service no coincide con la etiqueta del pod del experimento
   - D) Los pods del experimento tienen un `readinessProbe` que siempre falla

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) El selector `traffic-class` de Service no coincide con la etiqueta del pod del experimento**

**Explicación:**
El ejemplo separa explícitamente los conjuntos seleccionados mediante etiquetas/selectores. Otro Service que seleccione solo la etiqueta de la aplicación aún podría incluir los pods del experimento. Para enviarles tráfico intencionalmente, establece el atributo `service` en una plantilla para crear un Service con alcance al experimento, o usa `weight` en un Rollout con `trafficRouting` configurado.

</details>

5. ¿Qué requisito previo se necesita para enviar tráfico real a los pods del experimento mediante el campo `weight` de una plantilla?
   - A) El Rollout debe tener `trafficRouting` que admita Experiments ponderados
   - B) El número de réplicas de la plantilla debe ser igual al de las réplicas estables
   - C) AnalysisTemplate debe usar el proveedor web
   - D) Experiment debe crearse de forma independiente, sin un Rollout

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) El Rollout debe tener `trafficRouting` que admita Experiments ponderados**

**Explicación:**
`weight` pertenece a cada plantilla de paso de experimento de Rollout. Se necesita un enrutador compatible, como ALB/Istio; la ponderación de un canary normal no implica que se admita la división de tráfico de Experiment. Sin `trafficRouting`, crea un Service con alcance al experimento mediante el atributo `service` y conecta el enrutamiento por tu cuenta.

</details>

6. Con `failureLimit: 1` en una métrica de AnalysisTemplate, ¿cuándo pasa todo el AnalysisRun al estado Failed?
   - A) Inmediatamente después de una medición fallida
   - B) Después de dos mediciones fallidas (`failed > failureLimit`)
   - C) Solo después de un fallo consecutivo
   - D) Solo cuando terminan todas las mediciones indicadas por `count`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Después de dos mediciones fallidas (`failed > failureLimit`)**

**Explicación:**
`failureLimit` es el número de fallos permitidos; el AnalysisRun se considera Failed en cuanto el recuento de fallos lo supera. La implementación 1.10.0 compara `failed > failureLimit`. Del mismo modo, superar `inconclusiveLimit` genera Inconclusive, y superar `consecutiveErrorLimit` (errores consecutivos de recopilación, predeterminado 4) genera Error.

</details>

7. ¿Cuándo empieza a contar el temporizador de `duration` de Experiment?
   - A) Inmediatamente al crear el recurso Experiment
   - B) Cuando tiene éxito la primera medición de AnalysisRun
   - C) Cuando todos los ReplicaSets de `spec.templates` están en buen estado y disponibles
   - D) Justo antes de que Rollout llegue al paso del experimento

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Cuando todos los ReplicaSets de `spec.templates` están en buen estado y disponibles**

**Explicación:**
El controlador de Experiment primero crea los ReplicaSets por plantilla y espera hasta que todos los pods estén disponibles. El temporizador de duración y la creación de AnalysisRun empiezan solo después de eso; un inicio lento de los pods no reduce la ventana del experimento.

</details>

8. ¿Qué ocurre con los ReplicaSets del experimento cuando Experiment termina, tanto si tiene éxito como si falla?
   - A) Se conservan para el siguiente experimento
   - B) Se escalan a cero y se limpia cualquier Service creado mediante el atributo `service`
   - C) Se promueven a ReplicaSet estable
   - D) Permanecen hasta que se eliminen manualmente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Se escalan a cero y se limpia cualquier Service creado mediante el atributo `service`**

**Explicación:**
Experiment es efímero. Al terminar, se aplica la demora predeterminada de treinta segundos antes de reducir las réplicas a cero. Los Services generados se eliminan cuando las réplicas disponibles llegan a cero. Los objetos ReplicaSet/AnalysisRun pueden permanecer según las políticas de retención. Successful permite avanzar; Failed/Error aborta; e Inconclusive pausa el Rollout.

</details>
