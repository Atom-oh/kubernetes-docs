# Cuestionario de revisión del benchmark de Kafka, parte 9

Distinga las mediciones reportadas, las afirmaciones causales y las comprobaciones para reproducir los resultados.

## 1. ¿Cuál es el modelo de almacenamiento de tres brokers con RF3 y cómo debe interpretarse el valor de 134,74 MiB/s de F1?

<details>
<summary>Mostrar respuesta</summary>

Cada broker almacena una copia de cada partición. Las tasas del registro codificado y de la carga útil del cliente son distintas; F1 es un informe breve del cliente obtenido en una sola ejecución. Antes de afirmar que existe un límite sostenido validado de 130–135 MiB/s, reconcilie la caché, la escritura diferida, las ventanas y las unidades.

</details>

## 2. ¿Unos IOPS bajos y unas tasas altas de bytes demuestran que el throughput del volumen es el único cuello de botella?

<details>
<summary>Mostrar respuesta</summary>

No. Son compatibles con presión de throughput por E/S secuencial, pero también importan la base y la ráfaga de EBS de la instancia, la caché, los clientes y la incertidumbre del muestreo. No equipare una muestra máxima de 135 con un valor aprovisionado de 125 MiB/s. Compruebe la hipótesis con cambios controlados.

</details>

## 3. Si B1/B2 tienen p50 de 3 ms y p99 de 126/17 ms, ¿se puede concluir que acks solo afecta la cola de latencia?

<details>
<summary>Mostrar respuesta</summary>

No. La proporción de p99 es aproximadamente 7,412, pero las medias también difieren: 5,27/2,58 ms. Que las medianas muestreadas coincidan en milisegundos enteros no demuestra que las latencias subyacentes sean iguales, y un par de mediciones no es universal. La devolución de llamada con acks=0 no es una confirmación de durabilidad del broker.

</details>

## 4. ¿Por qué la proporción 337,81/134,74=2,507 de F4/F1 no es una medición pura del costo de replicación?

<details>
<summary>Mostrar respuesta</summary>

Cambian tanto RF como acks: de RF3/acks=all a RF1/acks=1. Además, difieren los valores predeterminados de idempotencia que no se especificaron. También cambian la duración, los datos por broker, la caché y las limitaciones del cliente. Conserve la proporción observada sin presentarla como un efecto aislado de RF.

</details>

## 5. ¿Cómo debe describirse F6 si cambian el tamaño del lote, linger y la cantidad de registros?

<details>
<summary>Mostrar respuesta</summary>

148,38 MiB/s supera 134,74 en un 10,12 %, con un intervalo de CPU reportado más bajo. La diferencia del 39,19 % entre los puntos medios de CPU es un cálculo aritmético, no un efecto atribuible solo al tamaño del lote. Sin mediciones repetidas de la variabilidad, no se puede clasificar la diferencia de throughput como ruido.

</details>

## 6. ¿Se pueden aplicar sin cambios a otros registros las proporciones de compresión y el orden de los códecs del JSON rellenado?

<details>
<summary>Mostrar respuesta</summary>

No. El relleno con el carácter x en aproximadamente el 63,2 % hace que la distribución sea inusual; ni las proporciones ni el orden son límites o clasificaciones universales. Regenerar el AWK con otra implementación puede cambiar los hashes y la compresión. Conserve la carga útil, la imagen y las versiones originales de las herramientas.

</details>

## 7. ¿Qué factores de confusión importan para la ralentización de E4 y los contadores de red de EC2?

<details>
<summary>Mostrar respuesta</summary>

El throughput del productor cae un 44,49 %, de 103,36 a 57,37 MiB/s, pero el productor comparte un cliente/NIC de 1,9 CPU con el consumidor. Un uso bajo de CPU en los brokers no descarta la contención del cliente. Los créditos de recepción y transmisión de red de EC2 son independientes: F1 tiene recepción de 136 MiB/s≈1,141 Gbps y transmisión de 108≈0,906 Gbps; cada una está por debajo de 1,25 Gbps. No las sume para afirmar que se usó la ráfaga.

</details>

## 8. ¿Cómo debe validar una nueva reproducción las unidades, el estado estable y la entrega satisfactoria?

<details>
<summary>Mostrar respuesta</summary>

30 M×1024 B son 28,610 GiB; no existe un umbral universal de estado estable de diez GiB o un minuto. Registre el calentamiento, las ventanas largas, el vaciado, las repeticiones, los denominadores comunes y el dispositivo/las marcas de tiempo reales. Compruebe las opciones actuales, los temas nuevos y poblados, el recuento final satisfactorio del productor y su stderr, y el contenido consumido. Es posible que los fallos de devolución de llamada no se reflejen solo en el código de salida; una estimación de costos no es una factura.

</details>

---

[Volver al material de aprendizaje](../../../data-on-eks/kafka/09-kafka-benchmark.md) | [Inicio del análisis detallado de Kafka](../../../data-on-eks/kafka/README.md)
