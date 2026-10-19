# Sistema de autenticación y autorización de Kubernetes

> **Alcance**: API estables de Kubernetes y administración del acceso de usuarios de Amazon EKS
> **Última actualización**: 12 de octubre de 2026

## Descripción general

La autenticación establece la identidad de la solicitud, la autorización decide qué operaciones de la API puede realizar esa identidad y la admisión aplica políticas adicionales a los cambios autorizados. Los manifiestos siguientes son ejemplos independientes para aprender; prepare antes los espacios de nombres, los permisos de administrador, los certificados y los servidores de webhooks. No se probaron llamadas en vivo al clúster ni a su API, ni cambios en el acceso a EKS.

Los ejemplos de indicadores de `kube-apiserver` se aplican a un **plano de control autogestionado**. Use la configuración de acceso administrada para EKS; estos ejemplos no son instrucciones para configurar sus indicadores de servidor API ni obtener su clave privada de CA.

## Autenticación

La autenticación es el proceso de verificar que un usuario o servicio es quien afirma ser. Kubernetes admite varios métodos de autenticación, que pueden habilitarse simultáneamente.

Cuando hay varios autenticadores, se usa el primer resultado satisfactorio, aunque no se garantiza el orden de evaluación. Las credenciales no válidas pueden hacer fallar la autenticación. El tratamiento de las solicitudes sin credenciales depende de la configuración de autenticación anónima; una identidad anónima también necesita autorización.

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

Un ServiceAccount es una identidad de carga de trabajo con ámbito de espacio de nombres. Cada espacio de nombres tiene una cuenta `default`; el `serviceAccountName` de un Pod hace referencia a una cuenta del mismo espacio de nombres. Seleccionar una cuenta no concede por sí mismo acceso a recursos de la aplicación.

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

Para los Pods que necesitan acceso a la API, kubelet obtiene y rota los tokens proyectados predeterminados mediante TokenRequest. El archivo de token predeterminado es `/var/run/secrets/kubernetes.io/serviceaccount/token`. Las aplicaciones deben volver a leer el archivo tras su rotación. El vencimiento y la vinculación a una audiencia reducen la exposición, pero no hacen seguro divulgar un token de portador. No dé por sentado que crear una cuenta genera automáticamente un token Secret de larga duración. El [ejemplo de volumen proyectado del cuestionario](../quizzes/security/02-kubernetes-auth-authz-quiz.md) muestra una audiencia personalizada y una vigencia solicitada.

#### 3. OpenID Connect (OIDC)

OIDC permite que el servidor API valide **tokens de ID** de un proveedor de identidad externo. Configure el emisor, la audiencia, la validación de firma y vencimiento, y el mapeo de identidad. El servidor API no ofrece inicio de sesión interactivo ni emite tokens de actualización. Los clientes usan una herramienta revisada o un complemento de credenciales `exec` para su proveedor de identidad.

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

Un proxy de autenticación verifica al solicitante y reenvía el nombre de usuario y los grupos resultantes. El mero hecho de declarar encabezados de confianza no establece una relación de confianza. Primero autentique la identidad TLS del proxy mediante una CA dedicada para el front proxy y un CN de certificado de cliente permitido.

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

1. **Usuarios regulares**: Se administran fuera del clúster; Kubernetes no los administra directamente.
2. **Cuentas de servicio**: Cuentas administradas por la API de Kubernetes.

Los usuarios pueden pertenecer a uno o más grupos, y los grupos se utilizan en políticas de autorización.

## Autorización

La autorización es el proceso de verificar si un usuario autenticado tiene permiso para realizar la acción solicitada. Kubernetes admite varios módulos de autorización.

### Modos de autorización

#### 1. RBAC (Role-Based Access Control)

RBAC proporciona control de acceso basado en roles y actualmente es el mecanismo de autorización más utilizado en Kubernetes.

**Conceptos clave:**

1. **Role**: Define permisos dentro de un espacio de nombres.
2. **ClusterRole**: Una definición de ámbito de clúster para recursos del clúster, rutas URL que no corresponden a recursos de la API o permisos reutilizables para recursos con ámbito de espacio de nombres.
3. **RoleBinding**: Hace referencia a un Role del mismo espacio de nombres o a un ClusterRole y concede permisos **solo en el espacio de nombres de la vinculación**. El sujeto puede ser una ServiceAccount de otro espacio de nombres si así se indica explícitamente.
4. **ClusterRoleBinding**: Concede los permisos de un ClusterRole en todo el clúster; no puede hacer referencia a un Role.

Una definición de rol no concede permisos sin vincularse a un sujeto. RBAC solo añade permisos y no admite reglas explícitas de denegación. `get/list/watch` sobre Secret permite leer sus datos, por lo que estos ejemplos usan permisos de lectura de Pods.

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

El ClusterRoleBinding ilustra un grupo de operaciones que necesita explícitamente **información de Pods en todos los espacios de nombres**; no es una recomendación predeterminada. Para un solo espacio de nombres, cree allí un RoleBinding con `roleRef.kind: ClusterRole` y `roleRef.name: pod-reader-reusable`.

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

ABAC se incluye para comprender los clústeres autoadministrados existentes. La política consumida por `--authorization-policy-file` es un archivo con **un objeto JSON por línea**, no un recurso de la API de Kubernetes. La sangría anterior es explicativa; serialice cada política en una línea en el archivo real. Los cambios requieren reiniciar el servidor API. Prefiera RBAC para configuraciones nuevas; este indicador no es un mecanismo de configuración de EKS.

#### 3. Autorización de nodos

La autorización de nodos es específica para kubelets. La identidad de cada kubelet debe pertenecer a `system:nodes` y usar el nombre de usuario `system:node:<nodeName>`, que debe coincidir con el nombre del objeto Node real. Este mecanismo no sirve para controlar el acceso de las cargas de trabajo. En clústeres autoadministrados, combínelo con la admisión NodeRestriction para limitar los cambios que hace kubelet a objetos Node y Pod.

#### 4. Autorización mediante webhook

Un servidor API autoadministrado envía una **SubjectAccessReview** de `authorization.k8s.io/v1` a un servicio externo. Use el mismo formato de archivo de conexión que para el webhook de autenticación anterior, con un punto de conexión de autorización, una CA y un certificado de cliente independientes. Configure `--authorization-webhook-config-file` y `--authorization-webhook-version=v1`, o use `AuthorizationConfiguration` estructurada para configurar la cadena de autorización y la política ante fallas. El kubeconfig de un usuario no tiene un campo `authorization.webhook`.

Los autorizadores se ejecutan en el orden configurado; el primer **Allow o Deny** determina el resultado. `NoOpinion` hace que se consulte al siguiente autorizador; si todos responden NoOpinion, se deniega el acceso. Un webhook posterior no puede vetar una solicitud que RBAC ya permitió. `system:masters` es un grupo especial que omite la autorización RBAC y la del webhook; no lo asigne a administradores ordinarios ni suponga que eliminar una asociación de rol revoca su acceso.

### Prácticas recomendadas de autorización

1. **Principio de mínimo privilegio**: Conceda solo los permisos mínimos necesarios.
2. **Separación de roles**: Conceda los permisos apropiados según roles como administradores, desarrolladores y operadores.
3. **Separación de espacios de nombres**: Separe los espacios de nombres por equipo o proyecto y conceda los permisos apropiados.
4. **Separación de cuentas de servicio**: Use una cuenta de servicio distinta para cada aplicación.
5. **Auditoría periódica**: Revise y actualice periódicamente las políticas de autorización.

## Control de admisión

El control de admisión realiza validaciones y modificaciones adicionales antes de procesar solicitudes después de la autenticación y la autorización.

La admisión gestiona la creación, los cambios, la eliminación y algunas solicitudes de conexión; las **lecturas get/list/watch omiten la admisión**. La mutación precede a la validación, y cualquiera de las fases puede rechazar una solicitud.

### Tipos de controladores de admisión

1. **Controladores de admisión que modifican solicitudes**: Pueden cambiar las solicitudes.
2. **Controladores de admisión validadores**: Solo validan las solicitudes, sin modificarlas.

### Controladores de admisión clave

1. **LimitRanger**: Aplica valores predeterminados y restricciones mínimas/máximas definidas por LimitRange.
2. **ResourceQuota**: Comprueba las cuotas configuradas del espacio de nombres para cantidades de objetos, solicitudes de recursos y cantidades similares; no es un límite para el consumo medido de CPU/memoria ni para el gasto.
3. **PodSecurity**: Aplica los estándares de seguridad de Pod según etiquetas de espacio de nombres. La antigua PodSecurityPolicy se eliminó en Kubernetes 1.25.
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

Este webhook se aplica únicamente a espacios de nombres con etiquetas explícitas. No lo instale sin un servicio HTTPS operativo, la CA correspondiente y una implementación de AdmissionReview que conserve el UID de la solicitud. `failurePolicy: Fail` bloquea las solicitudes coincidentes si la llamada falla o agota el tiempo de espera. `Ignore` omite los errores de llamada, pero no convierte una denegación devuelta correctamente en una respuesta de autorización positiva. Pruebe la disponibilidad y la recuperación en un espacio de nombres dedicado. CEL ValidatingAdmissionPolicy es otra opción de validación.

## Ejemplos prácticos de implementación

### Configuración de autenticación y autorización en EKS

#### Integración de IAM y RBAC

Use **entradas de acceso (access entries)** para gestionar el acceso de usuarios de IAM a EKS. Un rol de IAM proporciona la identidad autenticada; las políticas de acceso de EKS asociadas o RBAC de Kubernetes conceden permisos para Kubernetes. Los permisos concedidos por ambas vías se acumulan. Una política de acceso de EKS no es una política de IAM.

El siguiente ejemplo muestra un cambio administrativo en un clúster y un rol de IAM existentes. Antes de ejecutarlo, confirme que usa la cuenta y la región correctas; que el clúster está en modo `API` o `API_AND_CONFIG_MAP`; que existe el espacio de nombres `development`; que no hay ya una entrada de acceso duplicada; y que cuenta con permisos para `eks:CreateAccessEntry` y para los cambios de RBAC. No es un script para crear infraestructura ni un procedimiento completo de migración.

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

Después de aplicar los objetos RBAC, verifique el acceso con las credenciales reales del rol. Este ejemplo no asocia ninguna política de acceso, y crear una entrada de acceso no crea objetos RBAC. Las vinculaciones o políticas existentes pueden ampliar los permisos efectivos más allá de estas lecturas de Pods. Tenga en cuenta el retraso de propagación.

El ConfigMap `aws-auth` es el mecanismo heredado. Reemplazar el ConfigMap completo puede eliminar los mapeos de Node/Fargate. Planifique la migración de `CONFIG_MAP` a `API_AND_CONFIG_MAP`, migre y verifique los mapeos, y luego use `API`. Una vez habilitado, el acceso de API no puede eliminarse al revertir los modos; `API` no puede regresar a un modo ConfigMap. Al usar ambos, una entrada de acceso tiene prioridad para el mismo principal IAM. No todos los mapeos existentes se migran automáticamente.

`kubectl auth can-i --list` no muestra los permisos de las políticas de acceso EKS. La suplantación con `--as`/`--as-group` fuerza la evaluación de Kubernetes RBAC y, por tanto, no prueba los permisos de la política de acceso del rol IAM. Verifique acciones individuales como el rol real, incluidas las denegaciones esperadas fuera del espacio de nombres y para lecturas de Secret.

#### Configuración del proveedor OIDC

Estas tres rutas tienen direcciones y propósitos diferentes.

| Ruta | Destino y configuración de autenticación |
|---|---|
| Usuario OIDC externo → API de Kubernetes | Asocie el IdP externo mediante `AssociateIdentityProviderConfig` de EKS y, después, vincule sus usuarios/grupos a RBAC. EKS debe poder alcanzar al emisor mediante HTTPS público; con salida de plano de control enrutada por el cliente (`controlPlaneEgressMode=CUSTOMER_ROUTED`), también se debe poder alcanzar al emisor mediante la ruta de salida que configure en la VPC. No se admiten certificados de emisor autofirmados. Esto no deshabilita la autenticación IAM. |
| Pod → API de AWS mediante IRSA | Establezca la confianza IAM en el emisor OIDC de ServiceAccount del clúster, restrinja la confianza del rol al espacio de nombres/ServiceAccount previsto y conceda solo los recursos AWS necesarios. `eksctl utils associate-iam-oidc-provider` es para esta ruta, no para el inicio de sesión de usuario externo. |
| Pod → API de AWS mediante EKS Pod Identity | Use el agente Pod Identity y una asociación de rol en entornos de ejecución admitidos. Esto difiere de la configuración del proveedor OIDC de IAM de IRSA. |

Ninguno de estos mecanismos para cargas de trabajo concede por sí solo permisos RBAC en la API de Kubernetes. Evite usar como ejemplo predeterminado una política administrada que permita leer S3 en toda la cuenta; limite los permisos a los ARN de los buckets y objetos necesarios. Consulte [OIDC externo de EKS](https://docs.aws.amazon.com/eks/latest/userguide/authenticate-oidc-identity-provider.html) y [roles IAM de cargas de trabajo](https://docs.aws.amazon.com/eks/latest/userguide/service-accounts.html) para ver los detalles de configuración.

### Seguridad de clústeres multiinquilino

En entornos multiinquilino, el aislamiento entre inquilinos es importante.

**Aislamiento de espacio de nombres:**

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

Esta política permite tráfico de entrada desde **todos** los espacios de nombres etiquetados con `tenant: a`. Otras políticas de entrada pueden agregar permisos y la salida no tiene restricciones. Requiere que la CNI aplique NetworkPolicy; solo los administradores de confianza deben controlar las etiquetas y políticas de los espacios de nombres. Un espacio de nombres por sí solo no garantiza un aislamiento sólido entre inquilinos hostiles. El cuestionario incluye denegación predeterminada en ambas direcciones; revise los permisos independientes para DNS y el tráfico necesario.

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
2. **Deshabilitar el montaje automático de tokens de ServiceAccount**: Deshabilite este montaje cuando la aplicación no necesite el token.
3. **Minimizar las políticas RBAC**: Conceda solo los permisos mínimos necesarios.
4. **Implementar políticas de red**: Restrinja la comunicación entre Pods.
5. **Habilitar el registro de auditoría**: Verifique la cobertura de la política de auditoría, las exclusiones de datos sensibles, la retención y el acceso a los registros. En EKS, habilite el tipo de registro `audit` del plano de control y compruebe que los registros lleguen a CloudWatch; no dé por sentado que se registra el cuerpo de todas las solicitudes.
6. **Configurar contextos de seguridad**: Configure correctamente los contextos de seguridad de los Pods y contenedores.
7. **Escaneo de imágenes**: Analice periódicamente las imágenes de contenedor en busca de vulnerabilidades.

## Conclusión

El sistema de autenticación y autorización de Kubernetes es un elemento fundamental de la seguridad del clúster. Al seleccionar métodos de autenticación apropiados, implementar control de acceso detallado mediante RBAC y aplicar políticas de seguridad adicionales mediante controladores de admisión, puede crear un entorno de Kubernetes seguro.

La autenticación, la autorización y el control de admisión se complementan entre sí, y es importante usarlos juntos para implementar una estrategia de defensa en profundidad.

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
