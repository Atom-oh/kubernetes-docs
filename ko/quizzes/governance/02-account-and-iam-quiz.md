# Account 구성과 IAM 경계 퀴즈

> 이 퀴즈는 [Account 구성과 IAM 경계](../../governance/02-account-and-iam.md) 문서의 학습 내용을 테스트합니다.

---

1. Identity Center의100group 한도가 적용되는 범위는?
   - A) 전체 조직의 group
   - B) Account 전체의 모든 group
   - C) 한 Account의 한 Permission Set 또는 한 application에 할당된 group
   - D) 동시 로그인 사용자

<details>
<summary>정답 보기</summary>

**정답: C) 한 Account의 한 Permission Set 또는 한 application에 할당된 group**

**설명:**
Permission Set–Account 조합별 한도입니다. 서로 다른 Permission Set의 group을 합산한 Account 전체 상한이 아니며 ABAC를 무조건 강제하지 않습니다.

</details>

---

2. Shared VPC를 사용하는 Account의 분사를 계획할 때 맞는 설명은?
   - A) 기존 resource가 즉시 전부 삭제됨
   - B) 동일 Organization 요건과 공유 해제 후 생성·교체 제한을 고려해 network 이전을 준비함
   - C) RAM subnet은 외부 조직에도 그대로 공유 가능
   - D) EKS가 자동으로 다른 VPC로 이동함

<details>
<summary>정답 보기</summary>

**정답: B) 동일 Organization 요건과 공유 해제 후 생성·교체 제한을 고려해 network 이전을 준비함**

**설명:**
공유 해제 후 기존 resource는 실행될 수 있지만 새 생성과 managed-service scaling/replacement가 영향을 받습니다. 장기 운영 가능한 독립 경로를 이탈 전에 설계합니다.

</details>

---

3. Shared Cluster에서 다른 Account의 AWS resource를 접근하는 방법은?
   - A) 항상 IAM user key 필요
   - B) Target-role chaining, 지원 resource policy 또는 IRSA 등 요구에 맞는 경로 선택
   - C) 모든 workload에 반드시2개씩 role 생성
   - D) aws-auth만 수정하면 AWS 권한 부여됨

<details>
<summary>정답 보기</summary>

**정답: B) Target-role chaining, 지원 resource policy 또는 IRSA 등 요구에 맞는 경로 선택**

**설명:**
Pod Identity 기본 role의 같은 Account 제약은 모든 요청에 target role을 강제하지 않습니다. EKS를 생성한 Cluster Account와 DB만 소유한 Workload Account도 구분합니다.

</details>

---

4. Access Policy와 Kubernetes RBAC를 함께 쓰면?
   - A) 마지막 설정만 적용
   - B) 허용 권한이 합쳐지고 한쪽으로 다른 쪽을 제한할 수 없음
   - C) 동시 사용 불가
   - D) RBAC가 항상 덮어씀

<details>
<summary>정답 보기</summary>

**정답: B) 허용 권한이 합쳐지고 한쪽으로 다른 쪽을 제한할 수 없음**

**설명:**
의도된 grant와 중복 권한을 검토합니다. 자동 검사는 유용하지만 API 사용의 필수 조건은 아닙니다.

</details>
