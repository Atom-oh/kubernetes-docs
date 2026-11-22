# Capacidades de Amazon EKS: Argo CD administrado, kro y ACK

> **Versiones compatibles**: EKS 1.36–1.37, Argo CD `3.4.6-eks-2` y `3.4.7-eks-1`, kro `0.9.4-eks-1`, ACK `46.186.1-eks-1`, AWS CLI 2.38.3
> **Última actualización**: 19 de noviembre de 2026

EKS Capabilities ejecuta Argo CD, kro (Kube Resource Orchestrator) y ACK (AWS Controllers for Kubernetes) como controladores operados por AWS fuera del clúster. La función estuvo disponible de forma general el 30 de noviembre de 2025. La entrega de registros del controlador (Vended Logs) llegó en junio de 2026, y la configuración personalizada de `argocd-cm` para Argo CD, en agosto de 2026.

Las cifras de este capítulo se midieron en octubre de 2026 en clústeres de prueba en ap-northeast-2. El clúster principal usó subredes privadas, authenticationMode `API` y dos nodos m7g.large (el hub y el spoke usados para las pruebas de actualización y multiclúster tenían un nodo cada uno). Se repitieron los mismos escenarios con controladores autoadministrados (OSS) instalados en el mismo clúster. Cada escenario se ejecutó solo entre 1 y 5 veces, así que interprete las cifras como intervalos y vuelva a verificarlas en su propio entorno antes de tomar decisiones operativas. Todo lo que se verificó únicamente en la documentación, sin medirlo, se marca como «según la documentación». El informe de mediciones y los resultados sin procesar están en la [serie de artículos sobre EKS Capabilities](https://blog.atomai.click/eks-capabilities-argocd/) (en coreano).

## Tabla de contenido

1. [Modelo común](#common)
2. [Creación y operaciones cotidianas](#create)
3. [Capacidad de Argo CD](#argocd)
4. [Capacidad de kro](#kro)
5. [Capacidad de ACK](#ack)
6. [Uso conjunto de las tres](#together)
7. [Actualizaciones del clúster y versiones de las capacidades](#upgrade)
8. [Multiclúster y reemplazo azul/verde](#multicluster)
9. [Comparación con la gestión autoadministrada y cuándo elegirla](#compare)
10. [Precios](#pricing)
11. [Alcance de la verificación y referencias](#refs)

---

<span id="common"></span>

## 1. Modelo común

| Elemento | Comportamiento |
|---|---|
| Ubicación del controlador | Infraestructura propiedad de AWS. No hay Pods en los nodos de trabajo (se midió cero para los tres) |
| Acceso al clúster | El rol de la capacidad (principal de confianza `capabilities.eks.amazonaws.com`) llama al servidor de API mediante una entrada de acceso de EKS. Funciona incluso con un endpoint de API exclusivamente privado |
| Cantidad | Una por tipo de capacidad y por clúster |
| Versión | AWS la elige y actualiza. Las API de creación y actualización no tienen un argumento de versión, así que no se puede fijar ni seleccionar una |
| Eliminación | Solo `--delete-propagation-policy RETAIN`. Los CRD, los CR, los recursos implementados y la entrada de acceso permanecen |
| Registros | No están disponibles mediante `kubectl logs`. Se entregan con CloudWatch Vended Logs a CloudWatch Logs, S3 o Amazon Data Firehose (consulte [Supervisión y registro de EKS](./06-eks-monitoring-logging.md)) |
| Precios | Cargo por hora de la capacidad más un cargo por objeto administrado (Applications para Argo CD, instancias para kro y recursos para ACK) |

La característica común de las tres es que sus permisos predeterminados son limitados. Con solo las políticas de entrada de acceso creadas automáticamente, Argo CD no puede implementar, kro no puede iniciar el controlador RGD y ACK no puede crear recursos de AWS sin permisos de IAM específicos para cada servicio. En cambio, los valores predeterminados de los Helm Chart de OSS para Argo CD y kro otorgan al controlador `apiGroups: ["*"], resources: ["*"], verbs: ["*"]`.

<span id="create"></span>

## 2. Creación y operaciones cotidianas

### Rol de la capacidad y comando de creación

Configure la confianza para `capabilities.eks.amazonaws.com` en el rol de la capacidad y permita `sts:AssumeRole` y `sts:TagSession`. kro nunca llama a las API de AWS, por lo que no necesita una política de permisos. Argo CD también funcionó sin ella con repositorios Git públicos.

```bash
aws eks create-capability --cluster-name "$CLUSTER_NAME" \
  --capability-name kro --type KRO \
  --role-arn "arn:aws:iam::${ACCOUNT_ID}:role/${CLUSTER_NAME}-kro" \
  --delete-propagation-policy RETAIN

aws eks describe-capability --cluster-name "$CLUSTER_NAME" --capability-name kro \
  --query 'capability.{status:status,version:version}'
```

| Capacidad | `CREATING` → `ACTIVE` | Eliminación | Políticas de entrada de acceso creadas automáticamente | CRD instalados |
|---|---|---|---|---|
| Argo CD | 349 s (385 s para una capacidad nueva con `endpointPrefix` en otro clúster, 338 s al volver a crearla con el mismo prefijo) | 100.5 s | `AmazonEKSArgoCDClusterPolicy` (clúster), `AmazonEKSArgoCDPolicy` (espacio de nombres `argocd`) | `applications`, `applicationsets`, `appprojects` |
| kro | 70.1–70.4 s | 46.9 s | `AmazonEKSKROPolicy` | `resourcegraphdefinitions.kro.run`, `graphrevisions.internal.kro.run` |
| ACK | 385.7 s (77 s cuando los CRD ya existen) | 67.3 s | `AmazonEKSACKPolicy` | 267 (66 grupos de API de servicios más `IAMRoleSelector` en `services.k8s.aws`) |

### Notas operativas

- **Mantenga actualizado AWS CLI.** CLI 2.35.11 solo reconocía `namespace`, `awsIdc`, `rbacRoleMappings` y `networkAccess` en `argoCd` (sin `endpointPrefix`), y rechazaba la configuración de ACK con `Unknown parameter in configuration: "ack", must be one of: argoCd`; 2.38.3 aceptaba ambos. Compruebe la versión de CLI antes de concluir que algo no es compatible.
- **Aplique los cambios de capacidad de uno en uno.** Cada fuente de entrega de registros añadida puso la capacidad en `UPDATING` durante unos 6.6–7 segundos, y el siguiente cambio falló con `ConflictException: ... currently in UPDATING state`. Espere a que vuelva a `ACTIVE` entre cambios.
- **Habilite la entrega de registros desde el primer día.** Como el controlador está fuera del clúster, los registros son la única forma de observar su comportamiento interno posteriormente (CloudTrail sigue mostrando las horas de las llamadas a la API de AWS). Los registros son JSON estructurado; Argo CD registra los tiempos por fase de cada reconciliación (`compare_app_state_ms`, `patch_ms`, etc.).
- **RETAIN conserva «todo excepto el controlador».** Mientras se elimina una capacidad, los cambios en los CR no se reconcilian (se verificó cambiando las réplicas de una instancia de kro). Un controlador OSS que use los mismos CRD recoge los cambios pendientes una vez instalado.

<span id="argocd"></span>

## 3. Capacidad de Argo CD

### Registro del clúster local y permisos de implementación

Argo CD administrado no agrega como destino ni siquiera su propio clúster. Cree un Secret de clúster usando el ARN de EKS, no una URL de API.

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

La entrada de acceso creada automáticamente no basta para permitir la sincronización, porque Argo CD enumera todos los tipos de recursos del clúster para crear su caché, no solo los recursos que implementa.

| Permisos del rol de la capacidad en el clúster | Resultado |
|---|---|
| Solo la entrada de acceso creada automáticamente | `ComparisonError: ... podtemplates is forbidden ... at the cluster scope` |
| + `AmazonEKSEditPolicy` | Sigue fallando después de 141 s; se denegó la lista de `securitygrouppolicies.vpcresources.k8s.aws` |
| + `AmazonEKSAdminViewPolicy` | Sincronizado y Healthy en 11.6 s |
| Implementación de CR de las API de kro/ACK (una instancia de NginxApp, una Queue de ACK) | `nginxapps.platform.example.com is forbidden`. Se solucionó al agregar un grupo de Kubernetes a la entrada de acceso y asociarle un ClusterRole para ese grupo de API, en 16 s |

La documentación de AWS usa `AmazonEKSClusterAdminPolicy` (equivalente a `system:masters`) para empezar, y describe una configuración de mínimo privilegio para producción con acceso de lectura en todo el clúster y `AmazonEKSEditPolicy` limitado al espacio de nombres. En las pruebas, funcionó Edit con alcance de clúster más AdminView, junto con un ClusterRole por cada CRD de la plataforma; es una configuración más amplia que la configuración documentada para producción. Para restringirla aún más, `resource.respectRBAC`, compatible con la capacidad administrada, limita la observación a los recursos permitidos (no probado).

### Sondeo de Git y webhooks

| Método | Confirmación → Synced (3 ejecuciones) |
|---|---|
| Administrado, sondeo predeterminado (6 minutos según la documentación) | 341.8 s, 619.3 s, 697.1 s |
| Administrado, webhook de GitHub | 7.0–7.3 s |
| Autoadministrado 3.4.6, sondeo predeterminado (120 s + 60 s de variación aleatoria) | 115.7–171.4 s |

El intervalo de sondeo administrado (`timeout.reconciliation`) no es una clave configurable y no se publica la variación aleatoria. Si el retraso de implementación no debe variar en minutos, los webhooks son prácticamente imprescindibles. Asigne una cadena aleatoria a `webhook.github.secret` en el `argocd-webhook-creds-secret` creado por la capacidad y registre `<server URL>/api/webhook` con el mismo secreto en el repositorio Git. La URL del servidor es una dirección pública alojada por AWS, así que no es necesario exponer un endpoint de webhook independiente. Es probable que restringir el acceso público con un endpoint de VPC también bloquee los webhooks de GitHub (no probado).

La autocorrección de desviaciones tuvo resultados similares: 2.08–2.32 s para la versión administrada y 1.05–3.06 s para la autoadministrada. Sin embargo, las autocorrecciones repetidas de la misma app sin una confirmación nueva activaron la espera progresiva de upstream (2 s, ×3 cada vez, hasta un máximo de 300 s) y la recuperación se ralentizó hasta casi 5 minutos (se midieron 251–254 s). La versión autoadministrada permite ajustar esto con las opciones `--self-heal-backoff-*`. La versión administrada solo expone tres claves de `argocd-cmd-params-cm` (`hydrator.enabled`, `application.namespaces`, `applicationsetcontroller.namespaces`), y la documentación de AWS remite a AWS Support las solicitudes para cambiar los tiempos de autocorrección. Cuando sea urgente, active una sincronización manual.

### Configuración, comprobaciones de estado y CLI

Cree el ConfigMap `argocd-cm` en el espacio de nombres de la capacidad con la etiqueta `app.kubernetes.io/part-of: argocd`. Las claves no compatibles se ignoran sin aviso.

| Elemento | Resultado |
|---|---|
| `ui.bannercontent` | Se muestra en la interfaz |
| Comprobación de estado en Lua para una instancia de kro | Aplicada; los cambios en el script surtieron efecto en unos 12 s |
| `string.upper()` y `os.time()` de Lua | `attempt to index a non-table object(nil)`, estado `Unknown`. Igual que el valor predeterminado de upstream (`useOpenLibs` desactivado), pero la versión administrada no permite activarlo |
| `argocd login --username admin` o `--sso` | Ambos fallan |
| Token de la interfaz + `ARGOCD_SERVER`, `ARGOCD_AUTH_TOKEN`, `ARGOCD_OPTS=--grpc-web` | Funcionan `app list/get/sync`, `cluster list` y `proj list` |
| Hook PreSync que espera 150 s | `Succeeded` en 161 s, a pesar del tiempo de espera de sincronización documentado de 120 s; se desconoce a qué fase se aplica el límite |

Argo CD 3.x no almacena el estado de los recursos en el estado de Application de forma predeterminada, por lo que es normal que `.status.resources[].health` esté vacío en `kubectl get application -o json`. Compruebe el estado con `argocd app get` o en la interfaz.

Según la documentación, no se admiten, entre otras cosas, los Config Management Plugins (CMP), el SSO personalizado, las extensiones de la interfaz ni `argocd admin`. Si genera manifiestos mediante un CMP, no puede migrar tal cual a la capacidad administrada. El controlador Notifications, que no era compatible durante las mediciones de octubre de 2026 anteriores, se añadió en noviembre de 2026 (consulte a continuación).

### Actualización de noviembre de 2026: compatibilidad con Argo CD Notifications

Según el [anuncio del 3 de noviembre de 2026](https://aws.amazon.com/about-aws/whats-new/2026/11/amazon-eks-argo-cd-notifications/), la capacidad de EKS para Argo CD ahora es compatible con Argo CD Notifications: se definen activadores y plantillas de mensajes en el clúster y se suscriben Applications individuales con una anotación, igual que en Argo CD upstream. Se admiten 16 servicios de notificación, incluidos Slack, PagerDuty, Opsgenie, Amazon SQS y Amazon EventBridge. SQS y EventBridge se autentican mediante el IAM Capability Role, por lo que los eventos de implementación pueden alimentar flujos de trabajo basados en eventos sin almacenar credenciales en el clúster; para los servicios que necesitan credenciales de terceros (como un token de Slack), se puede hacer referencia a un ARN de AWS Secrets Manager en lugar del secreto. Está disponible sin costo adicional en todas las regiones donde se ofrece la capacidad. Las mediciones de este documento son anteriores al lanzamiento, por lo que aquí no se probaron las notificaciones.

### Inicio de sesión: solo IAM Identity Center

La autenticación se realiza exclusivamente mediante IAM Identity Center; no hay usuarios locales. `rbacRoleMappings` en la configuración de la capacidad asigna usuarios (`SSO_USER`) o grupos (`SSO_GROUP`) de Identity Center a ADMIN, EDITOR o VIEWER. Okta y Microsoft Entra ID no se conectan directamente a Argo CD; se debe establecer el IdP externo como origen de identidades de Identity Center, usando SAML para iniciar sesión y SCIM para sincronizar usuarios y grupos (según la documentación).

- Una instancia de Identity Center tiene un solo origen de identidades. Si la instancia de la organización ya usa otro IdP, para que solo Argo CD use un IdP diferente se necesita una instancia de cuenta (no probado).
- La instancia de Identity Center vinculada no se puede cambiar después de la creación (según la ayuda de la consola de EKS). Las asignaciones se almacenan como ID de usuario y de grupo; al cambiar el origen de identidades a Active Directory se eliminan los usuarios y grupos, por lo que hay que volver a crear las asignaciones.
- Una capacidad admite hasta 1.000 identidades asignadas, así que conviene asignar grupos en lugar de usuarios. Solo hay tres roles globales, por lo que las políticas detalladas de `argocd-rbac-cm` deben trasladarse a los roles de AppProject.

<span id="kro"></span>

## 4. Capacidad de kro

La documentación de AWS indica que kro administrado usa el mismo controlador upstream y es totalmente compatible. En las pruebas, la versión informada `0.9.4-eks-1` coincidía con la última versión de OSS, y los mismos RGD y expresiones CEL se comportaron de forma idéntica. Las diferencias están en los permisos y las operaciones. Para conocer los conceptos y ejemplos de kro, consulte el [capítulo sobre kro](../platform-engineering/03-kro.md).

### Los permisos predeterminados no permiten que se inicie el controlador

`AmazonEKSKROPolicy` solo cubre el grupo `kro.run` y los CRD. No otorga permisos para observar la API generada a partir del grupo de esquema del RGD (por ejemplo, `platform.example.com`), ni para crear los Deployment y Service secundarios. El fallo aparece como un tiempo de espera al sincronizar la caché, no como un error de permisos.

```text
ControllerReady=False FailedToStart
  ...
  cache sync timeout for platform.example.com/v1alpha1, Resource=nginxapps
```

La guía de eksctl asocia `AmazonEKSClusterAdminPolicy` para empezar. Una alternativa de mínimo privilegio es agregar un grupo de Kubernetes a la entrada de acceso y asociar un ClusterRole por cada RGD.

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

Cuando se concedieron los permisos después de crear el RGD, este pasó a `Active` solo 228 s más tarde (presumiblemente, el intervalo de reintento del controlador; no se confirmó en los registros). Un segundo RGD cuyo ClusterRole se aplicó primero pasó a `Active` de inmediato. Mantenga el RGD y su ClusterRole en la misma ruta de Git y aplique primero RBAC mediante sync waves (no se probaron las sync waves). `rbac.mode: aggregation` de OSS también combina únicamente los ClusterRoles con etiquetas en los permisos del controlador, así que requiere un trabajo similar (según el Helm Chart; no probado).

### Rendimiento del ciclo de vida y migración

| Fase (5 ejecuciones cada una) | Administrado | OSS 0.9.4 |
|---|---|---|
| Creación → `ACTIVE` | 2.49–3.73 s | 2.43–3.44 s |
| Cambio de Spec → Deployment actualizado | 0.50–0.52 s (un valor atípico de 51.6 s, causa desconocida) | 0.49–0.56 s |
| Eliminación → Deployment y Service eliminados | 1.02–3.02 s | 1.01–4.38 s |

El cambio de administrado → OSS → administrado mantuvo intactos dos RGD y cuatro instancias (se eliminó un controlador antes de instalar el otro). Para una migración sin tiempo de inactividad, siga el procedimiento de AWS para mover el lease de elección del líder (no probado), pero tenga en cuenta que la ruta y la clave de valor del Helm Chart están desactualizadas: el Helm Chart actual es `oci://registry.k8s.io/kro/charts/kro`, y la clave de la versión 0.9.4 es `config.leaderElectionNamespace`.

### Riesgo: kro se hace cargo de los CR existentes con el mismo nombre

Si ya existe en el espacio de nombres un CR con el mismo nombre que un recurso secundario, kro no lo rechaza: lo sobrescribe con server-side apply. En las pruebas, un CR Table de ACK existente recibió `kro.run/owned=true` y un valor de `spec.tableName` modificado; ACK creó una tabla nueva y la tabla original quedó sin administrar. Al eliminar la instancia, también se eliminó el CR del que se había hecho cargo. OSS 0.9.4 reprodujo el mismo comportamiento, así que este es un comportamiento de upstream.

- Agregue a los nombres de los recursos secundarios un sufijo específico del RGD (`${schema.metadata.name + "-os"}`).
- Separe los espacios de nombres administrados por kro de aquellos en los que las personas crean CR directamente.
- Establezca `services.k8s.aws/deletion-policy: retain` en los recursos de ACK que contienen datos. Esto no impide que un cambio de nombre los traslade a un recurso nuevo, por lo que la solución real es separar los nombres (no se probó `retain` en este caso).
- En clústeres multiinquilino, no permita que las instancias elijan libremente `ingressClassName` ni los nombres de host; fíjelos en el RGD o derívelos del nombre de la instancia.

<span id="ack"></span>

## 5. Capacidad de ACK

ACK administrado agrupa en una sola capacidad todos los controladores de servicios que tienen disponibilidad general upstream; los controladores en vista previa se agregan automáticamente cuando alcanzan esa disponibilidad (según la documentación). Para conocer el modelo de recursos de ACK, su adopción y retención, consulte el [capítulo sobre ACK](../platform-engineering/02-ack.md).

### IAM por equipo con IAMRoleSelector

Conceda al rol de la capacidad únicamente permiso para asumir roles de equipo y asigne los espacios de nombres a los roles mediante un `IAMRoleSelector` con alcance de clúster. El rol de cada equipo confía en el rol de la capacidad y permite `sts:AssumeRole` y `sts:TagSession`.

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

Un S3 Bucket creado en team-b cuyo rol solo permitía SQS falló con `AccessDenied`, y el mensaje indicaba el rol realmente usado (`assumed-role/ack-team-b/...`). La condición del CR `ACK.IAMRoleSelected=True` también muestra que hubo una coincidencia con un selector. Los detalles confirmaron lo siguiente:

- El controlador de S3 Bucket llama primero a `s3:ListAllMyBuckets`. Aunque se restrinjan los recursos de bucket mediante un patrón de nombres, parece que se necesita este permiso por separado (no se probó sin él).
- Los espacios de nombres sin un selector coincidente usan el rol de la capacidad (según la documentación). Sin permisos para los servicios en el rol de la capacidad, el resultado predeterminado es la denegación.
- Para lograr la misma separación con controladores OSS, establezca tanto `featureGates.IAMRoleSelector=true` como `enableCARM=false`. Con el valor predeterminado del Helm Chart `enableCARM: true`, el controlador entra en un ciclo de fallos con `cannot enable feature gate 'IAMRoleSelector' when flag 'enable-carm' is set to true`.

### Creación de recursos, etiquetas y desviaciones

| Recurso | Administrado (3 ejecuciones) | OSS (2 ejecuciones) |
|---|---|---|
| SQS Queue | 1.04–1.06 s | 1.10–1.16 s |
| S3 Bucket | 3.10–3.14 s | 3.20–3.32 s |
| DynamoDB Table | 11.28–11.53 s | 10.15–11.54 s |

Solo fue más lenta la primera creación inmediatamente después de crear la capacidad: Queue, 7.3 s; Bucket, 10.9 s; Table, 16.5 s.

ACK administrado agrega cinco etiquetas a los recursos de AWS: `eks:controller-version`, `eks:kubernetes-namespace`, `eks:kubernetes-resource-name`, `eks:kubernetes-api-group` y `eks:eks-capability-arn`. Todas las llamadas a la API de AWS llevan las etiquetas de sesión `eks:eks-capability-arn`, `eks:kubernetes-namespace` y `eks:kubernetes-api-group`. OSS agrega dos etiquetas: `services.k8s.aws/controller-version` y `services.k8s.aws/namespace`. La migración desde OSS cambia el prefijo de las etiquetas, así que actualice al mismo tiempo las etiquetas de asignación de costos y las condiciones de IAM basadas en etiquetas.

ACK no observa en tiempo real los cambios realizados en AWS. Ni la versión administrada (2 ejecuciones) ni OSS (1 ejecución) revirtieron periódicamente, en un plazo de 25 minutos, un cambio de `VisibilityTimeout` de SQS realizado fuera de ACK (con CLI). Las dos reversiones observadas en la versión administrada ocurrieron 86 s después de que la capacidad pasara por `UPDATING` debido a un cambio en la configuración de registros, y justo después de volver a crear la capacidad (horas de las llamadas obtenidas de CloudTrail). Parece que el desencadenante es un reinicio del controlador, pero no se confirmó en los registros. El intervalo de resincronización predeterminado de OSS es de 10 horas (`reconcile.defaultResyncPeriod: 36000`) y se puede ajustar; el intervalo de la versión administrada no se publica y no se puede cambiar. Si importa una recuperación rápida, evite los cambios externos mediante SCP o condiciones de IAM; por ejemplo, permita cambios en recursos etiquetados con `aws:ResourceTag/eks:eks-capability-arn` solo si proceden de llamadas con un `aws:PrincipalTag/eks:eks-capability-arn` coincidente (no probado).

### Diferencias de la versión administrada y migración

- No hay un CRD `FieldExport`. Para exportar valores de estado a un ConfigMap o Secret, use otro método, como hacer que kro escriba el estado en un ConfigMap.
- La desactivación de servicios con `--configuration '{"ack":{"disabledServices":["sagemaker"]}}'` surtió efecto en 12.5 s con CLI 2.38.3, pero los CRD de ese servicio ya instalados seguían presentes después de 350 s. En su lugar, especifique los servicios que no se utilizarán al crear la capacidad (la configuración durante la creación no se probó).
- Las versiones de los controladores estaban un paso por detrás de las últimas versiones de OSS (s3 1.12.2 frente a 1.13.1, sqs 1.7.1 frente a 1.8.2).
- Las anotaciones de adopción (`services.k8s.aws/adoption-policy: adopt-or-create`) y retención funcionan con la capacidad administrada: la adopción tardó 4.7 s y una Queue eliminada con `retain` permaneció en AWS (medido en la versión administrada). Tras eliminar la capacidad, un controlador OSS adoptó los 12 CR restantes tal como estaban.

<span id="together"></span>

## 6. Uso conjunto de las tres

La división natural es que Argo CD sincronice los manifiestos desde Git, kro combine varios recursos en una sola API y ACK cree los recursos de AWS que formen parte de ellos. El RGD `OrderService` probado creó una Queue y una Table de ACK, copió sus valores de estado (URL de la queue y ARN de la table) a un ConfigMap e inició un Deployment.

| Combinación | Resultado | Configuración adicional necesaria |
|---|---|---|
| Argo CD → ACK Queue | El CR Queue de Git quedó Synced en 6.5 s | RBAC para `queues.sqs.services.k8s.aws` en el rol de la capacidad de Argo CD |
| kro → ACK Queue y Table + ConfigMap + Deployment | Instancia `ACTIVE` en 13.2–34.3 s (principalmente por la creación de la tabla de DynamoDB) | RBAC para los recursos de ACK en el rol de la capacidad de kro; IAMRoleSelector en ACK |

Los CRD de ACK no están cubiertos por las políticas de acceso predeterminadas de EKS (como `AmazonEKSEditPolicy`), así que cualquier componente que cree recursos de ACK —Argo CD o kro— necesita permisos para esos grupos de API. Las dos mediciones se hicieron por separado; no se ejecutó de principio a fin toda la secuencia de tres pasos.

<span id="upgrade"></span>

## 7. Actualizaciones del clúster y versiones de las capacidades

### Comportamiento durante una actualización in situ

Se actualizó in situ un clúster con las tres capacidades, de 1.36 a 1.37. La actualización del plano de control tardó unos 7 minutos, y las tres capacidades permanecieron en `ACTIVE`, con su versión, estado y `modifiedAt` sin cambios.

| Fase | Autocorrección de Argo CD | Propagación de kro | Sincronización de ACK Queue |
|---|---|---|---|
| Antes (3 ejecuciones) | 2.1–14.6 s | 1.02–1.04 s | 1.49–3.53 s |
| Durante (4 ejecuciones) | 2.1 s, 6.1 s, 112.9 s, 254.5 s | 1.02–1.07 s | 1.52–1.58 s |
| Después (5 ejecuciones) | 2.3 s, luego 251–252 s | 1.01–1.15 s | 1.47–1.57 s |

En kro y ACK, una de las cuatro ejecuciones «durante» se realizó justo después de que terminara la actualización. El retraso de la autocorrección durante la actualización se reprodujo de forma idéntica después, por lo que se debió a la espera progresiva de la autocorrección descrita anteriormente, no a la actualización. No se hicieron mediciones de kro ni ACK durante los aproximadamente 3 minutos en que la versión del servidor de API alternó entre 1.36.4 y 1.37.0. No se actualizaron los grupos de nodos.

La actualización in situ no requirió pasos específicos para las capacidades. En los controladores autoadministrados hay que comprobar la compatibilidad con la nueva versión de Kubernetes y posiblemente actualizarlos primero; el modelo administrado deja esa comprobación de compatibilidad en manos de AWS. Tenga en cuenta que ninguna de las comprobaciones de información de actualización de EKS cubría las capacidades.

### No se puede elegir la versión

`create-capability` y `update-capability` no tienen un argumento de versión, y la documentación de AWS solo menciona «actualizaciones automáticas y parches de seguridad». No se encontró en la documentación un calendario de actualizaciones, aviso previo, ventana de mantenimiento, notas de la versión por versión ni procedimiento para revertir versiones de capacidades. La [reversión de la versión del clúster](./08-eks-upgrades.md) añadida en julio de 2026 revierte la versión secundaria de Kubernetes, y la documentación de reversión no contempla las capacidades. Como las capacidades no tienen un argumento de versión, no se debe considerar una forma de revertir la versión de una capacidad (inferencia). En las pruebas, una capacidad de Argo CD creada el 21 de octubre informó `3.4.6-eks-2`, y otra creada un día después en otro clúster informó `3.4.7-eks-1`. Las versiones de los controladores pueden cambiar independientemente de las actualizaciones del clúster.

Prepárese para una versión con errores de la siguiente manera.

| Preparación | Cómo | Fundamento |
|---|---|---|
| Registrar los cambios de versión | Sondee `capability.version` mediante `describe-capability` y correlaciónelo con los incidentes | Medido (campo confirmado) |
| Clúster de validación | Ejecute primero los RGD, Applications y CR de ACK de producción en un clúster con las mismas capacidades. No se puede controlar el orden del despliegue, así que no se garantiza que se actualice antes que producción | Inferencia |
| Fijar el comportamiento en Git | Mantenga en Git las comprobaciones de estado (`resource.customizations`), las opciones de sincronización y RBAC para que la recreación o migración reproduzca el mismo comportamiento | Medido (configuración aplicada) |
| AWS Support | Como no existe una reversión del lado del usuario, abra un caso. La documentación de AWS remite a Support para ajustar los tiempos de autocorrección | Inferencia (tiempos de autocorrección según la documentación) |
| Alternativa temporal autoadministrada | Al eliminar una capacidad con RETAIN se conservan los CRD y los recursos, y un controlador OSS que use los mismos CRD se hace cargo de ellos (medido para kro, ACK y Argo CD). En Argo CD fue necesario cambiar `server` en el Secret del clúster de ARN de EKS a una URL de API (`https://kubernetes.default.svc` en local); los spokes remotos o privados registrados por ARN necesitan su propia ruta de red y autenticación con OSS. Para volver al modelo administrado hay que volver a crear la capacidad (unos 6 minutos para Argo CD) | Medido |
| Reversión de ACK por servicio | Agregue solo el servicio afectado a `disabledServices` e instale o escale su controlador autoadministrado. El controlador OSS necesita su propia configuración de IAM, además de `featureGates.IAMRoleSelector=true` y `enableCARM=false` cuando se usa IAMRoleSelector. No se probó ejecutar el Helm Chart de OSS sobre CRD instalados por la capacidad. Los CRD ya instalados permanecen (medido) | Según la documentación |

Si necesita claramente fijar versiones, la propia documentación de AWS señala que se debe usar la versión autoadministrada («si se requieren versiones específicas de la API de recursos de Kubernetes o compilaciones de controladores personalizadas»).

<span id="multicluster"></span>

## 8. Multiclúster y reemplazo azul/verde

### Hub de Argo CD y spoke privado

La capacidad de Argo CD de un clúster hub registró un spoke en la misma cuenta y VPC cuyo endpoint de API era exclusivamente privado, sin configuración de red (endpoints, grupos de seguridad ni rutas). Una estación de trabajo en otra VPC no podía llegar al spoke, así que, aparentemente, la conexión usa una ruta proporcionada por AWS. El spoke necesita una entrada de acceso para el rol de la capacidad del hub, que se crea manualmente.

| Permisos de la entrada de acceso del spoke | Resultado |
|---|---|
| `AmazonEKSEditPolicy` + `AmazonEKSAdminViewPolicy` | La conexión y la autenticación funcionaron, pero `CreateNamespace=true` falló con `namespaces is forbidden`; se agotaron cinco reintentos automáticos (unos 303 s) |
| + `AmazonEKSArgoCDClusterPolicy`, luego sincronización manual | Sincronizado y Healthy en 11.1 s |

- Los Secrets de clúster solo aceptan ARN de EKS, así que los clústeres que no son de EKS no pueden ser destinos (según la documentación).
- El cargo por Application cuenta las Applications por clúster de destino, así que un hub y una distribución por clúster cuestan lo mismo; solo aumenta el cargo por capacidad con la cantidad de instancias de Argo CD. Sin embargo, el rol de la capacidad del hub tiene acceso de escritura a todos los spokes, así que considere restringir los destinos de AppProject o dividir las capacidades por equipo.
- Según la documentación, en los clústeres de otras cuentas solo se necesita una entrada de acceso para el rol de la capacidad del hub (no probado). Los límites de la versión administrada son 100 clústeres remotos y 3.000 Applications.

### Dónde ubicar kro y ACK

Las capacidades de kro y ACK solo administran su propio clúster. Para que Argo CD en un hub implemente instancias RGD o CR de ACK en un spoke, el spoke también necesita kro o ACK (administrado u OSS).

| Distribución | Adecuada cuando | Consideraciones |
|---|---|---|
| kro en cada clúster, RGD distribuidos con un ApplicationSet | Los equipos de aplicaciones usan la misma API en cada clúster | El costo de las capacidades y el trabajo de RBAC aumentan con la cantidad de clústeres; la documentación no garantiza versiones idénticas de kro en todos los clústeres (no probado) |
| kro solo en el hub; los RGD crean recursos de ACK y Applications de Argo CD para los spokes | Las abstracciones de plataforma se definen en un solo lugar | Los permisos y el radio de impacto se concentran en el hub; los equipos de aplicaciones de los spokes no pueden usar directamente la API de kro (no probado) |
| ACK centralizado (hub) | Recursos propiedad de la plataforma, como bases de datos, IAM y VPC | El rol de la capacidad del hub tiene permisos para todas las cuentas y recursos |
| ACK distribuido (por clúster) | Queues y buckets declarados junto a las cargas de trabajo | La configuración de IAMRoleSelector aumenta con la cantidad de clústeres |
| ACK híbrido | Recursos de alcance administrativo en el hub y recursos de alcance de carga de trabajo en los spokes | Necesita reglas de alcance para que ningún recurso se declare en dos lugares |

En todas las distribuciones, establezca reglas de alcance para que ningún par de clústeres declare el mismo recurso de AWS al mismo tiempo.

### Reemplazo azul/verde

- **Argo CD**: La capacidad pertenece a su clúster, así que reemplazar el clúster que aloja Argo CD implica volver a crear la capacidad. La dirección predeterminada `argocd-<ID>-<account ID>.eks-capabilities.<region>.amazonaws.com` es distinta en cada clúster, así que cambian las URL de la interfaz y del webhook. Al establecer `endpointPrefix` durante la creación, eliminar y volver a crear la capacidad con el mismo prefijo conservó la dirección (solo se probó en el mismo clúster). La dirección no contiene nada específico del clúster, así que también debería funcionar después de trasladarse a otro clúster. Si el prefijo es único dentro de una cuenta y una región (no probado), los clústeres antiguos y nuevos no pueden tenerlo al mismo tiempo; el reemplazo pasa a ser una operación de eliminación y recreación, y durante ese tiempo (100 s más 338 s medidos) se interrumpen la interfaz, los webhooks y la sincronización. Si esa pausa es inaceptable, levante primero una nueva capacidad con un prefijo nuevo y cambie la URL del webhook de Git; desactive la sincronización automática de la antigua o elimine sus Applications sin cascada antes de habilitar la nueva, y cree de antemano las entradas de acceso del nuevo rol de capacidad en los clústeres de destino (no probado). El prefijo no se puede cambiar después de la creación. Ubique Argo CD en un hub dedicado, no en clústeres de cargas de trabajo que se sustituyen con frecuencia.
- **kro**: Los ClusterRole y las vinculaciones se trasladan mediante Git, pero agregar un grupo de Kubernetes a la entrada de acceso es una llamada a la API de EKS. Inclúyalo en la IaC que crea los clústeres (eksctl, Terraform, etc.).
- **ACK**: Una secuencia posible es eliminar los CR del clúster antiguo con `deletion-policy: retain` y luego adoptar los mismos recursos en el nuevo clúster con `adoption-policy: adopt-or-create` (se midió cada paso; no se probó la secuencia completa entre clústeres). Si un SCP bloquea cambios según la etiqueta `eks:eks-capability-arn`, el ARN de la nueva capacidad será distinto y la adopción podría bloquearse; relaje la condición durante el cambio o use condiciones basadas en etiquetas de entorno o equipo.

<span id="compare"></span>

## 9. Comparación con la gestión autoadministrada y cuándo elegirla

| Elemento | Capacidad administrada | Autoadministrada (OSS) |
|---|---|---|
| Tiempo de instalación | Argo CD 349 s, kro 70 s, ACK 386 s | Argo CD 43.4 s, kro 15.6 s, tres controladores ACK 46 s |
| Recursos de los nodos | Ninguno | Argo CD: 7 Pods (339–624 MiB de memoria), kro: 1 Pod (solicitudes de 256m y 128 MiB), ACK: 3 Pods (cada uno solicita 50m y 64 MiB) |
| Versión | La elige AWS; no se puede fijar | A elección del usuario (Argo CD v3.5.5 y ACK s3 1.13.1 eran las últimas versiones al realizar las pruebas) |
| Permisos predeterminados | Limitados; se deben conceder permisos de implementación, recursos secundarios e IAM | Los valores predeterminados de los Helm Chart de Argo CD y kro son `*/*/*` |
| Rendimiento | kro, ACK y la autocorrección de Argo CD igualan a OSS; el sondeo predeterminado de Argo CD es más lento | Referencia (Argo CD 3.4.6 y kro 0.9.4 se midieron con las mismas versiones; ACK OSS usaba una versión más reciente) |
| SSO | Solo Identity Center, dos campos de configuración | Dex, OIDC y otros; se configuran por cuenta propia |
| Clústeres remotos | ARN de EKS + entrada de acceso; clústeres privados sin configurar la red | URL de API, autenticación y ruta de red por clúster |
| Funciones no disponibles | CMP, `argocd admin`, bibliotecas estándar de Lua; FieldExport de ACK (Argo CD Notifications se añadió en noviembre de 2026) | Ninguna |
| Elementos que no se pueden ajustar directamente | Sondeo de Argo CD, intervalo de resincronización de ACK, opciones del controlador y límites de recursos; la espera progresiva de autocorrección de Argo CD solo se puede cambiar mediante AWS Support | Todo se puede ajustar |
| Registros | Vended Logs | `kubectl logs`, con recopilación propia |

La versión administrada es adecuada cuando:

- Se está creando un hub que implementa en varios clústeres de EKS, especialmente clústeres privados o clústeres de otras cuentas
- El inicio de sesión en AWS ya está centralizado en Identity Center y no se quiere administrar por cuenta propia el SSO de Argo CD
- Se administran varios servicios de AWS desde Kubernetes, ejecutar un controlador ACK por servicio supone una carga y se necesita separación de IAM por equipo
- Se quiere que los permisos de los controladores de plataforma sean limitados de forma predeterminada y explícitos en las entradas de acceso y RBAC

Conviene mantener la gestión autoadministrada cuando:

- Se depende de CMP, FieldExport o las bibliotecas estándar de Lua
- Entre los destinos de implementación hay clústeres que no son de EKS
- Solo Argo CD debe usar un IdP distinto del Identity Center de la organización y no es posible usar una instancia de cuenta
- Se deben controlar por cuenta propia las versiones de los controladores, los tiempos de actualización y los intervalos de sondeo o resincronización

Un buen momento para evaluarla es antes de crecer más allá de un clúster: la ubicación del hub, la instancia de Identity Center y `endpointPrefix` se fijan al crear la capacidad o son difíciles de cambiar después. Otro momento es cuando Argo CD autoadministrado necesita reconstruirse en alta disponibilidad o someterse a una actualización importante. El procedimiento de migración de AWS escala el controlador a cero, traslada Applications y Secrets, y cambia `destination.server` por el ARN; mientras tanto, la sincronización se detiene (no probado).

<span id="pricing"></span>

## 10. Precios

Precios de Seúl (ap-northeast-2), consultados mediante la API de precios de AWS el 21 de octubre de 2026, usando 730 horas al mes.

| Capacidad | Cargo por capacidad | Cargo por objeto | Ejemplo (por mes) |
|---|---|---|---|
| Argo CD | $0.034799 por hora (unos $25.4 al mes) | $0.001726 por hora y por Application (se cuenta por clúster de destino) | 9 apps: unos $36.7; 100 apps: unos $151 |
| kro | $0.006038 por hora (unos $4.4 al mes) | $0.000061 por hora y por instancia | 100 instancias: unos $8.9 |
| ACK | $0.006038 por hora (unos $4.4 al mes) | $0.000061 por hora y por recurso | 200 recursos: unos $13.3 |

A modo de comparación, si se distribuye el costo de m7g.large (Seúl, $0.1003 por hora) entre las instalaciones autoadministradas predeterminadas, se obtienen unos $5.6 para Argo CD (624 MiB de memoria), $9.4 para kro (solicitud de 256m de CPU) y $5.5 para tres controladores ACK (solicitud de 150m de CPU). Las configuraciones de alta disponibilidad y una mayor cantidad de apps o servicios también elevan el costo de OSS. Argo CD administrado se encarece a medida que crece la cantidad de apps; para kro y ACK la diferencia es pequeña, así que la carga operativa y las limitaciones de funciones son los factores decisivos.

<span id="refs"></span>

## 11. Alcance de la verificación y referencias

Las mediciones se hicieron en una sola cuenta de ap-northeast-2: un clúster de EKS 1.36.4 y otros dos clústeres para las pruebas de actualización y multiclúster (hub de 1.36 → 1.37, spoke privado 1.37). Los escenarios se ejecutaron entre 1 y 5 veces, con un máximo de 9 apps de Argo CD, 6 instancias de kro y unos 20 recursos de ACK. ACK solo se probó con S3, SQS y DynamoDB. No se probaron los casos siguientes y se basan en la documentación: integración con Okta o Entra ID e instancias de cuenta de Identity Center, acceso privado mediante un endpoint de VPC, registro de clústeres en otras cuentas o VPC, Notifications y CMP, ACK entre cuentas, migración sin tiempo de inactividad con las versiones administrada y OSS en ejecución simultánea, y la secuencia completa entre clústeres de retención y posterior adopción de ACK. Los clústeres de prueba y los recursos de AWS se eliminaron después de las mediciones.

- [EKS Capabilities](https://docs.aws.amazon.com/eks/latest/userguide/capabilities.html)
- [Consideraciones sobre EKS Capabilities](https://docs.aws.amazon.com/eks/latest/userguide/capabilities-considerations.html)
- [Recursos de Kubernetes de las capacidades](https://docs.aws.amazon.com/eks/latest/userguide/capability-kubernetes-resources.html)
- [Consideraciones sobre Argo CD](https://docs.aws.amazon.com/eks/latest/userguide/argocd-considerations.html)
- [Comparación entre la capacidad de EKS para Argo CD y Argo CD autoadministrado](https://docs.aws.amazon.com/eks/latest/userguide/argocd-comparison.html)
- [Registrar clústeres de destino](https://docs.aws.amazon.com/eks/latest/userguide/argocd-register-clusters.html)
- [Configurar los ajustes de Argo CD](https://docs.aws.amazon.com/eks/latest/userguide/argocd-configure-settings.html)
- [Configurar los permisos de kro](https://docs.aws.amazon.com/eks/latest/userguide/kro-permissions.html)
- [Comparación entre la capacidad de EKS para kro y kro autoadministrado](https://docs.aws.amazon.com/eks/latest/userguide/kro-comparison.html)
- [Configurar los permisos de ACK](https://docs.aws.amazon.com/eks/latest/userguide/ack-permissions.html)
- [Comparación entre la capacidad de EKS para ACK y ACK autoadministrado](https://docs.aws.amazon.com/eks/latest/userguide/ack-comparison.html)
- [Acceder a los registros de los controladores de EKS Capabilities](https://docs.aws.amazon.com/eks/latest/userguide/capabilities-controller-logs.html)
- [Revertir un clúster a una versión anterior de Kubernetes](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html)
- [Precios de Amazon EKS](https://aws.amazon.com/eks/pricing/)
- Artículos sobre las mediciones (en coreano): [Argo CD administrado](https://blog.atomai.click/eks-capabilities-argocd/), [kro administrado](https://blog.atomai.click/eks-capabilities-kro/), [ACK administrado](https://blog.atomai.click/eks-capabilities-ack/)
- Manifiestos de prueba: [Atom-oh/eks-capabilities-demo](https://github.com/Atom-oh/eks-capabilities-demo)

[Cuestionario sobre EKS Capabilities](../quizzes/eks/13-eks-capabilities-quiz.md)
