# Flink Kubernetes Operator 퀴즈

이 퀴즈는 Flink Kubernetes Operator의 핵심 CRD, 업그레이드 모드, 내장 오토스케일러에 대한 이해도를 테스트합니다.

## 객관식 문제

1. `FlinkDeployment`와 `FlinkSessionJob`의 가장 큰 차이는 무엇인가요?
   - A) `FlinkDeployment`는 배치 잡 전용이고 `FlinkSessionJob`은 스트리밍 잡 전용이다
   - B) `FlinkDeployment`는 Application 모드 클러스터나 잡이 없는 Session 모드 클러스터를 정의하고, `FlinkSessionJob`은 이미 실행 중인 Session 모드 클러스터에 잡을 제출한다
   - C) 두 리소스는 동일한 대상을 가리키는 다른 이름일 뿐이다
   - D) `FlinkSessionJob`은 한 번만 실행 가능하며 독립적으로 삭제할 수 없다

<details>

<summary>정답 보기</summary>

**정답: B) `FlinkDeployment`는 Application 모드 클러스터나 잡이 없는 Session 모드 클러스터를 정의하고, `FlinkSessionJob`은 이미 실행 중인 Session 모드 클러스터에 잡을 제출한다**

**설명:**
`FlinkDeployment`는 Application 모드 클러스터에 잡을 직접 포함시켜 정의하거나, 잡이 붙어있지 않은 Session 모드 클러스터를 정의합니다. `FlinkSessionJob`은 이미 실행 중인 Session 모드 `FlinkDeployment` 위에 잡을 제출하며, 하나의 세션 클러스터는 각각 독립적으로 관리되는 여러 개의 `FlinkSessionJob`을 호스팅할 수 있습니다.
</details>

2. Flink Kubernetes Operator 1.15+가 요구하는 Kubernetes 버전과 그 이유는 무엇인가요?
   - A) Kubernetes 1.16+, CRD v1 지원 때문
   - B) Kubernetes 1.21+, 어드미션 웹훅이 의존하는 네임스페이스 자동 라벨링 기능이 이 버전부터 지원되기 때문
   - C) Kubernetes 1.25+, PodSecurityPolicy가 제거되었기 때문
   - D) 최소 버전 요구사항이 없다

<details>

<summary>정답 보기</summary>

**정답: B) Kubernetes 1.21+, 어드미션 웹훅이 의존하는 네임스페이스 자동 라벨링 기능이 이 버전부터 지원되기 때문**

**설명:**
Operator의 어드미션 웹훅은 네임스페이스 자동 라벨링 기능에 의존하며, 이 기능은 Kubernetes 1.21 이상부터 지원됩니다.
</details>

3. Operator 1.14.0 릴리스에서 네이티브로 추가된 기능은 무엇인가요?
   - A) 세이브포인트 기반 업그레이드
   - B) Blue/Green 배포
   - C) 내장 오토스케일러
   - D) Session 모드 클러스터

<details>

<summary>정답 보기</summary>

**정답: B) Blue/Green 배포**

**설명:**
2026년 2월에 나온 Operator 1.14.0은 네이티브 Blue/Green 배포 지원을 추가하여, 외부 스크립트 없이도 Operator 제어 하에 잡의 두 버전을 동시에 운영하고 전환할 수 있게 되었습니다.
</details>

4. 세 가지 `upgradeMode` 중 가장 안전하지만 가장 느린 것은 무엇인가요? (진행 전 stop-the-world 방식의 깨끗한 세이브포인트가 필요)
   - A) `stateless`
   - B) `last-state`
   - C) `savepoint`
   - D) `blue-green`

<details>

<summary>정답 보기</summary>

**정답: C) `savepoint`**

**설명:**
`savepoint` 모드는 명시적으로 세이브포인트를 생성한 뒤 클러스터를 안전하게 종료하고 해당 세이브포인트로부터 복원합니다. 가장 내구성 있고 검증 가능한 방식이지만, 기존 클러스터를 종료하기 전에 깨끗한 세이브포인트가 반드시 필요하기 때문에 가장 느립니다.
</details>

5. `last-state` 업그레이드 모드가 `savepoint` 모드와 달리 비정상 상태이거나 계속 실패 중인 잡에서도 동작할 수 있는 이유는 무엇인가요?
   - A) 체크포인팅을 완전히 건너뛰기 때문에
   - B) 새로운 세이브포인트를 생성할 필요 없이 가장 최근 체크포인트의 메타데이터를 사용하기 때문에
   - C) 상태를 전혀 가져오지 않고 잡을 재시작하기 때문에
   - D) 사람(운영자)의 수동 개입이 필요하기 때문에

<details>

<summary>정답 보기</summary>

**정답: B) 새로운 세이브포인트를 생성할 필요 없이 가장 최근 체크포인트의 메타데이터를 사용하기 때문에**

**설명:**
`last-state`는 새 세이브포인트 대신 가장 최근 체크포인트의 메타데이터로부터 복원하므로, 잡이 세이브포인트를 뜨기 위해 정상적으로 정지될 수 있을 만큼 건강한 상태일 필요가 없습니다. 그래서 이미 실패 중인 잡에서도 사용할 수 있습니다.
</details>

6. `last-state` 업그레이드 모드가 (`FlinkDeployment`뿐 아니라) `FlinkSessionJob`에서도 사용 가능해진 것은 몇 버전부터인가요?
   - A) 1.0.0
   - B) 1.10.0
   - C) 1.14.0
   - D) 1.15.0

<details>

<summary>정답 보기</summary>

**정답: B) 1.10.0**

**설명:**
`last-state`는 Operator 1.10.0부터 `FlinkSessionJob`에서도 사용할 수 있게 되었으며, 그 이전에는 `FlinkDeployment`에서만 사용 가능했습니다.
</details>

7. 일반적인 Kubernetes HPA와 달리, Flink 오토스케일러는 부하에 대응해 무엇을 조정하나요?
   - A) HPA와 동일하게 Pod 복제본 수
   - B) TaskManager Pod의 CPU/메모리 request/limit
   - C) 잡 그래프 안의 각 개별 vertex의 병렬도
   - D) 소스 토픽의 Kafka 파티션 수

<details>

<summary>정답 보기</summary>

**정답: C) 잡 그래프 안의 각 개별 vertex의 병렬도**

**설명:**
Pod 복제본 수를 조정하는 HPA와 달리, Flink 오토스케일러는 각 vertex(소스, 맵, 조인, 싱크 등)의 병렬도를 그 vertex 자체의 처리 요구량에 맞춰 개별적으로 조정합니다.
</details>

8. 하위(비소스) vertex의 목표 처리율은 어떻게 계산되나요?
   - A) 사용자가 지정한 고정 값
   - B) 이 vertex로 유입되는 모든 상위 vertex의 출력 속도의 합
   - C) TaskManager Pod의 평균 CPU 사용률
   - D) 전체 잡의 Kafka 컨슈머 랙(lag)

<details>

<summary>정답 보기</summary>

**정답: B) 이 vertex로 유입되는 모든 상위 vertex의 출력 속도의 합**

**설명:**
소스 vertex의 목표 처리율은 유입 데이터 속도이고, 하위 vertex의 목표 처리율은 상위 vertex들의 출력 속도의 합입니다. 오토스케일러는 이 목표 처리율을 설정된 사용률 목표에서 감당할 수 있는 병렬도를 역산합니다.
</details>

9. 오토스케일러가 부하를 감지할 때 CPU/메모리 지표를 의도적으로 사용하지 않는 이유는 무엇인가요?
   - A) Kubernetes에서 CPU/메모리 지표를 사용할 수 없기 때문
   - B) vertex가 느린 I/O를 기다리는 동안 CPU는 유휴 상태이면서도 병목일 수 있으므로, busy time과 처리율 지표가 실제 처리량 압박을 더 직접적으로 반영하기 때문
   - C) CPU/메모리 지표를 사용하려면 별도의 Prometheus 설치가 필요하기 때문
   - D) Flink vertex는 CPU나 메모리를 전혀 소비하지 않기 때문

<details>

<summary>정답 보기</summary>

**정답: B) vertex가 느린 I/O를 기다리는 동안 CPU는 유휴 상태이면서도 병목일 수 있으므로, busy time과 처리율 지표가 실제 처리량 압박을 더 직접적으로 반영하기 때문**

**설명:**
데이터플로우 엔진에서는 vertex가 I/O를 기다리며 CPU는 유휴 상태이면서도 병목일 수 있고, 반대로 CPU는 바쁘면서도 실제 부하 압박은 없을 수 있습니다. busy time, 백로그, 처리율 지표는 Flink가 입력을 따라갈 수 있는지를 결정하는 실제 처리량 압박을 직접 반영하는 반면, CPU/메모리는 이를 대변하기에 적합하지 않습니다.
</details>

10. `pipeline.max-parallelism`을 고합성수(예: 360)로 설정하는 것이 권장되는 이유는 무엇인가요?
    - A) JVM 힙 사용량이 줄어들기 때문
    - B) Flink의 key-group 모델이 max-parallelism을 선택된 병렬도로 균등하게 나누기 때문에, 고합성수로 설정하면 오토스케일러가 고를 수 있는 유효한 약수 후보가 훨씬 많아진다
    - C) Kubernetes 스케줄러가 이를 요구하기 때문
    - D) 체크포인팅 오버헤드가 사라지기 때문

<details>

<summary>정답 보기</summary>

**정답: B) Flink의 key-group 모델이 max-parallelism을 선택된 병렬도로 균등하게 나누기 때문에, 고합성수로 설정하면 오토스케일러가 고를 수 있는 유효한 약수 후보가 훨씬 많아진다**

**설명:**
Flink의 key-group 모델에서는 max-parallelism이 실제 병렬도로 균등하게 나누어져야 하므로, 120, 180, 240, 360, 720처럼 약수가 많은 고합성수는 소수보다 훨씬 많은 약수를 가져 오토스케일러가 선택할 수 있는 유효한 병렬도 값이 늘어납니다.
</details>

## 단답형 문제

11. 오토스케일러가 vertex를 리스케일하기로 결정했을 때, 내부적으로 어떤 업그레이드 메커니즘을 사용하나요?

<details>

<summary>정답 보기</summary>

**정답: `last-state` 업그레이드**

**설명:**
오토스케일러가 스케일링 임계값을 넘으면, 수동 `last-state` 업그레이드와 동일한 메커니즘을 통해 리스케일을 트리거합니다 — 빠르고, 잡이 완전히 정상적이지 않아도 동작합니다.
</details>

12. Operator 1.15.0이 잡 런타임으로 지원하는 Flink 버전들은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: Flink 2.2.x, 2.1.x, 2.0.x, 1.20.x, 1.19.x**

**설명:**
2026년 5월에 나온 Operator 1.15.0은 이 다섯 개의 Flink 마이너 버전 라인을 잡 런타임으로 지원합니다.
</details>

13. Operator 1.15.0이 추가한 로깅/메트릭 관련 두 가지 새로운 기능은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: 기본 Log4j2와 함께 선택 가능한 Logback 로깅 옵션, 그리고 Helm 차트에 기본으로 포함된 `flink-metrics-dropwizard` 리포터**

**설명:**
1.15.0은 `FlinkDeployment.status`에 Kubernetes 네이티브 `Conditions`를 추가한 것 외에도, Log4j2와 함께 사용할 수 있는 Logback 옵션과 Helm 차트에 기본 포함된 Dropwizard 메트릭 리포터를 추가했습니다.
</details>

14. Operator가 클러스터 전체가 아니라 특정 네임스페이스만 감시하도록 범위를 제한하는 Helm 차트 값은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: `watchNamespaces`**

**설명:**
Operator는 기본적으로 모든 네임스페이스를 감시합니다. `watchNamespaces` 값을 설정하면(예: `--set watchNamespaces="{flink,flink-staging}"`) 지정된 네임스페이스만 감시하도록 제한할 수 있습니다.
</details>

15. 오토스케일러가 스케일링 결정을 내리기 전에 지표를 평활화하는 데 사용하는 롤링 윈도우를 제어하는 설정 키는 무엇이며, 권장 범위는 어떻게 되나요?

<details>

<summary>정답 보기</summary>

**정답: `job.autoscaler.metrics.window`, 권장 범위는 3~60분**

**설명:**
윈도우가 너무 짧으면 노이즈에 반응하고, 너무 길면 실제 부하 변화에 너무 늦게 반응합니다. 권장 범위는 3~60분입니다.
</details>

## 실습 문제

16. Flink Kubernetes Operator를 Helm으로 `flink` 네임스페이스에 설치하는 전체 명령어 시퀀스를 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```bash
# Flink Kubernetes Operator Helm 저장소 추가
helm repo add flink-operator-repo https://downloads.apache.org/flink/flink-kubernetes-operator-1.15.0/
helm repo update

# flink 네임스페이스에 Operator 설치
helm install flink-kubernetes-operator flink-operator-repo/flink-kubernetes-operator \
  --namespace flink \
  --create-namespace

# 설치 확인
kubectl get pods -n flink
kubectl get crd | grep flink
```

**설명:**
`helm repo add`로 Operator의 Helm 저장소를 등록하고, `helm install`에 `--create-namespace`를 추가하면 `flink` 네임스페이스가 없어도 자동으로 생성됩니다. `kubectl get crd | grep flink`로 `FlinkDeployment`, `FlinkSessionJob` CRD가 등록되었는지 확인할 수 있습니다.
</details>

17. `upgradeMode: last-state`와 병렬도 4로 설정된 Application 모드 `FlinkDeployment`를 최소 구성으로 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```yaml
apiVersion: flink.apache.org/v1beta1
kind: FlinkDeployment
metadata:
  name: order-events-processor
  namespace: flink
spec:
  image: apache/flink:2.1.0
  flinkVersion: v2_1
  serviceAccount: flink
  jobManager:
    resource:
      memory: "2048m"
      cpu: 1
  taskManager:
    resource:
      memory: "4096m"
      cpu: 2
  job:
    jarURI: local:///opt/flink/usrlib/order-events-processor.jar
    entryClass: com.example.flink.OrderEventsJob
    parallelism: 4
    upgradeMode: last-state
```

**설명:**
`jarURI`와 `entryClass`가 포함된 `spec.job`이 있으면 이 `FlinkDeployment`는 Application 모드입니다 — 잡이 별도의 `FlinkSessionJob`으로 제출되는 것이 아니라 클러스터 정의 자체에 포함되어 있습니다. `upgradeMode: last-state`는 이후 스펙 변경(및 오토스케일러 리스케일)이 새 세이브포인트 없이 가장 최근 체크포인트로부터 복원됨을 의미합니다.
</details>

18. 목표 사용률 0.6, 10분 메트릭 윈도우, 고합성수로 설정된 `pipeline.max-parallelism`으로 오토스케일러를 활성화하는 `flinkConfiguration` 블록을 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```yaml
flinkConfiguration:
  job.autoscaler.enabled: "true"
  job.autoscaler.target.utilization: "0.6"
  job.autoscaler.metrics.window: "10m"
  pipeline.max-parallelism: "360"
```

**설명:**
`job.autoscaler.target.utilization: "0.6"`은 오토스케일러가 각 vertex에서 유지하려는 busy time 비율입니다. `job.autoscaler.metrics.window: "10m"`은 권장 범위인 3~60분 안에 들어갑니다. `pipeline.max-parallelism: "360"`은 고합성수(1, 2, 3, 4, 5, 6, 8, 9, 10, 12 등으로 나누어짐)이므로 오토스케일러가 선택할 수 있는 유효한 병렬도 값이 많습니다.
</details>

19. `FlinkDeployment`를 적용한 뒤 사용 가능해질 때까지 대기하는 `kubectl` 명령어를 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```bash
kubectl apply -f order-events-processor.yaml -n flink
kubectl get flinkdeployment -n flink
kubectl wait --for=condition=Available flinkdeployment/order-events-processor -n flink --timeout=180s
```

**설명:**
`kubectl wait --for=condition=Available`은 Operator 1.15.0이 `FlinkDeployment.status`에 추가한 Kubernetes 네이티브 `Conditions`를 활용합니다. 이를 통해 `.status.jobStatus.state`를 직접 폴링하는 대신 특정 조건이 될 때까지 블로킹할 수 있습니다.
</details>

20. `job.autoscaler.catch-up.duration` 설정이 백로그를 처리 중인 vertex를 오토스케일러가 과도하게 스케일업하지 않도록 방지하는 이유를 직접 설명하세요.

<details>

<summary>정답 보기</summary>

**정답:**
백로그를 처리 중인 vertex는 새로운 데이터뿐 아니라 밀린 과거 데이터까지 함께 처리하기 때문에, 일시적으로 평상시보다 높은 처리율과 busy time을 보입니다. `job.autoscaler.catch-up.duration`이 없다면 오토스케일러는 이 일시적인 캐치업 스파이크를 영구적인 부하 증가로 오인해 불필요하게 vertex를 스케일업할 수 있습니다. catch-up duration은 오토스케일러가 이를 지속적인 부하로 반응하기 전에, vertex가 백로그를 처리할 수 있는 시간 여유를 부여합니다.

**설명:**
이 설정은 일시적인 백로그 해소 스파이크와 실제로 지속되는 유입 데이터 속도 증가를 구분해주어, 일시적인 상황 때문에 불필요한 리스케일(그리고 이로 인해 트리거되는 `last-state` 업그레이드)이 발생하지 않도록 합니다.
</details>

---

[학습 자료로 돌아가기](../../../data-on-eks/flink/02-flink-kubernetes-operator.md)
