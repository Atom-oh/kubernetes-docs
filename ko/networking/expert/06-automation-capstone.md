# 6. 네트워크 자동화와 종합 평가

> **마지막 업데이트**: 2026년 9월 15일

**선수 조건:** 공통으로 1·2·4장의 관측 능력이 필요합니다. EVPN/fabric 종합 과제에는 3장, cloud 종합 과제에는 5장을 추가합니다. Linux 호스트 종합 과제는 4장의 제한된 실험을 사용합니다. 아래 검증기 연습은 Python 3.9+와 자신의 새 작업 디렉터리만 필요합니다.

**목표:** 의도와 관측을 분리하고, 정상·금지·장애·복구를 재현 가능한 결과물로 제출합니다. 자동화는 누락된 증거를 성공으로 바꾸는 장치가 아닙니다.

## 1. 변경 전에 의도부터 승인하기 {#intent}

| 구분 | 변경 전에 정할 것 | 관측 후 확인 |
|---|---|---|
| 도달성 | 누가 어느 서비스에 접근해야 하는가? | 실제 응답과 관측 지점 |
| 격리 | 어떤 흐름이 금지되어야 하는가? | 정책 근거와 probe를 함께 확인 |
| 경로 정책 | 어느 peer/VRF에 어떤 prefix를 광고해야 하는가? | 같은 범위의 실제 광고·선택·전달 상태 |
| 복원력 | 한 항목이 실패하면 무엇이 유지되어야 하는가? | 서비스 연속성과 수렴·복구 구간 |
| 운영 경계 | 관리 접근, 변경 범위, 중단 조건은 무엇인가? | 범위 밖 변경이 없는지와 원상복구 |

기대값을 결과와 같은 변경에서 임의로 맞추면 회귀를 숨길 수 있습니다. 의도 문서는 먼저 검토하고 revision/hash를 기록합니다. 관측 어댑터는 실제 출력의 단위·scope·시간을 유지하며 정규화합니다.

예를 들어 FRR의 특정 peer 광고, Linux의 전체 FIB, TGW route table을 같은 데이터라고 취급하지 않습니다. 아래 prefix 계약은 **지정한 peer에 광고한 prefix 집합**만 비교합니다. 경로 선호도, ECMP 개수, FIB 설치나 실제 전달 성공은 별도 증거입니다.

## 2. 작은 검증기 연습 {#record-validator}

아래 데이터는 **합성 예제**입니다. 네트워크를 구성하거나 패킷을 전송하지 않습니다. 검증기는 입력된 의도와 기록의 일관성을 검사하며, 원본 PCAP·카운터의 진위를 증명하지 않습니다.

자신의 실습 VM 또는 로컬 학습 터미널에서 새 디렉터리를 만듭니다.

```bash
EVIDENCE_DIR=$(mktemp -d /tmp/network-evidence.XXXXXX)
printf '%s\n' "$EVIDENCE_DIR"
```

아래 JSON을 그 디렉터리의 `intent.json`으로 저장합니다. 실제 자동화에서는 검토된 별도 입력으로 관리합니다.

```json
{
  "schema": 1,
  "scenario": "tenant-isolation",
  "phase": "steady",
  "route_scope": "r2:export-to-r1",
  "maximum_window_seconds": 60,
  "exported_prefixes": ["203.0.113.0/24"],
  "flows": {"a-to-web": "allow", "b-to-a": "deny"}
}
```

다음은 `observations.json`입니다. 주소는 문서용이고 시간·artifact 이름도 설명용입니다.

```json
{
  "schema": 1,
  "scenario": "tenant-isolation",
  "phase": "steady",
  "route_scope": "r2:export-to-r1",
  "evidence_kind": "synthetic",
  "window": {"start": "2026-09-15T00:00:00Z", "end": "2026-09-15T00:00:10Z"},
  "exported_prefixes": ["203.0.113.0/24"],
  "route_artifact": "synthetic:advertised-routes",
  "flows": {
    "a-to-web": {
      "verdict": "allow",
      "artifacts": {"probe": "synthetic:http-response"}
    },
    "b-to-a": {
      "verdict": "deny",
      "artifacts": {"probe": "synthetic:blocked-probe", "policy": "synthetic:policy-decision"}
    }
  }
}
```

다음 Python을 같은 디렉터리의 `check_record.py`로 저장합니다.

```python
import ipaddress
import json
import sys
from datetime import datetime
from pathlib import Path


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON key: " + key)
        result[key] = value
    return result


def load(path):
    return json.loads(Path(path).read_text(), object_pairs_hook=unique_object)


def prefixes(values):
    require(isinstance(values, list), "prefixes must be a list")
    return {str(ipaddress.ip_network(value, strict=True)) for value in values}


def timestamp(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(parsed.tzinfo is not None, "timestamp needs a timezone")
    return parsed


require(len(sys.argv) == 3, "usage: check_record.py intent.json observations.json")
intent, seen = load(sys.argv[1]), load(sys.argv[2])
for record in (intent, seen):
    require(type(record.get("schema")) is int and record["schema"] == 1, "schema")
for key in ("scenario", "phase", "route_scope"):
    require(intent[key] == seen[key], "scope mismatch: " + key)
require(seen["evidence_kind"] in {"synthetic", "supplied", "measured"}, "evidence kind")
duration = (timestamp(seen["window"]["end"]) - timestamp(seen["window"]["start"])).total_seconds()
require(0 < duration <= intent["maximum_window_seconds"], "invalid observation window")
require(prefixes(intent["exported_prefixes"]), "empty intended prefix scope")
require(prefixes(seen["exported_prefixes"]) == prefixes(intent["exported_prefixes"]), "prefix mismatch")
require(isinstance(seen.get("route_artifact"), str) and seen["route_artifact"].strip(), "route evidence missing")
require(intent["flows"] and set(intent["flows"]) == set(seen["flows"]), "flow coverage mismatch")
for name, wanted in intent["flows"].items():
    require(wanted in {"allow", "deny"}, "unsupported intent")
    actual = seen["flows"][name]
    require(actual["verdict"] == wanted, "flow mismatch: " + name)
    needed = {"probe"} if wanted == "allow" else {"probe", "policy"}
    artifacts = actual["artifacts"]
    require(all(isinstance(artifacts.get(k), str) and artifacts[k].strip() for k in needed),
            "evidence missing: " + name)
print("CONSISTENT_RECORD kind=" + seen["evidence_kind"] + "; live behavior not attested")
```

실행합니다.

```bash
python3 "${EVIDENCE_DIR:?}/check_record.py" \
  "${EVIDENCE_DIR:?}/intent.json" "${EVIDENCE_DIR:?}/observations.json"
```

기대 출력은 `CONSISTENT_RECORD kind=synthetic; live behavior not attested`입니다. 이는 이 기록의 필수 조건 검사 통과이며 네트워크 통신 성공이나 운영 반영 승인이 아닙니다. `assert` 대신 명시적인 예외를 사용하므로 Python 최적화 옵션으로 검사가 제거되지 않습니다.

### 반드시 실패시킬 입력

원본 파일을 유지하고 `observations-bad.json` 복사본으로 다음을 **하나씩** 바꿉니다. 같은 명령의 마지막 인자만 복사본으로 바꿔 실행합니다.

| 변경 | 기대 결과 |
|---|---|
| `b-to-a` 관측 누락 | `flow coverage mismatch` |
| `b-to-a.verdict`를 `unknown` 또는 `allow`로 변경 | `flow mismatch` |
| 금지 흐름의 `policy` artifact 삭제 | `evidence missing` |
| 광고 prefix에 `0.0.0.0/0` 추가 또는 목록을 비움 | `prefix mismatch` |
| 종료 시각을 시작보다 이르게 변경 | `invalid observation window` |
| `phase`를 다른 값으로 변경 | `scope mismatch` |

빈 출력이나 timeout을 `deny`로 정규화하지 않습니다. 금지 결과에는 실제 정책/강제 지점의 근거와 그 probe가 연결되어야 합니다. artifact 이름을 적었다는 사실만으로 그 근거가 존재하거나 올바른 지점에서 수집됐다고 증명되지는 않습니다.

검증기를 실제 수집기로 확장할 때는 파일 존재·해시·시간 범위·수집자·장치/계정 identity를 검사하고 원본과 대조합니다. 주소 집합으로 정규화하면서 경로 속성이나 endpoint별 readiness를 잃지 않도록 해당 검사를 별도로 설계합니다.

## 3. 변경 파이프라인 설계 {#pipeline}

다음 단계의 입력과 출력, 실패 시 담당자를 정의합니다.

| 단계 | 검사 | 다음 단계로 넘기는 결과 |
|---|---|---|
| 의도 검토 | 허용/금지 흐름·경로·관리 접근·고장 범위 | 검토된 의도 revision |
| 정적 검증 | 구문·지원 기능·주소 중복·정책 범위 | 정확한 도구/provider 버전에 대한 결과 |
| 변경 미리 보기 | 영향 범위와 대상, 예상 차이, 복구 가능성 | 사람이 검토할 변경 계획 |
| 실습 환경 적용 | 한 항목 변경, 시간/자원 제한, 관리 경로 유지 | 사전·사후 상태와 실행 기록 |
| 동작 확인 | 허용·금지·장애·복구와 누락 증거 | 원본과 연결된 구조화 결과 |
| 운영 판단 | 검증 범위, 미확인 항목, rollout/rollback 조건 | 별도 운영 절차에 따른 승인 또는 거절 |

이 과정은 운영 배포를 자동 승인하는 파이프라인을 제공하지 않습니다. 복구 명령 자체도 사전에 읽고, 관리 경로가 영향받는 경우 콘솔 등 독립적인 복구 경로를 준비합니다.

## 4. 종합 과제 선택 {#capstones}

### A. 라우팅·fabric

[2장](02-routing-policy-convergence.md)과 [3장](03-datacenter-evpn.md)의 준비된 lab 중 하나를 사용합니다.

1. 특정 peer/VRF의 허용 prefix와 금지 경로·흐름을 정의합니다.
2. 정상 광고·선택·FIB·서비스 probe를 기록합니다.
3. 해당 장에서 복구 가능한 단일 정책 또는 경로 장애를 선택합니다.
4. 제어 평면 변화와 실제 서비스 복구 시점을 분리합니다.
5. 원래 설정을 복원하고 허용 흐름과 격리를 다시 확인합니다.

세션이 다시 Established가 된 시각을 서비스 수렴 시각으로 대체하지 않습니다. 다른 장비의 시계를 비교한다면 동기화·오차를 기록하거나 동일 관측자의 시간축을 사용합니다.

### B. Linux·클라우드/SRE

[4장](04-linux-performance.md)의 제한된 호스트 실험 또는 [5장](05-cloud-cni-design.md)의 승인된 cloud 증거를 선택합니다.

1. 흐름의 정방향·반환 경로와 최소 두 관측 지점을 표시합니다.
2. 지연·손실·큐·정책 중 가설 하나를 고르고 반증 조건을 정합니다.
3. 실제 관측과 source/namespace·시간·단위를 연결합니다.
4. 실험을 수행했다면 정확히 복구하고 같은 기준으로 재확인합니다.
5. 설계/제공 자료만 분석했다면 그 범위로 결과를 제한합니다.

실제 장비·계정이 없으면 설계 또는 제공 증거 분석을 제출할 수 있습니다. **실습 수행 완료**는 자신이 실행한 제한된 실험의 원본·복구 증거가 있어야 표시합니다.

## 5. 평가표 {#assessment}

각 항목을 `충족 / 미충족 / 미관측`으로 평가합니다. 합산 점수로 필수 증거의 누락을 숨기지 않습니다.

| 항목 | 충족 기준 |
|---|---|
| 범위·재현성 | 토폴로지, 환경, 권한, 버전/revision, 입력과 시간 범위를 재구성할 수 있음 |
| 프로토콜 추론 | 패킷/경로/애플리케이션 관계를 설명하고 최소 한 가설을 반증함 |
| 정상·금지 검증 | 긍정 probe와 격리 조건을 각각 확인하고 누락을 성공으로 처리하지 않음 |
| 장애·복구 | 단일 변화의 영향과 복구 후 상태를 같은 기준으로 확인함 |
| 자동화 품질 | 잘못된 scope·누락·unknown·의도 불일치를 거절하고 원본을 추적함 |
| 판단의 정직성 | 실측·제공·합성·설계 근거와 미관측 항목을 구분함 |

필수 항목이 미충족이면 해당 장으로 돌아가 보완합니다. 미관측 항목은 실환경 검증 완료로 선언하지 않습니다. 리뷰어는 같은 자료로 결론을 재구성할 수 있어야 합니다.

## 정리와 후속 학습

검증기 연습 파일만 정리할 때 자신의 디렉터리에서 생성한 파일을 확인합니다.

```bash
ls -la -- "${EVIDENCE_DIR:?}"
rm -- "${EVIDENCE_DIR:?}/intent.json" "${EVIDENCE_DIR:?}/observations.json" \
  "${EVIDENCE_DIR:?}/check_record.py"
```

복사본을 만들었다면 **확인한 그 파일만** 별도로 삭제한 뒤 `rmdir -- "${EVIDENCE_DIR:?}"`를 실행합니다. 실제 실험 원본은 이 임시 합성 예제와 구분해 승인된 보관 정책을 따릅니다.

이후 포트폴리오에서 가장 약한 항목에 맞춰 [프로토콜](01-protocol-projects.md), [라우팅](02-routing-policy-convergence.md), [EVPN](03-datacenter-evpn.md), [Linux 성능](04-linux-performance.md), [클라우드](05-cloud-cni-design.md) 실험을 추가합니다.

참고: [Python JSON](https://docs.python.org/3/library/json.html), [ipaddress](https://docs.python.org/3/library/ipaddress.html), [datetime](https://docs.python.org/3/library/datetime.html).

[이전: 클라우드·CNI](05-cloud-cni-design.md) · [퀴즈](../../quizzes/networking/expert/06-automation-capstone-quiz.md) · [과정으로](README.md)
