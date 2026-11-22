# Migrar los permisos IAM de los nodos de EKS a IRSA y Pod Identity

> **Última actualización**: 21 de noviembre de 2026

Cuando el permiso de una aplicación para S3 está asociado al perfil de instancia de los nodos EC2 —el rol IAM del nodo—, todos los Pod de ese nodo que puedan acceder al servicio de metadatos de instancia (IMDS) obtienen el mismo permiso. Un permiso concedido a un Pod de pagos también queda disponible para el agente de envío de registros y los Jobs por lotes del nodo. CloudTrail los registra a todos como la misma sesión de instancia del nodo, por lo que no puedes saber qué carga de trabajo realizó una llamada.

Este cuaderno compara las dos formas de trasladar ese permiso a una identidad por carga de trabajo: IRSA (IAM Roles for Service Accounts) y EKS Pod Identity. Luego presenta un orden de migración para clústeres de producción y muestra una demostración en vivo en la que se migran en paralelo tres copias de la misma aplicación.

## De dónde proceden las credenciales

![Tres Pod obtienen credenciales mediante tres rutas. El Pod con el rol del nodo las obtiene de IMDSv2, el Pod con IRSA de STS AssumeRoleWithWebIdentity y el Pod con Pod Identity a través del Pod Identity Agent de su nodo y EKS Auth. Cada Pod firma su solicitud a S3 con las credenciales que recibió.](../.gitbook/assets/en-security-17-eks-workload-identity-migration-anim-0.svg)

Los SDK de AWS y la CLI de AWS dentro de un Pod recorren la [cadena predeterminada de proveedores de credenciales](https://docs.aws.amazon.com/sdkref/latest/guide/standardized-credentials.html) de principio a fin. Las claves estáticas en las variables de entorno, el token de identidad web (IRSA) y el proveedor de credenciales del contenedor (Pod Identity) se procesan antes que IMDS. Por lo tanto, un Pod nuevo al que EKS haya inyectado las variables de IRSA o Pod Identity usa el nuevo rol sin cambios en el código. Un Pod al que no se le haya inyectado nada continúa hasta el último paso, IMDS, y recibe el rol del nodo.

| Ruta | Qué se inyecta en el Pod | Llamadas del SDK | Rol resultante |
| --- | --- | --- | --- |
| Perfil de instancia del nodo | Nada | IMDSv2 `169.254.169.254` | Rol IAM del nodo (compartido por todos los Pod del nodo) |
| IRSA | `AWS_ROLE_ARN`, `AWS_WEB_IDENTITY_TOKEN_FILE`, volumen de token | STS regional (Security Token Service) `AssumeRoleWithWebIdentity` | Rol indicado en la anotación de ServiceAccount |
| EKS Pod Identity | `AWS_CONTAINER_CREDENTIALS_FULL_URI`, `AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE`, volumen de token | Pod Identity Agent del mismo nodo, `169.254.170.23` | Rol de la asociación |

**Quién inyecta las variables y cuándo.** Cuando se crea un Pod, el servidor de API autentica y autoriza la solicitud y, durante la admisión mutante, llama al webhook `iam-for-pods.amazonaws.com` (amazon-eks-pod-identity-webhook). EKS ejecuta este webhook dentro del plano de control, por lo que no hay ningún Pod de webhook en tus nodos. El webhook examina el ServiceAccount del Pod: si hay una asociación, añade las variables de Pod Identity y el volumen de token; si solo hay una anotación de IRSA, añade las variables de IRSA y el volumen de token; y, si hay ambas, añade únicamente las variables de Pod Identity. A continuación, kubelet solicita el token proyectado para esa audiencia y lo monta. El `MutatingWebhookConfiguration` del clúster de demostración tiene una única regla, `CREATE pods`, y `failurePolicy: Ignore`. Por eso los Pod en ejecución no cambian hasta que se realiza un despliegue y, si el webhook no responde, el Pod se crea sin las variables y utiliza silenciosamente el rol del nodo. Comprueba el resultado mediante el ARN del llamante y, antes de crear Pod, usa `kubectl create --dry-run=server` para ver la especificación del Pod después de que actúe el webhook.

Con un límite de saltos de respuesta de IMDS de 2 o más, un Pod común sin red de host puede obtener un token de IMDSv2 y las credenciales del rol del nodo. Las plantillas de lanzamiento de grupos de nodos administrados suelen establecer este valor en 2. Por eso, el último paso de la migración reduce el límite de saltos a 1.

<a id="irsa-flow"></a>
## Cómo funciona IRSA

![Flujo de IRSA. Un webhook detecta la anotación de ServiceAccount e inyecta variables de entorno y un token proyectado (aud sts.amazonaws.com). El SDK envía el token a STS AssumeRoleWithWebIdentity; STS verifica la firma mediante el proveedor OIDC de IAM, comprueba aud y sub en la política de confianza y devuelve credenciales temporales.](../.gitbook/assets/en-security-17-eks-workload-identity-migration-anim-1.svg)

1. **Configuración de confianza.** Cada clúster tiene una URL de emisor OIDC (OpenID Connect). Registra ese emisor una sola vez como proveedor OIDC de IAM en la cuenta. La política de confianza del rol especifica el proveedor como principal `Federated` y establece condiciones para `aud` (`sts.amazonaws.com`) y `sub` (`system:serviceaccount:<namespace>:<serviceaccount>`).
2. **Inyección al crear el Pod.** Cuando el ServiceAccount incluye `eks.amazonaws.com/role-arn`, un webhook mutante de EKS añade `AWS_ROLE_ARN`, `AWS_WEB_IDENTITY_TOKEN_FILE` y un volumen con un token proyectado en `/var/run/secrets/eks.amazonaws.com/serviceaccount/token` a cada Pod nuevo. Los Pod en ejecución no cambian, por lo que se requiere un despliegue.
3. **Emisión y renovación del token.** kubelet solicita un token de ServiceAccount para la audiencia `sts.amazonaws.com`, lo escribe en el archivo y lo renueva antes de que caduque.
4. **Intercambio del token.** El SDK envía el token a STS regional `AssumeRoleWithWebIdentity`. STS verifica su firma con las claves del emisor registradas mediante el proveedor OIDC de IAM, comprueba las condiciones `aud` y `sub` y devuelve credenciales temporales. El Pod se comunica directamente con STS, por lo que necesita una ruta de red a STS. [Documentación de AWS sobre IRSA](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)

<a id="pod-identity-flow"></a>
## Cómo funciona EKS Pod Identity

![Flujo de Pod Identity. Una asociación en la API de EKS asigna el ServiceAccount a un rol, y EKS inyecta variables de credenciales del contenedor y un token proyectado (aud pods.eks.amazonaws.com). El SDK llama al Pod Identity Agent de su nodo; el Agent usa el permiso eks-auth del rol del nodo para llamar a EKS Auth AssumeRoleForPodIdentity, y EKS devuelve credenciales para el rol con etiquetas de sesión.](../.gitbook/assets/en-security-17-eks-workload-identity-migration-anim-2.svg)

1. **Configuración del Agent.** Instala el complemento `eks-pod-identity-agent` una vez por clúster. El Agent es un DaemonSet en la red de host del nodo que utiliza los puertos 80 y 2703 en la dirección de enlace local `169.254.170.23` (IPv6 `[fd00:ec2::23]`). EKS Auto Mode lo incluye de forma integrada.
2. **Rol y asociación.** El rol confía en la entidad de servicio `pods.eks.amazonaws.com` para `sts:AssumeRole` y `sts:TagSession`. No hay un proveedor por clúster, por lo que el mismo rol funciona en otro clúster sin cambios en la política de confianza. La vinculación es una asociación en la API de EKS (clúster, espacio de nombres, ServiceAccount → rol); no se anota ningún objeto de Kubernetes.
3. **Inyección al crear el Pod.** Para un ServiceAccount con una asociación, EKS inyecta en los Pod nuevos `AWS_CONTAINER_CREDENTIALS_FULL_URI=http://169.254.170.23/v1/credentials`, `AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE` y un token proyectado para la audiencia `pods.eks.amazonaws.com`.
4. **Búsqueda de credenciales.** El SDK envía el token al Agent de su nodo. El Agent llama a EKS Auth con el permiso `eks-auth:AssumeRoleForPodIdentity` del rol del nodo (incluido en `AmazonEKSWorkerNodePolicy`). EKS Auth valida el token y la asociación, asume el rol y devuelve credenciales con etiquetas de sesión como `eks-cluster-arn`, `kubernetes-namespace` y `kubernetes-service-account`. El rol del nodo conserva únicamente el permiso que necesita el Agent para llamar a EKS Auth; el permiso de negocio de la aplicación reside en el rol de Pod Identity. [Cómo funciona Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/pod-id-how-it-works.html)

## Comparación entre IRSA y Pod Identity

AWS recomienda EKS Pod Identity siempre que sea posible. IRSA sigue siendo adecuado para algunos entornos de ejecución y estructuras de equipo. [Comparación de AWS](https://docs.aws.amazon.com/eks/latest/userguide/service-accounts.html)

| Atributo | IRSA | EKS Pod Identity |
| --- | --- | --- |
| Configuración por clúster | Registrar un proveedor OIDC de IAM para cada clúster | Complemento Pod Identity Agent para cada clúster (integrado en Auto Mode) |
| Dónde reside la vinculación | Anotación de Kubernetes ServiceAccount | Asociación de la API de EKS (sin cambios en los objetos de Kubernetes) |
| Política de confianza | Proveedor OIDC `Federated` con condiciones `aud`/`sub`; una declaración adicional por clúster | Un principal, `pods.eks.amazonaws.com`; no cambia al añadir clústeres |
| Límites de escala | 100 proveedores OIDC por cuenta de forma predeterminada; la política de confianza predeterminada de 2.048 caracteres suele admitir unas cuatro vinculaciones por rol | 5.000 asociaciones por clúster; la política de confianza del rol no aumenta |
| Ruta de credenciales | Pod → STS regional (el Pod consume cuota de la API de STS) | Pod → Agent del nodo → EKS Auth (el Pod no llama a STS) |
| Información de sesión | Nombre de sesión del rol; sin etiquetas de sesión | Las etiquetas de sesión de clúster, espacio de nombres y ServiceAccount permiten ABAC (control de acceso basado en atributos) |
| Entornos de ejecución | EKS en EC2 y Fargate, EKS Anywhere, ROSA, Kubernetes autoadministrado en EC2 | Nodos Linux de EC2 en EKS y EKS Hybrid Nodes (requiere el DaemonSet híbrido del Agent y el archivo de credenciales del nodo); no es compatible con Fargate, Windows, Outposts ni EKS Anywhere |
| Entre cuentas | El rol de la cuenta de destino confía en el proveedor OIDC de este clúster | El rol de la asociación está en la cuenta del clúster; se delega mediante un rol de destino o encadenamiento de roles |
| Separación de funciones | Los administradores de IAM crean el proveedor OIDC; los operadores del clúster añaden anotaciones | IAM solo administra los roles; las vinculaciones residen en la API de EKS |

En resumen, Pod Identity es más sencillo y escala mejor para nuevas cargas de trabajo de EKS en EC2. Usa IRSA para los nodos de Fargate o Windows, o cuando la misma configuración también deba ejecutarse en Kubernetes fuera de EKS. Ambas opciones pueden ejecutarse en un mismo clúster. Cuando un ServiceAccount tiene tanto una anotación de IRSA como una asociación, el webhook de EKS inyecta únicamente las variables de Pod Identity en los Pod nuevos, no las de IRSA. En el clúster de demostración, una comprobación con `kubectl create --dry-run=server` devolvió `AWS_ROLE_ARN` y `AWS_WEB_IDENTITY_TOKEN_FILE` cuando solo estaba la anotación, y únicamente `AWS_CONTAINER_CREDENTIALS_FULL_URI` y `AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE` después de añadir la asociación. Los Pod en ejecución conservan sus variables de IRSA hasta que se vuelven a crear, así que cambia de método mediante un despliegue y elimina la anotación que ya no se usa.

Ambas opciones funcionan en EKS Hybrid Nodes. IRSA solo necesita una ruta desde el Pod hasta STS. Por lo general, el Pod Identity Agent obtiene sus credenciales del IMDS del nodo, que no está disponible en los nodos híbridos; por eso, establece `spec.hybrid.enableCredentialsFile: true` en la configuración `nodeadm` del nodo para crear `/eks-hybrid/.aws/credentials`, y habilita `daemonsets.hybrid.create` en la configuración del complemento del Agent (v1.3.3-eksbuild.1 o posterior). Bottlerocket requiere el complemento v1.3.7-eksbuild.2 o posterior, el sistema operativo 1.39.0 o posterior y `daemonsets.hybrid-bottlerocket.create`. [Configurar complementos para nodos híbridos](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-add-ons.html) · [Arranque del nodo](../eks-hybrid-nodes/04-node-bootstrap.md)

En clústeres privados, asegúrate de que haya una ruta a STS regional para los Pod con IRSA y a EKS Auth (`eks-auth`) para el Pod Identity Agent. Si no hay una ruta a Internet, comprueba los puntos de enlace de interfaz de VPC correspondientes, el DNS y los grupos de seguridad. Si hay un proxy, añade `169.254.170.23` y `[fd00:ec2::23]` a `NO_PROXY`. [Consideraciones sobre Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html) · [Requisitos para clústeres privados](https://docs.aws.amazon.com/eks/latest/userguide/private-clusters.html)

## Orden de migración para clústeres de producción

1. **Inventariar las dependencias.** Compara las políticas del rol del nodo con las sesiones de IAM que CloudTrail registra realmente y enumera las API de AWS a las que llaman los Deployment, StatefulSet, DaemonSet, CronJob y controladores. Para ver el acceso a objetos de S3 en CloudTrail, se requieren eventos de datos en el bucket. Conserva `AmazonEKSWorkerNodePolicy` para el registro de nodos y el Pod Identity Agent, y `AmazonEC2ContainerRegistryPullOnly` (o su equivalente) para extraer imágenes de Amazon ECR (Elastic Container Registry). La política `AmazonEKS_CNI_Policy` de VPC CNI (Container Network Interface) puede trasladarse a un rol dedicado de `aws-node`; antes de eliminarla del rol del nodo, verifica las credenciales de CNI y la asignación de direcciones IP a los Pod nuevos. [Rol IAM de nodo de EKS](https://docs.aws.amazon.com/eks/latest/userguide/create-node-role.html) · [Eventos de S3 en CloudTrail](https://docs.aws.amazon.com/AmazonS3/latest/userguide/cloudtrail-logging-s3-info.html)
2. **Crear un rol IAM con permisos específicos y un ServiceAccount dedicado para cada carga de trabajo.** Para IRSA, registra el emisor del clúster como proveedor OIDC de IAM, crea un rol que compruebe la audiencia y el asunto exactos, y anota el ServiceAccount con `eks.amazonaws.com/role-arn`. Para Pod Identity, comprueba que el Agent esté listo y que el nodo tenga el permiso de EKS Auth; luego crea la asociación con un rol cuyo alcance se limite mediante etiquetas de solicitud. Confirma la compatibilidad del entorno de ejecución y del SDK. [Versiones de SDK para IRSA](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts-minimum-sdk.html) · [Versiones de SDK para Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/pod-id-minimum-sdk.html)
3. **Crear Pod canario.** Cambia `serviceAccountName` en la plantilla del Pod o despliega Pod nuevos; luego comprueba los nombres de las variables inyectadas, el ARN del llamante del proceso en ejecución y las API de AWS que necesita. No registres nunca tokens ni claves. Las credenciales explícitas o un proveedor anterior de la cadena predeterminada pueden tener prioridad. [Cadena predeterminada de proveedores de credenciales](https://docs.aws.amazon.com/sdkref/latest/guide/standardized-credentials.html)
4. **Cambiar las cargas de trabajo una a una.** Supervisa las tasas de error, `AccessDenied`, la renovación de tokens y credenciales, y las ejecuciones programadas. Cuando una carga de trabajo ya no dependa del permiso de negocio del rol del nodo, elimina únicamente esa declaración de política. Conserva la plantilla anterior del Pod y una copia exacta de la política del nodo durante el período de reversión. Para volver atrás después de eliminar el permiso, restaura primero esa política mínima, confirma que los cambios se hayan propagado y, luego, despliega los Pod anteriores.
5. **Restringir el acceso a las credenciales del nodo.** Empieza por los grupos de nodos cuya compatibilidad hayas probado, aplica IMDSv2 y restringe el acceso de los Pod comunes a IMDS. En un grupo de nodos administrado con una plantilla de lanzamiento personalizada, establece `HttpTokens=required` y `HttpPutResponseHopLimit=1` en una nueva versión de la plantilla y renueva los nodos. Karpenter usa `EC2NodeClass.spec.metadataOptions`; EKS Auto Mode aplica IMDSv2 y un límite de saltos de 1 de forma predeterminada. Los Pod con `hostNetwork` pueden acceder a IMDS independientemente del límite de saltos, así que contrólalos por separado. No desactives IMDS (`HttpEndpoint=disabled`): el propio Pod Identity Agent se ejecuta en la red de host y obtiene del IMDS las credenciales del rol del nodo para llamar a EKS Auth. [Plantillas de lanzamiento de grupos de nodos administrados](https://docs.aws.amazon.com/eks/latest/userguide/launch-templates.html) · [Prácticas recomendadas de IAM para EKS](https://docs.aws.amazon.com/eks/latest/best-practices/identity-and-access-management.html)

<details>
<summary>Políticas de confianza y comandos para canarios</summary>

La política de confianza del rol de IRSA limita el acceso al emisor del clúster y al ServiceAccount. Para `<OIDC_ISSUER>`, usa el emisor sin `https://`.

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Federated": "arn:aws:iam::<ACCOUNT_ID>:oidc-provider/<OIDC_ISSUER>"},
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {"StringEquals": {
      "<OIDC_ISSUER>:aud": "sts.amazonaws.com",
      "<OIDC_ISSUER>:sub": "system:serviceaccount:<NAMESPACE>:<IRSA_SA>"
    }}
  }]
}
```

El rol de Pod Identity confía en la entidad de servicio de EKS. Estas condiciones limitan el clúster, el espacio de nombres y el ServiceAccount mediante etiquetas de sesión; por eso, mantén habilitadas las etiquetas de sesión en la asociación.

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "pods.eks.amazonaws.com"},
    "Action": ["sts:AssumeRole", "sts:TagSession"],
    "Condition": {"StringEquals": {
      "aws:RequestTag/eks-cluster-arn": "<CLUSTER_ARN>",
      "aws:RequestTag/kubernetes-namespace": "<NAMESPACE>",
      "aws:RequestTag/kubernetes-service-account": "<POD_IDENTITY_SA>"
    }}
  }]
}
```

```bash
# If you chose IRSA
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" annotate sa "$IRSA_SA" \
  "eks.amazonaws.com/role-arn=$IRSA_ROLE_ARN"

# If you chose Pod Identity and the Agent is ready
aws eks create-pod-identity-association --region "$AWS_REGION" --cluster-name "$CLUSTER" \
  --namespace "$NAMESPACE" --service-account "$POD_IDENTITY_SA" --role-arn "$POD_IDENTITY_ROLE_ARN"

# Roll out the canary with the ServiceAccount chosen above
SA="$IRSA_SA"   # or "$POD_IDENTITY_SA"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" set serviceaccount \
  deployment "$CANARY_DEPLOYMENT" "$SA"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" rollout status \
  "deployment/$CANARY_DEPLOYMENT" --timeout=5m
```

</details>

<a id="live-demo"></a>
## Demostración en vivo: migración de tres copias de una aplicación

![Flujo de la demostración. Al principio, las tres copias de la aplicación de pedidos obtienen el rol del nodo de IMDS y leen de S3. Después de migrate-irsa, una copia obtiene el rol de IRSA de STS; después de migrate-podid, otra obtiene el rol de Pod Identity a través del Agent. Después de que revoke elimina el permiso de S3 del rol del nodo, solo se deniega el acceso a la copia heredada.](../.gitbook/assets/en-security-17-eks-workload-identity-migration-anim-3.svg)

La demostración añade un grupo de nodos administrado dedicado (t3.medium, subredes privadas, con taint) a un clúster de EKS 1.36 existente y ejecuta en él tres copias de la misma aplicación de pedidos. Cada 3 segundos, cada copia llama a STS `GetCallerIdentity` y a S3 `GetObject`, e imprime una línea JSON con el origen de las credenciales, el nombre del rol y el resultado de S3. El punto de partida coincide con el grupo de nodos de producción del clúster: IMDSv2 obligatorio con un límite de saltos de 2, y el rol del nodo tiene el permiso `s3:GetObject` de la aplicación. El Pod heredado es un Pod común, sin red de host. [Código de la demostración y guía de ejecución para el presentador](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/security/eks-workload-identity) · [Diapositivas (en coreano)](https://presentation.atomai.click/eks-workload-identity/)

```bash
cd examples/security/eks-workload-identity
export AWS_REGION=ap-northeast-2
export CLUSTER=<cluster name> VPC_NAME=<Name tag of the cluster VPC> \
  SUBNET_NAMES=<private subnet Name tag 1>,<private subnet Name tag 2>
./demo.sh up d1124            # before the talk: node group, roles, bucket, three copies
./demo.sh watch d1124         # second terminal: live table
./demo.sh migrate-irsa d1124  # ServiceAccount annotation + rollout
./demo.sh migrate-podid d1124 # association + injection check + rollout
./demo.sh diff d1124          # compare injected variables, tokens, trust policies
./demo.sh revoke d1124        # remove the S3 permission from the node role
./demo.sh harden d1124        # (optional, ~15 min) roll the nodes to hop limit 1
./demo.sh restore d1124       # back to the start (rehearse again)
./demo.sh down d1124          # clean up
```

Con `page-up` puedes compartir con el público una página en vivo de solo lectura. La ruta es CloudFront → origen de VPC → ALB interno → Pod del panel, y el grupo de seguridad del ALB solo admite el origen de VPC de CloudFront. El Pod del panel no tiene ningún rol IAM, solo un Role que lee los Pod y los registros de este espacio de nombres; y, como el nodo de demostración usa un límite de saltos de 2, una NetworkPolicy impide que llegue a IMDS o al Pod Identity Agent. Este aislamiento requiere la aplicación de políticas de red de VPC CNI (`enableNetworkPolicy`), que `page-up` comprueba primero.

Todo lo que crea el script lleva el ID de ejecución en su nombre o una etiqueta `LabRun`, y el script solo modifica o elimina recursos que coinciden con ese nombre o esa etiqueta. No crea ninguna VPC, subred, complemento ni proveedor OIDC y solo comprueba que existan; el único grupo de seguridad procede de `page-up`, para el ALB interno. El [laboratorio práctico](../labs/security/17-eks-workload-identity-migration-lab.md) explica cada paso con comandos, resultados esperados y puntos de comprobación.

### Mediciones en la región de Seúl

Hicimos dos ensayos el 21 de noviembre de 2026 en un clúster de EKS 1.36 en `ap-northeast-2`, con AWS CLI 2.35.11 dentro de los Pod. La inyección de Pod Identity falló en el primer ensayo (véase más abajo), así que se corrigió el script; la tabla muestra el segundo ensayo, ejecutado de principio a fin con el script corregido. Solo `harden` corresponde al primer ensayo.

| Paso | orders-legacy | orders-irsa | orders-podid | Tiempo |
| --- | --- | --- | --- | --- |
| Inicio | IMDS · rol del nodo · lectura permitida | IMDS · rol del nodo · lectura permitida | IMDS · rol del nodo · lectura permitida | — |
| `migrate-irsa` | Sin cambios | STS · rol de IRSA · lectura permitida | Sin cambios | 6 s |
| `migrate-podid` | Sin cambios | Sin cambios | Agent · rol de Pod Identity · lectura permitida | 11 s (incluye 5 s hasta que la inyección fue visible después de crear la asociación) |
| `revoke` | Rol del nodo · **lectura denegada** | Lectura permitida | Lectura permitida | Denegada después de 13 s |
| `harden` (opcional, primer ensayo) | **Sin credenciales** (respuesta de IMDS bloqueada) | Lectura permitida | Lectura permitida | Renovación de nodos: 878 s |

`diff` muestra en qué se diferencian. Ambos tokens son tokens de ServiceAccount firmados por el mismo emisor del clúster, pero difieren la audiencia y el receptor.

| Comparación | Pod con IRSA | Pod con Pod Identity |
| --- | --- | --- |
| Variables inyectadas | `AWS_ROLE_ARN`, `AWS_WEB_IDENTITY_TOKEN_FILE`, `AWS_STS_REGIONAL_ENDPOINTS` | `AWS_CONTAINER_CREDENTIALS_FULL_URI`, `AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE`, `AWS_STS_REGIONAL_ENDPOINTS` |
| `aud` del token | `sts.amazonaws.com` | `pods.eks.amazonaws.com` |
| `sub` del token | `system:serviceaccount:wid-d1124:orders-irsa` | `system:serviceaccount:wid-d1124:orders-podid` |
| Duración del token | 86.400 s (24 h) | Unas 22–24 h (el webhook añade variación aleatoria; se midieron 79.636 s y 86.171 s) |
| Principal de confianza del rol | `Federated`: proveedor OIDC del clúster, condiciones `aud` y `sub` | `Service`: `pods.eks.amazonaws.com`, tres condiciones de etiquetas de solicitud |

Los ensayos revelaron dos efectos de consistencia eventual. Primero, en el primer ensayo, un Pod que se desplegó justo después de crear la asociación no tenía variables de Pod Identity y siguió usando el rol del nodo, por lo que también se le denegó el acceso al eliminar la política del nodo. Por eso, `migrate-podid` envía la plantilla del Pod del Deployment mediante `kubectl create --dry-run=server` para ver qué inyectan los webhooks mutantes, y solo después realiza el despliegue. En el segundo ensayo, la inyección se hizo visible 5 segundos después de crear la asociación. Segundo, tras ejecutar `revoke` en el primer ensayo, se denegó el acceso al Pod heredado en 13 segundos, pero unos 4,5 minutos después aparecieron otras dos lecturas permitidas; las 11 lecturas del minuto comprobadas inmediatamente después se denegaron. En producción, sigue supervisando durante varios minutos después de eliminar una política del nodo antes de sacar conclusiones.

## Solución de problemas

- **Aparece el rol del nodo.** Comprueba que el Pod sea nuevo, haga referencia al ServiceAccount correcto y tenga la anotación de IRSA o una asociación exacta. Revisa la versión del SDK, la cadena predeterminada de proveedores y los nombres de las variables inyectadas.
- **Falla el intercambio del token de IRSA.** Comprueba el proveedor de IAM correspondiente al emisor del token, las condiciones de confianza `aud`/`sub` y la conectividad con STS.
- **Falla la búsqueda de credenciales de Pod Identity.** Comprueba el Agent de ese nodo, la conectividad con EKS Auth, los permisos de IAM del nodo, la propagación de la asociación y las condiciones de confianza del rol basadas en etiquetas de solicitud. Una asociación puede tardar varios segundos en surtir efecto después de crearla.
- **S3 deniega el acceso al rol esperado.** La identidad y el acceso a los recursos son aspectos distintos. Comprueba el ARN del objeto, la política del bucket, las SCP (Service Control Policies), los límites de permisos y las políticas de los puntos de enlace de VPC. Para objetos cifrados con una clave de AWS KMS (Key Management Service) (SSE-KMS), comprueba también los permisos de la clave.
