# Kubeflow Notebooks 퀴즈

기준: Notebooks 1.11.0 / Community Distribution 26.03.1.

## 객관식 문제

1. Notebook 컨트롤러는 무엇을 조정하나요?

   - A) 사용자 노트북의 브라우저 프로세스
   - B) Notebook CR로부터 StatefulSet, Service와 설정된 라우팅 리소스
   - C) 사용자마다 하나의 EC2 인스턴스
   - D) HTML 대시보드만

<details>
<summary>정답 보기</summary>

**정답: B) Notebook CR로부터 StatefulSet, Service와 설정된 라우팅 리소스**

StatefulSet 컨트롤러가 Pod를 만들고 Kubernetes가 배치합니다. 대시보드는 UI 진입점입니다.
</details>

2. 이 장의 정확한 버전 기준은 무엇인가요?

   - A) 모든 컴포넌트가 Workspaces GA
   - B) Notebooks v1.11.0; 26.03.1은 Workspaces를 베타라고 설명하지만 이미지 태그는 v2.0.0-alpha.3
   - C) Notebook과 Workspace가 동일 API
   - D) 이 장에 v1 지원 종료일이 확정됨

<details>
<summary>정답 보기</summary>

**정답: B) Notebooks v1.11.0; 26.03.1은 Workspaces를 베타라고 설명하지만 이미지 태그는 v2.0.0-alpha.3**

릴리스 설명과 이미지 태그가 다릅니다. GA나 v1 종료 시점을 추정하지 말고 실제 API·이전 지원을 확인하세요.
</details>

3. Profile은 모든 노트북을 다른 사용자로부터 자동 격리하나요?

   - A) AWS와 스토리지를 포함해 모두 격리
   - B) 아니며 팀 공유가 가능하고 네트워크·스토리지·IAM·앱 인가는 별도
   - C) 네임스페이스가 패킷을 차단하므로 격리
   - D) RBAC가 다른 권한을 모두 취소하므로 격리

<details>
<summary>정답 보기</summary>

**정답: B) 아니며 팀 공유가 가능하고 네트워크·스토리지·IAM·앱 인가는 별도**

전체 UI는 Profile 네임스페이스를 선택합니다. Notebook CRD 자체가 모든 네임스페이스의 Profile 객체를 요구하지는 않습니다.
</details>

4. 노트북 Pod 교체 후 무엇이 보존되나요?

   - A) 모든 프로세스 메모리
   - B) 컨테이너 어디에 설치하든 모든 패키지
   - C) 보존된 영속 볼륨의 데이터; 컨테이너 계층 패키지·커널 메모리는 보존되지 않음
   - D) 연결된 모든 EC2 인스턴스

<details>
<summary>정답 보기</summary>

**정답: C) 보존된 영속 볼륨의 데이터; 컨테이너 계층 패키지·커널 메모리는 보존되지 않음**

마운트 경로, PVC·볼륨 수명, 백업을 확인하세요. ReadWriteOnce는 단일 노드 접근 모드이며 단일 Pod 보장이 아닙니다.
</details>

5. 검토한 유휴 컬링 기본값은 무엇인가요?

   - A) 활성화, 유휴 기준 1분
   - B) 비활성화, 유휴 기준 1440분, 확인 주기 1분
   - C) 모든 RStudio·셸 프로세스에 활성화
   - D) GPU 노트북만 비활성화

<details>
<summary>정답 보기</summary>

**정답: B) 비활성화, 유휴 기준 1440분, 확인 주기 1분**

Jupyter 커널 활동을 사용합니다. API 실패·빈 결과는 기존 활동 시각을 유지해 중지로 이어질 수 있으므로 실제 이미지와 접근 경로로 검증해야 합니다.
</details>

6. v1.11.0은 중지된 Notebook을 어떻게 표현하나요?

   - A) spec.replicas: 0
   - B) kubeflow-resource-stopped의 존재; 컨트롤러가 StatefulSet replica를 0으로 설정
   - C) annotation 값 false이면 실행 중
   - D) PVC 삭제

<details>
<summary>정답 보기</summary>

**정답: B) kubeflow-resource-stopped의 존재; 컨트롤러가 StatefulSet replica를 0으로 설정**

NotebookSpec에는 replicas가 없습니다. 재시작은 annotation 제거로 처리하며 문자열 false도 존재하면 중지입니다.
</details>

7. 커스텀 이미지 digest가 보장하는 것은 무엇인가요?

   - A) 모든 사용자의 전체 런타임 환경 동일
   - B) 참조 이미지 내용; 마운트 데이터와 런타임 변경은 다를 수 있음
   - C) 모든 GPU 드라이버와 자동 호환
   - D) UI 이미지 제한을 API로 우회할 수 없음

<details>
<summary>정답 보기</summary>

**정답: B) 참조 이미지 내용; 마운트 데이터와 런타임 변경은 다를 수 있음**

서버 경로·포트·UID, 의존성, 아키텍처를 검증해야 합니다. 변경 가능한 태그만으로 이미지 바이트가 고정되지는 않습니다.
</details>

## 단답형 문제

8. 유휴 GPU 노트북을 중지해도 즉각적인 비용 감소가 보장되지 않는 이유는 무엇인가요?

<details>
<summary>정답 보기</summary>

Pod 자원 요청이 해제되어도 다른 워크로드, PDB, NodePool 제한·중단 정책, 용량 관리가 노드 종료에 영향을 줍니다. 노드가 실행 중인 동안 EC2 비용이 계속 발생할 수 있습니다.
</details>

9. 노트북에서 RBAC, Istio 인가, NetworkPolicy의 역할은 어떻게 다른가요?

<details>
<summary>정답 보기</summary>

RBAC는 Kubernetes API 작업을 제어합니다. Istio 인가는 구성된 프록시·정책이 처리하는 요청을 제어합니다. NetworkPolicy는 CNI가 집행할 때 Pod 네트워크 통신을 제한합니다. 어느 하나만으로 스토리지·IAM·애플리케이션 격리가 모두 보장되지는 않습니다.
</details>

---

[학습 자료로 돌아가기](../../../ai-ml/kubeflow/03-notebooks.md)
