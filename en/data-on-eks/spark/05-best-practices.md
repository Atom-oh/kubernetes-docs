# Part 5: Best Practices and Security

> **Review baseline**: September 12, 2026 · upstream Spark 4.2.0 / Hadoop 3.5.0 / AWS SDK v2 2.35.4

## Scope

This chapter builds on Part 1's direct Kubernetes submission, covering temporary
S3 credentials, metrics/event logs, History Server, networking and RBAC. Use
Kubernetes 1.34+ for Spark 4.2 and compatible kubectl, with the spark-jobs namespace
and EKS access prepared. Operators and EMR require their own configuration and
permission paths.

Prepare administrator access for IRSA or Pod Identity, an existing S3 bucket and
roles, a registry and image-build tools. Apply the PodMonitor example only where
Prometheus Operator is installed. Account, bucket, image and region values below
are **examples to replace**. A configuration checklist alone does not establish
operational safety, recovery or performance.

## 1. Build a version-compatible S3A image

The reviewed Spark 4.2 distribution includes Hadoop client 3.5.0, but not all
additional S3A dependencies. Match hadoop-aws to the **same Hadoop version**.
The Maven-resolved runtime dependencies for 3.5.0 are:

| Artifact | Version |
| --- | --- |
| org.apache.hadoop:hadoop-aws | 3.5.0 |
| software.amazon.awssdk:bundle | 2.35.4 |
| software.amazon.s3.analyticsaccelerator:analyticsaccelerator-s3 | 1.3.1 |
| org.wildfly.openssl:wildfly-openssl | 2.2.5.Final |

Do not mix arbitrary old AWS SDK JARs or copy only hadoop-aws. This POM resolves
its runtime dependencies without recopying Hadoop common. Recheck bundled versions
for a different Spark image or EMR runtime.

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

Save as Dockerfile. The chosen image platform must match workload and History Server nodes.

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

Use the dependency-complete image for driver, executors and History Server.
--packages resolves dependencies through the submitter; it does not automatically
install them into a History Server launched with spark-class. Validate registry
access, image checks, compatibility and actual S3 reads/writes, then pin the
tested image digest for operations.

## 2. Distinguish IRSA from Pod Identity

For this Hadoop 3.5.0 / SDK v2 combination, use:

| Identity path | fs.s3a.aws.credentials.provider |
| --- | --- |
| IRSA | software.amazon.awssdk.auth.credentials.WebIdentityTokenFileCredentialsProvider |
| EKS Pod Identity | software.amazon.awssdk.auth.credentials.ContainerCredentialsProvider |

IRSA uses OIDC trust, a service-account annotation and a projected web-identity
token. Pod Identity uses an association and the Agent's container-credential path;
the IRSA annotation does not configure it. Do not blindly combine both paths.

The default S3A chain includes the container/instance credential wrapper, but not
the web-identity provider. The old com.amazonaws.auth.WebIdentityTokenCredentialsProvider
was not automatically mapped in this SDK-v2-only combination. Some other legacy
aliases are mapped, so this is not a claim that all old names always fail.
An explicit identity path also reduces unintended fallback to other credential
sources. Temporary credentials still require correct trust, permissions and networking.

Save this **IRSA example** as serviceaccounts.yaml. Replace the roles and first
configure trust for the cluster's OIDC provider, audience and exact namespace/
service-account subject. Executors and History Server do not receive the driver's
Kubernetes management permissions.

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

Separate data permissions by purpose:

- Driver: required input/output access and event-log writes under spark-events.
  Review S3A rename/multipart requirements and any KMS permissions.
- Executors: only the buckets/prefixes needed for actual data processing.
- History Server: list/read the event-log prefix and required KMS decryption.
  This example disables its cleaner, so it does not need deletion permission.

For Pod Identity, remove IRSA annotations and configure associations, role trust
and Agent/node EKS Auth permissions for these three service accounts. Also change
the properties below to ContainerCredentialsProvider. The IAM OIDC provider is
an IRSA prerequisite, not a universal prerequisite for every identity path.

## 3. Driver RBAC and job configuration

Save as driver-rbac.yaml. This baseline does not create PVCs or enable other
features requiring additional permissions; review those features before adding rights.

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

A Role grants rights to the listed resources within its namespace, not only to
“the driver's own executors.” Kubernetes RBAC does not add pod-label conditions to
these rules. A ClusterRole bound by a RoleBinding can also scope namespaced
resource permissions to that namespace. Assess the **rules and binding scope**,
not only the object's name.

Pod-creation rights can combine with another service account or host access, so a
namespaced Role alone is not a complete boundary. Separate trust domains and use
Pod Security/admission, dangerous-pod-spec restrictions, IAM and networking.
Disabling automatic API-token mounting is distinct from a separately injected
IRSA token.

Save as job.properties, replacing bucket and region.

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

spark.authenticate authenticates internal connections, not UI users. In Kubernetes
mode, generated per-application secrets are propagated to executor environments
and can be visible to identities allowed to read pods. Review pod-read permissions
and the alternative of securely generated, mounted Secret files. Do not commit a
fixed authentication secret in properties or Git.

The RPC encryption settings here target matching current Spark versions; validate
compatibility with other clients/shuffle services. IO encryption covers supported
Spark temporary local data, not S3/EBS/KMS or UI TLS. The UI needs a separate
authentication, authorization and TLS access path.

## 4. Per-run ingress and submission

Selecting only the role label also permits **other jobs' executors** in the same
namespace. Save this as make-network-policy.py. It uses a unique run ID, created
before submission, in both pod labels and policies. Replace the Prometheus
namespace/pod label with the actual installation values.

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

After reviewing/applying the service accounts and RBAC, submit the policy and job with the same run ID.

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

This is an **ingress example**. Restricting egress additionally requires DNS,
Kubernetes API, S3/STS or EKS Auth/credential endpoints and actual data-source
paths. An enforcing CNI is required and policies are additive. Consider other
allow policies, node/hostNetwork behavior and pod creators able to forge labels.
Labels are not cryptographic job identities or a guarantee against every bypass.

Ports 7078/7079 are fixed and port.maxRetries=0 prevents moving to another port
after a collision. A busy port makes startup fail. Design separate access for
Spark Connect, additional plugins or a JMX exporter if used.

## 5. Prometheus: different endpoints

Part 2's chart metrics describe the operator itself; it does not automatically
install a JMX agent into every Spark JVM. A Java agent runs inside its JVM,
not as a separate additional process.

| Collection path | Meaning |
| --- | --- |
| Driver /metrics/prometheus/ | PrometheusServlet's Dropwizard registry; documented as experimental |
| Driver /metrics/executors/prometheus/ | Executor aggregates collected by the driver |
| JmxSink + JMX exporter | Selected JVM MBeans/exporter mappings; requires its JAR and configuration |

Each executor does not get its own Spark UI. Available series, names, labels and
units are not guaranteed identical across these servlet/JMX paths.
spark.ui.prometheus.enabled controls the executor aggregate endpoint and defaults
to true. The driver Dropwizard endpoint uses the separate sink configuration above.

Save as podmonitor.yaml. Its metadata labels and namespace must match the real
Prometheus podMonitorSelector/podMonitorNamespaceSelector. Collector discovery
RBAC and the earlier ingress rules must also agree.

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

Verify actual targets are UP and both paths return the expected series. Short jobs
can finish between scrapes. Metrics retention and event logs complement each other;
check real series, labels and units before reusing a Grafana dashboard.

## 6. Inspect jobs after completion

When the driver JVM stops, its live UI is gone even if the pod object remains.
History Server reconstructs a UI from **persisted event logs**, not stdout/stderr,
Structured Streaming checkpoints, output data or recovery backups. Missing,
deleted, corrupt, incomplete or unflushed events limit reconstruction.
Replay cost depends on log volume and concurrency; compaction can discard events.
Do not assume one small replica always suffices.

Save as history-server.yaml, replacing image, bucket and region. Mounting a file
alone does not load it: the command explicitly reads it through **--properties-file**.
spark-class runs in the foreground for container lifecycle management. The S3
identity is the separate read-only History Server account prepared above.

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

Inspect applications through local port 18080. Port-forwarding lasts until the
command ends and is a diagnostic path. Use a separately authenticated TLS path
for operational access. ClusterIP and Spark RPC authentication do not authenticate
UI users.

This example disables the History Server cleaner. Design S3 lifecycle, retention
and cost policies separately; enabling the cleaner requires review of deletion
permissions, retention and other consumers. Select only the intended run ID when
cleaning up completed jobs and their NetworkPolicies.

## Operational validation

Verify effective AWS identity and allowed/denied S3 prefixes in actual pods.
Test History Server access after driver termination, permission/network failures,
interruption/retry behavior and data recovery. Size driver/executors using Part 4's
request/limit and overhead model. Choose a validated direct-submission, operator
or EMR lifecycle and appropriate client/cluster mode; an operator or cluster mode
alone is not a universal production prerequisite.

This review checks native provider construction, both live local Spark metrics
endpoints, event-log replay after job termination, and YAML/policy semantics.
It does not include an EKS deployment, S3 permission test, image build/publication
or remote-executor communication test.


- [Hadoop 3.5.0 S3A dependencies and credentials](https://hadoop.apache.org/docs/r3.5.0/hadoop-aws/tools/hadoop-aws/index.html)
- [Hadoop 3.5.0 credential-provider factory](https://github.com/apache/hadoop/blob/rel/release-3.5.0/hadoop-tools/hadoop-aws/src/main/java/org/apache/hadoop/fs/s3a/auth/CredentialProviderListFactory.java)
- [EKS IRSA](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
- [EKS Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html)
- [Spark 4.2 monitoring and History Server](https://spark.apache.org/docs/4.2.0/monitoring.html)
- [Spark executor Prometheus configuration](https://github.com/apache/spark/blob/v4.2.0/core/src/main/scala/org/apache/spark/internal/config/UI.scala)
- [Spark security](https://spark.apache.org/docs/4.2.0/security.html)
- [Kubernetes NetworkPolicy semantics](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Kubernetes RBAC and RoleBinding scope](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)

[README](./README.md)

[Quiz](../../quizzes/data-on-eks/spark/05-best-practices-quiz.md)
