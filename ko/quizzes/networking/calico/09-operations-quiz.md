# Calico 운영 퀴즈

> **관련 문서**: [Calico 운영](../../../networking/calico/09-operations.md)
> **마지막 업데이트**: 2026년 2월 22일

## 퀴즈

1. Calico 설치 방법 3가지로 올바른 것은?
   - A) kubectl, docker, helm
   - B) Operator, Manifest, Helm
   - C) apt, yum, snap
   - D) eksctl, terraform, pulumi

<details>
<summary>정답 보기</summary>

**정답: B) Operator, Manifest, Helm**

**설명:**
Calico는 세 가지 방법으로 설치할 수 있습니다: Tigera Operator(권장), 직접 Manifest 적용, Helm Chart. Operator 방식은 Installation CRD를 통해 선언적으로 관리되며, 업그레이드와 설정 변경이 용이합니다.

</details>

2. `calicoctl node status` 명령어가 보여주는 정보는?
   - A) Pod 목록
   - B) 노드의 BGP 피어링 상태 및 연결 정보
   - C) Network Policy 목록
   - D) IP 풀 사용량

<details>
<summary>정답 보기</summary>

**정답: B) 노드의 BGP 피어링 상태 및 연결 정보**

**설명:**
`calicoctl node status`는 현재 노드의 BGP 피어링 상태, 연결된 피어 수, 각 피어와의 연결 상태(Established, Connect 등)를 보여줍니다. BGP 관련 문제를 진단할 때 가장 먼저 확인하는 명령어입니다.

</details>

3. `calicoctl ipam show --show-blocks`의 용도는?
   - A) 모든 Pod IP 주소 표시
   - B) 노드별 IP 블록 할당 상태 및 사용률 확인
   - C) DNS 레코드 표시
   - D) 라우팅 테이블 표시

<details>
<summary>정답 보기</summary>

**정답: B) 노드별 IP 블록 할당 상태 및 사용률 확인**

**설명:**
`calicoctl ipam show --show-blocks`는 각 노드에 할당된 IP 블록과 해당 블록의 사용률을 보여줍니다. IP 고갈 문제를 진단하거나 IPAM 효율성을 확인할 때 유용합니다. 블록 어피니티와 할당된 IP 수를 확인할 수 있습니다.

</details>

4. Felix가 노출하는 Prometheus 메트릭의 예시가 아닌 것은?
   - A) felix_iptables_rules
   - B) felix_active_local_endpoints
   - C) felix_cluster_node_count
   - D) felix_ipset_count

<details>
<summary>정답 보기</summary>

**정답: C) felix_cluster_node_count**

**설명:**
Felix는 로컬 노드의 메트릭만 수집합니다. `felix_iptables_rules`(iptables 규칙 수), `felix_active_local_endpoints`(활성 엔드포인트 수), `felix_ipset_count`(ipset 수) 등이 있습니다. 클러스터 전체 노드 수는 Felix가 아닌 다른 소스에서 수집해야 합니다.

</details>

5. Typha가 노출하는 Prometheus 메트릭의 예시는?
   - A) typha_connections_accepted
   - B) typha_pod_count
   - C) typha_cluster_size
   - D) typha_network_policies

<details>
<summary>정답 보기</summary>

**정답: A) typha_connections_accepted**

**설명:**
Typha는 `typha_connections_accepted`(수락된 연결 수), `typha_connections_active`(활성 연결 수), `typha_cache_size`(캐시 크기) 등의 메트릭을 노출합니다. 이 메트릭들은 Typha의 부하 상태와 Felix 연결 상태를 모니터링하는 데 사용됩니다.

</details>

6. Pod가 IP를 할당받지 못할 때 디버깅 순서로 올바른 것은?
   - A) 바로 Calico 재설치
   - B) calico-node 로그 확인 -> IPAM 블록 확인 -> IP Pool 확인
   - C) 클러스터 재시작
   - D) 노드 삭제 후 재생성

<details>
<summary>정답 보기</summary>

**정답: B) calico-node 로그 확인 -> IPAM 블록 확인 -> IP Pool 확인**

**설명:**
IP 할당 문제 디버깅 순서: 1) `kubectl logs -n calico-system -l k8s-app=calico-node`로 calico-node 로그 확인, 2) `calicoctl ipam show --show-blocks`로 블록 할당 상태 확인, 3) `calicoctl get ippool -o yaml`로 IP Pool 설정 확인. IP 풀이 가득 찼거나 노드에 블록이 할당되지 않은 경우를 찾습니다.

</details>

7. BGP 피어링 실패를 확인하는 첫 번째 명령어는?
   - A) kubectl get pods
   - B) calicoctl node status
   - C) calicoctl get ippool
   - D) kubectl describe node

<details>
<summary>정답 보기</summary>

**정답: B) calicoctl node status**

**설명:**
`calicoctl node status`는 현재 노드의 BGP 세션 상태를 보여줍니다. 피어가 "Established" 상태인지, 연결 실패 시 어떤 상태(Connect, Active, OpenSent 등)인지 확인할 수 있습니다. 추가로 BIRD 로그를 확인하여 상세한 오류 원인을 파악합니다.

</details>

8. Network Policy가 작동하지 않을 때 확인해야 할 사항이 아닌 것은?
   - A) Policy selector가 Pod 레이블과 일치하는지
   - B) kube-proxy 설정
   - C) calicoctl get workloadendpoint로 엔드포인트 확인
   - D) Felix 로그에서 Policy 적용 여부 확인

<details>
<summary>정답 보기</summary>

**정답: B) kube-proxy 설정**

**설명:**
Network Policy는 kube-proxy와 독립적으로 Calico Felix가 처리합니다. Policy 문제 디버깅 시에는 selector와 레이블 일치 여부, workloadendpoint 상태, Felix 로그를 확인합니다. kube-proxy는 Service 관련 기능을 담당하며 Network Policy와 직접 관련이 없습니다.

</details>

9. Calico 버전 업그레이드 시 권장되는 절차로 올바른 것은?
   - A) 모든 컴포넌트 동시 업그레이드
   - B) Operator 업그레이드 -> Installation CR 업데이트 -> 롤링 업데이트 확인
   - C) calico-node만 업그레이드
   - D) 클러스터 재생성

<details>
<summary>정답 보기</summary>

**정답: B) Operator 업그레이드 -> Installation CR 업데이트 -> 롤링 업데이트 확인**

**설명:**
Operator 기반 설치에서는 먼저 Tigera Operator를 새 버전으로 업그레이드하고, Installation CR의 버전을 업데이트합니다. Operator가 자동으로 calico-node, typha 등을 롤링 업데이트합니다. 업그레이드 중 Network Policy가 계속 적용되는지 확인합니다.

</details>

10. 기본 거부 정책(Default Deny) 구현의 모범 사례는?
    - A) 모든 네임스페이스에 개별 NetworkPolicy 생성
    - B) GlobalNetworkPolicy로 클러스터 전체 기본 거부 후 필요한 트래픽만 허용
    - C) Security Group으로 대체
    - D) 정책 없이 방화벽만 사용

<details>
<summary>정답 보기</summary>

**정답: B) GlobalNetworkPolicy로 클러스터 전체 기본 거부 후 필요한 트래픽만 허용**

**설명:**
보안 모범 사례는 GlobalNetworkPolicy로 클러스터 전체 기본 거부(Default Deny)를 설정하고, DNS, 모니터링 등 필수 트래픽을 허용한 후, 애플리케이션별 NetworkPolicy로 필요한 통신만 허용하는 것입니다. 이를 "Zero Trust" 네트워킹이라고 합니다.

</details>

11. Felix flow log를 활성화하는 FelixConfiguration 설정은?
    - A) flowLogsEnabled: true
    - B) flowLogsFileEnabled: true
    - C) enableFlowLogs: true
    - D) logsFlow: enabled

<details>
<summary>정답 보기</summary>

**정답: B) flowLogsFileEnabled: true**

**설명:**
FelixConfiguration에서 `flowLogsFileEnabled: true`를 설정하면 플로우 로그가 파일로 기록됩니다. 추가로 `flowLogsFlushInterval`(플러시 간격), `flowLogsFileDirectory`(저장 경로), `flowLogsFileMaxFiles`(최대 파일 수) 등을 설정할 수 있습니다.

</details>

12. calicoctl이 Kubernetes datastore를 사용하도록 설정하는 환경변수는?
    - A) CALICO_DATASTORE=kubernetes
    - B) DATASTORE_TYPE=kubernetes
    - C) ETCD_ENDPOINTS=kubernetes
    - D) CALICO_BACKEND=kube

<details>
<summary>정답 보기</summary>

**정답: B) DATASTORE_TYPE=kubernetes**

**설명:**
`export DATASTORE_TYPE=kubernetes`와 `export KUBECONFIG=~/.kube/config`를 설정하면 calicoctl이 Kubernetes API를 데이터스토어로 사용합니다. etcd를 직접 사용하는 경우에는 `DATASTORE_TYPE=etcdv3`와 `ETCD_ENDPOINTS` 환경변수를 설정합니다.

</details>
