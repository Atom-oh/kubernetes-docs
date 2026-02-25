# 추론 프레임워크 퀴즈

이 퀴즈는 NVIDIA NIM, NVIDIA Dynamo, AIBrix, Ray Serve, AWS Neuron을 포함한 Kubernetes 배포를 위한 LLM 추론 프레임워크에 대한 이해를 테스트합니다.

## 퀴즈 문제

### 1. NVIDIA NIM이 LLM 배포에 제공하는 주요 이점은 무엇인가요?

A) 오픈소스 모델만 지원한다
B) 최적화된 추론 엔진과 OpenAI 호환 API를 갖춘 프로덕션 준비 컨테이너화된 LLM 배포를 제공한다
C) 모든 모델을 수동으로 컴파일해야 한다
D) CPU 인스턴스에서만 작동한다

<details>
<summary>정답 보기</summary>

**정답: B) 최적화된 추론 엔진과 OpenAI 호환 API를 갖춘 프로덕션 준비 컨테이너화된 LLM 배포를 제공한다**

**설명:**
NVIDIA NIM(NVIDIA Inference Microservices)은 여러 핵심 기능을 갖춘 프로덕션 준비 컨테이너화된 LLM 배포를 제공합니다:

1. **최적화된 추론 엔진**: 최대 성능을 위해 TensorRT-LLM 사용
2. **OpenAI 호환 API**: OpenAI API 호출의 드롭인 대체
3. **내장 모니터링**: Prometheus 메트릭과 Grafana 대시보드
4. **NGC Catalog 통합**: 사전 최적화된 모델에 쉽게 액세스
5. **엔터프라이즈 지원**: NVIDIA의 프로덕션 SLA 및 지원

```yaml
# NIM 배포 예시
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nim-llama-70b
spec:
  template:
    spec:
      containers:
      - name: nim
        image: nvcr.io/nim/meta/llama-3.1-70b-instruct:1.2.0
        ports:
        - containerPort: 8000
        resources:
          limits:
            nvidia.com/gpu: 8
```

</details>

### 2. NVIDIA Dynamo에서 "분리형 서빙(Disaggregated Serving)"이란 무엇인가요?

A) 단일 GPU에서 여러 모델 실행
B) Prefill(프롬프트 처리)과 Decode(토큰 생성) 단계를 서로 다른 워커 풀로 분리
C) 여러 서버에 로그 분산
D) GPU 없이 추론 실행

<details>
<summary>정답 보기</summary>

**정답: B) Prefill(프롬프트 처리)과 Decode(토큰 생성) 단계를 서로 다른 워커 풀로 분리**

**설명:**
분리형 서빙은 LLM 추론의 두 가지 주요 단계를 분리하는 NVIDIA Dynamo의 핵심 아키텍처 패턴입니다:

1. **Prefill 단계**:
   - 입력 프롬프트 처리
   - 컴퓨트 집약적 (높은 FLOPs 필요)
   - A100과 같은 고급 GPU에 적합

2. **Decode 단계**:
   - 출력 토큰을 하나씩 생성
   - 메모리 대역폭 집약적
   - A10G와 같은 비용 효율적인 GPU 사용 가능

**분리의 이점:**
- 더 나은 리소스 활용
- 이기종 GPU 사용을 통한 비용 최적화
- 전체 처리량 향상
- Prefill과 Decode 용량의 독립적 스케일링

```yaml
# Dynamo 구성 예시
prefill:
  replicas: 2
  backend: vllm
  tensor_parallel_size: 8
  # A100 GPU가 있는 p4d.24xlarge 사용

decode:
  replicas: 4
  backend: vllm
  tensor_parallel_size: 4
  # A10G GPU가 있는 g5.12xlarge 사용
```

</details>

### 3. AIBrix에서 동적 LoRA 어댑터 로딩 및 관리를 담당하는 구성 요소는 무엇인가요?

A) Gateway
B) Autoscaler
C) LoRA Manager
D) Model Registry

<details>
<summary>정답 보기</summary>

**정답: C) LoRA Manager**

**설명:**
AIBrix는 각각 특정 역할을 가진 여러 핵심 구성 요소로 이루어져 있습니다:

1. **Gateway**: 지능형 요청 라우팅 및 로드 밸런싱
2. **LoRA Manager**: 동적 LoRA 어댑터 로딩 및 관리
3. **Autoscaler**: 추론 파드를 위한 워크로드 인식 오토스케일링
4. **Model Registry**: 중앙 집중식 모델 및 어댑터 관리

**LoRA Manager**가 특별히 처리하는 것:
- 재시작 없이 LoRA 어댑터 동적 로딩
- 다른 어댑터 간 핫스왑
- 여러 어댑터를 위한 메모리 관리
- 어댑터 버전 관리 및 수명 주기

```bash
# LoRA 어댑터 등록
curl -X POST http://aibrix-registry:8081/v1/lora/register \
  -d '{
    "name": "customer-support",
    "base_model": "meta-llama/Llama-3.1-8B-Instruct",
    "lora_path": "s3://aibrix-models/lora/customer-support",
    "rank": 16,
    "alpha": 32
  }'

# 추론 요청에서 LoRA 사용
curl -X POST http://aibrix-gateway:8080/v1/chat/completions \
  -d '{
    "model": "meta-llama/Llama-3.1-8B-Instruct",
    "lora_adapter": "customer-support",
    "messages": [{"role": "user", "content": "도와주세요"}]
  }'
```

</details>

### 4. 분산 추론을 위해 Ray Serve를 배포하는 데 사용되는 Kubernetes 오퍼레이터는 무엇인가요?

A) NVIDIA GPU Operator
B) KubeRay Operator
C) Prometheus Operator
D) Flux Operator

<details>
<summary>정답 보기</summary>

**정답: B) KubeRay Operator**

**설명:**
KubeRay Operator는 분산 추론을 위한 Ray Serve를 포함하여 Ray 클러스터를 배포하고 관리하는 Kubernetes 네이티브 방법입니다.

**KubeRay Operator 기능:**
- Ray 클러스터 수명 주기 관리
- RayCluster, RayJob, RayService CRD 지원
- Ray 워커의 자동 스케일링 처리
- Kubernetes RBAC 및 네트워킹과 통합

**설치:**
```bash
helm repo add kuberay https://ray-project.github.io/kuberay-helm/
helm install kuberay-operator kuberay/kuberay-operator \
  --namespace kuberay-system \
  --create-namespace
```

**RayService 예시:**
```yaml
apiVersion: ray.io/v1
kind: RayService
metadata:
  name: vllm-serve
spec:
  serveConfigV2: |
    applications:
    - name: vllm-app
      import_path: serve_vllm:deployment
      deployments:
      - name: VLLMDeployment
        num_replicas: 2
        ray_actor_options:
          num_gpus: 1
  rayClusterConfig:
    workerGroupSpecs:
    - groupName: gpu-workers
      replicas: 2
      maxReplicas: 8
```

</details>

### 5. LLM 추론에 AWS Inferentia2(inf2) 인스턴스를 사용하는 주요 이점은 무엇인가요?

A) A100보다 높은 GPU 메모리
B) GPU 인스턴스 대비 최대 70% 낮은 비용
C) 더 빠른 모델 컴파일 시간
D) 학습 워크로드에 대한 더 나은 지원

<details>
<summary>정답 보기</summary>

**정답: B) GPU 인스턴스 대비 최대 70% 낮은 비용**

**설명:**
AWS Inferentia2는 추론 워크로드에 상당한 비용 이점을 제공합니다:

**비용 이점:**
- 유사한 GPU 인스턴스 대비 최대 70% 낮은 비용
- 달러당 높은 처리량
- 추론 전용 워크로드에 효율적

**지원 모델:**
- Llama 2/3
- Mistral
- Stable Diffusion
- 다양한 인코더 모델

**인스턴스 유형:**
| 인스턴스 | Neuron 코어 | 메모리 | 사용 사례 |
|----------|-------------|--------|----------|
| inf2.xlarge | 2 | 32 GB | 7B 모델 |
| inf2.24xlarge | 6 | 96 GB | 13B-70B 모델 |
| inf2.48xlarge | 12 | 192 GB | 70B+ 모델 |

**트레이드오프:**
- Neuron용 모델 컴파일 필요
- GPU에 비해 제한된 모델 지원
- 더 긴 초기 설정 시간

```yaml
# Neuron 리소스 요청
resources:
  limits:
    aws.amazon.com/neuron: 2
    memory: 32Gi
  requests:
    aws.amazon.com/neuron: 2
```

</details>

### 6. LLM 추론에서 첫 번째 토큰이 생성될 때까지의 시간을 측정하는 메트릭은 무엇인가요?

A) ITL (Inter-Token Latency)
B) TTFT (Time to First Token)
C) TPS (Tokens Per Second)
D) QPS (Queries Per Second)

<details>
<summary>정답 보기</summary>

**정답: B) TTFT (Time to First Token)**

**설명:**
TTFT(Time to First Token)는 사용자가 출력을 보기 전에 얼마나 기다리는지를 측정하는 LLM 추론의 중요한 지연 시간 메트릭입니다.

**주요 LLM 추론 메트릭:**

1. **TTFT (Time to First Token)**:
   - 요청 제출부터 첫 번째 토큰까지의 시간
   - 프롬프트 처리(prefill) 시간 포함
   - 목표: 좋은 UX를 위해 < 500ms

2. **ITL (Inter-Token Latency)**:
   - 연속 생성 토큰 간의 시간
   - 체감 스트리밍 속도에 영향
   - 목표: < 50ms

3. **처리량 (Throughput)**:
   - 초당 생성되는 토큰
   - 시스템 용량 측정

4. **E2E 지연 시간**:
   - 완전한 응답을 위한 총 시간
   - TTFT + (ITL * 출력_토큰)

**모니터링 예시:**
```promql
# TTFT P99
histogram_quantile(0.99, sum(rate(nim_time_to_first_token_bucket[5m])) by (le))

# ITL P99
histogram_quantile(0.99, sum(rate(nim_inter_token_latency_bucket[5m])) by (le))

# 처리량
sum(rate(nim_tokens_generated_total[5m]))
```

</details>

### 7. NVIDIA Dynamo에서 KV 인식 라우팅의 목적은 무엇인가요?

A) 사용자 위치에 따라 요청 라우팅
B) 최적의 성능을 위해 KV 캐시 지역성에 따라 요청 라우팅
C) 가장 저렴한 인스턴스로 요청 라우팅
D) 모델 버전에 따라 요청 라우팅

<details>
<summary>정답 보기</summary>

**정답: B) 최적의 성능을 위해 KV 캐시 지역성에 따라 요청 라우팅**

**설명:**
NVIDIA Dynamo의 KV 인식 라우팅은 KV 캐시 데이터가 있는 위치를 기반으로 요청 라우팅을 최적화하여 데이터 전송을 줄여 성능을 향상시킵니다.

**KV 인식 라우팅 작동 방식:**

1. **KV 캐시 추적**: 라우터가 이전 요청에 대해 캐시된 KV 데이터를 가진 decode 워커를 추적
2. **지역성 최적화**: 후속 요청(멀티턴 대화에서)을 이미 관련 KV 캐시를 가진 워커로 라우팅
3. **로드 밸런싱**: 지역성 이점과 워커 부하 간 균형 조정

**구성:**
```yaml
router:
  kv_routing:
    enabled: true
    locality_weight: 0.7  # 캐시 지역성 선호
    load_weight: 0.3      # 워커 부하 고려
```

**이점:**
- 멀티턴 대화에 대한 TTFT 감소
- 낮은 메모리 압력(중복 KV 캐시 방지)
- 더 나은 GPU 메모리 활용
- 더 높은 유효 처리량

**라우팅 결정 공식:**
```
score = locality_weight * cache_hit_score + load_weight * (1 - worker_load)
```

</details>

### 8. Kubernetes용 Neuron device plugin을 설치하는 데 사용되는 명령은 무엇인가요?

A) `kubectl apply -f nvidia-device-plugin.yml`
B) `helm install neuron-plugin aws/neuron`
C) `kubectl apply -f k8s-neuron-device-plugin.yml`
D) `eksctl create addon --name neuron-device-plugin`

<details>
<summary>정답 보기</summary>

**정답: C) `kubectl apply -f k8s-neuron-device-plugin.yml`**

**설명:**
Neuron device plugin은 AWS Neuron SDK 저장소의 공식 매니페스트와 함께 kubectl apply를 사용하여 설치됩니다.

**설치 명령:**
```bash
kubectl apply -f https://raw.githubusercontent.com/aws-neuron/aws-neuron-sdk/master/src/k8/k8s-neuron-device-plugin.yml
```

**확인:**
```bash
# DaemonSet 확인
kubectl get ds neuron-device-plugin-daemonset -n kube-system

# 노드의 Neuron 디바이스 확인
kubectl get nodes -l 'node.kubernetes.io/instance-type in (inf2.xlarge,inf2.8xlarge,inf2.24xlarge,inf2.48xlarge)' \
  -o custom-columns=NAME:.metadata.name,NEURON:.status.allocatable.aws\\.amazon\\.com/neuron
```

**리소스 요청 형식:**
```yaml
resources:
  limits:
    aws.amazon.com/neuron: 2  # 2개의 Neuron 코어 요청
```

NVIDIA device plugin은 `nvidia.com/gpu`를 사용하고 Neuron은 `aws.amazon.com/neuron`을 사용합니다.

</details>

### 9. 핵심 기능으로 내장 오토스케일링을 제공하는 추론 프레임워크는 무엇인가요?

A) vLLM 단독
B) NVIDIA NIM
C) AIBrix
D) Triton Inference Server

<details>
<summary>정답 보기</summary>

**정답: C) AIBrix**

**설명:**
AIBrix는 HPA나 KEDA와 같은 외부 솔루션이 필요한 다른 프레임워크와 달리 핵심 기능으로 내장된 워크로드 인식 오토스케일링을 제공합니다.

**AIBrix Autoscaler 기능:**
- 워크로드 인식 스케일링 정책
- 다중 메트릭 지원 (RPS, 지연 시간, GPU 활용률, 큐 깊이)
- 구성 가능한 스케일업/스케일다운 동작
- 배포별 스케일링 정책

**AIBrix Autoscaler 구성:**
```yaml
autoscaler:
  enabled: true
  poll_interval: 30s
  scaling_policies:
    - name: default
      min_replicas: 2
      max_replicas: 10
      target_metrics:
        - name: requests_per_second
          target: 50
        - name: gpu_utilization
          target: 80
        - name: queue_depth
          target: 20
      scale_up:
        stabilization_window: 60s
        step_size: 2
      scale_down:
        stabilization_window: 300s
        step_size: 1
```

**비교:**
| 프레임워크 | 자동 스케일링 |
|-----------|--------------|
| NIM | 수동 (외부 HPA/KEDA) |
| Dynamo | 수동 (외부) |
| AIBrix | 내장 |
| vLLM | 수동 (외부) |
| Ray Serve | 내장 |
| Triton | 수동 (외부) |

</details>

### 10. NVIDIA NIM 배포에서 NGC Catalog의 목적은 무엇인가요?

A) Kubernetes 매니페스트 저장
B) 사전 최적화된 모델 컨테이너 및 구성 제공
C) 클러스터 네트워킹 관리
D) 사용자 인증 처리

<details>
<summary>정답 보기</summary>

**정답: B) 사전 최적화된 모델 컨테이너 및 구성 제공**

**설명:**
NGC(NVIDIA GPU Cloud) Catalog는 최적화된 모델이 포함된 사전 빌드된 NIM 컨테이너를 포함하여 GPU 최적화 소프트웨어를 위한 NVIDIA의 저장소입니다.

**NGC Catalog 기능:**
- 사전 최적화된 모델 컨테이너
- 여러 모델 프로필 (다양한 배치 크기, 정밀도)
- 버전 관리
- 보안 스캔
- 엔터프라이즈 지원

**NGC 액세스:**
```bash
# NGC API 키 시크릿 생성
kubectl create secret generic ngc-api-key \
  --from-literal=NGC_API_KEY='your-ngc-api-key'

# 이미지 풀을 위한 docker config 시크릿 생성
kubectl create secret docker-registry ngc-credentials \
  --docker-server=nvcr.io \
  --docker-username='$oauthtoken' \
  --docker-password='your-ngc-api-key'
```

**NGC 이미지 사용:**
```yaml
spec:
  imagePullSecrets:
  - name: ngc-credentials
  containers:
  - name: nim
    image: nvcr.io/nim/meta/llama-3.1-70b-instruct:1.2.0
    env:
    - name: NGC_API_KEY
      valueFrom:
        secretKeyRef:
          name: ngc-api-key
          key: NGC_API_KEY
```

**사용 가능한 NIM 프로필:**
- `vllm-bf16-tp8`: 8-GPU 텐서 병렬, BF16 정밀도
- `vllm-fp8-tp4`: 4-GPU 텐서 병렬, FP8 정밀도
- `tensorrt-llm-fp16-tp8`: TensorRT-LLM 백엔드

</details>

### 11. NVIDIA Dynamo가 추론에 지원하는 백엔드는 무엇인가요?

A) TensorRT-LLM만
B) vLLM, SGLang, TensorRT-LLM
C) vLLM만
D) PyTorch만

<details>
<summary>정답 보기</summary>

**정답: B) vLLM, SGLang, TensorRT-LLM**

**설명:**
NVIDIA Dynamo는 백엔드에 구애받지 않도록 설계되었으며 여러 추론 엔진을 지원합니다:

1. **vLLM**:
   - 오픈소스, 고성능
   - 메모리 효율성을 위한 PagedAttention
   - 광범위한 모델 지원

2. **SGLang**:
   - 구조화된 생성에 최적화
   - 빠른 JSON/regex 제약 디코딩
   - 효율적인 접두사 캐싱

3. **TensorRT-LLM**:
   - 최대 NVIDIA GPU 성능
   - 최적화된 커널
   - INT8/FP8 양자화

**구성 예시:**
```yaml
# Prefill에 vLLM 백엔드 사용
prefill:
  backend: vllm
  model: meta-llama/Llama-3.1-70B-Instruct
  tensor_parallel_size: 8

# Decode에 SGLang 백엔드 사용
decode:
  backend: sglang
  model: meta-llama/Llama-3.1-70B-Instruct
  tensor_parallel_size: 4

# 또는 TensorRT-LLM 사용
prefill:
  backend: tensorrt-llm
  engine_path: /models/llama-70b-trt
```

이 유연성을 통해:
- 최적의 성능을 위해 백엔드 혼합
- 다양한 엔진 테스트
- 특정 작업에 특화된 백엔드 사용

</details>

### 12. EKS에서 vLLM 배포를 위한 모델 스토리지를 처리하는 권장 방법은 무엇인가요?

A) ConfigMap에 모델 저장
B) 매번 컨테이너 시작 시 모델 다운로드
C) 사전 다운로드된 모델과 함께 FSx for Lustre 또는 영구 볼륨 사용
D) 컨테이너 이미지에 모델 임베드

<details>
<summary>정답 보기</summary>

**정답: C) 사전 다운로드된 모델과 함께 FSx for Lustre 또는 영구 볼륨 사용**

**설명:**
프로덕션 LLM 배포의 경우 고성능 영구 스토리지 사용이 중요합니다:

**권장 스토리지 옵션:**

1. **FSx for Lustre**:
   - 고처리량 병렬 파일 시스템
   - 대용량 모델 파일에 이상적
   - 모델 업데이트를 위한 S3 통합
   - 최대 1000+ MB/s 처리량

2. **EBS gp3 볼륨**:
   - 단일 노드 배포에 적합
   - 비용 효율적
   - 최대 16,000 IOPS

3. **EFS**:
   - 파드 간 공유 액세스
   - FSx보다 낮은 처리량
   - 소형 모델에 적합

**FSx for Lustre 설정:**
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: model-cache
spec:
  accessModes:
  - ReadWriteMany
  storageClassName: fsx-lustre-sc
  resources:
    requests:
      storage: 1200Gi
```

**다른 옵션이 적합하지 않은 이유:**
- **ConfigMap**: 1MB 크기 제한, 대용량 파일에 부적합
- **시작 시 다운로드**: 느린 시작, 대역폭 비용, 안정성 문제
- **이미지에 임베드**: 거대한 이미지, 느린 풀, 버전 유연성 부족

</details>

### 13. NIM 배포에서 GenAI-Perf의 기능은 무엇인가요?

A) AI 이미지 생성
B) LLM 추론 성능 벤치마킹 및 프로파일링
C) GPU 메모리 관리
D) 네트워크 정책 구성

<details>
<summary>정답 보기</summary>

**정답: B) LLM 추론 성능 벤치마킹 및 프로파일링**

**설명:**
GenAI-Perf는 생성형 AI 추론 성능을 벤치마킹하고 프로파일링하기 위한 NVIDIA의 도구입니다.

**기능:**
- TTFT, ITL, 처리량 측정
- 동시 요청 테스트 지원
- 여러 엔드포인트 유형 (chat, completion)
- 분석을 위한 결과 내보내기

**설치:**
```bash
pip install genai-perf
```

**사용 예시:**
```bash
genai-perf \
  --endpoint-type chat \
  --service-kind openai \
  --url http://nim-inference:8000/v1 \
  --model meta/llama-3.1-70b-instruct \
  --concurrency 16 \
  --input-sequence-length 512 \
  --output-sequence-length 256 \
  --num-prompts 100 \
  --profile-export-file nim-benchmark.json

# 결과 분석
genai-perf analyze nim-benchmark.json
```

**보고되는 주요 메트릭:**
- Time to First Token (P50, P90, P99)
- Inter-Token Latency (P50, P90, P99)
- 요청 처리량
- 토큰 처리량
- 벤치마크 중 GPU 활용률

</details>

### 14. 여러 파드에 걸친 텐서 병렬화를 사용하는 분산 vLLM 배포에 가장 적합한 Kubernetes 리소스 유형은 무엇인가요?

A) Deployment
B) StatefulSet
C) DaemonSet
D) ReplicaSet

<details>
<summary>정답 보기</summary>

**정답: B) StatefulSet**

**설명:**
StatefulSet은 다음이 필요한 분산 vLLM 배포에 적합한 리소스입니다:

1. **안정적인 네트워크 ID**: 각 파드가 예측 가능한 호스트명(vllm-0, vllm-1 등)을 얻음
2. **순차적 배포**: 파드가 순서대로 생성되며, 마스터/워커 조정에 중요
3. **안정적인 스토리지**: 각 파드가 자체 영구 볼륨을 가질 수 있음
4. **헤드리스 서비스**: NCCL을 위한 직접적인 파드 간 통신

**StatefulSet 구성:**
```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: vllm-distributed
spec:
  serviceName: "vllm-distributed"
  replicas: 2
  selector:
    matchLabels:
      app: vllm-distributed
  template:
    metadata:
      labels:
        app: vllm-distributed
    spec:
      containers:
      - name: vllm
        image: vllm/vllm-openai:latest
        env:
        - name: MASTER_ADDR
          value: "vllm-distributed-0.vllm-distributed"
        - name: MASTER_PORT
          value: "29500"
        ports:
        - containerPort: 8000
        - containerPort: 29500  # NCCL 통신
---
apiVersion: v1
kind: Service
metadata:
  name: vllm-distributed
spec:
  clusterIP: None  # 헤드리스 서비스
  selector:
    app: vllm-distributed
```

**Deployment 대신 StatefulSet을 사용하는 이유:**
- Deployment는 안정적인 호스트명을 보장하지 않음
- NCCL은 예측 가능한 주소 지정이 필요
- 마스터 선출에 일관된 파드 ID 필요

</details>

### 15. 컨테이너에 표시되는 Neuron 코어 수를 제어하는 환경 변수는 무엇인가요?

A) CUDA_VISIBLE_DEVICES
B) NEURON_RT_VISIBLE_CORES
C) AWS_NEURON_CORES
D) NEURON_DEVICE_COUNT

<details>
<summary>정답 보기</summary>

**정답: B) NEURON_RT_VISIBLE_CORES**

**설명:**
`NEURON_RT_VISIBLE_CORES`는 컨테이너 내의 Neuron 런타임에 어떤 Neuron 코어가 표시되는지를 제어합니다.

**주요 Neuron 환경 변수:**

1. **NEURON_RT_VISIBLE_CORES**:
   - 사용할 코어 지정
   - 형식: "0,1" 또는 "0-3"
   ```yaml
   env:
   - name: NEURON_RT_VISIBLE_CORES
     value: "0,1"
   ```

2. **NEURON_RT_NUM_CORES**:
   - 사용할 총 코어 수
   ```yaml
   env:
   - name: NEURON_RT_NUM_CORES
     value: "2"
   ```

3. **NEURON_CC_FLAGS**:
   - 모델 컴파일을 위한 컴파일러 플래그
   ```yaml
   env:
   - name: NEURON_CC_FLAGS
     value: "--model-type transformer"
   ```

**전체 예시:**
```yaml
containers:
- name: vllm-neuron
  image: public.ecr.aws/neuron/pytorch-inference-neuronx:latest
  env:
  - name: NEURON_RT_NUM_CORES
    value: "2"
  - name: NEURON_RT_VISIBLE_CORES
    value: "0,1"
  - name: NEURON_CC_FLAGS
    value: "--model-type transformer"
  resources:
    limits:
      aws.amazon.com/neuron: 2
```

참고: `CUDA_VISIBLE_DEVICES`는 Neuron이 아닌 NVIDIA GPU용입니다.

</details>
