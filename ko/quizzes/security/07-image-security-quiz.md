# 컨테이너 이미지 보안 퀴즈

이 퀴즈는 이미지 스캐닝, 이미지 서명, 공급망 보안, 베이스 이미지 선택에 대한 이해를 테스트합니다.

## 퀴즈 문제

### 1. Trivy로 컨테이너 이미지를 스캔하는 올바른 명령은?

A. trivy scan nginx:latest
B. trivy image nginx:latest
C. trivy container nginx:latest
D. trivy check nginx:latest

<details>
<summary>정답 보기</summary>

**정답: B. trivy image nginx:latest**

**설명:**
Trivy의 이미지 스캔 명령:
```bash
trivy image nginx:latest
trivy image --severity HIGH,CRITICAL nginx:latest
trivy image --format json nginx:latest
```

`trivy image`는 컨테이너 이미지의 취약점을 스캔합니다.

</details>

### 2. 이미지 서명 및 검증에 사용되는 도구는?

A. Trivy
B. Cosign/Sigstore
C. Clair
D. Anchore

<details>
<summary>정답 보기</summary>

**정답: B. Cosign/Sigstore**

**설명:**
Cosign은 Sigstore 프로젝트의 일부로, 컨테이너 이미지 서명 및 검증을 위한 도구입니다:
```bash
# 이미지 서명
cosign sign --key cosign.key myregistry/myimage:tag

# 서명 검증
cosign verify --key cosign.pub myregistry/myimage:tag
```

Trivy, Clair, Anchore는 취약점 스캐너입니다.

</details>

### 3. "Shift-Left" 보안 접근 방식의 의미는?

A. 보안을 운영 단계로 미룸
B. 보안을 개발 초기 단계로 이동
C. 보안팀만 담당
D. 자동화 제거

<details>
<summary>정답 보기</summary>

**정답: B. 보안을 개발 초기 단계로 이동**

**Explanation:**
Shift-Left 보안은 보안 검사를 개발 주기의 가능한 한 이른 단계로 이동시키는 것입니다:
- IDE 단계에서 스캐닝
- CI/CD 파이프라인에서 빌드 게이트
- PR 검토 시 보안 체크

문제를 일찍 발견할수록 수정 비용이 낮습니다.

</details>

### 4. Distroless 이미지의 주요 특징은?

A. 모든 Linux 유틸리티 포함
B. 애플리케이션 실행에 필요한 최소 구성요소만 포함
C. 디버깅 도구 포함
D. 패키지 관리자 포함

<details>
<summary>정답 보기</summary>

**정답: B. 애플리케이션 실행에 필요한 최소 구성요소만 포함**

**설명:**
Distroless 이미지는:
- 셸 없음 (bash, sh 등)
- 패키지 관리자 없음
- 불필요한 유틸리티 없음
- 최소 공격 표면
- 애플리케이션 런타임만 포함

보안과 이미지 크기 측면에서 이점이 있습니다.

</details>

### 5. Amazon ECR 이미지 스캐닝의 두 가지 유형은?

A. 기본 스캐닝, 고급 스캐닝
B. 자동 스캐닝, 수동 스캐닝
C. 빠른 스캐닝, 심층 스캐닝
D. 무료 스캐닝, 유료 스캐닝

<details>
<summary>정답 보기</summary>

**정답: A. 기본 스캐닝, 고급 스캐닝**

**설명:**
Amazon ECR 스캐닝 유형:
- **기본 스캐닝 (Basic)**: Clair 기반, OS 패키지 취약점 스캔
- **고급 스캐닝 (Enhanced)**: Amazon Inspector 기반, OS + 프로그래밍 언어 패키지 스캔, 지속적 스캐닝

고급 스캐닝은 추가 비용이 발생하지만 더 포괄적입니다.

</details>

### 6. SBOM(Software Bill of Materials)이란?

A. 소프트웨어 라이선스 목록
B. 소프트웨어 구성요소 목록
C. 보안 취약점 목록
D. 빌드 명령어 목록

<details>
<summary>정답 보기</summary>

**정답: B. 소프트웨어 구성요소 목록**

**설명:**
SBOM은 소프트웨어에 포함된 모든 구성요소(라이브러리, 종속성, 버전 등)의 목록입니다. 공급망 보안과 취약점 관리에 필수적입니다:
```bash
# Trivy로 SBOM 생성
trivy image --format spdx-json -o sbom.json nginx:latest
```

</details>

### 7. Kyverno에서 이미지 서명을 검증하는 정책 유형은?

A. validate
B. mutate
C. verifyImages
D. generate

<details>
<summary>정답 보기</summary>

**정답: C. verifyImages**

**설명:**
Kyverno의 `verifyImages` 규칙은 컨테이너 이미지 서명을 검증합니다:
```yaml
spec:
  rules:
  - name: verify-signature
    verifyImages:
    - imageReferences:
      - "myregistry/*"
      attestors:
      - entries:
        - keys:
            publicKeys: |-
              -----BEGIN PUBLIC KEY-----
              ...
              -----END PUBLIC KEY-----
```

</details>

### 8. 이미지 태그 대신 다이제스트를 사용해야 하는 이유는?

A. 더 짧은 이름
B. 불변성 보장
C. 더 빠른 풀링
D. 저장 공간 절약

<details>
<summary>정답 보기</summary>

**정답: B. 불변성 보장**

**설명:**
태그(예: `nginx:latest`)는 다른 이미지를 가리키도록 변경될 수 있습니다. 다이제스트(예: `nginx@sha256:abc123...`)는 특정 이미지 콘텐츠의 해시로, 변경 불가능합니다:
```yaml
image: nginx@sha256:abc123def456...
```

이는 재현성과 보안을 보장합니다.

</details>

### 9. Trivy가 스캔하지 않는 대상은?

A. OS 패키지 취약점
B. 언어별 종속성
C. 런타임 행위
D. 시크릿 탐지

<details>
<summary>정답 보기</summary>

**정답: C. 런타임 행위**

**설명:**
Trivy는 정적 분석 도구로 다음을 스캔합니다:
- OS 패키지 취약점
- 언어별 종속성 (npm, pip, go 등)
- IaC 구성 오류
- 하드코딩된 시크릿
- 라이선스

런타임 행위 분석은 Falco 같은 런타임 보안 도구의 영역입니다.

</details>

### 10. 컨테이너 이미지 레지스트리 보안 모범 사례가 아닌 것은?

A. 프라이빗 레지스트리 사용
B. 이미지 스캐닝 활성화
C. 익명 풀링 허용
D. 취약한 이미지 푸시 차단

<details>
<summary>정답 보기</summary>

**정답: C. 익명 풀링 허용**

**설명:**
레지스트리 보안 모범 사례:
- 프라이빗 레지스트리 사용
- IAM 기반 인증
- 이미지 스캐닝 활성화
- 취약한 이미지 푸시/풀 차단
- 이미지 서명 검증
- 불변 태그 또는 다이제스트 사용

익명 풀링은 보안 위험이 있으며, 프로덕션 환경에서는 비활성화해야 합니다.

</details>

### 11. CI/CD 파이프라인에서 이미지 스캐닝 실패 시 권장 조치는?

A. 경고만 기록
B. 빌드 중단
C. 자동 수정
D. 무시하고 진행

<details>
<summary>정답 보기</summary>

**정답: B. 빌드 중단**

**설명:**
CI/CD 파이프라인에서 Critical/High 취약점 발견 시 빌드를 중단해야 합니다:
```bash
trivy image --exit-code 1 --severity HIGH,CRITICAL myimage:tag
```

`--exit-code 1`은 취약점 발견 시 0이 아닌 종료 코드를 반환하여 파이프라인을 실패시킵니다.

</details>

### 12. Alpine 베이스 이미지의 장점이 아닌 것은?

A. 작은 크기
B. 적은 취약점
C. glibc 호환성
D. 빠른 빌드

<details>
<summary>정답 보기</summary>

**정답: C. glibc 호환성**

**설명:**
Alpine Linux의 특징:
- 작은 크기 (~5MB)
- 최소 패키지
- musl libc 사용 (glibc 아님)

Alpine은 glibc 대신 musl libc를 사용하므로, glibc에 의존하는 일부 애플리케이션은 호환성 문제가 발생할 수 있습니다.

</details>
