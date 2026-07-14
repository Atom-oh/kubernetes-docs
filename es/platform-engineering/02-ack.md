# AWS Controllers for Kubernetes (ACK)

## Tabla de contenidos

* [Introducción](02-ack.md#introduction)
* [Arquitectura](02-ack.md#architecture)
* [Instalación y configuración](02-ack.md#installation-and-configuration)
* [Servicios de AWS compatibles](02-ack.md#supported-aws-services)
* [Los orígenes y la evolución de ACK](02-ack.md#the-origins-and-evolution-of-ack)
* [Ejemplos de creación de recursos](02-ack.md#resource-creation-examples)
* [Gestión de recursos](02-ack.md#resource-management)
* [Consideraciones de seguridad](02-ack.md#security-considerations)
* [Monitoreo y logging](02-ack.md#monitoring-and-logging)
* [Mejores prácticas](02-ack.md#best-practices)
* [Solución de problemas](02-ack.md#troubleshooting)
* [Conclusión](02-ack.md#conclusion)

## Introducción

AWS Controllers for Kubernetes (ACK) es un proyecto que permite a los usuarios de Kubernetes gestionar directamente servicios y recursos de AWS a través de la Kubernetes API. ACK extiende el modelo de API declarativa de Kubernetes a los recursos de AWS, lo que permite a desarrolladores y operadores gestionar infraestructura de AWS usando herramientas y APIs familiares de Kubernetes.

### Beneficios clave de ACK

* **Experiencia unificada**: Gestiona recursos de Kubernetes y AWS con las mismas herramientas y flujos de trabajo
* **Compatibilidad con GitOps**: Define recursos de AWS como código y gestiónalos en repositorios Git
* **Configuración declarativa**: Define el estado deseado y deja que el controller reconcilie el estado real
* **Enfoque nativo de Kubernetes**: Usa conceptos y APIs estándar de Kubernetes
* **Compatibilidad multi-cluster**: Referencia los mismos recursos de AWS desde múltiples clusters
* **Integración con IAM**: Integración de Kubernetes service accounts con AWS IAM roles

### Comparación con enfoques existentes

| Característica         | ACK                 | AWS CloudFormation       | Terraform       | AWS SDK/CLI         |
| ---------------------- | ------------------- | ------------------------ | --------------- | ------------------- |
| Interfaz               | Kubernetes API      | CloudFormation templates | HCL             | Programming API/CLI |
| Declarativo            | ✅                   | ✅                        | ✅               | ❌                   |
| Gestión de estado      | Kubernetes etcd     | CloudFormation stack     | Terraform state | Gestión manual      |
| Detección de drift     | ✅                   | ✅                        | ✅               | ❌                   |
| Integración con Kubernetes | Nativa          | Limitada                 | Limitada        | Limitada            |
| Servicios compatibles  | Limitados (en expansión) | Amplios            | Amplios         | Todos los servicios |

## Arquitectura

ACK se basa en el patrón Kubernetes operator y proporciona controllers para cada servicio de AWS.

### Componentes clave

1. **Service Controller**: Controller dedicado para cada servicio de AWS
2. **Custom Resource Definitions (CRD)**: Definen recursos de AWS como Kubernetes API
3. **Custom Resources (CR)**: Instancias de recursos de AWS
4. **Reconciliation Loop**: Detecta y resuelve diferencias entre el estado deseado y el estado real

### Cómo funciona

1. El usuario aplica un manifest YAML de Kubernetes para definir un recurso de AWS
2. El controller de ACK detecta cambios en custom resources
3. El controller llama a la AWS API para crear, actualizar o eliminar el recurso de AWS correspondiente
4. El controller monitorea el estado del recurso de AWS y actualiza el estado del recurso de Kubernetes

## Instalación y configuración

### Prerrequisitos

* Kubernetes cluster (v1.16 o superior)
* kubectl configurado
* Cuenta de AWS y permisos IAM adecuados
* Helm 3 (opcional)

### Métodos de instalación

#### 1. Instalación del ACK Service Controller

Los controllers de ACK se instalan por separado para cada servicio de AWS. Por ejemplo, para instalar el controller de S3:

```bash
# Add Helm chart repository
helm repo add aws-controllers-k8s https://aws.github.io/eks-charts

# Install S3 controller
helm install --create-namespace -n ack-system ack-s3-controller \
  aws-controllers-k8s/s3-chart
```

#### 2. Configuración de permisos IAM

Los controllers de ACK necesitan permisos IAM adecuados para gestionar recursos de AWS. Puedes configurar permisos usando IRSA (IAM Roles for Service Accounts):

```bash
# Create IAM policy
aws iam create-policy \
  --policy-name ACKs3ControllerPolicy \
  --policy-document file://s3-controller-policy.json

# Attach IAM role to service account
eksctl create iamserviceaccount \
  --cluster=<cluster-name> \
  --namespace=ack-system \
  --name=ack-s3-controller \
  --attach-policy-arn=arn:aws:iam::<account-id>:policy/ACKs3ControllerPolicy \
  --approve
```

Ejemplo de s3-controller-policy.json:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:CreateBucket",
        "s3:DeleteBucket",
        "s3:PutBucketTagging",
        "s3:GetBucketTagging",
        "s3:PutEncryptionConfiguration",
        "s3:GetEncryptionConfiguration",
        "s3:PutBucketPolicy",
        "s3:GetBucketPolicy",
        "s3:ListBucket"
      ],
      "Resource": "*"
    }
  ]
}
```

#### 3. Configuración del controller

Puedes usar archivos de valores de Helm para personalizar la configuración del controller:

```yaml
# values.yaml
aws:
  region: us-west-2
resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 500m
    memory: 256Mi
serviceAccount:
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::<account-id>:role/ACKs3ControllerRole
```

```bash
helm install --create-namespace -n ack-system ack-s3-controller \
  aws-controllers-k8s/s3-chart -f values.yaml
```

## Servicios de AWS compatibles

ACK proporciona controllers para varios servicios de AWS. Cada service controller puede instalarse y gestionarse individualmente.

### Servicios compatibles actualmente (a julio de 2025)

* Amazon API Gateway (apigatewayv2)
* Amazon DynamoDB
* Amazon ECR
* Amazon EKS
* Amazon ElastiCache
* Amazon MemoryDB
* Amazon MQ
* Amazon RDS
* Amazon S3
* Amazon SageMaker
* AWS IAM
* AWS Lambda
* AWS SNS
* AWS SQS
* Amazon EventBridge
* Amazon MSK
* Amazon OpenSearch Service
* AWS ACM
* AWS Route 53

### Estado de los service controllers

Cada service controller tiene uno de los siguientes estados:

* **Alpha**: Etapa temprana de desarrollo, la API puede cambiar
* **Beta**: Funcionalmente completo, estable, pero la API puede cambiar
* **GA (Generally Available)**: Listo para uso en producción

Consulta el estado más reciente en el [ACK GitHub Repository](https://github.com/aws-controllers-k8s/community).

## Los orígenes y la evolución de ACK

### Evolución de Infrastructure as Code

La gestión de recursos de AWS ha evolucionado de la siguiente manera:

1. **Era de gestión manual**: Creación y gestión de recursos directamente en la AWS Console
2. **AWS CloudFormation**: Introducción de gestión declarativa de infraestructura basada en templates, pero separada de los flujos de trabajo de Kubernetes
3. **Terraform**: Gestión unificada de infraestructura con soporte multi-cloud y HCL, pero aún requiere herramientas y flujos de trabajo separados
4. **ACK**: Gestión directa de recursos de AWS a través de la Kubernetes API, aprovechando la toolchain existente de K8s, incluidos kubectl, GitOps y RBAC

### ¿Por qué gestión de AWS nativa de Kubernetes?

Limitaciones de los enfoques existentes:

* **Separación de herramientas**: Carga de gestión dual al operar Terraform/CloudFormation y kubectl por separado
* **Inconsistencia de estado**: El estado de la herramienta IaC y el estado del Kubernetes cluster están separados, lo que puede causar drift
* **Dificultad de integración con GitOps**: Resulta difícil gestionar recursos de AWS con herramientas GitOps como ArgoCD/Flux
* **Fragmentación de la experiencia de los equipos**: Los equipos de infraestructura y aplicaciones usan herramientas y flujos de trabajo diferentes

ACK aborda estos problemas al permitir la gestión unificada de infraestructura y aplicaciones de AWS a través de un único plano de control de Kubernetes.

## Ejemplos de creación de recursos

Para ver ejemplos detallados de creación de recursos de AWS con ACK, consulta los siguientes documentos:

* [S3 and IAM](ack/01-s3-iam.md)
* [SQS and SNS](ack/02-sqs-sns.md)
* [ELBv2, Route 53, RDS (NLB + Aurora PostgreSQL)](ack/03-elbv2-route53-rds.md)

## Gestión de recursos

### Comprobar el estado de los recursos

Para comprobar el estado de los recursos de ACK:

```bash
kubectl describe bucket my-sample-bucket
```

Salida de ejemplo:

```
Name:         my-sample-bucket
Namespace:    default
API Version:  s3.services.k8s.aws/v1alpha1
Kind:         Bucket
Metadata:
  ...
Spec:
  Name:  my-unique-bucket-name-123
  ...
Status:
  Ack Resource Metadata:
    Arn:                    arn:aws:s3:::my-unique-bucket-name-123
    Owner Account ID:       123456789012
  Conditions:
    Last Transition Time:  2025-07-13T04:00:00Z
    Status:                True
    Type:                  ACK.ResourceSynced
```

### Actualización de recursos

Para actualizar un recurso de ACK, modifica el manifest y vuelve a aplicarlo:

```bash
kubectl apply -f updated-bucket.yaml
```

### Eliminación de recursos

Para eliminar un recurso de ACK:

```bash
kubectl delete bucket my-sample-bucket
```

De forma predeterminada, ACK también elimina el recurso de AWS correspondiente cuando se elimina el recurso de Kubernetes. Puedes cambiar este comportamiento usando annotations:

```yaml
metadata:
  annotations:
    services.k8s.aws/deletion-policy: "orphan"
```

### Importación de recursos

Para importar recursos de AWS existentes a ACK:

```yaml
apiVersion: s3.services.k8s.aws/v1alpha1
kind: Bucket
metadata:
  name: imported-bucket
  annotations:
    services.k8s.aws/resource-imported: "true"
spec:
  name: existing-bucket-name
```

## Consideraciones de seguridad

### Gestión de permisos IAM

Los controllers de ACK necesitan permisos IAM adecuados para los recursos de AWS que gestionan. Se recomienda seguir el principio de mínimo privilegio y conceder solo los permisos necesarios.

#### Ejemplo de política IAM granular

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:CreateBucket",
        "s3:DeleteBucket",
        "s3:GetBucketTagging",
        "s3:PutBucketTagging"
      ],
      "Resource": "arn:aws:s3:::my-unique-bucket-name-*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:ListAllMyBuckets"
      ],
      "Resource": "*"
    }
  ]
}
```

### Aislamiento de namespaces

Puedes usar namespaces y IAM roles separados para distintos equipos o entornos con el fin de aislar permisos:

```bash
# Install controller for development environment
helm install --create-namespace -n ack-system-dev ack-s3-controller \
  aws-controllers-k8s/s3-chart \
  --set serviceAccount.annotations."eks\.amazonaws\.com/role-arn"=arn:aws:iam::123456789012:role/ACKs3ControllerRoleDev

# Install controller for production environment
helm install --create-namespace -n ack-system-prod ack-s3-controller \
  aws-controllers-k8s/s3-chart \
  --set serviceAccount.annotations."eks\.amazonaws\.com/role-arn"=arn:aws:iam::123456789012:role/ACKs3ControllerRoleProd
```

### Políticas de recursos

Puedes usar Kubernetes RBAC para restringir el acceso a recursos de ACK:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: dev
  name: s3-editor
rules:
- apiGroups: ["s3.services.k8s.aws"]
  resources: ["buckets"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: dev-s3-editor
  namespace: dev
subjects:
- kind: User
  name: developer
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: s3-editor
  apiGroup: rbac.authorization.k8s.io
```

## Monitoreo y logging

### Comprobar los logs del controller

Para comprobar los logs del controller de ACK:

```bash
kubectl logs -n ack-system -l app.kubernetes.io/name=ack-s3-controller
```

### Métricas de Prometheus

Los controllers de ACK exponen métricas de Prometheus:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: ack-s3-controller
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: ack-s3-controller
  endpoints:
  - port: metrics
    interval: 30s
```

Métricas clave:

* `ack_reconcile_success_total`: Número de reconciliaciones exitosas
* `ack_reconcile_failure_total`: Número de reconciliaciones fallidas
* `ack_api_call_duration_seconds`: Latencia de llamadas a la AWS API

### Integración con AWS CloudTrail

Las llamadas a la AWS API realizadas por los controllers de ACK se registran en CloudTrail. Puedes revisar los logs de CloudTrail para auditar las operaciones de ACK.

## Mejores prácticas

### Organización de recursos

1. **Nomenclatura clara**: Usa nombres de recursos claros y coherentes
2. **Usar annotations**: Aprovecha annotations para la gestión de recursos
3. **Aplicar labels**: Usa labels para agrupar y filtrar recursos

```yaml
apiVersion: s3.services.k8s.aws/v1alpha1
kind: Bucket
metadata:
  name: app-data-bucket
  annotations:
    services.k8s.aws/deletion-policy: "orphan"
    description: "Application data storage"
  labels:
    environment: production
    app: my-application
    team: data-engineering
spec:
  name: my-app-data-20250713
  tagging:
    tagSet:
      - key: Environment
        value: Production
```

### Control de versiones

1. **Usar repositorio Git**: Almacena manifests de recursos de ACK en un repositorio Git
2. **Separar configuraciones de entorno**: Mantén configuraciones separadas para entornos de desarrollo, staging y producción
3. **Usar Kustomize**: Usa Kustomize para gestionar diferencias específicas de cada entorno

```
├── base/
│   ├── s3-bucket.yaml
│   ├── sqs-queue.yaml
│   └── kustomization.yaml
├── overlays/
│   ├── dev/
│   │   ├── kustomization.yaml
│   │   └── patch.yaml
│   ├── staging/
│   │   ├── kustomization.yaml
│   │   └── patch.yaml
│   └── prod/
│       ├── kustomization.yaml
│       └── patch.yaml
```

### Rendimiento y escalabilidad

1. **Establecer Resource Requests y Limits**: Asigna recursos adecuados a los controllers
2. **Escalar réplicas del controller**: Aumenta las réplicas del controller en entornos grandes
3. **Ajustar la frecuencia de reconciliación**: Optimiza la frecuencia de reconciliación según sea necesario

```yaml
apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: ack-s3-controller
  namespace: ack-system
spec:
  chart:
    spec:
      chart: s3-chart
      sourceRef:
        kind: HelmRepository
        name: aws-controllers-k8s
  values:
    resources:
      requests:
        cpu: 200m
        memory: 256Mi
      limits:
        cpu: 500m
        memory: 512Mi
    replicaCount: 2
```

### Recuperación ante desastres

1. **Estrategia de backup**: Backup regular de los manifests de recursos de ACK
2. **Plan de recuperación**: Documenta procedimientos de recuperación de recursos en caso de fallo
3. **Consideración multi-region**: Implementa una estrategia multi-region para recursos críticos

## Solución de problemas

### Problemas comunes

#### 1. Error en la creación de recursos

**Síntoma**: Se crea el recurso de ACK, pero no se crea el recurso de AWS

**Solución**:

* Comprueba los logs del controller
* Verifica los permisos IAM
* Comprueba el estado y los eventos del recurso

```bash
kubectl logs -n ack-system -l app.kubernetes.io/name=ack-s3-controller
kubectl describe bucket my-sample-bucket
```

#### 2. Problemas de permisos

**Síntoma**: Mensaje de error "AccessDenied"

**Solución**:

* Verifica las políticas y roles IAM
* Comprueba la configuración de IRSA
* Revisa los logs de CloudTrail

#### 3. Eliminación de recurso atascada

**Síntoma**: Recurso atascado en estado "Terminating"

**Solución**:

* Comprueba las dependencias
* Elimina finalizers (si es necesario)

```bash
kubectl patch bucket my-sample-bucket -p '{"metadata":{"finalizers":[]}}' --type=merge
```

### Herramientas de depuración

```bash
# Check controller version
kubectl get deployment -n ack-system ack-s3-controller -o jsonpath="{.spec.template.spec.containers[0].image}"

# Check CRDs
kubectl get crd | grep services.k8s.aws

# Check events
kubectl get events --field-selector involvedObject.name=my-sample-bucket

# Check controller logs in detail
kubectl logs -n ack-system -l app.kubernetes.io/name=ack-s3-controller --tail=100
```

## Conclusión

AWS Controllers for Kubernetes (ACK) es una herramienta potente que cierra la brecha entre Kubernetes y los servicios de AWS. ACK permite a los usuarios de Kubernetes gestionar recursos de AWS usando APIs y herramientas familiares de Kubernetes.

Este documento cubrió los conceptos básicos de ACK, métodos de instalación, ejemplos de creación de recursos S3, IAM, SQS y SNS, gestión de recursos, consideraciones de seguridad, monitoreo y solución de problemas.

ACK sigue evolucionando, con soporte añadido para más servicios de AWS. Combinado con flujos de trabajo GitOps, proporciona una forma potente de gestionar infraestructura de AWS como código.

### Próximos pasos

* Construir pipelines GitOps usando ACK
* Integrar múltiples AWS service controllers
* Extender custom resource definitions
* Desarrollar estrategias multi-account y multi-region

## Referencias

* [ACK Official Documentation](https://aws-controllers-k8s.github.io/community/)
* [ACK GitHub Repository](https://github.com/aws-controllers-k8s/community)
* [AWS Service Controller List](https://aws-controllers-k8s.github.io/community/docs/community/services/)
* [ACK Design Principles](https://aws-controllers-k8s.github.io/community/docs/community/design/)
* [EKS Workshop - ACK](https://www.eksworkshop.com/intermediate/290_ack/)

## Quiz

Para comprobar lo que aprendiste en este capítulo, intenta el [ACK Quiz](../quizzes/platform-engineering/02-ack-quiz.md).
