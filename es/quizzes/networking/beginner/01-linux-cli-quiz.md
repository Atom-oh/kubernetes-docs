# Cuestionario 1. Tu primera terminal Linux

> **Versiones compatibles**: Ubuntu Server 24.04 LTS (principal), Rocky Linux 9 (alternativa)
> **Última actualización**: 15 de septiembre de 2026

[Volver a la lección](../../../networking/beginner/01-linux-cli.md) | [Preparación del curso](../../../networking/beginner/README.md)

Elige una respuesta antes de abrir su explicación. Estos escenarios usan la máquina virtual desechable y el cuaderno privado de la lección 1. Los comandos de las preguntas sirven para interpretar, no son instrucciones para ejecutar en tu host.

1. `cat /etc/os-release` identifica Ubuntu 24.04, mientras que `uname -r` imprime otro número de versión. ¿Qué explicación encaja?

   - A) Uno de los comandos debe estar averiado porque Linux solo tiene un número de versión.
   - B) Ubuntu es una biblioteca y `uname` identifica el terminal.
   - C) Ubuntu es una distribución; `uname -r` informa sobre el kernel en ejecución. Las bibliotecas y el shell son componentes de espacio de usuario independientes.
   - D) Instalar un editor nuevo siempre reemplaza el kernel.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

**Explicación:** Una distribución reúne un kernel, bibliotecas, herramientas, repositorios y configuración. El kernel administra los recursos y expone llamadas al sistema; una biblioteca proporciona funciones reutilizables, algunas de las cuales usan esas llamadas. Bash interpreta comandos en el espacio de usuario. Sus versiones no tienen por qué coincidir con la versión de la distribución. Debian es la familia de la que deriva Ubuntu, pero esa relación no garantiza que los valores predeterminados sean idénticos.

</details>

2. Tu directorio de trabajo es una raíz temporal única. Ejecutas `cp -i notes/draft.txt notes/copy.txt` y luego `mv -i notes/copy.txt archive/saved.txt`. ¿Qué debería existir después de que ambos comandos tengan éxito?

   - A) Solo `archive/saved.txt`; `cp` eliminó el borrador.
   - B) `notes/draft.txt` y `archive/saved.txt`; `notes/copy.txt` ya no existe.
   - C) Los tres archivos; `mv` es otra forma de escribir copy.
   - D) Archivos en `/notes` y `/archive`, porque las rutas relativas empiezan en `/`.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** `cp` deja el origen en su lugar y crea una copia; `mv` cambia la ubicación/el nombre de la copia. Las rutas relativas empiezan en el directorio de trabajo, por eso es importante comprobar `pwd`. `-i` pregunta antes de sobrescribir un destino existente; no proporciona un historial general de deshacer. Más adelante, la copia guardada puede recuperar el borrador.

</details>

3. Quieres un archivo de práctica vacío y ejecutas `touch notes/draft.txt`, olvidando que ya contiene tus notas. ¿Qué hace normalmente `touch`?

   - A) Vacía el archivo y conserva sus marcas de tiempo anteriores.
   - B) Crea un directorio con ese nombre.
   - C) Actualiza las marcas de tiempo del archivo existente y conserva su contenido.
   - D) Mueve el archivo a tu directorio personal.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

**Explicación:** `touch` crea un archivo vacío solo si esa ruta no existe. En un archivo existente normalmente cambia las marcas de tiempo de acceso/modificación, no su texto. Usa `cat` para inspeccionar el contenido y `ls -l` para ver el tamaño. Por eso la lección empieza en un directorio único en vez de dar por sentado que un nombre de archivo conocido no se está usando.

</details>

4. Tienes cambios sin guardar en vi y quieres descartarlos. ¿Qué acción es correcta?

   - A) Escribe `:q!` en el prompt de Bash.
   - B) Pulsa Esc, escribe `:q!` y pulsa Enter dentro de vi.
   - C) Pulsa `i` y luego escribe `:wq`.
   - D) Pulsa Ctrl+O, que guarda y cierra todos los editores.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** Esc vuelve al modo normal de vi; `:q!` descarta los cambios desde el último guardado y sale. `:wq` guarda y sale, mientras que `:q` protege el trabajo sin guardar al negarse a salir. En nano, Ctrl+O escribe después de confirmar el nombre del archivo y Ctrl+X sale. Para descartar cambios sin guardar en nano, sal y rechaza el guardado cuando te lo pregunte. Los comandos del editor se escriben dentro del editor, no en el shell.

</details>

5. El modo básico de un archivo es `640` (`-rw-r-----`). ¿Qué interpretación es correcta?

   - A) El propietario puede leer/escribir, el grupo puede leer y los demás no tienen permisos básicos sobre el archivo.
   - B) Todos pueden leer/escribir porque `6` es el dígito mayor.
   - C) El propietario puede ejecutar porque `6` significa lectura más ejecución.
   - D) Nadie puede eliminarlo porque no tiene el bit de ejecución.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

**Explicación:** Lectura=4, escritura=2, ejecución=1; por tanto, el `6` del propietario significa lectura+escritura y el `4` del grupo significa lectura. Los permisos del directorio y otros controles afectan al acceso y a la eliminación de entradas del directorio; el permiso de escritura del archivo por sí solo no determina la eliminación. Para deshacer el `chmod 600` de la lección, restaura el modo numérico original registrado, no un `644` supuesto.

</details>

6. Al guardar tu cuaderno aparece «Permission denied». ¿Cuál es la mejor primera respuesta?

   - A) Ejecutar un cambio recursivo de permisos en `/home`.
   - B) Abrir un shell de root y repetir todos los comandos restantes de la lección.
   - C) Comprobar `pwd`, `id` y el propietario/permisos del directorio y archivo pertinentes.
   - D) Deshabilitar el firewall de la máquina virtual.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

**Explicación:** Puede que estés en el directorio equivocado o editando un archivo que pertenece a otra cuenta. El cuaderno está en tu propio directorio temporal y normalmente no necesita privilegios elevados. `sudo` eleva un comando permitido, con root como usuario predeterminado; no es una herramienta de diagnóstico. Ejecutar `sudo whoami` y luego `whoami` muestra que un solo comando con privilegios elevados no convierte permanentemente el shell normal en root.

</details>

7. En Ubuntu, `sudo apt update` termina correctamente. ¿Actualizó todos los paquetes instalados y garantizó que nano esté instalado?

   - A) Sí; `update` significa instalar todas las actualizaciones disponibles y el editor que falte.
   - B) No; actualizó los índices de paquetes de los repositorios. Hace falta una transacción de paquetes independiente para instalar o actualizar software.
   - C) Solo cambió el kernel que se está ejecutando.
   - D) Habilitó todos los servicios detectados recientemente.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** `apt update` actualiza la información de los paquetes disponibles; `apt install nano` solicita una instalación y la resolución de dependencias, mientras que `apt upgrade` tiene otra función. En la máquina virtual, revisa la transacción propuesta antes de confirmarla. Un `dpkg-query` local comprueba los registros de paquetes instalados. Eliminar un paquete posteriormente no revierte exactamente todos los cambios de dependencias, caché, registros o configuración; para recuperar por completo la instalación opcional se usa la instantánea registrada de la máquina virtual.

</details>

8. Una máquina virtual Rocky Linux 9 necesita un editor. ¿Qué procedimiento de preparación coincide con la lección?

   - A) Añadir repositorios de Ubuntu y ejecutar APT.
   - B) Usar `rpm -q` para inventariar paquetes locales y DNF para instalar; existe compatibilidad con `yum`, pero no es necesario ejecutar ambos.
   - C) Usar `systemctl install nano` porque todo software es un servicio.
   - D) Reconstruir el kernel antes de instalar cualquier paquete.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** Rocky usa paquetes RPM y DNF para administrar dependencias. Los editores alternativos de la lección son `nano` y `vim-minimal`; Ubuntu usa su propia familia de paquetes y nombres de paquetes. Conocer las distribuciones ayuda a elegir herramientas, pero no da permiso para mezclar repositorios ni para asumir que los valores predeterminados de servicios/red son idénticos.

</details>

9. ¿Qué ayudan a observar `ps -p $$ -o pid,ppid,user,comm` y el ejercicio `sleep 30`?

   - A) La identidad del proceso del shell y un proceso en primer plano que ocupa el shell temporalmente.
   - B) Todos los paquetes instalados en la máquina virtual.
   - C) Un servicio permanente creado por cada comando de shell.
   - D) Un PID que será el mismo en ambas máquinas virtuales y después de cada reinicio.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

**Explicación:** `$$` se expande al PID del Bash actual; `PPID` identifica a su padre. Un proceso es una instancia en ejecución de un programa, mientras que un paquete es software instalado en el disco. `sleep` termina después de 30 segundos o se puede interrumpir con Ctrl+C. No se habilitó ningún servicio, y no se debe usar un PID copiado de un documento para terminar un proceso desconocido.

</details>

10. `systemctl is-active systemd-journald.service` indica `active`, mientras que `is-enabled` indica `static`. ¿Qué conclusión está justificada?

   - A) El servicio de registro falló porque no está `enabled`.
   - B) La unidad está activa ahora y no tiene una sección de habilitación normal; las rutas de dependencia/activación pueden iniciarla.
   - C) `static` significa que los registros están congelados permanentemente.
   - D) Hay que ejecutar `enable` repetidamente hasta que ambos comandos devuelvan la misma palabra.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** El estado de ejecución y la habilitación son cosas distintas. `start` afecta a la operación actual, mientras que `enable` crea enlaces de habilitación y no inicia por sí mismo una unidad, a menos que se combine con `--now`. Una unidad estática no está averiada por definición. Lea `Loaded`, `Active` y los registros pertinentes en vez de cambiar servicios del sistema para forzar una salida concreta.

</details>

11. ¿Qué selecciona `sudo journalctl -b -u systemd-journald.service -n 20 --no-pager`?

   - A) Las primeras 20 líneas de todos los archivos de registro de todos los arranques.
   - B) Las 20 entradas coincidentes más recientes que se conservan para esa unidad durante el arranque actual, impresas sin paginador.
   - C) Todas las entradas y luego elimina las 20 últimas.
   - D) Solo errores, porque todos los mensajes del journal son errores.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** `-b` limita al arranque actual, `-u` a la unidad y `-n` indica cuántas entradas recientes mostrar. Es una operación de lectura. Interpreta las marcas de tiempo y el contexto del mensaje; un evento informativo no es un fallo. Si no hay entradas coincidentes, puede deberse al filtro o a la retención; los usuarios con menos privilegios también pueden tener una visibilidad incompleta. Comprueba el estado del servicio antes de concluir que el registro está averiado.

</details>

12. Volviste a abrir la consola de la máquina virtual y `LAB_DIR` está vacío. ¿Cuál es el procedimiento de limpieza correcto?

   - A) Eliminar todos los directorios cuyo nombre empiece por `network-beginner`.
   - B) Suponer que se conserva el directorio actual del shell anterior y ejecutar una eliminación recursiva.
   - C) Restaurar `LAB_DIR` desde la ruta exacta registrada, inspeccionarla, eliminar solo los archivos de práctica indicados y después quitar los directorios vacíos.
   - D) Eliminar `/tmp` para borrar todos los posibles archivos temporales.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

**Explicación:** Las variables no persisten automáticamente entre sesiones. La ruta única registrada y los nombres de archivo explícitos delimitan la operación. Que `rmdir` rechace un directorio no vacío es evidencia útil: inspecciona los archivos sobrantes del editor o los pasos incompletos en vez de recurrir a una eliminación amplia. Una ejecución correcta de `test ! -e "$LAB_DIR"` devuelve el estado `0`, que confirma que esa ruta específica ya no existe.

</details>

Si alguna explicación te resultó difícil, vuelve al ejercicio correspondiente en la [lección](../../../networking/beginner/01-linux-cli.md) y luego continúa con [direcciones e interfaces](../../../networking/beginner/02-addressing-interfaces.md).
