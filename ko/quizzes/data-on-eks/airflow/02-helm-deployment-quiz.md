# Helm 배포와 Executor 선택 퀴즈

Chart 1.22.0 / Airflow 3.3.1 / KEDA 2.20.

## 1. 이 문서의 공식 chart 이름과 repository alias는?

<details>
<summary>정답 보기</summary>

Apache Airflow 프로젝트의 chart를 사용하며 저장소를 apache-airflow로 등록했으므로 명령에서는 apache-airflow/airflow를 지정합니다. 별도 커뮤니티 chart의 values 스키마와 혼용하지 않습니다.

</details>

## 2. Chart 1.22.0의 실제 기본 Airflow/executor는?

<details>
<summary>정답 보기</summary>

Airflow 3.2.2와 CeleryExecutor입니다. 본문의 3.3.1/KubernetesExecutor는 명시적으로 override한 profile이며 기본 설치 동작과 구분합니다.

</details>

## 3. 최소 버전이 모두 Chart.yaml에서 강제되나요?

<details>
<summary>정답 보기</summary>

그렇게 가정하면 안 됩니다. 현재는 Helm 3.19.0+를 사용하고 호환 Kubernetes/Airflow를 확인합니다. Chart 1.16 README는 Kubernetes 1.29+였으며, 검토한 1.22 템플릿도 1.29 대상으로 렌더링됐지만 지원 증명은 아닙니다.

</details>

## 4. Celery worker·Redis·리소스 종류를 executor 하나만으로 결정하나요?

<details>
<summary>정답 보기</summary>

Executor가 영향을 주지만 Redis 활성화/외부 broker, worker persistence 등의 값도 중요합니다. Worker는 Deployment 또는 StatefulSet일 수 있고 Celery에도 외부 broker를 사용할 수 있습니다.

</details>

## 5. PostgreSQL을 끄기만 하면 외부 DB가 연결되나요?

<details>
<summary>정답 보기</summary>

아닙니다. 준비된 DB·migration 권한·URI·TLS와 metadataSecretName 등의 연결 설정이 필요합니다. Secret 이름이 설정되면 metadataConnection은 우선 연결 출처가 아닙니다.

</details>

## 6. Fernet/API/JWT key를 upgrade 때 새로 만들어도 되나요?

<details>
<summary>정답 보기</summary>

일반 upgrade에서는 기존 키를 보존합니다. Fernet key 손실은 암호화된 데이터 접근에, JWT key 변경은 진행 중 task 인증에 영향을 줄 수 있습니다. 백업·회전은 별도 절차로 진행합니다.

</details>

## 7. 기본 admin/admin을 피하는 예제 방식은?

<details>
<summary>정답 보기</summary>

createUserJob.enabled=false로 기본 생성 Job을 끄고, 선택한 FAB auth manager의 airflow users create를 대화형으로 실행해 비밀번호를 두 번 입력합니다. 다른 auth manager/SSO에는 해당 절차를 사용합니다.

</details>

## 8. KubernetesExecutor 시작 지연은 항상 1–2분인가요?

<details>
<summary>정답 보기</summary>

아닙니다. Image cache/pull, Kubernetes API·scheduler, node 여유·증설, quota와 task runtime 초기화 등을 실제로 측정합니다. Celery도 scale-to-zero 뒤에는 cold start가 있습니다.

</details>

## 9. KubernetesExecutor worker에 임의 GPU/CLI image를 넣으면 되나요?

<details>
<summary>정답 보기</summary>

호환 Airflow task runtime과 DAG/provider 의존성이 있어야 합니다. KubernetesPodOperator가 별도 child Pod에 임의 작업 image를 실행하는 경로와 구분합니다.

</details>

## 10. Worker Pod가 없으면 Airflow 유휴 비용도 0인가요?

<details>
<summary>정답 보기</summary>

Control plane·DB·broker·노드·스토리지·로그 비용이 남을 수 있습니다. Pod별 실행이나 scale-to-zero만으로 모든 비용 또는 보안 격리가 보장되지 않습니다.

</details>

## 11. Chart 기본 KEDA 시간과 본문 예제의 시간은?

<details>
<summary>정답 보기</summary>

Chart 기본은 pollingInterval=5s, cooldownPeriod=30s입니다. 본문은 10s/300s를 명시적으로 선택했습니다. 0으로 줄이는 cooldown과 1개 이상 HPA 조정·stabilization은 구분합니다.

</details>

## 12. SQL의 worker_concurrency는 어떤 값이어야 하나요?

<details>
<summary>정답 보기</summary>

Chart가 넣은 숫자입니다. 예제에서는 4이며 DB column 이름 worker_concurrency가 아닙니다. running/queued task를 해당 queue/executor 범위로 세어 나눈 뒤 올림합니다.

</details>

## 13. 혼합 executor에서 k8s alias가 문제가 될 수 있는 이유는?

<details>
<summary>정답 보기</summary>

TaskInstance는 task.executor 값을 저장합니다. Chart 기본 필터가 KubernetesExecutor 문자열만 제외하면 k8s로 저장한 task는 Celery 집계에 포함될 수 있습니다. 실제 저장 값에 맞는 명시적 필터를 사용합니다.

</details>

## 14. 쿼리가 25를 반환하고 maxReplicaCount=20이면?

<details>
<summary>정답 보기</summary>

Worker는 설정한 최대값의 제약을 받으므로 모든 수요가 즉시 충족되지는 않습니다. Backlog·task concurrency·worker 자원·DB/broker·node 용량을 함께 확인합니다.

</details>

## 15. KEDA가 DB에 연결하려면 Airflow Pod의 TLS 설정만 있으면 되나요?

<details>
<summary>정답 보기</summary>

KEDA도 별도 DB client이므로 DNS·네트워크·권한·호환 URI·CA가 필요합니다. URI의 sslrootcert 경로는 scaler 프로세스에서도 읽혀야 하며 chart가 자동 복사하지 않습니다.

</details>

## 16. KEDA는 Deployment에만 사용할 수 있나요?

<details>
<summary>정답 보기</summary>

아닙니다. 이 chart의 Celery ScaledObject는 persistence에 따라 Deployment 또는 StatefulSet을 대상으로 합니다. KubernetesExecutor task Pod는 같은 방식의 고정 replica pool이 아니지만 다른 KEDA 사용까지 금지되는 것은 아닙니다.

</details>

## 17. Helm --wait 성공이면 설치 검증이 끝났나요?

<details>
<summary>정답 보기</summary>

Migration Job 성공, 장기 컴포넌트 Ready, DAG 전달·worker 실행·Execution API·결과·로그를 확인해야 합니다. KEDA profile은 실제 task 투입과 idle 복귀·오류 복구도 시험합니다.

</details>

## 18. Helm uninstall이 PostgreSQL 데이터를 즉시 전부 삭제하나요?

<details>
<summary>정답 보기</summary>

Pod 삭제와 PVC/PV 데이터 수명주기는 다릅니다. PVC retention, StorageClass reclaim policy, 외부 DB 삭제·백업 정책을 각각 확인하고 공유 namespace·Secret·DB를 일괄 삭제하지 않습니다.

</details>

[Guide](../../../data-on-eks/airflow/02-helm-deployment.md)

[Previous quiz](./01-architecture-quiz.md)
