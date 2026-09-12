# Cuestionario de despliegue de vLLM

Base: vLLM 0.29.0. Los resultados históricos de L4 se distinguen de la validación actual.

## Preguntas del cuestionario

### 1. ¿Qué afirmación describe correctamente vLLM?

- A. Un modelo llamado Vector Language Model
- B. Un motor de inferencia para cargas de trabajo de modelos generativos/multimodales compatibles y otros modelos
- C. Un optimizador exclusivo de bases de datos
- D. Una herramienta de entrenamiento que mejora automáticamente la precisión de todos los modelos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Un motor de inferencia para cargas de trabajo de modelos generativos/multimodales compatibles y otros modelos**

vLLM es un motor, no esa expansión inventada. Los beneficios de PagedAttention y batching dependen de las cargas de trabajo; no se garantiza una aceleración fija ni una ejecución sin cola.
</details>

### 2. ¿Cómo deben estimarse los requisitos de memoria de GPU?

- A. 70B siempre cabe en 80GB independientemente de la precisión
- B. Sume weights, KV cache, activations/workspaces y comunicación, considerando la arquitectura, la precisión y el paralelismo
- C. Cuatro núcleos de CPU por GPU garantizan que todos los modelos se ejecuten
- D. Más RAM del host elimina los requisitos de GPU

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Sume weights, KV cache, activations/workspaces y comunicación, considerando la arquitectura, la precisión y el paralelismo**

Solo los weights de 70B FP16/BF16 ocupan unos 140GB. GQA/MQA requieren recuentos de KV-heads, no una fórmula de hidden-size de MHA. Compruebe el mínimo actual de NVIDIA capability 7.5 y los requisitos adicionales de kernel.
</details>

### 3. ¿Qué afirmación sobre almacenamiento es correcta?

- A. FSx for Lustre siempre es óptimo
- B. snapshot_download descarga desde S3
- C. Elija según el tiempo de carga, la concurrencia, el costo y la retención; registre la revisión e integridad del modelo
- D. emptyDir siempre se elimina al reiniciar el contenedor

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Elija según el tiempo de carga, la concurrencia, el costo y la retención; registre la revisión e integridad del modelo**

emptyDir puede sobrevivir al reinicio del contenedor, pero no a la recreación del Pod. Distinga el aprovisionamiento estático/dinámico de FSx, los modos de acceso de EBS y las rutas de modelo idénticas de los workers. Las descargas de Hugging Face y las transferencias de S3 son independientes.
</details>

### 4. ¿En qué se diferencian TP, PP y las réplicas independientes?

- A. Aumentar las réplicas de StatefulSet reconfigura automáticamente TP
- B. TP particiona dentro de las capas, PP particiona las etapas de las capas y las réplicas independientes cargan cada una el modelo
- C. TP siempre reduce la latencia de una sola solicitud
- D. Todo despliegue multi-node utiliza --rank

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. TP particiona dentro de las capas, PP particiona las etapas de las capas y las réplicas independientes cargan cada una el modelo**

El multiprocessing de 0.29.0 utiliza --nnodes/--node-rank y workers headless; Ray necesita un clúster real. Haga coincidir los entornos, modelos, red/rendezvous y GPUs. La topología de procesos no es el recuento de réplicas de Kubernetes.
</details>

### 5. ¿Qué afirmación sobre disponibilidad es correcta?

- A. PDB garantiza réplicas mínimas ante cada fallo de nodo
- B. maxUnavailable0 por sí solo garantiza que no haya tiempo de inactividad
- C. Valide conjuntamente las réplicas independientes, probes, el inicio, la capacidad de reserva, el draining y los streams
- D. Distribuir un grupo TP entre AZs siempre mejora el rendimiento

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Valide conjuntamente las réplicas independientes, probes, el inicio, la capacidad de reserva, el draining y los streams**

PDB restringe algunas expulsiones voluntarias. La estrategia Recreate de ejemplo evita una GPU adicional, pero provoca tiempo de inactividad durante las actualizaciones. startupProbe controla readiness/liveness durante la inicialización; verifique el tiempo de carga real.
</details>

### 6. ¿Qué afirmación sobre batching/cache es correcta?

- A. Cada solicitud se ejecuta inmediatamente sin cola
- B. La programación ocurre paso a paso y pueden formarse colas bajo límites de token/cache/capacidad
- C. El prefix caching siempre reutiliza respuestas completas
- D. --swap-space es el valor predeterminado de expansión de memoria en 0.29

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. La programación ocurre paso a paso y pueden formarse colas bajo límites de token/cache/capacidad**

El prefix caching reutiliza el estado de prefix KV compatible. Chunked prefill, max-num-seqs, los presupuestos de token y los límites de contexto son distintos. CacheConfig establece gpu_memory_utilization en 0.92 de forma predeterminada; el ejemplo establece 0.80. --swap-space no está presente en la CLI actual.
</details>

### 7. ¿Qué debe usar la configuración actual de métricas?

- A. Un puerto 8001 independiente y --enable-metrics=true
- B. /metrics en el puerto de API 8000 con nombres, labels y unidades reales de vllm:
- C. La ocupación de KV como bytes totales de memoria de GPU
- D. Alertar sobre cada período de inactividad como un fallo de bajo throughput

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. /metrics en el puerto de API 8000 con nombres, labels y unidades reales de vllm:**

Los ejemplos incluyen vllm:generation_tokens_total y vllm:e2e_request_latency_seconds_bucket. La ocupación de KV es una proporción donde 1 significa 100%. Distinga la agregación de modelos, los errores/cancelaciones del gateway, TTFT y la latencia de extremo a extremo.
</details>

### 8. ¿Qué afirmación sobre redes multi-node es correcta?

- A. Las API keys cifran todo el transporte interno
- B. La configuración arbitraria copiada de GID/mlx5 configura EFA
- C. Valide los dispositivos/drivers compatibles, OFI NCCL/libfabric y las rutas de comunicación privadas
- D. Una prueba de NCCL en un único nodo demuestra el rendimiento de EFA en multi-node

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Valide los dispositivos/drivers compatibles, OFI NCCL/libfabric y las rutas de comunicación privadas**

La comunicación distribuida necesita una red confiable. La autenticación de API difiere de la seguridad del transporte de PyTorch/Ray/KV. Las plantillas genéricas de SR-IOV/InfiniBand y las variables de NCCL inventadas no son configuración lista para usar de EKS.
</details>

### 9. ¿Qué afirmación sobre escalado/enrutamiento es correcta?

- A. Un header de modelo HTTP lee automáticamente el campo JSON del modelo
- B. La afinidad de sesión comparte automáticamente todos los KV caches
- C. Seleccione réplicas, TP/PP y enrutamiento según los cuellos de botella medidos y la topología del modelo
- D. CPU y almacenamiento nunca afectan al rendimiento cuando existen GPUs

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Seleccione réplicas, TP/PP y enrutamiento según los cuellos de botella medidos y la topología del modelo**

Los caches de prefix, response y weight son distintos. La tokenización de CPU, las redes o la carga pueden convertirse en cuellos de botella. HPA/KEDA y NodePools son capas independientes con requisitos de métricas, propiedad y capacidad.
</details>

### 10. ¿Qué afirmación sobre API-key/security es correcta en 0.29.0?

- A. --api-key protege cada endpoint del servidor
- B. Otras rutas y capacidades operativas necesitan límites de gateway, permisos y red más allá de la autenticación por prefijo
- C. CORS sustituye la autenticación
- D. Una sola regex evita toda inyección de prompts y filtración de PII

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Otras rutas y capacidades operativas necesitan límites de gateway, permisos y red más allá de la autenticación por prefijo**

El middleware inspeccionado protege los prefijos /v1,/v2,/inference,/cohere; otras rutas y OPTIONS lo omiten. LoRA dinámico necesita opt-in explícito y una ruta de operador confiable. La auditoría Secret RequestResponse y las anotaciones de Pod que pretenden habilitar la auditoría del control plane son ejemplos inseguros/ineficaces.
</details>

### 11. ¿Cómo debe interpretarse el resultado histórico de L4 5.65s→7.52s?

- A. La latencia no aumentó
- B. p50 aumentó aproximadamente un 33.1% mientras el throughput agregado creció en ese rango de prueba; un informe antiguo sin logs sin procesar no es evidencia de la versión actual
- C. Un profiler demostró el cuello de botella de memoria
- D. El continuous batching omite el prefill

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. p50 aumentó aproximadamente un 33.1% mientras el throughput agregado creció en ese rango de prueba; un informe antiguo sin logs sin procesar no es evidencia de la versión actual**

Los datos informados corresponden a una ejecución de 0.6.4.post1. Esta auditoría no localizó logs sin procesar de solicitud/servidor ni la volvió a ejecutar. Un promedio máximo de intervalo registrado no es un pico instantáneo; un cálculo roofline es una estimación, no evidencia de profiler.
</details>

---

[Volver a los materiales de aprendizaje](../../ai-ml/02-vllm-deployment.md)
