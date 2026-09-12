# Part 4: 성능 및 비용 튜닝 퀴즈

Spark 4.2.0 / Karpenter 1.14 기준 · September 2026.

## 1. 셔플 작업은 항상 R 계열·NVMe가 가장 빠른가요?

<details>
<summary>정답 보기</summary>

아닙니다. Task/stage 시간, spill, shuffle fetch wait, skew, CPU·메모리·디스크·네트워크 병목을 측정하고 현재 용량·성공한 작업당 비용으로 비교합니다. 다른 instance 계열이나 EBS가 부적합하다고 단정하지 않습니다.

</details>

## 2. Graviton 평가 시 필요한 것은?

<details>
<summary>정답 보기</summary>

Spark 이미지와 JNI·codec·BLAS·Python wheel·plugin의 arm64 호환성을 확인하고 대표 작업을 측정합니다. 이미 검증된 multi-arch 이미지가 있으면 직접 빌드가 항상 필요한 것은 아닙니다.

</details>

## 3. 마운트되지 않은 nvme 디스크를 포맷해도 되나요?

<details>
<summary>정답 보기</summary>

아닙니다. Nitro의 EBS도 NVMe로 보이고 마운트되지 않은 디스크에 데이터나 파티션이 있을 수 있습니다. 이름·mount 여부만으로 instance store를 판별하지 않습니다.

</details>

## 4. AL2023의 instanceStorePolicy: RAID0는 무엇을 구성하나요?

<details>
<summary>정답 보기</summary>

Karpenter가 NodeConfig로 instance-store RAID0와 kubelet/containerd의 ephemeral storage 사용을 구성하고 allocatable을 반영합니다. RAID0은 백업이 아니며 IAM·AMI·subnet 등의 완전한 NodeClass 설정은 별도로 필요합니다.

</details>

## 5. 이 장에서 hostPath 없이 NVMe scratch를 사용하는 이유는?

<details>
<summary>정답 보기</summary>

준비한 NodeClass가 kubelet filesystem을 instance store로 구성하므로 Pod의 disk-backed emptyDir도 그 저장소를 사용합니다. 다른 node 설정이나 tmpfs를 사용하면 backing store가 달라집니다.

</details>

## 6. Spark가 인식하는 scratch volume 이름은?

<details>
<summary>정답 보기</summary>

`spark-local-dir-scratch`처럼 spark-local-dir- 접두사와 뒤따르는 이름이 필요합니다. 이전 spark-local-dir은 일치하지 않아 같은 mountPath에 추가 emptyDir이 생길 수 있습니다.

</details>

## 7. emptyDir sizeLimit은 디스크 공간 예약인가요?

<details>
<summary>정답 보기</summary>

아닙니다. Pod 요청·노드 allocatable·다른 Pod·로그·writable layer와 함께 고려합니다. 노드가 먼저 가득 찰 수 있으며 memory-backed tmpfs는 RAM 예산에 포함합니다.

</details>

## 8. On-Demand driver와 Spot executor가 보장하지 않는 것은?

<details>
<summary>정답 보기</summary>

Driver 장애·drift/expiry를 없애거나 executor 손실을 항상 무해하게 만들지는 않습니다. Spot-only selector는 On-Demand fallback을 허용하지 않아 용량 부족 시 Pending일 수 있습니다.

</details>

## 9. Taint·toleration과 node selector의 역할은?

<details>
<summary>정답 보기</summary>

Toleration은 taint를 허용하고 selector가 노드를 선택합니다. 다른 Pod도 같은 toleration을 가질 수 있으며 NoSchedule은 이미 실행 중인 Pod를 퇴거시키지 않습니다.

</details>

## 10. Spot 경고와 decommission flag만으로 이동 완료가 보장되나요?

<details>
<summary>정답 보기</summary>

아닙니다. 경고는 best effort이고 hibernation에는 2분 여유가 없습니다. EventBridge/SQS/interruption queue, drain, 실제 hook/signal, 남은 시간·peer 공간·네트워크가 맞아야 합니다. 120s Pod grace도 클라우드 종료를 연장하지 않습니다.

</details>

## 11. Remote storage만 있으면 shuffle fallback이 자동 동작하나요?

<details>
<summary>정답 보기</summary>

아닙니다. spark.storage.decommission.fallbackStorage.path와 지원 filesystem·권한을 구성해야 합니다. RDD cache와 shuffle 복구는 다르며 재계산·fetch 실패·재시도 한도 때문에 잡이 실패할 수 있습니다.

</details>

## 12. DRA와 Karpenter가 사용하는 신호는 무엇인가요?

<details>
<summary>정답 보기</summary>

DRA는 Spark task backlog와 executor idle/cache/shuffle 상태로 수량을 조절합니다. Karpenter는 Pod 요청·스케줄링 조건으로 노드를 공급합니다. 이 경로에 metrics-server는 필수가 아니며 allocation.batch.size는 Kubernetes allocator의 생성 속도 설정입니다.

</details>

## 13. consolidateAfter를 executorIdleTimeout보다 크게 두면 DRA가 먼저 비우나요?

<details>
<summary>정답 보기</summary>

보장되지 않습니다. 시작 조건이 다른 타이머이고 shuffle/cache가 executor를 유지할 수 있습니다. WhenEmpty는 일반 작업 Pod 통합을 줄이는 선택이지만 drift·expiry·Spot 종료는 별도입니다.

</details>

## 14. JVM executor heap 4g와 cores=2를 Pod 총 memory/CPU limit으로 보면 되나요?

<details>
<summary>정답 보기</summary>

아닙니다. 이 예제의 기본 overhead 409MiB를 더한 memory는 4505MiB입니다. cores는 기본 CPU request와 Spark 병렬성에 관련되며 CPU limit은 spark.kubernetes.executor.limit.cores로 명시합니다. PySpark·off-heap·별도 overhead는 추가 검토합니다.

</details>

[Guide](../../../data-on-eks/spark/04-performance-tuning.md)
