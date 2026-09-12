# Cuestionario de mejores prácticas de AI/ML

15 preguntas sobre medición, recuperación y APIs actuales.

## 1. ¿Qué mide TTFT y cuándo no está disponible?

<details>
<summary>Respuesta y explicación</summary>

Tiempo desde la solicitud hasta la primera salida no vacía. El primer frame HTTP y el token pueden diferir; una respuesta sin streaming no puede medir TTFT/ITL real. Especifique el tokenizer, los fallos y los límites de warmup.
</details>

## 2. ¿La combinación de optimizaciones de inicio siempre mejora entre un 80 y un 95 %?

<details>
<summary>Respuesta y explicación</summary>

No. Mida por separado la obtención/desempaquetado de la imagen, la descarga/carga del modelo, la preparación para la disponibilidad y la preparación del nodo. Evalúe los costos de prefetch/lazy-loading, las cachés y las lecturas de todos los pesos en lugar de ahorros fijos.
</details>

## 3. ¿Cómo se deben seleccionar las GPUs para entrenamiento distribuido grande?

<details>
<summary>Respuesta y explicación</summary>

Compruebe los dispositivos/memoria del tamaño exacto de la instancia, CPU/RAM/red, el estado/las activaciones del modelo, la comunicación, los precios y las cuotas. El nombre de una familia no fija los recuentos de GPU ni demuestra una elección universalmente mejor.
</details>

## 4. ¿EFA y los placement groups siempre son obligatorios?

<details>
<summary>Respuesta y explicación</summary>

EFA es una ruta de alto rendimiento para cargas de trabajo adecuadas, no un requisito previo para cada DDP. La comunicación de EFA requiere la misma AZ; los cluster placement groups se recomiendan para el rendimiento. Verifique drivers/plugins/security groups/interfaces.
</details>

## 5. ¿Un dataset de más de 10 TB siempre requiere FSx?

<details>
<summary>Respuesta y explicación</summary>

Ningún umbral de tamaño único decide esto. Compare I/O, concurrencia, metadatos, latencia, durabilidad, semántica de montaje y costo. Distinga EFS/FSx/S3/instance store y los límites actuales de gp3.
</details>

## 6. ¿La temperatura por sí sola puede establecer throttling o fallo de hardware?

<details>
<summary>Respuesta y explicación</summary>

No. Compruebe los límites específicos del dispositivo, los clocks, la energía, los motivos de throttling y la carga de trabajo. DCGMFB_USED se mide en MiB y XID_ERRORS es un gauge del último código; no todos los XID indican un fallo de hardware.
</details>

## 7. ¿Son suficientes 120 segundos de gracia y una llamada a/drain para la inferencia Spot?

<details>
<summary>Respuesta y explicación</summary>

EC2 no siempre garantiza 120 segundos y no se puede asumir una API arbitraria de vLLM/drain. Pruebe la disponibilidad del gateway, SIGTERM, streams, reintentos, duplicados y recargas de caché.
</details>

## 8. ¿Cómo se calcula el ITL medio?

<details>
<summary>Respuesta y explicación</summary>

Con timestamps de tokens reales y al menos dos tokens:(último-primero)/(tokens-1). Tenga en cuenta los chunks de varios tokens y las salidas vacías/de un solo token; distinga la definición de TPOT específica de la herramienta.
</details>

## 9. ¿Qué demuestra una prueba de saturación?

<details>
<summary>Respuesta y explicación</summary>

Cómo cambian el throughput, la latencia, los errores y el goodput con la carga. Por sí sola no demuestra un cuello de botella de CPU/GPU/memoria. Distinga la tasa de llegada de la concurrencia e inspeccione los clientes, el profiling y las colas.
</details>

## 10. ¿Qué entrada usa SOCI 0.15 standalone?

<details>
<summary>Respuesta y explicación</summary>

Un directorio/archivo local de OCI image-layout, no un tar genérico de docker-save. convert --standalone no necesita containerd; los beneficios reales del inicio diferido requieren validación de runtime/registry/carga de trabajo.
</details>

## 11. ¿Cómo se configura un presupuesto de horario laboral de 09–17 UTC?

<details>
<summary>Respuesta y explicación</summary>

Use 0 9 * * 1-5 con una duración de 8 h.0 9-17 * * 1-5 inicia cada hora y se extiende hasta01:00del día siguiente. Los presupuestos limitan la interrupción voluntaria, no la recuperación de Spot, los fallos ni la expiración forzada.
</details>

## 12. ¿La actualización de ESO emite automáticamente credenciales, recarga aplicaciones y audita cada lectura?

<details>
<summary>Respuesta y explicación</summary>

No. Distinga la rotación del proveedor, la sincronización de Secret y las relecturas de la aplicación. Los valores de subPath/env no se actualizan automáticamente; CloudTrail no registra cada lectura local. ESO 2.10 sirve v1, no v1beta1.
</details>

## 13. ¿Cómo se debe estimar la memoria GPU para un modelo 30B FP16?

<details>
<summary>Respuesta y explicación</summary>

Solo los pesos ocupan unos 60 GB; agregue KV, activaciones, workspace y comunicación. Cuatro GPUs de 24 GB suman 96 GB, pero requieren comprobaciones de sharding/memoria pico/throughput. 13B FP16 supera 24 GB; 70B FP16 supera 96 GB.
</details>

## 14. ¿Una alta ocupación actual de la caché KV de vLLM siempre rechaza solicitudes?

<details>
<summary>Respuesta y explicación</summary>

Use vllm:kv_cache_usage_perc. Interprete la ocupación junto con las colas, la preemption y el estado de memoria; el rechazo inmediato no está garantizado. Evite el obsoleto gpu_cache_usage_perc y nombres de tasa de aciertos no verificados.
</details>

## 15. ¿Se configura un placement group de Karpenter mediante una etiqueta?

<details>
<summary>Respuesta y explicación</summary>

La versión 1.14.1 usa EC2NodeClass.spec.placementGroupSelector name/id. Una etiqueta aws:ec2:placement-group no es la API de placement. Verifique AZ, capacidad y red, y evalúe el riesgo de recuperación de una sola AZ.
</details>

[Volver a la guía](../../ai-ml/07-ai-ml-best-practices.md)
