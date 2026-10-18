# Cuestionario 2. Direcciones, subredes e interfaces

> **Versiones compatibles**: Ubuntu Server 24.04 LTS (principal), Rocky Linux 9 (alternativa)
> **Última actualización**: 15 de septiembre de 2026

[Volver a la lección](../../../networking/beginner/02-addressing-interfaces.md) | [Preparación del curso](../../../networking/beginner/README.md)

Usa el acuerdo del laboratorio aislado con dos máquinas virtuales. Elige una respuesta antes de abrir su explicación. Los ejemplos sirven para interpretar, no para reconfigurar el host.

1. El cliente envía una solicitud HTTP directamente al servidor en `192.0.2.20:8080`. ¿Qué descripción es correcta?

   - A) `8080` es la dirección MAC del servidor.
   - B) Ethernet usa direcciones MAC en el enlace local, IP identifica los endpoints enrutados y el puerto TCP `8080` identifica un endpoint de transporte en el que debe escuchar un servicio.
   - C) Asignar la IP del servidor inicia HTTP automáticamente.
   - D) Los puertos TCP y UDP `8080` siempre llegan al mismo programa.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** Una trama Ethernet local contiene un paquete IP, que a su vez contiene información de transporte y datos de aplicación. Los puertos son números específicos del protocolo, no cables. La configuración de direcciones no crea ningún listener. Que responda ICMP echo tampoco demuestra que TCP `8080` esté abierto.

</details>

2. ¿Cuáles son la red, la dirección de difusión y el rango normal de hosts para `192.0.2.10/24`?

   - A) Red `.10`, dirección de difusión `.24`, hosts `.1`–`.9`.
   - B) Red `192.0.2.0`, dirección de difusión `192.0.2.255`, hosts `.1`–`.254`.
   - C) Red `192.0.0.0`, dirección de difusión `192.0.255.255`, hosts `.0`–`.255`.
   - D) Las 256 direcciones son direcciones normales de host en este laboratorio.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** `/24` reserva 24 bits para la red y deja 8 bits para hosts, es decir, 256 direcciones. En esta subred normal, los bits de host todos a cero y todos a uno identifican la dirección de red y la de difusión, respectivamente, por lo que quedan 254 direcciones de host. `/31` y `/32` tienen usos especiales y no deben forzarse dentro de este cálculo.

</details>

3. ¿Qué destino comparte la subred de `192.0.2.70/26` y por qué?

   - A) `.130`, porque coinciden los tres primeros octetos.
   - B) `.100`, porque el bloque `.64/26` abarca `.64`–`.127`, con hosts `.65`–`.126`.
   - C) `.20`, porque cualquier dirección de documentación es local.
   - D) `.127`, porque la dirección de difusión de una subred es la recomendada para servidores.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** `/26` deja 6 bits para hosts, así que los bloques contienen 64 direcciones y comienzan en `.0`, `.64`, `.128` y `.192`. `.70` y `.100` pertenecen al segundo bloque. `.130` pertenece al tercero. Compara el prefijo real en lugar de suponer que todas las redes son `/24`.

</details>

4. El cliente tiene una ruta predeterminada de administración y una ruta conectada `192.0.2.0/24` en la NIC del laboratorio. ¿Por dónde debe salir un paquete destinado a `.20`?

   - A) Por la ruta predeterminada de administración, porque la ruta predeterminada siempre tiene prioridad.
   - B) Directamente por la NIC del laboratorio, porque `/24` es un prefijo coincidente más largo que `/0`.
   - C) Por `.1`, que es una gateway automática.
   - D) A ningún sitio hasta que se configure DNS en la NIC del laboratorio.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** La ruta conectada es más específica. No se necesita gateway ni DNS del laboratorio para el tráfico con una IP literal dentro de la misma subred. Conserva la ruta predeterminada de administración existente. Una gateway debe existir y ser accesible; una dirección que termina en `.1` no es intrínsecamente un router.

</details>

5. ¿Qué asignación de responsabilidades es correcta?

   - A) DHCP reenvía todos los paquetes, DNS asigna la MAC del cliente y ARP resuelve nombres.
   - B) DHCP puede conceder una dirección/configuración, DNS responde consultas de registros de nombres y ARP resuelve un vecino IPv4 del siguiente salto a su MAC en el enlace.
   - C) Que DNS funcione demuestra que se puede acceder a todos los servicios.
   - D) ARP descubre la MAC de cualquier servidor en Internet.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** Para llegar mediante un router a un destino IPv4 remoto, ARP normalmente resuelve la MAC del router en el enlace local, no la del servidor remoto. DHCP intercambia configuración. DNS resuelve nombres. Responden preguntas distintas y pueden funcionar o fallar de forma independiente.

</details>

6. Antes de agregar una dirección, ¿qué evidencia identifica de forma fiable la NIC del laboratorio?

   - A) Siempre es `eth1`.
   - B) Es la segunda línea que no corresponde a loopback en `ip a`.
   - C) Su MAC completa coincide con la NIC registrada por el hipervisor y conectada a la red interna aislada.
   - D) Ya tiene la ruta predeterminada.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

**Explicación:** Los nombres y el orden de los dispositivos invitados varían. Registra por separado las MAC de administración y del laboratorio de cada máquina virtual, y compáralas con `ip -br link`. Una ruta predeterminada suele identificar la ruta de administración, que debe quedar intacta. La NIC del laboratorio también debe cumplir el requisito previo de no tener una IPv4 existente antes de que el ejercicio agregue una dirección.

</details>

7. ¿Qué hace `ip a` y qué puede significar `UP` sin `LOWER_UP`?

   - A) `ip a` agrega una dirección y `UP` demuestra que hay acceso a Internet.
   - B) `ip a` enumera las direcciones; un enlace habilitado administrativamente aún puede no tener portadora de la capa inferior.
   - C) Ambas expresiones significan que DNS funciona.
   - D) `UNKNOWN` en loopback siempre significa que el entorno invitado está defectuoso.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** `a` es una abreviatura del objeto address; para agregar una dirección se necesita la operación `add`. La habilitación administrativa, la portadora, la asignación de direcciones, el enrutamiento y la accesibilidad de servicios son observaciones distintas. Si falta portadora, inspecciona el cable virtual y la conexión de red antes de modificar la configuración IP.

</details>

8. `ip -4 route get 192.0.2.20` selecciona la NIC del laboratorio con origen `.10`, pero ping no recibe respuesta. ¿Qué ha demostrado la consulta de ruta?

   - A) El par recibió un paquete.
   - B) El kernel seleccionaría esa ruta y ese origen; esta consulta no envió ningún paquete de prueba.
   - C) El firewall permite ICMP y TCP.
   - D) ARP necesariamente resolvió el par.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** La selección de ruta es evidencia local. Después de un ping acotado, inspecciona los vecinos para distinguir entre la resolución local del enlace que no se completa y una ruta donde se resuelve la MAC, pero quizá se filtra ICMP. No confundas una decisión de enrutamiento con el éxito de extremo a extremo ni deshabilites un firewall para ocultar el síntoma.

</details>

9. Después del tráfico, una entrada de vecino tiene la MAC del par esperada y el estado `STALE`. ¿Qué significa?

   - A) La interfaz ha quedado inutilizable permanentemente.
   - B) Hay una asociación en caché que debe volver a confirmarse cuando se use; esto no indica un fallo inmediato.
   - C) Alguien necesariamente falsificó la identidad del par.
   - D) Hay que vaciar todas las entradas de vecinos.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** El estado del vecino cambia según se confirme su accesibilidad. `REACHABLE` significa que se confirmó hace poco, `INCOMPLETE` indica que se está resolviendo y `FAILED` que falló la resolución. Una tabla vacía antes del tráfico puede ser normal. Compara las MAC con tus registros y usa observaciones del tráfico en vez de exigir que todas las entradas en caché siempre indiquen `REACHABLE`.

</details>

10. Agregaste una dirección manual y se muestra `valid_lft forever`. ¿Sobrevivirá al reinicio y qué debe eliminar la limpieza?

   - A) Sí; elimina toda la tabla de direcciones del sistema invitado.
   - B) No significa que sea persistente; elimina la IP/prefijo exactos que se agregaron correctamente de la NIC de laboratorio identificada y restaura el estado down solo si esa NIC estaba down originalmente.
   - C) Sí; solo reinstalar Linux puede eliminarla.
   - D) Elimina primero la ruta predeterminada de administración.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** `forever` significa que no hay un temporizador de expiración en tiempo de ejecución, no que se haya guardado una configuración. Si se cumple el requisito previo de la lección de no tener IPv4, quitar la única dirección IPv4 del laboratorio también elimina su ruta conectada creada automáticamente. Si un reinicio o un administrador ya quitó la dirección, confirma su ausencia y omite la eliminación. Recupera las variables registradas y el estado original en vez de adivinar.

</details>

11. Ves una dirección IPv6 que empieza por `fe80:` en la NIC del laboratorio. ¿Qué respuesta es adecuada?

   - A) Deshabilitar IPv6 globalmente para que funcione IPv4.
   - B) Considerarla probablemente de enlace local, dejar intacto el IPv6 existente y continuar con el ejercicio IPv4.
   - C) Suponer que hay acceso a Internet porque todas las direcciones IPv6 son globales.
   - D) Configurar una entrada ARP de IPv4 para ella.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** IPv6 tiene direcciones de 128 bits; el alcance de enlace local se limita a su enlace y puede requerir una zona de interfaz al usarla como destino. IPv6 utiliza Neighbor Discovery en lugar de ARP y no tiene difusión al estilo IPv4. Una dirección de enlace local por sí sola no demuestra que haya acceso a Internet.

</details>

12. ¿Qué afirmación de finalización es honesta y completa?

   - A) «Los ejemplos se probaron en vivo porque leí los comandos».
   - B) «Existe la dirección del laboratorio, así que funcionan todos los servicios TCP».
   - C) «Verifiqué por MAC las dos NIC del laboratorio, las direcciones/rutas y las pruebas acotadas de accesibilidad; conservé la administración y luego eliminé solo mi dirección y restauré el estado de enlace registrado».
   - D) «Una red solo de host siempre está aislada y nunca tiene DHCP».

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

**Explicación:** El acuerdo incluye configuración, evidencia y recuperación. La red interna aislada del laboratorio no tiene DHCP ni salida; no se debe suponer que los valores predeterminados de una red solo de host sean equivalentes. Los ejemplos de la lección son ilustrativos, no transcripciones de pruebas en vivo. La siguiente lección configura persistencia sin depender de variables residuales.

</details>

Vuelve a comprobar cualquier resultado incierto en la [lección](../../../networking/beginner/02-addressing-interfaces.md) y luego continúa con la [configuración persistente](../../../networking/beginner/03-persistent-configuration.md).
