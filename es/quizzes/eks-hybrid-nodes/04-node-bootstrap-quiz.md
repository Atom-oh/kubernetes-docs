# Cuestionario sobre bootstrapping de nodos de EKS Hybrid Nodes

> **Documento relacionado**: [Bootstrapping de nodos](../../eks-hybrid-nodes/04-node-bootstrap.md)

## Preguntas de opción múltiple

### 1. ¿Cuál es el rol principal de nodeadm?

A. Crear clusters de EKS
B. Instalar y realizar el bootstrapping de componentes del nodo como kubelet y containerd
C. Tomar decisiones de programación de Pods
D. Gestionar políticas de red del cluster

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Instalar y realizar el bootstrapping de componentes del nodo como kubelet y containerd**

**Explicación:**
nodeadm es la herramienta oficial para el bootstrapping de nodos de EKS. Instala y configura los componentes necesarios, incluidos kubelet, containerd y aws-iam-authenticator.

```bash
# Install nodeadm
curl -L -o nodeadm https://github.com/awslabs/amazon-eks-ami/releases/download/nodeadm-v0.1.0/nodeadm-linux-amd64
chmod +x nodeadm
sudo mv nodeadm /usr/local/bin/

# Initialize node with nodeadm
sudo nodeadm init --config-source file://nodeadm-config.yaml
```

**Características de nodeadm:**
- Instalación de componentes de Kubernetes (kubelet, containerd)
- Configuración de AWS IAM Authenticator
- Bootstrapping de certificados de kubelet
- Configuración de labels y taints de Node

</details>

### 2. ¿Cuáles son las 3 piezas de información del cluster requeridas al inicializar un Hybrid Node con nodeadm?

A. Nombre del cluster, ID de VPC, ID de Subnet
B. Nombre del cluster, endpoint del servidor API, certificado de CA
C. Nombre del cluster, rol de IAM, Security group
D. Nombre del cluster, Región, Availability zone

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Nombre del cluster, endpoint del servidor API, certificado de CA**

**Explicación:**
Elementos requeridos en el archivo de configuración de nodeadm:

```yaml
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  cluster:
    name: my-cluster                    # Required 1
    region: us-west-2
    apiServerEndpoint: https://xxxxx.eks.amazonaws.com  # Required 2
    certificateAuthority: LS0tLS1CRUdJTi...             # Required 3
```

```bash
# Get required information from EKS
aws eks describe-cluster --name my-cluster \
  --query "cluster.{name:name,endpoint:endpoint,ca:certificateAuthority.data}" \
  --output json
```

</details>

### 3. ¿Qué método de autenticación se usa para IAM en EKS Hybrid Nodes?

A. Tokens estáticos
B. Solo certificados x509
C. IAM Roles Anywhere o credenciales de usuario de IAM
D. Autenticación LDAP

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. IAM Roles Anywhere o credenciales de usuario de IAM**

**Explicación:**
EKS Hybrid Nodes requiere autenticación de AWS IAM desde on-premises. IAM Roles Anywhere permite usar roles de IAM desde servidores on-premises.

```bash
# Create IAM Roles Anywhere Trust Anchor
aws rolesanywhere create-trust-anchor \
  --name hybrid-nodes-anchor \
  --source "sourceType=CERTIFICATE_BUNDLE,sourceData={x509CertificateData=$CERT_DATA}"

# Create IAM Roles Anywhere Profile
aws rolesanywhere create-profile \
  --name hybrid-node-profile \
  --role-arns arn:aws:iam::123456789012:role/HybridNodeRole \
  --duration-seconds 3600
```

```yaml
# Using IAM Roles Anywhere in nodeadm Configuration
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  iam:
    mode: rolesAnywhere
    rolesAnywhere:
      trustAnchorArn: arn:aws:rolesanywhere:us-west-2:123456789012:trust-anchor/xxxxx
      profileArn: arn:aws:rolesanywhere:us-west-2:123456789012:profile/xxxxx
      roleArn: arn:aws:iam::123456789012:role/HybridNodeRole
```

</details>

### 4. ¿Cuál NO es una opción válida de configuración de kubelet en NodeConfig?

A. maxPods
B. clusterDNS
C. clusterCIDR
D. podScheduler

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D. podScheduler**

**Explicación:**
`podScheduler` no es una opción de configuración de kubelet en NodeConfig. La programación la gestiona kube-scheduler en el control plane.

```yaml
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  kubelet:
    config:
      maxPods: 110              # Maximum Pods per node
      clusterDNS:               # Cluster DNS servers
        - 10.100.0.10
      clusterDomain: cluster.local
      evictionHard:             # Pod eviction thresholds
        memory.available: "100Mi"
        nodefs.available: "10%"
    flags:
      - "--node-labels=location=onprem"
      - "--register-with-taints=dedicated=hybrid:NoSchedule"
```

</details>

### 5. ¿Qué componentes se requieren al registrar un Hybrid Node usando SSM (Systems Manager)?

A. SSM Agent y código de activación
B. Solo CloudWatch Agent
C. Solo AWS CLI
D. Perfil de instancia EC2

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A. SSM Agent y código de activación**

**Explicación:**
Para gestionar servidores on-premises con SSM, debes instalar SSM Agent y registrarlos mediante activación híbrida.

```bash
# 1. Create SSM hybrid activation (AWS Console or CLI)
aws ssm create-activation \
  --default-instance-name "hybrid-node" \
  --iam-role service-role/AmazonEC2RunCommandRoleForManagedInstances \
  --registration-limit 10

# Output: ActivationId, ActivationCode

# 2. Install and register SSM Agent on on-premises server
sudo amazon-ssm-agent -register \
  -code "activation-code" \
  -id "activation-id" \
  -region "us-west-2"

# 3. Start SSM Agent
sudo systemctl start amazon-ssm-agent
sudo systemctl enable amazon-ssm-agent
```

```yaml
# Use SSM mode in nodeadm
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  hybrid:
    ssm: true
    ssmActivationId: "activation-id"
    ssmActivationCode: "activation-code"
```

</details>

### 6. ¿Cuál es el propósito de proporcionar el certificado de CA en la configuración de nodeadm?

A. Cifrar el tráfico entre nodos
B. Que kubelet verifique la confiabilidad del servidor API
C. Configurar mTLS entre Pods
D. Autenticación del registry Harbor

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Que kubelet verifique la confiabilidad del servidor API**

**Explicación:**
El certificado de CA (Certificate Authority) lo usa kubelet para verificar la confiabilidad del servidor EKS API al conectarse.

```yaml
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  cluster:
    name: my-cluster
    apiServerEndpoint: https://xxxxx.eks.amazonaws.com
    certificateAuthority: |
      LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUM...
      # Base64 encoded CA certificate
```

**Flujo de certificados:**
```
kubelet ----TLS connection----> EKS API Server
   |                              |
   |-- Verify server cert with CA |
   |                              |
   |<-- Issue client certificate --|
```

```bash
# Get CA certificate from EKS cluster
aws eks describe-cluster --name my-cluster \
  --query "cluster.certificateAuthority.data" \
  --output text | base64 -d > ca.crt

# View CA certificate contents
openssl x509 -in ca.crt -text -noout
```

</details>

### 7. Cuando un nodo no logra unirse al cluster después de ejecutar nodeadm init, ¿qué debe revisarse primero?

A. Estado de despliegue de Pods
B. Logs de kubelet y conectividad de red
C. Configuración de Deployment
D. Contenido de ConfigMap

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Logs de kubelet y conectividad de red**

**Explicación:**
Cuando falla la unión de un nodo, primero revisa los logs de kubelet y la conectividad de red.

```bash
# 1. Check kubelet service status
sudo systemctl status kubelet

# 2. Check kubelet logs
sudo journalctl -u kubelet -f

# 3. Check for common error patterns
sudo journalctl -u kubelet | grep -E "error|failed|unable"

# 4. Check resource status (memory, disk)
free -h
df -h

# 5. Test network connectivity
curl -vk https://<eks-api-endpoint>:443

# 6. Check DNS resolution
nslookup <eks-api-endpoint>

# 7. Check firewall rules
sudo iptables -L -n | grep 443

# 8. Check nodeadm status
sudo nodeadm status
```

**Causas comunes de fallo:**
- Endpoint del servidor API inaccesible (firewall)
- Certificado de CA no coincidente
- Fallo de autenticación de IAM
- Fallo de resolución DNS
- Problemas de sincronización horaria (NTP)

</details>
