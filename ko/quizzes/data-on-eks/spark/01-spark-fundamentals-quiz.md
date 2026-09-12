# Spark on Kubernetes 기초 퀴즈

제출 모드, 역할 분리, 리소스·동적 할당·종료의 실제 조건을 확인합니다.

## 1. Spark 4.2의 Kubernetes 배포 모드와 버전 전제는 무엇인가요?

<details>
<summary>정답 보기</summary>

Cluster·client mode를 모두 지원하며 4.2 문서는 Kubernetes 1.34 이상을 전제로 합니다. Client mode는 2.4부터이고 notebook 전용이 아닙니다. kubectl은 실제 API server와 호환되어야 합니다.

</details>

## 2. Executor Pod 요청, Pod 배치·시작과 Spark task 할당은 누가 담당하나요?

<details>
<summary>정답 보기</summary>

Driver가 API에 executor Pod를 요청합니다. Kubernetes scheduler가 노드를 선택하고 kubelet이 컨테이너를 시작합니다. Spark driver의 scheduler는 등록된 executor에 Spark task를 할당합니다. API server나 driver가 Kubernetes scheduler를 대신하지 않습니다.

</details>

## 3. YARN 계층이 없어지면 운영 인프라와 driver 권한도 필요 없어지나요?

<details>
<summary>정답 보기</summary>

아닙니다. 노드·Kubernetes·이미지·네트워크·스토리지·관측 운영은 남습니다. 제출자 API 인증과 driver의 namespace RBAC도 필요합니다. 기본 예제는 executor에 별도 service account를 사용하며 AWS 데이터 접근 권한과 Kubernetes RBAC는 별개입니다.

</details>

## 4. DRA에서 shuffle tracking 플래그 두 개를 언제나 명시해야 하나요?

<details>
<summary>정답 보기</summary>

아닙니다. DRA는 켜야 하지만 shuffle tracking은 Spark 4.2에서 기본 true이며 3.0부터 제공됩니다. Stock Kubernetes의 ESS는 지원되지 않지만 decommission 기반 보존·적절한 reliable ShuffleDataIO도 조건부 대안입니다. 중복 보존 방식은 회수를 늦출 수 있습니다.

</details>

## 5. Decommission을 켰을 때 기본 Kubernetes 종료 경로는 무엇인가요?

<details>
<summary>정답 보기</summary>

Spark 4.2가 기본 /opt/decom.sh를 실행하는 preStop hook을 주입합니다. 공식 이미지는 스크립트를 포함하며 executor JVM에 SIGPWR를 보내 기다립니다. Block 이전에는 storage decommission 설정과 실제 대상·시간·용량도 필요합니다.

</details>

## 6. terminationGracePeriodSeconds를 60으로 늘리면 모든 block 이전이 보장되나요?

<details>
<summary>정답 보기</summary>

아닙니다. Spark 4.2는 template 값을 자체 설정으로 덮어쓰므로 spark.kubernetes.executor.terminationGracePeriodSeconds=60s도 필요합니다. 기본 30초·설정 60초 모두 preStop을 포함한 상한일 뿐이며 강제 종료·Spot 기한·대상 용량 부족 등으로 이전이 끝나지 못할 수 있습니다.

</details>

## 7. allocation.batch.size와 초기·최소 executor 수는 어떻게 다른가요?

<details>
<summary>정답 보기</summary>

batch.size는 API에 보낼 Pod 요청 묶음을 제어합니다. min/initial/max는 executor 범위·시작 수이며 기존 executor.instances도 초기 수에 반영됩니다. 예제 min2·initial3·instances3은 처음 3개를 선택하며 노드 프로비저닝은 별도 과정입니다.

</details>

## 8. Spark cores·CPU limit·memory와 Pod template을 어떻게 해석해야 하나요?

<details>
<summary>정답 보기</summary>

cores는 기본 CPU request와 executor task 용량에 관련되며 CPU limit은 별도 limit.cores 설정입니다. JVM 예제 heap1GiB+최소overhead384MiB는 request/limit1408MiB입니다. Template은 제출자가 읽고 Spark가 합성하는 파일이며 이미지 없는 조각을 kubectl apply하는 완전한 Pod가 아닙니다.

</details>

## 9. Shuffle tracking과 정상 종료가 있어도 무엇을 검증해야 하나요?

<details>
<summary>정답 보기</summary>

Tracking·idle timeout, 강제 종료, node capacity와 블록 재계산을 확인합니다. Client mode에서는 executor→driver 주소·포트와 실제 driver Pod owner도 필요합니다. 중간 블록 보존이 checkpoint·driver 재시작·전체 경로 exactly-once를 대신하지는 않습니다.

</details>

---

[학습 자료로 돌아가기](../../../data-on-eks/spark/01-spark-fundamentals.md)
