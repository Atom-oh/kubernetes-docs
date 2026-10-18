# Cuestionario sobre rendimiento de red de Linux

> **Última actualización**: 15 de septiembre de 2026

Lee primero [Rendimiento de red de Linux](../../../networking/expert/04-linux-performance.md).
Elige la mejor respuesta. Explica tanto la interpretación como los límites de la medición.

1. ¿Qué afirmación relaciona correctamente los materiales públicos de Bootlin con este cuaderno?
   - A) Las diapositivas descargables garantizan un laboratorio de hardware gratuito con soporte.
   - B) La máquina virtual para principiantes reproduce necesariamente todas las observaciones de placas y controladores.
   - C) Las diapositivas y los laboratorios públicos sirven para estudiar; los ejercicios de hardware requieren la placa y la cadena de herramientas documentadas, además de conocimientos de C y del kernel.
   - D) Un certificado de formación reemplaza una captura que falta.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

**Explicación:** El acceso público a lecturas no equivale a instrucción, acceso al hardware ni matrícula. Los laboratorios de controladores requieren conocimientos de bajo nivel y una configuración adecuada. El ejercicio básico de Python con loopback tiene menos requisitos previos y no demuestra el comportamiento de una NIC física. Identifica explícitamente las pruebas de hardware no disponibles en vez de sustituirlas por un certificado.

</details>

2. El cliente espera deliberadamente 0.15 segundos después de analizar los encabezados. Aumenta la duración total de la transacción. ¿Qué conclusión está justificada?
   - A) El RTT de red aumentó exactamente 150 ms.
   - B) El retraso de consumo del cliente contribuye al tiempo de finalización; el retraso de la ruta requiere pruebas independientes.
   - C) Una qdisc necesariamente descartó paquetes.
   - D) Un búfer de recepción más grande eliminará la pausa deliberada.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** La pausa configurada forma parte de `read_ms` y `total_ms`, no es un retraso de red inyectado. La planificación y el almacenamiento en búfer afectan las mediciones reales. `headers_ms` también incluye trabajo de conexión/solicitud y no es el RTT puro. El experimento prueba una explicación alternativa relacionada con la aplicación sin afirmar una duración medida concreta.

</details>

3. ¿Qué interpretación de `ss` es adecuada?
   - A) `Recv-Q` en estado LISTEN siempre cuenta los bytes de carga útil de la aplicación aún no leídos.
   - B) `Send-Q` en estado ESTABLISHED es el máximo configurado del búfer de envío.
   - C) `Recv-Q` en estado ESTABLISHED se refiere a los datos recibidos que aún no se leen; la memoria del socket y la cola pendiente de LISTEN son cantidades distintas.
   - D) `skmem`, la ventana de recepción anunciada y `cwnd` deben tener todos el mismo valor numérico.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

**Explicación:** El estado del socket cambia el significado de las columnas. `Send-Q` en estado ESTABLISHED se refiere a los bytes no confirmados, incluidos los que aún no se han enviado, mientras que las columnas de LISTEN se refieren a la aceptación de conexiones. La contabilidad de memoria incluye gastos generales y difiere de la ocupación del flujo. Para compararla con `cwnd`, también hay que comprobar sus unidades en segmentos y el MSS.

</details>

4. Una ruta hipotética transporta 100 Mbit/s con un RTT de 40 ms. ¿Cuál es su BDP y qué demuestra?
   - A) 4,000,000 bytes, lo que demuestra que todos los búferes de socket deben tener ese valor.
   - B) 500,000 bytes, un dato de referencia para razonar que no demuestra la causa de una ejecución lenta.
   - C) 500 bytes, una capacidad medida de loopback.
   - D) 2,500,000 bytes, una longitud obligatoria de cola qdisc.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** Convierte el RTT a 0.040 segundos y los bits a bytes: `100,000,000 × 0.040 ÷ 8 = 500,000`. Es un cálculo hipotético. El rendimiento depende de las ventanas efectivas, los datos proporcionados por la aplicación, la congestión y otras restricciones; el cálculo por sí solo no diagnostica el cuello de botella ni autoriza un ajuste global.

</details>

5. Una captura del host muestra una unidad TCP grande y errores aparentes de suma de comprobación saliente. ¿Qué debes hacer primero?
   - A) Deshabilitar todas las descargas de trabajo de la NIC y repetir con carga ilimitada.
   - B) Declarar que la red física transmitió tramas corruptas de tamaño excesivo.
   - C) Registrar el punto de captura, la dirección, el contexto de descarga de trabajo y los contadores de truncamiento/captura.
   - D) Eliminar la captura porque no puede contener pruebas útiles.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

**Explicación:** GSO/TSO/GRO y la descarga de comprobación pueden cambiar lo que ve un observador del host con respecto a la transmisión física. Esto tampoco demuestra que la red funcione correctamente. Identifica el punto de observación y busca pruebas correspondientes en el endpoint o en el cable cuando sea necesario. El cuaderno no cambia las descargas de trabajo de la NIC para normalizar lo observado.

</details>

6. ¿Qué combinación es correcta?
   - A) NAPI garantiza que todas las aplicaciones cumplan un objetivo de latencia.
   - B) RSS siempre distribuye un único flujo TCP entre todas las CPU.
   - C) RSS dirige las colas de recepción mediante hardware, RPS dirige el trabajo a las CPU mediante software y NAPI gestiona el sondeo de eventos del controlador.
   - D) Loopback puede evaluar directamente la tabla de distribución RSS de la NIC física.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

**Explicación:** Estos mecanismos operan en lugares relacionados, pero distintos. Un flujo puede asignarse mediante hash a una cola RSS; la distribución del procesamiento por software entre CPU puede ser diferente. Los presupuestos y el contexto de procesamiento de NAPI no garantizan el tiempo de finalización de una aplicación. Loopback no atraviesa las colas de recepción de una NIC física.

</details>

7. tcpdump informa descartes de captura y una muestra de `ss` muestra retransmisiones. ¿Qué se puede concluir?
   - A) Cada retransmisión fue causada por la pérdida de un paquete en tcpdump.
   - B) Se demostró que la qdisc es el lugar donde se pierden los paquetes.
   - C) Los descartes del observador y las retransmisiones TCP son señales distintas que requieren correlación temporal y por flujo, además de pruebas adicionales.
   - D) El endpoint remoto necesariamente agotó su búfer de recepción.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

**Explicación:** Los descartes de captura describen el límite de entrega o procesamiento del observador, no directamente la entrega de paquetes en la ruta. TCP puede retransmitir tras pérdidas, reordenación o un timeout espurio. Ninguno de los dos contadores identifica por sí solo un componente defectuoso. Compara el mismo intervalo y la misma tupla, y usa ambos endpoints cuando la hipótesis lo requiera.

</details>

8. `bpftool net show` informa de una asociación. ¿Qué pruebas adicionales se necesitan para afirmar que aceleró tu flujo?
   - A) Ninguna; una asociación implica aceleración.
   - B) Correlación del flujo y del hook, una comparación definida, mediciones reales de rendimiento y contabilidad de la sobrecarga del observador.
   - C) Solo el nombre del programa BPF.
   - D) Una comprobación de permisos fallida en otro host.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** Un inventario no demuestra ejecución ni rendimiento. XDP nativo, XDP genérico y TC operan en lugares distintos. Una comparación válida requiere una carga de trabajo y un contrato de medición definidos; también importan las pérdidas de trazas y la sobrecarga. Si faltan permisos, el resultado es «no observado», no «no hay BPF». El cuaderno básico no carga programas.

</details>

9. Cinco solicitudes de una fase se completan correctamente, pero la mayoría de las muestras periódicas de `ss` están vacías. ¿Qué informe es correcto?
   - A) Un p99 de producción demostrado y una afirmación de que no había sockets.
   - B) La cantidad real de muestras y los valores mínimo, mediano y máximo, indicando las brechas de muestreo de conexiones breves.
   - C) Latencia cero para cada muestra de socket faltante.
   - D) Rendimiento máximo de la NIC calculado únicamente a partir del cuerpo eco de mayor tamaño.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** Las conexiones breves pueden ocurrir entre intervalos de observación. Cinco muestras de transacción solo permiten un informe descriptivo pequeño, no un objetivo creíble de latencia de cola del servicio. Los datos ausentes no equivalen a cero. La carga útil dividida por el tiempo de transacción es el rendimiento útil de la operación, incluidos el trabajo de la aplicación y de conexión, no la velocidad de línea de la NIC.

</details>

10. ¿Qué plan de restauración cumple los requisitos del cuaderno?
   - A) Reemplazar la qdisc raíz del host, eliminarla después y suponer que vuelve la jerarquía anterior.
   - B) Vaciar todas las rutas y terminar todos los procesos Python.
   - C) Detener solo los procesos loopback propios y verificar la eliminación del listener; mantener el diseño netem en el plano teórico hasta definir por separado la propiedad, el estado previo y la restauración exacta.
   - D) Deshabilitar los controles de seguridad compartidos si falta una observación.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

**Explicación:** La ejecución básica no cambia la configuración de red global. Su limpieza se limita a sus propios procesos y archivos; es normal que permanezca TIME_WAIT. Eliminar una qdisc no reconstruye una configuración previa arbitraria. Un futuro experimento netem requiere un límite propio de espacio de nombres o máquina virtual, una restauración exacta o la eliminación exclusiva de los recursos registrados.

</details>

Vuelve a los [criterios de finalización del cuaderno](../../../networking/expert/04-linux-performance.md#completion) o al [mapa del curso avanzado](../../../networking/expert/README.md).
