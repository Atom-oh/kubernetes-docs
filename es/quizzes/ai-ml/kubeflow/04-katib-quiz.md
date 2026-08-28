# Parte 4: Cuestionario sobre Katib — Ajuste de hiperparámetros y AutoML

Este cuestionario evalúa tu comprensión de la arquitectura Experiment/Trial/Suggestion de Katib, los algoritmos de búsqueda que admite, la detención temprana, la recopilación de métricas y las consideraciones de presión de recursos al ejecutar Katib en EKS.

## Preguntas de opción múltiple

1. En la arquitectura de Katib, ¿cuál es la relación entre un Experiment, un Trial y una Suggestion?
   - A) Son tres nombres intercambiables para el mismo CRD
   - B) Una Suggestion posee muchos Experiments, cada uno de los cuales posee un Trial
   - C) Un Experiment posee muchos Trials, cada uno ejecutando una combinación específica de hiperparámetros, mientras que un servicio Suggestion propone esas combinaciones
   - D) Un Trial posee muchos Experiments, coordinados por una sola Suggestion global

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Un Experiment posee muchos Trials, cada uno ejecutando una combinación específica de hiperparámetros, mientras que un servicio Suggestion propone esas combinaciones**

**Explicación:**
Un CRD Experiment describe una ejecución de ajuste y posee hasta `maxTrialCount` Trials durante su ciclo de vida. Cada Trial es una única ejecución de entrenamiento con una combinación específica de hiperparámetros. El servicio Suggestion implementa el algoritmo de búsqueda y propone qué combinaciones debe probar cada Trial, según los resultados anteriores.
</details>

2. ¿Qué algoritmo de búsqueda construye un modelo probabilístico de cómo los hiperparámetros se relacionan con la métrica objetivo y usa ese modelo para elegir los siguientes puntos más prometedores que se probarán?
   - A) Búsqueda en cuadrícula
   - B) Búsqueda aleatoria
   - C) Optimización bayesiana
   - D) Hyperband

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Optimización bayesiana**

**Explicación:**
La optimización bayesiana construye un modelo probabilístico que relaciona los hiperparámetros con el objetivo y lo usa para seleccionar los siguientes candidatos con mayor probabilidad de mejorar el mejor resultado observado hasta el momento. La búsqueda aleatoria toma muestras independientes sin memoria de Trials anteriores; la búsqueda en cuadrícula enumera exhaustivamente las combinaciones discretas; Hyperband asigna un presupuesto pequeño de forma amplia y lo reasigna a los supervivientes tempranos.
</details>

3. ¿Qué equilibrio establece Hyperband en comparación con dar a cada configuración un presupuesto de entrenamiento completo e igual?
   - A) Entrena cada configuración hasta completarla antes de compararlas
   - B) Da a muchas configuraciones un presupuesto pequeño, descarta temprano las de peor rendimiento y reasigna el presupuesto liberado a las supervivientes
   - C) Solo prueba una configuración a la vez
   - D) Ignora por completo el rendimiento intermedio y elige configuraciones al azar

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Da a muchas configuraciones un presupuesto pequeño, descarta temprano las de peor rendimiento y reasigna el presupuesto liberado a las supervivientes**

**Explicación:**
Hyperband intercambia información exhaustiva por configuración por poda temprana: primero ejecuta muchas configuraciones a bajo costo, descarta agresivamente las que parecen más débiles y entrega el presupuesto de recursos liberado a las configuraciones que siguen siendo prometedoras.
</details>

4. En la especificación de un Experiment, ¿qué define el campo `objective`?
   - A) La imagen de contenedor utilizada para ejecutar cada Trial
   - B) La métrica que se debe optimizar y si se debe maximizar o minimizar
   - C) El número de Trials que se pueden ejecutar en paralelo
   - D) Los hiperparámetros internos del algoritmo de búsqueda

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) La métrica que se debe optimizar y si se debe maximizar o minimizar**

**Explicación:**
`objective` nombra la métrica (por ejemplo, exactitud o pérdida) y el objetivo (maximizar o minimizar), y puede incluir opcionalmente un valor objetivo que permite al Experiment detenerse temprano una vez alcanzado. El espacio de búsqueda se define por separado, en `parameters`, y la forma de ejecutar el trabajo de cada Trial se define en `trialTemplate`.
</details>

5. Conceptualmente, ¿qué hace la regla de detención por mediana?
   - A) Detiene por completo el Experiment una vez que termina el Trial mediano
   - B) Compara el valor objetivo intermedio de un Trial con la mediana de sus pares en el mismo punto del entrenamiento y detiene el Trial temprano si está significativamente por detrás
   - C) Solo permite ejecutar exactamente la mitad de todos los Trials propuestos
   - D) Selecciona el valor mediano de hiperparámetro como respuesta final

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Compara el valor objetivo intermedio de un Trial con la mediana de sus pares en el mismo punto del entrenamiento y detiene el Trial temprano si está significativamente por detrás**

**Explicación:**
La detención por mediana es una forma de detención temprana: en vez de permitir que un Trial claramente con bajo rendimiento se ejecute hasta terminar, su valor intermedio se compara con la mediana de otros Trials en el mismo punto de entrenamiento, y se termina temprano si se queda significativamente corto, ahorrando el cómputo que de otro modo consumiría para un resultado poco probable de ser competitivo.
</details>

6. ¿Cómo obtiene normalmente Katib el valor de la métrica objetivo del contenedor de entrenamiento de un Trial en ejecución?
   - A) El contenedor de entrenamiento debe llamar directamente a una API de Katib desde su código
   - B) Un sidecar de recopilación de métricas sigue logs/stdout o extrae un endpoint de métricas e informa el valor analizado a Katib
   - C) Katib pausa el contenedor e inspecciona directamente su memoria
   - D) El scheduler de Kubernetes extrae automáticamente la métrica del uso de recursos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Un sidecar de recopilación de métricas sigue logs/stdout o extrae un endpoint de métricas e informa el valor analizado a Katib**

**Explicación:**
Se inyecta un sidecar de recopilación de métricas en el Pod del Trial junto al contenedor de entrenamiento. Observa la salida del contenedor de entrenamiento, normalmente analizando archivos stdout/log o extrayendo un endpoint de métricas expuesto, e informa la métrica objetivo a Katib, manteniendo el propio código de entrenamiento mayormente ajeno a Katib.
</details>

7. ¿Por qué un `parallelTrialCount` alto genera una presión de recursos más intensa en un clúster EKS que el mismo `maxTrialCount` ejecutado con baja concurrencia?
   - A) `parallelTrialCount` no afecta a la cantidad de Pods creados
   - B) Un alto paralelismo significa que muchos Trials (y sus solicitudes de recursos, por ejemplo, GPU) llegan al clúster al mismo tiempo en lugar de distribuirse, produciendo un pico de demanda breve e intenso
   - C) EKS limita `parallelTrialCount` a 1 de forma predeterminada
   - D) Los Trials paralelos siempre se ejecutan en el mismo nodo, por lo que no hay demanda adicional

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Un alto paralelismo significa que muchos Trials (y sus solicitudes de recursos, por ejemplo, GPU) llegan al clúster al mismo tiempo en lugar de distribuirse, produciendo un pico de demanda breve e intenso**

**Explicación:**
Cada Trial concurrente es un trabajo de entrenamiento completo. Un `parallelTrialCount` de 8 significa 8 solicitudes de recursos simultáneas (por ejemplo, solicitudes de GPU), en vez de distribuidas a lo largo del tiempo, lo que puede aumentar bruscamente la demanda incluso para un Experiment cuyo `maxTrialCount` total parece modesto.
</details>

8. En EKS, ¿cuál es una explicación probable si los Pods de Trial recién creados permanecen pendientes durante un tiempo justo después de que se inicia un Experiment con `parallelTrialCount` alto?
   - A) El servicio Suggestion se ha bloqueado
   - B) Karpenter está aprovisionando nuevos nodos con GPU en respuesta a la ráfaga de Pods pendientes, y los tipos de instancia con GPU suelen tener tiempos de aprovisionamiento más largos
   - C) Katib siempre pausa los nuevos Trials durante un período fijo de calentamiento
   - D) El sidecar de recopilación de métricas está bloqueando el inicio del Pod

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Karpenter está aprovisionando nuevos nodos con GPU en respuesta a la ráfaga de Pods pendientes, y los tipos de instancia con GPU suelen tener tiempos de aprovisionamiento más largos**

**Explicación:**
Una ráfaga de Pods de Trial pendientes desde un `parallelTrialCount` alto normalmente hace que Karpenter aprovisione nuevos nodos. Los tipos de instancia con GPU pueden tardar más en aprovisionarse que los de propósito general, por lo que los Trials pueden permanecer esperando capacidad de nodos; conviene verificar los eventos de los Pods de Trial antes de asumir que el propio algoritmo de búsqueda es lento.
</details>

## Preguntas de respuesta corta

9. Nombra dos de los algoritmos de búsqueda que admite Katib y, en una oración para cada uno, describe para qué problema es más adecuado.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** Cualquiera dos de: búsqueda aleatoria (una base económica para espacios de búsqueda grandes o poco comprendidos), búsqueda en cuadrícula (cobertura exhaustiva de espacios discretos pequeños y de baja dimensionalidad), optimización bayesiana (reducir el total de Trials necesarios cuando cada Trial es costoso, mediante un modelo probabilístico del objetivo), Hyperband (podar temprano las configuraciones con bajo rendimiento usando una señal temprana económica e informativa), o enfoques CMA-ES/basados en población (espacios continuos o de mayor dimensionalidad adecuados para evolucionar una población de candidatos).

**Explicación:**
Cada algoritmo establece un equilibrio diferente entre el costo de exploración y la eficiencia de búsqueda, y la elección adecuada depende de cuán costoso sea un solo Trial y de cuánta estructura tenga el espacio de búsqueda.
</details>

10. ¿Cuál es la diferencia entre lo que hace Hyperband y lo que hace la detención temprana (por ejemplo, la regla de detención por mediana), dado que ambos buscan evitar desperdiciar cómputo?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** Hyperband es una estrategia de búsqueda que decide por adelantado cuánto presupuesto de recursos dar a cada configuración; la detención temprana es una comprobación en tiempo de ejecución aplicada a un Trial ya en curso, según cómo se desempeña en relación con sus pares en ese punto del entrenamiento.

**Explicación:**
Los dos operan en niveles distintos: la poda de Hyperband es parte de la estrategia general de asignación de presupuesto del algoritmo de búsqueda, mientras que la detención temprana es una decisión por Trial que se toma mientras ese Trial se ejecuta, independientemente de qué algoritmo de búsqueda lo propuso.
</details>

## Pregunta práctica / aplicada

11. Estás configurando un Experiment en el que cada Trial solicita una GPU, y el clúster tiene un NodePool de Karpenter para instancias GPU que normalmente tarda varios minutos en aprovisionar nueva capacidad. Configuras `maxTrialCount: 60` y estás decidiendo el valor de `parallelTrialCount`. Explica, en unas pocas oraciones, el equilibrio entre establecerlo alto (por ejemplo, 20) frente a bajo (por ejemplo, 4) en este entorno.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** Un `parallelTrialCount` alto (por ejemplo, 20) completa los 60 Trials en menos rondas secuenciales, pero produce una ráfaga intensa de 20 solicitudes de GPU simultáneas, que puede superar la velocidad con la que Karpenter puede aprovisionar nodos GPU, dejando los primeros Trials pendientes en lugar de entrenar y potencialmente aumentando bruscamente la capacidad compartida del clúster si otras cargas de trabajo compiten por el mismo NodePool de GPU. Un `parallelTrialCount` bajo (por ejemplo, 4) distribuye los mismos 60 Trials en más rondas, dando a Karpenter tiempo para aprovisionar de forma incremental y reduciendo el riesgo de un pico de capacidad, a costa de que el Experiment tarde más en total en alcanzar `maxTrialCount`.

**Explicación:**
`parallelTrialCount` y `maxTrialCount` deben ajustarse juntos teniendo en cuenta el comportamiento del escalado automático del clúster, no tratarse como configuraciones independientes, especialmente cuando los Trials solicitan recursos escasos o lentos de aprovisionar, como las GPU.
</details>

---

[Volver a los materiales de aprendizaje](../../../ai-ml/kubeflow/04-katib.md)
