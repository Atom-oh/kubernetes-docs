# vLLM 배포 퀴즈

기준: vLLM 0.29.0. 과거 L4 결과는 별도로 구분합니다.

## 퀴즈 문제

### 1. vLLM의 주요 역할에 대한 올바른 설명은 무엇인가요?

- A. Vector Language Model이라는 모델 자체
- B. 지원되는 생성형·멀티모달 등의 모델을 실행하는 추론 엔진
- C. 데이터베이스 전용 optimizer
- D. 모든 모델의 정확도를 자동 향상시키는 학습 도구

<details>
<summary>정답 및 설명</summary>

**정답: B. 지원되는 생성형·멀티모달 등의 모델을 실행하는 추론 엔진**

vLLM은 모델 이름이 아닌 엔진입니다. PagedAttention과 batching의 이점은 workload에 따라 달라지며 고정된 처리량 배수나 대기 없는 실행을 보장하지 않습니다.
</details>

### 2. GPU 메모리 요구량을 평가하는 올바른 방법은 무엇인가요?

- A. 70B는 정밀도와 관계없이 80GB면 충분
- B. 가중치 바이트에 KV cache·activation·workspace·통신 버퍼를 더하고 모델 구조와 병렬화·정밀도를 반영
- C. GPU당 CPU4개만 있으면 모든 모델 실행
- D. host RAM만 늘리면 GPU 요구량이 사라짐

<details>
<summary>정답 및 설명</summary>

**정답: B. 가중치 바이트에 KV cache·activation·workspace·통신 버퍼를 더하고 모델 구조와 병렬화·정밀도를 반영**

70B FP16/BF16 가중치만 약 140GB입니다. GQA/MQA는 KV head 수를 사용해야 하며 MHA hidden-size 식을 그대로 적용하면 안 됩니다. 현재 NVIDIA 최소 capability 7.5와 선택 kernel의 추가 조건도 확인하세요.
</details>

### 3. vLLM 모델 스토리지에 대한 올바른 설명은 무엇인가요?

- A. 항상 FSx for Lustre가 최적
- B. snapshot_download는 S3 다운로드
- C. 로드 시간·동시성·비용·보존 조건으로 선택하고 model revision과 파일 무결성을 기록
- D. emptyDir는 컨테이너가 재시작할 때마다 무조건 삭제

<details>
<summary>정답 및 설명</summary>

**정답: C. 로드 시간·동시성·비용·보존 조건으로 선택하고 model revision과 파일 무결성을 기록**

emptyDir는 컨테이너 재시작에는 남을 수 있지만 Pod 재생성에는 보존되지 않습니다. FSx 정적·동적 방식, EBS 접근 모드, 각 worker의 동일 model path를 구분하세요. Hugging Face 다운로드와 S3 전송은 다릅니다.
</details>

### 4. TP·PP·독립 replica의 차이를 올바르게 설명한 것은 무엇인가요?

- A. StatefulSet replica만 늘리면 TP가 자동 재구성
- B. TP는 레이어 내부 텐서를, PP는 레이어 구간을 분할하며 독립 replica는 모델을 각각 적재
- C. TP는 항상 단일 요청 지연을 줄임
- D. 모든 멀티노드에서 --rank를 사용

<details>
<summary>정답 및 설명</summary>

**정답: B. TP는 레이어 내부 텐서를, PP는 레이어 구간을 분할하며 독립 replica는 모델을 각각 적재**

0.29.0 multiprocessing은 --nnodes/--node-rank와 worker --headless 등을 사용합니다. Ray는 실제 cluster가 필요합니다. 동일 이미지·모델, 네트워크, rendezvous와 GPU 용량을 맞춰야 하며 프로세스 수와 Kubernetes replica 수를 혼동하지 마세요.
</details>

### 5. 가용성 구성에 대한 올바른 설명은 무엇인가요?

- A. PDB가 모든 노드 장애에서 최소 replica 보장
- B. maxUnavailable0만으로 무중단 보장
- C. 독립 replica·readiness·startup 시간·용량·drain·stream 중단을 함께 검증
- D. 같은 TP group을 AZ마다 나누면 항상 성능 향상

<details>
<summary>정답 및 설명</summary>

**정답: C. 독립 replica·readiness·startup 시간·용량·drain·stream 중단을 함께 검증**

PDB는 일부 voluntary eviction을 제한합니다. 예제 Recreate는 여분 GPU 요구를 줄이는 대신 업데이트 중 중단됩니다. 모델 로딩 중 liveness 재시작을 피하도록 startupProbe를 구성하고 실제 시작 시간을 검증해야 합니다.
</details>

### 6. 연속 batching과 cache 옵션의 올바른 설명은 무엇인가요?

- A. 모든 요청은 도착 즉시 실행되고 queue가 없음
- B. scheduler가 단계별로 작업을 조정하며 queue·token budget·cache 여유에 따라 대기가 발생할 수 있음
- C. prefix caching은 응답 전체를 항상 재사용
- D. --swap-space가0.29의 기본 메모리 확장 방법

<details>
<summary>정답 및 설명</summary>

**정답: B. scheduler가 단계별로 작업을 조정하며 queue·token budget·cache 여유에 따라 대기가 발생할 수 있음**

Prefix cache는 지원되는 prefix의 KV 재사용입니다. chunked prefill과 max-num-seqs, token budget, max-model-len은 다릅니다. 0.29 CacheConfig의 gpu_memory_utilization 기본은 0.92이며 예제는 0.80을 명시합니다. --swap-space는 현재 CLI에 없습니다.
</details>

### 7. 현재 메트릭 구성은 무엇을 기준으로 해야 하나요?

- A. 별도 8001포트와 --enable-metrics=true
- B. API와 같은 8000포트의 /metrics, 실제 vllm: 이름·label·단위
- C. KV cache 비율을 GPU 전체 사용 바이트로 해석
- D. 요청이 없는 상태를 항상 throughput 장애로 알림

<details>
<summary>정답 및 설명</summary>

**정답: B. API와 같은 8000포트의 /metrics, 실제 vllm: 이름·label·단위**

생성 token counter는 vllm:generation_tokens_total, 종단 histogram은 vllm:e2e_request_latency_seconds_bucket 등입니다. KV cache usage는1이100%인 비율입니다. model별 집계와 gateway 오류·취소, TTFT·전체 응답 시간을 구분하세요.
</details>

### 8. 멀티노드 네트워크의 올바른 운영 경계는 무엇인가요?

- A. API key가 모든 내부 통신을 암호화
- B. 임의 GID·mlx5 값을 복사하면 EFA 구성 완료
- C. 지원 장치·driver·OFI NCCL/libfabric와 private 통신 경로를 검증
- D. 단일 노드 NCCL 테스트가 멀티노드 EFA 성능 증명

<details>
<summary>정답 및 설명</summary>

**정답: C. 지원 장치·driver·OFI NCCL/libfabric와 private 통신 경로를 검증**

분산 통신은 기본적으로 신뢰 네트워크가 필요합니다. API 인증과 내부 PyTorch/Ray/KV 전송 보안은 다릅니다. 일반 SR-IOV/InfiniBand 템플릿을 EKS에 그대로 적용하거나 임의 NCCL 변수를 만들어서는 안 됩니다.
</details>

### 9. 확장성과 요청 라우팅에 대한 올바른 설명은 무엇인가요?

- A. HTTP model header 라우팅이 JSON model 필드를 자동 파싱
- B. 세션 어피니티가 모든 KV cache를 자동 공유
- C. 실제 병목과 모델 topology를 기준으로 독립 replica·TP/PP·라우팅을 선택
- D. GPU가 있으면 CPU와 스토리지는 성능에 영향 없음

<details>
<summary>정답 및 설명</summary>

**정답: C. 실제 병목과 모델 topology를 기준으로 독립 replica·TP/PP·라우팅을 선택**

Prefix cache, 응답 cache, 모델 weight cache는 다릅니다. CPU tokenization과 네트워크·로드 시간이 병목일 수도 있습니다. HPA/KEDA와 NodePool은 별도 계층이며 메트릭·소유권·용량 조건을 검증해야 합니다.
</details>

### 10. 0.29.0 API key와 보안에 대한 올바른 설명은 무엇인가요?

- A. --api-key가 서버의 모든 endpoint 보호
- B. 접두사 기반 보호 외 endpoint와 운영 기능은 별도 gateway·권한·network 경계가 필요
- C. CORS가 사용자 인증을 대신
- D. 정규표현식 하나로 prompt injection과 PII 제거 보장

<details>
<summary>정답 및 설명</summary>

**정답: B. 접두사 기반 보호 외 endpoint와 운영 기능은 별도 gateway·권한·network 경계가 필요**

검토한 middleware는 /v1,/v2,/inference,/cohere 접두사를 보호하고 다른 경로나 OPTIONS는 건너뜁니다. 동적 LoRA는 별도 opt-in이며 trusted operator 경로가 필요합니다. Secret을 RequestResponse audit로 기록하거나 Pod annotation으로 control-plane audit를 켜는 예제는 잘못된 접근입니다.
</details>

### 11. 과거 L4 벤치마크의 5.65s→7.52s 결과를 어떻게 해석해야 하나요?

- A. 지연이 증가하지 않았다
- B. p50이 약 33.1% 증가했고 이 측정 범위에서 집계 처리량이 늘었다; 원시 로그 없는 과거 보고를 현재 버전 결과로 일반화하지 않는다
- C. memory-bound가 profiler로 증명되었다
- D. continuous batching은 prefill을 건너뛴다

<details>
<summary>정답 및 설명</summary>

**정답: B. p50이 약 33.1% 증가했고 이 측정 범위에서 집계 처리량이 늘었다; 원시 로그 없는 과거 보고를 현재 버전 결과로 일반화하지 않는다**

기록된 값은 0.6.4.post1의 n=1 과거 보고입니다. 이번 감사는 raw request/server logs를 찾지 못했고 재실행하지 않았습니다. 서버 interval average의 최댓값은 순간 peak가 아니며 roofline 계산은 병목에 대한 추정입니다.
</details>

---

[학습 자료로 돌아가기](../../ai-ml/02-vllm-deployment.md)
