# EKS Hybrid Nodes 운영 퀴즈

> **관련 문서**: [운영](../../eks-hybrid-nodes/08-operations.md)

## 객관식 문제

### 1. Hybrid Nodes 환경에서 노드 모니터링을 위해 권장되는 도구 조합은?

A. 메모장과 수동 기록
B. Prometheus + Grafana + Node Exporter
C. 이메일 알림만 사용
D. 로그 파일 수동 검토

<details>
<summary>정답 보기</summary>

**정답: B. Prometheus + Grafana + Node Exporter**

**설명:**
Kubernetes 환경에서 표준 모니터링 스택은 Prometheus, Grafana, 그리고 Node Exporter의 조합입니다.

```yaml
# Node Exporter DaemonSet
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: node-exporter
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: node-exporter
  template:
    spec:
      containers:
      - name: node-exporter
        image: prom/node-exporter:v1.6.1
        ports:
        - containerPort: 9100
```

**모니터링 스택 구성:**
- **Prometheus**: 메트릭 수집 및 저장
- **Grafana**: 시각화 대시보드
- **Node Exporter**: 노드 시스템 메트릭
- **DCGM Exporter**: GPU 메트릭 (GPU 노드)
- **Alertmanager**: 알림 관리

```bash
# Prometheus 스택 설치 (Helm)
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace
```

</details>

### 2. kubelet 인증서 갱신이 필요한 시점을 확인하는 방법은?

A. 인증서는 영구적이므로 확인 불필요
B. openssl 명령으로 인증서 만료일 확인
C. 노드가 NotReady 상태가 될 때까지 대기
D. 매일 수동으로 갱신

<details>
<summary>정답 보기</summary>

**정답: B. openssl 명령으로 인증서 만료일 확인**

**설명:**
kubelet 인증서는 일정 기간 후 만료되므로 주기적으로 확인하고 갱신해야 합니다.

```bash
# kubelet 인증서 만료일 확인
sudo openssl x509 -in /var/lib/kubelet/pki/kubelet-client-current.pem \
  -text -noout | grep -A 2 "Validity"

# 또는 kubeadm 사용
kubeadm certs check-expiration

# 인증서 갱신 (kubeadm 클러스터)
kubeadm certs renew all
```

**자동 갱신 설정 (EKS):**
```yaml
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  kubelet:
    config:
      rotateCertificates: true  # 자동 인증서 갱신
      serverTLSBootstrap: true
```

**모니터링 알림:**
```yaml
- alert: KubeletCertExpiringSoon
  expr: |
    kubelet_certificate_manager_client_expiration_seconds < 604800
  for: 1h
  labels:
    severity: warning
  annotations:
    summary: "kubelet 인증서 7일 내 만료 예정"
```

</details>

### 3. Hybrid Node에서 kubelet이 응답하지 않을 때 가장 먼저 수행해야 할 트러블슈팅 단계는?

A. 클러스터 전체 재시작
B. kubelet 서비스 상태 및 로그 확인
C. 새 노드 생성
D. 모든 Pod 삭제

<details>
<summary>정답 보기</summary>

**정답: B. kubelet 서비스 상태 및 로그 확인**

**설명:**
kubelet 문제 해결을 위한 체계적인 트러블슈팅 절차:

```bash
# 1. kubelet 서비스 상태 확인
sudo systemctl status kubelet

# 2. kubelet 로그 확인
sudo journalctl -u kubelet -f --no-pager | tail -100

# 3. 일반적인 오류 패턴 확인
sudo journalctl -u kubelet | grep -E "error|failed|unable"

# 4. 리소스 상태 확인 (메모리, 디스크)
free -h
df -h

# 5. 네트워크 연결 확인
curl -vk https://<eks-api-endpoint>:443

# 6. containerd 상태 확인
sudo systemctl status containerd

# 7. kubelet 재시작 (필요시)
sudo systemctl restart kubelet
```

**일반적인 kubelet 장애 원인:**
- 메모리 부족 (OOM)
- 디스크 공간 부족
- 인증서 만료
- 네트워크 연결 끊김
- containerd 장애

</details>

### 4. 노드 유지보수를 위해 워크로드를 안전하게 이동시키는 명령은?

A. kubectl delete node
B. kubectl drain
C. kubectl cordon만 사용
D. kubectl delete pods --all

<details>
<summary>정답 보기</summary>

**정답: B. kubectl drain**

**설명:**
`kubectl drain`은 노드를 스케줄링 불가 상태로 만들고 기존 Pod를 안전하게 퇴거시킵니다.

```bash
# 1. 노드 드레인 (워크로드 이동)
kubectl drain hybrid-node-1 \
  --ignore-daemonsets \
  --delete-emptydir-data \
  --grace-period=300

# 2. 유지보수 작업 수행
# (OS 패치, 드라이버 업데이트 등)

# 3. 노드 다시 스케줄링 가능하게 설정
kubectl uncordon hybrid-node-1
```

**drain vs cordon 비교:**

| 명령 | 동작 |
|-----|-----|
| `kubectl cordon` | 새 Pod 스케줄링 방지만 |
| `kubectl drain` | cordon + 기존 Pod 퇴거 |
| `kubectl uncordon` | 스케줄링 다시 허용 |

```yaml
# PodDisruptionBudget으로 안전한 드레인 보장
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: myapp-pdb
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: myapp
```

</details>

### 5. Hybrid Nodes에서 로그를 중앙 집중화하기 위한 권장 솔루션은?

A. 각 노드에서 수동으로 로그 파일 복사
B. Fluent Bit/Fluentd를 사용한 로그 수집 및 전송
C. 로그 수집 안 함
D. 콘솔 출력만 확인

<details>
<summary>정답 보기</summary>

**정답: B. Fluent Bit/Fluentd를 사용한 로그 수집 및 전송**

**설명:**
Fluent Bit 또는 Fluentd는 컨테이너 로그를 수집하여 중앙 로그 저장소로 전송합니다.

```yaml
# Fluent Bit DaemonSet
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: fluent-bit
  namespace: logging
spec:
  template:
    spec:
      containers:
      - name: fluent-bit
        image: fluent/fluent-bit:2.1
        volumeMounts:
        - name: varlog
          mountPath: /var/log
        - name: varlibdockercontainers
          mountPath: /var/lib/docker/containers
          readOnly: true
      volumes:
      - name: varlog
        hostPath:
          path: /var/log
      - name: varlibdockercontainers
        hostPath:
          path: /var/lib/docker/containers
```

**로그 아키텍처:**
```
[Hybrid Nodes]          [중앙 로그 시스템]
├── Node 1              ┌─────────────────┐
│   └── Fluent Bit ────>│ Elasticsearch   │
├── Node 2              │ 또는            │
│   └── Fluent Bit ────>│ CloudWatch Logs │
└── Node 3              │ 또는            │
    └── Fluent Bit ────>│ Loki            │
                        └─────────────────┘
```

</details>

### 6. 노드 장애 시 자동으로 Pod를 다른 노드로 재스케줄링하기까지 기본 대기 시간은?

A. 즉시 (0초)
B. 30초
C. 5분 (300초)
D. 1시간

<details>
<summary>정답 보기</summary>

**정답: C. 5분 (300초)**

**설명:**
Kubernetes의 기본 `pod-eviction-timeout`은 5분입니다. 노드가 NotReady 상태가 되면 5분 후에 Pod가 퇴거됩니다.

```yaml
# Node Lifecycle Controller 설정 (kube-controller-manager)
# --pod-eviction-timeout=5m0s  (기본값)
# --node-monitor-grace-period=40s  (노드 NotReady 감지)
```

**빠른 장애 조치를 위한 설정:**
```yaml
# Pod에 tolerations 추가
apiVersion: v1
kind: Pod
spec:
  tolerations:
  - key: "node.kubernetes.io/not-ready"
    operator: "Exists"
    effect: "NoExecute"
    tolerationSeconds: 60  # 60초 후 퇴거 (기본 300초)
  - key: "node.kubernetes.io/unreachable"
    operator: "Exists"
    effect: "NoExecute"
    tolerationSeconds: 60
```

**노드 상태 전환:**
```
Ready ──(40초)──> NotReady ──(5분)──> Pod 퇴거
         │                    │
    node-monitor-        pod-eviction-
    grace-period         timeout
```

</details>

### 7. EKS Hybrid Nodes 업그레이드 시 권장되는 전략은?

A. 모든 노드를 동시에 업그레이드
B. 롤링 업그레이드 (한 번에 하나씩)
C. 클러스터 삭제 후 재생성
D. 업그레이드 하지 않음

<details>
<summary>정답 보기</summary>

**정답: B. 롤링 업그레이드 (한 번에 하나씩)**

**설명:**
롤링 업그레이드는 서비스 중단 없이 노드를 순차적으로 업그레이드하는 방법입니다.

```bash
# 롤링 업그레이드 절차

# 1. 첫 번째 노드 드레인
kubectl drain hybrid-node-1 --ignore-daemonsets --delete-emptydir-data

# 2. nodeadm 업그레이드
sudo nodeadm upgrade --config-source file://nodeadm-config.yaml

# 3. 노드 상태 확인
kubectl get node hybrid-node-1

# 4. 노드 uncordon
kubectl uncordon hybrid-node-1

# 5. 워크로드 안정화 대기
sleep 60

# 6. 다음 노드로 반복
kubectl drain hybrid-node-2 ...
```

**업그레이드 체크리스트:**
- [ ] PodDisruptionBudget 설정 확인
- [ ] 노드별 순차 업그레이드
- [ ] 각 단계 후 상태 검증
- [ ] 롤백 계획 준비
- [ ] 백업 수행

</details>

