# Cuestionario de networking de EKS - Parte 3

> **Última actualización**: October 12, 2026

Este cuestionario cubre los [conceptos de resolución de problemas de la Parte 3](../../eks/03-eks-networking-part3.md), la conectividad privada, el diseño multiclúster y las operaciones de mesh. Los ejemplos actuales usan EKS Kubernetes 1.36 y VPC CNI 1.23.0; la configuración histórica de App Mesh se identifica explícitamente. Los ejemplos de creación de recursos requieren prerrequisitos revisados de IAM, red y propiedad. Esta auditoría realiza comprobaciones locales, no un despliegue de EKS.

### 1. ¿Qué cambia cuando una aplicación se inscribe en un service mesh basado en sidecar?

- A. Todo el tráfico del Pod sale de la VPC
- B. Un proxy gestiona el tráfico de servicios inscritos
- C. Se elimina el descubrimiento de servicios
- D. Todo el tráfico requiere Transit Gateway

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Un proxy inyectado procesa el tráfico de servicios inscritos.**

En modo sidecar, la aplicación y el proxy comparten un espacio de nombres de red y una IP de Pod. El proxy forma parte del plano de datos; el plano de control distribuye la configuración de enrutamiento, seguridad e identidad. NetworkPolicy, el enrutamiento de VPC y el descubrimiento de Service siguen siendo importantes. La ruta lógica es:
```text
Application → client proxy → Pod network → destination proxy → application
```
La interceptación depende de la inscripción, los puertos excluidos, el protocolo y el modo; no todos los paquetes deben atravesar un VIP de Service. Los mesh ambient usan un diseño diferente de proxy de nodo/waypoint, por lo que la pregunta trata explícitamente sobre el modo sidecar. Los mesh pueden proporcionar reintentos, enrutamiento, mTLS y telemetría sin reescribir la implementación del servicio principal, pero las aplicaciones aún pueden necesitar propagación del contexto de trazas, protocolos compatibles y gestión de tiempos de espera.

Use el inyector/revisión compatible del mesh seleccionado, no una imagen antigua de Envoy añadida manualmente ni inyectores simultáneos. AWS App Mesh es un ejemplo histórico: el soporte y el acceso finalizaron el 30 de septiembre de 2026. Los despliegues existentes deben migrar; no es el ejemplo predeterminado para nuevas instalaciones. Consulte [Istio installation](../../service-mesh/istio/01-installation.md) para conocer la ruta de implementación mantenida.

</details>

### 2. ¿Qué proporcionan los endpoints de VPC para las cargas de trabajo privadas de EKS?

- A. Ancho de banda ilimitado
- B. Conectividad privada a servicios compatibles
- C. Un descuento automático del 50%
- D. Autenticación automática de AWS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Rutas privadas a endpoints de servicios de AWS compatibles sin internet/NAT para esas solicitudes.**

Los endpoints de interfaz crean ENI en las subredes/AZ seleccionadas y normalmente generan cargos horarios y de procesamiento de datos. Los endpoints de gateway para S3/DynamoDB agregan entradas de tabla de rutas y no tienen cargo por endpoint; los cargos de servicio/almacenamiento/solicitud aún se aplican. Los endpoints no conceden permisos de IAM, no garantizan menor costo/latencia ni satisfacen automáticamente los requisitos de cumplimiento.

Para extracciones privadas de imágenes de ECR, planifique `ecr.api`, `ecr.dkr` y la ruta de descarga de capas de S3, las reglas HTTPS del SG de endpoint, compatibilidad de DNS/DNS privado, tablas de rutas y políticas de endpoint/IAM. Los demás servicios necesarios dependen de las cargas de trabajo: STS regional para IRSA, `eks-auth` para Pod Identity, API de EC2 para CNI, Logs/monitorización y otros según se utilicen. El endpoint de servicio de EKS no sustituye al endpoint privado de API de Kubernetes. ECR Public y las primeras solicitudes de pull-through cache/capas externas de Windows pueden requerir conectividad externa adicional o un mirror de imágenes preparado.

Este ejemplo parametrizado de CloudFormation agrega solo tres endpoints a una VPC **existente**. Revise los endpoints existentes/la propiedad de DNS privado antes de crearlo. Deliberadamente deja las políticas de endpoint específicas del servicio para que las defina el propietario de seguridad; el acceso predeterminado de endpoint no anula IAM. Prepare un change set en lugar de asumir que se trata de un despliegue completo de clúster aislado:
```yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: ECR API/DKR and S3 endpoints in an existing VPC; not a complete private EKS stack
Parameters:
  VpcId:
    Type: AWS::EC2::VPC::Id
  PrivateSubnetIds:
    Type: List<AWS::EC2::Subnet::Id>
    Description: Existing subnets in distinct Availability Zones
  PrivateRouteTableIds:
    Type: CommaDelimitedList
    Description: Route tables used by the image-pulling workloads
  EndpointSecurityGroupId:
    Type: AWS::EC2::SecurityGroup::Id
    Description: Existing same-VPC SG permitting HTTPS from the intended nodes/Pods
Resources:
  S3GatewayEndpoint:
    Type: AWS::EC2::VPCEndpoint
    Properties:
      ServiceName: !Sub com.amazonaws.${AWS::Region}.s3
      VpcId: !Ref VpcId
      RouteTableIds: !Ref PrivateRouteTableIds
      VpcEndpointType: Gateway
  ECRApiEndpoint:
    Type: AWS::EC2::VPCEndpoint
    Properties:
      ServiceName: !Sub com.amazonaws.${AWS::Region}.ecr.api
      VpcId: !Ref VpcId
      SubnetIds: !Ref PrivateSubnetIds
      SecurityGroupIds: [!Ref EndpointSecurityGroupId]
      PrivateDnsEnabled: true
      VpcEndpointType: Interface
  ECRDkrEndpoint:
    Type: AWS::EC2::VPCEndpoint
    Properties:
      ServiceName: !Sub com.amazonaws.${AWS::Region}.ecr.dkr
      VpcId: !Ref VpcId
      SubnetIds: !Ref PrivateSubnetIds
      SecurityGroupIds: [!Ref EndpointSecurityGroupId]
      PrivateDnsEnabled: true
      VpcEndpointType: Interface
```
Cuando se requiere un nuevo node group, `eksctl create nodegroup` usa **`--subnet-ids`**; la marca anterior `--vpc-private-subnets` era incorrecta para este comando. El ejemplo crea nodos administrados facturables después de que las rutas privadas de API/servicio estén listas; úselo solo si eksctl es el propietario previsto, sin un `private-ng` existente. El tamaño de instancia es ilustrativo, no una guía de dimensionamiento.
```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the existing cluster name}"
: "${AWS_REGION:?Set its Region}"
: "${PRIVATE_SUBNET_A:?Set an existing private subnet}"
: "${PRIVATE_SUBNET_B:?Set another private subnet}"
eksctl create nodegroup --cluster "$CLUSTER_NAME" --region "$AWS_REGION" \
  --name private-ng --managed --version auto --node-type m5.large \
  --nodes 2 --nodes-min 2 --nodes-max 3 --node-private-networking \
  --subnet-ids "$PRIVATE_SUBNET_A,$PRIVATE_SUBNET_B"
```

</details>

### 3. ¿Qué opción proporciona enrutamiento de hub entre varias VPC sin solapamiento?

- A. Un balanceador de carga público es obligatorio
- B. Transit Gateway con enrutamiento completo
- C. Cada clúster debe compartir una VPC
- D. Un gateway NAT proporciona descubrimiento de Kubernetes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. AWS Transit Gateway**

Transit Gateway es un diseño para muchas VPC; no es universalmente la arquitectura multiclúster más eficaz. Compare VPC peering, VPC compartidas, exposición de servicios mediante PrivateLink, VPC Lattice y gateways de mesh con respecto a límites de confianza, escala, DNS, solapamiento de direcciones y costo. NAT también tiene usos de conectividad privada; no proporciona descubrimiento de servicios.

Para un diseño de TGW, planifique CIDR de Pod/VPC enrutables sin solapamiento, attachments en cada AZ participante, asociaciones/propagación de tablas de rutas de TGW, rutas de subred de cargas de trabajo y rutas de retorno. Una sola ruta de TGW es insuficiente. Los ClusterIP de Kubernetes son direcciones de servicio virtuales, no endpoints remotos enrutables automáticamente. Exporte endpoints de Pod accesibles o direcciones de servicio de gateway/balanceador de carga mediante un diseño de descubrimiento explícito. Lea el estado real de las rutas antes de modificarlo:
```bash
set -euo pipefail
: "${AWS_REGION:?Set the transit gateway Region}"
: "${TGW_ROUTE_TABLE_ID:?Set the intended TGW route table}"
: "${VPC_ROUTE_TABLE_ID:?Set a workload-subnet route table}"
aws ec2 search-transit-gateway-routes --region "$AWS_REGION" \
  --transit-gateway-route-table-id "$TGW_ROUTE_TABLE_ID" \
  --filters Name=state,Values=active
aws ec2 describe-route-tables --region "$AWS_REGION" \
  --route-table-ids "$VPC_ROUTE_TABLE_ID"
```
TGW no tiene un SG de firewall conectado a él. Use SG de endpoint/nodo/Pod, NACL, NetworkPolicy y enrutamiento inspeccionado según corresponda. La referencia de SG entre VPC es una característica compatible de TGW bajo las restricciones documentadas de attachment/Region; es distinta de conectar un SG al TGW y no sustituye el enrutamiento.

Cloud Map requiere completar el namespace, un Service y la gestión de registro/salud/cancelación de registro. TGW no comparte automáticamente DNS de zonas alojadas privadas. Use asociaciones de zonas privadas aprobadas o endpoints/reglas de Route 53 Resolver. No reenvíe al resolvedor `base+2` de otra VPC como si fuera el CoreDNS de ese clúster. Este **fragmento de Corefile** asume dos resolvedores de entrada reales y accesibles que ya resuelven los registros `cluster2.example.internal` exportados. Intégrelo mediante el propietario de la configuración DNS y conserve la zona local del clúster:
```text
cluster2.example.internal:53 {
    errors
    cache 30
    forward . 10.1.20.10 10.1.21.10
}
```
La siguiente política de ingress permite un CIDR de origen remoto hacia un puerto de API, según la dirección de origen realmente visible después de NAT/proxies. Otras políticas coincidentes pueden ampliar la autorización. Los requisitos de egress/DNS deben diseñarse por separado; los labels de namespace/Pod entre clústeres no se comparten automáticamente.
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: remote-api-ingress
  namespace: multicluster-demo
spec:
  podSelector:
    matchLabels:
      app: api-service
  policyTypes:
  - Ingress
  ingress:
  - from:
    - ipBlock:
        cidr: 10.1.0.0/16
    ports:
    - protocol: TCP
      port: 8080
```
Istio multi-primary y primary-remote son diseños de plano de control diferentes; seleccione el modelo compatible y verifique los gateways east-west, la confianza de identidad y el estado de los endpoints. El uso multiclúster existente de App Mesh debe tener en cuenta su retirada de septiembre de 2026. Compare los cargos por hora, procesamiento y entre AZ usando la ruta real; los diseños de misma VPC o de balanceador de carga público no son inherentemente inválidos, pero requieren su propio análisis de seguridad/costo.

</details>

### 4. ¿Qué característica de VPC CNI asigna direcciones IPv4 en bloques /28 para aumentar la densidad de slots de direcciones?

- A. hostNetwork para todos los Pods
- B. Delegación de prefijos
- C. NodePort para cada Service
- D. Global Accelerator para tráfico entre Pods

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Delegación de prefijos**

Un /28 de IPv4 delegado proporciona 16 direcciones de Pod y consume un slot de dirección ENI. Puede reducir el trabajo de API de asignación y mejorar el inicio/densidad de Pod; no es una optimización universal del rendimiento de paquetes ni una solución para el agotamiento total de subredes. IPv6 usa un tamaño de prefijo diferente. El hardware Nitro compatible, los prefijos libres contiguos, maxPods de kubelet y la capacidad de recursos aún restringen la densidad.

Fusione este fragmento JSON en la configuración exacta del add-on de EKS después de revisar el esquema/la propiedad, o use los valores `env` de Helm correspondientes. Las claves antiguas en minúsculas de ConfigMap `amazon-vpc-cni` no configuran el CNI de Linux:
```json
{
  "env": {
    "ENABLE_PREFIX_DELEGATION": "true",
    "WARM_PREFIX_TARGET": "1"
  }
}
```
`WARM_PREFIX_TARGET=1` significa un prefijo de reserva, no el tamaño del prefijo. Los valores positivos de `WARM_IP_TARGET`/`MINIMUM_IP_TARGET` tienen prioridad sobre el objetivo de prefijo de reserva. Los pools de reserva grandes reservan más espacio de subred. Planifique una transición de node group y la configuración de maxPods; alternar solo el DaemonSet no hace que los nodos existentes admitan una densidad arbitraria.

| Instancia | Fórmula convencional de maxPods de IPv4 secundarias | Límite ilustrativo del modo de prefijo para estas instancias pequeñas |
|---|---:|---:|
| t3.medium | 17 | 110 |
| m5.large | 29 | 110 |
| c5.xlarge | 58 | 110 |
| r5.2xlarge | 58 | 110 |

Estos son límites de configuración, no resultados de benchmark ni garantías de que todos los Pods quepan. Las anteriores 250 entradas para c5.xlarge/r5.2xlarge eran incorrectas: el límite recomendado por EKS es 110 con menos de 30 vCPU y 250 con 30 o más vCPU. Las interfaces de rama de Pod SG tienen límites independientes. La asignación de prefijos necesita bloques /28 contiguos, no una subred mínima /24 universal, y no simplifica automáticamente la política de SG.
```bash
set -euo pipefail
: "${AWS_REGION:?Set the node Region}"
kubectl get nodes -o 'custom-columns=NAME:.metadata.name,TYPE:.metadata.labels.node\.kubernetes\.io/instance-type,PODS:.status.allocatable.pods'
kubectl -n kube-system get daemonset aws-node -o yaml
kubectl -n kube-system logs -l k8s-app=aws-node -c aws-node --tail=200 --prefix=true
aws ec2 describe-instance-types --region "$AWS_REGION" \
  --instance-types t3.medium m5.large c5.xlarge r5.2xlarge \
  --query 'InstanceTypes[].{Type:InstanceType,vCPUs:VCpuInfo.DefaultVCpus,ENIs:NetworkInfo.MaximumNetworkInterfaces,IPv4Slots:NetworkInfo.Ipv4AddressesPerInterface}'
```

</details>

### 5. ¿Qué proxy usa el modo sidecar de Istio y cómo se diagnostica?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: Envoy**

El modo sidecar de Istio usa Envoy, con istiod proporcionando descubrimiento, enrutamiento y configuración de certificados. Las funciones antiguas de Pilot/Citadel se consolidaron en istiod y Mixer no es un componente requerido actualmente. Otros mesh pueden usar proxies distintos; Envoy no es un requisito de Kubernetes ni de todos los mesh.

Envoy admite pools de conexiones, enrutamiento HTTP/TCP, reintentos, detección de valores atípicos, TLS y telemetría cuando se configura. Añadir meramente un contenedor Envoy no organiza la interceptación transparente de tráfico, identidad de carga de trabajo, xDS ni mTLS. Para un mesh real, use su inyector y compilación de proxy compatibles. La imagen independiente antigua de Envoy 1.20 y el Deployment incompleto no eran una instalación actual válida.

El siguiente **bootstrap de proxy inverso independiente** ilustra los conceptos originales de listener/route/cluster. Se valida localmente con Envoy 1.39.1 upstream. Una aplicación HTTP independiente debe escuchar en `127.0.0.1:8080` en el mismo espacio de nombres de red. El proxy y el listener de administración se enlazan solo a loopback; no es un despliegue de mesh de producción ni de Kubernetes:
```yaml
admin:
  address:
    socket_address:
      address: 127.0.0.1
      port_value: 9901
static_resources:
  listeners:
  - name: local-proxy
    address:
      socket_address:
        address: 127.0.0.1
        port_value: 15001
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: demo_http
          route_config:
            name: local-route
            virtual_hosts:
            - name: backend
              domains: ["*"]
              routes:
              - match:
                  prefix: /
                route:
                  cluster: local-app
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              "@type": type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  clusters:
  - name: local-app
    connect_timeout: 0.25s
    type: STATIC
    lb_policy: ROUND_ROBIN
    load_assignment:
      cluster_name: local-app
      endpoints:
      - lb_endpoints:
        - endpoint:
            address:
              socket_address:
                address: 127.0.0.1
                port_value: 8080
```
Guárdelo como `envoy-config.yaml` y valídelo con el binario upstream correspondiente. La validación analiza la configuración; no demuestra que el backend o la identidad de carga de trabajo funcionen.
```bash
envoy --mode validate --concurrency 1 --config-path envoy-config.yaml
```
Para un proxy de mesh de Kubernetes existente, descubra el puerto de administración y el nombre del contenedor configurados en lugar de suponer 19000. El puerto de administración predeterminado de App Mesh es 9901; Istio suele usar 15000 y la configuración de despliegue puede variar. Ejecute este port-forward en una terminal:
```bash
set -euo pipefail
: "${MESH_NAMESPACE:?Set the existing mesh workload namespace}"
: "${MESH_POD:?Set the existing proxy Pod}"
: "${ENVOY_ADMIN_PORT:?Use the admin port actually configured by that mesh}"
kubectl -n "$MESH_NAMESPACE" port-forward --address 127.0.0.1 \
  "pod/$MESH_POD" "19000:$ENVOY_ADMIN_PORT"
```
Después emita consultas acotadas de solo lectura desde otra terminal. Los volcados de configuración pueden contener topología interna o configuración sensible; no los publique ni exponga externamente el listener de administración.
```bash
curl --fail --show-error --max-time 10 http://127.0.0.1:19000/config_dump
curl --fail --show-error --max-time 10 http://127.0.0.1:19000/stats
curl --fail --show-error --max-time 10 http://127.0.0.1:19000/clusters
```
Inspeccione conjuntamente el estado upstream, los límites de pool de conexiones, los reintentos, el costo de filtros, la memoria y la latencia de solicitudes. Ajuste a partir del comportamiento medido de la carga de trabajo; eliminar filtros de seguridad únicamente para reducir la sobrecarga cambia el modelo de seguridad.

</details>

### 6. ¿Qué proporciona DNS en los nodos convencionales de EKS y cómo debe configurarse?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: CoreDNS (primero identifique el propietario real de DNS/add-on).**

CoreDNS es el add-on de DNS habitual en el cómputo convencional de EKS. El método de creación/la propiedad del add-on pueden diferir; EKS Auto Mode incluye DNS de clúster administrado y no necesita inherentemente el Deployment tradicional de CoreDNS. Identifique el propietario de cómputo/DNS antes de aplicar las siguientes comprobaciones del add-on convencional. Una respuesta ResourceNotFound requiere investigar la propiedad, no una reinstalación automática:
```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the existing cluster}"
: "${AWS_REGION:?Set the cluster Region}"
aws eks describe-addon --region "$AWS_REGION" --cluster-name "$CLUSTER_NAME" \
  --addon-name coredns
kubectl -n kube-system get deployment coredns -o yaml
kubectl -n kube-system get configmap coredns -o yaml
kubectl -n kube-system get endpointslices -l kubernetes.io/service-name=kube-dns
```
DNS de Service normalmente sigue `<service>.<namespace>.svc.<cluster-domain>`; `cluster.local` es un dominio común, no inmutable. Los registros Headless/ExternalName difieren de los registros ClusterIP normales. No suponga que cada IP de Pod arbitraria tiene un registro DNS inverso útil.

Este es un **Corefile** ilustrativo, no un ConfigMap para sobrescribir a ciegas. Conserve la configuración administrada, el dominio real del clúster, las probes y el Service DNS. `pods insecure` permite respuestas DNS sintácticas de IP de Pod sin verificar el Pod; elija el modo previsto del plugin Kubernetes.
```text
.:53 {
    errors
    health {
        lameduck 5s
    }
    ready
    kubernetes cluster.local in-addr.arpa ip6.arpa {
        pods insecure
        fallthrough in-addr.arpa ip6.arpa
        ttl 30
    }
    prometheus :9153
    forward . /etc/resolv.conf
    cache 30
    loop
    reload
    loadbalance
}
```
`errors` registra fallos; `health` y `ready` cumplen funciones de probe distintas; `kubernetes` responde registros de clúster; `forward` resuelve otros dominios; `prometheus` expone métricas; `cache`, `reload` y `loadbalance` afectan el almacenamiento en caché, la recarga de configuración y el orden de registros. El plugin `loop` detecta ciertos bucles de reenvío simples durante el inicio, no todos los bucles DNS dinámicos indefinidamente. `loadbalance` cambia el orden de las respuestas DNS, no el reenvío de paquetes de Service.

Para reenvío condicional, use servidores DNS aprobados y accesibles y permita UDP/TCP53. La primera dirección de una subred VPC, como 10.0.0.1, no es un servidor DNS corporativo de ejemplo. El plugin `file` sirve un archivo de zona autoritativo que se debe crear/montar y mantener con SOA/registros válidos; no sustituye un reenvío de dominio de stub. Los resolvedores públicos requieren una política deliberada de egress y divulgación; no pueden resolver zonas alojadas privadas por arte de magia.

Este fragmento de caché corrige el orden original de argumentos: `prefetch AMOUNT DURATION PERCENTAGE`. Reemplace la directiva de caché existente en lugar de añadir una segunda:
```text
cache 30 {
    success 10000
    denial 1024
    prefetch 10 2m 10%
}
```
En CoreDNS upstream 1.14.7, `denial1000` se acepta pero se normaliza a1024; `success10000` se normaliza a9984. El valor explícito1024 conserva la capacidad de denegación efectiva original. Estas capacidades son comportamiento de implementación, no una recomendación de dimensionamiento DNS medida.

Elija un **único propietario de escalado**. Use el autoescalado administrado de CoreDNS por EKS cuando sea compatible con la versión/esquema exactos del add-on, o un HPA/autoscaler proporcional al clúster de propiedad independiente. El siguiente HPA es solo para un Deployment administrado deliberadamente por el usuario con metrics-server y solicitudes de CPU; no lo combine con otro administrador de réplicas:
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: coredns
  namespace: kube-system
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: coredns
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 60
```
El ejemplo original de recursos (solicitud de CPU de 100m, solicitud de memoria de 70Mi, límite de memoria de 170Mi) es ilustrativo, no está validado para la carga de trabajo. Supervise la tasa de consultas, los errores, el comportamiento de aciertos/fallos de caché, memoria/OOM y la latencia de respuesta, y después dimensione. Para el diagnóstico use una carga de trabajo de diagnóstico aprobada existente con herramientas DNS; inspeccione dnsPolicy/dnsConfig/resolv.conf, EndpointSlices de kube-dns y las rutas de política/SG/upstream. Pruebe por separado un Service del clúster y un nombre externo/privado aprobado. La imagen dnsutils obsoleta anterior y el Pod sin propietario no eran prerrequisitos para el diagnóstico de DNS.

</details>

### 7. ¿Cómo se debe proteger, observar y migrar un despliegue existente de App Mesh?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: Revise el grafo, la identidad y la telemetría existentes, y después valide un reemplazo compatible.**

**Ejercicio de operaciones históricas y migración:** El soporte y el acceso a recursos de AWS App Mesh finalizaron el **30 de septiembre de 2026**. No siga la receta original para aprovisionar un nuevo mesh, Private CA y Grafana público. Para un despliegue anterior de App Mesh, inventaríe su grafo y migre a un mesh/gateway compatible. ECS Service Connect no es un objetivo de instalación de EKS; evalúe una arquitectura de mesh/gateway de Kubernetes compatible para las características que realmente se usan.
```bash
set -euo pipefail
: "${MESH_NAMESPACE:?Set the namespace of the existing mesh workloads}"
kubectl get meshes.appmesh.k8s.aws
kubectl -n "$MESH_NAMESPACE" get virtualnodes.appmesh.k8s.aws,virtualservices.appmesh.k8s.aws,virtualrouters.appmesh.k8s.aws
kubectl -n "$MESH_NAMESPACE" get deployments,services
```
**1. Mapee el grafo existente.** Los selectores de namespace de mesh eligen los namespaces participantes; los selectores de Pod de VirtualNode eligen cargas de trabajo, listeners y descubrimiento de servicios. Los nombres de VirtualService se enrutan a un VirtualNode o VirtualRouter; las rutas de router seleccionan VirtualNodes ponderados. Inventaríe referencias de backend, DNS de endpoint, comprobaciones de salud, IAM/IRSA, configuración de inyector y puertos de escucha de aplicaciones. El marcador de posición original `service-a:latest` y las cargas de trabajo service-b ausentes no eran una aplicación funcional. No sobrescriba ServiceAccounts existentes ni adjunte políticas de acceso completo como paso de resolución de problemas.

**2. Distinga TLS de la autenticación mutua.** Un listener en modo STRICT con solo un certificado de servidor requiere conexiones cifradas, pero por sí solo no autentica clientes. App Mesh mTLS necesita certificados de cliente y confianza de cliente en el lado del servidor, así como confianza de servidor/comprobaciones de SAN en el lado del cliente. Los certificados de cliente y la confianza de validación de listener usan archivos o SDS, no una referencia de certificado de cliente de ACM. El tráfico de app a Envoy dentro de la carga de trabajo no se cifra automáticamente mediante mTLS de proxy a proxy.

Lo siguiente es un **ejemplo de revisión de configuración heredada**, no una instalación nueva. Sus archivos ya deben estar montados de forma segura en el proxy, los certificados deben tener las identidades/usos requeridos, service-b debe existir y el namespace coincidente debe pertenecer al Mesh previsto. Agregue restricciones SAN de cliente aprobadas según requiera el diseño de confianza; confiar solo en una CA acepta sus certificados de cliente elegibles:
```yaml
apiVersion: appmesh.k8s.aws/v1beta2
kind: VirtualNode
metadata:
  name: service-a
  namespace: app-namespace
spec:
  podSelector:
    matchLabels:
      app: service-a
  listeners:
  - portMapping:
      port: 8080
      protocol: http
    tls:
      mode: STRICT
      certificate:
        file:
          certificateChain: /certs/server.crt
          privateKey: /certs/server.key
      validation:
        trust:
          file:
            certificateChain: /certs/trusted-client-ca.pem
    outlierDetection:
      baseEjectionDuration:
        unit: s
        value: 30
      interval:
        unit: s
        value: 10
      maxEjectionPercent: 50
      maxServerErrors: 5
  backends:
  - virtualService:
      virtualServiceRef:
        name: service-b
      clientPolicy:
        tls:
          enforce: true
          ports: [8080]
          certificate:
            file:
              certificateChain: /certs/client.crt
              privateKey: /certs/client.key
          validation:
            trust:
              file:
                certificateChain: /certs/trusted-server-ca.pem
            subjectAlternativeNames:
              match:
                exact: [service-b.app-namespace.svc.cluster.local]
  serviceDiscovery:
    dns:
      hostname: service-a.app-namespace.svc.cluster.local
  logging:
    accessLog:
      file:
        path: /dev/stdout
```
No seleccione todas las CA ACTIVE de una cuenta en una variable. Crear una CA raíz requiere una configuración explícita y pasos de activación/certificado, e incurre en cargos; no produce inmediatamente un certificado utilizable. Conserve los ARN exactos previstos. Los campos de CRD de Kubernetes de App Mesh distinguen mayúsculas y minúsculas (`certificateARN`, `certificateAuthorityARNs`); `${CA_ARN}` en un archivo YAML plano no es interpolación de shell. El ejemplo mostrado basado en archivos evita fingir que se ha ejecutado un flujo de trabajo de CA inexistente.

Para pares existentes en texto sin cifrar, establezca una transición PERMISSIVE documentada, aprovisione identidades y confianza de cliente/servidor, pruebe tanto pares aceptados como rechazados y después exija STRICT. Inspeccione `ssl.handshake`, `ssl.no_certificate`, `ssl.fail_verify_no_cert` y `ssl.fail_verify_san` junto con los resultados reales de solicitudes. Un handshake TLS de servidor exitoso por sí solo no es prueba suficiente de mTLS.

**3. Conserve la observabilidad durante la migración.** `Mesh.spec.tracing`, `Mesh.spec.logging` y `Mesh.spec.serviceDiscovery` de la receta original no son campos en el CRD del controlador 1.13.1 revisado. El registro de acceso pertenece a VirtualNode (como arriba). La configuración de trazas de la imagen Envoy de App Mesh es independiente; por ejemplo, este **fragmento de entorno de contenedor** requiere un daemon/colector local de X-Ray funcional en2000, permisos, acceso al endpoint y propagación de contexto de trazas:
```yaml
env:
- name: ENABLE_ENVOY_XRAY_TRACING
  value: "1"
- name: XRAY_DAEMON_PORT
  value: "2000"
```
Recopile el endpoint `/stats` o Prometheus real del proxy con un collector aprobado. CloudWatch requiere scraping/exportación/EMF configurados; no suponga que las métricas RequestCount/Latency de `AWS/AppMesh` aparecen automáticamente. Inventaríe el namespace real, los nombres de métricas, las dimensiones y las unidades antes de crear un dashboard. Conserve el propietario, las credenciales y las StorageClasses compatibles existentes de CloudWatch/Prometheus/Grafana. Evite manifests flotantes, contraseñas de administrador de Grafana codificadas y un LoadBalancer público sin revisar. Este fragmento opcional de aprovisionamiento de Grafana solo identifica un datasource existente de Prometheus; no instala ni protege ninguno de los dos sistemas:
```yaml
apiVersion: 1
datasources:
- name: Prometheus
  type: prometheus
  url: http://prometheus-server.prometheus.svc.cluster.local
  access: proxy
  isDefault: true
```
**4. Mapee explícitamente el comportamiento del tráfico.** Este ejemplo de router heredado asume que ambos VirtualNodes versionados ya existen y tienen endpoints saludables. Los pesos no son garantías exactas del número de solicitudes. La detección de valores atípicos es expulsión de endpoints, distinta de los límites de circuit-breaking de pool de conexiones. Las cuatro cadenas originales de eventos de reintento HTTP son válidas: `client-error` significa 409 y `stream-error` significa flujos rechazados. Elija reintentos para operaciones idempotentes dentro del presupuesto general de tiempo de espera; los reintentos pueden amplificar la carga de fallos.
```yaml
apiVersion: appmesh.k8s.aws/v1beta2
kind: VirtualRouter
metadata:
  name: service-a-router
  namespace: app-namespace
spec:
  listeners:
  - portMapping:
      port: 8080
      protocol: http
  routes:
  - name: service-a-route
    httpRoute:
      match:
        prefix: /
      action:
        weightedTargets:
        - virtualNodeRef:
            name: service-a-v1
          weight: 90
        - virtualNodeRef:
            name: service-a-v2
          weight: 10
      retryPolicy:
        maxRetries: 3
        perRetryTimeout:
          unit: ms
          value: 2000
        httpRetryEvents:
        - gateway-error
```
**5. Valide y haga el cambio gradualmente.** Compare enrutamiento, pares autorizados/no autorizados, DNS, rotación TLS, reintentos, recuperación ante fallos, trazas y continuidad de métricas antes de mover tráfico. Conserve una ruta de reversión dentro de la ventana restante de soporte del producto. Los valores originales de CPU de proxy de100–200m y memoria de128–256Mi son **estimaciones de ejemplo no verificadas**, no mediciones ni dimensionamiento garantizado. Mida la saturación real, memoria, latencia y tasas de error. En esta auditoría no se aprovisionó ningún mesh, CA, collector ni dashboard de nube.

</details>

### 8. ¿Qué variable configura la MTU de ENI adjunta en VPC CNI 1.23.0?

- A. `ENI_MTU`
- B. `AWS_VPC_ENI_MTU`
- C. `VPC_MTU_SIZE`
- D. `MAX_ENI`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. `AWS_VPC_ENI_MTU`**

`POD_MTU` configura las interfaces virtuales de Pod y se deriva de la MTU de ENI cuando no se establece. `ENI_MTU` era el nombre incorrecto. Haga coincidir la MTU de la ruta real y el despliegue planificado de nodo/Pod; un valor numérico aceptado no garantiza que los gateways/túneles/endpoints remotos acepten ese tamaño de paquete. Los SG no son dispositivos para establecer MTU.

</details>

### 9. ¿Dónde pertenece la solución alternativa de early-demux de TCP estricto de Pod-SG?

- A. Deployment de aplicación
- B. ConfigMap de CoreDNS
- C. Contenedor init de CNI
- D. Anotación de LoadBalancer

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. `aws-vpc-cni-init`**

La configuración documentada `DISABLE_TCP_EARLY_DEMUX=true` pertenece al contenedor init, representada por Helm `init.env`. Establecerla en el contenedor principal `aws-node` no aplica ese cambio en el momento de init. Confirme el problema de kubelet probe en modo estricto; el modo Pod-SG estándar no requiere esta solución alternativa.

</details>

### 10. ¿Qué optimización de orden de reglas garantiza Kubernetes NetworkPolicy?

- A. Poner primero la regla más usada
- B. Ordenar los nombres alfabéticamente
- C. Crear las políticas restrictivas en último lugar
- D. No hay garantía de orden

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D. Ninguna; las autorizaciones coincidentes son aditivas.**

No hay una precedencia portátil de «primera coincidencia gana» o de política más reciente. Los selectores/direcciones y la unión de autorizaciones determinan el aislamiento. Las API de nivel/orden de proveedores son independientes. Conserve las restricciones necesarias y mida el costo de programación/ejecución de políticas en lugar de eliminar reglas basándose únicamente en su cantidad.

</details>

### 11. Una subred está agotada. ¿Aumentar WARM_IP_TARGET añade capacidad de direcciones?

- A. Sí, expande la subred
- B. No, aumenta la demanda de direcciones de reserva
- C. Sí, omite los límites de ENI
- D. Sí, repara cada Pod en ContainerCreating

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. No; solicita más direcciones de reserva.**

Un objetivo de reserva mayor puede reducir la latencia de asignación cuando existe capacidad, pero también reserva direcciones y puede empeorar el agotamiento. Identifique de forma independiente el espacio de subred, los slots de ENI, maxPods, la limitación de API y la fragmentación de prefijos. La delegación de prefijos no crea más direcciones IPv4 totales.

</details>

### 12. ¿Qué API se debe inspeccionar para obtener las direcciones y condiciones actuales de backend de Service?

- A. Solo eventos de Node
- B. Anotaciones de Ingress
- C. EndpointSlice
- D. Solo el ClusterIP de Service

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. EndpointSlice**

Consulte EndpointSlices en el namespace de Service usando `kubernetes.io/service-name=<service>`. Compruebe direcciones, puertos y condiciones ready/serving/terminating junto con el selector de Service y targetPort. El objeto Endpoints heredado puede truncar conjuntos de endpoints grandes; un resultado vacío puede indicar problemas de selector/readiness en lugar de un fallo del balanceador de carga.

</details>

### 13. ¿Qué significa trafficDistribution: PreferSameZone?

- A. Nunca cruzar un límite de AZ
- B. Preferir la misma zona con alternativa
- C. Mover los Pods existentes a una AZ
- D. Anular todas las políticas de tráfico Local

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Preferir endpoints disponibles en la misma zona, con alternativa.**

Es una preferencia de enrutamiento para un proxy de Service compatible, no una política de aislamiento de AZ. Asegure suficiente capacidad local. Una anotación Auto de modo topology existente tiene prioridad. Las políticas de tráfico interno/externo Local imponen requisitos más estrictos de nodo local para su tráfico respectivo y pueden descartar tráfico cuando no existe un endpoint local.

</details>

### 14. Calcule el producto de ancho de banda-retardo para un flujo hipotético de 10 Gbps con 20 ms de RTT.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: 25,000,000 bytes, aproximadamente 23.84 MiB.**

```text
10,000,000,000 bits/s × 0.020 s / 8 = 25,000,000 bytes
```
Este es un ejemplo aritmético, no un benchmark de EKS ni una recomendación de establecer cada buffer de socket con ese valor. Tenga en cuenta los límites reales de flujo único/ráfaga de EC2, el ajuste automático de TCP, el escalado de ventana, las conexiones simultáneas y la presión de memoria. Los máximos anteriores de 16 MiB no pueden considerarse óptimos sin mediciones. Keepalive opera en sockets inactivos habilitados; es independiente del pooling HTTP y del tamaño de buffers.

</details>

### 15. ¿Cómo se separan los fallos de DNS, selección de Service y conectividad de aplicación?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: Recopile evidencia y después pruebe el protocolo real con controles positivos.**

Compruebe los eventos del Pod afectado antes de clasificar ContainerCreating como networking. Resuelva un Service de clúster conocido y el hostname previsto, inspeccione la coherencia de selector-puerto-readiness de Service/EndpointSlice y después compare el acceso por IP de Pod y URL de Service desde el mismo origen. Pruebe una ruta permitida conocida para que una herramienta ausente, DNS fallido o backend inactivo no se confunda con una denegación de política. Use los diagnósticos acotados del capítulo fuente:
```bash
set -euo pipefail
: "${APP_NAMESPACE:?Set the affected namespace}"
: "${APP_POD:?Set the affected Pod}"
: "${APP_SERVICE:?Set the affected Service}"
kubectl -n "$APP_NAMESPACE" describe pod "$APP_POD"
kubectl -n "$APP_NAMESPACE" get events --field-selector "involvedObject.name=$APP_POD" --sort-by=.metadata.creationTimestamp
kubectl -n "$APP_NAMESPACE" get service "$APP_SERVICE" -o yaml
kubectl -n "$APP_NAMESPACE" get endpointslices \
  -l "kubernetes.io/service-name=$APP_SERVICE" -o yaml
kubectl -n "$APP_NAMESPACE" get networkpolicy
kubectl -n kube-system logs -l k8s-app=aws-node -c aws-node --tail=200 --prefix=true
```
Para un balanceador de carga, identifique el controlador/clase, esquema, tipo de destino y motivo de estado de salud del destino. Verifique los puertos reales de aplicación/salud, las rutas de SG y enrutamiento, TLS/SNI y el enrutamiento Host. El comportamiento de ICMP por sí solo no puede demostrar la aplicación de NetworkPolicy para TCP/UDP. Cambie una causa confirmada, conserve la ruta de reversión del propietario y repita las mismas comprobaciones. Estos ejemplos no afirman realizar pruebas de red de producción.

</details>

Referencias oficiales: [Private EKS](https://docs.aws.amazon.com/eks/latest/userguide/private-clusters.html), [VPC CNI 1.23.0](https://github.com/aws/amazon-vpc-cni-k8s/blob/v1.23.0/README.md), [CoreDNS cache](https://coredns.io/plugins/cache/), [App Mesh mTLS](https://docs.aws.amazon.com/app-mesh/latest/userguide/mutual-tls.html), [App Mesh metrics](https://docs.aws.amazon.com/app-mesh/latest/userguide/metrics.html), [Envoy 1.39.1](https://github.com/envoyproxy/envoy/releases/tag/v1.39.1).