# AI/ML 워크로드 퀴즈

이 퀴즈는 Kubernetes에서 AI/ML 워크로드를 실행하는 방법에 대한 이해를 테스트합니다.

## 퀴즈 문제

### 1. Kubernetes에서 GPU를 사용하는 파드를 스케줄링할 때 필요한 리소스 요청 필드는 무엇인가요?

A. resources.requests.gpu  
B. resources.requests.nvidia.com/gpu  
C. resources.requests.k8s.io/gpu  
D. resources.requests.compute/gpu  

<details>
<summary>정답 및 설명</summary>

**정답: B. resources.requests.nvidia.com/gpu**

**설명:**
Kubernetes에서 GPU를 사용하는 파드를 스케줄링할 때 필요한 리소스 요청 필드는 `resources.requests.nvidia.com/gpu`입니다. 이는 NVIDIA GPU를 요청하는 표준 방법이며, 다른 GPU 공급업체는 자체 네임스페이스를 사용할 수 있습니다(예: `amd.com/gpu`).

**GPU 리소스 요청 예시:**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: gpu-pod
spec:
  containers:
  - name: gpu-container
    image: nvidia/cuda:11.0-base
    resources:
      limits:
        nvidia.com/gpu: 1  # 1개의 GPU 요청
      requests:
        nvidia.com/gpu: 1  # 요청과 제한은 동일해야 함
```

**GPU 리소스 특징:**
1. **정수 할당**: GPU는 정수 단위로만 할당할 수 있습니다(예: 1, 2, 3). 소수점 값(예: 0.5)은 지원되지 않습니다.
2. **요청과 제한 일치**: GPU 리소스의 경우 `requests`와 `limits`는 동일해야 합니다.
3. **독점적 사용**: 기본적으로 GPU는 컨테이너 간에 공유되지 않습니다. 각 GPU는 한 번에 하나의 컨테이너에만 할당됩니다.
4. **노드 레이블**: GPU가 있는 노드는 일반적으로 `nvidia.com/gpu` 레이블로 표시됩니다.

**GPU 사용을 위한 사전 요구 사항:**
1. **노드에 GPU 하드웨어**: 노드에 물리적 GPU가 설치되어 있어야 합니다.
2. **GPU 드라이버**: 노드에 적절한 GPU 드라이버가 설치되어 있어야 합니다.
3. **NVIDIA Device Plugin**: Kubernetes 클러스터에 NVIDIA Device Plugin이 설치되어 있어야 합니다.
4. **컨테이너 런타임 지원**: 컨테이너 런타임이 GPU를 지원해야 합니다.

**NVIDIA Device Plugin 설치:**
```bash
# Helm을 사용한 설치
helm repo add nvdp https://nvidia.github.io/k8s-device-plugin
helm repo update
helm install nvidia-device-plugin nvdp/nvidia-device-plugin

# 또는 직접 설치
kubectl create -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.13.0/nvidia-device-plugin.yml
```

**GPU 리소스 확인:**
```bash
# 노드의 GPU 리소스 확인
kubectl get nodes -o custom-columns=NAME:.metadata.name,GPU:.status.allocatable.nvidia\\.com/gpu

# GPU 사용 중인 파드 확인
kubectl get pods -A -o custom-columns=NAME:.metadata.name,GPU:.spec.containers[*].resources.limits.nvidia\\.com/gpu
```

**다중 GPU 요청:**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: multi-gpu-pod
spec:
  containers:
  - name: multi-gpu-container
    image: nvidia/cuda:11.0-base
    resources:
      limits:
        nvidia.com/gpu: 4  # 4개의 GPU 요청
      requests:
        nvidia.com/gpu: 4
```

**GPU 메모리 분할(NVIDIA MPS):**
NVIDIA Multi-Process Service(MPS)를 사용하면 여러 프로세스가 동일한 GPU를 공유할 수 있습니다. 이는 Kubernetes에서 기본적으로 지원되지 않으며, 사용자 정의 설정이 필요합니다.

**다른 GPU 공급업체:**
다른 GPU 공급업체는 자체 네임스페이스를 사용합니다:
- AMD GPU: `amd.com/gpu`
- Intel GPU: `intel.com/gpu`

**다른 옵션들의 문제점:**
- A. resources.requests.gpu: 이는 유효한 Kubernetes 리소스 필드가 아닙니다. GPU 리소스는 공급업체별 네임스페이스를 사용해야 합니다.
- C. resources.requests.k8s.io/gpu: 이는 유효한 Kubernetes 리소스 필드가 아닙니다. `k8s.io` 네임스페이스는 일반적으로 Kubernetes 코어 리소스에 사용됩니다.
- D. resources.requests.compute/gpu: 이는 유효한 Kubernetes 리소스 필드가 아닙니다.
</details>

### 2. Kubernetes에서 분산 TensorFlow 학습 작업을 실행하는 데 가장 적합한 리소스 유형은 무엇인가요?

A. Deployment  
B. StatefulSet  
C. Job  
D. TFJob (Kubeflow)  

<details>
<summary>정답 및 설명</summary>

**정답: D. TFJob (Kubeflow)**

**설명:**
Kubernetes에서 분산 TensorFlow 학습 작업을 실행하는 데 가장 적합한 리소스 유형은 `TFJob`입니다. TFJob은 Kubeflow 프로젝트의 일부로, TensorFlow 학습 작업을 Kubernetes에서 실행하기 위해 특별히 설계된 사용자 정의 리소스입니다.

**TFJob의 주요 특징:**
1. **분산 학습 지원**: 여러 작업자(worker), 파라미터 서버(parameter server), 평가자(evaluator) 등 TensorFlow의 분산 학습 아키텍처를 지원합니다.
2. **자동 복구**: 실패한 작업자를 자동으로 재시작합니다.
3. **Gang 스케줄링**: 모든 작업자가 동시에 스케줄링되도록 보장합니다.
4. **TensorFlow 특화 기능**: TensorFlow 분산 학습에 필요한 환경 변수 및 설정을 자동으로 구성합니다.
5. **모니터링 및 로깅**: TensorFlow 작업의 상태 및 로그를 모니터링하는 기능을 제공합니다.

**TFJob 예시:**
```yaml
apiVersion: kubeflow.org/v1
kind: TFJob
metadata:
  name: mnist-training
spec:
  tfReplicaSpecs:
    Worker:
      replicas: 3
      restartPolicy: OnFailure
      template:
        spec:
          containers:
          - name: tensorflow
            image: tensorflow/tensorflow:2.6.0
            command:
            - python
            - /opt/model/train.py
            - --batch_size=64
            - --learning_rate=0.001
            resources:
              limits:
                nvidia.com/gpu: 1
    PS:
      replicas: 1
      restartPolicy: OnFailure
      template:
        spec:
          containers:
          - name: tensorflow
            image: tensorflow/tensorflow:2.6.0
            command:
            - python
            - /opt/model/train.py
            - --batch_size=64
            - --learning_rate=0.001
    Chief:
      replicas: 1
      restartPolicy: OnFailure
      template:
        spec:
          containers:
          - name: tensorflow
            image: tensorflow/tensorflow:2.6.0
            command:
            - python
            - /opt/model/train.py
            - --batch_size=64
            - --learning_rate=0.001
            resources:
              limits:
                nvidia.com/gpu: 1
```

**TFJob 구성 요소:**
1. **Chief**: 주 작업자로, 모델 체크포인트 저장 및 요약 작성을 담당합니다.
2. **Worker**: 모델 학습을 수행하는 작업자입니다.
3. **PS (Parameter Server)**: 모델 파라미터를 저장하고 업데이트합니다.
4. **Evaluator**: 모델 평가를 수행합니다.

**TFJob 설치:**
```bash
# Kubeflow 설치
kubectl apply -f https://raw.githubusercontent.com/kubeflow/kubeflow/master/kfctl_k8s_istio.yaml

# 또는 TFJob 컨트롤러만 설치
kubectl apply -f https://raw.githubusercontent.com/kubeflow/tf-operator/master/deploy/v1/tf-operator.yaml
```

**TFJob 모니터링:**
```bash
# TFJob 상태 확인
kubectl get tfjobs

# 특정 TFJob 세부 정보 확인
kubectl describe tfjob mnist-training

# TFJob 파드 확인
kubectl get pods -l tf-job-name=mnist-training
```

**다른 리소스 유형과의 비교:**

1. **Deployment**:
   - 장기 실행 서비스에 적합
   - 자동 복구 및 롤링 업데이트 지원
   - 분산 학습 작업의 조정 기능 부족
   - TensorFlow 특화 기능 없음

2. **StatefulSet**:
   - 안정적인 네트워크 식별자 및 영구 스토리지 제공
   - 순서가 지정된 배포 및 스케일링
   - 분산 학습 작업의 조정 기능 부족
   - TensorFlow 특화 기능 없음

3. **Job**:
   - 일회성 작업에 적합
   - 작업 완료 보장
   - 분산 학습 작업의 조정 기능 부족
   - TensorFlow 특화 기능 없음

4. **TFJob**:
   - TensorFlow 분산 학습에 최적화
   - 작업자, 파라미터 서버 등의 역할 정의
   - TensorFlow 특화 환경 변수 및 설정 자동 구성
   - 작업 완료 및 실패 처리 로직 내장

**다른 ML 프레임워크를 위한 Kubeflow 연산자:**
- **PyTorchJob**: PyTorch 학습 작업용
- **MPIJob**: Horovod와 같은 MPI 기반 분산 학습용
- **XGBoostJob**: XGBoost 학습 작업용

**다른 옵션들의 문제점:**
- A. Deployment: 장기 실행 서비스에 적합하며, 분산 TensorFlow 학습 작업의 특정 요구 사항을 처리하지 않습니다.
- B. StatefulSet: 상태 유지가 필요한 애플리케이션에 적합하지만, 분산 TensorFlow 학습 작업의 조정 기능이 부족합니다.
- C. Job: 일회성 작업에 적합하지만, 분산 TensorFlow 학습 작업의 특정 요구 사항을 처리하지 않습니다.
</details>
### 3. Kubernetes에서 AI/ML 워크로드를 위한 영구 스토리지를 구성할 때 가장 중요한 고려 사항은 무엇인가요?

A. 스토리지 용량  
B. 스토리지 클래스 유형  
C. 데이터 접근 패턴 및 처리량 요구 사항  
D. 스토리지 프로비저너  

<details>
<summary>정답 및 설명</summary>

**정답: C. 데이터 접근 패턴 및 처리량 요구 사항**

**설명:**
Kubernetes에서 AI/ML 워크로드를 위한 영구 스토리지를 구성할 때 가장 중요한 고려 사항은 데이터 접근 패턴 및 처리량 요구 사항입니다. AI/ML 워크로드는 대량의 데이터를 처리하고, 다양한 접근 패턴(순차적 읽기, 무작위 읽기, 병렬 접근 등)을 가질 수 있으며, 높은 처리량이 필요한 경우가 많습니다. 이러한 요구 사항에 맞는 스토리지 솔루션을 선택하는 것이 성능과 효율성에 큰 영향을 미칩니다.

**AI/ML 워크로드의 일반적인 데이터 접근 패턴:**
1. **대규모 데이터셋 읽기**: 학습 데이터셋은 수 GB에서 수 TB까지 클 수 있으며, 효율적인 읽기 성능이 중요합니다.
2. **병렬 접근**: 여러 작업자가 동시에 데이터에 접근하는 분산 학습 시나리오가 일반적입니다.
3. **순차적 읽기**: 전체 데이터셋을 순차적으로 읽는 배치 처리 작업이 있습니다.
4. **무작위 접근**: 미니배치 학습이나 온라인 학습에서는 데이터셋의 무작위 부분에 접근합니다.
5. **체크포인트 저장**: 학습 중간에 모델 체크포인트를 저장하는 쓰기 작업이 발생합니다.

**AI/ML 워크로드에 적합한 스토리지 솔루션:**

1. **분산 파일 시스템**:
   - **Amazon FSx for Lustre**: 고성능 컴퓨팅 및 기계 학습 워크로드에 최적화된 고성능 파일 시스템
   - **GlusterFS/Ceph**: 오픈 소스 분산 파일 시스템으로 확장성과 병렬 접근 지원
   - **HDFS**: 대규모 데이터셋 처리에 적합한 Hadoop 분산 파일 시스템

2. **고성능 블록 스토리지**:
   - **AWS EBS io2/io2 Block Express**: 높은 IOPS와 처리량을 제공하는 SSD 기반 블록 스토리지
   - **GCP Persistent Disk SSD**: 높은 IOPS와 처리량을 제공하는 SSD 기반 블록 스토리지
   - **Azure Ultra Disk**: 매우 높은 IOPS와 처리량을 제공하는 SSD 기반 블록 스토리지

3. **객체 스토리지**:
   - **Amazon S3**: 대규모 데이터셋 저장에 적합한 확장성 높은 객체 스토리지
   - **Google Cloud Storage**: 대규모 데이터셋 저장에 적합한 확장성 높은 객체 스토리지
   - **Azure Blob Storage**: 대규모 데이터셋 저장에 적합한 확장성 높은 객체 스토리지

**스토리지 구성 예시(FSx for Lustre):**
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
  name: ml-dataset
spec:
  accessModes:
    - ReadWriteMany
  storageClassName: fsx-lustre
  resources:
    requests:
      storage: 1200Gi

---
# 학습 작업에서 사용
apiVersion: kubeflow.org/v1
kind: TFJob
metadata:
  name: distributed-training
spec:
  tfReplicaSpecs:
    Worker:
      replicas: 4
      template:
        spec:
          containers:
          - name: tensorflow
            image: tensorflow/tensorflow:2.6.0-gpu
            command:
            - python
            - /opt/model/train.py
            volumeMounts:
            - name: dataset
              mountPath: /data
            resources:
              limits:
                nvidia.com/gpu: 1
          volumes:
          - name: dataset
            persistentVolumeClaim:
              claimName: ml-dataset
```

**스토리지 선택 시 고려해야 할 성능 지표:**
1. **처리량(Throughput)**: 초당 읽기/쓰기할 수 있는 데이터의 양(MB/s 또는 GB/s)
2. **IOPS(Input/Output Operations Per Second)**: 초당 수행할 수 있는 I/O 작업 수
3. **지연 시간(Latency)**: I/O 요청에 대한 응답 시간
4. **병렬 접근 지원**: 여러 클라이언트가 동시에 접근할 수 있는 능력
5. **확장성**: 데이터 증가에 따른 성능 유지 능력

**AI/ML 워크로드 유형별 권장 스토리지:**
1. **대규모 분산 학습**: FSx for Lustre, HDFS, Ceph
2. **단일 노드 학습**: 고성능 SSD 블록 스토리지
3. **데이터 전처리**: 분산 파일 시스템 또는 객체 스토리지
4. **모델 서빙**: 고성능 SSD 블록 스토리지 또는 메모리 내 스토리지

**스토리지 성능 테스트:**
```bash
# FIO를 사용한 스토리지 성능 테스트
kubectl run fio-test --image=nixery.dev/shell/fio --restart=Never -- \
  fio --name=benchmark --directory=/data --direct=1 --rw=randread --bs=4k \
  --size=1G --numjobs=16 --runtime=60 --group_reporting
```

**다른 옵션들의 문제점:**
- A. 스토리지 용량: 중요하지만, 용량만으로는 AI/ML 워크로드의 성능 요구 사항을 충족할 수 없습니다.
- B. 스토리지 클래스 유형: 스토리지 클래스는 프로비저닝 방법을 정의하지만, 그 자체로 성능 특성을 완전히 결정하지는 않습니다.
- D. 스토리지 프로비저너: 프로비저너는 스토리지 생성 방법을 정의하지만, 워크로드의 성능 요구 사항을 직접적으로 해결하지는 않습니다.
</details>

### 4. Kubernetes에서 AI/ML 워크로드를 위한 리소스 할당 시 가장 효과적인 방법은 무엇인가요?

A. 모든 파드에 동일한 리소스 할당  
B. 워크로드 특성에 따른 리소스 프로파일링 및 최적화  
C. 항상 최대 리소스 요청  
D. 리소스 요청 없이 배포  

<details>
<summary>정답 및 설명</summary>

**정답: B. 워크로드 특성에 따른 리소스 프로파일링 및 최적화**

**설명:**
Kubernetes에서 AI/ML 워크로드를 위한 리소스 할당 시 가장 효과적인 방법은 워크로드 특성에 따른 리소스 프로파일링 및 최적화입니다. AI/ML 워크로드는 학습, 추론, 데이터 전처리 등 다양한 단계에서 서로 다른 리소스 요구 사항을 가지며, 각 워크로드의 특성을 이해하고 그에 맞게 리소스를 할당하는 것이 성능과 비용 효율성을 최적화하는 데 중요합니다.

**AI/ML 워크로드 리소스 프로파일링 방법:**
1. **벤치마킹**: 다양한 리소스 구성으로 워크로드를 실행하고 성능을 측정합니다.
2. **모니터링**: 실제 리소스 사용량을 모니터링하여 패턴을 파악합니다.
3. **점진적 조정**: 초기 추정치에서 시작하여 점진적으로 리소스를 조정합니다.
4. **자동 스케일링**: 워크로드 요구에 따라 자동으로 리소스를 조정합니다.

**AI/ML 워크로드 유형별 리소스 특성:**

1. **모델 학습**:
   - CPU: 데이터 전처리 및 피처 엔지니어링에 중요
   - GPU: 딥러닝 모델 학습에 필수적
   - 메모리: 대규모 데이터셋 및 모델 파라미터 저장에 필요
   - 스토리지: 데이터셋 및 체크포인트 저장에 필요

2. **모델 추론**:
   - CPU: 간단한 모델 또는 배치 추론에 적합
   - GPU: 복잡한 모델 또는 실시간 추론에 유리
   - 메모리: 모델 로딩 및 입력/출력 처리에 필요
   - 지연 시간: 실시간 추론에 중요

3. **데이터 전처리**:
   - CPU: 병렬 처리 능력이 중요
   - 메모리: 대규모 데이터셋 처리에 필요
   - 스토리지 I/O: 데이터 읽기/쓰기 성능이 중요

**리소스 최적화 예시:**
```yaml
# 학습 작업 - GPU 및 높은 메모리 요구
apiVersion: kubeflow.org/v1
kind: TFJob
metadata:
  name: training-job
spec:
  tfReplicaSpecs:
    Worker:
      replicas: 4
      template:
        spec:
          containers:
          - name: tensorflow
            image: tensorflow/tensorflow:2.6.0-gpu
            resources:
              requests:
                cpu: 4
                memory: 16Gi
                nvidia.com/gpu: 1
              limits:
                cpu: 8
                memory: 32Gi
                nvidia.com/gpu: 1

---
# 추론 서비스 - 낮은 지연 시간 요구
apiVersion: apps/v1
kind: Deployment
metadata:
  name: inference-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: inference
  template:
    metadata:
      labels:
        app: inference
    spec:
      containers:
      - name: inference
        image: tensorflow/serving:2.6.0-gpu
        resources:
          requests:
            cpu: 2
            memory: 4Gi
            nvidia.com/gpu: 1
          limits:
            cpu: 4
            memory: 8Gi
            nvidia.com/gpu: 1
        env:
        - name: TF_FORCE_GPU_ALLOW_GROWTH
          value: "true"

---
# 데이터 전처리 작업 - CPU 및 메모리 집약적
apiVersion: batch/v1
kind: Job
metadata:
  name: data-preprocessing
spec:
  template:
    spec:
      containers:
      - name: preprocessing
        image: python:3.9
        resources:
          requests:
            cpu: 8
            memory: 16Gi
          limits:
            cpu: 16
            memory: 32Gi
```

**리소스 모니터링 및 최적화 도구:**
1. **Prometheus + Grafana**: 리소스 사용량 모니터링 및 시각화
2. **Kubernetes Metrics Server**: 기본 리소스 메트릭 수집
3. **NVIDIA DCGM Exporter**: GPU 메트릭 수집
4. **Vertical Pod Autoscaler**: 리소스 요청 자동 조정
5. **Horizontal Pod Autoscaler**: 파드 수 자동 조정

**리소스 최적화 전략:**
1. **GPU 공유**: NVIDIA MPS 또는 시간 분할 스케줄링을 통해 여러 작업 간에 GPU 공유
2. **메모리 최적화**: 모델 양자화, 지연 로딩, 메모리 효율적인 알고리즘 사용
3. **배치 처리**: 추론 요청을 배치로 처리하여 처리량 향상
4. **자동 스케일링**: 부하에 따라 리소스 자동 조정
5. **노드 어피니티**: 특정 하드웨어 특성을 가진 노드에 워크로드 배치

**GPU 메모리 최적화 예시:**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: gpu-memory-optimized
spec:
  containers:
  - name: tensorflow
    image: tensorflow/tensorflow:2.6.0-gpu
    env:
    - name: TF_FORCE_GPU_ALLOW_GROWTH
      value: "true"  # 필요한 만큼만 GPU 메모리 할당
    - name: TF_GPU_ALLOCATOR
      value: "cuda_malloc_async"  # 비동기 메모리 할당자 사용
    resources:
      limits:
        nvidia.com/gpu: 1
```

**CPU 및 메모리 최적화 예시:**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: cpu-memory-optimized
spec:
  containers:
  - name: python
    image: python:3.9
    env:
    - name: OMP_NUM_THREADS
      value: "4"  # OpenMP 스레드 수 제한
    - name: MKL_NUM_THREADS
      value: "4"  # Intel MKL 스레드 수 제한
    resources:
      requests:
        cpu: 4
        memory: 8Gi
      limits:
        cpu: 8
        memory: 16Gi
```

**다른 옵션들의 문제점:**
- A. 모든 파드에 동일한 리소스 할당: 서로 다른 워크로드 특성을 고려하지 않아 리소스 낭비 또는 부족 문제가 발생할 수 있습니다.
- C. 항상 최대 리소스 요청: 비용 효율성이 떨어지고, 클러스터 리소스 활용도가 낮아집니다.
- D. 리소스 요청 없이 배포: 스케줄링 및 리소스 경합 문제가 발생할 수 있으며, 특히 GPU와 같은 제한된 리소스의 경우 적절한 할당이 중요합니다.
</details>
### 5. Kubernetes에서 AI/ML 모델 서빙을 위한 가장 적합한 방법은 무엇인가요?

A. 일반 Deployment 리소스 사용  
B. KServe(이전의 KFServing) 또는 Seldon Core와 같은 전문 서빙 플랫폼 사용  
C. StatefulSet 리소스 사용  
D. CronJob 리소스 사용  

<details>
<summary>정답 및 설명</summary>

**정답: B. KServe(이전의 KFServing) 또는 Seldon Core와 같은 전문 서빙 플랫폼 사용**

**설명:**
Kubernetes에서 AI/ML 모델 서빙을 위한 가장 적합한 방법은 KServe(이전의 KFServing) 또는 Seldon Core와 같은 전문 서빙 플랫폼을 사용하는 것입니다. 이러한 플랫폼은 모델 서빙에 필요한 다양한 기능(모델 버전 관리, A/B 테스트, 카나리 배포, 자동 스케일링, 모니터링 등)을 제공하며, 다양한 ML 프레임워크를 지원합니다.

**전문 모델 서빙 플랫폼의 주요 기능:**
1. **다양한 ML 프레임워크 지원**: TensorFlow, PyTorch, ONNX, scikit-learn 등 다양한 프레임워크로 학습된 모델 지원
2. **모델 버전 관리**: 여러 버전의 모델을 관리하고 롤백 가능
3. **트래픽 분할**: A/B 테스트, 카나리 배포 등을 위한 트래픽 분할 기능
4. **자동 스케일링**: 요청 부하에 따른 자동 스케일링
5. **모니터링 및 로깅**: 모델 성능, 지연 시간, 처리량 등의 모니터링
6. **전처리 및 후처리**: 입력 데이터 전처리 및 출력 데이터 후처리 파이프라인
7. **배치 추론**: 대량의 데이터에 대한 배치 추론 지원
8. **모델 설명 가능성**: 모델 예측에 대한 설명 기능

**KServe 예시:**
```yaml
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  name: sklearn-iris
spec:
  predictor:
    sklearn:
      storageUri: "gs://kserve-examples/models/sklearn/iris"
      resources:
        requests:
          cpu: 100m
          memory: 256Mi
        limits:
          cpu: 1
          memory: 1Gi
```

**Seldon Core 예시:**
```yaml
apiVersion: machinelearning.seldon.io/v1
kind: SeldonDeployment
metadata:
  name: iris-model
spec:
  name: iris
  predictors:
  - name: default
    replicas: 1
    graph:
      name: classifier
      implementation: SKLEARN_SERVER
      modelUri: "gs://seldon-models/sklearn/iris"
      envSecretRefName: seldon-init-container-secret
    engineResources:
      requests:
        cpu: 100m
        memory: 256Mi
      limits:
        cpu: 1
        memory: 1Gi
```

**고급 서빙 기능 예시:**

1. **카나리 배포(KServe):**
```yaml
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  name: sklearn-iris
spec:
  predictor:
    canaryTrafficPercent: 20
    sklearn:
      storageUri: "gs://kserve-examples/models/sklearn/iris-v2"
    containers:
    - name: sklearn-v1
      image: kserve/sklearnserver:latest
      args:
      - --model_dir=/mnt/models
      - --model_name=sklearn-iris
```

2. **전처리 및 후처리 파이프라인(Seldon Core):**
```yaml
apiVersion: machinelearning.seldon.io/v1
kind: SeldonDeployment
metadata:
  name: iris-pipeline
spec:
  name: iris
  predictors:
  - name: default
    replicas: 1
    graph:
      name: preprocessor
      type: TRANSFORMER
      children:
      - name: model
        type: MODEL
        implementation: SKLEARN_SERVER
        modelUri: "gs://seldon-models/sklearn/iris"
        children:
        - name: postprocessor
          type: TRANSFORMER
          implementation: PYTHON
          modelUri: "gs://seldon-models/postprocessor"
```

3. **멀티 모델 서빙(KServe):**
```yaml
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  name: multi-model-example
spec:
  predictor:
    triton:
      storageUri: "gs://kserve-examples/models/triton/multi-model"
```

**전문 서빙 플랫폼 설치:**
```bash
# KServe 설치
kubectl apply -f https://github.com/kserve/kserve/releases/download/v0.8.0/kserve.yaml

# Seldon Core 설치 (Helm 사용)
helm install seldon-core seldon-core-operator \
  --repo https://storage.googleapis.com/seldon-charts \
  --namespace seldon-system \
  --create-namespace
```

**모델 서빙 모니터링:**
```bash
# KServe 서비스 상태 확인
kubectl get inferenceservices

# Seldon Core 서비스 상태 확인
kubectl get seldondeployments
```

**일반 Deployment와 전문 서빙 플랫폼 비교:**

| 기능 | 일반 Deployment | 전문 서빙 플랫폼 |
|------|----------------|----------------|
| 기본 서빙 | 지원 | 지원 |
| 모델 버전 관리 | 수동 구현 필요 | 기본 지원 |
| 트래픽 분할 | 수동 구현 필요 | 기본 지원 |
| 자동 스케일링 | HPA로 제한적 지원 | 고급 스케일링 지원 |
| 모니터링 | 수동 구현 필요 | 기본 지원 |
| 전처리/후처리 | 수동 구현 필요 | 기본 지원 |
| 배치 추론 | 수동 구현 필요 | 기본 지원 |
| 모델 설명 가능성 | 수동 구현 필요 | 기본 지원 |

**다른 옵션들의 문제점:**
- A. 일반 Deployment 리소스 사용: 기본적인 서빙은 가능하지만, 모델 버전 관리, 트래픽 분할, 고급 모니터링 등의 기능이 부족합니다.
- C. StatefulSet 리소스 사용: 상태 유지가 필요한 애플리케이션에 적합하지만, 모델 서빙에 필요한 특화된 기능이 부족합니다.
- D. CronJob 리소스 사용: 주기적인 배치 작업에 적합하며, 실시간 모델 서빙에는 적합하지 않습니다.
</details>

### 6. Kubernetes에서 AI/ML 워크로드를 위한 자동 스케일링 구성 시 가장 적합한 메트릭은 무엇인가요?

A. CPU 사용률  
B. 메모리 사용률  
C. GPU 사용률  
D. 워크로드 특성에 따른 사용자 정의 메트릭  

<details>
<summary>정답 및 설명</summary>

**정답: D. 워크로드 특성에 따른 사용자 정의 메트릭**

**설명:**
Kubernetes에서 AI/ML 워크로드를 위한 자동 스케일링 구성 시 가장 적합한 메트릭은 워크로드 특성에 따른 사용자 정의 메트릭입니다. AI/ML 워크로드는 CPU, 메모리, GPU 사용률 외에도 요청 지연 시간, 큐 길이, 배치 크기 등 다양한 요소에 따라 스케일링이 필요할 수 있으며, 워크로드의 특성을 가장 잘 반영하는 메트릭을 선택하는 것이 중요합니다.

**AI/ML 워크로드를 위한 자동 스케일링 메트릭 유형:**
1. **리소스 기반 메트릭**:
   - CPU 사용률
   - 메모리 사용률
   - GPU 사용률

2. **사용자 정의 메트릭**:
   - 요청 지연 시간(Latency)
   - 요청 처리량(Throughput)
   - 큐 길이(Queue Length)
   - 배치 크기(Batch Size)
   - 모델 정확도(Model Accuracy)
   - 추론 시간(Inference Time)

3. **외부 메트릭**:
   - 메시지 큐 길이(Kafka, RabbitMQ 등)
   - 데이터베이스 쿼리 지연 시간
   - API 게이트웨이 요청 수

**AI/ML 워크로드 유형별 권장 메트릭:**
1. **모델 추론 서비스**:
   - 요청 지연 시간
   - 초당 요청 수(RPS)
   - 큐에 대기 중인 요청 수

2. **배치 처리 작업**:
   - 작업 큐 길이
   - 처리 대기 중인 데이터 양
   - 작업 완료 시간

3. **스트리밍 처리**:
   - 스트림 처리 지연 시간
   - 이벤트 처리 속도
   - 미처리 이벤트 수

**Horizontal Pod Autoscaler(HPA) 예시:**
```yaml
# CPU 사용률 기반 HPA
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: inference-hpa-cpu
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: inference-service
  minReplicas: 1
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70

---
# 사용자 정의 메트릭 기반 HPA
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: inference-hpa-custom
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: inference-service
  minReplicas: 1
  maxReplicas: 10
  metrics:
  - type: Pods
    pods:
      metric:
        name: inference_latency_milliseconds
      target:
        type: AverageValue
        averageValue: 100

---
# 외부 메트릭 기반 HPA
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: inference-hpa-external
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: inference-service
  minReplicas: 1
  maxReplicas: 10
  metrics:
  - type: External
    external:
      metric:
        name: kafka_topic_lag
        selector:
          matchLabels:
            topic: inference-requests
      target:
        type: AverageValue
        averageValue: 100
```

**사용자 정의 메트릭 수집 및 노출:**
1. **Prometheus Adapter**: Prometheus에서 수집한 메트릭을 Kubernetes API로 노출
2. **Custom Metrics API**: 사용자 정의 메트릭을 Kubernetes API로 노출
3. **External Metrics API**: 외부 시스템의 메트릭을 Kubernetes API로 노출

**Prometheus Adapter 설정 예시:**
```yaml
# Prometheus Adapter 구성
apiVersion: v1
kind: ConfigMap
metadata:
  name: adapter-config
  namespace: monitoring
data:
  config.yaml: |
    rules:
    - seriesQuery: 'inference_latency_milliseconds{namespace!="",pod!=""}'
      resources:
        overrides:
          namespace: {resource: "namespace"}
          pod: {resource: "pod"}
      name:
        matches: "inference_latency_milliseconds"
      metricsQuery: 'avg(<<.Series>>{<<.LabelMatchers>>})'
```

**KEDA(Kubernetes Event-driven Autoscaling) 예시:**
```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: inference-scaler
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: inference-service
  minReplicaCount: 1
  maxReplicaCount: 10
  triggers:
  - type: prometheus
    metadata:
      serverAddress: http://prometheus.monitoring.svc:9090
      metricName: inference_latency_milliseconds
      threshold: "100"
      query: avg(inference_latency_milliseconds{service="inference-service"})
```

**GPU 사용률 기반 스케일링:**
GPU 사용률 기반 스케일링은 NVIDIA DCGM Exporter와 같은 도구를 사용하여 구현할 수 있습니다.

```yaml
# NVIDIA DCGM Exporter 배포
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: dcgm-exporter
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: dcgm-exporter
  template:
    metadata:
      labels:
        app: dcgm-exporter
    spec:
      containers:
      - name: dcgm-exporter
        image: nvidia/dcgm-exporter:2.3.1-2.6.1-ubuntu20.04
        ports:
        - containerPort: 9400
          name: metrics
        securityContext:
          runAsNonRoot: false
          runAsUser: 0
        volumeMounts:
        - name: docker-socket
          mountPath: /var/run/docker.sock
      volumes:
      - name: docker-socket
        hostPath:
          path: /var/run/docker.sock

---
# GPU 사용률 기반 HPA
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: inference-hpa-gpu
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: inference-service
  minReplicas: 1
  maxReplicas: 10
  metrics:
  - type: Pods
    pods:
      metric:
        name: DCGM_FI_DEV_GPU_UTIL
      target:
        type: AverageValue
        averageValue: 70
```

**자동 스케일링 전략 선택 시 고려 사항:**
1. **워크로드 특성**: 배치 처리, 실시간 추론, 스트리밍 처리 등
2. **성능 요구 사항**: 지연 시간, 처리량, 정확도 등
3. **리소스 효율성**: 비용 최적화, 리소스 활용도 등
4. **확장성**: 부하 변동에 대한 대응 능력
5. **안정성**: 급격한 스케일링으로 인한 서비스 중단 방지

**다른 옵션들의 문제점:**
- A. CPU 사용률: AI/ML 워크로드는 종종 GPU 바운드이거나 메모리 바운드일 수 있어, CPU 사용률만으로는 적절한 스케일링 결정을 내리기 어려울 수 있습니다.
- B. 메모리 사용률: 메모리 사용률은 일반적으로 워크로드 증가에 비례하여 증가하지 않을 수 있으며, 특히 모델 로딩 후에는 상대적으로 일정할 수 있습니다.
- C. GPU 사용률: GPU 사용률은 중요한 메트릭이지만, 모든 AI/ML 워크로드가 GPU를 사용하는 것은 아니며, 사용하더라도 GPU 사용률만으로는 서비스 품질을 완전히 반영하지 못할 수 있습니다.
</details>
### 7. Kubernetes에서 AI/ML 워크로드를 위한 네트워크 구성 시 가장 중요한 고려 사항은 무엇인가요?

A. 네트워크 정책 설정  
B. 서비스 메시 구현  
C. 분산 학습을 위한 고성능 네트워킹 및 토폴로지 인식  
D. 외부 접근성 구성  

<details>
<summary>정답 및 설명</summary>

**정답: C. 분산 학습을 위한 고성능 네트워킹 및 토폴로지 인식**

**설명:**
Kubernetes에서 AI/ML 워크로드를 위한 네트워크 구성 시 가장 중요한 고려 사항은 분산 학습을 위한 고성능 네트워킹 및 토폴로지 인식입니다. 분산 AI/ML 워크로드는 노드 간에 대량의 데이터와 모델 파라미터를 교환해야 하므로, 네트워크 성능이 전체 학습 및 추론 성능에 큰 영향을 미칩니다. 또한, 네트워크 토폴로지를 인식하여 가까운 노드 간에 통신이 이루어지도록 하는 것이 지연 시간을 최소화하는 데 중요합니다.

**분산 AI/ML 워크로드의 네트워크 요구 사항:**
1. **높은 대역폭**: 대량의 데이터 및 모델 파라미터 교환을 위한 높은 네트워크 대역폭
2. **낮은 지연 시간**: 노드 간 빠른 통신을 위한 낮은 네트워크 지연 시간
3. **RDMA(Remote Direct Memory Access) 지원**: 메모리 간 직접 데이터 전송을 통한 CPU 오버헤드 감소
4. **토폴로지 인식**: 네트워크 토폴로지를 고려한 파드 배치
5. **GPU 직접 통신**: GPU 간 직접 통신을 위한 NVIDIA GPUDirect RDMA와 같은 기술 지원

**고성능 네트워킹 구성 예시:**
```yaml
# 고성능 네트워킹을 위한 노드 셀렉터 및 어피니티 설정
apiVersion: kubeflow.org/v1
kind: TFJob
metadata:
  name: distributed-training
spec:
  tfReplicaSpecs:
    Worker:
      replicas: 4
      template:
        spec:
          nodeSelector:
            network-type: high-performance
          affinity:
            podAntiAffinity:
              preferredDuringSchedulingIgnoredDuringExecution:
              - weight: 100
                podAffinityTerm:
                  labelSelector:
                    matchExpressions:
                    - key: tf-job-name
                      operator: In
                      values:
                      - distributed-training
                  topologyKey: kubernetes.io/hostname
            nodeAffinity:
              requiredDuringSchedulingIgnoredDuringExecution:
                nodeSelectorTerms:
                - matchExpressions:
                  - key: topology.kubernetes.io/zone
                    operator: In
                    values:
                    - us-west-2a
          containers:
          - name: tensorflow
            image: tensorflow/tensorflow:2.6.0-gpu
            env:
            - name: TF_CONFIG
              valueFrom:
                configMapKeyRef:
                  name: tf-config
                  key: tf-config.json
            resources:
              limits:
                nvidia.com/gpu: 1
```

**네트워크 토폴로지 인식 구성:**
```yaml
# 토폴로지 분산 제약 조건 설정
apiVersion: v1
kind: Pod
metadata:
  name: ml-worker
  labels:
    app: distributed-training
spec:
  topologySpreadConstraints:
  - maxSkew: 1
    topologyKey: kubernetes.io/hostname
    whenUnsatisfiable: DoNotSchedule
    labelSelector:
      matchLabels:
        app: distributed-training
  - maxSkew: 1
    topologyKey: topology.kubernetes.io/zone
    whenUnsatisfiable: ScheduleAnyway
    labelSelector:
      matchLabels:
        app: distributed-training
  containers:
  - name: ml-container
    image: ml-training:latest
```

**고성능 네트워크 인터페이스 구성:**
```yaml
# Multus CNI를 사용한 고성능 네트워크 인터페이스 구성
apiVersion: "k8s.cni.cncf.io/v1"
kind: NetworkAttachmentDefinition
metadata:
  name: sriov-net
spec:
  config: '{
    "cniVersion": "0.3.1",
    "name": "sriov-net",
    "type": "sriov",
    "ipam": {
      "type": "host-local",
      "subnet": "192.168.1.0/24",
      "rangeStart": "192.168.1.10",
      "rangeEnd": "192.168.1.200"
    }
  }'

---
apiVersion: v1
kind: Pod
metadata:
  name: ml-worker
  annotations:
    k8s.v1.cni.cncf.io/networks: sriov-net
spec:
  containers:
  - name: ml-container
    image: ml-training:latest
    resources:
      limits:
        intel.com/sriov: 1
```

**RDMA 지원 구성:**
```yaml
# RDMA 지원을 위한 구성
apiVersion: "k8s.cni.cncf.io/v1"
kind: NetworkAttachmentDefinition
metadata:
  name: rdma-net
spec:
  config: '{
    "cniVersion": "0.3.1",
    "name": "rdma-net",
    "type": "rdma",
    "ipam": {
      "type": "host-local",
      "subnet": "192.168.2.0/24"
    },
    "deviceID": "0000:03:00.0"
  }'

---
apiVersion: v1
kind: Pod
metadata:
  name: rdma-pod
  annotations:
    k8s.v1.cni.cncf.io/networks: rdma-net
spec:
  containers:
  - name: rdma-container
    image: rdma-app:latest
    securityContext:
      capabilities:
        add: ["IPC_LOCK"]
    volumeMounts:
    - name: rdma-devices
      mountPath: /dev/infiniband
  volumes:
  - name: rdma-devices
    hostPath:
      path: /dev/infiniband
```

**NVIDIA GPUDirect RDMA 구성:**
```yaml
# NVIDIA GPUDirect RDMA 지원을 위한 구성
apiVersion: v1
kind: Pod
metadata:
  name: gpudirect-pod
spec:
  containers:
  - name: gpudirect-container
    image: nvidia/cuda:11.0-base
    command: ["sleep", "infinity"]
    resources:
      limits:
        nvidia.com/gpu: 1
    securityContext:
      capabilities:
        add: ["IPC_LOCK"]
    volumeMounts:
    - name: nvidia-dev
      mountPath: /dev/nvidia0
    - name: nvidia-uvm
      mountPath: /dev/nvidia-uvm
    - name: nvidia-uvm-tools
      mountPath: /dev/nvidia-uvm-tools
    - name: nvidia-modeset
      mountPath: /dev/nvidia-modeset
  volumes:
  - name: nvidia-dev
    hostPath:
      path: /dev/nvidia0
  - name: nvidia-uvm
    hostPath:
      path: /dev/nvidia-uvm
  - name: nvidia-uvm-tools
    hostPath:
      path: /dev/nvidia-uvm-tools
  - name: nvidia-modeset
    hostPath:
      path: /dev/nvidia-modeset
```

**네트워크 성능 최적화 전략:**
1. **노드 배치 최적화**: 동일한 랙 또는 가까운 노드에 관련 파드 배치
2. **네트워크 인터페이스 최적화**: SR-IOV, DPDK 등의 기술을 사용하여 네트워크 성능 향상
3. **네트워크 토폴로지 인식**: 토폴로지 분산 제약 조건을 사용하여 네트워크 토폴로지를 고려한 파드 배치
4. **전용 네트워크 사용**: AI/ML 워크로드를 위한 전용 네트워크 인터페이스 구성
5. **MTU 최적화**: 대형 패킷 전송을 위한 MTU(Maximum Transmission Unit) 최적화

**네트워크 성능 테스트:**
```bash
# iperf3를 사용한 네트워크 성능 테스트
kubectl run iperf3-server --image=networkstatic/iperf3 --port=5201 -- -s
kubectl expose pod iperf3-server --port=5201 --target-port=5201

kubectl run iperf3-client --image=networkstatic/iperf3 --rm -it -- -c iperf3-server -p 5201 -t 30
```

**다른 옵션들의 문제점:**
- A. 네트워크 정책 설정: 보안을 위해 중요하지만, AI/ML 워크로드의 성능에 직접적인 영향을 미치지 않습니다.
- B. 서비스 메시 구현: 마이크로서비스 아키텍처에 유용하지만, AI/ML 워크로드의 고성능 네트워킹 요구 사항을 충족하지 않습니다.
- D. 외부 접근성 구성: 모델 서빙에 중요하지만, 분산 학습의 성능에는 직접적인 영향을 미치지 않습니다.
</details>

### 8. Kubernetes에서 AI/ML 워크로드를 위한 보안 구성 시 가장 중요한 고려 사항은 무엇인가요?

A. 네트워크 정책 설정  
B. 모델 및 데이터에 대한 접근 제어 및 암호화  
C. 컨테이너 이미지 스캐닝  
D. 파드 보안 정책 설정  

<details>
<summary>정답 및 설명</summary>

**정답: B. 모델 및 데이터에 대한 접근 제어 및 암호화**

**설명:**
Kubernetes에서 AI/ML 워크로드를 위한 보안 구성 시 가장 중요한 고려 사항은 모델 및 데이터에 대한 접근 제어 및 암호화입니다. AI/ML 워크로드는 종종 민감한 데이터와 지적 재산권이 있는 모델을 다루기 때문에, 이러한 자산을 보호하는 것이 가장 중요합니다. 데이터 유출이나 모델 도난은 심각한 비즈니스 및 규제 영향을 미칠 수 있습니다.

**AI/ML 워크로드의 주요 보안 위험:**
1. **데이터 유출**: 학습 데이터, 추론 데이터 등의 민감한 정보 유출
2. **모델 도난**: 지적 재산권이 있는 모델 파일 도난
3. **모델 오염**: 적대적 공격을 통한 모델 성능 저하 또는 편향 주입
4. **추론 조작**: 입력 데이터 조작을 통한 잘못된 예측 유도
5. **권한 상승**: 과도한 권한을 통한 시스템 접근

**모델 및 데이터 보안을 위한 주요 전략:**
1. **접근 제어**:
   - RBAC(Role-Based Access Control)을 통한 세분화된 권한 관리
   - 최소 권한 원칙 적용
   - 서비스 계정 분리

2. **암호화**:
   - 저장 데이터 암호화(Encryption at Rest)
   - 전송 중 데이터 암호화(Encryption in Transit)
   - 모델 파일 암호화

3. **비밀 관리**:
   - Kubernetes Secrets 또는 외부 비밀 관리 시스템 사용
   - API 키, 인증 토큰 등의 안전한 관리

4. **컨테이너 보안**:
   - 최소 권한으로 컨테이너 실행
   - 읽기 전용 파일 시스템 사용
   - 루트가 아닌 사용자로 실행

**RBAC 구성 예시:**
```yaml
# 모델 접근을 위한 역할 정의
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: model-reader
  namespace: ml-models
rules:
- apiGroups: [""]
  resources: ["secrets", "configmaps"]
  verbs: ["get", "list"]
  resourceNames: ["model-weights", "model-config"]

---
# 모델 접근 역할 바인딩
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: model-reader-binding
  namespace: ml-models
subjects:
- kind: ServiceAccount
  name: inference-service
  namespace: ml-models
roleRef:
  kind: Role
  name: model-reader
  apiGroup: rbac.authorization.k8s.io
```

**암호화된 모델 저장 예시:**
```yaml
# 암호화된 모델 저장을 위한 Secret
apiVersion: v1
kind: Secret
metadata:
  name: model-weights
  namespace: ml-models
type: Opaque
data:
  model.h5: <base64-encoded-encrypted-model>

---
# 암호화된 모델을 사용하는 파드
apiVersion: v1
kind: Pod
metadata:
  name: inference-pod
  namespace: ml-models
spec:
  serviceAccountName: inference-service
  containers:
  - name: inference
    image: ml-inference:latest
    volumeMounts:
    - name: model-volume
      mountPath: /models
      readOnly: true
    env:
    - name: MODEL_ENCRYPTION_KEY
      valueFrom:
        secretKeyRef:
          name: model-encryption-keys
          key: key1
  volumes:
  - name: model-volume
    secret:
      secretName: model-weights
```

**외부 비밀 관리 시스템 통합 예시(HashiCorp Vault):**
```yaml
# Vault Agent Injector를 사용한 비밀 주입
apiVersion: v1
kind: Pod
metadata:
  name: ml-training
  namespace: ml-workloads
  annotations:
    vault.hashicorp.com/agent-inject: "true"
    vault.hashicorp.com/agent-inject-secret-db-creds: "database/creds/ml-training-role"
    vault.hashicorp.com/role: "ml-training-role"
spec:
  serviceAccountName: ml-training
  containers:
  - name: training
    image: ml-training:latest
```

**데이터 암호화 구성 예시:**
```yaml
# EBS 암호화를 사용한 PersistentVolume
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: encrypted-data
  namespace: ml-workloads
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: encrypted-storage
  resources:
    requests:
      storage: 100Gi

---
# 암호화된 스토리지 클래스
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: encrypted-storage
provisioner: kubernetes.io/aws-ebs
parameters:
  type: gp3
  encrypted: "true"
  kmsKeyId: arn:aws:kms:us-west-2:111122223333:key/1234abcd-12ab-34cd-56ef-1234567890ab
```

**컨테이너 보안 강화 예시:**
```yaml
# 보안 강화된 파드 구성
apiVersion: v1
kind: Pod
metadata:
  name: secure-ml-pod
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    runAsGroup: 1000
    fsGroup: 1000
  containers:
  - name: ml-container
    image: ml-image:latest
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
        - ALL
    volumeMounts:
    - name: tmp
      mountPath: /tmp
    - name: model-output
      mountPath: /output
  volumes:
  - name: tmp
    emptyDir: {}
  - name: model-output
    persistentVolumeClaim:
      claimName: model-output-pvc
```

**네트워크 정책 예시:**
```yaml
# ML 워크로드를 위한 네트워크 정책
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: ml-network-policy
  namespace: ml-workloads
spec:
  podSelector:
    matchLabels:
      app: ml-inference
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
      port: 8080
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
          name: logging
    ports:
    - protocol: TCP
      port: 8125
```

**모델 및 데이터 보안을 위한 추가 전략:**
1. **모델 서명 및 검증**: 모델 파일에 디지털 서명을 적용하고 사용 전에 검증
2. **모델 버전 관리**: 모델 버전 및 변경 사항 추적
3. **감사 로깅**: 모델 및 데이터 접근에 대한 감사 로그 유지
4. **데이터 마스킹**: 민감한 데이터 필드 마스킹
5. **차등 프라이버시**: 개인 정보 보호를 위한 차등 프라이버시 기법 적용

**다른 옵션들의 문제점:**
- A. 네트워크 정책 설정: 중요하지만, 모델 및 데이터 자체의 보안을 직접적으로 보장하지는 않습니다.
- C. 컨테이너 이미지 스캐닝: 취약점 관리에 중요하지만, 모델 및 데이터 보안을 직접적으로 다루지 않습니다.
- D. 파드 보안 정책 설정: 컨테이너 실행 환경의 보안을 강화하지만, 모델 및 데이터 자체의 보안을 직접적으로 보장하지는 않습니다.
</details>
### 9. Kubernetes에서 AI/ML 워크로드를 위한 로깅 및 모니터링 구성 시 가장 중요한 지표는 무엇인가요?

A. 파드 및 노드 상태  
B. 모델 성능 메트릭(정확도, 지연 시간 등) 및 리소스 사용량  
C. API 호출 수  
D. 네트워크 트래픽  

<details>
<summary>정답 및 설명</summary>

**정답: B. 모델 성능 메트릭(정확도, 지연 시간 등) 및 리소스 사용량**

**설명:**
Kubernetes에서 AI/ML 워크로드를 위한 로깅 및 모니터링 구성 시 가장 중요한 지표는 모델 성능 메트릭(정확도, 지연 시간 등) 및 리소스 사용량입니다. 이러한 지표는 모델의 품질, 서비스 수준 목표(SLO) 준수 여부, 리소스 효율성을 평가하는 데 필수적이며, 모델 성능 저하나 리소스 병목 현상을 조기에 감지하는 데 도움이 됩니다.

**주요 모니터링 지표:**

1. **모델 성능 메트릭**:
   - **정확도(Accuracy)**: 모델 예측의 정확도
   - **정밀도(Precision)**: 양성으로 예측한 것 중 실제 양성의 비율
   - **재현율(Recall)**: 실제 양성 중 양성으로 예측한 비율
   - **F1 점수**: 정밀도와 재현율의 조화 평균
   - **AUC-ROC**: 이진 분류 모델의 성능 측정
   - **평균 제곱 오차(MSE)**: 회귀 모델의 오차 측정

2. **서비스 수준 메트릭**:
   - **지연 시간(Latency)**: 요청에서 응답까지의 시간
   - **처리량(Throughput)**: 단위 시간당 처리된 요청 수
   - **오류율(Error Rate)**: 실패한 요청의 비율
   - **가용성(Availability)**: 서비스가 정상적으로 응답한 시간의 비율

3. **리소스 사용량**:
   - **CPU 사용률**: 컨테이너 및 노드의 CPU 사용률
   - **메모리 사용률**: 컨테이너 및 노드의 메모리 사용률
   - **GPU 사용률**: GPU 계산 및 메모리 사용률
   - **디스크 I/O**: 스토리지 읽기/쓰기 성능
   - **네트워크 I/O**: 네트워크 송수신 성능

**모니터링 스택 구성 예시:**
```yaml
# Prometheus 구성
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
  namespace: monitoring
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
    scrape_configs:
    - job_name: 'kubernetes-pods'
      kubernetes_sd_configs:
      - role: pod
      relabel_configs:
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true
    - job_name: 'ml-metrics'
      kubernetes_sd_configs:
      - role: pod
        selectors:
        - role: pod
          label: "app=ml-inference"
      relabel_configs:
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
        action: replace
        target_label: __metrics_path__
        regex: (.+)
      - source_labels: [__address__, __meta_kubernetes_pod_annotation_prometheus_io_port]
        action: replace
        regex: ([^:]+)(?::\d+)?;(\d+)
        replacement: $1:$2
        target_label: __address__

---
# ML 서비스에서 메트릭 노출
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ml-inference
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ml-inference
  template:
    metadata:
      labels:
        app: ml-inference
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8080"
        prometheus.io/path: "/metrics"
    spec:
      containers:
      - name: inference
        image: ml-inference:latest
        ports:
        - containerPort: 8080
          name: http
        - containerPort: 9090
          name: metrics
```

**사용자 정의 메트릭 노출 예시(Python):**
```python
from prometheus_client import start_http_server, Summary, Counter, Gauge, Histogram
import time
import random

# 메트릭 정의
INFERENCE_LATENCY = Histogram('inference_latency_seconds', 'Inference latency in seconds', 
                             ['model', 'version'])
INFERENCE_REQUESTS = Counter('inference_requests_total', 'Total number of inference requests', 
                            ['model', 'version', 'status'])
MODEL_ACCURACY = Gauge('model_accuracy', 'Model accuracy', 
                      ['model', 'version', 'dataset'])
GPU_MEMORY_USAGE = Gauge('gpu_memory_usage_bytes', 'GPU memory usage in bytes', 
                        ['device'])

# 메트릭 서버 시작
start_http_server(9090)

# 메트릭 업데이트 예시
def process_request(model_name, model_version, input_data):
    start_time = time.time()
    
    try:
        # 모델 추론 수행
        result = model.predict(input_data)
        
        # 지연 시간 기록
        latency = time.time() - start_time
        INFERENCE_LATENCY.labels(model=model_name, version=model_version).observe(latency)
        
        # 요청 수 증가
        INFERENCE_REQUESTS.labels(model=model_name, version=model_version, status="success").inc()
        
        # GPU 메모리 사용량 업데이트
        GPU_MEMORY_USAGE.labels(device="gpu0").set(get_gpu_memory_usage())
        
        return result
    except Exception as e:
        # 오류 요청 수 증가
        INFERENCE_REQUESTS.labels(model=model_name, version=model_version, status="error").inc()
        raise e

# 주기적으로 모델 정확도 업데이트
def update_model_accuracy():
    while True:
        accuracy = evaluate_model_accuracy()
        MODEL_ACCURACY.labels(model="image_classifier", version="v1", dataset="validation").set(accuracy)
        time.sleep(3600)  # 1시간마다 업데이트
```

**Grafana 대시보드 구성 예시:**
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ml-dashboard
  namespace: monitoring
  labels:
    grafana_dashboard: "1"
data:
  ml-dashboard.json: |
    {
      "title": "ML Model Monitoring",
      "panels": [
        {
          "title": "Inference Latency",
          "type": "graph",
          "datasource": "Prometheus",
          "targets": [
            {
              "expr": "histogram_quantile(0.95, sum(rate(inference_latency_seconds_bucket[5m])) by (le, model, version))",
              "legendFormat": "p95 - {{model}} - {{version}}"
            },
            {
              "expr": "histogram_quantile(0.50, sum(rate(inference_latency_seconds_bucket[5m])) by (le, model, version))",
              "legendFormat": "p50 - {{model}} - {{version}}"
            }
          ]
        },
        {
          "title": "Request Rate",
          "type": "graph",
          "datasource": "Prometheus",
          "targets": [
            {
              "expr": "sum(rate(inference_requests_total[5m])) by (model, version, status)",
              "legendFormat": "{{model}} - {{version}} - {{status}}"
            }
          ]
        },
        {
          "title": "Model Accuracy",
          "type": "gauge",
          "datasource": "Prometheus",
          "targets": [
            {
              "expr": "model_accuracy",
              "legendFormat": "{{model}} - {{version}} - {{dataset}}"
            }
          ],
          "options": {
            "min": 0,
            "max": 1,
            "thresholds": [
              { "color": "red", "value": 0 },
              { "color": "yellow", "value": 0.7 },
              { "color": "green", "value": 0.9 }
            ]
          }
        },
        {
          "title": "GPU Memory Usage",
          "type": "graph",
          "datasource": "Prometheus",
          "targets": [
            {
              "expr": "gpu_memory_usage_bytes",
              "legendFormat": "{{device}}"
            }
          ]
        }
      ]
    }
```

**로깅 구성 예시:**
```yaml
# Fluent Bit 구성
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluent-bit-config
  namespace: logging
data:
  fluent-bit.conf: |
    [SERVICE]
        Flush        5
        Daemon       Off
        Log_Level    info

    [INPUT]
        Name             tail
        Tag              kube.*
        Path             /var/log/containers/*.log
        Parser           docker
        DB               /var/log/flb_kube.db
        Mem_Buf_Limit    5MB
        Skip_Long_Lines  On
        Refresh_Interval 10

    [FILTER]
        Name                kubernetes
        Match               kube.*
        Kube_URL            https://kubernetes.default.svc:443
        Kube_CA_File        /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
        Kube_Token_File     /var/run/secrets/kubernetes.io/serviceaccount/token
        Kube_Tag_Prefix     kube.var.log.containers.
        Merge_Log           On
        Merge_Log_Key       log_processed
        K8S-Logging.Parser  On
        K8S-Logging.Exclude Off

    [FILTER]
        Name         grep
        Match        kube.var.log.containers.ml-*
        Regex        log ERROR|WARN|INFO

    [OUTPUT]
        Name            es
        Match           kube.var.log.containers.ml-*
        Host            elasticsearch
        Port            9200
        Index           ml-logs
        Type            _doc
        Logstash_Format On
        Logstash_Prefix ml-logs
        Time_Key        @timestamp
        Replace_Dots    On
        Retry_Limit     False
```

**모델 성능 모니터링을 위한 추가 도구:**
1. **MLflow**: 실험 추적, 모델 버전 관리, 모델 레지스트리 제공
2. **TensorBoard**: TensorFlow 모델의 학습 과정 및 성능 시각화
3. **Weights & Biases**: 실험 추적, 모델 성능 비교, 하이퍼파라미터 최적화
4. **Seldon Core Metrics**: Seldon Core에서 제공하는 모델 서빙 메트릭
5. **KServe Metrics**: KServe에서 제공하는 모델 서빙 메트릭

**모니터링 알림 구성 예시:**
```yaml
# Prometheus 알림 규칙
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: ml-alerts
  namespace: monitoring
spec:
  groups:
  - name: ml.rules
    rules:
    - alert: HighInferenceLatency
      expr: histogram_quantile(0.95, sum(rate(inference_latency_seconds_bucket[5m])) by (le, model, version)) > 0.5
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "High inference latency"
        description: "Model {{ $labels.model }} version {{ $labels.version }} has p95 latency above 500ms"
    
    - alert: LowModelAccuracy
      expr: model_accuracy < 0.8
      for: 10m
      labels:
        severity: critical
      annotations:
        summary: "Low model accuracy"
        description: "Model {{ $labels.model }} version {{ $labels.version }} has accuracy below 80%"
    
    - alert: HighErrorRate
      expr: sum(rate(inference_requests_total{status="error"}[5m])) / sum(rate(inference_requests_total[5m])) > 0.05
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: "High error rate"
        description: "Error rate is above 5%"
```

**다른 옵션들의 문제점:**
- A. 파드 및 노드 상태: 기본적인 시스템 상태 모니터링에 중요하지만, AI/ML 워크로드의 성능과 품질을 직접적으로 반영하지 않습니다.
- C. API 호출 수: 시스템 사용량을 측정하는 데 유용하지만, 모델 성능이나 리소스 효율성을 직접적으로 나타내지 않습니다.
- D. 네트워크 트래픽: 분산 학습이나 대규모 데이터 전송에 중요하지만, 모델 성능이나 품질을 직접적으로 반영하지 않습니다.
</details>

### 10. Kubernetes에서 AI/ML 워크로드를 위한 비용 최적화 전략으로 가장 효과적인 것은 무엇인가요?

A. 항상 최신 인스턴스 유형 사용  
B. 모든 워크로드에 Spot 인스턴스 사용  
C. 워크로드 특성에 따른 적절한 인스턴스 유형 선택 및 자동 스케일링  
D. 모든 리소스에 대한 요청 및 제한 최소화  

<details>
<summary>정답 및 설명</summary>

**정답: C. 워크로드 특성에 따른 적절한 인스턴스 유형 선택 및 자동 스케일링**

**설명:**
Kubernetes에서 AI/ML 워크로드를 위한 비용 최적화 전략으로 가장 효과적인 것은 워크로드 특성에 따른 적절한 인스턴스 유형 선택 및 자동 스케일링입니다. AI/ML 워크로드는 학습, 추론, 데이터 전처리 등 다양한 단계에서 서로 다른 리소스 요구 사항을 가지며, 각 워크로드의 특성에 맞는 인스턴스 유형을 선택하고 필요에 따라 자동으로 스케일링하는 것이 비용 효율성을 최적화하는 데 중요합니다.

**워크로드 특성별 인스턴스 유형 선택:**

1. **모델 학습**:
   - **GPU 인스턴스**: 딥러닝 모델 학습에 적합
   - **메모리 최적화 인스턴스**: 대규모 데이터셋 처리에 적합
   - **컴퓨팅 최적화 인스턴스**: 계산 집약적 알고리즘에 적합

2. **모델 추론**:
   - **GPU 인스턴스**: 복잡한 모델 또는 실시간 추론에 적합
   - **CPU 인스턴스**: 간단한 모델 또는 배치 추론에 적합
   - **추론 최적화 인스턴스(AWS Inferentia, Google TPU 등)**: 추론에 특화된 인스턴스

3. **데이터 전처리**:
   - **컴퓨팅 최적화 인스턴스**: 병렬 처리에 적합
   - **메모리 최적화 인스턴스**: 대규모 데이터셋 처리에 적합
   - **스토리지 최적화 인스턴스**: I/O 집약적 작업에 적합

**노드 그룹 구성 예시:**
```yaml
# 학습용 노드 그룹 (GPU 인스턴스)
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: ml-cluster
  region: us-west-2
nodeGroups:
  - name: training-ng
    instanceType: p3.2xlarge  # GPU 인스턴스
    minSize: 0
    maxSize: 10
    labels:
      workload-type: training
    taints:
      - key: workload-type
        value: training
        effect: NoSchedule
    tags:
      k8s.io/cluster-autoscaler/enabled: "true"
      k8s.io/cluster-autoscaler/ml-cluster: "owned"

  # 추론용 노드 그룹 (CPU 인스턴스)
  - name: inference-ng
    instanceType: c5.2xlarge  # 컴퓨팅 최적화 인스턴스
    minSize: 1
    maxSize: 20
    labels:
      workload-type: inference
    tags:
      k8s.io/cluster-autoscaler/enabled: "true"
      k8s.io/cluster-autoscaler/ml-cluster: "owned"

  # 데이터 전처리용 노드 그룹 (메모리 최적화 인스턴스)
  - name: preprocessing-ng
    instanceType: r5.2xlarge  # 메모리 최적화 인스턴스
    minSize: 0
    maxSize: 10
    labels:
      workload-type: preprocessing
    tags:
      k8s.io/cluster-autoscaler/enabled: "true"
      k8s.io/cluster-autoscaler/ml-cluster: "owned"

  # Spot 인스턴스 노드 그룹 (비용 효율적인 배치 작업용)
  - name: spot-ng
    instanceTypes: ["m5.xlarge", "m5a.xlarge", "m5n.xlarge"]
    minSize: 0
    maxSize: 20
    spot: true
    labels:
      workload-type: batch
    tags:
      k8s.io/cluster-autoscaler/enabled: "true"
      k8s.io/cluster-autoscaler/ml-cluster: "owned"
```

**워크로드 배치 예시:**
```yaml
# 학습 작업 (GPU 노드에 배치)
apiVersion: batch/v1
kind: Job
metadata:
  name: training-job
spec:
  template:
    spec:
      nodeSelector:
        workload-type: training
      containers:
      - name: training
        image: training:latest
        resources:
          limits:
            nvidia.com/gpu: 1

# 추론 서비스 (CPU 노드에 배치)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: inference-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: inference
  template:
    metadata:
      labels:
        app: inference
    spec:
      nodeSelector:
        workload-type: inference
      containers:
      - name: inference
        image: inference:latest
        resources:
          requests:
            cpu: 1
            memory: 2Gi
          limits:
            cpu: 2
            memory: 4Gi

# 데이터 전처리 작업 (메모리 최적화 노드에 배치)
apiVersion: batch/v1
kind: Job
metadata:
  name: preprocessing-job
spec:
  template:
    spec:
      nodeSelector:
        workload-type: preprocessing
      containers:
      - name: preprocessing
        image: preprocessing:latest
        resources:
          requests:
            memory: 16Gi
          limits:
            memory: 32Gi

# 배치 추론 작업 (Spot 인스턴스에 배치)
apiVersion: batch/v1
kind: Job
metadata:
  name: batch-inference
spec:
  template:
    spec:
      nodeSelector:
        workload-type: batch
      tolerations:
      - key: spot
        operator: Exists
      containers:
      - name: batch-inference
        image: batch-inference:latest
```

**자동 스케일링 구성 예시:**
```yaml
# 클러스터 오토스케일러 구성
apiVersion: v1
kind: ConfigMap
metadata:
  name: cluster-autoscaler-config
  namespace: kube-system
data:
  config.yaml: |
    expendablePodsPriorityCutoff: -10
    scaleDownUtilizationThreshold: 0.5
    scaleDownUnneededTime: 5m
    scaleDownDelayAfterAdd: 5m
    scaleDownDelayAfterDelete: 0s
    scaleDownDelayAfterFailure: 3m
    maxNodeProvisionTime: 15m

# HPA 구성 (추론 서비스)
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: inference-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: inference-service
  minReplicas: 2
  maxReplicas: 20
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
        name: inference_latency_milliseconds
      target:
        type: AverageValue
        averageValue: 100
```

**비용 최적화 전략:**

1. **적절한 인스턴스 유형 선택**:
   - 워크로드 특성에 맞는 인스턴스 유형 선택
   - 비용 대비 성능 분석을 통한 최적의 인스턴스 선택
   - 특화된 인스턴스(GPU, TPU 등) 활용

2. **Spot 인스턴스 활용**:
   - 내결함성이 있는 워크로드에 Spot 인스턴스 사용
   - 다양한 인스턴스 유형 지정으로 가용성 향상
   - 중단 허용 전략 구현

3. **자동 스케일링**:
   - 클러스터 오토스케일러를 통한 노드 수 자동 조정
   - HPA를 통한 파드 수 자동 조정
   - 사용자 정의 메트릭 기반 스케일링

4. **리소스 요청 및 제한 최적화**:
   - 실제 사용량에 기반한 리소스 요청 설정
   - Vertical Pod Autoscaler를 통한 리소스 요청 자동 조정
   - 리소스 사용량 모니터링 및 최적화

5. **작업 일정 최적화**:
   - 비용이 저렴한 시간대에 배치 작업 실행
   - 우선순위가 낮은 작업은 저비용 리소스에 배치
   - 작업 큐 및 우선순위 설정

**비용 모니터링 및 최적화 도구:**
1. **Kubecost**: Kubernetes 클러스터의 비용 모니터링 및 최적화
2. **AWS Cost Explorer**: AWS 리소스 비용 분석
3. **Google Cloud Cost Management**: GCP 리소스 비용 분석
4. **Azure Cost Management**: Azure 리소스 비용 분석
5. **Prometheus + Grafana**: 사용자 정의 비용 대시보드 구성

**다른 옵션들의 문제점:**
- A. 항상 최신 인스턴스 유형 사용: 최신 인스턴스가 항상 비용 효율적이지는 않으며, 워크로드 특성에 맞는 인스턴스 선택이 더 중요합니다.
- B. 모든 워크로드에 Spot 인스턴스 사용: Spot 인스턴스는 중단될 수 있으므로, 중요하고 중단에 민감한 워크로드에는 적합하지 않습니다.
- D. 모든 리소스에 대한 요청 및 제한 최소화: 리소스 요청을 과도하게 최소화하면 성능 문제가 발생할 수 있으며, 워크로드 특성에 맞는 적절한 리소스 할당이 중요합니다.
</details>
