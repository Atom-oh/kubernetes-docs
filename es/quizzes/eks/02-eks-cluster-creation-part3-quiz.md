# EKS Cluster Creation Quiz - Part 3

Este quiz evalúa tu comprensión de redes avanzadas, configuración de almacenamiento y multi-tenancy relacionados con la creación de clusters de Amazon EKS. Cubre temas como redes del cluster, opciones de almacenamiento y configuración de entornos multi-tenant.

## Basic Concept Questions

1. ¿Cuál es el factor principal que limita la cantidad de direcciones IP por pod en un cluster de Amazon EKS?
   * A) Tamaño del bloque CIDR de la VPC
   * B) Tipo de instancia del nodo
   * C) Versión de Kubernetes del cluster
   * D) Cantidad de direcciones IP disponibles en la subnet

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Tipo de instancia del nodo**

**Explicación:** El factor principal que limita la cantidad de direcciones IP por pod en un cluster de Amazon EKS es el tipo de instancia del nodo. El plugin Amazon VPC CNI usa las Elastic Network Interfaces (ENIs) y las direcciones IP secundarias de cada nodo para asignar direcciones IP a los pods. Cada tipo de instancia EC2 admite una cantidad máxima diferente de ENIs y de direcciones IP máximas por ENI, lo que determina la cantidad máxima de pods que pueden ejecutarse en un nodo.

**Cálculo del recuento máximo de pods por tipo de instancia:**

La cantidad máxima de pods se calcula con la siguiente fórmula:

```
(Number of ENIs × IP addresses per ENI - 1) + 2
```

Donde:

* Se resta 1 porque la dirección IP primaria de la ENI primaria la usa el propio nodo.
* Se suma 2 porque los pods kube-proxy y aws-node usan redes del host.

**Recuento máximo de pods para tipos de instancia comunes:**

| Instance Type | Max ENIs | IPs per ENI | Max Pods |
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

**Cómo comprobar el recuento máximo de pods:**

```bash
# Check maximum pod count for a node
kubectl get nodes -o jsonpath='{.items[*].status.capacity.pods}'

# Or use the max-pods script
curl -s https://raw.githubusercontent.com/awslabs/amazon-eks-ami/master/scripts/max-pods-calculator.sh | bash -s -- --instance-type m5.large
```

**Factores que limitan el recuento máximo de pods:**

1. **Tipo de instancia**:
   * Cada tipo de instancia admite una cantidad máxima diferente de ENIs y direcciones IP por ENI.
   * Los tipos de instancia más grandes generalmente admiten más ENIs y direcciones IP.
2. **Configuración de CNI**:
   * La configuración predeterminada de VPC CNI usa direcciones IP secundarias en lugar de asignar una ENI completa a cada pod.
   * Este comportamiento puede cambiarse usando redes personalizadas.
3.  **Delegación de prefijos**:

    * VPC CNI 1.9.0 y versiones posteriores admiten delegación de prefijos, que asigna un bloque CIDR /28 (16 IPs) a cada ENI.
    * Esto puede aumentar significativamente la cantidad máxima de pods por nodo.

    ```bash
    kubectl set env daemonset aws-node -n kube-system ENABLE_PREFIX_DELEGATION=true
    ```
4.  **Valor personalizado de max-pods**:

    * Puedes usar el flag `--max-pods` de kubelet para limitar la cantidad máxima de pods por nodo.
    * Esto puede establecerse en un valor menor que el admitido por el tipo de instancia.

    ```bash
    eksctl create nodegroup \
      --cluster my-cluster \
      --name my-nodegroup \
      --node-type m5.large \
      --nodes 3 \
      --kubelet-extra-args "--max-pods=110"
    ```

**Problemas con otras opciones:**

* **Tamaño del bloque CIDR de la VPC**: El tamaño del bloque CIDR de la VPC limita la cantidad total de direcciones IP disponibles en la VPC, pero no limita directamente la cantidad máxima de pods por nodo individual.
* **Versión de Kubernetes del cluster**: La versión de Kubernetes afecta las características admitidas, pero no limita directamente la cantidad máxima de pods por nodo.
* **Cantidad de direcciones IP disponibles en la subnet**: La cantidad de direcciones IP disponibles en una subnet afecta la cantidad total de pods que pueden desplegarse en esa subnet, pero no limita directamente la cantidad máxima de pods por nodo individual.

El tipo de instancia del nodo es el factor principal que determina la cantidad máxima de pods que pueden ejecutarse en un nodo mediante la cantidad de ENIs y direcciones IP por ENI que admite. Por lo tanto, es importante seleccionar un tipo de instancia adecuado que cumpla con los requisitos de tu workload.

</details>

2\. ¿Cuál es la política de red predeterminada para la comunicación pod-a-pod en un cluster de Amazon EKS? - A) Permitir toda la comunicación pod-a-pod - B) Permitir comunicación solo entre pods en el mismo namespace - C) Permitir solo la comunicación pod-a-pod explícitamente autorizada - D) Bloquear toda la comunicación pod-a-pod

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: A) Permitir toda la comunicación pod-a-pod**

**Explicación:** La política de red predeterminada para la comunicación pod-a-pod en un cluster de Amazon EKS es permitir toda la comunicación pod-a-pod. De forma predeterminada, EKS no implementa políticas de red, y todos los pods pueden comunicarse libremente con todos los demás pods del cluster. Este es el comportamiento predeterminado de Kubernetes, y debes configurar explícitamente políticas de red para restringir la comunicación pod-a-pod.

**Comportamiento de red predeterminado en EKS:**

1. **Política de permitir por defecto**:
   * De forma predeterminada, todos los pods pueden comunicarse con todos los demás pods del cluster.
   * La comunicación entre namespaces también se permite sin restricciones.
   * Esto sigue el modelo de "red plana" de Kubernetes.
2. **Amazon VPC CNI**:
   * El plugin CNI predeterminado para EKS es Amazon VPC CNI.
   * Este plugin asigna direcciones IP de la VPC a los pods, lo que los hace directamente enrutables dentro de la VPC.
   * No implementa políticas de red de forma predeterminada.

**Cómo implementar políticas de red:**

Para restringir la comunicación pod-a-pod en EKS, debes implementar una de las siguientes soluciones de políticas de red:

1.  **Calico**:

    ```bash
    # Install Calico
    kubectl create namespace tigera-operator
    helm repo add projectcalico https://docs.projectcalico.org/charts
    helm install calico projectcalico/tigera-operator --namespace tigera-operator
    ```
2.  **Cilium**:

    ```bash
    # Install Cilium
    helm repo add cilium https://helm.cilium.io/
    helm install cilium cilium/cilium --namespace kube-system
    ```
3. **AWS Network Firewall** (nivel de VPC):
   * Puedes usar AWS Network Firewall para filtrar tráfico a nivel de VPC.
   * Esto proporciona control a nivel de subnet en lugar de control granular a nivel de pod.

**Ejemplos de políticas de red:**

1.  **Política de denegación predeterminada**:

    ```yaml
    # Block all ingress traffic
    apiVersion: networking.k8s.io/v1
    kind: NetworkPolicy
    metadata:
      name: default-deny-ingress
      namespace: default
    spec:
      podSelector: {}
      policyTypes:
      - Ingress
    ```
2.  **Permitir comunicación entre pods específicos**:

    ```yaml
    # Allow communication only from frontend to backend
    apiVersion: networking.k8s.io/v1
    kind: NetworkPolicy
    metadata:
      name: allow-frontend-to-backend
      namespace: default
    spec:
      podSelector:
        matchLabels:
          app: backend
      ingress:
      - from:
        - podSelector:
            matchLabels:
              app: frontend
        ports:
        - protocol: TCP
          port: 8080
    ```
3.  **Restringir la comunicación entre namespaces**:

    ```yaml
    # Allow access only from prod namespace
    apiVersion: networking.k8s.io/v1
    kind: NetworkPolicy
    metadata:
      name: allow-from-prod-namespace
      namespace: default
    spec:
      podSelector:
        matchLabels:
          app: database
      ingress:
      - from:
        - namespaceSelector:
            matchLabels:
              name: prod
        ports:
        - protocol: TCP
          port: 5432
    ```

**Mejores prácticas de políticas de red:**

1. **Aplicar política de denegación predeterminada**:
   * Aplica una política de denegación predeterminada a todos los namespaces para bloquear todo el tráfico que no esté explícitamente permitido.
   * Permite explícitamente solo la comunicación necesaria.
2. **Aplicar el principio de privilegio mínimo**:
   * Permite solo el acceso de red mínimo que los pods requieren.
   * Permite solo puertos y protocolos específicos.
3. **Aislamiento de namespaces**:
   * Usa namespaces para separar lógicamente los workloads.
   * Controla explícitamente la comunicación entre namespaces.
4. **Políticas basadas en labels**:
   * Usa labels de pods para definir políticas de red granulares.
   * Mantén un esquema de labels consistente.

**Problemas con otras opciones:**

* **Permitir comunicación solo entre pods en el mismo namespace**: De forma predeterminada, EKS permite toda la comunicación pod-a-pod, incluida la comunicación entre namespaces.
* **Permitir solo la comunicación pod-a-pod explícitamente autorizada**: Este es el comportamiento después de implementar políticas de red, pero no es el comportamiento predeterminado.
* **Bloquear toda la comunicación pod-a-pod**: De forma predeterminada, EKS no bloquea la comunicación pod-a-pod.

La política de red predeterminada en EKS es permitir toda la comunicación pod-a-pod. Aunque esto puede ser conveniente en entornos de desarrollo y prueba, es importante implementar políticas de red adecuadas para mejorar la seguridad en entornos de producción.

</details>

3. ¿Qué se requiere para que los pods en un cluster de Amazon EKS accedan a internet fuera de la VPC?
   * A) Adjuntar un internet gateway a la subnet donde se encuentra el pod
   * B) Adjuntar un NAT gateway o una NAT instance a la subnet donde se encuentra el pod
   * C) Asignar una dirección IP pública al pod
   * D) Asociar una dirección Elastic IP con el pod

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Adjuntar un NAT gateway o una NAT instance a la subnet donde se encuentra el pod**

**Explicación:** Para que los pods en un cluster de Amazon EKS accedan a internet fuera de la VPC, la subnet donde se encuentra el pod debe tener un NAT gateway o una NAT instance adjunta. Este es el método estándar para permitir que los pods en subnets privadas accedan a internet.

**Arquitectura de redes de EKS:**

1. **Pods en subnets privadas**:
   * Los worker nodes de EKS normalmente se colocan en subnets privadas por seguridad.
   * Los pods en subnets privadas no pueden acceder directamente a internet.
   * Deben acceder a internet a través de un NAT gateway o una NAT instance.
2. **Pods en subnets públicas**:
   * Incluso si los worker nodes están en subnets públicas, los pods no reciben direcciones IP públicas de forma predeterminada.
   * Los pods acceden a internet mediante NAT a través de la interfaz de red del nodo.

**Configuración de NAT Gateway:**

```bash
# Create NAT gateway
aws ec2 create-nat-gateway \
  --subnet-id subnet-public1 \
  --allocation-id eipalloc-12345

# Update private subnet routing table
aws ec2 create-route \
  --route-table-id rtb-private \
  --destination-cidr-block 0.0.0.0/0 \
  --nat-gateway-id nat-12345
```

**Ejemplo de configuración de VPC usando CloudFormation:**

```yaml
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
      MapPublicIpOnLaunch: true
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
```

**Configuración de VPC usando eksctl:**

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
vpc:
  cidr: 192.168.0.0/16
  nat:
    gateway: Single  # NAT gateway configuration
  clusterEndpoints:
    publicAccess: true
    privateAccess: true
```

**Problemas con otras opciones:**

* **Adjuntar un internet gateway a la subnet donde se encuentra el pod**: Un internet gateway se adjunta a subnets públicas, y los recursos en subnets privadas necesitan un NAT gateway para acceder a internet. Además, un internet gateway por sí solo no permite que los pods accedan a internet.
* **Asignar una dirección IP pública al pod**: El plugin Amazon VPC CNI no admite asignar direcciones IP públicas a pods. Los pods siempre reciben direcciones IP privadas.
* **Asociar una dirección Elastic IP con el pod**: No puedes asociar directamente una dirección Elastic IP con un pod. Las direcciones Elastic IP solo pueden asociarse con instancias EC2 o interfaces de red.

Un NAT gateway o una NAT instance es el método estándar para permitir que los pods en subnets privadas accedan a internet. Traduce la dirección IP privada del pod a la dirección IP pública del NAT gateway para habilitar la comunicación con internet. Para entornos de producción, se recomienda desplegar un NAT gateway en cada Availability Zone para alta disponibilidad.

</details>

4. ¿Cuál de los siguientes NO es un requisito para aplicar security groups a pods usando SecurityGroupPolicy en un cluster de Amazon EKS?
   * A) Plugin Amazon VPC CNI versión 1.7.7 o posterior
   * B) Configuración del recurso ENIConfig
   * C) Configurar hostNetwork: true en el pod
   * D) Especificar una service account para los pods a los que se aplicarán security groups

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Configurar hostNetwork: true en el pod**

**Explicación:** "Configurar hostNetwork: true en el pod" NO es un requisito para aplicar security groups a pods usando SecurityGroupPolicy en un cluster de Amazon EKS. De hecho, no se pueden aplicar security groups a pods con hostNetwork: true. Para aplicar security groups a pods, los pods deben usar su propio namespace de red.

**Requisitos de la característica Pod Security Group:**

1.  **Plugin Amazon VPC CNI versión 1.7.7 o posterior**:

    * La característica pod security group es compatible con el plugin Amazon VPC CNI versión 1.7.7 y posteriores.
    * Se recomienda usar la versión más reciente.

    ```bash
    # Check CNI version
    kubectl describe daemonset aws-node -n kube-system | grep Image

    # Update CNI
    kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.10.0/config/master/aws-k8s-cni.yaml
    ```
2.  **Habilitar la característica Pod Security Group**:

    ```bash
    # Enable pod security group feature
    kubectl set env daemonset aws-node -n kube-system ENABLE_POD_ENI=true

    # Or use eksctl
    eksctl utils update-cluster-config \
      --name my-cluster \
      --region us-west-2 \
      --enable-pod-security-groups
    ```
3.  **Especificar una Service Account para los pods a los que se aplicarán security groups**:

    * En SecurityGroupPolicy, debes especificar los pods a los que se aplicarán security groups usando un pod selector o un service account selector.

    ```yaml
    apiVersion: vpcresources.k8s.aws/v1beta1
    kind: SecurityGroupPolicy
    metadata:
      name: my-security-group-policy
      namespace: default
    spec:
      podSelector:
        matchLabels:
          app: my-app
      securityGroups:
        groupIds:
          - sg-12345
    ```

**Ejemplos de configuración de Pod Security Group:**

1.  **Crear SecurityGroupPolicy**:

    ```yaml
    apiVersion: vpcresources.k8s.aws/v1beta1
    kind: SecurityGroupPolicy
    metadata:
      name: db-client-policy
      namespace: default
    spec:
      serviceAccountSelector:
        matchLabels:
          role: db-client
      securityGroups:
        groupIds:
          - sg-db-client
    ```
2.  **Crear Service Account**:

    ```yaml
    apiVersion: v1
    kind: ServiceAccount
    metadata:
      name: db-client
      namespace: default
      labels:
        role: db-client
    ```
3.  **Desplegar Pod**:

    ```yaml
    apiVersion: v1
    kind: Pod
    metadata:
      name: db-client-pod
    spec:
      serviceAccountName: db-client
      containers:
      - name: db-client
        image: mysql:5.7
        command: ['sleep', '3600']
    ```

**Problemas con hostNetwork: true:**

Los pods con `hostNetwork: true` usan el namespace de red del nodo, por lo que no se pueden aplicar security groups separados al pod. Estos pods heredan los security groups del nodo.

```yaml
# Security groups cannot be applied to this pod
apiVersion: v1
kind: Pod
metadata:
  name: host-network-pod
spec:
  hostNetwork: true  # Uses the node's network namespace
  containers:
  - name: nginx
    image: nginx
```

**Configuración del recurso ENIConfig:**

Los recursos ENIConfig son necesarios al configurar redes personalizadas, pero no son un requisito obligatorio cuando se usa únicamente la característica pod security groups. Sin embargo, si usas pod security groups junto con redes personalizadas, debes configurar recursos ENIConfig.

```yaml
apiVersion: crd.k8s.amazonaws.com/v1alpha1
kind: ENIConfig
metadata:
  name: us-west-2a
spec:
  subnet: subnet-12345
  securityGroups:
  - sg-12345
```

**Limitaciones de Pod Security Group:**

1. **Limitaciones de recursos**:
   * Cada nodo requiere ENIs adicionales para pod security groups.
   * La cantidad máxima de ENIs admitidas está limitada por el tipo de instancia.
2. **Limitaciones de compatibilidad**:
   * No se puede aplicar a pods con hostNetwork: true.
   * No se puede aplicar a pods que usan hostPort.
   * Puede no ser compatible con algunos plugins CNI.
3. **Impacto en el rendimiento**:
   * Como se requieren ENIs adicionales por pod, el tiempo de inicio del pod puede ser mayor.
   * La cantidad máxima de pods por nodo puede verse limitada.

La característica pod security groups es una capacidad potente que proporciona seguridad de red granular a nivel de pod. Sin embargo, como esta característica no puede aplicarse a pods con hostNetwork: true, los pods deben usar su propio namespace de red para usar pod security groups.

</details>

4\. ¿Qué NO es un requisito para aplicar security groups a pods usando SecurityGroupPolicy en un cluster de Amazon EKS? - A) Plugin Amazon VPC CNI versión 1.7.7 o superior - B) Configuración del recurso ENIConfig - C) Configurar hostNetwork: true en el pod - D) Especificar una service account para los pods a los que se aplicarán security groups

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Configurar hostNetwork: true en el pod**

**Explicación:** La opción que NO es un requisito para aplicar security groups a pods usando SecurityGroupPolicy en un cluster de Amazon EKS es "Configurar hostNetwork: true en el pod". De hecho, no se pueden aplicar security groups a pods con hostNetwork: true. Para aplicar security groups a pods, los pods deben usar su propio namespace de red.

**Requisitos de la característica Pod Security Groups:**

1.  **Plugin Amazon VPC CNI versión 1.7.7 o superior**:

    * La característica pod security groups es compatible con el plugin Amazon VPC CNI versión 1.7.7 y posteriores.
    * Se recomienda usar la versión más reciente.

    ```bash
    # Check CNI version
    kubectl describe daemonset aws-node -n kube-system | grep Image

    # Update CNI
    kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.10.0/config/master/aws-k8s-cni.yaml
    ```
2.  **Habilitar la característica pod security groups**:

    ```bash
    # Enable pod security groups feature
    kubectl set env daemonset aws-node -n kube-system ENABLE_POD_ENI=true

    # Or use eksctl
    eksctl utils update-cluster-config \
      --name my-cluster \
      --region us-west-2 \
      --enable-pod-security-groups
    ```
3.  **Especificar service account para los pods a los que se aplicarán security groups**:

    * En SecurityGroupPolicy, debes especificar los pods a los que se aplicarán security groups usando pod selector o service account selector.

    ```yaml
    apiVersion: vpcresources.k8s.aws/v1beta1
    kind: SecurityGroupPolicy
    metadata:
      name: my-security-group-policy
      namespace: default
    spec:
      podSelector:
        matchLabels:
          app: my-app
      securityGroups:
        groupIds:
          - sg-12345
    ```

**Ejemplos de configuración de Pod Security Group:**

1.  **Crear SecurityGroupPolicy**:

    ```yaml
    apiVersion: vpcresources.k8s.aws/v1beta1
    kind: SecurityGroupPolicy
    metadata:
      name: db-client-policy
      namespace: default
    spec:
      serviceAccountSelector:
        matchLabels:
          role: db-client
      securityGroups:
        groupIds:
          - sg-db-client
    ```
2.  **Crear Service Account**:

    ```yaml
    apiVersion: v1
    kind: ServiceAccount
    metadata:
      name: db-client
      namespace: default
      labels:
        role: db-client
    ```
3.  **Desplegar Pod**:

    ```yaml
    apiVersion: v1
    kind: Pod
    metadata:
      name: db-client-pod
    spec:
      serviceAccountName: db-client
      containers:
      - name: db-client
        image: mysql:5.7
        command: ['sleep', '3600']
    ```

**Problemas con hostNetwork: true:**

Los pods con `hostNetwork: true` usan el namespace de red del nodo, por lo que no se pueden aplicar security groups separados al pod. Estos pods heredan los security groups del nodo.

```yaml
# Security groups cannot be applied to this pod
apiVersion: v1
kind: Pod
metadata:
  name: host-network-pod
spec:
  hostNetwork: true  # Uses the node's network namespace
  containers:
  - name: nginx
    image: nginx
```

**Configuración del recurso ENIConfig:**

Los recursos ENIConfig son necesarios al configurar redes personalizadas, pero no son un requisito obligatorio cuando se usa únicamente la característica pod security groups. Sin embargo, si usas pod security groups junto con redes personalizadas, debes configurar recursos ENIConfig.

```yaml
apiVersion: crd.k8s.amazonaws.com/v1alpha1
kind: ENIConfig
metadata:
  name: us-west-2a
spec:
  subnet: subnet-12345
  securityGroups:
  - sg-12345
```

**Limitaciones de Pod Security Group:**

1. **Limitaciones de recursos**:
   * Cada nodo requiere ENIs adicionales para pod security groups.
   * La cantidad máxima de ENIs admitidas está limitada por el tipo de instancia.
2. **Limitaciones de compatibilidad**:
   * No se puede aplicar a pods con hostNetwork: true.
   * No se puede aplicar a pods que usan hostPort.
   * Puede no ser compatible con algunos plugins CNI.
3. **Impacto en el rendimiento**:
   * Como se requieren ENIs adicionales por pod, el tiempo de inicio del pod puede ser mayor.
   * La cantidad máxima de pods por nodo puede verse limitada.

La característica pod security groups es una capacidad potente que proporciona seguridad de red granular a nivel de pod. Sin embargo, como esta característica no puede aplicarse a pods con hostNetwork: true, los pods deben usar su propio namespace de red para usar pod security groups.

</details>

5. ¿Cuál es el beneficio principal de la característica Prefix Delegation en un cluster de Amazon EKS?
   * A) Mayor velocidad de comunicación entre pods
   * B) Mayor cantidad máxima de pods por nodo
   * C) Capacidad de asignar direcciones IP públicas a pods
   * D) Mejor aislamiento de red de pods

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Mayor cantidad máxima de pods por nodo**

**Explicación:** El beneficio principal de la característica Prefix Delegation en un cluster de Amazon EKS es aumentar la cantidad máxima de pods por nodo. Esta característica asigna bloques CIDR /28 (16 direcciones IP) en lugar de direcciones IP individuales a cada Elastic Network Interface (ENI), lo que aumenta significativamente la cantidad máxima de pods que un nodo puede admitir.

**Cómo funciona Prefix Delegation:**

1. **Comportamiento predeterminado de VPC CNI**:
   * De forma predeterminada, VPC CNI asigna direcciones IP secundarias desde la ENI para cada pod.
   * Cada tipo de instancia EC2 tiene límites en la cantidad máxima de ENIs y direcciones IP por ENI.
   * Esto limita la cantidad máxima de pods por nodo.
2. **Comportamiento de Prefix Delegation**:
   * Cuando prefix delegation está habilitada, se asignan bloques CIDR /28 (16 IPs) a cada ENI en lugar de direcciones IP individuales.
   * Esto aumenta significativamente la cantidad de direcciones IP que cada ENI puede admitir.
   * Como resultado, aumenta la cantidad máxima de pods por nodo.

**Habilitar Prefix Delegation:**

```bash
# Enable prefix delegation
kubectl set env daemonset aws-node -n kube-system ENABLE_PREFIX_DELEGATION=true

# Check prefix delegation status
kubectl describe daemonset aws-node -n kube-system | grep ENABLE_PREFIX_DELEGATION
```

**Beneficios de Prefix Delegation:**

1. **Mayor cantidad máxima de pods por nodo**:
   * Usar prefix delegation aumenta significativamente la cantidad máxima de pods por nodo.
   * Por ejemplo, para una instancia m5.large:
     * Configuración predeterminada: máximo 29 pods
     * Con prefix delegation habilitada: más de 110 pods como máximo
2. **Eficiencia de direcciones IP**:
   * Optimiza el uso de direcciones IP en clusters grandes.
   * Útil en entornos con rangos CIDR de VPC limitados.
3. **Mejor utilización de recursos del nodo**:
   * Ejecutar más pods mejora la utilización de recursos del nodo.
   * Ayuda con la optimización de costos del cluster.

**Limitaciones de Prefix Delegation:**

1. **Compatibilidad de instancias EC2**:
   * Solo las instancias basadas en Nitro admiten prefix delegation.
   * No puede usarse con instancias de generaciones anteriores.
2. **Requisitos de versión de VPC CNI**:
   * Se requiere VPC CNI versión 1.9.0 o superior.
   * Esta característica no puede usarse con versiones anteriores.
3. **Requisitos de tamaño de subnet**:
   * Se requieren subnets con suficiente espacio de direcciones IP.
   * Las direcciones IP pueden agotarse rápidamente en subnets pequeñas.
4. **Consideraciones de migración**:
   * Cuando se habilita en clusters existentes, solo los pods nuevos usan prefix delegation.
   * Los pods existentes deben reiniciarse para aplicarla a todos los pods.

**Ejemplo de configuración de Prefix Delegation:**

```yaml
# eksctl configuration file
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
vpc:
  clusterEndpoints:
    publicAccess: true
    privateAccess: true
managedNodeGroups:
  - name: ng-1
    instanceType: m5.large
    minSize: 2
    maxSize: 5
    disableIMDSv1: true
iam:
  withOIDC: true
addons:
  - name: vpc-cni
    version: latest
    configurationValues: |
      {
        "env": {
          "ENABLE_PREFIX_DELEGATION": "true"
        }
      }
```

**Problemas con otras opciones:**

* **Mayor velocidad de comunicación entre pods**: Prefix delegation no afecta directamente la velocidad de comunicación pod-a-pod. El rendimiento de comunicación de pods está determinado principalmente por la infraestructura de red y la implementación de CNI.
* **Capacidad de asignar direcciones IP públicas a pods**: Prefix delegation no proporciona la capacidad de asignar direcciones IP públicas a pods. VPC CNI siempre asigna direcciones IP privadas a los pods.
* **Mejor aislamiento de red de pods**: Prefix delegation no está relacionada con el aislamiento de red de pods. El aislamiento de red se implementa mediante políticas de red o security groups.

Prefix delegation es una característica potente que aumenta la cantidad máxima de pods por nodo, mejorando la densidad y eficiencia del cluster. Es especialmente útil en clusters grandes o entornos que ejecutan workloads de alta densidad.

</details>

6. ¿Cuál es la forma correcta de personalizar CoreDNS en un cluster de Amazon EKS?
   * A) Modificar la configuración de CoreDNS en la AWS Management Console
   * B) Modificar el ConfigMap de CoreDNS
   * C) Especificar la configuración de CoreDNS durante la creación del cluster EKS
   * D) Actualizar los parámetros del add-on de CoreDNS usando la AWS CLI

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Modificar el ConfigMap de CoreDNS**

**Explicación:** La forma correcta de personalizar CoreDNS en un cluster de Amazon EKS es modificar el ConfigMap de CoreDNS. CoreDNS es el servidor DNS del cluster para Kubernetes y se configura mediante un ConfigMap. En EKS, puedes personalizar el comportamiento de CoreDNS modificando el ConfigMap `coredns`.

**Cómo modificar el ConfigMap de CoreDNS:**

1.  **Comprobar el ConfigMap actual**:

    ```bash
    kubectl get configmap coredns -n kube-system -o yaml
    ```
2.  **Editar ConfigMap**:

    ```bash
    kubectl edit configmap coredns -n kube-system
    ```
3.  **O aplicar un patch**:

    ```bash
    kubectl patch configmap coredns -n kube-system --type=merge -p '{"data":{"Corefile":".:53 {\n    errors\n    health {\n        lameduck 5s\n    }\n    ready\n    kubernetes cluster.local in-addr.arpa ip6.arpa {\n        pods insecure\n        fallthrough in-addr.arpa ip6.arpa\n        ttl 30\n    }\n    prometheus :9153\n    forward . /etc/resolv.conf\n    cache 30\n    loop\n    reload\n    loadbalance\n    # Add custom settings\n    hosts {\n        10.0.0.1 example.com\n        fallthrough\n    }\n}"}}'
    ```

**Casos comunes de personalización de CoreDNS:**

1.  **Agregar registros DNS personalizados**:

    ```
    hosts {
        10.0.0.1 example.com
        10.0.0.2 api.example.com
        fallthrough
    }
    ```
2.  **Configurar forwarding para dominios específicos**:

    ```
    forward example.org 10.0.0.1:53
    ```
3.  **Ajustar la caché DNS**:

    ```
    cache {
        success 10000
        denial 5000
        prefetch 10 10 10%
    }
    ```
4.  **Configurar logging**:

    ```
    log {
        class error
    }
    ```
5.  **Deshabilitar Autopath**:

    ```
    kubernetes cluster.local in-addr.arpa ip6.arpa {
        pods insecure
        fallthrough in-addr.arpa ip6.arpa
        ttl 30
        autopath off
    }
    ```

**Aplicar cambios después de modificar CoreDNS:**

Después de modificar el ConfigMap, debes reiniciar los pods de CoreDNS para aplicar los cambios:

```bash
# Check CoreDNS pods
kubectl get pods -n kube-system -l k8s-app=kube-dns

# Restart CoreDNS pods
kubectl rollout restart deployment coredns -n kube-system

# Verify changes are applied
kubectl logs -n kube-system -l k8s-app=kube-dns
```

**Optimización de rendimiento de CoreDNS:**

1.  **Configurar auto-scaling**:

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
2.  **Ajustar Resource Requests y Limits**:

    ```bash
    kubectl patch deployment coredns -n kube-system --type=json -p='[{"op": "replace", "path": "/spec/template/spec/containers/0/resources", "value": {"requests": {"cpu": "100m", "memory": "70Mi"}, "limits": {"cpu": "200m", "memory": "170Mi"}}}]'
    ```

**Problemas con otras opciones:**

* **Modificar la configuración de CoreDNS en la AWS Management Console**: La AWS Management Console no proporciona una interfaz para modificar directamente la configuración de CoreDNS.
* **Especificar la configuración de CoreDNS durante la creación del cluster EKS**: La configuración detallada de CoreDNS no puede especificarse durante la creación del cluster EKS. Debes modificar el ConfigMap después de crear el cluster.
* **Actualizar los parámetros del add-on de CoreDNS usando la AWS CLI**: Aunque puedes actualizar la versión del add-on de CoreDNS usando la AWS CLI, no puedes modificar la configuración detallada. Los cambios de configuración deben realizarse mediante el ConfigMap.

```bash
# Update CoreDNS add-on version (not configuration change)
aws eks update-addon \
  --cluster-name my-cluster \
  --addon-name coredns \
  --addon-version v1.8.7-eksbuild.2 \
  --resolve-conflicts PRESERVE
```

Modificar el ConfigMap de CoreDNS es el método estándar para personalizar la configuración DNS en un cluster EKS. Esto habilita varias personalizaciones, como agregar registros DNS personalizados, configurar forwarding para dominios específicos y ajustar el comportamiento de caché.

</details>

7\. ¿Cuál es la forma más efectiva de implementar multi-tenancy en un cluster de Amazon EKS? - A) Crear clusters EKS separados para cada tenant - B) Usar namespaces separados para cada tenant y aplicar RBAC, políticas de red y cuotas de recursos - C) Crear node groups separados para cada tenant y usar node selectors - D) Usar VPCs separadas para cada tenant

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Usar namespaces separados para cada tenant y aplicar RBAC, políticas de red y cuotas de recursos**

**Explicación:** La forma más efectiva de implementar multi-tenancy en un cluster de Amazon EKS es usar namespaces separados para cada tenant y aplicar RBAC (Role-Based Access Control), políticas de red y cuotas de recursos. Este enfoque aísla eficientemente varios tenants dentro de un único cluster mientras permite compartir recursos.

**Implementar multi-tenancy basado en namespaces:**

1.  **Crear namespaces para cada tenant**:

    ```bash
    # Create namespaces for each tenant
    kubectl create namespace tenant-a
    kubectl create namespace tenant-b
    ```
2.  **Configurar RBAC**:

    ```yaml
    # Create tenant role
    apiVersion: rbac.authorization.k8s.io/v1
    kind: Role
    metadata:
      name: tenant-full-access
      namespace: tenant-a
    rules:
    - apiGroups: ["", "apps", "batch"]
      resources: ["*"]
      verbs: ["*"]
    ---
    # Bind role to tenant users
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
      name: tenant-full-access
      apiGroup: rbac.authorization.k8s.io
    ```
3.  **Aplicar políticas de red**:

    ```yaml
    # Restrict communication between tenants
    apiVersion: networking.k8s.io/v1
    kind: NetworkPolicy
    ```

metadata: name: deny-cross-tenant-traffic namespace: tenant-a spec: podSelector: {} policyTypes: - Ingress - Egress ingress: - from: - namespaceSelector: matchLabels: name: tenant-a egress: - to: - namespaceSelector: matchLabels: name: tenant-a - to: - namespaceSelector: matchLabels: name: kube-system

````

4. **Configuración de Resource Quota**:
 ```yaml
 # Tenant Resource Quota
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
````

5.  **Configuración de LimitRange**:

    ```yaml
    # Default resource limit settings
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

**Beneficios de la multi-tenancy basada en namespaces:**

1. **Eficiencia de recursos**:
   * La utilización de recursos mejora porque varios tenants comparten un único cluster.
   * Se reducen los costos del control plane.
2. **Facilidad de gestión**:
   * La sobrecarga operativa disminuye al gestionar un único cluster.
   * Es posible centralizar monitoreo y logging.
3. **Flexibilidad**:
   * Agregar y eliminar tenants es sencillo.
   * Las políticas específicas de cada tenant pueden aplicarse fácilmente.
4. **Eficiencia de costos**:
   * La sobrecarga del cluster se comparte entre varios tenants.
   * Una mejor utilización de recursos genera ahorros de costos.

**Desventajas de la multi-tenancy basada en namespaces:**

1. **Nivel de aislamiento limitado**:
   * Los namespaces proporcionan solo aislamiento lógico, no aislamiento físico completo.
   * Puede estar expuesto a vulnerabilidades a nivel de kernel.
2. **Contención de recursos**:
   * Puede ocurrir contención de recursos entre tenants.
   * Pueden surgir problemas de Noisy Neighbor.
3. **Riesgos de seguridad**:
   * Existe riesgo de escalación de privilegios a nivel de cluster.
   * Puede estar expuesto a vulnerabilidades de escape de contenedores.

**Otros enfoques de multi-tenancy:**

1. **Multi-tenancy basada en clusters (cluster EKS separado por tenant)**:
   * Proporciona el aislamiento más fuerte
   * Mayor sobrecarga de gestión
   * Costos mayores
   * Adecuado para entornos empresariales grandes o industrias muy reguladas
2. **Multi-tenancy basada en nodos (node group separado por tenant)**:
   * Proporciona un nivel intermedio de aislamiento
   * Posible personalización a nivel de nodo por tenant
   * Menor utilización de recursos
   * Adecuado cuando los requisitos de seguridad son altos pero el costo también es una consideración
3. **Enfoque híbrido**:
   * Proporcionar clusters dedicados para tenants críticos
   * Separar tenants menos críticos por namespace en un cluster compartido
   * Equilibrar flexibilidad y eficiencia de costos

**Problemas con otras opciones:**

* **Crear un cluster EKS separado por tenant**: Proporciona el aislamiento más fuerte, pero aumenta significativamente la sobrecarga de gestión y los costos. Pueden surgir problemas de escalabilidad cuando hay muchos tenants.
* **Crear node groups separados por tenant y usar node selectors**: Proporciona aislamiento a nivel de nodo, pero la utilización de recursos disminuye y la gestión puede volverse compleja. Además, los node groups por sí solos no proporcionan aislamiento completo.
* **Usar VPCs separadas por tenant**: Como los clusters EKS se crean dentro de una única VPC, usar VPCs separadas por tenant requiere crear clusters separados por tenant. Esto aumenta significativamente la sobrecarga de gestión y los costos.

La multi-tenancy basada en namespaces proporciona el equilibrio óptimo entre aislamiento, facilidad de gestión y eficiencia de costos para la mayoría de los casos de uso. Sin embargo, la multi-tenancy basada en clusters debe considerarse cuando los requisitos de seguridad son muy altos.

</details>

8. ¿Cuál de los siguientes NO es un factor a considerar al seleccionar un tipo de instancia para un node group en un cluster de Amazon EKS?
   * A) Requisitos de CPU y memoria del workload
   * B) Optimización de costos
   * C) Versión de Kubernetes del cluster
   * D) Densidad de pods requerida

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Versión de Kubernetes del cluster**

**Explicación:** El factor que NO debe considerarse al seleccionar un tipo de instancia para un node group en un cluster de Amazon EKS es "versión de Kubernetes del cluster". Aunque la versión de Kubernetes afecta las características admitidas, no impacta directamente la selección del tipo de instancia del node group. El tipo de instancia se determina principalmente por los requisitos del workload, el costo, la densidad de pods y otros factores.

**Factores reales a considerar al seleccionar tipos de instancia de node group:**

1. **Requisitos de CPU y memoria del workload**:
   * Selecciona tipos de instancia que coincidan con los requisitos de recursos de tu workload
   * Workloads intensivos en CPU: instancias compute-optimized como c5, c6g
   * Workloads intensivos en memoria: instancias memory-optimized como r5, r6g
   * Workloads equilibrados: instancias general-purpose como m5, m6g
   * Workloads GPU: instancias accelerated computing como p3, g4dn
2. **Optimización de costos**:
   * Instancias On-Demand vs Spot
   * Reserved Instances o Savings Plans
   * Ahorros de costos mediante instancias Graviton basadas en ARM (por ejemplo, m6g, c6g)
   * Selección de instancias de tamaño adecuado (evitando sobreaprovisionamiento)
3. **Densidad de pods requerida**:
   * La cantidad máxima de pods admitida varía según el tipo de instancia
   * Considera la cantidad de ENIs por tipo de instancia y direcciones IP por ENI
   * Para workloads de alta densidad, selecciona tipos de instancia que admitan más ENIs y direcciones IP
4. **Requisitos de red**:
   * Requisitos de ancho de banda de red
   * Compatibilidad con redes mejoradas (ENA, EFA, etc.)
   * El rendimiento de red varía según el tipo de instancia
5. **Requisitos de almacenamiento**:
   * Si se necesita almacenamiento local de instancia (por ejemplo, instancias i3, d3)
   * Compatibilidad con optimización EBS
   * Requisitos de throughput de almacenamiento e IOPS
6. **Requisitos de disponibilidad**:
   * Disponibilidad regional de tipos de instancia
   * Posibilidad de interrupción al usar Spot instances
   * Disponibilidad de tipos de instancia por Availability Zone

**Ejemplos de selección de tipos de instancia:**

1.  **Servidores de aplicaciones web**:

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
    ```
2.  **Workloads de bases de datos**:

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
    ```
3.  **Workloads de procesamiento batch**:

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
    ```
4.  **Workloads optimizados para costos**:

    ```yaml
    apiVersion: eksctl.io/v1alpha5
    kind: ClusterConfig
    metadata:
      name: my-cluster
      region: us-west-2
    managedNodeGroups:
      - name: spot-workers
        instanceTypes: ["m5.large", "m5a.large", "m5d.large", "m5ad.large"]
        minSize: 2
        maxSize: 10
        spot: true
        labels:
          lifecycle: spot
    ```

**Relación entre la versión de Kubernetes y los tipos de instancia:**

La versión de Kubernetes afecta al cluster de las siguientes formas, pero no impacta directamente la selección del tipo de instancia:

1. **Características admitidas**:
   * Las nuevas versiones de Kubernetes proporcionan nuevas características.
   * Algunas características solo están disponibles en versiones específicas.
2. **Compatibilidad de API**:
   * Algunas APIs pueden cambiar o eliminarse en nuevas versiones.
   * La selección de versión es importante si tu aplicación depende de APIs específicas.
3. **Parches de seguridad**:
   * Las versiones más recientes incluyen los últimos parches de seguridad.
   * Las versiones antiguas pueden estar expuestas a vulnerabilidades de seguridad.
4. **Período de soporte**:
   * Cada versión de Kubernetes recibe soporte por un período limitado.
   * EKS admite cada versión durante aproximadamente 14 meses.

La selección del tipo de instancia se determina principalmente por los requisitos de recursos del workload, la optimización de costos, la densidad de pods y otros factores, y no está directamente relacionada con la versión de Kubernetes. Por lo tanto, "versión de Kubernetes del cluster" no es un factor principal a considerar al seleccionar el tipo de instancia de un node group.

</details>

9\. ¿Cuál es el método más efectivo para minimizar la interrupción de pods durante las actualizaciones de node groups en un cluster de Amazon EKS? - A) Usar una estrategia de rolling update - B) Configurar PodDisruptionBudget - C) Migrar manualmente todos los pods antes de la actualización del node group - D) Usar una estrategia de deployment blue/green

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Configurar PodDisruptionBudget**

**Explicación:** El método más efectivo para minimizar la interrupción de pods durante las actualizaciones de node groups en un cluster de Amazon EKS es configurar PodDisruptionBudget (PDB). PDB limita la cantidad de pods que pueden interrumpirse simultáneamente durante interrupciones voluntarias, asegurando la disponibilidad de la aplicación. Como las actualizaciones de node groups se consideran interrupciones voluntarias, puedes mantener la disponibilidad de la aplicación durante las actualizaciones mediante PDB.

**Cómo funciona PodDisruptionBudget:**

1. **Definición de PDB**:
   * `minAvailable`: Especifica la cantidad o porcentaje mínimo de pods que deben estar siempre disponibles
   * `maxUnavailable`: Especifica la cantidad o porcentaje máximo de pods que pueden estar no disponibles simultáneamente
   * Solo debe especificarse una de estas dos opciones
2. **Aplicación de PDB**:
   * Kubernetes respeta el PDB durante el draining de nodos
   * El proceso de draining se pausa si se infringe el PDB
   * El draining continúa cuando nuevos pods comienzan a ejecutarse en otros nodos

**Ejemplos de PodDisruptionBudget:**

```yaml
# Ensure at least 2 pods are always available
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: app-pdb
  namespace: default
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: my-app
```

```yaml
# Limit only up to 50% of pods to be unavailable simultaneously
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: app-pdb
  namespace: default
spec:
  maxUnavailable: 50%
  selector:
    matchLabels:
      app: my-app
```

**Proceso de actualización de node groups de EKS:**

1. **Inicio de actualización**:
   * Crear nodos nuevos
   * Los nodos nuevos se unen al cluster
2. **Draining de nodos**:
   * Aplicar cordoning a nodos existentes (evitar scheduling de pods nuevos)
   * Hacer drain de pods desde nodos existentes (migrar pods)
   * Migrar pods respetando PDB
3. **Terminación de nodos**:
   * Terminar nodos después de migrar todos los pods
   * Repetir el proceso para el siguiente nodo

**Mejores prácticas de configuración de PDB:**

1. **Establecer un recuento de réplicas adecuado**:
   * Se necesitan réplicas suficientes para que PDB funcione eficazmente
   * Se recomiendan al menos 3 réplicas
2. **Elegir valores de PDB adecuados**:
   * Selecciona valores apropiados para las características de la aplicación
   * Valores demasiado restrictivos pueden retrasar actualizaciones
   * Valores demasiado permisivos pueden afectar la disponibilidad
3. **Aplicar PDB a todos los workloads críticos**:
   * Aplicaciones stateful
   * Servicios orientados a usuarios
   * Componentes del sistema
4. **Probar PDB**:
   * Prueba el comportamiento de PDB antes de las actualizaciones
   * Verifica la disponibilidad con simulación de draining

**Configuración de actualización de node group:**

```bash
# Modify managed node group update configuration
aws eks update-nodegroup-config \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup \
  --update-config '{"maxUnavailable": 1}'

# Or using eksctl
eksctl update nodegroup \
  --cluster my-cluster \
  --name my-nodegroup \
  --max-unavailable 1
```

**Problemas con otras opciones:**

* **Usar una estrategia de rolling update**: Los node groups administrados de EKS ya usan una estrategia de rolling update de forma predeterminada. Sin embargo, las rolling updates por sí solas no pueden controlar la interrupción de pods, y deben usarse junto con PDB para ser efectivas.
* **Migrar manualmente todos los pods antes de la actualización del node group**: Este es un proceso manual que consume tiempo y es propenso a errores. Tampoco es práctico para clusters grandes.
* **Usar una estrategia de deployment blue/green**: El deployment blue/green implica crear un nuevo node group, migrar workloads y luego eliminar el node group existente. Es una estrategia efectiva, pero tiene desventajas de mayores costos debido a la duplicación de recursos e implementación compleja. También se usa mejor junto con PDB.

PodDisruptionBudget es una forma nativa de Kubernetes para controlar la interrupción de pods durante actualizaciones de node groups, lo que te permite actualizar node groups de forma segura mientras aseguras la disponibilidad de la aplicación. Por lo tanto, el método más efectivo para minimizar la interrupción de pods durante actualizaciones de node groups es configurar PodDisruptionBudget.

</details>

10. ¿Cuál de los siguientes NO se usa para controlar el comportamiento de Auto Scaling de node groups en un cluster de Amazon EKS?
    * A) Cluster Autoscaler
    * B) Karpenter
    * C) Horizontal Pod Autoscaler
    * D) Vertical Pod Autoscaler

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: D) Vertical Pod Autoscaler**

**Explicación:** El que NO se usa para controlar el comportamiento de Auto Scaling de node groups en un cluster de Amazon EKS es Vertical Pod Autoscaler (VPA). VPA se usa para ajustar automáticamente las solicitudes de CPU y memoria de los pods, pero no se usa para ajustar el tamaño de los node groups. El Auto Scaling de node groups se controla principalmente mediante Cluster Autoscaler, Karpenter e indirectamente mediante Horizontal Pod Autoscaler (HPA).

**Herramientas de Auto Scaling de node groups:**

1.  **Cluster Autoscaler**:

    * Un componente de Kubernetes que ajusta automáticamente el tamaño de los node groups
    * Agrega nodos cuando los pods no pueden programarse
    * Elimina nodos cuando no están suficientemente utilizados
    * Se integra con AWS Auto Scaling Groups

    ```yaml
    # Cluster Autoscaler Deployment
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: cluster-autoscaler
      namespace: kube-system
    spec:
      replicas: 1
      selector:
        matchLabels:
          app: cluster-autoscaler
      template:
        metadata:
          labels:
            app: cluster-autoscaler
        spec:
          serviceAccountName: cluster-autoscaler
          containers:
          - image: k8s.gcr.io/autoscaling/cluster-autoscaler:v1.23.0
            name: cluster-autoscaler
            command:
            - ./cluster-autoscaler
            - --v=4
            - --stderrthreshold=info
            - --cloud-provider=aws
            - --skip-nodes-with-local-storage=false
            - --expander=least-waste
            - --node-group-auto-discovery=asg:tag=k8s.io/cluster-autoscaler/enabled,k8s.io/cluster-autoscaler/my-cluster
    ```
2.  **Karpenter**:

    * Proyecto open-source de aprovisionamiento de nodos de AWS
    * Selecciona tipos de instancia óptimos para los requisitos del workload
    * Aprovisionamiento rápido de nodos (en segundos)
    * Optimización de costos y gestión unificada del ciclo de vida

    ```yaml
    # Karpenter Provisioner
    apiVersion: karpenter.sh/v1alpha5
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
            name: default-class
      limits:
        cpu: 1000
          memory: 1000Gi
      provider:
        subnetSelector:
          karpenter.sh/discovery: "true"
        securityGroupSelector:
          karpenter.sh/discovery: "true"
      ttlSecondsAfterEmpty: 30
    ```
3.  **Horizontal Pod Autoscaler (HPA)**:

    * Ajusta automáticamente la cantidad de réplicas de pods
    * Basado en CPU, memoria o métricas personalizadas
    * Puede activar indirectamente Auto Scaling de node groups
    * Funciona junto con Cluster Autoscaler o Karpenter

    ```yaml
    # Horizontal Pod Autoscaler
    apiVersion: autoscaling/v2
    kind: HorizontalPodAutoscaler
    metadata:
      name: my-app-hpa
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

**Vertical Pod Autoscaler (VPA):**

VPA se usa para ajustar automáticamente las solicitudes de CPU y memoria de los pods, pero no ajusta directamente el tamaño de los node groups:

```yaml
# Vertical Pod Autoscaler
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: my-app-vpa
spec:
  targetRef:
    apiVersion: "apps/v1"
    kind: Deployment
    name: my-app
  updatePolicy:
    updateMode: "Auto"
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

VPA proporciona las siguientes características:

* Ajuste automático de solicitudes de recursos de pods
* Recomendaciones basadas en el uso de recursos
* Actualizaciones de solicitudes de recursos mediante reinicios de pods

Sin embargo, VPA no ajusta directamente el tamaño de los node groups y solo afecta la asignación de recursos a nivel de pod.

**Estrategias de Auto Scaling de node groups:**

1. **Scaling reactivo**:
   * Usa Cluster Autoscaler
   * Agrega nodos cuando los pods no pueden programarse
   * Elimina nodos cuando la utilización de recursos es baja
   * Adecuado para workloads predecibles
2. **Scaling predictivo**:
   * Usa AWS Auto Scaling predictive scaling
   * Predice la demanda futura basándose en patrones históricos
   * Asegura capacidad antes de que aumente la demanda
   * Adecuado para workloads con patrones periódicos
3. **Scaling dirigido por eventos**:
   * Usa KEDA (Kubernetes Event-driven Autoscaling)
   * Scaling basado en eventos o métricas externas
   * Scaling basado en longitud de cola, conteo de eventos, etc.
   * Adecuado para workloads de procesamiento batch y procesamiento de eventos

**Explicación de otras opciones:**

* **Cluster Autoscaler**: Un componente de Kubernetes que controla directamente Auto Scaling de node groups, agregando o eliminando nodos según los requisitos de scheduling de pods.
* **Karpenter**: Un proyecto open-source de aprovisionamiento de nodos de AWS que aprovisiona rápidamente instancias óptimas que coinciden con los requisitos del workload. Puede usarse como alternativa a Cluster Autoscaler.
* **Horizontal Pod Autoscaler**: Ajusta automáticamente la cantidad de réplicas de pods, lo que puede activar indirectamente Cluster Autoscaler o Karpenter para ajustar el tamaño del node group cuando se crean más pods.

Vertical Pod Autoscaler se usa para ajustar las solicitudes de recursos de pods, pero no ajusta directamente el tamaño de node groups. Por lo tanto, Vertical Pod Autoscaler es el que NO se usa para controlar el comportamiento de Auto Scaling de node groups.

</details>

## Hands-on Exercises

### Exercise 1: Implementing Network Policies in an EKS Cluster

**Escenario:** Eres ingeniero de seguridad en tu empresa y necesitas restringir el tráfico de red entre microservicios en un cluster EKS. Específicamente, solo el servicio frontend debe poder acceder a la API backend, y la base de datos solo debe ser accesible desde la API backend.

**Requisitos:**

1. Instalar el motor de políticas de red Calico
2. Implementar una política de denegación predeterminada
3. Permitir tráfico desde frontend hacia backend
4. Permitir tráfico desde backend hacia database
5. Probar políticas

**Solución:**

<details>

<summary>Mostrar solución</summary>

**1. Instalar el motor de políticas de red Calico**

```bash
# Install Tigera Operator
kubectl create namespace tigera-operator
helm repo add projectcalico https://docs.projectcalico.org/charts
helm install calico projectcalico/tigera-operator --namespace tigera-operator

# Verify installation
kubectl get pods -n calico-system
```

**2. Crear namespace y aplicaciones de ejemplo**

```bash
# Create namespace
kubectl create namespace microservices

# Deploy frontend
cat > frontend.yaml << EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
  namespace: microservices
  labels:
    app: frontend
spec:
  replicas: 2
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      containers:
      - name: nginx
        image: nginx:alpine
        ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: frontend
  namespace: microservices
spec:
  selector:
    app: frontend
  ports:
  - port: 80
    targetPort: 80
EOF

kubectl apply -f frontend.yaml

# Deploy backend
cat > backend.yaml << EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: microservices
  labels:
    app: backend
spec:
  replicas: 2
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
      - name: httpd
        image: httpd:alpine
        ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: backend
  namespace: microservices
spec:
  selector:
    app: backend
  ports:
  - port: 80
    targetPort: 80
EOF

kubectl apply -f backend.yaml

# Deploy database
cat > database.yaml << EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: database
  namespace: microservices
  labels:
    app: database
spec:
  replicas: 1
  selector:
    matchLabels:
      app: database
  template:
    metadata:
      labels:
        app: database
    spec:
      containers:
      - name: postgres
        image: postgres:13-alpine
        env:
        - name: POSTGRES_PASSWORD
          value: "password"
        ports:
        - containerPort: 5432
---
apiVersion: v1
kind: Service
metadata:
  name: database
  namespace: microservices
spec:
  selector:
    app: database
  ports:
  - port: 5432
    targetPort: 5432
EOF

kubectl apply -f database.yaml

# Verify deployment
kubectl get pods -n microservices
kubectl get services -n microservices
```

**3. Implementar política de denegación predeterminada**

```bash
# Create default deny policy
cat > default-deny.yaml << EOF
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: microservices
spec:
  selector: all()
  types:
  - Ingress
  - Egress
EOF

kubectl apply -f default-deny.yaml
```

**4. Permitir tráfico desde frontend hacia backend**

```bash
# Policy to allow traffic from frontend to backend
cat > frontend-to-backend.yaml << EOF
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: frontend-to-backend
  namespace: microservices
spec:
  selector: app == 'backend'
  types:
  - Ingress
  ingress:
  - action: Allow
    source:
      selector: app == 'frontend'
    destination:
      ports:
      - 80
EOF

kubectl apply -f frontend-to-backend.yaml

# Allow frontend egress to external DNS and API
cat > frontend-egress.yaml << EOF
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: frontend-egress
  namespace: microservices
spec:
  selector: app == 'frontend'
  types:
  - Egress
  egress:
  - action: Allow
    destination:
      selector: app == 'backend'
      ports:
      - 80
  # Allow DNS access
  - action: Allow
    destination:
      selector: k8s-app == 'kube-dns'
      ports:
      - 53
EOF

kubectl apply -f frontend-egress.yaml
```

**5. Permitir tráfico desde backend hacia database**

```bash
# Policy to allow traffic from backend to database
cat > backend-to-database.yaml << EOF
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: backend-to-database
  namespace: microservices
spec:
  selector: app == 'database'
  types:
  - Ingress
  ingress:
  - action: Allow
    source:
      selector: app == 'backend'
    destination:
      ports:
      - 5432
EOF

kubectl apply -f backend-to-database.yaml

# Allow backend egress to external DNS and database
cat > backend-egress.yaml << EOF
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: backend-egress
  namespace: microservices
spec:
  selector: app == 'backend'
  types:
  - Egress
  egress:
  - action: Allow
    destination:
      selector: app == 'database'
      ports:
      - 5432
  # Allow DNS access
  - action: Allow
    destination:
      selector: k8s-app == 'kube-dns'
      ports:
      - 53
EOF

kubectl apply -f backend-egress.yaml
```

**6. Probar políticas**

```bash
# Get frontend pod name
FRONTEND_POD=$(kubectl get pods -n microservices -l app=frontend -o jsonpath='{.items[0].metadata.name}')

# Get backend pod name
BACKEND_POD=$(kubectl get pods -n microservices -l app=backend -o jsonpath='{.items[0].metadata.name}')

# Get database pod name
DATABASE_POD=$(kubectl get pods -n microservices -l app=database -o jsonpath='{.items[0].metadata.name}')

# Test connection from frontend to backend (should succeed)
kubectl exec -it $FRONTEND_POD -n microservices -- wget -O- --timeout=2 http://backend

# Test connection from frontend to database (should fail)
kubectl exec -it $FRONTEND_POD -n microservices -- nc -zv database 5432

# Test connection from backend to database (should succeed)
kubectl exec -it $BACKEND_POD -n microservices -- nc -zv database 5432

# Test connection from backend to external site (should fail)
kubectl exec -it $BACKEND_POD -n microservices -- wget -O- --timeout=2 https://www.example.com
```

**7. Visualización de políticas de red (opcional)**

```bash
# Install Calico network policy visualization tool
kubectl apply -f https://raw.githubusercontent.com/tigera/ccol/master/manifests/tigera-policies-viewer/tigera-policies-viewer.yaml

# Set up port forwarding
kubectl port-forward -n tigera-policies-viewer svc/tigera-policies-viewer 8080:8080

# Access http://localhost:8080 in browser to visualize policies
```

A través de este ejercicio, aprendiste a usar Calico para restringir el tráfico de red entre microservicios en un cluster EKS. Al implementar políticas de denegación predeterminada y permitir explícitamente solo el tráfico necesario, aplicaste el principio de privilegio mínimo. Estas políticas de red ayudan a mejorar la seguridad al restringir la comunicación entre servicios dentro del cluster y reducir la superficie de ataque potencial.

</details>

\### Exercise 2: Configuring IRSA and S3 Access in an EKS Cluster

**Escenario:** Eres ingeniero DevOps en tu empresa y tienes aplicaciones ejecutándose en un cluster EKS que necesitan acceder de forma segura a un bucket S3. Siguiendo mejores prácticas de seguridad, en lugar de compartir el rol IAM del nodo, quieres usar IRSA (IAM Roles for Service Accounts) para conceder solo los permisos necesarios a pods específicos.

**Requisitos:**

1. Asociar el proveedor OIDC con el cluster EKS
2. Crear un rol IAM con permisos de acceso a S3
3. Crear una service account de Kubernetes y asociar el rol IAM
4. Desplegar un pod usando la service account
5. Probar el acceso a S3

**Solución:**

<details>

<summary>Mostrar solución</summary>

**1. Asociar el proveedor OIDC con el cluster EKS**

```bash
# Set cluster name
CLUSTER_NAME=my-cluster
REGION=us-west-2

# Get OIDC provider URL
OIDC_PROVIDER=$(aws eks describe-cluster --name $CLUSTER_NAME --region $REGION --query "cluster.identity.oidc.issuer" --output text | sed -e "s/^https:\/\///")

# Check if OIDC provider already exists
aws iam list-open-id-connect-providers | grep $OIDC_PROVIDER

# Create OIDC provider if it doesn't exist
if [ $? -ne 0 ]; then
  echo "Creating OIDC provider..."
  eksctl utils associate-iam-oidc-provider --cluster $CLUSTER_NAME --region $REGION --approve
else
  echo "OIDC provider already exists."
fi
```

**2. Crear rol IAM con permisos de acceso a S3**

```bash
# Get account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Set namespace and service account name
NAMESPACE=default
SERVICE_ACCOUNT_NAME=s3-access-sa

# Create trust policy
cat > trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::${ACCOUNT_ID}:oidc-provider/${OIDC_PROVIDER}"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "${OIDC_PROVIDER}:sub": "system:serviceaccount:${NAMESPACE}:${SERVICE_ACCOUNT_NAME}"
        }
      }
    }
  ]
}
EOF

# Create IAM role
ROLE_NAME=eks-s3-access-role
aws iam create-role --role-name $ROLE_NAME --assume-role-policy-document file://trust-policy.json

# Attach S3 read-only policy
aws iam attach-role-policy --role-name $ROLE_NAME --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess

# Get role ARN
ROLE_ARN=$(aws iam get-role --role-name $ROLE_NAME --query Role.Arn --output text)
echo "Role ARN: $ROLE_ARN"
```

**3. Crear Kubernetes Service Account y asociar rol IAM**

```bash
# Create service account
cat > service-account.yaml << EOF
apiVersion: v1
kind: ServiceAccount
metadata:
  name: ${SERVICE_ACCOUNT_NAME}
  namespace: ${NAMESPACE}
  annotations:
    eks.amazonaws.com/role-arn: ${ROLE_ARN}
EOF

kubectl apply -f service-account.yaml

# Verify service account
kubectl get serviceaccount $SERVICE_ACCOUNT_NAME -o yaml
```

**4. Desplegar Pod usando la Service Account**

```bash
# Deploy test pod
cat > s3-test-pod.yaml << EOF
apiVersion: v1
kind: Pod
metadata:
  name: s3-test-pod
  namespace: ${NAMESPACE}
spec:
  serviceAccountName: ${SERVICE_ACCOUNT_NAME}
  containers:
  - name: aws-cli
    image: amazon/aws-cli:latest
    command:
    - sleep
    - "3600"
  restartPolicy: Never
EOF

kubectl apply -f s3-test-pod.yaml

# Check pod status
kubectl get pod s3-test-pod
kubectl describe pod s3-test-pod
```

**5. Probar acceso a S3**

```bash
# Test listing S3 buckets
kubectl exec -it s3-test-pod -- aws s3 ls

# Test listing objects in a specific S3 bucket (change bucket name as needed)
kubectl exec -it s3-test-pod -- aws s3 ls s3://my-bucket/

# Verify AWS credentials
kubectl exec -it s3-test-pod -- aws sts get-caller-identity

# Check environment variables
kubectl exec -it s3-test-pod -- env | grep AWS
```

**6. Desplegar un Pod regular para comparación**

```bash
# Deploy a pod using a regular service account
cat > regular-pod.yaml << EOF
apiVersion: v1
kind: Pod
metadata:
  name: regular-pod
  namespace: ${NAMESPACE}
spec:
  containers:
  - name: aws-cli
    image: amazon/aws-cli:latest
    command:
    - sleep
    - "3600"
  restartPolicy: Never
EOF

kubectl apply -f regular-pod.yaml

# Test S3 access from regular pod (should fail if node IAM role doesn't have S3 access permissions)
kubectl exec -it regular-pod -- aws s3 ls
```

**7. Limpieza**

```bash
# Delete pods
kubectl delete pod s3-test-pod regular-pod

# Delete service account
kubectl delete serviceaccount $SERVICE_ACCOUNT_NAME

# Clean up IAM role (optional)
aws iam detach-role-policy --role-name $ROLE_NAME --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess
aws iam delete-role --role-name $ROLE_NAME
```

**Cómo funciona IRSA:**

1. **Conexión del proveedor OIDC**:
   * El cluster EKS se configura como proveedor OIDC.
   * Esto permite que los tokens de service account de Kubernetes se conviertan en un mecanismo de autenticación de confianza en AWS IAM.
2. **Trust policy del rol IAM**:
   * La trust policy del rol IAM restringe qué service accounts de Kubernetes pueden asumir el rol.
   * Se usan condiciones para limitarlo a service accounts específicas en namespaces específicos.
3. **Anotación de Service Account**:
   * La anotación `eks.amazonaws.com/role-arn` especifica qué rol IAM debe asumir la service account.
   * Esta anotación es procesada por el EKS Pod Identity Webhook.
4. **Inyección de variables de entorno**:
   * El EKS Pod Identity Webhook inyecta automáticamente las siguientes variables de entorno en los pods:
     * `AWS_ROLE_ARN`
     * `AWS_WEB_IDENTITY_TOKEN_FILE`
     * `AWS_REGION`
   * Los AWS SDKs usan estas variables de entorno para obtener credenciales.
5. **Principio de privilegio mínimo**:
   * Otorga solo los permisos mínimos requeridos para la aplicación.
   * En este ejemplo, solo otorgamos permisos de acceso de solo lectura a S3.

A través de este laboratorio, aprendiste a configurar IRSA para conceder permisos granulares a servicios de AWS solo a pods específicos que se ejecutan en un cluster EKS. Este enfoque es más seguro que compartir roles IAM de nodos y sigue el principio de privilegio mínimo.

</details>

## Advanced Topics

Las siguientes preguntas tratan sobre temas avanzados relacionados con la creación de clusters de Amazon EKS. Esta sección evalúa tu comprensión de conceptos avanzados y mejores prácticas para la creación de clusters EKS.

1. ¿Cuál de los siguientes NO es un cambio que ocurre al habilitar Prefix Delegation en un cluster de Amazon EKS?
   * A) A cada ENI se le asigna un bloque CIDR /28 (16 IPs)
   * B) Aumento de pods máximos por nodo
   * C) Reducción del tiempo de inicio de pods
   * D) Mayor eficiencia en el uso de direcciones IP

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Reducción del tiempo de inicio de pods**

**Explicación:** El cambio que NO ocurre al habilitar Prefix Delegation en un cluster de Amazon EKS es "Reducción del tiempo de inicio de pods". En realidad, habilitar prefix delegation no reduce el tiempo de inicio de pods; incluso puede aumentarlo ligeramente. Los beneficios principales de prefix delegation son el aumento de pods máximos por nodo y una mayor eficiencia en el uso de direcciones IP.

**Cambios reales al habilitar Prefix Delegation:**

1. **A cada ENI se le asigna un bloque CIDR /28 (16 IPs)**:
   * De forma predeterminada, VPC CNI asigna direcciones IP secundarias desde la ENI para cada pod.
   * Cuando prefix delegation está habilitada, a cada ENI se le asignan bloques CIDR /28 (16 IPs) en lugar de direcciones IP individuales.
   * Esto aumenta significativamente la cantidad de direcciones IP que cada ENI puede admitir.
2. **Aumento de pods máximos por nodo**:
   * Usar prefix delegation aumenta significativamente los pods máximos por nodo.
   * Por ejemplo, para una instancia m5.large:
     * Configuración predeterminada: máximo 29 pods
     * Con prefix delegation habilitada: máximo 110+ pods
3. **Mayor eficiencia en el uso de direcciones IP**:
   * Optimiza el uso de direcciones IP en clusters grandes.
   * Útil en entornos con rangos CIDR de VPC limitados.
   * Permite ejecutar más pods dentro del mismo espacio de direcciones IP.

**Impacto de Prefix Delegation en el tiempo de inicio de pods:**

Prefix delegation no reduce el tiempo de inicio de pods; en realidad puede aumentarlo ligeramente por las siguientes razones:

1. **Sobrecarga adicional de configuración**:
   * Puede ocurrir sobrecarga adicional para la asignación y gestión de bloques CIDR.
   * Puede necesitarse tiempo para actualizaciones de tablas de rutas.
2. **Complejidad de asignación de direcciones IP**:
   * La asignación y gestión de bloques CIDR puede ser más compleja que la asignación de direcciones IP individuales.
   * Esto puede causar ligeros retrasos durante el inicio de pods.
3. **Tiempo de configuración inicial**:
   * El tiempo de configuración inicial para asignar bloques CIDR a nuevas ENIs puede ser mayor.
   * Sin embargo, una vez configurado, se pueden iniciar varios pods rápidamente en esa ENI.

**Cómo habilitar Prefix Delegation:**

```bash
# Enable prefix delegation
kubectl set env daemonset aws-node -n kube-system ENABLE_PREFIX_DELEGATION=true

# Check prefix delegation status
kubectl describe daemonset aws-node -n kube-system | grep ENABLE_PREFIX_DELEGATION
```

**Limitaciones de Prefix Delegation:**

1. **Compatibilidad de instancias EC2**:
   * Solo las instancias basadas en Nitro admiten prefix delegation.
   * No puede usarse en instancias de generaciones anteriores.
2. **Requisitos de versión de VPC CNI**:
   * Requiere VPC CNI versión 1.9.0 o superior.
   * Esta característica no está disponible en versiones anteriores.
3. **Requisitos de tamaño de subnet**:
   * Requiere subnets con suficiente espacio de direcciones IP.
   * Las direcciones IP pueden agotarse rápidamente en subnets pequeñas.
4. **Consideraciones de transición**:
   * Cuando se habilita en clusters existentes, solo los pods nuevos usan prefix delegation.
   * Los pods existentes deben reiniciarse para aplicarla a todos los pods.

Prefix delegation es una característica potente que aumenta los pods máximos por nodo y mejora la eficiencia de uso de direcciones IP, pero no reduce el tiempo de inicio de pods. Por lo tanto, "Reducción del tiempo de inicio de pods" NO es un cambio que ocurra al habilitar prefix delegation.

</details>

2\. ¿Cuál de los siguientes NO es un beneficio principal de mezclar tipos de instancia en un node group de un cluster de Amazon EKS? - A) Optimización de costos - B) Mayor disponibilidad - C) Seleccionar tipos de instancia adecuados para las características del workload - D) Gestión simplificada del cluster

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: D) Gestión simplificada del cluster**

**Explicación:** La opción que NO es un beneficio principal de mezclar tipos de instancia en un node group de un cluster de Amazon EKS es "Gestión simplificada del cluster". En realidad, mezclar varios tipos de instancia puede hacer que la gestión del cluster sea más compleja. Los beneficios principales de mezclar tipos de instancia son optimización de costos, mayor disponibilidad y selección de tipos de instancia adecuados para las características del workload.

**Beneficios reales de mezclar tipos de instancia:**

1. **Optimización de costos**:
   * Mezclar spot instances e instancias on-demand
   * Aprovechar diferencias de precio entre varias familias de instancias
   * Seleccionar la relación precio-rendimiento óptima para los requisitos del workload
   *   Ejemplo:

       ```yaml
       apiVersion: eksctl.io/v1alpha5
       kind: ClusterConfig
       metadata:
         name: my-cluster
         region: us-west-2
       managedNodeGroups:
         - name: mixed-spot-instances
           instanceTypes: ["m5.large", "m5a.large", "m5d.large", "m5ad.large", "m5n.large"]
           spot: true
           minSize: 2
           maxSize: 10
       ```
2. **Mayor disponibilidad**:
   * Usar tipos de instancia alternativos cuando tipos de instancia específicos tienen capacidad insuficiente
   * Puede sustituir con otros tipos cuando se interrumpen spot instances
   * Distribución del riesgo mediante diversificación entre múltiples familias de instancias
   *   Ejemplo:

       ```yaml
       apiVersion: eksctl.io/v1alpha5
       kind: ClusterConfig
       metadata:
         name: my-cluster
         region: us-west-2
       managedNodeGroups:
         - name: mixed-instance-types
           instanceTypes: ["c5.large", "c5a.large", "c5d.large", "c5n.large"]
           minSize: 3
           maxSize: 10
           spotAllocationStrategy: capacity-optimized
       ```
3. **Seleccionar tipos de instancia adecuados para las características del workload**:
   * Proporcionar tipos de instancia para diversos requisitos de workload
   * Serie C para workloads intensivos en cómputo
   * Serie R para workloads intensivos en memoria
   * Serie M para workloads equilibrados
   * Series G o P para workloads GPU
   *   Ejemplo:

       ```yaml
       # Compute optimized node group
       apiVersion: eksctl.io/v1alpha5
       kind: ClusterConfig
       metadata:
         name: my-cluster
         region: us-west-2
       managedNodeGroups:
         - name: compute-optimized
           instanceTypes: ["c5.2xlarge"]
           minSize: 2
           maxSize: 10
           labels:
             workload-type: compute
           taints:
             - key: workload-type
               value: compute
               effect: NoSchedule

         # Memory optimized node group
         - name: memory-optimized
           instanceTypes: ["r5.2xlarge"]
           minSize: 2
           maxSize: 10
           labels:
             workload-type: memory
           taints:
             - key: workload-type
               value: memory
               effect: NoSchedule
       ```

**Desventajas de mezclar tipos de instancia:**

1. **Mayor complejidad de gestión del cluster**:
   * Requiere monitorear y gestionar varios tipos de instancia
   * Complejidad de troubleshooting debido a diferentes características de rendimiento
   * Necesidad de ajustar resource requests y limits para varios tipos de instancia
2. **Menor predictibilidad del workload**:
   * Las características de rendimiento pueden variar según el tipo de instancia
   * Posibles variaciones de rendimiento del workload, especialmente al usar spot instances
3. **Complejidad de asignación de recursos**:
   * Dificultad para establecer pod resource requests y limits para varios tipos de instancia
   * Reglas de scheduling complejas necesarias usando node selectors y taints
4. **Carga de pruebas y validación**:
   * Necesidad de probar aplicaciones en varios tipos de instancia
   * Mayor probabilidad de descubrir problemas de rendimiento y compatibilidad

**Estrategias para mezclar tipos de instancia:**

1.  **Separar node groups por workload**:

    ```yaml
    # Node group for web servers
    - name: web-servers
      instanceTypes: ["c5.large", "c5a.large"]
      labels:
        role: web

    # Node group for databases
    - name: databases
      instanceTypes: ["r5.xlarge", "r5a.xlarge"]
      labels:
        role: database
    ```
2.  **Estrategia de optimización de costos**:

    ```yaml
    # Base on-demand node group
    - name: on-demand-base
      instanceTypes: ["m5.large"]
      minSize: 2
      maxSize: 5
      spot: false

    # Spot node group for scaling
    - name: spot-scaling
      instanceTypes: ["m5.large", "m5a.large", "m5d.large", "m5n.large"]
      minSize: 0
      maxSize: 20
      spot: true
    ```
3.  **Estrategia de optimización de disponibilidad**:

    ```yaml
    # Diversification across multiple instance families
    - name: high-availability
      instanceTypes: ["m5.large", "m5a.large", "c5.large", "c5a.large", "r5.large", "r5a.large"]
      minSize: 3
      maxSize: 10
      spotAllocationStrategy: capacity-optimized
    ```

Mezclar tipos de instancia proporciona beneficios como optimización de costos, mayor disponibilidad y selección de tipos de instancia adecuados para las características del workload, pero la gestión del cluster no se simplifica y de hecho puede volverse más compleja. Por lo tanto, "Gestión simplificada del cluster" NO es un beneficio principal de mezclar tipos de instancia.

</details>

3. ¿Cuál es la estrategia más segura para actualizar node groups en un cluster de Amazon EKS?
   * A) Actualización in-place
   * B) Deployment Blue/Green
   * C) Canary deployment
   * D) Rolling update

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Deployment Blue/Green**

**Explicación:** La estrategia más segura para actualizar node groups en un cluster de Amazon EKS es Blue/Green deployment. Blue/Green deployment crea un nuevo node group (green), migra workloads y luego elimina el node group existente (blue). Este enfoque es el más seguro porque puedes volver inmediatamente al entorno anterior si ocurren problemas durante la actualización.

**Comparación de estrategias de actualización de node group:**

1. **Blue/Green Deployment**:
   * **Cómo funciona**: Crear nuevo node group → Migrar workloads → Eliminar node group existente
   * **Ventajas**:
     * Rollback inmediato posible
     * Interrupción mínima del workload durante actualizaciones
     * Puede comparar entornos antes y después de la actualización
     * Puede cambiar después de probar
   * **Desventajas**:
     * Requiere temporalmente el doble de recursos
     * Complejidad de implementación
     * Mayor costo
   *   **Ejemplo de implementación**:

       ```bash
       # 1. Create new node group
       eksctl create nodegroup \
         --cluster my-cluster \
         --name my-nodegroup-v2 \
         --node-type m5.large \
         --nodes 3 \
         --node-ami-family AmazonLinux2 \
         --node-labels "version=v2,color=green"

       # 2. Migrate workloads (update node selector)
       kubectl patch deployment my-app -p '{"spec":{"template":{"spec":{"nodeSelector":{"color":"green"}}}}}'

       # 3. Verify all workloads have moved to new nodes
       kubectl get pods -o wide

       # 4. Remove existing node group
       eksctl delete nodegroup --cluster my-cluster --name my-nodegroup-v1
       ```
2. **Rolling Update**:
   * **Cómo funciona**: Reemplazar nodos uno a la vez (cordon → drain → terminate → agregar nuevo nodo)
   * **Ventajas**:
     * No se necesitan recursos adicionales
     * Estrategia predeterminada para node groups administrados de EKS
     * Implementación simple
   * **Desventajas**:
     * Difícil hacer rollback
     * Los problemas durante la actualización pueden afectar a todo el cluster
     * El tiempo de actualización puede ser largo
   *   **Ejemplo de implementación**:

       ```bash
       # Update managed node group
       aws eks update-nodegroup-version \
         --cluster-name my-cluster \
         --nodegroup-name my-nodegroup

       # Modify update configuration
       aws eks update-nodegroup-config \
         --cluster-name my-cluster \
         --nodegroup-name my-nodegroup \
         --update-config '{"maxUnavailable": 1}'
       ```
3. **Canary Deployment**:
   * **Cómo funciona**: Crear un nuevo node group pequeño → Migrar algunos workloads → Validar → Completar migración
   * **Ventajas**:
     * Minimiza el riesgo
     * Permite validación gradual
     * Limita el alcance del impacto cuando ocurren problemas
   * **Desventajas**:
     * Complejidad de implementación
     * Requiere recursos adicionales
     * Consume tiempo hasta completar la migración
   *   **Ejemplo de implementación**:

       ```bash
       # 1. Create small canary node group
       eksctl create nodegroup \
         --cluster my-cluster \
         --name canary-nodegroup \
         --node-type m5.large \
         --nodes 1 \
         --node-labels "deployment=canary"

       # 2. Migrate some workloads
       kubectl patch deployment my-app -p '{"spec":{"template":{"spec":{"nodeSelector":{"deployment":"canary"}}}}}'

       # 3. Proceed with complete migration after validation
       ```
4. **Actualización in-place**:
   * **Cómo funciona**: Realizar actualizaciones directamente en nodos existentes
   * **Ventajas**:
     * No se necesitan recursos adicionales
     * Adecuada para cambios simples
   * **Desventajas**:
     * Alto riesgo
     * Rollback difícil
     * Posible daño al nodo si la actualización falla
     * No recomendada en EKS
   *   **Ejemplo de implementación**:

       ```bash
       # SSH into node for direct update (not recommended)
       ssh ec2-user@node-ip
       sudo yum update -y
       ```

**Por qué Blue/Green Deployment es lo más seguro:**

1. **Aislamiento completo**:
   * El nuevo entorno está completamente separado del entorno existente, minimizando el impacto
   * El entorno existente no se ve afectado incluso si ocurren problemas durante la actualización
2. **Rollback inmediato**:
   * Puede redirigir inmediatamente el tráfico al entorno existente cuando ocurren problemas
   * Rollback posible sin downtime
3. **Oportunidad de validación**:
   * Puede probar exhaustivamente el nuevo entorno antes de cambiar el tráfico de producción
   * Puede validar bajo condiciones idénticas al entorno real
4. **Transición gradual**:
   * Puede hacer la transición gradual del tráfico al nuevo entorno
   * Limita el alcance del impacto cuando ocurren problemas

**Mejores prácticas de Blue/Green Deployment:**

1. **Automatización**:
   * Minimizar errores humanos automatizando el proceso de deployment
   * Integrar con pipeline CI/CD
2. **Monitoreo mejorado**:
   * Monitorear métricas de rendimiento y errores del nuevo entorno
   * Comparar y analizar con el entorno existente
3. **Transición gradual**:
   * Hacer transición gradual del tráfico al nuevo entorno
   * Hacer rollback inmediatamente cuando ocurren problemas
4. **Optimización de recursos**:
   * Limpiar rápidamente recursos innecesarios después de completar la transición
   * Optimización de costos

Blue/Green deployment tiene desventajas de recursos adicionales y complejidad de implementación, pero es el enfoque más excelente en términos de seguridad. Se recomienda especialmente para entornos de producción importantes o casos donde el impacto de negocio es significativo si fallan las actualizaciones.

</details>

4\. ¿Cuál de los siguientes NO es un método para optimizar Auto Scaling de node groups en un cluster de Amazon EKS? - A) Ajustar el intervalo de escaneo de Cluster Autoscaler - B) Configurar prioridad y preemption de pods - C) Etiquetar Auto Scaling groups por node group - D) Usar el mismo tipo de instancia para todos los nodos

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: D) Usar el mismo tipo de instancia para todos los nodos**

**Explicación:** La opción que NO es un método para optimizar Auto Scaling de node groups en un cluster de Amazon EKS es "Usar el mismo tipo de instancia para todos los nodos". En la práctica, mezclar varios tipos de instancia es una estrategia de Auto Scaling más efectiva en términos de optimización de costos y disponibilidad. Especialmente al usar Spot Instances, se recomienda especificar múltiples tipos de instancia para aumentar la disponibilidad de capacidad y reducir el riesgo de interrupción.

**Métodos reales para optimizar Auto Scaling de node groups:**

1. **Ajustar el intervalo de escaneo de Cluster Autoscaler**:
   * Cluster Autoscaler escanea periódicamente el cluster para determinar si se necesita escalar hacia arriba o hacia abajo.
   * Puedes equilibrar tiempo de respuesta y uso de recursos ajustando el intervalo de escaneo.
   *   Ejemplo:

       ```yaml
       # Cluster Autoscaler deployment configuration
       apiVersion: apps/v1
       kind: Deployment
       metadata:
         name: cluster-autoscaler
         namespace: kube-system
       spec:
         template:
           spec:
             containers:
             - name: cluster-autoscaler
               image: k8s.gcr.io/autoscaling/cluster-autoscaler:v1.23.0
               command:
               - ./cluster-autoscaler
               - --v=4
               - --stderrthreshold=info
               - --cloud-provider=aws
               - --scan-interval=30s  # Adjust scan interval (default: 10 seconds)
               - --max-node-provision-time=15m
               - --node-group-auto-discovery=asg:tag=k8s.io/cluster-autoscaler/enabled,k8s.io/cluster-autoscaler/my-cluster
       ```
2. **Configurar prioridad y preemption de pods**:
   * Usa prioridad y preemption de pods (PriorityClass) para asegurar que los workloads importantes se programen primero.
   * Cuando los recursos son insuficientes, los pods de menor prioridad son preempted para hacer espacio para pods de mayor prioridad.
   *   Ejemplo:

       ```yaml
       # Priority class definition
       apiVersion: scheduling.k8s.io/v1
       kind: PriorityClass
       metadata:
         name: high-priority
       value: 1000000
       globalDefault: false
       description: "High priority pods"
       ---
       # High priority pod
       apiVersion: v1
       kind: Pod
       metadata:
         name: high-priority-pod
       spec:
         priorityClassName: high-priority
         containers:
         - name: nginx
           image: nginx
       ```
3. **Etiquetar Auto Scaling Groups por node group**:
   * Etiqueta Auto Scaling groups para que Cluster Autoscaler pueda identificar y gestionar node groups específicos.
   * Se pueden configurar distintos comportamientos de Auto Scaling para cada node group.
   *   Ejemplo:

       ```bash
       # Tag Auto Scaling group
       aws autoscaling create-or-update-tags \
         --tags ResourceId=my-asg,ResourceType=auto-scaling-group,Key=k8s.io/cluster-autoscaler/enabled,Value=true,PropagateAtLaunch=true \
                ResourceId=my-asg,ResourceType=auto-scaling-group,Key=k8s.io/cluster-autoscaler/my-cluster,Value=owned,PropagateAtLaunch=true

       # Configure Auto Scaling settings per node group
       aws autoscaling update-auto-scaling-group \
         --auto-scaling-group-name my-asg \
         --min-size 2 \
         --max-size 10 \
         --desired-capacity 2
       ```

**Beneficios de mezclar varios tipos de instancia:**

1. **Optimización de costos**:
   * Aprovechar diferencias de precio entre varios tipos de instancia
   * Mayor disponibilidad al usar Spot Instances
   *   Ejemplo:

       ```yaml
       # Node group using various instance types
       apiVersion: eksctl.io/v1alpha5
       kind: ClusterConfig
       metadata:
         name: my-cluster
         region: us-west-2
       managedNodeGroups:
         - name: mixed-instances
           instanceTypes: ["m5.large", "m5a.large", "m5d.large", "m5n.large"]
           minSize: 2
           maxSize: 10
           spot: true
       ```
2. **Mayor disponibilidad**:
   * Usar tipos de instancia alternativos cuando tipos de instancia específicos tienen capacidad insuficiente
   * Puede cambiar a otros tipos cuando Spot Instances se interrumpen
   *   Ejemplo:

       ```yaml
       # Capacity-optimized Spot allocation strategy
       apiVersion: eksctl.io/v1alpha5
       kind: ClusterConfig
       metadata:
         name: my-cluster
         region: us-west-2
       managedNodeGroups:
         - name: spot-nodes
           instanceTypes: ["c5.large", "c5a.large", "c5d.large", "c5n.large"]
           minSize: 2
           maxSize: 10
           spot: true
           spotAllocationStrategy: capacity-optimized
       ```
3. **Seleccionar tipos de instancia según las características del workload**:
   * Proporcionar tipos de instancia adecuados para diversos requisitos de workload
   * Controlar la colocación de workloads usando node selectors y taints
   *   Ejemplo:

       ```yaml
       # Node groups by workload characteristics
       apiVersion: eksctl.io/v1alpha5
       kind: ClusterConfig
       metadata:
         name: my-cluster
         region: us-west-2
       managedNodeGroups:
         - name: general-purpose
           instanceTypes: ["m5.large"]
           minSize: 2
           maxSize: 10

         - name: compute-intensive
           instanceTypes: ["c5.large"]
           minSize: 0
           maxSize: 10
           labels:
             workload-type: compute
       ```

**Estrategias adicionales para optimización de Auto Scaling:**

1. **Overprovisioning**:
   * Mantener cierta cantidad de recursos disponibles para prepararse ante solicitudes repentinas de scaling
   *   Ejemplo:

       ```yaml
       # Overprovisioning pod
       apiVersion: apps/v1
       kind: Deployment
       metadata:
         name: overprovisioning
         namespace: kube-system
       spec:
         replicas: 1
         selector:
           matchLabels:
             app: overprovisioning
         template:
           metadata:
             labels:
               app: overprovisioning
           spec:
             priorityClassName: overprovisioning
             containers:
             - name: reserve-resources
               image: k8s.gcr.io/pause:3.2
               resources:
                 requests:
                   cpu: 1000m
                   memory: 1000Mi
       ```
2. **Optimizar políticas de scaling**:
   * Usar políticas de scaling target tracking
   * Usar políticas de step scaling
   * Habilitar predictive scaling
   *   Ejemplo:

       ```bash
       # Configure target tracking scaling policy
       aws autoscaling put-scaling-policy \
         --auto-scaling-group-name my-asg \
         --policy-name cpu70-target-tracking-scaling-policy \
         --policy-type TargetTrackingScaling \
         --target-tracking-configuration '{"PredefinedMetricSpecification":{"PredefinedMetricType":"ASGAverageCPUUtilization"},"TargetValue":70.0,"DisableScaleIn":false}'
       ```
3. **Usar Karpenter**:
   * Considerar usar Karpenter en lugar de Cluster Autoscaler
   * Aprovisionamiento de nodos más rápido y selección de tipos de instancia más flexible
   *   Ejemplo:

       ```yaml
       # Karpenter Provisioner
       apiVersion: karpenter.sh/v1alpha5
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
               - key: node.kubernetes.io/instance-type
                 operator: In
                 values: ["m5.large", "m5a.large", "m5d.large", "m5n.large"]
         limits:
           resources:
             cpu: 1000
             memory: 1000Gi
       ```

Usar el mismo tipo de instancia para todos los nodos no es una estrategia de optimización de Auto Scaling; más bien, mezclar varios tipos de instancia es más efectivo en términos de optimización de costos y disponibilidad. Por lo tanto, "Usar el mismo tipo de instancia para todos los nodos" NO es un método para optimizar Auto Scaling de node groups.

</details>

5. ¿Cuál de los siguientes NO es una mejor práctica de seguridad a considerar al crear node groups en un cluster de Amazon EKS?
   * A) Requerir IMDSv2
   * B) Aplicar políticas IAM de privilegio mínimo
   * C) Asignar direcciones IP públicas a todos los nodos
   * D) Restringir reglas de security group

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Asignar direcciones IP públicas a todos los nodos**

**Explicación:** La opción que NO es una mejor práctica de seguridad a considerar al crear node groups en un cluster de Amazon EKS es "Asignar direcciones IP públicas a todos los nodos". La mejor práctica de seguridad es en realidad lo contrario: colocar nodos en subnets privadas y no asignar direcciones IP públicas. Esto reduce la superficie de ataque al evitar que los nodos sean directamente accesibles desde internet.

**Mejores prácticas reales de seguridad para la creación de node groups EKS:**

1. **Requerir IMDSv2**:
   * Requerir Instance Metadata Service versión 2 (IMDSv2) para proteger contra ataques SSRF (Server-Side Request Forgery)
   * IMDSv2 usa solicitudes basadas en sesión para mayor seguridad
   *   Ejemplo:

       ```yaml
       # eksctl configuration file
       apiVersion: eksctl.io/v1alpha5
       kind: ClusterConfig
       metadata:
         name: my-cluster
         region: us-west-2
       managedNodeGroups:
         - name: secure-nodes
           instanceType: m5.large
           minSize: 2
           maxSize: 5
           disableIMDSv1: true  # Disable IMDSv1
           metadataOptions:
             httpTokens: required  # Require IMDSv2
             httpPutResponseHopLimit: 1
       ```
2. **Aplicar políticas IAM de privilegio mínimo**:
   * Otorgar solo los permisos mínimos necesarios a roles IAM de nodos
   * Crear políticas granulares cuando se necesiten permisos adicionales más allá de las políticas administradas predeterminadas
   *   Ejemplo:

       ```yaml
       # Least privilege policy for node IAM role
       apiVersion: eksctl.io/v1alpha5
       kind: ClusterConfig
       metadata:
         name: my-cluster
         region: us-west-2
       managedNodeGroups:
         - name: secure-nodes
           instanceType: m5.large
           minSize: 2
           maxSize: 5
           iam:
             attachPolicyARNs:
               - arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy
               - arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly
               - arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy
             withAddonPolicies:
               imageBuilder: false
               autoScaler: false
               externalDNS: false
               certManager: false
               appMesh: false
               ebs: true
               fsx: false
               efs: false
               albIngress: false
               xRay: false
               cloudWatch: true
       ```
3. **Restringir reglas de Security Group**:
   * Restringir reglas inbound y outbound para security groups de nodos
   * Abrir solo los puertos mínimos necesarios
   *   Ejemplo:

       ```bash
       # Create security group
       aws ec2 create-security-group \
         --group-name eks-node-sg \
         --description "Security group for EKS nodes" \
         --vpc-id vpc-12345

       # Add only rules necessary for cluster communication
       aws ec2 authorize-security-group-ingress \
         --group-id sg-12345 \
         --protocol tcp \
         --port 443 \
         --source-group sg-cluster

       aws ec2 authorize-security-group-ingress \
         --group-id sg-12345 \
         --protocol tcp \
         --port 10250 \
         --source-group sg-cluster
       ```

**Razones para no asignar direcciones IP públicas a los nodos:**

1. **Reducción de la superficie de ataque**:
   * Sin IPs públicas, los nodos no pueden ser accedidos directamente desde internet
   * Tareas de gestión como acceso SSH se realizan mediante bastion hosts o AWS Systems Manager
2. **Arquitectura de seguridad mejorada**:
   * Colocar nodos en subnets privadas
   * Permitir solo comunicación outbound mediante NAT Gateway
   * Permitir tráfico inbound solo mediante load balancers
3. **Cumplimiento normativo**:
   * Muchos estándares y regulaciones de seguridad requieren minimizar la exposición directa a internet
   * Ayuda con cumplimiento para PCI DSS, HIPAA y otras regulaciones

**Ejemplo de colocar nodos en subnets privadas:**

```yaml
# eksctl configuration file
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
vpc:
  subnets:
    private:
      us-west-2a: { id: subnet-private-a }
      us-west-2b: { id: subnet-private-b }
    public:
      us-west-2a: { id: subnet-public-a }
      us-west-2b: { id: subnet-public-b }
managedNodeGroups:
  - name: secure-nodes
    instanceType: m5.large
    minSize: 2
    maxSize: 5
    privateNetworking: true  # Place nodes in private subnets
```

**Mejores prácticas adicionales de seguridad de EKS:**

1. **Habilitar cifrado**:
   * Cifrado de volúmenes EBS
   * Cifrado de Secrets
   *   Ejemplo:

       ```yaml
       apiVersion: eksctl.io/v1alpha5
       kind: ClusterConfig
       metadata:
         name: my-cluster
         region: us-west-2
       secretsEncryption:
         keyARN: arn:aws:kms:us-west-2:123456789012:key/key-id
       nodeGroups:
         - name: secure-nodes
           volumeEncrypted: true
           volumeKmsKeyID: arn:aws:kms:us-west-2:123456789012:key/key-id
       ```
2. **Seguridad de contenedores**:
   * Deshabilitar contenedores privilegiados
   * Usar filesystem raíz de solo lectura
   *   Ejemplo:

       ```yaml
       apiVersion: v1
       kind: Pod
       metadata:
         name: secure-pod
       spec:
         containers:
         - name: secure-container
           image: nginx
           securityContext:
             privileged: false
             readOnlyRootFilesystem: true
             allowPrivilegeEscalation: false
       ```
3. **Implementar políticas de red**:
   * Restringir comunicación pod-a-pod
   * Aplicar políticas de denegación predeterminada
   *   Ejemplo:

       ```yaml
       apiVersion: networking.k8s.io/v1
       kind: NetworkPolicy
       metadata:
         name: default-deny
         namespace: default
       spec:
         podSelector: {}
         policyTypes:
         - Ingress
         - Egress
       ```
4. **Logging y monitoreo**:
   * Habilitar CloudWatch Logs
   * Habilitar GuardDuty EKS Protection
   *   Ejemplo:

       ```bash
       # Enable CloudWatch Logs
       aws eks update-cluster-config \
         --name my-cluster \
         --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'
       ```

Asignar direcciones IP públicas a todos los nodos no es una mejor práctica de seguridad; más bien, aumenta el riesgo de seguridad. Por lo tanto, "Asignar direcciones IP públicas a todos los nodos" NO es una mejor práctica de seguridad a considerar al crear node groups en un cluster de Amazon EKS.

</details>
