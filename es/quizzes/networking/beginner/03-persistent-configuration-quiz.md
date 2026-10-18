# Cuestionario sobre configuración de red persistente

> **Última actualización**: 15 de septiembre de 2026

Usa la [lección](../../../networking/beginner/03-persistent-configuration.md) para explicar el razonamiento, no solo la letra de la opción. El laboratorio tiene el cliente `.10/24` y el servidor `.20/24` en `192.0.2.0/24`, sin DHCP/router/DNS en esa red interna, y una NIC de administración independiente que no se modifica.

## Preguntas

1. Una máquina virtual tiene dos interfaces con nombres desconocidos. ¿A cuál debes asignar `192.0.2.10/24`?
   - A) A la primera interfaz que muestra `ip`
   - B) A la interfaz con la ruta predeterminada actual
   - C) A la interfaz cuya MAC coincide con el adaptador del laboratorio interno registrado por el hipervisor
   - D) A cualquier interfaz que esté marcada como UP

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) A la interfaz cuya MAC coincide con el adaptador del laboratorio interno registrado por el hipervisor**

**Explicación:** El nombre y el orden de la interfaz no permiten asignarle una función de forma fiable. Relaciona la MAC registrada con `ip -br link`; después, inspecciona el direccionamiento y las rutas. Conserva la NIC de administración independiente aunque tenga un nombre más conocido.

</details>

2. `systemd-networkd` está activo, pero una definición de Netplan selecciona NetworkManager para la NIC del laboratorio. ¿Qué debes hacer?
   - A) Suponer que networkd administra todas las interfaces porque su servicio está en ejecución
   - B) Inspeccionar la definición de Netplan coincidente y el perfil generado antes de elegir qué administrador modificar
   - C) Crear también un archivo `.network` directo para la misma NIC
   - D) Deshabilitar ambos servicios y usar solo `ip address add`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Inspeccionar la definición de Netplan coincidente y el perfil generado antes de elegir qué administrador modificar**

**Explicación:** El estado del servicio y la administración de cada dispositivo son cosas distintas. Netplan puede generar configuración para el backend y una definición directa que compita con ella puede causar conflictos. Un comando `ip` solo modifica el estado en tiempo de ejecución, no las instrucciones persistentes para el arranque.

</details>

3. Un archivo de Netplan anterior ya contiene una lista de direcciones DNS para la NIC del laboratorio. Un archivo posterior especifica `nameservers: {addresses: []}`. ¿Es una forma segura y general de eliminar la lista anterior?
   - A) Sí; el archivo con el número más alto siempre borra todos los valores anteriores
   - B) Sí; las listas siempre se comportan como valores escalares
   - C) No; mueve todos los archivos de Netplan fuera del directorio
   - D) No; inspecciona la configuración combinada y la definición propietaria, porque las listas se pueden concatenar

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) No; inspecciona la configuración combinada y la definición propietaria, porque las listas se pueden concatenar**

**Explicación:** Una superposición posterior no restablece los valores de forma universal. Inspecciona `netplan get`, los archivos de entrada reales, los ID/MAC coincidentes y cualquier fuente de aprovisionamiento. Con una copia de seguridad, modifica el administrador confirmado del laboratorio o usa la ruta de una NIC nueva sin definición existente. Nunca reemplaces la configuración de administración para resolver un conflicto del laboratorio.

</details>

4. ¿Qué configuración IPv4 persistente corresponde a la NIC del cliente del laboratorio del curso?
   - A) `192.0.2.10/24`, sin gateway ni DNS en esa NIC, con DHCP deshabilitado
   - B) `192.0.2.10/24`, gateway `192.0.2.1` porque todas las subredes tienen un router `.1`
   - C) DHCP habilitado y una dirección DNS pública para obtener una concesión
   - D) `192.0.2.20/24`, la misma dirección del servidor

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) `192.0.2.10/24`, sin gateway ni DNS en esa NIC, con DHCP deshabilitado**

**Explicación:** El par está conectado directamente dentro de `/24`. En esta red interna no hay router ni servicio DHCP/DNS. Adivinar una gateway no crea un router y DNS no proporciona concesiones DHCP. La conexión de administración independiente conserva su propia configuración.

</details>

5. `netplan generate` termina correctamente y, después, se agota el tiempo de un `netplan try` sin confirmación. ¿Qué está justificado?
   - A) Que la sintaxis sea válida demuestra que se eligió la MAC correcta y se conservó la ruta de administración
   - B) El timeout garantiza la restauración tanto de los archivos en disco como del estado en ejecución
   - C) Inspeccionar desde la consola el estado en ejecución y en disco; si hace falta, usar el procedimiento de recuperación para el archivo exacto
   - D) Reiniciar inmediatamente sin leer los archivos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Inspeccionar desde la consola el estado en ejecución y en disco; si hace falta, usar el procedimiento de recuperación para el archivo exacto**

**Explicación:** `generate` comprueba/genera la configuración, pero no demuestra que haya conectividad. `try` está pensado para revertir cambios no confirmados, aunque tiene salvedades de reversión documentadas. Verifica la configuración guardada antes de reiniciar, mueve solo el archivo que administraste para revertir y comprueba si la dirección exacta del laboratorio sigue presente en el estado de ejecución.

</details>

6. Creaste `beginner-lab-static` con `connection.autoconnect no`. ¿Qué significa?
   - A) El perfil desaparece cuando `nmcli` termina
   - B) El perfil se guarda, pero se deshabilita la activación automática; actívalo explícitamente y verifícalo antes de habilitar autoconnect
   - C) Ya está activo en todas las NIC Ethernet
   - D) Solo cambia la conexión de administración

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El perfil se guarda, pero se deshabilita la activación automática; actívalo explícitamente y verifícalo antes de habilitar autoconnect**

**Explicación:** La configuración guardada y el estado activo del dispositivo son cosas distintas. La lección asocia el perfil con la NIC/MAC verificada, activa el UUID registrado, comprueba las direcciones/rutas en tiempo de ejecución y luego habilita autoconnect para el reinicio. Que el perfil esté guardado no demuestra que se haya activado correctamente.

</details>

7. Un perfil de laboratorio antiguo muestra `DEVICE=--`. ¿Qué debes hacer antes de confiar en tu perfil nuevo tras el reinicio?
   - A) Eliminar todos los perfiles inactivos
   - B) Ignorarlo porque los perfiles inactivos nunca pueden activarse
   - C) Aumentar la prioridad de autoconnect de todos los perfiles
   - D) Inspeccionar su compatibilidad y asociaciones, registrar el estado original y deshabilitar autoconnect solo en los perfiles en conflicto confirmados como exclusivos del laboratorio

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Inspeccionar su compatibilidad y asociaciones, registrar el estado original y deshabilitar autoconnect solo en los perfiles en conflicto confirmados como exclusivos del laboratorio**

**Explicación:** Inactivo describe el estado actual. Un perfil guardado y compatible podría activarse más adelante. Un perfil sin asociación también podría servir para la NIC de administración, así que no lo cambies a ciegas. Conserva los UUID anteriores, los valores de autoconnect y el estado de activación para poder restaurarlos de forma específica.

</details>

8. Guardas una edición de `beginner-lab-static` mediante nmtui. ¿Qué debe ocurrir a continuación?
   - A) Inspeccionar el mismo perfil de NetworkManager con nmcli y volver a activar su UUID de laboratorio registrado cuando corresponda
   - B) Escribir una segunda definición de Netplan para hacer persistente la configuración de nmtui
   - C) Reiniciar todos los servicios de red
   - D) Desactivar la conexión de administración para actualizar todas las interfaces

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Inspeccionar el mismo perfil de NetworkManager con nmcli y volver a activar su UUID de laboratorio registrado cuando corresponda**

**Explicación:** nmtui y nmcli son interfaces para el mismo administrador. Guardar la configuración del perfil no equivale a aplicarla a un dispositivo ya activo. Limita la activación al perfil dedicado del laboratorio y verifica el comportamiento de gateway/DNS/ruta predeterminada.

</details>

9. ¿Dónde corresponden la gateway de ejemplo `10.77.0.1` y el resolver `10.77.0.53` de la lección?
   - A) En la NIC de administración existente NAT/DHCP como mejora automática
   - B) En la NIC aislada del curso aunque no existan esos servicios
   - C) En una máquina virtual de práctica independiente y preparada, cuyo administrador confirme que los servicios existen y cuya conexión de práctica no tenga una ruta predeterminada de administración en conflicto
   - D) En cualquier NIC después de vaciar las rutas predeterminadas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) En una máquina virtual de práctica independiente y preparada, cuyo administrador confirme que los servicios existen y cuya conexión de práctica no tenga una ruta predeterminada de administración en conflicto**

**Explicación:** Los ejemplos de gateway y DNS requieren requisitos previos reales y específicos de la ruta. De igual manera, el ejemplo de DHCP requiere una red con DHCP habilitado. No son instrucciones para agregar servicios a un laboratorio de curso aislado ni para reconfigurar su conexión de administración. Un dominio de búsqueda expande nombres; no crea registros.

</details>

10. Quieres revertir el ejercicio de NetworkManager. ¿Qué reversión conserva la configuración que no está relacionada?
    - A) Eliminar todos los perfiles Ethernet y reiniciar
    - B) Verificar y eliminar el UUID nuevo del laboratorio, restaurar el valor de autoconnect registrado de cada perfil anterior y reactivar solo el perfil que estaba activo
    - C) Vaciar todas las direcciones y rutas predeterminadas
    - D) Eliminar el perfil de administración porque se creó primero

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Verificar y eliminar el UUID nuevo del laboratorio, restaurar el valor de autoconnect registrado de cada perfil anterior y reactivar solo el perfil que estaba activo**

**Explicación:** La recuperación requiere el perfil exacto que administraste y un registro del estado anterior. Un perfil que estaba inactivo debe seguir inactivo. Inspecciona el estado resultante de enlace/dirección del laboratorio y la configuración de administración que no cambió; otros perfiles compatibles podrían activarse cuando una conexión se desconecte.

</details>

---

[Volver a la lección](../../../networking/beginner/03-persistent-configuration.md) · [Siguiente lección: DNS y conectividad](../../../networking/beginner/04-dns-connectivity.md)
