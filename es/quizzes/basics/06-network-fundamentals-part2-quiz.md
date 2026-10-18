# Cuestionario sobre fundamentos de redes, parte 2: transporte y TLS

> **Última actualización**: 11 de septiembre de 2026

Compruebe su comprensión de TCP, UDP, QUIC y TLS.

## Preguntas de opción múltiple

1. ¿Cómo evita QUIC que el bloqueo de cabecera de línea (HOL) de TCP afecte a los demás flujos?
   - A) Restableciendo toda la conexión cuando se pierde un paquete
   - B) Manteniendo un orden de bytes independiente para cada flujo dentro de una conexión
   - C) Renunciando por completo a las garantías de orden
   - D) Gestionando la retransmisión a nivel del kernel

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Manteniendo un orden de bytes independiente para cada flujo dentro de una conexión**

**Explicación:**
TCP no puede entregar bytes posteriores a un segmento que falta, lo que puede retrasar varios flujos HTTP/2. QUIC puede entregar independientemente los datos disponibles de otro flujo. Un flujo aún puede esperar sus propios bytes faltantes; el control de congestión de conexión/ruta, la recuperación de paquetes y las dependencias de la aplicación son aspectos compartidos.

</details>

2. ¿Qué afirmación sobre TLS 1.3 NO es correcta?
   - A) Un handshake completo normal tarda alrededor de 1 RTT; la reanudación que cumple los requisitos puede incluir datos tempranos opcionales 0-RTT
   - B) Se eliminaron el intercambio de claves RSA y las suites de cifrado débiles
   - C) TLS 1.3 por sí solo cifra SNI sin ECH
   - D) (EC)DHE efímero proporciona confidencialidad directa, pero el intercambio solo con PSK y los datos 0-RTT tienen excepciones

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) TLS 1.3 por sí solo cifra SNI sin ECH**

**Explicación:**
TLS 1.3 por sí solo no oculta SNI en ClientHello. ECH (RFC 9849) protege el ClientHello interno cuando es compatible y está configurado. TLS 1.3 permite el intercambio de claves solo con PSK, y los datos 0-RTT carecen de confidencialidad directa; por tanto, es incorrecto decir que esta confidencialidad siempre está garantizada. Además, los datos tempranos no significan que el handshake ya haya concluido.

</details>

3. ¿Qué caracteriza el enfoque de BBR para controlar la congestión?
   - A) Ignora la pérdida de paquetes y siempre envía a la velocidad máxima
   - B) Modela el ancho de banda del cuello de botella y el RTT de propagación para guiar el envío; el comportamiento ante pérdidas/ECN depende de la versión
   - C) Se ejecuta en espacio de usuario en vez de hacerlo en el kernel
   - D) Delega la retransmisión a la capa de enlace

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Modela el ancho de banda del cuello de botella y el RTT de propagación para guiar el envío; el comportamiento ante pérdidas/ECN depende de la versión**

**Explicación:**
BBR utiliza un modelo de ancho de banda/RTT en lugar de depender únicamente de una ventana de congestión guiada por pérdidas. Sigue necesitando recuperación de pérdidas y respuestas a la congestión específicas de cada versión. El rendimiento depende de la implementación, el tráfico competidor y las condiciones de la ruta; no se garantiza un caudal mayor.

</details>

4. ¿Qué regla se debe seguir al enviar solicitudes mediante la reanudación de sesiones TLS 1.3/QUIC 0-RTT?
   - A) Enviar solo solicitudes POST
   - B) Los datos 0-RTT se pueden repetir; permitir solo operaciones que la aplicación haya evaluado explícitamente como seguras frente a ataques de repetición
   - C) En 0-RTT se omite la validación de certificados; usarlo solo en redes internas
   - D) 0-RTT solo funciona sobre UDP; bloquear el uso de TCP como alternativa

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Los datos 0-RTT se pueden repetir; permitir solo operaciones que la aplicación haya evaluado explícitamente como seguras frente a ataques de repetición**

**Explicación:**
Los intercambios con datos tempranos pueden repetirse y provocar que la aplicación procese solicitudes varias veces. Que el método se llame GET o que se afirme que es idempotente no demuestra por sí solo que sea seguro frente a ataques de repetición. Limite los datos tempranos a operaciones aprobadas en el cliente, la CDN y el origen. Un servidor HTTP puede responder 425 Too Early para que la solicitud se vuelva a intentar después del handshake.

</details>

---

[Volver al material de estudio](../../basics/06-network-fundamentals-part2.md) | [Siguiente cuestionario: parte 3](./06-network-fundamentals-part3-quiz.md)
