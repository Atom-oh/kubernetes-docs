# Capacidades de Amazon EKS: Argo CD administrado, kro y ACK

> **Versiones compatibles**: EKS 1.36–1.37, Argo CD `3.4.6-eks-2` y `3.4.7-eks-1`, kro `0.9.4-eks-1`, ACK `46.186.1-eks-1`, AWS CLI 2.38.3
> **Última actualización**: 23 de octubre de 2026

EKS Capabilities ejecuta Argo CD, kro (Kube Resource Orchestrator) y ACK (AWS Controllers for Kubernetes) como controladores operados por AWS fuera del clúster. La función estuvo disponible de forma general el 30 de noviembre de 2025. La entrega de registros de los controladores (Vended Logs) llegó en junio de 2026, y la configuración personalizada de `argocd-cm` para Argo CD, en agosto de 2026.

Las cifras de este capítulo se midieron en octubre de 2026 en clústeres de prueba de ap-northeast-2. El clúster principal usó subredes privadas, authenticationMode `API` y dos nodos m7g.large (el hub y el spoke usados para las pruebas de actualización y multiclúster tenían un nodo cada uno). Se repitieron los mismos escenarios con controladores autoadministrados (OSS) instalados en el mismo clúster. Cada escenario se ejecutó solo entre 1 y 5 veces, así que interpreta las cifras como rangos y vuelve a verificarlas en tu entorno antes de tomar decisiones operativas. Todo lo que se verificó únicamente en la documentación, sin medirlo, está marcado como «según la documentación». El informe de las mediciones y los resultados sin procesar están en la [serie de artículos sobre EKS Capabilities](https://blog.atomai.click/eks-capabilities-argocd/) (en coreano).

## Índice

1. [Modelo común](#common)
2. [Creación y operación cotidiana](#create)
3. [Capability de Argo CD](#argocd)
4. [Capability de kro](#kro)
5. [Capability de ACK](#ack)
6. [Uso conjunto de las tres](#together)
7. [Actualizaciones del clúster y versiones de las capabilities](#upgrade)
8. [Multiclúster y sustitución blue/green](#multicluster)
9. [Comparación con la gestión autoadministrada y cuándo elegirla](#compare)
10. [Precios](#pricing)
11. [Alcance de la verificación y referencias](#refs)

---

<span id="common"></span>

## 1. Modelo común

| Elemento | Comportamiento |
|---|---|
| Ubicación del controlador | Infraestructura propiedad de AWS. No hay Pods en los nodos de trabajo (se midió cero para los tres) |
| Acceso al clúster | El rol de la capability (principal de confianza `capabilities.eks.amazonaws.com`) llama al servidor de la API a través de una entrada de acceso de EKS. Funciona incluso con un endpoint de la API solo privado |
| Cantidad | Una por tipo de capability y por clúster |
| Versión | AWS la elige y la implementa. Las API de creación y actualización no tienen un argumento de versión, así que no puedes fijarla ni elegirla |
| Eliminación | Solo `--delete-propagation-policy RETAIN`. Los CRD, CR, recursos implementados y la entrada de acceso permanecen |
| Registros | No están disponibles mediante `kubectl logs`. Se entregan con CloudWatch Vended Logs a CloudWatch Logs, S3 o Amazon Data Firehose (consulta [Supervisión y registro de EKS](./06-eks-monitoring-logging.md)) |
| Precios | Cargo por hora de la capability más un cargo por objeto administrado (Applications para Argo CD, instancias para kro, recursos para ACK) |

La característica común a las tres es que los permisos predeterminados son limitados. Con solo las políticas de entrada de acceso creadas automáticamente, Argo CD no puede implementar recursos, kro no puede iniciar el controlador RGD y ACK no puede crear recursos de AWS sin permisos de IAM por servicio. En cambio, los valores predeterminados de los Helm Chart de OSS tanto para Argo CD como para kro otorgan al controlador `apiGroups: ["*"], resources: ["*"], verbs: ["*"]`.

<span id="create"></span>

## 2. Creación y operación cotidiana

### Rol de la capability y comando de creación

Configura la confianza para `capabilities.eks.amazonaws.com` en el rol de la capability y permite `sts:AssumeRole` y `sts:TagSession`. kro nunca llama a las API de AWS, así que no necesita una política de permisos. Argo CD también funcionó sin una cuando se conectó a repositorios Git públicos.

```bash
aws eks create-capability --cluster-name "$CLUSTER_NAME" \
  --capability-name kro --type KRO \
  --role-arn "arn:aws:iam::${ACCOUNT_ID}:role/${CLUSTER_NAME}-kro" \
  --delete-propagation-policy RETAIN

aws eks describe-capability --cluster-name "$CLUSTER_NAME" --capability-name kro \
  --query 'capability.{status:status,version:version}'
```

| Capability | `CREATING` → `ACTIVE` | Eliminación | Políticas de entrada de acceso creadas automáticamente | CRD instalados |
|---|---|---|---|---|
| Argo CD | 349 s (385 s para una capability nueva con `endpointPrefix` en otro clúster, 338 s al volver a crearla con el mismo prefijo) | 100.5 s | `AmazonEKSArgoCDClusterPolicy` (clúster), `AmazonEKSArgoCDPolicy` (espacio de nombres `argocd`) | `applications`, `applicationsets`, `appprojects` |
| kro | 70.1–70.4 s | 46.9 s | `AmazonEKSKROPolicy` | `resourcegraphdefinitions.kro.run`, `graphrevisions.internal.kro.run` |
| ACK | 385.7 s (77 s cuando los CRD ya existen) | 67.3 s | `AmazonEKSACKPolicy` | 267 (66 grupos de API de servicios más `IAMRoleSelector` en `services.k8s.aws`) |

### Notas operativas

- **Mantén actualizado AWS CLI.** CLI 2.35.11 solo reconocía `namespace`, `awsIdc`, `rbacRoleMappings` y `networkAccess` dentro de `argoCd` (no incluía `endpointPrefix`) y rechazaba la configuración de ACK con `Unknown parameter in configuration: "ack", must be one of: argoCd`; 2.38.3 aceptaba ambas. Comprueba la versión de CLI antes de concluir que algo no es compatible.
- **Aplica los cambios de las capabilities de uno en uno.** Cada fuente de entrega de registros añadida puso la capability en `UPDATING` durante unos 6.6–7 segundos, y el siguiente cambio falló con `ConflictException: ... currently in UPDATING state`. Espera a que esté `ACTIVE` antes de continuar.
- **Activa la entrega de registros desde el primer día.** Como el controlador está fuera del clúster, los registros serán la única forma de observar más adelante su comportamiento interno (CloudTrail sigue mostrando las horas de las llamadas a la API de AWS). Los registros son JSON estructurado; Argo CD registra los tiempos por fase de cada reconciliación (`compare_app_state_ms`, `patch_ms` y otros).
- **RETAIN conserva «todo excepto el controlador».** Mientras se elimina una capability, los cambios en los CR no se reconcilian (se verificó cambiando las réplicas de una instancia de kro). Un controlador OSS que use los mismos CRD recoge los cambios pendientes cuando se instala.

<span id="argocd"></span>

## 3. Capability de Argo CD

### Registro del clúster local y permisos de implementación

Argo CD administrado no agrega como destino ni siquiera su propio clúster. Crea un Secret de clúster usando el ARN de EKS en vez de una URL de la API.

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: in-cluster
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: cluster
stringData:
  name: in-cluster
  server: arn:aws:eks:ap-northeast-2:111122223333:cluster/example-cluster
  project: default
```

La entrada de acceso creada automáticamente, por sí sola, no permite la sincronización, porque Argo CD enumera todos los tipos de recursos del clúster para crear su caché, no solo los recursos que implementa.

| Permisos de clúster del rol de la capability | Resultado |
|---|---|
| Solo la entrada de acceso creada automáticamente | `ComparisonError: ... podtemplates is forbidden ... at the cluster scope` |
| + `AmazonEKSEditPolicy` | Sigue fallando después de 141 s; se deniega la enumeración de `securitygrouppolicies.vpcresources.k8s.aws` |
| + `AmazonEKSAdminViewPolicy` | Se sincronizó y quedó Healthy en 11.6 s |
| Implementación de CR de las API de kro/ACK (una instancia de NginxApp, una Queue de ACK) | `nginxapps.platform.example.com is forbidden`. Se resolvió en 16 s al agregar un grupo de Kubernetes a la entrada de acceso y vincular un ClusterRole para ese grupo de API |

La documentación de AWS usa `AmazonEKSClusterAdminPolicy` (equivalente a `system:masters`) para empezar, y describe una configuración de producción con privilegios mínimos que combina acceso de lectura a todo el clúster con `AmazonEKSEditPolicy` limitado a espacios de nombres. En las pruebas funcionó el acceso Edit con ámbito de clúster junto con AdminView y un ClusterRole por CRD de plataforma; esto es más amplio que la configuración de producción documentada. Para limitarlo más, `resource.respectRBAC`, compatible con la capability administrada, restringe la supervisión a los recursos permitidos (no se probó).

### Sondeo de Git y webhooks

| Método | Commit → Synced (3 ejecuciones) |
|---|---|
| Administrado, sondeo predeterminado (6 minutos según la documentación) | 341.8 s, 619.3 s, 697.1 s |
| Administrado, webhook de GitHub | 7.0–7.3 s |
| Autoadministrado 3.4.6, sondeo predeterminado (120 s + 60 s de variación aleatoria) | 115.7–171.4 s |

El intervalo de sondeo administrado (`timeout.reconciliation`) no es una clave configurable y no se publica la variación aleatoria. Si el retraso de implementación no debe variar en varios minutos, los webhooks son prácticamente indispensables. Añade una cadena aleatoria a `webhook.github.secret` del `argocd-webhook-creds-secret` creado por la capability y registra `<server URL>/api/webhook` en el repositorio Git con el mismo secreto. La URL del servidor es una dirección pública alojada por AWS, así que no hace falta exponer un endpoint independiente para el webhook. Es probable que restringir el acceso público con un VPC endpoint también bloquee los webhooks de GitHub (no se probó).

La autocorrección de la desviación tuvo resultados similares: 2.08–2.32 s en la versión administrada y 1.05–3.06 s en la autoadministrada. Sin embargo, las autocorrecciones repetidas en la misma aplicación sin un commit nuevo activaron el retroceso exponencial de la versión upstream (2 s, ×3 en cada intento, con un máximo de 300 s), y la recuperación se ralentizó hasta casi 5 minutos (se midieron 251–254 s). La versión autoadministrada permite ajustar este comportamiento mediante las opciones `--self-heal-backoff-*`. La versión administrada solo expone tres claves de `argocd-cmd-params-cm` (`hydrator.enabled`, `application.namespaces`, `applicationsetcontroller.namespaces`), y la documentación de AWS indica que las solicitudes para ajustar los tiempos de autocorrección deben dirigirse a AWS Support. Si es urgente, inicia una sincronización manual.

### Configuración, comprobaciones de estado y CLI

Crea el ConfigMap `argocd-cm` en el espacio de nombres de la capability con la etiqueta `app.kubernetes.io/part-of: argocd`. Las claves no compatibles se ignoran sin aviso.

| Elemento | Resultado |
|---|---|
| `ui.bannercontent` | Se muestra en la interfaz |
| Comprobación de estado Lua para una instancia de kro | Se aplicó; los cambios al script surtieron efecto en unos 12 s |
| Lua `string.upper()`, `os.time()` | `attempt to index a non-table object(nil)`, estado `Unknown`. Igual que el valor predeterminado upstream (`useOpenLibs` desactivado), pero la versión administrada no permite activarlo |
| `argocd login --username admin` o `--sso` | Ambos fallan |
| Token de la interfaz + `ARGOCD_SERVER`, `ARGOCD_AUTH_TOKEN`, `ARGOCD_OPTS=--grpc-web` | Funcionan `app list/get/sync`, `cluster list`, `proj list` |
| Hook PreSync con espera de 150 s | Terminó en `Succeeded` en 161 s, pese al tiempo de espera de sincronización documentado de 120 s; se desconoce a qué fase se aplica el límite |

Argo CD 3.x no almacena de forma predeterminada el estado de salud de los recursos en el estado de Application, así que es normal que `.status.resources[].health` esté vacío en `kubectl get application -o json`. Comprueba el estado de salud con `argocd app get` o en la interfaz.

Según la documentación, no son compatibles, entre otros, Config Management Plugins (CMP), el controlador Notifications, el SSO personalizado, las extensiones de la interfaz y `argocd admin`. Si envías notificaciones de implementación con Notifications o generas manifiestos mediante un CMP, no puedes pasarte tal cual a la capability administrada.

### Inicio de sesión: solo IAM Identity Center

La autenticación se realiza exclusivamente mediante IAM Identity Center, sin usuarios locales. `rbacRoleMappings` en la configuración de la capability asigna usuarios (`SSO_USER`) o grupos (`SSO_GROUP`) de Identity Center a ADMIN, EDITOR o VIEWER. Okta o Microsoft Entra ID no se conectan directamente a Argo CD; configura el proveedor de identidad externo como fuente de identidad de Identity Center, usando SAML para el inicio de sesión y SCIM para sincronizar usuarios y grupos (según la documentación).

- Una instancia de Identity Center tiene una sola fuente de identidad. Si la instancia de la organización ya usa otro proveedor de identidad, para dar a Argo CD un proveedor distinto se necesita una instancia de cuenta (no se probó).
- La instancia de Identity Center vinculada no se puede cambiar después de la creación (según la ayuda de la consola de EKS). Las asignaciones se almacenan como ID de usuarios y grupos; al cambiar la fuente de identidad a Active Directory se eliminan los usuarios y grupos, por lo que hay que volver a crear las asignaciones.
- Una capability admite hasta 1,000 identidades asignadas, así que conviene asignar grupos en vez de usuarios. Solo hay tres roles globales, por lo que las políticas detalladas de `argocd-rbac-cm` deben trasladarse a los roles de AppProject.

<span id="kro"></span>

## 4. Capability de kro

La documentación de AWS afirma que kro administrado usa el mismo controlador upstream y es totalmente compatible. En las pruebas, la versión indicada, `0.9.4-eks-1`, coincidía con la versión OSS más reciente, y los mismos RGD y expresiones CEL se comportaron de forma idéntica. Las diferencias están en los permisos y las operaciones. Para conocer los conceptos y ejemplos de kro, consulta el [capítulo de kro](../platform-engineering/03-kro.md).

### Los permisos predeterminados no permiten iniciar el controlador

`AmazonEKSKROPolicy` cubre únicamente el grupo `kro.run` y los CRD. No otorga permiso para supervisar la API generada a partir del grupo del esquema RGD (por ejemplo, `platform.example.com`) ni para crear los Deployment y Service secundarios. El fallo aparece como un tiempo de espera agotado al sincronizar la caché, no como un error de acceso denegado.

```text
ControllerReady=False FailedToStart
  ...
  cache sync timeout for platform.example.com/v1alpha1, Resource=nginxapps
```

La guía de eksctl vincula `AmazonEKSClusterAdminPolicy` para empezar. Una alternativa con privilegios mínimos consiste en agregar un grupo de Kubernetes a la entrada de acceso y vincular un ClusterRole por RGD.

```bash
aws eks update-access-entry --cluster-name "$CLUSTER_NAME" \
  --principal-arn "arn:aws:iam::${ACCOUNT_ID}:role/${CLUSTER_NAME}-kro" \
  --kubernetes-groups kro-workloads
```

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: kro-workloads-reviewed-nginxapps
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: kro:controller:reviewed-nginxapps
subjects:
  - kind: Group
    name: kro-workloads
    apiGroup: rbac.authorization.k8s.io
```

Cuando se otorgaron los permisos después del RGD, este pasó a `Active` solo 228 s más tarde (presumiblemente por el intervalo de reintento del controlador; no se confirmó en los registros). Un segundo RGD cuyo ClusterRole se aplicó primero pasó a `Active` de inmediato. Mantén el RGD y su ClusterRole en la misma ruta de Git y aplica primero RBAC con sync waves (no se probaron las sync waves). `rbac.mode: aggregation` de OSS también combina únicamente los ClusterRole etiquetados en los permisos del controlador, así que requiere un trabajo similar (según el chart; no se probó).

### Rendimiento del ciclo de vida y migración

| Fase (5 ejecuciones cada una) | Administrado | OSS 0.9.4 |
|---|---|---|
| Creación → `ACTIVE` | 2.49–3.73 s | 2.43–3.44 s |
| Cambio de Spec → Deployment actualizado | 0.50–0.52 s (un valor atípico de 51.6 s, causa desconocida) | 0.49–0.56 s |
| Eliminación → Deployment y Service eliminados | 1.02–3.02 s | 1.01–4.38 s |

El cambio de administrado → OSS → administrado dejó intactos dos RGD y cuatro instancias (se quitó un controlador antes de instalar el otro). Para migrar sin tiempo de inactividad, sigue el procedimiento de AWS para transferir el lease de elección del líder (no se probó), pero ten en cuenta que la ruta del chart y la clave del valor están desactualizadas: el chart actual es `oci://registry.k8s.io/kro/charts/kro`, y la clave de la versión 0.9.4 es `config.leaderElectionNamespace`.

### Riesgo: kro se hace cargo de CR existentes con el mismo nombre

Si ya existe en el espacio de nombres un CR con el mismo nombre que un recurso secundario, kro no lo rechaza; lo sobrescribe mediante server-side apply. En las pruebas, un CR de Table de ACK existente recibió `kro.run/owned=true` y un `spec.tableName` modificado; ACK creó una tabla nueva y la tabla original quedó sin administrar. Al eliminar la instancia también se eliminó el CR del que se había hecho cargo. OSS 0.9.4 reprodujo el mismo comportamiento, así que se trata de un comportamiento upstream.

- Añade un sufijo específico del RGD a los nombres de los recursos secundarios (`${schema.metadata.name + "-os"}`).
- Separa los espacios de nombres administrados por kro de aquellos donde la gente crea CR directamente.
- Configura `services.k8s.aws/deletion-policy: retain` en los recursos de ACK que contienen datos. Esto no impide que un cambio de nombre cree un recurso nuevo, así que la verdadera solución es separar los nombres (no se probó `retain` en combinación con este caso).
- En clústeres multiinquilino, no permitas que las instancias elijan libremente `ingressClassName` ni los nombres de host; fíjalos en el RGD o derívalos del nombre de la instancia.

<span id="ack"></span>

## 5. Capability de ACK

ACK administrado reúne en una capability todos los controladores de servicios que tienen disponibilidad general upstream; los controladores en vista previa se agregan automáticamente cuando alcanzan esa disponibilidad (según la documentación). Para conocer el modelo de recursos, la adopción y la retención de ACK, consulta el [capítulo de ACK](../platform-engineering/02-ack.md).

### IAM por equipo con IAMRoleSelector

Otorga al rol de la capability únicamente permiso para asumir roles de equipo y asigna espacios de nombres a roles mediante un `IAMRoleSelector` con ámbito de clúster. Cada rol de equipo confía en el rol de la capability y permite `sts:AssumeRole` y `sts:TagSession`.

```json
{"Effect": "Allow", "Action": ["sts:AssumeRole", "sts:TagSession"],
 "Resource": ["arn:aws:iam::111122223333:role/ack-team-a",
              "arn:aws:iam::111122223333:role/ack-team-b"]}
```

```yaml
apiVersion: services.k8s.aws/v1alpha1
kind: IAMRoleSelector
metadata:
  name: team-b
spec:
  arn: arn:aws:iam::111122223333:role/ack-team-b
  namespaceSelector:
    names: [team-b]
```

La creación de un Bucket de S3 en team-b falló con `AccessDenied` porque su rol solo permitía SQS; el mensaje identificó el rol que realmente se usó (`assumed-role/ack-team-b/...`). La condición del CR `ACK.IAMRoleSelected=True` también indica que coincidió un selector. Los detalles confirmaron lo siguiente:

- El controlador de Bucket de S3 llama primero a `s3:ListAllMyBuckets`. Incluso si los recursos de bucket se restringen con un patrón de nombres, esta acción (con el recurso `*`) parece necesitar permisos aparte (no se probó sin ellos).
- Los espacios de nombres sin un selector coincidente usan el rol de la capability (según la documentación). Sin permisos para el servicio en el rol de la capability, el resultado predeterminado es la denegación.
- Para conseguir la misma separación con controladores OSS, configura tanto `featureGates.IAMRoleSelector=true` como `enableCARM=false`. Con el valor predeterminado del chart `enableCARM: true`, el controlador entra en un ciclo de fallos con `cannot enable feature gate 'IAMRoleSelector' when flag 'enable-carm' is set to true`.

### Creación de recursos, etiquetas y desviación

| Recurso | Administrado (3 ejecuciones) | OSS (2 ejecuciones) |
|---|---|---|
| Queue de SQS | 1.04–1.06 s | 1.10–1.16 s |
| Bucket de S3 | 3.10–3.14 s | 3.20–3.32 s |
| Table de DynamoDB | 11.28–11.53 s | 10.15–11.54 s |

Solo la primera creación, justo después de crear la capability, fue más lenta: Queue, 7.3 s; Bucket, 10.9 s; Table, 16.5 s.

ACK administrado añade cinco etiquetas a los recursos de AWS: `eks:controller-version`, `eks:kubernetes-namespace`, `eks:kubernetes-resource-name`, `eks:kubernetes-api-group` y `eks:eks-capability-arn`. Todas las llamadas a las API de AWS incluyen las etiquetas de sesión `eks:eks-capability-arn`, `eks:kubernetes-namespace` y `eks:kubernetes-api-group`. OSS añade dos etiquetas: `services.k8s.aws/controller-version` y `services.k8s.aws/namespace`. Al migrar desde OSS cambia el prefijo de las etiquetas, así que actualiza al mismo tiempo las etiquetas de asignación de costos y las condiciones de IAM basadas en etiquetas.

ACK no supervisa en tiempo real los cambios que se hacen directamente en AWS. Un cambio de `VisibilityTimeout` de SQS realizado fuera de ACK (con CLI) no se revirtió periódicamente en un plazo de 25 minutos, ni con la versión administrada (2 ejecuciones) ni con OSS (1 ejecución). Las dos reversiones observadas en la versión administrada se produjeron 86 s después de que la capability pasara por `UPDATING` para cambiar una configuración de registros y justo después de volver a crear la capability (horas de las llamadas obtenidas de CloudTrail). Un reinicio del controlador parece ser el desencadenante, pero esto no se confirmó en los registros. El intervalo de resincronización predeterminado de OSS es de 10 horas (`reconcile.defaultResyncPeriod: 36000`) y se puede ajustar; el intervalo de la versión administrada no se publica ni se puede modificar. Si es importante recuperarse rápidamente, evita los cambios fuera de banda mediante SCP o condiciones de IAM; por ejemplo, permite cambios en recursos etiquetados con `aws:ResourceTag/eks:eks-capability-arn` solo cuando las llamadas tengan una `aws:PrincipalTag/eks:eks-capability-arn` coincidente (no se probó).

### Diferencias de la versión administrada y migración

- No existe el CRD `FieldExport`. Para exportar valores de estado a un ConfigMap o Secret, usa otro método, como hacer que kro escriba el estado en un ConfigMap.
- Desactivar servicios con `--configuration '{"ack":{"disabledServices":["sagemaker"]}}'` surtió efecto en 12.5 s con CLI 2.38.3, pero los CRD ya instalados para ese servicio seguían presentes después de 350 s. En su lugar, especifica los servicios que no se usarán al crear la capability (no se probó la configuración durante la creación).
- Las versiones de los controladores estaban un paso por detrás de las versiones OSS más recientes (s3 1.12.2 frente a 1.13.1, sqs 1.7.1 frente a 1.8.2).
- Las anotaciones de adopción (`services.k8s.aws/adoption-policy: adopt-or-create`) y de retención funcionan en la capability administrada: la adopción tardó 4.7 s, y una Queue eliminada con `retain` permaneció en AWS (medido en la versión administrada). Tras eliminar la capability, un controlador OSS adoptó sin cambios los 12 CR restantes.

<span id="together"></span>

## 6. Uso conjunto de las tres

La división natural es: Argo CD sincroniza manifiestos desde Git, kro compone varios recursos en una API y ACK crea los recursos de AWS que forman parte de ella. El RGD `OrderService` probado creó una Queue y una Table de ACK, copió sus valores de estado (la URL de la queue y el ARN de la tabla) a un ConfigMap e inició un Deployment.

| Combinación | Resultado | Configuración adicional necesaria |
|---|---|---|
| Argo CD → Queue de ACK | El CR de Queue de Git se sincronizó en 6.5 s | RBAC para `queues.sqs.services.k8s.aws` en el rol de la capability de Argo CD |
| kro → Queue y Table de ACK + ConfigMap + Deployment | La instancia quedó `ACTIVE` en 13.2–34.3 s (principalmente por la creación de la tabla de DynamoDB) | RBAC para los recursos de ACK en el rol de la capability de kro; IAMRoleSelector en ACK |

Los CRD de ACK no están cubiertos por las políticas de acceso predeterminadas de EKS (como `AmazonEKSEditPolicy`), así que el componente que cree recursos de ACK —Argo CD o kro— necesita permisos para esos grupos de API. Las dos mediciones se hicieron por separado; no se ejecutó de principio a fin la secuencia completa de tres pasos.

<span id="upgrade"></span>

## 7. Actualizaciones del clúster y versiones de las capabilities

### Comportamiento durante una actualización in situ

Se actualizó in situ de 1.36 a 1.37 un clúster con las tres capabilities. La actualización del plano de control tardó unos 7 minutos, y las tres capabilities permanecieron `ACTIVE` con la misma versión, estado de salud y `modifiedAt`.

| Fase | Autocorrección de Argo CD | Propagación de kro | Sincronización de Queue de ACK |
|---|---|---|---|
| Antes (3 ejecuciones) | 2.1–14.6 s | 1.02–1.04 s | 1.49–3.53 s |
| Durante (4 ejecuciones) | 2.1 s, 6.1 s, 112.9 s, 254.5 s | 1.02–1.07 s | 1.52–1.58 s |
| Después (5 ejecuciones) | 2.3 s, luego 251–252 s | 1.01–1.15 s | 1.47–1.57 s |

En kro y ACK, una de las cuatro ejecuciones «durante» se realizó justo después de terminar la actualización. El retraso de autocorrección durante la actualización se reprodujo de forma idéntica después de esta, así que se debió al retroceso exponencial de la autocorrección descrito antes, no a la actualización. No se midieron kro ni ACK durante los aproximadamente 3 minutos en que la versión del servidor de la API alternó entre 1.36.4 y 1.37.0. Los grupos de nodos no se actualizaron.

La actualización in situ no requirió pasos específicos para las capabilities. En los controladores autoadministrados hay que comprobar que admitan la nueva versión de Kubernetes y, posiblemente, actualizarlos primero; el modelo administrado deja esa comprobación de compatibilidad en manos de AWS. Ten en cuenta que ninguna de las comprobaciones de información sobre actualizaciones de EKS cubría las capabilities.

### No puedes elegir la versión

`create-capability` y `update-capability` no tienen un argumento de versión, y la documentación de AWS solo menciona «actualizaciones automáticas y parches de seguridad». No se encontró en la documentación un calendario de actualizaciones, aviso previo, ventana de mantenimiento, notas de publicación por versión ni un procedimiento para revertir versiones de las capabilities. La [reversión de la versión del clúster](./08-eks-upgrades.md), añadida en julio de 2026, revierte la versión secundaria de Kubernetes, y la documentación de reversión no cubre las capabilities. Como las capabilities no tienen un argumento de versión, no la consideres un medio para revertir una versión de capability (inferencia). En las pruebas, una capability de Argo CD creada el 21 de octubre indicó `3.4.6-eks-2`, y otra creada un día después en otro clúster indicó `3.4.7-eks-1`. Las versiones de los controladores pueden cambiar independientemente de las actualizaciones del clúster.

Prepárate para una versión con errores de la siguiente manera:

| Preparación | Cómo | Fundamento |
|---|---|---|
| Registrar los cambios de versión | Consulta periódicamente `capability.version` con `describe-capability` y compáralo con los incidentes | Medido (campo confirmado) |
| Clúster de validación | Ejecuta primero los RGD, Applications y CR de ACK de producción en un clúster con las mismas capabilities. No puedes controlar el orden de implementación, así que no hay garantía de que se actualice antes que producción | Inferencia |
| Fijar el comportamiento en Git | Mantén las comprobaciones de estado (`resource.customizations`), las opciones de sincronización y RBAC en Git para que volver a crear o migrar reproduzca el mismo comportamiento | Medido (configuración aplicada) |
| AWS Support | No existe una reversión que pueda hacer el usuario, así que abre un caso. La documentación de AWS indica que las solicitudes para ajustar los tiempos de autocorrección deben dirigirse a Support | Inferencia (el ajuste de los tiempos de autocorrección según la documentación) |
| Alternativa temporal autoadministrada | Al eliminar una capability con RETAIN se conservan los CRD y los recursos, y un controlador OSS que use esos CRD se hace cargo (medido para kro, ACK y Argo CD). En Argo CD fue necesario cambiar `server` del Secret del clúster, del ARN de EKS a una URL de la API (`https://kubernetes.default.svc` en local); los spokes remotos o privados registrados mediante ARN necesitan su propia ruta de red y autenticación con OSS. Para volver al modo administrado hay que volver a crear la capability (unos 6 minutos para Argo CD) | Medido |
| Reversión de ACK por servicio | Añade solo el servicio afectado a `disabledServices` e instala o escala su controlador autoadministrado. El controlador OSS necesita su propia configuración de IAM, además de `featureGates.IAMRoleSelector=true` y `enableCARM=false` cuando se usa IAMRoleSelector. No se probó ejecutar el chart OSS sobre CRD instalados por la capability. Los CRD ya instalados permanecen (medido) | Según la documentación |

Si necesitas claramente fijar las versiones, la propia documentación de AWS recomienda la modalidad autoadministrada («se requieren versiones específicas de la API de recursos de Kubernetes o compilaciones personalizadas del controlador»).

<span id="multicluster"></span>

## 8. Multiclúster y sustitución blue/green

### Hub de Argo CD y spoke privado

La capability de Argo CD de un clúster hub registró un spoke en la misma cuenta y VPC cuyo endpoint de la API era solo privado, sin configuración de red (endpoints, grupos de seguridad ni rutas). Una estación de trabajo en otra VPC no pudo acceder al spoke, así que la conexión aparentemente usa una ruta proporcionada por AWS. El spoke necesita una entrada de acceso para el rol de la capability del hub, que se debe crear manualmente.

| Permisos de la entrada de acceso del spoke | Resultado |
|---|---|
| `AmazonEKSEditPolicy` + `AmazonEKSAdminViewPolicy` | La conexión y la autenticación funcionaron, pero `CreateNamespace=true` falló con `namespaces is forbidden`; se agotaron cinco reintentos automáticos (unos 303 s) |
| + `AmazonEKSArgoCDClusterPolicy`, luego sincronización manual | Se sincronizó y quedó Healthy en 11.1 s |

- Los Secret de clúster solo aceptan ARN de EKS, así que los clústeres que no sean de EKS no pueden ser destinos (según la documentación).
- El cargo por aplicación cuenta las Applications por clúster de destino, así que ubicar las aplicaciones en el hub o en cada clúster cuesta lo mismo; solo aumenta el cargo de la capability según la cantidad de instancias de Argo CD. Sin embargo, el rol de la capability del hub tiene acceso de escritura a todos los spokes, así que considera restringir los destinos de AppProject o dividir las capabilities por equipo.
- Según la documentación, los clústeres de otras cuentas solo necesitan una entrada de acceso para el rol de la capability del hub (no se probó). Los límites de la modalidad administrada son 100 clústeres remotos y 3,000 Applications.

### Dónde ubicar kro y ACK

Las capabilities de kro y ACK solo administran su propio clúster. Para que Argo CD del hub implemente instancias RGD o CR de ACK en un spoke, el spoke también necesita kro o ACK (administrados u OSS).

| Distribución | Adecuada cuando | Inquietudes |
|---|---|---|
| kro en cada clúster, con los RGD distribuidos mediante un ApplicationSet | Los equipos de aplicaciones usan la misma API en cada clúster | Los cargos de las capabilities y el trabajo de RBAC aumentan con la cantidad de clústeres; la documentación no garantiza versiones idénticas de kro entre clústeres (no se probó) |
| kro solo en el hub; los RGD crean recursos de ACK y Applications de Argo CD para los spokes | Las abstracciones de plataforma se definen en un solo lugar | Los permisos y el radio de impacto se concentran en el hub; los equipos de aplicaciones de los spokes no pueden usar directamente la API de kro (no se probó) |
| ACK centralizado (hub) | Recursos propiedad de la plataforma, como bases de datos, IAM y VPC | El rol de la capability del hub tiene permisos para todas las cuentas y los recursos |
| ACK distribuido (por clúster) | Queues y buckets declarados junto a las cargas de trabajo | La configuración de IAMRoleSelector aumenta con la cantidad de clústeres |
| ACK híbrido | Recursos con ámbito de administrador en el hub y recursos con ámbito de carga de trabajo en los spokes | Necesita reglas de ámbito para que un recurso nunca se declare en dos ubicaciones |

En todas las distribuciones, define reglas de ámbito para que dos clústeres no declaren el mismo recurso de AWS al mismo tiempo.

### Sustitución blue/green

- **Argo CD**: La capability pertenece a su clúster, así que sustituir el clúster que aloja Argo CD implica volver a crearla. La dirección predeterminada `argocd-<ID>-<account ID>.eks-capabilities.<region>.amazonaws.com` varía según el clúster, por lo que cambian las URL de la interfaz y de los webhooks. Si se define `endpointPrefix` durante la creación, al eliminar y volver a crear la capability con el mismo prefijo se conservó la dirección (solo se probó en el mismo clúster). La dirección no contiene nada específico del clúster, así que también debería funcionar después de trasladarla a otro clúster. Si el prefijo es único dentro de una cuenta y una región (no se probó), los clústeres antiguo y nuevo no pueden tenerlo al mismo tiempo; la sustitución pasa a ser una eliminación seguida de una nueva creación, durante las cuales se interrumpen la interfaz, los webhooks y la sincronización (se midieron 100 s más 338 s). Si esa pausa es inaceptable, crea primero una nueva capability con otro prefijo y cambia la URL del webhook de Git; desactiva la sincronización automática de la antigua o elimina sus Applications sin propagación en cascada antes de activar la nueva, y crea de antemano las entradas de acceso del nuevo rol de la capability en los clústeres de destino (no se probó). El prefijo no se puede cambiar después de la creación. Ubica Argo CD en un hub dedicado en vez de en clústeres de cargas de trabajo que se sustituyen con frecuencia.
- **kro**: Los ClusterRole y las vinculaciones se trasladan mediante Git, pero agregar un grupo de Kubernetes a la entrada de acceso es una llamada a la API de EKS. Inclúyelo en la IaC que crea los clústeres (eksctl, Terraform, etc.).
- **ACK**: Una secuencia posible consiste en eliminar los CR del clúster antiguo con `deletion-policy: retain` y luego adoptar los mismos recursos en el clúster nuevo con `adoption-policy: adopt-or-create` (se midió cada paso; no se probó la secuencia completa entre clústeres). Si una SCP bloquea los cambios según la etiqueta `eks:eks-capability-arn`, la nueva capability tendrá un ARN distinto y la adopción podría bloquearse; relaja la condición durante la transición o condiciona el acceso a etiquetas de entorno o equipo.

<span id="compare"></span>

## 9. Comparación con la gestión autoadministrada y cuándo elegirla

| Elemento | Capability administrada | Autoadministrada (OSS) |
|---|---|---|
| Tiempo de instalación | Argo CD 349 s, kro 70 s, ACK 386 s | Argo CD 43.4 s, kro 15.6 s, tres controladores de ACK 46 s |
| Recursos de los nodos | Ninguno | Argo CD: 7 Pods (339–624Mi de memoria), kro: 1 Pod (solicitudes de 256m, 128Mi), ACK: 3 Pods (cada uno solicita 50m, 64Mi) |
| Versión | La elige AWS; no se puede fijar | La eliges tú (Argo CD v3.5.5 y ACK s3 1.13.1 eran las versiones más recientes al momento de las pruebas) |
| Permisos predeterminados | Limitados; debes otorgar permisos de implementación, de recursos secundarios y de IAM | Los valores predeterminados de los chart de Argo CD y kro son `*/*/*` |
| Rendimiento | kro, ACK y la autocorrección de Argo CD igualan a OSS; el sondeo predeterminado de Argo CD es más lento | Referencia (Argo CD 3.4.6 y kro 0.9.4 se midieron con las mismas versiones; ACK OSS usó una versión más reciente) |
| SSO | Solo Identity Center, dos campos de configuración | Dex, OIDC y otros; los configuras tú |
| Clústeres remotos | ARN de EKS + entrada de acceso; clústeres privados sin configuración de red | URL de la API, autenticación y ruta de red por clúster |
| Funciones que faltan | Argo CD Notifications, CMP, `argocd admin`, bibliotecas estándar de Lua; FieldExport de ACK | Ninguna |
| Aspectos que no se pueden ajustar directamente | Sondeo de Argo CD, intervalo de resincronización de ACK, indicadores del controlador y límites de recursos; el retroceso exponencial de autocorrección de Argo CD solo se puede ajustar mediante AWS Support | Todo se puede ajustar |
| Registros | Vended Logs | `kubectl logs`, con recopilación propia |

La modalidad administrada es adecuada cuando:

- Estás creando un hub que implementa en varios clústeres de EKS, especialmente en clústeres privados o de otras cuentas.
- Ya centralizas los inicios de sesión de AWS en Identity Center y no quieres administrar por tu cuenta el SSO de Argo CD.
- Administras varios servicios de AWS desde Kubernetes, ejecutar un controlador ACK por servicio supone una carga y necesitas separar el acceso de IAM por equipo.
- Quieres que los permisos de los controladores de plataforma sean limitados de forma predeterminada y explícitos en las entradas de acceso y RBAC.

Conviene mantener la modalidad autoadministrada cuando:

- Dependes de Notifications, CMP, FieldExport o de las bibliotecas estándar de Lua.
- Entre tus destinos de implementación hay clústeres que no son de EKS.
- Solo Argo CD debe usar un proveedor de identidad distinto al Identity Center de la organización y no tienes la opción de usar una instancia de cuenta.
- Debes controlar por tu cuenta las versiones de los controladores, los tiempos de actualización y los intervalos de sondeo o resincronización.

Un buen momento para evaluarla es antes de crecer más allá de un clúster: la ubicación del hub, la instancia de Identity Center y `endpointPrefix` quedan fijados o son difíciles de cambiar después de la creación. Otro buen momento es cuando un Argo CD autoadministrado necesita una reconstrucción de alta disponibilidad o una actualización importante. El procedimiento de migración de AWS escala el controlador existente a cero, traslada las Applications y los Secret y cambia `destination.server` al ARN; mientras tanto, se detiene la sincronización (no se probó).

<span id="pricing"></span>

## 10. Precios

Los precios corresponden a Seúl (ap-northeast-2), se consultaron con la API de precios de AWS el 21 de octubre de 2026 y usan 730 horas al mes.

| Capability | Cargo de la capability | Cargo por objeto | Ejemplo (al mes) |
|---|---|---|---|
| Argo CD | $0.034799 por hora (unos $25.4/mes) | $0.001726 por hora de Application (se cuenta por clúster de destino) | 9 aplicaciones: unos $36.7; 100 aplicaciones: unos $151 |
| kro | $0.006038 por hora (unos $4.4/mes) | $0.000061 por hora de instancia | 100 instancias: unos $8.9 |
| ACK | $0.006038 por hora (unos $4.4/mes) | $0.000061 por hora de recurso | 200 recursos: unos $13.3 |

A modo de comparación, al distribuir el costo de m7g.large (Seúl: $0.1003 por hora) entre las instalaciones autoadministradas predeterminadas, se obtienen unos $5.6 para Argo CD (624Mi de memoria), $9.4 para kro (solicitud de CPU de 256m) y $5.5 para tres controladores de ACK (solicitud de CPU de 150m). Las configuraciones de alta disponibilidad y el aumento de aplicaciones o servicios también elevan el costo de OSS. Argo CD administrado se vuelve más caro a medida que aumenta la cantidad de aplicaciones; en kro y ACK la diferencia es pequeña, así que la carga operativa y las funciones que faltan son los factores decisivos.

<span id="refs"></span>

## 11. Alcance de la verificación y referencias

Las mediciones se hicieron en una sola cuenta de ap-northeast-2: un clúster de EKS 1.36.4 y dos clústeres para las pruebas de actualización y multiclúster (hub de 1.36 a 1.37 y spoke privado 1.37). Los escenarios se ejecutaron entre 1 y 5 veces, con un máximo de 9 aplicaciones de Argo CD, 6 instancias de kro y unos 20 recursos de ACK. ACK solo se probó con S3, SQS y DynamoDB. No se probaron los siguientes casos, por lo que la información se basa en la documentación: integración con Okta o Entra ID e instancias de cuenta de Identity Center, acceso privado mediante un VPC endpoint, registro de clústeres de otras cuentas o VPC, Notifications y CMP, ACK entre cuentas, migración sin tiempo de inactividad con las versiones administrada y OSS en ejecución simultánea, y la secuencia completa de retención y posterior adopción de ACK entre clústeres. Los clústeres de prueba y los recursos de AWS se eliminaron después de las mediciones.

- [EKS Capabilities](https://docs.aws.amazon.com/eks/latest/userguide/capabilities.html)
- [Consideraciones sobre EKS Capabilities](https://docs.aws.amazon.com/eks/latest/userguide/capabilities-considerations.html)
- [Recursos de Kubernetes de Capability](https://docs.aws.amazon.com/eks/latest/userguide/capability-kubernetes-resources.html)
- [Consideraciones sobre Argo CD](https://docs.aws.amazon.com/eks/latest/userguide/argocd-considerations.html)
- [Comparación entre EKS Capability para Argo CD y Argo CD autoadministrado](https://docs.aws.amazon.com/eks/latest/userguide/argocd-comparison.html)
- [Registrar clústeres de destino](https://docs.aws.amazon.com/eks/latest/userguide/argocd-register-clusters.html)
- [Configurar los ajustes de Argo CD](https://docs.aws.amazon.com/eks/latest/userguide/argocd-configure-settings.html)
- [Configurar los permisos de kro](https://docs.aws.amazon.com/eks/latest/userguide/kro-permissions.html)
- [Comparación entre EKS Capability para kro y kro autoadministrado](https://docs.aws.amazon.com/eks/latest/userguide/kro-comparison.html)
- [Configurar los permisos de ACK](https://docs.aws.amazon.com/eks/latest/userguide/ack-permissions.html)
- [Comparación entre EKS Capability para ACK y ACK autoadministrado](https://docs.aws.amazon.com/eks/latest/userguide/ack-comparison.html)
- [Acceder a los registros de los controladores de EKS Capabilities](https://docs.aws.amazon.com/eks/latest/userguide/capabilities-controller-logs.html)
- [Revertir un clúster a una versión anterior de Kubernetes](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html)
- [Precios de Amazon EKS](https://aws.amazon.com/eks/pricing/)
- Artículos sobre las mediciones (en coreano): [Argo CD administrado](https://blog.atomai.click/eks-capabilities-argocd/), [kro administrado](https://blog.atomai.click/eks-capabilities-kro/), [ACK administrado](https://blog.atomai.click/eks-capabilities-ack/)
- Manifiestos de prueba: [Atom-oh/eks-capabilities-demo](https://github.com/Atom-oh/eks-capabilities-demo)

[Cuestionario sobre EKS Capabilities](../quizzes/eks/13-eks-capabilities-quiz.md)
