# Cuestionario 6. Firewalls y seguridad del host

> **Versiones compatibles**: Ubuntu Server 24.04 LTS (principal), Rocky Linux 9 (alternativa)
> **Última actualización**: 15 de septiembre de 2026

[Lección y fuentes principales](../../../networking/beginner/06-firewalls-host-security.md) | [Curso](../../../networking/beginner/README.md)

Usa el cliente `.10`, el servidor `.20`, la NIC de administración independiente y el procedimiento acordado de recuperación desde la consola. Elige antes de mostrar la explicación.

1. Un cliente inicia una conexión SSH a este servidor. Desde la perspectiva del firewall del servidor, ¿es tráfico entrante, saliente o reenviado?

   - A) Reenviado, porque todas las conexiones remotas convierten al servidor en un router.
   - B) Saliente, porque el servidor envía una respuesta.
   - C) Entrante para la conexión nueva; las respuestas pertenecen a esa conversación, mientras que el tráfico de otro host se reenviaría.
   - D) Ninguno; SSH omite los firewalls.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

**Explicación:** La dirección depende del host de observación y de la ruta del paquete. Nuestro servidor es el destino, no un router. El manejo de respuestas con seguimiento de estado también explica por qué una conexión SSH antigua puede sobrevivir cuando se rechazan las nuevas. Este laboratorio no requiere cambiar NAT ni el reenvío.

</details>

2. UFW ya tiene una regla amplia que permite SSH. ¿Agregar una regla que permita el acceso desde `.10` limita por sí solo el acceso a `.10`?

   - A) No. Las reglas más amplias existentes permanecen; inspecciona el orden y las reglas personalizadas anteriores, y luego usa la regla permitida con ámbito limitado de la lección seguida de su denegación para el mismo endpoint.
   - B) Sí. Cualquier regla nueva elimina automáticamente las anteriores.
   - C) Sí, si su comentario contiene «secure».
   - D) Solo si firewalld también está habilitado.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

**Explicación:** Una regla limitada que permite el tráfico se agrega; no revoca otras. La lección inserta reglas independientes para el cliente, TCP 22 y 8000 antes de una denegación en la misma NIC del laboratorio/destino/puertos. Así, el permiso HTTP se puede eliminar sin afectar SSH. `before.rules` personalizadas aún pueden cambiar el resultado, así que inspecciona quién las administra y el procesamiento anterior. Tener dos administradores en conflicto hace más difícil razonar sobre el sistema, no más seguro.

</details>

3. ¿Qué es cierto sobre los cambios de reglas y la limpieza de UFW de la lección?

   - A) Son solo cambios en tiempo de ejecución y vencen después de diez minutos.
   - B) Siempre es exacto eliminar las reglas usando un número anterior que se recuerde.
   - C) La limpieza debe deshabilitar UFW aunque estuviera activo antes de la lección.
   - D) Las reglas se guardan y se aplican; elimina las especificaciones exactas de las reglas agregadas correctamente y restaura el estado inactivo solo si la lección habilitó un UFW que originalmente estaba inactivo.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D**

**Explicación:** Este flujo de UFW no tiene la separación entre configuración permanente y de ejecución de firewalld por regla. Las posiciones pueden cambiar; en cambio, la interfaz, el origen, el destino, el protocolo y los puertos definen la regla prevista. Un fallo solo HTTP elimina el permiso independiente de TCP 8000; para restaurarlo, hay que insertarlo antes de la denegación restante del laboratorio. No elimines el permiso TCP 22 para ese experimento. La activación inicial también requiere comprobar el acceso de administración: que la configuración de la NIC no haya cambiado no conserva por sí solo todos los servicios entrantes.

</details>

4. ¿Por qué se coloca la interfaz del laboratorio de Rocky en una nueva zona firewalld vacía?

   - A) Una zona hace innecesarias las direcciones MAC.
   - B) La zona predeterminada o una existente quizá ya permita SSH de forma amplia; una zona exclusiva del laboratorio facilita establecer los permisos previstos sin mover la NIC de administración.
   - C) Todas las zonas bloquean automáticamente ICMP e IPv6.
   - D) Las zonas eliminan la necesidad de inspeccionar las asociaciones de origen o las políticas.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** Una configuración `connection.zone` vacía de NetworkManager usa la zona predeterminada. Los servicios, objetivos, asociaciones de origen, políticas y reglas directas existentes pueden cambiar los permisos efectivos. Registra el UUID del perfil activo del laboratorio y la zona original, incluido un valor vacío, y deja intacto el perfil de administración.

</details>

5. Se agregó una regla rich con `--timeout=600`. ¿Qué ocurre durante una recarga?

   - A) La regla solo de ejecución se pierde; la recarga usa la política guardada, y la asociación de interfaz con zona es un cambio independiente.
   - B) El timeout se convierte automáticamente en permanente.
   - C) Se eliminan todas las direcciones de NetworkManager.
   - D) No cambia nada porque la configuración de ejecución siempre reemplaza la permanente.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

**Explicación:** La regla de prueba vence cuando termina su timeout y también se pierde durante una recarga. Una regla guardada requiere un cambio permanente explícito y cargarse en el estado de ejecución. La recarga también puede descartar otros cambios de ejecución; no la uses a la ligera ni copies todo el estado desconocido con `--runtime-to-permanent`. Sigue haciendo falta recuperación por consola si la zona del laboratorio ya no permite nuevas conexiones SSH.

</details>

6. El cliente permitido recibe HTTP 200 desde `.20:8000`. ¿Qué afirmación está respaldada?

   - A) Se ha probado y denegado el acceso de todos los orígenes no aprobados.
   - B) No puede haber otra regla amplia de permiso.
   - C) Este cliente llegó a este servicio en escucha durante esta prueba; restringir el origen aún requiere inspeccionar las políticas y cualquier prueba de denegación realizada por separado.
   - D) SELinux permite que cualquier aplicación lea todos los archivos.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

**Explicación:** Una prueba correcta de la ruta permitida tiene un alcance limitado. Una solicitud desde el propio servidor o `localhost` no prueba que se haya denegado a un cliente externo. Compara el listener, la ruta, la interfaz/zona y las reglas; informa lo que realmente mediste. El servidor Python acotado y el archivo temporal deben detenerse/eliminarse por separado de la política del firewall.

</details>

7. Un archivo tiene un tipo SELinux deliberadamente incorrecto. ¿Qué recuperación corresponde a la lección?

   - A) Deshabilitar SELinux globalmente.
   - B) Otorgar permisos de escritura a todos de forma recursiva.
   - C) Generar una política allow amplia para todos los registros de auditoría.
   - D) Comparar el contexto esperado de la ruta, previsualizar `restorecon -n`, restaurar la etiqueta de política de ese archivo y verificar con `matchpathcon -V`.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D**

**Explicación:** Los modos de Unix y los contextos SELinux son comprobaciones independientes. `chcon` cambia la etiqueta actual; no crea una asociación duradera para la ruta. `restorecon` usa las reglas de contexto de archivos de la política. Una ruta personalizada permanente quizá requiera una asociación intencional de `semanage fcontext`, pero el ejercicio del archivo temporal no.

</details>

8. `ausearch` no encuentra AVC coincidentes y Fail2ban informa cero bloqueos. ¿Cuál es una interpretación sólida?

   - A) Ambas herramientas demuestran que los ataques son imposibles.
   - B) Los registros/contadores consultados están vacíos; los filtros, el intervalo de tiempo, los metadatos del journal, los permisos y los eventos reales determinan qué pruebas existen.
   - C) Desactiva el modo enforcing hasta que aparezcan errores.
   - D) Ejecuta un bucle de fuerza bruta para crear un valor distinto de cero.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** El ejercicio de etiquetas no activa deliberadamente el acceso a un recurso confinado, así que no se garantiza un AVC. Fail2ban puede estar correctamente inactivo o mal configurado. Inspecciona la unidad de journal real, el backend/filtro/acción y los registros de inicio. La lección opcional indica explícitamente que no se usa fuerza bruta ni se afirma que se haya probado la aplicación en vivo.

</details>

9. ¿Qué configuración opcional de paquetes corresponde a Rocky Linux 9?

   - A) Registrar el estado existente, habilitar el requisito previo CRB adecuado y EPEL 9 según las instrucciones de la distribución, verificar los paquetes candidatos y sus firmas, e instalar solo los paquetes necesarios.
   - B) Usar cualquier versión principal de EPEL con la verificación de firmas deshabilitada.
   - C) Instalar paquetes de Ubuntu si DNF no resuelve una dependencia.
   - D) Deshabilitar CRB/EPEL existentes después de la instalación aunque otros paquetes dependan de ellos.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

**Explicación:** EPEL proporciona software opcional y CRB proporciona dependencias. Importan la versión principal correcta de EL, la identidad del repositorio y la arquitectura del entorno invitado. La misma preparación permite instalar de forma opcional `iftop` en la lección 7. Deshabilitar un repositorio no revierte los paquetes; para revertir por completo una instalación opcional se usa la instantánea registrada.

</details>

10. ¿Qué configuración y limpieza de Fail2ban respetan los límites del laboratorio?

   - A) Usar `backend=systemd` con una ruta `/var/log/auth.log` supuesta y luego vaciar todos los bloqueos.
   - B) Reutilizar cualquier jail de producción existente y detenerlo sin inspeccionarlo.
   - C) Verificar un jail SSH dedicado respaldado por journal y una acción limitada al laboratorio, inspeccionar su estado, desbloquear solo las direcciones de curso indicadas, detener ese jail, eliminar sus dos archivos administrados y después limpiar la zona del firewall.
   - D) Suponer que el servicio activo demuestra que funcionan el filtro y la acción del firewall.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

**Explicación:** El backend journal usa `journalmatch`, no `logpath`. La acción debe ir antes del permiso del laboratorio y limitarse a la interfaz/zona del laboratorio, `.20` y TCP 22. Prueba la configuración interpretada e inspecciona la expansión de la acción. Restaura los bloqueos accidentales exactos y detén el jail antes de eliminar su zona; nunca vacíes el estado de firewalls no relacionados. Sin pruebas adicionales, informa que se verificaron la configuración y el inicio, no que se haya demostrado la detección de ataques.

</details>

[Volver a la lección](../../../networking/beginner/06-firewalls-host-security.md) | [Siguiente: Monitorización](../../../networking/beginner/07-monitoring-performance.md)
