# EKS에서의 AI/ML 모범 사례

> **마지막 업데이트**: 2026년 9월 12일
> **기준**: inference-perf0.6.1 / SOCI0.15.0 / Karpenter1.14.1 / External Secrets2.10.0

개선의 기준은 같은 workload에서 측정한 지연·성공률·처리량·비용과 복구 가능성입니다. 특정 GPU, snapshotter 또는 sharing 기능만으로 고정 절감률이나 성능 배수를 보장하지 않습니다.

![벤치마킹, 시작 최적화, 장치, network/storage, 관측성, 비용과 보안을 실제 측정·복구 기준으로 검증하는 영역.](../.gitbook/assets/ko-ai-ml-07-ai-ml-best-practices-0.png)

[인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-ai-ml-07-ai-ml-best-practices-0.html)

## LLM 추론 벤치마킹

![첫 출력 시간, token 간격, end-to-end 지연과 집계 throughput/goodput의 측정 구간을 구분하는 그림.](../.gitbook/assets/ko-ai-ml-07-ai-ml-best-practices-1.png)

[인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-ai-ml-07-ai-ml-best-practices-1.html)

| 지표 | 정의와 주의점 |
| --- | --- |
| TTFT | 요청 전송부터 첫 **비어 있지 않은 출력**을 받은 시간. 첫 HTTP/SSE frame이 반드시 token은 아님 |
| ITL | 출력 token/chunk 사이의 간격. 하나의 network chunk가 여러 token일 수 있음 |
| TPOT | 도구 정의에 따른 첫 token 이후 평균 시간. output token이1개 이하이면 정의되지 않음 |
| E2E | 요청부터 응답 완료까지. queue·network·후처리 경계도 기록 |
| Request throughput | 성공 완료 요청 수 / 명시한 측정 구간 |
| Token throughput | 해당 구간 output token 합계 / 시간. 개별 요청 TPS의 단순 평균과 다름 |
| Goodput | 성공과 지연 SLO 등을 만족한 요청의 처리율 |

동일한 token timestamp를 관측했다면 평균 ITL은 (마지막-첫 token 시간)/(token 수-1)입니다. streaming 없이 전체 응답만 받으면 실제 TTFT/ITL을 측정할 수 없습니다. tokenizer·빈 출력·한 token·실패·warm-up 제외 규칙을 명시합니다.500ms/50ms를 모든 workload의 보편적 SLO로 고정하지 않습니다.

### inference-perf와 GenAI-Perf

inference-perf는 Kubernetes SIGs/wg-serving의 benchmark 도구입니다. 검토한 PyPI package는0.6.1이고 Git tag의 pyproject에는0.5.0이 남아 있어 metadata 차이를 기록했습니다. 실제 CLI는 --config_file 또는 --server.type 같은 구조화 옵션을 사용하며 이전의 benchmark --endpoint --prompt-length 형식이 아닙니다.

아래는 model server를 호출하지 않는 **내부 mock** 구성입니다. 실제0.6.1 CLI에서 worker1개·요청3개가 성공하는 것을 확인했습니다. mock의 token 수는0이고 TTFT/TPOT는null이므로 실제 모델 성능 수치로 사용하지 않습니다.

```yaml
api:
  type: chat
  streaming: false
data:
  type: mock
load:
  type: concurrent
  stages:
    - concurrency_level: 1
      num_requests: 3
  num_workers: 1
  worker_max_concurrency: 1
  base_seed: 17
server:
  type: mock
  base_url: http://127.0.0.1:8000
report:
  request_lifecycle:
    summary: true
    per_stage: true
    per_request: true
storage:
  local_storage:
    path: ./benchmark-fixture-results
```

```bash
inference-perf --config_file benchmark-fixture.yaml
```

실제 endpoint로 전환할 때는 지원 server/API 유형·model alias·streaming·tokenizer와 인증을 먼저 확인합니다. config에는 secret header가 포함될 수 있고 도구가 병합 config를 로그로 출력하므로 credential 전달/마스킹도 검증해야 합니다. 결과 디렉터리·raw 요청/응답과 실패를 보관하고, 실제 데이터의 개인정보·사용 권한을 확인합니다.

constant/poisson rate는 초당 도착률이고 concurrent는 동시 처리 수이므로 같은 값으로 비교하지 않습니다. 단일 요청 기준선→부하 증가→burst/실제 분포를 제한된 범위에서 검사합니다. 포화 곡선만으로 CPU/GPU/메모리 병목이 입증되는 것은 아니며 profiler·queue·network·client capacity를 함께 봅니다.

GenAI-Perf0.0.16은 [검토한 CLI](04-inference-frameworks.md)의 profile/endpoint-type/service-kind와 token 분포 옵션을 사용합니다. --backend vllm 같은 임의 조합을 그대로 쓰지 않습니다. GPU 지표는 별도 collector가 필요하며 load generator 자체가 CPU/network 병목이 되지 않는지도 검사하세요. Kubernetes benchmark Job에는 검증한 image·config key·PVC·실행 한도·retry로 발생하는 중복 부하를 명시해야 합니다.

## 컨테이너 시작 최적화

![Pod 배치, image fetch/unpack, container 시작, 모델 로딩과 readiness를 따로 측정하는 sequence.](../.gitbook/assets/ko-ai-ml-07-ai-ml-best-practices-2.png)

[인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-ai-ml-07-ai-ml-best-practices-2.html)

이미지 pull, 압축 해제, 모델 다운로드·로드와 readiness를 분리해 측정합니다. 과거의 “항상5~15분”, “통합80~95% 절감” 표는 측정 근거가 없어 제거했습니다.45GB/1Gbps≈360초는 압축 크기·프로토콜·disk·동시성 overhead를 제외한 단순 전송 산식이지 실제 pull 결과가 아닙니다.

모델을 이미지 밖에 두면 image 변경·pull이 작아질 수 있지만 startup download와 cache 관리 비용이 생깁니다. 일부 환경에서는 사전 준비한 image가 적합할 수도 있으므로 언제나 분리가 정답은 아닙니다. 초기화 command는 실패를 전파하고 checksum/revision/완료 상태를 검증해야 합니다. S3 sync가 실패해도 마지막 echo가 성공 상태를 반환하는 예제는 제거했습니다.

멀티 stage build에서는 Python interpreter/ABI와 CUDA/runtime library를 일치시키고 실행 파일·shared library도 포함해야 합니다. Ubuntu22.04에서 python3.11과 pip3가 같은 interpreter라고 가정하거나 site-packages만 복사하면 안 됩니다. 선택한 distribution의 공식 패키지·wheel을 사용하고 image 안에서 import/entrypoint를 실제 검사하세요. rootfs는 가능한 읽기 전용으로 하고 필요한 cache/tmp/model 경로만 별도 mount합니다.

### SOCI0.15

SOCI는 lazy image loading을 지원하지만 app이 시작 직후 모든 weights/library를 읽으면 이점이 제한될 수 있습니다. index가 있다는 것만으로 CRI가 SOCI snapshotter를 사용하는 것은 아닙니다. 검증한 containerd/CRI 통합·image/index digest·registry를 준비해야 합니다. 임의 privileged DaemonSet으로 host containerd socket을 넘기는 예제는 제거했습니다.

0.15의 create/push는 image reference를 위치 인자로 사용합니다. --ref 옵션이 아닙니다. 현재 getting-started는 convert로 SOCI-enabled image를 만드는 경로를 설명하며, standalone mode는 containerd나 sudo 없이 로컬 OCI layout을 처리합니다.

```bash
soci convert --standalone --format oci-dir input-oci-layout output-soci-layout
```

입력은 OCI image layout이며 일반 docker save tar와 다릅니다. 기본 min-layer-size보다 모든 layer가 작으면 변환이 실패할 수 있습니다. 검토에서는 합성 단일 layer와 명시적 min-layer-size=0으로 실제 변환해8개 blob의 digest를 확인했습니다. image 실행이나 시작 시간 benchmark는 수행하지 않았습니다. registry에 push할 때는 변환된 image/index를 함께 보존해야 합니다.

### Bottlerocket bootstrap

1.64의 `bootstrap-containers.<name>.user-data`는 **base64 데이터**이며 bootstrap container가 파일을 읽어 처리해야 합니다. plain shell을 설정에 넣는다고 자동 실행되지 않습니다. source image는 실제로 존재하고 host image store/namespace를 올바르게 다루는 검증한 구현이어야 합니다. 정적 images-prefetched=true label은 성공 증거가 아닙니다.

mode=once는 실행 후 off로 바뀌며 essential=true인 container가 실패하면 boot가 중단됩니다. false는 실패를 허용하므로 readiness 요구에 맞게 선택합니다. allowed-unsafe-sysctls는 privileged container 허용 설정이 아닙니다. prefetch 때문에 node 준비가 더 느려지는 시간도 포함해 평가하세요.

## GPU·Neuron과 저장소 선택

parameter 수×정밀도 byte는 가중치 하한일 뿐입니다. GQA/MQA·KV cache·activation·workspace·통신 buffer와 fragmentation, sharding 제약을 포함해야 합니다.13B FP16 weight≈26GB는24GB GPU에 들어가지 않고70B FP16≈140GB는4×24GB의 합보다 큽니다. CPU가 많은 g5 variant도 GPU가 같다면 VRAM은 늘지 않습니다.

p4d.24xlarge는8×40GB, p4de는8×80GB A100을 구분합니다. g5g는 Arm/T4G이므로 amd64 image나 kernel 호환을 가정하지 않습니다. Inf2.48xlarge의192vCPU/768GiB host RAM,12chip/24NeuronCore/384GiB HBM은 [검토한 표](04-inference-frameworks.md)를 참고하세요. P5라는 family 이름만으로 모든 크기의 GPU 수를 고정하지 않습니다. 최신 세대·region availability·quota·가격은 실제 선택 시 확인합니다.

LoRA는 trainable adapter 상태를 줄이지만 base weights·activation이 남으며 QLoRA와 다릅니다. “LoRA면 대부분의 모델이24GB에 들어감” 같은 선택 함수를 사용하지 않습니다. 실제 peak memory·latency·throughput과 재시작을 측정해야 합니다.

저장소도 dataset10TB 같은 하나의 경계로 선택하지 않습니다. 접근 pattern·동시성·metadata·지연·mount semantics·durability·비용을 비교합니다. 현재 일반 gp3 문서는 기본3000IOPS/125MiB/s, 최대80000IOPS/2000MiB/s를 설명하며 volume 크기/IOPS/instance 제약이 있습니다. Outposts 한도는 별도입니다. 예전16000IOPS/1GB/s를 모든 gp3의 현재 한도로 쓰지 않습니다.

EFS Elastic throughput·FSx filesystem 유형과 CSI·S3 association·Mountpoint POSIX 제한은 [인프라 가이드](06-ai-infrastructure.md)를 사용하세요. S3는 무한 throughput/고정 지연이 아니며 EFS가 항상 FSx보다 느리지 않습니다. instance store와 tmpfs는 내구성 없는 저장소입니다. 일반 GPU KV cache는 GPU memory에 있으며 SSD/tmpfs를 자동 기본 cache로 사용하는 것이 아닙니다.

### 모델 cache 검증

config.json 하나가 존재한다고 weights 다운로드가 완료된 것은 아닙니다. 신뢰할 수 있는 release manifest와 model revision으로 **모든 파일**을 확인한 뒤 읽기 전용 경로로 공개합니다. 여러 downloader가 같은 경로에 쓰는 race와 부분 파일을 방지해야 합니다.

다음 로컬 검사 함수는 다운로드·삭제를 하지 않습니다. 정상 파일, 잘못된 revision, 부분/누락 weights, 경로 이동과 외부 symlink를 검증했습니다. manifest의 신뢰와 검증 이후 불변성은 별도 조건입니다.

```python
from pathlib import Path
import hashlib
import re


def verify_model_cache(root, manifest, expected_revision):
    """Verify files against a separately trusted release manifest; no downloads/deletion."""
    root = Path(root).resolve(strict=True)
    if manifest.get("revision") != expected_revision:
        raise ValueError("Model revision mismatch")
    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError("Empty or invalid release manifest")
    for relative, expected_hash in files.items():
        name = Path(relative)
        if name.is_absolute() or ".." in name.parts or not name.parts:
            raise ValueError("Unsafe manifest path")
        if not isinstance(expected_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
            raise ValueError("Invalid SHA256")
        target = (root / name).resolve(strict=True)
        if not target.is_relative_to(root) or not target.is_file():
            raise ValueError("File escapes the cache or is not a regular file")
        digest = hashlib.sha256()
        with target.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
        if digest.hexdigest() != expected_hash:
            raise ValueError("Incomplete or corrupt model file: " + relative)
    return root
```

체크포인트는 [훈련·복구 예제](05-model-training.md)처럼 optimizer/RNG/data cursor와 shard를 포함해야 합니다. 전송 성공·checksum·완료 manifest를 확인하기 전 이전 정상본을 삭제하지 않습니다. ls의 디렉터리 내용과 checkpoint 경로를 혼동하거나 xargs rm -rf로 지우는 예제, readOnly mount에서 삭제하려는 sidecar는 제거했습니다. 첫30분 동안 전송하지 않는 loop나 종료 시 flush가 없는 동기화는 허용 손실을 늘립니다.

## 네트워킹과 scheduling

EFA는 선택한 workload의 통신 성능을 높이는 경로이지 모든 DDP 실행의 필수 조건은 아닙니다. 지원 interface·같은 AZ·driver/libfabric/aws-ofi-nccl·Pod 할당·SG와 실제 transport를 확인합니다. instance store RAID0과 subnet tag만으로 활성화되지 않습니다. NCCL_TIMEOUT 같은 미확인 변수나 과거 Ring/Simple/IB_DISABLE 설정을 복사하지 않습니다. torchrun --nnodes는 node 수이며 전체 process WORLD_SIZE가 아닙니다.

Karpenter1.14.1의 실제 placementGroupSelector를 사용합니다. aws:ec2:placement-group tag는 placement API가 아니며 aws: prefix를 사용자 tag로 생성하는 방식도 잘못입니다. 아래는 **스키마 예제**로, AMI/subnet/SG/role와 존재하는 placement group을 승인된 값으로 교체해야 합니다. 이 예제의 amiFamily는 AL2023이므로 교체한 AMI도 검증한 EKS AL2023 이미지여야 합니다. 다른 OS의 AMI ID를 넣으면 안 됩니다. EFA networkInterfaces 설정까지 완성된 구성은 아닙니다.

```yaml
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: prepared-gpu-class
spec:
  role: REPLACE_WITH_APPROVED_NODE_ROLE
  amiSelectorTerms:
  - id: ami-0123456789abcdef0
  subnetSelectorTerms:
  - id: subnet-0123456789abcdef0
  securityGroupSelectorTerms:
  - id: sg-0123456789abcdef0
  placementGroupSelector:
    name: prepared-training-placement-group
  amiFamily: AL2023
```

### 중단 예산과 Spot

다음 예제의 budget은 월~금 **UTC09:00~17:00**에 적용됩니다. 이전0 9-17 * * 1-5는09~17시에 매시간8시간짜리 window를 시작하므로 다음날01시까지 이어집니다. budget은 여러 개가 활성화되면 더 엄격한 제한을 적용하며 사용자 로컬 시간대를 자동 반영하지 않습니다.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: reviewed-gpu-pool
spec:
  template:
    spec:
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: prepared-gpu-class
      requirements:
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
        - spot
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 5m
    budgets:
    - nodes: '0'
      schedule: 0 9 * * 1-5
      duration: 8h
    - nodes: 30%
```

budgets.nodes=0은 자발적 disruption 제한이며 Spot interruption·노드 장애·forceful expiration을 막지 않습니다. Spot만 허용하면 선호가 아니라 필수이며 on-demand fallback이 생기지 않습니다. topology spread의 ScheduleAnyway는 soft 조건이고 실제 replica·capacity·AZ 분포를 확인해야 합니다.

terminationGracePeriodSeconds=120은 EC2가120초를 반드시 보장한다는 뜻이 아닙니다. gateway readiness/drain, endpoint 전파, SIGTERM, 진행 중 streaming·retry·중복 처리를 실제 종료로 검증하세요. vLLM에 임의 /drain API가 있다고 가정하지 않습니다. cache/session/TP group은 추론이더라도 상태와 재시작 비용을 가집니다.

## 관측성과 비용

[현재 vLLM 지표](02-vllm-deployment.md)와 [DCGM 규칙](06-ai-infrastructure.md)을 사용합니다. KV cache는 vllm:kv_cache_usage_perc이며 예전 gpu_cache_usage_perc와 다릅니다. cache가 차면 queue/preemption 등 backend 동작을 관찰해야 하며 자동 요청 거부로 단정하지 않습니다. prefix hit ratio는 해당 버전의 hit/query counter와 분모0 처리를 확인합니다.

DCGM FB_USED/FREE는MiB, XID_ERRORS는마지막 코드 gauge입니다. 없는 FB_TOTAL이나 gauge의 increase()를 기준으로 경보를 만들지 않습니다. 온도만으로 thermal throttling을 확정하지 말고 clocks·power·throttle reason·workload를 대조하세요. Prometheus series label과 histogram 집계 경계를 맞추고, avg_over_time의 expression에는 적합한 subquery 문법이 필요합니다.

VPA Off는 CPU/memory 추천을 제공할 뿐 GPU instance 자동 선택기가 아닙니다. 첫 series 하나만 뽑거나0~1 ratio를50/90과 비교하는 rightsizing script는 제거했습니다. 모든 workload의 peak·queue·SLO와 노드 제거 후 복구를 확인합니다.

절감률은 region·OS·purchase term·시간당 사용·유휴·실패·스토리지·전송·운영 비용을 포함한 실제 비교로 기록합니다. Spot/Savings Plans/RI는 할인 조건·capacity 보장 범위가 다르며 고정60~90% 표나 여러 최적화 절감률의 단순 합을 사용하지 않습니다. commit 기반 할인 구매는 계측한 baseline과 사용 변동을 바탕으로 별도 결정합니다.

## 모델 접근과 secret 관리

S3 ListBucket과 GetObject는 bucket/object ARN과 지원 condition key를 각각 사용합니다. 일반 목적 버킷도 ABAC를 명시적으로 활성화하면 aws:ResourceTag/Environment 같은 버킷 태그 조건으로 접근을 제어할 수 있습니다. 기본값은 비활성화이므로 기존 예제의 태그 조건만 복사하지 말고 버킷의 ABAC 상태, 태그 변경 권한, identity/bucket policy와 action/resource 조합을 검토하세요. 활성화 자체가 필요한 Allow를 생성하거나 다른 Deny를 무효화하지는 않습니다. IAM trust의 ServiceAccount namespace/name, SDK credential chain과 실제 요청 identity를 확인합니다. vLLM이 모든 S3 model URI를 자동 다운로드하는 것은 아닙니다.

ESO2.10.0의 확인한 CRD는 **v1이 served**, v1beta1은 served=false입니다. 다음 예시는 미리 승인된 같은 namespace SecretStore를 참조합니다. remote key·권한·rotation과 target lifecycle은 별도로 준비해야 합니다.

```yaml
apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: model-download-token
  namespace: ai-ml
spec:
  refreshPolicy: Periodic
  refreshInterval: 1h
  secretStoreRef:
    name: approved-secrets-manager
    kind: SecretStore
  target:
    name: model-download-credential
    creationPolicy: Owner
  data:
  - secretKey: token
    remoteRef:
      key: approved/model-download
      property: token
```

Kubernetes Secret은 volume으로 mount하고 app이 필요한 시점에 파일을 다시 읽도록 구성합니다. subPath mount는 자동 갱신을 받지 않으며 환경 변수·시작 때 한 번 읽은 값도 자동 reload되지 않습니다. ESO refresh는 upstream credential을 새로 발급하는 rotation 그 자체가 아닙니다. provider/Secret 접근·app reload를 각각 검증하세요.

CloudTrail의 Secrets Manager API 기록은 app의 모든 로컬 Secret 파일 읽기까지 기록하지 않습니다. SecretKeyRef 환경 값은 kubectl describe에서 평문 값이 보인다고 일반화하면 안 되지만 환경 전달은 프로세스/디버깅 경로의 노출 위험이 있어 파일 credential 정책과 다릅니다. 민감 값은 예제·로그에 출력하지 않습니다.

NetworkPolicy는 실제 CNI가 적용해야 하며 namespaceSelector와podSelector의 AND/OR, 기본 namespace name label과 DNS TCP/UDP를 확인합니다.10.0.0.0/8을 health check용으로 여는 규칙이나 인터넷443허용을 S3전용이라고 부르는 규칙은 제거했습니다. 모델이 사전 준비됐으면 runtime egress를 필요한 내부 경로로 제한하고 gateway에서 API/관리 endpoint를 구분합니다.

감사 로그는 user/workload identity·model revision·행위·결과·request ID를 기록하고 prompt/secret는 필요에 따라 마스킹합니다. containerd CRI log를 Docker parser로 읽거나 request라는 문자열만 남기는 필터는 감사 누락을 만들 수 있습니다. Fluent Bit config만 만들지 말고 실제 collector·parser·IAM·buffer·보존·전송 실패를 검증하세요.

## 검증 범위

본문·퀴즈의 모든 원문과87개 고유 code block을 검토했습니다. 실제 inference-perf mock3요청, SOCI local OCI변환, cache검증6사례, Karpenter/ESO3스키마와 cron 산식을 확인했습니다. GPU·실제 모델 benchmark·container startup·SOCI host 설치·클라우드 자원·secret provider를 실행하지 않았습니다.

## 참고 자료

- [inference-perf0.6.1](https://github.com/kubernetes-sigs/inference-perf/tree/v0.6.1)
- [SOCI0.15 CLI](https://github.com/awslabs/soci-snapshotter/blob/v0.15.0/docs/cli-usage.md)
- [Bottlerocket1.64 bootstrap settings](https://bottlerocket.dev/en/os/1.64.x/api/settings/bootstrap-containers/)
- [Karpenter1.14.1 CRDs](https://github.com/aws/karpenter-provider-aws/tree/v1.14.1/pkg/apis/crds)
- [Karpenter disruption](https://karpenter.sh/docs/concepts/disruption/)
- [ESO2.10 ExternalSecret CRD](https://github.com/external-secrets/external-secrets/blob/helm-chart-2.10.0/config/crds/bases/external-secrets.io_externalsecrets.yaml)
- [Kubernetes Secret updates](https://kubernetes.io/docs/concepts/configuration/secret/)
- [S3 general-purpose bucket ABAC enablement](https://docs.aws.amazon.com/AmazonS3/latest/userguide/buckets-tagging-enable-abac.html)
- [EBS gp3 performance](https://docs.aws.amazon.com/ebs/latest/userguide/general-purpose.html)

## 퀴즈

[AI/ML 모범 사례 퀴즈](../quizzes/ai-ml/07-ai-ml-best-practices-quiz.md)
