# Parte 5: prácticas recomendadas y seguridad

> **Fecha de referencia de la revisión**: 12 de septiembre de 2026 · Spark upstream 4.2.0 / Hadoop 3.5.0 / AWS SDK v2 2.35.4

## Ámbito

Este capítulo se basa en el envío directo a Kubernetes de la Parte 1 y cubre las credenciales temporales de S3, las métricas/registros de eventos, History Server, la red y RBAC. Para Spark 4.2, usa Kubernetes 1.34 o posterior y una versión compatible de kubectl, y prepara el espacio de nombres spark-jobs y el acceso a EKS. Operators y EMR tienen sus propias rutas de configuración y permisos.

Prepara acceso administrativo para IRSA o Pod Identity, un bucket y roles de S3 existentes, un registro de imágenes y herramientas para crearlas. Aplica el ejemplo de PodMonitor solo donde esté instalado Prometheus Operator. Los valores de cuenta, bucket, imagen y región que aparecen a continuación son **ejemplos que debes reemplazar**. Una lista de comprobación de configuración por sí sola no demuestra la seguridad operativa, la recuperación ni el rendimiento.

## 1. Crear una imagen S3A compatible con las versiones

La distribución de Spark 4.2 revisada incluye Hadoop client 3.5.0, pero no todas las dependencias S3A adicionales. La versión de hadoop-aws debe coincidir con la **misma versión de Hadoop**. Estas son las dependencias de ejecución que Maven resuelve para 3.5.0:

| Artefacto | Versión |
| --- | --- |
| org.apache.hadoop:hadoop-aws | 3.5.0 |
| software.amazon.awssdk:bundle | 2.35.4 |
| software.amazon.s3.analyticsaccelerator:analyticsaccelerator-s3 | 1.3.1 |
| org.wildfly.openssl:wildfly-openssl | 2.2.5.Final |

No mezcles JAR antiguos de AWS SDK al azar ni copies solo hadoop-aws. Este POM resuelve sus dependencias de ejecución sin volver a copiar Hadoop common. Comprueba de nuevo las versiones incluidas si usas otra imagen de Spark o un runtime de EMR.

```xml
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>docs.review</groupId>
  <artifactId>spark-s3a-runtime</artifactId>
  <version>1.0.0</version>
  <dependencies>
    <dependency>
      <groupId>org.apache.hadoop</groupId>
      <artifactId>hadoop-aws</artifactId>
      <version>3.5.0</version>
    </dependency>
  </dependencies>
</project>
```

Guárdalo como Dockerfile. La plataforma de la imagen elegida debe coincidir con los nodos de la carga de trabajo y de History Server.

```dockerfile
FROM spark:4.2.0-scala2.13-java21-ubuntu
COPY --chown=185:185 s3a-jars/ /opt/spark/jars/
USER 185
```

```bash
# Save the XML below as s3a-pom.xml.
mvn -f s3a-pom.xml org.apache.maven.plugins:maven-dependency-plugin:3.8.1:copy-dependencies \
  -DincludeScope=runtime -DoutputDirectory="$PWD/s3a-jars"
: "${SPARK_S3_IMAGE:?Set a registry/repository/tag you can publish}"
: "${SPARK_IMAGE_PLATFORM:?Set a platform matching the target nodes, for example linux/amd64}"
docker build --platform "$SPARK_IMAGE_PLATFORM" --tag "$SPARK_S3_IMAGE" .
# Authenticate to your registry through your normal procedure, then publish the tested image.
docker push "$SPARK_S3_IMAGE"
```

Usa la imagen con todas las dependencias para el driver, los executors y History Server.
`--packages` resuelve dependencias a través del proceso que envía el trabajo; no las instala automáticamente en un History Server iniciado con spark-class. Valida el acceso al registro, las comprobaciones de la imagen, la compatibilidad y las lecturas/escrituras reales en S3; después, fija el digest de la imagen probada para las operaciones.

## 2. Distinguir IRSA de Pod Identity

Para esta combinación de Hadoop 3.5.0 y SDK v2, usa:

| Ruta de identidad | fs.s3a.aws.credentials.provider |
| --- | --- |
| IRSA | software.amazon.awssdk.auth.credentials.WebIdentityTokenFileCredentialsProvider |
| EKS Pod Identity | software.amazon.awssdk.auth.credentials.ContainerCredentialsProvider |

IRSA usa confianza OIDC, una anotación en la cuenta de servicio y un token web identity proyectado. Pod Identity usa una asociación y la ruta de credenciales de contenedor del Agent; la anotación de IRSA no lo configura. No combines ambas rutas a ciegas.

La cadena predeterminada de S3A incluye el wrapper de credenciales de contenedor/instancia, pero no el proveedor web identity. En esta combinación que solo usa SDK v2, no se asignaba automáticamente el nombre antiguo `com.amazonaws.auth.WebIdentityTokenCredentialsProvider`. Sí se asignan algunos otros alias heredados, así que esto no significa que todos los nombres antiguos siempre fallen.
Una ruta de identidad explícita también reduce el fallback no deseado a otras fuentes de credenciales. Aun así, las credenciales temporales requieren que la confianza, los permisos y la red estén configurados correctamente.

Guarda este **ejemplo de IRSA** como serviceaccounts.yaml. Reemplaza los roles y configura primero la confianza para el proveedor OIDC del clúster, la audiencia y el subject exacto de espacio de nombres/cuenta de servicio. Los executors y History Server no reciben los permisos de administración de Kubernetes del driver.

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: spark-data-driver
  namespace: spark-jobs
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::111122223333:role/docs-spark-driver
automountServiceAccountToken: true
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: spark-data-executor
  namespace: spark-jobs
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::111122223333:role/docs-spark-executor
automountServiceAccountToken: false
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: spark-data-history
  namespace: spark-jobs
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::111122223333:role/docs-spark-history
automountServiceAccountToken: false
```

Separa los permisos de datos según su propósito:

- Driver: acceso de entrada/salida necesario y escritura de registros de eventos bajo spark-events. Revisa los requisitos de cambio de nombre/multipart de S3A y los permisos de KMS que se necesiten.
- Executors: solo los buckets/prefijos necesarios para el procesamiento real de datos.
- History Server: listar/leer el prefijo de registros de eventos y los permisos de descifrado de KMS necesarios. Este ejemplo desactiva el cleaner, así que no necesita permiso de eliminación.

Para Pod Identity, elimina las anotaciones de IRSA y configura las asociaciones, la confianza de los roles y los permisos de EKS Auth del Agent/nodo para estas tres cuentas de servicio. Cambia también las propiedades que siguen a ContainerCredentialsProvider. El proveedor OIDC de IAM es un requisito previo de IRSA, no un requisito universal para todas las rutas de identidad.

## 3. RBAC del driver y configuración del trabajo

Guarda el archivo como driver-rbac.yaml. Esta configuración base no crea PVC ni habilita otras funciones que requieran permisos adicionales; revisa esas funciones antes de añadir derechos.

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: spark-data-driver
  namespace: spark-jobs
rules:
- apiGroups:
  - ''
  resources:
  - pods
  - services
  - configmaps
  verbs:
  - create
  - get
  - list
  - watch
  - delete
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: spark-data-driver
  namespace: spark-jobs
subjects:
- kind: ServiceAccount
  name: spark-data-driver
  namespace: spark-jobs
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: spark-data-driver
```

Un Role concede derechos sobre los recursos enumerados dentro de su espacio de nombres, no solo sobre «los executors propios del driver». RBAC de Kubernetes no añade condiciones basadas en etiquetas de Pods a estas reglas. También se puede vincular un ClusterRole mediante un RoleBinding para limitar a ese espacio de nombres los permisos sobre recursos con ámbito de espacio de nombres. Evalúa las **reglas y el ámbito de la vinculación**, no solo el nombre del objeto.

Los permisos para crear Pods pueden combinarse con otra cuenta de servicio o acceso al host; por eso, un Role limitado a un espacio de nombres no constituye por sí solo un límite completo. Separa los dominios de confianza y usa Pod Security/admission, restricciones sobre especificaciones de Pod peligrosas, IAM y controles de red.
Deshabilitar el montaje automático del token de API es distinto de inyectar por separado un token de IRSA.

Guarda el archivo como job.properties y reemplaza el bucket y la región.

```properties
spark.kubernetes.namespace=spark-jobs
spark.kubernetes.authenticate.driver.serviceAccountName=spark-data-driver
spark.kubernetes.authenticate.executor.serviceAccountName=spark-data-executor
spark.hadoop.fs.s3a.aws.credentials.provider=software.amazon.awssdk.auth.credentials.WebIdentityTokenFileCredentialsProvider
spark.hadoop.fs.s3a.endpoint.region=ap-northeast-2
spark.eventLog.enabled=true
spark.eventLog.dir=s3a://my-spark-bucket/spark-events/
spark.eventLog.logStageExecutorMetrics=true
spark.metrics.conf.*.sink.prometheusServlet.class=org.apache.spark.metrics.sink.PrometheusServlet
spark.metrics.conf.*.sink.prometheusServlet.path=/metrics/prometheus
spark.ui.prometheus.enabled=true
spark.ui.port=4040
spark.driver.port=7078
spark.driver.blockManager.port=7079
spark.blockManager.port=7079
spark.port.maxRetries=0
spark.authenticate=true
spark.network.crypto.enabled=true
spark.network.crypto.cipher=AES/GCM/NoPadding
spark.network.crypto.authEngineVersion=2
spark.network.crypto.saslFallback=false
spark.io.encryption.enabled=true
```

`spark.authenticate` autentica las conexiones internas, no a los usuarios de la interfaz de usuario. En modo Kubernetes, los secretos generados por aplicación se propagan a los entornos de los executors y pueden quedar visibles para las identidades autorizadas a leer Pods. Revisa esos permisos de lectura y la alternativa de montar archivos Secret generados de forma segura. No guardes un secreto fijo de autenticación en las propiedades ni en Git.

La configuración de cifrado RPC está orientada a versiones actuales de Spark que sean compatibles entre sí; valida la compatibilidad con otros clientes/servicios shuffle. El cifrado de E/S cubre los datos locales temporales de Spark admitidos, no S3/EBS/KMS ni TLS de la interfaz. La interfaz necesita una ruta independiente de autenticación, autorización y acceso TLS.
## 4. Ingreso y envío por ejecución

Seleccionar solo la etiqueta del rol también permite los executors **de otros trabajos** del mismo espacio de nombres. Guarda lo siguiente como make-network-policy.py. Usa un ID de ejecución único, generado antes del envío, tanto en las etiquetas de los Pods como en las políticas. Reemplaza el espacio de nombres/la etiqueta de Pod de Prometheus por los valores de la instalación real.

```python
import json
import os
import re
from pathlib import Path

run_id = os.environ["SPARK_RUN_ID"]
if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,38}[a-z0-9])?", run_id):
    raise ValueError("SPARK_RUN_ID must be a lowercase DNS label, at most 40 characters")
monitor_ns = os.environ.get("PROMETHEUS_NAMESPACE", "monitoring")
def peer(role):
    return {"podSelector": {"matchLabels": {"docs-job": run_id, "spark-role": role}}}
def policy(role, ingress):
    return {
        "apiVersion": "networking.k8s.io/v1", "kind": "NetworkPolicy",
        "metadata": {"name": run_id + "-" + role, "namespace": "spark-jobs"},
        "spec": {"podSelector": {"matchLabels": {"docs-job": run_id, "spark-role": role}},
                 "policyTypes": ["Ingress"], "ingress": ingress}}
driver = policy("driver", [
    {"from": [peer("executor")], "ports": [{"protocol": "TCP", "port": 7078}, {"protocol": "TCP", "port": 7079}]},
    {"from": [{"namespaceSelector": {"matchLabels": {"kubernetes.io/metadata.name": monitor_ns}},
               "podSelector": {"matchLabels": {"app.kubernetes.io/name": "prometheus"}}}],
     "ports": [{"protocol": "TCP", "port": 4040}]},
])
executor = policy("executor", [
    {"from": [peer("driver"), peer("executor")], "ports": [{"protocol": "TCP", "port": 7079}]},
])
Path("job-networkpolicy.json").write_text(json.dumps({"apiVersion": "v1", "kind": "List", "items": [driver, executor]}, indent=2) + "\n")
```

Después de revisar/aplicar las cuentas de servicio y RBAC, envía la política y el trabajo con el mismo ID de ejecución.

```bash
kubectl apply -f serviceaccounts.yaml
kubectl apply -f driver-rbac.yaml
```

```bash
# Set SPARK_S3_IMAGE to the built/published image accessible to your EKS nodes.
: "${SPARK_S3_IMAGE:?Set the tested Spark S3 image reference}"
export SPARK_RUN_ID="spark-$(python3 -c 'import uuid; print(uuid.uuid4().hex[:12])')"
# Set this to the actual namespace/Pod labels of the Prometheus collector.
export PROMETHEUS_NAMESPACE=monitoring
python3 make-network-policy.py
kubectl apply -f job-networkpolicy.json

K8S_API_SERVER="$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}')"
: "${K8S_API_SERVER:?Select the intended context}"
spark-submit \
  --master "k8s://${K8S_API_SERVER}" --deploy-mode cluster \
  --name "$SPARK_RUN_ID" --properties-file job.properties \
  --conf "spark.kubernetes.container.image=$SPARK_S3_IMAGE" \
  --conf "spark.kubernetes.driver.label.docs-job=$SPARK_RUN_ID" \
  --conf "spark.kubernetes.executor.label.docs-job=$SPARK_RUN_ID" \
  --conf spark.executor.instances=2 \
  --conf spark.driver.memory=1g --conf spark.executor.memory=1g \
  --class org.apache.spark.examples.SparkPi \
  local:///opt/spark/examples/jars/spark-examples.jar 10
```

Este es un **ejemplo de ingreso**. Para restringir también el tráfico de salida, hay que incluir además DNS, la API de Kubernetes, S3/STS o los endpoints de credenciales/EKS Auth y las rutas a las fuentes de datos reales. Se requiere un CNI que aplique las políticas, que además se acumulan. Considera otras políticas de permiso, el comportamiento del nodo/hostNetwork y la posibilidad de que los creadores de Pods falsifiquen etiquetas.
Las etiquetas no son identidades de trabajos criptográficas ni garantizan protección contra todos los bypasses.

Los puertos 7078/7079 son fijos y port.maxRetries=0 impide cambiar a otro puerto después de una colisión. Si el puerto está ocupado, el inicio falla. Si se usan, diseña acceso separado para Spark Connect, complementos adicionales o un exportador JMX.

## 5. Prometheus: distintos endpoints

Las métricas del chart de la Parte 2 describen al operator en sí; no instala automáticamente un agente JMX en cada JVM de Spark. Un agente Java se ejecuta dentro de su JVM, no como un proceso adicional separado.

| Ruta de recopilación | Significado |
| --- | --- |
| Driver /metrics/prometheus/ | Registro Dropwizard de PrometheusServlet; documentado como experimental |
| Driver /metrics/executors/prometheus/ | Agregados de executors recopilados por el driver |
| JmxSink + exportador JMX | MBeans de JVM y asignaciones del exportador seleccionados; requiere su JAR y configuración |

Los executors no tienen cada uno su propia interfaz de Spark. No se garantiza que las series, los nombres, las etiquetas ni las unidades disponibles sean idénticos en las rutas servlet/JMX.
`spark.ui.prometheus.enabled` controla el endpoint agregado de executors y su valor predeterminado es true. El endpoint Dropwizard del driver usa la configuración independiente del sink indicada anteriormente.

Guarda el archivo como podmonitor.yaml. Sus etiquetas de metadatos y su espacio de nombres deben coincidir con los valores reales de podMonitorSelector/podMonitorNamespaceSelector de Prometheus. También deben concordar RBAC para descubrir los collectors y las reglas de ingreso anteriores.

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PodMonitor
metadata:
  name: spark-drivers
  namespace: monitoring
  labels:
    release: monitoring
spec:
  namespaceSelector:
    matchNames:
    - spark-jobs
  selector:
    matchLabels:
      spark-role: driver
    matchExpressions:
    - key: docs-job
      operator: Exists
  podMetricsEndpoints:
  - port: spark-ui
    path: /metrics/prometheus/
    interval: 30s
  - port: spark-ui
    path: /metrics/executors/prometheus/
    interval: 30s
```

Comprueba que los destinos reales estén UP y que ambas rutas devuelvan las series esperadas. Los trabajos breves pueden finalizar entre dos consultas de scraping. La retención de métricas y los registros de eventos se complementan; antes de reutilizar un dashboard de Grafana, comprueba las series, etiquetas y unidades reales.
## 6. Inspeccionar los trabajos después de que terminen

Cuando se detiene la JVM del driver, su interfaz en vivo desaparece aunque el objeto Pod siga existiendo.
History Server reconstruye la interfaz a partir de **registros de eventos persistidos**, no de stdout/stderr, checkpoints de Structured Streaming, datos de salida ni copias de seguridad de recuperación. Los eventos que falten, se hayan eliminado, estén dañados, incompletos o no se hayan vaciado limitan la reconstrucción.
El costo de reproducirlos depende del volumen de registros y de la concurrencia; la compactación puede descartar eventos.
No des por sentado que siempre basta con una sola réplica pequeña.

Guárdalo como history-server.yaml y reemplaza la imagen, el bucket y la región. Montar un archivo no basta para cargarlo: el comando lo lee explícitamente mediante **--properties-file**.
`spark-class` se ejecuta en primer plano para gestionar el ciclo de vida del contenedor. La identidad de S3 es la cuenta independiente de solo lectura de History Server preparada anteriormente.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: spark-history-config
  namespace: spark-jobs
data:
  history.properties: 'spark.history.fs.logDirectory=s3a://my-spark-bucket/spark-events/

    spark.hadoop.fs.s3a.aws.credentials.provider=software.amazon.awssdk.auth.credentials.WebIdentityTokenFileCredentialsProvider

    spark.hadoop.fs.s3a.endpoint.region=ap-northeast-2

    spark.history.ui.port=18080

    spark.history.fs.cleaner.enabled=false

    '
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: spark-history
  namespace: spark-jobs
spec:
  replicas: 1
  selector:
    matchLabels:
      app: spark-history
  template:
    metadata:
      labels:
        app: spark-history
    spec:
      serviceAccountName: spark-data-history
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 185
        fsGroup: 185
      containers:
      - name: history
        image: registry.example.com/team/spark-s3:4.2.0
        command:
        - /opt/spark/bin/spark-class
        args:
        - org.apache.spark.deploy.history.HistoryServer
        - --properties-file
        - /etc/spark/history.properties
        ports:
        - name: http
          containerPort: 18080
        env:
        - name: SPARK_DAEMON_MEMORY
          value: 1g
        resources:
          requests:
            cpu: 250m
            memory: 1536Mi
          limits:
            cpu: '1'
            memory: 2Gi
        securityContext:
          allowPrivilegeEscalation: false
          capabilities:
            drop:
            - ALL
          seccompProfile:
            type: RuntimeDefault
        readinessProbe:
          httpGet:
            path: /
            port: http
          initialDelaySeconds: 10
          periodSeconds: 10
        volumeMounts:
        - name: config
          mountPath: /etc/spark
          readOnly: true
      volumes:
      - name: config
        configMap:
          name: spark-history-config
---
apiVersion: v1
kind: Service
metadata:
  name: spark-history
  namespace: spark-jobs
spec:
  type: ClusterIP
  selector:
    app: spark-history
  ports:
  - name: http
    port: 18080
    targetPort: http
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: spark-history-ingress
  namespace: spark-jobs
spec:
  podSelector:
    matchLabels:
      app: spark-history
  policyTypes:
  - Ingress
  ingress: []
```

```bash
# Replace the image, bucket, region and IAM role examples before applying.
kubectl apply -f history-server.yaml
kubectl -n spark-jobs rollout status deployment/spark-history --timeout=180s
kubectl -n spark-jobs logs deployment/spark-history
kubectl -n spark-jobs port-forward --address 127.0.0.1 service/spark-history 18080:18080
```

Inspecciona las aplicaciones mediante el puerto local 18080. El reenvío de puertos dura hasta que termina el comando y sirve como ruta de diagnóstico. Para el acceso operativo, usa una ruta TLS autenticada por separado. ClusterIP y la autenticación RPC de Spark no autentican a los usuarios de la interfaz.

Este ejemplo deshabilita el cleaner de History Server. Diseña por separado las políticas de ciclo de vida, retención y costo de S3; si habilitas el cleaner, revisa los permisos de eliminación, la retención y otros consumidores. Al limpiar los trabajos completados y sus NetworkPolicies, selecciona solo el ID de ejecución previsto.

## Validación operativa

Verifica en los Pods reales la identidad efectiva de AWS y los prefijos de S3 permitidos/denegados.
Prueba el acceso a History Server después de que termine el driver, los fallos de permisos/red, el comportamiento ante interrupciones/reintentos y la recuperación de datos. Dimensiona el driver/executors según el modelo de requests/limits y overhead de la Parte 4. Elige un ciclo de vida validado de envío directo, operator o EMR, y el modo client/cluster correspondiente; ni usar un operator ni usar el modo cluster es un requisito universal de producción por sí solo.

Esta revisión comprueba la construcción nativa del proveedor, los dos endpoints de métricas locales en vivo de Spark, la reproducción del registro de eventos después de terminar el trabajo y la semántica de YAML/políticas.
No incluye un despliegue en EKS, una prueba de permisos de S3, la creación/publicación de una imagen ni una prueba de comunicación con executors remotos.

- [Dependencias y credenciales S3A de Hadoop 3.5.0](https://hadoop.apache.org/docs/r3.5.0/hadoop-aws/tools/hadoop-aws/index.html)
- [Fábrica de proveedores de credenciales de Hadoop 3.5.0](https://github.com/apache/hadoop/blob/rel/release-3.5.0/hadoop-tools/hadoop-aws/src/main/java/org/apache/hadoop/fs/s3a/auth/CredentialProviderListFactory.java)
- [EKS IRSA](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
- [EKS Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html)
- [Monitoreo y History Server de Spark 4.2](https://spark.apache.org/docs/4.2.0/monitoring.html)
- [Configuración de Prometheus para executors de Spark](https://github.com/apache/spark/blob/v4.2.0/core/src/main/scala/org/apache/spark/internal/config/UI.scala)
- [Seguridad de Spark](https://spark.apache.org/docs/4.2.0/security.html)
- [Semántica de NetworkPolicy de Kubernetes](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Ámbito de RBAC de Kubernetes y RoleBinding](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)

[README](./README.md)

[Cuestionario](../../quizzes/data-on-eks/spark/05-best-practices-quiz.md)
