# Configuración y Secrets

> **Versiones compatibles**: Kubernetes 1.32, 1.33, 1.34
> **Última actualización**: February 22, 2026

En Kubernetes, la gestión de la configuración es una parte importante de administrar los ajustes de la aplicación por separado del código. En este capítulo, exploraremos en detalle los métodos de gestión de configuración de Kubernetes, incluidos ConfigMaps, Secrets, variables de entorno y el montaje de configuración mediante volúmenes.

## Configuración del entorno de laboratorio

Para seguir los ejemplos de este documento, necesitarás las siguientes herramientas y entorno:

### Herramientas necesarias
- kubectl v1.34 o superior
- Un clúster de Kubernetes funcional (EKS, minikube, kind, etc.)

### Configuración de ejemplo

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

## Gestión de configuración de un vistazo

![Los administradores de clústeres, los pipelines de GitOps y los sistemas externos crean ConfigMaps y Secrets, que los Pods consumen como variables de entorno, montajes de volúmenes y secrets de extracción de imágenes, mientras que ConfigMap alimenta la recarga automática del sidecar y Secret alimenta el cifrado de KSOPS y la inyección dinámica de Vault Injector como funciones avanzadas.](../.gitbook/assets/en-core-05-configuration-secrets-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-05-configuration-secrets-0.html)

## Tabla de contenidos

1. [ConfigMap](#configmap)
2. [Secret](#secret)
3. [Variables de entorno](#environment-variables)
4. [Montaje de configuración mediante volúmenes](#mounting-configuration-through-volumes)
5. [Prácticas recomendadas de configuración](#configuration-best-practices)
6. [Herramientas externas de gestión de configuración](#external-configuration-management-tools)

## ConfigMap

> **Concepto clave**: Los ConfigMaps almacenan datos de configuración en pares clave-valor, separando el código de la aplicación de la configuración.

Los ConfigMaps son objetos de API que almacenan datos de configuración en pares clave-valor. El uso de ConfigMaps permite separar los datos de configuración de las imágenes de contenedor, lo que hace que las aplicaciones sean más portátiles.

### Comparación entre ConfigMap y Secret

| Característica | ConfigMap | Secret |
|---------|-----------|--------|
| **Propósito** | Datos de configuración generales | Datos de configuración confidenciales |
| **Formato de almacenamiento** | Texto sin formato | Codificado en Base64 (predeterminado) |
| **Límite de tamaño** | 1MB | 1MB |
| **Cifrado** | Ninguno de forma predeterminada | Compatibilidad con cifrado de etcd |
| **Tipo de volumen** | configMap | secret |
| **Casos de uso** | Variables de entorno, archivos de configuración | Contraseñas, tokens, certificados |
| **Actualización automática** | Posible retraso cuando se monta como volumen | Posible retraso cuando se monta como volumen |

### Métodos de creación de ConfigMap

Los ConfigMaps se pueden crear de varias formas:

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

### Métodos de uso de ConfigMap

Los ConfigMaps se pueden usar de las siguientes formas:

1. **Usar como variables de entorno**:

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

![Los datos de clave-valor de un ConfigMap (key1, key2, config.properties) son consumidos por los Pods de tres formas: como variables de entorno, como un volumen montado o como argumentos de línea de comandos; la ruta de variables de entorno se resuelve en env.key1/env.key2 y la ruta de volumen en archivos bajo /etc/config dentro del contenedor.](../.gitbook/assets/en-core-05-configuration-secrets-1.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-05-configuration-secrets-1.html)

### Creación de ConfigMap

Los ConfigMaps se pueden crear de varias formas:

#### Imperativa

```bash
# Create from literal values
kubectl create configmap my-config --from-literal=key1=value1 --from-literal=key2=value2

# Create from file
kubectl create configmap my-config --from-file=config.properties

# Create from directory
kubectl create configmap my-config --from-file=config-dir/
```

#### Declarativa

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

### Uso de ConfigMap

Los ConfigMaps se pueden usar en Pods de las siguientes formas:

#### Usar como variables de entorno

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

#### Montar como volumen

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

#### Montar solo claves específicas

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

### Actualizaciones de ConfigMap

Cuando se actualiza un ConfigMap, el contenido del ConfigMap montado como volumen se actualiza automáticamente. Sin embargo, los ConfigMaps usados como variables de entorno requieren reiniciar el Pod para actualizarse.

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

Los Secrets son objetos de API que almacenan información confidencial, como contraseñas, tokens de OAuth y claves SSH. Los Secrets son similares a los ConfigMaps, pero proporcionan funciones de seguridad adicionales para almacenar datos confidenciales.

![Los tipos compatibles de un Secret de Kubernetes (Opaque, TLS, dockerconfigjson, basic-auth) y su codificación en base64 más el almacenamiento opcional con cifrado de etcd, junto con las tres formas en que un Pod lo consume: como variables de entorno, un volumen montado o un secret de extracción de imágenes.](../.gitbook/assets/en-core-05-configuration-secrets-2.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-05-configuration-secrets-2.html)

### Tipos de Secret

Kubernetes proporciona varios tipos de secrets:

- **Opaque**: Tipo predeterminado; almacena datos arbitrarios definidos por el usuario.
- **kubernetes.io/service-account-token**: Almacena tokens de cuentas de servicio.
- **kubernetes.io/dockercfg**: Almacena la forma serializada del archivo `.dockercfg`.
- **kubernetes.io/dockerconfigjson**: Almacena la forma serializada del archivo `.docker/config.json`.
- **kubernetes.io/basic-auth**: Almacena credenciales para autenticación básica.
- **kubernetes.io/ssh-auth**: Almacena credenciales para autenticación SSH.
- **kubernetes.io/tls**: Almacena certificados y claves TLS.
- **bootstrap.kubernetes.io/token**: Almacena datos de tokens de bootstrap.

### Creación de Secret

Los Secrets se pueden crear de varias formas:

#### Imperativa

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

#### Declarativa

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

### Uso de Secret

Los Secrets se pueden usar en Pods de las siguientes formas:

#### Usar como variables de entorno

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

#### Montar como volumen

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

#### Secrets de extracción de imágenes

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

### Consideraciones de seguridad para Secret

Los Secrets se codifican en base64 de forma predeterminada, pero esto no es cifrado. Para mejorar la seguridad de los secrets, considera los siguientes métodos:

1. **Cifrado de etcd**: Cifra los secrets almacenados en etcd.
2. **RBAC**: Restringe el acceso a los secrets.
3. **Network Policies**: Limita los Pods que pueden acceder a los secrets.
4. **Herramientas externas de gestión de secrets**: Usa herramientas externas de gestión de secrets, como AWS Secrets Manager, HashiCorp Vault, etc.

#### Configuración de cifrado de etcd

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

## Variables de entorno

Las variables de entorno son una forma sencilla de pasar información de configuración a los contenedores. Kubernetes proporciona varias formas de establecer variables de entorno.

![Las cuatro fuentes desde las que Kubernetes puede rellenar las variables de entorno de un Container: un valor estático directo, una clave de ConfigMap o una referencia completa de envFrom, una clave de Secret o una referencia completa de envFrom, y las referencias de campos o recursos de la Downward API.](../.gitbook/assets/en-core-05-configuration-secrets-3.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-05-configuration-secrets-3.html)

### Configuración directa

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

### Configuración desde ConfigMap

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

### Configuración desde Secret

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

### Configuración mediante Downward API

La Downward API permite exponer información del Pod y del contenedor como variables de entorno.

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

## Montaje de configuración mediante volúmenes

El montaje de archivos de configuración en contenedores mediante volúmenes proporciona un método de gestión de configuración más flexible que las variables de entorno.

![Un Pod define Volumes respaldados por un ConfigMap o Secret; su Container los monta mediante Volume Mounts que hacen referencia a esos Volumes; y hay cuatro opciones de montaje disponibles: montaje de volumen completo, solo claves específicas (items), de solo lectura (readOnly) y montaje con subPath.](../.gitbook/assets/en-core-05-configuration-secrets-4.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-05-configuration-secrets-4.html)

### Volumen de ConfigMap

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

### Volumen de Secret

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

### Montaje de archivo específico

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

### Montaje de solo lectura

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

### Montaje con SubPath

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

## Prácticas recomendadas de configuración

Considera las siguientes prácticas recomendadas al administrar la configuración en Kubernetes:

### 1. Separar la configuración del código

Administra el código de la aplicación y la configuración por separado. Esto elimina la necesidad de reconstruir la aplicación al cambiar la configuración.

### 2. Gestión de configuración específica por entorno

Administra la configuración por separado para distintos entornos, como desarrollo, pruebas y producción. Puedes usar namespaces para separar entornos y usar diferentes ConfigMaps y Secrets para cada entorno.

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

### 3. Usar Secrets para información confidencial

Usa siempre Secrets para almacenar información confidencial, como contraseñas, claves de API y certificados. Usa ConfigMaps solo para datos de configuración no confidenciales.

### 4. Mantener la inmutabilidad

Al cambiar la configuración, crea una nueva versión en lugar de modificar la existente. Esto facilita las reversiones y permite realizar un seguimiento del historial de cambios de configuración.

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

### 5. Reiniciar Pods ante cambios de configuración

La configuración usada como variables de entorno requiere reiniciar el Pod para actualizarse. Usa Deployments para realizar actualizaciones graduales.

```bash
kubectl rollout restart deployment/my-deployment
```

### 6. Validar la configuración

Valida la configuración antes de aplicarla. Una configuración no válida puede provocar fallos en la aplicación.

### 7. Documentar la configuración

Documenta las opciones de configuración y sus efectos. Esto ayuda a los miembros del equipo a comprender y administrar la configuración.

## Gestión de configuración en Amazon EKS

En Amazon EKS, puedes usar los diversos servicios de AWS además de las funciones básicas de gestión de configuración de Kubernetes para administrar la configuración y los secrets. Esta sección cubre varias formas de administrar la configuración en EKS y la integración con servicios de AWS.

![Un clúster de Amazon EKS usa ConfigMaps y Secrets nativos de Kubernetes mientras se integra con AWS Secrets Manager, Parameter Store, AppConfig, KMS e IAM; las herramientas de integración, como External Secrets Operator, ASCP, IRSA y ACK, crean o montan Secrets, los cifran con KMS y otorgan a los Pods permisos de IAM con alcance limitado.](../.gitbook/assets/en-core-05-configuration-secrets-5.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-05-configuration-secrets-5.html)

### Integración con AWS Secrets Manager

AWS Secrets Manager es un servicio que permite almacenar y administrar de forma segura credenciales de bases de datos, claves de API y otra información confidencial. En EKS, puedes usar External Secrets Operator o AWS Secrets and Configuration Provider (ASCP) para sincronizar secrets de AWS Secrets Manager con secrets de Kubernetes.

#### Instalación de External Secrets Operator

```bash
# Install External Secrets Operator using Helm
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets \
  --namespace external-secrets \
  --create-namespace
```

#### Crear SecretStore

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

#### Crear ExternalSecret

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

#### Configuración de IRSA (IAM Roles for Service Accounts)

External Secrets Operator necesita permisos de IAM adecuados para acceder a AWS Secrets Manager. Puedes usar IRSA para asociar roles de IAM con cuentas de servicio de Kubernetes.

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

### Uso de AWS Parameter Store

AWS Systems Manager Parameter Store es un servicio que permite almacenar y administrar jerárquicamente datos de configuración y valores confidenciales. Parameter Store es menos costoso que Secrets Manager y es adecuado para almacenar valores de configuración simples.

#### Instalación de ASCP (AWS Secrets and Configuration Provider)

```bash
# Install ASCP
helm repo add secrets-store-csi-driver https://kubernetes-sigs.github.io/secrets-store-csi-driver/charts
helm install csi-secrets-store secrets-store-csi-driver/secrets-store-csi-driver \
  --namespace kube-system

# Install AWS provider
kubectl apply -f https://raw.githubusercontent.com/aws/secrets-store-csi-driver-provider-aws/main/deployment/aws-provider-installer.yaml
```

#### Crear SecretProviderClass

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

#### Uso de valores de Parameter Store en Pods

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

### Configuración dinámica con AWS AppConfig

AWS AppConfig es un servicio que administra e implementa la configuración de aplicaciones. El uso de AppConfig permite actualizar dinámicamente la configuración sin volver a implementar las aplicaciones.

#### Patrón de sidecar de AppConfig Agent

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

### Configuración con perfiles de EKS Fargate

El uso de EKS Fargate permite ejecutar Pods de Kubernetes sin administrar nodos. Puedes configurar el entorno de ejecución del Pod mediante perfiles de Fargate.

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

### Cifrado de Secret con AWS KMS

Los secrets de Kubernetes se codifican en base64 de forma predeterminada, lo que no es cifrado. Puedes usar AWS KMS (Key Management Service) para cifrar secrets en tu clúster de EKS.

#### Crear clave de KMS

```bash
# Create KMS key
aws kms create-key --description "EKS Secret Encryption Key"

# Store key ID
KEY_ID=$(aws kms create-key --query KeyMetadata.KeyId --output text)

# Create key alias
aws kms create-alias --alias-name alias/eks-secrets --target-key-id $KEY_ID
```

#### Aplicar configuración de cifrado al clúster de EKS

```bash
# Apply encryption configuration
aws eks update-cluster-config \
  --name my-cluster \
  --encryption-config '[{"resources":["secrets"],"provider":{"keyArn":"arn:aws:kms:us-west-2:123456789012:key/'$KEY_ID'"}}]'
```

### Control de acceso a Secret con AWS IAM

El uso de IRSA (IAM Roles for Service Accounts) para asociar roles de IAM con cuentas de servicio de Kubernetes permite que los Pods accedan de forma segura a los servicios de AWS.

#### Crear cuenta de servicio

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-service-account
  namespace: my-namespace
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/my-iam-role
```

#### Uso de cuenta de servicio en Pods

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

### Prácticas recomendadas de configuración de EKS

Considera las siguientes prácticas recomendadas al administrar la configuración en EKS:

1. **Usar IRSA**: Usa siempre IRSA para otorgar permisos mínimos a los Pods al acceder a servicios de AWS.

2. **Cifrar Secrets**: Usa KMS para cifrar secrets en tu clúster de EKS.

3. **Gestión externa de secrets**: Usa servicios externos de gestión de secrets, como AWS Secrets Manager o Parameter Store, para administrar información confidencial.

4. **Gestión de versiones de configuración**: Usa AWS AppConfig o Parameter Store para administrar versiones de configuración.

5. **Separación de configuración específica por entorno**: Administra la configuración por separado para los entornos de desarrollo, pruebas y producción. Usa namespaces de Kubernetes y etiquetas de recursos de AWS.

6. **Minimizar las políticas de IAM**: Sigue el principio de privilegio mínimo al acceder a servicios de AWS.

7. **Automatización de la configuración**: Usa herramientas como AWS CloudFormation, AWS CDK o Terraform para automatizar la gestión de configuración.

### Herramientas de gestión de configuración de EKS

Veamos las herramientas que ayudan a administrar la configuración en EKS:

#### AWS Controllers for Kubernetes (ACK)

ACK es una herramienta que permite administrar recursos de AWS desde Kubernetes. Con ACK, puedes crear y administrar recursos de AWS mediante manifiestos de Kubernetes.

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

eksctl es una herramienta de línea de comandos para crear y administrar clústeres de EKS. Puedes usar eksctl para administrar la configuración del clúster.

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

AWS CDK (Cloud Development Kit) es una herramienta para definir recursos de AWS mediante lenguajes de programación. Puedes usar CDK para definir clústeres de EKS y recursos relacionados.

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

## Conclusión

En este capítulo, aprendimos sobre los métodos de gestión de configuración de Kubernetes. Los ConfigMaps y Secrets proporcionan formas básicas de administrar la configuración de la aplicación, y puedes pasar esta configuración a los contenedores mediante variables de entorno y volúmenes. También cubrimos prácticas recomendadas de gestión de configuración y herramientas externas de gestión de configuración.

En entornos de Amazon EKS, puedes lograr una gestión de configuración más potente y segura mediante el uso de servicios de AWS junto con las funciones básicas de gestión de configuración de Kubernetes. Puedes administrar secrets de forma segura integrando servicios como AWS Secrets Manager, Parameter Store, KMS e IAM, y otorgar permisos mínimos a los Pods mediante IRSA. Además, puedes actualizar dinámicamente la configuración sin volver a implementar aplicaciones con AWS AppConfig.

La gestión eficaz de la configuración es importante para mejorar la mantenibilidad, la escalabilidad y la seguridad de las aplicaciones de Kubernetes. Es importante elegir la estrategia de gestión de configuración adecuada para los requisitos de tu aplicación y seguir las prácticas recomendadas. En entornos de EKS, puedes crear soluciones de gestión de configuración más potentes mediante la integración con servicios de AWS.

En el próximo capítulo, aprenderemos sobre la seguridad de Kubernetes.

## Cuestionario

Para poner a prueba lo aprendido en este capítulo, prueba el [Cuestionario de configuración y Secrets](../quizzes/core/05-configuration-secrets-quiz.md).

## Referencias

- [Documentación oficial de Kubernetes - ConfigMaps](https://kubernetes.io/docs/concepts/configuration/configmap/)
- [Documentación oficial de Kubernetes - Secrets](https://kubernetes.io/docs/concepts/configuration/secret/)
- [Documentación oficial de Kubernetes - Variables de entorno](https://kubernetes.io/docs/tasks/inject-data-application/define-environment-variable-container/)
- [Documentación oficial de Kubernetes - Configurar un Pod para usar un ConfigMap](https://kubernetes.io/docs/tasks/configure-pod-container/configure-pod-configmap/)
- [Documentación oficial de Kubernetes - Distribuir credenciales de forma segura mediante Secrets](https://kubernetes.io/docs/tasks/inject-data-application/distribute-credentials-secure/)
- [Documentación oficial de Helm](https://helm.sh/docs/)
- [Documentación oficial de Kustomize](https://kustomize.io/)
- [Documentación oficial de External Secrets Operator](https://external-secrets.io/latest/)
- [Documentación oficial de AWS Secrets Manager](https://docs.aws.amazon.com/secretsmanager/latest/userguide/intro.html)
- [Documentación oficial de AWS Systems Manager Parameter Store](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-parameter-store.html)
- [Documentación oficial de AWS AppConfig](https://docs.aws.amazon.com/appconfig/latest/userguide/what-is-appconfig.html)
- [Documentación oficial de EKS - IRSA](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
- [Documentación oficial de EKS - Cifrado de Secrets](https://docs.aws.amazon.com/eks/latest/userguide/enable-kms.html)
- [Documentación oficial de AWS Controllers for Kubernetes (ACK)](https://aws-controllers-k8s.github.io/community/)
