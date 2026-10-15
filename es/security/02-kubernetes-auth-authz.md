# Sistema de autenticación y autorización de Kubernetes

> **Alcance**: API estables de Kubernetes y administración del acceso de usuarios de Amazon EKS
> **Última actualización**: October 12, 2026

## Descripción general

La autenticación establece la identidad de la solicitud, la autorización decide qué operaciones de la API puede realizar esa identidad, y la admisión aplica políticas adicionales a los cambios autorizados. Los manifiestos a continuación son ejemplos de aprendizaje independientes; primero prepare los namespaces, los permisos de administrador, los certificados y los servidores webhook. No se probaron llamadas a clusters/API en producción ni cambios de acceso a EKS.

Los ejemplos de indicadores de `kube-apiserver` se aplican a un **control plane autoadministrado**. Use la configuración de acceso administrada para EKS; estos ejemplos no son instrucciones para configurar sus indicadores de servidor API ni obtener su clave privada de CA.

## Autenticación

La autenticación es el proceso de verificar que un usuario o servicio es quien afirma ser. Kubernetes admite varios métodos de autenticación, que pueden habilitarse simultáneamente.

Con varios autenticadores, se utiliza el primer resultado correcto, pero no se garantiza su orden de evaluación. Las credenciales no válidas pueden hacer que la autenticación falle. El manejo de solicitudes sin credenciales depende de la configuración de autenticación anónima, y una identidad anónima aún necesita autorización.

### Estrategias de autenticación

#### 1. Certificados X.509

Use un certificado firmado por una **CA de cliente** en la que confía el servidor API mediante `--client-ca-file`. El CN del sujeto proporciona el nombre de usuario y O proporciona los grupos; el certificado necesita el uso de autenticación de cliente (`clientAuth`). La CA utilizada para verificar el certificado TLS del servidor tiene un propósito diferente al de la CA que autentica clientes.

**Ejemplo de clave privada local y CSR:**

```bash
umask 077
auth_lab_dir=$(mktemp -d)
openssl genrsa -out "$auth_lab_dir/john.key" 2048
openssl req -new -key "$auth_lab_dir/john.key" \
  -out "$auth_lab_dir/john.csr" -subj '/CN=john/O=engineering'
openssl req -in "$auth_lab_dir/john.csr" -noout -verify
```

Estos comandos no emiten un certificado. Envíe **solo el CSR** a un emisor aprobado, que debe revisar la identidad, los grupos, el uso y la vigencia. No copie la clave privada de la CA a los usuarios ni apruebe nombres de organizaciones sin revisión. El firmante `beta.eks.amazonaws.com/app-serving` de EKS es para certificados de servicio y no admite la firma de certificados de cliente de usuario. Use las rutas IAM/OIDC a continuación para el acceso de usuarios a EKS.

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

Reemplace las rutas por los archivos emitidos y restrinja el acceso a la clave privada y al kubeconfig. Base64 en los campos `*-data` no es cifrado. Inspeccione los archivos kubeconfig no confiables antes de usarlos: pueden ejecutar comandos mediante complementos de credenciales.

#### 2. Tokens de ServiceAccount

Un ServiceAccount es una identidad de carga de trabajo con ámbito de namespace. Cada namespace tiene una cuenta `default`; el `serviceAccountName` de un Pod hace referencia a una cuenta del mismo namespace. Seleccionar una cuenta no concede por sí mismo acceso a recursos de la aplicación.

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

`automountServiceAccountToken` es un campo de nivel superior de ServiceAccount y un campo `spec` de Pod. La configuración de Pod tiene precedencia. Controla el montaje predeterminado; no impide un volumen proyectado `serviceAccountToken` declarado explícitamente.

Para los Pods que necesitan acceso a la API, kubelet obtiene y rota los tokens proyectados predeterminados mediante TokenRequest. El archivo de token predeterminado es `/var/run/secrets/kubernetes.io/serviceaccount/token`. Las aplicaciones deben recargar el archivo rotado. El vencimiento y la vinculación de audiencia reducen la exposición, pero no hacen que sea seguro revelar un bearer token. No asuma que crear una cuenta crea automáticamente un token Secret de larga duración. El [ejemplo de volumen proyectado del cuestionario](../quizzes/security/02-kubernetes-auth-authz-quiz.md) cubre una audiencia personalizada y una vigencia solicitada.

#### 3. OpenID Connect (OIDC)

OIDC permite que el servidor API valide **ID tokens** de un proveedor de identidad externo. Configure el emisor, la audiencia, la validación de firma/vencimiento y el mapeo de identidad. El servidor API no proporciona un inicio de sesión interactivo ni emite refresh tokens. Los clientes usan una herramienta revisada o un complemento de credenciales `exec` para su proveedor de identidad.

Estos son **indicadores adicionales para un servidor API autoadministrado**, no un comando de inicio completo ni un kubeconfig. Reemplace el emisor HTTPS y el ID de cliente de ejemplo.

```text
--oidc-issuer-url=https://idp.example.com
--oidc-client-id=kubernetes
--oidc-username-claim=sub
--oidc-username-prefix=oidc:
--oidc-groups-claim=groups
--oidc-groups-prefix=oidc:
```

Agregue prefijos a los nombres de usuario y grupos para evitar colisiones con identidades existentes, como los grupos `system:`. La `AuthenticationConfiguration` estructurada es una alternativa; no combine `--authentication-config` con los indicadores `--oidc-*`. Configure un proveedor OIDC externo para EKS mediante el procedimiento administrado independiente que se muestra a continuación.

#### 4. Autenticación de tokens mediante webhook

Un servidor API autoadministrado envía una **TokenReview** de `authentication.k8s.io/v1` a un servicio externo. Lo siguiente es un **kubeconfig independiente que utiliza el servidor API para llegar a ese servicio**. No es un campo `authentication.webhook` en el kubeconfig de un usuario.

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

Si se instala en `/etc/kubernetes/authn-webhook.kubeconfig`, configure `--authentication-token-webhook-config-file=/etc/kubernetes/authn-webhook.kubeconfig` y `--authentication-token-webhook-version=v1` en el servidor API. Aprovisione por separado los certificados y el servicio referenciados. El servicio debe validar el token y la audiencia prevista, y devolver una respuesta TokenReview. Diseñe TLS mutuo, protección de credenciales, TTL de caché y comportamiento ante fallas. Este ejemplo no proporciona ni una implementación de webhook ni validación de disponibilidad.

#### 5. Proxy de autenticación

Un proxy de autenticación verifica al solicitante y reenvía el nombre de usuario y los grupos resultantes. Solo nombrar encabezados confiables no establece la confianza. Primero autentique la identidad TLS del proxy mediante una CA de front-proxy dedicada y un CN de certificado de cliente permitido.

**Extracto de indicadores de servidor API autoadministrado:**

```text
--requestheader-client-ca-file=/etc/kubernetes/front-proxy-ca.crt
--requestheader-allowed-names=front-proxy-client
--requestheader-username-headers=X-Remote-User
--requestheader-group-headers=X-Remote-Group
```

El proxy debe eliminar los encabezados de identidad proporcionados por el solicitante y reemplazarlos por valores verificados. No reutilice la CA habitual de cliente de usuario como CA de proxy ni deje los CN permitidos vacíos para confiar en todos los certificados de cliente. Este extracto no implementa el proxy en sí.

### Usuarios y grupos

En Kubernetes, los usuarios se clasifican de la siguiente manera:

1. **Usuarios regulares**: Se administran fuera del cluster; Kubernetes no los administra directamente.
2. **Service Accounts**: Cuentas administradas por la API de Kubernetes.

Los usuarios pueden pertenecer a uno o más grupos, y los grupos se utilizan en políticas de autorización.

## Autorización

La autorización es el proceso de verificar si un usuario autenticado tiene permiso para realizar la acción solicitada. Kubernetes admite varios módulos de autorización.

### Modos de autorización

#### 1. RBAC (Role-Based Access Control)

RBAC proporciona control de acceso basado en roles y actualmente es el mecanismo de autorización más utilizado en Kubernetes.

**Conceptos clave:**

1. **Role**: Define permisos dentro de un namespace.
2. **ClusterRole**: Una definición con ámbito de cluster para recursos de cluster, URL sin recursos o permisos reutilizables sobre recursos con ámbito de namespace.
3. **RoleBinding**: Hace referencia a un Role en el mismo namespace o a un ClusterRole y concede permisos **solo en el namespace del binding**. Un sujeto ServiceAccount puede pertenecer explícitamente a otro namespace.
4. **ClusterRoleBinding**: Concede los permisos de un ClusterRole en todo el cluster; no puede hacer referencia a un Role.

Una definición de rol no concede nada sin un binding. RBAC agrega permisos permitidos y no tiene reglas de denegación explícita. `get/list/watch` en Secret permite leer datos secretos, por lo que estos ejemplos usan lecturas de Pod en su lugar.

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

El ClusterRoleBinding ilustra un grupo de operaciones que necesita explícitamente **información de Pod en todos los namespaces**; no es una recomendación predeterminada. Para un único namespace, use allí un RoleBinding con `roleRef.kind: ClusterRole` y `roleRef.name: pod-reader-reusable`.

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
    "apiGroup": "",
    "resource": "pods",
    "readonly": true
  }
}
```

ABAC se incluye para comprender los clusters autoadministrados existentes. La política consumida por `--authorization-policy-file` es un archivo con **un objeto JSON por línea**, no un recurso de la API de Kubernetes. La sangría anterior es explicativa; serialice cada política en una línea en el archivo real. Los cambios requieren reiniciar el servidor API. Prefiera RBAC para configuraciones nuevas; este indicador no es un mecanismo de configuración de EKS.

#### 3. Autorización de Node

La autorización de Node es específica de los kubelets. Su identidad debe pertenecer a `system:nodes` y usar el nombre de usuario `system:node:<nodeName>`, que debe coincidir con el nombre de Node real. No es un mecanismo de acceso de cargas de trabajo. En clusters autoadministrados, combínela con la admisión NodeRestriction para restringir los cambios de kubelet a objetos Node y Pod.

#### 4. Autorización mediante webhook

Un servidor API autoadministrado envía una **SubjectAccessReview** de `authorization.k8s.io/v1` a un servicio externo. Use el mismo formato de archivo de conexión que el webhook de autenticación anterior, con un endpoint de autorización, una CA y un certificado de cliente independientes. Configure `--authorization-webhook-config-file` y `--authorization-webhook-version=v1`, o use `AuthorizationConfiguration` estructurada para configurar la cadena y la política de fallas. No existe un campo `authorization.webhook` en un kubeconfig de usuario.

Los autorizadores se ejecutan en el orden configurado; el primer **Allow o Deny** decide. `NoOpinion` continúa con el siguiente autorizador; todos los resultados NoOpinion deniegan el acceso. Un webhook posterior no puede vetar una solicitud que RBAC ya permitió. `system:masters` es un grupo especial que omite la autorización RBAC y webhook; no lo asigne a administradores ordinarios ni suponga que eliminar un role binding revoca su acceso.

### Prácticas recomendadas de autorización

1. **Principio de mínimo privilegio**: Conceda solo los permisos mínimos necesarios.
2. **Separación de roles**: Conceda los permisos apropiados según roles como administradores, desarrolladores y operadores.
3. **Separación de namespaces**: Separe los namespaces por equipo o proyecto y conceda los permisos apropiados.
4. **Separación de Service Accounts**: Use Service Accounts independientes para cada aplicación.
5. **Auditoría periódica**: Revise y actualice periódicamente las políticas de autorización.

## Control de admisión

El control de admisión realiza validaciones y modificaciones adicionales antes de procesar solicitudes después de la autenticación y la autorización.

La admisión gestiona la creación, los cambios, la eliminación y algunas solicitudes de conexión; las **lecturas get/list/watch omiten la admisión**. La mutación precede a la validación, y cualquiera de las fases puede rechazar una solicitud.

### Tipos de controladores de admisión

1. **Controladores de admisión mutantes**: Pueden modificar solicitudes.
2. **Controladores de admisión de validación**: Solo validan solicitudes sin modificarlas.

### Controladores de admisión clave

1. **LimitRanger**: Aplica valores predeterminados y restricciones mínimas/máximas definidas por LimitRange.
2. **ResourceQuota**: Comprueba las cuotas configuradas del namespace para cantidades de objetos, solicitudes de recursos y cantidades similares; no es un límite para el consumo medido de CPU/memoria ni para el gasto.
3. **PodSecurity**: Aplica los estándares de seguridad de Pod según etiquetas de namespace. La antigua PodSecurityPolicy se eliminó en Kubernetes 1.25.
4. **ServiceAccount**: Asigna automáticamente Service Accounts a los pods.
5. **DefaultStorageClass**: Selecciona una StorageClass predeterminada para un PVC sin una clase especificada; no crea la StorageClass.

### Control de admisión dinámico

El control de admisión dinámico se implementa mediante webhooks:

1. **MutatingAdmissionWebhook**: Puede modificar solicitudes.
2. **ValidatingAdmissionWebhook**: Solo valida solicitudes sin modificarlas.

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

Este webhook se dirige solo a namespaces etiquetados explícitamente. No lo instale sin el servicio HTTPS, la CA y una implementación de AdmissionReview reales que conserve el UID de la solicitud. `failurePolicy: Fail` bloquea las solicitudes coincidentes ante errores/tiempos de espera de llamada. `Ignore` ignora las fallas de llamada; no convierte una denegación devuelta correctamente en una autorización. Pruebe la disponibilidad y la recuperación en un namespace dedicado. CEL ValidatingAdmissionPolicy es otra opción para validación.

## Ejemplos prácticos de implementación

### Configuración de autenticación y autorización en EKS

#### Integración de IAM y RBAC

Use **access entries** para el acceso actual de usuarios de IAM a EKS. Un rol IAM proporciona la identidad autenticada; las políticas de acceso EKS asociadas o Kubernetes RBAC conceden permisos de Kubernetes. Los permisos permitidos de ambas rutas se acumulan. Una política de acceso EKS no es una política IAM.

Lo siguiente es un ejemplo de cambio de un administrador para un cluster y un rol IAM existentes. Primero confirme la cuenta, la región, el cluster, el modo `API` o `API_AND_CONFIG_MAP`, un namespace `development` existente, la ausencia de una access entry duplicada y los permisos para `eks:CreateAccessEntry` y los cambios de RBAC. No es un script de creación de infraestructura ni un procedimiento de migración completo.

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

Después de aplicar los objetos RBAC, verifique el acceso con las credenciales reales del rol. Este ejemplo no asocia ninguna política de acceso, y crear una access entry no crea objetos RBAC. Los bindings o las políticas existentes pueden hacer que los permisos efectivos sean más amplios que estas lecturas de Pod. Considere el retraso de propagación.

El ConfigMap `aws-auth` es el mecanismo heredado. Reemplazar el ConfigMap completo puede eliminar los mapeos de Node/Fargate. Planifique la migración de `CONFIG_MAP` a `API_AND_CONFIG_MAP`, migre y verifique los mapeos, y luego use `API`. Una vez habilitado, el acceso de API no puede eliminarse al revertir los modos; `API` no puede regresar a un modo ConfigMap. Al usar ambos, una access entry tiene precedencia para el mismo principal IAM. No todos los mapeos existentes se migran automáticamente.

`kubectl auth can-i --list` no muestra los permisos de las políticas de acceso EKS. La suplantación con `--as`/`--as-group` fuerza la evaluación de Kubernetes RBAC y, por tanto, no prueba los permisos de la política de acceso del rol IAM. Verifique acciones individuales como el rol real, incluidas las denegaciones esperadas fuera del namespace y para lecturas de Secret.

#### Configuración del proveedor OIDC

Estas tres rutas tienen direcciones y propósitos diferentes.

| Ruta | Destino y configuración de autenticación |
|---|---|
| Usuario OIDC externo → API de Kubernetes | Asocie el IdP externo mediante `AssociateIdentityProviderConfig` de EKS y, después, vincule sus usuarios/grupos a RBAC. EKS debe poder alcanzar al emisor mediante HTTPS público; con salida de control plane enrutada por el cliente (`controlPlaneEgressMode=CUSTOMER_ROUTED`), también se debe poder alcanzar al emisor mediante la ruta de salida que configure en la VPC. No se admiten certificados de emisor autofirmados. Esto no deshabilita la autenticación IAM. |
| Pod → API de AWS mediante IRSA | Establezca la confianza IAM en el emisor OIDC de ServiceAccount del cluster, restrinja la confianza del rol al namespace/ServiceAccount previsto y conceda solo los recursos AWS necesarios. `eksctl utils associate-iam-oidc-provider` es para esta ruta, no para el inicio de sesión de usuario externo. |
| Pod → API de AWS mediante EKS Pod Identity | Use el agente Pod Identity y una asociación de rol en entornos de ejecución admitidos. Esto difiere de la configuración del proveedor OIDC de IAM de IRSA. |

Ninguno de los mecanismos de carga de trabajo concede Kubernetes API RBAC por sí mismo. Evite usar como ejemplo predeterminado una política administrada de lectura de S3 para toda la cuenta; limite los permisos a los ARN reales de bucket/objeto. Siga [OIDC externo de EKS](https://docs.aws.amazon.com/eks/latest/userguide/authenticate-oidc-identity-provider.html) y [roles IAM de cargas de trabajo](https://docs.aws.amazon.com/eks/latest/userguide/service-accounts.html) para conocer los detalles de configuración.

### Seguridad de clusters multiinquilino

En entornos multiinquilino, el aislamiento entre inquilinos es importante.

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
  policyTypes: [Ingress]
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          tenant: a
```

Esta política permite tráfico de entrada desde **todos** los namespaces etiquetados con `tenant: a`. Otras políticas de entrada pueden agregar permisos y la salida no tiene restricciones. Requiere la aplicación de NetworkPolicy por parte de CNI; solo los administradores de confianza deben controlar las etiquetas y políticas de namespace. Un namespace por sí solo no garantiza un aislamiento sólido entre inquilinos hostiles. El cuestionario incluye denegación predeterminada en ambas direcciones; revise los permisos independientes para DNS y el tráfico necesario.

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

## Prácticas recomendadas de seguridad

1. **Rotación periódica de certificados**: Renueve los certificados periódicamente.
2. **Deshabilitar el montaje automático de tokens de ServiceAccount**: Deshabilite el montaje automático de tokens de ServiceAccount cuando no sea necesario.
3. **Minimizar las políticas RBAC**: Conceda solo los permisos mínimos necesarios.
4. **Implementar Network Policies**: Restrinja la comunicación entre pods.
5. **Habilitar el registro de auditoría**: Verifique la cobertura de audit-policy, las exclusiones de datos sensibles, la retención y el acceso a los registros. En EKS, habilite el tipo de registro de control plane `audit` y verifique la entrega a CloudWatch; no suponga que se registra cada cuerpo de solicitud.
6. **Configurar Security Contexts**: Configure correctamente los security contexts de pods y contenedores.
7. **Escaneo de imágenes**: Analice periódicamente las imágenes de contenedor para detectar vulnerabilidades.

## Conclusión

El sistema de autenticación y autorización de Kubernetes es un elemento fundamental de la seguridad del cluster. Al seleccionar métodos de autenticación apropiados, implementar control de acceso detallado mediante RBAC y aplicar políticas de seguridad adicionales mediante controladores de admisión, puede crear un entorno de Kubernetes seguro.

La autenticación, la autorización y el control de admisión se complementan entre sí, y es importante usarlos juntos para implementar una estrategia de Defense in Depth.

## Referencias oficiales

- [Autenticación de Kubernetes](https://kubernetes.io/docs/reference/access-authn-authz/authentication/)
- [Autorización de Kubernetes](https://kubernetes.io/docs/reference/access-authn-authz/authorization/)
- [RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
- [Configuración de ServiceAccount](https://kubernetes.io/docs/tasks/configure-pod-container/configure-service-account/)
- [ABAC](https://kubernetes.io/docs/reference/access-authn-authz/abac/)
- [Autorización de Node](https://kubernetes.io/docs/reference/access-authn-authz/node/)
- [Controladores de admisión](https://kubernetes.io/docs/reference/access-authn-authz/admission-controllers/)
- [Webhooks de admisión](https://kubernetes.io/docs/reference/access-authn-authz/extensible-admission-controllers/)
- [NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Firma de certificados de EKS](https://docs.aws.amazon.com/eks/latest/userguide/cert-signing.html)
- [Access entries de EKS](https://docs.aws.amazon.com/eks/latest/userguide/creating-access-entries.html)
- [Modos de autenticación de EKS](https://docs.aws.amazon.com/eks/latest/userguide/setting-up-access-entries.html)
- [Evaluación de políticas de acceso de EKS](https://docs.aws.amazon.com/eks/latest/userguide/access-policies.html)
- [Registros de auditoría de EKS](https://docs.aws.amazon.com/eks/latest/userguide/control-plane-logs.html)
- [kubeconfig confiable](https://kubernetes.io/docs/concepts/configuration/organize-cluster-access-kubeconfig/)
