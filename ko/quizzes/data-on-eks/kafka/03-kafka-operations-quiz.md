# Kafka 운영 퀴즈

> **검토 기준**: 2026-09-12, Strimzi 1.2.0 / Kafka 4.3.1.

이 퀴즈는 EKS 위에서 Strimzi로 운영되는 Kafka 클러스터의 스토리지 설계, 브로커 스케일링, Cruise Control 리밸런싱, 롤링 업그레이드, 장애 대응에 대한 이해도를 테스트합니다.

## 객관식 문제

1. AWS가 낮은 지연과 높은 IOPS·내구성을 목표로 설계한 다음 SSD 선택지는 무엇인가요?
   - A) gp2
   - B) gp3
   - C) io2
   - D) st1

<details>

<summary>정답 보기</summary>

**정답: C) io2**

**설명:**
io2 Block Express는 낮은 지연과 높은 IOPS·내구성을 목표로 설계되었습니다. 최대 256,000 IOPS는 Nitro 등 조건이 필요하고, 99.999% 설계 내구성과 AFR 0.001%는 구분합니다. 용량과 IOPS가 과금에 포함되며 실제 선택은 측정·SLA·가격을 함께 평가합니다.
</details>

2. `KafkaNodePool`에서 브로커가 여러 개의 독립된 볼륨을 사용하도록 구성하는 스토리지 타입은 무엇인가요?
   - A) `type: persistent-claim`
   - B) `type: jbod`
   - C) `type: ephemeral`
   - D) `type: multi-volume`

<details>

<summary>정답 보기</summary>

**정답: B) `type: jbod`**

**설명:**
JBOD는 독립 volume ID를 제공합니다. Kafka 4.3.1은 기본적으로 새 로그를 파티션 로그 수가 적은 디렉터리에 배치하며, round-robin이나 바이트 사용량 균등 분배를 보장하지 않습니다. 기존 데이터 이동은 별도 작업입니다.
</details>

3. 지속되는 로그율 100MB/s, 7일 보존, RF=3에서 전체 용량의 30%를 빈 공간으로 두려면 어떤 공식이 필요한가요?
   - A) 100MB/s × 7일(초) × 3
   - B) 100MB/s × 7일(초) × 3 ÷ 0.70
   - C) 100MB/s × 7일(초) ÷ 3
   - D) 100MB/s × 3 × 1.3

<details>

<summary>정답 보기</summary>

**정답: B) 100MB/s × 7일(초) × 3 ÷ 0.70**

**설명:**
데이터에 30%를 추가한 용량은 실제로 약 23.08%만 비어 있습니다. 전체 용량의 30%를 비우려면 복제된 데이터량을 0.70으로 나눕니다. 지속되는 압축 후 로그 바이트율과 실제 retention을 사용하고 별도 운영 overhead를 고려합니다.
</details>

4. Strimzi가 관리하는 Kafka 클러스터에서 볼륨 포맷을 위해 운영자가 직접 실행해야 하는 스크립트는 무엇인가요?
   - A) `kafka-storage.sh format`을 매 브로커마다 수동 실행해야 한다
   - B) `kafka-configs.sh`로 포맷 설정을 적용해야 한다
   - C) Strimzi Operator가 브로커 파드 시작 시 자동으로 처리하므로 별도 실행이 필요 없다
   - D) `kafka-reassign-partitions.sh --format` 옵션을 사용해야 한다

<details>

<summary>정답 보기</summary>

**정답: C) Strimzi Operator가 브로커 파드 시작 시 자동으로 처리하므로 별도 실행이 필요 없다**

**설명:**
Strimzi와 시작 스크립트가 필요한 새 storage metadata 초기화를 관리합니다. 기존 데이터가 매번 지워진다는 뜻이 아닙니다. Operator가 관리하는 볼륨에 운영자가 임의의 수동 format을 실행하지 않습니다.
</details>

5. 관련 autoRebalance 모드가 없는 경우 broker pool replicas 증가만으로 일어나는 동작은?
   - A) 기존 파티션이 즉시 새 브로커로 재분배된다
   - B) 새 브로커가 클러스터에 합류하지만, 기존 토픽 파티션은 자동으로 재분배되지 않는다
   - C) 새 브로커가 자동으로 모든 파티션의 리더가 된다
   - D) 새 브로커는 컨트롤러 역할만 수행한다

<details>

<summary>정답 보기</summary>

**정답: B) 새 브로커가 클러스터에 합류하지만, 기존 토픽 파티션은 자동으로 재분배되지 않는다**

**설명:**
해당 autoRebalance 모드가 없을 때의 설명입니다. Strimzi 1.2에서 add-brokers autoRebalance를 구성하면 기존 pool의 replicas 증가에 따라 자동 재배치를 조정합니다. pool 생성/삭제는 같은 자동 트리거가 아닙니다.
</details>

6. broker를 제거하기 전에 만족해야 할 데이터 상태는?
   - A) 아무 작업도 필요 없다 — Strimzi가 자동으로 드레인한다
   - B) 제거할 브로커의 파티션을 남아 있는 브로커로 먼저 재배치해야 한다
   - C) 클러스터를 재시작해야 한다
   - D) 모든 토픽을 삭제해야 한다

<details>

<summary>정답 보기</summary>

**정답: B) 제거할 브로커의 파티션을 남아 있는 브로커로 먼저 재배치해야 한다**

**설명:**
broker 제거 전에 모든 replica가 안전하게 이동되어야 합니다. 수동 절차에서는 internal topic도 포함해 확인하며, 설정된 remove-brokers autoRebalance는 이동을 자동 조정할 수 있습니다. 기본 nonempty-broker 검사와 실제 제거 ID 확인을 유지합니다.
</details>

7. Cruise Control의 주요 역할은 무엇인가요?
   - A) 토픽 생성과 삭제를 자동화한다
   - B) 브로커 부하 지표를 수집해 목표 기반 파티션 재배치 계획을 자동으로 생성/실행한다
   - C) 컨슈머 그룹의 오프셋 커밋을 관리한다
   - D) TLS 인증서를 자동으로 갱신한다

<details>

<summary>정답 보기</summary>

**정답: B) 브로커 부하 지표를 수집해 목표 기반 파티션 재배치 계획을 자동으로 생성/실행한다**

**설명:**
Cruise Control은 부하와 목표로 제안을 계산하고 승인/자동화 정책에 따라 실행합니다. 제안 생성과 데이터 이동은 구분하며, 메트릭 부족이나 hard goal 위반 시 임의로 검사를 건너뛰지 않습니다.
</details>

8. `KafkaRebalance` 리소스의 `mode` 필드에서, 새로 추가된 브로커로만 파티션을 이동시켜 부하를 채우는 데 특화된 모드는 무엇인가요?
   - A) `full`
   - B) `add-brokers`
   - C) `remove-brokers`
   - D) `partial`

<details>

<summary>정답 보기</summary>

**정답: B) `add-brokers`**

**설명:**
add-brokers는 지정된 새 broker를 대상으로 하며 실제 broker ID 목록이 필요합니다. 목표·데이터량·rack 조건에 따라 시간과 영향이 달라지므로 항상 full보다 빠르다고 보장하지 않습니다. remove-brokers는 제거 전 이동에 사용합니다.
</details>

9. Kafka 4.2.1에서 4.3.1로 올리며 이전 metadata format을 유지해 검증 기간을 두는 패턴은?
   - A) version과 metadataVersion을 모두 새 값으로 즉시 변경
   - B) version을 4.3.1로 올리고 metadataVersion은 4.2-IV1로 유지한 뒤 검증 후 4.3-IV0으로 변경
   - C) binary 호환성 확인 없이 metadataVersion부터 올림
   - D) 모든 데이터를 삭제하고 재시작

<details>

<summary>정답 보기</summary>

**정답: B) version을 4.3.1로 올리고 metadataVersion은 4.2-IV1로 유지한 뒤 검증 후 4.3-IV0으로 변경**

**설명:**
이 문제는 이전 metadataVersion을 명시적으로 보존해 검증 시간을 두는 운영 패턴입니다. metadataVersion을 생략하면 Strimzi가 binary 업그레이드 후 자동 갱신할 수도 있습니다. Operator는 현재/목표 Kafka를 모두 지원해야 하며 format 갱신 후 downgrade가 불가능할 수 있습니다.
</details>

10. Strimzi Kafka 클러스터의 자발적 eviction을 제한하는 Kubernetes 리소스는?
    - A) ResourceQuota
    - B) NetworkPolicy
    - C) PodDisruptionBudget
    - D) LimitRange

<details>

<summary>정답 보기</summary>

**정답: C) PodDisruptionBudget**

**설명:**
Strimzi 1.2의 기본 Kafka PDB는 Kafka 클러스터 하나에 하나이며 모든 node pool의 Kafka Pod를 포함합니다. voluntary eviction에만 적용되며 node/AZ 장애나 강제 삭제를 막지는 않습니다.
</details>

## 단답형 문제

11. Kafka rolling availability 판단에서 참조하는 최소 ISR 설정 이름은?

<details>

<summary>정답 보기</summary>

**정답: `min.insync.replicas`**

**설명:**
min.insync.replicas는 가용성 판단의 중요한 입력이지만 모든 rolling 상황의 무중단 보장은 아닙니다. 실제 ISR, controller quorum, storage/network와 client timeout·재시도를 함께 확인합니다.
</details>

12. Kafka 업그레이드 전에 현재와 목표 Kafka 버전의 지원 범위를 확인할 컴포넌트는?

<details>

<summary>정답 보기</summary>

**정답: Strimzi Operator**

**설명:**
현재와 목표 Kafka를 모두 지원하는 Strimzi 버전을 확인합니다. 이미 지원하면 Operator 업그레이드가 필수는 아닙니다. 최신 Operator가 현재 Kafka를 지원하지 않으면 중간 버전과 API/CRD 전환 경로를 계획합니다.
</details>

13. 파티션 재배치 계획을 실제로 실행하기 전, 재배치 대상 브로커 목록을 지정해 계획을 생성할 때 사용하는 `kafka-reassign-partitions.sh`의 옵션은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: `--generate`**

**설명:**
--generate는 현재 배치와 제안 배치를 출력하지만 이동은 실행하지 않습니다. Proposed JSON만 별도 파일로 추출하고 RF·broker ID·rack·용량을 검토합니다. --verify는 preserve-throttles 없이 완료되면 설정을 정리할 수 있습니다.
</details>

14. acks=all의 내구성 조건과 rolling 중 요청 성공 보장을 구분해 설명하세요.

<details>

<summary>정답 보기</summary>

**정답: 동기화된 복제본과 유효한 quorum/leader 등 조건 아래 내구성이 강화되지만, 요청 timeout·재시도까지 없어지는 것은 아니다.**

**설명:**
acks=all은 현재 ISR 전체의 승인을 기다리며 최소 ISR 조건도 만족해야 합니다. 동기화된 복제본이 남아 있고 유효한 leader/quorum·storage 조건이 유지되어야 하며, 요청 timeout·재시도·중복 처리 가능성은 별도로 관리합니다.
</details>

## 실습 문제

15. 새 환경을 위한 broker pool 정의 예제로 300Gi gp3 volume 세 개를 구성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaNodePool
metadata:
  name: broker
  namespace: kafka
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
      size: 300Gi
      class: gp3-kafka
      deleteClaim: false
      kraftMetadata: shared
    - id: 1
      type: persistent-claim
      size: 300Gi
      class: gp3-kafka
      deleteClaim: false
    - id: 2
      type: persistent-claim
      size: 300Gi
      class: gp3-kafka
      deleteClaim: false
  resources:
    requests:
      cpu: '2'
      memory: 4Gi
    limits:
      memory: 4Gi
  template:
    pod:
      metadata:
        labels:
          docs.example.com/kafka-role: broker
      topologySpreadConstraints:
      - maxSkew: 1
        minDomains: 3
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        nodeAffinityPolicy: Honor
        nodeTaintsPolicy: Honor
        labelSelector:
          matchLabels:
            strimzi.io/cluster: my-cluster
            docs.example.com/kafka-role: broker
```

**설명:**
이것은 새 환경의 정의 예제이며 이미 500Gi로 확장한 volume을 300Gi로 줄이는 명령이 아닙니다. class는 Part 2의 gp3-kafka를 사용하고 metadata는 한 volume에만 지정합니다. Retain/deleteClaim은 백업을 대신하지 않습니다.
</details>

16. `my-cluster`라는 이름의 클러스터에 대해 `full` 모드로 `KafkaRebalance` 리소스를 생성하고, 생성된 리밸런싱 계획을 승인하는 명령어를 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaRebalance
metadata:
  name: reviewed-full-rebalance
  namespace: kafka
  labels:
    strimzi.io/cluster: my-cluster
  annotations:
    strimzi.io/rebalance-auto-approval: "false"
spec:
  mode: full
```

```bash
kubectl create -f rebalance-full.yaml
kubectl -n kafka wait kafkarebalance/reviewed-full-rebalance \
  --for=condition=ProposalReady --timeout=30m
kubectl -n kafka get kafkarebalance reviewed-full-rebalance -o yaml
# Review the proposal before executing:
kubectl -n kafka annotate kafkarebalance reviewed-full-rebalance \
  strimzi.io/rebalance=approve --overwrite
kubectl -n kafka get kafkarebalance reviewed-full-rebalance -w
```

**설명:**
Cruise Control이 활성화되어 있고 유효한 메트릭/목표가 있어야 합니다. 요청의 auto-approval은 false이며 ProposalReady 결과를 검토한 뒤 approve합니다. 자동 scale 기능이 만든 요청과 수동 요청을 구분합니다.
</details>

17. broker 확장 후 실제 ID와 TLS 관리자 설정으로 orders의 계획 생성·추출·실행·상태 확인 명령을 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```bash
set -euo pipefail
: "${DOCS_BOOTSTRAP:?Set reachable TLS bootstrap}"
: "${DOCS_ADMIN_CONFIG:?Set local admin properties file}"
: "${DOCS_BROKER_IDS:?Set verified comma-separated broker IDs}"
: "${DOCS_MOVE_BYTES_PER_SEC:?Choose reviewed throttle bytes/second}"
cat > topics-to-move.json <<'JSON'
{"version":1,"topics":[{"topic":"orders"}]}
JSON
kafka-reassign-partitions.sh \
  --bootstrap-server "$DOCS_BOOTSTRAP" --command-config "$DOCS_ADMIN_CONFIG" \
  --topics-to-move-json-file topics-to-move.json --broker-list "$DOCS_BROKER_IDS" \
  --generate > generate-output.txt
python3 extract_reassignment.py generate-output.txt reassignment.json
python3 -m json.tool reassignment.json
# Review the exact proposal before movement:
kafka-reassign-partitions.sh \
  --bootstrap-server "$DOCS_BOOTSTRAP" --command-config "$DOCS_ADMIN_CONFIG" \
  --reassignment-json-file reassignment.json --execute --throttle "$DOCS_MOVE_BYTES_PER_SEC"
kafka-reassign-partitions.sh \
  --bootstrap-server "$DOCS_BOOTSTRAP" --command-config "$DOCS_ADMIN_CONFIG" \
  --reassignment-json-file reassignment.json --verify --preserve-throttles
```

**설명:**
파일은 CLI를 실행하는 같은 환경에 둡니다. 실제 broker ID와 TLS 관리자 설정을 사용하고 Current/Proposed 중 Proposed만 추출합니다. --verify --preserve-throttles로 이동을 확인한 뒤 URP/min ISR/offline 상태는 별도로 확인합니다. 한 토픽 이동은 전체 broker drain 증명이 아닙니다.
</details>

---

[학습 자료로 돌아가기](../../../data-on-eks/kafka/03-kafka-operations.md) | [다음 퀴즈: 스키마 레지스트리](./04-schema-registry-quiz.md)
