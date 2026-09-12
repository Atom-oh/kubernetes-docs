# Part 5: 모범 사례와 보안 퀴즈

Spark 4.2.0 / Hadoop 3.5.0 / AWS SDK v2 2.35.4.

## 1. Spark 4.2의 검증한 Hadoop/S3A 버전 조합은?

<details>
<summary>정답 보기</summary>

Hadoop client와 hadoop-aws는 3.5.0으로 맞추며 AWS SDK v2 bundle 2.35.4와 Maven이 해결한 runtime 의존성을 포함합니다. 다른 이미지·EMR에는 그 번들의 버전을 다시 확인합니다.

</details>

## 2. SDK v2 조합의 IRSA provider는?

<details>
<summary>정답 보기</summary>

software.amazon.awssdk.auth.credentials.WebIdentityTokenFileCredentialsProvider입니다. 이전 com.amazonaws.auth.WebIdentityTokenCredentialsProvider는 이 조합에서 자동 변환되지 않습니다.

</details>

## 3. Pod Identity를 사용할 때 바뀌는 것은?

<details>
<summary>정답 보기</summary>

ContainerCredentialsProvider, service-account association, pods.eks.amazonaws.com trust와 Agent/노드 권한을 사용합니다. IRSA annotation과 OIDC 설정이 이를 대신하지 않습니다.

</details>

## 4. 기본 S3A chain이 IRSA도 자동 사용하나요?

<details>
<summary>정답 보기</summary>

검증한 Hadoop 3.5.0 chain에는 container/instance wrapper가 있지만 web-identity provider는 없습니다. 필요한 provider를 명시하고 실제 유효 ID와 prefix 접근을 검증합니다.

</details>

## 5. Driver·executor·History Server의 ServiceAccount를 나누는 이유는?

<details>
<summary>정답 보기</summary>

Driver의 Kubernetes API 관리 권한과 각 프로세스의 S3 데이터 권한을 분리하기 위해서입니다. History Server는 cleaner를 끈 읽기 전용 역할로 시작할 수 있습니다.

</details>

## 6. namespace Role은 자신의 executor만 관리하게 제한하나요?

<details>
<summary>정답 보기</summary>

아닙니다. 명시된 리소스·verb를 namespace 범위로 허용하며 이 규칙에는 Pod label 기반 소유권 제한이 없습니다. Pod 생성·다른 SA 사용·host 접근은 admission과 신뢰 경계로 함께 제한합니다.

</details>

## 7. ClusterRole은 항상 클러스터 전체 권한을 뜻하나요?

<details>
<summary>정답 보기</summary>

아닙니다. RoleBinding이 ClusterRole을 참조하면 namespaced 리소스 권한은 그 binding namespace로 제한할 수 있습니다. 규칙과 binding 종류·범위를 함께 확인합니다.

</details>

## 8. spark.authenticate=true가 Spark UI 로그인도 제공하나요?

<details>
<summary>정답 보기</summary>

아닙니다. 내부 연결 인증입니다. Kubernetes가 생성한 app secret은 executor 환경으로 전달될 수 있어 Pod 조회 권한도 중요합니다. UI 사용자 인증·인가·TLS는 별도입니다.

</details>

## 9. 역할 label만 사용한 NetworkPolicy의 문제는?

<details>
<summary>정답 보기</summary>

같은 namespace의 다른 작업 executor도 조건을 만족합니다. 예제는 고유 run ID를 driver/executor label과 정책에 같이 넣습니다. Label 자체가 인증 수단은 아니므로 위조 가능한 Pod 생성 권한도 고려합니다.

</details>

## 10. NetworkPolicy를 적용하면 허용된 포트 외 모든 경로가 막히나요?

<details>
<summary>정답 보기</summary>

정책은 합산되고 CNI 집행이 필요합니다. 이 예제는 ingress만 제한합니다. Egress, node/hostNetwork, 다른 allow 정책, DNS/API/AWS endpoint와 추가 plugin 경로는 별도로 검토합니다.

</details>

## 11. 고정 포트와 spark.port.maxRetries=0을 같이 쓰는 이유는?

<details>
<summary>정답 보기</summary>

포트 충돌 시 다른 포트로 이동하지 않고 실패하도록 해 NetworkPolicy와 실제 listener가 어긋나지 않게 합니다. 추가 endpoint를 사용할 때는 그 포트·보안도 따로 구성합니다.

</details>

## 12. PrometheusServlet과 executor 집계 endpoint는 같은가요?

<details>
<summary>정답 보기</summary>

아닙니다. /metrics/prometheus/는 driver Dropwizard registry이고 /metrics/executors/prometheus/는 driver가 수집한 executor 집계입니다. Executor마다 별도 Spark UI가 생기지 않으며 series·label·단위도 대조해야 합니다.

</details>

## 13. JMX Java agent와 Operator chart 메트릭에 관한 올바른 설명은?

<details>
<summary>정답 보기</summary>

Agent는 JVM 안에서 실행되고 별도 프로세스가 아닙니다. Operator chart 기본 메트릭은 Operator 자체이며 Spark JVM마다 agent를 자동 설치하지 않습니다.

</details>

## 14. PodMonitor 리소스를 만들기만 하면 수집되나요?

<details>
<summary>정답 보기</summary>

Prometheus의 PodMonitor label/namespace selector, discovery RBAC, 실제 Pod port/path와 NetworkPolicy가 모두 맞아야 합니다. Targets UP과 실제 series를 확인하며 짧은 작업은 scrape 사이에 끝날 수 있습니다.

</details>

## 15. Driver Pod 객체가 남아 있으면 작업 종료 후 UI도 남나요?

<details>
<summary>정답 보기</summary>

JVM이 끝나면 live UI는 서비스되지 않습니다. History Server는 별도 보존한 event log로 재구성하며 stdout/stderr나 checkpoint를 대신 읽는 것이 아닙니다.

</details>

## 16. History Server 설정 파일은 mount만 하면 적용되나요?

<details>
<summary>정답 보기</summary>

아닙니다. 예제는 spark-class org.apache.spark.deploy.history.HistoryServer --properties-file 경로로 명시적으로 읽고 foreground로 실행합니다. 파일 경로와 로그 디렉터리·S3 identity를 함께 확인합니다.

</details>

## 17. History Server가 모든 과거 작업의 모든 정보를 복원하나요?

<details>
<summary>정답 보기</summary>

Event log가 실제로 보존되어 읽을 수 있어야 합니다. 누락·손상·미flush·삭제·compaction이 정보에 영향을 줍니다. 이벤트 로그는 데이터 복구용 checkpoint나 출력 백업이 아닙니다.

</details>

## 18. Production에서 Operator·cluster mode·IRSA만이 정답인가요?

<details>
<summary>정답 보기</summary>

아닙니다. 검증된 직접 제출·Operator·EMR, client/cluster mode와 IRSA/Pod Identity를 요구에 맞게 선택합니다. 권한·데이터 정확성·복구·네트워크·리소스·비용을 실제 환경에서 시험해야 합니다.

</details>

[Guide](../../../data-on-eks/spark/05-best-practices.md)

[README](../../../data-on-eks/spark/README.md)
