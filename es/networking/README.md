# Redes en Kubernetes

> **Última actualización**: September 14, 2026. Las referencias a funcionalidades incluyen Cilium 1.20.1, Calico Open Source 3.32, Flannel 0.28.9 y AWS VPC CNI 1.23.0. Consulte la matriz de Kubernetes/plataforma de cada producto antes de instalarlo; no constituyen una configuración de clúster probada de forma conjunta.

## Descripción general

Las redes en Kubernetes son la capa de infraestructura central que permite la comunicación entre aplicaciones en contenedores. Esta sección abarca todo, desde los conceptos básicos de redes en Kubernetes hasta soluciones CNI (Container Network Interface) avanzadas y patrones de red en entornos de AWS EKS.

## Ruta de aprendizaje {#learning-path}

Avance desde los conceptos de protocolos hasta las observaciones, y conéctelos después con las responsabilidades del contenedor, del clúster y de la nube. Use los prerrequisitos para elegir un punto de entrada y los resultados para comprobar su comprensión antes de continuar.

| Etapa | Rol | Prerrequisitos | Resultado | Lectura / práctica |
|---|---|---|---|---|
| Protocolos, direccionamiento, HTTP | Establecer el vocabulario | Uso básico de la línea de comandos | Trazar una petición y distinguir el direccionamiento, el transporte y el comportamiento de la aplicación | Fundamentos de redes [Parte 1](../basics/06-network-fundamentals-part1.md), [Parte 2](../basics/06-network-fundamentals-part2.md), [Parte 3](../basics/06-network-fundamentals-part3.md), [Parte 4](../basics/06-network-fundamentals-part4.md) |
| Sockets de Linux, VFS, rutas de paquetes | Conectar las API con el kernel | Fundamentos de TCP/IP | Distinguir FD, búferes de socket, ventanas y colas | [Pila de red del kernel](../kernel/02-network-stack.md) |
| Diagnóstico de red en Linux | Comprobar hipótesis con evidencia | Conceptos de sockets y rutas de paquetes | Correlacionar observaciones de socket, paquete y aplicación | [Práctica de diagnóstico](07-linux-network-diagnostics.md) · [Cuestionario](../quizzes/networking/07-linux-network-diagnostics-quiz.md) |
| Redes en Docker y contenedores | Localizar los límites de los namespaces | Rutas de paquetes en Linux y diagnóstico básico | Explicar las redes bridge, los puertos publicados y la resolución de nombres de contenedores | [Tecnología de contenedores](../basics/03-container-technology.md) |
| Service, DNS e Ingress de Kubernetes | Situar las abstracciones del clúster | Redes de contenedores | Trazar un nombre a través de un Service hasta sus endpoints e identificar el rol del ingress | [Services y redes](../core/03-services-networking.md) · [Laboratorio](../labs/core/03-services-networking-lab.md) |
| eBPF, CNI, políticas | Comparar responsabilidades de implementación | Rutas de Pod y de Service | Distinguir el reenvío de paquetes, la aplicación de políticas y la observabilidad | [Fundamentos de eBPF](../basics/05-ebpf-fundamentals.md) · [Cilium](cilium/README.md) · [Calico](calico/README.md) |
| Límites de red y rendimiento en AWS | Aplicar el modelo a las rutas de la nube | Conceptos de CNI y habilidades de medición | Identificar los límites de VPC, nodo y AZ e interpretar las mediciones en su contexto | [VPC CNI](01-vpc-cni.md) · [AWS Load Balancer Controller](03-aws-lb-controller.md) · [Conectividad de VPC entre organizaciones](05-cross-org-vpc-connectivity.md) · [Benchmark de red de Pods](06-pod-network-benchmark.md) |

## Modelo de red de Kubernetes

El modelo actual de Kubernetes ofrece una red de Pods en la que estos pueden comunicarse directamente entre nodos sin traducción de direcciones ni proxies, **sujeto a una segmentación de red intencionada**. Los agentes del nodo, como kubelet, deben poder alcanzar los Pods de su propio nodo. Las políticas de red, el enrutamiento y los listeners de la aplicación siguen determinando si una conexión concreta tiene éxito.

Los Pods ordinarios tienen su propio network namespace (espacio de nombres de red) y direcciones válidas en todo el clúster; los contenedores de un mismo Pod comparten ese namespace y localhost. Los Pods con red de host comparten la red del nodo, y las configuraciones de doble pila o multired requieren un manejo de direcciones más preciso. Recrear un Pod puede asignarle una IP distinta; reiniciar un contenedor dentro del mismo Pod no necesariamente recrea su sandbox de red.

| Componente | Rol |
|---|---|
| Red de Pods | Direccionamiento y conectividad entre los network namespaces de las cargas de trabajo |
| Service/descubrimiento | Nombres de servicio o direcciones virtuales estables sobre endpoints cambiantes |
| Implementación de Ingress/Gateway | Punto de entrada externo configurado y enrutamiento de aplicaciones |
| Motor de políticas de red | Aplica las políticas que admite la implementación seleccionada |

Estos roles no forman una ruta de paquetes secuencial obligatoria. La traducción de Service, un proxy L7 y las políticas de la carga de trabajo pueden cambiar la forma en que una petición concreta atraviesa la red.

### Redes de Pods

Las redes de Pods proporcionan el direccionamiento y las rutas para la comunicación entre Pods. La ilustración siguiente muestra Pods IPv4 ordinarios; sus conexiones asumen que las políticas y controles de red aplicables las permiten.

![Rutas IPv4 directas ilustrativas entre Pods de dos nodos, con una conectividad sujeta a las políticas y el enrutamiento configurados.](../.gitbook/assets/en-networking-readme-1.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-1.html)

Las direcciones son direcciones ilustrativas de Pods ordinarios. El aislamiento intencionado y las configuraciones de red de host o multired requieren su propia interpretación.

#### Métodos de implementación de redes de Pods

| Método | Descripción | CNI de ejemplo |
|--------|-------------|-------------|
| **Red overlay** | Encapsula el tráfico sobre la red existente | Flannel VXLAN, Calico VXLAN/IPIP, Cilium VXLAN/Geneve |
| **Enrutamiento nativo** | Usa rutas de la red subyacente sin esa encapsulación overlay | AWS VPC CNI, enrutamiento/BGP de Calico, enrutamiento nativo de Cilium |
| **Encapsulación condicional** | Usa rutas directas o encapsulación según la topología configurada | Modos admitidos de Calico/Flannel/Cilium, con prerrequisitos distintos |

### Redes de Service

Los Services describen un conjunto lógico de endpoints, normalmente Pods, y cómo alcanzarlos. ClusterIP proporciona por defecto una IP virtual estable; los Services headless omiten esa IP virtual, y ExternalName usa una asignación DNS CNAME. Un Service también puede tener endpoints gestionados sin un selector de Pods.

![Mecanismos de entrada típicos para Services ClusterIP, NodePort, LoadBalancer y ExternalName; la asignación DNS se distingue del reenvío de paquetes.](../.gitbook/assets/en-networking-readme-2.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-2.html)

Estos son mecanismos de exposición típicos, no garantías de seguridad. El rango de NodePort y las direcciones de nodo accesibles son configurables; los LoadBalancer pueden ser internos. ExternalName devuelve un alias DNS y no crea un proxy de reenvío.

#### Características de los tipos de Service

Cree Pods con la etiqueta `app: my-app` en `default`, escuchando en los puertos de destino indicados. El rango de asignación por defecto de NodePort es 30000–32767 y se puede configurar. La accesibilidad externa sigue dependiendo de las direcciones, las rutas y los controles de acceso.

El ejemplo de LoadBalancer selecciona explícitamente **AWS Load Balancer Controller**, con destinos de instancia EC2 y NodePorts asignados. Instale y configure primero ese controlador y sus prerrequisitos de IAM/subredes. EKS Auto Mode usa un controlador/clase diferente. Aquí el puerto 443 solo selecciona un puerto TCP; el backend debe servir TLS en 8443 o bien configurarse por separado en el balanceador de carga.

Estas asignaciones de puertos ilustran la API de Service general de Kubernetes. AWS documenta actualmente requisitos adicionales para las políticas de red nativas de EKS: el puerto del Service debe coincidir con el puerto del contenedor, y los Pods gestionados por un controlador con `metadata.ownerReferences` ofrecen una aplicación fiable. Adapte los ejemplos a esos requisitos antes de probar esa implementación de políticas.

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

### Redes de Ingress

Un recurso Ingress necesita un controlador y su plano de datos. Este ejemplo HTTP usa AWS LBC con `spec.ingressClassName: alb` y destinos IP. Los Services `api-v1`, `api-v2` y `web-frontend` referenciados deben existir en `default`, exponer el puerto 80 y tener endpoints de Pod listos y enrutables dentro de la VPC. Configure HTTPS/certificados por separado cuando sea necesario. Consulte la [guía de LBC](03-aws-lb-controller.md) para su instalación y los prerrequisitos de destinos.

Ingress define reglas para enrutar tráfico HTTP/HTTPS a Services internos del clúster.

![Enrutamiento lógico de Ingress por host/ruta hacia Services de backend y Pods.](../.gitbook/assets/en-networking-readme-3.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-3.html)

El recuadro representa la función del plano de datos de Ingress. AWS LBC programa el ALB; el tráfico de la aplicación no atraviesa el proceso de reconciliación del controlador. Según el modo de destino, el plano de datos puede alcanzar IP de Pod o NodePorts en lugar de atravesar la IP virtual de un Service como un salto adicional literal.

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

CNI estandariza la interfaz mediante la cual un runtime configura la red de un contenedor. En el Kubernetes actual, kubelet solicita operaciones de sandbox de Pod a través de CRI y **el runtime de contenedores gestiona CNI**. Los antiguos flags de kubelet para gestionar CNI directamente se eliminaron en Kubernetes 1.24.

### Responsabilidades del runtime y del plugin

| Actor | Responsabilidad |
|---|---|
| kubelet | Solicita la creación/eliminación del sandbox a través de la interfaz del runtime de contenedores |
| Runtime de contenedores | Selecciona la configuración de red e invoca la cadena de plugins CNI |
| Plugin CNI | Recibe la configuración, ejecuta ADD/DEL y otras operaciones admitidas, y devuelve resultados |
| Implementación de IPAM | Asigna/libera direcciones; puede ser un plugin delegado o parte de un agente específico del proveedor |
| Agente de nodo opcional | Mantiene rutas, políticas, pools de IP o estado del datapath específicos del proveedor |

El runtime pasa la configuración al plugin a través de la interfaz CNI; no es obligatorio que todos los plugins tengan un agente de larga duración o un binario de IPAM independiente. Los tipos de interfaz también varían: los pares veth son habituales, pero no son la única implementación.

## Comparación de CNI

| Proyecto / alcance | Redes y políticas | Funcionalidades y límites a distinguir |
|---|---|---|
| **Cilium 1.20.1** | Redes con eBPF; Envoy para las funciones L7 correspondientes; políticas de red de Cilium y Hubble | Dataplane de workers Linux, con requisitos AMD64/Arm64. La disponibilidad de la CLI para Windows no equivale a soporte de CNI en Windows. WireGuard/IPsec y el mTLS ztunnel en Beta tienen alcances distintos. |
| **Calico Open Source 3.32** | Opciones de enrutamiento/encapsulación; opciones de iptables, nftables y eBPF; niveles de política ordenados y políticas de host/carga de trabajo | Windows tiene límites propios, incluida la ausencia de dataplane eBPF de Linux o WireGuard. La observabilidad de flujos Whisker/Goldmane está disponible como Tech Preview. Consulte la matriz de ediciones para las capacidades de pago. |
| **Flannel 0.28.9** | Asignación de subredes por host y transporte entre nodos; VXLAN, host-gw y otros backends | `flanneld` por sí mismo no aplica NetworkPolicy; el `netpol.enabled` opcional del chart despliega un controlador de políticas de los SIG. WireGuard es un backend documentado; IPsec es experimental. VXLAN en Windows tiene ajustes y límites específicos. |
| **AWS VPC CNI 1.23.0 / EKS** | Asignación de direcciones de VPC y ENI/prefijos de EC2; capacidades de políticas de red estándar y Admin de EKS en nodos EC2 Linux admitidos | EKS Auto Mode es una implementación de red gestionada con capacidades adicionales de políticas de DNS. Windows, Fargate, las redes personalizadas, la delegación de prefijos y el soporte multi-NIC tienen condiciones aparte. |
| **Proyecto original Weave Net** | Implementación histórica de redes overlay | El repositorio original `weaveworks/weave` está archivado. No lo describa como una opción activa y con soporte por defecto para un clúster nuevo. |

### Políticas, cifrado y observabilidad

- Cilium ofrece políticas conscientes de HTTP/DNS mediante los componentes L7 aplicables, además de políticas a nivel de clúster y de host. Su semántica de deny/allow no es la API de Tier ordenados de Calico.
- Calico Open Source incluye niveles jerárquicos de política y políticas de host. La matriz de producto actual asigna las políticas de capa de aplicación, las políticas de DNS/FQDN y Cluster Mesh a Cloud/Enterprise; no deben atribuirse tácitamente a la edición open source. El cifrado en tránsito documentado por Calico usa WireGuard.
- Amazon EKS proporciona controles Admin/Baseline de `ClusterNetworkPolicy` para Auto Mode y para instalaciones EC2/VPC-CNI admitidas. La funcionalidad `ApplicationNetworkPolicy` de DNS/FQDN descrita por AWS es para **Auto Mode**. Su nombre no implica que hoy inspeccione el método o el cuerpo HTTP.
- El controlador de políticas opcional de Flannel tiene sus propios requisitos; elegir únicamente un backend de red no habilita la aplicación de políticas.
- El cifrado entre nodos, la identidad autenticada de la carga de trabajo y el mTLS de aplicación son controles diferentes. La visibilidad de flujos de red también difiere del trazado de aplicaciones o de la aplicación de políticas de procesos/archivos.

### Enrutamiento y rendimiento

Calico y Cilium pueden anunciar rutas mediante BGP; eso por sí solo no proporciona descubrimiento de servicios multiclúster, sincronización de políticas ni cifrado. Flannel host-gw usa rutas directas y requiere conectividad de capa 2 adecuada. Un overlay añade encapsulación y consideraciones de MTU, pero no puede inferirse una clasificación universal de rendimiento a partir del nombre del CNI.

La antigua cifra de rendimiento del 100/98/95/85/80/75 por ciento no tenía carga de trabajo, versiones ni fuente de medición reproducibles. Use hardware, kernel, tamaños de paquete/petición, concurrencia y ajustes de cifrado/políticas comparables, junto con el rendimiento, la pérdida y la latencia de cola. El [benchmark de Pods](06-pod-network-benchmark.md) aparte conserva su propio entorno y mediciones históricos.

## Guía de selección de CNI

Defina primero el enrutamiento, las políticas, el sistema operativo y el modelo de soporte requeridos, y luego pruebe esa combinación.

| Necesidad | Ruta de evaluación |
|---|---|
| Direccionamiento de VPC estándar de EKS y políticas de red admitidas | Evalúe las capacidades de AWS VPC CNI/EKS antes de añadir un segundo motor de políticas. |
| Niveles de política ordenados, políticas de host o BGP de infraestructura | Evalúe la edición/dataplane de Calico correspondiente y los prerrequisitos de enrutamiento. |
| Políticas de Cilium, Hubble o determinadas funciones de mesh | Compruebe la compatibilidad de Linux/kernel/plataforma y la [guía de mesh de Cilium](../service-mesh/cilium-service-mesh/README.md). Envoy sigue formando parte de las rutas L7 aplicables. |
| Una red pequeña con un conjunto de funciones limitado | Evalúe el backend de Flannel y su controlador de políticas opcional frente a los requisitos reales. |
| Aplicación de políticas de procesos, llamadas de sistema o archivos | Evalúe un componente de seguridad en tiempo de ejecución como Tetragon de forma independiente de las políticas de red. |

### Configuración del add-on gestionado de EKS

Lo siguiente es un ejemplo de **payload de configuración**, no una instrucción para instalar a la vez Calico y el motor de políticas de VPC CNI sobre las mismas cargas de trabajo:

```json
{
  "enableNetworkPolicy": "true"
}
```

La cadena `"true"` es el tipo documentado para este ajuste. Seleccione una compilación del add-on de EKS compatible con la versión de Kubernetes existente e inspeccione el esquema de configuración de esa compilación:

```bash
EKS_REGION=ap-northeast-2
KUBERNETES_MINOR=1.35  # Replace with the existing cluster's minor version
aws eks describe-addon-versions --region "$EKS_REGION" --addon-name vpc-cni \
  --kubernetes-version "$KUBERNETES_MINOR"
: "${VPC_CNI_ADDON_VERSION:?Set the compatible eksbuild version selected from metadata}"
aws eks describe-addon-configuration --region "$EKS_REGION" --addon-name vpc-cni \
  --addon-version "$VPC_CNI_ADDON_VERSION"
```

El número de release 1.23.0 del proyecto upstream y una versión `eksbuild` de EKS son identificadores diferentes. Combine los cambios con la configuración prevista del add-on gestionado; no seleccione `latest` a ciegas ni reemplace valores no relacionados. Migrar desde una implementación de políticas de terceros también requiere eliminar su estado de aplicación existente y un plan de transición de nodos/cargas de trabajo probado.

## Fundamentos de redes en EKS

### Arquitectura de red por defecto de EKS

| Ubicación / componente | Responsabilidad |
|---|---|
| VPC gestionada por EKS | AWS ejecuta el plano de control gestionado de Kubernetes distribuido entre zonas de disponibilidad. |
| VPC del clúster del cliente | Las redes de los workers, las subredes seleccionadas y las ENI entre cuentas gestionadas por EKS proporcionan las rutas configuradas hacia el plano de control. |
| ALB/NLB en las subredes seleccionadas de la VPC del cliente | Proporciona el punto de entrada de aplicación público o interno elegido; una internet gateway o NAT gateway no sustituye a esa configuración de enrutamiento. |
| NAT gateway o endpoints de servicio privados | Proporciona las rutas de salida concretas que requiere el diseño de la carga de trabajo. |

La figura anterior situaba el plano de control dentro de la VPC del cliente y los balanceadores de carga fuera de ella; se ha sustituido por estos límites de propiedad.

### DNS y redes según el modo de cómputo

| Modo de cómputo | Ubicación de DNS / componentes |
|---|---|
| Nodos EC2 estándar | Normalmente usan el Deployment de CoreDNS configurado y los componentes de red instalados; los reemplazos necesitan su propia configuración admitida. |
| EKS Auto Mode puro | Las funciones de CoreDNS, VPC CNI y kube-proxy se ejecutan como servicios systemd gestionados del nodo. Para estos nodos no es necesario un Deployment/add-on de CoreDNS. |
| Auto Mode mezclado con nodos no Auto | Conserve el Deployment de CoreDNS para los nodos no Auto; no pueden usar el servicio DNS de Auto Mode de otro nodo. |

El primer resolutor DNS de Auto Mode es local al nodo. El reenvío upstream y la comunicación con el plano de control pueden seguir requiriendo acceso de red; esto no garantiza que todos los paquetes relacionados con DNS permanezcan en el nodo. AWS documenta políticas tanto Admin como de DNS para Auto Mode, mientras que las políticas Admin de VPC-CNI en EC2 estándar tienen sus propios requisitos de versión y habilitación.

### Cómo funciona VPC CNI

AWS VPC CNI asigna a los Pods ordinarios direcciones enrutables en la VPC usando el modo de IPAM seleccionado. Las direcciones IPv4 secundarias, los prefijos delegados, las branch ENI y las configuraciones multi-NIC son diferentes entre sí; los Pods con red de host comparten la red del nodo.

![Asignación ilustrativa de IPv4 secundarias desde ENI de EC2 hacia los Pods, incluida una interfaz warm opcional.](../.gitbook/assets/en-networking-readme-9.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-9.html)

Esto representa únicamente el modo de IP secundarias. Una ENI warm es una estrategia de asignación configurable, no un requisito de que cada nodo reserve siempre exactamente una. La delegación de prefijos, las redes personalizadas y las branch ENI tienen reglas de asignación distintas.

#### Límites de ENI e IP

| Tipo de instancia | ENI máximas | Slots IPv4 por ENI | Valor histórico de arranque con IP secundarias |
|---------------|----------|--------------|------------------------|
| t3.medium | 3 | 6 | 17 |
| t3.large | 3 | 12 | 35 |
| m5.large | 3 | 10 | 29 |
| m5.xlarge | 4 | 15 | 58 |
| m5.2xlarge | 4 | 15 | 58 |
| c5.4xlarge | 8 | 30 | 234 |

Estos valores se verificaron contra los límites por instancia de VPC CNI 1.23.0 y la tabla histórica de max-Pods. El cálculo histórico es `ENIs × (IPv4 slots per ENI − 1) + 2`; no es una recomendación universal actual. La delegación de prefijos, las redes personalizadas, las branch ENI y varias tarjetas de red cambian la capacidad de direccionamiento. La planificación de Kubernetes también está limitada por `maxPods` de kubelet y por los recursos. Los managed node groups de EKS limitan `maxPods` a 110 en instancias con menos de 30 vCPU y a 250 en el resto; el número de IP disponibles por sí solo no anula ese límite.

### Consideraciones de red en EKS

#### Gestión de direcciones IP

Para **VPC CNI en Linux**, configure las variables de entorno documentadas mediante el mecanismo de gestión de add-on/Helm/DaemonSet elegido. Lo siguiente es un fragmento de configuración de add-on de EKS. El antiguo ConfigMap `amazon-vpc-cni` con `enable-prefix-delegation` no configura IPAMD de Linux de esta forma. Conserve los demás valores previstos del add-on al aplicar un cambio.

```json
{
  "env": {
    "ENABLE_PREFIX_DELEGATION": "true",
    "WARM_PREFIX_TARGET": "1"
  }
}
```

Como alternativa, ajuste el mínimo total de asignación y el objetivo de IP libres. Cuando se configura `MINIMUM_IP_TARGET` o `WARM_IP_TARGET`, este tiene precedencia sobre `WARM_PREFIX_TARGET`; son políticas alternativas y no cuatro objetivos independientes que se sumen. La asignación sigue produciéndose en unidades del tamaño del prefijo. El soporte de Nitro, un espacio `/28` contiguo para IPv4 y un límite de Pods de kubelet adecuado son prerrequisitos aparte.

La asignación de prefijos en Windows es una ruta de configuración diferente: AWS documenta `enable-windows-prefix-delegation` y sus claves de warm target en el ConfigMap `amazon-vpc-cni`. No copie sin cambios a Windows el procedimiento de variables de entorno de Linux.

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

Estos ejemplos IPv4 requieren identificadores reales de subred y grupo de seguridad en la AZ y la VPC previstas. Habilite las redes personalizadas y seleccione el ENIConfig de cada nodo mediante su etiqueta de zona. Una anotación explícita de ENIConfig en el nodo tiene precedencia sobre esa etiqueta. Los nombres de ejemplo siguientes usan la misma región en ambos idiomas; sustitúyalos por las zonas reales de los nodos. Instalar únicamente objetos ENIConfig no activa las redes personalizadas.

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

Los elementos siguientes se mencionan de pasada en otros puntos de esta descripción general. Los procedimientos de configuración completos y las cifras medidas están en las páginas de análisis detallado enlazadas; esta sección organiza en qué se diferencian estas piezas según la capa y dónde encaja cada una.

### L2–L7 y la diferencia entre routers y balanceadores de carga

«Router» y «balanceador de carga» aparecen a menudo en la misma frase, pero responden a preguntas distintas. Un router elige (en general) una ruta hacia un único destino; un balanceador de carga elige un destino entre varios candidatos equivalentes usando un algoritmo de distribución.

| Capa | Dispositivo/función | Base de la decisión | Correspondencia en Kubernetes/AWS |
|---|---|---|---|
| L2 (enlace) | Switch, bridge | Dirección MAC de destino | Pares veth y bridges de Linux creados por el CNI, la NIC virtual que expone una ENI |
| L3 (red) | Router o inserción de appliance transparente | IP de destino para el enrutamiento; identidad del flujo para la selección del appliance | El router implícito de la VPC, TGW; GWLB encapsula paquetes IP para los appliances |
| L4 (transporte) | Balanceador de carga L4 | Identidad de conexión/flujo, habitualmente la 5-tupla | NLB; kube-proxy (iptables, IPVS, nftables); implementaciones eBPF de Service aparte |
| L7 (aplicación) | Balanceador de carga L7/proxy inverso | Host, ruta y cabeceras por petición; consciente del protocolo | ALB, implementaciones de Ingress/Gateway API, sidecars de service mesh (Envoy) |

La diferencia clave es la **unidad de distribución**. Un balanceador de carga L4 normalmente selecciona un destino para una conexión TCP o un flujo UDP rastreado. Un proxy L7 puede seleccionar un destino para cada petición de aplicación admitida, incluidas peticiones que comparten una conexión. GWLB distribuye flujos IP encapsulados entre appliances de seguridad en lugar de analizar peticiones de aplicación. La adherencia de flujo depende del tiempo de espera, la salud y el comportamiento de failover configurados; no garantiza que un flujo nunca pueda reasignarse o interrumpirse.

> 📎 Las definiciones a nivel de protocolo de los conceptos L2/L3 están en [Fundamentos de redes Parte 1](../basics/06-network-fundamentals-part1.md); los tipos de destino de ALB/NLB y la configuración real están en [AWS Load Balancer Controller](03-aws-lb-controller.md).

### Conectividad entre cuentas/VPC: TGW, VPC Peering, GWLB, PrivateLink, Lattice

Estas cinco opciones de conectividad difieren en la capa y el modelo de tráfico. La latencia medida en TGW compartido con RAM, VPC Peering, PrivateLink, TGW Peering y VPC Lattice está en [Conectividad de VPC entre organizaciones](05-cross-org-vpc-connectivity.md). Esta sección añade GWLB, que no aparece en esa tabla comparativa, y reencuadra las cinco opciones por capa.

| Conectividad | Capa/modelo | Características |
|---|---|---|
| VPC Peering | L3, enrutamiento IP bidireccional | No es transitivo; no se puede configurar entre CIDR solapados |
| Transit Gateway (TGW) | L3, enrutamiento IP en hub-and-spoke | Usa asociaciones de attachment y propagación en una o más tablas de rutas de TGW; se comparte entre cuentas mediante RAM |
| Gateway Load Balancer (GWLB) | L3, inserción de appliance transparente | Encapsula el paquete original en GENEVE (UDP 6081); un modelo de servicio de endpoint de VPC conecta el tráfico del consumidor con la flota de appliances del proveedor |
| PrivateLink | Conectividad mediante endpoint privado | Un servicio de endpoint respaldado por NLB es un modelo; también existen los resource endpoints. Los CIDR de consumidor y proveedor pueden solaparse |
| VPC Lattice | Redes de aplicaciones y de recursos | Los servicios HTTP/HTTPS admiten enrutamiento L7 y autorización IAM opcional; el passthrough de TLS y las configuraciones de recursos tienen capacidades distintas |

GWLB inserta appliances de inspección, como firewalls e IDS/IPS, en una ruta IP a través de un endpoint de Gateway Load Balancer. Su adherencia de flujo por defecto usa cinco campos; las configuraciones admitidas pueden usar en su lugar dos o tres. Valide las rutas de ida y de retorno, la salud de los appliances, la MTU de la encapsulación, las NACL y los grupos de seguridad de las cargas de trabajo/appliances reales. GWLB en sí no tiene un grupo de seguridad al estilo de ALB, y la adherencia de flujo no sustituye a las pruebas de fallos.

> 📎 La integración completa de EKS/VPC Lattice (Gateway API Controller, autorización IAM, enrutamiento) está en [VPC Lattice](02-vpc-lattice.md).

### Cómo se comportan realmente el resolutor DNS y las tablas de rutas

**Resolutor DNS:** AmazonProvidedDNS **es Route 53 Resolver**. Sus direcciones incluyen la dirección de red IPv4 principal de la VPC más dos (`10.0.0.2` para `10.0.0.0/16`) y `169.254.169.253`; resuelve las zonas privadas asociadas y los nombres públicos según las reglas de Resolver. CoreDNS sirve normalmente el dominio de clúster de Kubernetes configurado, a menudo `cluster.local`; `kube-dns` es el nombre de su Service, no un namespace ni una zona DNS. El reenvío externo sigue el Corefile y el fichero de resolución visible para el Pod de DNS. Inspeccione esos ajustes en lugar de asumir que el fichero de resolución del nodo se usa sin cambios. En un diseño con endpoints de Resolver, los endpoints entrantes aceptan consultas on-premises, mientras que los endpoints salientes y sus reglas asociadas reenvían determinadas consultas de la VPC al DNS on-premises. El resolutor local al nodo de Auto Mode no elimina las dependencias upstream.

**Tablas de rutas:** la evaluación de rutas de la VPC usa en general la coincidencia del prefijo más largo. AWS permite reemplazar el destino de una ruta `local` y añadir rutas de subred más específicas admitidas para el enrutamiento hacia appliances; `local` no es incondicionalmente la ruta más específica. Para destinos idénticos, las rutas estáticas de la VPC tienen precedencia sobre las rutas propagadas desde una virtual private gateway. Una ruta de VPC que apunta a un TGW es estática; la propagación dentro de un TGW corresponde a sus tablas de rutas independientes. Los destinos no válidos pueden dejar entradas `blackhole` que descartan el tráfico, así que inspeccione también el estado de la ruta, no solo el destino. Una subred sin asociación explícita a una tabla de rutas usa la tabla de rutas principal de la VPC.

> 📎 La prioridad de rutas de TGW/Peering y ejemplos de configuración de rutas estáticas están en los [hallazgos operativos de Conectividad de VPC entre organizaciones](05-cross-org-vpc-connectivity.md#operational-findings).

### El plano de datos del kernel: iptables, IPVS, eBPF y filtrado de paquetes

El reenvío de Services en Linux y la aplicación de políticas de red pueden usar mecanismos diferentes. Netfilter proporciona los hooks de la ruta de paquetes que usan iptables y nftables. Las implementaciones eBPF pueden engancharse en XDP, tc o hooks de socket y realizar allí la selección de Service. Esto no significa que en un clúster con eBPF todos los paquetes eludan Netfilter o el seguimiento de conexiones; la ruta depende del CNI, el kernel, el enrutamiento y la configuración de funcionalidades.

| Implementación | Dónde se sitúa | Características |
|---|---|---|
| iptables | Cadenas de reglas secuenciales en los hooks de netfilter | El tiempo de evaluación escala con el número de reglas (O(n)); modo por defecto histórico de kube-proxy |
| IPVS | Balanceador de carga L4 nativo del kernel, una extensión de netfilter | Búsqueda basada en hash (cercana a O(1)); en desuso como modo de kube-proxy a partir de Kubernetes 1.35 |
| nftables | Framework sucesor de iptables en netfilter | Modo estable de kube-proxy desde 1.33; compruebe antes la compatibilidad de kernel/CNI |
| eBPF (p. ej., Cilium) | Hooks configurados de XDP, tc y socket | Puede reemplazar el manejo de Services de kube-proxy; es una implementación aparte, con comportamiento de Netfilter/conntrack específico de cada ruta |

Cambiar de implementación puede dejar atrás reglas del kernel y conexiones activas. Siga el procedimiento de migración de la distribución/CNI, drene las cargas de trabajo cuando sea necesario y prevea reinicios de nodos allí donde la limpieza los requiera. Reemplazar kube-proxy por un CNI basado en eBPF también requiere un orden de conmutación admitido para que las implementaciones no compitan por el mismo tráfico de Service.

> 📎 El calendario de desuso de IPVS y la transición estable a nftables se tratan en [Introducción a Kubernetes](../basics/04-kubernetes-introduction.md); el reemplazo de kube-proxy con eBPF de Cilium está en [Cilium eBPF](cilium/02-ebpf.md); el plano de datos eBPF de Calico y su procedimiento de migración están en [Calico eBPF](calico/06-ebpf-dataplane.md).

### Redes para cómputo intensivo: ENI, EFA, NVLink y transceptores ópticos

ENI, EFA y NVLink sirven a rutas diferentes. Una **ENI** es una interfaz de red virtual adjunta a una instancia EC2 en una única zona de disponibilidad; su tráfico IP normal puede alcanzar otras AZ y VPC conectadas cuando el enrutamiento y las políticas lo permiten (véase [VPC CNI](01-vpc-cni.md)). **EFA** proporciona un dispositivo de OS-bypass que se usa a través de libfabric desde software MPI/NCCL compatible. **El tráfico del dispositivo EFA no es enrutable y no puede cruzar los límites de VPC/AZ**; el tráfico IP normal a través del dispositivo ENA de una interfaz EFA-con-ENA sigue siendo enrutable. Las interfaces solo EFA no tienen dispositivo ENA ni direccionamiento IP. **NVLink** conecta GPU dentro de sistemas compatibles, incluidos los dominios NVLink a escala de rack admitidos. Mida el hardware, las operaciones colectivas y la ubicación seleccionados en lugar de asumir una mejora fija frente a EFA.

Los **transceptores ópticos** son un concepto general de redes de centro de datos. Los cables de cobre DAC (Direct Attach Copper) son adecuados para tiradas cortas; los módulos ópticos y la fibra cubren otros requisitos de alcance y ancho de banda. QSFP y OSFP describen factores de forma de módulo, no una garantía de medio óptico. Tómelo como contexto general: no determina el cableado físico de una carga de trabajo concreta de AWS.

> 📎 La planificación consciente de la topología NVLink/IMEX y ejemplos de ubicación de Pods con GPU están en [Infraestructura de IA/ML](../ai-ml/06-ai-infrastructure.md); la restricción de límites de VPC/AZ de EFA y sus mediciones están en [Conectividad de VPC entre organizaciones](05-cross-org-vpc-connectivity.md).

### Qué implican los protocolos de nueva generación para Kubernetes: HTTP/3, gRPC, QUIC

Los mecanismos de protocolo de HTTP/3 (RFC 9114) y de su transporte QUIC (RFC 9000) se tratan en [Fundamentos de redes Parte 2](../basics/06-network-fundamentals-part2.md) y [Parte 3](../basics/06-network-fundamentals-part3.md). Aquí cubrimos solo lo que afecta realmente a la distribución de tráfico en Kubernetes.

- **gRPC y los balanceadores de carga L4:** gRPC multiplexa peticiones sobre conexiones HTTP/2. Un balanceador L4 normalmente mantiene una conexión TCP establecida en el endpoint que seleccionó; si ese endpoint es un proxy, puede tomar decisiones de enrutamiento adicionales. Añadir Pods por sí solo no redistribuye las conexiones existentes. La distribución por RPC requiere un proxy L7 compatible o una política del lado del cliente. Un RPC en streaming sigue siendo una sola llamada; sus mensajes individuales no se balancean de forma independiente.
- **GRPCRoute de Gateway API:** Ingress no tiene un recurso específico para gRPC, pero Gateway API estandariza el enrutamiento a nivel de servicio/método con `GRPCRoute`. El soporte varía según la implementación (cuántas coincidencias de cabecera, políticas de reintento, etc.), así que consulte la documentación propia del controlador.
- **Hasta dónde llegan realmente HTTP/3 y QUIC dentro del clúster:** el soporte de HTTP/3 entre un cliente y el borde (una CDN, un balanceador de carga) es una cuestión distinta del soporte de HTTP/3 dentro del clúster o en la conexión de backend de un Ingress. Muchas implementaciones de Ingress/Gateway siguen hablando HTTP/1.1 o HTTP/2 con el backend, y el soporte de HTTP/3 de extremo a extremo varía según la implementación y la versión: no generalice; consulte la documentación del controlador que realmente se está usando.

## Subpáginas de redes

Esta sección cubre en detalle los siguientes temas:

### [Práctica de diagnóstico de red en Linux](07-linux-network-diagnostics.md) {#linux-network-diagnostics}

Conecte los [conceptos de sockets y rutas de paquetes del kernel](../kernel/02-network-stack.md) con las observaciones antes de estudiar las implementaciones de CNI. Use el [cuestionario de diagnóstico](../quizzes/networking/07-linux-network-diagnostics-quiz.md) para comprobar su interpretación.

### [VPC CNI](01-vpc-cni.md)
Redes de EKS con direcciones de VPC para Pods ordinarios y prerrequisitos de IPAM/políticas específicos de cada modo.

### [Análisis detallado de Cilium](cilium/README.md)
Solución CNI de alto rendimiento basada en eBPF. Proporciona funciones avanzadas como Network Policy L7, Service Mesh y observabilidad (Hubble).

### [Análisis detallado de Calico](calico/README.md)
Uno de los CNI más utilizados. Network Policy potente, soporte de BGP y funciones empresariales. Cubre la introducción, la arquitectura, los modos de red, un análisis detallado de BGP, Network Policy, eBPF, temas avanzados, la integración con EKS y la guía de operaciones.

### [VPC Lattice](02-vpc-lattice.md)
Servicio gestionado de redes de aplicaciones de AWS. Comunicación entre servicios a través de VPC y de cuentas.

### [AWS Load Balancer Controller](03-aws-lb-controller.md)
Integra los Services e Ingress de Kubernetes con AWS ELB (ALB/NLB).

### [Gateway API](04-gateway-api.md)
API de ingress de nueva generación para Kubernetes. Modelo de recursos estandarizado y configuración basada en roles.

### [Benchmark de red de Pods](06-pod-network-benchmark.md)
RTT entre Pods, latencia HTTP y rendimiento medidos en EKS para el mismo nodo, la misma AZ y entre AZ, además de la amplificación de consultas DNS con `ndots:5`.

## Resolución de problemas de red

### Problemas comunes y soluciones

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

Ejecute los diagnósticos desde un Pod existente que disponga de las herramientas indicadas. Consulte solo el CNI instalado en el clúster; los servicios de sistema de Auto Mode no son esos DaemonSets. El éxito de DNS, la accesibilidad TCP y una respuesta HTTP de la aplicación son comprobaciones diferentes. ICMP puede estar bloqueado o requerir privilegios adicionales, así que un ping fallido por sí solo no demuestra que un servicio TCP sea inalcanzable.

#### Service inalcanzable

```bash
NAMESPACE=default
SERVICE_NAME=my-service
kubectl -n "$NAMESPACE" get service "$SERVICE_NAME" -o yaml
kubectl -n "$NAMESPACE" get endpointslices \
  -l "kubernetes.io/service-name=$SERVICE_NAME" -o yaml
kubectl -n kube-system logs -l k8s-app=kube-proxy --tail=100
```

Use EndpointSlice para el diagnóstico actual de endpoints. Compruebe los selectores del Service, los puertos de destino, la disponibilidad de los endpoints, la familia de direcciones y las políticas aplicables. Inspeccione los logs de kube-proxy solo si ese componente es realmente el responsable del reenvío de Services; un reemplazo basado en eBPF o Auto Mode necesita sus propios diagnósticos.

#### Depuración de políticas de red

```bash
kubectl get networkpolicies.networking.k8s.io -A
kubectl -n kube-system exec ds/cilium -c cilium-agent -- cilium-dbg policy get
kubectl -n kube-system exec ds/cilium -c cilium-agent -- cilium-dbg endpoint list
# For a Calico installation using its standard CRD datastore:
kubectl get networkpolicies.crd.projectcalico.org -A
kubectl get globalnetworkpolicies.crd.projectcalico.org
```

Los comandos de Cilium inspeccionan un Agent seleccionado por la referencia al DaemonSet; elija el Agent del nodo afectado al investigar un incidente. Las instalaciones con la API nativa de Calico pueden exponer un grupo de API diferente, así que inspeccione los recursos que sirve la instalación. Las políticas de Kubernetes, de Calico y de las extensiones de AWS son recursos distintos y pueden tener precedencias diferentes.

### Pruebas de rendimiento de red

Este ejercicio TCP acotado usa el índice de imágenes fijado de Netshoot v0.16 del publicador, que contiene imágenes Linux AMD64 y Arm64; su Dockerfile incluye `iperf3`. Cree estos Pods en un entorno de pruebas donde se permita el TCP 5201. Es una carga de trabajo ilustrativa, no una comparación medida de CNI.

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

El cliente duerme durante una hora y el comando limita el tráfico ofrecido a 10 Mbit/s durante diez segundos. Esto prueba la ruta seleccionada, no el rendimiento máximo. Registre la ubicación real de Pod/nodo/AZ, los límites de recursos y las políticas antes de interpretar los resultados. Elija herramientas específicas de Windows para los nodos Windows. Al terminar, elimine únicamente los recursos de prueba que haya creado.

Estos Pods de diagnóstico independientes sirven para pruebas de conectividad. Para probar la aplicación de políticas de red nativas de EKS, use Pods gestionados por un Deployment o Job y los requisitos documentados de puerto de Service y de contenedor.

## Buenas prácticas

### 1. Planificación de direcciones IP

- Diseñe bloques CIDR suficientemente grandes
- Separe la red de Pods de la red de Services
- Diseñe las subredes pensando en la expansión futura

### 2. Aplicar políticas de red

Cree el namespace aislado `networking-demo` antes de usar este ejemplo. Selecciona todos los Pods de ese namespace y aísla tanto el tráfico de entrada como el de salida según la semántica estándar de NetworkPolicy de Kubernetes; los flujos de DNS y de aplicación necesarios requieren reglas de permiso explícitas. Su aplicación requiere un motor de políticas que la soporte. Otras API de políticas de clúster/administración pueden alterar la precedencia, y este único manifiesto no constituye una arquitectura completa de confianza cero.

- Aplique políticas de denegación por defecto (Zero Trust)
- Permita explícitamente solo el tráfico necesario
- Aísle los namespaces

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

### 3. Optimización del rendimiento

- Elija el CNI adecuado (acorde con la carga de trabajo)
- Optimización de MTU
- Ajuste de parámetros del kernel

### 4. Refuerzo de la seguridad

- Seleccione un cifrado de transporte admitido y verifique qué tráfico cubre.
- Configure la identidad de la carga de trabajo/aplicación y mTLS donde sea necesario; manténgalos separados de las listas de permitidos basadas en DNS/IP.
- Revise periódicamente los cambios de políticas, certificados y controles de acceso.

### 5. Garantizar la observabilidad

- Recopile métricas de red
- Habilite los flow logs
- Implemente el trazado distribuido

## Próximos pasos

Empiece por la [Pila de red del kernel](../kernel/02-network-stack.md), y continúe con la [Práctica de diagnóstico de red en Linux](07-linux-network-diagnostics.md) y su [cuestionario](../quizzes/networking/07-linux-network-diagnostics-quiz.md). La [ruta de aprendizaje](#learning-path) conecta estos fundamentos con los contenedores y los Services antes de los temas de CNI y AWS que siguen.

1. [VPC CNI](01-vpc-cni.md) - CNI por defecto de EKS
2. [Análisis detallado de Cilium](cilium/README.md) - Redes basadas en eBPF
3. [Análisis detallado de Calico](calico/README.md) - Enrutamiento, políticas y dataplanes
4. [VPC Lattice](02-vpc-lattice.md) - Redes gestionadas de AWS
5. [AWS Load Balancer Controller](03-aws-lb-controller.md) - Integración con ELB
6. [Gateway API](04-gateway-api.md) - Ingress de nueva generación
7. [Conectividad de VPC entre organizaciones](05-cross-org-vpc-connectivity.md) - Conectar VPC entre AWS Organizations (verificado en campo)
8. [Benchmark de red de Pods](06-pod-network-benchmark.md) - Latencia y rendimiento medidos por límite de nodo/AZ

---

## Referencias

- [Kubernetes network model](https://kubernetes.io/docs/concepts/services-networking/)
- [Kubernetes Services](https://kubernetes.io/docs/concepts/services-networking/service/)
- [Container runtime and CNI](https://kubernetes.io/docs/concepts/extend-kubernetes/compute-storage-net/network-plugins/)
- [Kubernetes NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [CNI specification](https://raw.githubusercontent.com/containernetworking/cni/main/SPEC.md)
- [Calico product editions](https://docs.tigera.io/calico/latest/about)
- [Calico policy tiers](https://docs.tigera.io/calico/latest/network-policy/policy-tiers/tiered-policy)
- [Calico Whisker flow logs](https://docs.tigera.io/calico/latest/observability/view-flow-logs)
- [Calico Windows limitations](https://docs.tigera.io/calico/latest/getting-started/kubernetes/windows-calico/limitations)
- [Flannel 0.28.9 networking and policy](https://raw.githubusercontent.com/flannel-io/flannel/v0.28.9/README.md)
- [Flannel backends](https://raw.githubusercontent.com/flannel-io/flannel/v0.28.9/Documentation/backends.md)
- [Original Weave repository status](https://api.github.com/repos/weaveworks/weave)
- [AWS VPC CNI 1.23.0](https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.23.0/README.md)
- [EKS network policy configuration](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy-configure.html)
- [EKS standard and Admin network policies](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html)
- [EKS prefix delegation and maxPods](https://docs.aws.amazon.com/eks/latest/userguide/cni-increase-ip-addresses-procedure.html)
- [EKS Admin and DNS policy deployment models](https://aws.amazon.com/blogs/containers/enhance-amazon-eks-network-security-posture-with-dns-and-admin-network-policies/)
- [EKS Auto Mode networking](https://docs.aws.amazon.com/eks/latest/userguide/auto-networking.html)
- [EKS add-on requirements](https://docs.aws.amazon.com/eks/latest/userguide/workloads-add-ons-available-eks.html)
- [EKS control plane architecture](https://docs.aws.amazon.com/eks/latest/best-practices/control-plane.html)
- [Netshoot v0.16 image metadata](https://hub.docker.com/v2/repositories/nicolaka/netshoot/tags/v0.16)
- [Netshoot v0.16 Dockerfile](https://raw.githubusercontent.com/nicolaka/netshoot/v0.16/Dockerfile)
- [Tetragon runtime security](https://tetragon.io/docs/overview/)
- [AWS LBC 3.5 NLB configuration](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/docs/guide/service/nlb.md)
- [AWS LBC 3.5 Ingress configuration](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/docs/guide/ingress/annotations.md)
- [Gateway Load Balancer concepts](https://docs.aws.amazon.com/vpc/latest/privatelink/gateway-load-balancers.html)
- [GENEVE encapsulation (RFC 8926)](https://www.rfc-editor.org/rfc/rfc8926)
- [VPC DNS resolver](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-dns.html)
- [Route 53 Resolver endpoints and rules](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver.html)
- [VPC route table evaluation order](https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Route_Tables.html)
- [Local routes and more-specific subnet routes](https://docs.aws.amazon.com/vpc/latest/userguide/subnet-route-tables.html)
- [Static and propagated route priority](https://docs.aws.amazon.com/vpc/latest/userguide/route-tables-priority.html)
- [AmazonProvidedDNS addresses and behavior](https://docs.aws.amazon.com/vpc/latest/userguide/AmazonDNS-concepts.html)
- [GWLB flow stickiness and failover](https://docs.aws.amazon.com/elasticloadbalancing/latest/gateway/edit-target-group-attributes.html)
- [Kubernetes Service virtual IPs and kube-proxy modes](https://kubernetes.io/docs/reference/networking/virtual-ips/)
- [CoreDNS Service names and forwarding configuration](https://kubernetes.io/docs/tasks/administer-cluster/dns-custom-nameservers/)
- [PrivateLink resource endpoints](https://docs.aws.amazon.com/vpc/latest/privatelink/privatelink-access-resources.html)
- [Netfilter/iptables project documentation](https://www.netfilter.org/documentation/index.html)
- [EC2 Elastic Fabric Adapter](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/efa.html)
- [QUIC transport protocol (RFC 9000)](https://www.rfc-editor.org/rfc/rfc9000)
- [HTTP/3 (RFC 9114)](https://www.rfc-editor.org/rfc/rfc9114)
- [gRPC over HTTP/2 and load balancing](https://grpc.io/blog/grpc-load-balancing/)
- [Gateway API GRPCRoute](https://gateway-api.sigs.k8s.io/guides/user-guides/grpc-routing/)
