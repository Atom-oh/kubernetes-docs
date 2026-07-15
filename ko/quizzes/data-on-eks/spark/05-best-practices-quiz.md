# Part 5: 모범 사례와 보안 퀴즈

이 퀴즈는 Spark on EKS를 프로덕션에 투입하기 위한 모범 사례에 대한 이해도를 테스트합니다. IRSA 기반 S3 접근, 관찰 가능성(observability) 옵션, Spark History Server, 리소스 사이징 철학, IAM을 넘어서는 보안 강화까지 다룹니다.

## 객관식 문제

1. 드라이버/Executor Pod가 IRSA로 S3에 접근하도록 하려면 `spark.hadoop.fs.s3a.aws.credentials.provider`를 어떤 클래스로 설정해야 하나요?
   - A) `com.amazonaws.auth.EnvironmentVariableCredentialsProvider`
   - B) `com.amazonaws.auth.WebIdentityTokenCredentialsProvider`
   - C) `com.amazonaws.auth.InstanceProfileCredentialsProvider`
   - D) `org.apache.spark.SparkS3CredentialsProvider`

<details>

<summary>정답 보기</summary>

**정답: B) `com.amazonaws.auth.WebIdentityTokenCredentialsProvider`**

**설명:**
이 provider는 (ServiceAccount의 `eks.amazonaws.com/role-arn` 어노테이션을 기반으로) EKS Pod Identity 웹훅이 Pod에 주입한 웹 아이덴티티 토큰을 읽어, STS `AssumeRoleWithWebIdentity`를 통해 임시 AWS 자격 증명으로 교환하고 만료 시점에 맞춰 자동으로 갱신합니다. 이 방식을 사용하면 Secret, ConfigMap, 컨테이너 이미지 어디에도 정적인 AWS Access Key를 둘 필요가 없습니다.
</details>

2. 드라이버/Executor Pod가 IRSA 바인딩 ServiceAccount를 사용하도록 지정하는 Spark 설정 키는 무엇인가요?
   - A) `spark.kubernetes.driver.serviceAccountName` / `spark.kubernetes.executor.serviceAccountName`
   - B) `spark.kubernetes.authenticate.driver.serviceAccountName` / `spark.kubernetes.authenticate.executor.serviceAccountName`
   - C) `spark.hadoop.fs.s3a.serviceAccountName`
   - D) `spark.driver.iamRole` / `spark.executor.iamRole`

<details>

<summary>정답 보기</summary>

**정답: B) `spark.kubernetes.authenticate.driver.serviceAccountName` / `spark.kubernetes.authenticate.executor.serviceAccountName`**

**설명:**
이 `spark-submit` 설정 키는 드라이버와 Executor Pod가 어떤 Kubernetes ServiceAccount로 실행될지를 지정합니다. 해당 ServiceAccount에 `eks.amazonaws.com/role-arn` 어노테이션이 있으면, Pod는 IRSA에 필요한 웹 아이덴티티 토큰을 자동으로 주입받습니다.
</details>

3. Spark 내장 `PrometheusServlet`이 JmxSink + JMX Prometheus Exporter 방식보다 갖는 주된 운영상의 장점은 무엇인가요?
   - A) 완전히 다른 종류의 메트릭을 수집한다
   - B) 외부 JAR이나 별도 자바 에이전트 없이, Spark가 이미 사용하는 UI 포트를 그대로 재사용한다
   - C) Spark Operator에서만 동작한다
   - D) 이벤트 로깅을 대체한다

<details>

<summary>정답 보기</summary>

**정답: B) 외부 JAR이나 별도 자바 에이전트 없이, Spark가 이미 사용하는 UI 포트를 그대로 재사용한다**

**설명:**
`PrometheusServlet`(Spark 3.0부터 제공)은 Spark의 기존 UI 포트에서 곧바로 Prometheus 형식으로 메트릭을 노출합니다. JmxSink + JMX Prometheus Exporter 방식(Spark Operator의 Helm 차트가 기본으로 구성하는 방식)은 JVM에 별도의 `-javaagent`를 붙이고 이미지에 추가 JAR을 넣어야 합니다. 두 방식 모두 측정하는 Spark 메트릭 자체는 동일하며, 전달 방식과 패키징만 다릅니다.
</details>

4. `PrometheusServlet`으로 전환하지 않고 JmxSink + JMX Prometheus Exporter 방식을 의도적으로 계속 사용하는 것이 합리적인 경우는 언제인가요?
   - A) 항상 그렇다 — `PrometheusServlet`이 모든 경우에 더 나쁘다
   - B) Spark Operator의 기본 차트 구성을 그대로 쓰고 있거나, 그 방식을 기준으로 만들어진 더 방대하고 성숙한 커뮤니티 Grafana 대시보드 생태계를 활용하고 싶을 때
   - C) Kubernetes 밖에서 Spark를 실행할 때
   - D) `spark.eventLog.enabled`를 `false`로 설정했을 때

<details>

<summary>정답 보기</summary>

**정답: B) Spark Operator의 기본 차트 구성을 그대로 쓰고 있거나, 그 방식을 기준으로 만들어진 더 방대하고 성숙한 커뮤니티 Grafana 대시보드 생태계를 활용하고 싶을 때**

**설명:**
두 방식의 트레이드오프는 서로 다릅니다. `PrometheusServlet`은 JVM에 아무것도 추가로 붙일 필요가 없어 운영이 더 단순하고, JMX Exporter 방식은 이미 만들어진 폭넓은 Grafana 대시보드 자산과 Spark Operator 차트의 기본 구성이라는 이점이 있습니다. 어느 한쪽이 항상 우월한 것이 아니라, 이미 갖추고 있는 도구에 따라 선택이 달라집니다.
</details>

5. 지난밤에 끝난 작업을 디버깅하려 할 때 라이브 Spark UI를 그냥 확인할 수 없는 이유는 무엇인가요?
   - A) Kubernetes에서는 Spark UI가 기본적으로 비활성화되어 있다
   - B) UI를 호스팅하던 드라이버 Pod가 이미 Kubernetes에 의해 회수되었을 가능성이 높다
   - C) Spark UI는 Pod 생존 여부와 무관하게 현재 실행 중인 스테이지만 보여주고 과거 기록은 절대 보여주지 않는다
   - D) 라이브 UI는 client 배포 모드에서만 제공된다

<details>

<summary>정답 보기</summary>

**정답: B) UI를 호스팅하던 드라이버 Pod가 이미 Kubernetes에 의해 회수되었을 가능성이 높다**

**설명:**
드라이버 Pod가 스스로 스케줄링을 담당하며 라이브 Spark UI도 그 안에 존재하기 때문에, 작업이 끝나거나(또는 실패하거나) Kubernetes가 해당 Pod를 회수하면 UI도 함께 사라집니다. 바로 이 공백을 채우는 것이 Spark History Server로, 원본 드라이버 Pod의 존재 여부와 무관하게 저장된 이벤트 로그로부터 UI를 재구성해서 제공합니다.
</details>

6. Spark History Server가 S3에 저장된 작업의 이벤트 로그를 읽으려면 어떤 두 가지 Spark 설정이 필요한가요?
   - A) `spark.eventLog.enabled`, 그리고 `spark.eventLog.dir`과 동일한 S3 경로를 가리키는 `spark.history.fs.logDirectory`
   - B) `spark.dynamicAllocation.enabled`와 `spark.decommission.enabled`
   - C) `spark.kubernetes.authenticate.driver.serviceAccountName`만 있으면 된다
   - D) `spark.metrics.conf`와 `spark.ui.port`

<details>

<summary>정답 보기</summary>

**정답: A) `spark.eventLog.enabled`, 그리고 `spark.eventLog.dir`과 동일한 S3 경로를 가리키는 `spark.history.fs.logDirectory`**

**설명:**
각 작업은 `spark.eventLog.enabled=true`와 `spark.eventLog.dir=s3a://...`를 설정해 실제로 S3에 이벤트 로그를 기록해야 합니다. History Server 인스턴스는 이 S3 위치를 가리키는 `spark.history.fs.logDirectory`(그리고 이를 읽을 수 있는 자체 IRSA 바인딩 ServiceAccount)를 설정해야, 주기적으로 다시 스캔해서 완료된 작업의 재구성된 UI를 제공할 수 있습니다.
</details>

7. 이 문서에서 요약한 리소스 사이징 철학에 따르면, 드라이버 사이징은 무엇을 우선해야 하나요?
   - A) Executor와 마찬가지로 최대 처리량
   - B) 안정성 — 드라이버 자체가 병목이 되거나 OOMKilled로 작업 전체를 끌고 내려가지 않을 정도의 여유
   - C) 드라이버 불안정성을 감수하더라도 최소 비용
   - D) Executor의 `spark.executor.memory` 값과 정확히 동일하게 맞추기

<details>

<summary>정답 보기</summary>

**정답: B) 안정성 — 드라이버 자체가 병목이 되거나 OOMKilled로 작업 전체를 끌고 내려가지 않을 정도의 여유**

**설명:**
드라이버는 무거운 데이터 처리를 직접 수행하는 대신 작업을 조율하고 태스크 상태를 추적하므로, 사이징의 목표는 안정성입니다. 실제 처리가 이루어지는 Executor는 반대로 처리량을 목표로, 작업의 실제 셔플 양과 태스크당 메모리 요구량에 맞춰 튜닝합니다. 어느 쪽에도 만능 기본값은 없으며, 둘 다 실제 워크로드 벤치마킹을 통해 도출해야 합니다.
</details>

8. Spark 드라이버의 Kubernetes ServiceAccount에 애초에 Pod 관리 권한이 필요한 이유는 무엇인가요?
   - A) 필요 없다 — Pod 권한은 Executor에만 필요하다
   - B) 드라이버가 Kubernetes API를 직접 호출해 자신의 Executor Pod를 생성·watch·삭제하기 때문이다
   - C) S3A 자격 증명 확인을 위해 필요하다
   - D) 일반 `spark-submit`이 아니라 Spark Operator를 사용할 때만 필요하다

<details>

<summary>정답 보기</summary>

**정답: B) 드라이버가 Kubernetes API를 직접 호출해 자신의 Executor Pod를 생성·watch·삭제하기 때문이다**

**설명:**
Part 1에서 다뤘듯, Kubernetes에서는 드라이버가 스스로 스케줄러 역할을 하며, 별도의 클러스터 매니저 데몬이 대신 Executor Pod를 생성해주지 않습니다. 따라서 드라이버의 ServiceAccount에는 Pod를 관리할 수 있는 RBAC 권한이 필요하지만, 최소 권한 버전에서는 이를 클러스터 전체 `ClusterRole`이 아니라 드라이버가 실제로 사용하는 verb로만 한정한 네임스페이스 범위의 `Role`로 제한해야 합니다.
</details>

9. Spark 드라이버의 ServiceAccount에 넓은 Pod 권한을 가진 `ClusterRole`을 부여하면 어떤 문제가 있나요?
   - A) `ClusterRole` 객체는 `RoleBinding`을 지원하지 않는다
   - B) 최소 권한 원칙을 위반한다 — 드라이버가 침해되거나 오작동할 경우 자신의 네임스페이스 밖의 Pod에도 영향을 줄 수 있다
   - C) `ClusterRole`은 `create`/`delete` verb를 부여할 수 없다
   - D) 드라이버가 Executor Pod를 전혀 생성할 수 없게 된다

<details>

<summary>정답 보기</summary>

**정답: B) 최소 권한 원칙을 위반한다 — 드라이버가 침해되거나 오작동할 경우 자신의 네임스페이스 밖의 Pod에도 영향을 줄 수 있다**

**설명:**
드라이버는 자신의 네임스페이스 안에 있는 Pod, Service, ConfigMap만 관리하면 충분합니다. 권한을 해당 네임스페이스로 범위를 좁힌 `Role`로 제한하면, 드라이버가 침해되거나 오작동해도 영향 범위가 그 네임스페이스 하나로 한정되고 클러스터 전체 Pod에는 영향을 줄 수 없습니다.
</details>

10. `NetworkPolicy`를 작성하기 전에 `spark.driver.port`와 `spark.blockManager.port`를 고정된 값으로 지정해야 하는 이유는 무엇인가요?
    - A) 셔플 압축률을 높이기 위해
    - B) 예측할 수 없는 포트 범위 대신, 특정하고 알려진 포트로만 트래픽을 허용하는 `NetworkPolicy`를 작성할 수 있게 하기 위해
    - C) 동적 리소스 할당(DRA)을 활성화하기 위해
    - D) IRSA의 신뢰 정책 요구 사항을 만족시키기 위해

<details>

<summary>정답 보기</summary>

**정답: B) 예측할 수 없는 포트 범위 대신, 특정하고 알려진 포트로만 트래픽을 허용하는 `NetworkPolicy`를 작성할 수 있게 하기 위해**

**설명:**
이 포트들을 고정하지 않으면 Spark가 임의의 포트에 바인딩할 수 있어, 드라이버-Executor·Executor-Executor 통신에 필요한 포트만 정확히 허용하는 `NetworkPolicy`를 작성하기가 불가능해집니다. `spark.driver.port`와 `spark.blockManager.port`(및 Executor 측 대응 값)를 알려진 값으로 고정하면, 정책이 드라이버-Executor Pod 간의 해당 포트로만 트래픽을 제한할 수 있습니다.
</details>

## 단답형 문제

11. `WebIdentityTokenCredentialsProvider`가 사용하는 토큰은 무엇이며, 그 토큰은 어디에서 오나요?

<details>

<summary>정답 보기</summary>

**정답: EKS Pod Identity 웹훅이 Pod의 ServiceAccount 어노테이션(`eks.amazonaws.com/role-arn`)을 기반으로 Pod에 주입하는 웹 아이덴티티 토큰**

**설명:**
ServiceAccount에 올바른 role-arn 어노테이션이 있으면 EKS는 이 토큰을 Pod에 자동으로 주입합니다. `WebIdentityTokenCredentialsProvider`는 이 토큰을 읽어 STS `AssumeRoleWithWebIdentity`를 호출해 임시 AWS 자격 증명을 얻고, 만료 시점에 맞춰 자동으로 갱신합니다. 어디에도 정적 자격 증명이 필요하지 않습니다.
</details>

12. 이 문서에서 다룬 두 가지 Spark 메트릭/관찰 가능성 방식의 이름과, 각각을 선택할 만한 이유를 하나씩 쓰세요.

<details>

<summary>정답 보기</summary>

**정답: (1) 네이티브 `PrometheusServlet` — 더 단순하고 추가 에이전트/JAR이 필요 없어 신규 파이프라인의 기본 선택지로 적합. (2) JmxSink + JMX Prometheus Exporter 자바 에이전트 — Spark Operator의 기본 차트 구성을 이미 쓰고 있거나, 더 방대하고 성숙한 Grafana 대시보드 생태계를 활용하고 싶을 때 유지할 가치가 있음**

**설명:**
두 방식 모두 측정하는 Spark 메트릭 자체는 동일합니다. 선택은 무엇을 측정하느냐가 아니라 운영 부담과 기존에 갖춰둔 도구·대시보드 자산 사이의 트레이드오프에 관한 것입니다.
</details>

13. Kubernetes에서 드라이버 Pod가 동작하는 방식을 고려할 때, Spark History Server가 왜 필요한가요?

<details>

<summary>정답 보기</summary>

**정답: 드라이버 Pod만이 유일한 라이브 Spark UI를 호스팅하는데, 작업이 끝나면 Kubernetes가 그 Pod를 회수하면서 UI도 함께 사라지기 때문입니다. History Server는 라이브 드라이버 연결 대신 S3에 저장된 이벤트 로그로부터 UI를 재구성합니다.**

**설명:**
이는 Part 1에서 다룬, 드라이버가 스스로 스케줄링을 수행하는 아키텍처의 직접적인 결과입니다. 드라이버 Pod가 사라진 뒤에도 작업의 UI를 유지해주는 별도의 장기 실행 프로세스가 없으므로, 사후 디버깅을 위해서는 영속적인 이벤트 로그를 읽는 메커니즘이 유일한 방법입니다.
</details>

14. `spark.dynamicAllocation.shuffleTracking.enabled`는 무엇을 방지하며, 이것이 YARN보다 Kubernetes에서 더 중요한 이유는 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: 다른 태스크가 아직 필요로 하는 셔플 블록을 갖고 있는 Executor를 동적 리소스 할당(DRA)이 제거하지 못하도록 막습니다. YARN의 External Shuffle Service와 달리 Kubernetes에는 Executor가 사라진 뒤에도 그 셔플 블록을 계속 제공해줄 데몬이 없기 때문에 이것이 더 중요합니다.**

**설명:**
이 내용은 Part 1에서 Kubernetes에서 DRA를 안전하게 사용하기 위한 전제 조건으로 소개되었으며, 프로덕션 체크리스트에서 go-live 전에 반드시 확인해야 하는 리소스 관리 항목의 일부로 남아 있습니다.
</details>

15. IRSA 외에 이 문서에서 다룬, Spark on EKS 배포를 강화하기 위한 두 가지 Kubernetes 네이티브 메커니즘은 무엇이며 각각 무엇을 제한하나요?

<details>

<summary>정답 보기</summary>

**정답: (1) `NetworkPolicy` — 어떤 Pod가 어떤 포트로 드라이버/Executor Pod에 접근할 수 있는지를 제한. (2) 네임스페이스 범위의 RBAC `Role`/`RoleBinding` — 드라이버의 ServiceAccount가 Kubernetes API로 할 수 있는 일을 자신의 네임스페이스와 필요한 verb로만 제한**

**설명:**
IRSA는 클러스터 밖 AWS 리소스에 대한 접근을 제어하고, `NetworkPolicy`와 RBAC는 클러스터 안에서 Pod들이 서로에게, 그리고 Kubernetes API에 할 수 있는 일을 제어합니다. 심층 방어(defense in depth)를 위해 세 가지 모두 필요합니다.
</details>

## 실습 문제

16. 네임스페이스 `spark-jobs`의 IRSA 바인딩 ServiceAccount `spark-s3-sa`를 통해 드라이버와 Executor Pod가 모두 S3에 인증하도록 하는 `spark-submit` 설정을 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```bash
spark-submit \
  --master k8s://https://<EKS_API_SERVER_ENDPOINT>:443 \
  --deploy-mode cluster \
  --conf spark.kubernetes.namespace=spark-jobs \
  --conf spark.kubernetes.authenticate.driver.serviceAccountName=spark-s3-sa \
  --conf spark.kubernetes.authenticate.executor.serviceAccountName=spark-s3-sa \
  --conf spark.hadoop.fs.s3a.aws.credentials.provider=com.amazonaws.auth.WebIdentityTokenCredentialsProvider \
  local:///opt/spark/jobs/etl-job.jar
```

**설명:**
`spark.kubernetes.authenticate.driver.serviceAccountName`과 Executor에 대응하는 설정 모두 IRSA 바인딩 ServiceAccount를 가리켜야 하며, `spark.hadoop.fs.s3a.aws.credentials.provider`를 설정해야 S3A 커넥터가 정적 자격 증명을 찾는 대신 실제로 웹 아이덴티티 토큰을 사용하게 됩니다.
</details>

17. 네임스페이스 `spark-jobs`에서, 드라이버 Pod(`spark-role: driver`)의 드라이버 포트(7078)와 블록 매니저 포트(7079)에는 Executor Pod(`spark-role: executor`)만 접근할 수 있도록 허용하는 `NetworkPolicy`를 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
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

**설명:**
`podSelector`는 드라이버 Pod를 대상으로 하며, 단일 `ingress` 규칙은 `spark-role: executor` 레이블이 붙은 Pod로부터의 트래픽만 드라이버 포트와 블록 매니저 포트로 한정해 허용합니다. 이 정책이 유효하려면 `spark.driver.port`/`spark.driver.blockManager.port`를 고정된 값으로 지정해 두어야 합니다.
</details>

18. `ClusterRole`을 사용하지 않고, Spark 드라이버의 ServiceAccount(`spark-jobs` 네임스페이스의 `spark-s3-sa`)에 자신의 Executor Pod를 관리하는 데 필요한 권한만 정확히 부여하는 네임스페이스 범위의 `Role`과 `RoleBinding`을 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
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

**설명:**
`ClusterRole`이 아니라 `spark-jobs` 네임스페이스 안에서만 바인딩되는 `Role`을 사용하고, verb도 드라이버가 실제로 수행하는 작업(자신의 Executor Pod 생성/조회/watch/삭제, 로그 조회, Executor 디스커버리용 헤드리스 서비스·ConfigMap 관리)으로만 제한하면, 드라이버가 침해되거나 오작동해도 영향 범위가 자신의 네임스페이스로 한정됩니다.
</details>

---

[학습 자료로 돌아가기](../../../data-on-eks/spark/05-best-practices.md) | [Spark 딥다이브 홈으로](../../../data-on-eks/spark/README.md)
