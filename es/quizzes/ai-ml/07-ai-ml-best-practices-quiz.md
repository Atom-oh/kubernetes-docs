# Cuestionario de mejores prácticas de AI/ML

15 preguntas sobre medición, recuperación y API actuales.

## 1. ¿Qué mide TTFT y cuándo no está disponible?

<details>
<summary>Respuesta y explicación</summary>

Tiempo desde que se envía la solicitud hasta la primera salida no vacía. La primera trama HTTP y el primer token pueden llegar en momentos distintos; una respuesta sin streaming no permite medir el TTFT ni el ITL reales. Especifica el tokenizador y cómo tratar los fallos y el período de calentamiento.
</details>

## 2. ¿La combinación de optimizaciones de inicio siempre mejora entre un 80 y un 95 %?

<details>
<summary>Respuesta y explicación</summary>

No. Mide por separado la descarga y descompresión de la imagen, la descarga y carga del modelo, el tiempo hasta que esté listo y la preparación del nodo. Evalúa el coste de la precarga y la carga diferida, las cachés y la lectura de todos los pesos; no supongas un ahorro fijo.
</details>

## 3. ¿Cómo se deben seleccionar las GPU para entrenamiento distribuido a gran escala?

<details>
<summary>Respuesta y explicación</summary>

Comprueba los dispositivos y la memoria del tamaño exacto de la instancia, la CPU, la RAM y la red, el estado y las activaciones del modelo, la comunicación, los precios y las cuotas. El nombre de una familia no determina la cantidad de GPU ni demuestra que sea la mejor opción en todos los casos.
</details>

## 4. ¿EFA y los grupos de ubicación siempre son obligatorios?

<details>
<summary>Respuesta y explicación</summary>

EFA ofrece una ruta de alto rendimiento para las cargas de trabajo adecuadas, pero no es un requisito para todo entrenamiento DDP. La comunicación de EFA requiere que las instancias estén en la misma AZ; se recomiendan los grupos de ubicación de clúster para mejorar el rendimiento. Verifica los controladores, los complementos, los grupos de seguridad y las interfaces.
</details>

## 5. ¿Un conjunto de datos de más de 10 TB siempre requiere FSx?

<details>
<summary>Respuesta y explicación</summary>

El tamaño por sí solo no determina la elección. Compara la entrada/salida, la concurrencia, los metadatos, la latencia, la durabilidad, el comportamiento del montaje y el coste. Distingue EFS, FSx, S3 y el almacenamiento local de instancia (instance store), y comprueba los límites actuales de gp3.
</details>

## 6. ¿La temperatura por sí sola permite confirmar una limitación de rendimiento o un fallo de hardware?

<details>
<summary>Respuesta y explicación</summary>

No. Comprueba los límites específicos del dispositivo, las frecuencias de reloj, el consumo de energía, los motivos de limitación y la carga de trabajo. `DCGMFB_USED` se mide en MiB y `XID_ERRORS` es un indicador de tipo gauge del último código; no todos los errores XID indican un fallo de hardware.
</details>

## 7. ¿Son suficientes 120 segundos de gracia y una llamada a `/drain` para la inferencia Spot?

<details>
<summary>Respuesta y explicación</summary>

EC2 no siempre garantiza 120 segundos, y no se puede dar por sentada una API `/drain` genérica de vLLM. Prueba la preparación del gateway, el manejo de `SIGTERM`, las respuestas en streaming, los reintentos, los duplicados y la recarga de cachés.
</details>

## 8. ¿Cómo se calcula el ITL medio?

<details>
<summary>Respuesta y explicación</summary>

Usa las marcas de tiempo de los tokens reales y requiere al menos dos tokens: `(último - primero) / (número de tokens - 1)`. Ten en cuenta los bloques que contienen varios tokens y las salidas vacías o de un solo token; distingue la definición de TPOT específica de cada herramienta.
</details>

## 9. ¿Qué demuestra una prueba de saturación?

<details>
<summary>Respuesta y explicación</summary>

Cómo cambian con la carga el caudal de solicitudes, la latencia, los errores y el rendimiento útil (goodput). Por sí sola no demuestra que haya un cuello de botella de CPU, GPU o memoria. Distingue la tasa de llegada de la concurrencia e inspecciona los clientes, el perfilado y las colas.
</details>

## 10. ¿Qué entrada usa SOCI 0.15 standalone?

<details>
<summary>Respuesta y explicación</summary>

Un directorio o archivo local con el formato OCI image-layout, no un archivo tar genérico de `docker save`. `convert --standalone` no necesita containerd; los beneficios reales del inicio diferido requieren validar el runtime, el registro y la carga de trabajo.
</details>

## 11. ¿Cómo se configura un presupuesto de horario laboral de 09–17 UTC?

<details>
<summary>Respuesta y explicación</summary>

Usa `0 9 * * 1-5` con una duración de 8 h. `0 9-17 * * 1-5` inicia cada hora y se extiende hasta la 01:00 del día siguiente. Los presupuestos limitan las interrupciones voluntarias, no la recuperación de instancias Spot, los fallos ni el vencimiento forzado.
</details>

## 12. ¿La actualización de ESO emite automáticamente credenciales, recarga aplicaciones y audita cada lectura?

<details>
<summary>Respuesta y explicación</summary>

No. Distingue la rotación del proveedor, la sincronización del Secret y las relecturas que hace la aplicación. Los valores de `subPath` y las variables de entorno no se actualizan automáticamente; CloudTrail no registra cada lectura local. ESO 2.10 expone `v1`, no `v1beta1`.
</details>

## 13. ¿Cómo se debe estimar la memoria GPU para un modelo 30B FP16?

<details>
<summary>Respuesta y explicación</summary>

Solo los pesos ocupan unos 60 GB; añade la memoria de KV, las activaciones, el espacio de trabajo y la comunicación. Cuatro GPU de 24 GB suman 96 GB, pero hay que comprobar el particionado (sharding), la memoria máxima y el caudal. Un modelo 13B FP16 supera los 24 GB; uno 70B FP16 supera los 96 GB.
</details>

## 14. ¿Una alta ocupación actual de la caché KV de vLLM siempre rechaza solicitudes?

<details>
<summary>Respuesta y explicación</summary>

Usa `vllm:kv_cache_usage_perc`. Interpreta la ocupación junto con las colas, la preempción y el estado de la memoria; no se garantiza el rechazo inmediato de solicitudes. Evita la métrica obsoleta `gpu_cache_usage_perc` y los nombres de tasa de aciertos que no se hayan verificado.
</details>

## 15. ¿Se configura un placement group de Karpenter mediante una etiqueta?

<details>
<summary>Respuesta y explicación</summary>

La versión 1.14.1 usa `EC2NodeClass.spec.placementGroupSelector` con `name` o `id`. La etiqueta `aws:ec2:placement-group` no es la API para configurar el grupo de ubicación. Verifica la AZ, la capacidad y la red, y evalúa el riesgo de recuperación ante un fallo de una sola AZ.
</details>

[Volver a la guía](../../ai-ml/07-ai-ml-best-practices.md)
