# Redes de Kubernetes

> **Última actualización**: October 12, 2026
>
> **Ejemplos fijados**: Cilium 1.20.1, Calico Open Source 3.32.2, Flannel 0.28.9 y AWS VPC CNI/gráfico Helm upstream 1.23.0.
>
> **Información de la versión actual**: AWS enumera el complemento VPC CNI administrado por EKS `v1.23.1-eksbuild.1` para Kubernetes 1.31–1.37. Calico 3.33.0 es la versión Open Source más reciente y se prueba en Kubernetes 1.35–1.37. Revise sus notas de versión antes de cambiar los ejemplos fijados.
>
> Estas versiones no constituyen una configuración de clúster probada conjuntamente. Compruebe la matriz de Kubernetes/plataforma de cada producto antes de instalarlo.

## Descripción general

Las redes de Kubernetes son la capa central de infraestructura que permite la comunicación entre aplicaciones en contenedores. Esta sección abarca desde conceptos básicos de redes de Kubernetes hasta soluciones avanzadas de CNI (Container Network Interface) y patrones de red en entornos de AWS EKS.

## Ruta de aprendizaje {#learning-path}

Después del curso para principiantes, utilice la [ruta de redes experta](expert/README.md) para conectar proyectos de protocolos, políticas de enrutamiento, EVPN, rendimiento de Linux, diseño de nube y evaluación de automatización. Primero compruebe los criterios de entorno, evidencia y recuperación de cada cuaderno.

Si es nuevo en Linux o redes, comience con el [curso para principiantes](beginner/README.md). Sus ocho lecciones conectan la CLI, direccionamiento, DNS, SSH, firewalls, monitoreo y un proyecto final. La ruta siguiente extiende esa base hacia protocolos, el kernel e implementaciones de clúster.

Construya desde conceptos de protocolo hasta observaciones, y luego conéctelos con las responsabilidades de contenedores, clúster y nube. Use los prerrequisitos para elegir un punto de entrada y los resultados para comprobar su comprensión antes de continuar.

| Etapa | Función | Prerrequisitos | Resultado | Leer / practicar |
|---|---|---|---|---|
| Protocolos, direccionamiento, HTTP | Establecer el vocabulario | Uso básico de línea de comandos | Rastrear una solicitud y distinguir el comportamiento de direccionamiento, transporte y aplicación | Fundamentos de red [Parte 1](../basics/06-network-fundamentals-part1.md), [Parte 2](../basics/06-network-fundamentals-part2.md), [Parte 3](../basics/06-network-fundamentals-part3.md), [Parte 4](../basics/06-network-fundamentals-part4.md) |
| Sockets de Linux, VFS, rutas de paquetes | Conectar las API con el kernel | Fundamentos de TCP/IP | Distinguir FD, búferes de socket, ventanas y colas | [Pila de redes del kernel](../kernel/02-network-stack.md) |
| Diagnósticos de red de Linux | Probar hipótesis con evidencia | Conceptos de socket y ruta de paquetes | Correlacionar observaciones de socket, paquetes y aplicaciones | [Práctica de diagnósticos](07-linux-network-diagnostics.md) · [Cuestionario](../quizzes/networking/07-linux-network-diagnostics-quiz.md) |
| Docker y redes de contenedores | Localizar límites de namespaces | Rutas de paquetes de Linux y diagnóstico básico | Explicar redes de bridge, puertos publicados y resolución de nombres de contenedor | [Tecnología de contenedores](../basics/03-container-technology.md) |
| Kubernetes Service, DNS, Ingress | Mapear abstracciones del clúster | Redes de contenedores | Rastrear un nombre mediante un Service hasta sus endpoints e identificar la función de ingress | [Servicios y redes](../core/03-services-networking.md) · [Laboratorio](../labs/core/03-services-networking-lab.md) |
| eBPF, CNI, políticas | Comparar responsabilidades de implementación | Rutas de Pod y Service | Distinguir reenvío de paquetes, aplicación de políticas y observabilidad | [Fundamentos de eBPF](../basics/05-ebpf-fundamentals.md) · [Cilium](cilium/README.md) · [Calico](calico/README.md) |
| Límites y rendimiento de red de AWS | Aplicar el modelo a rutas en la nube | Conceptos de CNI y habilidades de medición | Identificar límites de VPC, nodo y AZ e interpretar mediciones en contexto | [VPC CNI](01-vpc-cni.md) · [AWS Load Balancer Controller](03-aws-lb-controller.md) · [Conectividad VPC entre organizaciones](05-cross-org-vpc-connectivity.md) · [Benchmark de red de Pod](06-pod-network-benchmark.md) |

## Modelo de redes de Kubernetes

El modelo actual de Kubernetes proporciona una red de Pod en la que los Pods pueden comunicarse directamente entre nodos sin traducción de direcciones ni proxies, **sujeto a una segmentación de red intencional**. Los agentes de nodo como kubelet deben poder alcanzar los Pods de su propio nodo. La política de red, el enrutamiento y los listeners de aplicación aún determinan si una conexión concreta tiene éxito.

Los Pods ordinarios tienen su propio namespace de red y direcciones de todo el clúster; los contenedores en un Pod comparten ese namespace y localhost. Los Pods con red de host comparten la red del nodo, y las configuraciones dual-stack o de múltiples redes requieren un manejo más preciso de direcciones. Recrear un Pod puede asignar una IP distinta; reiniciar un contenedor dentro del mismo Pod no necesariamente recrea su sandbox de red.

| Componente | Función |
|---|---|
| Red de Pod | Direccionamiento y conectividad entre namespaces de red de cargas de trabajo |
| Service/discovery | Nombres de servicio estables o direcciones virtuales sobre endpoints cambiantes |
| Implementación de Ingress/Gateway | Entrada externa configurada y enrutamiento de aplicaciones |
| Motor de política de red | Aplica las políticas admitidas por la implementación seleccionada |

Estas funciones no forman una ruta de paquetes en serie obligatoria. La traducción de Service, un proxy L7 y la política de carga de trabajo pueden cambiar cómo una solicitud concreta atraviesa la red.

### Redes de Pod

Las redes de Pod proporcionan el direccionamiento y las rutas para la comunicación de Pod. La siguiente ilustración muestra Pods IPv4 ordinarios; sus conexiones suponen que las políticas y controles de red aplicables las permiten.

![Rutas directas ilustrativas de Pods IPv4 entre dos nodos, con conectividad sujeta a la política y el enrutamiento configurados.](../.gitbook/assets/en-networking-readme-1.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-1.html)

Las direcciones son direcciones ilustrativas de Pods ordinarios. El aislamiento intencional y las configuraciones con red de host o múltiples redes requieren su propia interpretación.

#### Métodos de implementación de redes de Pod

| Método | Descripción | CNI de ejemplo |
|--------|-------------|-------------|
| **Red superpuesta** | Encapsula tráfico sobre la red existente | Flannel VXLAN, Calico VXLAN/IPIP, Cilium VXLAN/Geneve |
| **Enrutamiento nativo** | Usa rutas en la red subyacente sin esa encapsulación superpuesta | AWS VPC CNI, enrutamiento/BGP de Calico, enrutamiento nativo de Cilium |
| **Encapsulación condicional** | Usa rutas directas o encapsulación según la topología configurada | Modos compatibles de Calico/Flannel/Cilium, con distintos prerrequisitos |

### Redes de Service

Los Services describen un conjunto lógico de endpoints, normalmente Pods, y cómo alcanzarlos. ClusterIP proporciona una IP virtual estable de forma predeterminada; los Services headless omiten esa IP virtual, y ExternalName usa mapeo CNAME de DNS. Un Service también puede tener endpoints administrados sin un selector de Pod.

![Mecanismos de entrada típicos para Services ClusterIP, NodePort, LoadBalancer y ExternalName; el mapeo DNS se distingue del reenvío de paquetes.](../.gitbook/assets/en-networking-readme-2.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-2.html)

Estos son mecanismos de exposición típicos, no garantías de seguridad. El rango de NodePort y las direcciones de nodo accesibles son configurables; los LoadBalancers pueden ser internos. ExternalName devuelve un alias DNS y no crea un proxy de reenvío.

#### Características de los tipos de Service

Cree Pods coincidentes con `app: my-app` en `default`, que escuchen en los puertos destino mostrados. El rango de asignación predeterminado de NodePort es 30000–32767 y se puede configurar. La accesibilidad externa todavía depende de direcciones, rutas y controles de acceso.

El ejemplo de LoadBalancer selecciona explícitamente **AWS Load Balancer Controller**, con destinos de instancias EC2 y NodePorts asignados. Primero instale/configure ese controller y sus prerrequisitos de IAM/subred. EKS Auto Mode usa un controller/clase diferente. El puerto 443 aquí solo selecciona un puerto TCP; el backend debe servir TLS en 8443 o configurarse por separado en el balanceador de carga.

Estos mapeos de puertos ilustran la API general de Kubernetes Service. AWS actualmente documenta requisitos adicionales de política de red nativa de EKS: el puerto de Service debe coincidir con el puerto del contenedor, y los Pods administrados por controller con `metadata.ownerReferences` proporcionan una aplicación confiable. Adapte los ejemplos a esos requisitos antes de probar esa implementación de política.

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

Un recurso Ingress necesita un controller y su plano de datos. Este ejemplo HTTP usa AWS LBC con `spec.ingressClassName: alb` y destinos IP. Los Services referenciados `api-v1`, `api-v2` y `web-frontend` deben existir en `default`, exponer el puerto 80 y tener endpoints de Pod listos y enrutables por VPC. Configure HTTPS/certificados por separado cuando sea necesario. Consulte la [guía de LBC](03-aws-lb-controller.md) para conocer sus prerrequisitos de instalación y destinos.

Ingress define reglas para enrutar tráfico HTTP/HTTPS hacia Services internos del clúster.

![Enrutamiento lógico de host/ruta de Ingress hacia backends de Service y Pods.](../.gitbook/assets/en-networking-readme-3.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-3.html)

El recuadro representa la función del plano de datos de Ingress. AWS LBC programa ALB; el tráfico de la aplicación no atraviesa el proceso de reconciliación del controller. Según el modo de destino, el plano de datos puede alcanzar IP de Pod o NodePorts en lugar de atravesar una IP virtual de Service como un salto adicional literal.

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

CNI estandariza la interfaz mediante la cual un runtime configura una red de contenedor. Para Kubernetes actual, kubelet solicita operaciones de sandbox de Pod mediante CRI y el **runtime de contenedores administra CNI**. Los antiguos indicadores de administración directa de CNI de kubelet se eliminaron en Kubernetes 1.24.

### Responsabilidades de runtime y plugin

| Actor | Responsabilidad |
|---|---|
| kubelet | Solicita creación/eliminación de sandbox mediante la interfaz de runtime de contenedores |
| Runtime de contenedores | Selecciona la configuración de red e invoca la cadena de plugins CNI |
| Plugin CNI | Recibe configuración, ejecuta ADD/DEL y otras operaciones compatibles, y devuelve resultados |
| Implementación de IPAM | Asigna/libera direcciones; puede ser un plugin delegado o parte de un agente específico del proveedor |
| Agente de nodo opcional | Mantiene rutas, política, pools de IP o estado del datapath específicos del proveedor |

El runtime pasa la configuración al plugin mediante la interfaz CNI; no es obligatorio un agente separado de larga ejecución ni un binario IPAM para todos los plugins. Los tipos de interfaz también varían: los pares veth son comunes, pero no son la única implementación.

## Comparación de CNI

| Proyecto / alcance | Redes y política | Características y límites que distinguir |
|---|---|---|
| **Cilium 1.20.1** | Redes eBPF; Envoy para funciones L7 relevantes; políticas de red Cilium y Hubble | Dataplane de worker Linux, con requisitos de AMD64/Arm64. La disponibilidad de CLI de Windows no es compatibilidad con Windows CNI. WireGuard/IPsec y Beta ztunnel mTLS tienen alcances distintos. |
| **Ejemplos de Calico Open Source 3.32.2; 3.33.0 actual** | Opciones de enrutamiento/encapsulación; opciones iptables, nftables y eBPF; niveles de políticas ordenadas y política de host/carga de trabajo | Calico 3.33.0 está probado en Kubernetes 1.35–1.37. Revise sus notas de versión antes de actualizar. Windows tiene límites independientes, incluida la ausencia de dataplane Linux eBPF o WireGuard. La observabilidad de flujos Whisker/Goldmane está disponible como Tech Preview. Consulte la matriz de ediciones para capacidades de pago. |
| **Flannel 0.28.9** | Asignación de subred de host y transporte entre nodos; VXLAN, host-gw y otros backends | `flanneld` no aplica NetworkPolicy por sí mismo; el `netpol.enabled` opcional del gráfico despliega un controller de políticas SIGs. WireGuard es un backend documentado; IPsec es experimental. Windows VXLAN tiene configuraciones/límites específicos. |
| **Ejemplos upstream/Helm de AWS VPC CNI 1.23.0; complemento EKS `v1.23.1-eksbuild.1`** | Asignación de direcciones VPC y ENI/prefijos EC2; capacidades de política de red Standard y Admin de EKS en nodos EC2 Linux compatibles | AWS enumera esta compilación de complemento administrado para Kubernetes 1.31–1.37; verifique la disponibilidad regional y la versión real del clúster. EKS Auto Mode es una implementación de red administrada con capacidades adicionales de política DNS. Windows, Fargate, redes personalizadas, delegación de prefijos y soporte multi-NIC tienen condiciones independientes. |
| **Proyecto original Weave Net** | Implementación histórica de redes superpuestas | El repositorio original `weaveworks/weave` está archivado. No lo describa como una opción predeterminada activa y compatible para un clúster nuevo. |

### Política, cifrado y observabilidad

- Cilium proporciona política con reconocimiento HTTP/DNS mediante los componentes L7 aplicables, y política de todo el clúster/host. Su semántica de denegación/autorización no es la API Tier ordenada de Calico.
- Calico Open Source incluye niveles jerárquicos de política y política de host. La matriz de producto actual asigna política de capa de aplicación, política DNS/FQDN y Cluster Mesh a Cloud/Enterprise; no deben atribuirse silenciosamente a la edición open-source. El cifrado en tránsito documentado de Calico usa WireGuard.
- Amazon EKS proporciona controles Admin/Baseline `ClusterNetworkPolicy` para Auto Mode e instalaciones EC2/VPC-CNI compatibles. La función DNS/FQDN `ApplicationNetworkPolicy` descrita por AWS es para **Auto Mode**. Su nombre no implica inspección actual de métodos/cuerpo HTTP.
- El controller de políticas opcional de Flannel tiene sus propios requisitos; seleccionar solo un backend de red no habilita la aplicación.
- El cifrado de nodo a nodo, la identidad autenticada de carga de trabajo y mTLS de aplicación son controles diferentes. La visibilidad del flujo de red también difiere del tracing de aplicaciones o de la aplicación de procesos/archivos.

### Enrutamiento y rendimiento

Calico y Cilium pueden anunciar rutas mediante BGP; esto por sí solo no proporciona descubrimiento de servicios multiclúster, sincronización de políticas ni cifrado. Flannel host-gw usa rutas directas y requiere conectividad adecuada de capa 2. Una red superpuesta añade encapsulación y consideraciones de MTU, pero no se puede inferir una clasificación de rendimiento universal del nombre de CNI.

La anterior cifra de rendimiento 100/98/95/85/80/75 por ciento no tenía carga de trabajo reproducible, versiones ni fuente de medición. Use hardware, kernel, tamaños de paquete/solicitud, concurrencia, configuración de cifrado/política, rendimiento, pérdida y latencia de cola comparables. El [benchmark de Pod](06-pod-network-benchmark.md) independiente conserva su propio entorno y mediciones históricas.

## Guía de selección de CNI

Elija primero el modelo de enrutamiento, política, sistema operativo y soporte requerido, y luego pruebe esa combinación.

| Necesidad | Ruta de evaluación |
|---|---|
| Direccionamiento VPC estándar de EKS y políticas de red compatibles | Evalúe las capacidades de AWS VPC CNI/EKS antes de añadir un segundo motor de políticas. |
| Niveles de política ordenados, política de host o BGP de infraestructura | Evalúe la edición/dataplane de Calico relevante y los prerrequisitos de enrutamiento. |
| Política Cilium, Hubble o características de mesh seleccionadas | Compruebe la compatibilidad de Linux/kernel/plataforma y la [guía de mesh de Cilium](../service-mesh/cilium-service-mesh/README.md). Envoy sigue formando parte de las rutas L7 aplicables. |
| Una red pequeña con un conjunto limitado de características | Evalúe el backend de Flannel y el controller de políticas opcional frente a los requisitos reales. |
| Aplicación de procesos, syscall o archivos | Evalúe por separado un componente de seguridad de runtime como Tetragon de la política de red. |

### Configuración de complemento administrado de EKS

Lo siguiente es una **carga de configuración** de ejemplo, no una instrucción para instalar Calico y el motor de políticas VPC CNI en las mismas cargas de trabajo:

```json
{
  "enableNetworkPolicy": "true"
}
```

La cadena `"true"` es el tipo documentado para esta configuración. Seleccione una compilación de complemento EKS compatible con la versión existente de Kubernetes e inspeccione el esquema de configuración de esa compilación:

```bash
EKS_REGION=ap-northeast-2
KUBERNETES_MINOR=1.35  # Replace with the existing cluster's minor version
aws eks describe-addon-versions --region "$EKS_REGION" --addon-name vpc-cni \
  --kubernetes-version "$KUBERNETES_MINOR"
: "${VPC_CNI_ADDON_VERSION:?Set the compatible eksbuild version selected from metadata}"
aws eks describe-addon-configuration --region "$EKS_REGION" --addon-name vpc-cni \
  --addon-version "$VPC_CNI_ADDON_VERSION"
```

El número de versión upstream 1.23.0 y una versión EKS `eksbuild` son identificadores distintos. La tabla actual de complementos de AWS enumera `v1.23.1-eksbuild.1` para Kubernetes 1.31–1.37; use `describe-addon-versions` en la Region objetivo para seleccionar una compilación compatible. Combine los cambios con la configuración prevista del complemento administrado; no seleccione ciegamente `latest` ni reemplace valores no relacionados. Una migración desde una implementación de política de terceros también necesita eliminar su estado de aplicación existente y un plan probado de transición de nodo/carga de trabajo.

## Fundamentos de redes de EKS

### Arquitectura de red predeterminada de EKS

| Ubicación / componente | Responsabilidad |
|---|---|
| VPC administrada por EKS | AWS ejecuta el plano de control administrado de Kubernetes entre Availability Zones. |
| VPC de clúster del cliente | Las redes de worker, las subredes seleccionadas y los ENI entre cuentas administrados por EKS proporcionan las rutas configuradas al plano de control. |
| ALB/NLB en subredes de VPC de cliente seleccionadas | Proporciona el punto de entrada de aplicación público o interno elegido; un internet gateway/NAT gateway no sustituye esa configuración de enrutamiento. |
| NAT gateway o endpoints de servicio privados | Proporciona las rutas de salida concretas que requiere el diseño de carga de trabajo. |

La figura anterior ubicaba el plano de control dentro de la VPC del cliente y los balanceadores de carga fuera de ella; se ha sustituido por estos límites de propiedad.

### DNS y redes por modo de cómputo

| Modo de cómputo | Ubicación de DNS / componentes |
|---|---|
| Nodos EC2 Standard | Normalmente usan el Deployment CoreDNS configurado y los componentes de red instalados; los reemplazos necesitan su propia configuración compatible. |
| EKS Auto Mode puro | Las funciones CoreDNS, VPC CNI y kube-proxy se ejecutan como servicios systemd de nodo administrados. Un Deployment/complemento de CoreDNS es innecesario para estos nodos. |
| Auto Mode mezclado con nodos no Auto | Conserve el Deployment CoreDNS para los nodos no Auto; no pueden usar el servicio DNS Auto Mode de otro nodo. |

El primer resolvedor DNS de Auto Mode es local al nodo. El reenvío upstream y la comunicación con el plano de control aún pueden requerir acceso de red; esto no garantiza que todos los paquetes relacionados con DNS permanezcan en el nodo. AWS documenta políticas Admin y DNS para Auto Mode, mientras que la política Admin VPC-CNI de EC2 Standard tiene sus propios requisitos de versión/habilitación.

### Cómo funciona VPC CNI

AWS VPC CNI ofrece a los Pods ordinarios direcciones enrutables por VPC mediante el modo IPAM seleccionado. Las direcciones IPv4 secundarias, prefijos delegados, ENI de rama y configuraciones multi-NIC difieren; los Pods con red de host comparten la red del nodo.

![Asignación ilustrativa de IPv4 secundarias desde ENI EC2 a Pods, incluida una interfaz warm opcional.](../.gitbook/assets/en-networking-readme-9.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-9.html)

Esto representa solo el modo de IP secundaria. Un ENI warm es una estrategia de asignación configurable, no un requisito de que cada nodo reserve siempre exactamente uno. La delegación de prefijos, las redes personalizadas y los ENI de rama tienen reglas de asignación distintas.

#### Límites de ENI e IP

| Tipo de instancia | Máx. ENI | Ranuras IPv4 por ENI | Valor de arranque heredado de IP secundaria |
|---------------|----------|--------------|------------------------|
| t3.medium | 3 | 6 | 17 |
| t3.large | 3 | 12 | 35 |
| m5.large | 3 | 10 | 29 |
| m5.xlarge | 4 | 15 | 58 |
| m5.2xlarge | 4 | 15 | 58 |
| c5.4xlarge | 8 | 30 | 234 |

Estos valores se verifican frente a los límites de instancias de VPC CNI 1.23.0 y la tabla heredada de max-Pods. El cálculo histórico es `ENIs × (IPv4 slots per ENI − 1) + 2`; no es una recomendación universal actual. La delegación de prefijos, las redes personalizadas, los ENI de rama y varias tarjetas de red cambian la capacidad de direcciones. La planificación de Kubernetes también está limitada por `maxPods` de kubelet y los recursos. Los grupos de nodos administrados por EKS limitan `maxPods` a 110 para instancias con menos de 30 vCPU y a 250 en caso contrario; el número de IP disponibles por sí solo no anula ese límite.

### Consideraciones de redes de EKS

#### Administración de direcciones IP

Para **Linux VPC CNI**, configure las variables de entorno documentadas mediante el mecanismo de administración de complemento/Helm/DaemonSet seleccionado. Lo siguiente es un fragmento de configuración de complemento de EKS. El antiguo ConfigMap `amazon-vpc-cni` con `enable-prefix-delegation` no configura Linux IPAMD de esta manera. Conserve otros valores previstos del complemento al aplicar un cambio.

```json
{
  "env": {
    "ENABLE_PREFIX_DELEGATION": "true",
    "WARM_PREFIX_TARGET": "1"
  }
}
```

Como alternativa, ajuste el mínimo total de asignación y el objetivo de IP libres. Cuando se configura `MINIMUM_IP_TARGET` o `WARM_IP_TARGET`, tiene prioridad sobre `WARM_PREFIX_TARGET`; son políticas alternativas en vez de cuatro objetivos aditivos independientes. La asignación aún ocurre en unidades del tamaño del prefijo. El soporte Nitro, espacio `/28` contiguo para IPv4 y un límite de Pod kubelet adecuado son prerrequisitos independientes.

La asignación de prefijos de Windows es una ruta de configuración distinta: AWS documenta `enable-windows-prefix-delegation` y sus claves de objetivo warm en el ConfigMap `amazon-vpc-cni`. No copie sin cambios el procedimiento de variables de entorno de Linux a Windows.

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

Estos ejemplos IPv4 requieren ID reales de subred/grupo de seguridad en la AZ y VPC previstas. Habilite las redes personalizadas y seleccione el ENIConfig de cada nodo mediante su etiqueta de zona. Una anotación explícita de nodo ENIConfig tiene prioridad sobre esa etiqueta. Los nombres de ejemplo siguientes usan la misma región en ambos idiomas; reemplácelos por las zonas reales del nodo. Instalar objetos ENIConfig por sí solo no activa las redes personalizadas.

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

Los elementos siguientes se mencionan de pasada en otras partes de esta descripción general. Los procedimientos completos de configuración y las cifras medidas se encuentran en las páginas de profundización vinculadas; esta sección organiza cómo difieren estas piezas por capa y dónde encaja cada una.

### L2–L7 y la diferencia entre routers y balanceadores de carga

"Router" y "load balancer" suelen aparecer en la misma frase, pero responden preguntas distintas. Un router elige (en general) una ruta a un único destino; un load balancer elige un destino entre varios candidatos equivalentes mediante un algoritmo de distribución.

| Capa | Dispositivo/función | Base de decisión | Mapeo Kubernetes/AWS |
|---|---|---|---|
| L2 (enlace) | Switch, bridge | Dirección MAC de destino | pares veth y bridges Linux creados por el CNI, la NIC virtual que expone un ENI |
| L3 (red) | Router o inserción transparente de appliance | IP de destino para enrutamiento; identidad de flujo para selección de appliance | Router implícito de VPC, TGW; GWLB encapsula paquetes IP para appliances |
| L4 (transporte) | Balanceador de carga L4 | Identidad de conexión/flujo, normalmente la 5-tupla | NLB; kube-proxy (iptables, IPVS, nftables); implementaciones independientes eBPF de Service |
| L7 (aplicación) | Balanceador de carga/proxy inverso L7 | Host, ruta, headers por solicitud; reconoce protocolos | ALB, implementaciones de Ingress/Gateway API, sidecars de service mesh (Envoy) |

La diferencia clave es la **unidad de distribución**. Un balanceador de carga L4 normalmente selecciona un destino para una conexión TCP o un flujo UDP rastreado. Un proxy L7 puede seleccionar un destino para cada solicitud de aplicación compatible, incluidas solicitudes que comparten una conexión. GWLB distribuye flujos IP encapsulados entre appliances de seguridad en lugar de analizar solicitudes de aplicación. La afinidad de flujo depende de la configuración de timeout, salud y failover; no garantiza que un flujo nunca pueda reasignarse o interrumpirse.

> 📎 Las definiciones de nivel de protocolo de conceptos L2/L3 están en [Fundamentos de red Parte 1](../basics/06-network-fundamentals-part1.md); los tipos de destino ALB/NLB y la configuración real están en [AWS Load Balancer Controller](03-aws-lb-controller.md).

### Conectividad entre cuentas/VPC: TGW, VPC Peering, GWLB, PrivateLink, Lattice

Estas cinco opciones de conectividad difieren en capa y modelo de tráfico. La latencia medida entre compartición TGW RAM, VPC Peering, PrivateLink, TGW Peering y VPC Lattice se encuentra en [Conectividad VPC entre organizaciones](05-cross-org-vpc-connectivity.md). Esta sección añade GWLB, que no está en esa tabla comparativa, y replantea las cinco por capa.

| Conectividad | Capa/modelo | Características |
|---|---|---|
| VPC Peering | L3, enrutamiento IP bidireccional | No transitivo; no se puede configurar entre CIDR superpuestos |
| Transit Gateway (TGW) | L3, enrutamiento IP hub-and-spoke | Usa asociaciones de attachment y propagación entre una o más tablas de rutas TGW; compartido entre cuentas mediante RAM |
| Gateway Load Balancer (GWLB) | L3, inserción transparente de appliance | Encapsula el paquete original en GENEVE (UDP 6081); un modelo de servicio de endpoint VPC conecta el tráfico del consumidor con la flota de appliances del proveedor |
| PrivateLink | Conectividad de endpoint privado | Un servicio de endpoint respaldado por NLB es un modelo; también existen endpoints de recursos. Los CIDR de consumidor/proveedor pueden superponerse |
| VPC Lattice | Redes de aplicaciones y recursos | Los servicios HTTP/HTTPS admiten enrutamiento L7 y autorización IAM opcional; TLS passthrough y las configuraciones de recursos tienen capacidades distintas |

GWLB inserta appliances de inspección como firewalls e IDS/IPS en una ruta IP mediante un endpoint Gateway Load Balancer. Su afinidad de flujo predeterminada usa cinco campos; las configuraciones compatibles pueden usar dos o tres en su lugar. Valide las rutas de ida y retorno, la salud de appliance, la MTU de encapsulación, NACL y los grupos de seguridad de las cargas de trabajo/appliances reales. GWLB no tiene por sí mismo un grupo de seguridad al estilo ALB, y la afinidad de flujo no sustituye las pruebas de fallos.

> 📎 La integración completa EKS/VPC Lattice (Gateway API Controller, autorización IAM, enrutamiento) está en [VPC Lattice](02-vpc-lattice.md).

### Cómo se comportan realmente el resolvedor DNS y las tablas de rutas

**Resolvedor DNS:** AmazonProvidedDNS **es Route 53 Resolver**. Sus direcciones incluyen la dirección de red IPv4 primaria de VPC más dos (`10.0.0.2` para `10.0.0.0/16`) y `169.254.169.253`; resuelve zonas privadas asociadas y nombres públicos según las reglas de Resolver. CoreDNS normalmente sirve el dominio de clúster Kubernetes configurado, a menudo `cluster.local`; `kube-dns` es su nombre de Service, no un namespace ni zona DNS. El reenvío externo sigue el Corefile y el archivo del resolvedor visible para el Pod DNS. Inspeccione esos ajustes en lugar de suponer que el archivo de resolvedor del nodo se usa sin cambios. En un diseño de endpoint Resolver, los endpoints entrantes aceptan consultas on-premises, mientras que los endpoints salientes y las reglas asociadas reenvían consultas VPC seleccionadas al DNS on-premises. El resolvedor local al nodo de Auto Mode no elimina las dependencias upstream.

**Tablas de rutas:** La evaluación de rutas de VPC generalmente usa coincidencia de prefijo más largo. AWS permite reemplazar el destino de una ruta `local` y añadir rutas de subred más específicas compatibles para enrutamiento de appliance; `local` no es incondicionalmente la ruta más específica. Para destinos idénticos, las rutas VPC estáticas tienen prioridad sobre las rutas propagadas desde un virtual private gateway. Una ruta VPC que se dirige a un TGW es estática; la propagación dentro de un TGW pertenece a sus tablas de rutas independientes. Los destinos no válidos pueden dejar entradas `blackhole` que descartan tráfico, por lo que inspeccione el estado de la ruta además del destino. Una subred sin asociación explícita de tabla de rutas usa la tabla de rutas principal de la VPC.

> 📎 La prioridad de rutas TGW/Peering y ejemplos de configuración de rutas estáticas están en los [hallazgos operativos de Conectividad VPC entre organizaciones](05-cross-org-vpc-connectivity.md#operational-findings).

### El plano de datos del kernel: iptables, IPVS, eBPF y filtrado de paquetes

El reenvío de Service de Linux y la aplicación de políticas de red pueden usar mecanismos distintos. Netfilter proporciona hooks de ruta de paquetes utilizados por iptables y nftables. Las implementaciones eBPF pueden adjuntarse en hooks XDP, tc o socket y realizar selección de Service allí. Esto no significa que cada paquete de un clúster habilitado para eBPF omita Netfilter o el seguimiento de conexiones; la ruta depende del CNI, kernel, enrutamiento y configuración de características.

| Implementación | Dónde se ubica | Características |
|---|---|---|
| iptables | Cadenas de reglas secuenciales en hooks netfilter | El tiempo de evaluación escala con el número de reglas (O(n)); modo predeterminado histórico de kube-proxy |
| IPVS | Balanceador de carga L4 nativo del kernel, extensión netfilter | Búsqueda basada en hash (casi O(1)); obsoleto como modo kube-proxy a partir de Kubernetes 1.35 |
| nftables | Marco sucesor de netfilter para iptables | Modo estable de kube-proxy desde 1.33; compruebe primero la compatibilidad de kernel/CNI |
| eBPF (p. ej., Cilium) | Hooks XDP, tc y socket configurados | Puede reemplazar el manejo de Service de kube-proxy; es una implementación independiente, con comportamiento Netfilter/conntrack específico de la ruta |

Cambiar implementaciones puede dejar reglas de kernel y conexiones activas. Siga el procedimiento de migración de distribución/CNI, drene las cargas de trabajo según sea necesario y planifique reinicios de nodo cuando la limpieza los requiera. Reemplazar kube-proxy por un CNI basado en eBPF también exige un orden de transición compatible para que las implementaciones no compitan por el mismo tráfico de Service.

> 📎 La cronología de obsolescencia de IPVS y la transición estable a nftables se tratan en [Introducción a Kubernetes](../basics/04-kubernetes-introduction.md); el reemplazo eBPF de kube-proxy de Cilium está en [Cilium eBPF](cilium/02-ebpf.md); el plano de datos eBPF de Calico y su procedimiento de migración están en [Calico eBPF](calico/06-ebpf-dataplane.md).

### Redes intensivas en cómputo: ENI, EFA, NVLink y transceptores ópticos

ENI, EFA y NVLink sirven rutas distintas. Un **ENI** es una interfaz de red virtual adjunta a una instancia EC2 en una Availability Zone; su tráfico IP normal puede alcanzar otras AZ y VPC conectadas cuando el enrutamiento y la política lo permiten (consulte [VPC CNI](01-vpc-cni.md)). **EFA** proporciona un dispositivo de omisión del SO usado mediante libfabric por software MPI/NCCL compatible. **El tráfico de dispositivo EFA no es enrutable y no puede cruzar límites de VPC/AZ**; el tráfico IP normal mediante el dispositivo ENA de una interfaz EFA-with-ENA sigue siendo enrutable. Las interfaces solo EFA no tienen dispositivo ENA ni direccionamiento IP. **NVLink** conecta GPU dentro de sistemas compatibles, incluidos dominios NVLink de escala rack compatibles. Mida el hardware seleccionado, las operaciones colectivas y la ubicación en vez de suponer una aceleración fija sobre EFA.

Los **transceptores ópticos** son un concepto general de redes de centros de datos. Los cables DAC (Direct Attach Copper) son adecuados para tramos cortos; los módulos ópticos y la fibra admiten otros requisitos de alcance y ancho de banda. QSFP y OSFP describen factores de forma de módulo, no una garantía de medio óptico. Trate esto como información general: no establece el cableado físico de una carga de trabajo AWS concreta.

> 📎 La programación consciente de topología NVLink/IMEX y los ejemplos de ubicación de GPU Pod están en [Infraestructura de AI/ML](../ai-ml/06-ai-infrastructure.md); la restricción de límites VPC/AZ de EFA y las mediciones están en [Conectividad VPC entre organizaciones](05-cross-org-vpc-connectivity.md).

### Qué significan los protocolos de próxima generación para Kubernetes: HTTP/3, gRPC, QUIC

La mecánica de protocolo de HTTP/3 (RFC 9114) y su transporte QUIC (RFC 9000) se tratan en [Fundamentos de red Parte 2](../basics/06-network-fundamentals-part2.md) y [Parte 3](../basics/06-network-fundamentals-part3.md). Aquí solo cubrimos lo que realmente afecta a la distribución de tráfico de Kubernetes.

- **gRPC y balanceadores de carga L4:** gRPC multiplexa solicitudes sobre conexiones HTTP/2. Un balanceador L4 normalmente mantiene una conexión TCP establecida en su endpoint seleccionado; si ese endpoint es un proxy, puede tomar más decisiones de enrutamiento. Añadir Pods por sí solo no redistribuye conexiones existentes. La distribución por RPC requiere un proxy L7 compatible o una política del lado del cliente. Un RPC de streaming sigue siendo una llamada; sus mensajes individuales no se equilibran de forma independiente.
- **GRPCRoute de Gateway API:** Ingress no tiene un recurso específico para gRPC, pero Gateway API estandariza el enrutamiento de nivel servicio/método con `GRPCRoute`. La compatibilidad varía según la implementación (cuántas coincidencias de header, políticas de reintento, etc.), por lo que consulte la documentación del propio controller.
- **Hasta dónde llega realmente HTTP/3/QUIC dentro del clúster:** El soporte HTTP/3 entre un cliente y el borde (un CDN, un balanceador de carga) es una cuestión independiente del soporte HTTP/3 dentro del clúster o en la conexión backend de un Ingress. Muchas implementaciones de Ingress/Gateway aún hablan HTTP/1.1 o HTTP/2 con el backend, y si se admite HTTP/3 de extremo a extremo varía según implementación y versión — no generalice; consulte la documentación del controller realmente en uso.

## Subpáginas de redes

Esta sección abarca en detalle los siguientes temas:

### [Redes de Linux desde el principio](beginner/README.md) {#beginner-course}

Si es nuevo en Linux o redes, comience con el [curso para principiantes](beginner/README.md). Sus ocho lecciones conectan la CLI, direccionamiento, DNS, SSH, firewalls, monitoreo y un proyecto final. La ruta siguiente extiende esa base hacia protocolos, el kernel e implementaciones de clúster.

### [Ruta de redes experta](expert/README.md) {#expert-course}

Después del curso para principiantes, utilice la [ruta de redes experta](expert/README.md) para conectar proyectos de protocolos, políticas de enrutamiento, EVPN, rendimiento de Linux, diseño de nube y evaluación de automatización. Primero compruebe los criterios de entorno, evidencia y recuperación de cada cuaderno.

### [Práctica de diagnósticos de red de Linux](07-linux-network-diagnostics.md) {#linux-network-diagnostics}

Conecte los [conceptos de socket y ruta de paquetes del kernel](../kernel/02-network-stack.md) con observaciones antes de estudiar implementaciones de CNI. Use el [cuestionario de diagnósticos](../quizzes/networking/07-linux-network-diagnostics-quiz.md) para comprobar su interpretación.

### [VPC CNI](01-vpc-cni.md)
Redes de EKS con direcciones VPC para Pods ordinarios y prerrequisitos de IPAM/política específicos del modo.

### [Profundización en Cilium](cilium/README.md)
Solución CNI de alto rendimiento basada en eBPF. Proporciona características avanzadas como Network Policy L7, Service Mesh y observabilidad (Hubble).

### [Profundización en Calico](calico/README.md)
Uno de los CNI más usados. Potente Network Policy, soporte BGP y características empresariales. Abarca introducción, arquitectura, modos de red, profundización en BGP, Network Policy, eBPF, temas avanzados, integración de EKS y guía de operaciones.

### [VPC Lattice](02-vpc-lattice.md)
Servicio administrado de redes de aplicaciones de AWS. Comunicación servicio a servicio entre VPC y cuentas.

### [AWS Load Balancer Controller](03-aws-lb-controller.md)
Integra Services e Ingress de Kubernetes con AWS ELB (ALB/NLB).

### [Gateway API](04-gateway-api.md)
API ingress de Kubernetes de próxima generación. Modelo de recursos estandarizado y configuración basada en roles.

### [Benchmark de red de Pod](06-pod-network-benchmark.md)
RTT de Pod a Pod, latencia HTTP y rendimiento medidos en EKS para el mismo nodo, la misma AZ y entre AZ, además de amplificación de consultas DNS `ndots:5`.

## Solución de problemas de red

### Problemas y soluciones habituales

#### Fallo de comunicación de Pod a Pod

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

Ejecute diagnósticos desde un Pod existente con las herramientas indicadas. Consulte solo el CNI instalado en el clúster; los servicios del sistema Auto Mode no son esos DaemonSets. El éxito DNS, la accesibilidad TCP y una respuesta HTTP de aplicación son comprobaciones distintas. ICMP puede estar bloqueado o requerir privilegios adicionales, por lo que un ping fallido por sí solo no prueba que un servicio TCP sea inalcanzable.

#### Service inalcanzable

```bash
NAMESPACE=default
SERVICE_NAME=my-service
kubectl -n "$NAMESPACE" get service "$SERVICE_NAME" -o yaml
kubectl -n "$NAMESPACE" get endpointslices \
  -l "kubernetes.io/service-name=$SERVICE_NAME" -o yaml
kubectl -n kube-system logs -l k8s-app=kube-proxy --tail=100
```

Use EndpointSlice para el diagnóstico actual de endpoints. Compruebe selectores de Service, puertos destino, disponibilidad de endpoint, familia de direcciones y política aplicable. Inspeccione los logs de kube-proxy solo si ese componente realmente posee el reenvío de Service; un reemplazo eBPF o Auto Mode requiere sus propios diagnósticos.

#### Depuración de Network Policy

```bash
kubectl get networkpolicies.networking.k8s.io -A
kubectl -n kube-system exec ds/cilium -c cilium-agent -- cilium-dbg policy get
kubectl -n kube-system exec ds/cilium -c cilium-agent -- cilium-dbg endpoint list
# For a Calico installation using its standard CRD datastore:
kubectl get networkpolicies.crd.projectcalico.org -A
kubectl get globalnetworkpolicies.crd.projectcalico.org
```

Los comandos de Cilium inspeccionan un Agent seleccionado por la referencia DaemonSet; elija el Agent del nodo afectado al rastrear un incidente. Las instalaciones con API nativa de Calico pueden exponer un grupo de API distinto, por lo que inspeccione los recursos servidos por la instalación. Las políticas de extensión de Kubernetes, Calico y AWS son recursos distintos y pueden tener precedencia diferente.

### Pruebas de rendimiento de red

Este ejercicio TCP acotado usa el índice de imagen Netshoot v0.16 fijado por el editor, que contiene imágenes Linux AMD64 y Arm64; su Dockerfile incluye `iperf3`. Cree estos Pods en un entorno de prueba donde se permita TCP 5201. Es una carga de trabajo ilustrativa, no una comparación medida de CNI.

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

El cliente duerme una hora y el comando limita el tráfico ofrecido a 10 Mbit/s durante diez segundos. Esto prueba la ruta seleccionada, no el rendimiento máximo. Registre la ubicación real de Pod/nodo/AZ, los límites de recursos y la política antes de interpretar resultados. Elija herramientas específicas de Windows para nodos Windows. Elimine solo los recursos de prueba que creó al finalizar.

Estos Pods de diagnóstico independientes son para pruebas de conectividad. Para pruebas de aplicación nativa de políticas de red de EKS, use Pods administrados por Deployment/Job y los requisitos documentados de puerto de Service/contenedor.

## Prácticas recomendadas

### 1. Planificación de direcciones IP

- Diseñe bloques CIDR suficientemente grandes
- Separe la red de Pod de la red de Service
- Diseñe subredes considerando expansión futura

### 2. Aplicar políticas de red

Cree el namespace aislado `networking-demo` antes de usar este ejemplo. Selecciona cada Pod allí y aísla tanto ingress como egress bajo la semántica estándar Kubernetes NetworkPolicy; los flujos DNS y de aplicación requeridos necesitan reglas explícitas de autorización. La aplicación requiere un motor de políticas compatible. Las API adicionales de política de clúster/admin pueden alterar la precedencia, y este único manifiesto no es una arquitectura completa de confianza cero.

- Aplique políticas de denegación predeterminada (Zero Trust)
- Autorice explícitamente solo el tráfico necesario
- Aísle namespaces

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

### 3. Optimización de rendimiento

- Elija un CNI apropiado (que coincida con la carga de trabajo)
- Optimización de MTU
- Ajuste de parámetros del kernel

### 4. Fortalecimiento de seguridad

- Seleccione cifrado de transporte compatible y verifique qué tráfico cubre.
- Configure identidad de carga de trabajo/aplicación y mTLS cuando sea necesario; manténgalos separados de las listas de autorización basadas en DNS/IP.
- Revise con regularidad los cambios de política, certificados y control de acceso.

### 5. Garantizar la observabilidad

- Recopile métricas de red
- Habilite logs de flujo
- Implemente tracing distribuido

## Pasos siguientes

Después del [curso para principiantes](beginner/README.md), continúe con la [Pila de redes del kernel](../kernel/02-network-stack.md), después con la [Práctica de diagnósticos de red de Linux](07-linux-network-diagnostics.md) y su [cuestionario](../quizzes/networking/07-linux-network-diagnostics-quiz.md). La [ruta de aprendizaje](#learning-path) conecta estas bases con contenedores y Services antes de los temas CNI y AWS siguientes.

1. [VPC CNI](01-vpc-cni.md) - CNI predeterminado de EKS
2. [Profundización en Cilium](cilium/README.md) - Redes basadas en eBPF
3. [Profundización en Calico](calico/README.md) - Enrutamiento, política y dataplanes
4. [VPC Lattice](02-vpc-lattice.md) - Redes administradas de AWS
5. [AWS Load Balancer Controller](03-aws-lb-controller.md) - Integración ELB
6. [Gateway API](04-gateway-api.md) - Ingress de próxima generación
7. [Conectividad VPC entre organizaciones](05-cross-org-vpc-connectivity.md) - Conectar VPC entre AWS Organizations (verificado en campo)
8. [Benchmark de red de Pod](06-pod-network-benchmark.md) - Latencia y rendimiento medidos por límite de nodo/AZ

---

## Referencias

- [Modelo de red de Kubernetes](https://kubernetes.io/docs/concepts/services-networking/)
- [Kubernetes Services](https://kubernetes.io/docs/concepts/services-networking/service/)
- [Runtime de contenedores y CNI](https://kubernetes.io/docs/concepts/extend-kubernetes/compute-storage-net/network-plugins/)
- [Kubernetes NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Especificación CNI](https://raw.githubusercontent.com/containernetworking/cni/main/SPEC.md)
- [Ediciones de producto Calico](https://docs.tigera.io/calico/latest/about)
- [Versión Calico Open Source 3.33.0](https://github.com/projectcalico/calico/releases/tag/v3.33.0)
- [Niveles de política Calico](https://docs.tigera.io/calico/latest/network-policy/policy-tiers/tiered-policy)
- [Logs de flujo Calico Whisker](https://docs.tigera.io/calico/latest/observability/view-flow-logs)
- [Limitaciones de Calico Windows](https://docs.tigera.io/calico/latest/getting-started/kubernetes/windows-calico/limitations)
- [Redes y política de Flannel 0.28.9](https://raw.githubusercontent.com/flannel-io/flannel/v0.28.9/README.md)
- [Backends de Flannel](https://raw.githubusercontent.com/flannel-io/flannel/v0.28.9/Documentation/backends.md)
- [Estado del repositorio original Weave](https://api.github.com/repos/weaveworks/weave)
- [AWS VPC CNI 1.23.0](https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.23.0/README.md)
- [Últimas versiones de complemento AWS VPC CNI para EKS](https://docs.aws.amazon.com/eks/latest/userguide/managing-vpc-cni.html)
- [Configuración de política de red de EKS](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy-configure.html)
- [Políticas de red Standard y Admin de EKS](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html)
- [Delegación de prefijos y maxPods de EKS](https://docs.aws.amazon.com/eks/latest/userguide/cni-increase-ip-addresses-procedure.html)
- [Modelos de implementación de políticas Admin y DNS de EKS](https://aws.amazon.com/blogs/containers/enhance-amazon-eks-network-security-posture-with-dns-and-admin-network-policies/)
- [Redes EKS Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/auto-networking.html)
- [Requisitos de complementos EKS](https://docs.aws.amazon.com/eks/latest/userguide/workloads-add-ons-available-eks.html)
- [Arquitectura de plano de control de EKS](https://docs.aws.amazon.com/eks/latest/best-practices/control-plane.html)
- [Metadatos de imagen Netshoot v0.16](https://hub.docker.com/v2/repositories/nicolaka/netshoot/tags/v0.16)
- [Dockerfile de Netshoot v0.16](https://raw.githubusercontent.com/nicolaka/netshoot/v0.16/Dockerfile)
- [Seguridad de runtime Tetragon](https://tetragon.io/docs/overview/)
- [Configuración AWS LBC 3.5 NLB](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/docs/guide/service/nlb.md)
- [Configuración AWS LBC 3.5 Ingress](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/docs/guide/ingress/annotations.md)
- [Conceptos de Gateway Load Balancer](https://docs.aws.amazon.com/vpc/latest/privatelink/gateway-load-balancers.html)
- [Encapsulación GENEVE (RFC 8926)](https://www.rfc-editor.org/rfc/rfc8926)
- [Resolvedor DNS de VPC](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-dns.html)
- [Endpoints y reglas Route 53 Resolver](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver.html)
- [Orden de evaluación de tabla de rutas VPC](https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Route_Tables.html)
- [Rutas locales y rutas de subred más específicas](https://docs.aws.amazon.com/vpc/latest/userguide/subnet-route-tables.html)
- [Prioridad de ruta estática y propagada](https://docs.aws.amazon.com/vpc/latest/userguide/route-tables-priority.html)
- [Direcciones y comportamiento de AmazonProvidedDNS](https://docs.aws.amazon.com/vpc/latest/userguide/AmazonDNS-concepts.html)
- [Afinidad de flujo y failover de GWLB](https://docs.aws.amazon.com/elasticloadbalancing/latest/gateway/edit-target-group-attributes.html)
- [IP virtuales de Kubernetes Service y modos kube-proxy](https://kubernetes.io/docs/reference/networking/virtual-ips/)
- [Nombres de Service CoreDNS y configuración de reenvío](https://kubernetes.io/docs/tasks/administer-cluster/dns-custom-nameservers/)
- [Endpoints de recursos PrivateLink](https://docs.aws.amazon.com/vpc/latest/privatelink/privatelink-access-resources.html)
- [Documentación del proyecto Netfilter/iptables](https://www.netfilter.org/documentation/index.html)
- [Elastic Fabric Adapter EC2](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/efa.html)
- [Protocolo de transporte QUIC (RFC 9000)](https://www.rfc-editor.org/rfc/rfc9000)
- [HTTP/3 (RFC 9114)](https://www.rfc-editor.org/rfc/rfc9114)
- [gRPC sobre HTTP/2 y balanceo de carga](https://grpc.io/blog/grpc-load-balancing/)
- [Gateway API GRPCRoute](https://gateway-api.sigs.k8s.io/guides/user-guides/grpc-routing/)
