# Cuestionario de creación de clústeres EKS - Parte 2

Este cuestionario evalúa tu comprensión de conceptos avanzados, configuraciones de seguridad y configuraciones de red relacionadas con la creación de clústeres Amazon EKS. Cubre temas como seguridad del clúster, network policies y service accounts.

## Preguntas de conceptos básicos

1. ¿Cuál es el propósito principal de IRSA (IAM Roles for Service Accounts) en un clúster Amazon EKS?
   * A) Conceder permisos de IAM a los administradores del clúster
   * B) Asignar IAM roles a worker nodes
   * C) Conceder permisos de acceso a servicios de AWS a Kubernetes service accounts
   * D) Conceder permisos de IAM al EKS control plane

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Conceder permisos de acceso a servicios de AWS a Kubernetes service accounts**

**Explicación:** El propósito principal de IRSA (IAM Roles for Service Accounts) es conceder permisos de acceso a servicios de AWS a Kubernetes service accounts. Esta característica permite proporcionar permisos detallados a nivel de Pod y, en lugar de compartir IAM roles a nivel de node, puedes conceder solo los permisos mínimos necesarios a cada aplicación.

**Cómo funciona IRSA:**

1.  **Configuración del proveedor OpenID Connect (OIDC)**:

    * El clúster EKS se configura como un proveedor OIDC.
    * Esto permite que los tokens de Kubernetes service account se conviertan en un mecanismo de autenticación confiable en AWS IAM.

    ```bash
    # Associate OIDC provider
    eksctl utils associate-iam-oidc-provider --cluster my-cluster --approve
    ```
2.  **Crear IAM Role y configurar la trust policy**:

    * Crea un IAM role que la Kubernetes service account pueda asumir.
    * La trust policy restringe la asunción del role solo a service accounts específicos en namespaces específicos.

    ```json
    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Effect": "Allow",
          "Principal": {
            "Federated": "arn:aws:iam::123456789012:oidc-provider/oidc.eks.region.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE"
          },
          "Action": "sts:AssumeRoleWithWebIdentity",
          "Condition": {
            "StringEquals": {
              "oidc.eks.region.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE:sub": "system:serviceaccount:default:my-service-account"
            }
          }
        }
      ]
    }
    ```
3.  **Crear Service Account y asociar IAM Role**:

    * Agrega el ARN del IAM role como annotation a la service account.

    ```yaml
    apiVersion: v1
    kind: ServiceAccount
    metadata:
      name: my-service-account
      namespace: default
      annotations:
        eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/my-role
    ```
4.  **Usar Service Account en el Pod**:

    * Especifica la service account en el manifiesto del Pod.

    ```yaml
    apiVersion: v1
    kind: Pod
    metadata:
      name: my-pod
    spec:
      serviceAccountName: my-service-account
      containers:
      - name: my-container
        image: my-image
    ```

**Beneficios de IRSA:**

1. **Principio de privilegio mínimo**:
   * Puedes conceder solo los permisos mínimos necesarios a cada aplicación.
   * Configuraciones de permisos diferentes por Pod en lugar de compartir IAM roles a nivel de node
2. **Seguridad mejorada**:
   * No es necesario almacenar credenciales de AWS en el código ni en variables de entorno.
   * Menor riesgo de filtración de credenciales
3. **Aislamiento de permisos**:
   * Diferentes Pods que se ejecutan en el mismo node pueden tener diferentes permisos de IAM.
   * Importante en entornos multi-tenant
4. **Gestión simplificada de credenciales**:
   * No es necesario gestionar directamente credenciales de AWS.
   * La rotación de credenciales se gestiona automáticamente.

**Ejemplo de configuración de IRSA usando eksctl:**

```bash
# Create service account and IAM role
eksctl create iamserviceaccount \
  --name my-service-account \
  --namespace default \
  --cluster my-cluster \
  --attach-policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess \
  --approve

# Verify created service account
kubectl get serviceaccount my-service-account -o yaml
```

**Problemas con otras opciones:**

* **Conceder permisos de IAM a los administradores del clúster**: Este no es el propósito de IRSA. Los permisos de administrador del clúster normalmente se gestionan mediante el ConfigMap aws-auth.
* **Asignar IAM roles a worker nodes**: Esto se hace mediante IAM roles de node y está separado de IRSA. Los IAM roles de node son compartidos por todos los Pods, lo que puede vulnerar el principio de privilegio mínimo.
* **Conceder permisos de IAM al EKS control plane**: Los permisos del EKS control plane se gestionan mediante el IAM role del clúster y no están relacionados con IRSA.

IRSA es una característica importante que permite que los workloads de Kubernetes accedan de forma segura a servicios de AWS, y es el enfoque recomendado al ejecutar aplicaciones en clústeres EKS.

</details>

2\. ¿Cuál es el rol principal de los security groups en un clúster Amazon EKS? - A) Controlar el tráfico de red entre Pods - B) Controlar el tráfico entre el cluster API server y los nodes - C) Aplicar políticas Kubernetes RBAC - D) Gestionar la autenticación de usuarios

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Controlar el tráfico entre el cluster API server y los nodes**

**Explicación:** El rol principal de los security groups en un clúster Amazon EKS es controlar el tráfico entre el cluster API server y los nodes. Los security groups son firewalls virtuales de AWS que controlan el tráfico entrante y saliente a nivel de instancia EC2. En EKS, existen security groups de clúster y security groups de node, que protegen la comunicación entre los componentes del clúster.

**Tipos de Security Groups en clústeres EKS:**

1. **Cluster Security Group**:
   * Se aplica al EKS control plane.
   * Permite la comunicación entre worker nodes y el control plane.
   * Se crea automáticamente de forma predeterminada al crear un clúster EKS.
   * Reglas clave:
     * Permitir tráfico entrante en el puerto 443 desde el node security group
     * Permitir tráfico saliente hacia el node security group
2. **Node Security Group**:
   * Se aplica a worker nodes.
   * Permite la comunicación entre nodes y entre nodes y el control plane.
   * Reglas clave:
     * Permitir todo el tráfico entre nodes
     * Permitir tráfico saliente en el puerto 443 hacia el cluster security group
     * Permitir tráfico entrante desde el cluster security group
     * Permitir el puerto 10250 para kubelet

**Ejemplos de configuración de Security Groups:**

**Reglas del Cluster Security Group**:

```
Inbound:
- Protocol: TCP
- Port Range: 443
- Source: Node Security Group

Outbound:
- Protocol: All Traffic
- Port Range: All Ports
- Destination: 0.0.0.0/0
```

**Reglas del Node Security Group**:

```
Inbound:
- Protocol: All Traffic
- Source: Node Security Group itself (node-to-node communication)

- Protocol: TCP
- Port Range: 10250
- Source: Cluster Security Group (kubelet communication)

Outbound:
- Protocol: All Traffic
- Port Range: All Ports
- Destination: 0.0.0.0/0
```

**Personalización de Security Groups:**

Puedes especificar security groups personalizados al crear un clúster EKS:

```bash
# Specifying custom security groups using AWS CLI
aws eks create-cluster \
  --name my-cluster \
  --role-arn arn:aws:iam::123456789012:role/EksClusterRole \
  --resources-vpc-config subnetIds=subnet-12345,subnet-67890,securityGroupIds=sg-12345

# Specifying custom security groups using eksctl
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
vpc:
  id: vpc-12345
  securityGroup: sg-12345
  subnets:
    private:
      us-west-2a: subnet-12345
      us-west-2b: subnet-67890
```

**Security Groups para Pods:**

Recientemente, EKS también admite security groups a nivel de Pod (característica SecurityGroupsForPods). Esto permite aplicar security groups a Pods individuales:

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

**Problemas con otras opciones:**

* **Controlar el tráfico de red entre Pods**: De forma predeterminada, el tráfico de red entre Pods se controla mediante Kubernetes Network Policies (NetworkPolicy), no mediante security groups de AWS. Aunque la característica SecurityGroupsForPods permite aplicar security groups a nivel de Pod, este no es el rol principal de los security groups.
* **Aplicar políticas Kubernetes RBAC**: RBAC (Role-Based Access Control) es un mecanismo para controlar el acceso a recursos de la Kubernetes API y está separado de los security groups de AWS.
* **Gestionar la autenticación de usuarios**: La autenticación de usuarios en clústeres EKS se gestiona mediante la integración de AWS IAM y Kubernetes RBAC, y no está relacionada con los security groups.

Los security groups desempeñan un rol importante en la seguridad de red de los clústeres EKS, protegiendo la comunicación entre los componentes del clúster y bloqueando tráfico innecesario. Una configuración adecuada de security groups es esencial para fortalecer la postura de seguridad de los clústeres EKS.

</details>

3. ¿Qué se requiere para implementar Kubernetes Network Policies en un clúster Amazon EKS?
   * A) Configuración de AWS security groups
   * B) Un CNI plugin que admita network policies, como Calico o Cilium
   * C) Configuración de AWS Network Firewall
   * D) VPC Flow Logs habilitado

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Un CNI plugin que admita network policies, como Calico o Cilium**

**Explicación:** Para implementar Kubernetes Network Policies en un clúster Amazon EKS, necesitas un CNI (Container Network Interface) plugin que admita network policies, como Calico o Cilium. El Amazon VPC CNI plugin predeterminado no admite network policies, por lo que deben instalarse componentes adicionales.

**Opciones de CNI con soporte para Network Policy:**

1. **Calico**:
   * Solución open-source de networking y seguridad de red ampliamente utilizada
   * Puede usarse junto con Amazon VPC CNI en EKS
   *   Método de instalación:

       ```bash
       # Install Calico using Helm
       helm repo add projectcalico https://docs.projectcalico.org/charts
       helm install calico projectcalico/tigera-operator --namespace tigera-operator --create-namespace

       # Or install using manifest files
       kubectl apply -f https://docs.projectcalico.org/manifests/calico-vxlan.yaml
       ```
2. **Cilium**:
   * Solución de networking, seguridad y observabilidad basada en eBPF
   * Proporciona alto rendimiento y características avanzadas
   *   Método de instalación:

       ```bash
       # Install Cilium using Helm
       helm repo add cilium https://helm.cilium.io/
       helm install cilium cilium/cilium --namespace kube-system
       ```
3. **AWS CNI con Cilium**:
   * Enfoque híbrido que usa Amazon VPC CNI y Cilium juntos
   * VPC CNI gestiona el networking de Pods, y Cilium gestiona las network policies
   *   Método de instalación:

       ```bash
       # Install Cilium in network policy only mode
       helm install cilium cilium/cilium --namespace kube-system \
         --set enableIPv4Masquerade=false \
         --set tunnel=disabled \
         --set installIptablesRules=false \
         --set autoDirectNodeRoutes=false \
         --set policyEnforcementMode=default
       ```

**Ejemplos de Network Policy:**

```yaml
# Default deny policy
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

# Allow communication between specific applications
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

**Verificación de la implementación de Network Policy:**

```bash
# Verify network policy support
kubectl get pods -n kube-system | grep -E 'calico|cilium'

# Apply test network policy
kubectl apply -f test-network-policy.yaml

# Test connectivity
kubectl run -it --rm --restart=Never busybox --image=busybox -- wget -O- --timeout=2 http://service-name
```

**Problemas con otras opciones:**

* **Configuración de AWS security groups**: Los security groups de AWS operan a nivel de instancia EC2 y no pueden usarse para implementar network policies detalladas entre Kubernetes Pods. Aunque la característica SecurityGroupsForPods permite aplicar security groups a Pods, este es un mecanismo diferente de Kubernetes NetworkPolicy.
* **Configuración de AWS Network Firewall**: AWS Network Firewall opera a nivel de VPC y no puede usarse para implementar network policies detalladas entre Kubernetes Pods.
* **VPC Flow Logs habilitado**: VPC Flow Logs se usa para monitorear y registrar tráfico de red, pero no puede usarse para implementar network policies.

Las network policies son una herramienta importante para controlar la comunicación entre microservices y mejorar la seguridad dentro de los clústeres Kubernetes. Para implementar network policies en EKS, debes instalar CNI plugins adicionales como Calico o Cilium.

</details>

4. ¿Cuál es la forma correcta de configurar el cifrado de Secrets en un clúster Amazon EKS?
   * A) Habilitar el cifrado usando una AWS KMS key al crear el clúster EKS
   * B) Migrar Kubernetes Secrets a AWS Secrets Manager
   * C) Codificar todos los Secrets en Base64
   * D) Implementar un encryption sidecar container en el clúster EKS

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: A) Habilitar el cifrado usando una AWS KMS key al crear el clúster EKS**

**Explicación:** La forma correcta de configurar el cifrado de Secrets en un clúster Amazon EKS es habilitar el cifrado usando una AWS KMS (Key Management Service) key al crear el clúster EKS o en un clúster existente. Este método garantiza que Kubernetes Secrets se cifren cuando se almacenan en etcd.

**Pasos para configurar el cifrado de EKS Secrets:**

1.  **Crear una KMS Key o usar una Key existente**:

    ```bash
    # Create KMS key
    aws kms create-key --description "EKS Secrets Encryption Key"

    # Store the created key ID
    KEY_ID=$(aws kms create-key --query KeyMetadata.KeyId --output text)
    ```
2.  **Habilitar el cifrado al crear un nuevo clúster**:

    ```bash
    # Enable encryption using AWS CLI
    aws eks create-cluster \
      --name my-cluster \
      --role-arn arn:aws:iam::123456789012:role/EksClusterRole \
      --resources-vpc-config subnetIds=subnet-12345,subnet-67890 \
      --encryption-config '[{"resources":["secrets"],"provider":{"keyArn":"arn:aws:kms:region:123456789012:key/'$KEY_ID'"}}]'

    # Enable encryption using eksctl
    cat > cluster.yaml << EOF
    apiVersion: eksctl.io/v1alpha5
    kind: ClusterConfig
    metadata:
      name: my-cluster
      region: us-west-2
    secretsEncryption:
      keyARN: arn:aws:kms:us-west-2:123456789012:key/$KEY_ID
    EOF

    eksctl create cluster -f cluster.yaml
    ```
3.  **Habilitar el cifrado en un clúster existente**:

    ```bash
    # For existing clusters, you cannot update the encryption configuration, so you need to create a new cluster and migrate workloads.
    ```
4.  **Verificar la configuración de cifrado**:

    ```bash
    # Check cluster information
    aws eks describe-cluster --name my-cluster --query cluster.encryptionConfig
    ```

**Uso de Secrets cifrados:**

Una vez habilitado el cifrado, el método para crear y usar Secrets no cambia. Todo el cifrado y descifrado lo gestiona automáticamente el EKS control plane.

```yaml
# Create Secret
apiVersion: v1
kind: Secret
metadata:
  name: my-secret
type: Opaque
data:
  username: YWRtaW4=  # base64 encoded "admin"
  password: cGFzc3dvcmQ=  # base64 encoded "password"
```

```bash
# Create Secret
kubectl create secret generic my-secret --from-literal=username=admin --from-literal=password=password

# Verify Secret
kubectl get secret my-secret -o yaml
```

**Configuración de permisos de KMS Key:**

Necesitas configurar permisos adecuados para que el clúster EKS pueda usar la KMS key:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowEKSToUseKMSKey",
      "Effect": "Allow",
      "Principal": {
        "Service": "eks.amazonaws.com"
      },
      "Action": [
        "kms:Encrypt",
        "kms:Decrypt",
        "kms:ReEncrypt*",
        "kms:GenerateDataKey*",
        "kms:DescribeKey"
      ],
      "Resource": "*"
    }
  ]
}
```

**Problemas con otras opciones:**

* **Migrar Kubernetes Secrets a AWS Secrets Manager**: Este es un enfoque posible, pero tiene menos compatibilidad con la API estándar de Kubernetes Secrets y requiere configuración e integración adicionales. Además, todas las aplicaciones deben modificarse para recuperar secretos desde AWS Secrets Manager.
* **Codificar todos los Secrets en Base64**: Kubernetes Secrets ya están codificados en Base64 de forma predeterminada. Sin embargo, Base64 es un método de codificación, no cifrado, y no proporciona seguridad.
* **Implementar un encryption sidecar container en el clúster EKS**: Este no es un enfoque estándar, y agregar sidecars a todos los Pods introduce complejidad. También requiere integración con el Kubernetes API server.

El cifrado de EKS Secrets usando AWS KMS es la forma más eficaz e integrada de proteger Secrets almacenados en etcd. Esto te permite proteger datos confidenciales en reposo y aprovechar las potentes capacidades de gestión de keys de AWS.

</details>

5\. ¿Cuál es la forma correcta de personalizar la configuración de kubelet para worker nodes en un clúster Amazon EKS? - A) Modificar la configuración del clúster en la consola de EKS - B) Usar el parámetro --kubelet-extra-args al crear el node group - C) Usar el comando kubectl edit node - D) Usar AWS Systems Manager para cambiar la configuración del node

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Usar el parámetro --kubelet-extra-args al crear el node group**

**Explicación:** La forma correcta de personalizar la configuración de kubelet para worker nodes en un clúster Amazon EKS es usar el parámetro `--kubelet-extra-args` al crear el node group. Este método permite pasar argumentos adicionales a kubelet cuando se inicializa el node.

**Métodos para personalizar la configuración de kubelet:**

1.  **Uso de Launch Templates con Managed Node Groups**:

    * Personaliza el bootstrap script en la sección user data del launch template.

    ```bash
    #!/bin/bash
    set -o xtrace
    /etc/eks/bootstrap.sh my-cluster \
      --kubelet-extra-args '--max-pods=110 --kube-reserved memory=0.3Gi,cpu=100m --system-reserved memory=0.5Gi,cpu=200m --eviction-hard memory.available<500Mi'
    ```
2. **Creación de Node Groups usando eksctl**:

```bash
# Create node group with kubelet arguments
eksctl create nodegroup \
  --cluster my-cluster \
  --name my-nodegroup \
  --node-type m5.large \
  --nodes 3 \
  --kubelet-extra-args "--max-pods=110 --kube-reserved memory=0.3Gi,cpu=100m"
```

3.  **Uso de archivo de configuración de eksctl**:

    ```yaml
    apiVersion: eksctl.io/v1alpha5
    kind: ClusterConfig
    metadata:
      name: my-cluster
      region: us-west-2
    managedNodeGroups:
      - name: my-nodegroup
        instanceType: m5.large
        minSize: 2
        maxSize: 5
        kubeletExtraArgs:
          max-pods: "110"
          kube-reserved: "memory=0.3Gi,cpu=100m"
          system-reserved: "memory=0.5Gi,cpu=200m"
          eviction-hard: "memory.available<500Mi"
    ```
4.  **Uso de user data script para self-managed node groups**:

    ```bash
    #!/bin/bash
    set -o xtrace
    /etc/eks/bootstrap.sh my-cluster \
      --kubelet-extra-args '--max-pods=110 --node-labels=node.kubernetes.io/role=worker,environment=prod'
    ```

**Parámetros de kubelet comúnmente personalizados:**

1. **max-pods**:
   * Establece el número máximo de Pods por node
   * Ejemplo: `--max-pods=110`
2. **node-labels**:
   * Agrega labels al node
   * Ejemplo: `--node-labels=environment=prod,node-type=worker`
3. **kube-reserved**:
   * Reserva recursos para componentes del sistema Kubernetes
   * Ejemplo: `--kube-reserved=cpu=100m,memory=0.3Gi,ephemeral-storage=1Gi`
4. **system-reserved**:
   * Reserva recursos para daemons del sistema operativo
   * Ejemplo: `--system-reserved=cpu=100m,memory=0.5Gi,ephemeral-storage=1Gi`
5. **eviction-hard**:
   * Establece umbrales estrictos de eviction
   * Ejemplo: `--eviction-hard=memory.available<500Mi,nodefs.available<10%`
6. **cgroup-driver**:
   * Establece el cgroup driver
   * Ejemplo: `--cgroup-driver=systemd`

**Cómo verificar la configuración:**

```bash
# SSH into the node
ssh -i ~/.ssh/id_rsa ec2-user@<node-ip>

# Check kubelet service configuration
sudo systemctl status kubelet
sudo cat /etc/systemd/system/kubelet.service.d/10-kubelet-args.conf

# Check running kubelet process arguments
ps aux | grep kubelet
```

**Problemas con otras opciones:**

* **Modificar la configuración del clúster en la consola de EKS**: Aunque la consola de EKS permite modificar configuraciones a nivel de clúster, no proporciona opciones para modificar directamente la configuración de kubelet de nodes individuales.
* **Usar el comando kubectl edit node**: El comando `kubectl edit node` puede modificar metadatos del objeto node, pero no puede cambiar la configuración de kubelet. La configuración de kubelet se ejecuta como un servicio en el sistema operativo del node y no puede modificarse directamente mediante la Kubernetes API.
* **Usar AWS Systems Manager para cambiar la configuración del node**: AWS Systems Manager puede usarse para ejecutar comandos o cambiar configuraciones en nodes, pero este método se aplica después de que los nodes ya se han creado. Además, después de cambiar la configuración de kubelet, el servicio debe reiniciarse, lo que puede afectar a Pods en ejecución. Por lo tanto, configurar en el momento de creación del node group es más seguro y es el enfoque recomendado.

Personalizar la configuración de kubelet permite optimizar la gestión de recursos del node, la densidad de Pods, las políticas de eviction y más para cumplir con los requisitos de tus workloads. Sin embargo, los cambios deben probarse cuidadosamente, ya que pueden afectar la estabilidad del clúster.

</details>

6. ¿Cuál es el mecanismo recomendado para reemplazar Pod Security Policy en clústeres Amazon EKS?
   * A) AWS Security Hub
   * B) Pod Security Admission o policy engines como Kyverno
   * C) AWS Config Rules
   * D) EKS Security Groups

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Pod Security Admission o policy engines como Kyverno**

**Explicación:** El mecanismo recomendado para reemplazar Pod Security Policy (PSP) en clústeres Amazon EKS es Pod Security Admission o policy engines como Kyverno. A partir de Kubernetes 1.21, PSP quedó deprecated, y fue eliminado por completo en Kubernetes 1.25. Pod Security Admission se introdujo como reemplazo, y policy engines como Kyverno u OPA Gatekeeper también pueden usarse como alternativas.

**Pod Security Admission:**

Pod Security Admission se introdujo como característica beta a partir de Kubernetes 1.23 y se volvió estable en la versión 1.25. Es una característica integrada de Kubernetes que proporciona tres niveles de seguridad (Privileged, Baseline, Restricted).

1.  **Método de configuración**:

    ```yaml
    # Apply Pod Security standards to namespace
    apiVersion: v1
    kind: Namespace
    metadata:
      name: my-namespace
      labels:
        pod-security.kubernetes.io/enforce: restricted
        pod-security.kubernetes.io/audit: restricted
        pod-security.kubernetes.io/warn: restricted
    ```
2. **Niveles de seguridad**:
   * **Privileged**: Sin restricciones, todas las características permitidas
   * **Baseline**: Previene escaladas de privilegios conocidas
   * **Restricted**: Endurecimiento de seguridad fuerte, aplica el principio de privilegio mínimo
3. **Modos**:
   * **enforce**: Rechaza la creación de Pods ante una violación
   * **audit**: Registra violaciones en audit logs
   * **warn**: Muestra mensajes de advertencia ante una violación

**Kyverno:**

Kyverno es un policy engine nativo de Kubernetes que usa políticas basadas en YAML para validar, mutar y generar recursos del clúster.

1.  **Método de instalación**:

    ```bash
    # Install Kyverno using Helm
    helm repo add kyverno https://kyverno.github.io/kyverno/
    helm install kyverno kyverno/kyverno --namespace kyverno --create-namespace
    ```
2.  **Ejemplo de política**:

    ```yaml
    # Policy to prevent privileged containers
    apiVersion: kyverno.io/v1
    kind: ClusterPolicy
    metadata:
      name: disallow-privileged-containers
    spec:
      validationFailureAction: enforce
      rules:
      - name: privileged-containers
        match:
          resources:
            kinds:
            - Pod
        validate:
          message: "Privileged containers are not allowed"
          pattern:
            spec:
              containers:
              - name: "*"
                securityContext:
                  privileged: false
    ```

**OPA Gatekeeper:**

OPA (Open Policy Agent) Gatekeeper es otra solución popular para gestión de políticas en Kubernetes.

1.  **Método de instalación**:

    ```bash
    # Install Gatekeeper
    kubectl apply -f https://raw.githubusercontent.com/open-policy-agent/gatekeeper/master/deploy/gatekeeper.yaml
    ```
2.  **Ejemplo de política**:

    ```yaml
    # ConstraintTemplate definition
    apiVersion: templates.gatekeeper.sh/v1beta1
    kind: ConstraintTemplate
    metadata:
      name: k8spsprivilegedcontainer
    spec:
      crd:
        spec:
          names:
            kind: K8sPSPPrivilegedContainer
      targets:
      - target: admission.k8s.gatekeeper.sh
        rego: |
          package k8spsprivilegedcontainer
          violation[{"msg": msg}] {
            c := input.review.object.spec.containers[_]
            c.securityContext.privileged
            msg := sprintf("Privileged container is not allowed: %v", [c.name])
          }

    # Apply Constraint
    apiVersion: constraints.gatekeeper.sh/v1beta1
    kind: K8sPSPPrivilegedContainer
    metadata:
      name: psp-privileged-container
    spec:
      match:
        kinds:
        - apiGroups: [""]
          kinds: ["Pod"]
    ```

**Recomendaciones de implementación para EKS:**

1. **Habilitar Pod Security Admission**:
   * Disponible de forma predeterminada en EKS 1.23 y superior
   * Aplica labels adecuados a namespaces
2. **Instalar Kyverno o Gatekeeper**:
   * Cuando se necesitan políticas más complejas
   * Cuando se requieren políticas para múltiples tipos de recursos
3. **Migración gradual**:
   * Migra gradualmente de PSP a nuevas soluciones
   * Comienza en modo audit para identificar problemas, luego cambia al modo enforce

**Problemas con otras opciones:**

* **AWS Security Hub**: AWS Security Hub es un servicio para monitorear la postura de seguridad de recursos de AWS, pero no puede usarse para aplicar políticas de seguridad a nivel de Pod en Kubernetes.
* **AWS Config Rules**: AWS Config es un servicio para evaluar configuraciones de recursos de AWS, pero no puede usarse para aplicar políticas de seguridad a nivel de Pod en Kubernetes.
* **EKS Security Groups**: Los EKS Security Groups se usan para controlar tráfico de red y no pueden usarse para restringir contextos de seguridad o privilegios de Pods.

Con la eliminación de Pod Security Policy (PSP), los clústeres EKS deben usar mecanismos alternativos como Pod Security Admission, Kyverno u OPA Gatekeeper para fortalecer la seguridad de Pods. Estas herramientas pueden restringir privileged containers, acceso a host namespaces, montajes host path y más.

</details>

7\. ¿Cuál es el primer paso para configurar IRSA (IAM Roles for Service Accounts) con el fin de integrar la identidad de Pod con AWS IAM en un clúster Amazon EKS? - A) Crear un IAM role - B) Crear una service account - C) Asociar un proveedor OIDC - D) Modificar el manifiesto del Pod

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Asociar un proveedor OIDC**

**Explicación:** El primer paso para configurar IRSA (IAM Roles for Service Accounts) en un clúster Amazon EKS es asociar un proveedor OIDC (OpenID Connect). El proveedor OIDC es necesario para establecer una relación de confianza entre AWS IAM y Kubernetes service accounts. Esto permite que los tokens de Kubernetes service account se conviertan en un mecanismo de autenticación confiable en AWS IAM.

**Pasos de configuración de IRSA en orden:**

1.  **Asociar proveedor OIDC**:

    * Verifica la URL del issuer OIDC del clúster EKS
    * Crea un proveedor OIDC en AWS IAM

    ```bash
    # Check OIDC issuer URL
    aws eks describe-cluster --name my-cluster --query "cluster.identity.oidc.issuer" --output text
    # Example output: https://oidc.eks.us-west-2.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE

    # Associate OIDC provider
    eksctl utils associate-iam-oidc-provider --cluster my-cluster --approve

    # Or use AWS CLI
    aws iam create-open-id-connect-provider \
      --url https://oidc.eks.us-west-2.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE \
      --thumbprint-list 9e99a48a9960b14926bb7f3b02e22da2b0ab7280 \
      --client-id-list sts.amazonaws.com
    ```
2.  **Crear IAM role**:

    * Crea el IAM role que asumirá la service account
    * Incluye el proveedor OIDC y las condiciones de service account en la trust policy

    ```json
    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Effect": "Allow",
          "Principal": {
            "Federated": "arn:aws:iam::123456789012:oidc-provider/oidc.eks.us-west-2.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE"
          },
          "Action": "sts:AssumeRoleWithWebIdentity",
          "Condition": {
            "StringEquals": {
              "oidc.eks.us-west-2.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE:sub": "system:serviceaccount:default:my-service-account"
            }
          }
        }
      ]
    }
    ```
3.  **Crear service account**:

    * Crea una service account con el ARN del IAM role como annotation

    ```yaml
    apiVersion: v1
    kind: ServiceAccount
    metadata:
      name: my-service-account
      namespace: default
      annotations:
        eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/my-role
    ```
4.  **Modificar manifiesto del Pod**:

    * Especifica la service account en el manifiesto del Pod

    ```yaml
    apiVersion: v1
    kind: Pod
    metadata:
      name: my-pod
    spec:
      serviceAccountName: my-service-account
      containers:
      - name: my-container
        image: my-image
    ```

**Configuración simplificada de IRSA usando eksctl:**

eksctl proporciona comandos que automatizan todos los pasos anteriores:

```bash
# Associate OIDC provider
eksctl utils associate-iam-oidc-provider --cluster my-cluster --approve

# Create service account and IAM role
eksctl create iamserviceaccount \
  --name my-service-account \
  --namespace default \
  --cluster my-cluster \
  --attach-policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess \
  --approve
```

**Verificar que IRSA funciona:**

```bash
# Check service account
kubectl get serviceaccount my-service-account -o yaml

# Run test pod
kubectl run -it --rm \
  --image amazon/aws-cli \
  --serviceaccount my-service-account \
  aws-cli -- s3 ls
```

**Problemas con otras opciones:**

* **Crear un IAM role**: Crear un IAM role es el segundo paso en la configuración de IRSA. Primero debe asociarse el proveedor OIDC para que la trust policy del IAM role pueda hacer referencia al proveedor OIDC.
* **Crear una service account**: Crear una service account es el tercer paso en la configuración de IRSA. Primero debe crearse el IAM role para que el ARN del IAM role pueda añadirse como annotation a la service account.
* **Modificar el manifiesto del Pod**: Modificar el manifiesto del Pod es el último paso en la configuración de IRSA. Primero debe crearse la service account para que el Pod pueda hacer referencia a esa service account.

IRSA es una forma segura y eficiente de conceder permisos detallados a servicios de AWS para workloads de Kubernetes. Esto te permite conceder a cada aplicación solo los permisos mínimos necesarios en lugar de compartir IAM roles a nivel de node. El primer paso en la configuración de IRSA es asociar un proveedor OIDC, lo cual es esencial para establecer la relación de confianza entre AWS IAM y Kubernetes service accounts.

</details>

8. ¿Cuál es la forma correcta de habilitar logs del control plane en un clúster Amazon EKS?
   * A) Instalar CloudWatch agent en el EKS control plane
   * B) Habilitar la configuración de logging del clúster mediante AWS CLI o la consola
   * C) Configurar log forwarding usando Fluentd
   * D) Hacer SSH en los nodes del EKS control plane para modificar la configuración de logs

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Habilitar la configuración de logging del clúster mediante AWS CLI o la consola**

**Explicación:** La forma correcta de habilitar logs del control plane en un clúster Amazon EKS es habilitar la configuración de logging del clúster mediante AWS CLI o AWS Management Console. Como EKS es un servicio administrado y el control plane es gestionado por AWS, no puedes acceder a él directamente ni instalar agents. En su lugar, debes configurar logging mediante APIs proporcionadas por AWS.

**Habilitar logs del control plane usando AWS CLI:**

```bash
# Enable all log types
aws eks update-cluster-config \
  --name my-cluster \
  --region us-west-2 \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'

# Enable only specific log types
aws eks update-cluster-config \
  --name my-cluster \
  --region us-west-2 \
  --logging '{"clusterLogging":[{"types":["api","audit"],"enabled":true},{"types":["authenticator","controllerManager","scheduler"],"enabled":false}]}'
```

**Habilitar logs del control plane usando eksctl:**

```bash
# Enable all log types
eksctl utils update-cluster-logging \
  --enable-types api,audit,authenticator,controllerManager,scheduler \
  --cluster my-cluster \
  --region us-west-2

# Enable only specific log types
eksctl utils update-cluster-logging \
  --enable-types api,audit \
  --disable-types authenticator,controllerManager,scheduler \
  --cluster my-cluster \
  --region us-west-2
```

**Habilitar logs del control plane usando AWS Management Console:**

1. Inicia sesión en AWS Management Console.
2. Navega al servicio EKS.
3. Selecciona el clúster objetivo de la lista de clústeres.
4. Selecciona la pestaña "Logging".
5. Haz clic en "Manage".
6. Selecciona los tipos de log que quieres habilitar:
   * API server (api)
   * Audit (audit)
   * Authenticator (authenticator)
   * Controller manager (controllerManager)
   * Scheduler (scheduler)
7. Haz clic en "Save changes".

**Tipos de log disponibles:**

1. **API server (api)**:
   * Logs del Kubernetes API server
   * Contiene información de solicitudes y respuestas de API
2. **Audit (audit)**:
   * Audit logs de todas las actividades del clúster
   * Importante para fines de seguridad y cumplimiento
3. **Authenticator (authenticator)**:
   * Logs de AWS IAM Authenticator
   * Útil para solucionar problemas de autenticación
4. **Controller manager (controllerManager)**:
   * Logs del Kubernetes controller manager
   * Contiene información de gestión de estado de recursos
5. **Scheduler (scheduler)**:
   * Logs del Kubernetes scheduler
   * Contiene información sobre decisiones de scheduling de Pods

**Cómo ver los logs:**

Los logs habilitados se almacenan en CloudWatch Logs y pueden verse en el siguiente log group:

```
/aws/eks/my-cluster/cluster
```

Cada tipo de log se almacena como un log stream separado:

```
kube-apiserver-xxxxx
audit-xxxxx
authenticator-xxxxx
kube-controller-manager-xxxxx
kube-scheduler-xxxxx
```

**Consideraciones de costo:**

* Los logs del control plane están sujetos a los precios de CloudWatch Logs.
* Habilitar todos los tipos de log puede generar una cantidad significativa de logs.
* Para optimización de costos, se recomienda habilitar selectivamente solo los tipos de log que necesitas.
* Puedes gestionar costos estableciendo períodos de retención de logs adecuados.

**Problemas con otras opciones:**

* **Instalar CloudWatch agent en el EKS control plane**: El EKS control plane es gestionado por AWS, por lo que no puedes acceder a él directamente ni instalar agents.
* **Configurar log forwarding usando Fluentd**: Fluentd puede usarse para recopilar logs de worker nodes, pero no puede acceder a logs del EKS control plane.
* **Hacer SSH en los nodes del EKS control plane para modificar la configuración de logs**: Los nodes del EKS control plane son gestionados por AWS, por lo que no puedes hacer SSH en ellos directamente.

Los logs del EKS control plane proporcionan información importante para la solución de problemas del clúster, auditorías de seguridad y cumplimiento. Puedes monitorear eficazmente habilitando selectivamente los tipos de log requeridos mediante AWS CLI o AWS Management Console.

</details>

9. ¿Cuál es la forma correcta de cambiar el instance type de un node group en un clúster Amazon EKS?
   * A) Modificar directamente el instance type del node group en AWS Management Console
   * B) Crear un nuevo node group con el nuevo instance type y migrar workloads
   * C) Modificar especificaciones de node con el comando kubectl edit
   * D) Usar el comando AWS CLI update-nodegroup-config

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Crear un nuevo node group con el nuevo instance type y migrar workloads**

**Explicación:** La forma correcta de cambiar el instance type de un node group en un clúster Amazon EKS es crear un nuevo node group con el nuevo instance type y luego migrar workloads. En EKS managed node groups, no puedes cambiar directamente el instance type después de la creación, por lo que debes crear un nuevo node group, migrar workloads y luego eliminar el node group existente.

**Pasos para cambiar el instance type del node group:**

1.  **Crear nuevo node group**:

    ```bash
    # Create new node group using eksctl
    eksctl create nodegroup \
      --cluster my-cluster \
      --name my-new-nodegroup \
      --node-type m5.large \
      --nodes 3 \
      --nodes-min 1 \
     --nodes-max 5 \
     --node-labels "migration-target=true"
    ```

## Crear nuevo node group usando AWS CLI

aws eks create-nodegroup\
\--cluster-name my-cluster\
\--nodegroup-name my-new-nodegroup\
\--subnets subnet-12345 subnet-67890\
\--instance-types m5.large\
\--scaling-config minSize=1,maxSize=5,desiredSize=3\
\--node-role arn:aws:iam::123456789012:role/EksNodeRole\
\--labels migration-target=true

````

2. **Verificar el estado del nuevo node group**:
 ```bash
 # Check node group status
 aws eks describe-nodegroup \
   --cluster-name my-cluster \
   --nodegroup-name my-new-nodegroup \
   --query "nodegroup.status"

 # Check nodes
 kubectl get nodes --label-columns migration-target
````

3.  **Migrar workloads**:

    **Método 1: Usando Cordoning y Draining**

    ```bash
    # Identify nodes in the existing node group
    OLD_NODES=$(kubectl get nodes -l alpha.eksctl.io/nodegroup-name=my-old-nodegroup -o jsonpath='{.items[*].metadata.name}')

    # Cordon nodes (prevent new pod scheduling)
    for node in $OLD_NODES; do
      kubectl cordon $node
    done

    # Drain nodes (remove existing pods)
    for node in $OLD_NODES; do
      kubectl drain $node --ignore-daemonsets --delete-emptydir-data
    done
    ```

    **Método 2: Usando Pod Selector**

    ```yaml
    # Deploy to new nodes using node selector
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: my-app
    spec:
      template:
        spec:
          nodeSelector:
            migration-target: "true"
    ```

    **Método 3: Blue/Green Deployment**

    * Implementar la nueva versión de Deployment en el nuevo node group
    * Cambiar gradualmente el tráfico a la nueva versión
    * Eliminar la versión existente del Deployment
4.  **Eliminar node group existente**:

    ```bash
    # Delete node group using eksctl
    eksctl delete nodegroup \
      --cluster my-cluster \
      --name my-old-nodegroup

    # Delete node group using AWS CLI
    aws eks delete-nodegroup \
      --cluster-name my-cluster \
      --nodegroup-name my-old-nodegroup
    ```

**Consideraciones durante la migración:**

1.  **Minimizar la interrupción de workloads**:

    * Configura PodDisruptionBudget

    ```yaml
    apiVersion: policy/v1
    kind: PodDisruptionBudget
    metadata:
      name: my-app-pdb
    spec:
      minAvailable: 2  # or maxUnavailable: 1
      selector:
        matchLabels:
          app: my-app
    ```

    * Usa estrategia de rolling update
2. **Requisitos de recursos**:
   * Verifica que el nuevo instance type cumpla con los requisitos de workload
   * Considera requisitos de CPU, memoria, almacenamiento y networking
3. **Stateful workloads**:
   * Verifica la persistencia de datos para workloads que usan persistent volumes
   * Realiza backups si es necesario
4. **Impacto de costo**:
   * Evalúa el impacto de costo del nuevo instance type
   * Los costos aumentan temporalmente mientras ambos node groups se ejecutan simultáneamente durante la migración

**Problemas con otras opciones:**

* **Modificar directamente el instance type del node group en AWS Management Console**: En EKS managed node groups, no puedes modificar directamente el instance type después de la creación.
* **Modificar especificaciones de node con el comando kubectl edit**: kubectl se usa para modificar objetos de la Kubernetes API, pero el instance type subyacente de un node se determina a nivel de infraestructura de AWS y no puede cambiarse mediante kubectl.
* **Usar el comando AWS CLI update-nodegroup-config**: El comando `update-nodegroup-config` puede modificar la configuración de scaling, labels, taints, etc. del node group, pero no puede cambiar el instance type.

Cambiar el instance type de un node group puede ser necesario para optimizar el rendimiento del clúster, reducir costos o cumplir con nuevos requisitos de workload. Crear un nuevo node group y migrar workloads es el enfoque recomendado para cambiar instance types de forma segura mientras se minimiza la interrupción.

</details>

10\. ¿Cuál es la forma correcta de aplicar Kubernetes taints a un node group en un clúster Amazon EKS? - A) Usar el comando kubectl taint - B) Usar el parámetro --taints al crear el node group - C) Configurar taints del node group en AWS Management Console - D) Modificar la configuración de kubelet en el node bootstrap script

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Usar el parámetro --taints al crear el node group**

**Explicación:** La forma correcta de aplicar Kubernetes taints a un node group en un clúster Amazon EKS es usar el parámetro `--taints` al crear el node group. EKS managed node groups proporcionan la capacidad de configurar taints en el momento de creación o durante actualizaciones. Usar este método garantiza que los taints se apliquen consistentemente a todos los nodes del node group y se mantengan cuando los nodes se reemplazan.

**Configuración de taints usando eksctl:**

```bash
# Create node group with taints
eksctl create nodegroup \
  --cluster my-cluster \
  --name tainted-ng \
  --node-type m5.large \
  --nodes 3 \
  --taints "dedicated=gpu:NoSchedule,special=true:PreferNoSchedule"

# Configure taints using configuration file
cat > nodegroup.yaml << EOF
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
  - name: tainted-ng
    instanceType: m5.large
    minSize: 2
    maxSize: 5
    taints:
      - key: dedicated
        value: gpu
        effect: NoSchedule
      - key: special
        value: "true"
        effect: PreferNoSchedule
EOF

eksctl create nodegroup -f nodegroup.yaml
```

**Configuración de taints usando AWS CLI:**

```bash
# Create node group with taints
aws eks create-nodegroup \
  --cluster-name my-cluster \
  --nodegroup-name tainted-ng \
  --subnets subnet-12345 subnet-67890 \
  --instance-types m5.large \
  --scaling-config minSize=2,maxSize=5,desiredSize=3 \
  --node-role arn:aws:iam::123456789012:role/EksNodeRole \
  --taints "key=dedicated,value=gpu,effect=NoSchedule" "key=special,value=true,effect=PreferNoSchedule"

# Update taints on existing node group
aws eks update-nodegroup-config \
  --cluster-name my-cluster \
  --nodegroup-name tainted-ng \
  --taints "addOrUpdateTaints=[{key=dedicated,value=gpu,effect=NoSchedule}],removeTaints=[{key=special}]"
```

**Configuración de taints usando AWS Management Console:**

1. Inicia sesión en AWS Management Console.
2. Navega al servicio EKS.
3. Selecciona el clúster.
4. Selecciona la pestaña "Compute".
5. Haz clic en "Add node group".
6. Introduce los detalles del node group.
7. En la sección "Kubernetes taints", haz clic en "Add taint".
8. Introduce la key, value y effect.
9. Haz clic en "Create".

**Tipos de effect de taint:**

1. **NoSchedule**:
   * Pods sin una toleration coincidente para el taint no se programarán en el node.
   * Los Pods existentes no se ven afectados.
2. **PreferNoSchedule**:
   * Pods sin una toleration coincidente para el taint preferiblemente no se programarán en el node, pero esto no está garantizado.
   * Si no pueden programarse en otros nodes, pueden programarse en este node.
3. **NoExecute**:
   * Pods sin una toleration coincidente para el taint no se programarán en el node.
   * Los Pods ya en ejecución que no tengan una toleration coincidente para el taint serán expulsados.

**Casos de uso comunes para taints:**

1.  **Aislar nodes con hardware especial**:

    ```bash
    # Apply taint to GPU nodes
    eksctl create nodegroup \
      --cluster my-cluster \
      --name gpu-nodes \
      --node-type p3.2xlarge \
      --taints "dedicated=gpu:NoSchedule"

    # Add toleration to GPU workload
    apiVersion: v1
    kind: Pod
    metadata:
      name: gpu-pod
    spec:
      tolerations:
      - key: "dedicated"
        operator: "Equal"
        value: "gpu"
        effect: "NoSchedule"
      containers:
      - name: gpu-container
        image: gpu-image
    ```
2.  **Preparación para mantenimiento de node**:

    ```bash
    # Apply taint to node
    kubectl taint nodes node1 maintenance=planned:NoSchedule

    # Remove taint after maintenance
    kubectl taint nodes node1 maintenance=planned:NoSchedule-
    ```
3.  **Configurar nodes dedicados para workloads específicos**:

    ```bash
    # Node group dedicated to production workloads
    eksctl create nodegroup \
      --cluster my-cluster \
      --name prod-nodes \
      --node-type m5.large \
      --taints "environment=production:NoSchedule"

    # Add toleration to production deployment
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: prod-app
    spec:
      template:
        spec:
          tolerations:
          - key: "environment"
            operator: "Equal"
            value: "production"
            effect: "NoSchedule"
    ```

**Problemas con otras opciones:**

* **Usar el comando kubectl taint**: Puedes usar el comando `kubectl taint` para aplicar taints a nodes individuales, pero este es un cambio temporal y los taints no se mantienen cuando los nodes se reemplazan. También es difícil aplicarlos de forma consistente a todos los nodes de un node group.
* **Configurar taints del node group en AWS Management Console**: También puedes configurar taints al crear un node group en AWS Management Console, pero este es el mismo enfoque que "usar el parámetro --taints al crear node group". Por lo tanto, esta opción podría ser una respuesta correcta, pero técnicamente es lo mismo que configurar taints al crear un node group.
* **Modificar la configuración de kubelet en el node bootstrap script**: Puedes modificar la configuración de kubelet usando la flag `--register-with-taints` en el bootstrap script, pero este es un método complejo y propenso a errores. Tampoco se recomienda para EKS managed node groups.

Los taints son una característica útil de Kubernetes para implementar workloads específicos solo en nodes específicos o excluir ciertos workloads de nodes específicos. Para EKS managed node groups, configurar taints al crear o actualizar el node group es el método más eficaz y manejable.

</details>

## Ejercicios prácticos

### Ejercicio 1: Configuración de IRSA (IAM Roles for Service Accounts)

**Escenario:** Tienes una aplicación ejecutándose en un clúster EKS que necesita acceder a un bucket S3. Siguiendo las mejores prácticas de seguridad, quieres usar IRSA para conceder solo los permisos necesarios a Pods específicos en lugar de compartir el IAM role del node.

**Requisitos:**

1. Asociar proveedor OIDC
2. Crear IAM role con permisos de acceso a S3
3. Crear service account y asociar IAM role
4. Implementar Pod usando la service account
5. Probar acceso a S3

**Solución:**

<details>

<summary>Mostrar solución</summary>

**1. Asociar proveedor OIDC**

```bash
# Get the cluster's OIDC issuer URL
OIDC_PROVIDER=$(aws eks describe-cluster --name my-cluster --query "cluster.identity.oidc.issuer" --output text | sed -e "s/^https:\/\///")

# Check if OIDC provider already exists
aws iam list-open-id-connect-providers | grep $OIDC_PROVIDER

# Create OIDC provider if it doesn't exist
eksctl utils associate-iam-oidc-provider --cluster my-cluster --approve
```

**2. Crear IAM Role con permisos de acceso a S3**

```bash
# Create trust policy
cat > trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):oidc-provider/${OIDC_PROVIDER}"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "${OIDC_PROVIDER}:sub": "system:serviceaccount:default:s3-access-sa"
        }
      }
    }
  ]
}
EOF

# Create IAM role
aws iam create-role --role-name s3-access-role --assume-role-policy-document file://trust-policy.json

# Attach S3 access policy
aws iam attach-role-policy --role-name s3-access-role --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess
```

**3. Crear Service Account y asociar IAM Role**

```bash
# Get IAM role ARN
ROLE_ARN=$(aws iam get-role --role-name s3-access-role --query Role.Arn --output text)

# Create service account
cat > service-account.yaml << EOF
apiVersion: v1
kind: ServiceAccount
metadata:
  name: s3-access-sa
  namespace: default
  annotations:
    eks.amazonaws.com/role-arn: ${ROLE_ARN}
EOF

kubectl apply -f service-account.yaml
```

**4. Implementar Pod usando la Service Account**

```bash
# Deploy test pod
cat > pod.yaml << EOF
apiVersion: v1
kind: Pod
metadata:
  name: s3-access-pod
  namespace: default
spec:
  serviceAccountName: s3-access-sa
  containers:
  - name: aws-cli
    image: amazon/aws-cli:latest
    command:
    - sleep
    - "3600"
  restartPolicy: Never
EOF

kubectl apply -f pod.yaml
```

**5. Probar acceso a S3**

```bash
# Verify the pod is running
kubectl get pod s3-access-pod

# Test listing S3 buckets
kubectl exec -it s3-access-pod -- aws s3 ls

# Test listing objects in a specific S3 bucket
kubectl exec -it s3-access-pod -- aws s3 ls s3://my-bucket

# Verify AWS credentials
kubectl exec -it s3-access-pod -- aws sts get-caller-identity
```

**6. Limpieza**

```bash
# Delete pod
kubectl delete pod s3-access-pod

# Delete service account
kubectl delete serviceaccount s3-access-sa

# Clean up IAM role
aws iam detach-role-policy --role-name s3-access-role --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess
aws iam delete-role --role-name s3-access-role
```

**Explicación adicional:**

1. **Asociación del proveedor OIDC**:
   * El proveedor OIDC establece una relación de confianza entre AWS IAM y Kubernetes service accounts.
   * Esto solo debe configurarse una vez por clúster.
2. **Trust Policy de IAM Role**:
   * La trust policy restringe la asunción del role solo a service accounts específicos en namespaces específicos.
   * La seguridad se mejora usando condition statements.
3. **Annotation de Service Account**:
   * La annotation `eks.amazonaws.com/role-arn` especifica el IAM role que asumirá la service account.
   * Esta annotation es procesada por EKS Pod Identity Webhook.
4. **Variables de entorno**:
   * EKS Pod Identity Webhook inyecta automáticamente las siguientes variables de entorno en el Pod:
     * `AWS_ROLE_ARN`
     * `AWS_WEB_IDENTITY_TOKEN_FILE`
     * `AWS_REGION`
   * Los AWS SDKs usan estas variables de entorno para obtener credenciales.
5. **Principio de privilegio mínimo**:
   * Concede solo los permisos mínimos requeridos por la aplicación.
   * En este ejemplo, solo se concedió permiso de acceso de solo lectura a S3.

Mediante este ejercicio, aprendiste a configurar IRSA para conceder permisos detallados a servicios de AWS solo a Pods específicos que se ejecutan en un clúster EKS. Este enfoque es más seguro que compartir el IAM role del node y sigue el principio de privilegio mínimo.

</details>

\### Ejercicio 2: Fortalecimiento de la seguridad del clúster EKS

**Escenario:** Eres security engineer en tu empresa y necesitas fortalecer la seguridad de un clúster EKS recién creado. El clúster ya está creado y configurado con valores predeterminados. Quieres endurecer el clúster de acuerdo con las mejores prácticas de seguridad.

**Requisitos:**

1. Restringir el acceso al endpoint del clúster
2. Habilitar el cifrado de Secrets
3. Implementar network policies
4. Aplicar Pod Security Standards
5. Habilitar control plane logging

**Solución:**

<details>

<summary>Mostrar solución</summary>

**1. Restringir acceso al endpoint del clúster**

```bash
# Check current cluster endpoint configuration
aws eks describe-cluster --name my-cluster --query "cluster.resourcesVpcConfig.endpointPublicAccess"
aws eks describe-cluster --name my-cluster --query "cluster.resourcesVpcConfig.endpointPrivateAccess"

# Restrict public access (allow only specific CIDR blocks)
aws eks update-cluster-config \
  --name my-cluster \
  --resources-vpc-config endpointPublicAccess=true,endpointPrivateAccess=true,publicAccessCidrs=["203.0.113.0/24","198.51.100.0/24"]

# Or disable public access (private cluster)
aws eks update-cluster-config \
  --name my-cluster \
  --resources-vpc-config endpointPublicAccess=false,endpointPrivateAccess=true
```

**2. Habilitar cifrado de Secrets**

```bash
# Create KMS key
aws kms create-key --description "EKS Secrets Encryption Key"
KEY_ID=$(aws kms create-key --query KeyMetadata.KeyId --output text)

# Add alias to KMS key
aws kms create-alias \
  --alias-name alias/eks-secrets \
  --target-key-id $KEY_ID

# Cannot enable encryption on current cluster, so a new cluster must be created
# Get existing cluster configuration
aws eks describe-cluster --name my-cluster > cluster-config.json

# Create new cluster (more parameters are needed in practice)
aws eks create-cluster \
  --name my-cluster-encrypted \
  --role-arn $(aws eks describe-cluster --name my-cluster --query cluster.roleArn --output text) \
  --resources-vpc-config subnetIds=$(aws eks describe-cluster --name my-cluster --query cluster.resourcesVpcConfig.subnetIds --output text | tr -d '[]" ' | tr ',' ' '),securityGroupIds=$(aws eks describe-cluster --name my-cluster --query cluster.resourcesVpcConfig.securityGroupIds --output text | tr -d '[]" ') \
  --encryption-config '[{"resources":["secrets"],"provider":{"keyArn":"arn:aws:kms:'$(aws configure get region)':'$(aws sts get-caller-identity --query Account --output text)':key/'$KEY_ID'"}}]'
```

**3. Implementar Network Policies**

```bash
# Install Calico
kubectl create namespace tigera-operator
helm repo add projectcalico https://docs.projectcalico.org/charts
helm install calico projectcalico/tigera-operator --namespace tigera-operator

# Create default deny network policy
cat > default-deny.yaml << EOF
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
EOF

kubectl apply -f default-deny.yaml

# Policy to allow communication between specific applications
cat > allow-app-communication.yaml << EOF
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
EOF

kubectl apply -f allow-app-communication.yaml
```

**4. Aplicar Pod Security Standards**

```bash
# Apply Pod Security Standards to namespace
cat > pod-security.yaml << EOF
apiVersion: v1
kind: Namespace
metadata:
  name: restricted-ns
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
EOF

kubectl apply -f pod-security.yaml

# Add labels to existing namespace
kubectl label namespace default \
  pod-security.kubernetes.io/enforce=baseline \
  pod-security.kubernetes.io/audit=restricted \
  pod-security.kubernetes.io/warn=restricted

# Install Kyverno (for additional policy enforcement)
kubectl create namespace kyverno
helm repo add kyverno https://kyverno.github.io/kyverno/
helm install kyverno kyverno/kyverno --namespace kyverno

# Policy to prevent privileged containers
cat > restrict-privileged.yaml << EOF
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: disallow-privileged-containers
spec:
  validationFailureAction: enforce
  rules:
  - name: privileged-containers
    match:
      resources:
        kinds:
        - Pod
    validate:
      message: "Privileged containers are not allowed"
      pattern:
        spec:
          containers:
          - name: "*"
            securityContext:
              privileged: false
EOF

kubectl apply -f restrict-privileged.yaml
```

**5. Habilitar Control Plane Logging**

```bash
# Enable all control plane log types
aws eks update-cluster-config \
  --name my-cluster \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'

# Verify logging status
aws eks describe-cluster --name my-cluster --query "cluster.logging"

# Check logs in CloudWatch Logs
aws logs describe-log-groups --log-group-name-prefix /aws/eks/my-cluster
```

**6. Medidas adicionales de hardening de seguridad**

```bash
# Restrict IAM policy for AWS Load Balancer Controller
cat > alb-controller-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeVpcs",
        "ec2:DescribeSubnets",
        "ec2:DescribeSecurityGroups",
        "elasticloadbalancing:DescribeLoadBalancers",
        "elasticloadbalancing:DescribeTargetGroups",
        "elasticloadbalancing:DescribeListeners"
      ],
      "Resource": "*"
    }
  ]
}
EOF

aws iam create-policy \
  --policy-name EksAlbControllerRestrictedPolicy \
  --policy-document file://alb-controller-policy.json

# Configure node group update for periodic node replacement
aws eks update-nodegroup-config \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup \
  --update-config '{"maxUnavailable": 1}'

# Start node group update
aws eks update-nodegroup-version \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup
```

**Explicación del hardening de seguridad:**

1. **Restringir acceso al endpoint del clúster**:
   * Restringe el acceso al endpoint público a rangos IP específicos o deshabilítalo por completo.
   * Habilita el endpoint privado para permitir acceso al clúster desde dentro de la VPC.
   * Esto previene acceso no autorizado al cluster API server.
2. **Habilitar cifrado de Secrets**:
   * Usa AWS KMS keys para cifrar Kubernetes Secrets almacenados en etcd.
   * Protege datos confidenciales en reposo.
   * Nota: El cifrado no puede habilitarse en clústeres existentes, por lo que necesitas crear un nuevo clúster.
3. **Implementar Network Policies**:
   * Instala Calico para admitir Kubernetes network policies.
   * Aplica políticas default deny para bloquear todo el tráfico no permitido explícitamente.
   * Implementa políticas detalladas que permitan solo la comunicación necesaria.
4. **Aplicar Pod Security Standards**:
   * Aplica Pod Security Standards disponibles en Kubernetes 1.23 y posteriores.
   * Establece restricciones de seguridad a nivel de namespace.
   * Usa policy engines como Kyverno para aplicar políticas de seguridad adicionales.
5. **Habilitar Control Plane Logging**:
   * Envía todos los tipos de log del control plane a CloudWatch Logs.
   * Monitorea la actividad del clúster mediante audit logs.
   * Mantén logs para eventos de seguridad y troubleshooting.

Mediante este ejercicio práctico, aprendiste varios métodos para fortalecer la seguridad de tu clúster EKS. Estas medidas de seguridad ayudan a mejorar la postura de seguridad de tu clúster y a protegerlo contra acceso no autorizado y actividades maliciosas.

</details>

## Temas avanzados

Las siguientes son preguntas sobre temas avanzados en la creación de clústeres Amazon EKS. Esta sección evalúa tu comprensión de conceptos avanzados y mejores prácticas en la creación de clústeres EKS.

1. ¿Cuál de las siguientes opciones NO es un requisito para configurar soporte IPv6 en un clúster Amazon EKS?
   * A) VPC con un bloque CIDR IPv6 asignado
   * B) Versión del CNI plugin que admita IPv6
   * C) Subnets dual-stack
   * D) Instance types solo IPv6

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: D) Instance types solo IPv6**

**Explicación:** "Instance types solo IPv6" NO es un requisito para configurar soporte IPv6 en un clúster Amazon EKS. No existen instance types especiales requeridos para soporte IPv6, ya que la mayoría de los instance types EC2 admiten IPv6. Los requisitos reales son una VPC con un bloque CIDR IPv6 asignado, una versión del CNI plugin que admita IPv6 y subnets dual-stack.

**Requisitos reales para soporte IPv6 en EKS:**

1.  **VPC con un bloque CIDR IPv6 asignado**:

    * Debes asignar un bloque CIDR IPv6 a tu VPC.
    * Esto puede configurarse mediante AWS Management Console o AWS CLI.

    ```bash
    # Assign IPv6 CIDR block to existing VPC
    aws ec2 associate-vpc-cidr-block \
      --vpc-id vpc-12345 \
      --amazon-provided-ipv6-cidr-block
    ```
2.  **Versión del CNI plugin que admita IPv6**:

    * Se requiere Amazon VPC CNI plugin versión 1.10.0 o posterior.
    * Se necesita configuración para soporte IPv6.

    ```bash
    # Check CNI version
    kubectl describe daemonset aws-node --namespace kube-system | grep Image

    # Update CNI
    kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.10.0/config/master/aws-k8s-cni.yaml

    # Enable IPv6
    kubectl set env daemonset aws-node -n kube-system ENABLE_IPV6=true
    ```
3.  **Subnets dual-stack**:

    * Las subnets deben tener asignados bloques CIDR tanto IPv4 como IPv6.
    * El routing IPv6 debe configurarse en la route table.

    ```bash
    # Assign IPv6 CIDR block to subnet
    aws ec2 associate-subnet-cidr-block \
      --subnet-id subnet-12345 \
      --ipv6-cidr-block 2600:1f16:d93:e900::/64

    # Create IPv6 internet gateway
    aws ec2 create-egress-only-internet-gateway --vpc-id vpc-12345
    ```

**Creación de un clúster EKS IPv6:**

```bash
# Create IPv6 cluster using eksctl
cat > ipv6-cluster.yaml << EOF
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: ipv6-cluster
  region: us-west-2
  version: '1.23'
vpc:
  id: vpc-12345
  subnets:
    private:
      us-west-2a:
        id: subnet-12345
      us-west-2b:
        id: subnet-67890
  clusterEndpoints:
    publicAccess: true
    privateAccess: true
kubernetesNetworkConfig:
  ipFamily: IPv6
managedNodeGroups:
  - name: ng-1
    instanceType: m5.large
    desiredCapacity: 2
EOF

eksctl create cluster -f ipv6-cluster.yaml
```

**Verificación de la configuración del clúster IPv6:**

```bash
# Check cluster information
aws eks describe-cluster --name ipv6-cluster --query "cluster.kubernetesNetworkConfig"

# Verify Pod IP assignment
kubectl get pods -o wide

# Verify Service IP assignment
kubectl get services -o wide
```

**Características de clústeres IPv6:**

1. **Asignación de IP de Pod**:
   * Los Pods reciben solo direcciones IPv6.
   * La comunicación dentro del clúster ocurre sobre IPv6.
2. **Asignación de IP de Service**:
   * Los Services ClusterIP usan direcciones IPv6.
   * El service CIDR predeterminado es fd00::/108.
3. **Configuración de DNS**:
   * CoreDNS se configura con direcciones IPv6.
   * La resolución de nombres de Service está disponible mediante registros AAAA.
4. **Comunicación externa**:
   * Se requiere un Egress-Only Internet Gateway para comunicación con internet.
   * Se requiere un load balancer con IPv6 habilitado para comunicación entrante.

**Beneficios de usar IPv6:**

1. **Resolver el agotamiento de direcciones IP**:
   * Supera las limitaciones del espacio de direcciones IPv4.
   * Resuelve problemas de escasez de direcciones IP en clústeres a gran escala.
2. **Networking simplificado**:
   * No se necesita NAT, lo que simplifica la configuración de red.
   * El routing directo puede mejorar el rendimiento de red.
3. **Compatibilidad futura**:
   * Prepara la transición a entornos solo IPv6.
   * Permite aprovechar nuevas características y optimizaciones de networking.

"Instance types solo IPv6" es un concepto inexistente, y la mayoría de los instance types EC2 admiten IPv6. No hay necesidad de seleccionar instance types especiales para configurar IPv6 en EKS.

</details>

2\. ¿Cuál es el principal beneficio de configurar custom networking en un clúster Amazon EKS? - A) Separar el rango de direcciones IP de Pod del VPC CIDR para prevenir conflictos de direcciones IP - B) Reducir el tiempo de creación del clúster - C) Mejorar el rendimiento del control plane - D) Cifrar la comunicación node-to-node

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: A) Separar el rango de direcciones IP de Pod del VPC CIDR para prevenir conflictos de direcciones IP**

**Explicación:** El principal beneficio de configurar custom networking en un clúster Amazon EKS es separar el rango de direcciones IP de Pod del VPC CIDR para prevenir conflictos de direcciones IP. Esta característica facilita la integración con infraestructura de red existente y permite una gestión de direcciones IP más eficiente en clústeres a gran escala.

**Cómo funciona Custom Networking:**

De forma predeterminada, el Amazon VPC CNI plugin asigna direcciones IP secundarias desde la interfaz de red primaria del node para proporcionar direcciones IP a Pods. En este enfoque, las direcciones IP de Pod se asignan desde el rango VPC CIDR. En contraste, custom networking permite asignar direcciones IP de Pod desde un bloque CIDR separado del VPC CIDR.

**Pasos para configurar Custom Networking:**

1.  **Habilitar Custom Networking**:

    ```bash
    # Modify CNI plugin configuration
    kubectl set env daemonset aws-node -n kube-system AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG=true
    ```
2.  **Crear recursos ENIConfig**:

    ```yaml
    # Create ENIConfig for each availability zone
    apiVersion: crd.k8s.amazonaws.com/v1alpha1
    kind: ENIConfig
    metadata:
      name: us-west-2a
    spec:
      subnet: subnet-12345
      securityGroups:
      - sg-12345
    ---
    apiVersion: crd.k8s.amazonaws.com/v1alpha1
    kind: ENIConfig
    metadata:
      name: us-west-2b
    spec:
      subnet: subnet-67890
      securityGroups:
      - sg-12345
    ```
3.  **Habilitar uso de ENIConfig basado en Availability Zone**:

    ```bash
    kubectl set env daemonset aws-node -n kube-system ENI_CONFIG_LABEL_DEF=topology.kubernetes.io/zone
    ```
4.  **Verificar Node Labels**:

    ```bash
    kubectl get nodes --show-labels | grep topology.kubernetes.io/zone
    ```

**Beneficios de Custom Networking:**

1. **Prevención de conflictos de direcciones IP**:
   * Separa el rango de direcciones IP de Pod del VPC CIDR para prevenir conflictos de direcciones IP.
   * Facilita la integración con infraestructura de red existente.
   * Útil para conexiones de peering o VPN entre redes on-premises y VPCs.
2. **Flexibilidad en gestión de direcciones IP**:
   * Permite planificar y gestionar por separado los rangos de direcciones IP de Pod.
   * Permite una gestión de direcciones IP más eficiente en clústeres a gran escala.
3. **Segmentación de red**:
   * Permite segmentación de red colocando Pods en subnets específicas.
   * El control de acceso de red mediante security groups es posible.
4. **Soporte Multi-CIDR**:
   * Se pueden usar múltiples bloques CIDR para expandir el espacio de direcciones IP.
   * Se pueden construir clústeres a gran escala incluso cuando el VPC CIDR existente es limitado.

**Casos de uso para Custom Networking:**

1. **Entornos de red híbridos**:
   * Cuando existe conectividad entre redes on-premises y AWS VPC
   * Cuando debe prevenirse el solapamiento del espacio de direcciones IP
2. **Clústeres a gran escala**:
   * Cuando se ejecuta una gran cantidad de Pods
   * Cuando el rango VPC CIDR es limitado
3. **Entornos multi-tenant**:
   * Cuando se requieren subnets separadas para cada tenant
   * Cuando se necesita aislamiento de red
4. **Requisitos regulatorios**:
   * Cuando las regulaciones requieren colocar workloads específicos en subnets específicas

**Problemas con otras opciones:**

* **Reducir el tiempo de creación del clúster**: Custom networking no afecta el tiempo de creación del clúster y, de hecho, puede aumentar el tiempo de configuración debido a la configuración adicional.
* **Mejorar el rendimiento del control plane**: Custom networking solo afecta el networking del data plane (worker nodes y Pods) y no impacta directamente el rendimiento del control plane.
* **Cifrar la comunicación node-to-node**: Custom networking solo cambia cómo se asignan las direcciones IP y no está relacionado con el cifrado de comunicación node-to-node. El cifrado de comunicación node-to-node debe implementarse mediante mecanismos de seguridad separados (por ejemplo, características de cifrado de Calico o Cilium).

Custom networking es una característica potente que permite una configuración más flexible del networking de clústeres EKS, pero es compleja de configurar y puede implicar overhead de gestión adicional, por lo que debe usarse solo cuando realmente sea necesario.

</details>

3\. ¿Cuál de las siguientes opciones NO es un requisito para admitir Windows worker nodes en un clúster Amazon EKS? - A) Se requieren al menos 2 Amazon Linux-based managed node groups - B) Add-ons VPC-CNI, kube-proxy y CoreDNS instalados - C) AMI Windows Server 2019 o posterior - D) Versión del clúster 1.14 o superior

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: A) Se requieren al menos 2 Amazon Linux-based managed node groups**

**Explicación:** Para admitir Windows worker nodes en un clúster Amazon EKS, se requiere al menos 1 (no 2 o más) Amazon Linux-based managed node group. Esto se debe a que Pods esenciales del sistema como CoreDNS deben ejecutarse en Linux nodes. Sin embargo, es incorrecto que se requieran al menos 2 Linux node groups.

**Requisitos reales para soporte de Windows Worker Node en EKS:**

1.  **Linux Node Group requerido**:

    * Se requiere al menos 1 Linux node en el clúster.
    * System Pods como CoreDNS, VPC CNI plugin y kube-proxy solo se ejecutan en Linux nodes.

    ```bash
    # Create Linux node group
    eksctl create nodegroup \
      --cluster my-cluster \
      --name linux-ng \
      --node-type m5.large \
      --nodes 2
    ```
2.  **Add-ons VPC-CNI, kube-proxy y CoreDNS instalados**:

    * Estos add-ons son componentes esenciales de un clúster EKS.
    * Pueden requerirse versiones específicas o superiores para soporte de Windows node.

    ```bash
    # Check add-on versions
    aws eks describe-addon-versions \
      --addon-name vpc-cni \
      --kubernetes-version 1.23

    # Update add-on
    aws eks update-addon \
      --cluster-name my-cluster \
      --addon-name vpc-cni \
      --addon-version v1.10.4-eksbuild.1
    ```
3.  **AMI Windows Server 2019 o posterior**:

    * Los Windows worker nodes deben usar una AMI Windows Server 2019 o posterior.
    * Se recomienda usar una AMI Windows optimizada para EKS.

    ```bash
    # Create Windows node group
    eksctl create nodegroup \
      --cluster my-cluster \
      --name windows-ng \
      --node-type m5.large \
      --nodes 2 \
      --node-ami-family WindowsServer2019FullContainer
    ```
4.  **Versión del clúster 1.14 o superior**:

    * El soporte de Windows node fue soportado oficialmente a partir de Kubernetes 1.14.
    * Se recomienda usar una versión superior para obtener las características más recientes.

    ```bash
    # Check cluster version
    aws eks describe-cluster --name my-cluster --query "cluster.version"
    ```

**Pasos para habilitar soporte Windows:**

1.  **Habilitar soporte Windows**:

    ```bash
    # Enable Windows support
    kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/vpc-resource-controller.yaml

    kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/vpc-admission-webhook.yaml
    ```
2.  **Crear Windows Node Group**:

    ```bash
    # Create Windows node group using eksctl
    eksctl create nodegroup \
      --cluster my-cluster \
      --name windows-ng \
      --node-type m5.large \
      --nodes 2 \
      --node-ami-family WindowsServer2019FullContainer
    ```
3.  **Verificar Windows Nodes**:

    ```bash
    # Verify nodes
    kubectl get nodes -o wide

    # Verify Windows node labels
    kubectl get nodes -l kubernetes.io/os=windows
    ```

**Ejemplo de Deployment de Windows Container:**

```yaml
# Windows Pod deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: windows-server-iis
spec:
  selector:
    matchLabels:
      app: windows-server-iis
      tier: backend
      track: stable
  replicas: 2
  template:
    metadata:
      labels:
        app: windows-server-iis
        tier: backend
        track: stable
    spec:
      nodeSelector:
        kubernetes.io/os: windows
      containers:
      - name: windows-server-iis
        image: mcr.microsoft.com/windows/servercore:ltsc2019
        ports:
        - containerPort: 80
        command:
        - powershell.exe
        - -command
        - "Add-WindowsFeature Web-Server; Invoke-WebRequest -UseBasicParsing -Uri 'https://dotnetbinaries.blob.core.windows.net/servicemonitor/2.0.1.6/ServiceMonitor.exe' -OutFile 'C:\\ServiceMonitor.exe'; echo '<html><body><br/><br/><center><h1>Hello from Windows Container</h1></center></body></html>' > C:\\inetpub\\wwwroot\\default.html; C:\\ServiceMonitor.exe 'w3svc';"
```

**Limitaciones de Windows Node:**

1. **Limitaciones de networking**:
   * Windows nodes no admiten los modos HostPort y HostNetwork.
   * Windows nodes no admiten NodeLocal DNSCache.
2. **Limitaciones de almacenamiento**:
   * Windows nodes solo admiten ciertos storage drivers.
   * Hay limitaciones en montajes host path volume.
3. **Container Runtime**:
   * Windows nodes solo admiten el runtime containerd.
   * Linux containers no pueden ejecutarse en Windows nodes.
4. **Limitaciones de características**:
   * Algunas características de Kubernetes no son compatibles con Windows nodes.
   * Hay limitaciones en privileged containers, process namespace sharing, etc.

Para admitir Windows worker nodes en EKS, se requiere al menos un Linux node group, pero no son obligatorios dos o más Linux node groups. Por lo tanto, "se requieren al menos 2 Amazon Linux-based managed node groups" no es un requisito preciso.

</details>

3\. ¿Cuál de las siguientes opciones NO es un requisito para admitir Windows worker nodes en un clúster Amazon EKS? - A) Se requieren al menos 2 Amazon Linux-based managed node groups - B) Instalación de add-ons VPC-CNI, kube-proxy y CoreDNS - C) Uso de AMI Windows Server 2019 o posterior - D) Versión del clúster 1.14 o posterior

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: A) Se requieren al menos 2 Amazon Linux-based managed node groups**

**Explicación:** Para admitir Windows worker nodes en un clúster Amazon EKS, se requiere al menos un (no dos o más) Amazon Linux-based managed node group. Esto se debe a que Pods esenciales del sistema como CoreDNS deben ejecutarse en Linux nodes. Sin embargo, requerir al menos dos Linux node groups no es preciso.

**Requisitos reales para soporte de Windows Worker Node en EKS:**

1.  **Linux Node Group requerido**:

    * El clúster requiere al menos un Linux node.
    * System Pods como CoreDNS, VPC CNI plugin y kube-proxy solo se ejecutan en Linux nodes.

    ```bash
    # Create Linux node group
    eksctl create nodegroup \
      --cluster my-cluster \
      --name linux-ng \
      --node-type m5.large \
      --nodes 2
    ```
2.  **Instalación de add-ons VPC-CNI, kube-proxy y CoreDNS**:

    * Estos add-ons son componentes fundamentales de un clúster EKS.
    * Pueden requerirse versiones específicas o superiores para soporte de Windows node.

    ```bash
    # Check add-on versions
    aws eks describe-addon-versions \
      --addon-name vpc-cni \
      --kubernetes-version 1.23

    # Update add-on
    aws eks update-addon \
      --cluster-name my-cluster \
      --addon-name vpc-cni \
      --addon-version v1.10.4-eksbuild.1
    ```
3.  **Uso de AMI Windows Server 2019 o posterior**:

    * Los Windows worker nodes deben usar una AMI Windows Server 2019 o posterior.
    * Se recomienda usar una AMI Windows optimizada para EKS.

    ```bash
    # Create Windows node group
    eksctl create nodegroup \
      --cluster my-cluster \
      --name windows-ng \
      --node-type m5.large \
      --nodes 2 \
      --node-ami-family WindowsServer2019FullContainer
    ```
4.  **Versión del clúster 1.14 o posterior**:

    * El soporte de Windows node estuvo disponible de forma general a partir de Kubernetes 1.14.
    * Se recomienda usar una versión superior para obtener las características más recientes.

    ```bash
    # Check cluster version
    aws eks describe-cluster --name my-cluster --query "cluster.version"
    ```

**Pasos para habilitar soporte Windows:**

1.  **Habilitar soporte Windows**:

    ```bash
    # Enable Windows support
    kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/vpc-resource-controller.yaml

    kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/vpc-admission-webhook.yaml
    ```
2.  **Crear Windows Node Group**:

    ```bash
    # Create Windows node group using eksctl
    eksctl create nodegroup \
      --cluster my-cluster \
      --name windows-ng \
      --node-type m5.large \
      --nodes 2 \
      --node-ami-family WindowsServer2019FullContainer
    ```
3.  **Verificar Windows Nodes**:

    ```bash
    # Verify nodes
    kubectl get nodes -o wide

    # Verify Windows node labels
    kubectl get nodes -l kubernetes.io/os=windows
    ```

**Ejemplo de Deployment de Windows Container:**

```yaml
# Windows Pod deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: windows-server-iis
spec:
  selector:
    matchLabels:
      app: windows-server-iis
      tier: backend
      track: stable
  replicas: 2
  template:
    metadata:
      labels:
        app: windows-server-iis
        tier: backend
        track: stable
    spec:
      nodeSelector:
        kubernetes.io/os: windows
      containers:
      - name: windows-server-iis
        image: mcr.microsoft.com/windows/servercore:ltsc2019
        ports:
        - containerPort: 80
        command:
        - powershell.exe
        - -command
        - "Add-WindowsFeature Web-Server; Invoke-WebRequest -UseBasicParsing -Uri 'https://dotnetbinaries.blob.core.windows.net/servicemonitor/2.0.1.6/ServiceMonitor.exe' -OutFile 'C:\\ServiceMonitor.exe'; echo '<html><body><br/><br/><center><h1>Hello from Windows Container</h1></center></body></html>' > C:\\inetpub\\wwwroot\\default.html; C:\\ServiceMonitor.exe 'w3svc';"
```

**Limitaciones de Windows Node:**

1. **Limitaciones de networking**:
   * Windows nodes no admiten los modos HostPort y HostNetwork.
   * Windows nodes no admiten NodeLocal DNSCache.
2. **Limitaciones de almacenamiento**:
   * Windows nodes solo admiten ciertos storage drivers.
   * Hay limitaciones en montajes host path volume.
3. **Container Runtime**:
   * Windows nodes solo admiten el runtime containerd.
   * Linux containers no pueden ejecutarse en Windows nodes.
4. **Limitaciones de características**:
   * Algunas características de Kubernetes no son compatibles con Windows nodes.
   * Hay limitaciones en privileged containers, process namespace sharing, etc.

Para admitir Windows worker nodes en EKS, se requiere al menos un Linux node group, pero no son obligatorios dos o más Linux node groups. Por lo tanto, "se requieren al menos 2 Amazon Linux-based managed node groups" no es un requisito preciso.

</details>

4. ¿Cuál es la forma más efectiva de proteger el Instance Metadata Service (IMDS) de node groups en un clúster Amazon EKS?
   * A) Deshabilitar IMDSv1 y requerir IMDSv2
   * B) Restringir el acceso a 169.254.169.254 con reglas de security group
   * C) Establecer permisos restrictivos en el node IAM role
   * D) Asociar IAM roles a Pod service accounts

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: A) Deshabilitar IMDSv1 y requerir IMDSv2**

**Explicación:** La forma más efectiva de proteger el Instance Metadata Service (IMDS) de node groups en un clúster Amazon EKS es deshabilitar IMDSv1 y requerir IMDSv2. IMDSv2 usa solicitudes basadas en sesión para proporcionar características de seguridad mejoradas que protegen contra Server-Side Request Forgery (SSRF) y vulnerabilidades similares.

**Importancia de la seguridad de IMDS:**

El Instance Metadata Service proporciona información importante sobre instancias EC2, incluidas credenciales de IAM role. El acceso no autorizado a este servicio puede provocar escalada de privilegios y brechas de seguridad. En entornos Kubernetes, el riesgo de seguridad aumenta porque los Pods pueden acceder al IMDS del node.

**Cómo configurar IMDSv2:**

1.  **Configurar IMDSv2 usando Launch Template**:

    ```bash
    # Create launch template
    aws ec2 create-launch-template \
      --launch-template-name eks-imdsv2-template \
      --version-description "IMDSv2 required" \
      --launch-template-data '{
        "MetadataOptions": {
          "HttpTokens": "required",
          "HttpPutResponseHopLimit": 1,
          "HttpEndpoint": "enabled"
        }
      }'

    # Create node group using launch template
    eksctl create nodegroup \
      --cluster my-cluster \
      --name ng-imdsv2 \
      --node-type m5.large \
      --nodes 3 \
      --launch-template-name eks-imdsv2-template \
      --launch-template-version 1
    ```
2.  **Configurar IMDSv2 usando archivo de configuración de eksctl**:

    ```yaml
    apiVersion: eksctl.io/v1alpha5
    kind: ClusterConfig
    metadata:
      name: my-cluster
      region: us-west-2
    managedNodeGroups:
      - name: ng-imdsv2
        instanceType: m5.large
        minSize: 2
        maxSize: 5
        disableIMDSv1: true
        metadataOptions:
          httpTokens: required
          httpPutResponseHopLimit: 1
    ```
3.  **Modificar Node Groups existentes**: Para cambiar la configuración de IMDS de node groups existentes, necesitas crear un nuevo node group y migrar workloads. La configuración de IMDS de instancias EC2 existentes puede modificarse de la siguiente manera:

    ```bash
    aws ec2 modify-instance-metadata-options \
      --instance-id i-1234567890abcdef0 \
      --http-tokens required \
      --http-put-response-hop-limit 1 \
      --http-endpoint enabled
    ```

**Beneficios de seguridad de IMDSv2:**

1. **Autenticación basada en sesión**:
   * IMDSv2 usa tokens generados mediante solicitudes PUT para autenticar solicitudes posteriores.
   * Estos tokens son válidos solo por un tiempo limitado.
2. **Prevención de ataques SSRF**:
   * Previene el acceso a metadata mediante vulnerabilidades Server-Side Request Forgery (SSRF).
   * No se puede acceder a metadata sin un token.
3. **Configuración de hop limit**:
   * Establecer el HTTP PUT response hop limit evita que las solicitudes de metadata sean redirigidas fuera de la instancia.
   * El valor predeterminado es 1, asegurando que las solicitudes solo se procesen dentro de la instancia.

**Medidas adicionales de seguridad de IMDS:**

1.  **Deshabilitar IMDS por completo**: Si IMDS no es necesario para ciertos workloads, puede deshabilitarse por completo:

    ```yaml
    metadataOptions:
      httpEndpoint: disabled
    ```
2.  **Bloquear acceso de Pods a IMDS**: Si los Pods no están usando host networking, puedes agregar reglas iptables para bloquear el acceso a IMDS:

    ```bash
    iptables -t nat -A PREROUTING -d 169.254.169.254/32 -i eth0 -p tcp -m tcp --dport 80 -j DNAT --to-destination 127.0.0.1:1
    ```
3. **Usar IRSA**: Usa IAM Roles for Service Accounts (IRSA) para proporcionar a los Pods los permisos de AWS necesarios y eliminar la dependencia del IMDS del node.

**Problemas con otras opciones:**

* **Restringir el acceso a 169.254.169.254 con reglas de security group**: Los security groups controlan el tráfico que llega desde fuera de la instancia, pero IMDS se accede desde dentro de la instancia, por lo que no puede restringirse con security groups.
* **Establecer permisos restrictivos en el node IAM role**: Esta es una buena práctica de seguridad, pero no fortalece la seguridad de IMDS en sí. Si un atacante puede acceder a IMDS, incluso permisos limitados pueden ser explotados.
* **Asociar IAM roles a Pod service accounts**: IRSA es una buena forma de asegurar que los Pods no dependan del IMDS del node, pero no fortalece directamente la seguridad del IMDS del node en sí.

Deshabilitar IMDSv1 y requerir IMDSv2 es la forma más efectiva de proteger el metadata service de los EKS nodes. Esta es una mejor práctica de seguridad de AWS y es especialmente importante en entornos Kubernetes multi-tenant.

</details>

5. ¿Cuál de las siguientes opciones NO es un propósito principal de personalizar bootstrap scripts al crear node groups en un clúster Amazon EKS?
   * A) Modificar componentes del cluster control plane
   * B) Instalar software adicional
   * C) Ajustar parámetros del kernel
   * D) Establecer node labels y taints

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: A) Modificar componentes del cluster control plane**

**Explicación:** El propósito principal de personalizar bootstrap scripts al crear node groups en un clúster Amazon EKS NO es modificar componentes del cluster control plane. EKS es un servicio administrado donde el control plane es gestionado por AWS y los usuarios no pueden modificarlo directamente. Los bootstrap scripts solo pueden modificar configuraciones de worker nodes.

**Casos de uso reales para Bootstrap Scripts:**

1.  **Instalar software adicional**:

    * Monitoring agents (CloudWatch Agent, Prometheus Node Exporter, etc.)
    * Logging tools (Fluentd, Fluent Bit, etc.)
    * Security tools (Falco, Sysdig, etc.)
    * Herramientas de optimización de rendimiento

    ```bash
    #!/bin/bash
    # Install CloudWatch agent
    wget https://s3.amazonaws.com/amazoncloudwatch-agent/amazon_linux/amd64/latest/amazon-cloudwatch-agent.rpm
    rpm -U amazon-cloudwatch-agent.rpm

    # Create configuration file
    cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << 'EOF'
    {
      "metrics": {
        "metrics_collected": {
          "mem": {
            "measurement": ["mem_used_percent"]
          },
          "swap": {
            "measurement": ["swap_used_percent"]
          }
        }
      }
    }
    EOF

    # Start agent
    /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json -s
    ```
2.  **Ajustar parámetros del kernel**:

    * Optimización de configuración de red
    * Configuraciones de gestión de memoria
    * Configuraciones de file system e I/O

    ```bash
    #!/bin/bash
    # Adjust kernel parameters
    cat > /etc/sysctl.d/99-kubernetes.conf << EOF
    net.ipv4.ip_forward = 1
    net.bridge.bridge-nf-call-iptables = 1
    net.ipv4.tcp_keepalive_time = 600
    net.ipv4.tcp_max_syn_backlog = 40000
    net.core.somaxconn = 40000
    net.core.netdev_max_backlog = 40000
    vm.max_map_count = 262144
    EOF

    # Apply changes
    sysctl --system
    ```
3.  **Establecer Node Labels y Taints**:

    * Establecer labels de rol de node
    * Establecer labels de características de hardware
    * Establecer taints para workloads específicos

    ```bash
    #!/bin/bash
    # Execute EKS bootstrap script
    /etc/eks/bootstrap.sh my-cluster \
      --kubelet-extra-args '--node-labels=node.kubernetes.io/role=worker,environment=prod,node-type=compute --register-with-taints=dedicated=compute:NoSchedule'
    ```
4.  **Configuración de disco y file system**:

    * Montar volúmenes adicionales
    * Optimización de file system
    * Configuración de almacenamiento temporal

    ```bash
    #!/bin/bash
    # Format and mount additional EBS volume
    mkfs -t xfs /dev/nvme1n1
    mkdir -p /data
    mount /dev/nvme1n1 /data
    echo "/dev/nvme1n1 /data xfs defaults 0 0" >> /etc/fstab
    ```
5.  **Configuración de seguridad**:

    * Establecer reglas de firewall
    * Configuraciones de security hardening
    * Configuración de log audit

    ```bash
    #!/bin/bash
    # Set firewall rules
    iptables -A INPUT -p tcp --dport 22 -s 10.0.0.0/8 -j ACCEPT
    iptables -A INPUT -p tcp --dport 22 -j DROP

    # Security hardening settings
    sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
    systemctl restart sshd
    ```

**Cómo implementar Bootstrap Scripts:**

1.  **User Data Script usando Launch Template**:

    ```bash
    # Create launch template
    aws ec2 create-launch-template \
      --launch-template-name eks-custom-bootstrap \
      --version-description "Custom bootstrap script" \
      --launch-template-data '{
        "UserData": "BASE64_ENCODED_USER_DATA_SCRIPT"
      }'

    # Create node group using launch template
    eksctl create nodegroup \
      --cluster my-cluster \
      --name custom-ng \
      --node-type m5.large \
      --nodes 3 \
      --launch-template-name eks-custom-bootstrap \
      --launch-template-version 1
    ```
2.  **User Data Script usando archivo de configuración de eksctl**:

    ```yaml
    apiVersion: eksctl.io/v1alpha5
    kind: ClusterConfig
    metadata:
      name: my-cluster
      region: us-west-2
    managedNodeGroups:
      - name: custom-ng
        instanceType: m5.large
        minSize: 2
        maxSize: 5
        preBootstrapCommands:
          - "echo 'net.ipv4.ip_forward = 1' >> /etc/sysctl.d/99-kubernetes.conf"
          - "sysctl --system"
        kubeletExtraArgs:
          node-labels: "environment=prod,node-type=compute"
    ```

**Componentes del Cluster Control Plane:**

Los componentes del control plane de un clúster EKS son gestionados por AWS y no pueden modificarse mediante bootstrap scripts:

* API Server
* Controller Manager
* Scheduler
* etcd
* CoreDNS

Para modificar estos componentes, debes configurarlos a nivel de clúster mediante APIs proporcionadas por AWS. Por ejemplo, control plane logging puede configurarse de la siguiente manera:

```bash
aws eks update-cluster-config \
  --name my-cluster \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'
```

El bootstrap script solo puede modificar configuraciones de worker node y no puede modificar componentes del cluster control plane. Por lo tanto, "modificar componentes del cluster control plane" no es un propósito principal del bootstrap script.

</details>
