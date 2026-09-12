# AI/ML 워크로드 퀴즈

장치 할당, 학습·서빙, 스토리지, 네트워크, 보안, 관측성과 비용의 운영 경계를 확인합니다.

## 퀴즈 문제

### 1. NVIDIA device plugin의 GPU를 Pod에 할당하는 올바른 방법은 무엇인가요?

- A. requests에만 nvidia.com/gpu: 0.5를 지정한다
- B. limits에 nvidia.com/gpu 정수를 지정하고, requests를 함께 쓰면 같은 값을 지정한다
- C. nvidia.com/gpu라는 node annotation만 추가한다
- D. RuntimeClass 이름을 nvidia-mps로 정하면 자동 공유된다

<details>
<summary>정답 및 설명</summary>

**정답: B. limits에 nvidia.com/gpu 정수를 지정하고, requests를 함께 쓰면 같은 값을 지정한다**

limits만 있으면 동일한 request가 적용됩니다. GPU allocatable은 node label이 아닌 자원 용량입니다. GPU Feature Discovery label, MIG, MPS, time-slicing은 별도 구성이며 공유 slot을 GPU 메모리 비율로 해석하면 안 됩니다.

[장치 할당·공유 예제](../../ai-ml/01-ai-ml-workloads.md#gpu-allocation)
</details>

### 2. TensorFlow의 분산 역할을 지원하는 설치된 레거시 Kubeflow 리소스는 무엇인가요?

- A. Deployment가 모든 TF_CONFIG를 자동 생성한다
- B. Job이 학습 성공과 모든 워커의 동시 배치를 보장한다
- C. TFJob이 프레임워크별 역할·설정을 제공한다
- D. TFJob은 Kubernetes 내장 리소스라 설치가 불필요하다

<details>
<summary>정답 및 설명</summary>

**정답: C. TFJob이 프레임워크별 역할·설정을 제공한다**

TFJob CRD와 컨트롤러가 필요합니다. restartPolicy, framework strategy, checkpoint와 저장소·네트워크를 준비해야 하며 자동 복구나 gang scheduling이 모든 환경에서 보장되지는 않습니다. 일반 Job도 실제 실행 코드를 제공하면 학습할 수 있습니다.

[Trainer와 레거시 API](../../ai-ml/kubeflow/05-training-operator.md)
</details>

### 3. 기존 FSx for Lustre 파일시스템을 CSI로 연결할 때 올바른 구분은 무엇인가요?

- A. Lustre CR과 StorageClass에 기존 파일시스템 ID를 넣으면 모든 설정이 끝난다
- B. 정적 PV의 volumeHandle·dnsname·mountname과 이를 바인딩하는 PVC를 사용한다
- C. SCRATCH_2는 모든 persistent backup·throughput 옵션을 지원한다
- D. 마운트 없는 /data에 FIO를 실행하면 FSx 성능을 측정한다

<details>
<summary>정답 및 설명</summary>

**정답: B. 정적 PV의 volumeHandle·dnsname·mountname과 이를 바인딩하는 PVC를 사용한다**

정적 연결과 새 파일시스템을 생성하는 동적 provisioning은 다릅니다. capacity, IOPS/throughput, latency, 접근 패턴·POSIX 권한·AZ/네트워크·백업을 비교하세요. 테스트는 전용 경로에 실제 볼륨을 마운트한 뒤 수행해야 합니다.

[정적 PV/PVC와 동적 방식](../../ai-ml/01-ai-ml-workloads.md#storage-and-caching)
</details>

### 4. AI/ML 자원 할당을 정하는 근거로 가장 적절한 것은 무엇인가요?

- A. 모든 작업은 GPU가 필수다
- B. CPU·메모리·GPU 사용량, 모델 크기, 데이터 I/O, 지연·처리량 측정
- C. 항상 최대 요청량
- D. requests를 생략하면 가장 효율적이다

<details>
<summary>정답 및 설명</summary>

**정답: B. CPU·메모리·GPU 사용량, 모델 크기, 데이터 I/O, 지연·처리량 측정**

CPU 학습이나 가속기별 대안도 있습니다. OMP/MKL thread 설정은 지원하는 라이브러리에만 작용하고 GPU를 공유하지 않습니다. CUDA allocator 설정과 Kubernetes GPU 할당·메모리 격리도 별도입니다. VPA 적용은 모드와 workload 재시작·호환성에 따라 달라집니다.

[자원·배치 설계](../../ai-ml/01-ai-ml-workloads.md#placement-and-topology)
</details>

### 5. KServe 같은 서빙 플랫폼을 선택할 때 확인할 것은 무엇인가요?

- A. 어떤 모델 URI든 즉시 서빙된다
- B. 서버 이미지·모델 형식·프로토콜·스토리지·배포 모드가 실제 요구에 맞는지
- C. 일반 Deployment는 추론을 할 수 없다
- D. 모든 모드에서 같은 캐너리와 scale-to-zero가 제공된다

<details>
<summary>정답 및 설명</summary>

**정답: B. 서버 이미지·모델 형식·프로토콜·스토리지·배포 모드가 실제 요구에 맞는지**

일반 Deployment도 추론 서버를 운영할 수 있습니다. KServe의 Knative/Standard와 Seldon의 버전별 API는 다릅니다. 모델 설명·전후처리·가중치 라우팅·batch inference가 모두 기본 활성화된다고 가정하면 안 됩니다. TorchServe는 현재 유지보수되는 기본 선택이 아닙니다.

[KServe 모드와 runtime](../../ai-ml/kubeflow/06-kserve.md)
</details>

### 6. GPU 활용률이나 요청량으로 HPA를 구성할 때 올바른 설명은 무엇인가요?

- A. nvidia.com/gpu 할당량이 Resource GPU 사용률 메트릭으로 자동 제공된다
- B. exporter와 custom/external metrics adapter가 필요하며 대상별 label·단위·집계를 확인한다
- C. 모델 정확도가 낮으면 replica를 늘려 해결한다
- D. HPA 여러 개를 같은 Deployment에 연결하면 효과가 합산된다

<details>
<summary>정답 및 설명</summary>

**정답: B. exporter와 custom/external metrics adapter가 필요하며 대상별 label·단위·집계를 확인한다**

metrics-server의 기본 Resource 경로는 CPU·메모리입니다. GPU/요청 신호는 별도 수집·adapter가 필요합니다. Pod 메트릭은 namespace/Pod별 값이어야 하며 global avg로 label을 잃으면 대응할 수 없습니다. 하나의 scaling owner를 사용하고 지연 percentile보다 부하·큐가 더 적합한지 검증하세요.

[HPA 예제](../../ai-ml/01-ai-ml-workloads.md#hpa-and-metrics)
</details>

### 7. 분산 학습 네트워크와 배치에 대한 올바른 설명은 무엇인가요?

- A. zone annotation만 넣으면 그 AZ에 배치된다
- B. hostPath로 GPU 장치를 마운트하면 EFA·GPUDirect가 구성된다
- C. 실제 node label 기반 배치, 지원 장치·driver·plugin·통신 라이브러리·네트워크 정책을 함께 검증한다
- D. NCCL은 반드시 MPI 위에서 통신한다

<details>
<summary>정답 및 설명</summary>

**정답: C. 실제 node label 기반 배치, 지원 장치·driver·plugin·통신 라이브러리·네트워크 정책을 함께 검증한다**

NCCL의 EFA 경로는 AWS OFI NCCL과 libfabric을 사용합니다. MPI는 실행기로 쓰일 수 있습니다. Multus/SR-IOV, MTU, RDMA 설정은 환경별 조건이 필요하고 일반 NIC 템플릿을 EKS에 그대로 적용하면 안 됩니다. NetworkPolicy도 필요한 통신을 막으면 성능·가용성에 영향을 줍니다.

[분산 학습 경계](../../ai-ml/01-ai-ml-workloads.md#kubeflow-and-distributed-training)
</details>

### 8. 모델·데이터 접근을 보호하는 올바른 설명은 무엇인가요?

- A. Secret base64가 암호화다
- B. Kubernetes RBAC만으로 S3·KMS 권한을 부여한다
- C. API RBAC, workload IAM, 암호화·키 관리, 파일 자격 증명과 네트워크 정책을 각각 구성한다
- D. 복호화 키를 환경 변수로 넣고 큰 모델을 Secret에 저장하는 것이 기본이다

<details>
<summary>정답 및 설명</summary>

**정답: C. API RBAC, workload IAM, 암호화·키 관리, 파일 자격 증명과 네트워크 정책을 각각 구성한다**

Secret에는 크기 제한이 있고 base64는 인코딩입니다. 큰 모델은 오브젝트 저장소에서 권한·무결성 검증과 함께 관리하세요. Secret volume을 마운트하는 Pod의 서비스 계정에 Secret get 권한이 항상 필요한 것은 아니며 API 읽기와 kubelet volume 전달은 다릅니다. PodSecurityPolicy는 제거되었고 현재 admission/PSS를 검토해야 합니다.

[데이터와 모델 접근](../../ai-ml/01-ai-ml-workloads.md#data-and-model-access)
</details>

### 9. ML 서비스의 관측에서 무엇을 구분해야 하나요?

- A. GPU 사용률만으로 모델 정확도를 알 수 있다
- B. ServiceMonitor는 Pod label을 직접 선택한다
- C. 서비스 오류·지연·처리량, 자원 사용량, 정답 기반 모델 품질을 별도로 관측한다
- D. 컨테이너 로그는 모두 Docker JSON이다

<details>
<summary>정답 및 설명</summary>

**정답: C. 서비스 오류·지연·처리량, 자원 사용량, 정답 기반 모델 품질을 별도로 관측한다**

ServiceMonitor는 Service label과 named port를 선택합니다. latency histogram은 성공·실패를 포함할 범위를 정하고 오류 counter를 중복 집계하지 않아야 합니다. 정확도에는 정답 데이터가 필요합니다. CRI framing과 앱 JSON, Grafana datasource·패널 스키마, 알림의 label별 집계와 무트래픽 처리를 검증하세요.

[메트릭과 로그](../../ai-ml/01-ai-ml-workloads.md#prometheus-and-grafana)
</details>

### 10. 비용 최적화를 검증하는 올바른 방식은 무엇인가요?

- A. 모든 작업에 Spot을 쓰면 된다
- B. 최신 인스턴스가 항상 가장 저렴하다
- C. 요구 성능과 총비용, interruption 복구·checkpoint, 실제 Pod·노드 회수를 측정한다
- D. 밤에 실행하면 On-Demand 단가가 자동으로 낮아진다

<details>
<summary>정답 및 설명</summary>

**정답: C. 요구 성능과 총비용, interruption 복구·checkpoint, 실제 Pod·노드 회수를 측정한다**

Pod 수 감소가 EC2 종료를 뜻하지 않습니다. 인스턴스 가용성·quota·AMI·driver와 NodePool limits를 확인하세요. training taint에는 맞는 toleration이 필요하며 CPU/GPU 노드 혼합은 EKS Hybrid Nodes와 다릅니다. Autoscaler 설정 ConfigMap을 만들기만 해서는 controller flag가 변경되지 않습니다.

[Spot과 노드 공급](../../ai-ml/01-ai-ml-workloads.md#spot-and-node-provisioning)
</details>

---

[학습 자료로 돌아가기](../../ai-ml/01-ai-ml-workloads.md)
