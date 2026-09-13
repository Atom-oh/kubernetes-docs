# Amazon EMR on EKS 퀴즈

2026년 9월 검토 본문 기준입니다.

## 1. Virtual cluster는 무엇인가요?

<details>
<summary>정답 보기</summary>

EKS cluster의 namespace를 EMR에 등록한 논리적 리소스입니다. 새 compute를 만들지는 않지만 최초 service-linked role과 CAM access entry/policy 설정이 발생할 수 있습니다.

</details>

## 2. StartJobRun과 EMR Spark Operator 제출의 차이는?

<details>
<summary>정답 보기</summary>

StartJobRun은 virtual cluster를 대상으로 하는 AWS API입니다. Operator 경로는 별도 설치 후 SparkApplication CR을 적용하며, StartJobRun이 내부적으로 Operator에 위임하는 옵션이 아닙니다.

</details>

## 3. Operator로 제출한 CR에 EMR job ID가 자동 생기나요?

<details>
<summary>정답 보기</summary>

그렇게 가정하면 안 됩니다. CR 상태·로그·재시도는 해당 Operator 경로로 관리하며 EMR job API 수명주기와 구분합니다.

</details>

## 4. EMR용 Spark Operator 지원이 시작된 버전과 설치 방식은?

<details>
<summary>정답 보기</summary>

EMR 6.10.0+입니다. 공식 EMR용 chart와 호환 런타임을 설치하고 kubectl apply로 제출합니다. Part 2의 최신 upstream chart와 동일한 배포라고 가정하지 않습니다.

</details>

## 5. emr-spark-8.0.0의 Apache Spark 버전은?

<details>
<summary>정답 보기</summary>

4.0.2-amzn-0입니다. 2026년 4월 출시된 Spark 4.x GA이며, 8.0.0은 EMR 런타임 릴리스 이름입니다.

</details>

## 6. -latest와 날짜 suffix의 차이는?

<details>
<summary>정답 보기</summary>

-latest는 해당 릴리스의 보안 업데이트를 따라가므로 동일 이미지 바이트를 고정하지 않습니다. 날짜 suffix는 릴리스 재현에 유용하지만 이후 업데이트 검토도 필요합니다.

</details>

## 7. CreateVirtualCluster 응답에서 다음 작업에 사용할 값은?

<details>
<summary>정답 보기</summary>

응답의 id입니다. StartJobRun 요청의 virtualClusterId에 넣고 등록 대상 namespace와 RUNNING 상태를 확인합니다.

</details>

## 8. 실행 역할의 데이터 권한과 제출자의 권한은 같은가요?

<details>
<summary>정답 보기</summary>

다릅니다. 실행 역할은 작업의 S3·KMS·로그 등 접근을 허용하고, 제출자는 API 호출 및 허용 역할 사용 권한이 필요합니다. ExecutionRoleArn 조건과 해당 identity 경로의 PassRole을 검토합니다.

</details>

## 9. update-role-trust-policy가 하는 일은?

<details>
<summary>정답 보기</summary>

IRSA를 사용할 때 cluster OIDC·namespace·EMR 관리 service account에 맞는 실행 역할 trust를 갱신합니다. S3 데이터 권한이나 제출자 권한을 자동으로 부여하지 않습니다.

</details>

## 10. StartJobRun에서 Pod Identity를 사용할 수 있나요?

<details>
<summary>정답 보기</summary>

EMR 7.3.0+에서 지원합니다. Agent·노드 EKS Auth 권한, pods.eks.amazonaws.com trust와 service-account association이 필요합니다. IRSA annotation만으로 대체되지 않습니다.

</details>

## 11. create-role-associations는 어떤 연결을 준비하나요?

<details>
<summary>정답 보기</summary>

작업 실행 역할과 submitter·driver·executor의 EMR service account 세 연결입니다. 최신 CLI helper를 사용하며 namespace나 역할 사용이 끝난 뒤 남은 association도 별도로 정리합니다.

</details>

## 12. maxConcurrentJobRuns=2가 namespace CPU 상한을 뜻하나요?

<details>
<summary>정답 보기</summary>

아닙니다. 실행 작업 수 제한이며 maxInQueueJobRuns는 대기 작업 수 제한입니다. 실제 CPU·메모리 quota와 작업별 executor 상한은 별도입니다.

</details>

## 13. StartJobRun이 성공 응답을 반환하면 작업이 끝났나요?

<details>
<summary>정답 보기</summary>

아직 아닙니다. 접수된 job ID로 최종 상태와 로그를 확인합니다. 이 장의 smoke job은 COMPLETED와 SMOKE_OK rows=10 total=45를 함께 확인합니다.

</details>

## 14. 같은 clientToken으로 재요청하면 데이터 exactly-once도 보장되나요?

<details>
<summary>정답 보기</summary>

API 요청 중복을 제어하는 기능입니다. 애플리케이션 재시도·외부 출력 부작용까지 보장하지 않으며 새로 실행하려는 작업에는 새 token을 사용합니다.

</details>

## 15. EMR Pod의 template이나 image를 바꿀 수 있나요?

<details>
<summary>정답 보기</summary>

지원되는 pod template·custom image 경로로 가능합니다. 다만 StartJobRun이 관리하는 namespace·service account·Pod 이름 등을 임의로 덮어쓰지 않고 릴리스별 제약을 검증합니다.

</details>

## 16. CloudWatch와 Step Functions 통합은 설정 없이 완성되나요?

<details>
<summary>정답 보기</summary>

아닙니다. 로그 monitoringConfiguration·실행 역할 권한, state machine·역할 등이 필요합니다. 서비스 메트릭과 모든 Spark JVM 메트릭도 구분합니다.

</details>

## 17. EMR Studio의 대화형 실행 경로는?

<details>
<summary>정답 보기</summary>

CreateManagedEndpoint로 만든 endpoint의 Jupyter Enterprise Gateway가 kernel을 관리합니다. 일반 StartJobRun batch 호출과 다르며 private network·ALB·역할 구성이 필요합니다. 같은 endpoint 사용자/kernel은 endpoint 역할을 공유합니다.

</details>

## 18. Virtual cluster 삭제를 전체 정리로 보면 안 되는 이유는?

<details>
<summary>정답 보기</summary>

작업·endpoint 상태를 먼저 확인하고 해당 리소스를 정리해야 합니다. EKS·namespace·S3·로그·IAM 역할·Pod Identity 연결의 수명주기는 별도이며 삭제 상태와 권한 오류도 확인합니다.

</details>

[Guide](../../../data-on-eks/spark/03-emr-on-eks.md)
