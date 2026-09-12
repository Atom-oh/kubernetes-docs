# Feature Flags와 OpenFeature 퀴즈

1. OpenFeature의 Provider 모델의 핵심 장점은?
   - A) 특정 벤더에 종속되어 최적의 성능을 제공
   - B) 벤더 중립적인 평가 API로 백엔드 교체 시 코드 변경을 줄일 수 있음
   - C) 자체 Feature Flag 서버를 반드시 운영해야 함
   - D) REST API만 지원

<details>
<summary>정답 보기</summary>

**정답: B) 벤더 중립적인 평가 API로 백엔드 교체 시 코드 변경을 줄일 수 있음**

**설명:**
OpenFeature는 벤더 중립적인 SDK API로 백엔드 교체 시 평가 코드 변경을 줄입니다. 플래그 키·변형·타겟팅 규칙·컨텍스트 의미·인증·캐시와 이벤트 동작까지 자동으로 이관되는 것은 아니므로 별도 검증이 필요합니다.

</details>

---

2. flagd의 Kubernetes 배포 방식 중 Sidecar 모드와 Standalone 모드의 차이점은?
   - A) Sidecar는 성능이 좋고, Standalone은 관리가 쉬움
   - B) Sidecar는 앱 Pod 안에서 실행되고, Standalone은 공유 Service를 통해 평가를 제공
   - C) Sidecar는 TCP만 지원하고, Standalone은 HTTP만 지원
   - D) Sidecar는 CRD를 사용하고, Standalone은 ConfigMap만 사용

<details>
<summary>정답 보기</summary>

**정답: B) Sidecar는 앱 Pod 안에서 실행되고, Standalone은 공유 Service를 통해 평가를 제공**

**설명:**
RPC에서는 Sidecar에 로컬로 호출하거나 공유 Deployment의 Service에 네트워크로 호출할 수 있습니다. 실제 지연과 자원 사용량은 측정해야 합니다. Sidecar/공유 배포는 배포 위치의 선택이고 RPC/인프로세스는 평가 위치의 선택입니다. 인프로세스 방식은 규칙을 동기화해 앱 안에서 평가할 수 있습니다.

</details>

---

3. Feature Flag의 Evaluation Context에 포함되는 정보의 역할은?
   - A) 빌드 정보를 전달하여 컴파일 타임에 Flag를 결정
   - B) 사용자 ID, 리전, 환경 등의 컨텍스트로 타겟팅 규칙을 평가
   - C) 데이터베이스 연결 정보를 전달
   - D) Kubernetes 노드 정보를 전달

<details>
<summary>정답 보기</summary>

**정답: B) 사용자 ID, 리전, 환경 등의 컨텍스트로 타겟팅 규칙을 평가**

**설명:**
Evaluation Context는 Flag 평가 시 동적으로 전달되는 메타데이터입니다. 사용자 ID, 리전, 환경(dev/staging/prod), 사용자 그룹 등의 정보를 포함하며, 타겟팅 규칙에서 이 정보를 기반으로 특정 사용자나 그룹에게만 기능을 활성화할 수 있습니다. 요금제·권한에 영향을 주는 속성은 서버가 검증한 값을 사용하며, Feature Flag가 인증·인가를 대체하지는 않습니다.

</details>

---

4. Dark Launch 패턴에서 Feature Flag의 역할은?
   - A) 서비스를 완전히 숨기고 접근을 차단
   - B) 사용자에게 기존 결과를 반환하면서 새 로직을 부작용 없는 그림자 검증에 사용
   - C) 서버를 다크 모드로 전환
   - D) 야간에만 배포를 실행

<details>
<summary>정답 보기</summary>

**정답: B) 사용자에게 기존 결과를 반환하면서 새 로직을 부작용 없는 그림자 검증에 사용**

**설명:**
그림자 검증에서는 기존 결과를 반환하고 읽기 전용 계산이나 격리된 재생 환경에서 새 로직을 비교합니다. 결제·저장·알림을 두 번 실행하지 않습니다. 비동기 검증에는 동시 실행 한도와 독립된 타임아웃을 둡니다. 일부 사용자에게 새 결과를 실제로 보여주는 점진적 릴리스와 구분합니다.

</details>

---

5. Feature Flag as Code (GitOps)의 장점은?
   - A) GUI에서만 Flag를 관리할 수 있음
   - B) Flag 변경을 Git PR로 관리하여 리뷰, 감사, 롤백이 가능
   - C) Flag 평가 속도가 빨라짐
   - D) 서버 리소스를 절약

<details>
<summary>정답 보기</summary>

**정답: B) Flag 변경을 Git PR로 관리하여 리뷰, 감사, 롤백이 가능**

**설명:**
FeatureFlag CR을 Git에서 관리하면 PR 리뷰와 변경 이력, Git revert를 활용할 수 있습니다. 실제 반영에는 ArgoCD/Flux 조정, 소스 동기화와 SDK 상태 갱신이 필요합니다. 긴급 수동 패치는 self-heal이 되돌릴 수 있으므로 소유권과 조정 동작을 함께 고려해야 합니다.

</details>

---

6. Feature Flag의 기술 부채를 방지하기 위한 모범 사례는?
   - A) 모든 Flag를 영구적으로 유지
   - B) Flag에 만료일을 설정하고, 릴리스 완료 후 Flag 코드를 정리
   - C) Flag 수를 제한하지 않고 자유롭게 생성
   - D) Flag 이름에 날짜를 포함하지 않음

<details>
<summary>정답 보기</summary>

**정답: B) Flag에 만료일을 설정하고, 릴리스 완료 후 Flag 코드를 정리**

**설명:**
소유자와 검토일을 기록하고, 구버전 앱이나 다른 소비자가 해당 키를 쓰는지 확인한 뒤 코드와 설정을 정리합니다. 만료일 메타데이터가 자동 삭제를 의미하지는 않습니다. 영구 운영용 플래그는 삭제보다 정기 검토가 적절할 수 있습니다.

</details>

---

7. OpenFeature Operator가 Kubernetes에서 제공하는 핵심 기능은?
   - A) Pod에 자동으로 flagd 사이드카를 주입하고 FeatureFlag CRD를 관리
   - B) Kubernetes 클러스터의 보안을 감사
   - C) 컨테이너 이미지를 자동으로 빌드
   - D) HPA를 자동으로 구성

<details>
<summary>정답 보기</summary>

**정답: A) Pod에 자동으로 flagd 사이드카를 주입하고 FeatureFlag CRD를 관리**

**설명:**
Operator는 FeatureFlag와 FeatureFlagSource 등의 리소스를 관리합니다. Pod에서는 openfeature.dev/enabled와 openfeature.dev/featureflagsource 어노테이션으로 주입을 구성합니다. file 소스의 ConfigMap 볼륨, Kubernetes 직접 접근, proxy 등은 서로 다른 동기화 경로이며 SDK 호출은 앱 코드에 별도로 구현해야 합니다.

</details>

---

8. Flagger + Feature Flag 조합에서 메트릭 기반 자동 롤아웃의 동작 방식은?
   - A) Feature Flag가 직접 트래픽을 제어
   - B) Flagger가 Canary 트래픽을 전환하고, Feature Flag는 기능 레벨에서 점진적 노출을 제어
   - C) Feature Flag가 Flagger를 완전히 대체
   - D) 두 도구가 동일한 메트릭을 사용

<details>
<summary>정답 보기</summary>

**정답: B) Flagger가 Canary 트래픽을 전환하고, Feature Flag는 기능 레벨에서 점진적 노출을 제어**

**설명:**
Flagger는 워크로드 배포와 트래픽을, Feature Flag는 앱 동작을 제어합니다. 두 제어가 자동으로 하나의 트랜잭션이 되는 것은 아닙니다. 플래그 변경과 롤백까지 연결하려면 실제 웹훅이나 Git 변경 자동화, 권한과 실패 처리를 구현해야 합니다. 카나리 트래픽 비율과 사용자 코호트 비율도 같은 집합을 뜻하지 않습니다.

</details>
