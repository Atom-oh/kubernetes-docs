# Cuestionario sobre la creación de clústeres de EKS - Parte 3

> **Última actualización**: 11 de septiembre de 2026

Este cuestionario trata sobre redes de EKS, capacidad de los nodos, multitenencia, escalado automático y seguridad de los nodos. Los comandos y manifiestos son ejemplos didácticos; no se ha ejecutado ningún despliegue en la nube ni se ha probado el comportamiento integral durante esta revisión. Antes de usarlos, confirme la cuenta de destino, la región, el kubeconfig, las versiones compatibles de los complementos y quién es propietario de los recursos.

## Preguntas sobre conceptos básicos

1. En el cálculo convencional de direcciones IPv4 secundarias, ¿qué determina los límites de ENI y de direcciones por ENI?
   * A) El nombre del espacio de nombres
   * B) El tipo de instancia EC2
   * C) El nombre del servicio
   * D) El nombre del Deployment

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El tipo de instancia EC2**

En el **modo IPv4 de IP secundaria** para Linux, si hay suficientes direcciones en la subred y no se usan redes personalizadas ni grupos de seguridad para Pods, el tipo de instancia determina los límites de ENI y de direcciones por ENI. Esto permite estimar el límite convencional de Pods del nodo; no significa «direcciones IP por Pod».

La fórmula convencional reserva la dirección principal de **cada** ENI:

```text
ENIs × (IPv4 addresses per ENI − 1) + 2
```
Las dos adicionales corresponden a la asignación histórica para la red del host de `aws-node` y `kube-proxy`. La tabla conserva este cálculo del modo de IP secundarias; **no** representa el valor efectivo de `maxPods` para todas las AMI, modos de CNI o grupos de nodos administrados.

| Tipo de instancia | ENI máx. | IP por ENI | Pods máx. |
| ------------- | -------- | ----------- | -------- |
| t3.small      | 3        | 4          | 11       |
| t3.medium     | 3        | 6          | 17       |
| m5.large      | 3        | 10         | 29       |
| m5.xlarge     | 4        | 15         | 58       |
| m5.2xlarge    | 4        | 15         | 58       |
| m5.4xlarge    | 8        | 30         | 234      |
| c5.large      | 3        | 10         | 29       |
| c5.xlarge     | 4        | 15         | 58       |
| r5.large      | 3        | 10         | 29       |
| r5.xlarge     | 4        | 15         | 58       |

**Compruebe la capacidad y los límites reales de EC2:**

```bash
kubectl get nodes -o custom-columns=NAME:.metadata.name,TYPE:.metadata.labels.node\\.kubernetes\\.io/instance-type,CAPACITY:.status.capacity.pods,ALLOCATABLE:.status.allocatable.pods
aws ec2 describe-instance-types --region us-west-2 \
  --instance-types m5.large m5.4xlarge \
  --query 'InstanceTypes[].{Type:InstanceType,ENIs:NetworkInfo.MaximumNetworkInterfaces,IPv4PerENI:NetworkInfo.Ipv4AddressesPerInterface}'
```
El agotamiento de la subred puede impedir crear Pods incluso antes de alcanzar el límite del nodo. También influyen las solicitudes de CPU y memoria, otros Pods con red del host, las redes personalizadas, los grupos de seguridad para Pods y la configuración de kubelet. Los grupos de nodos administrados limitan `maxPods` a 110 en instancias con menos de 30 vCPU y a 250 en las demás, aunque la fórmula dé un valor mayor.

La delegación de prefijos IPv4 asigna un `/28` a una **ranura** de direcciones secundarias de una ENI; varias asignaciones de prefijos pueden ocupar una misma ENI. No crea espacio de direcciones adicional en la subred. Consulte la pregunta 5 para ver los requisitos previos y la migración.

En una AMI AL2023 personalizada, configure `spec.kubelet.config.maxPods` en NodeConfig después de calcular y probar un valor adecuado. En un grupo de nodos administrado sin un ID de AMI personalizado, EKS calcula el valor recomendado. Aumentar únicamente el límite de kubelet no crea direcciones IP ni capacidad de cómputo. No use la opción inexistente `--kubelet-extra-args` de eksctl.

</details>

2. Si ningún NetworkPolicy selecciona un Pod, ¿cuál es su estado de aislamiento según NetworkPolicy?
   * A) No aislado, sujeto a otros controles de red
   * B) Solo admite tráfico del mismo espacio de nombres
   * C) Requiere reglas de permiso explícitas
   * D) Deniega todo el tráfico

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) No aislado, sujeto a otros controles de red**

Si ninguna política selecciona un Pod para el sentido correspondiente del tráfico, Kubernetes NetworkPolicy deja ese sentido sin aislar. Esto **no** elude grupos de seguridad, tablas de rutas, ACL de red, otras API de políticas ni el proceso de escucha de la aplicación.

Amazon VPC CNI puede aplicar NetworkPolicy de forma nativa cuando se habilita en nodos EC2 Linux compatibles. La guía estándar y administrativa actual para políticas requiere VPC CNI 1.21 o posterior y kernel 5.10 o posterior; compruebe la compatibilidad de la versión del complemento elegida. Esta vía de aplicación no cubre Windows ni Fargate. Use Pods administrados por controladores (por ejemplo, Deployments) y compruebe las limitaciones de la interfaz de AWS y de los puertos de Service.

Calico Policy con redes de AWS VPC y el encadenamiento de Cilium con AWS-CNI son alternativas con sus propios requisitos de instalación. No instale un segundo CNI sin configurarlo ni acumule agentes de políticas por accidente. AWS Network Firewall filtra el tráfico enrutado de la VPC; no implementa selectores de Kubernetes NetworkPolicy.

Los ejemplos siguientes son para un espacio de nombres `network-policy-lab` **nuevo y dedicado**. La primera política aísla solo el ingreso. Las dos siguientes permiten tráfico específico; el par `prod` requiere tanto la etiqueta de espacio de nombres integrada como la etiqueta del Pod backend.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
  namespace: network-policy-lab
spec:
  podSelector: {}
  policyTypes: [Ingress]
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
  namespace: network-policy-lab
spec:
  podSelector:
    matchLabels: {app: backend}
  policyTypes: [Ingress]
  ingress:
  - from:
    - podSelector:
        matchLabels: {app: frontend}
    ports:
    - {protocol: TCP, port: 8080}
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-prod-to-database
  namespace: network-policy-lab
spec:
  podSelector:
    matchLabels: {app: database}
  policyTypes: [Ingress]
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: prod
      podSelector:
        matchLabels: {app: backend}
    ports:
    - {protocol: TCP, port: 5432}
```
Para aislar el egreso, permita por separado la ruta DNS real y las dependencias de la aplicación. Un intento de conexión denegado solo aporta información después de que funcionen la conectividad de referencia, DNS, disponibilidad y un control positivo permitido. No aplique políticas de denegación general a `kube-system` ni a un espacio de nombres `default` compartido como prueba rápida.

</details>

3. ¿Cuál es una ruta convencional de salida a Internet para una subred IPv4 privada?
   * A) Asociar una IGW a la subred
   * B) Enrutar a una puerta de enlace NAT pública y, después, a la IGW de la VPC
   * C) Asignar una Elastic IP a cada Pod
   * D) Enrutar directamente una puerta de enlace NAT privada a través de una IGW

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Enrutar a una puerta de enlace NAT pública y, después, a la IGW de la VPC**

Para proporcionar salida IPv4 a Internet a nodos y Pods de subredes privadas, un diseño común enruta la ruta predeterminada de la subred privada a una **puerta de enlace NAT pública situada en una subred pública**. Esa subred pública enruta a una puerta de enlace de Internet asociada a la **VPC**, y la puerta de enlace NAT tiene una Elastic IP. Una instancia NAT es otra opción, con requisitos adicionales de enrutamiento, comprobación de origen/destino y operación.

Con el comportamiento predeterminado de SNAT IPv4 de VPC CNI, el tráfico de Pods que sale de la VPC usa primero la dirección IPv4 principal del nodo. Los nodos públicos con una dirección IPv4 pública y una ruta a una IGW pueden seguir otra ruta. La salida IPv6 nativa puede usar una puerta de enlace de Internet de solo salida; para acceder a servicios de AWS mediante endpoints de VPC quizá no haga falta NAT a Internet. No suponga que NAT sea un requisito universal para todos los Pods.

**Ejemplo de enrutamiento de CloudFormation para una AZ:** muestra las asociaciones de rutas públicas y privadas; no es una VPC EKS completa. Las subredes del clúster EKS necesitan al menos dos AZ. En un diseño NAT zonal, considere una puerta de enlace NAT y una ruta privada por AZ para evitar dependencias entre AZ. Las puertas de enlace NAT y las direcciones IPv4 públicas tienen cargos. Para desplegar un clúster, consulte la plantilla completa de VPC EKS en la guía de conceptos.

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: One-AZ IPv4 NAT routing demonstration; not a complete EKS VPC
Resources:
  VPC:
    Type: AWS::EC2::VPC
    Properties:
      CidrBlock: 10.0.0.0/16
      EnableDnsSupport: true
      EnableDnsHostnames: true
      Tags:
        - Key: Name
          Value: EKS-VPC

  PublicSubnet1:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      AvailabilityZone: !Select [0, !GetAZs ""]
      CidrBlock: 10.0.0.0/24
      MapPublicIpOnLaunch: false
      Tags:
        - Key: Name
          Value: Public-Subnet-1

  PrivateSubnet1:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      AvailabilityZone: !Select [0, !GetAZs ""]
      CidrBlock: 10.0.2.0/24
      Tags:
        - Key: Name
          Value: Private-Subnet-1

  InternetGateway:
    Type: AWS::EC2::InternetGateway
    Properties:
      Tags:
        - Key: Name
          Value: EKS-IGW

  VPCGatewayAttachment:
    Type: AWS::EC2::VPCGatewayAttachment
    Properties:
      VpcId: !Ref VPC
      InternetGatewayId: !Ref InternetGateway

  NatGatewayEIP:
    Type: AWS::EC2::EIP
    DependsOn: VPCGatewayAttachment
    Properties:
      Domain: vpc

  NatGateway:
    Type: AWS::EC2::NatGateway
    Properties:
      AllocationId: !GetAtt NatGatewayEIP.AllocationId
      SubnetId: !Ref PublicSubnet1
      Tags:
        - Key: Name
          Value: EKS-NAT-GW

  PublicRouteTable:
    Type: AWS::EC2::RouteTable
    Properties:
      VpcId: !Ref VPC
      Tags:
        - Key: Name
          Value: Public-RT

  PublicRoute:
    Type: AWS::EC2::Route
    DependsOn: VPCGatewayAttachment
    Properties:
      RouteTableId: !Ref PublicRouteTable
      DestinationCidrBlock: 0.0.0.0/0
      GatewayId: !Ref InternetGateway

  PrivateRouteTable:
    Type: AWS::EC2::RouteTable
    Properties:
      VpcId: !Ref VPC
      Tags:
        - Key: Name
          Value: Private-RT

  PrivateRoute:
    Type: AWS::EC2::Route
    Properties:
      RouteTableId: !Ref PrivateRouteTable
      DestinationCidrBlock: 0.0.0.0/0
      NatGatewayId: !Ref NatGateway

  PublicSubnetAssociation:
    Type: AWS::EC2::SubnetRouteTableAssociation
    Properties:
      SubnetId: !Ref PublicSubnet1
      RouteTableId: !Ref PublicRouteTable

  PrivateSubnetAssociation:
    Type: AWS::EC2::SubnetRouteTableAssociation
    Properties:
      SubnetId: !Ref PrivateSubnet1
      RouteTableId: !Ref PrivateRouteTable
```
Los recursos `SubnetRouteTableAssociation` son esenciales: crear rutas en una tabla que no está asociada no cambia la ruta de ninguna de las dos subredes.

Después de un despliegue revisado de forma independiente, inspeccione los ID y las rutas reales. Si en su lugar crea una puerta de enlace NAT con la CLI, capture el ID que devuelve y espere a que su estado sea `nat-gateway-available` antes de crear una ruta. Si falla la creación de NAT, detenga el flujo de trabajo.

```bash
set -euo pipefail
: "${AWS_REGION:?Set the Region}"
: "${VPC_ID:?Set the deployed VPC ID}"
aws ec2 describe-route-tables --region "$AWS_REGION" \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query 'RouteTables[].{Id:RouteTableId,Associations:Associations,Routes:Routes}'
aws ec2 describe-nat-gateways --region "$AWS_REGION" \
  --filter "Name=vpc-id,Values=$VPC_ID" \
  --query 'NatGateways[].{Id:NatGatewayId,Subnet:SubnetId,State:State}'
```
`vpc.nat.gateway: Single` de eksctl es válido para su flujo de creación de VPC administrada, pero introduce una dependencia de una sola AZ. `HighlyAvailable` crea una NAT zonal en cada AZ. Estas opciones no corrigen el enrutamiento de subredes existentes arbitrarias. En una pila de laboratorio, elimine solo los recursos que haya creado, después de retirar las cargas de trabajo/ENI dependientes; confirme que se hayan liberado la NAT y su EIP.

</details>

4. ¿Qué ajuste de Pod comparte la red del nodo en lugar de usar una ENI de rama del Pod?
   * A) Una etiqueta coincidente del Pod
   * B) Una etiqueta coincidente de ServiceAccount
   * C) `hostNetwork: true`
   * D) Una SecurityGroupPolicy seleccionada

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) `hostNetwork: true`**

Un Pod que usa la red del host comparte el espacio de nombres de red y los grupos de seguridad del nodo. Los grupos de seguridad para Pods usan ENI de rama para los Pods seleccionados, que tienen su propio espacio de nombres de red.

Los requisitos de este ejemplo para Linux en EC2 incluyen un tipo de instancia compatible con trunking, una versión compatible de VPC CNI, permisos `AmazonEKSVPCResourceController` para el rol del clúster y `ENABLE_POD_ENI=true`. Las familias EC2 `t` y EKS Auto Mode no admiten esta función. Compruebe DNS, las reglas del plano de control y de la aplicación, la capacidad de ENI de rama y `POD_SECURITY_GROUP_ENFORCING_MODE`; el comportamiento de SNAT y las políticas cambia según el modo. Use el flujo de configuración del propietario del complemento en vez de aplicar un manifiesto antiguo de CNI.

SecurityGroupPolicy selecciona Pods mediante `podSelector` **o** `serviceAccountSelector`; no es obligatorio crear una ServiceAccount especial para seleccionar Pods. `ENIConfig` es un recurso para redes personalizadas y no es necesario solo para usar grupos de seguridad para Pods.

Para la alternativa con selector de ServiceAccount que sigue, cree primero un espacio de nombres dedicado `pod-sg-lab`, reemplace el marcador del grupo de seguridad por un grupo existente y revisado en la VPC correcta, y cumpla los requisitos previos. Este cliente en espera demuestra la selección; no demuestra conectividad con una base de datos. Están presentes tanto una etiqueta coincidente en ServiceAccount como el `serviceAccountName` del Pod.

```yaml
apiVersion: vpcresources.k8s.aws/v1beta1
kind: SecurityGroupPolicy
metadata:
  name: db-client-policy
  namespace: pod-sg-lab
spec:
  serviceAccountSelector:
    matchLabels:
      role: db-client
  securityGroups:
    groupIds:
    - sg-REPLACE_WITH_REVIEWED_GROUP
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: db-client
  namespace: pod-sg-lab
  labels:
    role: db-client
automountServiceAccountToken: false
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: db-client
  namespace: pod-sg-lab
spec:
  replicas: 1
  selector:
    matchLabels: {app: db-client}
  template:
    metadata:
      labels: {app: db-client}
    spec:
      serviceAccountName: db-client
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        seccompProfile: {type: RuntimeDefault}
      containers:
      - name: client
        image: public.ecr.aws/docker/library/busybox:1.38.0
        command: [sleep, '3600']
        resources:
          requests: {cpu: 10m, memory: 16Mi}
          limits: {cpu: 100m, memory: 32Mi}
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities: {drop: [ALL]}
```
Como alternativa, reemplace `serviceAccountSelector` por `podSelector: {matchLabels: {app: db-client}}`. Mantenga la política y los Pods seleccionados en el mismo espacio de nombres. Compruebe la ENI de rama y las conexiones permitidas/denegadas reales de un Pod **recién creado**; crear una política no modifica los Pods que ya se están ejecutando. Tras la prueba, limpie únicamente este espacio de nombres de laboratorio y su política, y no elimine un grupo de seguridad que sigan usando otros recursos.

</details>


5. ¿Cuál es la principal ventaja de capacidad de la delegación de prefijos IPv4?
   * A) Garantiza un tráfico Pod a Pod más rápido
   * B) Aumenta la capacidad de IP de Pods por nodo
   * C) Proporciona una dirección IPv4 pública a cada Pod
   * D) Aísla la red automáticamente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Aumenta la capacidad de IP de Pods por nodo**

En el modo de prefijos IPv4 para Linux, un `/28` (16 direcciones) ocupa una ranura de direcciones secundarias de la ENI. Se pueden asociar varios prefijos a una ENI; el número máximo de ENI no aumenta. Esto puede elevar la densidad de Pods basada en IP y reducir las llamadas a la API de asignación de direcciones, sujeto a los límites de kubelet y de recursos.

Para `m5.large`, el cálculo convencional de IP secundarias da 29 Pods. Un grupo de nodos administrado compatible en modo de prefijos puede usar el valor recomendado `maxPods` de 110, no un valor ilimitado «superior a 110». Las ranuras de direcciones teóricas no garantizan la capacidad de una aplicación.

**Requisitos previos y concesiones:**

* Use una instancia Nitro compatible y una versión compatible de CNI (el mínimo histórico para IPv4 Linux es 1.9.0; elija una versión que siga siendo compatible).
* La subred necesita bloques `/28` contiguos. Una subred fragmentada puede fallar con `InsufficientCidrBlocks` aunque tenga muchas IP individuales libres. Las reservas de CIDR de subred pueden preservar espacio para prefijos.
* Los prefijos consumen direcciones reales de la subred en bloques. No amplían un CIDR ni garantizan menor consumo de IP, mejor utilización o menor costo.
* `WARM_PREFIX_TARGET` especifica prefijos libres. `WARM_IP_TARGET` especifica IP libres; `MINIMUM_IP_TARGET` establece una asignación total mínima. Si se configuran, los dos últimos prevalecen sobre `WARM_PREFIX_TARGET`. Ajústelos teniendo en cuenta la latencia de lanzamiento y el consumo de direcciones no utilizadas.
* Planifique grupos de nodos de reemplazo y una migración controlada con cordón y drenaje. No se limite a cambiar la variable y reiniciar todos los Pods. Compruebe PDB, volúmenes, capacidad disponible y reversión; valide los nodos nuevos antes de retirar los grupos antiguos.

El ejemplo siguiente es una **configuración para un clúster nuevo**, no un comando para actualizar uno existente. Usa acceso privado a la API, por lo que el administrador necesita una ruta de administración enrutada. Si no se especifica una versión, se selecciona la compilación predeterminada compatible de CNI de EKS; registre y revise la versión realmente resuelta antes del despliegue. `withOIDC` participa en la integración IAM de CNI de eksctl; revise el rol resultante. Los límites de tamaño no instalan un autoscaler.

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: prefix-demo
  region: us-west-2
  version: "1.36"
vpc:
  clusterEndpoints:
    publicAccess: false
    privateAccess: true
iam:
  withOIDC: true
addons:
- name: vpc-cni
  configurationValues: |
    {"env":{"ENABLE_PREFIX_DELEGATION":"true","WARM_PREFIX_TARGET":"1"}}
managedNodeGroups:
- name: prefix-linux
  amiFamily: AmazonLinux2023
  instanceType: m5.large
  desiredCapacity: 2
  minSize: 2
  maxSize: 5
  privateNetworking: true
  disableIMDSv1: true
```

</details>

6. ¿Qué objeto de Kubernetes contiene el Corefile que consume CoreDNS?
   * A) Un grupo de seguridad del nodo
   * B) El ConfigMap `coredns`
   * C) Una StorageClass
   * D) Un PodDisruptionBudget

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El ConfigMap `coredns`**

El ConfigMap `coredns` contiene `data.Corefile`. El **propietario de la configuración** adecuado depende de si CoreDNS es un complemento administrado de EKS o es autoadministrado.

Para el complemento administrado, tanto la consola de AWS como `aws eks update-addon --configuration-values` permiten personalizar los campos compatibles. Una edición directa del ConfigMap puede sobrescribirse al actualizar el complemento: almacene el Corefile personalizado completo en la clave de configuración `corefile` del complemento. Conserve las claves de configuración existentes y consulte el esquema de la versión exacta del complemento.

Use un directorio de trabajo local nuevo para guardar la configuración actual antes de editarla:

```bash
set -euo pipefail
: "${EXAMPLE_CLUSTER:?Set the cluster}"
: "${EXAMPLE_REGION:?Set the Region}"
: "${EXAMPLE_KUBECONFIG:?Set a private kubeconfig path}"
aws eks describe-addon --cluster-name "$EXAMPLE_CLUSTER" \
  --region "$EXAMPLE_REGION" --addon-name coredns > coredns-addon-before.json
COREDNS_VERSION=$(jq -er '.addon.addonVersion' coredns-addon-before.json)
aws eks describe-addon-configuration --region "$EXAMPLE_REGION" \
  --addon-name coredns --addon-version "$COREDNS_VERSION" \
  --query configurationSchema --output text > coredns-schema.json
jq -e '(.addon.configurationValues // "{}") | fromjson | select(type == "object")' \
  coredns-addon-before.json > coredns-values-before.json
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n kube-system \
  get configmap coredns -o json | jq -er '.data.Corefile' > Corefile.reviewed
```
Edite `Corefile.reviewed` y conserve los plugins de zona Kubernetes, reenvío, `ready`, health y supervisión que necesite esta instalación. Son ejemplos de personalización distintos, no un Corefile de reemplazo:

* Añada registros estáticos al bloque de servidor existente; use las direcciones internas reales:

```text
hosts {
    10.0.0.1 example.com
    10.0.0.2 api.example.com
    fallthrough
}
```
* Use un bloque de servidor independiente para un reenviador condicional; el servidor ascendente debe ser accesible y no debe reenviar de vuelta a este servicio de CoreDNS:

```text
example.org:53 {
    errors
    forward . 10.0.0.53
    cache 30
}
```
* Reemplace la directiva de caché existente en vez de añadir un duplicado. La duración de `prefetch` debe incluir una unidad:

```text
cache {
    success 10000
    denial 5000
    prefetch 10 10m 10%
}
```
* Registro opcional de consultas con errores (revise el volumen y los nombres sensibles):

```text
log {
    class error
}
```
`autopath` es un plugin independiente para completar rutas de búsqueda en el servidor, no una subdirectiva de `kubernetes`. `autopath off` dentro del bloque de Kubernetes no es válido. Para deshabilitar un `autopath @kubernetes` existente, elimine esa directiva; no la añada en instalaciones donde nunca se habilitó.

Después de revisar el esquema y la sintaxis, actualice la **misma** versión del complemento:

```bash
# After reviewing the complete Corefile and existing configuration:
jq --rawfile corefile Corefile.reviewed '.corefile = $corefile' \
  coredns-values-before.json > coredns-values-reviewed.json
COREDNS_UPDATE_ID=$(aws eks update-addon \
  --cluster-name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --addon-name coredns --addon-version "$COREDNS_VERSION" \
  --resolve-conflicts PRESERVE \
  --configuration-values file://coredns-values-reviewed.json \
  --query update.id --output text)
aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --addon-name coredns --update-id "$COREDNS_UPDATE_ID" \
  --query 'update.{status:status,errors:errors}'
```
La respuesta todavía puede indicar `InProgress`. Vuelva a consultar este ID de actualización hasta que el estado sea `Successful`; si falla, deténgase e inspeccione los errores antes de realizar otro cambio. Después compruebe que Deployment esté listo, sus registros, la resolución del Service interno y los casos DNS personalizados. Si hace falta, restaure la configuración guardada mediante el mismo propietario.

En CoreDNS autoadministrado, edite el ConfigMap revisado mediante el propietario de GitOps/manifiestos. Con `reload`, los cambios del Corefile se detectan después de proyectar el ConfigMap y transcurrir el intervalo de recarga; no siempre hace falta reiniciar. Supervise los errores de recarga y el comportamiento de DNS. Los cambios en la configuración de Deployment sí pueden requerir un rollout.

**Escalado y recursos:** CoreDNS administrado de EKS admite un objeto de configuración `autoScaling` si la versión elegida cumple los requisitos previos de AWS. Mantenga un solo controlador a cargo de las réplicas. El siguiente HPA de CPU es una **alternativa para CoreDNS autoadministrado**, que requiere Metrics Server y solicitudes de CPU; no lo ejecute junto con el escalado automático de CoreDNS de EKS:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: coredns-autoscaler
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
El rango de 2 a 10 réplicas y el objetivo del 60 % son ejemplos, no una estimación basada en mediciones. Revise la memoria, la limitación de CPU, el crecimiento de la caché, la topología y la latencia DNS; cambie los recursos mediante el esquema del complemento o el propietario de la carga autoadministrada, en vez de reemplazar un objeto de recursos completo mediante el índice de un arreglo de contenedores.

</details>

7. ¿Qué combinación permite el aislamiento lógico de equipos de confianza que comparten un clúster de EKS?
   * A) Solo espacios de nombres
   * B) Espacios de nombres, RBAC, políticas aplicadas y cuotas
   * C) Solo selectores de nodos
   * D) Un rol compartido de administrador del clúster

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Espacios de nombres, RBAC, políticas aplicadas y cuotas**

Para equipos de confianza mutua que comparten un clúster, los espacios de nombres junto con RBAC, políticas de red aplicadas y cuotas ofrecen una separación lógica útil. No son una solución universal para inquilinos hostiles.

El administrador de la plataforma crea los espacios de nombres nuevos `tenant-a`/`tenant-b` y aplica una política adecuada de Pod Security Admission (para este ejemplo Linux en EKS 1.36, Restricted con versión `v1.36`). El siguiente conjunto de políticas es para `tenant-a`; aplique una política equivalente y revisada a `tenant-b`. También se requiere una asignación de grupo autenticado para `tenant-a-users`.

Los permisos de la aplicación son explícitos. Este Role no permite al inquilino cambiar directamente ResourceQuota, LimitRange, NetworkPolicy, Roles ni RoleBindings. Los recursos con alcance de clúster siguen siendo propiedad de la plataforma.

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: tenant-workloads
  namespace: tenant-a
rules:
- apiGroups: ["apps"]
  resources: ["deployments", "statefulsets", "deployments/scale", "statefulsets/scale"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: ["batch"]
  resources: ["jobs", "cronjobs"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: [""]
  resources: ["services", "configmaps", "persistentvolumeclaims"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: [""]
  resources: ["pods", "pods/log", "events"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: tenant-a-access
  namespace: tenant-a
subjects:
- kind: Group
  name: tenant-a-users
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: tenant-workloads
  apiGroup: rbac.authorization.k8s.io
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: tenant-boundary
  namespace: tenant-a
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
  ingress:
  - from:
    - podSelector: {}
  egress:
  - to:
    - podSelector: {}
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - {protocol: UDP, port: 53}
    - {protocol: TCP, port: 53}
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: tenant-quota
  namespace: tenant-a
spec:
  hard:
    requests.cpu: "10"
    requests.memory: 20Gi
    limits.cpu: "20"
    limits.memory: 40Gi
    pods: "50"
    services: "20"
    persistentvolumeclaims: "30"
    secrets: "100"
    configmaps: "100"
---
apiVersion: v1
kind: LimitRange
metadata:
  name: tenant-limits
  namespace: tenant-a
spec:
  limits:
  - default:
      cpu: 500m
      memory: 512Mi
    defaultRequest:
      cpu: 100m
      memory: 256Mi
    type: Container
```
**Límites y validación:**

* La creación de cargas de trabajo aún puede permitir usar ServiceAccounts accesibles y montar Secrets del espacio de nombres. Este Role no constituye un límite de confidencialidad para Secrets dentro de un inquilino. Aplique políticas de admisión para controlar las identidades, los montajes y la configuración de seguridad permitidos; mantenga las credenciales de la plataforma fuera de los espacios de nombres de inquilinos.
* La regla DNS presupone Pods ordinarios de CoreDNS etiquetados `k8s-app=kube-dns` en `kube-system`. Adáptela y pruébela con NodeLocal DNSCache u otra ruta DNS. Permite consultas DNS, no todo el egreso hacia Pods del sistema; tampoco oculta los nombres DNS de otros espacios de nombres.
* Las cuotas limitan las solicitudes de recursos y el número de objetos admitidos; no reservan nodos físicos, garantizan ancho de banda ni eliminan la interferencia de vecinos. Los valores de LimitRange son valores predeterminados ilustrativos.
* Antes de incorporar equipos, compruebe los permisos efectivos y la aplicación de políticas con una identidad de inquilino, conexiones permitidas, conexiones entre inquilinos denegadas y casos de rechazo de cuota.
* Los grupos de nodos dedicados reducen algunas formas de uso compartido, pero los selectores y taints por sí solos no son límites de seguridad. Para un aislamiento más sólido, evalúe runtimes aislados, planos de control virtuales o clústeres/cuentas/redes separados, teniendo en cuenta sus dependencias compartidas y costos operativos.

Compartir espacios de nombres puede reducir la sobrecarga del plano de control y simplificar las operaciones centralizadas. El diseño lo determina el nivel de aislamiento requerido, no una afirmación universal de que exista una opción «óptima».

</details>

8. ¿Qué elemento no cambia por sí solo la capacidad técnica de un tipo de instancia EC2?
   * A) La cantidad de vCPU y memoria
   * B) Los límites de red y almacenamiento
   * C) Una etiqueta de nombre que solo se muestra
   * D) Los límites de ENI y direcciones

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Una etiqueta de nombre que solo se muestra**

Al elegir una instancia, tenga en cuenta CPU, memoria, aceleradores, imágenes/AMI y controladores compatibles con la arquitectura, densidad de Pods, ancho de banda de red, rendimiento de EBS/almacenamiento de instancia, disponibilidad por AZ, tolerancia a interrupciones y costo. La versión de Kubernetes puede influir por las AMI, los controladores y las funciones compatibles; no es irrelevante.

Los ejemplos originales de familias siguientes ilustran tipos de cargas de trabajo, no una clasificación actual de precio/rendimiento. `m5` es de uso general, `r5` está optimizada para memoria y `c5` para cómputo. Las alternativas Graviton requieren imágenes y dependencias compatibles con Arm. Las cargas GPU también necesitan una AMI acelerada y un plugin de dispositivo adecuados. Los datos de almacenamiento de instancia son efímeros; las etiquetas por sí solas tampoco garantizan durabilidad para una base de datos ni determinan la ubicación de los Pods.

Estos archivos son **configuraciones alternativas de grupos de nodos** para un clúster existente y revisado (`eksctl create nodegroup -f ...`), con nombres de grupo que no estén en uso y subredes privadas que dispongan del egreso/endpoints requeridos. Revise la oferta real en cada región/AZ. Los límites no instalan Cluster Autoscaler; un grupo de procesamiento por lotes con capacidad cero requiere un autoscaler bien configurado o escalado manual.

**Servidores web**

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: web-servers
  instanceType: m5.large
  minSize: 2
  maxSize: 10
  labels:
    role: web
  amiFamily: AmazonLinux2023
  privateNetworking: true
```

**Cargas de trabajo de bases de datos**

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: database-nodes
  instanceType: r5.xlarge
  minSize: 3
  maxSize: 5
  labels:
    role: database
  amiFamily: AmazonLinux2023
  privateNetworking: true
```

**Procesamiento por lotes**

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: batch-processors
  instanceType: c5.2xlarge
  minSize: 0
  maxSize: 20
  labels:
    role: batch
  amiFamily: AmazonLinux2023
  privateNetworking: true
```

**Workers Spot interrumpibles**

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: spot-workers
  instanceTypes:
  - m5.large
  - m5a.large
  - m5d.large
  - m5ad.large
  minSize: 2
  maxSize: 10
  spot: true
  labels:
    lifecycle: spot
  amiFamily: AmazonLinux2023
  privateNetworking: true
```
EKS ofrece 14 meses de soporte estándar para una versión, seguidos de 12 meses de soporte extendido. Consulte el calendario de soporte de EKS, los requisitos de actualización y la compatibilidad de complementos por separado de las versiones de Kubernetes upstream. Estos ejemplos no afirman ahorros de costos ni capacidad medidos.

</details>

9. ¿Qué objeto de Kubernetes limita el desalojo voluntario de Pods durante un drenaje?
   * A) StorageClass
   * B) PodDisruptionBudget
   * C) ConfigMap
   * D) IngressClass

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) PodDisruptionBudget**

Un PDB limita los desalojos voluntarios a través de la API Eviction. Es parte de una estrategia de actualización, no una garantía de disponibilidad. No impide un fallo del nodo, el borrado directo de un Pod ni una actualización gradual propia de Deployment.

Para un Deployment `update-lab` revisado con tres réplicas etiquetadas `app=my-app`, este ejemplo solo permite el desalojo si quedan al menos dos Pods seleccionados en buen estado:

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: app-pdb
  namespace: update-lab
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: my-app
```
Una alternativa es `maxUnavailable: "50%"`; especifique un solo campo de presupuesto. El redondeo de porcentajes es **hacia arriba**, de modo que aquí se permiten dos Pods no disponibles de tres, o uno de uno. No garantiza que permanezca disponible al menos la mitad. Elija los presupuestos según el quórum, la disponibilidad, el comportamiento de la carga y la capacidad programable de reserva.

Las actualizaciones `DEFAULT` de grupos de nodos administrados lanzan capacidad de reemplazo antes de drenar los nodos antiguos seleccionados. `MINIMAL` reduce las necesidades temporales de capacidad al terminar primero los nodos antiguos seleccionados. `maxUnavailable` controla cuántos nodos pueden estar no disponibles simultáneamente; los PDB limitan por separado el desalojo de Pods. No use `--force` como respuesta rutinaria a un drenaje bloqueado: puede omitir la protección de desalojo de Pods.

Configure la política de actualización de nodos y espere a que esta actualización concreta termine correctamente **antes** de iniciar una actualización de versión:

```bash
set -euo pipefail
NODEGROUP_UPDATE_ID=$(aws eks update-nodegroup-config \
  --cluster-name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --nodegroup-name "${EXAMPLE_NODEGROUP:?}" \
  --update-config '{"maxUnavailable":1,"updateStrategy":"DEFAULT"}' \
  --query update.id --output text)
aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --nodegroup-name "$EXAMPLE_NODEGROUP" --update-id "$NODEGROUP_UPDATE_ID" \
  --query 'update.{status:status,errors:errors}'
```
Consulte `describe-update` periódicamente para ese ID hasta que el estado sea `Successful`, gestionando explícitamente `Failed`/`Cancelled`. El comando original de eksctl `update nodegroup --max-unavailable` no es una alternativa compatible. Compruebe el valor real de `disruptionsAllowed` del PDB, la disponibilidad, el estado de la aplicación y la reubicación de volúmenes; una disposición de tres réplicas es un ejemplo, no un mínimo universal.

</details>

10. ¿Qué controlador recomienda o cambia las solicitudes de CPU y memoria de los Pods?
   * A) Cluster Autoscaler
   * B) Karpenter
   * C) Horizontal Pod Autoscaler
   * D) Vertical Pod Autoscaler

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Vertical Pod Autoscaler**

VPA recomienda o actualiza las solicitudes de recursos de los Pods. HPA cambia el número de réplicas. **Ambos** pueden cambiar indirectamente la demanda de nodos; ninguno administra directamente el ASG de un grupo de nodos administrado.

| Componente | Objeto que controla |
| --- | --- |
| Cluster Autoscaler | Capacidad deseada de grupos de nodos/ASG existentes detectados, según la posibilidad de programar y retirar nodos de forma segura |
| Karpenter | Sus propios NodeClaims/capacidad EC2, seleccionados mediante NodePools y EC2NodeClasses; no los ASG de grupos de nodos administrados |
| HPA / KEDA | Réplicas de cargas de trabajo según métricas de recursos/personalizadas/externas o eventos |
| VPA | Recomendaciones/solicitudes de recursos de Pods según el modo de actualización |

**Cluster Autoscaler:** use la misma versión secundaria de Kubernetes que el clúster. Para el ejemplo EKS 1.36, el chart 9.59.0 debe usar explícitamente la imagen `v1.36.1` (su imagen predeterminada es 1.35.0). Primero configure una ServiceAccount dedicada `cluster-autoscaler` con permisos IAM revisados y limitados por etiquetas, y etiquetas de detección de ASG. Renderice e inspeccione RBAC, imagen y argumentos antes de instalar:

```bash
helm repo add autoscaler https://kubernetes.github.io/autoscaler
helm repo update autoscaler
helm template cluster-autoscaler autoscaler/cluster-autoscaler \
  --version 9.59.0 --namespace kube-system \
  --set-string autoDiscovery.clusterName="${EXAMPLE_CLUSTER:?}" \
  --set-string awsRegion="${EXAMPLE_REGION:?}" \
  --set-string image.tag=v1.36.1 \
  --set rbac.serviceAccount.create=false \
  --set-string rbac.serviceAccount.name=cluster-autoscaler \
  > cluster-autoscaler-reviewed.yaml
```
No deshabilite a la ligera las protecciones del almacenamiento local ni permita que políticas ASG de seguimiento de objetivos/predictivas compitan con Cluster Autoscaler por la misma capacidad deseada.

**Alternativa con Karpenter:** instale y autorice por separado un controlador compatible. Reemplace el ID de AMI, el rol de nodo y los valores de etiqueta de detección por recursos revisados de este clúster; la AMI debe coincidir con AL2023, la versión de Kubernetes y la arquitectura. Fije un ID de AMI o un alias versionado que haya probado en lugar de seleccionar `al2023@latest` silenciosamente. Los límites y el plazo de consolidación siguientes son ejemplos; no son un dimensionamiento medido ni una garantía de velocidad de aprovisionamiento.

```yaml
# Karpenter NodePool (karpenter.sh/v1)
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: default
spec:
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot", "on-demand"]
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default-class
  limits:
    cpu: 1000
    memory: 1000Gi
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
---
# Karpenter EC2NodeClass (karpenter.k8s.aws/v1)
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: default-class
spec:
  amiFamily: AL2023
  amiSelectorTerms:
    - id: ami-REPLACE_WITH_VERIFIED_AL2023_AMI
  role: KarpenterNodeRole-my-cluster
  subnetSelectorTerms:
    - tags:
        karpenter.sh/discovery: my-cluster
  securityGroupSelectorTerms:
    - tags:
        karpenter.sh/discovery: my-cluster
```
**HPA:** este ejemplo requiere un Deployment existente `my-app` en `autoscaling-lab`, Metrics Server y solicitudes de CPU:

```yaml
# Horizontal Pod Autoscaler
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: my-app-hpa
  namespace: autoscaling-lab
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```
**VPA:** primero instale el CRD/controladores de VPA. Comience en modo de solo recomendación e inspeccione las recomendaciones antes de elegir explícitamente un modo de actualización compatible:

```yaml
# Vertical Pod Autoscaler
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: my-app-vpa
  namespace: autoscaling-lab
spec:
  targetRef:
    apiVersion: "apps/v1"
    kind: Deployment
    name: my-app
  updatePolicy:
    updateMode: "Off"
  resourcePolicy:
    containerPolicies:
    - containerName: '*'
      minAllowed:
        cpu: 100m
        memory: 50Mi
      maxAllowed:
        cpu: 1
        memory: 500Mi
      controlledResources: ["cpu", "memory"]
```
`Off` no cambia los recursos de los Pods. Aplicar recomendaciones puede requerir recreación o redimensionamiento in situ compatible, según las versiones y la configuración de VPA/Kubernetes; no prometa que todos los modos reinician los Pods. Cambiar las solicitudes de CPU mientras un HPA basado en utilización de CPU controla la misma carga genera realimentación a través del denominador de utilización. El ejemplo de solo recomendación evita ese conflicto hasta que se revise un diseño coordinado.

</details>

## Ejercicios prácticos

### Ejercicio 1: Implementar políticas de red en un clúster EKS

**Escenario:** permitir frontend → backend y backend → base de datos, y denegar frontend → base de datos. Mantenga el objetivo didáctico original de Calico usando AWS VPC CNI para asignar IP.

**Alcance:** un clúster EKS Linux IPv4 existente y desechable, sin políticas globales/de nivel en conflicto, CoreDNS estándar y una instalación de Calico revisada por un administrador. Es un ejercicio de conectividad, no una receta de microservicio/base de datos para producción. La instalación en la nube y las pruebas de tráfico no se ejecutaron durante esta auditoría.


<details>
<summary>Mostrar solución</summary>

**1. Prepare el motor de políticas.** Siga la ruta oficial de Calico EKS para **redes de Amazon VPC**. Deshabilite NetworkPolicy nativa de AWS VPC CNI mediante su propietario de configuración; entra en conflicto con la aplicación de Calico. Conserve la red de `aws-node`. Habilite su ajuste `ANNOTATE_POD_IP=true` y conceda permiso de parche de Pods a su ServiceAccount. Este ejemplo de RBAC dedicado añade ese permiso sin anexar YAML mal formado al ClusterRole del complemento:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: calico-vpc-cni-pod-annotation
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["patch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: calico-vpc-cni-pod-annotation
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: calico-vpc-cni-pod-annotation
subjects:
- kind: ServiceAccount
  name: aws-node
  namespace: kube-system
```
Guarde y revise RBAC, y luego aplíquelo únicamente a la ServiceAccount `aws-node` prevista; configure la variable de entorno mediante el complemento administrado o el propietario del manifiesto autoadministrado. No continúe hasta que el rollout y la anotación estén en buen estado. Si Calico ya está instalado, revíselo y reutilícelo en vez de ejecutar los comandos de instalación nueva siguientes.

```bash
# Download pinned manifests for inspection; do not overwrite an existing installation.
curl --fail --location --output calico-crds.yaml \
  https://raw.githubusercontent.com/projectcalico/calico/v3.32.2/manifests/v1_crd_projectcalico_org.yaml
curl --fail --location --output tigera-operator.yaml \
  https://raw.githubusercontent.com/projectcalico/calico/v3.32.2/manifests/tigera-operator.yaml
# After review, on the intended new lab installation:
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" create -f calico-crds.yaml
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" create -f tigera-operator.yaml
```
Cuando se hayan establecido los CRD del operador, cree los recursos `Installation` y `APIServer` revisados siguientes. La instalación del operador por sí sola no configura las redes de AWS VPC. Se necesita el servidor de API para los ejemplos de políticas `projectcalico.org/v3`:

```yaml
apiVersion: operator.tigera.io/v1
kind: Installation
metadata:
  name: default
spec:
  kubernetesProvider: EKS
  cni:
    type: AmazonVPC
  calicoNetwork:
    bgp: Disabled
---
apiVersion: operator.tigera.io/v1
kind: APIServer
metadata:
  name: default
spec: {}
```

```bash
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" get tigerastatus
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" get apiservice v3.projectcalico.org
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n calico-system get pods
```
Espere a que los componentes de Calico y la API agregada estén disponibles; después compruebe la aplicación real de las políticas. Que el nodo esté `Ready` no basta. La interfaz opcional Goldmane/Whisker no se necesita para este ejercicio.

**2. Cree un espacio de nombres propio y una credencial de base de datos temporal.** Use una única sesión de Bash para los fragmentos restantes. El nombre y el UID del espacio de nombres quedan registrados para impedir que la limpieza apunte intencionalmente a otro espacio de nombres:

```bash
set -euo pipefail
umask 077
: "${EXAMPLE_KUBECONFIG:?Use the reviewed lab cluster kubeconfig}"
NETWORK_LAB_DIR=$(mktemp -d /tmp/eks-calico-lab.XXXXXX)
NETWORK_NAMESPACE="calico-quiz-$(date +%s)-$$"
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" create namespace "$NETWORK_NAMESPACE"
NETWORK_NAMESPACE_UID=$(kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" \
  get namespace "$NETWORK_NAMESPACE" -o jsonpath='{.metadata.uid}')
: "${NETWORK_NAMESPACE_UID:?}"
jq -n --arg name "$NETWORK_NAMESPACE" --arg uid "$NETWORK_NAMESPACE_UID" \
  '{namespace:$name,namespaceUID:$uid}' > "$NETWORK_LAB_DIR/ownership.json"
openssl rand -hex 32 > "$NETWORK_LAB_DIR/db-password"
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n "$NETWORK_NAMESPACE" \
  create secret generic database-auth \
  --from-file=password="$NETWORK_LAB_DIR/db-password"
```
**3. Despliegue los tres niveles.** Los servidores HTTP de Python representan frontend/backend para que el cliente TCP de diagnóstico esté disponible en ambos contenedores. La imagen PostgreSQL 17 usa `POSTGRES_PASSWORD_FILE` y un Secret local al espacio de nombres; no ejecuta ninguna operación en una base de datos externa. El `emptyDir` de la base de datos **se pierde al reemplazar el Pod**. No almacene aquí datos valiosos. Se conserva el comportamiento de inicialización de la imagen DB; este no es un manifiesto de base de datos de producción con perfil Restricted. Las etiquetas principales de versión de la imagen son mutables: registre los digests resueltos para poder repetir la ejecución.

```bash
# The HTTP layers are diagnostic stand-ins, not business applications.
for tier in frontend backend; do
  kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n "$NETWORK_NAMESPACE" create -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: $tier
spec:
  replicas: 1
  selector:
    matchLabels: {app: $tier}
  template:
    metadata:
      labels: {app: $tier}
    spec:
      automountServiceAccountToken: false
      nodeSelector: {kubernetes.io/os: linux}
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        seccompProfile: {type: RuntimeDefault}
      containers:
      - name: diagnostic
        image: python:3.13-alpine
        command: [python, -m, http.server, "8080", --directory, /tmp]
        ports:
        - containerPort: 8080
        readinessProbe:
          tcpSocket: {port: 8080}
        resources:
          requests: {cpu: 50m, memory: 64Mi}
          limits: {cpu: 200m, memory: 128Mi}
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities: {drop: [ALL]}
---
apiVersion: v1
kind: Service
metadata:
  name: $tier
spec:
  selector: {app: $tier}
  ports:
  - {port: 8080, targetPort: 8080, protocol: TCP}
EOF
done

kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n "$NETWORK_NAMESPACE" create -f - <<'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: database
spec:
  replicas: 1
  selector:
    matchLabels: {app: database}
  template:
    metadata:
      labels: {app: database}
    spec:
      automountServiceAccountToken: false
      nodeSelector: {kubernetes.io/os: linux}
      containers:
      - name: database
        image: postgres:17-alpine
        env:
        - name: POSTGRES_PASSWORD_FILE
          value: /run/secrets/postgres/password
        ports:
        - containerPort: 5432
        readinessProbe:
          exec:
            command: [pg_isready, -U, postgres]
          initialDelaySeconds: 5
        resources:
          requests: {cpu: 100m, memory: 128Mi}
          limits: {cpu: 500m, memory: 256Mi}
        volumeMounts:
        - {name: data, mountPath: /var/lib/postgresql/data}
        - {name: auth, mountPath: /run/secrets/postgres, readOnly: true}
      volumes:
      - name: data
        emptyDir: {}
      - name: auth
        secret: {secretName: database-auth}
---
apiVersion: v1
kind: Service
metadata:
  name: database
spec:
  selector: {app: database}
  ports:
  - {port: 5432, targetPort: 5432, protocol: TCP}
EOF

for tier in frontend backend database; do
  kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n "$NETWORK_NAMESPACE" \
    rollout status "deployment/$tier" --timeout=180s
done
```
**4. Establezca la conectividad de referencia.** Las tres rutas TCP y DNS deben funcionar antes de aplicar la política. Un éxito en el puerto 5432 solo demuestra una conexión TCP, no la autenticación SQL ni el funcionamiento de la aplicación.

```bash
# Distinguish DNS failure from TCP denial. Status 42 means a TCP failure.
check_tcp() {
  kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n "$NETWORK_NAMESPACE" \
    exec "deployment/$1" -c diagnostic -- python -c '
import socket, sys
host, port = sys.argv[1], int(sys.argv[2])
try:
    address = socket.gethostbyname(host)
except OSError as error:
    print("DNS failure:", error, file=sys.stderr)
    sys.exit(43)
try:
    connection = socket.create_connection((address, port), timeout=3)
    connection.close()
except OSError as error:
    print("TCP connection failed:", error, file=sys.stderr)
    sys.exit(42)
print("TCP connection succeeded")
' "$2" "$3"
}

# Baseline: all three must succeed BEFORE the policy is applied.
check_tcp frontend backend 8080
check_tcp backend database 5432
check_tcp frontend database 5432
```
**5. Aplique y pruebe la política.** Los Pods seleccionados quedan aislados en ambas direcciones; el tráfico no coincidente se deniega. Las reglas explícitas permiten las dos rutas de aplicación y DNS por UDP/TCP. Se necesitan selectores de espacio de nombres para llegar a CoreDNS, que está fuera del espacio de nombres del laboratorio. Antes de probar, adapte la regla DNS si usa NodeLocal DNSCache u otras etiquetas.

```bash
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n "$NETWORK_NAMESPACE" create -f - <<'EOF'
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: tier-boundaries
spec:
  selector: all()
  types: [Ingress, Egress]
  ingress:
  - action: Allow
    protocol: TCP
    source:
      selector: app == 'frontend'
    destination:
      selector: app == 'backend'
      ports: [8080]
  - action: Allow
    protocol: TCP
    source:
      selector: app == 'backend'
    destination:
      selector: app == 'database'
      ports: [5432]
  egress:
  - action: Allow
    protocol: UDP
    destination:
      namespaceSelector: kubernetes.io/metadata.name == 'kube-system'
      selector: k8s-app == 'kube-dns'
      ports: [53]
  - action: Allow
    protocol: TCP
    destination:
      namespaceSelector: kubernetes.io/metadata.name == 'kube-system'
      selector: k8s-app == 'kube-dns'
      ports: [53]
  - action: Allow
    protocol: TCP
    source:
      selector: app == 'frontend'
    destination:
      selector: app == 'backend'
      ports: [8080]
  - action: Allow
    protocol: TCP
    source:
      selector: app == 'backend'
    destination:
      selector: app == 'database'
      ports: [5432]
EOF

# Allow policy propagation, then verify positive controls and the denied path.
POLICY_VERIFIED=false
for attempt in $(seq 1 30); do
  check_tcp frontend backend 8080
  check_tcp backend database 5432
  if check_tcp frontend database 5432; then
    sleep 2
  else
    result=$?
    if [ "$result" -ne 42 ]; then
      printf '%s\n' 'DNS/exec failure is not proof of policy denial.' >&2
      exit 1
    fi
    # Database availability must still hold after the negative observation.
    check_tcp backend database 5432
    POLICY_VERIFIED=true
    break
  fi
done
[ "$POLICY_VERIFIED" = true ] || {
  printf '%s\n' 'Expected denial was not observed; inspect policy enforcement.' >&2
  exit 1
}
```
La propagación de políticas es asíncrona. Un timeout, un fallo de DNS, la ausencia del binario de diagnóstico o una base de datos no disponible, por sí solos, no demuestran que el aislamiento funcione. El procedimiento parte de una conectividad de referencia funcional y usa controles positivos; si los resultados difieren, investigue otras políticas o rutas.

**6. Limpieza.** Después de confirmar el UID, elimine solo el espacio de nombres propio. Esto quita las cargas de prueba, la política, el Secret y los datos efímeros, pero no la instalación de Calico de todo el clúster. Después del ejercicio, elimine el archivo de contraseña local. Mantenga la configuración compartida de CNI/RBAC, salvo que una reversión independiente revisada por un administrador sea su propietaria.

```bash
CURRENT_NETWORK_UID=$(kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" \
  get namespace "${NETWORK_NAMESPACE:?}" --ignore-not-found \
  -o jsonpath='{.metadata.uid}') || exit 1
if [ -z "$CURRENT_NETWORK_UID" ]; then
  printf '%s\n' 'Lab namespace is already absent.'
elif [ "$CURRENT_NETWORK_UID" = "${NETWORK_NAMESPACE_UID:?Recorded UID required}" ]; then
  kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" \
    delete namespace "$NETWORK_NAMESPACE" --wait=true || exit 1
else
  printf '%s\n' 'Namespace UID changed; no deletion attempted.' >&2
  exit 1
fi
```

</details>

### Ejercicio 2: Configurar IRSA y acceso a S3 en un clúster EKS

**Escenario:** conceda a una carga de trabajo acceso de solo lectura a un prefijo `training/` aprobado de un bucket S3 existente, mediante IRSA en vez del rol de nodo. Verifique la identidad del rol asumido y compárela con un Pod deliberadamente sin credenciales.

**Requisitos previos:** Bash, jq, AWS CLI, eksctl y kubectl; un clúster EKS existente y autorizado; acceso de administrador a un espacio de nombres nuevo y a un rol IAM; un objeto S3 existente, aprobado y no sensible. Este ejemplo para la partición comercial presupone que el objeto no tiene requisitos adicionales de KMS del cliente. Las políticas del bucket/KMS, SCP, DNS, STS y las rutas de red S3 pueden añadir requisitos. No se crea, modifica ni elimina ningún objeto de S3.


<details>
<summary>Mostrar solución</summary>

**1. Delimite el laboratorio y verifique OIDC.** Configure `EXAMPLE_CLUSTER`, `EXAMPLE_REGION`, `S3_BUCKET` y `S3_TEST_KEY` (dentro de `training/`). El proveedor OIDC es infraestructura compartida del clúster; no lo elimine durante la limpieza. Deténgase si falla la creación del espacio de nombres o la verificación del proveedor.

```bash
set -euo pipefail
umask 077
# Commercial AWS partition example; use an existing approved S3 training prefix.
: "${EXAMPLE_CLUSTER:?}"
: "${EXAMPLE_REGION:?}"
: "${S3_BUCKET:?Existing bucket containing the approved training object}"
: "${S3_TEST_KEY:?Existing non-sensitive object key under training/}"
case "$S3_TEST_KEY" in training/*) ;; *) printf '%s\n' 'Use a training/ key.' >&2; exit 1 ;; esac
IRSA_LAB_DIR=$(mktemp -d /tmp/eks-irsa-lab.XXXXXX)
: "${IRSA_LAB_DIR:?}"
IRSA_LAB_ID="irsa-quiz-$(date +%s)-$$"
IRSA_NAMESPACE="$IRSA_LAB_ID"
IRSA_ROLE_NAME="$IRSA_LAB_ID"
IRSA_SERVICE_ACCOUNT=s3-reader
IRSA_KUBECONFIG="$IRSA_LAB_DIR/kubeconfig"

aws sts get-caller-identity --output json > "$IRSA_LAB_DIR/caller.json" || exit 1
IRSA_ACCOUNT_ID=$(jq -er '.Account' "$IRSA_LAB_DIR/caller.json") || exit 1
jq -e '.Arn | startswith("arn:aws:")' "$IRSA_LAB_DIR/caller.json" >/dev/null || exit 1
aws eks describe-cluster --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --query cluster --output json > "$IRSA_LAB_DIR/cluster.json" || exit 1
IRSA_ISSUER=$(jq -er '.identity.oidc.issuer' "$IRSA_LAB_DIR/cluster.json") || exit 1
case "$IRSA_ISSUER" in https://*) ;; *) printf '%s\n' 'Invalid OIDC issuer.' >&2; exit 1 ;; esac
IRSA_ISSUER_HOST="${IRSA_ISSUER#https://}"
IRSA_PROVIDER_ARN="arn:aws:iam::$IRSA_ACCOUNT_ID:oidc-provider/$IRSA_ISSUER_HOST"

aws eks update-kubeconfig --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --kubeconfig "$IRSA_KUBECONFIG" --alias "$EXAMPLE_CLUSTER" || exit 1
kubectl --kubeconfig "$IRSA_KUBECONFIG" create namespace "$IRSA_NAMESPACE" || exit 1
IRSA_NAMESPACE_UID=$(kubectl --kubeconfig "$IRSA_KUBECONFIG" \
  get namespace "$IRSA_NAMESPACE" -o jsonpath='{.metadata.uid}') || exit 1
: "${IRSA_NAMESPACE_UID:?}"
jq -n --arg namespace "$IRSA_NAMESPACE" --arg uid "$IRSA_NAMESPACE_UID" \
  '{namespace:$namespace,namespaceUID:$uid}' > "$IRSA_LAB_DIR/ownership.json" || exit 1

# The cluster's provider is shared infrastructure; eksctl checks/associates it.
eksctl utils associate-iam-oidc-provider --cluster "$EXAMPLE_CLUSTER" \
  --region "$EXAMPLE_REGION" --approve || exit 1
aws iam get-open-id-connect-provider --open-id-connect-provider-arn "$IRSA_PROVIDER_ARN" \
  --output json > "$IRSA_LAB_DIR/provider.json" || exit 1
jq -e '.ClientIDList | index("sts.amazonaws.com") != null' \
  "$IRSA_LAB_DIR/provider.json" >/dev/null || exit 1
```
**2. Cree un rol único y de alcance limitado.** La relación de confianza requiere tanto `aud=sts.amazonaws.com` como el `sub` exacto del espacio de nombres/ServiceAccount. Si falla la creación del rol, no adjunte la política; registre el RoleId inmutable para la limpieza.

```bash
jq -n --arg provider "${IRSA_PROVIDER_ARN:?}" --arg issuer "${IRSA_ISSUER_HOST:?}" \
  --arg subject "system:serviceaccount:${IRSA_NAMESPACE:?}:${IRSA_SERVICE_ACCOUNT:?}" \
  '{
    Version:"2012-10-17",
    Statement:[{
      Effect:"Allow",
      Principal:{Federated:$provider},
      Action:"sts:AssumeRoleWithWebIdentity",
      Condition:{StringEquals:{
        ($issuer+":aud"):"sts.amazonaws.com",
        ($issuer+":sub"):$subject
      }}
    }]
  }' > "${IRSA_LAB_DIR:?}/trust.json" || exit 1

jq -n --arg bucket "${S3_BUCKET:?}" \
  '{
    Version:"2012-10-17",
    Statement:[
      {
        Effect:"Allow",Action:"s3:ListBucket",Resource:("arn:aws:s3:::"+$bucket),
        Condition:{StringLike:{"s3:prefix":["training/","training/*"]}}
      },
      {
        Effect:"Allow",Action:"s3:GetObject",
        Resource:("arn:aws:s3:::"+$bucket+"/training/*")
      }
    ]
  }' > "$IRSA_LAB_DIR/s3-policy.json" || exit 1

# Stop on creation failure; never attach this policy to a pre-existing role.
aws iam create-role --role-name "${IRSA_ROLE_NAME:?}" \
  --assume-role-policy-document "file://$IRSA_LAB_DIR/trust.json" \
  --tags "Key=TrainingLab,Value=${IRSA_LAB_ID:?}" \
  --query Role --output json > "$IRSA_LAB_DIR/created-role.json" || exit 1
IRSA_ROLE_ARN=$(jq -er '.Arn' "$IRSA_LAB_DIR/created-role.json") || exit 1
IRSA_ROLE_ID=$(jq -er '.RoleId' "$IRSA_LAB_DIR/created-role.json") || exit 1
jq -n --arg namespace "$IRSA_NAMESPACE" --arg uid "${IRSA_NAMESPACE_UID:?}" \
  --arg roleName "$IRSA_ROLE_NAME" --arg roleArn "$IRSA_ROLE_ARN" --arg roleId "$IRSA_ROLE_ID" \
  '{namespace:$namespace,namespaceUID:$uid,roleName:$roleName,roleARN:$roleArn,roleID:$roleId}' \
  > "$IRSA_LAB_DIR/ownership.json" || exit 1
aws iam put-role-policy --role-name "$IRSA_ROLE_NAME" \
  --policy-name ScopedTrainingS3Read \
  --policy-document "file://$IRSA_LAB_DIR/s3-policy.json" || exit 1
```
**3. Despliegue y verifique.** Si una prueba falla, espere a que se propaguen los cambios de IAM antes de volver a intentarla. Los tres contenedores comprueban la identidad, el recuento de objetos del prefijo y la longitud del objeto, sin registrar el contenido del objeto ni las credenciales. La identidad debe coincidir con el rol recién creado; de lo contrario, un éxito de S3 podría proceder de un rol de nodo más amplio.

```bash
# JSON construction preserves literal object keys and prevents YAML interpolation errors.
jq -n --arg ns "${IRSA_NAMESPACE:?}" --arg sa "${IRSA_SERVICE_ACCOUNT:?}" \
  --arg role "${IRSA_ROLE_ARN:?}" --arg region "${EXAMPLE_REGION:?}" \
  --arg bucket "${S3_BUCKET:?}" --arg key "${S3_TEST_KEY:?}" '
  {
    apiVersion:"v1",kind:"List",items:[
      {
        apiVersion:"v1",kind:"ServiceAccount",
        metadata:{name:$sa,namespace:$ns,annotations:{
          "eks.amazonaws.com/role-arn":$role,
          "eks.amazonaws.com/sts-regional-endpoints":"true"
        }}
      },
      {
        apiVersion:"v1",kind:"Pod",metadata:{name:"irsa-check",namespace:$ns},
        spec:{
          serviceAccountName:$sa,nodeSelector:{"kubernetes.io/os":"linux"},restartPolicy:"Never",
          containers:[
            {name:"identity",args:["--region",$region,"sts","get-caller-identity"]},
            {name:"list-prefix",args:["--region",$region,"s3api","list-objects-v2","--bucket",$bucket,
              "--prefix","training/","--max-keys","1","--query","KeyCount","--output","json"]},
            {name:"object-metadata",args:["--region",$region,"s3api","head-object","--bucket",$bucket,
              "--key",$key,"--query","ContentLength","--output","json"]}
          ] | map(.+{
            image:"public.ecr.aws/aws-cli/aws-cli:2.36.43",command:["aws"],
            resources:{requests:{cpu:"100m",memory:"128Mi"},limits:{memory:"256Mi"}}
          })
        }
      }
    ]
  }' > "${IRSA_LAB_DIR:?}/workload.json" || exit 1
kubectl --kubeconfig "${IRSA_KUBECONFIG:?}" create -f "$IRSA_LAB_DIR/workload.json" || exit 1
kubectl --kubeconfig "$IRSA_KUBECONFIG" -n "$IRSA_NAMESPACE" \
  wait --for=jsonpath='{.status.phase}'=Succeeded pod/irsa-check --timeout=180s || exit 1
kubectl --kubeconfig "$IRSA_KUBECONFIG" -n "$IRSA_NAMESPACE" \
  logs irsa-check -c identity > "$IRSA_LAB_DIR/pod-identity.json" || exit 1
jq -e --arg account "${IRSA_ACCOUNT_ID:?}" --arg role "${IRSA_ROLE_NAME:?}" \
  '.Account == $account and (.Arn | startswith("arn:aws:sts::"+$account+":assumed-role/"+$role+"/"))' \
  "$IRSA_LAB_DIR/pod-identity.json" >/dev/null || exit 1
kubectl --kubeconfig "$IRSA_KUBECONFIG" -n "$IRSA_NAMESPACE" logs irsa-check -c list-prefix
kubectl --kubeconfig "$IRSA_KUBECONFIG" -n "$IRSA_NAMESPACE" logs irsa-check -c object-metadata
```
**4. Comparación negativa controlada.** La ServiceAccount predeterminada del nuevo espacio de nombres no debe tener anotación IRSA ni asociación de EKS Pod Identity, y no se deben inyectar otras credenciales. Deshabilite la vía de respaldo de IMDS en este cliente de prueba y exija el error concreto de credenciales ausentes. Un error aleatorio de red o autorización no es un resultado negativo válido.

```bash
# Controlled comparison: no IRSA, no Pod Identity association, no IMDS fallback.
jq -n --arg ns "${IRSA_NAMESPACE:?}" --arg region "${EXAMPLE_REGION:?}" '
{
  apiVersion:"v1",kind:"Pod",
  metadata:{name:"no-role-check",namespace:$ns},
  spec:{
    automountServiceAccountToken:false,
    serviceAccountName:"default",
    nodeSelector:{"kubernetes.io/os":"linux"},
    restartPolicy:"Never",
    containers:[{
      name:"identity",image:"public.ecr.aws/aws-cli/aws-cli:2.36.43",
      command:["aws"],args:["--region",$region,"sts","get-caller-identity"],
      env:[{name:"AWS_EC2_METADATA_DISABLED",value:"true"}],
      resources:{requests:{cpu:"100m",memory:"128Mi"},limits:{memory:"256Mi"}}
    }]
  }
}' > "${IRSA_LAB_DIR:?}/negative-pod.json" || exit 1
kubectl --kubeconfig "$IRSA_KUBECONFIG" create -f "$IRSA_LAB_DIR/negative-pod.json" || exit 1
kubectl --kubeconfig "$IRSA_KUBECONFIG" -n "$IRSA_NAMESPACE" \
  wait --for=jsonpath='{.status.phase}'=Failed pod/no-role-check --timeout=180s || exit 1
kubectl --kubeconfig "$IRSA_KUBECONFIG" -n "$IRSA_NAMESPACE" \
  get pod no-role-check -o json > "$IRSA_LAB_DIR/negative-status.json" || exit 1
jq -e '.status.containerStatuses[] | select(.name=="identity") |
  .state.terminated.exitCode == 255' "$IRSA_LAB_DIR/negative-status.json" >/dev/null || exit 1
kubectl --kubeconfig "$IRSA_KUBECONFIG" -n "$IRSA_NAMESPACE" \
  logs no-role-check -c identity > "$IRSA_LAB_DIR/negative-log.txt" || exit 1
grep -F 'Unable to locate credentials' "$IRSA_LAB_DIR/negative-log.txt" >/dev/null || {
  printf '%s\n' 'Unexpected failure: inspect the saved log; do not claim isolation.' >&2
  exit 1
}
```
Esta comparación se refiere a proveedores de credenciales; no demuestra que cualquier Pod carezca de acceso a IMDS ni que los contenedores sean límites de seguridad. Restrinja por separado las credenciales de nodo. IRSA usa un token proyectado de identidad web y credenciales temporales de STS; los SDK compatibles las renuevan. No vuelque todas las variables de entorno `AWS_*` ni los archivos de tokens.

**5. Limpie únicamente los recursos propios.** Conserve el UID registrado del espacio de nombres y el RoleId de IAM. La limpieza con protecciones elimina el espacio de nombres del laboratorio, la política insertada en el rol y el rol único; conserva el bucket/objeto S3, el proveedor OIDC compartido y el clúster. Si la preparación solo se completó parcialmente, inspeccione `ownership.json` y limpie únicamente los recursos que realmente estén registrados.

```bash
# Recover the recorded values from ownership.json if this is a later shell.
IRSA_CLEANUP_NAMESPACE_OK=false
if CURRENT_IRSA_UID=$(kubectl --kubeconfig "${IRSA_KUBECONFIG:?}" \
  get namespace "${IRSA_NAMESPACE:?}" --ignore-not-found -o jsonpath='{.metadata.uid}'); then
  if [ -z "$CURRENT_IRSA_UID" ]; then
    IRSA_CLEANUP_NAMESPACE_OK=true
  elif [ "$CURRENT_IRSA_UID" = "${IRSA_NAMESPACE_UID:?Recorded UID required}" ]; then
    if kubectl --kubeconfig "$IRSA_KUBECONFIG" delete namespace "$IRSA_NAMESPACE" --wait=true; then
      IRSA_CLEANUP_NAMESPACE_OK=true
    else
      exit 1
    fi
  else
    printf '%s\n' 'Namespace UID mismatch; stop and inspect.' >&2
    exit 1
  fi
else
  printf '%s\n' 'Namespace lookup failed; stop and inspect.' >&2
  exit 1
fi

if [ "$IRSA_CLEANUP_NAMESPACE_OK" = true ]; then
  CURRENT_IRSA_ROLE_JSON=$(aws iam get-role --role-name "${IRSA_ROLE_NAME:?}" \
    --query Role --output json) || exit 1
  CURRENT_IRSA_ROLE_ID=$(printf '%s' "$CURRENT_IRSA_ROLE_JSON" | jq -er '.RoleId') || exit 1
  if [ "$CURRENT_IRSA_ROLE_ID" = "${IRSA_ROLE_ID:?Recorded IAM RoleId required}" ]; then
    IRSA_INLINE_POLICIES=$(aws iam list-role-policies --role-name "$IRSA_ROLE_NAME" \
      --query PolicyNames --output json) || exit 1
    printf '%s' "$IRSA_INLINE_POLICIES" |
      jq -e 'all(.[]; . == "ScopedTrainingS3Read")' >/dev/null || exit 1
    if printf '%s' "$IRSA_INLINE_POLICIES" | jq -e 'index("ScopedTrainingS3Read") != null' >/dev/null; then
      aws iam delete-role-policy --role-name "$IRSA_ROLE_NAME" \
        --policy-name ScopedTrainingS3Read || exit 1
    fi
    aws iam delete-role --role-name "$IRSA_ROLE_NAME"
  else
    printf '%s\n' 'IAM RoleId mismatch; no IAM deletion attempted.' >&2
    exit 1
  fi
fi
```

</details>

## Temas avanzados

Las siguientes preguntas tratan temas avanzados relacionados con la creación de clústeres de Amazon EKS. Esta sección comprueba la comprensión de conceptos avanzados y prácticas recomendadas para crear clústeres de EKS.

1. ¿Qué afirmación sobre la delegación de prefijos IPv4 **no** está garantizada?
   * A) Un prefijo ocupa una ranura de direcciones de ENI
   * B) Puede caber más capacidad de IP en un nodo
   * C) Todas las aplicaciones estarán listas más rápido
   * D) Se requieren bloques contiguos de subred

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Todas las aplicaciones estarán listas más rápido**

La delegación de prefijos puede reducir la latencia de asignación de direcciones: asociar otro prefijo a una ENI existente evita parte del trabajo de crear y adjuntar ENI. AWS documenta este beneficio, por lo que era incorrecta la explicación original de que la delegación de prefijos no puede reducir el tiempo de inicio y necesariamente añade sobrecarga de enrutamiento.

La disponibilidad integral de un Pod sigue dependiendo de la programación, el lanzamiento del nodo, la descarga de imágenes, la asociación de volúmenes, la inicialización, las sondas y el inicio de la aplicación. Aquí no se aportó una prueba comparativa antes/después y esta auditoría no ejecutó ninguna. No deduzca una mejora fija de latencia ni invente una causa para una ralentización.

Cada `/28` IPv4 ocupa una ranura de direcciones secundarias y 16 direcciones de un bloque de subred contiguo. Aumenta la capacidad de IP por nodo, sujeto a `maxPods`, recursos de cómputo y espacio de subred. No amplía el CIDR ni garantiza que se asignen menos direcciones. Los ajustes de reserva de IP/prefijos intercambian el consumo de direcciones libres por la disponibilidad de asignación.

Use los requisitos previos y la migración a un grupo de nodos nuevo de la pregunta básica 5: inspeccione la fragmentación, configure un CNI compatible, valide la capacidad calculada del nodo y migre con capacidad de reserva y drenaje que tenga en cuenta los PDB. Reiniciar indiscriminadamente los Pods existentes no es un plan de transición completo.

</details>

2. ¿Qué práctica es incorrecta al usar grupos de nodos administrados con varios tipos de instancia y Cluster Autoscaler?
   * A) Usar tipos con formas comparables de CPU/memoria/GPU
   * B) Verificar la compatibilidad de imagen y AZ
   * C) Separar los grupos Spot y On-Demand
   * D) Mezclar formas arbitrarias porque el autoscaler las simula todas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Mezclar formas arbitrarias porque el autoscaler las simula todas**

La diversidad puede ampliar las opciones de capacidad, especialmente para Spot, pero debe respetar el modelo de programación del autoscaler. Cluster Autoscaler simula un grupo mixto usando su primer tipo de instancia; los candidatos deberían tener la misma forma de CPU, memoria y GPU. Las alternativas más pequeñas pueden dejar Pods pendientes y las más grandes desperdiciar capacidad. Los nombres parecidos no garantizan una forma equivalente: por ejemplo, `c5n.large` tiene una memoria distinta de `c5.large`.

Un grupo de nodos administrado tiene un solo tipo de capacidad. Use **grupos separados** para la base On-Demand y la expansión Spot; enumerar varios `instanceTypes` no mezcla opciones de compra en un mismo grupo administrado. EKS elige la estrategia de asignación Spot administrada; `spotAllocationStrategy` no es un campo compatible de `managedNodeGroups` de eksctl.

Este ejemplo conserva tipos comparables de la familia `m5`. Es una configuración de grupo de nodos para un clúster existente y revisado, con nombres de grupo que no estén en uso; no demuestra precio/rendimiento ni capacidad garantizada. Compruebe la oferta por AZ y la compatibilidad de imágenes/controladores/almacenamiento:

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: on-demand-base
  amiFamily: AmazonLinux2023
  instanceType: m5.large
  privateNetworking: true
  spot: false
  desiredCapacity: 2
  minSize: 2
  maxSize: 5
- name: spot-scaling
  amiFamily: AmazonLinux2023
  instanceTypes: [m5.large, m5a.large, m5d.large, m5ad.large, m5n.large]
  privateNetworking: true
  spot: true
  desiredCapacity: 0
  minSize: 0
  maxSize: 20
```
Separe las formas de cargas de trabajo distintas en vez de combinar instancias optimizadas para memoria, cómputo y uso general en un grupo con escalado automático:

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: compute-optimized
  amiFamily: AmazonLinux2023
  instanceTypes: [c5.2xlarge, c5a.2xlarge]
  privateNetworking: true
  minSize: 2
  maxSize: 10
  labels: {workload-type: compute}
  taints:
  - {key: workload-type, value: compute, effect: NoSchedule}
- name: memory-optimized
  amiFamily: AmazonLinux2023
  instanceTypes: [r5.2xlarge, r5a.2xlarge]
  privateNetworking: true
  minSize: 2
  maxSize: 10
  labels: {workload-type: memory}
  taints:
  - {key: workload-type, value: memory, effect: NoSchedule}
```
La carga de trabajo necesita una tolerancia coincidente **y** un selector/afinidad si debe usar un grupo dedicado. Las etiquetas por sí solas no la programan y los taints no son un límite de seguridad entre inquilinos. Tenga en cuenta la detección al escalar desde cero, la sobrecarga de daemons, la gestión de interrupciones, la persistencia del almacenamiento y las pruebas con todos los tipos candidatos. La diversidad puede aumentar las tareas de supervisión y solución de problemas; ni una operación más sencilla ni un costo menor son automáticos.

</details>

3. ¿Qué estrategia crea un grupo de nodos de reemplazo separado antes de retirar el antiguo?
   * A) Actualizaciones de paquetes del host sin seguimiento
   * B) Migración blue/green
   * C) Eliminar todos los nodos a la vez
   * D) Cambiar únicamente el nombre visible del clúster

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Migración blue/green**

Blue/green crea un grupo de nodos de reemplazo independiente y migra las cargas de trabajo después de validarlo. Puede mantener la opción de reversión mientras se conserven el grupo antiguo y un estado compatible de la aplicación/datos. Dos grupos en un clúster siguen compartiendo el plano de control y otras dependencias; no es aislamiento completo ni garantiza tiempo de inactividad cero.

| Estrategia | Ventaja | Límite importante |
| --- | --- | --- |
| Blue/green | Validar capacidad de reemplazo antes del retiro definitivo | Costo/capacidad adicionales; la reversión depende de conservar nodos y un estado compatible |
| Actualización gradual administrada | EKS coordina el reemplazo gradual de nodos | `DEFAULT` usa nodos adicionales temporales; los PDB o la falta de capacidad pueden bloquear el progreso |
| Canary | Probar primero una carga/grupo pequeño aparte | Debe limitar realmente el alcance de cargas/tráfico; añade trabajo de validación y enrutamiento |
| Modificación manual de paquetes del host | Cambia un host individual | Provoca divergencia de la AMI; use un ciclo de vida revisado de imágenes de reemplazo en vez de una receta SSH/yum sin calificar |

**Ejemplo del grupo de reemplazo:** para un clúster existente y un nombre de grupo sin usar, revise este archivo y ejecute `eksctl create nodegroup -f green-nodegroup.yaml`. Primero confirme la compatibilidad de AL2023/arquitectura, los complementos, el egreso, el espacio de IP, las cuotas y la topología de almacenamiento.

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: green-nodegroup
  amiFamily: AmazonLinux2023
  instanceType: m5.large
  privateNetworking: true
  desiredCapacity: 3
  minSize: 3
  maxSize: 5
  labels:
    audit.example.com/pool: green
```
**Un canary real usa un Deployment separado:** lo siguiente es una carga HTTP mínima de sondeo en un espacio de nombres dedicado `update-lab`, con etiquetas únicas para que no se una por accidente al Service existente. Reemplácela por un canary revisado de su aplicación real antes de afirmar que la aplicación es compatible. Aplicar un parche al selector de nodos del Deployment principal inicia un rollout de **todas** sus réplicas y no es un canary limitado.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app-canary
  namespace: update-lab
spec:
  replicas: 1
  selector:
    matchLabels: {app: my-app-canary}
  template:
    metadata:
      labels: {app: my-app-canary}
    spec:
      automountServiceAccountToken: false
      nodeSelector:
        audit.example.com/pool: green
      containers:
      - name: web
        image: nginx:1.30.6
        ports:
        - containerPort: 80
        readinessProbe:
          httpGet: {path: /, port: 80}
        resources:
          requests: {cpu: 100m, memory: 64Mi}
          limits: {cpu: 500m, memory: 128Mi}
```
Valide durante un periodo de observación revisado la disponibilidad, la API/CNI/DNS, los errores de aplicación, la presión de recursos, los volúmenes persistentes y el tráfico representativo. Mantenga explícito el enrutamiento del tráfico; una etiqueta de nodo no cambia el tráfico. Una vez verificadas la capacidad de reemplazo y la conducta de cargas/datos, drene un nodo antiguo confirmado cada vez:

```bash
# One reviewed node at a time, after validating replacement capacity.
OLD_NODE_JSON=$(kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" \
  get node "${OLD_NODE_NAME:?}" -o json) || exit 1
OLD_NODE_GROUP=$(printf '%s' "$OLD_NODE_JSON" |
  jq -er '.metadata.labels["eks.amazonaws.com/nodegroup"]') || exit 1
if [ "$OLD_NODE_GROUP" != "${OLD_NODEGROUP_NAME:?}" ]; then
  printf '%s\n' 'Node is not in the intended old managed node group.' >&2
  exit 1
fi
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" cordon "$OLD_NODE_NAME" &&
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" drain "$OLD_NODE_NAME" \
  --ignore-daemonsets --timeout=15m
```
Un drenaje bloqueado requiere diagnóstico, no `--force` ni borrado automático de emptyDir. Confirme la migración de todas las cargas y su estado antes de efectuar este borrado final separado:

```bash
# Separate final step, after application/data validation and ownership review.
if [ "${MIGRATION_VERIFIED:?Set yes only after workload and data checks}" = yes ]; then
  eksctl delete nodegroup --cluster "${EXAMPLE_CLUSTER:?}" \
    --region "${EXAMPLE_REGION:?}" --name "${OLD_NODEGROUP_NAME:?}" --approve --wait
fi
```
Como alternativa de actualización gradual administrada, complete la operación `update-nodegroup-config` de la pregunta básica 9 antes de enviar `update-nodegroup-version`, y luego haga seguimiento del ID de actualización que devuelve. Un grupo administrado puede conservar su identidad de recurso mientras se reemplazan sus nodos EC2. Una vez eliminada la capacidad antigua o modificados los datos de forma incompatible, ya no hay «reversión instantánea».

</details>

4. ¿Qué acción puede entrar en conflicto con el control de Cluster Autoscaler sobre un ASG administrado?
   * A) Revisar las etiquetas de detección
   * B) Ajustar la frecuencia de análisis según observaciones
   * C) Usar solicitudes de recursos precisas en los Pods
   * D) Añadir otra política que cambie independientemente la misma capacidad deseada

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Añadir otra política que cambie independientemente la misma capacidad deseada**

Cluster Autoscaler controla la capacidad del grupo de nodos según las solicitudes de programación, no solo el promedio de CPU de EC2. Una política ASG predictiva o de seguimiento de objetivos que cambie la misma capacidad deseada puede competir con ese bucle de control y eludir el proceso de drenaje esperado de Kubernetes. No restablezca directamente la capacidad deseada a dos como «optimización».

**Controles útiles:**

* Ajuste la frecuencia de análisis teniendo en cuenta el tiempo de respuesta y la carga de la API. El valor predeterminado documentado es 10 segundos; 30 segundos es un ejemplo que se debe probar, no un valor óptimo medido. Del mismo modo, los timeouts de aprovisionamiento deben corresponder al inicio real de sus nodos.
* Use etiquetas de detección de ASG revisadas e IAM limitado por etiquetas. Las etiquetas identifican grupos elegibles; no conceden permisos ni definen un algoritmo de escalado.
* Haga coincidir las solicitudes, las etiquetas y los taints con la capacidad real. Puede bastar un tipo de instancia; la diversidad de formas comparables es útil cuando lo justifican la disponibilidad o las necesidades de Spot (pregunta avanzada 2).
* Use las prioridades de forma deliberada. La apropiación de prioridad no garantiza disponibilidad y puede interrumpir cargas de menor prioridad. Asigne la siguiente clase mediante `priorityClassName` solo después de evaluar la admisión y la política de cargas de trabajo:

```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: audit-high-priority
value: 1000000
globalDefault: false
description: Reviewed priority for critical application Pods
```
**Sobreaprovisionamiento:** reserve solicitudes con Pods de baja prioridad que puedan ser desalojados. En este ejemplo, el umbral de Pods prescindibles configurado en Cluster Autoscaler debe ser inferior a `-5` (por ejemplo, `-10`), mientras que los Pods de la aplicación deben tener prioridad más alta. De lo contrario, los Pods de reserva quizá no provoquen la reposición prevista. Use un espacio de nombres dedicado y un nombre de PriorityClass no utilizado:

```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: audit-overprovisioning
value: -5
globalDefault: false
description: Temporary spare capacity for an autoscaling lab
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: overprovisioning
  namespace: autoscaling-lab
spec:
  replicas: 1
  selector:
    matchLabels: {app: overprovisioning}
  template:
    metadata:
      labels: {app: overprovisioning}
    spec:
      priorityClassName: audit-overprovisioning
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        seccompProfile: {type: RuntimeDefault}
      containers:
      - name: reserve
        image: public.ecr.aws/docker/library/busybox:1.38.0
        command: [sleep, '86400']
        resources:
          requests: {cpu: 1000m, memory: 1000Mi}
          limits: {cpu: 1000m, memory: 1000Mi}
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities: {drop: [ALL]}
```
Esto reserva 1 CPU y 1000Mi de capacidad solicitada; no prepara de antemano el estado de la aplicación y genera costos de nodo. No evita descargar imágenes, asociar volúmenes ni inicializar la aplicación. Dimensione según la demanda observada y, después de la prueba, elimine el Deployment de reserva y la PriorityClass que sean de su propiedad.

Use la configuración completa y renderizada de Cluster Autoscaler de la pregunta básica 10 en vez del antiguo Deployment incompleto v1.23. Karpenter es una alternativa para capacidad administrada por separado; su NodePool debe hacer referencia a una EC2NodeClass válida y autorizada. KEDA/HPA escalan las réplicas de las cargas de trabajo, lo que puede crear demanda para cualquiera de los autoscalers de nodos. Valide la interacción de estos bucles en vez de habilitar todos los mecanismos de escalado en los mismos recursos.

</details>

5. ¿Cuál de las siguientes **no** es una práctica general recomendada de seguridad para un grupo de nodos de EKS?
   * A) Exigir IMDSv2 y revisar el acceso a metadatos
   * B) Aplicar el mínimo privilegio de IAM
   * C) Asignar una IP pública a cada nodo
   * D) Revisar las reglas de grupos de seguridad

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Asignar una IP pública a cada nodo**

Asignar una IP pública a cada nodo no es una práctica general recomendada de seguridad. Las subredes privadas reducen la exposición directa a Internet, pero siguen importando las rutas, los grupos de seguridad, IAM, el mantenimiento del software y los controles de las cargas.

**Identidad del nodo y metadatos:** exija IMDSv2 con el campo `disableIMDSv1` compatible con eksctl. Un objeto anidado `metadataOptions` no es un campo de eksctl para grupos de nodos administrados; las opciones EC2 MetadataOptions personalizadas pertenecen a una plantilla de lanzamiento revisada. IMDSv2 mitiga algunas rutas SSRF, pero no impide que todos los Pods alcancen las credenciales del nodo, especialmente los Pods que usan la red del host. Revise el acceso a metadatos por separado de la identidad de carga y las dependencias del host.

**Mínimo privilegio y volumen raíz cifrado:** este ejemplo de grupo de nodos para un clúster existente presupone que el CNI ya tiene sus propios permisos IRSA/Pod Identity. EBS CSI, los recopiladores de registros y las aplicaciones también necesitan sus propios roles revisados; adjuntar sus permisos amplios a todos los nodos contradice el mínimo privilegio.

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: secure-nodes
  amiFamily: AmazonLinux2023
  instanceType: m5.large
  privateNetworking: true
  desiredCapacity: 2
  minSize: 2
  maxSize: 5
  disableIMDSv1: true
  volumeEncrypted: true
  iam:
    attachPolicyARNs:
    - arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy
    - arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPullOnly
```
El cifrado de EBS protege una capa distinta de los datos de la API de Kubernetes. EKS 1.28 y posteriores cifran en reposo todos los datos de la API de Kubernetes con cifrado de sobre predeterminado; una clave KMS administrada por el cliente es opcional y exige concesiones/permisos adicionales y gestionar el ciclo de vida de la clave. No deshabilite ni elimine la clave de un clúster como parte de una limpieza rutinaria.

**Diseño de red:** un endpoint privado de API requiere una ruta de acceso enrutada para el administrador/nodo. Las restricciones de la API pública usan `publicAccessCidrs`, no una regla de entrada del SG del clúster. Revise los requisitos completos de AWS para los SG de clúster/nodo: TCP 443, TCP 10250, TCP/UDP 53 y rutas específicas de la carga, con las direcciones y los grupos de pares correctos. Dos reglas de puertos de entrada no bastan para diseñar toda la red de nodos.

El egreso a Internet de IPv4 privada puede usar NAT; los endpoints de VPC y el IPv6 nativo siguen rutas distintas. El tráfico entrante puede llegar de balanceadores de carga o redes conectadas autorizadas. Una subred privada por sí sola no demuestra aislamiento completo ni cumplimiento normativo.

**Controles de contenedores:** use una carga compatible con ejecución sin root y de solo lectura. Este Pod de diagnóstico, administrado por un controlador, se ejecuta en un espacio de nombres `security-lab` **nuevo y dedicado**, y no necesita red ni escritura en el sistema raíz:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: secure-pod
  namespace: security-lab
spec:
  replicas: 1
  selector:
    matchLabels: &id001
      app: secure-pod
  template:
    metadata:
      labels: *id001
    spec:
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: secure-container
        image: public.ecr.aws/docker/library/busybox:1.38.0
        command:
        - sh
        - -c
        - echo read-only-lab; sleep 3600
        resources:
          requests:
            cpu: 10m
            memory: 16Mi
          limits:
            cpu: 100m
            memory: 32Mi
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
```
En ese espacio de nombres dedicado se puede demostrar una política de denegación aplicada; antes de usarla con una carga real, añada permisos explícitos para DNS y la aplicación:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: security-lab
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
```
**Registro y detección:** los registros de CloudWatch del plano de control tienen cinco tipos configurables:

```bash
# Enable the reviewed set of log types; this example enables all five.
if LOG_UPDATE_ID=$(aws eks update-cluster-config \
  --name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}' \
  --query update.id --output text); then
  aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
    --update-id "$LOG_UPDATE_ID" --query 'update.{status:status,errors:errors}'
fi
```
Espere a que la actualización devuelta termine correctamente y compruebe la entrega y retención reales de registros. Esto no recopila los registros de aplicación de todos los contenedores. La protección de registros de auditoría de EKS de GuardDuty y Runtime Monitoring son capacidades distintas, con configuración y cobertura independientes; habilitar solo los registros del plano de control no equivale a detección de amenazas en tiempo de ejecución.

</details>


## Referencias

* [Modo de prefijos de EKS](https://docs.aws.amazon.com/eks/latest/best-practices/prefix-mode-linux.html)
* [Procedimiento maxPods y prefijos de EKS](https://docs.aws.amazon.com/eks/latest/userguide/cni-increase-ip-addresses-procedure.html)
* [Política de red de EKS](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html)
* [Puertas de enlace NAT](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-nat-gateway.html)
* [Asociación de tabla de rutas de subred](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-ec2-subnetroutetableassociation.html)
* [Grupos de seguridad para Pods](https://docs.aws.amazon.com/eks/latest/userguide/security-groups-for-pods.html)
* [Complemento CoreDNS administrado](https://docs.aws.amazon.com/eks/latest/userguide/managing-coredns.html)
* [Caché de CoreDNS](https://coredns.io/plugins/cache/)
* [Recarga de CoreDNS](https://coredns.io/plugins/reload/)
* [Multitenencia de Kubernetes](https://kubernetes.io/docs/concepts/security/multi-tenancy/)
* [PDB de Kubernetes](https://kubernetes.io/docs/tasks/run-application/configure-pdb/)
* [Cluster Autoscaler de EKS](https://docs.aws.amazon.com/eks/latest/best-practices/cas.html)
* [Actualizaciones de nodos administrados de EKS](https://docs.aws.amazon.com/eks/latest/userguide/managed-node-update-behavior.html)
* [Calico en EKS](https://docs.tigera.io/calico/latest/getting-started/kubernetes/managed-public-cloud/eks)
* [NetworkPolicy de Calico](https://docs.tigera.io/calico/latest/reference/resources/networkpolicy)
* [IRSA](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
* [Rol IAM de nodo de EKS](https://docs.aws.amazon.com/eks/latest/userguide/create-node-role.html)
