# Linux 실무 기술 실습 가이드

> **난이도**: 초급
> **예상 소요 시간**: 40분
> **마지막 업데이트**: 2026년 9월 11일

## 학습 목표
- jq를 사용한 JSON 데이터 파싱을 실습합니다
- 간단한 쉘 스크립트를 작성합니다
- kubectl 출력을 파이프라인으로 처리합니다

## 사전 요구 사항
- [ ] Bash와 표준 Linux 텍스트 도구(awk, grep, sed, coreutils)
- [ ] jq·curl 설치 (`sudo apt-get install jq curl` 또는 `sudo dnf install jq curl`)
- [ ] [Linux 운영 기술](../../basics/02-linux-advanced.md) 학습 완료

같은 Bash 터미널에서 순서대로 실행합니다. 파일은 전용 임시 디렉터리에 만듭니다. 축약한 PodList는 JSON 파싱 fixture이며 적용할 매니페스트가 아니므로 Kubernetes 클러스터가 필요하지 않습니다. Running phase만으로 Ready를 뜻하지는 않습니다.

---

## 실습 1: jq를 사용한 JSON 파싱

### 목표
Kubernetes kubectl 출력과 유사한 JSON 데이터를 jq로 처리합니다.

### 단계

**Step 1.1: 샘플 JSON 생성**
```bash
LINUX_ADVANCED_LAB_DIR=$(mktemp -d /tmp/k8s-docs-linux-advanced.XXXXXX)
: "${LINUX_ADVANCED_LAB_DIR:?mktemp failed}"
cat > "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/pods.json" << 'EOF'
{
  "apiVersion": "v1",
  "kind": "PodList",
  "items": [
    {
      "metadata": {"name": "nginx-7d4f8b", "namespace": "default", "labels": {"app": "nginx"}},
      "status": {"phase": "Running", "podIP": "10.244.0.5"}
    },
    {
      "metadata": {"name": "redis-abc123", "namespace": "cache", "labels": {"app": "redis"}},
      "status": {"phase": "Running", "podIP": "10.244.1.3"}
    },
    {
      "metadata": {"name": "api-server-xyz", "namespace": "default", "labels": {"app": "api"}},
      "status": {"phase": "Pending", "podIP": null}
    }
  ]
}
EOF
```

**Step 1.2: 기본 jq 쿼리**
```bash
# Pod 이름만 추출
jq '.items[].metadata.name' "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/pods.json"

# Running 상태인 Pod만 필터링
jq '.items[] | select(.status.phase == "Running") | .metadata.name' "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/pods.json"

# 테이블 형태 출력
jq -r '.items[] | [.metadata.name, .metadata.namespace, .status.phase] | @tsv' "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/pods.json"
```

예상 결과:
```
nginx-7d4f8b    default    Running
redis-abc123    cache      Running
api-server-xyz  default    Pending
```

**Step 1.3: 고급 jq 파이프라인**
```bash
# namespace별 Pod 수 집계
jq '[.items[].metadata.namespace] | group_by(.) | map({namespace: .[0], count: length})' "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/pods.json"

# label 기반 필터링
jq '.items[] | select(.metadata.labels.app == "nginx") | {name: .metadata.name, ip: .status.podIP}' "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/pods.json"
```

<details>
<summary>힌트가 필요하신가요?</summary>

- `jq -r`은 문자열의 따옴표를 제거합니다
- `select(조건)`은 조건에 맞는 항목만 필터링합니다
- `@tsv`는 탭 구분 형식으로 출력합니다
- 실제 K8s에서는 `kubectl get pods -A -o json | jq '...'` 형태로 사용합니다
</details>

### 검증
```bash
# Running Pod 수가 2개인지 확인
COUNT=$(jq '[.items[] | select(.status.phase == "Running")] | length' "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/pods.json")
[ "$COUNT" -eq 2 ] && echo "정답! Running Pod 수: $COUNT" || echo "다시 확인하세요"
```

---

## 실습 2: 쉘 스크립트 작성

### 목표
K8s 운영에 유용한 간단한 쉘 스크립트를 작성합니다.

### 단계

**Step 2.1: Health Check 스크립트**
스크립트는 의도적으로 HTTP200을 요구합니다. 타임아웃을 검증하고200헤더를 받았더라도 curl 전송이 실패하면 실패로 처리합니다. curlrc·proxy 설정 없이 직접 요청합니다. 앱이 실제 엔드포인트를 제공해야 하며 스크립트가 생성하지는 않습니다. Kubernetes에서는 가능하면 native httpGet probe를 사용하세요. 그 성공 범위200–399는 이 스크립트와 다릅니다. exec probe라면 이미지에 Bash·curl이 있어야 하고 probe 타임아웃이 스크립트 예산을 수용해야 합니다.

```bash
cat > "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/health-check.sh" << 'SCRIPT'
#!/bin/bash
set -u

ENDPOINT="${1:-http://127.0.0.1:8080/health}"
TIMEOUT="${2:-5}"
if (( $# > 2 )) || ! [[ "$TIMEOUT" =~ ^[1-9][0-9]?$ ]] || (( TIMEOUT > 60 )); then
    printf 'Usage: health-check.sh [http(s) URL] [timeout integer 1..60]\n' >&2
    exit 2
fi
case "$ENDPOINT" in
    http://*|https://*) ;;
    *) printf 'Only HTTP(S) endpoints are supported\n' >&2; exit 2 ;;
esac

# Ignore curlrc and proxies for this direct health-endpoint check.
if ! response=$(curl --disable --noproxy '*' --silent --show-error \
    --output /dev/null --write-out '%{http_code}' \
    --connect-timeout "$TIMEOUT" --max-time "$TIMEOUT" -- "$ENDPOINT"); then
    printf 'FAIL: transport error or timeout\n' >&2
    exit 1
fi
if [[ "$response" == "200" ]]; then
    printf 'OK: health endpoint returned HTTP 200\n'
    exit 0
fi
printf 'FAIL: health endpoint returned HTTP %s\n' "$response" >&2
exit 1
SCRIPT
chmod +x "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/health-check.sh"
```

**Step 2.2: 로그 분석 스크립트**
아래6줄의 합성 fixture를 명시적으로 생성합니다. 분석기는 전달한 일반 파일을 읽기만 하고 경로가 틀렸을 때 데이터를 만들지 않습니다. timestamp와 level이1·2번째 필드인 정적 스냅샷을 전제로 합니다. 메시지에 ERROR라는 단어가 들어 있는 INFO 레코드는 오류로 세면 안 됩니다.

```bash
# Explicit synthetic fixture, not a copy of production logs.
cat > "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/sample.log" << 'LOG'
2026-01-01T10:00:00Z INFO Application started
2026-01-01T10:00:01Z WARN Cache warming
2026-01-01T10:00:02Z ERROR Database connection timeout
2026-01-01T10:00:03Z INFO The word ERROR appears in this message
2026-01-01T10:00:04Z ERROR Upstream request timeout
2026-01-01T10:00:05Z INFO Health check passed
LOG

cat > "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/log-analyzer.sh" << 'SCRIPT'
#!/bin/bash
set -euo pipefail

if (( $# != 1 )) || [[ ! -f "$1" || ! -r "$1" ]]; then
    printf 'Usage: log-analyzer.sh readable-regular-log-file\n' >&2
    exit 2
fi
LOG_FILE="$1"

# Assumes a static snapshot: first field UTC timestamp, second field log level.
printf 'Total lines: %s\n' "$(wc -l < "$LOG_FILE")"
printf 'Counts by level:\n'
awk '$2 ~ /^(INFO|WARN|ERROR)$/ {count[$2]++}
     END {for (level in count) print count[level], level}' "$LOG_FILE" | sort -rn
printf 'Recent ERROR records (last 5):\n'
awk '$2 == "ERROR"' "$LOG_FILE" | tail -5
SCRIPT
chmod +x "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/log-analyzer.sh"
bash "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/log-analyzer.sh" "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/sample.log"
```

<details>
<summary>힌트가 필요하신가요?</summary>

- `awk`로 level 필드를 정확히 비교할 수 있습니다. 메시지의 단어와는 다릅니다.
- `grep -E`는 확장 정규식을 사용하며 예제에 Perl 정규식 지원은 필요하지 않습니다.
- fixture는6개 레코드로 INFO3·WARN1·ERROR2입니다. 실제 서비스 로그가 아닌 합성 데이터의 개수입니다.
</details>

### 검증
```bash
# 스크립트가 실행 가능한지 확인
[ -x "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/health-check.sh" ] && echo "health-check.sh 실행 가능" || echo "실행 권한 없음"
[ -x "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/log-analyzer.sh" ] && echo "log-analyzer.sh 실행 가능" || echo "실행 권한 없음"
```

---

## 실습 3: 텍스트 처리 파이프라인

### 목표
grep, awk, sed를 조합하여 데이터를 처리합니다.

### 단계

**Step 3.1: grep 패턴 검색**
```bash
# Match the level field, not the word ERROR inside a message.
grep -E '^[^[:space:]]+[[:space:]]+ERROR([[:space:]]|$)' "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/sample.log" | head -5

# Sample UTC window: 10:00:02 through 10:00:04 on the fixture date.
grep -E '^2026-01-01T10:00:0[2-4]Z[[:space:]]+ERROR([[:space:]]|$)' "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/sample.log"
```

**Step 3.2: awk 필드 추출**
```bash
# 로그에서 시간과 레벨만 추출
awk '{print $1, $2}' "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/sample.log" | head -10

# ERROR 레벨만 필터링하고 카운트
awk '$2 == "ERROR" {count++} END {print "에러 수:", count+0}' "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/sample.log"
```

**Step 3.3: sed 텍스트 변환**
```bash
# 로그 레벨을 한글로 변환
sed -E 's/^([^[:space:]]+[[:space:]]+)INFO([[:space:]]|$)/\1정보\2/; s/^([^[:space:]]+[[:space:]]+)WARN([[:space:]]|$)/\1경고\2/; s/^([^[:space:]]+[[:space:]]+)ERROR([[:space:]]|$)/\1오류\2/' "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/sample.log" | head -5

# Deployment replicas 필드의 텍스트 예시이며 ConfigMap·API 갱신이 아닙니다
echo "replicas: 3" | sed 's/replicas: [0-9]*/replicas: 5/'
```

**Step 3.4: 파이프라인 조합**
```bash
awk '$2 == "ERROR" {sub(/^[^[:space:]]+[[:space:]]+[^[:space:]]+[[:space:]]+/, ""); print}' "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/sample.log" | sort | uniq -c | sort -rn
```

### 검증
```bash
echo "실습 완료! 파이프라인 조합을 자유롭게 실험해보세요."
```

---

## 정리
```bash
if [[ -n ${LINUX_ADVANCED_LAB_DIR:-} ]]; then
  rm -f -- "$LINUX_ADVANCED_LAB_DIR/pods.json" \
    "$LINUX_ADVANCED_LAB_DIR/health-check.sh" \
    "$LINUX_ADVANCED_LAB_DIR/log-analyzer.sh" \
    "$LINUX_ADVANCED_LAB_DIR/sample.log"
  if rmdir -- "$LINUX_ADVANCED_LAB_DIR"; then
    unset LINUX_ADVANCED_LAB_DIR
  fi
fi
```


## 참고 자료와 검증 범위

* [jq manual](https://jqlang.org/manual/)
* [curl manual](https://curl.se/docs/manpage.html)
* [Kubernetes probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)

로컬 합성 JSON·로그와 모의 curl 상태·종료 코드로 검증합니다. 실제 health 엔드포인트·운영 로그·Kubernetes API에는 접근하지 않습니다.

## 다음 단계
- [Linux 실무 기술 퀴즈](../../quizzes/basics/02-linux-advanced-quiz.md)
- [컨테이너 기술 실습](./03-container-technology-lab.md)
