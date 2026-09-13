# Part 9: Kafka 벤치마크 검토 퀴즈

보고된 수치와 인과 주장, 재현 절차를 구분해 판단합니다.

## 1. 브로커 3개·RF3에서 각 브로커의 저장량 모델은 무엇이며 F1의 134.74MiB/s를 어떻게 해석해야 하나요?

<details>
<summary>정답 보기</summary>

각 브로커는 모든 파티션의 복제본 하나를 가집니다. 인코딩 log rate와 client payload rate는 다르며 F1은 짧은 단일 실행의 client 보고값입니다. 캐시·writeback·구간·단위를 맞추기 전에는 130–135MiB/s를 검증된 지속 상한으로 부를 수 없습니다.

</details>

## 2. 낮은 IOPS와 높은 byte rate가 관찰되면 볼륨 처리량만이 유일한 병목이라고 확정할 수 있나요?

<details>
<summary>정답 보기</summary>

아닙니다. 순차 I/O·처리량 압박과 일치하지만 인스턴스 EBS 기준·burst, 캐시, client와 표본 오차도 확인해야 합니다. 최고 표본 135를 gp3의 125MiB/s 설정과 등식으로 취급하지 않습니다. 다른 조건을 고정한 처리량 변경 등으로 가설을 시험합니다.

</details>

## 3. B1/B2의 p50이 각각 3ms, p99가 126/17ms이면 acks 비용은 꼬리에만 있다고 말할 수 있나요?

<details>
<summary>정답 보기</summary>

아닙니다. p99 비율은 약 7.412이지만 평균도 5.27/2.58ms로 다릅니다. 정수 ms 표본의 같은 p50은 underlying latency 동일성을 증명하지 않으며 한 쌍의 실행을 일반화하지 않습니다. acks=0 callback은 브로커 내구성 응답도 아닙니다.

</details>

## 4. F4/F1의 337.81/134.74=2.507배를 순수한 복제 비용으로 해석하면 안 되는 이유는 무엇인가요?

<details>
<summary>정답 보기</summary>

RF3/acks=all에서 RF1/acks=1로 두 설정을 바꿨고 생략한 멱등성 기본값도 달라집니다. 실행 시간·브로커당 데이터량·캐시·client 제약도 다릅니다. 관찰된 산술 비율은 보존하되 RF만 통제한 인과 결과로 제시하지 않습니다.

</details>

## 5. F6에서 batch·linger·건수를 함께 바꾼 결과를 어떻게 기술해야 하나요?

<details>
<summary>정답 보기</summary>

처리량 148.38은 134.74보다 10.12% 높고 CPU 범위는 낮게 보고되었습니다. CPU 중간값의 39.19% 차이는 산술일 뿐 batch만의 효과가 아닙니다. 반복 분산 없이 처리량 차이를 노이즈라고 판정할 수 없습니다.

</details>

## 6. 패딩된 JSON의 압축 비율과 codec 순서를 다른 로그에도 그대로 적용할 수 있나요?

<details>
<summary>정답 보기</summary>

아닙니다. 약 63.2%의 x 패딩 때문에 데이터 분포가 특수하며 비율·순서 모두 공통 상한이나 순위가 아닙니다. 공개 AWK를 다른 구현으로 재생성하면 hash·압축률도 달라질 수 있어 원본 payload·이미지·도구 버전을 보존해야 합니다.

</details>

## 7. E4의 감소율과 EC2 네트워크 카운터를 해석할 때 어떤 혼동을 피해야 하나요?

<details>
<summary>정답 보기</summary>

producer는 103.36→57.37MiB/s로 44.49% 감소했지만 consumer와 같은 1.9CPU client·NIC를 공유합니다. broker CPU만으로 client 경합을 배제하지 않습니다. EC2 rx/tx credit은 별도이며 F1의 rx136MiB/s≈1.141Gbps, tx108≈0.906Gbps는 각각 1.25Gbps보다 낮습니다. 합산해 burst를 주장하지 않습니다.

</details>

## 8. 새 재현 실험에서 단위·정상 상태·성공 여부를 어떻게 검증해야 하나요?

<details>
<summary>정답 보기</summary>

30M×1024B는 28.610GiB이며 10GiB·1분 같은 보편적 정상 상태 기준은 없습니다. 고정 warmup·긴 구간·drain·반복·공통 분모와 실제 장치/시각 카운터를 기록합니다. 최신 옵션, 생성·채운 새 토픽, producer 최종 성공 건수와 stderr, consumer 내용을 확인합니다. callback 오류가 종료 코드만으로 드러나지 않을 수 있으며 비용 추정은 청구서가 아닙니다.

</details>

---

[학습 자료로 돌아가기](../../../data-on-eks/kafka/09-kafka-benchmark.md) | [Kafka 딥다이브 홈](../../../data-on-eks/kafka/README.md)
