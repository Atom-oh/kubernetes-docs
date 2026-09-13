# ArgoCD 동기화 전략 퀴즈

이 퀴즈는 ArgoCD 동기화 전략과 옵션에 대한 이해도를 테스트합니다.

1. ArgoCD에서 "Sync"와 "Refresh"의 차이점은 무엇인가요?
   - A) 같은 작업임
   - B) Refresh는 현재 상태와 Git을 비교하고, Sync는 일치하도록 변경 사항 적용
   - C) Sync는 수동, Refresh는 자동
   - D) Refresh는 리소스 삭제, Sync는 리소스 생성

<details>
<summary>정답 보기</summary>

**정답: B) Refresh는 현재 상태와 Git을 비교하고, Sync는 일치하도록 변경 사항 적용**

**설명:**
Refresh 작업은 Git에서 최신 매니페스트를 가져와 라이브 상태와 비교하여 Application 상태를 업데이트합니다. Sync 작업은 실제로 클러스터에 변경 사항을 적용하여 라이브 상태를 Git의 원하는 상태와 일치시킵니다.

</details>

2. `automated` 동기화 정책을 활성화하면 어떻게 되나요?
   - A) 애플리케이션 자동 삭제
   - B) 원하는 상태가 라이브 상태와 다를 때 자동 동기화 활성화
   - C) 자동 롤백 활성화
   - D) 자동 백업 생성

<details>
<summary>정답 보기</summary>

**정답: B) 원하는 상태가 라이브 상태와 다를 때 자동 동기화 활성화**

**설명:**
`syncPolicy.automated`가 활성화되면 ArgoCD는 정책에 따라 OutOfSync 변경을 자동 적용합니다. live-only 드리프트 수정은 selfHeal, 삭제는 prune이 별도이며, 같은 실패 commit을 무조건 계속 재시도하는 것은 아닙니다.

</details>

3. 자동 동기화에서 `prune` 옵션의 목적은 무엇인가요?
   - A) 오래된 Git 브랜치 정리
   - B) Git에 더 이상 정의되지 않은 리소스 자동 삭제
   - C) 실패한 배포 제거
   - D) 애플리케이션 자체 삭제

<details>
<summary>정답 보기</summary>

**정답: B) Git에 더 이상 정의되지 않은 리소스 자동 삭제**

**설명:**
자동 동기화에서 `prune: true`가 설정되면 ArgoCD는 이 Application이 추적하는 리소스 중 원하는 소스에서 사라진 대상을 삭제합니다. 클러스터의 모든 비관리 리소스를 삭제하는 기능은 아닙니다.

</details>

4. 동기화 정책에서 `selfHeal: true`는 무엇을 하나요?
   - A) YAML 구문 오류 자동 수정
   - B) 수동 변경으로 인해 라이브 상태가 원하는 상태에서 벗어나면 자동 동기화
   - C) 비정상 파드 재시작
   - D) 손상된 Git 리포지토리 복구

<details>
<summary>정답 보기</summary>

**정답: B) 수동 변경으로 인해 라이브 상태가 원하는 상태에서 벗어나면 자동 동기화**

**설명:**
자동 sync가 활성화되고 selfHeal을 설정하면 비교 대상의 live-only 드리프트를 조정합니다. 동기화 윈도우·권한·ignore 규칙도 적용되며 손실된 데이터나 YAML 오류를 자동 복구하지는 않습니다.

</details>

5. 패치 적용 대신 리소스를 교체하려면 어떤 동기화 옵션을 사용해야 하나요?
   - A) Force=true
   - B) Replace=true
   - C) Recreate=true
   - D) Update=true

<details>
<summary>정답 보기</summary>

**정답: B) Replace=true**

**설명:**
`Replace=true` 동기화 옵션은 ArgoCD에 `kubectl apply` 대신 `kubectl replace`를 사용하도록 지시하여 패치가 아닌 리소스를 완전히 교체합니다. replace/create도 immutable 필드 제한을 자동 우회하지 않습니다. Force=true와 Replace=true의 delete/create는 별도 파괴적 동작이며 PVC 마이그레이션을 대신하지 않습니다.

</details>
