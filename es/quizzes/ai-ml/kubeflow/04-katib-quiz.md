# Parte 4: Katib — Cuestionario sobre ajuste de hiperparámetros y AutoML

Este cuestionario evalúa tu comprensión de la arquitectura Experiment/Trial/Suggestion de Katib, los algoritmos de búsqueda que admite, la detención temprana, la recopilación de métricas y las consideraciones sobre presión de recursos al ejecutar Katib en EKS.

## Preguntas de opción múltiple

1. En la arquitectura de Katib, ¿cuál es la relación entre un Experiment, un Trial y un Suggestion?
   - A) Son tres nombres intercambiables para el mismo CRD
   - B) Un Suggestion posee muchos Experiments, cada uno de los cuales posee un Trial
   - C) Un Experiment posee muchos Trials, cada uno de los cuales ejecuta una combinación específica de hiperparámetros, mientras que un servicio Suggestion propone dichas combinaciones
   - D) Un Trial posee muchos Experiments, coordinados por un único Suggestion global

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Un Experiment posee muchos Trials, cada uno de los cuales ejecuta una combinación específica de hiperparámetros, mientras que un servicio Suggestion propone dichas combinaciones**

**Explicación:**
Un objeto Experiment describe el ajuste; maxTrialCount es un criterio de recuento de finalizaciones, no un recuento de entrenamientos exitosos ni un límite de gasto inmutable. Cada Trial es una única ejecución de entrenamiento con una combinación específica de hiperparámetros. El servicio Suggestion implementa un algoritmo; cómo usa las observaciones previas depende de ese algoritmo.
</details>

2. ¿Qué algoritmo de búsqueda construye un modelo probabilístico de cómo los hiperparámetros se relacionan con la métrica objetivo y usa ese modelo para elegir el o los siguientes puntos más prometedores que probar?
   - A) Búsqueda en cuadrícula
   - B) Búsqueda aleatoria
   - C) Optimización bayesiana
   - D) Hyperband

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Optimización bayesiana**

**Explicación:**
La optimización bayesiana construye un modelo probabilístico que relaciona los hiperparámetros con el objetivo y lo utiliza para seleccionar los siguientes candidatos con mayor probabilidad de mejorar el mejor resultado observado hasta ahora. La búsqueda aleatoria toma muestras independientes sin memoria de Trials anteriores; la búsqueda en cuadrícula enumera exhaustivamente combinaciones discretas; Hyperband asigna un presupuesto pequeño de forma amplia y lo reasigna a los supervivientes tempranos.
</details>

3. ¿Qué concesión hace Hyperband en comparación con otorgar a cada configuración un presupuesto de entrenamiento completo e igual?
   - A) Entrena cada configuración hasta completarla antes de compararlas
   - B) Otorga a muchas configuraciones un presupuesto pequeño, descarta anticipadamente a las de peor rendimiento y reasigna el presupuesto liberado a las supervivientes
   - C) Solo prueba una configuración a la vez
   - D) Ignora por completo el rendimiento intermedio y elige configuraciones al azar

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Otorga a muchas configuraciones un presupuesto pequeño, descarta anticipadamente a las de peor rendimiento y reasigna el presupuesto liberado a las supervivientes**

**Explicación:**
Hyperband intercambia información exhaustiva por configuración por poda temprana: primero ejecuta muchas configuraciones a bajo costo, descarta de forma agresiva las que parecen más débiles y asigna el presupuesto de recursos liberado a las configuraciones que aún son prometedoras.
</details>

4. En la spec de un Experiment, ¿qué define el campo `objective`?
   - A) La imagen de contenedor utilizada para ejecutar cada Trial
   - B) La métrica que se debe optimizar y si debe maximizarse o minimizarse
   - C) La cantidad de Trials que pueden ejecutarse en paralelo
   - D) Los hiperparámetros internos del algoritmo de búsqueda

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) La métrica que se debe optimizar y si debe maximizarse o minimizarse**

**Explicación:**
`objective` nombra la métrica (p. ej., exactitud o pérdida) y el objetivo (maximizar o minimizar), y puede incluir opcionalmente un valor objetivo que permite que el Experiment se detenga temprano una vez alcanzado. El espacio de búsqueda se define por separado, en `parameters`, y la forma en que se ejecuta el trabajo de cada Trial se define en `trialTemplate`.
</details>

5. ¿Qué verificó esta revisión sobre el cálculo del umbral medianstop de Katib 0.19.0?
   - A) Detiene por completo el Experiment cuando termina el Trial mediano
   - B) Almacena los promedios de Trials exitosos sobre las primeras observaciones start_step y luego calcula su media aritmética
   - C) Solo permite que se ejecute exactamente la mitad de todos los Trials propuestos
   - D) Selecciona el valor mediano de hiperparámetros como respuesta final

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Almacena los promedios de Trials exitosos sobre las primeras observaciones start_step y luego calcula su media aritmética**

**Explicación:**
La guía oficial describe una regla de mediana, pero la versión 0.19.0 calcula una media aritmética. Los promedios de Trials exitosos [1, 2, 100] producen aproximadamente 34.333 en la función sin cambios, no la mediana estadística 2. Los valores predeterminados son min_trials_required=3 y start_step=4; también se aplican requisitos de collector/timestamp.
</details>

6. ¿Cómo obtiene normalmente Katib el valor de la métrica objetivo desde el contenedor de entrenamiento de un Trial en ejecución?
   - A) El contenedor de entrenamiento debe llamar directamente a una API de Katib desde su código
   - B) Los collectors de extracción configurados recopilan métricas, o el modo Push envía report_metrics() al administrador de DB
   - C) Katib pausa el contenedor e inspecciona directamente su memoria
   - D) El scheduler de Kubernetes extrae automáticamente la métrica del uso de recursos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Los collectors de extracción configurados recopilan métricas, o el modo Push envía report_metrics() al administrador de DB**

**Explicación:**
Los collectors StdOut/File/TensorFlowEvent y Custom coexisten con el modo Push. El scraping HTTP arbitrario no es una opción predeterminada integrada. La inyección de extracción requiere etiquetado de namespace, configuración de webhook y del Pod/contenedor de destino. El éxito de un Job por sí solo no demuestra la recopilación de métricas.
</details>

7. ¿Por qué un valor alto de `parallelTrialCount` genera una presión de recursos más intensa en un clúster EKS que el mismo `maxTrialCount` ejecutado con baja concurrencia?
   - A) `parallelTrialCount` no afecta cuántos pods se crean
   - B) Un paralelismo alto significa que muchos Trials (y sus solicitudes de recursos, p. ej., GPUs) llegan al clúster al mismo tiempo en lugar de distribuirse, lo que produce un pico de demanda breve e intenso
   - C) EKS limita `parallelTrialCount` a 1 de forma predeterminada
   - D) Los Trials paralelos siempre se ejecutan en el mismo nodo, por lo que no hay demanda adicional

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Un paralelismo alto significa que muchos Trials (y sus solicitudes de recursos, p. ej., GPUs) llegan al clúster al mismo tiempo en lugar de distribuirse, lo que produce un pico de demanda breve e intenso**

**Explicación:**
Cada Trial concurrente es un trabajo de entrenamiento completo. La demanda es concurrencia × Pods por Trial × recursos por Pod, más la sobrecarga de collectors y servicios, lo que puede aumentar la demanda drásticamente incluso para un Experiment cuyo `maxTrialCount` total parece modesto.
</details>

8. En EKS, ¿cuál es una explicación probable si los pods de Trial recién creados permanecen pending durante un tiempo justo después de que se inicia un Experiment con `parallelTrialCount` alto?
   - A) El servicio Suggestion se ha bloqueado
   - B) Es posible que esté esperando capacidad; confírmalo mediante eventos de Pod, condiciones de NodePool, cuotas, capacidad de EC2 y estado de bootstrap
   - C) Katib siempre pausa los Trials nuevos durante un período fijo de calentamiento
   - D) El sidecar metrics-collector está bloqueando el inicio del pod

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Es posible que esté esperando capacidad; confírmalo mediante eventos de Pod, condiciones de NodePool, cuotas, capacidad de EC2 y estado de bootstrap**

**Explicación:**
El estado Pending por sí solo no demuestra que Karpenter esté aprovisionando correctamente. La afinidad, los taints, los volúmenes, las cuotas, los límites de capacidad y los fallos de bootstrap también pueden explicarlo. Usa los eventos observados y el estado del controller.
</details>

## Preguntas de respuesta corta

9. Menciona dos de los algoritmos de búsqueda que admite Katib y, en una oración para cada uno, describe para qué problema es más adecuado.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** Cualquiera de dos de los siguientes: búsqueda aleatoria (referencia económica para espacios de búsqueda grandes o poco comprendidos), búsqueda en cuadrícula (cobertura exhaustiva de espacios discretos pequeños y de baja dimensionalidad), optimización bayesiana (reduce el total de Trials necesarios cuando cada Trial es costoso, mediante un modelo probabilístico del objetivo), Hyperband (poda temprano configuraciones de bajo rendimiento usando una señal temprana económica e informativa), o CMA-ES (evolución con adaptación de covarianza), o PBT (una estrategia independiente de entrenamiento basado en población que requiere compartir checkpoints).

**Explicación:**
Cada algoritmo intercambia de manera distinta el costo de exploración por la eficiencia de búsqueda, y la elección correcta depende de cuán costoso sea un solo Trial y de cuánta estructura tenga el espacio de búsqueda.
</details>

10. ¿Cuál es la diferencia entre lo que hace Hyperband y lo que hace la detención temprana (p. ej., la regla de detención por mediana), dado que ambos buscan evitar desperdiciar capacidad de cómputo?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** Hyperband es una estrategia de búsqueda que decide de antemano cuánto presupuesto de recursos otorgar a cada configuración; la detención temprana es una comprobación en tiempo de ejecución aplicada a un Trial que ya está en curso, según su rendimiento relativo respecto de sus pares en ese punto del entrenamiento.

**Explicación:**
Ambos operan en niveles diferentes: la poda de Hyperband forma parte de la estrategia general de asignación de presupuesto del algoritmo de búsqueda, mientras que la detención temprana es una decisión por Trial tomada mientras ese Trial se está ejecutando, sujeta a una configuración compatible de collector/log, y no es compatible automáticamente con todas las combinaciones.
</details>

## Pregunta práctica / aplicada

11. Estás configurando un Experiment en el que cada Trial solicita una GPU y el clúster tiene un Karpenter NodePool para instancias GPU que normalmente tarda varios minutos en aprovisionar nueva capacidad. Estableces `maxTrialCount: 60` y estás decidiendo el valor de `parallelTrialCount`. Explica, en unas pocas oraciones, la compensación entre establecerlo alto (p. ej., 20) frente a bajo (p. ej., 4) en este entorno.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** Un valor alto de `parallelTrialCount` (p. ej., 20) puede procesar Trials en menos rondas cuando hay capacidad disponible, pero produce una ráfaga intensa de 20 solicitudes de GPU simultáneas, que puede superar la velocidad con la que Karpenter puede aprovisionar nodos GPU, dejando los primeros Trials pending en lugar de entrenar y, potencialmente, aumentando bruscamente la capacidad compartida del clúster si otras cargas de trabajo compiten por el mismo GPU NodePool. Un valor bajo de `parallelTrialCount` (p. ej., 4) distribuye los mismos 60 Trials en más rondas, da a Karpenter tiempo para aprovisionar de forma incremental y reduce el riesgo de un pico de capacidad, aunque posiblemente aumenta el tiempo transcurrido. El tiempo y el costo reales dependen de la capacidad, las duraciones, los fallos, la detención y la recuperación de nodos.

**Explicación:**
`parallelTrialCount` y `maxTrialCount` deben ajustarse conjuntamente teniendo en cuenta el comportamiento del escalado automático del clúster, no tratarse como configuraciones independientes, especialmente cuando los Trials solicitan recursos escasos o lentos de aprovisionar como las GPUs.
</details>

---

[Volver a los materiales de aprendizaje](../../../ai-ml/kubeflow/04-katib.md)
