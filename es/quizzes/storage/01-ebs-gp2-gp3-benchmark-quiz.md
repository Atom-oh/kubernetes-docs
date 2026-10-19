# Cuestionario sobre los resultados medidos de EBS gp2 y gp3

1. ¿Cómo eran los IOPS medidos de un volumen gp2 de 100 GiB bajo lecturas aleatorias 4k sostenidas (qd32)?
   - A) Se mantuvieron suavemente alrededor de 300 IOPS desde el inicio
   - B) Igualaron a gp3 con 3,001 IOPS durante unos 33 minutos (1,999 s), y luego cayeron a 300 IOPS en un segundo
   - C) Comenzaron en 3,000 IOPS y descendieron gradualmente a 300 durante 45 minutos
   - D) Se mantuvieron en 3,000 IOPS durante los 45 minutos completos
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Igualaron a gp3 con 3,001 IOPS durante unos 33 minutos (1,999 s), y luego cayeron a 300 IOPS en un segundo**

**Explicación:**
El registro de IOPS por segundo de fio mostró 3,001 a los 1,998 s, 2,659 a los 1,999 s y 300 a los 2,000 s. Mientras queden créditos, gp2 es indistinguible de gp3; en el momento en que se agotan, el 90 % de la capacidad desaparece como si se accionara un interruptor. La afirmación correcta no es «gp2 es lento», sino «gp2 se vuelve lento de repente».

</details>

2. ¿Por qué la duración de burst de un volumen gp2 de 100 GiB se calcula en aproximadamente 2,000 segundos?
   - A) 5,400,000 créditos ÷ (3,000 − 300) IOPS = 2,000 s
   - B) 100 GiB × 20 s/GiB = 2,000 s
   - C) 3,000 IOPS ÷ 1.5 = 2,000 s
   - D) AWS lo fija en 2,000 s independientemente del tamaño del volumen
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) 5,400,000 créditos ÷ (3,000 − 300) IOPS = 2,000 s**

**Explicación:**
gp2 tiene una línea base de 3 IOPS/GiB (100 GiB → 300 IOPS) y un depósito de 5.4M créditos. El burst a 3,000 IOPS consume 2,700 créditos por segundo después de restar los 300 que la línea base repone, por lo que 5,400,000 ÷ 2,700 = 2,000 s. Los volúmenes más grandes tienen líneas base mayores y se agotan más lentamente; a partir de 1,000 GiB, la línea base ya es de 3,000, por lo que no hay un desplome.

</details>

3. Después de agotar los créditos, la latencia promedio de gp2 con qd32 midió aproximadamente 106 ms. ¿Qué interpretación es correcta?
   - A) El tiempo de respuesta del dispositivo EBS se volvió superior a 100 ms
   - B) Según la ley de Little, 32 I/O pendientes ÷ 300 IOPS ≈ 106.7 ms; es una aproximación al tiempo de respuesta, incluida la espera en cola y el servicio
   - C) La latencia de red tuvo un pico
   - D) Es un error de medición de fio
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Según la ley de Little, 32 I/O pendientes ÷ 300 IOPS ≈ 106.7 ms; es una aproximación al tiempo de respuesta, incluida la espera en cola y el servicio**

**Explicación:**
La latencia promedio = I/O pendientes ÷ throughput. Mantener 32 I/O en vuelo mientras solo se completan 300 por segundo da una respuesta promedio de 106.7 ms. Los 10.4 ms a 3,000 IOPS corresponden a la misma aritmética (32 ÷ 3,000 = 10.7 ms). Este cálculo aproxima el tiempo de respuesta e incluye la espera en cola y el servicio, pero no los separa. Incluso qd1 incluye la latencia del kernel, la virtualización y el servicio de EBS.

</details>

4. ¿Por qué una prueba de escritura aleatoria de 120 segundos en gp2, ejecutada justo después de agotar los créditos, midió 601 IOPS en lugar de 300?
   - A) Las escrituras no consumen créditos
   - B) Durante los 120 s previos de reposo, gp2 acumuló 300 créditos/s × 120 s = 36,000 créditos, lo que añadió 300 IOPS durante la prueba de 120 segundos
   - C) fio cuenta los IOPS de escritura dos veces
   - D) La línea base de escritura de gp2 es el doble de su línea base de lectura
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Durante los 120 s previos de reposo, gp2 acumuló 300 créditos/s × 120 s = 36,000 créditos, lo que añadió 300 IOPS durante la prueba de 120 segundos**

**Explicación:**
El depósito de créditos de gp2 no queda vacío para siempre una vez agotado; es una cuenta bancaria que se repone a 3 créditos/GiB/s (100 GiB → 300/s) siempre que el volumen está en reposo. Gastar 36,000 créditos durante 120 s añade 300 IOPS a la línea base de 300, para exactamente 600 (medido: 601). Los 603 IOPS en la prueba qd1 siguen la misma aritmética con 18,000 créditos acumulados durante un reposo de 60 segundos. Por eso gp2 bajo tráfico intermitente es «rápido algunos días, lento otros días».

</details>

5. En la prueba de lectura aleatoria 4k qd1, gp2 limitado mostró p50 de 0.602 ms y p95 de 3.391 ms. ¿Qué indica esta distribución?
   - A) El dispositivo gp2 es fundamentalmente más lento que gp3
   - B) Una mediana similar y una cola más lenta son compatibles con la limitación, pero no demuestran que los dispositivos físicos sean idénticos
   - C) Otro Pod compartió el volumen durante la prueba
   - D) Las lecturas aleatorias siempre muestran una distribución bimodal
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Una mediana similar y una cola más lenta son compatibles con la limitación, pero no demuestran que los dispositivos físicos sean idénticos**

**Explicación:**
La mitad de los I/O de gp2 terminó en 0.6 ms, exactamente como gp3. La otra mitad llegó a 3.4–3.6 ms porque los I/O que excedieron la asignación por segundo (unos 603 IOPS) se mantuvieron en la cola de limitación. El promedio por sí solo es de 1.65 ms — «un poco más lento» — mientras que p95 aumentó 6 veces. Por eso los dashboards de almacenamiento necesitan p50 junto con p95/p99.

</details>

6. ¿Por qué tanto gp2 como gp3 se detuvieron en 125–130 MiB/s en la prueba de lectura/escritura secuencial de 1 MiB?
   - A) gp3 alcanzó su línea base de 125 MiB/s y gp2 (≤170 GiB) alcanzó su límite de 128 MiB/s; ambos valores resultan ser cercanos
   - B) El límite de ancho de banda de red de la instancia m5.xlarge
   - C) El `iodepth=8` de fio fue el cuello de botella
   - D) Los créditos de gp2 se agotaron y ralentizaron ambos volúmenes
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) gp3 alcanzó su línea base de 125 MiB/s y gp2 (≤170 GiB) alcanzó su límite de 128 MiB/s; ambos valores resultan ser cercanos**

**Explicación:**
El throughput predeterminado de gp3 es 125 MiB/s; gp2 tiene un límite de 128 MiB/s para volúmenes de 170 GiB o menos. El depósito de créditos vacío de gp2 no ralentizó la prueba secuencial porque EBS cuenta una I/O de 1 MiB como cuatro operaciones de 256 KiB, por lo que 130 MiB/s son solo unos 520 IOPS, muy por debajo de los 36,000 créditos acumulados durante el reposo previo. El límite de throughput se activó antes que el límite de IOPS. Ten en cuenta que el ancho de banda EBS de la instancia m5.xlarge (≈137 MiB/s) es ligeramente mayor y no fue el cuello de botella en esta prueba; sin embargo, durante un burst de la instancia, gp3 a 250 MiB/s puede superar ese nivel. Para planificar el rendimiento sostenido, también hay que tener en cuenta la línea base de aproximadamente 137 MiB/s.

</details>

7. Para un conjunto de datos de 100 GiB que necesita 3,000 IOPS sostenidos, ¿qué comparación de costos, según las tarifas de Seúl de septiembre de 2026, es correcta?
   - A) gp2 de 100 GiB ($11.40) es suficiente
   - B) gp3 de 100 GiB ($9.12) proporciona 3,000 IOPS sin depender de créditos de ráfaga, mientras que obtener la misma línea base en gp2 requiere 1,000 GiB ($114.00) — aproximadamente una diferencia de 12 veces
   - C) gp3 requiere IOPS adicionales de pago, por lo que cuesta más que gp2
   - D) Ambos volúmenes cuestan lo mismo al mes
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) gp3 de 100 GiB ($9.12) proporciona 3,000 IOPS sin depender de créditos de ráfaga, mientras que obtener la misma línea base en gp2 requiere 1,000 GiB ($114.00) — aproximadamente una diferencia de 12 veces**

**Explicación:**
gp2 de 100 GiB a $11.40 garantiza solo 300 IOPS sostenidos (la ráfaga de 3,000 IOPS dura como máximo 33 minutos). En la época de gp2, la práctica habitual era aumentar el volumen a 1,000 GiB para obtener IOPS, por $114.00. gp3 desacopla los IOPS de la capacidad y proporciona los mismos 3,000 IOPS a $9.12 para 100 GiB. Si es necesario, se pueden adquirir por separado 6,000 IOPS (+$17.10) o 250 MiB/s (+$5.70).

</details>

8. ¿Cuál es la forma nativa de Kubernetes de convertir un PVC gp2 existente con datos a gp3 sin reiniciar el Pod?
   - A) Editar el parámetro `type` de StorageClass a gp3 y los PV existentes cambian automáticamente
   - B) Crear una `VolumeAttributesClass` (storage.k8s.io/v1, GA en Kubernetes 1.34) y establecer `volumeAttributesClassName` del PVC; el EBS CSI driver llama a ModifyVolume
   - C) Eliminar el PVC y volver a crearlo con la StorageClass gp3
   - D) Ejecutar `aws ec2 modify-volume` en el nodo es la única opción
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Crear una `VolumeAttributesClass` (storage.k8s.io/v1, GA en Kubernetes 1.34) y establecer `volumeAttributesClassName` del PVC; el EBS CSI driver llama a ModifyVolume**

**Explicación:**
Los parámetros de StorageClass se aplican solo al crear volúmenes nuevos; no afectan los PV existentes. `VolumeAttributesClass` permite cambiar `type`, `iops` y `throughput` mientras el Pod se ejecuta, mediante EBS Elastic Volumes. Consideraciones: cada modificación debe alcanzar el estado `completed` antes de iniciar la siguiente en el mismo volumen (hasta seis horas para un volumen de 1 TiB); EBS permite como máximo cuatro modificaciones por volumen en un período móvil de 24 horas, así que agrupa los cambios de tipo, IOPS y throughput en una sola solicitud. Además, Kubernetes 1.31–1.33 requiere la API v1beta1 y un feature gate. Incluso el uso de VAC no cambia automáticamente `storageClassName`. Comprueba tanto el estado de modificación del PVC como las propiedades reales de EBS.

</details>
