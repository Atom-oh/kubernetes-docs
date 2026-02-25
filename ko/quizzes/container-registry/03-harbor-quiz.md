# Harbor 퀴즈
> **마지막 업데이트**: 2026년 2월 25일

1. Harbor의 CNCF(Cloud Native Computing Foundation) 프로젝트 상태는?
   - A) Sandbox 프로젝트
   - B) Incubating 프로젝트
   - C) Graduated 프로젝트
   - D) CNCF 프로젝트가 아님

<details>
<summary>정답 보기</summary>

**정답: C) Graduated 프로젝트**

**설명:**
Harbor는 2020년에 CNCF Graduated 프로젝트가 되었습니다. 이는 Harbor가 프로덕션 환경에서 널리 사용되고, 건강한 커뮤니티와 거버넌스 구조를 갖추고 있음을 의미합니다.

</details>

2. Harbor의 핵심 구성 요소가 아닌 것은?
   - A) Core (API 및 UI)
   - B) Registry (Docker Distribution)
   - C) Trivy (취약점 스캐너)
   - D) Prometheus (메트릭 수집)

<details>
<summary>정답 보기</summary>

**정답: D) Prometheus (메트릭 수집)**

**설명:**
Harbor의 핵심 구성 요소는 Core(웹 UI와 API), Registry(Docker Distribution 기반), Database(PostgreSQL), Redis, 그리고 선택적으로 Trivy(취약점 스캐너), Notary(이미지 서명) 등이 있습니다. Prometheus는 Harbor의 구성 요소가 아니라 외부 모니터링 도구입니다.

</details>

3. Helm을 사용하여 Harbor를 설치할 때 권장되는 방식은?
   - A) helm install harbor harbor/harbor --set expose.type=nodePort
   - B) helm install harbor harbor/harbor --set expose.type=ingress
   - C) helm install harbor harbor/harbor --set persistence.enabled=false
   - D) helm install harbor harbor/harbor --set database.external.enabled=true

<details>
<summary>정답 보기</summary>

**정답: B) helm install harbor harbor/harbor --set expose.type=ingress**

**설명:**
프로덕션 환경에서는 Ingress를 통해 Harbor를 노출하는 것이 권장됩니다. TLS 종료, 로드 밸런싱, 도메인 기반 라우팅 등을 Ingress Controller에서 처리할 수 있습니다. NodePort는 개발/테스트 환경에 적합합니다.

</details>

4. Harbor에서 Robot Account의 용도는?
   - A) 관리자 권한으로 모든 작업 수행
   - B) CI/CD 파이프라인 등 자동화 시스템의 인증
   - C) 사용자 계정 비밀번호 재설정
   - D) Harbor 시스템 업그레이드

<details>
<summary>정답 보기</summary>

**정답: B) CI/CD 파이프라인 등 자동화 시스템의 인증**

**설명:**
Robot Account는 CI/CD 파이프라인, 스크립트 등 자동화된 시스템에서 Harbor에 인증하기 위해 사용됩니다. 특정 프로젝트나 레포지토리에 대해 제한된 권한(push, pull 등)을 부여할 수 있으며, 만료 기간을 설정할 수 있습니다.

</details>

5. Harbor의 복제(Replication) 모드 중 "Pull-based" 복제의 특징은?
   - A) 소스 Harbor에서 대상 레지스트리로 이미지를 푸시
   - B) 대상 Harbor에서 소스 레지스트리의 이미지를 가져옴
   - C) 양방향으로 이미지를 동기화
   - D) 실시간으로 모든 이미지를 복제

<details>
<summary>정답 보기</summary>

**정답: B) 대상 Harbor에서 소스 레지스트리의 이미지를 가져옴**

**설명:**
Pull-based 복제에서는 대상(destination) Harbor가 소스 레지스트리(Harbor, Docker Hub, ECR 등)에서 이미지를 가져옵니다. 이는 소스 레지스트리에 Harbor가 설치되지 않은 경우나 에어갭 환경으로 이미지를 가져올 때 유용합니다.

</details>

6. Harbor에서 Trivy를 사용한 이미지 스캔 결과에 포함되지 않는 것은?
   - A) CVE (Common Vulnerabilities and Exposures) 목록
   - B) 취약점 심각도 (Critical, High, Medium, Low)
   - C) 수정 가능 버전 정보
   - D) 런타임 행위 분석 결과

<details>
<summary>정답 보기</summary>

**정답: D) 런타임 행위 분석 결과**

**설명:**
Trivy는 정적 취약점 스캐너로, 이미지의 OS 패키지와 애플리케이션 의존성에서 알려진 CVE를 탐지합니다. 런타임 행위 분석은 Falco 같은 런타임 보안 도구의 영역입니다.

</details>

7. Harbor에서 Cosign을 사용한 이미지 서명의 장점이 아닌 것은?
   - A) 이미지 무결성 검증
   - B) 이미지 출처(provenance) 확인
   - C) Notary v1 대비 간단한 키 관리
   - D) 서명된 이미지의 자동 취약점 패치

<details>
<summary>정답 보기</summary>

**정답: D) 서명된 이미지의 자동 취약점 패치**

**설명:**
Cosign을 통한 이미지 서명은 이미지의 무결성과 출처를 검증하는 데 사용됩니다. 이미지 서명 자체는 취약점 패치와 무관하며, 취약점 관리는 별도의 프로세스입니다.

</details>

8. 에어갭(Air-gap) 환경에 Harbor를 배포할 때 필요한 준비 작업은?
   - A) 인터넷 연결 필수
   - B) 필요한 이미지와 Helm 차트를 오프라인 번들로 준비
   - C) 클라우드 스토리지 연결
   - D) 외부 데이터베이스 서비스 필수

<details>
<summary>정답 보기</summary>

**정답: B) 필요한 이미지와 Helm 차트를 오프라인 번들로 준비**

**설명:**
에어갭 환경에서는 Harbor 설치에 필요한 컨테이너 이미지, Helm 차트, 의존성을 사전에 다운로드하여 오프라인으로 전달해야 합니다. Harbor 자체도 오프라인 설치 스크립트와 번들을 제공합니다.

</details>

9. Harbor의 Proxy Cache 기능의 주요 이점은?
   - A) 이미지 빌드 속도 향상
   - B) 외부 레지스트리의 레이트 리밋 완화 및 네트워크 트래픽 감소
   - C) 이미지 자동 업데이트
   - D) 멀티 아키텍처 이미지 자동 생성

<details>
<summary>정답 보기</summary>

**정답: B) 외부 레지스트리의 레이트 리밋 완화 및 네트워크 트래픽 감소**

**설명:**
Proxy Cache는 Docker Hub 등 외부 레지스트리의 이미지를 캐싱하여 반복 요청 시 로컬에서 제공합니다. 이를 통해 Docker Hub의 레이트 리밋 영향을 줄이고, 외부 네트워크 트래픽을 감소시키며, 이미지 풀 속도를 개선할 수 있습니다.

</details>

10. Harbor에서 Garbage Collection의 목적과 주의사항은?
    - A) 사용하지 않는 레포지토리 자동 삭제 / 주의사항 없음
    - B) 참조되지 않는 이미지 레이어 정리로 스토리지 회수 / 실행 중 Harbor 성능 저하 가능
    - C) 오래된 로그 파일 삭제 / 로그 손실 주의
    - D) 만료된 사용자 계정 삭제 / 계정 복구 불가

<details>
<summary>정답 보기</summary>

**정답: B) 참조되지 않는 이미지 레이어 정리로 스토리지 회수 / 실행 중 Harbor 성능 저하 가능**

**설명:**
Garbage Collection은 더 이상 어떤 이미지 매니페스트에서도 참조하지 않는 블롭(레이어)을 삭제하여 스토리지 공간을 회수합니다. GC 실행 중에는 I/O 부하가 증가하여 Harbor 성능이 저하될 수 있으므로, 사용량이 적은 시간대에 스케줄링하는 것이 권장됩니다.

</details>
