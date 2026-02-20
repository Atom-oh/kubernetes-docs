# CloudWatch Metrics 퀴즈

CloudWatch Metrics에 대한 이해도를 테스트하는 퀴즈입니다.

---

1. Amazon CloudWatch Container Insights의 주요 기능은?
   - A) 컨테이너 이미지 빌드
   - B) EKS 클러스터의 컨테이너/파드 수준 모니터링
   - C) 컨테이너 오케스트레이션
   - D) CI/CD 파이프라인 관리

<details>
<summary>정답 보기</summary>

**정답: B) EKS 클러스터의 컨테이너/파드 수준 모니터링**

**설명:**
Container Insights는 EKS, ECS, Kubernetes 환경의 컨테이너화된 워크로드를 모니터링하는 CloudWatch 기능입니다. 클러스터, 노드, 파드, 컨테이너 수준의 CPU, 메모리, 네트워크, 파일시스템 메트릭을 자동으로 수집하고 시각화합니다.

</details>

---

2. CloudWatch Agent를 EKS에 배포하는 권장 방식은?
   - A) 단일 Pod로 배포
   - B) DaemonSet으로 모든 노드에 배포
   - C) Deployment로 3개 복제본 배포
   - D) StatefulSet으로 배포

<details>
<summary>정답 보기</summary>

**정답: B) DaemonSet으로 모든 노드에 배포**

**설명:**
CloudWatch Agent는 DaemonSet으로 배포하여 각 노드에서 메트릭과 로그를 수집합니다. 이를 통해 모든 노드의 시스템 메트릭, 컨테이너 메트릭, 로그를 일관되게 수집할 수 있습니다.

</details>

---

3. CloudWatch Metric Math에서 `SEARCH()` 함수의 용도는?
   - A) 로그 검색
   - B) 패턴에 맞는 메트릭을 동적으로 검색
   - C) 알림 검색
   - D) 대시보드 검색

<details>
<summary>정답 보기</summary>

**정답: B) 패턴에 맞는 메트릭을 동적으로 검색**

**설명:**
`SEARCH()` 함수는 네임스페이스, 차원, 메트릭 이름 패턴을 사용하여 메트릭을 동적으로 검색합니다. 예를 들어, `SEARCH('{AWS/EC2,InstanceId} MetricName="CPUUtilization"', 'Average')`는 모든 EC2 인스턴스의 CPU 사용률을 검색합니다.

</details>

---

4. CloudWatch Anomaly Detection의 동작 방식은?
   - A) 수동으로 설정한 임계값 기반 탐지
   - B) ML 기반 자동 이상 패턴 탐지
   - C) 로그 패턴 분석
   - D) 네트워크 트래픽 분석

<details>
<summary>정답 보기</summary>

**정답: B) ML 기반 자동 이상 패턴 탐지**

**설명:**
CloudWatch Anomaly Detection은 머신러닝을 사용하여 메트릭의 정상 패턴을 학습하고, 비정상적인 값을 자동으로 감지합니다. 계절성, 추세, 요일별 패턴 등을 고려하여 동적인 예상 범위(band)를 생성하고, 이 범위를 벗어나면 이상으로 판단합니다.

</details>

---

5. AWS Distro for OpenTelemetry (ADOT)를 사용하여 Prometheus 메트릭을 CloudWatch로 전송할 때 사용하는 exporter는?
   - A) prometheus-exporter
   - B) awsemf (AWS EMF Exporter)
   - C) cloudwatch-exporter
   - D) metric-exporter

<details>
<summary>정답 보기</summary>

**정답: B) awsemf (AWS EMF Exporter)**

**설명:**
ADOT에서 Prometheus 메트릭을 CloudWatch로 전송하려면 AWS EMF(Embedded Metric Format) Exporter를 사용합니다. 이 exporter는 메트릭을 CloudWatch Logs의 EMF 형식으로 변환하여 전송하고, CloudWatch가 이를 메트릭으로 추출합니다.

</details>

---

6. CloudWatch 비용 최적화를 위한 방법으로 올바르지 않은 것은?
   - A) 로그 보존 기간 설정
   - B) 불필요한 고해상도 메트릭 제거
   - C) 모든 메트릭을 1초 간격으로 수집
   - D) Infrequent Access 로그 클래스 활용

<details>
<summary>정답 보기</summary>

**정답: C) 모든 메트릭을 1초 간격으로 수집**

**설명:**
고해상도 메트릭(1초 간격)은 비용이 높습니다. 비용 최적화를 위해서는 필요한 메트릭만 고해상도로 수집하고, 대부분의 메트릭은 60초 간격(기본)으로 수집하는 것이 좋습니다. 로그 보존 기간 설정, 불필요한 메트릭 필터링, Infrequent Access 로그 클래스 활용도 비용 절감에 도움됩니다.

</details>

---

7. CloudWatch 커스텀 메트릭을 생성할 때 사용하는 API는?
   - A) CreateMetric
   - B) PutMetricData
   - C) PublishMetric
   - D) SendMetric

<details>
<summary>정답 보기</summary>

**정답: B) PutMetricData**

**설명:**
`PutMetricData` API를 사용하여 CloudWatch에 커스텀 메트릭을 전송합니다. 네임스페이스, 메트릭 이름, 차원, 값, 단위, 타임스탬프 등을 지정할 수 있습니다. AWS SDK나 CLI를 통해 호출할 수 있습니다.

</details>

---

8. CloudWatch에서 차원(Dimension)의 역할은?
   - A) 메트릭의 단위 지정
   - B) 메트릭을 세분화하는 키-값 쌍
   - C) 알림 심각도 지정
   - D) 로그 그룹 지정

<details>
<summary>정답 보기</summary>

**정답: B) 메트릭을 세분화하는 키-값 쌍**

**설명:**
차원(Dimension)은 메트릭을 세분화하고 식별하는 키-값 쌍입니다. 예를 들어, EC2 인스턴스 메트릭에서 `InstanceId` 차원으로 특정 인스턴스를 식별합니다. 하나의 메트릭에 최대 30개의 차원을 지정할 수 있습니다.

</details>

---

9. Enhanced Container Insights가 기본 Container Insights와 다른 점은?
   - A) 무료로 제공됨
   - B) 추가 메트릭과 더 세분화된 모니터링 제공
   - C) 로그 수집 기능 제거
   - D) 알림 기능만 제공

<details>
<summary>정답 보기</summary>

**정답: B) 추가 메트릭과 더 세분화된 모니터링 제공**

**설명:**
Enhanced Container Insights는 기본 Container Insights보다 더 많은 메트릭을 수집합니다. 예약된 CPU/메모리 용량, GPU 메트릭(해당 시), Kubernetes 컨트롤 플레인 메트릭 등 추가 정보를 제공합니다. 추가 비용이 발생하지만 더 상세한 모니터링이 가능합니다.

</details>

---

10. CloudWatch 알림에서 `ANOMALY_DETECTION_BAND()` 함수의 역할은?
    - A) 고정 임계값 설정
    - B) 이상 탐지 모델의 예상 범위 반환
    - C) 로그 필터링
    - D) 대시보드 생성

<details>
<summary>정답 보기</summary>

**정답: B) 이상 탐지 모델의 예상 범위 반환**

**설명:**
`ANOMALY_DETECTION_BAND()` 함수는 이상 탐지 모델이 학습한 예상 값의 범위(상한/하한)를 반환합니다. 알림에서 이 범위를 사용하여 메트릭이 예상 범위를 벗어날 때 알림을 트리거할 수 있습니다. 두 번째 인자로 표준편차 배수를 지정하여 범위의 폭을 조절합니다.

</details>
