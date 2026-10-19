# Prácticas recomendadas de seguridad de EKS

> **Base de la revisión**: Documentación vigente de AWS, esquemas de API de Kubernetes 1.35 y Terraform 1.15.7 con el proveedor de AWS 6.64.0. No se realizó ningún despliegue en un clúster real.
> **Última actualización**: 15 de octubre de 2026

Este documento presenta las prácticas recomendadas para proteger los entornos de Amazon EKS, desde la integración con IAM hasta la seguridad de red y la protección durante la ejecución de las aplicaciones.

## Índice

1. [IRSA (IAM Roles for Service Accounts)](#irsa-iam-roles-for-service-accounts)
2. [EKS Pod Identity](#eks-pod-identity)
3. [Security Groups para Pods](#security-groups-for-pods)
4. [VPC Endpoints](#vpc-endpoints)
5. [Registro del plano de control](#control-plane-logging)
6. [Protección de EKS de GuardDuty](#guardduty-eks-protection)
7. [Amazon Inspector](#amazon-inspector)
8. [Benchmark CIS de Kubernetes](#cis-kubernetes-benchmark)
9. [Cifrado del clúster](#cluster-encryption)
10. [Seguridad de nodos](#node-security)
11. [Clústeres privados](#private-clusters)
12. [Patrones para varios inquilinos](#multi-tenancy-patterns)
13. [Seguridad perimetral y rutas de inspección](#perimeter-security-and-inspection-paths)

---

## IRSA (IAM Roles for Service Accounts)

### Descripción general de IRSA

IRSA (IAM Roles for Service Accounts) asocia roles de IAM con ServiceAccounts de Kubernetes, lo que permite que los Pods accedan de forma segura a servicios de AWS.

El servidor de API de Kubernetes emite el token proyectado de la ServiceAccount. El SDK lo intercambia por credenciales mediante STS AssumeRoleWithWebIdentity. STS valida el emisor y las claves JWKS asociados al proveedor OIDC de IAM, junto con las condiciones de confianza del rol, y devuelve credenciales temporales. El objeto de proveedor OIDC de IAM no es un proxy en ejecución que emita tokens.


### Configuración de IRSA

El siguiente ejemplo de administración no se ha ejecutado. Adapte la región, el clúster, el propietario y la ruta del bucket, y el ARN de la política a los valores reales. Sustituya la imagen de la aplicación por una versión o un digest revisados. No utilice un emisor OIDC de otra región ni dé por supuesto el ARN del rol que genera eksctl.



```bash
# 1. Create OIDC Provider (once per cluster)
eksctl utils associate-iam-oidc-provider \
    --cluster my-cluster \
    --approve

# 2. Create IAM policy
cat <<'EOF' > s3-policy.json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket"
      ],
      "Resource": "arn:aws:s3:::replace-with-owned-bucket",
      "Condition": {
        "StringEquals": {
          "aws:ResourceAccount": "123456789012"
        },
        "StringLike": {
          "s3:prefix": [
            "app-data",
            "app-data/*"
          ]
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject"
      ],
      "Resource": "arn:aws:s3:::replace-with-owned-bucket/app-data/*",
      "Condition": {
        "StringEquals": {
          "aws:ResourceAccount": "123456789012"
        }
      }
    }
  ]
}
EOF

aws iam create-policy \
    --policy-name S3ReadPolicy \
    --policy-document file://s3-policy.json

# 3. Create IAM ServiceAccount
eksctl create iamserviceaccount \
    --name s3-reader-sa \
    --namespace production \
    --cluster my-cluster \
    --attach-policy-arn arn:aws:iam::123456789012:policy/S3ReadPolicy \
    --approve
```

### Uso de IRSA

```yaml
# Reuse the ServiceAccount created by eksctl; do not guess its generated role ARN.
# Use ServiceAccount in Pod
apiVersion: v1
kind: Pod
metadata:
  name: s3-reader
  namespace: production
spec:
  serviceAccountName: s3-reader-sa
  containers:
  - name: app
    image: public.ecr.aws/aws-cli/aws-cli:replace-with-reviewed-version
    command: ["aws", "s3", "ls", "s3://replace-with-owned-bucket/app-data/"]
    # AWS SDK automatically uses IRSA token
```

### Política de confianza de IRSA

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Federated": "arn:aws:iam::123456789012:oidc-provider/oidc.eks.us-east-1.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE"
            },
            "Action": "sts:AssumeRoleWithWebIdentity",
            "Condition": {
                "StringEquals": {
                    "oidc.eks.us-east-1.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE:sub": "system:serviceaccount:production:s3-reader-sa",
                    "oidc.eks.us-east-1.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE:aud": "sts.amazonaws.com"
                }
            }
        }
    ]
}
```

### Prácticas recomendadas de IRSA

```yaml
# 1. Principle of least privilege
# Grant only minimum required permissions to each ServiceAccount

# 2. Separate ServiceAccounts per namespace
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: dynamodb-reader
  namespace: orders-service
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/orders-dynamodb-role
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: s3-uploader
  namespace: media-service
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/media-s3-role
```

---

## EKS Pod Identity

### Descripción general de Pod Identity

EKS Pod Identity ofrece otra forma de entregar credenciales. Elija entre este mecanismo e IRSA según la compatibilidad de la plataforma y del SDK, los límites de confianza y los requisitos operativos. Pod Identity no sustituye a IRSA ni hace automáticamente más segura cada carga de trabajo.

El SDK compatible del Pod accede a las credenciales a través del agente local. Este obtiene credenciales temporales mediante EKS Auth, según la asociación y el rol configurados. Para los roles entre cuentas o el encadenamiento de roles, compruebe por separado el mecanismo admitido, la confianza y las condiciones de las etiquetas de sesión.


### Configuración de Pod Identity

EKS Auto Mode incluye el agente. En las demás plataformas admitidas, seleccione una versión compatible del complemento y adminístrela mediante el responsable o la herramienta que ya gestiona ese recurso. Sustituya los valores de cuenta, clúster, namespace y ServiceAccount del ejemplo. Restrinja la confianza del rol mediante las condiciones de etiquetas de sesión correspondientes al namespace y la ServiceAccount previstos. Instalar el complemento y crear la asociación no demuestra que el SDK sea compatible, que se elijan las credenciales correctas ni que exista acceso de red.



```bash
# 1. Install Pod Identity Agent addon
aws eks create-addon \
    --cluster-name my-cluster \
    --addon-name eks-pod-identity-agent

# 2. Create IAM role (with Pod Identity trust policy)
cat <<'EOF' > trust-policy.json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "pods.eks.amazonaws.com"
      },
      "Action": [
        "sts:AssumeRole",
        "sts:TagSession"
      ],
      "Condition": {
        "StringEquals": {
          "aws:RequestTag/kubernetes-namespace": "production",
          "aws:RequestTag/kubernetes-service-account": "my-app-sa"
        }
      }
    }
  ]
}
EOF

aws iam create-role \
    --role-name my-pod-role \
    --assume-role-policy-document file://trust-policy.json

# 3. Attach policy
aws iam attach-role-policy \
    --role-name my-pod-role \
    --policy-arn arn:aws:iam::123456789012:policy/S3ReadPolicy

# 4. Create Pod Identity Association
aws eks create-pod-identity-association \
    --cluster-name my-cluster \
    --namespace production \
    --service-account my-app-sa \
    --role-arn arn:aws:iam::123456789012:role/my-pod-role
```

### Uso de Pod Identity

```yaml
# ServiceAccount (no annotation needed)
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-app-sa
  namespace: production
---
# Pod
apiVersion: v1
kind: Pod
metadata:
  name: my-app
  namespace: production
spec:
  serviceAccountName: my-app-sa
  containers:
  - name: app
    image: myapp:latest
    # AWS SDK automatically uses Pod Identity
```

### Comparación de IRSA y Pod Identity

| Característica | IRSA | EKS Pod Identity |
|---------|------|------------------|
| **Complejidad de configuración** | Requiere un proveedor OIDC | Sencilla: una llamada a la API |
| **Política de confianza** | Emisor OIDC, audiencia y sujeto exactos | Principal de servicio con condiciones que restringen su uso |
| **Reutilización de roles** | Requiere ajustes para cada clúster | Permite reutilizarlos entre clústeres |
| **Registro de auditoría** | CloudTrail, a nivel de ServiceAccount | CloudTrail, a nivel de Pod |
| **Etiquetas de sesión** | No presuponga el mismo comportamiento que en EKS Pod Identity | Admite las etiquetas documentadas; revise su desactivación y el encadenamiento de roles |
| **Selección** | Plataforma compatible, confianza OIDC y modelo operativo | Plataforma compatible, asociación y modelo de agente y SDK |

---

## Security Groups para Pods {#security-groups-for-pods}

### Descripción general

Security Groups para Pods aplica grupos de seguridad de VPC directamente a los Pods y permite aislarlos a nivel de red.

### Requisitos previos

```bash
# Inspect the installed CNI and verify current platform/version requirements
kubectl describe daemonset aws-node -n kube-system | grep Image

# Enable Security Groups for Pods
kubectl set env daemonset aws-node -n kube-system ENABLE_POD_ENI=true

# Attach to the EKS CLUSTER role, after resolving its actual name
aws iam attach-role-policy \
    --role-name "$EKS_CLUSTER_ROLE_NAME" \
    --policy-arn arn:aws:iam::aws:policy/AmazonEKSVPCResourceController
```

Security Groups para Pods requiere una instancia que admita interfaces de tipo trunk y un modo de CNI compatible. La documentación vigente excluye Windows y EKS Auto Mode; no todas las instancias Nitro son compatibles. La política de VPC Resource Controller debe asociarse al rol del clúster. Cuando se asocian varios grupos de seguridad, se suman las reglas que permiten tráfico, en lugar de exigir que todos lo permitan. Antes de habilitar esta función, revise el modo strict o standard, DNS, las sondas y el comportamiento del balanceador de carga.

### Configuración de SecurityGroupPolicy

```yaml
apiVersion: vpcresources.k8s.aws/v1beta1
kind: SecurityGroupPolicy
metadata:
  name: database-sg-policy
  namespace: production
spec:
  # Target Pod selection
  podSelector:
    matchLabels:
      app: database
  # Security Groups to apply
  securityGroups:
    groupIds:
      - sg-0123456789abcdef0  # Database SG
      - sg-0987654321fedcba0  # Common monitoring SG
```

### Configuración de Security Groups con Terraform

Identifique los grupos de seguridad reales de origen y los puertos necesarios para la base de datos, la replicación y la monitorización. Recuerde que se suman las reglas de los grupos asociados. SecurityGroupPolicy, los grupos de origen y destino, la VPC y los selectores de Pods deben corresponderse. La declaración anterior incluía referencias a módulos y grupos de seguridad sin definir y permitía tráfico saliente sin restricciones; no constituía un módulo de despliegue completo.

Los grupos de seguridad mantienen el estado de las conexiones y permiten el tráfico de respuesta. Sin embargo, cada nueva conexión que inicia la aplicación hacia DNS, una base de datos o un servicio externo necesita sus propias reglas de salida. Restrinja los destinos y pruebe la conectividad con el modo de aplicación de políticas del CNI y con NetworkPolicy. La revisión documentada no creó grupos de seguridad ni ENI de Pods, ni realizó pruebas de aislamiento de red.

---

## VPC Endpoints

### VPC Endpoints para EKS privado

El endpoint privado de la API de Kubernetes es distinto de los endpoints PrivateLink de los servicios de AWS. Un endpoint VPC de `eks` no sustituye la conexión con la API de Kubernetes que utiliza kubectl. Seleccione únicamente los servicios necesarios para las rutas reales de nodos, cargas de trabajo y administradores. Compruebe conjuntamente la disponibilidad en la región, DNS, los grupos de seguridad, las rutas, la política del endpoint e IAM.

| Propósito | Ruta |
|---|---|
| API de Kubernetes | Endpoint privado de la API del clúster y red conectada |
| API de administración de EKS | `com.amazonaws.<region>.eks` |
| Pod Identity | `com.amazonaws.<region>.eks-auth` |
| Intercambio STS de IRSA | `com.amazonaws.<region>.sts`; configure el endpoint regional de STS en el SDK |
| Descubrimiento OIDC y claves JWKS | `com.amazonaws.<region>.oidc-eks`, según la documentación vigente; es independiente de STS |
| Imágenes de ECR | Interfaces `ecr.api` y `ecr.dkr`, junto con la ruta de S3 para las capas de las imágenes |
| Servicios adicionales | Endpoints comprobados para las API utilizadas de EC2, Logs, ELB, Auto Scaling, SSM u otros servicios |

La documentación vigente de clústeres privados de EKS también enumera el servicio de API de Route 53 `com.amazonaws.route53`. Distinga la resolución DNS de las llamadas a la API de administración de Route 53 y compruebe la disponibilidad del servicio en la región. Antes de crear endpoints heredados de `ec2messages`, revise los requisitos de SSM Agent y de mensajería; no los cree de forma indiscriminada en todas las regiones.

### Configuración de VPC Endpoint con Terraform

El [ejemplo completo de Terraform](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/security/eks-security/private-endpoints) recibe un mapa `logical name → exact service name`, que relaciona cada nombre lógico con el nombre exacto del servicio. La expresión anterior `split(...)[4]` podía acceder a una posición inexistente o producir una etiqueta incorrecta, según la longitud del nombre del servicio. Ahora las etiquetas utilizan `each.key`.

Proporcione subredes y tablas de rutas existentes, grupos de seguridad de clientes aprobados y una política revisada para el endpoint de S3. Solo se permite HTTPS desde los grupos de clientes indicados. La política de S3 debe incluir los buckets de capas de ECR y los demás buckets necesarios; la política de un endpoint no concede por sí sola permisos de IAM. La revisión documentada superó la validación del esquema con Terraform 1.15.7 y el proveedor de AWS 6.64.0, sin ejecutar plan/apply ni crear recursos.

---

## Registro del plano de control {#control-plane-logging}

### Tipos de registros del plano de control de EKS

Los tipos admitidos son `api`, `audit`, `authenticator`, `controllerManager` y `scheduler`. Los registros de kubelet y de contenedores se recopilan por separado. El grupo de registros es `/aws/eks/<cluster-name>/cluster`. Configure la región, la retención, el acceso, el cifrado, el tratamiento de datos sensibles y el coste de recopilación según la política operativa.

### Habilitación de registros

Coordine los cambios con el responsable o la herramienta de IaC que gestiona el clúster existente. El ejemplo se dirige a un clúster bajo su administración y no se ejecutó en la revisión documentada. Las actualizaciones son asíncronas: consulte el ID de actualización devuelto mediante `describe-update` y compruebe después, por separado, que llegan registros. Habilitar los registros no exige declarar un recurso de clúster nuevo ni cambiar la exposición de la API.

```bash
aws eks update-cluster-config --region ap-northeast-2 \
  --name "$CLUSTER_NAME" --logging file://control-plane-logging.json
```

### Consultas de CloudWatch Logs Insights

Los siguientes ejemplos son **consultas independientes en el lenguaje QL de Logs Insights**. Compruebe los campos reales y el intervalo de tiempo del grupo de registros seleccionado. La primera consulta busca coincidencias de texto de forma exploratoria; no detecta todos los fallos de autenticación. La revisión documentada no ejecutó consultas en un motor administrado.

Errores del autenticador: consulta exploratoria

```text
fields @timestamp, @message
| filter @logStream like /authenticator/
| filter @message like /error|denied/
| sort @timestamp desc
| limit 100
```

Llamadas realizadas por una identidad seleccionada

```text
fields @timestamp, user.username, verb, requestURI, responseStatus.code
| filter @logStream like /audit/
| filter user.username = "REPLACE_WITH_REVIEWED_USERNAME"
| sort @timestamp desc
| limit 50
```

Denegaciones de autorización

```text
fields @timestamp, user.username, verb, requestURI, responseStatus.code
| filter @logStream like /audit/
| filter responseStatus.code = 403
| sort @timestamp desc
| limit 100
```

Accesos a Secrets mediante la API

```text
fields @timestamp, user.username, verb, objectRef.namespace, objectRef.name, responseStatus.code
| filter @logStream like /audit/
| filter objectRef.resource = "secrets"
| sort @timestamp desc
| limit 100
```

---

## Protección de EKS de GuardDuty {#guardduty-eks-protection}

### Descripción general de la protección de EKS de GuardDuty

Distinga el análisis de registros de auditoría de EKS, Runtime Monitoring y las fuentes de datos básicas de GuardDuty. El análisis de auditoría de EKS examina la actividad de la API de Kubernetes y no depende de que el usuario habilite la exportación de registros del plano de control a CloudWatch. Runtime Monitoring requiere el agente de seguridad y una cobertura comprobada.

La documentación vigente de Runtime Monitoring admite EKS sobre EC2 y EKS Auto Mode, y excluye EKS Hybrid Nodes y EKS Fargate. La compatibilidad con ECS Fargate no implica compatibilidad con EKS Fargate. Confirme quién administra la configuración de la organización o del administrador delegado, qué detector regional se utiliza, la plataforma, el coste y quién gestiona los agentes.

### Habilitación de GuardDuty

El siguiente **ejemplo de contenido de configuración** corresponde a un detector existente y no se ha aplicado a ninguna cuenta. `RUNTIME_MONITORING` incluye EKS, por lo que no es válido especificarlo junto con `EKS_RUNTIME_MONITORING`. Consulte el detector que administra, en lugar de crear uno nuevo y elegir el primer ID devuelto. Revise los recursos y permisos para la gestión automática de agentes, así como la cobertura medida.

```json
[
  {"Name": "EKS_AUDIT_LOGS", "Status": "ENABLED"},
  {
    "Name": "RUNTIME_MONITORING",
    "Status": "ENABLED",
    "AdditionalConfiguration": [
      {"Name": "EKS_ADDON_MANAGEMENT", "Status": "ENABLED"}
    ]
  }
]
```

### Tipos de hallazgos de EKS de GuardDuty

Los tipos reales incluyen un prefijo de táctica. Para interpretar un hallazgo, utilice su `severity`, el recurso, la cuenta y la región, la cobertura y la explicación oficial. Evite asignarle una gravedad fija mediante una tabla inventada.

| Ejemplo de tipo real | Alcance |
|---|---|
| `CredentialAccess:Kubernetes/MaliciousIPCaller` | Actividad de la API de Kubernetes |
| `Discovery:Kubernetes/AnomalousBehavior.PermissionChecked` | Comprobaciones anómalas de permisos de Kubernetes |
| `Execution:Runtime/ReverseShell` | Comportamiento en tiempo de ejecución observado por el agente |
| `CryptoCurrency:Runtime/BitcoinTool.B` | Detección relacionada con minería en tiempo de ejecución |

### Respuesta automatizada a hallazgos

Este patrón de EventBridge dirige los hallazgos de Kubernetes y Runtime. Los filtros anteriores `prefix: Kubernetes` y `prefix: Runtime` no coincidían con los nombres reales, que incluyen un prefijo de táctica. La revisión documentada comprobó seis casos con y sin coincidencia y reprodujo el fallo anterior mediante la biblioteca oficial AWS Event Ruler 2.2.0.

El patrón no define ningún destino de notificación o aislamiento. Los hallazgos de Runtime pueden corresponder a recursos distintos de EKS: compruebe los metadatos reales antes de dirigirlos a una respuesta aprobada. Configure por separado los roles y permisos del destino, los reintentos, la DLQ y la deduplicación. Crear `boto3.client("eks")` no aísla un Pod. La contención requiere un control diseñado para el CNI, el host o la nube, junto con una operación autorizada de Kubernetes.

```json
{
  "source": ["aws.guardduty"],
  "detail-type": ["GuardDuty Finding"],
  "detail": {
    "type": [
      {"wildcard": "*:Kubernetes/*"},
      {"wildcard": "*:Runtime/*"}
    ]
  }
}
```

---

## Amazon Inspector

### Análisis de imágenes de contenedor de Inspector

El análisis mejorado de ECR se integra con Amazon Inspector para detectar vulnerabilidades de paquetes en las imágenes admitidas. La información sobre dónde se utiliza una imagen en ejecución es distinta de la detección de comportamientos durante la ejecución. El análisis de imágenes no inspecciona manifiestos arbitrarios de Kubernetes, políticas de IAM ni tráfico de red en directo.

Los cambios en el análisis del registro afectan a la cuenta, la región y los repositorios seleccionados por el filtro. Confirme quién administra la configuración y su alcance previsto. Seleccione el digest que se desplegará, en lugar de `latest`. Mantenga la gestión de nuevos CVE, imágenes admitidas, requisitos para volver a analizarlas y fallos del análisis. Superar el análisis inicial no garantiza la seguridad futura de la imagen.

### Inspector e integración de CI/CD

El [control de análisis completo y sus pruebas](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/security/eks-security) requieren el registro, el repositorio y el digest exactos, una marca de tiempo de finalización y un mapa explícito de recuentos por gravedad. El estado `ACTIVE` del análisis continuo no demuestra, por sí solo, que el resultado inicial esté disponible. La ausencia de resultados, un tiempo de espera agotado, una denegación de acceso, un fallo o un estado desconocido nunca deben interpretarse como cero hallazgos.

```bash
python ecr_scan_gate.py --region ap-northeast-2 \
  --registry-id 123456789012 --repository my-app \
  --digest "$PUBLISHED_IMAGE_DIGEST" --timeout 600 --interval 10 --max-high 0
```

`PUBLISHED_IMAGE_DIGEST` debe contener el valor `sha256:...` confirmado por el registro después de construir y publicar la imagen. Sustituya la cuenta y el repositorio del ejemplo e instale boto3. Las doce pruebas de regresión documentadas utilizan Stubber de boto3/botocore y un reloj simulado, sin enviar solicitudes a AWS ni realizar esperas reales.

La integración con GitHub Actions necesita el ARN de un rol aprobado que confíe en OIDC, `permissions: id-token: write`, permisos mínimos de lectura, el registro devuelto por el inicio de sesión en ECR y el digest de la imagen construida. Un `$ECR_REGISTRY` sin definir, una configuración de credenciales sin rol y una espera fija de 60 segundos no forman un flujo de trabajo completo. En los índices de imágenes multiarquitectura, defina la política de análisis de los digests de las imágenes que se despliegan. Gestione por separado las excepciones, su caducidad y sus responsables, y la antigüedad máxima admisible de los resultados.

Los eventos de hallazgos del análisis mejorado utilizan `aws.inspector2` y `Inspector2 Finding`. Son distintos de los eventos del análisis básico de imágenes de ECR. El [ejemplo validado de alertas con CloudFormation](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/image-security/inspector-alerts.yaml) tiene requisitos adicionales de claves, permisos y destinatarios.

---

## Benchmark CIS de Kubernetes {#cis-kubernetes-benchmark}

### Ejecución de kube-bench

La versión del proyecto revisada es kube-bench **0.16.0**. Incluye `eks-1.5.0`, `eks-1.7.0` y `eks-1.8.0`, pero no el directorio `eks-1.4.0` del ejemplo anterior. Seleccione la edición CIS EKS que exige su organización y que sea compatible con el clúster, el sistema operativo de los nodos y la herramienta. El número más alto no es necesariamente la opción adecuada. El Job de ejemplo del proyecto aún utiliza `latest` y el perfil 1.5.0. Revise y fije el digest de la imagen, el perfil, los montajes del host y los permisos antes de aplicarlo.

Algunas comprobaciones requieren acceso al espacio de procesos PID o al sistema de archivos del host, lo que puede entrar en conflicto con namespaces de aplicaciones que aplican Restricted. Ejecute el escáner mediante un procedimiento aprobado y registre los nodos inspeccionados, las omisiones y las advertencias. La revisión documentada no ejecutó kube-bench en nodos reales.

### Secciones clave del Benchmark CIS

Revise las comprobaciones de controlplane, node, policies y managedservices del perfil CIS EKS elegido. No dé por supuesto que el cliente puede acceder a los archivos del plano de control administrado. Las comprobaciones de configuración de nodos, RBAC, políticas de red y auditoría pueden requerir una clasificación como automáticas, manuales o no aplicables. El porcentaje de comprobaciones superadas no constituye una certificación de seguridad ni una evaluación exhaustiva de posibles intrusiones.

### Comprobaciones de cumplimiento automatizadas

Un Job puede inspeccionar únicamente el nodo en el que se ejecuta. Diseñe la cobertura teniendo en cuenta los grupos de nodos y las diferencias de sistema operativo, arquitectura y configuración. Identifique los resultados con el clúster, el nodo, la imagen, el perfil y la hora. Las ejecuciones programadas necesitan montajes del host, una ServiceAccount, los permisos de lectura necesarios, control de concurrencia, gestión de la finalización y los fallos, y retención de resultados.

El CronJob anterior no montaba los archivos del host y daba por supuesto que la imagen de kube-bench incluía AWS CLI. Si necesita publicar los resultados, utilice un componente de carga revisado o una canalización de registros, con una identidad de carga de trabajo y permisos restringidos. Que los resultados se hayan cargado correctamente no debe ocultar un fallo del análisis.

---

## Cifrado del clúster {#cluster-encryption}

### Cifrado de Secrets de EKS (KMS)

EKS **1.28+ cifra por defecto todos los datos de la API de Kubernetes mediante cifrado de envolvente y una clave KMS propiedad de AWS**. Utilice una clave administrada por el cliente cuando tenga requisitos específicos. La ausencia de una clave de ese tipo no significa que los Secrets de una versión actual de EKS se almacenen sin cifrar.

Para las claves administradas por el cliente, revise conjuntamente el rol del clúster y las concesiones de KMS, la política de la clave, la cuenta y la región, su disponibilidad y los procedimientos de cambio. Deshabilitar o eliminar una clave puede afectar a la disponibilidad y la recuperación; una ventana de eliminación de siete días no es un estándar universal para producción. `Resource: "*"` tiene un significado específico dentro de una política de clave y no debe trasladarse a una política de IAM como acceso sin restricciones. Compruebe quién administra la clave, los roles de administración y uso, las condiciones y la delegación de permisos mediante IAM.

El cifrado en reposo no impide las lecturas autorizadas de la API ni que una aplicación comprometida utilice un valor al que tiene acceso. La rotación de credenciales, la entrega de Secrets y su recarga son operaciones independientes de [gestión de secretos](./05-secrets-management.md). La revisión de este capítulo no creó una clave KMS o un clúster, ni cambió una asociación de clave existente.

---

## Seguridad de nodos {#node-security}

### SO Bottlerocket

Bottlerocket es un sistema operativo para alojar contenedores; utilizarlo no garantiza la seguridad de todas las cargas de trabajo. Compruebe la combinación admitida de versión de Kubernetes, arquitectura de CPU, grupos de nodos administrados o Auto Mode, CNI, almacenamiento y agentes. Respete las reglas para combinar la configuración de arranque de los grupos de nodos administrados, en lugar de sobrescribir los ajustes del clúster, la API o la CA.

Gestione las actualizaciones, los reinicios y los reemplazos, el acceso a los contenedores de control y administración, los permisos de SSM, la procedencia de las imágenes y la recuperación. Los parámetros sysctl de búferes de red del ejemplo anterior no demostraban un refuerzo de la seguridad. El tipo de AMI debe corresponder a la arquitectura de la instancia. La revisión documentada no desplegó grupos de nodos ni sistemas operativos.

### Endurecimiento de seguridad de nodos

Mantenga un rol de nodo con permisos limitados, separado de los roles IRSA o Pod Identity de cada carga de trabajo. Evalúe IMDSv2 y los controles de acceso a metadatos teniendo en cuenta hostNetwork, los Pods privilegiados y la posibilidad de que un nodo resulte comprometido. Habilitar IRSA no bloquea automáticamente el acceso al rol del nodo.

Use identidades sin privilegios de root adecuadas, impida la elevación de privilegios, elimine capacidades, configure seccomp y monte el sistema de archivos raíz en modo de solo lectura, con volúmenes explícitos para las escrituras necesarias. Pruebe la aplicación real con esos controles. Las etiquetas, los selectores y las tolerancias influyen en la programación de Pods; no acreditan el sistema operativo ni conceden autorización. Una etiqueta que puede establecer un usuario, como `node.kubernetes.io/os: bottlerocket`, no debe servir como límite de confianza. Para ubicar cargas por motivos de seguridad, revise las etiquetas controladas por administradores y las protecciones efectivas, como NodeRestriction.

---

## Clústeres privados {#private-clusters}

### Configuración completamente privada de EKS

Para acceder a la API privada de Kubernetes desde la VPC o una red de administración conectada, se necesitan DNS, rutas y grupos de seguridad adecuados, además de autenticación mediante IAM y autorización de Kubernetes. Que la API no sea accesible desde Internet no autoriza automáticamente a todos los usuarios de las redes conectadas.

Antes de cambiar la exposición de la API, pruebe el acceso privado desde los administradores actuales, CI y las rutas de recuperación. Gestione `endpoint_private_access` y `endpoint_public_access` mediante el responsable o la herramienta de IaC existente, evitando declarar accidentalmente un clúster nuevo. Diseñe por separado el arranque de los nodos de trabajo y el acceso a las API, imágenes y paquetes de AWS necesarios. Operar sin Internet y disponer de una API privada son requisitos diferentes.

### Acceso mediante bastión o VPN

Utilice una VPN, Direct Connect, una red conectada adecuadamente o un host de administración con acceso restringido. Asociar una subred a Client VPN no basta: configure conjuntamente la autenticación del servidor y de los clientes, un CIDR de clientes sin solapamientos, las reglas de autorización, las rutas de ida y vuelta, DNS, los grupos de seguridad, el registro de conexiones y los permisos de IAM y Kubernetes.

Un bastión añade responsabilidades de control de acceso, aplicación de parches y auditoría. Evite utilizar como configuración predeterminada un acceso SSH amplio o una administración del clúster sin restricciones. La revisión de este capítulo no desplegó una VPN, un bastión ni certificados.

---

## Patrones para varios inquilinos {#multi-tenancy-patterns}

### Separación de inquilinos mediante namespaces

Los namespaces ofrecen un ámbito administrativo dentro de un clúster compartido, pero no constituyen una separación completa entre inquilinos que no confían entre sí. Combine PSS, RBAC, cuotas, NetworkPolicy, almacenamiento, identidades de cargas de trabajo y límites de acceso a nodos y de administradores. El ejemplo utiliza políticas de Kubernetes 1.35; compruebe su compatibilidad con el clúster real.

La política permite comunicarse con Pods del mismo namespace. Para DNS, un único destino combina el selector de namespace kube-system **y** el selector de Pods kube-dns. Incluye UDP y TCP en el puerto 53. Compruebe por separado las etiquetas DNS reales, NodeLocal DNS, la aplicación de políticas del CNI, otras políticas cuyos permisos se suman y el tráfico de hostNetwork y de nodos. La revisión documentada no realizó pruebas de conectividad en un entorno real.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: tenant-a
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.35
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: v1.35
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: v1.35
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: tenant-a-quota
  namespace: tenant-a
spec:
  hard:
    requests.cpu: "10"
    requests.memory: 20Gi
    limits.cpu: "20"
    limits.memory: 40Gi
    persistentvolumeclaims: "10"
    services.loadbalancers: "2"
---
apiVersion: v1
kind: LimitRange
metadata:
  name: tenant-a-limits
  namespace: tenant-a
spec:
  limits:
    - type: Container
      default:
        cpu: 500m
        memory: 512Mi
      defaultRequest:
        cpu: 100m
        memory: 128Mi
      min:
        cpu: 50m
        memory: 64Mi
      max:
        cpu: "2"
        memory: 4Gi
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: tenant-a-isolation
  namespace: tenant-a
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
  ingress:
    - from:
        - podSelector: {}
  egress:
    - to:
        - podSelector: {}
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: kube-system
          podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - protocol: UDP
          port: 53
        - protocol: TCP
          port: 53
---
# Workload administration is sensitive, even when namespace-scoped.
# The group cannot change Namespace labels, RoleBindings or this NetworkPolicy.
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: tenant-workload-admin
  namespace: tenant-a
rules:
  - apiGroups: [""]
    resources: [pods, services, configmaps]
    verbs: [get, list, watch, create, update, patch, delete]
  - apiGroups: [apps]
    resources: [deployments, statefulsets]
    verbs: [get, list, watch, create, update, patch, delete]
  - apiGroups: [""]
    resources: [pods/log]
    verbs: [get]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: tenant-a-workload-admins
  namespace: tenant-a
subjects:
  - kind: Group
    name: tenant-a-workload-admins
    apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: tenant-workload-admin
  apiGroup: rbac.authorization.k8s.io
```

### Separación de inquilinos mediante RBAC

El administrador de cargas de trabajo del ejemplo no puede modificar directamente las etiquetas de Namespace, los RoleBindings, NetworkPolicy ni los permisos de acceso a Secrets mediante la API. Sin embargo, crear Pods o Deployments puede permitir utilizar indirectamente los Secrets, las ServiceAccounts y los volúmenes del namespace. Excluir el permiso de lectura directa de Secrets no demuestra que sea imposible acceder a sus valores. Si necesita un aislamiento mayor, considere clústeres o cuentas separados.

Para el acceso de usuarios a EKS, evalúe las entradas de acceso actuales con políticas limitadas a namespaces o con grupos y RBAC de Kubernetes. El ConfigMap aws-auth ofrece compatibilidad heredada, pero no es el único mecanismo de integración. Los cambios de modo de autenticación tienen transiciones irreversibles: valide las asignaciones de administradores y nodos y las rutas de recuperación antes de migrar. Las políticas de acceso de EKS y RBAC de Kubernetes pueden conceder permisos de forma independiente. La ausencia de un permiso en uno de ellos no anula el acceso concedido por el otro. Evite conceder system:masters a los desarrolladores como opción predeterminada.

---

## Seguridad perimetral y rutas de inspección {#perimeter-security-and-inspection-paths}

Además de las políticas de IAM y de Pods, revise por separado las aplicaciones públicas, los webhooks de admisión, el acceso de administradores, el tráfico saliente y las rutas entre VPC. Un WAF externo no protege automáticamente los webhooks internos. La inspección central mediante TGW abarca únicamente el tráfico que pasa por esa ruta. Utilice estas guías junto con los controles existentes de IAM, CNI y protección durante la ejecución.

| Área de protección | Guía detallada |
|---|---|
| Incidentes, detección y recuperación tras aplicar parches | [Defensa en profundidad y respuesta a incidentes](./13-defense-in-depth-incident-response.md) |
| HTTP(S), API y acceso al origen que elude la protección perimetral | [Seguridad de WAF, del perímetro y de API](./14-waf-edge-api-security.md) |
| Administración, visibilidad TLS y selección de dispositivos de seguridad | [NGFW de Palo Alto y Fortinet](./15-ngfw-paloalto-fortinet.md) |
| Enrutamiento simétrico, NAT, zonas de disponibilidad y fallos | [GWLB y GENEVE](./16-gwlb-geneve-inspection.md) |

Estas guías presentan fuentes primarias, límites de inspección y planes de verificación para entornos aprobados. No documentan despliegues reales de dispositivos ni resultados de rendimiento.

---

## Resumen

Prácticas recomendadas clave de seguridad de EKS:

1. **Integración con IAM**: Acceso a servicios de AWS mediante IRSA o Pod Identity.
2. **Seguridad de red**: Security Groups para Pods y endpoints de VPC.
3. **Registro y monitorización**: Registros del plano de control y GuardDuty.
4. **Seguridad de imágenes**: Amazon Inspector y análisis de ECR.
5. **Cumplimiento**: Benchmark CIS y kube-bench.
6. **Cifrado**: Cifrado de Secrets mediante KMS.
7. **Seguridad de nodos**: Bottlerocket y permisos mínimos.
8. **Varios inquilinos**: Aislamiento mediante namespaces, RBAC y ResourceQuota.

---

## Referencias

- [Prácticas recomendadas de seguridad de EKS](https://docs.aws.amazon.com/eks/latest/best-practices/security.html)
- [Seguridad en la guía del usuario de Amazon EKS](https://docs.aws.amazon.com/eks/latest/userguide/security.html)
- [Artículos sobre EKS en el blog de seguridad de AWS](https://aws.amazon.com/blogs/security/tag/amazon-eks/)
- [Benchmark CIS de Amazon EKS](https://www.cisecurity.org/benchmark/kubernetes)

- [security-groups-for-pods](https://docs.aws.amazon.com/eks/latest/userguide/security-groups-for-pods.html)
- [sgpp](https://docs.aws.amazon.com/eks/latest/best-practices/sgpp.html)
- [private-clusters](https://docs.aws.amazon.com/eks/latest/userguide/private-clusters.html)
- [configure-sts-endpoint](https://docs.aws.amazon.com/eks/latest/userguide/configure-sts-endpoint.html)
- [how-runtime-monitoring-works-eks](https://docs.aws.amazon.com/guardduty/latest/ug/how-runtime-monitoring-works-eks.html)
- [kubernetes-protection](https://docs.aws.amazon.com/guardduty/latest/ug/kubernetes-protection.html)
- [API_DescribeImageScanFindings](https://docs.aws.amazon.com/AmazonECR/latest/APIReference/API_DescribeImageScanFindings.html)
- [image-scanning-enhanced](https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-scanning-enhanced.html)
- [eventbridge-integration](https://docs.aws.amazon.com/inspector/latest/user/eventbridge-integration.html)
- [access-entries](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html)
- [guardduty_finding-types-kubernetes](https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_finding-types-kubernetes.html)
- [findings-runtime-monitoring](https://docs.aws.amazon.com/guardduty/latest/ug/findings-runtime-monitoring.html)
- [API_UpdateDetector](https://docs.aws.amazon.com/guardduty/latest/APIReference/API_UpdateDetector.html)
- [guardduty_findings_eventbridge](https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_findings_eventbridge.html)
