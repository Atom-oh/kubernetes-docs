# Unified Studio Domain과 Project 거버넌스 퀴즈

## 객관식 문제

1. Project profile은 무엇인가요?
   - A) GPU driver
   - B) blueprint 모음으로 구성된 project 템플릿
   - C) MLflow run
   - D) S3 object version

<details>
<summary>정답 보기</summary>

**정답: B**

Project profile은 project가 사용할 도구와 capability 구성을 정의합니다.
</details>

2. IAM `DeleteProject` 권한만 있으면 충분한가요?
   - A) 예
   - B) 아니요, 해당 project의 owner/member authorization도 필요
   - C) EKS cluster가 있으면 충분
   - D) S3 tag가 있으면 충분

<details>
<summary>정답 보기</summary>

**정답: B**

IAM 호출 권한과 Unified Studio/DataZone membership은 별도 계층입니다.
</details>

3. `All capabilities` 이름에 대한 안전한 해석은 무엇인가요?
   - A) 모든 blueprint가 모든 리전에 즉시 준비됨
   - B) profile enablement와 필요한 blueprint/region readiness를 별도 확인
   - C) 누구나 project 생성 가능
   - D) 강한 보안 격리를 자동 제공

<details>
<summary>정답 보기</summary>

**정답: B**

이름만으로 readiness와 authorization을 가정하면 안 됩니다.
</details>

4. custom project tag가 거부되면 어떻게 해야 하나요?
   - A) GPU Job을 먼저 시작
   - B) project 요청을 수정하고 이미 생성한 자원을 정리
   - C) 모든 tag를 IAM role에 복사
   - D) 잔존 자원을 무시

<details>
<summary>정답 보기</summary>

**정답: B**

부분 생성된 App·S3·IAM을 inventory 기반으로 teardown합니다.
</details>

5. Project 삭제 완료의 증거는 무엇인가요?
   - A) delete API가 한 번 성공
   - B) `ListProjects`에서 사라지고 전체 inventory가 0
   - C) `GetProject` authorization 오류
   - D) MLflow UI가 닫힘

<details>
<summary>정답 보기</summary>

**정답: B**

권한 오류를 부재로 해석하지 말고 list와 전체 자원 검사를 사용합니다.
</details>

---

[학습 자료로 돌아가기](../../../data-on-eks/sagemaker-unified-studio/01-domains-projects-governance.md)
