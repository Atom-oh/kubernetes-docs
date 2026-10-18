# Cuestionario final sobre contenedores y nube

[Lección](../../../networking/beginner/08-container-cloud-capstone.md)

Seis preguntas. Explica cada respuesta con tus propias palabras.

1. Una solicitud a una IP devuelve HTTP 200, pero getent no puede resolver el nombre del servicio. ¿Qué se debe investigar primero?

   - A) Los algoritmos de control de congestión de la CPU
   - B) La ruta de resolución de nombres
   - C) Solo los permisos de archivos HTTP
   - D) Todas las implementaciones de CNI

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) La ruta de resolución de nombres**

**Explicación:** Ya se establecieron la conectividad IP y una respuesta de la aplicación, así que investiga cómo se resuelve el nombre. Hace falta más evidencia para atribuir la causa a un servidor DNS en particular.

</details>

2. El servidor devuelve HTTP 404. ¿Qué ha demostrado esta solicitud?

   - A) Todos los puertos están abiertos
   - B) La tabla de enrutamiento está vacía
   - C) Se intercambió una respuesta HTTP con el servidor
   - D) Toda Internet está en buen estado

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Se intercambió una respuesta HTTP con el servidor**

**Explicación:** 404 es una respuesta de la capa HTTP. Compara las rutas y los registros del servidor; esta evidencia no justifica restablecer todo el firewall.

</details>

3. ss muestra solo un socket en escucha en 127.0.0.1:8000 y funciona una solicitud local al servidor. ¿Qué es fundamental al investigar un fallo remoto?

   - A) Comprobar si el socket escucha en la dirección de destino de la solicitud remota
   - B) Suponer que localhost del cliente y localhost del servidor son lo mismo
   - C) Aumentar siempre el TTL de DNS
   - D) Desactivar SELinux

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Comprobar si el socket escucha en la dirección de destino de la solicitud remota**

**Explicación:** La interfaz loopback pertenece a su propio espacio de nombres de red. Para recibir tráfico en la IP de laboratorio del servidor, se necesita un socket que escuche en la dirección adecuada y reglas de acceso apropiadas.

</details>

4. Solo se eliminó la regla independiente de UFW que permitía TCP 8000. La nueva conexión SSH solo con clave sigue funcionando, pero HTTP falla. ¿Qué recuperación conserva la política prevista?

   - A) Añadir una regla para permitir HTTP después de la regla deny de laboratorio restante
   - B) Eliminar la regla deny de laboratorio y todas las reglas SSH
   - C) Desactivar UFW y suponer que una sesión SSH antigua demuestra la recuperación
   - D) Insertar la regla allow original y restringida para HTTP antes de la regla deny; después verificar el orden, HTTP 200 y una nueva conexión SSH solo con clave

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Insertar la regla allow original y restringida para HTTP antes de la regla deny; después verificar el orden, HTTP 200 y una nueva conexión SSH solo con clave**

**Explicación:** SSH y HTTP tienen reglas allow independientes, así que el fallo HTTP debe dejar intactos TCP 22 y las políticas predeterminadas. La posición de las reglas en UFW importa: una regla allow añadida después de una regla deny coincidente no surte efecto. Prueba una conexión nueva, sin multiplexación y solo con clave, antes, durante y después del fallo; permite que se solicite la frase de contraseña de la clave cifrada en vez de dar por hecho que el agente está desbloqueado. En la variante de firewalld, solo se elimina y restaura la regla HTTP en tiempo de ejecución; la regla permanente se mantiene. Si HTTP nunca falla tras eliminarla, inspecciona otras reglas accept y el comportamiento de las zonas en vez de afirmar que el tráfico está bloqueado.

</details>

5. ¿Qué cambia curl --resolve lesson.test:8000:192.0.2.20?

   - A) Los servidores DNS de todas las máquinas virtuales
   - B) La asignación de nombre de host y puerto para esa invocación de curl
   - C) El archivo /etc/hosts persistente
   - D) Una IP de Kubernetes Service

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) La asignación de nombre de host y puerto para esa invocación de curl**

**Explicación:** La anulación se limita a esa invocación. No modifica la resolución de nombres del sistema ni las asignaciones que usan otros programas.

</details>

6. ¿Qué principio se debe conservar al pasar de prácticas en VM a CNI?

   - A) El puente de Docker y todos los complementos CNI son la misma implementación
   - B) La IP de servicio y localhost son idénticos
   - C) Volver a identificar los espacios de nombres, las direcciones, las rutas, las políticas y los puntos de observación
   - D) Una solicitud HTTP pequeña demuestra el rendimiento máximo de la nube

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Volver a identificar los espacios de nombres, las direcciones, las rutas, las políticas y los puntos de observación**

**Explicación:** Las preguntas de diagnóstico siguen siendo útiles, pero la implementación y sus límites son distintos. Distingue las abstracciones del clúster de la ruta real de los paquetes.

</details>
