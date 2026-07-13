# Configuration and Secrets

> **Versiones compatibles**: Kubernetes 1.32, 1.33, 1.34
> **Última actualización**: February 22, 2026

En Kubernetes, la gestión de configuración es una parte importante de administrar los ajustes de una aplicación por separado del código. En este capítulo, exploraremos en detalle los métodos de gestión de configuración de Kubernetes, incluidos ConfigMaps, Secrets, environment variables y el montaje de configuración mediante volumes.

## Lab Environment Setup

Para seguir los ejemplos de este documento, necesitarás las siguientes herramientas y entorno:

### Required Tools
- kubectl v1.34 o superior
- Un cluster Kubernetes funcional (EKS, minikube, kind, etc.)

### Configuration Example Setup

```bash
# Create namespace
kubectl create namespace config-demo

# Create ConfigMap
kubectl -n config-demo create configmap app-config \
  --from-literal=APP_ENV=production \
  --from-literal=APP_DEBUG=false \
  --from-literal=APP_PORT=8080

# Create Secret
kubectl -n config-demo create secret generic app-secrets \
  --from-literal=DB_USER=admin \
  --from-literal=DB_PASSWORD=s3cr3t \
  --from-literal=API_KEY=abcdef123456

# Create Pod using ConfigMap and Secret
kubectl -n config-demo apply -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: config-test-pod
spec:
  containers:
  - name: test-container
    image: busybox
    command: ["sh", "-c", "env | sort && sleep 3600"]
    env:
    - name: APP_ENV
      valueFrom:
        configMapKeyRef:
          name: app-config
          key: APP_ENV
    - name: DB_PASSWORD
      valueFrom:
        secretKeyRef:
          name: app-secrets
          key: DB_PASSWORD
  restartPolicy: Never
EOF

# Check Pod logs
kubectl -n config-demo logs config-test-pod
```

## Configuration Management at a Glance

```mermaid
graph TD
    subgraph "Kubernetes Configuration Management"
        subgraph "Configuration Sources"
            Admin[Cluster Administrator]
            GitOps[GitOps Pipeline]
            ExtSys[External System]

            Admin -->|Creates| CM[ConfigMap]
            Admin -->|Creates| Secret[Secret]
            GitOps -->|Automates| CM
            GitOps -->|Automates| Secret
            ExtSys -->|Integrates| CM
            ExtSys -->|Integrates| Secret
        end

        subgraph "Configuration Consumption"
            CM -->|Environment Variables| EnvPod[Pod]
            Secret -->|Environment Variables| EnvPod

            CM -->|Volume Mount| VolPod[Pod]
            Secret -->|Volume Mount| VolPod

            Secret -->|Image Pull Secret| ImgPod[Pod]

            subgraph "Advanced Features"
                CM -->|Auto Reload| Sidecar[Sidecar]
                Secret -->|Encryption| KSOPS[KSOPS]
                Secret -->|Dynamic Injection| Vault[Vault Injector]
            end
        end
    end

    %% Style definitions
    classDef admin fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;
    classDef config fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef pod fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef advanced fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef integration fill:#E83E8C,stroke:#333,stroke-width:1px,color:white;

    %% Apply classes
    class Admin,GitOps,ExtSys admin;
    class CM,Secret config;
    class EnvPod,VolPod,ImgPod pod;
    class Sidecar,KSOPS,Vault advanced;
    class GitOps,ExtSys integration;
```

## Table of Contents

1. [ConfigMap](#configmap)
2. [Secret](#secret)
3. [Environment Variables](#environment-variables)
4. [Mounting Configuration Through Volumes](#mounting-configuration-through-volumes)
5. [Configuration Best Practices](#configuration-best-practices)
6. [External Configuration Management Tools](#external-configuration-management-tools)

## ConfigMap

> **Concepto clave**: Los ConfigMaps almacenan datos de configuración en pares clave-valor, separando el código de la aplicación de la configuración.

Los ConfigMaps son objetos de API que almacenan datos de configuración en pares clave-valor. Usar ConfigMaps te permite separar los datos de configuración de las container images, lo que hace que las aplicaciones sean más portables.

### ConfigMap vs Secret Comparison

| Feature | ConfigMap | Secret |
|---------|-----------|--------|
| **Purpose** | General configuration data | Sensitive configuration data |
| **Storage Format** | Plain text | Base64 encoded (default) |
| **Size Limit** | 1MB | 1MB |
| **Encryption** | None by default | etcd encryption support |
| **Volume Type** | configMap | secret |
| **Use Cases** | Environment variables, config files | Passwords, tokens, certificates |
| **Auto Update** | Possible delay when volume mounted | Possible delay when volume mounted |

### ConfigMap Creation Methods

Los ConfigMaps se pueden crear de varias maneras:

1. **Creación imperativa**:

```bash
# Create from literal values
kubectl create configmap my-config --from-literal=key1=value1 --from-literal=key2=value2

# Create from file
kubectl create configmap my-config --from-file=config.properties

# Create from directory
kubectl create configmap my-config --from-file=config-dir/
```

2. **Creación declarativa**:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: my-config
data:
  # Simple key-value pairs
  database.host: "mysql"
  database.port: "3306"

  # File-like configuration
  config.yaml: |
    server:
      port: 8080
    logging:
      level: INFO
    features:
      enabled: true
```

### ConfigMap Usage Methods

Los ConfigMaps se pueden usar de las siguientes maneras:

1. **Usar como environment variables**:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: config-env-pod
spec:
  containers:
  - name: app
    image: nginx
    env:
    # Single key-value reference
    - name: DB_HOST
      valueFrom:
        configMapKeyRef:
          name: my-config
          key: database.host
    # All key-value references
    envFrom:
    - configMapRef:
        name: my-config
```

```mermaid
flowchart TD
    CM[ConfigMap] -->|Environment Variables| Pod1[Pod]
    CM -->|Volume Mount| Pod2[Pod]
    CM -->|Command Line Arguments| Pod3[Pod]

    subgraph "ConfigMap Data"
        CMData1["key1: value1"]
        CMData2["key2: value2"]
        CMData3["config.properties: file contents"]
    end

    subgraph "Environment Variable Usage"
        Env1["env.key1 = value1"]
        Env2["env.key2 = value2"]
    end

    subgraph "Volume Mount Usage"
        Vol1["/etc/config/key1"]
        Vol2["/etc/config/key2"]
        Vol3["/etc/config/config.properties"]
    end

    CM --- CMData1
    CM --- CMData2
    CM --- CMData3

    Pod1 --- Env1
    Pod1 --- Env2

    Pod2 --- Vol1
    Pod2 --- Vol2
    Pod2 --- Vol3

    %% Style definitions
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;

    %% Apply classes
    class CM k8sComponent;
    class Pod1,Pod2,Pod3 userApp;
```

### ConfigMap Creation

Los ConfigMaps se pueden crear de varias maneras:

#### Imperative

```bash
# Create from literal values
kubectl create configmap my-config --from-literal=key1=value1 --from-literal=key2=value2

# Create from file
kubectl create configmap my-config --from-file=config.properties

# Create from directory
kubectl create configmap my-config --from-file=config-dir/
```

#### Declarative

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: my-config
data:
  # Simple key-value pairs
  key1: value1
  key2: value2
  # File-like configuration
  config.properties: |
    property1=value1
    property2=value2
  # JSON configuration
  config.json: |
    {
      "property1": "value1",
      "property2": "value2"
    }
```

### ConfigMap Usage

Los ConfigMaps se pueden usar en Pods de las siguientes maneras:

#### Use as Environment Variables

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: configmap-pod
spec:
  containers:
  - name: test-container
    image: busybox
    command: [ "/bin/sh", "-c", "env" ]
    env:
    # Use single key-value pair
    - name: SPECIAL_KEY
      valueFrom:
        configMapKeyRef:
          name: my-config
          key: key1
    # Use all key-value pairs as environment variables
    envFrom:
    - configMapRef:
        name: my-config
  restartPolicy: Never
```

#### Mount as Volume

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: configmap-pod
spec:
  containers:
  - name: test-container
    image: busybox
    command: [ "/bin/sh", "-c", "ls /etc/config/" ]
    volumeMounts:
    - name: config-volume
      mountPath: /etc/config
  volumes:
  - name: config-volume
    configMap:
      name: my-config
  restartPolicy: Never
```

#### Mount Only Specific Keys

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: configmap-pod
spec:
  containers:
  - name: test-container
    image: busybox
    command: [ "/bin/sh", "-c", "cat /etc/config/key1" ]
    volumeMounts:
    - name: config-volume
      mountPath: /etc/config
  volumes:
  - name: config-volume
    configMap:
      name: my-config
      items:
      - key: key1
        path: key1
  restartPolicy: Never
```

### ConfigMap Updates

Cuando se actualiza un ConfigMap, el contenido del ConfigMap montado como volume se actualiza automáticamente. Sin embargo, los ConfigMaps usados como environment variables requieren reiniciar el Pod para actualizarse.

```bash
kubectl edit configmap my-config
```

O

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: my-config
data:
  key1: updated-value1
  key2: value2
```

```bash
kubectl apply -f updated-configmap.yaml
```

## Secret

Los Secrets son objetos de API que almacenan información sensible, como passwords, OAuth tokens y SSH keys. Los Secrets son similares a los ConfigMaps, pero proporcionan características de seguridad adicionales para almacenar datos sensibles.

```mermaid
graph LR
    Secret[Secret] -->|Environment Variables| Pod1[Pod]
    Secret -->|Volume Mount| Pod2[Pod]
    Secret -->|Image Pull Secret| Pod3[Pod]

    subgraph "Secret Types"
        ST1["Opaque (Default)"]
        ST2["kubernetes.io/tls"]
        ST3["kubernetes.io/dockerconfigjson"]
        ST4["kubernetes.io/basic-auth"]
    end

    subgraph "Storage Method"
        Store1["base64 encoding"]
        Store2["etcd encryption (optional)"]
    end

    Secret --- ST1
    Secret --- ST2
    Secret --- ST3
    Secret --- ST4

    Secret --- Store1
    Secret --- Store2

    %% Style definitions
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef dataStore fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;

    %% Apply classes
    class Secret k8sComponent;
    class Pod1,Pod2,Pod3 userApp;
    class Store1,Store2 dataStore;
```

### Secret Types

Kubernetes proporciona varios tipos de secrets:

- **Opaque**: Tipo predeterminado, almacena datos arbitrarios definidos por el usuario.
- **kubernetes.io/service-account-token**: Almacena service account tokens.
- **kubernetes.io/dockercfg**: Almacena la forma serializada del archivo `.dockercfg`.
- **kubernetes.io/dockerconfigjson**: Almacena la forma serializada del archivo `.docker/config.json`.
- **kubernetes.io/basic-auth**: Almacena credenciales para basic authentication.
- **kubernetes.io/ssh-auth**: Almacena credenciales para SSH authentication.
- **kubernetes.io/tls**: Almacena certificados y keys TLS.
- **bootstrap.kubernetes.io/token**: Almacena datos de bootstrap token.

### Secret Creation

Los Secrets se pueden crear de varias maneras:

#### Imperative

```bash
# Create from literal values
kubectl create secret generic my-secret --from-literal=username=admin --from-literal=password=secret

# Create from files
kubectl create secret generic my-secret --from-file=username.txt --from-file=password.txt

# Create TLS secret
kubectl create secret tls my-tls-secret --cert=path/to/cert.crt --key=path/to/key.key

# Create Docker registry secret
kubectl create secret docker-registry my-registry-secret \
  --docker-server=DOCKER_REGISTRY_SERVER \
  --docker-username=DOCKER_USER \
  --docker-password=DOCKER_PASSWORD \
  --docker-email=DOCKER_EMAIL
```

#### Declarative

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: my-secret
type: Opaque
data:
  # base64 encoded values
  username: YWRtaW4=  # admin
  password: c2VjcmV0  # secret
```

O puedes usar el campo `stringData` para proporcionar valores sin codificar:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: my-secret
type: Opaque
stringData:
  # Unencoded values
  username: admin
  password: secret
```

### Secret Usage

Los Secrets se pueden usar en Pods de las siguientes maneras:

#### Use as Environment Variables

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: secret-pod
spec:
  containers:
  - name: test-container
    image: busybox
    command: [ "/bin/sh", "-c", "env" ]
    env:
    # Use single key-value pair
    - name: USERNAME
      valueFrom:
        secretKeyRef:
          name: my-secret
          key: username
    # Use all key-value pairs as environment variables
    envFrom:
    - secretRef:
        name: my-secret
  restartPolicy: Never
```

#### Mount as Volume

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: secret-pod
spec:
  containers:
  - name: test-container
    image: busybox
    command: [ "/bin/sh", "-c", "ls /etc/secret/" ]
    volumeMounts:
    - name: secret-volume
      mountPath: /etc/secret
  volumes:
  - name: secret-volume
    secret:
      secretName: my-secret
  restartPolicy: Never
```

#### Image Pull Secrets

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: private-image-pod
spec:
  containers:
  - name: private-image-container
    image: private-registry.example.com/my-app:v1
  imagePullSecrets:
  - name: my-registry-secret
```

### Secret Security Considerations

Los Secrets se codifican en base64 de forma predeterminada, pero esto no es encryption. Para mejorar la seguridad de los secrets, considera los siguientes métodos:

1. **etcd Encryption**: Cifra los secrets almacenados en etcd.
2. **RBAC**: Restringe el acceso a los secrets.
3. **Network Policies**: Limita los Pods que pueden acceder a los secrets.
4. **External Secret Management Tools**: Usa herramientas externas de gestión de secrets como AWS Secrets Manager, HashiCorp Vault, etc.

#### etcd Encryption Configuration

```yaml
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
  - resources:
    - secrets
    providers:
    - aescbc:
        keys:
        - name: key1
          secret: <base64 encoded key>
    - identity: {}
```

## Environment Variables

Las environment variables son una forma sencilla de pasar información de configuración a los contenedores. Kubernetes proporciona varias formas de establecer environment variables.

```mermaid
graph TD
    Pod[Pod] -->|Contains| Container[Container]

    subgraph "Environment Variable Sources"
        Direct["Direct Setting"]
        CM["ConfigMap"]
        Secret["Secret"]
        DownAPI["Downward API"]
    end

    Direct -->|env| Container
    CM -->|valueFrom.configMapKeyRef| Container
    CM -->|envFrom.configMapRef| Container
    Secret -->|valueFrom.secretKeyRef| Container
    Secret -->|envFrom.secretRef| Container
    DownAPI -->|valueFrom.fieldRef| Container
    DownAPI -->|valueFrom.resourceFieldRef| Container

    %% Style definitions
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;

    %% Apply classes
    class Pod,Container userApp;
    class CM,Secret,DownAPI k8sComponent;
    class Direct k8sComponent;
```

### Direct Setting

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: env-pod
spec:
  containers:
  - name: test-container
    image: busybox
    command: [ "/bin/sh", "-c", "env" ]
    env:
    - name: ENVIRONMENT
      value: "production"
    - name: LOG_LEVEL
      value: "INFO"
  restartPolicy: Never
```

### Setting from ConfigMap

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: env-pod
spec:
  containers:
  - name: test-container
    image: busybox
    command: [ "/bin/sh", "-c", "env" ]
    env:
    - name: ENVIRONMENT
      valueFrom:
        configMapKeyRef:
          name: my-config
          key: environment
  restartPolicy: Never
```

### Setting from Secret

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: env-pod
spec:
  containers:
  - name: test-container
    image: busybox
    command: [ "/bin/sh", "-c", "env" ]
    env:
    - name: DATABASE_PASSWORD
      valueFrom:
        secretKeyRef:
          name: my-secret
          key: password
  restartPolicy: Never
```

### Setting through Downward API

La Downward API te permite exponer información de Pods y contenedores como environment variables.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: downward-api-pod
  labels:
    app: myapp
spec:
  containers:
  - name: test-container
    image: busybox
    command: [ "/bin/sh", "-c", "env" ]
    env:
    - name: POD_NAME
      valueFrom:
        fieldRef:
          fieldPath: metadata.name
    - name: POD_NAMESPACE
      valueFrom:
        fieldRef:
          fieldPath: metadata.namespace
    - name: POD_IP
      valueFrom:
        fieldRef:
          fieldPath: status.podIP
    - name: NODE_NAME
      valueFrom:
        fieldRef:
          fieldPath: spec.nodeName
    - name: CONTAINER_CPU_REQUEST
      valueFrom:
        resourceFieldRef:
          containerName: test-container
          resource: requests.cpu
  restartPolicy: Never
```

## Mounting Configuration Through Volumes

Montar archivos de configuración en contenedores mediante volumes proporciona un método de gestión de configuración más flexible que las environment variables.

```mermaid
graph TD
    Pod[Pod] -->|Contains| Container[Container]
    Pod -->|Defines| Volumes[Volumes]
    Container -->|Mounts| VolumeMounts[Volume Mounts]
    VolumeMounts -->|References| Volumes

    subgraph "Volume Sources"
        CM["ConfigMap"]
        Secret["Secret"]
    end

    Volumes -->|configMap| CM
    Volumes -->|secret| Secret

    subgraph "Mount Options"
        MO1["Full Volume Mount"]
        MO2["Mount Specific Keys Only"]
        MO3["Read-only Mount"]
        MO4["SubPath Mount"]
    end

    VolumeMounts --- MO1
    VolumeMounts --- MO2
    VolumeMounts --- MO3
    VolumeMounts --- MO4

    %% Style definitions
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;

    %% Apply classes
    class Pod,Container userApp;
    class Volumes,VolumeMounts,CM,Secret k8sComponent;
```

### ConfigMap Volume

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: configmap-volume-pod
spec:
  containers:
  - name: test-container
    image: busybox
    command: [ "/bin/sh", "-c", "ls -la /etc/config" ]
    volumeMounts:
    - name: config-volume
      mountPath: /etc/config
  volumes:
  - name: config-volume
    configMap:
      name: my-config
  restartPolicy: Never
```

### Secret Volume

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: secret-volume-pod
spec:
  containers:
  - name: test-container
    image: busybox
    command: [ "/bin/sh", "-c", "ls -la /etc/secret" ]
    volumeMounts:
    - name: secret-volume
      mountPath: /etc/secret
  volumes:
  - name: secret-volume
    secret:
      secretName: my-secret
  restartPolicy: Never
```

### Specific File Mount

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: specific-file-pod
spec:
  containers:
  - name: test-container
    image: busybox
    command: [ "/bin/sh", "-c", "cat /etc/config/config.properties" ]
    volumeMounts:
    - name: config-volume
      mountPath: /etc/config
  volumes:
  - name: config-volume
    configMap:
      name: my-config
      items:
      - key: config.properties
        path: config.properties
  restartPolicy: Never
```

### Read-only Mount

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: readonly-mount-pod
spec:
  containers:
  - name: test-container
    image: busybox
    command: [ "/bin/sh", "-c", "ls -la /etc/config" ]
    volumeMounts:
    - name: config-volume
      mountPath: /etc/config
      readOnly: true
  volumes:
  - name: config-volume
    configMap:
      name: my-config
  restartPolicy: Never
```

### SubPath Mount

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: subpath-mount-pod
spec:
  containers:
  - name: test-container
    image: busybox
    command: [ "/bin/sh", "-c", "cat /etc/nginx/nginx.conf" ]
    volumeMounts:
    - name: config-volume
      mountPath: /etc/nginx/nginx.conf
      subPath: nginx.conf
  volumes:
  - name: config-volume
    configMap:
      name: my-config
  restartPolicy: Never
```

## Configuration Best Practices

Considera las siguientes best practices al gestionar configuración en Kubernetes:

### 1. Separate Configuration from Code

Gestiona el código de la aplicación y la configuración por separado. Esto elimina la necesidad de reconstruir la aplicación cuando cambia la configuración.

### 2. Environment-Specific Configuration Management

Gestiona la configuración por separado para distintos entornos, como development, testing y production. Puedes usar namespaces para separar entornos y usar diferentes ConfigMaps y Secrets para cada entorno.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: my-config
  namespace: development
data:
  environment: development
  log_level: DEBUG
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: my-config
  namespace: production
data:
  environment: production
  log_level: INFO
```

### 3. Use Secrets for Sensitive Information

Usa siempre Secrets para almacenar información sensible, como passwords, API keys y certificados. Usa ConfigMaps solo para datos de configuración no sensibles.

### 4. Maintain Immutability

Al cambiar la configuración, crea una nueva versión en lugar de modificar la existente. Esto facilita los rollbacks y permite rastrear el historial de cambios de configuración.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: my-config-v1
data:
  # Configuration data
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: my-config-v2
data:
  # Updated configuration data
```

### 5. Restart Pods on Configuration Changes

La configuración usada como environment variables requiere reiniciar el Pod para actualizarse. Usa Deployments para realizar rolling updates.

```bash
kubectl rollout restart deployment/my-deployment
```

### 6. Validate Configuration

Valida la configuración antes de aplicarla. Una configuración no válida puede provocar fallos en la aplicación.

### 7. Document Configuration

Documenta las opciones de configuración y sus efectos. Esto ayuda a los miembros del equipo a entender y gestionar la configuración.

## Configuration Management in Amazon EKS

En Amazon EKS, puedes usar varios servicios de AWS además de las características básicas de gestión de configuración de Kubernetes para gestionar configuración y secrets. Esta sección cubre varias formas de gestionar configuración en EKS y la integración con servicios de AWS.

```mermaid
graph TD
    EKS[Amazon EKS] -->|Uses| K8s[Kubernetes Configuration]
    EKS -->|Integrates| AWS[AWS Services]

    subgraph "Kubernetes Configuration"
        CM["ConfigMap"]
        Secret["Secret"]
    end

    subgraph "AWS Services"
        SM["AWS Secrets Manager"]
        PS["AWS Parameter Store"]
        AC["AWS AppConfig"]
        KMS["AWS KMS"]
        IAM["AWS IAM"]
    end

    subgraph "Integration Tools"
        ESO["External Secrets Operator"]
        ASCP["AWS Secrets and Configuration Provider"]
        IRSA["IAM Roles for Service Accounts"]
        ACK["AWS Controllers for Kubernetes"]
    end

    K8s --- CM
    K8s --- Secret

    AWS --- SM
    AWS --- PS
    AWS --- AC
    AWS --- KMS
    AWS --- IAM

    SM -->|Integrates| ESO
    PS -->|Integrates| ASCP
    IAM -->|Integrates| IRSA
    AWS -->|Integrates| ACK

    ESO -->|Creates| Secret
    ASCP -->|Mounts| Secret
    IRSA -->|Grants Permissions| Pod[Pod]
    ACK -->|Manages| AWS

    KMS -->|Encrypts| Secret

    %% Style definitions
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef awsService fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef integrationTool fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;

    %% Apply classes
    class EKS,K8s,CM,Secret k8sComponent;
    class Pod userApp;
    class AWS,SM,PS,AC,KMS,IAM awsService;
    class ESO,ASCP,IRSA,ACK integrationTool;
```

### AWS Secrets Manager Integration

AWS Secrets Manager es un servicio que te permite almacenar y gestionar de forma segura credenciales de bases de datos, API keys y otra información secreta. En EKS, puedes usar External Secrets Operator o AWS Secrets and Configuration Provider (ASCP) para sincronizar secrets desde AWS Secrets Manager hacia Kubernetes secrets.

#### External Secrets Operator Installation

```bash
# Install External Secrets Operator using Helm
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets \
  --namespace external-secrets \
  --create-namespace
```

#### Create SecretStore

```yaml
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: aws-secretsmanager
  namespace: my-namespace
spec:
  provider:
    aws:
      service: SecretsManager
      region: us-west-2
      auth:
        jwt:
          serviceAccountRef:
            name: my-serviceaccount
```

#### Create ExternalSecret

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: database-credentials
  namespace: my-namespace
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secretsmanager
    kind: SecretStore
  target:
    name: db-credentials
  data:
  - secretKey: username
    remoteRef:
      key: prod/db/credentials
      property: username
  - secretKey: password
    remoteRef:
      key: prod/db/credentials
      property: password
```

#### IRSA (IAM Roles for Service Accounts) Setup

External Secrets Operator necesita permisos de IAM adecuados para acceder a AWS Secrets Manager. Puedes usar IRSA para asociar IAM roles con Kubernetes service accounts.

```bash
# Create OIDC provider
eksctl utils associate-iam-oidc-provider \
  --cluster my-cluster \
  --approve

# Create IAM role and service account
eksctl create iamserviceaccount \
  --cluster my-cluster \
  --namespace my-namespace \
  --name my-serviceaccount \
  --attach-policy-arn arn:aws:iam::aws:policy/SecretsManagerReadWrite \
  --approve
```

### Using AWS Parameter Store

AWS Systems Manager Parameter Store es un servicio que te permite almacenar y gestionar jerárquicamente datos de configuración y valores secretos. Parameter Store es menos costoso que Secrets Manager y es adecuado para almacenar valores de configuración simples.

#### ASCP (AWS Secrets and Configuration Provider) Installation

```bash
# Install ASCP
helm repo add secrets-store-csi-driver https://kubernetes-sigs.github.io/secrets-store-csi-driver/charts
helm install csi-secrets-store secrets-store-csi-driver/secrets-store-csi-driver \
  --namespace kube-system

# Install AWS provider
kubectl apply -f https://raw.githubusercontent.com/aws/secrets-store-csi-driver-provider-aws/main/deployment/aws-provider-installer.yaml
```

#### Create SecretProviderClass

```yaml
apiVersion: secrets-store.csi.x-k8s.io/v1
kind: SecretProviderClass
metadata:
  name: aws-parameters
  namespace: my-namespace
spec:
  provider: aws
  parameters:
    objects: |
      - objectName: /my-app/config/log-level
        objectType: ssmparameter
      - objectName: /my-app/config/environment
        objectType: ssmparameter
```

#### Using Parameter Store Values in Pods

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: parameter-store-pod
  namespace: my-namespace
spec:
  containers:
  - name: app
    image: my-app:latest
    volumeMounts:
    - name: parameters-store-volume
      mountPath: "/mnt/parameters"
      readOnly: true
  volumes:
  - name: parameters-store-volume
    csi:
      driver: secrets-store.csi.k8s.io
      readOnly: true
      volumeAttributes:
        secretProviderClass: aws-parameters
```

### Dynamic Configuration with AWS AppConfig

AWS AppConfig es un servicio que gestiona y despliega configuración de aplicaciones. Usar AppConfig te permite actualizar configuración dinámicamente sin redesplegar aplicaciones.

#### AppConfig Agent Sidecar Pattern

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
  namespace: my-namespace
spec:
  replicas: 3
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      containers:
      - name: app
        image: my-app:latest
        env:
        - name: CONFIG_PATH
          value: /config/config.json
        volumeMounts:
        - name: config-volume
          mountPath: /config
      - name: appconfig-agent
        image: public.ecr.aws/aws-appconfig/aws-appconfig-agent:2.0
        env:
        - name: AWS_APPCONFIG_EXTENSION_POLL_INTERVAL_SECONDS
          value: "45"
        - name: AWS_APPCONFIG_EXTENSION_POLL_TIMEOUT_SECONDS
          value: "15"
        - name: AWS_APPCONFIG_EXTENSION_HTTP_PORT
          value: "2772"
        - name: AWS_APPCONFIG_EXTENSION_PREFETCH_LIST
          value: '{"Applications":[{"ApplicationId":"MyApp","Environments":[{"EnvironmentId":"Production","Configurations":[{"ConfigurationProfileId":"MyConfig","VersionNumber":null}]}]}]}'
        volumeMounts:
        - name: config-volume
          mountPath: /config
      volumes:
      - name: config-volume
        emptyDir: {}
```

### Configuration with EKS Fargate Profiles

Usar EKS Fargate te permite ejecutar Kubernetes Pods sin gestionar nodes. Puedes configurar el entorno de ejecución del Pod mediante Fargate profiles.

```yaml
apiVersion: eks.amazonaws.com/v1beta1
kind: FargateProfile
metadata:
  name: my-profile
  namespace: my-namespace
spec:
  clusterName: my-cluster
  podExecutionRoleArn: arn:aws:iam::123456789012:role/my-pod-execution-role
  selectors:
  - namespace: my-namespace
    labels:
      environment: production
  subnets:
  - subnet-1234567890abcdef0
  - subnet-0abcdef1234567890
```

### Secret Encryption with AWS KMS

Los Kubernetes secrets se codifican en base64 de forma predeterminada, lo cual no es encryption. Puedes usar AWS KMS (Key Management Service) para cifrar secrets en tu EKS cluster.

#### Create KMS Key

```bash
# Create KMS key
aws kms create-key --description "EKS Secret Encryption Key"

# Store key ID
KEY_ID=$(aws kms create-key --query KeyMetadata.KeyId --output text)

# Create key alias
aws kms create-alias --alias-name alias/eks-secrets --target-key-id $KEY_ID
```

#### Apply Encryption Configuration to EKS Cluster

```bash
# Apply encryption configuration
aws eks update-cluster-config \
  --name my-cluster \
  --encryption-config '[{"resources":["secrets"],"provider":{"keyArn":"arn:aws:kms:us-west-2:123456789012:key/'$KEY_ID'"}}]'
```

### Secret Access Control with AWS IAM

Usar IRSA (IAM Roles for Service Accounts) para asociar IAM roles con Kubernetes service accounts permite que los Pods accedan de forma segura a servicios de AWS.

#### Create Service Account

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-service-account
  namespace: my-namespace
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/my-iam-role
```

#### Using Service Account in Pods

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: my-pod
  namespace: my-namespace
spec:
  serviceAccountName: my-service-account
  containers:
  - name: app
    image: my-app:latest
```

### EKS Configuration Best Practices

Considera las siguientes best practices al gestionar configuración en EKS:

1. **Use IRSA**: Usa siempre IRSA para otorgar permisos mínimos a Pods al acceder a servicios de AWS.

2. **Encrypt Secrets**: Usa KMS para cifrar secrets en tu EKS cluster.

3. **External Secret Management**: Usa servicios externos de gestión de secrets como AWS Secrets Manager o Parameter Store para gestionar información sensible.

4. **Configuration Version Management**: Usa AWS AppConfig o Parameter Store para gestionar versiones de configuración.

5. **Environment-Specific Configuration Separation**: Gestiona la configuración por separado para entornos de development, testing y production. Usa Kubernetes namespaces y AWS resource tags.

6. **Minimize IAM Policies**: Sigue el principio de mínimo privilegio al acceder a servicios de AWS.

7. **Configuration Automation**: Usa herramientas como AWS CloudFormation, AWS CDK o Terraform para automatizar la gestión de configuración.

### EKS Configuration Management Tools

Veamos herramientas que ayudan a gestionar configuración en EKS:

#### AWS Controllers for Kubernetes (ACK)

ACK es una herramienta que te permite gestionar recursos de AWS desde Kubernetes. Usando ACK, puedes crear y gestionar recursos de AWS mediante Kubernetes manifests.

```yaml
apiVersion: secretsmanager.services.k8s.aws/v1alpha1
kind: Secret
metadata:
  name: my-secret
spec:
  name: my-secret
  description: "My secret created via ACK"
  forceDeleteWithoutRecovery: true
  generateSecretString:
    excludeCharacters: "\"@/\\"
    excludePunctuation: true
    includeSpace: false
    passwordLength: 16
```

#### eksctl

eksctl es una herramienta de línea de comandos para crear y gestionar EKS clusters. Puedes usar eksctl para gestionar la configuración del cluster.

```yaml
# cluster.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
secretsEncryption:
  keyARN: arn:aws:kms:us-west-2:123456789012:key/1234abcd-12ab-34cd-56ef-1234567890ab
```

```bash
eksctl create cluster -f cluster.yaml
```

#### AWS CDK

AWS CDK (Cloud Development Kit) es una herramienta para definir recursos de AWS usando lenguajes de programación. Puedes usar CDK para definir EKS clusters y recursos relacionados.

```typescript
import * as cdk from 'aws-cdk-lib';
import * as eks from 'aws-cdk-lib/aws-eks';
import * as iam from 'aws-cdk-lib/aws-iam';

const app = new cdk.App();
const stack = new cdk.Stack(app, 'EksStack');

// Create EKS cluster
const cluster = new eks.Cluster(stack, 'Cluster', {
  version: eks.KubernetesVersion.V1_21,
  secretsEncryptionKey: new kms.Key(stack, 'Key'),
});

// Create service account
const serviceAccount = cluster.addServiceAccount('ServiceAccount', {
  name: 'my-service-account',
  namespace: 'my-namespace',
});

// Attach IAM policy
serviceAccount.role.addManagedPolicy(
  iam.ManagedPolicy.fromAwsManagedPolicyName('SecretsManagerReadWrite')
);
```

## Conclusion

En este capítulo, aprendimos sobre los métodos de gestión de configuración de Kubernetes. Los ConfigMaps y Secrets proporcionan formas básicas de gestionar la configuración de aplicaciones, y puedes pasar esta configuración a los contenedores mediante environment variables y volumes. También cubrimos best practices de gestión de configuración y herramientas externas de gestión de configuración.

En entornos Amazon EKS, puedes lograr una gestión de configuración más potente y segura usando servicios de AWS junto con las características básicas de gestión de configuración de Kubernetes. Puedes gestionar secrets de forma segura integrando servicios como AWS Secrets Manager, Parameter Store, KMS e IAM, y otorgar permisos mínimos a Pods mediante IRSA. Además, puedes actualizar configuración dinámicamente sin redesplegar aplicaciones usando AWS AppConfig.

La gestión eficaz de configuración es importante para mejorar la mantenibilidad, escalabilidad y seguridad de las aplicaciones Kubernetes. Es importante elegir la estrategia de gestión de configuración adecuada para los requisitos de tu aplicación y seguir best practices. En entornos EKS, puedes crear soluciones de gestión de configuración más potentes mediante la integración con servicios de AWS.

En el próximo capítulo, aprenderemos sobre la seguridad de Kubernetes.

## Quiz

Para comprobar lo que aprendiste en este capítulo, intenta el [Configuration and Secrets Quiz](../quizzes/core/05-configuration-secrets-quiz.md).

## References

- [Kubernetes Official Documentation - ConfigMaps](https://kubernetes.io/docs/concepts/configuration/configmap/)
- [Kubernetes Official Documentation - Secrets](https://kubernetes.io/docs/concepts/configuration/secret/)
- [Kubernetes Official Documentation - Environment Variables](https://kubernetes.io/docs/tasks/inject-data-application/define-environment-variable-container/)
- [Kubernetes Official Documentation - Configure a Pod to Use a ConfigMap](https://kubernetes.io/docs/tasks/configure-pod-container/configure-pod-configmap/)
- [Kubernetes Official Documentation - Distribute Credentials Securely Using Secrets](https://kubernetes.io/docs/tasks/inject-data-application/distribute-credentials-secure/)
- [Helm Official Documentation](https://helm.sh/docs/)
- [Kustomize Official Documentation](https://kustomize.io/)
- [External Secrets Operator Official Documentation](https://external-secrets.io/latest/)
- [AWS Secrets Manager Official Documentation](https://docs.aws.amazon.com/secretsmanager/latest/userguide/intro.html)
- [AWS Systems Manager Parameter Store Official Documentation](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-parameter-store.html)
- [AWS AppConfig Official Documentation](https://docs.aws.amazon.com/appconfig/latest/userguide/what-is-appconfig.html)
- [EKS Official Documentation - IRSA](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
- [EKS Official Documentation - Secrets Encryption](https://docs.aws.amazon.com/eks/latest/userguide/enable-kms.html)
- [AWS Controllers for Kubernetes (ACK) Official Documentation](https://aws-controllers-k8s.github.io/community/)
