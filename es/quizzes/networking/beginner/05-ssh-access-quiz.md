# Cuestionario 5. Acceso remoto con SSH

> **Versiones admitidas**: Ubuntu Server 24.04 LTS (principal), Rocky Linux 9 (alternativa)
> **Última actualización**: 15 de septiembre de 2026

[Lección y fuentes principales](../../../networking/beginner/05-ssh-access.md) | [Curso](../../../networking/beginner/README.md)

Elige la respuesta más segura que esté justificada y explica qué pruebas
inspeccionarías. Los comandos son ejercicios de interpretación para las VM
desechables.

1. Ubuntu 24.04 muestra `ssh.socket` activo, mientras que una guía de Rocky menciona `sshd.service`. ¿Qué deberías hacer?

   - A) Deshabilitar todos los sockets para que ambas distribuciones sean idénticas.
   - B) Usar `sshd.service` en todas partes porque el ejecutable se llama `sshd`.
   - C) Inspeccionar las unidades instaladas en el guest; Ubuntu usa `ssh.service` y puede activar el socket, mientras que Rocky usa `sshd.service`.
   - D) Cambiar el puerto SSH antes de comprobar cualquier listener.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

**Explicación:** Los nombres del ejecutable y de la unidad de servicio no tienen que coincidir. La activación del socket de Ubuntu puede ser responsable del listener, por lo que deshabilitarlo o cambiar las asociaciones a ciegas puede interrumpir el acceso. Esta lección comprueba la sintaxis, el estado del servicio/socket y TCP 22, sin cambiar las direcciones de escucha existentes.

</details>

2. En la primera conexión, el cliente muestra una huella de host ED25519. ¿Qué comparación establece la confianza prevista?

   - A) Compara la huella completa con la clave pública de host del servidor que se muestra en su consola del hipervisor.
   - B) Compárala con la clave pública del usuario que acabas de generar.
   - C) Acéptala porque la IP termina en `.20`.
   - D) Ejecuta `ssh-keyscan` por la misma ruta no confiable y acepta cualquier resultado.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

**Explicación:** Las claves de host identifican el servidor; las claves de usuario autentican una cuenta de usuario. Una consola confiable proporciona una ruta de comparación independiente. Un escaneo puede obtener una clave, pero no autenticar a su propietario. Si hay una discrepancia, investiga la VM/dirección y un posible cambio de identidad en vez de omitir las comprobaciones.

</details>

3. ¿Qué se debe instalar en el servidor al agregar tu clave de usuario?

   - A) El archivo privado `id_ed25519` y su frase de contraseña.
   - B) La clave privada de host del servidor, copiada en tu directorio personal.
   - C) Una captura de pantalla de la contraseña de tu cuenta.
   - D) La línea pública `id_ed25519.pub`, añadida a las claves autorizadas de la cuenta correcta sin reemplazar otras entradas.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D**

**Explicación:** La clave privada permanece en el cliente y se protege con una frase de contraseña no vacía. `ssh-copy-id -i` selecciona la clave pública que se instalará con la autenticación existente. Si SSH de bootstrap no está disponible, añade la línea pública desde la consola; no habilites contraseñas ni transmitas la clave privada para copiarla.

</details>

4. Ya tienes una sesión SSH abierta. ¿Qué debe ocurrir antes de deshabilitar la autenticación por contraseña e interactiva de teclado?

   - A) Nada; una conexión existente demuestra que los próximos inicios de sesión funcionarán.
   - B) Debe funcionar una segunda conexión independiente que use solo la clave, con el uso compartido de conexiones deshabilitado; también se deben verificar las rutas SSH de administración necesarias.
   - C) Elimina todas las claves autorizadas salvo la que aparece primero.
   - D) Cierra la consola para que la prueba sea realista.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** Las sesiones existentes autenticadas o multiplexadas pueden ocultar una ruta rota de inicio de sesión nuevo. Usa explícitamente la clave, `IdentitiesOnly`, autenticación solo de clave pública y sin conexión compartida. Se espera que la frase de contraseña de la clave privada siga siendo local. Mantén abierta la consola y la sesión original para recuperarte.

</details>

5. Un archivo drop-in tardío indica `PasswordAuthentication no`, pero `sshd -T -C` sigue mostrando `yes` para el usuario del laboratorio. ¿Cuál es la respuesta correcta?

   - A) Investiga los valores anteriores, el orden de Include y los bloques Match aplicables; no vuelvas a cargar el servicio suponiendo que el nombre del archivo determina la precedencia.
   - B) Supón que el resultado efectivo impreso es irrelevante.
   - C) Añade el mismo ajuste a diez archivos más.
   - D) Reinicia la red para que SSH lea el drop-in.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

**Explicación:** El comportamiento de primer valor de OpenSSH y las reglas Match específicas de conexión son distintas de «gana el último archivo». `-C` proporciona el usuario, el origen y el endpoint local que se usan para evaluar los ajustes efectivos. Una comprobación de sintaxis por sí sola no demuestra que la política deseada sea efectiva. Elimina solo el archivo creado por el curso si no puedes establecer su precedencia prevista.

</details>

6. ¿Qué afirmación sobre el endurecimiento de seguridad es correcta?

   - A) `PasswordAuthentication no` también deshabilita siempre la autenticación interactiva de teclado.
   - B) `PermitRootLogin no` significa que sudo deja de funcionar.
   - C) Comprueba explícitamente los valores de contraseña, autenticación interactiva de teclado, clave pública e inicio de sesión de root, y conserva el acceso de usuarios normales mediante clave y sudo.
   - D) Es necesario desactivar PAM globalmente para iniciar sesión con clave.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

**Explicación:** Los métodos por contraseña e interactivo de teclado son distintos. También son distintos el inicio directo de sesión SSH de root y el acceso sudo autorizado de un usuario normal. La lección no deshabilita PAM. Los cambios globales de autenticación requieren comprobar todas las cuentas y rutas de administración necesarias, no solo la IP del laboratorio.

</details>

7. La recarga tuvo éxito, pero falla un nuevo inicio de sesión. ¿Qué método de recuperación tiene el alcance adecuado?

   - A) Vacía el firewall y elimina `/etc/ssh`.
   - B) Restaura todo el directorio SSH anterior sobre cualquier cambio administrativo más reciente.
   - C) Reinicia inmediatamente y descarta la consola.
   - D) Usa la consola del servidor para eliminar solo el drop-in propio, valida la sintaxis y la configuración efectiva de referencia, vuelve a cargar y prueba una conexión nueva.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D**

**Explicación:** El método de archivo propio permite una reversión exacta sin reemplazar otra configuración. Compara los resultados efectivos para usuarios normales, root y los casos de administración registrados. Si hubo cambios concurrentes, concílialos en vez de restaurar a ciegas un directorio antiguo. Las sesiones existentes por sí solas no validan la recuperación.

</details>

8. Se añadió la clave pública del curso a un `authorized_keys` existente. ¿Cómo se debe realizar la limpieza final?

   - A) Elimina `~/.ssh` de forma recursiva.
   - B) Elimina solo la línea identificada por el comentario y la huella del curso, conserva las demás claves, restaura los permisos registrados y luego elimina los archivos de clave del cliente dedicados, después de revocarla.
   - C) Sobrescribe el archivo con uno vacío porque la lección terminó.
   - D) Primero elimina la clave privada del cliente y supón que la autorización del servidor se revoca automáticamente.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** Eliminar una copia del cliente no revoca una clave pública instalada en un servidor. Primero revoca la entrada exacta del servidor y conserva los cambios ajenos. Un directorio solo se elimina si la lección lo creó y está vacío. La reversión de la instalación de paquetes es independiente y utiliza la instantánea del guest si se requiere una restauración completa.

</details>

[Volver a la lección](../../../networking/beginner/05-ssh-access.md) | [Siguiente: Seguridad del host](../../../networking/beginner/06-firewalls-host-security.md)
