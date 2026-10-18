# 2. Direcciones, subredes e interfaces de red

> **Versiones compatibles**: Ubuntu Server 24.04 LTS (principal), Rocky Linux 9 (alternativa)
> **Última actualización**: 15 de septiembre de 2026

[Anterior: Terminal Linux](01-linux-cli.md) | [Preparación del curso](README.md) | [Cuestionario](../../quizzes/networking/beginner/02-addressing-interfaces-quiz.md) | [Siguiente: Configuración persistente](03-persistent-configuration.md)

Una interfaz de red puede tener un cable y una dirección y aun así no alcanzar un servicio. Son capas distintas del problema. En esta lección primero seguiremos un mensaje por esas capas y luego crearemos una pequeña red IPv4 local para que puedas ver la diferencia por ti mismo.

## Requisitos previos y objetivos

Completa la [lección 1](01-linux-cli.md): utiliza con soltura una cuenta normal, `sudo`, variables, un directorio temporal único y la consola de la VM. Empieza con dos VM locales desechables. Ambas pueden ejecutar Ubuntu Server 24.04 LTS, o puedes usar Rocky Linux 9 como ruta administrativa alternativa. Estos comandos usan `iproute2` (paquete `iproute` en Rocky) y `ping` de iputils; tenlos disponibles antes del ejercicio. En esta lección no se instala ningún paquete.

Prepara lo siguiente en el hipervisor como se explica en la [preparación del curso](README.md). «Solo interna» significa que ambas NIC virtuales se conectan a **la misma red virtual aislada**, sin servidor DHCP, router ni enlace ascendente externo. Una red solo de host no es necesariamente equivalente: algunos hipervisores pueden darle acceso al host o DHCP.

| Función del sistema invitado | NIC de administración existente | NIC independiente para el laboratorio interno |
| --- | --- | --- |
| Cliente | Conexión NAT/DHCP existente, sin cambios | `192.0.2.10/24`, sin gateway ni DNS |
| Servidor | Conexión NAT/DHCP existente, sin cambios | `192.0.2.20/24`, sin gateway ni DNS |

Anota desde la configuración del hipervisor las direcciones MAC de **ambas NIC de cada sistema invitado**, además de la red virtual a la que se conecta cada una. Usa direcciones MAC distintas para las dos VM. Deja abiertas sus consolas. El bloque `192.0.2.0/24` está reservado para documentación (RFC 5737); úsalo solo en este laboratorio aislado, nunca como destino real de Internet. No conectes la NIC del laboratorio a la red de tu casa, empresa o nube.

Al terminar, podrás:

- Distinguir tramas Ethernet, paquetes IP, puertos de transporte y servicios de aplicación.
- Calcular un límite de subred y decidir si un destino es local o requiere un router.
- Explicar qué hace cada uno de estos elementos: gateway, DHCP, DNS, ARP y la detección de vecinos IPv6.
- Relacionar una interfaz del sistema invitado con la NIC correcta del hipervisor sin adivinar su nombre.
- Inspeccionar enlaces, direcciones, rutas y vecinos, añadir una dirección IPv4 temporal a cada NIC de laboratorio y deshacer exactamente esos cambios.

**Contrato de ejecución:** ejecuta comandos solo **dentro de la VM de práctica indicada**, como usuario normal salvo que una línea incluya `sudo`. Nunca configures el host físico ni el host de documentación. Las líneas que dicen «cada VM» se ejecutan por separado desde la consola de cada VM; las variables son locales a ese shell. Los ejemplos son ilustrativos, **no son resultados de VM probados en vivo**. Detente ante un error inesperado antes de continuar.

## Sigue un mensaje desde la aplicación hasta el cable

Imagina un ejercicio posterior en el que el cliente solicita al servidor una página web en el puerto TCP `8080`. Para ello debe haber un servidor web escuchando allí; asignar una dirección IP no lo crea.

| Capa | Qué transporta o identifica | Ejemplo en nuestra red local de laboratorio |
| --- | --- | --- |
| Aplicación | Significado de la solicitud y la respuesta | Solicitud HTTP de una página |
| Transporte | Extremos de comunicación TCP o UDP mediante números de puerto | Puerto de origen TCP temporal del cliente hacia el puerto TCP `8080` del servidor |
| Internet | Paquete IP con direcciones de origen/destino para el enrutamiento | De `192.0.2.10` a `192.0.2.20` |
| Enlace local | Trama Ethernet con direcciones MAC de origen/destino | MAC de la NIC de laboratorio del cliente hacia la MAC de la NIC de laboratorio del servidor |

El emisor encapsula los datos de aplicación con información de transporte, luego en un paquete IP y, por último, en una trama para el enlace actual. El receptor quita esas envolturas. Las tramas transportan tráfico por un enlace; los routers reenvían paquetes IP entre redes. En un router, la trama de capa de enlace se sustituye para el siguiente enlace. Este sencillo laboratorio no necesita un router entre los sistemas invitados.

Una **dirección MAC** identifica una interfaz Ethernet en su enlace; una NIC virtual también tiene una. Una **dirección IP más un prefijo** indica al host cómo ubicar una interfaz en una red IP. Una NIC puede tener varias direcciones. Ninguna de las dos direcciones demuestra la identidad de una persona.

Un **puerto** es un número de 16 bits de TCP o UDP, no el conector físico de la VM. El puerto TCP `8080` y el puerto UDP `8080` son extremos distintos. El protocolo, la IP/puerto de origen y la IP/puerto de destino distinguen una conversación. Que una IP sea alcanzable no significa que un puerto elegido esté escuchando o que el firewall lo permita. ICMP, usado por `ping`, no utiliza números de puerto TCP/UDP. Probaremos servicios de aplicación en lecciones posteriores.

## Calcula IPv4 y CIDR en lugar de memorizarlos

Las direcciones IPv4 tienen 32 bits, normalmente escritos como cuatro octetos decimales, cada uno entre `0` y `255`. Una **longitud de prefijo**, que se escribe después de `/`, indica cuántos bits iniciales describen la red. Los bits restantes distinguen las direcciones dentro de ella. Esta notación con barra se llama notación CIDR.

Para `192.0.2.10/24`, los primeros 24 bits son la red y quedan 8 bits:

| Cálculo | Resultado |
| --- | --- |
| Máscara de prefijo: 24 bits uno y luego 8 bits cero | `255.255.255.0` |
| Dirección con todos los bits de host en cero | Dirección de red `192.0.2.0` |
| Dirección con todos los bits de host en uno | Dirección de broadcast `192.0.2.255` |
| Número de direcciones | `2^(32-24) = 256` |
| Rango de hosts ordinarios de esta subred | `192.0.2.1`–`192.0.2.254` |

Aquí no se asignan a hosts ordinarios las dos direcciones de los extremos, por lo que quedan 254 direcciones de host. Los casos especiales `/31` punto a punto y `/32` siguen reglas distintas y quedan fuera de este primer laboratorio. `.10/24` y `.20/24` pertenecen ambos a `192.0.2.0/24`. `192.0.3.20` queda fuera, aunque coincidan los dos primeros octetos.

Para un ejemplo menos evidente, considera **`192.0.2.70/26`**:

1. `/26` deja 6 bits de host, lo que da bloques de `2^6 = 64` direcciones.
2. La máscara es `255.255.255.192`. Su último octeto en binario es `11000000`.
3. El último octeto de `.70` es `01000110`. Conserva sus dos primeros bits y pon el resto a cero: queda `01000000`, o `.64`.
4. Por tanto, los bloques empiezan en `.0`, `.64`, `.128` y `.192`. La dirección `.70` pertenece al bloque `.64`.
5. Su red es `192.0.2.64/26`, el broadcast es `.127` y el rango de hosts ordinarios es `.65`–`.126` (62 direcciones de host).

Así, `.100/26` comparte subred con `.70/26`, pero `.130/26` no. Que coincidan los tres primeros octetos no basta, salvo que el prefijo sea `/24`. Un número de prefijo mayor implica un bloque de direcciones menor. En el laboratorio real usa `/24`, no el ejemplo de cálculo `/26`.

## Gateway, DHCP, DNS y vecinos responden preguntas distintas

Una **ruta** indica al kernel adónde enviar un paquete. Una ruta directamente conectada dice «este destino está en el enlace de esa interfaz». Una ruta que incluye `via` selecciona un router de siguiente salto, normalmente llamado **gateway**. Si coinciden varias rutas, primero gana el prefijo coincidente más largo. Una **ruta predeterminada** (`0.0.0.0/0`, mostrada como `default`) es la alternativa cuando no coincide ninguna ruta más específica.

Cuando `.10` envía a `.20` en nuestra `/24`, la ruta conectada es más específica que una ruta predeterminada de administración. El cliente envía directamente por el enlace de laboratorio. **No hay que introducir un gateway para el laboratorio**, y `.1` no es automáticamente un router. Conserva la ruta predeterminada de administración existente.

| Mecanismo | Pregunta que responde | Lo que no demuestra |
| --- | --- | --- |
| DHCP | «¿Puede un servidor de configuración asignarme una dirección y proporcionar opciones como rutas/DNS?» | Que se esté ejecutando un servicio web |
| DNS | «¿Qué dirección u otro registro corresponde a este nombre?» | Que exista una ruta o un servicio escuchando |
| ARP IPv4 | «¿Qué dirección MAC corresponde actualmente a este vecino IPv4 de mi enlace?» | Que el vecino acepte una conexión TCP |

DHCP es un intercambio de configuración, no el acto de reenviar todos los paquetes. DNS resuelve nombres; no asigna la propia dirección IP del cliente. En un trayecto IPv4 hacia otra subred, ARP normalmente obtiene la **MAC del gateway de siguiente salto**, no la MAC de un servidor remoto a través de Internet.

La NIC del laboratorio no tiene servidor DHCP ni necesita gateway o DNS para comunicarse con una IP literal. La NIC de administración independiente puede seguir usando su configuración DHCP existente. No cambiaremos ni su dirección ni sus ajustes del resolver.

IPv6 usa direcciones de **128 bits** escritas en grupos hexadecimales separados por dos puntos. Se pueden omitir los ceros iniciales de un grupo y `::` puede comprimir una secuencia de grupos compuestos solo por ceros. `::1` es loopback; una dirección que empieza por `fe80:` suele ser de enlace local y solo se puede usar en ese enlace. Varias interfaces pueden tener direcciones de enlace local, por lo que el destino podría necesitar una zona como `%interface-name` para identificar el enlace. Los nombres de interfaz deben obtenerse del sistema invitado, no de este ejemplo.

`2001:db8::/32` es espacio IPv6 para documentación (RFC 3849), no una dirección que debas configurar aquí. Los prefijos ordinarios de LAN IPv6 suelen ser `/64`. IPv6 usa Neighbor Discovery de ICMPv6 en lugar de ARP y no tiene broadcast como IPv4. Los anuncios de router, SLAAC y DHCPv6 son temas de configuración separados. Una dirección IPv6 de enlace local por sí sola no demuestra acceso a Internet. Mantén habilitada y sin cambios la configuración IPv6 existente mientras haces el ejercicio IPv4.

## Inspecciona antes de seleccionar una interfaz

El comando moderno `ip` agrupa objetos relacionados: `link` para dispositivos, `address` (también `addr` o `a`) para direcciones, `route` para enrutamiento y `neigh` para la tabla de vecinos. Normalmente no hace falta `sudo` para leerlos.

**Cada VM, usuario normal; solo inspección:**

```bash
hostname
ip -br link
ip -br address
ip a
ip -4 route
ip neigh
```

`-br` solicita una salida breve. `-4` limita el comando a IPv4; sin él, `ip a` también muestra IPv6. `ip a` es una forma abreviada de `ip address`, no un comando para añadir una dirección.

Salida breve ilustrativa **con etiquetas que sustituyen los nombres reales de las interfaces**:

```text
lo            UNKNOWN  00:00:00:00:00:00 <LOOPBACK,UP,LOWER_UP>
<management>  UP       02:00:00:00:01:10 <BROADCAST,MULTICAST,UP,LOWER_UP>
<lab>         DOWN     02:00:00:00:02:10 <BROADCAST,MULTICAST>
```

Lee cada fila como nombre de interfaz, estado operativo, dirección MAC y luego flags. Compara la **MAC completa** con el registro del hipervisor, por separado para cada sistema invitado. El orden de las NIC, la conexión PCI, los ajustes de imagen y las reglas de nombres del SO pueden cambiar los nombres. Ni «la segunda fila» ni adivinar `eth1`/`ens19` es fiable. `lo` es loopback dentro del sistema invitado y no es una NIC Ethernet virtual.

El flag `UP` significa habilitada administrativamente. `LOWER_UP` indica carrier de capa inferior. Un dispositivo puede estar habilitado administrativamente pero carecer de carrier; en ese caso inspecciona el cable virtual y la conexión a la red interna. El estado operativo mostrado como `UNKNOWN`, sobre todo en loopback, no es automáticamente un fallo. Guarda el estado administrativo original antes de cambiar nada.

## Registra el límite y la línea base en cada VM

**Cada VM, usuario normal; escribe los nombres reales cuando se solicite:**

```bash
read -r -p 'Lab NIC name matched by MAC: ' LAB_IF
read -r -p 'Management NIC name matched by MAC: ' MGMT_IF
ip -br link show dev "$LAB_IF"
ip -br link show dev "$MGMT_IF"
ip -4 address show dev "$LAB_IF"
ip -4 route show table main
```

`read` guarda tu entrada en una variable del shell; no cambia ninguna interfaz. Si falta un nombre, no existe un dispositivo, los nombres son iguales o alguna MAC no coincide con tu registro, detente y repite la identificación. No continúes solo porque un comando acepte el nombre.

**Comprobación previa al cambio:** la NIC del laboratorio **no debe tener ninguna dirección IPv4 asignada** y el sistema invitado no debe tener ninguna ruta IPv4 existente que se solape con `192.0.2.0/24`, salvo la ruta predeterminada de administración (`default`), que es lo esperado. Una dirección IPv6 de enlace local existente está bien. Si la NIC del laboratorio ya tiene una IPv4 o aparece una ruta inesperada, detente y revisa la preparación del curso; no elimines estado desconocido ni reutilices una dirección que pertenezca a un administrador de red. La gestión de red de los sistemas invitados puede reemplazar después el estado manual, por eso el ejercicio es temporal.

Crea un lugar donde guardar la línea base. Hazlo por separado en los dos sistemas invitados.

**Cada VM, usuario normal:**

```bash
NET_NOTE_DIR=$(mktemp -d "$HOME/network-beginner-ip.XXXXXX")
printf '%s\n' "$NET_NOTE_DIR"
```

Registra esta ruta exacta. Detente si falla la creación o el valor queda vacío. Luego guarda la línea base:

```bash
ip -details link show dev "$LAB_IF" > "$NET_NOTE_DIR/lab-link.before"
ip -4 -br address show dev "$MGMT_IF" > "$NET_NOTE_DIR/management-addresses.before"
ip -4 route show table main > "$NET_NOTE_DIR/routes.before"
cat "$NET_NOTE_DIR/lab-link.before"
```

`>` escribe la salida en el archivo nombrado y reemplaza un archivo existente con ese nombre; aquí el directorio es nuevo. En los flags del enlace, determina si aparece el **flag independiente `UP`**. `LOWER_UP` por sí solo no es suficiente. Registra el resultado con **una** de estas asignaciones, en el shell de esa VM:

```bash
# Use this only if the standalone UP flag was present:
LAB_LINK_WAS=up
```

```bash
# Otherwise use this:
LAB_LINK_WAS=down
```

Registra también fuera del shell el estado original, las MAC, los nombres de interfaz y el directorio de línea base. Los necesitarás para limpiar si pierdes la sesión.

## Añade las dos direcciones temporales

Elige **un bloque de función por VM**. Estas asignaciones solo guardan texto. No intercambies por accidente las direcciones de cliente y servidor ni las asignes a ambas VM.

**Solo VM cliente, usuario normal:**

```bash
LAB_IP=192.0.2.10
LAB_CIDR=192.0.2.10/24
LAB_PEER=192.0.2.20
```

**Solo VM servidor, usuario normal:**

```bash
LAB_IP=192.0.2.20
LAB_CIDR=192.0.2.20/24
LAB_PEER=192.0.2.10
```

Vuelve a comprobar el destino antes de elevar privilegios.

**Cada VM, usuario normal:**

```bash
printf 'guest=%s lab=%s management=%s address=%s original-link=%s\n' \
  "$(hostname)" "$LAB_IF" "$MGMT_IF" "$LAB_CIDR" "$LAB_LINK_WAS"
ip -br link show dev "$LAB_IF"
```

Compara el resultado con tu función y la MAC registrada. Después, **en cada VM, como usuario normal que invoca sudo**, añade solo la dirección de laboratorio de esa VM:

```bash
sudo ip link set dev "$LAB_IF" up
sudo ip address add "$LAB_CIDR" dev "$LAB_IF"
```

`link set ... up` habilita administrativamente la NIC de laboratorio identificada; no modifica la NIC de administración. `address add` asigna una dirección adicional al sistema invitado **en su NIC secundaria**. No significa «añadir una segunda dirección IPv4 a la NIC de administración» ni requiere que Linux muestre un flag `secondary`.

Una asignación correcta normalmente no imprime nada. Si aparece `File exists`, inspecciona las direcciones y detente en vez de cambiar a `replace` o vaciar la interfaz. Si habilitaste la NIC de laboratorio que estaba inicialmente inactiva pero falló la asignación, la parte de limpieza sobre el estado del enlace que aparece abajo sigue siendo aplicable; elimina una dirección solo si la añadiste tú correctamente.

Este cambio de `ip` actualiza el estado actual del kernel, no la configuración de Netplan ni NetworkManager. Un reinicio elimina el estado añadido manualmente; un administrador de red podría eliminar o recrear las direcciones antes. Una duración de dirección mostrada como `forever` significa que esta dirección en ejecución no tiene temporizador de vencimiento, **no** que persista después de reiniciar. La configuración persistente es el tema de la siguiente lección.

## Interpreta el resultado en cada capa

**Cada VM, usuario normal; solo inspección:**

```bash
ip -br link show dev "$LAB_IF"
ip -4 address show dev "$LAB_IF"
ip -4 route show dev "$LAB_IF"
ip -4 route get "$LAB_PEER"
```

En el cliente, las líneas ilustrativas pertinentes podrían ser:

```text
inet 192.0.2.10/24 scope global <lab-name>
    valid_lft forever preferred_lft forever
192.0.2.0/24 dev <lab-name> proto kernel scope link src 192.0.2.10
192.0.2.20 dev <lab-name> src 192.0.2.10 uid 1000
```

La dirección indica «esta NIC posee `.10/24`». `scope global` es la etiqueta de alcance de direcciones de Linux; no convierte una dirección de documentación en una dirección accesible globalmente. De forma predeterminada, añadir la dirección también crea una ruta para su prefijo conectado. `proto kernel` identifica esa ruta creada automáticamente, `scope link` indica que no se requiere un router de siguiente salto y `src` proporciona una dirección de origen preferida. De forma similar, el servidor debe poseer `.20/24` y seleccionar `.20` como origen.

`ip route get` pregunta al kernel cómo enrutaría hacia un destino; **no envía paquetes de prueba**. Para el par debe seleccionar la NIC de laboratorio, el origen local correcto y no indicar ningún gateway `via`. Una ruta por la NIC de administración indica un error de configuración aunque funcione alguna otra forma de conectividad. Si falta una ruta conectada o desaparece una dirección, inspecciona el estado del enlace y quién administra la interfaz; no añadas una ruta predeterminada que compita.

Después de configurar **ambos** sistemas invitados, genera un poco de tráfico para que ARP tenga motivos para resolver el par.

**Cada VM, usuario normal:**

```bash
ping -4 -c 3 -W 2 -I "$LAB_IF" "$LAB_PEER"
ip -4 neigh show dev "$LAB_IF"
```

`ping -4` usa eco ICMP IPv4, `-c 3` limita la prueba a tres solicitudes, `-W 2` establece el timeout de respuesta en segundos y `-I` selecciona la interfaz de laboratorio. El empaquetado habitual de iputils permite ejecutar esta prueba de eco como usuario normal. Un error de permisos corresponde a la configuración de la herramienta/capacidades; no demuestra que la red esté caída.

En una ruta correctamente configurada que permita ICMP, espera respuestas y un resumen de paquetes transmitidos/recibidos. La latencia varía; no copies de un ejemplo una latencia supuestamente medida. Una entrada de vecino ilustrativa:

```text
192.0.2.20 dev <lab-name> lladdr 02:00:00:00:02:20 REACHABLE
```

Compara `lladdr` con la **MAC de la NIC de laboratorio del par** que registraste en el hipervisor. `REACHABLE` significa que se confirmó hace poco; `STALE` significa que existe una asignación en caché, pero necesita reconfirmarse cuando se use, no que haya fallado inmediatamente. Una tabla vacía antes de generar tráfico es normal. `INCOMPLETE` significa que la resolución está en curso; `FAILED` indica que falló. Las entradas son dinámicas, así que el estado puede cambiar mientras lo lees.

| Observación | Siguiente comprobación en esta lección |
| --- | --- |
| Sin carrier / sin `LOWER_UP` | Cable virtual del hipervisor y conexión a la red interna correcta |
| Dirección IPv4 ausente o incorrecta | Variables de función, resultado de la asignación y posible cambio de la NIC por un administrador |
| La ruta al par usa la NIC de administración | Prefijo, dirección de laboratorio y consulta de ruta |
| El vecino permanece `INCOMPLETE`/`FAILED` | Ambas VM en ejecución, misma red interna, dirección del par, MAC e IP únicas |
| Se resuelve la MAC del vecino, pero ping no recibe respuesta | Estado del par y filtrado de ICMP; que ARP funcione no significa que ICMP o el servicio funcionen |

No deshabilites firewalls ni IPv6 para hacer que esta primera prueba pase. Guarda la evidencia y, si hace falta, continúa con el método de diagnóstico de la lección 4 y la política de firewall de la lección 6.

## Comprobación de éxito y limpieza exacta

Antes de deshacer nada, verifica en **ambos sistemas invitados** que:

1. La comparación de MAC identifica por separado las interfaces de administración y laboratorio.
2. La NIC de laboratorio tiene exactamente la dirección `/24` de la función y una ruta conectada `192.0.2.0/24`.
3. La ruta al par usa la NIC de laboratorio y el origen correcto, sin gateway.
4. Comprendes la evidencia de vecino; una respuesta ICMP satisfactoria demuestra esta prueba IP limitada, no que haya un servicio TCP abierto.
5. La dirección de administración, la ruta predeterminada y el acceso de administración original siguen coincidiendo con la línea base registrada.

**Cada VM, usuario normal; compara los datos de administración guardados/actuales:**

```bash
cat "$NET_NOTE_DIR/management-addresses.before"
ip -4 -br address show dev "$MGMT_IF"
cat "$NET_NOTE_DIR/routes.before"
ip -4 route show table main
```

La nueva ruta conectada del laboratorio es esperada; una ruta predeterminada nueva del laboratorio no lo es. DHCP podría renovar de forma independiente la concesión de administración, así que compara la interfaz, la dirección, el gateway y el propósito de las rutas, en vez de tratar cada detalle dinámico como un cambio del laboratorio.

Practica ahora la reversión, por separado en cada VM. Si perdiste el shell, vuelve a identificar primero las NIC por las MAC registradas y restaura `LAB_IF`, `MGMT_IF`, `LAB_IP`, `LAB_CIDR`, `LAB_LINK_WAS` y `NET_NOTE_DIR` desde el registro **de ese sistema invitado**. Inspecciona el estado actual; las variables no se conservan automáticamente. No adivines qué dirección eliminar.

**Cada VM, usuario normal; verifica que la dirección añadida por ti aún esté presente:**

```bash
ip -4 address show dev "$LAB_IF"
```

**Cada VM, usuario normal que invoca sudo; elimina solo la dirección que añadió esa VM:**

```bash
sudo ip address del "$LAB_CIDR" dev "$LAB_IF"
```

Ejecuta la eliminación solo si la asignación fue correcta y la dirección aún está presente. Si ya reiniciaste o un administrador de red la eliminó, omite la eliminación después de confirmar su ausencia. Esta es una operación inversa dirigida: especifica la IP, el prefijo y la interfaz exactos. No se vacía ninguna dirección ni ruta. Dada la condición previa de IPv4 vacío, eliminar la única dirección IPv4 del laboratorio también quita su ruta conectada creada automáticamente.

**Cada VM, mismo shell, usuario normal que invoca sudo solo cuando sea necesario:**

```bash
if [ "$LAB_LINK_WAS" = down ]; then
  sudo ip link set dev "$LAB_IF" down
fi
```

Esta condición restaura un enlace que **tú** activaste cuando estaba inactivo. Si ya estaba activo, déjalo así. `[` comprueba el valor registrado; solo se ejecuta la rama `down` con el comando privilegiado. Si falta ese valor, recupera el registro en vez de inventar un estado original.

**Cada VM, usuario normal; verifica la recuperación:**

```bash
ip -br link show dev "$LAB_IF"
ip -4 address show dev "$LAB_IF"
ip -4 route show dev "$LAB_IF"
ip -4 -br address show dev "$MGMT_IF"
ip -4 route show default
```

Espera que no haya dirección IPv4 ni ruta conectada del laboratorio, el estado administrativo original del enlace y la configuración/acceso de administración originales. Las entradas dinámicas de vecinos pueden caducar; no vacíes una tabla para que parezca vacía. Si reaparece una dirección, podría pertenecer a un administrador: pausa e investiga la configuración persistente en vez de borrarla repetidamente.

Cuando ya no necesites la línea base, elimina solo sus tres archivos y el directorio vacío.

**Cada VM, usuario normal:**

```bash
rm -i -- "$NET_NOTE_DIR/lab-link.before" \
  "$NET_NOTE_DIR/management-addresses.before" "$NET_NOTE_DIR/routes.before"
rmdir -- "$NET_NOTE_DIR"
test ! -e "$NET_NOTE_DIR"
echo $?
unset LAB_IF MGMT_IF LAB_IP LAB_CIDR LAB_PEER LAB_LINK_WAS NET_NOTE_DIR
```

Confirma que sean solo tus tres archivos de texto de snapshot. El código de salida `0` de la comprobación de existencia significa que la limpieza tuvo éxito; si falla `rmdir`, inspecciona los nombres exactos restantes. No se modificó configuración persistente de red. La [lección 3](03-persistent-configuration.md) volverá a establecer las mismas direcciones mediante el administrador de red real; no debe depender de variables ni de estado temporal que permanezca en este shell.

## Referencias y lecturas adicionales

Documentación principal consultada del 14 al 15 de septiembre de 2026:

- [Manual `ip-address` de Ubuntu 24.04](https://manpages.ubuntu.com/manpages/noble/man8/ip-address.8.html), [`ip-link`](https://manpages.ubuntu.com/manpages/noble/man8/ip-link.8.html), [`ip-route`](https://manpages.ubuntu.com/manpages/noble/man8/ip-route.8.html) e [`ip-neighbour`](https://manpages.ubuntu.com/manpages/noble/man8/ip-neighbour.8.html): sintaxis de comandos, rutas conectadas, duración de direcciones y estados de vecinos.
- [Manual `ping` de Ubuntu 24.04](https://manpages.ubuntu.com/manpages/noble/man8/ping.8.html): pruebas de eco acotadas y selección de interfaz.
- [IETF RFC 1122](https://www.rfc-editor.org/rfc/rfc1122.html), [RFC 4632](https://www.rfc-editor.org/rfc/rfc4632.html) y [RFC 826](https://www.rfc-editor.org/rfc/rfc826.html): capas de Internet, CIDR y resolución de direcciones IPv4.
- [IETF RFC 2131](https://www.rfc-editor.org/rfc/rfc2131.html) y [RFC 1034](https://www.rfc-editor.org/rfc/rfc1034.html): DHCP y DNS tienen responsabilidades distintas.
- [IETF RFC 5737](https://www.rfc-editor.org/rfc/rfc5737.html) y [RFC 3849](https://www.rfc-editor.org/rfc/rfc3849.html): bloques de direcciones reservados para documentación.
- [IETF RFC 4291](https://www.rfc-editor.org/rfc/rfc4291.html) y [RFC 4861](https://www.rfc-editor.org/rfc/rfc4861.html): direccionamiento IPv6 y Neighbor Discovery.

Haz el [cuestionario](../../quizzes/networking/beginner/02-addressing-interfaces-quiz.md) y luego continúa con la [Configuración persistente](03-persistent-configuration.md).
