# MLflow EKS 배포 퀴즈

## 객관식 문제

1. EKS 자체 운영의 주요 trade-off는?
   - A) 항상 관리형보다 저렴하다
   - B) 기존 Kubernetes 패턴을 재사용하지만 서버·저장소·접근 제어를 직접 운영한다
   - C) 관리형 서비스에는 Tracking이 없다
   - D) S3와 DB가 자동 생성된다

<details>
<summary>정답 보기</summary>

**정답: B**

운영 부담, 기능, 지원 버전과 실제 부하를 비교합니다.
</details>

2. SQLite 동시성에 대한 정확한 설명은?
   - A) 두 번째 사용자가 접근하면 반드시 즉시 깨진다
   - B) 여러 프로세스 접근과 직렬화된 쓰기는 가능하지만 쓰기·잠금·공유 파일 제약이 있다
   - C) 관계형 DB가 아니다
   - D) 모든 다중 Pod에 독립 파일을 두면 같은 DB가 된다

<details>
<summary>정답 보기</summary>

**정답: B**

SQLite 자체 기능과 여러 Pod의 저장소 배치를 구분합니다.
</details>

3. 검토한 community chart 1.11.7의 기본 metadata 설정은?
   - A) 항상 RDS PostgreSQL
   - B) S3 객체
   - C) backendStore.defaultSqlitePath가 :memory:
   - D) 영구 PVC가 자동 생성됨

<details>
<summary>정답 보기</summary>

**정답: C**

Upstream CLI의 새 SQLite 파일 기본값과 chart의 override는 다릅니다.
</details>

4. Tracking DB를 외부 PostgreSQL로 바꾸면 무엇도 자동 공유되나요?
   - A) 모든 auth DB와 cache
   - B) 모든 worker의 메모리
   - C) 모든 session secret
   - D) 별도 auth DB·secret·queue/cache는 추가 확인이 필요하다

<details>
<summary>정답 보기</summary>

**정답: D**

선택한 기능의 공유 상태를 확인한 뒤 replica를 늘립니다.
</details>

5. 차트·image·source 버전에 대한 올바른 설명은?
   - A) 항상 같은 번호다
   - B) source tag가 있으면 OCI package도 반드시 있다
   - C) 각 버전을 따로 확인하고 실제 package를 내려받아 manifest를 검사한다
   - D) 최신 tag만 쓰면 digest 검토가 필요 없다

<details>
<summary>정답 보기</summary>

**정답: C**

검토한 공식 source chart와 appVersion도 서로 달랐습니다.
</details>

6. S3용 ServiceAccount IAM 권한으로 PostgreSQL 로그인도 자동 허용되나요?
   - A) 항상 그렇다
   - B) 아니다. DB 네트워크·TLS·사용자/credential 또는 IAM DB auth를 별도 구성한다
   - C) S3 bucket 이름이 같으면 된다
   - D) DB password를 이미지에 넣으면 된다

<details>
<summary>정답 보기</summary>

**정답: B**

서로 다른 권한과 인증 계층입니다.
</details>

7. EKS Pod Identity에 필요한 조건은?
   - A) 모든 Fargate·Windows Pod에서 무조건 동작
   - B) ServiceAccount 이름만 지정
   - C) Linux EC2 worker, Agent, association, 지원 SDK 등
   - D) 정적 root access key

<details>
<summary>정답 보기</summary>

**정답: C**

IRSA와 Pod Identity의 지원 범위·설정도 각각 확인합니다.
</details>

8. SecretKeyRef와 allowed_hosts 설정만으로 충분한 보안이 되나요?
   - A) 환경 변수 노출과 사용자 인가가 모두 해결된다
   - B) 아니다. secret 전달 방식과 애플리케이션 인증·인가를 별도로 검토한다
   - C) DB 백업도 자동 수행한다
   - D) 모든 CORS origin을 허용해야 한다

<details>
<summary>정답 보기</summary>

**정답: B**

SecretKeyRef의 runtime env 전달과 host 검사의 한계를 구분합니다.
</details>

## 서술형 문제

9. 확인한 /health가 200을 반환하면 RDS·S3도 정상이라고 단정할 수 있나요?

<details>
<summary>정답 보기</summary>

아닙니다. 해당 구현은 OK, 200을 반환하는 HTTP process 검사입니다. DB/S3/권한의 지속 상태와 실제 workload 경로는 따로 검사합니다.
</details>

10. 고빈도 로깅의 DB 부하와 Aurora Serverless v2를 평가할 때 무엇을 고려하나요?

<details>
<summary>정답 보기</summary>

API batch·transaction·metric history·trace payload·전체 replica/worker pool을 측정합니다. Aurora도 capacity 범위, 연결·I/O·transaction 제약이 있어 무제한 burst 흡수나 최저 비용을 보장하지 않습니다.
</details>

---

[학습 자료로 돌아가기](../../../ai-ml/mlflow/03-eks-deployment.md)
