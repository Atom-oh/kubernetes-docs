# Unified Studio Domain과 Project 거버넌스 퀴즈

## 객관식 문제

1. Project profile에 대한 설명으로 맞는 것은 무엇인가요?

   - A) GPU driver 버전만 정한다
   - B) Blueprint를 묶고 생성 시 또는 on-demand 도구 준비를 구성한다
   - C) 이름이 All capabilities이면 모든 도구가 즉시 준비된다
   - D) 사용자의 모든 IAM 권한을 대체한다

<details>
<summary>정답 보기</summary>

**정답: B**

의도한 profile ID, domain 유형, 필요한 blueprint/account/region을 확인합니다.

</details>

2. IAM DeleteProject 허용과 일반 contributor membership만으로 삭제가 보장되나요?

   - A) 언제나 보장된다
   - B) 아니요. 삭제 경로의 owner/admin 권한과 다른 IAM·서비스 정책도 확인해야 한다
   - C) EKS namespace가 같으면 보장된다
   - D) Project 이름이 고유하면 보장된다

<details>
<summary>정답 보기</summary>

**정답: B**

Project ownership, API authorization과 실제 데이터/resource 권한은 서로 다른 경계입니다.

</details>

3. projectStatus=ACTIVE의 올바른 해석은 무엇인가요?

   - A) 모든 environment와 GPU 도구가 준비되었다
   - B) Project 상태이며 필요한 environmentDeploymentDetails와 도구 접근은 별도 확인한다
   - C) 모든 on-demand capability가 이미 provision되었다
   - D) 학습이 성공했다

<details>
<summary>정답 보기</summary>

**정답: B**

의도적으로 미생성인 on-demand 도구와 실제 실패를 구분합니다.

</details>

4. CreateProject membershipAssignments의 member에는 어떤 값을 넣나요?

   - A) userIdentifier와 groupIdentifier를 항상 둘 다 넣는다
   - B) 의도한 profile에 맞는 userIdentifier 또는 groupIdentifier 하나만 넣는다
   - C) IAM secret access key를 넣는다
   - D) 아무 IAM role ARN을 group ID 대신 넣으면 된다

<details>
<summary>정답 보기</summary>

**정답: B**

Tagged union입니다. 같은 요청의 assignment도 전체 environment provision의 원자적 rollback을 보장하지 않으므로 결과를 확인합니다.

</details>

5. 잔존 project 삭제를 확인하는 올바른 방법은 무엇인가요?

   - A) AccessDenied이면 없는 것으로 판단한다
   - B) 권한·domain·filter·pagination을 확인한 get/list 결과와 소유 자원 inventory를 대조한다
   - C) 9월 초 기록이 현재 상태도 증명한다
   - D) Tag 오류가 나면 같은 prefix의 공유 bucket과 role을 모두 삭제한다

<details>
<summary>정답 보기</summary>

**정답: B**

과거 기록은 현재 조회를 대신하지 않습니다. 정리는 이번 실행의 소유 자원과 보존 정책에 맞게 수행합니다.

</details>

---

[학습 자료로 돌아가기](../../../data-on-eks/sagemaker-unified-studio/01-domains-projects-governance.md)
