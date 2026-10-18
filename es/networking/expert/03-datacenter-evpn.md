# 03. EVPN de centro de datos: aislamiento y evidencia del plano de datos

> **Última actualización**: 15 de septiembre de 2026
> **Límites del laboratorio**: máquinas virtuales Linux propias, desechables y preparadas por separado para el fabric; no se usan un fabric de producción ni recursos de nube.
> **Estado de verificación**: se revisaron la documentación oficial, la topología upstream y las fuentes de CLI/plantillas de FRR; estos laboratorios **no se ejecutaron** durante la redacción.

Una sesión BGP de EVPN establecida es una observación inicial, no una certificación de que el fabric funcione.
Este cuaderno te pide seguir una trama o un paquete por su VLAN, VNI, VRF y underlay, y después demostrar el aislamiento y la restauración.
Completa primero [las ocho lecciones para principiantes](../beginner/README.md) y la [política de enrutamiento](02-routing-policy-convergence.md).
Consulta los [fundamentos de la pila de red de Linux](../../kernel/02-network-stack.md) para interpretar la evidencia de bridges, vecinos y rutas del kernel.

## 1. Lee la arquitectura por capas

| Lectura principal | Entregable antes de tocar el laboratorio |
|---|---|
| [Módulo EVPN de netlab](https://netlab.tools/module/evpn/) | Una lista de comprobación de funciones y proveedores para los dispositivos seleccionados |
| [Plataformas compatibles con netlab](https://netlab.tools/platforms/) y [advertencias de FRR](https://netlab.tools/caveats/#frrouting) | Explica por qué FRR dentro de un contenedor sigue dependiendo del kernel de la VM |
| [EVPN de FRR](https://docs.frrouting.org/en/latest/evpn.html) | Relaciona un bridge de Linux, una interfaz VXLAN, una SVI y una VRF con los conceptos de EVPN |
| [RFC 7348](https://www.rfc-editor.org/rfc/rfc7348.html), [RFC 7432](https://www.rfc-editor.org/rfc/rfc7432.html) | Dibuja la encapsulación y distingue la identidad de ruta de la política de importación |
| [RFC 9135](https://www.rfc-editor.org/rfc/rfc9135.html), [RFC 9136](https://www.rfc-editor.org/rfc/rfc9136.html) | Explica IRB y por qué los anuncios de prefijos difieren de los anuncios de hosts |

**VLAN** define la pertenencia local a la capa 2; una VLAN de puerto de acceso y una VLAN permitida en un trunk no son configuraciones intercambiables.
**LACP** negocia un grupo de agregación de enlaces: el estado de los miembros y el hash determinan la capacidad utilizable; un único flujo no tiene por qué usar todos los miembros.
**STP** protege una topología con bridges de los bucles; un puerto bloqueado inesperadamente puede explicar la falta de tráfico antes de que EVPN intervenga.
Lee [VLAN de netlab](https://netlab.tools/module/vlan/), [LAG](https://netlab.tools/module/lag/) y [STP](https://netlab.tools/module/stp/) junto con esta lista de comprobación.
Los laboratorios pequeños seleccionados **no** crean LACP ni una topología STP redundante. Márcalos como «no instanciados», no como «probados correctamente».
Antes de adaptar los ejercicios a otro fabric, exige la pertenencia correcta a las VLAN de acceso/trunk, los miembros LAG previstos y la topología de reenvío STP esperada.

El **underlay** proporciona conectividad IP entre los VTEP. Su enrutamiento, la ruta de retorno y la MTU utilizable deben funcionar de forma independiente del direccionamiento de los tenants.
El **overlay** transporta el tráfico de los tenants entre esos VTEP; VXLAN añade una encapsulación exterior de Ethernet/IP/UDP/VXLAN.
El destino exterior es un VTEP remoto, no el host del tenant; el VNI identifica un segmento virtual en la cabecera VXLAN.
Los ID de VLAN tienen significado local; hay que verificar su asignación a los VNI y no se debe suponer que los ID de VLAN y los VNI sean numéricamente iguales.

## 2. Distingue identificadores, rutas y reenvío

| Concepto | Significado | Evidencia que debes buscar |
|---|---|---|
| VTEP | Extremo de encapsulación/decapsulación | Dirección local, conectividad remota, interfaz VXLAN |
| L2VNI / MAC-VRF | Segmento de tenant con bridging | Asignación VLAN/bridge, MAC remota aprendida y VTEP |
| L3VNI / IP-VRF | Contexto de enrutamiento del tenant | Tabla de VRF, VNI de tránsito y prefijo remoto |
| RD | Distingue las identidades de rutas VPN que de otro modo se superpondrían | RD de la ruta de origen |
| RT | Pertenencia mediante comunidad extendida utilizada para la política de importación/exportación | RT de exportación anunciado y conjunto efectivo de RT importados por el receptor |
| SVI / IRB | Enrutamiento en el límite de un dominio de bridge | Dirección/MAC de gateway, asociación SVI-VRF y prueba de enrutamiento |

Diferentes RD pueden pertenecer a la misma VPN; los RD coincidentes no conceden pertenencia.
Un RT no es un firewall de paquetes. Una ruta importada sin intención puede crear conectividad, pero la ruta por sí sola tampoco demuestra el reenvío.
En IRB asimétrico, las rutas de entrada dirigen el tráfico y el lado remoto lo puentea al segmento de destino; los gateways participantes necesitan el estado L2 pertinente del destino.
En IRB simétrico, ambos extremos enrutan tráfico del tenant y utilizan un L3VNI entre sí.
No deduzcas que hay IRB simétrico solo porque BGP tenga una familia de direcciones EVPN.

| Ruta EVPN | Función en este cuaderno | Lo que su presencia no demuestra |
|---|---|---|
| Tipo 2: anuncio MAC/IP | Anuncia una MAC, opcionalmente con su IP asociada; permite conocer hosts remotos | Que todas las MAC anunciadas estén instaladas en el bridge correcto |
| Tipo 3: IMET | Anuncia la participación usada para construir la entrega BUM, como la replicación de entrada | Que funcione el reenvío unicast a hosts o el enrutamiento del tenant |
| Tipo 5: prefijo IP | Transporta conectividad IP del tenant sin depender del anuncio de la MAC de un host particular | Que el receptor importe el prefijo o pueda alcanzar su VTEP |

BUM significa broadcast, unicast desconocido y multicast; el estado de replicación de un VTEP importa junto con su ruta de Tipo 3.
En el informe, mantén separadas las rutas EVPN globales, el estado importado por VNI/VRF y la evidencia real del reenvío.

## 3. Selecciona laboratorios upstream reproducibles

Usa el repositorio de ejemplos enlazado desde la [página principal de netlab](https://netlab.tools/), en la revisión **`7c4fa0dac160d3cc2eac41e11f20b74d083bb896`**:

| Etapa | Ruta upstream exacta | Línea base prevista |
|---|---|---|
| A: L2 | [EVPN/vxlan-bridging](https://github.com/ipspace/netlab-examples/tree/7c4fa0dac160d3cc2eac41e11f20b74d083bb896/EVPN/vxlan-bridging) | h1↔h2 en red; h3↔h4 en blue; sin enrutamiento entre VLAN |
| B: L3 | [EVPN/l3vpn](https://github.com/ipspace/netlab-examples/tree/7c4fa0dac160d3cc2eac41e11f20b74d083bb896/EVPN/l3vpn) | h1↔h2 en la VRF red; h3↔h4 en la VRF blue; sin importación entre VRF |

Ambas usan `clab`, dos switches s1/s2, cuatro hosts Linux y un underlay OSPF con EVPN AS65000.
La selección upstream de la etapa A especifica EOS y Cumulus; la etapa B usa EOS de forma predeterminada.
**La selección declarada aquí anula cada nodo s1 y s2 individualmente para usar `frr`**, mediante las [opciones de inicio](https://netlab.tools/netlab/up/) documentadas `-s nodes.s1.device=frr -s nodes.s2.device=frr`.
La [matriz de compatibilidad con EVPN](https://netlab.tools/module/evpn/#platform-support) incluye FRR para EVPN basado en VLAN, IRB simétrico e iBGP/IGP.
Esa matriz no garantiza que funcione cualquier combinación de imágenes antiguas o proveedores.

Prepara **una VM exclusiva por etapa** o restaura una instantánea vacía de una VM propia entre etapas después de exportar la evidencia.
No inicies ambas copias con identidades de nodos/laboratorio en conflicto en un mismo host.
La etapa B tiene enlaces enrutados a los hosts y VNI de tránsito; es un ejercicio L3VPN, **no** un ejercicio de gateway anycast en una VLAN de acceso ni de movilidad de hosts.
Estudia la distinción de IRB con las lecturas; no informes como superadas pruebas de Tipo 2/3 o anycast cuando el modelo seleccionado, que solo usa L3, no las requiere.

## 4. Requisitos previos y registro específicos del laboratorio

- Usa una VM Linux Ubuntu 24.04 x86-64 propia con acceso a la consola. Como previsión, asigna 4 vCPU, 8 GiB de RAM y 20 GiB de disco libre **por cada etapa activa de seis contenedores**; mide el uso real.
- Completa la [configuración de Ubuntu para netlab](https://netlab.tools/install/ubuntu/) y la [configuración del proveedor containerlab](https://netlab.tools/labs/clab/) antes de usar el cuaderno, incluidas Docker, las dependencias de Ansible y las imágenes de los nodos.
- Usa una versión de netlab que anuncie las capacidades EVPN/VXLAN/VRF de FRR seleccionadas. Registra su versión exacta, la revisión del ejemplo y las anulaciones de ambos nodos.
- La [definición de dispositivo FRR](https://github.com/ipspace/netlab/blob/4d85d13365caf3962a72ba59ec57a2e4450f365f/netsim/devices/frr.yml) de netlab que se inspeccionó selecciona `quay.io/frrouting/frr:10.6.1`; los ejemplos de CLI de aquí se comprobaron con FRR 10.6.1. Registra la imagen y el digest de la versión instalada realmente en lugar de suponer que coinciden.
- FRR/clab necesita compatibilidad del kernel de la VM con bridge y VXLAN, y con VRF para la etapa B. La configuración upstream puede cargar módulos en **esta VM propia**. Un Codespace restringido que no permita cargar los módulos necesarios no es una alternativa válida.
- Prepara iproute2, iputils, tcpdump y GNU `timeout` en la VM. Para las pruebas de DF/tamaño, usa iputils de la VM dentro de un espacio de nombres de nodo registrado; no supongas que el `ping` BusyBox de una imagen de host Alpine admite esas opciones.
- FRR y las imágenes Linux de host seleccionadas no requieren licencias comerciales de router. Mantener EOS/Cumulus sería una selección de plataforma distinta, con sus propios requisitos de acceso a imágenes, licencias y CLI.
- El propietario de la VM proporciona los privilegios de Docker/proveedor; `vtysh` y las operaciones de espacio de nombres requieren privilegios de laboratorio adecuados. No cambies interfaces de administración, rutas de la estación de trabajo ni parámetros de la nube.

En el **shell de la VM de la etapa A**, cuando el destino no exista:

```bash
test ! -e "$HOME/expert-fabric-examples"
git clone --no-checkout https://github.com/ipspace/netlab-examples.git "$HOME/expert-fabric-examples"
git -C "$HOME/expert-fabric-examples" checkout --detach 7c4fa0dac160d3cc2eac41e11f20b74d083bb896
cd "$HOME/expert-fabric-examples/EVPN/vxlan-bridging"
git rev-parse HEAD
git status --short
sha256sum topology.yml
python3 -c 'from importlib.metadata import version; print(version("networklab"))'
containerlab version
docker version
ansible --version
uname -r
```

Detente si falla la comprobación de ausencia. El clon es un nuevo objeto propio; consérvalo junto con la evidencia hasta que se elimine esta VM.
Repite el procedimiento de clonación/revisión en la VM independiente de la etapa B y usa después `EVPN/l3vpn` como directorio de trabajo.
Antes de observar cualquiera de las etapas, el propietario debe completar el procedimiento oficial de inicio con el proveedor `clab` y las anulaciones de nodo de FRR.
Registra la instantánea vacía de la VM, la identidad generada del laboratorio, las opciones exactas de inicio y una instantánea saludable previa al experimento.
Esta configuración es la que crea el bridge/VTEP/VRF: [FRR no crea por sí mismo las interfaces Linux](https://docs.frrouting.org/en/latest/evpn.html#the-linux-vxlan-dataplane).
No pegues parámetros BGP aislados en un contenedor vacío y lo describas como un overlay funcional.

## 5. Verifica las identidades y la disponibilidad del plano de datos

En el **shell de la VM** de la etapa activa:

```bash
netlab status
netlab inspect nodes.s1.interfaces
netlab inspect nodes.s2.interfaces
netlab connect --dry-run s1
netlab connect s1 --show version
netlab connect s1 --show running-config
netlab connect s1 --show ip ospf neighbor
netlab connect s1 --show bgp l2vpn evpn summary
netlab connect s1 --show evpn vni
netlab connect s1 --show bgp l2vpn evpn vni
netlab connect s1 ip -d link show
netlab connect s1 bridge link show
netlab connect s1 bridge fdb show
netlab connect s1 ip route show
```

Repite en s2 las comprobaciones de estado de solo lectura. Usa las referencias de [inspección](https://netlab.tools/netlab/inspect/) y [conexión](https://netlab.tools/netlab/connect/) para interpretar las asignaciones de nodos/interfaces.
`netlab connect s1` abre el shell Linux del **contenedor FRR**; escribe `vtysh` para entrar a la CLI de FRR.
`s1#` indica el modo operativo de FRR; `configure terminal` entra al modo de configuración, `end` sale de él y `exit` desde el modo operativo vuelve a Linux.
Usa `ip`/`bridge` en Linux y `show` en FRR, o el wrapper `--show` desde la VM como arriba.

Registra la imagen exacta de cada contenedor con `docker inspect --format '{{.Config.Image}} {{.Image}}' CONTAINER`; inspecciona cada objeto de laboratorio por separado y por nombre.
Exige interfaces VXLAN reales con direcciones VTEP locales, pertenencia al bridge, VNI operativos y conectividad a los VTEP remotos.
En la etapa B también exige `show vrf vni`, dispositivos/tablas VRF de Linux y que los enlaces de host pertenezcan a red o blue.
Las [advertencias actuales de FRR](https://netlab.tools/caveats/#frrouting) indican que la inicialización de VLAN/VRF no es idempotente y que la recopilación de configuración omite el estado de las interfaces Linux.
No intentes corregir un requisito previo fallido repitiendo la inicialización; conserva el fallo y vuelve a la instantánea de configuración propia.

Completa esta asignación con la salida real; nunca la rellenes de memoria:

| Host | IP/prefijo de datos | VLAN de acceso o enlace enrutado | VRF | L2VNI / L3VNI | VTEP local/remoto | Interfaz de captura |
|---|---|---|---|---|---|---|
| h1 | Registrar | red en etapa A / enrutado en etapa B | Registrar | Registrar o N/A justificado | Registrar | Registrar |
| h2 | Registrar | red en etapa A / enrutado en etapa B | Registrar | Registrar o N/A justificado | Registrar | Registrar |
| h3/h4 | Registrar cada uno | blue | Registrar | Registrar o N/A justificado | Registrar | Registrar |

## 6. Etapa A: demuestra el reenvío L2 y la separación

Lee las direcciones de datos de h1/h2/h3/h4 con `netlab connect h1 ip address show`, sustituyendo un host exacto cada vez.
Este comando se ejecuta dentro del contenedor host; instalar iproute2 en la VM no cambia la implementación BusyBox de ese contenedor. Usa direcciones de datos, no direcciones de administración ni un nombre de host sin resolver que pueda seleccionar la red de administración.
En el shell de la VM, sustituye estos marcadores con los datos de tu asignación:

```bash
fabric_h2='REPLACE_WITH_H2_DATA_IPV4'
fabric_h3='REPLACE_WITH_H3_DATA_IPV4'
fabric_h4='REPLACE_WITH_H4_DATA_IPV4'
netlab connect h1 ping -c 5 -W 1 "$fabric_h2"
netlab connect h3 ping -c 5 -W 1 "$fabric_h4"
netlab connect h1 ping -c 5 -W 1 "$fabric_h3"
netlab connect s1 --show bgp l2vpn evpn route type 2
netlab connect s1 --show bgp l2vpn evpn route type 3
netlab connect s1 bridge fdb show
```

Genera tráfico de host previsto antes de esperar que se aprendan MAC remotas de Tipo 2.
Asocia cada MAC remota con el VNI y el VTEP correctos; el estado de Tipo 3/replicación debe corresponder al segmento previsto.
Las dos primeras pruebas deben tener éxito. La prueba entre VLAN debe fallar con este diseño sin enrutamiento.
Ese fallo por sí solo no basta: exige ambos controles positivos, la conexión correcta de los hosts y la ausencia de una ruta de enrutamiento no prevista.
Registra si la prueba negativa falló localmente por falta de ruta o si alcanzó un límite del plano de datos; son observaciones distintas.

Confirma en el inventario cuál es la interfaz entre switches de s1; en la asignación FRR fijada para la etapa A es `eth3`.
Mientras repites una prueba permitida en otra terminal, captura solo esa interfaz propia:

```bash
timeout 20s netlab capture s1 eth3 -nn -e -vv -l -c 30 udp port 4789
```

Guarda el par VTEP exterior, el VNI y el par MAC/IP interior. La ausencia de salida, un error de captura o el tráfico de administración no constituyen evidencia.
Explica cómo coincide la encapsulación observada con la evidencia de rutas y FDB.
No esperes un prefijo de tenant Tipo 5 en este ejercicio de solo bridging para satisfacer una lista de comprobación.

## 7. Etapa B: demuestra el servicio enrutado de VRF

Cambia a la VM independiente preparada para la etapa B y reconstruye la asignación de identidades/direcciones.
Vuelve a asignar las variables `fabric_h2`, `fabric_h3`, `fabric_h4` con las direcciones de la **etapa B**; los valores de la etapa A no son evidencia reutilizable.
Repite las tres pruebas de la sección 6: deben funcionar los pares red y blue, pero no el tráfico entre VRF.
Inspecciona también:

```bash
netlab connect s1 --show vrf vni
netlab connect s1 --show bgp l2vpn evpn route type 5
netlab connect s1 --show bgp vrf red ipv4 unicast
netlab connect s1 --show ip route vrf red
netlab connect s1 ip -d link show type vrf
netlab connect s1 ip route show vrf red
```

Identifica en la tabla Tipo 5 la subred remota real de h2, su RD/RT de exportación, su importación en red y la ruta Linux correspondiente.
Comprueba blue por separado. Confirma que red no importa blue e inspecciona la ruta de retorno en s2.
Captura el underlay como en la sección 6 usando la **interfaz real de la etapa B**, que quizá no sea `eth3`.
Relaciona el VNI de tránsito con la VRF; un ping de administración correcto no cuenta como servicio enrutado del tenant.

## 8. Etapa B: elimina una pertenencia de importación y restáurala

Objeto propio: **la lista de RT de importación EVPN de la VRF red en s1**. Conserva su configuración exacta en ejecución y el conjunto efectivo de RT.
Usa `netlab connect s1 --show bgp l2vpn evpn vni RED_L3VNI`, sustituyendo el VNI numérico de tránsito registrado para red, para inspeccionar los detalles de RT importados/exportados.
El estado previo debe tener un RT de importación explícito, denominado `RED_RT` más abajo, sin comodines ni importaciones automáticas adicionales que admitan las mismas rutas.
Elige `BAD_RT` como `65000:424242` solo después de demostrar que ninguna ruta del laboratorio lo anuncia y que ninguna lista existente lo usa.
Si el estado previo difiere, no improvises la eliminación de otras entradas.
Usa el `RED_RT` real, no el marcador literal, en la **CLI de FRR** de s1:

```text
configure terminal
router bgp 65000 vrf red
 address-family l2vpn evpn
  route-target import 65000:424242
  no route-target import RED_RT
 exit-address-family
end
```

Añadir el RT sin uso antes de quitar el original mantiene una lista explícita.
Eliminar el único RT manual sin esta protección puede restaurar un RT automático e invalidar el experimento.
Las versiones de FRR difieren en los controles de RT automático; verifica el conjunto efectivo de importación con los detalles del VNI y la [documentación de RT coincidente en ejecución](https://docs.frrouting.org/en/latest/bgp.html).
Si el RT original sigue siendo efectivo, clasifica la inyección como no realizada y restaura el estado; no afirmes que se probó el aislamiento.

Espera que el anuncio global Tipo 5 y la sesión BGP permanezcan, pero que el prefijo remoto de h2 desaparezca de la VRF/FIB red de s1 y que falle la prueba red.
Exige que el par blue siga funcionando y que h2 alcance su gateway local red; un host inactivo o un underlay roto no demuestran aislamiento por RT.
Lee el prefijo exacto en las tablas global e importada y conserva el resultado/código de salida de la prueba negativa.
Restaura el mismo objeto, añadiendo la pertenencia original antes de quitar la temporal:

```text
configure terminal
router bgp 65000 vrf red
 address-family l2vpn evpn
  route-target import RED_RT
  no route-target import 65000:424242
 exit-address-family
end
```

Exige que se recuperen el conjunto original de RT efectivos, la ruta remota, la prueba red y el control blue; no cambies el RD, el vecino ni el RT de exportación.

## 9. Etapa B: mide el comportamiento de la MTU del underlay

Objeto propio: **la MTU de la interfaz de datos entre switches de s1**. El enlace upstream de la etapa B solicita 1600; verifica que el valor real sea 1600 en la interfaz elegida antes de continuar.
Registra que no es una interfaz de administración/acceso/bridge/VXLAN y que su par es s2.
Mantén abierta una segunda terminal de VM para la restauración. Sustituye la interfaz, el espacio de nombres de h1 y la dirección de datos de h2 según la asignación de esta etapa:

```bash
fabric_underlay='REPLACE_WITH_S1_TO_S2_INTERFACE'
fabric_h1_ns='REPLACE_WITH_THIS_LABS_H1_NAMESPACE'
fabric_h2='REPLACE_WITH_H2_DATA_IPV4'
netlab connect s1 ip -d link show dev "$fabric_underlay"
sudo ip netns exec "$fabric_h1_ns" ip -br address
sudo ip netns exec "$fabric_h1_ns" ping -n -M do -s 1200 -c 5 -W 1 "$fabric_h2"
sudo ip netns exec "$fabric_h1_ns" ping -n -M do -s 1400 -c 5 -W 1 "$fabric_h2"
```

Confirma que ambos tamaños de línea base funcionan. El [ping de iputils](https://github.com/iputils/iputils/blob/master/doc/ping.xml) de la VM proporciona `-M do`; no se presupone instalar paquetes dentro del contenedor host.
Para Ethernet sin etiquetas con IPv4 exterior, una carga ICMP de 1400 bytes produce un paquete IP interior de 1428 bytes y aproximadamente 1478 bytes de IP exterior tras la encapsulación.
Registra las etiquetas/cabeceras reales; el transporte IPv6 o una encapsulación adicional cambia el presupuesto.

Cambia solo la MTU registrada, repite ambas pruebas y captura el underlay a la vez:

```bash
netlab connect s1 ip link set dev "$fabric_underlay" mtu 1400
timeout 20s netlab capture s1 "$fabric_underlay" -nn -vv -l -c 30 'ip proto 17 or icmp'
```

La prueba pequeña puede seguir funcionando mientras la grande se pierde o los paquetes exteriores se fragmentan; DF en el paquete interior no garantiza por sí mismo DF en el exterior.
El filtro de protocolo IPv4 incluye fragmentos UDP posteriores que un filtro limitado a puertos podría perder; identifica VXLAN con el par VTEP registrado y el primer fragmento.
OSPF también puede reaccionar a una discrepancia de MTU. Registra el estado del vecino, los errores, los fragmentos y cualquier mensaje ICMP en lugar de insistir en que BGP deba seguir establecido.
Si no aparece un efecto dependiente del tamaño, informa esa observación e investiga la encapsulación/fragmentación/descarga de procesamiento; no inventes un agujero negro.
Restaura inmediatamente después de la recopilación acotada:

```bash
netlab connect s1 ip link set dev "$fabric_underlay" mtu 1600
netlab connect s1 ip -d link show dev "$fabric_underlay"
```

Vuelve a comprobar OSPF/BGP, ambos tamaños de prueba, los controles positivos de ambas VRF y la afirmación negativa entre VRF.
No vacíes rutas, tablas de vecinos ni todos los bridges para obtener una salida que parezca limpia.

## 10. Evidencia y finalización

| Prueba | Control positivo | Evidencia negativa prevista | Prueba de restauración |
|---|---|---|---|
| Segmentación L2 | Pasan ambos pares de la misma VLAN; VXLAN/FDB correctos | Bloqueo entre VLAN sin servicio de enrutamiento | Asignaciones originales y repetición de las pruebas |
| VPN L3 | Tipo 5 importado en la VRF correcta; pasa la prueba del tenant | La otra VRF no aparece en la importación/FIB y la prueba falla | Matriz original de rutas y pruebas |
| Desajuste de RT | Blue funciona; el host objetivo/gateway local está activo | La ruta global existe, pero falta la importación en red y falla la prueba red | Lista exacta de RT y recuperación de ruta y prueba red |
| Reducción de MTU | Tamaños de línea base y underlay conocido | Efecto medido en tamaño/fragmentación/adyacencia, o falta de reproducción explícita | MTU 1600 y repetición de toda la línea base |

En cada fila conserva la fase, la marca de tiempo, la identidad de VM/laboratorio, la revisión upstream, las versiones de herramientas/imágenes, el nodo/interfaz, el resultado previsto, la salida real y la conclusión.
Usa **PASS**, **FAIL**, **BLOCKED** o **N/A** justificado; una tabla de rutas vacía, una prueba ausente o una captura que falte no pueden ser por sí solas un PASS.
Registra N/A para el tipo/función del modelo elegido, no como excusa para una prueba obligatoria rota.
Hay que revertir todos los cambios activos en los objetos nombrados; si esto falla, conserva la evidencia y restaura solo la instantánea registrada de la VM propia.
Deja sin guardar los cambios experimentales; no repitas inicializaciones no idempotentes ni hagas un desmontaje de todo el laboratorio/poda global.
El ejercicio se completa cuando puedes seguir el servicio L2 y L3, explicar RD/RT y los tipos de ruta, mostrar el aislamiento con controles funcionales y demostrar la restauración.
Continúa con [rendimiento de Linux](04-linux-performance.md), [diseño de nube/CNI](05-cloud-cni-design.md), el [proyecto final de automatización](06-automation-capstone.md) y el [cuestionario](../../quizzes/networking/expert/03-datacenter-evpn-quiz.md).
