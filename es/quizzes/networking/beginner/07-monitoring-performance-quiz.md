# Cuestionario sobre monitoreo y rendimiento

[Lección](../../../networking/beginner/07-monitoring-performance.md)

Seis preguntas. Explique cada respuesta con sus propias palabras.

1. Un socket LISTEN muestra Recv-Q 3 y Send-Q 128. ¿Qué significa?

   - A) Se recibieron 3 bytes del cuerpo y se enviaron 128 bytes del cuerpo
   - B) Hay 3 conexiones esperando que se acepten; el máximo de la cola de aceptación es 128
   - C) Hay 3 retransmisiones y una RTT de 128 ms
   - D) Existen 128 conexiones en este momento

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Hay 3 conexiones esperando que se acepten; el máximo de la cola de aceptación es 128**

**Explicación:** Las colas LISTEN cuentan conexiones. Sus unidades son distintas de los bytes de flujo de los sockets ESTABLISHED, así que primero compruebe el estado.

</details>

2. Una solicitud curl a una dirección IP muestra un time_namelookup muy pequeño. ¿Qué se puede concluir?

   - A) El DNS de la organización siempre es rápido
   - B) Todas las cachés DNS están vacías
   - C) Esta solicitud no sirve para validar el rendimiento de DNS
   - D) El procesamiento del servidor tomó cero tiempo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Esta solicitud no sirve para validar el rendimiento de DNS**

**Explicación:** Un literal de IP no prueba la resolución del nombre de un servicio. Evite también sumar campos de tiempo acumulados como si fueran intervalos independientes.

</details>

3. curl funciona, pero tcpdump no captura nada. ¿Qué se debe comprobar primero?

   - A) La NIC seleccionada, el filtro y el intervalo de captura
   - B) Restablecer todas las tablas de enrutamiento del host
   - C) Habilitar el inicio de sesión SSH con contraseña
   - D) Aumentar todos los buffers TCP máximos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) La NIC seleccionada, el filtro y el intervalo de captura**

**Explicación:** Una captura depende del lugar y las condiciones de observación. Alinee las horas de la solicitud y de la captura, y verifique la NIC seleccionada para el laboratorio.

</details>

4. ¿Qué diferencia hay entre 100 Mbit/s y 100 MB/s?

   - A) Siempre son iguales
   - B) El valor en Mbit/s es ocho veces mayor
   - C) Solo son iguales con HTTP
   - D) 100 MB/s equivale a una tasa de 800 Mbit/s

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) 100 MB/s equivale a una tasa de 800 Mbit/s**

**Explicación:** Un byte son ocho bits. Comparar el rendimiento real de una aplicación también requiere considerar la sobrecarga del protocolo, los puntos de observación y las condiciones de ejecución.

</details>

5. Una instantánea de Send-Q muestra un valor mayor que cero. ¿Cuál es el siguiente paso adecuado?

   - A) Confirmar que se perdió tráfico de red
   - B) Duplicar todos los sysctl de buffers
   - C) Correlacionar el estado, los cambios a lo largo del tiempo, el progreso de la aplicación y los paquetes
   - D) Desactivar el firewall remoto

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Correlacionar el estado, los cambios a lo largo del tiempo, el progreso de la aplicación y los paquetes**

**Explicación:** Send-Q puede incluir tanto bytes no confirmados como bytes aún no enviados. Una sola instantánea no permite establecer la causa.

</details>

6. ¿Qué diferencia hay entre un scheduler de E/S de bloques y un qdisc de red?

   - A) Gestionan solicitudes de almacenamiento y colas de transmisión de red, respectivamente
   - B) Ambos son cachés DNS
   - C) Ambos validan claves SSH
   - D) Ambos usan el mismo sysctl único

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Gestionan solicitudes de almacenamiento y colas de transmisión de red, respectivamente**

**Explicación:** Primero localice el cuello de botella. Que compartan el concepto de planificación no significa que controlen los mismos recursos ni que sus ajustes tengan los mismos efectos.

</details>
