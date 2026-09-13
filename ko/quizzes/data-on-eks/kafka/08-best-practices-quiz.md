# Part 8: 모범 사례 퀴즈

파티션·클라이언트·보안·용량·복구를 실제 조건에 맞춰 판단합니다.

## 1. 일반적인 컨슈머 그룹의 파티션 수를 정할 때 무엇을 함께 고려하나요?

<details>
<summary>정답 보기</summary>

멤버 병렬도뿐 아니라 파티션당 처리량, 키 편중, 레코드 크기, replica 배치와 장애 복구를 측정합니다. 한 파티션은 그룹의 한 멤버에 할당되지만 Share group이나 애플리케이션 내부 병렬화는 다른 의미입니다.

</details>

## 2. 과거 파티션 수 경험치를 현재의 공통 상한으로 사용해도 되나요?

<details>
<summary>정답 보기</summary>

아닙니다. 버전·브로커·컨트롤러·replica 수와 부하에 따라 다릅니다. 논리 파티션과 브로커별 replica 배치를 구분하고 정상·장애 상태에서 시험합니다.

</details>

## 3. PartitionCount가 들어간 줄을 세면 전체 파티션 수가 나오나요?

<details>
<summary>정답 보기</summary>

아닙니다. 토픽 요약 줄 수입니다. 본문의 partition_summary.py처럼 Partition: 줄을 읽어 논리 파티션과 replica 배치를 따로 계산합니다. 빈 결과·조회 권한·필터도 확인합니다.

</details>

## 4. 키가 있는 토픽의 파티션 수를 늘릴 때 모든 키가 반드시 이동하나요?

<details>
<summary>정답 보기</summary>

모든 키가 이동하는 것은 아니지만 일부는 바뀔 수 있습니다. 옛 레코드는 이동하지 않아 키 단위 순서·상태·co-partitioned join 가정에 영향을 줍니다. serializer·partitioner와 토폴로지를 함께 검토합니다.

</details>

## 5. 명시적으로 acks나 retries를 설정하면 기본 멱등성이 항상 꺼지나요?

<details>
<summary>정답 보기</summary>

아닙니다. 호환되지 않는 설정이 문제입니다. enable.idempotence=true를 명시하면 acks·retries·max.in.flight가 호환되어야 하며 충돌 시 설정 오류가 납니다.

</details>

## 6. 멱등성이나 transactional.id 하나로 전체 경로 exactly-once가 완성되나요?

<details>
<summary>정답 보기</summary>

아닙니다. producer 재시도 중복과 애플리케이션 재전송·외부 효과는 다릅니다. Kafka 트랜잭션에는 출력·입력 오프셋의 원자적 커밋, fencing·read_committed 등이 필요하며 외부 시스템은 별도 전략이 필요합니다.

</details>

## 7. RF=3, acks=all, min.insync.replicas=2에서 ISR이 1이 되면 어떻게 되나요?

<details>
<summary>정답 보기</summary>

쓰기가 거부됩니다. acks=all은 현재 ISR을 기다리며 min ISR은 토픽·브로커 설정입니다. 이미 복제가 저하된 경우까지 단일 장애 후 쓰기 지속·무손실을 무조건 보장하지는 않습니다.

</details>

## 8. max.poll.interval.ms 초과와 heartbeat/session 설정에서 구분할 점은 무엇인가요?

<details>
<summary>정답 보기</summary>

실제 처리 시간이 poll 간격을 넘는지 확인합니다. 정적 멤버는 session 만료까지 재할당이 지연될 수 있습니다. classic 프로토콜의 클라이언트 간격 설정과 consumer 프로토콜의 브로커 설정을 구분합니다.

</details>

## 9. 정적 멤버십이 항상 rebalance 없는 재시작을 보장하나요?

<details>
<summary>정답 보기</summary>

아닙니다. 안정적·고유한 논리 ID와 재접속 시간뿐 아니라 토폴로지·구독·멤버 상태도 중요합니다. 중복 활성 ID는 fencing을 일으킬 수 있고 session을 늘리면 실제 장애 복구도 늦어집니다.

</details>

## 10. 기본 Strimzi에서 KafkaUser의 mTLS 클라이언트 인증서에 서명하는 CA는 무엇인가요?

<details>
<summary>정답 보기</summary>

clients CA입니다. cluster CA는 브로커·내부 구성요소의 인증서에 사용합니다. 클라이언트 자격증명과 브로커를 신뢰하는 CA 체인을 구분해야 합니다.

</details>

## 11. 고카디널리티나 랜덤 salt를 사용하면 키 편중 문제가 안전하게 해결되나요?

<details>
<summary>정답 보기</summary>

아닙니다. 매우 바쁜 키가 여전히 편중을 만들 수 있습니다. salt는 순서·조인·compaction 키의 의미를 바꾸므로 계약이 허용하는지와 재결합 전략을 먼저 검토합니다.

</details>

## 12. 처리 중 예외가 발생한 뒤 commit을 하지 않고 다음 poll을 계속하면 안전한가요?

<details>
<summary>정답 보기</summary>

그렇지 않습니다. fetch 위치는 이미 진행했을 수 있습니다. 중단·복구하거나 올바르게 seek하고, 영속 처리 완료 후에만 커밋합니다. 재처리 중복과 외부 작업의 멱등성도 설계합니다.

</details>

## 13. Kafka 용량을 메모리나 heap 고정 크기 하나로 결정해도 되나요?

<details>
<summary>정답 보기</summary>

아닙니다. page cache 외에도 TLS·압축 CPU, 네트워크, IOPS·처리량, cgroup 메모리와 장애 복구를 측정합니다. codec·인스턴스 종류의 비용 우위도 실제 데이터와 부하에 달려 있습니다.

</details>

## 14. 한 networkPolicyPeers 항목의 namespaceSelector와 podSelector는 어떤 관계인가요?

<details>
<summary>정답 보기</summary>

AND입니다. 서로 다른 peer 항목은 OR입니다. NetworkPolicy들은 합산되며 CNI 집행과 egress도 확인해야 합니다. 다른 정책이 허용한 트래픽을 이 항목이 거부하지는 않습니다.

</details>

## 15. StorageClass 암호화 설정과 Auto Mode·기존 볼륨의 관계를 설명하세요.

<details>
<summary>정답 보기</summary>

사용하는 provisioner에 맞춰 encrypted:true와 실제 KMS 권한을 구성하고 EBS 결과를 확인합니다. Auto Mode 노드·임시 디스크 암호화로 모든 동적 PVC를 추정하지 않습니다. StorageClass·계정 기본값 변경은 기존 볼륨을 소급 암호화하지 않습니다.

</details>

## 16. 본문의 producer 튜닝 프로필을 작성하고 batch.size·min ISR의 의미를 설명하세요.

<details>
<summary>정답 보기</summary>

```properties
acks=all
enable.idempotence=true
max.in.flight.requests.per.connection=5
compression.type=lz4
linger.ms=10
batch.size=32768
delivery.timeout.ms=120000
```

batch.size는 파티션별 배치·할당 설정이며 레코드·요청의 엄격한 상한은 아닙니다. min.insync.replicas는 토픽·브로커에 설정합니다. codec·linger는 측정해서 결정하고 send 실패·delivery timeout을 처리합니다.

</details>

## 17. 기존 SCRAM 사용자를 보존하면서 별도 mTLS KafkaUser를 작성하세요.

<details>
<summary>정답 보기</summary>

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaUser
metadata:
  name: order-service-mtls
  namespace: kafka
  labels:
    strimzi.io/cluster: my-cluster
spec:
  authentication:
    type: tls
  authorization:
    type: simple
    acls:
    - resource:
        type: topic
        name: orders
        patternType: literal
      operations:
      - Read
      - Write
      - Describe
    - resource:
        type: group
        name: order-processor-mtls
        patternType: literal
      operations:
      - Read
    - resource:
        type: cluster
      operations:
      - IdempotentWrite
```

tls:true와 authentication.type:tls인 별도 listener도 필요합니다. type:tls라는 노출 방식은 없습니다. clients CA가 발급한 자격증명·브로커 신뢰를 배포·회전시키고 실제 허용·거부를 검증합니다.

</details>

## 18. 정적 멤버 ID 환경변수와 수동 커밋을 어떻게 연결해야 하나요?

<details>
<summary>정답 보기</summary>

Java Properties의 ${POD_NAME}은 자동 치환되지 않습니다. 본문의 setStaticIdentity에 실제 고유·안정적 ID를 전달한 뒤 컨슈머를 만듭니다. enable.auto.commit=false와 processOneBatch를 사용하고 처리 실패를 삼켜 다음 poll로 넘어가지 않습니다. 토픽 보존·복구와 중복 처리도 필요합니다.

</details>

---

[학습 자료로 돌아가기](../../../data-on-eks/kafka/08-best-practices.md) | [다음 퀴즈](./09-kafka-benchmark-quiz.md)
