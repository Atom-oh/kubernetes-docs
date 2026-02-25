# Kubescape 퀴즈

다음 질문들을 통해 Kubescape 보안 태세 관리 도구에 대한 이해도를 점검해보세요.

---

## 문제

### 1. Kubescape 프로젝트의 CNCF 상태는?

- A) Graduated
- B) Incubating
- C) Sandbox
- D) CNCF 프로젝트가 아님

<details>
<summary>정답 보기</summary>

**정답: C) Sandbox**

**설명:**
Kubescape는 2022년 9월 CNCF Sandbox 프로젝트로 승인되었습니다. ARMO에서 시작된 오픈소스 프로젝트로, Kubernetes 보안 태세 관리(KSPM)를 위한 포괄적인 도구입니다. Sandbox 단계는 초기 채택 단계로, 커뮤니티의 관심과 발전 가능성을 인정받은 상태입니다.

</details>

---

### 2. Kubescape가 지원하는 보안 프레임워크가 아닌 것은?

- A) NSA-CISA Kubernetes Hardening Guide
- B) CIS Kubernetes Benchmark
- C) MITRE ATT&CK for Containers
- D) PCI-DSS Kubernetes Standard

<details>
<summary>정답 보기</summary>

**정답: D) PCI-DSS Kubernetes Standard**

**설명:**
Kubescape가 지원하는 주요 보안 프레임워크:

- **NSA-CISA**: NSA와 CISA의 Kubernetes 보안 강화 가이드
- **CIS Benchmark**: Center for Internet Security의 Kubernetes 벤치마크
- **MITRE ATT&CK**: 컨테이너 환경의 공격 기법 매핑

```bash
# 특정 프레임워크로 스캔
kubescape scan framework nsa
kubescape scan framework cis-v1.23-t1.0.1
kubescape scan framework mitre
```

PCI-DSS는 결제 카드 산업 보안 표준으로, Kubernetes 전용 프레임워크가 별도로 존재하지 않습니다.

</details>

---

### 3. Kubescape CLI로 클러스터를 스캔하는 기본 명령어 형식은?

- A) kubescape check cluster
- B) kubescape scan
- C) kubescape audit --cluster
- D) kubescape verify

<details>
<summary>정답 보기</summary>

**정답: B) kubescape scan**

**설명:**
Kubescape CLI 기본 사용법:

```bash
# 클러스터 전체 스캔 (모든 프레임워크)
kubescape scan

# 특정 프레임워크로 스캔
kubescape scan framework nsa

# 특정 네임스페이스만 스캔
kubescape scan --include-namespaces production,staging

# 특정 컨트롤만 스캔
kubescape scan control C-0001,C-0002

# YAML 파일 스캔 (CI/CD용)
kubescape scan *.yaml

# 결과를 JSON으로 출력
kubescape scan --format json --output results.json
```

</details>

---

### 4. Kubescape Operator와 CLI 모드의 주요 차이점은?

- A) Operator는 GUI만 제공
- B) Operator는 클러스터 내 지속적 모니터링, CLI는 일회성 스캔
- C) CLI만 CIS 프레임워크 지원
- D) Operator는 유료 전용

<details>
<summary>정답 보기</summary>

**정답: B) Operator는 클러스터 내 지속적 모니터링, CLI는 일회성 스캔**

**설명:**
두 모드의 차이:

| 특성 | CLI | Operator |
|------|-----|----------|
| 실행 방식 | 일회성 스캔 | 지속적 모니터링 |
| 배포 위치 | 로컬/CI | 클러스터 내부 |
| 리소스 변경 감지 | 수동 재스캔 필요 | 자동 감지 |
| 이미지 스캐닝 | 지원 | 지원 + 스케줄링 |
| 대시보드 | 없음 | ARMO 플랫폼 연동 |

```bash
# Operator 설치 (Helm)
helm repo add kubescape https://kubescape.github.io/helm-charts/
helm install kubescape kubescape/kubescape-operator \
  --namespace kubescape --create-namespace
```

</details>

---

### 5. Kubescape의 리스크 스코어(Risk Score) 계산 방식은?

- A) 발견된 취약점 수의 합계
- B) 컨트롤 실패 수 / 전체 컨트롤 수
- C) 실패한 리소스의 심각도 가중 평균
- D) CVSS 점수의 평균

<details>
<summary>정답 보기</summary>

**정답: C) 실패한 리소스의 심각도 가중 평균**

**설명:**
Kubescape 리스크 스코어 계산:

```
리스크 스코어 = Σ(실패 리소스 × 컨트롤 심각도 가중치) / Σ(전체 리소스 × 최대 가중치)
```

스코어 해석:
- **0-30%**: 낮은 리스크 (양호)
- **30-60%**: 중간 리스크 (주의 필요)
- **60-100%**: 높은 리스크 (즉시 조치 필요)

```bash
# 스캔 결과 예시
kubescape scan framework nsa

# Controls: 28 (Failed: 5, Passed: 18, Skipped: 5)
# Risk Score: 24%
```

단순 실패 수가 아닌 리소스 중요도와 컨트롤 심각도를 고려합니다.

</details>

---

### 6. CI/CD 파이프라인에서 Kubescape 스캔이 특정 점수 이상이면 실패하도록 설정하는 플래그는?

- A) --fail-threshold
- B) --compliance-threshold
- C) --max-score
- D) --risk-limit

<details>
<summary>정답 보기</summary>

**정답: B) --compliance-threshold**

**설명:**
CI/CD 통합을 위한 임계값 설정:

```bash
# 리스크 스코어가 30% 초과 시 실패 (exit code 1)
kubescape scan --compliance-threshold 30

# GitHub Actions 예시
- name: Kubescape Scan
  run: |
    kubescape scan framework nsa \
      --compliance-threshold 25 \
      --format junit \
      --output kubescape-results.xml

# 결과
# If risk score <= 30%: exit 0 (성공)
# If risk score > 30%: exit 1 (실패)
```

이를 통해 보안 게이트를 설정하고 기준 미달 배포를 차단할 수 있습니다.

</details>

---

### 7. kube-bench와 Kubescape의 주요 차이점은?

- A) kube-bench는 클러스터 구성만, Kubescape는 워크로드 포함 종합 스캔
- B) Kubescape는 CIS 벤치마크 미지원
- C) kube-bench가 더 많은 프레임워크 지원
- D) 기능 차이 없음

<details>
<summary>정답 보기</summary>

**정답: A) kube-bench는 클러스터 구성만, Kubescape는 워크로드 포함 종합 스캔**

**설명:**
kube-bench vs Kubescape 비교:

| 특성 | kube-bench | Kubescape |
|------|------------|-----------|
| 스캔 대상 | 노드/컨트롤 플레인 구성 | 클러스터 + 워크로드 + 이미지 |
| 프레임워크 | CIS 전용 | NSA, CIS, MITRE 등 |
| 실행 위치 | 각 노드에서 실행 | 외부 또는 클러스터 내 |
| YAML 스캔 | 미지원 | 지원 (CI/CD) |
| 이미지 취약점 | 미지원 | 지원 |

```bash
# kube-bench: 노드 구성 검사
kube-bench run --targets node

# Kubescape: 종합 보안 스캔
kubescape scan framework cis
```

두 도구는 보완적이며, 함께 사용하면 더 포괄적인 보안 평가가 가능합니다.

</details>

---

### 8. Kubescape의 RBAC 시각화 기능이 제공하는 정보는?

- A) 네트워크 정책 그래프
- B) 주체별 권한 매핑 및 과도한 권한 탐지
- C) Pod 간 통신 흐름
- D) 인증서 체인 구조

<details>
<summary>정답 보기</summary>

**정답: B) 주체별 권한 매핑 및 과도한 권한 탐지**

**설명:**
Kubescape RBAC 분석 기능:

```bash
# RBAC 시각화
kubescape scan control C-0035  # RBAC 관련 컨트롤

# 분석 결과 예시
# - ServiceAccount 'default'가 cluster-admin 권한 보유
# - 불필요한 secrets 읽기 권한 탐지
# - 과도한 와일드카드(*) 권한 사용
```

탐지하는 RBAC 문제:
- 과도한 권한 부여 (Privilege Escalation 가능성)
- 사용되지 않는 Role/RoleBinding
- 위험한 와일드카드 사용
- cluster-admin 남용
- 민감한 리소스(secrets, configmaps)에 대한 광범위한 접근

</details>

---

### 9. Kubescape에서 이미지 취약점 스캐닝을 위해 연동되는 도구는?

- A) Trivy
- B) Grype
- C) Clair
- D) Snyk

<details>
<summary>정답 보기</summary>

**정답: B) Grype**

**설명:**
Kubescape는 Anchore의 Grype를 통해 컨테이너 이미지 취약점을 스캔합니다:

```bash
# 이미지 스캔 포함 전체 검사
kubescape scan --enable-host-scan

# Operator 모드에서 이미지 스캔 설정
apiVersion: kubescape.io/v1
kind: VulnerabilityManifest
spec:
  scanner: grype
  schedule: "0 */6 * * *"  # 6시간마다 스캔
```

Grype 연동 이점:
- SBOM(Software Bill of Materials) 생성
- CVE 데이터베이스 기반 취약점 탐지
- 심각도별 분류 (Critical, High, Medium, Low)
- 워크로드 컨텍스트에서 취약점 우선순위화

</details>

---

### 10. Kubescape에서 특정 컨트롤을 예외 처리하는 방법은?

- A) kubescape.ignore 파일 생성
- B) 리소스에 kubescape.io/ignore 어노테이션 추가
- C) --exclude-controls 플래그와 예외 설정 파일 사용
- D) ConfigMap으로 예외 정책 정의

<details>
<summary>정답 보기</summary>

**정답: C) --exclude-controls 플래그와 예외 설정 파일 사용**

**설명:**
Kubescape 예외 처리 방법:

```bash
# CLI에서 특정 컨트롤 제외
kubescape scan --exclude-controls C-0001,C-0002

# 예외 설정 파일 사용
kubescape scan --exceptions exceptions.json
```

exceptions.json 예시:
```json
{
  "name": "my-exceptions",
  "policyType": "postureExceptionPolicy",
  "actions": ["alertOnly"],
  "resources": [
    {
      "designatorType": "Attributes",
      "attributes": {
        "namespace": "kube-system"
      }
    }
  ],
  "posturePolicies": [
    {
      "controlID": "C-0001"
    }
  ]
}
```

예외 처리 시 고려사항:
- 비즈니스 정당성 문서화
- 주기적인 예외 검토
- 최소한의 범위로 예외 적용

</details>

---

## 점수 계산

- **9-10개 정답**: 우수 - 해당 주제를 깊이 이해하고 있습니다.
- **7-8개 정답**: 양호 - 핵심 개념을 잘 파악하고 있습니다.
- **5-6개 정답**: 보통 - 추가 학습이 필요한 부분이 있습니다.
- **4개 이하**: 문서를 다시 복습하시기 바랍니다.

## 관련 문서

- [Kubescape를 활용한 보안 태세 관리](../../security/11-kubescape.md)
