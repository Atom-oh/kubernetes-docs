# Cuestionario de autenticación y autorización de Kubernetes

> **Documento relacionado**: [Kubernetes Authentication and Authorization System](../../security/02-kubernetes-auth-authz.md)

> **Última actualización**: September 13, 2026

## Preguntas de opción múltiple

### 1. En la autenticación mediante certificados X.509 de Kubernetes, ¿de qué campo se extrae el nombre de usuario?

- A) Subject Alternative Name (SAN)
- B) Common Name (CN)
- C) Organization Unit (OU)
- D) Issuer

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Common Name (CN)**

**Explicación:**
En los certificados X.509, el Common Name (CN) se asigna al nombre de usuario y la Organization (O) se asigna a los grupos.

</details>

### 2. ¿Cuál es la diferencia principal entre ClusterRole y Role en RBAC?

- A) ClusterRole es de solo lectura, Role es de lectura/escritura
- B) ClusterRole es una definición con ámbito de clúster; Role es una definición con ámbito de namespace
- C) ClusterRole es solo para administradores, Role es para usuarios regulares
- D) ClusterRole se aplica solo a nodos, Role se aplica solo a pods

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) ClusterRole es una definición con ámbito de clúster; Role es una definición con ámbito de namespace**

**Explicación:**
Un ClusterRole también puede definir permisos reutilizables para recursos con ámbito de namespace. Un RoleBinding que lo referencia limita la concesión al namespace de la asociación; un ClusterRoleBinding concede sus permisos en todo el clúster. Una definición por sí sola no concede nada.

</details>

### 3. ¿Cuál es la ruta predeterminada en la que los tokens de ServiceAccount se montan automáticamente en los pods?

- A) /var/run/secrets/kubernetes.io/token
- B) /etc/kubernetes/serviceaccount
- C) /var/run/secrets/kubernetes.io/serviceaccount
- D) /opt/kubernetes/secrets

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) /var/run/secrets/kubernetes.io/serviceaccount**

**Explicación:**
Este es el directorio predeterminado en un Pod de Linux con el montaje automático habilitado. El token es el archivo `token` que se encuentra dentro. Los Pods con `automountServiceAccountToken: false` o volúmenes proyectados personalizados pueden tener rutas distintas o no tener token.

</details>

### 4. ¿Cuál es el orden de ejecución de MutatingAdmissionWebhook y ValidatingAdmissionWebhook?

- A) Primero Validating, después Mutating
- B) Primero Mutating, después Validating
- C) Se ejecutan simultáneamente en paralelo
- D) Se ejecutan aleatoriamente sin orden

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Primero Mutating, después Validating**

**Explicación:**
Orden de ejecución del controlador de admisión: 1) MutatingAdmissionWebhook (modifica las solicitudes), 2) ValidatingAdmissionWebhook (valida las solicitudes).

</details>

<span id="_5-what-configmap-maps-iam-users-roles-to-kubernetes-rbac-in-eks"></span>

### 5. ¿Qué ConfigMap almacena las asignaciones de IAM en el modo de autenticación heredado CONFIG_MAP de EKS?

- A) kube-config
- B) aws-auth
- C) eks-iam-mapping
- D) cluster-auth

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) aws-auth**

**Explicación:**
`kube-system/aws-auth` es la asignación heredada de IAM. Para la gestión de acceso actual, use entradas de acceso de EKS con RBAC adecuado o políticas de acceso de EKS. Durante la migración en modo dual, una entrada de acceso tiene prioridad para el mismo principal. Reemplazar todo el ConfigMap puede eliminar las asignaciones de nodos.

</details>

<span id="_6-which-authentication-method-is-recommended-for-production-kubernetes-clusters"></span>

### 6. ¿Qué método integra el inicio de sesión de usuarios mediante tokens de ID emitidos por un proveedor de identidad externo?

- A) Archivo de token estático
- B) Autenticación básica
- C) OIDC (OpenID Connect)
- D) Autenticación anónima

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) OIDC (OpenID Connect)**

**Explicación:**
OIDC valida el emisor, la audiencia, la firma y la expiración de los tokens de ID emitidos externamente. El IdP/cliente gestiona el inicio de sesión y la renovación; el servidor de API no emite tokens de renovación. La autenticación de IAM de EKS es otra vía de acceso de usuarios, mientras que IRSA/Pod Identity tienen un propósito distinto: el acceso de Pod a las API de AWS.

</details>

### 7. ¿Cuál es el propósito del grupo `system:masters` en Kubernetes?

- A) Administrar nodos master
- B) Proporcionar acceso ilimitado a la API que omite la autorización de RBAC/webhook
- C) Programar pods en nodos master
- D) Administrar namespaces del sistema

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Proporcionar acceso ilimitado a la API que omite la autorización de RBAC/webhook**

**Explicación:**
`system:masters` es un grupo especial que omite la autorización. No equivale a una asociación de rol de administrador ordinaria, y eliminar un ClusterRoleBinding no revoca esa omisión. Evite asignar este grupo a administradores ordinarios.

</details>

### 8. ¿Cómo restringe una ServiceAccount para que solo lea pods en un namespace específico?

- A) ClusterRole + ClusterRoleBinding
- B) Role + ClusterRoleBinding
- C) Solo Role
- D) Role + RoleBinding

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Role + RoleBinding**

**Explicación:**
Use un Role que permita solo get/list/watch de Pod y un RoleBinding en ese namespace, suponiendo que no existan otras concesiones. **ClusterRole + RoleBinding también es válido** y, por lo tanto, no es una opción de respuesta incorrecta. Un sujeto ServiceAccount puede pertenecer explícitamente a otro namespace; el ámbito del permiso sigue siendo el namespace de la asociación.

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
El volumen predeterminado de ServiceAccount montado automáticamente proporciona estos archivos (las proyecciones personalizadas pueden diferir): `ca.crt` (certificado de CA), `namespace` (namespace actual) y `token` (token JWT para la autenticación).

</details>

## Preguntas de respuesta corta

### 1. ¿Cuál es la diferencia principal entre las cuentas de usuario y las cuentas de servicio en Kubernetes?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: Las cuentas de usuario se gestionan externamente y no directamente por Kubernetes, mientras que las cuentas de servicio son recursos con ámbito de namespace gestionados mediante la API de Kubernetes.**

</details>

### 2. ¿Cómo deshabilita el montaje automático de tokens de ServiceAccount?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: Configure `automountServiceAccountToken: false` en el nivel superior de ServiceAccount o en la especificación del Pod. La configuración del Pod tiene prioridad; los volúmenes de token proyectado declarados explícitamente siguen funcionando.**

</details>

### 3. ¿Cuál es la diferencia entre `rules` y `aggregationRule` en un ClusterRole?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: `rules` define los permisos directamente, mientras que `aggregationRule` combina automáticamente permisos de otros ClusterRoles que coinciden con etiquetas específicas.**

**Explicación:**
El controlador de agregación gestiona las reglas del ClusterRole de destino y puede sobrescribir los cambios manuales de reglas. El permiso para agregar o editar roles seleccionados por etiquetas también afecta al acceso resultante.

</details>

### 4. ¿Qué es la API TokenRequest y por qué se prefiere frente a los tokens estáticos?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: La API TokenRequest crea tokens con duración limitada y vinculados a una audiencia que son más seguros que los tokens estáticos de larga duración.**

**Explicación:**
Verifique la expiración real devuelta por el servidor, que puede ajustar la duración solicitada. Kubelet rota los tokens proyectados de Pod, pero la aplicación debe volver a cargar el archivo. Una TokenRequest independiente no proporciona por sí misma rotación automática de archivos. Estos tokens siguen siendo credenciales secretas de portador.

</details>

### 5. ¿Cómo determina Kubernetes qué método de autenticación usar cuando hay varios configurados?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: Se usa el primer resultado de autenticación exitoso, pero no se garantiza el orden de evaluación de los autenticadores.**

**Explicación:**
No suponga un orden fijo X.509 → OIDC → proxy. Las credenciales no válidas pueden producir un 401. El manejo anónimo de solicitudes sin credenciales depende de la configuración del servidor; una identidad anónima aún puede ser denegada por la autorización.

</details>

## Preguntas prácticas

### 1. Escriba un Role y un RoleBinding que cumplan los siguientes requisitos:

- Namespace: development
- Permisos: lectura de Pod (get, list, watch), lecturas de ConfigMap y create/update/patch/delete de objetos individuales (sin deletecollection)
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

<span id="_2-create-a-serviceaccount-with-a-custom-token-expiration-time"></span>

### 2. Cree una ServiceAccount y un Pod con un token proyectado que solicite una duración personalizada.

<details>
<summary>Mostrar respuesta</summary>

```yaml
# ServiceAccount definition
apiVersion: v1
kind: ServiceAccount
metadata:
  name: custom-sa
  namespace: default
automountServiceAccountToken: false
---
# Pod using projected token with custom expiration
apiVersion: v1
kind: Pod
metadata:
  name: app-with-custom-token
  namespace: default
spec:
  serviceAccountName: custom-sa
  automountServiceAccountToken: false
  containers:
  - name: app
    image: registry.k8s.io/pause:3.10
    volumeMounts:
    - name: token
      mountPath: /var/run/secrets/tokens
      readOnly: true
  volumes:
  - name: token
    projected:
      sources:
      - serviceAccountToken:
          path: token
          expirationSeconds: 3600  # requested, not guaranteed
          audience: https://service.example.com
```

**Explicación:**
El valor mínimo solicitado de `expirationSeconds` es 600; el servidor determina la expiración real. La audiencia de ejemplo debe estar configurada y validada por el servicio receptor; no es aceptada automáticamente por la API de Kubernetes. Para las llamadas a la API de Kubernetes, use una audiencia que acepte el servidor de API. El montaje automático está deshabilitado y solo el token explícito se monta como de solo lectura. Este Pod pause ilustra el volumen; no usa el token ni sirve HTTP. Una aplicación real debe volver a cargar el archivo después de que Kubelet lo rote.

</details>

### 3. Escriba un comando para comprobar qué permisos tiene un usuario específico.

<details>
<summary>Mostrar respuesta</summary>

```bash
# Check if a user can perform a specific action
kubectl auth can-i create deployments --as=developer@example.com -n development

# Request the namespace rule list (see authorizer limitations below)
kubectl auth can-i --list --as=developer@example.com -n development

# Check permissions for a ServiceAccount
kubectl auth can-i get pods -n development \
  --as=system:serviceaccount:default:my-sa \
  --as-group=system:serviceaccounts \
  --as-group=system:serviceaccounts:default \
  --as-group=system:authenticated

# Impersonate a group
kubectl auth can-i create pods --as=developer@example.com --as-group=developers -n development
```

**Explicación:**
La persona que llama necesita permiso `impersonate` para el usuario/ServiceAccount y cada grupo usado. No suponga que la pertenencia a grupos se reconstruye automáticamente. `--list` no siempre es un inventario completo de permisos efectivos y omite los permisos de políticas de acceso de EKS. La suplantación en EKS fuerza la evaluación de RBAC; pruebe por separado el rol de IAM real. Un resultado positivo de `can-i` no garantiza la admisión, el acceso a la red ni la aceptación de cuotas.

</details>

## Preguntas avanzadas

### 1. Diseñe una estrategia de seguridad para el aislamiento de tenants en un clúster de Kubernetes multi-tenant.

<details>
<summary>Mostrar respuesta</summary>

**Diseño de Namespace y RBAC:**

- Cree namespaces separados por tenant
- Aplique Pod Security Standards
- Implemente NetworkPolicy para el aislamiento de red
- Configure ResourceQuota para los límites de recursos

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: tenant-alpha
  labels:
    tenant: alpha
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.35
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
  name: tenant-workload-editor
  namespace: tenant-alpha
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: ["networking.k8s.io"]
  resources: ["networkpolicies"]
  verbs: ["get", "list"]  # Read-only for network policies
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: tenant-workload-editors
  namespace: tenant-alpha
subjects:
- kind: Group
  name: tenant-alpha:developers
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: tenant-workload-editor
  apiGroup: rbac.authorization.k8s.io
```

La versión de PSS fijada `v1.35` es una referencia de aprendizaje; seleccione y valide una versión de política compatible con el clúster de destino. La denegación predeterminada también bloquea DNS y dependencias externas, por lo que se deben revisar las excepciones explícitas. El CNI debe aplicar las políticas. Los tenants no deben cambiar las etiquetas de namespace, NetworkPolicy, ResourceQuota ni RBAC, y se deben revisar otras asociaciones existentes.

**La creación/edición de Deployment puede permitir que los Pods usen otras ServiceAccounts o Secrets en el namespace.** Eliminar solo el permiso de get de Secret no cierra esta vía. Separe identidades/secrets con distintos niveles de confianza en diferentes namespaces, restrinja las identidades permitidas mediante admisión cuando sea necesario o use clústeres separados. Este ejemplo no demuestra un aislamiento sólido de tenants.

**Medidas de seguridad adicionales:**

- Use ServiceAccounts separadas por aplicación
- Implemente el registro de auditoría
- Use webhooks de admisión para la aplicación de políticas
- Defina explícitamente la propiedad de sub-tenants y la propagación de políticas; los namespaces ordinarios de Kubernetes son planos

</details>

### 2. Explique el flujo completo de autenticación y autorización cuando se ejecuta un comando kubectl.

<details>
<summary>Mostrar respuesta</summary>

1. **Cliente**: kubectl lee el kubeconfig/context seleccionado y valida el certificado TLS del servidor. El archivo predeterminado es `~/.kube/config`, pero `--kubeconfig` y `KUBECONFIG` pueden cambiarlo. Obtiene credenciales de certificados, tokens o un plugin exec; el acceso de IAM de EKS suele usar `aws eks get-token`.
2. **Autenticación**: El servidor de API verifica las credenciales para establecer la identidad de usuario/grupo. Usa el primer resultado de autenticación exitoso sin garantizar un orden de evaluación fijo. OIDC, los proxies y los webhooks tienen requisitos de verificación y confianza diferentes.
3. **Autorización**: Los autorizadores configurados se ejecutan en orden hasta el primer Allow o Deny. NoOpinion continúa; todos los resultados NoOpinion provocan una denegación 403. RBAC agrega permisos de las asociaciones aplicables y no tiene una regla de denegación explícita. La omisión de `system:masters` es un riesgo independiente.
4. **Manejo de solicitudes**: Las solicitudes ordinarias de recursos CREATE/UPDATE pasan primero por la admisión de mutación y luego por la de validación; ambas pueden rechazar. Los cambios exitosos se almacenan después de la validación del objeto, las comprobaciones de conflictos y otras comprobaciones pertinentes. `get/list/watch` omite la admisión. Las API de ejecución en seco, DELETE, CONNECT y agregadas no se pueden representar todas mediante la misma secuencia de escritura en etcd.
5. **Respuesta**: El servidor de API devuelve un resultado o error. El éxito de la API no significa que un controlador haya terminado de procesar ni que una aplicación esté lista.

| Solicitud de ejemplo | Diferencia después de la autenticación/autorización |
|---|---|
| `kubectl get pods` | Devuelve resultados de lectura; no ejecuta admisión ni almacena un Pod nuevo |
| CREATE de Pod | Pasa por la admisión de mutación/validación y las comprobaciones de objetos antes del almacenamiento; la programación se realiza después |
| CREATE de ejecución en seco del servidor | Realiza la validación del servidor, incluida la admisión, sin almacenamiento persistente |

La autenticación establece la identidad, la autorización permite operaciones de API y la admisión aplica políticas adicionales a los cambios.

</details>

## Referencias oficiales

- [Authentication](https://kubernetes.io/docs/reference/access-authn-authz/authentication/)
- [Authorization](https://kubernetes.io/docs/reference/access-authn-authz/authorization/)
- [RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
- [ServiceAccount](https://kubernetes.io/docs/tasks/configure-pod-container/configure-service-account/)
- [Admission](https://kubernetes.io/docs/reference/access-authn-authz/admission-controllers/)
- [EKS access policies](https://docs.aws.amazon.com/eks/latest/userguide/access-policies.html)
