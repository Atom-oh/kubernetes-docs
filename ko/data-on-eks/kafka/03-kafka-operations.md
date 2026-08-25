# Part 3: Kafka 운영

> **지원 버전**: Strimzi 0.45+, Kafka 3.9\
> **마지막 업데이트**: 2026년 7월 9일

Strimzi Operator로 Kafka 클러스터를 배포한 이후에는 스토리지 용량 계획, 브로커 스케일링, 파티션 재배치, 무중단 업그레이드 같은 운영 작업이 이어집니다. 이 문서는 EKS 위에서 Strimzi가 관리하는 Kafka 클러스터를 실제로 운영할 때 마주치는 핵심 작업을 다룹니다.

## 스토리지 설계

### EBS 볼륨 타입 선택: gp3 vs io2

Kafka 브로커의 로그 세그먼트는 순차 쓰기/읽기가 대부분이지만, 컨슈머 랙(consumer lag)이 커지면 오래된 세그먼트에 대한 랜덤 읽기가 발생할 수 있습니다. EBS 볼륨 타입은 이 특성에 맞춰 선택합니다.

| 항목 | gp3 | io2 |
|------|-----|-----|
| **과금 방식** | 용량 기준, IOPS/처리량은 별도 프로비저닝 | IOPS 기준 (더 높은 단가) |
| **처리량** | 기본 125MB/s, 최대 1,000MB/s로 개별 조정 가능 | 볼륨 크기와 IOPS에 연동 |
| **최대 IOPS** | 16,000 | 256,000 |
| **적합한 워크로드** | 대부분의 Kafka 워크로드 — 처리량이 병목인 경우 | 컨슈머 랙 급증, 다수의 소규모 랜덤 I/O가 빈번한 지연시간 민감 워크로드 |
| **내구성(연간 오류율)** | 99.8~99.9% | 99.999% |

일반적인 이벤트 스트리밍 워크로드는 **gp3**로 시작해 처리량(throughput)과 IOPS를 필요에 맞게 개별 프로비저닝하는 것이 비용 효율적입니다. 다수의 컨슈머 그룹이 서로 다른 오프셋에서 동시에 읽어 랜덤 I/O 비중이 높거나, p99 지연시간 SLA가 엄격한 경우에만 **io2**로 전환을 고려합니다.

### JBOD를 이용한 멀티 볼륨 스토리지

Strimzi는 브로커당 여러 개의 독립된 볼륨을 사용하는 JBOD(Just a Bunch Of Disks) 구성을 지원합니다. 하나의 대형 볼륨 대신 여러 개의 볼륨으로 나누면 볼륨 단위로 처리량을 병렬화할 수 있고, 볼륨을 개별적으로 추가/교체할 수 있습니다.

```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaNodePool
metadata:
  name: broker
  labels:
    strimzi.io/cluster: my-cluster
spec:
  replicas: 3
  roles:
    - broker
  storage:
    type: jbod
    volumes:
      - id: 0
        type: persistent-claim
        size: 500Gi
        class: gp3-encrypted
        deleteClaim: false
      - id: 1
        type: persistent-claim
        size: 500Gi
        class: gp3-encrypted
        deleteClaim: false
  resources:
    requests:
      memory: 8Gi
      cpu: "2"
    limits:
      memory: 8Gi
      cpu: "4"
```

각 `volumes` 항목의 `id`는 브로커 내에서 로그 디렉터리를 구분하는 데 사용되며, 파티션은 라운드 로빈 방식으로 볼륨에 분산 배치됩니다. `deleteClaim: false`는 브로커 스케일 다운이나 재생성 시 PVC가 삭제되지 않도록 보호합니다.

> **참고**: Strimzi를 사용하면 브로커 파드가 시작될 때 `kafka-storage.sh format`을 Operator가 자동으로 처리하므로, 볼륨 포맷을 위해 이 스크립트를 직접 실행할 필요가 없습니다.

### 스토리지 사이징 가이드

디스크 용량은 다음 공식을 기준으로 산정합니다.

```
필요 디스크 용량 = 보존 기간 × 피크 처리량(초당 바이트) × 복제 팩터 × (1 + 헤드룸 비율)
```

예를 들어 피크 처리량 50MB/s, 보존 기간 7일(`604,800초`), 복제 팩터 3, 헤드룸 30%를 가정하면:

```
50MB/s × 604,800s × 3 × 1.3 ≈ 118TB (클러스터 전체)
```

브로커 3대로 나누면 브로커당 약 39TB가 필요합니다. 헤드룸을 반드시 확보해야 하는 이유는, Kafka 브로커는 디스크 사용률이 임계치(기본적으로 로그 클리너와 세그먼트 롤링 동작에 영향)를 넘으면 성능이 급격히 저하되고, `log.retention.bytes`/`log.retention.hours` 기준 삭제가 지연되면 디스크가 가득 차 브로커가 오프라인 상태가 될 수 있기 때문입니다. 최소 20~30%의 여유 공간을 항상 유지하는 것을 권장합니다.

## 브로커/컨트롤러 스케일링

### 브로커 스케일 아웃

`KafkaNodePool`의 `replicas` 값을 늘리면 Strimzi가 새 브로커 파드를 생성하고 클러스터에 자동으로 합류시킵니다.

```bash
kubectl patch kafkanodepool broker -n kafka --type=merge \
  -p '{"spec":{"replicas":6}}'

# 새 브로커가 클러스터에 합류했는지 확인
kubectl get pods -n kafka -l strimzi.io/pool-name=broker
```

새로 추가된 브로커는 기존 파티션의 리더/팔로워로 자동 선출되지 않습니다. 기존 토픽의 파티션을 새 브로커로 재분배하려면 별도의 파티션 재배치 작업이 필요합니다.

### 파티션 재배치 (`kafka-reassign-partitions.sh`)

```bash
# 1) 재배치 대상 토픽을 정의하는 JSON을 브로커 파드 내부에 작성
kubectl exec -it my-cluster-broker-0 -n kafka -- bash -c 'cat <<EOF > /tmp/topics-to-move.json
{
  "topics": [{"topic": "orders"}, {"topic": "payments"}],
  "version": 1
}
EOF'

# 2) 브로커 ID 목록을 지정해 재배치 계획을 생성하고, 파드 내부 파일로 저장
kubectl exec -it my-cluster-broker-0 -n kafka -- bash -c '
  bin/kafka-reassign-partitions.sh \
    --bootstrap-server localhost:9092 \
    --topics-to-move-json-file /tmp/topics-to-move.json \
    --broker-list "0,1,2,3,4,5" \
    --generate > /tmp/generate-output.txt
  # --generate 출력에는 현재 배치(Current)와 제안 배치(Proposed) JSON이 함께 들어있으므로,
  # "Proposed partition reassignment configuration" 아래의 JSON만 추출해 저장
  awk "/^Proposed partition reassignment configuration/{flag=1; next} flag" /tmp/generate-output.txt > /tmp/reassignment.json
'

# 3) 생성된 계획(reassignment.json)을 실제로 적용
kubectl exec -it my-cluster-broker-0 -n kafka -- \
  bin/kafka-reassign-partitions.sh \
  --bootstrap-server localhost:9092 \
  --reassignment-json-file /tmp/reassignment.json \
  --execute

# 4) 진행 상태 확인
kubectl exec -it my-cluster-broker-0 -n kafka -- \
  bin/kafka-reassign-partitions.sh \
  --bootstrap-server localhost:9092 \
  --reassignment-json-file /tmp/reassignment.json \
  --verify
```

### 브로커 스케일 다운은 왜 위험한가

**Strimzi는 브로커를 스케일 다운할 때 파티션을 자동으로 드레인(drain)하지 않습니다.** `KafkaNodePool`의 `replicas`를 줄이기 전에, 제거할 브로커에 할당된 모든 파티션(리더 및 팔로워 레플리카 포함)을 남아 있는 브로커로 먼저 재배치해야 합니다. 이 순서를 지키지 않으면 해당 브로커에만 존재하던 레플리카가 사라져 언더 리플리케이트(under-replicated) 파티션이 발생하거나, 최악의 경우 데이터 손실로 이어질 수 있습니다.

안전한 스케일 다운 절차는 다음과 같습니다.

1. `kafka-reassign-partitions.sh --generate`로 제거 대상 브로커를 제외한 브로커 목록만으로 재배치 계획 생성
2. `--execute`로 재배치 적용 후 `--verify`로 완료 확인 (언더 리플리케이트 파티션이 0인지 확인)
3. 재배치가 완전히 끝난 뒤에만 `KafkaNodePool.spec.replicas`를 줄여 브로커 파드 제거

## Cruise Control을 이용한 자동 리밸런싱

Cruise Control은 브로커 간 디스크 사용량, CPU, 네트워크 처리량 등의 부하 지표를 지속적으로 수집하고, 이를 기반으로 파티션 재배치 계획을 자동으로 생성/실행하는 컴포넌트입니다. 브로커를 추가하거나 제거할 때마다 `kafka-reassign-partitions.sh`를 수동으로 실행하는 대신, 목표(goal) 기반으로 리밸런싱을 위임할 수 있습니다.

### Cruise Control 활성화

```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: Kafka
metadata:
  name: my-cluster
spec:
  kafka:
    version: 3.9.0
    # ... 기존 kafka 설정 ...
  cruiseControl:
    config:
      # 목표: 디스크/CPU/네트워크 사용량을 브로커 간 균등하게 유지
      goals: >-
        com.linkedin.kafka.cruisecontrol.analyzer.goals.RackAwareGoal,
        com.linkedin.kafka.cruisecontrol.analyzer.goals.DiskCapacityGoal,
        com.linkedin.kafka.cruisecontrol.analyzer.goals.CpuCapacityGoal,
        com.linkedin.kafka.cruisecontrol.analyzer.goals.NetworkInboundCapacityGoal,
        com.linkedin.kafka.cruisecontrol.analyzer.goals.NetworkOutboundCapacityGoal
```

### `KafkaRebalance` 리소스로 리밸런싱 트리거

```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaRebalance
metadata:
  name: my-rebalance
  namespace: kafka
  labels:
    strimzi.io/cluster: my-cluster
spec:
  mode: full
```

```bash
# 리밸런싱 계획 생성 (아직 실행되지 않음, PendingProposal → ProposalReady)
kubectl get kafkarebalance my-rebalance -n kafka -o yaml

# 생성된 계획을 승인해 실제 리밸런싱 실행
kubectl annotate kafkarebalance my-rebalance -n kafka \
  strimzi.io/rebalance=approve

# 진행 상태 확인
kubectl get kafkarebalance my-rebalance -n kafka -w
```

### 리밸런싱 모드

| 모드 | 용도 |
|------|------|
| `full` (기본값) | 클러스터의 모든 브로커를 대상으로 설정된 목표에 따라 전체 리밸런싱 계획 생성 |
| `add-brokers` | 새로 추가된 브로커로만 파티션을 이동시켜 신규 브로커의 부하를 채우는 데 특화 (전체 재배치보다 빠르고 영향 범위가 작음) |
| `remove-brokers` | 제거할 브로커의 파티션만 나머지 브로커로 옮기는 데 특화 — 스케일 다운 전 안전한 드레인 절차로 활용 |

브로커를 추가/제거하는 스케일링 작업 직후에는 `add-brokers` 또는 `remove-brokers` 모드로 범위를 좁혀 리밸런싱하면, 관련 없는 파티션까지 불필요하게 이동시키는 `full` 모드보다 네트워크 부하와 소요 시간을 줄일 수 있습니다.

## 롤링 업그레이드

### CR 스펙 변경에 따른 자동 롤링 재시작

`Kafka` 또는 `KafkaNodePool` CR의 스펙(리소스 요청/제한, 설정 값, 볼륨 등)을 변경하면 Strimzi Operator는 이를 감지해 **브로커 파드를 한 번에 하나씩** 재시작합니다. 이 과정에서 Operator는 각 파티션의 `min.insync.replicas`를 만족하는 범위 내에서만 재시작을 진행하도록 조율하여, 재시작으로 인해 특정 파티션의 가용 레플리카 수가 요구치 밑으로 떨어지지 않도록 보장합니다.

### Kafka 버전 업그레이드 — 2단계 절차

KRaft 모드에서는 ZooKeeper 시절의 `inter.broker.protocol.version`/`log.message.format.version` 대신, `Kafka` CR의 `spec.kafka.version`(소프트웨어 버전)과 `spec.kafka.metadataVersion`(KRaft 메타데이터 로그 포맷 버전)을 **동시에 올리지 않고 두 단계로 나누어 진행**해야 합니다. `metadataVersion`은 컨트롤러 쿼럼이 메타데이터를 기록하는 포맷을 결정하므로, 신버전과 구버전 브로커/컨트롤러가 혼재하는 롤링 업그레이드 도중에는 이전 포맷을 유지해야 합니다.

**1단계 — 소프트웨어 버전만 업그레이드**

```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: Kafka
metadata:
  name: my-cluster
spec:
  kafka:
    version: 3.9.0
    # metadataVersion은 이전 버전으로 유지
    metadataVersion: 3.8-IV0
```

이 상태로 적용하면 Strimzi가 브로커/컨트롤러 소프트웨어를 롤링 방식으로 3.9.0으로 교체하지만, 메타데이터 포맷은 여전히 3.8-IV0 방식을 사용합니다. 이렇게 하면 업그레이드 도중 신버전과 구버전 노드가 혼재하는 시점에도 동일한 메타데이터 포맷으로 컨트롤러 쿼럼이 정상 동작합니다.

**2단계 — 모든 노드 교체 확인 후 metadataVersion 상향**

```yaml
    version: 3.9.0
    metadataVersion: 3.9-IV0
```

모든 브로커/컨트롤러가 3.9.0으로 정상 교체된 것을 확인한 뒤에만 `metadataVersion`을 올립니다. 이 변경 역시 새 메타데이터 포맷을 반영하기 위한 조정을 한 번 더 유발합니다. 순서를 바꿔 소프트웨어 버전과 `metadataVersion`을 동시에 올리면, 아직 이전 버전으로 실행 중인 노드가 새 메타데이터 포맷을 이해하지 못해 컨트롤러 쿼럼 통신 오류가 발생할 수 있습니다.

### Strimzi Operator 버전 업그레이드

Kafka 버전을 올리기 전에 **Strimzi Operator 자체를 먼저 최신 버전으로 업그레이드**해야 합니다. 각 Strimzi 버전은 지원하는 Kafka 버전 범위가 명시되어 있으며, Operator가 인식하지 못하는 Kafka 버전으로 CR을 변경하면 검증에 실패합니다. 일반적인 순서는 Operator 업그레이드 → Operator가 재조정(reconcile)을 완료할 시간 확보 → Kafka 소프트웨어 버전 업그레이드(1단계) → `metadataVersion` 업그레이드(2단계)입니다.

## 장애 대응 기초

### PodDisruptionBudget과 브로커 파드 축출

Strimzi는 `KafkaNodePool`마다 `PodDisruptionBudget`(PDB)을 자동으로 생성합니다. 기본값은 한 번에 하나의 브로커 파드만 자발적 축출(voluntary eviction) — 노드 드레인, 클러스터 오토스케일러의 노드 교체 등 — 을 허용하도록 설정되어, 여러 브로커가 동시에 다운되어 쿼럼/가용성이 깨지는 상황을 방지합니다.

```bash
kubectl get pdb -n kafka -l strimzi.io/cluster=my-cluster
```

### `acks=all` 프로듀서와 롤링 재시작

프로듀서가 `acks=all`로 설정된 경우, 브로커 롤링 재시작 중에도 데이터 손실 없이 안전하게 동작합니다. 재시작 대상 브로커가 특정 파티션의 리더였다면, 재시작 직전에 컨트롤러가 다른 인-싱크 레플리카(ISR) 중 하나를 새 리더로 선출합니다. 프로듀서는 리더 변경을 감지하면 메타데이터를 갱신하고 새 리더로 요청을 재전송하며, 이 과정에서 일시적인 지연은 발생할 수 있지만 `min.insync.replicas`를 만족하는 한 커밋된 데이터는 손실되지 않습니다. 반대로 `acks=1` 이하로 설정된 프로듀서는 재시작 시점에 아직 팔로워로 복제되지 않은 메시지가 유실될 위험이 있습니다.

컨슈머 관점에서는 리밸런스(consumer group rebalance)가 발생해 일시적으로 처리량이 감소할 수 있지만, 컨슈머 오프셋 커밋이 정상적으로 이루어졌다면 재시작 이후 중단 지점부터 처리를 이어갈 수 있습니다.

---

[메인 페이지로 돌아가기](./README.md)

## 퀴즈

이 장에서 배운 내용을 테스트하려면 [주제 퀴즈](../../quizzes/data-on-eks/kafka/03-kafka-operations-quiz.md)를 풀어보세요.

다음 문서: Part 4 — 스키마 레지스트리(Schema Registry)를 이용한 메시지 스키마 관리와 호환성 전략을 다룹니다.
