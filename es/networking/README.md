# Redes de Kubernetes

> **Última actualización**: 16 de octubre de 2026
>
> **Ejemplos fijados**: Cilium 1.20.3, Calico Open Source 3.32.2, Flannel 0.28.10 y VPC CNI/Helm chart de AWS upstream 1.23.2.
>
> **Información sobre las versiones actuales**: AWS incluye el complemento de VPC CNI administrado por EKS `v1.23.1-eksbuild.1` para Kubernetes 1.31–1.37. Calico 3.33.0 es la versión más reciente de Open Source y se prueba en Kubernetes 1.35–1.37. Revisa sus notas de la versión antes de cambiar los ejemplos fijados.
>
> Estas versiones no constituyen una configuración de clúster probada en conjunto. Comprueba la matriz de Kubernetes/plataforma de cada producto antes de instalarlo.

## Descripción general

Las redes de Kubernetes son la capa de infraestructura fundamental que permite la comunicación entre aplicaciones en contenedores. En esta sección se cubre todo, desde los conceptos básicos de redes de Kubernetes hasta las soluciones CNI (Container Network Interface) avanzadas y los patrones de red en entornos AWS EKS.

## Ruta de aprendizaje {#learning-path}

Después del curso para principiantes, usa la [ruta avanzada de redes](expert/README.md) para conectar proyectos de protocolos, políticas de enrutamiento, EVPN, rendimiento de Linux, diseño de la nube y evaluación de automatización. Comprueba primero el entorno, las evidencias y los criterios de recuperación de cada cuaderno de trabajo.

Si estás empezando con Linux o las redes, comienza con el [curso para principiantes](beginner/README.md). Sus ocho lecciones conectan la CLI, el direccionamiento, DNS, SSH, los firewalls, la monitorización y un proyecto final. La ruta siguiente amplía esos fundamentos con protocolos, el kernel e implementaciones de clústeres.

Avanza desde los conceptos de protocolos hasta las observaciones y, después, relaciónalos con las responsabilidades de los contenedores, los clústeres y la nube. Usa los requisitos previos para elegir un punto de partida y los resultados esperados para comprobar que comprendes el tema antes de continuar.

| Etapa | Función | Requisitos previos | Resultado | Leer / practicar |
|---|---|---|---|---|
| Protocolos, direccionamiento, HTTP | Establecer el vocabulario | Uso básico de la línea de comandos | Seguir una solicitud y distinguir el direccionamiento, el transporte y el comportamiento de la aplicación | Fundamentos de redes [Parte 1](../basics/06-network-fundamentals-part1.md), [Parte 2](../basics/06-network-fundamentals-part2.md), [Parte 3](../basics/06-network-fundamentals-part3.md), [Parte 4](../basics/06-network-fundamentals-part4.md) |
| Sockets de Linux, VFS, rutas de paquetes | Relacionar las API con el kernel | Fundamentos de TCP/IP | Distinguir los FD, los búferes de sockets, las ventanas y las colas | [Pila de redes del kernel](../kernel/02-network-stack.md) |
| Diagnóstico de redes de Linux | Poner a prueba hipótesis con evidencias | Conceptos de sockets y rutas de paquetes | Correlacionar observaciones de sockets, paquetes y aplicaciones | [Práctica de diagnóstico](07-linux-network-diagnostics.md) · [Cuestionario](../quizzes/networking/07-linux-network-diagnostics-quiz.md) |
| Redes de Docker y contenedores | Localizar los límites de los espacios de nombres | Rutas de paquetes de Linux y diagnóstico básico | Explicar las redes de puente, los puertos publicados y la resolución de nombres de contenedores | [Tecnología de contenedores](../basics/03-container-technology.md) |
| Service, DNS e Ingress de Kubernetes | Mapear las abstracciones del clúster | Redes de contenedores | Seguir un nombre a través de un Service hasta sus endpoints e identificar la función de Ingress | [Services y redes](../core/03-services-networking.md) · [Laboratorio](../labs/core/03-services-networking-lab.md) |
| eBPF, CNI y políticas | Comparar las responsabilidades de implementación | Rutas de Pod y Service | Distinguir el reenvío de paquetes, la aplicación de políticas y la observabilidad | [Fundamentos de eBPF](../basics/05-ebpf-fundamentals.md) · [Cilium](cilium/README.md) · [Calico](calico/README.md) |
| Límites de red y rendimiento de AWS | Aplicar el modelo a las rutas de la nube | Conceptos de CNI y habilidades de medición | Identificar los límites de VPC, nodo y AZ e interpretar las mediciones en contexto | [VPC CNI](01-vpc-cni.md) · [AWS Load Balancer Controller](03-aws-lb-controller.md) · [Conectividad de VPC entre organizaciones](05-cross-org-vpc-connectivity.md) · [Evaluación comparativa de redes de Pod](06-pod-network-benchmark.md) |

## Modelo de redes de Kubernetes

El modelo actual de Kubernetes proporciona una red de Pod en la que los Pods pueden comunicarse directamente entre nodos sin traducción de direcciones ni proxies, **sujeto a una segmentación de red intencional**. Los agentes de nodo, como kubelet, deben poder acceder a los Pods de su propio nodo. Las políticas de red, el enrutamiento y los listeners de las aplicaciones siguen determinando si una conexión concreta se establece correctamente.

Los Pods ordinarios tienen su propio espacio de nombres de red y direcciones en todo el clúster; los contenedores de un mismo Pod comparten ese espacio de nombres y localhost. Los Pods que usan la red del host comparten la red del nodo, y las configuraciones de doble pila o de varias redes requieren un tratamiento más preciso de las direcciones. Al recrear un Pod se le puede asignar una IP distinta; reiniciar un contenedor dentro del mismo Pod no recrea necesariamente su entorno aislado de red.

| Componente | Función |
|---|---|
| Red de Pod | Direccionamiento y conectividad entre los espacios de nombres de red de las cargas de trabajo |
| Service/detección | Nombres de servicio estables o direcciones virtuales sobre endpoints cambiantes |
| Implementación de Ingress/Gateway | Punto de entrada externo configurado y enrutamiento de aplicaciones |
| Motor de políticas de red | Aplica las políticas que admite la implementación seleccionada |

Estas funciones no conforman una ruta serial obligatoria para los paquetes. La traducción de Service, un proxy L7 y las políticas de las cargas de trabajo pueden cambiar la forma en que una solicitud concreta atraviesa la red.

### Redes de Pod

Las redes de Pod proporcionan el direccionamiento y las rutas para la comunicación entre Pods. La ilustración siguiente muestra Pods IPv4 ordinarios; las conexiones presuponen que las políticas y los controles de red aplicables permiten el tráfico.

![Rutas IPv4 directas ilustrativas entre Pods de dos nodos; la conectividad está sujeta a las políticas y el enrutamiento configurados.](../.gitbook/assets/en-networking-readme-1.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-1.html)

Las direcciones son direcciones ilustrativas de Pods ordinarios. El aislamiento intencional y las configuraciones que usan la red del host o varias redes requieren una interpretación propia.

#### Métodos de implementación de redes de Pod

| Método | Descripción | Ejemplo de CNI |
|--------|-------------|-------------|
| **Red superpuesta** | Encapsula el tráfico sobre la red existente | Flannel VXLAN, Calico VXLAN/IPIP, Cilium VXLAN/Geneve |
| **Enrutamiento nativo** | Usa rutas de la red subyacente sin esa encapsulación superpuesta | AWS VPC CNI, enrutamiento/BGP de Calico, enrutamiento nativo de Cilium |
| **Encapsulación condicional** | Usa rutas directas o encapsulación según la topología configurada | Modos compatibles de Calico/Flannel/Cilium, con distintos requisitos previos |

### Redes de Service

Los Services describen un conjunto lógico de endpoints, normalmente Pods, y cómo acceder a ellos. ClusterIP proporciona de forma predeterminada una IP virtual estable; los Services sin cabecera omiten esa IP virtual y ExternalName usa una asignación DNS CNAME. Un Service también puede tener endpoints administrados sin un selector de Pod.

![Mecanismos habituales de entrada para Services ClusterIP, NodePort, LoadBalancer y ExternalName; se distingue la asignación DNS del reenvío de paquetes.](../.gitbook/assets/en-networking-readme-2.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-2.html)

Estos son mecanismos habituales de exposición, no garantías de seguridad. El rango de NodePort y las direcciones de nodo accesibles se pueden configurar; los LoadBalancer pueden ser internos. ExternalName devuelve un alias DNS y no crea un proxy de reenvío.

#### Características de los tipos de Service

Crea Pods `app: my-app` coincidentes en `default`, que escuchen en los puertos de destino mostrados. El rango de asignación predeterminado de NodePort es 30000–32767 y se puede configurar. La accesibilidad externa sigue dependiendo de las direcciones, las rutas y los controles de acceso.

El ejemplo de LoadBalancer selecciona explícitamente **AWS Load Balancer Controller**, con destinos de instancias EC2 y NodePorts asignados. Instala y configura primero ese controlador y sus requisitos previos de IAM/subredes. EKS Auto Mode usa una clase/controlador diferente. El puerto 443 solo selecciona aquí un puerto TCP; el backend debe ofrecer TLS en 8443 o este se debe configurar por separado en el balanceador de carga.

Estas asignaciones de puertos ilustran la API general de Service de Kubernetes. Actualmente AWS documenta requisitos adicionales para las políticas de red nativas de EKS: el puerto del Service debe coincidir con el puerto del contenedor, y los Pods administrados por un controlador que tengan `metadata.ownerReferences` permiten una aplicación fiable. Adapta los ejemplos a esos requisitos antes de probar esa implementación de políticas.

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

Un recurso Ingress necesita un controlador y su plano de datos. Este ejemplo HTTP usa AWS LBC con `spec.ingressClassName: alb` y destinos IP. Los Services `api-v1`, `api-v2` y `web-frontend` a los que se hace referencia deben existir en `default`, exponer el puerto 80 y tener endpoints de Pod listos y enrutables desde la VPC. Configura HTTPS/los certificados por separado si es necesario. Consulta la [guía de LBC](03-aws-lb-controller.md) para conocer los requisitos previos de instalación y de los destinos.

Ingress define reglas para enrutar el tráfico HTTP/HTTPS a los Services internos del clúster.

![Enrutamiento lógico de host/ruta de Ingress hacia backends de Service y Pods.](../.gitbook/assets/en-networking-readme-3.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-3.html)

El recuadro representa la función del plano de datos de Ingress. AWS LBC configura ALB; el tráfico de la aplicación no atraviesa el proceso de reconciliación del controlador. Según el modo de destino, el plano de datos puede llegar a las IP de Pod o a NodePorts, en lugar de atravesar una IP virtual de Service como un salto literal adicional.

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

CNI estandariza la interfaz que usa un runtime para configurar la red de un contenedor. En las versiones actuales de Kubernetes, kubelet solicita operaciones del sandbox de Pod a través de CRI y el **runtime de contenedores administra CNI**. Los antiguos parámetros de administración directa de CNI de kubelet se eliminaron en Kubernetes 1.24.

### Responsabilidades del runtime y los plugins

| Actor | Responsabilidad |
|---|---|
| kubelet | Solicita la creación o eliminación del sandbox a través de la interfaz del runtime de contenedores |
| Runtime de contenedores | Selecciona la configuración de red e invoca la cadena de plugins CNI |
| Plugin CNI | Recibe la configuración, ejecuta ADD/DEL y otras operaciones compatibles, y devuelve resultados |
| Implementación de IPAM | Asigna y libera direcciones; puede ser un plugin delegado o parte de un agente específico del proveedor |
| Agente de nodo opcional | Mantiene rutas, políticas, grupos de IP o estado del plano de datos específicos del proveedor |

El runtime pasa la configuración al plugin a través de la interfaz CNI; no todos los plugins requieren un agente independiente de larga ejecución o un binario IPAM. Los tipos de interfaz también varían: los pares veth son habituales, pero no son la única implementación.

## Comparación de CNI

| Proyecto / ámbito | Redes y políticas | Características y límites que conviene distinguir |
|---|---|---|
| **Cilium 1.20.3** | Redes eBPF; Envoy para las funciones L7 pertinentes; políticas de red de Cilium y Hubble | Plano de datos de los nodos de trabajo Linux, con requisitos para AMD64/Arm64. Que la CLI esté disponible en Windows no significa que CNI sea compatible con Windows. WireGuard/IPsec y mTLS Beta de ztunnel tienen ámbitos distintos. |
| **Ejemplos de Calico Open Source 3.32.2; 3.33.0 actual** | Opciones de enrutamiento/encapsulación; opciones de iptables, nftables y eBPF; niveles ordenados de políticas y políticas de host/carga de trabajo | Calico 3.33.0 se prueba en Kubernetes 1.35–1.37. Revisa sus notas de la versión antes de actualizar. Windows tiene límites distintos, entre ellos la ausencia de un plano de datos Linux eBPF o WireGuard. La observabilidad de flujos Whisker/Goldmane está disponible como Tech Preview. Consulta la matriz de ediciones para conocer las funciones de pago. |
| **Flannel 0.28.10** | Asignación de subredes de host y transporte entre nodos; backends VXLAN, host-gw y otros | `flanneld` por sí solo no aplica NetworkPolicy; `netpol.enabled`, opcional en el chart, implementa un controlador de políticas de SIGs. WireGuard es un backend documentado; IPsec es experimental. VXLAN en Windows tiene ajustes y límites específicos. |
| **Ejemplos upstream/Helm de AWS VPC CNI 1.23.2; complemento de EKS `v1.23.1-eksbuild.1`** | Asignación de direcciones VPC y ENI/prefijos de EC2; capacidades de políticas de red estándar y Admin de EKS en nodos Linux EC2 compatibles | AWS incluye esta compilación del complemento administrado para Kubernetes 1.31–1.37; verifica su disponibilidad regional y la versión real del clúster. EKS Auto Mode es una implementación de redes administrada con capacidades adicionales de políticas DNS. Windows, Fargate, las redes personalizadas, la delegación de prefijos y la compatibilidad con varias NIC tienen condiciones aparte. |
| **Proyecto original Weave Net** | Implementación histórica de redes superpuestas | El repositorio original `weaveworks/weave` está archivado. No lo describas como una opción predeterminada activa y compatible para un clúster nuevo. |

### Políticas, cifrado y observabilidad

- Cilium ofrece políticas conscientes de HTTP/DNS mediante los componentes L7 aplicables, además de políticas de clúster y de host. Su semántica de denegación/permiso no es la API de niveles ordenados de Calico.
- Calico Open Source incluye niveles jerárquicos de políticas y políticas de host. La matriz actual de productos atribuye las políticas de capa de aplicación, las políticas DNS/FQDN y Cluster Mesh a Cloud/Enterprise; no se deben atribuir implícitamente a la edición de código abierto. El cifrado en tránsito documentado por Calico usa WireGuard.
- Amazon EKS proporciona controles `ClusterNetworkPolicy` Admin/Baseline para Auto Mode y para instalaciones compatibles de EC2/VPC CNI. La función `ApplicationNetworkPolicy` DNS/FQDN descrita por AWS es para **Auto Mode**. Su nombre no implica que actualmente inspeccione métodos/cuerpos HTTP.
- El controlador de políticas opcional de Flannel tiene sus propios requisitos; elegir solo un backend de red no habilita la aplicación de políticas.
- El cifrado entre nodos, la identidad autenticada de cargas de trabajo y el mTLS de aplicaciones son controles diferentes. La visibilidad de los flujos de red también es distinta del rastreo de aplicaciones o de la aplicación de políticas sobre procesos/archivos.

### Enrutamiento y rendimiento

Calico y Cilium pueden anunciar rutas mediante BGP; eso no proporciona por sí solo detección de servicios entre varios clústeres, sincronización de políticas ni cifrado. host-gw de Flannel usa rutas directas y requiere conectividad de capa 2 adecuada. Una red superpuesta añade encapsulación y consideraciones de MTU, pero no se puede inferir una clasificación universal de rendimiento a partir del nombre del CNI.

La cifra anterior de rendimiento del 100/98/95/85/80/75 por ciento no tenía una carga de trabajo, versiones ni fuente de medición reproducibles. Usa hardware, kernel, tamaños de paquetes/solicitudes, concurrencia, ajustes de cifrado/políticas, rendimiento, pérdida y latencia de cola comparables. La [evaluación comparativa de Pod](06-pod-network-benchmark.md), independiente, conserva su propio entorno y mediciones históricos.

## Guía para elegir un CNI

Primero elige el modelo de enrutamiento, políticas, sistema operativo y soporte que necesites; luego prueba esa combinación.

| Necesidad | Ruta de evaluación |
|---|---|
| Direccionamiento VPC estándar de EKS y políticas de red compatibles | Evalúa las capacidades de AWS VPC CNI/EKS antes de añadir un segundo motor de políticas. |
| Niveles de políticas ordenados, política de host o BGP de infraestructura | Evalúa la edición/plano de datos de Calico pertinente y los requisitos previos de enrutamiento. |
| Políticas de Cilium, Hubble o funciones de malla seleccionadas | Comprueba la compatibilidad con Linux/kernel/plataforma y la [guía de malla de Cilium](../service-mesh/cilium-service-mesh/README.md). Envoy sigue formando parte de las rutas L7 aplicables. |
| Una red pequeña con un conjunto de funciones limitado | Evalúa el backend de Flannel y el controlador de políticas opcional en función de los requisitos reales. |
| Aplicación de políticas sobre procesos, llamadas al sistema o archivos | Evalúa por separado un componente de seguridad en runtime como Tetragon, distinto de las políticas de red. |

### Configuración del complemento administrado de EKS

Lo siguiente es un ejemplo de **contenido de configuración**, no una instrucción para instalar Calico y el motor de políticas de VPC CNI en las mismas cargas de trabajo:

```json
{
  "enableNetworkPolicy": "true"
}
```

El tipo documentado para este ajuste es la cadena `"true"`. Selecciona una compilación del complemento de EKS compatible con la versión de Kubernetes existente y consulta el esquema de configuración de esa compilación:

```bash
EKS_REGION=ap-northeast-2
KUBERNETES_MINOR=1.35  # Replace with the existing cluster's minor version
aws eks describe-addon-versions --region "$EKS_REGION" --addon-name vpc-cni \
  --kubernetes-version "$KUBERNETES_MINOR"
: "${VPC_CNI_ADDON_VERSION:?Set the compatible eksbuild version selected from metadata}"
aws eks describe-addon-configuration --region "$EKS_REGION" --addon-name vpc-cni \
  --addon-version "$VPC_CNI_ADDON_VERSION"
```

El número de versión upstream 1.23.2 y una versión `eksbuild` de EKS son identificadores distintos. La tabla actual de complementos de AWS incluye `v1.23.1-eksbuild.1` para Kubernetes 1.31–1.37; usa `describe-addon-versions` en la región de destino para seleccionar una compilación compatible. Integra los cambios con la configuración prevista del complemento administrado; no selecciones `latest` a ciegas ni reemplaces valores no relacionados. Migrar desde una implementación de políticas de terceros también requiere eliminar su estado de aplicación existente y contar con un plan probado de transición de nodos/cargas de trabajo.

## Fundamentos de redes de EKS

### Arquitectura de red predeterminada de EKS

| Ubicación / componente | Responsabilidad |
|---|---|
| VPC administrada por EKS | AWS ejecuta el plano de control administrado de Kubernetes en varias zonas de disponibilidad. |
| VPC del clúster del cliente | Las redes de los nodos de trabajo, las subredes seleccionadas y las ENI entre cuentas administradas por EKS proporcionan las rutas configuradas hacia el plano de control. |
| ALB/NLB en subredes seleccionadas de la VPC del cliente | Proporciona el punto de entrada de aplicación público o interno elegido; una puerta de enlace de Internet/puerta de enlace NAT no sustituye esa configuración de enrutamiento. |
| Puerta de enlace NAT o endpoints de servicio privados | Proporciona las rutas de salida concretas que requiere el diseño de la carga de trabajo. |

La ilustración anterior situaba el plano de control dentro de la VPC del cliente y los balanceadores de carga fuera de ella; se ha sustituido por estos límites de propiedad.

### DNS y redes por modo de cómputo

| Modo de cómputo | DNS / ubicación de componentes |
|---|---|
| Nodos EC2 estándar | Normalmente usan el Deployment de CoreDNS configurado y los componentes de red instalados; los reemplazos necesitan su propia configuración compatible. |
| EKS Auto Mode puro | Las funciones de CoreDNS, VPC CNI y kube-proxy se ejecutan como servicios systemd administrados en los nodos. No se necesita un Deployment/complemento de CoreDNS para estos nodos. |
| Auto Mode combinado con nodos no Auto | Conserva el Deployment de CoreDNS para los nodos que no usan Auto Mode; estos no pueden usar el servicio DNS de Auto Mode de otro nodo. |

El primer resolvedor DNS de Auto Mode es local al nodo. El reenvío upstream y la comunicación con el plano de control aún pueden requerir acceso a la red; esto no garantiza que todos los paquetes relacionados con DNS permanezcan en el nodo. AWS documenta políticas Admin y DNS para Auto Mode, mientras que la política Admin de VPC CNI de EC2 estándar tiene requisitos propios de versión/habilitación.

### Cómo funciona VPC CNI

AWS VPC CNI proporciona a los Pods ordinarios direcciones enrutables desde la VPC usando el modo IPAM seleccionado. Las direcciones IPv4 secundarias, los prefijos delegados, las ENI de ramificación y las configuraciones con varias NIC difieren entre sí; los Pods que usan la red del host comparten la red del nodo.

![Asignación ilustrativa de IPv4 secundarias desde las ENI de EC2 a los Pods, con una interfaz activa opcional.](../.gitbook/assets/en-networking-readme-9.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-9.html)

Esto solo representa el modo de IP secundaria. Una ENI activa es una estrategia de asignación configurable, no un requisito que obligue a cada nodo a reservar siempre exactamente una. La delegación de prefijos, las redes personalizadas y las ENI de ramificación tienen reglas de asignación distintas.

#### Límites de ENI e IP

| Tipo de instancia | ENI máximas | Espacios IPv4 por ENI | Valor de inicialización de IP secundaria heredado |
|---------------|----------|--------------|------------------------|
| t3.medium | 3 | 6 | 17 |
| t3.large | 3 | 12 | 35 |
| m5.large | 3 | 10 | 29 |
| m5.xlarge | 4 | 15 | 58 |
| m5.2xlarge | 4 | 15 | 58 |
| c5.4xlarge | 8 | 30 | 234 |

Estos valores se verificaron con los límites de instancias de VPC CNI 1.23.2 y la tabla heredada de max-Pods. El cálculo histórico es `ENIs × (IPv4 slots per ENI − 1) + 2`; no es una recomendación universal actual. La delegación de prefijos, las redes personalizadas, las ENI de ramificación y las tarjetas de red múltiples cambian la capacidad de direcciones. La programación de Kubernetes también está limitada por `maxPods` de kubelet y por los recursos. Los grupos de nodos administrados de EKS limitan `maxPods` a 110 para instancias con menos de 30 vCPU y a 250 en los demás casos; la cantidad de IP disponibles no anula ese límite.

### Consideraciones sobre las redes de EKS

#### Administración de direcciones IP

Para **Linux VPC CNI**, configura las variables de entorno documentadas mediante el mecanismo de administración seleccionado para el complemento/Helm/DaemonSet. Lo siguiente es un fragmento de configuración del complemento de EKS. El antiguo ConfigMap `amazon-vpc-cni` con `enable-prefix-delegation` no configura Linux IPAMD de esta manera. Conserva los demás valores previstos del complemento al aplicar un cambio.

```json
{
  "env": {
    "ENABLE_PREFIX_DELEGATION": "true",
    "WARM_PREFIX_TARGET": "1"
  }
}
```

Como alternativa, ajusta el mínimo total de asignación y el objetivo de IP libres. Cuando se configura `MINIMUM_IP_TARGET` o `WARM_IP_TARGET`, cualquiera de ellos tiene prioridad sobre `WARM_PREFIX_TARGET`; son políticas alternativas, no cuatro objetivos aditivos independientes. La asignación sigue realizándose en unidades del tamaño de un prefijo. La compatibilidad con Nitro, el espacio contiguo `/28` para IPv4 y un límite adecuado de Pod en kubelet son requisitos previos independientes.

La asignación de prefijos de Windows sigue una ruta de configuración distinta: AWS documenta `enable-windows-prefix-delegation` y sus claves de objetivo de capacidad en el ConfigMap `amazon-vpc-cni`. No copies sin cambios el procedimiento de variables de entorno de Linux para Windows.

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

Estos ejemplos IPv4 requieren ID reales de subredes/grupos de seguridad en la AZ y la VPC previstas. Habilita las redes personalizadas y selecciona el ENIConfig de cada nodo mediante su etiqueta de zona. Una anotación explícita de nodo ENIConfig tiene prioridad sobre esa etiqueta. Los nombres de ejemplo siguientes usan la misma región en ambos idiomas; sustitúyelos por las zonas reales de los nodos. Instalar objetos ENIConfig por sí solo no activa las redes personalizadas.

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

Los temas siguientes se mencionan de pasada en otros puntos de esta descripción general. Los procedimientos de configuración completos y las cifras medidas se encuentran en las páginas detalladas enlazadas; esta sección organiza las diferencias entre capas y explica dónde encaja cada elemento.

### L2–L7 y la diferencia entre routers y balanceadores de carga

«Router» y «balanceador de carga» suelen aparecer en la misma frase, pero responden a preguntas distintas. Un router elige (por lo general) una ruta hacia un único destino; un balanceador de carga elige un destino entre varios candidatos equivalentes mediante un algoritmo de distribución.

| Capa | Dispositivo/función | Criterio de decisión | Correspondencia con Kubernetes/AWS |
|---|---|---|---|
| L2 (enlace) | Switch, puente | Dirección MAC de destino | Pares veth y puentes Linux creados por CNI, NIC virtual expuesta por una ENI |
| L3 (red) | Router o inserción transparente de dispositivos | IP de destino para el enrutamiento; identidad del flujo para seleccionar dispositivos | Router implícito de la VPC, TGW; GWLB encapsula paquetes IP para dispositivos |
| L4 (transporte) | Balanceador de carga L4 | Identidad de conexión/flujo, normalmente la tupla de 5 elementos | NLB; kube-proxy (iptables, IPVS, nftables); implementaciones eBPF de Service independientes |
| L7 (aplicación) | Balanceador de carga/proxy inverso L7 | Host, ruta y encabezados por solicitud; conocimiento del protocolo | ALB, implementaciones de Ingress/Gateway API, sidecars de service mesh (Envoy) |

La diferencia fundamental es la **unidad de distribución**. Un balanceador de carga L4 normalmente selecciona un destino para una conexión TCP o un flujo UDP rastreado. Un proxy L7 puede seleccionar un destino para cada solicitud de aplicación compatible, incluso las que comparten una conexión. GWLB distribuye flujos IP encapsulados entre dispositivos de seguridad en lugar de analizar solicitudes de aplicación. La persistencia de flujo depende del tiempo de espera, el estado de salud y el comportamiento de conmutación por error configurados; no garantiza que un flujo nunca se reasigne o interrumpa.

> 📎 Las definiciones de protocolo de los conceptos L2/L3 están en [Fundamentos de redes, Parte 1](../basics/06-network-fundamentals-part1.md); los tipos de destino de ALB/NLB y la configuración real están en [AWS Load Balancer Controller](03-aws-lb-controller.md).

### Conectividad entre cuentas/VPC: TGW, VPC Peering, GWLB, PrivateLink y Lattice

Estas cinco opciones de conectividad difieren en capa y modelo de tráfico. Las latencias medidas entre el uso compartido de TGW con RAM, VPC Peering, PrivateLink, TGW Peering y VPC Lattice están en [Conectividad de VPC entre organizaciones](05-cross-org-vpc-connectivity.md). Esta sección añade GWLB, que no aparece en esa tabla comparativa, y replantea las cinco opciones según la capa.

| Conectividad | Capa/modelo | Características |
|---|---|---|
| VPC Peering | L3, enrutamiento IP bidireccional | No es transitivo; no se puede configurar con CIDR superpuestos |
| Transit Gateway (TGW) | L3, enrutamiento IP en estrella | Usa asociaciones y propagación de adjuntos en una o varias tablas de rutas de TGW; se comparte entre cuentas mediante RAM |
| Gateway Load Balancer (GWLB) | L3, inserción transparente de dispositivos | Encapsula el paquete original en GENEVE (UDP 6081); el modelo de servicio de endpoint de VPC conecta el tráfico del consumidor con la flota de dispositivos del proveedor |
| PrivateLink | Conectividad de endpoints privados | Un servicio de endpoint respaldado por NLB es un modelo; también existen endpoints de recursos. Los CIDR del consumidor y del proveedor pueden superponerse |
| VPC Lattice | Redes de aplicaciones y recursos | Los servicios HTTP/HTTPS admiten enrutamiento L7 y autorización IAM opcional; el paso directo de TLS y las configuraciones de recursos ofrecen capacidades distintas |

GWLB inserta dispositivos de inspección, como firewalls e IDS/IPS, en una ruta IP mediante un endpoint de Gateway Load Balancer. Su persistencia de flujo predeterminada usa cinco campos; las configuraciones compatibles pueden usar en su lugar dos o tres. Valida las rutas de ida y vuelta, el estado de los dispositivos, la MTU de encapsulación, las NACL y los grupos de seguridad de las cargas de trabajo/dispositivos reales. GWLB no tiene un grupo de seguridad propio como ALB, y la persistencia de flujo no sustituye las pruebas de fallos.

Para el diseño de seguridad, consulta [protección de WAF/origen](../security/14-waf-edge-api-security.md), [NGFW de Palo Alto/Fortinet](../security/15-ngfw-paloalto-fortinet.md) y [rutas y fallos de GWLB/GENEVE](../security/16-gwlb-geneve-inspection.md). GWLBE tampoco admite grupos de seguridad. Para destinos que no están en buen estado, AWS describe la selección de destino por flujo y el descarte hasta que se recupere, sin omisión directa del dispositivo. Revisa conjuntamente la persistencia con tuplas reducidas, la disponibilidad entre zonas, NAT y el modo de dispositivo de TGW.

> 📎 La integración completa de EKS/VPC Lattice (Gateway API Controller, autorización IAM, enrutamiento) está en [VPC Lattice](02-vpc-lattice.md).

### Comportamiento real de Route 53 Resolver y las tablas de rutas

**Resolvedor DNS:** AmazonProvidedDNS **es Route 53 Resolver**. Sus direcciones incluyen la dirección IPv4 principal de la red de la VPC más dos (`10.0.0.2` para `10.0.0.0/16`) y `169.254.169.253`; resuelve las zonas privadas asociadas y los nombres públicos según las reglas de Resolver. Normalmente CoreDNS sirve el dominio de clúster de Kubernetes configurado, a menudo `cluster.local`; `kube-dns` es el nombre de su Service, no un espacio de nombres ni una zona DNS. El reenvío externo sigue el Corefile y el archivo del resolvedor que ve el Pod DNS. Inspecciona esos ajustes en lugar de suponer que se usa sin cambios el archivo del resolvedor del nodo. En un diseño con endpoints de Resolver, los endpoints de entrada reciben consultas locales, mientras que los endpoints de salida y las reglas asociadas reenvían a DNS local las consultas seleccionadas de la VPC. El resolvedor local al nodo de Auto Mode no elimina las dependencias upstream.

**Tablas de rutas:** La evaluación de rutas de VPC suele usar la coincidencia de prefijo más largo. AWS permite reemplazar el destino de una ruta `local` y agregar rutas de subred más específicas compatibles para el enrutamiento mediante dispositivos; `local` no siempre es la ruta más específica. Para destinos idénticos, las rutas estáticas de VPC tienen prioridad sobre las rutas propagadas desde una puerta de enlace privada virtual. Una ruta de VPC con destino a un TGW es estática; la propagación dentro de un TGW pertenece a sus tablas de rutas independientes. Los destinos no válidos pueden dejar entradas `blackhole` que descartan el tráfico, así que inspecciona el estado de la ruta además del destino. Una subred sin asociación explícita a una tabla de rutas usa la tabla de rutas principal de la VPC.

> 📎 La prioridad de rutas de TGW/Peering y ejemplos de configuración de rutas estáticas están en los [hallazgos operativos de Conectividad de VPC entre organizaciones](05-cross-org-vpc-connectivity.md#operational-findings).

### Plano de datos del kernel: iptables, IPVS, eBPF y filtrado de paquetes

El reenvío de Service de Linux y la aplicación de políticas de red pueden usar mecanismos distintos. Netfilter proporciona los hooks de la ruta de paquetes que usan iptables y nftables. Las implementaciones eBPF pueden asociarse a hooks de XDP, tc o sockets y realizar allí la selección de Service. Esto no significa que todos los paquetes de un clúster habilitado para eBPF eviten Netfilter o el seguimiento de conexiones; la ruta depende del CNI, el kernel, el enrutamiento y la configuración de funciones.

| Implementación | Ubicación | Características |
|---|---|---|
| iptables | Cadenas secuenciales de reglas en hooks de netfilter | El tiempo de evaluación aumenta con la cantidad de reglas (O(n)); modo predeterminado histórico de kube-proxy |
| IPVS | Balanceador de carga L4 nativo del kernel, extensión de netfilter | Búsqueda basada en hash (casi O(1)); quedó obsoleto como modo de kube-proxy a partir de Kubernetes 1.35 |
| nftables | Framework sucesor de iptables en netfilter | Modo estable de kube-proxy desde 1.33; primero comprueba la compatibilidad del kernel/CNI |
| eBPF (p. ej., Cilium) | Hooks XDP, tc y de sockets configurados | Puede sustituir el manejo de Service de kube-proxy; es una implementación distinta, con comportamiento de Netfilter/seguimiento de conexiones específico de cada ruta |

Cambiar de implementación puede dejar reglas del kernel y conexiones activas. Sigue el procedimiento de migración de la distribución/CNI, drena las cargas de trabajo según sea necesario y planifica reinicios de nodos cuando se requieran para limpiar el estado. Sustituir kube-proxy por un CNI basado en eBPF también requiere un orden de cambio compatible para evitar que las implementaciones compitan por el mismo tráfico de Service.

> 📎 La cronología de obsolescencia de IPVS y la transición de nftables a estable se tratan en [Introducción a Kubernetes](../basics/04-kubernetes-introduction.md); el reemplazo eBPF de kube-proxy de Cilium está en [eBPF de Cilium](cilium/02-ebpf.md); el plano de datos eBPF de Calico y su procedimiento de migración están en [eBPF de Calico](calico/06-ebpf-dataplane.md).

### Redes de cómputo intensivo: ENI, EFA, NVLink y transceptores ópticos

ENI, EFA y NVLink sirven para rutas distintas. Una **ENI** es una interfaz de red virtual conectada a una instancia EC2 en una zona de disponibilidad; su tráfico IP normal puede llegar a otras AZ y VPC conectadas cuando el enrutamiento y las políticas lo permiten (consulta [VPC CNI](01-vpc-cni.md)). **EFA** proporciona un dispositivo de acceso directo al sistema operativo que el software MPI/NCCL compatible usa mediante libfabric. **El tráfico del dispositivo EFA no es enrutable y no puede atravesar los límites de VPC/AZ**; el tráfico IP normal a través del dispositivo ENA de una interfaz EFA con ENA sí es enrutable. Las interfaces EFA únicamente no tienen dispositivo ENA ni direccionamiento IP. **NVLink** conecta GPU dentro de los sistemas compatibles, incluidos los dominios NVLink compatibles a escala de rack. Mide el hardware, las operaciones colectivas y la ubicación seleccionados en lugar de dar por supuesto un aumento de velocidad fijo respecto a EFA.

Los **transceptores ópticos** son un concepto general de redes de centros de datos. Los cables de cobre DAC (Direct Attach Copper) sirven para tramos cortos; los módulos ópticos y la fibra satisfacen otros requisitos de alcance y ancho de banda. QSFP y OSFP describen formatos físicos de módulos, pero no garantizan el uso de medios ópticos. Considera esto información general: no establece el cableado físico de una carga de trabajo concreta de AWS.

> 📎 La programación que tiene en cuenta la topología de NVLink/IMEX y los ejemplos de ubicación de Pod GPU están en [Infraestructura de IA/ML](../ai-ml/06-ai-infrastructure.md); los límites VPC/AZ y las mediciones de EFA están en [Conectividad de VPC entre organizaciones](05-cross-org-vpc-connectivity.md).

### Qué significan los protocolos de próxima generación para Kubernetes: HTTP/3, gRPC y QUIC

La mecánica de los protocolos HTTP/3 (RFC 9114) y su transporte QUIC (RFC 9000) se explica en [Fundamentos de redes, Parte 2](../basics/06-network-fundamentals-part2.md) y [Parte 3](../basics/06-network-fundamentals-part3.md). Aquí solo cubrimos lo que afecta de hecho a la distribución del tráfico de Kubernetes.

- **gRPC y los balanceadores de carga L4:** gRPC multiplexa solicitudes en conexiones HTTP/2. Un balanceador L4 normalmente mantiene una conexión TCP establecida en el endpoint seleccionado; si ese endpoint es un proxy, este puede tomar otras decisiones de enrutamiento. Añadir Pods por sí solo no redistribuye las conexiones existentes. La distribución por RPC requiere un proxy L7 compatible o una política del lado del cliente. Una llamada RPC en streaming sigue siendo una única llamada; sus mensajes individuales no se balancean de forma independiente.
- **GRPCRoute de Gateway API:** Ingress no tiene un recurso específico para gRPC, pero Gateway API estandariza el enrutamiento por servicio/método con `GRPCRoute`. La compatibilidad varía según la implementación (cantidad de coincidencias de encabezados, políticas de reintento, etc.), así que consulta la documentación del controlador.
- **Hasta dónde llega realmente HTTP/3/QUIC dentro del clúster:** La compatibilidad con HTTP/3 entre un cliente y el borde (una CDN, un balanceador de carga) es una cuestión distinta de la compatibilidad con HTTP/3 dentro del clúster o en la conexión backend de un Ingress. Muchas implementaciones de Ingress/Gateway siguen usando HTTP/1.1 o HTTP/2 con el backend, y la compatibilidad con HTTP/3 de extremo a extremo varía según la implementación y la versión, así que no generalices; consulta la documentación del controlador que se usa realmente.

## Subsecciones de redes

Esta sección trata en detalle los siguientes temas:

### [Redes de Linux desde cero](beginner/README.md) {#beginner-course}

Si estás empezando con Linux o las redes, comienza con el [curso para principiantes](beginner/README.md). Sus ocho lecciones conectan la CLI, el direccionamiento, DNS, SSH, los firewalls, la monitorización y un proyecto final. La ruta siguiente amplía esos fundamentos con protocolos, el kernel e implementaciones de clústeres.

### [Ruta avanzada de redes](expert/README.md) {#expert-course}

Después del curso para principiantes, usa la [ruta avanzada de redes](expert/README.md) para conectar proyectos de protocolos, políticas de enrutamiento, EVPN, rendimiento de Linux, diseño de la nube y evaluación de automatización. Comprueba primero el entorno, las evidencias y los criterios de recuperación de cada cuaderno de trabajo.

### [Práctica de diagnóstico de redes de Linux](07-linux-network-diagnostics.md) {#linux-network-diagnostics}

Relaciona los [conceptos de sockets del kernel y rutas de paquetes](../kernel/02-network-stack.md) con las observaciones antes de estudiar las implementaciones de CNI. Usa el [cuestionario de diagnóstico](../quizzes/networking/07-linux-network-diagnostics-quiz.md) para comprobar tu interpretación.

### [VPC CNI](01-vpc-cni.md)
Redes de EKS con direcciones VPC para Pods ordinarios y requisitos previos de IPAM/políticas específicos del modo.

### [Análisis detallado de Cilium](cilium/README.md)
Solución CNI de alto rendimiento basada en eBPF. Ofrece funciones avanzadas como Network Policy L7, Service Mesh y observabilidad (Hubble).

### [Análisis detallado de Calico](calico/README.md)
Uno de los CNI más utilizados. Ofrece potentes Network Policy, compatibilidad con BGP y funciones empresariales. Abarca la introducción, la arquitectura, los modos de red, un análisis detallado de BGP, Network Policy, eBPF, temas avanzados, integración con EKS y una guía de operaciones.

### [VPC Lattice](02-vpc-lattice.md)
Servicio administrado de AWS para redes de aplicaciones. Comunicación entre servicios de distintas VPC y cuentas.

### [AWS Load Balancer Controller](03-aws-lb-controller.md)
Integra los Services e Ingress de Kubernetes con AWS ELB (ALB/NLB).

### [Gateway API](04-gateway-api.md)
API de Ingress de próxima generación para Kubernetes. Modelo de recursos estandarizado y configuración basada en roles.

### [Evaluación comparativa de redes de Pod](06-pod-network-benchmark.md)
RTT entre Pods, latencia HTTP y rendimiento medidos en EKS para el mismo nodo, la misma AZ y AZ distintas, además de la amplificación de consultas DNS `ndots:5`.

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

Ejecuta los diagnósticos desde un Pod existente que tenga las herramientas indicadas. Consulta únicamente el CNI instalado en el clúster; los servicios systemd de Auto Mode no son esos DaemonSets. La resolución DNS, la accesibilidad TCP y una respuesta HTTP de la aplicación son comprobaciones distintas. ICMP puede estar bloqueado o requerir privilegios adicionales, así que un ping fallido por sí solo no demuestra que un servicio TCP sea inaccesible.

#### Service inaccesible

```bash
NAMESPACE=default
SERVICE_NAME=my-service
kubectl -n "$NAMESPACE" get service "$SERVICE_NAME" -o yaml
kubectl -n "$NAMESPACE" get endpointslices \
  -l "kubernetes.io/service-name=$SERVICE_NAME" -o yaml
kubectl -n kube-system logs -l k8s-app=kube-proxy --tail=100
```

Usa EndpointSlice para el diagnóstico actual de endpoints. Comprueba los selectores del Service, los puertos de destino, la disponibilidad de los endpoints, la familia de direcciones y las políticas aplicables. Inspecciona los registros de kube-proxy solo si ese componente se encarga realmente del reenvío de Service; un reemplazo eBPF o Auto Mode requiere sus propios diagnósticos.

#### Depuración de Network Policy

```bash
kubectl get networkpolicies.networking.k8s.io -A
kubectl -n kube-system exec ds/cilium -c cilium-agent -- cilium-dbg policy get
kubectl -n kube-system exec ds/cilium -c cilium-agent -- cilium-dbg endpoint list
# For a Calico installation using its standard CRD datastore:
kubectl get networkpolicies.crd.projectcalico.org -A
kubectl get globalnetworkpolicies.crd.projectcalico.org
```

Los comandos de Cilium inspeccionan un Agent seleccionado mediante la referencia al DaemonSet; al investigar un incidente, elige el Agent del nodo afectado. Las instalaciones de la API nativa de Calico pueden exponer otro grupo de API, así que inspecciona los recursos que ofrece la instalación. Las políticas de Kubernetes, Calico y las extensiones de AWS son recursos distintos y pueden tener precedencias diferentes.

### Pruebas de rendimiento de red

Este ejercicio TCP acotado usa el índice de imágenes Netshoot v0.16 fijado por el publicador, que contiene imágenes Linux AMD64 y Arm64; su Dockerfile incluye `iperf3`. Crea estos Pods en un entorno de prueba donde se permita TCP 5201. Es una carga de trabajo ilustrativa, no una comparación medida entre CNI.

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

El cliente duerme durante una hora y el comando limita el tráfico ofrecido a 10 Mbit/s durante diez segundos. Esto prueba la ruta seleccionada, no el rendimiento máximo. Registra la ubicación real de Pod/nodo/AZ, los límites de recursos y la política antes de interpretar los resultados. Elige herramientas específicas para Windows si usas nodos Windows. Al terminar, elimina únicamente los recursos de prueba que hayas creado.

Estos Pods de diagnóstico independientes sirven para probar la conectividad. Para probar la aplicación nativa de políticas de red de EKS, usa Pods administrados por Deployment/Job y cumple los requisitos documentados de Service/puerto de contenedor.

## Prácticas recomendadas

### 1. Planificación de direcciones IP

- Diseña bloques CIDR suficientemente grandes
- Separa la red de Pod de la red de Service
- Diseña las subredes pensando en la expansión futura

### 2. Aplicación de políticas de red

Crea el espacio de nombres aislado `networking-demo` antes de usar este ejemplo. Selecciona todos los Pods que contiene y aísla tanto el tráfico de entrada como el de salida según la semántica estándar de NetworkPolicy de Kubernetes; los flujos DNS y de aplicación necesarios requieren reglas de permiso explícitas. La aplicación requiere un motor de políticas compatible. Las API adicionales de políticas de clúster/administración pueden alterar la precedencia, y este manifiesto no constituye una arquitectura completa de confianza cero.

- Aplica políticas de denegación predeterminada (confianza cero)
- Permite explícitamente solo el tráfico necesario
- Aísla los espacios de nombres

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

- Elige el CNI adecuado (según la carga de trabajo)
- Optimiza la MTU
- Ajusta los parámetros del kernel

### 4. Refuerzo de la seguridad

- Selecciona un cifrado de transporte compatible y verifica qué tráfico cubre.
- Configura la identidad de cargas de trabajo/aplicaciones y mTLS cuando sea necesario; mantenlos separados de las listas de permitidos basadas en DNS/IP.
- Revisa periódicamente los cambios en políticas, certificados y controles de acceso.

### 5. Garantizar la observabilidad

- Recopila métricas de red
- Habilita registros de flujo
- Implementa el rastreo distribuido

## Próximos pasos

Después del [curso para principiantes](beginner/README.md), continúa con la [pila de redes del kernel](../kernel/02-network-stack.md) y luego con la [práctica de diagnóstico de redes de Linux](07-linux-network-diagnostics.md) y su [cuestionario](../quizzes/networking/07-linux-network-diagnostics-quiz.md). La [ruta de aprendizaje](#learning-path) conecta estos fundamentos con contenedores y Services antes de los temas de CNI y AWS que siguen.

1. [VPC CNI](01-vpc-cni.md) - CNI predeterminado de EKS
2. [Análisis detallado de Cilium](cilium/README.md) - Redes basadas en eBPF
3. [Análisis detallado de Calico](calico/README.md) - Enrutamiento, políticas y planos de datos
4. [VPC Lattice](02-vpc-lattice.md) - Redes administradas de AWS
5. [AWS Load Balancer Controller](03-aws-lb-controller.md) - Integración con ELB
6. [Gateway API](04-gateway-api.md) - Ingress de próxima generación
7. [Conectividad de VPC entre organizaciones](05-cross-org-vpc-connectivity.md) - Conexión de VPC entre AWS Organizations (verificada en campo)
8. [Evaluación comparativa de redes de Pod](06-pod-network-benchmark.md) - Latencia y rendimiento medidos por límite de nodo/AZ

---

## Referencias

- [Modelo de red de Kubernetes](https://kubernetes.io/docs/concepts/services-networking/)
- [Services de Kubernetes](https://kubernetes.io/docs/concepts/services-networking/service/)
- [Runtime de contenedores y CNI](https://kubernetes.io/docs/concepts/extend-kubernetes/compute-storage-net/network-plugins/)
- [NetworkPolicy de Kubernetes](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Especificación de CNI](https://raw.githubusercontent.com/containernetworking/cni/main/SPEC.md)
- [Ediciones del producto Calico](https://docs.tigera.io/calico/latest/about)
- [Versión de Calico Open Source 3.33.0](https://github.com/projectcalico/calico/releases/tag/v3.33.0)
- [Niveles de políticas de Calico](https://docs.tigera.io/calico/latest/network-policy/policy-tiers/tiered-policy)
- [Registros de flujo de Calico Whisker](https://docs.tigera.io/calico/latest/observability/view-flow-logs)
- [Limitaciones de Calico en Windows](https://docs.tigera.io/calico/latest/getting-started/kubernetes/windows-calico/limitations)
- [Redes y políticas de Flannel 0.28.10](https://raw.githubusercontent.com/flannel-io/flannel/v0.28.10/README.md)
- [Backends de Flannel](https://raw.githubusercontent.com/flannel-io/flannel/v0.28.10/Documentation/backends.md)
- [Estado del repositorio original de Weave](https://api.github.com/repos/weaveworks/weave)
- [AWS VPC CNI 1.23.2](https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.23.2/README.md)
- [Versiones más recientes del complemento VPC CNI de Amazon EKS](https://docs.aws.amazon.com/eks/latest/userguide/managing-vpc-cni.html)
- [Configuración de políticas de red de EKS](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy-configure.html)
- [Políticas de red estándar y Admin de EKS](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html)
- [Delegación de prefijos y maxPods de EKS](https://docs.aws.amazon.com/eks/latest/userguide/cni-increase-ip-addresses-procedure.html)
- [Modelos de implementación de políticas Admin y DNS de EKS](https://aws.amazon.com/blogs/containers/enhance-amazon-eks-network-security-posture-with-dns-and-admin-network-policies/)
- [Redes de EKS Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/auto-networking.html)
- [Requisitos de los complementos de EKS](https://docs.aws.amazon.com/eks/latest/userguide/workloads-add-ons-available-eks.html)
- [Arquitectura del plano de control de EKS](https://docs.aws.amazon.com/eks/latest/best-practices/control-plane.html)
- [Metadatos de la imagen Netshoot v0.16](https://hub.docker.com/v2/repositories/nicolaka/netshoot/tags/v0.16)
- [Dockerfile de Netshoot v0.16](https://raw.githubusercontent.com/nicolaka/netshoot/v0.16/Dockerfile)
- [Seguridad en runtime de Tetragon](https://tetragon.io/docs/overview/)
- [Configuración de NLB de AWS LBC 3.6](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.6.0/docs/guide/service/nlb.md)
- [Configuración de Ingress de AWS LBC 3.6](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.6.0/docs/guide/ingress/annotations.md)
- [Conceptos de Gateway Load Balancer](https://docs.aws.amazon.com/vpc/latest/privatelink/gateway-load-balancers.html)
- [Encapsulación GENEVE (RFC 8926)](https://www.rfc-editor.org/rfc/rfc8926)
- [Resolvedor DNS de VPC](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-dns.html)
- [Endpoints y reglas de Route 53 Resolver](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver.html)
- [Orden de evaluación de la tabla de rutas de VPC](https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Route_Tables.html)
- [Rutas locales y rutas de subred más específicas](https://docs.aws.amazon.com/vpc/latest/userguide/subnet-route-tables.html)
- [Prioridad de rutas estáticas y propagadas](https://docs.aws.amazon.com/vpc/latest/userguide/route-tables-priority.html)
- [Direcciones y comportamiento de AmazonProvidedDNS](https://docs.aws.amazon.com/vpc/latest/userguide/AmazonDNS-concepts.html)
- [Persistencia de flujos y conmutación por error de GWLB](https://docs.aws.amazon.com/elasticloadbalancing/latest/gateway/edit-target-group-attributes.html)
- [IP virtuales de Service de Kubernetes y modos de kube-proxy](https://kubernetes.io/docs/reference/networking/virtual-ips/)
- [Nombres de Service de CoreDNS y configuración de reenvío](https://kubernetes.io/docs/tasks/administer-cluster/dns-custom-nameservers/)
- [Endpoints de recursos de PrivateLink](https://docs.aws.amazon.com/vpc/latest/privatelink/privatelink-access-resources.html)
- [Documentación del proyecto Netfilter/iptables](https://www.netfilter.org/documentation/index.html)
- [Elastic Fabric Adapter de EC2](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/efa.html)
- [Protocolo de transporte QUIC (RFC 9000)](https://www.rfc-editor.org/rfc/rfc9000)
- [HTTP/3 (RFC 9114)](https://www.rfc-editor.org/rfc/rfc9114)
- [gRPC sobre HTTP/2 y balanceo de carga](https://grpc.io/blog/grpc-load-balancing/)
- [GRPCRoute de Gateway API](https://gateway-api.sigs.k8s.io/guides/user-guides/grpc-routing/)
