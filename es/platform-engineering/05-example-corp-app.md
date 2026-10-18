# Sistema de pedidos de ExampleCorp: integración de ACK + kro

> **Última actualización**: 16 de octubre de 2026 · kro 0.9.4 / AWS Load Balancer Controller 3.6.0

## Escenario y alcance de la verificación

ExampleCorp es ficticia. Esta guía define un contrato de integración que conecta un grafo de aplicación de kro con infraestructura administrada por ACK. No es un laboratorio integral que proporcione una API de pedidos funcional ni una imagen de aplicación pública. La anterior imagen ficticia de ECR no se presenta como ejecutable.

ACK administra NLB, TargetGroup, Listener, registros de Route 53 y Aurora. kro crea recursos Service, ConfigMap, TargetGroupBinding (TGB) y Deployment. **Un AWS Load Balancer Controller (LBC) independiente reconcilia TGB y registra/anula el registro de targets de IP de Pod.** Instalar solo ACK y kro no implementa esa conexión.

![AWS LBC reconcilia TargetGroupBinding entre la infraestructura de ACK y la aplicación de kro](../.gitbook/assets/en-platform-engineering-05-example-corp-app-0.png)

[Diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-platform-engineering-05-example-corp-app-0.html)

## Requisitos previos de infraestructura y aplicación

Revise primero los esquemas actuales y la guía de ciclo de vida de los [ejemplos de recursos de ACK](ack/03-elbv2-route53-rds.md). Prepare una VPC aprobada, subredes privadas y grupos de seguridad; un NLB y un Listener internos; un TargetGroup de tipo IP; DNS; y el clúster y las instancias de Aurora. Obtenga el ARN de TargetGroup de `.status.ackResourceMetadata.arn`, no del campo obsoleto `.status.targetGroupARN`.

Prepare por separado AWS LBC, sus CRD, IAM/ServiceAccount y webhook. Esta guía comprueba el TGB `elbv2.k8s.aws/v1beta1` de OSS LBC 3.6.0; no cubre las API de balanceo distintas de EKS Auto Mode. Quienes definan TGB pueden hacer referencia a TargetGroups dentro de los permisos de IAM del controlador, así que limite los ARN permitidos, los namespaces y el acceso de escritura.

El operador debe proporcionar una imagen para la API de pedidos que cumpla este contrato:

- Servir HTTP en el puerto configurado y exponer la comprobación de disponibilidad en `/readyz`.
- Leer `DB_WRITER_HOST`, `DB_READER_HOST`, `DB_PORT` y `DB_NAME` de la configuración de ConfigMap.
- Leer y rotar los archivos de credenciales ubicados bajo `DB_CREDENTIALS_DIR`. No almacenar contraseñas en variables de entorno, ConfigMaps ni en el estado del recurso.
- Ejecutarse con UID 10001, un sistema de archivos raíz de solo lectura, recursos limitados y un volumen `/tmp` con permisos de escritura. Ajuste el contrato según la política de seguridad si la imagen real difiere.

Prepare el namespace `production` y el Secret `order-db-credentials` mediante un flujo aprobado con un proveedor o ESO. Las credenciales de Secrets Manager administradas por RDS no crean automáticamente un Secret de Kubernetes. La base de datos y sus usuarios, los permisos mínimos de base de datos, la verificación de TLS y el pool de conexiones son requisitos independientes. Indicar el nombre de una base de datos en el CR no la crea.

## Puertas de disponibilidad y orden de creación

Para que LBC inyecte puertas de disponibilidad en los Pods, etiquete el namespace con `elbv2.k8s.aws/pod-readiness-gate-inject=enabled` **antes de crear los Pods**. Ya deben existir un Service coincidente y su TGB de tipo IP. El grafo impone mediante CEL el orden Service → TGB → Deployment; una anotación del Deployment hace referencia al nombre del TGB para establecer esa dependencia.

El TGB no incluye un `readyWhen` que espere a que los targets estén saludables. Si la creación del Pod espera a que un target esté saludable, puede producirse un interbloqueo: no hay ningún Pod que pueda convertirse en un target saludable. La existencia del TGB, su reconciliación por LBC, la salud del target y la disponibilidad del Pod son estados distintos. Verifique `failurePolicy`, la inyección del webhook, el rollout, el período de gracia para el apagado y la demora para cancelar el registro de los targets.

## ResourceGraphDefinition

Estos archivos también se encuentran en `examples/platform/examplecorp`. Revise y añada RBAC de agregación para los recursos OrderApp/status/finalizers, Service, ConfigMap, Deployment y TGB. Permitir la creación de RGD delega el uso de los privilegios del controlador.

```yaml
apiVersion: kro.run/v1alpha1
kind: ResourceGraphDefinition
metadata:
  name: examplecorp-webapps
spec:
  schema:
    apiVersion: v1alpha1
    group: platform.example.com
    kind: OrderApp
    scope: Namespaced
    spec:
      replicas: integer | default=3 minimum=1 maximum=10
      image: string | required=true
      port: integer | default=8080 minimum=1 maximum=65535
      targetGroupARN: string | required=true
      vpcID: string | required=true
      credentialsSecretName: string | required=true
      aurora:
        writerEndpoint: string | required=true
        readerEndpoint: string | required=true
        port: integer | default=5432
        dbName: string | required=true
    status:
      availableReplicas: ${deployment.status.availableReplicas}
      serviceIP: ${service.spec.clusterIP}
  resources:
  - id: service
    template:
      apiVersion: v1
      kind: Service
      metadata:
        name: ${schema.metadata.name}
        namespace: ${schema.metadata.namespace}
        labels:
          app.kubernetes.io/name: ${schema.metadata.name}
      spec:
        type: ClusterIP
        selector:
          app.kubernetes.io/name: ${schema.metadata.name}
        ports:
        - name: http
          port: ${schema.spec.port}
          targetPort: http
  - id: dbConfig
    template:
      apiVersion: v1
      kind: ConfigMap
      metadata:
        name: ${schema.metadata.name + "-db"}
        namespace: ${schema.metadata.namespace}
        labels:
          app.kubernetes.io/name: ${schema.metadata.name}
      data:
        DB_WRITER_HOST: ${schema.spec.aurora.writerEndpoint}
        DB_READER_HOST: ${schema.spec.aurora.readerEndpoint}
        DB_PORT: ${string(schema.spec.aurora.port)}
        DB_NAME: ${schema.spec.aurora.dbName}
  - id: targetGroupBinding
    template:
      apiVersion: elbv2.k8s.aws/v1beta1
      kind: TargetGroupBinding
      metadata:
        name: ${schema.metadata.name + "-tgb"}
        namespace: ${schema.metadata.namespace}
        labels:
          app.kubernetes.io/name: ${schema.metadata.name}
      spec:
        targetGroupARN: ${schema.spec.targetGroupARN}
        targetType: ip
        vpcID: ${schema.spec.vpcID}
        serviceRef:
          name: ${service.metadata.name}
          port: ${schema.spec.port}
  - id: deployment
    readyWhen:
    - ${deployment.status.availableReplicas >= deployment.spec.replicas}
    - ${deployment.status.observedGeneration >= deployment.metadata.generation}
    template:
      apiVersion: apps/v1
      kind: Deployment
      metadata:
        name: ${schema.metadata.name}
        namespace: ${schema.metadata.namespace}
        labels:
          app.kubernetes.io/name: ${schema.metadata.name}
      spec:
        replicas: ${schema.spec.replicas}
        selector:
          matchLabels:
            app.kubernetes.io/name: ${schema.metadata.name}
        template:
          metadata:
            labels:
              app.kubernetes.io/name: ${schema.metadata.name}
            annotations:
              platform.example.com/target-group-binding: ${targetGroupBinding.metadata.name}
          spec:
            automountServiceAccountToken: false
            securityContext:
              runAsNonRoot: true
              runAsUser: 10001
              runAsGroup: 10001
              fsGroup: 10001
              seccompProfile:
                type: RuntimeDefault
            containers:
            - name: order-api
              image: ${schema.spec.image}
              ports:
              - name: http
                containerPort: ${schema.spec.port}
              securityContext:
                allowPrivilegeEscalation: false
                readOnlyRootFilesystem: true
                capabilities:
                  drop:
                  - ALL
              resources:
                requests:
                  cpu: 100m
                  memory: 64Mi
                limits:
                  cpu: 500m
                  memory: 128Mi
              readinessProbe:
                httpGet:
                  path: /readyz
                  port: http
              volumeMounts:
              - name: tmp
                mountPath: /tmp
              - name: db-credentials
                mountPath: /var/run/order-db
                readOnly: true
              envFrom:
              - configMapRef:
                  name: ${dbConfig.metadata.name}
              env:
              - name: DB_CREDENTIALS_DIR
                value: /var/run/order-db
            volumes:
            - name: tmp
              emptyDir:
                sizeLimit: 64Mi
            - name: db-credentials
              secret:
                secretName: ${schema.spec.credentialsSecretName}
```

## Entradas de instancia

Las direcciones y la imagen bajo `example.invalid`, así como el ARN y el ID de VPC que aparecen a continuación, son marcadores de posición. Antes de usarlos, obtenga los endpoints y ARN reales de ACK, y verifique el digest de la imagen de la aplicación y el Secret. Los endpoints copiados manualmente no se actualizan automáticamente cuando ACK cambia; defina una ruta aprobada para actualizar las entradas de GitOps.

```yaml
apiVersion: platform.example.com/v1alpha1
kind: OrderApp
metadata:
  name: order-api
  namespace: production
spec:
  replicas: 3
  image: example.invalid/order-api:replace-with-reviewed-image
  port: 8080
  targetGroupARN: arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/replace-with-approved-tg/0123456789abcdef
  vpcID: vpc-0123456789abcdef0
  credentialsSecretName: order-db-credentials
  aurora:
    writerEndpoint: replace-with-writer-endpoint.example.invalid
    readerEndpoint: replace-with-reader-endpoint.example.invalid
    port: 5432
    dbName: orders
```

## Verificación y operaciones

```bash
kubectl get orderapps.platform.example.com order-api -n production -o yaml
kubectl get deploy,svc,targetgroupbindings.elbv2.k8s.aws,configmap \
  -n production -l app.kubernetes.io/name=order-api
kubectl get pods -n production -l app.kubernetes.io/name=order-api -o wide
```

Inspeccione las condiciones del CR y el estado del Deployment junto con las puertas de disponibilidad de los Pods, EndpointSlices, el estado del TGB, la salud de los targets de AWS y la conectividad DNS/HTTP y TLS con la base de datos. Que la comprobación de disponibilidad verifique la base de datos depende de la aplicación real. Todos los metadatos de recursos generados llevan la misma etiqueta de consulta.

Un nuevo servicio de pagos necesita una imagen revisada, un plan independiente de enrutamiento de TargetGroup/Listener y un contrato que defina el usuario, los permisos y el esquema de la base de datos. Compartir Aurora no garantiza el aislamiento de los datos, del rendimiento ni de los costos. Compartir un TargetGroup entre TGB o clústeres requiere gestionar deliberadamente el ciclo de vida de `multiClusterTargetGroup`; ignorar el modelo de propiedad predeterminado puede dar de baja los targets de otros recursos.

Añada réplicas de Aurora mediante recursos `DBInstance` administrados por ACK y combinaciones compatibles de clase y región; los nombres y las etiquetas no fijan de forma permanente qué instancia es la de escritura. Siga la guía sobre `promotionTier`, endpoints y failover del [ejemplo de RDS](ack/03-elbv2-route53-rds.md) y luego pruebe la carga y la recuperación reales.

Actualizar la imagen de un Deployment normalmente activa un `RollingUpdate`; no realiza automáticamente un despliegue Blue/Green ni garantiza que no haya tiempo de inactividad. Blue/Green requiere versiones de aplicación independientes, targets y un cambio de enrutamiento, métricas de validación, condiciones para la reversión y compatibilidad con la base de datos. Al eliminar o reemplazar un CR se pueden limpiar los TGB y Deployments secundarios, así como las asociaciones de targets; no es un cambio de versión inocuo.

## Comprobaciones realizadas

Se leyeron y compararon ambas guías originales y todos los ejemplos con los esquemas actuales de RGD/TGB. cel-go compiló/evaluó 21 expresiones únicas para comprobar cuatro recursos, selectores de Service/Pod, referencias de ConfigMap/Service, la dependencia TGB-antes-de-Deployment y status. Estas son comprobaciones locales que usan entradas sintéticas. No se ejecutaron recursos de AWS, imagen de aplicación, base de datos, salud de targets, mutación de Pod ni tráfico.

- [ACK](02-ack.md)
- [kro](03-kro.md)
- [TGB de AWS LBC 3.6.0](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.6.0/docs/guide/targetgroupbinding/targetgroupbinding.md)
- [Puertas de preparación de Pod](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.6.0/docs/deploy/pod_readiness_gate.md)
