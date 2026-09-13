# Spark Operator 퀴즈

Kubeflow 2.5.2와 Apache operator 1.0.0 / chart 1.8.0 기준입니다.

## 1. 두 Spark Operator의 관계는?

- A) 같은 chart의 이름 변경
- B) Kubeflow의 지원 종료 후 대체품
- C) 서로 다른 API와 수명주기를 가진 별개 프로젝트
- D) apiVersion만 바꾸면 완전히 호환

<details>
<summary>정답 보기</summary>

**정답: C**

Kubeflow는 sparkoperator.k8s.io/v1beta2, 이 장의 Apache 예제는 spark.apache.org/v1을 사용합니다. 필드와 상태·재시도 모델도 검토해야 합니다.

</details>

## 2. 검토한 Apache operator 1.0.0의 Helm chart 버전은?

- A) 1.0.0으로 반드시 동일
- B) Kubeflow와 같은 2.5.2
- C) Spark와 같은 4.2.0
- D) 1.8.0

<details>
<summary>정답 보기</summary>

**정답: D**

Chart 버전과 앱 버전은 별개입니다. 릴리스·chart metadata와 실제 렌더링 결과를 함께 확인합니다.

</details>

## 3. Comet 또는 Gluten을 사용하려면?

- A) 호환되는 plugin·이미지·classpath·설정을 검증
- B) Apache Operator만 설치하면 자동 가속
- C) 어떤 아키텍처·Spark 버전에서도 동일
- D) Kubeflow는 무조건 불가능

<details>
<summary>정답 보기</summary>

**정답: A**

공식 예제도 별도 의존성과 설정이 있습니다. Operator 선택만으로 성능이나 plugin 호환성이 보장되지 않습니다.

</details>

## 4. 일반 spark-submit에 관한 올바른 설명은?

- A) 항상 fire-and-forget
- B) 완료 대기와 로그 확인이 가능하지만 Operator CR 재조정은 별도
- C) Executor Pod를 만들 수 없음
- D) Git으로 설정 관리 불가

<details>
<summary>정답 보기</summary>

**정답: B**

네이티브 제출도 상태·로그·UI를 확인할 수 있습니다. Operator는 CR 상태 관리·예약 controller·애플리케이션 재시도를 추가합니다.

</details>

## 5. Kubeflow 2.5.2의 webhook.enable 기본값은?

- A) false
- B) Spark 버전마다 자동 변경
- C) true
- D) 설치 namespace가 default일 때만 true

<details>
<summary>정답 보기</summary>

**정답: C**

예제는 기본값을 명시합니다. 별도로 false로 바꾸면 해당 webhook 경로의 기능을 검토해야 합니다.

</details>

## 6. 두 chart의 admission 구조는?

- A) 두 chart 모두 같은 Pod mutator 설치
- B) Webhook이 노드 배치 수행
- C) Webhook이 Spark task 할당
- D) Kubeflow의 Pod mutator와 동일한 webhook을 Apache chart가 설치하지 않음

<details>
<summary>정답 보기</summary>

**정답: D**

이 장의 흐름도는 Kubeflow를 설명합니다. Kubernetes scheduler·kubelet과 Spark driver의 역할은 별개입니다.

</details>

## 7. 작업을 spark-jobs에 제출할 때 필요한 설정은?

- A) Controller watch 범위와 작업 namespace·RBAC를 일치시킴
- B) Operator 설치 namespace에만 모든 작업 제출
- C) ClusterRole만 있으면 watch 범위 불필요
- D) default namespace가 자동으로 모든 namespace를 포함

<details>
<summary>정답 보기</summary>

**정답: A**

설치 namespace와 작업 namespace는 다를 수 있습니다. 기본 watch 범위가 자동으로 새 작업 namespace를 포함하지는 않습니다.

</details>

## 8. Kubeflow에서 사용자 볼륨의 올바른 위치는?

- A) spec.driver.volumes만
- B) spec.volumes와 driver/executor.volumeMounts
- C) spec.executor.volumes만
- D) status.volumes

<details>
<summary>정답 보기</summary>

**정답: B**

Driver·executor의 volumes 필드는 해당 CRD에 없습니다. 볼륨은 공통 spec.volumes에 선언하고 필요한 컨테이너에 mount합니다.

</details>

## 9. spark-local-dir- 접두사의 의미는?

- A) 물리 NVMe 디스크를 자동 생성
- B) 모든 볼륨을 S3로 전환
- C) Operator가 native Spark 로컬 볼륨 설정으로 변환하는 특별 경로
- D) Webhook이 반드시 유일한 구현 경로

<details>
<summary>정답 보기</summary>

**정답: C**

일반 볼륨 mutator는 이 로컬 디렉터리 볼륨을 건너뛰고 제출 설정 변환 경로가 처리합니다. emptyDir 자체는 물리 디스크를 선택하지 않습니다.

</details>

## 10. Kubeflow 2.5.2의 유효한 serviceAccount 필드는?

- A) driver에만 존재
- B) executor에만 존재
- C) 둘 다 AWS IAM ARN이어야 함
- D) driver.serviceAccount와 executor.serviceAccount 모두

<details>
<summary>정답 보기</summary>

**정답: D**

두 필드 모두 Kubernetes service account 이름입니다. API RBAC와 AWS 데이터 접근 권한은 별도로 구성합니다.

</details>

## 11. ScheduledSparkApplication을 매일 02:00 UTC에 실행하려면?

- A) schedule: "0 2 * * *"와 timeZone: UTC
- B) Controller 로컬 시간대에 무조건 의존
- C) timeZone은 지원하지 않음
- D) Executor Pod의 TZ만 설정

<details>
<summary>정답 보기</summary>

**정답: A**

2.5.2는 timeZone을 지원하며 기본값은 Local입니다. 예약 시간대를 명시하면 운영 환경의 로컬 설정에 의존하지 않습니다.

</details>

## 12. concurrencyPolicy: Forbid가 막는 것은?

- A) 모든 시스템의 중복 데이터 쓰기
- B) 같은 예약 리소스의 이전 실행과 새 예약 실행의 겹침
- C) 애플리케이션 재시도 전부
- D) 수동 제출 전부

<details>
<summary>정답 보기</summary>

**정답: B**

다른 scheduler·수동 실행·재시도로 생기는 부작용은 별도입니다. 실제 출력은 멱등성 또는 트랜잭션을 설계합니다.

</details>

## 13. 예약 리소스의 suspend: true 효과는?

- A) 실행 중인 자식 작업을 반드시 종료
- B) 이미 쓴 데이터를 롤백
- C) 향후 예약 트리거를 중지
- D) Operator deployment 삭제

<details>
<summary>정답 보기</summary>

**정답: C**

현재 실행은 별도로 확인·종료해야 합니다. suspend는 데이터 롤백이나 백업 기능도 아닙니다.

</details>

## 14. sparkVersion: 4.2.0만 바꾸면 무엇이 보장되는가?

- A) Controller 런타임 자동 업그레이드
- B) 모든 Spark plugin 호환성
- C) Kubernetes 버전 자동 업그레이드
- D) Controller 내부 spark-submit 업그레이드는 보장되지 않음

<details>
<summary>정답 보기</summary>

**정답: D**

이 장의 Kubeflow 실습은 controller 제출 런타임에 맞춰 4.0.4를 사용합니다. 다른 조합은 별도 검증합니다.

</details>

## 15. Operator가 관찰하는 Pod 상태는?

- A) Driver와 executor 모두
- B) Driver만
- C) Executor만
- D) Pod는 전혀 관찰하지 않음

<details>
<summary>정답 보기</summary>

**정답: A**

Controller는 executor 상태도 반영하고 정리합니다. Executor 요청과 Spark task 할당은 Spark driver가 수행합니다.

</details>

## 16. OnFailure 재시도 시 주의할 점은?

- A) 정확히 한 번 쓰기가 자동 보장
- B) 애플리케이션 재실행이 출력 부작용을 반복할 수 있음
- C) 항상 같은 컨테이너만 재시작
- D) 실패한 외부 트랜잭션을 모두 자동 롤백

<details>
<summary>정답 보기</summary>

**정답: B**

제출·애플리케이션 재시도와 컨테이너 재시작은 다릅니다. 재시도 횟수·간격뿐 아니라 데이터 처리 의미를 검증합니다.

</details>

## 17. IRSA와 EKS Pod Identity의 차이는?

- A) 두 방식 모두 같은 annotation만 필요
- B) Kubernetes Role이 S3 권한 제공
- C) IRSA는 OIDC·role annotation, Pod Identity는 association·Agent 경로
- D) S3 URI만 지정하면 인증 완료

<details>
<summary>정답 보기</summary>

**정답: C**

AWS 권한·trust 또는 association과 호환 credential provider가 필요합니다. 실제 Pod에서 유효 ID와 접근을 검증합니다.

</details>

## 18. Chart의 기본 8080 Prometheus endpoint는?

- A) 모든 Spark JVM의 JMX 자동 수집
- B) Spark History Server 전체 로그
- C) S3 데이터 검증 결과
- D) Operator 메트릭

<details>
<summary>정답 보기</summary>

**정답: D**

작업 JMX는 애플리케이션 exporter JAR·설정과 scrape 구성이 별도로 필요합니다.

</details>

## 19. Helm으로 Operator를 업그레이드할 때 CRD는?

- A) 별도 CRD 변경 절차와 hook.upgradeCrd opt-in을 검토
- B) 일반 helm upgrade가 항상 자동 교체
- C) 기존 CRD를 무조건 삭제
- D) 애플리케이션 리소스에는 영향 없음

<details>
<summary>정답 보기</summary>

**정답: A**

crds/의 CRD는 일반 upgrade에서 자동 교체되지 않습니다. CRD 삭제는 해당 custom resource에 영향을 주므로 일상적인 업그레이드 수단으로 쓰지 않습니다.

</details>

## 20. Helm 렌더링·CRD 검증 통과의 의미는?

- A) 실제 webhook 연결까지 증명
- B) 리소스 형식과 설정 경로 검증이며 실제 작업 성공은 별도
- C) S3 권한과 결과 정확성까지 증명
- D) 모든 Spark 버전의 호환성 보장

<details>
<summary>정답 보기</summary>

**정답: B**

실제 Pod·status·출력·재시도와 권한을 추가 검증합니다. COMPLETED도 외부 데이터가 올바르다는 증거만으로 해석하지 않습니다.

</details>

[본문 / Guide](../../../data-on-eks/spark/02-spark-operator.md)
