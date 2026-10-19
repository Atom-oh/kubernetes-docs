# Seguridad de Kubernetes

> **Versiones compatibles**: Kubernetes 1.35, 1.36, 1.37
> **Última actualización**: 16 de octubre de 2026

La seguridad de Kubernetes es esencial para proteger los clústeres y las aplicaciones. Este capítulo presenta sus conceptos de seguridad, los mecanismos de autenticación y autorización, las políticas de red y los contextos de seguridad, además de las opciones para reforzar la seguridad en Amazon EKS.

## Configuración del entorno de laboratorio

Para seguir los ejemplos de este documento, necesitas las siguientes herramientas y un entorno de Kubernetes:

### Herramientas necesarias
- kubectl con una diferencia máxima de una versión menor respecto al servidor de API
- Un clúster de Kubernetes en funcionamiento (EKS, minikube, kind, etc.)
- OpenSSL (para crear certificados)

### Configuración del ejemplo de seguridad

```bash
# Create namespace
kubectl create namespace security-demo

# Create service account
kubectl -n security-demo create serviceaccount demo-sa

# Create role
kubectl -n security-demo apply -f - <<EOF
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: pod-reader
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "watch", "list"]
EOF

# Create role binding
kubectl -n security-demo apply -f - <<EOF
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: read-pods
subjects:
- kind: ServiceAccount
  name: demo-sa
  namespace: security-demo
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
EOF

# Create Pod with security context
kubectl -n security-demo apply -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: security-context-demo
spec:
  serviceAccountName: demo-sa
  securityContext:
    runAsUser: 1000
    runAsGroup: 3000
    fsGroup: 2000
    runAsNonRoot: true
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: sec-ctx-demo
    image: busybox
    command: ["sh", "-c", "sleep 3600"]
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
EOF
```

## Arquitectura de seguridad de Kubernetes

![Tres capas de defensa en profundidad: la seguridad de la infraestructura (sistema anfitrión, entorno de ejecución de contenedores y red) sirve de base a la seguridad del servidor de API. La seguridad del clúster combina autenticación, autorización, control de admisión, registros de auditoría y cifrado de datos. De estas capas se derivan los controles de las cargas de trabajo: RBAC, Pod Security Standards, políticas de red y seguridad de las imágenes.](../.gitbook/assets/en-core-06-security-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-06-security-0.html)

## Tabla de contenido
1. [Descripción general de la seguridad](#security-overview)
2. [Autenticación](#authentication)
3. [Autorización](#authorization)
4. [Contexto de seguridad](#security-context)
5. [Política de red](#network-policy)
6. [Administración de Secrets](#secret-management)
7. [Seguridad de imágenes](#image-security)
8. [Pod Security Standards](#pod-security-standards)
9. [Auditoría](#audit)
10. [Mejora de la seguridad de Amazon EKS](#amazon-eks-security-enhancement)

## Descripción general de la seguridad {#security-overview}

> **Concepto clave**: La seguridad de Kubernetes sigue un enfoque de defensa en profundidad que proporciona varios mecanismos de seguridad en los niveles de infraestructura, clúster y carga de trabajo.

La seguridad de Kubernetes consta de las siguientes áreas principales:

### Comparación de las áreas de seguridad

| Área de seguridad | Componentes principales | Responsable | Mecanismos de seguridad |
|--------------|-----------------|-------------------|---------------------|
| **Seguridad de la infraestructura** | Sistema operativo anfitrión, entorno de ejecución de contenedores, red | Administrador del clúster | Cortafuegos, refuerzo del sistema operativo, seguridad del entorno de ejecución de contenedores |
| **Seguridad del clúster** | Servidor de API, etcd, kubelet | Administrador del clúster | Autenticación, autorización, control de admisión, cifrado |
| **Seguridad de las cargas de trabajo** | Pods, contenedores, Services | Desarrollador de aplicaciones | Contexto de seguridad, políticas de red, RBAC |

### Principios de seguridad

1. **Principio de privilegio mínimo**: Otorgar únicamente los permisos mínimos necesarios
2. **Defensa en profundidad**: Defensa mediante varias capas de seguridad
3. **Denegación predeterminada**: Denegar todo lo que no se permita explícitamente
4. **Refuerzo de la seguridad**: Aplicar configuraciones de seguridad más estrictas que las predeterminadas
5. **Supervisión continua**: Detectar y responder a eventos de seguridad

## Autenticación {#authentication}

El acceso al servidor de API de Kubernetes requiere autenticación. Kubernetes admite varios métodos:

![Un usuario o servicio envía una solicitud de autenticación al servidor de API. Este la verifica mediante uno de cinco métodos admitidos: certificados X.509, tokens de cuentas de servicio, OIDC, autenticación de tokens mediante webhook o proxy de autenticación. Después, pasa la solicitud a la etapa de autorización o la rechaza.](../.gitbook/assets/en-core-06-security-1.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-06-security-1.html)

### Certificados X.509

Kubernetes usa certificados TLS para autenticar clientes. Se utilizan principalmente para la comunicación interna del clúster y la autenticación de administradores.

```bash
# Example kubeconfig setup for certificate-based authentication
kubectl config set-credentials admin --client-certificate=admin.crt --client-key=admin.key
```

### Tokens de cuentas de servicio

Las cuentas de servicio permiten que los procesos de los Pods se comuniquen con el servidor de API. Actualmente, los Pods suelen recibir tokens proyectados de corta duración, vinculados al Pod, mediante la API TokenRequest. kubelet los rota, por lo que las aplicaciones deben volver a leer el archivo del token. Desde v1.24, crear un ServiceAccount no genera automáticamente un Secret con un token de larga duración. Establece `automountServiceAccountToken: false` cuando no sean necesarias credenciales de API, como en este ejemplo de servidor web. Para solicitar expresamente un token de corta duración, usa `kubectl create token`; los Secrets con tokens de larga duración constituyen una excepción heredada.

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-service-account
  namespace: default
```

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: my-pod
spec:
  serviceAccountName: my-service-account
  automountServiceAccountToken: false
  containers:
  - name: my-container
    image: nginx:1.30.6
```

### OpenID Connect (OIDC)

Admite la autenticación mediante proveedores de identidad externos (por ejemplo, Google o Microsoft Entra ID). Esto resulta útil para implementar el inicio de sesión único (SSO) en entornos empresariales.

Configura un complemento de inicio de sesión de confianza que utilice client-go ExecCredential y sea compatible con tu proveedor de identidad. Completa después su flujo de inicio de sesión. El fragmento de usuario de kubeconfig siguiente contiene un nombre de ejecutable de ejemplo: sustitúyelo por el complemento instalado y sus argumentos documentados. La autenticación IAM de EKS utiliza tokens firmados por AWS, por ejemplo mediante `aws eks get-token`; en este caso, IAM no actúa como un proveedor de identidad OIDC genérico.

```yaml
users:
- name: oidc-user
  user:
    exec:
      apiVersion: client.authentication.k8s.io/v1
      command: oidc-login-helper
      interactiveMode: IfAvailable
      provideClusterInfo: true
```

### Autenticación de tokens mediante webhook

Método que valida tokens mediante un servicio de autenticación externo. El servidor de API reenvía los tokens a un servicio externo, que los valida y devuelve información del usuario.

### Proxy de autenticación

Un proxy de autenticación situado delante del servidor de API autentica a los usuarios. Incluye la información del usuario autenticado en los encabezados HTTP y la reenvía al servidor de API.

## Autorización {#authorization}

Si la autenticación es el proceso de verificar «quién eres», la autorización es el proceso de determinar «qué puedes hacer». Kubernetes admite varios modos de autorización:

![Un usuario o servicio autenticado envía una solicitud de autorización al servidor de API. Este la evalúa mediante RBAC, ABAC, Node o Webhook y decide si la procesa o la rechaza. En RBAC, los Roles o ClusterRoles se vinculan a sujetos mediante RoleBindings o ClusterRoleBindings.](../.gitbook/assets/en-core-06-security-2.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-06-security-2.html)

### RBAC (control de acceso basado en roles)

RBAC es el mecanismo de autorización más utilizado en Kubernetes. Mediante Roles y RoleBindings, se otorgan permisos específicos a usuarios o cuentas de servicio para determinados recursos.

#### Role y ClusterRole

Un Role se define en un namespace. Un ClusterRole se define a nivel de clúster y puede describir permisos sobre recursos de un namespace o de todo el clúster. Ninguno concede acceso por sí solo: un RoleBinding limita el acceso a los recursos del namespace donde se crea, mientras que un ClusterRoleBinding concede acceso en todo el clúster.

```yaml
# Namespace Role example
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: default
  name: pod-reader
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "watch", "list"]
```

```yaml
# Cluster-wide ClusterRole example
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: node-reader
rules:
- apiGroups: [""]
  resources: ["nodes"]
  verbs: ["get", "watch", "list"]
```

#### RoleBinding y ClusterRoleBinding

RoleBinding vincula un Role o ClusterRole a usuarios, grupos o cuentas de servicio en un namespace específico. ClusterRoleBinding vincula un ClusterRole a usuarios, grupos o cuentas de servicio en todo el clúster.

```yaml
# RoleBinding example
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: read-pods
  namespace: default
subjects:
- kind: User
  name: jane
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
```

```yaml
# ClusterRoleBinding example
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: read-nodes-global
subjects:
- kind: Group
  name: node-viewers
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: ClusterRole
  name: node-reader
  apiGroup: rbac.authorization.k8s.io
```

### ABAC (control de acceso basado en atributos)

ABAC es un método para otorgar permisos según los atributos del usuario, los atributos del recurso, los atributos del entorno, etc. En Kubernetes, las políticas se definen mediante archivos JSON. Se utiliza con menos frecuencia que RBAC debido a la complejidad de su administración, aunque es más flexible.

### Autorización de nodos

La autorización de nodos es un modo específico para el acceso de los kubelets al servidor de API. Cada kubelet solo puede acceder a los recursos relacionados con el nodo donde se ejecuta, como sus Pods y el estado del nodo.

### Autorización mediante webhook

Las decisiones de autorización pueden delegarse en un servicio externo. El servidor de API le reenvía las solicitudes de autorización y el servicio decide si las permite o las deniega.

## Contexto de seguridad {#security-context}

El contexto de seguridad define la configuración de seguridad del Pod o del contenedor. Permite controlar de forma detallada los privilegios, el acceso, las capacidades y otros aspectos.

![Un Pod incluye un contexto de seguridad propio (runAsUser, runAsGroup, fsGroup, supplementalGroups). Su contenedor dispone de otro contexto de seguridad (privileged, allowPrivilegeEscalation, readOnlyRootFilesystem, capabilities, seLinuxOptions). El Pod en su conjunto debe cumplir uno de los niveles de Pod Security Standards: Privileged, Baseline o Restricted.](../.gitbook/assets/en-core-06-security-3.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-06-security-3.html)

### Contexto de seguridad del Pod

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: security-context-pod
spec:
  securityContext:
    runAsUser: 1000
    runAsGroup: 3000
    fsGroup: 2000
    runAsNonRoot: true
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: security-context-container
    image: busybox:1.36
    command: ["sh", "-c", "sleep 3600"]
    securityContext:
      allowPrivilegeEscalation: false
      capabilities:
        drop:
        - ALL
      readOnlyRootFilesystem: true
```

En el ejemplo anterior:
- `runAsUser`: ID del usuario que ejecuta el proceso del contenedor
- `runAsGroup`: ID del grupo que ejecuta el proceso del contenedor
- `fsGroup`: ID del grupo utilizado para acceder a los volúmenes
- `allowPrivilegeEscalation`: Indica si un proceso puede obtener más privilegios que su proceso padre
- `capabilities`: Añade o elimina capacidades del kernel de Linux
- `readOnlyRootFilesystem`: Monta el sistema de archivos raíz en modo de solo lectura

### Pod Security Standards

PodSecurityPolicy se eliminó en v1.25. Pod Security Admission, estable desde v1.25, permite aplicar los requisitos de Pod Security Standards mediante etiquetas de namespace. Estos estándares son definiciones de políticas; no existe un recurso de API `PodSecurityStandard`. Definen tres niveles:

1. **Privileged**: Sin restricciones; permite todos los privilegios
2. **Baseline**: Bloquea las vías conocidas de escalada de privilegios
3. **Restricted**: Aplica una política de seguridad estrictamente reforzada

```yaml
# Example applying Pod Security Standards to namespace
apiVersion: v1
kind: Namespace
metadata:
  name: my-namespace
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

Las cargas de trabajo Linux sujetas al nivel Restricted deben establecer `runAsNonRoot: true` y `allowPrivilegeEscalation: false`, utilizar un perfil seccomp permitido y eliminar capacidades, además de restringir el acceso al sistema anfitrión. `readOnlyRootFilesystem` es una medida útil de refuerzo, pero el nivel Restricted no la exige por sí mismo. Fija las etiquetas de namespace `*-version` si necesitas mantener una versión concreta de la política.

## Política de red {#network-policy}

Las políticas de red permiten controlar la comunicación entre Pods. De forma predeterminada, todos los Pods de un clúster de Kubernetes pueden comunicarse entre sí, pero esto se puede restringir mediante políticas de red.

![La NetworkPolicy api-allow selecciona Pods mediante podSelector y declara las direcciones Ingress y Egress en policyTypes. Sus reglas definen orígenes y puertos de entrada, y destinos y puertos de salida, mediante podSelector, namespaceSelector e ipBlock. Aplicada al Pod de API, permite únicamente tráfico de Frontend a API por 8080/TCP y de API a Database por 5432/TCP.](../.gitbook/assets/en-core-06-security-4.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-06-security-4.html)

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-allow
  namespace: default
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 8080
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: database
    ports:
    - protocol: TCP
      port: 5432
```

En el ejemplo anterior:
- Define una política de red para los Pods con `app=api`
- Solo permite el tráfico entrante por el puerto 8080 desde Pods con `app=frontend`
- Solo permite el tráfico saliente por el puerto 5432 hacia Pods con `app=database`

Para usar políticas de red, el complemento de red del clúster debe admitirlas. Complementos CNI como Calico, Cilium y Antrea admiten políticas de red.

Estos podSelectors seleccionan Pods del namespace `default`. Los permisos de las políticas se suman, de modo que otra política puede autorizar tráfico adicional. Tanto las reglas de salida del origen como las de entrada del destino deben permitir la conexión. El ejemplo no incluye DNS: si la aplicación resuelve nombres de Service, añade acceso al puerto 53 por TCP y UDP hacia los endpoints DNS que realmente utilice el clúster.

## Administración de Secrets {#secret-management}

Los Secrets de Kubernetes almacenan y gestionan información sensible, como contraseñas, claves de API y certificados. La API de Secret representa `data` en base64, una codificación que no cifra los datos. La protección en reposo depende del clúster: los clústeres autogestionados necesitan configurar el cifrado, mientras que los clústeres actuales de EKS tienen cifrado por envolvente habilitado de forma predeterminada. Ambos requieren RBAC y un tratamiento seguro de los datos por parte de las aplicaciones.

### Cifrado de Secrets

Para cifrar los Secrets almacenados en etcd, configura el cifrado del servidor de API:

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
              secret: <base64-encoded-key>
      - identity: {}
```

El servidor de API autogestionado debe cargar este archivo mediante `--encryption-provider-config`. Protege la clave y vuelve a escribir los Secrets existentes para aplicar el cifrado. Este archivo no es un recurso de Kubernetes que puedas aplicar con kubectl.

### Administración externa de Secrets

Para administrar Secrets de forma más segura, puedes usar sistemas externos de administración de Secrets:

- HashiCorp Vault
- AWS Secrets Manager
- Azure Key Vault
- Google Secret Manager
- External Secrets Operator

## Seguridad de imágenes {#image-security}

La seguridad de las imágenes de contenedores es una parte importante de la seguridad de Kubernetes.

### Análisis de vulnerabilidades de imágenes

Analiza las imágenes de contenedores en busca de vulnerabilidades para identificar y resolver problemas de seguridad conocidos:

- Trivy
- Clair
- Anchore
- AWS ECR Scan
- Docker Hub Scan

### Firma y verificación de imágenes

Verifica el origen y la integridad de las imágenes mediante la firma de imágenes:

- Notary
- Cosign
- Portieris
- AWS Signer
- Connaisseur

### Políticas de imágenes

Utiliza políticas de imágenes para limitar su descarga a registros de confianza:

```yaml
apiVersion: apiserver.config.k8s.io/v1
kind: AdmissionConfiguration
plugins:
- name: ImagePolicyWebhook
  configuration:
    imagePolicy:
      kubeConfigFile: /path/to/kubeconfig
      allowTTL: 50
      denyTTL: 50
      retryBackoff: 500
      defaultAllow: false
```

ImagePolicyWebhook requiere un servicio de políticas en funcionamiento y la configuración de admisión del servidor de API autogestionado. El archivo por sí solo no hace cumplir las reglas sobre registros. EKS no permite modificar libremente las opciones del servidor de API; utiliza webhooks de admisión o controladores de políticas compatibles.

## Auditoría {#audit}

La auditoría de Kubernetes proporciona un mecanismo para registrar y analizar los eventos que ocurren en el clúster.

### Política de auditoría

Las políticas de auditoría definen qué eventos se registran:

```yaml
apiVersion: audit.k8s.io/v1
kind: Policy
rules:
- level: Metadata
  resources:
  - group: ""
    resources: ["secrets", "serviceaccounts/token"]
  - group: "authentication.k8s.io"
    resources: ["tokenreviews"]
- level: Metadata
```

Niveles de auditoría:
- `None`: No registrar eventos
- `Metadata`: Registrar solo los metadatos de la solicitud (usuario, hora, recurso, etc.)
- `Request`: Registrar los metadatos y el cuerpo de la solicitud
- `RequestResponse`: Registrar los metadatos de la solicitud, el cuerpo de la solicitud y el cuerpo de la respuesta

### Backends de registros de auditoría

Los registros de auditoría se pueden almacenar en varios backends:
- Archivo
- Webhook

Los destinos de auditoría integrados son el registro en archivo y el webhook. Para enviar su salida a Elasticsearch o Loki, utiliza un recolector: estas herramientas no son destinos de auditoría dinámicos nativos. El ejemplo registra únicamente metadatos para evitar que los cuerpos de los Secrets y los tokens se copien a los registros. Los clústeres autogestionados necesitan configurar la política y el destino de auditoría en el servidor de API. En EKS, los registros de auditoría se habilitan mediante el registro del plano de control.

## Mejora de la seguridad de Amazon EKS {#amazon-eks-security-enhancement}

Amazon EKS puede mejorar la seguridad mediante la integración con servicios de seguridad de AWS, además de las funciones de seguridad básicas de Kubernetes.

![Integración con los servicios de seguridad de AWS: IAM proporciona identidad a las cargas de trabajo, KMS cifra los datos de la API, los grupos de seguridad restringen el tráfico de red, Secrets Manager suministra secretos, GuardDuty detecta amenazas y WAF protege el tráfico web a través de ALB o CloudFront.](../.gitbook/assets/en-core-06-security-5.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-06-security-5.html)

### Roles de IAM para cuentas de servicio (IRSA)

IRSA (Roles de IAM para cuentas de servicio) permite asociar roles de IAM a cuentas de servicio de Kubernetes para acceder de forma segura a los servicios de AWS.

```bash
# Create OIDC provider
eksctl utils associate-iam-oidc-provider --cluster my-cluster --approve

# Create IAM role and associate with service account
eksctl create iamserviceaccount \
  --name my-service-account \
  --namespace default \
  --cluster my-cluster \
  --attach-policy-arn arn:aws:iam::123456789012:policy/ReadApplicationBucket \
  --approve
```

Crea `ReadApplicationBucket` con el permiso `s3:GetObject` limitado al bucket y al prefijo necesarios. Añade `s3:ListBucket` únicamente si lo necesitas. Evita conceder acceso a todos los buckets mediante una política administrada demasiado amplia. EKS Pod Identity es otra opción para los tipos de cómputo compatibles; las aplicaciones de Fargate utilizan IRSA.

### Cifrado de Secrets con AWS KMS

EKS 1.28+ cifra de forma predeterminada todos los datos de la API de Kubernetes con una clave KMS propiedad de AWS. El uso de una clave administrada por el cliente es opcional. El [capítulo de configuración](./05-configuration-secrets.md#secret-encryption-with-aws-kms) contiene un ejemplo de asociación con el alcance adecuado. La representación en base64 de la API es distinta del cifrado administrado en reposo.

### Grupos de seguridad de AWS

Aplica grupos de seguridad de AWS a los nodos y Pods del clúster de EKS para controlar el tráfico de red.

```bash
# Create security group
SECURITY_GROUP_ID=$(aws ec2 create-security-group \
  --vpc-id vpc-0123456789abcdef0 \
  --group-name eks-client-access --description "EKS client access example" \
  --query GroupId --output text)

# Add inbound rule
aws ec2 authorize-security-group-ingress \
  --group-id "$SECURITY_GROUP_ID" \
  --protocol tcp \
  --port 443 \
  --cidr 10.0.0.0/16
```

Sustituye la VPC y el CIDR por los de tu entorno y asocia el grupo de seguridad al recurso previsto. Crear un grupo no protege por sí solo los nodos o Pods existentes. Los grupos de seguridad para Pods también requieren una configuración compatible de VPC CNI y una SecurityGroupPolicy.

### AWS WAF

AWS WAF protege el tráfico HTTP(S) de las aplicaciones a través de un ALB asociado o una distribución de CloudFront. No se asocia directamente al servidor de API de EKS, a los Pods ni a un NLB. Una Web ACL sin reglas y con `Allow` como acción predeterminada no bloquea tráfico. Configura y prueba las reglas y, después, asocia la ACL regional al ALB de la aplicación en la misma región. Por ejemplo:

```bash
aws wafv2 associate-web-acl \
  --web-acl-arn "$WEB_ACL_ARN" \
  --resource-arn "$APPLICATION_ALB_ARN"
```

### AWS GuardDuty

Usa AWS GuardDuty para detectar y responder a amenazas de seguridad en clústeres de EKS.

Primero, consulta el detector de la cuenta y la región de destino. El análisis de registros de auditoría de EKS (`EKS_AUDIT_LOGS`) y Runtime Monitoring (`RUNTIME_MONITORING`) son funciones independientes. Runtime Monitoring también requiere que los agentes cubran los nodos compatibles. La gestión automatizada de agentes de EKS utiliza `EKS_ADDON_MANAGEMENT`. Si ya utilizas `EKS_RUNTIME_MONITORING`, sigue el procedimiento de migración en lugar de habilitar ambas funciones de supervisión de la ejecución.

```bash
aws guardduty list-detectors
aws guardduty get-detector --detector-id "$DETECTOR_ID"
```

Asigna a `DETECTOR_ID` uno de los ID devueltos. Después, sigue la [configuración de Runtime Monitoring](https://docs.aws.amazon.com/guardduty/latest/ug/runtime-monitoring-configuration.html) y verifica la cobertura. GuardDuty genera hallazgos; la respuesta automatizada requiere flujos de trabajo configurados por separado.

## Prácticas recomendadas de seguridad

Estas son algunas prácticas recomendadas para mejorar la seguridad de los clústeres y las cargas de trabajo de Kubernetes.

### Seguridad del clúster

1. **Mantener las versiones actualizadas**: Mantén Kubernetes y todos sus componentes actualizados para corregir vulnerabilidades conocidas.
2. **Restringir el acceso al servidor de API**: Restringe el acceso al servidor de API y permite el acceso público solo cuando sea necesario.
3. **Cifrado de etcd**: Cifra los datos almacenados en etcd para proteger la información sensible.
4. **Habilitar el registro de auditoría**: Habilita el registro de auditoría para supervisar y analizar la actividad del clúster.
5. **Implementar políticas de red**: Implementa políticas de red para restringir la comunicación entre Pods.

### Seguridad de las cargas de trabajo

1. **Principio de privilegio mínimo**: Otorga a los Pods y contenedores únicamente los permisos mínimos necesarios.
2. **Usuario no root**: Ejecuta los contenedores como usuarios no root.
3. **Sistema de archivos de solo lectura**: Monta como de solo lectura los sistemas de archivos raíz de los contenedores siempre que sea posible.
4. **Límites de recursos**: Establece límites de recursos de CPU y memoria para evitar ataques DoS.
5. **Configurar el contexto de seguridad**: Configura correctamente los contextos de seguridad de los Pods y contenedores.

### Seguridad de imágenes

1. **Imágenes base mínimas**: Usa imágenes base con el mínimo de paquetes.
2. **Análisis de vulnerabilidades de imágenes**: Analiza periódicamente las imágenes de contenedores en busca de vulnerabilidades.
3. **Firma y verificación de imágenes**: Verifica el origen y la integridad de las imágenes mediante la firma de imágenes.
4. **Registros de confianza**: Descarga imágenes únicamente desde registros de confianza.
5. **Usar imágenes actualizadas**: Actualiza periódicamente las imágenes para corregir vulnerabilidades conocidas.

### Administración de Secrets

1. **Administración externa de Secrets**: Usa sistemas externos de administración de Secrets para gestionarlos de forma segura.
2. **Cifrado de Secrets**: Cifra los Secrets almacenados en etcd.
3. **Rotación de Secrets**: Rota periódicamente los Secrets para mejorar la seguridad.
4. **Acceso con privilegios mínimos**: Restringe el acceso a los Secrets a los Pods que lo necesiten.
5. **Usar volúmenes en lugar de variables de entorno**: Monta los Secrets mediante volúmenes en lugar de variables de entorno.

## Conclusión

La seguridad de Kubernetes debe implementarse en varias capas, teniendo en cuenta todas las áreas, incluida la infraestructura del clúster, los componentes de Kubernetes y las cargas de trabajo de las aplicaciones. Además de las funciones de seguridad básicas de Kubernetes, como la autenticación, la autorización, las políticas de red y los contextos de seguridad, puedes mejorar la seguridad del clúster y de las cargas de trabajo mediante medidas adicionales, como la seguridad de las imágenes, la administración de Secrets y el registro de auditoría.

Amazon EKS permite reforzar la seguridad mediante la integración con servicios de AWS. Los roles de IAM para cuentas de servicio (IRSA), el cifrado de Secrets con AWS KMS, los grupos de seguridad de AWS, AWS WAF y AWS GuardDuty contribuyen a proteger el clúster de EKS.

La seguridad exige un trabajo continuo. Mantén la postura de seguridad de los clústeres y las cargas de trabajo mediante evaluaciones y actualizaciones periódicas.

## Cuestionario

Para comprobar lo que aprendiste en este capítulo, prueba el [cuestionario de seguridad](../quizzes/core/06-security-quiz.md).

## Referencias

- [Documentación oficial de Kubernetes - Seguridad](https://kubernetes.io/docs/concepts/security/)
- [Documentación oficial de Kubernetes - Autenticación](https://kubernetes.io/docs/reference/access-authn-authz/authentication/)
- [Documentación oficial de Kubernetes - Autorización](https://kubernetes.io/docs/reference/access-authn-authz/authorization/)
- [Documentación oficial de Kubernetes - RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
- [Documentación oficial de Kubernetes - Políticas de red](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Documentación oficial de Kubernetes - Contexto de seguridad](https://kubernetes.io/docs/tasks/configure-pod-container/security-context/)
- [Documentación oficial de Kubernetes - Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/)
- [Documentación oficial de Kubernetes - Secrets](https://kubernetes.io/docs/concepts/configuration/secret/)
- [Documentación oficial de Kubernetes - Auditoría](https://kubernetes.io/docs/tasks/debug/debug-cluster/audit/)
- [Documentación oficial de Amazon EKS - Seguridad](https://docs.aws.amazon.com/eks/latest/userguide/security.html)
- [Documentación oficial de Amazon EKS - Roles de IAM para cuentas de servicio](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
- [Documentación oficial de Amazon EKS - Cifrado de Secrets](https://docs.aws.amazon.com/eks/latest/userguide/enable-kms.html)
- [Prácticas recomendadas de seguridad de Amazon EKS](https://docs.aws.amazon.com/eks/latest/best-practices/security.html)
