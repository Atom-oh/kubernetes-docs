# Redes de Kubernetes

> **Última actualización**: 13 de septiembre de 2026. Las referencias incluyen Cilium 1.20.1, Calico Open Source 3.32, Flannel 0.28.9 y AWS VPC CNI 1.23.0. Consulte la matriz Kubernetes/plataforma de cada producto antes de instalar; no constituyen una configuración probada conjuntamente.

## Descripción general

La red de Kubernetes es la capa central de infraestructura que permite la comunicación entre aplicaciones en contenedores. Esta sección abarca desde los conceptos básicos de redes de Kubernetes hasta soluciones avanzadas de CNI (Container Network Interface) y patrones de red en entornos AWS EKS.

## Modelo de red de Kubernetes

El modelo actual ofrece una red donde los Pods se comunican directamente entre nodos sin traducción de direcciones ni proxies, **sujetos a la segmentación intencionada de la red**. Los agentes como kubelet deben alcanzar los Pods de su propio nodo. Las políticas, las rutas y los listeners de aplicación siguen determinando si una conexión concreta tiene éxito.

Los Pods ordinarios tienen su propio espacio de nombres de red y direcciones únicas en el clúster; sus contenedores comparten ese espacio y localhost. Los Pods con red de host comparten la del nodo; las configuraciones dual-stack o multirred necesitan un tratamiento más preciso de direcciones. Recrear un Pod puede cambiar su IP; reiniciar un contenedor del mismo Pod no recrea necesariamente el entorno de red.

| Componente | Función |
|---|---|
| Red de Pods | Direccionamiento y conectividad entre espacios de red de cargas |
| Service/descubrimiento | Nombres estables o direcciones virtuales sobre endpoints cambiantes |
| Implementación Ingress/Gateway | Entrada externa y enrutamiento de aplicaciones configurados |
| Motor de políticas | Aplica las políticas soportadas por la implementación elegida |

Estas funciones no forman un recorrido serial obligatorio. La traducción de Service, un proxy L7 y las políticas pueden cambiar la ruta de cada solicitud.

### Red de Pods

Proporciona direcciones y rutas para comunicar Pods. La ilustración muestra Pods IPv4 ordinarios y presupone que las políticas y controles permiten sus conexiones.

![Rutas IPv4 directas entre Pods de dos nodos, sujetas a las políticas y rutas configuradas.](../.gitbook/assets/en-networking-readme-1.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-1.html)

Las direcciones son ejemplos de Pods ordinarios. El aislamiento intencionado, la red de host y las configuraciones multirred requieren su propia interpretación.

#### Métodos de implementación

| Método | Descripción | Ejemplos de CNI |
|--------|-------------|-------------|
| **Red superpuesta** | Encapsula tráfico sobre la red existente | Flannel VXLAN, Calico VXLAN/IPIP, Cilium VXLAN/Geneve |
| **Enrutamiento nativo** | Usa rutas subyacentes sin esa encapsulación | AWS VPC CNI, Calico routing/BGP, Cilium native routing |
| **Encapsulación condicional** | Elige rutas directas o encapsulación según la topología | Modos compatibles de Calico/Flannel/Cilium, con requisitos distintos |

### Red de Services

Los Services describen un conjunto lógico de endpoints, normalmente Pods, y cómo alcanzarlos. ClusterIP ofrece una IP virtual estable por defecto; headless la omite y ExternalName usa un CNAME DNS. También pueden existir endpoints administrados sin selector de Pods.

![Entradas habituales de ClusterIP, NodePort, LoadBalancer y ExternalName; se diferencia el mapeo DNS del reenvío de paquetes.](../.gitbook/assets/en-networking-readme-2.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-2.html)

Son mecanismos habituales de exposición, no garantías de seguridad. El rango NodePort y las direcciones accesibles son configurables; un LoadBalancer puede ser interno. ExternalName devuelve un alias DNS y no crea un proxy de reenvío.

#### Características de los tipos de Service

Cree Pods `app: my-app` en `default` escuchando en los puertos de destino indicados. El rango NodePort predeterminado, configurable, es 30000–32767. La accesibilidad externa depende de direcciones, rutas y controles.

El ejemplo LoadBalancer selecciona explícitamente **AWS Load Balancer Controller**, destinos de instancia EC2 y NodePorts asignados. Prepare primero controlador, IAM y subredes. Auto Mode usa otro controlador/clase. Aquí 443 solo elige un puerto TCP; el backend debe servir TLS en 8443 o configurarse por separado en el balanceador.

Estos mapeos ilustran la API general de Service. AWS documenta requisitos adicionales para su política EKS nativa: el puerto Service debe coincidir con el del contenedor, y los Pods gestionados por controlador con `metadata.ownerReferences` permiten aplicación fiable. Adapte los ejemplos antes de probar ese motor.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-service
  namespace: default
spec:
  type: ClusterIP
  selector:
    app: my-app
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8080
---
apiVersion: v1
kind: Service
metadata:
  name: my-nodeport-service
  namespace: default
spec:
  type: NodePort
  selector:
    app: my-app
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8080
    nodePort: 30080
---
apiVersion: v1
kind: Service
metadata:
  name: my-loadbalancer-service
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-scheme: internet-facing
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: instance
  namespace: default
spec:
  type: LoadBalancer
  selector:
    app: my-app
  ports:
  - protocol: TCP
    port: 443
    targetPort: 8443
  loadBalancerClass: service.k8s.aws/nlb
  allocateLoadBalancerNodePorts: true
```

### Red de Ingress

Ingress necesita controlador y plano de datos. El ejemplo HTTP usa AWS LBC con `spec.ingressClassName: alb` y destinos IP. `api-v1`, `api-v2` y `web-frontend` deben existir en `default`, publicar 80 y tener endpoints listos enrutables en la VPC. Configure HTTPS/certificados aparte cuando corresponda. Consulte la [guía LBC](03-aws-lb-controller.md).

Ingress define reglas HTTP/HTTPS hacia Services internos.

![Enrutamiento lógico por host/ruta de Ingress hacia Services backend y Pods.](../.gitbook/assets/en-networking-readme-3.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-3.html)

El cuadro representa la función del plano de datos. LBC programa ALB; el tráfico no atraviesa la reconciliación del controlador. Según el modo, puede llegar a IP de Pods o NodePorts sin pasar por la IP virtual del Service como salto literal adicional.

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: my-ingress
  annotations:
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
  namespace: default
spec:
  rules:
  - host: api.example.com
    http:
      paths:
      - path: /v1
        pathType: Prefix
        backend:
          service:
            name: api-v1
            port:
              number: 80
      - path: /v2
        pathType: Prefix
        backend:
          service:
            name: api-v2
            port:
              number: 80
  - host: web.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: web-frontend
            port:
              number: 80
  ingressClassName: alb
```

## CNI (Container Network Interface)

CNI estandariza cómo el runtime configura la red de un contenedor. Actualmente kubelet solicita operaciones del entorno de Pod mediante CRI y el **runtime de contenedores administra CNI**. Los antiguos indicadores de gestión directa de kubelet se eliminaron en Kubernetes 1.24.

### Responsabilidades del runtime y los plugins

| Actor | Responsabilidad |
|---|---|
| kubelet | Solicita crear/eliminar el entorno mediante la interfaz del runtime |
| Runtime de contenedores | Selecciona la configuración e invoca la cadena CNI |
| Plugin CNI | Recibe configuración, ejecuta ADD/DEL y otras operaciones compatibles, y devuelve resultados |
| Implementación IPAM | Asigna/libera direcciones; puede delegarse a un plugin o integrarse en un agente específico |
| Agente de nodo opcional | Mantiene rutas, políticas, grupos IP o estado del datapath del proveedor |

El runtime entrega configuración mediante CNI; no todos los plugins requieren un agente permanente o binario IPAM separado. También varían las interfaces: los pares veth son habituales, pero no únicos.

## Comparación de CNI

| Proyecto / alcance | Redes y políticas | Funciones y límites que distinguir |
|---|---|---|
| **Cilium 1.20.1** | Redes eBPF; Envoy para funciones L7; políticas Cilium y Hubble | Dataplane Linux con requisitos AMD64/Arm64. CLI Windows no implica CNI Windows. WireGuard/IPsec y ztunnel mTLS Beta tienen ámbitos distintos. |
| **Calico Open Source 3.32** | Opciones de rutas/encapsulación, iptables/nftables/eBPF, niveles ordenados y políticas de host/cargas | Windows tiene límites propios, sin dataplane Linux eBPF/WireGuard. Whisker/Goldmane está en vista previa técnica. Consulte la matriz para funciones de pago. |
| **Flannel 0.28.9** | Subredes de host y transporte entre nodos; VXLAN, host-gw y otros backends | `flanneld` no aplica NetworkPolicy; `netpol.enabled` instala el controlador SIGs opcional. WireGuard está documentado e IPsec es experimental. VXLAN Windows tiene ajustes y límites propios. |
| **AWS VPC CNI 1.23.0 / EKS** | Direcciones VPC y ENI/prefijos EC2; políticas estándar/Admin en Linux EC2 compatible | Auto Mode es una implementación administrada con políticas DNS adicionales. Windows, Fargate, redes personalizadas, delegación de prefijos y varias NIC tienen condiciones separadas. |
| **Proyecto Weave Net original** | Implementación histórica de red superpuesta | `weaveworks/weave` está archivado. No lo presente como opción predeterminada activa y soportada para un clúster nuevo. |

### Políticas, cifrado y observabilidad

- Cilium ofrece políticas HTTP/DNS mediante los componentes L7 correspondientes y políticas globales/de host. Su semántica deny/allow no es la API ordenada Tier de Calico.
- Calico Open Source incluye niveles jerárquicos y política de host. La matriz actual reserva política de aplicación, DNS/FQDN y Cluster Mesh para Cloud/Enterprise; no los atribuya silenciosamente a Open Source. Su cifrado en tránsito documentado usa WireGuard.
- EKS ofrece controles Admin/Baseline `ClusterNetworkPolicy` en Auto Mode e instalaciones EC2/VPC-CNI compatibles. La función DNS/FQDN `ApplicationNetworkPolicy` descrita por AWS corresponde a **Auto Mode**; el nombre no implica inspección actual de métodos/cuerpos HTTP.
- El controlador opcional de Flannel tiene requisitos propios; elegir un backend no activa por sí solo la aplicación de políticas.
- Cifrado entre nodos, identidad autenticada de carga y mTLS de aplicación son controles distintos. La visibilidad de flujos también difiere del tracing o control de procesos/archivos.

### Rutas y rendimiento

Calico y Cilium anuncian rutas BGP, pero eso no proporciona por sí solo descubrimiento multiclúster, sincronización de políticas o cifrado. Flannel host-gw usa rutas directas y necesita conectividad L2 adecuada. Una superposición añade encapsulación y consideraciones MTU; el nombre del CNI no permite deducir una clasificación universal de rendimiento.

La antigua cifra de rendimiento 100/98/95/85/80/75% no tenía carga reproducible, versiones ni fuente. Compare hardware, kernel, tamaños, concurrencia, cifrado/políticas, rendimiento, pérdidas y latencia de cola equivalentes. El [benchmark de Pods](06-pod-network-benchmark.md) conserva su entorno y mediciones históricos.

## Guía de selección de CNI

Elija primero rutas, políticas, sistema operativo y soporte necesarios; pruebe después la combinación.

| Necesidad | Evaluación |
|---|---|
| Direcciones VPC EKS estándar y políticas compatibles | Evalúe AWS VPC CNI/EKS antes de añadir otro motor. |
| Niveles ordenados, política host o BGP de infraestructura | Evalúe edición/dataplane Calico y requisitos de rutas. |
| Políticas Cilium, Hubble o funciones de mesh | Compruebe Linux/kernel/plataforma y la [guía Cilium](../service-mesh/cilium-service-mesh/README.md). Envoy sigue en las rutas L7 pertinentes. |
| Red pequeña con pocas funciones | Evalúe backend Flannel y controlador opcional frente a requisitos reales. |
| Control de procesos, syscalls o archivos | Evalúe un componente runtime como Tetragon aparte de la política de red. |

### Configuración de complemento administrado EKS

Lo siguiente es una **carga de configuración** de ejemplo, no una instrucción para instalar Calico y el motor VPC CNI sobre las mismas cargas:

```json
{
  "enableNetworkPolicy": "true"
}
```

La cadena `"true"` es el tipo documentado. Seleccione un build compatible con la versión Kubernetes existente e inspeccione su esquema:

```bash
EKS_REGION=ap-northeast-2
KUBERNETES_MINOR=1.35  # Replace with the existing cluster's minor version
aws eks describe-addon-versions --region "$EKS_REGION" --addon-name vpc-cni \
  --kubernetes-version "$KUBERNETES_MINOR"
: "${VPC_CNI_ADDON_VERSION:?Set the compatible eksbuild version selected from metadata}"
aws eks describe-addon-configuration --region "$EKS_REGION" --addon-name vpc-cni \
  --addon-version "$VPC_CNI_ADDON_VERSION"
```

La versión upstream 1.23.0 y un `eksbuild` son identificadores distintos. Combine los cambios con la configuración prevista; no seleccione `latest` a ciegas ni sustituya valores ajenos. Migrar desde otro motor también requiere retirar su estado de aplicación existente y un plan probado de transición de nodos/cargas.

## Fundamentos de red de EKS

### Arquitectura predeterminada

| Ubicación / componente | Responsabilidad |
|---|---|
| VPC administrada por EKS | AWS ejecuta el plano de control administrado entre AZ. |
| VPC del clúster del cliente | Red de workers, subredes y ENI entre cuentas administradas por EKS proporcionan las rutas al plano de control. |
| ALB/NLB en subredes elegidas de la VPC del cliente | Entrada pública o interna; internet gateway/NAT no sustituye esa configuración. |
| NAT gateway o endpoints privados | Rutas de salida concretas que necesita el diseño. |

La figura anterior situaba el control plane dentro de la VPC del cliente y los balanceadores fuera; se sustituyó por estos límites de propiedad.

### DNS y redes según el cómputo

| Modo | DNS / ubicación de componentes |
|---|---|
| Nodos EC2 estándar | Normalmente CoreDNS Deployment y componentes instalados; las sustituciones necesitan configuración compatible propia. |
| Solo EKS Auto Mode | CoreDNS, VPC CNI y kube-proxy funcionan como servicios systemd administrados; no necesitan Deployment/add-on CoreDNS. |
| Auto Mode y nodos no Auto mezclados | Conserve CoreDNS Deployment para los nodos no Auto; no pueden usar DNS Auto Mode de otro nodo. |

El primer resolver Auto Mode es local al nodo. El reenvío upstream y la comunicación de control todavía pueden necesitar red; no garantiza que todo paquete DNS permanezca local. AWS documenta Admin y DNS para Auto Mode, mientras Admin en EC2/VPC-CNI tiene requisitos propios de versión/activación.

### Funcionamiento de VPC CNI

VPC CNI asigna direcciones enrutables a Pods ordinarios según IPAM. Direcciones IPv4 secundarias, prefijos delegados, ENI de rama y varias NIC difieren; host-network comparte la red del nodo.

![Asignación ilustrativa de IPv4 secundarias desde ENI EC2 a Pods, incluida una interfaz caliente opcional.](../.gitbook/assets/en-networking-readme-9.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-9.html)

Solo muestra modo secondary-IP. Una ENI caliente es una estrategia configurable, no la obligación de reservar exactamente una siempre. Delegación, redes personalizadas y ENI de rama tienen reglas diferentes.

#### Límites de ENI e IP

| Tipo de instancia | ENI máximas | Espacios IPv4 por ENI | Valor histórico de arranque secondary-IP |
|---------------|----------|--------------|------------------------|
| t3.medium | 3 | 6 | 17 |
| t3.large | 3 | 12 | 35 |
| m5.large | 3 | 10 | 29 |
| m5.xlarge | 4 | 15 | 58 |
| m5.2xlarge | 4 | 15 | 58 |
| c5.4xlarge | 8 | 30 | 234 |

Se verificaron contra los límites de VPC CNI 1.23.0 y la tabla histórica max-Pods. La fórmula `ENIs × (IPv4 slots per ENI − 1) + 2` no es una recomendación universal actual. Prefijos, redes personalizadas, ENI de rama y varias tarjetas cambian la capacidad. La programación también queda limitada por `maxPods` y recursos. Los grupos administrados EKS limitan `maxPods` a 110 con menos de 30 vCPU y 250 en el resto; disponer de más IP no anula ese límite.

### Consideraciones de red de EKS

#### Gestión de direcciones IP

Para **Linux VPC CNI**, configure las variables de entorno documentadas mediante el mecanismo de gestión seleccionado de complemento/Helm/DaemonSet. Lo siguiente es un fragmento de configuración del complemento de EKS. El antiguo ConfigMap `amazon-vpc-cni` con `enable-prefix-delegation` no configura Linux IPAMD de esta manera. Conserve los demás valores previstos del complemento al aplicar un cambio.

```json
{
  "env": {
    "ENABLE_PREFIX_DELEGATION": "true",
    "WARM_PREFIX_TARGET": "1"
  }
}
```

Como alternativa, ajuste el mínimo total y objetivo de IP libres. `MINIMUM_IP_TARGET` o `WARM_IP_TARGET` prevalecen sobre `WARM_PREFIX_TARGET`; son políticas alternativas, no cuatro objetivos aditivos. La asignación sigue usando unidades de prefijo. Soporte Nitro, espacio IPv4 `/28` contiguo y límite kubelet adecuado son requisitos independientes.

La asignación de prefijos de Windows utiliza una ruta de configuración diferente: AWS documenta `enable-windows-prefix-delegation` y sus claves de objetivos de reserva en el ConfigMap `amazon-vpc-cni`. No copie sin cambios a Windows el procedimiento de variables de entorno de Linux.

```json
{
  "env": {
    "ENABLE_PREFIX_DELEGATION": "true",
    "MINIMUM_IP_TARGET": "5",
    "WARM_IP_TARGET": "2"
  }
}
```

#### Redes personalizadas

Los ejemplos IPv4 requieren ID reales de subred/grupo en la AZ y VPC previstas. Active la función y seleccione ENIConfig mediante la etiqueta de zona del nodo. Una anotación ENIConfig explícita prevalece. Los nombres usan la misma región en ambos idiomas; sustitúyalos por las zonas reales. Instalar objetos ENIConfig no activa por sí solo la función.

```json
{
  "env": {
    "AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG": "true",
    "ENI_CONFIG_LABEL_DEF": "topology.kubernetes.io/zone"
  }
}
```

```yaml
apiVersion: crd.k8s.amazonaws.com/v1alpha1
kind: ENIConfig
metadata:
  name: ap-northeast-2a
spec:
  securityGroups:
  - sg-0123456789abcdef0
  subnet: subnet-0123456789abcdef0
---
apiVersion: crd.k8s.amazonaws.com/v1alpha1
kind: ENIConfig
metadata:
  name: ap-northeast-2b
spec:
  securityGroups:
  - sg-0123456789abcdef0
  subnet: subnet-fedcba9876543210f
```

## Conceptos avanzados de redes

Los elementos siguientes se mencionan brevemente en otras partes de esta introducción. Las páginas enlazadas contienen los procedimientos completos y mediciones; aquí se ordenan sus diferencias por capa y su función.

### L2–L7 y la diferencia entre routers y balanceadores

Aunque suelen mencionarse juntos, responden a preguntas distintas. Un router elige normalmente una ruta hacia un destino; un balanceador elige un destino entre varios candidatos equivalentes mediante un algoritmo de distribución.

| Capa | Dispositivo/función | Criterio | Correspondencia Kubernetes/AWS |
|---|---|---|---|
| L2 (enlace) | Switch, bridge | MAC de destino | Pares veth y bridges Linux del CNI, NIC virtual de una ENI |
| L3 (red) | Router o inserción transparente de dispositivos | IP destino para rutas; identidad del flujo para elegir dispositivo | Router implícito de VPC, TGW; GWLB encapsula paquetes IP para dispositivos |
| L4 (transporte) | Balanceador L4 | Identidad de conexión/flujo, normalmente 5-tupla | NLB; kube-proxy (iptables, IPVS, nftables); implementaciones Service eBPF separadas |
| L7 (aplicación) | Balanceador L7/proxy inverso | Host, ruta y cabeceras por solicitud, con conocimiento del protocolo | ALB, implementaciones Ingress/Gateway API, sidecars Envoy |

La diferencia principal es la **unidad de distribución**. L4 normalmente selecciona por conexión TCP o flujo UDP seguido. Un proxy L7 puede hacerlo por solicitud compatible, incluso dentro de una misma conexión. GWLB distribuye flujos IP encapsulados entre dispositivos de seguridad, sin interpretar solicitudes. La afinidad depende de timeout, salud y failover; no garantiza que un flujo nunca se reasigne o interrumpa.

> 📎 Las definiciones L2/L3 están en [Fundamentos de red, Parte 1](../basics/06-network-fundamentals-part1.md); los tipos de destino y configuración ALB/NLB, en [AWS Load Balancer Controller](03-aws-lb-controller.md).

### Conectividad entre cuentas/VPC: TGW, VPC Peering, GWLB, PrivateLink, Lattice

Estas cinco opciones difieren en capa y modelo de tráfico. [Conectividad VPC entre organizaciones](05-cross-org-vpc-connectivity.md) contiene latencias medidas para TGW compartido por RAM, VPC Peering, PrivateLink, TGW Peering y Lattice. Aquí se añade GWLB, ausente de aquella tabla, y se reorganizan las cinco por capa.

| Conectividad | Capa/modelo | Características |
|---|---|---|
| VPC Peering | L3, rutas IP bidireccionales | No transitivo; no admite CIDR superpuestos |
| Transit Gateway (TGW) | L3, concentrador y radios | Asociaciones y propagación de adjuntos en una o más tablas TGW; compartido entre cuentas por RAM |
| Gateway Load Balancer (GWLB) | L3, inserción transparente | Encapsula en GENEVE (UDP 6081); el servicio de endpoint VPC conecta tráfico consumidor con dispositivos del proveedor |
| PrivateLink | Conectividad privada por endpoints | El servicio con NLB es un modelo; también hay endpoints de recursos. Los CIDR pueden solaparse |
| VPC Lattice | Redes de aplicaciones y recursos | HTTP/HTTPS con rutas L7 e IAM opcional; TLS passthrough y recursos tienen capacidades distintas |

GWLB inserta dispositivos de inspección, como cortafuegos e IDS/IPS, en una ruta IP mediante un endpoint de Gateway Load Balancer. Su afinidad de flujo predeterminada utiliza cinco campos; las configuraciones compatibles pueden utilizar dos o tres en su lugar. Valide las rutas de ida y retorno, el estado de los dispositivos, la MTU de encapsulación, las NACL y los grupos de seguridad de las cargas de trabajo/dispositivos reales. GWLB no tiene un grupo de seguridad al estilo ALB, y la afinidad de flujo no sustituye las pruebas de fallo.

> 📎 La integración EKS/Lattice completa, con controlador, IAM y rutas, está en [VPC Lattice](02-vpc-lattice.md).

### Comportamiento real de DNS Resolver y tablas de rutas

**Resolver DNS:** AmazonProvidedDNS **es Route 53 Resolver**. Sus direcciones incluyen la dirección IPv4 primaria de red VPC más dos (`10.0.0.2` para `10.0.0.0/16`) y `169.254.169.253`; resuelve zonas privadas asociadas y nombres públicos según sus reglas. CoreDNS sirve normalmente el dominio del clúster, a menudo `cluster.local`; `kube-dns` es el nombre del Service, no un namespace o zona DNS. El reenvío externo sigue Corefile y el archivo resolver visible para el Pod DNS. Inspecciónelos, sin asumir que se usa intacto el archivo del nodo. Los endpoints de entrada reciben consultas locales externas; los de salida y sus reglas envían consultas VPC seleccionadas al DNS local. El resolver local de Auto Mode no elimina dependencias upstream.

**Tablas de rutas:** VPC suele elegir el prefijo más largo. AWS permite sustituir el destino de una ruta `local` y añadir rutas de subred más específicas compatibles para dispositivos; `local` no siempre es la más específica. Para destinos idénticos, las rutas estáticas VPC prevalecen sobre las propagadas desde una virtual private gateway. Una ruta VPC a TGW es estática; la propagación dentro de TGW pertenece a sus propias tablas. Un destino inválido puede dejar entradas `blackhole` que descartan tráfico: revise el estado además del destino. Sin asociación explícita, una subred usa la tabla principal de la VPC.

> 📎 Consulte prioridades TGW/Peering y rutas estáticas en los [hallazgos operativos de conectividad VPC entre organizaciones](05-cross-org-vpc-connectivity.md#operational-findings).

### Plano de datos del kernel: iptables, IPVS, eBPF y filtrado

El reenvío de Service en Linux y la aplicación de políticas de red pueden utilizar mecanismos distintos. Netfilter proporciona puntos de conexión de la ruta de paquetes utilizados por iptables y nftables. Las implementaciones eBPF pueden asociarse a puntos XDP, tc o de sockets y realizar allí la selección de Service. Esto no significa que todos los paquetes de un clúster con eBPF eludan Netfilter o el seguimiento de conexiones; la ruta depende del CNI, el kernel, el enrutamiento y la configuración de funciones.

| Implementación | Ubicación | Características |
|---|---|---|
| iptables | Cadenas secuenciales sobre hooks netfilter | Tiempo proporcional a reglas (O(n)); modo predeterminado histórico de kube-proxy |
| IPVS | Balanceador L4 del kernel, extensión netfilter | Búsqueda hash cercana a O(1); modo kube-proxy obsoleto desde Kubernetes 1.35 |
| nftables | Marco netfilter sucesor de iptables | Modo estable de kube-proxy desde 1.33; comprobar kernel/CNI |
| eBPF (p. ej., Cilium) | Hooks XDP, tc y socket configurados | Puede sustituir Service de kube-proxy; implementación separada con comportamiento Netfilter/conntrack específico de la ruta |

Un cambio puede dejar reglas del kernel y conexiones activas. Siga la migración de la distribución/CNI, drene cargas cuando corresponda y prevea reinicios si la limpieza los requiere. Sustituir kube-proxy por eBPF también exige un orden compatible para evitar competencia por el mismo tráfico Service.

> 📎 La obsolescencia de IPVS y estabilidad de nftables se explican en [Introducción a Kubernetes](../basics/04-kubernetes-introduction.md); la sustitución eBPF, en [Cilium eBPF](cilium/02-ebpf.md), y el dataplane/migración Calico, en [Calico eBPF](calico/06-ebpf-dataplane.md).

### Redes de cómputo intensivo: ENI, EFA, NVLink y transceptores ópticos

ENI, EFA y NVLink sirven rutas distintas. Una **ENI** es una interfaz virtual conectada a una instancia EC2 de una AZ; su tráfico IP normal puede alcanzar otras AZ/VPC conectadas si lo permiten rutas y políticas (véase [VPC CNI](01-vpc-cni.md)). **EFA** proporciona un dispositivo que evita el SO, usado mediante libfabric por MPI/NCCL compatible. **El tráfico del dispositivo EFA no es enrutable y no cruza límites VPC/AZ**; el tráfico IP normal del dispositivo ENA de EFA-with-ENA sigue siendo enrutable. EFA-only no tiene ENA ni direccionamiento IP. **NVLink** conecta GPU en sistemas compatibles, incluidos dominios a escala de rack soportados. Mida hardware, operaciones colectivas y ubicación, sin asumir una aceleración fija respecto a EFA.

Los **transceptores ópticos** son un concepto general de centros de datos. DAC de cobre sirve recorridos cortos; módulos ópticos y fibra cubren otras distancias y anchos de banda. QSFP/OSFP son formatos físicos, no garantía de medio óptico. Es contexto general, no prueba del cableado físico de una carga AWS concreta.

> 📎 La programación consciente de NVLink/IMEX y ubicación de GPU están en [Infraestructura AI/ML](../ai-ml/06-ai-infrastructure.md); los límites VPC/AZ y mediciones EFA, en [Conectividad VPC entre organizaciones](05-cross-org-vpc-connectivity.md).

### Protocolos de nueva generación en Kubernetes: HTTP/3, gRPC y QUIC

HTTP/3 (RFC 9114) y QUIC (RFC 9000) se explican en [Fundamentos de red, Parte 2](../basics/06-network-fundamentals-part2.md) y [Parte 3](../basics/06-network-fundamentals-part3.md). Aquí solo se aborda su efecto real en la distribución de tráfico.

- **gRPC y balanceadores L4:** gRPC multiplexa solicitudes en conexiones HTTP/2. L4 suele mantener una conexión TCP establecida en su endpoint; si este es un proxy, puede tomar decisiones adicionales. Añadir Pods no redistribuye conexiones existentes. Distribuir por RPC requiere proxy L7 o política cliente compatible. Un RPC streaming sigue siendo una llamada; sus mensajes no se balancean individualmente.
- **GRPCRoute de Gateway API:** Ingress no tiene un recurso específico de gRPC, pero Gateway API estandariza el enrutamiento a nivel de servicio/método con `GRPCRoute`. La compatibilidad varía según la implementación (cuántas coincidencias de cabeceras, políticas de reintentos, etc.), por lo que debe consultar la documentación del propio controlador.
- **Hasta dónde llega realmente HTTP/3/QUIC dentro del clúster:** La compatibilidad con HTTP/3 entre un cliente y el borde (una CDN, un equilibrador de carga) es una cuestión distinta de la compatibilidad con HTTP/3 dentro del clúster o en la conexión de backend de un Ingress. Muchas implementaciones de Ingress/Gateway siguen hablando HTTP/1.1 o HTTP/2 con el backend, y la compatibilidad con HTTP/3 de extremo a extremo varía según implementación y versión; no generalice, consulte la documentación del controlador realmente utilizado.

## Subpáginas de redes

Esta sección desarrolla los siguientes temas:

### [VPC CNI](01-vpc-cni.md)
Red EKS con direcciones VPC para Pods ordinarios y requisitos IPAM/política por modo.

### [Cilium en profundidad](cilium/README.md)
CNI de alto rendimiento basado en eBPF. Incluye política L7, service mesh y observabilidad Hubble.

### [Calico en profundidad](calico/README.md)
Uno de los CNI más utilizados. Potentes políticas de red, compatibilidad con BGP y funciones empresariales. Cubre introducción, arquitectura, modos de red, análisis detallado de BGP, políticas de red, eBPF, temas avanzados, integración con EKS y guía de operaciones.

### [VPC Lattice](02-vpc-lattice.md)
Servicio administrado AWS de redes de aplicaciones. Comunicación entre servicios de distintas VPC y cuentas.

### [AWS Load Balancer Controller](03-aws-lb-controller.md)
Integra Services e Ingress con AWS ELB (ALB/NLB).

### [Gateway API](04-gateway-api.md)
API de entrada Kubernetes de nueva generación, con recursos estandarizados y configuración por roles.

### [Benchmark de red de Pods](06-pod-network-benchmark.md)
RTT, latencia HTTP y rendimiento entre Pods medidos en EKS dentro de nodo/AZ y entre AZ, más amplificación DNS por `ndots:5`.

## Resolución de problemas de red

### Problemas y soluciones habituales

#### Fallo de comunicación entre Pods

```bash
NAMESPACE=default
POD_NAME=iperf-client  # An existing diagnostic Pod with nslookup/curl
SERVICE_NAME=my-service
kubectl -n "$NAMESPACE" get pods -o wide
kubectl -n "$NAMESPACE" exec "$POD_NAME" -- nslookup "$SERVICE_NAME"
kubectl -n "$NAMESPACE" exec "$POD_NAME" -- \
  curl --connect-timeout 3 --max-time 5 -v "http://$SERVICE_NAME:80/"
kubectl -n kube-system logs -l k8s-app=aws-node -c aws-node --tail=100
kubectl -n kube-system logs -l k8s-app=cilium -c cilium-agent --tail=100
```

Diagnostique desde un Pod existente con las herramientas indicadas. Consulte solo el CNI instalado; los servicios Auto Mode no son esos DaemonSets. DNS, conectividad TCP y respuesta HTTP son comprobaciones distintas. ICMP puede estar bloqueado o necesitar privilegios; un ping fallido no demuestra que un servicio TCP sea inaccesible.

#### Service inaccesible

```bash
NAMESPACE=default
SERVICE_NAME=my-service
kubectl -n "$NAMESPACE" get service "$SERVICE_NAME" -o yaml
kubectl -n "$NAMESPACE" get endpointslices \
  -l "kubernetes.io/service-name=$SERVICE_NAME" -o yaml
kubectl -n kube-system logs -l k8s-app=kube-proxy --tail=100
```

Utilice EndpointSlice para el diagnóstico actual de endpoints. Compruebe los selectores de Service, los puertos de destino, la disponibilidad de endpoints, la familia de direcciones y las políticas aplicables. Inspeccione los registros de kube-proxy solo si ese componente realmente gestiona el reenvío de Service; una sustitución eBPF o Auto Mode necesitan sus propios diagnósticos.

#### Diagnóstico de políticas

```bash
kubectl get networkpolicies.networking.k8s.io -A
kubectl -n kube-system exec ds/cilium -c cilium-agent -- cilium-dbg policy get
kubectl -n kube-system exec ds/cilium -c cilium-agent -- cilium-dbg endpoint list
# For a Calico installation using its standard CRD datastore:
kubectl get networkpolicies.crd.projectcalico.org -A
kubectl get globalnetworkpolicies.crd.projectcalico.org
```

Los comandos Cilium inspeccionan un Agent elegido por la referencia DaemonSet; seleccione el del nodo afectado. Calico con API nativa puede exponer otro grupo; compruebe los recursos servidos. Las políticas Kubernetes, Calico y extensiones AWS son recursos distintos con posibles precedencias diferentes.

### Pruebas de rendimiento

Este ejercicio TCP limitado usa el índice Netshoot v0.16 fijado por su editor, con Linux AMD64/Arm64 y `iperf3` en el Dockerfile. Cree los Pods en pruebas donde TCP 5201 esté permitido. Es una carga ilustrativa, no una comparación medida entre CNI.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: iperf-server
  namespace: default
  labels:
    app: iperf-server
spec:
  restartPolicy: Never
  automountServiceAccountToken: false
  nodeSelector:
    kubernetes.io/os: linux
  containers:
  - name: netshoot
    image: nicolaka/netshoot:v0.16@sha256:b09d9b21381f47a79b3cbcb30da25266dc17186ea00ae65e99fdc51396f48e70
    command:
    - iperf3
    - -s
    workingDir: /tmp
    resources:
      requests:
        cpu: 100m
        memory: 64Mi
      limits:
        cpu: 500m
        memory: 256Mi
    securityContext:
      runAsNonRoot: true
      runAsUser: 1000
      allowPrivilegeEscalation: false
      capabilities:
        drop:
        - ALL
      seccompProfile:
        type: RuntimeDefault
    ports:
    - containerPort: 5201
      protocol: TCP
---
apiVersion: v1
kind: Pod
metadata:
  name: iperf-client
  namespace: default
  labels:
    app: iperf-client
spec:
  restartPolicy: Never
  automountServiceAccountToken: false
  nodeSelector:
    kubernetes.io/os: linux
  containers:
  - name: netshoot
    image: nicolaka/netshoot:v0.16@sha256:b09d9b21381f47a79b3cbcb30da25266dc17186ea00ae65e99fdc51396f48e70
    command:
    - sleep
    - '3600'
    workingDir: /tmp
    resources:
      requests:
        cpu: 100m
        memory: 64Mi
      limits:
        cpu: 500m
        memory: 256Mi
    securityContext:
      runAsNonRoot: true
      runAsUser: 1000
      allowPrivilegeEscalation: false
      capabilities:
        drop:
        - ALL
      seccompProfile:
        type: RuntimeDefault
```

```bash
kubectl -n default wait --for=condition=Ready pod/iperf-server pod/iperf-client --timeout=120s
IPERF_SERVER_IP="$(kubectl -n default get pod iperf-server -o jsonpath='{.status.podIP}')"
test -n "$IPERF_SERVER_IP"
kubectl -n default exec iperf-client -- iperf3 -c "$IPERF_SERVER_IP" -t 10 -b 10M
```

El cliente duerme una hora y el comando limita la oferta a 10 Mbit/s durante diez segundos. Prueba la ruta, no el máximo rendimiento. Registre ubicación Pod/nodo/AZ, límites y política antes de interpretar. Use herramientas Windows para nodos Windows. Al terminar, retire solo los recursos de prueba creados.

Estos Pods independientes son para conectividad. Para comprobar políticas EKS nativas, use Pods de Deployment/Job y los requisitos documentados de puertos Service/contenedor.

## Buenas prácticas

### 1. Planificar direcciones IP

- Diseñar bloques CIDR suficientemente grandes
- Separar la red de Pods de la de Services
- Prever expansión futura en las subredes

### 2. Aplicar políticas de red

Cree primero el namespace aislado `networking-demo`. El ejemplo selecciona todos sus Pods y aísla entrada/salida bajo NetworkPolicy estándar; DNS y flujos necesarios requieren permisos explícitos. Se necesita un motor compatible. Las API de clúster/Admin pueden alterar la precedencia, y un manifiesto no es una arquitectura completa de confianza cero.

- Aplicar denegación por defecto (confianza cero)
- Permitir explícitamente solo tráfico necesario
- Aislar namespaces

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: networking-demo
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
```

### 3. Optimizar rendimiento

- Elegir el CNI adecuado para la carga
- Optimizar MTU
- Ajustar parámetros del kernel

### 4. Reforzar seguridad

- Elegir cifrado compatible y verificar el tráfico cubierto.
- Configurar identidad de carga/aplicación y mTLS donde proceda, separados de listas DNS/IP.
- Revisar periódicamente cambios de políticas, certificados y acceso.

### 5. Garantizar observabilidad

- Recopilar métricas de red
- Activar logs de flujo
- Implementar tracing distribuido

## Próximos pasos

1. [VPC CNI](01-vpc-cni.md) - CNI predeterminado de EKS
2. [Cilium en profundidad](cilium/README.md) - Redes eBPF
3. [Calico en profundidad](calico/README.md) - Rutas, políticas y dataplanes
4. [VPC Lattice](02-vpc-lattice.md) - Redes administradas AWS
5. [AWS Load Balancer Controller](03-aws-lb-controller.md) - Integración ELB
6. [Gateway API](04-gateway-api.md) - Entrada de nueva generación
7. [Conectividad VPC entre organizaciones](05-cross-org-vpc-connectivity.md) - VPC entre AWS Organizations, verificado en campo
8. [Benchmark de red de Pods](06-pod-network-benchmark.md) - Latencia y rendimiento medidos por límite nodo/AZ

---

## Referencias

- [Modelo de red de Kubernetes](https://kubernetes.io/docs/concepts/services-networking/)
- [Services de Kubernetes](https://kubernetes.io/docs/concepts/services-networking/service/)
- [Runtime de contenedores y CNI](https://kubernetes.io/docs/concepts/extend-kubernetes/compute-storage-net/network-plugins/)
- [Kubernetes NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Especificación CNI](https://raw.githubusercontent.com/containernetworking/cni/main/SPEC.md)
- [Ediciones de Calico](https://docs.tigera.io/calico/latest/about)
- [Niveles de políticas Calico](https://docs.tigera.io/calico/latest/network-policy/policy-tiers/tiered-policy)
- [Logs de flujo Calico Whisker](https://docs.tigera.io/calico/latest/observability/view-flow-logs)
- [Limitaciones Windows de Calico](https://docs.tigera.io/calico/latest/getting-started/kubernetes/windows-calico/limitations)
- [Redes y políticas Flannel 0.28.9](https://raw.githubusercontent.com/flannel-io/flannel/v0.28.9/README.md)
- [Backends de Flannel](https://raw.githubusercontent.com/flannel-io/flannel/v0.28.9/Documentation/backends.md)
- [Estado del repositorio Weave original](https://api.github.com/repos/weaveworks/weave)
- [AWS VPC CNI 1.23.0](https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.23.0/README.md)
- [Configuración de políticas EKS](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy-configure.html)
- [Políticas estándar y Admin de EKS](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html)
- [Delegación de prefijos y maxPods de EKS](https://docs.aws.amazon.com/eks/latest/userguide/cni-increase-ip-addresses-procedure.html)
- [Modelos de despliegue de políticas Admin y DNS de EKS](https://aws.amazon.com/blogs/containers/enhance-amazon-eks-network-security-posture-with-dns-and-admin-network-policies/)
- [Redes EKS Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/auto-networking.html)
- [Requisitos de complementos EKS](https://docs.aws.amazon.com/eks/latest/userguide/workloads-add-ons-available-eks.html)
- [Arquitectura del plano de control EKS](https://docs.aws.amazon.com/eks/latest/best-practices/control-plane.html)
- [Metadatos de imagen Netshoot v0.16](https://hub.docker.com/v2/repositories/nicolaka/netshoot/tags/v0.16)
- [Dockerfile Netshoot v0.16](https://raw.githubusercontent.com/nicolaka/netshoot/v0.16/Dockerfile)
- [Seguridad runtime de Tetragon](https://tetragon.io/docs/overview/)
- [Configuración NLB de AWS LBC 3.5](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/docs/guide/service/nlb.md)
- [Configuración Ingress de AWS LBC 3.5](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/docs/guide/ingress/annotations.md)
- [Conceptos de Gateway Load Balancer](https://docs.aws.amazon.com/vpc/latest/privatelink/gateway-load-balancers.html)
- [Encapsulación GENEVE (RFC 8926)](https://www.rfc-editor.org/rfc/rfc8926)
- [Resolver DNS de VPC](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-dns.html)
- [Endpoints y reglas Route 53 Resolver](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver.html)
- [Orden de evaluación de rutas VPC](https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Route_Tables.html)
- [Rutas locales y subredes más específicas](https://docs.aws.amazon.com/vpc/latest/userguide/subnet-route-tables.html)
- [Prioridad de rutas estáticas y propagadas](https://docs.aws.amazon.com/vpc/latest/userguide/route-tables-priority.html)
- [Direcciones y comportamiento AmazonProvidedDNS](https://docs.aws.amazon.com/vpc/latest/userguide/AmazonDNS-concepts.html)
- [Afinidad y failover GWLB](https://docs.aws.amazon.com/elasticloadbalancing/latest/gateway/edit-target-group-attributes.html)
- [IP virtuales Service y modos kube-proxy](https://kubernetes.io/docs/reference/networking/virtual-ips/)
- [Nombres Service CoreDNS y reenvío](https://kubernetes.io/docs/tasks/administer-cluster/dns-custom-nameservers/)
- [Endpoints de recursos PrivateLink](https://docs.aws.amazon.com/vpc/latest/privatelink/privatelink-access-resources.html)
- [Documentación Netfilter/iptables](https://www.netfilter.org/documentation/index.html)
- [EC2 Elastic Fabric Adapter](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/efa.html)
- [Protocolo QUIC (RFC 9000)](https://www.rfc-editor.org/rfc/rfc9000)
- [HTTP/3 (RFC 9114)](https://www.rfc-editor.org/rfc/rfc9114)
- [gRPC sobre HTTP/2 y balanceo](https://grpc.io/blog/grpc-load-balancing/)
- [Gateway API GRPCRoute](https://gateway-api.sigs.k8s.io/guides/user-guides/grpc-routing/)
