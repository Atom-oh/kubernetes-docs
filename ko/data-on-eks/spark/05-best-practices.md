# Part 5: 모범 사례와 보안

> **검토 기준**: 2026년 9월 12일 · upstream Spark 4.2.0 / Hadoop 3.5.0 / AWS SDK v2 2.35.4

## 실습 범위

Part 1의 직접 Kubernetes 제출을 기준으로 S3 임시 자격 증명, 메트릭과 event log,
History Server, 통신·RBAC를 구성합니다. Spark 4.2에 맞는 Kubernetes 1.34+ 및
호환 kubectl을 사용합니다. `spark-jobs` namespace와 EKS 접근이 준비되어 있어야 합니다.
Operator·EMR 제출은 해당 경로의 설정 변환·권한을 추가로 확인합니다.

IRSA 또는 Pod Identity를 준비할 관리자 권한, 기존 S3 bucket·역할, 이미지 registry와
빌드 도구가 필요합니다. Prometheus Operator가 설치된 환경에서만 PodMonitor 예제를
적용합니다. 아래 계정·bucket·image·region은 **교체할 예시 값**입니다.
설정 목록을 충족하는 것만으로 운영 안전성·복구·성능이 보장되지는 않습니다.

## 1. 버전이 맞는 S3A 이미지

검증한 Spark 4.2 배포본은 Hadoop client 3.5.0을 포함하지만 S3A 실행에 필요한
추가 의존성이 전부 들어 있는 것은 아닙니다. hadoop-aws는 Hadoop client와
**같은 버전**을 사용합니다. Maven으로 확인한 3.5.0 런타임 의존성은 다음과 같습니다.

| Artifact | Version |
| --- | --- |
| org.apache.hadoop:hadoop-aws | 3.5.0 |
| software.amazon.awssdk:bundle | 2.35.4 |
| software.amazon.s3.analyticsaccelerator:analyticsaccelerator-s3 | 1.3.1 |
| org.wildfly.openssl:wildfly-openssl | 2.2.5.Final |

구버전 AWS SDK JAR를 임의로 섞거나 hadoop-aws 하나만 추가하지 않습니다.
아래 POM은 Hadoop common을 다시 복사하지 않고 hadoop-aws의 런타임 의존성을
해결합니다. 다른 Spark 이미지·EMR runtime에는 해당 번들의 버전을 다시 확인합니다.

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

Dockerfile로 저장합니다. 선택한 이미지 platform이 작업/History Server 노드와 맞아야 합니다.

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

Driver·executor·History Server 모두 이 의존성을 포함한 이미지를 사용합니다.
--packages는 제출자가 의존성을 해결하는 경로이며, spark-class로 시작한 History
Server에 그 JAR가 자동 설치되는 것은 아닙니다. Registry 접근·이미지 검사·실제 S3
읽기/쓰기와 호환성을 확인한 뒤 고정된 이미지 digest로 운영합니다.

## 2. IRSA와 Pod Identity를 구분

Hadoop 3.5.0의 이 SDK v2 조합에서는 다음 provider를 사용합니다.

| 방식 | fs.s3a.aws.credentials.provider |
| --- | --- |
| IRSA | software.amazon.awssdk.auth.credentials.WebIdentityTokenFileCredentialsProvider |
| EKS Pod Identity | software.amazon.awssdk.auth.credentials.ContainerCredentialsProvider |

IRSA는 OIDC trust·service account annotation·projected web-identity token을
사용합니다. Pod Identity는 association과 Agent의 container-credential 경로를
사용하며 IRSA annotation으로 연결되지 않습니다. 두 방식을 무조건 함께 적용하지 않습니다.

기본 S3A provider chain에는 container/instance credential wrapper가 있지만
web-identity provider는 없습니다. 이전 com.amazonaws.auth.WebIdentityTokenCredentialsProvider는
이 SDK v2-only 조합에서 자동 변환되지 않았습니다. 일부 다른 구버전 alias는
변환되므로 “모든 구버전 이름이 무조건 실패한다”는 뜻도 아닙니다.
선택한 identity 경로를 명시하면 뜻하지 않은 다른 credential source로의 fallback도
줄일 수 있습니다. 임시 자격 증명도 자격 증명이며, 역할 trust·권한·네트워크를 검증합니다.

아래는 **IRSA 예제** serviceaccounts.yaml입니다. 실제 역할로 교체하고
cluster OIDC provider, audience, 정확한 namespace/service-account subject에
맞는 trust를 먼저 구성합니다. Executor·History Server에는 driver의 API 관리
권한을 주지 않습니다.

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

권한은 용도에 맞춰 분리합니다.

- Driver: 필요한 입력·출력 및 spark-events prefix의 event-log 쓰기. S3A가 rename/
  multipart 작업에 요구하는 권한과 KMS 사용 여부도 확인합니다.
- Executor: 실제 데이터 입출력에 필요한 bucket/prefix만 허용합니다.
- History Server: event-log prefix 읽기·목록과 필요한 KMS decrypt. 이 예제는
  cleaner를 끄므로 History Server에 삭제 권한을 추가할 필요가 없습니다.

Pod Identity를 선택한다면 IRSA annotation을 제거하고 이 세 service account에
맞는 association·역할 trust·Agent/노드 EKS Auth 권한을 구성합니다. 아래 properties의
provider도 ContainerCredentialsProvider로 바꿉니다. OIDC provider는 IRSA 경로의
전제 조건이며 모든 identity 방식에 공통으로 필요한 것은 아닙니다.

## 3. Driver RBAC와 실행 설정

driver-rbac.yaml로 저장합니다. 이 예제는 PVC 생성 등 추가 기능을 쓰지 않는
기본 경로입니다. 새 기능이 필요한 권한은 해당 기능을 검증하며 추가합니다.

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

Role은 namespace 안의 해당 리소스에 권한을 주며 “자기 executor만”으로 제한하지
않습니다. Kubernetes RBAC는 이 규칙에 Pod label 조건을 붙이지 않습니다.
ClusterRole도 RoleBinding으로 바인딩하면 namespaced 리소스 권한을 그 namespace에
한정할 수 있습니다. 문제는 이름 자체보다 **실제 규칙과 binding 범위**입니다.

Pod 생성 권한은 같은 namespace의 다른 service account 사용이나 host 접근과
결합될 수 있으므로 namespace Role 하나가 완전한 보안 경계는 아닙니다.
신뢰 경계를 나누고 Pod Security/admission, 위험한 Pod spec 제한, IAM, 네트워크를
함께 적용합니다. 자동 API token mount를 꺼도 별도로 주입되는 IRSA token과는
구분해야 합니다.

job.properties로 저장하고 bucket·region을 실제 값으로 바꿉니다.

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

Spark.authenticate는 내부 연결 인증이며 UI 사용자 인증이 아닙니다. Kubernetes
모드에서 생성된 애플리케이션별 secret은 executor 환경으로 전달되므로 Pod를 읽을
수 있는 주체가 볼 수 있습니다. 안전하게 생성한 Secret 파일을 직접 mount하는
대안과 Pod 조회 권한도 검토합니다. 고정 secret 값을 properties/Git에 넣지 않습니다.

여기의 RPC 암호화 설정은 같은 최신 Spark 버전끼리 쓰는 예제입니다. 다른
shuffle/클라이언트와 섞으면 호환성을 확인합니다. IO encryption은 Spark의 지원되는
로컬 임시 데이터에 적용되며 S3/EBS/KMS·UI TLS를 대신하지 않습니다.
UI에는 별도의 인증·인가·TLS 접근 경로가 필요합니다.

## 4. 작업별 ingress와 실제 제출

역할 label만 선택하면 같은 namespace의 **다른 작업 executor도** 통과합니다.
아래 make-network-policy.py는 제출 전에 만든 고유 run ID를 두 Pod label과
정책에 같이 사용합니다. Prometheus namespace·Pod label은 실제 설치 값으로 바꿉니다.

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

ServiceAccount와 RBAC 파일을 검토·적용한 뒤 같은 run ID로 정책과 작업을 제출합니다.

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

이 정책은 **ingress 예제**입니다. Egress를 제한하려면 DNS, Kubernetes API,
S3/STS 또는 EKS Auth/credential endpoint, 데이터 소스 등의 실제 경로를 허용해야
합니다. NetworkPolicy를 집행하는 CNI가 필요하며 정책은 합산됩니다. 다른 allow
정책, node/hostNetwork 동작, label을 위조할 수 있는 Pod 생성 권한까지 고려합니다.
이를 암호학적인 작업 ID나 모든 우회 경로를 막는 경계로 해석하지 않습니다.

7078/7079를 고정하고 port.maxRetries=0으로 충돌 시 다른 포트로 이동하지 않게
했습니다. 포트가 사용 중이면 시작이 실패합니다. Spark Connect·추가 plugin·JMX
exporter가 필요하면 해당 endpoint를 따로 설계합니다.

## 5. Prometheus: 서로 다른 endpoint

Part 2의 chart 기본 메트릭은 Operator 자체 메트릭이며 모든 Spark JVM에 JMX agent를
자동 설치하지 않습니다. Java agent는 같은 JVM 안에서 실행되며 별도 프로세스가
하나 더 생긴다는 설명도 부정확합니다.

| 수집 방식 | 의미 |
| --- | --- |
| Driver /metrics/prometheus/ | PrometheusServlet의 Dropwizard registry; 문서상 experimental |
| Driver /metrics/executors/prometheus/ | Driver가 모은 executor 집계 메트릭 |
| JmxSink + JMX exporter | 선택한 JVM MBean과 exporter mapping; 별도 JAR·설정 필요 |

Executor마다 Spark UI가 생기는 것은 아닙니다. 두 servlet/JMX 경로의 항목·이름·
label·단위가 항상 같은 것도 아닙니다. spark.ui.prometheus.enabled는 executor
집계 endpoint 설정이며 기본값은 true입니다. Driver Dropwizard endpoint는 앞의
별도 sink 설정을 사용합니다.

podmonitor.yaml 예제입니다. metadata label과 namespace가 실제 Prometheus의
podMonitorSelector/podMonitorNamespaceSelector에 포함되어야 하며, collector의
discovery RBAC와 앞의 ingress 조건도 맞아야 합니다.

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

실제 targets가 UP이고 두 path에서 예상 series가 오는지 확인합니다. 짧은 작업은
scrape 사이에 끝날 수 있습니다. 메트릭 보존과 event log는 서로 보완합니다.
기존 Grafana dashboard를 쓰려면 실제 series·label·단위를 대조합니다.

## 6. 종료 후 History Server 조회

Driver JVM이 끝나면 Pod 객체가 남아 있어도 live UI는 서비스되지 않습니다.
History Server는 **저장된 event log**로 UI를 재구성하며 실행 stdout/stderr,
Structured Streaming checkpoint, 출력 데이터 또는 복구용 백업과는 다릅니다.
Event log가 없거나 삭제·손상·미완성·미flush 상태면 모든 정보를 복원할 수 없습니다.
재생 비용은 로그량·동시 사용자에 따라 달라지고 compaction은 일부 이벤트를 버릴
수 있으므로 하나의 작은 replica가 항상 충분하다고 가정하지 않습니다.

history-server.yaml로 저장합니다. 이미지·bucket·region을 교체합니다.
설정 파일을 mount하는 것만으로는 부족하며 아래 명령이 **--properties-file로
그 파일을 읽는 것**을 확인합니다. spark-class를 foreground로 실행하여 container
수명주기와 연결합니다. S3 role은 앞의 읽기 전용 History Server ID입니다.

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

로컬 브라우저의 18080 포트에서 작업을 확인합니다. Port-forward는 확인용이며
명령을 종료하면 연결도 끝납니다. 운영 접근은 인증·TLS를 갖춘 별도 경로로 구성합니다.
ClusterIP나 RPC 인증 설정만으로 UI 사용자 인증이 제공되지는 않습니다.

이 예제는 History Server의 cleaner를 껐습니다. S3 lifecycle/보존·비용 정책은
별도로 설계하며, cleaner를 켜면 삭제 권한·보존 기간과 다른 consumer 영향을 검토합니다.
새 실행 후 이전 작업·NetworkPolicy를 정리할 때는 해당 run ID만 선택합니다.

## 운영 검증 범위

실제 Pod에서 유효 AWS ID와 허용/거부할 S3 prefix를 확인하고, driver가 종료된 뒤
History Server 재조회, 권한 오류·네트워크 차단·중단/재시도·데이터 복구를 시험합니다.
Driver/Executor 리소스는 Part 4의 실제 request/limit·overhead 기준으로 측정합니다.
검증된 직접 제출·Operator·EMR 및 client/cluster 방식 중 운영 요구에 맞는 것을
선택하며 Operator나 cluster mode 하나만을 production의 필수 조건으로 두지 않습니다.

이번 검토는 native provider 생성, 로컬 Spark의 실제 두 메트릭 endpoint,
종료 후 로컬 event log 재생과 YAML/정책 의미를 확인했습니다.
실제 EKS 배포·S3 권한·이미지 빌드/게시·원격 executor 통신 시험은 포함하지 않습니다.


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
