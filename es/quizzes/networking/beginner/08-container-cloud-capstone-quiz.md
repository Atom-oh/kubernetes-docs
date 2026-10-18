# Cuestionario final sobre contenedores y nube

[Lección](../../../networking/beginner/08-container-cloud-capstone.md)

Seis preguntas. Explique cada respuesta con sus propias palabras.

1. Una solicitud a una IP devuelve HTTP 200, pero getent no puede resolver el nombre del servicio. ¿Qué se debe investigar primero?

   - A) Los algoritmos de control de congestión de CPU
   - B) La ruta de resolución de nombres
   - C) Solo los permisos de archivos HTTP
   - D) Todas las implementaciones de CNI

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) La ruta de resolución de nombres**

**Explicación:** Se establecieron la conectividad IP y una respuesta de la aplicación, así que investigue cómo se resuelve el nombre. Hace falta más evidencia para identificar un servidor DNS en particular como causa.

</details>

2. El servidor devuelve HTTP 404. ¿Qué ha demostrado esta solicitud?

   - A) Todos los puertos están abiertos
   - B) La tabla de enrutamiento está vacía
   - C) Se intercambió una respuesta HTTP con el servidor
   - D) Toda Internet está en buen estado

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Se intercambió una respuesta HTTP con el servidor**

**Explicación:** 404 es una respuesta de la capa HTTP. Compare las rutas y los registros del servidor; esta evidencia no justifica restablecer todo el firewall.

</details>

3. ss muestra solo un listener en 127.0.0.1:8000 y funciona una solicitud local al servidor. ¿Qué es fundamental al investigar un fallo remoto?

   - A) Comprobar si el listener está vinculado a la dirección de destino de la solicitud remota
   - B) Suponer que localhost del cliente y localhost del servidor son lo mismo
   - C) Aumentar siempre el TTL de DNS
   - D) Desactivar SELinux

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Comprobar si el listener está vinculado a la dirección de destino de la solicitud remota**

**Explicación:** Loopback pertenece a su namespace de red. Para recibir tráfico en la IP de laboratorio del servidor se necesita un listener vinculado correctamente y reglas de acceso adecuadas.

</details>

4. Solo se eliminó la regla independiente de UFW que permitía TCP 8000. La nueva conexión SSH solo con clave sigue funcionando, pero HTTP falla. ¿Qué recuperación conserva la política prevista?

   - A) Añadir una regla que permita HTTP detrás de la regla deny de laboratorio restante
   - B) Eliminar la regla deny de laboratorio y todas las reglas SSH
   - C) Desactivar UFW y suponer que una sesión SSH antigua demuestra la recuperación
   - D) Insertar la regla HTTP allow original y restringida antes de la regla deny; después verificar el orden, HTTP 200 y una conexión SSH nueva solo con clave

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Insertar la regla HTTP allow original y restringida antes de la regla deny; después verificar el orden, HTTP 200 y una conexión SSH nueva solo con clave**

**Explicación:** SSH y HTTP tienen reglas allow independientes, así que el fallo HTTP debe dejar intactos TCP 22 y las políticas predeterminadas. La ubicación en UFW importa: una regla allow añadida detrás de una regla deny coincidente no surte efecto. Pruebe un inicio de sesión nuevo, sin multiplexación y solo con clave antes, durante y después del fallo; permita que se solicite la frase de contraseña de la clave cifrada en lugar de asumir que el agente está desbloqueado. En la variante de firewalld, solo se elimina/restaura HTTP en runtime y su regla permanente permanece presente. Si HTTP nunca falla tras eliminar la regla, inspeccione otras reglas accept y el comportamiento de las zonas en vez de afirmar que está bloqueado.

</details>

5. ¿Qué cambia curl --resolve lesson.test:8000:192.0.2.20?

   - A) Los servidores DNS de todas las VM
   - B) La asignación de host/puerto para esa invocación de curl
   - C) El archivo /etc/hosts persistente
   - D) Una IP de Kubernetes Service

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) La asignación de host/puerto para esa invocación de curl**

**Explicación:** La anulación se limita a esa invocación. No modifica el resolver del sistema ni las asignaciones que usan otros programas.

</details>

6. ¿Qué principio se debe conservar al pasar de prácticas en VM a CNI?

   - A) Docker bridge y todos los CNI son la misma implementación
   - B) Service IP y localhost son idénticos
   - C) Volver a identificar namespaces, direcciones, rutas, políticas y puntos de observación
   - D) Una solicitud HTTP pequeña demuestra el throughput máximo de la nube

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Volver a identificar namespaces, direcciones, rutas, políticas y puntos de observación**

**Explicación:** Las preguntas de diagnóstico se transfieren, pero la implementación y los límites son distintos. Distinga las abstracciones del clúster de la ruta real de los paquetes.

</details>
