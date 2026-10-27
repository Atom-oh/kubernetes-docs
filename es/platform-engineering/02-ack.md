# AWS Controllers for Kubernetes (ACK)

> **Última actualización**: 23 de octubre de 2026

## Conceptos y arquitectura

ACK conecta los recursos personalizados de Kubernetes con las API de AWS mediante controladores específicos de cada servicio. Las CRD definen las entradas; los controladores reconcilian el estado deseado con el estado observado en AWS. Crear un CR no significa que el recurso de AWS esté listo. Inspeccione el estado y la condición de disponibilidad propia del servicio.

ACK reutiliza las API de Kubernetes, RBAC y las herramientas GitOps, pero la autorización de Kubernetes y IAM de AWS siguen siendo independientes. Normalmente, el CR de un usuario provoca acciones que se ejecutan con los permisos de AWS del controlador. Por lo tanto, el permiso para escribir un CR delega la capacidad de solicitar acciones de AWS a través de ese controlador.

ACK no es un sucesor obligatorio de CloudFormation ni de Terraform. AWS mantiene el recurso real; Kubernetes mantiene la spec y el status del CR. La gestión de la divergencia depende de los campos admitidos y de la lógica del controlador. Asigne un único propietario de las modificaciones en lugar de permitir que varias herramientas o clústeres reconcilien el mismo recurso de AWS.

![ACK reconcilia los recursos personalizados de Kubernetes mediante las API de AWS](../.gitbook/assets/en-platform-engineering-02-ack-0.png)

[Diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-platform-engineering-02-ack-0.html)

## Versiones y compatibilidad

| Controlador | Versión |
| --- | --- |
| s3 | 1.13.1 |
| iam | 1.10.1 |
| sqs | 1.8.2 |
| sns | 1.11.1 |
| elbv2 | 1.8.2 |
| route53 | 1.7.1 |
| rds | 1.13.3 |

Estas versiones se verificaron con las versiones oficiales y los charts OCI. Consulte la lista oficial de servicios para conocer la cobertura completa y el estado Alpha/Beta/GA. GA no implica que se cubran todas las funciones de la API de AWS ni todos los requisitos operativos. La cadena de API v1alpha1 de una CRD es distinta de la madurez del controlador.

El mínimo histórico de Kubernetes 1.16 no es una base operativa actual. Verifique en conjunto una versión compatible de Kubernetes/EKS, la compatibilidad del controlador, la versión de Helm y el proceso de actualización de las CRD.

## Preparación de la instalación e inspección sin conexión

Use la ruta del chart OCI que aparece a continuación, en lugar de la antigua ruta eks-charts s3-chart. Este comando genera los manifiestos sin instalarlos en un clúster.

```bash
helm template ack-s3 \
  oci://public.ecr.aws/aws-controllers-k8s/s3-chart \
  --version 1.13.1 --namespace infra \
  --set aws.region=us-west-2 \
  --set installScope=namespace --set watchNamespace=infra \
  --set enableCARM=false --set enableCrossNamespace=false \
  --set serviceAccount.create=false \
  --set serviceAccount.name=ack-s3-controller \
  --set metrics.service.create=true --set deletionPolicy=retain
```

Antes de una instalación o actualización real, prepare el namespace infra y el ServiceAccount del controlador; luego, configure IRSA o EKS Pod Identity, si es compatible. Verifique las condiciones de confianza OIDC de IRSA para el namespace y el ServiceAccount, o la compatibilidad del agente/SDK de Pod Identity y su asociación. Crear un rol de IAM por sí solo no asigna permisos a un ServiceAccount.

Revise los permisos de lectura, creación, actualización, eliminación y etiquetado del controlador, así como cualquier permiso PassRole, con respecto a los recursos administrados. AmazonS3FullAccess o Resource:"*" no son ejemplos de privilegio mínimo. Las políticas de acceso a datos de la subguía no constituyen una política completa para el controlador.

Que la generación se complete correctamente no valida IAM, las restricciones de las API de AWS, la admisión, la instalación de las CRD, la conectividad con los endpoints ni la creación de recursos. Instalar controladores y modificar CRD son cambios operativos distintos.

## Aislamiento de namespaces y cuentas

El valor predeterminado de installScope es cluster. Limitarse a instalar versiones en los namespaces dev/prod puede hacer que ambos controladores sigan observando los mismos CR. Este ejemplo establece installScope=namespace y watchNamespace=infra, y desactiva CARM y las referencias entre namespaces. Use ámbitos de observación, ServiceAccounts, roles de IAM y RBAC separados para los demás equipos.

Incluso en modo namespace, el chart actual genera un ClusterRole que concede permisos get/list/watch sobre los namespaces para la caché de namespaces. El modo namespace no elimina todos los permisos del clúster. Inspeccione los Roles, ClusterRoles, Bindings y el acceso a Secret/FieldExport generados. El permiso para modificar anotaciones de namespaces, asignaciones de roles y destinos de referencias también afecta al aislamiento.

CARM es una función de administración entre cuentas que requiere confianza en el rol de destino, permisos AssumeRole y configuración del controlador. No garantiza que varios clústeres puedan realizar modificaciones simultáneas de forma segura. Separe las referencias de solo lectura de la propiedad de las modificaciones.

## Creación, referencias y estado

Los esquemas de los servicios varían. La política de S3 pertenece a Bucket.spec.policy; no hay una CRD BucketPolicy independiente. Las políticas administradas de IAM se asocian mediante Role.policies/policyRefs. Las subguías muestran queueName y atributos de tipo string para SQS, así como los campos específicos de Topic/Subscription para SNS.

- [S3 / IAM](ack/01-s3-iam.md)
- [SQS / SNS](ack/02-sqs-sns.md)
- [ELBv2 / Route 53 / Aurora](ack/03-elbv2-route53-rds.md)

```bash
kubectl get buckets.s3.services.k8s.aws -n infra
kubectl get bucket.s3.services.k8s.aws app-data -n infra -o json
kubectl describe bucket.s3.services.k8s.aws app-data -n infra
kubectl logs -n infra \
  -l app.kubernetes.io/instance=ack-s3 --all-containers --tail=100
kubectl get events -n infra \
  --field-selector involvedObject.name=app-data
```

ACK.ResourceSynced=True describe la sincronización del controlador; no es una comprobación de conexión a la base de datos ni de disponibilidad de la aplicación. Inspeccione otras condiciones, como ACK.Terminal/ACK.Recoverable, y el estado del servicio. Cuando se proporciona para el recurso, su ARN se encuentra en status.ackResourceMetadata.arn; las ARN de NLB y TargetGroup también usan esta ruta.

Los campos Ref admitidos pueden conectar recursos del mismo namespace. Aplicar varios documentos YAML no constituye una transacción que abarque AWS. Verifique que los recursos referenciados estén listos y compruebe los identificadores/ARN externos.

## Adopción y retención

Use las anotaciones de ResourceAdoption que se muestran a continuación. El chart actual de S3 habilita esta feature gate. Revise los identificadores, la cuenta y la región, y planifique la transferencia de propiedad desde otras herramientas antes de adoptar.

```yaml
apiVersion: s3.services.k8s.aws/v1alpha1
kind: Bucket
metadata:
  name: existing-data
  namespace: infra
  annotations:
    services.k8s.aws/adoption-policy: adopt
    services.k8s.aws/adoption-fields: '{"name":"REPLACE_WITH_EXISTING_BUCKET"}'
    services.k8s.aws/deletion-policy: retain
spec:
  name: REPLACE_WITH_EXISTING_BUCKET
```

El entorno de ejecución acepta adopt y adopt-or-create. adopt lee el estado existente y lo incorpora a spec/status; adopt-or-create puede crear un recurso que no exista. La reconciliación normal posterior puede modificar un recurso adoptado, por lo que la adopción no es simplemente acceso de lectura. El comportamiento de solo lectura es una función independiente, con su propia feature gate y ciclo de vida. La antigua anotación resource-imported:"true" no configura la adopción. La documentación oficial también identifica AdoptedResource como el enfoque anterior.

El valor de retención es **retain**. El entorno de ejecución actual no acepta orphan. El orden de precedencia es services.k8s.aws/deletion-policy del CR individual, luego la deletion-policy específica del servicio del namespace y, por último, el valor predeterminado del controlador. Retener recursos de AWS deja responsabilidades continuas de costos, propiedad y copias de seguridad.

## Observabilidad, escalado y recuperación

Habilite metrics.service.create y haga coincidir el namespace de destino y el nombre del puerto que se muestran a continuación. Las CRD del Prometheus Operator y los selectores del Prometheus ServiceMonitor son requisitos previos independientes.

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: ack-s3
  namespace: monitoring
spec:
  namespaceSelector:
    matchNames: [infra]
  selector:
    matchLabels:
      app.kubernetes.io/name: s3-chart
      app.kubernetes.io/instance: ack-s3
  endpoints:
    - port: metricsport
      interval: 30s
```

El entorno de ejecución revisado define ack_outbound_api_requests_total y ack_outbound_api_requests_error_total. No invente nombres de métricas para el éxito o el fallo de la reconciliación ni para la latencia de la API. Verifique los nombres de las métricas de controller-runtime, sus etiquetas y sus versiones en el endpoint real. La auditoría de CloudTrail depende de la compatibilidad del servicio con el registro de API y de los eventos configurados.

La configuración de réplicas es deployment.replicas; revise leaderElection.enabled cuando ejecute varias réplicas. replicaCount no es una configuración de este chart. Las réplicas adicionales con elección de líder no aumentan automáticamente el rendimiento en paralelo. Ajuste la concurrencia de reconciliación y la resincronización según las cuotas, el throttling y el uso de recursos observados.

Versione en Git los manifiestos y charts específicos de cada entorno, sin incluir credenciales. La recuperación requiere datos y copias de seguridad de AWS, identificadores, política de retención y propiedad, además de los CR. Crear un CR en otra región no implementa la replicación ni la recuperación de datos.

## ACK administrado por EKS

La capacidad ACK de EKS Capabilities ejecuta los controladores de servicios GA de upstream como una sola capacidad en una infraestructura propiedad de AWS. Según las pruebas de octubre de 2026, presenta las siguientes diferencias con respecto a la instalación con Helm anterior.

- IAM parte de un único rol de capacidad, y un `IAMRoleSelector` con ámbito de clúster asume un rol distinto para cada namespace. Para lograr la misma separación con los controladores OSS se necesitan tanto `featureGates.IAMRoleSelector=true` como `enableCARM=false`; si se deja CARM activado, el controlador no se inicia.
- Las etiquetas de recursos de AWS y las etiquetas de sesión usan el prefijo `eks:` (`eks:eks-capability-arn` y otras). Al migrar, actualice las condiciones de asignación de costos y de IAM definidas para las etiquetas OSS `services.k8s.aws/`.
- No hay CRD `FieldExport`, y no se pueden elegir ni cambiar las versiones de los controladores ni el intervalo de resincronización. La divergencia del lado de AWS no se revirtió periódicamente en un plazo de 25 minutos ni en el entorno administrado ni en OSS.
- Las anotaciones de adopción (`adopt-or-create`) y `deletion-policy: retain` también funcionaron en la capacidad administrada (medido en el entorno administrado); asimismo, un controlador OSS instalado después de eliminar la capacidad con RETAIN adoptó los CR existentes.

Para ver mediciones y recomendaciones de selección, consulte [EKS Capabilities](../eks/13-eks-capabilities.md).

## Solución de problemas

Si falla la creación, inspeccione las condiciones y los eventos, la imagen y los registros del controlador, la cuenta/región, la confianza y las políticas de IAM, las referencias y las restricciones del servicio. Distinga los errores de RBAC de Kubernetes de los errores de IAM de AWS. En los recursos en estado Terminating, identifique qué condición de eliminación, dependencia o retención de AWS está esperando el finalizer.

No elimine los finalizers como práctica habitual. Esto puede dejar recursos de AWS sin seguimiento. Primero resuelva la causa; recurra a un procedimiento de recuperación de último recurso solo después de revisar el estado real de los recursos, las copias de seguridad y la propiedad posterior.

## Verificación y referencias

Se leyeron los ocho archivos originales de la guía y los dos cuestionarios en coreano/inglés, incluidos 56 bloques de código únicos. Se generaron siete charts OCI oficiales y se verificaron 18 ejemplos de recursos con las CRD versionadas y el rechazo de campos desconocidos en spec. No se probaron la creación de recursos de AWS, la ejecución de controladores, la admisión/CEL, la entrega de mensajes ni la conectividad con bases de datos.

- [Servicios de ACK](https://aws-controllers-k8s.github.io/community/docs/community/services/)
- [Adopción de recursos](https://aws-controllers-k8s.github.io/community/docs/user-docs/features/#resourceadoption)
- [Retención](https://aws-controllers-k8s.github.io/community/docs/user-docs/deletion-policy/)
- [Chart de S3 1.13.1](https://github.com/aws-controllers-k8s/s3-controller/tree/v1.13.1/helm)
- [Runtime 0.66.0](https://github.com/aws-controllers-k8s/runtime/tree/v0.66.0)

[Cuestionario de ACK](../quizzes/platform-engineering/02-ack-quiz.md)
