# Cuestionario sobre el análisis del impacto en la latencia

Este cuestionario evalúa tu comprensión de los factores que empeoran o mejoran la latencia durante una migración a Lattice y de cómo diseñar una medición de prueba de concepto.

## Preguntas de opción múltiple

1. ¿Por qué no se puede afirmar de antemano que el impacto de una migración a Lattice «añade N milisegundos»?
   - A) AWS no publica cifras de latencia
   - B) Cambian a la vez el trabajo del proxy, las rutas de red, la reutilización de TLS y la autenticación; por eso hay que medir la carga de trabajo real
   - C) Lattice aún no tiene disponibilidad general
   - D) La latencia depende únicamente de la región

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Cambian a la vez el trabajo del proxy, las rutas de red, la reutilización de TLS y la autenticación; por eso hay que medir la carga de trabajo real**

**Explicación:**
Aquí no se proporcionan mediciones de latencia de Lattice. La dirección y la magnitud dependen de la configuración probada; no presentes estimaciones en microsegundos ni mejoras garantizadas como resultados observados.
</details>

2. ¿Qué significa que los factores que afectan p50 y p99 no sean los mismos?
   - A) p99 siempre es peor que p50, por lo que basta con observar p50
   - B) La mediana y la cola pueden reaccionar de forma distinta a la contención, los inicios en frío y el enrutamiento; por eso hay que medir ambas
   - C) Los mismos factores afectan a p50 y p99, así que basta con medir uno
   - D) p99 es ruido y se debe ignorar

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) La mediana y la cola pueden reaccionar de forma distinta a la contención, los inicios en frío y el enrutamiento; por eso hay que medir ambas**

**Explicación:**
Las respuestas distintas de cada percentil son hipótesis que hay que investigar, no una garantía de que p50 empeore mientras p99 mejora. Incluye errores, rendimiento y condiciones de la carga de trabajo junto con las distribuciones.
</details>

3. ¿Qué ajuste del cliente se indicó que podría importar más que añadir un salto de proxy?
   - A) TTL de la caché DNS
   - B) Ajustes de keepalive y del pool de conexiones
   - C) Nivel de registro
   - D) Valor del tiempo de espera de la solicitud

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Ajustes de keepalive y del pool de conexiones**

**Explicación:**
La prueba comparativa citada muestra que la reutilización de conexiones importó en esa carga de trabajo. Las conexiones TCP nuevas requieren establecer la conexión; si se usa TLS, también se realizan los handshakes correspondientes. Esto no es una medición de latencia de Lattice.
</details>

4. En la matriz de medición de la prueba de concepto, ¿qué indica la diferencia entre `IAM Auth on` e `IAM Auth off`?
   - A) El costo de atravesar AZ
   - B) El efecto combinado de la firma, la gestión de credenciales y la evaluación de las políticas habilitadas, bajo condiciones equivalentes
   - C) El efecto de eliminar la contención de CPU de Envoy
   - D) El efecto aislado del cambio de ruta

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) El efecto combinado de la firma, la gestión de credenciales y la evaluación de las políticas habilitadas, bajo condiciones equivalentes**

**Explicación:**
Activar o desactivar la autenticación no aísla únicamente HMAC. Repite las pruebas en condiciones equivalentes, mantén constantes la carga y los ajustes de conexión, e informa sobre la actualización de credenciales, los fallos y el rendimiento.
</details>

5. ¿Qué afirmación sobre el tráfico entre AZ es correcta?
   - A) Es un factor que empeora la latencia y supone un cargo adicional independiente
   - B) Es un factor que empeora la latencia, pero el tráfico a través de Lattice no tiene un cargo inter-AZ independiente; se incluye en el cargo de procesamiento de datos
   - C) No afecta a la latencia ni a la facturación
   - D) Lattice siempre selecciona un Target en la AZ del emisor, así que no hace falta tenerlo en cuenta

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Es un factor que empeora la latencia, pero el tráfico a través de Lattice no tiene un cargo inter-AZ independiente; se incluye en el cargo de procesamiento de datos**

**Explicación:**
La distancia física aumenta la latencia entre AZ (valores de referencia medidos: 0.339 ms en la misma AZ frente a 0.544 ms entre AZ). Sin embargo, en la facturación Lattice no aplica un cargo inter-AZ independiente: se incluye en el procesamiento de datos. D es incorrecta: la documentación oficial no confirma si la selección de Target de Lattice tiene en cuenta la AZ del emisor, y hay que medirlo en una prueba de concepto. Precisamente por eso la matriz incluye un eje para AZ.
</details>

6. ¿Por qué se necesita una fase de calentamiento en el diseño de la medición y por qué se debe registrar aparte la latencia de la primera solicitud?
   - A) El calentamiento no es necesario; basta con medir la primera solicitud
   - B) Las credenciales o los pools de conexiones en frío pueden añadir trabajo de inicialización; registra por separado la latencia de la primera solicitud y la latencia después del calentamiento, y evalúa ambas si los inicios en frío son frecuentes
   - C) El calentamiento solo mejora p50 y no afecta a p99
   - D) La primera solicitud siempre falla

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Las credenciales o los pools de conexiones en frío pueden añadir trabajo de inicialización; registra por separado la latencia de la primera solicitud y la latencia después del calentamiento, y evalúa ambas si los inicios en frío son frecuentes**

**Explicación:**
La primera solicitud puede incluir la adquisición de credenciales y el establecimiento de la conexión cuando las cachés o los pools están fríos. La ruta de adquisición depende del proveedor: IRSA usa STS, mientras que EKS Pod Identity usa el agente del nodo y EKS Auth. El trabajo del handshake TLS solo se aplica a conexiones TLS. Registra por separado la latencia de la primera solicitud y la latencia después del calentamiento, junto con el estado del proveedor, la caché y el transporte; no supongas que todas las primeras solicitudes hacen una llamada directa a STS o establecen TLS. Evalúa ambas condiciones cuando los inicios en frío sean frecuentes.
</details>
