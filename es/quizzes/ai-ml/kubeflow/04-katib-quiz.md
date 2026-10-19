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

4. En la especificación de un Experiment, ¿qué define el campo `objective`?
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
   - B) Calcula el promedio de cada Trial exitoso usando las observaciones iniciales hasta start_step y luego obtiene la media aritmética de esos promedios
   - C) Solo permite que se ejecute exactamente la mitad de todos los Trials propuestos
   - D) Selecciona el valor mediano de hiperparámetros como respuesta final

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Calcula el promedio de cada Trial exitoso usando las observaciones iniciales hasta start_step y luego obtiene la media aritmética de esos promedios**

**Explicación:**
La guía oficial describe una regla de mediana, pero la versión 0.19.0 calcula una media aritmética. Los promedios de Trials exitosos [1, 2, 100] producen aproximadamente 34.333 en la función sin cambios, no la mediana estadística 2. Los valores predeterminados son min_trials_required=3 y start_step=4; también se aplican requisitos de recolector y marca temporal.
</details>

6. ¿Cómo obtiene normalmente Katib el valor de la métrica objetivo desde el contenedor de entrenamiento de un Trial en ejecución?
   - A) El contenedor de entrenamiento debe llamar directamente a una API de Katib desde su código
   - B) Los colectores configurados en modo de extracción recopilan métricas, o el modo Push las envía mediante report_metrics() al administrador de bases de datos
   - C) Katib pausa el contenedor e inspecciona directamente su memoria
   - D) El planificador de Kubernetes extrae automáticamente la métrica del uso de recursos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Los colectores configurados en modo de extracción recopilan métricas, o el modo Push las envía mediante report_metrics() al administrador de bases de datos**

**Explicación:**
Los colectores StdOut/File/TensorFlowEvent y Custom coexisten con el modo Push. El scraping HTTP arbitrario no es una opción predeterminada integrada. La inyección de métricas en modo de extracción requiere etiquetar el espacio de nombres y configurar el webhook y el Pod o contenedor de destino. Que un Job finalice correctamente no demuestra por sí solo que se hayan recopilado las métricas.
</details>

7. ¿Por qué un valor alto de `parallelTrialCount` genera una presión de recursos más intensa en un clúster EKS que el mismo `maxTrialCount` ejecutado con baja concurrencia?
   - A) `parallelTrialCount` no afecta cuántos Pods se crean
   - B) Un paralelismo alto significa que muchos Trials (y sus solicitudes de recursos, p. ej., GPUs) llegan al clúster al mismo tiempo en lugar de distribuirse, lo que produce un pico de demanda breve e intenso
   - C) EKS limita `parallelTrialCount` a 1 de forma predeterminada
   - D) Los Trials paralelos siempre se ejecutan en el mismo nodo, por lo que no hay demanda adicional

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Un paralelismo alto significa que muchos Trials (y sus solicitudes de recursos, p. ej., GPUs) llegan al clúster al mismo tiempo en lugar de distribuirse, lo que produce un pico de demanda breve e intenso**

**Explicación:**
Cada Trial concurrente es un trabajo de entrenamiento completo. La demanda es concurrencia × Pods por Trial × recursos por Pod, más la sobrecarga de colectores y servicios, lo que puede aumentar la demanda drásticamente incluso para un Experiment cuyo `maxTrialCount` total parece modesto.
</details>

8. En EKS, ¿cuál es una explicación probable si los Pods de Trial recién creados permanecen pending durante un tiempo justo después de que se inicia un Experiment con `parallelTrialCount` alto?
   - A) El servicio Suggestion se ha bloqueado
   - B) Es posible que esté esperando capacidad; confírmalo mediante eventos de Pod, condiciones de NodePool, cuotas, capacidad de EC2 y estado de inicialización
   - C) Katib siempre pausa los Trials nuevos durante un período fijo de calentamiento
   - D) El sidecar de recopilación de métricas está bloqueando el inicio del Pod

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Es posible que esté esperando capacidad; confírmalo mediante eventos de Pod, condiciones de NodePool, cuotas, capacidad de EC2 y estado de inicialización**

**Explicación:**
El estado Pending por sí solo no demuestra que Karpenter esté aprovisionando correctamente. La afinidad, los taints, los volúmenes, las cuotas, los límites de capacidad y los fallos de inicialización también pueden explicarlo. Revisa los eventos y el estado del controlador.
</details>

## Preguntas de respuesta corta

9. Menciona dos de los algoritmos de búsqueda que admite Katib y, en una oración para cada uno, describe para qué problema es más adecuado.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** Se aceptan dos cualesquiera de los siguientes: búsqueda aleatoria (referencia de bajo costo para espacios de búsqueda grandes o poco comprendidos), búsqueda en cuadrícula (cobertura exhaustiva de espacios discretos pequeños y de baja dimensionalidad), optimización bayesiana (reduce el total de Trials necesarios cuando cada Trial es costoso, mediante un modelo probabilístico del objetivo), Hyperband (poda temprano las configuraciones de bajo rendimiento usando una señal temprana económica e informativa), CMA-ES (evolución con adaptación de covarianza) o PBT (estrategia independiente de entrenamiento basado en población que requiere compartir puntos de control).

**Explicación:**
Cada algoritmo intercambia de manera distinta el costo de exploración por la eficiencia de búsqueda, y la elección correcta depende de cuán costoso sea un solo Trial y de cuánta estructura tenga el espacio de búsqueda.
</details>

10. ¿Cuál es la diferencia entre lo que hace Hyperband y lo que hace la detención temprana (p. ej., la regla de detención por mediana), dado que ambos buscan evitar desperdiciar capacidad de cómputo?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** Hyperband es una estrategia de búsqueda que decide de antemano cuánto presupuesto de recursos otorgar a cada configuración; la detención temprana es una comprobación en tiempo de ejecución aplicada a un Trial que ya está en curso, según su rendimiento relativo respecto de sus pares en ese punto del entrenamiento.

**Explicación:**
Ambos operan en niveles diferentes: la poda de Hyperband forma parte de la estrategia general de asignación de presupuesto del algoritmo de búsqueda, mientras que la detención temprana es una decisión por Trial tomada mientras ese Trial se ejecuta, sujeta a una configuración compatible de colectores y registros; la compatibilidad no se ofrece automáticamente para todas las combinaciones.
</details>

## Pregunta práctica / aplicada

11. Estás configurando un Experiment en el que cada Trial solicita una GPU y el clúster tiene un Karpenter NodePool para instancias GPU que normalmente tarda varios minutos en aprovisionar nueva capacidad. Estableces `maxTrialCount: 60` y estás decidiendo el valor de `parallelTrialCount`. Explica, en unas pocas oraciones, las ventajas y desventajas de establecerlo alto (p. ej., 20) o bajo (p. ej., 4) en este entorno.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** Un valor alto de `parallelTrialCount` (p. ej., 20) puede procesar Trials en menos rondas cuando hay capacidad disponible, pero genera una ráfaga intensa de 20 solicitudes de GPU simultáneas. Esta puede superar la velocidad con la que Karpenter aprovisiona nodos GPU y dejar los primeros Trials en estado Pending, sin entrenar. Si otras cargas compiten por el mismo GPU NodePool, también puede provocar picos en la demanda de capacidad compartida del clúster. Un valor bajo de `parallelTrialCount` (p. ej., 4) distribuye los mismos 60 Trials en más rondas, da a Karpenter tiempo para aprovisionar capacidad gradualmente y reduce el riesgo de un pico, aunque puede aumentar el tiempo total. El tiempo y el costo reales dependen de la capacidad, las duraciones, los fallos, la detención y la recuperación de nodos.

**Explicación:**
`parallelTrialCount` y `maxTrialCount` deben ajustarse conjuntamente teniendo en cuenta el comportamiento del escalado automático del clúster, no tratarse como configuraciones independientes, especialmente cuando los Trials solicitan recursos escasos o lentos de aprovisionar como las GPU.
</details>

---

[Volver a los materiales de aprendizaje](../../../ai-ml/kubeflow/04-katib.md)
