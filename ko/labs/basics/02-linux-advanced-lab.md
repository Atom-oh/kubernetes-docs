# Linux 실무 기술 실습 가이드

> **난이도**: 초급
> **예상 소요 시간**: 40분
> **마지막 업데이트**: 2026년 2월 11일

## 학습 목표
- jq를 사용한 JSON 데이터 파싱을 실습합니다
- 간단한 쉘 스크립트를 작성합니다
- kubectl 출력을 파이프라인으로 처리합니다

## 사전 요구 사항
- [ ] Linux 터미널 접근
- [ ] jq 설치 (`sudo apt-get install jq` 또는 `sudo yum install jq`)
- [ ] [Linux 운영 기술](../../basics/02-linux-advanced.md) 학습 완료

---

## 실습 1: jq를 사용한 JSON 파싱

### 목표
Kubernetes kubectl 출력과 유사한 JSON 데이터를 jq로 처리합니다.

### 단계

**Step 1.1: 샘플 JSON 생성**
```bash
cat > /tmp/pods.json << 'EOF'
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
jq '.items[].metadata.name' /tmp/pods.json

# Running 상태인 Pod만 필터링
jq '.items[] | select(.status.phase == "Running") | .metadata.name' /tmp/pods.json

# 테이블 형태 출력
jq -r '.items[] | [.metadata.name, .metadata.namespace, .status.phase] | @tsv' /tmp/pods.json
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
jq '[.items[].metadata.namespace] | group_by(.) | map({namespace: .[0], count: length})' /tmp/pods.json

# label 기반 필터링
jq '.items[] | select(.metadata.labels.app == "nginx") | {name: .metadata.name, ip: .status.podIP}' /tmp/pods.json
```

<details>
<summary>힌트가 필요하신가요?</summary>

- `jq -r`은 문자열의 따옴표를 제거합니다
- `select(조건)`은 조건에 맞는 항목만 필터링합니다
- `@tsv`는 탭 구분 형식으로 출력합니다
- 실제 K8s에서는 `kubectl get pods -o json | jq '...'` 형태로 사용합니다
</details>

### 검증
```bash
# Running Pod 수가 2개인지 확인
COUNT=$(jq '[.items[] | select(.status.phase == "Running")] | length' /tmp/pods.json)
[ "$COUNT" -eq 2 ] && echo "정답! Running Pod 수: $COUNT" || echo "다시 확인하세요"
```

---

## 실습 2: 쉘 스크립트 작성

### 목표
K8s 운영에 유용한 간단한 쉘 스크립트를 작성합니다.

### 단계

**Step 2.1: Health Check 스크립트**
```bash
cat > /tmp/health-check.sh << 'SCRIPT'
#!/bin/bash
# K8s liveness probe에서 사용할 수 있는 health check 스크립트

ENDPOINT="${1:-http://localhost:8080/health}"
TIMEOUT="${2:-5}"

response=$(curl -s -o /dev/null -w "%{http_code}" --max-time $TIMEOUT "$ENDPOINT" 2>/dev/null)

if [ "$response" = "200" ]; then
    echo "OK: Health check passed (HTTP $response)"
    exit 0
else
    echo "FAIL: Health check failed (HTTP $response)"
    exit 1
fi
SCRIPT

chmod +x /tmp/health-check.sh
cat /tmp/health-check.sh
```

**Step 2.2: 로그 분석 스크립트**
```bash
cat > /tmp/log-analyzer.sh << 'SCRIPT'
#!/bin/bash
# 로그 파일에서 에러 패턴을 분석하는 스크립트

LOG_FILE="${1:-/tmp/sample.log}"

# 샘플 로그 생성
if [ ! -f "$LOG_FILE" ]; then
    for i in $(seq 1 100); do
        level=$((RANDOM % 4))
        case $level in
            0) echo "$(date -Iseconds) INFO  Request processed successfully" ;;
            1) echo "$(date -Iseconds) WARN  High memory usage detected" ;;
            2) echo "$(date -Iseconds) ERROR Connection timeout to database" ;;
            3) echo "$(date -Iseconds) INFO  Health check passed" ;;
        esac
    done > "$LOG_FILE"
fi

echo "=== 로그 분석 결과 ==="
echo "총 라인 수: $(wc -l < "$LOG_FILE")"
echo ""
echo "레벨별 통계:"
grep -oP '(INFO|WARN|ERROR)' "$LOG_FILE" | sort | uniq -c | sort -rn
echo ""
echo "최근 에러 (마지막 5개):"
grep "ERROR" "$LOG_FILE" | tail -5
SCRIPT

chmod +x /tmp/log-analyzer.sh
bash /tmp/log-analyzer.sh
```

<details>
<summary>힌트가 필요하신가요?</summary>

- `$((RANDOM % N))`은 0부터 N-1까지의 랜덤 숫자를 생성합니다
- `grep -oP`는 Perl 정규식으로 매칭된 부분만 추출합니다
- `sort | uniq -c | sort -rn`은 빈도 집계의 기본 패턴입니다
</details>

### 검증
```bash
# 스크립트가 실행 가능한지 확인
[ -x /tmp/health-check.sh ] && echo "health-check.sh 실행 가능" || echo "실행 권한 없음"
[ -x /tmp/log-analyzer.sh ] && echo "log-analyzer.sh 실행 가능" || echo "실행 권한 없음"
```

---

## 실습 3: 텍스트 처리 파이프라인

### 목표
grep, awk, sed를 조합하여 데이터를 처리합니다.

### 단계

**Step 3.1: grep 패턴 검색**
```bash
# 샘플 로그에서 ERROR 라인 추출
grep "ERROR" /tmp/sample.log | head -5

# 시간대별 에러 추출 (정규식 사용)
grep -P "T\d{2}:" /tmp/sample.log | grep ERROR | head -5
```

**Step 3.2: awk 필드 추출**
```bash
# 로그에서 시간과 레벨만 추출
awk '{print $1, $2}' /tmp/sample.log | head -10

# ERROR 레벨만 필터링하고 카운트
awk '$2 == "ERROR" {count++} END {print "에러 수:", count}' /tmp/sample.log
```

**Step 3.3: sed 텍스트 변환**
```bash
# 로그 레벨을 한글로 변환
sed 's/INFO/정보/g; s/WARN/경고/g; s/ERROR/오류/g' /tmp/sample.log | head -5

# K8s YAML 값 변경 (ConfigMap 업데이트 시뮬레이션)
echo "replicas: 3" | sed 's/replicas: [0-9]*/replicas: 5/'
```

**Step 3.4: 파이프라인 조합**
```bash
# 에러 메시지별 빈도 분석
grep "ERROR" /tmp/sample.log | awk '{$1=$2=""; print $0}' | sort | uniq -c | sort -rn
```

### 검증
```bash
echo "실습 완료! 파이프라인 조합을 자유롭게 실험해보세요."
```

---

## 정리
```bash
rm -f /tmp/pods.json /tmp/health-check.sh /tmp/log-analyzer.sh /tmp/sample.log
```

## 다음 단계
- [Linux 실무 기술 퀴즈](../../quizzes/basics/02-linux-advanced-quiz.md)
- [컨테이너 기술 실습](./03-container-technology-lab.md)
