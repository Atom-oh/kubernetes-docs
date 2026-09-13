# Parte 3: Modos de red

> **Base de revisión**: Calico Open Source 3.32.2 / operador 1.42.6; Kubernetes 1.34–1.36 es el intervalo probado de Calico 3.32.
> **Última actualización**: 12 de septiembre de 2026. Los valores históricos de benchmark se conservan como informes no verificados, no como mediciones nuevas.

## Alcance y selección del modo

Este capítulo trata las redes e IPAM de Pods Linux gestionados por Calico. En EKS de solo políticas, Amazon VPC CNI sigue gestionando la red Pod; crear IPPools de Calico no convierte esa instalación en overlay. Los ejemplos son diseños alternativos, no manifiestos para aplicar juntos ni sobre el pool ya creado del laboratorio introductorio. La auditoría no realizó migraciones ni benchmarks de red.

| Opción | Significado | Límite importante |
|---|---|---|
| IPIP | IPv4 dentro de IPv4, protocolo IP 4 | Calico IPIP solo admite IPv4; la red subyacente debe permitirlo |
| VXLAN | Ethernet interno transportado por UDP, puerto Calico predeterminado 4789 | IPv4 e IPv6 exteriores tienen distinta sobrecarga; puerto/VNI configurables |
| Direct / sin encapsulación | Paquetes IP Pod enrutados sin overlay de red Pod | La red subyacente y el retorno deben enrutar direcciones Pod |
| CrossSubnet | Ajuste de IPIP o VXLAN | Encapsula tráfico entre nodos solo cuando sus direcciones pertinentes están en subredes configuradas diferentes |

`Always` afecta al tráfico elegible entre nodos hacia direcciones del pool configurado; el tráfico dentro del mismo nodo no necesita un túnel físico. `Never` desactiva esa encapsulación, no toda la red. CrossSubnet no detecta AZ, regiones ni enlaces WAN: dos subredes de una misma AZ pueden necesitar encapsulación. Inspeccione la dirección y máscara del nodo usadas por Calico.

Los valores predeterminados dependen de instalación/proveedor y plano de datos. No existe una regla universal de que «IPIP es el predeterminado en todas las nubes», ni garantía de que Direct siempre sea más rápido. La [guía de overlay](https://docs.tigera.io/calico/latest/networking/configuring/vxlan-ipip) describe las rutas admitidas.

### Enrutamiento y encapsulación son elecciones separadas

Por defecto, Felix programa rutas de pools VXLAN, mientras confd/BIRD programan las de clúster para IPIP y pools sin encapsular. Calico 3.32 también admite `Installation.spec.calicoNetwork.clusterRoutingMode: Felix` para esas rutas no VXLAN. Los ajustes inferiores correspondientes son Felix `programClusterRoutes: Enabled` y BGP `programClusterRoutes: Disabled`; use el ajuste del operador cuando gestione la instalación. Los anuncios BGP externos siguen requiriendo BGP. Rutas estáticas o una red enrutada adecuada también pueden dar conectividad subyacente, así que BGP y adyacencia en la misma L2 no son requisitos universales de todo diseño sin encapsular.

## Estructura de paquetes y sobrecarga

Lo siguiente usa una **MTU IP de la red subyacente**. La cabecera Ethernet exterior queda fuera de esa MTU. Se supone que no hay opciones IPv4 ni etiquetas VLAN internas adicionales; las opciones TCP y otras encapsulaciones pueden reducir más la carga útil.

```text
Direct: outer Ethernet | Pod IP | TCP or UDP | payload
IPIP:   outer Ethernet | outer IPv4 | Pod IPv4 | TCP or UDP | payload
VXLAN:  outer Ethernet | outer IP | UDP | VXLAN | inner Ethernet | Pod IP | TCP or UDP | payload
```

| Transporte | Sobrecarga sobre el paquete IP Pod | MTU IP Pod con MTU IP subyacente de 1500 |
|---|---|---|
| Direct, sin otro túnel | 0 | 1500 |
| IPIP, IPv4 exterior | 20 | 1480 |
| VXLAN, IPv4 exterior | 20 + 8 + 8 + 14 = 50 | 1450 |
| VXLAN, IPv6 exterior | 40 + 8 + 8 + 14 = 70 | 1430 |
| WireGuard, IPv4 exterior | 60 | 1440 |
| WireGuard, IPv6 exterior | 80 | 1420 |

En VXLAN, los 14 bytes de sobrecarga son la **cabecera Ethernet interior**, no la exterior. TCP simple tiene una cabecera mínima de 20 bytes; UDP, de 8 bytes. Así, bajo estas suposiciones, un paquete IP IPv4 de 1500 bytes puede contener hasta 1460 bytes de carga TCP o 1472 de UDP. La etiqueta compartida original «TCP/UDP = 20 bytes» era incorrecta.

IPIP usa el número de protocolo 4, no el puerto TCP/UDP 4. El VNI VXLAN habitual de Calico es 4096 y su puerto UDP predeterminado es 4789, pero ambos son configurables. Otras implementaciones VXLAN actuales pueden usar 8472; no se limita a software obsoleto. Consulte [IP-in-IP](https://www.rfc-editor.org/rfc/rfc2003) y [VXLAN](https://www.rfc-editor.org/rfc/rfc7348).

### Rutas de paquetes ilustradas

![Los paquetes IPv4 atraviesan el túnel IPIP del kernel de origen y la ruta de desencapsulación del kernel de destino.](../../.gitbook/assets/en-networking-calico-03-networking-modes-2.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-03-networking-modes-2.html)

Las columnas «Felix» representan rutas/políticas del kernel programadas por Felix; los paquetes no atraviesan su daemon. Es la ruta IPv4 entre nodos, no tráfico intranodo ni un mecanismo de cifrado.

![Dos VTEP de Calico encapsulan y desencapsulan una trama interna sobre UDP.](../../.gitbook/assets/en-networking-calico-03-networking-modes-3.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-03-networking-modes-3.html)

4789 y VNI 4096 son los valores predeterminados ilustrados. La sobrecarga de 50 bytes y MTU 1450 se aplican a una ruta de 1500 bytes con IPv4 exterior y las cabeceras indicadas, no a toda red o familia de direcciones.

### Ejemplo CrossSubnet

Con direcciones de nodo 10.0.1.10/24 y 10.0.1.11/24, la ruta dentro de la subred puede ir sin encapsular. Un peer en 10.0.2.20/24 necesita encapsulación en el diseño CrossSubnet. Las máscaras incorrectas pueden cambiar el resultado aunque los nombres de subred de nube parezcan correctos. CrossSubnet no establece conectividad entre VPC/regiones ni proporciona cifrado.

![Los nodos de la misma subred usan una ruta sin encapsular, mientras IPIP transporta tráfico entre dos subredes de nodos configuradas.](../../.gitbook/assets/en-networking-calico-03-networking-modes-1.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-03-networking-modes-1.html)

Las direcciones/máscaras determinan la elección. Los valores 1500/1480 suponen una red IPv4 subyacente de 1500 bytes; las cargas deben seguir usando la MTU mínima de sus rutas posibles. La MTU de interfaz no aumenta dinámicamente para un flujo de la misma subred.

### Diagnóstico de nodos

Ejecute estos comandos de solo lectura en un **namespace de red de nodo Linux** autorizado, no en un Pod de aplicación ordinario. Las interfaces solo existen para el modo habilitado. Los valores dependen de la instalación real.

```bash
ip link show tunl0
ip link show vxlan.calico
bridge fdb show dev vxlan.calico
ip route show
```

Una ruta Pod local típica es una ruta de host como `10.244.1.5/32 dev cali…`; no enrute un /24 o /26 completo al veth de un Pod. Un bloque agregado puede tener una ruta blackhole y rutas Pod más específicas. Los bloques remotos pueden usar un túnel o un nodo/router de siguiente salto, y la etiqueta de protocolo depende de si programa BIRD o Felix.

![Direct, IPIP y VXLAN muestran diferentes envolturas de paquetes entre Pods.](../../.gitbook/assets/en-networking-calico-03-networking-modes-5.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-03-networking-modes-5.html)

Son ejemplos IPv4 con red subyacente de 1500 bytes. El diagrama compara envolturas, no velocidad medida ni comportamiento idéntico del plano de control. Incluya otras encapsulaciones y rutas de Service al seleccionar la MTU de la carga.

## Configurar un pool mediante su propietario

Los ejemplos `kubectl …projectcalico.org` suponen la API agregada Calico de la introducción, o una configuración nativa v3 adecuada. Sin ella, use un calicoctl compatible para recursos lógicos Calico. Los comandos del operador solo se aplican a sus instalaciones. Los rangos de pools también deben evitar conflictos con Services y nodos/red subyacente.

Use un único propietario de configuración. Los pools de `Installation.spec.calicoNetwork.ipPools` los reconcilia el operador; edite esa lista deseada mediante su propietario en vez de aplicar IPPools competidores. Los pools independientes usan la API IPPool. En ambos casos, verifique primero CIDR Pod real del clúster, ausencia de solapamiento, tipo IPAM y asignaciones existentes.

```bash
kubectl get installation.operator.tigera.io default -o yaml
kubectl get ippools.projectcalico.org -o yaml
calicoctl ipam show --show-blocks
```

Para un pool del operador, esto es un **fragmento de entrada** de la lista `ipPools` existente. Conserve las demás entradas y campos Installation. No lo cree sobre el pool /16 ya asignado del laboratorio introductorio:

```yaml
- name: mode-demo-pool
  cidr: 10.244.0.0/16
  blockSize: 26
  encapsulation: VXLAN
  natOutgoing: Enabled
  nodeSelector: all()
```

Para un pool independiente recién planificado, el recurso IPv4 equivalente aparece abajo. Es una alternativa a la entrada del operador, no un pool solapado adicional. El CIDR es un ejemplo que debe encajar en el clúster real y no colisionar con ningún pool existente.

```yaml
apiVersion: projectcalico.org/v3
kind: IPPool
metadata:
  name: mode-demo-pool
spec:
  cidr: 10.244.0.0/16
  blockSize: 26
  ipipMode: Never
  vxlanMode: Always
  natOutgoing: true
  nodeSelector: all()
```

Seleccione una fila, no varios recursos con el mismo CIDR:

| Diseño IPv4 | IPPool `ipipMode` | IPPool `vxlanMode` | Operador `encapsulation` |
|---|---|---|---|
| IPIP Always | Always | Never | IPIP |
| IPIP CrossSubnet | CrossSubnet | Never | IPIPCrossSubnet |
| VXLAN Always | Never | Always | VXLAN |
| VXLAN CrossSubnet | Never | CrossSubnet | VXLANCrossSubnet |
| Direct | Never | Never | None |

IPIP y VXLAN no pueden habilitarse simultáneamente en un pool. `encapsulation` es un campo del pool del operador, no el del IPPool independiente. En la instalación normal con API agregada, se rechaza crear pools solapados. Con CRD nativos v3, en vista previa técnica, la validación es asíncrona y un pool creado puede recibir una condición Disabled; crearlo con éxito no demuestra que pueda asignar direcciones.

El esquema Installation de Calico 3.32 permite una lista de pools de hasta 25 entradas, sujeta a validación del controlador y restricciones de plataforma. Los ejemplos antiguos que afirmaban exactamente un pool IPv4 no son un límite actual universal.

### Enrutamiento directo con BGP externo

Si usa BGP externo, configure peers y rutas de retorno reales antes de eliminar un overlay. Declarar un peer no configura el router físico ni demuestra aceptación de rutas. Este ejemplo independiente no complementa un laboratorio VXLAN con BGP desactivado:

```yaml
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: example-rack-tor
spec:
  peerIP: 192.0.2.1
  asNumber: 65001
  nodeSelector: rack == 'rack1'
```

Sustituya la dirección de documentación y el ASN, etiquete los nodos previstos y valide filtros/gestión de bucles AS en cada rack. `natOutgoing: false` solo es adecuado con retorno y NAT externo necesario diseñados; BGP no hace por sí solo que direcciones Pod privadas sean enrutables en Internet. Para cambios de malla/RR, use la [guía de transición BGP](02-architecture.md) y [BGP en profundidad](04-bgp-deep-dive.md).

![Un paquete Pod sin encapsular cruza una red subyacente enrutada cuyas rutas proporciona BGP en este ejemplo.](../../.gitbook/assets/en-networking-calico-03-networking-modes-4.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-03-networking-modes-4.html)

Esto ilustra un diseño BGP, no exige que todo diseño Direct lo use. El valor 1500 supone esa MTU útil y ningún otro túnel; la transferencia de Service eBPF o el cifrado pueden imponer una MTU menor.

## NAT y selección de pools

Con `natOutgoing: true`, Calico normalmente aplica SNAT a direcciones de origen de ese pool cuando el destino queda fuera de **todos los IPPools de Calico**. No es solo una comprobación de «salir del clúster». Incluso un pool desactivado puede identificar un rango destino sin NAT; eliminarlo puede cambiar el comportamiento. Otros ajustes Felix pueden excluir IP de hosts. NAT no concede permisos NetworkPolicy. Consulte [NAT de salida](https://docs.tigera.io/calico/latest/networking/configuring/workloads-outside-cluster).

### Asignación automática basada en topología

Este ejemplo separado tiene dos pools /18 disjuntos dentro de un rango de clúster /16. No debe coexistir con un pool padre /16 ya asignado. No elimine un pool padre en uso solo para adaptar el ejemplo.

```yaml
apiVersion: projectcalico.org/v3
kind: IPPool
metadata:
  name: zone-a-pool
spec:
  cidr: 10.244.0.0/18
  ipipMode: Never
  vxlanMode: CrossSubnet
  natOutgoing: true
  nodeSelector: topology.kubernetes.io/zone == 'ap-northeast-2a'
---
apiVersion: projectcalico.org/v3
kind: IPPool
metadata:
  name: zone-b-pool
spec:
  cidr: 10.244.64.0/18
  ipipMode: Never
  vxlanMode: CrossSubnet
  natOutgoing: true
  nodeSelector: topology.kubernetes.io/zone == 'ap-northeast-2b'
```

Para asignación automática, asegure que cada nodo previsto coincida con un pool elegible; el selector no programa Pods. Las etiquetas de zona anteriores eligen pools, mientras CrossSubnet sigue usando direcciones/máscaras para decidir encapsulación.

### Solicitudes explícitas de pool por namespace o Pod

Cree y verifique un pool adecuado antes de solicitarlo. El fragmento añade una anotación mediante el propietario actual del namespace; no es su sustitución completa. Las anotaciones Pod prevalecen sobre las de namespace, que prevalecen sobre la configuración de pools CNI.

```yaml
metadata:
  annotations:
    cni.projectcalico.org/ipv4pools: '["production-pool"]'
```

`production-pool` debe existir, estar habilitado y disponer de direcciones suficientes. `assignmentMode: Manual` puede excluirlo de la selección automática permitiendo solicitudes explícitas. **Ni un selector de pool ni esta anotación son límites de seguridad.** La [implementación IPAM publicada](https://github.com/projectcalico/calico/blob/v3.32.2/libcalico-go/lib/ipam/ipam.go) ignora deliberadamente selectores de nodo/namespace al solicitar explícitamente un pool habilitado. Controle quién puede solicitar pools si sus rangos implican confianza. Los Pods existentes conservan sus direcciones; cambiar anotaciones no los renumera.

## Límites de nube y plataforma

| Entorno | Orientación |
|---|---|
| AWS EC2 autogestionado | Compruebe protocolo IP 4 o UDP VXLAN, rutas, comprobaciones de origen/destino y retorno para el modo elegido |
| EKS con Amazon VPC CNI | La red Pod predeterminada es VPC CNI, no VXLAN Calico; Calico de solo políticas no gestiona estos pools |
| EKS con red Calico completa | Instalación separada planificada con Calico CNI/IPAM; use el [procedimiento oficial EKS](https://docs.tigera.io/calico/latest/getting-started/kubernetes/managed-public-cloud/eks) |
| Azure con red gestionada por Calico | La guía overlay admite VXLAN donde IPIP no está soportado; configurar UDR no arregla encapsulación IPIP no admitida |
| AKS | Use la integración Azure CNI/políticas específica admitida, no una suposición genérica de overlay Calico |
| GCE / GKE | El enrutamiento GCE autogestionado difiere de GKE gestionado; [GKE Dataplane V2 usa Cilium](https://cloud.google.com/kubernetes-engine/docs/concepts/dataplane-v2) |
| Local | Direct, rutas estáticas/BGP u overlay dependen de la conectividad subyacente; no hay una opción universalmente más rápida |
| Integración OpenStack Neutron | La guía overlay citada excluye esta integración; no copie instrucciones Kubernetes sin el procedimiento de su plataforma |

Este capítulo no ofrece una receta CNI personalizada para EKS Auto Mode o Fargate. Desactivar BGP en VXLAN significa que esa configuración no lo necesita, no que AWS carezca de servicios BGP. Windows también tiene limitaciones independientes, incluido no admitir Calico IPIP ni VXLAN CrossSubnet.

## Configuración y validación de MTU

Use la MTU útil mínima de todas las rutas posibles, incluidas las de cifrado y Service. La [guía MTU de Calico](https://docs.tigera.io/calico/latest/networking/configuring/mtu) explica detección automática y propiedad operador/manifiestos. `mtuIfacePattern` selecciona interfaces consideradas durante la detección; no es un interruptor ni demuestra la MTU extremo a extremo.

**No sume a ciegas las sobrecargas IPIP y WireGuard.** En una implementación mixta normal, WireGuard se usa entre peers habilitados; IPIP/VXLAN en otras rutas. Elija la menor MTU aplicable. Con una ruta real de 1500 bytes, WireGuard IPv4 más IPIP significa `min(1440, 1480) = 1440`, no `1500 − 60 − 20 = 1420`. WireGuard con IPv6 exterior tiene, por separado, 80 bytes de sobrecarga.

AKS tiene una excepción WireGuard documentada: la ruta subyacente puede ser 1400 aunque la interfaz muestre 1500, dando 1340 para WireGuard IPv4 o 1320 para IPv6. La ruta NodePort eBPF también usa VXLAN, por lo que un pool Pod sin encapsular no implica por sí solo MTU de 1500 bytes.

En una instalación del operador, tras determinar que **1450 es adecuado para esta ruta VXLAN IPv4 concreta**, combínelo con el estado deseado existente:


```bash
kubectl patch installation.operator.tigera.io default --type merge   -p '{"spec":{"calicoNetwork":{"mtu":1450}}}'
```

En instalaciones mediante manifiestos, el ajuste documentado es `calico-config.data.veth_mtu`; actualice ese ConfigMap y despliegue gradualmente el DaemonSet de nodos según el procedimiento. No aplique ese procedimiento a un Deployment del operador. **La MTU actualizada se aplica a cargas nuevas.** Reiniciar calico-node no recrea por sí solo los Pods de aplicación ni demuestra que su MTU haya cambiado.

| Ejemplo de MTU IP subyacente | IPIP IPv4 | VXLAN IPv4 | VXLAN IPv6 | WireGuard IPv4 | WireGuard IPv6 |
|---|---|---|---|---|---|
| 9000 | 8980 | 8950 | 8930 | 8940 | 8920 |
| 9001, cuando la ruta AWS realmente lo admite | 8981 | 8951 | 8931 | 8941 | 8921 |

Toda la ruta debe admitir jumbo; ajustar una interfaz no basta. Valide la ruta de la carga desde una carga de diagnóstico, no solo desde el nodo.

Estas comprobaciones acotadas suponen un Pod Linux de diagnóstico aprobado con iputils y permisos necesarios. Use nombres/direcciones reales. Los tamaños siguientes son ejemplos **ICMP IPv4**: añada 20 bytes IPv4 y 8 ICMP. IPv6 exige otro cálculo; probes correctos no demuestran que todas las rutas ECMP sean seguras.

```bash
CHECK_NS=calico-demo
CHECK_POD=diagnostic-client
CHECK_TARGET=diagnostic-server
DEST_IPV4=$(kubectl -n "$CHECK_NS" get pod "$CHECK_TARGET" -o jsonpath='{.status.podIP}')
case "$DEST_IPV4" in
  ""|*:*) echo "Select a ready target Pod with an IPv4 address" >&2; exit 1 ;;
esac
kubectl -n "$CHECK_NS" exec "$CHECK_POD" -- ip link show eth0
kubectl -n "$CHECK_NS" exec "$CHECK_POD" -- ping -4 -c 3 -W 2 -M do -s 1472 "$DEST_IPV4"
kubectl -n "$CHECK_NS" exec "$CHECK_POD" -- ping -4 -c 3 -W 2 -M do -s 1452 "$DEST_IPV4"
kubectl -n "$CHECK_NS" exec "$CHECK_POD" -- ping -4 -c 3 -W 2 -M do -s 1422 "$DEST_IPV4"
```

Las tres cargas prueban paquetes IP de 1500, 1480 y 1450 bytes. Los fallos pueden deberse a políticas/filtrado ICMP además de MTU. En capturas, inspeccione mensajes IPv4 de fragmentación necesaria e IPv6 Packet Too Big con permisos adecuados; el filtro original solo IPv4 no cubría IPv6.

## Cambiar modos o migrar direcciones deliberadamente

Cambiar encapsulación no equivale a cambiar CIDR Pod o tamaño de bloque. Calico permite cambiar encapsulación, pero puede interrumpir conexiones activas. Valide permisos subyacentes, rutas, MTU real, soporte del plano de datos y recuperación antes del mantenimiento. No reinicie todos los nodos ni todos los Deployments de un namespace como paso genérico.

Para un pool del operador, cambie `encapsulation` en la lista Installation deseada, conservando los demás pools/ajustes. **Solo para un IPPool IPv4 independiente**, este ejemplo cambia ambos campos de encapsulación manteniendo CIDR y asignación:

```bash
POOL_NAME=mode-demo-pool
kubectl get ippool.projectcalico.org "$POOL_NAME" -o yaml > pool-before.yaml
kubectl patch ippool.projectcalico.org "$POOL_NAME" --type merge   -p '{"spec":{"ipipMode":"Never","vxlanMode":"Always"}}'
```

No garantiza ausencia de interrupciones. Si procede una transición planificada Direct a IPIP CrossSubnet, los campos son `ipipMode: CrossSubnet` / `vxlanMode: Never`; no requiere sustituir el CIDR. Recree únicamente las cargas necesarias para el plan validado de MTU/direcciones, usando su estrategia de rollout/readiness. Los [PodDisruptionBudgets](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/) no limitan el rolling update de un controlador Deployment.

### Migración independiente de IPPool/CIDR

Use el [procedimiento de migración de pools](https://docs.tigera.io/calico/latest/networking/ipam/migrate-pools) solo cuando Calico gestione IPAM y el diseño de red/orquestador lo admita.

1. Inventaríe pools, CIDR de clúster Kubernetes/kube-proxy, solicitudes explícitas y todas las asignaciones. Un pool fuera del CIDR puede cambiar NAT o romper tráfico; el 10.245/16 antiguo no es automáticamente compatible con el clúster introductorio 10.244/16.
2. Añada mediante su propietario un pool verificado sin solapamiento y pruebe asignaciones nuevas antes de retirar el antiguo. Conserve este para las cargas existentes.
3. Detenga asignaciones nuevas en el pool antiguo mediante el propietario adecuado. `spec.disabled: true` en un pool independiente lo excluye de IPAM. `nodeSelector: "!all()"` del operador desactiva la **selección automática**, pero las solicitudes explícitas evitan selectores; elimínelas también.
4. Migre cargas elegidas por lotes controlados, verificando direcciones, MTU, rutas, políticas y readiness. Recrear Pods puede interrumpir aplicaciones y cambiar IP; un pool nuevo no garantiza reversión transparente.
5. Retire el pool antiguo solo después de contabilizar asignaciones y dependencias restantes, incluidos túneles o LoadBalancer cuando corresponda. Listar Pods no basta. Considere sus efectos NAT/rutas al retirarlo de la configuración del propietario.

Comprobaciones útiles de solo lectura:


```bash
kubectl get ippools.projectcalico.org -o yaml
calicoctl ipam show --show-blocks
calicoctl ipam show --show-borrowed
kubectl get pods --all-namespaces -o wide
```

El tamaño de bloque es otra consideración de migración; no cambie la estructura inmutable de asignación sustituyendo un manifiesto de tutorial. El antiguo ejemplo que reiniciaba calico-node «para aplicar inmediatamente el modo» no demostraba la MTU de la carga ni la recuperación de la aplicación.

## Informes de benchmark anteriores: procedencia no verificada

Las páginas inglesa y coreana anteriores contenían cifras distintas y no aportaban resultados brutos, versiones completas, ubicación ni un entorno reproducible. Se conservan ambos registros; no pueden tratarse como un único experimento ni garantías validadas. Esta auditoría no los repitió.

### Registro A: página inglesa anterior

Entorno informado: **3 × c5.xlarge en AWS**, red declarada de 10 Gbps, iperf3 TCP, **un flujo durante 60 segundos**. No se proporcionaron grupo de ubicación, versión Calico/kernel ni método de recogida de latencia.

| Métrica informada | Direct | IPIP | VXLAN |
|---|---|---|---|
| Rendimiento, Gbps | 9.41 | 9.12 | 8.89 |
| Latencia p99, µs | 45 | 52 | 61 |
| CPU, % por Gbps | 2.1 | 2.8 | 3.4 |

AWS documenta un límite habitual de 5 Gbps por flujo fuera de un grupo de ubicación de clúster, con excepciones. Por tanto, los valores superiores a 9 Gbps necesitan las condiciones de ubicación/ruta ausentes antes de predecir otro despliegue. «Hasta 10 Gbps» tampoco establece ancho de banda base sostenido. Consulte [ancho de banda EC2](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-network-bandwidth.html).

### Registro B: página coreana anterior

| Métrica informada | Direct | IPIP | VXLAN | Método declarado |
|---|---|---|---|---|
| Rendimiento, Gbps | 9.8 | 9.2 | 8.5 | iperf3, MTU 1500 |
| Latencia, µs (estadístico sin especificar) | 35 | 42 | 55 | netperf TCP_RR |
| Utilización CPU | Baja | Media | Media-alta | A 10 Gbps |
| PPS, millones por segundo | 1.8 | 1.5 | 1.2 | Paquetes de 64 bytes |

No se aportaron hardware, número de muestras ni interpretación exacta de «64 bytes». TCP_RR de netperf suele informar **transacciones por segundo**; un recíproco explícitamente justificado puede estimar el ciclo medio solicitud/respuesta, pero no es p99 ni latencia aislada unidireccional. Falta la salida bruta/conversión de los microsegundos informados.

El tamaño de cabecera no determina por sí solo qué modo es más rápido. Offloads de NIC, kernel/plano de datos, tamaño de paquete, CPU, rutas, reutilización y carga ofrecida pueden cambiar el resultado. Conserve estos registros como historia no verificada y mida el entorno objetivo, en vez de clasificar modos a partir de ellos.

### Probes acotados de cliente para un experimento nuevo

Prepare Pods dedicados con versiones compatibles de iperf3/netperf, listeners de servidor activos y permisos de política necesarios. Los comandos son solo probes de cliente, no reproducen completamente ninguno de los registros. Capture versiones, ubicación nodo/AZ, MTU, tamaños de solicitud/respuesta, salida bruta y repeticiones. Confirme que el servidor tenga IPv4 para este ejemplo.

```bash
set -euo pipefail
BENCH_NS=calico-demo
CLIENT_POD=benchmark-client
SERVER_POD=benchmark-server
SERVER_IP=$(kubectl -n "$BENCH_NS" get pod "$SERVER_POD" -o jsonpath='{.status.podIP}')
: "${SERVER_IP:?Server Pod has no address}"
case "$SERVER_IP" in
  *:*) echo "This example requires an IPv4 server Pod" >&2; exit 1 ;;
esac
kubectl -n "$BENCH_NS" get pods "$CLIENT_POD" "$SERVER_POD" -o wide
kubectl -n "$BENCH_NS" exec "$CLIENT_POD" --   iperf3 -c "$SERVER_IP" -t 30 -P 4 -J > iperf3-result.json
kubectl -n "$BENCH_NS" exec "$CLIENT_POD" --   netperf -H "$SERVER_IP" -t TCP_RR -l 60 > netperf-result.txt
```

El ejemplo iperf3 usa cuatro flujos, por lo que no es el método de flujo único del Registro A. El [manual netperf](https://github.com/HewlettPackard/netperf/blob/master/doc/netperf.txt) define unidades y salidas opcionales de latencia. Aísle la carga de prueba, detenga después solo servidores/recursos propios y no cambie modos de red de producción para reproducir una gráfica sin fuente.

[Descripción general de Calico](README.md) · [Arquitectura](02-architecture.md) · [Siguiente: BGP en profundidad](04-bgp-deep-dive.md) · [Cuestionario de modos de red](../../quizzes/networking/calico/03-networking-modes-quiz.md)
