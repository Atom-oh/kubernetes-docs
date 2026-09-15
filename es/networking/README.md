# Redes de Kubernetes

> **Última actualización**: September 15, 2026. Las referencias a características incluyen Cilium 1.20.1, Calico Open Source 3.32, Flannel 0.28.9 y AWS VPC CNI 1.23.0. Compruebe la matriz de Kubernetes/plataforma de cada producto antes de la instalación; no constituyen una configuración de clúster probada de manera conjunta.

## Descripción general

Las redes de Kubernetes son la capa de infraestructura principal que permite la comunicación entre aplicaciones en contenedores. Esta sección abarca desde los conceptos básicos de redes de Kubernetes hasta soluciones avanzadas de CNI (Container Network Interface) y patrones de red en entornos de AWS EKS.

## Ruta de aprendizaje {#learning-path}

Después del curso para principiantes, use la [ruta experta de redes](expert/README.md) para conectar proyectos de protocolos, políticas de enrutamiento, EVPN, rendimiento de Linux, diseño en la nube y evaluación de automatización. Primero compruebe los criterios de entorno, evidencia y recuperación de cada cuaderno.

Si no conoce Linux o las redes, comience con el [curso para principiantes](beginner/README.md). Sus ocho lecciones conectan la CLI, el direccionamiento, DNS, SSH, firewalls, monitorización y un proyecto final. La ruta inferior amplía esa base hacia los protocolos, el kernel y las implementaciones de clúster.

Avance desde los conceptos de protocolo hasta las observaciones y, después, conéctelos con las responsabilidades de contenedores, clústeres y nube. Use los requisitos previos para elegir un punto de entrada y los resultados para comprobar la comprensión antes de continuar.

| Etapa | Rol | Requisitos previos | Resultado | Leer / practicar |
|---|---|---|---|---|
| Protocolos, direccionamiento, HTTP | Establecer el vocabulario | Uso básico de la línea de comandos | Rastrear una solicitud y distinguir el comportamiento de direccionamiento, transporte y aplicación | Fundamentos de red [Parte 1](../basics/06-network-fundamentals-part1.md), [Parte 2](../basics/06-network-fundamentals-part2.md), [Parte 3](../basics/06-network-fundamentals-part3.md), [Parte 4](../basics/06-network-fundamentals-part4.md) |
| Sockets de Linux, VFS, rutas de paquetes | Conectar las API con el kernel | Fundamentos de TCP/IP | Distinguir FD, búferes de socket, ventanas y colas | [Pila de red del kernel](../kernel/02-network-stack.md) |
| Diagnóstico de red de Linux | Probar hipótesis con evidencia | Conceptos de sockets y rutas de paquetes | Correlacionar observaciones de sockets, paquetes y aplicaciones | [Práctica de diagnóstico](07-linux-network-diagnostics.md) · [Cuestionario](../quizzes/networking/07-linux-network-diagnostics-quiz.md) |
| Redes de Docker y contenedores | Localizar los límites de espacios de nombres | Rutas de paquetes de Linux y diagnóstico básico | Explicar las redes de bridge, los puertos publicados y la resolución de nombres de contenedores | [Tecnología de contenedores](../basics/03-container-technology.md) |
| Kubernetes Service, DNS, Ingress | Mapear abstracciones de clúster | Redes de contenedores | Rastrear un nombre mediante un Service hasta sus endpoints e identificar el rol de ingress | [Servicios y redes](../core/03-services-networking.md) · [Laboratorio](../labs/core/03-services-networking-lab.md) |
| eBPF, CNI, políticas | Comparar las responsabilidades de implementación | Rutas de Pod y Service | Distinguir el reenvío de paquetes, la aplicación de políticas y la observabilidad | [Fundamentos de eBPF](../basics/05-ebpf-fundamentals.md) · [Cilium](cilium/README.md) · [Calico](calico/README.md) |
| Límites y rendimiento de red de AWS | Aplicar el modelo a rutas en la nube | Conceptos de CNI y habilidades de medición | Identificar los límites de VPC, nodos y AZ e interpretar las mediciones en contexto | [VPC CNI](01-vpc-cni.md) · [AWS Load Balancer Controller](03-aws-lb-controller.md) · [Conectividad VPC entre organizaciones](05-cross-org-vpc-connectivity.md) · [Benchmark de red de Pod](06-pod-network-benchmark.md) |

## Modelo de redes de Kubernetes

El modelo actual de Kubernetes proporciona una red de Pod en la que los Pods pueden comunicarse directamente entre nodos sin traducción de direcciones ni proxies, **sujeto a una segmentación de red intencional**. Los agentes de nodo como kubelet deben poder alcanzar los Pods de su propio nodo. Las políticas de red, el enrutamiento y los listeners de aplicación aún determinan si una conexión concreta tiene éxito.

Los Pods ordinarios tienen su propio espacio de nombres de red y direcciones de todo el clúster; los contenedores de un Pod comparten ese espacio de nombres y localhost. Los Pods de red de host comparten la red del nodo, y las configuraciones dual-stack o multirred necesitan un manejo de direcciones más preciso. Volver a crear un Pod puede asignar una IP distinta; reiniciar un contenedor dentro del mismo Pod no necesariamente vuelve a crear su sandbox de red.

| Componente | Rol |
|---|---|
| Red de Pod | Direccionamiento y conectividad entre espacios de nombres de red de cargas de trabajo |
| Service/detección | Nombres de servicio o direcciones virtuales estables sobre endpoints cambiantes |
| Implementación de Ingress/Gateway | Entrada externa configurada y enrutamiento de aplicaciones |
| Motor de políticas de red | Aplica las políticas compatibles con la implementación seleccionada |

Estos roles no forman una ruta de paquetes serie obligatoria. La traducción de Service, un proxy L7 y la política de carga de trabajo pueden cambiar cómo una solicitud concreta atraviesa la red.

### Redes de Pod

Las redes de Pod proporcionan el direccionamiento y las rutas para la comunicación de Pod. La siguiente ilustración muestra Pods IPv4 ordinarios; sus conexiones suponen que las políticas y controles de red aplicables los permiten.

![Rutas ilustrativas directas de Pod IPv4 entre dos nodos, con conectividad sujeta a la política y el enrutamiento configurados.](../.gitbook/assets/en-networking-readme-1.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-1.html)

Las direcciones son direcciones de Pod ordinarias ilustrativas. El aislamiento intencional y las configuraciones de red de host o multirred requieren su propia interpretación.

#### Métodos de implementación de redes de Pod

| Método | Descripción | CNI de ejemplo |
|--------|-------------|-------------|
| **Red superpuesta** | Encapsula el tráfico sobre la red existente | Flannel VXLAN, Calico VXLAN/IPIP, Cilium VXLAN/Geneve |
| **Enrutamiento nativo** | Usa rutas en la red subyacente sin esa encapsulación superpuesta | AWS VPC CNI, enrutamiento/BGP de Calico, enrutamiento nativo de Cilium |
| **Encapsulación condicional** | Usa rutas directas o encapsulación conforme a la topología configurada | Modos compatibles de Calico/Flannel/Cilium, con distintos requisitos previos |

### Redes de Service

Los Services describen un conjunto lógico de endpoints, normalmente Pods, y cómo acceder a ellos. ClusterIP proporciona de forma predeterminada una IP virtual estable; los Services headless omiten esa IP virtual y ExternalName usa asignación DNS CNAME. Un Service también puede tener endpoints administrados sin un selector de Pod.

![Mecanismos de entrada típicos para Services ClusterIP, NodePort, LoadBalancer y ExternalName; la asignación DNS se distingue del reenvío de paquetes.](../.gitbook/assets/en-networking-readme-2.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-2.html)

Estos son mecanismos de exposición típicos, no garantías de seguridad. El rango de NodePort y las direcciones de nodo accesibles son configurables; los LoadBalancers pueden ser internos. ExternalName devuelve un alias DNS y no crea un proxy de reenvío.

#### Características de los tipos de Service

Cree Pods coincidentes con `app: my-app` en `default`, escuchando en los puertos de destino mostrados. El rango de asignación predeterminado de NodePort es 30000–32767 y se puede configurar. La accesibilidad externa sigue dependiendo de las direcciones, rutas y controles de acceso.

El ejemplo de LoadBalancer selecciona explícitamente **AWS Load Balancer Controller**, con destinos de instancias EC2 y NodePorts asignados. Primero instale/configure ese controlador y sus requisitos previos de IAM/subred. EKS Auto Mode usa otro controlador/clase. El puerto 443 solo selecciona aquí un puerto TCP; el backend debe servir TLS en 8443 o configurarse por separado en el balanceador de carga.

Estas asignaciones de puertos ilustran la API general de Kubernetes Service. Actualmente, AWS documenta requisitos adicionales de políticas de red nativas de EKS: el puerto de Service debe coincidir con el puerto de contenedor, y los Pods administrados por controladores con `metadata.ownerReferences` proporcionan una aplicación confiable. Adapte los ejemplos a esos requisitos antes de probar esa implementación de políticas.

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

Un recurso Ingress necesita un controlador y su plano de datos. Este ejemplo HTTP usa AWS LBC con `spec.ingressClassName: alb` y destinos IP. Los Services `api-v1`, `api-v2` y `web-frontend` referenciados deben existir en `default`, exponer el puerto 80 y tener endpoints de Pod listos y enrutables por VPC. Configure HTTPS/certificados por separado cuando sea necesario. Consulte la [guía de LBC](03-aws-lb-controller.md) para conocer sus requisitos previos de instalación y destinos.

Ingress define reglas para enrutar tráfico HTTP/HTTPS a Services internos del clúster.

![Enrutamiento lógico de host/ruta de Ingress a backends de Service y Pods.](../.gitbook/assets/en-networking-readme-3.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-3.html)

El cuadro representa la función del plano de datos de Ingress. AWS LBC programa ALB; el tráfico de aplicación no atraviesa el proceso de reconciliación del controlador. Dependiendo del modo de destino, el plano de datos puede alcanzar IP de Pod o NodePorts en lugar de atravesar una IP virtual de Service como un salto adicional literal.

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

CNI estandariza la interfaz mediante la cual un runtime configura una red de contenedor. En Kubernetes actual, kubelet solicita operaciones de sandbox de Pod mediante CRI y el **runtime de contenedores administra CNI**. Los antiguos flags de administración directa de CNI de kubelet se eliminaron en Kubernetes 1.24.

### Responsabilidades del runtime y los plugins

| Actor | Responsabilidad |
|---|---|
| kubelet | Solicita la creación/eliminación de sandbox mediante la interfaz de runtime de contenedores |
| Runtime de contenedores | Selecciona la configuración de red e invoca la cadena de plugins CNI |
| Plugin CNI | Recibe configuración, realiza ADD/DEL y otras operaciones compatibles, y devuelve resultados |
| Implementación de IPAM | Asigna/libera direcciones; puede ser un plugin delegado o parte de un agente específico del proveedor |
| Agente de nodo opcional | Mantiene rutas, políticas, grupos de IP o estado del datapath específicos del proveedor |

El runtime pasa la configuración al plugin mediante la interfaz CNI; un agente separado de larga ejecución o un binario IPAM no es obligatorio para todos los plugins. Los tipos de interfaz también varían: los pares veth son comunes, pero no son la única implementación.

## Comparación de CNI

| Proyecto / ámbito | Redes y políticas | Características y límites que distinguir |
|---|---|---|
| **Cilium 1.20.1** | Redes eBPF; Envoy para funciones L7 relevantes; políticas de red Cilium y Hubble | Dataplane de worker Linux, con requisitos de AMD64/Arm64. La disponibilidad de CLI de Windows no es soporte de CNI de Windows. WireGuard/IPsec y Beta ztunnel mTLS tienen ámbitos distintos. |
| **Calico Open Source 3.32** | Opciones de enrutamiento/encapsulación; opciones iptables, nftables y eBPF; niveles de políticas ordenados y políticas de host/cargas de trabajo | Windows tiene límites independientes, incluida la ausencia de dataplane Linux eBPF o WireGuard. La observabilidad de flujos Whisker/Goldmane está disponible como Tech Preview. Consulte la matriz de ediciones para capacidades de pago. |
| **Flannel 0.28.9** | Asignación de subred de host y transporte entre nodos; VXLAN, host-gw y otros backends | `flanneld` no aplica por sí mismo NetworkPolicy; el `netpol.enabled` opcional del chart despliega un controlador de políticas SIGs. WireGuard es un backend documentado; IPsec es experimental. Windows VXLAN tiene configuraciones/límites específicos. |
| **AWS VPC CNI 1.23.0 / EKS** | Asignación de direcciones VPC y ENI/prefijos EC2; capacidades de políticas de red estándar y Admin de EKS en nodos EC2 Linux compatibles | EKS Auto Mode es una implementación de red administrada con capacidades adicionales de políticas DNS. Windows, Fargate, redes personalizadas, delegación de prefijos y soporte multi-NIC tienen condiciones independientes. |
| **Proyecto original Weave Net** | Implementación histórica de redes superpuestas | El repositorio original `weaveworks/weave` está archivado. No lo describa como un valor predeterminado activo y compatible para un clúster nuevo. |

### Políticas, cifrado y observabilidad

- Cilium proporciona políticas conscientes de HTTP/DNS mediante los componentes L7 aplicables, y políticas de clúster completo/host. Su semántica de denegar/permitir no es la API de Tier ordenado de Calico.
- Calico Open Source incluye niveles jerárquicos de políticas y políticas de host. La matriz de productos actual asigna la política de capa de aplicación, la política DNS/FQDN y Cluster Mesh a Cloud/Enterprise; no deben atribuirse silenciosamente a la edición de código abierto. El cifrado en tránsito documentado de Calico usa WireGuard.
- Amazon EKS proporciona controles Admin/Baseline de `ClusterNetworkPolicy` para Auto Mode y las instalaciones EC2/VPC-CNI compatibles. La característica DNS/FQDN `ApplicationNetworkPolicy` que describe AWS es para **Auto Mode**. Su nombre no implica la inspección actual de métodos/cuerpo HTTP.
- El controlador de políticas opcional de Flannel tiene sus propios requisitos; seleccionar solo un backend de red no habilita la aplicación.
- El cifrado entre nodos, la identidad autenticada de cargas de trabajo y mTLS de aplicación son controles diferentes. La visibilidad de flujos de red también difiere del rastreo de aplicaciones o de la aplicación de procesos/archivos.

### Enrutamiento y rendimiento

Calico y Cilium pueden anunciar rutas mediante BGP; eso por sí solo no proporciona descubrimiento de servicios multiclúster, sincronización de políticas ni cifrado. Flannel host-gw usa rutas directas y requiere conectividad adecuada de capa 2. Una red superpuesta añade consideraciones de encapsulación y MTU, pero no puede inferirse una clasificación universal de rendimiento a partir del nombre de CNI.

La cifra anterior de rendimiento de 100/98/95/85/80/75 por ciento no tenía una carga de trabajo, versiones ni fuente de medición reproducibles. Use hardware, kernel, tamaños de paquete/solicitud, concurrencia, configuraciones de cifrado/política, rendimiento, pérdida y latencia de cola comparables. El [benchmark de Pod](06-pod-network-benchmark.md) separado conserva su propio entorno y mediciones históricas.

## Guía de selección de CNI

Primero elija el modelo de enrutamiento, políticas, sistema operativo y soporte requerido; después pruebe esa combinación.

| Necesidad | Ruta de evaluación |
|---|---|
| Direccionamiento VPC estándar de EKS y políticas de red compatibles | Evalúe las capacidades de AWS VPC CNI/EKS antes de añadir un segundo motor de políticas. |
| Niveles de políticas ordenados, política de host o BGP de infraestructura | Evalúe la edición/dataplane de Calico relevante y los requisitos previos de enrutamiento. |
| Política Cilium, Hubble o características de mesh seleccionadas | Compruebe la compatibilidad de Linux/kernel/plataforma y la [guía de mesh de Cilium](../service-mesh/cilium-service-mesh/README.md). Envoy sigue formando parte de las rutas L7 aplicables. |
| Una red pequeña con un conjunto de características limitado | Evalúe el backend y el controlador de políticas opcional de Flannel frente a los requisitos reales. |
| Aplicación de procesos, syscall o archivos | Evalúe por separado un componente de seguridad de runtime como Tetragon frente a la política de red. |

### Configuración del complemento administrado de EKS

Lo siguiente es una **carga útil de configuración** de ejemplo, no una instrucción para instalar tanto Calico como el motor de políticas VPC CNI en las mismas cargas de trabajo:

```json
{
  "enableNetworkPolicy": "true"
}
```

La cadena `"true"` es el tipo documentado para esta configuración. Seleccione una compilación de complemento de EKS compatible con la versión existente de Kubernetes e inspeccione el esquema de configuración de esa compilación:

```bash
EKS_REGION=ap-northeast-2
KUBERNETES_MINOR=1.35  # Replace with the existing cluster's minor version
aws eks describe-addon-versions --region "$EKS_REGION" --addon-name vpc-cni \
  --kubernetes-version "$KUBERNETES_MINOR"
: "${VPC_CNI_ADDON_VERSION:?Set the compatible eksbuild version selected from metadata}"
aws eks describe-addon-configuration --region "$EKS_REGION" --addon-name vpc-cni \
  --addon-version "$VPC_CNI_ADDON_VERSION"
```

El número de lanzamiento upstream 1.23.0 y una versión `eksbuild` de EKS son identificadores distintos. Combine los cambios con la configuración prevista del complemento administrado; no seleccione ciegamente `latest` ni reemplace valores no relacionados. Una migración desde una implementación de políticas de terceros también necesita eliminar su estado de aplicación existente y un plan probado de transición de nodos/cargas de trabajo.

## Fundamentos de redes de EKS

### Arquitectura de red predeterminada de EKS

| Ubicación / componente | Responsabilidad |
|---|---|
| VPC administrada por EKS | AWS ejecuta el plano de control administrado de Kubernetes entre zonas de disponibilidad. |
| VPC de clúster del cliente | Las redes de worker, las subredes seleccionadas y las ENI entre cuentas administradas por EKS proporcionan las rutas configuradas hacia el plano de control. |
| ALB/NLB en subredes VPC de cliente seleccionadas | Proporciona el punto de entrada de aplicación público o interno elegido; un internet gateway/NAT gateway no sustituye esa configuración de enrutamiento. |
| NAT gateway o endpoints de servicio privados | Proporciona las rutas salientes concretas que requiere el diseño de la carga de trabajo. |

La figura anterior situaba el plano de control dentro de la VPC del cliente y los balanceadores de carga fuera de ella; se ha sustituido por estos límites de propiedad.

### DNS y redes por modo de cómputo

| Modo de cómputo | DNS / ubicación de componentes |
|---|---|
| Nodos EC2 estándar | Normalmente usan el Deployment CoreDNS configurado y los componentes de red instalados; los reemplazos necesitan su propia configuración compatible. |
| EKS Auto Mode puro | Las funciones de CoreDNS, VPC CNI y kube-proxy se ejecutan como servicios systemd de nodo administrados. Un Deployment/complemento CoreDNS es innecesario para estos nodos. |
| Auto Mode combinado con nodos no Auto | Conserve el Deployment CoreDNS para los nodos no Auto; no pueden usar el servicio DNS Auto Mode de otro nodo. |

El primer resolvedor DNS de Auto Mode es local al nodo. El reenvío upstream y la comunicación con el plano de control aún pueden requerir acceso a la red; esto no garantiza que cada paquete relacionado con DNS permanezca en el nodo. AWS documenta políticas Admin y DNS para Auto Mode, mientras que la política Admin estándar de EC2 VPC-CNI tiene sus propios requisitos de versión/habilitación.

### Cómo funciona VPC CNI

AWS VPC CNI proporciona a los Pods ordinarios direcciones enrutables por VPC usando el modo IPAM seleccionado. Las direcciones IPv4 secundarias, los prefijos delegados, las ENI de rama y las configuraciones multi-NIC difieren; los Pods de red de host comparten la red del nodo.

![Asignación ilustrativa de IPv4 secundaria desde ENI EC2 a Pods, incluida una interfaz cálida opcional.](../.gitbook/assets/en-networking-readme-9.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-9.html)

Esto representa únicamente el modo de IP secundaria. Una ENI cálida es una estrategia de asignación configurable, no un requisito de que cada nodo reserve siempre exactamente una. La delegación de prefijos, las redes personalizadas y las ENI de rama tienen reglas de asignación distintas.

#### Límites de ENI e IP

| Tipo de instancia | ENI máximas | Slots IPv4 por ENI | Valor de arranque IPv4 secundaria heredado |
|---------------|----------|--------------|------------------------|
| t3.medium | 3 | 6 | 17 |
| t3.large | 3 | 12 | 35 |
| m5.large | 3 | 10 | 29 |
| m5.xlarge | 4 | 15 | 58 |
| m5.2xlarge | 4 | 15 | 58 |
| c5.4xlarge | 8 | 30 | 234 |

Estos valores se verifican frente a los límites de instancia de VPC CNI 1.23.0 y la tabla heredada de Pods máximos. El cálculo histórico es `ENIs × (IPv4 slots per ENI − 1) + 2`; no es una recomendación universal actual. La delegación de prefijos, las redes personalizadas, las ENI de rama y varias tarjetas de red modifican la capacidad de direcciones. La programación de Kubernetes también está limitada por `maxPods` de kubelet y los recursos. Los grupos de nodos administrados de EKS limitan `maxPods` a 110 para instancias con menos de 30 vCPU y a 250 en caso contrario; el número de IP disponibles por sí solo no anula ese límite.

### Consideraciones de redes de EKS

#### Administración de direcciones IP

Para **Linux VPC CNI**, configure las variables de entorno documentadas mediante el mecanismo de administración seleccionado para el complemento/Helm/DaemonSet. Lo siguiente es un fragmento de configuración del complemento EKS. El antiguo ConfigMap `amazon-vpc-cni` con `enable-prefix-delegation` no configura Linux IPAMD de esta manera. Conserve otros valores previstos del complemento al aplicar un cambio.

```json
{
  "env": {
    "ENABLE_PREFIX_DELEGATION": "true",
    "WARM_PREFIX_TARGET": "1"
  }
}
```

Como alternativa, ajuste el mínimo total de asignación y el objetivo de IP libres. Cuando se configura `MINIMUM_IP_TARGET` o `WARM_IP_TARGET`, tiene prioridad sobre `WARM_PREFIX_TARGET`; son políticas alternativas en lugar de cuatro objetivos aditivos independientes. La asignación aún se produce en unidades del tamaño de prefijo. El soporte Nitro, espacio `/28` contiguo para IPv4 y un límite de Pod de kubelet adecuado son requisitos previos independientes.

La asignación de prefijos de Windows es una ruta de configuración distinta: AWS documenta `enable-windows-prefix-delegation` y sus claves de objetivo cálido en el ConfigMap `amazon-vpc-cni`. No copie sin cambios el procedimiento de variables de entorno de Linux a Windows.

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

Estos ejemplos IPv4 requieren ID de subred/grupo de seguridad reales en la AZ y VPC previstas. Habilite las redes personalizadas y seleccione la ENIConfig de cada nodo mediante su etiqueta de zona. Una anotación explícita de nodo ENIConfig tiene prioridad sobre esa etiqueta. Los nombres de ejemplo siguientes usan la misma región en ambos idiomas; reemplácelos por las zonas de nodo reales. Instalar solamente objetos ENIConfig no activa las redes personalizadas.

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

Los elementos siguientes se mencionan de pasada en otras partes de esta descripción general. Los procedimientos completos de configuración y los números medidos se encuentran en las páginas detalladas vinculadas; esta sección organiza en qué se diferencian estas piezas por capa y dónde encaja cada una.

### L2–L7 y la diferencia entre routers y balanceadores de carga

"Router" y "load balancer" suelen aparecer en la misma frase, pero responden a preguntas distintas. Un router elige (en general) una ruta hacia un único destino; un balanceador de carga elige un destino entre varios candidatos equivalentes mediante un algoritmo de distribución.

| Capa | Dispositivo/función | Base de decisión | Correspondencia Kubernetes/AWS |
|---|---|---|---|
| L2 (enlace) | Switch, bridge | Dirección MAC de destino | Pares veth y bridges Linux creados por el CNI, la NIC virtual que expone una ENI |
| L3 (red) | Router o inserción transparente de appliance | IP de destino para el enrutamiento; identidad de flujo para la selección de appliance | El router implícito de la VPC, TGW; GWLB encapsula paquetes IP para appliances |
| L4 (transporte) | Balanceador de carga L4 | Identidad de conexión/flujo, comúnmente la tupla de 5 | NLB; kube-proxy (iptables, IPVS, nftables); implementaciones de Service eBPF independientes |
| L7 (aplicación) | Balanceador de carga/proxy inverso L7 | Host, ruta y encabezados por solicitud; consciente del protocolo | ALB, implementaciones de Ingress/Gateway API, sidecars de service mesh (Envoy) |

La diferencia clave es la **unidad de distribución**. Un balanceador de carga L4 normalmente selecciona un destino para una conexión TCP o un flujo UDP rastreado. Un proxy L7 puede seleccionar un destino para cada solicitud de aplicación compatible, incluidas las solicitudes que comparten una conexión. GWLB distribuye flujos IP encapsulados entre appliances de seguridad en lugar de analizar solicitudes de aplicación. La afinidad de flujo depende del timeout, la salud y el comportamiento de failover configurados; no garantiza que un flujo nunca pueda reasignarse o interrumpirse.

> 📎 Las definiciones de los conceptos L2/L3 a nivel de protocolo están en [Fundamentos de red Parte 1](../basics/06-network-fundamentals-part1.md); los tipos de destino ALB/NLB y la configuración real están en [AWS Load Balancer Controller](03-aws-lb-controller.md).

### Conectividad entre cuentas/VPC: TGW, VPC Peering, GWLB, PrivateLink, Lattice

Estas cinco opciones de conectividad difieren en capa y modelo de tráfico. La latencia medida entre el uso compartido de TGW RAM, VPC Peering, PrivateLink, TGW Peering y VPC Lattice está en [Conectividad VPC entre organizaciones](05-cross-org-vpc-connectivity.md). Esta sección añade GWLB, que no está en esa tabla de comparación, y reformula las cinco por capa.

| Conectividad | Capa/modelo | Características |
|---|---|---|
| VPC Peering | L3, enrutamiento IP bidireccional | No es transitivo; no puede configurarse entre CIDR superpuestos |
| Transit Gateway (TGW) | L3, enrutamiento IP hub-and-spoke | Usa asociaciones de adjuntos y propagación en una o más tablas de rutas de TGW; uso compartido entre cuentas mediante RAM |
| Gateway Load Balancer (GWLB) | L3, inserción transparente de appliance | Encapsula el paquete original en GENEVE (UDP 6081); un modelo de servicio de endpoint VPC conecta el tráfico del consumidor con la flota de appliances del proveedor |
| PrivateLink | Conectividad de endpoint privado | Un servicio de endpoint respaldado por NLB es un modelo; también existen endpoints de recursos. Los CIDR de consumidor/proveedor pueden superponerse |
| VPC Lattice | Redes de aplicaciones y recursos | Los servicios HTTP/HTTPS admiten enrutamiento L7 y autorización IAM opcional; el paso directo TLS y las configuraciones de recursos tienen capacidades distintas |

GWLB inserta appliances de inspección como firewalls e IDS/IPS en una ruta IP mediante un endpoint de Gateway Load Balancer. Su afinidad de flujo predeterminada usa cinco campos; las configuraciones compatibles pueden usar en cambio dos o tres. Valide las rutas de ida y retorno, la salud de los appliances, la MTU de encapsulación, las NACL y los grupos de seguridad de las cargas de trabajo/appliances reales. GWLB no tiene por sí mismo un grupo de seguridad como ALB, y la afinidad de flujo no sustituye las pruebas de fallos.

> 📎 La integración completa de EKS/VPC Lattice (Gateway API Controller, autorización IAM, enrutamiento) está en [VPC Lattice](02-vpc-lattice.md).

### Cómo se comportan realmente el resolvedor DNS y las tablas de rutas

**Resolvedor DNS:** AmazonProvidedDNS **es Route 53 Resolver**. Sus direcciones incluyen la dirección de red IPv4 principal de la VPC más dos (`10.0.0.2` para `10.0.0.0/16`) y `169.254.169.253`; resuelve zonas privadas asociadas y nombres públicos según las reglas de Resolver. CoreDNS normalmente sirve el dominio de clúster de Kubernetes configurado, a menudo `cluster.local`; `kube-dns` es su nombre de Service, no un espacio de nombres ni una zona DNS. El reenvío externo sigue el Corefile y el archivo de resolvedor visible para el Pod DNS. Inspeccione esas configuraciones en lugar de asumir que el archivo de resolvedor del nodo se usa sin cambios. En un diseño de endpoint de Resolver, los endpoints entrantes aceptan consultas on-premises, mientras que los endpoints salientes y las reglas asociadas reenvían consultas de VPC seleccionadas al DNS on-premises. El resolvedor local al nodo de Auto Mode no elimina las dependencias upstream.

**Tablas de rutas:** La evaluación de rutas de VPC generalmente usa coincidencia de prefijo más largo. AWS permite reemplazar el destino de una ruta `local` y añadir rutas de subred más específicas compatibles para el enrutamiento de appliances; `local` no es incondicionalmente la ruta más específica. Para destinos idénticos, las rutas estáticas de VPC tienen prioridad sobre las rutas propagadas desde un virtual private gateway. Una ruta VPC que apunta a un TGW es estática; la propagación dentro de un TGW pertenece a sus tablas de rutas independientes. Los destinos no válidos pueden dejar entradas `blackhole` que descartan tráfico, por lo que debe inspeccionar el estado de la ruta además del destino. Una subred sin una asociación explícita de tabla de rutas usa la tabla de rutas principal de la VPC.

> 📎 La prioridad de rutas TGW/Peering y los ejemplos de configuración de rutas estáticas están en [hallazgos operativos de Conectividad VPC entre organizaciones](05-cross-org-vpc-connectivity.md#operational-findings).

### El plano de datos del kernel: iptables, IPVS, eBPF y filtrado de paquetes

El reenvío de Service de Linux y la aplicación de políticas de red pueden usar mecanismos distintos. Netfilter proporciona hooks de rutas de paquetes usados por iptables y nftables. Las implementaciones eBPF pueden adjuntarse en hooks XDP, tc o socket y realizar allí la selección de Service. Esto no significa que cada paquete de un clúster habilitado para eBPF omita Netfilter o el seguimiento de conexiones; la ruta depende de CNI, kernel, enrutamiento y configuración de características.

| Implementación | Dónde se sitúa | Características |
|---|---|---|
| iptables | Cadenas de reglas secuenciales en hooks netfilter | El tiempo de evaluación escala con el número de reglas (O(n)); modo predeterminado histórico de kube-proxy |
| IPVS | Balanceador de carga L4 nativo del kernel, una extensión de netfilter | Búsqueda basada en hash (casi O(1)); obsoleto como modo kube-proxy desde Kubernetes 1.35 |
| nftables | Marco sucesor de netfilter para iptables | Modo estable de kube-proxy desde 1.33; compruebe primero la compatibilidad del kernel/CNI |
| eBPF (p. ej., Cilium) | Hooks XDP, tc y socket configurados | Puede reemplazar el manejo de Service de kube-proxy; es una implementación independiente, con comportamiento Netfilter/conntrack específico de la ruta |

Cambiar implementaciones puede dejar reglas de kernel y conexiones activas. Siga el procedimiento de migración de la distribución/CNI, drene las cargas de trabajo según sea necesario y planifique reinicios de nodos cuando la limpieza los requiera. Reemplazar kube-proxy por un CNI basado en eBPF también requiere un orden de transición compatible para que las implementaciones no compitan por el mismo tráfico de Service.

> 📎 La cronología de la obsolescencia de IPVS y la transición estable a nftables se tratan en [Introducción a Kubernetes](../basics/04-kubernetes-introduction.md); el reemplazo de kube-proxy eBPF de Cilium está en [Cilium eBPF](cilium/02-ebpf.md); el plano de datos eBPF de Calico y su procedimiento de migración están en [Calico eBPF](calico/06-ebpf-dataplane.md).

### Redes de cómputo intensivo: ENI, EFA, NVLink y transceptores ópticos

ENI, EFA y NVLink sirven a rutas distintas. Una **ENI** es una interfaz de red virtual adjunta a una instancia EC2 en una zona de disponibilidad; su tráfico IP normal puede alcanzar otras AZ y VPC conectadas cuando el enrutamiento y la política lo permiten (consulte [VPC CNI](01-vpc-cni.md)). **EFA** proporciona un dispositivo de omisión de SO utilizado mediante libfabric por software MPI/NCCL compatible. **El tráfico de dispositivos EFA no es enrutable y no puede cruzar límites de VPC/AZ**; el tráfico IP normal mediante el dispositivo ENA de una interfaz EFA-with-ENA sigue siendo enrutable. Las interfaces solo EFA no tienen dispositivo ENA ni direccionamiento IP. **NVLink** conecta GPU dentro de sistemas compatibles, incluidos dominios NVLink a escala de rack compatibles. Mida el hardware seleccionado, las operaciones colectivas y la ubicación en lugar de suponer una aceleración fija respecto a EFA.

Los **transceptores ópticos** son un concepto general de redes de centros de datos. Los cables DAC (Direct Attach Copper) son adecuados para tiradas cortas; los módulos ópticos y la fibra admiten otros requisitos de alcance y ancho de banda. QSFP y OSFP describen factores de forma de módulos, no una garantía de medios ópticos. Considere esto como información general: no establece el cableado físico de una carga de trabajo concreta de AWS.

> 📎 Los ejemplos de programación consciente de topología NVLink/IMEX y colocación de GPU Pod están en [Infraestructura de IA/ML](../ai-ml/06-ai-infrastructure.md); la restricción de límite VPC/AZ de EFA y las mediciones están en [Conectividad VPC entre organizaciones](05-cross-org-vpc-connectivity.md).

### Qué significan los protocolos de próxima generación para Kubernetes: HTTP/3, gRPC, QUIC

La mecánica de protocolo de HTTP/3 (RFC 9114) y su transporte QUIC (RFC 9000) se tratan en [Fundamentos de red Parte 2](../basics/06-network-fundamentals-part2.md) y [Parte 3](../basics/06-network-fundamentals-part3.md). Aquí cubrimos únicamente lo que realmente afecta a la distribución del tráfico de Kubernetes.

- **gRPC y balanceadores de carga L4:** gRPC multiplexa solicitudes sobre conexiones HTTP/2. Un balanceador L4 normalmente mantiene una conexión TCP establecida en su endpoint seleccionado; si ese endpoint es un proxy, puede tomar decisiones adicionales de enrutamiento. Añadir Pods por sí solo no redistribuye las conexiones existentes. La distribución por RPC requiere un proxy L7 compatible o una política del lado del cliente. Un RPC de streaming sigue siendo una llamada; sus mensajes individuales no se balancean de forma independiente.
- **GRPCRoute de Gateway API:** Ingress no tiene un recurso específico de gRPC, pero Gateway API estandariza el enrutamiento a nivel de servicio/método con `GRPCRoute`. El soporte varía según la implementación (cuántas coincidencias de encabezado, políticas de reintento, etc.), por lo que debe consultar la documentación propia del controlador.
- **Hasta dónde llega realmente HTTP/3/QUIC al clúster:** El soporte HTTP/3 entre un cliente y el borde (una CDN, un balanceador de carga) es una cuestión independiente del soporte HTTP/3 dentro del clúster o en la conexión backend de un Ingress. Muchas implementaciones de Ingress/Gateway aún hablan HTTP/1.1 o HTTP/2 con el backend, y si se admite HTTP/3 de extremo a extremo varía según la implementación y la versión; no generalice, consulte la documentación del controlador que se usa realmente.

## Subpáginas de redes

Esta sección trata los siguientes temas en detalle:

### [Redes de Linux desde el principio](beginner/README.md) {#beginner-course}

Si no conoce Linux o las redes, comience con el [curso para principiantes](beginner/README.md). Sus ocho lecciones conectan la CLI, el direccionamiento, DNS, SSH, firewalls, monitorización y un proyecto final. La ruta inferior amplía esa base hacia los protocolos, el kernel y las implementaciones de clúster.

### [Ruta experta de redes](expert/README.md) {#expert-course}

Después del curso para principiantes, use la [ruta experta de redes](expert/README.md) para conectar proyectos de protocolos, políticas de enrutamiento, EVPN, rendimiento de Linux, diseño en la nube y evaluación de automatización. Primero compruebe los criterios de entorno, evidencia y recuperación de cada cuaderno.

### [Práctica de diagnóstico de red de Linux](07-linux-network-diagnostics.md) {#linux-network-diagnostics}

Conecte los [conceptos de sockets y rutas de paquetes del kernel](../kernel/02-network-stack.md) con las observaciones antes de estudiar las implementaciones de CNI. Use el [cuestionario de diagnóstico](../quizzes/networking/07-linux-network-diagnostics-quiz.md) para comprobar su interpretación.

### [VPC CNI](01-vpc-cni.md)
Redes EKS con direcciones VPC para Pods ordinarios y requisitos previos de IPAM/políticas específicos de modo.

### [Análisis profundo de Cilium](cilium/README.md)
Solución CNI de alto rendimiento basada en eBPF. Proporciona características avanzadas como L7 Network Policy, Service Mesh y observabilidad (Hubble).

### [Análisis profundo de Calico](calico/README.md)
Uno de los CNI más utilizados. Potente Network Policy, soporte BGP y características empresariales. Abarca introducción, arquitectura, modos de red, análisis profundo de BGP, Network Policy, eBPF, temas avanzados, integración de EKS y guía de operaciones.

### [VPC Lattice](02-vpc-lattice.md)
Servicio administrado de redes de aplicaciones de AWS. Comunicación servicio a servicio entre VPC y cuentas.

### [AWS Load Balancer Controller](03-aws-lb-controller.md)
Integra Kubernetes Services e Ingress con AWS ELB (ALB/NLB).

### [Gateway API](04-gateway-api.md)
API de ingress de Kubernetes de próxima generación. Modelo de recursos estandarizado y configuración basada en roles.

### [Benchmark de red de Pod](06-pod-network-benchmark.md)
RTT de Pod a Pod, latencia HTTP y rendimiento medidos en EKS para el mismo nodo, la misma AZ y entre AZ, además de la amplificación de consultas DNS `ndots:5`.

## Solución de problemas de red

### Problemas y soluciones comunes

#### Error de comunicación de Pod a Pod

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

Ejecute los diagnósticos desde un Pod existente con las herramientas indicadas. Consulte solo el CNI instalado en el clúster; los servicios del sistema de Auto Mode no son esos DaemonSets. El éxito DNS, la accesibilidad TCP y una respuesta HTTP de aplicación son comprobaciones diferentes. ICMP puede estar bloqueado o requerir privilegios adicionales, por lo que un ping fallido por sí solo no demuestra que un servicio TCP sea inaccesible.

#### Service inaccesible

```bash
NAMESPACE=default
SERVICE_NAME=my-service
kubectl -n "$NAMESPACE" get service "$SERVICE_NAME" -o yaml
kubectl -n "$NAMESPACE" get endpointslices \
  -l "kubernetes.io/service-name=$SERVICE_NAME" -o yaml
kubectl -n kube-system logs -l k8s-app=kube-proxy --tail=100
```

Use EndpointSlice para el diagnóstico de endpoints actual. Compruebe los selectores de Service, puertos de destino, disponibilidad de endpoints, familia de direcciones y la política aplicable. Inspeccione los logs de kube-proxy solo si ese componente realmente posee el reenvío de Service; un reemplazo eBPF o Auto Mode necesita su propio diagnóstico.

#### Depuración de políticas de red

```bash
kubectl get networkpolicies.networking.k8s.io -A
kubectl -n kube-system exec ds/cilium -c cilium-agent -- cilium-dbg policy get
kubectl -n kube-system exec ds/cilium -c cilium-agent -- cilium-dbg endpoint list
# For a Calico installation using its standard CRD datastore:
kubectl get networkpolicies.crd.projectcalico.org -A
kubectl get globalnetworkpolicies.crd.projectcalico.org
```

Los comandos de Cilium inspeccionan un Agent seleccionado por la referencia DaemonSet; elija el Agent del nodo afectado al rastrear un incidente. Las instalaciones de API nativa de Calico pueden exponer un grupo de API distinto, por lo que debe inspeccionar los recursos servidos por la instalación. Las políticas de extensión de Kubernetes, Calico y AWS son recursos distintos y pueden tener distinta precedencia.

### Pruebas de rendimiento de red

Este ejercicio TCP acotado usa el índice de imagen Netshoot v0.16 fijado por el publicador, que contiene imágenes Linux AMD64 y Arm64; su Dockerfile incluye `iperf3`. Cree estos Pods en un entorno de prueba donde TCP 5201 esté permitido. Es una carga de trabajo ilustrativa, no una comparación de CNI medida.

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

El cliente duerme durante una hora y el comando limita el tráfico ofrecido a 10 Mbit/s durante diez segundos. Esto prueba la ruta seleccionada, no el rendimiento máximo. Registre la ubicación real de Pod/nodo/AZ, los límites de recursos y la política antes de interpretar los resultados. Elija herramientas específicas de Windows para nodos Windows. Elimine solo los recursos de prueba que creó al terminar.

Estos Pods de diagnóstico independientes son para pruebas de conectividad. Para pruebas de aplicación de políticas de red nativas de EKS, use Pods administrados por Deployment/Job y los requisitos documentados de puertos de Service/contenedor.

## Prácticas recomendadas

### 1. Planificación de direcciones IP

- Diseñe bloques CIDR suficientemente grandes
- Separe la red de Pod de la red de Service
- Diseñe subredes pensando en futuras ampliaciones

### 2. Aplicar políticas de red

Cree el espacio de nombres aislado `networking-demo` antes de usar este ejemplo. Selecciona todos los Pods allí y aísla tanto el ingreso como el egreso según la semántica estándar de Kubernetes NetworkPolicy; los flujos DNS y de aplicación necesarios requieren reglas explícitas de permiso. La aplicación requiere un motor de políticas compatible. Las API adicionales de políticas de clúster/admin pueden modificar la precedencia, y este manifiesto no es una arquitectura completa de confianza cero.

- Aplique políticas predeterminadas de denegación (Zero Trust)
- Permita explícitamente solo el tráfico necesario
- Aísle espacios de nombres

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

- Elija el CNI apropiado (que coincida con la carga de trabajo)
- Optimización de MTU
- Ajuste de parámetros del kernel

### 4. Endurecimiento de seguridad

- Seleccione el cifrado de transporte compatible y verifique qué tráfico cubre.
- Configure la identidad de carga de trabajo/aplicación y mTLS donde sea necesario; manténgalos separados de las listas de permisos basadas en DNS/IP.
- Revise con regularidad los cambios de políticas, certificados y control de acceso.

### 5. Garantizar la observabilidad

- Recopile métricas de red
- Habilite logs de flujo
- Implemente rastreo distribuido

## Próximos pasos

Después del [curso para principiantes](beginner/README.md), continúe con la [Pila de red del kernel](../kernel/02-network-stack.md), luego con la [Práctica de diagnóstico de red de Linux](07-linux-network-diagnostics.md) y su [cuestionario](../quizzes/networking/07-linux-network-diagnostics-quiz.md). La [ruta de aprendizaje](#learning-path) conecta estas bases con contenedores y Services antes de los temas de CNI y AWS siguientes.

1. [VPC CNI](01-vpc-cni.md) - CNI predeterminado de EKS
2. [Análisis profundo de Cilium](cilium/README.md) - Redes basadas en eBPF
3. [Análisis profundo de Calico](calico/README.md) - Enrutamiento, políticas y dataplanes
4. [VPC Lattice](02-vpc-lattice.md) - Redes administradas de AWS
5. [AWS Load Balancer Controller](03-aws-lb-controller.md) - Integración de ELB
6. [Gateway API](04-gateway-api.md) - Ingress de próxima generación
7. [Conectividad VPC entre organizaciones](05-cross-org-vpc-connectivity.md) - Conectar VPC entre AWS Organizations (verificado en campo)
8. [Benchmark de red de Pod](06-pod-network-benchmark.md) - Latencia y rendimiento medidos por límite de nodo/AZ

---

## Referencias

- [Modelo de red de Kubernetes](https://kubernetes.io/docs/concepts/services-networking/)
- [Kubernetes Services](https://kubernetes.io/docs/concepts/services-networking/service/)
- [Runtime de contenedores y CNI](https://kubernetes.io/docs/concepts/extend-kubernetes/compute-storage-net/network-plugins/)
- [Kubernetes NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Especificación de CNI](https://raw.githubusercontent.com/containernetworking/cni/main/SPEC.md)
- [Ediciones de producto de Calico](https://docs.tigera.io/calico/latest/about)
- [Niveles de políticas de Calico](https://docs.tigera.io/calico/latest/network-policy/policy-tiers/tiered-policy)
- [Logs de flujo Whisker de Calico](https://docs.tigera.io/calico/latest/observability/view-flow-logs)
- [Limitaciones de Calico para Windows](https://docs.tigera.io/calico/latest/getting-started/kubernetes/windows-calico/limitations)
- [Redes y políticas de Flannel 0.28.9](https://raw.githubusercontent.com/flannel-io/flannel/v0.28.9/README.md)
- [Backends de Flannel](https://raw.githubusercontent.com/flannel-io/flannel/v0.28.9/Documentation/backends.md)
- [Estado del repositorio original de Weave](https://api.github.com/repos/weaveworks/weave)
- [AWS VPC CNI 1.23.0](https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.23.0/README.md)
- [Configuración de políticas de red de EKS](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy-configure.html)
- [Políticas de red estándar y Admin de EKS](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html)
- [Delegación de prefijos y maxPods de EKS](https://docs.aws.amazon.com/eks/latest/userguide/cni-increase-ip-addresses-procedure.html)
- [Modelos de implementación de políticas Admin y DNS de EKS](https://aws.amazon.com/blogs/containers/enhance-amazon-eks-network-security-posture-with-dns-and-admin-network-policies/)
- [Redes de EKS Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/auto-networking.html)
- [Requisitos de complementos de EKS](https://docs.aws.amazon.com/eks/latest/userguide/workloads-add-ons-available-eks.html)
- [Arquitectura del plano de control de EKS](https://docs.aws.amazon.com/eks/latest/best-practices/control-plane.html)
- [Metadatos de imagen Netshoot v0.16](https://hub.docker.com/v2/repositories/nicolaka/netshoot/tags/v0.16)
- [Dockerfile de Netshoot v0.16](https://raw.githubusercontent.com/nicolaka/netshoot/v0.16/Dockerfile)
- [Seguridad de runtime de Tetragon](https://tetragon.io/docs/overview/)
- [Configuración de NLB de AWS LBC 3.5](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/docs/guide/service/nlb.md)
- [Configuración de Ingress de AWS LBC 3.5](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/docs/guide/ingress/annotations.md)
- [Conceptos de Gateway Load Balancer](https://docs.aws.amazon.com/vpc/latest/privatelink/gateway-load-balancers.html)
- [Encapsulación GENEVE (RFC 8926)](https://www.rfc-editor.org/rfc/rfc8926)
- [Resolvedor DNS de VPC](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-dns.html)
- [Endpoints y reglas de Route 53 Resolver](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver.html)
- [Orden de evaluación de tablas de rutas de VPC](https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Route_Tables.html)
- [Rutas locales y rutas de subred más específicas](https://docs.aws.amazon.com/vpc/latest/userguide/subnet-route-tables.html)
- [Prioridad de rutas estáticas y propagadas](https://docs.aws.amazon.com/vpc/latest/userguide/route-tables-priority.html)
- [Direcciones y comportamiento de AmazonProvidedDNS](https://docs.aws.amazon.com/vpc/latest/userguide/AmazonDNS-concepts.html)
- [Afinidad de flujo y failover de GWLB](https://docs.aws.amazon.com/elasticloadbalancing/latest/gateway/edit-target-group-attributes.html)
- [IP virtuales de Kubernetes Service y modos de kube-proxy](https://kubernetes.io/docs/reference/networking/virtual-ips/)
- [Nombres de Service de CoreDNS y configuración de reenvío](https://kubernetes.io/docs/tasks/administer-cluster/dns-custom-nameservers/)
- [Endpoints de recursos de PrivateLink](https://docs.aws.amazon.com/vpc/latest/privatelink/privatelink-access-resources.html)
- [Documentación del proyecto Netfilter/iptables](https://www.netfilter.org/documentation/index.html)
- [EC2 Elastic Fabric Adapter](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/efa.html)
- [Protocolo de transporte QUIC (RFC 9000)](https://www.rfc-editor.org/rfc/rfc9000)
- [HTTP/3 (RFC 9114)](https://www.rfc-editor.org/rfc/rfc9114)
- [gRPC sobre HTTP/2 y balanceo de carga](https://grpc.io/blog/grpc-load-balancing/)
- [GRPCRoute de Gateway API](https://gateway-api.sigs.k8s.io/guides/user-guides/grpc-routing/)
