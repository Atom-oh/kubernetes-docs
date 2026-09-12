# Tekton Pipelines 퀴즈

1. Task, TaskRun, Workspace의 관계를 올바르게 설명한 것은?
   - A) Task 정의 자체가 실행 중인 Pod이다
   - B) TaskRun이 Task를 실행하며 Workspace는 volume 바인딩 필드이다
   - C) Workspace는 항상 독립 CRD이다
   - D) 같은 Pod의 Step은 서로 완전히 격리된다

<details>
<summary>정답 보기</summary>

**정답: B) TaskRun이 Task를 실행하며 Workspace는 volume 바인딩 필드이다**

Task/Pipeline은 정의, Run은 실행 인스턴스입니다. 같은 Pod의 Step은 네트워크와 volume을 공유하므로 상호 불신 코드의 보안 경계가 아닙니다.

</details>

---

2. 서로 다른 TaskRun 사이에서 소스를 공유할 때 맞는 설명은?
   - A) emptyDir가 다른 Pod에도 같은 파일을 제공한다
   - B) 실행별 PVC를 사용할 수 있으며 RWO/RWX 자체는 신뢰 경계가 아니다
   - C) 같은 PVC에 subPath만 다르면 외부 PR과 release를 안전하게 공유할 수 있다
   - D) Result는 항상 무제한 문자열이다

<details>
<summary>정답 보기</summary>

**정답: B) 실행별 PVC를 사용할 수 있으며 RWO/RWX 자체는 신뢰 경계가 아니다**

volumeClaimTemplate으로 실행별 PVC를 만들고 신뢰 수준이 다른 실행과 writable 저장소를 공유하지 않습니다. 작은 값은 Result, 큰 보고서는 아티팩트 저장소를 사용합니다.

</details>

---

3. GitHub HMAC 검증을 통과한 외부 PR을 처리할 때 올바른 것은?
   - A) release와 같은 IRSA·서명 권한을 사용한다
   - B) 별도 신뢰 수준의 실행 환경과 제한된 권한으로 처리한다
   - C) HMAC이 있으므로 PR의 셸 명령을 script에 그대로 삽입한다
   - D) 검증된 요청은 항상 main push이다

<details>
<summary>정답 보기</summary>

**정답: B) 별도 신뢰 수준의 실행 환경과 제한된 권한으로 처리한다**

HMAC은 전달 출처를 확인할 뿐 코드에 배포 권한을 부여하지 않습니다. 본문의 privileged CI 경로는 승인 저장소의 보호된 main push만 대상으로 합니다.

</details>

---

4. Chains의 slsa/v1 formatter는 어떤 provenance 버전인가?
   - A) SLSA provenance v1.0
   - B) SLSA provenance v0.2이며 v1.0은 slsa/v2alpha3 또는 slsa/v2alpha4 사용
   - C) 어떤 버전이든 서명 키가 자동 결정
   - D) Kubernetes v1 API 버전과 항상 같음

<details>
<summary>정답 보기</summary>

**정답: B) SLSA provenance v0.2이며 v1.0은 slsa/v2alpha3 또는 slsa/v2alpha4 사용**

formatter 이름과 SLSA 명세 버전은 다릅니다. Pipeline-level provenance는 Pipeline 종료 후 만들어지며 별도 검증·승격 절차가 필요합니다.

</details>

---

5. finally Task에 대해 맞는 설명은?
   - A) 어떤 오류·취소·timeout에서도 반드시 실행된다
   - B) 일반 Task 종료 후 실행하지만 누락 Result·취소·timeout 등으로 skip되거나 실행되지 못할 수 있다
   - C) 항상 선언 순서대로 하나씩 실행된다
   - D) 없는 이미지 Result도 자동 기본값을 제공한다

<details>
<summary>정답 보기</summary>

**정답: B) 일반 Task 종료 후 실행하지만 누락 Result·취소·timeout 등으로 skip되거나 실행되지 못할 수 있다**

본문의 최종 리포트는 run 이름과 tasks.status만 참조합니다. 여러 finally Task의 순서를 가정하지 않으며 별도 timeout도 확인합니다.

</details>

---

6. CI 성공과 chains.tekton.dev/signed=true를 확인한 뒤 무엇이 필요한가?
   - A) 즉시 임의 태그를 production에 배포
   - B) 신뢰된 키·digest·builder·소스 provenance를 검증하고 GitOps 변경을 리뷰
   - C) 서명 JSON 내용을 검증 없이 base64 decode만 수행
   - D) ArgoCD가 애플리케이션 이미지를 직접 pull하는지 확인

<details>
<summary>정답 보기</summary>

**정답: B) 신뢰된 키·digest·builder·소스 provenance를 검증하고 GitOps 변경을 리뷰**

signed annotation은 암호학적 검증이나 승인 자체가 아닙니다. ArgoCD는 manifest를 동기화하고 실제 image pull은 kubelet/runtime이 담당합니다.

</details>

---

7. Pipelines 1.16의 controller ServiceMonitor에서 확인할 포트와 counter는?
   - A) metrics / pipelinerun_count
   - B) http-metrics / tekton_pipelines_controller_pipelinerun_total
   - C) http / 모든 namespace별 counter가 자동 제공
   - D) 9097 / running duration histogram

<details>
<summary>정답 보기</summary>

**정답: B) http-metrics / tekton_pipelines_controller_pipelinerun_total**

실제 Service label·포트와 Prometheus selector를 맞춰야 합니다. 현재 완료 counter는 status만 가지며 namespace를 임의로 붙여 조회할 수 없습니다.

</details>

---

8. coschedule=workspaces에서 volumeClaimTemplate PVC의 완료 후 기본 동작은?
   - A) 항상 즉시 삭제
   - B) 유지하며 정확한 true 값의 auto-cleanup annotation으로 완료 시 정리를 선택할 수 있다
   - C) 기존 사용자가 지정한 PVC도 무조건 삭제
   - D) PipelineRun은 기본 7일 TTL 후 삭제

<details>
<summary>정답 보기</summary>

**정답: B) 유지하며 정확한 true 값의 auto-cleanup annotation으로 완료 시 정리를 선택할 수 있다**

다른 coschedule 모드와 기존 PVC의 생명 주기는 다릅니다. 실행 기록 삭제 전에는 완료 시각·보관 정책·로그/서명 아카이브를 확인해야 합니다.

</details>
