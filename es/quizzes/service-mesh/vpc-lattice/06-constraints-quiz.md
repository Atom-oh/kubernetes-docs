# Cuestionario sobre restricciones y puntos de decisión

Este cuestionario evalúa tu comprensión de las seis restricciones de migración, el orden de las decisiones y la estructura de facturación.

## Preguntas de opción múltiple

1. ¿Qué afirmación distingue correctamente los modelos de identidad TLS y conectividad TCP?
   - A) El impacto en la aplicación de la firma SigV4 y la excepción de iptables de Envoy
   - B) Separar la identidad HTTP autenticada de la política TLS anónima, y los listeners de servicio de la conectividad de recursos TCP
   - C) Los cargos por salto y la dependencia de STS
   - D) La concentración de dominios de error y los límites de cuota

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Separar la identidad HTTP autenticada de la política TLS anónima, y los listeners de servicio de la conectividad de recursos TCP**

**Explicación:**
Estas son decisiones actuales sobre API y límites de confianza. No demuestran que todas las políticas de autenticación TLS sean imposibles ni que todo el producto Lattice carezca de acceso a recursos TCP.
</details>

2. ¿Qué decisión debe tomarse primero en el diseño de la migración?
   - A) Si se debe firmar con una biblioteca compartida o un proxy de salida
   - B) Si la normativa exige cifrado de extremo a extremo o autenticación mutua de cargas de trabajo; esto determina la elección entre un listener HTTPS + IAM Auth y TLS Passthrough, y condiciona la mayoría de las decisiones de diseño posteriores
   - C) La cantidad de servicios Lattice y el costo estimado
   - D) La configuración de la lista de prefijos del Security Group del nodo

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Si la normativa exige cifrado de extremo a extremo o autenticación mutua de cargas de trabajo; esto determina la elección entre un listener HTTPS + IAM Auth y TLS Passthrough, y condiciona la mayoría de las decisiones de diseño posteriores**

**Explicación:**
Esta decisión depende de los requisitos de seguridad de la organización. TLS Passthrough impide que Lattice autentique a los llamantes SigV4 o inspeccione campos HTTP para el enrutamiento L7; sus políticas de autenticación se limitan a principales anónimos. Por tanto, la identidad y autorización autenticadas de cargas de trabajo requieren un diseño de endpoint o aplicación, que puede incluir mTLS y SPIRE. En cambio, un listener HTTPS conduce a la decisión sobre el método de firma. Acuerda estos límites con los revisores de seguridad antes de elegir el diseño.
</details>

3. ¿Cómo debe estimarse el costo de Lattice?
   - A) Una cadena profunda aumenta el cargo por aprovisionar el servicio
   - B) Contar las llamadas reales al servicio, incluida la profundidad de la cadena, la dispersión a varios destinos y los reintentos, junto con el volumen de datos y las horas aprovisionadas
   - C) La profundidad de la cadena determina el cargo entre zonas de disponibilidad
   - D) Una cadena profunda alcanza las cuotas antes

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Contar las llamadas reales al servicio, incluida la profundidad de la cadena, la dispersión a varios destinos y los reintentos, junto con el volumen de datos y las horas aprovisionadas**

**Explicación:**
Una cadena simple de cuatro llamadas genera cuatro solicitudes solo bajo ese supuesto. Los cargos por hora, los bytes transferidos, los reintentos y el modelo de acceso también afectan el costo; aquí no se mide ningún ahorro.
</details>

4. ¿Cómo deben conservarse las pruebas de las cadenas de llamadas?
   - A) Porque las aplicaciones cambian después de la migración y las cadenas son distintas
   - B) Conservar las trazas de la aplicación durante la migración y correlacionarlas con los registros de Lattice y los ID de solicitud
   - C) Porque CloudWatch no proporciona una métrica de profundidad de cadena
   - D) Porque ya no hace falta estimar el costo después de la migración

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Conservar las trazas de la aplicación durante la migración y correlacionarlas con los registros de Lattice y los ID de solicitud**

**Explicación:**
Lattice no tiene spans nativos; eso no elimina los spans de la aplicación ni imposibilita analizar las cadenas de llamadas después de la migración.
</details>

5. ¿Qué configuración se recomienda para un entorno con tráfico TCP sin cifrar?
   - A) Introducir TLS en todas partes y trasladarlo todo a Lattice
   - B) Evaluar por separado los listeners HTTP/TLS del servicio, la conectividad de recursos TCP y las alternativas privadas existentes
   - C) Eliminar todos los servicios TCP sin cifrar
   - D) Habilitar el listener TCP sin procesar de Lattice

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Evaluar por separado los listeners HTTP/TLS del servicio, la conectividad de recursos TCP y las alternativas privadas existentes**

**Explicación:**
Las configuraciones de recursos admiten TCP sin heredar el enrutamiento ni la autenticación L7 del servicio. Asocia cada protocolo con el modelo correcto y verifica la compatibilidad de la API y el controlador.
</details>

6. ¿Qué sacrificio implica mantener fuera de Lattice la comunicación dentro del clúster?
   - A) Ninguno; siempre es ventajoso
   - B) Reduce el costo y la latencia, pero las llamadas DNS directas a servicios de Kubernetes no se evalúan con las políticas de autenticación, así que la autorización del tráfico interno debe diseñarse por separado mediante NetworkPolicy o en la capa de aplicación
   - C) Se conserva la autorización, pero se pierde la observabilidad
   - D) El controlador de Gateway API deja de funcionar

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Reduce el costo y la latencia, pero las llamadas DNS directas a servicios de Kubernetes no se evalúan con las políticas de autenticación, así que la autorización del tráfico interno debe diseñarse por separado mediante NetworkPolicy o en la capa de aplicación**

**Explicación:**
La ventaja de Lattice está en la comunicación que cruza límites entre clústeres, VPC y cuentas; dentro de un mismo clúster aporta poco y añade costo y latencia, por lo que suele ser razonable dirigir a través de Lattice solo el tráfico que cruza esos límites. Sin embargo, `IAMAuthPolicy` autoriza únicamente el tráfico que pasa por Gateways/HTTPRoutes/GRPCRoutes, así que sacar el tráfico interno de Lattice elimina la autorización de ese segmento. Aquí entran en conflicto la optimización de costos y la coherencia de autorización.
</details>

7. ¿Cómo deben compararse los dominios de error?
   - A) Lattice es administrado, así que no hay fallos
   - B) Ambas rutas tienen dependencias locales y compartidas; evalúa los servicios, las zonas de disponibilidad, las políticas y los controles de recuperación afectados
   - C) El alcance del fallo es idéntico en ambos modelos
   - D) El modelo de sidecar tiene el mayor alcance de fallo

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Ambas rutas tienen dependencias locales y compartidas; evalúa los servicios, las zonas de disponibilidad, las políticas y los controles de recuperación afectados**

**Explicación:**
Un fallo del proxy puede ser local, pero un fallo en la configuración compartida del mesh puede tener un alcance amplio. Un fallo de Lattice no afecta automáticamente a todo el tráfico East-West, y siguen existiendo tareas de corrección para las políticas, los destinos y el controlador del cliente.
</details>

8. ¿Cuál de las siguientes opciones aparece marcada como `Needs verification` porque no se pudo confirmar en la documentación oficial?
   - A) Que el nombre del servicio SigV4 es `vpc-lattice-svcs`
   - B) Si API Gateway admite de forma nativa una red de servicios Lattice como destino de integración privada
   - C) Que el fin del soporte de App Mesh es el 30 de septiembre de 2026
   - D) Que hay tres protocolos de listener: HTTP/HTTPS/TLS_PASSTHROUGH

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Si API Gateway admite de forma nativa una red de servicios Lattice como destino de integración privada**

**Explicación:**
No se encontró evidencia de que API Gateway acepte de forma nativa una red de servicios Lattice como destino de integración privada. La compatibilidad con un listener ALB/NLB detrás de un VPC Link no demuestra que exista una ruta directa de enlace local ALB/NLB → Lattice. Antes de afirmar que un puente está admitido, valida el tipo exacto de API, el destino y la conectividad compatibles, y un proxy o consumidor implementado explícitamente con el comportamiento requerido de firma y gestión de fallos. Comprueba las cuotas actuales de la cuenta y la región, y mide la ubicación de los destinos del backend; la afinidad de zona de disponibilidad de la entrada DNS no garantiza que el backend esté en la misma zona. Los límites de las políticas TLS para principales anónimos, los límites de asociación del controlador y la exclusión ECH/ESNI del listener TLS están documentados por separado y no deben describirse como totalmente sin confirmar.
</details>
