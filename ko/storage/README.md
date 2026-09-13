# Storage 개요

> **마지막 업데이트**: 2026년 9월 11일

Kubernetes 위에서 상태(state)를 다루는 순간, 스토리지는 더 이상 "붙이면 되는 것"이 아니라 성능·비용·가용성을 좌우하는 독립된 도메인이 됩니다. 이 섹션은 클라우드 스토리지를 **선택 기준 → 실측 성능 → 운영**의 순서로 다룹니다.

## 이 섹션의 구성

| 문서 | 다루는 내용 |
|------|-------------|
| [EBS gp2 vs gp3 실측 벤치마크](./01-ebs-gp2-gp3-benchmark.md) | 같은 100 GiB 볼륨인데 왜 성능이 10배 차이 나는가 — fio로 직접 측정한 IOPS/레이턴시/처리량과 gp2 버스트 크레딧 절벽 |

Kubernetes 스토리지의 기본 개념과 EKS에서의 실전 구성은 기존 문서에서 이미 깊게 다루고 있습니다. 이 섹션과 함께 읽어야 할 문서:

- [Kubernetes 스토리지 기본](../core/04-storage.md) — PV/PVC, StorageClass, 동적 프로비저닝, 액세스 모드
- [EKS 스토리지 Part 1: EBS, EFS](../eks/04-eks-storage-part1.md) — CSI 드라이버 설치와 기본 사용
- [EKS 스토리지 Part 2: FSx for Lustre, S3, 스냅샷, 성능 최적화](../eks/04-eks-storage-part2.md)
- [EKS 스토리지 Part 3: 모니터링, 문제 해결, 비용 최적화](../eks/04-eks-storage-part3.md)

## 스토리지 스택 한눈에 보기

파드가 볼륨에 쓰기까지의 경로를 이해하면 성능 문제를 어느 계층에서 찾아야 할지 보입니다:

```text
애플리케이션 write()
  → 마운트한 볼륨의 파일시스템 (ext4/xfs)
    → 게스트 커널·블록 디바이스
      → EC2 인스턴스의 EBS 경로 (전체 볼륨이 공유하는 IOPS/대역폭)
        → EBS 서비스·볼륨 (볼륨별 IOPS/처리량 한도)
```

볼륨 자체의 한도와 **인스턴스 레벨의 EBS 대역폭/IOPS 한도**는 별개입니다. 예를 들어 m5.xlarge는 베이스라인 약 6,000 IOPS이므로, gp3 볼륨 3개를 각 3,000 IOPS로 동시에 사용하면 총 9,000 IOPS 수요가 지속 베이스라인을 넘습니다. 인스턴스 버스트 상태와 다른 볼륨의 I/O까지 함께 확인해야 합니다.

## AWS 스토리지 선택 가이드

| 서비스 | 액세스 모드 | 특성 | 적합한 워크로드 |
|--------|------------|------|----------------|
| **EBS (gp3/io2)** | RWO (단일 노드) | 블록, 지연시간은 타입·부하·큐 깊이에 의존 | 데이터베이스, 단일 파드 상태 저장 |
| **EFS** | RWX (다중 노드) | NFS, ms급 레이턴시, 탄력적 용량(사전 프로비저닝 불필요) | 공유 설정/콘텐츠, ML 학습 데이터 공유 |
| **FSx for Lustre** | RWX | 병렬 파일시스템, 고처리량 | HPC, 대규모 ML 학습 |
| **S3 (Mountpoint CSI)** | RWX (읽기 중심) | 객체, POSIX/NFS와 다른 파일 연산 제약 | 데이터 레이크, 모델/아티팩트 저장 |
| **인스턴스 스토어** | 노드 로컬 | NVMe, 최저 레이턴시, **비영속** | 캐시, 셔플 데이터, 임시 스크래치 |

RWO는 한 노드의 여러 Pod에서 사용될 수 있어 단일 Pod 보장과 다릅니다. io2 Multi-Attach 같은 예외는 별도 지원 조건과 파일시스템/애플리케이션 동시성 설계가 필요합니다. Mountpoint S3는 범용 POSIX 공유 파일시스템이 아니므로 기존 파일 수정·rename·잠금 등의 지원을 워크로드별로 확인합니다. 인스턴스 스토어는 reboot와 달리 stop/termination 등에서 데이터가 사라질 수 있습니다.

## 왜 실측이 필요한가

스토리지는 스펙 시트와 실제 체감이 가장 크게 벌어지는 영역입니다. 대표적인 함정:

1. **작은 gp2의 버스트 크레딧** — 베이스라인이 3,000 IOPS 미만인 볼륨은 잔여 크레딧으로 버스트합니다. 지속 시간은 초기 잔량·용량·부하에 따라 달라집니다. 가득 찬 100 GiB 볼륨에 3,000 IOPS를 가한 경우 계산상 약 33분이므로 짧은 테스트는 소진 이후 성능을 놓칠 수 있습니다.
2. **볼륨 한도 vs 인스턴스 한도** — 위 스택 다이어그램 참고.
3. **iodepth(동시성)에 따라 다른 결론** — 큐 깊이 1의 레이턴시 측정과 큐 깊이 32의 IOPS 측정은 전혀 다른 특성을 보여줍니다.

[EBS gp2 vs gp3 실측 벤치마크](./01-ebs-gp2-gp3-benchmark.md)에서 이 함정들을 fio로 직접 확인합니다.

## 참고 자료

- [EBS performance](https://docs.aws.amazon.com/ebs/latest/userguide/general-purpose.html)
- [EC2 EBS limits](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ebs-optimized.html)
- [Mountpoint S3 semantics](https://github.com/awslabs/mountpoint-s3/blob/main/doc/SEMANTICS.md)
