# 추론 프레임워크 퀴즈

현재 API와 실행 경계를 확인하는15문항입니다.

## 1. NIM의 주요 이점과 배포 시 확인할 조건은 무엇인가요?

<details>
<summary>정답 및 설명</summary>

모델·장치별 컨테이너와 profile을 제공하지만 모든 NIM이 TensorRT-LLM인 것은 아닙니다. 컨테이너·모델 revision, 지원 장치·계약과 인증·cache·메트릭을 확인합니다.
</details>

## 2. Dynamo의 분리형 서빙이란 무엇인가요?

<details>
<summary>정답 및 설명</summary>

prefill과 decode를 별도 worker로 나누고 호환되는 KV transfer로 연결합니다. 모델·KV 형식·backend·장치·네트워크가 맞아야 하며 항상 더 빠르거나 저렴한 것은 아닙니다.
</details>

## 3. AIBrix 0.7.0에서 LoRA를 어떻게 선언하나요?

<details>
<summary>정답 및 설명</summary>

ModelAdapter의 baseModel, podSelector, artifactURL 등을 사용합니다. replicas 생략은 모든 matching Pod,1은 한 Pod이며 임의 숫자는 허용되지 않습니다. adapter 이름은 tenant 인증이 아닙니다.
</details>

## 4. Ray Serve를 Kubernetes에서 운영하는 controller와 확장 계층은 무엇인가요?

<details>
<summary>정답 및 설명</summary>

KubeRay가 Ray 리소스를 관리하고 Ray autoscaler는 worker, Serve autoscaler는 serving replica를 조정합니다. RayCluster에 일반 Deployment HPA를 그대로 적용하지 않습니다.
</details>

## 5. Inf2 선택 시 비용과 장치 수를 어떻게 평가하나요?

<details>
<summary>정답 및 설명</summary>

동일 모델·SLO·성공 처리량·가격 시점으로 측정합니다. 칩1개는 코어2개·HBM32GiB입니다. inf2.24xlarge는 칩6/코어12/HBM192GiB,48xlarge는12/24/384GiB이며 host RAM과 다릅니다.
</details>

## 6. TTFT, ITL과 end-to-end latency는 어떻게 다른가요?

<details>
<summary>정답 및 설명</summary>

TTFT는 첫 token까지, ITL은 이후 token 사이의 시간입니다. 균일한 간격의 근사는 TTFT+(출력token수-1)×ITL이며 네트워크·후처리 overhead는 별도입니다. workload별 SLO와 실제 단위를 사용합니다.
</details>

## 7. Dynamo의 KV-aware routing은 무엇을 고려하나요?

<details>
<summary>정답 및 설명</summary>

cache 지역성과 worker 부하를 고려합니다. 고정0.7/0.3 산식이나 decode worker만의 cache를 모든 구현의 기준으로 삼지 않습니다. 실제 backend와 선택 정책을 확인합니다.
</details>

## 8. Neuron device plugin을 설치하기 전에 무엇을 확인하나요?

<details>
<summary>정답 및 설명</summary>

공식 고정 Helm chart를 렌더링하고 driver, RBAC/hostPath, enabled component와 실제 DaemonSet을 확인합니다. neuron은 전체 장치, neuroncore는 코어이며 같은 단위가 아닙니다.
</details>

## 9. AIBrix의 autoscaler 설정은 어떤 구조인가요?

<details>
<summary>정답 및 설명</summary>

PodAutoscaler의 scaleTargetRef, metricsSources와 HPA/KPA/APA 전략을 사용합니다. controller와 실제 metrics source가 필요하며 ConfigMap 하나나 GPU resource request만으로 작동하지 않습니다.
</details>

## 10. NGC와 NIM profile의 역할 및 credential 경계는 무엇인가요?

<details>
<summary>정답 및 설명</summary>

지원 모델·이미지·profile을 확인하는 경로입니다. NIM_MODEL_PROFILE은 실제 profile ID/이름이어야 합니다. image pull과 runtime download 인증을 구분하며 NGC_API_KEY Secret 환경 전달은 파일 전용 정책을 충족하지 않습니다.
</details>

## 11. Dynamo의 여러 backend 지원은 자유로운 혼합을 뜻하나요?

<details>
<summary>정답 및 설명</summary>

아닙니다. vLLM/SGLang/TensorRT-LLM과 선택 장치·connector·모델·KV 형식의 조합을 검증해야 합니다. 같은 모델 이름만으로 prefill/decode 간 전송이 호환되지는 않습니다.
</details>

## 12. 모델 cache를 어떤 기준으로 선택하나요?

<details>
<summary>정답 및 설명</summary>

모델 크기·revision·재시작·동시 다운로드·권한·비용으로 local/EBS/EFS/FSx를 비교합니다. 하나의 RWO EBS PVC를 여러 노드에서 공유하지 않으며 image에 모델을 넣는 방식도 조건에 따라 가능합니다.
</details>

## 13. GenAI-Perf CLI와 측정 결과에서 주의할 점은 무엇인가요?

<details>
<summary>정답 및 설명</summary>

0.0.16은 profile과 synthetic-input-tokens-mean/output-tokens-mean을 사용합니다. analyze는 sweep에 따른 추가 부하를 실행할 수 있습니다. raw 결과와 실패·warm-up·tokenizer를 기록하며 GPU 활용률은 수집 설정이 필요합니다.
</details>

## 14. StatefulSet만으로 분산 vLLM이 완성되나요?

<details>
<summary>정답 및 설명</summary>

아닙니다. 안정된 이름은 도움이 되지만 rank·rendezvous·TP/PP·모델·통신을 별도로 구성합니다. 순차 readiness가 worker 간 상호 대기를 막는지도 확인합니다. 운영 방식에 따라 다른 controller도 사용할 수 있습니다.
</details>

## 15. NEURON_RT_VISIBLE_CORES와 Kubernetes resource 요청의 관계는 무엇인가요?

<details>
<summary>정답 및 설명</summary>

runtime의 사용할 코어를 선택하며 Kubernetes가 할당하지 않은 장치를 추가하지 않습니다. inf2.xlarge의 전체 장치는1개이므로 neuron:2 요청은 배치되지 않습니다. SDK2.32의 Inf2용 NxD와 Trn2/3용 베타 경로도 구분합니다.
</details>

[본문으로 돌아가기](../../ai-ml/04-inference-frameworks.md)
