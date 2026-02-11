# 클러스터 아키텍처 퀴즈

이 퀴즈는 Kubernetes 클러스터 아키텍처, 주요 구성 요소, 통신 경로, 고가용성 구성 등에 대한 이해도를 테스트합니다.

## 객관식 문제

1. Kubernetes 컨트롤 플레인의 핵심 구성 요소가 아닌 것은 무엇인가요?
   - A) kube-apiserver
   - B) etcd
   - C) kube-proxy
   - D) kube-scheduler
   
<details>

<summary>정답 보기</summary>

**정답: C) kube-proxy**

**설명:**
kube-proxy는 노드 구성 요소로, 컨트롤 플레인의 구성 요소가 아닙니다. 컨트롤 플레인의 핵심 구성 요소는 kube-apiserver, etcd, kube-scheduler, kube-controller-manager, cloud-controller-manager입니다. kube-proxy는 각 노드에서 실행되며 네트워크 규칙을 유지하고 연결 포워딩을 수행합니다.
</details>

2. Kubernetes에서 모든 클러스터 데이터를 저장하는 "소스 오브 트루스(source of truth)"로 작동하는 구성 요소는 무엇인가요?
   - A) kube-apiserver
   - B) etcd
   - C) kube-controller-manager
   - D) kubelet
   
<details>

<summary>정답 보기</summary>

**정답: B) etcd**

**설명:**
etcd는 모든 클러스터 데이터를 저장하는 일관성 있고 고가용성을 갖춘 키-값 저장소로, Kubernetes의 "소스 오브 트루스"로 작동합니다. 모든 클러스터 상태, 구성, 메타데이터가 etcd에 저장되며, 다른 모든 컨트롤 플레인 구성 요소는 etcd에서 정보를 읽고 쓰기 위해 kube-apiserver를 통해 상호 작용합니다.
</details>

3. 다음 중 Kubernetes 노드 구성 요소가 아닌 것은 무엇인가요?
   - A) kubelet
   - B) kube-proxy
   - C) 컨테이너 런타임
   - D) kube-controller-manager
   
<details>

<summary>정답 보기</summary>

**정답: D) kube-controller-manager**

**설명:**
kube-controller-manager는 컨트롤 플레인 구성 요소로, 노드 구성 요소가 아닙니다. 노드 구성 요소는 kubelet, kube-proxy, 컨테이너 런타임(containerd, CRI-O 등)입니다. kube-controller-manager는 컨트롤 플레인에서 실행되며, 노드 컨트롤러, 레플리케이션 컨트롤러 등 다양한 컨트롤러 프로세스를 실행합니다.
</details>

4. Kubernetes에서 새로 생성된 파드를 실행할 노드를 선택하는 컨트롤 플레인 구성 요소는 무엇인가요?
   - A) kube-apiserver
   - B) kube-scheduler
   - C) kubelet
   - D) kube-controller-manager
   
<details>

<summary>정답 보기</summary>

**정답: B) kube-scheduler**

**설명:**
kube-scheduler는 새로 생성된 파드를 실행할 노드를 선택하는 컨트롤 플레인 구성 요소입니다. 스케줄링 과정은 필터링(파드를 실행할 수 있는 노드 식별)과 스코어링(적합한 노드에 점수 부여)으로 이루어지며, 최종적으로 최적의 노드에 파드를 할당합니다. kube-scheduler는 리소스 요구사항, 하드웨어/소프트웨어/정책 제약 조건, 어피니티/안티-어피니티 명세, 데이터 지역성, 워크로드 간섭 등을 고려합니다.
</details>

5. 다음 중 클라우드 제공업체 API와 상호 작용하는 컨트롤 플레인 구성 요소는 무엇인가요?
   - A) kube-apiserver
   - B) etcd
   - C) cloud-controller-manager
   - D) kubelet
   
<details>

<summary>정답 보기</summary>

**정답: C) cloud-controller-manager**

**설명:**
cloud-controller-manager는 클라우드별 컨트롤 로직을 포함하는 컨트롤 플레인 구성 요소로, 클라우드 제공업체 API와 상호 작용합니다. 이를 통해 Kubernetes 코어와 클라우드 제공업체의 API를 분리할 수 있습니다. cloud-controller-manager는 노드 컨트롤러, 라우트 컨트롤러, 서비스 컨트롤러, 볼륨 컨트롤러 등 클라우드 특화 컨트롤러를 실행합니다.
</details>

6. 각 노드에서 실행되며 파드 내 컨테이너가 실행되도록 관리하는 에이전트는 무엇인가요?
   - A) kube-proxy
   - B) kubelet
   - C) containerd
   - D) kube-scheduler
   
<details>

<summary>정답 보기</summary>

**정답: B) kubelet**

**설명:**
kubelet은 각 노드에서 실행되는 에이전트로, 파드 내 컨테이너가 실행되도록 관리합니다. kubelet은 다양한 메커니즘을 통해 파드 스펙(PodSpec)을 받아 컨테이너가 해당 스펙에 따라 건강하게 실행되도록 보장합니다. 주요 기능으로는 PodSpec에 따른 컨테이너 실행, 컨테이너 상태 모니터링 및 보고, 컨테이너 라이프사이클 관리, 볼륨 마운트 관리, 노드 상태 보고, 컨테이너 헬스 체크 수행 등이 있습니다.
</details>

7. Kubernetes에서 서비스 IP에 대한 네트워크 규칙을 유지하고 연결 포워딩을 수행하는 노드 구성 요소는 무엇인가요?
   - A) kubelet
   - B) kube-proxy
   - C) CNI 플러그인
   - D) containerd
   
<details>

<summary>정답 보기</summary>

**정답: B) kube-proxy**

**설명:**
kube-proxy는 각 노드에서 실행되는 네트워크 프록시로, Kubernetes 서비스 개념의 구현을 담당합니다. 노드의 네트워크 규칙을 유지하고 연결 포워딩을 수행합니다. 주요 기능으로는 서비스 IP 및 포트에 대한 네트워크 규칙 유지, 연결 포워딩, 로드 밸런싱 구현, 서비스 디스커버리 지원 등이 있습니다. kube-proxy는 userspace 모드, iptables 모드, IPVS 모드 등 여러 작동 모드를 지원합니다.
</details>

8. Kubernetes에서 컨테이너를 실행하기 위한 표준 인터페이스는 무엇인가요?
   - A) CRI (Container Runtime Interface)
   - B) CNI (Container Network Interface)
   - C) CSI (Container Storage Interface)
   - D) CPI (Container Platform Interface)
   
<details>

<summary>정답 보기</summary>

**정답: A) CRI (Container Runtime Interface)**

**설명:**
CRI(Container Runtime Interface)는 Kubernetes에서 컨테이너를 실행하기 위한 표준 인터페이스입니다. CRI를 통해 Kubernetes는 containerd, CRI-O 등 다양한 컨테이너 런타임을 지원할 수 있습니다. CRI는 kubelet과 컨테이너 런타임 간의 통신을 위한 API를 정의하며, 이를 통해 컨테이너 생성, 시작, 중지, 삭제 등의 작업을 수행합니다. CNI(Container Network Interface)는 네트워킹을 위한 인터페이스이고, CSI(Container Storage Interface)는 스토리지를 위한 인터페이스입니다.
</details>

9. Kubernetes 클러스터에서 파드 네트워킹을 구현하는 데 사용되는 인터페이스는 무엇인가요?
   - A) CRI (Container Runtime Interface)
   - B) CNI (Container Network Interface)
   - C) CSI (Container Storage Interface)
   - D) API (Application Programming Interface)
   
<details>

<summary>정답 보기</summary>

**정답: B) CNI (Container Network Interface)**

**설명:**
CNI(Container Network Interface)는 Kubernetes에서 파드 네트워킹을 구현하기 위한 표준 인터페이스입니다. CNI 플러그인은 파드에 네트워크 인터페이스를 연결하고 IP 주소를 할당하는 역할을 합니다. Calico, Cilium, Flannel, Weave Net 등 다양한 CNI 플러그인이 있으며, 각각 다른 기능과 성능 특성을 가집니다. CNI를 통해 Kubernetes는 다양한 네트워킹 솔루션을 지원할 수 있습니다.
</details>

10. Kubernetes 클러스터에서 스토리지 시스템과의 표준 인터페이스를 제공하는 것은 무엇인가요?
    - A) CRI (Container Runtime Interface)
    - B) CNI (Container Network Interface)
    - C) CSI (Container Storage Interface)
    - D) CPI (Cloud Provider Interface)
    
<details>

<summary>정답 보기</summary>

**정답: C) CSI (Container Storage Interface)**

**설명:**
CSI(Container Storage Interface)는 Kubernetes와 스토리지 시스템 간의 표준 인터페이스를 제공합니다. CSI를 통해 스토리지 제공업체는 Kubernetes 코드를 수정하지 않고도 자체 스토리지 드라이버를 개발할 수 있습니다. CSI는 볼륨 생성, 삭제, 마운트, 언마운트 등의 작업을 위한 표준화된 API를 정의합니다. AWS EBS CSI 드라이버, Azure Disk CSI 드라이버, GCP PD CSI 드라이버 등 다양한 CSI 드라이버가 있습니다.
</details>

## 단답형 문제

11. Kubernetes 컨트롤 플레인에서 여러 컨트롤러 프로세스를 실행하는 구성 요소의 이름은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: kube-controller-manager**

**설명:**
kube-controller-manager는 여러 컨트롤러 프로세스를 실행하는 컨트롤 플레인 구성 요소입니다. 각 컨트롤러는 클러스터의 특정 측면을 관리합니다. 주요 컨트롤러로는 노드 컨트롤러, 레플리케이션 컨트롤러, 엔드포인트 컨트롤러, 서비스 어카운트 & 토큰 컨트롤러, 잡 컨트롤러, 크론잡 컨트롤러, 데몬셋 컨트롤러, 스테이트풀셋 컨트롤러, PV 컨트롤러, 네임스페이스 컨트롤러, 가비지 컬렉터 등이 있습니다.
</details>

12. Kubernetes에서 etcd 데이터의 일관성을 보장하기 위해 사용하는 합의 알고리즘은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: Raft**

**설명:**
etcd는 Raft 합의 알고리즘을 사용하여 분산 시스템에서 데이터의 강한 일관성을 보장합니다. Raft는 리더 선출, 로그 복제, 안전성을 통해 분산 시스템에서 합의를 이루는 알고리즘입니다. etcd 클러스터는 일반적으로 3개 또는 5개의 노드로 구성되며, 과반수(quorum)의 노드가 정상 작동하는 한 클러스터는 계속 작동할 수 있습니다.
</details>

13. Kubernetes에서 kube-proxy의 기본 작동 모드는 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: iptables**

**설명:**
kube-proxy의 기본 작동 모드는 iptables 모드입니다. 이 모드에서 kube-proxy는 리눅스 iptables를 사용하여 NAT를 구현하고 서비스 IP에 대한 트래픽을 파드로 라우팅합니다. 다른 작동 모드로는 userspace 모드(레거시)와 IPVS 모드(고성능)가 있습니다. IPVS 모드는 대규모 클러스터에서 더 나은 성능을 제공하지만, 리눅스 커널에 IPVS 모듈이 필요합니다.
</details>

14. Kubernetes 클러스터에서 API 서버와 통신하기 위한 구성 파일의 이름은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: kubeconfig**

**설명:**
kubeconfig는 Kubernetes API 서버와 통신하기 위한 구성 파일입니다. 이 파일에는 클러스터 정보, 인증 정보(인증서, 토큰 등), 컨텍스트(클러스터와 사용자의 조합) 등이 포함됩니다. kubectl 명령어는 기본적으로 $HOME/.kube/config 파일을 사용하지만, --kubeconfig 플래그나 KUBECONFIG 환경 변수를 통해 다른 파일을 지정할 수 있습니다.
</details>

15. Kubernetes에서 고가용성 클러스터를 구성할 때 일반적으로 권장되는 최소 컨트롤 플레인 노드 수는 몇 개인가요?

<details>

<summary>정답 보기</summary>

**정답: 3**

**설명:**
Kubernetes에서 고가용성 클러스터를 구성할 때 일반적으로 권장되는 최소 컨트롤 플레인 노드 수는 3개입니다. 이는 etcd 클러스터가 과반수(quorum) 기반으로 작동하기 때문입니다. 3개의 노드가 있으면 1개의 노드가 실패해도 클러스터는 계속 작동할 수 있습니다(2개가 과반수). 5개의 노드가 있으면 2개의 노드가 실패해도 클러스터는 계속 작동할 수 있습니다(3개가 과반수). 일반적으로 홀수 개의 노드를 사용하는 것이 권장됩니다.
</details>
## 실습 문제

16. etcd 데이터베이스의 백업을 생성하는 명령어를 작성하세요. 백업 파일은 `/backup/etcd-snapshot-$(date +%Y%m%d).db`에 저장하고, etcd 엔드포인트는 `https://127.0.0.1:2379`이며, 인증서 파일은 `/etc/kubernetes/pki/etcd/` 디렉토리에 있습니다.

<details>

<summary>정답 보기</summary>

**정답:**
```bash
ETCDCTL_API=3 etcdctl snapshot save /backup/etcd-snapshot-$(date +%Y%m%d).db \
--endpoints=https://127.0.0.1:2379 \
--cacert=/etc/kubernetes/pki/etcd/ca.crt \
--cert=/etc/kubernetes/pki/etcd/server.crt \
--key=/etc/kubernetes/pki/etcd/server.key
```

**설명:**
이 명령어는 ETCDCTL_API 환경 변수를 3으로 설정하여 etcdctl v3 API를 사용하고, snapshot save 명령으로 etcd 데이터베이스의 스냅샷을 생성합니다. --endpoints 플래그는 etcd 서버의 엔드포인트를 지정하고, --cacert, --cert, --key 플래그는 TLS 인증에 필요한 인증서 파일을 지정합니다. 백업 파일은 현재 날짜를 포함한 이름으로 /backup 디렉토리에 저장됩니다.
</details>

17. 다음 요구사항을 충족하는 kube-scheduler 구성 파일(YAML)을 작성하세요:
    - 스케줄러 이름: custom-scheduler
    - 리더 선출 활성화
    - 스코어링 플러그인: NodeResourcesBalancedAllocation 가중치를 2로 설정
    - 필터링 플러그인: NodeUnschedulable 비활성화

<details>

<summary>정답 보기</summary>

**정답:**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
leaderElection:
  leaderElect: true

profiles:
  - schedulerName: custom-scheduler
    plugins:
      score:
        enabled:
          - name: NodeResourcesBalancedAllocation
        disabled: []
      filter:
        disabled:
          - name: NodeUnschedulable
```

**설명:**
이 YAML 파일은 KubeSchedulerConfiguration 객체를 정의합니다. leaderElection.leaderElect: true는 리더 선출을 활성화하고, profiles 섹션에서 custom-scheduler라는 이름의 스케줄러 프로필을 정의합니다. plugins 섹션에서는 score 플러그인 중 NodeResourcesBalancedAllocation의 가중치를 2로 설정하고, filter 플러그인 중 NodeUnschedulable을 비활성화합니다.
</details>

18. 다음 요구사항을 충족하는 고가용성 etcd 클러스터 구성을 위한 etcd 시작 명령어를 작성하세요:
    - 노드 이름: etcd-1
    - 클러스터 이름: etcd-cluster
    - 클라이언트 URL: https://192.168.1.10:2379
    - 피어 URL: https://192.168.1.10:2380
    - 초기 클러스터: etcd-1=https://192.168.1.10:2380,etcd-2=https://192.168.1.11:2380,etcd-3=https://192.168.1.12:2380
    - 데이터 디렉토리: /var/lib/etcd
    - 인증서 파일은 /etc/kubernetes/pki/etcd/ 디렉토리에 있음

<details>

<summary>정답 보기</summary>

**정답:**
```bash
etcd \
--name=etcd-1 \
--initial-advertise-peer-urls=https://192.168.1.10:2380 \
--listen-peer-urls=https://192.168.1.10:2380 \
--listen-client-urls=https://192.168.1.10:2379,https://127.0.0.1:2379 \
--advertise-client-urls=https://192.168.1.10:2379 \
--initial-cluster-token=etcd-cluster \
--initial-cluster=etcd-1=https://192.168.1.10:2380,etcd-2=https://192.168.1.11:2380,etcd-3=https://192.168.1.12:2380 \
--initial-cluster-state=new \
--data-dir=/var/lib/etcd \
--cert-file=/etc/kubernetes/pki/etcd/server.crt \
--key-file=/etc/kubernetes/pki/etcd/server.key \
--trusted-ca-file=/etc/kubernetes/pki/etcd/ca.crt \
--peer-cert-file=/etc/kubernetes/pki/etcd/peer.crt \
--peer-key-file=/etc/kubernetes/pki/etcd/peer.key \
--peer-trusted-ca-file=/etc/kubernetes/pki/etcd/ca.crt
```

**설명:**
이 명령어는 etcd-1이라는 이름의 etcd 노드를 시작합니다. --initial-advertise-peer-urls와 --listen-peer-urls는 피어 통신을 위한 URL을, --listen-client-urls와 --advertise-client-urls는 클라이언트 통신을 위한 URL을 지정합니다. --initial-cluster-token은 클러스터의 고유 식별자를 지정하고, --initial-cluster는 클러스터의 모든 노드를 나열합니다. --initial-cluster-state=new는 새 클러스터를 생성함을 나타냅니다. --data-dir은 etcd 데이터가 저장될 디렉토리를 지정합니다. 마지막으로, 인증서 관련 플래그들은 TLS 통신을 위한 인증서 파일을 지정합니다.
</details>
## 심화 문제

19. Kubernetes 클러스터의 고가용성 아키텍처를 설계하고, 컨트롤 플레인 구성 요소와 etcd의 배포 방식, 로드 밸런서 구성, 그리고 장애 시나리오에 대한 대응 방안을 설명하세요.

<details>

<summary>정답 보기</summary>

**정답:**

**고가용성 Kubernetes 클러스터 아키텍처 설계**

1. **컨트롤 플레인 구성 요소 배포**:
  - 최소 3개의 컨트롤 플레인 노드를 여러 가용 영역에 분산 배치
  - 각 노드에 kube-apiserver, kube-scheduler, kube-controller-manager 배포
  - kube-scheduler와 kube-controller-manager는 리더 선출 모드로 실행 (한 번에 하나의 인스턴스만 활성)
  - kube-apiserver는 수평적으로 확장 가능 (모든 인스턴스가 동시에 활성)

2. **etcd 배포 방식**:
  - 스택형 토폴로지: etcd를 컨트롤 플레인 노드와 함께 배포
  - 외부 토폴로지: etcd를 별도의 노드에 배포 (더 높은 격리성과 확장성)
  - 최소 3개의 etcd 노드를 여러 가용 영역에 분산 배치 (5개 권장)
  - etcd 클러스터는 Raft 합의 알고리즘을 사용하여 데이터 일관성 보장

3. **로드 밸런서 구성**:
  - kube-apiserver 앞에 로드 밸런서 배치
  - 로드 밸런서는 L4(TCP) 또는 L7(HTTP/HTTPS) 레벨에서 작동 가능
  - 헬스 체크를 통해 비정상 kube-apiserver 인스턴스 감지 및 트래픽 제외
  - 클라우드 환경에서는 클라우드 제공업체의 관리형 로드 밸런서 사용 (AWS ELB, GCP Cloud Load Balancer 등)
  - 온프레미스 환경에서는 HAProxy, NGINX, keepalived 등 사용

4. **장애 시나리오 및 대응 방안**:
  - **단일 컨트롤 플레인 노드 장애**:
  - kube-apiserver: 로드 밸런서가 트래픽을 정상 노드로 라우팅
  - kube-scheduler/kube-controller-manager: 리더 선출을 통해 다른 노드의 인스턴스가 활성화
  - etcd: 과반수가 정상이면 클러스터 계속 작동 (3노드 중 2개, 5노드 중 3개)

  - **가용 영역 장애**:
  - 여러 가용 영역에 노드 분산 배치로 단일 가용 영역 장애 대응
  - 워커 노드도 여러 가용 영역에 분산 배치

  - **네트워크 파티션**:
  - etcd는 과반수 기반으로 작동하여 네트워크 파티션 시 "스플릿 브레인" 방지
  - 소수 파티션의 etcd 노드는 읽기 전용 모드로 전환

  - **etcd 데이터 손상/손실**:
  - 정기적인 etcd 백업 수행
  - 백업에서 복구 절차 문서화 및 테스트

5. **추가 고려사항**:
  - **인증서 관리**: 인증서 만료 모니터링 및 자동 갱신
  - **감사 로깅**: 중요 작업에 대한 감사 로그 활성화 및 외부 저장
  - **모니터링 및 알림**: 컨트롤 플레인 구성 요소 상태 모니터링 및 알림 설정
  - **자동화된 복구**: 자동 복구 메커니즘 구현 (예: systemd 서비스 자동 재시작)

이러한 고가용성 아키텍처를 통해 단일 노드, 단일 가용 영역, 또는 일부 구성 요소의 장애가 발생해도 Kubernetes 클러스터는 계속 작동할 수 있습니다.
</details>

20. Kubernetes 클러스터의 네트워킹 아키텍처를 설명하고, 파드 간 통신, 서비스 네트워킹, 외부 통신의 작동 방식과 CNI 플러그인의 역할을 설명하세요. 또한, 네트워크 정책을 사용하여 파드 간 통신을 제한하는 방법에 대해 설명하세요.

<details>

<summary>정답 보기</summary>

**정답:**

**Kubernetes 네트워킹 아키텍처**

1. **Kubernetes 네트워킹 모델**:
  - 모든 파드는 고유한 IP 주소를 가짐
  - 파드 간 NAT 없이 통신 가능
  - 노드와 파드 간 NAT 없이 통신 가능
  - 파드 내부의 컨테이너는 localhost를 통해 통신

2. **파드 간 통신**:
  - **같은 노드의 파드 간 통신**: 노드의 로컬 브리지 네트워크를 통해 통신
  - **다른 노드의 파드 간 통신**: 오버레이 네트워크 또는 라우팅 테이블을 통해 통신
  - CNI 플러그인이 파드 IP 주소 할당 및 라우팅 담당

3. **서비스 네트워킹**:
  - **ClusterIP**: 클러스터 내부에서만 접근 가능한 가상 IP
  - **kube-proxy**: 서비스 IP에 대한 트래픽을 파드로 라우팅
  - iptables 모드: 리눅스 iptables 규칙을 사용하여 NAT 구현
  - IPVS 모드: 리눅스 커널의 IP Virtual Server를 사용하여 고성능 로드 밸런싱 제공
  - **CoreDNS**: 서비스 이름을 ClusterIP로 해석하는 DNS 서비스
  - **서비스 디스커버리**: 환경 변수 또는 DNS를 통해 서비스 발견

4. **외부 통신**:
  - **인그레스(Ingress)**: HTTP/HTTPS 트래픽을 서비스로 라우팅
  - **NodePort**: 노드의 특정 포트를 통해 서비스 노출
  - **LoadBalancer**: 클라우드 제공업체의 로드 밸런서를 통해 서비스 노출
  - **ExternalName**: 외부 서비스에 대한 CNAME 레코드 생성

5. **CNI(Container Network Interface) 플러그인의 역할**:
  - 파드에 네트워크 인터페이스 연결
  - IP 주소 할당 및 관리
  - 라우팅 테이블 구성
  - 네트워크 정책 구현
  - 주요 CNI 플러그인:
  - **Calico**: BGP 기반 네트워킹, 네트워크 정책 지원, 고성능
  - **Cilium**: eBPF 기반 네트워킹 및 보안, L3-L7 보안 정책, 고성능
  - **Flannel**: 간단한 오버레이 네트워크, 설정 간단
  - **Weave Net**: 멀티 호스트 컨테이너 네트워킹, 암호화 지원

6. **네트워크 정책을 사용한 파드 간 통신 제한**:
  - NetworkPolicy 리소스를 사용하여 파드 간 통신 제어
  - 기본적으로 모든 파드는 서로 통신 가능 (정책이 없는 경우)
  - 네트워크 정책 구성 요소:
  - **podSelector**: 정책이 적용될 파드 선택
  - **policyTypes**: Ingress(수신), Egress(송신) 또는 둘 다
  - **ingress**: 수신 트래픽 규칙
  - **egress**: 송신 트래픽 규칙

  - **기본 거부 정책 예시**:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
```

  - **특정 파드 간 통신만 허용하는 정책 예시**:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
    - Ingress
  ingress:
    - from:
      - podSelector:
          matchLabels:
            app: frontend
      ports:
        - protocol: TCP
          port: 8080
```

  - **네임스페이스 간 통신 제어 예시**:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-monitoring
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
    - Ingress
  ingress:
    - from:
      - namespaceSelector:
          matchLabels:
            purpose: monitoring
      ports:
        - protocol: TCP
          port: 9090
```

7. **네트워크 정책 구현 고려사항**:
  - 네트워크 정책은 CNI 플러그인에 의해 구현됨
  - 모든 CNI 플러그인이 네트워크 정책을 지원하는 것은 아님
  - 정책 적용 전 테스트 환경에서 검증 필요
  - 기본 거부 정책부터 시작하여 필요한 통신만 허용하는 방식 권장

Kubernetes 네트워킹 아키텍처는 유연하고 확장 가능한 방식으로 컨테이너 간 통신을 가능하게 하며, 네트워크 정책을 통해 세분화된 보안 제어를 제공합니다.
</details>

---

[학습 자료로 돌아가기](../../core/01-cluster-architecture.md) | [다음 퀴즈: 파드와 워크로드](../core/02-pods-and-workloads-quiz.md)
