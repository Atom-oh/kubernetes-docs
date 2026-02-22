# ArgoCD ApplicationSets 퀴즈

이 퀴즈는 템플릿 기반 애플리케이션 생성을 위한 ArgoCD ApplicationSets에 대한 이해도를 테스트합니다.

1. ApplicationSet의 주요 목적은 무엇인가요?
   - A) 기존 Applications 그룹화
   - B) 템플릿에서 여러 Applications 자동 생성
   - C) 애플리케이션 백업 생성
   - D) 애플리케이션 시크릿 관리

<details>
<summary>정답 보기</summary>

**정답: B) 템플릿에서 여러 Applications 자동 생성**

**설명:**
ApplicationSets는 generators와 templates를 사용하여 여러 ArgoCD Applications를 자동으로 생성하고 관리합니다. 여러 클러스터나 환경에 애플리케이션을 배포하는 데 이상적입니다.

</details>

2. ArgoCD에 등록된 각 클러스터에 대해 Applications를 생성하려면 어떤 generator를 사용해야 하나요?
   - A) Git generator
   - B) List generator
   - C) Cluster generator
   - D) Matrix generator

<details>
<summary>정답 보기</summary>

**정답: C) Cluster generator**

**설명:**
Cluster generator는 ArgoCD에 등록된 각 클러스터에 대해 자동으로 Applications를 생성합니다. 레이블 선택기를 사용하여 특정 클러스터를 대상으로 할 수 있습니다.

</details>

3. Git directory generator는 무엇을 하나요?
   - A) Git 브랜치를 기반으로 Applications 생성
   - B) 지정된 경로의 각 디렉토리에 대해 Applications 생성
   - C) Git 자격 증명 동기화
   - D) Git 웹훅 관리

<details>
<summary>정답 보기</summary>

**정답: B) 지정된 경로의 각 디렉토리에 대해 Applications 생성**

**설명:**
Git directory generator는 Git 리포지토리의 지정된 디렉토리를 스캔하고 발견된 각 하위 디렉토리에 대해 Application을 생성합니다. 이는 모노레포 설정에 유용합니다.

</details>

4. ApplicationSet에서 여러 generators를 어떻게 결합하나요?
   - A) Merge generator 사용
   - B) Matrix generator 사용
   - C) Combine generator 사용
   - D) A와 B 둘 다

<details>
<summary>정답 보기</summary>

**정답: D) A와 B 둘 다**

**설명:**
Matrix generator는 여러 generators의 파라미터 조합(데카르트 곱)을 생성합니다. Merge generator는 여러 generators의 파라미터를 결합하여 일치하는 항목을 병합합니다. 둘 다 generators를 결합하는 데 사용할 수 있습니다.

</details>

5. ApplicationSet 템플릿에서 `goTemplate` 필드의 목적은 무엇인가요?
   - A) Go 프로그래밍 활성화
   - B) 더 복잡한 템플릿을 위해 Go 템플릿 구문 사용
   - C) Go 애플리케이션 컴파일
   - D) 디버깅 활성화

<details>
<summary>정답 보기</summary>

**정답: B) 더 복잡한 템플릿을 위해 Go 템플릿 구문 사용**

**설명:**
`goTemplate: true`를 설정하면 Go 템플릿 구문이 활성화되어 기본 단순 변수 치환에 비해 조건문, 루프, 함수와 같은 더 강력한 템플릿 기능을 제공합니다.

</details>

6. Pull Request를 기반으로 Applications를 생성하려면 어떤 generator를 사용해야 하나요?
   - A) Git generator
   - B) Pull Request generator
   - C) SCM Provider generator
   - D) Webhook generator

<details>
<summary>정답 보기</summary>

**정답: B) Pull Request generator**

**설명:**
Pull Request generator는 리포지토리의 각 열린 pull request에 대해 Applications를 생성하여 코드 리뷰를 위한 미리보기 환경을 활성화합니다. GitHub, GitLab, Bitbucket, Gitea를 지원합니다.

</details>

7. ApplicationSet을 삭제하면 기본적으로 어떻게 되나요?
   - A) 아무 일도 없음, 생성된 Applications 유지
   - B) 생성된 모든 Applications 삭제됨
   - C) Applications가 고아가 됨
   - D) 백업 생성됨

<details>
<summary>정답 보기</summary>

**정답: B) 생성된 모든 Applications 삭제됨**

**설명:**
기본적으로 ApplicationSets는 계단식 삭제 정책을 가지므로 ApplicationSet을 삭제하면 생성된 모든 Applications도 삭제됩니다. 이는 `preserveResourcesOnDeletion` 정책을 사용하여 변경할 수 있습니다.

</details>

8. ApplicationSet이 제거될 때 생성된 Applications가 삭제되지 않도록 하려면 어떻게 해야 하나요?
   - A) `syncPolicy.preserveResourcesOnDeletion: true` 설정
   - B) `orphan` finalizer 사용
   - C) 삭제 정책 어노테이션 설정
   - D) owner reference를 수동으로 제거

<details>
<summary>정답 보기</summary>

**정답: A) `syncPolicy.preserveResourcesOnDeletion: true` 설정**

**설명:**
ApplicationSet의 syncPolicy에서 `preserveResourcesOnDeletion: true`를 설정하면 ApplicationSet이 삭제될 때 생성된 Applications(및 배포된 리소스)가 보존됩니다.

</details>
