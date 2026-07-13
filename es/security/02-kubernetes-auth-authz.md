# Sistema de autenticación y autorización de Kubernetes

> **Versiones compatibles**: Kubernetes 1.31, 1.32, 1.33
> **Última actualización**: February 19, 2026

## Descripción general

El sistema de autenticación y autorización de Kubernetes es un elemento central de la seguridad del cluster. Este documento ofrece una mirada detallada a los mecanismos de autenticación y autorización de Kubernetes y explica cómo configurarlos en entornos reales.

## Autenticación

La autenticación es el proceso de verificar que un usuario o servicio sea quien afirma ser. Kubernetes admite varios métodos de autenticación, y estos pueden habilitarse simultáneamente.

### Estrategias de autenticación

#### 1. Certificados X.509

Los certificados X.509 son el método de autenticación más común en Kubernetes. Los certificados de cliente deben estar firmados por la Certificate Authority (CA) del cluster.

**Ejemplo de generación de certificados:**

```bash
# Generate private key
openssl genrsa -out john.key 2048

# Generate Certificate Signing Request (CSR)
openssl req -new -key john.key -out john.csr -subj "/CN=john/O=engineering"

# Sign CSR with Kubernetes CA
openssl x509 -req -in john.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out john.crt -days 365
```

**Configuración de kubeconfig:**

```yaml
apiVersion: v1
kind: Config
clusters:
- name: my-cluster
  cluster:
    certificate-authority-data: <BASE64_ENCODED_CA_CERT>
    server: https://kubernetes.example.com
users:
- name: john
  user:
    client-certificate-data: <BASE64_ENCODED_CLIENT_CERT>
    client-key-data: <BASE64_ENCODED_CLIENT_KEY>
contexts:
- name: john@my-cluster
  context:
    cluster: my-cluster
    user: john
current-context: john@my-cluster
```

#### 2. Tokens de Service Account

Las Service Accounts proporcionan identidad para los procesos que se ejecutan dentro de pods. Cada namespace tiene una Service Account predeterminada, y se pueden crear Service Accounts adicionales.

**Creación de Service Account:**

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-service-account
  namespace: default
```

**Asignación de Service Account a Pod:**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: my-pod
spec:
  serviceAccountName: my-service-account
  containers:
  - name: my-container
    image: nginx
```

#### 3. OpenID Connect (OIDC)

OIDC admite autenticación mediante proveedores de identidad externos (por ejemplo, Google, Azure AD, Okta).

**Ejemplo de configuración del API Server:**

```yaml
apiVersion: v1
kind: Config
clusters:
- name: my-cluster
  cluster:
    server: https://kubernetes.example.com
    certificate-authority-data: <BASE64_ENCODED_CA_CERT>
users:
- name: oidc-user
  user:
    auth-provider:
      name: oidc
      config:
        client-id: <CLIENT_ID>
        client-secret: <CLIENT_SECRET>
        id-token: <ID_TOKEN>
        refresh-token: <REFRESH_TOKEN>
        idp-issuer-url: https://accounts.google.com
contexts:
- name: oidc-context
  context:
    cluster: my-cluster
    user: oidc-user
current-context: oidc-context
```

#### 4. Autenticación con token Webhook

La autenticación con token Webhook valida tokens mediante un servicio externo.

**Configuración del API Server:**

```yaml
apiVersion: v1
kind: Config
# ...
authentication:
  webhook:
    config:
      url: https://authn.example.com/authenticate
      caCert: <BASE64_ENCODED_CA_CERT>
```

#### 5. Proxy de autenticación

Un proxy de autenticación se ubica delante del API Server para gestionar la autenticación.

**Configuración del API Server:**

```yaml
apiVersion: v1
kind: Config
# ...
authentication:
  proxy:
    headerName: X-Remote-User
    usernameHeaders: ["X-Remote-User"]
    groupHeaders: ["X-Remote-Group"]
```

### Usuarios y grupos

En Kubernetes, los usuarios se clasifican de la siguiente manera:

1. **Usuarios regulares**: Se gestionan fuera del cluster; Kubernetes no los gestiona directamente.
2. **Service Accounts**: Cuentas gestionadas por la API de Kubernetes.

Los usuarios pueden pertenecer a uno o más grupos, y los grupos se utilizan en las políticas de autorización.

## Autorización

La autorización es el proceso de verificar si un usuario autenticado tiene permiso para realizar la acción solicitada. Kubernetes admite varios módulos de autorización.

### Modos de autorización

#### 1. RBAC (Role-Based Access Control)

RBAC proporciona control de acceso basado en roles y actualmente es el mecanismo de autorización más utilizado en Kubernetes.

**Conceptos clave:**

1. **Role**: Define permisos dentro de un namespace.
2. **ClusterRole**: Define permisos en todo el cluster.
3. **RoleBinding**: Vincula un Role a usuarios, grupos o Service Accounts.
4. **ClusterRoleBinding**: Vincula un ClusterRole a usuarios, grupos o Service Accounts.

**Ejemplo de Role:**

```yaml
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

**Ejemplo de RoleBinding:**

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: read-pods
  namespace: default
subjects:
- kind: User
  name: john
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
```

**Ejemplo de ClusterRole:**

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: secret-reader
rules:
- apiGroups: [""]
  resources: ["secrets"]
  verbs: ["get", "watch", "list"]
```

**Ejemplo de ClusterRoleBinding:**

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: read-secrets-global
subjects:
- kind: Group
  name: security-team
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: ClusterRole
  name: secret-reader
  apiGroup: rbac.authorization.k8s.io
```

#### 2. ABAC (Attribute-Based Access Control)

ABAC proporciona control de acceso basado en atributos. Las políticas se definen en archivos JSON.

**Ejemplo de política:**

```json
{
  "apiVersion": "abac.authorization.kubernetes.io/v1beta1",
  "kind": "Policy",
  "spec": {
    "user": "john",
    "namespace": "default",
    "resource": "pods",
    "readonly": true
  }
}
```

#### 3. Autorización de Node

La autorización de Node se utiliza cuando los kubelets acceden al API Server.

#### 4. Autorización Webhook

La autorización Webhook toma decisiones de autorización mediante un servicio externo.

**Configuración del API Server:**

```yaml
apiVersion: v1
kind: Config
# ...
authorization:
  webhook:
    config:
      url: https://authz.example.com/authorize
      caCert: <BASE64_ENCODED_CA_CERT>
```

### Mejores prácticas de autorización

1. **Principio de mínimo privilegio**: Concede solo los permisos mínimos necesarios.
2. **Separación de roles**: Concede permisos adecuados según roles como administradores, desarrolladores y operadores.
3. **Separación de namespaces**: Separa los namespaces por equipo o proyecto y concede permisos adecuados.
4. **Separación de Service Accounts**: Usa Service Accounts separadas para cada aplicación.
5. **Auditoría regular**: Revisa y actualiza periódicamente las políticas de autorización.

## Admission Control

Admission control realiza validación y modificación adicionales antes de procesar las solicitudes después de la autenticación y la autorización.

### Tipos de Admission Controller

1. **Mutating Admission Controllers**: Pueden modificar solicitudes.
2. **Validating Admission Controllers**: Solo validan solicitudes sin modificarlas.

### Admission Controllers clave

1. **LimitRanger**: Establece límites de recursos para pods y containers.
2. **ResourceQuota**: Limita el uso de recursos por namespace.
3. **PodSecurityPolicy**: Restringe los contextos de seguridad de pods.
4. **ServiceAccount**: Asigna automáticamente Service Accounts a pods.
5. **DefaultStorageClass**: Establece la storage class predeterminada.

### Admission Control dinámico

Admission control dinámico se implementa mediante webhooks:

1. **MutatingAdmissionWebhook**: Puede modificar solicitudes.
2. **ValidatingAdmissionWebhook**: Solo valida solicitudes sin modificarlas.

**Ejemplo de configuración de Webhook:**

```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingWebhookConfiguration
metadata:
  name: pod-policy-webhook
webhooks:
- name: pod-policy.example.com
  clientConfig:
    url: https://pod-policy.example.com/validate
    caBundle: <BASE64_ENCODED_CA_CERT>
  rules:
  - apiGroups: [""]
    apiVersions: ["v1"]
    resources: ["pods"]
    operations: ["CREATE", "UPDATE"]
    scope: "Namespaced"
  admissionReviewVersions: ["v1"]
  sideEffects: None
  timeoutSeconds: 5
```

## Ejemplos prácticos de implementación

### Configuración de autenticación y autorización en EKS

#### Integración de IAM y RBAC

Amazon EKS integra AWS IAM con Kubernetes RBAC para proporcionar autenticación y autorización.

**ConfigMap aws-auth:**

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: aws-auth
  namespace: kube-system
data:
  mapRoles: |
    - rolearn: arn:aws:iam::123456789012:role/EKSAdminRole
      username: admin
      groups:
        - system:masters
    - rolearn: arn:aws:iam::123456789012:role/EKSDeveloperRole
      username: developer
      groups:
        - developers
  mapUsers: |
    - userarn: arn:aws:iam::123456789012:user/john
      username: john
      groups:
        - developers
```

#### Configuración de proveedor OIDC

```bash
# Create OIDC provider
eksctl utils associate-iam-oidc-provider \
    --cluster my-cluster \
    --approve

# Create IAM role and associate with service account
eksctl create iamserviceaccount \
    --name my-service-account \
    --namespace default \
    --cluster my-cluster \
    --attach-policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess \
    --approve
```

### Seguridad de clusters multi-tenant

En entornos multi-tenant, el aislamiento entre tenants es importante.

**Aislamiento de namespace:**

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: tenant-a
  labels:
    tenant: a
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-from-other-namespaces
  namespace: tenant-a
spec:
  podSelector: {}
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          tenant: a
```

**Cuotas de recursos:**

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: tenant-a-quota
  namespace: tenant-a
spec:
  hard:
    pods: "10"
    requests.cpu: "4"
    requests.memory: 8Gi
    limits.cpu: "8"
    limits.memory: 16Gi
```

## Mejores prácticas de seguridad

1. **Rotación regular de certificados**: Renueva los certificados periódicamente.
2. **Deshabilitar el montaje automático de tokens de Service Account**: Deshabilita el montaje automático de tokens de Service Account cuando no sea necesario.
3. **Minimizar las políticas RBAC**: Concede solo los permisos mínimos necesarios.
4. **Implementar Network Policies**: Restringe la comunicación entre pods.
5. **Habilitar audit logging**: Registra y monitorea todas las solicitudes a la API.
6. **Configurar security contexts**: Configura correctamente los security contexts para pods y containers.
7. **Image scanning**: Escanea periódicamente las imágenes de container en busca de vulnerabilidades.

## Conclusión

El sistema de autenticación y autorización de Kubernetes es un elemento central de la seguridad del cluster. Al seleccionar métodos de autenticación adecuados, implementar control de acceso detallado mediante RBAC y aplicar políticas de seguridad adicionales usando admission controllers, puedes construir un entorno de Kubernetes seguro.

La autenticación, la autorización y admission control se complementan entre sí, y es importante usarlos juntos para implementar una estrategia de Defense in Depth.
