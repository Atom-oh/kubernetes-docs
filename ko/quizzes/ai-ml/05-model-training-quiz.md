# EKS 모델 훈련 퀴즈

현재 API·launcher·복구 경계를 확인하는15문항입니다.

## 1. 텐서 병렬화는 무엇을 분할하나요?

<details>
<summary>정답 및 설명</summary>

레이어 내부 tensor 연산과 가중치를 나눕니다. DP는 데이터 replica,PP는 layer stage,expert parallel은 expert/token dispatch를 나누며 각 통신 패턴이 다릅니다.
</details>

## 2. 200B 모델과 global batch를 어떻게 설계하나요?

<details>
<summary>정답 및 설명</summary>

크기만으로3D를 고정하지 않고 훈련 상태·activation·통신·device mesh를 계산합니다. TP8×PP4×DP2는64rank지만 microbatch1×accumulation32×DP2의 global batch는64입니다.
</details>

## 3. slurmctld와 slurmdbd의 상태 관리 역할은 어떻게 다른가요?

<details>
<summary>정답 및 설명</summary>

slurmctld는 실행 job/node/partition과 스케줄링 및 StateSaveLocation을 관리합니다. slurmdbd는 accounting DB 기록 경로이며 controller의 복구 상태를 대체하지 않습니다.
</details>

## 4. Slinky1.2.2의 compute group API는 무엇인가요?

<details>
<summary>정답 및 설명</summary>

slinky.slurm.net/v1beta1 NodeSet입니다. Controller 참조와 template을 사용하고 기본 StatefulSet 방식,선택적 DaemonSet 방식이 있습니다. DaemonSet 방식에서는 replicas를 무시합니다. SlurmNodeSet이 아닙니다.
</details>

## 5. FI_PROVIDER=efa만 설정하면 NCCL EFA가 작동하나요?

<details>
<summary>정답 및 설명</summary>

아닙니다. EFA interface/driver/libfabric/aws-ofi-nccl/device plugin·Pod 할당·보안 그룹·같은 AZ가 필요합니다. 실제 transport를 로그·collective 테스트로 확인하며 대역폭을400Gbps로 고정하지 않습니다.
</details>

## 6. BioNeMo3.0.0에서 확인할 것은 무엇인가요?

<details>
<summary>정답 및 설명</summary>

BioNeMo Recipes의 모델·TransformerEngine·훈련 recipe별 지원입니다. 예전1.5 MegaMolBART module을 그대로 쓰지 않고 이미지·데이터·모델 revision,장치·수렴과 생물학적 평가를 검증합니다.
</details>

## 7. Optimum Neuron의 Trainer가 모든 HF 모델 훈련을 보장하나요?

<details>
<summary>정답 및 설명</summary>

아닙니다. 해당 버전의 training-model 구현·training config·SDK/PyTorch·장치·데이터와 collator가 맞아야 합니다. 추론 지원과 훈련 지원을 구분하고 pretrained 모델·undefined dataset만으로 TP 훈련을 주장하지 않습니다.
</details>

## 8. 훈련 스토리지에서 FSx와 S3 연동을 어떻게 확인하나요?

<details>
<summary>정답 및 설명</summary>

static mount와 dynamic provisioning을 구분하고 DRA/import/export 정책·완료 상태·권한을 확인합니다. EFS PVC 용량은 quota가 아니며 local 저장만으로 S3 durability가 보장되지 않습니다.
</details>

## 9. Volcano minAvailable:4이면 node가4개 필요하나요?

<details>
<summary>정답 및 설명</summary>

아닙니다. Pod/member 수입니다.3node에도4Pod를 수용할 수 있습니다. 최소 member/자원 조건과 gang plugin을 확인해야 하며 동시에 모든 container가 시작하거나 학습에 성공한다는 뜻은 아닙니다.
</details>

## 10. BF16이 FP16과 다른 점은 무엇인가요?

<details>
<summary>정답 및 설명</summary>

지수8bit·가수7bit로 FP32와 지수bit수는 같지만 precision·최대 유한값은 다릅니다. 대개FP16용 loss scaling 없이 쓰지만 device·operation·수렴을 확인하며 autocast가 모든 훈련 상태를BF16으로 바꾸지는 않습니다.
</details>

## 11. activation checkpointing과 복구 checkpoint는 어떻게 다른가요?

<details>
<summary>정답 및 설명</summary>

activation checkpointing은 backward 재계산으로 memory와 compute를 교환합니다. 디스크의 모델/optimizer/RNG 복구본과 다릅니다. use_reentrant·RNG/상태·gradient를 확인하고 고정3–4배 절약을 가정하지 않습니다.
</details>

## 12. ZeRO Stage3는 자동 CPU offload인가요?

<details>
<summary>정답 및 설명</summary>

아닙니다. optimizer·gradient·parameter 분할 단계이며 offload는 별도 설정입니다. Stage1/2/3의 메모리 절감은 DP크기·state·buffer·activation에 따라 달라지고 무제한 scaling은 아닙니다.
</details>

## 13. MPIJob slotsPerWorker가 무엇을 보장하나요?

<details>
<summary>정답 및 설명</summary>

hostfile의 worker별 slot입니다. 실제 process수는 mpirun -np/mapping과 launcher 설정으로 결정되며 GPU당1rank binding도 별도로 필요합니다. 현재 Operator0.8.2는v2beta1 API를 사용합니다.
</details>

## 14. 체크포인트 주기와 복구 성공을 어떻게 검증하나요?

<details>
<summary>정답 및 설명</summary>

저장 시간·장애율·허용 손실·보존 비용으로 주기를 선택합니다. 모든 state/manifest/checksum과 remote 완료를 확인하고 실제 resume를 비교합니다. 본문 CPU 예제는4update 연속 실행과2update 후 복구가 동일함을 검증했습니다.
</details>

## 15. EFA용 단일 AZ와 Karpenter disruption budget의 의미는 무엇인가요?

<details>
<summary>정답 및 설명</summary>

통신 worker가 실제 같은AZ에 배치되도록 Pod/NodePool 조건을 연결합니다. placement group은 권장 성능 조건입니다. budget0은 자발적 disruption 제한이며 Spot회수·장애·강제 종료를 막지 못합니다.
</details>

[본문으로 돌아가기](../../ai-ml/05-model-training.md)
