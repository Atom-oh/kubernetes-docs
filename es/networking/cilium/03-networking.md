# Modelos de red y VXLAN

> **Base de revisión**: Cilium 1.20.3, Kubernetes 1.33–1.36 probado, Linux 5.10+ o backports equivalentes documentados, como el kernel 4.18 de RHEL 8.10.
> **Última revisión**: 16 de octubre de 2026

## Preparación del entorno de laboratorio

Usa la [guía de instalación](README.md) para preparar un clúster desechable y una versión de Cilium CLI adecuada para la arquitectura. Mantén kubectl con una diferencia máxima de una versión menor respecto del servidor de API; «v1.31 o superior» no es una regla de compatibilidad.

Los ejemplos genéricos de modos requieren al menos dos nodos Linux programables, sin otro CNI de pods, con kube-proxy operativo y un CIDR de pods que no se solape con otros rangos. El ejemplo de enrutamiento nativo también requiere que los nodos compartan un segmento L2. Estas instrucciones no sirven para EKS ENI, GKE Dataplane V2, Cilium administrado en AKS ni para migrar el CNI en un clúster existente.

### Herramientas de análisis de red

Instala tcpdump/Wireshark desde un origen de paquetes admitido por el host de análisis. La captura de paquetes del nodo debe ejecutarse en el nodo o espacio de nombres de red correspondiente, no solo en el portátil desde el que se usa kubectl. Un monitor de agentes informa de eventos BPF emitidos; no sustituye una captura completa de paquetes.

```bash
kubectl config current-context
kubectl -n kube-system get pods -l k8s-app=cilium -o wide
export CILIUM_POD=cilium-REPLACE-WITH-AGENT-ON-TARGET-NODE
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- \
  cilium-dbg monitor --type trace -v
```

Para el perfil VXLAN explícito que se muestra a continuación, captura una muestra acotada en el nodo de trabajo correspondiente:

```bash
sudo tcpdump -nn -i any -c 50 'udp port 8472'
```

Usa el puerto de túnel configurado si es distinto. Genera tráfico entre pods de nodos diferentes: el tráfico entre pods del mismo nodo puede no atravesar la red superpuesta. Una captura vacía puede deberse a que se eligió el nodo, la interfaz, el puerto o la ruta de tráfico incorrectos, y no necesariamente a un fallo de red.

## Comparación de modelos de red de contenedores

Los espacios de nombres del host, los puentes y los transportes entre nodos describen aspectos distintos de la red y pueden coexistir. No constituyen una clasificación universal de rendimiento o seguridad.

| Modelo | Mecanismo | Compromiso importante |
|---|---|---|
| Red del host | Un pod comparte el espacio de nombres de red del nodo | Conflictos de puertos y menor aislamiento entre espacios de nombres de red; no ofrece automáticamente el mejor rendimiento de aplicación |
| Puente | Un puente virtual L2 conecta interfaces | La comunicación entre nodos sigue necesitando enrutamiento/transporte; Cilium no requiere un puente Linux para cada endpoint |
| Red superpuesta (overlay) | El tráfico encapsulado atraviesa una red IP subyacente | Añade cabeceras y procesamiento, pero la red subyacente no necesita enrutar cada prefijo de pods |
| Enrutamiento nativo/subyacente | La red puede enrutar las direcciones de las cargas de trabajo | Requiere rutas correctas de reenvío y retorno, además de planificar direcciones; no proporciona ni elimina por sí mismo las políticas o el cifrado |

### Modos de red de Cilium

El valor `routingMode` de Cilium es `tunnel` o `native`. VXLAN y Geneve son las opciones de protocolo de túnel. La integración con IPAM de la nube es otra dimensión de configuración, a menudo combinada con un plano de datos nativo; no es un tercer valor de `routingMode`. BGP anuncia rutas, pero no es un modo de reenvío de paquetes independiente.

## Análisis detallado de la tecnología VXLAN

VXLAN transporta una trama Ethernet interna mediante UDP sobre una red IP. Un VTEP encapsula y desencapsula el tráfico; el VNI de 24 bits ofrece un espacio teórico de 2^24 identificadores. Esto no significa que una implementación de Kubernetes admita 16 millones de inquilinos.

El puerto de destino UDP estandarizado para VXLAN es 4789. **Cilium usa UDP 8472 de forma predeterminada** para VXLAN y UDP 6081 para Geneve; ambos puertos se pueden configurar. Cilium puede incluir metadatos de identidad de seguridad en la encapsulación, por lo que no se deben equiparar los segmentos VXLAN genéricos con los límites de inquilino o de políticas de Cilium.

### Estructura de un paquete VXLAN

```text
Outer Ethernet
  Outer IP (IPv4 or IPv6)
    Outer UDP (Cilium VXLAN default destination 8472; standard 4789)
      VXLAN header (8 bytes, including VNI)
        Inner Ethernet
          Inner IP packet and transport/application payload
```

IP transporta UDP; la cabecera IP externa no va dentro de la cabecera UDP externa. La segmentación VXLAN no proporciona cifrado, integridad ni aislamiento automático de NetworkPolicy. Restringe adecuadamente la ruta subyacente y configura por separado las políticas o el cifrado.

### Presupuesto de MTU

Para VXLAN normal, sin encapsulación ni opciones adicionales, la reducción del presupuesto de IP interno es la siguiente:

| Familia IP subyacente | IP externa + UDP + VXLAN + Ethernet interno | Presupuesto de IP interno con una MTU IP subyacente de 1.500 bytes |
|---|---|---|
| IPv4 | 20 + 8 + 8 + 14 = 50 bytes | 1.450 bytes |
| IPv6 | 40 + 8 + 8 + 14 = 70 bytes | 1.430 bytes |

La cabecera Ethernet externa queda fuera de la MTU IP subyacente. El cifrado, las opciones de Geneve y otras rutas pueden modificar el presupuesto. La MTU efectiva de la ruta y la MTU del dispositivo veth de un pod no tienen por qué coincidir.

En Cilium 1.20.3, Helm **`MTU` sustituye la MTU de la red subyacente**; después Cilium calcula la sobrecarga de la ruta. `MTU: 0` selecciona la detección automática. Configurar `MTU: 1450` como si significara «MTU final de la carga útil del pod» puede restar de nuevo la sobrecarga del túnel. La detección de interfaces locales tampoco demuestra cuál es la MTU mínima de toda la ruta.

### VXLAN frente a otras encapsulaciones

| Tecnología | Transporte/identificador | Protocolo o puerto | Límite |
|---|---|---|---|
| VXLAN | Ethernet sobre UDP; VNI de 24 bits | UDP 4789 estándar; 8472 predeterminado en Cilium | Cabecera base fija; no cifra el tráfico |
| Geneve | Virtualización de red genérica con opciones ampliables; VNI de 24 bits | UDP 6081 | La longitud de las opciones modifica la sobrecarga |
| GRE | Encapsulación genérica; GRE base no tiene un VNI equivalente al de VXLAN | Protocolo IP 47, no puerto TCP/UDP 47 | Hay que tener en cuenta las extensiones opcionales; «redes ilimitadas» no define una capacidad concreta |
| NVGRE | Ethernet sobre GRE; VSID de 24 bits dentro de la clave GRE | Protocolo IP 47 | Tiene semántica distinta de identificadores y flujos; la compatibilidad depende de la implementación |

## Red superpuesta de Cilium

Si no hay una configuración de plataforma o perfil que la sustituya, Cilium utiliza enrutamiento por túnel con VXLAN. El transporte de pods entre nodos requiere direcciones de nodo alcanzables, tráfico UDP del túnel permitido y una MTU utilizable. La red superpuesta no corrige rangos de direcciones de pods solapados ni permite alcanzar nodos desconectados. Para el recorrido de paquetes, los dispositivos de túnel, el presupuesto de MTU y las variantes de enrutamiento nativo, consulta [Red superpuesta y enrutamiento nativo](09-overlay-native-routing.md).

![Flujo superpuesto entre nodos: procesamiento del endpoint, encapsulación en el VTEP de origen, tránsito por la red subyacente, desencapsulación en destino y entrega al endpoint.](../../.gitbook/assets/en-networking-cilium-03-networking-2.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-cilium-03-networking-2.html)

La figura representa un flujo conceptual. Sus direcciones no constituyen un plan de asignación IPAM por nodo; los bloques de pods reales de cada nodo deben asignarse de forma coherente y sin solapamientos. Las políticas se aplican donde estén configuradas, y los hooks de origen y destino pueden diferir.

1. Cilium identifica el endpoint o nodo remoto a partir del estado del plano de control y del plano de datos.
2. El origen encapsula el paquete del pod correspondiente y lo envía usando las direcciones de los nodos de la red subyacente.
3. El destino desencapsula el paquete interno y lo procesa o entrega.
4. Los eventos del plano de datos, el estado de las rutas y las capturas ayudan a localizar fallos; la ausencia de un solo evento no identifica por sí sola la causa.

## Mecanismos de enrutamiento

### Encapsulación

La red subyacente solo necesita la ruta entre nodos o túneles, en lugar de una ruta para cada prefijo de pods. La sobrecarga incluye cabeceras y procesamiento. Las tramas más grandes reducen la sobrecarga relativa solo si toda la ruta admite la MTU elegida.

### Enrutamiento nativo

El nodo y la red subyacente deben enrutar las direcciones de los pods, incluido el tráfico de retorno. Las rutas pueden proceder de una red de nube, un router, una configuración estática u otro componente de enrutamiento. Habilitar el modo nativo no inicia BGP automáticamente ni anuncia todos los CIDR de pods.

`autoDirectNodeRoutes: true` instala rutas directas a los PodCIDR de los nodos que comparten una red L2. Si hay varios segmentos L2, `directRoutingSkipUnreachable` puede omitir las rutas directas inalcanzables mientras otra ruta enrutada, que funcione de forma independiente, las gestiona. No cambia a túneles superpuestos como alternativa.

**No combines el enrutamiento por túnel con `autoDirectNodeRoutes: true`: Cilium 1.20.3 rechaza explícitamente esta combinación al iniciar.** La antigua receta del «modo híbrido» no era válida. El enrutamiento nativo sí puede coexistir con encapsulación específica de una función, como una ruta DSR de Geneve configurada; se trata de una función de servicio independiente.

El plano de control BGP de Cilium anuncia a sus pares los prefijos de pods o servicios que se hayan configurado. **No programa el plano de datos local** y no se debe tratar como el componente que proporciona automáticamente las rutas que falten dentro del clúster.

## Técnicas de optimización del rendimiento

Mide con el mismo protocolo, tamaño de carga útil, concurrencia, ubicación de nodos, políticas, cifrado y configuración del proxy antes de comparar modos. Quitar una cabecera de encapsulación no garantiza una menor latencia de aplicación.

- **Plano de datos:** el balanceo de carga por socket, la aceleración XDP admitida y DSR se aplican a rutas concretas. VXLAN y el enrutamiento nativo no los habilitan automáticamente.
- **Seguimiento de conexiones:** el seguimiento BPF de conexiones de Cilium y conntrack de netfilter de Linux son mecanismos de estado distintos. Evitar una ruta de netfilter no significa que todo el tráfico establecido deje de usar el estado de conexiones de Cilium.
- **Mapas:** dimensiona los mapas según la capacidad real y la presión de memoria. La expulsión LRU es útil para cachés, pero no es una optimización universal para todos los mapas.
- **Ajustes del host:** la colocación de CPU/NUMA, la distribución/coalescencia de IRQ y la configuración de colas pueden ayudar o perjudicar determinadas cargas de trabajo. Las páginas enormes no son un acelerador general de Cilium; exige pruebas del consumidor y el entorno concretos.

## Redes específicas de cada proveedor de nube

| Entorno | Distinción correcta |
|---|---|
| IPAM de AWS ENI | Cilium asigna direcciones ENI enrutables desde la VPC y requiere permisos IAM del operador, acceso a la API, subredes y capacidad de instancias. Los grupos de seguridad de ENI complementan las políticas de Cilium; esto no activa automáticamente la función de branch ENI por pod del CNI de AWS VPC |
| Plataformas de EKS | El uso de un CNI alternativo en nodos EC2 normales tiene responsabilidades de soporte propias. Fargate y EKS Auto Mode no permiten sustituir su CNI por este perfil genérico de laboratorio. Hybrid Nodes tiene una ruta de instalación admitida independiente |
| Google Cloud | Cilium autoadministrado upstream puede usar IPAM de ámbito de host de Kubernetes y rangos de alias enrutables. GKE Dataplane V2 administrado usa Cilium/`anetd` administrado por Google; no instales otro plano de datos upstream encima ni supongas que expone las mismas funciones |
| Azure | Azure CNI Powered by Cilium lo administra AKS con IPAM delegado. Azure IPAM upstream está dirigido a clústeres autoadministrados en Azure VM/VMSS; AKS BYOCNI es otro modelo de despliegue que debe seleccionarse explícitamente |

La configuración de cortafuegos o grupos de seguridad de la nube no se crea automáticamente con todas las políticas de Cilium. Primero elige la guía de plataforma y el modelo de soporte.

## Laboratorio: configuración de modos de red de Cilium y pruebas de rendimiento

### Seleccionar un modo en un clúster nuevo y preparado

Guarda este archivo común y, antes, sustituye el CIDR de pods si se solapa con los rangos de nodos, servicios, VPC o redes conectadas. Mantén el rango elegido coherente con la configuración del clúster/kube-proxy y con `ipv4NativeRoutingCIDR` del perfil nativo; cambiar un solo archivo no basta. `kubeProxyReplacement: false` presupone deliberadamente que kube-proxy funciona. Estos son valores de Helm, no un ConfigMap que se aplique con kubectl.

**`lab-common.yaml`**

```yaml
kubeProxyReplacement: false
ipv4:
  enabled: true
ipv6:
  enabled: false
ipam:
  mode: cluster-pool
  operator:
    clusterPoolIPv4PodCIDRList:
    - 10.244.0.0/16
    clusterPoolIPv4MaskSize: 24
MTU: 0
hubble:
  enabled: true
  relay:
    enabled: true
  ui:
    enabled: true
```

Elige exactamente uno de los siguientes archivos de modo. Para comparar modos, utiliza clústeres desechables distintos en vez de reinstalar el CNI repetidamente en un clúster activo.

**`mode-vxlan.yaml`**

```yaml
routingMode: tunnel
tunnelProtocol: vxlan
tunnelPort: 8472
autoDirectNodeRoutes: false
```

**`mode-geneve.yaml`**

```yaml
routingMode: tunnel
tunnelProtocol: geneve
tunnelPort: 6081
autoDirectNodeRoutes: false
```

**`mode-native.yaml`**

```yaml
routingMode: native
ipv4NativeRoutingCIDR: 10.244.0.0/16
autoDirectNodeRoutes: true
```

Para el ejemplo VXLAN:

```bash
kubectl config current-context
cilium install --version 1.20.3 --values lab-common.yaml --values mode-vxlan.yaml
cilium status --wait
```

Selecciona `mode-geneve.yaml` o `mode-native.yaml` solo si se cumplen sus requisitos de red. No apliques los ejemplos obsoletos de ConfigMap `tunnel: vxlan`, `ipv4-range` o `ipv4-service-range`; configura IPAM mediante los campos Helm admitidos.

### Pruebas de rendimiento de red

Usa las cargas de trabajo de rendimiento mantenidas por la CLI; no des por sentado que un manifiesto ajeno crea `netperf-client` y `netperf-server`. En el clúster desechable preparado:

```bash
cilium connectivity perf --test-namespace cilium-net-perf \
  --namespace-labels docs-audit-lab=cilium-networking-03 \
  --duration 10s --samples 2 --crr --udp \
  --host-net=false --pod-net=true --same-node=true --other-node=true \
  --report-dir ./cilium-net-perf-results
```

La duración se aplica a cada caso de prueba y muestra; no representa una ejecución total de diez segundos. Esto crea cargas de prueba y genera tráfico de red. CLI 0.20.1 añade un sufijo de secuencia al espacio de nombres (`cilium-net-perf-1` para la suite única predeterminada). Guarda junto con los resultados las versiones, la ubicación de las cargas y la configuración; no se garantiza ninguna cifra de rendimiento o latencia.

Las pruebas TCP de solicitud/respuesta, de tasa de conexiones y de flujo continuo responden preguntas distintas. Si usas una configuración de iperf3 preparada de forma independiente, la prueba UDP sigue necesitando la conexión de control TCP y una ruta de datos UDP; no basta con que un servicio exponga solo TCP 5201. La tasa UDP ofrecida no equivale al rendimiento medido que se consigue.

Estos ejemplos se comprobaron con valores oficiales actuales, esquemas de API y el código fuente de la CLI. Esta auditoría no generó las plantillas Helm, no desplegó un clúster ni ejecutó un benchmark de red después de reiniciar el host; valida el entorno completo de plataforma y laboratorio antes de confiar en los resultados.

## Fuentes

- [Enrutamiento de Cilium 1.20.3](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/concepts/routing.rst), [valores de Helm](https://github.com/cilium/cilium/blob/v1.20.3/install/kubernetes/cilium/values.yaml), [validación al inicio](https://github.com/cilium/cilium/blob/v1.20.3/daemon/cmd/daemon_main.go), [cálculo de MTU](https://github.com/cilium/cilium/blob/v1.20.3/pkg/mtu/mtu.go), [opción MTU](https://github.com/cilium/cilium/blob/v1.20.3/pkg/mtu/cell.go)
- [RFC 7348 de VXLAN](https://www.rfc-editor.org/rfc/rfc7348.txt), [RFC 8926 de Geneve](https://www.rfc-editor.org/rfc/rfc8926.txt), [RFC 2784 de GRE](https://www.rfc-editor.org/rfc/rfc2784.txt), [RFC 7637 de NVGRE](https://www.rfc-editor.org/rfc/rfc7637.txt)
- [Plano de control BGP](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/bgp-control-plane/bgp-control-plane.rst), [AWS ENI](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/concepts/ipam/eni.rst), [CNI alternativos en EKS](https://docs.aws.amazon.com/eks/latest/userguide/alternate-cni-plugins.html), [GKE Dataplane V2](https://docs.cloud.google.com/kubernetes-engine/docs/concepts/dataplane-v2), [IPAM de Azure](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/concepts/ipam/azure.rst)
- [Opciones de conexión/rendimiento de CLI 0.20.1](https://github.com/cilium/cilium-cli/blob/v0.20.1/vendor/github.com/cilium/cilium/cilium-cli/cli/connectivity.go), [uso de iperf3](https://software.es.net/iperf/invoking.html), [diferencias de versión de kubectl](https://kubernetes.io/releases/version-skew-policy/)

[Vuelve a la página principal](README.md)

## Cuestionario

Completa los [ejercicios de validación de red y consulta los resultados esperados](../../quizzes/networking/cilium/03-networking-quiz.md).
