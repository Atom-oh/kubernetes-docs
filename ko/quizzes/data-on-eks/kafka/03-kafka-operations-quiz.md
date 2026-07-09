# Kafka 운영 퀴즈

이 퀴즈는 EKS 위에서 Strimzi로 운영되는 Kafka 클러스터의 스토리지 설계, 브로커 스케일링, Cruise Control 리밸런싱, 롤링 업그레이드, 장애 대응에 대한 이해도를 테스트합니다.

## 객관식 문제

1. 다수의 컨슈머 그룹이 서로 다른 오프셋에서 동시에 읽어 랜덤 I/O 비중이 높고 p99 지연시간 SLA가 엄격한 워크로드에 더 적합한 EBS 볼륨 타입은 무엇인가요?
   - A) gp2
   - B) gp3
   - C) io2
   - D) st1

<details>

<summary>정답 보기</summary>

**정답: C) io2**

**설명:**
io2는 IOPS 기준으로 과금되며 최대 256,000 IOPS와 99.999%의 높은 내구성을 제공해, 다수의 소규모 랜덤 I/O가 빈번하고 지연시간에 민감한 워크로드에 적합합니다. 대부분의 이벤트 스트리밍 워크로드는 처리량 중심이므로 gp3로 시작하는 것이 비용 효율적이며, io2는 컨슈머 랙 급증이나 엄격한 p99 SLA처럼 랜덤 I/O가 병목이 되는 특수한 경우에만 전환을 고려합니다.
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
`storage.type: jbod`는 Just a Bunch Of Disks 구성으로, 브로커당 여러 개의 독립된 볼륨(`volumes` 목록)을 정의할 수 있게 합니다. 각 볼륨은 `id`로 구분되고 파티션은 라운드 로빈 방식으로 볼륨에 분산됩니다. `persistent-claim`은 개별 볼륨의 타입을 지정하는 값으로 JBOD 구성 안에서 각 볼륨에 사용됩니다.
</details>

3. 보존 기간 7일, 피크 처리량 100MB/s, 복제 팩터 3, 헤드룸 30%일 때, 클러스터 전체에 필요한 디스크 용량 공식은 무엇인가요?
   - A) 100MB/s × 7일(초) × 3
   - B) 100MB/s × 7일(초) × 3 × 1.3
   - C) 100MB/s × 7일(초) ÷ 3
   - D) 100MB/s × 3 × 1.3

<details>

<summary>정답 보기</summary>

**정답: B) 100MB/s × 7일(초) × 3 × 1.3**

**설명:**
디스크 사이징 공식은 `보존 기간 × 피크 처리량 × 복제 팩터 × (1 + 헤드룸 비율)`입니다. 보존 기간을 초 단위로 환산하고 피크 처리량을 곱해 원본 데이터량을 구한 뒤, 복제 팩터를 곱해 복제본까지 포함한 총량을 계산하고, 마지막으로 헤드룸(예: 30%는 1.3배)을 곱해 안전 여유분을 반영합니다.
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
Strimzi를 사용하면 브로커 파드가 시작될 때 볼륨 포맷팅을 Operator가 자동으로 처리합니다. 이는 순수 오픈소스 Kafka를 수동으로 운영할 때 `kafka-storage.sh format`을 직접 실행해야 하는 것과 대비되는 Strimzi의 편의 기능입니다.
</details>

5. `KafkaNodePool`의 `replicas` 값을 늘려 브로커를 스케일 아웃했을 때, 새로 추가된 브로커에 대해 자동으로 일어나는 일은 무엇인가요?
   - A) 기존 파티션이 즉시 새 브로커로 재분배된다
   - B) 새 브로커가 클러스터에 합류하지만, 기존 토픽 파티션은 자동으로 재분배되지 않는다
   - C) 새 브로커가 자동으로 모든 파티션의 리더가 된다
   - D) 새 브로커는 컨트롤러 역할만 수행한다

<details>

<summary>정답 보기</summary>

**정답: B) 새 브로커가 클러스터에 합류하지만, 기존 토픽 파티션은 자동으로 재분배되지 않는다**

**설명:**
`replicas`를 늘리면 Strimzi가 새 브로커 파드를 생성하고 클러스터에 합류시키지만, 기존 토픽의 파티션을 새 브로커로 옮기는 작업은 자동으로 이루어지지 않습니다. 새 브로커의 용량을 실제로 활용하려면 `kafka-reassign-partitions.sh`를 사용한 수동 재배치나 Cruise Control의 `add-brokers` 모드 리밸런싱이 필요합니다.
</details>

6. 브로커를 스케일 다운하기 전에 반드시 해야 하는 작업은 무엇인가요?
   - A) 아무 작업도 필요 없다 — Strimzi가 자동으로 드레인한다
   - B) 제거할 브로커의 파티션을 남아 있는 브로커로 먼저 재배치해야 한다
   - C) 클러스터를 재시작해야 한다
   - D) 모든 토픽을 삭제해야 한다

<details>

<summary>정답 보기</summary>

**정답: B) 제거할 브로커의 파티션을 남아 있는 브로커로 먼저 재배치해야 한다**

**설명:**
Strimzi는 브로커 스케일 다운 시 파티션을 자동으로 드레인하지 않습니다. `replicas`를 줄이기 전에 제거 대상 브로커의 모든 레플리카를 남아 있는 브로커로 재배치해야 하며, 그렇지 않으면 언더 리플리케이트 파티션이나 데이터 손실이 발생할 수 있습니다.
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
Cruise Control은 디스크 사용량, CPU, 네트워크 처리량 등 브로커별 부하 지표를 지속적으로 수집하고, 설정된 목표(goal)에 따라 파티션 재배치 계획을 자동으로 생성하고 실행합니다. 이를 통해 수동으로 `kafka-reassign-partitions.sh`를 실행하는 번거로움을 줄일 수 있습니다.
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
`add-brokers` 모드는 새로 추가된 브로커로 파티션을 이동시켜 부하를 채우는 데 특화되어 있어, 관련 없는 파티션까지 재배치하는 `full` 모드보다 빠르고 영향 범위가 작습니다. 반대로 `remove-brokers`는 제거할 브로커의 파티션을 나머지 브로커로 옮기는 데 특화되어 있어 스케일 다운 전 드레인 절차로 활용할 수 있습니다.
</details>

9. KRaft 모드 클러스터의 Kafka 버전을 3.8에서 3.9로 업그레이드할 때, 올바른 절차는 무엇인가요?
   - A) `version`과 `metadataVersion`을 동시에 3.9로 변경한다
   - B) 먼저 `version`만 3.9로 변경해 브로커/컨트롤러 소프트웨어를 롤링 교체하고, 모든 노드 교체가 끝난 뒤에 `metadataVersion`을 3.9-IV0으로 올린다
   - C) 먼저 `metadataVersion`을 올린 뒤 `version`을 변경한다
   - D) 클러스터를 완전히 중지한 뒤 모든 값을 한 번에 변경한다

<details>

<summary>정답 보기</summary>

**정답: B) 먼저 `version`만 3.9로 변경해 브로커/컨트롤러 소프트웨어를 롤링 교체하고, 모든 노드 교체가 끝난 뒤에 `metadataVersion`을 3.9-IV0으로 올린다**

**설명:**
KRaft 모드에서는 ZooKeeper 시절의 `inter.broker.protocol.version`/`log.message.format.version`이 존재하지 않고, 대신 `spec.kafka.version`(소프트웨어 버전)과 `spec.kafka.metadataVersion`(컨트롤러 쿼럼이 메타데이터를 기록하는 포맷 버전)을 2단계로 나눠 올려야 합니다. 1단계에서는 소프트웨어 버전만 올리고 `metadataVersion`은 이전 포맷으로 유지해, 업그레이드 도중 신구 버전 노드가 혼재해도 동일한 메타데이터 포맷으로 통신하게 합니다. 2단계는 모든 노드가 신버전으로 교체된 것을 확인한 뒤에만 `metadataVersion`을 올립니다. 순서를 바꾸면 구버전 노드가 새 메타데이터 포맷을 이해하지 못해 컨트롤러 쿼럼 통신 오류가 발생할 수 있습니다.
</details>

10. Strimzi가 `KafkaNodePool`마다 자동으로 생성하는, 자발적 축출을 제한하는 Kubernetes 리소스는 무엇인가요?
    - A) ResourceQuota
    - B) NetworkPolicy
    - C) PodDisruptionBudget
    - D) LimitRange

<details>

<summary>정답 보기</summary>

**정답: C) PodDisruptionBudget**

**설명:**
Strimzi는 `KafkaNodePool`마다 `PodDisruptionBudget`(PDB)을 자동으로 생성합니다. 기본값은 한 번에 하나의 브로커 파드만 자발적 축출(노드 드레인, 오토스케일러의 노드 교체 등)을 허용하도록 설정되어, 여러 브로커가 동시에 다운되어 가용성이 깨지는 상황을 방지합니다.
</details>

## 단답형 문제

11. 브로커가 재시작될 때 특정 파티션의 가용 레플리카 수가 최소치 밑으로 떨어지지 않도록 Strimzi가 롤링 재시작 시 준수하는 Kafka 설정 값은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: `min.insync.replicas`**

**설명:**
Strimzi Operator는 CR 스펙 변경으로 인한 롤링 재시작 시, 각 파티션의 `min.insync.replicas` 조건을 만족하는 범위 내에서만 브로커를 한 번에 하나씩 재시작합니다. 이를 통해 재시작 도중 특정 파티션의 사용 가능한 인-싱크 레플리카 수가 요구치 밑으로 떨어져 쓰기가 실패하거나 가용성이 손상되는 상황을 방지합니다.
</details>

12. Kafka 버전 업그레이드를 진행하기 전에, Kafka 클러스터 자체보다 먼저 업그레이드해야 하는 컴포넌트는 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: Strimzi Operator**

**설명:**
각 Strimzi 버전은 지원하는 Kafka 버전 범위가 정해져 있어, Operator가 인식하지 못하는 Kafka 버전으로 CR을 변경하면 검증에 실패합니다. 따라서 Kafka 소프트웨어 버전을 올리기 전에 Strimzi Operator 자체를 먼저 최신 버전으로 업그레이드해야 합니다.
</details>

13. 파티션 재배치 계획을 실제로 실행하기 전, 재배치 대상 브로커 목록을 지정해 계획을 생성할 때 사용하는 `kafka-reassign-partitions.sh`의 옵션은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: `--generate`**

**설명:**
`--generate` 옵션은 `--topics-to-move-json-file`과 `--broker-list`를 기반으로 재배치 계획(JSON)을 생성하지만 실제로 실행하지는 않습니다. 생성된 계획을 검토한 뒤 `--execute`로 적용하고, `--verify`로 진행 상태와 완료 여부를 확인합니다.
</details>

14. `acks=all`로 설정된 프로듀서가 브로커 롤링 재시작 중에도 데이터 손실 없이 동작할 수 있는 이유를 한 문장으로 설명하세요.

<details>

<summary>정답 보기</summary>

**정답: 재시작 대상 브로커가 파티션 리더였다면 재시작 전에 다른 ISR(인-싱크 레플리카) 중 하나가 새 리더로 선출되고, `min.insync.replicas`를 만족하는 한 커밋된 데이터는 보존되기 때문이다.**

**설명:**
`acks=all` 프로듀서는 `min.insync.replicas` 조건을 만족하는 레플리카들이 메시지를 기록할 때까지 커밋을 기다립니다. 브로커가 재시작되기 전 리더가 교체되면 프로듀서는 메타데이터를 갱신하고 새 리더로 요청을 재전송하므로, 일시적인 지연은 있어도 이미 커밋된 데이터는 손실되지 않습니다. `acks=1` 이하로 설정된 프로듀서는 이런 보장이 없어 유실 위험이 있습니다.
</details>

## 실습 문제

15. 3개 볼륨(각 300Gi, gp3)을 사용하는 JBOD 스토리지를 가진 `broker`라는 이름의 `KafkaNodePool` YAML을 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
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
        size: 300Gi
        class: gp3
        deleteClaim: false
      - id: 1
        type: persistent-claim
        size: 300Gi
        class: gp3
        deleteClaim: false
      - id: 2
        type: persistent-claim
        size: 300Gi
        class: gp3
        deleteClaim: false
```

**설명:**
`storage.type: jbod`로 지정한 뒤 `volumes` 목록에 3개의 `persistent-claim` 볼륨을 각각 고유한 `id`(0, 1, 2)로 정의합니다. `deleteClaim: false`를 설정하면 브로커가 재생성되거나 스케일 다운되어도 PVC가 삭제되지 않아 데이터가 보호됩니다.
</details>

16. `my-cluster`라는 이름의 클러스터에 대해 `full` 모드로 `KafkaRebalance` 리소스를 생성하고, 생성된 리밸런싱 계획을 승인하는 명령어를 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
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
# 계획 생성 상태 확인 (PendingProposal → ProposalReady)
kubectl get kafkarebalance my-rebalance -n kafka -o yaml

# 계획 승인 → 실행
kubectl annotate kafkarebalance my-rebalance -n kafka \
  strimzi.io/rebalance=approve

# 진행 상태 확인
kubectl get kafkarebalance my-rebalance -n kafka -w
```

**설명:**
`KafkaRebalance` CR을 생성하면 Cruise Control이 자동으로 리밸런싱 계획을 생성하고 `ProposalReady` 상태로 대기합니다. `strimzi.io/rebalance=approve` 어노테이션을 추가해야 실제로 파티션 이동이 실행됩니다. `mode: full`은 클러스터의 모든 브로커를 대상으로 목표 기반 전체 리밸런싱 계획을 생성합니다.
</details>

17. 브로커 3대(ID 0,1,2)를 6대(ID 0~5)로 스케일 아웃한 뒤, `orders` 토픽의 파티션을 새 브로커까지 포함한 전체 브로커로 재배치하는 3단계 명령어(계획 생성 → 실행 → 검증)를 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```bash
# 1) 재배치 대상 토픽 정의
cat <<EOF > topics-to-move.json
{
  "topics": [{"topic": "orders"}],
  "version": 1
}
EOF

# 2) 계획 생성
kubectl exec -it my-cluster-broker-0 -n kafka -- \
  bin/kafka-reassign-partitions.sh \
  --bootstrap-server localhost:9092 \
  --topics-to-move-json-file topics-to-move.json \
  --broker-list "0,1,2,3,4,5" \
  --generate

# 3) 계획 실행 (생성된 reassignment.json 사용)
kubectl exec -it my-cluster-broker-0 -n kafka -- \
  bin/kafka-reassign-partitions.sh \
  --bootstrap-server localhost:9092 \
  --reassignment-json-file reassignment.json \
  --execute

# 4) 완료 여부 검증
kubectl exec -it my-cluster-broker-0 -n kafka -- \
  bin/kafka-reassign-partitions.sh \
  --bootstrap-server localhost:9092 \
  --reassignment-json-file reassignment.json \
  --verify
```

**설명:**
`--generate`는 지정된 `--broker-list`(여기서는 0~5, 새 브로커 포함) 전체를 대상으로 파티션 이동 계획을 만듭니다. `--execute`로 실제 재배치를 시작하고, `--verify`로 재배치가 완료되었는지, 언더 리플리케이트 파티션이 없는지 확인합니다. 이 과정을 거쳐야 새로 추가된 브로커가 실제로 파티션 리더/팔로워 역할을 갖게 됩니다.
</details>

---

[학습 자료로 돌아가기](../../../data-on-eks/kafka/03-kafka-operations.md) | [다음 퀴즈: 스키마 레지스트리](./04-schema-registry-quiz.md)
