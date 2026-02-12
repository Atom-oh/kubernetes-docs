## 주관식 문제

1. Kubernetes 클러스터에서 etcd 데이터베이스의 백업 및 복원 절차를 설명하세요.

<details>
<summary>정답 보기</summary>

**정답:**

**etcd 백업 절차:**

1. **etcdctl 도구 설치 확인:**
   ```bash
   etcdctl version
   ```

2. **백업 명령 실행:**
   ```bash
   ETCDCTL_API=3 etcdctl snapshot save snapshot.db \
     --endpoints=https://127.0.0.1:2379 \
     --cacert=/etc/kubernetes/pki/etcd/ca.crt \
     --cert=/etc/kubernetes/pki/etcd/server.crt \
     --key=/etc/kubernetes/pki/etcd/server.key
   ```

3. **백업 파일 확인:**
   ```bash
   ETCDCTL_API=3 etcdctl snapshot status snapshot.db --write-out=table
   ```

4. **백업 파일을 안전한 위치에 저장:**
   - 클러스터 외부 스토리지
   - 클라우드 스토리지(S3, GCS 등)
   - 다른 물리적 위치

**etcd 복원 절차:**

1. **복원을 위해 모든 API 서버 중지:**
   ```bash
   sudo systemctl stop kube-apiserver
   ```

2. **etcd 서비스 중지:**
   ```bash
   sudo systemctl stop etcd
   ```

3. **데이터 디렉토리 백업(선택 사항):**
   ```bash
   sudo mv /var/lib/etcd /var/lib/etcd.bak
   ```

4. **스냅샷에서 새 데이터 디렉토리 생성:**
   ```bash
   ETCDCTL_API=3 etcdctl snapshot restore snapshot.db \
     --data-dir=/var/lib/etcd-restore \
     --name=master \
     --initial-cluster=master=https://127.0.0.1:2380 \
     --initial-cluster-token=etcd-cluster-1 \
     --initial-advertise-peer-urls=https://127.0.0.1:2380
   ```

5. **복원된 데이터 디렉토리를 etcd가 사용하도록 설정:**
   ```bash
   sudo mv /var/lib/etcd-restore /var/lib/etcd
   sudo chown -R etcd:etcd /var/lib/etcd
   ```

6. **etcd 서비스 재시작:**
   ```bash
   sudo systemctl start etcd
   ```

7. **etcd 상태 확인:**
   ```bash
   ETCDCTL_API=3 etcdctl endpoint health \
     --endpoints=https://127.0.0.1:2379 \
     --cacert=/etc/kubernetes/pki/etcd/ca.crt \
     --cert=/etc/kubernetes/pki/etcd/server.crt \
     --key=/etc/kubernetes/pki/etcd/server.key
   ```

8. **API 서버 재시작:**
   ```bash
   sudo systemctl start kube-apiserver
   ```

9. **클러스터 상태 확인:**
   ```bash
   kubectl get nodes
   kubectl get pods --all-namespaces
   ```

**모범 사례:**
- 정기적인 백업 일정 설정(예: 매일)
- 백업 전에 etcd 클러스터 상태 확인
- 백업 파일의 무결성 검증
- 복원 절차 정기적으로 테스트
- 백업 파일에 타임스탬프 포함
- 여러 백업 버전 유지
- 백업 및 복원 절차 문서화
</details>

2. Kubernetes 클러스터에서 노드 유지 보수를 위한 절차를 설명하고, `cordon`, `drain`, `uncordon` 명령의 차이점을 설명하세요.

<details>
<summary>정답 보기</summary>

**정답:**

**노드 유지 보수 절차:**

1. **노드 상태 확인:**
   ```bash
   kubectl get nodes
   kubectl describe node <노드_이름>
   ```

2. **노드 cordon(차단):**
   ```bash
   kubectl cordon <노드_이름>
   ```

3. **노드 drain(비우기):**
   ```bash
   kubectl drain <노드_이름> --ignore-daemonsets --delete-emptydir-data
   ```

4. **유지 보수 작업 수행:**
   - 소프트웨어 업데이트
   - 커널 업그레이드
   - 하드웨어 교체
   - 구성 변경

5. **작업 완료 후 노드 uncordon(차단 해제):**
   ```bash
   kubectl uncordon <노드_이름>
   ```

6. **노드 상태 확인:**
   ```bash
   kubectl get nodes
   ```

**명령어 차이점:**

1. **`kubectl cordon <노드_이름>`:**
   - 노드를 스케줄 불가능(unschedulable)으로 표시합니다.
   - 새로운 포드가 노드에 스케줄링되지 않습니다.
   - 이미 실행 중인 포드는 계속 실행됩니다.
   - 노드 상태에 `SchedulingDisabled` 표시가 나타납니다.

2. **`kubectl drain <노드_이름>`:**
   - 노드를 스케줄 불가능으로 표시합니다(cordon 포함).
   - 노드에서 실행 중인 포드를 안전하게 축출(evict)합니다.
   - 포드는 다른 노드로 재스케줄링됩니다.
   - DaemonSet 포드는 기본적으로 무시됩니다(`--ignore-daemonsets` 플래그 필요).
   - emptyDir 볼륨을 사용하는 포드는 데이터 손실 가능성이 있으므로 특별한 처리가 필요합니다(`--delete-emptydir-data` 플래그).
   - PodDisruptionBudget을 존중합니다.

3. **`kubectl uncordon <노드_이름>`:**
   - 노드를 다시 스케줄 가능(schedulable)으로 표시합니다.
   - 새로운 포드가 노드에 스케줄링될 수 있습니다.
   - 이전에 축출된 포드는 자동으로 돌아오지 않습니다.

**유지 보수 시 고려 사항:**
- 클러스터에 충분한 여유 용량이 있는지 확인
- 중요 워크로드에 PodDisruptionBudget 설정
- 한 번에 하나의 노드만 유지 보수
- 유지 보수 기간 동안 자동 확장 설정 조정
- 유지 보수 전후에 워크로드 상태 확인
- 롤링 업데이트 전략 사용
</details>

3. Kubernetes 클러스터에서 리소스 사용량을 모니터링하고 관리하는 방법을 설명하세요. 포함해야 할 도구와 기술을 나열하세요.

<details>
<summary>정답 보기</summary>

**정답:**

**Kubernetes 리소스 모니터링 및 관리 방법:**

**1. 기본 모니터링 도구:**

- **Metrics Server:**
  - 기본적인 CPU 및 메모리 사용량 메트릭 제공
  - `kubectl top` 명령 지원
  - 설치 방법:
    ```bash
    kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
    ```
  - 사용 예:
    ```bash
    kubectl top nodes
    kubectl top pods --all-namespaces
    ```

- **Kubernetes Dashboard:**
  - 클러스터 상태 및 리소스 사용량의 시각적 표현
  - 포드, 노드, 네임스페이스 등의 리소스 관리 인터페이스 제공

**2. 고급 모니터링 스택:**

- **Prometheus + Grafana:**
  - Prometheus: 메트릭 수집 및 저장
  - Grafana: 메트릭 시각화 및 대시보드
  - kube-prometheus-stack 또는 Prometheus Operator로 설치 가능
  - 사용자 정의 알림 규칙 및 대시보드 지원

- **ELK/EFK 스택:**
  - Elasticsearch: 로그 저장 및 검색
  - Logstash/Fluentd: 로그 수집 및 처리
  - Kibana: 로그 시각화 및 분석

**3. 리소스 관리 기술:**

- **리소스 요청 및 제한 설정:**
  ```yaml
  resources:
    requests:
      memory: "64Mi"
      cpu: "250m"
    limits:
      memory: "128Mi"
      cpu: "500m"
  ```

- **네임스페이스 수준 리소스 할당량(ResourceQuota):**
  ```yaml
  apiVersion: v1
  kind: ResourceQuota
  metadata:
    name: compute-quota
    namespace: dev
  spec:
    hard:
      pods: "10"
      requests.cpu: "4"
      requests.memory: 8Gi
      limits.cpu: "8"
      limits.memory: 16Gi
  ```

- **기본 리소스 제한(LimitRange):**
  ```yaml
  apiVersion: v1
  kind: LimitRange
  metadata:
    name: default-limits
    namespace: dev
  spec:
    limits:
    - default:
        cpu: 500m
        memory: 512Mi
      defaultRequest:
        cpu: 200m
        memory: 256Mi
      type: Container
  ```

- **Horizontal Pod Autoscaler(HPA):**
  ```yaml
  apiVersion: autoscaling/v2
  kind: HorizontalPodAutoscaler
  metadata:
    name: web-app
  spec:
    scaleTargetRef:
      apiVersion: apps/v1
      kind: Deployment
      name: web-app
    minReplicas: 2
    maxReplicas: 10
    metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 80
  ```

- **Vertical Pod Autoscaler(VPA):**
  - 포드의 CPU 및 메모리 요청을 자동으로 조정
  - 리소스 사용 패턴에 기반한 권장 사항 제공

- **Cluster Autoscaler:**
  - 워크로드 요구 사항에 따라 클러스터 노드 수 자동 조정
  - 리소스 부족 시 노드 추가, 사용률 낮을 때 노드 제거

**4. 모니터링 모범 사례:**

- 모든 포드에 리소스 요청 및 제한 설정
- 중요 메트릭에 대한 알림 구성
- 과거 사용량 분석을 통한 리소스 계획
- 정기적인 리소스 감사 수행
- 비용 최적화를 위한 리소스 사용량 추세 분석
- 개발, 스테이징, 프로덕션 환경에 적절한 리소스 할당량 설정
- 노드 레벨 및 포드 레벨 메트릭 모두 모니터링
</details>

4. Kubernetes 클러스터 업그레이드 과정에서 발생할 수 있는 주요 위험과 이를 완화하기 위한 전략을 설명하세요.

<details>
<summary>정답 보기</summary>

**정답:**

**Kubernetes 클러스터 업그레이드 위험 및 완화 전략:**

**1. 주요 위험:**

- **API 호환성 문제:**
  - 새 버전에서 API가 변경되거나 제거될 수 있음
  - 일부 사용자 정의 리소스 정의(CRD) 또는 API 버전이 더 이상 지원되지 않을 수 있음

- **워크로드 중단:**
  - 컨트롤 플레인 구성 요소 재시작으로 인한 일시적 API 서버 사용 불가
  - 노드 업그레이드 중 포드 재스케줄링으로 인한 서비스 중단

- **기능 변경:**
  - 기본 동작이 변경되어 기존 워크로드에 영향을 줄 수 있음
  - 보안 정책 변경으로 인한 권한 문제

- **성능 문제:**
  - 새 버전에서 리소스 요구 사항이 증가할 수 있음
  - 초기 안정화 기간 동안 성능 저하 가능성

- **롤백 복잡성:**
  - 일부 업그레이드는 쉽게 롤백할 수 없음
  - 데이터 형식 변경으로 인한 롤백 제한

**2. 완화 전략:**

- **철저한 계획 및 준비:**
  - **변경 로그 검토:** 새 버전의 변경 사항, 제거된 기능, 알려진 이슈 확인
  - **업그레이드 경로 확인:** 현재 버전에서 대상 버전으로의 직접 업그레이드가 지원되는지 확인
  - **리소스 요구 사항 검토:** 새 버전의 최소 요구 사항 확인

- **테스트 환경에서 먼저 테스트:**
  - 프로덕션과 유사한 테스트 클러스터에서 업그레이드 수행
  - 모든 중요 워크로드 및 사용자 정의 리소스 테스트
  - 자동화된 테스트 스위트 실행

- **API 호환성 확인:**
  - 사용 중인 API 버전 확인:
    ```bash
    kubectl api-resources -o wide
    ```
  - 더 이상 사용되지 않는 API 사용 확인:
    ```bash
    kubectl get -A | grep "deprecated"
    ```
  - 필요한 경우 매니페스트 업데이트

- **백업 및 복구 계획:**
  - etcd 데이터베이스 백업:
    ```bash
    ETCDCTL_API=3 etcdctl snapshot save snapshot.db
    ```
  - 모든 중요 매니페스트 백업:
    ```bash
    kubectl get all --all-namespaces -o yaml > all-resources.yaml
    ```
  - 복구 절차 문서화 및 테스트

- **점진적 업그레이드 접근 방식:**
  - **컨트롤 플레인 구성 요소 먼저 업그레이드:**
    - 고가용성 설정에서는 한 번에 하나의 컨트롤 플레인 노드 업그레이드
  - **워커 노드 롤링 업그레이드:**
    - 노드 그룹을 작은 배치로 나누어 업그레이드
    - 각 배치 후 안정성 확인

- **워크로드 보호:**
  - **PodDisruptionBudget 설정:**
    ```yaml
    apiVersion: policy/v1
    kind: PodDisruptionBudget
    metadata:
      name: app-pdb
    spec:
      minAvailable: 2  # 또는 maxUnavailable: 1
      selector:
        matchLabels:
          app: my-app
    ```
  - **노드 드레이닝 시 주의:**
    ```bash
    kubectl drain <노드_이름> --ignore-daemonsets --delete-emptydir-data
    ```

- **모니터링 강화:**
  - 업그레이드 전, 중, 후에 클러스터 상태 모니터링
  - 주요 메트릭 및 로그 집중 관찰
  - 알림 임계값 일시적 조정

- **롤백 계획:**
  - 롤백 트리거 조건 정의
  - 롤백 절차 문서화
  - 롤백에 필요한 모든 구성 요소 및 이미지 보존

- **커뮤니케이션 계획:**
  - 모든 이해관계자에게 업그레이드 일정 및 예상되는 영향 공지
  - 업그레이드 중 상태 업데이트 제공
  - 문제 발생 시 에스컬레이션 경로 정의

**3. 버전별 특별 고려 사항:**

- **마이너 버전 업그레이드(예: 1.24 → 1.25):**
  - 제거된 API 및 기능 변경에 특히 주의
  - 한 번에 한 마이너 버전씩 업그레이드

- **패치 버전 업그레이드(예: 1.24.0 → 1.24.1):**
  - 일반적으로 더 안전하지만 여전히 테스트 필요
  - 보안 패치의 경우 더 빠른 배포 고려
</details>

5. Kubernetes 클러스터에서 발생할 수 있는 일반적인 네트워킹 문제와 이를 진단하고 해결하는 방법을 설명하세요.

<details>
<summary>정답 보기</summary>

**정답:**

**Kubernetes 네트워킹 문제 진단 및 해결:**

**1. 포드 간 통신 문제:**

- **증상:**
  - 포드가 다른 포드와 통신할 수 없음
  - 서비스 이름으로 연결할 수 없음
  - 네트워크 타임아웃 오류

- **진단 방법:**
  - 네트워크 정책 확인:
    ```bash
    kubectl get networkpolicy --all-namespaces
    ```
  - 테스트 포드 생성하여 연결 테스트:
    ```bash
    kubectl run -it --rm debug --image=busybox -- sh
    # 포드 내에서
    ping <대상_포드_IP>
    wget -O- <서비스_이름>:<포트>
    ```
  - CNI 플러그인 포드 상태 확인:
    ```bash
    kubectl get pods -n kube-system | grep -E 'calico|flannel|weave|cilium'
    ```

- **해결 방법:**
  - CNI 플러그인 재설치 또는 업데이트
  - 네트워크 정책 수정 또는 제거
  - 노드 네트워크 인터페이스 확인
  - 방화벽 규칙 확인

**2. 서비스 디스커버리 및 DNS 문제:**

- **증상:**
  - 서비스 이름으로 연결할 수 없음
  - DNS 조회 실패
  - 간헐적인 연결 문제

- **진단 방법:**
  - CoreDNS 포드 상태 확인:
    ```bash
    kubectl get pods -n kube-system -l k8s-app=kube-dns
    kubectl logs -n kube-system -l k8s-app=kube-dns
    ```
  - DNS 조회 테스트:
    ```bash
    kubectl run -it --rm debug --image=busybox -- sh
    # 포드 내에서
    nslookup kubernetes.default.svc.cluster.local
    nslookup <서비스_이름>.<네임스페이스>.svc.cluster.local
    cat /etc/resolv.conf
    ```
  - 서비스 엔드포인트 확인:
    ```bash
    kubectl get endpoints <서비스_이름>
    ```

- **해결 방법:**
  - CoreDNS 포드 재시작:
    ```bash
    kubectl rollout restart deployment coredns -n kube-system
    ```
  - DNS 구성 확인 및 수정:
    ```bash
    kubectl edit configmap coredns -n kube-system
    ```
  - kubelet DNS 설정 확인

**3. 서비스 및 인그레스 문제:**

- **증상:**
  - 서비스에 외부에서 접근할 수 없음
  - 인그레스 규칙이 작동하지 않음
  - 로드 밸런서가 생성되지 않음

- **진단 방법:**
  - 서비스 상태 확인:
    ```bash
    kubectl describe service <서비스_이름>
    ```
  - 인그레스 상태 확인:
    ```bash
    kubectl describe ingress <인그레스_이름>
    ```
  - 인그레스 컨트롤러 포드 로그 확인:
    ```bash
    kubectl logs -n <인그레스_네임스페이스> <인그레스_컨트롤러_포드>
    ```
  - 엔드포인트 확인:
    ```bash
    kubectl get endpoints <서비스_이름>
    ```

- **해결 방법:**
  - 서비스 셀렉터와 포드 레이블 일치 확인
  - 인그레스 컨트롤러 재설치 또는 업데이트
  - 서비스 타입 및 포트 구성 확인
  - 클라우드 제공자 로드 밸런서 설정 확인

**4. 노드 네트워킹 문제:**

- **증상:**
  - 노드가 클러스터에서 분리됨
  - 노드 간 통신 실패
  - kubelet 연결 오류

- **진단 방법:**
  - 노드 상태 확인:
    ```bash
    kubectl describe node <노드_이름>
    ```
  - 노드 네트워크 인터페이스 확인:
    ```bash
    # 노드에서 직접
    ip addr
    ip route
    ```
  - 방화벽 규칙 확인:
    ```bash
    # 노드에서 직접
    iptables -L
    ```
  - kubelet 로그 확인:
    ```bash
    journalctl -u kubelet
    ```

- **해결 방법:**
  - 노드 네트워크 인터페이스 재구성
  - 방화벽 규칙 수정
  - kubelet 재시작
  - 필요한 경우 노드 재부팅

**5. 네트워크 정책 문제:**

- **증상:**
  - 예상치 못한 연결 차단
  - 특정 네임스페이스 간 통신 불가
  - 일부 포드만 접근 가능

- **진단 방법:**
  - 네트워크 정책 확인:
    ```bash
    kubectl get networkpolicy -A
    kubectl describe networkpolicy <정책_이름> -n <네임스페이스>
    ```
  - 포드 레이블 확인:
    ```bash
    kubectl get pods --show-labels
    ```
  - 네트워크 플러그인이 네트워크 정책을 지원하는지 확인

- **해결 방법:**
  - 네트워크 정책 수정 또는 삭제
  - 포드 레이블 수정
  - 네트워크 정책 디버깅 도구 사용

**6. 일반적인 네트워킹 디버깅 도구:**

- **네트워크 디버깅 포드:**
  ```yaml
  apiVersion: v1
  kind: Pod
  metadata:
    name: network-debug
  spec:
    containers:
    - name: debug
      image: nicolaka/netshoot
      command: ["sleep", "3600"]
  ```

- **유용한 명령어:**
  ```bash
  # 포드 내에서
  ping <IP>
  traceroute <IP>
  dig <서비스_이름>.<네임스페이스>.svc.cluster.local
  curl -v <URL>
  tcpdump -i any
  netstat -tuln
  ```

- **CNI 플러그인별 디버깅 도구:**
  - Calico: `calicoctl`
  - Cilium: `cilium`
  - Weave: `weave`

**7. 모범 사례:**

- 네트워크 토폴로지 문서화
- 정기적인 연결성 테스트 수행
- 네트워크 정책 변경 전 영향 분석
- 클러스터 네트워크 CIDR 범위 계획
- 네트워크 모니터링 도구 구현
</details>
## 실습 문제

1. 다음 요구 사항에 맞는 ResourceQuota 매니페스트를 작성하세요:
   - 네임스페이스: development
   - 최대 포드 수: 20
   - 최대 CPU 요청: 4 코어
   - 최대 메모리 요청: 8Gi
   - 최대 PVC 수: 10
   - 최대 스토리지 요청: 100Gi

<details>
<summary>정답 보기</summary>

**정답:**

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: dev-quota
  namespace: development
spec:
  hard:
    pods: "20"
    requests.cpu: "4"
    requests.memory: 8Gi
    persistentvolumeclaims: "10"
    requests.storage: 100Gi
```

이 ResourceQuota는 'development' 네임스페이스에 다음과 같은 제한을 설정합니다:
- 최대 20개의 포드
- 총 CPU 요청 4 코어
- 총 메모리 요청 8Gi
- 최대 10개의 PersistentVolumeClaim
- 총 스토리지 요청 100Gi

ResourceQuota를 적용하려면:
```bash
kubectl apply -f resource-quota.yaml
```

현재 할당량 사용량을 확인하려면:
```bash
kubectl describe quota dev-quota -n development
```

참고: ResourceQuota를 적용하려면 네임스페이스가 이미 존재해야 합니다. 네임스페이스가 없는 경우 먼저 생성해야 합니다:
```bash
kubectl create namespace development
```
</details>

2. 클러스터의 모든 노드에서 kubelet 서비스 상태를 확인하고, 문제가 있는 경우 해결하는 스크립트를 작성하세요.

<details>
<summary>정답 보기</summary>

**정답:**

```bash
#!/bin/bash
# 파일명: check_kubelet.sh
# 설명: 모든 노드에서 kubelet 서비스 상태를 확인하고 문제 해결

# 노드 목록 가져오기
NODES=$(kubectl get nodes -o jsonpath='{.items[*].metadata.name}')

# 각 노드에 대해 반복
for NODE in $NODES; do
  echo "===== 노드 확인: $NODE ====="
  
  # 노드 상태 확인
  NODE_STATUS=$(kubectl get node $NODE -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}')
  echo "노드 상태: $NODE_STATUS"
  
  # SSH를 통해 kubelet 상태 확인
  echo "kubelet 서비스 상태 확인 중..."
  ssh $NODE "sudo systemctl status kubelet | grep Active"
  
  # kubelet이 실행 중이 아니면 시작
  if ssh $NODE "sudo systemctl is-active kubelet" != "active"; then
    echo "kubelet이 실행 중이 아닙니다. 서비스 시작 중..."
    ssh $NODE "sudo systemctl start kubelet"
    
    # 시작 후 상태 다시 확인
    sleep 5
    if ssh $NODE "sudo systemctl is-active kubelet" == "active"; then
      echo "kubelet 서비스가 성공적으로 시작되었습니다."
    else
      echo "kubelet 서비스 시작 실패. 로그 확인 중..."
      ssh $NODE "sudo journalctl -u kubelet --no-pager -n 50"
    fi
  else
    echo "kubelet 서비스가 정상적으로 실행 중입니다."
  fi
  
  # kubelet 구성 확인
  echo "kubelet 구성 확인 중..."
  ssh $NODE "sudo cat /var/lib/kubelet/config.yaml | grep -E 'address|authentication|authorization'"
  
  echo "===== $NODE 확인 완료 ====="
  echo ""
done
```

이 스크립트는 다음 작업을 수행합니다:
1. `kubectl get nodes`를 사용하여 클러스터의 모든 노드 목록을 가져옵니다.
2. 각 노드에 대해:
   - 노드의 Ready 상태를 확인합니다.
   - SSH를 통해 노드에 연결하여 kubelet 서비스 상태를 확인합니다.
   - kubelet이 실행 중이 아니면 서비스를 시작합니다.
   - 서비스 시작 후 상태를 다시 확인합니다.
   - 시작에 실패한 경우 로그를 확인합니다.
   - kubelet 구성 파일의 주요 설정을 확인합니다.

**사용 방법:**
```bash
chmod +x check_kubelet.sh
./check_kubelet.sh
```

**참고 사항:**
- 이 스크립트를 실행하려면 모든 노드에 SSH 접근 권한이 필요합니다.
- 프로덕션 환경에서는 SSH 키 기반 인증을 사용하는 것이 좋습니다.
- 클라우드 환경에서는 노드에 직접 SSH 접근이 제한될 수 있으므로, 클라우드 제공자의 노드 관리 도구를 사용해야 할 수 있습니다.
</details>

3. 클러스터의 etcd 데이터베이스를 백업하고, 백업 파일을 안전한 위치에 저장하는 cron 작업을 설정하세요.

<details>
<summary>정답 보기</summary>

**정답:**

**1. 백업 스크립트 생성:**

```bash
#!/bin/bash
# 파일명: backup_etcd.sh
# 설명: etcd 데이터베이스 백업 및 원격 저장

# 변수 설정
BACKUP_DIR="/opt/etcd-backup"
REMOTE_BACKUP_DIR="/mnt/remote-storage/etcd-backups"
DATE=$(date +%Y%m%d-%H%M%S)
BACKUP_FILE="etcd-snapshot-$DATE.db"
ETCD_ENDPOINTS="https://127.0.0.1:2379"
ETCD_CACERT="/etc/kubernetes/pki/etcd/ca.crt"
ETCD_CERT="/etc/kubernetes/pki/etcd/server.crt"
ETCD_KEY="/etc/kubernetes/pki/etcd/server.key"
RETENTION_DAYS=7

# 백업 디렉토리 생성
mkdir -p $BACKUP_DIR

# etcd 스냅샷 생성
ETCDCTL_API=3 etcdctl snapshot save $BACKUP_DIR/$BACKUP_FILE \
  --endpoints=$ETCD_ENDPOINTS \
  --cacert=$ETCD_CACERT \
  --cert=$ETCD_CERT \
  --key=$ETCD_KEY

# 백업 성공 확인
if [ $? -eq 0 ]; then
  echo "etcd 백업 성공: $BACKUP_FILE"
  
  # 백업 파일 상태 확인
  ETCDCTL_API=3 etcdctl snapshot status $BACKUP_DIR/$BACKUP_FILE --write-out=table
  
  # 백업 파일 압축
  gzip $BACKUP_DIR/$BACKUP_FILE
  
  # 원격 저장소에 복사
  mkdir -p $REMOTE_BACKUP_DIR
  cp $BACKUP_DIR/$BACKUP_FILE.gz $REMOTE_BACKUP_DIR/
  
  # 오래된 백업 파일 정리 (로컬)
  find $BACKUP_DIR -name "etcd-snapshot-*.db.gz" -type f -mtime +$RETENTION_DAYS -delete
  
  # 오래된 백업 파일 정리 (원격)
  find $REMOTE_BACKUP_DIR -name "etcd-snapshot-*.db.gz" -type f -mtime +$RETENTION_DAYS -delete
  
  echo "백업 완료 및 원격 저장소에 복사됨: $REMOTE_BACKUP_DIR/$BACKUP_FILE.gz"
else
  echo "etcd 백업 실패"
  exit 1
fi
```

**2. 스크립트에 실행 권한 부여:**

```bash
chmod +x /opt/etcd-backup/backup_etcd.sh
```

**3. cron 작업 설정:**

```bash
# root 사용자의 crontab 편집
sudo crontab -e
```

다음 내용 추가:

```
# 매일 새벽 2시에 etcd 백업 실행
0 2 * * * /opt/etcd-backup/backup_etcd.sh >> /var/log/etcd-backup.log 2>&1
```

**4. 백업 로그 로테이션 설정:**

`/etc/logrotate.d/etcd-backup` 파일 생성:

```
/var/log/etcd-backup.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 root root
}
```

**5. 백업 테스트:**

```bash
sudo /opt/etcd-backup/backup_etcd.sh
```

**6. 백업 모니터링 설정 (선택 사항):**

백업 실패 시 알림을 받기 위해 모니터링 도구(예: Prometheus)와 통합할 수 있습니다. 백업 스크립트에 다음과 같은 코드를 추가할 수 있습니다:

```bash
# 백업 성공 여부를 나타내는 파일 생성
if [ $? -eq 0 ]; then
  echo "success" > /var/lib/node_exporter/etcd_backup_status.prom
else
  echo "failure" > /var/lib/node_exporter/etcd_backup_status.prom
fi
```

**참고 사항:**
- 백업 파일은 클러스터 외부의 안전한 위치에 저장해야 합니다.
- 클라우드 환경에서는 S3, GCS 등의 객체 스토리지를 사용하는 것이 좋습니다.
- 정기적으로 백업 복원 테스트를 수행하여 백업의 유효성을 확인해야 합니다.
- 고가용성 etcd 클러스터의 경우 하나의 etcd 인스턴스에서만 백업을 수행하면 됩니다.
</details>
4. 클러스터의 모든 노드에 대해 롤링 업데이트를 수행하는 절차를 작성하세요. 업데이트 중에도 워크로드 가용성을 유지해야 합니다.

<details>
<summary>정답 보기</summary>

**정답:**

**노드 롤링 업데이트 절차:**

```bash
#!/bin/bash
# 파일명: node_rolling_update.sh
# 설명: 클러스터 노드 롤링 업데이트 수행

# 변수 설정
UPGRADE_COMMAND="sudo apt update && sudo apt upgrade -y"
REBOOT_REQUIRED_CHECK="[ -f /var/run/reboot-required ]"
MAX_UNAVAILABLE=1  # 한 번에 업데이트할 노드 수

# 클러스터 상태 확인
echo "클러스터 상태 확인 중..."
kubectl get nodes
kubectl get pods --all-namespaces -o wide

# PodDisruptionBudget 확인
echo "PodDisruptionBudget 확인 중..."
kubectl get poddisruptionbudget --all-namespaces

# 노드 목록 가져오기
NODES=$(kubectl get nodes -o jsonpath='{.items[*].metadata.name}')
NODE_COUNT=$(echo $NODES | wc -w)

echo "총 $NODE_COUNT 개의 노드를 업데이트합니다."
echo "노드 목록: $NODES"
echo "한 번에 최대 $MAX_UNAVAILABLE 개의 노드가 업데이트됩니다."
echo "계속하려면 Enter 키를 누르세요. 취소하려면 Ctrl+C를 누르세요."
read

# 각 노드에 대해 반복
for NODE in $NODES; do
  echo "===== 노드 업데이트: $NODE ====="
  
  # 노드 cordon
  echo "노드 cordon 중..."
  kubectl cordon $NODE
  
  # 노드 drain
  echo "노드 drain 중..."
  kubectl drain $NODE --ignore-daemonsets --delete-emptydir-data --force
  
  # 노드 업데이트
  echo "노드 업데이트 중..."
  ssh $NODE "$UPGRADE_COMMAND"
  
  # 재부팅 필요 여부 확인
  REBOOT_REQUIRED=$(ssh $NODE "$REBOOT_REQUIRED_CHECK && echo 'true' || echo 'false'")
  
  if [ "$REBOOT_REQUIRED" == "true" ]; then
    echo "노드 재부팅 필요. 재부팅 중..."
    ssh $NODE "sudo reboot"
    
    # 노드가 다시 Ready 상태가 될 때까지 대기
    echo "노드 재부팅 중. Ready 상태가 될 때까지 대기 중..."
    while true; do
      STATUS=$(kubectl get node $NODE -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}')
      if [ "$STATUS" == "True" ]; then
        echo "노드가 Ready 상태가 되었습니다."
        break
      fi
      echo "노드가 아직 Ready 상태가 아닙니다. 10초 후 다시 확인합니다."
      sleep 10
    done
  else
    echo "노드 재부팅이 필요하지 않습니다."
  fi
  
  # 노드 uncordon
  echo "노드 uncordon 중..."
  kubectl uncordon $NODE
  
  # 노드 상태 확인
  echo "노드 상태 확인 중..."
  kubectl get node $NODE
  
  # 포드가 노드에 다시 스케줄링될 때까지 대기
  echo "포드가 노드에 다시 스케줄링될 때까지 대기 중..."
  sleep 30
  
  # 클러스터 상태 확인
  echo "클러스터 상태 확인 중..."
  kubectl get pods --all-namespaces -o wide | grep $NODE
  
  echo "===== $NODE 업데이트 완료 ====="
  echo ""
  
  # 다음 노드로 진행하기 전에 사용자 확인 (선택 사항)
  echo "다음 노드로 진행하려면 Enter 키를 누르세요. 취소하려면 Ctrl+C를 누르세요."
  read
done

echo "모든 노드 업데이트 완료!"
kubectl get nodes
```

**롤링 업데이트 전 준비 사항:**

1. **PodDisruptionBudget 설정:**
   중요 워크로드에 대해 PDB를 설정하여 가용성을 보장합니다.
   
   ```yaml
   apiVersion: policy/v1
   kind: PodDisruptionBudget
   metadata:
     name: app-pdb
     namespace: default
   spec:
     minAvailable: 2  # 또는 maxUnavailable: 1
     selector:
       matchLabels:
         app: my-app
   ```

2. **충분한 리소스 확보:**
   노드 하나가 제거되어도 나머지 노드가 모든 워크로드를 처리할 수 있는지 확인합니다.

3. **백업 수행:**
   업데이트 전에 etcd 데이터베이스 백업을 수행합니다.

**롤링 업데이트 모범 사례:**

1. **점진적 접근:**
   - 한 번에 하나의 노드만 업데이트
   - 각 노드 업데이트 후 클러스터 상태 확인

2. **자동화 및 멱등성:**
   - 스크립트를 사용하여 프로세스 자동화
   - 실패 시 안전하게 재시도할 수 있도록 설계

3. **모니터링 강화:**
   - 업데이트 중 클러스터 메트릭 모니터링
   - 애플리케이션 상태 및 성능 모니터링

4. **롤백 계획:**
   - 문제 발생 시 롤백 절차 준비
   - 이전 상태로 복원할 수 있는 방법 확보

5. **커뮤니케이션:**
   - 업데이트 일정 및 예상되는 영향 공지
   - 업데이트 진행 상황 정기적으로 보고

**참고 사항:**
- 클라우드 환경에서는 관리형 Kubernetes 서비스(EKS, GKE, AKS 등)의 노드 업데이트 기능을 활용할 수 있습니다.
- 노드 그룹이 여러 개인 경우 그룹별로 업데이트를 수행합니다.
- 중요 시스템 포드(CoreDNS, kube-proxy 등)의 상태를 특별히 모니터링합니다.
</details>

5. 클러스터에서 리소스 사용량이 높은 포드를 식별하고, 해당 정보를 보고서로 생성하는 스크립트를 작성하세요.

<details>
<summary>정답 보기</summary>

**정답:**

```bash
#!/bin/bash
# 파일명: resource_usage_report.sh
# 설명: 클러스터의 리소스 사용량이 높은 포드 식별 및 보고서 생성

# 변수 설정
REPORT_DIR="/tmp/k8s-reports"
DATE=$(date +%Y%m%d-%H%M%S)
REPORT_FILE="$REPORT_DIR/resource-usage-report-$DATE.txt"
TOP_N=10  # 상위 N개 포드 표시

# 보고서 디렉토리 생성
mkdir -p $REPORT_DIR

# 보고서 헤더 작성
echo "===== Kubernetes 클러스터 리소스 사용량 보고서 =====" > $REPORT_FILE
echo "생성 시간: $(date)" >> $REPORT_FILE
echo "" >> $REPORT_FILE

# 클러스터 정보 추가
echo "===== 클러스터 정보 =====" >> $REPORT_FILE
kubectl cluster-info >> $REPORT_FILE 2>&1
echo "" >> $REPORT_FILE

# 노드 리소스 사용량
echo "===== 노드 리소스 사용량 =====" >> $REPORT_FILE
kubectl top nodes | sort -k 3 -hr >> $REPORT_FILE
echo "" >> $REPORT_FILE

# CPU 사용량이 높은 상위 포드
echo "===== CPU 사용량 상위 $TOP_N 포드 =====" >> $REPORT_FILE
kubectl top pods --all-namespaces | sort -k 3 -hr | head -n $((TOP_N + 1)) >> $REPORT_FILE
echo "" >> $REPORT_FILE

# 메모리 사용량이 높은 상위 포드
echo "===== 메모리 사용량 상위 $TOP_N 포드 =====" >> $REPORT_FILE
kubectl top pods --all-namespaces | sort -k 4 -hr | head -n $((TOP_N + 1)) >> $REPORT_FILE
echo "" >> $REPORT_FILE

# 네임스페이스별 리소스 사용량
echo "===== 네임스페이스별 리소스 사용량 =====" >> $REPORT_FILE
echo "CPU 사용량 (코어):" >> $REPORT_FILE
kubectl top pods --all-namespaces | tail -n +2 | awk '{print $2, $3}' | sed 's/m//' | awk '{ns[$1] += $2} END {for (namespace in ns) print namespace, ns[namespace]/1000}' | sort -k 2 -hr >> $REPORT_FILE
echo "" >> $REPORT_FILE

echo "메모리 사용량 (GiB):" >> $REPORT_FILE
kubectl top pods --all-namespaces | tail -n +2 | awk '{print $2, $4}' | sed 's/Mi//' | awk '{ns[$1] += $2} END {for (namespace in ns) print namespace, ns[namespace]/1024}' | sort -k 2 -hr >> $REPORT_FILE
echo "" >> $REPORT_FILE

# 리소스 요청 대비 사용량이 높은 포드 식별
echo "===== 리소스 요청 대비 사용량이 높은 포드 =====" >> $REPORT_FILE
echo "포드 정보 수집 중..." >> $REPORT_FILE

# 임시 파일 생성
PODS_USAGE_FILE="$REPORT_DIR/pods-usage-$DATE.tmp"
PODS_REQUESTS_FILE="$REPORT_DIR/pods-requests-$DATE.tmp"

# 현재 사용량 수집
kubectl top pods --all-namespaces | tail -n +2 > $PODS_USAGE_FILE

# 모든 네임스페이스의 포드 리소스 요청 수집
echo "네임스페이스,포드,CPU요청(m),메모리요청(Mi)" > $PODS_REQUESTS_FILE
for ns in $(kubectl get ns -o jsonpath='{.items[*].metadata.name}'); do
  kubectl get pods -n $ns -o jsonpath='{range .items[*]}{.metadata.namespace},{.metadata.name},{range .spec.containers[*]}{.resources.requests.cpu}{","}{.resources.requests.memory}{"\n"}{end}{end}' | sed 's/$/,/' | sed 's/,$//' >> $PODS_REQUESTS_FILE
done

# 리소스 요청 대비 사용량 계산 및 보고서에 추가
echo "CPU 사용률이 높은 포드 (사용량/요청 > 80%):" >> $REPORT_FILE
while read line; do
  ns=$(echo $line | awk '{print $1}')
  pod=$(echo $line | awk '{print $2}')
  cpu_usage=$(echo $line | awk '{print $3}' | sed 's/m//')
  
  # 해당 포드의 CPU 요청 찾기
  cpu_request=$(grep "$ns,$pod," $PODS_REQUESTS_FILE | awk -F, '{print $3}' | sed 's/[^0-9m.]//g' | sed 's/m//')
  
  # CPU 요청이 없으면 "미설정"으로 표시
  if [ -z "$cpu_request" ] || [ "$cpu_request" == "" ]; then
    echo "$ns/$pod: CPU 사용량 ${cpu_usage}m, 요청 미설정" >> $REPORT_FILE
  else
    # CPU 사용률 계산
    cpu_percentage=$(echo "scale=2; $cpu_usage / $cpu_request * 100" | bc)
    
    # 사용률이 80% 이상인 경우만 표시
    if (( $(echo "$cpu_percentage >= 80" | bc -l) )); then
      echo "$ns/$pod: CPU 사용량 ${cpu_usage}m, 요청 ${cpu_request}m, 사용률 ${cpu_percentage}%" >> $REPORT_FILE
    fi
  fi
done < $PODS_USAGE_FILE

echo "" >> $REPORT_FILE
echo "메모리 사용률이 높은 포드 (사용량/요청 > 80%):" >> $REPORT_FILE
while read line; do
  ns=$(echo $line | awk '{print $1}')
  pod=$(echo $line | awk '{print $2}')
  mem_usage=$(echo $line | awk '{print $4}' | sed 's/Mi//')
  
  # 해당 포드의 메모리 요청 찾기
  mem_request=$(grep "$ns,$pod," $PODS_REQUESTS_FILE | awk -F, '{print $4}' | sed 's/[^0-9Mi.]//g' | sed 's/Mi//')
  
  # 메모리 요청이 없으면 "미설정"으로 표시
  if [ -z "$mem_request" ] || [ "$mem_request" == "" ]; then
    echo "$ns/$pod: 메모리 사용량 ${mem_usage}Mi, 요청 미설정" >> $REPORT_FILE
  else
    # 메모리 사용률 계산
    mem_percentage=$(echo "scale=2; $mem_usage / $mem_request * 100" | bc)
    
    # 사용률이 80% 이상인 경우만 표시
    if (( $(echo "$mem_percentage >= 80" | bc -l) )); then
      echo "$ns/$pod: 메모리 사용량 ${mem_usage}Mi, 요청 ${mem_request}Mi, 사용률 ${mem_percentage}%" >> $REPORT_FILE
    fi
  fi
done < $PODS_USAGE_FILE

echo "" >> $REPORT_FILE

# 리소스 요청이 설정되지 않은 포드 식별
echo "===== 리소스 요청이 설정되지 않은 포드 =====" >> $REPORT_FILE
kubectl get pods --all-namespaces -o json | jq -r '.items[] | select((.spec.containers[].resources.requests.cpu == null) or (.spec.containers[].resources.requests.memory == null)) | .metadata.namespace + "/" + .metadata.name' >> $REPORT_FILE
echo "" >> $REPORT_FILE

# 임시 파일 정리
rm -f $PODS_USAGE_FILE $PODS_REQUESTS_FILE

# 보고서 요약
echo "===== 보고서 요약 =====" >> $REPORT_FILE
echo "총 노드 수: $(kubectl get nodes | tail -n +2 | wc -l)" >> $REPORT_FILE
echo "총 포드 수: $(kubectl get pods --all-namespaces | tail -n +2 | wc -l)" >> $REPORT_FILE
echo "총 네임스페이스 수: $(kubectl get ns | tail -n +2 | wc -l)" >> $REPORT_FILE
echo "보고서 생성 완료: $REPORT_FILE" >> $REPORT_FILE

# 보고서 위치 출력
echo "보고서가 생성되었습니다: $REPORT_FILE"

# HTML 보고서 생성 (선택 사항)
HTML_REPORT="${REPORT_FILE%.txt}.html"
echo "<html><head><title>Kubernetes 리소스 사용량 보고서</title>" > $HTML_REPORT
echo "<style>body{font-family:Arial;margin:20px}h1{color:#326ce5}table{border-collapse:collapse;width:100%}th,td{border:1px solid #ddd;padding:8px}th{background-color:#f2f2f2}</style>" >> $HTML_REPORT
echo "</head><body>" >> $HTML_REPORT
echo "<h1>Kubernetes 클러스터 리소스 사용량 보고서</h1>" >> $HTML_REPORT
echo "<p>생성 시간: $(date)</p>" >> $HTML_REPORT

# 보고서 내용을 HTML로 변환
awk '/===== 클러스터 정보 =====/{flag=1;print "<h2>클러스터 정보</h2><pre>"}/===== 노드 리소스 사용량 =====/{flag=0;print "</pre><h2>노드 리소스 사용량</h2><table><tr><th>노드</th><th>CPU(%)</th><th>메모리(%)</th></tr>"}/===== CPU 사용량 상위/{flag=0;print "</table><h2>CPU 사용량 상위 포드</h2><table><tr><th>네임스페이스</th><th>포드</th><th>CPU(m)</th><th>메모리(Mi)</th></tr>"}/===== 메모리 사용량 상위/{flag=0;print "</table><h2>메모리 사용량 상위 포드</h2><table><tr><th>네임스페이스</th><th>포드</th><th>CPU(m)</th><th>메모리(Mi)</th></tr>"}/===== 네임스페이스별 리소스 사용량 =====/{flag=0;print "</table><h2>네임스페이스별 리소스 사용량</h2>"}/CPU 사용량 \(코어\):/{flag=0;print "<h3>CPU 사용량 (코어)</h3><table><tr><th>네임스페이스</th><th>CPU(코어)</th></tr>"}/메모리 사용량 \(GiB\):/{flag=0;print "</table><h3>메모리 사용량 (GiB)</h3><table><tr><th>네임스페이스</th><th>메모리(GiB)</th></tr>"}/===== 리소스 요청 대비 사용량이 높은 포드 =====/{flag=0;print "</table><h2>리소스 요청 대비 사용량이 높은 포드</h2>"}/CPU 사용률이 높은 포드/{flag=0;print "<h3>CPU 사용률이 높은 포드 (사용량/요청 > 80%)</h3><ul>"}/메모리 사용률이 높은 포드/{flag=0;print "</ul><h3>메모리 사용률이 높은 포드 (사용량/요청 > 80%)</h3><ul>"}/===== 리소스 요청이 설정되지 않은 포드 =====/{flag=0;print "</ul><h2>리소스 요청이 설정되지 않은 포드</h2><ul>"}/===== 보고서 요약 =====/{flag=0;print "</ul><h2>보고서 요약</h2><ul>"}{if(flag==1)print;else if($0 ~ /^NAME/){print "<tr>";for(i=1;i<=NF;i++)print "<th>"$i"</th>";print "</tr>"}else if($0 ~ /^[a-z].*[0-9]%/){print "<tr>";for(i=1;i<=NF;i++)print "<td>"$i"</td>";print "</tr>"}else if($0 ~ /^[a-z].*[0-9]m/){print "<tr>";for(i=1;i<=NF;i++)print "<td>"$i"</td>";print "</tr>"}else if($0 ~ /^[a-z].* [0-9]/){print "<tr><td>"$1"</td><td>"$2"</td></tr>"}else if($0 ~ /^[a-z].*\//){print "<li>"$0"</li>"}else if($0 ~ /^총/){print "<li>"$0"</li>"}}' $REPORT_FILE >> $HTML_REPORT

echo "</ul></body></html>" >> $HTML_REPORT
echo "HTML 보고서가 생성되었습니다: $HTML_REPORT"
```

**스크립트 사용 방법:**
```bash
chmod +x resource_usage_report.sh
./resource_usage_report.sh
```

**스크립트 기능:**
1. 클러스터 정보 수집
2. 노드 리소스 사용량 수집
3. CPU 및 메모리 사용량이 높은 상위 포드 식별
4. 네임스페이스별 리소스 사용량 계산
5. 리소스 요청 대비 사용량이 높은 포드 식별
6. 리소스 요청이 설정되지 않은 포드 식별
7. 텍스트 및 HTML 형식의 보고서 생성

**참고 사항:**
- 이 스크립트를 실행하려면 `kubectl`, `jq`, `bc` 도구가 필요합니다.
- Metrics Server가 클러스터에 설치되어 있어야 합니다.
- 대규모 클러스터에서는 스크립트 실행 시간이 길어질 수 있습니다.
- 정기적인 보고서 생성을 위해 cron 작업으로 설정할 수 있습니다.
- 보고서를 이메일로 전송하거나 모니터링 시스템과 통합할 수 있습니다.
</details>
## 고급 주제

1. Kubernetes 클러스터에서 etcd 성능 최적화를 위한 주요 설정 매개변수와 모범 사례는 무엇인가요?
   - A) `--max-request-bytes`, `--quota-backend-bytes`, 정기적인 압축
   - B) `--max-concurrent-requests`, `--max-connections`, 디스크 RAID 구성
   - C) `--auto-compaction-retention`, `--snapshot-count`, SSD 스토리지 사용
   - D) `--max-txn-ops`, `--max-result-buffer`, 메모리 증설

<details>
<summary>정답 보기</summary>

**정답: C) `--auto-compaction-retention`, `--snapshot-count`, SSD 스토리지 사용**

**설명:**
etcd는 Kubernetes 클러스터의 핵심 데이터 저장소로, 그 성능은 전체 클러스터 성능에 직접적인 영향을 미칩니다. etcd 성능 최적화를 위한 주요 설정 매개변수와 모범 사례는 다음과 같습니다:

1. **`--auto-compaction-retention`**: etcd는 모든 변경 사항의 기록을 유지하는 append-only 저장소입니다. 이 매개변수는 이전 버전의 키를 자동으로 압축하는 주기를 설정합니다. 기본값은 0(비활성화)이지만, 프로덕션 환경에서는 일반적으로 1시간(1h) 또는 24시간(24h)으로 설정합니다. 이를 통해 디스크 공간을 절약하고 성능을 향상시킬 수 있습니다.

2. **`--snapshot-count`**: etcd가 스냅샷을 생성하기 전에 커밋할 트랜잭션 수를 지정합니다. 기본값은 100,000이지만, 대규모 클러스터에서는 이 값을 조정하여 스냅샷 생성 빈도를 최적화할 수 있습니다. 값이 작을수록 스냅샷이 더 자주 생성되어 복구 시간이 단축되지만, 디스크 I/O가 증가합니다.

3. **SSD 스토리지 사용**: etcd는 디스크 I/O에 민감하므로, SSD(Solid State Drive)를 사용하면 성능이 크게 향상됩니다. 특히 대규모 클러스터에서는 SSD 사용이 필수적입니다.

기타 중요한 최적화 설정 및 모범 사례:

- **전용 디스크 사용**: etcd 데이터를 위한 전용 디스크를 사용하여 다른 애플리케이션과의 I/O 경합을 방지합니다.
- **적절한 메모리 할당**: etcd는 성능을 위해 데이터를 메모리에 캐시하므로, 충분한 메모리를 할당해야 합니다.
- **클러스터 크기 최적화**: 일반적으로 3-5개의 etcd 멤버가 최적의 성능과 가용성을 제공합니다.
- **네트워크 지연 시간 최소화**: etcd 멤버 간의 네트워크 지연 시간을 최소화하기 위해 동일한 데이터 센터 또는 가용 영역에 배치합니다.
- **정기적인 백업 및 압축**: 데이터 안전성을 보장하고 디스크 공간을 효율적으로 사용하기 위해 정기적인 백업과 압축을 수행합니다.

`--max-request-bytes`와 `--quota-backend-bytes`는 실제 etcd 매개변수이지만, 주로 성능보다는 리소스 제한에 관련됩니다. `--max-concurrent-requests`, `--max-connections`, `--max-txn-ops`, `--max-result-buffer`는 실제 etcd 매개변수가 아니거나 성능 최적화의 주요 요소가 아닙니다.
</details>

2. Kubernetes 클러스터에서 컨트롤 플레인 고가용성(HA)을 구현하는 가장 효과적인 방법은 무엇인가요?
   - A) 단일 마스터 노드에 여러 API 서버 인스턴스 실행
   - B) 여러 마스터 노드와 로드 밸런서를 사용한 etcd 클러스터 구성
   - C) API 서버를 StatefulSet으로 배포하고 PersistentVolume 사용
   - D) 마스터 노드에 자동 복구 기능이 있는 감시 프로세스 구현

<details>
<summary>정답 보기</summary>

**정답: B) 여러 마스터 노드와 로드 밸런서를 사용한 etcd 클러스터 구성**

**설명:**
Kubernetes 컨트롤 플레인의 고가용성(HA)을 구현하는 가장 효과적인 방법은 여러 마스터 노드와 로드 밸런서를 사용하여 etcd 클러스터를 구성하는 것입니다. 이 접근 방식은 다음과 같은 구성 요소로 이루어집니다:

1. **여러 마스터 노드**: 일반적으로 3개 또는 5개의 마스터 노드를 서로 다른 가용 영역에 배포하여 단일 장애점을 제거합니다. 각 마스터 노드는 다음 컨트롤 플레인 구성 요소를 실행합니다:
   - kube-apiserver: API 요청을 처리하는 서버
   - kube-controller-manager: 컨트롤러 프로세스 실행
   - kube-scheduler: 포드 스케줄링 결정

2. **etcd 클러스터**: etcd는 분산 키-값 저장소로, Kubernetes의 모든 클러스터 데이터를 저장합니다. 고가용성을 위해 일반적으로 3개 또는 5개의 etcd 인스턴스를 실행합니다. etcd는 마스터 노드에서 직접 실행하거나 별도의 전용 노드에서 실행할 수 있습니다.

3. **로드 밸런서**: 클라이언트 요청을 여러 kube-apiserver 인스턴스에 분산하기 위한 로드 밸런서가 필요합니다. 이는 일반적으로 클라우드 제공자의 로드 밸런서 서비스나 HAProxy, Nginx 등의 소프트웨어 로드 밸런서를 사용하여 구현합니다.

이 구성의 주요 이점:
- **내결함성**: 하나의 마스터 노드가 실패해도 클러스터는 계속 작동합니다.
- **고가용성**: 여러 가용 영역에 걸쳐 배포하면 데이터 센터 수준의 장애에도 대응할 수 있습니다.
- **확장성**: API 서버 요청을 여러 인스턴스에 분산하여 처리할 수 있습니다.
- **데이터 일관성**: etcd의 Raft 합의 알고리즘을 통해 데이터 일관성을 보장합니다.

다른 옵션들의 문제점:
- 단일 마스터 노드에 여러 API 서버 인스턴스를 실행하는 것은 노드 자체가 단일 장애점이 됩니다.
- API 서버를 StatefulSet으로 배포하는 것은 일반적인 접근 방식이 아니며, 컨트롤 플레인 구성 요소는 일반적으로 Kubernetes 외부에서 관리됩니다.
- 감시 프로세스는 도움이 될 수 있지만, 그 자체로는 진정한 고가용성 솔루션이 아닙니다.
</details>

3. Kubernetes 클러스터에서 감사 로깅(Audit Logging)을 구성할 때 가장 중요한 고려 사항은 무엇인가요?
   - A) 모든 API 요청을 로깅하여 완전한 감사 추적 보장
   - B) 감사 정책을 사용하여 중요한 이벤트만 선택적으로 로깅
   - C) 감사 로그를 외부 SIEM 시스템으로 실시간 전송
   - D) 감사 로그에 대한 접근을 관리자로 제한

<details>
<summary>정답 보기</summary>

**정답: B) 감사 정책을 사용하여 중요한 이벤트만 선택적으로 로깅**

**설명:**
Kubernetes 감사 로깅(Audit Logging)을 구성할 때 가장 중요한 고려 사항은 감사 정책을 사용하여 중요한 이벤트만 선택적으로 로깅하는 것입니다. 이는 다음과 같은 이유로 중요합니다:

1. **성능 영향 최소화**: 모든 API 요청을 로깅하면 API 서버에 상당한 부하가 발생하고 성능이 저하될 수 있습니다. 특히 대규모 클러스터에서는 초당 수천 개의 API 요청이 발생할 수 있습니다.

2. **스토리지 효율성**: 모든 이벤트를 로깅하면 로그 데이터의 양이 급격히 증가하여 스토리지 비용이 증가하고 로그 분석이 어려워집니다.

3. **관련 정보 집중**: 중요한 이벤트만 로깅함으로써 보안 분석가가 중요한 정보에 집중할 수 있습니다.

4. **규정 준수**: 많은 규정 준수 요구 사항은 모든 이벤트가 아닌 특정 유형의 이벤트 로깅을 요구합니다.

Kubernetes 감사 정책은 다음과 같은 감사 수준을 지원합니다:

- **None**: 이벤트를 로깅하지 않습니다.
- **Metadata**: 요청 메타데이터(사용자, 타임스탬프, 리소스, 동작 등)만 로깅하고 요청/응답 본문은 제외합니다.
- **Request**: 메타데이터와 요청 본문은 로깅하지만 응답 본문은 제외합니다.
- **RequestResponse**: 메타데이터, 요청 본문, 응답 본문을 모두 로깅합니다.

효과적인 감사 정책의 예:
```yaml
apiVersion: audit.k8s.io/v1
kind: Policy
rules:
# 인증 및 권한 부여 요청에 대한 로깅 수준 설정
- level: Metadata
  users: ["system:anonymous"]
  verbs: ["get", "list", "watch"]

# Secret, ConfigMap 등 민감한 리소스에 대한 변경 사항 자세히 로깅
- level: Request
  resources:
  - group: ""
    resources: ["secrets", "configmaps"]
  verbs: ["create", "update", "patch", "delete"]

# 중요한 리소스 변경 사항 자세히 로깅
- level: RequestResponse
  resources:
  - group: ""
    resources: ["pods"]
  verbs: ["create", "update", "patch", "delete"]

# 기본적으로 메타데이터만 로깅
- level: Metadata
```

다른 옵션들의 문제점:
- 모든 API 요청을 로깅하는 것은 성능 및 스토리지 문제를 일으킬 수 있습니다.
- 외부 SIEM 시스템으로의 실시간 전송은 중요하지만, 로깅할 내용을 결정하는 것보다 우선순위가 낮습니다.
- 감사 로그에 대한 접근 제한은 중요하지만, 로깅 정책 자체보다는 보안 조치에 해당합니다.
</details>

4. Kubernetes 클러스터에서 노드 자동 복구(Node Auto-Repair)를 구현하는 가장 효과적인 방법은 무엇인가요?
   - A) 노드 상태를 모니터링하고 문제가 있는 노드를 자동으로 재부팅하는 DaemonSet 배포
   - B) 클라우드 제공자의 관리형 노드 그룹 및 자동 복구 기능 활용
   - C) Node Problem Detector와 사용자 정의 컨트롤러를 사용한 노드 상태 모니터링 및 복구
   - D) 노드 상태를 주기적으로 확인하고 문제가 있는 노드를 재생성하는 cron 작업 구현

<details>
<summary>정답 보기</summary>

**정답: C) Node Problem Detector와 사용자 정의 컨트롤러를 사용한 노드 상태 모니터링 및 복구**

**설명:**
Kubernetes 클러스터에서 노드 자동 복구(Node Auto-Repair)를 구현하는 가장 효과적인 방법은 Node Problem Detector와 사용자 정의 컨트롤러를 함께 사용하는 것입니다. 이 접근 방식은 다음과 같은 이점을 제공합니다:

1. **정확한 문제 감지**: Node Problem Detector(NPD)는 다양한 노드 문제를 감지할 수 있는 특수 목적의 도구입니다. 이는 다음과 같은 문제를 감지할 수 있습니다:
   - 커널 오류 및 충돌
   - 하드웨어 문제
   - 파일 시스템 문제
   - 네트워크 문제
   - 리소스 부족 문제

2. **유연한 대응**: 사용자 정의 컨트롤러를 사용하면 감지된 문제에 대해 다양한 복구 전략을 구현할 수 있습니다:
   - 경미한 문제: 노드 재부팅
   - 심각한 문제: 노드 교체
   - 특정 유형의 문제: 특정 서비스 재시작

3. **Kubernetes 네이티브 통합**: NPD는 노드 상태를 NodeCondition으로 보고하므로, 기존 Kubernetes 메커니즘과 잘 통합됩니다.

4. **클라우드 독립적**: 이 접근 방식은 모든 환경(온프레미스, 다양한 클라우드 제공자)에서 작동합니다.

구현 단계:

1. **Node Problem Detector 배포**:
   ```bash
   kubectl apply -f https://raw.githubusercontent.com/kubernetes/node-problem-detector/master/deployment/node-problem-detector.yaml
   ```

2. **사용자 정의 컨트롤러 구현**:
   - Kubernetes 이벤트 및 노드 상태 변경을 감시
   - 특정 NodeCondition에 대응하는 로직 구현
   - 복구 작업 수행(SSH를 통한 명령 실행, 클라우드 API를 통한 노드 재생성 등)

3. **알림 및 로깅 설정**:
   - 복구 작업에 대한 알림 구성
   - 문제 및 복구 작업 로깅

다른 옵션들의 문제점:

- **DaemonSet 접근 방식**: 노드에 심각한 문제가 있는 경우 DaemonSet 자체가 영향을 받을 수 있으며, 모든 유형의 문제를 감지하기 어렵습니다.

- **클라우드 제공자의 관리형 노드 그룹**: 특정 클라우드 제공자에 종속되며, 온프레미스 환경에서는 사용할 수 없습니다. 또한 감지할 수 있는 문제 유형이 제한적일 수 있습니다.

- **cron 작업 접근 방식**: 반응 시간이 느리고, 문제 감지 능력이 제한적이며, 클러스터 외부에서 실행되어야 하는 단점이 있습니다.

Node Problem Detector와 사용자 정의 컨트롤러를 결합하면 다양한 환경에서 작동하는 강력하고 유연한 노드 자동 복구 솔루션을 구현할 수 있습니다.
</details>

5. Kubernetes 클러스터에서 RBAC(Role-Based Access Control)를 효과적으로 관리하기 위한 모범 사례는 무엇인가요?
   - A) 모든 사용자에게 cluster-admin 역할을 부여하여 관리 용이성 확보
   - B) 네임스페이스별로 세분화된 역할을 정의하고 최소 권한 원칙 적용
   - C) 모든 권한을 단일 ClusterRole에 통합하여 일관성 유지
   - D) 인증을 위해 서비스 계정 대신 항상 사용자 인증서 사용

<details>
<summary>정답 보기</summary>

**정답: B) 네임스페이스별로 세분화된 역할을 정의하고 최소 권한 원칙 적용**

**설명:**
Kubernetes 클러스터에서 RBAC(Role-Based Access Control)를 효과적으로 관리하기 위한 모범 사례는 네임스페이스별로 세분화된 역할을 정의하고 최소 권한 원칙을 적용하는 것입니다. 이 접근 방식은 다음과 같은 이점을 제공합니다:

1. **최소 권한 원칙**: 사용자와 서비스 계정에 필요한 최소한의 권한만 부여하여 보안 위험을 최소화합니다. 이는 의도하지 않은 변경이나 악의적인 행위로부터 클러스터를 보호하는 데 도움이 됩니다.

2. **네임스페이스 격리**: 네임스페이스별로 역할을 정의하면 팀이나 애플리케이션 간의 논리적 격리를 강화할 수 있습니다. 이를 통해 한 팀의 실수가 다른 팀의 리소스에 영향을 미치는 것을 방지할 수 있습니다.

3. **세분화된 접근 제어**: 특정 리소스 유형이나 작업에 대한 권한을 세밀하게 제어할 수 있습니다. 예를 들어, 개발자에게는 포드와 서비스를 관리할 수 있는 권한을 부여하되, 시크릿이나 네임스페이스 자체를 수정할 수 있는 권한은 제한할 수 있습니다.

4. **감사 용이성**: 세분화된 역할을 사용하면 누가 어떤 작업을 수행할 수 있는지 명확하게 문서화되므로, 감사 및 규정 준수가 용이해집니다.

RBAC 모범 사례 구현 예시:

1. **네임스페이스별 역할 정의**:
   ```yaml
   apiVersion: rbac.authorization.k8s.io/v1
   kind: Role
   metadata:
     name: developer
     namespace: development
   rules:
   - apiGroups: [""]
     resources: ["pods", "services", "configmaps"]
     verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
   - apiGroups: ["apps"]
     resources: ["deployments", "replicasets"]
     verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
   - apiGroups: [""]
     resources: ["secrets"]
     verbs: ["get", "list", "watch"]  # 시크릿 읽기만 허용
   ```

2. **역할 바인딩 생성**:
   ```yaml
   apiVersion: rbac.authorization.k8s.io/v1
   kind: RoleBinding
   metadata:
     name: developer-binding
     namespace: development
   subjects:
   - kind: Group
     name: developers
     apiGroup: rbac.authorization.k8s.io
   roleRef:
     kind: Role
     name: developer
     apiGroup: rbac.authorization.k8s.io
   ```

3. **클러스터 수준 역할은 제한적으로 사용**:
   ```yaml
   apiVersion: rbac.authorization.k8s.io/v1
   kind: ClusterRole
   metadata:
     name: pod-reader
   rules:
   - apiGroups: [""]
     resources: ["pods"]
     verbs: ["get", "list", "watch"]
   ```

4. **서비스 계정에 대한 세분화된 권한**:
   ```yaml
   apiVersion: rbac.authorization.k8s.io/v1
   kind: Role
   metadata:
     name: app-role
     namespace: production
   rules:
   - apiGroups: [""]
     resources: ["configmaps"]
     resourceNames: ["app-config"]  # 특정 ConfigMap만 접근 가능
     verbs: ["get"]
   ```

다른 옵션들의 문제점:

- **모든 사용자에게 cluster-admin 역할 부여**: 이는 심각한 보안 위험을 초래합니다. 모든 사용자가 클러스터의 모든 리소스에 대한 완전한 접근 권한을 갖게 되어, 의도하지 않은 변경이나 악의적인 행위에 취약해집니다.

- **모든 권한을 단일 ClusterRole에 통합**: 이는 세분화된 접근 제어를 불가능하게 만들고, 최소 권한 원칙에 위배됩니다.

- **항상 사용자 인증서 사용**: 서비스 계정은 애플리케이션에 대한 인증에 적합하며, 모든 상황에서 사용자 인증서를 사용하는 것은 관리 부담을 증가시킵니다. 상황에 따라 적절한 인증 메커니즘을 선택하는 것이 중요합니다.
</details>
