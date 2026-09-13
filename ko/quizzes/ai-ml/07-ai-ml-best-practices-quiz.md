# AI/ML 모범 사례 퀴즈

측정, 복구와 현재 API를 확인하는 15문항입니다.

## 1. TTFT는 무엇을 측정하며 언제 측정할 수 없나요?

<details>
<summary>정답 및 설명</summary>

요청부터 첫 번째 비어 있지 않은 출력 수신까지의 시간입니다. 첫 HTTP frame과 token은 다를 수 있고, nonstreaming 응답으로 실제 TTFT/ITL을 측정할 수는 없습니다. tokenizer, 실패, warm-up의 측정 경계를 명시합니다.
</details>

## 2. 시작 최적화를 조합하면 항상 80–95% 빨라지나요?

<details>
<summary>정답 및 설명</summary>

아닙니다. image fetch/unpack, model download/load, readiness와 node 준비 시간을 각각 측정해야 합니다. prefetch와 lazy loading의 비용, cache 상태, 전체 weights 읽기의 영향을 확인하며 고정 절감률을 사용하지 않습니다.
</details>

## 3. 대규모 분산 훈련용 GPU는 어떻게 선택하나요?

<details>
<summary>정답 및 설명</summary>

정확한 instance size의 device memory/count, CPU/RAM, network와 모델 상태·activation·통신·가격·할당량을 확인합니다. family 이름만으로 모든 크기의 GPU 수를 고정하거나 항상 가장 적합하다고 단정하지 않습니다.
</details>

## 4. EFA와 placement group은 항상 필수인가요?

<details>
<summary>정답 및 설명</summary>

EFA는 적합한 workload의 고성능 통신 경로이며 모든 DDP 실행의 필수 조건은 아닙니다. EFA 통신은 같은 AZ가 필요하고, cluster placement group은 성능을 위한 권장 조건입니다. driver, plugin, SG와 interface를 검증합니다.
</details>

## 5. dataset이 10TB를 넘으면 무조건 FSx를 선택하나요?

<details>
<summary>정답 및 설명</summary>

크기 하나로 정하지 않습니다. I/O 패턴, 동시성, metadata, latency, durability, mount semantics와 비용을 비교합니다. EFS·FSx·S3·instance store와 현재 gp3 한도도 구분합니다.
</details>

## 6. GPU 온도만으로 throttling이나 고장을 확정할 수 있나요?

<details>
<summary>정답 및 설명</summary>

아닙니다. 장치별 제한, clock, power, throttle reason과 workload를 확인합니다. DCGM FB_USED는 MiB이고 XID_ERRORS는 마지막 코드 gauge이며, 모든 XID가 하드웨어 고장을 뜻하지는 않습니다.
</details>

## 7. Spot 추론에서 120초 grace 기간과 /drain 호출이면 충분한가요?

<details>
<summary>정답 및 설명</summary>

EC2가 항상 120초를 보장하지 않으며 vLLM에 임의 /drain API가 있다고 가정할 수 없습니다. gateway readiness, SIGTERM, stream, retry, 중복 처리와 cache 재로딩을 실제로 검증해야 합니다.
</details>

## 8. 평균 ITL은 어떻게 계산하나요?

<details>
<summary>정답 및 설명</summary>

실제 token timestamp가 있고 token이 2개 이상이면 (last-first)/(tokens-1)입니다. chunk당 token 수가 다르거나 빈 응답·한 token 응답이면 측정 한계와 분모 처리가 필요합니다. 도구의 TPOT 정의와도 구분합니다.
</details>

## 9. 포화 시험은 무엇을 보여주나요?

<details>
<summary>정답 및 설명</summary>

부하에 따른 throughput, latency, error와 goodput 변화입니다. 그것만으로 CPU/GPU/메모리 병목을 확정하지 않습니다. constant/poisson rate와 concurrency를 구분하고 client, profiler와 queue도 확인합니다.
</details>

## 10. SOCI 0.15 standalone은 어떤 입력을 사용하나요?

<details>
<summary>정답 및 설명</summary>

로컬 OCI image layout 디렉터리나 archive입니다. 일반 docker-save tar와 다릅니다. convert --standalone은 containerd 없이 변환하지만 실제 lazy-start 효과는 runtime·registry 구성과 workload에서 검증합니다.
</details>

## 11. UTC 09~17시 업무 시간 budget은 어떻게 설정하나요?

<details>
<summary>정답 및 설명</summary>

0 9 * * 1-5와 duration 8h를 사용합니다. 0 9-17 * * 1-5는 매시간 시작해 다음날 01시까지 이어집니다. budget은 자발적 disruption의 제한이며 Spot 회수, 장애와 forceful expiration을 막지 않습니다.
</details>

## 12. ESO refresh가 credential 발급·app reload·모든 읽기 감사를 자동 수행하나요?

<details>
<summary>정답 및 설명</summary>

아닙니다. provider rotation, Secret 동기화와 app의 파일 재읽기를 구분합니다. subPath/env 값은 자동 갱신되지 않고 CloudTrail은 모든 local file read를 기록하지 않습니다. ESO 2.10은 v1을 제공하며 v1beta1은 제공하지 않습니다.
</details>

## 13. 30B FP16 모델에 필요한 GPU memory를 어떻게 계산하나요?

<details>
<summary>정답 및 설명</summary>

weights만 약 60GB이며 KV, activation, workspace와 통신 여유를 추가합니다. 4×24GB는 총 96GB지만 실제 sharding, peak memory와 throughput 검증이 필요합니다. 13B FP16은 24GB보다 크고 70B FP16은 96GB보다 큽니다.
</details>

## 14. 현재 vLLM KV cache 지표가 높으면 항상 요청을 거부하나요?

<details>
<summary>정답 및 설명</summary>

현재 이름은 vllm:kv_cache_usage_perc입니다. 높은 사용률은 queue, preemption과 메모리 상태를 함께 해석해야 하며 즉시 거부를 뜻하지 않습니다. 이전 gpu_cache_usage_perc와 미확인 prefix hit-rate 이름을 복사하지 않습니다.
</details>

## 15. Karpenter에서 placement group은 tag로 지정하나요?

<details>
<summary>정답 및 설명</summary>

1.14.1은 EC2NodeClass.spec.placementGroupSelector의 name/id를 사용합니다. aws:ec2:placement-group tag는 placement API가 아닙니다. 같은 AZ, capacity와 실제 network 조건을 검증하며 단일 AZ의 복구 위험도 평가합니다.
</details>

[본문으로 돌아가기](../../ai-ml/07-ai-ml-best-practices.md)
