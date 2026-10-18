# Configuración y Secrets

> **Versiones compatibles**: Kubernetes 1.35, 1.36, 1.37
> **Última actualización**: October 16, 2026

En Kubernetes, la gestión de la configuración es una parte importante de la administración de los ajustes de las aplicaciones por separado del código. En este capítulo, exploraremos en detalle los métodos de gestión de la configuración de Kubernetes, incluidos ConfigMaps, Secrets, las variables de entorno y el montaje de la configuración mediante volúmenes.

## Configuración del entorno de laboratorio

Para seguir los ejemplos de este documento, necesitarás las siguientes herramientas y el siguiente entorno:

### Herramientas necesarias
- kubectl, con una diferencia máxima de una versión secundaria respecto a la del servidor de API
- Un clúster de Kubernetes en funcionamiento (EKS, minikube, kind, etc.)

### Configuración del ejemplo de configuración

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
kubectl -n config-demo apply -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: config-test-pod
spec:
  containers:
  - name: test-container
    image: busybox
    command: ["sh", "-c", 'test -n "$DB_PASSWORD" && echo "Secret available" && sleep 3600']
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

## Gestión de la configuración de un vistazo

![Los administradores del clúster, los pipelines de GitOps y los sistemas externos crean ConfigMaps y Secrets, que los Pods consumen como variables de entorno, montajes de volúmenes y Secrets para extraer imágenes. ConfigMap alimenta la recarga automática del sidecar y Secret alimenta el cifrado de KSOPS y la inyección dinámica de Vault Injector como funciones avanzadas.](../.gitbook/assets/en-core-05-configuration-secrets-0.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-05-configuration-secrets-0.html)

## Tabla de contenido

1. [ConfigMap](#configmap)
2. [Secret](#secret)
3. [Variables de entorno](#environment-variables)
4. [Montaje de la configuración mediante volúmenes](#mounting-configuration-through-volumes)
5. [Prácticas recomendadas para la configuración](#configuration-best-practices)
6. [Gestión de la configuración en Amazon EKS](#configuration-management-in-amazon-eks)

## ConfigMap

> **Concepto clave**: ConfigMaps almacenan datos de configuración en pares clave-valor y separan el código de la aplicación de la configuración.

ConfigMaps son objetos de API que almacenan datos de configuración en pares clave-valor. El uso de ConfigMaps permite separar los datos de configuración de las imágenes de contenedor, lo que hace que las aplicaciones sean más portables.

### Comparación entre ConfigMap y Secret

| Característica | ConfigMap | Secret |
|---------|-----------|--------|
| **Propósito** | Datos de configuración generales | Datos de configuración sensibles |
| **Representación en la API** | `data` en UTF-8 o `binaryData` en base64 | `data` en base64; se acepta `stringData` al escribir |
| **Límite de tamaño** | 1 MiB | 1 MiB |
| **Cifrado en reposo** | Depende de la configuración del servidor de API o de la plataforma | Depende de la configuración del servidor de API o de la plataforma |
| **Tipo de volumen** | configMap | secret |
| **Casos de uso** | Variables de entorno, archivos de configuración | Contraseñas, tokens, certificados |
| **Actualización automática** | Puede haber demora cuando se monta como volumen | Puede haber demora cuando se monta como volumen |

### Métodos para crear ConfigMaps

ConfigMaps se pueden crear de varias maneras:

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

### Métodos para usar ConfigMaps

ConfigMaps se pueden usar de las siguientes maneras:

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

![Los Pods consumen los datos clave-valor de un ConfigMap (key1, key2, config.properties) de tres formas: como variables de entorno, como volumen montado o como argumentos de línea de comandos. La ruta de las variables de entorno se resuelve en env.key1/env.key2, y la ruta del volumen, en archivos ubicados en /etc/config dentro del contenedor.](../.gitbook/assets/en-core-05-configuration-secrets-1.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-05-configuration-secrets-1.html)

### Creación de ConfigMaps

ConfigMaps se pueden crear de varias maneras:

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

### Uso de ConfigMaps

ConfigMaps se pueden usar en Pods de las siguientes maneras:

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

### Actualización de ConfigMaps

Los ConfigMaps y Secrets mutables montados como volúmenes completos se actualizan eventualmente; la demora depende de la sincronización de kubelet y de la configuración de detección de cambios y caché. Las aplicaciones deben volver a leer o recargar los archivos. Los montajes `subPath` no reciben actualizaciones. Los valores de entorno no cambian en un proceso en ejecución; vuelve a crear los Pods (por ejemplo, mediante un rollout de Deployment) para usar los nuevos valores.

```bash
kubectl edit configmap my-config
```

O bien

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

Secrets son objetos de API que almacenan información sensible, como contraseñas, tokens de OAuth y claves SSH. Secrets son similares a ConfigMaps, pero ofrecen funciones de seguridad adicionales para almacenar datos sensibles.

![Tipos compatibles de Secret de Kubernetes (Opaque, TLS, dockerconfigjson, basic-auth) y su codificación base64, además del almacenamiento opcional con cifrado de etcd. También se muestran las tres formas en que un Pod lo consume: como variables de entorno, como volumen montado o como Secret para extraer imágenes.](../.gitbook/assets/en-core-05-configuration-secrets-2.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-05-configuration-secrets-2.html)

### Tipos de Secret

Kubernetes ofrece varios tipos de Secret:

- **Opaque**: tipo predeterminado, almacena datos arbitrarios definidos por el usuario.
- **kubernetes.io/service-account-token**: almacena tokens de cuentas de servicio.
- **kubernetes.io/dockercfg**: almacena la forma serializada de un archivo `.dockercfg`.
- **kubernetes.io/dockerconfigjson**: almacena la forma serializada de un archivo `.docker/config.json`.
- **kubernetes.io/basic-auth**: almacena credenciales para la autenticación básica.
- **kubernetes.io/ssh-auth**: almacena credenciales para la autenticación SSH.
- **kubernetes.io/tls**: almacena certificados y claves TLS.
- **bootstrap.kubernetes.io/token**: almacena datos de tokens de arranque.

### Creación de Secrets

Secrets se pueden crear de varias maneras:

#### Imperativa

```bash
# Create from literal values
kubectl create secret generic my-secret --from-literal=username=admin --from-literal=password=secret

# Create from files
kubectl create secret generic my-secret --from-file=username=username.txt --from-file=password=password.txt

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

También puedes usar el campo `stringData` para proporcionar valores sin codificar:

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

### Uso de Secrets

Secrets se pueden usar en Pods de las siguientes maneras:

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
    command: ["/bin/sh", "-c", 'test -n "$USERNAME" && echo "Secret available"']
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

#### Secrets para extraer imágenes

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

### Consideraciones de seguridad de Secret

Los Secrets se codifican en base64 de forma predeterminada, pero esto no es cifrado. Para reforzar la seguridad de los Secrets, considera los siguientes métodos:

1. **Cifrado de etcd**: cifra los Secrets almacenados en etcd.
2. **RBAC**: restringe el acceso a los Secrets.
3. **Políticas de red**: restringe el acceso de red a la API o a los almacenes externos cuando sea compatible; la autorización de los objetos Secret se aplica mediante RBAC, no mediante NetworkPolicy.
4. **Herramientas externas de gestión de Secrets**: usa herramientas externas de gestión de Secrets, como AWS Secrets Manager, HashiCorp Vault, etc.

Todas las credenciales que se muestran aquí son valores ficticios para aprender. No registres el contenido de Secret ni confirmes valores reales o sus equivalentes en base64; es preferible usar archivos de entrada protegidos o un gestor externo de Secrets en lugar de argumentos literales de CLI. Los usuarios que puedan crear Pods que usen un Secret pueden obtenerlo, incluso sin permiso directo para leer Secrets.

#### Configuración del cifrado de etcd

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

En clústeres autogestionados, carga este archivo con `--encryption-provider-config`, protege la clave de cifrado y vuelve a escribir los Secrets existentes para cifrarlos. No es un recurso para `kubectl apply`. EKS administra su propio cifrado (ver más abajo).

## Variables de entorno {#environment-variables}

Las variables de entorno son una forma sencilla de pasar información de configuración a los contenedores. Kubernetes ofrece varias maneras de establecer variables de entorno.

![Las cuatro fuentes que Kubernetes puede usar para asignar variables de entorno a un Container: un valor estático directo, una clave de ConfigMap o una referencia envFrom completa, una clave de Secret o una referencia envFrom completa, y las referencias a campos o recursos de la API Downward.](../.gitbook/assets/en-core-05-configuration-secrets-3.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-05-configuration-secrets-3.html)

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
          key: key1
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
    command: ["/bin/sh", "-c", 'test -n "$DATABASE_PASSWORD" && echo "Secret available"']
    env:
    - name: DATABASE_PASSWORD
      valueFrom:
        secretKeyRef:
          name: my-secret
          key: password
  restartPolicy: Never
```

### Configuración mediante la API Downward

La API Downward permite exponer información del Pod y del contenedor como variables de entorno.

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

## Montaje de la configuración mediante volúmenes {#mounting-configuration-through-volumes}

Montar archivos de configuración en los contenedores mediante volúmenes ofrece un método de gestión de la configuración más flexible que las variables de entorno.

![Un Pod define Volumes respaldados por un ConfigMap o un Secret; su Container los monta mediante Volume Mounts que hacen referencia a esos Volumes. Hay cuatro opciones de montaje disponibles: montaje de volumen completo, solo claves específicas (items), solo lectura (readOnly) y montaje subPath.](../.gitbook/assets/en-core-05-configuration-secrets-4.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-05-configuration-secrets-4.html)

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

### Montaje de un archivo específico

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

### Montaje SubPath

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: subpath-mount-pod
spec:
  containers:
  - name: test-container
    image: busybox
    command: [ "/bin/sh", "-c", "cat /etc/config/config.properties" ]
    volumeMounts:
    - name: config-volume
      mountPath: /etc/config/config.properties
      subPath: config.properties
  volumes:
  - name: config-volume
    configMap:
      name: my-config
  restartPolicy: Never
```

## Prácticas recomendadas para la configuración {#configuration-best-practices}

Ten en cuenta las siguientes prácticas recomendadas al administrar la configuración en Kubernetes:

### 1. Separar la configuración del código

Administra el código de la aplicación y la configuración por separado. Así se elimina la necesidad de volver a compilar la aplicación cuando se cambia la configuración.

### 2. Gestión de la configuración específica de cada entorno

Administra la configuración por separado para distintos entornos, como desarrollo, pruebas y producción. Puedes usar namespaces para separar los entornos y usar distintos ConfigMaps y Secrets para cada uno.

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

### 3. Usar Secrets para información sensible

Usa siempre Secrets para almacenar información sensible, como contraseñas, claves de API y certificados. Usa ConfigMaps solo para datos de configuración no sensibles.

### 4. Mantener la inmutabilidad

Al cambiar la configuración, crea una nueva versión en lugar de modificar la existente. Esto facilita las reversiones y permite hacer un seguimiento del historial de cambios de configuración.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: my-config-v1
immutable: true
data:
  log_level: INFO
  # Configuration data
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: my-config-v2
immutable: true
data:
  log_level: DEBUG
  # Updated configuration data
```

### 5. Reiniciar los Pods cuando cambie la configuración

La configuración usada como variables de entorno requiere reiniciar el Pod para actualizarse. Usa Deployments para realizar actualizaciones graduales.

```bash
kubectl rollout restart deployment/my-deployment
```

### 6. Validar la configuración

Valida la configuración antes de aplicarla. Una configuración no válida puede provocar fallos en la aplicación.

### 7. Documentar la configuración

Documenta las opciones de configuración y sus efectos. Esto ayuda a los miembros del equipo a comprender y administrar la configuración.

### Solicitudes de recursos y QoS

Las solicitudes orientan la planificación y la asignación de recursos en tiempo de ejecución; no obligan a una aplicación a consumir esa cantidad. Los límites de CPU restringen el uso de CPU, mientras que los límites de memoria pueden provocar la terminación por OOM. En los ejemplos del cuestionario a nivel de contenedor, Guaranteed requiere solicitudes y límites de CPU y memoria iguales en cada contenedor; BestEffort no tiene ninguno, y las demás configuraciones son Burstable. Los recursos a nivel de Pod también pueden afectar a QoS. La expulsión por presión en el nodo también tiene en cuenta la prioridad y el uso en relación con las solicitudes. Consulta [gestión de recursos](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/) y [QoS de Pod](https://kubernetes.io/docs/concepts/workloads/pods/pod-qos/).

## Gestión de la configuración en Amazon EKS {#configuration-management-in-amazon-eks}

En Amazon EKS, además de las funciones básicas de gestión de la configuración de Kubernetes, puedes usar distintos servicios de AWS para administrar la configuración y los Secrets. En esta sección se describen varias maneras de gestionar la configuración en EKS y de integrarla con los servicios de AWS.

![Un clúster de Amazon EKS usa ConfigMaps y Secrets nativos de Kubernetes e integra AWS Secrets Manager, Parameter Store, AppConfig, KMS e IAM. Herramientas de integración como External Secrets Operator, ASCP, IRSA y ACK crean o montan Secrets, los cifran con KMS y conceden a los Pods permisos de IAM con alcance limitado.](../.gitbook/assets/en-core-05-configuration-secrets-5.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-05-configuration-secrets-5.html)

### Integración con AWS Secrets Manager

AWS Secrets Manager es un servicio que permite almacenar y administrar de forma segura credenciales de bases de datos, claves de API y otra información secreta. External Secrets Operator reconcilia Secrets de Kubernetes. ASCP con Secrets Store CSI Driver monta valores externos como archivos; la sincronización de Secrets de Kubernetes y la rotación automática requieren una configuración opcional del controlador.

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
apiVersion: external-secrets.io/v1
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
apiVersion: external-secrets.io/v1
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

External Secrets Operator necesita permisos de IAM adecuados para acceder a AWS Secrets Manager. Puedes usar IRSA para asociar roles de IAM a cuentas de servicio de Kubernetes.

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
  --attach-policy-arn arn:aws:iam::123456789012:policy/ReadAppDatabaseSecret \
  --approve
```

Primero crea `ReadAppDatabaseSecret` con `secretsmanager:GetSecretValue` y `secretsmanager:DescribeSecret` restringidos al ARN completo de `prod/db/credentials`; agrega `kms:Decrypt` con alcance limitado solo si una clave administrada por el cliente lo requiere. La política de confianza de IAM debe coincidir con este clúster, namespace y ServiceAccount. Instala ESO y sus CRD v1, y crea el namespace y la ServiceAccount antes de crear SecretStore.

### Uso de AWS Parameter Store

AWS Systems Manager Parameter Store es un servicio que permite almacenar y administrar jerárquicamente datos de configuración y valores secretos. Elige entre Parameter Store y Secrets Manager según los requisitos de rotación, ciclo de vida y acceso; los cargos dependen del nivel del parámetro y del uso de la API.

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
  serviceAccountName: parameter-reader
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

Crea `parameter-reader` con un rol de IRSA o una asociación de Pod Identity que conceda `ssm:GetParameters` para los ARN de los dos parámetros y, si hace falta, descifrado de KMS con alcance limitado. El rol anterior de Secrets Manager no proporciona permisos de SSM. ASCP requiere una combinación compatible de nodo y complemento; el montaje CSI no funciona en Fargate. Hybrid Nodes requiere la versión del complemento compatible indicada explícitamente y la configuración de credenciales correspondiente.

### Configuración dinámica con AWS AppConfig

AWS AppConfig es un servicio que administra y despliega la configuración de aplicaciones. AppConfig permite actualizar la configuración dinámicamente sin volver a desplegar las aplicaciones.

#### Patrón de sidecar de AppConfig Agent

La aplicación obtiene la configuración desde el endpoint HTTP local del agente y debe actualizarla o recargarla. Un emptyDir compartido, por sí solo, no hace que el agente escriba en `/config/config.json`. Primero crea el perfil de aplicación, entorno y configuración, y concede a la identidad del Pod los permisos `appconfig:StartConfigurationSession` y `appconfig:GetLatestConfiguration` para la configuración necesaria.

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
      serviceAccountName: appconfig-reader
      containers:
      - name: app
        image: my-app:latest
        env:
        - name: CONFIG_URL
          value: http://localhost:2772/applications/MyApp/environments/Production/configurations/MyConfig
      - name: appconfig-agent
        image: public.ecr.aws/aws-appconfig/aws-appconfig-agent:2.x
        env:
        - name: SERVICE_REGION
          value: us-west-2
        - name: POLL_INTERVAL
          value: "45s"
        - name: REQUEST_TIMEOUT
          value: "15s"
        - name: HTTP_PORT
          value: "2772"
        - name: HTTP_HOST
          value: localhost
        - name: PREFETCH_LIST
          value: MyApp:Production:MyConfig
```

La imagen de la aplicación debe implementar la obtención de CONFIG_URL y los reintentos mientras se inicia el sidecar. Crea `appconfig-reader` y su identidad de AWS con alcance limitado antes del despliegue; fija una versión o un digest del agente que se haya probado en producción. Se trata de ajustes del agente de contenedor, no de variables de extensión de Lambda.

### Configuración con perfiles de EKS Fargate

El uso de EKS Fargate permite ejecutar Pods de Kubernetes sin administrar nodos. Puedes configurar el entorno de ejecución del Pod mediante perfiles de Fargate.

Los perfiles de Fargate son recursos de la API de EKS, no objetos nativos de Kubernetes. Por ejemplo, usa esta configuración de `eksctl` con `eksctl create fargateprofile -f fargate-profile.yaml` después de reemplazar los ID de subred privada y el rol de ejecución:

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
fargateProfiles:
- name: my-profile
  podExecutionRoleARN: arn:aws:iam::123456789012:role/my-pod-execution-role
  selectors:
  - namespace: my-namespace
    labels:
      environment: production
  subnets:
  - subnet-1234567890abcdef0
  - subnet-0abcdef1234567890
```

### Cifrado de Secrets con AWS KMS {#secret-encryption-with-aws-kms}

Los clústeres de EKS con Kubernetes 1.28 o posterior tienen [cifrado de sobre predeterminado para todos los datos de la API de Kubernetes](https://docs.aws.amazon.com/eks/latest/userguide/envelope-encryption.html), incluidos Secrets y ConfigMaps, con una clave propiedad de AWS. Una clave de KMS administrada por el cliente es opcional; no es necesaria para activar el cifrado.

Para asociar una clave administrada por el cliente a un clúster existente que cumpla los requisitos, usa `associate-encryption-config`, no `update-cluster-config`. Revisa la región de la clave, su política, los permisos y las restricciones de asociación antes de aplicarla. El siguiente ejemplo crea una clave y vuelve a usar el ARN que devuelve:

```bash
set -eu
KEY_ARN=$(aws kms create-key --region us-west-2 \
  --description "EKS customer-managed encryption key" \
  --query KeyMetadata.Arn --output text)
aws kms create-alias --region us-west-2 \
  --alias-name alias/eks-secrets --target-key-id "$KEY_ARN"

aws eks associate-encryption-config --region us-west-2 \
  --cluster-name my-cluster \
  --encryption-config "resources=secrets,provider={keyArn=$KEY_ARN}"
```

Comprueba que la operación haya finalizado con `aws eks describe-update`, usando el ID de actualización devuelto, e inspecciona `aws eks describe-cluster --name my-cluster --region us-west-2 --query cluster.encryptionConfig`. La ausencia de una configuración administrada por el cliente no significa que el cifrado predeterminado esté desactivado.

### Control de acceso a Secrets con AWS IAM

El uso de IRSA (IAM Roles for Service Accounts) para asociar roles de IAM a cuentas de servicio de Kubernetes permite que los Pods accedan de forma segura a los servicios de AWS.

#### Crear una cuenta de servicio

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-service-account
  namespace: my-namespace
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/my-iam-role
```

#### Uso de una cuenta de servicio en Pods

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

### Prácticas recomendadas para la configuración de EKS

Ten en cuenta las siguientes prácticas recomendadas al administrar la configuración en EKS:

1. **Usa la identidad de la carga de trabajo**: usa EKS Pod Identity en cómputo compatible o IRSA, con permisos de alcance limitado. Las aplicaciones de Fargate usan IRSA; su rol de ejecución de Pod es para la infraestructura, no para las credenciales de la aplicación.

2. **Cifra Secrets**: usa KMS para cifrar Secrets en tu clúster de EKS.

3. **Gestión externa de Secrets**: usa servicios externos de gestión de Secrets, como AWS Secrets Manager o Parameter Store, para administrar información sensible.

4. **Gestión de versiones de configuración**: usa AWS AppConfig o Parameter Store para administrar las versiones de configuración.

5. **Separación de la configuración por entorno**: administra la configuración por separado para los entornos de desarrollo, pruebas y producción. Usa namespaces de Kubernetes y etiquetas de recursos de AWS.

6. **Minimiza las políticas de IAM**: sigue el principio de privilegio mínimo al acceder a los servicios de AWS.

7. **Automatización de la configuración**: usa herramientas como AWS CloudFormation, AWS CDK o Terraform para automatizar la gestión de la configuración.

### Herramientas de gestión de la configuración de EKS

Veamos algunas herramientas que ayudan a administrar la configuración en EKS:

#### AWS Controllers for Kubernetes (ACK)

ACK es una herramienta que permite administrar recursos de AWS desde Kubernetes. ACK permite crear y administrar recursos de AWS mediante manifiestos de Kubernetes.

```yaml
apiVersion: secretsmanager.services.k8s.aws/v1alpha1
kind: Secret
metadata:
  name: my-secret
  annotations:
    services.k8s.aws/deletion-policy: retain
spec:
  name: my-secret
  description: "My secret created via ACK"
  recoveryWindowInDays: 30
```

Primero instala el controlador ACK Secrets Manager y su rol de IAM y sus CRD. Este manifiesto administra los metadatos del contenedor del secreto; no genera una contraseña ni crea un Secret nativo de Kubernetes. Introduce el valor del secreto mediante un flujo de trabajo controlado de gestión de secretos.

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

Este helper funciona con un clúster de EKS de CDK existente y un construct Secret; concede acceso de lectura solo a ese Secret. El namespace debe existir y el clúster debe tener configurado un proveedor kubectl compatible.

```typescript
import * as eks from 'aws-cdk-lib/aws-eks';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';

export function addSecretReader(
  cluster: eks.Cluster,
  secret: secretsmanager.ISecret,
): eks.ServiceAccount {
  const serviceAccount = cluster.addServiceAccount('SecretReader', {
    name: 'my-service-account',
    namespace: 'my-namespace',
  });
  secret.grantRead(serviceAccount);
  return serviceAccount;
}
```

## Conclusión

En este capítulo, aprendimos sobre los métodos de gestión de la configuración de Kubernetes. ConfigMaps y Secrets ofrecen formas básicas de administrar la configuración de las aplicaciones, y puedes pasar esta configuración a los contenedores mediante variables de entorno y volúmenes. También repasamos las prácticas recomendadas para gestionar la configuración y las herramientas externas de gestión de la configuración.

En entornos de Amazon EKS, puedes lograr una gestión de la configuración más potente y segura usando servicios de AWS junto con las funciones básicas de gestión de la configuración de Kubernetes. Puedes administrar Secrets de forma segura integrando servicios como AWS Secrets Manager, Parameter Store, KMS e IAM, y conceder permisos mínimos a los Pods mediante IRSA. Además, puedes actualizar la configuración dinámicamente sin volver a desplegar las aplicaciones mediante AWS AppConfig.

Una gestión eficaz de la configuración es importante para mejorar la mantenibilidad, la escalabilidad y la seguridad de las aplicaciones de Kubernetes. Es importante elegir la estrategia de gestión de la configuración adecuada para los requisitos de tu aplicación y seguir las prácticas recomendadas. En entornos de EKS, puedes crear soluciones de gestión de la configuración más potentes mediante la integración con los servicios de AWS.

En el próximo capítulo, aprenderemos sobre la seguridad de Kubernetes.

## Cuestionario

Para poner a prueba lo que aprendiste en este capítulo, prueba el [cuestionario sobre configuración y Secrets](../quizzes/core/05-configuration-secrets-quiz.md).

## Referencias

- [Documentación oficial de Kubernetes: ConfigMaps](https://kubernetes.io/docs/concepts/configuration/configmap/)
- [Documentación oficial de Kubernetes: Secrets](https://kubernetes.io/docs/concepts/configuration/secret/)
- [Documentación oficial de Kubernetes: variables de entorno](https://kubernetes.io/docs/tasks/inject-data-application/define-environment-variable-container/)
- [Documentación oficial de Kubernetes: configurar un Pod para que use un ConfigMap](https://kubernetes.io/docs/tasks/configure-pod-container/configure-pod-configmap/)
- [Documentación oficial de Kubernetes: distribuir credenciales de forma segura mediante Secrets](https://kubernetes.io/docs/tasks/inject-data-application/distribute-credentials-secure/)
- [Documentación oficial de Helm](https://helm.sh/docs/)
- [Documentación oficial de Kustomize](https://kustomize.io/)
- [Documentación oficial de External Secrets Operator](https://external-secrets.io/latest/)
- [Documentación oficial de AWS Secrets Manager](https://docs.aws.amazon.com/secretsmanager/latest/userguide/intro.html)
- [Documentación oficial de AWS Systems Manager Parameter Store](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-parameter-store.html)
- [Documentación oficial de AWS AppConfig](https://docs.aws.amazon.com/appconfig/latest/userguide/what-is-appconfig.html)
- [Documentación oficial de EKS: IRSA](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
- [Documentación oficial de EKS: cifrado de Secrets](https://docs.aws.amazon.com/eks/latest/userguide/enable-kms.html)
- [Documentación oficial de AWS Controllers for Kubernetes (ACK)](https://aws-controllers-k8s.github.io/community/)
