# Part 9: Kafka on EKS 벤치마크 — 기록된 결과와 재현·해석 범위

> **보고된 실험**: 2026년 9월 2일 02:07–02:36 UTC\
> **검토 갱신**: 2026년 9월 12일\
> **실험 버전**: Kafka 4.3.1, EKS Kubernetes 1.36; broker/controller combined Pod 3개

PR #166에 보고된 단일 실행 표를 유지하면서 단위·비교 조건과 재현 절차를
검토했습니다. 원시 telemetry와 원본 payload hash는 저장소 보고서에 포함되어 있지
않습니다. 이번 검토는 AWS 실험을 다시 실행하거나 과거 측정의 수집 성공을 독립적으로
확인한 작업이 아닙니다.

기록은 스토리지·캐시·클라이언트 제약을 추가 시험할 근거가 됩니다. 하지만
**RF3의 공통 또는 수 시간 지속 상한이 130–135MiB/s라고 확정하지는 못합니다**.
RF 비교는 acks도 바꾸고 배치 비교는 linger·실행 길이도 바꿉니다.
관찰된 비율을 특정 변수 하나의 인과 효과로 제시하지 않습니다.

![브로커 3개·RF3 환경에서 한 파티션의 producer, leader, follower fetch 응답과 비동기 볼륨 쓰기를 보여주며 클러스터 합계 관찰값은 별도로 표시한 데이터 흐름.](../../.gitbook/assets/ko-data-on-eks-kafka-09-kafka-benchmark-0.png)

[인터랙티브 다이어그램](https://www.atomai.click/kubernetes-docs/archmaps/ko-data-on-eks-kafka-09-kafka-benchmark-0.html)

## 주요 관찰과 해석 한계

| 보고된 비교 | 기록값 | 해석 한계 |
| --- | --- | --- |
| F1 RF3 / acks=all | 클라이언트 134.74MiB/s, 브로커 표본 구간 약 75초 | 짧은 client rate이며 검증된 지속 디스크 쓰기율은 아님 |
| F4 / F1 | 337.81 / 134.74 = 2.507배 | RF·acks/기본 멱등성·실행 시간·캐시 상태가 함께 다름 |
| F6 / F1 | 148.38 / 134.74MiB/s, +10.12%; 브로커 CPU는 낮게 기록 | batch·linger·레코드 수가 모두 바뀌었고 반복 분산 측정 없음 |
| B1 / B2 | p50 각각 3ms, p99 126 / 17ms | 정속 단일 비교이며 “비용은 꼬리에만 있음”이라는 일반 규칙은 아님 |
| E4 / E0 | producer 57.37 / 103.36MiB/s, −44.49% | 읽기·쓰기 경합은 가능하지만 공용 client의 경합도 있음 |

## 보고된 환경

| 항목 | 값 |
|------|-----|
| 클러스터 | Amazon EKS, Kubernetes 1.36, ap-northeast-2 (서울), Karpenter 프로비저닝 노드 |
| 브로커 | 3 × `apache/kafka:4.3.1` (kafka_2.13-4.3.1, OpenJDK 21.0.11), **KRaft combined 모드**(각 파드가 broker+controller), StatefulSet 직접 배포 — Strimzi 등 Operator 없음 |
| 브로커 노드 | 3 × **m5.xlarge** 온디맨드 (4 vCPU, 16 GiB), 모두 **ap-northeast-2b** 단일 AZ, podAntiAffinity로 노드당 브로커 1개, Karpenter `system` NodePool이 측정 직전 새로 만든 노드 |
| 브로커 파드 리소스 | requests cpu 3 / mem 10Gi, limits cpu 4 / mem 12Gi, `KAFKA_HEAP_OPTS=-Xms4G -Xmx4G` (나머지 메모리도 native/off-heap·page cache 등이 함께 사용) |
| 브로커 스토리지 | 브로커당 **gp3 100 GiB** PVC 1개 (EBS CSI, StorageClass `gp3`), gp3 기본 성능 **3,000 IOPS / 125 MiB/s** (크기와 무관한 베이스라인) |
| 브로커 설정 | `num.partitions=6`, `default.replication.factor=3`, `min.insync.replicas=2`, `log.segment.bytes=1 GiB`, `num.network.threads=4`, `num.io.threads=8`, `num.replica.fetchers=2`, `log.retention.hours=2` |
| 커널 | Amazon Linux 2023, 6.18.41-94.142.amzn2023.x86_64; `vm.dirty_ratio=20`, `vm.dirty_background_ratio=10`, `vm.dirty_expire_centisecs=3000` |
| m5.xlarge 인스턴스 한도 | 네트워크 베이스라인 1.25 Gbps (버스트 10 Gbps); EBS 베이스라인 1,150 Mbps = 143.75 MB/s (≈137 MiB/s; 1,150 × 10⁶ ÷ 8 ÷ 1,048,576), 6,000 IOPS |
| 부하 생성기 | `kafka-client` 파드 1개 (같은 이미지), **m5.large** 노드 (2 vCPU, 8 GiB), cgroup **CPU 한도 1.9**, `KAFKA_HEAP_OPTS=-Xms2G -Xmx2G`; m5.large 네트워크 베이스라인 0.75 Gbps (버스트 10 Gbps) |
| 도구 | `kafka-producer-perf-test.sh`, `kafka-consumer-perf-test.sh` (apache/kafka 4.3.1 이미지에 동봉) |
| 네트워크 경로 | 같은 AZ 안의 파드 간 통신, PLAINTEXT (TLS/SASL 없음) |
| 토픽 | 테스트마다 새 토픽, 파티션 6개; RF3/min.isr=2 (RF1 테스트만 RF1/min.isr=1); `retention.bytes=-1` |
| 테스트 프로듀서 설정 | `linger.ms=5`, `batch.size=65536`, `buffer.memory=67108864` (64 MiB), `compression.type=none` — 별도 표기 없으면 모든 테스트 공통 |
| 시간당 비용 | m5.xlarge 온디맨드 $0.236/h × 3 + gp3 100 GiB $0.0912/GB-월 × 3 (서울 리전, 2026-09 Pricing API 조회) |

원문은 첫 측정 전에 02:05:22Z의 `kafka-1` 재시작 1회와 측정 중 재시작 없음을
기록했습니다. “기동 race”라는 설명은 원인 분석으로 확정된 결과가 아닙니다.

모두 단일 AZ·PLAINTEXT·SASL 없음·Strimzi 없음으로 보고되었습니다.
3개 AZ의 운영 환경과 같은 비교가 아닙니다. TLS, AZ 간 트래픽, 노드·스토리지 한계와
분리된 controller는 별도 측정이 필요합니다.

## 페이로드와 도구의 의미

보고된 파일은 **값 길이 1,008바이트**인 합성 JSON 20,000줄이며 약 63.2%는 쉽게
압축되는 `x` 패딩입니다. 줄 구분 문자는 전송 값에 포함되지 않습니다.
1,000만 건의 payload는 **9.388GiB**이고, 원문의 디스크상 1,018B/record를 적용하면
복제본당 약 **9.481GiB**입니다.

E2/E3는 **3,000만 × 1,024B = 28.610GiB**입니다. 기존의 “30GiB”, “29.3GiB”는
정확한 GiB 환산이 아니었습니다. 300만 × 1,024B는 2.861GiB입니다.

Kafka 4.3.1 도구 기준:

- `--record-size`는 레코드마다 A–Z 바이트를 만들고, `--payload-file`은 이미 읽은
  값을 선택합니다. 생성 비용은 CPU에 영향을 주지만 **보고되는 send latency의
  측정 시작 전**에 발생합니다.
- 출력의 MB/sec는 1,024²로 나누므로 **MiB/s**입니다. 압축 시에도 NIC·볼륨 바이트가
  아닌 압축 전 payload 바이트를 셉니다.
- latency는 send 직전부터 callback까지이며 동기 send/buffer 대기는 포함하지만
  앞선 payload 생성·후속 업무 처리는 포함하지 않습니다. acks=0 callback은
  브로커 내구성 확인 응답이 아닙니다.
- 큰 실행은 정수 ms latency를 주기적으로 표본 추출합니다. p50이 둘 다 3ms라는
  사실로 실제 지연 분포가 동일하다고 증명할 수 없습니다.
- callback 실패는 출력되지만 성공 전송 건수에 포함되지 않습니다. 종료 코드만
  보지 말고 최종 성공 건수와 stderr를 확인합니다.
- 컨슈머 전체 시간·그룹 조인을 뺀 fetch 시간·선택 구간의 rate는 분모가 다릅니다.
  마지막 poll 묶음으로 요청 건수를 초과할 수 있습니다.

기존 `--producer-props`, 컨슈머 `--messages`는 아직 동작하지만 deprecated입니다.
새 예제는 `--command-property`, `--num-records`를 사용합니다.

## 1. RF·응답 방식·표본 구간

payload-file·무압축 실행의 원문 기록값입니다.

| Test | acks | RF | 프로듀서 | 레코드 | rec/s | MiB/s | avg ms | p50 | p95 | p99 | p99.9 | max |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| F1 | all | 3 | 1 | 1,000만 | 140,164 | **134.74** | 443.89 | 321 | 1,276 | 2,689 | 4,026 | 4,038 |
| F2 | 1 | 3 | 1 | 600만 | 248,221 | 238.62 | 222.66 | 230 | 321 | 398 | 426 | 650 |
| F3 | 0 | 3 | 1 | 600만 | 241,138 | 231.81 | 235.02 | 191 | 333 | 1,977 | 4,327 | 4,340 |
| F4 | 1 | 1 | 1 | 1,000만 | 351,407 | **337.81** | 159.51 | 138 | 290 | 358 | 515 | 642 |
| F5 | all | 3 | 2 | 2 × 500만 | 67,694 + 67,360 = 135,054 | 65.07 + 64.75 = **129.82** | 893.88 / 889.22 | 639 / 630 | 2,536 / 2,493 | 3,270 / 3,301 | 4,284 / 4,228 | 4,662 / 4,660 |
| F6 | all | 3 | 1 | 600만 | 154,349 | 148.38 | 395.82 | 238 | 1,142 | 2,094 | 2,594 | 2,621 |

F4/F1의 산술 비율은 2.507이지만 F4는 RF1/acks=1, F1은 RF3/acks=all입니다.
멱등성을 생략한 Kafka 4.3.1의 기본 동작도 이 acks 설정에 따라 달라집니다.
복제만 통제한 비교가 아닙니다. 약 32초인 F4는 각 브로커에 데이터의 약 1/3만
배치되어 캐시·클라이언트 한계의 영향을 받을 수 있습니다.

F5의 129.82는 두 프로세스가 각각 보고한 rate의 합입니다. 정확한 통합 rate는
공통 시작·끝 구간의 총 성공 바이트로 계산해야 하며 서로 다른 시간 구간의 rate를
더한 값과 같지 않을 수 있습니다.

### 보고된 브로커 카운터

| 윈도우 | 쓰기 MiB/s 평균 (peak10s) | wIOPS | 읽기 MiB/s (rIOPS) | 브로커 CPU 코어 | NIC tx / rx MiB/s |
|---|---|---|---|---|---|
| F1 RF3 acks=all 1,000만 (75 s) | 115.2–117.5 (134.9–135.1) | 495–505 | 0 | 0.64–0.84 | 80.2–108.1 / 134.2–135.8 |
| F2 RF3 acks=1 600만 (28 s) | 92.8–100.4 (124.1–127.6) | 397–427 | 0 | 0.53–0.62 | 64.4–80.4 / 123.7–125.0 |
| F3 RF3 acks=0 600만 (28 s) | 97.2–120.5 (123.5–124.1) | 414–514 | 0 | 0.80–0.81 | 87.3–94.4 / 163.5–170.6 |
| F4 RF1 acks=1 1,000만 (32 s) | 72.5–80.4 (117.6–129.1) | 312–346 | 0 | 0.30–0.31 | 0.3 / 119.9–125.4 |
| F5 프로듀서 2개 RF3 acks=all (81 s) | 99.9–102.2 (134.8–135.5) | 431–439 | 0 | 0.59–0.81 | 66.5–89.7 / 113.8–115.6 |
| F6 RF3 acks=all batch 256 KiB (43 s) | 102.3–107.7 (134.8–135.4) | 426–445 | 0 | **0.40–0.50** | 68.7–110.4 / 124.2–124.5 |
| E2 30M × 1,024 B 채우기 (262 s, 랜덤 모드) | 110.0–111.5 (134.5–135.0) | 468–473 | 0 | 0.72–0.80 | 74.9–77.5 / 114.3 |

기존 sampler는 kubectl을 **순차 실행**한 뒤 10초 쉬어 실제 간격이 약 12초였고,
브로커마다 읽은 시각이 아닌 라운드 시작 시각 하나를 사용했습니다.
실행 지연·시각 해상도·구간 경계가 중요합니다. 최고 표본은 정상 상태의 추정값이
아니며 135MiB/s 근처 값으로 gp3의 125MiB/s 설정을 135로 모델링해서는 안 됩니다.

원문의 CloudWatch E2 구간은 7,008–7,257MiB/분 = 116.8–121.0MiB/s,
29,637–30,730 write/분 = 약 494–512IOPS입니다. 순차 I/O가 상당했음을 뒷받침하지만
볼륨·인스턴스 EBS 한계, 버퍼와 짧은 표본의 영향을 각각 분리하지는 못합니다.
브로커 CPU가 낮다고 클라이언트 병목까지 배제할 수도 없습니다.

### 저장량 균형 모델과 실측 상한은 다름

복제본 하나의 인코딩된 log-byte rate를 Xlog, 복제 수를 R, 브로커 수를 B,
브로커별 지속 저장소 예산을 D라 하면 균등 배치에서 평균 쓰기는 대략
`R × Xlog / B`와 기타 I/O입니다. **브로커 3개·RF3**일 때 각 브로커가 모든
파티션의 복제본 하나를 가집니다. 리더 트래픽도 균등하면 브로커별 replica 송신은
약 `2 × Xlog / 3`, 클러스터 전체 replica 트래픽은 약 `2 × Xlog`입니다.

이 산술은 가설을 세우는 도구입니다. payload benchmark rate와 동일하지 않으며
인코딩·압축, 캐시/writeback, 읽기와 metadata가 서로 다른 예산을 사용합니다.
다른 조건을 고정한 채 스토리지 처리량 등을 바꾸는 통제 실험으로 원인을 확인합니다.

## 2. acks 지연

![한 파티션에서 acks=1은 leader append, acks=all은 그림의 안정된 ISR에서 필요한 다음 오프셋 복제를 확인한다. 백그라운드 writeback과 메시지별 fsync 보장은 구분한다.](../../.gitbook/assets/ko-data-on-eks-kafka-09-kafka-benchmark-1.png)

[인터랙티브 다이어그램](https://www.atomai.click/kubernetes-docs/archmaps/ko-data-on-eks-kafka-09-kafka-benchmark-1.html)

B 테스트는 20,000rec/s, RF3, 랜덤 1,024B 값을 사용했습니다.

| Test | acks | linger.ms | avg ms | p50 | p95 | p99 | p99.9 | max |
|---|---|---|---|---|---|---|---|---|
| B1 | all | 5 | 5.27 | 3 | 6 | **126** | 173 | 771 |
| B2 | 1 | 5 | 2.58 | 3 | 5 | **17** | 40 | 642 |
| B3 | all | 0 | 3.23 | 3 | 5 | 25 | 59 | 752 |

보고된 B1/B2 p99 비율은 7.412입니다. 평균도 5.27/2.58ms로 다르므로 “꼬리만
다르다”는 결론은 과도합니다. B3는 linger를 바꿨지만 작은 배치 때문이라는 인과
설명에는 요청 크기·개수와 반복 측정이 필요합니다. 정속 acks=0 결과는 없습니다.

A 실행에도 랜덤 payload 생성 비용이 들어갑니다.

| Test | acks | RF | rec/s | MiB/s | avg ms | p50 | p95 | p99 | p99.9 | max |
|---|---|---|---|---|---|---|---|---|---|---|
| A1 | all | 3 | 107,150 | 104.64 | 11.38 | 3 | 50 | 164 | 263 | 871 |
| A2 | 1 | 3 | 105,955 | 103.47 | 3.00 | 1 | 11 | 38 | 79 | 812 |
| A3 | 0 | 3 | 112,461 | 109.82 | 1.48 | 0 | 6 | 26 | 52 | 636 |
| A4 | 1 | 1 | 109,926 | 107.35 | 1.57 | 1 | 6 | 11 | 36 | 662 |

비슷한 처리량은 공통 제약을 시사하지만 그 자체가 CPU profile은 아닙니다.
acks=0에서도 client·buffer·socket backpressure는 존재합니다.
브로커 ack가 없다고 모든 backpressure가 사라지거나 callback 성공이 복제본 기록을
증명하는 것은 아닙니다.

시퀀스의 HW는 **다음 오프셋**입니다. 마지막 레코드가 r이면 요구 오프셋은 r+1이며
HW와 ISR 조건을 충족해야 합니다. 그림은 세 replica가 안정된 ISR에 있는 경우이고,
minISR=2인데 항상 팔로워 둘 모두가 ISR이어야 한다는 뜻은 아닙니다.

## 3. 배치 크기와 프로듀서 수

| 비교 | 설정 | MiB/s | avg ms | p99 ms | 브로커 CPU 코어 (윈도우 평균 범위) |
|---|---|---|---|---|---|
| F1 (기준) | 프로듀서 1, `batch.size=65536`, `linger.ms=5`, 1,000만 건 | 134.74 | 443.89 | 2,689 | 0.64–0.84 |
| F5 | **프로듀서 2**, 같은 배치, 2 × 500만 건 | 65.07 + 64.75 = 129.82 | 893.88 / 889.22 | 3,270 / 3,301 | 0.59–0.81 |
| F6 | 프로듀서 1, **`batch.size=262144`, `linger.ms=10`**, 600만 건 | 148.38 | 395.82 | 2,094 | **0.40–0.50** |

F6는 batch·linger·레코드 수를 바꿨습니다. 처리량은 10.12% 높고 브로커 CPU는
낮게 기록되었습니다. 중간값 계산 `1 − 0.45/0.74 = 39.19%`는 이 범위를 설명할
뿐 배치 크기로 인한 독립적인 40% 절감이 아닙니다. 반복이 없으므로 처리량 차이를
“노이즈 범위”로 판정할 수 없습니다.

F5는 이 구성의 보고된 rate를 높이지 못했지만 두 producer가 같은 제한된 client
Pod를 사용했습니다. 독립적인 부하 용량과 공통 시간 구간으로 재시험하기 전에
추가 producer가 언제나 도움이 안 된다고 일반화하지 않습니다.

## 4. 패딩 코퍼스의 압축

| codec | rec/s | MiB/s (비압축 환산) | avg ms | p50 | p95 | p99 | p99.9 | 디스크상 B/레코드 (복제본당) | `none` 대비 |
|---|---|---|---|---|---|---|---|---|---|
| none | 203,887 | 196.00 | 259.59 | 266 | 370 | 425 | 458 | 1,018 | 1.00× |
| lz4 | 275,356 | **264.70** | 4.38 | 3 | 11 | 24 | 60 | 113.1 | **9.0×** 축소 |
| snappy | 198,557 | 190.87 | 5.07 | 3 | 10 | 35 | 205 | 141.7 | 7.2× |
| zstd | 160,274 | 154.07 | 5.39 | 5 | 10 | 18 | 47 | 61.3 | **16.6×** |
| gzip | 53,418 | 51.35 | 6.01 | 6 | 10 | 17 | 45 | 60.7 | 16.8× |

원문의 복제본별 log 크기는 none/lz4/snappy/zstd/gzip 순서로
2,912.4 / 323.5 / 405.3 / 175.3 / 173.8MiB입니다. 300만 건으로 나누면 반올림된
B/record가 재현됩니다. 모든 index·파일시스템·프로비저닝 볼륨 바이트를 뜻하지는 않습니다.

패딩 때문에 많은 실제 데이터셋을 대표하지 않습니다. **비율과 codec 순서 모두
보편적 결과나 수학적 상한이 아닙니다**. 원문은 전체 zlib-6를 패딩 포함 18.5배,
제거 7.8배로 기록했습니다. 이번 검토에서 공개 AWK를 GNU Awk 5.1.0으로 실행하면
유효한 1,008B JSON 20,000개·패딩 63.17%는 확인되지만 비율은 15.92배·6.53배였습니다.
새 코퍼스이지 과거 측정을 대체하는 수치가 아닙니다. 이미지·AWK 구현과 payload hash를
함께 보존해야 합니다.

topic compression이 producer이면 지정한 다른 codec으로 의도적으로 재압축하는
대신 producer의 codec을 유지합니다. 브로커 검증과 다른 처리의 CPU까지 0인 것은
아닙니다. 압축 후 낮은 지연은 저장·전송 바이트 감소와 일치하지만 배타적인 병목
이동을 주장하려면 해당 phase의 client CPU·I/O 근거가 필요합니다.

## 5. 레코드 크기

| Test | 레코드 크기 | 레코드 수 | rec/s | MiB/s | avg ms | p50 | p95 | p99 | p99.9 |
|---|---|---|---|---|---|---|---|---|---|
| D1 | 100 B | 1,000만 | **506,380** | 48.29 | 3.18 | 2 | 9 | 15 | 33 |
| A1 | 1,024 B | 300만 | 107,150 | 104.64 | 11.38 | 3 | 50 | 164 | 263 |
| D2 | 10,240 B | 30만 | 12,326 | 120.37 | 17.40 | 5 | 84 | 157 | 223 |

생성 비용과 레코드 수가 다른 실행입니다. 100B 경우는 1,024B 대비 rec/s 약
4.73배, payload rate는 46.15%입니다. 두 단위가 모두 중요함을 보여주지만
브로커의 건당 비용을 client 생성·배치·캐시와 분리한 결과는 아닙니다.
집계는 지연·키·실패 의미가 애플리케이션에 맞을 때 검토합니다.

## 6. 생산과 동시에 재처리

E0 producer는 103.36MiB/s·p99 82ms, E1의 선택된 hot 구간은 434.11MiB/s로
기록되었습니다. E2는 3,000만 × 1,024B(**28.610GiB**)에서 112.84MiB/s·p99
1,531ms였습니다. 반복적으로 느린 구간이 관찰되었지만 dirty-page writeback은
가설이었습니다.

E2의 다른 기록값은 평균 60.17ms, p50 2, p95 125, p99.9 5,034, max 5,258ms입니다.
51개 보고 구간 중 60MiB/s 미만은 56.8, 36.3, 45.3, 40.8, 45.8의 다섯 구간입니다.
이 관찰만으로 정지 원인을 특정할 수는 없습니다.

E3의 13개 완전 구간 rate는 337.6, 431.3, 414.2, 495.7, 454.9, 452.1,
387.9, 458.7, 439.9, 452.4, 447.7, 491.0, 438.6이며 단순 평균은
**438.615MiB/s**입니다. 완전히 cold한 캐시는 확립되지 않았습니다.
구간이 다른 NIC·디스크 평균을 빼 정확한 page-cache 바이트율을 산출하지 않습니다.

| | E1 hot | E3 cold |
|---|---|---|
| 컨슈머 처리량 (정상 구간) | 434.11 MiB/s | 평균 438.6 MiB/s (337.6–495.7) |
| 브로커 디스크 읽기 (볼륨당) | 0 | 88–111 MiB/s 평균, 피크 ≈124 (1,315–1,545 rIOPS) |
| 브로커 NIC tx (브로커당) | 82.8–83.4 MiB/s (15초 윈도우, JVM 기동·그룹 조인 포함) | 136.6–141.5 MiB/s |
| 브로커 CPU | 0.11–0.15 코어 | 0.11–0.12 코어 |

| | E0 (produce 단독) | E4 (리플레이 중 produce) |
|---|---|---|
| produce MiB/s | 103.36 | **57.37** |
| produce p99 | 82 ms | **2,147 ms** |
| 브로커 디스크 (볼륨당) | 쓰기 60.4–67.4 MiB/s (테스트 중; 나머지는 이후 드레인) | 쓰기 39.4–47.2 + 읽기 28.6–37.7 MiB/s |

E4 producer 감소율은 **44.49%**입니다. 볼륨 읽기·쓰기가 공유되므로 저장소 경합은
가능하지만 producer·consumer도 CPU 1.9개인 client Pod와 NIC를 공유했습니다.
전체 세션의 throttling 합계나 낮은 **브로커** CPU로 phase별 **클라이언트**
경합을 배제할 수 없습니다.

E4 소비 기록은 29,297.33MiB·30,000,466건, 전체 288.79MiB/s·조인 제외
299.62MiB/s입니다. 마지막 poll 묶음 때문에 요청 건수를 초과할 수 있으므로
초과한 건수만으로 중복이라고 판단하지 않습니다.

E1의 선택 구간, E3의 비가중 구간 평균, E4의 fetch·전체 rate는 같은 값이 아닙니다.
특히 438.6→299.62를 같은 분모의 통제된 감소율로 해석하지 않습니다.
공통 구간으로 비교할 수 있도록 원시 시각·총 바이트와 phase별 자원 카운터를 보존합니다.

## 7. 얼마나 길게 실행해야 하는가?

Kafka ack는 모든 replica의 메시지별 fsync를 뜻하지 않습니다. page cache에 append가
쌓이는 동안 writeback이 비동기로 진행될 수 있으며 복제가 모든 연관 장애의 무손실을
보장하는 것은 아닙니다.

F4의 일부 구간은 이상화된 `3 × 125 = 375MiB/s` 볼륨 예산보다 높고 E0 종료 후에도
writeback이 기록되었습니다. 버퍼와 측정 구간을 맞춰야 하는 이유입니다.
**10GiB나 1분이라는 공통 기준으로 디스크 정상 상태를 증명할 수는 없습니다**.
F1의 인코딩 데이터 약 9.5GiB도 그런 증거는 아닙니다.

고정한 warmup과 긴 steady 구간, 종료 후 drain, dirty memory·EBS·네트워크 credit을
관찰하고 순서를 무작위화하여 반복합니다. 인과 비교는 한 번에 한 요소를 바꿉니다.
다른 조건을 유지한 스토리지 처리량 증설 등이 후속 통제 실험이 될 수 있습니다.

### 네트워크·EBS 비교 바로잡기

EC2는 **송신과 수신의 네트워크 credit이 별도**입니다. rx+tx를 더해 하나의 방향별
기준과 비교하지 않습니다. F1에서 최대 rx 136MiB/s는 약 **1.141Gbps**, tx
108MiB/s는 약 **0.906Gbps**로 각각 m5.xlarge 기준 1.25Gbps보다 낮습니다.
이 F1 값으로 브로커의 네트워크 burst 사용을 증명할 수 없습니다.

반면 F4 client의 payload 337.81MiB/s는 약 2.834Gbps로 m5.large의 0.75Gbps
기준보다 높습니다. credit에 영향을 받는 client 성능은 중요한 한계입니다.
packet rate·flow 한계와 노드의 다른 트래픽도 관찰합니다.

m5.xlarge EBS는 기준 1,150Mbps·최대 4,750Mbps, 약 **137.09/566.24MiB/s**입니다.
기준값은 순간적인 절대 상한이 아닙니다. 현재 gp3 최대는 조건에 따라
**2,000MiB/s**이며 필요한 IOPS·볼륨 조건과 인스턴스 한계를 함께 봅니다.
기존 1,000MiB/s 설명은 오래되었습니다. 볼륨이나 브로커 크기를 키우는 것만으로
과거 실행의 병목 원인이 입증되지는 않습니다.

## 비용 계산과 비용 청구·현재 단가는 구분

원문에 기록된 `$0.236/브로커-시간`, `$0.0912/GB-월`과 당시의 배분 가정으로 계산하면:

| 계산 | 결과 |
| --- | --- |
| 브로커 3대 × 50분 | $0.590 |
| 100GiB 볼륨 3개 × 39분, 730시간을 분모로 사용 | $0.02436 |
| 위 배분 항목의 1회 합계 | 약 $0.614 |
| 브로커 3대 × 730시간 + 300GiB-월 저장소 | $544.20 |

730시간은 비교용 가정이지 9월 청구서가 아닙니다. 기존 client 노드, EKS/control
plane, 네트워크와 다른 공용 인프라는 제외되어 있습니다. 다른 워크로드를 위해
남은 노드도 있어 배분 시간은 추정입니다. 배포 전 현재 리전 가격을 다시 확인하며,
이번 검토에서 비용 청구 조회나 새 Pricing API 근거를 만들지는 않았습니다.

브로커 CPU가 낮다는 이유만으로 컴퓨팅 비용이 낭비인 것은 아닙니다.
메모리·네트워크·EBS 대역폭·장애 여유와 배치 조건이 인스턴스 크기를 요구할 수 있습니다.

## 보완한 재현 예제

표준 EBS CSI와 지정한 인스턴스·AZ 용량이 있는 **새 전용 테스트 환경·네임스페이스**에서
사용합니다. 기존 Kafka/PVC 위에 적용하지 않습니다. 새 실행은
`kafka-storage.sh random-uuid`로 만든 ID로 예제 CLUSTER_ID를 바꾸고 실제 image
digest·런타임 버전을 기록합니다.

아래는 원본 그대로가 아닌 **보완된 재현 템플릿**입니다. AZ를 고정하고 gp3
IOPS·처리량·암호화를 명시했으며 readiness 이전 headless DNS, TCP startup/readiness,
benchmark Pod만 허용하는 ingress와 API token automount 비활성화를 추가했습니다.
NetworkPolicy는 CNI 집행이 필요합니다. 격리된 시험을 위해 PLAINTEXT·combined 역할을
유지하며 운영 환경 설계로 제시하는 것은 아닙니다.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: bench-kafka
---
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: bench-kafka-gp3
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Delete
parameters:
  type: gp3
  iops: '3000'
  throughput: '125'
  encrypted: 'true'
---
apiVersion: v1
kind: Service
metadata:
  name: kafka-hs
  namespace: bench-kafka
spec:
  clusterIP: None
  selector:
    app: kafka
  ports:
  - name: broker
    port: 9092
  - name: controller
    port: 9093
  publishNotReadyAddresses: true
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: kafka
  namespace: bench-kafka
spec:
  serviceName: kafka-hs
  replicas: 3
  podManagementPolicy: Parallel
  selector:
    matchLabels:
      app: kafka
  template:
    metadata:
      labels:
        app: kafka
      annotations:
        karpenter.sh/do-not-disrupt: 'true'
    spec:
      terminationGracePeriodSeconds: 60
      nodeSelector:
        node.kubernetes.io/instance-type: m5.xlarge
        karpenter.sh/capacity-type: on-demand
        topology.kubernetes.io/zone: ap-northeast-2b
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchLabels:
                app: kafka
            topologyKey: kubernetes.io/hostname
      securityContext:
        fsGroup: 1000
      containers:
      - name: kafka
        image: apache/kafka:4.3.1
        command:
        - /bin/bash
        - -c
        - |
          set -e
          ORD=${HOSTNAME##*-}
          export KAFKA_NODE_ID=$ORD
          export KAFKA_ADVERTISED_LISTENERS="PLAINTEXT://${HOSTNAME}.kafka-hs.bench-kafka.svc.cluster.local:9092"
          exec /etc/kafka/docker/run
        env:
        - name: CLUSTER_ID
          value: UdHYY7YQRrunSRromZFozw
        - name: KAFKA_PROCESS_ROLES
          value: broker,controller
        - name: KAFKA_CONTROLLER_QUORUM_VOTERS
          value: 0@kafka-0.kafka-hs.bench-kafka.svc.cluster.local:9093,1@kafka-1.kafka-hs.bench-kafka.svc.cluster.local:9093,2@kafka-2.kafka-hs.bench-kafka.svc.cluster.local:9093
        - name: KAFKA_LISTENERS
          value: PLAINTEXT://0.0.0.0:9092,CONTROLLER://0.0.0.0:9093
        - name: KAFKA_LISTENER_SECURITY_PROTOCOL_MAP
          value: PLAINTEXT:PLAINTEXT,CONTROLLER:PLAINTEXT
        - name: KAFKA_INTER_BROKER_LISTENER_NAME
          value: PLAINTEXT
        - name: KAFKA_CONTROLLER_LISTENER_NAMES
          value: CONTROLLER
        - name: KAFKA_LOG_DIRS
          value: /var/lib/kafka/data/kafka
        - name: KAFKA_NUM_PARTITIONS
          value: '6'
        - name: KAFKA_DEFAULT_REPLICATION_FACTOR
          value: '3'
        - name: KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR
          value: '3'
        - name: KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR
          value: '3'
        - name: KAFKA_TRANSACTION_STATE_LOG_MIN_ISR
          value: '2'
        - name: KAFKA_MIN_INSYNC_REPLICAS
          value: '2'
        - name: KAFKA_LOG_RETENTION_HOURS
          value: '2'
        - name: KAFKA_LOG_SEGMENT_BYTES
          value: '1073741824'
        - name: KAFKA_NUM_NETWORK_THREADS
          value: '4'
        - name: KAFKA_NUM_IO_THREADS
          value: '8'
        - name: KAFKA_NUM_REPLICA_FETCHERS
          value: '2'
        - name: KAFKA_HEAP_OPTS
          value: -Xms4G -Xmx4G
        ports:
        - containerPort: 9092
        - containerPort: 9093
        resources:
          requests:
            cpu: '3'
            memory: 10Gi
          limits:
            cpu: '4'
            memory: 12Gi
        volumeMounts:
        - name: data
          mountPath: /var/lib/kafka/data
        startupProbe:
          tcpSocket:
            port: 9092
          periodSeconds: 5
          failureThreshold: 60
        readinessProbe:
          tcpSocket:
            port: 9092
          periodSeconds: 5
      automountServiceAccountToken: false
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes:
      - ReadWriteOnce
      storageClassName: bench-kafka-gp3
      resources:
        requests:
          storage: 100Gi
---
apiVersion: v1
kind: Pod
metadata:
  name: kafka-client
  namespace: bench-kafka
  labels:
    app: kafka-client
spec:
  restartPolicy: Never
  nodeSelector:
    node.kubernetes.io/instance-type: m5.large
    topology.kubernetes.io/zone: ap-northeast-2b
    karpenter.sh/capacity-type: on-demand
  containers:
  - name: client
    image: apache/kafka:4.3.1
    command:
    - sleep
    - infinity
    env:
    - name: KAFKA_HEAP_OPTS
      value: -Xms2G -Xmx2G
    resources:
      requests:
        cpu: 500m
        memory: 2500Mi
      limits:
        cpu: 1900m
        memory: 4Gi
  automountServiceAccountToken: false
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: benchmark-brokers
  namespace: bench-kafka
spec:
  podSelector:
    matchLabels:
      app: kafka
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchExpressions:
        - key: app
          operator: In
          values:
          - kafka
          - kafka-client
    ports:
    - protocol: TCP
      port: 9092
    - protocol: TCP
      port: 9093
```

`bench-kafka.yaml`로 저장하고 리소스·가용 용량을 검토한 다음 실행합니다.

```bash
kubectl apply -f bench-kafka.yaml
kubectl -n bench-kafka rollout status statefulset/kafka --timeout=600s
kubectl -n bench-kafka wait --for=condition=Ready pod/kafka-client --timeout=600s
kubectl -n bench-kafka get pods -o wide
kubectl -n bench-kafka get pods -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.containerStatuses[*].imageID}{"\n"}{end}'
```

공개된 생성기를 `payload.awk`로 저장하고 **client Pod 안에서** 실행합니다.
비교를 위해 유지한 생성기이며 압축하기 쉬운 패딩은 의도적으로 들어 있습니다.

```awk
BEGIN{srand(42); split("payments orders inventory auth search checkout shipping catalog notify gateway",ns," ");
     split("INFO INFO INFO INFO WARN ERROR DEBUG",lv," ");
     for(i=0;i<20000;i++){
       n=ns[int(rand()*10)+1]; l=lv[int(rand()*7)+1]; d=int(rand()*900)+5; u=int(rand()*100000);
       msg=sprintf("{\"ts\":\"2026-09-02T02:%02d:%02d.%03dZ\",\"level\":\"%s\",\"namespace\":\"%s\",\"pod\":\"%s-7d9f8b6c4-%05x\",\"trace_id\":\"%08x%08x%08x%08x\",\"http\":{\"method\":\"POST\",\"path\":\"/api/v1/%s/%d\",\"status\":%d,\"duration_ms\":%d,\"bytes\":%d},\"user_id\":%d,\"region\":\"ap-northeast-2\",\"msg\":\"request completed upstream=%s-svc:8080 retries=%d cache=%s\"",
         int(rand()*60),int(rand()*60),int(rand()*1000),l,n,n,int(rand()*1048576),int(rand()*4294967296),int(rand()*4294967296),int(rand()*4294967296),int(rand()*4294967296),n,u,(l=="ERROR"?500:200),d,int(rand()*20000),u,n,int(rand()*3),(rand()<0.7?"hit":"miss"));
       pad=1000-length(msg)-2; if(pad<0)pad=0; p=""; for(k=0;k<pad;k++)p=p "x";
       printf "%s,\"pad\":\"%s\"}\n", msg, p }}
```

```bash
mkdir -p /tmp/results
LC_ALL=C awk -f payload.awk > /tmp/results/payload-1k.txt
sha256sum /tmp/results/payload-1k.txt
wc -l -c /tmp/results/payload-1k.txt
```

`runs.sh`도 client Pod 안에서 실행합니다. 토픽 생성·데이터 채우기, 별도 로그,
producer 최종 성공 건수 검사를 포함하며 전체 시간은 20분 후 종료 신호·30초 후
강제 종료로 제한합니다. consumer의 --timeout은 전체 시간이 아닌 무응답 간격입니다.

```bash
#!/bin/bash
set -euo pipefail
BIN=/opt/kafka/bin
BS="kafka-0.kafka-hs.bench-kafka.svc.cluster.local:9092,kafka-1.kafka-hs.bench-kafka.svc.cluster.local:9092,kafka-2.kafka-hs.bench-kafka.svc.cluster.local:9092"
BENCH_RESULTS=/tmp/results
mkdir -p "$BENCH_RESULTS"
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-$$"

new_topic() {
  "$BIN/kafka-topics.sh" --bootstrap-server "$BS" --create --topic "$1" \
    --partitions 6 --replication-factor "$2" \
    --config "min.insync.replicas=$3" --config retention.bytes=-1
}
produce() {
  local topic="$1" count="$2" mode="$3" value="$4" rate="$5" acks="$6" codec="$7"
  shift 7
  local result="$BENCH_RESULTS/$topic-$BASHPID.log"
  date -u +%Y-%m-%dT%H:%M:%SZ > "$result.start"
  timeout -k 30 1200 "$BIN/kafka-producer-perf-test.sh" \
    --bootstrap-server "$BS" --topic "$topic" --num-records "$count" \
    --throughput "$rate" "$mode" "$value" --print-metrics \
    --command-property "acks=$acks" "compression.type=$codec" \
      linger.ms=5 batch.size=65536 buffer.memory=67108864 "$@" 2>&1 | tee "$result"
  date -u +%Y-%m-%dT%H:%M:%SZ > "$result.end"
  # The tool can print callback errors without making every failure a nonzero exit.
  # This check is for warmup-records=0 and the final, non-window summary.
  awk -v expected="$count" '/ms 99[.]9th[.]/ {seen=1; actual=$1}
    END {if (!seen || actual != expected) exit 1}' "$result"
}

# Historical F1-shaped workload: a new topic and the published padded payload.
F_TOPIC="bench-f1-$RUN_ID"
new_topic "$F_TOPIC" 3 2
produce "$F_TOPIC" 10000000 --payload-file "$BENCH_RESULTS/payload-1k.txt" -1 all none

# Historical B1-shaped workload: pre-create the latency topic.
B_TOPIC="bench-b1-$RUN_ID"
new_topic "$B_TOPIC" 3 2
produce "$B_TOPIC" 1200000 --record-size 1024 20000 all none

# E2/E3-shaped replay: populate before consuming; 30M*1024 B = 28.61 GiB.
E_TOPIC="bench-e2-$RUN_ID"
new_topic "$E_TOPIC" 3 2
produce "$E_TOPIC" 30000000 --record-size 1024 -1 all none
timeout -k 30 1200 "$BIN/kafka-consumer-perf-test.sh" --bootstrap-server "$BS" \
  --topic "$E_TOPIC" --num-records 30000000 --group "bench-e3-$RUN_ID" \
  --timeout 600000 --show-detailed-stats --reporting-interval 5000 --print-metrics \
  2>&1 | tee "$BENCH_RESULTS/$E_TOPIC-consumer.log"

printf '%s\n' "$F_TOPIC" "$B_TOPIC" "$E_TOPIC" > "$BENCH_RESULTS/topics-$RUN_ID.txt"
# Preserve logs and validate success/readback before deleting this run's topics.
```

템플릿은 F1·B1·E2/E3 형태의 실행을 보여줍니다. 나머지는 새 토픽에 표의 RF/minISR,
건수, acks, codec, batch/linger를 적용합니다. produce helper는 필수 인자 7개 뒤에
추가 Kafka 속성을 받으며 F6은 `batch.size=262144 linger.ms=10`입니다.
F5는 500만 건 producer 두 개의 로그와 공통 시간 구간을 따로 기록합니다.
E4는 같은 client 재현과 별도 부하 용량을 쓰는 통제 변형을 구분합니다.
실행 사이 writeback/drain을 확인하고 특히 acks=0의 내용·오류를 검증합니다.
요청 건수를 채웠다는 사실만으로 정상 상태 실험이라 부르지 않습니다.

### 실제 장치와 실제 시간 간격 수집

PVC→PV→EBS 볼륨과 block device를 확인한 뒤 devices.txt를 만듭니다.
nvme1n1이 언제나 데이터 볼륨인 것은 아닙니다. 예제는 cgroup v2 CPU 카운터,
sysfs 가시성과 eth0를 전제로 하므로 실제 환경을 먼저 확인합니다.

kubectl이 있는 곳에 `sample-broker.sh`로 저장합니다.

```sh
#!/bin/sh
set -eu
device="${1:?Pass the verified data-volume block-device name}"
interface="${2:-eth0}"
case "$device" in *[!a-zA-Z0-9_-]*|'') echo "Invalid block-device name" >&2; exit 2;; esac
case "$interface" in *[!a-zA-Z0-9_.-]*|'') echo "Invalid network interface" >&2; exit 2;; esac
read -r start_uptime ignored < /proc/uptime
read -r read_ios read_merges read_sectors read_ms write_ios write_merges write_sectors write_ms rest \
  < "/sys/class/block/$device/stat"
cpu_usage="$(awk '$1=="usage_usec" {print $2}' /sys/fs/cgroup/cpu.stat)"
cpu_throttled="$(awk '$1=="throttled_usec" {print $2}' /sys/fs/cgroup/cpu.stat)"
: "${cpu_usage:?Missing cgroup v2 CPU usage counter}"
: "${cpu_throttled:?Missing cgroup v2 CPU throttling counter}"
net_tx="$(cat "/sys/class/net/$interface/statistics/tx_bytes")"
net_rx="$(cat "/sys/class/net/$interface/statistics/rx_bytes")"
read -r end_uptime ignored < /proc/uptime
printf '{"device":"%s","interface":"%s","start_uptime_s":%s,"end_uptime_s":%s,"read_ios":%s,"read_sectors":%s,"write_ios":%s,"write_sectors":%s,"cpu_usage_usec":%s,"cpu_throttled_usec":%s,"net_tx_bytes":%s,"net_rx_bytes":%s}\n' \
  "$device" "$interface" "$start_uptime" "$end_uptime" "$read_ios" "$read_sectors" "$write_ios" "$write_sectors" \
  "$cpu_usage" "$cpu_throttled" "$net_tx" "$net_rx"
```

다음을 `sampler.sh`로 저장합니다. devices.txt에는 확인한 `kafka-N 장치이름 [인터페이스]`를
한 줄에 하나씩 적으며 인터페이스 기본값은 eth0입니다.

```bash
#!/bin/bash
set -euo pipefail
# devices.txt: "pod block-device [interface]" per line; interface defaults to eth0.
# Example only: kafka-0 nvme1n1. Verify PVC -> PV -> EBS volume -> device first.
while true; do
  while read -r pod device interface; do
    [[ "$pod" =~ ^kafka-[0-2]$ ]] || { echo "Invalid benchmark pod" >&2; exit 2; }
    utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    sample="$(kubectl -n bench-kafka exec -i "$pod" -- sh -s -- "$device" "${interface:-eth0}" < sample-broker.sh)"
    printf '%s\t%s\t%s\n' "$utc" "$pod" "$sample" >> broker-samples.tsv
  done < devices.txt
  sleep 10
done
```

Pod별 단조 증가 sample 시각과 읽기 시작·끝 범위를 사용합니다.
sector 차이×512/경과 시간은 bytes/s, I/O 차이는 IOPS, usage_usec 차이/1,000,000/
경과 시간은 CPU core입니다. reset·음수 차이·누락 표본을 제외합니다.
같은 phase의 **client** CPU/NIC, producer buffer/request 메트릭도 수집하며
확인한 volume ID의 CloudWatch VolumeReadBytes·VolumeWriteBytes·VolumeWriteOps와
시간 구간을 맞춥니다.

정리 전에 결과를 내보냅니다. namespace 삭제는 파괴적이며 노드·클러스터 범위
StorageClass를 자동 삭제하지 않습니다. 템플릿은 Delete reclaim을 사용하지만
PVC/PV/EBS 삭제와 남은 노드 비용을 확인해야 합니다.

```bash
kubectl delete namespace bench-kafka
# After confirming this run's PVs/volumes are gone and no claims use the class:
kubectl delete storageclass bench-kafka-gp3
```

## 검토 근거와 함께 읽기

이번 검토는 산술, 공개 payload 생성기, 실제 Kafka 성능 도구의 옵션·callback 동작,
리소스 스키마·셸 구문과 다이어그램 렌더링을 검사했습니다.
AWS 처리량 벤치마크를 새로 실행한 결과는 아닙니다.

- [Original benchmark report, PR #166](https://github.com/Atom-oh/kubernetes-docs/pull/166)
- [Kafka 4.3.1 ProducerPerformance source](https://github.com/apache/kafka/blob/4.3.1/tools/src/main/java/org/apache/kafka/tools/ProducerPerformance.java)
- [Kafka 4.3.1 ConsumerPerformance source](https://github.com/apache/kafka/blob/4.3.1/tools/src/main/java/org/apache/kafka/tools/ConsumerPerformance.java)
- [Kafka 4.3.1 required produce offset](https://github.com/apache/kafka/blob/4.3.1/core/src/main/scala/kafka/server/ReplicaManager.scala)
- [Kafka 4.3.1 high-watermark check](https://github.com/apache/kafka/blob/4.3.1/core/src/main/scala/kafka/cluster/Partition.scala)
- [Official Kafka image definition](https://github.com/apache/kafka/blob/4.3.1/docker/jvm/Dockerfile)
- [gp3 performance and provisioning conditions](https://docs.aws.amazon.com/ebs/latest/userguide/general-purpose.html)
- [EC2 per-direction network credits](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-network-bandwidth.html)
- [EC2 general-purpose network/EBS specifications](https://docs.aws.amazon.com/ec2/latest/instancetypes/gp.html)
- [Linux block I/O counters](https://www.kernel.org/doc/html/latest/admin-guide/iostats.html)

- [EBS gp2/gp3 벤치마크](../../storage/01-ebs-gp2-gp3-benchmark.md)
- [ClickHouse on EKS](../../database/01-clickhouse-on-eks.md)
- [Kafka 기초](./01-kafka-fundamentals.md)
- [Kafka 운영](./03-kafka-operations.md)
- [모범 사례](./08-best-practices.md)
- [주제 퀴즈](../../quizzes/data-on-eks/kafka/09-kafka-benchmark-quiz.md)
