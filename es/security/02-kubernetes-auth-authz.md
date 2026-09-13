# Sistema de autenticación y autorización de Kubernetes

> **Alcance**: APIs estables de Kubernetes y gestión de acceso de usuarios en Amazon EKS
> **Última actualización**: September 13, 2026

## Descripción general

La autenticación establece la identidad de la solicitud, la autorización decide qué operaciones de la API puede realizar esa identidad y la admisión aplica políticas adicionales a los cambios autorizados. Los manifiestos siguientes son ejemplos de aprendizaje independientes; prepare primero los namespaces (espacios de nombres), los permisos de administrador, los certificados y los servidores de webhook. No se probaron llamadas reales al clúster/API ni cambios de acceso en EKS.

Los ejemplos de flags de `kube-apiserver` se aplican a un **plano de control autogestionado**. Para EKS, utilice la configuración de acceso gestionado; estos ejemplos no son instrucciones para configurar los flags de su servidor de API ni para obtener la clave privada de su CA.

## Autenticación

La autenticación es el proceso de verificar que un usuario o servicio es quien afirma ser. Kubernetes admite varios métodos de autenticación, y estos pueden habilitarse simultáneamente.

Con varios autenticadores, se utiliza el primer resultado satisfactorio, pero su orden de evaluación no está garantizado. Las credenciales no válidas pueden hacer que falle la autenticación. El tratamiento de las solicitudes sin credenciales depende de la configuración de autenticación anónima, y una identidad anónima aún necesita autorización.

### Estrategias de autenticación

#### 1. Certificados X.509

Utilice un certificado firmado por una **CA de cliente** en la que se confíe a través del `--client-ca-file` del servidor de API. El CN del sujeto proporciona el nombre de usuario y el O proporciona los grupos; el certificado necesita el uso de autenticación de cliente (`clientAuth`). La CA utilizada para verificar el certificado TLS del servidor cumple un propósito diferente al de la CA que autentica a los clientes.

**Ejemplo de clave privada y CSR local:**

```bash
umask 077
auth_lab_dir=$(mktemp -d)
openssl genrsa -out "$auth_lab_dir/john.key" 2048
openssl req -new -key "$auth_lab_dir/john.key" \
  -out "$auth_lab_dir/john.csr" -subj '/CN=john/O=engineering'
openssl req -in "$auth_lab_dir/john.csr" -noout -verify
```

Estos comandos no emiten un certificado. Envíe **solo la CSR** a un emisor aprobado, que debe revisar la identidad, los grupos, el uso y la vigencia. No copie la clave privada de la CA a los usuarios ni apruebe nombres de organización sin revisión. El firmante `beta.eks.amazonaws.com/app-serving` de EKS es para certificados de servicio y no admite la firma de certificados de cliente de usuario. Utilice las rutas de IAM/OIDC que se describen a continuación para el acceso de usuarios en EKS.

**kubeconfig después de la emisión:**

```yaml
apiVersion: v1
kind: Config
clusters:
- name: my-cluster
  cluster:
    certificate-authority: /secure/path/server-ca.crt
    server: https://kubernetes.example.com
users:
- name: john
  user:
    client-certificate: /secure/path/john.crt
    client-key: /secure/path/john.key
contexts:
- name: john@my-cluster
  context:
    cluster: my-cluster
    user: john
    namespace: default
current-context: john@my-cluster
```

Sustituya las rutas por los archivos emitidos y restrinja el acceso a la clave privada y al kubeconfig. Base64 en los campos `*-data` no es cifrado. Inspeccione los archivos kubeconfig no confiables antes de usarlos: pueden ejecutar comandos a través de plugins de credenciales.

#### 2. Tokens de ServiceAccount

Un ServiceAccount es una identidad de carga de trabajo con ámbito de namespace. Cada namespace tiene una cuenta `default`; el `serviceAccountName` de un Pod hace referencia a una cuenta de ese mismo namespace. Seleccionar una cuenta no otorga por sí mismo acceso a los recursos de la aplicación.

Este ejemplo no llama a la API y deshabilita el montaje automático de tokens. Su imagen de ejemplo no proporciona un servicio de red.

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-service-account
  namespace: default
automountServiceAccountToken: false
---
apiVersion: v1
kind: Pod
metadata:
  name: my-pod
  namespace: default
spec:
  serviceAccountName: my-service-account
  automountServiceAccountToken: false
  containers:
  - name: my-container
    image: registry.k8s.io/pause:3.10
```

`automountServiceAccountToken` es un campo de nivel superior del ServiceAccount y un campo del `spec` del Pod. La configuración del Pod tiene prioridad. Controla el montaje predeterminado; no impide un volumen proyectado `serviceAccountToken` declarado explícitamente.

Para los Pods que necesitan acceso a la API, kubelet obtiene y rota los tokens proyectados predeterminados mediante TokenRequest. El archivo de token predeterminado es `/var/run/secrets/kubernetes.io/serviceaccount/token`. Las aplicaciones deben volver a cargar el archivo rotado. La expiración y la vinculación de audiencia reducen la exposición, pero no hacen que sea seguro divulgar un token de portador (bearer token). No dé por supuesto que crear una cuenta crea automáticamente un token de Secret de larga duración. El [ejemplo de volumen proyectado del cuestionario](../quizzes/security/02-kubernetes-auth-authz-quiz.md) cubre una audiencia personalizada y una vigencia solicitada.

#### 3. OpenID Connect (OIDC)

OIDC permite al servidor de API validar **tokens de ID** de un proveedor de identidad externo. Configure el emisor, la audiencia, la validación de firma/expiración y el mapeo de identidades. El servidor de API no proporciona un inicio de sesión interactivo ni emite tokens de actualización. Los clientes utilizan una herramienta revisada o un plugin de credenciales `exec` para su proveedor de identidad.

Estos son **flags adicionales para un servidor de API autogestionado**, no un comando de arranque completo ni un kubeconfig. Sustituya el emisor HTTPS y el ID de cliente de ejemplo.

```text
--oidc-issuer-url=https://idp.example.com
--oidc-client-id=kubernetes
--oidc-username-claim=sub
--oidc-username-prefix=oidc:
--oidc-groups-claim=groups
--oidc-groups-prefix=oidc:
```

Añada prefijos a los nombres de usuario y grupos para evitar colisiones con identidades existentes, como los grupos `system:`. La `AuthenticationConfiguration` estructurada es una alternativa; no combine `--authentication-config` con los flags `--oidc-*`. Configure un proveedor OIDC externo para EKS mediante el procedimiento gestionado independiente que se describe más abajo.

#### 4. Autenticación de tokens mediante webhook

Un servidor de API autogestionado envía un **TokenReview** de `authentication.k8s.io/v1` a un servicio externo. Lo siguiente es un **kubeconfig independiente que el servidor de API utiliza para acceder a ese servicio**. No es un campo `authentication.webhook` en el kubeconfig de un usuario.

```yaml
apiVersion: v1
kind: Config
clusters:
- name: authentication-service
  cluster:
    server: https://authn.example.com/authenticate
    certificate-authority: /etc/kubernetes/authn-webhook/ca.crt
users:
- name: kube-apiserver-webhook-client
  user:
    client-certificate: /etc/kubernetes/authn-webhook/client.crt
    client-key: /etc/kubernetes/authn-webhook/client.key
contexts:
- name: webhook
  context:
    cluster: authentication-service
    user: kube-apiserver-webhook-client
current-context: webhook
```

Si se instala en `/etc/kubernetes/authn-webhook.kubeconfig`, configure `--authentication-token-webhook-config-file=/etc/kubernetes/authn-webhook.kubeconfig` y `--authentication-token-webhook-version=v1` en el servidor de API. Aprovisione por separado los certificados y el servicio referenciados. El servicio debe validar el token y la audiencia prevista, y devolver una respuesta TokenReview. Diseñe el TLS mutuo, la protección de credenciales, el TTL de caché y el comportamiento ante fallos. Este ejemplo no proporciona ni una implementación de webhook ni una validación de disponibilidad.

#### 5. Proxy de autenticación

Un proxy de autenticación verifica al llamante y reenvía el nombre de usuario y los grupos resultantes. Limitarse a nombrar cabeceras confiables no establece confianza. Autentique primero la identidad TLS del proxy utilizando una CA de front-proxy dedicada y un CN de certificado de cliente permitido.

**Extracto de flags de un servidor de API autogestionado:**

```text
--requestheader-client-ca-file=/etc/kubernetes/front-proxy-ca.crt
--requestheader-allowed-names=front-proxy-client
--requestheader-username-headers=X-Remote-User
--requestheader-group-headers=X-Remote-Group
```

El proxy debe eliminar las cabeceras de identidad suministradas por el llamante y sustituirlas por valores verificados. No reutilice la CA ordinaria de clientes de usuario como CA del proxy ni deje vacíos los CN permitidos, lo que haría confiar en todos los certificados de cliente. Este extracto no implementa el proxy en sí.

### Usuarios y grupos

En Kubernetes, los usuarios se clasifican de la siguiente manera:

1. **Usuarios normales**: Se gestionan fuera del clúster; Kubernetes no los gestiona directamente.
2. **Service Accounts**: Cuentas gestionadas por la API de Kubernetes.

Los usuarios pueden pertenecer a uno o más grupos, y los grupos se utilizan en las políticas de autorización.

## Autorización

La autorización es el proceso de verificar si un usuario autenticado tiene permiso para realizar la acción solicitada. Kubernetes admite varios módulos de autorización.

### Modos de autorización

#### 1. RBAC (control de acceso basado en roles)

RBAC proporciona control de acceso basado en roles y es actualmente el mecanismo de autorización más utilizado en Kubernetes.

**Conceptos clave:**

1. **Role**: Define permisos dentro de un namespace.
2. **ClusterRole**: Una definición con ámbito de clúster para recursos del clúster, URLs no relacionadas con recursos o permisos reutilizables sobre recursos con ámbito de namespace.
3. **RoleBinding**: Hace referencia a un Role del mismo namespace o a un ClusterRole y otorga permisos **solo en el namespace del binding**. Un sujeto ServiceAccount puede pertenecer explícitamente a otro namespace.
4. **ClusterRoleBinding**: Otorga los permisos de un ClusterRole en todo el clúster; no puede hacer referencia a un Role.

Una definición de rol no otorga nada sin un binding. RBAC añade permisos permitidos y no tiene reglas de denegación explícitas. Los permisos `get/list/watch` sobre Secret permiten leer datos secretos, por lo que estos ejemplos utilizan lecturas de Pod en su lugar.

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
  name: pod-reader-reusable
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "watch", "list"]
```

**Ejemplo de ClusterRoleBinding:**

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: read-pods-global
subjects:
- kind: Group
  name: cluster-inventory-readers
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: ClusterRole
  name: pod-reader-reusable
  apiGroup: rbac.authorization.k8s.io
```

El ClusterRoleBinding ilustra un grupo de operaciones que necesita explícitamente **información de Pods en todos los namespaces**; no es una recomendación predeterminada. Para un solo namespace, utilice en su lugar un RoleBinding en ese namespace con `roleRef.kind: ClusterRole` y `roleRef.name: pod-reader-reusable`.

#### 2. ABAC (control de acceso basado en atributos)

ABAC proporciona control de acceso basado en atributos. Las políticas se definen en archivos JSON.

**Ejemplo de política:**

```json
{
  "apiVersion": "abac.authorization.kubernetes.io/v1beta1",
  "kind": "Policy",
  "spec": {
    "user": "john",
    "namespace": "default",
    "apiGroup": "",
    "resource": "pods",
    "readonly": true
  }
}
```

ABAC se incluye para comprender los clústeres autogestionados existentes. La política que consume `--authorization-policy-file` es un archivo con **un objeto JSON por línea**, no un recurso de la API de Kubernetes. La indentación anterior es explicativa; serialice cada política en una sola línea en el archivo real. Los cambios requieren reiniciar el servidor de API. Prefiera RBAC para configuraciones nuevas; este flag no es un mecanismo de configuración de EKS.

#### 3. Autorización de nodos

La autorización de nodos es específica de los kubelets. Su identidad debe pertenecer a `system:nodes` y usar el nombre de usuario `system:node:<nodeName>` coincidente con el nombre real del nodo. No es un mecanismo de acceso para cargas de trabajo. En clústeres autogestionados, combínela con la admisión NodeRestriction para limitar los cambios de kubelet a los objetos Node y Pod.

#### 4. Autorización mediante webhook

Un servidor de API autogestionado envía un **SubjectAccessReview** de `authorization.k8s.io/v1` a un servicio externo. Utilice el mismo formato de archivo de conexión que el webhook de autenticación anterior, con un endpoint de autorización, una CA y un certificado de cliente independientes. Configure `--authorization-webhook-config-file` y `--authorization-webhook-version=v1`, o utilice la `AuthorizationConfiguration` estructurada para configurar la cadena y la política ante fallos. No existe un campo `authorization.webhook` en el kubeconfig de un usuario.

Los autorizadores se ejecutan en el orden configurado; el primer **Allow o Deny** decide. `NoOpinion` continúa con el siguiente autorizador; si todos los resultados son NoOpinion, se deniega el acceso. Un webhook posterior no puede vetar una solicitud que RBAC ya ha permitido. `system:masters` es un grupo especial que omite RBAC y la autorización por webhook; no lo asigne a administradores ordinarios ni suponga que eliminar un role binding revoca su acceso.

### Buenas prácticas de autorización

1. **Principio de mínimo privilegio**: Otorgue solo los permisos mínimos necesarios.
2. **Separación de roles**: Otorgue los permisos adecuados según roles como administradores, desarrolladores y operadores.
3. **Separación de namespaces**: Separe los namespaces por equipo o proyecto y otorgue los permisos adecuados.
4. **Separación de Service Accounts**: Utilice service accounts separadas para cada aplicación.
5. **Auditoría periódica**: Revise y actualice periódicamente las políticas de autorización.

## Control de admisión

El control de admisión realiza validaciones y modificaciones adicionales antes de procesar las solicitudes, después de la autenticación y la autorización.

La admisión gestiona la creación, los cambios, la eliminación y algunas solicitudes de conexión; **las lecturas get/list/watch omiten la admisión**. La mutación precede a la validación, y cualquiera de las dos fases puede rechazar una solicitud.

### Tipos de controladores de admisión

1. **Controladores de admisión mutantes**: Pueden modificar las solicitudes.
2. **Controladores de admisión de validación**: Solo validan las solicitudes, sin modificarlas.

### Controladores de admisión clave

1. **LimitRanger**: Aplica los valores predeterminados y las restricciones mínimas/máximas definidas por LimitRange.
2. **ResourceQuota**: Comprueba las cuotas configuradas del namespace para el número de objetos, las solicitudes de recursos y cantidades similares; no es un límite sobre el consumo medido de CPU/memoria ni sobre el gasto.
3. **PodSecurity**: Aplica los Pod Security Standards según las etiquetas del namespace. La antigua PodSecurityPolicy se eliminó en Kubernetes 1.25.
4. **ServiceAccount**: Asigna automáticamente service accounts a los pods.
5. **DefaultStorageClass**: Selecciona una StorageClass predeterminada para un PVC sin clase especificada; no crea la StorageClass.

### Control de admisión dinámico

El control de admisión dinámico se implementa mediante webhooks:

1. **MutatingAdmissionWebhook**: Puede modificar las solicitudes.
2. **ValidatingAdmissionWebhook**: Solo valida las solicitudes, sin modificarlas.

**Ejemplo de configuración de webhook:**

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
  namespaceSelector:
    matchLabels:
      training.example.com/pod-policy: "enabled"
  failurePolicy: Fail
  matchPolicy: Equivalent
  admissionReviewVersions: ["v1"]
  sideEffects: None
  timeoutSeconds: 5
```

Este webhook solo se aplica a los namespaces etiquetados explícitamente. No lo instale sin el servicio HTTPS real, la CA y una implementación de AdmissionReview que preserve el UID de la solicitud. `failurePolicy: Fail` bloquea las solicitudes coincidentes ante errores o tiempos de espera en la llamada. `Ignore` ignora los fallos de llamada; no convierte en permiso una denegación devuelta correctamente. Pruebe la disponibilidad y la recuperación en un namespace dedicado. La ValidatingAdmissionPolicy con CEL es otra opción para la validación.

## Ejemplos de implementación práctica

### Configuración de autenticación y autorización en EKS

#### Integración de IAM y RBAC

Utilice **access entries** (entradas de acceso) para el acceso actual de usuarios IAM en EKS. Un rol de IAM proporciona la identidad autenticada; las políticas de acceso de EKS asociadas o el RBAC de Kubernetes otorgan los permisos de Kubernetes. Los permisos permitidos de ambas vías se acumulan. Una política de acceso de EKS no es una política de IAM.

Lo siguiente es un ejemplo de cambio por parte de un administrador para un clúster y un rol de IAM existentes. Confirme primero la cuenta, la Región, el clúster, el modo `API` o `API_AND_CONFIG_MAP`, la existencia del namespace `development`, la ausencia de una entrada de acceso duplicada y los permisos para `eks:CreateAccessEntry` y los cambios de RBAC. Esto no es un script de creación de infraestructura ni un procedimiento de migración completo.

```bash
# Example inputs: replace with the approved cluster and existing IAM role.
region=ap-northeast-2
cluster_name=my-cluster
principal_arn=arn:aws:iam::123456789012:role/EKSDeveloperRole
aws eks describe-cluster --region "$region" --name "$cluster_name" \
  --query 'cluster.accessConfig.authenticationMode' --output text

# Mutates access configuration; run only after the prerequisites above.
aws eks create-access-entry --region "$region" --cluster-name "$cluster_name" \
  --principal-arn "$principal_arn" --type STANDARD \
  --kubernetes-groups eks:developers
```

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: developer-pod-reader
  namespace: development
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: eks-developer-pod-reader
  namespace: development
subjects:
- kind: Group
  name: eks:developers
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: developer-pod-reader
  apiGroup: rbac.authorization.k8s.io
```

Después de aplicar los objetos de RBAC, verifique el acceso con las credenciales reales del rol. Este ejemplo no asocia ninguna política de acceso, y crear una entrada de acceso no crea objetos de RBAC. Los bindings o las políticas existentes pueden hacer que los permisos efectivos sean más amplios que estas lecturas de Pod. Tenga en cuenta el retardo de propagación.

El ConfigMap `aws-auth` es el mecanismo heredado. Reemplazar el ConfigMap completo puede eliminar los mapeos de nodos/Fargate. Planifique la migración de `CONFIG_MAP` a `API_AND_CONFIG_MAP`, migre y verifique los mapeos, y después use `API`. Una vez habilitado, el acceso por API no puede eliminarse revirtiendo los modos; `API` no puede volver a un modo de ConfigMap. Mientras se usen ambos, una entrada de acceso tiene prioridad para el mismo principal de IAM. No todos los mapeos existentes se migran automáticamente.

`kubectl auth can-i --list` no muestra los permisos procedentes de las políticas de acceso de EKS. La suplantación con `--as`/`--as-group` fuerza la evaluación de RBAC de Kubernetes y, por lo tanto, no prueba los permisos de la política de acceso del rol de IAM. Verifique acciones individuales con el rol real, incluidas las denegaciones esperadas fuera del namespace y para las lecturas de Secret.

#### Configuración del proveedor OIDC

Estas tres vías tienen direcciones y propósitos diferentes.

| Vía | Objetivo de autenticación y configuración |
|---|---|
| Usuario OIDC externo → API de Kubernetes | Asocie el IdP externo mediante `AssociateIdentityProviderConfig` de EKS y, a continuación, vincule sus usuarios/grupos a RBAC. EKS debe poder alcanzar el emisor a través de HTTPS público; los certificados de emisor autofirmados no son compatibles. Esto no deshabilita la autenticación de IAM. |
| Pod → API de AWS mediante IRSA | Establezca la confianza de IAM en el emisor OIDC de ServiceAccount del clúster, restrinja la confianza del rol al namespace/ServiceAccount previsto y otorgue solo los recursos de AWS necesarios. `eksctl utils associate-iam-oidc-provider` sirve para esta vía, no para el inicio de sesión de usuarios externos. |
| Pod → API de AWS mediante EKS Pod Identity | Utilice el Pod Identity Agent y una asociación de rol en los entornos de ejecución compatibles. Esto es distinto de la configuración del proveedor OIDC de IAM de IRSA. |

Ninguno de los dos mecanismos de carga de trabajo otorga por sí mismo RBAC en la API de Kubernetes. Evite usar como ejemplo predeterminado una política gestionada de lectura de S3 a nivel de toda la cuenta; limite los permisos a los ARN reales del bucket/objeto. Consulte [EKS external OIDC](https://docs.aws.amazon.com/eks/latest/userguide/authenticate-oidc-identity-provider.html) y [workload IAM roles](https://docs.aws.amazon.com/eks/latest/userguide/service-accounts.html) para los detalles de configuración.

### Seguridad de clústeres multiinquilino

En entornos multiinquilino, el aislamiento entre inquilinos es importante.

**Aislamiento de namespaces:**

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
  policyTypes: [Ingress]
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          tenant: a
```

Esta política permite el tráfico de entrada desde **todos** los namespaces etiquetados con `tenant: a`. Otras políticas de entrada pueden añadir permisos, y la salida no está restringida. Requiere que el CNI aplique NetworkPolicy; solo administradores de confianza deberían controlar las etiquetas y las políticas de los namespaces. Un namespace por sí solo no garantiza un aislamiento fuerte entre inquilinos hostiles. El cuestionario incluye la denegación predeterminada en ambas direcciones; revise los permisos separados para DNS y el tráfico necesario.

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

## Buenas prácticas de seguridad

1. **Rotación periódica de certificados**: Renueve los certificados con regularidad.
2. **Deshabilitar el automontaje de tokens de Service Account**: Deshabilite el montaje automático de tokens de service account cuando no sea necesario.
3. **Minimizar las políticas de RBAC**: Otorgue solo los permisos mínimos necesarios.
4. **Implementar Network Policies**: Restrinja la comunicación entre pods.
5. **Habilitar el registro de auditoría**: Verifique la cobertura de la política de auditoría, las exclusiones de datos sensibles, la retención y el acceso a los registros. En EKS, habilite el tipo de registro del plano de control `audit` y verifique la entrega a CloudWatch; no suponga que se registra el cuerpo de cada solicitud.
6. **Configurar contextos de seguridad**: Configure correctamente los security contexts de los pods y contenedores.
7. **Escaneo de imágenes**: Escanee periódicamente las imágenes de contenedor en busca de vulnerabilidades.

## Conclusión

El sistema de autenticación y autorización de Kubernetes es un elemento central de la seguridad del clúster. Al seleccionar los métodos de autenticación adecuados, implementar un control de acceso granular mediante RBAC y aplicar políticas de seguridad adicionales con controladores de admisión, puede construir un entorno de Kubernetes seguro.

La autenticación, la autorización y el control de admisión se complementan entre sí, y es importante utilizarlos conjuntamente para implementar una estrategia de defensa en profundidad (Defense in Depth).

## Referencias oficiales

- [Kubernetes authentication](https://kubernetes.io/docs/reference/access-authn-authz/authentication/)
- [Kubernetes authorization](https://kubernetes.io/docs/reference/access-authn-authz/authorization/)
- [RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
- [ServiceAccount configuration](https://kubernetes.io/docs/tasks/configure-pod-container/configure-service-account/)
- [ABAC](https://kubernetes.io/docs/reference/access-authn-authz/abac/)
- [Node authorization](https://kubernetes.io/docs/reference/access-authn-authz/node/)
- [Admission controllers](https://kubernetes.io/docs/reference/access-authn-authz/admission-controllers/)
- [Admission webhooks](https://kubernetes.io/docs/reference/access-authn-authz/extensible-admission-controllers/)
- [NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [EKS certificate signing](https://docs.aws.amazon.com/eks/latest/userguide/cert-signing.html)
- [EKS access entries](https://docs.aws.amazon.com/eks/latest/userguide/creating-access-entries.html)
- [EKS authentication modes](https://docs.aws.amazon.com/eks/latest/userguide/setting-up-access-entries.html)
- [EKS access policy evaluation](https://docs.aws.amazon.com/eks/latest/userguide/access-policies.html)
- [EKS audit logs](https://docs.aws.amazon.com/eks/latest/userguide/control-plane-logs.html)
- [Trusted kubeconfig](https://kubernetes.io/docs/concepts/configuration/organize-cluster-access-kubeconfig/)
