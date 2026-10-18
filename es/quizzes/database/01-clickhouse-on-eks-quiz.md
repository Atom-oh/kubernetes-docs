# Cuestionario sobre la prueba comparativa medida de ClickHouse en EKS

1. En la prueba, el recuento del rango de una hora `namespace + timestamp` (Q1) finalizó en 4 ms frente a una tabla de 100 millones de filas. ¿Cuál es la razón principal?
   - A) El resultado ya estaba guardado en la caché de consultas
   - B) El filtrado mediante PARTITION BY (day) y ORDER BY (namespace, timestamp) hizo que solo se leyeran 16,385 de las 100 millones de filas
   - C) Las 3,000 IOPS del volumen gp3 fueron suficientes
   - D) El tipo LowCardinality vectorizó las comparaciones

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El filtrado mediante PARTITION BY (day) y ORDER BY (namespace, timestamp) hizo que solo se leyeran 16,385 de las 100 millones de filas**

**Explicación:**
Cuando las condiciones de consulta coinciden con la clave de partición (diaria) y la clave de ordenamiento (namespace, timestamp), ClickHouse filtra a nivel de granularidad mediante el índice primario. En esta prueba, la consulta contó 59,916 filas, pero solo leyó 16,385 (0.016%): las granularidades que quedan totalmente dentro del rango de la clave primaria se cuentan desde el índice (una optimización de ClickHouse 24.6+), y solo se descomprimen las granularidades parciales en los extremos del rango. Gran parte de la velocidad de ClickHouse proviene de este diseño de «no leer esos datos».

</details>

2. En los resultados de compresión por columna, trace_id se comprimió 1.0× (incompresible), mientras que namespace se comprimió unas 201×. ¿A qué se debe la diferencia?
   - A) Solo a la columna trace_id le faltaba un códec de compresión
   - B) Las cadenas namespace son más cortas
   - C) trace_id tenía pocos patrones repetidos y apenas se comprimió con LZ4 en esta ejecución, mientras que namespace tiene baja cardinalidad y es la primera clave ORDER BY, por lo que los valores idénticos aparecen en largas secuencias
   - D) Solo namespace obtiene un archivo de diccionario independiente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) trace_id tenía pocos patrones repetidos y apenas se comprimió con LZ4 en esta ejecución, mientras que namespace tiene baja cardinalidad y es la primera clave ORDER BY, por lo que los valores idénticos aparecen en largas secuencias**

**Explicación:**
Este resultado con LZ4 fue de unos 3.07 GiB sin comprimir → 3.08 GiB comprimidos. Hex almacena solo cuatro bits de información por byte, así que otros códecs o representaciones binarias aún podrían reducirlo. namespace solo tiene 10 valores distintos y es la primera clave de ordenamiento, por lo que los valores idénticos se almacenan en secuencias contiguas: 95.72 MiB se redujeron a 488.63 KiB (201×). Por eso, «cómo almacenamos los ID» es la palanca de mayor impacto en el costo de almacenamiento de un esquema de registros.

</details>

3. ¿Qué afirmación coincide con la comparación medida entre LZ4 (predeterminado) y ZSTD(3)?
   - A) ZSTD(3) ganó tanto en almacenamiento como en velocidad de análisis
   - B) El almacenamiento con ZSTD(3) fue 47% menor, pero el análisis completo limitado por CPU fue unas 1.9× más lento que con LZ4
   - C) La diferencia de almacenamiento entre los códecs fue inferior al 5%
   - D) LZ4 ocupó menos espacio en disco, pero fue más lento al analizar

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El almacenamiento con ZSTD(3) fue 47% menor, pero el análisis completo limitado por CPU fue unas 1.9× más lento que con LZ4**

**Explicación:**
Medición: LZ4 ocupó 7.82 GiB (1.97×) frente a 4.16 GiB con ZSTD(3) (3.7×), es decir, 47% menos almacenamiento; al mismo tiempo, el análisis completo en caliente de `LIKE '%timeout%'` pasó de 2.63 s a 4.9 s. Usar LZ4 en las particiones recientes y aplicar recompresión ZSTD mediante TTL es una opción que se debe validar con los datos reales y el equilibrio entre CPU y E/S.

</details>

4. El análisis completo de `LIKE '%timeout%'` (Q3) tardó 31.5 s al omitir la caché de páginas. ¿A qué cuello de botella apunta este valor?
   - A) El algoritmo de búsqueda de cadenas de ClickHouse no es eficiente
   - B) Leer la columna comprimida message (~4 GiB) ÷ 31.5 s ≈ 130 MiB/s, coherente con una restricción de rendimiento del volumen/instancia EBS, pero insuficiente para identificar el único cuello de botella
   - C) Las 4 vCPU de m5.xlarge estuvieron saturadas
   - D) La sobrecarga del controlador CSI de EBS fue dominante

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Leer la columna comprimida message (~4 GiB) ÷ 31.5 s ≈ 130 MiB/s, coherente con una restricción de rendimiento del volumen/instancia EBS, pero insuficiente para identificar el único cuello de botella**

**Explicación:**
La misma consulta servida desde la caché de páginas terminó en 2.63 s (limitada por CPU, unos 38 millones de filas/s). La ralentización de 12× en las lecturas directas desde disco es una prueba medida de que el rendimiento del análisis completo puede depender de la configuración de rendimiento del volumen, en lugar de una propiedad de la base de datos; el rendimiento de gp3 se puede aprovisionar hasta 2,000 MiB/s con un costo adicional (para alcanzarlo también se necesitan al menos 8,000 IOPS), pero en esta m5.xlarge también hay que comprobar la línea base de aproximadamente 137 MiB/s de la instancia y su estado de ráfaga. Evalúa conjuntamente la capacidad del nodo y del volumen para una demanda sostenida.

</details>

5. Según las mediciones, ¿qué cambió al agregar un índice de omisión bloom filter para la búsqueda puntual de trace_id (Q5)?
   - A) Tiempo de búsqueda de 1.13 s → 0.036 s (31×), filas leídas de 100 millones → 1.08 millones (98.9% omitidas), tamaño del índice de aproximadamente 1.5% de la tabla
   - B) El tiempo de búsqueda no cambió; solo disminuyó el uso de memoria
   - C) El tiempo de búsqueda se redujo a la mitad y el índice ocupó el 30% del tamaño de la tabla
   - D) El efecto fue igual al de cambiar la clave ORDER BY y también se redujo el almacenamiento

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Tiempo de búsqueda de 1.13 s → 0.036 s (31×), filas leídas de 100 millones → 1.08 millones (98.9% omitidas), tamaño del índice de aproximadamente 1.5% de la tabla**

**Explicación:**
El índice de omisión `bloom_filter(0.01) GRANULARITY 4` no produce falsos negativos para pertenencia: un resultado negativo permite omitir el grupo, mientras que un resultado positivo puede ser un falso positivo que requiera lecturas adicionales. La cantidad de datos leídos bajó de 3.82 GiB a 42.6 MiB; el índice en sí ocupa 119.7 MiB (1.5% de la tabla) y MATERIALIZE tardó unos 20 segundos.

</details>

6. ¿Qué salvedad debe acompañar la cifra de ingesta (~940 mil filas/s) de la prueba?
   - A) Se midió con tres réplicas
   - B) Se midió mediante INSERT…SELECT dentro del servidor, por lo que no mide directamente el rendimiento de ingesta de un cliente externo que envía datos por la red y requiere análisis
   - C) Solo escribió en memoria; nunca en disco
   - D) La compresión estaba deshabilitada durante la medición

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Se midió mediante INSERT…SELECT dentro del servidor, por lo que no mide directamente el rendimiento de ingesta de un cliente externo que envía datos por la red y requiere análisis**

**Explicación:**
Las filas se generaron dentro del servidor y se insertaron directamente, lo que es más favorable que un cliente externo que envía datos TSV/Native. Se incluyen el ordenamiento, la compresión y las escrituras en disco, pero también el costo de CPU de generar los datos, así que la cifra no es un límite máximo matemático para la ingesta externa. Mide por separado el cliente, el procesamiento por lotes, la concurrencia y el formato previstos.

</details>

7. Q4 (p50/p99 de duración por namespace) analiza las 100 millones de filas, pero termina en cerca de 1 segundo con caché caliente. ¿Qué propiedad lo permite?
   - A) El resultado estaba precalculado en una vista materializada
   - B) El almacenamiento orientado a columnas: solo lee duration_ms (289 MiB) y namespace (0.5 MiB), no los 7.8 GiB completos de la tabla
   - C) La función quantile solo lee 8,192 filas del disco y nunca procesa el resto
   - D) El filtrado de particiones lo limitó a un día de datos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El almacenamiento orientado a columnas: solo lee duration_ms (289 MiB) y namespace (0.5 MiB), no los 7.8 GiB completos de la tabla**

**Explicación:**
Una base de datos orientada a filas tendría que leer filas completas para esta consulta; un motor columnar lee únicamente las columnas que necesita la agregación. El análisis cubrió todo el intervalo de tiempo (así que no hubo filtrado de particiones; D es incorrecta), y `quantile` procesa todas las filas de entrada, aunque usa una muestra de como máximo 8,192 elementos para calcular una aproximación. El muestreo no elimina el análisis de las columnas de entrada. Evalúa quantileExact por separado cuando se requieran valores exactos.

</details>

8. Según el marco de decisión de esta guía, ¿cuándo es especialmente defendible ejecutar ClickHouse autogestionado en EKS en lugar de usar un servicio administrado?
   - A) Cuando no hay equipo de plataforma ni experiencia en operaciones de bases de datos
   - B) Cuando basta con un servicio administrado estándar y hay un solo inquilino
   - C) Cuando las ofertas administradas son limitadas o tienen un costo mucho mayor, y un equipo de plataforma puede encargarse de las operaciones basadas en operadores, incluidos los ensayos de copia de seguridad y restauración
   - D) Cuando los datos son pequeños (menos de 100 GiB)

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Cuando las ofertas administradas son limitadas o tienen un costo mucho mayor, y un equipo de plataforma puede encargarse de las operaciones basadas en operadores, incluidos los ensayos de copia de seguridad y restauración**

**Explicación:**
Este marco entre servicios administrados y autogestionados proviene del [resumen de la sección Database](../../database/README.md), no del artículo de la prueba comparativa. ClickHouse usa Apache-2.0 y cuenta con un operador comunitario consolidado (Altinity), lo que hace viable la autogestión; el requisito previo es disponer tanto del operador como de un equipo que lo ejecute. En cambio, si escasea el personal de operaciones o existe una opción administrada adecuada, conviene elegir el servicio administrado. Un equipo que opere un StatefulSet sin operador debe implementar por su cuenta las mismas responsabilidades de ciclo de vida y recuperación.

</details>
