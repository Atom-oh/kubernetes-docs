# Part 3: Kafka 운영

> **검토 기준**: 2026-09-12, Strimzi 1.2.0 / Kafka 4.3.1.
> **검증 범위**: 현재 릴리스 문서·소스, 로컬 CRD/merge patch, 제안 생성·JSON 추출, Decimal 계산과 CLI 옵션. 실제 Kafka 재배치·업그레이드·AWS 볼륨 변경은 수행하지 않았습니다.

이 장은 [Part 2](./02-strimzi-operator.md)의 인증된 Kafka와 broker 전용 node pool을 기준으로 합니다. 운영 명령은 실제 파티션 이동과 리소스 변경을 일으킬 수 있으므로, 현재 설정·데이터 배치와 제안 결과를 확인한 뒤 실행합니다. controller 역할 풀에 broker 증감 절차를 그대로 적용하지 않습니다.

## 1. 스토리지 성능과 내구성

컨슈머 랙이 크다고 모든 읽기가 랜덤 I/O가 되는 것은 아닙니다. 과거 로그를 순차적으로 읽더라도 여러 소비자의 범위가 섞이거나 page cache를 벗어나면 물리 I/O와 tail latency가 증가할 수 있습니다. 실제 IOPS·처리량·큐 지연·cache hit·instance EBS 한계를 측정합니다.

| 항목 | gp3 | io2 Block Express |
| --- | --- | --- |
| 기본 성능 | 3,000 IOPS / 125 MiB/s 포함 | 프로비저닝한 IOPS에 따른 성능 |
| 최대 볼륨 IOPS | 80,000 | Nitro에서 256,000 |
| 최대 볼륨 처리량 | 2,000 MiB/s | 4,000 MiB/s |
| 최대 용량 | 64 TiB | 64 TiB |
| 공개된 설계 내구성 | 99.8–99.9% | 99.999% |
| 공개된 AFR 상한 | 0.2% | 0.001% |

이는 볼륨의 설계 수치이며 Kafka 서비스 SLA나 임의 장애에서 데이터 보존을 보장하는 값이 아닙니다. 최대 성능에는 볼륨 크기·IOPS 비율과 인스턴스 조건이 있습니다. Outposts gp3 및 non-Nitro io2의 한계는 다르므로 일반 표를 그대로 적용하지 않습니다.

비용에는 스토리지 용량도 포함됩니다. gp3는 기본 성능을 넘는 IOPS/처리량, io2는 프로비저닝한 IOPS도 함께 평가합니다. 지연·내구성 요구, 실제 측정과 현재 리전 가격으로 선택하며 “io2는 IOPS만 과금” 또는 “랙이 크면 반드시 io2”라고 단정하지 않습니다.

## 2. 보존량과 여유 공간

기준은 보존될 **압축 후 로그 바이트율**과 실제 retention입니다. 짧은 피크를 7일 내내 유지한다고 가정하면 과도한 추정이 될 수 있습니다. 토픽별 retention·복제 수가 다르면 각각 계산하고, compaction·인덱스·내부 토픽·재배치 임시 복사본을 추가로 고려합니다.

가상으로 50 **MB/s(10⁶ bytes/s)**가 7일 동안 지속되고 RF=3이라면 복제된 로그는 90.72 TB입니다.

| 해석 | 용량 | 실제 빈 공간 비율 |
| --- | --- | --- |
| 데이터 크기에 30% 용량 추가 | 117.936 TB | 약 23.08% |
| 전체 디스크의 30%를 비워 둠 | 129.6 TB, 약 117.87 TiB | 30% |

기존 약 118 TB 계산은 첫 번째 해석으로 맞습니다. 두 번째 목표에는 `data / (1 - 0.30)`을 사용합니다. 129.6 TB를 세 broker에 균등 분배한다고 가정한 평균은 43.2 TB이지만, 실제 partition skew를 따로 확인해야 합니다. 이 수치는 Part 2 실습 PVC 크기의 근거가 아닌 계산 예제입니다.

**`storage-sizing.py`**

```python
"""Illustrative storage calculation, not measured traffic or a volume recommendation."""
from decimal import Decimal
import json

retained_log_bytes_per_second = Decimal("50000000")  # 50 decimal MB/s, sustained
retention_seconds = Decimal(7 * 24 * 60 * 60)
replication_factor = Decimal(3)
broker_count = Decimal(3)
margin = Decimal("0.30")
replicated_bytes = retained_log_bytes_per_second * retention_seconds * replication_factor
additive_capacity = replicated_bytes * (1 + margin)
free_space_capacity = replicated_bytes / (1 - margin)

print(json.dumps({
    "replicated_log_TB": str(replicated_bytes / Decimal(10**12)),
    "capacity_with_30_percent_added_TB": str(additive_capacity / Decimal(10**12)),
    "free_percent_with_added_margin": str((1 - replicated_bytes / additive_capacity) * 100),
    "capacity_with_30_percent_free_TB": str(free_space_capacity / Decimal(10**12)),
    "capacity_with_30_percent_free_TiB": str(free_space_capacity / Decimal(2**40)),
    "average_per_broker_TB": str(free_space_capacity / broker_count / Decimal(10**12)),
    "assumptions": [
        "Sustained retained-log bytes after compression; not a short traffic peak.",
        "No separate allowance here for indexes, internal topics, compaction or temporary reassignment copies.",
        "Per-broker division assumes equal data placement; measure actual skew."
    ]
}, indent=2))
```

## 3. JBOD 확장과 변경

Kafka 4.3.1의 기본 새 로그 디렉터리 선택은 파티션 로그 수가 적은 디렉터리를 우선합니다. 단순 round-robin이나 바이트 사용량 균등 배치가 아닙니다. 새 디스크 추가만으로 기존 데이터가 자동으로 옮겨지지도 않습니다.

다음 merge patch는 Part 2의 volume 0(100Gi)을 500Gi로 늘리고 volume 1을 추가하는 예제입니다. **volumes 배열 전체를 교체**하므로 현재 풀에 다른 볼륨이 있으면 그대로 사용하지 말고 모두 보존하는 변경안을 작성합니다. 기존 topology/resource 설정은 유지합니다.

**`storage-expand.patch.yaml`**

```yaml
# For the Part 2 broker pool with one 100Gi volume (id 0).
# Merge patch replaces the entire volumes array; preserve every existing volume.
spec:
  storage:
    type: jbod
    volumes:
      - id: 0
        type: persistent-claim
        size: 500Gi
        class: gp3-kafka
        deleteClaim: false
        kraftMetadata: shared
      - id: 1
        type: persistent-claim
        size: 500Gi
        class: gp3-kafka
        deleteClaim: false
```

```bash
kubectl -n kafka get kafkanodepool broker -o yaml > broker-before.yaml
kubectl -n kafka patch kafkanodepool broker --type=merge \
  --patch-file storage-expand.patch.yaml
kubectl -n kafka get pvc -l strimzi.io/cluster=my-cluster
```

확장은 StorageClass/CSI와 실제 파일시스템 지원을 확인합니다. PVC shrink는 이 절차가 아니며, class나 volume ID를 바꾸는 것도 단순 증설이 아닙니다. `kraftMetadata: shared`를 두 볼륨에 지정하지 않습니다.

볼륨 제거 전에는 해당 디렉터리의 replica와 metadata 위치를 확인하고 데이터를 이동해야 합니다. Strimzi 1.2의 `remove-disks` rebalance 모드는 broker 내부 JBOD 이동을 지원하지만, 필드와 지원 조건에 맞는 별도 계획이 필요합니다. `deleteClaim: false`/Retain은 백업이나 복구 가능성의 증명이 아닙니다. Strimzi가 관리하는 데이터에 수동 `kafka-storage.sh format`을 실행하지 않습니다.

## 4. 브로커 증감: 수동과 자동 구분

아래 절차는 **broker 전용 pool** 대상입니다. Strimzi 1.2는 controller quorum을 정적으로 구성하므로 controller-role pool을 같은 방식으로 증감하지 않습니다. upstream Kafka의 동적 quorum 기능과 Operator의 지원 범위를 혼동하지 않습니다.

| 설정 | 기존 풀의 replicas 변경 |
| --- | --- |
| 해당 autoRebalance 모드 없음 | broker 추가와 기존 replica 이동은 별도 작업 |
| `add-brokers` autoRebalance | scale-out 후 새 broker로 자동 재배치 |
| `remove-brokers` autoRebalance | scale-in 때 제거 대상에서 replica 이동을 자동 조정 |

자동 기능은 **기존 pool의 replicas 변경**에 반응합니다. pool 생성/삭제는 같은 트리거가 아닙니다. Kafka 4.3 이상에서는 자동 scale-down 과정에서 새 replica 할당을 막기 위한 broker cordoning도 사용합니다.

### 수동 scale-out

```bash
kubectl -n kafka get kafka my-cluster -o jsonpath='{.spec.cruiseControl.autoRebalance}'
# Continue with the manual path only when the relevant automatic mode is not enabled.
kubectl -n kafka get kafkanodepool broker -o json > broker-before.json
kubectl -n kafka patch kafkanodepool broker --type=merge -p '{"spec":{"replicas":6}}'
kubectl -n kafka get pods -l strimzi.io/pool-name=broker
kubectl -n kafka get kafkanodepool broker -o json > broker-pool.json
```

Pod Running만 확인하지 말고 Operator의 현재 generation, broker 등록·ISR과 용량을 확인합니다. Node ID는 cluster 전체에서 할당되므로 0–5나 `my-cluster-broker-0`을 가정하지 않습니다.

### 수동 scale-down

제거할 실제 broker ID를 고정하고, **내부 토픽을 포함한 모든 replica**를 다른 broker로 옮깁니다. orders/payments 두 토픽만 이동했다고 broker가 비었다고 판단하지 않습니다. 이동 완료·남은 RF/ISR·rack 분포·용량을 확인한 뒤에만 replicas를 줄입니다.

특정 ID를 선택하려면 `strimzi.io/remove-node-ids`를 사용하되, 잘못된 범위는 기본 선택으로 fallback할 수 있으므로 현재 nodeIds와 일치하는지 확인합니다. Strimzi의 기본 nonempty-broker scale-down 검사는 유지합니다. 이 검사를 건너뛰어 데이터가 있는 broker를 강제로 제거하는 방법은 기본 운영 절차가 아닙니다.

## 5. Cruise Control 제안과 승인

이 예제는 수동 승인을 기본으로 합니다. 기존 Kafka 설정을 보존하면서 Cruise Control을 추가합니다. 임의의 goals 목록으로 기본 hard goals를 빠뜨리거나 `skipHardGoalCheck`를 기본값처럼 켜지 않습니다.

**`cruise-control.patch.yaml`**

```yaml
spec:
  cruiseControl: {}
```

```bash
kubectl -n kafka patch kafka my-cluster --type=merge \
  --patch-file cruise-control.patch.yaml
kubectl -n kafka get kafka my-cluster -o yaml
```

**`rebalance-full.yaml`**

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
# Review optimizationResult, movement volume, goals, capacity and expected impact first.
kubectl -n kafka annotate kafkarebalance reviewed-full-rebalance \
  strimzi.io/rebalance=approve --overwrite
kubectl -n kafka get kafkarebalance reviewed-full-rebalance -w
```

메트릭 샘플이 부족하거나 목표를 만족하지 못하면 ProposalReady가 되지 않을 수 있습니다. 승인 전 이동량·목표·rack·용량을 확인합니다. `auto-approval=false`로 만든 수동 요청과 자동 scale 기능이 생성한 요청은 구분합니다. 이미 같은 이름의 요청이 있으면 새 변경에 고유한 이름을 사용합니다.

| 모드 | 목적 |
| --- | --- |
| `full` | 전체 범위의 목표 기반 재배치 |
| `add-brokers` | 지정한 새 broker로 이동 |
| `remove-brokers` | 지정한 broker에서 이동 |
| `remove-disks` | 같은 broker의 JBOD 볼륨에서 이동 |

add/remove는 `brokers` 목록이 필요합니다. 좁은 범위가 항상 더 빨리 끝나거나 영향이 적다는 보장은 없습니다. 다음 도구는 현재 broker pool snapshot에서 ID를 확인해 **제안 CR JSON만** 만듭니다. capacity·ISR·rack 안전성을 판정하거나 API를 호출하지 않습니다.

**`rebalance_request.py`**

```python
"""Generate a manual KafkaRebalance proposal from a broker pool snapshot; no API calls."""
import argparse
import json
from pathlib import Path


def request(pool, mode, broker_ids):
    if pool.get("kind") != "KafkaNodePool" or pool.get("spec", {}).get("roles") != ["broker"]:
        raise ValueError("Use a broker-only KafkaNodePool snapshot")
    metadata = pool.get("metadata", {})
    namespace = metadata.get("namespace")
    cluster = metadata.get("labels", {}).get("strimzi.io/cluster")
    if not namespace or not cluster:
        raise ValueError("The pool must include namespace and cluster label")
    known = pool.get("status", {}).get("nodeIds", [])
    if not known or any(type(value) is not int or value < 0 for value in known):
        raise ValueError("Read a fresh pool snapshot with valid status.nodeIds")
    if mode not in ("add-brokers", "remove-brokers"):
        raise ValueError("Select add-brokers or remove-brokers")
    if not broker_ids or len(broker_ids) != len(set(broker_ids)):
        raise ValueError("Supply distinct broker IDs")
    if any(type(value) is not int or value not in known for value in broker_ids):
        raise ValueError("Every selected broker must belong to the supplied pool")
    return {
        "apiVersion": "kafka.strimzi.io/v1", "kind": "KafkaRebalance",
        "metadata": {
            "name": f"reviewed-{mode}", "namespace": namespace,
            "labels": {"strimzi.io/cluster": cluster},
            "annotations": {"strimzi.io/rebalance-auto-approval": "false"},
        },
        "spec": {"mode": mode, "brokers": sorted(broker_ids)},
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pool", type=Path, required=True)
    parser.add_argument("--mode", choices=["add-brokers", "remove-brokers"], required=True)
    parser.add_argument("--brokers", nargs="+", type=int, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(request(json.loads(args.pool.read_text()), args.mode, args.brokers), indent=2))
    except (ValueError, TypeError, KeyError) as error:
        parser.exit(1, f"Cannot create proposal: {error}\n")
```

```bash
kubectl -n kafka get kafkanodepool broker -o json > broker-pool.json
# Set actual broker IDs from the snapshot, not controller IDs.
DOCS_BROKER_ID="REPLACE_WITH_VERIFIED_BROKER_ID"
python3 rebalance_request.py --pool broker-pool.json \
  --mode remove-brokers --brokers "$DOCS_BROKER_ID" > remove-proposal.json
python3 -m json.tool remove-proposal.json
# Review the generated proposal before creating/approving it.
```

### 선택 사항: 기존 pool의 자동 재배치

다음 설정은 replicas 변경 시 **별도 수동 승인 없이 데이터 이동을 유발할 수 있습니다**. 운영 정책과 목표를 정한 뒤 사용합니다. `status.autoRebalance.state=Idle`은 실패 후에도 나타날 수 있으므로 생성된 KafkaRebalance의 결과와 Kafka 상태를 함께 확인합니다.

**`auto-rebalance.patch.yaml`**

```yaml
# Optional: enables automatic partition movement on existing pool replica changes.
spec:
  cruiseControl:
    autoRebalance:
      - mode: add-brokers
      - mode: remove-brokers
```

```bash
kubectl -n kafka patch kafka my-cluster --type=merge \
  --patch-file auto-rebalance.patch.yaml
kubectl -n kafka get kafka my-cluster -o yaml
kubectl -n kafka get kafkarebalances -l strimzi.io/cluster=my-cluster
```

## 6. 수동 Kafka CLI 재배치 대안

CLI를 실행하는 같은 환경에 모든 JSON 파일과 관리자 설정을 둡니다. 로컬에 만든 파일을 복사 없이 `kubectl exec` 내부 경로에서 읽는 방식은 동작하지 않습니다. Kafka의 모든 advertised endpoint에 접근 가능하고 해당 관리 작업 권한을 가진 TLS/SASL 설정이 필요합니다. Part 2의 orders 애플리케이션 사용자는 관리 계정이 아닙니다.

다음 예제의 대상 토픽은 orders 하나입니다. 전체 broker 제거용 inventory로 사용하지 않습니다.

```json
{
  "version": 1,
  "topics": [{"topic": "orders"}]
}
```

```bash
set -euo pipefail
: "${DOCS_BOOTSTRAP:?Set a reachable TLS bootstrap endpoint}"
: "${DOCS_ADMIN_CONFIG:?Set the local admin client.properties path}"
: "${DOCS_BROKER_IDS:?Set verified comma-separated target broker IDs}"
# Save the JSON above as topics-to-move.json in this environment.
kafka-reassign-partitions.sh \
  --bootstrap-server "$DOCS_BOOTSTRAP" --command-config "$DOCS_ADMIN_CONFIG" \
  --topics-to-move-json-file topics-to-move.json \
  --broker-list "$DOCS_BROKER_IDS" --generate > generate-output.txt
```

`--generate` 출력에는 Current와 Proposed JSON이 함께 들어갑니다. 원본 출력은 이전 배치의 기록으로 보관하고, 아래 도구로 Proposed만 별도의 새 파일에 저장합니다. 기존 출력 파일을 덮어쓰지 않으므로 새 계획에는 새 파일명을 사용합니다.

**`extract_reassignment.py`**

```python
"""Extract Kafka 4.3 --generate's proposal; never execute reassignment."""
import argparse
import json
from pathlib import Path

MARKER = "Proposed partition reassignment configuration"


def extract(text):
    if text.count(MARKER) != 1:
        raise ValueError("Expected exactly one proposal marker; inspect the command output")
    proposal, _ = json.JSONDecoder().raw_decode(text.split(MARKER, 1)[1].lstrip())
    if (not isinstance(proposal, dict) or type(proposal.get("version")) is not int
            or proposal["version"] != 1 or not isinstance(proposal.get("partitions"), list)
            or not proposal["partitions"]):
        raise ValueError("Expected a nonempty version-1 reassignment proposal")
    seen = set()
    for entry in proposal["partitions"]:
        if not isinstance(entry, dict):
            raise ValueError("Invalid partition entry")
        topic, partition, replicas = entry.get("topic"), entry.get("partition"), entry.get("replicas")
        if not isinstance(topic, str) or not topic or type(partition) is not int or partition < 0:
            raise ValueError("Invalid topic/partition")
        if (topic, partition) in seen:
            raise ValueError("Duplicate topic/partition")
        seen.add((topic, partition))
        if (not isinstance(replicas, list) or not replicas
                or any(type(broker) is not int or broker < 0 for broker in replicas)
                or len(replicas) != len(set(replicas))):
            raise ValueError("Invalid replica list")
        if "log_dirs" in entry:
            if (not isinstance(entry["log_dirs"], list) or len(entry["log_dirs"]) != len(replicas)
                    or not all(isinstance(directory, str) for directory in entry["log_dirs"])):
                raise ValueError("Log directory and replica lists must have equal lengths")
    return proposal


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        proposal = extract(args.input.read_text())
        with args.output.open("x") as stream:
            json.dump(proposal, stream, indent=2)
            stream.write("\n")
    except (ValueError, OSError, TypeError, AttributeError) as error:
        parser.exit(1, f"Proposal extraction failed: {error}\n")
```

```bash
python3 extract_reassignment.py generate-output.txt reassignment.json
python3 -m json.tool reassignment.json
# Review topic coverage, replica order/count, broker IDs, racks and capacity.
: "${DOCS_MOVE_BYTES_PER_SEC:?Choose the reviewed movement throttle in bytes/second}"
kafka-reassign-partitions.sh \
  --bootstrap-server "$DOCS_BOOTSTRAP" --command-config "$DOCS_ADMIN_CONFIG" \
  --reassignment-json-file reassignment.json --execute \
  --throttle "$DOCS_MOVE_BYTES_PER_SEC"

# Status check without removing configured throttles:
kafka-reassign-partitions.sh \
  --bootstrap-server "$DOCS_BOOTSTRAP" --command-config "$DOCS_ADMIN_CONFIG" \
  --reassignment-json-file reassignment.json --verify --preserve-throttles
```

이 도구의 JSON 검증은 형식 검사입니다. 실제 broker 존재, RF 보존, rack 균형이나 전체 partition inventory를 입증하지 않습니다.

`--verify`는 지정된 재배치·log directory 이동 상태를 확인합니다. **`--preserve-throttles` 없이 완료 상태를 확인하면 broker/topic throttle 설정을 정리할 수 있으므로 순수한 읽기 명령이 아닙니다.** 다른 작업과 공유하는 제한이 있는지 확인한 뒤 정리합니다. 이 옵션이 under-replicated/offline partition을 모두 검사한다는 뜻도 아닙니다.

```bash
kafka-topics.sh --bootstrap-server "$DOCS_BOOTSTRAP" --command-config "$DOCS_ADMIN_CONFIG" \
  --describe --under-replicated-partitions
kafka-topics.sh --bootstrap-server "$DOCS_BOOTSTRAP" --command-config "$DOCS_ADMIN_CONFIG" \
  --describe --under-min-isr-partitions
kafka-topics.sh --bootstrap-server "$DOCS_BOOTSTRAP" --command-config "$DOCS_ADMIN_CONFIG" \
  --describe --unavailable-partitions
```

## 7. 버전 업그레이드

먼저 **현재 Kafka와 목표 Kafka를 모두 지원하는 Operator 조합**을 선택합니다. 이미 지원한다면 Operator를 먼저 바꿀 이유는 없습니다. 반대로 최신 Operator가 현재 Kafka를 지원하지 않으면 곧바로 설치하지 말고 중간 지원 버전과 API 변환 경로를 계획합니다.

### 소프트웨어와 metadataVersion

Strimzi는 `metadataVersion`을 명시하지 않은 경우 Kafka binary 업데이트 후 기본 metadata version으로 자동 갱신할 수 있습니다. 두 필드를 같은 변경에 넣으면 무조건 quorum이 깨진다는 설명은 맞지 않습니다.

검증/복구 판단 시간을 확보하려면 이전 metadataVersion을 명시적으로 유지한 뒤 나중에 올리는 패턴을 사용할 수 있습니다. 다음 예제는 **기존 Kafka 4.2.1 / metadata 4.2-IV1**을 Strimzi 1.2에서 4.3.1로 올리는 경우입니다. 이미 4.3.1인 Part 2 실습 클러스터에 이 패치를 적용해 metadata를 낮추는 절차가 아닙니다.

**`upgrade-binaries.patch.yaml`**

```yaml
# Only for an existing Kafka 4.2.1 cluster currently using metadata 4.2-IV1.
spec:
  kafka:
    version: 4.3.1
    metadataVersion: 4.2-IV1
```

```bash
kubectl -n kafka get kafka my-cluster -o yaml > kafka-before-upgrade.yaml
# Check current version, metadataVersion and any custom image override first.
kubectl -n kafka patch kafka my-cluster --type=merge \
  --patch-file upgrade-binaries.patch.yaml
kubectl -n kafka get pods -l 'strimzi.io/cluster=my-cluster,strimzi.io/pool-name' \
  -o 'custom-columns=NAME:.metadata.name,IMAGES:.spec.containers[*].image'
kubectl -n kafka get kafka my-cluster -o yaml
```

`status.kafkaVersion`, `status.kafkaMetadataVersion`, `status.operatorLastSuccessfulVersion`, generation과 실제 Pod image를 함께 확인합니다. image override와 Connect/MirrorMaker 사용자 이미지를 쓰면 호환되는 이미지도 함께 준비해야 합니다.

클라이언트 동작·복구 계획을 검토한 뒤 필요한 경우 metadata를 올립니다. 새 metadata/feature를 사용한 뒤에는 다운그레이드가 불가능할 수 있으며 단순 Git revert를 복구 보장으로 취급하지 않습니다.

**`upgrade-metadata.patch.yaml`**

```yaml
# Apply only after validating the completed binary upgrade and recovery plan.
spec:
  kafka:
    metadataVersion: 4.3-IV0
```

```bash
kubectl -n kafka patch kafka my-cluster --type=merge \
  --patch-file upgrade-metadata.patch.yaml
kubectl -n kafka get kafka my-cluster -o yaml
```

모든 spec 변경이 Pod를 재시작하는 것은 아닙니다. 동적 Kafka config나 지원되는 볼륨 확장은 별도 방식으로 반영될 수 있습니다. 재시작이 필요한 경우에도 Operator의 availability 검사는 절대적인 무중단·무손실 보장이 아닙니다. 데이터 상태, ISR, controller quorum, client timeout·재시도를 함께 관측합니다.

## 8. PDB와 장애 대응

Strimzi 1.2의 기본 Kafka PDB는 **Kafka 클러스터 하나에 하나이며 모든 node pool의 Kafka Pod를 포함**합니다. pool마다 별도 PDB가 생기는 것이 아닙니다. 생성 설정이나 사용자 PDB를 변경한 경우에는 실제 selector·minAvailable/maxUnavailable을 확인합니다.

PDB는 자발적 eviction을 제한합니다. 노드 장애·AZ 손실·직접 Pod 삭제·모든 Operator 동작을 막는 안전장치가 아닙니다. `min.insync.replicas`도 모든 데이터 손실을 방지하는 단일 스위치가 아닙니다.

```bash
kubectl -n kafka get pdb -l strimzi.io/cluster=my-cluster -o yaml
kubectl -n kafka get kafka my-cluster -o yaml
kubectl -n kafka get pods,pvc -l strimzi.io/cluster=my-cluster
```

`acks=all`은 동기화된 복제본의 승인이라는 조건 아래 더 강한 내구성을 제공하지만 애플리케이션의 요청이 항상 성공하는 것은 아닙니다. 재시작 중 leader/coordinator 변경, timeout, 재시도와 처리 중복을 계획합니다. broker 재시작이 모든 consumer group을 반드시 전체 중단시키는 것도 아닙니다.

Strimzi Drain Cleaner 같은 추가 구성은 별도 지원 모드와 PDB 동작을 확인합니다. 장애가 났다는 이유만으로 finalizer나 scale-down 검사를 제거하지 말고, 원인과 남아 있는 replica·metadata를 먼저 확인합니다.

## 다음 단계와 참고

- [Schema Registry](./04-schema-registry.md)
- [Kafka overview](./README.md)
- [Quiz](../../quizzes/data-on-eks/kafka/03-kafka-operations-quiz.md)
- [Strimzi 1.2 operations](https://strimzi.io/docs/operators/1.2.0/deploying.html)
- [Kafka 4.3 design](https://kafka.apache.org/43/design/design/)
- [Kafka 4.3.1 log directory selection](https://github.com/apache/kafka/blob/4.3.1/core/src/main/scala/kafka/log/LogManager.scala)
- [Kafka reassignment command implementation](https://github.com/apache/kafka/blob/4.3.1/tools/src/main/java/org/apache/kafka/tools/reassign/ReassignPartitionsCommand.java)
- [EBS gp3](https://docs.aws.amazon.com/ebs/latest/userguide/general-purpose.html)
- [EBS io2 Block Express](https://docs.aws.amazon.com/ebs/latest/userguide/provisioned-iops.html)
- [EBS pricing](https://aws.amazon.com/ebs/pricing/)
