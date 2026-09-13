# 클러스터 관리 퀴즈

자체 관리형 클러스터와 EKS의 운영, 백업, 유지 관리, 모니터링, 복구를 다룹니다. 기존 15개 문제를 유지하며 호스트의 etcd 작업은 EKS 관리형 컨트롤 플레인에 적용하지 않습니다.

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
   etcdutl snapshot status snapshot.db --write-out=table
   ```

4. **백업 파일을 안전한 위치에 저장:**
   - 클러스터 외부 스토리지
   - 클라우드 스토리지(S3, GCS 등)
   - 다른 물리적 위치

**etcd 복원 절차:**

1. 스냅샷을 검증하고 원본 데이터, PKI, 암호화 공급자 키·설정을 보관합니다. etcd 스냅샷에는 PV 파일이나 모든 호스트 설정이 포함되지 않습니다.
2. 배포판 운영 절차로 모든 API 서버와 해당 etcd 프로세스를 중지합니다. kubeadm은 보통 개별 systemd 서비스가 아닌 정적 파드를 사용하며 kubelet만 중지해도 컨테이너가 종료되지는 않습니다.
3. 호환 etcdutl로 새 디렉토리에 오프라인 복원합니다. 아래 단일 멤버 예시는 HA 복구 명령이 아닙니다:

```bash
etcdutl snapshot restore snapshot.db \
  --data-dir=/var/lib/etcd-restore \
  --name=etcd-1 \
  --initial-cluster=etcd-1=https://127.0.0.1:2380 \
  --initial-cluster-token=restored-cluster \
  --initial-advertise-peer-urls=https://127.0.0.1:2380 \
  --bump-revision=1000000000 --mark-compacted
```

4. HA는 같은 스냅샷을 각 멤버 고유 이름·피어 URL과 동일한 전체 멤버 목록으로 복원합니다. 리비전 증가량은 스냅샷 이후 쓰기를 초과하도록 정하고 watch 캐시를 무효화합니다.
5. etcd 매니페스트·서비스의 경로, 소유권, 인증서를 복원 데이터에 맞춥니다. etcd 쿼럼·상태 확인 후 API 서버·컨트롤러를 시작하고 노드·워크로드를 검증합니다.
6. [공식 복구 절차](https://etcd.io/docs/v3.6/op-guide/recovery/)를 따르세요. EKS 사용자는 관리형 etcd에 접근하지 않고 지원되는 백업 도구로 앱 리소스·데이터를 복원합니다.

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
   kubectl drain <노드_이름> --ignore-daemonsets
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
   - 워크로드 컨트롤러가 대체 파드를 생성할 수 있으며 배치는 용량·제약 조건에 따라 달라집니다.
   - DaemonSet 파드가 있으면 --ignore-daemonsets 없이는 drain이 거부되며 이 플래그는 해당 파드를 계속 실행시킵니다.
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
  - Kubernetes 1.34+ 설치 예시 (요구사항과 기존 설치 여부를 먼저 확인):
    ```bash
    kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/download/v0.9.0/components.yaml
    ```
  - 사용 예:
    ```bash
    kubectl top nodes
    kubectl top pods --all-namespaces
    ```

- **Headlamp (Kubernetes Dashboard는 보관 상태):**
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
  - 현재 제공되는 API 종류 확인 (클라이언트 사용 이력과 다름):
    ```bash
    kubectl api-resources -o wide
    ```
  - /metrics 접근이 허용되면 관측된 deprecated API 요청을 확인하고 매니페스트·요청 로그도 함께 검토:
    ```bash
    kubectl get --raw /metrics | grep '^apiserver_requested_deprecated_apis'
    ```
  - 필요한 경우 매니페스트 업데이트

- **백업 및 복구 계획:**
  - etcd 데이터베이스 백업:
    ```bash
    ETCDCTL_API=3 etcdctl snapshot save snapshot.db \
      --endpoints=https://127.0.0.1:2379 \
      --cacert=/etc/kubernetes/pki/etcd/ca.crt \
      --cert=/etc/kubernetes/pki/etcd/healthcheck-client.crt \
      --key=/etc/kubernetes/pki/etcd/healthcheck-client.key
    ```
  - 일부 워크로드 객체 내보내기 (전체 백업이 아니며 출력 보호 필요):
    ```bash
    umask 077
    kubectl get all --all-namespaces -o yaml > workload-subset.yaml
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
    kubectl drain <노드_이름> --ignore-daemonsets
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

2. 각 노드의 SSH 별칭이 구성된 자체 관리형 Linux 클러스터에서 kubelet을 점검하고 명시적인 복구 모드를 지원하는 스크립트를 작성하세요.

<details>
<summary>정답 보기</summary>

**정답:**

```bash
#!/usr/bin/env bash
# check_kubelet.sh: self-managed Linux nodes with configured SSH aliases only.
set -euo pipefail
repair=${REPAIR_KUBELET:-0}
status=0
nodes=$(kubectl get nodes -o jsonpath='{.items[*].metadata.name}')
for node in $nodes; do
  printf '%s: ' "$node"
  if state=$(ssh -o BatchMode=yes -o ConnectTimeout=5 "$node" \
      'sudo -n systemctl is-active kubelet'); then
    printf 'kubelet %s\n' "$state"
    continue
  else
    rc=$?
  fi
  if [ "$rc" -ne 3 ]; then
    printf 'SSH/sudo/service query failed (exit %s); no repair attempted\n' "$rc" >&2
    status=1
    continue
  fi
  printf 'kubelet %s\n' "$state"
  if [ "$repair" != 1 ]; then
    printf 'Inspect logs and approve a repair before rerunning with REPAIR_KUBELET=1\n'
    status=1
    continue
  fi
  if ssh -o BatchMode=yes -o ConnectTimeout=5 "$node" \
      'sudo -n systemctl start kubelet && sudo -n systemctl is-active --quiet kubelet' \
      && kubectl wait --for=condition=Ready "node/$node" --timeout=120s; then
    printf '%s: kubelet active and node Ready\n' "$node"
  else
    status=1
    ssh -o BatchMode=yes -o ConnectTimeout=5 "$node" \
      'sudo -n journalctl -u kubelet --no-pager -n 50' || true
  fi
done
exit "$status"
```

이 스크립트는 다음 작업을 수행합니다:
1. `kubectl get nodes`를 사용하여 클러스터의 모든 노드 목록을 가져옵니다.
2. 각 노드에 대해:
   - 서비스 상태를 조회하고 복구 요청 후 Ready 상태를 검증합니다.
   - SSH를 통해 노드에 연결하여 kubelet 서비스 상태를 확인합니다.
   - 서비스 상태 조회에 성공한 비활성 서비스를 보고하고 REPAIR_KUBELET=1일 때만 시작합니다.
   - 서비스 시작 후 상태를 다시 확인합니다.
   - 시작에 실패한 경우 로그를 확인합니다.
   - SSH·sudo·조회 실패를 비활성 서비스와 구분하고 복구 후 노드 Ready를 확인합니다.

**사용 방법:**
```bash
chmod +x check_kubelet.sh
./check_kubelet.sh
# After diagnosing the inactive service and approving repair:
REPAIR_KUBELET=1 ./check_kubelet.sh
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
#!/usr/bin/env bash
# backup_etcd.sh: self-managed etcd; external storage must already be mounted.
set -euo pipefail
umask 077
BACKUP_DIR=${BACKUP_DIR:-/opt/etcd-backup}
REMOTE_ROOT=${REMOTE_ROOT:-/mnt/remote-storage}
REMOTE_DIR="$REMOTE_ROOT/etcd-backups"
METRICS_DIR=${METRICS_DIR:-/var/lib/node_exporter/textfile_collector}
RETENTION_DAYS=${RETENTION_DAYS:-7}
ETCD_ENDPOINT=${ETCD_ENDPOINT:-https://127.0.0.1:2379}
ETCD_CACERT=${ETCD_CACERT:-/etc/kubernetes/pki/etcd/ca.crt}
ETCD_CERT=${ETCD_CERT:-/etc/kubernetes/pki/etcd/healthcheck-client.crt}
ETCD_KEY=${ETCD_KEY:-/etc/kubernetes/pki/etcd/healthcheck-client.key}

publish_status() {
  rc=$?
  trap - EXIT
  if [ -d "$METRICS_DIR" ]; then
    tmp=$(mktemp "$METRICS_DIR/.etcd-backup.XXXXXX")
    success=0
    [ "$rc" -eq 0 ] && success=1
    printf 'etcd_backup_success %s\netcd_backup_last_attempt_timestamp_seconds %s\n' \
      "$success" "$(date +%s)" > "$tmp"
    chmod 0644 "$tmp"
    mv "$tmp" "$METRICS_DIR/etcd_backup_status.prom"
  fi
  exit "$rc"
}
trap publish_status EXIT
case "$RETENTION_DAYS" in ''|*[!0-9]*) echo 'Invalid retention' >&2; exit 1;; esac
mountpoint -q "$REMOTE_ROOT" || { echo 'Remote storage is not mounted' >&2; exit 1; }
mkdir -p "$BACKUP_DIR" "$REMOTE_DIR"
exec 9>"$BACKUP_DIR/.backup.lock"
flock -n 9 || { echo 'Another backup is running' >&2; exit 1; }
name="etcd-snapshot-$(date -u +%Y%m%d-%H%M%S).db"
ETCDCTL_API=3 etcdctl snapshot save "$BACKUP_DIR/$name" \
  --endpoints="$ETCD_ENDPOINT" --cacert="$ETCD_CACERT" \
  --cert="$ETCD_CERT" --key="$ETCD_KEY"
etcdutl snapshot status "$BACKUP_DIR/$name" --write-out=table
gzip "$BACKUP_DIR/$name"
cp "$BACKUP_DIR/$name.gz" "$REMOTE_DIR/.$name.gz.partial"
cmp "$BACKUP_DIR/$name.gz" "$REMOTE_DIR/.$name.gz.partial"
mv "$REMOTE_DIR/.$name.gz.partial" "$REMOTE_DIR/$name.gz"
# Retention runs only after snapshot validation and verified external copy.
find "$BACKUP_DIR" -maxdepth 1 -type f -name 'etcd-snapshot-*.db.gz' \
  -mtime "+$RETENTION_DAYS" -delete
find "$REMOTE_DIR" -maxdepth 1 -type f -name 'etcd-snapshot-*.db.gz' \
  -mtime "+$RETENTION_DAYS" -delete
printf 'Verified backup copied to %s\n' "$REMOTE_DIR/$name.gz"
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
    create 0600 root root
}
```

**5. 백업 테스트:**

```bash
sudo /opt/etcd-backup/backup_etcd.sh
```

**6. 백업 모니터링:**

스크립트의 EXIT 트랩은 METRICS_DIR이 있을 때 숫자형 `etcd_backup_success`, `etcd_backup_last_attempt_timestamp_seconds`를 기록합니다. node-exporter textfile collector가 해당 디렉토리를 읽도록 구성하고 작성 권한을 부여하며 실패·오래된 시도를 경고하세요. echo·복사 명령 뒤의 `$?`로 백업 성공 여부를 판정하면 안 됩니다. 외부 마운트는 이미 있어야 하며 검증·복사 실패 시 보존 기간 정리를 중단합니다.

**참고 사항:**
- 백업 파일은 클러스터 외부의 안전한 위치에 저장해야 합니다.
- 클라우드 환경에서는 S3, GCS 등의 객체 스토리지를 사용하는 것이 좋습니다.
- 정기적으로 백업 복원 테스트를 수행하여 백업의 유효성을 확인해야 합니다.
- 고가용성 etcd 클러스터의 경우 하나의 etcd 인스턴스에서만 백업을 수행하면 됩니다.
</details>
4. 명시적으로 선택한 자체 관리형 Linux 워커 노드의 유지 관리 절차를 작성하세요. 중단 예산을 준수하고 상태 확인 실패 시 중단해야 합니다.

<details>
<summary>정답 보기</summary>

**정답:**

**노드 롤링 업데이트 절차:**

```bash
#!/usr/bin/env bash
# node_rolling_update.sh: explicitly selected self-managed Linux workers only.
set -euo pipefail
: "${MAINTENANCE_COMMAND:?Set a reviewed node-maintenance command that does not reboot itself}"
: "${WORKLOAD_HEALTHCHECK:?Set a command that verifies critical workload health}"
[ "$#" -gt 0 ] || { echo 'Pass the worker node names as arguments' >&2; exit 1; }
trap 'echo "Stopped on error; inspect the node before manually uncordoning it" >&2' ERR
for node in "$@"; do
  kubectl get node "$node" -o json | jq -e '
    (.metadata.labels["kubernetes.io/os"] == "linux") and
    (.metadata.labels | has("node-role.kubernetes.io/control-plane") | not) and
    (.metadata.labels | has("node-role.kubernetes.io/master") | not)' >/dev/null
  ssh -o BatchMode=yes -o ConnectTimeout=5 "$node" 'sudo -n true'
done
kubectl get poddisruptionbudgets -A
bash -c "$WORKLOAD_HEALTHCHECK"
for node in "$@"; do
  kubectl wait --for=condition=Ready "node/$node" --timeout=120s
  boot_before=$(kubectl get node "$node" -o jsonpath='{.status.nodeInfo.bootID}')
  kubectl cordon "$node"
  kubectl drain "$node" --ignore-daemonsets --timeout=10m
  ssh -o BatchMode=yes -o ConnectTimeout=5 "$node" "$MAINTENANCE_COMMAND"
  reboot_required=$(ssh -o BatchMode=yes -o ConnectTimeout=5 "$node" \
    'if [ -f /var/run/reboot-required ]; then echo yes; else echo no; fi')
  if [ "$reboot_required" = yes ]; then
    ssh -o BatchMode=yes -o ConnectTimeout=5 "$node" 'sudo -n reboot' || true
    deadline=$((SECONDS + 600))
    while :; do
      boot_after=$(kubectl get node "$node" -o jsonpath='{.status.nodeInfo.bootID}')
      [ -n "$boot_after" ] && [ "$boot_after" != "$boot_before" ] && break
      [ "$SECONDS" -lt "$deadline" ] || { echo 'New boot ID not reported' >&2; exit 1; }
      sleep 5
    done
  fi
  # Require a fresh kubelet lease renewal, not a stale pre-maintenance Ready flag.
  lease_before=$(kubectl -n kube-node-lease get lease "$node" -o jsonpath='{.spec.renewTime}')
  deadline=$((SECONDS + 120))
  while :; do
    lease_after=$(kubectl -n kube-node-lease get lease "$node" -o jsonpath='{.spec.renewTime}')
    [ -n "$lease_after" ] && [ "$lease_after" != "$lease_before" ] && break
    [ "$SECONDS" -lt "$deadline" ] || { echo 'No fresh kubelet lease' >&2; exit 1; }
    sleep 5
  done
  kubectl wait --for=condition=Ready "node/$node" --timeout=5m
  bash -c "$WORKLOAD_HEALTHCHECK"
  kubectl uncordon "$node"
  bash -c "$WORKLOAD_HEALTHCHECK"
done
```

이 예시는 kubectl, jq, 선택한 노드의 SSH 별칭, 승인된 비대화형 sudo, 검토한 유지 관리 명령이 필요합니다. Debian/Ubuntu의 reboot-required 표시를 검사하므로 OS에 맞게 조정하세요. WORKLOAD_HEALTHCHECK는 실제 중요 앱을 검증하는 명령으로 설정하고 검토한 워커 목록만 전달합니다:

```bash
MAINTENANCE_COMMAND='sudo -n /usr/local/sbin/approved-node-maintenance' \
WORKLOAD_HEALTHCHECK='kubectl -n app rollout status deployment/frontend --timeout=5m' \
./node_rolling_update.sh worker-1 worker-2
```

명령·스크립트와 앱 이름은 실제 환경·계획과 일치해야 합니다. force나 emptyDir 손실을 기본 허용하지 않으며 drain·유지 관리 실패 시 중단합니다. 재부팅 후 변경된 boot ID와 새 kubelet lease를 확인하고 실패 노드는 cordon 상태로 남깁니다. PDB·검증은 계획 중단을 줄이지만 동시 장애까지 가용성을 보장하지는 않습니다. EKS 관리형·Auto Mode 노드는 제공자의 업데이트 기능을, 컨트롤 플레인은 별도 kubeadm 절차를 사용하세요.

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

```python
#!/usr/bin/env python3
# resource_usage_report.py: read-only Kubernetes API/metrics reporting.
import datetime
from decimal import Decimal
import html
import json
import os
from pathlib import Path
import re
import subprocess

SCALE = {"": Decimal(1), "n": Decimal("1e-9"), "u": Decimal("1e-6"),
         "m": Decimal("1e-3"), "k": Decimal(1000), "K": Decimal(1000)}
SCALE.update({s: Decimal(1000) ** n for n, s in enumerate("MGTPE", 2)})
SCALE.update({s + "i": Decimal(1024) ** n for n, s in enumerate("KMGTPE", 1)})

def quantity(value):
    text = str(value)
    match = re.fullmatch(r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)([a-zA-Z]*)", text)
    if not match or match[2] not in SCALE:
        raise ValueError("Unsupported Kubernetes quantity: " + text)
    return Decimal(match[1]) * SCALE[match[2]]

def kubectl_json(*args):
    return json.loads(subprocess.check_output(["kubectl", *args], text=True))

def make_rows(pods, metrics):
    index = {(p["metadata"]["namespace"], p["metadata"]["name"]): p for p in pods}
    rows = []
    for metric in metrics:
        key = metric["metadata"]["namespace"], metric["metadata"]["name"]
        if key not in index:
            continue  # API snapshots are not atomic; the Pod may have disappeared.
        spec = index[key]["spec"]
        active = spec.get("containers", []) + [c for c in spec.get("initContainers", [])
                                               if c.get("restartPolicy") == "Always"]
        usage = {r: sum((quantity(c["usage"][r]) for c in metric["containers"]), Decimal(0))
                 for r in ("cpu", "memory")}
        requests = {}
        for resource in ("cpu", "memory"):
            pod_request = spec.get("resources", {}).get("requests", {}).get(resource)
            values = [c.get("resources", {}).get("requests", {}).get(resource) for c in active]
            requests[resource] = (quantity(pod_request) if pod_request is not None else
                                  sum((quantity(v) for v in values), Decimal(0))
                                  if all(v is not None for v in values) else None)
        rows.append((key, usage, requests))
    return rows

def render_report(rows):
    lines = ["Kubernetes resource usage report", "Generated: " + datetime.datetime.now(datetime.timezone.utc).isoformat(),
             "Requests: active application/native-sidecar containers or Pod-level requests.",
             "This is not scheduler effective-request accounting for completed init stages/overhead."]
    totals = {}
    for key, usage, _ in rows:
        total = totals.setdefault(key[0], {"cpu": Decimal(0), "memory": Decimal(0)})
        for resource in total:
            total[resource] += usage[resource]
    for resource in ("cpu", "memory"):
        lines.append("\nTop 10 Pods by " + resource)
        for key, usage, requests in sorted(rows, key=lambda row: row[1][resource], reverse=True)[:10]:
            request = requests[resource]
            ratio = f"{usage[resource] / request * 100:.1f}%" if request else "request missing/zero"
            lines.append(f"{key[0]}/{key[1]}: usage={usage[resource]}, request={request}, ratio={ratio}")
    lines.append("\nNamespace totals (CPU cores, memory GiB)")
    for namespace, total in sorted(totals.items()):
        lines.append(f"{namespace}: {total['cpu']:.3f}, {total['memory'] / (1024 ** 3):.3f}")
    lines.append("\nPods above 80% of known requests or with missing requests")
    for key, usage, requests in rows:
        if any(not requests[r] or usage[r] / requests[r] >= Decimal('0.8') for r in requests):
            lines.append(f"{key[0]}/{key[1]}: usage={usage}; requests={requests}")
    return "\n".join(lines)

def main():
    os.umask(0o077)
    group = kubectl_json("get", "--raw", "/apis/metrics.k8s.io")
    version = group["preferredVersion"]["version"]
    pod_metrics = kubectl_json("get", "--raw", f"/apis/metrics.k8s.io/{version}/pods")["items"]
    pods = kubectl_json("get", "pods", "-A", "-o", "json")["items"]
    rows = make_rows(pods, pod_metrics)
    report = render_report(rows)
    nodes = subprocess.check_output(["kubectl", "top", "nodes"], text=True)
    report += "\n\nNode resource usage\n" + nodes
    node_count = len(kubectl_json("get", "nodes", "-o", "json")["items"])
    namespace_count = len(kubectl_json("get", "namespaces", "-o", "json")["items"])
    context = subprocess.check_output(["kubectl", "config", "current-context"], text=True).strip()
    report += f"\nContext: {context}; nodes: {node_count}; namespaces: {namespace_count}\n"
    report += f"Inventory Pods: {len(pods)}; Pods with matched metrics: {len(rows)}\n"
    directory = Path(os.environ.get("REPORT_DIR", "/tmp/k8s-reports"))
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    stem = "resource-usage-" + datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")
    text_path = directory / (stem + ".txt")
    text_path.write_text(report, encoding="utf-8")
    (directory / (stem + ".html")).write_text(
        '<!doctype html><meta charset="utf-8"><title>Kubernetes resource report</title><pre>'
        + html.escape(report) + '</pre>', encoding="utf-8")
    print(text_path)

if __name__ == "__main__":
    main()
```

**스크립트 사용 방법:**
```bash
python3 resource_usage_report.py
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
- Python 3와 파드·메트릭 API 읽기 권한이 있는 kubectl이 필요합니다. 제공되는 메트릭 버전을 검색하고 다중 컨테이너 사용량을 네임스페이스별로 합산하며 단위 변환과 HTML 이스케이프를 수행합니다.
- Metrics Server가 클러스터에 설치되어 있어야 합니다.
- 대규모 클러스터에서는 스크립트 실행 시간이 길어질 수 있습니다.
- 정기적인 보고서 생성을 위해 cron 작업으로 설정할 수 있습니다.
- 보고서를 이메일로 전송하거나 모니터링 시스템과 통합할 수 있습니다.
</details>
## 고급 주제

1. 실제 etcd 설정·운영 기법으로 구성된 항목 두 개는 무엇인가요? (두 개 선택)
   - A) `--max-request-bytes`, `--quota-backend-bytes`, 정기적인 압축
   - B) `--max-concurrent-requests`, `--max-connections`, 디스크 RAID 구성
   - C) `--auto-compaction-retention`, `--snapshot-count`, SSD 스토리지 사용
   - D) `--max-txn-ops`, `--max-result-buffer`, 메모리 증설

<details>
<summary>정답 보기</summary>

**정답: A, C**

**설명:**
etcd는 Kubernetes 클러스터의 핵심 데이터 저장소로, 그 성능은 전체 클러스터 성능에 직접적인 영향을 미칩니다. etcd 성능 최적화를 위한 주요 설정 매개변수와 모범 사례는 다음과 같습니다:

1. **`--auto-compaction-retention`**: etcd는 모든 변경 사항의 기록을 유지하는 append-only 저장소입니다. 이 매개변수는 이전 버전의 키를 자동으로 압축하는 주기를 설정합니다. 기본값은 0(비활성화)이지만, 프로덕션 환경에서는 일반적으로 1시간(1h) 또는 24시간(24h)으로 설정합니다. 이를 통해 디스크 공간을 절약하고 성능을 향상시킬 수 있습니다.

2. **`--snapshot-count`**: etcd가 스냅샷을 생성하기 전에 커밋할 트랜잭션 수를 지정합니다. 이는 이식형 백업 스냅샷이 아닌 내부 Raft 스냅샷을 제어합니다. 기본값은 버전별로 다르며 v3.6 문서는 10,000을 명시하므로 설치 버전을 확인하고 측정 후 조정하세요.

3. **SSD 스토리지 사용**: etcd는 디스크 I/O에 민감하므로, SSD(Solid State Drive)를 사용하면 성능이 크게 향상됩니다. 특히 대규모 클러스터에서는 SSD 사용이 필수적입니다.

기타 중요한 최적화 설정 및 모범 사례:

- **전용 디스크 사용**: etcd 데이터를 위한 전용 디스크를 사용하여 다른 애플리케이션과의 I/O 경합을 방지합니다.
- **적절한 메모리 할당**: etcd는 성능을 위해 데이터를 메모리에 캐시하므로, 충분한 메모리를 할당해야 합니다.
- **클러스터 크기 최적화**: 일반적으로 3-5개의 etcd 멤버가 최적의 성능과 가용성을 제공합니다.
- **네트워크 지연 시간 최소화**: 멤버 간 지연과 장애 격리를 함께 고려하세요. 모든 멤버를 한 영역에 배치하면 그 영역 장애로 쿼럼을 잃습니다.
- **정기적인 백업 및 압축**: 데이터 안전성을 보장하고 디스크 공간을 효율적으로 사용하기 위해 정기적인 백업과 압축을 수행합니다.

`--max-request-bytes`, `--quota-backend-bytes`, `--max-txn-ops`는 실제 설정입니다. D에는 지원되지 않는 `--max-result-buffer`도 포함되어 있습니다. 설정 한도, 보존 기간, 내부 스냅샷은 백업 전략과 구분해야 합니다.
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

3. Kubernetes 감사 로그에 기록할 이벤트와 상세 수준을 선택하는 메커니즘은 무엇인가요?
   - A) 필터 없이 모든 요청·응답 본문 기록
   - B) 감사 정책으로 이벤트와 수준 선택
   - C) 감사 로그를 외부 SIEM 시스템으로 실시간 전송
   - D) 감사 로그에 대한 접근을 관리자로 제한

<details>
<summary>정답 보기</summary>

**정답: B) 감사 정책으로 이벤트와 수준 선택**

**설명:**
Kubernetes 감사 로깅(Audit Logging)을 구성할 때 가장 중요한 고려 사항은 감사 정책으로 이벤트와 수준 선택하는 것입니다. 이는 다음과 같은 이유로 중요합니다:

1. **성능 영향 최소화**: 모든 API 요청을 로깅하면 API 서버에 상당한 부하가 발생하고 성능이 저하될 수 있습니다. 필요한 감사 이력과 측정한 부하에 따라 수준을 선택하며 모든 요청의 메타데이터 기록도 지원되는 기본 전략입니다.

2. **스토리지 효율성**: 모든 이벤트를 로깅하면 로그 데이터의 양이 급격히 증가하여 스토리지 비용이 증가하고 로그 분석이 어려워집니다.

3. **관련 정보 집중**: 중요한 이벤트만 로깅함으로써 보안 분석가가 중요한 정보에 집중할 수 있습니다.

4. **규정 준수**: 시스템에 적용되는 요구사항에 맞게 이벤트 범위·보존·접근 제어를 정하세요.

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
- level: Metadata
  resources:
  - group: ""
    resources: ["secrets", "configmaps", "serviceaccounts/token"]
  - group: authentication.k8s.io
    resources: ["tokenreviews"]
- level: Metadata
```

다른 옵션들의 문제점:
- 모든 API 요청을 로깅하는 것은 성능 및 스토리지 문제를 일으킬 수 있습니다.
- 외부 SIEM 시스템으로의 실시간 전송은 중요하지만, 로깅할 내용을 결정하는 것보다 우선순위가 낮습니다.
- 감사 로그에 대한 접근 제한은 중요하지만, 로깅 정책 자체보다는 보안 조치에 해당합니다.
</details>

4. 자체 관리형 환경에서 전용 노드 문제 감지와 사용자 정의 복구 로직을 결합하는 방식은 무엇인가요?
   - A) 노드 상태를 모니터링하고 문제가 있는 노드를 자동으로 재부팅하는 DaemonSet 배포
   - B) 클라우드 제공자의 관리형 노드 그룹 및 자동 복구 기능 활용
   - C) Node Problem Detector와 사용자 정의 컨트롤러를 사용한 노드 상태 모니터링 및 복구
   - D) 노드 상태를 주기적으로 확인하고 문제가 있는 노드를 재생성하는 cron 작업 구현

<details>
<summary>정답 보기</summary>

**정답: C) Node Problem Detector와 사용자 정의 컨트롤러를 사용한 노드 상태 모니터링 및 복구**

**설명:**
Node Problem Detector와 사용자 정의 복구는 확장 가능한 설계 중 하나입니다. 보편적으로 가장 좋은 방식은 아니며 EKS 노드 복구 같은 제공자 관리 기능이 운영 부담을 줄일 수 있습니다. 이 접근 방식은 다음과 같은 이점을 제공합니다:

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

4. **클라우드 독립적**: 감지·복구는 OS·런타임·제공자에 맞아야 하며 노드 에이전트가 보고할 수 없는 노드 손실에는 외부 신호·컨트롤러도 필요합니다.

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

2. **네임스페이스 격리**: 네임스페이스별로 역할을 정의하면 팀이나 애플리케이션 간의 논리적 격리를 강화할 수 있습니다. 일반적인 API 작업을 제한하며 네임스페이스 격리에는 워크로드 admission·네트워크 통제도 필요합니다.

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
   ```

Pod·Deployment 생성 권한으로 네임스페이스의 Secret·ServiceAccount 권한을 간접적으로 사용할 수 있습니다. 직접 Secret 읽기 제거만으로 워크로드가 마운트할 자격 증명을 제한하지는 못하므로 적절한 admission 통제가 필요합니다.

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

- **모든 권한을 단일 ClusterRole에 통합**: 모든 권한을 모은 역할은 과도한 권한을 줄 수 있지만 좁게 정의한 재사용 ClusterRole과 네임스페이스 RoleBinding은 적절할 수 있습니다.

- **항상 사용자 인증서 사용**: 서비스 계정은 애플리케이션에 대한 인증에 적합하며, 모든 상황에서 사용자 인증서를 사용하는 것은 관리 부담을 증가시킵니다. 상황에 따라 적절한 인증 메커니즘을 선택하는 것이 중요합니다.
</details>
