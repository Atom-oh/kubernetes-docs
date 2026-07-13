# Cuestionario sobre autenticación y autorización de Kubernetes

> **Documento relacionado**: [Sistema de autenticación y autorización de Kubernetes](../../security/02-kubernetes-auth-authz.md)

## Preguntas de opción múltiple

### 1. En la autenticación con certificados X.509 de Kubernetes, ¿de qué campo se extrae el nombre de usuario?

- A) Subject Alternative Name (SAN)
- B) Common Name (CN)
- C) Organization Unit (OU)
- D) Issuer

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Common Name (CN)**

**Explicación:**
En los certificados X.509, el Common Name (CN) se asigna al nombre de usuario, y la Organization (O) se asigna a los grupos.

</details>

### 2. ¿Cuál es la principal diferencia entre ClusterRole y Role en RBAC?

- A) ClusterRole es de solo lectura, Role es de lectura/escritura
- B) ClusterRole tiene alcance de todo el cluster, Role tiene alcance de namespace
- C) ClusterRole es solo para administradores, Role es para usuarios normales
- D) ClusterRole se aplica solo a nodes, Role se aplica solo a pods

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) ClusterRole tiene alcance de todo el cluster, Role tiene alcance de namespace**

**Explicación:**
Role define permisos para recursos dentro de un namespace específico, mientras que ClusterRole define permisos para recursos de todo el cluster o recursos que no pertenecen a un namespace.

</details>

### 3. ¿Cuál es la ruta predeterminada donde los tokens de ServiceAccount se montan automáticamente en pods?

- A) /var/run/secrets/kubernetes.io/token
- B) /etc/kubernetes/serviceaccount
- C) /var/run/secrets/kubernetes.io/serviceaccount
- D) /opt/kubernetes/secrets

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) /var/run/secrets/kubernetes.io/serviceaccount**

**Explicación:**
Los tokens de ServiceAccount se montan de forma predeterminada en `/var/run/secrets/kubernetes.io/serviceaccount`.

</details>

### 4. ¿Cuál es el orden de ejecución de MutatingAdmissionWebhook y ValidatingAdmissionWebhook?

- A) Primero Validating, luego Mutating
- B) Primero Mutating, luego Validating
- C) Se ejecutan en paralelo simultáneamente
- D) Se ejecutan aleatoriamente sin orden

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Primero Mutating, luego Validating**

**Explicación:**
Orden de ejecución del admission controller: 1) MutatingAdmissionWebhook (modifica las solicitudes), 2) ValidatingAdmissionWebhook (valida las solicitudes).

</details>

### 5. ¿Qué ConfigMap asigna usuarios/roles de IAM a Kubernetes RBAC en EKS?

- A) kube-config
- B) aws-auth
- C) eks-iam-mapping
- D) cluster-auth

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) aws-auth**

**Explicación:**
En Amazon EKS, el ConfigMap `aws-auth` (en el namespace kube-system) asigna usuarios y roles de AWS IAM a usuarios y grupos de Kubernetes.

</details>

### 6. ¿Qué método de autenticación se recomienda para clusters de Kubernetes en producción?

- A) Archivo de token estático
- B) Autenticación básica
- C) OIDC (OpenID Connect)
- D) Autenticación anónima

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) OIDC (OpenID Connect)**

**Explicación:**
OIDC proporciona autenticación de nivel empresarial con características como expiración de tokens, tokens de renovación e integración con proveedores de identidad como Okta, Azure AD y Google.

</details>

### 7. ¿Cuál es el propósito del grupo `system:masters` en Kubernetes?

- A) Administrar master nodes
- B) Proporcionar privilegios de cluster-admin
- C) Programar pods en master nodes
- D) Administrar namespaces del sistema

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Proporcionar privilegios de cluster-admin**

**Explicación:**
El grupo `system:masters` está vinculado al ClusterRole `cluster-admin`, lo que otorga acceso administrativo completo al cluster.

</details>

### 8. ¿Cómo restringes un ServiceAccount para que solo pueda leer pods en un namespace específico?

- A) ClusterRole + ClusterRoleBinding
- B) Role + ClusterRoleBinding
- C) ClusterRole + RoleBinding
- D) Role + RoleBinding

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Role + RoleBinding**

**Explicación:**
Para permisos con alcance de namespace, usa un Role (define permisos dentro de un namespace) con un RoleBinding (vincula el rol a un sujeto dentro del mismo namespace).

</details>

### 9. ¿Cuál es el propósito del verbo `impersonate` en RBAC?

- A) Crear recursos falsos
- B) Permitir que un usuario actúe como otro usuario o grupo
- C) Duplicar recursos
- D) Ocultar nombres de recursos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Permitir que un usuario actúe como otro usuario o grupo**

**Explicación:**
El verbo `impersonate` permite que un usuario realice acciones como si fuera otro usuario, grupo o ServiceAccount. Esto es útil para fines de depuración y administración.

</details>

### 10. ¿Qué archivo contiene el token de ServiceAccount en un volumen montado?

- A) ca.crt
- B) namespace
- C) token
- D) serviceaccount.json

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) token**

**Explicación:**
El montaje de volumen de ServiceAccount contiene tres archivos: `ca.crt` (certificado de CA), `namespace` (namespace actual) y `token` (token JWT para autenticación).

</details>

## Preguntas de respuesta corta

### 1. ¿Cuál es la principal diferencia entre cuentas de usuario y cuentas de servicio en Kubernetes?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: Las cuentas de usuario se administran externamente y no las administra directamente Kubernetes, mientras que las cuentas de servicio son recursos con alcance de namespace administrados mediante la API de Kubernetes.**

</details>

### 2. ¿Cómo deshabilitas el montaje automático de tokens de ServiceAccount?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: Establece `automountServiceAccountToken: false` en la especificación del ServiceAccount o del Pod.**

</details>

### 3. ¿Cuál es la diferencia entre `rules` y `aggregationRule` en un ClusterRole?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: `rules` define permisos directamente, mientras que `aggregationRule` combina automáticamente permisos de otros ClusterRoles que coinciden con etiquetas específicas.**

**Explicación:**
Los ClusterRoles agregados son útiles para extender roles integrados sin modificarlos directamente.

</details>

### 4. ¿Qué es la TokenRequest API y por qué se prefiere frente a los tokens estáticos?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: La TokenRequest API crea tokens con límite de tiempo y vinculados a una audiencia que son más seguros que los tokens estáticos de larga duración.**

**Explicación:**
Los tokens de la TokenRequest API expiran automáticamente y están vinculados a audiencias específicas, lo que reduce el riesgo de robo y uso indebido de tokens.

</details>

### 5. ¿Cómo determina Kubernetes qué método de autenticación usar cuando hay varios configurados?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: Kubernetes prueba cada método de autenticación en secuencia hasta que uno tiene éxito. Se usa la primera autenticación exitosa.**

**Explicación:**
Los métodos de autenticación se prueban en una cadena. Si todos los métodos fallan, la solicitud se rechaza con un error 401 Unauthorized.

</details>

## Preguntas prácticas

### 1. Escribe un Role y un RoleBinding que cumplan los siguientes requisitos:

- Namespace: development
- Permisos: lectura de Pod (get, list, watch), acceso completo a ConfigMap
- Usuario: developer@example.com

<details>
<summary>Mostrar respuesta</summary>

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: development
  name: developer-role
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list", "watch"]
- apiGroups: [""]
  resources: ["configmaps"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: developer-binding
  namespace: development
subjects:
- kind: User
  name: developer@example.com
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: developer-role
  apiGroup: rbac.authorization.k8s.io
```

</details>

### 2. Crea un ServiceAccount con un tiempo de expiración de token personalizado.

<details>
<summary>Mostrar respuesta</summary>

```yaml
# ServiceAccount definition
apiVersion: v1
kind: ServiceAccount
metadata:
  name: custom-sa
  namespace: default
---
# Pod using projected token with custom expiration
apiVersion: v1
kind: Pod
metadata:
  name: app-with-custom-token
spec:
  serviceAccountName: custom-sa
  containers:
  - name: app
    image: nginx
    volumeMounts:
    - name: token
      mountPath: /var/run/secrets/tokens
  volumes:
  - name: token
    projected:
      sources:
      - serviceAccountToken:
          path: token
          expirationSeconds: 3600  # 1 hour
          audience: api
```

**Explicación:**
Al usar volúmenes proyectados con `serviceAccountToken`, puedes especificar `expirationSeconds` personalizado (mínimo 600 segundos) y `audience` para el token.

</details>

### 3. Escribe un comando para comprobar qué permisos tiene un usuario específico.

<details>
<summary>Mostrar respuesta</summary>

```bash
# Check if a user can perform a specific action
kubectl auth can-i create deployments --as=developer@example.com -n development

# List all permissions for a user in a namespace
kubectl auth can-i --list --as=developer@example.com -n development

# Check permissions for a ServiceAccount
kubectl auth can-i --list --as=system:serviceaccount:default:my-sa

# Impersonate a group
kubectl auth can-i create pods --as=developer@example.com --as-group=developers -n development
```

**Explicación:**
El comando `kubectl auth can-i` permite comprobar permisos para el usuario actual o suplantar a otros usuarios/grupos para verificar sus niveles de acceso.

</details>

## Preguntas avanzadas

### 1. Diseña una estrategia de seguridad para el aislamiento de tenants en un cluster de Kubernetes multi-tenant.

<details>
<summary>Mostrar respuesta</summary>

**Diseño de Namespace y RBAC:**
- Crea namespaces separados por tenant
- Aplica Pod Security Standards
- Implementa NetworkPolicy para aislamiento de red
- Establece ResourceQuota para límites de recursos

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: tenant-alpha
  labels:
    tenant: alpha
    pod-security.kubernetes.io/enforce: restricted
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: tenant-alpha
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: tenant-quota
  namespace: tenant-alpha
spec:
  hard:
    requests.cpu: "10"
    requests.memory: 20Gi
    limits.cpu: "20"
    limits.memory: 40Gi
    pods: "50"
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: tenant-admin
  namespace: tenant-alpha
rules:
- apiGroups: ["", "apps", "batch"]
  resources: ["*"]
  verbs: ["*"]
- apiGroups: ["networking.k8s.io"]
  resources: ["networkpolicies"]
  verbs: ["get", "list"]  # Read-only for network policies
```

**Medidas de seguridad adicionales:**
- Usa ServiceAccounts separados por aplicación
- Implementa registro de auditoría
- Usa admission webhooks para aplicar políticas
- Considera usar Hierarchical Namespaces para la administración de sub-tenants

</details>

### 2. Explica el flujo completo de autenticación y autorización cuando se ejecuta un comando kubectl.

<details>
<summary>Mostrar respuesta</summary>

**Flujo completo:**

1. **Autenticación del cliente (kubeconfig)**
   - kubectl lee `~/.kube/config`
   - Extrae credenciales (certificado, token o plugin exec)
   - Para EKS: `aws eks get-token` genera un token temporal

2. **Autenticación del API Server**
   - El API Server recibe la solicitud con credenciales
   - Prueba los métodos de autenticación en orden:
     - Certificados de cliente X.509
     - Tokens Bearer (ServiceAccount, OIDC)
     - Proxy de autenticación
     - Autenticación de token mediante webhook
   - El primer método exitoso determina la identidad

3. **Autorización**
   - El API Server comprueba la autorización (normalmente RBAC)
   - Evalúa todos los Roles/ClusterRoles aplicables
   - Decisión: Allow o Deny
   - Si hay varios autorizadores: gana el primero que no deniegue

4. **Admission Control**
   - **Mutating Admission**: modifica la solicitud
     - Agrega valores predeterminados, inyecta sidecars
   - **Validating Admission**: valida la solicitud
     - Aplica políticas, cuotas
   - Ambos pueden rechazar la solicitud

5. **Persistencia**
   - Si todas las comprobaciones pasan, el recurso se almacena en etcd
   - Se devuelve la respuesta al cliente

```
kubectl -> kubeconfig -> API Server
                            |
                     Authentication
                            |
                     Authorization (RBAC)
                            |
                   Mutating Admission
                            |
                  Validating Admission
                            |
                         etcd
```

**Puntos clave:**
- La autenticación determina QUIÉN eres
- La autorización determina QUÉ puedes hacer
- Los admission controls determinan CÓMO se modifican/validan los recursos

</details>
