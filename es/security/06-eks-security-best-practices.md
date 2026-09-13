# Mejores prácticas de seguridad de EKS

> **Base de revisión**: Documentación actual de AWS, esquemas de API de Kubernetes 1.35, Terraform 1.15.7 / proveedor de AWS 6.64.0. No se realizó ninguna implementación en un clúster activo.
> **Última actualización**: September 13, 2026

Este documento cubre las mejores prácticas de seguridad para entornos de Amazon EKS. Aprenda a operar clústeres EKS de forma segura, desde la integración de IAM hasta la seguridad de red y la protección en tiempo de ejecución.

## Tabla de contenido

1. [IRSA (IAM Roles for Service Accounts)](#irsa-iam-roles-for-service-accounts)
2. [EKS Pod Identity](#eks-pod-identity)
3. [Security Groups for Pods](#security-groups-for-pods)
4. [VPC Endpoints](#vpc-endpoints)
5. [Registro del plano de control](#control-plane-logging)
6. [Protección de GuardDuty para EKS](#guardduty-eks-protection)
7. [Amazon Inspector](#amazon-inspector)
8. [CIS Kubernetes Benchmark](#cis-kubernetes-benchmark)
9. [Cifrado del clúster](#cluster-encryption)
10. [Seguridad de nodos](#node-security)
11. [Clústeres privados](#private-clusters)
12. [Patrones de multi-tenancy](#multi-tenancy-patterns)

---

## IRSA (IAM Roles for Service Accounts) {#irsa-iam-roles-for-service-accounts}

### Descripción general de IRSA

IRSA (IAM Roles for Service Accounts) asocia roles de IAM con Kubernetes ServiceAccounts, lo que permite que los Pods accedan de forma segura a servicios de AWS.

El servidor de la API de Kubernetes emite el token proyectado de ServiceAccount. El SDK lo intercambia con STS AssumeRoleWithWebIdentity; STS valida el emisor/JWKS asociado con el proveedor IAM OIDC y las condiciones de confianza del rol, y luego devuelve credenciales temporales. El objeto de proveedor IAM OIDC no es un proxy de emisión de tokens en ejecución.


### Configuración de IRSA

El siguiente ejemplo de operador no se ejecutó. Haga coincidir la Region, el clúster, el propietario/ruta del bucket y el ARN de la política reales, y reemplace la imagen de aplicación por una versión/digest revisada. No mezcle un emisor OIDC de otra Region ni un ARN de rol generado por eksctl adivinado.



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

### Mejores prácticas de IRSA

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

## EKS Pod Identity {#eks-pod-identity}

### Descripción general de Pod Identity

EKS Pod Identity es un mecanismo alternativo de entrega de credenciales. Elija entre este e IRSA según la compatibilidad real de la plataforma/SDK, los límites de confianza y los requisitos operativos; no sustituye a IRSA ni hace automáticamente que cada carga de trabajo sea más segura.

Un SDK de Pod compatible usa la ruta del agente local; el agente obtiene credenciales temporales mediante EKS Auth de acuerdo con la asociación y el rol. Para roles entre cuentas o encadenamiento de roles, verifique por separado el mecanismo, la confianza y las condiciones de etiquetas de sesión admitidos actualmente.


### Configuración de Pod Identity

EKS Auto Mode incluye el agente. Para otras plataformas compatibles, seleccione una versión de addon actualmente compatible y adminístrela mediante el propietario existente. Reemplace los valores de cuenta/clúster/namespace/ServiceAccount siguientes y restrinja la confianza del rol con las condiciones de etiquetas de sesión del namespace/ServiceAccount previsto. Instalar el addon y la asociación no valida la compatibilidad del SDK, la precedencia de credenciales ni el acceso de red.



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
| **Complejidad de configuración** | Se requiere proveedor OIDC | Simple (llamada a API) |
| **Política de confianza** | Emisor OIDC, audiencia y sujeto exactos | Principal de servicio más condiciones restringidas |
| **Reutilización de roles** | Se necesita modificación por clúster | Reutilización entre clústeres |
| **Registro de auditoría** | CloudTrail (nivel de SA) | CloudTrail (nivel de Pod) |
| **Etiquetas de sesión** | No suponga el mismo comportamiento de etiquetas de sesión de EKS Pod Identity | Admite etiquetas de sesión documentadas; revise el comportamiento de deshabilitación/encadenamiento |
| **Selección** | Plataforma compatible, confianza OIDC y modelo operativo | Plataforma compatible, asociación y modelo de agente/SDK |

---

## Security Groups para Pods {#security-groups-for-pods}

### Descripción general

Security Groups para Pods aplica VPC Security Groups directamente a los Pods, proporcionando aislamiento a nivel de red.

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

Security Groups para Pods requiere una instancia compatible con trunking y un modo CNI compatibles. La documentación actual excluye Windows y EKS Auto Mode; no todas las instancias Nitro son compatibles. La política VPC Resource Controller pertenece al rol del clúster. Varios security groups adjuntos combinan las reglas permitidas; no las intersecan. Revise el modo estricto/estándar, DNS, probes y el comportamiento del balanceador de carga antes de habilitarlo.

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

### Configuración de Security Group con Terraform

Identifique los security groups de origen reales y los puertos de base de datos, replicación y monitorización requeridos, recordando que las reglas de SG adjuntas se combinan. SecurityGroupPolicy, los SG de origen/destino, la VPC y los selectores de Pod deben coincidir. La declaración anterior contenía referencias indefinidas a módulos/SG y salida sin restricciones; no era un módulo de implementación completo.

El tráfico de retorno de security groups tiene estado, pero las nuevas conexiones DNS/base de datos/externas iniciadas por una aplicación tienen requisitos de salida independientes. Limite los destinos y pruebe la conectividad con el modo de aplicación de CNI y NetworkPolicy. Esta auditoría no creó security groups/Pod ENIs ni ejecutó pruebas de aislamiento de red.

---

## VPC Endpoints {#vpc-endpoints}

### VPC Endpoints para EKS privado

El endpoint privado de API de Kubernetes y los endpoints PrivateLink de servicios de AWS son distintos. Un endpoint VPC de `eks` no reemplaza la conexión de API de Kubernetes utilizada por kubectl. Seleccione solo los servicios requeridos por las rutas reales de nodo, carga de trabajo y operador, y verifique conjuntamente la compatibilidad de Region, DNS, security groups, rutas, política de endpoint e IAM.

| Propósito | Ruta |
|---|---|
| API de Kubernetes | Endpoint de API privada del clúster y red conectada |
| API de administración de EKS | `com.amazonaws.<region>.eks` |
| Pod Identity | `com.amazonaws.<region>.eks-auth` |
| Intercambio STS de IRSA | `com.amazonaws.<region>.sts`; configure STS regional en el SDK |
| Detección de OIDC/JWKS | `com.amazonaws.<region>.oidc-eks` documentado actualmente, independiente de STS |
| Imágenes de ECR | Interfaces `ecr.api`, `ecr.dkr` más la ruta de capas de imagen de S3 |
| Servicios adicionales | Endpoints verificados para las API de EC2, Logs, ELB, Auto Scaling, SSM y otras que se usen realmente |

La documentación actual de clústeres privados de EKS también enumera el servicio de API Route 53 `com.amazonaws.route53`. Distinga la resolución DNS de las llamadas de API de administración de Route 53 y verifique la compatibilidad de servicio/Region. No cree incondicionalmente endpoints `ec2messages` heredados en todas las Region; compruebe los requisitos del SSM Agent y de mensajería.

### Configuración de VPC Endpoint con Terraform

El [ejemplo completo de Terraform](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/security/eks-security/private-endpoints) toma un mapa de `nombre lógico → nombre de servicio exacto`. El anterior `split(...)[4]` podía estar fuera de rango o producir la etiqueta incorrecta según la longitud del nombre del servicio; ahora las etiquetas usan `each.key`.

Proporcione subredes existentes, tablas de rutas, security groups de cliente aprobados y una política de endpoint S3 revisada. HTTPS solo se permite desde los grupos de cliente indicados. La política de S3 debe abarcar los buckets de capas de ECR y otros buckets necesarios; una política de endpoint no concede por sí misma acceso de IAM. La validación de esquema de Terraform 1.15.7/proveedor de AWS 6.64.0 fue exitosa; no se realizó ningún plan/apply ni creación de recursos.

---

## Registro del plano de control {#control-plane-logging}

### Tipos de logs del plano de control de EKS

Los tipos compatibles son `api`, `audit`, `authenticator`, `controllerManager` y `scheduler`. Los logs de kubelet/contenedor tienen rutas de recopilación independientes. El grupo de logs es `/aws/eks/<cluster-name>/cluster`; configure Region, retención, acceso, cifrado, manejo de datos sensibles y coste de recopilación según la política operativa.

### Habilitación del registro

Coordine los cambios con el propietario de IaC del clúster existente. Lo siguiente se dirige a un clúster propio y no se ejecutó durante esta auditoría. Las actualizaciones son asíncronas: inspeccione el ID de actualización devuelto con `describe-update`, y después verifique por separado la llegada real de logs. Habilitar el registro no requiere declarar un nuevo recurso de clúster ni cambiar la exposición del endpoint de API.

```bash
aws eks update-cluster-config --region ap-northeast-2 \
  --name "$CLUSTER_NAME" --logging file://control-plane-logging.json
```

### Consultas de CloudWatch Logs Insights

Estas son **consultas de Logs Insights QL independientes**. Inspeccione los campos/rango de tiempo reales en el grupo de logs seleccionado. La primera consulta es una coincidencia de texto exploratoria, no un detector completo de errores de autenticación. No se ejecutó ningún motor de consultas administrado durante esta auditoría.

Errores de autenticador (exploratorio)

```text
fields @timestamp, @message
| filter @logStream like /authenticator/
| filter @message like /error|denied/
| sort @timestamp desc
| limit 100
```

Llamadas de una identidad elegida

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

Acceso a la API de Secret

```text
fields @timestamp, user.username, verb, objectRef.namespace, objectRef.name, responseStatus.code
| filter @logStream like /audit/
| filter objectRef.resource = "secrets"
| sort @timestamp desc
| limit 100
```

---

## Protección de GuardDuty para EKS {#guardduty-eks-protection}

### Descripción general de GuardDuty EKS Protection

Distinga el análisis de logs de auditoría de EKS, Runtime Monitoring y las fuentes de datos fundamentales de GuardDuty. El análisis de auditoría de EKS se refiere a la actividad de la API de Kubernetes y no depende de habilitar la exportación de logs del plano de control CloudWatch del usuario. Runtime Monitoring requiere el agente de seguridad y cobertura real.

La documentación actual de Runtime Monitoring admite EKS respaldado por EC2 y EKS Auto Mode, y excluye EKS Hybrid Nodes y EKS Fargate. La compatibilidad con ECS Fargate no es compatibilidad con EKS Fargate. Confirme la propiedad de organización/administrador delegado, el detector regional, la plataforma, el coste y el propietario de la gestión de agentes.

### Habilitación de GuardDuty

Lo siguiente es un **ejemplo de payload de configuración** para un detector existente; no se aplicó a una cuenta. `RUNTIME_MONITORING` incluye EKS, por lo que especificarlo junto con `EKS_RUNTIME_MONITORING` no es válido. Inspeccione el detector propio en lugar de crear siempre un detector y seleccionar el primer ID devuelto. Revise los recursos/permisos de gestión automatizada de agentes y la cobertura medida.

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

### Tipos de hallazgos de GuardDuty EKS

Los tipos reales incluyen un prefijo de táctica. Use la `severity`, el recurso, la cuenta/Region, la cobertura y la explicación oficial del hallazgo en lugar de una tabla de severidad fija inventada.

| Ejemplo de tipo real | Alcance |
|---|---|
| `CredentialAccess:Kubernetes/MaliciousIPCaller` | Actividad de API de Kubernetes |
| `Discovery:Kubernetes/AnomalousBehavior.PermissionChecked` | Comprobaciones anómalas de permisos de Kubernetes |
| `Execution:Runtime/ReverseShell` | Comportamiento en tiempo de ejecución observado por el agente |
| `CryptoCurrency:Runtime/BitcoinTool.B` | Detección relacionada con minería en tiempo de ejecución |

### Respuesta automatizada a hallazgos

Este patrón de EventBridge enruta tipos de Kubernetes/Runtime. Los anteriores `prefix: Kubernetes` y `prefix: Runtime` no coincidían con los nombres reales con prefijo de táctica. Se comprobaron seis casos coincidentes/no coincidentes y el error anterior con la biblioteca oficial AWS Event Ruler 2.2.0.

El patrón no tiene destino de notificación/aislamiento. Los hallazgos de Runtime pueden afectar a recursos más allá de EKS: inspeccione los metadatos reales del recurso antes de enrutar a una respuesta aprobada. Configure por separado roles/permisos de destino, reintentos, DLQ y deduplicación. Crear `boto3.client("eks")` no aísla un Pod; la contención requiere un control diseñado de CNI/host/cloud y una operación de Kubernetes autorizada.

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

## Amazon Inspector {#amazon-inspector}

### Escaneo de imágenes de contenedor de Inspector

El escaneo mejorado de ECR se integra con Amazon Inspector para inspeccionar vulnerabilidades de paquetes en imágenes compatibles. El contexto de uso de la imagen en ejecución difiere de la detección de comportamiento en tiempo de ejecución. El mismo escaneo de imágenes no inspecciona manifiestos arbitrarios de Kubernetes, políticas de IAM ni tráfico de red activo.

Los cambios de escaneo de registro afectan a la cuenta/Region y al alcance de filtro del repositorio; confirme la propiedad y el alcance previsto. Seleccione el digest que se implementará en lugar de `latest`. Continúe gestionando nuevos CVE, imágenes compatibles, elegibilidad para reescaneo y errores; superar un escaneo inicial no garantiza seguridad futura.

### Inspector e integración con CI/CD

La [puerta de escaneo y pruebas completas](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/security/eks-security) requieren el registro/repositorio/digest exactos, una marca de tiempo de finalización y un mapa explícito de conteo por severidad. `ACTIVE` de escaneo continuo por sí solo no demuestra que el resultado inicial esté listo. Los resultados ausentes, el tiempo de espera, la denegación de acceso, el error y el estado desconocido nunca se convierten en cero hallazgos.

```bash
python ecr_scan_gate.py --region ap-northeast-2 \
  --registry-id 123456789012 --repository my-app \
  --digest "$PUBLISHED_IMAGE_DIGEST" --timeout 600 --interval 10 --max-high 0
```

`PUBLISHED_IMAGE_DIGEST` debe ser el valor `sha256:...` confirmado por el registro después de build/push. Reemplace la cuenta/repositorio de ejemplo e instale boto3. Doce pruebas de regresión usan Stubber real de boto3/botocore y tiempo simulado, sin solicitudes de AWS ni espera real.

Una integración de GitHub Actions necesita un ARN de rol aprobado con confianza OIDC, `permissions: id-token: write`, lecturas de mínimo privilegio, el registro de las salidas de inicio de sesión de ECR y propagación del digest creado. Un `$ECR_REGISTRY` indefinido, configuración de credenciales sin un rol y una espera fija de 60 segundos no constituyen un flujo de trabajo completo. Para índices de múltiples arquitecturas, defina una política de escaneo para los digests secundarios implementados. Gestione por separado las excepciones, la caducidad/propiedad y los requisitos de actualidad de resultados.

Los eventos de hallazgos mejorados usan `aws.inspector2` / `Inspector2 Finding`, distintos de los eventos de escaneo de imágenes de ECR Basic. El [ejemplo validado de alertas de CloudFormation](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/image-security/inspector-alerts.yaml) tiene requisitos previos independientes de clave, permiso y receptor.

---

## CIS Kubernetes Benchmark {#cis-kubernetes-benchmark}

### Ejecución de kube-bench

La versión upstream revisada es kube-bench **0.16.0**. Incluye `eks-1.5.0`, `eks-1.7.0` y `eks-1.8.0`, pero no el directorio `eks-1.4.0` del ejemplo anterior. Seleccione la edición CIS EKS requerida por su organización y compatible con el clúster/SO de nodo/compatibilidad de herramienta; el número más alto no es automáticamente la elección correcta. El Job de ejemplo upstream aún usa `latest` y1.5.0, por lo que revise y fije el digest de imagen, el perfil, los montajes de host y los permisos en lugar de aplicarlo ciegamente.

Algunas comprobaciones requieren acceso al PID/sistema de archivos del host y entran en conflicto con namespaces de aplicación Restricted. Use una ruta operativa de escáner aprobada y registre los nodos inspeccionados, las omisiones y las advertencias. Esta auditoría no ejecutó kube-bench en nodos reales.

### Secciones clave de CIS Benchmark

Inspeccione las comprobaciones reales de controlplane, node, policies y managedservices en el perfil CIS EKS elegido. No suponga acceso del cliente a archivos administrados del plano de control. La configuración de nodos, RBAC, política de red y las comprobaciones de auditoría pueden requerir clasificaciones automática/manual/no aplicable. Una tasa de aprobación de herramienta no es una certificación de seguridad ni una evaluación exhaustiva de compromiso.

### Comprobaciones automatizadas de cumplimiento

Un Job puede inspeccionar solo el nodo en el que está programado. Diseñe la cobertura para grupos de nodos, SO, arquitectura y diferencias de configuración, y etiquete los resultados con clúster/nodo/imagen/perfil/hora. Las ejecuciones programadas necesitan montajes de host, un ServiceAccount, los permisos de lectura requeridos, control de concurrencia, manejo de finalización/error y retención de resultados.

El CronJob anterior carecía de montajes de host y asumía que la imagen de kube-bench contenía AWS CLI. Si los resultados deben cargarse, use un cargador revisado o una canalización de logs con identidad de carga de trabajo restringida. Una carga exitosa no debe ocultar un escaneo fallido.

---

## Cifrado del clúster {#cluster-encryption}

### Cifrado de Secrets de EKS (KMS)

EKS **1.28+ usa de forma predeterminada cifrado de envolvente de todos los datos de API de Kubernetes mediante una clave KMS propiedad de AWS**. Elija una clave administrada por el cliente para requisitos específicos; la ausencia de tal clave no significa que los Secrets actuales de EKS se almacenen sin cifrar.

Para claves administradas por el cliente, revise conjuntamente las concesiones de rol de clúster/KMS, la política de clave, la cuenta/Region, la disponibilidad de la clave y los procedimientos de cambio. Deshabilitar/eliminar una clave puede afectar la disponibilidad y la recuperación; no copie una ventana de eliminación de siete días como estándar universal de producción. `Resource: "*"` tiene un significado específico de política de clave, pero no debe reutilizarse como acceso de IAM sin restricciones. Verifique el propietario real de la clave, los roles administrativos/de uso, las condiciones y la delegación de IAM.

El cifrado en reposo no impide lecturas autorizadas de API ni el uso de un valor por parte de una aplicación comprometida. La rotación de credenciales, la entrega de Secret y la recarga son operaciones independientes de [secrets-management](./05-secrets-management.md). Este capítulo no creó una clave KMS/clúster ni cambió una asociación de clave existente.

---

## Seguridad de nodos {#node-security}

### Bottlerocket OS

Bottlerocket es una opción de SO de host de contenedor, no una garantía de que cada carga de trabajo sea segura. Verifique la combinación compatible de versión de Kubernetes del clúster, arquitectura de CPU, modelo de managed-node-group/Auto Mode, CNI, almacenamiento y agentes. Siga las reglas de combinación de bootstrap de managed-node-group en lugar de sobrescribir ciegamente la configuración de clúster/API/CA.

Opere actualizaciones/reinicios/reemplazos, acceso de control/admin-container, permisos de SSM, procedencia de imágenes y recuperación. Los sysctls de búfer de red del ejemplo anterior no eran evidencia de refuerzo de seguridad. El tipo de AMI y la arquitectura de instancia deben coincidir; esta auditoría no ejecutó ningún grupo de nodos ni SO.

### Refuerzo de seguridad de nodos

Separe un rol de nodo limitado de los roles de carga de trabajo específicos de IRSA/Pod Identity. Evalúe IMDSv2 y los controles de acceso a metadatos, incluidos hostNetwork, Pods privilegiados y compromiso de nodos. El mero hecho de habilitar IRSA no bloquea automáticamente el acceso al rol de nodo.

Use identidades adecuadas sin root, sin escalada de privilegios, capacidades eliminadas, seccomp y un sistema de archivos raíz de solo lectura con volúmenes escribibles explícitos, y pruebe la aplicación real. Las etiquetas/selectores/tolerations son entradas de programación, no certificación de SO ni autorización. No trate una etiqueta establecida por el usuario como `node.kubernetes.io/os: bottlerocket` como límite de confianza; revise las etiquetas controladas por administradores y protecciones reales como NodeRestriction para la ubicación de seguridad.

---

## Clústeres privados {#private-clusters}

### Configuración de EKS completamente privado

Una API privada de Kubernetes requiere DNS, rutas y security groups desde la VPC o red de administración conectada, además de autenticación IAM y autorización de Kubernetes. La ausencia de accesibilidad desde Internet público no autoriza a todo usuario conectado.

Antes de cambiar la exposición de API, pruebe el acceso privado desde los operadores, CI y rutas de recuperación actuales. Administre `endpoint_private_access`/`endpoint_public_access` mediante el propietario de IaC existente en lugar de declarar inadvertidamente un clúster nuevo. Diseñe por separado el bootstrap de workers y el acceso requerido a API/imágenes/paquetes de AWS. La operación sin Internet y la exposición de API privada son requisitos diferentes.

### Acceso por bastion o VPN

Use VPN, Direct Connect, una red conectada adecuadamente o un host de administración restringido. Una asociación de subred de Client VPN por sí sola es insuficiente: configure conjuntamente autenticación de servidor/cliente, CIDR de cliente sin superposición, reglas de autorización, rutas/rutas de retorno, DNS, security groups, registro de conexiones y permisos de IAM/Kubernetes.

Un bastion añade sus propias responsabilidades de acceso, parcheado y auditoría. No use de forma predeterminada entrada SSH amplia ni administración de clúster sin restricciones. Este capítulo no implementó una VPN, bastion ni certificados.

---

## Patrones de multi-tenancy {#multi-tenancy-patterns}

### Multi-tenancy basada en namespace

Los namespaces son un ámbito administrativo en un clúster compartido, no un límite completo entre tenants mutuamente hostiles. Combine PSS, RBAC, cuota, NetworkPolicy, almacenamiento, identidad de carga de trabajo y límites de nodos/administradores. El ejemplo usa una línea base de políticas de Kubernetes1.35; verifique la compatibilidad con el clúster real.

Se permiten pares del mismo namespace, mientras que DNS usa el namespace kube-system **y** el selector de Pod kube-dns en un par. Se incluyen UDP y TCP53. Verifique por separado las etiquetas DNS reales, NodeLocal DNS, aplicación de CNI, otras políticas aditivas y tráfico de hostNetwork/nodo. No se realizó ninguna prueba de conectividad activa.

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

### RBAC multi-tenancy

El administrador de carga de trabajo de ejemplo no puede modificar directamente las etiquetas de Namespace, RoleBindings, NetworkPolicy ni permisos de API de Secret. Sin embargo, crear Pods/Deployments puede usar indirectamente Secrets, ServiceAccounts y volúmenes del namespace. Excluir `get` de Secret no demuestra la imposibilidad de acceder a un secret. Considere clústeres/cuentas independientes cuando se requiera un aislamiento más fuerte.

Para acceso de usuarios de EKS, evalúe las entradas de acceso actuales con políticas de acceso de ámbito de namespace o grupos/RBAC de Kubernetes. El ConfigMap aws-auth es una ruta de compatibilidad heredada, no el único mecanismo de integración. Los cambios de modo de autenticación tienen restricciones de transición irreversibles; valide las asignaciones de administrador/nodo y las rutas de recuperación antes de la migración. Las políticas de acceso de EKS y Kubernetes RBAC pueden permitir acceso de forma independiente, por lo que la ausencia de permiso en una no deniega una autorización de la otra. No conceda system:masters a desarrolladores ordinarios como ejemplo predeterminado.

---

## Resumen

Mejores prácticas clave de seguridad de EKS:

1. **Integración de IAM**: Acceda a servicios de AWS con IRSA o Pod Identity
2. **Seguridad de red**: Security Groups para Pods, VPC endpoints
3. **Registro y monitorización**: Logs del plano de control, GuardDuty
4. **Seguridad de imágenes**: Amazon Inspector, escaneo de ECR
5. **Cumplimiento**: CIS Benchmark, kube-bench
6. **Cifrado**: Cifrado de Secrets con KMS
7. **Seguridad de nodos**: Bottlerocket OS, mínimo privilegio
8. **Multi-tenancy**: Aislamiento de namespace, RBAC, ResourceQuota

---

## Referencias

- [EKS Security Best Practices](https://docs.aws.amazon.com/eks/latest/best-practices/security.html)
- [Amazon EKS User Guide - Security](https://docs.aws.amazon.com/eks/latest/userguide/security.html)
- [AWS Security Blog - EKS](https://aws.amazon.com/blogs/security/tag/amazon-eks/)
- [CIS Amazon EKS Benchmark](https://www.cisecurity.org/benchmark/kubernetes)

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
