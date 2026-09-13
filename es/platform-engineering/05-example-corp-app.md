# Sistema de pedidos de ExampleCorp: integración de ACK + kro

> **Última actualización**: September 12, 2026 · kro 0.9.4 / AWS Load Balancer Controller 3.5.0

## Escenario y alcance de la verificación

ExampleCorp es ficticia. Esta guía define un contrato de integración que conecta un grafo de aplicación de kro con infraestructura administrada por ACK. No es un laboratorio integral que proporcione una API de pedidos funcional ni una imagen de aplicación pública. La anterior imagen ficticia de ECR no se presenta como ejecutable.

ACK administra NLB, TargetGroup, Listener, registros de Route 53 y Aurora. kro crea recursos Service, ConfigMap, TargetGroupBinding (TGB) y Deployment. **Un AWS Load Balancer Controller (LBC) independiente reconcilia TGB y registra/anula el registro de targets de IP de Pod.** Instalar solo ACK y kro no implementa esa conexión.

![AWS LBC reconciles TargetGroupBinding between ACK infrastructure and the kro application](../.gitbook/assets/en-platform-engineering-05-example-corp-app-0.png)

[Diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-platform-engineering-05-example-corp-app-0.html)

## Requisitos previos de infraestructura y aplicación

Primero revise los esquemas actuales y la guía de ciclo de vida en los [ejemplos de recursos de ACK](ack/03-elbv2-route53-rds.md). Prepare VPC/subnets privadas/grupos de seguridad aprobados, un NLB/Listener interno, un TargetGroup de ip, DNS y clúster/instancias de Aurora. Lea el ARN de TargetGroup desde `.status.ackResourceMetadata.arn`, no desde el anterior `.status.targetGroupARN`.

Prepare AWS LBC, sus CRD, IAM/ServiceAccount y webhook por separado. Esta guía verifica el TGB elbv2.k8s.aws/v1beta1 de OSS LBC 3.5.0, no las API de balanceo de carga distintas de EKS Auto Mode. Los autores de TGB pueden hacer referencia a TargetGroups dentro de los permisos IAM del controller, por lo que debe restringir los ARN permitidos, los namespaces y el acceso de escritura.

El operador debe proporcionar una imagen de API de pedidos que cumpla este contrato:

- Sirva HTTP en el puerto configurado con preparación en `/readyz`.
- Lea DB_WRITER_HOST, DB_READER_HOST, DB_PORT y DB_NAME desde la configuración de ConfigMap.
- Lea y rote los archivos de credenciales bajo DB_CREDENTIALS_DIR. No incluya contraseñas en variables de entorno, ConfigMaps ni status.
- Funcione con UID 10001, una raíz de solo lectura, recursos limitados y un volumen /tmp escribible. Adapte el contrato según la política de seguridad si la imagen real difiere.

Prepare production y order-db-credentials mediante un flujo de proveedor/ESO aprobado. Las credenciales de Secrets Manager administradas por RDS no crean automáticamente un Secret de Kubernetes. La base de datos/usuarios de aplicación, los permisos mínimos de DB, la verificación de TLS y el agrupamiento de conexiones son requisitos independientes. Nombrar una base de datos en el CR no la crea.

## Puertas de preparación y orden de creación

Para las puertas de preparación de Pod de LBC, etiquete el namespace elbv2.k8s.aws/pod-readiness-gate-inject=enabled **antes de la creación de Pod**. Ya deben existir un Service coincidente y su TGB de ip. El grafo impone Service → TGB → Deployment mediante CEL; una anotación de Deployment hace referencia al nombre de TGB para establecer esa dependencia.

El TGB no tiene un readyWhen que espere targets saludables. Hacer que la creación de Pod espere la salud del target puede provocar un interbloqueo cuando no existe ningún Pod que pueda convertirse en un target saludable. La existencia de TGB, la reconciliación de LBC, la salud del target y la preparación de Pod son estados diferentes. Verifique failurePolicy/inyección de webhook, rollout, periodo de gracia de apagado y retraso de anulación de registro.

## ResourceGraphDefinition

Estos archivos también se encuentran en examples/platform/examplecorp. Revise y añada RBAC de agregación para los recursos OrderApp/status/finalizers y Service, ConfigMap, Deployment y TGB. El permiso para crear RGD delega el uso de los privilegios del controller.

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

Las direcciones/la imagen example.invalid y el ARN/ID de VPC a continuación son marcadores de posición. Lea los endpoints/ARN reales de ACK y verifique el digest de la imagen de aplicación y el Secret antes de usarlos. Los endpoints copiados manualmente no siguen automáticamente los cambios de ACK; proporcione una ruta aprobada de actualización de entradas de GitOps.

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

Inspeccione las condiciones de CR y el estado de Deployment junto con las puertas de preparación de Pod, EndpointSlices, el estado de TGB, la salud del target de AWS, la conectividad DNS/HTTP y TLS de la base de datos. Que la preparación compruebe la base de datos depende de la aplicación real. Todos los metadatos de recursos generados llevan la misma etiqueta de consulta.

Un nuevo servicio de pagos necesita una imagen revisada, un plan independiente de enrutamiento de TargetGroup/Listener y un contrato de usuario/permisos/esquema de base de datos. Compartir Aurora no garantiza el aislamiento de datos, rendimiento ni costos. Compartir un TargetGroup entre TGB/clústeres requiere un manejo deliberado del ciclo de vida de multiClusterTargetGroup; ignorar el modelo de propiedad predeterminado puede anular el registro de otros targets.

Añada réplicas de Aurora mediante ACK DBInstances usando combinaciones de clase/región compatibles; los nombres/etiquetas no corrigen los roles de writer. Siga la guía de promotionTier, endpoints y failover en el [ejemplo de RDS](ack/03-elbv2-route53-rds.md), y luego pruebe la carga y la recuperación reales.

Actualizar una imagen de Deployment normalmente realiza RollingUpdate, no Blue/Green automático ni tiempo de inactividad cero garantizado. Blue/Green necesita versiones de aplicación independientes, targets/corte de enrutamiento, métricas de validación, condiciones de rollback y compatibilidad de base de datos. Eliminar/reemplazar un CR puede limpiar TGB/Deployments secundarios y asociaciones de targets; no es un cambio de versión inofensivo.

## Comprobaciones realizadas

Se leyeron y compararon ambas guías originales y todos los ejemplos con los esquemas actuales de RGD/TGB. cel-go compiló/evaluó 21 expresiones únicas para comprobar cuatro recursos, selectores de Service/Pod, referencias de ConfigMap/Service, la dependencia TGB-antes-de-Deployment y status. Estas son comprobaciones locales que usan entradas sintéticas. No se ejecutaron recursos de AWS, imagen de aplicación, base de datos, salud de targets, mutación de Pod ni tráfico.

- [ACK](02-ack.md)
- [kro](03-kro.md)
- [AWS LBC 3.5.0 TGB](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/docs/guide/targetgroupbinding/targetgroupbinding.md)
- [Puertas de preparación de Pod](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/docs/deploy/pod_readiness_gate.md)
