# Platform Engineering 개요 퀴즈

> 이 퀴즈는 [Platform Engineering 개요](../../platform-engineering/00-platform-engineering-overview.md) 문서의 학습 내용을 테스트합니다.

---

1. Platform Engineering의 핵심 목표는 무엇인가?
   - A) 모든 개발자가 인프라를 직접 관리하도록 교육하는 것
   - B) 개발자 셀프서비스를 위한 Internal Developer Platform(IDP)을 구축하는 것
   - C) 운영팀의 역할을 완전히 자동화로 대체하는 것
   - D) 모든 애플리케이션을 서버리스로 마이그레이션하는 것

<details>
<summary>정답 보기</summary>

**정답: B) 개발자 셀프서비스를 위한 Internal Developer Platform(IDP)을 구축하는 것**

**설명:**
Platform Engineering은 개발자가 인프라의 복잡성을 직접 다루지 않고도 애플리케이션을 빠르고 안전하게 배포할 수 있도록 IDP를 구축하는 분야입니다. 인프라 직접 관리를 교육하는 것이 아니라, 추상화된 셀프서비스 인터페이스를 제공하는 것이 핵심입니다.

</details>

---

2. AWS CAF 성숙도 모델에서 "IaC를 통한 인프라 자동화"와 "셀프서비스 제품 제공"이 해당하는 단계는?
   - A) START
   - B) ADVANCE
   - C) EXCEL
   - D) 모든 단계에 공통

<details>
<summary>정답 보기</summary>

**정답: B) ADVANCE**

**설명:**
AWS CAF 성숙도 모델에서 ADVANCE 단계는 자동화를 확대하고 중앙 관측성을 구축하는 단계입니다. 인프라 자동화(IaC, 셀프서비스 제품)는 START의 기반 위에 구축되는 ADVANCE 역량입니다. START는 기반 구축, EXCEL은 지속적 최적화에 해당합니다.

</details>

---

3. Platform Engineering, DevOps, SRE의 관계에 대한 설명으로 올바른 것은?
   - A) 세 가지는 상호 배타적인 접근법이다
   - B) Platform Engineering은 DevOps와 SRE를 대체한다
   - C) Platform Engineering은 DevOps 원칙과 SRE 관행을 제품으로 패키징한다
   - D) SRE가 Platform Engineering과 DevOps를 포함하는 상위 개념이다

<details>
<summary>정답 보기</summary>

**정답: C) Platform Engineering은 DevOps 원칙과 SRE 관행을 제품으로 패키징한다**

**설명:**
세 가지 접근법은 보완적입니다. DevOps는 문화와 방법론, SRE는 운영 엔지니어링 실천을 제공하며, Platform Engineering은 이들을 Internal Developer Platform이라는 제품으로 패키징합니다.

</details>

---

4. Kubernetes 기반 IDP 참조 아키텍처에서 ArgoCD, FluxCD, KRO가 위치하는 계층은?
   - A) 개발자 인터페이스 계층
   - B) 통합/오케스트레이션 계층
   - C) 리소스 계층
   - D) 인프라 계층

<details>
<summary>정답 보기</summary>

**정답: B) 통합/오케스트레이션 계층**

**설명:**
통합/오케스트레이션 계층은 선언적 상태 관리와 배포 자동화를 담당합니다. ArgoCD와 FluxCD는 GitOps 기반 배포를, KRO는 리소스 그래프 오케스트레이션을 제공합니다. 개발자 인터페이스 계층은 Backstage 같은 UI/CLI, 리소스 계층은 ACK/Helm/Operator, 인프라 계층은 EKS/VPC/IAM입니다.

</details>

---

5. Golden Path에 대한 설명으로 올바르지 않은 것은?
   - A) 플랫폼 팀이 제공하는 권장 배포 경로이다
   - B) 개발자가 반드시 따라야 하는 강제 규칙이다
   - C) 검증된 방법으로 빠르게 시작할 수 있도록 가이드한다
   - D) 필요시 벗어날 수 있지만 대부분의 경우 최적의 선택이다

<details>
<summary>정답 보기</summary>

**정답: B) 개발자가 반드시 따라야 하는 강제 규칙이다**

**설명:**
Golden Path는 "강제"가 아닌 "권장" 경로입니다. 플랫폼 팀이 검증하고 최적화한 배포 방법을 제공하지만, 개발자는 필요에 따라 다른 방법을 선택할 수 있습니다. 대부분의 사용 사례에서 Golden Path가 최적의 선택이 되도록 설계합니다.

</details>

---

6. KRO의 ResourceGraphDefinition(RGD)과 ACK를 결합한 셀프서비스 패턴에서, 개발자가 단일 매니페스트를 제출하면 자동으로 생성되는 리소스 조합으로 올바른 것은?
   - A) Deployment + ConfigMap + PVC
   - B) Deployment + Service + RDS 인스턴스 + IAM Role
   - C) StatefulSet + Service + DynamoDB 테이블
   - D) Pod + Ingress + S3 버킷

<details>
<summary>정답 보기</summary>

**정답: B) Deployment + Service + RDS 인스턴스 + IAM Role**

**설명:**
KRO RGD + ACK 셀프서비스 패턴에서 개발자의 단일 WebApplication 매니페스트를 통해 KRO가 Kubernetes 네이티브 리소스(Deployment + Service)와 ACK를 통한 AWS 리소스(RDS 인스턴스, IAM Role)를 자동 생성합니다. 이것이 IDP의 핵심 가치인 인프라 복잡성의 추상화입니다.

</details>

---

7. DORA 메트릭이 AWS CAF 성숙도 모델에서 해당하는 단계와 역량 영역은?
   - A) START - 비용 관리
   - B) ADVANCE - 중앙 관측성
   - C) EXCEL - 플랫폼 메트릭
   - D) 모든 단계에 공통

<details>
<summary>정답 보기</summary>

**정답: C) EXCEL - 플랫폼 메트릭**

**설명:**
DORA 메트릭(배포 빈도, 리드 타임, MTTR, 변경 실패율)은 EXCEL 단계의 "플랫폼 메트릭" 역량에 해당합니다. 이는 조직 목표와 정렬된 메트릭을 통해 지속적 최적화를 달성하는 가장 높은 성숙도 수준입니다.

</details>

---

8. IDP의 핵심 가치 중, 보안과 규정 준수를 기본으로 내장하여 개발자가 별도의 보안 설정 없이도 안전한 환경에서 작업할 수 있게 하는 것은?
   - A) 셀프서비스
   - B) 가드레일
   - C) 표준화
   - D) 자동화

<details>
<summary>정답 보기</summary>

**정답: B) 가드레일**

**설명:**
가드레일은 보안과 규정 준수를 플랫폼에 기본으로 내장하는 것입니다. 개발자가 명시적으로 보안을 설정하지 않아도 플랫폼이 자동으로 보안 정책(Pod Security Standards, 네트워크 정책, 이미지 스캔 등)을 적용합니다. 셀프서비스는 직접 프로비저닝, 표준화는 Golden Path, 자동화는 반복 작업 제거에 관한 가치입니다.

</details>
