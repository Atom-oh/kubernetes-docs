# Cuestionario sobre el despliegue de vLLM

Versión de referencia: vLLM 0.29.0. Los resultados históricos de L4 se distinguen de las comprobaciones actuales.

## Preguntas del cuestionario

### 1. ¿Qué afirmación describe correctamente vLLM?

- A. Un modelo llamado Vector Language Model
- B. Un motor de inferencia para cargas de trabajo compatibles con modelos generativos, multimodales y de otros tipos
- C. Un optimizador exclusivo de bases de datos
- D. Una herramienta de entrenamiento que mejora automáticamente la precisión de todos los modelos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Un motor de inferencia para cargas de trabajo compatibles con modelos generativos, multimodales y de otros tipos**

vLLM es un motor de inferencia, no una expansión inventada de su nombre. Las ventajas de PagedAttention y del procesamiento por lotes dependen de la carga de trabajo; no se garantiza una aceleración fija ni la ausencia de colas.
</details>

### 2. ¿Cómo deben estimarse los requisitos de memoria de GPU?

- A. Un modelo de 70B siempre cabe en 80 GB, sin importar la precisión
- B. Sume los pesos, la caché KV, las activaciones, los espacios de trabajo y la memoria para comunicación; tenga en cuenta la arquitectura, la precisión y el paralelismo
- C. Cuatro núcleos de CPU por GPU garantizan que se ejecute cualquier modelo
- D. Más RAM del host elimina la necesidad de GPU

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Sume los pesos, la caché KV, las activaciones, los espacios de trabajo y la memoria para comunicación; tenga en cuenta la arquitectura, la precisión y el paralelismo**

Solo los pesos de un modelo 70B en FP16/BF16 ocupan unos 140 GB. GQA/MQA requieren conocer la cantidad de cabezas KV; no se debe usar una fórmula para MHA basada en el tamaño oculto. Compruebe que se cumpla el requisito mínimo actual de capacidad de cómputo (compute capability) 7.5 de NVIDIA, así como los requisitos adicionales de los kernels.
</details>

### 3. ¿Qué afirmación sobre el almacenamiento es correcta?

- A. FSx for Lustre siempre es la opción óptima
- B. `snapshot_download` descarga desde S3
- C. Elija según el tiempo de carga, la concurrencia, el costo y la retención; registre la revisión y la integridad del modelo
- D. `emptyDir` siempre se elimina al reiniciar el contenedor

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Elija según el tiempo de carga, la concurrencia, el costo y la retención; registre la revisión y la integridad del modelo**

`emptyDir` puede sobrevivir al reinicio de un contenedor, pero no a la recreación del Pod. Distinga entre el aprovisionamiento estático y dinámico de FSx, los modos de acceso de EBS y la necesidad de que todos los workers usen rutas idénticas para el modelo. Las descargas de Hugging Face y las transferencias desde S3 son operaciones distintas.
</details>

### 4. ¿En qué se diferencian TP, PP y las réplicas independientes?

- A. Aumentar las réplicas de un StatefulSet reconfigura automáticamente TP
- B. TP divide el trabajo dentro de las capas, PP divide las capas en etapas y cada réplica independiente carga el modelo
- C. TP siempre reduce la latencia de una sola solicitud
- D. Todo despliegue en varios nodos utiliza `--rank`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. TP divide el trabajo dentro de las capas, PP divide las capas en etapas y cada réplica independiente carga el modelo**

El modo multiprocessing de 0.29.0 utiliza `--nnodes` y `--node-rank`, además de workers `headless`; Ray necesita un clúster real. Haga coincidir los entornos, los modelos, la red, la configuración de coordinación (`rendezvous`) y las GPU. La topología de procesos no equivale al número de réplicas de Kubernetes.
</details>

### 5. ¿Qué afirmación sobre la disponibilidad es correcta?

- A. Un PDB garantiza que se mantenga el número mínimo de réplicas durante cualquier fallo de nodo
- B. `maxUnavailable: 0` por sí solo garantiza que no haya tiempo de inactividad
- C. Valide conjuntamente las réplicas independientes, las sondas, el inicio, la capacidad de reserva, el drenado de nodos y los flujos de streaming
- D. Distribuir un grupo TP entre varias AZ siempre mejora el rendimiento

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Valide conjuntamente las réplicas independientes, las sondas, el inicio, la capacidad de reserva, el drenado de nodos y los flujos de streaming**

Un PDB limita algunas expulsiones voluntarias. La estrategia `Recreate` del ejemplo evita usar una GPU adicional, pero causa una interrupción durante las actualizaciones. `startupProbe` aplaza las sondas de actividad y disponibilidad mientras se inicializa el modelo; compruebe el tiempo real de carga.
</details>

### 6. ¿Qué afirmación sobre la planificación por lotes y la caché es correcta?

- A. Cada solicitud se ejecuta inmediatamente, sin formar colas
- B. La planificación ocurre paso a paso y pueden formarse colas cuando se alcanzan los límites de tokens, caché o capacidad
- C. La caché de prefijos siempre reutiliza respuestas completas
- D. `--swap-space` es el valor predeterminado para ampliar la memoria en 0.29.0

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. La planificación ocurre paso a paso y pueden formarse colas cuando se alcanzan los límites de tokens, caché o capacidad**

La caché de prefijos reutiliza el estado KV de prefijos compatibles. La precarga fragmentada, `max-num-seqs`, los presupuestos de tokens y los límites de contexto son parámetros distintos. `CacheConfig` establece `gpu_memory_utilization` en 0.92 de forma predeterminada; el ejemplo lo establece en 0.80. `--swap-space` no está disponible en la CLI actual.
</details>

### 7. ¿Qué debe usar la configuración actual de métricas?

- A. Un puerto 8001 independiente y `--enable-metrics=true`
- B. `/metrics` en el puerto 8000 de la API, con los nombres, etiquetas y unidades reales de las métricas con prefijo `vllm:`
- C. La ocupación de KV expresada como bytes totales de memoria de GPU
- D. Generar una alerta por cada período de inactividad como si fuera un fallo de bajo rendimiento

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. `/metrics` en el puerto 8000 de la API, con los nombres, etiquetas y unidades reales de las métricas con prefijo `vllm:`**

Algunos ejemplos son `vllm:generation_tokens_total` y `vllm:e2e_request_latency_seconds_bucket`. La ocupación de KV es una proporción en la que 1 equivale al 100 %. Distinga la agregación de modelos, los errores y cancelaciones de la puerta de enlace, TTFT y la latencia de extremo a extremo.
</details>

### 8. ¿Qué afirmación sobre las redes de varios nodos es correcta?

- A. Las claves de API cifran todas las comunicaciones internas
- B. Copiar configuraciones arbitrarias de GID/mlx5 configura EFA
- C. Valide los dispositivos y controladores compatibles, OFI NCCL/libfabric y las rutas de comunicación privadas
- D. Una prueba de NCCL en un solo nodo demuestra el rendimiento de EFA en varios nodos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Valide los dispositivos y controladores compatibles, OFI NCCL/libfabric y las rutas de comunicación privadas**

La comunicación distribuida requiere una red confiable. La autenticación de la API es distinta de la seguridad del transporte de PyTorch, Ray y KV. Las plantillas genéricas de SR-IOV/InfiniBand y las variables de NCCL inventadas no son configuraciones listas para usar en EKS.
</details>

### 9. ¿Qué afirmación sobre el escalado y el enrutamiento es correcta?

- A. Un encabezado HTTP de modelo lee automáticamente el campo del modelo en el JSON
- B. La afinidad de sesión comparte automáticamente todas las cachés KV
- C. Seleccione las réplicas, TP/PP y el enrutamiento según los cuellos de botella medidos y la topología del modelo
- D. La CPU y el almacenamiento no afectan al rendimiento si hay GPU

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Seleccione las réplicas, TP/PP y el enrutamiento según los cuellos de botella medidos y la topología del modelo**

Las cachés de prefijos, respuestas y pesos son distintas. La tokenización en CPU, la red o la carga del modelo también pueden convertirse en cuellos de botella. HPA/KEDA y NodePools son capas independientes con requisitos de métricas, administración y capacidad.
</details>

### 10. ¿Qué afirmación sobre la seguridad de las claves de API es correcta en 0.29.0?

- A. `--api-key` protege todos los endpoints del servidor
- B. Otras rutas y capacidades operativas necesitan controles en la puerta de enlace, de permisos y de red, además de la autenticación por prefijo
- C. CORS sustituye la autenticación
- D. Una sola expresión regular impide toda inyección de prompts y filtración de PII

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Otras rutas y capacidades operativas necesitan controles en la puerta de enlace, de permisos y de red, además de la autenticación por prefijo**

El middleware inspeccionado protege los prefijos `/v1`, `/v2`, `/inference` y `/cohere`; otras rutas y `OPTIONS` no pasan por esa protección. LoRA dinámico requiere habilitarse explícitamente y contar con una ruta de operador confiable. El registro de auditoría `Secret RequestResponse` y las anotaciones de Pod que supuestamente habilitan la auditoría del plano de control son ejemplos inseguros o ineficaces.
</details>

### 11. ¿Cómo debe interpretarse el resultado histórico de L4 de 5.65 s a 7.52 s?

- A. La latencia no aumentó
- B. La latencia p50 aumentó aproximadamente un 33.1 % mientras creció la tasa de procesamiento agregada en ese rango de prueba; un informe antiguo sin registros originales no demuestra el rendimiento de la versión actual
- C. Un generador de perfiles demostró que el cuello de botella era la memoria
- D. El procesamiento continuo por lotes omite la precarga

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. La latencia p50 aumentó aproximadamente un 33.1 % mientras creció la tasa de procesamiento agregada en ese rango de prueba; un informe antiguo sin registros originales no demuestra el rendimiento de la versión actual**

Los datos informados corresponden a una ejecución de 0.6.4.post1. Esta auditoría no encontró los registros originales de solicitudes y del servidor ni volvió a ejecutar la prueba. El promedio máximo de un intervalo registrado no es un pico instantáneo; un cálculo de techo de rendimiento (roofline) es una estimación, no evidencia obtenida mediante un generador de perfiles.
</details>

---

[Volver a los materiales de aprendizaje](../../ai-ml/02-vllm-deployment.md)
