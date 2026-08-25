# Part 5: 모범 사례와 보안

> **마지막 업데이트**: 2026년 7월 15일

지금까지 이 5부작 시리즈에서는 Spark on Kubernetes의 핵심 개념(Part 1), Spark Operator를 이용한 선언적 배포/운영(Part 2), 매니지드 대안인 Amazon EMR on EKS(Part 3), 드라이버/Executor 리소스 사이징을 포함한 성능·비용 튜닝(Part 4)을 다뤘습니다. 이번 마지막 문서에서는 Spark on EKS 파이프라인을 실제 프로덕션에 투입하기 전에 마무리해야 할 항목들을 정리합니다. 정적 자격 증명 없이 안전하게 S3에 접근하는 방법, 드라이버 Pod가 사라진 뒤에도 유지되는 관찰 가능성(observability), 리소스 사이징 철학의 요약, 그리고 IAM 외의 보안 강화 방법까지 다룹니다.

## 실습 환경 준비

이 문서의 예제를 따라 하려면 다음이 필요합니다.

* kubectl v1.30 이상, 정상 동작하는 Amazon EKS 클러스터에 연결된 상태
* 클러스터에 활성화된 IAM OIDC 공급자 (IRSA 사용을 위한 필수 조건)
* Spark 이벤트 로그/체크포인트 데이터를 저장할 S3 버킷, 그리고 IAM 역할/정책을 생성할 수 있는 권한
* Spark History Server를 매니페스트 대신 Helm 차트로 배포하려는 경우 Helm 3
* 아래에서 다루는 메트릭 엔드포인트를 실제로 스크래핑하고 시각화하려는 경우에만 필요한 Prometheus/Grafana 스택(예: `kube-prometheus-stack` 차트)

## 1. IRSA를 이용한 안전한 S3 접근

드라이버와 Executor Pod는 입력 데이터 읽기, 출력 데이터 쓰기, 그리고 (Part 4와 아래에서 다시 언급할) 체크포인트/이벤트 로그 기록 등의 이유로 S3와 자주 통신합니다. EKS에서 이를 프로덕션 수준으로 안전하게 처리하는 방법은 **IAM Roles for Service Accounts(IRSA)** 입니다. 드라이버/Executor Pod가 사용하는 Kubernetes ServiceAccount를 IAM 역할에 바인딩하고, Spark의 Hadoop S3A 커넥터가 이 바인딩으로부터 자동으로 자격 증명을 받아오도록 설정하는 방식입니다. Secret이나 ConfigMap, 컨테이너 이미지 어디에도 정적인 AWS Access Key를 둘 필요가 없습니다.

S3A 커넥터는 기본적으로 이렇게 동작하지 않으므로, Pod에 프로젝션된 웹 아이덴티티 토큰을 임시 AWS 자격 증명으로 교환하는 방법을 아는 자격 증명 공급자를 명시적으로 지정해야 합니다.

```properties
spark.hadoop.fs.s3a.aws.credentials.provider=com.amazonaws.auth.WebIdentityTokenCredentialsProvider
```

`WebIdentityTokenCredentialsProvider`는 EKS Pod Identity 웹훅이 (ServiceAccount에 올바른 어노테이션이 있을 경우) Pod에 자동으로 주입한 웹 아이덴티티 토큰을 읽어, 내부적으로 STS `AssumeRoleWithWebIdentity`를 호출하고 만료 시점에 맞춰 임시 자격 증명을 자동으로 갱신합니다.

이를 종합하면 드라이버/Executor용 ServiceAccount는 다음과 같은 형태가 됩니다.

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: spark-s3-sa
  namespace: spark-jobs
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/spark-s3-access
```

```bash
spark-submit \
  --master k8s://https://<EKS_API_SERVER_ENDPOINT>:443 \
  --deploy-mode cluster \
  --conf spark.kubernetes.namespace=spark-jobs \
  --conf spark.kubernetes.authenticate.driver.serviceAccountName=spark-s3-sa \
  --conf spark.kubernetes.authenticate.executor.serviceAccountName=spark-s3-sa \
  --conf spark.hadoop.fs.s3a.aws.credentials.provider=com.amazonaws.auth.WebIdentityTokenCredentialsProvider \
  --conf spark.hadoop.fs.s3a.endpoint.region=us-east-1 \
  local:///opt/spark/jobs/etl-job.jar
```

위 예시의 `spark-s3-access` IAM 역할 자체는 클러스터의 OIDC 공급자와 특정 네임스페이스/ServiceAccount 주체로 신뢰 관계(trust policy)를 한정하고, 권한 정책도 `s3:*` on `*` 같은 포괄적인 권한이 아니라 해당 작업이 실제로 필요로 하는 버킷·프리픽스로만 좁혀야 합니다.

## 2. 관찰 가능성: Prometheus 메트릭을 얻는 두 가지 방법

Part 2에서 다룬 Spark Operator의 Helm 차트는 기본적으로 예전 방식을 사용합니다. Spark 내부의 `JmxSink`가 JMX로 메트릭을 노출하고, 이를 JVM에 붙인 별도의 **JMX Prometheus Exporter** 자바 에이전트(`-javaagent:...jmx_prometheus_javaagent.jar`)가 스크래핑해 Prometheus가 읽을 수 있는 HTTP 엔드포인트로 변환하는 방식입니다. 이 방식은 잘 동작하고 이미 만들어진 Grafana 대시보드 생태계도 풍부하지만, 이미지에 추가 JAR을 넣고 에이전트 설정 파일을 관리해야 하며 JVM마다 프로세스가 하나 더 붙는다는 부담이 있습니다.

Spark 3.0부터는 Spark 자체에 내장된, 더 가벼운 대안인 네이티브 **`PrometheusServlet`**이 제공됩니다. Spark가 이미 사용하는 UI 포트에서 Prometheus 텍스트 형식으로 메트릭을 바로 노출하므로, 외부 JAR도 별도 에이전트도 필요 없습니다.

```properties
# metrics.properties
*.sink.prometheusServlet.class=org.apache.spark.metrics.sink.PrometheusServlet
*.sink.prometheusServlet.path=/metrics/prometheus
master.sink.prometheusServlet.path=/metrics/master/prometheus
applications.sink.prometheusServlet.path=/metrics/applications/prometheus
```

```bash
spark-submit \
  --conf spark.metrics.conf=/opt/spark/conf/metrics.properties \
  ...
```

(`metrics.properties`는 보통 `ConfigMap`을 통해 드라이버/Executor Pod에 마운트합니다.)

**어느 쪽을 선택할지:**

- **`PrometheusServlet`** — 별도 에이전트/JAR이 필요 없어 운영 부담이 적고, 버전 관리해야 할 대상이 하나 줄어듭니다. JMX Exporter의 대시보드 생태계에 아직 의존하고 있지 않은 신규 파이프라인이라면 기본 선택지로 삼기 좋습니다.
- **JmxSink + JMX Prometheus Exporter** — Part 2에서 다룬 Spark Operator의 기본 차트 구성을 이미 쓰고 있다면, 또는 JMX Exporter의 메트릭 네이밍을 기준으로 만들어진 훨씬 방대하고 성숙한 커뮤니티 Grafana 대시보드를 그대로 활용하고 싶다면 유지할 가치가 있습니다.

두 방식 모두 측정 대상은 같습니다(Executor 태스크 수, 셔플 읽기/쓰기, JVM GC 등 Spark 자체의 메트릭). 차이는 전달 방식과 패키징에 있을 뿐입니다.

## 3. Spark History Server로 이미 끝난 작업 디버깅하기

Part 1에서 드라이버 Pod가 스스로 스케줄링을 수행한다는 점을 다뤘는데, 이는 곧 라이브 Spark UI도 그 드라이버 Pod 안에서만 존재한다는 뜻입니다. 작업이 끝나거나(또는 실패하거나) 나면 Kubernetes는 결국 그 Pod를 회수하고, UI도 함께 사라집니다. "지난밤 작업이 왜 느렸는지" 물어보고 싶어도 드라이버 Pod가 이미 없어졌다면 확인할 라이브 UI 자체가 없는 것입니다.

**Spark History Server**는 살아있는 드라이버에 접속하는 대신 저장된 이벤트 로그를 읽어 이 문제를 해결합니다. 모든 작업에서 이벤트 로깅을 활성화하고, (섹션 1의 IRSA 설정을 그대로 사용해) S3에 기록하도록 합니다.

```properties
spark.eventLog.enabled=true
spark.eventLog.dir=s3a://my-spark-bucket/spark-events/
```

그리고 같은 위치를 바라보는 History Server 인스턴스를 실행합니다. 보통 EKS 위에서 항상 켜져 있는 작은 `Deployment` 하나로 충분합니다.

```properties
# spark-history-server.conf, History Server Pod에 마운트
spark.history.fs.logDirectory=s3a://my-spark-bucket/spark-events/
spark.hadoop.fs.s3a.aws.credentials.provider=com.amazonaws.auth.WebIdentityTokenCredentialsProvider
```

History Server Pod도 같은 S3 버킷을 읽어야 하므로 드라이버/Executor와 동일한 방식의 IRSA 바인딩 ServiceAccount가 필요합니다. 실행되고 나면 History Server는 주기적으로 이벤트 로그 디렉터리를 다시 스캔해, 해당 작업의 드라이버 Pod가 남아 있는지와 무관하게 완료된 모든 작업에 대해 스테이지, SQL 실행 계획, Executor 타임라인 등을 재구성한 UI로 제공합니다. 덕분에 "이미 끝난 작업을 디버깅한다"는 문제가 "UI가 이미 사라져서 불가능"에서 "History Server를 열어 해당 Application ID를 찾는다"로 바뀝니다.

## 4. 리소스 사이징: 짧은 요약

자세한 내용은 Part 4에서 다뤘지만, 프로덕션에 들어가기 전에 다시 한번 원칙을 짚어볼 필요가 있습니다. **드라이버와 Executor Pod는 서로 다른 목표를 위해 사이징합니다.** 드라이버는 대량의 데이터 처리 자체를 수행하지 않고 작업을 조율하고 태스크 상태를 추적하며 스케줄링을 결정하는 역할을 하므로, 드라이버 사이징은 *안정성*을 우선합니다. 드라이버 자체가 병목이 되거나, 더 나쁘게는 OOMKilled로 죽어 작업 전체를 함께 끌고 내려가지 않을 정도의 메모리·CPU 여유를 확보하는 것이 목표입니다. 반면 실제 작업이 이루어지는 곳은 Executor이므로, Executor 사이징(`spark.executor.memory`, `spark.executor.cores` 및 이를 매핑한 Kubernetes `resources.requests`/`resources.limits`, Part 1에서 다룬 내용)은 해당 작업의 실제 셔플 양과 태스크당 메모리 사용량을 기준으로 *처리량*에 맞춰 튜닝합니다.

여기에도 모든 작업에 들어맞는 만능 숫자 기본값은 없습니다. 다른 팀의 `spark-submit` 옵션을 그대로 복사하는 대신, 실제 워크로드를 현실적인 데이터 규모로 벤치마킹해서 값을 도출해야 합니다.

## 5. IRSA를 넘어서는 보안

IRSA는 Pod가 클러스터 *바깥*(AWS)에서 할 수 있는 일을 제한합니다. 클러스터 *안*에서 Pod가 할 수 있는 일을 제한하는 것은 다음 두 가지입니다.

### 네트워크 정책(Network Policy)

기본 설정에서는 (CNI의 기본 동작에 따라) 같은 네임스페이스나 클러스터의 어떤 Pod든 Spark 드라이버·Executor Pod의 어떤 포트로도 접근할 수 있습니다. 드라이버-Executor, Executor-Executor 간 통신에 실제로 필요한 포트는 소수의 고정된 포트뿐이므로, 포트를 명시적으로 고정하고 트래픽을 그 포트로만 제한해야 합니다.

```properties
spark.driver.port=7078
spark.driver.blockManager.port=7079
spark.blockManager.port=7079
```

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: spark-driver-executor-only
  namespace: spark-jobs
spec:
  podSelector:
    matchLabels:
      spark-role: driver
  policyTypes:
    - Ingress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              spark-role: executor
      ports:
        - protocol: TCP
          port: 7078
        - protocol: TCP
          port: 7079
```

Executor Pod에도 `spark-role: driver`, `spark-role: executor` 피어를 블록 매니저 포트로 한정한 대응 정책을 걸어두면, 해당 작업의 드라이버/Executor Pod가 아닌 어떤 대상도 이 포트에 접근할 수 없게 됩니다.

### 드라이버 ServiceAccount에 대한 최소 권한 RBAC

드라이버 Pod는 Kubernetes API를 직접 호출해 자신의 Executor Pod를 생성·관리합니다(Part 1). 즉 드라이버의 ServiceAccount에는 어느 정도의 Pod 관리 권한이 필요합니다. 여기서 흔히 하는 실수는 이 권한을 클러스터 전체 범위로 부여하거나, 드라이버가 실제로 쓰지 않는 verb까지 함께 부여하는 것입니다. 필요한 만큼만, 드라이버가 속한 네임스페이스로만 범위를 좁혀야 합니다.

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: spark-driver-role
  namespace: spark-jobs
rules:
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["create", "get", "list", "watch", "delete"]
  - apiGroups: [""]
    resources: ["pods/log"]
    verbs: ["get"]
  - apiGroups: [""]
    resources: ["services", "configmaps"]
    verbs: ["create", "get", "list", "watch", "delete"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: spark-driver-rolebinding
  namespace: spark-jobs
subjects:
  - kind: ServiceAccount
    name: spark-s3-sa
    namespace: spark-jobs
roleRef:
  kind: Role
  name: spark-driver-role
  apiGroup: rbac.authorization.k8s.io
```

`ClusterRole`이 아니라 네임스페이스로 범위를 한정한 `Role`을 사용하고, verb도 드라이버가 실제로 하는 일(자신의 Executor Pod 생성/조회/watch/삭제, 로그 조회, Executor 디스커버리용 헤드리스 서비스·ConfigMap 관리)로만 제한하면, 드라이버 Pod가 침해되거나 오작동하더라도 영향 범위가 자신의 네임스페이스로 한정됩니다.

## 6. 체크리스트

이 딥다이브 시리즈(Part 1~5)에서 다룬 프로덕션 준비 핵심 항목을 정리하면 다음과 같습니다.

- [ ] **클러스터 모드 제출**: `--deploy-mode cluster`로 제출하며, 드라이버의 ServiceAccount가 필요한 Executor Pod를 생성/watch/삭제할 수 있다 (Part 1)
- [ ] **동적 리소스 할당(DRA)**: Kubernetes에는 External Shuffle Service가 없으므로, DRA를 사용하는 모든 곳에서 `spark.dynamicAllocation.enabled`와 함께 `spark.dynamicAllocation.shuffleTracking.enabled`를 설정했다 (Part 1)
- [ ] **Graceful Decommissioning**: Spot 기반 Executor 풀에서 `spark.decommission.enabled`/`spark.storage.decommission.enabled`를 활성화했다 (Part 1)
- [ ] **선언적 작업 관리**: 프로덕션 작업은 임시 `spark-submit` 호출이 아니라 Spark Operator의 CRD를 통해 실행한다 (Part 2)
- [ ] **리소스 사이징**: 드라이버는 안정성, Executor는 처리량을 기준으로 사이징했고, 둘 다 다른 작업의 설정을 복사한 것이 아니라 실제 워크로드 벤치마킹으로 검증했다 (Part 4, Part 5)
- [ ] **S3 접근**: 드라이버/Executor Pod가 IRSA 바인딩 ServiceAccount와 `WebIdentityTokenCredentialsProvider`를 사용하며, 정적 AWS 자격 증명이 어디에도 없다 (Part 5)
- [ ] **메트릭**: `PrometheusServlet` 또는 JMX Exporter 방식 중 하나가 실제로 연결되어 스크래핑되고 있다 (Part 5)
- [ ] **완료 후 디버깅 가능성**: 모든 작업이 기록하는 S3 이벤트 로그 위치를 바라보는 Spark History Server가 배포되어 있어, 드라이버 Pod가 사라진 뒤에도 완료된 작업을 조회할 수 있다 (Part 5)
- [ ] **네트워크 정책**: 드라이버↔Executor, Executor↔Executor 트래픽이 실제 사용 중인 고정 Spark 포트로만 제한되어 있다 (Part 5)
- [ ] **RBAC**: 드라이버의 ServiceAccount가 `ClusterRole`이 아닌 네임스페이스 범위의 `Role`을 사용하며, 실제로 필요한 verb로만 제한되어 있다 (Part 5)

이 체크리스트를 모두 충족한다면, 해당 Spark on EKS 파이프라인은 프로덕션 환경에서 운영할 준비가 되었다고 볼 수 있습니다.

---

[메인 페이지로 돌아가기](./README.md)

## 퀴즈

이 장에서 배운 내용을 테스트하려면 [주제 퀴즈](../../quizzes/data-on-eks/spark/05-best-practices-quiz.md)를 풀어보세요.
