# Crossplane 퀴즈

1. Crossplane의 Composition이 해결하는 핵심 문제는?
   - A) Kubernetes 클러스터의 네트워킹 구성
   - B) 여러 인프라 리소스를 하나의 추상화된 API로 묶어 셀프서비스 제공
   - C) 컨테이너 이미지 빌드 자동화
   - D) Pod의 리소스 요청 최적화

<details>
<summary>정답 보기</summary>

**정답: B) 여러 인프라 리소스를 하나의 추상화된 API로 묶어 셀프서비스 제공**

**설명:**
Composition은 RDS 인스턴스, SecurityGroup, SubnetGroup 등 여러 Managed Resource를 하나의 Composite Resource(XR)로 패키징합니다. 개발자는 복잡한 인프라 세부사항을 알 필요 없이, 간단한 Claim으로 필요한 인프라를 프로비저닝할 수 있습니다.

</details>

---

2. Crossplane의 Claim(XC)과 Composite Resource(XR)의 관계는?
   - A) Claim은 클러스터 범위이고, XR은 네임스페이스 범위
   - B) Claim은 네임스페이스 범위의 요청이고, XR은 클러스터 범위의 실제 리소스
   - C) Claim과 XR은 동일한 리소스
   - D) XR은 Claim의 백업 복사본

<details>
<summary>정답 보기</summary>

**정답: B) Claim은 네임스페이스 범위의 요청이고, XR은 클러스터 범위의 실제 리소스**

**설명:**
Claim(XC)은 네임스페이스 범위로, 개발자가 필요한 인프라를 요청하는 인터페이스입니다. Claim이 생성되면 대응하는 Composite Resource(XR)가 클러스터 범위에 생성되고, XR이 Composition에 따라 실제 Managed Resource들을 프로비저닝합니다.

</details>

---

3. Crossplane에서 AWS 리소스를 관리할 때 IRSA(IAM Roles for Service Accounts)를 사용하는 이유는?
   - A) Crossplane 라이선스 비용을 줄이기 위해
   - B) AWS 자격 증명을 Pod에 안전하게 전달하고, 최소 권한 원칙을 적용하기 위해
   - C) Crossplane의 성능을 향상시키기 위해
   - D) 멀티 클러스터 지원을 위해

<details>
<summary>정답 보기</summary>

**정답: B) AWS 자격 증명을 Pod에 안전하게 전달하고, 최소 권한 원칙을 적용하기 위해**

**설명:**
IRSA를 사용하면 AWS Access Key를 직접 관리하지 않고, Kubernetes ServiceAccount에 IAM Role을 연결하여 임시 자격 증명을 자동으로 주입합니다. 이를 통해 보안을 강화하고, Provider별로 필요한 최소한의 IAM 권한만 부여할 수 있습니다.

</details>

---

4. Terraform과 Crossplane의 가장 큰 아키텍처적 차이점은?
   - A) Terraform은 YAML을 사용하고, Crossplane은 HCL을 사용
   - B) Terraform은 명령형 실행(apply/destroy)이고, Crossplane은 Kubernetes 컨트롤러로 지속적 조정(reconciliation)
   - C) Terraform은 클라우드만 지원하고, Crossplane은 온프레미스만 지원
   - D) Terraform은 무료이고, Crossplane은 유료

<details>
<summary>정답 보기</summary>

**정답: B) Terraform은 명령형 실행(apply/destroy)이고, Crossplane은 Kubernetes 컨트롤러로 지속적 조정(reconciliation)**

**설명:**
Terraform은 `terraform apply`/`destroy` 명령으로 실행하는 워크플로우 기반 도구입니다. Crossplane은 Kubernetes 컨트롤러 패턴으로 동작하여, 선언된 상태와 실제 상태를 지속적으로 비교하고 조정(reconcile)합니다. 이를 통해 드리프트를 자동으로 감지하고 수정합니다.

</details>

---

5. ACK(AWS Controllers for Kubernetes)와 Crossplane을 함께 사용하는 시나리오는?
   - A) ACK와 Crossplane은 호환되지 않으므로 하나만 사용
   - B) ACK로 단순 AWS 리소스를 관리하고, Crossplane Composition으로 복잡한 멀티 리소스 패키지를 추상화
   - C) ACK는 개발 환경, Crossplane은 프로덕션 환경에서만 사용
   - D) ACK는 네트워킹, Crossplane은 스토리지만 관리

<details>
<summary>정답 보기</summary>

**정답: B) ACK로 단순 AWS 리소스를 관리하고, Crossplane Composition으로 복잡한 멀티 리소스 패키지를 추상화**

**설명:**
ACK는 AWS API와 1:1 매핑되는 단순한 리소스 관리에 적합하고, Crossplane은 Composition을 통해 여러 리소스를 하나의 추상화된 API로 패키징하는 데 강점이 있습니다. 간단한 S3 버킷은 ACK로, RDS+SecurityGroup+SubnetGroup 패키지는 Crossplane Composition으로 관리할 수 있습니다.

</details>

---

6. Crossplane의 Connection Details가 중요한 이유는?
   - A) 네트워크 연결 상태를 모니터링
   - B) 프로비저닝된 리소스의 접속 정보(엔드포인트, 비밀번호 등)를 Kubernetes Secret으로 자동 생성
   - C) Crossplane Provider 간의 연결을 관리
   - D) 멀티 클러스터 간의 네트워크 연결을 구성

<details>
<summary>정답 보기</summary>

**정답: B) 프로비저닝된 리소스의 접속 정보(엔드포인트, 비밀번호 등)를 Kubernetes Secret으로 자동 생성**

**설명:**
Connection Details는 Crossplane이 프로비저닝한 리소스의 접속 정보(데이터베이스 엔드포인트, 포트, 사용자명, 비밀번호 등)를 자동으로 Kubernetes Secret에 저장하는 기능입니다. 애플리케이션은 이 Secret을 마운트하여 프로비저닝된 인프라에 연결할 수 있습니다.

</details>

---

7. Backstage + Crossplane 통합에서 개발자 셀프서비스 워크플로우의 순서는?
   - A) ArgoCD 배포 → Backstage 카탈로그 등록 → Crossplane Claim 생성
   - B) Backstage Template에서 Crossplane Claim YAML 생성 → Git Push → ArgoCD 동기화 → Crossplane 프로비저닝
   - C) Crossplane 프로비저닝 → Backstage Template 생성 → Git Push
   - D) Git Push → Backstage 카탈로그 등록 → ArgoCD 배포

<details>
<summary>정답 보기</summary>

**정답: B) Backstage Template에서 Crossplane Claim YAML 생성 → Git Push → ArgoCD 동기화 → Crossplane 프로비저닝**

**설명:**
개발자가 Backstage Template에서 파라미터(DB 크기, 환경 등)를 입력하면, Template이 Crossplane Claim YAML을 생성하고 Git 리포지토리에 Push합니다. ArgoCD가 변경을 감지하여 클러스터에 동기화하면, Crossplane이 Claim을 처리하여 실제 인프라를 프로비저닝합니다.

</details>

---

8. Crossplane의 드리프트 감지(Drift Detection)가 Terraform 대비 우수한 점은?
   - A) Terraform이 드리프트 감지를 지원하지 않음
   - B) Crossplane은 컨트롤러가 지속적으로 실제 상태를 감시하여 자동 수정하고, Terraform은 수동 `plan`/`apply` 필요
   - C) Crossplane이 더 빠른 속도로 프로비저닝
   - D) Crossplane이 더 많은 클라우드를 지원

<details>
<summary>정답 보기</summary>

**정답: B) Crossplane은 컨트롤러가 지속적으로 실제 상태를 감시하여 자동 수정하고, Terraform은 수동 `plan`/`apply` 필요**

**설명:**
Crossplane의 컨트롤러는 주기적으로 실제 클라우드 리소스 상태를 확인하고, 선언된 상태와 차이가 있으면 자동으로 수정합니다. Terraform은 `terraform plan`을 수동으로 실행해야 드리프트를 감지할 수 있으며, 수정도 `terraform apply`를 실행해야 합니다.

</details>
