# vLLM 배포 퀴즈

이 퀴즈는 Kubernetes에서 vLLM(Vector Language Model)을 배포하는 방법에 대한 이해를 테스트합니다.

## 퀴즈 문제

### 1. vLLM(Vector Language Model)의 주요 목적은 무엇인가요?

A. 이미지 처리 가속화  
B. 대규모 언어 모델(LLM) 추론 최적화 및 가속화  
C. 데이터베이스 쿼리 최적화  
D. 네트워크 트래픽 관리  

<details>
<summary>정답 및 설명</summary>

**정답: B. 대규모 언어 모델(LLM) 추론 최적화 및 가속화**

**설명:**
vLLM(Vector Language Model)의 주요 목적은 대규모 언어 모델(LLM) 추론을 최적화하고 가속화하는 것입니다. vLLM은 PagedAttention이라는 혁신적인 어텐션 알고리즘을 사용하여 메모리 관리를 최적화하고, 높은 처리량과 낮은 지연 시간으로 LLM 추론을 수행할 수 있게 해줍니다.

**vLLM의 주요 특징:**
1. **PagedAttention**: 메모리 효율적인 어텐션 메커니즘으로, GPU 메모리 사용을 최적화합니다.
2. **연속 배치 처리**: 동적으로 요청을 배치 처리하여 처리량을 향상시킵니다.
3. **분산 추론**: 여러 GPU와 노드에 걸쳐 대규모 모델을 분산 처리합니다.
4. **다양한 모델 지원**: Llama, GPT-NeoX, Falcon, MPT 등 다양한 오픈 소스 LLM을 지원합니다.
5. **OpenAI 호환 API**: OpenAI API와 호환되는 인터페이스를 제공합니다.

**PagedAttention의 작동 방식:**
PagedAttention은 운영 체제의 가상 메모리 관리에서 영감을 받은 기술로, KV(Key-Value) 캐시를 효율적으로 관리합니다. 기존 방식은 각 요청마다 고정된 크기의 메모리 블록을 할당하지만, PagedAttention은 필요한 만큼만 메모리를 할당하고 재사용합니다.

**vLLM의 성능 이점:**
1. **높은 처리량**: 기존 솔루션 대비 2-4배 높은 처리량
2. **메모리 효율성**: 최대 8배 더 많은 동시 요청 처리 가능
3. **낮은 지연 시간**: 효율적인 메모리 관리로 응답 시간 단축
4. **자원 활용도 향상**: GPU 자원을 더 효율적으로 활용

**vLLM 사용 사례:**
1. **대화형 AI 서비스**: 챗봇, 가상 비서 등
2. **텍스트 생성 서비스**: 콘텐츠 생성, 요약, 번역 등
3. **코드 생성 및 완성**: 프로그래밍 지원 도구
4. **대규모 텍스트 처리**: 문서 분석, 정보 추출 등

**다른 옵션들의 문제점:**
- A. 이미지 처리 가속화: vLLM은 텍스트 기반 언어 모델을 위한 것이며, 이미지 처리에 특화되어 있지 않습니다.
- C. 데이터베이스 쿼리 최적화: vLLM은 데이터베이스 쿼리 최적화와 관련이 없습니다.
- D. 네트워크 트래픽 관리: vLLM은 네트워크 트래픽 관리와 관련이 없습니다.
</details>

### 2. Kubernetes에서 vLLM을 배포할 때 가장 중요한 리소스 요구 사항은 무엇인가요?

A. 대용량 CPU 및 메모리  
B. 고성능 GPU 및 충분한 GPU 메모리  
C. 고속 네트워크 인터페이스  
D. 대용량 영구 스토리지  

<details>
<summary>정답 및 설명</summary>

**정답: B. 고성능 GPU 및 충분한 GPU 메모리**

**설명:**
Kubernetes에서 vLLM을 배포할 때 가장 중요한 리소스 요구 사항은 고성능 GPU 및 충분한 GPU 메모리입니다. 대규모 언어 모델(LLM)은 수십억 또는 수천억 개의 파라미터를 가지고 있으며, 이러한 모델을 효율적으로 실행하기 위해서는 강력한 GPU 연산 능력과 모델 파라미터를 저장할 수 있는 충분한 GPU 메모리가 필수적입니다.

**GPU 요구 사항:**
1. **GPU 유형**: NVIDIA A100, H100, V100, RTX A6000 등 고성능 GPU
2. **GPU 메모리**: 모델 크기에 따라 다르지만, 일반적으로 다음과 같은 요구 사항이 있습니다:
   - 7B 파라미터 모델: 최소 16GB GPU 메모리
   - 13B 파라미터 모델: 최소 24GB GPU 메모리
   - 70B 파라미터 모델: 최소 80GB GPU 메모리 또는 여러 GPU에 분산
3. **GPU 수**: 처리량 요구 사항과 모델 크기에 따라 다르지만, 대규모 모델은 여러 GPU에 분산 배포해야 합니다.

**vLLM 배포를 위한 GPU 리소스 요청 예시:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-service
spec:
  replicas: 1
  selector:
    matchLabels:
      app: vllm
  template:
    metadata:
      labels:
        app: vllm
    spec:
      containers:
      - name: vllm
        image: vllm/vllm-openai:latest
        args:
        - --model=meta-llama/Llama-2-7b-chat-hf
        - --tensor-parallel-size=1
        resources:
          limits:
            nvidia.com/gpu: 1
          requests:
            nvidia.com/gpu: 1
            cpu: 4
            memory: 16Gi
```

**대규모 모델을 위한 분산 배포 예시:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-large-model
spec:
  replicas: 1
  selector:
    matchLabels:
      app: vllm-large
  template:
    metadata:
      labels:
        app: vllm-large
    spec:
      nodeSelector:
        gpu-type: a100-80gb
      containers:
      - name: vllm
        image: vllm/vllm-openai:latest
        args:
        - --model=meta-llama/Llama-2-70b-chat-hf
        - --tensor-parallel-size=8
        - --max-model-len=4096
        resources:
          limits:
            nvidia.com/gpu: 8
          requests:
            nvidia.com/gpu: 8
            cpu: 32
            memory: 128Gi
```

**GPU 메모리 요구 사항 계산:**
LLM의 GPU 메모리 요구 사항은 다음과 같은 요소에 의해 결정됩니다:
1. **모델 파라미터**: 각 파라미터는 일반적으로 2바이트(FP16) 또는 4바이트(FP32)를 차지합니다.
2. **KV 캐시**: 각 토큰에 대한 키-값 캐시는 추가 메모리를 필요로 합니다.
3. **배치 크기**: 동시에 처리하는 요청 수가 증가하면 메모리 요구 사항도 증가합니다.
4. **컨텍스트 길이**: 더 긴 컨텍스트 길이는 더 많은 KV 캐시 메모리를 필요로 합니다.

**대략적인 메모리 요구 사항 계산식:**
```
필요한 GPU 메모리 = 모델 크기 + (배치 크기 × 시퀀스 길이 × 숨겨진 크기 × 레이어 수 × 4바이트)
```

**다른 리소스 요구 사항:**
1. **CPU**: 전처리 및 후처리를 위한 충분한 CPU 코어
2. **시스템 메모리**: 모델 로딩 및 처리를 위한 충분한 RAM
3. **스토리지**: 모델 가중치 저장을 위한 충분한 스토리지
4. **네트워크**: 분산 추론을 위한 고속 네트워크 연결

**다른 옵션들의 문제점:**
- A. 대용량 CPU 및 메모리: CPU는 LLM 추론에 효율적이지 않으며, 시스템 메모리만으로는 GPU 메모리를 대체할 수 없습니다.
- C. 고속 네트워크 인터페이스: 분산 추론에 중요하지만, GPU 및 GPU 메모리보다 우선순위가 낮습니다.
- D. 대용량 영구 스토리지: 모델 가중치 저장에 필요하지만, 추론 성능에 직접적인 영향을 미치지 않습니다.
</details>
### 3. Kubernetes에서 vLLM을 위한 최적의 스토리지 솔루션은 무엇인가요?

A. emptyDir 볼륨  
B. hostPath 볼륨  
C. 고성능 분산 파일 시스템(예: FSx for Lustre)  
D. 일반 네트워크 파일 시스템(NFS)  

<details>
<summary>정답 및 설명</summary>

**정답: C. 고성능 분산 파일 시스템(예: FSx for Lustre)**

**설명:**
Kubernetes에서 vLLM을 위한 최적의 스토리지 솔루션은 고성능 분산 파일 시스템(예: FSx for Lustre)입니다. vLLM은 대규모 언어 모델을 처리하기 위해 모델 가중치 파일을 빠르게 로드해야 하며, 특히 분산 추론 환경에서는 여러 노드가 동일한 모델 파일에 동시에 접근해야 합니다. 고성능 분산 파일 시스템은 높은 처리량, 낮은 지연 시간, 병렬 접근 기능을 제공하여 이러한 요구 사항을 충족합니다.

**고성능 분산 파일 시스템의 장점:**
1. **높은 처리량**: 대용량 모델 파일을 빠르게 로드할 수 있습니다.
2. **병렬 접근**: 여러 노드가 동시에 동일한 파일에 접근할 수 있습니다.
3. **확장성**: 스토리지 용량과 성능을 필요에 따라 확장할 수 있습니다.
4. **데이터 일관성**: 여러 노드 간에 일관된 데이터 뷰를 제공합니다.
5. **내구성**: 데이터 복제 및 백업 기능을 통해 데이터 손실 위험을 줄입니다.

**AWS FSx for Lustre 구성 예시:**
```yaml
# StorageClass 정의
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fsx-lustre
provisioner: fsx.csi.aws.com
parameters:
  subnetId: subnet-0eabfaa81fb22bcaf
  securityGroupIds: sg-068000ccf82dfba88
  deploymentType: SCRATCH_2
  automaticBackupRetentionDays: "0"
  dailyAutomaticBackupStartTime: "00:00"
  perUnitStorageThroughput: "200"
  dataCompressionType: "NONE"
mountOptions:
  - flock

---
# PersistentVolumeClaim 정의
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: vllm-models
spec:
  accessModes:
    - ReadWriteMany
  storageClassName: fsx-lustre
  resources:
    requests:
      storage: 1200Gi

---
# vLLM 배포에서 사용
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-service
spec:
  replicas: 1
  selector:
    matchLabels:
      app: vllm
  template:
    metadata:
      labels:
        app: vllm
    spec:
      containers:
      - name: vllm
        image: vllm/vllm-openai:latest
        args:
        - --model=/models/llama-2-70b
        - --tensor-parallel-size=8
        volumeMounts:
        - name: model-storage
          mountPath: /models
        resources:
          limits:
            nvidia.com/gpu: 8
      volumes:
      - name: model-storage
        persistentVolumeClaim:
          claimName: vllm-models
```

**Google Cloud Filestore 구성 예시:**
```yaml
# StorageClass 정의
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: filestore-hpc
provisioner: filestore.csi.storage.gke.io
parameters:
  tier: ENTERPRISE
  network: default
  location: us-central1-a

---
# PersistentVolumeClaim 정의
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: vllm-models
spec:
  accessModes:
    - ReadWriteMany
  storageClassName: filestore-hpc
  resources:
    requests:
      storage: 1200Gi
```

**Azure NetApp Files 구성 예시:**
```yaml
# StorageClass 정의
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: netapp-files-premium
provisioner: netapp.io/trident
parameters:
  backendType: "azure-netapp-files"
  serviceLevel: "Premium"

---
# PersistentVolumeClaim 정의
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: vllm-models
spec:
  accessModes:
    - ReadWriteMany
  storageClassName: netapp-files-premium
  resources:
    requests:
      storage: 1200Gi
```

**다른 스토리지 옵션과의 비교:**

| 스토리지 옵션 | 처리량 | 지연 시간 | 다중 노드 접근 | 확장성 | 영구성 |
|-------------|-------|---------|------------|-------|-------|
| emptyDir | 높음 | 매우 낮음 | 불가능 | 제한적 | 임시 |
| hostPath | 높음 | 매우 낮음 | 불가능 | 제한적 | 노드 종속 |
| NFS | 중간 | 중간 | 가능 | 중간 | 영구적 |
| FSx for Lustre | 매우 높음 | 낮음 | 가능 | 높음 | 영구적 |
| Google Filestore | 높음 | 낮음 | 가능 | 높음 | 영구적 |
| Azure NetApp Files | 높음 | 낮음 | 가능 | 높음 | 영구적 |

**모델 로딩 성능 최적화 전략:**
1. **메모리 매핑**: 대용량 모델 파일을 메모리에 직접 매핑하여 로딩 시간 단축
2. **모델 샤딩**: 모델을 여러 샤드로 분할하여 병렬로 로드
3. **캐싱**: 자주 사용하는 모델을 메모리에 캐싱하여 재로딩 방지
4. **사전 로딩**: 서비스 시작 시 모델을 미리 로드하여 첫 요청 지연 시간 감소

**다른 옵션들의 문제점:**
- A. emptyDir 볼륨: 임시 스토리지로, 파드가 재시작되면 데이터가 손실됩니다. 대용량 모델 파일 저장에 적합하지 않습니다.
- B. hostPath 볼륨: 노드 로컬 스토리지에 의존하며, 다중 노드 환경에서 데이터 공유가 어렵습니다.
- D. 일반 네트워크 파일 시스템(NFS): 처리량과 지연 시간 측면에서 고성능 분산 파일 시스템보다 성능이 떨어집니다.
</details>

### 4. vLLM에서 텐서 병렬 처리(Tensor Parallelism)의 주요 목적은 무엇인가요?

A. 여러 사용자 요청을 병렬로 처리  
B. 대규모 모델을 여러 GPU에 분산하여 메모리 요구 사항 감소  
C. 데이터 전처리 가속화  
D. 네트워크 통신 최적화  

<details>
<summary>정답 및 설명</summary>

**정답: B. 대규모 모델을 여러 GPU에 분산하여 메모리 요구 사항 감소**

**설명:**
vLLM에서 텐서 병렬 처리(Tensor Parallelism)의 주요 목적은 대규모 모델을 여러 GPU에 분산하여 메모리 요구 사항을 감소시키는 것입니다. 대규모 언어 모델(LLM)은 종종 단일 GPU의 메모리 용량을 초과하는 수십억 또는 수천억 개의 파라미터를 가지고 있습니다. 텐서 병렬 처리는 모델의 레이어를 여러 GPU에 분할하여 각 GPU가 모델의 일부만 저장하고 처리하도록 함으로써 이 문제를 해결합니다.

**텐서 병렬 처리의 작동 방식:**
1. **모델 분할**: 모델의 각 레이어(특히 어텐션 및 MLP 레이어)를 여러 GPU에 분할합니다.
2. **병렬 계산**: 각 GPU는 할당된 모델 부분에 대한 계산을 수행합니다.
3. **동기화**: 필요한 경우 GPU 간에 중간 결과를 동기화합니다.
4. **결과 집계**: 최종 출력을 생성하기 위해 각 GPU의 결과를 집계합니다.

**vLLM에서 텐서 병렬 처리 구성 예시:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-tensor-parallel
spec:
  replicas: 1
  selector:
    matchLabels:
      app: vllm
  template:
    metadata:
      labels:
        app: vllm
    spec:
      nodeSelector:
        nvidia.com/gpu.product: A100-SXM4-80GB
      containers:
      - name: vllm
        image: vllm/vllm-openai:latest
        args:
        - --model=meta-llama/Llama-2-70b-chat-hf
        - --tensor-parallel-size=8  # 8개 GPU에 모델 분산
        - --max-model-len=4096
        - --gpu-memory-utilization=0.9
        resources:
          limits:
            nvidia.com/gpu: 8  # 8개 GPU 요청
```

**텐서 병렬 처리 크기 선택 가이드:**
1. **모델 크기**: 모델 파라미터 수에 따라 필요한 텐서 병렬 처리 크기가 결정됩니다.
   - 7B 파라미터 모델: 1-2 GPU
   - 13B 파라미터 모델: 2-4 GPU
   - 70B 파라미터 모델: 8-16 GPU
   - 175B 파라미터 모델: 16개 이상의 GPU

2. **GPU 메모리**: 사용 가능한 GPU 메모리에 따라 텐서 병렬 처리 크기를 조정해야 합니다.
   - 24GB GPU: 작은 모델에 적합
   - 40GB GPU: 중간 크기 모델에 적합
   - 80GB GPU: 대규모 모델에 적합

3. **성능 고려 사항**: 텐서 병렬 처리는 GPU 간 통신 오버헤드를 발생시킵니다.
   - 너무 작은 텐서 병렬 처리 크기: 메모리 부족 문제 발생
   - 너무 큰 텐서 병렬 처리 크기: 통신 오버헤드로 인한 성능 저하

**텐서 병렬 처리 vs 다른 병렬화 기법:**
1. **데이터 병렬 처리(Data Parallelism)**: 동일한 모델의 여러 복사본이 서로 다른 데이터 배치를 처리합니다. 주로 학습에 사용됩니다.
2. **파이프라인 병렬 처리(Pipeline Parallelism)**: 모델의 레이어를 순차적으로 여러 GPU에 분산합니다.
3. **텐서 병렬 처리(Tensor Parallelism)**: 개별 레이어의 계산을 여러 GPU에 분산합니다.

**텐서 병렬 처리의 장점:**
1. **메모리 효율성**: 대규모 모델을 여러 GPU에 분산하여 메모리 요구 사항 감소
2. **단일 요청 지연 시간 감소**: 병렬 계산으로 추론 속도 향상
3. **리소스 활용도 향상**: GPU 자원을 더 효율적으로 활용

**텐서 병렬 처리의 단점:**
1. **통신 오버헤드**: GPU 간 데이터 전송으로 인한 오버헤드 발생
2. **구현 복잡성**: 모델 분할 및 동기화 로직이 복잡함
3. **하드웨어 요구 사항**: 고속 GPU 상호 연결(NVLink, NVSwitch 등) 필요

**다른 옵션들의 문제점:**
- A. 여러 사용자 요청을 병렬로 처리: 이는 배치 처리 또는 요청 병렬 처리의 목적입니다.
- C. 데이터 전처리 가속화: 텐서 병렬 처리는 데이터 전처리가 아닌 모델 추론에 초점을 맞춥니다.
- D. 네트워크 통신 최적화: 텐서 병렬 처리는 네트워크 통신을 최적화하는 것이 아니라 오히려 추가적인 통신을 발생시킵니다.
</details>
### 5. Kubernetes에서 vLLM 서비스의 고가용성을 보장하기 위한 가장 효과적인 방법은 무엇인가요?

A. 단일 파드에 여러 컨테이너 배포  
B. 여러 복제본과 적절한 리소스 요청/제한을 가진 Deployment 사용  
C. DaemonSet으로 모든 노드에 배포  
D. CronJob으로 주기적으로 재시작  

<details>
<summary>정답 및 설명</summary>

**정답: B. 여러 복제본과 적절한 리소스 요청/제한을 가진 Deployment 사용**

**설명:**
Kubernetes에서 vLLM 서비스의 고가용성을 보장하기 위한 가장 효과적인 방법은 여러 복제본과 적절한 리소스 요청/제한을 가진 Deployment를 사용하는 것입니다. 이 접근 방식은 서비스 중단 없이 트래픽을 처리하고, 노드 장애 시 자동 복구를 제공하며, 부하에 따라 확장할 수 있는 능력을 제공합니다.

**고가용성 vLLM 배포 구성 예시:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-service
  labels:
    app: vllm
spec:
  replicas: 3  # 여러 복제본 실행
  selector:
    matchLabels:
      app: vllm
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0  # 제로 다운타임 업데이트
  template:
    metadata:
      labels:
        app: vllm
    spec:
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchExpressions:
                - key: app
                  operator: In
                  values:
                  - vllm
              topologyKey: "kubernetes.io/hostname"  # 다른 노드에 파드 분산
      containers:
      - name: vllm
        image: vllm/vllm-openai:latest
        args:
        - --model=meta-llama/Llama-2-7b-chat-hf
        - --tensor-parallel-size=1
        resources:
          requests:
            nvidia.com/gpu: 1
            cpu: 4
            memory: 16Gi
          limits:
            nvidia.com/gpu: 1
            cpu: 8
            memory: 32Gi
        readinessProbe:  # 준비 상태 확인
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 60
          periodSeconds: 10
        livenessProbe:  # 활성 상태 확인
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 120
          periodSeconds: 30
        ports:
        - containerPort: 8000
          name: http
```

**서비스 구성 예시:**
```yaml
apiVersion: v1
kind: Service
metadata:
  name: vllm-service
spec:
  selector:
    app: vllm
  ports:
  - port: 80
    targetPort: 8000
    protocol: TCP
  type: ClusterIP
```

**수평 파드 자동 확장 구성 예시:**
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: vllm-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: vllm-service
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Pods
    pods:
      metric:
        name: inference_requests_per_second
      target:
        type: AverageValue
        averageValue: 100
```

**고가용성을 위한 추가 구성:**

1. **파드 중단 예산(PDB) 설정**:
```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: vllm-pdb
spec:
  minAvailable: 2  # 항상 최소 2개의 파드가 실행 중이어야 함
  selector:
    matchLabels:
      app: vllm
```

2. **노드 어피니티 및 톨러레이션**:
```yaml
affinity:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
      - matchExpressions:
        - key: nvidia.com/gpu.product
          operator: In
          values:
          - A100-SXM4-40GB
          - A100-SXM4-80GB
tolerations:
- key: nvidia.com/gpu
  operator: Exists
  effect: NoSchedule
```

3. **토폴로지 분산 제약 조건**:
```yaml
topologySpreadConstraints:
- maxSkew: 1
  topologyKey: topology.kubernetes.io/zone
  whenUnsatisfiable: ScheduleAnyway
  labelSelector:
    matchLabels:
      app: vllm
```

**고가용성 구성의 주요 이점:**
1. **내결함성**: 노드 또는 파드 장애 시에도 서비스 계속 제공
2. **부하 분산**: 여러 인스턴스에 걸쳐 트래픽 분산
3. **제로 다운타임 업데이트**: 롤링 업데이트를 통한 무중단 배포
4. **자동 확장**: 부하에 따른 자동 스케일링
5. **자동 복구**: 실패한 파드 자동 재시작

**로드 밸런싱 전략:**
1. **서비스 내부 로드 밸런싱**: Kubernetes Service를 통한 기본 로드 밸런싱
2. **외부 로드 밸런싱**: Ingress 또는 클라우드 로드 밸런서를 통한 외부 트래픽 분산
3. **세션 어피니티**: 필요한 경우 동일한 클라이언트 요청을 동일한 파드로 라우팅

**모니터링 및 알림:**
```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: vllm-monitor
spec:
  selector:
    matchLabels:
      app: vllm
  endpoints:
  - port: http
    interval: 15s
    path: /metrics
```

**다른 옵션들의 문제점:**
- A. 단일 파드에 여러 컨테이너 배포: 이는 노드 장애 시 전체 서비스가 중단될 수 있으며, 진정한 고가용성을 제공하지 않습니다.
- C. DaemonSet으로 모든 노드에 배포: 모든 노드에 GPU가 있다는 보장이 없으며, 리소스 낭비를 초래할 수 있습니다.
- D. CronJob으로 주기적으로 재시작: 이는 서비스 중단을 초래하며, 고가용성 솔루션이 아닙니다.
</details>

### 6. vLLM에서 "연속 배치 처리(Continuous Batching)"의 주요 이점은 무엇인가요?

A. 모델 정확도 향상  
B. 처리량 증가 및 GPU 활용도 향상  
C. 모델 크기 축소  
D. 네트워크 대역폭 절약  

<details>
<summary>정답 및 설명</summary>

**정답: B. 처리량 증가 및 GPU 활용도 향상**

**설명:**
vLLM에서 "연속 배치 처리(Continuous Batching)"의 주요 이점은 처리량 증가 및 GPU 활용도 향상입니다. 연속 배치 처리는 다양한 길이와 시작 시간을 가진 요청을 동적으로 배치로 그룹화하여 처리함으로써, GPU 자원을 더 효율적으로 활용하고 전체 시스템 처리량을 크게 향상시킵니다.

**전통적인 배치 처리 vs 연속 배치 처리:**
1. **전통적인 배치 처리**:
   - 고정된 크기의 배치를 형성하기 위해 요청을 대기시킴
   - 모든 요청이 동시에 시작하고 종료됨
   - 배치 내 가장 긴 시퀀스에 맞춰 패딩 필요
   - 새 요청은 현재 배치가 완료될 때까지 대기해야 함

2. **연속 배치 처리**:
   - 요청이 도착하는 대로 동적으로 처리
   - 다양한 시작 시간과 길이를 가진 요청을 동시에 처리
   - 불필요한 패딩 없이 효율적인 메모리 사용
   - 완료된 요청의 자원이 즉시 새 요청에 할당됨

**연속 배치 처리의 작동 방식:**
1. **동적 요청 스케줄링**: 요청이 도착하면 즉시 처리 시작
2. **토큰별 처리**: 각 요청은 토큰 단위로 처리되며, 각 단계에서 새 토큰 생성
3. **자원 재할당**: 요청이 완료되면 해당 자원이 즉시 새 요청에 할당됨
4. **KV 캐시 관리**: PagedAttention을 통해 효율적인 KV 캐시 관리

**연속 배치 처리의 이점:**
1. **높은 처리량**: GPU 자원을 더 효율적으로 활용하여 초당 처리할 수 있는 요청 수 증가
2. **낮은 지연 시간**: 요청이 배치가 형성될 때까지 대기할 필요 없음
3. **자원 활용도 향상**: GPU 계산 및 메모리 자원의 유휴 시간 감소
4. **다양한 요청 길이 처리**: 다양한 길이의 요청을 효율적으로 처리

**vLLM 구성에서 연속 배치 처리 설정:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-service
spec:
  replicas: 1
  selector:
    matchLabels:
      app: vllm
  template:
    metadata:
      labels:
        app: vllm
    spec:
      containers:
      - name: vllm
        image: vllm/vllm-openai:latest
        args:
        - --model=meta-llama/Llama-2-7b-chat-hf
        - --tensor-parallel-size=1
        - --max-num-batched-tokens=8192  # 배치당 최대 토큰 수
        - --max-num-seqs=256  # 동시에 처리할 수 있는 최대 시퀀스 수
        - --max-model-len=4096  # 최대 컨텍스트 길이
        resources:
          limits:
            nvidia.com/gpu: 1
```

**연속 배치 처리 성능 최적화:**
1. **최적의 배치 크기 설정**:
   - `max-num-batched-tokens`: 한 번에 처리할 수 있는 최대 토큰 수
   - `max-num-seqs`: 동시에 처리할 수 있는 최대 시퀀스 수

2. **GPU 메모리 활용도 조정**:
   - `gpu-memory-utilization`: GPU 메모리 사용 비율 설정 (0.0-1.0)

3. **KV 캐시 관리**:
   - `max-model-len`: 최대 컨텍스트 길이 설정
   - `block-size`: PagedAttention 블록 크기 설정

**성능 벤치마크 예시:**
| 배치 처리 방식 | 처리량 (요청/초) | 평균 지연 시간 (ms) | GPU 활용도 (%) |
|--------------|--------------|-----------------|------------|
| 정적 배치 처리 | 10 | 500 | 60% |
| 연속 배치 처리 | 25 | 300 | 90% |

**연속 배치 처리의 한계:**
1. **메모리 관리 복잡성**: 동적 메모리 할당 및 해제로 인한 복잡성 증가
2. **스케줄링 오버헤드**: 동적 요청 스케줄링에 따른 추가 오버헤드
3. **최적화 어려움**: 다양한 워크로드에 대한 최적의 파라미터 설정 어려움

**다른 옵션들의 문제점:**
- A. 모델 정확도 향상: 연속 배치 처리는 모델 정확도에 영향을 미치지 않습니다.
- C. 모델 크기 축소: 연속 배치 처리는 모델 크기를 변경하지 않습니다.
- D. 네트워크 대역폭 절약: 연속 배치 처리는 네트워크 대역폭 사용에 직접적인 영향을 미치지 않습니다.
</details>
### 7. Kubernetes에서 vLLM 서비스를 모니터링하기 위한 가장 중요한 메트릭은 무엇인가요?

A. 파드 재시작 횟수  
B. 추론 지연 시간, 처리량, GPU 메모리 사용량  
C. 네트워크 패킷 손실률  
D. 디스크 I/O 성능  

<details>
<summary>정답 및 설명</summary>

**정답: B. 추론 지연 시간, 처리량, GPU 메모리 사용량**

**설명:**
Kubernetes에서 vLLM 서비스를 모니터링하기 위한 가장 중요한 메트릭은 추론 지연 시간, 처리량, GPU 메모리 사용량입니다. 이러한 메트릭은 vLLM 서비스의 성능, 효율성 및 리소스 활용도를 직접적으로 반영하며, 서비스 품질(QoS) 및 사용자 경험에 직접적인 영향을 미칩니다.

**주요 모니터링 메트릭:**

1. **추론 지연 시간(Inference Latency)**:
   - **정의**: 요청을 받은 시점부터 응답을 반환하는 시점까지의 시간
   - **중요성**: 사용자 경험과 서비스 응답성에 직접적인 영향
   - **측정 단위**: 밀리초(ms) 또는 초(s)
   - **세부 메트릭**:
     - 첫 토큰 생성 시간(Time to First Token)
     - 토큰당 생성 시간(Time per Token)
     - 전체 응답 생성 시간(Total Generation Time)

2. **처리량(Throughput)**:
   - **정의**: 단위 시간당 처리할 수 있는 요청 또는 토큰의 수
   - **중요성**: 시스템 용량 및 확장성 평가
   - **측정 단위**: 요청/초(RPS) 또는 토큰/초(TPS)
   - **세부 메트릭**:
     - 초당 처리된 요청 수(Requests per Second)
     - 초당 생성된 토큰 수(Tokens per Second)
     - 배치 크기(Batch Size)

3. **GPU 메모리 사용량**:
   - **정의**: vLLM 서비스가 사용하는 GPU 메모리의 양
   - **중요성**: 메모리 부족 문제 예방 및 리소스 최적화
   - **측정 단위**: 기가바이트(GB) 또는 메가바이트(MB)
   - **세부 메트릭**:
     - 모델 가중치 메모리 사용량
     - KV 캐시 메모리 사용량
     - 활성화 메모리 사용량
     - 총 GPU 메모리 사용량

**Prometheus 메트릭 구성 예시:**
```yaml
# vLLM 서비스에서 메트릭 노출
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-service
spec:
  template:
    metadata:
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8000"
        prometheus.io/path: "/metrics"
    spec:
      containers:
      - name: vllm
        image: vllm/vllm-openai:latest
        args:
        - --model=meta-llama/Llama-2-7b-chat-hf
        - --tensor-parallel-size=1
        - --enable-metrics=true  # 메트릭 활성화
```

**Prometheus ServiceMonitor 구성:**
```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: vllm-monitor
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: vllm
  endpoints:
  - port: http
    interval: 15s
    path: /metrics
```

**주요 vLLM 메트릭 및 PromQL 쿼리:**

1. **추론 지연 시간**:
   ```
   # 95 백분위수 추론 지연 시간
   histogram_quantile(0.95, sum(rate(vllm_request_latency_seconds_bucket[5m])) by (le))
   
   # 평균 토큰당 생성 시간
   avg(rate(vllm_token_generation_time_seconds_sum[5m]) / rate(vllm_token_generation_time_seconds_count[5m]))
   ```

2. **처리량**:
   ```
   # 초당 처리된 요청 수
   sum(rate(vllm_requests_total[5m]))
   
   # 초당 생성된 토큰 수
   sum(rate(vllm_generated_tokens_total[5m]))
   ```

3. **GPU 메모리 사용량**:
   ```
   # GPU 메모리 사용량
   vllm_gpu_memory_used_bytes
   
   # KV 캐시 메모리 사용량
   vllm_kv_cache_memory_bytes
   ```

**Grafana 대시보드 구성 예시:**
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: vllm-dashboard
  namespace: monitoring
  labels:
    grafana_dashboard: "1"
data:
  vllm-dashboard.json: |
    {
      "title": "vLLM Performance Dashboard",
      "panels": [
        {
          "title": "Inference Latency",
          "type": "graph",
          "datasource": "Prometheus",
          "targets": [
            {
              "expr": "histogram_quantile(0.95, sum(rate(vllm_request_latency_seconds_bucket[5m])) by (le))",
              "legendFormat": "p95 Latency"
            },
            {
              "expr": "histogram_quantile(0.50, sum(rate(vllm_request_latency_seconds_bucket[5m])) by (le))",
              "legendFormat": "p50 Latency"
            }
          ]
        },
        {
          "title": "Throughput",
          "type": "graph",
          "datasource": "Prometheus",
          "targets": [
            {
              "expr": "sum(rate(vllm_requests_total[5m]))",
              "legendFormat": "Requests/sec"
            },
            {
              "expr": "sum(rate(vllm_generated_tokens_total[5m]))",
              "legendFormat": "Tokens/sec"
            }
          ]
        },
        {
          "title": "GPU Memory Usage",
          "type": "graph",
          "datasource": "Prometheus",
          "targets": [
            {
              "expr": "vllm_gpu_memory_used_bytes / 1024 / 1024 / 1024",
              "legendFormat": "GPU Memory (GB)"
            },
            {
              "expr": "vllm_kv_cache_memory_bytes / 1024 / 1024 / 1024",
              "legendFormat": "KV Cache (GB)"
            }
          ]
        },
        {
          "title": "GPU Utilization",
          "type": "graph",
          "datasource": "Prometheus",
          "targets": [
            {
              "expr": "DCGM_FI_DEV_GPU_UTIL",
              "legendFormat": "GPU {{gpu}}"
            }
          ]
        }
      ]
    }
```

**알림 규칙 구성 예시:**
```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: vllm-alerts
  namespace: monitoring
spec:
  groups:
  - name: vllm.rules
    rules:
    - alert: HighInferenceLatency
      expr: histogram_quantile(0.95, sum(rate(vllm_request_latency_seconds_bucket[5m])) by (le)) > 2
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "High inference latency"
        description: "95th percentile latency is above 2 seconds"
    
    - alert: LowThroughput
      expr: sum(rate(vllm_requests_total[5m])) < 10
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "Low request throughput"
        description: "Request throughput is below 10 RPS"
    
    - alert: HighGPUMemoryUsage
      expr: vllm_gpu_memory_used_bytes / vllm_gpu_memory_total_bytes > 0.95
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: "High GPU memory usage"
        description: "GPU memory usage is above 95%"
```

**추가 모니터링 메트릭:**
1. **GPU 활용도**: GPU 계산 유닛의 활용 비율
2. **CPU 사용량**: 전처리 및 후처리에 사용되는 CPU 자원
3. **시스템 메모리 사용량**: 호스트 메모리 사용량
4. **오류율**: 실패한 요청의 비율
5. **큐 길이**: 처리 대기 중인 요청 수
6. **배치 효율성**: 평균 배치 크기 및 활용도

**모니터링 도구 통합:**
1. **Prometheus + Grafana**: 메트릭 수집 및 시각화
2. **NVIDIA DCGM Exporter**: GPU 메트릭 수집
3. **Jaeger/Zipkin**: 분산 추적
4. **ELK Stack**: 로그 수집 및 분석

**다른 옵션들의 문제점:**
- A. 파드 재시작 횟수: 시스템 안정성의 지표이지만, vLLM 서비스의 성능을 직접적으로 반영하지 않습니다.
- C. 네트워크 패킷 손실률: 네트워크 문제를 진단하는 데 유용하지만, vLLM 서비스의 핵심 성능 지표가 아닙니다.
- D. 디스크 I/O 성능: 모델 로딩 시 중요할 수 있지만, 실행 중인 vLLM 서비스의 성능에는 덜 중요합니다.
</details>

### 8. Kubernetes에서 vLLM 서비스를 위한 최적의 네트워크 구성은 무엇인가요?

A. 기본 CNI 플러그인 사용  
B. 텐서 병렬 처리를 위한 고성능 네트워크 인터페이스 및 RDMA 지원  
C. 네트워크 정책으로 모든 트래픽 제한  
D. 서비스 메시 구현  

<details>
<summary>정답 및 설명</summary>

**정답: B. 텐서 병렬 처리를 위한 고성능 네트워크 인터페이스 및 RDMA 지원**

**설명:**
Kubernetes에서 vLLM 서비스를 위한 최적의 네트워크 구성은 텐서 병렬 처리를 위한 고성능 네트워크 인터페이스 및 RDMA(Remote Direct Memory Access) 지원입니다. 대규모 언어 모델을 여러 GPU에 분산하여 실행할 때, GPU 간 통신 성능이 전체 시스템 성능에 큰 영향을 미칩니다. 고성능 네트워크 인터페이스와 RDMA 지원은 GPU 간 데이터 전송 지연 시간을 최소화하고 처리량을 극대화하여 분산 추론 성능을 향상시킵니다.

**고성능 네트워킹의 중요성:**
1. **텐서 병렬 처리**: 모델 레이어를 여러 GPU에 분산할 때 GPU 간 빈번한 통신 필요
2. **모델 샤딩**: 대규모 모델을 여러 노드에 분산할 때 노드 간 통신 성능 중요
3. **지연 시간 민감성**: GPU 간 통신 지연은 전체 추론 지연 시간에 직접적인 영향
4. **대역폭 요구 사항**: 대용량 텐서 데이터 전송에 높은 대역폭 필요

**최적의 네트워크 구성 요소:**

1. **고성능 네트워크 인터페이스**:
   - **NVIDIA ConnectX-6/7**: 최대 200Gbps 대역폭 지원
   - **InfiniBand**: 초저지연 고대역폭 네트워킹
   - **RDMA over Converged Ethernet(RoCE)**: 이더넷 네트워크에서 RDMA 기능 제공

2. **RDMA(Remote Direct Memory Access) 지원**:
   - CPU 개입 없이 GPU 메모리 간 직접 데이터 전송
   - 지연 시간 최소화 및 처리량 극대화
   - GPU Direct RDMA: GPU 메모리 간 직접 데이터 전송

3. **NVLink/NVSwitch**:
   - 동일 노드 내 GPU 간 고속 연결
   - 최대 600GB/s 대역폭(NVLink 4.0)
   - 멀티 GPU 시스템에서 중요

**Kubernetes에서의 고성능 네트워킹 구성:**

1. **SR-IOV(Single Root I/O Virtualization) 네트워크 장치 플러그인**:
```yaml
# SR-IOV 네트워크 장치 플러그인 구성
apiVersion: v1
kind: ConfigMap
metadata:
  name: sriovdp-config
  namespace: kube-system
data:
  config.json: |
    {
      "resourceList": [
        {
          "resourceName": "nvidia_sriov_netdevice",
          "rootDevices": ["0000:03:00.0"],
          "sriovMode": true,
          "deviceType": "netdevice"
        },
        {
          "resourceName": "nvidia_sriov_rdma",
          "rootDevices": ["0000:03:00.0"],
          "sriovMode": true,
          "deviceType": "rdma"
        }
      ]
    }
```

2. **NetworkAttachmentDefinition 구성**:
```yaml
apiVersion: "k8s.cni.cncf.io/v1"
kind: NetworkAttachmentDefinition
metadata:
  name: sriov-rdma-network
spec:
  config: '{
    "cniVersion": "0.3.1",
    "name": "sriov-rdma-network",
    "type": "sriov",
    "ipam": {
      "type": "host-local",
      "subnet": "192.168.1.0/24",
      "rangeStart": "192.168.1.10",
      "rangeEnd": "192.168.1.200"
    },
    "capabilities": { "ips": true }
  }'
```

3. **vLLM 배포에 고성능 네트워크 구성 적용**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-distributed
spec:
  replicas: 1
  selector:
    matchLabels:
      app: vllm
  template:
    metadata:
      labels:
        app: vllm
      annotations:
        k8s.v1.cni.cncf.io/networks: sriov-rdma-network
    spec:
      containers:
      - name: vllm
        image: vllm/vllm-openai:latest
        args:
        - --model=meta-llama/Llama-2-70b-chat-hf
        - --tensor-parallel-size=8
        - --max-model-len=4096
        resources:
          limits:
            nvidia.com/gpu: 8
            nvidia.com/sriov_rdma: 8
        env:
        - name: NCCL_DEBUG
          value: "INFO"
        - name: NCCL_IB_DISABLE
          value: "0"
        - name: NCCL_IB_GID_INDEX
          value: "3"
        - name: NCCL_IB_HCA
          value: "mlx5_0:1,mlx5_1:1,mlx5_2:1,mlx5_3:1"
        - name: NCCL_SOCKET_IFNAME
          value: "eth0,ens"
```

**NCCL(NVIDIA Collective Communications Library) 구성:**
NCCL은 GPU 간 통신을 최적화하는 라이브러리로, 다음과 같은 환경 변수를 통해 구성할 수 있습니다:

```
# NCCL 디버그 정보 활성화
NCCL_DEBUG=INFO

# InfiniBand 사용 활성화
NCCL_IB_DISABLE=0

# InfiniBand GID 인덱스 설정
NCCL_IB_GID_INDEX=3

# 사용할 HCA(Host Channel Adapter) 지정
NCCL_IB_HCA=mlx5_0:1,mlx5_1:1

# 네트워크 인터페이스 지정
NCCL_SOCKET_IFNAME=eth0,ens

# RDMA 전송 활성화
NCCL_IB_ENABLE_RDMA=1

# GPU Direct RDMA 활성화
NCCL_IB_GDR_LEVEL=4
```

**다중 노드 분산 구성:**
여러 노드에 걸쳐 vLLM을 분산 배포할 때는 노드 간 네트워크 성능이 더욱 중요합니다. 이를 위해 다음과 같은 구성이 필요합니다:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: vllm-distributed-node1
  annotations:
    k8s.v1.cni.cncf.io/networks: sriov-rdma-network
spec:
  nodeSelector:
    kubernetes.io/hostname: node1
  containers:
  - name: vllm
    image: vllm/vllm-openai:latest
    args:
    - --model=meta-llama/Llama-2-70b-chat-hf
    - --tensor-parallel-size=16
    - --tensor-parallel-rank=0-7
    - --distributed-init-method=tcp://vllm-init:7777
    env:
    - name: NCCL_DEBUG
      value: "INFO"
    - name: NCCL_IB_DISABLE
      value: "0"
    resources:
      limits:
        nvidia.com/gpu: 8
        nvidia.com/sriov_rdma: 8

---
apiVersion: v1
kind: Pod
metadata:
  name: vllm-distributed-node2
  annotations:
    k8s.v1.cni.cncf.io/networks: sriov-rdma-network
spec:
  nodeSelector:
    kubernetes.io/hostname: node2
  containers:
  - name: vllm
    image: vllm/vllm-openai:latest
    args:
    - --model=meta-llama/Llama-2-70b-chat-hf
    - --tensor-parallel-size=16
    - --tensor-parallel-rank=8-15
    - --distributed-init-method=tcp://vllm-init:7777
    env:
    - name: NCCL_DEBUG
      value: "INFO"
    - name: NCCL_IB_DISABLE
      value: "0"
    resources:
      limits:
        nvidia.com/gpu: 8
        nvidia.com/sriov_rdma: 8
```

**네트워크 성능 테스트:**
```bash
# NCCL 테스트 실행
kubectl run nccl-test --image=nvidia/cuda:11.8.0-devel-ubuntu22.04 --overrides='{"spec": {"containers": [{"name": "nccl-test", "image": "nvidia/cuda:11.8.0-devel-ubuntu22.04", "command": ["/bin/bash", "-c"], "args": ["apt-get update && apt-get install -y git && git clone https://github.com/NVIDIA/nccl-tests.git && cd nccl-tests && make && ./build/all_reduce_perf -b 8 -e 128M -f 2 -g 8"], "resources": {"limits": {"nvidia.com/gpu": 8}}}]}}' --restart=Never

# 네트워크 대역폭 테스트
kubectl run iperf3-server --image=networkstatic/iperf3 --port=5201 -- -s
kubectl expose pod iperf3-server --port=5201 --target-port=5201
kubectl run iperf3-client --image=networkstatic/iperf3 --rm -it -- -c iperf3-server -p 5201 -t 30
```

**다른 옵션들의 문제점:**
- A. 기본 CNI 플러그인 사용: 기본 CNI 플러그인은 일반적으로 RDMA와 같은 고성능 네트워킹 기능을 지원하지 않으며, 텐서 병렬 처리에 필요한 성능을 제공하지 못합니다.
- C. 네트워크 정책으로 모든 트래픽 제한: 이는 보안을 강화할 수 있지만, 성능을 향상시키지는 않으며 오히려 추가적인 오버헤드를 발생시킬 수 있습니다.
- D. 서비스 메시 구현: 서비스 메시는 마이크로서비스 아키텍처에 유용하지만, vLLM과 같은 고성능 컴퓨팅 워크로드에는 불필요한 오버헤드를 추가합니다.
</details>
### 9. Kubernetes에서 vLLM 서비스의 확장성을 향상시키기 위한 가장 효과적인 방법은 무엇인가요?

A. 더 많은 CPU 코어 할당  
B. 수평적 확장(여러 복제본) 및 로드 밸런싱과 수직적 확장(더 큰 GPU) 조합  
C. 더 많은 메모리 할당  
D. 더 큰 영구 볼륨 프로비저닝  

<details>
<summary>정답 및 설명</summary>

**정답: B. 수평적 확장(여러 복제본) 및 로드 밸런싱과 수직적 확장(더 큰 GPU) 조합**

**설명:**
Kubernetes에서 vLLM 서비스의 확장성을 향상시키기 위한 가장 효과적인 방법은 수평적 확장(여러 복제본) 및 로드 밸런싱과 수직적 확장(더 큰 GPU) 조합입니다. 이 접근 방식은 다양한 워크로드 요구 사항과 리소스 제약 조건에 유연하게 대응할 수 있으며, 비용 효율성과 성능 사이의 균형을 맞출 수 있습니다.

**수평적 확장(Horizontal Scaling)의 이점:**
1. **처리량 증가**: 더 많은 복제본으로 더 많은 동시 요청 처리 가능
2. **고가용성**: 일부 인스턴스 장애 시에도 서비스 계속 제공
3. **지역적 분산**: 여러 지역에 배포하여 지연 시간 감소
4. **비용 효율성**: 필요에 따라 인스턴스 수 조정 가능

**수직적 확장(Vertical Scaling)의 이점:**
1. **더 큰 모델 지원**: 더 큰 GPU 메모리로 더 큰 모델 로드 가능
2. **단일 요청 지연 시간 감소**: 더 강력한 GPU로 추론 속도 향상
3. **더 긴 컨텍스트 처리**: 더 많은 메모리로 더 긴 컨텍스트 처리 가능
4. **통신 오버헤드 감소**: 단일 GPU 또는 노드 내 여러 GPU 사용 시 통신 오버헤드 감소

**수평적 확장 구성 예시:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-service
spec:
  replicas: 5  # 여러 복제본 실행
  selector:
    matchLabels:
      app: vllm
  template:
    metadata:
      labels:
        app: vllm
    spec:
      containers:
      - name: vllm
        image: vllm/vllm-openai:latest
        args:
        - --model=meta-llama/Llama-2-7b-chat-hf
        resources:
          limits:
            nvidia.com/gpu: 1
```

**수평적 자동 확장 구성:**
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: vllm-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: vllm-service
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Pods
    pods:
      metric:
        name: inference_requests_per_second
      target:
        type: AverageValue
        averageValue: 100
```

**수직적 확장 구성 예시:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-large-model
spec:
  replicas: 1
  selector:
    matchLabels:
      app: vllm-large
  template:
    metadata:
      labels:
        app: vllm-large
    spec:
      nodeSelector:
        gpu-type: a100-80gb  # 더 큰 GPU 선택
      containers:
      - name: vllm
        image: vllm/vllm-openai:latest
        args:
        - --model=meta-llama/Llama-2-70b-chat-hf
        - --tensor-parallel-size=8  # 여러 GPU에 모델 분산
        resources:
          limits:
            nvidia.com/gpu: 8  # 더 많은 GPU 할당
```

**로드 밸런싱 구성:**
```yaml
apiVersion: v1
kind: Service
metadata:
  name: vllm-service
spec:
  selector:
    app: vllm
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: vllm-ingress
  annotations:
    kubernetes.io/ingress.class: nginx
    nginx.ingress.kubernetes.io/affinity: "cookie"
    nginx.ingress.kubernetes.io/session-cookie-name: "route"
    nginx.ingress.kubernetes.io/session-cookie-expires: "172800"
    nginx.ingress.kubernetes.io/session-cookie-max-age: "172800"
spec:
  rules:
  - host: vllm.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: vllm-service
            port:
              number: 80
```

**모델 샤딩 및 라우팅:**
다양한 모델 크기와 유형을 지원하기 위해 여러 배포를 조합하고 라우팅할 수 있습니다:

```yaml
# 작은 모델용 배포
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-small
spec:
  replicas: 5
  template:
    spec:
      containers:
      - name: vllm
        args:
        - --model=meta-llama/Llama-2-7b-chat-hf
---
# 중간 크기 모델용 배포
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-medium
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: vllm
        args:
        - --model=meta-llama/Llama-2-13b-chat-hf
---
# 대형 모델용 배포
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-large
spec:
  replicas: 1
  template:
    spec:
      containers:
      - name: vllm
        args:
        - --model=meta-llama/Llama-2-70b-chat-hf
        - --tensor-parallel-size=8
```

**API 게이트웨이 구성:**
```yaml
apiVersion: networking.istio.io/v1alpha3
kind: VirtualService
metadata:
  name: vllm-routing
spec:
  hosts:
  - "api.example.com"
  gateways:
  - api-gateway
  http:
  - match:
    - uri:
        prefix: "/v1/completions"
      headers:
        model:
          exact: "llama-2-7b"
    route:
    - destination:
        host: vllm-small
        port:
          number: 8000
  - match:
    - uri:
        prefix: "/v1/completions"
      headers:
        model:
          exact: "llama-2-13b"
    route:
    - destination:
        host: vllm-medium
        port:
          number: 8000
  - match:
    - uri:
        prefix: "/v1/completions"
      headers:
        model:
          exact: "llama-2-70b"
    route:
    - destination:
        host: vllm-large
        port:
          number: 8000
```

**확장성 최적화 전략:**
1. **요청 라우팅 최적화**:
   - 모델 크기 및 복잡성에 따라 적절한 인스턴스로 요청 라우팅
   - 세션 어피니티를 통한 KV 캐시 재사용 최적화

2. **자원 할당 최적화**:
   - 워크로드 특성에 맞는 GPU 유형 선택
   - 적절한 텐서 병렬 처리 크기 설정

3. **캐싱 전략**:
   - 자주 사용되는 프롬프트 및 응답 캐싱
   - 모델 가중치 캐싱

4. **하이브리드 클라우드 확장**:
   - 온프레미스 및 클라우드 리소스 조합
   - 버스트 트래픽을 위한 클라우드 확장

**확장성 테스트 및 벤치마킹:**
```bash
# 부하 테스트 실행
kubectl run locust --image=locustio/locust --env="LOCUST_HOST=http://vllm-service" --env="LOCUST_LOCUSTFILE=/mnt/locustfile.py" --volume=locustfile.py:/mnt/locustfile.py
```

**다른 옵션들의 문제점:**
- A. 더 많은 CPU 코어 할당: vLLM은 주로 GPU 바운드이며, CPU 코어 추가만으로는 성능이 크게 향상되지 않습니다.
- C. 더 많은 메모리 할당: 시스템 메모리는 중요하지만, GPU 메모리가 주요 제약 요소입니다.
- D. 더 큰 영구 볼륨 프로비저닝: 스토리지 용량은 모델 저장에 중요하지만, 추론 성능과 확장성에 직접적인 영향을 미치지 않습니다.
</details>

### 10. Kubernetes에서 vLLM 배포 시 가장 중요한 보안 고려 사항은 무엇인가요?

A. 네트워크 정책 설정  
B. 모델 가중치 및 API 키 보호, 컨테이너 보안 강화  
C. 파드 보안 정책 설정  
D. 감사 로깅 활성화  

<details>
<summary>정답 및 설명</summary>

**정답: B. 모델 가중치 및 API 키 보호, 컨테이너 보안 강화**

**설명:**
Kubernetes에서 vLLM 배포 시 가장 중요한 보안 고려 사항은 모델 가중치 및 API 키 보호, 컨테이너 보안 강화입니다. vLLM 서비스는 지적 재산권이 있는 모델 가중치, 민감한 API 키, 그리고 사용자 데이터를 처리하므로, 이러한 자산을 보호하고 컨테이너 환경의 보안을 강화하는 것이 가장 중요합니다.

**주요 보안 고려 사항:**

1. **모델 가중치 보호**:
   - 모델 가중치는 지적 재산권이 있는 귀중한 자산입니다.
   - 무단 접근, 복사, 유출로부터 보호해야 합니다.
   - 암호화된 스토리지 및 전송 중 암호화가 필요합니다.

2. **API 키 및 인증 정보 보호**:
   - API 키, 토큰, 비밀번호 등의 인증 정보는 안전하게 관리해야 합니다.
   - Kubernetes Secrets 또는 외부 비밀 관리 시스템을 사용해야 합니다.
   - 환경 변수 대신 마운트된 볼륨을 통해 비밀을 제공해야 합니다.

3. **컨테이너 보안 강화**:
   - 최소 권한 원칙 적용
   - 루트가 아닌 사용자로 컨테이너 실행
   - 읽기 전용 파일 시스템 사용
   - 불필요한 기능 및 권한 제거

4. **입력 검증 및 출력 필터링**:
   - 프롬프트 인젝션 공격 방지
   - 민감한 정보 유출 방지
   - 유해 콘텐츠 필터링

**모델 가중치 보호 구성 예시:**
```yaml
# 암호화된 영구 볼륨 클레임
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: encrypted-storage
provisioner: kubernetes.io/aws-ebs
parameters:
  type: gp3
  encrypted: "true"
  kmsKeyId: arn:aws:kms:us-west-2:111122223333:key/1234abcd-12ab-34cd-56ef-1234567890ab

---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: model-storage
spec:
  accessModes:
    - ReadOnlyMany
  storageClassName: encrypted-storage
  resources:
    requests:
      storage: 100Gi

---
# 모델 가중치에 대한 접근 제한
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-service
spec:
  template:
    spec:
      securityContext:
        fsGroup: 1000
        runAsUser: 1000
        runAsGroup: 1000
      containers:
      - name: vllm
        volumeMounts:
        - name: model-volume
          mountPath: /models
          readOnly: true
      volumes:
      - name: model-volume
        persistentVolumeClaim:
          claimName: model-storage
```

**API 키 및 인증 정보 보호:**
```yaml
# Kubernetes Secrets 사용
apiVersion: v1
kind: Secret
metadata:
  name: api-keys
type: Opaque
data:
  openai-api-key: base64EncodedApiKey
  huggingface-token: base64EncodedToken

---
# 외부 비밀 관리 시스템 통합(HashiCorp Vault)
apiVersion: v1
kind: ServiceAccount
metadata:
  name: vllm-service
  annotations:
    vault.hashicorp.com/agent-inject: "true"
    vault.hashicorp.com/agent-inject-secret-api-keys: "secret/data/api-keys"
    vault.hashicorp.com/role: "vllm-role"

---
# 비밀을 볼륨으로 마운트
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-service
spec:
  template:
    spec:
      containers:
      - name: vllm
        volumeMounts:
        - name: api-keys
          mountPath: /app/secrets
          readOnly: true
      volumes:
      - name: api-keys
        secret:
          secretName: api-keys
```

**컨테이너 보안 강화:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-service
spec:
  template:
    spec:
      # 파드 수준 보안 컨텍스트
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 1000
        fsGroup: 1000
      containers:
      - name: vllm
        image: vllm/vllm-openai:latest
        # 컨테이너 수준 보안 컨텍스트
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
          seccompProfile:
            type: RuntimeDefault
```

**네트워크 정책:**
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: vllm-network-policy
spec:
  podSelector:
    matchLabels:
      app: vllm
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: frontend
    - podSelector:
        matchLabels:
          app: api-gateway
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: monitoring
    ports:
    - protocol: TCP
      port: 9090
  - to:
    - namespaceSelector:
        matchLabels:
          name: huggingface
    ports:
    - protocol: TCP
      port: 443
```

**입력 검증 및 출력 필터링:**
```python
# 프롬프트 검증 및 필터링 예시
def validate_prompt(prompt):
    # 프롬프트 인젝션 패턴 확인
    if re.search(r"(ignore|forget|disregard).*instructions", prompt, re.IGNORECASE):
        return False, "Potential prompt injection detected"
    
    # 민감한 명령어 확인
    if re.search(r"(system|sudo|exec|eval)", prompt, re.IGNORECASE):
        return False, "Potentially harmful commands detected"
    
    return True, prompt

# 출력 필터링 예시
def filter_output(response):
    # PII 필터링
    response = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[REDACTED SSN]", response)
    response = re.sub(r"\b\d{16}\b", "[REDACTED CREDIT CARD]", response)
    
    # 유해 콘텐츠 필터링
    for harmful_pattern in HARMFUL_PATTERNS:
        if re.search(harmful_pattern, response, re.IGNORECASE):
            response = "[Content removed due to policy violation]"
            break
    
    return response
```

**RBAC(Role-Based Access Control) 구성:**
```yaml
# 서비스 계정 생성
apiVersion: v1
kind: ServiceAccount
metadata:
  name: vllm-service
  namespace: ml-services

---
# 역할 정의
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: vllm-role
  namespace: ml-services
rules:
- apiGroups: [""]
  resources: ["secrets"]
  verbs: ["get"]
  resourceNames: ["model-access-keys"]
- apiGroups: [""]
  resources: ["configmaps"]
  verbs: ["get"]
  resourceNames: ["vllm-config"]

---
# 역할 바인딩
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: vllm-role-binding
  namespace: ml-services
subjects:
- kind: ServiceAccount
  name: vllm-service
  namespace: ml-services
roleRef:
  kind: Role
  name: vllm-role
  apiGroup: rbac.authorization.k8s.io
```

**감사 로깅 구성:**
```yaml
# 감사 로깅을 위한 ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: vllm-audit-config
data:
  audit.yaml: |
    apiVersion: audit.k8s.io/v1
    kind: Policy
    rules:
    - level: RequestResponse
      resources:
      - group: ""
        resources: ["secrets"]
    - level: Metadata
      resources:
      - group: ""
        resources: ["pods"]

# 감사 로깅 활성화
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-service
spec:
  template:
    metadata:
      annotations:
        audit-log-path: "/var/log/vllm/audit.log"
        audit-log-maxage: "30"
        audit-log-maxbackup: "10"
        audit-log-maxsize: "100"
    spec:
      containers:
      - name: vllm
        volumeMounts:
        - name: audit-logs
          mountPath: /var/log/vllm
      volumes:
      - name: audit-logs
        emptyDir: {}
```

**추가 보안 모범 사례:**
1. **정기적인 보안 스캔**: 컨테이너 이미지 및 의존성 취약점 스캔
2. **최소 권한 원칙**: 필요한 최소한의 권한만 부여
3. **불변 인프라**: 변경이 필요할 때 새 컨테이너 배포
4. **보안 모니터링**: 이상 행동 감지 및 알림
5. **비상 대응 계획**: 보안 사고 발생 시 대응 절차 마련

**다른 옵션들의 문제점:**
- A. 네트워크 정책 설정: 중요하지만, 모델 가중치 및 API 키 보호, 컨테이너 보안 강화보다 우선순위가 낮습니다.
- C. 파드 보안 정책 설정: 컨테이너 보안의 일부이지만, 모델 가중치 및 API 키 보호를 포함하지 않습니다.
- D. 감사 로깅 활성화: 보안 모니터링에 중요하지만, 예방적 보안 조치보다 우선순위가 낮습니다.
</details>

### 11. 이 문서에서 NVIDIA L4 GPU 1장으로 실측한 Qwen2.5-7B-Instruct 벤치마크에서, 동시성을 1에서 16으로 늘렸을 때 요청당 지연시간은 어떻게 됐나요?

A. 늘어난 부하에 비례해 거의 16배로 늘었습니다
B. 거의 그대로였고(p50 5.65s → 7.52s, +33%), 집계 처리량은 거의 선형으로 늘었습니다
C. 더 많은 요청이 vLLM의 prefill 단계를 건너뛰게 해서 오히려 줄었습니다
D. 동시성 16에 도달하기 전에 GPU의 KV 캐시 메모리가 고갈되어 측정할 수 없었습니다

<details>
<summary>정답 보기</summary>

**정답: B. 거의 그대로였고(p50 5.65s → 7.52s, +33%), 집계 처리량은 거의 선형으로 늘었습니다**

**설명:**
이것이 continuous batching의 핵심입니다. vLLM은 새 요청을 이미 실행 중인 요청 뒤에 줄 세우지 않고, 다음 스케줄러 스텝에서 배치에 합류시킵니다. 그래서 GPU가 여러 시퀀스를 순차가 아니라 병렬로 처리합니다. 이번 실측에서 약 100~128 토큰 응답의 p50 지연시간은 동시성 1일 때 5.65s에서 동시성 16일 때 7.52s로만 늘었지만(+33%), 집계 completion 처리량은 약 17 tokens/s에서 208 tokens/s(클라이언트 기준)로 늘었습니다. 이 스케일링 양상 자체가 메모리 대역폭 병목(memory-bandwidth-bound) 디코딩의 특징입니다 — 동시성 1에서는 토큰 하나마다 약 15.2GB의 bf16 가중치를 GDDR6 메모리에서 읽어야 하고, 이 L4의 대역폭(약 300GB/s)만으로 계산해도 단일 요청 디코딩 한계는 실측값 17~18 tokens/s와 거의 일치합니다. 반면 연산은 가장 바쁜 구간에서도 L4의 bf16 연산 한계(약 121 TFLOPS)의 몇 % 수준에 그칩니다. 배칭은 여러 요청이 같은 가중치 읽기를 거의 공짜로 나눠 쓰게 해 주므로, 지연시간은 거의 그대로인 채 처리량만 거의 선형으로 늘어나는 것입니다.

**다른 옵션들의 문제점:**
- A. 이는 continuous batching이 아니라 순차(비배칭) 요청 처리에서 벌어지는 일입니다.
- C. Continuous batching은 prefill을 건너뛰지 않습니다. 모든 새 요청은 여전히 decode 전에 prefill을 거치며, 다른 요청들의 decode 스텝과 함께 처리될 뿐입니다.
- D. 이 24GB L4에서 GPU KV 캐시 사용률은 동시성 16에서 최대 2.6%에 그쳤습니다 — 고갈과는 거리가 멉니다. 이번 벤치마크는 그 한계를 찾을 만큼 동시성을 높이지 않았습니다.
</details>
