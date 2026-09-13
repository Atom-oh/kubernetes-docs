# EKS Hybrid Nodes 운영 퀴즈

> **마지막 업데이트**: 2026년 9월 13일

> **관련 문서**: [운영](../../eks-hybrid-nodes/08-operations.md)

## 객관식 문제

<span id="_1-hybrid-nodes-환경에서-노드-모니터링을-위해-권장되는-도구-조합은"></span>

### 1. Hybrid Nodes의 호스트 지표와 대시보드를 구성할 수 있는 조합은?

- A) 메모장에 수동 기록
- B) Prometheus, Grafana와 올바르게 구성한 Node Exporter
- C) 이메일 알림만 사용
- D) 로그를 수동으로만 확인

<details>
<summary>정답 보기</summary>

**정답: B) Prometheus, Grafana와 올바르게 구성한 Node Exporter**

**설명:**

Prometheus는 지표를 수집하고 Grafana는 이를 표시합니다. Node Exporter는 호스트 지표, DCGM Exporter는 지원되는 GPU 지표를 제공하며 Alertmanager는 알림을 전달합니다. 이는 가능한 구성 중 하나입니다. 검토한 chart/add-on을 설치하고 호스트 mount, identity, 배치, TLS, 인증과 실제 scrape 대상을 확인합니다. selector와 Pod template label이 맞지 않는 불완전한 DaemonSet은 동작하는 설치 예제가 아닙니다. Container Insights는 Hybrid 환경에서 사용할 수 없는 EC2 IMDS에 의존하므로 Hybrid 호스트 수준 지표를 제공하지 않습니다.

</details>

<span id="_2-kubelet-인증서-갱신이-필요한-시점을-확인하는-방법은"></span>

### 2. 노드나 서비스에 설정된 인증서의 만료를 어떻게 확인해야 하나요?

- A) 인증서는 만료되지 않는다고 가정
- B) 실제 인증서를 OpenSSL로 확인하고 발급자와 갱신 책임을 식별
- C) Node가 NotReady가 될 때까지 대기
- D) 모든 인증서를 매일 수동 갱신

<details>
<summary>정답 보기</summary>

**정답: B) 실제 인증서를 OpenSSL로 확인하고 발급자와 갱신 책임을 식별**

**설명:**

먼저 kubelet serving/client 인증서, EKS control plane CA, Harbor TLS, IAM Roles Anywhere 호스트 인증서를 구분합니다. Hybrid의 IAM 인증이 kubelet-client-current.pem 파일의 존재를 의미하지는 않습니다. kubeadm 갱신 명령은 EKS control plane을 관리하지 않습니다. 만료 확인과 chain·hostname·폐기 상태·실제 인증 검증은 별도입니다. serverTLSBootstrap 설정만으로 serving CSR이 승인되거나 IAM Roles Anywhere 인증서가 갱신되지 않습니다.

```bash
set -euo pipefail
: "${CERT_PATH:?Set the actual certificate file}"
openssl x509 -in "$CERT_PATH" -checkend 604800 -noout
```

이 예제는 7일 이내 만료를 확인합니다. 인증서 수명과 갱신 정책에 맞춰 기준을 정하며, 파일이 없거나 유효하지 않으면 실패합니다.

</details>

<span id="_3-hybrid-node에서-kubelet이-응답하지-않을-때-가장-먼저-수행해야-할-트러블슈팅-단계는"></span>

### 3. Hybrid Node의 kubelet이 응답하지 않을 때 먼저 확인할 것은?

- A) 전체 클러스터 재시작
- B) 해당 노드에 대응하는 실제 호스트의 서비스 상태, 최근 로그와 의존성
- C) 조사 없이 대체 노드 생성
- D) 모든 Pod 삭제

<details>
<summary>정답 보기</summary>

**정답: B) 해당 노드에 대응하는 실제 호스트의 서비스 상태, 최근 로그와 의존성**

**설명:**

등록된 Node와 실제 호스트를 식별한 뒤 kubelet/containerd 상태, 범위를 제한한 최근 journal, disk/memory, 검증된 네트워크·자격 증명 경로를 확인합니다. TLS 검증을 끄거나 registry 자격 증명을 출력하지 않습니다. 검토한 Hybrid CLI에는 nodeadm reset 명령이 없습니다. 재시작과 재등록은 별도의 복구 판단이며, 진단 자료를 보존하고 노드 수명주기 문서의 절차를 따릅니다.

```bash
# Kubernetes Node 이름에서 추측한 호스트가 아니라 실제 대응을 확인한 호스트에서 실행합니다.
sudo systemctl status kubelet containerd --no-pager
sudo journalctl -u kubelet -u containerd --since '10 minutes ago' --no-pager -n 200
```

</details>

<span id="_4-노드-유지보수를-위해-워크로드를-안전하게-이동시키는-명령은"></span>

### 4. 계획된 노드 유지보수를 위해 워크로드 eviction을 요청하는 명령은?

- A) kubectl delete node
- B) kubectl drain
- C) kubectl cordon만 실행
- D) kubectl delete pods --all

<details>
<summary>정답 보기</summary>

**정답: B) kubectl drain**

**설명:**

drain은 Node를 스케줄 불가로 표시하고 일반적으로 Eviction API를 사용하여 적용되는 PDB를 준수합니다. Controller가 대체 Pod를 생성할 수 있지만 메모리 상태를 옮기거나 애플리케이션 연속성을 보장하지는 않습니다. 여유 용량, 배치, storage와 로컬 데이터를 먼저 확인합니다. eviction 우회, emptyDir 데이터 폐기, 모든 Pod의 종료 유예 시간 강제 변경을 기본 절차로 사용하지 않습니다. 호스트·워크로드 검증에 성공했고 원래 스케줄 가능한 Node였을 때만 uncordon합니다.

| 명령 | 범위 |
| --- | --- |
| cordon | 일반적인 새 Pod 스케줄링 방지 |
| drain | cordon 후 예외·제약에 따라 eviction 요청 |
| uncordon | 스케줄링 재허용; 상태 검증은 별도 |

minAvailable: 2인 PDB는 일치하는 정상 replica가 3개일 때 자발적 중단 1개를 허용합니다. PDB는 노드 장애나 모든 애플리케이션 오류를 방지하지 않습니다.

</details>

<span id="_5-hybrid-nodes에서-로그를-중앙-집중화하기-위한-권장-솔루션은"></span>

### 5. Hybrid 워크로드 로그를 중앙화할 수 있는 방법은?

- A) 모든 로그를 수동 복사
- B) 구성된 Fluent Bit/Fluentd 수집기와 보호된 중앙 저장소 사용
- C) 로그 수집 안 함
- D) 콘솔 출력만 확인

<details>
<summary>정답 보기</summary>

**정답: B) 구성된 Fluent Bit/Fluentd 수집기와 보호된 중앙 저장소 사용**

**설명:**

실제 container runtime 로그 경로와 parser, Kubernetes metadata 권한, buffer/checkpoint, 재시도와 인증된 TLS 출력을 구성합니다. Containerd는 일반적으로 /var/log/containers의 symlink를 통해 /var/log/pods 로그를 참조하므로 Docker 전용 /var/lib/docker/containers manifest를 그대로 복사하지 않습니다. 수집기에는 적절한 읽기 전용 host mount와 상태 저장 정책이 필요합니다. 수집기 설치가 로그 무손실을 보장하지는 않습니다.

```text
Hybrid Nodes → 구성한 수집기 → CloudWatch Logs / Loki / Elasticsearch
                    ↓
           보호된 buffer와 checkpoint
```

</details>

<span id="_6-노드-장애-시-자동으로-pod를-다른-노드로-재스케줄링하기까지-기본-대기-시간은"></span>

### 6. 기본 admission 동작에서 별도 설정이 없는 일반 Pod에 추가되는 not-ready·unreachable NoExecute toleration 시간은?

- A) 0초
- B) 30초
- C) 300초
- D) 1시간

<details>
<summary>정답 보기</summary>

**정답: C) 300초**

**설명:**

Kubernetes는 해당 taint의 toleration을 명시하지 않은 경우 일반적으로 양쪽에 tolerationSeconds: 300을 추가합니다. 이는 taint를 견디는 시간이며, 노드 장애 후 정확히 5분에 대체 워크로드가 Ready가 된다는 보장이 아닙니다. 장애 감지, taint 추가, controller, 여유 용량, volume과 기동 시간도 영향을 줍니다. DaemonSet Pod는 일반적으로 이 taint들을 시간 제한 없이 허용합니다. 시간을 줄여도 네트워크 단절 중 기존 프로세스의 중단을 입증하지 못하며, 상태를 쓰는 워크로드에는 fencing이 필요할 수 있습니다.

```yaml
# Pod spec 또는 workload의 PodTemplate.spec 아래 조각이며 완전한 Pod manifest가 아닙니다.
tolerations:
- key: node.kubernetes.io/not-ready
  operator: Exists
  effect: NoExecute
  tolerationSeconds: 60
- key: node.kubernetes.io/unreachable
  operator: Exists
  effect: NoExecute
  tolerationSeconds: 60
```

60초로 명시한 예제는 가용성·데이터 안전성 검증을 거쳐 선택해야 하며, 60초 복구 SLO를 정의하지 않습니다.

</details>

<span id="_7-eks-hybrid-nodes-업그레이드-시-권장되는-전략은"></span>

### 7. AWS Hybrid Nodes 업그레이드 지침에 맞는 접근은?

- A) 모든 노드를 동시에 업그레이드
- B) 새 호스트와 통제된 전환을 우선하고, 필요하면 검증한 절차로 한 노드씩 in-place 업그레이드
- C) 업그레이드마다 클러스터 삭제 후 재생성
- D) 업그레이드를 하지 않음

<details>
<summary>정답 보기</summary>

**정답: B) 새 호스트와 통제된 전환을 우선하고, 필요하면 검증한 절차로 한 노드씩 in-place 업그레이드**

**설명:**

AWS는 여유 용량이 있을 때 대체 호스트를 만들고 워크로드를 이전하는 방법을 우선 권장합니다. in-place nodeadm upgrade는 중단을 수반하며 Kubernetes major.minor 인자를 받습니다. 수명주기 문서에 따라 version skew, drain·데이터 검토, 실제 호스트 작업, Node UID·전체 버전·새 Lease와 워크로드 상태를 확인합니다. 고정 sleep이나 이전 Ready 상태는 작업 수락 근거가 아닙니다. 순차 실행만으로 서비스 무중단을 보장한다고 설명하지 않습니다.

각 단계 전에 backup, PDB, 여유 용량, 버전 호환성, 자격 증명 identity와 복구 계획을 확인합니다. 오류가 나면 중단하고 증거를 보존하며, 실패한 노드를 자동으로 uncordon하지 않습니다.

</details>
