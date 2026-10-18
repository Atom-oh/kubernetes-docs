# Part 13: 버전, 설치/업그레이드, Cluster Mesh 퀴즈

> **Cilium 1.20.2 · 2026-10-15**

1. **업그레이드와 롤백 모두에 대해 upstream이 테스트하는 경로는 무엇인가요?**
   - A) 연속된 minor만(예: 1.19에서 1.20, 그리고 되돌리기), 현재 minor의 최신 패치로 먼저 올린 뒤
   - B) 최신 패치만 설치되어 있으면 N에서 N+2 minor로 건너뛰기
   - C) pre-flight 차트가 통과하면 어떤 minor에서든 최신 minor로
   - D) agent만 먼저 올리고 operator는 한 minor 뒤에 올리기

   <details>
   <summary>정답 보기</summary>

   **정답: A) 연속된 minor만(예: 1.19에서 1.20, 그리고 되돌리기), 현재 minor의 최신 패치로 먼저 올린 뒤**

   minor를 건너뛰는 경로는 테스트되지 않으며 모든 구성 요소가 같은 버전이어야 합니다. 최신 패치로 먼저 올려 두면 모든 수정이 반영된 롤백 대상이 생깁니다.

   </details>

2. **새 minor 버전으로 올릴 때 `helm upgrade --reuse-values`를 쓰면 안 되는 이유는 무엇인가요?**
   - A) Cilium CRD를 삭제하기 때문
   - B) `upgradeCompatibility`를 새 버전으로 초기화하기 때문
   - C) OCI 차트를 클래식 저장소 차트로 강제로 바꾸기 때문
   - D) 이전 릴리스의 값을 재사용하고 새 차트 기본값을 무시해 manifest가 깨질 수 있기 때문

   <details>
   <summary>정답 보기</summary>

   **정답: D) 이전 릴리스의 값을 재사용하고 새 차트 기본값을 무시해 manifest가 깨질 수 있기 때문**

   `helm get values`로 값을 저장하고 이름이 바뀌거나 제거된 키를 검토한 뒤 `-f`로 전달합니다. `--reuse-values`는 차트 버전이 같을 때(예: 같은 버전에 Cluster Mesh 값을 적용)만 허용됩니다.

   </details>

3. **`maxConnectedClusters`의 기본값과 511로 설정할 때의 비용은 무엇인가요?**
   - A) 255; KVStoreMesh를 꺼야 함
   - B) 255; cluster-local identity 최대 개수가 65535에서 32767로 줄어듦
   - C) 127; 클러스터 name 길이 제한이 절반이 됨
   - D) 511; identity 범위는 그대로지만 overlay 모드만 동작함

   <details>
   <summary>정답 보기</summary>

   **정답: B) 255; cluster-local identity 최대 개수가 65535에서 32767로 줄어듦**

   클러스터 ID가 숫자 identity의 비트를 사용합니다. 모든 클러스터에서 값이 같아야 하고 설치 시에만 설정해야 하며, 동작 중인 클러스터에서 바꾸면 연결이 끊기거나 정책이 잘못 적용될 수 있습니다.

   </details>

4. **`clustermesh.apiserver.tls.authMode`의 기본값은 1.20과 1.21 pre-release에서 각각 무엇인가요?**
   - A) 1.20은 `legacy`, 1.21은 `migration`
   - B) 1.20은 `cluster`, 1.21은 `cluster-strict`
   - C) 1.20은 `migration`, 1.21은 `cluster`(새 `cluster-strict` 옵션 추가)
   - D) 둘 다 `migration`

   <details>
   <summary>정답 보기</summary>

   **정답: C) 1.20은 `migration`, 1.21은 `cluster`(새 `cluster-strict` 옵션 추가)**

   `cluster` 모드에서는 각 클러스터가 `remote-<cluster-name>`으로 인증하며 공유 CA가 필요합니다. 사용자 제공 인증서와 `tls.auto.enabled=false`를 쓰면 새 CN으로 remote 인증서를 재발급하거나 `authMode`를 `migration`으로 되돌려야 합니다.

   </details>

5. **Cilium 1.19 이상의 Cluster Mesh에서 클러스터 레이블이 없는 정책 selector는 어떤 endpoint와 일치하나요?**
   - A) 연결된 모든 클러스터의 endpoint
   - B) 없음, 정책이 거부됨
   - C) 원격 클러스터의 global 네임스페이스 endpoint만
   - D) 로컬 클러스터의 endpoint만

   <details>
   <summary>정답 보기</summary>

   **정답: D) 로컬 클러스터의 endpoint만**

   `policy-default-local-cluster`(Helm `clustermesh.policyDefaultLocalCluster`)는 1.19에서 기본 true입니다. 원격 클러스터는 `io.cilium.k8s.policy.cluster` 레이블로, 모든 클러스터는 `Exists` 표현식으로 선택합니다. 1.18까지는 기본이 모든 클러스터였습니다.

   </details>

6. **agent가 원격 클러스터 상태를 로컬 캐시에서 읽게 하는 clustermesh-apiserver 컨테이너는 무엇인가요?**
   - A) 원격 상태를 로컬 etcd로 가져오는 `kvstoremesh`
   - B) 원격 클러스터를 미러링하는 `apiserver`
   - C) 원격 etcd에서 직접 가져오는 `etcd`
   - D) 원격 etcd마다 연결을 유지하는 cilium-agent

   <details>
   <summary>정답 보기</summary>

   **정답: A) 원격 상태를 로컬 etcd로 가져오는 `kvstoremesh`**

   `apiserver` 컨테이너는 로컬 클러스터 상태를 로컬 etcd로 동기화할 뿐입니다. KVStoreMesh는 1.16부터 기본 활성이며 1.21 pre-release에서는 항상 활성입니다.

   </details>

7. **Cilium 1.20이 요구하는 Gateway API CRD 버전과 TLSRoute 함정은 무엇인가요?**
   - A) v1.6.1; Helm 차트가 CRD를 설치하고 TLSRoute도 자동 교체함
   - B) v1.4; TLSRoute는 전혀 지원되지 않음
   - C) v1.6.1; standard 채널 TLSRoute v1.6을 설치하면 기존 `v1alpha2` TLSRoute가 읽히지 않으므로 이미 쓰고 있다면 experimental v1.6.1 TLSRoute를 사용
   - D) v1.3.0; TLSRoute는 `bpf.tproxy` 플래그가 필요함

   <details>
   <summary>정답 보기</summary>

   **정답: C) v1.6.1; standard 채널 TLSRoute v1.6을 설치하면 기존 `v1alpha2` TLSRoute가 읽히지 않으므로 이미 쓰고 있다면 experimental v1.6.1 TLSRoute를 사용**

   차트는 Gateway API CRD를 설치하지 않습니다. 채널을 바꾸기 전에 TLSRoute를 백업하고 `kubectl apply --server-side`로 적용합니다.

   </details>

8. **EKS Auto Mode에서 Cilium을 CNI로 사용할 수 있나요?**
   - A) 예, `cni.chainingMode=aws-cni`를 쓰면 됨
   - B) 아니요, AWS는 Auto Mode가 대체 CNI와 network policy 플러그인을 지원하지 않는다고 명시함
   - C) 예, overlay 모드에서만
   - D) 예, `aws-node`를 일치하지 않는 node selector로 patch하면 됨

   <details>
   <summary>정답 보기</summary>

   **정답: B) 아니요, AWS는 Auto Mode가 대체 CNI와 network policy 플러그인을 지원하지 않는다고 명시함**

   managed 또는 self-managed 노드 그룹을 사용하세요. `aws-node` patch와 ENI 모드는 일반 노드 그룹용입니다.

   </details>

9. **`cilium_drift_checker_config_delta > 0`은 무엇을 뜻하나요?**
   - A) agent가 Kubernetes API 서버에 접근하지 못함
   - B) CiliumNodeConfig 검증이 실패함
   - C) `cilium-config` ConfigMap에 실행 중인 agent가 아직 적용하지 않은 키가 있어 agent 재시작이 필요함
   - D) operator와 agent의 이미지 버전이 다름

   <details>
   <summary>정답 보기</summary>

   **정답: C) `cilium-config` ConfigMap에 실행 중인 agent가 아직 적용하지 않은 키가 있어 agent 재시작이 필요함**

   drift checker는 감시 중인 ConfigMap과 agent가 시작될 때의 설정을 비교합니다. `cilium config set --restart=false`는 이 지표로 확인할 수 있는 보류 변경을 만드는 방법입니다.

   </details>

10. **KVStore에서 CRD로 Double Write 마이그레이션할 때 `identity-allocation-mode` 값의 순서는 무엇인가요?**
    - A) `crd`, `doublewrite-readcrd`, `kvstore`
    - B) `doublewrite-readcrd`, `doublewrite-readkvstore`, `crd`
    - C) `kvstore`, `crd`, 그리고 `doublewrite-readkvstore`는 롤백 상태로만 사용
    - D) `kvstore`, `doublewrite-readkvstore`, `doublewrite-readcrd`, `crd`

    <details>
    <summary>정답 보기</summary>

    **정답: D) `kvstore`, `doublewrite-readkvstore`, `doublewrite-readcrd`, `crd`**

    두 Double Write 단계에서는 operator를 먼저, 그다음 agent를 재배포하고, 마지막 `crd` 단계에서는 agent를 먼저, 그다음 operator를 재배포합니다. 이 기능은 beta이며 일회성 `migrate-identity` 도구는 1.21 pre-release에서 deprecated입니다.

    </details>
