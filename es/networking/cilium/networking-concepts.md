# Análisis profundo de los conceptos de redes

> **Versión de referencia**: Cilium 1.20.3.
> **Última revisión**: 16 de octubre de 2026.

Este documento ofrece explicaciones detalladas de los conceptos fundamentales de redes necesarios para comprender Cilium. Explora las redes de contenedores, las redes superpuestas, NAT, el enrutamiento, DNS, el balanceo de carga y las políticas. Los ejemplos son conceptuales o muestran configuraciones parciales de Helm/API para entornos de prueba preparados; no son recetas completas de instalación o migración. Verifique los requisitos previos de la plataforma y la versión en [la descripción general de Cilium](README.md); las plataformas administradas no permiten todas las mismas funciones de CNI.

## Objetivos de aprendizaje

Al leer este documento, comprenderá:
- La estructura básica del modelo OSI y de la pila TCP/IP, y la función de cada capa
- Los principios básicos y los métodos de implementación de las redes de contenedores
- Las diferencias entre las redes superpuestas y las redes subyacentes
- Cómo se utilizan en Cilium conceptos fundamentales de redes como NAT, el enrutamiento y DNS

## Tabla de contenido

1. [Modelo OSI y pila TCP/IP](#osi-model-and-tcp-ip-stack)
2. [Fundamentos de las redes de contenedores](#container-networking-basics)
3. [Redes superpuestas](#overlay-networks)
4. [Traducción de direcciones de red (NAT)](#network-address-translation-nat)
5. [Protocolos de enrutamiento](#routing-protocols)
6. [DNS y descubrimiento de servicios](#dns-and-service-discovery)
7. [Conceptos de balanceo de carga](#load-balancing-concepts)
8. [Fundamentos de seguridad de red](#network-security-basics)

## Modelo OSI y pila TCP/IP {#osi-model-and-tcp-ip-stack}

> **Concepto clave**: El modelo OSI es un marco conceptual que clasifica la comunicación de red en 7 capas abstractas, lo que facilita la comprensión de procesos de red complejos.

El modelo OSI (Interconexión de Sistemas Abiertos) es un marco conceptual que clasifica la comunicación de red en 7 capas abstractas. Cada capa se encarga de funciones de red específicas, lo que permite desglosar procesos de red complejos para entenderlos más fácilmente.

### Comparación entre el modelo OSI y el modelo TCP/IP

![Diagrama que relaciona las siete capas de referencia de OSI con las cuatro capas de la pila TCP/IP, con ejemplos de protocolos bajo cada capa OSI.](../../.gitbook/assets/en-networking-cilium-networking-concepts-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-cilium-networking-concepts-0.html)

La correspondencia es una aproximación didáctica, no una especificación de implementación de protocolos. SSL es una denominación obsoleta en la figura; en los sistemas actuales, utilice las versiones de TLS compatibles.

### Modelo OSI de 7 capas

1. **Capa física**
   - Convierte flujos de bits en señales eléctricas, ópticas o inalámbricas
   - Incluye cables, transceptores y señalización física; un switch también implementa funciones de capas superiores
   - Unidad de datos: bit

2. **Capa de enlace de datos**
   - Se encarga de transferir datos entre nodos de una red física
   - Identifica dispositivos mediante direcciones MAC (Control de acceso al medio)
   - Detecta errores y, cuando el protocolo de enlace lo permite, los corrige; la detección de errores de Ethernet no corrige por sí sola las tramas dañadas
   - Unidad de datos: trama
   - Los protocolos Ethernet y Wi-Fi funcionan en esta capa

3. **Capa de red**
   - Se encarga del enrutamiento de paquetes entre distintas redes
   - Direccionamiento lógico (direcciones IP)
   - Determinación de rutas y reenvío de paquetes
   - Unidad de datos: paquete
   - IP (Protocolo de Internet) es el protocolo central de esta capa

4. **Capa de transporte**
   - Control de la comunicación de extremo a extremo
   - Segmentación y reensamblado de datos
   - TCP proporciona control de flujo y retransmisión; UDP no ofrece esas garantías
   - Unidad de datos: segmento TCP o datagrama UDP
   - TCP (Protocolo de Control de Transmisión) y UDP (Protocolo de Datagramas de Usuario) son los principales protocolos de esta capa

5. **Capa de sesión**
   - Establecimiento, mantenimiento y finalización de sesiones de comunicación
   - Sincronización y control del diálogo
   - Configuración de puntos de control y recuperación
   - La gestión de sesiones puede analizarse en esta capa; las implementaciones reales de RPC no necesariamente corresponden a una sola capa OSI

6. **Capa de presentación**
   - Conversión de formatos de datos y cifrado
   - Codificación de caracteres, compresión de datos y cifrado/descifrado
   - La codificación y la compresión ilustran esta función; TLS es un protocolo de Internet, no una implementación literal de la capa de presentación de OSI

7. **Capa de aplicación**
   - Proporciona servicios de red utilizados por las aplicaciones, que no necesariamente tienen una interfaz gráfica de usuario
   - Servicios como el correo electrónico, la transferencia de archivos y la navegación web
   - HTTP, FTP, SMTP y DNS son ejemplos de esta capa

### Relación entre Cilium y el modelo OSI

Cilium funciona en varias capas OSI:

| Capa OSI | Función de Cilium | Ejemplo |
|-----------|----------------|---------|
| L2 (Enlace de datos) | Alcance de enlace; anuncios L2 opcionales | Respuestas ARP/NDP para VIP de Service configuradas |
| L3 (Red) | Enrutamiento IP, políticas basadas en CIDR | Enrutamiento IP entre Pods |
| L4 (Transporte) | Filtrado por puerto, seguimiento de conexiones | Control de acceso a puertos de Service |
| L7 (Aplicación) | Reglas compatibles del proxy HTTP/gRPC y DNS | Política de rutas HTTP o política de consultas DNS |

Los anuncios L2 siguen en estado Beta en esta versión de referencia y requieren la configuración de su controlador y dispositivo. Son distintos de una interfaz general de políticas de seguridad basada en direcciones MAC.

### Pila TCP/IP

La pila TCP/IP es un conjunto de protocolos que constituye la base de Internet. Su arquitectura suele describirse con cuatro capas y compararse con OSI; no es una implementación directa del modelo de siete capas.

1. **Capa de interfaz de red**
   - Corresponde a las capas física y de enlace de datos del modelo OSI
   - Se encarga de la interfaz con los medios de red físicos
   - Incluye protocolos como Ethernet y Wi-Fi

2. **Capa de Internet**
   - Corresponde a la capa de red del modelo OSI
   - Enrutamiento de paquetes mediante IP (Protocolo de Internet)
   - Incluye ICMP (Protocolo de Mensajes de Control de Internet); ARP resuelve las direcciones de la capa de enlace del siguiente salto IPv4 en el límite del enlace, mientras que IPv6 usa Neighbor Discovery

3. **Capa de transporte**
   - Igual que la capa de transporte del modelo OSI
   - Incluye los protocolos TCP y UDP
   - Proporciona comunicación orientada a la conexión (TCP) y sin conexión (UDP)

4. **Capa de aplicación**
   - Integra las capas de sesión, presentación y aplicación del modelo OSI
   - Incluye protocolos como HTTP, SMTP, FTP y DNS
   - Proporciona una interfaz entre las aplicaciones de usuario y la red

### Funciones de Cilium por capa

Cilium ofrece funciones en distintas capas de red:

- **L2 (capa de enlace de datos)**: Alcance de enlace y anuncios opcionales de Service en L2; no es una API general de NetworkPolicy basada en direcciones MAC ni una protección universal contra la suplantación de ARP
- **L3 (capa de red)**: Enrutamiento y filtrado basados en direcciones IP, IPAM
- **L4 (capa de transporte)**: Filtrado por puerto, balanceo de carga y seguimiento de conexiones
- **L7 (capa de aplicación)**: Funciones configuradas del proxy HTTP/gRPC y políticas de DNS; la antigua API de políticas L7 para Kafka se eliminó

## Fundamentos de las redes de contenedores {#container-networking-basics}

Las redes de contenedores son un mecanismo que permite que las aplicaciones en contenedores se comuniquen entre sí y con el exterior. Las plataformas de orquestación de contenedores, como Kubernetes, usan diversos modelos y soluciones de redes.

### Container Network Interface (CNI)

CNI (Container Network Interface) define una interfaz estándar entre los entornos de ejecución de contenedores y los plugins de red. Kubernetes actualmente usa un entorno de ejecución de contenedores CRI para invocar plugins de CNI. Esta interfaz permite varias implementaciones de redes; la especificación de CNI no exige que todos los plugins implementen Kubernetes NetworkPolicy.

#### Componentes principales de CNI:

1. **Plugins**: Ejecutables que se encargan de crear y configurar interfaces de red
2. **Archivos de configuración**: Archivos con formato JSON que definen el comportamiento de los plugins
3. **IPAM (gestión de direcciones IP)**: Módulo que se encarga de asignar y administrar direcciones IP

#### Responsabilidades principales de los plugins de CNI:

- Agregar o quitar interfaces de los espacios de nombres de red de los contenedores
- Asignar y liberar direcciones IP
- Configurar tablas de enrutamiento
- Una implementación de redes puede proporcionar por separado controladores de políticas y aplicación en el datapath; las políticas no son una operación obligatoria de ejecución de CNI

### Modelos de redes de contenedores

Existen varios modelos de redes de contenedores, cada uno adecuado para distintos casos de uso y requisitos.

#### 1. Redes en modo puente

- Crea un puente virtual en el host para conectar contenedores
- Cada contenedor se conecta al puente mediante pares de Ethernet virtual (veth)
- Comunicación eficiente entre contenedores del mismo host
- El puente predeterminado es un ejemplo de Docker Linux independiente; no es el modelo de red de Kubernetes ni de Cilium

![Diagrama que muestra dos contenedores conectados, cada uno mediante un par veth, al puente Linux docker0 del host de Docker, que reenvía el tráfico a la red del host a través de eth0.](../../.gitbook/assets/en-networking-cilium-networking-concepts-1.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-cilium-networking-concepts-1.html)

Este es un ejemplo de un puente de Docker en Linux con direcciones ilustrativas. La ruta de enrutamiento/NAT del host está simplificada; no es la topología de puente predeterminada de Cilium.

#### 2. Redes del host

- El contenedor usa directamente el espacio de nombres de red del host
- No hay aislamiento de red independiente
- Evita un espacio de nombres de red separado para el contenedor; el rendimiento sigue dependiendo de la carga de trabajo y de la ruta reales
- Posibilidad de conflictos de puertos

![Diagrama que muestra dos contenedores dentro de un host que comparten directamente la pila de red del host (eth0, 192.168.1.10), sin un espacio de nombres de red ni una capa de aislamiento independientes entre ellos.](../../.gitbook/assets/en-networking-cilium-networking-concepts-2.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-cilium-networking-concepts-2.html)

Aquí, «sin aislamiento» significa que se comparte el espacio de nombres de red. No significa que se eliminen todos los límites de aislamiento entre procesos, sistemas de archivos u otros contenedores.

#### 3. Redes superpuestas

- Permiten la comunicación entre contenedores en varios hosts
- Usan protocolos de encapsulación como VXLAN y GENEVE
- Adecuadas para clústeres de gran escala
- Compatibles con Cilium, Calico, Flannel, etc.

![Diagrama que muestra dos hosts, cada uno ejecutando un contenedor en la red superpuesta 10.0.0.0/24; los paquetes se encapsulan en eth0 del Host A, se transportan por un túnel VXLAN a través de la red física y se desencapsulan en eth0 del Host B para entregarse al contenedor par.](../../.gitbook/assets/en-networking-cilium-networking-concepts-3.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-cilium-networking-concepts-3.html)

Esta ilustración genérica de VXLAN usa el puerto UDP estándar 4789 y una subred L2 compartida. El puerto VXLAN predeterminado de Cilium es 8472; las asignaciones de Pod CIDR deben ajustarse al modo IPAM elegido, no copiarse de este diagrama.

#### 4. Redes subyacentes (enrutamiento directo)

- Utilizan directamente la infraestructura de red física
- No tienen la sobrecarga de la encapsulación
- Requieren control sobre la infraestructura de red
- Pueden integrarse con protocolos de enrutamiento como BGP

![Diagrama que muestra dos hosts, cada uno enrutando el tráfico de los contenedores mediante una tabla de enrutamiento local directamente a la red física, sin encapsulación.](../../.gitbook/assets/en-networking-cilium-networking-concepts-4.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-cilium-networking-concepts-4.html)

Las entradas ilustran rutas del host. Una implementación real sigue necesitando siguientes saltos accesibles y rutas de ida y vuelta válidas para las direcciones de los Pods.

### Modelo de red de Kubernetes

El modelo de Kubernetes proporciona conectividad directa entre Pods **salvo que se aplique intencionadamente una segmentación de red**:

1. Los Pods pueden comunicarse con otros Pods sin que sea obligatorio usar un proxy o NAT en la red de Pods.
2. Los agentes de los nodos deben poder comunicarse con los Pods **de ese nodo**. No es un requisito general que todos los hosts puedan llegar a todos los Pods.
3. La conectividad externa depende de las políticas de seguridad y enrutamiento del clúster; no se requiere acceso irrestricto a Internet.

La aplicación de NetworkPolicy depende de que la implementación de red sea compatible. La API puede existir aunque el plugin instalado no la aplique.

#### Componentes de red de Kubernetes:

1. **Red de Pods**: Red que conecta todos los Pods del clúster
2. **Red de Service**: Proporciona puntos de conexión estables para conjuntos de Pods
3. **DNS del clúster**: Servicio DNS para el descubrimiento de servicios
4. **Ingress/Egress**: Gestiona la comunicación con el exterior del clúster

### Enfoque de Cilium para las redes de contenedores

Cilium aprovecha eBPF para proporcionar una solución de redes de contenedores escalable y de alto rendimiento:

1. **Datapath basado en eBPF**: Procesamiento directo de paquetes dentro del kernel
2. **Compatibilidad con varios modos de red**: Redes superpuestas (VXLAN, Geneve) y enrutamiento nativo; el valor predeterminado genérico de Helm es el modo de túnel con VXLAN, sujeto a las anulaciones de la plataforma
3. **Balanceo de carga avanzado**: Funcionalidad de reemplazo de kube-proxy
4. **Políticas de red**: Políticas detalladas de L3 a L7
5. **IPAM integrado**: Compatibilidad con distintas estrategias de asignación de direcciones IP

Una instalación genérica de Helm sin anulaciones de la plataforma usa cluster-pool IPAM de forma predeterminada: el operador asigna CIDR a los nodos y los agentes asignan direcciones IP a los Pods desde el pool de su nodo. `ipam.mode: kubernetes` usa `spec.podCIDR`/`spec.podCIDRs` del Node. El modo ENI usa interfaces EC2 y direcciones VPC; no es una recomendación universal para todos los modos de cómputo de EKS. Consulte [IPAM y políticas](04-ipam-policy.md).

## Redes superpuestas {#overlay-networks}

Las redes superpuestas son una tecnología que construye una capa de red virtual sobre una infraestructura de red existente. Esta tecnología permite crear topologías de red virtuales independientemente de la topología física. En entornos de contenedores, se usa ampliamente para permitir la comunicación entre contenedores en varios hosts.

### Funcionamiento de las redes superpuestas

Las redes superpuestas funcionan mediante la encapsulación. Los paquetes originales se encapsulan dentro de otros paquetes y se transmiten a través de la red física.

1. **Encapsulación de paquetes**: El paquete original (paquete interno) se envuelve con nuevos encabezados y, en ocasiones, nuevos tráileres.
2. **Túnel**: Los paquetes encapsulados se transmiten por la red física hasta el host de destino.
3. **Desencapsulación de paquetes**: En el host de destino, se elimina el encabezado externo y se extrae el paquete original.
4. **Reenvío de paquetes**: El paquete original se reenvía al contenedor de destino.

### Principales protocolos de redes superpuestas

#### VXLAN (LAN virtual extensible)

VXLAN es uno de los protocolos de red superpuesta más utilizados en las redes de contenedores.

- **Punto de terminación del túnel VXLAN (VTEP)**: Se encarga de encapsular y desencapsular paquetes
- **Identificador de red VXLAN (VNI)**: Campo de 24 bits con 16,777,216 valores posibles; no representa la capacidad admitida de Cilium para inquilinos o endpoints
- **Encapsulación UDP**: VXLAN estándar usa UDP 4789; el puerto de túnel VXLAN predeterminado de Cilium es UDP 8472
- **Encapsulación MAC en UDP**: Encapsula tramas L2 originales en paquetes UDP

Estructura de paquetes VXLAN:

![Diagrama de un paquete encapsulado con VXLAN, que muestra los encabezados Ethernet, IP y UDP externos envolviendo un encabezado VXLAN, que a su vez envuelve la trama Ethernet original, el encabezado IP, el encabezado TCP/UDP y la carga útil.](../../.gitbook/assets/en-networking-cilium-networking-concepts-5.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-cilium-networking-concepts-5.html)

Este es el formato genérico de los paquetes VXLAN en el cable. UDP 4789 y el VNI de 24 bits describen el estándar; Cilium usa UDP 8472 de forma predeterminada y utiliza metadatos de redes superpuestas para la identidad. El ancho de campo no garantiza la capacidad de un clúster.

#### GENEVE (encapsulación de virtualización de redes genérica)

GENEVE es un protocolo de red superpuesta más flexible, diseñado para superar las limitaciones de VXLAN.

- **Encabezados de opciones extensibles**: Admite distintos metadatos
- **Independiente del protocolo**: Puede usarse con distintas tecnologías de virtualización
- **Encapsulación UDP**: Se transmite a través del puerto UDP 6081
- **Túneles flexibles**: Admite diversos requisitos de virtualización de redes

#### IPsec

IPsec es un conjunto de protocolos que proporciona servicios de seguridad en el nivel de los paquetes IP.

- **Autenticación y cifrado**: IPsec proporciona mecanismos de integridad/autenticación y, con el modo adecuado, de confidencialidad
- **Modos de transporte y túnel**: Admite distintos escenarios de implementación
- **Asociación de seguridad (SA)**: Define parámetros de seguridad entre las partes que se comunican
- **Intercambio de claves de Internet (IKE)**: Mecanismo general de negociación de IPsec. En cambio, la configuración de IPsec de Cilium usa un Secret con una clave proporcionada por el administrador y el procedimiento de rotación documentado

### Ventajas y desventajas de las redes superpuestas

#### Ventajas:

- **Flexibilidad**: Permiten configurar redes virtuales independientemente de la topología de red física
- **Escalabilidad**: Admiten segmentos de red grandes y numerosos endpoints
- **Aislamiento**: Los segmentos lógicos pueden separar el tráfico si se configuran correctamente; la encapsulación por sí sola no equivale a autenticación, cifrado ni a un límite completo de políticas
- **Compatibilidad**: Pueden funcionar con la infraestructura de red existente

#### Desventajas:

- **Sobrecarga**: Aumento del tamaño de los paquetes y de la carga de procesamiento por la encapsulación
- **Consideraciones sobre MTU**: Reducción de la unidad máxima de transmisión (MTU) debido a la encapsulación
- **Complejidad**: La resolución de problemas y la depuración pueden ser más complejas
- **Latencia**: La encapsulación añade trabajo de procesamiento; mida el efecto real con la implementación y las descargas de procesamiento seleccionadas

### Redes superpuestas en Cilium

Cilium admite protocolos de redes superpuestas como VXLAN y Geneve, y aprovecha eBPF para procesar paquetes de forma eficiente.

- **Procesamiento VXLAN asistido por eBPF**: Los programas BPF no construyen por sí mismos el encabezado VXLAN; configuran metadatos del túnel (`bpf_skb_set_tunnel_key`) y redirigen al dispositivo `cilium_vxlan` (o `cilium_geneve`), basado en flujos, donde el controlador VXLAN/Geneve del kernel encapsula y desencapsula. Consulte [Enrutamiento superpuesto y nativo](09-overlay-native-routing.md)
- **Enrutamiento eficiente**: Reenvío de paquetes por rutas optimizadas
- **Opciones de cifrado**: Redes superpuestas cifradas mediante IPsec o WireGuard
- **Selección de modo**: Elija un modo de enrutamiento compatible. Habilitar rutas directas automáticas a los nodos junto con el modo de túnel se rechaza; no es un mecanismo de reserva

#### Ejemplo de configuración VXLAN de Cilium:

Valores de Helm para una **instalación de prueba IPv4 nueva y preparada**; elija CIDR de Pods que no se superpongan. Esto no es una migración de IPAM activa ni un ConfigMap de reemplazo.

```yaml
# vxlan-values.yaml
routingMode: tunnel
tunnelProtocol: vxlan
tunnelPort: 8472
autoDirectNodeRoutes: false
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
```

## Traducción de direcciones de red (NAT) {#network-address-translation-nat}

La traducción de direcciones de red (NAT) es el proceso de modificar las direcciones de origen o destino de los paquetes IP. NAT se usa principalmente para permitir que los dispositivos de redes privadas se comuniquen con la Internet pública, o para permitir la comunicación entre dos redes cuyos espacios de direcciones se superponen.

### Principales tipos de NAT

#### 1. NAT de origen (SNAT)

SNAT modifica la dirección IP de origen de los paquetes. Suele utilizarse cuando los dispositivos de redes privadas acceden a Internet.

- **Funcionamiento**: Reescribe una dirección de origen y, en ocasiones, su puerto; la traducción de privada a pública es un uso habitual
- **Casos de uso**: Acceso a Internet, conexiones salientes
- **Seguimiento**: Almacena el estado de la conexión en la tabla NAT

![Diagrama que muestra un cliente de una red interna (10.0.0.2:1234) que envía tráfico a través de un router NAT; SNAT reescribe la dirección de origen como la IP pública 198.51.100.1:5678 antes de que llegue a un servidor de Internet (203.0.113.5).](../../.gitbook/assets/en-networking-cilium-networking-concepts-6.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-cilium-networking-concepts-6.html)

Las direcciones reservadas para documentación ilustran un caso de SNAT de privada a pública. SNAT significa traducción de origen; la dirección de sustitución no siempre tiene que ser pública.

#### 2. NAT de destino (DNAT)

DNAT modifica la dirección IP de destino de los paquetes. Suele utilizarse para acceder a servicios de redes privadas desde la Internet pública.

- **Funcionamiento**: Reescribe una dirección o puerto de destino; el reenvío de pública a privada es un ejemplo
- **Casos de uso**: Reenvío de puertos, balanceo de carga, conexiones entrantes
- **Configuración**: Define asignaciones para puertos o rangos de puertos específicos

![Diagrama que muestra un cliente de Internet que envía tráfico a través de un router NAT; este reescribe la dirección de destino y el tráfico llega a un servidor de la red interna en su IP privada.](../../.gitbook/assets/en-networking-cilium-networking-concepts-7.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-cilium-networking-concepts-7.html)

Esto muestra un caso de DNAT de pública a privada con direcciones reservadas para documentación. DNAT significa traducción de destino y también aparece en otros ámbitos de direcciones.

#### 3. Traducción de direcciones y puertos (PAT)

PAT modifica tanto las direcciones IP como los números de puerto. Esto permite que varios hosts internos compartan una única dirección IP pública.

- **Funcionamiento**: Traduce las combinaciones IP:puerto de los hosts internos a distintos puertos de una única IP pública
- **Casos de uso**: Conservación de direcciones IP, compatibilidad con muchos hosts internos
- **Limitaciones**: Recursos finitos de puertos y estado; el número de flujos simultáneos también depende del protocolo, las tuplas de destino y la reutilización de asignaciones, no de un límite universal de 65,000 conexiones

![Diagrama que muestra dos hosts internos compartiendo una única IP pública (198.51.100.1) a través de un router PAT, que asigna a cada host un puerto público distinto (5000 y 5001) al acceder a un servidor de Internet.](../../.gitbook/assets/en-networking-cilium-networking-concepts-8.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-cilium-networking-concepts-8.html)

El ejemplo usa puertos traducidos distintos para el mismo servidor remoto. El espacio de unos 65,000 puertos no es un límite universal para todas las conexiones NAT; importan el protocolo, la tupla de destino, el comportamiento de las asignaciones y la capacidad de estado.

#### 4. NAT doble y NAT bidireccional

**NAT doble** cambia las direcciones de origen y destino a medida que el tráfico atraviesa ámbitos de direcciones, y puede ayudar a resolver la superposición de espacios de direcciones. Las asignaciones de direcciones, los supuestos de DNS/aplicación y la ruta de retorno deben diseñarse en conjunto.

En el RFC 2663, **NAT bidireccional** describe, en cambio, la posibilidad de iniciar sesiones desde cualquiera de los dos ámbitos. Por definición, no significa cambiar ambas direcciones de cada paquete.

### Ventajas y desventajas de NAT

#### Ventajas:

- **Conservación de direcciones IP**: Permite admitir muchos hosts internos con un número limitado de direcciones IP públicas
- **Ocultamiento de direcciones**: Puede ocultar las direcciones internas, pero NAT no sustituye las políticas de firewall ni la autenticación
- **Conciliación de ámbitos de direcciones**: Una traducción adecuada puede conectar ámbitos que se superponen; por sí sola, no proporciona aislamiento
- **Diseño de red flexible**: Permite cambiar de ISP sin reconfigurar la red interna

#### Desventajas:

- **Sobrecarga del seguimiento de conexiones**: Se necesitan recursos para mantener la tabla de estado
- **Problemas con ciertos protocolos**: Algunos protocolos pueden no ser compatibles con NAT
- **Pérdida de conectividad de extremo a extremo**: Dificultad para la comunicación directa entre pares
- **Resolución de problemas compleja**: La depuración de problemas relacionados con NAT puede ser compleja

### NAT en Kubernetes y Cilium

#### NAT en Kubernetes

Kubernetes usa NAT en distintos escenarios:

1. **Comunicación fuera del clúster**: Puede usarse SNAT en función del alcance de las direcciones, las exclusiones de masquerading y el datapath elegido
2. **Implementación de Service**: Las implementaciones basadas en paquetes pueden traducir el destino de un Service; el balanceo de carga a nivel de socket puede elegir un backend antes de que exista ese paquete
3. **Services NodePort**: La implementación reenvía una IP:puerto del nodo a los backends seleccionados; el comportamiento de la ruta de retorno depende de SNAT/DSR y de la política de tráfico
4. **Services LoadBalancer**: El comportamiento del proveedor/controlador varía y no tiene por qué consistir en un único paso DNAT desde una dirección pública hasta un Pod

#### NAT en Cilium

Cilium aprovecha eBPF para ofrecer una implementación eficiente de NAT:

1. **NAT basado en eBPF**: Realiza NAT directamente dentro del kernel
2. **Seguimiento de conexiones de alto rendimiento**: Seguimiento del estado de las conexiones mediante mapas BPF optimizados
3. **Controles NAT**: Las exclusiones de masquerading compatibles, el reenvío de Service y las funciones de Egress Gateway tienen configuraciones y requisitos previos distintos
4. **Masquerading**: Traducción de origen condicional en rutas/dispositivos configurados; los CIDR excluidos y los modos compatibles afectan al resultado

Egress Gateway es una función independiente que dirige el tráfico saliente que coincide con los criterios a través de nodos seleccionados y aplica SNAT con las direcciones de gateway configuradas. Cambia la IP de origen original; es necesario preparar las interfaces, direcciones y rutas de retorno. Los Pods nuevos pueden enviar tráfico antes de que converjan las políticas, por lo que no garantiza inmediatamente que la IP de origen quede protegida mediante una política de denegación predeterminada.

#### Ejemplo de configuración NAT de Cilium:

Este fragmento de Helm presupone un entorno preparado de reemplazo de kube-proxy/masquerading BPF con un endpoint de API accesible. Revise primero los dispositivos conectados y las rutas reales. Excluir un CIDR de SNAT no crea una ruta de retorno; el tamaño NAT es un ejemplo, no una capacidad universal recomendada.

```yaml
# masquerade-values.yaml
enableIPv4Masquerade: true
kubeProxyReplacement: true
bpf:
  masquerade: true
  natMax: 262144
ipMasqAgent:
  enabled: true
  config:
    nonMasqueradeCIDRs:
    - 10.0.0.0/8
    - 172.16.0.0/12
    - 192.168.0.0/16
    masqLinkLocal: false
```

## Protocolos de enrutamiento {#routing-protocols}

Los protocolos de enrutamiento definen las reglas y los procedimientos que determinan la ruta óptima para que los paquetes viajen desde el origen hasta el destino en una red. Estos protocolos desempeñan un papel importante para adaptarse a los cambios de topología de la red, reenviar el tráfico con eficiencia y sortear fallos de red.

### Clasificación de los protocolos de enrutamiento

#### 1. Protocolos de gateway interior (IGP)

Los protocolos de gateway interior se utilizan para intercambiar información de enrutamiento dentro de un único sistema autónomo (AS).

##### Protocolos de vector de distancia

- **RIP (Protocolo de información de enrutamiento)**
  - Usa el número de saltos como métrica
  - Las métricas válidas llegan hasta 15 saltos; la métrica 16 indica que el destino es inalcanzable
  - Implementación sencilla, adecuada para redes pequeñas
  - Las actualizaciones periódicas se envían aproximadamente cada 30 segundos, con aleatorización de temporizadores y actualizaciones activadas por cambios

- **EIGRP (Protocolo de enrutamiento de gateway interior mejorado)**
  - Métrica compuesta configurable; los coeficientes predeterminados usan el caudal/ancho de banda y el retardo, no la carga ni la fiabilidad
  - Envía solo actualizaciones parciales
  - Convergencia rápida
  - Protocolo originado por Cisco y documentado en el RFC informativo 7868; esa publicación no le otorga la categoría de estándar del IETF

##### Protocolos de estado de enlace

- **OSPF (Primero la ruta más corta)**
  - Calcula la ruta más corta mediante el algoritmo de Dijkstra
  - Jerarquía basada en áreas
  - Convergencia rápida
  - Admite redes de gran escala
  - Intercambia información de topología mediante anuncios de estado de enlace (LSA)

- **IS-IS (Sistema intermedio a sistema intermedio)**
  - Protocolo de estado de enlace similar a OSPF
  - Ampliamente utilizado en grandes redes de proveedores de servicios
  - Admite varias capas de red
  - Actualizaciones de enrutamiento eficientes

#### 2. Protocolos de gateway exterior (EGP)

Los protocolos de gateway exterior se utilizan para intercambiar información de enrutamiento entre distintos sistemas autónomos.

- **BGP (Protocolo de gateway fronterizo)**
  - Protocolo central de enrutamiento de Internet
  - Protocolo de vector de ruta
  - Decisiones de enrutamiento basadas en políticas
  - Sesiones fiables sobre TCP
  - Selección de rutas mediante atributos de ruta (ruta de AS, preferencia local, etc.)
  - Variantes iBGP (BGP interno) y eBGP (BGP externo)

### Protocolos de enrutamiento en redes de contenedores

En los entornos de contenedores, se usan protocolos de enrutamiento tradicionales junto con mecanismos de enrutamiento específicos de contenedores.

#### 1. Redes de contenedores con BGP

BGP está ganando popularidad en las redes de contenedores por los siguientes motivos:

- **Anuncio de alcance**: Anuncia prefijos de Pods o Services a los routers; la implementación local del reenvío sigue determinando cómo circula el tráfico
- **Escalabilidad**: Admite clústeres de gran escala y entornos multiclúster
- **Integración con redes existentes**: Integración con la infraestructura de red del centro de datos
- **Disponibilidad**: La conectividad multipath y la convergencia dependen de las políticas del router, los temporizadores y un datapath operativo; una sesión por sí sola no garantiza una conmutación por error rápida

#### 2. Mecanismos de enrutamiento de redes de contenedores

- **Enrutamiento basado en el host**: Los hosts mantienen rutas a los Pods y pueden participar en un mecanismo de anuncio de rutas configurado por separado
- **Enrutamiento centralizado**: Un controlador gestiona las decisiones de enrutamiento de forma centralizada
- **Enrutamiento distribuido**: Intercambio directo de información de enrutamiento entre nodos
- **Enrutamiento basado en políticas**: Decisiones de enrutamiento basadas en las características del tráfico

### Enrutamiento en Cilium

Cilium implementa el enrutamiento con eBPF y admite distintos modos de datapath. **El enrutamiento del host es un eje independiente**: el enrutamiento BPF del host optimiza el reenvío dentro del nodo y puede omitir partes de la pila del host o de netfilter. Requiere un reemplazo de kube-proxy/masquerading BPF compatible y tiene limitaciones de integración. No significa elegir enrutamiento nativo en lugar de enrutamiento por túnel entre nodos.

#### 1. Enrutamiento nativo (enrutamiento directo)

En el modo de enrutamiento nativo, Cilium enruta las IP de los Pods directamente, sin encapsulación de redes superpuestas.

- **Funcionamiento**: El tráfico de los Pods usa rutas subyacentes sin encapsulación de redes superpuestas; habilitar el modo nativo no habilita BGP automáticamente
- **Ventajas**: Evita la sobrecarga de la encapsulación de redes superpuestas; el rendimiento real requiere mediciones
- **Requisitos**: Rutas válidas para las direcciones de los Pods pertinentes y su tráfico de retorno, no solo conectividad entre las IP de los nodos
- **Casos de uso**: Cargas de trabajo críticas para el rendimiento, clústeres de una sola subred

El enrutamiento nativo necesita rutas válidas a los Pods, pero elegir `routingMode: native` no las anuncia automáticamente mediante BGP. Proporcione las rutas subyacentes y de retorno o configure el mecanismo adecuado de distribución de rutas. La ilustración anterior de rutas del host muestra el principio de reenvío.

#### 2. Enrutamiento BGP

Cilium admite el enrutamiento BGP para integrar las IP de los Pods con la infraestructura de red física.

- **Funcionamiento**: Cilium anuncia los CIDR de Pods mediante sesiones BGP
- **Ventajas**: Integración con la infraestructura de red existente, alta disponibilidad
- **Componentes**: Sesiones BGP, filtrado de rutas y atributos de comunidad
- **Casos de uso**: Integración con redes de centros de datos, entornos multiclúster

#### 3. Enrutamiento por redes superpuestas

Cilium puede enrutar el tráfico de los Pods entre nodos mediante protocolos de redes superpuestas como VXLAN o Geneve.

- **Funcionamiento**: Encapsula los paquetes de los Pods para transmitirlos entre nodos
- **Ventajas**: Reduce al mínimo los requisitos de infraestructura de red, implementación flexible
- **Casos de uso**: Entornos de nube, topologías de red complejas

#### 4. Enrutamiento híbrido

No dé por sentado que Cilium usa automáticamente rutas nativas cuando están disponibles y, de lo contrario, recurre a una red superpuesta. El modo de túnel actual no puede combinarse con `autoDirectNodeRoutes: true`; el agente rechaza esa configuración. Elija un datapath compatible y prepare las rutas subyacentes.

El modo de balanceador de carga válido denominado `hybrid` es otra función distinta: TCP usa DSR y UDP usa SNAT. No es un mecanismo de reserva entre enrutamiento superpuesto y nativo.

### Ejemplos de configuración de enrutamiento de Cilium

#### Configuración de enrutamiento nativo:

Este fragmento de enrutamiento nativo presupone que el CIDR de Pods previsto y los nodos están en una red L2 compartida para usar rutas directas automáticas. Otras topologías necesitan un mecanismo de enrutamiento adecuado. No debe combinarse con el modo de túnel como mecanismo de reserva automático.

```yaml
# native-values.yaml
routingMode: native
autoDirectNodeRoutes: true
ipv4NativeRoutingCIDR: 10.244.0.0/16
```

#### Configuración de enrutamiento BGP:

La marca de función que aparece a continuación es solo un requisito previo. Configure los recursos actuales `CiliumBGPClusterConfig`, `CiliumBGPPeerConfig` y `CiliumBGPAdvertisement`, así como el router externo, tal como se describe en [Temas avanzados](07-advanced-topics.md). El anuncio BGP y el modo de enrutamiento del datapath son decisiones independientes.

```yaml
# bgp-values.yaml
bgpControlPlane:
  enabled: true
```

#### Configuración del enrutamiento por redes superpuestas:

Use el ejemplo completo de valores VXLAN anterior. Verifique el modo y el puerto activos en el estado del agente; no sobrescriba la configuración de instalación con un ConfigMap pequeño.

## DNS y descubrimiento de servicios {#dns-and-service-discovery}

DNS (Sistema de nombres de dominio) y el descubrimiento de servicios desempeñan un papel fundamental en las aplicaciones de red modernas, sobre todo en los entornos dinámicos de contenedores. Estos mecanismos abstraen la ubicación de los servicios y permiten que las aplicaciones se adapten a los cambios en la topología de red.

### DNS (Sistema de nombres de dominio)

DNS es un sistema distribuido que traduce nombres de dominio legibles por humanos a direcciones IP.

#### Funcionamiento de DNS

1. **Espacio de nombres jerárquico**: Los nombres de dominio se organizan en una estructura jerárquica separada por puntos (por ejemplo, www.example.com)
2. **Base de datos distribuida**: Red de servidores DNS distribuidos por todo el mundo
3. **Consultas iterativas y recursivas**: Dos métodos principales para procesar las solicitudes de los clientes
4. **Almacenamiento en caché**: Almacenamiento temporal de resultados para mejorar el rendimiento

#### Tipos de registros DNS

- **Registro A**: Asocia un nombre de dominio con una dirección IPv4
- **Registro AAAA**: Asocia un nombre de dominio con una dirección IPv6
- **Registro CNAME**: Alias (nombre canónico) de un nombre de dominio
- **Registro MX**: Especifica el servidor de correo
- **Registro SRV**: Especifica el servidor que proporciona un servicio concreto
- **Registro TXT**: Almacena información de texto (se usa principalmente para verificaciones y políticas)
- **Registro PTR**: Asocia una dirección IP con un nombre de dominio (DNS inverso)

#### Proceso de resolución DNS

Una consulta habitual sin caché separa el resolvedor stub de la aplicación del resolvedor recursivo:

| Paso | Consulta/respuesta |
| --- | --- |
| 1 | El stub pregunta por `www.example.com` al resolvedor recursivo configurado. |
| 2 | El resolvedor pregunta a un servidor raíz y recibe una referencia a los servidores de `.com`. |
| 3 | El resolvedor pregunta a un servidor de `.com` y recibe una referencia a los servidores autoritativos de `example.com`. |
| 4 | El resolvedor pregunta al servidor autoritativo y obtiene la respuesta pertinente. |
| 5 | El resolvedor almacena la respuesta en caché según el TTL y se la devuelve al stub. |

Normalmente, los servidores autoritativos no se reenvían entre sí esta secuencia. Las cachés, los alias y los reenviadores configurados pueden modificar el intercambio exacto.

### Descubrimiento de servicios en entornos de contenedores

El descubrimiento de servicios es el proceso de detectar automáticamente los servicios disponibles y localizar su ubicación en una red. En los entornos de contenedores, es especialmente importante para gestionar de forma eficaz los servicios que se crean y eliminan dinámicamente.

#### Enfoques para el descubrimiento de servicios

1. **Descubrimiento de servicios basado en DNS**
   - Crea registros DNS cuando se registran los servicios
   - Los clientes descubren servicios mediante consultas DNS estándar
   - Sencillo y ampliamente compatible
   - Ejemplos: DNS de Kubernetes, CoreDNS

2. **Descubrimiento de servicios basado en almacenes clave-valor**
   - Almacena información de servicios en almacenes clave-valor centralizados
   - Los clientes consultan el almacén para descubrir servicios
   - Compatibilidad con metadatos enriquecidos
   - Ejemplos: etcd, Consul, ZooKeeper

3. **Descubrimiento de servicios basado en API**
   - Proporciona información de servicios mediante API específicas
   - Los clientes llaman a las API para descubrir servicios
   - Admite consultas y filtros complejos
   - Ejemplo: servidor de API de Kubernetes

4. **Descubrimiento de servicios basado en service mesh**
   - La infraestructura de service mesh gestiona el descubrimiento de servicios
   - Admite balanceo de carga del lado del cliente y enrutamiento
   - Funciones avanzadas de gestión del tráfico
   - Ejemplos: Istio, Linkerd

### DNS y descubrimiento de servicios en Kubernetes

Kubernetes proporciona mecanismos integrados para descubrir servicios dentro del clúster.

#### Services de Kubernetes

Los Services de Kubernetes proporcionan puntos de conexión estables para conjuntos de Pods:

- **ClusterIP**: IP virtual de un Service, que normalmente se usa dentro del clúster; cualquier posibilidad de enrutamiento externo requiere un diseño de red explícito y no constituye un límite de seguridad inherente
- **NodePort**: Puerto de un nodo expuesto en las direcciones de nodo que correspondan, sujeto a la política de tráfico, el enrutamiento y las reglas de firewall
- **LoadBalancer**: Solicita una implementación del proveedor/controlador, que puede ser pública o interna
- **ExternalName**: Alias DNS de un servicio externo

#### DNS de Kubernetes

Kubernetes ejecuta un servicio DNS del clúster (normalmente CoreDNS) para permitir el descubrimiento de servicios:

- **DNS de Service**: `<service-name>.<namespace>.svc.<cluster-domain>`; `cluster.local` es un dominio configurado habitual, no una constante universal
- **DNS de Pod**: El antiguo formato basado en direcciones `pod.<cluster-domain>` depende de la implementación y es heredado. Los nombres de Pod estables suelen usar un nombre de host/subdominio con un Service headless correspondiente
- **Services headless**: DNS puede devolver direcciones de endpoints en vez de una VIP; el estado de disponibilidad y `publishNotReadyAddresses` afectan a los registros publicados

Las consultas DNS y el reenvío de Services son procesos independientes:

| Fase | Responsabilidad |
| --- | --- |
| Consulta DNS | CoreDNS resuelve un nombre de Service convencional a su ClusterIP usando el estado de los objetos de Kubernetes. No elige el backend de la aplicación para esa conexión. |
| Conexión | El cliente envía tráfico a la dirección de Service devuelta. |
| Reenvío | La implementación del Service, como el datapath de Cilium, elige un backend que corresponda usando el estado derivado de Service/EndpointSlice. |
| Service headless | DNS devuelve direcciones de endpoints en lugar de una VIP de Service; el comportamiento del cliente determina qué dirección se utiliza. |

Las actualizaciones de los observadores de objetos y del datapath son asíncronas; una respuesta DNS no es una comprobación del estado del backend.

#### Mecanismos de descubrimiento de servicios de Kubernetes

1. **Variables de entorno**: Los enlaces de Service pueden reflejar los Services presentes al crear el Pod; no son un canal de descubrimiento en tiempo real y pueden deshabilitarse
2. **DNS**: Resolución de nombres de Service mediante el DNS del clúster
3. **Servidor de API**: Recuperación de información de Services mediante consultas directas a la API de Kubernetes
4. **Objetos EndpointSlice**: Proporcionan información de direcciones, puertos y disponibilidad de los backends para las implementaciones de Services

### DNS y descubrimiento de servicios en Cilium

Cilium se integra con los mecanismos de descubrimiento de servicios de Kubernetes y proporciona funciones adicionales.

#### Políticas de Cilium basadas en DNS

Cilium puede definir políticas de red basadas en nombres DNS:

- **Filtrado basado en nombres DNS**: Control de acceso para nombres de dominio específicos
- **Compatibilidad con comodines**: `*.example.com` coincide con un nivel de subdominio; `**.example.com` admite varios niveles en esta versión, y ninguno de los dos incluye el dominio raíz sin una coincidencia explícita
- **Políticas FQDN**: Políticas basadas en nombres de dominio completos (FQDN)

Este ejemplo de política únicamente requiere que existan el namespace, la carga de trabajo etiquetada y la ruta del resolvedor verificada. La observación de DNS y las autorizaciones para destinos TCP 443 son independientes. El `*` de DNS permite todos los nombres de consulta; toFQDNs no es un mecanismo de autenticación de nombres de host.

```yaml
# dns-policy.yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: dns-policy
  namespace: cilium-fqdn-demo
spec:
  endpointSelector:
    matchLabels:
      app: myapp
  egress:
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
        k8s:k8s-app: kube-dns
    toPorts:
    - ports:
      - port: '53'
        protocol: UDP
      - port: '53'
        protocol: TCP
      rules:
        dns:
        - matchPattern: '*'
  - toFQDNs:
    - matchName: api.example.com
    - matchPattern: '*.api.example.com'
    toPorts:
    - ports:
      - port: '443'
        protocol: TCP
```

#### Mejoras de Cilium para el descubrimiento de servicios

Cilium proporciona varias funciones que mejoran el descubrimiento de servicios de Kubernetes:

1. **Implementación de Service basada en eBPF**:
   - Reemplazo de kube-proxy
   - Balanceo de carga directo de Service dentro del kernel
   - Mejor rendimiento y más funciones

2. **Global Services**:
   - Descubrimiento de servicios entre varios clústeres
   - Balanceo de carga entre clústeres
   - Coincidencia de nombres/namespaces de Service y configuración explícita de uso compartido/ClusterMesh

3. **Afinidad de Service**:
   - Compatibilidad con afinidad de sesión
   - La afinidad ClientIP es independiente del algoritmo de balanceo de carga; las rutas a nivel de socket pueden usar una cookie del espacio de nombres de red
   - Compatibilidad con conexiones con estado

4. **Integración con comprobaciones de estado**:
   - El estado de los backends sigue la información de disponibilidad de Kubernetes/EndpointSlice y las comprobaciones configuradas del proxy
   - Los cambios se propagan de forma asíncrona
   - No dé por sentado que todos los Services de Cilium realizan comprobaciones activas de la aplicación o una conmutación por error instantánea

#### Ejemplo de configuración de Service de Cilium:

La afinidad de sesión se configura en el Service; Global Services usa una anotación y un ClusterMesh operativo. Los Services pares deben tener el mismo nombre y namespace. Este ejemplo no crea la aplicación, ClusterMesh ni un balanceador de carga externo.

```yaml
# global-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: api
  namespace: cilium-service-demo
  annotations:
    service.cilium.io/global: 'true'
spec:
  type: ClusterIP
  selector:
    app: api
  ports:
  - name: http
    port: 80
    targetPort: 8080
  sessionAffinity: ClientIP
  sessionAffinityConfig:
    clientIP:
      timeoutSeconds: 10800
```

## Conceptos de balanceo de carga {#load-balancing-concepts}

El balanceo de carga es una tecnología que distribuye el tráfico de red entre varios servidores o servicios de backend para optimizar el uso de los recursos y respaldar los objetivos de rendimiento, latencia y disponibilidad cuando se combina con una capacidad adecuada y la gestión del estado de los backends. En los entornos de contenedores, es especialmente importante distribuir de forma eficaz el tráfico entre instancias de backend que cambian dinámicamente.

### Tipos de balanceo de carga

#### 1. Balanceo de carga L4 (capa de transporte)

El balanceo de carga L4 distribuye el tráfico según información de la capa de transporte, como las direcciones IP y los números de puerto.

- **Funcionamiento**: Decisiones de enrutamiento basadas en la información de los encabezados TCP/UDP
- **Ventajas**: Procesamiento rápido, baja sobrecarga, puede gestionar tráfico cifrado
- **Desventajas**: No puede realizar enrutamiento avanzado basado en información de la capa de aplicación
- **Casos de uso**: Services basados en TCP/UDP, requisitos de alto rendimiento

![Diagrama que muestra una solicitud de un cliente dirigida por un balanceador de carga de la capa de transporte a uno de dos servidores de backend, basándose únicamente en la información de los encabezados TCP/UDP.](../../.gitbook/assets/en-networking-cilium-networking-concepts-12.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-cilium-networking-concepts-12.html)

Las ramas representan posibles opciones de backend, no la difusión de una conexión a ambos servidores. El reenvío L4 puede transportar TLS sin inspeccionar la carga útil HTTP cifrada.

#### 2. Balanceo de carga L7 (capa de aplicación)

El balanceo de carga L7 distribuye el tráfico según información de la capa de aplicación, como encabezados HTTP, URL y cookies.

- **Funcionamiento**: Decisiones de enrutamiento mediante la inspección del contenido de solicitudes HTTP/HTTPS
- **Ventajas**: Enrutamiento basado en el contenido, gestión avanzada del tráfico y funciones de seguridad
- **Desventajas**: Coste de procesamiento del proxy; para inspeccionar contenido HTTP sobre HTTPS se necesita la terminación adecuada de TLS
- **Casos de uso**: Aplicaciones web, microservicios, gateways de API

![Diagrama que muestra una solicitud HTTP de un cliente dirigida por un balanceador de carga de la capa de aplicación a uno de dos servicios de backend, según la ruta URL y la inspección de encabezados.](../../.gitbook/assets/en-networking-cilium-networking-concepts-13.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-cilium-networking-concepts-13.html)

La ruta seleccionada depende de los atributos de la solicitud. El enrutamiento por contenido HTTP sobre HTTPS requiere una ruta adecuada de terminación/inspección de TLS.

### Algoritmos de balanceo de carga

Los algoritmos de balanceo de carga determinan cómo se distribuye el tráfico entre los servidores de backend.

#### 1. Round Robin

- **Funcionamiento**: Distribuye las solicitudes secuencialmente entre los servidores de backend
- **Ventajas**: Secuencia sencilla; que todos reciban el mismo número de solicitudes no significa que la carga de trabajo sea igual
- **Desventajas**: No tiene en cuenta las diferencias de capacidad ni la carga actual de los servidores
- **Variantes**: Round Robin ponderado (aplica ponderaciones según la capacidad del servidor)

#### 2. Menos conexiones

- **Funcionamiento**: Reenvía las solicitudes nuevas al servidor con menos conexiones activas
- **Ventajas**: Tiene en cuenta la carga del servidor; es eficaz para conexiones largas
- **Desventajas**: El número de conexiones no siempre refleja con precisión la carga
- **Variantes**: Menos conexiones ponderado (aplica ponderaciones según la capacidad del servidor)

#### 3. Hash de IP

- **Funcionamiento**: Calcula un hash de la dirección IP del cliente para seleccionar de forma coherente un servidor de backend
- **Ventajas**: Puede ofrecer una selección estable mientras se mantengan las entradas y los backends; no es almacenamiento de sesiones permanente
- **Desventajas**: Posible distribución desigual y sobrecarga potencial de servidores específicos
- **Variantes**: Hash de IP de origen y destino (tiene en cuenta ambas direcciones IP)

#### 4. Menor tiempo de respuesta

- **Funcionamiento**: Reenvía las solicitudes al servidor con el tiempo de respuesta más corto
- **Ventajas**: Tiene en cuenta el rendimiento y la disponibilidad; es adecuado para aplicaciones sensibles a la latencia
- **Desventajas**: Sobrecarga de medición del tiempo de respuesta y sensibilidad a las variaciones de red
- **Variantes**: Tiempo de respuesta ponderado (tiene en cuenta la capacidad del servidor y el tiempo de respuesta)

#### 5. Selección aleatoria

- **Funcionamiento**: Selecciona aleatoriamente un servidor de backend
- **Ventajas**: Implementación sencilla, no requiere seguimiento de estado especial
- **Desventajas**: Posible distribución desigual
- **Variantes**: Selección aleatoria ponderada (ajusta la probabilidad según la capacidad del servidor)

### Modelos de implementación de balanceadores de carga

#### 1. Balanceadores de carga de hardware

- **Características**: Equipo físico dedicado
- **Ventajas**: Alto rendimiento, fiabilidad y aceleración de hardware dedicada
- **Desventajas**: Coste, escalabilidad limitada y poca flexibilidad
- **Ejemplos**: Dispositivos controladores de entrega de aplicaciones; algunas familias de productos también ofrecen ediciones virtuales o de software

#### 2. Balanceadores de carga de software

- **Características**: Software ejecutado en servidores de propósito general
- **Ventajas**: Flexibilidad, eficiencia de costes y capacidad de programación
- **Desventajas**: La capacidad depende de la implementación, el hardware y la carga de trabajo; el software no es intrínsecamente más lento que todos los dispositivos especializados
- **Ejemplos**: NGINX, HAProxy, Envoy

#### 3. Balanceadores de carga en la nube

- **Características**: Servicios gestionados por proveedores de nube
- **Ventajas**: Menor carga de gestión, escalado automático y alta disponibilidad
- **Desventajas**: Dependencia del proveedor y personalización limitada
- **Ejemplos**: AWS ELB/ALB/NLB, Google Cloud Load Balancing, Azure Load Balancer

#### 4. Balanceadores de carga nativos para contenedores

- **Características**: Balanceo de carga optimizado para entornos de contenedores
- **Ventajas**: Integración con la orquestación de contenedores y descubrimiento dinámico de servicios
- **Desventajas**: Especializados para entornos de contenedores
- **Ejemplos**: Kubernetes Services, Istio, Cilium

### Balanceo de carga en Kubernetes

Kubernetes ofrece balanceo de carga en varios niveles:

#### 1. Balanceo de carga de Service

- **ClusterIP**: Balanceo de carga interno del clúster
- **NodePort**: Acceso externo mediante puertos de nodo
- **LoadBalancer**: Aprovisionamiento de un balanceador de carga externo
- **ExternalName**: Alias DNS de servicios externos

#### 2. Controladores de Ingress

- Balanceo de carga y enrutamiento L7
- Enrutamiento basado en URL y terminación de TLS; las capacidades de autenticación dependen del controlador y de la configuración
- Entre las implementaciones se incluyen controladores basados en Traefik, HAProxy e Istio. `ingress-nginx` de la comunidad se retiró en marzo de 2026; los artefactos que quedan no son una recomendación de instalación mantenida

#### 3. Service mesh

- Gestión avanzada del tráfico entre microservicios
- Enrutamiento detallado, división del tráfico e inyección de fallos
- Ejemplos: Istio, Linkerd y Consul service mesh; sus conjuntos de funciones de gestión del tráfico y seguridad son distintos

### Balanceo de carga en Cilium

Cilium implementa un balanceo de carga eficiente mediante eBPF:

#### 1. Balanceo de carga basado en eBPF

- **Reemplazo de kube-proxy**: Balanceo de carga directo de Service dentro del kernel
- **Rendimiento**: Las rutas BPF compatibles pueden evitar partes de la pila convencional; cuantifique el resultado para la carga de trabajo real
- **Escalabilidad**: Admite Services y endpoints de gran escala
- **Optimización del seguimiento de conexiones**: Gestión eficiente del estado

![Diagrama del balanceo de carga basado en eBPF de Cilium: un paquete que Pod A envía a una IP de Service pasa por una canalización eBPF de cuatro pasos dentro del kernel (intercepción del paquete, búsqueda en el mapa de Service, selección del backend y reenvío del paquete) y se entrega directamente a Pod B sin kube-proxy.](../../.gitbook/assets/en-networking-cilium-networking-concepts-14.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-cilium-networking-concepts-14.html)

Esto representa la traducción de Service en la ruta de un paquete. El balanceo de carga a nivel de socket puede seleccionar un backend antes de que exista un paquete destinado a la IP de Service. Las mejoras de latencia deben medirse para la ruta real.

#### 2. Algoritmos de balanceo de carga

Los algoritmos de Service BPF son **aleatorio** (el predeterminado) y **Maglev**. Maglev calcula un hash de la información del flujo; no es simplemente afinidad por IP de origen. La selección habitual a nivel de socket para tráfico este-oeste es una ruta distinta de las rutas de paquetes externos en las que se aplica Maglev.

La afinidad de sesión `ClientIP` se configura por separado en un Service. Su tiempo de espera no es un «tiempo de espera de Maglev»; Maglev no tiene un temporizador que reequilibre las sesiones periódicamente. Los cambios en la pertenencia, la semilla o la tabla pueden reasignar selecciones, y un backend eliminado no puede seguir atendiendo una conexión simplemente porque el hash sea coherente.

#### 3. Balanceo de carga L7

Cilium también admite el balanceo de carga L7 (capa de aplicación):

- **Enrutamiento basado en encabezados HTTP**: Enrutamiento según valores específicos de los encabezados
- **Enrutamiento basado en la ruta URL**: Distribución del tráfico según patrones de URL
- **Enrutamiento gRPC**: Enrutamiento según los métodos y metadatos gRPC
- **Kafka**: La versión actual de Cilium no ofrece la antigua función de políticas/enrutamiento L7 por temas de Kafka; utilice controles adecuados para el broker

#### 4. Balanceo de carga de Global Services

Cilium admite balanceo de carga entre varios clústeres:

- **Balanceo de carga entre clústeres**: Distribución del tráfico entre backends de varios clústeres
- **Preferencia de localidad**: La afinidad local/remota configurada no mide automáticamente la latencia de red
- **Gestión de fallos**: Depende del estado de los endpoints y del comportamiento de la caché remota; el TTL de caché predeterminado, igual a cero, puede conservar estados remotos obsoletos, por lo que debe probarse la conmutación por error de la aplicación

#### Ejemplo de configuración de balanceo de carga de Cilium:

Estos son valores de Helm para una instalación preparada. La semilla hash mostrada es un **valor de demostración válido de 12 bytes codificados en base64**. Para una implementación, genere y conserve una semilla aleatoria común para los nodos participantes, y considere cualquier cambio de semilla/tabla una operación que puede afectar a las conexiones. Consulte el [perfil de balanceo de carga preparado](05-l2-l7-networking.md).

```yaml
# load-balancing-values.yaml
kubeProxyReplacement: true
loadBalancer:
  algorithm: maglev
maglev:
  tableSize: 16381
  hashSeed: AAECAwQFBgcICQoL
```

## Fundamentos de seguridad de red {#network-security-basics}

La seguridad de red consiste en proteger la infraestructura de red, las aplicaciones y los datos frente al acceso no autorizado, el uso indebido, los fallos o las modificaciones. En los entornos de contenedores, la seguridad de red es aún más importante debido a su naturaleza dinámica y distribuida.

### Conceptos fundamentales de seguridad de red

#### 1. Defensa en profundidad

La defensa en profundidad combina controles para reducir el impacto de un fallo individual. Las dependencias compartidas o una configuración errónea común aún pueden afectar a varias capas.

- **Varias capas de seguridad**: Protección en los niveles de red, host, aplicación y datos
- **Controles redundantes**: Combinación de distintos mecanismos de seguridad
- **Aislamiento de fallos**: Diseñar y probar los límites; la independencia de los fallos no es automática
- **Detección y respuesta ante amenazas**: Supervisión y respuesta en cada capa

#### 2. Principio de privilegio mínimo

El principio de privilegio mínimo es una práctica de seguridad que concede a los usuarios, procesos o aplicaciones solo los privilegios mínimos necesarios para realizar sus tareas.

- **Control de acceso detallado**: Restringe el acceso únicamente a los recursos necesarios
- **Separación de privilegios**: Separa los privilegios para distintas funciones
- **Denegación predeterminada**: Deniega todo acceso que no se permita explícitamente
- **Revisión periódica**: Auditoría y ajuste periódicos de los privilegios

#### 3. Segmentación de red

La segmentación de red es una técnica que divide una red en segmentos o zonas más pequeños para mejorar la seguridad y limitar el movimiento lateral de las amenazas.

- **Zonas de seguridad**: Agrupan sistemas con requisitos de seguridad similares
- **Microsegmentación**: Control detallado en el nivel de la carga de trabajo
- **Protección perimetral**: Control y supervisión del tráfico entre zonas
- **Aislamiento de amenazas**: Limita el alcance del impacto de una brecha

#### 4. Cifrado

El cifrado es el proceso de transformar datos para que las partes no autorizadas no puedan leerlos.

- **Cifrado en tránsito**: Protege los datos que circulan por la red (por ejemplo, con TLS compatible)
- **Cifrado en reposo**: Protege los datos almacenados en discos o bases de datos
- **Cifrado de extremo a extremo**: Protege los datos a lo largo de toda la ruta de comunicación
- **Gestión de claves**: Generación, almacenamiento y rotación seguros de las claves de cifrado

### Amenazas para la seguridad de las redes de contenedores

Los entornos de contenedores presentan desafíos de seguridad particulares:

#### 1. Ataques basados en la red

- **Ataques DDoS (denegación de servicio distribuida)**: Grandes volúmenes de tráfico para interrumpir la disponibilidad del servicio
- **Escaneo de puertos**: Exploración de puertos abiertos y vulnerabilidades
- **Suplantación de ARP**: Manipulación del protocolo de resolución de direcciones para interceptar el tráfico de red
- **Envenenamiento de DNS**: Redirección de consultas DNS a destinos maliciosos

#### 2. Ataques a la capa de aplicación

- **Inyección SQL**: Inserción de código SQL malicioso
- **XSS (secuencias de comandos en sitios cruzados)**: Inserción de scripts del lado del cliente
- **CSRF (falsificación de solicitudes entre sitios)**: Realización de acciones maliciosas mediante usuarios autenticados
- **Inyección de comandos**: Uso de entradas maliciosas para ejecutar comandos del sistema

#### 3. Amenazas específicas de los contenedores

- **Vulnerabilidades de imágenes**: Imágenes de contenedores con componentes vulnerables
- **Escalada de privilegios**: Obtención de permisos dentro de un límite o a través de él; no siempre es lo mismo que escapar de un contenedor
- **Movimiento lateral**: Acceso no autorizado de un contenedor a otro
- **Explotación de montajes de volúmenes**: Acceso a rutas sensibles del host

### Controles de seguridad de red

#### 1. Firewalls

Los firewalls son sistemas de seguridad de red que filtran el tráfico según reglas de seguridad definidas.

- **Filtrado de paquetes**: Filtrado basado en direcciones IP, puertos y protocolos
- **Inspección con estado**: Decisiones basadas en el contexto, con seguimiento del estado de las conexiones
- **Filtrado de la capa de aplicación**: Comprensión e inspección de protocolos de aplicación
- **Firewalls de nueva generación (NGFW)**: Funciones avanzadas de detección y prevención de amenazas

#### 2. Sistemas de detección y prevención de intrusiones (IDS/IPS)

IDS/IPS son sistemas que supervisan el tráfico de red y detectan o bloquean actividades maliciosas.

- **Detección basada en firmas**: Búsqueda de patrones de ataques conocidos
- **Detección de anomalías**: Identificación de actividades que se desvían del comportamiento normal
- **Supervisión del comportamiento**: Análisis de patrones de actividad sospechosos
- **Respuesta automatizada**: Respuesta en tiempo real ante las amenazas detectadas

#### 3. Políticas de red

Las políticas de red son conjuntos de reglas que definen las comunicaciones permitidas dentro de una red.

- **Control de Ingress**: Restricción del tráfico entrante
- **Control de Egress**: Restricción del tráfico saliente
- **Políticas detalladas**: Control de comunicaciones en el nivel de la carga de trabajo
- **Políticas basadas en etiquetas**: Aplicación flexible de políticas en entornos dinámicos

#### 4. Protocolos de cifrado

Los protocolos de cifrado proporcionan comunicaciones seguras a través de las redes.

- **TLS**: Protección del tráfico web y las comunicaciones con las API; los protocolos SSL están obsoletos
- **IPsec**: Cifrado en la capa de red
- **WireGuard**: Protocolo VPN moderno y eficiente
- **mTLS (TLS mutuo)**: Autenticación tanto del cliente como del servidor

### Seguridad de red en Kubernetes

Kubernetes proporciona varios mecanismos para la seguridad de red de las aplicaciones en contenedores:

#### 1. Network Policies

Kubernetes NetworkPolicy especifica autorizaciones L3/L4 para los Pods seleccionados. Requiere una implementación de red que las aplique; las autorizaciones de las políticas aplicables se combinan, y las rutas existentes o de red del host tienen semánticas propias.

- **Selectores de Pods**: Seleccionan los Pods a los que se aplican las políticas según sus etiquetas
- **Reglas de Ingress**: Controlan el tráfico entrante
- **Reglas de Egress**: Controlan el tráfico saliente
- **Reglas basadas en CIDR**: Filtran según rangos de IP

Este ejemplo L4 usa su propio namespace y presupone que existen cargas de trabajo frontend/API/base de datos con las etiquetas indicadas, así como las etiquetas especificadas de CoreDNS. Incluye Egress de DNS. Manténgalo separado del ejemplo L7 posterior: una autorización amplia L4 puede eludir una restricción L7 superpuesta.

```yaml
# api-l4-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-allow
  namespace: cilium-policy-l4-demo
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 8080
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: database
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
```

#### 2. Seguridad de service mesh

Un service mesh es una capa de infraestructura que gestiona y protege la comunicación entre microservicios.

- **mTLS**: Comunicación cifrada entre servicios
- **Autenticación y autorización**: Verificación de la identidad del servicio y control de acceso
- **Políticas de tráfico**: Enrutamiento y control de acceso detallados
- **Observabilidad**: Visibilidad de la comunicación entre servicios

#### 3. Contextos de seguridad

Los contextos de seguridad definen la configuración de privilegios y control de acceso para Pods y contenedores.

- **Restricción de privilegios**: Ejecución como usuario no root
- **Restricción de capabilities**: Permiso solo para las capabilities necesarias de Linux
- **Sistema de archivos raíz de solo lectura**: Restringe las escrituras al sistema de archivos raíz del contenedor; los volúmenes montados pueden seguir permitiendo escrituras
- **seccomp y AppArmor**: Restricción de llamadas al sistema y del comportamiento de las aplicaciones

### Funciones de seguridad de red de Cilium

Cilium aprovecha eBPF para proporcionar potentes funciones de seguridad de red:

#### 1. Seguridad basada en la identidad

Cilium admite políticas basadas en la identidad de las cargas de trabajo, derivada de etiquetas pertinentes para la seguridad, además de controles explícitos de CIDR/IP cuando se configuran.

- **Políticas basadas en etiquetas**: Seguridad coherente en entornos dinámicos
- **Políticas basadas en cuentas de servicio**: Control de acceso basado en cuentas de servicio de Kubernetes
- **Políticas basadas en DNS**: Control de Egress basado en FQDN
- **Seguridad consciente de la API**: Filtrado basado en métodos y rutas HTTP

`toCIDR` selecciona rangos de destino, pero, de forma predeterminada, los selectores CIDR no coinciden con los Pods/nodos gestionados dentro del clúster; esta versión ofrece una opción explícita Beta para esos casos. La entidad `world` abarca endpoints externos, no todas las identidades conocidas del clúster/ClusterMesh. Use el ámbito de identidad/entidad apropiado en lugar de tratar `world` como sinónimo de permitir todos los clústeres.

#### 2. Cifrado transparente

Cilium puede cifrar rutas compatibles sin cambios en las aplicaciones. Los túneles entre nodos no cubren el tráfico dentro del mismo nodo ni todos los destinos externos. El protocolo de enlace de autenticación mutua de SPIRE, que es independiente, no cifra por sí mismo el tráfico de las aplicaciones; el mTLS de cargas de trabajo mediante ztunnel Beta tiene sus propios requisitos previos.

- **IPsec**: Cifrado en la capa de red para el tráfico entre nodos
- **WireGuard**: Protocolo de cifrado moderno y eficiente
- **Integración transparente**: El cifrado se aplica sin cambios en las aplicaciones
- **Rotación de claves**: Siga el ciclo de vida de claves del modo elegido; IPsec de Cilium requiere material de claves aprovisionado y el procedimiento documentado de rotación de Secret

#### 3. Detección de amenazas y visibilidad

Cilium/Hubble proporciona observaciones de red que pueden ayudar en las investigaciones. Un IDS/WAF completo, la aplicación de controles en tiempo de ejecución o un flujo de trabajo de alertas/respuesta requieren la configuración o integración independiente adecuada.

- **Hubble**: Supervisión y análisis de flujos de red
- **Registros de flujo**: Registros detallados de la comunicación entre Pods
- **Detección de anomalías**: Las reglas de detección externas pueden analizar patrones observados; Hubble no clasifica automáticamente todos los ataques
- **Alertas de eventos de seguridad**: Configure una integración con alertas/SIEM y tenga en cuenta la pérdida de eventos, el ruido y las observaciones incompletas

#### 4. Aplicación de políticas L3-L7

Cilium ofrece una aplicación integral de políticas desde la capa de red hasta la capa de aplicación.

- **Políticas L3/L4**: Filtrado basado en IP y puertos
- **Filtrado HTTP L7**: Control basado en URL, método y encabezados
- **Filtrado gRPC L7**: Control basado en métodos y metadatos gRPC
- **Política DNS**: Filtrado de consultas y observación de DNS para reglas FQDN; actualmente no hay políticas L7 para temas de Kafka

#### Ejemplo de configuración de seguridad de red de Cilium:

Esta política L7 alternativa usa un namespace distinto al del ejemplo L4. Requiere HTTP en texto claro visible o una ruta adecuada de inspección de TLS, dependencias etiquetadas reales y acceso al resolvedor. El nombre externo `.example` es un marcador de posición; no se aprovisiona ningún servicio externo operativo.

```yaml
# api-l7-policy.yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: secure-api
  namespace: cilium-policy-l7-demo
spec:
  endpointSelector:
    matchLabels:
      app: api
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: cilium-policy-l7-demo
        k8s:app: frontend
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
      rules:
        http:
        - method: GET
          path: /api/v1/products
  egress:
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
        k8s:k8s-app: kube-dns
    toPorts:
    - ports:
      - port: '53'
        protocol: UDP
      - port: '53'
        protocol: TCP
      rules:
        dns:
        - matchPattern: '*'
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: cilium-policy-l7-demo
        k8s:app: database
    toPorts:
    - ports:
      - port: '5432'
        protocol: TCP
  - toFQDNs:
    - matchName: api.external-service.example
    toPorts:
    - ports:
      - port: '443'
        protocol: TCP
```

### Prácticas recomendadas de seguridad de red

#### 1. Política de denegación predeterminada

- Implemente una política de denegación predeterminada que solo permita el tráfico autorizado explícitamente
- Abra únicamente las rutas de comunicación necesarias
- Revise las políticas con regularidad y elimine las reglas innecesarias
- Mantenga un registro de auditoría de los cambios en las políticas

#### 2. Enfoque de defensa en profundidad

- Implemente varias capas de seguridad
- Combine la protección de red, host y aplicación
- Use controles redundantes con distintos mecanismos de seguridad
- Elimine los puntos únicos de fallo

#### 3. Redes con privilegios mínimos

- Permita solo el acceso de red mínimo necesario
- Defina políticas detalladas para cada servicio
- Bloquee los puertos y protocolos innecesarios
- Revise y ajuste el acceso periódicamente

#### 4. Supervisión y auditoría continuas

- Supervise el tráfico de red y las infracciones de las políticas
- Detecte anomalías y posibles amenazas
- Configure alertas y respuestas ante eventos de seguridad
- Realice auditorías de seguridad y evaluaciones de vulnerabilidades periódicas

## Referencias principales

- [Enrutamiento de Cilium](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/network/concepts/routing.rst)
- [Valores del chart de Cilium](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/install/kubernetes/cilium/values.yaml)
- [Reemplazo de kube-proxy](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/network/kubernetes/kubeproxy-free.rst)
- [Masquerading](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/network/concepts/masquerading.rst)
- [Plano de control BGP](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/network/bgp-control-plane/bgp-control-plane.rst)
- [Global Services](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/network/clustermesh/global-services.rst)
- [Lenguaje de políticas](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/security/policy/layer3.rst)
- [Política DNS](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/security/dns.rst)
- [IPsec](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/security/network/encryption-ipsec.rst)
- [WireGuard](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/security/network/encryption-wireguard.rst)
- [Modelo de red de Kubernetes](https://kubernetes.io/docs/concepts/services-networking/)
- [Services](https://kubernetes.io/docs/concepts/services-networking/service/)
- [DNS para Services y Pods](https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/)
- [NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Especificación de CNI](https://raw.githubusercontent.com/containernetworking/cni/main/SPEC.md)
- [Redes de puente de Docker](https://docs.docker.com/engine/network/drivers/bridge/)
- [Redes del host de Docker](https://docs.docker.com/engine/network/drivers/host/)
- [Retirada de Ingress NGINX](https://kubernetes.io/blog/2025/11/11/ingress-nginx-retirement/)
- [Arquitectura de Internet / RFC 1122](https://www.rfc-editor.org/rfc/rfc1122.txt)
- [DNS / RFC 1034](https://www.rfc-editor.org/rfc/rfc1034.txt)
- [Terminología de NAT / RFC 2663](https://www.rfc-editor.org/rfc/rfc2663.txt)
- [Comportamiento de las asignaciones NAT / RFC 4787](https://www.rfc-editor.org/rfc/rfc4787.txt)
- [RIP v2 / RFC 2453](https://www.rfc-editor.org/rfc/rfc2453.txt)
- [EIGRP / RFC 7868](https://www.rfc-editor.org/rfc/rfc7868.txt)

## Cuestionario

Para comprobar lo que aprendió en este capítulo, pruebe el [cuestionario del tema](../../quizzes/networking/cilium/networking-concepts-quiz.md).
