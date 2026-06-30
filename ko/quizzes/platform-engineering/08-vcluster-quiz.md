# vCluster 퀴즈

1. vCluster가 기존 Namespace 기반 멀티 테넌시보다 우수한 점은?
   - A) vCluster는 물리 클러스터를 추가로 생성
   - B) 각 테넌트에게 완전한 Kubernetes API를 제공하면서 호스트 클러스터의 리소스를 공유
   - C) vCluster는 네트워크를 완전히 분리
   - D) vCluster는 별도의 노드를 필요로 함

<details>
<summary>정답 보기</summary>

**정답: B) 각 테넌트에게 완전한 Kubernetes API를 제공하면서 호스트 클러스터의 리소스를 공유**

**설명:**
vCluster는 가상 컨트롤 플레인을 통해 각 테넌트에게 독립된 Kubernetes API(CRD 설치, RBAC 관리, Namespace 생성 등)를 제공합니다. 실제 워크로드는 호스트 클러스터에서 실행되므로 물리 클러스터 추가 비용 없이 강력한 격리를 제공합니다.

</details>

---

2. vCluster의 Syncer 컴포넌트의 핵심 역할은?
   - A) 가상 클러스터의 DNS를 관리
   - B) 가상 클러스터의 리소스를 호스트 클러스터에 동기화하고, 호스트의 상태를 가상 클러스터로 반영
   - C) 가상 클러스터 간의 네트워크를 연결
   - D) 가상 클러스터의 로그를 수집

<details>
<summary>정답 보기</summary>

**정답: B) 가상 클러스터의 리소스를 호스트 클러스터에 동기화하고, 호스트의 상태를 가상 클러스터로 반영**

**설명:**
Syncer는 vCluster의 핵심 컴포넌트로, 가상 클러스터에서 생성된 Pod, Service, ConfigMap 등의 리소스를 호스트 클러스터의 실제 리소스로 변환합니다. 반대로 호스트의 Node 정보, 스토리지 클래스 등을 가상 클러스터로 동기화하여 양방향 리소스 관리를 수행합니다.

</details>

---

3. vCluster를 PR별 프리뷰 환경으로 사용할 때의 장점은?
   - A) PR 머지 없이 코드를 프로덕션에 배포
   - B) 각 PR에 격리된 Kubernetes 환경을 빠르게 생성/삭제하여 통합 테스트 가능
   - C) PR 리뷰어에게 클러스터 관리자 권한 부여
   - D) CI 파이프라인 실행 시간 단축

<details>
<summary>정답 보기</summary>

**정답: B) 각 PR에 격리된 Kubernetes 환경을 빠르게 생성/삭제하여 통합 테스트 가능**

**설명:**
vCluster는 30초 이내에 생성되므로, CI/CD 파이프라인에서 PR별로 격리된 Kubernetes 환경을 프로비저닝할 수 있습니다. PR이 머지/클로즈되면 vCluster를 삭제하여 리소스를 회수합니다. 이를 통해 각 PR의 변경사항을 독립된 환경에서 통합 테스트할 수 있습니다.

</details>

---

4. vCluster의 Sleep Mode 기능의 목적은?
   - A) 가상 클러스터의 보안을 강화
   - B) 사용하지 않는 가상 클러스터의 리소스를 해제하여 비용 절감
   - C) 가상 클러스터의 데이터를 백업
   - D) 가상 클러스터의 성능을 최적화

<details>
<summary>정답 보기</summary>

**정답: B) 사용하지 않는 가상 클러스터의 리소스를 해제하여 비용 절감**

**설명:**
Sleep Mode는 일정 시간 활동이 없는 vCluster의 워크로드를 자동으로 중지(Sleep)합니다. API 요청이 들어오면 자동으로 깨어납니다(Wake). 이를 통해 야간이나 주말에 사용되지 않는 개발/테스트 vCluster의 비용을 크게 절감할 수 있습니다.

</details>

---

5. vCluster에서 호스트 클러스터의 StorageClass를 가상 클러스터에서 사용하려면?
   - A) StorageClass를 가상 클러스터에서 다시 생성
   - B) syncFromHost 설정으로 호스트의 StorageClass를 가상 클러스터로 동기화
   - C) PV를 수동으로 마운트
   - D) CSI 드라이버를 가상 클러스터에 별도 설치

<details>
<summary>정답 보기</summary>

**정답: B) syncFromHost 설정으로 호스트의 StorageClass를 가상 클러스터로 동기화**

**설명:**
vCluster의 `syncFromHost` 설정을 통해 호스트 클러스터의 StorageClass, IngressClass, Node 등의 리소스를 가상 클러스터에서 조회할 수 있도록 동기화합니다. 가상 클러스터의 PVC는 호스트 클러스터의 StorageClass를 사용하여 실제 PV를 프로비저닝합니다.

</details>

---

6. Backstage + vCluster 통합에서 개발자 셀프서비스의 동작 방식은?
   - A) 개발자가 직접 kubectl로 vCluster를 생성
   - B) Backstage Template에서 vCluster 생성 요청 → GitOps 리포지토리에 Push → ArgoCD가 동기화하여 vCluster 프로비저닝
   - C) Backstage가 직접 Kubernetes API를 호출하여 vCluster 생성
   - D) 관리자가 수동으로 vCluster를 생성하고 개발자에게 할당

<details>
<summary>정답 보기</summary>

**정답: B) Backstage Template에서 vCluster 생성 요청 → GitOps 리포지토리에 Push → ArgoCD가 동기화하여 vCluster 프로비저닝**

**설명:**
개발자가 Backstage Template에서 환경 이름, 리소스 크기 등을 입력하면, Template이 vCluster Helm Release 매니페스트를 생성하여 GitOps 리포지토리에 Push합니다. ArgoCD가 변경을 감지하여 클러스터에 동기화하면 vCluster가 자동으로 프로비저닝됩니다.

</details>

---

7. vCluster의 보안 격리에서 NetworkPolicy의 역할은?
   - A) 가상 클러스터 간의 CPU 사용량을 제한
   - B) 가상 클러스터의 Pod가 다른 vCluster의 Pod나 호스트 클러스터 리소스에 접근하지 못하도록 네트워크 격리
   - C) 가상 클러스터의 Ingress 트래픽을 암호화
   - D) DNS 쿼리를 필터링

<details>
<summary>정답 보기</summary>

**정답: B) 가상 클러스터의 Pod가 다른 vCluster의 Pod나 호스트 클러스터 리소스에 접근하지 못하도록 네트워크 격리**

**설명:**
vCluster의 Pod는 호스트 클러스터에서 실행되므로, NetworkPolicy 없이는 다른 vCluster의 Pod에 네트워크로 접근할 수 있습니다. 각 vCluster의 네임스페이스에 NetworkPolicy를 적용하여 해당 네임스페이스 내부 통신만 허용하고 외부 접근을 차단하면 강력한 네트워크 격리를 구현할 수 있습니다.

</details>

---

8. vCluster와 물리 클러스터를 비교할 때 vCluster를 선택해야 하는 상황은?
   - A) 완전한 하드웨어 격리가 필요할 때
   - B) 빠른 프로비저닝, 비용 효율성, CRD 격리가 필요하되 완전한 노드 격리는 불필요할 때
   - C) 규제 요구사항으로 별도의 AWS 계정이 필요할 때
   - D) GPU 워크로드를 실행할 때

<details>
<summary>정답 보기</summary>

**정답: B) 빠른 프로비저닝, 비용 효율성, CRD 격리가 필요하되 완전한 노드 격리는 불필요할 때**

**설명:**
vCluster는 30초 이내 생성, 호스트 클러스터 리소스 공유로 비용 효율적이며, CRD/RBAC/Namespace 격리를 제공합니다. 개발/테스트 환경, CI/CD 임시 환경, 교육 환경 등에 적합합니다. 반면 규제 준수, 완전한 하드웨어 격리, 별도 네트워크 격리가 필요한 프로덕션 워크로드에는 물리 클러스터가 적합합니다.

</details>
