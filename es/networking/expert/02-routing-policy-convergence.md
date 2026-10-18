# 02. Política de enrutamiento y convergencia medida

> **Última actualización**: 15 de septiembre de 2026
> **Límite del laboratorio**: una VM Linux de enrutamiento independiente, propia y descartable que se preparó por separado; solo contenedores FRRouting locales.
> **Estado de verificación**: se comprobaron la documentación oficial del proyecto, la topología y las fuentes de CLI; **no se ejecutó** el laboratorio de enrutamiento al redactar este capítulo.

Al terminar este cuaderno, podrá explicar por qué se seleccionó un prefijo, demostrar que se puede usar su siguiente salto y medir lo que experimentó el tráfico durante un fallo controlado.
Complete primero las [ocho lecciones para principiantes](../beginner/README.md), incluido el [proyecto final sobre contenedores y nube](../beginner/08-container-cloud-capstone.md).
Vuelva al [reenvío de Linux](../../kernel/02-network-stack.md) cuando una ruta de una tabla de protocolo no explique la trayectoria del paquete.

## 1. Leer con una pregunta que responder

| Lectura | Pregunta que debe responder con sus propias palabras |
|---|---|
| [Descripción general de BGP Labs](https://bgplabs.net/) e [introducción a FRRouting](https://bgplabs.net/basic/0-frrouting/) | ¿Qué acciones se realizan en la shell de Linux y cuáles en `vtysh`? |
| [Laboratorio de preferencia local](https://bgplabs.net/policy/5-local-preference/) | ¿Por qué una preferencia configurada en un borde influye en el otro? |
| [Manual BGP de FRR](https://docs.frrouting.org/en/latest/bgp.html) | ¿Cuándo una ruta recibida es apta, se selecciona, se anuncia y se instala? |
| [Manual OSPF de FRR](https://docs.frrouting.org/en/latest/ospfd.html) | ¿Qué demuestra una adyacencia y qué prefijos transporta el IGP? |
| [RFC 4271](https://www.rfc-editor.org/rfc/rfc4271.html) y [RFC 4456](https://www.rfc-editor.org/rfc/rfc4456.html) | ¿En qué se diferencian las reglas habituales de anuncios iBGP de la reflexión de rutas? |

Lea las secciones elegidas antes de configurar nada. Dibuje un diagrama donde las sesiones de enrutamiento y los enlaces de reenvío aparezcan por separado.
Una sesión BGP es una conexión TCP entre dos routers BGP; no implica que todos los destinos anunciados sean accesibles mediante esa conexión.

## 2. Construir el modelo del plano de control

**IGP y BGP resuelven problemas distintos.** OSPF distribuye información de estado de enlace dentro de un dominio administrativo y calcula rutas mediante costes.
En este laboratorio proporciona conectividad interna, incluidas las loopbacks que se usan para iBGP.
BGP intercambia conectividad de destinos con atributos y aplica políticas; no es simplemente un sustituto de OSPF que elige el menor número de saltos.
Redistribuir a ciegas todo entre ambos protocolos introduce rutas adicionales, ambigüedad de políticas y posible retroalimentación.

**eBGP** normalmente intercambia rutas entre distintos sistemas autónomos; **iBGP** distribuye información BGP dentro de un AS.
AS_PATH ayuda a detectar bucles entre sistemas autónomos, mientras que las restricciones habituales de anuncios iBGP evitan bucles de reanuncio interno sencillos.
Por lo general, una ruta aprendida mediante iBGP no se anuncia a otro par iBGP; se necesita una malla completa, reflectores de rutas u otro diseño deliberado.
No deduzca la topología de reenvío a partir de esa malla de sesiones.

**La resolución del siguiente salto precede al reenvío útil.** Una ruta BGP puede estar visible pero no se puede usar si no hay una ruta alcanzable hacia su siguiente salto.
El siguiente salto iBGP puede seguir siendo una dirección externa salvo que el diseño lo cambie, por ejemplo mediante next-hop-self.
Compruebe el NEXT_HOP recibido y luego resuélvalo recursivamente en la tabla de enrutamiento hasta llegar a una interfaz y un vecino.
Una adyacencia OSPF por sí sola no demuestra que se haya anunciado el prefijo del siguiente salto requerido.

| Capa | Evidencia | Lo que esa evidencia no demuestra |
|---|---|---|
| Sesión BGP | Estado y familias de direcciones negociadas | Que se haya aceptado un prefijo previsto |
| RIB de BGP | Rutas candidatas, atributos, validez e indicador de mejor ruta | Que la ruta seleccionada haya llegado al plano de reenvío |
| Tabla de enrutamiento de Zebra | Ruta seleccionada y estado de instalación | Que los paquetes hayan salido por la interfaz prevista |
| Búsqueda en la FIB de Linux | Ruta, interfaz de salida y siguiente salto de un destino | Alcance de la ruta de retorno o ausencia de filtrado de paquetes |
| Observación de paquetes | Sondas específicas del origen y captura de interfaz | Que funcionen todas las aplicaciones, tamaños de paquete o rutas ECMP |

En los informes, distinga explícitamente «tabla BGP» y «tabla de reenvío del kernel» en vez de llamar a ambas «tabla de enrutamiento».
FRR pasa las decisiones de enrutamiento a través de Zebra; Linux efectúa el reenvío con el plano de datos de software seleccionado.

## 3. Explicar la política antes de probarla

| Mecanismo | Finalidad operativa | Inferencia incorrecta frecuente |
|---|---|---|
| Filtro de prefijos | Aceptar o anunciar solo los prefijos y longitudes previstos | Permitir un `/24` acepta automáticamente todas las rutas más específicas |
| LOCAL_PREF | Expresar la preferencia de salida dentro de un AS; se prefiere el valor mayor | Indica a un AS externo por qué punto de entrada debe enviar tráfico a este AS |
| Weight | Preferencia local específica de la implementación en un enrutador | Se propaga a otros enrutadores como atributo BGP |
| AS_PATH / prepending | Describir el recorrido del AS e influir en la selección de ruta cuando la política lo permite | Una ruta más corta siempre vence a una con local preference mayor |
| MED | Sugerir una preferencia de entrada según las reglas de comparación del receptor | Se compara universalmente entre todos los AS vecinos |
| Community | Transportar una etiqueta que una política receptora puede interpretar | La etiqueta impone un comportamiento sin una política que la aplique |
| Reflector de rutas | Reducir la cantidad de sesiones iBGP mediante reflexión | Aporta la ruta que falta para alcanzar el siguiente salto o necesariamente reenvía tráfico de tránsito |

ORIGINATOR_ID y CLUSTER_LIST del reflector ayudan a evitar bucles; la selección de rutas puede ocultar alternativas a los clientes.
Para una ruta reflejada, inspeccione por separado el cliente, el reflector y la alcanzabilidad del siguiente salto.
Use más adelante el [laboratorio de reflector de rutas](https://bgplabs.net/ibgp/3-rr/) como ejercicio preparado aparte, en vez de añadir un reflector a la topología de este cuaderno.

Escriba este diseño de filtro sin implementarlo: exporte únicamente a un proveedor externo `192.168.42.0/24`.
Una coincidencia exacta de `/24` debe aceptar esa ruta, rechazar `192.168.42.0/25` y rechazar el prefijo aprendido del proveedor `192.168.100.0/24`.
Rechace también `0.0.0.0/0`, salvo que un acuerdo indicado por separado lo permita.
Explique la denegación implícita, el orden de evaluación y la dirección de asociación.
Continúe con [Filtrar prefijos anunciados](https://bgplabs.net/policy/3-prefix/) para practicar filtros activos; no dé por hecho que la política existente de este laboratorio implementa el filtro propuesto.

## 4. Preparar este laboratorio en particular

El laboratorio seleccionado, **`bgplab/bgplab` en `policy/5-local-preference/topology.yml`**, corresponde a la revisión **`5a9fab68658ce69317b147396481714ee3478482`**.
Sus cuatro enrutadores son c1/c2 en AS65000 y x1/x2 en AS65100.
La topología configura OSPF, eBGP, iBGP y anuncios; en el laboratorio se modifica la política del cliente.
La [topología fuente](https://github.com/bgplab/bgplab/blob/5a9fab68658ce69317b147396481714ee3478482/policy/5-local-preference/topology.yml) requiere **netlab 2.0.0 o posterior**.

La dirección suministrada `https://bgplabs.net/install/` devolvió 404 en la fecha de comprobación; use la página oficial [Instalación y configuración](https://bgplabs.net/1-setup/).
Siga el [requisito previo de instalación en Ubuntu](https://netlab.tools/install/ubuntu/) en esta VM separada antes de comenzar el cuaderno.
No reutilice la VM para principiantes, un host Docker compartido ni un nodo de Kubernetes.

- Asigne una VM Ubuntu 24.04 x86-64 propia. Como **referencia de planificación**, no como mínimo exigido por el proyecto ni como benchmark, reserve 4 vCPU, 8 GiB de RAM y 20 GiB de disco libre para cuatro contenedores FRR y herramientas.
- Prepare netlab, sus dependencias de Ansible, Docker y containerlab (proveedor `clab`), Git, iproute2, `ping` de iputils, `timeout` de GNU y tcpdump según la documentación oficial.
- Anote la versión instalada de netlab y las versiones del proveedor. Use la imagen FRR que seleccione esa versión de netlab y registre su etiqueta, el ID de la imagen o su digest, y el resultado real de `show version`.
- Los ejemplos de CLI se comprobaron con código fuente FRR **10.6.1**. Si la versión de ejecución es distinta, antes de mutar el estado compruebe la ayuda de sus comandos; la etiqueta genérica «imagen FRR» no garantiza compatibilidad.
- FRR es software de código abierto; esta selección no requiere una licencia comercial de enrutador. La descarga de la imagen y la preparación de herramientas sí requieren acceso a la red.
- La administración del proveedor clab requiere privilegios en esta VM descartable; los contenedores FRR se ejecutan como root para la shell de Linux y `vtysh`. Mantenga disponible la consola de la VM y no toque las interfaces de administración.
- Asegúrese de ser el único propietario de la VM, del directorio clonado y del nombre del laboratorio. Los enlaces entre el cliente y el proveedor son simulaciones locales, no conexiones a un ISP ni a Internet.

En la **shell de la VM del laboratorio**, cree un clon nuevo; el destino no debe existir ya:

```bash
test ! -e "$HOME/expert-routing-bgplab"
git clone --no-checkout https://github.com/bgplab/bgplab.git "$HOME/expert-routing-bgplab"
git -C "$HOME/expert-routing-bgplab" checkout --detach 5a9fab68658ce69317b147396481714ee3478482
cd "$HOME/expert-routing-bgplab/policy/5-local-preference"
git rev-parse HEAD
git status --short
sha256sum topology.yml
python3 -c 'from importlib.metadata import version; print(version("networklab"))'
containerlab version
docker version
ansible --version
uname -r
```

Si falla la comprobación de ausencia, deténgase; no ejecute los comandos restantes para clonar encima de un directorio existente.
Registre estos resultados fuera del clon como evidencia.
La preparación solo termina cuando el propietario sigue en este directorio las instrucciones oficiales para iniciar el laboratorio con `provider=clab`, dispositivo cliente `frr` y dispositivo externo `frr`.
El comando de inicio documentado por el proyecto crea y configura el laboratorio; es un requisito previo, no un comando de solo lectura.
Pida al propietario de la VM que anote las identidades de nodos y contenedores generadas y guarde un punto de control de la VM propio previo al experimento.
El autor de este capítulo no realizó el inicio, la instalación, la configuración del host ni la eliminación del entorno.

## 5. Preparación y límites de cada terminal

Ejecute estos comandos desde el **mismo directorio del laboratorio en la shell de la VM**:

```bash
netlab defaults --project
netlab status
netlab connect --dry-run c1
netlab connect c1 --show version
netlab connect c1 --show running-config
netlab connect c2 --show bgp ipv4 unicast summary
netlab connect c1 --show ip ospf neighbor
netlab connect c2 --show ip ospf neighbor
```

`netlab defaults --project` requiere netlab 2.0.1 o posterior; con 2.0.0, inspeccione en su lugar el `defaults.yml` clonado.
La [referencia de conexión](https://netlab.tools/netlab/connect/) documenta el acceso tanto a un solo nodo como con `--show`.
`netlab connect c1` abre la **shell de Linux de c1** para esta selección FRR/clab; al entrar en `vtysh`, se abre la **CLI de FRR de c1**.
Los indicadores siguientes son etiquetas, no texto que se deba pegar:

```text
lab-vm$ netlab connect c1
c1-linux# vtysh
c1# show version
c1# show running-config
c1# exit
c1-linux# exit
```

Ejecute `ip`, `ping` y los comandos de shell en Linux, no en `c1#`.
`configure terminal` entra en el modo de configuración de FRR; `end` vuelve al indicador operativo de FRR.
Desde la VM, `netlab connect c1 --show ip route` ejecuta el wrapper FRR correcto; no envíe comandos `show` sin wrapper a la shell de Linux.

La preparación exige sesiones iBGP/eBGP realmente establecidas, los vecinos OSPF previstos, dos rutas de proveedor aptas en c2 y sondas acotadas que tengan éxito.
Inspeccione las imágenes de las identidades registradas de los contenedores c1, c2, x1 y x2 **por separado** con `docker inspect --format '{{.Config.Image}} {{.Image}}' CONTAINER`.
No sustituya esto por un listado global de contenedores del host como prueba de las versiones de esos nodos.

## 6. Referencia: predecir, observar y explicar

En la revisión fijada, el vecino BGP externo de c1 es `10.1.0.2` y el de c2 es `10.1.0.6`.
Las loopbacks iBGP son `10.0.0.1` y `10.0.0.2`; el segmento del cliente es `192.168.42.0/24`.
Antes de usarlos, compruebe esos valores en la configuración en ejecución.
El destino de prueba `192.168.100.10` es la dirección de x1 en el segmento simulado del proveedor.

```bash
netlab connect c2 --show bgp ipv4 unicast 192.168.100.0/24
netlab connect c2 --show ip route 10.0.0.1/32
netlab connect c2 --show ip route 192.168.100.0/24
netlab connect c2 ip route get 192.168.100.10
netlab connect c2 ping -I 192.168.42.2 -c 5 -W 1 192.168.100.10
netlab connect c1 --show bgp ipv4 unicast neighbors 10.1.0.2 advertised-routes
```

Registre las dos rutas candidatas, los siguientes saltos, AS_PATH, LOCAL_PREF, motivo de mejor ruta y la búsqueda del kernel.
Explique si c2 seleccionó el proveedor externo conectado directamente o la salida a través de c1.
En la salida de anuncios, clasifique cada prefijo observado frente a la lista permitida de exportación que propuso; cualquier anuncio inesperado es un hallazgo, no una prueba de que se haya aplicado ese filtro.
Antes de atribuir a la política de salida la ausencia de respuestas, compruebe la ruta de retorno de x1 a `192.168.42.0/24`.

## 7. Cambiar la preferencia de salida de un cliente

Estado previo: la instancia AS65000 de c1 **no tiene** `bgp default local-preference` explícito, el valor predeterminado efectivo es 100 y ninguna política de entrada sobrescribe las rutas de proveedor examinadas.
El valor efectivo de referencia de c2 también es 100. Conserve ambas configuraciones.
Si no se cumplen estas condiciones, deténgase y establezca una referencia adecuada en vez de eliminar una política existente.

El único objeto que se modifica es **la instancia BGP AS65000 de c1**; para revertirlo, quite solo el ajuste introducido aquí.
En la **CLI de FRR** de c1:

```text
configure terminal
router bgp 65000
 bgp default local-preference 200
end
show bgp ipv4 unicast 192.168.100.0/24
```

Este comando de FRR se verificó en [la implementación de CLI 10.6.1](https://github.com/FRRouting/frr/blob/frr-10.6.1/bgpd/bgp_vty.c); esa implementación también vuelve a procesar las rutas entrantes de esta instancia.
No copie en un entorno compartido los ejemplos del proyecto que borran rutas mediante comodines.
Vuelva a ejecutar en c2 la sección 6: se espera que la ruta apta a través de c1 tenga el valor 200 y prevalezca sobre la ruta con 100; compruebe también la FIB y la trayectoria correspondiente de los paquetes.
Si los atributos no cambian, inspeccione la política de entrada, la validez del siguiente salto y la versión real de ejecución; una línea de configuración por sí sola no es un PASS.
Este cuaderno solo modifica c1, por lo que la expectativa independiente del validador del proyecto de c2=50 **no es el criterio de aceptación de este cuaderno**.

## 8. Medir la caída de un vecino BGP

Mantenga activa la prueba de preferencia. Estado previo: el **vecino `10.1.0.2` de c1** está establecido y no tiene el ajuste `shutdown`.
Operación inversa: `no neighbor 10.1.0.2 shutdown` en la misma instancia BGP.
Esto provoca la caída administrativa del vecino BGP, no la desconexión de un cable, la pérdida silenciosa de paquetes ni una prueba BFD.

Para hacer sondas con marcas de tiempo, use iputils de la VM dentro del **espacio de nombres de red del contenedor registrado de c2**.
Obtenga el nombre a partir del inventario o del mapeo del proveedor de este laboratorio y compruebe que exista mediante `ip netns list`; nunca seleccione uno con un comodín poco específico.
Sustituya el marcador antes de ejecutar el comando en una segunda terminal de la VM:

```bash
routing_c2_ns='REPLACE_WITH_THIS_LABS_C2_NAMESPACE'
sudo ip netns exec "$routing_c2_ns" ip -br address
sudo ip netns exec "$routing_c2_ns" ping -D -O -n -I 192.168.42.2 -i 0.2 -c 150 -w 40 -W 1 192.168.100.10
```

Exija que las direcciones mostradas coincidan con las de c2. Obtenga varias respuestas correctas antes de inyectar el fallo.
La [opción `-O` de iputils](https://github.com/iputils/iputils/blob/master/doc/ping.xml) informa sobre respuestas pendientes; correlacione sus números de secuencia con las respuestas posteriores en vez de tratar cada aviso de respuesta pendiente como una pérdida permanente.
En la CLI de FRR de c1, anote la hora de intervención y luego aplique:

```text
configure terminal
router bgp 65000
 neighbor 10.1.0.2 shutdown
end
```

Desde la VM, tome muestras durante la ventana acotada de sondas de los prefijos BGP y la ruta del kernel de c2 mediante la sección 6.
En otra terminal, use el [comando de captura](https://netlab.tools/netlab/capture/) en la **interfaz de datos de respaldo confirmada de c2**; la topología fijada de FRR la asigna a `eth2`:

```bash
timeout 20s netlab capture c2 eth2 -nn -l -c 40 icmp
```

El tiempo de espera limita la recopilación; que no haya paquetes coincidentes o se produzca un error de acceso no constituye una captura correcta.
Se espera que c2 seleccione x2 y luego alcance x1 a través del segmento interno del proveedor.
Distinga `t_action`, el primer cambio/retiro de ruta observado, el cambio de FIB, la última sonda fallida y la primera recuperación sostenida.
Defina de antemano la recuperación sostenida, por ejemplo, cinco respuestas consecutivas; informe el intervalo de muestreo y la incertidumbre.
Use el mismo reloj de la VM para las sondas y las intervenciones; justo antes de la acción CLI, registre `date -u +%FT%T.%NZ` desde la shell de la VM e incluya en la incertidumbre la latencia de intervención manual desde la terminal.
Que no se observen pérdidas significa que, con esta frecuencia de muestreo, no se midió ninguna interrupción; no que el tiempo de convergencia fuera cero.
Los temporizadores hold de BGP, junto con BFD, el reinicio gradual, la detección de fallos, el procesamiento de rutas y la programación de la FIB, pueden afectar a los resultados; no afirme que haya un tiempo de convergencia universal fijo.

## 9. Restaurar, repetir y entregar

Restaure **primero el vecino BGP**, en la CLI de FRR de c1:

```text
configure terminal
router bgp 65000
 no neighbor 10.1.0.2 shutdown
end
```

Compruebe que el vecino vuelva a establecer la sesión, que se restablezca la ruta preferida y que se recuperen las sondas.
Luego restaure **el objeto de política**:

```text
configure terminal
router bgp 65000
 no bgp default local-preference
end
```

Vuelva a comprobar la configuración en ejecución, las dos rutas candidatas, la preferencia efectiva, la búsqueda de la FIB y la sonda original específica del origen.
No guarde los ajustes experimentales en la configuración de inicio, reinicie FRR ni ejecute comandos de limpieza generales.
Si falla la recuperación, detenga los demás experimentos e informe del objeto que difiere; el propietario puede restaurar el punto de control registrado de esta única VM descartable después de exportar la evidencia.
El clon nuevo se conserva como evidencia; su eliminación posterior se limita a esta VM propia y sigue el procedimiento de ciclo de vida del propietario.

| Fase | Evidencia positiva necesaria | Evidencia negativa/fallos que se debe conservar |
|---|---|---|
| Referencia | Dos rutas aptas, siguiente salto utilizable y sonda correcta | Falta la ruta de retorno, el siguiente salto no se resuelve o falla la preparación |
| Preferencia | LOCAL_PREF 200 derivado de c1, salida seleccionada y reenvío correspondiente | El atributo no cambia o hay discrepancia entre RIB y FIB |
| Caída del vecino BGP | Ruta alternativa observada y recuperación sostenida de sondas | Intervalo de pérdida, ausencia de ruta alternativa o errores de captura |
| Restauración | Configuración y comportamiento de reenvío originales | Persiste `shutdown`, deriva de política o pérdida |

Repita la medición del fallo tres veces solo si se verifica correctamente la restauración después de cada repetición; informe las muestras individuales y el intervalo observado.
Conserve las marcas de tiempo y salidas sin procesar en vez de limitarse a un promedio. Etiquete cada resultado como medido, planificado o bloqueado.
La ausencia de ruta, de registro de sonda o una captura vacía no satisface una afirmación positiva.
Complete el capítulo cuando pueda explicar la política, la resolución recursiva del siguiente salto, por qué una sesión activa no demuestra que el servicio funcione, las limitaciones de medición y la restauración verificada.
Continúe con [EVPN](03-datacenter-evpn.md) y después use [BGP de Calico](../calico/04-bgp-deep-dive.md) como continuación especializada en Kubernetes.
Entregue su matriz al [proyecto final de automatización](06-automation-capstone.md) y complete el [cuestionario](../../quizzes/networking/expert/02-routing-policy-convergence-quiz.md).
