# EKS Hybrid Nodes GPU 통합 퀴즈

> **관련 문서**: [GPU 통합](../../eks-hybrid-nodes/05-gpu-integration.md)
> **마지막 업데이트**: 2026년 9월 12일

### 1. MIG를 올바르게 설명한 것은?

A. 여러 물리 GPU를 하나로 합친다

B. 지원되는 하드웨어 compute·memory 인스턴스를 만들지만 호스트·드라이버·애플리케이션 SLO 고려는 남는다

C. 모든 tenant·장애에 완전 격리를 보장한다

D. 소프트웨어 time-slicing과 같다

<details>
<summary>정답 보기</summary>

**정답: B. 지원되는 하드웨어 compute·memory 인스턴스를 만들지만 호스트·드라이버·애플리케이션 SLO 고려는 남는다**

**설명:** MIG는 GPU 하드웨어 계층에서 메모리·장애·리소스 격리를 제공합니다. 지원 profile·한도는 GPU SKU·드라이버에 따라 다르며 공유 호스트의 완전한 보안이나 애플리케이션 지연 보장을 뜻하지 않습니다.

</details>

### 2. 일반적인 A10040GB 표에 해당하는 profile은?

A. 4g.40gb

B. 4g.20gb

C. 4g.80gb

D. 1g는 물리 GPU 전체 하나를 뜻한다

<details>
<summary>정답 보기</summary>

**정답: B. 4g.20gb**

**설명:** A10040GB 예제는1g.5gb,2g.10gb,3g.20gb,4g.20gb,7g.40gb입니다.4g.40gb는 A10080GB 집합에 속합니다. g는 profile의 compute slice 수이며 명목 메모리가 정확한 사용 가능 메모리를 보장하지 않습니다.

</details>

### 3. Time-slicing의 replicas:4가 제공하는 것은?

A. 물리 GPU4개와 독립 메모리 영역4개

B. 구성한 GPU마다 메모리·장애 영역을 공유하는 논리적 접근 슬롯4개

C. Pod마다 compute1/4 보장

D. GPU 메모리 자동 확장

<details>
<summary>정답 보기</summary>

**정답: B. 구성한 GPU마다 메모리·장애 영역을 공유하는 논리적 접근 슬롯4개**

**설명:** 경합과 워크로드 동작에 따라 지연·처리량이 달라집니다. Replica를 더 요청해도 비례한 compute를 보장하지 않습니다. renameByDefault:true이면 nvidia.com/gpu.shared를 게시하며 사용되지 않는 ConfigMap 생성만이 아니라 실제 plugin에 구성을 연결해야 합니다.

</details>

### 4. 현재 DRA가 GPU 할당에 추가하는 기능은?

A. 공급자 드라이버 없는 GPU 지원

B. 정적 CPU·메모리 요청만

C. DeviceClass·ResourceClaim을 통한 구조화된 장치 선택·할당

D. 모든 GPU 애플리케이션의 운영 자동 검증

<details>
<summary>정답 보기</summary>

**정답: C. DeviceClass·ResourceClaim을 통한 구조화된 장치 선택·할당**

**설명:** 공급자 드라이버, ResourceSlice, 호환 kubelet·런타임과 활성 API가 계속 필요합니다. 현재 v1 claim은 requests[].exactly를, Pod resourceClaims는 resourceClaimTemplateName 직접 참조를 사용합니다.

</details>

### 5. 현재 ResourceClaim은 어떻게 평가해야 하는가?

A. 일반적인 status.phase:Bound enum 대기

B. Claim 생성만으로 GPU 사용 가능 확인

C. allocation.devices.results, 예약, Pod 이벤트와 드라이버 준비 조사

D. 이전 resourceHandles 필드만 조사

<details>
<summary>정답 보기</summary>

**정답: C. allocation.devices.results, 예약, Pod 이벤트와 드라이버 준비 조사**

**설명:** 현재 ResourceClaim에 일반적인 저장 phase인 Pending→Allocated→Bound 순서는 없습니다. 할당·예약은 장치 주입이나 애플리케이션 실행 성공의 증거가 아닙니다.

</details>

### 6. GPU Operator26.7 소유권 설명으로 올바른 것은?

A. GPUCluster·ClusterPolicy를 항상 함께 실행

B. Device-plugin 관리에는 ClusterPolicy, 신규 관리 DRA에는 GPUCluster를 선택하며 둘은 공존 불가

C. driver.enabled:false가 누락된 호스트 드라이버 설치

D. 컨트롤러 nodeSelector가 모든 operand를 자동 한정

<details>
<summary>정답 보기</summary>

**정답: B. Device-plugin 관리에는 ClusterPolicy, 신규 관리 DRA에는 GPUCluster를 선택하며 둘은 공존 불가**

**설명:** GPUCluster는 이름이 gpu-cluster인 cluster-scoped singleton입니다. 관리 DRA 방식은 ClusterPolicy·독립 DRA에서의 제자리 마이그레이션이 아닙니다. 적절한 드라이버·CDI·discovery를 준비하고 operand label을 별도로 검토합니다.

</details>

### 7. H100SXM/H200SXM 비교가 보여주는 것은?

A. 모든 H100 variant의 메모리가 같다

B. NVIDIA 사양은 H100SXM80GB/3.35TB/s, H200SXM141GB/4.8TB/s이며 애플리케이션 결과는 별도 측정 필요

C. H200은 MIG 미지원

D. H200은 모든 애플리케이션 처리량을 항상 두 배로 증가

<details>
<summary>정답 보기</summary>

**정답: B. NVIDIA 사양은 H100SXM80GB/3.35TB/s, H200SXM141GB/4.8TB/s이며 애플리케이션 결과는 별도 측정 필요**

**설명:** 공급자의 SKU 사양이며 감사 벤치마크가 아닙니다. H100NVL/PCIe variant는 다릅니다. 모델 크기, 정밀도, batch, 소프트웨어, interconnect와 경합도 실제 성능에 영향을 줍니다.

</details>

### 8. EKS GPU 배포 경계로 올바른 것은?

A. 모든 Auto Mode 노드에 추가 NVIDIA device plugin 설치

B. 모든 EKS 노드에서 DRA 미지원

C. 한정된 Hybrid 할당 집합 사용; 현재 Auto Mode는 DRA 미지원이며 자체 device plugin 관리

D. 물리 GPU마다 최대한 많은 관리자로 중복 게시

<details>
<summary>정답 보기</summary>

**정답: C. 한정된 Hybrid 할당 집합 사용; 현재 Auto Mode는 DRA 미지원이며 자체 device plugin 관리**

**설명:** AWS는 지원되는 신규 EKS1.34 이상 정적 용량 배포에 DRA를 권고합니다. 문서화된 드라이버 요구 사항을 따르고 중복 장치 소유를 막습니다. Kubernetes API 성숙도와 공급자별 feature gate는 별개입니다.

</details>

### 9. 컨테이너가 DRA GPU1개를 요청할 때 CUDA_VISIBLE_DEVICES는 어떻게 다뤄야 하는가?

A. 항상0,1,2,3 지정

B. 호스트에서 발견한 모든 물리 index 지정

C. 변수로 GPU3개를 추가 요청

D. 장치 관리자·런타임이 할당한 장치를 제공하게 하고 관련 없는 물리 index로 덮어쓰지 않음

<details>
<summary>정답 보기</summary>

**정답: D. 장치 관리자·런타임이 할당한 장치를 제공하게 하고 관련 없는 물리 index로 덮어쓰지 않음**

**설명:** 프로세스가 보는 CUDA index와 물리 GPU index는 다를 수 있습니다. 수동 override는 장치를 숨기거나 잘못 식별할 수 있으며 추가 GPU를 허용하지 않습니다. 여러 컨테이너가 같은 claim을 참조해도 할당 하나를 공유합니다.

</details>

### 10. 정지 상태 smoke Job과 로컬 스키마 검사가 증명하는 것은?

A. GPU 드라이버·모델 실행 성공

B. 모든 GPU 워크로드의 지연 SLO 충족

C. 검토한 manifest·구성이 제한된 로컬 검사를 통과했으며 실제 GPU 검증은 소유자 승인·실행 필요

D. 정리 검증이 더는 필요 없음

<details>
<summary>정답 보기</summary>

**정답: C. 검토한 manifest·구성이 제한된 로컬 검사를 통과했으며 실제 GPU 검증은 소유자 승인·실행 필요**

**설명:** 의도적으로 사용 불가능한 이미지를 승인한 다이제스트로 교체하고 런타임·배치·보안을 확인한 뒤 Job 하나를 재개합니다. 결과를 보존하고 정리 시 claim unprepare·해제를 확인합니다. nvidia-smi 가시성만으로 CUDA·LLM 벤치마크가 되지 않습니다.

</details>

