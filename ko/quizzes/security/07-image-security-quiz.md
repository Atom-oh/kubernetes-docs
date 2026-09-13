<span id="퀴즈-문제"></span>

# 컨테이너 이미지 보안 퀴즈
> **마지막 업데이트**: 2026년 9월 13일

<span id="_1-trivy로-컨테이너-이미지를-스캔하는-올바른-명령은"></span>

### 1. 주어진 이미지 reference를 Trivy로 검사하는 명령은?

A. trivy scan "$IMAGE_REF"
B. trivy image "$IMAGE_REF"
C. trivy container "$IMAGE_REF"
D. trivy check "$IMAGE_REF"

<details>
<summary>정답 보기</summary>

**정답: B. trivy image "$IMAGE_REF"**

trivy image가 이미지 검사 명령입니다. IMAGE_REF에는 실제 digest reference를 넣습니다. 명령 구문이 유효해도 registry 권한·DB 갱신·지원 package 탐지 여부를 확인해야 합니다.

</details>

<span id="_2-이미지-서명-및-검증에-사용되는-도구는"></span>

### 2. 이미지 digest와 승인된 서명자의 연결을 검증하는 도구는?

A. Trivy의 CVE DB
B. Cosign/Sigstore
C. Clair의 package scanner
D. Docker imagePullPolicy

<details>
<summary>정답 보기</summary>

**정답: B. Cosign/Sigstore**

Cosign은 key 또는 OIDC identity/issuer와 digest 및 필요한 transparency 증거를 검증합니다. 서명은 알려진 취약점이 없다는 보증이 아닙니다.

</details>

<span id="_3-shift-left-보안-접근-방식의-의미는"></span>

### 3. Shift-left 보안은 무엇을 의미하는가?

A. 운영 단계까지 검사를 미룸
B. 개발·PR·빌드 단계에서 문제를 일찍 검사
C. 보안팀만 소스에 접근
D. 운영 재검사를 제거

<details>
<summary>정답 보기</summary>

**정답: B. 개발·PR·빌드 단계에서 문제를 일찍 검사**

개발 초기 검사는 수정 피드백을 앞당깁니다. 배포 후 새 CVE와 런타임 행위가 생기므로 registry 재검사와 런타임 탐지는 계속 필요합니다.

</details>

<span id="_4-distroless-이미지의-주요-특징은"></span>

### 4. 일반적인 distroless runtime 이미지의 특징은?

A. 모든 Linux 도구를 포함
B. 애플리케이션에 필요한 최소 runtime 구성요소 중심
C. 항상 shell과 debugger를 포함
D. package manager가 필수

<details>
<summary>정답 보기</summary>

**정답: B. 애플리케이션에 필요한 최소 runtime 구성요소 중심**

일반 runtime에는 shell/package manager가 없으며 debug variant는 다를 수 있습니다. 작은 base image에도 애플리케이션 binary·library 취약점은 남을 수 있습니다.

</details>

<span id="_5-amazon-ecr-이미지-스캐닝의-두-가지-유형은"></span>

### 5. 현재 ECR Basic과 Enhanced scanning의 차이는?

A. Basic은 AWS native OS scanner, Enhanced는 Inspector의 OS/언어 package 검사
B. Basic은 항상 Clair, Enhanced는 OS만 검사
C. 두 방식 모두 push를 자동 거부
D. Enhanced는 모든 이미지를 무기한 검사

<details>
<summary>정답 보기</summary>

**정답: A. Basic은 AWS native OS scanner, Enhanced는 Inspector의 OS/언어 package 검사**

Basic은 manual/scan-on-push, Enhanced는 scan-on-push/continuous를 지원합니다. 결과의 findings와 enhancedFindings 및 ECR/Inspector 이벤트를 구분합니다.

</details>

<span id="_6-sbom-software-bill-of-materials-이란"></span>

### 6. SBOM은 무엇을 제공하는가?

A. 취약점이 없다는 인증
B. 도구가 발견한 소프트웨어 구성요소 inventory
C. 승인된 signer의 자동 증명
D. 배포 권한

<details>
<summary>정답 보기</summary>

**정답: B. 도구가 발견한 소프트웨어 구성요소 inventory**

SBOM은 구성요소와 관계를 기록하지만 탐지 범위가 불완전할 수 있습니다. digest에 연결한 서명된 attestation과 검증 policy를 별도로 평가합니다.

</details>

<span id="_7-kyverno에서-이미지-서명을-검증하는-정책-유형은"></span>

### 7. 기존 Kyverno ClusterPolicy에서 이미지 서명 검사에 사용한 규칙은?

A. validate만
B. mutate만
C. verifyImages
D. generate만

<details>
<summary>정답 보기</summary>

**정답: C. verifyImages**

기존 verifyImages와 신규 ImageValidatingPolicy를 구분합니다. Kyverno1.19.1의 신규 예제는 CEL policy를 사용하며 registry/digest 제한과 일반·init·ephemeral container 범위를 함께 검사합니다.

</details>

<span id="_8-이미지-태그-대신-다이제스트를-사용해야-하는-이유는"></span>

### 8. 이미지 tag 대신 digest를 고정하는 이유는?

A. 항상 짧아짐
B. 특정 image content를 식별
C. 서명 검사가 자동 수행됨
D. CVE가 자동 제거됨

<details>
<summary>정답 보기</summary>

**정답: B. 특정 image content를 식별**

Tag는 이동할 수 있지만 digest는 내용을 식별합니다. 재현 가능한 artifact 선택에 도움이 되며 signer 신뢰·취약점·가용성 검증을 대신하지 않습니다.

</details>

<span id="_9-trivy가-스캔하지-않는-대상은"></span>

### 9. Trivy의 정적 검사와 별도인 영역은?

A. OS package 식별
B. 언어 dependency 검사
C. 실행 중 syscall·process 행위 탐지
D. 소스 시크릿 탐지

<details>
<summary>정답 보기</summary>

**정답: C. 실행 중 syscall·process 행위 탐지**

Trivy의 package·misconfiguration·secret 검사는 런타임 행위 탐지와 다릅니다. Falco 같은 런타임 도구의 역할을 별도로 설계합니다.

</details>

<span id="_10-컨테이너-이미지-레지스트리-보안-모범-사례가-아닌-것은"></span>

### 10. 레지스트리 접근 통제로 부적절한 것은?

A. Private image의 승인된 pull identity
B. 공개 image도 digest·서명 검증
C. 익명 사용자의 임의 image push/delete 허용
D. Registry·admission·scan gate의 권한 분리

<details>
<summary>정답 보기</summary>

**정답: C. 익명 사용자의 임의 image push/delete 허용**

공개 배포용 image의 anonymous read 자체를 모두 취약점으로 간주하지 않습니다. 기밀성, write/delete 권한, 출처 검증, rate limit을 각각 통제합니다.

</details>

<span id="_11-ci-cd-파이프라인에서-이미지-스캐닝-실패-시-권장-조치는"></span>

### 11. 사전에 정한 CI scan gate를 통과하지 못하면 어떻게 처리하는가?

A. 무조건 무시
B. Publish/sign 단계로 진행하지 않고 실패 원인을 확인
C. 다른 이미지를 재빌드해 검사 없이 push
D. exit code만0으로 바꿈

<details>
<summary>정답 보기</summary>

**정답: B. Publish/sign 단계로 진행하지 않고 실패 원인을 확인**

정책 위반과 scanner/DB/권한 오류를 구분하고 결과를 보존합니다. 검사 후 다시 빌드한 다른 artifact를 배포하지 않습니다. Severity 예외는 근거·소유자·만료일을 정합니다.

</details>

<span id="_12-alpine-베이스-이미지의-장점이-아닌-것은"></span>

### 12. Alpine에 대해 잘못된 가정은?

A. musl libc 기반
B. apk package manager 사용
C. glibc 의존 애플리케이션과 항상 완전 호환
D. 선택한 release의 지원기간 확인 필요

<details>
<summary>정답 보기</summary>

**정답: C. glibc 의존 애플리케이션과 항상 완전 호환**

Alpine은 musl을 사용하므로 glibc 의존 binary와 호환성 차이가 있습니다. 이미지 크기만으로 취약점 수나 build 속도를 보장하지 않습니다.

</details>
