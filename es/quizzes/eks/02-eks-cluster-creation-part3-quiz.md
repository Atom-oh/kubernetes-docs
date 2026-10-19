# Cuestionario sobre la creación de clústeres de EKS - Parte 3

> **Última actualización**: 11 de septiembre de 2026

Este cuestionario abarca las redes de EKS, la capacidad de los nodos, la multi-tenencia, el escalado automático y la seguridad de los nodos. Los comandos y manifiestos son ejemplos didácticos; no se ha ejecutado ninguna implementación en la nube ni se ha probado el comportamiento integral durante esta revisión. Antes de usarlos, confirma la cuenta de destino, la Región, el kubeconfig, las versiones compatibles de los complementos y la propiedad de los recursos.

## Preguntas sobre conceptos básicos

1. En el cálculo convencional de direcciones IPv4 secundarias, ¿qué determina los límites de ENI y de direcciones por ENI?
   * A) El nombre del espacio de nombres
   * B) El tipo de instancia de EC2
   * C) El nombre del Service
   * D) El nombre del Deployment

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El tipo de instancia de EC2**

En el **modo de IP secundaria** IPv4 para Linux, si hay suficientes direcciones de subred y no se usa redes personalizadas ni grupos de seguridad para Pods, el tipo de instancia proporciona los límites de ENI y de direcciones por ENI. Esto permite estimar el límite convencional de Pods del nodo, no las «direcciones IP por Pod».

La fórmula convencional reserva la dirección principal de **cada** ENI:

```text
ENIs × (IPv4 addresses per ENI − 1) + 2
```
Las dos adicionales corresponden a la asignación histórica para la red del host de `aws-node` y `kube-proxy`. La tabla conserva este cálculo de IP secundaria; **no** representa el `maxPods` efectivo de todas las AMI, modos de CNI o grupos de nodos administrados.

| Tipo de instancia | ENI máx. | IP por ENI | Pods máx. |
| ------------- | -------- | ----------- | -------- |
| t3.small      | 3        | 4           | 11       |
| t3.medium     | 3        | 6           | 17       |
| m5.large      | 3        | 10          | 29       |
| m5.xlarge     | 4        | 15          | 58       |
| m5.2xlarge    | 4        | 15          | 58       |
| m5.4xlarge    | 8        | 30          | 234      |
| c5.large      | 3        | 10          | 29       |
| c5.xlarge     | 4        | 15          | 58       |
| r5.large      | 3        | 10          | 29       |
| r5.xlarge     | 4        | 15          | 58       |

**Comprobar la capacidad real y los límites de EC2:**

```bash
kubectl get nodes -o custom-columns=NAME:.metadata.name,TYPE:.metadata.labels.node\\.kubernetes\\.io/instance-type,CAPACITY:.status.capacity.pods,ALLOCATABLE:.status.allocatable.pods
aws ec2 describe-instance-types --region us-west-2 \
  --instance-types m5.large m5.4xlarge \
  --query 'InstanceTypes[].{Type:InstanceType,ENIs:NetworkInfo.MaximumNetworkInterfaces,IPv4PerENI:NetworkInfo.Ipv4AddressesPerInterface}'
```
El agotamiento de la subred puede impedir la creación de Pods incluso por debajo del límite del nodo. También importan las solicitudes de CPU y memoria, otros Pods con red del host, las redes personalizadas, los grupos de seguridad para Pods y la configuración de kubelet. Los grupos de nodos administrados limitan `maxPods` a 110 en instancias con menos de 30 vCPU y a 250 en las demás, independientemente de que el resultado de la fórmula sea mayor.

La delegación de prefijos IPv4 asigna un `/28` a una **ranura** de dirección secundaria en una ENI; pueden ocupar una misma ENI varios prefijos. Esto no aumenta el espacio de direcciones de la subred. Consulta la pregunta 5 para conocer los requisitos previos y la migración.

Para una AMI personalizada de AL2023, configura `spec.kubelet.config.maxPods` en NodeConfig después de calcular y probar un valor adecuado. Con un grupo de nodos administrado y sin un ID de AMI personalizado, EKS calcula el valor recomendado. Elevar únicamente el límite de kubelet no permite disponer de más direcciones IP ni de más capacidad de cómputo. No pases la opción inexistente de eksctl `--kubelet-extra-args`.

</details>

2. Si ningún NetworkPolicy selecciona un Pod, ¿cuál es su estado de aislamiento de NetworkPolicy?
   * A) No está aislado, sujeto a otros controles de red
   * B) Solo admite tráfico dentro del mismo espacio de nombres
   * C) Requiere reglas explícitas de permiso
   * D) Se deniega todo el tráfico

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) No está aislado, sujeto a otros controles de red**

Si no hay una política que seleccione un Pod para una dirección del tráfico, Kubernetes NetworkPolicy deja esa dirección sin aislar. Esto **no** elude los grupos de seguridad, las tablas de rutas, las NACL, otras API de políticas ni el listener de una aplicación.

Amazon VPC CNI aplica NetworkPolicy de forma nativa cuando está habilitado en nodos Linux de EC2 compatibles. Las directrices actuales para las políticas estándar y de administración requieren VPC CNI 1.21 o posterior y el kernel 5.10 o posterior; verifica la compatibilidad del complemento seleccionado. La ruta de aplicación de estas políticas no abarca Windows ni Fargate. Usa Pods administrados por controladores (por ejemplo, Deployments) y comprueba las limitaciones de AWS relativas a las interfaces y los puertos de Service.

Las políticas de Calico con redes de AWS VPC y el encadenamiento de Cilium con AWS-CNI son alternativas con sus propios requisitos de instalación. No instales un segundo CNI sin configurarlo ni acumules agentes de políticas sin querer. AWS Network Firewall filtra el tráfico enrutado de la VPC; no implementa selectores de Kubernetes NetworkPolicy.

Los ejemplos siguientes son para un espacio de nombres `network-policy-lab` **nuevo y dedicado**. La primera política aísla solo el tráfico de entrada. Las dos siguientes permiten tráfico específico; el par `prod` requiere tanto la etiqueta integrada del espacio de nombres como la etiqueta del Pod de backend.

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
Para aislar el tráfico de salida, permite por separado la ruta DNS real y las dependencias de la aplicación. Una conexión denegada solo es significativa después de que funcionen la conectividad de referencia, DNS, la disponibilidad y un control positivo permitido. No apliques políticas de denegación general a `kube-system` ni a un espacio de nombres `default` compartido como prueba rápida.

</details>

3. ¿Cuál es una ruta convencional de salida a Internet para una subred IPv4 privada?
   * A) Asociar una IGW a la subred
   * B) Enrutar hacia una gateway NAT pública y luego hacia la IGW de la VPC
   * C) Asignar una Elastic IP a cada Pod
   * D) Enviar directamente una gateway NAT privada a través de una IGW

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Enrutar hacia una gateway NAT pública y luego hacia la IGW de la VPC**

Para los nodos y Pods IPv4 privados que necesitan salida a la Internet IPv4 pública, un diseño habitual enruta la ruta predeterminada de la subred privada hacia una **gateway NAT pública en una subred pública**. Esa subred pública tiene una ruta hacia una gateway de Internet asociada a la **VPC**, y la gateway NAT tiene una Elastic IP. Una instancia NAT es otro diseño, con requisitos adicionales de enrutamiento, comprobación de origen/destino y operación.

Con el comportamiento predeterminado de SNAT IPv4 de VPC CNI, el tráfico de Pods que sale de la VPC usa primero la dirección IPv4 principal del nodo. Los nodos públicos con dirección IPv4 pública y una ruta a una IGW pueden usar otra ruta. La salida IPv6 nativa puede usar una gateway de Internet de solo salida; el acceso a servicios de AWS mediante endpoints de VPC quizá no requiera NAT a Internet. No consideres NAT un requisito universal para todos los Pods.

**Ejemplo de enrutamiento de CloudFormation en una AZ:** muestra asociaciones de rutas públicas y privadas; no es una VPC completa de EKS. Las subredes de clúster de EKS requieren al menos dos AZ. Para un diseño con NAT por zona, considera una gateway NAT y una ruta privada por AZ para evitar una dependencia entre AZ. Las gateways NAT y las direcciones IPv4 públicas generan cargos. Para implementar un clúster, consulta la plantilla completa de VPC de EKS en la guía de conceptos.

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

Después de una implementación revisada de forma independiente, inspecciona los ID y las rutas reales. Si, en su lugar, creas una gateway NAT mediante la CLI, guarda el ID devuelto y espera a que su estado sea `nat-gateway-available` antes de crear una ruta. Si falla la creación de NAT, detén el flujo de trabajo.

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
`vpc.nat.gateway: Single` de eksctl es válido para su flujo de creación de VPC administrada, pero introduce una dependencia de una sola AZ. `HighlyAvailable` crea una NAT zonal en cada AZ. Estas opciones no corrigen el enrutamiento de subredes existentes arbitrarias. Para una pila de laboratorio, elimina solo los recursos que hayas creado, después de quitar las cargas de trabajo/ENI dependientes; confirma que se hayan liberado la NAT y su EIP.

</details>

4. ¿Qué ajuste de Pod comparte la red del nodo en lugar de usar una ENI de ramificación del Pod?
   * A) Una etiqueta coincidente del Pod
   * B) Una etiqueta coincidente de ServiceAccount
   * C) hostNetwork: true
   * D) Un SecurityGroupPolicy seleccionado

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) hostNetwork: true**

Un Pod que usa la red del host comparte el espacio de nombres de red y los grupos de seguridad del nodo. Los grupos de seguridad para Pods usan ENI de ramificación para los Pods seleccionados que tienen su propio espacio de nombres de red.

Los requisitos previos para este ejemplo en Linux sobre EC2 incluyen un tipo de instancia compatible con trunking, una versión compatible de VPC CNI, permisos `AmazonEKSVPCResourceController` para el rol del clúster y `ENABLE_POD_ENI=true`. Las familias EC2 `t` y EKS Auto Mode no admiten esta función. Verifica DNS, las reglas del plano de control y de la aplicación, la capacidad de ENI de ramificación y `POD_SECURITY_GROUP_ENFORCING_MODE`; el comportamiento de SNAT y las políticas varía según el modo. Usa el flujo de configuración del responsable del complemento en vez de aplicar un manifiesto antiguo de CNI.

SecurityGroupPolicy selecciona Pods mediante **`podSelector` o `serviceAccountSelector`**; no es obligatorio crear una ServiceAccount especial para seleccionar Pods. `ENIConfig` es un recurso de redes personalizadas y no se requiere solo para usar grupos de seguridad para Pods.

Para la alternativa con selector de ServiceAccount de abajo, primero crea un espacio de nombres dedicado `pod-sg-lab`, reemplaza el marcador de posición del SG por un grupo existente y revisado en la VPC correcta y cumple los requisitos previos. Este cliente en espera demuestra la selección; no demuestra conectividad con la base de datos. Están presentes tanto una etiqueta coincidente de ServiceAccount como `serviceAccountName` del Pod.

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
Como alternativa, reemplaza `serviceAccountSelector` por `podSelector: {matchLabels: {app: db-client}}`. Mantén la política y los Pods seleccionados en el mismo espacio de nombres. Verifica la ENI de ramificación de un Pod **recién creado** y las conexiones permitidas/denegadas reales; crear una política no la aplica retroactivamente a los Pods en ejecución. Después de las pruebas, limpia solo este espacio de nombres de laboratorio y su política, y no elimines un SG que sigan usando otros recursos.

</details>



5. ¿Cuál es el principal beneficio de capacidad de la delegación de prefijos IPv4?
   * A) Tráfico Pod a Pod más rápido garantizado
   * B) Más capacidad de IP de Pods por nodo
   * C) Direcciones IPv4 públicas para cada Pod
   * D) Aislamiento de red automático

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Más capacidad de IP de Pods por nodo**

En el modo de prefijos IPv4 de Linux, un `/28` (16 direcciones) ocupa una ranura de dirección secundaria de la ENI. Se pueden adjuntar varios prefijos a una ENI; el número máximo de ENI no aumenta. Esto puede elevar la densidad de Pods basada en IP y reducir el trabajo de la API de asignación de direcciones, sujeto a los límites de kubelet y de recursos.

Para `m5.large`, el cálculo convencional de IP secundaria da 29 Pods. Un grupo de nodos administrado compatible en modo de prefijos puede usar un `maxPods` recomendado de 110, no un valor sin límite «superior a 110». Las ranuras de direcciones teóricas no garantizan la capacidad de una aplicación.

**Requisitos previos y concesiones:**

* Usa una instancia Nitro compatible y una versión compatible de CNI (el mínimo histórico para IPv4 en Linux es 1.9.0; elige una versión actualmente compatible).
* La subred necesita bloques `/28` contiguos. Una subred fragmentada puede fallar con `InsufficientCidrBlocks` aunque tenga muchas IP individuales libres. Las reservas de CIDR de subred pueden preservar espacio para prefijos.
* Los prefijos consumen direcciones reales de la subred en bloques. No amplían un CIDR ni garantizan un menor consumo de IP, una mejor utilización o un costo menor.
* `WARM_PREFIX_TARGET` especifica prefijos libres. `WARM_IP_TARGET` especifica IP libres; `MINIMUM_IP_TARGET` establece una asignación total mínima. Si se configuran, los dos últimos prevalecen sobre `WARM_PREFIX_TARGET`. Ajústalos teniendo en cuenta la latencia de inicio y el consumo de direcciones no utilizadas.
* Planifica grupos de nodos de reemplazo y una migración controlada con cordon y drain. No te limites a cambiar la variable y reiniciar todos los Pods. Comprueba los PDB, los volúmenes, la capacidad disponible y la reversión; valida los nodos nuevos antes de retirar los grupos antiguos.

Lo siguiente es un **ejemplo de configuración para un clúster nuevo**, no un comando de actualización de un clúster existente. Usa acceso privado a la API, por lo que el administrador necesita una ruta de administración enrutada. Si no se proporciona una versión, se selecciona la versión predeterminada compatible de CNI para EKS; registra y revisa la versión resuelta real antes de la implementación. `withOIDC` participa en la integración IAM de CNI de eksctl; revisa el rol resultante. Los límites de tamaño no instalan un autoscaler.

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
   * A) Un grupo de seguridad de nodo
   * B) El ConfigMap de coredns
   * C) Una StorageClass
   * D) Un PodDisruptionBudget

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El ConfigMap de coredns**

El ConfigMap `coredns` contiene `data.Corefile`. El **responsable de la configuración** correcto depende de si CoreDNS es un complemento administrado de EKS o autoadministrado.

Para el complemento administrado, tanto la consola de AWS como `aws eks update-addon --configuration-values` pueden personalizar los campos admitidos. Una edición directa del ConfigMap puede sobrescribirse al actualizar el complemento: guarda el Corefile personalizado completo en la clave de configuración `corefile` del complemento. Conserva las claves de configuración existentes y revisa el esquema para la versión exacta del complemento.

Usa un directorio de trabajo local nuevo para guardar la configuración actual antes de editarla:

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
Edita `Corefile.reviewed` y conserva la zona de Kubernetes y los complementos de reenvío, `ready`, estado de salud y supervisión que requiera esta instalación. Estos son ejemplos independientes de personalización, no un Corefile de reemplazo:

* Añade registros estáticos al bloque de servidor existente; usa las direcciones internas reales:

```text
hosts {
    10.0.0.1 example.com
    10.0.0.2 api.example.com
    fallthrough
}
```
* Usa un bloque de servidor independiente para un reenviador condicional; el upstream debe ser accesible y no debe reenviar de vuelta a este servicio de CoreDNS:

```text
example.org:53 {
    errors
    forward . 10.0.0.53
    cache 30
}
```
* Reemplaza la sección `cache` existente en lugar de añadir una duplicada. La duración de `prefetch` requiere una unidad:

```text
cache {
    success 10000
    denial 5000
    prefetch 10 10m 10%
}
```
* Registro opcional de consultas de clase de error (revisa el volumen y los nombres sensibles):

```text
log {
    class error
}
```
`autopath` es un complemento independiente para completar la ruta de búsqueda del lado del servidor, no una subdirectiva de `kubernetes`. `autopath off` dentro del bloque de Kubernetes no es válido. Para desactivar un `autopath @kubernetes` existente, elimina esa directiva; no la añadas a instalaciones que nunca la habilitaron.

Después de revisar el esquema y la sintaxis, actualiza la **misma** versión del complemento:

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
La respuesta todavía puede ser `InProgress`. Vuelve a comprobar este ID de actualización hasta que el estado sea `Successful`; si falla, detente e inspecciona los errores antes de hacer otro cambio. Luego verifica que el Deployment esté listo, los registros, las búsquedas del Service interno y los casos DNS personalizados. Si hace falta, restaura la configuración guardada mediante el mismo responsable.

Para CoreDNS autoadministrado, edita el ConfigMap a través del responsable de GitOps/manifiestos. Con `reload`, los cambios del Corefile se detectan después de la proyección del ConfigMap y del intervalo de recarga; no siempre es necesario reiniciar. Supervisa los errores de recarga y el comportamiento de DNS. Los cambios en los ajustes del Deployment quizá requieran un rollout.

**Escalado y recursos:** CoreDNS administrado por EKS admite un objeto de configuración `autoScaling` cuando la versión elegida cumple los requisitos previos de AWS. Deja que un solo controlador sea responsable de las réplicas. El siguiente HPA de CPU es una **alternativa para CoreDNS autoadministrado** que requiere Metrics Server y solicitudes de CPU; no lo ejecutes junto con el escalado automático de CoreDNS de EKS:

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
El rango de 2–10 réplicas y el objetivo del 60 % son ejemplos, no un dimensionamiento medido. Revisa la memoria, el estrangulamiento de CPU, el crecimiento de la caché, la topología y la latencia de DNS; cambia los recursos mediante el esquema del complemento o el responsable de la carga autoadministrada, en lugar de reemplazar todo un objeto de recursos por índice de matriz de contenedores.

</details>

7. ¿Qué combinación permite un aislamiento lógico para equipos de confianza que comparten un clúster de EKS?
   * A) Solo espacios de nombres
   * B) Espacios de nombres, RBAC, políticas aplicadas y cuotas
   * C) Solo selectores de nodos
   * D) Un rol compartido de cluster-admin

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Espacios de nombres, RBAC, políticas aplicadas y cuotas**

Para equipos con confianza mutua que comparten un clúster, los espacios de nombres junto con RBAC, políticas de red aplicadas y cuotas proporcionan una separación lógica útil. No son una solución universal para inquilinos hostiles.

El administrador de la plataforma crea los espacios de nombres nuevos `tenant-a`/`tenant-b` y aplica una política de Pod Security Admission adecuada (para este ejemplo de EKS 1.36 en Linux, Restricted con la versión `v1.36`). El siguiente conjunto de políticas corresponde a `tenant-a`; aplica una política equivalente y revisada para `tenant-b`. También se requiere una asignación autenticada del grupo `tenant-a-users`.

Los permisos de la aplicación son explícitos. A través de este Role, el inquilino no puede cambiar directamente ResourceQuota, LimitRange, NetworkPolicy, Roles ni RoleBindings. Los recursos con ámbito de clúster siguen siendo responsabilidad de la plataforma.

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

* La creación de cargas de trabajo aún puede usar ServiceAccounts accesibles y montar Secrets del espacio de nombres. Este Role no constituye un límite de confidencialidad de Secrets dentro de un inquilino. Aplica políticas de admisión para restringir las identidades, los montajes y los ajustes de seguridad permitidos; mantén las credenciales de la plataforma fuera de los espacios de nombres de los inquilinos.
* La regla DNS presupone Pods normales de CoreDNS con la etiqueta `k8s-app=kube-dns` en `kube-system`. Adáptala y pruébala para NodeLocal DNSCache u otra ruta DNS. Permite consultas DNS, no toda la salida a Pods del sistema; tampoco oculta los nombres DNS de otros espacios de nombres.
* Las cuotas limitan las solicitudes y cantidades de recursos admitidas; no reservan nodos físicos, no garantizan ancho de banda ni eliminan los vecinos ruidosos. Los valores de LimitRange son valores predeterminados ilustrativos.
* Antes de incorporar equipos, verifica los permisos efectivos y la aplicación de las políticas con una identidad de inquilino, conexiones permitidas, conexiones entre inquilinos denegadas y casos de rechazo por cuota.
* Los grupos de nodos dedicados reducen algunos tipos de uso compartido, pero los selectores de nodos y las taints por sí solos no son límites de seguridad. Para un aislamiento más sólido, evalúa entornos de ejecución aislados, planos de control virtuales o clústeres/cuentas/redes separados, junto con sus dependencias compartidas y costos operativos.

Compartir espacios de nombres puede reducir la carga del plano de control y simplificar las operaciones centralizadas. El nivel de aislamiento necesario, no una afirmación universal de que exista una opción «óptima», determina el diseño.

</details>

8. ¿Qué elemento no cambia por sí mismo la capacidad técnica de un tipo de instancia de EC2?
   * A) Tamaño de vCPU y memoria
   * B) Límites de red y almacenamiento
   * C) Una etiqueta de nombre que solo se muestra
   * D) Límites de ENI y direcciones

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Una etiqueta de nombre que solo se muestra**

Al seleccionar una instancia, hay que tener en cuenta la CPU, la memoria, las necesidades de aceleración, las imágenes/AMI compatibles con la arquitectura y los controladores, la densidad de Pods, el ancho de banda de red, el rendimiento de EBS/almacenamiento de instancia, la disponibilidad de AZ, la tolerancia a interrupciones y el costo. La versión de Kubernetes puede importar por las AMI, los controladores y las funciones admitidas; no es irrelevante.

Los ejemplos de familias originales a continuación ilustran perfiles de carga de trabajo, no una clasificación actual de precio/rendimiento. `m5` es de propósito general, `r5` está optimizada para memoria y `c5` para cómputo. Las alternativas Graviton requieren imágenes y dependencias compatibles con Arm. Las cargas de trabajo con GPU también necesitan una AMI acelerada adecuada y un complemento de dispositivo. Los datos del almacenamiento de instancia son efímeros; las etiquetas por sí solas no proporcionan durabilidad de bases de datos ni ubicación.

Estos son **archivos de configuración alternativos para grupos de nodos** de un clúster existente y revisado (`eksctl create nodegroup -f ...`), con nombres de grupo no utilizados y subredes privadas que cuenten con la salida/endpoints requeridos. Revisa las ofertas reales por Región/AZ. Los límites no instalan Cluster Autoscaler; un grupo de procesamiento por lotes en cero necesita un autoscaler configurado correctamente o escalado manual.

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

**Nodos de trabajo Spot interrumpibles**

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
EKS proporciona 14 meses de soporte de versión estándar, seguidos de 12 meses de soporte extendido. Consulta el calendario de soporte de EKS, los requisitos de actualización y la compatibilidad de complementos por separado de las versiones de Kubernetes upstream. Estos ejemplos no afirman que haya ahorros de costos ni capacidad medidos.

</details>

9. ¿Qué objeto de Kubernetes limita la expulsión voluntaria de Pods durante un drain?
   * A) StorageClass
   * B) PodDisruptionBudget
   * C) ConfigMap
   * D) IngressClass

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) PodDisruptionBudget**

Un PDB limita las expulsiones voluntarias mediante la API de Eviction. Es una parte de la estrategia de actualización, no una garantía de disponibilidad. Un fallo del nodo, la eliminación directa de un Pod y una actualización gradual propia de un Deployment no están impedidos por un PDB.

Para un Deployment `update-lab` revisado con tres réplicas etiquetadas `app=my-app`, este ejemplo solo permite la expulsión si quedan al menos dos Pods seleccionados en buen estado:

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
Una alternativa es `maxUnavailable: "50%"`; especifica solo uno de los campos de presupuesto. El redondeo de porcentajes se hace **hacia arriba**, por lo que esta opción permite que haya dos Pods no disponibles de tres, o uno de uno. No promete que quede disponible al menos la mitad. Elige los presupuestos en función del quórum, la disponibilidad, el comportamiento de la carga de trabajo y la capacidad programable disponible.

Las actualizaciones `DEFAULT` de un grupo de nodos administrado lanzan capacidad de reemplazo antes de drenar los nodos antiguos seleccionados. `MINIMAL` reduce las necesidades de capacidad temporal terminando primero los nodos antiguos seleccionados. `maxUnavailable` controla la indisponibilidad simultánea de nodos; los PDB limitan las expulsiones de Pods por separado. No uses `--force` habitualmente como respuesta a un drain bloqueado, ya que puede eludir la protección de expulsión de Pods.

Configura la política de actualización de nodos y espera a que esta actualización específica termine correctamente **antes** de iniciar una actualización de versión:

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
Consulta `describe-update` hasta que ese ID tenga estado `Successful` y gestiona explícitamente los estados `Failed`/`Cancelled`. El comando original de eksctl `update nodegroup --max-unavailable` no es una alternativa compatible. Comprueba el valor real de `disruptionsAllowed` del PDB, la disponibilidad, el estado de la aplicación y la reubicación de volúmenes; una configuración de tres réplicas es un ejemplo, no un mínimo universal.

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

| Componente | Objeto controlado |
| --- | --- |
| Cluster Autoscaler | Capacidad deseada de grupos de nodos/ASG existentes detectados, según la posibilidad de programar Pods y de retirar nodos de forma segura |
| Karpenter | Sus propios NodeClaims/capacidad de EC2 seleccionados mediante NodePools y EC2NodeClasses; no los ASG de grupos de nodos administrados |
| HPA / KEDA | Réplicas de cargas de trabajo a partir de métricas de recursos/personalizadas/externas o eventos |
| VPA | Recomendaciones/solicitudes de recursos de Pods según el modo de actualización |

**Cluster Autoscaler:** usa la misma versión menor de Kubernetes que el clúster. Para el ejemplo de EKS 1.36, el chart 9.59.0 debe usar explícitamente la imagen `v1.36.1` (su imagen predeterminada es 1.35.0). Primero configura una ServiceAccount dedicada `cluster-autoscaler` con permisos IAM revisados y limitados por etiquetas y etiquetas de detección de ASG. Genera y revisa el RBAC, la imagen y los argumentos antes de la instalación:

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
No desactives a la ligera las protecciones de almacenamiento local ni permitas que las políticas predictivas/de seguimiento de objetivos del ASG compitan con Cluster Autoscaler por la misma capacidad deseada.

**Alternativa Karpenter:** instala y autoriza el controlador compatible por separado. Sustituye el ID de AMI, el rol de nodo y los valores de la etiqueta de detección por recursos revisados para este clúster; la AMI debe ser compatible con AL2023, la versión de Kubernetes y la arquitectura. Fija un ID de AMI o un alias versionado y probado en lugar de elegir silenciosamente `al2023@latest`. Los límites y el tiempo de consolidación siguientes son ejemplos, no un dimensionamiento medido ni garantías de velocidad de aprovisionamiento.

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
**HPA:** este ejemplo requiere un Deployment `my-app` existente en `autoscaling-lab`, Metrics Server y solicitudes de CPU:

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
**VPA:** instala primero los CRD/controladores de VPA. Comienza en modo de solo recomendación e inspecciona las recomendaciones antes de elegir un modo de actualización explícito compatible:

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
`Off` no cambia los recursos de los Pods. Aplicar recomendaciones puede requerir volver a crear Pods o cambiar su tamaño in situ de forma compatible, según las versiones y la configuración de VPA/Kubernetes; no prometas que siempre habrá un reinicio. Actualizar las solicitudes de CPU mientras un HPA basado en la utilización de CPU controla la misma carga crea una retroalimentación a través del denominador de utilización. El ejemplo de solo recomendaciones evita ese conflicto hasta que se revise un diseño coordinado.

</details>

## Ejercicios prácticos

### Ejercicio 1: Implementación de políticas de red en un clúster de EKS

**Escenario:** permite frontend → backend y backend → database, mientras deniegas frontend → database. Conserva el objetivo didáctico original de Calico usando AWS VPC CNI para la asignación de IP.

**Alcance:** un clúster EKS IPv4 de Linux existente y desechable, sin políticas globales/de nivel en conflicto, CoreDNS estándar y una instalación de Calico revisada por un administrador. Este es un ejercicio de conectividad, no una receta de producción para microservicios/base de datos. La instalación en la nube y las pruebas de tráfico no se ejecutaron durante esta auditoría.


<details>
<summary>Mostrar solución</summary>

**1. Prepara el motor de políticas.** Sigue la ruta oficial de Calico para EKS con **redes de Amazon VPC**. Desactiva NetworkPolicy nativo de AWS VPC CNI mediante su responsable de configuración; entra en conflicto con la aplicación de políticas de Calico. Conserva la red de `aws-node`. Habilita su ajuste `ANNOTATE_POD_IP=true` y concede a su ServiceAccount permiso para aplicar parches a Pods. Este ejemplo de RBAC dedicado añade ese permiso sin agregar YAML mal formado al ClusterRole del complemento:

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
Guarda y revisa el RBAC, y luego aplícalo solo a la ServiceAccount `aws-node` prevista; configura la variable de entorno mediante el complemento administrado o el responsable del manifiesto autoadministrado. No continúes hasta que el rollout y el comportamiento de las anotaciones sean correctos. Si Calico ya está instalado, revísalo y reutilízalo en lugar de ejecutar los siguientes comandos de instalación nueva.

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
Una vez establecidos los CRD del operador, crea los recursos `Installation` y `APIServer` revisados siguientes. La instalación del operador por sí sola no configura redes de AWS VPC. Se necesita el servidor de API para los ejemplos de políticas `projectcalico.org/v3`:

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
Espera a que los componentes de Calico y la API agregada estén disponibles; luego verifica la aplicación real de las políticas más abajo. Que el nodo esté `Ready` no basta. La interfaz opcional Goldmane/Whisker no se necesita para este ejercicio.

**2. Crea un espacio de nombres propio y una credencial temporal de base de datos.** Usa una misma sesión de Bash para los fragmentos restantes. Se registra el nombre y el UID del espacio de nombres para que la limpieza no pueda dirigirse intencionalmente a otro espacio:

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
**3. Implementa los tres niveles.** Los servidores HTTP de Python sustituyen a frontend/backend para que el cliente TCP de diagnóstico esté disponible en ambos contenedores. La imagen PostgreSQL 17 usa `POSTGRES_PASSWORD_FILE` y un Secret del espacio de nombres; no realiza ninguna operación externa con la base de datos. El `emptyDir` de la base de datos **se pierde cuando se reemplaza el Pod**. No guardes aquí datos valiosos. Se conserva el comportamiento de inicialización de la imagen de la base de datos; este no es un manifiesto de base de datos de producción con perfil Restricted. Las etiquetas de imagen de versión principal son mutables: registra los digest resueltos para que la ejecución sea reproducible.

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
**4. Establece la conectividad de referencia.** Las tres rutas TCP y DNS deben funcionar antes de aplicar la política. Que el puerto 5432 acepte una conexión solo demuestra una conexión TCP, no que funcionen la autenticación SQL ni la aplicación.

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
**5. Aplica y prueba la política.** Los Pods seleccionados quedan aislados en ambas direcciones; se deniega el tráfico que no coincide. Las reglas explícitas permiten las dos rutas de aplicación y DNS por UDP/TCP. Se necesitan selectores de espacio de nombres para llegar a CoreDNS fuera del espacio de nombres de laboratorio. Adapta la regla DNS para NodeLocal DNSCache u otras etiquetas antes de probarla.

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
La propagación de políticas es asíncrona. Un tiempo de espera agotado, un fallo de DNS, la ausencia del binario de diagnóstico o la indisponibilidad de la base de datos por sí sola no demuestran que el aislamiento se haya realizado correctamente. El procedimiento usa una conectividad de referencia funcional y controles positivos; investiga otras políticas/rutas si las observaciones difieren.

**6. Limpieza.** Elimina solo el espacio de nombres propio después de confirmar su UID. Esto elimina las cargas de trabajo de prueba, la política, el Secret y los datos efímeros, no la instalación de Calico del clúster. Elimina el archivo local de contraseña después del ejercicio. Conserva la configuración compartida de CNI/RBAC, salvo que haya un proceso de reversión revisado por un administrador que sea responsable de ella.

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

### Ejercicio 2: Configuración de IRSA y acceso a S3 en un clúster de EKS

**Escenario:** concede a una carga de trabajo acceso de solo lectura a un prefijo `training/` aprobado de un bucket de S3 existente, mediante IRSA en lugar del rol del nodo. Verifica la identidad del rol asumido y compárala con la de un Pod deliberadamente sin credenciales.

**Requisitos previos:** Bash, jq, AWS CLI, eksctl y kubectl; un clúster de EKS existente y autorizado; acceso de administrador a un espacio de nombres nuevo y un rol IAM; un objeto S3 existente aprobado y no sensible. Este ejemplo de la partición comercial presupone un objeto sin requisitos adicionales de KMS del cliente. Las políticas del bucket/KMS, las SCP, DNS, STS y las rutas de red a S3 pueden imponer requisitos adicionales. No se crea, modifica ni elimina ningún objeto de S3.


<details>
<summary>Mostrar solución</summary>

**1. Delimita el laboratorio y verifica OIDC.** Configura `EXAMPLE_CLUSTER`, `EXAMPLE_REGION`, `S3_BUCKET` y `S3_TEST_KEY` (dentro de `training/`). El proveedor OIDC es infraestructura compartida del clúster; no lo elimines durante la limpieza. Detente si falla la creación del espacio de nombres o la verificación del proveedor.

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
**2. Crea un rol único y acotado.** La relación de confianza requiere tanto `aud=sts.amazonaws.com` como el `sub` exacto del espacio de nombres/ServiceAccount. Si falla la creación del rol, detén la asociación de la política; registra el RoleId inmutable para la limpieza.

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
**3. Implementa y verifica.** Deja que se propaguen los cambios de IAM antes de volver a intentar una prueba fallida. Los tres contenedores comprueban la identidad, el recuento de objetos del listado del prefijo y la longitud del objeto, sin registrar su contenido ni las credenciales. La identidad debe coincidir con el rol recién creado; de lo contrario, el éxito de S3 podría deberse a un rol de nodo con permisos más amplios.

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
**4. Comparación negativa controlada.** La ServiceAccount predeterminada del espacio de nombres nuevo no debe tener anotación de IRSA ni asociación de EKS Pod Identity, y no se deben inyectar otras credenciales. Desactiva la alternativa de IMDS en este cliente de prueba y exige el error específico de ausencia de credenciales. Un error aleatorio de red o autorización no es un resultado negativo válido.

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
Esta es una comparación de proveedores de credenciales, no una prueba de que Pods arbitrarios no puedan acceder a IMDS ni de que los contenedores sean límites de seguridad. Restringe las credenciales de los nodos por separado. IRSA usa un token proyectado de identidad web y credenciales temporales de STS; los SDK compatibles las renuevan. No vuelques todas las variables de entorno `AWS_*` ni los archivos de token.

**5. Limpia solo los recursos propios.** Conserva el UID registrado del espacio de nombres y el RoleId de IAM. La limpieza protegida elimina el espacio de nombres del laboratorio, su política insertada y su rol único; conserva el bucket/objeto de S3, el proveedor OIDC compartido y el clúster. Si la configuración solo se completó parcialmente, inspecciona `ownership.json` y limpia únicamente los recursos que realmente estén registrados.

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

Las preguntas siguientes tratan temas avanzados relacionados con la creación de clústeres de Amazon EKS. Esta sección evalúa tu comprensión de conceptos avanzados y prácticas recomendadas para crear clústeres de EKS.

1. ¿Qué afirmación NO está garantizada por la delegación de prefijos IPv4?
   * A) Un prefijo usa una ranura de dirección de ENI
   * B) Puede caber más capacidad de IP en un nodo
   * C) Todas las aplicaciones están listas más rápido
   * D) Se requieren bloques contiguos en la subred

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Todas las aplicaciones están listas más rápido**

La delegación de prefijos puede reducir la latencia de asignación de direcciones: asociar otro prefijo a una ENI existente evita parte del trabajo de creación/asociación de ENI. AWS documenta este beneficio, por lo que la explicación original de que la delegación de prefijos no puede reducir el tiempo de inicio y necesariamente añade sobrecarga de enrutamiento era incorrecta.

La disponibilidad de extremo a extremo de un Pod sigue dependiendo de la programación, el inicio del nodo, la descarga de imágenes, la asociación de volúmenes, la inicialización, las sondas y el inicio de la aplicación. Aquí no se proporcionó ninguna comparación de referencia, y esta auditoría no ejecutó ninguna. No deduzcas una mejora de latencia fija ni inventes la causa de una ralentización.

Cada IPv4 `/28` consume una ranura de dirección secundaria y 16 direcciones de un bloque contiguo de la subred. Aumenta la capacidad de IP por nodo, sujeta a `maxPods`, los recursos de cómputo y el espacio de subred. No amplía el CIDR ni garantiza que haya menos direcciones asignadas. La configuración de los grupos de direcciones disponibles intercambia consumo de direcciones libres por disponibilidad de asignación.

Usa los requisitos previos y la migración a un grupo de nodos nuevo de la pregunta básica 5: inspecciona la fragmentación, configura un CNI compatible, valida la capacidad de nodo calculada y migra con capacidad disponible y drenado teniendo en cuenta los PDB. Reiniciar de forma general todos los Pods existentes no es un plan de transición completo.

</details>

2. ¿Qué práctica es incorrecta para grupos de nodos administrados con varios tipos de instancia que usan Cluster Autoscaler?
   * A) Usar perfiles de CPU/memoria/GPU comparables
   * B) Verificar la compatibilidad de las imágenes y las AZ
   * C) Separar los grupos Spot y bajo demanda
   * D) Mezclar perfiles arbitrarios porque el autoscaler simula todos los tipos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Mezclar perfiles arbitrarios porque el autoscaler simula todos los tipos**

La diversidad puede mejorar las opciones de capacidad, sobre todo para Spot, pero debe respetar el modelo de programación del autoscaler. Cluster Autoscaler simula un grupo mixto con el primer tipo de instancia; las opciones deben tener el mismo perfil de CPU, memoria y GPU. Las alternativas más pequeñas pueden dejar Pods pendientes, mientras que las más grandes pueden desperdiciar capacidad. Nombres parecidos no garantizan que coincidan los perfiles: por ejemplo, `c5n.large` tiene una memoria distinta de `c5.large`.

Un grupo de nodos administrado tiene un solo tipo de capacidad. Usa **grupos separados** para una base bajo demanda y la expansión Spot; listar varios `instanceTypes` no mezcla opciones de compra en un mismo grupo administrado. EKS elige la estrategia de asignación Spot administrada; `spotAllocationStrategy` no es un campo compatible de `managedNodeGroups` de eksctl.

Este ejemplo conserva perfiles comparables de la familia `m5`. Es una configuración de grupo de nodos para un clúster existente revisado con nombres de grupo no utilizados; no constituye una prueba de precio/rendimiento ni una garantía de capacidad. Verifica las ofertas por AZ y la compatibilidad de imágenes/controladores/almacenamiento:

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
Separa los distintos perfiles de carga de trabajo en lugar de combinar instancias optimizadas para memoria, cómputo y propósito general en un mismo grupo con escalado automático:

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
La carga de trabajo debe tener una toleration coincidente **y** un selector/afinidad si debe usar un grupo dedicado. Las etiquetas por sí solas no la programan, y las taints no son un límite de seguridad entre inquilinos. Ten en cuenta la detección al escalar desde cero, la sobrecarga de los daemon, la gestión de interrupciones, la persistencia del almacenamiento y las pruebas con todos los tipos candidatos. La diversidad puede aumentar el trabajo de supervisión y resolución de problemas; ni una gestión más sencilla ni un costo menor son automáticos.

</details>

3. ¿Qué estrategia crea un grupo de nodos de reemplazo independiente antes de retirar el antiguo?
   * A) Actualizaciones de paquetes del host sin seguimiento
   * B) Migración blue/green
   * C) Eliminar todos los nodos de una vez
   * D) Cambiar únicamente el nombre visible del clúster

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Migración blue/green**

Blue/green crea un grupo de nodos de reemplazo independiente y migra las cargas de trabajo después de validarlo. Puede conservar una opción de reversión mientras el grupo antiguo y el estado compatible de la aplicación/datos permanezcan disponibles. Dos grupos de nodos en un mismo clúster siguen compartiendo el plano de control y otras dependencias; esto no constituye un aislamiento completo ni garantiza cero tiempo de inactividad.

| Estrategia | Beneficio | Limitación importante |
| --- | --- | --- |
| Blue/green | Validar la capacidad de reemplazo antes de retirar definitivamente la anterior | Costo/capacidad adicional; la reversión depende de conservar los nodos y de la compatibilidad del estado |
| Actualización gradual administrada | EKS coordina el reemplazo gradual de nodos | `DEFAULT` usa nodos adicionales temporales; los fallos de PDB/capacidad pueden bloquear el avance |
| Canary | Probar primero un grupo/carga de trabajo pequeña e independiente | Hay que limitar realmente el alcance de la carga de trabajo/del tráfico; añade trabajo de validación y enrutamiento |
| Modificación manual de paquetes del host | Cambia un host individual | Crea una discrepancia con la AMI; usa un ciclo de vida revisado de imagen de reemplazo en lugar de una receta SSH/yum sin calificar |

**Ejemplo de grupo de reemplazo:** para un clúster existente y un nombre de grupo no utilizado, revisa este archivo y usa `eksctl create nodegroup -f green-nodegroup.yaml`. Confirma primero la compatibilidad de AL2023/arquitectura, los complementos, la salida, el espacio de IP, las cuotas y la topología de almacenamiento.

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
**Un canary real usa un Deployment independiente:** lo siguiente es una carga de trabajo HTTP de sondeo mínima en un espacio de nombres `update-lab` dedicado, con etiquetas únicas para que no se una accidentalmente al Service existente. Sustitúyela por un canary revisado de tu aplicación real antes de afirmar que es compatible. Aplicar un parche al selector de nodos del Deployment principal hace un rollout de **todas** sus réplicas y no es un canary limitado.

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
Valida la disponibilidad, API/CNI/DNS, los errores de la aplicación, la presión de recursos, los volúmenes persistentes y tráfico representativo durante un período de observación revisado. Mantén explícito el enrutamiento del tráfico; una etiqueta de nodo no cambia la ruta del tráfico. Cuando se hayan verificado la capacidad de reemplazo y el comportamiento de las cargas de trabajo/datos, drena un nodo antiguo confirmado cada vez:

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
Un drain bloqueado requiere diagnóstico, no `--force` ni eliminación automática de emptyDir. Confirma que todas las cargas de trabajo y el estado se hayan migrado antes de este paso final, que es independiente:

```bash
# Separate final step, after application/data validation and ownership review.
if [ "${MIGRATION_VERIFIED:?Set yes only after workload and data checks}" = yes ]; then
  eksctl delete nodegroup --cluster "${EXAMPLE_CLUSTER:?}" \
    --region "${EXAMPLE_REGION:?}" --name "${OLD_NODEGROUP_NAME:?}" --approve --wait
fi
```
Como alternativa gradual administrada, completa la operación `update-nodegroup-config` de la pregunta básica 9 antes de enviar `update-nodegroup-version`; luego sigue el ID de actualización devuelto. Un grupo administrado puede conservar su identidad de recurso mientras se reemplazan sus nodos de EC2. Una vez eliminada la capacidad antigua o modificados los datos de forma incompatible, ya no se dispone de una «reversión instantánea».

</details>

4. ¿Qué acción puede entrar en conflicto con la propiedad de un ASG administrado por Cluster Autoscaler?
   * A) Revisar las etiquetas de detección
   * B) Ajustar la frecuencia de análisis según observaciones
   * C) Usar solicitudes de recursos de Pod precisas
   * D) Añadir otra política que cambie de forma independiente la misma capacidad deseada

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Añadir otra política que cambie de forma independiente la misma capacidad deseada**

Cluster Autoscaler controla la capacidad del grupo de nodos según las solicitudes de programación, no solo la CPU promedio de EC2. Una política predictiva o de seguimiento de objetivos del ASG que cambie la misma capacidad deseada puede entrar en conflicto con ese ciclo de control y eludir el proceso previsto de drain de Kubernetes. No restablezcas directamente la capacidad deseada a dos como «optimización».

**Controles útiles:**

* Ajusta la frecuencia de análisis según el tiempo de reacción y la carga de la API. El valor predeterminado documentado es 10 segundos; 30 segundos es un ejemplo para probar, no un óptimo medido. Del mismo modo, los tiempos de espera de aprovisionamiento deben corresponder al comportamiento real de inicio de los nodos.
* Usa etiquetas de detección de ASG revisadas y permisos IAM limitados por etiquetas. Las etiquetas identifican los grupos aptos; no conceden permisos ni definen un algoritmo de escalado.
* Haz coincidir las solicitudes, las etiquetas y las taints con la capacidad real. Puede ser apropiado un tipo de instancia; la diversidad de perfiles comparables resulta útil cuando lo justifican las necesidades de disponibilidad/Spot (pregunta avanzada 2).
* Usa las prioridades deliberadamente. La preemption no garantiza la disponibilidad y puede interrumpir cargas de trabajo de menor prioridad. Vincula la siguiente clase mediante `priorityClassName` solo después de evaluar las políticas de admisión y de carga de trabajo:

```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: audit-high-priority
value: 1000000
globalDefault: false
description: Reviewed priority for critical application Pods
```
**Sobreaprovisionamiento:** reserva solicitudes con Pods desalojables de baja prioridad. Para este ejemplo, el límite de Pods prescindibles configurado en Cluster Autoscaler debe ser inferior a `-5` (por ejemplo, `-10`), y los Pods de aplicación deben tener una prioridad superior. De lo contrario, puede que los Pods de reserva no activen la reposición prevista. Usa un espacio de nombres dedicado y un nombre de PriorityClass no utilizado:

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
Esto reserva 1 CPU y 1000 Mi de capacidad solicitada, no un estado de aplicación precalentado, y genera costos de nodo. No evita la descarga de imágenes, la asociación de volúmenes ni la inicialización de la aplicación. Dimensiona según la demanda observada y, después de la prueba, elimina el Deployment de reserva y la PriorityClass propios.

Usa la configuración completa de Cluster Autoscaler generada en la pregunta básica 10, en lugar del Deployment 1.23 antiguo e incompleto. Karpenter es una alternativa para capacidad administrada por separado; su NodePool debe hacer referencia a una EC2NodeClass válida y autorizada. KEDA/HPA escalan las réplicas de cargas de trabajo, lo que puede generar demanda para cualquiera de los autoscalers de nodos. Valida estos ciclos de control interrelacionados en lugar de habilitar todos los mecanismos de escalado para los mismos recursos.

</details>

5. ¿Cuál NO es una práctica recomendada general de seguridad para un grupo de nodos de EKS?
   * A) Exigir IMDSv2 y revisar el acceso a metadatos
   * B) Usar IAM con privilegios mínimos
   * C) Asignar una IP pública a cada nodo
   * D) Revisar las reglas de los grupos de seguridad

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Asignar una IP pública a cada nodo**

Asignar una IP pública a cada nodo no es una práctica recomendada general de seguridad. Las subredes privadas reducen la exposición directa a Internet, pero siguen siendo importantes las rutas, los grupos de seguridad, IAM, el mantenimiento del software y los controles de las cargas de trabajo.

**Identidad del nodo y metadatos:** exige IMDSv2 con el campo compatible de eksctl `disableIMDSv1`. Un objeto anidado `metadataOptions` no es un campo de eksctl para grupos de nodos administrados; las opciones de metadatos de EC2 personalizadas pertenecen a una plantilla de lanzamiento revisada. IMDSv2 mitiga algunas rutas de SSRF, pero no impide que todos los Pods accedan a las credenciales del nodo, especialmente los Pods que usan la red del host. Revisa el acceso a los metadatos por separado de la identidad de la carga de trabajo y las dependencias del host.

**Privilegios mínimos y volumen raíz cifrado:** este ejemplo de grupo de nodos para un clúster existente presupone que el CNI ya tiene sus propios permisos de IRSA/Pod Identity. EBS CSI, los recopiladores de registros y las aplicaciones también necesitan sus propios roles revisados; adjuntarles sus permisos amplios a todos los nodos contradice el principio de privilegios mínimos.

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
El cifrado de EBS protege una capa distinta de los datos de la API de Kubernetes. EKS 1.28 y versiones posteriores cifran todos los datos de la API de Kubernetes en reposo con cifrado de sobre predeterminado; una clave KMS administrada por el cliente es opcional y conlleva permisos/concesiones adicionales y obligaciones relativas al ciclo de vida de la clave. No deshabilites ni elimines la clave de un clúster como parte de la limpieza habitual.

**Diseño de red:** un endpoint de API privado requiere una ruta de acceso enrutada para administradores/nodos. Las restricciones de la API pública usan `publicAccessCidrs`, no una regla de entrada en el SG del clúster. Revisa los requisitos completos de AWS para los SG del clúster/nodo: TCP 443, TCP 10250, TCP/UDP 53 y las rutas específicas de las cargas de trabajo, con las direcciones y los grupos de pares correctos. Dos reglas de puertos de entrada no constituyen un diseño completo de red de nodos.

La salida IPv4 privada a Internet puede usar NAT; los endpoints de VPC y las rutas IPv6 nativas son distintos. El tráfico entrante puede llegar desde balanceadores de carga o redes conectadas autorizadas. Una subred privada por sí sola no demuestra ni el aislamiento completo ni el cumplimiento normativo.

**Controles de contenedores:** usa una carga de trabajo compatible con la ejecución sin privilegios de root y de solo lectura. Este Pod de diagnóstico administrado por controlador se ejecuta en un espacio de nombres `security-lab` **nuevo y dedicado** y no necesita red ni un sistema de archivos raíz con permisos de escritura:

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
En ese espacio de nombres dedicado se puede demostrar una política de denegación aplicada; añade permisos explícitos para DNS y la aplicación antes de usarla con una carga de trabajo real:

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
**Registro y detección:** los registros del plano de control en CloudWatch tienen cinco tipos configurables:

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
Espera a que la actualización devuelta finalice correctamente y verifica la entrega real de registros y su retención. Esto no recopila los registros de aplicación de todos los contenedores. La protección de registros de auditoría de EKS de GuardDuty y la supervisión en tiempo de ejecución son capacidades distintas, con configuración/cobertura independientes; habilitar solo los registros del plano de control no equivale a detectar amenazas en tiempo de ejecución.

</details>


## Referencias

* [Modo de prefijos de EKS](https://docs.aws.amazon.com/eks/latest/best-practices/prefix-mode-linux.html)
* [maxPods y procedimiento de prefijos de EKS](https://docs.aws.amazon.com/eks/latest/userguide/cni-increase-ip-addresses-procedure.html)
* [Política de red de EKS](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html)
* [Gateways NAT](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-nat-gateway.html)
* [Asociación de tablas de rutas de subred](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-ec2-subnetroutetableassociation.html)
* [Grupos de seguridad para Pods](https://docs.aws.amazon.com/eks/latest/userguide/security-groups-for-pods.html)
* [Complemento administrado de CoreDNS](https://docs.aws.amazon.com/eks/latest/userguide/managing-coredns.html)
* [Caché de CoreDNS](https://coredns.io/plugins/cache/)
* [Recarga de CoreDNS](https://coredns.io/plugins/reload/)
* [Multi-tenencia de Kubernetes](https://kubernetes.io/docs/concepts/security/multi-tenancy/)
* [PDB de Kubernetes](https://kubernetes.io/docs/tasks/run-application/configure-pdb/)
* [Cluster Autoscaler de EKS](https://docs.aws.amazon.com/eks/latest/best-practices/cas.html)
* [Actualizaciones de nodos administrados de EKS](https://docs.aws.amazon.com/eks/latest/userguide/managed-node-update-behavior.html)
* [Calico en EKS](https://docs.tigera.io/calico/latest/getting-started/kubernetes/managed-public-cloud/eks)
* [NetworkPolicy de Calico](https://docs.tigera.io/calico/latest/reference/resources/networkpolicy)
* [IRSA](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
* [Rol IAM de nodo de EKS](https://docs.aws.amazon.com/eks/latest/userguide/create-node-role.html)
